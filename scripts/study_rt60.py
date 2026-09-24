#!/usr/bin/env python3
"""Does the fingerprint's RT60 measure reverb on a played passage?

    python scripts/study_rt60.py --renderer swift --pack toneking --amp rhythm \\
      --di howlong=how-long-di-6s.wav --di hotel=hotel-di-6s.wav \\
      --json rt60-toneking.json

Two questions, both about the `rt60` term `analysis.compare` puts in `ambience`:

- **fires**: the search-signal benchmark's targets (same seed, same topology),
  each rendered twice from the first --di beside the neutral start, one reused
  instance. How often both sides pass the confidence gate, what the term is
  worth when they do, and whether the same settings read the same twice.
- **tracks**: the neutral start with the amp's spring and then the rack reverb
  turned up step by step, one fresh process per render, through every --di. A
  reverb measurement has to rise with the reverb and agree across passages.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shlex
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded, positive_int
from benchmark_match import _backend_caveat, _renderer, _source_commit

SCHEMA = "rt60-study-1"

# The reverb steps, per signal path: the amp's own spring, then the rack reverb
# with the spring off. Values are in each parameter's own units (Tone King's
# decay is seconds; Morgan's is the plugin's 1–60 scale).
CASES = {
    ("toneking", "rhythm"): [("dry", {"ampReverb": 0.0})]
    + [(f"spring {x}", {"ampReverb": x}) for x in (0.5, 1.0)]
    + [(f"rack decay {x}", {"ampReverb": 0.0, "reverbActive": True, "reverbMix": 0.5,
                            "reverbDecay": x}) for x in (0.5, 1.0, 2.0, 4.0, 8.0)],
    ("morgan", "sw50r"): [("dry", {"sw50rAmp/sw50rReverb": 0.0})]
    + [(f"spring {x:g}", {"sw50rAmp/sw50rReverb": x}) for x in (50.0, 100.0)]
    + [(f"rack decay {x:g}", {"sw50rAmp/sw50rReverb": 0.0, "reverb/reverbActive": True,
                              "reverb/reverbMix": 50.0, "reverb/reverbDecay": x})
       for x in (1.0, 5.0, 15.0, 30.0, 60.0)],
}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", default="morgan")
    ap.add_argument("--amp", required=True)
    ap.add_argument("--template", type=pathlib.Path,
                    help="preset whose switches and selectors fix the topology "
                         "(default: the pack's neutral seed)")
    ap.add_argument("--renderer", choices=("synthetic", "swift"), default="synthetic")
    ap.add_argument("--di", action="append", required=True, metavar="NAME=PATH",
                    help="a played passage; repeatable. The first renders the targets")
    ap.add_argument("--targets", type=positive_int, default=12)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--loss-profile", default="unpaired-v1",
                    help="whose rt60 gate and scale the term is computed with")
    ap.add_argument("--json", type=pathlib.Path)
    return ap


def _estimate(audio, sample_rate):
    from analysis import io
    from analysis.fingerprint import fingerprint

    printed = fingerprint(io.from_samples(audio, sample_rate), regime="isolated_stem",
                          excerpt_s=None)
    seconds = printed.time_fx.get("rt60_s")
    return printed, {"rt60_s": None if seconds is None else round(float(seconds), 3),
                     "confidence": round(float(printed.time_fx.get("rt60_confidence")
                                               or 0.0), 3)}


def main() -> None:
    args = build_parser().parse_args()

    from analysis import io, require

    require("running the RT60 study")
    import numpy as np

    from analysis.compare import compare
    from match import benchmark, invert, search, signal_benchmark, space as space_module
    from match_preset import _seed_from_template

    try:
        amp = invert.resolve_signal_path(args.pack, args.amp)
    except invert.InversionError as error:
        die(str(error))
    if (args.pack, amp) not in CASES:
        die(f"reverb steps are defined for {', '.join('/'.join(k) for k in CASES)}, "
            f"not {args.pack}/{amp}")
    dis = {}
    for spec in args.di:
        name, _, path = spec.partition("=")
        if not name or not path:
            die(f"--di {spec!r}: give it as NAME=PATH")
        dis[name] = io.load(path).mono()
    first = next(iter(dis))
    space = space_module.build(args.pack, amp=amp)
    template_values = None
    if args.template is not None:
        template_values, _ = _seed_from_template(args.template, space, args.pack)

    def term(a, b):
        return compare(a, b, profile=args.loss_profile).detail["ambience"].get("rt60")

    started = time.time()
    fires = []
    renderer = _renderer(args.renderer, args.pack)
    try:
        metadata = renderer.metadata()
        topology = signal_benchmark.fixed_topology(
            space, amp, template_values, renderer.parameter_specs())
        seed = topology["seed"]
        scorer = search.Evaluator(renderer, None, dis[first], space,
                                  profile=args.loss_profile)
        streams = benchmark._spawn_streams(np.random.default_rng(args.seed),
                                           args.targets, np)
        for index in range(args.targets):
            truth = dict(seed)
            truth.update(benchmark.atlas_vector(topology["dimensions"], streams[index]))
            # Target, neutral, target, neutral: each pair compared as a score would.
            printed = []
            for values in (truth, seed, truth, seed):
                rendered = renderer.render(dis[first], scorer._settings(values))
                printed.append(_estimate(rendered.audio, rendered.metadata.sample_rate))
            fires.append({
                "target_index": index,
                "target": [printed[0][1], printed[2][1]],
                "neutral": [printed[1][1], printed[3][1]],
                "term_target_vs_neutral": [term(printed[0][0], printed[1][0]),
                                           term(printed[2][0], printed[3][0])],
                "term_target_vs_itself": term(printed[0][0], printed[2][0]),
            })
            print(f"  target {index + 1}/{args.targets}", file=sys.stderr, flush=True)
    finally:
        close = getattr(renderer, "close", None)
        if close is not None:
            close()

    tracks = []
    fresh = _renderer(args.renderer, args.pack, process_policy="fresh")
    try:
        dimensions = {dimension.path: dimension for dimension in space.dimensions}
        scorer = search.Evaluator(fresh, None, dis[first], space,
                                  profile=args.loss_profile)
        for name, changes in CASES[(args.pack, amp)]:
            values = dict(seed)
            for path, value in changes.items():
                dimension = dimensions[path]
                values[(dimension.module, dimension.key)] = value
            row = {"case": name, "settings": changes}
            for di_name, di in dis.items():
                rendered = fresh.render(di, scorer._settings(values))
                row[di_name] = _estimate(rendered.audio, rendered.metadata.sample_rate)[1]
            tracks.append(row)
            print(f"  {name}", file=sys.stderr, flush=True)
    finally:
        close = getattr(fresh, "close", None)
        if close is not None:
            close()

    fired = [row for row in fires
             if any(value is not None for value in row["term_target_vs_neutral"])]
    print(f"\n{args.pack}/{amp}, {metadata.renderer_id} {metadata.plugin_version}, "
          f"{time.time() - started:.0f}s")
    print(f"fires: the rt60 term was present between a target and the neutral start "
          f"on {len(fired)} of {len(fires)} targets")
    for row in fires:
        terms = ", ".join("—" if value is None else f"{value:.1f}"
                          for value in row["term_target_vs_neutral"])
        print(f"  target {row['target_index']:2}: term {terms}")
    print("tracks: rt60 s (confidence) per passage")
    for row in tracks:
        cells = "  ".join(
            f"{name} {'—' if row[name]['rt60_s'] is None else row[name]['rt60_s']}"
            f" ({row[name]['confidence']})" for name in dis)
        print(f"  {row['case']:18} {cells}")
    caveat = _backend_caveat(metadata)
    if caveat:
        print(f"\n  {caveat}.")

    if args.json:
        args.json.write_text(json.dumps({
            "schema": SCHEMA,
            "source_commit": _source_commit(),
            "command": " ".join(shlex.quote(arg) for arg in sys.argv),
            "pack": args.pack, "amp": amp,
            "template": None if args.template is None else str(args.template),
            "dis": {name: path for name, _, path in
                    (spec.partition("=") for spec in args.di)},
            "targets": args.targets, "seed": args.seed,
            "loss_profile": args.loss_profile,
            "backend": metadata.as_dict(), "measurement_caveat": caveat or None,
            "fires": fires, "tracks": tracks,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    guarded(main)
