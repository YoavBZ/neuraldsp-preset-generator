"""The aligned distance: zero for the same audio, blind to level, monotonic in tone
changes, on the DI's own timeline, sensitive to tails and excess fizz, deaf to noise
under the recording's own floor, and refusing input it cannot score."""

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


def _pink(n, rng):
    """Unit-RMS pink noise (-3 dB per octave)."""
    spectrum = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    spectrum[1:] /= np.sqrt(f[1:])
    spectrum[0] = 0.0
    x = np.fft.irfft(spectrum, n)
    return x / np.std(x)


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
    lag = estimate_lag(recording, render)
    assert lag == 960
    found = aligned_distance(recording, render, di, render_latency=0, lag=lag)
    assert found.lag_samples == 960
    assert found.distance == pytest.approx(0.0, abs=1e-3)
    wrong = aligned_distance(recording, render, di, render_latency=0, lag=0)
    assert wrong.distance > found.distance + 0.5


def test_an_echo_the_recording_lacks_is_heard_in_the_tails():
    di = _performance(seed=2)
    recording = _amp(di)
    echo = recording + 0.5 * _delay(recording, int(0.42 * SR))
    with_tails = aligned_distance(recording, echo, di, render_latency=0, lag=0)
    no_tails = aligned_distance(recording, echo, di, render_latency=0, lag=0, tail_s=0.0)
    assert with_tails.distance > no_tails.distance > 0


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


def test_the_di_timeline_follows_the_lag_and_the_latency():
    """A burst in the recording while the DI rests is not judged, wherever the
    lag and the plugin's latency put that rest."""
    latency, lag = SR // 2, int(0.8 * SR)
    di = _performance(seed=9, rest=(4.0, 7.5))
    render = _delay(_amp(di), latency)
    rng = np.random.default_rng(3)
    burst = np.zeros(len(di))
    burst[int(6.5 * SR): int(8.5 * SR)] = rng.standard_normal(2 * SR)
    recording = _delay(render, lag) + 0.5 * np.std(render) * burst
    kwargs = dict(lag=lag, start_s=1.0, tail_s=0.2)
    right = aligned_distance(recording, render, di, render_latency=latency, **kwargs)
    assert right.distance == pytest.approx(0.0, abs=0.05)
    for wrong in (0, -latency):
        assert aligned_distance(recording, render, di, render_latency=wrong,
                                **kwargs).distance > 0.3


def test_a_level_offset_from_content_outside_the_bands_is_removed():
    di = _performance(seed=10)
    recording = _amp(di)
    t = np.arange(len(di)) / SR
    hiss_above = recording + 3 * np.std(recording) * np.sin(2 * np.pi * 18000 * t)
    result = aligned_distance(recording, hiss_above, di, render_latency=0, lag=0)
    assert result.offset_db < -1.0 and result.distance < 0.1


def test_a_hint_reaches_a_lag_the_default_window_cannot():
    di = _performance(seed=11)
    render = _amp(di)
    recording = _delay(render, 3000)                      # 62.5 ms
    assert estimate_lag(recording, render, hint=2900, max_lag_s=0.015) == 3000
    with pytest.raises(ValueError, match="outside"):
        estimate_lag(recording, render)                   # ±50 ms around 0
    with pytest.raises(ValueError, match="outside"):
        estimate_lag(recording, render, hint=2900, max_lag_s=0.0015)


def test_a_stereo_render_is_one_render():
    di = _performance(seed=12)
    render = _amp(di)
    recording = _delay(render, 480)
    assert estimate_lag(recording, np.stack([render, render], axis=1)) == 480


def test_bad_input_is_refused_rather_than_scored():
    di = _performance(seed=13)
    render = _amp(di)
    broken = render.copy()
    broken[1000] = np.nan
    with pytest.raises(ValueError, match="finite"):
        aligned_distance(render, broken, di, render_latency=0, lag=0)
    with pytest.raises(ValueError, match="finite"):
        estimate_lag(render, [render, broken])
    silent_di = aligned_distance(render, render, np.zeros_like(di), render_latency=0, lag=0)
    assert silent_di.distance is None and "DI" in silent_di.reason


def test_a_note_just_before_the_window_still_has_its_tail_judged():
    di = _performance(seed=14, rest=(2.0, 6.0))
    dry = _amp(di)
    last = np.flatnonzero(np.abs(di[: 6 * SR]) > 0)[-1] / SR
    start = last + 0.05                                   # the window opens in the note's tail
    ring = np.zeros(len(di))
    span = slice(int(start * SR), int(start * SR) + SR)
    ring[span] = np.random.default_rng(4).standard_normal(SR) * np.exp(-np.arange(SR) / (0.3 * SR))
    tail = dry + np.std(dry) * ring                       # a tail the recording lacks
    result = aligned_distance(dry, tail, di, render_latency=0, lag=0, start_s=start)
    assert result.distance > 0.3


def test_noise_the_guitar_masks_does_not_bring_a_render_closer():
    """Over the frames where the guitar plays, noise far under it is clamped away;
    in pauses the recording's own hiss is audible, so matching it still counts."""
    di = _performance(seed=15)
    rng = np.random.default_rng(5)
    recording = _amp(di, drive=6.0)
    recording = recording + 10 ** (-35 / 20) * np.std(recording) * _pink(len(di), rng)
    render = _amp(di)
    noisy = render + 10 ** (-40 / 20) * np.std(render) * _pink(len(di), rng)
    clean = aligned_distance(recording, render, di, render_latency=0, lag=0, tail_s=0.0)
    added = aligned_distance(recording, noisy, di, render_latency=0, lag=0, tail_s=0.0)
    assert added.distance >= clean.distance - 0.1


def test_fizz_the_recording_lacks_is_seen():
    di = _performance(seed=16)
    b, a = scipy_signal.butter(8, 4000, btype="low", fs=SR)
    recording = scipy_signal.lfilter(b, a, _amp(di))
    b, a = scipy_signal.butter(4, [8000, 12000], btype="bandpass", fs=SR)
    fizz = scipy_signal.lfilter(b, a, np.tanh(20 * di))
    fizzy = recording + 0.25 * np.std(recording) / np.std(fizz) * fizz
    assert aligned_distance(recording, fizzy, di, render_latency=0, lag=0).distance > 1.0
