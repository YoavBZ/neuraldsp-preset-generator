"""M4's exit criterion: recover N random parameter vectors, three ways.

    python scripts/benchmark_match.py --targets 50 --budget 300
    python scripts/benchmark_match.py --targets 6 --budget 60 --json out.json

Samples random legal parameter vectors, renders each one, throws the vector away,
and tries to recover it from the audio alone — once with the recipe stack alone,
once with the calculated step added, and once with the whole pipeline. Reports
parameter MAE, objective distance, cost and failure rate **separately**, and says
whether M4 ships.

This is a local check, not CI. Fifty targets at a 300-render budget is about
15,000 renders and an hour on the synthetic chain; the defaults are the plan's
numbers, and `--targets`/`--budget` are there so a smaller version can be run while
working.

Needs the analysis and match extras:  pip install -e '.[analysis,match]'
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import (die, enumerated, guarded, positive_float, positive_int,
                  print_enumerable, probe_di, renderer_paths)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--targets", type=positive_int, default=50,
                    help="how many random vectors to try to recover (default: 50)")
    ap.add_argument("--budget", type=positive_int, default=300, metavar="RENDERS",
                    help="the search's render budget per target (default: 300)")
    ap.add_argument("--pack", default="morgan",
                    help="which plugin pack the targets are sampled from "
                         "(default: morgan)")
    ap.add_argument("--amp", default="sw50r",
                    help="which amp to benchmark (default: sw50r)")
    ap.add_argument("--loss-profile", default="unpaired-v1",
                    help="how the objective dimensions are weighted; this is what the "
                         "'objective' column measures (unpaired-v1, paired-v1)")
    ap.add_argument("--probe-di", type=pathlib.Path,
                    help="the DI to render through; a synthetic decaying noise-burst "
                         "sequence is used "
                         "otherwise")
    ap.add_argument("--seconds", type=positive_float, default=4.0,
                    help="length of the synthetic DI, if one is used (default: 4)")
    ap.add_argument("--seed", type=int, default=11,
                    help="the sampler's seed, so a run repeats (default: 11)")
    ap.add_argument("--arms", default="recipe,inversion,full",
                    help="which arms to run, comma-separated (default: all three)")
    ap.add_argument("--enumerate", dest="enumerated", action="append", default=[],
                    metavar="PATH",
                    help="enumerate this switch or selector in the full arm, each "
                         "position with its own inner search. Repeatable. Without it "
                         "no arm can choose a cabinet, so all three report the same "
                         "selector accuracy and that column measures nothing")
    ap.add_argument("--list-enumerable", action="store_true",
                    help="print the switches and selectors --enumerate accepts for "
                         "this pack and amp, and exit")
    ap.add_argument("--renderer", default="synthetic", choices=("synthetic", "swift"),
                    help="which backend renders a candidate (default: synthetic). "
                         "'swift' is the installed plugin, and is the only one whose "
                         "numbers are facts about it")
    ap.add_argument("--json", type=pathlib.Path,
                    help="also write every outcome here, one row per arm per target")
    return ap


def _renderer(name: str, pack_id: str):
    """The backend to benchmark through.

    The synthetic chain is the default because it is the only one that runs
    anywhere and the only one that is exactly reproducible. `swift` is the
    installed plugin, and everything it reports carries the caveat that a reused
    instance does not repeat itself — which is why `backend` goes in the JSON and
    in the printed header rather than being left to whoever remembers the command.
    """
    if name == "synthetic":
        from match.renderer_synth import SyntheticRenderer

        return SyntheticRenderer()
    from match.renderer_au import AudioUnitError, AudioUnitRenderer

    renderer = AudioUnitRenderer(pack_id)
    try:
        renderer.metadata()
    except AudioUnitError as e:
        renderer.close()
        die(f"{e}\n"
            f"  The swift backend needs macOS with the plugin licensed and "
            f"installed, and swiftc from the Xcode command line tools.")
    return renderer


def _backend_caveat(metadata) -> str:
    """What has to be said next to every number this run produces."""
    if metadata.reproducible:
        return ""
    return (
        f"rendered by {metadata.renderer_id} (plugin {metadata.plugin_version}), "
        f"which reports reproducible=False: two renders of identical parameters "
        f"from one reused instance differ, and per-band levels move by up to "
        f"{metadata.band_noise_db} dB. Every number below carries that, and none "
        f"of them may be committed without it"
    )


def main() -> None:
    args = build_parser().parse_args()

    from analysis import require

    require("running the match benchmark")

    import numpy as np

    from match import benchmark, space as space_module

    arms = tuple(name.strip() for name in args.arms.split(",") if name.strip())
    unknown = [name for name in arms if name not in benchmark.ARMS]
    if unknown:
        die(f"unknown arm(s) {', '.join(unknown)}. "
            f"Available: {', '.join(benchmark.ARMS)}")

    space = space_module.build(args.pack, amp=args.amp)
    renderer = _renderer(args.renderer, args.pack)
    supported = renderer_paths(renderer)
    if args.list_enumerable:
        print_enumerable(space, args.pack, args.amp, supported=supported)
        return

    seed = benchmark.centre_seed(space)
    # The same routing and the same budget arithmetic the match CLI uses, imported
    # rather than repeated: two copies of "is this a switch or a selector" would be
    # two places for the answer to drift.
    switches, selectors = enumerated(
        space, args.enumerated, args.budget, shortlist=1, supported=supported,
        seed=seed)
    di, di_caveat = probe_di(args.probe_di, args.seconds)

    started = time.time()

    def progress(done: int, total: int) -> None:
        elapsed = time.time() - started
        rate = elapsed / done
        print(f"  target {done}/{total} — {elapsed:.0f}s elapsed, "
              f"about {rate * (total - done):.0f}s left", file=sys.stderr, flush=True)

    metadata = renderer.metadata()
    try:
        result = benchmark.compare_baselines(
            renderer, space, di, seed, targets=args.targets, budget=args.budget,
            profile=args.loss_profile, rng=np.random.default_rng(args.seed), arms=arms,
            pack_id=args.pack, amp=args.amp, switches=switches, selectors=selectors,
            progress=progress,
        )
    finally:
        # The plugin instance goes back even if the run raised or was interrupted.
        close = getattr(renderer, "close", None)
        if close is not None:
            close()
    if di_caveat:
        result.caveats.insert(0, di_caveat)
    # First, not last: it is the caveat that qualifies every other line.
    backend_caveat = _backend_caveat(metadata)
    if backend_caveat:
        result.caveats.insert(0, backend_caveat)

    print(f"\n{args.targets} targets, budget {args.budget}, "
          f"{args.pack}/{args.amp}, {args.loss_profile}, "
          f"{metadata.renderer_id} {metadata.plugin_version}, "
          f"{time.time() - started:.0f}s total\n")
    print(benchmark.format_table(result, arms=arms))
    if backend_caveat:
        print(f"\n  {backend_caveat}.")

    if args.json:
        rows = [vars(outcome) for outcome in result.outcomes]
        args.json.write_text(json.dumps({
            "targets": args.targets, "budget": args.budget, "pack": args.pack,
            "amp": args.amp, "loss_profile": args.loss_profile, "seed": args.seed,
            # Which backend, and whether it repeats itself. A table of objectives
            # with no backend beside it is the one thing this project has agreed
            # never to write down.
            "backend": metadata.as_dict(),
            "summaries": {arm: result.summarise(arm) for arm in arms},
            "ships": result.verdict()[0], "reasons": result.verdict()[1],
            "caveats": result.caveats, "outcomes": rows,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")

    ships, _ = result.verdict()
    sys.exit(0 if ships else 1)


if __name__ == "__main__":
    guarded(main)
