"""Fingerprint v1 as a contract: it round-trips, it is versioned, it is honest."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

from analysis import FINGERPRINT_VERSION, io
from analysis.fingerprint import Fingerprint, FingerprintError, fingerprint
from tests import fixtures_audio as fx

SR = fx.SAMPLE_RATE


def make(samples, regime="probe"):
    return fingerprint(io.from_samples(samples, SR), regime=regime)


def test_roundtrip():
    """Fingerprint to JSON and back is lossless."""
    fp = make(fx.stereo(fx.band_limited(seconds=3.0), width=0.3))
    again = Fingerprint.from_json(fp.to_json())
    assert again.to_dict() == fp.to_dict()
    assert again.fingerprint_version == FINGERPRINT_VERSION


def test_json_is_a_plain_document():
    """Nothing in it needs this code to read: it is data, not a pickle."""
    fp = make(fx.band_limited(seconds=2.0))
    data = json.loads(fp.to_json())
    assert data["fingerprint_version"] == FINGERPRINT_VERSION
    assert set(data) == set(Fingerprint.SECTIONS) | {"fingerprint_version"}


def test_a_different_version_is_refused():
    """Results from different schema versions are never merged or compared."""
    data = make(fx.noise(seconds=2.0)).to_dict()
    data["fingerprint_version"] = 2
    with pytest.raises(FingerprintError, match="version"):
        Fingerprint.from_dict(data)


def test_ad_hoc_keys_are_refused():
    """Features are added by bumping the version, not by adding a key."""
    data = make(fx.noise(seconds=2.0)).to_dict()
    data["loudness_extra"] = 1.0
    with pytest.raises(FingerprintError, match="unknown field"):
        Fingerprint.from_dict(data)


def test_unknown_regime_is_refused():
    with pytest.raises(FingerprintError, match="regime"):
        make(fx.noise(seconds=1.0), regime="probably_a_stem")


def test_regime_carries_its_confidence():
    """A match against a mix is worth less than one against a paired DI."""
    assert make(fx.noise(seconds=2.0), regime="paired_di").regime_confidence > \
        make(fx.noise(seconds=2.0), regime="mix").regime_confidence


def test_features_are_level_invariant():
    """The same signal 14 dB apart fingerprints identically, except for level.

    This is what makes a mastered record comparable with a raw render.
    """
    signal = fx.stereo(fx.band_limited(seconds=4.0), width=0.3)
    quiet = make(signal * 0.1)
    loud = make(signal * 0.5)

    assert quiet.spectrum["band_db"] == pytest.approx(loud.spectrum["band_db"], abs=0.01)
    assert quiet.spectrum["tilt_db_per_decade"] == pytest.approx(
        loud.spectrum["tilt_db_per_decade"], abs=0.01)
    assert quiet.cepstral["mfcc_mean"] == pytest.approx(loud.cepstral["mfcc_mean"], abs=0.01)
    assert quiet.dynamics["crest_db"] == pytest.approx(loud.dynamics["crest_db"], abs=0.01)

    # Level itself is not invariant — it is the one thing that should differ.
    assert loud.source["lufs_i"] - quiet.source["lufs_i"] == pytest.approx(14.0, abs=0.1)


def test_missing_features_are_null_not_zero():
    """Noise has no sustained note. Saying so is different from saying zero."""
    fp = make(fx.noise(seconds=3.0))
    assert fp.harmonic["confidence"] == 0.0
    assert fp.harmonic["hnr_db"] is None
    assert fp.time_fx["delay_ms"] is None


def test_caveats_name_what_was_not_measured():
    fp = make(fx.noise(seconds=3.0), regime="mix")
    text = " ".join(fp.caveats())
    assert "mix" in text
    assert "monophonic" in text


def test_band_db_lookup():
    fp = make(fx.band_limited(seconds=2.0))
    assert fp.band_db(1000) is not None
    assert fp.band_db(1234) is None


@pytest.mark.parametrize(
    "name,samples",
    [
        ("one sample", [[0.5]]),
        ("ten samples", [[0.1]] * 10),
        ("one second of silence", [[0.0, 0.0]] * SR),
        ("denormal", [[1e-30]] * SR),
        ("full-scale DC", [[1.0, 1.0]] * SR),
    ],
)
def test_any_input_produces_a_valid_fingerprint(name, samples):
    """The M1 exit criterion, stated as a test: *any* input, not any nice input.

    Every one of these crashed something on the way to passing. A matcher that
    falls over on a silent render is a matcher that falls over mid-search.
    """
    import numpy as np

    fp = make(np.asarray(samples, dtype=np.float32))
    assert Fingerprint.from_json(fp.to_json()).to_dict() == fp.to_dict(), name
    assert fp.spectrum["band_db"], name


def test_excerpt_is_applied_before_measuring():
    """A long file records exactly which active window was measured."""
    import numpy as np

    padded = np.concatenate([np.zeros(SR * 5), fx.band_limited(seconds=4.0), np.zeros(SR * 5)])
    fp = fingerprint(io.from_samples(padded, SR), excerpt_s=3.0)
    assert fp.source["duration_s"] == pytest.approx(3.0, abs=0.01)
    assert fp.source["lufs_i"] is not None
    assert fp.source["source_duration_s"] == pytest.approx(14.0)
    assert fp.source["excerpt_end_s"] - fp.source["excerpt_start_s"] == \
        pytest.approx(3.0, abs=1 / SR)
    assert 4.9 < fp.source["excerpt_start_s"] < 6.1
    assert fp.source["excerpt_requested_s"] == 3.0
    assert fp.source["excerpt_policy"] == "most_continuously_active"


def test_a_short_source_records_that_the_full_file_was_used():
    fp = fingerprint(io.from_samples(fx.noise(seconds=1.0), SR), excerpt_s=20.0)
    assert fp.source["excerpt_start_s"] == 0.0
    assert fp.source["excerpt_end_s"] == pytest.approx(1.0)
    assert fp.source["source_duration_s"] == pytest.approx(1.0)
    assert fp.source["excerpt_requested_s"] == 20.0
    assert fp.source["excerpt_policy"] == "full_source"
