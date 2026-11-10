"""Every control on FT2's remaining real training rows, C2 (`docs/full-controls-plan.md`, "C2 in detail"; ledger
`pipeline-fix` `phase_c2`). Labels, not a measurement: for each of FT2's real training rows (GOAT's `goat_labels`,
BKS's `real_labels(2)`) less C1a's 40, C1a's search at budget 200, then C1b's stages A and B; then C1a's 40 BKS
records continued to 200 (their first evaluations replayed at zero renders) with stages A and B. No effect stage: the
sources are dry, so the time effects, the spring and the doubler are recorded as off by source (`known_keys`). The
near-silent guard (F70). Development only, the true DI, no model, no training.

    .venv/bin/python -m learn.full_controls_c2 c2-draw                 # the records (zero renders)
    .venv/bin/python -m learn.full_controls_c2 c2-search --shard 0/3   # the searches (renders; at most 3 shards at once)
    .venv/bin/python -m learn.full_controls_c2 c2-report               # the rows (zero renders)

C1a's and C1b's own code is reused as it is (their pure parts, unchanged); C2's search chains them on one record. The
pure parts (the records and blocks, the order, the known keys, the masks, the replay, the guards, the rows) are
unit-tested; the search is tested on a stub renderer.
"""

from __future__ import annotations

import argparse
import json
import math
import time

from learn import full_controls as F
from learn import full_controls_c1b as C

PHASE = "phase_c2"
BUDGET = 200                         # step 1: C1a's calibration (the first checkpoint whose median reached 90% of 300)
BLOCKS = ("goat", "bks1", "bks2", "c1a")   # the order: GOAT, BKS stage 1, BKS stage 2, then C1a's 40 continued
OUT_DIRS = {"goat": ("goat", "search-c2"), "bks": ("real", "search-c2")}
PLAN = "docs/full-controls-plan.md"
STEP2_RENDERS = 1 + C.BUDGET_ROOMS + C.BUDGET_MICS_EQ      # priming, stage A, stage B (at most)
SILENT_DBFS = -60.0                  # J0's silence floor (`arm_a_mega53.SILENT_DBFS`: a peak under it is "silent")
UNUSABLE_DB = 3.0                    # a later stage's best may not peak below min(floor + this, the start's peak) (F70)
PEAK_TOL = 0.05                      # dB: fresh and in-process peaks of one setting differ by up to 0.0038 dB (C1a)
QUIET_DBFS = -50.0                   # a label peaking under this is flagged and counted, nothing more (J0 removes level)
MISS_GUARD = (5, 10)                 # a shard stops when this many of its first records are refused at the start
KNOWN_WHY = ("off by source: the sources are dry (GOAT's capture renders, BKS's reamps) and mono (no doubler); not "
             "searched and not a learned label")


def c2_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "c2"


def out_path(rec, step1=False):
    from learn import pipeline_fix as P

    root, sub = OUT_DIRS[rec["set"]]
    d = P.out_dir() / root / sub
    return (d / "step1" if step1 else d) / f"{F.fname(rec['key'])}.json"


# --- records (zero renders) ---------------------------------------------------------------------------------------------

def goat_records(labelled, units, real_out, source):
    """GOAT's labelled records (`pipeline_fix.goat_labels`) -> C2's records, one forced amp a unit as stored, clustered
    by item (`di`). labelled: [stored record]; units: {unit: unit dict}; real_out: set of units; source(key) -> path."""
    out = []
    for r in labelled:
        prt = units[r["unit"]]
        key = f"{r['unit']}|{r['amp']}"
        out.append({"set": "goat", "block": "goat", "key": key, "unit": r["unit"], "amp": r["amp"], "cls": r["cls"],
                    "cluster": prt["di"], "source": str(source(key)), "prt": prt, "real_out": r["unit"] in real_out})
    return out


def goat_left_out(stored, kept):
    """The stored GOAT records C2 leaves out, with why: those without a label (the lag rule, no lag, a fallback)."""
    out = []
    for r in stored:
        key = f"{r['unit']}|{r['amp']}"
        if key in kept:
            continue
        why = r.get("why") or ("fallback: " + str((r.get("best") or {}).get("fallback")) if r.get("label") is None
                               else "not among goat_labels")
        out.append({"key": key, "block": "goat", "why": why})
    return out


def bks_records(labelled, parts, c1a_keys, real_out, source):
    """BKS's FT2 rows (`pipeline_fix.real_labels(2)`: stages 1 and 2, labelled, lag rule applied) less C1a's 40, which
    come last as their own block. parts: {unit: unit dict}. -> records, blocks bks1 and bks2."""
    out = []
    for r in labelled:
        key = f"{r['unit']}|{r['amp']}"
        if key in c1a_keys:
            continue
        prt = parts[r["unit"]]
        out.append({"set": "bks", "block": f"bks{r['stage']}", "key": key, "unit": r["unit"], "amp": r["amp"],
                    "cls": r["cls"], "cluster": prt["di"], "source": str(source(key)), "prt": prt,
                    "real_out": r["unit"] in real_out})
    return out


def bks_left_out(stored, kept, lag_off):
    """The stored BKS records that are not FT2 rows, with why (the lag rule, or no label)."""
    out = []
    for r in stored:
        key = f"{r['unit']}|{r['amp']}"
        if key in kept:
            continue
        why = ("the lag rule (`lag_refused`): not an FT2 row" if r["unit"] in lag_off
               else "no label" if r.get("label") is None else f"stage {r.get('stage')}")
        out.append({"key": key, "block": f"bks{r.get('stage')}", "why": why})
    return out


def c1a_block(c1a_recs, outputs):
    """C1a's BKS records ({key: C1a output}), continued to 200: the last block. -> (records, left out with why)."""
    recs, left = [], []
    for r in c1a_recs:
        o = outputs.get(r["key"])
        why = ("no C1a output" if o is None else "refused in C1a" if "refused" in o
               else "C1a label fell back" if o.get("label") is None else None)
        if why:
            left.append({"key": r["key"], "block": "c1a", "why": why})
            continue
        recs.append({k: r[k] for k in ("set", "key", "unit", "amp", "cls", "cluster", "source", "prt", "real_out")}
                    | {"block": "c1a", "c1a_output": o["_path"], "c1a_budget": r["budget"]})
    return recs, left


def order(records):
    """The search order: by block (`BLOCKS`), then by key."""
    return sorted(records, key=lambda r: (BLOCKS.index(r["block"]), r["key"]))


def shard_records(records, k, n):
    """Shard k of n: a round robin over `order`, so every shard does GOAT first and C1a's 40 last."""
    return [r for j, r in enumerate(order(records)) if j % n == k]


def known_keys(amp):
    """The controls C2 records as off by source, not searched (`KNOWN_WHY`): the three time-effect switches, the
    doubler, and on the amps that have one the spring's switch under FT2's head name (`full_space.spring_dim`, e.g.
    `pr12Amp/springOn`), recorded for C3, which masks it and holds it at S (C3 in detail). -> {"module/key": "false"}."""
    from learn import full_space as FS

    out = {"/".join(k): "false" for k in C.DRY_KEYS}
    if amp in FS.SPRING:
        out[FS.spring_dim(amp).name] = "false"
    return out


def known_problems(label, amp):
    """The known-off controls a label (the plugin's settings, {"module/key": value}) has on: a switch on, or the
    spring's level above 0 for its pseudo-switch (must be empty; a key the label does not store is off)."""
    from learn import full_space as FS
    from learn import knob_ceiling2 as K2

    out = []
    for k in known_keys(amp):
        if amp in FS.SPRING and k == FS.spring_dim(amp).name:
            lvl = label.get("/".join(next(iter(K2.SPRING[amp][0]))))
            if lvl is not None and float(lvl) > 0:
                out.append(k)
        elif str(label.get(k, "false")).lower() in ("true", "1"):
            out.append(k)
    return sorted(out)


def start_problems(src, amp, sel):
    """Zero-render checks on one stored record before its search: the select, a finite stored best, the canonical start
    changing nothing that sounds but the declared gate, and a dry label. -> [problem] (empty when it may run)."""
    from learn import local_objective as LO

    out = []
    if src.get("label") is None:
        return ["no label"]
    if src.get("select") != sel:
        out.append("select")
    if F._pos((src.get("best") or {}).get("judge", {}).get(src.get("search"))) is None:
        out.append("stored best not finite")
    st = F.c1a_start(src["best"]["settings"], amp)
    bad = F.audible_change(st, src["best"]["settings"], amp, declared=F.GATE_KEYS)
    if bad:
        out.append(f"start changes what sounds: {bad}")
    wet = C.dry_start_problems(LO.tdict(src["label"]), amp)
    if wet:
        out.append(f"wet: {wet}")
    return out


def searched_keys(c1a_names, start_b, xa, amp, lists):
    """C3's mask for a record: step 1's space (C1a's) with stages A's and B's, and nothing else: no effect key, since
    none is searched (C1b's `searched_union` would add every effect knob, F55 again)."""
    return sorted(set(c1a_names) | {d.name for d in C.rooms_dims(start_b)} | {d.name for d in C.mics_eq_dims(xa, amp, lists)})


def renders_upper(recs):
    """Renders at most on the canonical path: step 1 (priming and the budget; for C1a's 40, priming, the start check
    and the evaluations past the stored ones), steps A and B, the fresh final."""
    n = 0
    for r in recs:
        if r["block"] == "c1a":
            stored = r["c1a_budget"]
            n += (0 if stored >= BUDGET else 2 + BUDGET - stored) + STEP2_RENDERS + 2
        else:
            n += 1 + BUDGET + STEP2_RENDERS + 2
    return n


# --- the guards and the replay ----------------------------------------------------------------------------------------

def peak_bound(start_peak, floor=SILENT_DBFS, margin=UNUSABLE_DB):
    """The lowest peak a later stage's best may have: min(floor + margin, the start's peak), so a search may not go
    quieter than -57 dBFS, or than its start when the start is already quieter (an unknown start: floor + margin)."""
    try:
        p = float(start_peak)
    except (TypeError, ValueError):
        p = math.nan
    return min(floor + margin, p) if math.isfinite(p) else floor + margin


def unusable(judge, peak, bound=None):
    """Why a render can't stand as a label, or None: non-finite on either half, or (with a `bound`, `peak_bound`) its
    peak below the bound or unknown. The start is read without a bound: only its halves (F70: a final at -59.9 dBFS
    from a -59.6 dBFS start, which J0 refused on the held half, falls back under the bound)."""
    for h in ("A", "B"):
        if F._pos((judge or {}).get(h)) is None:
            return f"non-finite on half {h}"
    if bound is None:
        return None
    try:
        p = float(peak)
    except (TypeError, ValueError):
        p = math.nan
    if not math.isfinite(p) or p < bound - PEAK_TOL:
        return f"peak {peak} dBFS below the bound {bound:.2f} dBFS (min of -57 and the start's peak, less {PEAK_TOL})"
    return None


def constrained_index(evals, search, bound, n=None, known_only=False):
    """A stage's best under the bound: the index of the lowest search-half value among its first n evaluations that
    pass (`unusable` None: finite on both halves and, where the peak is known, not below the bound). A replayed
    evaluation's peak is unknown: it passes on its halves alone, or is left out with known_only. Earliest on ties; None
    if none passes."""
    best = None
    for i, e in enumerate(evals[:n]):
        if e.get("replayed") and known_only:
            continue
        if unusable(e["judge"], e.get("peak_dbfs"), None if e.get("replayed") else bound):
            continue
        v = e["judge"][search]
        if best is None or v < evals[best]["judge"][search]:
            best = i
    return best


class PeakFail(Exception):
    """Step 2's first evaluation (step 1's best rendered in a fresh process) fails the peak bound: a replayed best."""


def quiet(peak, level=QUIET_DBFS):
    """The quiet flag: a label's render peaking under `level` (counted, nothing more)."""
    try:
        return float(peak) < level
    except (TypeError, ValueError):
        return False


def systematic_miss(outcomes, guard=MISS_GUARD):
    """outcomes: the shard's first records' outcomes in order ("refused", "ok" or None when not yet written). True once
    `guard[0]` of the first `guard[1]` are refused: the start misses are systematic and the shard stops."""
    k, n = guard
    return sum(1 for o in outcomes[:n] if o == "refused") >= k


class StartUnusable(Exception):
    """The start's own first evaluation can't stand as a label (`unusable`): the record is refused."""


class ReplayMismatch(Exception):
    """A replayed evaluation's setting is not the stored one: the continuation is not exact."""


def replaying(trials, names, search, render):
    """An objective for `coord_search`: the stored trials in evaluation order, each call's setting checked against the
    stored one on `names` (ReplayMismatch if not), then `render(x)` past them. `.i` counts the replayed calls."""
    state = {"i": 0}

    def f(x):
        if state["i"] < len(trials):
            t = trials[state["i"]]
            if {nm: x.get(tuple(nm.rsplit("/", 1))) for nm in names} != t["x"]:
                raise ReplayMismatch(state["i"])
            state["i"] += 1
            return t["judge"][search]
        return render(x)
    f.state = state
    return f


def replay_check(c1a_out, amp, budget=None):
    """C1a's stored search replayed at zero renders through `coord_search` up to its stored length (or `budget`): ->
    (problems, best index). Exact when problems is empty: every call's setting is the stored one and the replay used
    every stored evaluation it was given."""
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    start = LO.tdict(c1a_out["start_settings"])
    names, trials = c1a_out["searched_keys"], c1a_out["trials"]
    n = min(len(trials), budget or len(trials))
    dims = F.c1a_space(amp, start)
    if [d.name for d in dims] != names:
        return ["the space's names differ"], None

    def past(x):
        raise ReplayMismatch(n)
    f = replaying(trials[:n], names, c1a_out["search"], past)
    try:
        K.coord_search(dims, start, f, n, F.SEED, cats="levels", canon=F.make_canon(amp))
    except ReplayMismatch as m:
        return [f"evaluation {m.args[0]} differs"], None
    probs = [] if f.state["i"] == n else [f"used {f.state['i']} of {n}"]
    return probs, F.incumbent_at([t["judge"][c1a_out["search"]] for t in trials], n)


# --- the rows ------------------------------------------------------------------------------------------------------------

def record_values(r):
    """One record's held-half rows (ln ratios), or None: the primary, the label's fresh render against the start's first
    evaluation; beside it, against the stored label (its in-process best) and against S; and step 1's in-process held
    gain at the 100 and 200 checkpoints (zero renders)."""
    h = r["held"]
    fr = r.get("fresh") or {}
    fin = F._pos(((fr.get("label") or {}).get("judge") or {}).get(h))
    s1 = r.get("step1") or {}
    st = F._pos((((s1.get("trials") or [{}])[0]).get("judge") or {}).get(h))
    if fin is None or st is None or r.get("label") is None:
        return None
    out = {"primary": math.log(fin / st)}
    lab, s = F._pos((r.get("source_best_judge") or {}).get(h)), F._pos((r.get("s_judge") or {}).get(h))
    if lab is not None:
        out["vs_stored_label"] = math.log(fin / lab)
    if s is not None:
        out["vs_S"] = math.log(fin / s)
    miss = ((s1.get("continuation") or {}).get("start_check") or {}).get("ok") is False
    for c in ("100",) if miss else ("100", "200"):         # a continuation that did not render: no 200 checkpoint
        v = F._pos((((s1.get("checkpoints") or {}).get(c) or {}).get("judge") or {}).get(h))
        if v is not None:
            out[f"held_gain_at_{c}"] = math.log(v / st)
    return out


def counts(recs):
    """What the records' finals changed, and the flags, counted (zero renders)."""
    def on(x, k):
        return str(x.get(k, "false")).lower() in ("true", "1")
    out = {"mics_changed": 0, "left_cab_off": 0, "rooms_on": 0, "phase_flipped": 0, "pedals_on": 0,
           "gate_threshold_moved": 0, "step2_refused": 0, "drift": 0, "quiet": 0, "fell_back_to_step1": 0,
           "fell_back_to_start": 0, "label_none": 0, "continuation_start_miss": 0, "step1_constrained": 0,
           "step2_constrained": 0, "peak_fail_at_step2": 0}
    for r in recs:
        s2 = r.get("step2") or {}
        out["step2_refused"] += int(s2.get("start_kind") == "refused")
        out["mics_changed"] += int(bool(s2.get("mics_changed")))
        a = s2.get("stage_a_changed") or {}
        out["left_cab_off"] += int(bool(a.get("left_cab_off")))
        out["rooms_on"] += int(a.get("rooms_on", 0))
        out["phase_flipped"] += int(bool(a.get("phase_flipped")))
        lab = r.get("label") or {}
        out["pedals_on"] += int(any(on(lab, "/".join(k)) for k in F.PEDAL_SWITCHES))
        out["gate_threshold_moved"] += int(F.gate_threshold_moved(r.get("step1") or {}))
        out["drift"] += int(bool(r.get("drift")))
        out["quiet"] += int(bool(r.get("quiet")))
        out["fell_back_to_step1"] += int(r.get("fallback_stage") == "step1")
        out["fell_back_to_start"] += int(r.get("fallback_stage") == "start")
        out["label_none"] += int(r.get("label") is None)
        s1 = r.get("step1") or {}
        out["continuation_start_miss"] += int(((s1.get("continuation") or {}).get("start_check") or {}).get("ok") is False)
        out["step1_constrained"] += int(bool((s1.get("best") or {}).get("constrained")))
        out["step2_constrained"] += int(bool(s2.get("a_constrained") or s2.get("b_constrained")))
        out["peak_fail_at_step2"] += int(bool(s1.get("peak_fail")))
    return out


ROWS = ("primary", "vs_stored_label", "vs_S", "held_gain_at_100", "held_gain_at_200")


def report_rows(recs, tq, clus):
    """One block's rows, all and by class: record-weighted jackknife t intervals with the band-weighted reading."""
    vals = [(r, record_values(r)) for r in recs]
    vals = [(r, v) for r, v in vals if v is not None]

    def row(sub, name):
        pts = [(r["cluster"], r["unit"], v[name]) for r, v in sub if name in v]
        if not pts:
            return None
        return dict(F.with_interval(F.jackknife_mean([(c, x) for c, _, x in pts]), tq), band_weighted=clus(pts))

    def rows(sub, every):                               # counts over every record, label None included
        return {**{name: row(sub, name) for name in ROWS}, "counts": counts(every), "records": len(sub),
                "records_counted": len(every)}

    res = {"all": rows(vals, recs) if recs else None}
    for cl in ("clean", "crunch"):
        sub = [(r, v) for r, v in vals if r["cls"] == cl]
        every = [r for r in recs if r["cls"] == cl]
        res[cl] = rows(sub, every) if every else None
    res["records"] = len(vals)
    res["left_out_of_primary"] = [{"unit": r["unit"], "amp": r.get("amp"),
                                   "why": "refused" if "refused" in r else
                                   f"no label ({r.get('fallback_reason')})" if r.get("label") is None
                                   else "non-finite final or start"} for r in recs if record_values(r) is None]
    return res


def no_finite_final(recs):
    """Every record whose final has no finite score on either half when rendered fresh, named (zero renders)."""
    out = []
    for r in recs:
        fin = ((r.get("fresh") or {}).get("final") or {}).get("judge")
        if "refused" not in r and (r.get("step2") or {}).get("start_kind") != "not_run" and \
                unusable(fin, None):
            out.append({"unit": r["unit"], "amp": r.get("amp"), "fallback_stage": r.get("fallback_stage")})
    return out


# --- commands -------------------------------------------------------------------------------------------------------------

def load_records():
    """-> (records, left out), at zero renders, with each record's zero-render start check (`start_problems`) and, for
    C1a's 40, the replay's exactness (`replay_check`)."""
    from learn import arm_a_levers as L
    from learn import pipeline_fix as P

    real_out = set(P.h4_exclusions()["real_out"])
    gdir = P.out_dir() / P.GOAT_DIR / P.SEARCH_DIR
    rdir = P.out_dir() / P.REAL_DIR / P.SEARCH_DIR
    labelled, units, _ = P.goat_labels()
    recs = goat_records(labelled, units, real_out, lambda key: gdir / f"{F.fname(key)}.json")
    left = goat_left_out([json.loads(p.read_text()) for p in sorted(gdir.glob("*.json"))], {r["key"] for r in recs})
    c1a = [r for r in json.loads((F.c1a_dir() / "records.json").read_text())["records"] if r["set"] == "bks"]
    blab, parts, _ = P.real_labels(2)
    b = bks_records(blab, parts, {r["key"] for r in c1a}, real_out, lambda key: rdir / f"{F.fname(key)}.json")
    stored = [json.loads(p.read_text()) for p in sorted(rdir.glob("*.json"))]
    left += bks_left_out(stored, {f"{r['unit']}|{r['amp']}" for r in blab}, P.lag_refused(stored))
    outs = {}
    for r in c1a:
        q = P.out_dir() / F.OUT_DIRS["bks"][0] / F.OUT_DIRS["bks"][1] / f"{F.fname(r['key'])}.json"
        if q.exists():
            outs[r["key"]] = dict(json.loads(q.read_text()), _path=str(q))
    cb, cl = c1a_block(c1a, outs)
    for r in cb:                                        # what "source" means on a fallback in this block (C3)
        r["c1b_record"] = str(P.out_dir() / C.OUT_DIRS["bks"][0] / C.OUT_DIRS["bks"][1] / f"{F.fname(r['key'])}.json")
    recs, left = recs + b + cb, left + cl
    ms = L.menu_S()
    ok = []
    for r in recs:
        bad = start_problems(json.loads(open(r["source"]).read()), r["amp"], ms[r["amp"]][r["cls"]][0])
        if r["block"] == "c1a":
            probs, _ = replay_check(outs[r["key"]], r["amp"])
            bad += [f"replay: {p}" for p in probs]
        if bad:
            left.append({"key": r["key"], "block": r["block"], "why": "; ".join(bad)})
        else:
            ok.append(r)
    return order(ok), left


def cmd_draw(_args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    path = c2_dir() / "records.json"
    if path.exists():
        raise SystemExit(f"{path} exists: the records are drawn once")
    recs, left = load_records()
    P.save(path, {"phase": PHASE, "budget": BUDGET, "seeds": {"step1": F.SEED, "stage_a": C.SEED, "stage_b": C.SEED + 1},
                  "records": recs, "left_out": left, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    n = {b: sum(1 for r in recs if r["block"] == b) for b in BLOCKS}
    print("C2 DRAW", n, "records,", len(left), "left out; renders at most", renders_upper(recs), flush=True)


class Shard:
    """What C2's search loop (`cmd_search`) takes from its caller; C2's own by default. C2r (`full_controls_c2r`)
    passes its own: its records and output folders, its phase, its continued block, its known keys and a `prepare`
    step (the panel's step 0) that writes a record's source before the loop reads it."""
    phase = PHASE
    tag = "C2"

    def mine(self, k, n):
        return shard_records(json.loads((c2_dir() / "records.json").read_text())["records"], k, n)

    def out_path(self, rec, step1=False):
        return out_path(rec, step1)

    def continued(self, rec):
        """A record whose stored C1a search is continued to the budget (replayed, then rendered past it)."""
        return rec["block"] == "c1a"

    def known(self, rec):
        """-> (the keys recorded off by source, why)."""
        return known_keys(rec["amp"]), KNOWN_WHY

    def prepare(self, rec):
        """-> (renders, None) once the record's source can start; (renders, record) to write as its output instead."""
        return 0, None

    def extra(self, rec):
        """More fields for the record's output."""
        return {}


def cmd_search(args, shard=None):
    """One shard of the search. `shard` (a `Shard`) is what the loop takes from its caller; C2's own by default."""
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

    cfg = shard or Shard()
    P.require(cfg.phase)
    k, n = args.shard
    mine = cfg.mine(k, n)
    first = mine[:MISS_GUARD[1]]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    ms = L.menu_S()
    LO._wait_cap()
    lists = C.mic_lists()
    renders = 0
    tally = {"step1": {"on": 0, "off_after_miss": 0, "refused": 0, "continued": 0, "resumed": 0, "replay_mismatch": 0,
                       "continuation_start_miss": 0},
             "step2": {"canonical": 0, "raw_after_miss": 0, "refused": 0, "not_run": 0}}

    def sx1(x):                                         # C1a's (step 1): edits in 5B.1's order
        return LO.tdict(LO.sdict(x))

    def sorted_x(x, amp):                               # C1b's (step 2): the plugin's settings, in 5B.1's order
        return LO.tdict(LO.sdict(C.plugin(x, amp)))

    def outcome(r):
        p = cfg.out_path(r)
        if not p.exists():
            return None
        return "refused" if "refused" in json.loads(p.read_text()) else "ok"

    for rec in mine:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        out, out1 = cfg.out_path(rec), cfg.out_path(rec, step1=True)
        if out.exists():
            continue
        used0, skip = cfg.prepare(rec)                  # C2r's panel: step 0 makes the source (C2: nothing)
        renders += used0
        if skip is not None:
            P.save(out, skip)
            print(f"{rec['key'][-70:]}: {skip.get('why')}; renders so far {renders}", flush=True)
            continue
        src = json.loads(open(rec["source"]).read())
        amp, prt = rec["amp"], rec["prt"]
        sel, S = ms[amp][rec["cls"]]
        if src["select"] != sel or src.get("label") is None or src["unit"] != rec["unit"] or src["amp"] != amp:
            raise SystemExit(f"{rec['key']}: the source record's unit, amp, select or label does not fit")
        search, held, lag = src["search"], src["held"], src["lag"]
        kk, kwhy = cfg.known(rec)
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        ref_v = float(src["best"]["judge"][search])
        base = {"plan": PLAN, "set": rec["set"], "block": rec["block"], "unit": rec["unit"], "rig": src.get("rig"),
                "di": src.get("di"), "item": src.get("item"), "fold": src.get("fold"), "cls": rec["cls"], "amp": amp,
                "select": sel, "search": search, "held": held, "lag": lag, "item_lag": src.get("item_lag"),
                "cluster": rec["cluster"], "real_out": rec["real_out"], "budget": BUDGET,
                "seeds": {"step1": F.SEED, "stage_a": C.SEED, "stage_b": C.SEED + 1}, "gate_on_db": F.GATE_ON_DB,
                "source": rec["source"], "source_best_judge": src["best"]["judge"], "s_judge": src.get("s_judge"),
                "known_keys": kk, "known_why": kwhy,
                **({"c1b_record": rec.get("c1b_record"), "c1a_output": rec.get("c1a_output"),
                    "on_fallback": "C1b's record (c1b_record) is C3's input"} if cfg.continued(rec) else {}),
                **cfg.extra(rec)}

        def fresh(x, form=None):
            xs = (form or (lambda z: sorted_x(z, amp)))(x)
            y = np.asarray(AM.fresh_render(CB.new_renderer, di32, sel, xs, xs), np.float64)[trim[0]:trim[1]]
            return {"judge": K.judge(ref, y, di, lag), "render_sha256": AM.audio_sha(y),
                    "peak_dbfs": A.peak_dbfs(y, trim_s=0.0)}

        def evaluate(rr, x):
            y = np.asarray(rr.render(di32, sel, sx1(x)), np.float64)[trim[0]:trim[1]]
            return y, K.judge(ref, y, di, lag)

        # --- step 1: C1a's search at budget 200, Amendment 1's start-miss path ---------------------------------------
        def step1(start):
            """One C1a search from `start` in its own renderer process, primed with the start. -> (renders, values,
            trials, evals, start record, names); raises F.StartMiss if its first evaluation is not the stored label's,
            StartUnusable if it can't stand as a label."""
            dims = F.c1a_space(amp, start)
            names = [d.name for d in dims]
            values, trials, evals, start_rec = [], [], [], {}
            used = [1]
            rr = CB.new_renderer()
            try:
                rr.render(di32, sel, sx1(start))            # the discarded priming render, with the start

                def f(x):
                    y, j = evaluate(rr, x)
                    used[0] += 1
                    if not values:
                        start_rec.update(value=j[search], sha=AM.audio_sha(y), ref_value=ref_v,
                                         ref_sha=src["best"].get("render_sha256"),
                                         bit_identical=AM.audio_sha(y) == src["best"].get("render_sha256"))
                        if not F.within(j[search], ref_v):
                            raise F.StartMiss(j[search], AM.audio_sha(y))
                        why = unusable(j, None)             # the start: its halves alone
                        if why:
                            raise StartUnusable(why)
                    evals.append({"judge": j, "peak_dbfs": A.peak_dbfs(y, trim_s=0.0), "render_sha256": AM.audio_sha(y),
                                  "x": dict(x)})
                    values.append(j[search])
                    trials.append({"x": {nm: x.get(tuple(nm.rsplit("/", 1))) for nm in names}, "judge": j})
                    return j[search]

                K.coord_search(dims, start, f, BUDGET, F.SEED, cats="levels", canon=F.make_canon(amp))
            except (F.StartMiss, StartUnusable) as miss:
                miss.renders = used[0]
                raise
            finally:
                rr.close()
            return used[0], values, trials, evals, start_rec, names

        def continued(c1a):
            """C1a's own search continued to BUDGET: its stored evaluations replayed (each setting checked), the rest
            rendered in a process primed with its start, after a check render of the start against C1a's first
            evaluation. -> (renders, values, trials, evals, start record, names, start, continuation record)."""
            start = LO.tdict(c1a["start_settings"])
            names, stored = c1a["searched_keys"], c1a["trials"][:BUDGET]
            dims = F.c1a_space(amp, start)
            if [d.name for d in dims] != names:
                raise SystemExit(f"{rec['key']}: C1a's space differs from its stored names")
            values, trials, evals = [], [], []
            info = {"stored": len(stored), "rendered": 0, "start_check": None}
            used, rr = [0], None
            try:
                if len(stored) < BUDGET:
                    rr = CB.new_renderer()
                    rr.render(di32, sel, sx1(start))
                    y, j = evaluate(rr, start)
                    used[0] += 2
                    ok = F.within(j[search], float(stored[0]["judge"][search]))
                    info["start_check"] = {"value": j[search], "ref_value": stored[0]["judge"][search], "ok": ok,
                                           "peak_dbfs": A.peak_dbfs(y, trim_s=0.0)}
                    why = unusable(j, None)                 # the start: its halves alone
                else:                                       # no render: C1a's first evaluation
                    why = unusable(stored[0]["judge"], None)
                if why:
                    e = StartUnusable(why)
                    e.renders = used[0]
                    raise e

                def render(x):
                    if rr is None or not info["start_check"]["ok"]:
                        return None                         # no continuation: the stored evaluations stand
                    y, j = evaluate(rr, x)
                    used[0] += 1
                    info["rendered"] += 1
                    evals.append({"judge": j, "peak_dbfs": A.peak_dbfs(y, trim_s=0.0),
                                  "render_sha256": AM.audio_sha(y), "x": dict(x)})
                    trials.append({"x": {nm: x.get(tuple(nm.rsplit("/", 1))) for nm in names}, "judge": j})
                    values.append(j[search])
                    return j[search]
                g = replaying(stored, names, search, render)

                def f(x):
                    replay = g.state["i"] < len(stored)
                    v = g(x)
                    if replay:
                        t = stored[g.state["i"] - 1]
                        evals.append({"judge": t["judge"], "peak_dbfs": None, "render_sha256": None, "x": dict(x),
                                      "replayed": True})
                        trials.append(t)
                        values.append(v)
                    return v
                K.coord_search(dims, start, f, BUDGET, F.SEED, cats="levels", canon=F.make_canon(amp))
            except ReplayMismatch as m:
                m.renders = used[0]
                raise
            finally:
                if rr is not None:
                    rr.close()
            info["replayed"] = g.state["i"]
            st = c1a.get("start") or {}
            return used[0], values, trials, evals, st, names, start, info

        start_gate, first_miss, cont = "on", None, None
        if out1.exists():                               # step 1 was saved before a stop: resume at step 2
            r1 = json.loads(out1.read_text())
            s1, peaks, start_gate = r1["step1"], r1["peaks"], r1["step1"]["start_gate"]
            start, names = LO.tdict(s1["start_settings"]), s1["searched_keys"]
            best1 = s1["best"]
            bx, why1 = LO.tdict(best1["settings"]), best1["unusable"]
            tally["step1"]["resumed"] += 1
        else:
            if cfg.continued(rec):
                c1a = json.loads(open(rec["c1a_output"]).read())
                start_gate = c1a.get("start_gate", "on")
                try:
                    used, values, trials, evals, start_rec, names, start, cont = continued(c1a)
                except StartUnusable as bad_start:
                    renders += bad_start.renders
                    P.save(out, {**base, "ledger": f"{P.LEDGER_ID} {cfg.phase}", "label": None,
                                 "step1": {"start_gate": "refused"}, "refused": {"unusable": str(bad_start)},
                                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
                    tally["step1"]["refused"] += 1
                    print(f"{rec['key'][-70:]}: refused (the start unusable: {bad_start}); renders so far {renders}",
                          flush=True)
                    continue
                except ReplayMismatch as m:
                    renders += m.renders
                    P.save(out, {**base, "ledger": f"{P.LEDGER_ID} {cfg.phase}", "label": None,
                                 "step1": {"start_gate": "refused"}, "refused": {"replay_mismatch": m.args[0]},
                                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
                    tally["step1"]["replay_mismatch"] += 1
                    print(f"{rec['key'][-70:]}: the replay is not exact at evaluation {m.args[0]}; renders so far "
                          f"{renders}", flush=True)
                    continue
                renders += used
                tally["step1"]["continued"] += 1
                if (cont.get("start_check") or {}).get("ok") is False:
                    tally["step1"]["continuation_start_miss"] += 1
            else:
                start = F.c1a_start(src["best"]["settings"], amp)
                bad = F.audible_change(start, src["best"]["settings"], amp, declared=F.GATE_KEYS)
                if bad:
                    raise SystemExit(f"{rec['key']}: the start changes what sounds: {bad}")
                try:
                    try:
                        used, values, trials, evals, start_rec, names = step1(start)
                        renders += used
                    except F.StartMiss as miss:
                        renders += miss.renders
                        first_miss = {"value": miss.value, "sha": miss.sha, "ref_value": ref_v}
                        start_off = F.c1a_start(src["best"]["settings"], amp, gate=False)
                        fo = fresh(start_off, sx1)      # the second start: the gate as in the label
                        renders += 2
                        v_off = fo["judge"][search]
                        start_gate = F.start_plan(False, F.within(v_off, ref_v))
                        first_miss.update(gate_off_value=v_off, gate_off_sha=fo["render_sha256"])
                        if start_gate == "off_after_miss":
                            start = start_off
                            try:
                                used, values, trials, evals, start_rec, names = step1(start)
                                renders += used
                            except F.StartMiss as m2:
                                renders += m2.renders
                                first_miss["gate_off_run_value"] = m2.value
                                start_gate = "refused"
                except StartUnusable as bad_start:
                    renders += bad_start.renders
                    start_gate, first_miss = "refused", dict(first_miss or {}, unusable=str(bad_start))
                if start_gate == "refused":
                    P.save(out, {**base, "ledger": f"{P.LEDGER_ID} {cfg.phase}", "label": None,
                                 "step1": {"start_gate": "refused"}, "refused": first_miss,
                                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
                    tally["step1"]["refused"] += 1
                    print(f"{rec['key'][-70:]}: refused ({first_miss}); renders so far {renders}", flush=True)
                    # read from the written records: after a restart the first ten are written, and the guard does
                    # not fire again on records it already passed (by design: a restart is a human's decision)
                    if rec in first and systematic_miss([outcome(r) for r in first]):
                        raise SystemExit(f"SYSTEMATIC MISS: {MISS_GUARD[0]} of shard {k}/{n}'s first {MISS_GUARD[1]} "
                                         "records refused at the start")
                    continue
                tally["step1"][start_gate] += 1
            p0 = evals[0]["peak_dbfs"]
            if p0 is None:                              # a replayed start: the start-check render, else the stored label
                p0 = ((cont or {}).get("start_check") or {}).get("peak_dbfs")
            if p0 is None:
                p0 = src["best"].get("peak_dbfs")
            bound = peak_bound(p0)
            # the constrained best: the lowest among the evaluations that pass the bound (a replayed one's peak is
            # unknown here; it is checked at step 2's first evaluation), the checkpoints likewise
            cps = {c: constrained_index(evals, search, bound, c) for c in F.CHECKPOINTS if c <= BUDGET}
            i1 = constrained_index(evals, search, bound, BUDGET)
            i_free = F.incumbent_at(values, BUDGET)
            if i1 is None:                              # nothing passes, not even the start: the source label
                i1 = i_free if i_free is not None else 0
            best_ev = evals[i1]
            bx = best_ev["x"]
            why1 = unusable(best_ev["judge"], best_ev["peak_dbfs"], None if best_ev.get("replayed") else bound)
            i_fb = constrained_index(evals, search, bound, BUDGET, known_only=True)   # if a replayed best fails later
            fb_ev = evals[i_fb] if i_fb is not None else None
            best1 = {"judge": best_ev["judge"], "peak_dbfs": best_ev["peak_dbfs"],
                     "render_sha256": best_ev["render_sha256"], "settings": LO.sdict(bx), "unusable": why1,
                     "replayed": bool(best_ev.get("replayed")), "index": i1, "unconstrained_index": i_free,
                     "constrained": i1 != i_free}
            s1 = {"start": start_rec, "start_gate": start_gate, "first_start_miss": first_miss, "continuation": cont,
                  "start_settings": LO.sdict(start), "searched_keys": names, "curve": values,
                  "evaluations": len(values), "trials": trials,
                  "checkpoints": {str(c): {"evaluations": c, "index": i, "judge": evals[i]["judge"]}
                                  for c, i in cps.items() if i is not None},
                  "best": best1, "changed": F.changed(bx, start, amp, S),
                  "peak_fallback": ({"kind": "rendered", "index": i_fb, "settings": LO.sdict(fb_ev["x"]),
                                     "judge": fb_ev["judge"], "peak_dbfs": fb_ev["peak_dbfs"]} if fb_ev is not None
                                    else {"kind": "start", "settings": LO.sdict(start), "judge": evals[0]["judge"],
                                          "peak_dbfs": p0}) if best_ev.get("replayed") else None}
            peaks = {"start": p0, "step1_best": best_ev["peak_dbfs"], "bound": bound}
            P.save(out1, {"ledger": f"{P.LEDGER_ID} {cfg.phase}", "step1": s1, "peaks": peaks})   # a stop loses <= 65
        ledger = f"{P.LEDGER_ID} {cfg.phase}" + (f" {F.PHASE_A1}" if start_gate == "off_after_miss" else "")
        if why1:                                        # step 2 skipped: C3 falls back to the source label
            P.save(out, {**base, "ledger": ledger, "step1": s1, "step2": {"start_kind": "not_run"},
                         "searched_keys": None, "peaks": peaks, "label": None, "fallback_stage": "start",
                         "fallback_reason": f"step 1's best unusable: {why1}",
                         "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            tally["step2"]["not_run"] += 1
            print(f"{rec['key'][-70:]}: step 1's best unusable ({why1}); the source label stands; renders so far "
                  f"{renders}", flush=True)
            continue

        # --- step 2: C1b's stages A and B on step 1's best, its start check against step 1's best --------------------
        bound = peaks.get("bound", peak_bound(peaks.get("start")))

        def dry_stages(x0, canon, ref2, check_peak):
            """C1b's stages A and B in one renderer process primed with x0, each stage's best the lowest of its
            evaluations that pass the bound (`constrained_index`). -> (renders, x_A, x_B, record); raises F.StartMiss
            if the first evaluation is not step 1's best, PeakFail if it fails the bound (check_peak: a replayed best,
            whose peak this is the first reading of)."""
            used = [1]
            seen, xs, stage_of, trace = {}, {}, {}, []
            stage = ["A"]
            rr = CB.new_renderer()
            try:
                rr.render(di32, sel, sorted_x(x0, amp))

                def f(x):
                    key = K.key(x)
                    if key in seen:
                        return seen[key]["judge"][search]
                    y = np.asarray(rr.render(di32, sel, sorted_x(x, amp)), np.float64)[trim[0]:trim[1]]
                    used[0] += 1
                    j = K.judge(ref, y, di, lag)
                    pk = A.peak_dbfs(y, trim_s=0.0)
                    if not trace:
                        if not F.within(j[search], ref2):
                            raise F.StartMiss(j[search], AM.audio_sha(y))
                        why_p = unusable(j, pk, bound) if check_peak else None
                        if why_p:
                            raise PeakFail({"judge": j, "peak_dbfs": pk, "why": why_p})
                    seen[key], xs[key], stage_of[key] = {"judge": j, "peak_dbfs": pk}, dict(x), stage[0]
                    trace.append({"stage": stage[0], "judge": j, "peak_dbfs": pk})
                    return j[search]

                def best_of(keys, fallback):
                    i = constrained_index([seen[q] for q in keys], search, bound)
                    return cn(xs[keys[i]]) if i is not None else fallback

                cn = canon or (lambda x: x)
                xa_free, _, _ = K.coord_search(C.rooms_dims(x0), x0, f, C.BUDGET_ROOMS, C.SEED, cats="levels",
                                               canon=canon)
                xa = best_of([q for q in seen if stage_of[q] == "A"], cn(x0))
                stage[0] = "B"
                xb_free, _, _, stages_b = K.knob_search(C.mics_eq_dims(xa, amp, lists), xa, f, C.BUDGET_MICS_EQ,
                                                        C.SEED + 1, shares=C.STAGE_B_SHARES, canon=canon)
                xb = best_of([K.key(xa)] + [q for q in seen if stage_of[q] == "B"], xa)
            except (F.StartMiss, PeakFail) as miss:
                miss.renders = used[0]
                raise
            finally:
                rr.close()
            return used[0], xa, xb, {"trace": trace, "start": seen[K.key(x0)], "a": seen[K.key(xa)],
                                     "b": seen[K.key(xb)], "stages_b": stages_b,
                                     "a_constrained": K.key(xa) != K.key(cn(xa_free)),
                                     "b_constrained": K.key(xb) != K.key(cn(xb_free))}

        def step2_from(label1, ref2, check_peak):
            """Step 2 from one step-1 label: the canonical start, then the raw label on a miss. -> (renders, kind,
            miss, start, x_A, x_B, record); PeakFail propagates."""
            start2 = C.c1b_start(label1, amp)
            bad = C.audible_change(start2, label1, amp)
            if bad:
                raise SystemExit(f"{rec['key']}: step 2's start changes what sounds: {bad}")
            got = 0
            try:
                used, xa, xb, dry = dry_stages(start2, C.make_canon(amp), ref2, check_peak)
                return got + used, "canonical", None, start2, xa, xb, dry
            except F.StartMiss as miss:
                got += miss.renders
                miss2 = {"value": miss.value, "sha": miss.sha, "ref_value": ref2}
            start2 = C.raw_start(label1, amp)
            try:
                used, xa, xb, dry = dry_stages(start2, None, ref2, check_peak)
                return got + used, "raw_after_miss", miss2, start2, xa, xb, dry
            except F.StartMiss as m2:
                miss2["raw_value"] = m2.value
                return got + m2.renders, "refused", miss2, start2, None, None, None
            except PeakFail as pf:
                pf.renders += got
                raise

        label1 = LO.sdict(bx)
        wet = C.dry_start_problems(LO.tdict(label1), amp)
        if wet:
            raise SystemExit(f"{rec['key']}: step 2's start must be dry: {wet} on")
        try:
            used, kind, miss2, start2, xa, xb, dry = step2_from(label1, float(best1["judge"][search]),
                                                               bool(best1.get("replayed")))
            renders += used
        except PeakFail as pf:                          # a replayed best quieter than the bound: the best rendered
            renders += pf.renders                       # evaluation that passes (101 to 200), else the start
            fb = s1["peak_fallback"]
            s1["peak_fail"] = {**pf.args[0], "fallback": fb["kind"], "replayed_best": dict(best1)}
            label1, bx = fb["settings"], LO.tdict(fb["settings"])
            best1 = {**best1, "settings": fb["settings"], "judge": fb["judge"], "peak_dbfs": fb["peak_dbfs"],
                     "replayed": False, "index": fb.get("index"), "constrained": True}
            s1["best"] = best1
            used, kind, miss2, start2, xa, xb, dry = step2_from(label1, float(fb["judge"][search]), False)
            renders += used
        tally["step2"][kind] += 1
        if kind == "refused":                           # step 1's best stands, with step 1's mask
            final, keys, form = bx, names, sx1
            s2 = {"start_kind": "refused", "refused": miss2}
        else:
            final, keys, form = xb, searched_keys(names, start2, xa, amp, lists), None
            s2 = {"start_kind": kind, "first_start_miss": miss2, "start_settings": LO.sdict(C.plugin(start2, amp)),
                  "start": dry["start"], "stage_a": dry["a"], "stage_b": dry["b"], "trace": dry["trace"],
                  "stages_b": dry["stages_b"], "a_constrained": dry["a_constrained"],
                  "b_constrained": dry["b_constrained"],
                  "rooms_keys": [d.name for d in C.rooms_dims(start2)],
                  "mics_eq_keys": [d.name for d in C.mics_eq_dims(xa, amp, lists)],
                  "stage_a_settings": LO.sdict(C.plugin(xa, amp)), "stage_b_settings": LO.sdict(C.plugin(xb, amp)),
                  "mics_changed": any(xb.get(m) != start2.get(m) for m in C.MIC_KEYS),
                  "stage_a_changed": C.stage_a_changes(xa, start2), "mic_lists": lists[amp]}
            peaks["step1_best_fresh"] = dry["start"]["peak_dbfs"]   # step 2's first evaluation, in its own process
        fr = fresh(final, form)
        renders += 2
        peaks["final_fresh"] = fr["peak_dbfs"]
        why = unusable(fr["judge"], fr["peak_dbfs"], bound)
        stage_fb, reason, lab_fr = None, None, fr
        label = LO.sdict(final if form else C.plugin(final, amp))
        if why:                                         # F70's guard: back to the previous stage's best
            why_s1 = unusable(dry["start"]["judge"], dry["start"]["peak_dbfs"], bound) if kind != "refused" else why
            if why_s1 is None:
                stage_fb, reason, lab_fr = "step1", f"the final unusable: {why}", dry["start"]
                label, keys = label1, names
            else:
                stage_fb, lab_fr = "start", None
                reason = f"the final unusable: {why}; step 1's best unusable: {why_s1}"
                label, keys = None, None
        known_bad = known_problems(label, amp) if label and kk else []
        if known_bad:
            raise SystemExit(f"{rec['key']}: the label is not dry: {known_bad}")
        lab_peak = (lab_fr or {}).get("peak_dbfs")
        P.save(out, {**base, "ledger": ledger, "step1": s1, "step2": s2, "searched_keys": keys,
                     "fresh": {"final": fr, "label": lab_fr}, "peaks": peaks,
                     "drift": bool(lab_fr) and C.drifted(peaks["start"], lab_peak),
                     "quiet": bool(lab_fr) and quiet(lab_peak),
                     "label": label, "fallback_stage": stage_fb, "fallback_reason": reason,
                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{rec['key'][-70:]}: step 1 {s1['evaluations']} + step 2 {len(s2.get('trace') or [])} evaluations "
              f"({kind}{', ' + stage_fb + ' fallback' if stage_fb else ''}); renders so far {renders}", flush=True)
    print(f"{cfg.tag}-SEARCH DONE {k}/{n}: {renders} renders; starts {tally}", flush=True)


def cmd_report(_args):
    from scipy import stats

    from learn import pipeline_fix as P

    P.require(PHASE)
    tq = lambda df: float(stats.t.ppf(0.95, df))          # noqa: E731
    plan = json.loads((c2_dir() / "records.json").read_text())
    out = {"phase": PHASE, "budget": BUDGET, "left_out_at_draw": plan["left_out"]}
    every = {}
    for r in plan["records"]:
        p = out_path(r)
        if p.exists():
            every.setdefault(r["block"], []).append(json.loads(p.read_text()))
    for b in BLOCKS:
        recs = every.get(b, [])
        main = [r for r in recs if not r.get("real_out")]
        out[b] = {"written": len(recs), "drawn": sum(1 for r in plan["records"] if r["block"] == b),
                  "rows": report_rows(main, tq, P.clustered),
                  "real_out": report_rows([r for r in recs if r.get("real_out")], tq, P.clustered),
                  "step1_starts": {kk: sum(1 for r in recs if (r.get("step1") or {}).get("start_gate") == kk)
                                   for kk in ("on", "off_after_miss", "refused")},
                  "step2_starts": {kk: sum(1 for r in recs if (r.get("step2") or {}).get("start_kind") == kk)
                                   for kk in ("canonical", "raw_after_miss", "refused", "not_run")},
                  "fallbacks": [{"unit": r["unit"], "amp": r["amp"], "stage": r.get("fallback_stage"),
                                 "why": r.get("fallback_reason")} for r in recs if r.get("fallback_stage")],
                  "quiet": [r["unit"] + "|" + r["amp"] for r in recs if r.get("quiet")],
                  "no_finite_final": no_finite_final(recs),
                  "refused": [{"unit": r["unit"], "amp": r["amp"], **r["refused"]} for r in recs if "refused" in r]}
    P.save(c2_dir() / "report.json", out)
    print(json.dumps({b: {"written": out[b]["written"], "drawn": out[b]["drawn"],
                          "primary": (out[b]["rows"]["all"] or {}).get("primary"),
                          "step1_starts": out[b]["step1_starts"], "step2_starts": out[b]["step2_starts"],
                          "counts": (out[b]["rows"]["all"] or {}).get("counts"),
                          "no_finite_final": len(out[b]["no_finite_final"])} for b in BLOCKS},
                     indent=1, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("c2-draw").set_defaults(fn=cmd_draw)
    s = sub.add_parser("c2-search")
    s.add_argument("--shard", type=F.shard, default=(0, 1))
    s.set_defaults(fn=cmd_search)
    sub.add_parser("c2-report").set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
