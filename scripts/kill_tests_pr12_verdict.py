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
  common pick no more than half of its picks. Every count is out of all the parts the
  test should score (its eligible parts that have a lag), ties included; a part the
  judge dropped, or the recogniser made no pick for, counts as not closer.

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


def k1_reading(rows, expected=None):
    m = band_median(rows, "oracle")
    scored = {r["part"] for r in rows if r.get("oracle") is not None}
    out = {"oracle_band_median": m, "parts": len(scored),
           "bands": len({r["band"] for r in rows if r.get("oracle") is not None})}
    if expected is not None:
        out["dropped_parts"] = sorted(set(expected) - scored)
    out["pass"] = m is not None and m <= K1_LINE
    return out


def k3_reading(rows, expected=None):
    """The K3 counts, out of `expected` parts when given (a part without a row is
    not closer), else out of the rows."""
    n = len(expected) if expected is not None else len(rows)
    m = band_median(rows, "model")
    closer = sum(r["model"] < 0 for r in rows)
    shuffled = sum(1.0 if r["model_vs_shuffled"] < 0 else 0.5 if r["model_vs_shuffled"] == 0
                   else 0.0 for r in rows)
    constant = sum(r["model_vs_constant"] < 0 for r in rows)
    picks = collections.Counter(r["pick"] for r in rows)
    share = max(picks.values()) / len(rows) if rows else None
    out = {"parts": n, "rows": len(rows), "band_median_vs_templateR": m,
           "closer_than_templateR": closer,
           "better_than_shuffled_ties_half": shuffled, "closer_than_constant": constant,
           "constant_ties": sum(r["model_vs_constant"] == 0 for r in rows),
           "distinct_picks": len(picks), "most_common_pick_share": share}
    if expected is not None:
        out["dropped_parts"] = sorted(set(expected) - {r["part"] for r in rows})
    out["pass"] = bool(n and m is not None and m < CLEAR_CUT and closer > n / 2
                       and shuffled > n / 2 and constant > n / 2 and share is not None
                       and share <= 0.5)
    return out


def verdict(k, judge):
    no_lag = set(judge.get("parts_without_lag") or {})
    k1_expected = sorted(set(judge["k1_parts"]) - no_lag) if "k1_parts" in judge else None
    k3_expected = sorted(set(judge["k3_parts"]) - no_lag) if "k3_parts" in judge else None
    k1 = {b: k1_reading(judge["k1"][b]["rows"], k1_expected) for b in BAND_SETS}
    k3 = {name: {b: k3_reading(judge["k3"][b][name]["rows"], k3_expected)
                 for b in BAND_SETS}
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
    if pathlib.Path(judge["k_json"]).expanduser().resolve() != \
            args.k_json.expanduser().resolve():
        raise SystemExit("the judge's output was scored from another K1-K2 output")
    derived = json.loads((pathlib.Path(k["panel"]).expanduser() / "index.json")
                         .read_text()).get("derived_from")
    if derived:
        import hashlib

        source = pathlib.Path(derived["source_panel"]).expanduser() / "index.json"
        if hashlib.sha256(source.read_bytes()).hexdigest() != derived["source_index_sha256"]:
            raise SystemExit("the source panel's index changed since the panel was derived")
        if k["factory_presets"] != len(derived["factory_presets"]):
            raise SystemExit("the K1-K2 output's menu is not the derived panel's")
    out = verdict(k, judge)
    import hashlib
    import subprocess

    out["inputs"] = {str(path): hashlib.sha256(path.expanduser().read_bytes()).hexdigest()
                     for path in (args.k_json, args.k_judge_json)}
    out["commit"] = subprocess.run(["git", "-C", str(pathlib.Path(__file__).parent), "rev-parse",
                                    "HEAD"], capture_output=True, text=True).stdout.strip()
    print(json.dumps(out, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
