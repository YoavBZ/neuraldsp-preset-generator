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
    kwargs = dict(lag=lag, start_s=1.0, tail_s=0.2, max_pauses=0.8)   # a long rest
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
    result = aligned_distance(dry, tail, di, render_latency=0, lag=0, start_s=start,
                              max_pauses=0.8)
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


def test_too_much_top_end_registers_and_the_bands_are_the_recordings():
    di = _performance(seed=16)
    bright = _amp(di, drive=8.0, tone=(200, 16000))
    b, a = scipy_signal.butter(4, [8000, 12000], btype="bandpass", fs=SR)
    fizz = scipy_signal.lfilter(b, a, np.tanh(20 * di))
    recording = bright + 0.3 * np.std(bright) / np.std(fizz) * fizz
    hotter = bright + 0.6 * np.std(bright) / np.std(fizz) * fizz     # +6 dB of fizz
    darker = _shelf(recording, 3000, -6)
    a_ = aligned_distance(recording, hotter, di, render_latency=0, lag=0)
    b_ = aligned_distance(recording, darker, di, render_latency=0, lag=0)
    assert a_.distance > 0.5
    assert a_.bands == b_.bands                     # one band set per recording


def test_a_quiet_passage_is_judged_against_its_own_frames():
    """The floor follows each frame: an EQ change in a passage 35 dB down still
    counts, where one floor for the whole window would clamp most of it away."""
    di = _performance(seed=18)
    gain = np.ones(len(di))
    gain[len(di) // 2:] = 10 ** (-35 / 20)
    recording = _amp(di) * gain
    render = recording.copy()
    render[len(di) // 2:] = _shelf(recording, 1000, 6)[len(di) // 2:]
    assert aligned_distance(recording, render, di, render_latency=0, lag=0,
                            start_s=1.0).distance > 0.75


def test_an_echo_late_in_a_rest_needs_the_whole_tail():
    di = _performance(seed=17, rest=(4.0, 6.2))
    dry = _amp(di)
    before_rest = dry.copy()
    before_rest[: 3 * SR] = 0.0
    before_rest[int(4.7 * SR):] = 0.0
    echo = dry + 0.7 * _delay(before_rest, int(1.3 * SR))
    result = aligned_distance(dry, echo, di, render_latency=0, lag=0)
    assert result.distance > 4.0 and result.temporal > result.tonal


def test_a_lag_longer_than_the_start_trims_the_window():
    di = _performance(seed=19)
    render = _amp(di)
    recording = _delay(render, int(1.5 * SR))
    result = aligned_distance(recording, render, di, render_latency=0, lag=int(1.5 * SR))
    assert result.distance == pytest.approx(0.0, abs=1e-3) and result.frames > 0


def test_windows_it_cannot_judge_are_refused():
    di = _performance(seed=20, rest=(3.0, 4.5))
    render = _amp(di)
    inaudible = 10 ** (-90 / 20) * render                # the guitar 90 dB down...
    inaudible[int(3.2 * SR): int(4.3 * SR)] = 0.1 * np.random.default_rng(1).standard_normal(
        int(1.1 * SR))                                     # ...under loud content in the rest
    quiet = aligned_distance(inaudible, render, di, render_latency=0, lag=0)
    assert quiet.distance is None and "inaudible" in quiet.reason
    sparse = aligned_distance(render, render, di, render_latency=0, lag=0, start_s=2.6,
                              end_s=5.0)
    assert sparse.distance is None and "pauses" in sparse.reason
    with pytest.raises(ValueError, match="channels-first"):
        aligned_distance(render, np.stack([render, render]), di, render_latency=0, lag=0)


def test_a_silent_lead_in_is_not_a_pause():
    di = _performance(seed=21)
    di[: 4 * SR] = 0.0                                    # nothing for the first 4 s
    render = _amp(di)
    result = aligned_distance(render, render, di, render_latency=0, lag=0, start_s=1.0)
    assert result.distance == pytest.approx(0.0, abs=1e-6)


def test_each_render_counts_once_in_the_pooled_lag():
    """A loud render of another performance must not outvote a quiet one of this."""
    di, other = _performance(seed=22), _performance(seed=23)
    render = _amp(di)
    recording = _delay(render, 480)
    assert estimate_lag(recording, [0.001 * render, 1000.0 * _amp(other)]) == 480


def test_hum_below_the_band_does_not_set_the_lag():
    di = _performance(seed=24)
    render = _amp(di)
    t = np.arange(len(di)) / SR
    hum = 20 * np.std(render) * np.sin(2 * np.pi * 50 * t)
    recording = _delay(render, 480) + hum                 # the hum is not delayed
    assert estimate_lag(recording, render + hum) == 480


def test_a_channels_first_render_is_refused_by_the_lag_too():
    di = _performance(seed=25)
    render = _amp(di)
    with pytest.raises(ValueError, match="channels-first"):
        estimate_lag(render, np.stack([render, render]))


def test_the_union_band_set_sees_treble_the_recording_lacks():
    di = _performance(seed=26)
    b, a = scipy_signal.butter(8, 4000, btype="low", fs=SR)
    recording = scipy_signal.lfilter(b, a, _amp(di))
    b, a = scipy_signal.butter(4, [8000, 12000], btype="bandpass", fs=SR)
    fizz = scipy_signal.lfilter(b, a, np.tanh(20 * di))
    fizzy = recording + 0.25 * np.std(recording) / np.std(fizz) * fizz
    union = aligned_distance(recording, fizzy, di, render_latency=0, lag=0, bands="union")
    own = aligned_distance(recording, fizzy, di, render_latency=0, lag=0)
    assert union.distance > 1.0 and own.distance < 0.5 and union.bands > own.bands
    with pytest.raises(ValueError, match="bands"):
        aligned_distance(recording, fizzy, di, render_latency=0, lag=0, bands="both")



def test_hearing_weighting_keeps_zero_level_blindness_and_the_flat_default():
    di = _performance()
    render = _amp(di)
    kw = dict(render_latency=0, lag=0, weighting="hearing")
    assert aligned_distance(render, render, di, **kw).distance == pytest.approx(0.0, abs=1e-6)
    assert aligned_distance(render, render * 4.0, di, **kw).distance == pytest.approx(0.0, abs=1e-3)
    flat = aligned_distance(render, _shelf(render, 2000, 6), di, render_latency=0, lag=0)
    default = aligned_distance(render, _shelf(render, 2000, 6), di, render_latency=0, lag=0,
                               weighting="flat")
    assert flat.distance == default.distance


def test_hearing_weighting_hears_treble_a_bass_heavy_recording_buries():
    """A recording with a dominant low end: flat weighting scores only the bass and is
    blind to a treble boost; hearing weighting scores more bands and hears it."""
    di = _performance(seed=3)
    rig = _amp(di, tone=(60, 6000))
    b, a = scipy_signal.butter(2, 150, btype="lowpass", fs=SR)
    recording = rig + 10 * scipy_signal.lfilter(b, a, rig)
    bright = _shelf(recording, 4000, 12)
    kw = dict(render_latency=0, lag=0)
    flat = aligned_distance(recording, bright, di, **kw)
    hearing = aligned_distance(recording, bright, di, weighting="hearing", **kw)
    assert hearing.bands > flat.bands
    assert hearing.distance > flat.distance


def test_hearing_weighting_refuses_a_window_scored_on_too_few_bands():
    di = _performance()
    render = _amp(di)
    d = aligned_distance(render, render, di, render_latency=0, lag=0, weighting="hearing",
                         min_bands=200)
    assert d.distance is None and "bands are scored" in d.reason
    with pytest.raises(ValueError):
        aligned_distance(render, render, di, render_latency=0, lag=0, weighting="loud")
