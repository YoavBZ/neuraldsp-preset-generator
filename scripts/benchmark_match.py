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

from _cli import die, guarded, positive_float, positive_int


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--targets", type=positive_int, default=50,
                    help="how many random vectors to try to recover (default: 50)")
    ap.add_argument("--budget", type=positive_int, default=300, metavar="RENDERS",
                    help="the search's render budget per target (default: 300)")
    ap.add_argument("--pack", default="morgan")
    ap.add_argument("--amp", default="sw50r",
                    help="which amp to benchmark (default: sw50r)")
    ap.add_argument("--loss-profile", default="unpaired-v1")
    ap.add_argument("--probe-di", type=pathlib.Path,
                    help="the DI to render through; a synthetic pluck sequence "
                         "otherwise")
    ap.add_argument("--seconds", type=positive_float, default=4.0,
                    help="length of the synthetic DI, if one is used (default: 4)")
    ap.add_argument("--seed", type=int, default=11,
                    help="the sampler's seed, so a run repeats (default: 11)")
    ap.add_argument("--arms", default="recipe,inversion,full",
                    help="which arms to run, comma-separated (default: all three)")
    ap.add_argument("--json", type=pathlib.Path,
                    help="also write every outcome here, one row per arm per target")
    return ap


def main() -> None:
    args = build_parser().parse_args()

    from analysis import require

    require("running the match benchmark")

    import numpy as np

    from analysis import io
    from match import benchmark, space as space_module
    from match.renderer_synth import SyntheticRenderer

    arms = tuple(name.strip() for name in args.arms.split(",") if name.strip())
    unknown = [name for name in arms if name not in benchmark.ARMS]
    if unknown:
        die(f"unknown arm(s) {', '.join(unknown)}. "
            f"Available: {', '.join(benchmark.ARMS)}")

    renderer = SyntheticRenderer()
    space = space_module.build(args.pack, amp=args.amp)
    probe_di = _probe(args.probe_di, args.seconds, io)
    seed = _centre_seed(space)

    started = time.time()

    def progress(done: int, total: int) -> None:
        elapsed = time.time() - started
        rate = elapsed / done
        print(f"  target {done}/{total} — {elapsed:.0f}s elapsed, "
              f"about {rate * (total - done):.0f}s left", file=sys.stderr, flush=True)

    result = benchmark.compare_baselines(
        renderer, space, probe_di, seed, targets=args.targets, budget=args.budget,
        profile=args.loss_profile, rng=np.random.default_rng(args.seed), arms=arms,
        pack_id=args.pack, amp=args.amp, progress=progress,
    )

    print(f"\n{args.targets} targets, budget {args.budget}, "
          f"{args.pack}/{args.amp}, {args.loss_profile}, "
          f"{time.time() - started:.0f}s total\n")
    print(benchmark.format_table(result, arms=arms))

    if args.json:
        rows = [vars(outcome) for outcome in result.outcomes]
        args.json.write_text(json.dumps({
            "targets": args.targets, "budget": args.budget, "pack": args.pack,
            "amp": args.amp, "loss_profile": args.loss_profile, "seed": args.seed,
            "summaries": {arm: result.summarise(arm) for arm in arms},
            "ships": result.verdict()[0], "reasons": result.verdict()[1],
            "caveats": result.caveats, "outcomes": rows,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")

    ships, _ = result.verdict()
    sys.exit(0 if ships else 1)


def _probe(path, seconds: float, io):
    if path is not None:
        return io.load(str(path)).mono()
    from tests import fixtures_audio

    return fixtures_audio.plucks(seconds=seconds, gap=0.9, seed=13)


def _centre_seed(space):
    """Every control at the middle of its range, effects off, EQ on.

    Not the recipe stack, and the difference matters for reading the `recipe` arm's
    score: this is a *neutral* starting point rather than a good one, so the number
    to beat is "the middle of every range", which is easier to beat than a preset
    someone chose. A recipe-stack seed would make the `recipe` baseline stronger and
    the comparison more honest — `packs/recipes.py` needs a genre or a reference to
    pick one, which a random target does not have, so the neutral seed is what a
    caller with no other information actually starts from.
    """
    values = {}
    for dimension in space.dimensions:
        if dimension.key == "selectedAmp":
            continue
        if dimension.switch:
            values[(dimension.module, dimension.key)] = (
                dimension.key.endswith("EQActive")
                or dimension.key.endswith("sectionActive"))
        elif dimension.kind == "enum":
            members = sorted((dimension.members or {}), key=int)
            if members:
                values[(dimension.module, dimension.key)] = int(members[0])
        else:
            low, high = dimension.bounds()
            values[(dimension.module, dimension.key)] = dimension.quantise(
                (low + high) / 2.0)
    values[("", "selectedAmp")] = 2
    return values


if __name__ == "__main__":
    guarded(main)
