#!/usr/bin/env python3
"""The verdict of `docs/kill-tests-pr12-plan.md`, from the kill-test outputs.

    python scripts/kill_tests_pr12_verdict.py --k-json k-pr12-clean.json \\
        --k-judge-json k-judge-pr12-clean.json --json verdict-pr12-clean.json

Committed before any of those outputs existed. The scripts' own `pass`, `verdict`
and `gate_open` fields apply the SW50R declaration (ALM required, ties half, log 0.9)
and are not this plan's verdict. This one uses the judge's two band sets only:

- K1: the oracle's median of band medians against template+R, unrounded, ≤ log 0.75
  under both band sets.
- K2: as declared, from the K1–K2 output (`k2_pass`; ALM's regret, 3× chance top-1).
- K3, per recogniser, under both band sets: the median of band medians of the pick
  against template+R, unrounded, below −0.150 (which also meets log 0.9); closer than
  template+R on more than half its parts; better than the shuffled control on more
  than half (a tie counts half, as declared); closer than the constant on more than
  half (a tie counts as not closer, as the declaration's text says); and its most
  common pick no more than half of its picks. Every count is out of all the
  recogniser's rows, ties included.

The gate is "passes on clean PR12" only if K1, K2 and K3 pass.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import guarded

BAND_SETS = ("recording", "union")
K1_LINE = math.log(0.75)
CLEAR_CUT = -0.150


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--k-json", type=pathlib.Path, required=True)
    ap.add_argument("--k-judge-json", type=pathlib.Path, required=True)
    ap.add_argument("--json", type=pathlib.Path)
    return ap


def band_median(rows, key):
    """The unrounded median over bands of each band's median of `key`."""
    by = collections.defaultdict(list)
    for r in rows:
        if r.get(key) is not None:
            by[r["band"]].append(r[key])
    vals = [statistics.median(v) for v in by.values()]
    return statistics.median(vals) if vals else None


def k1_reading(rows):
    m = band_median(rows, "oracle")
    return {"oracle_band_median": m, "pass": m is not None and m <= K1_LINE}


def k3_reading(rows):
    n = len(rows)
    m = band_median(rows, "model")
    closer = sum(r["model"] < 0 for r in rows)
    shuffled = sum(1.0 if r["model_vs_shuffled"] < 0 else 0.5 if r["model_vs_shuffled"] == 0
                   else 0.0 for r in rows)
    constant = sum(r["model_vs_constant"] < 0 for r in rows)
    picks = collections.Counter(r["pick"] for r in rows)
    share = max(picks.values()) / n if n else 1.0
    out = {"parts": n, "band_median_vs_templateR": m, "closer_than_templateR": closer,
           "better_than_shuffled_ties_half": shuffled, "closer_than_constant": constant,
           "constant_ties": sum(r["model_vs_constant"] == 0 for r in rows),
           "distinct_picks": len(picks), "most_common_pick_share": share}
    out["pass"] = bool(n and m is not None and m < CLEAR_CUT and closer > n / 2
                       and shuffled > n / 2 and constant > n / 2 and share <= 0.5)
    return out


def verdict(k, judge):
    k1 = {b: k1_reading(judge["k1"][b]["rows"]) for b in BAND_SETS}
    k3 = {name: {b: k3_reading(judge["k3"][b][name]["rows"]) for b in BAND_SETS}
          for name in judge["k3"][BAND_SETS[0]]}
    out = {"k1": {**k1, "pass": all(r["pass"] for r in k1.values())},
           "k2": {"pass": bool(k["k2_pass"])},
           "k3": {"by_recogniser": {n: {**r, "pass": all(x["pass"] for x in r.values())}
                                    for n, r in k3.items()}}}
    out["k3"]["pass"] = any(r["pass"] for r in out["k3"]["by_recogniser"].values())
    out["passes_on_clean_pr12"] = out["k1"]["pass"] and out["k2"]["pass"] and out["k3"]["pass"]
    return out


def main():
    args = build_parser().parse_args()
    k = json.loads(args.k_json.expanduser().read_text())
    judge = json.loads(args.k_judge_json.expanduser().read_text())
    if pathlib.Path(k["panel"]).expanduser().resolve() != \
            pathlib.Path(judge["panel"]).expanduser().resolve():
        raise SystemExit("the two outputs are for different panels")
    out = verdict(k, judge)
    print(json.dumps(out, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
