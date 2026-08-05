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
    for f0 in (110.0, 196.0, 330.0):
        held = fx.harmonic_note(seconds=4.0, f0=f0)
        assert F.time_effects(held, SR)["delay_ms"] is None, f"f0={f0}"


def test_delay_is_found_when_notes_ring_into_each_other():
    """The case the envelope veto used to reject: a real echo on dense material.

    Once notes overlap, the envelope stops dipping between them, so an echo adds
    nothing an envelope autocorrelation can see — a real 420 ms echo scored 0.348
    on the waveform against -0.012 on the envelope, and the veto threw it away.
    The envelope only vetoes where it has note structure to veto with.
    """
    for pulse in (0.25, 0.3, 0.5):
        for delay_s in (0.180, 0.420):
            wet = fx.with_echo(fx.dense(pulse=pulse), delay_s=delay_s, feedback=0.35)
            result = F.time_effects(wet, SR)
            assert result["delay_ms"] == pytest.approx(delay_s * 1000, abs=20.0), (
                f"pulse={pulse} delay={delay_s}"
            )
            assert result["delay_confidence"] > 0.15
            assert result["delay_feedback_est"] == pytest.approx(0.35, abs=0.08)


def test_a_repeated_phrase_is_not_reported_as_a_confident_delay():
    """Four notes coming round every second repeat in the waveform *and* the
    envelope, exactly as an echo does.

    This used to be reported as a 1000 ms delay at confidence 0.86 — higher than
    the detector ever reports a correct answer. Nothing in the audio alone
    separates a phrase repeat from a tempo-synced delay, so the reading is capped
    below the confidence `compare._ambience` requires instead of being trusted.
    """
    for pulse in (0.25, 0.4):
        for signal in (fx.dense(pulse=pulse, tonal=True),
                       fx.with_echo(fx.dense(pulse=pulse, tonal=True), 0.420, 0.35)):
            result = F.time_effects(signal, SR)
            assert result["delay_confidence"] < 0.15, (
                f"pulse={pulse}: reported {result['delay_ms']} ms at "
                f"{result['delay_confidence']}"
            )


def test_an_echo_that_decays_is_told_from_one_that_does_not():
    """The gate underneath both cases above: an echo gets quieter, a loop does not.

    Feedback is recovered across the usable range, and the *estimate* is checked
    too — without that, `DELAY_MAX_REPEAT_RATIO` could be raised to 0.999,
    disabling the gate three docstrings call load-bearing, with a green suite.
    """
    for feedback in (0.15, 0.35, 0.55, 0.75):
        result = F.time_effects(fx.with_echo(fx.plucks(gap=0.9), 0.420, feedback), SR)
        assert result["delay_ms"] == pytest.approx(420.0, abs=5.0), f"feedback={feedback}"
        assert result["delay_feedback_est"] == pytest.approx(feedback, abs=0.1)


def test_a_verbatim_loop_is_not_reported_as_a_delay():
    """What `DELAY_MAX_REPEAT_RATIO` is actually for, and nothing tested it.

    Setting the ratio to 0.999 — deleting the gate three docstrings call
    load-bearing — passed the entire suite. The reason is that every other
    recurring fixture is *pitched*, so it fills the search band with a comb and
    the comb rule catches it. A broadband phrase repeated verbatim has no such
    signature: the only thing separating it from an echo is that its repeats do
    not get quieter, and without the gate it comes back at the loop period with
    confidence 0.9, higher than a real echo ever scores.

    The cost of the gate is real and is stated on `_detect_delay`: it is why an
    echo above about 0.85 feedback is declined rather than measured.
    """
    for period in (0.8, 1.0, 1.5):
        result = F.time_effects(fx.looped_phrase(period=period), SR)
        assert result["delay_ms"] is None, (
            f"a {period}s loop was reported as a {result['delay_ms']} ms delay "
            f"at confidence {result['delay_confidence']}"
        )

    # And a real echo laid over the same looped material is still found, so the
    # gate is not simply refusing everything on this input.
    over_a_loop = F.time_effects(
        fx.with_echo(fx.looped_phrase(period=1.0), 0.420, 0.35), SR)
    assert over_a_loop["delay_ms"] == pytest.approx(420.0, abs=20.0)


def test_a_runaway_echo_abstains_instead_of_reporting_a_multiple():
    """The stated limit above 0.85 feedback, now actually exercised.

    This was claimed and untested, and the claim was false. Rejecting a lag for
    recurring is worthless if the same echo's 2T, 3T … 7T peaks are then offered
    and accepted: a 250 ms echo at 0.90 came back as 500 ms at confidence 0.76,
    and once two fixed divisors were tried, as 1750 ms. There is no bound on which
    harmonic carries the most prominence, so `fundamental()` searches the peaks
    that are present.

    The requirement is therefore not "detects it" but **never reports a wrong
    number**: either the true time, or nothing.
    """
    for delay_s, feedback in [(0.250, 0.85), (0.250, 0.90), (0.250, 0.95),
                              (0.420, 0.88), (0.420, 0.90), (0.420, 0.95),
                              (0.180, 0.92), (0.650, 0.93)]:
        result = F.time_effects(
            fx.with_echo(fx.plucks(seconds=10.0, gap=0.9), delay_s, feedback), SR)
        measured = result["delay_ms"]
        assert measured is None or measured == pytest.approx(delay_s * 1000, abs=20.0), (
            f"delay={delay_s * 1000:.0f} ms at feedback {feedback} reported "
            f"{measured} ms, a multiple of the truth"
        )


def test_a_delay_is_reported_at_its_fundamental_not_at_a_harmonic():
    """Directly, so the mechanism is pinned and not only its consequence."""
    for delay_s in (0.250, 0.420):
        result = F.time_effects(
            fx.with_echo(fx.plucks(seconds=10.0, gap=1.4), delay_s, 0.55), SR)
        assert result["delay_ms"] == pytest.approx(delay_s * 1000, abs=20.0)


def test_rt60_from_synthetic_decay():
    """Exponentially decaying bursts recover their RT60 within 15%."""
    for rt60 in (0.6, 1.2, 2.4):
        result = F.time_effects(fx.decaying_bursts(rt60_s=rt60), SR)
        assert result["rt60_s"] == pytest.approx(rt60, rel=0.15), f"rt60={rt60}"
        assert result["rt60_confidence"] > 0.5


def test_onsets_land_on_the_note_and_not_a_window_early():
    """An onset must be reported where the note is, within about one hop.

    `_frames` is uncentred, so a transient raises the spectral flux one whole
    analysis window before it happens. Reporting the frame's start put every
    onset about 30 ms early — larger than the attack times measured against it,
    and comparable to the pre-delays. Nothing caught it, because every feature
    downstream searched forward from the onset and found the note anyway.
    """
    hop_ms = F.FRAME_HOP / SR * 1000.0
    for gap in (0.9, 1.3):
        truth = np.arange(0.1, 8.0 - 0.4, gap)
        found = F.onsets(fx.plucks(seconds=8.0, gap=gap), SR) / SR
        assert len(found) >= len(truth)
        error = np.array([(found[np.argmin(np.abs(found - t))] - t) * 1000 for t in truth])
        assert np.abs(error).max() < 1.5 * hop_ms, f"gap={gap}, errors {error}"
        assert abs(error.mean()) < hop_ms, f"gap={gap}: systematic bias {error.mean():.1f} ms"


def test_rolloff_is_the_85_percent_point_and_not_the_middle():
    """85% of the energy sits below `rolloff85_hz`.

    Half the energy sits a long way below that, so a signal with a wide, flat
    band separates the two: the median of this spectrum is near 4 kHz and its
    85% point near 7 kHz.
    """
    wide = fx.band_limited(seconds=4.0, low=100.0, high=8000.0, seed=4)
    rolloff = F.spectral_statistics(wide, SR)["rolloff85_hz"]["p50"]
    assert 5500.0 < rolloff < 9000.0, f"rolloff85 came out at {rolloff} Hz"


def test_corner_frequencies_are_the_six_dB_points():
    """Measured against a curve whose 6 dB and 12 dB points are known by hand.

    A flat top with a 3 dB-per-band skirt puts -6 dB two bands out and -12 dB
    four bands out, which is far enough apart that reading the wrong one cannot
    pass. The interpolation lands between band centres, so the assertion is a
    range bracketing the true crossing rather than a single frequency.
    """
    centres = list(F.THIRD_OCTAVE_CENTRES)
    first, last = centres.index(500.0), centres.index(2000.0)
    band_db = [
        0.0 if first <= i <= last else -3.0 * (first - i if i < first else i - last)
        for i in range(len(centres))
    ]

    corners = F.corner_frequencies(centres, band_db)
    # -6 dB lands exactly two bands out: 315 Hz below and 3150 Hz above.
    # The -12 dB points would be 200 Hz and 5 kHz.
    assert corners["lf_corner_hz"] == pytest.approx(315.0, rel=1e-6), corners
    assert corners["hf_corner_hz"] == pytest.approx(3150.0, rel=1e-6), corners


def test_tilt_is_fitted_over_the_guitar_range_only():
    """The fit stops at 10 kHz, so what happens above it cannot move the answer.

    The top and bottom of a third-octave curve are dominated by the source's own
    filtering rather than by the amp. Here the curve is a clean -6 dB per decade
    line up to 10 kHz and then climbs steeply; a fit that included the climb
    would report a shallower slope than the line actually has.
    """
    import numpy as np

    centres = [c for c in F.THIRD_OCTAVE_CENTRES if c >= 50.0]
    band_db = []
    for centre in centres:
        if centre <= 10000.0:
            band_db.append(-6.0 * np.log10(centre / 50.0))
        else:
            band_db.append(-6.0 * np.log10(10000.0 / 50.0) + 30.0)

    assert F.spectral_tilt(centres, band_db) == pytest.approx(-6.0, abs=0.5)


def test_predelay_recovers_a_known_gap_before_the_tail():
    """A direct sound, a gap, then a decaying tail: the gap is recovered.

    The tolerance is one envelope-smoothing width and no more. The envelope is
    low-passed at 60 Hz, which blurs the crossover by a consistent +5 ms, so 10 ms
    is the honest bound — at 20 ms a detector that added a flat 15 ms passed.
    """
    for want in (80.0, 120.0, 150.0, 200.0):
        signal = fx.bursts_with_predelay(predelay_ms=want)
        assert F.time_effects(signal, SR)["predelay_ms"] == pytest.approx(want, abs=10.0), (
            f"predelay={want}"
        )


def test_predelay_is_found_when_the_tail_is_quieter_than_the_direct_sound():
    """The normal case, and the one that used to be silently skipped.

    `db` is measured relative to the attack, so anchoring the rise on `argmax(db)`
    only worked when the tail was *louder* than the direct sound — otherwise
    `argmax` returned 0 and the onset was discarded, 108 of 175 windows. The
    original fixture passed at `tail_level=0.5` purely because a 1.6 s tail
    survives envelope smoothing louder than the 12 ms burst that caused it.
    """
    for tail_level in (0.1, 0.2, 0.3):
        for want in (80.0, 150.0):
            signal = fx.bursts_with_predelay(predelay_ms=want, tail_level=tail_level)
            measured = F.time_effects(signal, SR)["predelay_ms"]
            assert measured == pytest.approx(want, abs=10.0), (
                f"tail_level={tail_level}, predelay={want}: got {measured}"
            )


def test_predelay_abstains_when_nothing_is_separated():
    """Dry material has no pre-delay, and inventing one would set a reverb control.

    Every one of these decays without a tail arriving after it. A pre-delay
    reported here would come from the shape of a note.
    """
    for label, signal in (
        ("plain decaying bursts", fx.decaying_bursts(rt60_s=1.2)),
        ("long reverb, no pre-delay", fx.decaying_bursts(rt60_s=2.4)),
        ("sustained note", fx.harmonic_note(seconds=4.0)),
        ("dry plucks", fx.plucks(seconds=8.0)),
        ("plucks that ring on", fx.plucks(seconds=8.0, decay=6.0, length=0.8)),
        ("white noise", fx.noise(seconds=4.0)),
        ("an echo, which is not a reverb", fx.with_echo(fx.plucks(seconds=8.0), 0.42, 0.35)),
    ):
        assert F.time_effects(signal, SR)["predelay_ms"] is None, label


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
    """Same signal, same MFCCs; different filter, different MFCCs.

    "Same signal, same MFCCs" used to be checked by calling `cepstral` twice on one
    array, which is comparing a pure function with itself — it cannot fail. Stability
    that means something is across a *different realisation* of the same process:
    two noise seeds through the same filter must land close together while a
    different filter lands far away.
    """
    dark = F.cepstral(fx.band_limited(high=2000, seed=3), SR)
    dark_again = F.cepstral(fx.band_limited(high=2000, seed=11), SR)
    bright = F.cepstral(fx.band_limited(high=8000, seed=3), SR)

    same_process = np.abs(np.array(dark["mfcc_mean"]) - np.array(dark_again["mfcc_mean"])).max()
    different_filter = np.abs(np.array(dark["mfcc_mean"]) - np.array(bright["mfcc_mean"])).max()
    assert same_process < 1.0, f"two seeds of one process differ by {same_process:.2f}"
    assert different_filter > 1.0
    assert different_filter > same_process * 3.0


def test_the_cepstrum_is_a_dct_of_the_mel_energies_and_not_the_energies():
    """The first coefficient is overall level, which is why `compare._timbre`
    skips it. That is only true of a DCT: dropping the transform, or offsetting
    which coefficients are kept, leaves the field no longer an MFCC mean while
    every "is it stable, is it discriminative" assertion still passes.

    Checked against the property the DCT gives and the raw energies do not — a
    strong level change moves coefficient 0 far more than the rest.
    """
    quiet = F.cepstral(fx.band_limited(high=4000, seed=5) * 0.05, SR)
    loud = F.cepstral(fx.band_limited(high=4000, seed=5) * 0.9, SR)

    coefficients = np.array(loud["mfcc_mean"]) - np.array(quiet["mfcc_mean"])
    assert abs(coefficients[0]) > 5.0, "coefficient 0 must carry the level"
    assert np.abs(coefficients[1:]).max() < abs(coefficients[0]) / 3.0, (
        f"the shape coefficients moved with the level: {coefficients}"
    )


def test_dynamics_separate_a_compressed_signal_from_a_dynamic_one():
    """Crest factor falls when the peaks are squashed, which is what it is for."""
    dynamic = fx.plucks(seconds=6.0)
    squashed = np.tanh(dynamic * 8.0)
    assert F.dynamics(squashed, SR)["crest_db"] < F.dynamics(dynamic, SR)["crest_db"]
