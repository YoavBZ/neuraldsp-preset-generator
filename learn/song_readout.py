"""Step 3's readout (`docs/song-settings-plan.md`): the declared decision rules as pure functions,
and a `report` command that reads the stored scores once they all exist.

    .venv/bin/python -m learn.song_readout report [--control-attempt N] [--without-half-bank]

The rules, in the plan's words and where they live here:
- arm B's positive control, per fold (`positive_control`);
- arm B's shuffled-input control (`shuffled_control`);
- each arm's pass rule, rows 1–5 (`arm_rules`), with arm B's data-limit reading (`data_limit`);
- arm A's known-target control, as amendment 2 reads it (`known_target_control`);
- amendment 3's sensitivity: Gym Hours GTR 1's half-B cells left out (`arm_status`);
- the step-6 readout table of the ML plan (`readout`).

Nothing here renders, trains or predicts. The pure functions take plain dicts; `gather` is the
only code that reads files.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

EPS = 1e-9                     # threshold comparisons are inclusive up to float noise
GAP_FLOOR = 0.1                # d_start − d_target (arm B's positive control; amendment 2)
CLOSE_SHARE = 0.5              # "closes ≥ 50% of the gap"
MAX_ATTEMPTS = 3               # the first run and "at most two fix-and-re-runs"
FOLDS = (0, 1, 2, 3)
GYM = "telefunken-Gym_Hours-GTR_1"
MUSDB_TRAIN_BANDS = ("Atlantis Bound", "Wall Of Death")
COST = {"B": 1, "C": 51, "A": 150}          # renders per cell, for ties at the readout
KS_CHECKPOINTS = (50, 100, 150)


def other(h):
    return "B" if h == "A" else "A"


def finite(*xs):
    return all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in xs)


def at_least_share(k, n, num, den):
    """k/n ≥ num/den, exactly (no float rounding at 2/3 or 60%)."""
    return k * den >= num * n


# --- statistics -------------------------------------------------------------------------------

def bw_stats(rows):
    """rows: (band, x). Band-weighted mean (each band's mean, then the mean of bands) with a
    band-clustered 90% interval: t on the band means, bands − 1 df. With one band there is no
    interval (None)."""
    by = {}
    for b, x in rows:
        by.setdefault(b, []).append(x)
    if not by:
        return {"band_weighted_mean": None, "lo90": None, "hi90": None, "bands": 0, "bands_negative": 0,
                "bands_positive": 0, "parts": 0, "leave_one_band_out": []}
    means = {b: statistics.fmean(v) for b, v in by.items()}
    g = len(means)
    m = statistics.fmean(means.values())
    lo = hi = None
    if g > 1:
        from scipy import stats

        half = stats.t.ppf(0.95, g - 1) * statistics.stdev(means.values()) / math.sqrt(g)
        lo, hi = m - half, m + half
    return {"band_weighted_mean": m, "lo90": lo, "hi90": hi, "bands": g,
            "bands_negative": sum(v < -EPS for v in means.values()),
            "bands_positive": sum(v > EPS for v in means.values()),
            "parts": len(rows),
            "leave_one_band_out": [statistics.fmean(v for c, v in means.items() if c != b) for b in sorted(means)]
            if g > 1 else []}


def part_rows(units, f):
    """The per-part unit: f(unit) (None skips the unit) averaged over a part's directions and
    amps. -> [(band, gain_class, value)], sorted by part."""
    by = {}
    for u in units:
        v = f(u)
        if v is None:
            continue
        by.setdefault((u["slug"], u["band"], u["cls"]), []).append(v)
    return [(b, c, statistics.fmean(v)) for (s, b, c), v in sorted(by.items())]


def bw(rows, classes=("clean", "crunch")):
    return bw_stats([(b, v) for b, c, v in rows if c in classes])


def log_vs(a, b):
    def f(u):
        x, y = u["d"].get(a), u["d"].get(b)
        return math.log(x / y) if finite(x, y) and x > 0 and y > 0 else None
    return f


# --- the units and the refused-half rule ------------------------------------------------------

DECISION_METHODS = ("S", "K_S", "A", "B", "C", "menu_pick")


def drop_refused(units, methods=DECISION_METHODS):
    """A held half that any arm or comparator could not be scored on (non-finite) drops that
    direction for every arm and comparator alike. The controls (shuffled, constant, amp track,
    half bank, K_S checkpoints) are compared only where both sides are finite.
    -> (kept, dropped [(slug, amp, search, [methods])])."""
    kept, dropped = [], []
    for u in units:
        if u.get("skipped"):
            dropped.append((u["slug"], u["amp"], u["search"], ["knob-ceiling skipped"]))
            continue
        bad = []
        for k in methods:
            if k in u["d"] and not (finite(u["d"][k]) and u["d"][k] > 0):
                bad.append(k)
        if bad:
            dropped.append((u["slug"], u["amp"], u["search"], sorted(bad)))
        else:
            kept.append(u)
    return kept, dropped


def without_gym_half_b(units):
    """Amendment 3: Gym Hours GTR 1's cells scored on half B left out."""
    return [u for u in units if not (u["slug"] == GYM and u["held"] == "B")]


# --- arm B's positive control -----------------------------------------------------------------

def gap_closed(d_start, d_found, d_target):
    """(d_start − d_found) / (d_start − d_target); None when the denominator is zero."""
    den = d_start - d_target
    return None if den == 0 else (d_start - d_found) / den


def positive_control(units, attempt=1, folds=FOLDS):
    """units: {"fold", "target" (id), "held", "d": {"target", "S", "pred", "median"}} per target and
    direction (the prediction from one half, judged on the other).

    Per fold: a unit is kept only if d_S − d_target ≥ 0.1 (after dropping non-finite ones). The
    fold passes if the gap closed is ≥ 50% on ≥ 2/3 of kept units AND the prediction is closer
    than the median settings (strictly) on ≥ 2/3. A fold with no kept unit fails. The control
    passes if every fold passes. `attempt` is 1 for the first run; up to 3 (two fix-and-re-runs)."""
    if not 1 <= attempt <= MAX_ATTEMPTS:
        raise ValueError(f"attempt {attempt}: the plan allows at most two fix-and-re-runs (attempts 1–3)")
    out = {"attempt": attempt, "folds": {}}
    for f in folds:
        us = [u for u in units if u["fold"] == f]
        fin = [u for u in us if all(finite(u["d"][k]) for k in ("target", "S", "pred", "median"))]
        kept = [u for u in fin if u["d"]["S"] - u["d"]["target"] >= GAP_FLOOR - EPS]
        closed = closer = 0
        gcs = []
        for u in kept:
            d = u["d"]
            g = gap_closed(d["S"], d["pred"], d["target"])
            gcs.append(g)
            closed += g >= CLOSE_SHARE - EPS
            closer += d["pred"] < d["median"]
        n = len(kept)
        ok = n > 0 and at_least_share(closed, n, 2, 3) and at_least_share(closer, n, 2, 3)
        out["folds"][f] = {"units": len(us), "non_finite": len(us) - len(fin), "kept": n,
                           "targets_kept": len({u["target"] for u in kept}),
                           "gap_closed_ge_50": closed, "closer_than_median": closer,
                           "median_gap_closed": statistics.median(gcs) if gcs else None, "passes": ok}
    out["passes"] = all(v["passes"] for v in out["folds"].values())
    out["final"] = out["passes"] or attempt >= MAX_ATTEMPTS
    out["reruns_left"] = 0 if out["passes"] else MAX_ATTEMPTS - attempt
    out["status"] = ("passes" if out["passes"] else
                     "fails after two re-runs" if attempt >= MAX_ATTEMPTS else
                     f"fails; fix and re-run allowed ({out['reruns_left']} left)")
    return out


# --- arm B's shuffled-input control and data-limit check --------------------------------------

def shuffled_control(units):
    """Arm B against the shuffled mean: per direction log d_B − mean_j log d_shuffled_j (the
    geometric mean of the shuffled distances), on the per-part unit. Passes if band-weighted
    ≤ −0.05 AND arm B is better (band mean < 0) in ≥ 60% of bands."""
    def f(u):
        sh = u["d"].get("shuffled") or []
        b = u["d"].get("B")
        if not sh or not finite(b, *sh) or b <= 0 or min(sh) <= 0:
            return None
        return math.log(b) - statistics.fmean(math.log(x) for x in sh)

    s = bw(part_rows(units, f))
    m = s["band_weighted_mean"]
    ok = (m is not None and m <= -0.05 + EPS and at_least_share(s["bands_negative"], s["bands"], 3, 5))
    return {**s, "passes": bool(ok)}


def data_limit(units):
    """Full bank against half bank, band-weighted on the per-part unit: data-limited if the full
    bank is better by more than 0.03 (log d_full − log d_half < −0.03)."""
    s = bw(part_rows(units, log_vs("B", "B_half")))
    m = s["band_weighted_mean"]
    return {**s, "data_limited": m is not None and m < -0.03 - EPS}


# --- arm A's known-target control (amendment 2) -----------------------------------------------

def known_target_control(results, held="B"):
    """results: the control cells' result.json dicts ({"target", "S", "measure_run",
    "rebuilt_run"}, each {half: distance}). Read on the held half, as amendment 2 declares:
    - informative: d_S − d_target ≥ 0.1;
    - ≥ 6 informative: the original rows, "8 of 12" read as ≥ 2/3 of the informative cells, and
      the mean shortfall log(d_found / d_target) over the informative cells;
    - fewer: the rows on the mean shortfall over all cells (finite ones).
    -> {"row": 1|2|3, "outcome": "set-up wrong"|"passes"|"fails", ...}"""
    cells = []
    for r in results:
        s, t = r["S"][held], r["target"][held]
        c = {"S": s, "target": t, "gap": s - t if finite(s, t) else None}
        for run in ("measure_run", "rebuilt_run"):
            fd = r[run][held]
            ok = finite(s, t, fd) and t > 0 and fd > 0
            c[run] = {"found": fd, "gap_closed": gap_closed(s, fd, t) if ok else None,
                      "shortfall": math.log(fd / t) if ok else None}
        cells.append(c)
    inf = [c for c in cells if c["gap"] is not None and c["gap"] >= GAP_FLOOR - EPS]
    n = len(inf)
    out = {"cells": len(cells), "informative": n}

    def mean_short(cs, run):
        v = [c[run]["shortfall"] for c in cs if c[run]["shortfall"] is not None]
        return statistics.fmean(v) if v else None

    if n >= 6:
        k_m = sum(c["measure_run"]["gap_closed"] is not None and c["measure_run"]["gap_closed"] >= CLOSE_SHARE - EPS
                  for c in inf)
        k_r = sum(c["rebuilt_run"]["gap_closed"] is not None and c["rebuilt_run"]["gap_closed"] >= CLOSE_SHARE - EPS
                  for c in inf)
        sm, sr = mean_short(inf, "measure_run"), mean_short(inf, "rebuilt_run")
        out.update(mode="gap closed (≥ 6 informative)", measure_closed=k_m, rebuilt_closed=k_r,
                   measure_mean_shortfall=sm, rebuilt_mean_shortfall=sr)
        if not at_least_share(k_m, n, 2, 3):
            row = 1
        elif at_least_share(k_r, n, 2, 3) or (sm is not None and sr is not None and sr <= sm + 0.03 + EPS):
            row = 2
        else:
            row = 3
    else:
        sm, sr = mean_short(cells, "measure_run"), mean_short(cells, "rebuilt_run")
        out.update(mode="mean shortfall (< 6 informative)", measure_mean_shortfall=sm, rebuilt_mean_shortfall=sr)
        if sm is None or sr is None:
            raise ValueError("no finite shortfall to read")
        if sm > 0.10 + EPS:
            row = 1
        elif sr <= sm + 0.03 + EPS or sr <= EPS:
            row = 2
        else:
            row = 3
    out["row"] = row
    out["outcome"] = {1: "set-up wrong", 2: "passes", 3: "fails"}[row]
    return out


# --- each arm's pass rule ---------------------------------------------------------------------

def arm_rules(units, arm, controls_pass=None):
    """The declared pass rule on these units (held half, band-weighted, against S):
    1. ≤ −0.03 against S AND ≥ 40% of K_S's band-weighted gain on the same units;
    2. better than S in ≥ 60% of bands;
    3. neither clean nor crunch worse than S by more than 0.05;
    4. arm A only: not worse than the C′ menu pick by more than 0.01;
    5. arm B only: `controls_pass` (its positive and shuffled-input controls)."""
    use = [u for u in units if finite(u["d"].get(arm), u["d"].get("S"), u["d"].get("K_S"))
           and (arm != "A" or finite(u["d"].get("menu_pick")))]
    rows = part_rows(use, log_vs(arm, "S"))
    ks = part_rows(use, log_vs("K_S", "S"))
    s, k = bw(rows), bw(ks)
    m, km = s["band_weighted_mean"], k["band_weighted_mean"]
    r = {}
    r[1] = m is not None and km is not None and m <= -0.03 + EPS and m <= 0.4 * km + EPS
    r[2] = s["bands"] > 0 and at_least_share(s["bands_negative"], s["bands"], 3, 5)
    by_cls = {c: bw(rows, (c,)) for c in ("clean", "crunch")}
    r[3] = all(v["band_weighted_mean"] is None or v["band_weighted_mean"] <= 0.05 + EPS for v in by_cls.values())
    out = {"arm": arm, "vs_S": s, "K_S_vs_S": k, "share_of_K_S_gain": (m / km if m is not None and km else None),
           "clean": by_cls["clean"], "crunch": by_cls["crunch"], "units": len(use)}
    if arm == "A":
        mp = bw(part_rows(use, log_vs("A", "menu_pick")))
        out["vs_menu_pick"] = mp
        r[4] = mp["band_weighted_mean"] is not None and mp["band_weighted_mean"] <= 0.01 + EPS
    if arm == "B":
        r[5] = bool(controls_pass)
    out["rules"] = {str(i): bool(v) for i, v in r.items()}
    out["passes"] = all(r.values())
    return out


def arm_status(units, arm, *, gate=None, positive=None, data_limited=None):
    """The arm's reading: the declared rule, then amendment 3's sensitivity (Gym Hours GTR 1's
    half-B cells left out; a disagreement on the pass makes the arm undecided), then, for arm B,
    the data-limit reading of a failing arm.

    gate: a reason the arm counts as failed regardless (arm A or C after a failed known-target
    control); its scores are still computed, descriptively. positive: arm B's positive control
    result. data_limited: arm B's `data_limit` result (None: not run)."""
    sens = without_gym_half_b(units)
    ctrl = {}
    if arm == "B":
        ctrl = {"declared": shuffled_control(units), "without_gym_half_b": shuffled_control(sens)}
    pos_ok = bool(positive and positive["passes"])
    declared = arm_rules(units, arm, pos_ok and ctrl["declared"]["passes"] if arm == "B" else None)
    excluded = arm_rules(sens, arm, pos_ok and ctrl["without_gym_half_b"]["passes"] if arm == "B" else None)
    out = {"declared": declared, "without_gym_half_b": excluded}
    if arm == "B":
        out["shuffled_control"] = ctrl
        out["data_limit"] = data_limited
    if gate:
        out["passes"], out["status"] = False, f"failed ({gate}); scores descriptive"
    elif declared["passes"] != excluded["passes"]:
        out["passes"], out["status"] = False, "undecided (amendment 3: Gym Hours GTR 1 half B changes the pass)"
    elif declared["passes"]:
        out["passes"], out["status"] = True, "passes"
    elif arm == "B" and data_limited is None:
        out["passes"], out["status"] = False, "failed (data-limit check not run)"
    elif arm == "B" and data_limited["data_limited"]:
        out["passes"], out["status"] = False, "undecided (data-limited)"
    else:
        out["passes"], out["status"] = False, "failed"
    return out


# --- the readout (ML plan, step 6) -----------------------------------------------------------

NEXT = {1: "Arm B's pipeline is wrong: read arms A and C on their own rules only",
        2: "The optimiser or the search space is wrong: arms A and C count as failed; read arm B alone",
        3: {"C": "C leads: run its 150-render variant, then hand 'model guess + short search' to the product session",
            "B": "B leads: the rebuilt DI is not needed. Grow arm B's bank to about 30k; optionally fine-tune on "
                 "true-DI search labels; then step 7",
            "A": "A leads: hand route 1 to the product session; arm B stays research"},
        4: "The song side is the loss: re-run arm A from the amp track on each part's best-amp cell"}


def readout(units, statuses, positive, known_target):
    """The first matching row wins. statuses: {arm: arm_status(...)} for the arms that ran.
    The leader is the passing arm with the best band-weighted mean against S; a passing arm whose
    paired band-weighted 90% interval against the leader includes 0 (or has none) is tied, and the
    cheapest of the tied arms leads."""
    if positive is not None and not positive["passes"] and not positive["final"]:
        return {"row": None, "result": f"blocked: arm B's positive control {positive['status']}"}
    if positive is not None and not positive["passes"]:
        return {"row": 1, "result": "Arm B's positive control still fails after two re-runs", "next": NEXT[1],
                "arms_A_C": {a: statuses[a]["status"] for a in ("A", "C") if a in statuses}}
    if known_target is not None and known_target["row"] == 1:
        return {"row": 2, "result": "Arm A's control says the search set-up is wrong", "next": NEXT[2],
                "arm_B": statuses["B"]["status"] if "B" in statuses else None}
    passing = [a for a, s in statuses.items() if s["passes"]]
    undecided = sorted(a for a, s in statuses.items() if s["status"].startswith("undecided"))
    if passing:
        mean = {a: statuses[a]["declared"]["vs_S"]["band_weighted_mean"] for a in passing}
        leader = min(passing, key=lambda a: (mean[a], COST[a]))
        tied, paired = [], {}
        for a in passing:
            if a == leader:
                continue
            p = bw(part_rows([u for u in units if finite(u["d"].get(a), u["d"].get(leader))], log_vs(a, leader)))
            paired[a] = p
            if p["lo90"] is None or p["lo90"] <= 0 <= p["hi90"]:
                tied.append(a)
        lead = min([leader] + tied, key=lambda a: COST[a])
        return {"row": 3, "result": "At least one arm passes", "best_mean": leader, "tied_with_best": tied,
                "leader": lead, "paired_vs_best": paired, "next": NEXT[3][lead], "undecided": undecided}
    return {"row": 4, "result": "No arm passes", "next": NEXT[4], "undecided": undecided}


# --- descriptives -----------------------------------------------------------------------------

def single_answer_rows(units, arm):
    """Per part and direction, only the amp whose S is best on the search half (S's own
    search-half score); the arm's log ratio against S there, on the per-part unit."""
    by = {}
    for u in units:
        if finite(u.get("S_search")):
            by.setdefault((u["slug"], u["search"]), []).append(u)
    chosen = [min(us, key=lambda u: (u["S_search"], u["amp"])) for _, us in sorted(by.items())]
    return part_rows(chosen, log_vs(arm, "S"))


def descriptives(units, arm):
    rows = part_rows(units, log_vs(arm, "S"))
    out = {"all": bw(rows),
           "without_musdb_train": bw([r for r in rows if r[0] not in MUSDB_TRAIN_BANDS]),
           "per_amp": {a: bw(part_rows([u for u in units if u["amp"] == a], log_vs(arm, "S")))
                       for a in sorted({u["amp"] for u in units})},
           "single_answer_amp": bw(single_answer_rows(units, arm))}
    if len({b for b, _, _ in rows}) > 1:
        from learn import confirm_run as CR

        out["part_weighted"] = CR.stats([(b, v) for b, c, v in rows])
    return out


# --- reading the stored outputs ---------------------------------------------------------------

def _load(path, missing):
    if not path.exists():
        missing.append(str(path))
        return None
    return json.loads(path.read_text())


def gather(root, kc_root, lt_root, cells, parts, control_cells, half_bank=True):
    """Read every expected output. root: learn/song-settings; kc_root: learn/knob-ceiling;
    lt_root: learn/label-table. cells: (slug, amp, search, held); parts: slug -> {band,
    gain_class}; control_cells: (slug, amp) for arm A's known-target control.
    -> (data, missing paths)."""
    missing = []
    kt = [_load(root / "armA-control" / f"{s}-{a}-result.json", missing) for s, a in control_cells]
    kt_ok = None if any(r is None for r in kt) else known_target_control(kt)
    run_c = kt_ok is not None and kt_ok["outcome"] == "passes"

    preds = _load(root / "armB" / "predictions.json", missing)
    targets = _load(root / "armB" / "control-targets.json", missing)
    pos_units = []
    if preds is not None and targets is not None:
        fold_of = {str(t["i"]): t["fold"] for t in targets}
        for key in sorted(preds["control"], key=int):
            r = _load(root / "armB" / "scores" / f"control-{key}.json", missing)
            if r is None:
                continue
            for h in "AB":                                  # predicted from h, judged on the other half
                held = other(h)
                pos_units.append({"fold": fold_of[key], "target": key, "held": held,
                                  "d": {"target": r["target"][held], "S": r["S"][held],
                                        "pred": r[f"pred{h}"][held], "median": r["median"][held]}})

    units, menus, picks = [], {}, {}
    for slug, amp, search, held in cells:
        p = parts[slug]
        u = {"slug": slug, "band": p["band"], "cls": p["gain_class"], "amp": amp, "search": search,
             "held": held, "d": {}}
        kc = _load(kc_root / "cells" / slug / amp / "result.json", missing)
        if kc is not None:
            run = kc["runs"][search]
            u["S_search"] = kc["menu"][kc["start"]][search]
            u["d"]["S"] = kc["menu"][kc["start"]][held]
            if "skipped" in run:
                u["skipped"] = True
            else:
                u["d"]["K_S"] = run["K_S"]["held"]
                for n in KS_CHECKPOINTS:
                    c = run["K_S"]["curve"]
                    u["d"][f"K_S@{n}"] = c[min(n, len(c)) - 1][2]
        a = _load(root / "armA" / slug / amp / f"{search}.json", missing)
        if a is not None:
            u["d"]["A"] = a["judge"][held]
        if slug not in picks:
            picks[slug] = _load(root / "menupick" / slug / "result.json", missing)
            menus[slug] = _load(lt_root / slug / "menu.json", missing)
        if picks[slug] is not None and menus[slug] is not None:
            u["d"]["menu_pick"] = menus[slug][amp][picks[slug][amp]["pick"][search]]["flat"][held]
        name = f"cell-{slug}_{amp}_{search}.json"
        b = _load(root / "armB" / "scores" / name, missing)
        if b is not None:
            u["d"]["B"] = b["B"][held]
            u["d"]["shuffled"] = [b[k][held] for k in sorted(b) if k.startswith("shuffled")]
            u["d"]["constant"] = b["constant"][held]
            if "amp_track" in b:
                u["d"]["amp_track"] = b["amp_track"][held]
        if half_bank:
            bh = _load(root / "armB" / "scores-half" / name, missing)
            if bh is not None:
                u["d"]["B_half"] = bh["B"][held]
        if run_c:
            c = _load(root / "armC" / slug / amp / f"{search}.json", missing)
            if c is not None:
                u["d"]["C"] = c["judge"][held]
        units.append(u)
    return {"units": units, "positive_units": pos_units, "known_target": kt_ok, "known_target_raw": kt,
            "run_c": run_c}, missing


def assemble(data, attempt=1, half_bank=True):
    """Every rule, the sensitivity and the readout, from `gather`'s data. -> report dict."""
    units, dropped = drop_refused(data["units"])
    kt = data["known_target"]
    pos = positive_control(data["positive_units"], attempt)
    gate_ac = {"set-up wrong": "known-target control: the search set-up is wrong",
               "fails": "known-target control fails"}.get(kt["outcome"])
    statuses = {"A": arm_status(units, "A", gate=gate_ac)}
    if data["run_c"]:
        statuses["C"] = arm_status(units, "C", gate=gate_ac)
    dl = data_limit(units) if half_bank else None
    statuses["B"] = arm_status(units, "B", positive=pos, data_limited=dl)
    rep = {"directions": len(data["units"]), "directions_used": len(units),
           "dropped": [list(d) for d in dropped],
           "known_target_control": kt, "positive_control": pos,
           "arm_C": "run" if data["run_c"] else "not run (arm A's known-target control did not pass)",
           "arms": statuses,
           "descriptive": {a: descriptives(units, a) for a in statuses},
           "K_S": {n: bw(part_rows(units, log_vs(n, "S"))) for n in ("K_S", *(f"K_S@{c}" for c in KS_CHECKPOINTS))},
           "B_vs_constant": bw(part_rows(units, log_vs("B", "constant"))),
           "amp_track_vs_S": bw(part_rows(units, log_vs("amp_track", "S"))),
           "readout": readout(units, statuses, pos, kt)}
    return rep


def _f(x):
    return "n/a" if x is None else f"{x:+.3f}"


def summary(rep):
    kt, pos, ro = rep["known_target_control"], rep["positive_control"], rep["readout"]
    lines = [f"Directions used: {rep['directions_used']} of {rep['directions']} ({len(rep['dropped'])} dropped).",
             f"Arm A's known-target control: {kt['outcome']} (row {kt['row']}, {kt['informative']} of {kt['cells']} "
             f"informative).",
             f"Arm B's positive control (attempt {pos['attempt']}): {pos['status']}; folds passing "
             f"{sum(v['passes'] for v in pos['folds'].values())} of {len(pos['folds'])}."]
    for a, s in rep["arms"].items():
        d = s["declared"]
        lines.append(f"Arm {a}: {s['status']}. Against S {_f(d['vs_S']['band_weighted_mean'])} "
                     f"[{_f(d['vs_S']['lo90'])}, {_f(d['vs_S']['hi90'])}], K_S {_f(d['K_S_vs_S']['band_weighted_mean'])}, "
                     f"better in {d['vs_S']['bands_negative']} of {d['vs_S']['bands']} bands; rules "
                     + ", ".join(f"{k} {'yes' if v else 'no'}" for k, v in d["rules"].items()) + ".")
    if "B" in rep["arms"]:
        sc = rep["arms"]["B"]["shuffled_control"]["declared"]
        lines.append(f"Shuffled-input control: {'passes' if sc['passes'] else 'fails'} "
                     f"({_f(sc['band_weighted_mean'])}, better in {sc['bands_negative']} of {sc['bands']} bands).")
    lines.append(f"Readout: row {ro['row']}, {ro['result']}." + (f" Leader: arm {ro['leader']}." if ro.get("leader") else "")
                 + (f" Next: {ro['next']}." if ro.get("next") else ""))
    return "\n".join(lines)


def report(out_dir=None, attempt=1, half_bank=True):
    from learn import knob_ceiling as K
    from learn import song_settings as SS

    root = SS.OUT
    ps = K.parts()
    cells = SS.cells()
    assert any(s == GYM for s, *_ in cells), GYM
    data, missing = gather(root, K.OUT, K.HOME / "learn/label-table", cells, ps, SS.control_cells(), half_bank)
    if missing:
        print(f"refusing to run: {len(missing)} expected file(s) missing, e.g.", file=sys.stderr)
        for m in missing[:20]:
            print("  " + m, file=sys.stderr)
        return 2
    rep = assemble(data, attempt, half_bank)
    rep["half_bank"] = "used" if half_bank else "not used (--without-half-bank)"
    out = pathlib.Path(out_dir) if out_dir else root / "readout"
    out.mkdir(parents=True, exist_ok=True)
    K._atomic(out / "report.json", rep)
    (out / "summary.txt").write_text(summary(rep) + "\n")
    print(summary(rep))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("report",))
    ap.add_argument("--control-attempt", type=int, default=1,
                    help="arm B's positive control: 1 for the first run, 2–3 after a fix-and-re-run")
    ap.add_argument("--without-half-bank", action="store_true",
                    help="no half-bank scores (armB/scores-half/): a failing arm B then reads "
                         "'failed (data-limit check not run)'")
    ap.add_argument("--out", default=None, help="default: learn/song-settings/readout/")
    a = ap.parse_args(argv)
    return report(a.out, a.control_attempt, not a.without_half_bank)


if __name__ == "__main__":
    sys.exit(main())
