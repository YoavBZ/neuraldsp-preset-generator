"""
Measure what each graphic-EQ band actually does, and write it down.

    python scripts/measure_eq_basis.py --pack morgan
    python scripts/measure_eq_basis.py --pack morgan --amp sw50r --gain 6

This is NOT part of the test suite and cannot be: it needs macOS, a licensed
copy of the plugin, and the plugin installed as an Audio Unit. What it produces —
`packs/<pack>/eq_basis.json` — is committed, and `tests/test_calibration_schema.py`
checks that file with no plugin at all.

**Why this exists.** `match/invert.py` fits a spectral difference onto nine fixed
band gains, and until this file exists it does so against textbook peaking
filters. Every run says so:

    nobody has measured this amp's equaliser yet … so the band gains were worked
    out from textbook filter shapes. The real bands overlap differently, so
    expect these to be a couple of dB out and to spill into their neighbours.

That caveat named the largest known error in the pipeline. This replaces the
guess with a measurement.

**Method.** For each band: render the amp with that band at `+gain`, then at
`-gain`, everything else flat, and take the third-octave difference between the
two. Half that difference, divided by the gain, is the band's response in dB per
dB of band gain — a row of the basis matrix `fit_graphic_eq` solves against.

Both signs rather than one against a flat reference, which is what the plan
budgeted for. It costs nine extra renders per amp — about three seconds — and it
cancels every even-order term: anything the chain does that is symmetric about
flat, including an amp that is driven slightly harder by a boost, drops out of a
difference taken between +g and -g instead of between +g and nothing. The flat
render is still made, and still used, to check that the measurement was linear.

**What is measured is a chain, not a filter.** The band sits inside the amp's
signal path with a cab after it, so a row is what that band does *to this amp's
output*, which is exactly what the fit needs and is not the same as the band's
own transfer function. It is therefore measured per amp, and a row is only valid
for the amp it was measured on.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded, positive_float
from _calibration import CalibrationError, signal_paths, spec_for

# The gain to measure at. Large enough to sit well clear of the plugin's own
# per-render variation (about 0.23 dB per band), small enough to stay inside the
# declared +/-12 dB range with room to spare.
DEFAULT_GAIN_DB = 6.0

# How far a band may sit from linear before the measurement is called into
# question. Compares the flat render against the mean of the +g and -g renders:
# on a linear chain those are the same spectrum, so anything above this is the
# chain bending, and the row is a secant rather than a tangent.
LINEARITY_TOLERANCE_DB = 0.75

# RMS of the excitation. Chosen so a flat render sits well below full scale on
# all three of Morgan's amps: at 0.1 the loudest band render peaked at 1.375, and
# what happens above full scale is the plugin's business rather than the band's.
DEFAULT_LEVEL = 0.03

# The schema version of the file this writes. In the file because a consumer has
# to be able to refuse a shape it does not understand rather than index into it.
SCHEMA = "eq-basis-1"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--pack", default="morgan",
                    help="which plugin pack to measure (default: morgan)")
    ap.add_argument("--amp", default=None,
                    help="measure one amp's equaliser (default: every amp the "
                         "pack declares bands for)")
    ap.add_argument("--gain", type=positive_float, default=DEFAULT_GAIN_DB,
                    metavar="DB",
                    help=f"band gain to measure at (default: {DEFAULT_GAIN_DB})")
    ap.add_argument("--seconds", type=positive_float, default=4.0,
                    help="length of the noise burst each render is measured on "
                         "(default: 4)")
    ap.add_argument("--level", type=positive_float, default=DEFAULT_LEVEL,
                    help=f"RMS of the noise fed to the plugin (default: "
                         f"{DEFAULT_LEVEL}). Lower it if a render peaks at or "
                         f"above full scale, which the run reports")
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="where to write (default: packs/<pack>/eq_basis.json)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would be measured and write nothing")
    return ap


def main() -> None:
    args = build_parser().parse_args()

    from analysis import require

    require("measuring an equaliser")

    import numpy as np

    from packs.loader import load_pack

    pack = load_pack(args.pack)
    try:
        paths = _paths_with_bands(pack, args.amp)
    except CalibrationError as error:
        die(str(error))
    if not paths:
        die(f"packs/{args.pack} declares no graphic-EQ bands"
            + (f" for {args.amp}" if args.amp else "")
            + f".\n  Nothing to measure — check --amp against "
              f"packs/{args.pack}/manifest.json.")

    out = args.out or PLUGIN_ROOT / "packs" / args.pack / "eq_basis.json"
    renders = (2 * sum(len(bands) for _, bands in paths.values())) + 2 * len(paths)
    print(f"{args.pack}: {len(paths)} signal path(s), "
          f"{sum(len(b) for _, b in paths.values())} bands, {renders} renders")
    for name, (_, bands) in paths.items():
        print(f"  {name}: {len(bands)} bands at "
              f"{', '.join(str(int(c)) for _, c in bands)} Hz")
    if args.dry_run:
        print(f"\n--dry-run: would write {out}")
        return

    from match.renderer_au import AudioUnitError, AudioUnitRenderer

    di = _excitation(args.seconds, args.level)
    started = time.time()
    try:
        renderer = AudioUnitRenderer(args.pack)
    except AudioUnitError as e:
        die(str(e))

    try:
        metadata = renderer.metadata()
        print(f"\nthrough {metadata.renderer_id} {metadata.plugin_version}\n")
        measured = {}
        for name, (path, bands) in paths.items():
            measured[name] = _measure_path(renderer, pack, path, bands, di,
                                           float(args.gain), np)
    except AudioUnitError as e:
        die(str(e))
    finally:
        renderer.close()

    measured_floor = max(
        rows["repeat_verification"]["max_band_difference_db"]
        for rows in measured.values()
    )
    metadata = dataclasses.replace(metadata, band_noise_db=measured_floor)
    document = {
        "schema": SCHEMA,
        "pack": args.pack,
        "gain_db": float(args.gain),
        "excitation": (f"deterministic white noise, {args.seconds:g} s, "
                       f"RMS {args.level:g}, seed 20250806"),
        "level": float(args.level),
        "analysis_centres_hz": measured[next(iter(measured))]["analysis_centres_hz"],
        # The backend that produced every number below, and whether it repeats
        # itself. It does not: this is a reused plugin instance, and the repository
        # does not commit a figure from one without saying so beside it.
        "renderer": metadata.as_dict(),
        "amps": {amp: _without(rows, "analysis_centres_hz")
                 for amp, rows in measured.items()},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    print(f"\nwrote {out} in {time.time() - started:.0f}s")
    if not metadata.reproducible:
        print(f"\n  Measured on a reused plugin instance, which does not repeat "
              f"itself: two\n  renders of identical parameters move a third-octave "
              f"band by up to\n  {metadata.band_noise_db:g} dB. Rows below that are "
              f"noise, and `renderer.reproducible`\n  in the file records this so a "
              f"reader cannot miss it.")
    for amp, rows in measured.items():
        for note in rows["caveats"]:
            print(f"  {amp}: {note}")


def _paths_with_bands(pack, only):
    """Every declared signal path with an ordered, centred EQ bank.

    Paths and controls come from pack topology, while frequencies remain facts on
    each ParamSpec. A path with a partially declared bank is refused rather than
    silently measured as a smaller equaliser.
    """
    found = {}
    for name, path in signal_paths(pack).items():
        if only is not None and only != name:
            continue
        bands = []
        for control in path.eq_band_controls:
            spec = spec_for(pack, control)
            if spec.centre_hz is None:
                raise CalibrationError(
                    f"{control} is an EQ band on {name} but declares no centre_hz"
                )
            bands.append((control, float(spec.centre_hz)))
        centres = [centre for _, centre in bands]
        if centres != sorted(centres) or len(centres) != len(set(centres)):
            raise CalibrationError(
                f"{name} EQ controls are not ordered at unique increasing centres: "
                f"{centres}"
            )
        if bands:
            found[name] = (path, bands)
    return found


def _excitation(seconds: float, level: float = DEFAULT_LEVEL):
    """Full-band noise, the same every run.

    Noise rather than a sweep because the measurement is a difference of
    third-octave averages: what matters is that every band has energy in it and
    that both renders see the identical signal, which a fixed seed guarantees.
    """
    import numpy as np

    from analysis import SAMPLE_RATE

    rng = np.random.default_rng(20250806)
    frames = int(seconds * SAMPLE_RATE)
    return (rng.standard_normal(frames) * level).astype(np.float32)


def _measure_path(renderer, pack, path, bands, di, gain_db: float, np):
    """One signal path's basis: output dB per dB of each band gain."""
    from analysis.features import third_octave_bands

    def render(settings):
        result = renderer.render(di, settings)
        if result.silent:
            # Silence is not evidence about a control, and it is certainly not a
            # basis row. Refused here rather than divided by.
            raise SystemExit(
                f"error: {path.name} rendered silence, so nothing about its equaliser "
                f"was measured.\n"
                f"  The repository's rule is that a silent render is not evidence "
                f"about a control either way — this is a hosting problem to fix "
                f"before the measurement means anything."
            )
        mono = np.asarray(result.audio, dtype=np.float64).mean(axis=1)
        spectrum = third_octave_bands(mono, renderer.sample_rate)
        return (np.asarray(spectrum["band_db"], dtype=np.float64),
                [float(c) for c in spectrum["band_centres_hz"]],
                result.peak)

    base = _flat_settings(pack, path, bands)
    flat_db, centres, flat_peak = render(base)
    repeated_db, repeated_centres, repeated_peak = render(base)
    if repeated_centres != centres:
        raise SystemExit("error: repeated flat render changed analysis centres")
    repeat_delta = np.abs(repeated_db - flat_db)
    repeat_at = int(np.argmax(repeat_delta))
    repeat_max = float(repeat_delta[repeat_at])
    print(
        f"  {path.name}: flat reference, peak {flat_peak:.3f}; identical-state "
        f"floor {repeat_max:.2f} dB at {centres[repeat_at]:g} Hz"
    )

    rows, caveats, peaks = [], [], [flat_peak, repeated_peak]
    for index, (control, centre) in enumerate(bands, start=1):
        up, _, up_peak = render({**base, control: gain_db})
        down, _, down_peak = render({**base, control: -gain_db})
        peaks.extend((up_peak, down_peak))
        # The symmetric estimate. Every even-order term cancels, so this is the
        # band's slope through flat rather than a chord from flat to +g.
        slope = (up - down) / (2.0 * gain_db)
        rows.append(slope)

        # And the check that the slope is worth having: on a linear chain the mean
        # of the two renders is the flat one.
        residual = np.abs((up + down) / 2.0 - flat_db)
        # A reused plugin is not exact. An identical-state repeat gives one
        # observed floor per analysis band; only curvature above that floor is
        # evidence that the EQ response itself is nonlinear.
        excess = np.maximum(0.0, residual - repeat_delta)
        audible = flat_db >= float(flat_db.max()) - 50.0
        # Curvature where this control moves the output by less than 0.3 dB at
        # the measured +/-6 dB range cannot make its fitted coefficient wrong;
        # it is unrelated chain/noise movement. This also prevents every row
        # being judged by 25 Hz merely because that is the noisiest cab band.
        influenced = np.abs(slope) >= 0.05
        relevant = audible & influenced
        if not bool(relevant.any()):
            relevant = audible
        bend_at = int(np.argmax(np.where(relevant, excess, -1.0)))
        bend = float(residual[bend_at])
        bend_excess = float(excess[bend_at])
        if bend_excess > LINEARITY_TOLERANCE_DB:
            caveats.append(
                f"band {index} at {centre:g} Hz bends {bend_excess:.2f} dB "
                f"beyond the {repeat_delta[bend_at]:.2f} dB identical-state "
                f"spread at {centres[bend_at]:g} Hz and +/-{gain_db:g} dB, so "
                f"its row is a secant through "
                f"that range rather than the band's slope. A fit far from "
                f"{gain_db:g} dB will be off."
            )
        peak_at = max(up_peak, down_peak)
        print(f"  {path.name}: band {index} at {centre:>6g} Hz, "
              f"peak {peak_at:.3f}, bend {bend_excess:.2f} dB above floor")

    if max(peaks) >= 1.0:
        caveats.append(
            f"a render peaked at {max(peaks):.3f}, at or above full scale. If "
            f"anything after the equaliser clips, part of what was measured is "
            f"the clipping rather than the band — re-run with a quieter "
            f"excitation before trusting these rows."
        )

    return {
        "band_controls": [control for control, _ in bands],
        "band_centres_hz": [centre for _, centre in bands],
        "analysis_centres_hz": centres,
        # Row i is what 1 dB on band i does at each analysis centre.
        "basis_db_per_db": [[round(float(v), 6) for v in row] for row in rows],
        "flat_band_db": [round(float(v), 3) for v in flat_db],
        "peak": round(float(max(peaks)), 4),
        "repeat_verification": {
            "max_band_difference_db": round(repeat_max, 6),
            "max_at_hz": centres[repeat_at],
            "band_difference_db": [round(float(v), 6) for v in repeat_delta],
        },
        "caveats": caveats,
    }


def _flat_settings(pack, path, bands):
    """Everything that has to be true for a band to be the only thing moving.

    The equaliser on, every band at zero, the corners out of the way, the amp
    selected, and the gate off — a gate that closes on part of the noise would put
    its own spectrum into the difference.
    """
    settings = dict(path.settings)
    for control in path.eq_enable_controls:
        settings[control] = True
    for control, _ in bands:
        settings[control] = 0.0
    for control, extreme in ((path.eq_hpf_control, "min"),
                             (path.eq_lpf_control, "max")):
        if control is None:
            continue
        spec = spec_for(pack, control)
        if spec is not None:
            value = spec.min if extreme == "min" else spec.max
            if value is not None:
                settings[control] = float(value)
    return settings


def _without(mapping, key):
    return {name: value for name, value in mapping.items() if name != key}


if __name__ == "__main__":
    guarded(main)
