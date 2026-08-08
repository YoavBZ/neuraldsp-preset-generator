"""Compare two recordings, or two fingerprints, and say how they differ.

    python scripts/compare_audio.py reference.wav render.wav
    python scripts/compare_audio.py reamp.wav candidate.wav --profile paired-v1
    python scripts/compare_audio.py a.wav b.wav --json

The first argument is the target and the second is the candidate, and the band
table reads as what the candidate would need to do to become the target: a
positive number means the candidate is that many dB short in that band.

Either argument may be an audio file or a fingerprint written by
scripts/fingerprint.py. Comparing two fingerprints costs nothing and needs no
audio, which is the point of storing them.

Needs the analysis extra:  pip install -e '.[analysis]'
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

AUDIO_SUFFIXES = {".wav", ".aiff", ".aif", ".flac", ".ogg", ".caf", ".w64"}


def _load_side(path: pathlib.Path, regime: str, excerpt):
    """Accept a fingerprint document or an audio file, and say which it was."""
    from analysis import io
    from analysis.fingerprint import Fingerprint, fingerprint

    if path.suffix.lower() == ".json":
        return Fingerprint.from_json(path.read_text()), None
    if path.suffix.lower() not in AUDIO_SUFFIXES:
        die(f"{path} is neither a .json fingerprint nor an audio file this reads")
    audio = io.load(path)
    return fingerprint(audio, regime=regime, excerpt_s=excerpt), audio


def print_report(target, candidate, objectives, deltas, scalar_value,
                 alignment=None, residual_value=None) -> None:
    print(f"profile     {objectives.profile}")
    print(f"target      {target.source.get('regime')} "
          f"({target.regime_confidence:.2f} confidence), "
          f"{target.source.get('duration_s')} s")
    print(f"candidate   {candidate.source.get('regime')}, "
          f"{candidate.source.get('duration_s')} s")

    print("\nobjectives  (0 is identical, 1 is one unit of wrong)")
    for name, value in objectives.values.items():
        if value is None:
            print(f"  {name:16} —        not measurable from this material")
        else:
            bar = "#" * min(int(value * 20), 40)
            print(f"  {name:16} {value:7.3f}  {bar}")
    print(f"  {'combined':16} {scalar_value:7.3f}" if scalar_value is not None
          else "  combined         —")

    if alignment is not None:
        trust = "trusted" if alignment.trustworthy else "not trusted; left unshifted"
        print(f"\npaired waveform residual  {residual_value:.2f} dB")
        print(f"  alignment {alignment.offset_ms:+.3f} ms, "
              f"correlation {alignment.correlation:+.3f} ({trust})")

    if deltas:
        print("\nband difference, target minus candidate, level offset removed")
        print("  (positive: the candidate is short in that band)")
        for row in deltas:
            centre = row["centre_hz"]
            if centre < 50 or centre > 16000:
                continue
            delta = row["delta_db"]
            scale = int(abs(delta) * 2)
            bar = ("+" if delta > 0 else "-") * min(scale, 30)
            label = f"{centre / 1000:g}k" if centre >= 1000 else f"{centre:g}"
            print(f"  {label:>6} Hz  {delta:+6.1f}  {bar}")

    caveats = list(dict.fromkeys(target.caveats() + candidate.caveats()))
    if caveats:
        print("\ncaveats")
        for note in caveats:
            print(f"  - {note}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compare two recordings or fingerprints.",
        epilog="Needs the analysis extra: pip install -e '.[analysis]'",
    )
    ap.add_argument("target", type=pathlib.Path, help="what you want it to sound like")
    ap.add_argument("candidate", type=pathlib.Path, help="what it sounds like now")
    ap.add_argument("--profile", default="unpaired-v1")
    ap.add_argument("--target-regime", default="mix")
    ap.add_argument("--candidate-regime", default="probe")
    ap.add_argument("--excerpt", type=float, default=None, metavar="SECONDS")
    ap.add_argument("--json", action="store_true", help="emit the objectives as JSON")
    args = ap.parse_args()

    for path in (args.target, args.candidate):
        if not path.exists():
            die(f"{path} does not exist")

    from analysis import AnalysisUnavailable
    from analysis.compare import (ProfileError, band_delta, compare, load_profile,
                                  scalar)
    from analysis.fingerprint import DEFAULT_EXCERPT_S, FingerprintError

    excerpt = DEFAULT_EXCERPT_S if args.excerpt is None else (args.excerpt or None)
    try:
        profile = load_profile(args.profile)
        target, target_audio = _load_side(args.target, args.target_regime, excerpt)
        candidate, candidate_audio = _load_side(
            args.candidate, args.candidate_regime, excerpt)
        residual_value = None
        alignment = None
        residual_weighted = float(
            profile.get("weights", {}).get("residual", 0.0) or 0.0
        ) > 0.0
        if residual_weighted:
            if target_audio is None or candidate_audio is None:
                die(f"loss profile {args.profile!r} weights waveform residual, "
                    "which requires both arguments to be audio files. A stored "
                    "fingerprint contains no samples; use --profile unpaired-v1 "
                    "to compare fingerprints.")
            from analysis.align import align, residual_db

            aligned_target, aligned_candidate, alignment = align(
                target_audio.samples, candidate_audio.samples,
                target_audio.sample_rate)
            residual_value = residual_db(aligned_target, aligned_candidate)
            if residual_value is None:
                die("paired waveform residual is not measurable: the aligned target "
                    "has no usable mono energy")
        objectives = compare(target, candidate, profile=args.profile,
                             residual_db=residual_value)
        value = scalar(objectives)
    except ProfileError as e:
        # ProfileError already lists the available profiles; appending them again
        # printed the same list twice.
        die(str(e))
    except (AnalysisUnavailable, FingerprintError) as e:
        die(str(e))

    deltas = band_delta(target, candidate)
    if args.json:
        alignment_json = None if alignment is None else {
            "offset_samples": alignment.offset_samples,
            "fractional_offset": alignment.fractional_offset,
            "offset_ms": alignment.offset_ms,
            "correlation": alignment.correlation,
            "polarity": alignment.polarity,
            "trustworthy": alignment.trustworthy,
        }
        print(json.dumps({"objectives": objectives.to_dict(), "combined": value,
                          "band_delta": deltas, "residual_db": residual_value,
                          "alignment": alignment_json}, indent=2))
    else:
        print_report(target, candidate, objectives, deltas, value,
                     alignment=alignment, residual_value=residual_value)


if __name__ == "__main__":
    guarded(main)
