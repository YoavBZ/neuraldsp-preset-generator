#!/usr/bin/env python3
"""The amp-reach decision with its minority rule held against a label-permutation null
(`docs/amp-reach-plan.md`, "The minority rule's null").

    python research/amp_reach_null.py --reach-json amp-reach.json --json amp-reach-null.json

Declared after a first run of `research/amp_reach.py` crashed before writing anything,
and before any output of the re-run was read. The minority count (parts where the full joint menu's pick is another
amp's preset and at least 0.150 closer on half B than the tested menu's) can fire when
the amps are interchangeable, because the joint menu is bigger. So the presets of the
joint menu are reassigned to amps at random, keeping each amp's menu size and using one
assignment for every part, 1000 times; the observed count must exceed the null's 95th
percentile under both band sets. The size-matched rule stands as declared.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from _cli import die, guarded
from amp_reach import ADDS_REACH, BAND_SETS, CLEAR, MIN_BANDS, MINORITY, oracle

PERMUTATIONS, QUANTILE = 1000, 0.95


def minority(dist, parts, bands_of, labels, tested, bands):
    """(parts, bands) where the joint pick is another label's and clearly closer."""
    menu = sorted(labels)
    own_menu = [c for c in menu if labels[c] == tested]
    hits = []
    for p in parts:
        _, own = oracle(dist[p], own_menu, bands)
        pick, full = oracle(dist[p], menu, bands)
        if (pick is not None and own is not None and labels[pick] != tested
                and math.log(full / own) <= -CLEAR):
            hits.append(p)
    return len(hits), len({bands_of[p] for p in hits})


def null_quantile(dist, parts, bands_of, labels, tested, bands, seed):
    rng = random.Random(seed)
    names, values = sorted(labels), [labels[c] for c in sorted(labels)]
    counts = []
    for _ in range(PERMUTATIONS):
        shuffled = values[:]
        rng.shuffle(shuffled)
        counts.append(minority(dist, parts, bands_of, dict(zip(names, shuffled)),
                               tested, bands)[0])
    counts.sort()
    return counts[int(QUANTILE * PERMUTATIONS) - 1], counts


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reach-json", type=pathlib.Path, required=True)
    ap.add_argument("--json", type=pathlib.Path)
    args = ap.parse_args()
    from plan_listening_validation import high_gain

    reach = json.loads(args.reach_json.expanduser().read_text())
    if reach["canary_misses"]:
        die(f"the canaries missed, so nothing is read: {reach['canary_misses']}")
    dist, parts = reach["distances"], reach["parts"]
    bands_of = {r["part"]: r["band"] for r in reach["rows"]["sw50r/all"]["recording"]}
    names = sorted({k.split("|")[0] for d in dist.values() for k in d})
    every = {c: c.split(":", 1)[0] for c in names if ":factory:" in c}
    clean = {c: a for c, a in every.items() if not high_gain(c)}
    out = {}
    for key, labels, tested in (("sw50r/all", every, "sw50r"), ("pr12/clean", clean, "pr12")):
        out[key] = {}
        for bands in BAND_SETS:
            n_parts, n_bands = minority(dist, parts, bands_of, labels, tested, bands)
            q95, counts = null_quantile(dist, parts, bands_of, labels, tested, bands,
                                        seed=key)     # the same permutations in both
            denominator = reach["readings"][key][bands]["parts"]   # as amp_reach's rule
            out[key][bands] = {"minority_parts": n_parts, "minority_bands": n_bands,
                               "null_95th": q95, "null_mean": sum(counts) / len(counts),
                               "rule": (n_parts >= MINORITY * denominator
                                        and n_bands >= MIN_BANDS and n_parts > q95)}
    sized = {k: all(reach["readings"][k][b]["sized_joint_vs_tested"] is not None
                    and reach["readings"][k][b]["sized_joint_vs_tested"] <= ADDS_REACH
                    for b in BAND_SETS) for k in out}
    minority_holds = {k: all(out[k][b]["rule"] for b in BAND_SETS) for k in out}
    decision = {"size_matched": sized, "minority_beyond_null": minority_holds,
                "rerun_kill_tests_jointly": any(sized.values()) or any(minority_holds.values())}
    result = {"minority": out, "decision": decision}
    print(json.dumps(result, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(result, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
