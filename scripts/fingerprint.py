"""Measure an audio file into a Fingerprint v1 document.

    python scripts/fingerprint.py reference.wav
    python scripts/fingerprint.py render.wav --regime probe --out fp.json
    python scripts/fingerprint.py song.wav --regime mix --text

The regime is how the guitar reaches the file, and it decides how much the
result is worth: `paired_di` is the same performance through the same notes,
`mix` is a guitar buried under a band and a master chain. It is recorded in the
fingerprint and reported with every number derived from it.

Needs the analysis extra:  pip install -e '.[analysis]'

No audio is copied, moved or written. The fingerprint stores the file's hash,
never its path or its contents.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded


def _format(value, digits: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def print_text(fp) -> None:
    """A summary a person reads, rather than the document a program reads."""
    source = fp.source
    print(f"regime      {source.get('regime')}  (confidence {fp.regime_confidence:.2f})")
    print(f"source      {_format(source.get('duration_s'))} s, "
          f"{source.get('channels')} ch, {source.get('sample_rate')} Hz"
          + (f" (from {source.get('source_sample_rate')} Hz)"
             if source.get("source_sample_rate") != source.get("sample_rate") else ""))
    print(f"level       {_format(source.get('lufs_i'), 1)} LUFS, "
          f"true peak {_format(source.get('true_peak_dbtp'), 1)} dBTP")
    print(f"sha256      {source.get('sha256', '')[:16]}…")

    print("\nspectrum")
    print(f"  tilt        {_format(fp.spectrum.get('tilt_db_per_decade'))} dB/decade")
    print(f"  extent      {_format(fp.spectrum.get('lf_corner_hz'), 0)} Hz "
          f"to {_format(fp.spectrum.get('hf_corner_hz'), 0)} Hz (-6 dB)")
    centroid = fp.spectrum.get("centroid_hz") or {}
    print(f"  centroid    {_format(centroid.get('p50'), 0)} Hz "
          f"(p10 {_format(centroid.get('p10'), 0)}, p90 {_format(centroid.get('p90'), 0)})")
    centres = fp.spectrum.get("band_centres_hz") or []
    levels = fp.spectrum.get("band_db") or []
    interesting = [(c, v) for c, v in zip(centres, levels) if 60 <= c <= 16000]
    if interesting:
        peak = max(v for _, v in interesting)
        print("  bands       " + " ".join(
            f"{int(c) if c >= 1000 else c:g}:{v - peak:+.0f}" for c, v in interesting[::2]))

    print("\ndynamics")
    print(f"  crest       {_format(fp.dynamics.get('crest_db'))} dB")
    print(f"  attack      {_format(fp.dynamics.get('attack_ms'), 1)} ms, "
          f"decay {_format(fp.dynamics.get('decay_db_per_s'), 1)} dB/s")
    print(f"  range       {_format(fp.dynamics.get('lra_lu'), 1)} LU")

    print("\ntime and modulation")
    time_fx = fp.time_fx
    delay = _format(time_fx.get("delay_ms"), 1)
    division = time_fx.get("delay_note_division")
    print(f"  delay       {delay} ms"
          + (f" ({division} at {_format(time_fx.get('bpm_est'), 0)} BPM)" if division else "")
          + f"  confidence {_format(time_fx.get('delay_confidence'))}")
    print(f"  feedback    {_format(time_fx.get('delay_feedback_est'))}")
    print(f"  rt60        {_format(time_fx.get('rt60_s'))} s  "
          f"confidence {_format(time_fx.get('rt60_confidence'))}")
    print(f"  tremolo     {_format(fp.modulation.get('am_rate_hz'), 1)} Hz, "
          f"depth {_format(fp.modulation.get('am_depth'))}")

    print("\nharmonic")
    print(f"  hnr         {_format(fp.harmonic.get('hnr_db'), 1)} dB")
    print(f"  odd/even    {_format(fp.harmonic.get('odd_even_ratio'))}, "
          f"fizz {_format(fp.harmonic.get('hf_residual_index'), 3)}")
    print(f"  confidence  {_format(fp.harmonic.get('confidence'))}")

    print("\nstereo")
    print(f"  width       {_format(fp.spatial.get('width'))}, "
          f"correlation {_format(fp.spatial.get('correlation'))}")

    caveats = fp.caveats()
    if caveats:
        print("\ncaveats")
        for note in caveats:
            print(f"  - {note}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Measure audio into a Fingerprint v1 document.",
        epilog="Needs the analysis extra: pip install -e '.[analysis]'",
    )
    ap.add_argument("audio", type=pathlib.Path)
    ap.add_argument("--regime", default="probe",
                    help="paired_di | isolated_stem | separated_stem | mix | probe")
    ap.add_argument("--excerpt", type=float, default=None, metavar="SECONDS",
                    help="measure the most active excerpt of this length (default 20; 0 for all)")
    ap.add_argument("--out", type=pathlib.Path, help="write the JSON here instead of stdout")
    ap.add_argument("--text", action="store_true", help="print a summary instead of JSON")
    args = ap.parse_args()

    if not args.audio.exists():
        die(f"{args.audio} does not exist")
    if args.audio.is_dir():
        # `.exists()` is true for a directory, which then reached soundfile and
        # came back as an IsADirectoryError traceback.
        die(f"{args.audio} is a directory; pass an audio file")

    from analysis import AnalysisUnavailable
    from analysis.fingerprint import DEFAULT_EXCERPT_S, FingerprintError, fingerprint_file

    excerpt = DEFAULT_EXCERPT_S if args.excerpt is None else (args.excerpt or None)
    try:
        fp = fingerprint_file(args.audio, regime=args.regime, excerpt_s=excerpt)
    except (AnalysisUnavailable, FingerprintError) as e:
        die(str(e))

    if args.out:
        args.out.write_text(fp.to_json() + "\n")
        print(f"wrote {args.out}", file=sys.stderr)
    elif args.text:
        print_text(fp)
    else:
        print(fp.to_json())


if __name__ == "__main__":
    guarded(main)
