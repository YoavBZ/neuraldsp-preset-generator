"""The two analysis entry points, run as a person would run them."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("soundfile", reason="needs the analysis extra")

from tests import fixtures_audio as fx

ROOT = pathlib.Path(__file__).resolve().parents[1]
FINGERPRINT = ROOT / "scripts" / "fingerprint.py"
COMPARE = ROOT / "scripts" / "compare_audio.py"


def run(*args, expect: int = 0):
    result = subprocess.run(
        [sys.executable, *[str(a) for a in args]],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == expect, f"exit {result.returncode}\n{result.stderr}"
    return result


@pytest.fixture(scope="module")
def dark(tmp_path_factory):
    path = tmp_path_factory.mktemp("audio") / "dark.wav"
    return fx.write_wav(path, fx.stereo(fx.band_limited(seconds=4.0, high=2200, seed=3)))


@pytest.fixture(scope="module")
def bright(tmp_path_factory):
    path = tmp_path_factory.mktemp("audio") / "bright.wav"
    return fx.write_wav(path, fx.stereo(fx.band_limited(seconds=4.0, high=8000, seed=3)))


def test_fingerprint_prints_valid_json(dark):
    """The exit criterion: a valid Fingerprint v1 for any input."""
    document = json.loads(run(FINGERPRINT, dark).stdout)
    assert document["fingerprint_version"] == 1
    assert document["source"]["channels"] == 2
    assert document["spectrum"]["band_db"]


def test_fingerprint_text_mode_is_readable(dark):
    out = run(FINGERPRINT, dark, "--text").stdout
    for heading in ("regime", "excerpt", "spectrum", "dynamics", "harmonic", "stereo"):
        assert heading in out
    assert "0.000000–4.000000 s of 4.000000 s" in out


def test_fingerprint_text_does_not_call_dry_note_decay_reverb(tmp_path):
    dry = fx.write_wav(
        tmp_path / "dry-plucks.wav",
        fx.plucks(seconds=10.0, gap=1.0, decay=5.0, length=0.8),
    )
    out = run(FINGERPRINT, dry, "--text").stdout
    assert "slope agreement" in out
    assert "agreeing dry notes" in out
    assert "not proof of reverb" in out


def test_fingerprint_text_distinguishes_weak_and_missing_rt60(capsys):
    from analysis import io
    from analysis.fingerprint import fingerprint
    from scripts.fingerprint import print_text

    fp = fingerprint(io.from_samples(fx.plucks(seconds=10.0), fx.SAMPLE_RATE))
    fp.time_fx.update(rt60_s=1.2, rt60_confidence=0.2)
    print_text(fp)
    out = capsys.readouterr().out
    assert "weak release-fit evidence (score 0.20)" in out
    assert "slope agreement 0.20" not in out

    fp.time_fx.update(rt60_s=None, rt60_confidence=0.0)
    print_text(fp)
    out = capsys.readouterr().out
    assert "rt60        — s  not measured" in out


def test_fingerprint_writes_a_file(dark, tmp_path):
    out = tmp_path / "fp.json"
    run(FINGERPRINT, dark, "--out", out)
    from analysis.fingerprint import Fingerprint

    assert Fingerprint.from_json(out.read_text()).source["channels"] == 2


def test_fingerprint_rejects_a_missing_file(tmp_path):
    result = run(FINGERPRINT, tmp_path / "nope.wav", expect=2)
    assert "does not exist" in result.stderr


def test_fingerprint_rejects_an_unknown_regime(dark):
    result = run(FINGERPRINT, dark, "--regime", "vibes", expect=2)
    assert "regime" in result.stderr


def test_fingerprint_rejects_a_negative_excerpt(dark):
    result = run(FINGERPRINT, dark, "--excerpt", "-1", expect=2)
    assert "zero or greater" in result.stderr


def test_fingerprint_rejects_an_infinite_excerpt(dark):
    result = run(FINGERPRINT, dark, "--excerpt", "inf", expect=2)
    assert "finite" in result.stderr


def test_compare_two_audio_files(dark, bright):
    out = run(COMPARE, dark, bright).stdout
    assert "objectives" in out
    assert "timbre" in out
    assert "band difference" in out


def test_compare_two_fingerprints(dark, bright, tmp_path):
    """Comparing stored fingerprints needs no audio, which is the point."""
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    run(FINGERPRINT, dark, "--out", a)
    run(FINGERPRINT, bright, "--out", b)
    document = json.loads(run(COMPARE, a, b, "--json").stdout)
    assert document["objectives"]["values"]["timbre"] > 0.0
    assert document["combined"] > 0.0
    assert document["band_delta"]


def test_paired_compare_uses_aligned_waveforms(dark):
    document = json.loads(run(
        COMPARE, dark, dark, "--profile", "paired-v1", "--json").stdout)
    assert document["objectives"]["values"]["residual"] == pytest.approx(0.0)
    assert document["residual_db"] < -100.0
    assert document["alignment"]["trustworthy"] is True


def test_paired_compare_refuses_fingerprints_without_samples(dark, tmp_path):
    stored = tmp_path / "dark.json"
    run(FINGERPRINT, dark, "--out", stored)
    result = run(COMPARE, stored, stored, "--profile", "paired-v1", expect=2)
    assert "requires both arguments to be audio files" in result.stderr


def test_paired_compare_refuses_an_excerpt_that_would_not_reach_the_residual(dark):
    result = run(COMPARE, dark, dark, "--profile", "paired-v1",
                 "--excerpt", "1", expect=2)
    assert "complete files" in result.stderr


def test_compare_rejects_an_unknown_profile(dark, bright):
    result = run(COMPARE, dark, bright, "--profile", "vibes-v3", expect=2)
    assert "unknown loss profile" in result.stderr
    assert "unpaired-v1" in result.stderr


def test_compare_of_a_file_with_itself_is_zero(dark):
    document = json.loads(run(COMPARE, dark, dark, "--json").stdout)
    assert document["combined"] == pytest.approx(0.0, abs=1e-9)


@pytest.fixture(scope="module")
def long_and_busy(tmp_path_factory):
    """Ten seconds that never stop, so the automatic choice has nothing to rank."""
    path = tmp_path_factory.mktemp("audio") / "busy.wav"
    return fx.write_wav(path, fx.stereo(fx.band_limited(seconds=10.0, seed=11)))


def test_excerpt_start_measures_the_window_you_name(long_and_busy):
    document = json.loads(
        run(FINGERPRINT, long_and_busy, "--excerpt", "2", "--excerpt-start", "6").stdout
    )
    assert document["source"]["excerpt_policy"] == "explicit_window"
    assert document["source"]["excerpt_start_s"] == pytest.approx(6.0)
    assert document["source"]["excerpt_end_s"] == pytest.approx(8.0)


def test_without_it_the_same_file_reports_an_unranked_choice(long_and_busy):
    """The contrast is the point: same file, same length, and the automatic
    window is the start of the file with a caveat rather than a selection."""
    out = run(FINGERPRINT, long_and_busy, "--excerpt", "2", "--text").stdout
    assert "activity tie" in out
    assert "--excerpt-start" in out, "the text summary has to carry the remedy"


def test_excerpt_start_without_a_window_is_refused(long_and_busy):
    """`--excerpt 0` means the whole source, so there is nothing to start."""
    result = run(FINGERPRINT, long_and_busy,
                 "--excerpt", "0", "--excerpt-start", "3", expect=2)
    assert "--excerpt-start needs a window" in result.stderr
    assert "Traceback" not in result.stderr


def test_a_negative_excerpt_start_is_refused(long_and_busy):
    result = run(FINGERPRINT, long_and_busy, "--excerpt-start", "-4", expect=2)
    assert "zero or greater" in result.stderr


def test_a_short_source_says_the_window_could_not_be_honoured(tmp_path):
    """Silently measuring the whole file would report `full source` for a run
    the user asked to window — the failure this flag was added to remove."""
    short = fx.write_wav(tmp_path / "short.wav",
                         fx.stereo(fx.band_limited(seconds=3.0)))
    out = run(FINGERPRINT, short, "--regime", "mix",
              "--excerpt", "20", "--excerpt-start", "1", "--text").stdout
    assert "--excerpt-start was ignored" in out


def test_the_no_window_error_does_not_blame_a_flag_you_did_not_pass(long_and_busy):
    """paired_di defaults to the complete performance, so this path is reachable
    without --excerpt ever appearing on the command line."""
    result = run(FINGERPRINT, long_and_busy, "--regime", "paired_di",
                 "--excerpt-start", "3", expect=2)
    assert "--excerpt-start needs a window" in result.stderr
    assert "defaults to the complete performance" in result.stderr
    assert "Traceback" not in result.stderr
