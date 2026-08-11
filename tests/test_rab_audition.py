"""A listening comparison must remove level bias without changing tone."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

np = pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("soundfile", reason="needs the analysis extra")

from analysis import io
from tests import fixtures_audio as fx

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_rab_audition.py"


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          cwd=ROOT, capture_output=True, text=True)


def _inputs(tmp_path):
    base = fx.band_limited(seconds=1.0, seed=23)
    paths = []
    for name, gain in (("reference", 0.05), ("first", 0.2), ("second", 0.01)):
        path = tmp_path / f"{name}.wav"
        fx.write_wav(path, base * gain)
        paths.append(path)
    return paths


def test_builds_one_level_matched_blind_file_and_key(tmp_path):
    reference, first, second = _inputs(tmp_path)
    out = tmp_path / "listen.flac"
    key = tmp_path / "private-key.json"
    done = _run("--reference", reference, "--a", first, "--b", second,
                "--out", out, "--key", key, "--seed", 17,
                "--target-lufs", -20)
    assert done.returncode == 0, done.stdout + done.stderr

    record = json.loads(key.read_text())
    assert record["schema"] == "rab-audition-v1"
    assert record["sequence"] == "Reference-A-B-Reference-A-B"
    assert set(record["blind_key"]) == {"A", "B"}
    assert set(record["blind_key"].values()) == {"first", "second"}
    assert record["seed"] == 17
    assert all(source["lufs_after"] == pytest.approx(
        record["level_matching"]["effective_target_lufs"], abs=0.05
    ) for source in record["sources"])
    assert all(source["true_peak_after_dbtp"] <= -1.0 + 0.02
               for source in record["sources"])

    rendered = io.load(out)
    assert rendered.channels == 1
    expected = 6 * 1.0 + 4 * 0.5 + 1.0
    assert rendered.duration_s == pytest.approx(expected, abs=1 / 48000)
    assert record["output"]["sha256"]
    original = io.load(reference).mono()
    gain = 10 ** (record["sources"][0]["static_gain_db"] / 20.0)
    assert rendered.mono()[:len(original)] == pytest.approx(
        original * gain, abs=2e-6
    ), "the reference segment received static gain and no other processing"
    assert "closer" in done.stdout and "prefer" in done.stdout
    assert "raw renders" in done.stdout


def test_peak_headroom_lowers_one_shared_target_instead_of_limiting(tmp_path):
    reference, first, second = _inputs(tmp_path)
    key = tmp_path / "listen.wav.key.json"
    done = _run("--reference", reference, "--a", first, "--b", second,
                "--out", tmp_path / "listen.wav", "--seed", 1,
                "--target-lufs", -3)
    assert done.returncode == 0, done.stderr
    record = json.loads(key.read_text())
    levels = record["level_matching"]
    assert levels["effective_target_lufs"] < levels["requested_target_lufs"]
    assert levels["shared_target_reduction_db"] > 0
    assert all(source["true_peak_after_dbtp"] <= -1.0 + 0.02
               for source in record["sources"])


def test_loudness_converges_when_the_absolute_gate_changes(tmp_path):
    """One-pass gain is wrong when amplification admits formerly gated blocks."""
    import soundfile as sf

    rng = np.random.default_rng(2)
    loud = rng.standard_normal(fx.SAMPLE_RATE) * 0.0007
    quiet = rng.standard_normal(fx.SAMPLE_RATE * 3) * 0.00021
    signal = np.concatenate([loud, quiet])
    paths = []
    for name in ("reference", "first", "second"):
        path = tmp_path / f"{name}.wav"
        sf.write(path, signal, fx.SAMPLE_RATE, subtype="FLOAT")
        paths.append(path)

    source = io.load(paths[0])
    before = io.loudness_lufs(source)
    one_pass = source.replace(source.samples * (10 ** ((-20.0 - before) / 20.0)))
    assert abs(io.loudness_lufs(one_pass) - (-20.0)) > 1.0, (
        "the fixture must exercise the gate transition, not ordinary gain"
    )

    done = _run("--reference", paths[0], "--a", paths[1], "--b", paths[2],
                "--out", tmp_path / "listen.wav", "--target-lufs", -20,
                "--seed", 8)
    assert done.returncode == 0, done.stderr
    record = json.loads((tmp_path / "listen.wav.key.json").read_text())
    assert all(source["lufs_after"] == pytest.approx(-20.0, abs=0.05)
               for source in record["sources"])


def test_stereo_is_preserved_and_mono_is_promoted(tmp_path):
    mono = fx.band_limited(seconds=1.0, seed=9) * 0.05
    reference = fx.write_wav(tmp_path / "reference.wav", fx.stereo(mono, width=0.5))
    first = fx.write_wav(tmp_path / "first.wav", mono)
    second = fx.write_wav(tmp_path / "second.wav", fx.stereo(mono, width=0.2))
    out = tmp_path / "listen.wav"
    done = _run("--reference", reference, "--a", first, "--b", second,
                "--out", out, "--seed", 4)
    assert done.returncode == 0, done.stderr

    record = json.loads((tmp_path / "listen.wav.key.json").read_text())
    assert io.load(out).channels == 2
    assert record["channels"] == 2
    assert [item["source_channels"] for item in record["sources"]] == [2, 1, 2]
    assert [item["audition_channels"] for item in record["sources"]] == [2, 2, 2]
    assert "stereo preserved" in record["channel_handling"]


def test_refuses_to_overwrite_either_artifact(tmp_path):
    reference, first, second = _inputs(tmp_path)
    out = tmp_path / "listen.wav"
    out.write_bytes(b"keep me")
    done = _run("--reference", reference, "--a", first, "--b", second,
                "--out", out)
    assert done.returncode != 0
    assert "already exists" in done.stderr
    assert out.read_bytes() == b"keep me"


def test_refuses_a_peak_ceiling_that_can_clip(tmp_path):
    reference, first, second = _inputs(tmp_path)
    done = _run("--reference", reference, "--a", first, "--b", second,
                "--out", tmp_path / "listen.wav", "--peak-ceiling-dbtp", 1)
    assert done.returncode != 0
    assert "zero or lower" in done.stderr


def test_force_still_cannot_replace_a_source(tmp_path):
    reference, first, second = _inputs(tmp_path)
    original = reference.read_bytes()
    done = _run("--reference", reference, "--a", first, "--b", second,
                "--out", reference, "--force")
    assert done.returncode != 0
    assert "must not replace an input" in done.stderr
    assert reference.read_bytes() == original


def test_rejects_an_output_format_before_building(tmp_path):
    reference, first, second = _inputs(tmp_path)
    done = _run("--reference", reference, "--a", first, "--b", second,
                "--out", tmp_path / "listen.mp3")
    assert done.returncode != 0
    assert "must end in .wav or .flac" in done.stderr
