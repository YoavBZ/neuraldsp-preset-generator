"""Measure amp breakup as THD over volume and input level.

    python scripts/measure_drive_curve.py --pack morgan
    python scripts/measure_drive_curve.py --pack morgan --amp pr12

This is a macOS calibration tool, not a CI test: it needs the licensed Audio
Unit. It writes ``packs/<pack>/drive_curve.json``; the plugin-free schema tests
then keep checking that committed measurement.

Every point uses a fresh plugin process through ``AudioUnitRenderer``. The Swift
host and input files are retained, but the Audio Unit instance is not. That is
deliberately slower than a reused instance. Fresh processes are bit-exact for
Morgan but not for Tone King, so the command repeats one point on every signal
path and records the observed difference. A committed calibration is a measured
fact, so speed is the wrong trade here.

The excitation is a two-second sine at 222.65625 Hz, exactly on a 4096-point
analysis bin at 48 kHz. THD is the root-sum-square of harmonics 2 through 8
relative to the fundamental. The surface changes both the amp's volume control
and the input amplitude because breakup position depends strongly on both.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import pathlib
import sys
import tempfile
import time
from typing import Any, Dict, Iterable, List, Sequence, Tuple

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(SCRIPT_ROOT))

from _cli import die, guarded, positive_float
from _calibration import CalibrationError, signal_paths, spec_for
from spectrum_diff import harmonics, nearest_bin, samples


SCHEMA = "drive-curve-1"
SAMPLE_RATE = 48000
FUNDAMENTAL_HZ = 222.65625
HARMONIC_COUNT = 8
DEFAULT_LEVELS = (0.015, 0.05, 0.15, 0.30)
DEFAULT_POSITIONS = tuple(float(value) for value in range(10, 101, 10))
DEFAULT_SETTLE_MS = 200.0
DEFAULT_OUTPUT_GAIN_DB = -6.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pack", default="morgan",
                        help="which installed plugin pack to measure (default: morgan)")
    parser.add_argument("--amp", default=None,
                        help="measure one amp prefix (default: every amp with a Volume control)")
    parser.add_argument("--levels", nargs="+", type=positive_float,
                        default=list(DEFAULT_LEVELS), metavar="AMPLITUDE",
                        help="input sine peak amplitudes (default: 0.015 0.05 0.15 0.30)")
    parser.add_argument("--positions", nargs="+", type=float,
                        default=list(DEFAULT_POSITIONS), metavar="PERCENT",
                        help="human volume positions in percent (default: 10 20 ... 100)")
    parser.add_argument("--frequency", type=positive_float,
                        default=FUNDAMENTAL_HZ, metavar="HZ",
                        help=f"bin-centred test frequency (default: {FUNDAMENTAL_HZ})")
    parser.add_argument("--settle", type=float, default=DEFAULT_SETTLE_MS,
                        metavar="MS", help="pause after the state write (default: 200)")
    parser.add_argument("--output-gain", type=float, default=DEFAULT_OUTPUT_GAIN_DB,
                        metavar="DB", help="post-amp output headroom (default: -6)")
    parser.add_argument("--out", type=pathlib.Path, default=None,
                        help="where to write (default: packs/<pack>/drive_curve.json)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the measurement grid and write nothing")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    levels = _levels(args.levels)
    positions = _positions(args.positions)
    frequency = _frequency(float(args.frequency))
    if args.settle < 0:
        die("--settle must be non-negative")
    if not -24.0 <= args.output_gain <= 0.0:
        die("--output-gain must be between -24 and 0 dB")

    from packs.loader import load_pack

    pack = load_pack(args.pack)
    try:
        controls = _volume_controls(pack, args.amp)
    except CalibrationError as error:
        die(str(error))
    if not controls:
        die(
            f"packs/{args.pack} declares no calibration path with a volume control"
            + (f" for {args.amp}" if args.amp else "")
            + ".\n  Nothing was measured; check --amp against the manifest."
        )

    out = args.out or PLUGIN_ROOT / "packs" / args.pack / "drive_curve.json"
    grid_renders = len(controls) * len(levels) * len(positions)
    repeats = len(controls)
    print(
        f"{args.pack}: {len(controls)} signal path(s), {len(levels)} input levels, "
        f"{len(positions)} volume positions"
    )
    print(f"  {grid_renders} grid renders + {repeats} exact-repeat checks")
    print(f"  sine {frequency:g} Hz; one fresh plugin process per render")
    for name, path in controls.items():
        print(f"  {name}: {path.volume_control}")
    if args.dry_run:
        print(f"\n--dry-run: would write {out}")
        return

    from analysis import require

    require("measuring an amp drive curve")

    started = time.time()
    from match.renderer_au import AudioUnitError, AudioUnitRenderer

    with tempfile.TemporaryDirectory(prefix="drive-curve-") as directory:
        workdir = pathlib.Path(directory)
        renderer = AudioUnitRenderer(
            args.pack,
            settle_ms=float(args.settle),
            process_policy="fresh",
        )
        measured: Dict[str, Any] = {}
        try:
            metadata = renderer.metadata()
            if metadata.plugin_version in ("", "n/a", "unknown"):
                die("the Audio Unit did not report its version; calibration provenance is incomplete")
            for name, path in controls.items():
                measured[name] = _measure_path(
                    renderer=renderer,
                    workdir=workdir,
                    pack=pack,
                    path=path,
                    levels=levels,
                    positions=positions,
                    frequency=frequency,
                    output_gain_db=float(args.output_gain),
                )
        except AudioUnitError as error:
            die(str(error))
        finally:
            renderer.close()

    repeat_exact = all(
        rows["repeat_verification"]["byte_exact"] for rows in measured.values()
    )
    if metadata.reproducible and not repeat_exact:
        for name, rows in measured.items():
            repeat = rows["repeat_verification"]
            if not repeat["byte_exact"]:
                print(
                    f"  {name}: repeat differed by {repeat['relative_error_db']:.2f} dB "
                    f"relative to the signal; max sample delta "
                    f"{repeat['max_abs_difference']:.9f}; max band delta "
                    f"{repeat['max_band_difference_db']:.2f} dB at "
                    f"{repeat['max_band_difference_hz']:g} Hz"
                )
        die(
            "the backend claimed reproducible=True but a fresh-process repeat was "
            "not byte-exact. Nothing was written; fix the renderer metadata or the "
            "host before measuring again."
        )
    measured_floor = max(
        rows["repeat_verification"]["max_band_difference_db"]
        for rows in measured.values()
    )
    if not repeat_exact:
        notes = tuple(metadata.notes) + (
            f"fresh-process repeats in this run moved a third-octave band by up "
            f"to {measured_floor:g} dB",
        )
        metadata = dataclasses.replace(
            metadata,
            reproducible=False,
            band_noise_db=max(metadata.band_noise_db, measured_floor),
            notes=notes,
        )

    document = {
        "schema": SCHEMA,
        "pack": args.pack,
        "fundamental_hz": frequency,
        "harmonic_count": HARMONIC_COUNT,
        "input_levels": levels,
        "positions_percent": positions,
        "excitation": (
            f"2 s sine at {frequency:g} Hz, a 4096-point analysis-bin centre "
            f"at {SAMPLE_RATE} Hz"
        ),
        "process_policy": "one fresh plugin process per render",
        "output_gain_db": float(args.output_gain),
        "renderer": {
            **metadata.as_dict(),
            "notes": list(metadata.notes) + [
                ("one repeated point per signal path was byte-exact before the file was written"
                 if repeat_exact else
                 "one repeated point per signal path was checked; at least one differed, "
                 "so renderer.reproducible is false"),
            ],
        },
        "amps": measured,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    print(f"\nwrote {out} in {time.time() - started:.0f}s")
    for amp, rows in measured.items():
        verification = rows["repeat_verification"]
        if verification["byte_exact"]:
            outcome = "was byte-exact"
        else:
            outcome = (
                f"differed by {verification['relative_error_db']:.2f} dB relative "
                f"to the signal and {verification['max_band_difference_db']:.2f} "
                f"dB in the noisiest band"
            )
        print(f"  {amp}: repeat at {verification['position_percent']:g}% / "
              f"{verification['input_level']:g} {outcome}")
        for caveat in rows["caveats"]:
            print(f"  {amp}: {caveat}")


def _levels(values: Iterable[float]) -> List[float]:
    levels = sorted({float(value) for value in values})
    if len(levels) < 3:
        die("measure at least three distinct --levels; drive is an input-level surface")
    if len(levels) > 4:
        die("measure at most four distinct --levels; the committed schema is a 3–4 level surface")
    if any(value <= 0.0 or value > 1.0 for value in levels):
        die("every --levels value must be greater than 0 and at most 1")
    return levels


def _positions(values: Iterable[float]) -> List[float]:
    positions = sorted({float(value) for value in values})
    if len(positions) < 2:
        die("measure at least two distinct --positions")
    if any(value < 0.0 or value > 100.0 for value in positions):
        die("every --positions value must be between 0 and 100 percent")
    return positions


def _frequency(value: float) -> float:
    exact = nearest_bin(value, SAMPLE_RATE)
    if abs(value - exact) > 1e-9:
        die(
            f"{value:g} Hz is not on the {SAMPLE_RATE / 4096:.5f} Hz analysis "
            f"grid. Use {exact:.5f} Hz and render the sine there too."
        )
    if HARMONIC_COUNT * value >= SAMPLE_RATE / 2:
        die(
            f"{value:g} Hz puts harmonic {HARMONIC_COUNT} at or above Nyquist; "
            "choose a lower bin-centred frequency"
        )
    return value


def _volume_controls(pack, only: str | None) -> Dict[str, Any]:
    return {
        name: path for name, path in signal_paths(pack).items()
        if path.volume_control is not None and (only is None or only == name)
    }


def _measure_path(
    *, renderer, workdir: pathlib.Path, pack, path,
    levels: Sequence[float], positions: Sequence[float],
    frequency: float, output_gain_db: float,
) -> Dict[str, Any]:
    assert path.volume_control is not None
    spec = spec_for(pack, path.volume_control)
    base = dict(path.settings)
    if path.output_gain_control is None:
        die(f"{path.name} declares no output_gain_control; THD could clip downstream")
    base[path.output_gain_control] = output_gain_db
    curves: List[Dict[str, Any]] = []
    rendered: Dict[Tuple[float, float], pathlib.Path] = {}
    clipped = 0
    silent = 0
    print(f"\n  {path.name}")
    # Move the highest-risk point to the front without adding a render. If it
    # clips or vanishes, waiting through the other 39 points cannot rescue this
    # calibration, and the same file/result is reused when the grid reaches it.
    preflight_level = max(levels)
    preflight_position = max(positions)
    preflight_di = _sine(preflight_level, frequency)
    preflight_out = workdir / (
        f"{path.name}-l{preflight_level:g}-v{preflight_position:g}.wav"
    )
    preflight_human = _position_value(spec, preflight_position)
    preflight_stored = pack.to_stored(spec, preflight_human)
    _render(renderer, preflight_di,
            {**base, path.volume_control: preflight_human}, preflight_out)
    preflight_point = _analyse(
        preflight_out, preflight_position, preflight_stored, frequency
    )
    if preflight_point["silent"]:
        die(f"{path.name}'s loudest drive point rendered silence; nothing was measured")
    if preflight_point["clipped"]:
        die(
            f"{path.name}'s loudest drive point peaked at "
            f"{preflight_point['output_peak']:.3f}. Re-run with a lower "
            "--output-gain before measuring the grid."
        )
    print(f"    preflight {preflight_level:g} input / {preflight_position:g}%: "
          f"peak {preflight_point['output_peak']:.3f}, no clipping")

    for level in levels:
        di = _sine(level, frequency)
        points = []
        for position in positions:
            out = workdir / f"{path.name}-l{level:g}-v{position:g}.wav"
            human = _position_value(spec, position)
            stored = pack.to_stored(spec, human)
            if level == preflight_level and position == preflight_position:
                point = preflight_point
            else:
                _render(renderer, di, {**base, path.volume_control: human}, out)
                point = _analyse(out, position, stored, frequency)
            rendered[(level, position)] = out
            clipped += int(point["clipped"])
            silent += int(point["silent"])
            points.append(point)
            thd = "n/a" if point["thd_percent"] is None else f"{point['thd_percent']:.3f}%"
            print(
                f"    input {level:>5g}, volume {position:>5g}%: "
                f"THD {thd:>9}, peak {point['output_peak']:.3f}"
            )
        curves.append({
            "input_level": float(level),
            "input_peak_dbfs": round(20.0 * math.log10(level), 3),
            "points": points,
        })

    repeat_level = min(levels, key=lambda value: abs(value - 0.05))
    repeat_position = min(positions, key=lambda value: abs(value - 50.0))
    first = rendered[(repeat_level, repeat_position)]
    repeated = workdir / f"{path.name}-repeat.wav"
    human = _position_value(spec, repeat_position)
    _render(renderer, _sine(repeat_level, frequency),
            {**base, path.volume_control: human}, repeated)
    first_hash = _sha256(first)
    repeated_hash = _sha256(repeated)
    repeat_difference = _difference(first, repeated)

    caveats = [
        f"THD describes the complete amp/cab output at {output_gain_db:g} dB "
        "output trim, not an isolated preamp stage."
    ]
    if clipped:
        caveats.append(
            f"{clipped} point(s) peaked at or above full scale. Re-run with lower "
            "input levels before treating their THD as amp breakup rather than "
            "downstream clipping."
        )
    if silent:
        caveats.append(
            f"{silent} point(s) rendered silence; their THD is null rather than zero."
        )
    if first_hash != repeated_hash:
        caveats.append(
            f"fresh processes were not sample-exact at the repeated point: "
            f"{repeat_difference['relative_error_db']:.2f} dB relative waveform "
            f"error and {repeat_difference['max_band_difference_db']:.2f} dB "
            f"maximum third-octave difference. Curve values are single renders, "
            f"not exact deterministic outputs."
        )
    return {
        "control": path.volume_control,
        "curves": curves,
        "repeat_verification": {
            "input_level": float(repeat_level),
            "position_percent": float(repeat_position),
            "sha256_first": first_hash,
            "sha256_repeat": repeated_hash,
            "byte_exact": first_hash == repeated_hash,
            **repeat_difference,
        },
        "caveats": caveats,
    }


def _render(renderer, di, settings, out: pathlib.Path) -> None:
    import soundfile as sf

    result = renderer.render(di, settings)
    sf.write(str(out), result.audio, renderer.sample_rate, subtype="FLOAT")


def _sine(level: float, frequency: float):
    import numpy as np

    frames = 2 * SAMPLE_RATE
    phase = 2.0 * math.pi * frequency * np.arange(frames) / SAMPLE_RATE
    return (np.sin(phase) * level).astype(np.float32)


def _position_value(spec, percent: float) -> float:
    """Map the command's 0..100 knob position onto this control's human scale."""
    if spec.kind == "rotation":
        return float(percent)
    if spec.min is None or spec.max is None:
        raise CalibrationError(
            f"{spec.path} is {spec.kind}, so percent positions require min and max"
        )
    return float(spec.min + (spec.max - spec.min) * percent / 100.0)


def _analyse(path: pathlib.Path, position: float, stored: str,
             frequency: float) -> Dict[str, Any]:
    values = samples(str(path))
    peak = max((abs(value) for value in values), default=0.0)
    silent = peak == 0.0
    return {
        "position_percent": float(position),
        "stored_value": str(stored),
        "thd_percent": None if silent else round(float(harmonics(
            str(path), frequency, count=HARMONIC_COUNT, sr=SAMPLE_RATE
        )), 6),
        "output_peak": round(float(peak), 6),
        "silent": silent,
        "clipped": peak >= 1.0,
    }


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _difference(first: pathlib.Path, second: pathlib.Path) -> Dict[str, Any]:
    import numpy as np
    import soundfile as sf

    one, rate_one = sf.read(str(first), dtype="float64", always_2d=True)
    two, rate_two = sf.read(str(second), dtype="float64", always_2d=True)
    if rate_one != rate_two or one.shape != two.shape:
        die(
            "the fresh-process repeat changed the WAV format: "
            f"{rate_one} Hz {one.shape} became {rate_two} Hz {two.shape}. "
            "Nothing was written."
        )
    delta = one - two
    signal_rms = float(np.sqrt(np.mean(one * one)))
    delta_rms = float(np.sqrt(np.mean(delta * delta)))
    # JSON has no representation for -infinity. `None` is the exact case: there
    # is no non-zero error whose dB ratio could be reported.
    relative = (20.0 * math.log10(delta_rms / signal_rms)
                if signal_rms > 0.0 and delta_rms > 0.0 else None)
    from analysis.features import third_octave_bands

    first_bands = third_octave_bands(one.mean(axis=1), int(rate_one))
    second_bands = third_octave_bands(two.mean(axis=1), int(rate_two))
    band_delta = np.abs(
        np.asarray(first_bands["band_db"]) - np.asarray(second_bands["band_db"])
    )
    max_band = int(np.argmax(band_delta))
    return {
        "relative_error_db": None if relative is None else round(relative, 6),
        "max_abs_difference": round(float(np.max(np.abs(delta))), 9),
        "max_band_difference_db": round(float(band_delta[max_band]), 6),
        "max_band_difference_hz": float(first_bands["band_centres_hz"][max_band]),
    }


if __name__ == "__main__":
    guarded(main)
