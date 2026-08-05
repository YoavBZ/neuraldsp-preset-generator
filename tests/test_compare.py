"""Comparison: named distances, honest gaps, and weights that live in data."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

from analysis import io
from analysis.compare import (
    DIMENSIONS, ProfileError, band_delta, compare, list_profiles, load_profile, scalar,
)
from analysis.fingerprint import fingerprint
from tests import fixtures_audio as fx

SR = fx.SAMPLE_RATE


def make(samples, regime="probe"):
    return fingerprint(io.from_samples(samples, SR), regime=regime)


def test_identical_fingerprints_score_zero():
    fp = make(fx.stereo(fx.band_limited(seconds=3.0), width=0.3))
    objectives = compare(fp, fp)
    for name, value in objectives.measured().items():
        assert value == pytest.approx(0.0, abs=1e-9), name
    assert scalar(objectives) == pytest.approx(0.0, abs=1e-9)


def test_every_dimension_is_named():
    fp = make(fx.band_limited(seconds=2.0))
    assert set(compare(fp, fp).values) == set(DIMENSIONS)


def test_a_brighter_candidate_costs_timbre():
    dark = make(fx.band_limited(seconds=3.0, high=2000, seed=3))
    bright = make(fx.band_limited(seconds=3.0, high=8000, seed=3))
    assert compare(dark, bright)["timbre"] > 0.5


def test_a_closer_candidate_scores_lower():
    """The property an optimiser depends on: closer must mean smaller."""
    target = make(fx.band_limited(seconds=3.0, high=4000, seed=3))
    near = make(fx.band_limited(seconds=3.0, high=4400, seed=3))
    far = make(fx.band_limited(seconds=3.0, high=9000, seed=3))
    assert compare(target, near)["timbre"] < compare(target, far)["timbre"]
    assert scalar(compare(target, near)) < scalar(compare(target, far))


def test_a_level_difference_is_not_a_timbre_difference():
    """Turning it up must not look like a tone change; that is what `level` is for."""
    signal = fx.band_limited(seconds=3.0)
    quiet, loud = make(signal * 0.1), make(signal * 0.6)
    objectives = compare(quiet, loud)
    assert objectives["timbre"] == pytest.approx(0.0, abs=0.02)
    assert objectives["level"] > 0.5


def test_unmeasurable_dimensions_are_none_not_zero():
    """Noise has no harmonic series. Ambience and harmonic must abstain."""
    fp = make(fx.noise(seconds=3.0))
    objectives = compare(fp, fp)
    assert objectives["harmonic"] is None
    assert objectives["spatial"] is None


def test_a_missing_dimension_does_not_flatter_the_score():
    """An abstaining dimension is dropped from the mean, not scored as perfect."""
    target = make(fx.band_limited(seconds=3.0, high=2000, seed=3))
    candidate = make(fx.band_limited(seconds=3.0, high=8000, seed=3))
    objectives = compare(target, candidate)
    combined = scalar(objectives)
    measured = objectives.measured()
    assert combined >= min(measured.values())
    assert combined <= max(measured.values())


def test_an_echo_on_only_one_side_is_a_full_unit_of_wrong():
    dry = make(fx.plucks(seconds=8.0))
    wet = make(fx.with_echo(fx.plucks(seconds=8.0), 0.42, 0.35))
    assert compare(dry, wet).detail["ambience"]["delay_present"] == 1.0


def test_prior_and_complexity_are_passed_in():
    """They are the optimiser's business, not a property of two recordings."""
    fp = make(fx.band_limited(seconds=2.0))
    objectives = compare(fp, fp, prior_deviation=0.4, complexity=0.2)
    assert objectives["prior_deviation"] == 0.4
    assert objectives["complexity"] == 0.2


def test_band_delta_reads_as_what_the_candidate_is_missing():
    """Positive means the candidate is short in that band."""
    dark = make(fx.band_limited(seconds=3.0, high=2000, seed=3))
    bright = make(fx.band_limited(seconds=3.0, high=8000, seed=3))
    rows = {row["centre_hz"]: row["delta_db"] for row in band_delta(dark, bright)}
    assert rows[6300] < -3.0   # the candidate has too much up there
    assert rows[250] > 1.0     # and not enough down here


def test_profiles_are_data():
    """Weights are tunable without editing code, and both shipped ones parse."""
    assert "unpaired-v1" in list_profiles()
    assert "paired-v1" in list_profiles()
    for name in list_profiles():
        profile = load_profile(name)
        assert set(profile["weights"]) == set(DIMENSIONS)
        assert profile["scales"]["band_db"] > 0


def test_unknown_profile_is_refused():
    with pytest.raises(ProfileError, match="unknown loss profile"):
        load_profile("vibes-v3")


def test_paired_profile_weights_time_features_higher():
    """The stated reason paired-v1 exists: the performance is the same, so the
    envelope means what it says."""
    unpaired = load_profile("unpaired-v1")["weights"]
    paired = load_profile("paired-v1")["weights"]
    assert paired["dynamics"] > unpaired["dynamics"]
    assert paired["ambience"] > unpaired["ambience"]
