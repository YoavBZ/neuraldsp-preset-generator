import pytest
"""The model path (`learn/product_path.py`): the window choice and the amp pick."""

from learn import product_path as PP


def test_the_window_is_where_the_stem_sits_loudest_against_the_mix():
    levels = [(0.0, -30.0, -14.0), (5.0, -20.0, -14.0), (10.0, -18.0, -10.0), (15.0, -20.0, -14.0)]
    assert PP.exposure_window(levels) == 5.0                              # -6 dB beats -8; the earliest of the ties


def test_the_pick_is_the_least_mean_cosine_distance():
    stem = [1.0, 0.0]
    feats = {"pr12": [[0.0, 1.0], [0.1, 1.0]], "sw50r": [[1.0, 0.1], [1.0, 0.0]], "ac20": [[1.0, 1.0], [1.0, 1.0]]}
    amp, dist = PP.pick_amp(stem, feats)
    assert amp == "sw50r" and dist["sw50r"] < dist["ac20"] < dist["pr12"]


def test_the_delay_rule_is_d1s():
    assert PP.delay_rule(0.5, (300.0, 305.0), 302.0, 250.0) == (False, None, None)
    on, ms, which = PP.delay_rule(0.8, (300.0, 305.0), 302.0, 250.0)
    assert on and ms == 302.0 and "peak" in which
    on, ms, which = PP.delay_rule(0.8, (300.0, 150.0), 302.0, 250.0)
    assert on and ms == 250.0 and "neighbours" in which


def test_exposure_window_takes_the_most_exposed_steady_window():
    levels = [(0.0, -20.0, -14.0, True), (5.0, -12.0, -14.0, False), (10.0, -15.0, -14.0, True)]
    assert PP.exposure_window(levels) == 10.0                             # the guard drops the louder, unsteady one
    assert PP.exposure_window([(r[0], r[1], r[2], False) for r in levels]) == 5.0   # none passes: the plain rule


def test_steady_catches_a_fade_and_a_late_entry():
    np = pytest.importorskip("numpy")
    from learn import pretrain_set as PS

    sr, rng = PS.SR, np.random.default_rng(0)
    x = rng.standard_normal(10 * sr) * 0.1
    assert PP.steady(x, sr)[0]
    fade = x * np.concatenate([np.ones(4 * sr), np.full(6 * sr, 0.01)])           # the song ends at 4 s
    late = x * np.concatenate([np.full(3 * sr, 0.01), np.ones(7 * sr)])           # the guitar enters at 3 s
    assert not PP.steady(fade, sr)[0] and not PP.steady(late, sr)[0]
