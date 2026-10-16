"""Arm B in sound space, the data (`docs/song-to-settings-soundspace-plan.md`, B2's inputs).

Run order (renders use at most 3 processes machine-wide; nothing here trains):

    .venv/bin/python -m learn.song_relabel weights                 # s_j from diag/sens -> weights.json (0 renders)
    .venv/bin/python -m learn.song_relabel draw                    # relabel plan + record-like examples (0 renders)
    .venv/bin/python -m learn.song_relabel render-new --shard i/3  # 2,500 record-like renders (disk check first)
    .venv/bin/python -m learn.song_relabel probe --shard i/3       # 9 probes per relabel example
    $TORCH_PY        -m learn.song_relabel features                # new examples' features (disk check, parity)
    .venv/bin/python -m learn.song_relabel sets                    # members, weights, the repeat check

The pure functions (weights, draws, anchors, probes, sets, the mixture) take plain data and are
unit-tested; the CLI steps are the only code that reads the Mac's files or renders.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import shutil
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import knob_ceiling as K  # noqa: E402
from learn import song_bank as B  # noqa: E402
from learn import song_diag as D  # noqa: E402
from learn.song_readout import finite  # noqa: E402

OUT = B.OUT.parent / "soundspace"
BANK2 = OUT / "bank2"
REL = OUT / "relabel"
SETS = OUT / "sets"
WEIGHTS = OUT / "weights.json"
PLAN = OUT / "relabel-plan.json"
DIAG = B.OUT.parent / "diag"

# seeds (plan, ledger)
SEED_RELABEL = 20261026
SEED_PROBES = 20261027
SEED_NEW = 20261028

CLASSES = ("clean", "crunch")
N_RELABEL_PER_FOLD = 250
N_NEW = 2500
NEW_BASE = 10000
PULLS = (0.25, 0.5, 0.75, 1.0)
PROBE_SIGMA = 0.15
TAU = 0.25
DS_FLOOR = 0.1
REPEAT_EVERY = 50                       # 1 in 50 relabel examples: 20 label re-renders
REPEAT_TOL = 1e-3
WEIGHT_CLIP = (0.25, 4.0)
CAPS = {"new": 2550, "relabel": 9050}
DISK_GUARD_GB = 31.0
DISK_NEED_GB = DISK_GUARD_GB + 2.5      # before the record-like renders and before `features`

RIGHT_ACTIVE = "cabParameters/rightCabActive"
RIGHT_GATED = ("cabParameters/rightCabMicLevel", "cabParameters/rightCabDistance", "cabParameters/rightCabPosition")
RIGHT_MIC = "cabParameters/rightMicType"

# The plan's table (2 decimals), from the stored step-1.2 medians; `weights` asserts the match.
PLAN_TABLE = {
    "pr12": {"pr12Amp/pr12Treble": 2.24, "parameters/inputGain": 1.73, "pr12Amp/pr12Volume": 1.64,
             RIGHT_ACTIVE: 1.18, "pr12Amp/pr12Bass": 0.83, "cabParameters/rightCabMicLevel": 0.61,
             "cabParameters/leftCabPosition": 0.56, "cabParameters/leftCabDistance": 0.55,
             "cabParameters/rightCabDistance": 0.44, "cabParameters/rightCabPosition": 0.25},
    "sw50r": {"sw50rAmp/sw50rInputMode": 2.38, "sw50rAmp/sw50rTrebleBoost": 2.11, "sw50rAmp/sw50rLevel": 1.86,
              "parameters/inputGain": 1.74, "sw50rAmp/sw50rVolume": 1.65, "sw50rAmp/sw50rBright": 1.43,
              RIGHT_ACTIVE: 0.68, "sw50rAmp/sw50rMid": 0.62, "sw50rAmp/sw50rTreble": 0.58,
              "sw50rAmp/sw50rBass": 0.46, "cabParameters/rightCabMicLevel": 0.45,
              "cabParameters/leftCabDistance": 0.42, "cabParameters/leftCabPosition": 0.25,
              "cabParameters/rightCabDistance": 0.25, "cabParameters/rightCabPosition": 0.25},
    "ac20": {"ac20Amp/ac20BassTreble": 3.44, "ac20Amp/ac20Volume": 1.93, "parameters/inputGain": 1.80,
             "ac20Amp/ac20Bright": 1.07, "ac20Amp/ac20Cut": 0.98, "ac20Amp/ac20Power": 0.75, RIGHT_ACTIVE: 0.64,
             "cabParameters/leftCabDistance": 0.36, "cabParameters/leftCabPosition": 0.31,
             "cabParameters/rightCabMicLevel": 0.30, "cabParameters/rightCabDistance": 0.25,
             "cabParameters/rightCabPosition": 0.25},
}


# ============================================================================== sensitivity weights

def sens_medians(sens_meta, results):
    """Median judge change per amp and setting from step 1.2. `sens_meta`: diag/sens.json (the
    bases' settings); `results`: [(index into sens_meta, sens file dict)]. The right cab's level,
    distance and position use only bases with the right cab on. -> {amp: {setting: median}}."""
    by = {}
    for n, s in results:
        meta = sens_meta[n]
        for bname, b in s["bases"].items():
            on = meta["bases"][bname].get(RIGHT_ACTIVE) == "true"
            for k, v in b["delta"].items():
                if v is None or (k in RIGHT_GATED and not on):
                    continue
                by.setdefault(s["amp"], {}).setdefault(k, []).append(v)
    return {a: {k: statistics.median(v) for k, v in d.items()} for a, d in by.items()}


def weight_table(medians, clip=WEIGHT_CLIP):
    """s_j = median / the amp's mean median, clipped. -> {amp: {setting: s_j}}."""
    out = {}
    for amp, med in medians.items():
        m = statistics.fmean(med.values())
        out[amp] = {k: min(clip[1], max(clip[0], v / m)) for k, v in med.items()}
    return out


def table_matches_plan(table, plan=PLAN_TABLE):
    """Every setting of the plan's table, to 2 decimals, and nothing extra. -> list of mismatches."""
    bad = []
    for amp, row in plan.items():
        got = table.get(amp, {})
        for k in sorted(set(row) | set(got)):
            if k not in got or k not in row or round(got[k], 2) != row[k]:
                bad.append((amp, k, got.get(k), row.get(k)))
    return bad


def right_cab_off(label):
    return str(label.get(RIGHT_ACTIVE, "true")).lower() in ("false", "0")


def label_weights(amp, label, table):
    """Union-layout weights for one label: (cont weights, switch weights, mic mask). A setting
    absent from the label weighs 0; with the label's right cab off, its level, distance, position
    and the right mic are masked. Mics keep B0's weight (1)."""
    from learn import song_model as M

    off = right_cab_off(label)
    row = table[amp]
    cw = []
    for n in M.CONT:
        if n not in label or (off and n in RIGHT_GATED):
            cw.append(0.0)
        else:
            assert n in row, (amp, n)
            cw.append(float(row[n]))
    sw = []
    for n in M.SW:
        if n not in label:
            sw.append(0.0)
        else:
            assert n in row, (amp, n)
            sw.append(float(row[n]))
    mic = [0.0 if (n not in label or str(label[n]) not in M.MICS or (off and n == RIGHT_MIC)) else 1.0
           for n in M.CAT]
    return cw, sw, mic


# ============================================================================== the relabel draw

def cell_counts(n=N_RELABEL_PER_FOLD, cells=len(K.AMPS) * len(CLASSES)):
    """n split over the cells in their seeded order: the first get one more (250 / 6: 42 × 4, 41 × 2)."""
    q, r = divmod(n, cells)
    return [q + 1 if j < r else q for j in range(cells)]


def relabel_draw(examples, seed=SEED_RELABEL, per_fold=N_RELABEL_PER_FOLD):
    """Original bank examples only, `per_fold` per fold, over amp × class cells (seeded order,
    `cell_counts`), broad and jittered alternating within a cell (a mode that runs out passes
    its turn). -> sorted list of example indices."""
    rng = random.Random(seed)
    out = []
    for f in range(4):
        cells = [(a, c) for a in K.AMPS for c in CLASSES]
        rng.shuffle(cells)
        for (a, c), n in zip(cells, cell_counts(per_fold, len(cells))):
            pool = [e for e in examples if e["i"] < NEW_BASE and e["fold"] == f and e["amp"] == a and e["class"] == c]
            modes = {m: sorted(e["i"] for e in pool if e["mode"] == m) for m in ("broad", "jitter")}
            for m in modes:
                rng.shuffle(modes[m])
            got, turn = [], 0
            while len(got) < n and (modes["broad"] or modes["jitter"]):
                m = ("broad", "jitter")[turn % 2]
                turn += 1
                if modes[m]:
                    got.append(modes[m].pop(0))
            assert len(got) == n, f"fold {f} {a}/{c}: only {len(got)} examples"
            out += got
    return sorted(out)


def optimum_part(path):
    """knob-ceiling/cells/<part>/<amp>/K_S-<half>.json -> part."""
    return pathlib.Path(path).parent.parent.name


def optima_by_part(ks_opt):
    """`song_bank.ks_optima()` -> {fold: {part: [(amp, class, path)]}}."""
    out = {}
    for f, rows in ks_opt.items():
        for a, c, p in rows:
            out.setdefault(f, {}).setdefault(optimum_part(p), []).append((a, c, p))
    return out


def _cont(dims):
    return [d for d in dims if d.kind in ("cont", "log")]


def unit_of(d, x):
    v = x.get((d.module, d.key))
    return d.to_unit(v if v is not None else d.lo)


def weighted_unit_distance(dims, x, y, w):
    """Σ s_j |Δu| / Σ s_j over continuous dims with a weight (w: {name: s_j})."""
    num = den = 0.0
    for d in _cont(dims):
        s = w.get(d.name, 0.0)
        num += s * abs(unit_of(d, x) - unit_of(d, y))
        den += s
    return num / den if den else math.inf


def anchor_for(label_x, S, dims, fold, amp, cls, optima, weights):
    """The nearest of the example's OWN fold's K_S optima (s-weighted unit distance on continuous
    dims), each optimum laid over S as the bank's centres are: same amp and class; else same amp,
    either class ("other-class"); else None ("none"). `optima`: {fold: [(amp, class, settings)]}
    (only the example's fold is read). -> (anchor settings or None, fallback tag)."""
    rows = optima.get(fold, [])
    cw, _, _ = weights
    w = {n: s for n, s in zip(_layout_cont(), cw)}
    for tag, cands in (("", [r for r in rows if r[0] == amp and r[1] == cls]),
                       ("other-class", [r for r in rows if r[0] == amp])):
        if cands:
            over = [{**S, **r[2]} for r in cands]
            best = min(range(len(over)), key=lambda j: (weighted_unit_distance(dims, label_x, over[j], w), j))
            return over[best], tag
    return None, "none"


def _layout_cont():
    from learn import song_model as M

    return M.CONT


def probes(label_x, S, dims, anchor, rng):
    """The relabel probes for one example, in a fixed order -> {name: settings}. S (the scale);
    pulls of the continuous settings toward the anchor (label's mics and switches); the label with
    the anchor's mics; with the anchor's switches (a third jitter if they already match); two
    continuous jitters σ 0.15 (mics and switches kept). Without an anchor the four pulls are
    jitters. `rng`: random.Random(int_seed(SEED_PROBES, i))."""
    from learn import arm_a_levers as AL

    out = {"S": dict(S)}
    cont = _cont(dims)
    if anchor is not None:
        a = dict(S)
        a.update(anchor)
        for t in PULLS:
            u = {(d.module, d.key): unit_of(d, label_x) + t * (unit_of(d, a) - unit_of(d, label_x)) for d in cont}
            out[f"pull{t:g}"] = AL.build(dims, label_x, u, label_x, label_x, (label_x, a))
        lab_u = {(d.module, d.key): unit_of(d, label_x) for d in cont}
        out["mics"] = AL.build(dims, label_x, lab_u, a, label_x, (label_x,))
        sw = AL.build(dims, label_x, lab_u, label_x, a, (label_x,))
        if K.key(sw) == K.key(label_x):
            out["jitter2"] = D.jitter(dims, label_x, label_x, rng, 1.0, PROBE_SIGMA)[0]
        else:
            out["switches"] = sw
    else:
        for j in range(4):
            out[f"jitter_p{j}"] = D.jitter(dims, label_x, label_x, rng, 1.0, PROBE_SIGMA)[0]
        out["mics"] = None
        out["switches"] = None
    for j in range(2):
        out[f"jitter{j}"] = D.jitter(dims, label_x, label_x, rng, 1.0, PROBE_SIGMA)[0]
    return {k: v for k, v in out.items() if v is not None}


def probe_renders(label_x, probe_set):
    """Unique settings to render, excluding any identical to the label (d = 0 by definition).
    -> (key -> first name, name -> key)."""
    lk = K.key(label_x)
    first, of = {}, {}
    for name, x in probe_set.items():
        k = K.key(x)
        of[name] = k
        if k != lk:
            first.setdefault(k, name)
    return first, of


def label_of(dims, x):
    """A settings dict as a bank label: unit floats for continuous settings, stored strings else."""
    return {d.name: (unit_of(d, x) if d.kind in ("cont", "log") else x.get((d.module, d.key), d.values[0]))
            for d in dims}


# ============================================================================== record-like examples

def record_centre(optima_parts, fold, amp, cls, rng):
    """A centre for a record-like example: a part uniform among the fold's parts with an optimum for
    this amp and class, then one of that part's optima; else the same amp, either class; else S.
    `optima_parts`: {fold: {part: [(amp, class, path)]}}. -> (centre, fallback tag)."""
    parts = optima_parts.get(fold, {})
    for tag, ok in (("", lambda r: r[0] == amp and r[1] == cls), ("other-class", lambda r: r[0] == amp)):
        names = sorted(p for p, rows in parts.items() if any(ok(r) for r in rows))
        if names:
            part = rng.choice(names)
            return rng.choice(sorted(r[2] for r in parts[part] if ok(r))), tag
    return "S", "none"


def new_examples(windows, backings, optima_parts, target_tracks, seed=SEED_NEW, n=N_NEW, base=NEW_BASE):
    """The record-like examples, as `song_bank.draw` but with the centre always a K_S optimum of the
    example's own fold (uniform per part). No diagnostics target track. -> list of example dicts."""
    rng = random.Random(seed)
    by_fold = {f: sorted((w for w in windows if str(w["fold"]) == str(f) and w["path"] not in target_tracks),
                         key=lambda w: (w["path"], w["start"])) for f in range(4)}
    shared = sorted((w for w in windows if w["fold"] == "all" and w["path"] not in target_tracks),
                    key=lambda w: (w["path"], w["start"]))
    ex = []
    for k in range(n):
        fold = rng.randrange(4)
        w = rng.choice(by_fold[fold]) if rng.random() < 0.5 else rng.choice(shared)
        amp = rng.choice(K.AMPS)
        cls = rng.choice(CLASSES)
        centre, fb = record_centre(optima_parts, fold, amp, cls, rng)
        b = sorted(x[2] for x in backings if x[1] == fold)
        ex.append({"i": base + k, "fold": fold, "window": w, "amp": amp, "class": cls, "mode": "jitter",
                   "centre": centre, "centre_fallback": fb, "centre_fold": None if centre == "S" else fold,
                   "backing": rng.choice(b) if b else None,
                   "second_guitar": rng.random() < 0.3, "mastered": rng.random() < 0.5,
                   "aac": rng.random() < 0.5, "separated": rng.random() < 0.5, "seed": rng.randrange(2 ** 31)})
    return ex


def assert_new_clean(new, target_tracks, fold_of_band, optima_parts):
    """Single-fold examples: a fold-own window's band maps to the example's fold; the centre is one
    of the example's own fold's optima; no diagnostics target track; indices from NEW_BASE."""
    for e in new:
        assert e["i"] >= NEW_BASE
        assert e["window"]["path"] not in target_tracks, e["i"]
        if e["window"]["fold"] != "all":
            assert fold_of_band[e["window"]["band"]] == e["fold"], e["i"]
        if e["centre"] not in (None, "S"):
            own = {r[2] for rows in optima_parts.get(e["fold"], {}).values() for r in rows}
            assert e["centre_fold"] == e["fold"] and e["centre"] in own, e["i"]


# ============================================================================== the mixture (bank parity)

def mixture_with(e, g, others, load_other, levels, eval_mix_lufs, read_backing=None):
    """`song_aug.mixture` with the render passed in: (guitar, mix, rng), the same draws in the same
    order. `others`: same-fold example indices with renders; `load_other(j)` loads one."""
    import numpy as np

    from learn import song_aug as A

    rng = random.Random(e["seed"] ^ 0x5EED)
    n = len(g)
    if e["backing"]:
        if read_backing is None:
            import soundfile as sf
            back, _ = sf.read(e["backing"], dtype="float64")
        else:
            back = read_backing(e["backing"])
    else:
        back = np.zeros(n)
    back = back.mean(axis=1) if back.ndim == 2 else back
    back = np.pad(back, (0, max(0, n - len(back))))[:n]
    g2b = rng.choice(levels)
    lg, lb = A.lufs(g), A.lufs(back)
    gain_b = 10 ** ((lg - g2b - lb) / 20) if lb > -70 else 0.0
    guitar = g.copy()
    if e["second_guitar"]:
        cands = [j for j in others if j != e["i"]]
        if cands:
            g2 = load_other(rng.choice(cands))[:n]
            g2 = np.pad(g2, (0, n - len(g2)))
            l2 = A.lufs(g2)
            if l2 > -70:
                guitar = guitar + g2 * 10 ** ((lg - rng.uniform(3, 9) - l2) / 20)
    mix = guitar + back * gain_b
    target = eval_mix_lufs + rng.uniform(-3, 3)
    k = 10 ** ((target - A.lufs(mix)) / 20)
    return g * k, mix * k, rng


def example_features(e, g, others, load_other, levels, eval_mix_lufs, tmp, separator):
    """`song_aug.build`'s per-example path: mixture, mastering (+AAC), separation, features."""
    import numpy as np

    from learn import song_aug as A

    g, mix, rng = mixture_with(e, g, others, load_other, levels, eval_mix_lufs)
    if e["mastered"]:
        mix = A.compress(mix, rng)
        if e["aac"]:
            mix = A.aac(mix, rng, tmp)
    stem = separator(mix.astype(np.float32)).astype(np.float64) if e["separated"] else g
    return A.features(stem, mix)


# ============================================================================== the sets

def half_set(d_half, labels, label, tau=TAU, floor=DS_FLOOR):
    """One example-half's set target. `d_half`: {probe name: d on this half} (S included);
    `labels`: {probe name: label}. Members: the label (d = 0) and every finite probe except S (the
    scale), r = d / d_S, normalised weights ∝ exp(−r / τ). A d_S below `floor` or non-finite keeps
    the point label. -> {"point": bool, "reason", "members": [{name, label, d, r, logw}]}."""
    ds = d_half.get("S")
    if not finite(ds) or ds < floor:
        return {"point": True, "reason": "d_S non-finite" if not finite(ds) else "d_S below floor",
                "members": [{"name": "label", "label": label, "d": 0.0, "r": 0.0, "logw": 0.0}]}
    mem = [("label", label, 0.0)]
    for name in sorted(labels):
        if name == "S":
            continue
        v = d_half.get(name)
        if finite(v):
            mem.append((name, labels[name], float(v)))
    r = [v / ds for _, _, v in mem]
    z = [-x / tau for x in r]
    mx = max(z)
    lse = mx + math.log(sum(math.exp(x - mx) for x in z))
    return {"point": False, "reason": None,
            "members": [{"name": n, "label": lab, "d": v, "r": ri, "logw": zi - lse}
                        for (n, lab, v), ri, zi in zip(mem, r, z)]}


def repeat_check(rows, tol=REPEAT_TOL):
    """rows: [(i, {"A": d, "B": d})] label re-renders against the stored render. Finite halves must
    be within tol; silent (non-finite) halves are dropped and counted, not failed."""
    bad, silent, n = [], [], 0
    for i, d in rows:
        for h in "AB":
            if not finite(d.get(h)):
                silent.append((i, h))
            else:
                n += 1
                if d[h] > tol:
                    bad.append((i, h, d[h]))
    return {"ok": not bad and n > 0, "checked_halves": n, "silent_halves": silent, "failures": bad}


def relabel_map(sets):
    """The reported map, per probe type: share with r ≤ 0.25 and ≤ 0.5; the largest pull t that
    keeps r ≤ 0.25 (mean over example-halves)."""
    by, pulls = {}, []
    for s in sets:
        for h in "AB":
            hs = s[h]
            if hs["point"]:
                continue
            best_t = 0.0
            for m in hs["members"][1:]:
                kind = "pull" if m["name"].startswith("pull") else m["name"].rstrip("0123456789").replace("_p", "")
                by.setdefault(kind, []).append(m["r"])
                if m["name"].startswith("pull") and m["r"] <= 0.25:
                    best_t = max(best_t, float(m["name"][4:]))
            pulls.append(best_t)
    return {"by_probe": {k: {"n": len(v), "share_r_le_0.25": sum(x <= 0.25 for x in v) / len(v),
                             "share_r_le_0.5": sum(x <= 0.5 for x in v) / len(v)} for k, v in sorted(by.items())},
            "mean_largest_pull_t": statistics.fmean(pulls) if pulls else None}


# ============================================================================== guards

def free_gb(path=None):
    return shutil.disk_usage(path or pathlib.Path.home()).free / 1e9


def require_disk(need=DISK_NEED_GB, free=None):
    """The plan's disk check before the record-like renders and before `features`."""
    f = free_gb() if free is None else free
    if f < need:
        raise SystemExit(f"disk check: {f:.1f} GB free, need {need:.1f} GB (31 GB guard + 2.5 GB): ask first")
    return f


def spent(folder):
    """Renders recorded under a folder's per-item json files."""
    return sum(json.loads(p.read_text()).get("renders", 0) for p in pathlib.Path(folder).glob("*.json"))


def check_cap(step, spent_n, planned):
    if spent_n + planned > CAPS[step]:
        raise SystemExit(f"{step}: {spent_n} spent + {planned} planned exceeds the hard cap {CAPS[step]}")


# ============================================================================== CLI steps

def step_weights():
    sens_meta = json.loads((DIAG / "sens.json").read_text())
    results = [(int(p.stem), json.loads(p.read_text())) for p in sorted((DIAG / "sens").glob("*.json"))]
    med = sens_medians(sens_meta, results)
    table = weight_table(med)
    bad = table_matches_plan(table)
    if bad:
        raise SystemExit(f"weights differ from the plan's table: {bad}")
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(WEIGHTS, {"medians": med, "weights": table})
    print("weights match the plan's table")


def _target_tracks():
    return {t["window"]["path"] for t in json.loads((DIAG / "targets.json").read_text())}


def _optima_settings():
    """{fold: [(amp, class, settings dict)]} from `song_bank.ks_optima`."""
    return {f: [(a, c, D.st(json.loads(pathlib.Path(p).read_text()))) for a, c, p in rows]
            for f, rows in B.ks_optima().items()}


def step_draw():
    """relabel-plan.json (1,000 examples: anchors, probes, repeat flags) and bank2/examples.json
    (2,500 record-like examples), with the cap checks. Existing files are never redrawn."""
    if PLAN.exists() or (BANK2 / "examples.json").exists():
        raise SystemExit("the draw exists; it is never redrawn")
    table = json.loads(WEIGHTS.read_text())["weights"]
    menu = D._menu()
    ex = json.loads((B.OUT / "examples.json").read_text())
    chosen = relabel_draw(ex)
    by_i = {e["i"]: e for e in ex}
    optima = _optima_settings()
    plan, planned, fallbacks = {}, 0, {}
    for n, i in enumerate(chosen):
        e = by_i[i]
        r = json.loads((B.OUT / "renders" / f"{i:05d}.json").read_text())
        _, S = D._S(menu, e["amp"], e["class"])
        dims = K.space(e["amp"], S)
        x = D.st(r["settings"])
        anchor, tag = anchor_for(x, S, dims, e["fold"], e["amp"], e["class"], optima,
                                 label_weights(e["amp"], r["label"], table))
        fallbacks[tag] = fallbacks.get(tag, 0) + 1
        ps = probes(x, S, dims, anchor, random.Random(D.int_seed(SEED_PROBES, i)))
        first, _ = probe_renders(x, ps)
        rep = n % REPEAT_EVERY == 0
        planned += len(first) + int(rep)
        plan[str(i)] = {"fold": e["fold"], "amp": e["amp"], "class": e["class"], "window": e["window"],
                        "anchor_fallback": tag, "probes": {k: D.sj(v) for k, v in ps.items()}, "repeat": rep}
    check_cap("relabel", 0, planned)
    fold_of = B.folds()
    tracks = _target_tracks()
    win = json.loads((B.OUT / "windows.json").read_text())
    parts = optima_by_part(B.ks_optima())
    new = new_examples(win, B.backings(), parts, tracks)
    assert_new_clean(new, tracks, fold_of, parts)
    check_cap("new", 0, len(new))
    OUT.mkdir(parents=True, exist_ok=True)
    BANK2.mkdir(parents=True, exist_ok=True)
    K._atomic(PLAN, {"examples": plan, "planned_renders": planned, "anchor_fallbacks": fallbacks})
    K._atomic(BANK2 / "examples.json", new)
    from collections import Counter
    print(len(plan), "relabel examples,", planned, "planned renders; anchors", fallbacks)
    print(len(new), "record-like examples; centre fallbacks", dict(Counter(e["centre_fallback"] for e in new)))
    print("ledger: append the relabel indices and the new examples' windows to the tally before any render")


def step_render_new(shard):
    """The record-like renders, as `song_bank.render` (16-bit peak-normalised FLAC + label json)."""
    import numpy as np
    import soundfile as sf

    from learn import knob_ceiling2 as K2

    D.check_shards(shard[1])
    require_disk()
    guard = D.MemoryGuard()
    ex = json.loads((BANK2 / "examples.json").read_text())
    d = BANK2 / "renders"
    d.mkdir(parents=True, exist_ok=True)
    todo = [e for e in ex[shard[0]::shard[1]] if not (d / f"{e['i']:05d}.json").exists()]
    check_cap("new", len(list(d.glob("*.json"))), len(todo))
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for n, e in enumerate(sorted(todo, key=lambda e: (e["amp"], e["class"], e["i"]))):
            if n % 50 == 0 and not K2.disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            sel, x, label = B.settings_for(e, menu)
            di = D.measured_di(e["window"])
            y = D.trim(rr.render(di, sel, x))
            peak = max(float(np.abs(y).max()), 1e-12)
            sf.write(str(d / f"{e['i']:05d}.flac"), (y / peak * 0.99).astype(np.float32), B.SR, subtype="PCM_16")
            K._atomic(d / f"{e['i']:05d}.json", {"label": label, "peak": peak, "settings": D.sj(x), "renders": 1})
            guard.tick()
    finally:
        rr.close()


def step_probe(shard):
    """Each relabel example's probes through its measure DI, judged per half against the stored
    bank render at lag 0; the 1-in-50 label re-render for the repeat check."""
    from learn import knob_ceiling2 as K2
    from learn import song_aug as A

    D.check_shards(shard[1])
    guard = D.MemoryGuard()
    menu = D._menu()
    plan = json.loads(PLAN.read_text())["examples"]
    REL.mkdir(parents=True, exist_ok=True)
    keys = sorted(plan, key=int)[shard[0]::shard[1]]
    todo = [k for k in keys if not (REL / f"{int(k):05d}.json").exists()]
    rr = K.Renderer()
    try:
        for n, key in enumerate(sorted(todo, key=lambda k: (plan[k]["amp"], plan[k]["class"], int(k)))):
            p = plan[key]
            i = int(key)
            if n % 5 == 0 and not K2.disk_ok():                          # about every 50 renders
                raise SystemExit("free disk below the 31 GB guard")
            r = json.loads((B.OUT / "renders" / f"{i:05d}.json").read_text())
            label_x = D.st(r["settings"])
            ps = {k: D.st(v) for k, v in p["probes"].items()}
            first, of = probe_renders(label_x, ps)
            check_cap("relabel", spent(REL), len(first) + int(p["repeat"]))
            sel, _ = D._S(menu, p["amp"], p["class"])
            di = D.measured_di(p["window"])
            ref = A.load_render(i)
            dist = {}
            for k, name in first.items():
                dist[k] = D.judge_trimmed(ref, rr.render(di, sel, ps[name]), di)
                guard.tick()
            lk = K.key(label_x)
            d = {name: ({"A": 0.0, "B": 0.0} if k == lk else dist[k]) for name, k in of.items()}
            rep = None
            if p["repeat"]:
                rep = D.judge_trimmed(ref, rr.render(di, sel, label_x), di)
                guard.tick()
            K._atomic(REL / f"{i:05d}.json", {"d": d, "repeat": rep, "renders": len(first) + int(p["repeat"])})
            print(i, len(first), flush=True)
    finally:
        rr.close()


def _parity_examples(ex, n=3):
    """Bank examples whose features are deterministic without the separator or AAC, and without a
    second guitar: the stored bank features were built while renders were still landing, so a
    second-guitar draw depended on which renders existed then (found 2026-10-16, amendment 3)."""
    return [e for e in ex if not e["separated"] and not e["aac"] and not e["second_guitar"]][:n]


def step_features():
    """The new examples' features (one torch process, 2 threads, not beside render processes),
    after the disk check and the 3-example parity check against the bank's stored features."""
    import tempfile

    import numpy as np

    from learn import song_aug as A

    require_disk()
    D.set_threads()
    lv = json.loads((B.OUT / "levels.json").read_text())
    levels = list(lv["guitar_to_backing_db"].values())
    eval_mix = lv["summary"]["eval_mix_lufs_median"]
    bank = json.loads((B.OUT / "examples.json").read_text())
    by_fold = {}
    for e in bank:
        by_fold.setdefault(e["fold"], []).append(e["i"])
    exists = {e["i"] for e in bank if (B.OUT / "renders" / f"{e['i']:05d}.flac").exists()}
    others = {f: [j for j in v if j in exists] for f, v in by_fold.items()}
    with tempfile.TemporaryDirectory() as tmp:
        for e in _parity_examples(bank):                            # set-up check: parity
            stored = np.load(B.OUT / "features" / f"{e['i']:05d}.npz")
            ft = example_features(e, A.load_render(e["i"]), others[e["fold"]], A.load_render, levels, eval_mix,
                                  tmp, None)
            for h in "AB":
                same = np.allclose(ft[h][0].astype(np.float32), stored[f"feat{h}"].astype(np.float32), atol=0.1)
                if not same or not np.allclose(ft[h][1], stored[f"lufs{h}"], atol=1e-3):
                    raise SystemExit(f"feature parity fails on bank example {e['i']} half {h}: stop and amend")
        print("feature parity ok on", [e["i"] for e in _parity_examples(bank)])
        new = json.loads((BANK2 / "examples.json").read_text())
        out = BANK2 / "features"
        out.mkdir(parents=True, exist_ok=True)
        sep = None
        for e in new:
            f = out / f"{e['i']:05d}.npz"
            r = BANK2 / "renders" / f"{e['i']:05d}.json"
            if f.exists() or not r.exists():
                continue
            peak = json.loads(r.read_text())["peak"]
            g = D.load_flac(BANK2 / "renders" / f"{e['i']:05d}.flac", peak)
            if e["separated"] and sep is None:
                from learn.separate import GuitarSeparator
                sep = GuitarSeparator()
            ft = example_features(e, g, others.get(e["fold"], []), A.load_render, levels, eval_mix, tmp, sep)
            np.savez(f, featA=ft["A"][0], lufsA=ft["A"][1], featB=ft["B"][0], lufsB=ft["B"][1])
            if e["i"] % 100 == 0:
                print(e["i"], flush=True)


def step_sets():
    """Members and weights per relabelled example-half (sets/<i>.json), the repeat check (read
    first: a failure stops), and the relabel map."""
    menu = D._menu()
    plan = json.loads(PLAN.read_text())["examples"]
    reps, sets = [], []
    missing = [k for k in plan if not (REL / f"{int(k):05d}.json").exists()]
    if missing:
        raise SystemExit(f"{len(missing)} relabel examples not probed yet")
    for key in sorted(plan, key=int):
        if plan[key]["repeat"]:
            reps.append((int(key), json.loads((REL / f"{int(key):05d}.json").read_text())["repeat"]))
    rc = repeat_check(reps)
    if not rc["ok"]:
        raise SystemExit(f"relabel repeat check fails: {rc}: stop and amend")
    SETS.mkdir(parents=True, exist_ok=True)
    counts = {"point_halves": 0, "set_halves": 0}
    for key in sorted(plan, key=int):
        p, i = plan[key], int(key)
        rel = json.loads((REL / f"{i:05d}.json").read_text())
        r = json.loads((B.OUT / "renders" / f"{i:05d}.json").read_text())
        _, S = D._S(menu, p["amp"], p["class"])
        dims = K.space(p["amp"], S)
        labels = {n: label_of(dims, D.st(x)) for n, x in p["probes"].items()}
        s = {h: half_set({n: v[h] for n, v in rel["d"].items()}, labels, r["label"]) for h in "AB"}
        for h in "AB":
            counts["point_halves" if s[h]["point"] else "set_halves"] += 1
        s["i"] = i
        K._atomic(SETS / f"{i:05d}.json", s)
        sets.append(s)
    K._atomic(OUT / "relabel-report.json", {"repeat_check": rc, "counts": counts, "map": relabel_map(sets)})
    print(json.dumps({"repeat_check_ok": rc["ok"], **counts}))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("weights", "draw", "render-new", "probe", "features", "sets"))
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    i, n = map(int, a.shard.split("/"))
    {"weights": step_weights, "draw": step_draw, "render-new": lambda: step_render_new((i, n)),
     "probe": lambda: step_probe((i, n)), "features": step_features, "sets": step_sets}[a.step]()


if __name__ == "__main__":
    main()
