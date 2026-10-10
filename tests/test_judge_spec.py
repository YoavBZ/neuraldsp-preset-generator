"""The judge's specification (`docs/judge-spec.md`), checked on synthetic signals.

One test per property, run for each judge in `JUDGES`. A property a judge is known to
violate is marked `xfail(strict=True)` with the reason, so a fix that makes it hold
fails the run until the mark is removed: the change is visible either way.

The synthetic rigs are shaped like the set-3 development recordings, octave by
octave (80 Hz–10 kHz, relative to the loudest octave): `crunch` like a typical driven
part (0, −2, −6, −7, −7, −9, −17 dB), `bass` like Ill Fate (0, −16, −26, −28, −29,
−30, −39), `clean` like a dark clean part (5–10 kHz at −73), `bright` with an open top.
"""

from __future__ import annotations

import functools

import pytest

np = pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("pyloudnorm", reason="needs the analysis extra")
sps = pytest.importorskip("scipy.signal", reason="needs the analysis extra")
stats = pytest.importorskip("scipy.stats", reason="needs the analysis extra")

from analysis import aligned as A  # noqa: E402
from analysis.aligned import aligned_distance, estimate_lag  # noqa: E402

SR = 48000

# Judge name -> keyword options for `aligned_distance`.
JUDGES = {"default": {}, "v2": {"bands": "fixed"}}
_V2_FLOOR = ("v2 keeps the default's floor, from the recording alone, under a fixed band set "
             "with unnormalised mel bands")

# (judge, property) -> why the judge violates it.
KNOWN = {
    ("default", "plus_minus"):
        "the per-frame floor comes from the recording alone, so a cut into it is clamped "
        "while the same boost counts in full; mel bands are not area-normalised",
    ("default", "fizz"):
        "the scored bands come from the recording's own spectrum: on dark or bass-heavy "
        "recordings the treble where fizz lives is not scored",
    ("default", "bass_heavy_treble"):
        "band choice and floor are 30/40 dB under the recording's loudest band, so a "
        "dominant low end drops the treble from scoring (Ill Fate)",
    ("default", "swap"):
        "bands and floor come from the recording only, so excess the recording lacks is "
        "judged differently from the same content missing",
    ("default", "band_width"):
        "mel filters are not area-normalised: a wide treble band reads up to 13 dB louder "
        "than a narrow low one of the same density, which moves floors and band choice",
    ("v2", "plus_minus"): _V2_FLOOR,
    ("v2", "band_width"): _V2_FLOOR,
}


def judges(prop):
    return [pytest.param(j, marks=pytest.mark.xfail(strict=True, reason=KNOWN[(j, prop)]))
            if (j, prop) in KNOWN else j for j in JUDGES]


def judged(judge, recording, render, di, **kw):
    kw = {"render_latency": 0, "lag": 0, **JUDGES[judge], **kw}
    return aligned_distance(recording, render, di, **kw)


def dist(judge, recording, render, di, **kw):
    d = judged(judge, recording, render, di, **kw).distance
    assert d is not None
    return d


# Signals --------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def performance(seed=5, seconds=10.0):
    """A DI-like part: decaying harmonic notes with short gaps."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    di = np.zeros_like(t)
    start = 0.3
    while start < seconds - 0.5:
        length = rng.uniform(0.25, 0.6)
        f0 = rng.choice([82.4, 110.0, 146.8, 196.0, 246.9, 329.6])
        idx = (t >= start) & (t < start + length)
        tt = t[idx] - start
        note = sum(np.sin(2 * np.pi * f0 * k * tt) / k for k in range(1, 12))
        di[idx] += 0.2 * note * np.exp(-tt * 4)
        start += length + rng.uniform(0.05, 0.4)
    di.flags.writeable = False
    return di


def fgain(x, fn):
    """`x` through a zero-phase filter whose gain in dB is `fn(frequency)`."""
    n = len(x)
    size = 1 << int(np.ceil(np.log2(n)))
    f = np.fft.rfftfreq(size, 1 / SR)
    return np.fft.irfft(np.fft.rfft(x, size) * 10 ** (fn(f) / 20), size)[:n]


def bell(fc, gain_db):
    """A one-octave-wide (at ±1 standard deviation) bell of `gain_db` at `fc`."""
    return lambda f: gain_db * np.exp(-0.5 * (np.log2(np.maximum(f, 1) / fc) / 0.5) ** 2)


def shelf(fc, gain_db):
    return lambda f: gain_db / (1 + np.exp(-6 * np.log2(np.maximum(f, 1) / fc)))


def tilt(db_per_octave):
    return lambda f: db_per_octave * np.clip(np.log2(np.maximum(f, 20) / 1000), -6, 4)


def _cab(lo, hi, presence):
    def fn(f):
        f = np.maximum(f, 1.0)
        g = -12 * np.log2(np.maximum(lo / f, 1)) - 30 * np.log2(np.maximum(f / hi, 1))
        return g + presence * np.clip(np.log2(f / 500), 0, np.log2(hi / 500))
    return fn


def rig(kind="crunch", drive=16.0, seed=5, seconds=10.0):
    return _rig(kind, float(drive), seed, seconds).copy()


@functools.lru_cache(maxsize=None)
def _rig(kind, drive, seed, seconds):
    di = performance(seed, seconds)
    if kind == "clean":
        return fgain(np.tanh(drive / 10 * di), _cab(150, 3000, 0))
    y = np.tanh(drive * di)
    if kind == "crunch":
        return fgain(y, _cab(90, 5500, 4))
    if kind == "bright":
        return fgain(y, _cab(110, 8000, 5))
    if kind == "bass":
        return fgain(y, lambda f: _cab(70, 5500, 4)(f) + 20 / (1 + (np.maximum(f, 1) / 180) ** 4))
    raise ValueError(kind)


def rms(x):
    return float(np.sqrt(np.mean(x ** 2)))


def delay(x, samples):
    return np.concatenate([np.zeros(samples), x])[: len(x)]


def fizz(reference, db, seed=5):
    """Band-passed (5–12 kHz) hard clipping of the DI, `db` under `reference`'s RMS."""
    b, a = sps.butter(4, [5000, 12000], btype="bandpass", fs=SR)
    z = sps.lfilter(b, a, np.tanh(30 * performance(seed, len(reference) / SR)))
    return z * rms(reference) / rms(z) * 10 ** (db / 20)


def reverb(x, wet_db, t60=1.2):
    rng = np.random.default_rng(1)
    t = np.arange(int(t60 * SR)) / SR
    wet = sps.fftconvolve(x, rng.standard_normal(len(t)) * 10 ** (-3 * t / t60))[: len(x)]
    return x + wet * rms(x) / rms(wet) * 10 ** (wet_db / 20)


def ratio(a, b):
    assert a > 0 and b > 0, (a, b)
    return max(a, b) / min(a, b)


# 1. Identity ----------------------------------------------------------------------

@pytest.mark.parametrize("judge", judges("identity"))
def test_identical_audio_is_at_zero(judge):
    di = performance()
    for kind in ("crunch", "clean", "bass"):
        x = rig(kind)
        assert dist(judge, x, x, di) == pytest.approx(0.0, abs=1e-6)


# 2. Level -------------------------------------------------------------------------

@pytest.mark.parametrize("judge", judges("level"))
def test_level_does_not_count(judge):
    di = performance()
    recording = rig("crunch")
    for g in (0.1, 3.0):
        assert dist(judge, recording, g * recording, di) == pytest.approx(0.0, abs=1e-3)
    render = fgain(recording, bell(1000, 4))
    base = dist(judge, recording, render, di)
    for g in (0.1, 3.0):
        assert dist(judge, recording, g * render, di) == pytest.approx(base, abs=1e-3)
        assert dist(judge, g * recording, render, di) == pytest.approx(base, abs=1e-3)


# 3. Time alignment ----------------------------------------------------------------

@pytest.mark.parametrize("judge", judges("alignment"))
def test_time_alignment_is_found_and_followed(judge):
    di = performance(seed=7)
    latency = 52
    render = delay(rig("crunch", seed=7), latency)          # the plugin's latency
    recording = delay(render, 960)                           # the recording 20 ms behind
    assert estimate_lag(recording, render) == 960
    other = -delay(rig("bright", drive=6, seed=7), latency)  # another rig, inverted
    assert abs(estimate_lag(-recording, [render, other]) - 960) <= 48
    kw = dict(lag=960, render_latency=latency)
    assert dist(judge, recording, render, di, **kw) == pytest.approx(0.0, abs=1e-3)
    assert dist(judge, recording, render, di, lag=960 - 144, render_latency=latency) > 0.3


# 4. EQ: monotone and sensibly scaled ----------------------------------------------

@pytest.mark.parametrize("judge", judges("eq_monotone"))
def test_an_eq_change_costs_more_as_it_grows(judge):
    di = performance()
    recording = rig("crunch")
    sixes = []
    for fc in (200, 800, 2500, 6000):
        for sign in (1, -1):
            c = [dist(judge, recording, fgain(recording, bell(fc, sign * g)), di)
                 for g in (1, 3, 6)]
            assert 0.02 < c[0] < c[1] < c[2], (fc, sign, c)
            assert 1.6 <= c[2] / c[1] <= 2.4, (fc, sign, c)   # roughly linear in dB
            sixes.append(c[2])
    # No octave where the guitar sounds is close to free.
    assert max(sixes) / min(sixes) <= 3.5, sixes


@pytest.mark.parametrize("judge", judges("tilt"))
def test_a_tilt_costs_more_as_it_grows_either_way(judge):
    di = performance()
    for kind in ("crunch", "bass"):
        recording = rig(kind)
        up = [dist(judge, recording, fgain(recording, tilt(g)), di) for g in (0.5, 1, 2)]
        down = [dist(judge, recording, fgain(recording, tilt(-g)), di) for g in (0.5, 1, 2)]
        assert 0 < up[0] < up[1] < up[2] and 0 < down[0] < down[1] < down[2]
        assert all(ratio(u, d) <= 1.2 for u, d in zip(up, down)), (kind, up, down)


# 5. Boosts and cuts alike ---------------------------------------------------------

def _white_with_region(lo_band, hi_band, level_db, change_db, seed=0):
    """Noise of flat density (80 Hz–11 kHz) that follows the DI's envelope, with mel
    bands `lo_band`..`hi_band` at `level_db`, then changed by `change_db`."""
    di = performance()
    env = np.sqrt(np.clip(sps.filtfilt(*sps.butter(2, 20, fs=SR), di ** 2), 0, None))
    white = np.random.default_rng(seed).standard_normal(len(di))
    mel = lambda f: 2595.0 * np.log10(1.0 + f / 700.0)          # noqa: E731
    edges = 700.0 * (10 ** (np.linspace(mel(A.FMIN), mel(A.FMAX), A.MEL_BANDS + 2) / 2595) - 1)
    lo, hi = edges[lo_band + 1], edges[hi_band + 1]

    def shape(f):
        inside = (f >= lo) & (f <= hi)
        out = np.where((f < 80) | (f > 11000), -80.0, 0.0)
        return out + np.where(inside, level_db + change_db, 0.0)
    return fgain(white, shape) * env


@pytest.mark.parametrize("judge", judges("plus_minus"))
def test_a_boost_and_the_same_cut_cost_alike(judge):
    di = performance()
    for kind in ("crunch", "bright"):
        recording = rig(kind)
        for fc in (400, 1000, 2500, 6000):
            up = dist(judge, recording, fgain(recording, bell(fc, 6)), di)
            down = dist(judge, recording, fgain(recording, bell(fc, -6)), di)
            assert ratio(up, down) <= 1.2, (kind, fc, up, down)
    for kind in ("crunch", "bright", "bass"):
        recording = rig(kind)
        for fc in (2000, 4000, 6000):
            up = dist(judge, recording, fgain(recording, shelf(fc, 12)), di)
            down = dist(judge, recording, fgain(recording, shelf(fc, -12)), di)
            assert ratio(up, down) <= 1.2, (kind, fc, up, down)
    # A quieter region of an even spectrum (20 dB down), raised or lowered 12 dB.
    for bands in ((8, 12), (48, 52)):
        recording = _white_with_region(*bands, -20, 0)
        up = dist(judge, recording, _white_with_region(*bands, -20, 12), di)
        down = dist(judge, recording, _white_with_region(*bands, -20, -12), di)
        assert ratio(up, down) <= 1.2, (bands, up, down)


# 6. Drive -------------------------------------------------------------------------

@pytest.mark.parametrize("judge", judges("drive"))
def test_more_drive_costs_more(judge):
    di = performance()
    for kind in ("crunch", "bass"):
        recording = rig(kind, drive=8)
        c = [dist(judge, recording, rig(kind, drive=8 * m), di) for m in (1.5, 2, 4)]
        assert 0.1 < c[0] < c[1] < c[2], (kind, c)


# 7. Fizz and noise above the recording --------------------------------------------

@pytest.mark.parametrize("judge", judges("fizz"))
def test_fizz_above_the_recording_costs_more_as_it_grows(judge):
    di = performance()
    for kind in ("crunch", "clean", "bass"):
        recording = rig(kind)
        c = [dist(judge, recording, recording + fizz(recording, db), di)
             for db in (-40, -30, -20, -10)]
        assert c[0] <= c[1] < c[2] < c[3], (kind, c)
        unit = dist(judge, recording, fgain(recording, bell(800, 3)), di)
        assert c[3] >= unit, (kind, c, unit)                 # fizz at −10 dB is plain
        if kind != "crunch":                                 # on a dark top, so is −20
            assert c[2] >= unit, (kind, c, unit)


# 8. Reverb and echo ---------------------------------------------------------------

@pytest.mark.parametrize("judge", judges("time_effects"))
def test_reverb_and_echo_cost_more_as_they_grow(judge):
    di = performance()
    for kind in ("crunch", "clean"):
        recording = rig(kind)
        c = [dist(judge, recording, reverb(recording, db), di) for db in (-30, -20, -10)]
        assert 0.1 < c[0] < c[1] < c[2], (kind, c)
        echo = [dist(judge, recording, recording + g * delay(recording, int(0.42 * SR)), di)
                for g in (0.25, 0.5)]
        assert 0.5 < echo[0] < echo[1], (kind, echo)


# 9. Small time shift --------------------------------------------------------------

@pytest.mark.parametrize("judge", judges("shift"))
def test_a_small_time_shift_costs_more_as_it_grows(judge):
    di = performance()
    recording = rig("crunch")
    c = [dist(judge, recording, delay(recording, int(ms * SR / 1000)), di) for ms in (1, 3, 10)]
    assert 0.05 < c[0] < c[1] < c[2], c


# 10. Treble on bass-heavy recordings ----------------------------------------------

@pytest.mark.parametrize("judge", judges("bass_heavy_treble"))
def test_treble_is_heard_on_a_bass_heavy_recording(judge):
    """A treble change costs on a bass-heavy recording at least half what it costs on
    a balanced one: the bass does not mask 2.5–10 kHz."""
    di = performance()
    heavy, balanced = rig("bass"), rig("crunch")
    changes = {"bell +6 at 2.5k": lambda x: fgain(x, bell(2500, 6)),
               "bell +6 at 6k": lambda x: fgain(x, bell(6000, 6)),
               "shelf -12 over 5k": lambda x: fgain(x, shelf(5000, -12)),
               "shelf +12 over 5k": lambda x: fgain(x, shelf(5000, 12))}
    for name, change in changes.items():
        on_heavy = dist(judge, heavy, change(heavy), di)
        on_balanced = dist(judge, balanced, change(balanced), di)
        assert on_heavy >= 0.5 * on_balanced, (name, on_heavy, on_balanced)


# 11. Missing and excess alike -----------------------------------------------------

@pytest.mark.parametrize("judge", judges("swap"))
def test_missing_content_costs_what_the_same_excess_costs(judge):
    """Swapping recording and render changes the distance by at most 10%: a render
    lacking what the recording has costs what one with the same thing extra costs."""
    di = performance()
    crunch, bass, clean = rig("crunch"), rig("bass"), rig("clean")
    pairs = {"fizz": (crunch, crunch + fizz(crunch, -20)),
             "bright shelf on bass": (bass, fgain(bass, shelf(4000, 12))),
             "fizz on clean": (clean, clean + fizz(clean, -25)),
             "drive": (crunch, rig("crunch", drive=32)),
             "reverb": (clean, reverb(clean, -15))}
    for name, (a, b) in pairs.items():
        assert ratio(dist(judge, a, b, di), dist(judge, b, a, di)) <= 1.1, name


# 12. Band width -------------------------------------------------------------------

@pytest.mark.parametrize("judge", judges("band_width"))
def test_the_same_change_costs_the_same_in_a_narrow_or_a_wide_band(judge):
    """On an even spectrum, the same change to a region of equal mel width and equal
    density costs the same low (narrow mel bands) as high (wide ones)."""
    di = performance()
    for level, change in ((-20, -12), (-20, 12), (0, -6)):
        cost = []
        for bands in ((8, 12), (48, 52)):
            recording = _white_with_region(*bands, level, 0)
            cost.append(dist(judge, recording, _white_with_region(*bands, level, change), di))
        assert ratio(*cost) <= 1.25, (level, change, cost)


# 13. Ranking across halves --------------------------------------------------------

@pytest.mark.parametrize("judge", judges("halves"))
def test_the_ranking_holds_across_halves(judge):
    di = performance(seed=8, seconds=20.0)
    recording = rig("crunch", seed=8, seconds=20.0)
    candidates = [fgain(recording, bell(800, 2)), fgain(recording, bell(2500, -5)),
                  fgain(recording, tilt(1)), fgain(recording, tilt(-2.5)),
                  rig("crunch", drive=24, seed=8, seconds=20.0),
                  rig("crunch", drive=64, seed=8, seconds=20.0),
                  rig("bright", seed=8, seconds=20.0), rig("bass", seed=8, seconds=20.0),
                  reverb(recording, -18), recording + fizz(recording, -15, seed=8)]
    first = [dist(judge, recording, c, di, start_s=1.0, end_s=10.0) for c in candidates]
    second = [dist(judge, recording, c, di, start_s=10.0, end_s=19.0) for c in candidates]
    assert stats.spearmanr(first, second).statistic >= 0.9, (first, second)
    assert int(np.argmin(first)) == int(np.argmin(second))


# 14. Refusals ---------------------------------------------------------------------

@pytest.mark.parametrize("judge", judges("refusal"))
def test_what_cannot_be_judged_is_refused_not_scored(judge):
    di = performance()
    x = rig("crunch")
    assert "DI" in judged(judge, x, x, np.zeros_like(di)).reason
    assert "loudness" in judged(judge, x, np.zeros_like(x), di).reason
    assert "second" in judged(judge, x, x, di, start_s=9.5).reason
    rested = di.copy()
    rested[int(2 * SR): int(9 * SR)] = 0.0                  # mostly tails
    assert "pauses" in judged(judge, x, x, rested, start_s=1.0, end_s=9.0).reason
    inaudible = 10 ** (-90 / 20) * x
    inaudible[int(3.2 * SR): int(4.3 * SR)] = 0.1 * np.random.default_rng(1).standard_normal(
        int(1.1 * SR))
    gap = di.copy()
    gap[int(3.0 * SR): int(4.5 * SR)] = 0.0
    refused = judged(judge, inaudible, x, gap)
    assert refused.distance is None and "inaudible" in refused.reason
    broken = x.copy()
    broken[100] = np.nan
    with pytest.raises(ValueError, match="finite"):
        judged(judge, x, broken, di)
    with pytest.raises(ValueError, match="channels-first"):
        judged(judge, x, np.stack([x, x]), di)


# 15. Masking ----------------------------------------------------------------------

@pytest.mark.parametrize("judge", judges("masked_noise"))
def test_noise_far_under_the_guitar_does_not_bring_a_render_closer(judge):
    """The validated design: noise well under the guitar, where it plays, is not
    rewarded for imitating the recording's own hiss."""
    di = performance(seed=15)
    rng = np.random.default_rng(5)

    def pink(n):
        spectrum = np.fft.rfft(rng.standard_normal(n))
        f = np.fft.rfftfreq(n, 1.0 / SR)
        spectrum[1:] /= np.sqrt(f[1:])
        spectrum[0] = 0.0
        p = np.fft.irfft(spectrum, n)
        return p / np.std(p)

    recording = rig("crunch", seed=15, drive=24)
    recording = recording + 10 ** (-35 / 20) * np.std(recording) * pink(len(di))
    render = rig("crunch", seed=15)
    noisy = render + 10 ** (-40 / 20) * np.std(render) * pink(len(di))
    clean = dist(judge, recording, render, di, tail_s=0.0)
    assert dist(judge, recording, noisy, di, tail_s=0.0) >= clean - 0.1
