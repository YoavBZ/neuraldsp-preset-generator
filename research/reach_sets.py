#!/usr/bin/env python3
"""Acceptable amps per recording, and distinct answers per menu (`docs/quick-checks-plan.md`).

    python research/reach_sets.py --reach-json ~/ndsp-presets/runs/kill/amp-reach.json \\
        --json reach-sets.json

Reads the judge distances `research/amp_reach.py` stored (every factory preset of the
three Morgan amps against each part's amp track; half A, half B and 1.0-10 s; both band
sets). Nothing is rendered or re-scored. Shares of parts are weighted by band (each band
counts once, its parts sharing its weight).

1. **Acceptable amps.** Per part, each amp's expected distance from the half-A oracle
   scored on half B, and from the half-B oracle scored on half A, averaged, over a random
   subset of its menu, every amp at one size (exact, from ranks). An amp is acceptable
   when that is within 0.150 (log) of the best amp's.
2. **Distinct answers.** On the parts where the track separates the menu (its presets'
   full-window log distances span at least 0.300), the dissimilarity of two presets is
   the band-weighted share of those parts where their distances to the amp track differ
   by 0.150 (log) or more. Complete linkage (scipy) cut at 1/3 counts the classes.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import pathlib
import random
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from _cli import die, guarded

AMPS = ("ac20", "pr12", "sw50r")
BAND_SETS = ("recording", "union")
CLEAR = 0.150
SPAN = 2 * CLEAR          # a part separates a menu when its distances span this much
APART = 1 / 3             # classes are cut at this band-weighted share of separating parts
ONE_AMP, MIN_BANDS = 0.5, 3
FEW_CLASSES = 5
SUBSETS = 200             # SW50R's size-matched class count, over random 21-preset menus


def expected_oracle(d, menu, choose, score, bands, size):
    """Exact expected `score`-half distance of the `choose`-half oracle over a random
    `size`-subset: rank k (from 1) wins with C(n-k, size-1) / C(n, size)."""
    menu = sorted((c for c in menu if d.get(f"{c}|{choose}|{bands}") is not None
                   and d.get(f"{c}|{score}|{bands}") is not None),
                  key=lambda c: (d[f"{c}|{choose}|{bands}"], c))
    n = len(menu)
    if n < size:
        return None
    total = math.comb(n, size)
    return sum(math.comb(n - k, size - 1) / total * d[f"{c}|{score}|{bands}"]
               for k, c in enumerate(menu, start=1) if n - k >= size - 1)


def acceptable(d, menus, bands):
    """{amp: within CLEAR of the best} for one part, menus matched in size, both halves."""
    size = min(len(m) for m in menus.values())
    score = {}
    for a in AMPS:
        ab = expected_oracle(d, menus[a], "A", "B", bands, size)
        ba = expected_oracle(d, menus[a], "B", "A", bands, size)
        if ab is None or ba is None:
            return None
        score[a] = (ab + ba) / 2
    best = min(score.values())
    return {a: math.log(v / best) <= CLEAR for a, v in score.items()}


def band_weighted_share(flags, band_of):
    """The share of parts where `flags[part]` is true, each band weighing one."""
    by = collections.defaultdict(list)
    for p, f in flags.items():
        by[band_of[p]].append(bool(f))
    return sum(sum(v) / len(v) for v in by.values()) / len(by) if by else 0.0


def classes(dist, parts, band_of, menu, bands):
    """(classes, separating parts): complete-linkage classes of `menu` on the parts whose
    full-window log distances to the amp track span at least SPAN."""
    import numpy as np
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    logs = {p: {c: math.log(dist[p][f"{c}|full|{bands}"]) for c in menu} for p in parts}
    used = [p for p in parts if max(logs[p].values()) - min(logs[p].values()) >= SPAN]
    if len(menu) < 2 or not used:
        return [list(menu)], used
    n = len(menu)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            D[i, j] = D[j, i] = band_weighted_share(
                {p: abs(logs[p][menu[i]] - logs[p][menu[j]]) >= CLEAR for p in used}, band_of)
    # A hair over the cut, so a share of exactly 1/3 computed as a float sum still joins.
    labels = fcluster(linkage(squareform(D, checks=False), "complete"), APART + 1e-9,
                      criterion="distance")
    found = collections.defaultdict(list)
    for c, label in zip(menu, labels):
        found[label].append(c)
    return sorted(found.values(), key=len, reverse=True), used


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


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

    out = {"inputs": {str(args.reach_json): _sha(args.reach_json.expanduser())},
           "commit": subprocess.run(["git", "-C", str(pathlib.Path(__file__).parent),
                                     "rev-parse", "HEAD"], capture_output=True,
                                    text=True).stdout.strip(),
           "acceptable_amps": {}, "classes": {}}
    for menu_name, menus in (("clean", clean), ("all", every)):
        for bands in BAND_SETS:
            rows = {p: acceptable(dist[p], menus, bands) for p in parts}
            rows = {p: r for p, r in rows.items() if r}
            one = {p: sum(r.values()) == 1 for p, r in rows.items()}
            out["acceptable_amps"][f"{menu_name}/{bands}"] = {
                "size_matched_to": min(len(m) for m in menus.values()), "parts": len(rows),
                "amps_acceptable_count": dict(sorted(collections.Counter(
                    sum(r.values()) for r in rows.values()).items())),
                "one_amp_share_band_weighted": band_weighted_share(one, band_of),
                "one_amp_bands": len({band_of[p] for p, v in one.items() if v}),
                "amp_acceptable_share_band_weighted": {
                    a: band_weighted_share({p: r[a] for p, r in rows.items()}, band_of)
                    for a in AMPS},
                "rows": rows}
    single = all(out["acceptable_amps"][f"clean/{b}"]["one_amp_share_band_weighted"]
                 >= ONE_AMP - 1e-9
                 and out["acceptable_amps"][f"clean/{b}"]["one_amp_bands"] >= MIN_BANDS
                 for b in BAND_SETS)
    out["amp_label"] = "single amp" if single else "set of acceptable amps"

    for key, menu in (("pr12/clean", clean["pr12"]), ("sw50r/all", every["sw50r"]),
                      ("ac20/all", every["ac20"])):
        out["classes"][key] = {}
        for bands in BAND_SETS:
            found, used = classes(dist, parts, band_of, menu, bands)
            out["classes"][key][bands] = {"menu": len(menu), "classes": len(found),
                                          "largest": len(found[0]), "separating_parts": len(used),
                                          "members": found}
    rng = random.Random("sw50r-21")
    sized = {}
    for bands in BAND_SETS:
        counts = [len(classes(dist, parts, band_of,
                              sorted(rng.sample(every["sw50r"], len(clean["pr12"]))),
                              bands)[0]) for _ in range(SUBSETS)]
        sized[bands] = sum(counts) / len(counts)
    out["sw50r_21_preset_mean_classes"] = sized
    pr12 = all(out["classes"]["pr12/clean"][b]["classes"] <= FEW_CLASSES for b in BAND_SETS)
    sw50r = all(sized[b] <= FEW_CLASSES for b in BAND_SETS)
    out["pr12_clean_collapses"], out["sw50r_collapses_at_21"] = pr12, sw50r
    # The plan's rule, per band set: PR12 collapses there and SW50R does not.
    out["identifiability_explains_pr12"] = all(
        out["classes"]["pr12/clean"][b]["classes"] <= FEW_CLASSES and sized[b] > FEW_CLASSES
        for b in BAND_SETS)
    brief = {k: v for k, v in out.items() if k not in ("acceptable_amps", "classes")}
    brief["acceptable_amps"] = {k: {kk: vv for kk, vv in v.items() if kk != "rows"}
                                for k, v in out["acceptable_amps"].items()}
    brief["classes"] = {k: {b: {kk: vv for kk, vv in r.items() if kk != "members"}
                            for b, r in v.items()} for k, v in out["classes"].items()}
    print(json.dumps(brief, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
