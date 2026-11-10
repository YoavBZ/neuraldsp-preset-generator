"""Amp choice on GOAT, C2b (`docs/full-controls-plan.md`, "C2b in detail"; ledger `pipeline-fix` `phase_c2b`). GOAT
has one forced amp a unit, so its rows carry no amp-choice label. C2b runs the same `K.space` main stage that made
GOAT's stored labels (`pipeline_fix.search_units`, 52 evaluations, seed 20261013, the class's S, the unit's halves and
lag) on each labelled unit's two other amps, and labels the unit's amp as the argmin of the three like-for-like
search-half bests, as `full_controls.bks_amp_choice` does on BKS. Development only, the true DI, no model, no training.

    .venv/bin/python -m learn.full_controls_c2b c2b-draw                 # the records (zero renders)
    .venv/bin/python -m learn.full_controls_c2b c2b-search --shard 0/3   # the searches (renders; at most 3 shards)
    .venv/bin/python -m learn.full_controls_c2b c2b-report               # the amp labels and their read (zero renders)

The pure parts (the records, the order and shards, the amp choice, its guard and the read's rows) are unit-tested;
the search renders and is not.
"""

from __future__ import annotations

import argparse
import json
import math
import time

PHASE = "phase_c2b"
LAG_PHASE = "phase_5c"               # GOAT's stored lags (and S's fresh renders on all three amps) are 5C's
SEARCH_SUB = "search-c2b"            # under the GOAT folder
START_TOL = 0.005                    # a first evaluation not bit-identical to S's stored render: within this, flagged
MISS_GUARD = (5, 10)                 # stop a shard when 5 of the first 10 records it reaches miss S's stored render
AMP_GUARD = (3, 5)                   # ... or when 3 of one amp's first 5 do (`pipeline_fix.systematic_miss`)
QUIET_DBFS = -57.0                   # J0's silence floor (-60) plus 3 dB, like for like on all three amps (not C2's
                                     # min(-57, start) - 0.05 rule: here every search starts from S)
QUIET_SENSITIVITY_DBFS = -54.0       # the report's zero-render sensitivity check of that floor
EVALS = 52                           # arm A's main stage (`arm_a_levers.main_stage`)
PER_RECORD = 1 + EVALS               # one priming render and the evaluations; the lags are stored


def shard(s):
    k, n = (int(v) for v in s.split("/"))
    if not 0 <= k < n:
        raise argparse.ArgumentTypeError("--shard k/n with 0 <= k < n")
    return k, n


# --- records (zero renders) -------------------------------------------------------------------------------------------

def c2b_records(stored, amps):
    """GOAT's stored labelled records -> C2b's: for each unit, every amp of `amps` but its forced one, with the stored
    record's halves, class and item; sorted by key ("unit|amp"). Refuses a unit stored twice."""
    seen, out = set(), []
    for r in stored:
        if r["unit"] in seen:
            raise SystemExit(f"{r['unit']}: stored twice")
        seen.add(r["unit"])
        for a in amps:
            if a == r["amp"]:
                continue
            out.append({"key": f"{r['unit']}|{a}", "unit": r["unit"], "amp": a, "forced_amp": r["amp"],
                        "search": r["search"], "held": r["held"], "cls": r["cls"], "item": r["item"]})
    return sorted(out, key=lambda q: q["key"])


def shard_records(records, k, n):
    """Shard k of n: a round robin over the records in key order."""
    return [r for j, r in enumerate(sorted(records, key=lambda q: q["key"])) if j % n == k]


# --- the amp choice (zero renders) ------------------------------------------------------------------------------------

def _pos(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v > 0 else None


def usable(r, floor=QUIET_DBFS):
    """A record's label counts for the amp choice: a label, a finite search-half best, and a best not near silence
    (peak at or above `floor`). The same rule for the stored forced-amp records and C2b's, so the three amps are
    compared like for like. -> bool."""
    if r is None or r.get("label") is None:
        return False
    best = r.get("best") or {}
    if _pos((best.get("judge") or {}).get(r["search"])) is None:
        return False
    peak = best.get("peak_dbfs")
    return peak is not None and float(peak) >= floor


def quiet(r, floor=QUIET_DBFS):
    """A label that the near-silence rule alone keeps out of the amp choice."""
    return r is not None and r.get("label") is not None and not usable(r, floor) and usable(r, -math.inf)


def withheld(by_amp):
    """A unit whose three records are not all there, or one of which was refused (a technical gap, not evidence):
    no amp label. -> why, or None."""
    if any(r is None for r in by_amp.values()):
        return "a record is missing"
    if any(r.get("refused") for r in by_amp.values()):
        return "a record was refused"
    return None


def amp_choice(by_amp, floor=QUIET_DBFS):
    """One unit's records {amp: record or None} -> the amp whose usable label has the lowest best.judge[search]
    (ties to the first in sorted order, as `full_controls.bks_amp_choice`), or None."""
    ok = {a: r for a, r in by_amp.items() if usable(r, floor)}
    if not ok:
        return None
    return min(sorted(ok), key=lambda a: float(ok[a]["best"]["judge"][ok[a]["search"]]))


def amp_read(by_amp, chosen):
    """Every-control stage 0b's reading for one unit: log(held half of the chosen amp) less the mean log held half over
    the usable amps with a finite held half; None when the chosen amp has none or only one amp is usable."""
    logs = {}
    for a, r in by_amp.items():
        if usable(r):
            v = _pos(r["best"]["judge"].get(r["held"]))
            if v is not None:
                logs[a] = math.log(v)
    if chosen not in logs or len(logs) < 2:
        return None
    return logs[chosen] - sum(logs.values()) / len(logs)


def held_best(by_amp):
    """The usable amp with the lowest held half, or None."""
    ok = {a: _pos(r["best"]["judge"].get(r["held"])) for a, r in by_amp.items() if usable(r)}
    ok = {a: v for a, v in ok.items() if v is not None}
    return min(sorted(ok), key=lambda a: ok[a]) if ok else None


def report_rows(units, clustered):
    """units: [{unit, item, cls, forced_amp, by_amp: {amp: record or None}}] -> the amp labels and the read's rows:
    the chosen amp against a blind one (clustered by item), all and by class; how often the chosen amp is also the
    held half's best; how often it is the forced amp; and the forced amp's own reading, for scale."""
    labels, rows, forced_rows = {}, [], []
    counts = {"units": len(units), "withheld": 0, "chosen": 0, "no_choice": 0, "chosen_is_forced": 0,
              "chosen_is_held_best": 0, "three_usable": 0, "read": 0, "read_dropped_held_nonfinite": 0,
              "read_dropped_one_amp": 0, "changed_at_sensitivity": 0}
    by_amp_chosen = {}
    for u in units:
        by = u["by_amp"]
        w = withheld(by)
        if w:
            counts["withheld"] += 1
            labels[u["unit"]] = {"amp": None, "withheld": w}
            continue
        c = amp_choice(by)
        counts["changed_at_sensitivity"] += amp_choice(by, QUIET_SENSITIVITY_DBFS) != c
        nu = sum(1 for r in by.values() if usable(r))
        counts["three_usable"] += nu == 3
        if c is None:
            counts["no_choice"] += 1
            labels[u["unit"]] = {"amp": None, "n_usable": 0}
            continue
        counts["chosen"] += 1
        counts["chosen_is_forced"] += c == u["forced_amp"]
        counts["chosen_is_held_best"] += c == held_best(by)
        cell = by_amp_chosen.setdefault(u["forced_amp"], {})
        cell[c] = cell.get(c, 0) + 1
        labels[u["unit"]] = {"amp": c, "forced_amp": u["forced_amp"], "n_usable": nu,
                             "search": {a: (r["best"]["judge"][r["search"]] if usable(r) else None)
                                        for a, r in sorted(by.items())}}
        v = amp_read(by, c)
        if v is not None:
            counts["read"] += 1
            rows.append((u["item"], u["unit"], u["cls"], v))
        elif nu < 2:
            counts["read_dropped_one_amp"] += 1
        else:
            counts["read_dropped_held_nonfinite"] += 1
        fv = amp_read(by, u["forced_amp"])
        if fv is not None:
            forced_rows.append((u["item"], u["unit"], u["cls"], fv))

    def cl(rs):
        return clustered([(i, p, v) for i, p, _, v in rs]) if rs else None

    chosen_totals = {}
    for cell in by_amp_chosen.values():
        for a, n in cell.items():
            chosen_totals[a] = chosen_totals.get(a, 0) + n
    return {"labels": labels, "counts": counts, "chosen_by_amp": chosen_totals,
            "chosen_by_forced_amp": {a: dict(sorted(c.items())) for a, c in sorted(by_amp_chosen.items())},
            "chosen_minus_blind": {"all": cl(rows), **{k: cl([q for q in rows if q[2] == k]) for k in ("clean", "crunch")}},
            "forced_minus_blind": {"all": cl(forced_rows),
                                   **{k: cl([q for q in forced_rows if q[2] == k]) for k in ("clean", "crunch")}}}


# --- commands ---------------------------------------------------------------------------------------------------------

def c2b_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "c2b"


def search_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / P.GOAT_DIR / SEARCH_SUB


def fname(key):
    return key.replace("/", "__")


def cmd_draw(_args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    path = c2b_dir() / "records.json"
    if path.exists():
        raise SystemExit(f"{path} exists: the records are drawn once")
    stored, _, off = P.goat_labels()
    recs = c2b_records(stored, P.AMPS3)
    P.save(path, {"phase": PHASE, "records": recs, "stored_units": len(stored), "lag_refused": sorted(off),
                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("C2B DRAW", len(stored), "units,", len(recs), "records; renders at most", len(recs) * PER_RECORD, flush=True)


def cmd_search(args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    plan = json.loads((c2b_dir() / "records.json").read_text())
    k, n = args.shard
    mine = shard_records(plan["records"], k, n)
    units = {u["unit"]: u for u in P.goat_units()}
    prts, halves = [], {}
    for r in mine:
        u = units[r["unit"]]
        if u["amp"] != r["forced_amp"] or u["cls"] != r["cls"]:
            raise SystemExit(f"{r['key']}: the unit's forced amp or class no longer fits the draw")
        prts.append(dict(u, amp=r["amp"]))
        halves[r["unit"]] = r["search"]
    renders = P.search_units(prts, P.out_dir() / P.GOAT_DIR, PHASE, halves, set(), False, sdir=search_dir(),
                             lag_phase=LAG_PHASE, first_tol=START_TOL, miss_guard=MISS_GUARD, amp_guard=AMP_GUARD,
                             lags_stored=True)
    print(f"C2B SEARCH DONE {k}/{n}: {renders} renders", flush=True)


def cmd_report(_args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    plan = json.loads((c2b_dir() / "records.json").read_text())
    stored, _, _ = P.goat_labels()
    by_unit = {r["unit"]: r for r in stored}
    new = {}
    for r in plan["records"]:
        q = search_dir() / f"{fname(r['key'])}.json"
        new[r["key"]] = json.loads(q.read_text()) if q.exists() else None
    missing = [k for k, v in new.items() if v is None]
    written = [v for v in new.values() if v is not None]
    out = {"phase": PHASE, "records": len(plan["records"]), "written": len(written), "missing": missing,
           "complete": not missing,
           "refused": sorted(v["unit"] + "|" + v["amp"] for v in written if v.get("refused")),
           "fallbacks": sorted(v["unit"] + "|" + v["amp"] for v in written
                               if v.get("label") is None and not v.get("refused")),
           "quiet": sorted([v["unit"] + "|" + v["amp"] for v in written if quiet(v)]
                           + [s["unit"] + "|" + s["amp"] + " (stored)" for s in stored if quiet(s)]),
           "sha_differs": sum(1 for v in written if (v.get("s_first") or {}).get("sha_differs")),
           "quiet_dbfs": QUIET_DBFS, "sensitivity_dbfs": QUIET_SENSITIVITY_DBFS,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    if missing:                                    # labels only from complete sets
        out["labels"] = None
        print(f"C2B REPORT: {len(missing)} of {len(plan['records'])} records missing; no labels written", flush=True)
    else:
        units = []
        for unit, s in sorted(by_unit.items()):
            by = {s["amp"]: s}
            for a in P.AMPS3:
                if a != s["amp"]:
                    by[a] = new[f"{unit}|{a}"]
            units.append({"unit": unit, "item": s["item"], "cls": s["cls"], "forced_amp": s["amp"], "by_amp": by})
        out.update(report_rows(units, P.clustered))
    P.save(c2b_dir() / "report.json", out)
    print(json.dumps({k: out.get(k) for k in ("complete", "counts", "chosen_by_amp", "chosen_minus_blind",
                                              "forced_minus_blind", "written", "refused", "fallbacks", "quiet",
                                              "sha_differs")}, indent=1, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("c2b-draw").set_defaults(fn=cmd_draw)
    s = sub.add_parser("c2b-search")
    s.add_argument("--shard", type=shard, default=(0, 1))
    s.set_defaults(fn=cmd_search)
    sub.add_parser("c2b-report").set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
