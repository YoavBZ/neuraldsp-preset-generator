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

from _cli import die, guarded, positive_float, positive_int

REGIMES = ("paired_di", "reamp", "isolated", "mix", "probe")
RENDERERS = ("synthetic", "swift", "pedalboard")

# Below this there is not enough signal for a playing-invariant statistic to mean
# anything: one note and a gap is not a distribution of onsets.
MINIMUM_REFERENCE_S = 1.0

# `fingerprint` floors a silent band at -300 dB rather than returning None, so this is
# how silence is recognised rather than matched.
SILENCE_FLOOR_DB = -120.0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--template", type=pathlib.Path, required=True,
                    help="the preset to start from; its values are the search's prior")
    ap.add_argument("--reference", type=pathlib.Path, required=True,
                    help="the audio to match")
    ap.add_argument("--reference-mode", default="mix", choices=REGIMES,
                    help="how the guitar reaches the reference file (default: mix)")
    ap.add_argument("--probe-di", type=pathlib.Path,
                    help="the DI every candidate is rendered through. Without one a "
                         "synthetic pluck sequence is used, and the report says so")
    ap.add_argument("--pack", default="morgan", help="which plugin pack (default: morgan)")
    ap.add_argument("--amp", default=None,
                    help="restrict the search to one amp's controls, e.g. sw50r")
    ap.add_argument("--loss-profile", default="unpaired-v1",
                    help="how the objective dimensions are weighted "
                         "(unpaired-v1, paired-v1)")
    ap.add_argument("--budget", type=positive_int, default=300, metavar="RENDERS",
                    help="renders to spend (default: 300). The screen and the ±6 dB "
                         "re-rank have fixed costs that cannot be part-paid, so a "
                         "budget below about 60 is exceeded rather than trimmed, and "
                         "the run says so")
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

    evaluator = search.Evaluator(renderer, target, probe_di, space,
                                 profile=args.loss_profile, recipe=seed)
    start = evaluator.evaluate(seed)
    if not start.objectives:
        die("the template rendered nothing comparable — a silent render, or no "
            "dimension this loss profile weights could be measured on both sides.\n"
            "  Check the reference is long enough to measure and that the renderer "
            "produces audio.")

    if args.no_invert:
        caveats.append("--no-invert was given, so nothing was calculated and the "
                       "search started from the template alone")
        calculated = None
    else:
        printed = _render_fingerprint(renderer, probe_di,
                                      evaluator._settings(seed))
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
        seed = _apply(seed, calculated.as_settings(), space)
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

    result = search.search(renderer, target, probe_di, space, seed,
                           budget=args.budget, profile=args.loss_profile,
                           shortlist=args.shortlist, store=store, run_id=run_id,
                           fallbacks=[template_values],
                           rng=np.random.default_rng(args.seed))
    caveats.extend(result.caveats)

    if not result.shortlist:
        die("no candidate produced a comparable render, so there is nothing to "
            f"write. See {args.out_dir / 'trials.sqlite3'} for what was tried.")

    # Nothing checked this, and on a near-perfect template it is the whole story: the
    # bundled PR12 preset matched against a render of itself scored 0.069, and the
    # pipeline handed back 0.408 while the report announced "-488% closer".
    if result.best.total >= start.total:
        caveats.insert(0, _no_better(result.best.total, start.total, args.budget))

    _write_specs(args.out_dir, result, space, template_name)
    prints = {index: _render_fingerprint(renderer, probe_di,
                                         evaluator._settings(candidate.values))
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
        movement=result.movement,
        profile=args.loss_profile, reference=str(args.reference),
    )
    store.close()

    best = result.shortlist[0]
    print(f"run {run_id}")
    print(f"  {result.renders} renders in {result.wall_ms / 1000:.0f}s"
          + (f", plus {result.cache_hits} answered from the cache"
             if result.cache_hits else ""))
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
    """
    from format.parser import parse_file
    from format.structured import build as build_preset
    from format.translate import from_binary
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    preset = build_preset(parse_file(str(path)))
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


def _probe(path):
    """The DI every candidate is rendered through, or a synthetic stand-in.

    The stand-in is honest about being one. A search's answer is only as
    representative as the DI it was scored on: plucks with gaps show attack and
    decay clearly and show a palm-muted chug not at all, so a preset matched on
    them may not hold up on the part someone actually plays.
    """
    if path is not None:
        from analysis import io

        audio = io.load(str(path))
        return audio.mono(), None
    from tests import fixtures_audio

    return (fixtures_audio.plucks(seconds=6.0, gap=0.9, seed=13),
            "no --probe-di was given, so candidates were rendered through a "
            "synthetic pluck sequence. It shows attack and decay clearly and shows "
            "sustained or palm-muted playing not at all — match against your own "
            "DI before trusting this on a real part.")


def _render_fingerprint(renderer, di, settings):
    from analysis import io
    from analysis.fingerprint import fingerprint

    rendered = renderer.render(di, settings)
    return fingerprint(io.from_samples(rendered.audio, rendered.metadata.sample_rate),
                       regime="probe", excerpt_s=None)


def _apply(seed, calculated, space):
    """Fold the calculated values into the seed, keyed the way the space reads.

    Only paths the space knows. `invert()` emits `/selectedAmp` and Morgan's own
    parameter paths, and a path the space excluded — a mic type whose members are
    unknown, say — must not come back in through here.
    """
    known = {dimension.path: (dimension.module, dimension.key)
             for dimension in space.dimensions}
    known["selectedAmp"] = ("", "selectedAmp")
    merged = dict(seed)
    for path, value in calculated.items():
        key = known.get(path) or known.get(path.lstrip("/"))
        if key is not None:
            merged[key] = value
    return merged


def _write_specs(out_dir: pathlib.Path, result, space, template_name: str) -> None:
    """One spec per shortlisted candidate, numbered in the order to try them."""
    for index, candidate in enumerate(result.shortlist, start=1):
        spec = space.to_spec(candidate.values, name=f"{template_name} match {index}")
        destination = out_dir / f"match-{index}.json"
        destination.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    guarded(main)
