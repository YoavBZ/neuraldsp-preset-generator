#!/usr/bin/env python3
"""Size and power of the listening check's primary (`docs/listening-check-plan.md`).

    python research/listening_check_power.py --listeners 800 --draws 2000

Use at least 2,000 draws: `block_p` seeds its null the same way on every call, as
`score` does, so its Monte Carlo error is shared by every simulated listener and does
not average out over them.

Simulated listeners answer the 32 main trials (16 parts, each heard twice through the
riff in its own style), and each listener's answers go through the scoring code's own
nulls: the chance test alone, and the primary (chance and the song-blind taste) with
the taste fitted per riff, as declared (each riff's parts apart), and fitted once over
all the answers, for comparison. Every listener's answers
are drawn from one seeded generator, so both fits see identical listeners.

The listeners, in the plan's table:
- **random:** each trial's pick uniform over the four.
- **random, same on both riffs:** one uniform pick per part, given on both trials.
- **always a PR12 / a PR12 half the time:** one pick per part, on both trials: a PR12
  candidate (uniform among the part's PR12s), always or with probability one half,
  otherwise uniform over the four.
- **always no drive:** one pick per part, uniform among its candidates with no drive
  pedal on (uniform over the four if none).
- **the least gain (always / half / 70%):** one pick per part: the candidate with no
  drive pedal before one with, then the lowest drive level, then the lowest volume;
  with probability 1, 0.5 or 0.7, otherwise uniform over the four.
- **leans to low gain:** each trial drawn in proportion to exp(-10 (volume + drive)).
- **least gain on the chords parts, a PR12 / random on the line parts.**
- **ear q:** each trial the judge's best (recording band set) with probability q,
  otherwise uniform over the four.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.append(str(PLUGIN_ROOT / "scripts"))

import listening_check as L  # noqa: E402

INPUTS = PLUGIN_ROOT / "docs" / "listening-check-inputs.json"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listeners", type=int, default=800)
    ap.add_argument("--draws", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261006)
    args = ap.parse_args()
    data = json.loads(INPUTS.read_text())
    parts, G = data["parts"], L.G
    F = data["taste_features"]
    feats = L.feature_rows(F, parts)
    centred = {}
    for b in L.BAND_SETS:
        centred[b] = []
        for p in parts:
            logs = [math.log(data["distances"][p][b][g]) for g in G]
            mean = sum(logs) / 4
            centred[b].append([v - mean for v in logs])
    best = [min(range(4), key=lambda j: centred["recording"][k][j]) for k in range(len(parts))]
    styles = [data["styles"][p] for p in parts]

    def least(k):
        f = [F[parts[k]][g] for g in G]
        return min(range(4), key=lambda j: (f[j]["drive_on"], f[j]["drive"], f[j]["volume"], j))

    def among(rng, k, ok):
        allowed = [j for j in range(4) if ok(F[parts[k]][G[j]])]
        return rng.choice(allowed or range(4))

    def both(choose):
        return lambda rng, k: [choose(rng, k)] * 2

    def sometimes(q, choose):
        return both(lambda rng, k: choose(rng, k) if rng.random() < q else rng.randrange(4))

    pr12 = lambda rng, k: among(rng, k, lambda f: f["amp"] == "pr12")  # noqa: E731
    listeners = {
        "random": lambda rng, k: [rng.randrange(4), rng.randrange(4)],
        "random, same on both riffs": both(lambda rng, k: rng.randrange(4)),
        "always a PR12": both(pr12),
        "a PR12 half the time": sometimes(0.5, pr12),
        "always no drive": both(lambda rng, k: among(rng, k, lambda f: not f["drive_on"])),
        "always the least gain": both(lambda rng, k: least(k)),
        "the least gain half the time": sometimes(0.5, lambda rng, k: least(k)),
        "the least gain 70% of the time": sometimes(0.7, lambda rng, k: least(k)),
        "leans to low gain": lambda rng, k: [
            rng.choices(range(4), weights=[math.exp(-10 * (F[parts[k]][g]["volume"]
                                                            + F[parts[k]][g]["drive"]))
                                           for g in G])[0] for _ in L.RIFFS],
        "least gain on chords parts, a PR12 on line parts": both(
            lambda rng, k: least(k) if styles[k] == "chords" else pr12(rng, k)),
        "least gain on chords parts, random on line parts": both(
            lambda rng, k: least(k) if styles[k] == "chords" else rng.randrange(4)),
    }
    for q in (0.2, 0.3, 0.4, 0.6):
        listeners[f"ear {q:.1f}"] = (lambda q: lambda rng, k: [
            best[k] if rng.random() < q else rng.randrange(4) for _ in L.RIFFS])(q)

    n = len(parts)
    uniform = [[None, None]] * n
    print(f"{'listener':44} chance  per-riff  one fit")
    for name, answer in listeners.items():
        rng = random.Random(args.seed)
        chance = per_riff = pooled = 0
        for _ in range(args.listeners):
            picks = [answer(rng, k) for k in range(n)]
            riff_fit = {r: L.taste_weights([feats[p] for p in parts],
                                           [x if styles[k] == r else []
                                            for k, x in enumerate(picks)]) for r in L.RIFFS}
            one_fit = L.taste_weights([feats[p] for p in parts], picks)
            by_riff = [[riff_fit[styles[k]][k]] * 2 for k in range(n)]
            once = [[one_fit[k], one_fit[k]] for k in range(n)]

            def passes(weights):
                return all(L.block_p(list(zip(centred[b], picks, weights)), args.draws) < 0.05
                           for b in L.BAND_SETS)

            if passes(uniform):
                chance += 1
                per_riff += passes(by_riff)
                pooled += passes(once)
        total = args.listeners
        print(f"{name:44} {chance / total:6.3f}  {per_riff / total:8.3f}  {pooled / total:7.3f}",
              flush=True)


if __name__ == "__main__":
    main()
