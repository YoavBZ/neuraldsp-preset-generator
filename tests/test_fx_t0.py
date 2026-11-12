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


def test_the_neighbours_leave_the_band_out_keep_the_amp_and_use_the_effects_own_features():
    bands = np.array(["a"] * 4 + ["b"] * 4)
    amps = np.array(["pr12", "pr12", "ac20", "ac20"] * 2)
    X = np.zeros((8, len(T.FEATURES)))
    j = T.FEATURES.index("fast_b1")
    X[:, j] = [0.0, 5.0, 0.0, 5.0, 0.1, 5.1, 0.2, 5.2]
    X[:, T.FEATURES.index("cep_h")] = [9, -9, 9, -9, -9, 9, -9, 9]       # another effect's feature: ignored for reverb
    Y = {c: np.full(8, np.nan) for c in ("ron", "rmix", "rdecay")}
    Y["ron"] = np.array([0, 1, 0, 1, 0, 1, 0, 1], float)
    Y["rmix"] = np.array([np.nan, .8, np.nan, .6, np.nan, .7, np.nan, .9])
    Y["rdecay"] = np.array([np.nan, 1.0, np.nan, 2.0, np.nan, 1.5, np.nan, 2.5])
    pred, prior = T.predict("reverb", X, X, Y, bands, amps, T.OWN["reverb"], k=1)
    assert list(pred["ron"]) == [0, 1, 0, 1, 0, 1, 0, 1]
    assert math.isclose(pred["rmix"][1], 0.7) and math.isclose(pred["rmix"][3], 0.9)      # same amp, other band
    assert math.isclose(prior["rmix"][1], 0.8)                                             # the other band's median


def test_a_pass_must_hold_with_each_large_band_left_out():
    ok = {"ci": [0.6, 0.8], "without Forkupines": 0.62, "without BKS": 0.7}
    r = {"reverb": {"strong_third": ok, "knobs": {"rmix": {"ci": [-0.2, -0.05], "without Forkupines": -0.1,
                                                           "without BKS": 0.01}}}}
    p = T.passes(r)
    assert p["reverb on/off"] and not p["rmix"]


def test_the_rule_per_parameter():
    tp = {"reverb on/off": True, "rmix": True, "dtime": False}
    sp = {"reverb on/off": True, "rmix": False, "dtime": False}
    assert T.rule(tp, sp) == {"reverb on/off": "R1", "rmix": "R3", "dtime": "R4"}
