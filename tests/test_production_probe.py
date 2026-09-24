"""The fallback probe used by production is named and owned honestly."""

from __future__ import annotations

import pathlib
import sys

import pytest

np = pytest.importorskip("numpy", reason="needs the analysis extra")

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from _cli import probe_di  # noqa: E402
from analysis.probes import decaying_noise_bursts  # noqa: E402
from tests import fixtures_audio as fx  # noqa: E402


def test_production_probe_is_byte_identical_to_the_original_fixture():
    """Moving it out of tests must not move any historical benchmark number."""
    production = decaying_noise_bursts(seconds=2.0, gap=0.9, seed=13)
    original = fx.plucks(seconds=2.0, gap=0.9, seed=13)
    assert np.array_equal(production, original)


def test_fallback_names_noise_bursts_not_guitar_plucks():
    samples, caveat = probe_di(None, seconds=2.0)
    assert len(samples) == 2 * fx.SAMPLE_RATE
    assert "noise-burst" in caveat
    assert "pluck" not in caveat


def test_the_synthetic_guitar_is_a_played_di_by_its_level_and_repeats_exactly():
    """A research search signal whose negative result the plan doc records, so it
    has to repeat bit for bit to be reproducible, sit at a played DI's loudness,
    and — at its default seed — stay under full scale, where the noise probe peaks
    at +10.5 dBFS. Other seeds can clip; only the default is measured."""
    from analysis import io
    from analysis.probes import synthetic_guitar

    first, again = synthetic_guitar(), synthetic_guitar()
    assert np.array_equal(first, again)
    assert len(first) == 6 * fx.SAMPLE_RATE
    audio = io.from_samples(first, fx.SAMPLE_RATE)
    assert io.loudness_lufs(audio) == pytest.approx(-17.0, abs=0.1)
    assert np.abs(first).max() < 1.0
    assert not np.array_equal(first, synthetic_guitar(seed=14)), "the seed matters"
    # Pinned to the signal the two committed runs used (samples sha256
    # b08146d9...), by value rather than by hash so a platform's last-bit
    # rounding does not fail it while a changed random stream or filter does.
    signal = first.astype(np.float64)
    assert float(np.sqrt(np.mean(signal ** 2))) == pytest.approx(0.1207730743, rel=1e-6)
    assert float(signal[1000]) == pytest.approx(0.0956163555, rel=1e-6)
    assert float(signal[150000]) == pytest.approx(0.0409496017, rel=1e-6)
