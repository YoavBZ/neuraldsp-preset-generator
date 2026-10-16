"""Arm B diagnostics, experiment 1 (`docs/song-to-settings-diagnostics-plan.md`).

The steps alternate between the renderer's interpreter (.venv) and torch's ($TORCH_PY), in this
order (nothing here trains):

    $TORCH_PY        -m learn.song_diag models                   # step 1.0: collapse, calibration
    .venv/bin/python -m learn.song_diag ks-replay                # step 1.0: replay stored K_S runs
    .venv/bin/python -m learn.song_diag preflight                # judge timing, repeat on P1/P2
    .venv/bin/python -m learn.song_diag draw                     # targets + sensitivity bases
    .venv/bin/python -m learn.song_diag render-targets --shard i/3
    $TORCH_PY        -m learn.song_diag features                 # views 1a and 1b (one process)
    $TORCH_PY        -m learn.song_diag propose                  # every candidate's settings
    .venv/bin/python -m learn.song_diag score --shard i/3
    .venv/bin/python -m learn.song_diag sensitivity --shard i/3
    .venv/bin/python -m learn.song_diag report                   # set-up check, R1–R4′, trigger row
    # top-up, only if `report` says a fold is short:  draw --top-up FOLD:N, then the steps again
    # step 1.3, only on trigger row 2 and the user's own yes:
    $TORCH_PY        -m learn.song_diag step13-propose --user-approved
    .venv/bin/python -m learn.song_diag step13-score --user-approved --shard i/3
    .venv/bin/python -m learn.song_diag step13-report --user-approved

The pure functions (draw, sampling, readings, guards) take plain data and are unit-tested; the
CLI steps are the only code that reads files, renders or loads models.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import statistics
import subprocess
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import knob_ceiling as K  # noqa: E402
from learn import song_bank as B  # noqa: E402
from learn.song_readout import EPS, at_least_share, bw_stats, finite, gap_closed  # noqa: E402

OUT = B.OUT.parent / "diag"
DOCS_SUMMARY = PLUGIN_ROOT / "docs/song-to-settings-diagnostics.json"
SR = B.SR
TRIM = int(B.TRIM_S * SR)                   # 12,000 samples: the isolate fade-in
CLIP = int(B.WIN_S * SR)                    # 480,000 samples: the 10-s clip
WIN_LEN = TRIM + CLIP                       # a window is 10.25 s

# seeds (plan, ledger)
SEED_TARGETS = 20261020
SEED_SAMPLES = 20261021
SEED_BASELINES = 20261022
SEED_SENS = 20261023
SEED_KS = K.SEED                            # 20261013

N_PER_FOLD = 30
MIN_INFORMATIVE = 40
GAP_FLOOR = 0.1
CLOSE = 0.5
REPEAT_TOL = 1e-3
REPEAT_SHARE = 0.95
FLAT = 0.05
SENS_STEP = 0.15
COLLAPSE_SEP = 0.5
FAR = 0.2
R2_MARGIN = -0.03
R4_SHARE, R4P_SHARE, R4P_RHO = 1 / 3, 0.10, -0.5
K_VIEW = {"1a": 4, "1b": 8}
N_BASE = 8                                  # random labels, S-jitters
N_JIT_CONT = N_JIT_BANK = 4                 # target jitters: continuous-only, bank-style
JITTER_SIGMA, KEEP_P = 0.1, 0.7
THREADS = 2
RENDER_CAP = 8200                           # hard stop, top-up and pre-flight included
PREFLIGHT_N, PREFLIGHT_JUDGE_CALLS = 5, 20
SENS_PER_AMP, SENS_BASES = 5, 4
MAX_SHARDS = 3
MEM_START_GB, MEM_LOW_GB, SWAP_GROWTH_MB, MEM_WAIT_S = 6.0, 3.0, 1024.0, 15 * 60
SLOWDOWN = 1.25
STEP5_BANDS = ("Adam Buckley", "Atlantis Bound", "Dom McLennon", "Eggy", "Magician's Nephew", "Turbosauro",
               "Wall Of Death", "Zeno")
VIEWS = ("1a", "1b")
DIRS = (("A", "B"), ("B", "A"))
NOT_IN_POOL = ("target", "target_repeat", "S")
STEP13_SAMPLES = 16
STEP13_SEED = 20261024           # not in the plan: step 1.3's sample seed, declared when it is offered


def sj(x):
    return {f"{m}/{k}": v for (m, k), v in x.items()}


def st(d):
    return {tuple(k.rsplit("/", 1)): v for k, v in d.items()}


def skey(x):
    return K.key(dict(x))


def int_seed(*parts):
    """A Python `random` seed from a numpy SeedSequence over `parts` (a dropped target shifts no
    other target's draws)."""
    import numpy as np

    return int(np.random.SeedSequence(list(parts)).generate_state(1)[0])


# ============================================================================== the catalogue

def catalogue():
    """Every classed development part with a DI: {slug, band, fold, di, crop, song}."""
    fold_of = B.folds()
    cat = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    lt = json.loads((PLUGIN_ROOT / "docs/label-table-parts.json").read_text())
    classed, crops = lt["classes_all"], lt["parts"]
    out = {}
    for s in cat["sessions"]:
        if s["split"] != "development":
            continue
        band = s.get("group") or f"{s['source']}/{s['song']}"
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_") for x in (s["source"], s["song"], p["part"]))
            if slug in classed and p.get("di"):
                out[slug] = {"slug": slug, "band": band, "fold": fold_of.get(band), "song": f"{s['source']}/{s['song']}",
                             "di": str(B.DATASETS / s["path"] / p["di"]), "crop": crops.get(slug, {}).get("crop")}
    s3 = json.loads((PLUGIN_ROOT / "docs/validation-set3.json").read_text())
    ses = {x["key"]: x for x in s3["sessions"]}
    for p in s3["parts"]:
        if p["split"] != "development" or p["slug"] not in classed:
            continue
        di = next((d["di"] for d in ses[p["session_key"]]["dis"] if d["part"] == p["part"]), None)
        if di:
            out[p["slug"]] = {"slug": p["slug"], "band": p["band"], "fold": fold_of.get(p["band"]),
                              "song": f"set3/{p['session_key']}", "di": str(B.DATA3 / di),
                              "crop": crops.get(p["slug"], {}).get("crop")}
    return out


def exclusions(cat, kc_slugs):
    """(excluded DI tracks, excluded crops, excluded bands): knob ceiling's parts' DIs and crops,
    and experiment 4 step 5's candidate bands."""
    tracks = {cat[s]["di"] for s in kc_slugs if s in cat}
    assert len(tracks) == len(kc_slugs), "every knob-ceiling part must map to its DI track"
    crops = {str(pathlib.Path(cat[s]["crop"])) for s in kc_slugs if cat.get(s, {}).get("crop")}
    return tracks, crops, set(STEP5_BANDS)


def eligible_windows(windows, fold_of, ex_tracks, ex_bands):
    """Fold-own development windows outside the exclusions; Guitar-TECHS (fold "all") never."""
    out = []
    for w in windows:
        if w["fold"] == "all" or str(w["band"]).startswith("Guitar-TECHS"):
            continue
        if w["band"] in ex_bands or w["path"] in ex_tracks:
            continue
        assert fold_of[w["band"]] == w["fold"], (w["band"], w["fold"])
        out.append(w)
    return out


def eligible_backings(backings, ex_crops, ex_bands):
    """(band, fold, path) same-fold candidates outside knob ceiling's crops and step 5's bands."""
    return [b for b in backings if str(pathlib.Path(b[2]).parent) not in ex_crops and b[0] not in ex_bands]


def overlaps(a, b):
    return a["path"] == b["path"] and abs(a["start"] - b["start"]) < WIN_LEN


def window_order(by_fold, seed=SEED_TARGETS):
    """Per fold, the full seeded order of windows: bands in a seeded order taken in turn, each
    band's windows shuffled (drawn without replacement). One generator, folds 0–3 in turn."""
    rng = random.Random(seed)
    order = {}
    for f in sorted(by_fold):
        bands = sorted({w["band"] for w in by_fold[f]})
        rng.shuffle(bands)
        per = {}
        for b in bands:
            ws = sorted((w for w in by_fold[f] if w["band"] == b), key=lambda w: (w["path"], w["start"]))
            rng.shuffle(ws)
            per[b] = ws
        seq = []
        while any(per.values()):
            for b in bands:
                if per[b]:
                    seq.append(per[b].pop(0))
        order[f] = seq
    return order


def pick_windows(seq, n, taken=()):
    """The first n windows of a fold's order that overlap no window already taken (any amount).
    A band that runs out simply passes its turn (its windows no longer appear)."""
    got = list(taken)
    out = []
    for w in seq:
        if len(out) >= n:
            break
        if any(overlaps(w, t) for t in got):
            continue
        out.append(w)
        got.append(w)
    return out


def target_attrs(i, fold, j, window, backings, song_of, ks_opt, menu_S):
    """One target's own draws (amp, class, type, K_S centre, backing, levels seed), seeded per
    target so a top-up or a drop shifts nothing else. j: its index within the fold (even: broad)."""
    rng = random.Random(int_seed(SEED_TARGETS, fold, j))
    amp = rng.choice(K.AMPS)
    cls = rng.choice(("clean", "crunch"))
    kind = "broad" if j % 2 == 0 else "ks_prior"
    centre = None
    if kind == "ks_prior":
        cands = sorted(p for g, rows in ks_opt.items() if g != fold for a, c, p in rows if a == amp and c == cls)
        assert cands, (fold, amp, cls)
        centre = rng.choice(cands)
    own_song = song_of.get(window["path"])
    back = sorted(p for b, g, p in backings if g == fold and song_of.get(p) != own_song)
    assert back, f"fold {fold}: no backing outside the target's own song"
    return {"i": i, "fold": fold, "j": j, "band": window["band"], "window": window, "amp": amp, "class": cls,
            "type": kind, "centre": centre, "backing": rng.choice(back), "seed": rng.randrange(2 ** 31),
            "aac": rng.random() < 0.5}


def draw_settings(t, S, rng):
    """The planted settings: broad (uniform) or K_S-prior (σ 0.1 around the centre, mics and
    switches kept with p 0.7). -> (settings, unit label)."""
    centre = dict(S)
    if t["type"] == "ks_prior":
        centre.update(st(json.loads(pathlib.Path(t["centre"]).read_text())) if isinstance(t["centre"], str)
                      else t["centre"])
        return jitter(K.space(t["amp"], S), S, centre, rng, KEEP_P)
    return broad(K.space(t["amp"], S), S, rng)


def broad(dims, S, rng):
    x, lab = dict(S), {}
    for d in dims:
        k = (d.module, d.key)
        if d.kind in ("cont", "log"):
            u = rng.random()
            x[k] = K.fmt(d.from_unit(u))
            lab[d.name] = u
        else:
            x[k] = lab[d.name] = rng.choice(d.values)
    return x, lab


def jitter(dims, S, centre, rng, keep_p, sigma=JITTER_SIGMA):
    """σ around `centre` on the 0–1 scale; each mic or switch kept with p `keep_p` (1.0: all kept,
    the continuous-only jitter), else drawn uniformly."""
    x, lab = dict(S), {}
    for d in dims:
        k = (d.module, d.key)
        if d.kind in ("cont", "log"):
            u = min(1.0, max(0.0, d.to_unit(centre.get(k, d.lo)) + rng.gauss(0, sigma)))
            x[k] = K.fmt(d.from_unit(u))
            lab[d.name] = u
        else:
            v = centre.get(k, d.values[0]) if rng.random() < keep_p else rng.choice(d.values)
            x[k] = lab[d.name] = v
    return x, lab


def assert_fold_clean(targets, examples):
    """Each target's DI track and backing appear in no bank example its fold model trained on."""
    for t in targets:
        trained = [e for e in examples if e["fold"] != t["fold"]]
        assert t["window"]["path"] not in {e["window"]["path"] for e in trained}, t["i"]
        assert t["backing"] not in {e["backing"] for e in trained}, t["i"]


# ============================================================================== MDN heads

def net_heads(net, feat, lufs_v, amp, cls):
    """The model's raw heads for one half, as numpy: pi (K,), mu, sigma (K, n), sw_p (n_sw,),
    mic_p (n_cat, 10)."""
    import torch

    from learn import song_model as M

    x = torch.tensor(M.norm_feat(feat)[None])
    c = torch.tensor(M.cond_vec(amp, cls, lufs_v)[None])
    with torch.no_grad():
        logpi, mu, ls, swl, catl = net(x, c)
    return {"pi": logpi.exp()[0].numpy(), "mu": mu[0].numpy(), "sigma": ls.exp()[0].numpy(),
            "sw_p": torch.sigmoid(swl)[0].numpy(), "mic_p": [torch.softmax(c_, -1)[0].numpy() for c_ in catl]}


def _layout():
    from learn import song_model as M

    return M.CONT, M.SW, M.CAT, M.MICS


def settings_from(amp, S, cont_u, sw_on, mic_idx):
    """S with the amp's settings set from unit values, switch states and mic indices (union
    layout); settings the amp lacks are ignored."""
    CONT, SW, CAT, MICS = _layout()
    x = dict(S)
    space = {d.name: d for d in K.space(amp, S)}
    for i, n in enumerate(CONT):
        if n in space:
            d = space[n]
            x[(d.module, d.key)] = K.fmt(d.from_unit(float(cont_u[i])))
    for i, n in enumerate(SW):
        if n in space:
            d = space[n]
            x[(d.module, d.key)] = d.values[int(bool(sw_on[i]))]
    for j, n in enumerate(CAT):
        if n in space:
            d = space[n]
            x[(d.module, d.key)] = MICS[int(mic_idx[j])]
    return x


def top_mean_settings(h, amp, S):
    """The single answer, as `song_model.predict_settings`: the heaviest component's mean, each
    switch > 0.5, each mic's top choice."""
    import numpy as np

    top = int(np.asarray(h["pi"]).argmax())
    return settings_from(amp, S, h["mu"][top], np.asarray(h["sw_p"]) > 0.5, [int(np.argmax(p)) for p in h["mic_p"]])


def mixture_mean_settings(h, amp, S):
    import numpy as np

    mean = (np.asarray(h["pi"])[:, None] * np.asarray(h["mu"])).sum(0)
    return settings_from(amp, S, mean, np.asarray(h["sw_p"]) > 0.5, [int(np.argmax(p)) for p in h["mic_p"]])


def truncnorm(rng, mu, sigma, lo=0.0, hi=1.0, max_tries=100000):
    """One draw of N(mu, sigma) truncated to [lo, hi], by redrawing."""
    for _ in range(max_tries):
        v = rng.normal(mu, sigma)
        if lo <= v <= hi:
            return float(v)
    raise RuntimeError(f"truncnorm: no draw inside [{lo}, {hi}] for mu={mu}, sigma={sigma}")


def truncnorm_vec(rng, mu, sigma, size):
    """`size` draws per (mu, sigma) pair (arrays of shape (d,)), truncated to [0, 1] by redrawing."""
    import numpy as np

    mu, sigma = np.broadcast_to(mu, (size, len(mu))).copy(), np.broadcast_to(sigma, (size, len(mu)))
    out = rng.normal(mu, sigma)
    bad = (out < 0) | (out > 1)
    while bad.any():
        out[bad] = rng.normal(mu[bad], sigma[bad])
        bad = (out < 0) | (out > 1)
    return out


def sample_units(h, rng):
    """One posterior sample on the union layout: (cont units, switch states, mic indices). A
    component by pi, each continuous setting from its Gaussian truncated to [0, 1], each switch by
    its probability, each mic by its softmax."""
    import numpy as np

    pi = np.asarray(h["pi"], np.float64)
    k = int(rng.choice(len(pi), p=pi / pi.sum()))
    cont = [truncnorm(rng, float(m), float(s)) for m, s in zip(h["mu"][k], h["sigma"][k])]
    sw = [bool(rng.random() < float(p)) for p in h["sw_p"]]
    mics = []
    for p in h["mic_p"]:
        p = np.asarray(p, np.float64)
        mics.append(int(rng.choice(len(p), p=p / p.sum())))
    return cont, sw, mics


def sample_rng(i, view, direction):
    import numpy as np

    return np.random.default_rng(np.random.SeedSequence([SEED_SAMPLES, i, VIEWS.index(view), "AB".index(direction)]))


def mode_separation(h, mask=None):
    """Σ_k π_k |μ_k − μ̄| / Σ_k π_k σ_k per continuous setting (μ̄ the mixture mean), averaged over
    the settings in `mask` (bool per union setting; None: all)."""
    import numpy as np

    pi, mu, sg = np.asarray(h["pi"], np.float64), np.asarray(h["mu"], np.float64), np.asarray(h["sigma"], np.float64)
    mbar = (pi[:, None] * mu).sum(0)
    sep = (pi[:, None] * np.abs(mu - mbar)).sum(0) / np.maximum((pi[:, None] * sg).sum(0), 1e-12)
    m = np.ones(len(sep), bool) if mask is None else np.asarray(mask, bool)
    return float(sep[m].mean()) if m.any() else math.nan


def collapse_flag(fold_median_sep):
    """{fold: median mode separation} -> True if < COLLAPSE_SEP in ≥ 3 of 4 folds."""
    return sum(v < COLLAPSE_SEP for v in fold_median_sep.values() if finite(v)) >= 3


def effective_components(pi):
    import numpy as np

    p = np.asarray(pi, np.float64)
    p = p[p > 0]
    return float(np.exp(-(p * np.log(p)).sum()))


# --- calibration (step 1.0) ---

def _phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def pit_truncated(pi, mu, sigma, u):
    """The truncated-to-[0, 1] mixture CDF of one setting at u."""
    num = den = 0.0
    for p, m, s in zip(pi, mu, sigma):
        lo, hi = _phi((0 - m) / s), _phi((1 - m) / s)
        num += p * (_phi((u - m) / s) - lo)
        den += p * (hi - lo)
    return float(min(1.0, max(0.0, num / den))) if den > 0 else math.nan


def pit_summary(values, bins=10):
    import numpy as np

    v = np.asarray([x for x in values if finite(x)])
    if not len(v):
        return {"n": 0}
    hist, _ = np.histogram(v, bins=bins, range=(0, 1))
    exp = len(v) / bins
    return {"n": int(len(v)), "hist": hist.tolist(), "chi2": float(((hist - exp) ** 2 / exp).sum()),
            "max_dev": float(np.abs(hist / len(v) - 1 / bins).max())}


def tarp(samples, truths, rng, alphas=None):
    """TARP (Lemos et al. 2023): samples (N, S, d), truths (N, d) on [0, 1]. Reference points
    uniform. -> {alphas, ecp, atc}."""
    import numpy as np

    samples, truths = np.asarray(samples, np.float64), np.asarray(truths, np.float64)
    alphas = np.linspace(0, 1, 21) if alphas is None else np.asarray(alphas)
    ref = rng.random(truths.shape)
    ds = np.linalg.norm(samples - ref[:, None, :], axis=-1)
    dt = np.linalg.norm(truths - ref, axis=-1)
    f = (ds < dt[:, None]).mean(axis=1)
    ecp = np.array([(f < a).mean() for a in alphas])
    return {"alphas": alphas.tolist(), "ecp": ecp.tolist(), "atc": float((ecp - alphas).sum())}


def ece(probs, hits, bins=10):
    """Expected calibration error: confidence probs vs 0/1 outcomes."""
    import numpy as np

    p, y = np.asarray(probs, np.float64), np.asarray(hits, np.float64)
    if not len(p):
        return math.nan
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean() for b in range(bins)
                     if (idx == b).any()))


# ============================================================================== candidates

def baseline_rng(i):
    return random.Random(int_seed(SEED_BASELINES, i))


def baselines(t, S, target_x, bank_settings, rng):
    """The model-free candidates, in a fixed order: 8 random bank labels, 8 S-jitters, 4
    continuous-only and 4 bank-style target jitters. `bank_settings`: stored settings (dicts) of
    fold ≠ f bank examples with the target's amp and class."""
    dims = K.space(t["amp"], S)
    out = {}
    pool = sorted(bank_settings, key=lambda d: json.dumps(d, sort_keys=True))
    assert len(pool) >= N_BASE, "too few bank labels for the random baseline"
    for k, d in enumerate(rng.sample(pool, N_BASE)):
        x = dict(S)
        x.update(st(d))
        out[f"rand{k}"] = x
    for k in range(N_BASE):
        out[f"jS{k}"] = jitter(dims, S, S, rng, KEEP_P)[0]
    for k in range(N_JIT_CONT):
        out[f"jTc{k}"] = jitter(dims, S, target_x, rng, 1.0)[0]
    for k in range(N_JIT_BANK):
        out[f"jTb{k}"] = jitter(dims, S, target_x, rng, KEEP_P)[0]
    return out


def model_candidates(heads, i, amp, S):
    """heads[(view, search half)] -> {name: settings}: per view and direction the top mean, K
    samples, and on 1b the mixture mean."""
    out = {}
    for view in VIEWS:
        for search, _ in DIRS:
            h = heads[(view, search)]
            out[f"{view}:{search}:top"] = top_mean_settings(h, amp, S)
            rng = sample_rng(i, view, search)
            for k in range(K_VIEW[view]):
                out[f"{view}:{search}:s{k}"] = settings_from(amp, S, *sample_units(h, rng))
            if view == "1b":
                out[f"{view}:{search}:mixmean"] = mixture_mean_settings(h, amp, S)
    return out


def render_plan(cands):
    """{name: settings} -> (unique key -> first name, name -> key). The target's repeat is always
    its own render."""
    first, of = {}, {}
    for name, x in cands.items():
        k = skey(x) if name != "target_repeat" else "repeat:" + skey(x)
        of[name] = k
        first.setdefault(k, name)
    return first, of


def planned_renders(cand_sets, n_sens=0, n_pre=PREFLIGHT_N * 2):
    return sum(len(render_plan(c)[0]) for c in cand_sets) + n_sens + n_pre


def budget_ok(planned, cap=RENDER_CAP):
    return planned <= cap


# ============================================================================== sensitivity

def sens_moves(amp, base):
    """{name: settings}: each continuous setting moved SENS_STEP toward the interior, each switch
    flipped (mics not moved)."""
    out = {}
    for d in K.space(amp, base):
        k = (d.module, d.key)
        if d.kind in ("cont", "log"):
            u = d.to_unit(base.get(k, d.lo))
            x = dict(base)
            x[k] = K.fmt(d.from_unit(u + SENS_STEP if u <= 0.5 else u - SENS_STEP))
            out[d.name] = x
        elif d.kind == "switch":
            x = dict(base)
            x[k] = next(v for v in d.values if v != base.get(k))
            out[d.name] = x
    return out


def flat_settings(deltas):
    """deltas: {amp: {setting: [Δjudge per base]}} -> {amp: sorted flat settings} (median < FLAT)."""
    return {amp: sorted(n for n, v in per.items() if v and statistics.median(v) < FLAT) for amp, per in deltas.items()}


def jacobian_summary(grams):
    """grams: list of n×n JᵀJ (same setting order), each normalised by its trace, averaged.
    -> participation ratio and the smallest direction's weights."""
    import numpy as np

    g = np.mean([np.asarray(x) / max(np.trace(x), 1e-12) for x in grams], axis=0)
    w, v = np.linalg.eigh(g)
    w = np.clip(w, 0, None)
    pr = float(w.sum() ** 2 / max((w ** 2).sum(), 1e-24))
    return {"eigenvalues": w.tolist(), "participation_ratio": pr, "smallest": v[:, 0].tolist()}


# ============================================================================== readings

def knob_distance(x, target_x, dims, flat=()):
    """Mean |Δ| on the 0–1 scale over continuous settings, flat ones dropped."""
    ds = [abs(d.to_unit(x.get((d.module, d.key), d.lo)) - d.to_unit(target_x.get((d.module, d.key), d.lo)))
          for d in dims if d.kind in ("cont", "log") and d.name not in flat]
    return statistics.fmean(ds) if ds else math.nan


def mics_match(x, target_x, dims):
    return all(x.get((d.module, d.key)) == target_x.get((d.module, d.key)) for d in dims if d.kind == "cat")


def informative(u):
    d = u["d"]
    return finite(d.get("S"), d.get("target_repeat"), d.get("target")) and \
        d["S"] - d["target_repeat"] >= GAP_FLOOR - EPS


def gap(u, name):
    """Gap closed on the held half; None for a refused (non-finite) candidate."""
    v = u["d"].get(name)
    return gap_closed(u["d"]["S"], v, u["d"]["target_repeat"]) if finite(v) else None


def closes(u, name):
    g = gap(u, name)
    return g is not None and g >= CLOSE - EPS


def best_of(u, names):
    """The candidate with the lowest finite search-half distance (never a non-finite one), or None."""
    ok = [n for n in names if finite(u["s"].get(n))]
    return min(ok, key=lambda n: (u["s"][n], n)) if ok else None


def mdn_names(view, search, k):
    return [f"{view}:{search}:s{j}" for j in range(k)]


def _fold_eval(units, fn):
    """fn(units) -> result with "passes"; adds leave-one-band-out fragility (a pass that flips)."""
    res = fn(units)
    bands = sorted({u["band"] for u in units})
    flips = [b for b in bands if res["passes"] and not fn([u for u in units if u["band"] != b])["passes"]]
    res["fragile_bands"] = flips
    res["fragile"] = bool(flips)
    return res


def r1_fold(units, view):
    def fn(us):
        n = len(us)
        closed = sum(closes(u, f"{view}:{u['search']}:top") for u in us)
        closer = sum(finite(u["d"].get(f"{view}:{u['search']}:top")) and
                     u["d"][f"{view}:{u['search']}:top"] < u["d"]["median"] for u in us)
        return {"n": n, "closed": closed, "closer_than_median": closer,
                "passes": n > 0 and at_least_share(closed, n, 2, 3) and at_least_share(closer, n, 2, 3)}
    return _fold_eval(units, fn)


def _log_rows(us, a_names, b_names):
    rows = []
    for u in us:
        a, b = best_of(u, a_names(u)), best_of(u, b_names(u))
        if a and b and finite(u["d"].get(a), u["d"].get(b)) and u["d"][a] > 0 and u["d"][b] > 0:
            rows.append((u["band"], math.log(u["d"][a] / u["d"][b])))
    return rows


def r2_fold(units, view, k=None):
    k = K_VIEW[view] if k is None else k

    def fn(us):
        n = len(us)
        mdn = lambda u: mdn_names(view, u["search"], k)  # noqa: E731
        closed = 0
        for u in us:
            p = best_of(u, mdn(u))
            closed += p is not None and closes(u, p)
        vs = {}
        for base in ("rand", "jS"):
            rows = _log_rows(us, mdn, lambda u, b=base: [f"{b}{j}" for j in range(k)])
            vs[base] = bw_stats(rows)["band_weighted_mean"] if rows else None
        ok = n > 0 and at_least_share(closed, n, 2, 3) and all(
            v is not None and v <= R2_MARGIN + EPS for v in vs.values())
        return {"n": n, "k": k, "closed": closed, "vs_random": vs["rand"], "vs_S_jitter": vs["jS"], "passes": ok}
    return _fold_eval(units, fn)


def view_status(fold_results):
    """pass: every fold passes and none is fragile; undecided: 3 of 4 pass, or any pass fragile;
    else fail."""
    passes = [r["passes"] for r in fold_results.values()]
    if all(passes) and not any(r["fragile"] for r in fold_results.values()):
        return "pass"
    if all(passes) or sum(passes) == len(passes) - 1 and len(passes) == 4:
        return "undecided"
    return "fail"


def r4_fold(units):
    """R4 and R4′'s inputs for one fold: the far-and-good share over the pooled (unit, distinct
    setting) pairs, the continuous-only jitter clause, and the within-unit Spearman."""
    close_n = far_close = 0
    close_match = far_close_match = 0
    jit_ok = 0
    rhos = []
    for u in units:
        seen = {u["key"][n] for n in NOT_IN_POOL if n in u["key"]}      # S's or the target's settings
        pts = []
        for name in sorted(u["d"]):
            if name in NOT_IN_POOL or u["key"][name] in seen:
                continue
            seen.add(u["key"][name])
            g = gap(u, name)
            kd = u["knob"].get(name)
            if g is not None and finite(kd):
                pts.append((kd, g))
            if g is not None and g >= CLOSE - EPS:
                close_n += 1
                far = finite(kd) and kd >= FAR - EPS
                far_close += far
                if u["mic_match"].get(name):
                    close_match += 1
                    far_close_match += far
        jit_ok += sum(closes(u, f"jTc{j}") for j in range(N_JIT_CONT)) >= 2
        r = spearman([p[0] for p in pts], [p[1] for p in pts])
        if r is not None:
            rhos.append((u["band"], r))
    n = len(units)
    share = far_close / close_n if close_n else None
    rho = bw_stats(rhos)["band_weighted_mean"] if rhos else None
    jit = n > 0 and at_least_share(jit_ok, n, 2, 3)
    return {"units": n, "closing": close_n, "far_and_closing": far_close, "share": share,
            "share_mics_match": far_close_match / close_match if close_match else None,
            "share_mics_differ": ((far_close - far_close_match) / (close_n - close_match)
                                  if close_n - close_match else None),
            "jitter_units_ok": jit_ok, "jitter_clause": jit, "spearman_bw": rho,
            "R4": share is not None and share >= R4_SHARE - EPS and jit,
            "R4p": share is not None and share < R4P_SHARE and rho is not None and rho <= R4P_RHO + EPS}


def spearman(a, b):
    if len(a) < 3:
        return None
    from scipy import stats

    if len(set(a)) < 2 or len(set(b)) < 2:
        return None
    return float(stats.spearmanr(a, b).statistic)


def landscape(per_fold):
    if all(r["R4"] for r in per_fold.values()):
        return "R4"
    if all(r["R4p"] for r in per_fold.values()):
        return "R4p"
    return "between"


def label_sampling_flag(units_by_fold):
    """True if, for R1 or R2 on either view, the K_S-prior half meets the count while the broad
    half does not, in ≥ 3 of 4 folds."""
    def count_ok(us, reading, view):
        if not us:
            return False
        r = (r1_fold if reading == "R1" else r2_fold)(us, view)
        n = r["n"]
        ok = at_least_share(r["closed"], n, 2, 3)
        return ok and (reading == "R2" or at_least_share(r["closer_than_median"], n, 2, 3))

    for reading in ("R1", "R2"):
        for view in VIEWS:
            hits = sum(count_ok([u for u in us if u["type"] == "ks_prior"], reading, view)
                       and not count_ok([u for u in us if u["type"] == "broad"], reading, view)
                       for us in units_by_fold.values())
            if hits >= 3:
                return True
    return False


def setup_check(preflight_repeats, target_repeats, informative_by_fold, parity_ok):
    """target_repeats: {target: (dA, dB)} of the repeat against the target."""
    pre_ok = bool(preflight_repeats) and all(finite(x) and x <= REPEAT_TOL + EPS for x in preflight_repeats)
    # a refused half (inf on target and every candidate) is a non-finite unit, dropped later by
    # informative(); only a finite repeat above the tolerance fails the check (audit 2026-10-16)
    good = [t for t, v in target_repeats.items() if all((not finite(x)) or x <= REPEAT_TOL + EPS for x in v)
            and any(finite(x) for x in v)]
    rep_ok = bool(target_repeats) and at_least_share(len(good), len(target_repeats), 95, 100)
    short = {f: n for f, n in informative_by_fold.items() if n < MIN_INFORMATIVE}
    return {"preflight_repeat_ok": pre_ok, "target_repeat_ok": rep_ok,
            "targets_dropped_repeat": sorted(set(target_repeats) - set(good)),
            "folds_short": short, "parity_ok": bool(parity_ok),
            "passes": pre_ok and rep_ok and not short and bool(parity_ok)}


def readings(units, setup):
    """All readings from the units (each {fold, band, target, type, search, held, d, s, key, knob,
    mic_match}). Units that aren't informative are dropped first (and counted)."""
    folds = sorted({u["fold"] for u in units})
    inf = [u for u in units if informative(u)]
    by = {f: [u for u in inf if u["fold"] == f] for f in folds}
    out = {"units": len(units), "informative": {f: len(v) for f, v in by.items()},
           "dropped_non_informative": [(u["target"], u["search"]) for u in units if not informative(u)],
           "R1": {}, "R2": {}, "R2_k4": {}, "status": {}}
    for view in VIEWS:
        out["R1"][view] = {f: r1_fold(by[f], view) for f in folds}
        out["R2"][view] = {f: r2_fold(by[f], view) for f in folds}
        out["R2_k4"][view] = {f: r2_fold(by[f], view, k=4) for f in folds}
        out["status"][f"R1:{view}"] = view_status(out["R1"][view])
        out["status"][f"R2:{view}"] = view_status(out["R2"][view])
        out["status"][f"R2k4:{view}"] = view_status(out["R2_k4"][view])
    s = out["status"]
    out["R3"] = ((s["R1:1a"] == "pass" and s["R1:1b"] == "fail") or
                 (s["R2k4:1a"] == "pass" and s["R2k4:1b"] == "fail"))
    out["R4"] = {f: r4_fold(by[f]) for f in folds}
    out["landscape"] = landscape(out["R4"])
    out["label_sampling_flag"] = label_sampling_flag(by)
    out["trigger"] = trigger(setup, s, out["R3"], out["landscape"])
    return out


TRIGGERS = {
    0: "set-up check fails: stop; amend; no reading",
    1: "R1 passes on 1b: rung 2 (fresh known-target draw, own plan), then ask; experiments 2-3 do not run",
    2: "R2 passes on 1b: experiment 2 skipped; 3A (or arm C if experiment 4 passes); offer step 1.3 (ask first)",
    3: "undecided: ask the user, with the per-fold and leave-one-band-out figures",
    4: "R3: experiment 2 as confirmation, then song-robustness; experiment 3 does not run",
    5: "both views fail, R4: experiment 2; then by its reading (fails both: 3B)",
    6: "both views fail, R4': experiment 2; fails both: front-end follow-up; 3B does not run",
    7: "both views fail, between: experiment 2 read on its own",
}


def trigger(setup, status, r3, land):
    if not setup["passes"]:
        return 0
    if status["R1:1b"] == "pass":
        return 1
    if status["R2:1b"] == "pass":
        return 2
    if any(status[f"{r}:{v}"] == "undecided" for r in ("R1", "R2") for v in VIEWS):
        return 3
    if r3:
        return 4
    if not all(status[f"{r}:{v}"] == "fail" for r in ("R1", "R2") for v in VIEWS):
        return 3                      # a pass on 1a alone that R3 does not cover: ask
    return {"R4": 5, "R4p": 6}.get(land, 7)


def pooled(units, value):
    """Pooled band-clustered stats of value(u) (None skips) over informative units."""
    return bw_stats([(u["band"], v) for u in units if informative(u) for v in [value(u)] if v is not None])


# --- the K_S replay ---

def replay_run(dims, x0, evals, search, budget=K.BUDGET["K_S"], seed=SEED_KS):
    """Feed a stored run's search-half values back into `knob_search`. -> (final x, [evaluated x
    in order], calls, ok-length)."""
    idx = "AB".index(search)
    xs = []

    def f(x):
        xs.append(dict(x))
        i = len(xs) - 1
        return evals[i][idx] if i < len(evals) else math.inf

    x, _, _, _ = K.knob_search(dims, x0, f, budget, seed)
    return x, xs, len(xs) == len(evals)


def equal_score_sets(xs, evals, held, dims):
    idx = "AB".index(held)
    hv = [e[idx] for e in evals]
    fin = [i for i, v in enumerate(hv) if finite(v) and v > 0]
    if not fin:
        return {}
    b = min(fin, key=lambda i: hv[i])
    out = {}
    for tol in (0.03, 0.1):
        s = [i for i in fin if math.log(hv[i] / hv[b]) <= tol + EPS]
        dist = [knob_distance(xs[i], xs[b], dims) for i in s]
        pair = [knob_distance(xs[i], xs[j], dims) for a, i in enumerate(s) for j in s[a + 1:]]
        out[str(tol)] = {"n": len(s), "mean_pairwise": statistics.fmean(pair) if pair else 0.0,
                         "share_far_from_best": sum(d >= FAR - EPS for d in dist) / len(s),
                         "mic_agreement": sum(mics_match(xs[i], xs[b], dims) for i in s) / len(s)}
    return out


# --- step 1.3 ---

def step13_reading(rows):
    """rows: {band, pick, KS16, S} held distances per direction. 'covers records' if the pick's
    band-weighted log ratio against K_S at 16 is ≤ 0 and it beats S in ≥ 60% of bands."""
    vs_ks = bw_stats([(r["band"], math.log(r["pick"] / r["KS16"])) for r in rows
                      if finite(r["pick"], r["KS16"]) and r["pick"] > 0 and r["KS16"] > 0])
    vs_s = bw_stats([(r["band"], math.log(r["pick"] / r["S"])) for r in rows
                     if finite(r["pick"], r["S"]) and r["pick"] > 0 and r["S"] > 0])
    m = vs_ks["band_weighted_mean"]
    covers = (m is not None and m <= EPS and vs_s["bands"] > 0
              and at_least_share(vs_s["bands_negative"], vs_s["bands"], 3, 5))
    return {"vs_KS16": vs_ks, "vs_S": vs_s, "reading": "covers records" if covers else "renders only"}


def require_user_approval(flag):
    if not flag:
        raise SystemExit("step 1.3 is ask-first: it runs only on the user's own yes (--user-approved), "
                         "after trigger row 2, and must be entered in the ledger's tally first")


# ============================================================================== guards

def parse_vm_stat(text):
    """Available bytes: (free + inactive + speculative) × page size."""
    import re

    ps = int(re.search(r"page size of (\d+) bytes", text).group(1))
    pages = {}
    for line in text.splitlines():
        m = re.match(r"\s*(Pages [a-z ]+):\s+(\d+)\.", line)
        if m:
            pages[m.group(1)] = int(m.group(2))
    return (pages.get("Pages free", 0) + pages.get("Pages inactive", 0) + pages.get("Pages speculative", 0)) * ps


def parse_swapusage(text):
    """Used swap in MB from `sysctl vm.swapusage`."""
    import re

    m = re.search(r"used\s*=\s*([\d.]+)([MG])", text)
    if not m:
        return 0.0
    return float(m.group(1)) * (1024 if m.group(2) == "G" else 1)


def training_slowdown(before_median_s, recent_median_s):
    """True if experiment 4's step time grew by more than 25%: drop to 2 processes."""
    return finite(before_median_s, recent_median_s) and recent_median_s > SLOWDOWN * before_median_s


class MemoryGuard:
    """Start only with ≥ 6 GB available; every `every` renders re-check; below 3 GB or swap grown
    > 1 GB since launch, sleep in 60-s steps; exit after 15 min."""

    def __init__(self, every=20, read=None, sleep=time.sleep, clock=time.monotonic):
        self.read = read or self._read
        self.sleep, self.clock, self.every, self.n = sleep, clock, every, 0
        avail, swap = self.read()
        if avail < MEM_START_GB * 1e9:
            raise SystemExit(f"memory guard: {avail / 1e9:.1f} GB available, need {MEM_START_GB} GB to start")
        self.swap0 = swap

    @staticmethod
    def _read():
        vm = subprocess.run(["vm_stat"], capture_output=True, text=True, check=True).stdout
        sw = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True, check=True).stdout
        return parse_vm_stat(vm), parse_swapusage(sw)

    def low(self):
        avail, swap = self.read()
        return avail < MEM_LOW_GB * 1e9 or swap - self.swap0 > SWAP_GROWTH_MB

    def tick(self):
        self.n += 1
        if self.n % self.every:
            return
        t0 = self.clock()
        while self.low():
            if self.clock() - t0 >= MEM_WAIT_S:
                raise SystemExit("memory guard: low memory for 15 min; exiting (resumable)")
            self.sleep(60)


def check_shards(n):
    if n > MAX_SHARDS:
        raise SystemExit(f"at most {MAX_SHARDS} render processes (experiment 4's count too)")


def set_threads():
    import torch

    torch.set_num_threads(THREADS)


# ============================================================================== audio helpers

def trim(y):
    import numpy as np

    y = np.asarray(y, np.float64)
    y = y.mean(axis=1) if y.ndim == 2 else y
    return y[TRIM:TRIM + CLIP]


def measured_di(w):
    """The measure DI on the untrimmed 10.25-s window, as `song_bank.render`."""
    import numpy as np

    return B.measure(B.load_window(w)).astype(np.float32)


def judge_trimmed(ref_trim, y_full, di_full):
    """Judge on the one trimmed timeline at lag 0 (render against render)."""
    import numpy as np

    return K.judge(ref_trim, trim(y_full), trim(np.asarray(di_full, np.float64)), 0)


def save_flac(path, y, subtype):
    import numpy as np
    import soundfile as sf

    peak = float(max(np.abs(y).max(), 1e-12))
    sf.write(str(path), (y / peak * 0.99).astype(np.float32), SR, subtype=subtype)
    return peak


def load_flac(path, peak):
    """The bank's loader formula (`song_aug.load_render`)."""
    import soundfile as sf

    y, _ = sf.read(str(path), dtype="float64")
    return y / 0.99 * peak


def file_hash(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


def _menu():
    return json.loads((B.OUT.parent / "armB/menu-S.json").read_text())


def _S(menu, amp, cls):
    return menu[amp][cls]["select"], st(menu[amp][cls]["settings"])


# ============================================================================== CLI steps

def step_models():
    """Step 1.0 on fold-own-window bank examples (P1/P2 apart): collapse, calibration, point error."""
    import numpy as np
    import torch

    from learn import song_model as M

    set_threads()
    CONT, SW, CAT, MICS = _layout()
    flat = json.loads((OUT / "flat.json").read_text()) if (OUT / "flat.json").exists() else None
    idx = M.bank_index()
    out = {"models": {f: file_hash(M.OUT / f"fold{f}" / "model.pt") for f in range(4)}, "folds": {}}
    for f in range(4):
        net = M.load_net(f)
        rows = [r for r in idx if r[1] == f]
        res = {}
        for group in ("own", "p1p2"):
            sel = [r for r in rows if (r[2].startswith("Guitar-TECHS") == (group == "p1p2"))]
            acc = {"sep": [], "sep_audible": [], "eff": [], "top_w": [], "top_vs_mix": [], "pit": {n: [] for n in CONT},
                   "pred": {n: [] for n in CONT}, "true": {n: [] for n in CONT}, "sig": {n: [] for n in CONT},
                   "sw": {n: ([], []) for n in SW}, "mic": {n: ([], []) for n in CAT}, "tarp_s": [], "tarp_t": []}
            rng = np.random.default_rng(SEED_SAMPLES)
            for b0 in range(0, len(sel), 256):
                for i, _, band, amp, cls, label in sel[b0:b0 + 256]:
                    d = np.load(B.OUT / "features" / f"{i:05d}.npz")
                    c, cm, s, sm, k, km = M.encode(label)
                    names = {dd.name for dd in K.space(amp)}
                    for h in "AB":
                        x = torch.tensor(M.norm_feat(d[f"feat{h}"])[None])
                        cv = torch.tensor(M.cond_vec(amp, cls, d[f"lufs{h}"])[None])
                        with torch.no_grad():
                            logpi, mu, ls, swl, catl = net(x, cv)
                        pi, mu_, sg = logpi.exp()[0].numpy(), mu[0].numpy(), ls.exp()[0].numpy()
                        hh = {"pi": pi, "mu": mu_, "sigma": sg}
                        mask = cm > 0
                        acc["sep"].append(mode_separation(hh, mask))
                        if flat is not None:
                            aud = mask & np.array([n not in flat.get(amp, []) for n in CONT])
                            acc["sep_audible"].append(mode_separation(hh, aud))
                        acc["eff"].append(effective_components(pi))
                        top = int(pi.argmax())
                        acc["top_w"].append(float(pi[top]))
                        mbar = (pi[:, None] * mu_).sum(0)
                        acc["top_vs_mix"].append(float(np.abs(mu_[top] - mbar)[mask].mean()))
                        for j, n in enumerate(CONT):
                            if cm[j]:
                                acc["pit"][n].append(pit_truncated(pi, mu_[:, j], sg[:, j], float(c[j])))
                                acc["pred"][n].append(float(mu_[top, j]))
                                acc["true"][n].append(float(c[j]))
                                acc["sig"][n].append(float(sg[top, j]))
                        p_sw = torch.sigmoid(swl)[0].numpy()
                        for j, n in enumerate(SW):
                            if sm[j]:
                                acc["sw"][n][0].append(float(max(p_sw[j], 1 - p_sw[j])))
                                acc["sw"][n][1].append(float((p_sw[j] > 0.5) == bool(s[j])))
                        for j, n in enumerate(CAT):
                            if km[j]:
                                p = torch.softmax(catl[j], -1)[0].numpy()
                                acc["mic"][n][0].append(float(p.max()))
                                acc["mic"][n][1].append(float(int(p.argmax()) == int(k[j])))
                        cont_idx = [j for j, n in enumerate(CONT) if n in names and cm[j]]
                        comp = rng.choice(len(pi), size=200, p=pi / pi.sum())
                        smp = np.empty((200, len(cont_idx)), np.float32)
                        for kk in set(comp.tolist()):
                            sel_k = comp == kk
                            smp[sel_k] = truncnorm_vec(rng, mu_[kk, cont_idx], sg[kk, cont_idx], int(sel_k.sum()))
                        acc["tarp_s"].append((amp, smp))
                        acc["tarp_t"].append((amp, np.asarray([c[j] for j in cont_idx], np.float32)))
            per = {}
            for n in CONT:
                t_, p_ = acc["true"][n], acc["pred"][n]
                if len(t_) < 3:
                    continue
                med = statistics.median(t_)
                per[n] = {"n": len(t_), "mae": statistics.fmean(abs(a - b) for a, b in zip(p_, t_)),
                          "mae_median": statistics.fmean(abs(med - b) for b in t_),
                          "pearson": float(np.corrcoef(p_, t_)[0, 1]) if np.std(p_) > 0 else None,
                          "spearman": spearman(p_, t_), "spread_ratio": float(np.std(p_) / max(np.std(t_), 1e-12)),
                          "sigma_top_over_label_sd": float(np.median(acc["sig"][n]) / max(np.std(t_), 1e-12)),
                          "pit": pit_summary(acc["pit"][n]),
                          "audible": None if flat is None else not any(n in v for v in flat.values())}
            tarp_by_amp = {}
            for amp, nd in sorted({(a, len(t_)) for a, t_ in acc["tarp_t"]}):
                S_ = [s_ for (a, s_), (_, t_) in zip(acc["tarp_s"], acc["tarp_t"]) if a == amp and len(t_) == nd]
                T_ = [t_ for a, t_ in acc["tarp_t"] if a == amp and len(t_) == nd]
                tarp_by_amp[f"{amp}|{nd}"] = tarp(S_, T_, np.random.default_rng(SEED_SAMPLES + 1))
            res[group] = {"examples_halves": len(acc["eff"]),
                          "mode_separation_median": statistics.median(acc["sep"]) if acc["sep"] else None,
                          "mode_separation_audible_median": statistics.median(acc["sep_audible"]) if acc["sep_audible"]
                          else None,
                          "exp_entropy_median": statistics.median(acc["eff"]) if acc["eff"] else None,
                          "top_weight_median": statistics.median(acc["top_w"]) if acc["top_w"] else None,
                          "top_vs_mixture_median": statistics.median(acc["top_vs_mix"]) if acc["top_vs_mix"] else None,
                          "settings": per, "tarp": tarp_by_amp,
                          "switch_ece": {n: ece(*v) for n, v in acc["sw"].items() if v[0]},
                          "mic_ece": {n: ece(*v) for n, v in acc["mic"].items() if v[0]},
                          "mic_accuracy": {n: statistics.fmean(v[1]) for n, v in acc["mic"].items() if v[1]}}
            print(f, group, res[group]["examples_halves"], flush=True)
        out["folds"][f] = res
    key = "mode_separation_audible_median" if flat is not None else "mode_separation_median"
    out["collapse_flag"] = collapse_flag({f: out["folds"][f]["own"][key] for f in range(4)})
    out["collapse_basis"] = key
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "models.json", out)


def step_ks_replay():
    menu = _menu()
    out = {"runs": {}, "reproduced": True}
    for slug, amp in K.cells():
        p = K.OUT / "cells" / slug / amp / "result.json"
        if not p.exists():
            continue
        c = json.loads(p.read_text())
        cls = c["gain_class"] if "gain_class" in c else K.parts()[slug]["gain_class"]
        _, S = _S(menu, amp, cls)
        dims = K.space(amp, S)
        for search, held in K.DIRECTIONS:
            run = c["runs"][search]
            if "skipped" in run:
                continue
            ks = run["K_S"]
            x, xs, ok = replay_run(dims, S, ks["evals"], search)
            stored = st(json.loads((p.parent / f"K_S-{search}.json").read_text()))
            same = ok and sj(x) == sj(stored)
            out["reproduced"] &= same
            out["runs"][f"{slug}|{amp}|{search}"] = {"reproduced": same, "renders": len(xs),
                                                     "sets": equal_score_sets(xs, ks["evals"], held, dims) if same
                                                     else None}
    if not out["reproduced"]:
        out["note"] = "not reproduced by today's code: retry once at the commit that produced the runs"
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "ks-replay.json", out)
    print("reproduced:", out["reproduced"], len(out["runs"]))


def _preflight_windows():
    win = json.loads((B.OUT / "windows.json").read_text())
    p = sorted((w for w in win if w["fold"] == "all"), key=lambda w: (w["path"], w["start"]))
    return random.Random(SEED_SENS + 1).sample(p, PREFLIGHT_N)


def step_preflight():
    """On P1/P2 windows (never targets): S rendered twice, the repeat judged; then 20 timed judge
    calls."""
    import numpy as np

    menu = _menu()
    rr = K.Renderer()
    out = {"repeats": [], "judge_s": []}
    try:
        for n, w in enumerate(_preflight_windows()):
            amp = K.AMPS[n % 3]
            sel, S = _S(menu, amp, "clean")
            di = measured_di(w)
            y1 = rr.render(di, sel, S)
            y2 = rr.render(di, sel, S)
            d = judge_trimmed(trim(y1), y2, di)
            out["repeats"].append(max(d.values()))
            for _ in range(PREFLIGHT_JUDGE_CALLS // PREFLIGHT_N):
                t0 = time.perf_counter()
                judge_trimmed(trim(y1), y2, di)
                out["judge_s"].append(time.perf_counter() - t0)
    finally:
        rr.close()
    out["repeat_ok"] = all(finite(x) and x <= REPEAT_TOL + EPS for x in out["repeats"])
    out["judge_s_median"] = statistics.median(out["judge_s"])
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "preflight.json", out)
    print(json.dumps({k: out[k] for k in ("repeats", "repeat_ok", "judge_s_median")}))
    if not out["repeat_ok"]:
        raise SystemExit("a repeat exceeds 1e-3: amend the tolerance before the draw")


def _pools():
    cat = catalogue()
    kc = sorted(K.parts())
    ex_tracks, ex_crops, ex_bands = exclusions(cat, kc)
    fold_of = B.folds()
    win = json.loads((B.OUT / "windows.json").read_text())
    el = eligible_windows(win, fold_of, ex_tracks, ex_bands)
    back = eligible_backings(B.backings(), ex_crops, ex_bands)
    song_of = {c["di"]: c["song"] for c in cat.values()}
    song_of.update({str(pathlib.Path(c["crop"]) / "backing_instrumental.wav"): c["song"] for c in cat.values()
                    if c.get("crop")})
    song_of.update({str(pathlib.Path(c["crop"]) / "backing.wav"): c["song"] for c in cat.values() if c.get("crop")})
    by_fold = {f: [w for w in el if w["fold"] == f] for f in range(4)}
    return by_fold, back, song_of, ex_tracks, ex_bands


def step_draw(top_up=None):
    """targets.json (step 1.1) and sens.json (step 1.2). `top_up`: {fold: n more}, continuing the
    seeded order; existing targets are never changed."""
    menu = _menu()
    by_fold, back, song_of, ex_tracks, ex_bands = _pools()
    order = window_order(by_fold)
    ks_opt = B.ks_optima()
    path = OUT / "targets.json"
    old = json.loads(path.read_text()) if path.exists() else []
    if old and not top_up and (OUT / "sens.json").exists():
        raise SystemExit("targets.json exists; only --top-up may add to it")
    targets = list(old)
    for f in range(4):
        have = [t for t in old if t["fold"] == f]
        n = (top_up or {}).get(f, 0) if old else N_PER_FOLD      # targets kept; sens drawn below if missing
        if not n:
            continue
        ws = pick_windows([w for w in order[f] if not any(overlaps(w, t["window"]) for t in have)], n,
                          [t["window"] for t in have])
        assert len(ws) == n, f"fold {f}: only {len(ws)} non-overlapping windows left"
        for j, w in enumerate(ws, start=len(have)):
            t = target_attrs(len(targets), f, j, w, back, song_of, ks_opt, menu)
            _, S = _S(menu, t["amp"], t["class"])
            x, lab = draw_settings(t, S, random.Random(t["seed"]))
            t["settings"], t["label"] = sj(x), lab
            assert t["window"]["path"] not in ex_tracks and t["band"] not in ex_bands
            targets.append(t)
    assert_fold_clean(targets, json.loads((B.OUT / "examples.json").read_text()))
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(path, targets)
    if not (OUT / "sens.json").exists():
        rng = random.Random(SEED_SENS)
        # Sensitivity windows may share a target's track but never overlap a target window
        # (amended 2026-10-16: excluding whole target tracks left too few windows).
        target_ws = [t["window"] for t in targets]
        pool = sorted((w for f in range(4) for w in by_fold[f]
                       if not any(overlaps(w, u) for u in target_ws)),
                      key=lambda w: (w["path"], w["start"]))
        rng.shuffle(pool)
        sens, used = [], []
        for amp in K.AMPS:
            for _ in range(SENS_PER_AMP):
                w = next(w for w in pool if not any(overlaps(w, u) for u in used))
                used.append(w)
                cls = rng.choice(("clean", "crunch"))
                sel, S = _S(menu, amp, cls)
                bases = {"S": sj(S)}
                for b in range(SENS_BASES - 1):
                    kind = "broad" if b % 2 == 0 else "ks_prior"
                    centre = None
                    if kind == "ks_prior":
                        centre = rng.choice(sorted(p for rows in ks_opt.values() for a, c, p in rows
                                                   if a == amp and c == cls))
                    x, _ = draw_settings({"amp": amp, "type": kind, "centre": centre}, S, rng)
                    bases[f"P{b}"] = sj(x)
                sens.append({"amp": amp, "class": cls, "window": w, "bases": bases})
        K._atomic(OUT / "sens.json", sens)
    print(len(targets), "targets; ledger: append the drawn tracks and windows before any render")


def step_render_targets(shard):
    """Each target through its measure DI, twice (target and repeat): 24-bit FLAC for the judge,
    16-bit for the features, both with their peak."""
    import numpy as np

    from learn import knob_ceiling2 as K2

    check_shards(shard[1])
    guard = MemoryGuard()
    menu = _menu()
    targets = json.loads((OUT / "targets.json").read_text())
    d = OUT / "targets"
    d.mkdir(parents=True, exist_ok=True)
    rr = K.Renderer()
    try:
        for t in sorted(targets[shard[0]::shard[1]], key=lambda t: (t["amp"], t["class"], t["i"])):
            f = d / f"{t['i']:03d}.json"
            if f.exists():
                continue
            if not K2.disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            sel, _ = _S(menu, t["amp"], t["class"])
            di = measured_di(t["window"])
            y = trim(rr.render(di, sel, st(t["settings"])))
            p24 = save_flac(d / f"{t['i']:03d}-24.flac", y, "PCM_24")
            p16 = save_flac(d / f"{t['i']:03d}-16.flac", y, "PCM_16")
            yr = rr.render(di, sel, st(t["settings"]))
            ref = load_flac(d / f"{t['i']:03d}-24.flac", p24)
            rep = judge_trimmed(ref, yr, di)
            K._atomic(f, {"peak24": p24, "peak16": p16, "repeat": rep, "renders": 2})
            guard.tick()
            guard.tick()
            print(t["i"], rep, flush=True)
    finally:
        rr.close()


def mixture_views(g, back, rng, levels, eval_mix_lufs, tmp, aac_on, separator):
    """The two views of one target (no second guitar): (stem, mix) for 1a and 1b."""
    import numpy as np

    from learn import song_aug as A

    n = len(g)
    back = back.mean(axis=1) if back.ndim == 2 else back
    back = np.pad(back, (0, max(0, n - len(back))))[:n]
    g2b = rng.choice(levels)
    lg, lb = A.lufs(g), A.lufs(back)
    gain_b = 10 ** ((lg - g2b - lb) / 20) if lb > -70 else 0.0
    mix = g + back * gain_b
    k = 10 ** ((eval_mix_lufs + rng.uniform(-3, 3) - A.lufs(mix)) / 20)
    g, mix = g * k, mix * k
    out = {"1a": (g, mix)}
    m = A.compress(mix, rng)
    if aac_on:
        m = A.aac(m, rng, tmp)
    out["1b"] = (separator(m.astype(np.float32)).astype(np.float64), m)
    return out


def step_features():
    import tempfile

    import numpy as np
    import soundfile as sf

    from learn import song_aug as A
    from learn.separate import GuitarSeparator

    set_threads()
    targets = json.loads((OUT / "targets.json").read_text())
    lv = json.loads((B.OUT / "levels.json").read_text())
    levels = list(lv["guitar_to_backing_db"].values())
    d = OUT / "targets"
    sep = GuitarSeparator()
    with tempfile.TemporaryDirectory() as tmp:
        for t in targets:
            f = d / f"{t['i']:03d}-features.npz"
            if f.exists():
                continue
            meta = json.loads((d / f"{t['i']:03d}.json").read_text())
            g = load_flac(d / f"{t['i']:03d}-16.flac", meta["peak16"])
            back, _ = sf.read(t["backing"], dtype="float64")
            views = mixture_views(g, back, random.Random(t["seed"] ^ 0x5EED), levels,
                                  lv["summary"]["eval_mix_lufs_median"], tmp, t["aac"], sep)
            arr = {}
            for v, (stem, mix) in views.items():
                ft = A.features(stem, mix)
                for h in "AB":
                    arr[f"{v}_feat{h}"], arr[f"{v}_lufs{h}"] = ft[h]
            np.savez(f, **arr)
            print(t["i"], flush=True)


def step_propose():
    """Every candidate's settings per target -> candidates.json, with the render-budget check and
    the top-mean parity check on 3 stored control inputs."""
    import numpy as np

    from learn import song_armb as AB
    from learn import song_model as M

    set_threads()
    menu = _menu()
    targets = json.loads((OUT / "targets.json").read_text())
    nets = {f: M.load_net(f) for f in range(4)}
    ex = json.loads((B.OUT / "examples.json").read_text())
    bank = {}
    for e in ex:
        r = B.OUT / "renders" / f"{e['i']:05d}.json"
        if r.exists():
            bank.setdefault((e["fold"], e["amp"], e["class"]), []).append(json.loads(r.read_text())["settings"])
    # parity: our top mean == predict_settings on 3 stored control inputs
    parity = True
    ctl = json.loads((B.OUT.parent / "armB/control-targets.json").read_text())[:3]
    for c in ctl:
        fz = B.OUT.parent / "armB/control" / f"{c['i']:03d}-features.npz"
        dz = np.load(fz)
        _, S = _S(menu, c["amp"], c["class"])
        a, _ = M.predict_settings(nets[c["fold"]], dz["featA"], dz["lufsA"], c["amp"], c["class"], S)
        b = top_mean_settings(net_heads(nets[c["fold"]], dz["featA"], dz["lufsA"], c["amp"], c["class"]),
                              c["amp"], S)
        parity &= sj(a) == sj(b)
    out = {"parity_ok": parity, "targets": {}}
    for t in targets:
        f, amp, cls = t["fold"], t["amp"], t["class"]
        _, S = _S(menu, amp, cls)
        dz = np.load(OUT / "targets" / f"{t['i']:03d}-features.npz")
        heads = {(v, h): net_heads(nets[f], dz[f"{v}_feat{h}"], dz[f"{v}_lufs{h}"], amp, cls) for v in VIEWS for h in "AB"}
        tx = st(t["settings"])
        c = {"target": tx, "target_repeat": tx, "S": S}
        c.update(model_candidates(heads, t["i"], amp, S))
        c["median"] = AB.bank_median(f, amp, cls, S)
        c["constant"] = AB.constant_settings(f, amp, cls, S)
        pool = [d for (g, a, k), v in bank.items() if g != f and a == amp and k == cls for d in v]
        c.update(baselines(t, S, tx, pool, baseline_rng(t["i"])))
        out["targets"][str(t["i"])] = {n: sj(x) for n, x in c.items()}
    sens = json.loads((OUT / "sens.json").read_text())
    n_sens = sum(1 + len(sens_moves(s["amp"], st(b))) for s in sens for b in s["bases"].values())
    planned = planned_renders([{n: st(x) for n, x in v.items()} for v in out["targets"].values()], n_sens)
    out["planned_renders"] = planned
    if not budget_ok(planned):
        raise SystemExit(f"planned {planned} renders > the {RENDER_CAP} hard stop: ask the user")
    K._atomic(OUT / "candidates.json", out)
    print("parity", parity, "planned renders", planned)


def step_score(shard):
    import numpy as np

    from learn import knob_ceiling2 as K2

    check_shards(shard[1])
    guard = MemoryGuard()
    menu = _menu()
    targets = {str(t["i"]): t for t in json.loads((OUT / "targets.json").read_text())}
    cpath = OUT / "candidates.json"
    cands, chash = json.loads(cpath.read_text())["targets"], file_hash(cpath)
    d = OUT / "scores"
    d.mkdir(parents=True, exist_ok=True)
    rr = K.Renderer()
    try:
        for key in sorted(cands, key=int)[shard[0]::shard[1]]:
            f = d / f"{int(key):03d}.json"
            if f.exists():
                continue
            if not K2.disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            t = targets[key]
            meta = json.loads((OUT / "targets" / f"{int(key):03d}.json").read_text())
            sel, _ = _S(menu, t["amp"], t["class"])
            di = measured_di(t["window"])
            ref = load_flac(OUT / "targets" / f"{int(key):03d}-24.flac", meta["peak24"])
            c = {n: st(x) for n, x in cands[key].items() if n not in ("target", "target_repeat")}
            first, of = render_plan(c)
            dist = {k: judge_trimmed(ref, rr.render(di, sel, c[n]), di) for k, n in first.items()}
            for _ in first:
                guard.tick()
            res = {n: dist[of[n]] for n in c}
            res["target"] = {"A": 0.0, "B": 0.0}
            res["target_repeat"] = meta["repeat"]
            K._atomic(f, {"candidates_hash": chash, "renders": len(first), "d": res})
            print(key, len(first), flush=True)
    finally:
        rr.close()


def step_sensitivity(shard):
    import numpy as np

    from analysis.aligned import _logmel
    from learn import knob_ceiling2 as K2

    check_shards(shard[1])
    guard = MemoryGuard()
    menu = _menu()
    sens = json.loads((OUT / "sens.json").read_text())
    d = OUT / "sens"
    d.mkdir(parents=True, exist_ok=True)
    rr = K.Renderer()
    try:
        for n, s in list(enumerate(sens))[shard[0]::shard[1]]:
            f = d / f"{n:02d}.json"
            if f.exists():
                continue
            if not K2.disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            sel, _ = _S(menu, s["amp"], s["class"])
            di = measured_di(s["window"])
            out = {}
            for bname, b in s["bases"].items():
                base = st(b)
                yb = trim(rr.render(di, sel, base))
                mb = _logmel(yb, 2048, SR)[0]
                deltas, cols, names = {}, [], []
                for name, x in sens_moves(s["amp"], base).items():
                    y = rr.render(di, sel, x)
                    guard.tick()
                    jd = judge_trimmed(yb, y, di)
                    deltas[name] = statistics.fmean(jd.values()) if all(finite(v) for v in jd.values()) else None
                    dim = next(dd for dd in K.space(s["amp"], base) if dd.name == name)
                    if dim.kind in ("cont", "log"):
                        step_signed = float(dim.to_unit(x[(dim.module, dim.key)])
                                            - dim.to_unit(base[(dim.module, dim.key)])) or SENS_STEP
                        cols.append(((_logmel(trim(y), 2048, SR)[0] - mb) / step_signed).ravel())   # signed move
                        names.append(name)
                J = np.stack(cols, axis=1) if cols else np.zeros((1, 0))
                out[bname] = {"delta": deltas, "gram_settings": names, "gram": (J.T @ J).tolist()}
            K._atomic(f, {"amp": s["amp"], "bases": out})
            print(n, flush=True)
    finally:
        rr.close()


def _sens_summary():
    files = sorted((OUT / "sens").glob("*.json"))
    deltas, grams = {}, {}
    for p in files:
        s = json.loads(p.read_text())
        for b in s["bases"].values():
            for n, v in b["delta"].items():
                if v is not None:
                    deltas.setdefault(s["amp"], {}).setdefault(n, []).append(v)
            grams.setdefault((s["amp"], tuple(b["gram_settings"])), []).append(b["gram"])
    flat = flat_settings(deltas)
    jac = {f"{a}|{'/'.join(n)}": jacobian_summary(g) for (a, n), g in grams.items() if n}
    return flat, jac, deltas


def build_units(targets, cands, scores, flat):
    """The units of the readings, from stored files (plain dicts)."""
    menu = _menu()
    units = []
    for t in targets:
        key = str(t["i"])
        if key not in scores:
            continue
        _, S = _S(menu, t["amp"], t["class"])
        dims = K.space(t["amp"], S)
        tx = st(t["settings"])
        c = {n: st(x) for n, x in cands[key].items()}
        d = scores[key]["d"]
        for search, held in DIRS:
            units.append({"fold": t["fold"], "band": t["band"], "target": t["i"], "type": t["type"],
                          "search": search, "held": held,
                          "d": {n: v[held] for n, v in d.items()}, "s": {n: v[search] for n, v in d.items()},
                          "key": {n: skey(x) for n, x in c.items()},
                          "knob": {n: knob_distance(x, tx, dims, flat.get(t["amp"], ())) for n, x in c.items()},
                          "mic_match": {n: mics_match(x, tx, dims) for n, x in c.items()}})
    return units


def step_report():
    targets = json.loads((OUT / "targets.json").read_text())
    cj = json.loads((OUT / "candidates.json").read_text())
    chash = file_hash(OUT / "candidates.json")
    scores = {}
    for p in sorted((OUT / "scores").glob("*.json")):
        s = json.loads(p.read_text())
        assert s["candidates_hash"] == chash, f"{p.name} scored from another candidates.json"
        scores[str(int(p.stem))] = s
    flat, jac, _ = _sens_summary()
    K._atomic(OUT / "flat.json", flat)
    units = build_units(targets, cj["targets"], scores, flat)
    pre = json.loads((OUT / "preflight.json").read_text())
    reps = {t: tuple(v["d"]["target_repeat"][h] for h in "AB") for t, v in scores.items()}
    dropped = set(setup_check(pre["repeats"], reps, {}, cj["parity_ok"])["targets_dropped_repeat"])
    units = [u for u in units if str(u["target"]) not in dropped]          # repeat failures dropped first
    inf_by = {f: sum(informative(u) for u in units if u["fold"] == f) for f in range(4)}
    setup = setup_check(pre["repeats"], reps, inf_by, cj["parity_ok"])
    rd = readings(units, setup)
    models = json.loads((OUT / "models.json").read_text()) if (OUT / "models.json").exists() else {}
    total = sum(s["renders"] for s in scores.values()) + 2 * len(scores) + len(pre["repeats"]) * 2
    rep = {"setup": setup, "readings": rd, "trigger_row": rd["trigger"], "trigger": TRIGGERS[rd["trigger"]],
           "collapse_flag": models.get("collapse_flag"), "flat": flat, "jacobian": jac,
           "pooled": {"R1_top_vs_S_1b": pooled(units, lambda u: math.log(u["d"]["1b:" + u["search"] + ":top"] /
                                                                          u["d"]["S"])
                                                if finite(u["d"].get("1b:" + u["search"] + ":top")) else None)},
           "renders_so_far": total}
    if setup["folds_short"]:
        rep["top_up"] = {f: math.ceil((MIN_INFORMATIVE - n) / 2) for f, n in setup["folds_short"].items()}
    K._atomic(OUT / "report.json", rep)
    K._atomic(DOCS_SUMMARY, {k: rep[k] for k in ("setup", "trigger_row", "trigger", "collapse_flag", "flat")}
              | {"status": rd["status"], "R3": rd["R3"], "landscape": rd["landscape"],
                 "label_sampling_flag": rd["label_sampling_flag"]})
    print(json.dumps({"trigger_row": rd["trigger"], "status": rd["status"], "landscape": rd["landscape"]}, indent=1))


# --- step 1.3 (ask first) ---

def step13_propose(approved):
    require_user_approval(approved)
    import numpy as np

    from learn import song_model as M
    from learn import song_settings as SS

    set_threads()
    menu = _menu()
    fo, ps = B.folds(), K.parts()
    nets = {f: M.load_net(f) for f in range(4)}
    ev = B.OUT.parent / "eval-features"
    out = {}
    for slug, amp, search, held in SS.cells():
        part = ps[slug]
        _, S = _S(menu, amp, part["gain_class"])
        dz = np.load(ev / f"{slug}.npz")
        h = net_heads(nets[fo[part["band"]]], dz[f"feat{search}"], dz[f"lufs{search}"], amp, part["gain_class"])
        rng = np.random.default_rng(np.random.SeedSequence([STEP13_SEED, *map(ord, f"{slug}|{amp}|{search}")]))
        out[f"{slug}|{amp}|{search}"] = [sj(settings_from(amp, S, *sample_units(h, rng))) for _ in range(STEP13_SAMPLES)]
    K._atomic(OUT / "step13-candidates.json", out)


def step13_score(approved, shard):
    require_user_approval(approved)
    import numpy as np

    from learn import confirm_run as CR

    check_shards(shard[1])
    guard = MemoryGuard()
    menu = _menu()
    ps = K.parts()
    c = json.loads((OUT / "step13-candidates.json").read_text())
    d = OUT / "step13"
    d.mkdir(parents=True, exist_ok=True)
    rr = K.Renderer()
    try:
        for key in sorted(c)[shard[0]::shard[1]]:
            f = d / f"{key.replace('|', '_')}.json"
            if f.exists():
                continue
            slug, amp, search = key.split("|")
            part = ps[slug]
            sel, _ = _S(menu, amp, part["gain_class"])
            di = K.measure_di(part)
            ref = CR.mono(part["crop"] / "reference.wav")
            res = []
            for x in c[key]:
                res.append(K.judge(ref, rr.render(di.astype(np.float32), sel, st(x)), di, part["judge_lag"]))
                guard.tick()
            K._atomic(f, res)
    finally:
        rr.close()


def step13_report(approved):
    require_user_approval(approved)
    ps = K.parts()
    rows = []
    for p in sorted((OUT / "step13").glob("*.json")):
        res = json.loads(p.read_text())
        slug, amp, search = next(k for k in json.loads((OUT / "step13-candidates.json").read_text())
                                 if k.replace("|", "_") == p.stem).split("|")
        held = "B" if search == "A" else "A"
        pick = best_of({"s": {str(i): r[search] for i, r in enumerate(res)}}, [str(i) for i in range(len(res))])
        kc = json.loads((K.OUT / "cells" / slug / amp / "result.json").read_text())["runs"][search]["K_S"]
        curve = kc["curve"]
        rows.append({"band": ps[slug]["band"], "pick": res[int(pick)][held] if pick is not None else math.inf,
                     "KS16": curve[min(15, len(curve) - 1)][2], "S": kc["start_held"]})
    rep = step13_reading(rows)
    K._atomic(OUT / "step13-report.json", rep)
    print(rep["reading"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("models", "ks-replay", "preflight", "draw", "render-targets", "features",
                                     "propose", "score", "sensitivity", "report", "step13-propose", "step13-score",
                                     "step13-report"))
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--top-up", default=None, help="FOLD:N[,FOLD:N]: continue the seeded draw for short folds")
    ap.add_argument("--user-approved", action="store_true", help="step 1.3 only: the user's own yes")
    a = ap.parse_args(argv)
    i, n = map(int, a.shard.split("/"))
    top = {int(x.split(":")[0]): int(x.split(":")[1]) for x in a.top_up.split(",")} if a.top_up else None
    {"models": step_models, "ks-replay": step_ks_replay, "preflight": step_preflight,
     "draw": lambda: step_draw(top), "render-targets": lambda: step_render_targets((i, n)),
     "features": step_features, "propose": step_propose, "score": lambda: step_score((i, n)),
     "sensitivity": lambda: step_sensitivity((i, n)), "report": step_report,
     "step13-propose": lambda: step13_propose(a.user_approved),
     "step13-score": lambda: step13_score(a.user_approved, (i, n)),
     "step13-report": lambda: step13_report(a.user_approved)}[a.step]()


if __name__ == "__main__":
    main()
