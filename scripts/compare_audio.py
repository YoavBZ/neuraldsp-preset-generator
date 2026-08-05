"""Compare two recordings, or two fingerprints, and say how they differ.

    python scripts/compare_audio.py reference.wav render.wav
    python scripts/compare_audio.py target.json candidate.json --profile paired-v1
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
    from analysis.fingerprint import Fingerprint, fingerprint_file

    if path.suffix.lower() == ".json":
        return Fingerprint.from_json(path.read_text())
    if path.suffix.lower() not in AUDIO_SUFFIXES:
        die(f"{path} is neither a .json fingerprint nor an audio file this reads")
    return fingerprint_file(path, regime=regime, excerpt_s=excerpt)


def print_report(target, candidate, objectives, deltas, scalar_value) -> None:
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
    from analysis.compare import ProfileError, band_delta, compare, list_profiles, scalar
    from analysis.fingerprint import DEFAULT_EXCERPT_S, FingerprintError

    excerpt = DEFAULT_EXCERPT_S if args.excerpt is None else (args.excerpt or None)
    try:
        target = _load_side(args.target, args.target_regime, excerpt)
        candidate = _load_side(args.candidate, args.candidate_regime, excerpt)
        objectives = compare(target, candidate, profile=args.profile)
        value = scalar(objectives)
    except ProfileError as e:
        die(f"{e}\n  Available profiles: {', '.join(list_profiles())}")
    except (AnalysisUnavailable, FingerprintError) as e:
        die(str(e))

    deltas = band_delta(target, candidate)
    if args.json:
        print(json.dumps({"objectives": objectives.to_dict(), "combined": value,
                          "band_delta": deltas}, indent=2))
    else:
        print_report(target, candidate, objectives, deltas, value)


if __name__ == "__main__":
    guarded(main)
