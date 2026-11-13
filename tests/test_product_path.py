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
