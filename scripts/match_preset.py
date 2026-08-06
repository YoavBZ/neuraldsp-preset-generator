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
from typing import Optional

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import (die, guarded, on_interrupt, positive_float, positive_int,
                  probe_di as _probe)

REGIMES = ("paired_di", "reamp", "isolated", "mix", "probe")
RENDERERS = ("synthetic", "swift", "pedalboard")

# Below this there is not enough signal for a playing-invariant statistic to mean
# anything: one note and a gap is not a distribution of onsets.
MINIMUM_REFERENCE_S = 1.0

# `fingerprint` floors a silent band at -300 dB rather than returning None, so this is
# how silence is recognised rather than matched.
SILENCE_FLOOR_DB = -120.0


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
                         "This is not a formality — it is recorded in the fingerprint "
                         "so nothing downstream reads a mastered spectrum as an amp's. "
                         "paired_di: the reference and its own DI; reamp: your DI "
                         "through the real rig; isolated: a solo guitar track, no "
                         "band; mix: a finished mix, so the spectrum includes the "
                         "band and the master chain; probe: a render of a known "
                         "chain, which is what the benchmarks use")
    ap.add_argument("--probe-di", type=pathlib.Path,
                    help="the DI every candidate is rendered through. Without one a "
                         "synthetic pluck sequence is used, and the report says so")
    ap.add_argument("--pack", default="morgan", help="which plugin pack (default: morgan)")
    ap.add_argument("--amp", default=None,
                    help="restrict the search to one amp's controls, e.g. sw50r")
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
                         "optimiser needs at least one whole round (~12) on top. On "
                         "Morgan that is about 70 before anything is searched, and a "
                         "run that could not afford a round says so and names the "
                         "number to raise this to")
    ap.add_argument("--shortlist", type=positive_int, default=3,
                    help="how many candidates to return (default: 3)")
    ap.add_argument("--renderer", default="synthetic", choices=RENDERERS,
                    help="which backend renders a candidate (default: synthetic)")
    ap.add_argument("--excerpt", type=positive_float, default=None, metavar="SECONDS",
                    help="measure only this much of the reference")
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
    load_profile(args.loss_profile)          # fail here rather than 200 renders in

    renderer = _renderer(args.renderer)
    space = space_module.build(args.pack, amp=args.amp)
    seed, template_name = _seed_from_template(args.template, space, args.pack)
    template_values = dict(seed)

    reference = io.load(str(args.reference))
    target = fingerprint(reference, regime=args.reference_mode,
                         excerpt_s=args.excerpt)
    unmeasurable = _unmeasurable(target, reference)
    if unmeasurable:
        die(unmeasurable)
    probe_di, probe_note = _probe(args.probe_di)

    run_id = args.run_id or f"{args.out_dir.name}-{time.strftime('%Y%m%d-%H%M%S')}"
    store = open_store(str(args.out_dir))
    # Every render commits before the next one starts, and the cache is keyed on the
    # score rather than the clock, so running the same command again re-uses everything
    # this run paid for. That is the whole reason the store exists and nothing said it.
    on_interrupt(
        f"{args.out_dir / 'trials.sqlite3'} has every render made so far. Run the "
        f"same command again and they are served from the cache rather than rendered "
        f"twice — you lose the time since the last render, not the run."
    )
    metadata = renderer.metadata()
    store.start_run(Run(
        run_id=run_id, pack=args.pack, template=str(args.template),
        reference_sha=target.source.get("sha256"), regime=args.reference_mode,
        loss_profile=args.loss_profile, budget=args.budget,
        renderer_id=metadata.renderer_id, plugin_version=metadata.plugin_version,
        notes=probe_note,
    ))

    caveats = [probe_note] if probe_note else []
    if args.reference_mode == "mix":
        caveats.append(
            "the reference is a mix, so the spectrum includes the rest of the band "
            "and whatever the master chain did. Anything the guitar shares a band "
            "with — the snare, a synth pad — is being matched too"
        )
    if not metadata.reproducible:
        caveats.append(
            f"this backend does not repeat itself exactly: two renders of identical "
            f"parameters differ by about {metadata.band_noise_db:.2f} dB per band, so "
            f"a difference smaller than that between two candidates is not a "
            f"difference"
        )

    # Renders made outside `search`, so the printed total is every render this command
    # caused rather than only the budgeted ones.
    extra: list = []
    evaluator = search.Evaluator(renderer, target, probe_di, space,
                                 profile=args.loss_profile, recipe=seed)
    start = evaluator.evaluate(seed)
    if not start.objectives:
        die("the template rendered nothing comparable — a silent render, or no "
            "dimension this loss profile weights could be measured on both sides.\n"
            "  Check the reference is long enough to measure and that the renderer "
            "produces audio.")

    dropped: list = []
    if args.no_invert:
        caveats.append("--no-invert was given, so nothing was calculated and the "
                       "search started from the template alone")
        calculated = None
    else:
        printed = _render_fingerprint(renderer, probe_di,
                                      evaluator._settings(seed), extra)
        amp = args.amp or space.amp_prefix(seed)
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
            die("the template does not say which amp is selected, and no --amp was "
                "given, so there is no way to tell which amp's controls to invert.\n"
                "  Pass --amp with one of the pack's amps, or use a template with a "
                "selectedAmp value.")
        calculated = invert.invert(target, printed, amp=amp, pack_id=args.pack)
        seed = invert.apply_to(seed, calculated.as_settings(), space)
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

    started_at = time.monotonic()
    result = search.search(renderer, target, probe_di, space, seed,
                           budget=args.budget, profile=args.loss_profile,
                           shortlist=args.shortlist, store=store, run_id=run_id,
                           fallbacks=[template_values],
                           rng=np.random.default_rng(args.seed))
    elapsed_s = time.monotonic() - started_at
    caveats.extend(result.caveats)

    if not result.shortlist:
        die("no candidate produced a comparable render, so there is nothing to "
            f"write. See {args.out_dir / 'trials.sqlite3'} for what was tried.")

    # Nothing checked this, and on a near-perfect template it is the whole story: the
    # bundled PR12 preset matched against a render of itself scored 0.069, and the
    # pipeline handed back 0.408 while the report announced "-488% closer".
    if result.best.total >= start.total:
        caveats.insert(0, _no_better(result.best.total, start.total, args.budget))

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
    report_path = report.write_report(
        str(args.out_dir / "report.html"), run_id=run_id, target=target,
        shortlist=result.shortlist, caveats=caveats, seed=template_values,
        seed_objectives=start.objectives, fingerprints=prints,
        convergence=report.convergence_from(store, run_id),
        summary=report.summarise(store, run_id, result),
        frozen=result.frozen, searched=result.searched,
        movement=result.movement, floor=result.floor, silences=result.silences,
        unheard=dropped,
        profile=args.loss_profile, reference=str(args.reference),
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
    # counts what the search spent; the template's own render, the inversion's probe and
    # one per shortlisted candidate for the report happen outside it, and a run that
    # reported 293 had made 298.
    outside = evaluator.renders + len(extra)
    print(f"  {result.renders + outside} renders in {elapsed_s:.0f}s "
          f"({result.wall_ms / 1000:.0f}s of it inside the search)"
          + (f", plus {result.cache_hits} answered from the cache"
             if result.cache_hits else ""))
    print(f"  {result.renders} of them against the {args.budget}-render budget; "
          f"{outside} outside it — the template, the inversion's probe and one per "
          f"shortlisted candidate for the report")
    worst = ""
    if best.worst_level is not None and best.worst_level > best.total + 5e-4:
        worst = f", {best.worst_level:.3f} at worst across ±6 dB of input level"
    elif best.worst_level is not None:
        worst = ", and it holds up across ±6 dB of input level"
    print(f"  distance to the reference {start.total:.3f} -> {best.total:.3f}{worst}")
    print(f"  {len(result.searched)} parameters searched, "
          f"{len(result.frozen)} frozen by the screen")
    print(f"  spec:   {args.out_dir / 'match-1.json'}")
    print(f"  report: {report_path}")
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
    seconds = getattr(audio, "duration_s", 0.0)
    if callable(seconds):
        seconds = seconds()
    if float(seconds) < MINIMUM_REFERENCE_S:
        return (f"the reference is {float(seconds):.2f} s long, and nothing "
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


def _no_better(found: float, started: float, budget: int) -> str:
    """The caveat for a run that did not improve on what it was given."""
    return (f"nothing beat the preset you started from: it scored {started:.3f} and "
            f"the best candidate {found:.3f}, so the spec below is not an "
            f"improvement. Either the template is already close and the search is "
            f"moving inside its own noise, or {budget} renders was not enough to "
            f"recover from what the calculated step did. Keep your template.")


def _renderer(name: str):
    """The backend, refusing the ones that are not built yet by name.

    `swift` and `pedalboard` are M5. Accepting the flag and silently substituting
    the synthetic chain would be the worst of the three options: the run would
    succeed, the report would look right, and every number in it would describe a
    Python approximation rather than the plugin.
    """
    if name == "synthetic":
        from match.renderer_synth import SyntheticRenderer

        return SyntheticRenderer()
    die(f"the {name!r} backend is not built yet — it is M5 work, and it needs "
        f"macOS with the plugin licensed and installed.\n"
        f"  Use --renderer synthetic, which is a Python approximation of the "
        f"chain's topology and is what every number in this repository's "
        f"development so far was measured against.")


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
    if detect_pack(preset.file_header) is None:
        die(f"{path} does not look like a plugin preset: it identifies itself as "
            f"{preset.file_header!r}, which is not a pack this tool knows.\n"
            f"  Known packs: {', '.join(list_packs()) or 'none'}.\n"
            f"  --template takes a preset to start from, exported from the plugin.")
    values = {}
    for dimension in space.dimensions:
        parameter = preset.by_path.get((dimension.module, dimension.key))
        if parameter is None:
            continue
        spec = pack.parameters.get(dimension.path)
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
    template's own render, the inversion's probe, and one per shortlisted candidate for
    the report's overlays. The documented run reported 293 renders and performed 298. On
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
