"""The aligned distance: zero for the same audio, blind to level, monotonic in tone
changes, robust to lag, sensitive to tails, and deaf to bleed it should not judge."""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("pyloudnorm", reason="needs the analysis extra")
scipy_signal = pytest.importorskip("scipy.signal", reason="needs the analysis extra")

from analysis.aligned import aligned_distance, estimate_lag  # noqa: E402

SR = 48000


def _performance(seconds=10.0, seed=0, rest=None):
    """A DI-like part: notes with short gaps, and a longer `rest` (start, end) in
    seconds if given, so frames where nothing plays exist."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    di = np.zeros_like(t)
    start = 0.3
    while start < seconds - 0.5:
        if rest and rest[0] <= start < rest[1]:
            start = rest[1]
            continue
        length = rng.uniform(0.25, 0.6)
        f0 = rng.choice([82.4, 110.0, 146.8, 196.0, 246.9, 329.6])
        idx = (t >= start) & (t < start + length)
        tt = t[idx] - start
        note = sum(np.sin(2 * np.pi * f0 * k * tt) / k for k in range(1, 12))
        di[idx] += 0.2 * note * np.exp(-tt * 4)
        start += length + rng.uniform(0.05, 0.4)
    return di


def _amp(di, drive=4.0, tone=(200, 4000)):
    """A stand-in for a rig: drive, then a band-pass 'cab'."""
    b, a = scipy_signal.butter(2, tone, btype="bandpass", fs=SR)
    return scipy_signal.lfilter(b, a, np.tanh(drive * di))


def _shelf(x, freq, gain_db):
    """A peaking boost of `gain_db` around `freq`, one octave wide."""
    w0 = 2 * np.pi * freq / SR
    A = 10 ** (gain_db / 40)
    alpha = np.sin(w0) / 2 * 1.41
    b = [1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A]
    return scipy_signal.lfilter(b, a, x)


def _delay(x, samples):
    return np.concatenate([np.zeros(samples), x])[: len(x)]


def test_the_same_audio_is_at_zero_and_level_does_not_count():
    di = _performance()
    render = _amp(di)
    same = aligned_distance(render, render, di, render_latency=0, lag=0)
    assert same.distance == pytest.approx(0.0, abs=1e-6)
    louder = aligned_distance(render, render * 4.0, di, render_latency=0, lag=0)
    assert louder.distance == pytest.approx(0.0, abs=1e-3)


def test_a_tone_change_registers_and_grows_with_its_size():
    di = _performance()
    recording = _amp(di)
    distances = [aligned_distance(recording, _shelf(recording, 1000, g), di,
                                  render_latency=0, lag=0).distance for g in (1, 3, 6)]
    assert 0 < distances[0] < distances[1] < distances[2]
    tonal = aligned_distance(recording, _shelf(recording, 1000, 6), di,
                             render_latency=0, lag=0)
    assert tonal.tonal > tonal.temporal          # an EQ move is a long-term change


def test_the_lag_is_found_and_the_timelines_follow_it():
    di = _performance(seed=1)
    render = _amp(di)
    recording = _delay(render, 960)              # the recording 20 ms behind the render
    assert estimate_lag(recording, render) == 960
    found = aligned_distance(recording, render, di, render_latency=0)
    assert found.lag_samples == 960
    assert found.distance == pytest.approx(0.0, abs=1e-3)
    wrong = aligned_distance(recording, render, di, render_latency=0, lag=0)
    assert wrong.distance > found.distance + 0.5


def test_a_window_to_the_end_is_trimmed_to_where_the_render_reaches():
    di = _performance(seed=5)
    render = _amp(di)
    recording = np.concatenate([render[480:], np.zeros(480)])   # the recording 10 ms ahead
    result = aligned_distance(recording, render, di, render_latency=0, lag=-480,
                              start_s=5.0, end_s=10.0)
    assert result.distance == pytest.approx(0.0, abs=1e-3)


def test_an_echo_the_recording_lacks_is_heard_in_the_tails():
    di = _performance(seed=2)
    recording = _amp(di)
    echo = recording + 0.5 * _delay(recording, int(0.42 * SR))
    with_tails = aligned_distance(recording, echo, di, render_latency=0, lag=0)
    no_tails = aligned_distance(recording, echo, di, render_latency=0, lag=0, tail_s=0.0)
    assert with_tails.distance > no_tails.distance > 0


def test_bleed_in_a_band_is_dropped_rather_than_judged():
    di = _performance(seed=3, rest=(4.0, 7.0))
    recording = _amp(di, tone=(200, 3000))
    rng = np.random.default_rng(7)
    b, a = scipy_signal.butter(4, [9000, 14000], btype="bandpass", fs=SR)
    cymbals = scipy_signal.lfilter(b, a, rng.standard_normal(len(recording)))
    cymbals *= 0.5 * np.std(recording) / np.std(cymbals)
    bled = recording + cymbals                    # present whether the DI plays or not
    result = aligned_distance(bled, recording, di, render_latency=0, lag=0)
    assert result.bleed_checked and result.bleed_bands and min(result.bleed_bands) > 6000
    clean = aligned_distance(recording, recording, di, render_latency=0, lag=0)
    assert result.distance < 1.0 and clean.distance == pytest.approx(0.0, abs=1e-6)


def test_the_guitars_own_reverb_is_not_taken_for_bleed():
    di = _performance(seed=6, rest=(4.0, 7.0))
    dry = _amp(di)
    rng = np.random.default_rng(8)
    t = np.arange(int(1.5 * SR)) / SR
    tail = rng.standard_normal(len(t)) * 10 ** (-3 * t / 1.5)   # a 1.5-s RT60 reverb
    wet = scipy_signal.fftconvolve(dry, tail)[: len(dry)]
    room = dry + np.std(dry) / np.std(wet) * wet
    result = aligned_distance(room, dry, di, render_latency=0, lag=0)
    assert result.bleed_checked and not result.bleed_bands
    assert result.distance > 0.5                      # the reverb is judged, not dropped


def test_it_refuses_rather_than_scores_silence():
    di = _performance()
    render = _amp(di)
    quiet = aligned_distance(render, np.zeros_like(render), di, render_latency=0, lag=0)
    assert quiet.distance is None and "loudness" in quiet.reason


def test_the_lag_is_found_across_different_rigs_and_inverted_polarity():
    di = _performance(seed=4)
    render = _amp(di, drive=2.0, tone=(300, 3000))
    recording = -_delay(_amp(di, drive=8.0, tone=(150, 5000)), 480)
    # Different rigs differ in phase by a few samples; what matters is no gross miss.
    assert abs(estimate_lag(recording, render) - 480) <= 48
    other = _amp(di, drive=1.0, tone=(100, 2000))
    assert abs(estimate_lag(recording, [render, other], hint=500, max_lag_s=0.015) - 480) <= 48
