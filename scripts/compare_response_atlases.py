#!/usr/bin/env python3
"""Compare two response-atlas scale runs on one identical held-out experiment.

    python scripts/compare_response_atlases.py \
      --baseline packs/morgan/response_atlas_pr12_pilot.json \
      --candidate packs/morgan/response_atlas_pr12_1024.json

The command is plugin-free.  It refuses to compare different topologies, probes,
renderer builds, or held-out seeds so that a lower score can be attributed to
atlas density rather than a changed experiment.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(SCRIPT_ROOT))

from _cli import guarded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", required=True, type=pathlib.Path,
                        help="smaller or earlier atlas JSON")
    parser.add_argument("--candidate", required=True, type=pathlib.Path,
                        help="larger or later atlas JSON")
    parser.add_argument("--json", action="store_true",
                        help="print the comparison as JSON")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    from match import atlas

    baseline = atlas.load(args.baseline)
    candidate = atlas.load(args.candidate)
    result = atlas.compare_scale(baseline, candidate)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    for caveat in dict.fromkeys((
            result["baseline_measurement_caveat"],
            result["candidate_measurement_caveat"],
    )):
        if caveat:
            print(f"CAUTION: {caveat}")
    reduction = result["mean_reduction_fraction"]
    median_reduction = result["median_target_reduction_fraction"]
    worst_reduction = result["worst_target_reduction_fraction"]
    print(
        f"{result['baseline_samples']} -> {result['candidate_samples']} atlas points; "
        f"{result['held_out_samples']} held-out targets, seed "
        f"{result['held_out_seed']}, profile {result['profile']}"
    )
    print(
        f"  mean: {result['baseline_atlas_mean']:.3f} -> "
        f"{result['candidate_atlas_mean']:.3f}"
        + ("" if reduction is None else f" ({100 * reduction:.1f}% lower)")
    )
    print(
        f"  median: {result['baseline_atlas_median']:.3f} -> "
        f"{result['candidate_atlas_median']:.3f}"
    )
    print(
        f"  candidate better on {result['candidate_better_targets']}/"
        f"{result['held_out_samples']} targets"
    )
    if median_reduction is not None and worst_reduction is not None:
        print(f"  median target reduction: {100 * median_reduction:.1f}%")
        if worst_reduction < 0:
            print(f"  worst target regression: {-100 * worst_reduction:.1f}%")
        else:
            print(f"  smallest target reduction: {100 * worst_reduction:.1f}%")


if __name__ == "__main__":
    guarded(main)
