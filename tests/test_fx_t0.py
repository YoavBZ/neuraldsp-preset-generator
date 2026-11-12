"""T0 (`learn/fx_t0.py`): the fixed features on synthetic playing (an echo, a tremolo, a reverb), the leave-one-song-out
neighbours and the rule."""

import math

import pytest

np = pytest.importorskip("numpy")
from learn import fx_t0 as T  # noqa: E402


def _playing(seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(int(10 * T.SR)) / T.SR
    y, s = np.zeros_like(t), 0.0
    while s < 9.5:
        i = int(s * T.SR)
        n = np.arange(len(t) - i) / T.SR
        y[i:] += np.sin(2 * np.pi * (150 * 2 ** (rng.integers(0, 12) / 12)) * n) * np.exp(-n * rng.uniform(3, 10))
        s += rng.uniform(0.15, 0.9)
    return t, y * 0.3, rng


def _f(y):
    return dict(zip(T.FEATURES, T.features(y)))


def test_an_echo_shows_at_its_lag_in_the_cepstrum():
    _, d, _ = _playing()
    lag = int(0.3 * T.SR)
    e = d.copy()
    e[lag:] += 0.5 * d[:-lag]
    fe, fd = _f(e), _f(d)
    assert abs(2 ** fe["cep_lag"] / 300 - 1) < 0.1 and fe["cep_h"] > 3 * fd["cep_h"]


def test_a_tremolo_shows_at_its_rate_in_the_modulation_spectrum():
    t, d, _ = _playing()
    f = _f(d * (1 + 0.8 * np.sin(2 * np.pi * 5 * t)))
    assert abs(2 ** f["mod_f"] / 5 - 1) < 0.1


def test_a_reverb_slows_the_fastest_decays_and_fills_the_gaps():
    _, d, rng = _playing()
    ir = rng.standard_normal(int(2.5 * T.SR)) * np.exp(-np.arange(int(2.5 * T.SR)) / T.SR * 3) * 0.05
    r = d + np.convolve(d, ir)[: len(d)]
    fr, fd = _f(r), _f(d)
    assert fr["fast_b2"] > fd["fast_b2"] / 3 and fr["fast_b3"] > fd["fast_b3"] / 3 and fr["fill_b2"] > fd["fill_b2"]


def test_the_neighbours_leave_the_query_song_out_and_vote():
    songs = np.array(["a"] * 4 + ["b"] * 4)
    X = np.array([[0.0], [0.1], [5.0], [5.1], [0.05], [0.12], [5.05], [5.2]])
    Y = {"ron": np.array([0, 0, 1, 1, 0, 0, 1, 1], float), "rmix": np.array([np.nan, np.nan, .8, .6, np.nan, np.nan, .7, .9])}
    pred, prior = T.loso(X, X, Y, songs, k=2)
    assert list(pred["ron"]) == [0, 0, 1, 1, 0, 0, 1, 1]
    assert math.isclose(pred["rmix"][2], 0.8) and math.isclose(prior["rmix"][0], 0.8)


def test_the_rule_per_parameter():
    tp = {"reverb on/off": True, "rmix": True, "dtime": False}
    sp = {"reverb on/off": True, "rmix": False, "dtime": False}
    assert T.rule(tp, sp) == {"reverb on/off": "R1", "rmix": "R3", "dtime": "R4"}
