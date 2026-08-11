"""Build a blind, level-matched Reference–A–B listening file.

    python scripts/build_rab_audition.py \
      --reference reference.wav --a template.wav --b candidate.wav \
      --out audition.flac

The output is one file in the order Reference, A, B, Reference, A, B, with
silence between segments. A and B are randomly assigned and revealed only in a
separate JSON key. Each segment receives one static gain to reach the same LUFS;
no EQ, compression, limiting, or other processing is applied. If the requested
level would exceed the peak ceiling, the shared target is lowered for all three.

Use this file to judge which option is closer to the reference. Judge raw renders
separately when output level itself is the question, and record "closer" and
"prefer" as separate answers.

Needs the analysis extra:  pip install -e '.[analysis]'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import random
import secrets
import shlex
import sys
import tempfile
from datetime import datetime, timezone

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded, positive_float

LOUDNESS_TOLERANCE_LU = 0.05
PEAK_TOLERANCE_DB = 0.01
MAX_LEVEL_ITERATIONS = 12


def _finite_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number") from None
    import math

    if not math.isfinite(value):
        raise argparse.ArgumentTypeError(f"must be finite, got {text!r}")
    return value


def _nonnegative_float(text: str) -> float:
    value = _finite_float(text)
    if value < 0.0:
        raise argparse.ArgumentTypeError(f"must be zero or greater, got {value:g}")
    return value


def _nonpositive_float(text: str) -> float:
    value = _finite_float(text)
    if value > 0.0:
        raise argparse.ArgumentTypeError(f"must be zero or lower, got {value:g}")
    return value


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slice(audio, start_s: float, duration_s: float):
    start = round(start_s * audio.sample_rate)
    frames = round(duration_s * audio.sample_rate)
    return audio.replace(audio.samples[start:start + frames])


def _mono(audio):
    return audio.replace(audio.mono())


def _audition_channels(audios, force_mono: bool):
    """Preserve stereo; only fold down when the caller explicitly asks."""
    import numpy as np

    if force_mono:
        return [_mono(audio) for audio in audios], 1
    if any(audio.channels > 2 for audio in audios):
        counts = ", ".join(str(audio.channels) for audio in audios)
        raise ValueError(
            f"the inputs have {counts} channels; auditions preserve mono/stereo only. "
            "Pass --mono to make an explicit channel-averaged fold-down."
        )
    channels = max(audio.channels for audio in audios)
    if channels == 1:
        return audios, 1
    return [
        audio if audio.channels == 2 else audio.replace(
            np.repeat(audio.samples, 2, axis=1)
        )
        for audio in audios
    ], 2


def _static_gain_to_lufs(clip, target_lufs: float, initial_lufs: float):
    """Converge one constant gain despite BS.1770's absolute gate.

    Integrated loudness normally moves one-for-one with gain. Near the -70 LUFS
    absolute gate, amplification can admit blocks that were previously excluded,
    changing the measured programme and invalidating a one-pass gain calculation.
    Iteration keeps the processing static while making the final claim checkable.
    """
    import numpy as np

    from analysis import io

    gain = target_lufs - initial_lufs
    best = None
    for _ in range(MAX_LEVEL_ITERATIONS):
        levelled = clip.replace(
            np.asarray(clip.samples, dtype=np.float64) * (10.0 ** (gain / 20.0))
        )
        measured = io.loudness_lufs(levelled)
        if measured is None:
            raise ValueError("loudness became unmeasurable while applying static gain")
        error = target_lufs - measured
        if best is None or abs(error) < best[0]:
            best = (abs(error), gain, levelled, measured)
        if abs(error) <= LOUDNESS_TOLERANCE_LU:
            return gain, levelled, measured
        gain += error
    assert best is not None
    if best[0] <= LOUDNESS_TOLERANCE_LU:
        return best[1], best[2], best[3]
    raise ValueError(
        f"static-gain loudness matching did not converge within "
        f"{LOUDNESS_TOLERANCE_LU:.2f} LU (best error {best[0]:.3f} LU)"
    )


def _level_with_headroom(clips, before_lufs, target_lufs: float,
                         peak_ceiling_dbtp: float):
    """Match one shared target, lowering it only enough to preserve headroom."""
    from analysis import io

    effective_target = target_lufs
    for _ in range(MAX_LEVEL_ITERATIONS):
        matched = [_static_gain_to_lufs(clip, effective_target, before)
                   for clip, before in zip(clips, before_lufs)]
        gains = [item[0] for item in matched]
        levelled = [item[1] for item in matched]
        measured = [item[2] for item in matched]
        peaks = [io.true_peak_dbtp(clip) for clip in levelled]
        overflow = max(
            (peak - peak_ceiling_dbtp for peak in peaks if peak is not None),
            default=0.0,
        )
        if overflow <= PEAK_TOLERANCE_DB:
            if any(abs(value - effective_target) > LOUDNESS_TOLERANCE_LU
                   for value in measured):
                raise ValueError("static-gain loudness verification failed")
            return effective_target, gains, levelled, measured, peaks
        effective_target -= overflow
    raise ValueError("static-gain matching could not satisfy the peak ceiling")


def build(
    *,
    reference: pathlib.Path,
    first: pathlib.Path,
    second: pathlib.Path,
    starts: tuple[float, float, float],
    duration_s: float | None,
    target_lufs: float,
    peak_ceiling_dbtp: float,
    gap_s: float,
    cycle_gap_s: float,
    seed: int,
    force_mono: bool = False,
):
    """Return the montage samples and the complete blind-key metadata."""
    import numpy as np

    from analysis import io

    paths = (reference, first, second)
    originals = [io.load(path) for path in paths]
    loaded, output_channels = _audition_channels(originals, force_mono)
    remaining = [audio.duration_s - start for audio, start in zip(loaded, starts)]
    if any(value <= 0.0 for value in remaining):
        bad = next(index for index, value in enumerate(remaining) if value <= 0.0)
        raise ValueError(
            f"start {starts[bad]:g} s is at or beyond the end of {paths[bad]} "
            f"({loaded[bad].duration_s:.3f} s)"
        )
    used_duration = min(remaining) if duration_s is None else duration_s
    if used_duration < 0.4:
        raise ValueError(
            f"the comparison segment is {used_duration:.3f} s; loudness needs at "
            "least 0.4 s, and a useful tone comparison needs longer"
        )
    if any(used_duration > value + 1e-9 for value in remaining):
        bad = next(index for index, value in enumerate(remaining)
                   if used_duration > value + 1e-9)
        raise ValueError(
            f"{paths[bad]} has only {remaining[bad]:.3f} s after its start, shorter "
            f"than --duration {used_duration:g} s"
        )

    clips = [_slice(audio, start, used_duration)
             for audio, start in zip(loaded, starts)]
    before_lufs = [io.loudness_lufs(clip) for clip in clips]
    if any(value is None for value in before_lufs):
        bad = next(index for index, value in enumerate(before_lufs) if value is None)
        raise ValueError(f"{paths[bad]} has no measurable loudness in the selected range")

    effective_target, gains, levelled, measured_after, measured_peaks = \
        _level_with_headroom(clips, before_lufs, target_lufs, peak_ceiling_dbtp)
    reduction = target_lufs - effective_target

    # The seed makes assignment reproducible while the separate key keeps a casual
    # audition blind. Reference is never randomised: it anchors every comparison.
    swap = bool(random.Random(seed).getrandbits(1))
    a_index, b_index = ((2, 1) if swap else (1, 2))
    gap = np.zeros(
        (round(gap_s * loaded[0].sample_rate), output_channels), dtype=np.float32
    )
    cycle_gap = np.zeros(
        (round(cycle_gap_s * loaded[0].sample_rate), output_channels), dtype=np.float32
    )
    order = (0, a_index, b_index, 0, a_index, b_index)
    pieces = []
    timeline = []
    cursor = 0
    labels = ("Reference", "A", "B", "Reference", "A", "B")
    for position, (label, index) in enumerate(zip(labels, order)):
        samples = levelled[index].samples
        start_frame = cursor
        pieces.append(samples)
        cursor += len(samples)
        timeline.append({
            "label": label,
            "source_role": ("reference", "first", "second")[index],
            "start_s": round(start_frame / loaded[0].sample_rate, 6),
            "end_s": round(cursor / loaded[0].sample_rate, 6),
        })
        if position < len(order) - 1:
            silence = cycle_gap if position == 2 else gap
            pieces.append(silence)
            cursor += len(silence)

    montage = np.concatenate(pieces, axis=0)
    entries = []
    for role, path, original, audio, start, before, gain, after, peak in zip(
            ("reference", "first", "second"), paths, originals, loaded, starts,
            before_lufs, gains, measured_after, measured_peaks):
        entries.append({
            "role": role,
            "path": str(path),
            "sha256": _sha256(path),
            "source_duration_s": round(audio.duration_s, 6),
            "source_channels": original.channels,
            "audition_channels": audio.channels,
            "used_start_s": round(start, 6),
            "used_end_s": round(start + used_duration, 6),
            "lufs_before": round(before, 4),
            "static_gain_db": round(gain, 4),
            "lufs_after": round(after, 4),
            "true_peak_after_dbtp": None if peak is None else round(peak, 4),
        })

    metadata = {
        "schema": "rab-audition-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "sample_rate": loaded[0].sample_rate,
        "channels": output_channels,
        "segment_duration_s": round(used_duration, 6),
        "sequence": "Reference-A-B-Reference-A-B",
        "blind_key": {
            "A": ("second" if swap else "first"),
            "B": ("first" if swap else "second"),
        },
        "level_matching": {
            "method": "one static gain per source; no EQ, compression, or limiting",
            "requested_target_lufs": target_lufs,
            "effective_target_lufs": round(effective_target, 4),
            "peak_ceiling_dbtp": peak_ceiling_dbtp,
            "shared_target_reduction_db": round(reduction, 4),
        },
        "channel_handling": (
            "explicit channel-averaged mono fold-down" if force_mono
            else "stereo preserved; mono promoted to dual-mono when another input is stereo"
        ),
        "sources": entries,
        "timeline": timeline,
    }
    return montage, metadata


def _write_audio(path: pathlib.Path, samples, sample_rate: int) -> None:
    import soundfile as sf

    suffix = path.suffix.lower()
    if suffix not in (".wav", ".flac"):
        raise ValueError("--out must end in .wav or .flac")
    subtype = "FLOAT" if suffix == ".wav" else "PCM_24"
    temporary = tempfile.NamedTemporaryFile(
        prefix=f".{path.stem}-", suffix=suffix, dir=path.parent, delete=False
    )
    temporary.close()
    temp_path = pathlib.Path(temporary.name)
    try:
        sf.write(str(temp_path), samples, sample_rate, subtype=subtype)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _write_text(path: pathlib.Path, contents: str) -> None:
    """Write the key atomically so an interruption cannot leave partial JSON."""
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}-", suffix=".tmp", dir=path.parent
    )
    temp_path = pathlib.Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build a blind, static-gain-matched R-A-B-R-A-B audition file.",
        epilog="Judge closer and prefer separately. Use raw renders for output level.",
    )
    ap.add_argument("--reference", required=True, type=pathlib.Path)
    ap.add_argument("--a", required=True, type=pathlib.Path,
                    help="first option; its blind label is assigned randomly")
    ap.add_argument("--b", required=True, type=pathlib.Path,
                    help="second option; its blind label is assigned randomly")
    ap.add_argument("--out", required=True, type=pathlib.Path,
                    help="output .wav or .flac montage")
    ap.add_argument("--key", type=pathlib.Path,
                    help="separate JSON key (default: OUT.key.json)")
    ap.add_argument("--reference-start", type=_nonnegative_float, default=0.0)
    ap.add_argument("--a-start", type=_nonnegative_float, default=0.0)
    ap.add_argument("--b-start", type=_nonnegative_float, default=0.0)
    ap.add_argument("--duration", type=positive_float,
                    help="seconds from each file (default: shortest remainder)")
    ap.add_argument("--target-lufs", type=_finite_float, default=-20.0)
    ap.add_argument("--peak-ceiling-dbtp", type=_nonpositive_float, default=-1.0)
    ap.add_argument("--gap", type=_nonnegative_float, default=0.5,
                    help="silence between R, A and B (default: 0.5 s)")
    ap.add_argument("--cycle-gap", type=_nonnegative_float, default=1.0,
                    help="silence between the two R-A-B cycles (default: 1 s)")
    ap.add_argument("--mono", action="store_true",
                    help="explicitly fold every input to channel-averaged mono")
    ap.add_argument("--seed", type=int,
                    help="blind assignment seed (default: generate and record one)")
    ap.add_argument("--force", action="store_true",
                    help="replace existing output and key")
    args = ap.parse_args()

    args.reference = args.reference.expanduser()
    args.a = args.a.expanduser()
    args.b = args.b.expanduser()
    paths = (args.reference, args.a, args.b)
    for path in paths:
        if not path.exists():
            die(f"{path} does not exist")
        if path.is_dir():
            die(f"{path} is a directory; pass an audio file")
    args.out = args.out.expanduser()
    key_path = args.key.expanduser() if args.key else args.out.with_suffix(
        args.out.suffix + ".key.json"
    )
    if args.out.resolve() == key_path.resolve():
        die("--out and --key must be different files")
    if args.out.suffix.lower() not in (".wav", ".flac"):
        die("--out must end in .wav or .flac")
    protected = {path.resolve() for path in paths}
    for label, path in (("--out", args.out), ("--key", key_path)):
        if path.resolve() in protected:
            die(f"{label} must not replace an input file, even with --force")
    for path in (args.out, key_path):
        if path.is_dir():
            die(f"{path} is a directory, not an output file")
        if path.exists() and not args.force:
            die(f"{path} already exists; choose another path or pass --force")
        path.parent.mkdir(parents=True, exist_ok=True)

    seed = args.seed if args.seed is not None else secrets.randbits(64)
    montage, metadata = build(
        reference=args.reference,
        first=args.a,
        second=args.b,
        starts=(args.reference_start, args.a_start, args.b_start),
        duration_s=args.duration,
        target_lufs=args.target_lufs,
        peak_ceiling_dbtp=args.peak_ceiling_dbtp,
        gap_s=args.gap,
        cycle_gap_s=args.cycle_gap,
        seed=seed,
        force_mono=args.mono,
    )
    metadata["invocation"] = [sys.executable, str(pathlib.Path(__file__)), *sys.argv[1:]]
    if args.seed is None:
        metadata["invocation"].extend(["--seed", str(seed)])

    _write_audio(args.out, montage, metadata["sample_rate"])
    metadata["output"] = {
        "path": str(args.out),
        "sha256": _sha256(args.out),
        "format": args.out.suffix.lower().lstrip("."),
    }
    _write_text(key_path, json.dumps(metadata, indent=2) + "\n")

    print(f"wrote {args.out}")
    print(f"blind key: {key_path}")
    print(f"level matched to {metadata['level_matching']['effective_target_lufs']:.2f} "
          "LUFS with static gain only")
    print(f"channels: {metadata['channel_handling']}")
    print("listen without opening the key: Reference -> A -> B, repeated once")
    print("answer separately: which is closer to the reference, and which do you prefer?")
    print("use the untouched raw renders if you are judging output level itself")
    print(f"reproducible blind assignment seed: {seed}")
    print(f"invocation: {shlex.join(metadata['invocation'])}")


if __name__ == "__main__":
    guarded(main)
