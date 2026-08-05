"""Comparison: named distances, honest gaps, and weights that live in data."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

from analysis import io
from analysis.compare import (
    DIMENSIONS, ProfileError, band_delta, compare, list_profiles, load_profile, scalar,
)
from analysis.fingerprint import Fingerprint, fingerprint
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


def _spectrum(band_db, centres=(125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0)):
    """A fingerprint carrying nothing but a band curve, built by hand.

    The sections are plain dicts by design, which makes the comparison functions
    testable against curves whose answer is arithmetic rather than a measurement.
    """
    return Fingerprint(
        source={"channels": 2, "regime": "probe", "lufs_i": -23.0},
        spectrum={"band_centres_hz": list(centres), "band_db": list(band_db)},
    )


def test_a_pure_level_difference_is_not_a_timbre_difference():
    """Every band up by 6 dB is the output gain, and `level` already has it.

    Leaving the mean in makes the optimiser chase volume instead of tone: the
    cheapest way to reduce a band-shape error becomes turning the amp down.
    """
    shape = [-4.0, -1.0, 0.0, 1.0, -2.0, -6.0]
    quiet = _spectrum(shape)
    loud = _spectrum([db + 6.0 for db in shape])

    objectives = compare(quiet, loud, profile="unpaired-v1")
    assert objectives.detail["timbre"]["band_shape"] == pytest.approx(0.0, abs=1e-9)

    # And a real shape change is still counted.
    tilted = _spectrum([db + 6.0 * i for i, db in enumerate(shape)])
    assert compare(quiet, tilted)["timbre"] > 0.5


def test_band_delta_removes_the_same_offset():
    """The table a person reads agrees with the objective about what a level is."""
    shape = [-4.0, -1.0, 0.0, 1.0, -2.0, -6.0]
    rows = band_delta(_spectrum(shape), _spectrum([db + 6.0 for db in shape]))
    assert all(abs(row["delta_db"]) < 1e-9 for row in rows), rows


def test_distortion_character_is_dropped_when_neither_side_could_measure_it():
    """HNR and odd/even measured across a chord describe the chord.

    The confidence gate is what keeps a search from chasing them. Without it a
    reference with no sustained monophonic note still produces harmonic numbers,
    and they move the optimiser as hard as real ones.
    """
    def with_harmonic(hnr, confidence):
        fp = _spectrum([0.0] * 6)
        fp.harmonic = {"hnr_db": hnr, "odd_even_ratio": 1.0,
                       "hf_residual_index": 0.1, "confidence": confidence}
        return fp

    unsure = compare(with_harmonic(20.0, 0.1), with_harmonic(6.0, 0.1))
    assert unsure["harmonic"] is None, unsure.detail["harmonic"]

    # One side being sure is not enough — the other still cannot support it.
    half = compare(with_harmonic(20.0, 0.9), with_harmonic(6.0, 0.1))
    assert half["harmonic"] is None

    confident = compare(with_harmonic(20.0, 0.9), with_harmonic(6.0, 0.9))
    assert confident["harmonic"] is not None and confident["harmonic"] > 0


def test_only_the_paired_profile_counts_the_waveform_residual():
    """What made paired-v1 paired, and was missing.

    The profile claimed time-domain features "mean what they say", but there was
    no waveform term at all — `align.residual_db` existed and nothing consumed
    it. Subtracting a commercial master from a render measures the difference
    between two performances, so the unpaired profile must not count it.
    """
    assert load_profile("paired-v1")["weights"]["residual"] > 0.5
    assert load_profile("unpaired-v1")["weights"]["residual"] == 0.0


def test_the_residual_dimension_is_supplied_not_derived():
    """Two fingerprints cannot produce it: a fingerprint drops the waveform."""
    a = make(fx.noise(seconds=2.0, seed=1))
    b = make(fx.noise(seconds=2.0, seed=2))

    assert compare(a, b, profile="paired-v1")["residual"] is None

    supplied = compare(a, b, profile="paired-v1", residual_db=-5.0)["residual"]
    assert supplied is not None and supplied > 0


def test_a_residual_at_the_render_noise_floor_scores_as_a_match():
    """M0 measured two renders of the *same* parameters differing by -17 dB.

    A paired objective that demanded better than that would rank the plugin's own
    per-render variation as an error no preset can fix.
    """
    a = make(fx.noise(seconds=2.0, seed=1))
    b = make(fx.noise(seconds=2.0, seed=2))

    assert compare(a, b, profile="paired-v1", residual_db=-17.0)["residual"] == 0.0
    assert compare(a, b, profile="paired-v1", residual_db=-40.0)["residual"] == 0.0
    # And worse than the floor is scored, in proportion.
    near = compare(a, b, profile="paired-v1", residual_db=-11.0)["residual"]
    far = compare(a, b, profile="paired-v1", residual_db=-5.0)["residual"]
    assert 0 < near < far


def test_the_residual_reaches_the_scalar_only_when_the_profile_wants_it():
    a = make(fx.noise(seconds=2.0, seed=1))
    b = make(fx.noise(seconds=2.0, seed=2))

    paired_without = scalar(compare(a, b, profile="paired-v1"))
    paired_with = scalar(compare(a, b, profile="paired-v1", residual_db=0.0))
    assert paired_with > paired_without, "a bad residual must cost something"

    unpaired_without = scalar(compare(a, b, profile="unpaired-v1"))
    unpaired_with = scalar(compare(a, b, profile="unpaired-v1", residual_db=0.0))
    assert unpaired_with == pytest.approx(unpaired_without), (
        "weighted zero, so it must not move the unpaired scalar at all"
    )
