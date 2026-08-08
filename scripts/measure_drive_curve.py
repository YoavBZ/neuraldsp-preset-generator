"""Measure amp breakup as THD over volume and input level.

    python scripts/measure_drive_curve.py --pack morgan
    python scripts/measure_drive_curve.py --pack morgan --amp pr12

This is a macOS calibration tool, not a CI test: it needs the licensed Audio
Unit. It writes ``packs/<pack>/drive_curve.json``; the plugin-free schema tests
then keep checking that committed measurement.

Every point uses a new ``au_render`` process and therefore a new plugin instance.
That is deliberately slower than the batched renderer. Morgan varies between
renders in a reused instance, while fresh processes are bit-exact. A committed
calibration is a measured fact, so speed is the wrong trade here.

The excitation is a two-second sine at 222.65625 Hz, exactly on a 4096-point
analysis bin at 48 kHz. THD is the root-sum-square of harmonics 2 through 8
relative to the fundamental. The surface changes both the amp's volume control
and the input amplitude because breakup position depends strongly on both.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(SCRIPT_ROOT))

from _cli import die, guarded, positive_float
from spectrum_diff import harmonics, nearest_bin, samples


SCHEMA = "drive-curve-1"
SAMPLE_RATE = 48000
BLOCK_FRAMES = 512
FUNDAMENTAL_HZ = 222.65625
HARMONIC_COUNT = 8
DEFAULT_LEVELS = (0.015, 0.05, 0.15, 0.30)
DEFAULT_POSITIONS = tuple(float(value) for value in range(10, 101, 10))
DEFAULT_SETTLE_MS = 200.0
DEFAULT_OUTPUT_GAIN_DB = -6.0
RENDER_SOURCE = SCRIPT_ROOT / "au_render.swift"


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
    controls = _volume_controls(pack, args.amp)
    if not controls:
        die(
            f"packs/{args.pack} declares no writable <amp>Amp/<amp>Volume control"
            + (f" for {args.amp}" if args.amp else "")
            + ".\n  Nothing was measured; check --amp against the manifest."
        )

    out = args.out or PLUGIN_ROOT / "packs" / args.pack / "drive_curve.json"
    grid_renders = len(controls) * len(levels) * len(positions)
    repeats = len(controls)
    print(
        f"{args.pack}: {len(controls)} amp(s), {len(levels)} input levels, "
        f"{len(positions)} volume positions"
    )
    print(f"  {grid_renders} grid renders + {repeats} exact-repeat checks")
    print(f"  sine {frequency:g} Hz; one fresh plugin process per render")
    for amp, spec in controls.items():
        print(f"  {amp}: {spec.path}")
    if args.dry_run:
        print(f"\n--dry-run: would write {out}")
        return

    from analysis import require

    require("measuring an amp drive curve")

    started = time.time()
    with tempfile.TemporaryDirectory(prefix="drive-curve-") as directory:
        workdir = pathlib.Path(directory)
        binary = workdir / "au_render"
        _compile(binary)
        version = _plugin_version(args.pack)
        measured: Dict[str, Any] = {}
        for amp, spec in controls.items():
            measured[amp] = _measure_amp(
                binary=binary,
                workdir=workdir,
                triple=pack.audio_unit,
                pack=pack,
                amp=amp,
                spec=spec,
                levels=levels,
                positions=positions,
                frequency=frequency,
                settle_ms=float(args.settle),
                output_gain_db=float(args.output_gain),
            )

    reproducible = all(
        rows["repeat_verification"]["byte_exact"] for rows in measured.values()
    )
    if not reproducible:
        die(
            "a fresh-process repeat was not byte-exact, so this run cannot be "
            "committed as a reproducible calibration. Diagnose the host before "
            "measuring again."
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
            "renderer_id": "swift-one-shot",
            "sample_rate": SAMPLE_RATE,
            "block_size": BLOCK_FRAMES,
            "plugin_version": version,
            "renderer_build": _renderer_build(),
            "quality_mode": (
                f"fresh-process;settle_ms={float(args.settle):g};"
                f"output_gain_db={float(args.output_gain):g}"
            ),
            "reproducible": True,
            "band_noise_db": 0.0,
            "notes": [
                "every THD point instantiated a new Audio Unit process",
                "one repeated point per amp was byte-exact before the file was written",
            ],
        },
        "amps": measured,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    print(f"\nwrote {out} in {time.time() - started:.0f}s")
    for amp, rows in measured.items():
        verification = rows["repeat_verification"]
        print(
            f"  {amp}: repeat at {verification['position_percent']:g}% / "
            f"{verification['input_level']:g} was byte-exact"
        )
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
    found = {}
    for amp in sorted(set(pack.amp_modules.values())):
        spec = pack.parameters.get(f"{amp}Amp/{amp}Volume")
        if spec is not None and spec.writable and (only is None or only == amp):
            found[amp] = spec
    return found


def _compile(binary: pathlib.Path) -> None:
    from _swift import compile_swift

    built, error = compile_swift(RENDER_SOURCE, binary)
    if built is None or built.returncode != 0:
        die(f"could not build {RENDER_SOURCE.name}:\n{error}")


def _plugin_version(pack_id: str) -> str:
    from match.renderer_au import AudioUnitError, AudioUnitRenderer

    try:
        with AudioUnitRenderer(pack_id) as renderer:
            version = renderer.metadata().plugin_version
    except AudioUnitError as error:
        die(str(error))
    if version in ("", "n/a", "unknown"):
        die("the Audio Unit did not report its version; calibration provenance is incomplete")
    return version


def _measure_amp(
    *, binary: pathlib.Path, workdir: pathlib.Path, triple: Mapping[str, str],
    pack, amp: str, spec, levels: Sequence[float], positions: Sequence[float],
    frequency: float, settle_ms: float, output_gain_db: float,
) -> Dict[str, Any]:
    curves: List[Dict[str, Any]] = []
    rendered: Dict[Tuple[float, float], pathlib.Path] = {}
    clipped = 0
    silent = 0
    print(f"\n  {amp}")
    for level in levels:
        points = []
        for position in positions:
            path = workdir / f"{amp}-l{level:g}-v{position:g}.wav"
            stored = pack.to_stored(spec, position)
            _render(binary, triple, spec.path, stored, path, level,
                    frequency, settle_ms, output_gain_db)
            point = _analyse(path, position, stored, frequency)
            rendered[(level, position)] = path
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
    repeated = workdir / f"{amp}-repeat.wav"
    stored = pack.to_stored(spec, repeat_position)
    _render(binary, triple, spec.path, stored, repeated,
            repeat_level, frequency, settle_ms, output_gain_db)
    first_hash = _sha256(first)
    repeated_hash = _sha256(repeated)

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
    return {
        "control": spec.path,
        "curves": curves,
        "repeat_verification": {
            "input_level": float(repeat_level),
            "position_percent": float(repeat_position),
            "sha256_first": first_hash,
            "sha256_repeat": repeated_hash,
            "byte_exact": first_hash == repeated_hash,
        },
        "caveats": caveats,
    }


def _render(binary: pathlib.Path, triple: Mapping[str, str], control: str,
            stored: str, out: pathlib.Path, level: float, frequency: float,
            settle_ms: float, output_gain_db: float) -> None:
    missing = [key for key in ("type", "subtype", "manufacturer") if not triple.get(key)]
    if missing:
        die(f"the pack declares no {', '.join(missing)} Audio Unit field(s)")
    command = _command(binary, triple, control, stored, out, level,
                       frequency, settle_ms, output_gain_db)
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 or not out.is_file():
        die(
            f"fresh-process render failed for {control}={stored} at input {level:g} "
            f"(exit {result.returncode}).\n  {result.stderr.strip()}"
        )


def _command(binary: pathlib.Path, triple: Mapping[str, str], control: str,
             stored: str, out: pathlib.Path, level: float, frequency: float,
             settle_ms: float, output_gain_db: float) -> List[str]:
    return [
        str(binary), triple["type"], triple["subtype"], triple["manufacturer"],
        control, str(stored), str(out), format(float(level), ".12g"),
        f"sine:{format(float(frequency), '.12g')}", "--settle",
        format(float(settle_ms), ".12g"), "--output-gain",
        format(float(output_gain_db), ".12g"),
    ]


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


def _renderer_build() -> str:
    digest = hashlib.sha256(RENDER_SOURCE.read_bytes()).hexdigest()
    return f"au-render-{digest[:12]}"


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    guarded(main)
