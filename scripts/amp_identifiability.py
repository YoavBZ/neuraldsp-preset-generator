#!/usr/bin/env python3
"""Can the judge tell which Morgan amp made a sound? (`docs/amp-identifiability-plan.md`)

    python scripts/amp_identifiability.py --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --panel-dir ~/ndsp-presets/runs/kill/pr12 --panel-dir ~/ndsp-presets/runs/kill/ac20 \\
        --json amp-identifiability.json

For every development part whose DI plays in at least half of 1.0-10 s, every offered
render of the three amps through that part's DI (factory presets with no drive pedal and
the amp's volume at most 0.75, and each amp's template with time effects off) is taken
in turn as the target. Every other offered render of the same part is a candidate,
scored against the target by the judge (`aligned_distance`, default bands, lag 0: both
are renders of the same DI). In each of 20 draws, the same number of candidates is drawn
from each amp (the target's own preset excluded), and the amp of the closest one is the
guess. A target's accuracy is the share of draws that guess its amp; chance is 1/3.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import pathlib
import random
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

LATENCY, DRAWS, CHANCE = 52, 20, 1 / 3
RECOVERABLE, NOT_RECOVERABLE = 0.6, 0.45


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, action="append", required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=4)
    return ap


def offered(candidate: str, high_gain) -> bool:
    """A factory preset that is not high-gain, or an amp's template with time effects off."""
    name = candidate.split(":", 1)[1]
    if name == "template+R":
        return True
    return name.startswith("factory:") and not high_gain(candidate)


def distances(job):
    """{target: {candidate: distance or None}} for one part, every pair of its renders."""
    part, files, crops = job
    import kill_tests as K
    from analysis.aligned import aligned_distance

    di = K.mono(crops / part / "di.wav")
    renders = {c: K.mono(f) for c, f in files.items()}
    out = {}
    for t, x in renders.items():
        out[t] = {c: aligned_distance(x, y, di, lag=0, render_latency=LATENCY, start_s=1.0,
                                      end_s=10.0).distance
                  for c, y in renders.items() if c != t}
    print(part, flush=True)
    return part, out


def guesses(matrix, seed):
    """{target: share of draws whose closest equal-sized candidate set's amp is right}."""
    amps = sorted({c.split(":", 1)[0] for c in matrix})
    by_amp = {a: sorted(c for c in matrix if c.startswith(f"{a}:")) for a in amps}
    k = min(len(v) for v in by_amp.values()) - 1
    rng = random.Random(seed)
    out = {}
    for t in sorted(matrix):
        own = t.split(":", 1)[0]
        pools = {a: [c for c in names if c != t and matrix[t].get(c) is not None]
                 for a, names in by_amp.items()}
        if any(len(pool) < k for pool in pools.values()):
            out[t] = None                       # the judge refused too many of its pairs
            continue
        right = 0
        for _ in range(DRAWS):
            best = {a: min(matrix[t][c] for c in rng.sample(pool, k))
                    for a, pool in pools.items()}
            right += min(best, key=best.get) == own
        out[t] = right / DRAWS
    return out, k


def sign_flip_p(values):
    """Exact one-sided sign-flip p that the mean of `values` is above 0."""
    obs = sum(values)
    hits = sum(sum(s * v for s, v in zip(signs, values)) >= obs - 1e-12
               for signs in itertools.product((1, -1), repeat=len(values)))
    return hits / 2 ** len(values)


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("measuring amp identifiability")
    import kill_tests as K
    from benchmark_recordings import CATALOG
    from plan_listening_validation import high_gain, panel_files

    files, index_hashes = panel_files(args.panel_dir)
    if len({c.split(":", 1)[0] for d in files.values() for c in d}) != 3:
        die("pass the three Morgan panels")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    meta = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            meta[slug] = {"band": s.get("group") or f"{s['source']}/{s['song']}",
                          "split": p.get("split") or s.get("split")}
    if any(meta[p]["split"] != "development" for p in files):
        die("a panel holds a part that is not development material")
    crops = args.crops_dir.expanduser()
    names = sorted({c for d in files.values() for c in d})
    kept = [c for c in names if offered(c, high_gain)]
    parts = [p for p in sorted(files)
             if K.active_fraction(K.mono(crops / p / "di.wav"), 1.0, 10.0) >= 0.5]
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(args.workers) as ex:
        matrices = dict(ex.map(distances, [(p, {c: files[p][c] for c in kept}, crops)
                                           for p in parts]))
    rows, k_used = [], set()
    for p in parts:
        acc, k = guesses(matrices[p], seed=p)
        k_used.add(k)
        for t, a in acc.items():
            rows.append({"part": p, "band": meta[p]["band"], "target": t,
                         "amp": t.split(":", 1)[0], "accuracy": a})
    scored = [r for r in rows if r["accuracy"] is not None]
    by_band = collections.defaultdict(list)
    for r in scored:
        by_band[r["band"]].append(r["accuracy"])
    band_means = {b: statistics.mean(v) for b, v in sorted(by_band.items())}
    median = statistics.median(band_means.values())
    p = sign_flip_p([v - CHANCE for v in band_means.values()])
    verdict = ("recoverable" if median >= RECOVERABLE and p < 0.05
               else "not recoverable" if median <= NOT_RECOVERABLE else "partly")
    per_amp = {a: statistics.mean(r["accuracy"] for r in scored if r["amp"] == a)
               for a in sorted({r["amp"] for r in scored})}
    out = {"panels": index_hashes, "offered": kept, "parts": len(parts),
           "bands": len(band_means), "candidates_per_amp_per_draw": sorted(k_used),
           "targets": len(rows), "unscored_targets": len(rows) - len(scored),
           "band_mean_accuracy": band_means, "median_band_accuracy": median,
           "sign_flip_p_one_sided": p, "per_amp_accuracy": per_amp, "verdict": verdict,
           "rows": rows, "distances": matrices}
    print(json.dumps({k: v for k, v in out.items() if k not in ("rows", "distances",
                                                                 "offered")}, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out) + "\n")


if __name__ == "__main__":
    guarded(main)
