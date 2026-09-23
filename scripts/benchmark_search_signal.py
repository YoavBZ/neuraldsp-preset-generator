#!/usr/bin/env python3
"""Measure what the signal a search renders through costs.

    python scripts/benchmark_search_signal.py --renderer swift --amp sw50r \\
      --template samples/SW50R_Atlas_Topology.xml --target-di passage-a.wav \\
      --signal same --signal other=passage-b.wav --signal noise \\
      --signal noise-at-di-level --targets 12 --budget 300 --workers 2 \\
      --json search-signal.json

Targets are known settings rendered from --target-di, standing in for a
reference recording. Each --signal runs the same pipeline — neutral settings,
inversion, search — with the same budget and the same random numbers, and every
answer is scored by rendering it from --target-di: what the player hears through
the preset. The template's switches and selectors are held fixed throughout.

Signals:
  same               --target-di itself: a paired DI, the upper bound
  NAME=PATH          another recording, e.g. a different passage by the same player
  noise              the synthetic noise-burst probe match_preset.py uses with no DI
  noise-at-di-level  that probe scaled to --target-di's integrated loudness

The first --signal is the reference every other one is paired against.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shlex
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded, positive_int, probe_di
from benchmark_match import _backend_caveat, _renderer, _source_commit

SCHEMA = "search-signal-benchmark-1"
NO_DI_SECONDS = 6.0   # what match_preset.py renders through when no DI is given


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", default="morgan")
    ap.add_argument("--amp", required=True, help="the amp or signal path to search")
    ap.add_argument("--template", type=pathlib.Path,
                    help="preset whose switches and selectors fix the topology "
                         "(default: the pack's neutral seed)")
    ap.add_argument("--renderer", choices=("synthetic", "swift"), default="synthetic")
    ap.add_argument("--target-di", required=True, type=pathlib.Path,
                    help="the played DI every target is rendered from and every "
                         "answer is scored through")
    ap.add_argument("--signal", action="append", required=True, metavar="SIGNAL",
                    help="a signal to search through: same, noise, "
                         "noise-at-di-level, or NAME=PATH. Repeatable; the first is "
                         "the reference")
    ap.add_argument("--targets", type=positive_int, default=12)
    ap.add_argument("--budget", type=positive_int, default=300)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--loss-profile", default="unpaired-v1")
    ap.add_argument("--workers", type=positive_int, default=1,
                    help="targets run at once, one plugin instance each (default: 1)")
    ap.add_argument("--json", type=pathlib.Path, help="write every outcome here")
    return ap


def _signals(specs, target, sample_rate):
    """Name → (samples, description) for each --signal, in the order given."""
    from analysis import io

    target_lufs = io.loudness_lufs(io.from_samples(target, sample_rate))
    signals, described, files = {}, {}, {}
    for spec in specs:
        if spec == "same":
            name, samples, kind = "same", target, "the target DI itself"
        elif spec == "noise":
            name, kind = "noise", f"synthetic noise-burst probe, {NO_DI_SECONDS:g} s"
            samples, _ = probe_di(None, NO_DI_SECONDS)
        elif spec == "noise-at-di-level":
            name = "noise-at-di-level"
            samples, _ = probe_di(None, NO_DI_SECONDS)
            gain_db = target_lufs - io.loudness_lufs(io.from_samples(samples, sample_rate))
            samples = samples * 10 ** (gain_db / 20.0)
            kind = (f"synthetic noise-burst probe, {NO_DI_SECONDS:g} s, "
                    f"{gain_db:+.1f} dB to the target DI's loudness")
        elif "=" in spec:
            name, path = spec.split("=", 1)
            if not name or name in ("same", "noise", "noise-at-di-level"):
                die(f"--signal {spec}: give the recording its own name")
            samples = io.load(path).mono()
            kind = f"recording {path}"
            files[name] = hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
        else:
            die(f"--signal {spec!r} is not same, noise, noise-at-di-level or NAME=PATH")
        if name in signals:
            die(f"--signal {name} is given twice")
        signals[name] = samples
        audio = io.from_samples(samples, sample_rate)
        # `samples_sha256` is of the decoded 48 kHz mono samples the search used;
        # a recording also gets the hash of its file, as --target-di does.
        described[name] = {"kind": kind, "samples_sha256": audio.sha256,
                           "seconds": round(audio.duration_s, 3),
                           "lufs": round(io.loudness_lufs(audio), 2)}
        if name in files:
            described[name]["file_sha256"] = files[name]
    return signals, described


def main() -> None:
    args = build_parser().parse_args()

    from analysis import io, require

    require("running the search-signal benchmark")
    import numpy as np

    from match import invert, signal_benchmark, space as space_module
    from match_preset import _seed_from_template

    try:
        amp = invert.resolve_signal_path(args.pack, args.amp)
    except invert.InversionError as error:
        die(str(error))
    space = space_module.build(args.pack, amp=amp)
    template_values = None
    if args.template is not None:
        template_values, _ = _seed_from_template(args.template, space, args.pack)
    renderer = _renderer(args.renderer, args.pack)
    try:
        metadata = renderer.metadata()
        target = io.load(str(args.target_di)).mono()
        signals, described = _signals(args.signal, target, metadata.sample_rate)
        topology = signal_benchmark.fixed_topology(
            space, amp, template_values, renderer.parameter_specs())
        started = time.time()

        def progress(done: int, total: int) -> None:
            print(f"  target {done}/{total} — {time.time() - started:.0f}s elapsed",
                  file=sys.stderr, flush=True)

        outcomes = signal_benchmark.compare_search_signals(
            renderer, space, target, signals, topology, targets=args.targets,
            budget=args.budget, profile=args.loss_profile,
            rng=np.random.default_rng(args.seed), pack_id=args.pack, amp=amp,
            progress=progress, workers=args.workers,
            renderer_factory=(None if args.workers < 2
                              else lambda: _renderer(args.renderer, args.pack)))
    finally:
        close = getattr(renderer, "close", None)
        if close is not None:
            close()

    reference = next(iter(signals))
    summary = signal_benchmark.summarise(outcomes, reference)
    caveat = _backend_caveat(metadata)
    elapsed = time.time() - started
    print(f"\n{args.targets} targets, budget {args.budget}, {args.pack}/{amp}, "
          f"{metadata.renderer_id} {metadata.plugin_version}, {elapsed:.0f}s; "
          f"answers scored through {args.target_di}\n")
    header = (f"{'signal':20} {'objective':>18} {'search belief':>14} "
              f"{'param MAE':>10} {'vs ' + reference:>22}")
    print(header)
    print("-" * len(header))
    for name, entry in summary.items():
        paired = ""
        if "closer_than_reference" in entry:
            p = entry.get("wilcoxon_p")
            paired = (f"closer {entry['closer_than_reference']}/"
                      f"{entry['paired_targets']}, "
                      f"{100 * entry['mean_change_fraction']:+.0f}%"
                      + (f", p={p:.3f}" if p is not None else ""))
        print(f"{name:20} {entry['objective_mean']!s:>8} / "
              f"{entry['objective_median']!s:<8} {entry['search_belief_mean']!s:>14} "
              f"{entry['parameter_mae']!s:>10} {paired:>22}")
    print("\nobjective is the answer rendered from the target DI, mean / median; "
          "search belief is the search's own best score through its own signal")
    if caveat:
        print(f"\n  {caveat}.")

    if args.json:
        args.json.write_text(json.dumps({
            "schema": SCHEMA,
            "source_commit": _source_commit(),
            "command": " ".join(shlex.quote(arg) for arg in sys.argv),
            "elapsed_s": round(elapsed, 1),
            "pack": args.pack, "amp": amp,
            "template": None if args.template is None else str(args.template),
            "target_di": {"path": str(args.target_di),
                          "sha256": hashlib.sha256(
                              args.target_di.read_bytes()).hexdigest()},
            "signals": described, "reference": reference,
            "targets": args.targets, "budget": args.budget, "seed": args.seed,
            "loss_profile": args.loss_profile, "workers": args.workers,
            "backend": metadata.as_dict(), "measurement_caveat": caveat or None,
            "summary": summary,
            "outcomes": [vars(outcome) for outcome in outcomes],
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    guarded(main)
