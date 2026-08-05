"""Each feature against a signal whose answer is known in advance.

These are the tests that decide whether the analysis core is worth building on.
A feature that cannot recover a parameter from a signal built with that exact
parameter will not recover it from a guitar recording, and every milestone after
this one consumes these numbers.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

import numpy as np
from scipy import signal as scipy_signal

from analysis import features as F
from tests import fixtures_audio as fx

SR = fx.SAMPLE_RATE


def test_ltas_matches_known_filter():
    """White noise through a known biquad: the band curve recovers its shape."""
    flat = fx.noise(seconds=4.0)
    sos = scipy_signal.butter(2, [300, 3000], btype="band", fs=SR, output="sos")
    filtered = scipy_signal.sosfilt(sos, flat)

    before = F.third_octave_bands(flat, SR)
    after = F.third_octave_bands(filtered, SR)
    measured = np.array(after["band_db"]) - np.array(before["band_db"])

    centres = np.array(before["band_centres_hz"])
    _, response = scipy_signal.sosfreqz(sos, worN=centres, fs=SR)
    expected = 20 * np.log10(np.abs(response) + 1e-12)

    usable = (centres >= 50) & (centres <= 16000)
    assert np.abs(measured[usable] - expected[usable]).max() < 1.0


def test_delay_detection_exact():
    """A 420 ms echo at 0.35 feedback is recovered as 420 ms at 0.35."""
    dry = fx.plucks()
    wet = fx.with_echo(dry, delay_s=0.420, feedback=0.35)
    result = F.time_effects(wet, SR)

    assert result["delay_ms"] == pytest.approx(420.0, abs=5.0)
    assert result["delay_feedback_est"] == pytest.approx(0.35, abs=0.05)
    assert result["delay_confidence"] > 0.1


def test_no_delay_is_reported_when_there_is_none():
    """The same material without an echo reports nothing, not a small number.

    Worth its own test: the failure that matters is not a wrong delay time, it
    is confidently inventing an effect the reference does not have.
    """
    assert F.time_effects(fx.plucks(), SR)["delay_ms"] is None
    assert F.time_effects(fx.noise(seconds=6.0), SR)["delay_ms"] is None


def test_delay_is_not_confused_with_the_playing_rate():
    """Notes every 900 ms and an echo at 420 ms: the echo is the answer.

    Envelope autocorrelation alone returns 900 here — the tempo. This is the
    test that pins the waveform-and-envelope agreement in `_detect_delay`.
    """
    wet = fx.with_echo(fx.plucks(gap=0.9), delay_s=0.420, feedback=0.35)
    assert F.time_effects(wet, SR)["delay_ms"] == pytest.approx(420.0, abs=5.0)


def test_delay_is_not_confused_with_pitch_periodicity():
    """A sustained note correlates with itself every period. That is not a delay."""
    held = fx.harmonic_note(seconds=4.0, f0=196.0)
    assert F.time_effects(held, SR)["delay_ms"] is None


def test_rt60_from_synthetic_decay():
    """Exponentially decaying bursts recover their RT60 within 15%."""
    for rt60 in (0.6, 1.2, 2.4):
        result = F.time_effects(fx.decaying_bursts(rt60_s=rt60), SR)
        assert result["rt60_s"] == pytest.approx(rt60, rel=0.15), f"rt60={rt60}"
        assert result["rt60_confidence"] > 0.5


def test_tremolo_rate():
    """5 Hz amplitude modulation is recovered as 5 Hz, with its depth."""
    result = F.modulation(fx.tremolo(fx.noise(seconds=6.0), rate_hz=5.0, depth=0.6), SR)
    assert result["am_rate_hz"] == pytest.approx(5.0, abs=0.2)
    assert result["am_depth"] == pytest.approx(0.6, abs=0.1)
    assert result["am_confidence"] > 0.8


def test_tremolo_is_distinguished_from_playing_rate():
    """Strumming at 2 Hz is not a 2 Hz tremolo, and the confidence says so.

    Nothing in the audio makes these different rates, so the honest answer is a
    reported rate with a low confidence rather than a silent assertion.
    """
    played = F.modulation(fx.plucks(seconds=6.0, gap=0.5, decay=6.0, length=0.45), SR)
    tremolo = F.modulation(fx.tremolo(fx.noise(seconds=6.0), rate_hz=2.0), SR)
    assert played["am_rate_hz"] == pytest.approx(2.0, abs=0.2)
    assert played["am_confidence"] < 0.75
    assert tremolo["am_confidence"] > 0.9


def test_tremolo_is_found_under_the_playing():
    """A 5 Hz tremolo over notes at 1.1 Hz is found, not the note rate."""
    played = fx.plucks(seconds=6.0, gap=0.9, decay=4.0, length=0.8)
    result = F.modulation(fx.tremolo(played, rate_hz=5.0, depth=0.6), SR)
    assert result["am_rate_hz"] == pytest.approx(5.0, abs=0.2)
    assert result["am_confidence"] > 0.8


def test_steady_signal_has_no_tremolo():
    assert F.modulation(fx.noise(seconds=6.0), SR)["am_rate_hz"] is None


def test_harmonic_features_need_a_sustained_note():
    """A note gives a fundamental and an HNR; noise gives nothing and admits it."""
    note = F.harmonic(fx.harmonic_note(seconds=2.0, f0=196.0), SR)
    assert note["f0_hz"] == pytest.approx(196.0, rel=0.03)
    assert note["confidence"] > 0.5
    assert note["hnr_db"] > 10.0

    from_noise = F.harmonic(fx.noise(seconds=2.0), SR)
    assert from_noise["confidence"] == 0.0
    assert from_noise["hnr_db"] is None
    assert from_noise["odd_even_ratio"] is None


def test_spectral_tilt_tracks_brightness():
    """A brighter filter is a less negative tilt."""
    dark = F.third_octave_bands(fx.band_limited(high=2000), SR)
    bright = F.third_octave_bands(fx.band_limited(high=8000), SR)
    dark_tilt = F.spectral_tilt(dark["band_centres_hz"], dark["band_db"])
    bright_tilt = F.spectral_tilt(bright["band_centres_hz"], bright["band_db"])
    assert bright_tilt > dark_tilt


def test_corner_frequencies_track_the_filter():
    """Corners are comparative, not absolute — a wider filter reads wider."""
    for low, high in ((90, 2000), (90, 5000), (90, 9000)):
        bands = F.third_octave_bands(fx.band_limited(low=low, high=high), SR)
        corners = F.corner_frequencies(bands["band_centres_hz"], bands["band_db"])
        assert corners["hf_corner_hz"] is not None
        if low == 90 and high == 2000:
            narrow = corners["hf_corner_hz"]
        else:
            assert corners["hf_corner_hz"] > narrow


def test_onsets_find_the_notes():
    """Nine bursts 0.9 s apart are found as about nine onsets."""
    found = F.onsets(fx.plucks(seconds=8.0, gap=0.9), SR)
    assert 7 <= len(found) <= 10
    spacing = np.diff(found) / SR
    assert np.median(spacing) == pytest.approx(0.9, abs=0.1)


def test_spatial_reports_mono_as_mono():
    mono = fx.stereo(fx.noise(seconds=2.0), width=0.0)
    result = F.spatial(mono, SR)
    assert result["width"] == pytest.approx(0.0, abs=1e-6)
    assert result["correlation"] == pytest.approx(1.0, abs=1e-6)


def test_spatial_width_increases_with_decorrelation():
    narrow = F.spatial(fx.stereo(fx.noise(seconds=2.0), width=0.2), SR)
    wide = F.spatial(fx.stereo(fx.noise(seconds=2.0), width=0.8), SR)
    assert wide["width"] > narrow["width"] > 0.0
    assert wide["correlation"] < narrow["correlation"]


def test_cepstral_shape_is_stable_and_discriminative():
    """Same signal, same MFCCs; different filter, different MFCCs."""
    dark = fx.band_limited(high=2000, seed=3)
    a = F.cepstral(dark, SR)
    b = F.cepstral(dark, SR)
    c = F.cepstral(fx.band_limited(high=8000, seed=3), SR)
    assert a["mfcc_mean"] == b["mfcc_mean"]
    difference = np.abs(np.array(a["mfcc_mean"]) - np.array(c["mfcc_mean"])).max()
    assert difference > 1.0


def test_dynamics_separate_a_compressed_signal_from_a_dynamic_one():
    """Crest factor falls when the peaks are squashed, which is what it is for."""
    dynamic = fx.plucks(seconds=6.0)
    squashed = np.tanh(dynamic * 8.0)
    assert F.dynamics(squashed, SR)["crest_db"] < F.dynamics(dynamic, SR)["crest_db"]
