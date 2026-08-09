#!/usr/bin/env python3
"""Build and validate a fixed-topology response-atlas pilot.

    python scripts/build_response_atlas.py --pack morgan --amp pr12 \
      --template samples/Example_Clean_PR12.xml \
      --renderer synthetic --samples 128 --held-out 24 \
      --out /tmp/morgan-pr12-synthetic-atlas.json

The atlas varies continuous controls with a deterministic Latin hypercube while
holding amp, bypass, cabinet, and microphone choices fixed.  ``--held-out`` then
tests whether nearest-neighbour lookup beats that topology's neutral settings.

The Audio Unit backend reuses one plugin instance and reports
``reproducible=False``.  The command prints that before any scores and stores the
same caveat beside the measurements in the JSON.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shlex
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(SCRIPT_ROOT))

from _cli import guarded, positive_float, positive_int, probe_di
from benchmark_match import _backend_caveat, _renderer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pack", default="morgan",
                        help="which plugin pack to sample (default: morgan)")
    parser.add_argument("--amp", default="pr12",
                        help="the fixed amp topology (default: pr12)")
    parser.add_argument("--template", required=True, type=pathlib.Path,
                        help="preset whose amp, cab, microphones, and switches define "
                             "the fixed topology")
    parser.add_argument("--renderer", choices=("synthetic", "swift"),
                        default="synthetic", help="render backend (default: synthetic)")
    parser.add_argument("--samples", type=positive_int, default=128,
                        help="Latin-hypercube samples (default: 128 pilot)")
    parser.add_argument("--held-out", type=int, default=24, metavar="SAMPLES",
                        help="independent validation targets; 0 skips (default: 24)")
    parser.add_argument("--seed", type=int, default=17,
                        help="Latin-hypercube seed (default: 17)")
    parser.add_argument("--held-out-seed", type=int, default=29,
                        help="held-out sampler seed (default: 29)")
    parser.add_argument("--loss-profile", default="unpaired-v1",
                        help="distance used for lookup (default: unpaired-v1)")
    parser.add_argument("--probe-di", type=pathlib.Path,
                        help="DI used for every atlas and validation render")
    parser.add_argument("--seconds", type=positive_float, default=4.0,
                        help="synthetic probe length when no DI is given (default: 4)")
    parser.add_argument("--out", required=True, type=pathlib.Path,
                        help="atlas JSON destination")
    parser.add_argument("--dry-run", action="store_true",
                        help="show the topology and render count without rendering")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.held_out < 0:
        raise ValueError("--held-out must be zero or greater")

    from analysis import require

    require("building a response atlas")
    from match import atlas
    from match import space as space_module
    from match_preset import _seed_from_template

    space = space_module.build(args.pack, amp=args.amp)
    template_values, template_name = _seed_from_template(
        args.template, space, args.pack)
    fixed = atlas.tone_topology(template_values, space, args.amp)
    # A dry run stays plugin-free. The real backend exposes every writable manifest
    # parameter, while the synthetic one intentionally models only a subset.
    supported = None
    if args.renderer == "synthetic":
        from match.renderer_synth import SyntheticRenderer

        supported = SyntheticRenderer().parameter_specs()
    dimensions = atlas.sampling_dimensions(space, fixed, supported)
    total = args.samples + args.held_out + (1 if args.held_out else 0)
    print(f"{args.pack}/{args.amp}: fixed topology from {template_name!r}, "
          f"{len(dimensions)} continuous dimensions")
    print("  gate, doubler, compressor, drives, tremolo, reverb, and delay bypassed")
    print(f"  {args.samples} atlas renders + {args.held_out} held-out renders"
          + (" + 1 neutral baseline" if args.held_out else ""))
    print(f"  {total} renders total; Latin-hypercube seed {args.seed}")
    for dimension in dimensions:
        print(f"  {dimension.path}: {dimension.bounds()[0]:g}..{dimension.bounds()[1]:g}")
    if args.dry_run:
        print(f"\n--dry-run: would write {args.out}")
        return

    renderer = _renderer(args.renderer, args.pack)
    metadata = renderer.metadata()
    caveat = _backend_caveat(metadata)
    if caveat:
        print(f"\nCAUTION: {caveat}.\n", flush=True)
    di, probe_caveat = probe_di(args.probe_di, args.seconds)
    started = time.time()

    def progress(label):
        def show(done: int, count: int) -> None:
            elapsed = time.time() - started
            print(f"  {label} {done}/{count} — {elapsed:.0f}s elapsed",
                  file=sys.stderr, flush=True)
        return show

    try:
        document = atlas.build(
            renderer, space, di, args.pack, args.amp, args.samples, args.seed,
            fixed=fixed,
            progress=progress("atlas"),
        )
        validation = None
        if args.held_out:
            validation = atlas.held_out(
                renderer, space, di, document, args.held_out,
                args.held_out_seed, args.loss_profile,
                progress=progress("held-out"),
            )
    finally:
        close = getattr(renderer, "close", None)
        if close is not None:
            close()

    document["build"] = {
        # The actual interpreter and argv, not an equivalent-looking command. The
        # plan records two measurements invalidated by changing an invocation while
        # "re-running" it; retaining both pieces makes that mistake inspectable.
        "command": " ".join(shlex.quote(arg) for arg in [
            _portable_executable(), *sys.argv]),
        "python_executable": _portable_executable(),
        "argv": list(sys.argv),
        "template": str(args.template),
        "template_name": template_name,
        "probe_caveat": probe_caveat,
        "validation": validation,
    }
    # Measurement fields were validated inside atlas.build. Build provenance is an
    # allowed outer field and is retained by atlas.load(), so a copied file keeps
    # the invocation that produced its numbers.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    elapsed = time.time() - started
    print(f"\nwrote {args.out} in {elapsed:.0f}s")
    if validation:
        print(f"  neutral mean {validation['neutral_mean']:.3f}")
        print(f"  atlas mean   {validation['atlas_mean']:.3f}")
        print(f"  atlas won {100 * validation['atlas_win_rate']:.0f}% of held-out targets")
        print("  pilot gate: " + ("PASS — atlas beats neutral"
                                  if validation["beats_neutral"]
                                  else "FAIL — atlas does not beat neutral"))
    print("  achievable ranges are finite sampled observations on this probe, "
          "not mathematical plugin limits")
    if caveat:
        print(f"  CAUTION: {caveat}.")


def _portable_executable() -> str:
    """Keep a repo-local interpreter exact without committing a home path."""
    # Do not resolve the venv's symlink: on pyenv that turns a useful
    # ``.venv/bin/python`` into a machine-specific home-directory path.
    executable = pathlib.Path(sys.executable).absolute()
    try:
        return str(executable.relative_to(PLUGIN_ROOT))
    except ValueError:
        return str(executable)


if __name__ == "__main__":
    guarded(main)
