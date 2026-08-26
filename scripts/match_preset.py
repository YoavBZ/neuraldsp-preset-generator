"""Match a reference recording with a preset, and say what not to believe.

    python scripts/match_preset.py \\
      --template samples/Example_Clean_PR12.xml \\
      --reference ~/audio/song-excerpt.wav --reference-mode mix \\
      --probe-di data/di/probe.wav \\
      --loss-profile unpaired-v1 --budget 300 --shortlist 3 \\
      --renderer synthetic \\
      --out-dir "$NDSP_PRESET_DATA/runs/hotel-california-001"

Four things happen, in this order, and each one is reported separately because
they fail in different ways:

1. The reference is **measured** into a fingerprint. `--reference-mode` says how
   the guitar reaches the file, and it is not a formality: `mix` means a guitar
   under a band and a master chain, and the fingerprint records that so nothing
   downstream treats a mastered spectrum as an amp's.
2. What can be **calculated** is calculated — the EQ curve, the filter corners,
   the delay, the level. `match/invert.py` does this against a first render of the
   template, and it takes those dimensions out of the search.
3. What is left is **searched**, on a render budget you set.
4. A **report** is written: one self-contained HTML file, with the caveats above
   the charts rather than under them.

The output is a spec `apply_spec.py` consumes, not a preset file. That is
deliberate: the winner is written by the same validated path as a hand-authored
preset, so a search cannot produce bytes a person could not have.

Needs the analysis and match extras:  pip install -e '.[analysis,match]'
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any, Dict, Optional

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import (die, enumerated as _enumerated, guarded, on_interrupt,
                  nonnegative_float, positive_float, positive_int,
                  print_enumerable as _print_enumerable, probe_di as _probe,
                  renderer_paths, resolved_excerpt)

# The regimes `analysis.fingerprint` accepts, and only those. This tuple used to read
# `("paired_di", "reamp", "isolated", "mix", "probe")` — two of which do not exist:
# `fingerprint()` refuses an unknown regime by name, so `--reference-mode reamp` passed
# argparse and then died with "unknown regime 'reamp'", and `separated_stem`, which the
# fingerprint scores at 0.55 confidence, could not be selected at all. Two dead choices
# and one missing one, in the flag that decides how much the whole run is worth.
# `tests/test_match_cli.py` asserts this list against the fingerprint's so it cannot
# drift again; it is not imported from there because `build_parser()` runs before the
# missing-extra check and must not need numpy to print `--help`.
REGIMES = ("paired_di", "isolated_stem", "separated_stem", "mix", "probe")
RENDERERS = ("synthetic", "swift", "pedalboard")

# Below this there is not enough signal for a playing-invariant statistic to mean
# anything: one note and a gap is not a distribution of onsets.
MINIMUM_REFERENCE_S = 1.0

# `fingerprint` floors a silent band at -300 dB rather than returning None, so this is
# how silence is recognised rather than matched.
SILENCE_FLOOR_DB = -120.0


class _ReplicatedStart:
    """Both the exact first trial and the aggregate a person should compare."""

    def __init__(self, *, estimate: Any, trial: Any, observations: int,
                 spread: Optional[float],
                 objective_observations: Dict[str, int],
                 objective_spreads: Dict[str, Optional[float]]):
        self.estimate = estimate
        self.trial = trial
        self.observations = int(observations)
        self.spread = spread
        self.objective_observations = dict(objective_observations)
        self.objective_spreads = dict(objective_spreads)


def build_parser() -> argparse.ArgumentParser:
    # The whole docstring, not its first line. `RawDescriptionHelpFormatter` was set
    # and then handed one line to preserve the layout of, so the worked invocation,
    # the four stages and "the output is a spec, not a preset file" were all written
    # down and none of them reached anybody running `--help`.
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--template", type=pathlib.Path, required=True,
                    help="the preset to start from; its values are the search's prior")
    ap.add_argument("--reference", type=pathlib.Path, required=True,
                    help="the audio to match")
    ap.add_argument("--reference-mode", default="mix", choices=REGIMES,
                    help="how the guitar reaches the reference file (default: mix). "
                         "This is not a formality — it sets how much the match is "
                         "worth, and is recorded in the fingerprint so nothing "
                         "downstream reads a mastered spectrum as an amp's. "
                         "paired_di: the reference and its own DI (worth 1.0); "
                         "isolated_stem: a solo guitar track from the session, no "
                         "band (0.85); separated_stem: a guitar track pulled out of a "
                         "mix by source separation, so it carries the separator's "
                         "artefacts too (0.55); mix: a finished mix, so the spectrum "
                         "includes the band and whatever the master chain did (0.35); "
                         "probe: a render of a known chain, which is what the "
                         "benchmarks use (1.0)")
    ap.add_argument("--probe-di", type=pathlib.Path,
                    help="the DI every candidate is rendered through. Without one a "
                         "synthetic decaying noise-burst sequence is used, and the "
                         "report says so")
    ap.add_argument("--pack", default="morgan", help="which plugin pack (default: morgan)")
    ap.add_argument("--amp", default=None,
                    help="signal path to invert, e.g. sw50r or lead (default: read "
                         "the template's amp/channel selector)")
    ap.add_argument("--loss-profile", default="unpaired-v1",
                    help="how the objective dimensions are weighted "
                         "(unpaired-v1, paired-v1)")
    # "about 60" was the wrong shape of answer: it is a number the user cannot check
    # and, on Morgan with 18 searchable parameters, one that leaves the optimiser
    # unable to take a single step. The arithmetic is short, so give the arithmetic.
    ap.add_argument("--budget", type=positive_int, default=300, metavar="RENDERS",
                    help="renders to spend (default: 300). Some of it is fixed cost "
                         "that cannot be part-paid: 2 per searchable parameter plus 1 "
                         "for the screen, 1 for the template as it arrived, 2 per "
                         "--shortlist entry for the ±6 dB re-rank, and then the "
                         "optimiser needs at least one whole round (~12) on top. A "
                         "backend that does not repeat itself costs more: 4 more on "
                         "the screen and 8 rather than 2 per --shortlist entry, "
                         "because each score is the mean of 3 renders. On "
                         "Morgan that is about 70 before anything is searched, and a "
                         "run that could not afford a round says so and names the "
                         "number to raise this to")
    ap.add_argument("--shortlist", type=positive_int, default=3,
                    help="how many candidates to return (default: 3)")
    ap.add_argument("--renderer", default="synthetic", choices=RENDERERS,
                    help="which backend renders a candidate (default: synthetic)")
    ap.add_argument("--enumerate", dest="enumerated", action="append", default=[],
                    metavar="PATH",
                    help="try every position of this switch or selector, each with "
                         "its own inner search — the cabinet, the microphone, the "
                         "amp, an effect on or off. Repeatable, and a product: two "
                         "two-state switches is four searches sharing the budget. "
                         "Without it every discrete control stays where the template "
                         "had it, which is what the run's caveat says. Use "
                         "--list-enumerable to see the paths")
    ap.add_argument("--list-enumerable", action="store_true",
                    help="print the switches and selectors --enumerate accepts for "
                         "this pack and amp, with how many positions each has, and "
                         "exit")
    ap.add_argument("--excerpt", type=nonnegative_float, default=None,
                    metavar="SECONDS",
                    help="measure the most continuously active window of this length; "
                         "the exact start and end are recorded (default: 20, except "
                         "paired_di uses all; 0 for all)")
    ap.add_argument("--out-dir", type=pathlib.Path, required=True,
                    help="where the store, the spec and the report are written")
    ap.add_argument("--run-id", default=None,
                    help="names this run in the store (default: the directory name "
                         "plus a timestamp)")
    ap.add_argument("--seed", type=int, default=0,
                    help="the optimiser's random seed, so a run repeats (default: 0)")
    ap.add_argument("--no-invert", action="store_true",
                    help="skip the calculated step and search from the template alone. "
                         "For measuring what the search contributes on its own")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    command_started_at = time.monotonic()

    from analysis import require

    require("matching a preset")

    import numpy as np

    from analysis import io
    from analysis.compare import list_profiles, load_profile
    from analysis.fingerprint import fingerprint
    from match import invert, report, search
    from match import space as space_module
    from match.store import Run, open_store

    if args.loss_profile not in list_profiles():
        die(f"unknown loss profile {args.loss_profile!r}. "
            f"Available: {', '.join(list_profiles())}")
    profile = load_profile(args.loss_profile)  # fail here rather than 200 renders in
    residual_weighted = float(
        profile.get("weights", {}).get("residual", 0.0) or 0.0
    ) > 0.0
    if residual_weighted and args.reference_mode != "paired_di":
        die(f"loss profile {args.loss_profile!r} weights a sample-for-sample "
            "waveform residual, but --reference-mode is "
            f"{args.reference_mode!r}. That term is only meaningful when "
            "--reference is a reamp of the exact --probe-di performance.\n"
            "  Use --reference-mode paired_di with that pair, or use "
            "--loss-profile unpaired-v1 for a different performance.")
    excerpt_s = resolved_excerpt(args.excerpt, args.reference_mode)
    if residual_weighted and excerpt_s is not None:
        die("a paired waveform residual must compare the complete reamp and DI; "
            "--excerpt would mix excerpt-level features with a full-performance "
            "waveform score.\n  Omit --excerpt or pass --excerpt 0.")

    signal_path_arg = None
    if args.amp is not None:
        try:
            signal_path_arg = invert.resolve_signal_path(args.pack, args.amp)
        except invert.InversionError as error:
            die(str(error))
    space = space_module.build(args.pack, amp=signal_path_arg)
    # Validate and load a real run's template before opening a renderer. Besides
    # avoiding needless Audio Unit startup, this preserves the more specific error
    # when a Morgan preset is accidentally paired with the Tone King pack.
    seed = template_name = None
    if not args.list_enumerable:
        seed, template_name = _seed_from_template(args.template, space, args.pack)
    renderer = _renderer(args.renderer, args.pack)
    supported = renderer_paths(renderer)
    if supported is not None and not any(
        dimension.path in supported for dimension in space.dimensions
    ):
        close = getattr(renderer, "close", None)
        if close is not None:
            close()
        suggestion = (
            " Use --renderer swift for Tone King."
            if args.renderer != "swift" else ""
        )
        die(
            f"the {args.renderer} renderer supports no searchable controls for "
            f"pack {args.pack}; a match would render the same settings repeatedly."
            f"{suggestion}"
        )
    if args.list_enumerable:
        _print_enumerable(space, args.pack, signal_path_arg, supported=supported)
        close = getattr(renderer, "close", None)
        if close is not None:
            close()
        return
    switches, selectors = _enumerated(
        space, args.enumerated, None, args.shortlist, supported=supported,
        replicates=search.shortlist_replicates(renderer.metadata()))
    assert seed is not None and template_name is not None
    if signal_path_arg is not None:
        # ``--amp`` selects the path being matched, not merely the basis used after
        # the first render. Apply it before the template score and inversion probe
        # so both audio and calibration describe the same path.
        seed = invert.apply_to(
            seed,
            invert.signal_path_selection(args.pack, signal_path_arg),
            space,
        )
    template_values = dict(seed)

    reference = io.load(str(args.reference))
    target = fingerprint(reference, regime=args.reference_mode,
                         excerpt_s=excerpt_s)
    unmeasurable = _unmeasurable(target, reference)
    if unmeasurable:
        die(unmeasurable)
    probe_di, probe_note = _probe(args.probe_di)

    run_id = args.run_id or f"{args.out_dir.name}-{time.strftime('%Y%m%d-%H%M%S')}"
    store = open_store(str(args.out_dir))
    metadata = renderer.metadata()
    # Every render commits before the next one starts. Deterministic backends can
    # safely reuse those scores; a stateful backend records them for diagnosis but
    # must render again because another process/instance need not produce that score.
    if metadata.reproducible:
        interrupt_note = (
            f"Run the same command again and completed renders are served from the "
            f"cache — you lose the time since the last render, not the run."
        )
    else:
        interrupt_note = (
            "This renderer reports reproducible=false, so a resumed command must "
            "render again; the recorded trials remain available for diagnosis only."
        )
    on_interrupt(
        f"{args.out_dir / 'trials.sqlite3'} has every render made so far. "
        f"{interrupt_note}"
    )
    store.start_run(Run(
        run_id=run_id, pack=args.pack, template=str(args.template),
        reference_sha=target.source.get("sha256"), regime=args.reference_mode,
        loss_profile=args.loss_profile, budget=args.budget,
        renderer_id=metadata.renderer_id, plugin_version=metadata.plugin_version,
        notes=json.dumps({
            "schema": "tone-match-run-notes-v1",
            "probe_note": probe_note,
            "renderer": metadata.as_dict(),
        }, sort_keys=True, separators=(",", ":")),
    ))

    caveats = [probe_note] if probe_note else []
    # What the *measurement of the reference* could not establish. `Fingerprint.caveats()`
    # docstring is "everything a report has to say out loud about this measurement", and
    # `fingerprint.py` and `compare_audio.py` both call it — this script, the one that
    # spends an hour of renders on the answer, reimplemented one of its five clauses by
    # hand and dropped the other four. So a reference with no sustained note (distortion
    # character unmeasured), an uncertain reverb decay, or an undetected delay said so
    # under `compare_audio.py` and said nothing here.
    caveats.extend(target.caveats())
    if args.reference_mode == "mix":
        caveats.append(
            "the reference is a mix, so the spectrum includes the rest of the band "
            "and whatever the master chain did. Anything the guitar shares a band "
            "with — the snare, a synth pad — is being matched too"
        )
    if not metadata.reproducible:
        caveats.append(
            f"this backend does not repeat itself exactly: identical-state "
            f"observations have differed by up to {metadata.band_noise_db:.2f} dB in "
            f"one third-octave band. That maximum is provenance, not a scalar "
            f"candidate-score floor: the sensitivity screen repeats its own seed in "
            f"objective units, and a measured EQ basis uses its frequency-aligned "
            f"repeat spread"
        )

    # Renders made outside `search`, so the printed total is every render this command
    # caused rather than only the budgeted ones.
    extra: list = []
    evaluator = search.Evaluator(renderer, target, probe_di, space,
                                 profile=args.loss_profile, recipe=seed,
                                 reference_audio=(reference.samples
                                                  if residual_weighted else None))
    start_requested = search.shortlist_replicates(metadata)
    start_result = _replicated_start(evaluator, seed, start_requested)
    if start_result is None:
        die("the template rendered nothing comparable — a silent render, or no "
            "dimension this loss profile weights could be measured on both sides.\n"
            "  Check the reference is long enough to measure and that the renderer "
            "produces audio.")
    start = start_result.estimate
    start_observations = start_result.observations
    start_spread = start_result.spread
    if start_observations < start_requested:
        caveats.append(
            f"the starting template score averages {start_observations} of the "
            f"{start_requested} observations this backend calls for, because one "
            "or more renders produced no comparable objective; the before-and-after "
            "comparison starts from thinner evidence than requested"
        )

    dropped: list = []
    inversion_detail = None
    if args.no_invert:
        caveats.append("--no-invert was given, so nothing was calculated and the "
                       "search started from the template alone")
        calculated = None
        inverted_values = None
    else:
        printed = _render_fingerprint(renderer, probe_di,
                                      evaluator._settings(seed), extra)
        amp = (signal_path_arg or space.amp_prefix(seed)
               or invert.selected_signal_path(args.pack, seed))
        if amp is None:
            # Two different problems, and one message told the wrong story for both.
            # `--pack toneking` with a Morgan template said "the template does not say
            # which amp is selected" about a template that says PR12, then advised
            # `--amp sw50r`, which is a Morgan amp and produces a second error.
            named, from_pack = _template_amp(args.template)
            if named is not None:
                belongs = (f" — it is a {from_pack} preset" if from_pack
                           and from_pack != args.pack else "")
                die(f"the template selects {named}, which is not an amp in pack "
                    f"{args.pack!r}{belongs}.\n"
                    f"  Pass --pack {from_pack or '<the plugin it is from>'}, or give "
                    f"a template from {args.pack!r}.")
            die("the template does not say which amp or channel is selected, and "
                "no --amp was given, so there is no way to tell which signal "
                "path's controls to invert.\n"
                "  Pass --amp with one of the pack's signal paths, or use a "
                "template whose selector is mapped by the pack.")
        calculated = invert.invert(target, printed, amp=amp, pack_id=args.pack,
                                   renderer=renderer, current_settings=seed)
        inversion_detail = dict(calculated.detail)
        seed = invert.apply_to(seed, calculated.as_settings(), space)
        inverted_values = dict(seed)
        caveats.extend(calculated.caveats)
        # Values this backend cannot be driven with still reach the output spec, and
        # nothing said so. With the docstring's own PR12 template and the synthetic
        # renderer, 12 of the 16 calculated values — the entire nine-band EQ fit and
        # both its corners — were unsupported: filtered out of every render, so no
        # score in the report reflects them, and written into the spec regardless.
        dropped = calculated.dropped_for(renderer.parameter_specs())
        if dropped:
            caveats.append(
                f"{len(dropped)} of the calculated values are for controls this "
                f"backend does not model, so they were written into the spec but no "
                f"score here reflects them — they have not been heard, only "
                f"calculated: {', '.join(dropped[:5])}"
                + (f" and {len(dropped) - 5} more" if len(dropped) > 5 else "")
            )

    # Validate the budget against the seed the screen will really see.  The
    # inversion can switch whole sections on and select a different amp, so doing
    # this against the template above overstated or understated the fixed cost.
    switches, selectors = _enumerated(
        space, args.enumerated, args.budget, args.shortlist,
        supported=supported, seed=seed,
        replicates=search.shortlist_replicates(metadata))

    search_started_at = time.monotonic()
    result = search.search(renderer, target, probe_di, space, seed,
                           budget=args.budget, profile=args.loss_profile,
                           shortlist=args.shortlist, store=store, run_id=run_id,
                           fallbacks=[template_values],
                           switches=switches, selectors=selectors,
                           rng=np.random.default_rng(args.seed),
                           reference_audio=(reference.samples
                                            if residual_weighted else None))
    search_elapsed_s = time.monotonic() - search_started_at
    caveats.extend(result.caveats)

    if not result.shortlist:
        die("no candidate produced a comparable render, so there is nothing to "
            f"write. See {args.out_dir / 'trials.sqlite3'} for what was tried.")

    # Nothing checked this, and on a near-perfect template it is the whole story: the
    # bundled PR12 preset matched against a render of itself scored 0.069, and the
    # pipeline handed back 0.408 while the report announced "-488% closer".
    if result.best.reference_score >= start.total:
        caveats.insert(0, _no_better(
            result.best.reference_score, start.total, args.budget,
            found_observations=result.best.by_level_observations.get(0.0, 1),
            started_observations=start_observations,
        ))

    # The caveat that says the headline was not searched for goes first, not ninth. A
    # reader who stops after two caveats must not stop above the one that says the
    # number they are reading came from the inversion and the screen's own probes.
    if result.unsearched and result.unsearched in caveats:
        caveats.insert(0, caveats.pop(caveats.index(result.unsearched)))

    _write_specs(args.out_dir, result, space, template_name)
    prints = {index: _render_fingerprint(renderer, probe_di,
                                         evaluator._settings(candidate.values), extra)
              for index, candidate in enumerate(result.shortlist)}
    # `seed` is the *post*-inversion vector and `start` the *pre*-inversion score, and
    # handing both to the report gave "the starting point" two meanings in one
    # document: the headline improved from the template while the shortlist's diff
    # column measured against the inverted seed, so a run that changed 16 controls
    # showed one. Both are the template now, which is what a reader means by it.
    accounting = report.summarise(store, run_id, result)
    convergence = report.convergence_from(store, run_id)
    report_path = report.write_report(
        str(args.out_dir / "report.html"), run_id=run_id, target=target,
        shortlist=result.shortlist, caveats=caveats, seed=template_values,
        seed_objectives=start.objectives, fingerprints=prints,
        convergence=convergence, summary=accounting,
        frozen=result.frozen, searched=result.searched,
        movement=result.movement, floor=result.floor, silences=result.silences,
        unheard=dropped,
        profile=args.loss_profile, reference=str(args.reference),
        seed_observations=start_observations, seed_spread=start_spread,
        seed_objective_observations=start_result.objective_observations,
        seed_objective_spreads=start_result.objective_spreads,
    )
    outside = evaluator.renders + len(extra)
    outside_sources = {
        "template": evaluator.renders,
        "inversion_probe": 0 if args.no_invert else 1,
        "report_candidates": len(result.shortlist),
    }
    command_elapsed_s = time.monotonic() - command_started_at
    command_accounting = {
        "total_renders": result.renders + outside,
        "budgeted_renders": result.renders,
        "outside_budget_renders": outside,
        "outside_budget_by_source": outside_sources,
        "elapsed_s": command_elapsed_s,
    }
    summary_path = report.write_summary(
        str(args.out_dir / "summary.json"), run_id=run_id, target=target,
        shortlist=result.shortlist, caveats=caveats, seed=template_values,
        seed_objectives=start.objectives, fingerprints=prints,
        seed_observations=start_observations, seed_spread=start_spread,
        seed_trial_score=start_result.trial.total,
        seed_trial_objectives=start_result.trial.objectives,
        seed_objective_observations=start_result.objective_observations,
        seed_objective_spreads=start_result.objective_spreads,
        inverted_seed=inverted_values, inversion_detail=inversion_detail,
        unheard=dropped,
        searched=result.searched, frozen=result.frozen,
        movement=result.movement, floor=result.floor,
        floor_observations=result.floor_observations,
        silences=result.silences,
        profile=args.loss_profile, reference=str(args.reference), pack=args.pack,
        renderer=metadata.as_dict(), budget=args.budget, accounting=accounting,
        elapsed_s=search_elapsed_s, command_accounting=command_accounting,
        out_dir=str(args.out_dir),
    )
    store.close()

    best = result.shortlist[0]
    print(f"run {run_id}")
    # Wall clock, not `result.wall_ms`, which is render time only — it said "4s" for a
    # run that took 16, and it is the number a person multiplies to decide whether
    # --budget 300 is worth starting before lunch. The render share is still shown,
    # because the gap between them is what says whether more budget or a faster
    # backend is the thing that would help.
    # Every render this command caused, not only the budgeted ones. `result.renders`
    # counts what the search spent; the template's own render, an optional inversion
    # probe and one per shortlisted candidate for the report happen outside it.
    print(f"  {result.renders + outside} renders in {command_elapsed_s:.0f}s "
          f"({result.wall_ms / 1000:.0f}s of it inside the search)"
          + (f", plus {result.cache_hits} answered from the cache"
             if result.cache_hits else ""))
    outside_sources = "the template, "
    if not args.no_invert:
        outside_sources += "the inversion's probe and "
    outside_sources += "one per shortlisted candidate for the report"
    print(f"  {result.renders} of them against the {args.budget}-render budget; "
          f"{outside} outside it — {outside_sources}")
    worst = ""
    # The reference-level estimate rather than the one render the search made: on a
    # stateful backend "it holds up" was decided by comparing a mean against a single
    # observation of the same settings, and could say so while the mean was worse.
    reached = best.reference_score
    if best.worst_level is not None and best.worst_level > reached + 5e-4:
        worst = f", {best.worst_level:.3f} at worst across ±6 dB of input level"
    elif best.worst_level is not None:
        worst = ", and it holds up across ±6 dB of input level"
    averaged = best.by_level_observations.get(0.0, 1)
    if averaged > 1 or start_observations > 1:
        worst += (f" (candidate mean of {averaged} renders; starting score mean "
                  f"of {start_observations})")
    print(f"  distance to the reference {start.total:.3f} -> {reached:.3f}{worst}")
    excerpt = target.source
    if "excerpt_start_s" in excerpt and "excerpt_end_s" in excerpt:
        print(f"  reference excerpt {excerpt['excerpt_start_s']:.6f}–"
              f"{excerpt['excerpt_end_s']:.6f} s of "
              f"{excerpt['source_duration_s']:.6f} s "
              f"({excerpt['excerpt_policy'].replace('_', ' ')})")
    print(f"  {len(result.searched)} parameters searched, "
          f"{len(result.frozen)} frozen by the screen")
    print(f"  spec:   {args.out_dir / 'match-1.json'}")
    print(f"  report: {report_path}")
    print(f"  summary: {summary_path}")
    print("\nto hear it:")
    print(f"  python3 scripts/apply_spec.py --template {args.template} \\")
    print(f"    --spec {args.out_dir / 'match-1.json'} \\")
    print(f"    --out {args.out_dir / 'match-1.xml'}")
    if caveats:
        print(f"\n{len(caveats)} caveats — read them before trusting the number "
              f"above:")
        for text in caveats:
            print(f"  - {text}")


# --- the pieces -------------------------------------------------------------


def _unmeasurable(target, audio) -> Optional[str]:
    """Why this reference cannot be matched, if it cannot be.

    Nothing checked the reference side, and the asymmetry showed: `Evaluator` is
    careful about `rendered.silent` while three seconds of digital silence went all
    the way through to a report headed "2.096 … 42% closer". `fingerprint` returns
    sentinel floors for silence — every band at −300 dB, every percentile at −240 —
    rather than `None`, so `timbre` and `dynamics` were "measured" against nothing and
    the whole run matched a number to a floor.

    The house rule is that a measurement that could not be made says so. Here it has
    to be checked before the run rather than after it: matching against silence is not
    a caveat, it is an hour of renders for an answer that means nothing.
    """
    source = (getattr(target, "source", {}) or {})
    seconds = source.get("duration_s")
    if seconds is None:
        seconds = getattr(audio, "duration_s", 0.0)
        if callable(seconds):
            seconds = seconds()
    if float(seconds) < MINIMUM_REFERENCE_S:
        selected = "selected reference excerpt" if (
            source.get("source_duration_s") is not None
            and float(source["source_duration_s"]) > float(seconds)
        ) else "reference"
        return (f"the {selected} is {float(seconds):.2f} s long, and nothing "
                f"playing-invariant can be measured from less than "
                f"{MINIMUM_REFERENCE_S:.0f} s.\n"
                f"  Give it a longer excerpt — a few seconds of the actual part is "
                f"enough, and --excerpt trims a long file.")
    bands = (getattr(target, "spectrum", {}) or {}).get("band_db") or []
    if bands and max(bands) < SILENCE_FLOOR_DB:
        return (f"the reference measures below {SILENCE_FLOOR_DB:.0f} dB in every "
                f"band, which means it is silent.\n"
                f"  Check the file plays, and that it is the guitar rather than an "
                f"empty channel of the session.")
    if (getattr(target, "source", {}) or {}).get("lufs_i") is None:
        return ("the reference has no measurable loudness, so there is nothing to "
                "match its level against.\n"
                "  It is probably too short or effectively silent; a few seconds of "
                "the actual part is enough.")
    return None


def _replicated_start(evaluator, values, requested: int):
    """The template score on the same evidence used for the published winner.

    A stateful backend makes one score a sample. The shortlist already averages
    three observations before a person reads it; doing less for the template makes
    the before-and-after verdict depend on which side drew the lucky render.
    Failed observations do not erase comparable ones, matching the benchmark's
    final-score contract.
    """
    from match.search import Candidate

    samples = []
    for _ in range(max(1, int(requested))):
        scored = evaluator.evaluate(values)
        if scored.objectives:
            samples.append(scored)
    if not samples:
        return None

    names = set().union(*(sample.objectives for sample in samples))
    values_by_objective = {
        name: [sample.objectives[name] for sample in samples
               if name in sample.objectives]
        for name in names
    }
    objectives = {
        name: sum(values) / len(values)
        for name, values in values_by_objective.items()
    }
    objective_observations = {
        name: len(values) for name, values in values_by_objective.items()
    }
    objective_spreads = {
        name: (max(values) - min(values) if len(values) > 1 else None)
        for name, values in values_by_objective.items()
    }
    totals = [sample.total for sample in samples]
    total = sum(totals) / len(totals)
    objectives["total"] = total
    candidate = Candidate(
        values=dict(values), objectives=objectives, total=total,
        trial_id=samples[0].trial_id)
    spread = max(totals) - min(totals) if len(totals) > 1 else None
    return _ReplicatedStart(
        estimate=candidate,
        trial=samples[0],
        observations=len(samples),
        spread=spread,
        objective_observations=objective_observations,
        objective_spreads=objective_spreads,
    )


def _no_better(found: float, started: float, budget: int,
               found_observations: int = 1,
               started_observations: int = 1) -> str:
    """The caveat for a run that did not improve on what it was given.

    Decided on the same number the rest of the run reports — the candidate's
    reference-level estimate. Deciding on the single search render while the summary
    line printed the replicated mean let one run say "nothing beat the preset you
    started from" beside a line showing it had, which is worse than either number
    alone.

    Both sides use the best evidence the backend calls for. If a failed render left
    one side thinner, the caveat says so instead of presenting unequal sample counts
    as the same kind of estimate.
    """
    against = (
        f" The candidate averages {found_observations} observations and the "
        f"template {started_observations}, so the comparison rests on unequal "
        f"evidence." if found_observations != started_observations else ""
    )
    return (f"nothing beat the preset you started from: it scored {started:.3f} and "
            f"the best candidate {found:.3f}, so the spec below is not an "
            f"improvement. Either the template is already close and the search is "
            f"moving inside its own noise, or {budget} renders was not enough to "
            f"recover from what the calculated step did. Keep your template."
            + against)


def _renderer(name: str, pack_id: str = "morgan"):
    """The backend, refusing the one that is still not built by name.

    `pedalboard` remains unbuilt. Accepting the flag and silently substituting the
    synthetic chain would be the worst of the three options: the run would
    succeed, the report would look right, and every number in it would describe a
    Python approximation rather than the plugin.
    """
    if name == "synthetic":
        from match.renderer_synth import SyntheticRenderer

        return SyntheticRenderer()
    if name == "swift":
        from match.renderer_au import AudioUnitError, AudioUnitRenderer

        renderer = AudioUnitRenderer(pack_id)
        try:
            # Instantiating here rather than at the first render: the plugin is
            # the one thing that can be missing, unlicensed or a different
            # version, and finding that out after the reference has been measured
            # wastes the part of the run a person is waiting through.
            renderer.metadata()
        except AudioUnitError as e:
            renderer.close()
            die(f"{e}\n"
                f"  This backend needs macOS with the plugin licensed and "
                f"installed, and swiftc from the Xcode command line tools.")
        return renderer
    die(f"the {name!r} backend is not built yet — it is M5 work, and it needs "
        f"macOS with the plugin licensed and installed.\n"
        f"  Use --renderer swift for the real plugin, or --renderer synthetic, "
        f"which is a Python approximation of the chain's topology and is what "
        f"this repository's numbers through M4 were measured against.")


def _seed_from_template(path: pathlib.Path, space, pack_id: str):
    """The template's values as the search's starting point and its prior.

    Read through `format.structured` and translated to human values, so the seed
    is what the preset actually says rather than what a recipe would have set. A
    parameter the template has and the space does not is skipped; the space's
    exclusions are deliberate and re-admitting them here would undo them.

    A file that is not a preset for this pack is refused here rather than tolerated.
    `parse_file` reads anything and `build_preset` yields zero parameters, so
    `--template pyproject.toml` used to search from an empty seed, spend the whole
    budget, write a report with a distance in it, and then print an `apply_spec.py`
    command that refuses the very file it had just been given. The one downstream tool
    that checked was the one this run told the user to go and run next.
    """
    from format.parser import parse_file
    from format.structured import build as build_preset
    from format.translate import from_binary
    from packs.loader import detect_pack, list_packs, load_pack

    pack = load_pack(pack_id)
    preset = build_preset(parse_file(str(path)))
    detected = detect_pack(preset.file_header)
    if detected is None:
        die(f"{path} does not look like a plugin preset: it identifies itself as "
            f"{preset.file_header!r}, which is not a pack this tool knows.\n"
            f"  Known packs: {', '.join(list_packs()) or 'none'}.\n"
            f"  --template takes a preset to start from, exported from the plugin.")
    if detected.pack_id != pack_id:
        named, from_pack = _template_amp(path)
        selection = f" and selects {named}" if named is not None else ""
        die(
            f"{path} is a {detected.pack_id} preset{selection}, not a preset for "
            f"pack {pack_id!r}.\n"
            f"  Pass --pack {from_pack or detected.pack_id}, or give a template "
            f"from {pack_id!r}."
        )
    values = {}
    for dimension in space.dimensions:
        parameter = preset.by_path.get((dimension.module, dimension.key))
        if parameter is None:
            continue
        # ParamSpec.path omits the leading slash for top-level controls, while
        # Pack.parameters uses `/key` as its canonical key. Morgan hid this bug:
        # most of its controls are module-scoped and selectedAmp has a fallback
        # below. Tone King's whole writable surface is top-level, so its template
        # seed was empty and every run rendered the plugin's boot state instead.
        canonical = (f"{dimension.module}/{dimension.key}"
                     if dimension.module else f"/{dimension.key}")
        spec = pack.parameters.get(canonical)
        if spec is None:
            continue
        try:
            values[(dimension.module, dimension.key)] = from_binary(
                spec.kind, parameter.value, spec.unit)
        except (ValueError, TypeError):
            # A value the translation layer will not read is a value this run must
            # not invent one for. Left out, so `active()` treats it as unstated.
            continue
    selected = preset.by_path.get(("", "selectedAmp"))
    if selected is not None:
        values[("", "selectedAmp")] = selected.value
    return values, preset.preset_name or path.stem


def _template_amp(template: pathlib.Path):
    """The amp this template selects and the pack it belongs to, for the message.

    Named rather than numbered: the raw value is a stored index, and telling somebody
    their template "selects '1'" is telling them nothing. The template's own file
    header says which plugin wrote it, so the message can say "it is a morgan preset"
    rather than leaving them to work out why their amp is not there.
    """
    from format.parser import parse_file
    from format.structured import build as build_preset
    from packs.loader import detect_pack

    preset = build_preset(parse_file(str(template)))
    parameter = preset.by_path.get(("", "selectedAmp"))
    if parameter is None:
        return None, None
    own = detect_pack(preset.file_header)
    if own is not None:
        spec = own.parameters.get("/selectedAmp")
        members = (spec.members if spec else None) or {}
        name = members.get(str(parameter.value))
        if name:
            return f"{name!r}", own.pack_id
        return f"amp {parameter.value!r}", own.pack_id
    return f"amp {parameter.value!r}", None


def _render_fingerprint(renderer, di, settings, counter=None):
    """Render and measure, counting the render if the caller is keeping a tally.

    These renders sit outside the search's budget and outside its accounting: the
    template's own render, the optional inversion probe, and one per shortlisted candidate
    for the report's overlays. The documented run reported 293 renders and performed 298. On
    the synthetic chain that is 5 spare seconds; on the M5 backend it is 5 real plugin
    renders that appear in no number anybody reads.
    """
    from analysis import io
    from analysis.fingerprint import fingerprint

    rendered = renderer.render(di, settings)
    if counter is not None:
        counter.append(1)
    return fingerprint(io.from_samples(rendered.audio, rendered.metadata.sample_rate),
                       regime="probe", excerpt_s=None)


def _write_specs(out_dir: pathlib.Path, result, space, template_name: str) -> None:
    """One spec per shortlisted candidate, numbered in the order to try them.

    Any higher-numbered spec from an earlier run in this directory is removed. A
    second run with a shorter `--shortlist` left the previous run's `match-2.json` and
    `match-3.json` sitting beside the new `match-1.json` and the new report, with
    nothing in either file saying which run it came from — so applying the runner-up
    gave you the *previous* search's runner-up. This tool's own error message for an
    `--out-dir` that is a file advises "one per run"; it should not then quietly break
    when a directory is reused.
    """
    written = set()
    for index, candidate in enumerate(result.shortlist, start=1):
        spec = space.to_spec(candidate.values, name=f"{template_name} match {index}")
        destination = out_dir / f"match-{index}.json"
        destination.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        written.add(destination)
    for stale in sorted(out_dir.glob("match-*.json")):
        if stale not in written:
            stale.unlink()


if __name__ == "__main__":
    guarded(main)
