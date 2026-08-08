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
    for heading in ("regime", "spectrum", "dynamics", "harmonic", "stereo"):
        assert heading in out


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


def test_compare_rejects_an_unknown_profile(dark, bright):
    result = run(COMPARE, dark, bright, "--profile", "vibes-v3", expect=2)
    assert "unknown loss profile" in result.stderr
    assert "unpaired-v1" in result.stderr


def test_compare_of_a_file_with_itself_is_zero(dark):
    document = json.loads(run(COMPARE, dark, dark, "--json").stdout)
    assert document["combined"] == pytest.approx(0.0, abs=1e-9)
