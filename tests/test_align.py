"""Alignment: the offset and polarity between two takes of the same audio."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

import numpy as np
from scipy import signal as scipy_signal

from analysis import align
from tests import fixtures_audio as fx

SR = fx.SAMPLE_RATE
EDGE = 2000  # ignore the zeros a shift necessarily introduces at the ends


def band_limited_noise(seconds: float = 2.0, seed: int = 3):
    """Band-limited, so a fractional-sample shift is exactly representable."""
    sos = scipy_signal.butter(4, 8000, fs=SR, output="sos")
    return scipy_signal.sosfilt(sos, fx.noise(seconds=seconds, seed=seed))


def shifted(signal_1d, samples: int, fractional: float = 0.0, polarity: int = 1):
    out = np.zeros_like(signal_1d)
    if samples >= 0:
        out[samples:] = signal_1d[: len(signal_1d) - samples]
    else:
        out[:samples] = signal_1d[-samples:]
    if fractional:
        out = align._fractional_shift(out, fractional)
    return out * polarity


@pytest.mark.parametrize(
    "offset,fractional,polarity",
    [(57, 0.0, 1), (-120, 0.0, 1), (57, 0.35, 1), (0, 0.0, -1), (240, -0.4, -1)],
)
def test_recovers_known_offset_and_polarity(offset, fractional, polarity):
    reference = band_limited_noise()
    candidate = shifted(reference, offset, fractional, polarity)

    found = align.find_alignment(reference, candidate, SR)
    assert found.offset_samples == offset
    assert found.fractional_offset == pytest.approx(fractional, abs=0.05)
    assert found.polarity == polarity
    assert abs(found.correlation) > 0.9


@pytest.mark.parametrize("offset,fractional", [(57, 0.0), (-120, 0.0), (240, -0.4)])
def test_applying_the_alignment_removes_the_difference(offset, fractional):
    """The point of aligning: what is left over is the audio, not the offset."""
    reference = band_limited_noise()
    candidate = shifted(reference, offset, fractional)

    before = align.residual_db(reference, candidate)
    a, b, _ = align.align(reference, candidate, SR)
    after = align.residual_db(a[EDGE:-EDGE], b[EDGE:-EDGE])
    assert after < -30.0
    assert after < before - 20.0


def test_offset_in_milliseconds_reads_correctly():
    """M0 measured 57 samples between two hosts; that is 1.19 ms."""
    reference = band_limited_noise()
    found = align.find_alignment(reference, shifted(reference, 57), SR)
    assert found.offset_ms == pytest.approx(57 / SR * 1000.0, abs=0.02)


def test_unrelated_signals_are_not_aligned():
    """A bad alignment is worse than none: it invents a timing that is not there."""
    a = band_limited_noise(seed=1)
    b = band_limited_noise(seed=2)
    found = align.find_alignment(a, b, SR)
    assert not found.trustworthy

    left, right, _ = align.align(a, b, SR)
    assert len(left) == len(right) == min(len(a), len(b))
    assert np.array_equal(right, b[: len(right)])


def test_silence_does_not_raise():
    silence = np.zeros(SR)
    found = align.find_alignment(silence, silence, SR)
    assert found.offset_samples == 0
    assert found.correlation == 0.0
    assert align.residual_db(silence, silence) is None
