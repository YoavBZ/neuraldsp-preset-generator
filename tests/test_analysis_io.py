"""Loading, level measurement and excerpt selection."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("soundfile", reason="needs the analysis extra")

import numpy as np

from analysis import SAMPLE_RATE, io
from tests import fixtures_audio as fx


def test_load_resamples_to_the_canonical_rate(tmp_path):
    """A 44.1 kHz file arrives at 48 kHz, and says where it came from."""
    one_second_at_44k = fx.noise(seconds=1.0, sample_rate=44100)
    path = fx.write_wav(tmp_path / "a.wav", one_second_at_44k, sample_rate=44100)
    audio = io.load(path)
    assert audio.sample_rate == SAMPLE_RATE
    assert audio.source_rate == 44100
    assert audio.duration_s == pytest.approx(1.0, abs=0.01)


def test_load_preserves_channels(tmp_path):
    path = fx.write_wav(tmp_path / "s.wav", fx.stereo(fx.noise(seconds=1.0), width=0.5))
    assert io.load(path).channels == 2


def test_sha256_is_of_the_bytes_not_the_samples(tmp_path):
    """The hash identifies a reference the project must never keep a copy of."""
    import hashlib

    path = fx.write_wav(tmp_path / "a.wav", fx.noise(seconds=0.5))
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert io.load(path).sha256 == expected


def test_normalise_hits_the_target_loudness():
    audio = io.from_samples(fx.stereo(fx.noise(seconds=3.0)) * 0.01, SAMPLE_RATE)
    assert io.loudness_lufs(io.normalise(audio, -23.0)) == pytest.approx(-23.0, abs=0.1)


def test_normalise_leaves_silence_alone():
    """There is no gain that makes silence -23 LUFS, so nothing is invented."""
    silent = io.from_samples(np.zeros((SAMPLE_RATE, 2), dtype=np.float32), SAMPLE_RATE)
    assert io.loudness_lufs(silent) is None
    assert float(np.abs(io.normalise(silent).samples).max()) == 0.0


def test_true_peak_sees_between_the_samples():
    """An inter-sample peak is above the sample peak, which is the point."""
    t = np.arange(SAMPLE_RATE) / SAMPLE_RATE
    tone = np.sin(2 * np.pi * 11000 * t + 0.4) * 0.99
    audio = io.from_samples(tone, SAMPLE_RATE)
    sample_peak = 20 * np.log10(float(np.abs(tone).max()))
    assert io.true_peak_dbtp(audio) > sample_peak


def test_active_frames_exclude_the_silence():
    """Gating keeps the sound and drops the gaps, and a long gap moves the mean."""
    loud = fx.noise(seconds=1.0)
    padded = np.concatenate([loud, np.zeros(SAMPLE_RATE * 3)])
    mask = io.active_frames(padded)
    assert 0.15 < mask.mean() < 0.40
    assert mask[: len(mask) // 5].all()


def test_excerpt_picks_the_busy_part():
    """Two seconds of noise buried in nine seconds of silence is what comes back."""
    quiet = np.zeros(SAMPLE_RATE * 4)
    audio = io.from_samples(
        np.concatenate([quiet, fx.noise(seconds=2.0), quiet]), SAMPLE_RATE
    )
    chosen = io.excerpt(audio, 2.0)
    assert chosen.frames == SAMPLE_RATE * 2
    assert float(np.abs(chosen.samples).mean()) > 0.1


def test_excerpt_of_a_short_file_is_the_whole_file():
    audio = io.from_samples(fx.noise(seconds=1.0), SAMPLE_RATE)
    assert io.excerpt(audio, 20.0).frames == audio.frames


def test_resample_uses_the_exact_ratio():
    """44100 to 48000 is 160/147, not a float approximation of it."""
    resampled = io.resample(fx.noise(seconds=1.0, sample_rate=44100)[:, None], 44100, 48000)
    assert len(resampled) == pytest.approx(48000, abs=2)
