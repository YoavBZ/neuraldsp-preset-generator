#!/usr/bin/env python3
"""Acceptable amps per recording, and distinct answers per menu (`docs/quick-checks-plan.md`).

    python scripts/reach_sets.py --reach-json ~/ndsp-presets/runs/kill/amp-reach.json \\
        --json reach-sets.json

Reads the judge distances `scripts/amp_reach.py` stored (every factory preset of the
three Morgan amps against each part's amp track; half A, half B and 1.0-10 s; both band
sets). Nothing is rendered or re-scored.

1. **Acceptable amps.** Per part, each amp's expected half-B distance from the half-A
   oracle over a random subset of its menu, all amps at one size (exact, from ranks).
   An amp is acceptable when that is within 0.150 (log) of the best amp's.
2. **Distinct answers.** Two presets of one menu are indistinguishable as answers when,
   on at least two thirds of the parts, the judge's full-window distances to the amp
   track differ by less than 0.150 (log). Complete-linkage clustering by that relation
   counts the menu's classes.
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

from _cli import die, guarded

AMPS = ("ac20", "pr12", "sw50r")
BAND_SETS = ("recording", "union")
CLEAR = 0.150
SAME_ON = 2 / 3
ONE_AMP = 0.5             # a single amp label if one amp alone is acceptable on half the parts
FEW_CLASSES = 5           # a menu "collapses" at this many classes or fewer


def expected_oracle(d, menu, bands, size):
    """Exact expected half-B distance of the half-A oracle over a random `size`-subset:
    rank k (from 1) on half A wins with C(n-k, size-1) / C(n, size)."""
    menu = sorted((c for c in menu if d.get(f"{c}|A|{bands}") is not None
                   and d.get(f"{c}|B|{bands}") is not None),
                  key=lambda c: (d[f"{c}|A|{bands}"], c))
    n = len(menu)
    if n < size:
        return None
    total = math.comb(n, size)
    return sum(math.comb(n - k, size - 1) / total * d[f"{c}|B|{bands}"]
               for k, c in enumerate(menu, start=1) if n - k >= size - 1)


def acceptable(d, menus, bands):
    """{amp: within CLEAR of the best} for one part, menus matched in size."""
    size = min(len(m) for m in menus.values())
    score = {a: expected_oracle(d, menus[a], bands, size) for a in AMPS}
    if any(v is None for v in score.values()):
        return None
    best = min(score.values())
    return {a: math.log(v / best) <= CLEAR for a, v in score.items()}


def classes(dist, parts, menu, bands):
    """Complete-linkage classes of `menu`: a cluster joins another only if every pair
    across them is indistinguishable (|log ratio| < CLEAR on >= SAME_ON of the parts)."""
    def same(a, b):
        votes = [abs(math.log(dist[p][f"{a}|full|{bands}"] / dist[p][f"{b}|full|{bands}"]))
                 < CLEAR for p in parts
                 if dist[p].get(f"{a}|full|{bands}") and dist[p].get(f"{b}|full|{bands}")]
        return bool(votes) and sum(votes) / len(votes) >= SAME_ON

    pair = {(a, b): same(a, b) for i, a in enumerate(menu) for b in menu[i + 1:]}
    linked = lambda a, b: pair.get((a, b), pair.get((b, a)))   # noqa: E731
    clusters = [[c] for c in menu]
    merged = True
    while merged:
        merged = False
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                if all(linked(a, b) for a in clusters[i] for b in clusters[j]):
                    clusters[i] += clusters.pop(j)
                    merged = True
                    break
            if merged:
                break
    return sorted(clusters, key=len, reverse=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reach-json", type=pathlib.Path, required=True)
    ap.add_argument("--json", type=pathlib.Path)
    args = ap.parse_args()
    from plan_listening_validation import high_gain

    reach = json.loads(args.reach_json.expanduser().read_text())
    if reach["canary_misses"]:
        die("the amp-reach canaries missed")
    dist, parts = reach["distances"], reach["parts"]
    band_of = {r["part"]: r["band"] for r in reach["rows"]["sw50r/all"]["recording"]}
    names = sorted({k.split("|")[0] for d in dist.values() for k in d})
    every = {a: [c for c in names if c.startswith(f"{a}:factory:")] for a in AMPS}
    clean = {a: [c for c in every[a] if not high_gain(c)] for a in AMPS}

    out = {"acceptable_amps": {}, "classes": {}}
    for menu_name, menus in (("clean", clean), ("all", every)):
        for bands in BAND_SETS:
            rows = {p: acceptable(dist[p], menus, bands) for p in parts}
            counts = collections.Counter(sum(r.values()) for r in rows.values() if r)
            n = sum(counts.values())
            one = counts.get(1, 0)
            out["acceptable_amps"][f"{menu_name}/{bands}"] = {
                "size_matched_to": min(len(m) for m in menus.values()),
                "parts": n, "amps_acceptable_count": dict(sorted(counts.items())),
                "one_amp_parts": one,
                "one_amp_bands": len({band_of[p] for p, r in rows.items()
                                      if r and sum(r.values()) == 1}),
                "amp_acceptable_share": {a: sum(r[a] for r in rows.values() if r) / n
                                         for a in AMPS},
                "rows": rows}
    single = all(out["acceptable_amps"][f"clean/{b}"]["one_amp_parts"]
                 >= ONE_AMP * out["acceptable_amps"][f"clean/{b}"]["parts"] for b in BAND_SETS)
    out["amp_label"] = "single amp" if single else "set of acceptable amps"

    for key, menu in (("pr12/clean", clean["pr12"]), ("sw50r/all", every["sw50r"]),
                      ("ac20/all", every["ac20"])):
        out["classes"][key] = {}
        for bands in BAND_SETS:
            found = classes(dist, parts, menu, bands)
            out["classes"][key][bands] = {"menu": len(menu), "classes": len(found),
                                          "largest": len(found[0]), "members": found}
    collapse = all(out["classes"]["pr12/clean"][b]["classes"] <= FEW_CLASSES
                   for b in BAND_SETS)
    out["pr12_clean_collapses"] = collapse
    brief = {"amp_label": out["amp_label"], "pr12_clean_collapses": collapse,
             "acceptable_amps": {k: {kk: vv for kk, vv in v.items() if kk != "rows"}
                                 for k, v in out["acceptable_amps"].items()},
             "classes": {k: {b: {kk: vv for kk, vv in r.items() if kk != "members"}
                             for b, r in v.items()} for k, v in out["classes"].items()}}
    print(json.dumps(brief, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
