"""The judge battery's pure functions (`learn/bakeoff_judge.py`)."""
import math

import pytest

np = pytest.importorskip("numpy")

from learn import bakeoff_judge as J


def frames(D):
    blocks = np.arange(len(D))
    return [(np.asarray(D, float), blocks)]


def test_terms_on_a_steady_error_agree():
    D = np.tile([[2.0, -2.0]], (10, 1))
    got = J.terms_of(frames(D))
    assert got == {"distance": 2.0, "tonal": 2.0, "cross": pytest.approx(2.0)}


def test_cross_has_no_floor_on_noise_where_distance_does():
    rng = np.random.default_rng(0)
    D = rng.normal(0, 5.0, size=(4000, 40))
    got = J.terms_of(frames(D - D.mean()))
    assert got["distance"] > 3.5 and abs(got["cross"]) < 0.3


def test_cross_keeps_a_small_steady_error_under_noise():
    rng = np.random.default_rng(1)
    err = np.where(np.arange(40) % 2 == 0, 1.0, -1.0)
    D = rng.normal(0, 5.0, size=(4000, 40)) + err
    clean = J.terms_of(frames(D - err))
    dirty = J.terms_of(frames(D))
    assert dirty["cross"] == pytest.approx(1.0, abs=0.15)
    assert (dirty["distance"] - clean["distance"]) < 0.15


def test_spearman_and_gamma_on_ties():
    assert J.spearman([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(1.0)
    assert J.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert J.gamma([1, 2, 3], [0, 0, 1]) == 1.0
    assert J.gamma([3, 2, 1], [0, 0, 1]) == -1.0


def test_flip_counts_only_the_ears_strict_orders():
    a, r, d = J.FLIP_ANCHOR, J.FLIP_EFFECTS[0], J.FLIP_EFFECTS[1]
    ear = {"one": {a: 1, r: 2, d: 2}, "two": {a: 2, r: 1, d: 2}}
    term = {"one": {a: 1.0, r: 2.0, d: 0.5}, "two": {a: 1.0, r: 2.0, d: 3.0}}
    assert J.flip_orders(term, ear) == (1, 3)


def test_tone_in_top_three_and_drive_order():
    groups = {"a": "tone", "b": "tone", "c": "drive", "d": "drive", "e": "drive"}
    assert J.tone_in_top_three({"a": 5, "b": 4, "c": 3, "d": 2, "e": 1}, groups) == 2
    assert J.drive_order({"c": 3.0, "d": 1.0, "e": 2.0}, {"c": 2, "d": 0, "e": 0}, groups) == 1.0


def test_gain_curves_peak_where_they_should():
    f = np.array([100.0, 1600.0, 16000.0])
    assert J.bell_gain(1600.0, 6.0)(f).tolist() == pytest.approx([0.0, 6.0, 0.0])
    assert J.shelf_gain(4000.0, 6.0)(f).tolist() == pytest.approx([0.0, 0.0, 6.0])


def test_fft_shape_with_no_gain_is_identity():
    x = np.random.default_rng(2).normal(size=1024)
    assert np.allclose(J.fft_shape(x, lambda f: 0 * f), x)
    assert math.isclose(J.spread([{"A": 1.0, "B": 0.0}, {"A": 0.0, "B": 0.0}]), np.std([1.0, 0.0], ddof=1) / math.sqrt(2))
