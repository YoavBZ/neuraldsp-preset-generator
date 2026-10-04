#!/usr/bin/env python3
"""Can the judge tell which Morgan amp made a sound? (`docs/amp-identifiability-plan.md`)

    python scripts/amp_identifiability.py --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --panel-dir ~/ndsp-presets/runs/kill/pr12 --panel-dir ~/ndsp-presets/runs/kill/ac20 \\
        --json amp-identifiability.json

For every development part whose DI plays in at least half of 1.0-10 s, every offered
render of the three amps through that part's DI (factory presets with no drive pedal,
the amp's volume at most 0.75 and the cab section on, and each amp's template with time
effects off) is taken in turn as the target. Every offered render of the same part
outside the target's family (its artist folder; the templates are one family) is a
candidate, scored against the target by the judge (`aligned_distance`, default bands,
lag 0: both are renders of the same DI). In each of 200 draws, the same number of
candidates is drawn from each amp (the smallest amp's remaining pool), and the amp of
the closest one is the guess. A target's accuracy is the share of draws that guess its
amp; chance is 1/3.
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

LATENCY, DRAWS, CHANCE = 52, 200, 1 / 3
RECOVERABLE, NOT_RECOVERABLE, EVERY_AMP = 0.6, 0.45, 0.5


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, action="append", required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=4)
    return ap


def offered(candidate: str, high_gain, cab_on=lambda c: True) -> bool:
    """A factory preset that is not high-gain and has its cab on, or an amp's template
    with time effects off."""
    name = candidate.split(":", 1)[1]
    if name == "template+R":
        return True
    return name.startswith("factory:") and not high_gain(candidate) and cab_on(candidate)


def family(candidate: str) -> str:
    """The artist folder a factory preset comes from; the templates are one family, and
    every other preset (Neural DSP's own, Default) is its own."""
    name = candidate.split(":", 1)[1]
    if name == "template+R":
        return "templates"
    parts = name[len("factory:"):].split("/")
    return f"artist:{parts[1]}" if parts[0] == "Artists" and len(parts) > 2 else candidate


def settings(candidate: str) -> dict:
    """The preset's compressor, cab and volume, as stored."""
    from format.parser import parse
    from format.structured import build
    from plan_listening_validation import preset_path

    amp = candidate.split(":", 1)[0]
    v = {(p.module_path, p.key): p.value
         for p in build(parse(preset_path(candidate).read_bytes())).parameters}
    on = lambda k: str(v.get(k, "false")).lower() == "true"                # noqa: E731
    return {"compressor": on(("compressor", "compressorActive")),
            "cab": on(("cabParameters", "sectionActive")),
            "volume": float(v.get((f"{amp}Amp", f"{amp}Volume"), "nan"))}


def distances(job):
    """{target: {candidate: distance or None}} for one part, every pair of its renders."""
    part, files, crops = job
    import kill_tests as K
    from analysis.aligned import aligned_distance

    di = K.mono(crops / part / "di.wav")
    renders = {c: K.mono(f) for c, f in files.items()}
    out = {}
    for t, x in renders.items():
        out[t] = {}
        for c, y in renders.items():
            if c != t:
                r = aligned_distance(x, y, di, lag=0, render_latency=LATENCY, start_s=1.0,
                                     end_s=10.0)
                out[t][c] = None if r.distance is None else [r.distance, r.tonal, r.temporal]
    print(part, flush=True)
    return part, out


def guesses(matrix, seed, which=0, keep=lambda c: True, min_k=3):
    """{target: (share of draws whose closest candidate's amp is right, the guesses'
    counts by amp, k)}. Candidates exclude the target's family; each amp contributes k,
    the smallest of the three remaining pools. `which` picks the distance (0 the
    judge's, 2 its temporal part); `keep` limits targets and candidates."""
    amps = sorted({c.split(":", 1)[0] for c in matrix})
    rng = random.Random(seed)
    out = {}
    for t in sorted(c for c in matrix if keep(c)):
        own = t.split(":", 1)[0]
        pools = {a: [c for c in matrix[t] if c.startswith(f"{a}:") and keep(c)
                     and family(c) != family(t) and matrix[t][c] is not None]
                 for a in amps}
        k = min(len(pool) for pool in pools.values())
        if k < min_k:
            out[t] = None                       # too few candidates left to compare
            continue
        counts = collections.Counter()
        for _ in range(DRAWS):
            best = {a: min(matrix[t][c][which] for c in rng.sample(pool, k))
                    for a, pool in pools.items()}
            counts[min(best, key=best.get)] += 1
        out[t] = (counts[own] / DRAWS, dict(counts), k)
    return out


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
    preset = {c: settings(c) for c in names if c.split(":", 1)[1] != "template"}
    kept = [c for c in names if offered(c, high_gain, lambda c: preset[c]["cab"])]
    missing = [p for p in files if p not in meta]
    if missing:
        die(f"parts the catalogue does not know: {missing}")
    if any(set(kept) - set(files[p]) for p in files):
        die("a panel is missing a render of an offered preset")
    parts = [p for p in sorted(files)
             if K.active_fraction(K.mono(crops / p / "di.wav"), 1.0, 10.0) >= 0.5]
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(args.workers) as ex:
        matrices = dict(ex.map(distances, [(p, {c: files[p][c] for c in kept}, crops)
                                           for p in parts]))
    def reading(which=0, keep=lambda c: True):
        rows = []
        for p in parts:
            for t, g in guesses(matrices[p], seed=p, which=which, keep=keep).items():
                rows.append({"part": p, "band": meta[p]["band"], "target": t,
                             "amp": t.split(":", 1)[0], "accuracy": None if g is None else g[0],
                             "guessed": None if g is None else g[1],
                             "k": None if g is None else g[2], **preset.get(t, {})})
        scored = [r for r in rows if r["accuracy"] is not None]
        if not scored:
            return {"rows": rows, "verdict": "nothing scored"}
        by_band = collections.defaultdict(list)
        for r in scored:
            by_band[r["band"]].append(r["accuracy"])
        band_means = {b: statistics.mean(v) for b, v in sorted(by_band.items())}
        median = statistics.median(band_means.values())
        p = sign_flip_p([v - CHANCE for v in band_means.values()])
        per_amp = {a: statistics.mean(r["accuracy"] for r in scored if r["amp"] == a)
                   for a in sorted({r["amp"] for r in scored})}
        confusion = {a: dict(sum((collections.Counter(r["guessed"]) for r in scored
                                  if r["amp"] == a), collections.Counter()))
                     for a in per_amp}
        verdict = ("recoverable" if median >= RECOVERABLE and p < 0.05
                   and min(per_amp.values()) >= EVERY_AMP
                   else "no evidence across presets" if median <= NOT_RECOVERABLE
                   else "partly")
        return {"targets": len(rows), "unscored_targets": len(rows) - len(scored),
                "k_range": [min(r["k"] for r in scored), max(r["k"] for r in scored)],
                "bands": len(band_means), "band_mean_accuracy": band_means,
                "median_band_accuracy": median, "sign_flip_p_one_sided": p,
                "per_amp_accuracy": per_amp, "confusion": confusion, "verdict": verdict,
                "rows": rows}

    main_reading = reading()
    out = {"panels": index_hashes, "offered": kept, "parts": len(parts),
           "verdict": main_reading["verdict"], "main": main_reading,
           "reported": {"temporal_part_only": reading(which=2),
                        "compressor_on_only": reading(
                            keep=lambda c: preset.get(c, {}).get("compressor", False))},
           "distances": matrices}
    def brief(r):
        return {k: v for k, v in r.items() if k != "rows"}

    print(json.dumps({"verdict": out["verdict"], "main": brief(main_reading),
                      "reported": {k: brief(v) for k, v in out["reported"].items()}},
                     indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out) + "\n")


if __name__ == "__main__":
    guarded(main)
