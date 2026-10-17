"""Arm A's local objective: step 0 and experiment 1 (`docs/local-objective-plan.md`).
Development only; estimates with 90% band-clustered intervals, no pass/fail bars.

    .venv/bin/python -m learn.local_objective align                    # step 0: the alignment table, zero renders
    .venv/bin/python -m learn.local_objective diag                     # step 0: zero renders
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective pregain  # step 0: 5 renders
    .venv/bin/python -m learn.local_objective sigma                    # experiment 1: freeze Σ (zero renders)
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective render --shard 0/3 [--after PID ...]
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective score --workers 3      # CPU, from the FLACs
    .venv/bin/python -m learn.local_objective report
    # the optional DAC-9 add-on (fold 3 only, on the user's yes):
    .venv/bin/python -m learn.local_objective dac-prep
    ~/ndsp-presets/tools/dac-venv/bin/python learn/dac_roundtrip.py --inp <OUT>/dac/in --out <OUT>/dac/out
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective render --di dac9 --shard 0/3
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective score --di dac9 --workers 3
    # experiment 1b, the matched cell (amendment 2):
    ~/ndsp-presets/tools/demucs-venv/bin/python -m learn.local_objective rebuild-ref   # CPU, zero renders
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective render --di cprime_ref --shard i/3
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective score --di cprime_ref --workers 3
    .venv/bin/python -m learn.local_objective report-1b
    # the DAC add-on's extension to the other 57 cells, if the fold-3 reading is undecided (the user's yes):
    dac-prep --all-folds; the DAC round trip; render --di dac9 --all-folds --shard i/3; score --di dac9
    # experiment 1c, a real separator in 1b's design (amendment 3): separate, rebuild and report are in
    # learn/local_objective_1c.py; the renders and scores are here:
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective render --di cprime_mega53 --shard i/3
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective score --di cprime_mega53,cprime@mega53 --workers 3
    # experiment 1d, the separator-robust rebuild in 1b's design (amendment 4): rebuild and report in
    # learn/local_objective_1d.py; the renders and scores are here:
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective render --di csep_stem,csep_mega53 --shard i/3
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective score --di csep_stem,csep_mega53 --workers 3

Σ (experiment 1's settings): per (part, amp) cell, S, its ±1/8 coordinate neighbourhood (switches
flipped), a seeded draw from both K_S directions' replayed trajectories up to 40, and 8 seeded
points from arm A's replayed paths. Each setting renders through C′'s rebuild of the stem and
through the measure DI, saved as 16-bit FLAC. Scoring crosses DI × reference × lag × mask, the lags
relative to each DI's native alignment (amendment 1).

The pure parts (Σ, the scorer's factorial, the fidelity measures, the step-0 statistics, the
guards) are unit-tested with fakes; the commands that render are not, like the other step modules.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import pathlib
import random
import re
import shutil
import statistics
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import arm_a_levers as L  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import song_readout as R  # noqa: E402

OUT = K.HOME / "learn/local-objective"
HALVES = ("A", "B")

# --- Σ ----------------------------------------------------------------------------------------------
STEP = 1 / 8                     # the neighbourhood's coordinate step (unit scale): 4 dB of input gain
N_FILL = 40                      # neighbourhood + K_S draw
N_ARM_A = 8                      # points from arm A's paths
SEED_KS = 20261032               # random.Random(f"{SEED_KS}|{slug}|{amp}")
SEED_A = 20261033                # random.Random(f"{SEED_A}|{slug}|{amp}")
EXCLUDED = ("telefunken-Honey-GTR",)
SIGMA_HASH = "ee91f710947dbb5c"  # Σ as declared in the plan (computed with zero renders, 2026-10-16)

# --- scoring: the factorial -------------------------------------------------------------------------
DIS = ("cprime", "measure")      # experiment 1's DIs; "dac9" is the optional add-on (fold 3)
REFS = ("stem", "reference")
# Amendment 1: lag levels relative to each DI's native alignment. Native is −52 for a rebuild
# (rebuilt_distance's, the current objective) and the part's judge_lag for the measure DI and
# DAC-9; "other" is the other DI's native lag; "zero" is 0; "gcc" (rebuilds only, deployable) is
# −52 − GCC(rebuild, stem), the rebuild's own measured alignment with the stem.
LAGS = ("native", "other", "zero")
REBUILT_LAGS = ("gcc",)
MASKS = ("own", "record")        # "record" = the reference in use (stem or reference.wav), in DI time
CURRENT = ("cprime", "stem", "native", "own")       # the rebuilt objective arm A searched with
TRUE = ("measure", "reference", "native", "own")    # the judge through the measure DI (true d)
DECISIVE = ("measure", "stem", "native", "own")     # the best any DI fix could do with a song's reference
CHECK_TOL = 0.005                # |log| between a corner and its stored value (knob_ceiling.REPEAT_TOL)
# Amendment 3 (experiment 1c): a real separator feeds both C′'s rebuild and the reference, in 1b's
# matched design. Each separator's stem crop is a reference ("mega53", "blend"); C′ rebuilt from it
# is the DI "cprime_<separator>" (`learn/local_objective_1c.py` separates, blends and rebuilds).
SEPARATORS = ("mega53", "blend")
SEP_DI = {s: f"cprime_{s}" for s in SEPARATORS}
# Amendment 4 (experiment 1d): the separator-robust networks (docs/cprime-sep-plan.md) rebuild step
# 3's htdemucs stem ("csep_stem") and 1c's Mega-53 crop ("csep_mega53"), each scored against its
# own source (`learn/local_objective_1d.py` rebuilds and reports).
SEPNET_SOURCES = ("stem", "mega53")
SEPNET_DI = {s: f"csep_{s}" for s in SEPNET_SOURCES}
SEPNET_PATTERN = "learn/direc-sep/models-sep-f{f}/fold{f}.pt"      # under K.HOME
REBUILT = ("cprime", "cprime_ref", *SEP_DI.values(), *SEPNET_DI.values())   # judged with rebuilt_distance's fallback
# Amendment 2 (experiment 1b): the matched cell. Each part's fold C′ rebuilds reference.wav (the
# amp track) instead of the stem, re-EQ'd and levelled as `song_settings.rebuild_all` does, and is
# scored against reference.wav: the ceiling for any separator with today's C′.
MATCHED_DI = "cprime_ref"
REBUILD_SOURCE = {"cprime": "stem", "cprime_ref": "reference", **{d: s for s, d in SEP_DI.items()},
                  **{d: s for s, d in SEPNET_DI.items()}}
REBUILD_DIR = {"cprime_ref": "rebuilt-ref", **{d: f"rebuilt-{s}" for s, d in SEP_DI.items()},
               **{d: f"rebuilt-csep-{s}" for s, d in SEPNET_DI.items()}}
NO_STORED = (MATCHED_DI, "dac9", *SEP_DI.values(), *SEPNET_DI.values())   # S's repeat is the render check
# 1c's rescoring of experiment 1's C′ renders against a separator's stem (zero renders): a score
# "view" name -> (the DI whose renders it reads, its configurations).
VIEWS = {f"cprime@{s}": ("cprime", (("cprime", s, "native", "own"),)) for s in SEPARATORS}
MATCHED = ("cprime_ref", "reference", "native", "own")
MATCHED_GCC = ("cprime_ref", "reference", "gcc", "own")      # diagnostic
SUBSETS = {"all": ("S", "nbr", "ks", "armA"), "neighbourhood": ("S", "nbr"), "ks": ("ks",), "armA": ("armA",)}
NEAR_GAP_SHARE = 0.25            # 1b's reading: "near" if the interval's top closes under this share of the gap
REBUILD_LAG_TOL = 3              # samples: |GCC(matched rebuild, C′'s stem rebuild)| at most this (amendment 2a)
REBUILD_LUFS = -22.9
REBUILD_LUFS_TOL = 0.05          # LU
EXPECTED_1B = {"cells": 72, "renders": 3528}
LARGE_OFFSET = 100               # samples: |judge_lag + 52| beyond this marks a large-offset part (3 of 24)

# --- machine ----------------------------------------------------------------------------------------
CAP = 3                          # render processes machine-wide, this one included
RENDERS = (r"-m learn\.song_relabel (render-new|probe)\b", r"-m learn\.ks_extend run\b",
           r"-m learn\.local_objective (render|pregain)\b",
           r"-m learn\.song_soundspace (score-targets|score-songs|c-start)\b")
# Separations that need the machine to themselves (amendment 3): no render starts beside one.
SEPARATIONS = (r"-m learn\.local_objective_1c separate\b", r"-m learn\.separator_screen (separate|identity)\b",
               r"-m learn\.separate\b")
DISK_GUARD_GB = 31.0             # the ML plan's 30 GB rule, as the other steps apply it
MB_PER_RENDER = 0.7              # measured: 48 step-0b 10-s 16-bit FLACs, mean 0.48 MB, max 0.68 MB
PEAK_TO = 0.99

# --- step 0 -----------------------------------------------------------------------------------------
PREGAIN_CELL = ("cambridge-just-don-t-talk-elecgtr3", "pr12")   # S = pr12 clean: its compressor is on
PREGAIN_FALLBACK_CELL = ("cambridge-just-don-t-talk-elecgtr3", "sw50r")   # compressor off; on a miss only
PREGAIN_DB = 6.0
INPUT_GAIN = ("parameters", "inputGain")
TRIM_S = 0.25                    # the isolate fade-in, left out of the waveform comparison


def _k(d):
    return (d.module, d.key)


def sdict(x):
    """{(module, key): v} -> {"module/key": v} (JSON)."""
    return {f"{a}/{b}": v for (a, b), v in sorted(x.items())}


def tdict(x):
    return {tuple(k.rsplit("/", 1)): v for k, v in x.items()}


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _pos(x):
    return _finite(x) and x > 0


# --- Σ: the settings ----------------------------------------------------------------------------------

def neighbourhood(dims, S, step=STEP):
    """S and its coordinate neighbourhood: each continuous dim ±`step` in unit space (clamped; a side
    that clamps onto S is dropped), each switch flipped; mics are left to the K_S and arm A points.
    Values are formatted as `coord_search` formats its candidates. -> [(tag, x)], tag = {"source",
    "dim", "side"}; deduplicated by `K.key`."""
    out, seen = [({"source": "S", "dim": None, "side": "0"}, dict(S))], {K.key(S)}
    for d in dims:
        k = _k(d)
        if d.kind in ("cont", "log"):
            u = L.unit(d, S)
            for side, s in (("-", -step), ("+", step)):
                v = min(max(u + s, 0.0), 1.0)
                if abs(v - u) < 1e-12:
                    continue
                x = dict(S)
                x[k] = K.fmt(d.from_unit(v))
                if K.key(x) not in seen:
                    seen.add(K.key(x))
                    out.append(({"source": "nbr", "dim": d.name, "side": side}, x))
        elif d.kind == "switch":
            cur = S.get(k)
            cands = [v for v in d.values if v != cur][:1]
            for v in cands:
                x = dict(S)
                x[k] = v
                if K.key(x) not in seen:
                    seen.add(K.key(x))
                    out.append(({"source": "nbr", "dim": d.name, "side": "flip"}, x))
    return out


def pool(paths):
    """paths: [[(x, value_dict), ...], ...] -> {key: (x, merged values)}; the first x of a key is kept,
    later values for the same key fill halves not yet seen."""
    out = {}
    for path in paths:
        for x, v in path:
            k = K.key(x)
            if k not in out:
                out[k] = (x, dict(v))
            else:
                for h, d in v.items():
                    out[k][1].setdefault(h, d)
    return out


def cell_sigma(slug, amp, dims, S, ks_paths, a_paths, n_fill=N_FILL, n_a=N_ARM_A, seed_ks=SEED_KS, seed_a=SEED_A):
    """One cell's Σ. ks_paths: both directions' K_S trajectories [(x, {"A": d, "B": d})]; a_paths:
    both directions' arm A paths [(x, {search half: rebuilt objective})]. -> [point], each
    {"x", "key", "source", "dim", "side", "true_stored", "obj_stored"}; the stored values are those
    of any K_S or arm A evaluation with the same key (the corner checks)."""
    ks, aa = pool(ks_paths), pool(a_paths)
    pts = []
    for tag, x in neighbourhood(dims, S):
        pts.append({**tag, "x": x, "key": K.key(x)})
    have = {p["key"] for p in pts}
    rest = sorted(k for k in ks if k not in have)
    need = max(0, n_fill - len(pts))
    for k in random.Random(f"{seed_ks}|{slug}|{amp}").sample(rest, min(need, len(rest))):
        pts.append({"source": "ks", "dim": None, "side": None, "x": ks[k][0], "key": k})
    have = {p["key"] for p in pts}
    rest = sorted(k for k in aa if k not in have)
    for k in random.Random(f"{seed_a}|{slug}|{amp}").sample(rest, min(n_a, len(rest))):
        pts.append({"source": "armA", "dim": None, "side": None, "x": aa[k][0], "key": k})
    for p in pts:
        p["true_stored"] = ks[p["key"]][1] if p["key"] in ks else None
        p["obj_stored"] = aa[p["key"]][1] if p["key"] in aa else None
    return pts


def sigma_json(sigma):
    """{(slug, amp): [point]} -> the frozen, JSON-ready Σ (settings as "module/key")."""
    return {f"{s}|{a}": [{**{k: v for k, v in p.items() if k != "x"}, "x": sdict(p["x"])} for p in pts]
            for (s, a), pts in sorted(sigma.items())}


def sigma_hash(sj):
    """A hash of Σ's settings only (keys and order), written into the plan's record when frozen."""
    flat = [[c, [p["key"] for p in pts]] for c, pts in sorted(sj.items())]
    return hashlib.sha256(json.dumps(flat).encode()).hexdigest()[:16]


def expected_renders(sj, dis=DIS, cells=None):
    """Settings × DIs plus one warm-up per (cell, DI)."""
    cs = [c for c in sj if cells is None or c in cells]
    return sum(len(sj[c]) for c in cs) * len(dis) + len(cs) * len(dis)


def arm_a_path(amp, S, curve, budget=L.BUDGET, seed=L.SEED):
    """Arm A's stored search replayed with zero renders. -> ([(x, value)], final x)."""
    rep = L.Replay(curve)
    x, _, _, _ = K.knob_search(K.space(amp, S), S, rep, budget, seed)
    return list(zip(rep.xs, curve)), x


# --- scoring: the factorial ---------------------------------------------------------------------------

def configs(di):
    """The scoring configurations for renders through `di`: reference × lag × mask (12), plus
    for a rebuild the GCC-aligned lag (4 more)."""
    if di == MATCHED_DI:                                               # amendment 2: two only
        return [MATCHED, MATCHED_GCC]
    if di in SEP_DI.values():                                          # amendment 3: matched, gcc, rebuild-only
        s = REBUILD_SOURCE[di]
        return [(di, s, "native", "own"), (di, s, "gcc", "own"), (di, "stem", "native", "own")]
    if di in SEPNET_DI.values():                                       # amendment 4: matched, gcc, other source
        s = REBUILD_SOURCE[di]
        other_ = "mega53" if s == "stem" else "stem"
        return [(di, s, "native", "own"), (di, s, "gcc", "own"), (di, other_, "native", "own")]
    if di in VIEWS:
        return list(VIEWS[di][1])
    lags = LAGS + (REBUILT_LAGS if di in REBUILT else ())
    return [(di, r, g, m) for r in REFS for g in lags for m in MASKS]


def cname(c):
    return "|".join(c)


def render_di(d):
    """The DI whose renders a score name reads: itself, or a view's DI (amendment 3)."""
    return VIEWS[d][0] if d in VIEWS else d


def lag_value(level, di, judge_lag, gcc=None, obj_lag=L.OBJ_LAG):
    """A lag level's value in samples for renders through `di` (amendment 1)."""
    native, other_ = (obj_lag, judge_lag) if di in REBUILT else (judge_lag, obj_lag)
    if level == "gcc":
        if di not in REBUILT or gcc is None:
            raise ValueError("the gcc level is for a rebuild with its measured GCC lag")
        return obj_lag - gcc
    return {"native": native, "other": other_, "zero": 0}[level]


def gcc_level(rebuilt, stem):
    """GCC(rebuild, its source): samples the rebuild lags the signal it was rebuilt from (the stem
    for C′, reference.wav for 1b's matched rebuild; `rank_margin.gcc_lag`)."""
    from learn import rank_margin as RM

    n = min(len(rebuilt), len(stem))
    return int(RM.gcc_lag(rebuilt[:n], stem[:n]))


def in_di_time(rec, lag, latency=None):
    """The recording moved into the DI's time base, for use as an activity mask: the judge reads
    the mask at DI time t − lag − latency for recording time t (`aligned_distance`), so the
    recording is advanced by lag + latency (zero-padded). Identity at lag = −latency."""
    import numpy as np

    from learn.rebuilt_judge import LATENCY

    s = int(lag) + (LATENCY if latency is None else latency)
    rec = np.asarray(rec)
    if s == 0:
        return rec
    out = np.zeros_like(rec)
    if abs(s) >= len(rec):
        return out
    if s > 0:
        out[:-s] = rec[s:]
    else:
        out[-s:] = rec[:s]
    return out


def score_render(y, di_name, signals, judge_lag, aligned, gcc=None, halves=K.R.HALVES, only=None):
    """Every configuration (or those in `only`) for one render. signals: {"di", "stem",
    "reference"} arrays; aligned(recording, render, mask, lag, start_s, end_s) -> (distance or
    None, reason) is the judge.
    - "own" mask: the DI itself. For a rebuild (C′) an activity refusal falls back to the
      recording as the mask, as `rebuilt_distance` does (the current objective); the measure DI
      and DAC-9 have no fallback, as `knob_ceiling.judge` has none (the true d).
    - "record" mask, and the fallback: the recording in use, moved into DI time by lag + 52
      (amendment 1; identical to `rebuilt_distance`'s at lag −52).
    A score view (amendment 3) is scored as its render DI, on the view's configurations.
    A refusal scores inf. -> ({config name: {"A": d, "B": d}}, {config name: fallbacks})."""
    from learn.rebuilt_judge import _ACTIVITY

    base = render_di(di_name)
    out, fb = {}, {}
    for c in configs(di_name):
        if only is not None and c not in only:
            continue
        _, ref, lag, mask = c
        rec, n = signals[ref], 0
        lg = lag_value(lag, base, judge_lag, gcc)
        rec_mask = None
        row = {}
        for h, (a, b) in halves.items():
            if mask == "own":
                d, why = aligned(rec, y, signals["di"], lg, a, b)
                if d is None and base in REBUILT and any(w in (why or "") for w in _ACTIVITY):
                    rec_mask = in_di_time(rec, lg) if rec_mask is None else rec_mask
                    d, _ = aligned(rec, y, rec_mask, lg, a, b)
                    n += 1
            else:
                rec_mask = in_di_time(rec, lg) if rec_mask is None else rec_mask
                d, _ = aligned(rec, y, rec_mask, lg, a, b)
            row[h] = math.inf if d is None else d
        out[cname(c)], fb[cname(c)] = row, n
    return out, fb


def judge_fns():
    """The real judge in `score_render`'s calling form."""
    from analysis.aligned import aligned_distance

    from learn.rebuilt_judge import LATENCY

    def aligned(rec, y, mask, lag, a, b):
        d = aligned_distance(rec, y, mask, lag=lag, render_latency=LATENCY, start_s=a, end_s=b)
        return d.distance, d.reason
    return aligned


def deviation(new, stored):
    """|log new/stored|; 0 when both are refusals, inf when only one is."""
    if not _pos(new) and not _pos(stored):
        return 0.0
    if not (_pos(new) and _pos(stored)):
        return math.inf
    return abs(math.log(new / stored))


def corner_checks(points, scores, di):
    """The two corners against their stored values: the true d (measure DI) against K_S's stored
    evaluations, the current objective (C′) against arm A's stored curves (search half) and 2b's
    stored objective. -> [(index, what, half, deviation)]."""
    out = []
    for i, p in enumerate(points):
        if di == "measure" and p.get("true_stored"):
            for h, v in p["true_stored"].items():
                out.append((i, "true_vs_KS", h, deviation(scores[i][cname(TRUE)][h], v)))
        if di == "cprime":
            for what, src in (("current_vs_armA", p.get("obj_stored")), ("current_vs_2b", p.get("obj_2b"))):
                for h, v in (src or {}).items():
                    out.append((i, what, h, deviation(scores[i][cname(CURRENT)][h], v)))
    return out


# --- fidelity -------------------------------------------------------------------------------------------

def rho(o, t):
    """Spearman over the points where both are finite and the truth positive ('pairwise', as 2b's
    headline −0.126); None with fewer than 3 points or a constant side."""
    from scipy.stats import spearmanr

    pairs = [(a, b) for a, b in zip(o, t) if _finite(a) and _pos(b)]
    if len(pairs) < 3 or len({a for a, _ in pairs}) < 2 or len({b for _, b in pairs}) < 2:
        return None
    r = spearmanr(*zip(*pairs)).correlation
    return float(r) if r is not None and math.isfinite(r) else None


def rho_worst(o, t):
    """Spearman with a refusal ranked as the worst on its side (`a7_local.py`'s convention)."""
    from scipy.stats import spearmanr

    f = lambda v: v if _finite(v) else math.inf  # noqa: E731
    a, b = [f(v) for v in o], [f(v) for v in t]
    if len(a) < 3 or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    r = spearmanr(a, b).correlation
    return float(r) if r is not None and math.isfinite(r) else None


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.fmean(xs) if xs else None


def other(h):
    return "B" if h == "A" else "A"


def same_half(obj, true, f=rho):
    """obj, true: {"A": [...], "B": [...]} over the same points. The mean over halves of f(obj_h, true_h)."""
    return _mean(f(obj[h], true[h]) for h in HALVES)


def cross_half(obj, true, f=rho):
    """The mean over halves of f(obj_h, true_h'): a search reads one half and is judged on the other."""
    return _mean(f(obj[h], true[other(h)]) for h in HALVES)


def ceiling(true, f=rho):
    """The true DI's own cross-half local Spearman."""
    return f(true["A"], true["B"])


def _sign(x):
    return (x > 0) - (x < 0)


def reliable_pairs(true):
    """Pairs whose true order is the same, and not tied, on both halves. -> [(i, j, sign)]."""
    n = len(true["A"])
    ok = [i for i in range(n) if _pos(true["A"][i]) and _pos(true["B"][i])]
    out = []
    for i, j in itertools.combinations(ok, 2):
        sa, sb = _sign(true["A"][i] - true["A"][j]), _sign(true["B"][i] - true["B"][j])
        if sa != 0 and sa == sb:
            out.append((i, j, sa))
    return out


def reliable_accuracy(obj, true, pairs=None):
    """The share of reliable pairs the objective orders as the truth does (a tie counts half), per
    half on the pairs it scores on both points, averaged over halves; None without pairs."""
    pairs = reliable_pairs(true) if pairs is None else pairs
    accs = []
    for h in HALVES:
        n = c = 0.0
        for i, j, s in pairs:
            a, b = obj[h][i], obj[h][j]
            if not (_finite(a) and _finite(b)):
                continue
            n += 1
            c += 1.0 if _sign(a - b) == s else 0.5 if a == b else 0.0
        accs.append(c / n if n else None)
    return _mean(accs)


def partial_rho(x, y, z):
    """Spearman partial correlation of x and y controlling z (the first-order formula on Spearman
    correlations), over the points where all three are finite; None if undefined."""
    from scipy.stats import spearmanr

    t = [(a, b, c) for a, b, c in zip(x, y, z) if _finite(a) and _finite(b) and _finite(c)]
    if len(t) < 4:
        return None
    cols = list(zip(*t))
    if any(len(set(c)) < 2 for c in cols):
        return None
    r = lambda u, v: spearmanr(u, v).correlation  # noqa: E731
    rxy, rxz, ryz = r(cols[0], cols[1]), r(cols[0], cols[2]), r(cols[1], cols[2])
    den = math.sqrt(max(0.0, (1 - rxz ** 2) * (1 - ryz ** 2)))
    return None if den < 1e-12 else float((rxy - rxz * ryz) / den)


def coord_pick(cands, values, start):
    """What `coord_search` keeps from a start and its candidates: the best candidate if it beats the
    start by more than 1e-12, else the start (a refusal is never picked)."""
    v = {i: (values[i] if _finite(values[i]) else math.inf) for i in [start, *cands]}
    best = min(cands, key=lambda i: (v[i], i)) if cands else start
    return best if v[best] < v[start] - 1e-12 else start


def three_way(points, obj, true):
    """Per neighbourhood dim and half: does the objective keep what the truth keeps among {S−, S, S+}
    (a switch: {S, flipped}), as one `coord_search` step does; and the regret, log true(kept by the
    objective) − log min true; and chance, 1 / the number of settings compared (1/2 where a side
    was clamped or for a switch: amendment 1). Truth refusals skip the dim.
    -> {dim: [(agree, regret, chance), ...]}."""
    s = next(i for i, p in enumerate(points) if p["source"] == "S")
    by = {}
    for i, p in enumerate(points):
        if p["source"] == "nbr":
            by.setdefault(p["dim"], []).append(i)
    out = {}
    for dim, cands in sorted(by.items()):
        for h in HALVES:
            idx = [s, *cands]
            if not all(_pos(true[h][i]) for i in idx):
                continue
            po, pt = coord_pick(cands, obj[h], s), coord_pick(cands, true[h], s)
            best = min(true[h][i] for i in idx)
            out.setdefault(dim, []).append((po == pt, math.log(true[h][po] / best), 1 / len(idx)))
    return out


def neighbourhood_regret(points, obj, true):
    """The objective's pick among the whole neighbourhood (S, ±1/8, flips), per half: log true(pick)
    − log min true over the neighbourhood; mean over halves (truth refusals skip the half)."""
    idx = [i for i, p in enumerate(points) if p["source"] in ("S", "nbr")]
    out = []
    for h in HALVES:
        if not all(_pos(true[h][i]) for i in idx):
            continue
        cand = [i for i in idx if _finite(obj[h][i])]
        if not cand:
            continue
        pick = min(cand, key=lambda i: (obj[h][i], i))
        out.append(math.log(true[h][pick] / min(true[h][i] for i in idx)))
    return _mean(out)


def pair_class(dims, x, y):
    """'categorical' if a mic or switch differs, else by the largest unit move: 'coarse' (≥ 0.25),
    'fine' (< 0.125) or 'mid'."""
    for d in dims:
        if d.kind in ("cat", "switch") and x.get(_k(d)) != y.get(_k(d)):
            return "categorical"
    dist = max((abs(L.unit(d, x) - L.unit(d, y)) for d in dims if d.kind in ("cont", "log")), default=0.0)
    return "coarse" if dist >= 0.25 - 1e-9 else "fine" if dist < 0.125 - 1e-9 else "mid"


def concordance_by_class(dims, xs, obj, true):
    """Same-half pairwise concordance (ties half) per pair class, mean over halves; true ties and
    refusals skipped. -> {class: (concordance or None, pairs)}."""
    cls = {(i, j): pair_class(dims, xs[i], xs[j]) for i, j in itertools.combinations(range(len(xs)), 2)}
    out = {}
    for c in ("coarse", "mid", "fine", "categorical"):
        accs, n = [], 0
        for h in HALVES:
            m = t = 0.0
            for (i, j), k in cls.items():
                if k != c or not (_pos(true[h][i]) and _pos(true[h][j]) and _finite(obj[h][i]) and _finite(obj[h][j])):
                    continue
                s = _sign(true[h][i] - true[h][j])
                if s == 0:
                    continue
                m += 1
                t += 1.0 if _sign(obj[h][i] - obj[h][j]) == s else 0.5 if obj[h][i] == obj[h][j] else 0.0
            accs.append(t / m if m else None)
            n = max(n, int(m))
        out[c] = (_mean(accs), n)
    return out


def cell_measures(points, dims, obj, true):
    """One configuration on one cell: the measures the plan declares."""
    ig = [L.unit(next(d for d in dims if _k(d) == INPUT_GAIN), p["x"]) for p in points]
    s_ig = ig[next(i for i, p in enumerate(points) if p["source"] == "S")]
    dg = [u - s_ig for u in ig]
    return {"same_half": same_half(obj, true), "cross_half": cross_half(obj, true),
            "same_half_worst": same_half(obj, true, rho_worst), "reliable_accuracy": reliable_accuracy(obj, true),
            "partial_vs_input_gain": _mean(partial_rho(obj[h], true[h], dg) for h in HALVES),
            "neighbourhood_regret": neighbourhood_regret(points, obj, true),
            "three_way": {d: tuple(statistics.fmean(t[j] for t in v) for j in range(3))
                          for d, v in three_way(points, obj, true).items()},
            "by_class": concordance_by_class(dims, [p["x"] for p in points], obj, true)}


# --- aggregation ---------------------------------------------------------------------------------------

def agg(rows):
    """rows: {(slug, amp, ...): (slug, band, cls, value)} (None values skipped) -> part means (over amps),
    band-weighted mean with the 90% band-clustered t interval (`song_readout.bw_stats`), the
    part-weighted interval, per amp and per class, the cell count, and the realised σ_d (the SD
    of the band means; for paired rows, the noise scale of that contrast)."""
    r3 = [(s, b, v) for (s, b, _, v) in rows.values() if v is not None]
    if not r3:
        return {"band_weighted_mean": None, "cells": 0}
    pm = L.part_means(r3)
    out = R.bw_stats([(b, v) for _, b, v in pm])
    m, lo, hi = L.part_interval(r3)
    bands = {}
    for _, b, v in pm:
        bands.setdefault(b, []).append(v)
    bm = [statistics.fmean(v) for v in bands.values()]
    out.update(part_weighted={"mean": m, "lo90": lo, "hi90": hi}, cells=len(r3),
               sigma_d=statistics.stdev(bm) if len(bm) > 1 else None)
    out["per_amp"] = {a: R.bw_stats([(b, v) for _, b, v in L.part_means(
        [(s, b, v) for k, (s, b, _, v) in rows.items() if k[1] == a and v is not None])])["band_weighted_mean"]
                      for a in sorted({k[1] for k in rows})}
    out["per_class"] = {c: R.bw_stats([(b, v) for _, b, v in L.part_means(
        [(s, b, v) for (s, b, cc, v) in rows.values() if cc == c and v is not None])])["band_weighted_mean"]
                        for c in ("clean", "crunch")}
    return out


def agg2(rows, large=()):
    """`agg` on all cells and without the large-offset parts (amendment 1)."""
    return {"all": agg(rows), "without_large_offset": agg({k: v for k, v in rows.items() if v[0] not in large})}


def large_offset_parts(parts, obj_lag=L.OBJ_LAG, limit=LARGE_OFFSET):
    """Parts whose judge_lag sits more than `limit` samples from the rebuilt objective's −52."""
    return sorted(s for s, p in parts.items() if p.get("judge_lag") is not None and abs(p["judge_lag"] - obj_lag) > limit)


def paired(rows_a, rows_b):
    """Cell-paired difference a − b, where both exist."""
    return {k: (*rows_a[k][:3], rows_a[k][3] - rows_b[k][3]) for k in rows_a
            if k in rows_b and rows_a[k][3] is not None and rows_b[k][3] is not None}


def main_effects(per_cell, measure="cross_half"):
    """per_cell: {cell: {config tuple: measures}} -> {effect: {cell: value}}. The DI, reference and
    mask effects and DI × reference are taken at each DI's native lag only (amendment 1: the
    "other" and 0 lags are diagnostic, since the measure DI keeps the raw DI's timing while C′'s
    rebuild sits on the recording's); each is the mean over the remaining factor's levels of
    (level − base level). Lag effects are within each DI, over references and masks."""
    contrasts = {"DI measure-cprime": (0, "measure", "cprime", None), "DI dac9-cprime": (0, "dac9", "cprime", None),
                 "reference reference-stem": (1, "reference", "stem", None),
                 "mask record-own": (3, "record", "own", None)}
    for d in ("cprime", "measure", "dac9"):                             # lag effects within each DI
        contrasts[f"lag other-native [{d}]"] = (2, "other", "native", d)
        contrasts[f"lag zero-native [{d}]"] = (2, "zero", "native", d)
    contrasts["lag gcc-native [cprime]"] = (2, "gcc", "native", "cprime")
    out = {}
    for name, (pos, hi, lo, only) in contrasts.items():
        vals = {}
        for cell, cfg in per_cell.items():
            ds = []
            for c, m in cfg.items():
                if c[pos] != hi or (only is not None and c[0] != only) or (pos != 2 and c[2] != "native"):
                    continue
                b = tuple(lo if i == pos else v for i, v in enumerate(c))
                if b in cfg and m.get(measure) is not None and cfg[b].get(measure) is not None:
                    ds.append(m[measure] - cfg[b][measure])
            if ds:
                vals[cell] = statistics.fmean(ds)
        if vals:
            out[name] = vals
    vals = {}
    for cell, cfg in per_cell.items():                                    # DI × reference
        ds = []
        for g, m in itertools.product(("native",), MASKS):
            q = [cfg.get((d, r, g, m), {}).get(measure) for d, r in
                 (("measure", "reference"), ("measure", "stem"), ("cprime", "reference"), ("cprime", "stem"))]
            if all(v is not None for v in q):
                ds.append((q[0] - q[1]) - (q[2] - q[3]))
        if ds:
            vals[cell] = statistics.fmean(ds)
    if vals:
        out["DI x reference"] = vals
    return out


# --- experiment 1b (amendment 2): the matched cell ----------------------------------------------------

def subset_measures(points, obj, true, sources):
    """Cross-half and same-half Spearman, reliable-pair accuracy and the ceiling on the points whose
    source is in `sources` (amendment 2's subsets: S's neighbourhood, K_S, arm A)."""
    idx = [i for i, p in enumerate(points) if p["source"] in sources]
    o = {h: [obj[h][i] for i in idx] for h in HALVES}
    t = {h: [true[h][i] for i in idx] for h in HALVES}
    return {"cross_half": cross_half(o, t), "same_half": same_half(o, t),
            "reliable_accuracy": reliable_accuracy(o, t), "ceiling": ceiling(t), "n": len(idx)}


def reading_1b(diff, current, ceiling_, share=NEAR_GAP_SHARE):
    """Amendment 2's reading of matched − current (cross-half, band-weighted; estimates only):
    'above' if the 90% interval is above 0 (next: a better real separator feeding both the rebuild
    and the reference); 'below' if under 0; 'near' if it contains 0 and its top closes less than
    `share` of the gap from today's objective to the ceiling (the rebuild limits even with a
    perfect stem); otherwise 'undecided'. Also the share of the gap the estimate closes."""
    lo, hi, m = diff.get("lo90"), diff.get("hi90"), diff.get("band_weighted_mean")
    gap = None if current is None or ceiling_ is None else ceiling_ - current
    closed = m / gap if m is not None and gap else None
    if lo is None or hi is None:
        r = "undecided"
    elif lo > 0:
        r = "above"
    elif hi < 0:
        r = "below"
    elif gap and hi < share * gap:
        r = "near"
    else:
        r = "undecided"
    return {"reading": r, "gap": gap, "gap_closed": closed}


def lufs(x):
    import numpy as np
    import pyloudnorm

    return float(pyloudnorm.Meter(K.P.SR).integrated_loudness(np.asarray(x, np.float64)))


def rebuild_ref_problems(gcc_vs_stem_rebuild, loudness, lag_tol=REBUILD_LAG_TOL, target=REBUILD_LUFS,
                         tol=REBUILD_LUFS_TOL):
    """Amendment 2a: a matched rebuild is used only if it sits within `lag_tol` samples of C′'s stem
    rebuild (GCC) and at −22.9 LUFS within `tol`. -> the problems (empty: usable)."""
    out = []
    if gcc_vs_stem_rebuild is None or abs(gcc_vs_stem_rebuild) > lag_tol:
        out.append(f"GCC against C′'s stem rebuild is {gcc_vs_stem_rebuild} samples (limit ±{lag_tol})")
    if loudness is None or not math.isfinite(loudness) or abs(loudness - target) > tol:
        out.append(f"loudness {loudness} LUFS (target {target} ± {tol})")
    return out


def cmd_rebuild_ref():
    """Amendment 2 (the torch interpreter, CPU): each part's fold C′ rebuilds reference.wav as
    `song_settings.rebuild_all` rebuilds the stem (re-EQ'd by fold 2's average − fold f's, at −22.9
    LUFS), with experiment 4's leak assertion per part; logs the network, and GCC against
    reference.wav and against C′'s stem rebuild. Before any render (amendment 2a), every part's
    matched rebuild must sit within 3 samples of C′'s stem rebuild (GCC) and at −22.9 LUFS within
    0.05; otherwise the command stops, and `render --di cprime_ref` refuses to start."""
    from learn import confirm_run as CR

    rebuild_from(MATCHED_DI, lambda slug, part: CR.mono(part["crop"] / "reference.wav"))


def rebuild_from(di, source, net=None, extra_leak=None, out_dir=None, gate=True, level_ref=None):
    """C′'s rebuild of `source(slug, part)` (a 10-s crop on the recording's timeline) for every
    part, into `REBUILD_DIR[di]`, exactly as `cmd_rebuild_ref` (amendment 2) rebuilt reference.wav:
    the fold's final C′ (DONE marker), experiment 4's leak assertion, re-EQ'd by fold 2's average −
    fold f's, −22.9 LUFS. Logs GCC against the source, reference.wav and C′'s stem rebuild; the
    amendment 2a checks (3 samples, 0.05 LU) gate `render --di <di>` through `check.json`.
    Amendment 4: `net(fold)` swaps the network (default C′); `extra_leak(band, path, fold)` adds a
    leak assertion per part (the separator-robust networks' pools and residual library); `out_dir`
    writes elsewhere (4a's identity check); `gate=False` returns the problems instead of exiting.
    Amendment 4b: `level_ref(slug)` replaces the −22.9 LUFS target of 2a's level check with the
    loudness of the paired comparator's stored rebuild (the recipe itself is unchanged)."""
    import numpy as np
    import torch

    from learn import confirm_run as CR
    from learn import di_fine_structure as DF
    from learn import direc as D
    from learn import rank_margin as RM
    from learn import song_settings as SS
    from learn.direc_check import eq_to, to_lufs

    ps, fo = K.parts(), SS.folds()
    avg = {f: np.load(SS.MODELS / "cache" / f"average-fold{f}.npy") for f in range(4)}
    d = pathlib.Path(out_dir) if out_dir else OUT / REBUILD_DIR[di]
    d.mkdir(parents=True, exist_ok=True)
    log_path = d / "rebuild-log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    nets = {}
    for slug in sorted(s for s in ps if s not in EXCLUDED):
        f = fo[ps[slug]["band"]]
        path = pathlib.Path(net(f)) if net else SS.cprime(f)
        if not SS.net_ready(path):
            raise SystemExit(f"{path} is not final (no DONE marker)")
        cfg = json.loads((path.parent / "config.json").read_text()) if (path.parent / "config.json").exists() else {}
        caches = [pathlib.Path(c) for c in cfg.get("caches", [DF.MODELS / c for c in DF.CACHES])]
        DF.assert_no_leak(ps[slug]["band"], cfg.get("fold", f), f, DF.train_pool_bands(f, caches))
        if extra_leak:
            extra_leak(ps[slug]["band"], path, f)
        out = d / f"{slug}.npy"
        if out.exists() and slug in log:
            continue
        if f not in nets:
            nets[f] = D.load_model(path).eval()
        src = np.asarray(source(slug, ps[slug]))
        x = D.rebuild(nets[f], src.astype(np.float32), device=torch.device("cpu")).astype(np.float64)
        y = to_lufs(eq_to(x, avg[2] - avg[f]))
        np.save(out, y)
        stem_rb = np.load(SS.OUT / "rebuilt" / f"{slug}.npy")
        n = min(len(y), len(stem_rb))
        g = int(RM.gcc_lag(y[:n], stem_rb[:n]))
        ref = CR.mono(ps[slug]["crop"] / "reference.wav")
        target = level_ref(slug) if level_ref else REBUILD_LUFS
        log[slug] = {"fold": f, "network": str(path), "source": REBUILD_SOURCE[di], "gcc_vs_source": gcc_level(y, src),
                     "gcc_vs_reference": gcc_level(y, ref), "gcc_vs_stem_rebuild": g, "lufs": lufs(y),
                     "problems": rebuild_ref_problems(g, lufs(y), target=target)}
        if level_ref:
            log[slug]["level_target"] = target
        if net:
            log[slug]["network_sha256"] = file_sha256(path)
        K._atomic(log_path, log)
        print(slug, "fold", f, log[slug], flush=True)
    bad = {s_: v["problems"] for s_, v in log.items() if v.get("problems")}
    missing = [s_ for s_ in ps if s_ not in EXCLUDED and s_ not in log]
    K._atomic(d / "check.json", {"ok": not bad and not missing, "problems": bad, "missing": missing})
    if not gate:
        return bad, missing
    if bad or missing:
        raise SystemExit(f"{di} rebuilds fail the pre-render checks: {bad or missing}")
    print(f"{di} rebuilds: all 24 within 3 samples of C′'s stem rebuild and at -22.9 ± 0.05 LUFS")


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rebuilds_ok(di):
    """A rebuilt DI's pre-render checks passed on all 24 parts (amendments 2a and 3)."""
    p = OUT / REBUILD_DIR[di] / "check.json"
    return p.exists() and json.loads(p.read_text()).get("ok") is True


def matched_rebuilds_ok():
    return rebuilds_ok(MATCHED_DI)


def complete_1b(cells, renders, expected=EXPECTED_1B):
    """Amendment 2a: a 1b reading only on the complete set (72 cells, 3,528 renders). -> None, or why not."""
    if cells != expected["cells"] or renders != expected["renders"]:
        return f"{cells} cells and {renders} renders, not {expected['cells']} and {expected['renders']}"
    return None


def cmd_report_1b():
    """Amendment 2, zero renders: the matched cell against the truth (experiment 1's measure-DI
    scores), paired with today's objective, on all of Σ and its subsets, per band, with the reading."""
    meta, sig = load_sigma()
    ps = K.parts()
    cfgs = {"matched": MATCHED, "matched_gcc": MATCHED_GCC, "current": CURRENT,
            "cprime_reference": ("cprime", "reference", "native", "own")}
    per = {}
    for c, pts in sorted(sig.items()):
        files = {d: OUT / "scores" / d / c[0] / f"{c[1]}.json" for d in ("measure", "cprime", MATCHED_DI)}
        if not all(f.exists() for f in files.values()):
            continue
        sc = {d: json.loads(f.read_text())["scores"] for d, f in files.items()}
        true = _vals(sc["measure"], TRUE)
        per[c] = {name: {sub: subset_measures(pts, _vals(sc[cfg[0]], cfg), true, srcs) for sub, srcs in SUBSETS.items()}
                  for name, cfg in cfgs.items()}

    def rows(name, sub, key):
        return {c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], v[name][sub][key]) for c, v in per.items()}

    rep = {"sigma": meta["hash"], "cells": len(per), "subsets": {}}
    for sub in SUBSETS:
        r = {"ceiling": agg(rows("current", sub, "ceiling"))}
        for name in cfgs:
            r[name] = {k: agg(rows(name, sub, k)) for k in ("cross_half", "reliable_accuracy", "same_half")}
        r["matched_minus_current"] = {k: agg(paired(rows("matched", sub, k), rows("current", sub, k)))
                                      for k in ("cross_half", "reliable_accuracy")}
        r["matched_minus_cprime_reference"] = {k: agg(paired(rows("matched", sub, k), rows("cprime_reference", sub, k)))
                                               for k in ("cross_half", "reliable_accuracy")}
        r["reading_figures"] = reading_1b(r["matched_minus_current"]["cross_half"],
                                          r["current"]["cross_half"]["band_weighted_mean"], r["ceiling"]["band_weighted_mean"])
        rep["subsets"][sub] = r
    bands = {}
    for c, v in per.items():
        b = ps[c[0]]["band"]
        bands.setdefault(b, {}).setdefault(c[0], []).append(
            (v["matched"]["all"]["cross_half"], v["current"]["all"]["cross_half"], v["current"]["all"]["ceiling"]))
    rep["per_band_cross_half"] = {
        b: {k: _mean(_mean(t[j] for t in vals) for vals in parts.values())
            for j, k in enumerate(("matched", "current", "ceiling"))} for b, parts in sorted(bands.items())}
    for b, v in rep["per_band_cross_half"].items():
        v["matched_minus_current"] = None if v["matched"] is None or v["current"] is None else v["matched"] - v["current"]
    renders = 0
    for p in (OUT / "renders" / MATCHED_DI).glob("*/*.json"):
        renders += json.loads(p.read_text())["renders"]
    rep["renders_used"] = renders
    rep["renders_expected"] = expected_renders(meta["cells"], dis=(MATCHED_DI,))
    devs = []
    for c in per:
        f = OUT / "scores" / MATCHED_DI / c[0] / f"{c[1]}.json"
        fv = json.loads(f.read_text()).get("flac_vs_float_S") or {}
        devs += [v for hv in fv.values() for v in hv.values()]
    rep["flac_vs_float_S"] = {"n": len(devs), "max": max(devs, default=None),
                              "over_tol": sum(v > CHECK_TOL for v in devs)}
    why = complete_1b(len(per), renders)
    for sub, r in rep["subsets"].items():
        r["reading"] = r["reading_figures"]["reading"] if why is None else f"refused: {why}"
    K._atomic(OUT / "report-1b.json", rep)
    a = rep["subsets"]["all"]
    f = lambda s: f"{s['band_weighted_mean']:+.3f} [{s['lo90']:+.3f}, {s['hi90']:+.3f}]" if s.get("lo90") is not None else str(s.get("band_weighted_mean"))  # noqa: E731
    print("matched cross-half:", f(a["matched"]["cross_half"]), "current:", f(a["current"]["cross_half"]),
          "ceiling:", f(a["ceiling"]))
    print("matched - current:", f(a["matched_minus_current"]["cross_half"]), "reading:", a["reading"],
          a["reading_figures"])
    print("renders used:", renders, "expected:", rep["renders_expected"])


# --- step 0: input gain as a pre-gain -----------------------------------------------------------------

def pregain_plan(S, eps=PREGAIN_DB, dims=None):
    """The warm-up and the 4 renders: for ε = +6 and −6 dB, (DI × 10^(ε/20), input gain g) and
    (DI, input gain g + ε); the warm-up is (DI, g + 6), so the later render of that setting repeats
    it. -> [(name, DI scale, settings)]; refuses a g ± ε outside the knob's range."""
    d = next(x for x in (dims or K.space("pr12")) if _k(x) == INPUT_GAIN)
    g = float(S.get(INPUT_GAIN, d.lo))
    out = [("warm-up", 1.0, {**S, INPUT_GAIN: K.fmt(g + eps)})]
    for e in (eps, -eps):
        if not d.lo <= g + e <= d.hi:
            raise ValueError(f"input gain {g} {e:+} dB leaves [{d.lo}, {d.hi}]")
        out.append((f"di{e:+g}dB", 10 ** (e / 20), dict(S)))
        out.append((f"knob{e:+g}dB", 1.0, {**S, INPUT_GAIN: K.fmt(g + e)}))
    return out


def residual_db(y1, y2, skip=0):
    """10 log10 of the residual's energy over y2's, after `skip` samples; -inf if identical."""
    import numpy as np

    a, b = np.asarray(y1, np.float64)[skip:], np.asarray(y2, np.float64)[skip:]
    n = min(len(a), len(b))
    e, s = float(np.sum((a[:n] - b[:n]) ** 2)), float(np.sum(b[:n] ** 2))
    return -math.inf if e == 0 else 10 * math.log10(e / max(s, 1e-30))


# --- step 0: zero-render diagnostics -------------------------------------------------------------------

def _lstsq(X, y):
    """OLS with an intercept: (coefficients without it, standard errors) — nan SEs when undefined."""
    import numpy as np

    X = np.column_stack([np.ones(len(y)), np.asarray(X, float)])
    y = np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    dof = len(y) - X.shape[1]
    if dof <= 0:
        return beta[1:], np.full(X.shape[1] - 1, np.nan)
    s2 = float(np.sum((y - X @ beta) ** 2)) / dof
    cov = s2 * np.linalg.pinv(X.T @ X)
    return beta[1:], np.sqrt(np.clip(np.diag(cov), 0, None))[1:]


def sign3(coef, se):
    """'+' or '-' when the coefficient is beyond one standard error, else '0'."""
    if not (_finite(coef) and _finite(se)):
        return "0"
    return "+" if coef > se else "-" if coef < -se else "0"


def knob_regression(dims, S, xs, obj, true, min_levels=4):
    """Per half: OLS of log obj, log true and their difference on each continuous dim's unit move
    from S (dims with ≥ `min_levels` distinct values; input gain signed like the others). ->
    {half: {dim: {"bias": coef, "true": sign3, "obj": sign3}}}."""
    cont = [d for d in dims if d.kind in ("cont", "log")]
    out = {}
    for h in HALVES:
        keep = [i for i in range(len(xs)) if _pos(true[h][i]) and _pos(obj[h][i])]
        use = [d for d in cont if len({L.unit(d, xs[i]) for i in keep}) >= min_levels]
        if not use or len(keep) < len(use) + 3:
            continue
        X = [[L.unit(d, xs[i]) - L.unit(d, S) for d in use] for i in keep]
        lt = [math.log(true[h][i]) for i in keep]
        lo = [math.log(obj[h][i]) for i in keep]
        bt, st = _lstsq(X, lt)
        bo, so = _lstsq(X, lo)
        bb, _ = _lstsq(X, [a - b for a, b in zip(lo, lt)])
        out[h] = {d.name: {"bias": float(bb[j]), "true": sign3(bt[j], st[j]), "obj": sign3(bo[j], so[j])}
                  for j, d in enumerate(use)}
    return out


def first_divergence(path_a, path_b):
    """Two searches from the same start and seed evaluate the same settings until a decision differs.
    -> (common prefix length, dims decided alike before it, dims that differ at the divergence)."""
    n = 0
    for (xa, _), (xb, _) in zip(path_a, path_b):
        if K.key(xa) != K.key(xb):
            break
        n += 1
    x0 = path_a[0][0] if path_a else {}
    probed = {k for x, _ in path_a[:n] for k in x if x.get(k) != x0.get(k)}
    if n < min(len(path_a), len(path_b)):
        xa, xb = path_a[n][0], path_b[n][0]
        diff = sorted(k for k in set(xa) | set(xb) if xa.get(k) != xb.get(k))
    else:
        diff = []
    return n, sorted(probed - set(diff)), diff


def knob_order(name):
    """The report's knob order: input gain, the amp's knobs, the cab, then switches."""
    sw = any(w in name for w in ("Bright", "Boost", "InputMode", "BassTreble", "Active"))
    return (sw, name != "parameters/inputGain", name.startswith("cabParameters"), name)


def alignment_row(judge_lag, reb_meas, reb_stem, stem_ref, ref_meas, latency=52):
    """Step 0's alignment table (amendment 1), one part. Inputs are GCC lags, `gcc_lag(x, y)` = the
    samples x lags y. -> the lags the plan uses and how they agree:
    - judge_offset: judge_lag + 52, how far the recording lags the DI by the stored judge lag;
    - judge_vs_gcc: that minus GCC(reference, measure DI);
    - gcc_lag_cprime: −52 − GCC(rebuild, stem), the rebuild's measured lag against the stem;
    - closure: GCC(reference, measure DI) minus the path reference→stem→rebuild→measure DI (0
      when the four GCC lags agree)."""
    path = -stem_ref - reb_stem + reb_meas
    return {"judge_lag": judge_lag, "judge_offset": judge_lag + latency,
            "judge_vs_gcc": judge_lag + latency - ref_meas, "gcc_lag_cprime": -latency - reb_stem,
            "gcc_rebuild_measure": reb_meas, "gcc_rebuild_stem": reb_stem, "gcc_stem_reference": stem_ref,
            "gcc_reference_measure": ref_meas, "closure": ref_meas - path,
            "large_offset": abs(judge_lag + latency) > LARGE_OFFSET}


def limit_side(d, x, tol=1e-6):
    u = L.unit(d, x)
    return "lo" if u <= tol else "hi" if u >= 1 - tol else "interior"


# --- guards ------------------------------------------------------------------------------------------

def disk_free_gb():
    return shutil.disk_usage(pathlib.Path.home()).free / 1e9


def disk_ok(free_gb, renders, guard=DISK_GUARD_GB, mb=MB_PER_RENDER):
    """Room for `renders` more FLACs (at the measured maximum size) above the guard."""
    return free_gb - renders * mb / 1000 >= guard


def is_render_process(cmd):
    from learn import ks_extend as X

    return X._is_python(cmd) and any(re.search(p, cmd) for p in RENDERS)


def others_rendering(ps, own=()):
    return [p for p, c in ps if p not in own and is_render_process(c)]


def is_separation(cmd):
    from learn import ks_extend as X

    return X._is_python(cmd) and any(re.search(p, cmd) for p in SEPARATIONS)


def separating(ps, own=()):
    """Separations running (amendment 3: a render waits while one runs)."""
    return [p for p, c in ps if p not in own and is_separation(c)]


def _wait_cap(cap=CAP):
    from learn import ks_extend as X

    own = {os.getpid(), os.getppid()}
    while True:
        ps = X._ps()
        if len(others_rendering(ps, own)) < cap and not separating(ps, own):
            return
        time.sleep(60)


def _wait_after(pids):
    from learn import ks_extend as X

    while any(p in dict(X._ps()) for p in pids):
        time.sleep(60)


# --- audio -------------------------------------------------------------------------------------------

def save_flac(path, y):
    """16-bit FLAC, peak-normalised to 0.99; -> the factor that restores the level."""
    import numpy as np
    import soundfile as sf

    peak = float(np.abs(y).max())
    scale = peak / PEAK_TO if peak > 0 else 1.0
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.flac")
    sf.write(str(tmp), np.asarray(y, np.float64) / scale, K.P.SR, subtype="PCM_16")
    tmp.replace(path)
    return scale


def load_flac(path, scale):
    import soundfile as sf

    y, _ = sf.read(str(path), dtype="float64")
    return (y.mean(1) if y.ndim == 2 else y) * scale


# --- data access (no renders) ----------------------------------------------------------------------

def cells():
    return [(s, a) for s in sorted(K.parts()) if s not in EXCLUDED for a in K.AMPS]


def _kc(slug, amp):
    return json.loads((K.OUT / "cells" / slug / amp / "result.json").read_text())


def build_sigma():
    """Σ for every cell from the stored K_S and arm A searches (zero renders). Stops on any replay
    mismatch. -> ({(slug, amp): [point]}, mismatches)."""
    from learn import song_settings as SS

    ms, ps = L.menu_S(), K.parts()
    folds = SS.folds()
    draws2b = draws_2b()
    sigma, bad = {}, []
    for slug, amp in cells():
        S = ms[amp][ps[slug]["gain_class"]][1]
        dims = K.space(amp, S)
        c = _kc(slug, amp)
        ks_paths, a_paths = [], []
        for search, _ in K.DIRECTIONS:
            run = c["runs"][search]
            if "K_S" in run:
                t, x = L.replay_ks(amp, S, run["K_S"]["evals"], search)
                if x != L._settings(K.OUT / "cells" / slug / amp / f"K_S-{search}.json"):
                    bad.append((slug, amp, f"K_S-{search}"))
                ks_paths.append(t)
            stored, xa = L.stored_a(slug, amp, search)
            path, x = arm_a_path(amp, S, stored["objective_curve"])
            if x != xa:
                bad.append((slug, amp, f"armA-{search}"))
            a_paths.append([(xx, {search: v}) for xx, v in path])
        pts = cell_sigma(slug, amp, dims, S, ks_paths, a_paths)
        if folds[ps[slug]["band"]] == 3:
            for p in pts:
                if p["key"] in draws2b.get((slug, amp), {}):
                    p["obj_2b"] = draws2b[(slug, amp)][p["key"]]
        sigma[(slug, amp)] = pts
    return sigma, bad


def draws_2b():
    """2b's 40 drawn settings per fold-3 cell, as 2b drew them, with C′'s stored objective on both
    halves: {(slug, amp): {key: {"A", "B"}}} (empty without 2b's files)."""
    lv = L.OUT
    files = sorted((lv / "replay" / "ks").glob("*/*.json"))
    if not files:
        return {}
    traj = {(p.parent.name, p.stem): [(L._settings_dict(x), d) for x, d in json.loads(p.read_text())["trajectory"]]
            for p in files}
    out = {}
    for (slug, amp), dr in L.local_draw(traj).items():
        f = lv / "local" / "C'" / f"{slug}-{amp}.json"
        if not f.exists():
            continue
        pts = json.loads(f.read_text())["points"]
        assert [p["true"] for p in pts] == [d for _, d in dr], (slug, amp)
        out[(slug, amp)] = {K.key(x): p["obj"] for (x, _), p in zip(dr, pts)}
    return out


def load_sigma():
    p = OUT / "sigma.json"
    if not p.exists():
        raise SystemExit("run `sigma` first")
    d = json.loads(p.read_text())
    if sigma_hash(d["cells"]) != d["hash"] or d["hash"] != SIGMA_HASH:
        raise SystemExit(f"sigma.json hashes to {sigma_hash(d['cells'])}, not {SIGMA_HASH}")
    sig = {}
    for c, pts in d["cells"].items():
        slug, amp = c.split("|")
        sig[(slug, amp)] = [{**q, "x": tdict(q["x"])} for q in pts]
    return d, sig


def sep_crop_path(sep, slug):
    """A separator's 10-s stem crop (amendment 3; `local_objective_1c separate` / `blend`)."""
    return OUT / "sep" / sep / "crop" / f"{slug}.npy"


def part_signals(slug, di_name):
    """The render input and the scoring signals for a part (a score view's: its render DI's, plus
    the separated references its configurations use)."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import song_settings as SS
    from learn.direc_check import to_lufs

    part = K.parts()[slug]
    base = render_di(di_name)
    if base == "measure":
        di = K.measure_di(part)
    elif base == "cprime":
        di = np.load(SS.OUT / "rebuilt" / f"{slug}.npy")
    elif base == "dac9":
        di = to_lufs(np.load(OUT / "dac" / "out" / f"{slug}-q9.npy"))
    elif base in REBUILD_DIR:
        di = np.load(OUT / REBUILD_DIR[base] / f"{slug}.npy")
    else:
        raise ValueError(di_name)
    sig = {"di": di, "stem": SS.stem(slug), "reference": CR.mono(part["crop"] / "reference.wav")}
    for s in sorted({c[1] for c in configs(di_name)} & set(SEPARATORS)):
        sig[s] = np.load(sep_crop_path(s, slug)).astype(np.float64)
    return sig, part


def _render_paths(di, slug, amp):
    d = OUT / "renders" / di / slug / amp
    return d, OUT / "renders" / di / slug / f"{amp}.json"


def _done(di, slug, amp):
    p = _render_paths(di, slug, amp)[1]
    return p.exists() and json.loads(p.read_text()).get("status") == "done"


# --- commands -------------------------------------------------------------------------------------------

def cmd_sigma(out=None):
    """Zero renders: build Σ, refuse on a replay mismatch, write it once (never overwritten)."""
    path = pathlib.Path(out) if out else OUT / "sigma.json"
    if path.exists():
        d = json.loads(path.read_text())
        print("Σ already frozen:", d["hash"], d["settings"], "settings,", d["expected_renders"], "renders")
        return
    sig, bad = build_sigma()
    if bad:
        raise SystemExit(f"{len(bad)} replay mismatch(es), e.g. {bad[:3]}: Σ is not frozen")
    sj = sigma_json(sig)
    if sigma_hash(sj) != SIGMA_HASH:
        raise SystemExit(f"Σ hashes to {sigma_hash(sj)}, not the plan's {SIGMA_HASH}: the stored searches or the code changed")
    from collections import Counter

    src = Counter(p["source"] for pts in sig.values() for p in pts)
    rec = {"hash": sigma_hash(sj), "seeds": {"ks": SEED_KS, "armA": SEED_A}, "step": STEP, "n_fill": N_FILL,
           "n_arm_a": N_ARM_A, "cells_n": len(sj), "settings": sum(len(v) for v in sj.values()),
           "by_source": dict(src), "per_cell": {"min": min(map(len, sj.values())), "max": max(map(len, sj.values()))},
           "expected_renders": expected_renders(sj),
           "checks_available": {"true_vs_KS": sum(bool(p["true_stored"]) for v in sig.values() for p in v),
                                "current_vs_armA": sum(bool(p["obj_stored"]) for v in sig.values() for p in v),
                                "current_vs_2b": sum("obj_2b" in p for v in sig.values() for p in v)},
           "cells": sj}
    path.parent.mkdir(parents=True, exist_ok=True)
    K._atomic(path, rec)
    print(json.dumps({k: v for k, v in rec.items() if k != "cells"}, indent=1))


def stop_path():
    return OUT / "STOP.json"


def check_stop():
    """A breakage in any shard stops every shard before its next cell (amendment 1)."""
    if stop_path().exists():
        raise SystemExit(f"stopped: {stop_path().read_text()}")


def breakage(rec_path, rec, why):
    """Record the cell as check_failed (never done), write the shared stop file, and exit."""
    K._atomic(rec_path, {**rec, "status": "check_failed", "why": why})
    stop_path().parent.mkdir(parents=True, exist_ok=True)
    K._atomic(stop_path(), {"why": why, "slug": rec["slug"], "amp": rec["amp"], "di": rec["di"],
                            "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    raise SystemExit(f"{why}: every shard stops; investigate, then delete {stop_path()}")


def native_config(di):
    """The DI's own objective: its source reference (the stem for C′, reference.wav otherwise) at
    its native lag with its own mask."""
    return (di, REBUILD_SOURCE.get(di, "reference"), "native", "own")


def render_checks(p, di, y, sig_s, judge_lag, aligned, warm=None):
    """The corner checks on one float render, as it lands (amendment 1): the true d (measure DI)
    against K_S's stored values; the current objective (C′) against arm A's stored search-half
    value and 2b's. A DI with no stored values (1b's matched rebuild, DAC-9: amendment 2; 1c's
    separator rebuilds: amendment 3) checks its S render against the cell's warm-up at S, a
    repeat, on its own objective. -> [(what, half, deviation)]."""
    out = []
    if di in NO_STORED and p.get("source") == "S" and warm is not None:
        c = native_config(di)
        a, _ = score_render(y, di, sig_s, judge_lag, aligned, only={c})
        b, _ = score_render(warm, di, sig_s, judge_lag, aligned, only={c})
        out += [("repeat_S", h, deviation(a[cname(c)][h], b[cname(c)][h])) for h in HALVES]
    if di == "measure" and p.get("true_stored"):
        s, _ = score_render(y, di, sig_s, judge_lag, aligned, only={TRUE})
        out += [("true_vs_KS", h, deviation(s[cname(TRUE)][h], v)) for h, v in p["true_stored"].items()]
    if di == "cprime" and (p.get("obj_stored") or p.get("obj_2b")):
        s, _ = score_render(y, di, sig_s, judge_lag, aligned, only={CURRENT})
        for what, src in (("current_vs_armA", p.get("obj_stored")), ("current_vs_2b", p.get("obj_2b"))):
            out += [(what, h, deviation(s[cname(CURRENT)][h], v)) for h, v in (src or {}).items()]
    return out


def _cells_for(sig, folds):
    from learn import song_settings as SS

    fo, ps = SS.folds(), K.parts()
    return [c for c in sorted(sig) if folds is None or fo[ps[c[0]]["band"]] in folds]


def cmd_render(shard, di_name="cprime,measure", after=(), folds=None, accept_guard_stop=False):
    """Experiment 1 (or the DAC add-on): each cell's Σ through each DI, 16-bit FLAC, one warm-up per
    (cell, DI). Guards: the shared stop file, the machine-wide cap, the swap guard, the disk guard
    (all shards' remaining renders at the start), and the corner checks on every render as it lands
    (the true d against K_S's stored values; C′'s objective against arm A's and 2b's): beyond 0.005
    the cell is recorded check_failed and every shard stops."""
    import numpy as np

    meta, sig = load_sigma()
    check_stop()
    dis = [d for d in di_name.split(",") if d]
    if MATCHED_DI in dis and not matched_rebuilds_ok():
        raise SystemExit("rebuild-ref's pre-render checks have not passed (amendment 2a)")
    for d in dis:
        if d in VIEWS:
            raise SystemExit(f"{d} is a score view of existing renders, not a DI to render")
        if d in SEP_DI.values() and not rebuilds_ok(d):
            raise SystemExit(f"{d}: local_objective_1c's pre-render checks have not passed (amendment 3)")
        if d in SEPNET_DI.values() and not rebuilds_ok(d):
            raise SystemExit(f"{d}: local_objective_1d's pre-render checks have not passed (amendment 4)")
    mine = _cells_for(sig, folds)
    left = sum(len(sig[c]) + 1 for c in mine for d in dis if not _done(d, *c))       # all shards
    if not accept_guard_stop and not disk_ok(disk_free_gb(), left):
        raise SystemExit(f"free disk {disk_free_gb():.1f} GB leaves under {DISK_GUARD_GB} GB after all "
                         f"shards' {left} renders: free space first, or accept a resumable guard stop "
                         f"(--accept-guard-stop)")
    todo = L._shard(mine, shard)
    if after:
        _wait_after(after)
    aligned = judge_fns()
    ms, rr, guard = L.menu_S(), None, L.SwapGuard()
    try:
        for slug, amp in todo:
            for d in dis:
                folder, rec_path = _render_paths(d, slug, amp)
                prev = json.loads(rec_path.read_text()) if rec_path.exists() else {}
                if prev.get("status") == "done":
                    continue
                if prev.get("status") == "check_failed":
                    raise SystemExit(f"{d} {slug} {amp} failed a check: investigate before rendering it again")
                check_stop()
                guard.check()
                _wait_cap()
                if not disk_ok(disk_free_gb(), len(sig[(slug, amp)]) + 1):
                    raise SystemExit("free disk below the 31 GB guard (resumable)")
                if rr is None:
                    rr = K.Renderer()
                    menu = rr.menu()
                sig_s, part = part_signals(slug, d)
                if d == "dac9":
                    from learn import rank_margin as RM
                    from learn.confirm_run import mono

                    lag = RM.gcc_lag(sig_s["di"], mono(part["crop"] / "di.wav"))
                    if abs(lag) > 3:
                        raise SystemExit(f"{slug}: the DAC round trip lags the DI by {lag}")
                sel, S = menu[amp][K.START[part["gain_class"]][amp]]
                if K.key(S) != K.key(ms[amp][part["gain_class"]][1]):
                    raise SystemExit(f"{amp} {part['gain_class']}: the live S differs from arm B's stored copy")
                comp = None
                if d in SEPNET_DI.values() and d == next(x for x in dis if x in SEPNET_DI.values()):
                    comp = prev.get("comparator") or comparator_check(rr, sel, slug, amp, sig[(slug, amp)], aligned)
                    if comp["max_dev"] > CHECK_TOL:
                        breakage(rec_path, {"slug": slug, "amp": amp, "di": d, "sigma": meta["hash"],
                                            "renders": prev.get("renders", 0), "comparator": comp},
                                 f"{slug} {amp}: C′ at S moved {comp['max_dev']:.4f} from experiment 1's stored score")
                di32 = sig_s["di"].astype(np.float32)
                n0 = rr.count
                rec = {"slug": slug, "amp": amp, "di": d, "sigma": meta["hash"], "status": "running",
                       "renders": prev.get("renders", 0), "warm_ups": prev.get("warm_ups", 0) + 1}
                if comp is not None:
                    rec["comparator"] = comp
                rec_path.parent.mkdir(parents=True, exist_ok=True)
                warm = rr.render(di32, sel, S)                                  # warm-up, counted
                scales, checks = [], []
                for i, p in enumerate(sig[(slug, amp)]):
                    y = rr.render(di32, sel, p["x"])
                    rec["renders"] = prev.get("renders", 0) + rr.count - n0
                    scales.append(save_flac(folder / f"{i:02d}.flac", y))
                    if p.get("source") == "S":                                 # amendment 2a: FLAC vs float
                        sf, _ = score_render(y, d, sig_s, part["judge_lag"], aligned, only={native_config(d)},
                                             gcc=None)
                        rec["S_float"] = {"index": i, "scores": sf}
                    for what, h, dev in render_checks(p, d, y, sig_s, part["judge_lag"], aligned, warm):
                        checks.append([i, what, h, dev])
                        if dev > CHECK_TOL:
                            breakage(rec_path, {**rec, "checks_float": checks},
                                     f"{d} {slug} {amp} setting {i}: {what} moved {dev:.4f} on half {h}")
                    if i % 12 == 0:                                             # a crash keeps its count
                        K._atomic(rec_path, rec)
                rec.update(scales=scales, renders=prev.get("renders", 0) + rr.count - n0,
                           checks_float=checks, status="done")
                K._atomic(rec_path, rec)
                print(d, slug, amp, len(scales), "renders", rec["renders"], "worst check",
                      round(max((c[3] for c in checks), default=0.0), 6), flush=True)
    finally:
        if rr is not None:
            rr.close()


def comparator_check(rr, sel, slug, amp, points, aligned):
    """Amendment 4a: one render of C′'s stem rebuild at S per cell, scored on today's objective
    and compared with experiment 1's stored score at S (|log| per half): the renderer still
    matches the stored comparators. Its two renders (a warm-up and S) are counted apart from the
    cell's 3,528."""
    import numpy as np

    i = next(j for j, q in enumerate(points) if q.get("source") == "S")
    sig_c, part = part_signals(slug, "cprime")
    x32 = sig_c["di"].astype(np.float32)
    rr.render(x32, sel, points[i]["x"])                                   # its own warm-up, as experiment 1
    y = rr.render(x32, sel, points[i]["x"])
    s, _ = score_render(y, "cprime", sig_c, part["judge_lag"], aligned, only={CURRENT})
    stored = json.loads((OUT / "scores" / "cprime" / slug / f"{amp}.json").read_text())["scores"][i][cname(CURRENT)]
    devs = {h: deviation(s[cname(CURRENT)][h], stored[h]) for h in HALVES}
    return {"index": i, "renders": 2, "devs": devs, "max_dev": max(devs.values())}


def _score_cell(args):
    """One (DI, cell) from its FLACs: every configuration (a worker; the output root travels with
    the task, since a spawned worker re-imports this module)."""
    d, slug, amp, root = args
    global OUT
    OUT = pathlib.Path(root)
    base = render_di(d)                                                 # a view reads its DI's renders
    sig_s, part = part_signals(slug, d)
    folder, rec_path = _render_paths(base, slug, amp)
    rec = json.loads(rec_path.read_text())
    aligned = judge_fns()
    gcc = gcc_level(sig_s["di"], sig_s[REBUILD_SOURCE[base]]) if base in REBUILT else None
    scores, fb = [], {}
    for i, sc in enumerate(rec["scales"]):
        s, f = score_render(load_flac(folder / f"{i:02d}.flac", sc), d, sig_s, part["judge_lag"], aligned, gcc)
        scores.append(s)
        for k, v in f.items():
            fb[k] = fb.get(k, 0) + v
    out = OUT / "scores" / d / slug / f"{amp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    K._atomic(out, {"scores": scores, "fallback": fb, "sigma": rec["sigma"], "gcc_rebuild_vs_stem": gcc,
                    "gcc_source": REBUILD_SOURCE.get(base), "render_di": base,
                    "flac_vs_float_S": None if d in VIEWS else flac_vs_float(rec, scores)})
    return d, slug, amp


def flac_vs_float(rec, scores):
    """Amendment 2a: S's score from its FLAC against the float score stored at render time, per
    configuration and half (|log|); None when the render record has no float score."""
    sf = rec.get("S_float")
    if not sf:
        return None
    flac = scores[sf["index"]]
    return {c: {h: deviation(flac[c][h], v) for h, v in hv.items()} for c, hv in sf["scores"].items()}


def cmd_score(di_name="cprime,measure", workers=3):
    from concurrent.futures import ProcessPoolExecutor

    meta, sig = load_sigma()
    todo = [(d, s, a, str(OUT)) for d in di_name.split(",") for (s, a) in sorted(sig)
            if _done(render_di(d), s, a) and not (OUT / "scores" / d / s / f"{a}.json").exists()]
    with ProcessPoolExecutor(workers) as ex:
        for d, s, a in ex.map(_score_cell, todo):
            print("scored", d, s, a, flush=True)


def _vals(scores, cfg):
    return {h: [s[cname(cfg)][h] for s in scores] for h in HALVES}


def wide(rows):
    """Fold-3-only figures: the band-weighted mean with the wider of the band and part intervals."""
    r3 = [(s, b, v) for (s, b, _, v) in rows.values() if v is not None]
    if not r3:
        return {"mean": None, "lo90": None, "hi90": None}
    m, lo, hi = L.interval(r3, wider=True)
    return {"mean": m, "lo90": lo, "hi90": hi, "bands": len({b for _, b, _ in r3}), "cells": len(r3)}


def undecided(s):
    """An interval that contains 0, or none at all."""
    return s.get("lo90") is None or s["lo90"] <= 0 <= s["hi90"]


def dac_extension_due(vs_cprime, vs_decisive):
    """Amendment 1's DAC extension rule: if the fold-3 interval of DAC-9 against C′, or against
    decisive (cross-half Spearman), is undecided, the add-on extends to the other 57 cells (2,793
    renders) on the user's yes."""
    return undecided(vs_cprime) or undecided(vs_decisive)


def cmd_report():
    """Zero renders: every measure the plan declares, from the scores; the corner checks; renders used."""
    from learn import song_settings as SS

    meta, sig = load_sigma()
    ps, folds = K.parts(), SS.folds()
    ms = L.menu_S()
    large = large_offset_parts({s: ps[s] for s in {c[0] for c in sig}})
    loaded = {}
    for d in (*DIS, "dac9"):
        for c in sorted(sig):
            p = OUT / "scores" / d / c[0] / f"{c[1]}.json"
            if p.exists():
                loaded[(d, c)] = json.loads(p.read_text())
    per_cell, ceil, rel_n, checks, fallback, gccs = {}, {}, {}, [], {}, {}
    for c, pts in sorted(sig.items()):
        if ("measure", c) not in loaded:
            continue
        slug, amp = c
        S = ms[amp][ps[slug]["gain_class"]][1]
        dims = K.space(amp, S)
        true = _vals(loaded[("measure", c)]["scores"], TRUE)
        ceil[c] = {"rho": ceiling(true), "rho_worst": ceiling(true, rho_worst)}
        rel_n[c] = len(reliable_pairs(true))
        per_cell[c] = {}
        for d in (*DIS, "dac9"):
            if (d, c) not in loaded:
                continue
            sc = loaded[(d, c)]["scores"]
            if loaded[(d, c)].get("gcc_rebuild_vs_stem") is not None and d == "cprime":
                gccs[slug] = loaded[(d, c)]["gcc_rebuild_vs_stem"]
            checks += [(c, d, *x) for x in corner_checks(pts, sc, d)]
            for cfg in configs(d):
                per_cell[c][cfg] = cell_measures(pts, dims, _vals(sc, cfg), true)
                fallback[cname(cfg)] = fallback.get(cname(cfg), 0) + loaded[(d, c)]["fallback"].get(cname(cfg), 0)

    def rows(f, cells=None):
        return {c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], f(c)) for c in per_cell if cells is None or c in cells}

    def m_of(cfg, key, cells=None):
        return rows(lambda c: per_cell[c].get(cfg, {}).get(key), cells)

    cfgs = sorted({cfg for v in per_cell.values() for cfg in v})
    table = {cname(cfg): {k: agg(m_of(cfg, k)) for k in ("same_half", "cross_half", "reliable_accuracy",
                                                          "same_half_worst", "partial_vs_input_gain",
                                                          "neighbourhood_regret")} for cfg in cfgs}
    ceiling_rows = rows(lambda c: ceil[c]["rho"])
    swaps_current = {"DI (= decisive)": DECISIVE, "reference": ("cprime", "reference", "native", "own"),
                     "lag other": ("cprime", "stem", "other", "own"), "lag zero": ("cprime", "stem", "zero", "own"),
                     "lag gcc": ("cprime", "stem", "gcc", "own"), "mask": ("cprime", "stem", "native", "record")}
    swaps_true = {"DI": ("cprime", "reference", "native", "own"), "reference (= decisive)": DECISIVE,
                  "lag other": ("measure", "reference", "other", "own"), "lag zero": ("measure", "reference", "zero", "own"),
                  "mask": ("measure", "reference", "native", "record")}
    lagged = lambda n: n.startswith(("DI", "lag"))  # noqa: E731
    contrasts = {"from_current": {n: {k: (agg2 if lagged(n) else lambda r, large=(): agg(r))(
                     paired(m_of(cfg, k), m_of(CURRENT, k)), large)
                     for k in ("same_half", "cross_half", "reliable_accuracy")} for n, cfg in swaps_current.items()},
                 "from_true_cross_half": {n: (agg2 if lagged(n) else lambda r, large=(): agg(r))(
                     paired(m_of(cfg, "cross_half"), ceiling_rows), large) for n, cfg in swaps_true.items()},
                 "current_minus_ceiling_cross_half": agg(paired(m_of(CURRENT, "cross_half"), ceiling_rows))}
    for cfg in (CURRENT, DECISIVE):
        a, b = agg(m_of(cfg, "cross_half"))["band_weighted_mean"], agg(ceiling_rows)["band_weighted_mean"]
        contrasts[f"{cname(cfg)} cross-half as a fraction of the ceiling (descriptive)"] = a / b if a is not None and b else None
    eff = {}
    for k in ("cross_half", "reliable_accuracy"):
        me = main_effects(per_cell, k)
        eff[k] = {n: (agg2 if n.startswith(("DI", "lag")) else lambda r, large=(): agg(r))(
            {c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], v) for c, v in vals.items()}, large)
            for n, vals in me.items() if "dac9" not in n}
    knobs = {}
    for cfg in (CURRENT, DECISIVE, ("measure", "stem", "other", "own"), ("cprime", "reference", "native", "own")):
        tw = {}
        for c in per_cell:
            for dim, v in per_cell[c].get(cfg, {}).get("three_way", {}).items():
                tw.setdefault(dim, {})[c] = v
        knobs[cname(cfg)] = {dim: {name: agg({c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], v[j]) for c, v in t.items()})
                                   for j, name in enumerate(("agreement", "regret", "chance"))}
                             for dim, t in sorted(tw.items(), key=lambda kv: knob_order(kv[0]))}
    classes = {cname(cfg): {k: agg(rows(lambda c, cfg=cfg, k=k: (per_cell[c].get(cfg, {}).get("by_class") or {}).get(k, (None,))[0]))
                            for k in ("coarse", "mid", "fine", "categorical")} for cfg in (CURRENT, DECISIVE)}
    dac = {}
    dcells = {c for (d, c) in loaded if d == "dac9" and c in per_cell}
    if dcells:
        dac_cfg = ("dac9", "stem", "native", "own")
        fold3_only = all(folds[ps[c[0]]["band"]] == 3 for c in dcells)
        summ = wide if fold3_only else (lambda r: agg2(r, large))
        me = main_effects({c: per_cell[c] for c in dcells}, "cross_half").get("DI dac9-cprime", {})
        vs_c = summ(paired(m_of(dac_cfg, "cross_half", dcells), m_of(CURRENT, "cross_half", dcells)))
        vs_d = summ(paired(m_of(dac_cfg, "cross_half", dcells), m_of(DECISIVE, "cross_half", dcells)))
        dac = {"interval": "wider of band and part (fold 3 only)" if fold3_only else "band-clustered",
               "dac9|stem|native|own same_half": summ(m_of(dac_cfg, "same_half", dcells)),
               "minus current cross_half": vs_c, "minus decisive cross_half": vs_d,
               "minus current same_half": summ(paired(m_of(dac_cfg, "same_half", dcells), m_of(CURRENT, "same_half", dcells))),
               "minus current reliable_accuracy": summ(paired(m_of(dac_cfg, "reliable_accuracy", dcells), m_of(CURRENT, "reliable_accuracy", dcells))),
               "DI dac9-cprime main effect cross_half": summ({c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], v) for c, v in me.items()})}
        if fold3_only:
            dac["extension_due_on_the_users_yes"] = dac_extension_due(vs_c, vs_d)
    by_what = {}
    for c, d, i, what, h, dev in checks:
        by_what.setdefault(what, []).append(dev)
    float_checks, renders = {}, {}
    for p in (OUT / "renders").glob("*/*/*.json"):
        r = json.loads(p.read_text())
        renders[r["di"]] = renders.get(r["di"], 0) + r["renders"]
        for c in r.get("checks_float", []):
            float_checks.setdefault(c[1], []).append(c[3])
    for pg in (OUT / "step0").glob("pregain-*.json"):
        renders["step0-pregain"] = renders.get("step0-pregain", 0) + json.loads(pg.read_text()).get("renders", 0)
    summ_dev = lambda v: {"n": len(v), "median": statistics.median(v), "max": max(v), "over_tol": sum(x > CHECK_TOL for x in v)}  # noqa: E731
    rep = {"sigma": meta["hash"], "cells": len(per_cell), "large_offset_parts": large, "gcc_rebuild_vs_stem": gccs,
           "renders_used": renders, "renders_expected": meta["expected_renders"],
           "corner_checks_flac": {w: summ_dev(v) for w, v in by_what.items()},
           "corner_checks_float": {w: summ_dev(v) for w, v in float_checks.items()},
           "ceiling": {"rho": agg(ceiling_rows), "rho_worst": agg(rows(lambda c: ceil[c]["rho_worst"])),
                       "reliable_pairs_per_cell": {"min": min(rel_n.values(), default=0), "median": statistics.median(rel_n.values()) if rel_n else 0}},
           "fallback": fallback, "table": table, "contrasts": contrasts, "main_effects": eff,
           "three_way_per_knob": knobs, "pair_classes": classes, "dac9": dac,
           "fold3_cells": sum(folds[ps[c[0]]["band"]] == 3 for c in per_cell)}
    K._atomic(OUT / "report.json", rep)
    cur, dec = table[cname(CURRENT)], table.get(cname(DECISIVE), {})
    f = lambda s: f"{s['band_weighted_mean']:+.3f} [{s['lo90']:+.3f}, {s['hi90']:+.3f}]" if s.get("lo90") is not None else str(s.get("band_weighted_mean"))  # noqa: E731
    print("ceiling (true cross-half rho):", f(rep["ceiling"]["rho"]))
    print("current same-half rho:", f(cur["same_half"]), "reliable acc:", f(cur["reliable_accuracy"]))
    if dec:
        print("decisive same-half rho:", f(dec["same_half"]), "cross-half:", f(dec["cross_half"]))
    print("renders used:", renders, "expected:", meta["expected_renders"])


def cmd_pregain(cell=PREGAIN_CELL):
    """Step 0: is input gain a pure pre-gain? 5 renders (warm-up + 4) through the measure DI at S."""
    import numpy as np

    from learn import confirm_run as CR

    out = OUT / "step0" / f"pregain-{cell[0]}-{cell[1]}.json"
    if out.exists():
        print(json.loads(out.read_text()))
        return
    _wait_cap()
    slug, amp = cell
    part = K.parts()[slug]
    di, ref = K.measure_di(part), CR.mono(part["crop"] / "reference.wav")
    rr = K.Renderer()
    try:
        menu = rr.menu()
        sel, S = menu[amp][K.START[part["gain_class"]][amp]]
        ys = {}
        for name, scale, x in pregain_plan(S, dims=K.space(amp, S)):
            ys[name] = rr.render((di * scale).astype(np.float32), sel, x)
        renders = rr.count
    finally:
        rr.close()
    skip = int(TRIM_S * K.P.SR)
    res = {"cell": list(cell), "S_input_gain": S.get(INPUT_GAIN), "compressor_on": S.get(("compressor", "compressorActive")),
           "gate_on": S.get(("parameters", "gateActive")), "di_peak_dbfs": 20 * math.log10(float(np.abs(di).max())),
           "renders": renders, "pairs": {}}
    res["clip_risk"] = res["di_peak_dbfs"] + PREGAIN_DB > 0      # a +6 dB DI past 0 dBFS: flag the reading
    res["repeat_floor_db"] = residual_db(ys["warm-up"], ys[f"knob+{PREGAIN_DB:g}dB"], skip)
    for e in (PREGAIN_DB, -PREGAIN_DB):
        a, b = ys[f"di{e:+g}dB"], ys[f"knob{e:+g}dB"]
        ja, jb = K.judge(ref, a, di, part["judge_lag"]), K.judge(ref, b, di, part["judge_lag"])
        res["pairs"][f"{e:+g}dB"] = {"residual_db": residual_db(a, b, skip),
                                     "max_abs_diff": float(np.max(np.abs(a[skip:] - b[skip:]))),
                                     "judge_di_scaled": ja, "judge_knob": jb,
                                     "judge_abs_log": {h: deviation(ja[h], jb[h]) for h in HALVES}}
    out.parent.mkdir(parents=True, exist_ok=True)
    K._atomic(out, res)
    print(json.dumps(res, indent=1))


def cmd_diag():
    """Step 0: the zero-render diagnostics (plan, table 1), on the stored 2b, K_S and arm A files."""
    import numpy as np

    from learn import direc as D
    from learn import rank_margin as RM
    from learn import song_settings as SS

    ps, folds, ms = K.parts(), SS.folds(), L.menu_S()
    out = {}
    lv = L.OUT
    traj = {(p.parent.name, p.stem): [(L._settings_dict(x), d) for x, d in json.loads(p.read_text())["trajectory"]]
            for p in sorted((lv / "replay" / "ks").glob("*/*.json"))}
    draws = L.local_draw(traj)
    nets = L.NETS
    d1, d2, d3, d6, fb2b, cellrows = {}, {}, {}, {}, {}, {n: {} for n in (*nets, "E4")}
    for (slug, amp), dr in sorted(draws.items()):
        pts = {n: json.loads((lv / "local" / n / f"{slug}-{amp}.json").read_text()) for n in nets}
        fb2b[f"{slug}|{amp}"] = {n: pts[n].get("fallback") for n in nets}
        xs = [x for x, _ in dr]
        true = {h: [p["true"][h] for p in pts["C'"]["points"]] for h in HALVES}
        S = ms[amp][ps[slug]["gain_class"]][1]
        dims = K.space(amp, S)
        band, cls = ps[slug]["band"], ps[slug]["gain_class"]
        d1[(slug, amp)] = {"rho": ceiling(true), "rho_worst": ceiling(true, rho_worst),
                           "sd_log_true": _mean(statistics.pstdev([math.log(v) for v in true[h] if _pos(v)]) for h in HALVES),
                           "reliable_pairs": len(reliable_pairs(true))}
        ig = next(d for d in dims if _k(d) == INPUT_GAIN)
        dg = [L.unit(ig, x) - L.unit(ig, S) for x in xs]
        at_s = [i for i, v in enumerate(dg) if abs(v) < 1e-9]
        for n in (*nets, "E4"):
            if n == "E4":
                obj = {h: [statistics.fmean(math.log(pts[m]["points"][i]["obj"][h]) for m in nets)
                           if all(_pos(pts[m]["points"][i]["obj"][h]) for m in nets) else math.inf
                           for i in range(len(xs))] for h in HALVES}
            else:
                obj = {h: [p["obj"][h] for p in pts[n]["points"]] for h in HALVES}
            cellrows[n][(slug, amp)] = (slug, band, cls, {
                "same_half": same_half(obj, true), "same_half_worst": same_half(obj, true, rho_worst),
                "reliable_accuracy": reliable_accuracy(obj, true),
                "partial_vs_input_gain": _mean(partial_rho(obj[h], true[h], dg) for h in HALVES),
                "at_S_input_gain": _mean(rho([obj[h][i] for i in at_s], [true[h][i] for i in at_s]) for h in HALVES)
                if len(at_s) >= 5 else None, "n_at_S_input_gain": len(at_s),
                "classes": concordance_by_class(dims, xs, obj, true)})
            if n == "C'":
                d3[(slug, amp)] = knob_regression(dims, S, xs, obj, true)
    out["D0_alignment"] = alignment_table()
    out["D1_ceiling_2b"] = {"cells": {f"{s}|{a}": v for (s, a), v in d1.items()},
                            "rho": agg({c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], v["rho"]) for c, v in d1.items()}),
                            "rho_worst": agg({c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], v["rho_worst"]) for c, v in d1.items()})}
    out["D2_partial_and_at_S"] = {n: {k: agg({c: (v[0], v[1], v[2], v[3][k]) for c, v in r.items()})
                                      for k in ("same_half", "same_half_worst", "reliable_accuracy",
                                                "partial_vs_input_gain", "at_S_input_gain")}
                                  for n, r in cellrows.items()}
    out["D2_cells_C'"] = {f"{s}|{a}": {k: v[3][k] for k in ("same_half", "partial_vs_input_gain", "at_S_input_gain", "n_at_S_input_gain")}
                          for (s, a), v in cellrows["C'"].items()}
    tally = {}
    for c, hs in d3.items():
        for h, dd in hs.items():
            for dim, v in dd.items():
                t = tally.setdefault(dim, {"bias": {}, "signs": {}})
                t["bias"].setdefault(c, []).append(v["bias"])
                key = v["true"] + v["obj"]
                t["signs"][key] = t["signs"].get(key, 0) + 1
    out["D3_knob_regression_C'"] = {dim: {"bias": agg({c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], statistics.fmean(b))
                                                        for c, b in t["bias"].items()}),
                                          "sign_table_true_obj": t["signs"],
                                          "agree_where_true_nonzero": [sum(v for k, v in t["signs"].items() if k[0] != "0" and k[0] == k[1]),
                                                                       sum(v for k, v in t["signs"].items() if k[0] != "0")]}
                                    for dim, t in sorted(tally.items())}
    lvl = {}
    for slug in sorted(s for s in ps if s not in EXCLUDED):
        meas = K.measure_di(ps[slug])
        reb = np.load(SS.OUT / "rebuilt" / f"{slug}.npy")
        lag = int(RM.gcc_lag(reb, meas))
        al = np.roll(reb, -lag) if lag else reb
        if lag > 0:
            al[-lag:] = 0
        elif lag < 0:
            al[:-lag] = 0
        fm = D.fine_metrics(al, meas)
        p999 = lambda x: 20 * math.log10(float(np.quantile(np.abs(x), 0.999)))  # noqa: E731
        lvl[slug] = {"band": ps[slug]["band"], "fold": folds[ps[slug]["band"]], "gcc_lag": lag,
                     "p999_db_rebuilt_minus_measure": p999(reb) - p999(meas),
                     **{k: fm[k] for k in ("crest_1ms_err", "crest_5ms_err", "crest_10ms_err", "quiet_db", "gap_db", "hf_3_8k_db")}}
    ig_bias = {}
    for (slug, amp), hs in d3.items():
        for h, dd in hs.items():
            if "parameters/inputGain" in dd:
                ig_bias.setdefault(slug, []).append(dd["parameters/inputGain"]["bias"])
    corr = {}
    from scipy.stats import spearmanr
    sl = sorted(ig_bias)
    for k in ("p999_db_rebuilt_minus_measure", "crest_1ms_err", "quiet_db"):
        xs = [lvl[s][k] for s in sl]
        ys = [statistics.fmean(ig_bias[s]) for s in sl]
        corr[k] = {"n_parts": len(sl), "spearman": float(spearmanr(xs, ys).correlation) if len(sl) >= 3 and all(_finite(x) for x in xs) else None}
    out["D4_di_level"] = {"parts": lvl, "vs_input_gain_bias_fold3": corr}
    sd = {}
    for n in ("1z", "1a", "1b", "E4"):
        for k in ("same_half", "same_half_worst"):
            diffs = {c: (v[0], v[1], v[2], (v[3][k] - cellrows["C'"][c][3][k]) if v[3][k] is not None and cellrows["C'"][c][3][k] is not None else None)
                     for c, v in cellrows[n].items()}
            by = {}
            for c, v in diffs.items():
                if v[3] is not None:
                    by.setdefault(v[1], {}).setdefault(c[0], []).append(v[3])
            bands = [statistics.fmean(statistics.fmean(p) for p in parts.values()) for parts in by.values()]
            sd[f"{n}-C' {k}"] = {"diff": agg(diffs), "sigma_d_band_sd": statistics.stdev(bands) if len(bands) > 1 else None}
    out["D5_sigma_d"] = sd
    out["D6_coarse_fine_2b"] = {n: {k: agg({c: (v[0], v[1], v[2], v[3]["classes"][k][0]) for c, v in r.items()})
                                    for k in ("coarse", "mid", "fine", "categorical")} for n, r in cellrows.items() if n in ("C'", "E4")}
    d7, knob_tally = {}, {}
    for slug, amp in cells():
        S = ms[amp][ps[slug]["gain_class"]][1]
        c = _kc(slug, amp)
        for search, held in K.DIRECTIONS:
            run = c["runs"][search]
            if "K_S" not in run:
                continue
            kt, _ = L.replay_ks(amp, S, run["K_S"]["evals"], search)
            stored, _ = L.stored_a(slug, amp, search)
            ap, _ = arm_a_path(amp, S, stored["objective_curve"])
            ka = {K.key(x): v for x, v in ap}
            kk = {K.key(x): d for x, d in kt}
            shared = sorted(set(ka) & set(kk))
            r = rho([ka[k] for k in shared], [kk[k][search] for k in shared]) if len(shared) >= 8 else None
            n, agreed, diff = first_divergence(ap, kt)
            for k in agreed:
                knob_tally.setdefault("/".join(k), [0, 0])[0] += 1
            for k in diff:
                knob_tally.setdefault("/".join(k), [0, 0])[1] += 1
            d7[(slug, amp, search)] = (slug, ps[slug]["band"], ps[slug]["gain_class"], r, len(shared), n)
    out["D7_armA_x_KS"] = {"directions": len(d7), "shared_keys": {"min": min(v[4] for v in d7.values()),
                                                                  "median": statistics.median(v[4] for v in d7.values()),
                                                                  "max": max(v[4] for v in d7.values())},
                           "common_prefix": {"median": statistics.median(v[5] for v in d7.values()),
                                             "max": max(v[5] for v in d7.values())},
                           "rho_shared": agg({k: (v[0], v[1], v[2], v[3]) for k, v in d7.items()}),
                           "knob_decisions_agreed_vs_first_divergence": dict(sorted(knob_tally.items()))}
    lim = {}
    for slug, amp in cells():
        S = ms[amp][ps[slug]["gain_class"]][1]
        cls = ps[slug]["gain_class"]
        fin = {}
        for search, _ in K.DIRECTIONS:
            p = K.OUT / "cells" / slug / amp / f"K_S-{search}.json"
            if p.exists():
                fin[search] = L._settings(p)
        for d in K.space(amp, S):
            if d.kind not in ("cont", "log"):
                continue
            t = lim.setdefault(f"{amp}|{cls}|{d.name}", {"lo": 0, "hi": 0, "interior": 0, "dirs_agree": 0, "pairs": 0})
            for x in fin.values():
                t[limit_side(d, x)] += 1
            if len(fin) == 2:
                t["pairs"] += 1
                t["dirs_agree"] += abs(L.unit(d, fin["A"]) - L.unit(d, fin["B"])) <= 1 / 8 + 1e-9
    out["D8_KS_optimum_limits"] = lim
    out["D9_fallbacks"] = {"2b_local": fb2b,
                           "armA": sum(json.loads(p.read_text()).get("fallback", 0) for p in (L.SS_OUT / "armA").glob("*/*/[AB].json"))}
    out["D10_step0c"] = "docs/audits/arm-a-2026-10-16/exp4-step0c-dac-cells.json (committed; zero renders)"

    def clean(o):
        if isinstance(o, dict):
            return {(("|".join(map(str, k))) if isinstance(k, tuple) else k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, float) and not math.isfinite(o):
            return None
        return o
    (OUT / "step0").mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "step0" / "diagnostics.json", clean(out))
    c = out["D2_partial_and_at_S"]["C'"]
    print("2b C' same-half", c["same_half"]["band_weighted_mean"], "partial|input gain", c["partial_vs_input_gain"]["band_weighted_mean"],
          "at S's input gain", c["at_S_input_gain"]["band_weighted_mean"])
    print("true cross-half ceiling (2b)", out["D1_ceiling_2b"]["rho"]["band_weighted_mean"])


def alignment_table():
    """Step 0 (amendment 1), zero renders: `alignment_row` for every part from its stored signals."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import rank_margin as RM
    from learn import song_settings as SS

    def g(x, y):
        n = min(len(x), len(y))
        return int(RM.gcc_lag(x[:n], y[:n]))

    ps, out = K.parts(), {}
    for slug in sorted(s for s in ps if s not in EXCLUDED):
        meas, stem = K.measure_di(ps[slug]), SS.stem(slug)
        reb = np.load(SS.OUT / "rebuilt" / f"{slug}.npy")
        ref = CR.mono(ps[slug]["crop"] / "reference.wav")
        out[slug] = {"band": ps[slug]["band"], **alignment_row(ps[slug]["judge_lag"], g(reb, meas), g(reb, stem),
                                                               g(stem, ref), g(ref, meas))}
    return out


def cmd_align():
    out = alignment_table()
    (OUT / "step0").mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "step0" / "alignment.json", out)
    for s, r in out.items():
        print(f"{s[:34]:34s} judge+52 {r['judge_offset']:5d}  gcc ref~meas {r['gcc_reference_measure']:5d}  "
              f"reb~stem {r['gcc_rebuild_stem']:4d}  closure {r['closure']:5d}{'  LARGE' if r['large_offset'] else ''}")


def cmd_dac_prep(all_folds=False):
    """The add-on: each fold-3 part's measure DI (every part's, for the extension) to
    `dac/in/<slug>.npy` for `learn/dac_roundtrip.py`."""
    import numpy as np

    from learn import song_settings as SS

    ps, folds = K.parts(), SS.folds()
    d = OUT / "dac" / "in"
    d.mkdir(parents=True, exist_ok=True)
    for slug in sorted(s for s in ps if s not in EXCLUDED and (all_folds or folds[ps[s]["band"]] == 3)):
        if (d / f"{slug}.npy").exists():
            continue
        np.save(d / f"{slug}.npy", K.measure_di(ps[slug]))
        print(slug, flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("align", "diag", "pregain", "sigma", "render", "score", "report", "dac-prep",
                                    "rebuild-ref", "report-1b"))
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--di", default="cprime,measure")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--after", type=int, nargs="*", default=())
    ap.add_argument("--cell", default=None, help="pregain: slug|amp (default: the plan's cell)")
    ap.add_argument("--out", default=None, help="sigma: write elsewhere (a dry run)")
    ap.add_argument("--all-folds", action="store_true", help="dac-prep/render --di dac9: the extension (user's yes)")
    ap.add_argument("--accept-guard-stop", action="store_true",
                    help="render: start although all shards' renders would cross the disk guard (the user's choice)")
    a = ap.parse_args(argv)
    sh = tuple(int(x) for x in a.shard.split("/"))
    folds = (3,) if a.di == "dac9" and not a.all_folds else None
    {"align": cmd_align, "diag": cmd_diag, "pregain": lambda: cmd_pregain(tuple(a.cell.split("|")) if a.cell else PREGAIN_CELL),
     "sigma": lambda: cmd_sigma(a.out), "render": lambda: cmd_render(sh, a.di, a.after, folds, a.accept_guard_stop),
     "score": lambda: cmd_score(a.di, a.workers), "report": cmd_report, "dac-prep": lambda: cmd_dac_prep(a.all_folds),
     "rebuild-ref": cmd_rebuild_ref, "report-1b": cmd_report_1b}[a.cmd]()


if __name__ == "__main__":
    main()
