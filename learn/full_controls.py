"""Every control on the real rows, C1a (`docs/full-controls-plan.md`, Amendment 2 of `docs/every-control-plan.md`; ledger
`pipeline-fix` `phase_c1a`). The EQ, both drive pedals, the compressor and the gate searched on top of each record's stored
label, on N12's 31 units and BKS's 40 stage-1 units. Development only, the true DI, no model, no training.

    .venv/bin/python -m learn.full_controls c1a-draw                 # the records and the calibration subset (zero renders)
    .venv/bin/python -m learn.full_controls c1a-search --shard 0/3   # the searches (renders; at most 3 shards at once)
    .venv/bin/python -m learn.full_controls c1a-report               # the rows (zero renders)

The pure parts (the BKS amp choice, the subset, the start, the space, the canonical form, the ablations, the checkpoints,
C2's budget and the report's rows) are unit-tested; the search renders and is not.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time

PHASE = "phase_c1a"
PHASE_A1 = "phase_c1a_a1"            # Amendment 1: a start miss tries the gate as in the label, else the record is refused
SEED = 20261123                      # the search's
SUBSET_SEED = 20261124               # the calibration subset's draw
BUDGET, SUBSET_BUDGET, SUBSET_PER_SET = 100, 300, 6
CHECKPOINTS = (50, 100, 150, 200, 300)
START_TOL = 0.005                    # |log(first evaluation / stored best.judge[search])|
C2_SHARE = 0.9                       # C2's budget: the first checkpoint reaching this share of the 300 gain
GAIN_DB = (-20.0, 12.0)              # FT2's input-gain head range (`knob_ceiling.space`)
PEDAL_MODULES = ("drive1", "drive2", "compressor")
PEDAL_SWITCHES = (("drive1", "drive1Active"), ("drive2", "drive2Active"), ("compressor", "compressorActive"))
GATE_KEYS = (("parameters", "gateActive"), ("parameters", "gateThreshold"))
GATE_ON_DB = "-80"                   # the factory threshold: the median of the factory menu's presets with the gate on
                                     # (102 of 107, read 2026-11-09 at zero renders, `factory_gate_median`); -60 if none.
                                     # C1a's start turns an off gate on here (`gate_on`, as `every_control.group_plan`
                                     # does), and an off gate's canonical threshold stays here
GATE_FALLBACK_DB = -60.0
FACTORY = "/Library/Audio/Presets/Neural DSP/Morgan Amps Suite"
ABLATIONS = ("pedals_reset", "eq_reset", "pedals_eq_reset", "gate_reset")
SETS = ("n12", "bks")
OUT_DIRS = {"n12": ("captures2", "search-c1a"), "bks": ("real", "search-c1a")}


def fname(key):
    return key.replace("/", "__")


# --- records (zero renders) -----------------------------------------------------------------------------------------

def bks_amp_choice(recs):
    """One BKS unit's stage-1 records ({amp: record}) -> the amp whose stored label has the lowest best.judge[search]
    (labels that fell back are left out), or None."""
    ok = {a: r for a, r in recs.items() if r.get("label") is not None
          and math.isfinite(float(r["best"]["judge"][r["search"]]))}
    if not ok:
        return None
    return min(sorted(ok), key=lambda a: float(ok[a]["best"]["judge"][ok[a]["search"]]))


def draw_subset(records, seed=SUBSET_SEED, per_set=SUBSET_PER_SET):
    """The calibration subset: `per_set` records of each set, seeded, from records sorted by key. -> set of keys."""
    rng = random.Random(seed)
    out = set()
    for s in SETS:
        keys = sorted(r["key"] for r in records if r["set"] == s)
        out |= set(rng.sample(keys, min(per_set, len(keys))))
    return out


def shard_order(records):
    """The searches' order: the subset first (it costs three times as much), then the rest, each by key, so a round
    robin over shards spreads the subset evenly."""
    return sorted(records, key=lambda r: (not r["subset"], r["key"]))


# --- the space, the start and the canonical form ----------------------------------------------------------------------

def gate_dims():
    from learn.knob_ceiling import Dim

    return [Dim("parameters", "gateActive", "switch", values=("false", "true")),
            Dim("parameters", "gateThreshold", "cont", -96.0, 0.0)]


def c1a_space(amp, start):
    """`knob_ceiling2.stage1_space` with input gain at FT2's head range, plus the gate; the mic types are left out
    (held at the label's)."""
    from learn import knob_ceiling2 as K2
    from learn.knob_ceiling import Dim

    dims = [d for d in K2.stage1_space(amp, start) if not (d.module == "parameters" and d.key == "inputGain")]
    if any(d.kind == "cat" for d in dims):
        raise SystemExit("C1a's space holds the mic types: no categorical dim may be searched")
    return [Dim("parameters", "inputGain", "cont", *GAIN_DB)] + dims + gate_dims()


def factory_gate_median(root=FACTORY):
    """The median threshold (dB) of the factory menu presets (`Neural DSP` and `Artists`) with the gate on, read from the
    files at zero renders; GATE_FALLBACK_DB if none has it on. -> (median, presets, gate on)."""
    import pathlib

    from format.parser import parse_file
    from format.structured import build

    files = sorted(p for d in ("Neural DSP", "Artists") for p in (pathlib.Path(root) / d).rglob("*.xml"))
    thr = []
    for f in files:
        by = build(parse_file(f)).by_path
        if str(by[("parameters", "gateActive")].value).lower() == "true":
            thr.append(float(by[("parameters", "gateThreshold")].value))
    return (statistics.median(thr) if thr else GATE_FALLBACK_DB), len(files), len(thr)


def gate_on(x):
    """The gate on at GATE_ON_DB when it is off, as `every_control.group_plan("gate")` does; a gate already on keeps its
    stored threshold. The start check (the first evaluation against the stored label) verifies that this is inert."""
    y = dict(x)
    if str(y.get(GATE_KEYS[0], "false")).lower() not in ("true", "1"):
        y[GATE_KEYS[0]] = "true"
        y[GATE_KEYS[1]] = GATE_ON_DB
    return y


def canon_gate(x):
    """An off gate's threshold to GATE_ON_DB (it can't sound while off)."""
    y = dict(x)
    if str(y.get(GATE_KEYS[0], "false")).lower() not in ("true", "1"):
        y[GATE_KEYS[1]] = GATE_ON_DB
    return y


def make_canon(amp):
    """canon_pedals, then the gate's canonical form (`canon_gate`). `amp` is kept for the callers' symmetry."""
    from learn import knob_ceiling2 as K2

    def canon(x):
        return canon_gate(K2.canon_pedals(x))
    return canon


def c1a_start(label, amp, gate=True):
    """The stored label (`knob_ceiling2.stage1_start`: inert keys only) with the gate on at the factory threshold
    (`gate_on`), in canonical form; with gate=False the gate stays as in the label (Amendment 1's second start). label:
    {"module/key": value} -> {(module, key): value}."""
    from learn import knob_ceiling2 as K2
    from learn import local_objective as LO

    x = K2.stage1_start(LO.tdict(label), amp)
    return make_canon(amp)(gate_on(x) if gate else x)


class StartMiss(Exception):
    """The search's first evaluation is not the stored label's within START_TOL."""

    def __init__(self, value, sha):
        super().__init__(value)
        self.value, self.sha = value, sha


def within(value, ref):
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0 and abs(math.log(value / ref)) <= START_TOL


def start_plan(first_ok, second_ok):
    """Amendment 1's rule on one record's start check. first_ok: the gate-on start matched the stored label; second_ok:
    the gate-as-in-the-label start did (None when not rendered). -> "on", "off_after_miss" or "refused"."""
    if first_ok:
        return "on"
    return "off_after_miss" if second_ok else "refused"


def audible_change(start, label, amp, declared=()):
    """Keys the start changes from the label that can sound in the start, less the `declared` ones (the gate turned on,
    which the start check verifies by render instead). Must be empty."""
    from learn import every_control as E
    from learn import local_objective as LO

    lab = LO.tdict(label)
    by = {c.path: c for c in E.table("morgan")}
    out = []
    for k, v in start.items():
        if lab.get(k) != v and k not in declared:
            c = by.get(k)
            if c is None or E.sounds(c, start, amp, True, by):
                out.append("/".join(k))
    return sorted(out)


# --- the ablations ----------------------------------------------------------------------------------------------------

def reset(best, start, keys):
    y = dict(best)
    for k in keys:
        if k in start:
            y[k] = start[k]
    return y


def ablation_settings(best, start, amp):
    """{name: setting}: the 100-budget best with the pedals, the amp EQ, both, or the gate back to the start's, in
    canonical form."""
    canon = make_canon(amp)
    pedals = [k for k in start if k[0] in PEDAL_MODULES]
    eq = [k for k in start if k[0] == f"{amp}EQ"]
    return {"pedals_reset": canon(reset(best, start, pedals)), "eq_reset": canon(reset(best, start, eq)),
            "pedals_eq_reset": canon(reset(best, start, pedals + eq)),
            "gate_reset": canon(reset(best, start, list(GATE_KEYS)))}


# --- checkpoints and C2's budget ----------------------------------------------------------------------------------------

def incumbent_at(values, n):
    """The index of the best (lowest, finite, earliest on ties) of the first n values, or None."""
    best = None
    for i, v in enumerate(values[:n]):
        if isinstance(v, (int, float)) and math.isfinite(v) and (best is None or v < values[best]):
            best = i
    return best


def checkpoints(values, budget):
    return {n: incumbent_at(values, n) for n in CHECKPOINTS if n <= budget}


def c2_budget(curves, share=C2_SHARE):
    """curves: [{checkpoint: search-half gain ln(d_start / d_incumbent)}], each run to 300. The first checkpoint whose
    median of gain(n) / gain(300) reaches `share`; records with no gain at 300 are left out. -> (checkpoint or None,
    {checkpoint: median ratio})."""
    use = [c for c in curves if c.get(CHECKPOINTS[-1], 0.0) > 0]
    if not use:
        return None, {}
    med = {n: statistics.median(c[n] / c[CHECKPOINTS[-1]] for c in use) for n in CHECKPOINTS}
    return next((n for n in CHECKPOINTS if med[n] >= share), None), med


# --- the rows ------------------------------------------------------------------------------------------------------------

def jackknife_mean(pairs):
    """pairs: [(cluster, value)]. The record-weighted mean, its delete-one-cluster jackknife SE and df = clusters − 1."""
    by = {}
    for c, v in pairs:
        by.setdefault(c, []).append(v)
    cl = sorted(by)
    n = len(pairs)
    mean = sum(v for _, v in pairs) / n if n else None
    if len(cl) < 2:
        return {"mean": mean, "records": n, "clusters": len(cl), "se": None, "df": None}
    th = []
    for k in cl:
        rest = [v for c, v in pairs if c != k]
        th.append(sum(rest) / len(rest))
    m = sum(th) / len(th)
    se = math.sqrt((len(cl) - 1) / len(cl) * sum((x - m) ** 2 for x in th))
    return {"mean": mean, "records": n, "clusters": len(cl), "se": se, "df": len(cl) - 1}


def with_interval(row, tq):
    """Adds the 90% t interval; tq(df) is the 0.95 quantile."""
    if row["se"] is None:
        return dict(row, lo=None, hi=None)
    q = tq(row["df"])
    return dict(row, lo=row["mean"] - q * row["se"], hi=row["mean"] + q * row["se"])


def _pos(v):
    """A finite positive judge value as float, else None."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v > 0 else None


def record_values(r):
    """One searched record's held-half rows (ln ratios) and counts, or None if it has no fresh best."""
    h = r["held"]
    fb = (r.get("fresh") or {}).get("best")
    if not fb or r.get("label") is None:
        return None
    lab_h, new_h, s_h = (_pos(r["source_best_judge"][h]), _pos(fb["judge"][h]), _pos(r["s_judge"][h]))
    if None in (lab_h, new_h, s_h):
        return None
    abl = {}
    for a in ABLATIONS:
        v = _pos(((r["fresh"].get("ablations") or {}).get(a) or {}).get("judge", {}).get(h))
        if v is not None:
            abl[a] = math.log(v / new_h)
    out = {"primary": math.log(new_h / lab_h), "label_vs_S": math.log(lab_h / s_h), "ablations": abl}
    b3 = _pos(((r["fresh"].get("best_300") or {}).get("judge") or {}).get(h))
    if r.get("subset") and b3 is not None:
        out["b300_vs_best"], out["b300_vs_label"] = math.log(b3 / new_h), math.log(b3 / lab_h)
    out["changed"] = r.get("changed", {})
    return out


def report_rows(recs, tq, clus):
    """recs: the searched records of one set (each with `cluster`, `cls`, `unit`). tq(df): the t quantile; clus: the
    band-weighted reading (`pipeline_fix.clustered`). -> rows, all and by class, each record-weighted (jackknife t)
    with the band-weighted reading and its per-cluster breakdown beside."""
    vals = [(r, record_values(r)) for r in recs]
    vals = [(r, v) for r, v in vals if v is not None]

    def row(sub, get):
        pts = [(r["cluster"], r["unit"], get(v)) for r, v in sub if get(v) is not None]
        if not pts:
            return None
        return dict(with_interval(jackknife_mean([(c, x) for c, _, x in pts]), tq), band_weighted=clus(pts))

    def rows(sub):
        out = {"primary": row(sub, lambda v: v["primary"]), "label_vs_S": row(sub, lambda v: v["label_vs_S"]),
               "ablations": {a: row(sub, lambda v, a=a: v["ablations"].get(a)) for a in ABLATIONS},
               "subset_b300_vs_best": row(sub, lambda v: v.get("b300_vs_best")),
               "subset_b300_vs_label": row(sub, lambda v: v.get("b300_vs_label"))}
        cnt = {}
        for _, v in sub:
            for k, c in v["changed"].items():
                cnt[k] = cnt.get(k, 0) + int(bool(c))
        out["changed_counts"] = cnt
        return out

    res = {"all": rows(vals) if vals else None}
    for cl in ("clean", "crunch"):
        sub = [(r, v) for r, v in vals if r["cls"] == cl]
        res[cl] = rows(sub) if sub else None
    res["records"] = len(vals)
    return res


def split_refused(recs):
    """(searched records, [{unit, the refused start's values}]): Amendment 1's refused records carry no search."""
    return [r for r in recs if "refused" not in r], [{"unit": r["unit"], **r["refused"]} for r in recs if "refused" in r]


def start_counts(recs):
    """Amendment 1's start kinds over a set's written records: on (the gate on at the factory threshold; records
    written before the amendment carry no flag and are this kind), off_after_miss, refused."""
    out = {"on": 0, "off_after_miss": 0, "refused": 0}
    for r in recs:
        out[r.get("start_gate", "on")] += 1
    return out


def subset_curves(recs):
    """The subset's checkpoint curves, from the stored checkpoint judges: per record {half: {checkpoint: gain}}, the gain
    ln(d_start / d_incumbent) on the search half and on the held half (the start's both halves are its first
    evaluation's)."""
    out = []
    for r in recs:
        if not r.get("subset"):
            continue
        s0 = r["trials"][0]["judge"]
        cur = {}
        for half, name in ((r["search"], "search"), (r["held"], "held")):
            v0 = _pos(s0[half])
            cur[name] = {int(c): math.log(v0 / _pos(cp["judge"][half])) for c, cp in r["checkpoints"].items()
                         if v0 is not None and _pos(cp["judge"][half]) is not None}
        out.append(cur)
    return out


def amp_choice_value(recs, chosen):
    """One BKS unit: the chosen amp's held half against an amp chosen blind, log(held of the chosen) less the mean log
    held over the amps with a label (every-control stage 0b's reading). recs: {amp: stored stage-1 record}."""
    logs = {}
    for a, r in recs.items():
        v = _pos(r["best"]["judge"].get(r["held"])) if r.get("label") is not None else None
        if v is not None:
            logs[a] = math.log(v)
    if chosen not in logs:
        return None
    return logs[chosen] - sum(logs.values()) / len(logs)


def changed(best, start, amp, S):
    """What the best changed: each pedal's switch from the start (the label), the amp EQ from S's curve, the gate."""
    from learn import knob_ceiling2 as K2

    out = {f"{m}": best.get((m, k)) != start.get((m, k)) for m, k in PEDAL_SWITCHES}
    for m, k in PEDAL_SWITCHES:                         # an on pedal's knobs moved from the start's
        on = str(best.get((m, k), "false")).lower() in ("true", "1")
        knobs = [(m, kk) for kk in K2.PEDALS[m][1]] + ([("compressor", "compressorRelease")] if m == "compressor" else [])
        out[f"{m}_knobs"] = on and any(best.get(q) != start.get(q) for q in knobs)
    eq = [k for k in best if k[0] == f"{amp}EQ" and k[1] != f"{amp}EQActive"]
    out["eq_moved_from_S"] = any(best.get(k) != S.get(k) for k in eq)
    out["gate"] = best.get(GATE_KEYS[0]) != start.get(GATE_KEYS[0])
    return out


# --- commands ----------------------------------------------------------------------------------------------------------

def c1a_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "c1a"


def load_sources():
    """-> [record], each {set, key, unit, amp, cls, cluster, source (path), prt (the harness's unit dict), real_out}."""
    from learn import cc_build as CB
    from learn import pipeline_fix as P
    from learn import score_ear as SE

    real_out = set(P.h4_exclusions()["real_out"])
    out = []
    units, _, _ = SE.wide_units()
    for u in units:
        key = f"{u['unit']}|{u['amp']}"
        path = P.out_dir() / "captures2" / P.SEARCH_DIR / f"{fname(key)}.json"
        out.append({"set": "n12", "key": key, "unit": u["unit"], "amp": u["amp"], "cls": u["cls"],
                    "cluster": u["player"], "source": str(path), "prt": u, "real_out": u["unit"] in real_out})
    e = P.require("phase_5b2")
    _, kept, _, sp, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    parts = P.stage_units(kept, sp, CB.cc_inventory(), 1)
    for prt in parts:
        recs = {}
        for a in P.AMPS3:
            p = P.out_dir() / P.REAL_DIR / P.SEARCH_DIR / f"{fname(P.real_key(prt, a))}.json"
            if p.exists():
                recs[a] = json.loads(p.read_text())
        a = bks_amp_choice(recs)
        if a is None:
            continue
        key = P.real_key(prt, a)
        out.append({"set": "bks", "key": key, "unit": prt["unit"], "amp": a, "cls": prt["cls"], "cluster": prt["di"],
                    "source": str(P.out_dir() / P.REAL_DIR / P.SEARCH_DIR / f"{fname(key)}.json"), "prt": prt,
                    "real_out": prt["unit"] in real_out,
                    "amp_choice": {b: float(r["best"]["judge"][r["search"]]) for b, r in recs.items()
                                   if r.get("label") is not None}})
    return out


def cmd_draw(_args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    path = c1a_dir() / "records.json"
    if path.exists():
        raise SystemExit(f"{path} exists: the records are drawn once")
    recs = load_sources()
    sub = draw_subset(recs)
    med, n_files, n_on = factory_gate_median()
    want = float(GATE_ON_DB) if n_on else GATE_FALLBACK_DB
    if med != want:
        raise SystemExit(f"the factory gate median is {med} dB ({n_on} of {n_files} on), not the declared {GATE_ON_DB}")
    for r in recs:
        r["subset"] = r["key"] in sub
        r["budget"] = SUBSET_BUDGET if r["subset"] else BUDGET
        r["measurement_only"] = r["set"] == "n12"
    P.save(path, {"phase": PHASE, "seed": SEED, "subset_seed": SUBSET_SEED, "records": recs,
                  "gate_factory": {"median_db": med, "presets": n_files, "gate_on": n_on, "used": GATE_ON_DB},
                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    n = {s: sum(1 for r in recs if r["set"] == s) for s in SETS}
    print("C1A DRAW", n, "subset", len(sub), "renders at most",
          sum(1 + r["budget"] + 10 + (2 if r["subset"] else 0) for r in recs), flush=True)


def cmd_search(args):
    import numpy as np

    from learn import arm_a_levers as L
    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(PHASE)
    P.require(PHASE_A1)
    plan = json.loads((c1a_dir() / "records.json").read_text())
    k, n = args.shard
    mine = [r for j, r in enumerate(shard_order(plan["records"])) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    ms = L.menu_S()
    LO._wait_cap()
    renders = 0
    counts = {"on": 0, "off_after_miss": 0, "refused": 0}

    def sorted_x(x):
        return LO.tdict(LO.sdict(x))

    def fresh(di32, sel, x):
        xs = sorted_x(x)
        y = AM.fresh_render(CB.new_renderer, di32, sel, xs, xs)
        return np.asarray(y, np.float64)[trim[0]:trim[1]]

    for rec in mine:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        root, sub = OUT_DIRS[rec["set"]]
        out = P.out_dir() / root / sub / f"{fname(rec['key'])}.json"
        if out.exists():
            continue
        src = json.loads(open(rec["source"]).read())
        amp, prt = rec["amp"], rec["prt"]
        sel, S = ms[amp][rec["cls"]]
        if src["select"] != sel or src.get("label") is None or src["unit"] != rec["unit"] or src["amp"] != amp:
            raise SystemExit(f"{rec['key']}: the source record's unit, amp, select or label does not fit")
        search, held, lag = src["search"], src["held"], src["lag"]
        start = c1a_start(src["best"]["settings"], amp)
        bad = audible_change(start, src["best"]["settings"], amp, declared=GATE_KEYS)
        if bad:
            raise SystemExit(f"{rec['key']}: the start changes what sounds: {bad}")
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        ref_v, ref_sha = float(src["best"]["judge"][search]), src["best"].get("render_sha256")

        def run(start):
            """One search from `start` in its own renderer process, primed with the start. -> (renders, values, trials,
            evals, start record, names); raises StartMiss if its first evaluation is not the stored label's."""
            dims = c1a_space(amp, start)
            canon = make_canon(amp)
            names = [d.name for d in dims]
            values, trials, evals, start_rec = [], [], [], {}
            used = [1]
            rr = CB.new_renderer()
            try:
                rr.render(di32, sel, sorted_x(start))   # the discarded priming render, with the start

                def f(x):
                    y = np.asarray(rr.render(di32, sel, sorted_x(x)), np.float64)[trim[0]:trim[1]]
                    used[0] += 1
                    j = K.judge(ref, y, di, lag)
                    if not values:
                        start_rec.update(value=j[search], sha=AM.audio_sha(y), ref_value=ref_v, ref_sha=ref_sha,
                                         bit_identical=AM.audio_sha(y) == ref_sha)
                        if not within(j[search], ref_v):
                            raise StartMiss(j[search], AM.audio_sha(y))
                    evals.append({"judge": j, "peak_dbfs": A.peak_dbfs(y, trim_s=0.0), "render_sha256": AM.audio_sha(y),
                                  "x": dict(x)})
                    values.append(j[search])
                    trials.append({"x": {nm: x.get(tuple(nm.rsplit("/", 1))) for nm in names}, "judge": j})
                    return j[search]

                K.coord_search(dims, start, f, rec["budget"], SEED, cats="levels", canon=canon)
            except StartMiss as miss:
                miss.renders = used[0]
                raise
            finally:
                rr.close()
            return used[0], values, trials, evals, start_rec, names

        start_gate, first_miss = "on", None
        try:
            used, values, trials, evals, start_rec, names = run(start)
            renders += used
        except StartMiss as miss:
            renders += miss.renders
            first_miss = {"value": miss.value, "sha": miss.sha, "ref_value": ref_v}
            start_off = c1a_start(src["best"]["settings"], amp, gate=False)
            y = fresh(di32, sel, start_off)             # the second start: the gate as in the label
            renders += 2
            v_off = K.judge(ref, y, di, lag)[search]
            start_gate = start_plan(False, within(v_off, ref_v))
            first_miss["gate_off_value"] = v_off
            if start_gate == "refused":
                P.save(out, {"plan": "docs/full-controls-plan.md", "ledger": f"{P.LEDGER_ID} {PHASE_A1}",
                             "set": rec["set"], "unit": rec["unit"], "cls": rec["cls"], "amp": amp,
                             "cluster": rec["cluster"], "real_out": rec["real_out"],
                             "measurement_only": rec["set"] == "n12", "subset": rec["subset"], "label": None,
                             "start_gate": "refused", "refused": first_miss,
                             "time": time.strftime("%Y-%m-%d %H:%M:%S")})
                counts["refused"] += 1
                print(f"{rec['key'][-70:]}: refused (start {miss.value} and gate off {v_off} against {ref_v}); "
                      f"renders so far {renders}", flush=True)
                continue
            start = start_off
            used, values, trials, evals, start_rec, names = run(start)
            renders += used
            counts["off_after_miss"] += 1
        if start_gate == "on":
            counts["on"] += 1
        cps = checkpoints(values, rec["budget"])
        by_order = evals                                # evaluation order
        best100 = by_order[cps[BUDGET]] if cps.get(BUDGET) is not None else None
        if best100 is None:
            raise SystemExit(f"{rec['key']}: no finite evaluation")
        bx = best100["x"]
        fb = A.fallback_reason(best100["peak_dbfs"], best100["judge"][search])
        fr = {"best": None, "ablations": {}}
        y = fresh(di32, sel, bx)
        renders += 2
        fr["best"] = {"judge": K.judge(ref, y, di, lag), "render_sha256": AM.audio_sha(y),
                      "peak_dbfs": A.peak_dbfs(y, trim_s=0.0)}
        for name, x in ablation_settings(bx, start, amp).items():
            if K.key(x) == K.key(bx):                   # nothing to reset: the best's own fresh render
                fr["ablations"][name] = dict(fr["best"], same_as_best=True)
                continue
            y = fresh(di32, sel, x)
            renders += 2
            fr["ablations"][name] = {"judge": K.judge(ref, y, di, lag), "render_sha256": AM.audio_sha(y),
                                     "same_as_best": False}
        extra = {}
        if rec["budget"] > BUDGET:
            b300 = by_order[cps[SUBSET_BUDGET]] if cps.get(SUBSET_BUDGET) is not None else best100
            if K.key(b300["x"]) == K.key(bx):
                fr["best_300"] = dict(fr["best"], same_as_best=True)
            else:
                y = fresh(di32, sel, b300["x"])
                renders += 2
                fr["best_300"] = {"judge": K.judge(ref, y, di, lag), "render_sha256": AM.audio_sha(y),
                                  "same_as_best": False}
            fb3 = A.fallback_reason(b300["peak_dbfs"], b300["judge"][search])
            extra = {"label_300": None if fb3 else LO.sdict(b300["x"]), "fallback_300": fb3}
        P.save(out, {"plan": "docs/full-controls-plan.md", "ledger": f"{P.LEDGER_ID} {PHASE}", "set": rec["set"],
                     "unit": rec["unit"], "rig": src.get("rig"), "di": src.get("di"), "item": src.get("item"),
                     "fold": src.get("fold"), "cls": rec["cls"], "amp": amp, "select": sel, "search": search,
                     "held": held, "lag": lag, "item_lag": src.get("item_lag"), "cluster": rec["cluster"],
                     "real_out": rec["real_out"], "measurement_only": rec["set"] == "n12", "subset": rec["subset"],
                     "budget": rec["budget"], "seed": SEED, "gate_on_db": GATE_ON_DB,
                     "source": rec["source"], "source_best_judge": src["best"]["judge"], "s_judge": src["s_judge"],
                     "start": start_rec, "start_gate": start_gate, "first_start_miss": first_miss,
                     "start_settings": LO.sdict(start), "searched_keys": names, "curve": values, "evaluations": len(values),
                     "trials": trials,
                     "checkpoints": {str(c): {"evaluations": c, "index": i, "judge": by_order[i]["judge"]}
                                     for c, i in cps.items() if i is not None},
                     "best": {"judge": best100["judge"], "peak_dbfs": best100["peak_dbfs"],
                              "render_sha256": best100["render_sha256"], "settings": LO.sdict(bx), "fallback": fb},
                     "fresh": fr, "changed": changed(bx, start, amp, S),
                     "label": None if fb else LO.sdict(bx), **extra,
                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{rec['key'][-70:]}: {len(values)} evaluations; renders so far {renders}", flush=True)
    print(f"C1A-SEARCH DONE {k}/{n}: {renders} renders; starts {counts}", flush=True)


def cmd_report(_args):
    from scipy import stats

    from learn import pipeline_fix as P

    P.require(PHASE)
    tq = lambda df: float(stats.t.ppf(0.95, df))          # noqa: E731
    out = {"phase": PHASE, "gate_on_db": GATE_ON_DB}
    for s in SETS:
        root, sub = OUT_DIRS[s]
        every = [json.loads(p.read_text()) for p in sorted((P.out_dir() / root / sub).glob("*.json"))]
        recs, refused = split_refused(every)                        # Amendment 1's refused starts are counted apart
        main = [r for r in recs if not r["real_out"]]
        cur = subset_curves(recs)
        out[s] = {"rows": report_rows(main, tq, P.clustered),
                  "real_out": report_rows([r for r in recs if r["real_out"]], tq, P.clustered),
                  "fallbacks": sum(1 for r in recs if r["label"] is None),
                  "start_bit_identical": sum(1 for r in recs if r["start"].get("bit_identical")),
                  "starts": start_counts(every),
                  "refused": refused,
                  "subset_curves": cur,
                  "subset_median_ratio": {h: c2_budget([c[h] for c in cur])[1] for h in ("search", "held")}}
    plan = json.loads((c1a_dir() / "records.json").read_text())
    pairs = []
    for r in plan["records"]:
        if r["set"] != "bks" or r["real_out"]:
            continue
        recs = {}
        for a in P.AMPS3:
            q = P.out_dir() / P.REAL_DIR / P.SEARCH_DIR / f"{fname(r['unit'] + '|' + a)}.json"
            if q.exists():
                recs[a] = json.loads(q.read_text())
        v = amp_choice_value(recs, r["amp"])
        if v is not None:
            pairs.append((r["cluster"], r["unit"], v))
    out["bks"]["amp_choice_chosen_search_read_held"] = (
        dict(with_interval(jackknife_mean([(c, x) for c, _, x in pairs]), tq), band_weighted=P.clustered(pairs))
        if pairs else None)
    allc = [c["search"] for c in out["n12"]["subset_curves"] + out["bks"]["subset_curves"]]
    out["c2_budget"], out["c2_median_ratio"] = c2_budget(allc)
    P.save(c1a_dir() / "report.json", out)
    print(json.dumps({s: (out[s]["rows"]["all"] or {}).get("primary") for s in SETS}, indent=1, default=str))
    print("C2 budget", out["c2_budget"], out["c2_median_ratio"])


def shard(s):
    a, b = s.split("/")
    return int(a), int(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("c1a-draw").set_defaults(fn=cmd_draw)
    s = sub.add_parser("c1a-search")
    s.add_argument("--shard", type=shard, default=(0, 1))
    s.set_defaults(fn=cmd_search)
    sub.add_parser("c1a-report").set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
