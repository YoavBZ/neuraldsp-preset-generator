"""S3's training (`docs/separation-plan.md`, ledger `separation` `phase_s3`): X-LANCE's `gtr_mss` fine-tuned to pull
the centred guitar out of a mix steered by the hint (`learn.sep_s3`'s steering).

- **s3-cache** (main .venv, CPU): D_CC's examples with other guitars in the training bands, their parts cached at
  44.1 kHz: per example the target render and the other guitars' render (mono, unscaled) with D_CC's gains; per section
  and vocal variant the non-guitar backing pre-panned by S0's rule (stereo) and the amp tracks of the other guitars
  summed (mono). The Adam Buckley band is validation, never trained on: 200 fixed steered validation mixes (10 s)
  by S0's strata recipe are drawn from it.
- **s3-check** (msst-venv): the gradient check (one batch on MPS against the CPU, per parameter tensor) and the speed
  check per batch size. The run goes on MPS only if the median relative error is < 1e-3 and the largest < 1e-2.
- **s3-train** (msst-venv, MPS): mixes drawn on the fly (`draw_layout`, `build_draw`; the hinted copy is the target,
  12% of draws drop it), X-LANCE's own loss, AdamW 1e-5 with 1,000 warm-up steps, fp32, all parameters, no weight
  decay, a hand-made clip at norm 1.0 (`clip_grad_norm_` gives NaN on MPS), non-finite steps skipped (reload the last
  checkpoint after 25 in a row, abort after 20 reloads). Validation every 1,000 steps: the median SI-SDR and the
  model's read; step 0 is the first best; a new best needs +0.1 dB and a read no worse than step 0's; it stops at 5
  evaluations without one, the abort rule, or 72 h. Resumes from `last.pt`.
- **s3-keep** (msst-venv, CPU, beside the run; Amendment 3d): after each evaluation, `last.pt`'s weights kept as
  `run/kept/step_N.pt` (`last.pt` is written at each evaluation, then replaced at the next).
- **s3-pick** (Amendment 3d, after the stop): among the evaluated checkpoints whose weights are kept (`best.pt` counts
  as its step), those within 0.1 dB of the best median SI-SDR with a read no worse than step 0's; the lowest read
  wins. Writes `run/pick.json` with the file's sha256; **s3-apply** applies that checkpoint.

    .venv/bin/python -m learn.sep_s3_train s3-cache
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s3_train s3-check
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s3_train s3-train --batch B
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s3_train s3-keep
    .venv/bin/python -m learn.sep_s3_train s3-pick

The pure parts (the layout draw, the crop rule, the checkpoint pick and the stop check) are unit-tested.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time

from learn import sep_s0 as S0
from learn import sep_s3 as S3

SR44 = 44_100
CROP = 61_000                     # 1.38 s: with the loss's 4,096 window padding, 65,096 < the MPS bug's 65,536
CONTROL_N = 98_304                # the gradient check's positive control, where the bug should show
PRE = 22_050                      # 0.5 s before the crop for the compressor's envelope
SEED = 20261153
N_VAL = 200
SILENT_P = 0.12                   # training draws with the target dropped (the network learns to return silence)
MIN_BATCH = 4
STRATA_P = (("centred", 0.30), ("off-centre", 0.30), ("double", 0.20), ("split", 0.20))
MIN_APART = 0.35                  # other guitars at least this far (in pan) from the target
HINT_JITTER = 0.10
RATIO_JITTER_DB = 3.0
ACTIVE_DB = 20.0                  # the crop's target within this many dB of the crop's mix
LR, BETAS, WARMUP = 1e-5, (0.8, 0.99), 1000
CLIP = 1.0
EVAL_EVERY, PATIENCE, MAX_HOURS, MIN_GAIN_DB = 1000, 5, 72.0, 0.1
BAD_RELOAD, MAX_RELOADS = 25, 20
GRAD_MEDIAN, GRAD_MAX = 1e-3, 1e-2


def out_dir():
    return S0.out_dir().parent / "s3"


# --- the pure parts -------------------------------------------------------------------------------------------------------

def _apart(rng, lo, hi, avoid, sign=None):
    """A pan in +-[lo, hi] (sign random unless given) at least MIN_APART from every pan in `avoid` (12 tries)."""
    p = 0.0
    for _ in range(12):
        s = sign if sign is not None else rng.choice((-1, 1))
        p = s * rng.uniform(lo, hi)
        if all(abs(p - a) >= MIN_APART for a in avoid):
            return p
    return p


def draw_layout(rng):
    """One training draw's placements (wider than S0's strata). -> {stratum, target: [p...], offset_ms, db2, others,
    amp, partner (or None)}."""
    u, acc, s = rng.random(), 0.0, STRATA_P[-1][0]
    for name, w in STRATA_P:
        acc += w
        if u < acc:
            s = name
            break
    side = rng.choice((-1, 1))
    lay = {"stratum": s, "offset_ms": 0.0, "db2": 0.0, "partner": None}
    if s == "centred":
        t = rng.uniform(-0.2, 0.2)
        o = side * rng.uniform(0.5, 1.0)
        lay.update(target=[t], others=o, amp=_apart(rng, 0.5, 1.0, [t]))
    elif s == "off-centre":
        t = side * rng.uniform(0.35, 1.0)
        o = (_apart(rng, 0.35, 1.0, [t], sign=-side) if rng.random() < 0.5 else rng.uniform(-0.2, 0.2))
        lay.update(target=[t], others=o, amp=_apart(rng, 0.0, 1.0, [t]))
    elif s == "double":
        t1, t2 = side * rng.uniform(0.5, 1.0), -side * rng.uniform(0.5, 1.0)
        lay.update(target=[t1, t2], offset_ms=rng.uniform(8.0, 30.0), db2=-rng.uniform(0.0, 4.0),
                   others=rng.uniform(-0.2, 0.2), amp=rng.uniform(-0.2, 0.2))
    else:                                                  # split: the target centred, takes hard on both sides
        t = rng.uniform(-0.15, 0.15)
        o = side * rng.uniform(0.8, 1.0)
        lay.update(target=[t], others=o, amp=o, partner=-side * rng.uniform(0.8, 1.0))
    return lay


def pick_crop(target_mid, mix_mid, rng, n_try=8, crop=CROP, pre=PRE, active_db=ACTIVE_DB):
    """A crop start (after `pre` samples) where the target's level is within `active_db` of the mix's; else the try
    with the smallest gap. Works on plain sequences of floats or numpy arrays."""
    n = len(mix_mid)
    best, best_gap = pre, float("inf")
    for _ in range(n_try):
        a = rng.randrange(pre, max(pre + 1, n - crop))
        et = _energy(target_mid[a:a + crop]) + 1e-12
        em = _energy(mix_mid[a:a + crop]) + 1e-12
        gap = 10 * math.log10(em / et)
        if gap <= active_db:
            return a
        if gap < best_gap:
            best, best_gap = a, gap
    return best


def _energy(seq):
    try:
        return float((seq * seq).sum())                     # numpy
    except TypeError:
        return sum(float(v) * float(v) for v in seq)


def hint_from(layout, rng):
    """The training hint: the first copy's coarse hint plus a uniform jitter."""
    return S3.coarse(layout["target"][0]) + rng.uniform(-HINT_JITTER, HINT_JITTER)


# --- the cache ------------------------------------------------------------------------------------------------------------

def _to44(x):
    from learn import separator_screen as SCR

    return SCR.to44(x)


def cmd_cache(_args):
    import numpy as np

    import pathlib

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    S3.require(S3.PHASE_S3)
    sr = PS.SR
    ns = argparse.Namespace(out=None, smoke=False)
    root = CB.V.out_root(ns)
    plan = CB.load_plan(ns)["examples"]
    rend = T.rows_of(root, CB.STAGE, "render")
    ctx = CB.ctx_for(ns)
    stems = T.Stems(ctx)
    exs = [x for x in plan if x["band"] in S3.TRAIN_BANDS and rend[x["i"]].get("others_file")]
    if any(x["band"] in S3.HELD_BANDS for x in exs):
        raise SystemExit("a held-out band in the training set")
    d = out_dir()
    (d / "ex").mkdir(parents=True, exist_ok=True)
    (d / "sec").mkdir(parents=True, exist_ok=True)
    kb = T.pan_fold(0.0) / S0.pan(0.0)[0]
    kt = 1 / S0.pan(0.0)[0]
    keys = {}                                    # the review: one (section, vocal variant) key, one track list
    index, t0 = [], time.time()
    for m, x in enumerate(sorted(exs, key=lambda x_: (x_["section"], x_["i"]))):
        rw = rend[x["i"]]
        voc = bool(x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"])
        sec_key = _sec_key(x["section"], voc)
        pe, ps_ = d / "ex" / f"{x['i']:07d}.npz", d / "sec" / f"{sec_key}.npz"
        row = {"i": x["i"], "band": x["band"], "section": x["section"], "sec": sec_key, "cls": x["cls"],
               "val": x["band"] == S3.VAL_BAND}
        if pe.exists() and ps_.exists():
            index.append({**row, **json.loads(pe.with_suffix(".json").read_text())})
            continue
        y = np.asarray(G.read_flac(T.flac_path(root, CB.STAGE, x["i"], "target"), rw["target"]["scale"],
                                   rw["target"]["sha256"]), np.float64)
        oth = np.asarray(G.read_flac(T.flac_path(root, CB.STAGE, x["i"], "others"), rw["others_file"]["scale"],
                                     rw["others_file"]["sha256"]), np.float64)
        tracks = T.backing_tracks(x, voc)
        sig = (tuple(tracks), tuple(sorted(a_["track"] for a_ in x.get("amp_tracks") or [])))
        if keys.setdefault(sec_key, sig) != sig:
            raise SystemExit(f"{x['i']}: section key {sec_key} with a different track list")
        st = np.asarray(stems.get(x["section"], tracks), np.float64)
        _, gains, _ = T.self_built_mix(y, oth, st, x)           # D_CC's gains, and its mastering-draw check
        mastered, _ = DS.master_draw(x["i"])
        if not ps_.exists():
            sec = ctx.sections[x["section"]]
            sess = pathlib.Path(ctx.inv[sec["di"]]["session_dir"])
            rng = random.Random(f"{SEED}|backing|{sec_key}")
            n = len(y)
            bL, bR, amp = np.zeros(n), np.zeros(n), np.zeros(n)
            guitar_amps = {a_["track"] for a_ in x.get("amp_tracks") or []}
            for t in tracks:
                a, ch = S0.load_track(sess / t, sec["start_s"], sr)
                if t in guitar_amps:                             # the other guitars' amp tracks, one mono group
                    # stored unpanned; the draw pans it with kb (= 1). A stereo file's (L+R)/2 is already the
                    # recipe's level, so it is raised by kt: panned centre with kb it then folds back to that level
                    amp += a[:n, 0] if ch == 1 else (a[:n, 0] + a[:n, 1]) / 2 * kt / kb
                elif ch == 1:
                    gl, gr = S0.pan(S0.backing_pan(t, rng))
                    bL, bR = bL + a[:n, 0] * gl * kb, bR + a[:n, 0] * gr * kb
                else:
                    bL, bR = bL + a[:n, 0], bR + a[:n, 1]
            np.savez(ps_, bL=_to44(bL).astype(np.float16), bR=_to44(bR).astype(np.float16),
                     amp=_to44(amp).astype(np.float16))
        np.savez(pe, y=_to44(y).astype(np.float16), oth=_to44(oth).astype(np.float16))
        meta = {"gb": gains["gb"], "ga": gains["ga"], "mastered": bool(mastered)}
        pe.with_suffix(".json").write_text(json.dumps(meta))
        index.append({**row, **meta})
        if m % 100 == 0:
            print(f"s3 cache {m + 1}/{len(exs)}: {(time.time() - t0) / (m + 1):.2f} s an example", flush=True)
    (d / "index.json").write_text(json.dumps({"examples": index, "val_band": S3.VAL_BAND,
                                              "train_bands": [b for b in S3.TRAIN_BANDS if b != S3.VAL_BAND]},
                                             indent=0))
    n_val = sum(r["val"] for r in index)
    print(f"S3 CACHE DONE: {len(index)} examples ({n_val} validation, band {S3.VAL_BAND})", flush=True)
    cmd_val(None)


def _sec_key(section, voc):
    import hashlib

    return hashlib.sha1(section.encode()).hexdigest()[:16] + f"-{int(voc)}"


# --- a draw ---------------------------------------------------------------------------------------------------------------

class Pool:
    """The cache's index (training or validation rows); the parts are read per draw (the OS keeps them cached), so a
    worker holds no copy of the whole set."""

    def __init__(self, val):
        d = out_dir()
        idx = json.loads((d / "index.json").read_text())["examples"]
        self.rows = [r for r in idx if r["val"] == val]
        self.by_band = {}
        for r in self.rows:
            self.by_band.setdefault(r["band"], []).append(r)
        self.p_master = sum(r["mastered"] for r in self.rows) / max(1, len(self.rows))

    def ex(self, i):
        import numpy as np

        return np.load(out_dir() / "ex" / f"{i:07d}.npz")

    def sec(self, key):
        import numpy as np

        return np.load(out_dir() / "sec" / f"{key}.npz")


def _panned(x, p, k):
    import numpy as np

    gl, gr = S0.pan(p)
    return np.stack([x * gl * k, x * gr * k])


def val_layout(k):
    """A validation draw's placements by S0's strata recipe (`S0.draw_stratum`, its own seed): the other guitars'
    amp tracks sit with the others, as in S0. -> a `draw_layout`-shaped dict."""
    s = S0.draw_stratum(k, seed=f"{SEED}|val")
    return {"stratum": s["stratum"], "target": s["target"], "offset_ms": s.get("target_offset_ms", 0.0),
            "db2": s.get("target_db2", 0.0), "others": s["others"], "amp": s["others"], "partner": None}


def build_draw(pool, rng, full=False, crop=CROP, layout=None):
    """One steered mix and its steered target. -> (x [2, n], y [2, n], phi, layout) at 44.1 kHz.
    - The target is the hinted (first) copy only, so a double's far copy is something to remove (the review).
    - Training draws (no `layout` given) take `draw_layout`, the jittered hint, and drop the target in SILENT_P of
      draws. A given layout (validation) takes the coarse hint, no jitter, no drop.
    - A `crop`-sample crop where the target plays, unless full (the whole 10 s)."""
    import numpy as np

    from learn import trusted_data as T

    train = layout is None
    r = rng.choice(pool.rows)
    lay = draw_layout(rng) if train else layout
    e, s = pool.ex(r["i"]), pool.sec(r["sec"])
    y, oth = np.asarray(e["y"], np.float64), np.asarray(e["oth"], np.float64)
    n = len(y)
    kt = 1 / S0.pan(0.0)[0]
    kb = T.pan_fold(0.0) / S0.pan(0.0)[0]
    copies = []
    for k, p in enumerate(lay["target"]):
        src = y
        if k == 1:
            lag = int(lay["offset_ms"] / 1000 * SR44)
            src = np.concatenate([np.zeros(lag), y[:n - lag]]) * 10 ** (lay["db2"] / 20)
        copies.append(_panned(src, p, kt))
    silent = train and rng.random() < SILENT_P
    t_mix = np.zeros((2, n)) if silent else sum(copies)
    t_ref = np.zeros((2, n)) if silent else copies[0]
    rest = _panned(oth, lay["others"], kt) + _panned(np.asarray(s["amp"], np.float64)[:n], lay["amp"], kb)
    rest += np.stack([np.asarray(s["bL"], np.float64)[:n], np.asarray(s["bR"], np.float64)[:n]])
    if lay["partner"] is not None:
        mates = [q for q in pool.by_band[r["band"]] if q["section"] != r["section"]] or pool.rows
        q = rng.choice(mates)
        rest += _panned(np.asarray(pool.ex(q["i"])["oth"], np.float64)[:n], lay["partner"], kt)
    gb = r["gb"] + (rng.uniform(-RATIO_JITTER_DB, RATIO_JITTER_DB) if train else 0.0)
    ga = 10 ** (r["ga"] / 20)
    mix = (t_mix + rest * 10 ** (gb / 20)) * ga
    tgt = t_ref * ga
    if full:
        a0, a1 = 0, n
    else:
        a = pick_crop(sum(copies).mean(0) * ga, mix.mean(0), rng, crop=crop)
        a0, a1 = a - PRE, a + crop
    mix, tgt = mix[:, a0:a1], tgt[:, a0:a1]
    if train:
        master, mrng = rng.random() < pool.p_master, rng   # S0's linked compressor at D_CC's rate
    else:                                                   # validation: the example's own draw, as S0
        from learn import direct_stems as DS

        master, mrng = DS.master_draw(r["i"])
    if master:
        from learn import song_aug as SA

        mid = mix.mean(0)
        g, mk = S0.linked_gain(mid, mrng, SR44)
        gm = 10 ** ((float(SA.lufs(mid)) + mk - float(SA.lufs(mid * g))) / 20)
        mix, tgt = mix * g * gm, tgt * g * gm
        peak = 10 ** (-1 / 20)
        mix = np.clip(mix, -peak, peak)
    if not full:
        mix, tgt = mix[:, PRE:], tgt[:, PRE:]
    phi = S3.steer_phi(hint_from(lay, rng) if train else S3.coarse(lay["target"][0]))
    xL, xR = S3.rotate(mix[0], mix[1], phi)
    yL, yR = S3.rotate(tgt[0], tgt[1], phi)
    lay = {**lay, "band": r["band"], "i": r["i"], "cls": r["cls"], "silent": silent}
    return np.stack([xL, xR]).astype(np.float32), np.stack([yL, yR]).astype(np.float32), phi, lay


def cmd_val(_args):
    """200 fixed validation mixes (10 s) from the validation band, by S0's strata recipe, seeded."""
    import numpy as np

    pool = Pool(val=True)
    if {r["band"] for r in pool.rows} != {S3.VAL_BAND}:
        raise SystemExit("the validation pool isn't the validation band alone")
    rng = random.Random(f"{SEED}|valset")
    X, Y, P, L = [], [], [], []
    for k in range(N_VAL):
        x, y, phi, lay = build_draw(pool, rng, full=True, layout=val_layout(k))
        X.append(x.astype(np.float16))
        Y.append(y.astype(np.float16))
        P.append(phi)
        L.append(lay)
    np.savez(out_dir() / "val.npz", x=np.stack(X), y=np.stack(Y), phi=np.array(P))
    (out_dir() / "val.json").write_text(json.dumps(L))
    print(f"S3 VAL DONE: {N_VAL} mixes", flush=True)


def unsteer_mono(z2, phi):
    """A steered stereo signal rotated back and averaged (numpy or torch, [..., 2, n])."""
    c, s = math.cos(-phi), math.sin(-phi)
    L, R = z2[..., 0, :], z2[..., 1, :]
    return ((c * L - s * R) + (s * L + c * R)) / 2


# --- Amendment 3d: the checkpoint, chosen with the read --------------------------------------------------------------

PHASE_S3D = "phase_s3d"


def pick_step(evals, kept, min_gain=None):
    """Amendment 3d: among the evaluated steps in `kept`, those whose median SI-SDR is within `min_gain` dB of the best
    median over all evaluations and whose read is no worse than step 0's; the lowest read wins (a tie: the earlier
    step). -> the step, or None."""
    min_gain = MIN_GAIN_DB if min_gain is None else min_gain
    read0 = next(e["read"] for e in evals if e["step"] == 0)
    top = max(e["si_sdr_median"] for e in evals)
    ok = [e for e in evals if e["step"] in kept and e["si_sdr_median"] >= top - min_gain and e["read"] <= read0]
    return min(ok, key=lambda e: (e["read"], e["step"]))["step"] if ok else None


def stopped(st, now):
    """Whether the run has stopped by its own rule: PATIENCE evaluations after the best, or MAX_HOURS."""
    after = [e for e in st["evals"] if e["step"] > st["best_step"]]
    return len(after) >= PATIENCE or (now - st["t_start"]) / 3600 > MAX_HOURS


# --- the model ------------------------------------------------------------------------------------------------------------

def load_model(device):
    """X-LANCE's gtr_mss (hash-checked by XLanceG), trainable, on `device`."""
    import torch

    from learn import direct_stems as DS

    m = DS.XLanceG("cpu").model
    torch.set_num_threads(4)
    m = m.to(device)
    m.train()
    return m


try:                                             # module level, so spawned DataLoader workers can pickle it
    from torch.utils.data import IterableDataset as _Base
except ImportError:                              # CI without torch: the pure parts still import
    _Base = object


class Draws(_Base):
    """An endless stream of training batches, seeded per worker and by the step a run resumes at."""

    def __init__(self, batch, seed):
        super().__init__()
        self.batch, self.seed = batch, seed

    def __iter__(self):
        import numpy as np
        import torch

        info = torch.utils.data.get_worker_info()
        wid = info.id if info else 0
        rng = random.Random(f"{SEED}|train|{self.seed}|{wid}")
        pool = Pool(val=False)
        if S3.VAL_BAND in {r["band"] for r in pool.rows} or set(S3.HELD_BANDS) & {r["band"] for r in pool.rows}:
            raise SystemExit("the validation or a held-out band in the training pool")
        while True:
            xs, ys = zip(*[build_draw(pool, rng)[:2] for _ in range(self.batch)])
            yield torch.from_numpy(np.stack(xs)), torch.from_numpy(np.stack(ys))


def make_dataset(batch, seed):
    return Draws(batch, seed)


def grad_sq_norm(model):
    import torch

    sq = [p.grad.detach().float().pow(2).sum() for p in model.parameters() if p.grad is not None]
    return float(torch.stack(sq).sum().cpu()) if sq else 0.0


def si_sdr_t(est, ref):
    import numpy as np

    return S0.si_sdr(np.asarray(est, np.float64), np.asarray(ref, np.float64))


def evaluate(model, device, nets):
    """On the 200 fixed validation mixes: the median and mean SI-SDR (dB) of the rotated-back mono estimate against
    the target's, and the model's read (mean cosine distance of the adopted model's features to the target's, CPU,
    at 48 kHz like S0's). -> {si_sdr_median, si_sdr_mean, read}."""
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import product_path as PP
    from learn import separator_screen as SCR

    z = np.load(out_dir() / "val.npz")
    metas = json.loads((out_dir() / "val.json").read_text())
    model.eval()
    si, rd = [], []

    def f(a):
        with torch.no_grad():
            t = torch.from_numpy(np.ascontiguousarray(a, np.float32))[None].to(device)
            return model(t)[0].float().cpu().numpy()

    for x, y, phi, meta in zip(z["x"], z["y"], z["phi"], metas):
        phi = float(phi)
        est = DS.xl_run_chunked(f, np.asarray(x, np.float32))
        e_m, r_m = unsteer_mono(est, phi), unsteer_mono(np.asarray(y, np.float64), phi)
        m_m = unsteer_mono(np.asarray(x, np.float64), phi)
        si.append(si_sdr_t(e_m, r_m))
        n48 = int(round(len(m_m) * 48000 / SR44))
        e8, r8, m8 = (SCR.to48(np.asarray(v, np.float64), n48) for v in (e_m, r_m, m_m))
        rd.append(PP.cosine_distance(S3.model_feats(nets, e8, m8, meta["cls"]),
                                     S3.model_feats(nets, r8, m8, meta["cls"])))
    model.train()
    return {"si_sdr_median": float(np.median(si)), "si_sdr_mean": float(np.mean(si)), "read": float(np.mean(rd))}


# --- the checks -----------------------------------------------------------------------------------------------------------

def grad_compare(x, y):
    """One batch's gradients on the CPU and on MPS (dropout off on both). -> {loss_cpu, loss_mps, norms, per-tensor
    relative errors ||d|| / max(||g_cpu||, 1e-3 x the median tensor norm), median, max, worst}."""
    import torch

    grads = {}
    for dev in ("cpu", "mps"):
        torch.manual_seed(0)
        m = load_model(dev)
        m.eval()                                    # dropout off: the config's 0.1 dropout draws differ per device
        loss = m(x.to(dev), target=y.to(dev))
        loss.backward()
        grads[dev] = ({k: p.grad.detach().float().cpu() for k, p in m.named_parameters() if p.grad is not None},
                      float(loss.detach().cpu()), grad_sq_norm(m))
        del m
    gc, lc, nc = grads["cpu"]
    gm, lm, nm = grads["mps"]
    norms = sorted(float(v.norm()) for v in gc.values())
    floor = 1e-3 * norms[len(norms) // 2]
    rel = {k: float((gm[k] - gc[k]).norm()) / max(float(gc[k].norm()), floor) for k in gc}
    vals = sorted(rel.values())
    return {"loss_cpu": lc, "loss_mps": lm, "grad_norm_cpu": math.sqrt(nc), "grad_norm_mps": math.sqrt(nm),
            "n_tensors": len(vals), "floor": floor, "rel_err_median": vals[len(vals) // 2], "rel_err_max": vals[-1],
            "worst": sorted(rel.items(), key=lambda t: -t[1])[:8]}


def cmd_check(args):
    import numpy as np
    import torch

    S3.require(S3.PHASE_S3)
    pool = Pool(val=False)
    rng = random.Random(f"{SEED}|check")
    rep = {}
    for name, n in (("crop", CROP), ("positive_control", CONTROL_N)):
        xs, ys = zip(*[build_draw(pool, rng, crop=n)[:2] for _ in range(2)])
        g = grad_compare(torch.from_numpy(np.stack(xs)), torch.from_numpy(np.stack(ys)))
        g["samples"] = n
        rep[name] = g
        print(f"S3 GRADIENT CHECK {name} ({n} samples): loss cpu {g['loss_cpu']:.6f} mps {g['loss_mps']:.6f}; "
              f"rel err median {g['rel_err_median']:.2e} max {g['rel_err_max']:.2e}", flush=True)
    rep["pass"] = bool(rep["crop"]["rel_err_median"] < GRAD_MEDIAN and rep["crop"]["rel_err_max"] < GRAD_MAX)
    rep["control_shows_the_bug"] = bool(rep["positive_control"]["rel_err_max"] >= GRAD_MAX)
    print(f"S3 GRADIENT CHECK: pass {rep['pass']}; the positive control shows the bug: "
          f"{rep['control_shows_the_bug']}", flush=True)
    # speed: forward, backward and an AdamW step, per batch size, on MPS
    m = load_model("mps")
    opt = torch.optim.AdamW(m.parameters(), lr=LR, betas=BETAS, weight_decay=0.0)
    rep["params"] = sum(p.numel() for p in m.parameters())
    rep["speed"] = {}
    for b in [b_ for b_ in args.batches if b_ >= MIN_BATCH]:
        xs, ys = zip(*[build_draw(pool, rng)[:2] for _ in range(b)])
        xb, yb = torch.from_numpy(np.stack(xs)).to("mps"), torch.from_numpy(np.stack(ys)).to("mps")
        try:
            for k in range(args.steps + 2):
                if k == 2:
                    torch.mps.synchronize()
                    t0 = time.time()
                opt.zero_grad()
                loss = m(xb, target=yb)
                loss.backward()
                opt.step()
            torch.mps.synchronize()
            dt = (time.time() - t0) / args.steps
            rep["speed"][b] = {"s_per_step": dt, "clips_per_s": b / dt,
                               "mem_gb": torch.mps.driver_allocated_memory() / 2 ** 30}
            print(f"S3 SPEED batch {b}: {dt:.3f} s a step, {b / dt:.1f} clips/s, "
                  f"{rep['speed'][b]['mem_gb']:.1f} GB", flush=True)
        except RuntimeError as err:
            rep["speed"][b] = {"error": str(err)[:300]}
            print(f"S3 SPEED batch {b}: {str(err)[:200]}", flush=True)
            break
    (out_dir() / "check.json").write_text(json.dumps(rep, indent=1))


# --- the training ---------------------------------------------------------------------------------------------------------

def cmd_train(args):
    import numpy as np
    import torch

    S3.require(S3.PHASE_S3)
    d = out_dir() / "run"
    d.mkdir(parents=True, exist_ok=True)
    chk = json.loads((out_dir() / "check.json").read_text())
    if not chk["pass"] and args.device == "mps":
        raise SystemExit("the gradient check failed on MPS: not training there (the plan)")
    if args.batch * args.accum < MIN_BATCH:
        raise SystemExit(f"batch {args.batch} x accumulation {args.accum} < {MIN_BATCH} (the plan)")
    from learn import product_path as PP

    nets, _, _ = PP._adopted()                  # the model's read, on the CPU
    dev = torch.device(args.device)
    model = load_model(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, betas=BETAS, weight_decay=0.0)
    st = {"step": 0, "best": -1e9, "best_step": 0, "read0": None, "evals": [], "reloads": 0, "t_start": time.time(),
          "skipped": 0, "batch": args.batch, "accum": args.accum}
    if (d / "last.pt").exists():
        ck = torch.load(d / "last.pt", map_location="cpu", weights_only=True)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        st = json.loads((d / "state.json").read_text())
        st["step"] = int(ck.get("step", st["step"]))           # the weights' own step (the review)
        if (st.get("batch", args.batch), st.get("accum", args.accum)) != (args.batch, args.accum):
            raise SystemExit("resumed with a different batch or accumulation than the run started with")
        print(f"resumed at step {st['step']}", flush=True)
    kw = {"persistent_workers": True, "prefetch_factor": 4} if args.workers > 0 else {}
    loader = torch.utils.data.DataLoader(make_dataset(args.batch, st["step"]), batch_size=None,
                                         num_workers=args.workers, **kw)
    it = iter(loader)

    def save_last():
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "step": st["step"]}, d / "last.tmp")
        (d / "state.tmp").write_text(json.dumps(st, indent=1))
        (d / "last.tmp").replace(d / "last.pt")
        (d / "state.tmp").replace(d / "state.json")

    if not st["evals"]:                          # step 0: X-LANCE as it is, the curve's start and the first best
        ev = evaluate(model, dev, nets)
        st["evals"].append({"step": 0, **ev, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        st["best"], st["best_step"], st["read0"] = ev["si_sdr_median"], 0, ev["read"]
        torch.save(model.state_dict(), d / "best.pt")
        save_last()
        print(f"EVAL step 0: SI-SDR median {ev['si_sdr_median']:+.2f} mean {ev['si_sdr_mean']:+.2f} read "
              f"{ev['read']:.4f}", flush=True)
    bad, t_log, losses = 0, time.time(), []
    while True:
        hours = (time.time() - st["t_start"]) / 3600
        if hours > MAX_HOURS:
            print(f"S3 TRAIN STOP: {MAX_HOURS} h", flush=True)
            break
        lr = LR * min(1.0, (st["step"] + 1) / WARMUP)
        for g in opt.param_groups:
            g["lr"] = lr
        opt.zero_grad(set_to_none=True)
        lv, ok = 0.0, True
        for _ in range(args.accum):                  # micro-batches summed: the same update as one batch
            x, y = next(it)
            loss = model(x.to(dev), target=y.to(dev)) / args.accum
            li = float(loss.detach().cpu())
            if not math.isfinite(li):
                ok = False
                break
            loss.backward()
            lv += li
        if ok:
            sq = grad_sq_norm(model)
            ok = math.isfinite(sq)
        if not ok:
            bad += 1
            st["skipped"] += 1
            if bad >= BAD_RELOAD:
                st["reloads"] += 1
                if st["reloads"] > MAX_RELOADS or not (d / "last.pt").exists():
                    print("S3 TRAIN ABORT: non-finite steps", flush=True)
                    break
                ck = torch.load(d / "last.pt", map_location="cpu", weights_only=True)
                model.load_state_dict(ck["model"])
                opt.load_state_dict(ck["opt"])
                st["step"] = int(ck.get("step", st["step"]))    # back to the checkpoint's step
                print(f"reloaded last.pt after {bad} bad steps (reload {st['reloads']})", flush=True)
                bad = 0
            continue
        bad = 0
        nrm = math.sqrt(sq)
        if nrm > CLIP:
            for p in model.parameters():
                if p.grad is not None:
                    p.grad.mul_(CLIP / (nrm + 1e-6))
        opt.step()
        st["step"] += 1
        losses.append(lv)
        if st["step"] % 50 == 0:
            dt = time.time() - t_log
            print(f"step {st['step']} loss {np.mean(losses):.4f} lr {lr:.1e} {50 / dt:.2f} steps/s "
                  f"skipped {st['skipped']} {hours:.1f} h", flush=True)
            t_log, losses = time.time(), []
        if st["step"] % EVAL_EVERY == 0:
            ev = evaluate(model, dev, nets)
            st["evals"].append({"step": st["step"], **ev, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            if ev["si_sdr_median"] >= st["best"] + MIN_GAIN_DB and ev["read"] <= st["read0"]:
                st["best"], st["best_step"] = ev["si_sdr_median"], st["step"]
                torch.save(model.state_dict(), d / "best.tmp")
                (d / "best.tmp").replace(d / "best.pt")
            save_last()
            print(f"EVAL step {st['step']}: SI-SDR median {ev['si_sdr_median']:+.2f} mean {ev['si_sdr_mean']:+.2f} "
                  f"read {ev['read']:.4f} (best {st['best']:+.2f} at {st['best_step']}; read at 0 "
                  f"{st['read0']:.4f})", flush=True)
            if len([e for e in st["evals"] if e["step"] > st["best_step"]]) >= PATIENCE:
                print(f"S3 TRAIN STOP: no new best in {PATIENCE} evaluations", flush=True)
                break
    save_last()
    print(f"S3 TRAIN DONE: step {st['step']}, best {st['best']:+.2f} at {st['best_step']}", flush=True)


def cmd_apply(args):
    """s3-pick's checkpoint on the held-out bands' items of a set (S0's main or the split set): steer by the coarse hint
    (steer_mdxc's), separate, rotate back, average; 48 kHz stems in `stems/s3`, as every S0 stem."""
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import separator_screen as SCR
    from learn import sep_s1b as S1B

    import hashlib
    import pathlib

    S3.require(S3.PHASE_S3)
    S3.require(PHASE_S3D)
    root = S1B.set_dir(args.set)
    pick = json.loads((out_dir() / "run" / "pick.json").read_text())          # s3-pick's choice (Amendment 3d)
    ck = pathlib.Path(pick["path"])
    if hashlib.sha256(ck.read_bytes()).hexdigest() != pick["sha256"]:
        raise SystemExit(f"{ck} isn't the picked file (sha256)")
    dev = torch.device(args.device)
    model = load_model(dev)
    model.load_state_dict(torch.load(ck, map_location="cpu", weights_only=True))
    model.eval()
    print(f"s3-apply: step {pick['step']} ({ck.name})", flush=True)

    def f(a):
        with torch.no_grad():
            t = torch.from_numpy(np.ascontiguousarray(a, np.float32))[None].to(dev)
            return model(t)[0].float().cpu().numpy()

    n_done = 0
    for p in sorted((root / "items").glob("*.npz")):
        meta = json.loads(p.with_suffix(".json").read_text())
        if meta["band"] not in S3.HELD_BANDS:
            continue
        q = root / "stems" / "s3" / p.name
        if q.exists():
            continue
        q.parent.mkdir(parents=True, exist_ok=True)
        z = np.load(p)
        L, R = np.asarray(z["L"], np.float64), np.asarray(z["R"], np.float64)
        phi = S3.steer_phi(S3.hint_of(meta))
        Ls, Rs = S3.rotate(L, R, phi)
        est = DS.xl_run_chunked(f, np.stack([SCR.to44(Ls), SCR.to44(Rs)]))
        np.savez(q, stem=np.asarray(SCR.to48(unsteer_mono(est, phi), len(L)), np.float16))
        n_done += 1
    print(f"S3 APPLY DONE: {args.set}, {n_done} stems", flush=True)


def cmd_keep(args):
    """Amendment 3d: `last.pt`'s weights as `run/kept/step_N.pt`, N an evaluated step (run after each evaluation)."""
    import torch

    S3.require(PHASE_S3D)
    d = out_dir() / "run"
    ck = torch.load(d / "last.pt", map_location="cpu", weights_only=True)
    n = int(ck["step"])
    st = json.loads((d / "state.json").read_text())
    if n not in {e["step"] for e in st["evals"]}:
        raise SystemExit(f"last.pt is at step {n}, not an evaluated step: run s3-keep right after an evaluation")
    q = d / "kept" / f"step_{n}.pt"
    if q.exists():
        print(f"S3 KEEP: step {n} already kept", flush=True)
        return
    q.parent.mkdir(exist_ok=True)
    torch.save(ck["model"], q.with_suffix(".tmp"))
    q.with_suffix(".tmp").replace(q)
    print(f"S3 KEEP: step {n} -> {q}", flush=True)


def cmd_pick(args):
    """Amendment 3d, after the stop: the checkpoint by `pick_step`, written to `run/pick.json` with its sha256."""
    import hashlib

    S3.require(PHASE_S3D)
    d = out_dir() / "run"
    st = json.loads((d / "state.json").read_text())
    if not stopped(st, time.time()):
        raise SystemExit("the run hasn't stopped by its rule yet")
    kept = {int(p.stem.split("_")[1]): p for p in sorted((d / "kept").glob("step_*.pt"))}
    kept.setdefault(st["best_step"], d / "best.pt")
    n = pick_step(st["evals"], set(kept))
    if n is None:
        raise SystemExit("no kept checkpoint qualifies")
    e = next(e for e in st["evals"] if e["step"] == n)
    out = {"step": n, "path": str(kept[n]), "sha256": hashlib.sha256(kept[n].read_bytes()).hexdigest(),
           "si_sdr_median": e["si_sdr_median"], "read": e["read"], "best_step": st["best_step"],
           "kept": sorted(kept), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    (d / "pick.json").write_text(json.dumps(out, indent=1))
    print(f"S3 PICK: step {n} (median {e['si_sdr_median']:+.2f}, read {e['read']:.4f}; best by SI-SDR at "
          f"{st['best_step']}; kept {sorted(kept)})", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="learn.sep_s3_train")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("s3-cache").set_defaults(fn=cmd_cache)
    sub.add_parser("s3-val").set_defaults(fn=cmd_val)
    s = sub.add_parser("s3-check")
    s.add_argument("--batches", type=int, nargs="+", default=[4, 8, 12])
    s.add_argument("--steps", type=int, default=8)
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("s3-train")
    s.add_argument("--batch", type=int, required=True)
    s.add_argument("--workers", type=int, default=2)
    s.add_argument("--accum", type=int, default=1, help="micro-batches per update (memory: a batch of 2 swaps)")
    s.add_argument("--device", default="mps")
    s.set_defaults(fn=cmd_train)
    s = sub.add_parser("s3-apply")
    s.add_argument("--set", choices=("main", "split"), required=True)
    s.add_argument("--device", default="mps")
    s.set_defaults(fn=cmd_apply)
    sub.add_parser("s3-keep").set_defaults(fn=cmd_keep)
    sub.add_parser("s3-pick").set_defaults(fn=cmd_pick)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
