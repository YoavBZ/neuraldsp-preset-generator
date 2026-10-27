"""ROADMAP step (b), D_F5ft: X-LANCE gtr_mss fine-tuned on our self-built mixes against their wet target renders, then
the every-control model fed the fine-tuned stem (`docs/trusted-data-t0-design.md`, "D_F5ft: the every-control model
fed the fine-tuned stem"; ledger `trusted-data-t3`, amendment 4). Declared before any fine-tune or training; approved
by the user 2026-10-27 ("Yes for all"). Outputs go to `trusted-data/t3-xlft/` only; `t0/`, `t2/`, `t3/`, `t3-mix/`
and `tone-probe/` are read, never written. Runs after step (a) (it reads D_F5-noaug and D_F5mix).

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    MSST=~/ndsp-presets/tools/msst-venv/bin/python
    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN -m learn.xlance_finetune check                     # zero: ledger, step (a) done, the frozen sets, disk
    $MSST -m learn.xlance_finetune prep                      # folds; F5's mixes and wet targets rebuilt (CPU); checks
    $MSST -m learn.xlance_finetune gate                      # the MPS gate and its fallbacks; step time and memory
    $MSST -m learn.xlance_finetune train --fold 0|1          # one cross-fitted fine-tune, up to 5.5 h of steps
    $MSST -m learn.xlance_finetune separate --fold k --device mps|cpu --order asc|desc   # out-of-fold stems
    $MSST -m learn.xlance_finetune vreal-stems               # V-real-11's crops through their assigned fold
    $TORCH_PY -m learn.xlance_finetune train-d --seed 20261042|20261043
    $TORCH_PY -m learn.xlance_finetune fit
    $TORCH_PY -m learn.xlance_finetune r0                    # zero renders: R0 beside D_F5-noaug, D_F5mix, D_F5
    $MAIN -m learn.xlance_finetune probe                     # zero renders: the tone probe on the new stems
    $TORCH_PY -m learn.xlance_finetune vreal-predict         # zero renders
    $MAIN -u -m learn.xlance_finetune vreal-render --shard k/3   # 99 renders in all (33 groups x (1 + 2))
    $MAIN -m learn.xlance_finetune report

**The fine-tune.** gtr_mss (BS-RoFormer, 51.0 M parameters) with its last 4 of 12 transformer layers, the final norm
and the mask estimator trainable (33.1 M), the rest frozen; AdamW at X-LANCE's own 2e-5 and betas (0.8, 0.99), no
weight decay, 100-step warm-up then cosine; one 6-s window per micro-batch, 2 accumulated; the model's own loss (L1
waveform + multi-resolution STFT). Input: each F5 full twin's self-built mix, rebuilt exactly (zero renders) and
checked against the stored `mix-t3` features, mono duplicated to two channels at 44.1 kHz. Target: the wet target
render as it sits in that mix (the mix gain; a mastered mix's compressor gain curve and make-up, without the clip).

**Cross-fitting.** F5's 59 sections split into two halves within each band (seed 20261110). Fold k fine-tunes on half
k less 3 validation sections (seed 20261111) and separates half 1 - k, so every F5 stem D trains on comes from a model
that never saw its section, as FS5's and V-real's stems do. FS5 sections and V-real parts are assigned to a fold
(seeds 20261110, 20261113). FS5 and V-real never train or choose anything in the fine-tune.

**Stopping on evidence.** Validation every 250 steps: the band mean of the mean SNR of the full 10-s validation
examples against their wet targets, step 0 the stock weights. Stop when it has not improved by 0.1 dB for 1,000 steps
(not before 500), or at the approved time: 5.5 h of the gate's measured step time per fold (11 h in all).

**The MPS gate** first: on 3-, 6- and 10-s examples against an all-CPU step, the loss within 1e-4 relative and each
trainable group's gradient cosine at least 0.999; fallbacks in order: the STFTs and iSTFT on the CPU, then also the
loss on the CPU, then all on the CPU (the step maximum recomputed).

**The readout,** as step (a)'s: R0 on FS5 (zero renders, descriptive, no stop rule), the tone probe on the new stems,
then V-real-11 (frozen, the drift check). D_F5ft is D_F5-noaug with the fine-tuned stem in place of the stock stem:
D_F5ft - D_F5-noaug is primary; D_F5ft - D_F5mix and - D_F5 beside.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import pathlib
import random
import time

from learn import full_space as F
from learn import trusted_data as T
from learn import trusted_data_t3 as T3
from learn import trusted_data_t3_mix as TM
from learn import trusted_data_t3_r as R
from learn import verify_tracks as V

OUT_DIR = "t3-xlft"                                  # trusted-data/t3-xlft/: never under t3/ or t3-mix/
FT_ARM = "D_F5ft"
FT_KIND = "xlance_ft-t3"                             # the fine-tuned stem's half features, as T3's xlance_g-t3
LEDGER_KEY = "amendment_4"
LEDGER_MARK = "X-LANCE fine-tune (ROADMAP (b))"
DESIGN = ("docs/trusted-data-t0-design.md#d_f5ft-the-every-control-model-fed-the-fine-tuned-stem-roadmap-step-b-"
          "declared-2026-10-27-nothing-run")
STATUS = ("declared 2026-10-27 before any fine-tune or training (ledger trusted-data-t3, amendment 4); approved by the "
          "user 2026-10-27; V-real read again after F5, R1 and step (a)")
INPUT = ("the full twin's stem from the cross-fitted fine-tuned gtr_mss (xlance_ft-t3) through D_F5's D_stem input; "
         "augmentation off (as D_F5-noaug)")

FOLDS = (0, 1)
FOLD_SEED, VAL_SEED, WINDOW_SEED, VREAL_SEED = 20261110, 20261111, 20261112, 20261113
VAL_SECTIONS = 3                                     # per fold, from distinct bands
VAL_MAX = 120                                        # validation examples per fold (a seeded subset)
CONTROL_PER_SECTION = 1                              # the stock-weights pipeline control: one FS5 example per section
TRAIN_LAYERS = (8, 9, 10, 11)
TRAINABLE_PREFIXES = tuple(f"layers.{k}." for k in TRAIN_LAYERS) + ("final_norm.", "mask_estimators.")
LR, BETAS, WEIGHT_DECAY, WARMUP = 2e-5, (0.8, 0.99), 0.0, 100
WINDOW_S, ACCUM, CLIP_NORM = 6.0, 2, 5.0
SILENT_DBFS = -50.0                                  # a window whose target RMS is below this is redrawn
CHECK_EVERY, PATIENCE, MIN_GAIN_DB, MIN_STEPS = 250, 1000, 0.1, 500
BUDGET_H = 5.5                                       # per fold: the approved 11 h in all
WALL_FACTOR = 1.25                                   # the wall guard over the budget (validation and saves included)
GATE_LENGTHS_S = (3.0, 6.0, 10.0)
GATE_LOSS_RTOL, GATE_COS, GATE_MEM_GB = 1e-4, 0.999, 20.0
GATE_TIMED_STEPS = 5
MODES = ("mps", "fft_cpu", "fft_loss_cpu", "cpu")    # in order: the first that passes trains
CPU_THREADS = 8
RENDERS_PER_GROUP = 1 + 2                            # 1 priming at S + 1 arm x 2 directions
XL_SR = 44_100

_save, _load = V._save, V._load


# --- pure: folds, windows, the schedule and the stop rule ----------------------------------------------------------

def _rng(*key):
    from learn import pretrain_set as PS

    return random.Random(PS.seed_int(*key))


def alternate(items, rng, start=0):
    """Shuffle `items` (sorted first) with `rng` and deal them alternately to folds 0 and 1 from `start`.
    -> {item: fold}."""
    xs = sorted(items)
    rng.shuffle(xs)
    return {x: (start + n) % 2 for n, x in enumerate(xs)}


def section_folds(sections_by_band, seed=FOLD_SEED):
    """F5's sections in two halves within each band: {section: fold}. Bands deal from alternating folds (by sorted
    band) so an odd band's extra section does not always land in fold 0."""
    out = {}
    for n, band in enumerate(sorted(sections_by_band)):
        out.update(alternate(sections_by_band[band], _rng(seed, "f5", band), start=n % 2))
    return out


def val_sections(fold_of, band_of, fold, seed=VAL_SEED, n=VAL_SECTIONS):
    """Fold `fold`'s validation sections: one from each of `n` distinct bands (a seeded band order), drawn from the
    fold's own half. -> sorted list."""
    rng = _rng(seed, fold)
    bands = sorted({band_of[s] for s, f in fold_of.items() if f == fold})
    rng.shuffle(bands)
    out = []
    for b in bands[:n]:
        secs = sorted(s for s, f in fold_of.items() if f == fold and band_of[s] == b)
        if len(secs) > 1:                                   # never a band's only section in this half
            out.append(rng.choice(secs))
    return sorted(out)


def fs5_folds(sections_by_band, seed=FOLD_SEED):
    """FS5's sections assigned to the fold whose model separates them: {section: fold} (both models never saw them)."""
    out = {}
    for n, band in enumerate(sorted(sections_by_band)):
        out.update(alternate(sections_by_band[band], _rng(seed, "fs5", band), start=n % 2))
    return out


def vreal_folds(slugs, seed=VREAL_SEED):
    return alternate(slugs, _rng(seed, "vreal"))


def sep_jobs(fold, f5_ids, fs_ids, section_of, fold_of, fs_fold_of):
    """The examples fold `fold`'s model separates: F5's of the other half (out of fold) and FS5's assigned to it."""
    return ([i for i in f5_ids if fold_of[section_of[i]] != fold]
            + [i for i in fs_ids if fs_fold_of[section_of[i]] == fold])


def step_limits(step_s, budget_h=BUDGET_H, min_steps=MIN_STEPS):
    """(maximum, minimum) optimizer steps: the budget over the gate's step time; the minimum is `min_steps` or half
    the maximum if smaller."""
    mx = int(math.floor(budget_h * 3600.0 / step_s))
    return mx, min(min_steps, mx // 2)


def lr_at(step, max_steps, lr=LR, warmup=WARMUP):
    """Linear warm-up over `warmup` steps, then cosine to 0 at `max_steps`."""
    if step < warmup:
        return lr * (step + 1) / warmup
    span = max(1, max_steps - warmup)
    return lr * 0.5 * (1.0 + math.cos(math.pi * min(1.0, (step - warmup) / span)))


def best_point(curve, min_gain=MIN_GAIN_DB):
    """(step, value) of the curve's best: a later point counts only if it beats the best so far by `min_gain`.
    curve: [(step, value)] in step order."""
    bs, bv = curve[0]
    for s, v in curve[1:]:
        if v > bv + min_gain:
            bs, bv = s, v
    return bs, bv


def plateau(curve, min_steps, patience=PATIENCE, min_gain=MIN_GAIN_DB):
    """True when the validation curve has not improved by `min_gain` for `patience` steps (and `min_steps` ran)."""
    step = curve[-1][0]
    return step >= min_steps and step - best_point(curve, min_gain)[0] >= patience


def window_start(n, w, rng):
    return rng.randrange(0, max(1, n - w + 1))


def band_mean(values, band_of):
    """The mean over bands of each band's mean. values: {id: float}; band_of: {id: band}."""
    by = {}
    for i, v in values.items():
        by.setdefault(band_of[i], []).append(v)
    return sum(sum(v) / len(v) for v in by.values()) / len(by) if by else None


def is_trainable(name):
    """The trained tensors. The rotary frequencies are one tensor shared by every layer (a frozen constant), so their
    aliases under layers 8-11 are left out."""
    return name.startswith(TRAINABLE_PREFIXES) and "rotary_embed" not in name


def cosine(a, b):
    import numpy as np

    a, b = np.asarray(a, np.float64).ravel(), np.asarray(b, np.float64).ravel()
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if not (np.isfinite(na) and np.isfinite(nb)) or na == 0.0 or nb == 0.0:
        return float("nan") if na != nb else 1.0
    return float(a @ b) / (na * nb)


def gate_ok(loss, ref_loss, cos_by_group, rtol=GATE_LOSS_RTOL, cmin=GATE_COS):
    """One gate comparison: the loss within `rtol` relative of the CPU's, every group's cosine at least `cmin`."""
    if not (math.isfinite(loss) and math.isfinite(ref_loss)):
        return False
    return abs(loss - ref_loss) <= rtol * abs(ref_loss) and all(math.isfinite(c) and c >= cmin
                                                                for c in cos_by_group.values())


def group_of(name):
    if name.startswith("mask_estimators."):
        return "mask estimator"
    if name.startswith("final_norm."):
        return "final norm"
    return "trunk " + name.split(".")[1]


# --- pure: the rebuild (the build's mix and the target as it sits in it) -----------------------------------------

def compress_parts(x, rng):
    """`song_aug.compress`, returning its output and the gain it applied before the clip:
    (y, g) with y == clip(x * g). Consumes `rng` exactly as `song_aug.compress`."""
    import numpy as np

    from learn import song_aug as SA

    ratio = rng.uniform(2, 4)
    thr = 10 * np.log10(np.mean(x ** 2) + 1e-12) + 3
    a_att, a_rel = np.exp(-1 / (0.010 * SA.SR)), np.exp(-1 / (0.100 * SA.SR))
    env = np.empty_like(x)
    e = 0.0
    for i, v in enumerate(x ** 2):
        a = a_att if v > e else a_rel
        e = a * e + (1 - a) * v
        env[i] = e
    db = 10 * np.log10(env + 1e-12)
    g = 10 ** (np.where(db > thr, (thr - db) * (1 - 1 / ratio), 0.0) / 20)
    y = x * g
    g = g * 10 ** ((SA.lufs(x) + rng.uniform(0, 4) - SA.lufs(y)) / 20)
    peak = 10 ** (-1 / 20)
    return np.clip(x * g, -peak, peak), g


def rebuild(y, others, stems_audio, x):
    """`trusted_data.self_built_mix`'s mix of one example and the target as it sits in it: the target render times
    the mix gain, and for a mastered mix times the compressor's gain curve and make-up (the clip, which cannot be split
    per source, left out). -> (mix, wet target, gains {gb, ga}, backing LUFS)."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import song_aug as SA

    y = np.asarray(y, np.float64)
    b = np.asarray(others, np.float64) + np.asarray(stems_audio, np.float64)
    lg, lb = float(SA.lufs(y)), float(SA.lufs(b))
    gb, ga = T.mix_gains(lg, lb, x["draw"])
    k = 10 ** (ga / 20)
    mix = (y + b * 10 ** (gb / 20)) * k
    tgt = y * k
    mastered, mrng = DS.master_draw(x["i"])
    if mastered != x["draw"]["mastered"]:
        raise SystemExit(f"{x['i']}: the mastering draw changed")
    if mastered:
        mix, g = compress_parts(mix, mrng)
        tgt = tgt * g
    return mix, tgt, {"gb": gb, "ga": ga}, lb


# --- paths, records, the ledger -------------------------------------------------------------------------------------

def out_dir(root):
    return pathlib.Path(root) / OUT_DIR


def ft_path(root, i):
    from learn import direct_stems as DS

    return DS.ex_path(out_dir(root), i, FT_KIND)


def cache_path(root, i):
    return out_dir(root) / "cache" / f"{int(i) // 1000:04d}" / f"{int(i):07d}.npy"


def ckpt_path(root, fold, which):
    return out_dir(root) / "ft" / f"fold{fold}-{which}.pt"


def ft_record_path(root, fold):
    return out_dir(root) / "ft" / f"fold{fold}.json"


def run_path(root, seed):
    return out_dir(root) / "runs" / f"{FT_ARM}-{seed}.json"


def vreal_stems_path(root):
    return out_dir(root) / "vreal" / "stems.json"


def ledger_declared():
    d = json.loads((V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == T3.LEDGER_ID), {})
    return LEDGER_MARK in str(e.get(LEDGER_KEY, ""))


def require_ft(args):
    T3.require_t3(args)
    if not args.smoke and not ledger_declared():
        raise SystemExit(f"the ledger's {T3.LEDGER_ID} has no {LEDGER_KEY} declaring '{LEDGER_MARK}': real runs refuse")


def step_a_done(root):
    """Step (a)'s outputs this step reads: its runs, fit, R0 and V-real report (`trusted_data_t3_mix`)."""
    od = TM.out_dir(root)
    rep = _load(od / "report.json") or {}
    return bool(rep) and all((od / f).exists() for f in ("fit.json", "r0.json")) and bool(rep.get("complete"))


def load_sets(root, smoke=False):
    """The frozen F5 and FS5 (step (a)'s drift check) with T2's examples and T3's render and build rows.
    -> dict."""
    plan, drift = TM.load_frozen(root, smoke)
    f5, fs, refused, _ = T3.t3_sets(root, plan)
    t2 = _load(T.plan_path(root, "t2"))
    ex = {x["i"]: x for x in t2["examples"]}
    return {"plan": plan, "drift": drift, "f5": f5, "fs": fs, "refused": refused, "ex": ex,
            "section_of": {i: ex[i]["section"] for i in f5 + fs}, "band_of_ex": {i: ex[i]["band"] for i in f5 + fs},
            "rend": T.rows_of(root, T3.STAGE, "render"), "built": T.rows_of(root, T3.STAGE, "build"),
            "t2rend": T.rows_of(root, "t2", "render")}


def folds_of(S):
    """The cross-fit's folds from the frozen sets (deterministic): F5 section -> fold, FS5 section -> fold, each fold's
    validation sections, band of each section."""
    band_of = {S["section_of"][i]: S["band_of_ex"][i] for i in S["f5"] + S["fs"]}
    f5_secs, fs_secs = {}, {}
    for i in S["f5"]:
        f5_secs.setdefault(band_of[S["section_of"][i]], set()).add(S["section_of"][i])
    for i in S["fs"]:
        fs_secs.setdefault(band_of[S["section_of"][i]], set()).add(S["section_of"][i])
    fold_of = section_folds(f5_secs)
    if set(fold_of) & set().union(*fs_secs.values(), set()):
        raise SystemExit("an FS5 section is also an F5 section")
    return {"fold_of": fold_of, "fs_fold_of": fs5_folds(fs_secs), "band_of": band_of,
            "val": {k: val_sections(fold_of, band_of, k) for k in FOLDS}}


def fold_ids(S, Fd, fold):
    """(training ids, validation ids) of one fold's fine-tune: its half's F5 examples, the validation sections apart;
    validation at most VAL_MAX (a seeded subset)."""
    val_secs = set(Fd["val"][fold])
    mine = [i for i in S["f5"] if Fd["fold_of"][S["section_of"][i]] == fold]
    tr = [i for i in mine if S["section_of"][i] not in val_secs]
    va = sorted(i for i in mine if S["section_of"][i] in val_secs)
    if len(va) > VAL_MAX:
        va = sorted(_rng(VAL_SEED, fold, "subset").sample(va, VAL_MAX))
    return tr, va


def example_audio(root, S, stems, i):
    """(target render, other guitars, stems audio, T2's example) of one full twin, as T3's build read them."""
    from learn import direct_sound_gate as G

    x = S["ex"][i]
    o2 = S["t2rend"][i]["others_file"]
    oth = G.read_flac(T.flac_path(root, "t2", i, "others"), o2["scale"], o2["sha256"])
    voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
    st = stems.get(x["section"], T.backing_tracks(x, voc))
    tf = S["rend"][i]["target"]
    y = G.read_flac(T.flac_path(root, T3.STAGE, i, "target"), tf["scale"], tf["sha256"])
    return y, oth, st, x


def features_match(mix, stored_npz, prefix="m"):
    """The rebuilt signal's half features against the stored ones: (least match share, max |LUFS| difference)."""
    import numpy as np

    from learn import direct_stems as DS

    mm, ml, _ = DS.half_features(mix)
    d = np.load(stored_npz)
    share = min(DS.match_share(mm["A"], d[f"{prefix}A"]), DS.match_share(mm["B"], d[f"{prefix}B"]))
    return share, float(max(abs(ml["A"] - d["lufs"][0]), abs(ml["B"] - d["lufs"][1])))


# --- the model (msst-venv) -------------------------------------------------------------------------------------------

class _CpuFFT:
    """The model module's `torch` with stft and istft run on the CPU (gradients pass through the moves): the gate's
    first fallback, for the MPS STFT bug."""

    def __init__(self, torch):
        self._t = torch

    def __getattr__(self, k):
        return getattr(self._t, k)

    def _run(self, fn, x, *a, window=None, **k):
        dev = x.device
        if dev.type == "cpu":
            return fn(x, *a, window=window, **k)
        return fn(x.cpu(), *a, window=None if window is None else window.cpu(), **k).to(dev)

    def stft(self, x, *a, **k):
        return self._run(self._t.stft, x, *a, **k)

    def istft(self, x, *a, **k):
        return self._run(self._t.istft, x, *a, **k)


@contextlib.contextmanager
def fft_mode(model, on):
    """Route the model's STFTs through the CPU while inside (its forward's module globals; X-LANCE's modules are
    forgotten from sys.modules after loading, so the globals are reached through the class)."""
    import torch

    g = type(model).forward.__globals__
    old = g["torch"]
    if on:
        g["torch"] = _CpuFFT(torch)
    try:
        yield
    finally:
        g["torch"] = old


def own_loss(model, recon, target):
    """The model's own loss (`BSRoformer.forward` with a target): L1 waveform plus the multi-resolution STFT L1,
    computed wherever recon and target are (the gate's second fallback puts them on the CPU)."""
    import torch
    import torch.nn.functional as Fn

    target = target[..., :recon.shape[-1]]
    loss = Fn.l1_loss(recon, target)
    multi = 0.0
    for w in model.multi_stft_resolutions_window_sizes:
        kw = dict(n_fft=max(w, model.multi_stft_n_fft), win_length=w, return_complex=True,
                  window=model.multi_stft_window_fn(w, device=recon.device), **model.multi_stft_kwargs)
        ry = torch.stft(recon.reshape(-1, recon.shape[-1]), **kw)
        ty = torch.stft(target.reshape(-1, target.shape[-1]), **kw)
        multi = multi + Fn.l1_loss(ry, ty)
    return loss + multi * model.multi_stft_resolution_loss_weight


def step_loss(model, mode, mix, tgt):
    """One forward to the loss under a gate mode. mix, tgt: (1, 2, n) tensors on the model's device."""
    if mode in ("mps", "cpu"):
        return model(mix, target=tgt)
    with fft_mode(model, True):
        if mode == "fft_cpu":
            return model(mix, target=tgt)
        recon = model(mix)
    return own_loss(model, recon.cpu(), tgt.cpu())


def base_model(device):
    """Stock gtr_mss (hash-checked by `direct_stems.XLanceG`), its trainable set marked. -> (model, base sha256)."""
    from learn import direct_stems as DS

    xl = DS.XLanceG("cpu", threads=CPU_THREADS)
    m = xl.model.to(device)
    for n, p in m.named_parameters():
        p.requires_grad_(is_trainable(n))
    return m, xl.sha256


def trainable_state(model):
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items() if is_trainable(k)}


def load_trainable(model, state):
    """The fine-tuned trainable tensors into a stock model: every trainable key, nothing else."""
    want = {k for k in model.state_dict() if is_trainable(k)}
    if set(state) != want:
        raise SystemExit(f"the checkpoint's tensors are not the trainable set ({len(set(state) ^ want)} differ)")
    model.load_state_dict(state, strict=False)


def ft_separator(root, fold, device):
    """`direct_stems.XLanceG` (the build's path: mono 48 kHz, two equal channels at 44.1 kHz, crossfaded 10-s chunks,
    the channel mean, back to 48 kHz) with one fold's fine-tuned tensors, hash-checked against its record."""
    import torch

    from learn import direct_stems as DS

    rec = _load(ft_record_path(root, fold)) or {}
    cp = ckpt_path(root, fold, "best")
    if rec.get("status") != "done" or DS.hashlib_file(cp) != rec.get("best_sha256"):
        raise SystemExit(f"fold {fold}: no finished fine-tune, or its best checkpoint changed")
    sep = DS.XLanceG(device, threads=DS.THREADS if device == "cpu" else 2)
    load_trainable(sep.model, torch.load(cp, map_location="cpu")["state"])
    sep.model.eval()
    sep.setting = f"gtr_mss fine-tuned, fold {fold}"
    sep.ft = {"fold": fold, "best_sha256": rec["best_sha256"], "best_step": rec.get("best_step")}
    return sep


# --- check (MAIN; writes nothing) -------------------------------------------------------------------------------------

def cmd_check(args):
    from learn import pretrain_set as PS

    require_ft(args)
    root = V.out_root(args)
    if not step_a_done(root) and not args.smoke:
        raise SystemExit("step (a)'s report is missing or incomplete (t3-mix/): D_F5ft is read against it")
    S = load_sets(root, args.smoke)
    Fd = folds_of(S)
    for k in FOLDS:
        tr, va = fold_ids(S, Fd, k)
        jobs = sep_jobs(k, S["f5"], S["fs"], S["section_of"], Fd["fold_of"], Fd["fs_fold_of"])
        print(f"fold {k}: fine-tune on {len(tr)} ({len({S['section_of'][i] for i in tr})} sections), validate on "
              f"{len(va)} ({Fd['val'][k]}); separates {len(jobs)}", flush=True)
    free = PS.free_gb()
    need = 2 * 2 * len(S["f5"]) * XL_SR * PS.SEC_S / 1e9 + 1.5     # the fp16 cache (mix, target); checkpoints, stems
    print(f"disk: {free:.0f} GB free; this step writes about {need:.1f} GB; guard {T.DISK_GUARD_GB:.0f} GB")
    if free - need < T.DISK_GUARD_GB and not args.smoke:
        raise SystemExit("not enough disk above the guard")
    print(f"CHECK OK ({STATUS})")


# --- prep (MSST): folds, the rebuilt cache and its checks -------------------------------------------------------------

_W = {}


def _init_worker(root):
    from learn import direct_stems as DS

    ctx = DS.Ctx(quiet=True)
    ctx.rows = None
    _W.update(root=root, S=load_sets(root), stems=T.Stems(ctx))


def _prep_one(i):
    """Rebuild one F5 example, check it against the stored mix features, cache (mix, wet target) at 44.1 kHz fp16."""
    import numpy as np

    from learn import separator_screen as SCR

    root, S = _W["root"], _W["S"]
    y, oth, st, x = example_audio(root, S, _W["stems"], i)
    mix, tgt, gains, lb = rebuild(y, oth, st, x)
    share, dl = features_match(mix, T.ex_path(root, T3.STAGE, i, f"mix-{T3.STAGE}"))
    p = cache_path(root, i)
    if not p.exists():
        a = np.stack([SCR.to44(mix), SCR.to44(tgt)]).astype(np.float16)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.stem + f".{os.getpid()}.tmp.npy")
        np.save(tmp, a)
        tmp.replace(p)
    return i, share, dl, gains["ga"]


def cmd_prep(args):
    """The folds (recorded), every F5 example's mix and wet target rebuilt (zero renders) and checked against the stored
    `mix-t3` features, cached; then the stock-weights pipeline control: one FS5 example per section separated by the
    build's path on the device its stored stem was made on, against the stored `xlance_g-t3` features."""
    from multiprocessing import Pool

    from learn import direct_stems as DS

    require_ft(args)
    root = V.out_root(args)
    S = load_sets(root, args.smoke)
    Fd = folds_of(S)
    fp = out_dir(root) / "folds.json"
    rec = {"seeds": {"folds": FOLD_SEED, "validation": VAL_SEED, "vreal": VREAL_SEED},
           "f5_fold_of": Fd["fold_of"], "fs5_fold_of": Fd["fs_fold_of"], "val": {str(k): v for k, v in Fd["val"].items()}}
    old = _load(fp)
    if old and TM.canon({k: old[k] for k in rec}) != TM.canon(rec):
        raise SystemExit("folds.json differs from today's folds: the frozen sets moved")
    _save(fp, {**rec, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    t0 = time.time()
    todo = sorted(S["f5"], key=lambda i: (S["section_of"][i], i))[:args.limit or None]
    bad = []
    with Pool(args.workers, initializer=_init_worker, initargs=(root,)) as pool:
        for n, (i, share, dl, _) in enumerate(pool.imap(_prep_one, todo, chunksize=8)):
            if share < DS.MATCH_SHARE:
                bad.append((i, share, dl))
            if (n + 1) % 250 == 0:
                print(f"prep {n + 1}/{len(todo)}: {time.time() - t0:.0f} s; {len(bad)} not reproduced", flush=True)
    if bad and not args.smoke:
        raise SystemExit(f"{len(bad)} rebuilt mixes do not reproduce the stored mix-t3 features: {bad[:5]}")
    control = pipeline_control(root, S, args.smoke)
    _save(out_dir(root) / "prep.json", {"design": DESIGN, "status": STATUS, "cached": len(todo), "not_reproduced": bad,
                                        "control": control, "drift": S["drift"], "smoke": bool(args.smoke),
                                        "minutes": round((time.time() - t0) / 60, 1),
                                        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"PREP DONE: {len(todo)} cached, all reproduce the stored mixes; control {control['ok']}")


def pipeline_control(root, S, smoke=False):
    """Stock gtr_mss through this module's rebuild and the build's path reproduces T3's stored stems (one FS5 example
    per section, on its stored device). -> record with "ok"; refuses unless every one matches."""
    import numpy as np

    from learn import direct_stems as DS

    ctx = DS.Ctx(quiet=True)
    ctx.rows = None
    stems, seps, rows = T.Stems(ctx), {}, []
    first = {}
    for i in sorted(S["fs"]):
        first.setdefault(S["section_of"][i], i)
    for sec, i in sorted(first.items()):
        dev = S["built"][i].get("device") or "cpu"
        if dev not in seps:
            seps[dev] = DS.stem_separator(T.SEP, dev)
        y, oth, st, x = example_audio(root, S, stems, i)
        mix, _, _, _ = rebuild(y, oth, st, x)
        s = np.asarray(seps[dev](mix), np.float64)
        share, dl = features_match(s, T.ex_path(root, T3.STAGE, i, f"{T.SEP}-{T3.STAGE}"), prefix="s")
        rows.append({"i": i, "section": sec, "device": dev, "stem_share": share, "lufs_diff": dl})
        print(f"control {i} ({sec}, {dev}): stem share {share:.4f}", flush=True)
    ok = all(r["stem_share"] >= DS.MATCH_SHARE for r in rows)
    if not ok and not smoke:
        raise SystemExit(f"the stock pipeline does not reproduce T3's stored stems: {rows}")
    return {"rows": rows, "ok": ok, "rule": f"every stem share >= {DS.MATCH_SHARE}"}


# --- gate (MSST) ------------------------------------------------------------------------------------------------------

def load_window(root, i, start, n):
    """(mix, wet target) tensors (1, 2, n), mono duplicated, from the fp16 cache."""
    import numpy as np
    import torch

    a = np.load(cache_path(root, i), mmap_mode="r")[:, start:start + n].astype(np.float32)
    m, t = torch.from_numpy(np.stack([a[0], a[0]]))[None], torch.from_numpy(np.stack([a[1], a[1]]))[None]
    return m, t


def grads_by_group(model):
    import numpy as np

    out = {}
    for n, p in model.named_parameters():
        if p.requires_grad:
            g = np.zeros(p.numel()) if p.grad is None else p.grad.detach().float().cpu().numpy().ravel()
            out.setdefault(group_of(n), []).append(g)
    return {k: np.concatenate(v) for k, v in out.items()}


def peak_gb(dev):
    import resource

    import torch

    if dev.type == "mps":
        return torch.mps.driver_allocated_memory() / 1e9
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9       # macOS: bytes


def cmd_gate(args):
    """The MPS gate (zero renders): stock weights, dropout off, on three cached F5 training examples (one per length:
    3, 6, 10 s) against an all-CPU forward and backward; the first mode in MODES that passes every comparison trains
    (all-CPU last). Then that mode's optimizer step time and peak memory at the training batch."""
    import copy

    import torch

    require_ft(args)
    root = V.out_root(args)
    if not (_load(out_dir(root) / "prep.json") or {}).get("control", {}).get("ok") and not args.smoke:
        raise SystemExit("run `prep` first (its control must pass)")
    S = load_sets(root, args.smoke)
    Fd = folds_of(S)
    tr, _ = fold_ids(S, Fd, 0)
    ids = sorted(tr)[:len(GATE_LENGTHS_S)]
    torch.set_num_threads(CPU_THREADS)
    ref_m, base_sha = base_model("cpu")
    ref_m.eval()
    refs = []
    for i, L in zip(ids, GATE_LENGTHS_S):
        mix, tgt = load_window(root, i, 0, int(L * XL_SR))
        ref_m.zero_grad(set_to_none=True)
        loss = ref_m(mix, target=tgt)
        loss.backward()
        refs.append((i, L, mix, tgt, float(loss), grads_by_group(ref_m)))
    results, chosen = [], "cpu"
    mps = torch.backends.mps.is_available()
    for mode in MODES[:-1]:
        if not mps:
            results.append({"mode": mode, "ok": False, "why": "MPS is not available"})
            continue
        m = copy.deepcopy(ref_m).to("mps")
        ok, rows = True, []
        for i, L, mix, tgt, rl, rg in refs:
            m.zero_grad(set_to_none=True)
            try:
                loss = step_loss(m, mode, mix.to("mps"), tgt.to("mps"))
                loss.backward()
                cos = {g: cosine(v, rg[g]) for g, v in grads_by_group(m).items()}
                lv = float(loss)
            except Exception as e:                       # noqa: BLE001  (a mode that errors fails the gate)
                rows.append({"i": i, "seconds": L, "error": repr(e)[:300]})
                ok = False
                break
            r_ok = gate_ok(lv, rl, cos)
            rows.append({"i": i, "seconds": L, "loss": lv, "cpu_loss": rl, "cosine": cos, "ok": r_ok})
            ok = ok and r_ok
        results.append({"mode": mode, "ok": ok, "rows": rows})
        print(f"gate {mode}: {'pass' if ok else 'fail'} {rows}", flush=True)
        del m
        torch.mps.empty_cache()
        if ok:
            chosen = mode
            break
    dev = torch.device("cpu" if chosen == "cpu" else "mps")
    step_s, peak = time_steps(root, tr, chosen, dev)
    if dev.type == "mps" and peak >= GATE_MEM_GB:
        results.append({"mode": chosen, "ok": False, "why": f"peak memory {peak:.1f} GB at the training batch"})
        chosen, dev = "cpu", torch.device("cpu")
        step_s, peak = time_steps(root, tr, chosen, dev)
    mx, mn = step_limits(step_s)
    rec = {"design": DESIGN, "status": STATUS, "base_sha256": base_sha, "mode": chosen, "results": results,
           "step_seconds": step_s, "peak_gb": peak, "max_steps": mx, "min_steps": mn, "budget_h": BUDGET_H,
           "rule": f"loss within {GATE_LOSS_RTOL} relative, gradient cosine >= {GATE_COS} per trainable group; "
                   f"peak memory under {GATE_MEM_GB:.0f} GB", "smoke": bool(args.smoke),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(out_dir(root) / "gate.json", rec)
    print(f"GATE DONE: mode {chosen}; {step_s:.2f} s per step; peak {peak:.1f} GB; steps {mn}-{mx} per fold")


def time_steps(root, ids, mode, dev):
    """(seconds per optimizer step, peak GB) over GATE_TIMED_STEPS steps after one untimed, in training mode."""
    import torch

    m, _ = base_model(dev)
    m.train()
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=LR, betas=BETAS,
                            weight_decay=WEIGHT_DECAY)
    rng = _rng(WINDOW_SEED, "gate")
    n = int(WINDOW_S * XL_SR)
    peak, t = 0.0, None
    for s in range(GATE_TIMED_STEPS + 1):
        if s == 1:
            t = time.time()
        opt.zero_grad(set_to_none=True)
        for _ in range(ACCUM):
            i = rng.choice(ids)
            mix, tgt = load_window(root, i, window_start(int(10 * XL_SR), n, rng), n)
            (step_loss(m, mode, mix.to(dev), tgt.to(dev)) / ACCUM).backward()
        opt.step()
        if dev.type == "mps":
            torch.mps.synchronize()
        peak = max(peak, peak_gb(dev))
    dt = (time.time() - t) / GATE_TIMED_STEPS
    del m, opt
    if dev.type == "mps":
        torch.mps.empty_cache()
    return dt, peak


# --- train (MSST): one cross-fitted fine-tune ------------------------------------------------------------------------

def validate(model, root, ids, band_of, dev):
    """The band mean of mean SNR (dB) over the full 10-s validation examples against their wet targets (inference,
    the channel mean), and per example."""
    import numpy as np
    import torch

    from learn import direct_stems as DS

    model.eval()
    per = {}
    with torch.no_grad():
        for i in ids:
            a = np.load(cache_path(root, i)).astype(np.float32)
            x = torch.from_numpy(np.stack([a[0], a[0]]))[None].to(dev)
            est = model(x)[0].float().cpu().numpy().mean(0)
            k = min(len(est), a.shape[1])
            per[i] = DS.snr_db(est[:k], a[1][:k])
    model.train()
    return band_mean(per, band_of), per


def clip_grads(params, max_norm=CLIP_NORM):
    """Global-norm clipping computed on the CPU (MPS's clip_grad_norm_ has returned NaN here). -> the norm (NaN or
    inf: the caller skips the step)."""
    import torch

    tot = 0.0
    for p in params:
        if p.grad is not None:
            tot += float(p.grad.detach().float().pow(2).sum().cpu())
    norm = math.sqrt(tot) if math.isfinite(tot) else float("nan")
    if math.isfinite(norm) and norm > max_norm:
        with torch.no_grad():
            for p in params:
                if p.grad is not None:
                    p.grad.mul_(max_norm / (norm + 1e-6))
    return norm


def cmd_train(args):
    """One fold's fine-tune (MSST): the gate's mode and step limits; validation every CHECK_EVERY steps from step 0
    (stock weights); best and last checkpoints (trainable tensors); a killed run resumes from its last checkpoint
    (recorded). Stops at the plateau, the step maximum or the wall guard."""
    import torch

    from learn import direct_stems as DS

    require_ft(args)
    root = V.out_root(args)
    if args.fold not in FOLDS:
        raise SystemExit(f"--fold in {FOLDS}")
    gate = _load(out_dir(root) / "gate.json")
    if not gate or (gate.get("smoke") and not args.smoke):
        raise SystemExit("run `gate` first")
    rp = ft_record_path(root, args.fold)
    rec = _load(rp) or {}
    if rec.get("status") == "done":
        print(f"fold {args.fold}: done (best step {rec['best_step']})")
        return
    S = load_sets(root, args.smoke)
    Fd = folds_of(S)
    tr, va = fold_ids(S, Fd, args.fold)
    band_of = {i: S["band_of_ex"][i] for i in va}
    mode = gate["mode"]
    dev = torch.device("cpu" if mode == "cpu" else "mps")
    torch.set_num_threads(CPU_THREADS if mode == "cpu" else 2)
    torch.manual_seed(_rng(WINDOW_SEED, args.fold, "torch").randrange(2 ** 31))
    mx, mn = (gate["max_steps"], gate["min_steps"]) if not args.smoke else (args.smoke_steps, 1)
    model, base_sha = base_model(dev)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR, betas=BETAS, weight_decay=WEIGHT_DECAY)
    lp = ckpt_path(root, args.fold, "last")
    lp.parent.mkdir(parents=True, exist_ok=True)
    step, curve, resumed, skipped = 0, [], rec.get("resumed", []), rec.get("skipped_steps", 0)
    if lp.exists() and rec.get("curve"):
        ck = torch.load(lp, map_location="cpu")
        load_trainable(model, ck["state"])
        opt.load_state_dict(ck["opt"])
        step, curve = ck["step"], [tuple(c) for c in rec["curve"]]
        resumed.append({"at_step": step, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"fold {args.fold}: resumed at step {step}", flush=True)
    rng = _rng(WINDOW_SEED, args.fold, "windows", step)
    n = int(WINDOW_S * XL_SR)
    swap0 = DS.swap_mb()
    t0 = time.time()
    wall0 = time.time() - rec.get("train_seconds", 0.0)
    rec.update({"design": DESIGN, "status": "running", "fold": args.fold, "mode": mode, "device": str(dev),
                "base_sha256": base_sha, "train": len(tr), "validation": len(va), "validation_sections": Fd["val"][args.fold],
                "train_sections": sorted({S["section_of"][i] for i in tr}), "max_steps": mx, "min_steps": mn,
                "trainable": sum(p.numel() for p in params), "resumed": resumed,
                "recipe": {"lr": LR, "betas": BETAS, "weight_decay": WEIGHT_DECAY, "warmup": WARMUP, "window_s": WINDOW_S,
                           "accumulate": ACCUM, "clip": CLIP_NORM, "layers": TRAIN_LAYERS}, "smoke": bool(args.smoke)})

    def check(step):
        v, _ = validate(model, root, va, band_of, dev)
        curve.append((step, v))
        bs, bv = best_point(curve)
        if bs == step:
            torch.save({"state": trainable_state(model), "step": step}, ckpt_path(root, args.fold, "best"))
        torch.save({"state": trainable_state(model), "opt": opt.state_dict(), "step": step}, lp)
        rec.update(curve=curve, best_step=bs, best_db=bv, step=step, skipped_steps=skipped,
                   train_seconds=time.time() - wall0, time=time.strftime("%Y-%m-%d %H:%M:%S"))
        _save(rp, rec)
        print(f"fold {args.fold} step {step}: validation {v:.3f} dB (best {bv:.3f} at {bs}); "
              f"{(time.time() - t0) / 60:.0f} min", flush=True)

    if not curve:
        check(0)
    model.train()
    why = None
    bad_run = 0
    while why is None:
        for g in opt.param_groups:
            g["lr"] = lr_at(step, mx)
        opt.zero_grad(set_to_none=True)
        for _ in range(ACCUM):
            for _try in range(20):
                i = rng.choice(tr)
                mix, tgt = load_window(root, i, window_start(int(10 * XL_SR), n, rng), n)
                if 20 * math.log10(float(tgt.pow(2).mean().sqrt()) + 1e-12) >= SILENT_DBFS:
                    break
            (step_loss(model, mode, mix.to(dev), tgt.to(dev)) / ACCUM).backward()
        norm = clip_grads(params)
        if math.isfinite(norm):
            opt.step()
            bad_run = 0
        else:
            skipped += 1
            bad_run += 1
            if bad_run >= 10:
                rec.update(status="failed", why="10 non-finite gradients in a row")
                _save(rp, rec)
                raise SystemExit(f"TRAIN FAILED fold {args.fold}: 10 non-finite gradients in a row")
        step += 1
        if step % CHECK_EVERY == 0 or step >= mx:
            g = DS._guards("xlft-train", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            check(step)
            if step >= mx:
                why = "the step maximum (the approved time)"
            elif plateau(curve, mn):
                why = f"plateau: no {MIN_GAIN_DB} dB gain for {PATIENCE} steps"
            elif time.time() - wall0 > WALL_FACTOR * BUDGET_H * 3600 and not args.smoke:
                why = "the wall guard"
    bs, bv = best_point(curve)
    rec.update(status="done", stopped=why, best_step=bs, best_db=bv, stock_db=curve[0][1],
               at_cap_improving=why != f"plateau: no {MIN_GAIN_DB} dB gain for {PATIENCE} steps" and bs == curve[-1][0],
               best_sha256=DS.hashlib_file(ckpt_path(root, args.fold, "best")), minutes=round((time.time() - t0) / 60, 1))
    _save(rp, rec)
    print(f"TRAIN DONE fold {args.fold}: {why}; best {bv:.3f} dB at step {bs} (stock {curve[0][1]:.3f} dB)")
    if rec["at_cap_improving"]:
        print(f"NOTE: fold {args.fold} was still improving when it stopped ({why}); an extension needs the user's yes")


# --- separate (MSST): the out-of-fold stems ---------------------------------------------------------------------------

def cmd_separate(args):
    """Fold k's model separates its examples (`sep_jobs`), each mix rebuilt exactly as T3's build made it; half
    features saved as `xlance_ft-t3` (as T3's `xlance_g-t3`), one row per example with the new stem's SNR against the
    wet target and T3's stored one. Two workers per fold (mps ascending, cpu descending) skip what exists."""
    import numpy as np

    from learn import direct_stems as DS

    require_ft(args)
    root = V.out_root(args)
    S = load_sets(root, args.smoke)
    Fd = folds_of(S)
    jobs = sep_jobs(args.fold, S["f5"], S["fs"], S["section_of"], Fd["fold_of"], Fd["fs_fold_of"])
    jobs = sorted(jobs, key=lambda i: (S["section_of"][i], i), reverse=args.order == "desc")
    jobs = [i for i in jobs if not ft_path(root, i).exists()][:args.limit or None]
    print(f"separate fold {args.fold} on {args.device}: {len(jobs)} to do", flush=True)
    if not jobs:
        print(f"SEPARATE DONE fold {args.fold} ({args.device})")
        return
    sep = ft_separator(root, args.fold, args.device)
    ctx = DS.Ctx(quiet=True)
    ctx.rows = None
    stems = T.Stems(ctx)
    swap0 = DS.swap_mb()
    rp = out_dir(root) / "rows" / f"sep-{args.fold}-{args.device}-{os.getpid()}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    fs = set(S["fs"])
    t0 = time.time()
    with open(rp, "a") as fh:
        for m, i in enumerate(jobs):
            g = DS._guards("xlft-separate", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            if ft_path(root, i).exists():
                continue                                    # the other worker's
            y, oth, st, x = example_audio(root, S, stems, i)
            mix, tgt, gains, _ = rebuild(y, oth, st, x)
            s = np.asarray(sep(mix), np.float64)
            if len(s) != len(mix) or not np.isfinite(s).all():
                raise SystemExit(f"{i}: bad stem")
            sm, sl, floor = DS.half_features(s)
            DS._save_npz(ft_path(root, i), sA=sm["A"], sB=sm["B"], lufs=[sl["A"], sl["B"]])
            row = {"i": i, "set": "fs5" if i in fs else "f5", "section": S["section_of"][i], "band": S["band_of_ex"][i],
                   "fold": args.fold, "section_fold": (Fd["fs_fold_of"] if i in fs else Fd["fold_of"])[S["section_of"][i]],
                   "device": args.device, "ckpt": sep.ft["best_sha256"], "lufs_sA": sl["A"], "lufs_sB": sl["B"],
                   "floor_share": floor, "snr_audio_db": DS.snr_db(s, y * 10 ** (gains["ga"] / 20)),
                   "snr_wet_db": DS.snr_db(s, tgt), "snr_stock_db": S["built"][i].get("snr_audio_db")}
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if m % 50 == 0:
                print(f"separate {m + 1}/{len(jobs)}: {(time.time() - t0) / (m + 1):.1f} s per example", flush=True)
    print(f"SEPARATE DONE fold {args.fold} ({args.device})")


def sep_rows(root):
    from learn import direct_stems as DS

    out = {}
    for f in sorted((out_dir(root) / "rows").glob("sep-*.jsonl")):
        for r in DS.read_jsonl(f):
            out[r["i"]] = r
    return out


def stems_complete(root, S, Fd):
    """Every F5 and FS5 example has its fine-tuned stem, made by the fold assigned to it (out of fold for F5).
    -> list of problems."""
    rows = sep_rows(root)
    f5, fs = set(S["f5"]), set(S["fs"])
    bad = []
    for i in S["f5"] + S["fs"]:
        r = rows.get(i)
        sec = S["section_of"][i]
        if r is None or not ft_path(root, i).exists():
            bad.append((i, "no stem"))
        elif i in f5 and r["fold"] == Fd["fold_of"][sec]:
            bad.append((i, "in-fold stem"))
        elif i in fs and r["fold"] != Fd["fs_fold_of"][sec]:
            bad.append((i, "FS5 stem from the other fold"))
    return bad


# --- V-real stems (MSST) -------------------------------------------------------------------------------------------

def vreal_mix_wav(slug, info):
    from learn import arm_a_mega53 as A

    crop = A.f_part(slug)["crop"] if info["kind"] == "stagef" else info["crop"]
    return pathlib.Path(crop) / "mix.wav"


def cmd_vreal_stems(args):
    """V-real-11's crop mixes (the same `mix.wav` their stored xlance_g stems were made from) through their assigned
    fold's model (`vreal_folds`); stored and hash-recorded; a recorded stem never changes."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import direct_stems as DS

    require_ft(args)
    root = V.out_root(args)
    plan, _ = TM.load_frozen(root, args.smoke)
    f5pred, _ = TM.f5_predictions(root, plan, args.smoke)
    _, parts, _ = T3.vreal_dirs(root, plan, bool(f5pred.get("dropped_members")))
    fold_of = vreal_folds(list(parts))
    mp = vreal_stems_path(root)
    man = _load(mp) or {"design": DESIGN, "folds": fold_of, "stems": {}}
    if man["folds"] != fold_of:
        raise SystemExit("V-real's fold assignment changed")
    seps = {}
    for slug in sorted(parts):
        if slug in man["stems"]:
            e = man["stems"][slug]
            if DS.hashlib_file(e["path"]) != e["sha256"]:
                raise SystemExit(f"{slug}: its stored stem changed since it was recorded")
            continue
        k = fold_of[slug]
        if k not in seps:
            seps[k] = ft_separator(root, k, args.device)
        wav = vreal_mix_wav(slug, parts[slug])
        x = CR.mono(wav)
        s = np.asarray(seps[k](x), np.float32)
        if len(s) != len(x) or not np.isfinite(s).all():
            raise SystemExit(f"{slug}: bad stem")
        p = mp.parent / "stems" / f"{slug}.npy"
        p.parent.mkdir(parents=True, exist_ok=True)
        np.save(p.with_suffix(".tmp.npy"), s)
        p.with_suffix(".tmp.npy").replace(p)
        man["stems"][slug] = {"path": str(p), "sha256": DS.hashlib_file(p), "fold": k, "device": args.device,
                              "mix_wav": str(wav), "mix_sha256": DS.hashlib_file(wav), "ckpt": seps[k].ft["best_sha256"]}
        _save(mp, man)
        print(f"vreal stem {slug}: fold {k}", flush=True)
    print(f"VREAL STEMS DONE: {len(man['stems'])} of {len(parts)}")


def vreal_ft_stem(root, slug):
    import numpy as np

    from learn import direct_stems as DS

    e = (_load(vreal_stems_path(root)) or {}).get("stems", {}).get(slug)
    if not e:
        raise SystemExit(f"{slug}: no fine-tuned V-real stem (run `vreal-stems`)")
    if DS.hashlib_file(e["path"]) != e["sha256"]:
        raise SystemExit(f"{slug}: its fine-tuned stem changed since it was recorded")
    return np.load(e["path"]).astype(np.float64), e["sha256"]


# --- D_F5ft: train, fit, r0 (TORCH_PY) --------------------------------------------------------------------------------

def ft_files(root, ids):
    """(mix, fine-tuned stem) feature files: the mix is the full twin's stored `mix-t3` (D_stem reads the mix's slots
    too, as D_F5 and D_F5-noaug do)."""
    return {i: (str(T.ex_path(root, T3.STAGE, i, f"mix-{T3.STAGE}")), str(ft_path(root, i))) for i in ids}


def load_ft_models(root, smoke=False):
    import torch

    nets, recs = [], []
    for s in T3.TRAIN_SEEDS:
        rec = _load(run_path(root, s))
        if not rec or (rec.get("smoke") and not smoke):
            raise SystemExit(f"{FT_ARM} seed {s} has no run")
        net = F.build_net()
        net.load_state_dict(torch.load(run_path(root, s).with_suffix(".pt"), map_location="cpu"))
        net.eval()
        nets.append(net)
        recs.append(rec)
    return nets, recs


def cmd_train_d(args):
    """One D_F5ft run: D_F5-noaug's recipe (D_F5's, augmentation off) with the fine-tuned stems; early stopping on FS5.
    Refuses unless every stem is in place and out of fold, and its examples are D_F5's."""
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import pretrain_set as PS

    require_ft(args)
    root = V.out_root(args)
    if args.seed not in T3.TRAIN_SEEDS and not args.smoke:
        raise SystemExit(f"--seed in {T3.TRAIN_SEEDS}")
    rp = run_path(root, args.seed)
    if rp.exists():
        print(f"{rp.name} exists: nothing to do")
        return
    S = load_sets(root, args.smoke)
    bad = stems_complete(root, S, folds_of(S))
    if bad and not args.smoke:
        raise SystemExit(f"{len(bad)} fine-tuned stems missing or not out of fold: {bad[:5]}")
    ctx = DS.Ctx(quiet=True)
    tr_rows, es_rows = T3.arm_rows(root, ctx, S["plan"], T3.FULL)
    why = TM.same_examples(_load(T3.run_path(root, T3.FULL, args.seed)) or {}, S["refused"], len(tr_rows), len(es_rows))
    if why and not args.smoke:
        raise SystemExit(f"{FT_ARM} must train on D_F5's examples: {why}")
    rows = tr_rows + es_rows
    files = ft_files(root, [r["i"] for r in rows])
    tr, es = np.arange(len(tr_rows)), np.arange(len(tr_rows), len(rows))
    torch.set_num_threads(2)
    dev = torch.device("cpu" if os.environ.get("DS_DEVICE") == "cpu" or not torch.backends.mps.is_available()
                       else "mps")
    data = T.ArmData(rows, files, aug=False, encode=T3.encode_for(T3.FULL))
    data.arm, data.aug = T.MODEL_ARM, False
    print(f"T3 {FT_ARM} seed {args.seed}: {len(tr)} train, {len(es)} early stopping (FS5); input: {INPUT}; {dev}",
          flush=True)
    t0 = time.time()
    for attempt in (1, 2):
        log = []
        data.masked, data.applied = 0, {}
        try:
            net, state, best_ep, best = DS.train_arm(data, tr, es, args.seed, dev, log, DS.MAX_EPOCHS,
                                                     build=F.build_net, loss=F.loss_fn)
            break
        except PS.StepsSkipped as e:
            print(f"attempt {attempt} aborted: {e}", flush=True)
            if dev.type == "mps":
                torch.mps.empty_cache()
            if attempt == 2:
                raise SystemExit(f"TRAIN FAILED {FT_ARM} {args.seed}: {e}")
    rp.parent.mkdir(parents=True, exist_ok=True)
    mp = rp.with_suffix(".pt")
    torch.save(state, mp)
    ckpts = {str(k): (_load(ft_record_path(root, k)) or {}).get("best_sha256") for k in FOLDS}
    rec = {"plan": T.PLAN, "design": DESIGN, "stage": f"T3 {FT_ARM}", "status": STATUS, "arm": FT_ARM,
           "seed": args.seed, "input": INPUT, "model_arm": T.MODEL_ARM, "augmented": False, "separators": ckpts,
           "labels": "115 (full space, masked; amp head)", "train": len(tr), "early_stop": len(es),
           "dropped": sorted(S["refused"]), "attempts": attempt, "epochs_run": len(log), "best_epoch": best_ep,
           "best_early_stop_loss": best, "minutes": round((time.time() - t0) / 60, 1), "device": str(dev),
           "model": mp.name, "model_sha256": DS.hashlib_file(mp), "log": log, "drift": S["drift"],
           "smoke": bool(args.smoke), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(rp, rec)
    print(f"TRAIN DONE {FT_ARM} {args.seed}: best epoch {best_ep} of {len(log)}")
    if best_ep is not None and best_ep >= DS.MAX_EPOCHS - T3.CAP_EDGE:
        print(f"WARNING: best epoch {best_ep} is within {T3.CAP_EDGE} of the cap {DS.MAX_EPOCHS}: extend this run "
              "before it is read")


def _fs5(root, plan, f5fit):
    from learn import direct_stems as DS

    ctx = DS.Ctx(quiet=True)
    tr_rows, fs_rows = T3.arm_rows(root, ctx, plan, T3.FULL)
    if [r["i"] for r in fs_rows] != f5fit["fs5_ids"]:
        raise SystemExit("FS5 differs from the set F5's fit.json read")
    enc = T3.encode_for(T3.FULL)
    return tr_rows, fs_rows, (lambda lab: enc(lab)[:6])


def cmd_fit(args):
    """D_F5ft's pull on FS5 (zero renders), as step (a)'s `fit`: the constant must be D_F5's."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS

    require_ft(args)
    root = V.out_root(args)
    plan, drift = TM.load_frozen(root, args.smoke)
    f5fit = R.load_fit(root)
    fd = f5fit["models"][T3.FULL]
    tr_rows, fs_rows, enc6 = _fs5(root, plan, f5fit)
    med = DS.label_medians(tr_rows, enc6)
    const = G.constant_answers(tr_rows, enc6, len(F.CONT), len(F.SW), len(F.CAT))
    if (TM.canon(DS.medians_json(med)) != TM.canon(fd["constant"])
            or TM.canon(G.const_json(const)) != TM.canon(fd["constant_answers"])) and not args.smoke:
        raise SystemExit("D_F5ft's constant differs from D_F5's stored one: the labels are not D_F5's")
    cell_of = {r["i"]: (r["amp"], r["base"]) for r in fs_rows}
    folds = DS.section_folds(fs_rows)
    amp_of = {r["i"]: r["amp"] for r in fs_rows}
    nets, recs = load_ft_models(root, args.smoke)
    X, C, Y, who = T3.fs_tensors(fs_rows, ft_files(root, [r["i"] for r in fs_rows]), enc6, model_arm=T.MODEL_ARM)
    outs = F.run_nets(nets, X, C)
    _, ans = DS.median_answers(outs, who)
    lab = DS.labels_of(who, Y)
    table = DS.fit_pull_table(ans, lab, cell_of, med)
    fold_tables = {f: DS.fit_pull_table({i: a for i, a in ans.items() if folds[i] == f}, lab, cell_of, med)
                   for f in (0, 1)}
    amp_acc = [float(int(np.argmax(np.mean([F._softmax(o[n][5]) for o in outs], axis=0))) == F.AMPS.index(amp_of[i]))
               for n, i in enumerate(who)]
    ent = {"models": TM.model_shas(recs), "input": INPUT, "constant": DS.medians_json(med),
           "constant_answers": G.const_json(const), "constant_is_d_f5s": True, "pull": DS.table_json(table),
           "pull_summary": DS.pull_summary(table),
           "pull_folds": {str(f): DS.pull_summary(t) for f, t in fold_tables.items()},
           "fs5_examples": len(fs_rows), "fs5_sections": len({r["section"] for r in fs_rows}),
           "amp_head_fs_accuracy": float(np.mean(amp_acc)) if amp_acc else None}
    print(f"{FT_ARM}: pull {ent['pull_summary']}; folds {ent['pull_folds']}; amp head FS5 accuracy "
          f"{ent['amp_head_fs_accuracy']}", flush=True)
    _save(out_dir(root) / "fit.json", {"plan": T.PLAN, "design": DESIGN, "stage": "T3 D_F5ft fit", "status": STATUS,
                                       "readout_rule": DS.READOUT_RULE + " (T3's)", "fs5_ids": f5fit["fs5_ids"],
                                       "models": {FT_ARM: ent}, "drift": drift, "smoke": bool(args.smoke),
                                       "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("FIT DONE t3-xlft")


def load_fit(root, smoke=False):
    fit = _load(out_dir(root) / "fit.json")
    if not fit or (fit.get("smoke") and not smoke):
        raise SystemExit("run `fit` first")
    return fit


PAIRS = {"the fine-tuned stem": (FT_ARM, TM.NOAUG_ARM),            # primary: both unaugmented, the stem input
         "fine-tuned stem against the mix": (FT_ARM, TM.MIX_ARM),   # beside, descriptive
         "fine-tuned stem, no augmentation, against D_F5": (FT_ARM, T3.FULL)}


def print_r0(rec):
    print(f"\n=== {FT_ARM} ===")
    R.print_r0(rec["rows"][FT_ARM])
    print("\nreadable heads (R0's rule; descriptive, no bar, about 6 per model by chance): "
          + ", ".join(f"{a} {n}" for a, n in rec["readable"].items()))
    for name, (a, b) in PAIRS.items():
        p, sm = rec["paired"][name], rec["summary"][name]
        print(f"\n{a} - {b} ({name}{'; primary' if name == 'the fine-tuned stem' else '; descriptive'}):")
        for who, arm in (("a", a), ("b", b)):
            names = [r["name"] for r in p if r["favours"] == who]
            print(f"  paired per head, reliably better for {arm}: {len(names)} {names}")
        for k in TM.SUMMARY:
            s = sm[k]
            extra = f"; left out {s['left_out']}" if s.get("left_out") else ""
            print(f"  {k:12s} {s['point']} [{s['lo']}, {s['hi']}] ({s['better']} 0 favours {a}; n {s['n']}; "
                  f"favours {dict(a=a, b=b).get(s['favours'])}{extra})")


def cmd_r0(args):
    """Readout 1 (zero renders, descriptive): D_F5ft's R0 table on FS5; D_F5-noaug's and D_F5mix's recomputed from
    step (a)'s stored models (their shas must be step (a)'s), D_F5's from F5's (its readable set must reproduce);
    paired per head and the four summary rows for each pair (the fine-tuned stem first). Read once."""
    from learn import direct_sound_gate as G

    require_ft(args)
    root = V.out_root(args)
    op = out_dir(root) / "r0.json"
    if op.exists():
        print(f"{op} exists: read once (the table it holds is the declared one)")
        print_r0(_load(op))
        return
    plan, drift = TM.load_frozen(root, args.smoke)
    f5fit, fit, afit = R.load_fit(root), load_fit(root, args.smoke), TM.load_fit(root, args.smoke)
    ar0 = TM.load_r0(root, args.smoke)
    r0_f5 = R.load_r0(root, args.smoke)
    tr_rows, fs_rows, enc6 = _fs5(root, plan, f5fit)
    fs_ids = [r["i"] for r in fs_rows]
    ex, shas = {}, {}
    for arm in (FT_ARM, TM.NOAUG_ARM, TM.MIX_ARM, T3.FULL):
        if arm == FT_ARM:
            nets, recs = load_ft_models(root, args.smoke)
            if fit["models"][arm]["models"] != TM.model_shas(recs):
                raise SystemExit(f"{arm}: fit.json was made with other models")
            files, model_arm = ft_files(root, fs_ids), T.MODEL_ARM
        elif arm == T3.FULL:
            nets, recs = T3.load_models(root, T3.FULL, args.smoke)
            if not (f5fit["models"][T3.FULL]["models"] == TM.model_shas(recs) == r0_f5["models"]):
                raise SystemExit("D_F5's models differ from those F5's fit and R0 read")
            files, model_arm = {i: T3.files_of(root, T3.FULL, i) for i in fs_ids}, None
        else:
            nets, recs = TM.load_models(root, arm, args.smoke)
            if not (afit["models"][arm]["models"] == TM.model_shas(recs) == ar0["models"][arm]):
                raise SystemExit(f"{arm}: its models differ from those step (a)'s fit and R0 read")
            files, model_arm = {i: T3.files_of(root, T3.FULL, i) for i in fs_ids}, TM.INPUT_OF[arm]
        X, C, Y, who = T3.fs_tensors(fs_rows, files, enc6, model_arm=model_arm)
        ex[arm] = R.per_example(F.run_nets(nets, X, C), who, Y)
        shas[arm] = TM.model_shas(recs)
    info = {r["i"]: {"section": r["section"], "cell": (r["amp"], r["base"]), "amp": r["amp"]} for r in fs_rows}
    rates, majority = R.train_priors([enc6(r["label"]) for r in tr_rows], [r["amp"] for r in tr_rows])
    const = G.const_from_json(f5fit["models"][T3.FULL]["constant_answers"])
    rows = {arm: R.r0_rows(ex[arm], info, const, rates, majority) for arm in ex}
    for arm, stored in ((T3.FULL, r0_f5["rows"]), (TM.NOAUG_ARM, ar0["rows"][TM.NOAUG_ARM]),
                        (TM.MIX_ARM, ar0["rows"][TM.MIX_ARM])):
        a, b = {r["name"] for r in rows[arm] if r["readable"]}, {r["name"] for r in stored if r["readable"]}
        if a != b and not args.smoke:
            raise SystemExit(f"{arm}'s R0 does not reproduce its stored table: {sorted(a ^ b)}")
    rec = {"plan": T.PLAN, "design": DESIGN, "stage": "T3 D_F5ft R0", "status": STATUS,
           "rule": "R0's: readable iff the 90% interval excludes chance in the right direction",
           "reading": "descriptive: no stop rule, V-real runs whatever FS5 shows; readable counts have no bar",
           "pairs": {k: list(v) for k, v in PAIRS.items()}, "models": shas,
           "fs5_examples": len(ex[FT_ARM]), "fs5_sections": len({v["section"] for v in info.values()}),
           "rows": rows, "by_family": {a: R.by_family(r) for a, r in rows.items()},
           "readable": {a: sum(x["readable"] for x in r) for a, r in rows.items()},
           "paired": {k: TM.paired_rows(ex[a], ex[b], info) for k, (a, b) in PAIRS.items()},
           "summary": {k: TM.summary_rows(ex[a], ex[b], info) for k, (a, b) in PAIRS.items()},
           "drift": drift, "smoke": bool(args.smoke), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(op, rec)
    print_r0(rec)
    print(f"R0 DONE: {op}")


def load_r0(root, smoke=False):
    r0 = _load(out_dir(root) / "r0.json")
    if not r0 or (r0.get("smoke") and not smoke):
        raise SystemExit("run `r0` first")
    return r0


# --- probe (MAIN): the tone probe on the new stems --------------------------------------------------------------------

PROBE = {"x": "fine-tuned stem", "c": "stock stem", "b": "mix"}


def cmd_probe(args):
    """The tone probe's linear probes (`tone_info_probe`, its stored summaries for the mix and the stock stem) with the
    fine-tuned stem's summaries beside: readable heads per input (R0's rule) and the paired step x - c per head
    (descriptive, zero renders)."""
    import numpy as np

    from learn import tone_info_probe as P

    require_ft(args)
    root, _, tr, fs, _ = P.load_sets()
    S = P.prepare(root, tr, fs)
    base = S["X_of"]
    cache = {}

    def x_of(rows):
        out = []
        for r in rows:
            i = r["i"]
            if i not in cache:
                z = np.load(ft_path(root, i))
                cache[i] = P.mel_summary({"A": z["sA"], "B": z["sB"]})
            out.append(cache[i])
        return np.stack(out)

    S["X_of"] = lambda key, rows: x_of(rows) if key == "x" else base(key, rows)
    lab_te, ids, sec, const_te = S["lab_te"], S["ids"], S["sec"], S["const_te"]
    preds, rows_by = {}, {}
    for key in PROBE:
        P_, _ = P.fit_input(S, key, tr, fs)
        preds[key] = P_
        ex = {i: {"a2": P_["a2"][n], "sw_p": P_["sw_p"][n], "mic_p": [m[n] for m in P_["mic_p"]],
                  "amp_p": P_["amp_p"][n], "c": lab_te[0][n], "cm": lab_te[1][n], "s": lab_te[2][n],
                  "sm": lab_te[3][n], "k": lab_te[4][n], "km": lab_te[5][n]} for n, i in enumerate(ids)}
        rows_by[key] = R.r0_rows(ex, S["info"], S["const"], S["rates"], S["majority"])
        print(f"({key}) {PROBE[key]}: {sum(r['readable'] for r in rows_by[key])} readable", flush=True)
    jix = {**{n: j for j, n in enumerate(F.CONT)}, **{n: j for j, n in enumerate(F.SW)},
           **{n: j for j, n in enumerate(F.CAT)}}
    heads = []
    for h, r in enumerate(rows_by["x"]):
        name, kind = r["name"], r["kind"]
        k2 = {"continuous": "continuous", "switch": "switch"}.get(kind, "amp" if name == R.AMP_NAME else "mic")
        xc = P.step_row(k2, preds["x"], preds["c"], ids, jix.get(name), lab_te, sec, const_te)
        cx = P.step_row(k2, preds["c"], preds["x"], ids, jix.get(name), lab_te, sec, const_te)
        heads.append({"name": name, "family": r["family"], "kind": kind,
                      "readable": {k: bool(rows_by[k][h]["readable"]) for k in PROBE},
                      "x_better_than_c": xc["reliable"], "c_better_than_x": cx["reliable"], "step_x_minus_c": xc})
    rec = {"design": DESIGN, "status": STATUS + "; the probe is descriptive", "inputs": PROBE,
           "readable": {k: sum(r["readable"] for r in rows_by[k]) for k in PROBE},
           "x_not_c": [h["name"] for h in heads if h["readable"]["x"] and not h["readable"]["c"]],
           "c_not_x": [h["name"] for h in heads if h["readable"]["c"] and not h["readable"]["x"]],
           "step_x_better": sum(h["x_better_than_c"] for h in heads),
           "step_c_better": sum(h["c_better_than_x"] for h in heads),
           "families": {k: P.family_table(rows_by[k]) for k in PROBE}, "heads": heads, "rows": rows_by,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(out_dir(root) / "probe.json", rec)
    print({k: rec[k] for k in ("readable", "step_x_better", "step_c_better")})
    print("x not c:", rec["x_not_c"])
    print("c not x:", rec["c_not_x"])
    print(f"PROBE DONE: {out_dir(root) / 'probe.json'}")


# --- V-real (predict: TORCH_PY, zero renders; render: MAIN) --------------------------------------------------------

def cmd_vreal_predict(args):
    """D_F5ft's answers on the frozen V-real-11 (zero renders): step (a)'s inputs (the crop's mix, its hashes equal to
    F5's), the fine-tuned stem through D_stem's input, pulled by D_F5ft's FS5 fit, the plain readout; its own amp
    recorded. Output gain stays S's here and is fitted at render to the stock stem's loudness, as step (a)."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import local_objective as LO

    require_ft(args)
    root = V.out_root(args)
    plan, drift = TM.load_frozen(root, args.smoke)
    r0 = load_r0(root, args.smoke)                       # read first (descriptive); no stop rule
    fit = load_fit(root, args.smoke)
    nets, recs = load_ft_models(root, args.smoke)
    f = fit["models"][FT_ARM]
    if f["models"] != TM.model_shas(recs) or r0["models"][FT_ARM] != TM.model_shas(recs):
        raise SystemExit(f"{FT_ARM}: the fit or R0 was made with other models")
    med, table = DS.medians_from_json(f["constant"]), DS.table_from_json(f["pull"])
    f5pred, f5pp = TM.f5_predictions(root, plan, args.smoke)
    dirs, parts, dropped = T3.vreal_dirs(root, plan, bool(f5pred.get("dropped_members")))
    if sorted(dropped) != sorted(f5pred.get("dropped_members") or []):
        raise SystemExit("V-real's parts changed since F5's predictions")
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    target = json.loads(DE.LEVELS.read_text())["summary"]["eval_mix_lufs_median"]
    ms = A.L.menu_S()
    preds, own, inputs, gaps, ft_sha = {}, {}, {}, {}, {}
    for slug, amp, search, held in dirs:
        cls, _ = T3.part_info(slug, parts[slug])
        if slug not in inputs:
            inputs[slug] = TM.vreal_input(slug, parts[slug], man, target)
            if inputs[slug]["hashes"] != f5pred["inputs"].get(slug) and not args.smoke:
                raise SystemExit(f"{slug}: its inputs differ from those F5's predictions read")
            inputs[slug]["ft"], ft_sha[slug] = vreal_ft_stem(root, slug)
        it = inputs[slug]
        s8, m8, ls, lm = DS.step4_half(it["ft"], it["mix"], search, it["gain_db"])
        _, S_ = ms[amp][cls]
        x, c = DS.model_input(s8, m8, ls, lm, search, amp, cls, T.MODEL_ARM)
        b, gap = DS.cell_b(table, (amp, cls), F.cell_masks(amp)[0])
        if gap:
            gaps[f"{amp}|{cls}"] = gap
        r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
        diag = {"a2": [float(v) for v in r["a2"]], "sw_p": [float(v) for v in r["sw_p"]], "mics": r["mics"]}
        preds[f"{slug}|{amp}|{search}"] = {"settings": LO.sdict(T3.full_answer(amp, S_, r, med[(amp, cls)], b)),
                                          "held": held, "diag": diag}
        own[f"{slug}|{search}"] = {"amp": r["amp"], "p": r["amp_p"]}
    od = out_dir(root) / "vreal"
    _save(od / "predictions.json", {
        "plan": T.PLAN, "design": DESIGN, "stage": "T3 D_F5ft V-real", "status": STATUS, "arm": FT_ARM, "input": INPUT,
        "smoke": bool(args.smoke), "members": plan["vreal"]["members"], "dropped_members": dropped,
        "directions": len(dirs), "predictions": {FT_ARM: preds}, "own_amp": {FT_ARM: own}, "pull_gaps": gaps,
        "inputs": {s: v["hashes"] for s, v in inputs.items()}, "ft_stems": ft_sha, "models": TM.model_shas(recs),
        "r0_sha256": TM.sha(out_dir(root) / "r0.json"), "f5_predictions_sha256": TM.sha(f5pp), "drift": drift,
        "output_gain": "S's here; fitted per answer at render to the stock stem's loudness, as F5 and step (a) ("
                       + F.OUTPUT_FIT_STATUS + ")",
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    groups = len({(s, a) for s, a, _, _ in dirs})
    print(f"FT PREDICT: {len(dirs)} directions; {groups} groups, {RENDERS_PER_GROUP * groups} renders to come"
          + (f"; dims with no fitted pull (read at the constant) {gaps}" if gaps else ""))


def cmd_vreal_render(args):
    """D_F5ft's V-real renders for one shard of (part, amp) groups, as step (a)'s: one discarded priming render at S,
    then the answer once per direction, judged on both halves; output gain fitted to the stock stem's loudness (as step
    (a), so the output gain does not move with the input). isolate=True; at most 3 render processes machine-wide; the
    31 GB disk guard; a done group is kept."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    require_ft(args)
    root = V.out_root(args)
    plan, _ = TM.load_frozen(root, args.smoke)
    od = out_dir(root) / "vreal"
    pred = _load(od / "predictions.json")
    if not pred or (pred.get("smoke") and not args.smoke):
        raise SystemExit("run `vreal-predict` first")
    if pred["members"] != plan["vreal"]["members"]:
        raise SystemExit("D_F5ft's predictions were made for another V-real membership")
    if pred["r0_sha256"] != TM.sha(out_dir(root) / "r0.json"):
        raise SystemExit("r0.json changed since vreal-predict")
    dirs, parts, dropped = T3.vreal_dirs(root, plan, bool(pred.get("dropped_members")))
    if sorted(dropped) != sorted(pred.get("dropped_members") or []):
        raise SystemExit("V-real's parts changed since vreal-predict")
    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    mine = DE.shard(A.groups(dirs), args.shard)
    LO._wait_cap()
    DS.wait_render_slot()
    rr = A.renderer()
    ms = A.L.menu_S()
    arms = (FT_ARM,)
    try:
        menu = rr.menu()
        for slug, amp in mine:
            gp = od / "groups" / f"{slug}|{amp}.json"
            if (_load(gp) or {}).get("status") == "done":
                continue
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            info = parts[slug]
            ctx = (A.group_ctx(menu, ms, "F", slug, amp) if info["kind"] == "stagef"
                   else T3.t3_group_ctx(menu, ms, info, amp))
            if K.key(dict(ctx["S"])) != K.key(ctx["S_stored"]):
                raise SystemExit(f"{amp}: the live S differs from the stored copy")
            g = {"sel": ctx["sel"], "S": ctx["S"], "di": ctx["di"], "di32": ctx["di32"], "ref": ctx["ref"],
                 "lag": ctx["part"]["judge_lag"]}
            stem = DS.stored_stem(man, f"stagef/{slug}") if info["kind"] == "stagef" else T3.crop_stem(info)
            settings = {FT_ARM: {sh: LO.tdict(pred["predictions"][FT_ARM][f"{slug}|{amp}|{sh}"]["settings"])
                                 for sh, _ in K.DIRECTIONS}}
            held_of = dict(K.DIRECTIONS)
            checks = {}

            def keep(arm, search, y, settings=settings, stem=stem, ref=g["ref"], checks=checks):
                gain = float(settings[arm][search].get(F.OUTPUT, "0"))
                checks[f"{arm}|{search}"] = T3.lufs_check(gain, y, stem, ref, search, held_of[search])

            rec = DS.run_group(rr, g, settings, False, None, K.judge, keep=keep, arms=arms)
            rec.update(slug=slug, amp=amp, lufs=checks, output_gain_fit=F.OUTPUT_FIT_STATUS, status_ft=STATUS)
            _save(gp, rec)
            print(slug, amp, rec["renders"], flush=True)
    finally:
        rr.close()
    print(f"FT RENDER DONE {args.shard[0]}/{args.shard[1]}; renders {rr.count}")


# --- report (MAIN) ---------------------------------------------------------------------------------------------------

def contrasts():
    """{name: (a, b)}: the primary (the fine-tuned stem against the stock stem, both unaugmented), D_F5ft against the
    mix and D_F5, the gate read with the fine-tuned stem, S and the constant; step (a)'s primary and F5's gate beside
    (stored)."""
    return {f"{FT_ARM} - {TM.NOAUG_ARM} (primary: the fine-tuned stem, both unaugmented)": (FT_ARM, TM.NOAUG_ARM),
            f"{FT_ARM} - {TM.MIX_ARM} (the fine-tuned stem against the mix; descriptive)": (FT_ARM, TM.MIX_ARM),
            f"{FT_ARM} - {T3.FULL} (descriptive)": (FT_ARM, T3.FULL),
            f"{FT_ARM} - {T3.CORE} (the gate read with the fine-tuned stem)": (FT_ARM, T3.CORE),
            f"{FT_ARM} - S": (FT_ARM, "S"),
            f"{FT_ARM} - constant (D_F5's, rendered in F5)": (FT_ARM, T3.CONST),
            f"step (a): {TM.MIX_ARM} - {TM.NOAUG_ARM} (stored)": (TM.MIX_ARM, TM.NOAUG_ARM),
            f"F5: {T3.FULL} - {T3.CORE} (the gate, stored)": (T3.FULL, T3.CORE)}


def snr_block(rows, S):
    """The stems' SNR against the wet target (as T3's build measured it: the target render times the mix gain), new
    minus stock per example, section-clustered 90% t, for F5 (out of fold) and FS5."""
    out = {}
    for name in ("f5", "fs5"):
        d = {i: r["snr_audio_db"] - r["snr_stock_db"] for i, r in rows.items()
             if r["set"] == name and r.get("snr_stock_db") is not None}
        new = sorted(r["snr_audio_db"] for r in rows.values() if r["set"] == name)
        old = sorted(r["snr_stock_db"] for r in rows.values() if r["set"] == name and r.get("snr_stock_db") is not None)
        out[name] = {"new_minus_stock_db": {**R.section_t(d, {i: S["section_of"][i] for i in d}), "n": len(d)},
                     "median_new_db": new[len(new) // 2] if new else None,
                     "median_stock_db": old[len(old) // 2] if old else None}
    return out


def cmd_report(args):
    """The rows (band-weighted, 90% band-clustered t, per class and V-real-10 beside), the stems' SNR, the fine-tunes'
    curves and the probe's counts."""
    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS
    from learn import perfect_sep_arm as P

    require_ft(args)
    root = V.out_root(args)
    plan, drift = TM.load_frozen(root, args.smoke)
    S = load_sets(root, args.smoke)
    od = out_dir(root) / "vreal"
    f5d = T.stage_root(root, T3.STAGE) / "vreal"
    pred, _ = TM.f5_predictions(root, plan, args.smoke)
    members = set(plan["vreal"]["members"]) - set(pred.get("dropped_members") or [])
    v10 = set(plan["vreal"]["v_real_10"])
    crops = (_load(T3.crops_manifest_path(root)) or {}).get("crops") or {}
    parts, _ = T3.vreal_parts(sorted(members), A.pool_slugs(), crops, drop_missing=True)
    units = [u for u in P.build_units() if u["slug"] in members] + T3.t3_units(parts, f5d / "groups")
    cache = {}
    where = {FT_ARM: od, TM.MIX_ARM: TM.out_dir(root) / "vreal", TM.NOAUG_ARM: TM.out_dir(root) / "vreal"}

    def value(arm):
        def f(u):
            d = where.get(arm, f5d)
            ck = (str(d), u["slug"], u["amp"])
            if ck not in cache:
                cache[ck] = _load(d / "groups" / f"{u['slug']}|{u['amp']}.json") or {}
            gr = cache[ck]
            if gr.get("status") != "done":
                return None
            return ((gr.get("judge") or {}).get(f"{arm}|{u['search']}") or {}).get(u["held"])
        return f

    arms = sorted({a for pair in contrasts().values() for a in pair} - {"S"})
    refused = {a: DS.add_step4_arm(units, a, value(a)) for a in arms}
    gaps = [f"{n} directions have no {a} value" for a in arms if (n := sum(1 for u in units if u["d"].get(a) is None))]
    bad = {a: n for a, n in refused.items() if n}
    if bad:
        gaps.append(f"refused answers scored as S {bad}")
    rows_ = ("all", "v_real_10")
    filt = {"all": lambda u: True, "v_real_10": lambda u: u["slug"] in v10}
    con = {name: DS.step4_contrast(units, a, b, filt, rows=rows_, fixed=("S",)) for name, (a, b) in contrasts().items()}
    lufs = []
    for (d, *_), gr in cache.items():
        if d == str(od):
            lufs += list((gr.get("lufs") or {}).values())
    renders = sum((_load(p) or {}).get("renders", 0) for p in (od / "groups").glob("*.json"))
    fts = {str(k): {q: (_load(ft_record_path(root, k)) or {}).get(q)
                    for q in ("mode", "stopped", "best_step", "best_db", "stock_db", "at_cap_improving", "minutes",
                              "resumed", "skipped_steps")} for k in FOLDS}
    probe = _load(out_dir(root) / "probe.json") or {}
    r0 = _load(out_dir(root) / "r0.json") or {}
    rep = {"plan": T.PLAN, "design": DESIGN, "stage": "T3 D_F5ft report", "status": STATUS,
           "v_real": sorted(members), "directions": len(units), "complete": not gaps, "incomplete_because": gaps,
           "refused_scored_as_S": refused, "contrasts": con, "abs_lufs_error": T3.lufs_summary(lufs),
           "own_amp": (_load(od / "predictions.json") or {}).get("own_amp"), "renders": renders,
           "fine_tunes": fts, "stems_snr": snr_block(sep_rows(root), S), "probe_readable": probe.get("readable"),
           "r0_readable": r0.get("readable"), "drift": drift, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(out_dir(root) / "report.json", rep)
    print(f"T3 {FT_ARM} ({STATUS}): V-real {len(members)} parts ({len(units)} directions); renders {renders}")
    for k, v in fts.items():
        print(f"  fine-tune fold {k}: {v}")
    for name, b in rep["stems_snr"].items():
        print(f"  stems {name}: {b}")
    print(f"  probe readable: {rep['probe_readable']}; R0 readable: {rep['r0_readable']}")
    for g in gaps:
        print(f"  incomplete: {g}")
    for name, c in con.items():
        for row in rows_:
            r = c["rows"].get(row) or {}
            for cls, s in [("", r.get("all") or {})] + sorted((r.get("per_class") or {}).items()):
                sign = f"; bands -/+ {s.get('bands_negative')}/{s.get('bands_positive')}" if s.get("bands") else ""
                print(f"  {name if not cls and row == 'all' else '':64s} {(row + ' ' + cls).strip():18s} "
                      f"{s.get('band_weighted_mean')} [{s.get('lo90')}, {s.get('hi90')}] ({s.get('bands')} bands{sign}) "
                      f"{T3.rule_reading(s)}")
    print(f"|LUFS error| (a pipeline check): {rep['abs_lufs_error']}")
    print("FT REPORT DONE")


# --- main -----------------------------------------------------------------------------------------------------------

COMMANDS = {"check": cmd_check, "prep": cmd_prep, "gate": cmd_gate, "train": cmd_train, "separate": cmd_separate,
            "vreal-stems": cmd_vreal_stems, "train-d": cmd_train_d, "fit": cmd_fit, "r0": cmd_r0, "probe": cmd_probe,
            "vreal-predict": cmd_vreal_predict, "vreal-render": cmd_vreal_render, "report": cmd_report}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="xlance_finetune", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=tuple(COMMANDS))
    ap.add_argument("--fold", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--device", default="cpu", choices=("mps", "cpu"))
    ap.add_argument("--order", default="asc", choices=("asc", "desc"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--shard", type=V.parse_shard, default=(0, 1))
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--smoke-steps", type=int, default=4)
    args = ap.parse_args(argv)
    if args.shard != (0, 1) and args.cmd != "vreal-render":
        raise SystemExit("--shard is for vreal-render")
    if (args.fold is None) == (args.cmd in ("train", "separate")):
        raise SystemExit("--fold is for train and separate, and they need it")
    if (args.seed is None) == (args.cmd == "train-d"):
        raise SystemExit("--seed is for train-d, and it needs it")
    return COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
