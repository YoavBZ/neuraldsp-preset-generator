"""The model comparison's inputs (`learn/bakeoff_inputs.py`), on small made-up mels."""
import numpy as np
import pytest

from learn import bakeoff_inputs as I

BANDS, FRAMES = 96, 446
CENTRES = np.geomspace(30.0, 16000.0, BANDS)


def norm(db):
    return (np.asarray(db, float) + 60.0) / 30.0


def bursts(every=50):
    """Quiet with a loud broadband click every `every` frames."""
    db = np.full((BANDS, FRAMES), -40.0)
    db[:, ::every] = 0.0
    return norm(db)


def test_dct_is_orthonormal_and_a_constant_lands_on_order_zero():
    c = I.dct(np.ones(16))
    assert c[0] == pytest.approx(4.0) and np.allclose(c[1:], 0.0, atol=1e-12)
    a = np.random.default_rng(0).normal(size=16)
    assert np.dot(I.dct(a), I.dct(a)) == pytest.approx(np.dot(a, a))


@pytest.mark.parametrize("name,size", [("mel", 192), ("ceps-lo", 20), ("ceps-hi", 80), ("onset", 384), ("flat", 18), ("hpss", 192)])
def test_sizes_are_fixed_and_finite(name, size):
    v = I.INPUTS[name](bursts(), CENTRES)
    assert v.shape == (size,) and np.isfinite(v).all()


def test_all_quiet_input_stays_finite():
    x = norm(np.full((BANDS, FRAMES), -60.0))
    for name, f in I.INPUTS.items():
        assert np.isfinite(f(x, CENTRES)).all(), name


def test_ltas_keeps_its_band_range_and_raises_the_floor():
    db = np.full((BANDS, FRAMES), -60.0)
    v = I.ltas(norm(db), CENTRES)
    assert len(v) == ((CENTRES >= 80) & (CENTRES <= 5000)).sum()
    assert np.allclose(v, (-45.0 + 60.0) / 30.0)
    db[(CENTRES < 80) | (CENTRES > 5000)] = 0.0        # outside the range changes nothing
    assert np.allclose(I.ltas(norm(db), CENTRES), v)


def test_onsets_find_the_clicks_and_keep_their_gap():
    got = I.onsets(bursts(50))
    assert got == list(range(50, FRAMES, 50))
    assert min(np.diff(got)) >= I.MIN_ONSET_GAP


def test_attack_mask_covers_sixty_ms():
    m = I.attack_mask(bursts(50))
    assert m[50:56].all() and not m[56] and not m[49]


def test_onset_tells_attacks_from_sustains():
    v = I.onset(bursts(50))
    attack_mean, sustain_mean = v[:96].mean(), v[192:288].mean()
    assert attack_mean > sustain_mean


def test_onset_without_onsets_gives_both_parts_all_frames():
    x = norm(np.full((BANDS, FRAMES), -30.0))
    v = I.onset(x)
    assert np.array_equal(v[:192], v[192:])


def test_flatness_is_zero_on_a_flat_spectrum_and_low_on_a_peak():
    even = I.flat(norm(np.full((BANDS, FRAMES), -20.0)))
    assert abs(even[0]) < 1e-6
    db = np.full((BANDS, FRAMES), -60.0)
    db[40] = 0.0
    assert I.flat(norm(db))[0] < -1.0


def test_hpss_keeps_the_click_more_than_the_tone():
    click = np.full((BANDS, FRAMES), -60.0)
    click[:, 200] = 0.0
    tone = np.full((BANDS, FRAMES), -60.0)
    tone[40] = 0.0
    assert I.hpss(norm(click))[:96].max() > I.hpss(norm(tone))[:96].max()
