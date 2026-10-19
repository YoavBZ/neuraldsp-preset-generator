"""learn/direct_existing.py: the pure parts (docs/direct-existing-plan.md)."""

import math

import numpy as np
import pytest

from learn import direct_existing as DE


def _out(logpi, mu, sw, cats):
    return (np.log(np.asarray(logpi, float)), np.asarray(mu, float), np.asarray(sw, float),
            [np.asarray(c, float) for c in cats])


def test_ensemble_takes_the_pooled_top_component_not_the_mean_of_means():
    a = _out([0.6, 0.4], [[0.1, 0.2], [0.9, 0.9]], [1.0], [[2.0, 0.0]])
    b = _out([0.2, 0.8], [[0.5, 0.5], [0.7, 0.3]], [-1.0], [[0.0, 1.0]])
    c = _out([0.5, 0.5], [[0.0, 0.0], [1.0, 1.0]], [3.0], [[0.0, 1.5]])
    cont, sw, mics, diag = DE.ensemble([a, b, c])
    assert np.allclose(cont, [0.7, 0.3])                      # seed b, component 1 (0.8 / 3 is the largest)
    assert diag["seed"] == DE.SEEDS[1] and diag["component"] == 1
    assert math.isclose(diag["pooled_weight"], 0.8 / 3)
    assert sw.tolist() == [True]                               # 2 of 3 above 0.5
    assert mics == [1]                                         # summed probabilities


def test_ensemble_clips_to_unit():
    a = _out([1.0], [[1.2, -0.1]], [0.0], [[0.0, 1.0]])
    cont, _, _, _ = DE.ensemble([a])
    assert cont.tolist() == [1.0, 0.0]


class _Dim:
    def __init__(self, name, module, key, kind, values=None):
        self.name, self.module, self.key, self.kind, self.values = name, module, key, kind, values

    def from_unit(self, u):
        return 10 * u


def test_settings_replace_only_the_labelled_dimensions():
    dims = [_Dim("g", "p", "gain", "cont"), _Dim("b", "p", "bright", "switch", ["false", "true"]),
            _Dim("m", "c", "mic", "cat", [str(i) for i in range(10)])]
    S = {("p", "gain"): "1", ("p", "bright"): "false", ("c", "mic"): "0", ("x", "other"): "keep"}
    layout = (["g", "z"], ["b"], ["m"], [str(i) for i in range(10)])
    x = DE.settings_from("pr12", S, [0.5, 0.9], [True], [3], lambda a, s: dims, lambda v: f"{v:g}", layout)
    assert x == {("p", "gain"): "5", ("p", "bright"): "true", ("c", "mic"): "3", ("x", "other"): "keep"}
    assert S[("p", "gain")] == "1"                              # S untouched


def test_features_mask_half_a_and_apply_one_gain():
    rng = np.random.default_rng(0)
    mix = rng.normal(0, 0.1, 480_000)
    stem = 0.5 * mix
    xa, la = DE.features(mix, stem, "A", 0.0)
    xb, lb = DE.features(mix, stem, "B", 0.0)
    assert xa.shape == xb.shape == (2, 96, 446)
    from learn import pretrain_set as PS
    assert np.all(xa[:, :, :PS.MASK_A_FRAMES] == 0) and np.any(xb[:, :, :PS.MASK_A_FRAMES] != 0)
    xg, lg = DE.features(mix, stem, "B", 6.0)
    assert lg[0] - lb[0] == pytest.approx(6.0, abs=0.01) and lg[1] - lb[1] == pytest.approx(6.0, abs=0.01)
    assert lb[1] - lb[0] == pytest.approx(20 * math.log10(2), abs=0.01)
    db = xb * 30 - 60                                          # on the 0.5-dB grid
    assert np.allclose(np.round((db + 112) / 0.5), (db + 112) / 0.5, atol=1e-3)


def test_counts_and_shards():
    assert DE.expected_renders() == 63 * 12 + 16 * 6 == 852 <= DE.CAP
    xs = [(i, "a") for i in range(7)]
    parts = [DE.shard(xs, (k, 3)) for k in range(3)]
    assert sorted(sum(parts, [])) == sorted(xs) and all(parts)


def test_unseen_bands_are_those_without_a_training_section():
    secs = [{"band": "Zeno", "split": "val"}, {"band": "Eat The Feeder", "split": "train"},
            {"band": "Diesel13", "split": "reserve"}]
    got = DE.unseen_bands(secs)
    assert "Zeno" in got and "Diesel13" in got and "Eat The Feeder" not in got
    assert len(got) == 11                                      # 12 stage F bands, one trained


def _unit(band, slug, d, dr, cls="clean"):
    return {"band": band, "slug": slug, "cls": cls, "amp": "pr12", "search": "A", "held": "B", "d": d, "d_raw": dr}


def test_widening_is_the_paired_change_of_the_log_ratio():
    us = [_unit(f"b{i}", f"p{i}", {"D": 2.0, "S": 4.0}, {"D": 1.0, "S": 4.0 * (1 + 0.1 * i)}) for i in range(4)]
    w = DE.widening(us, "D", "S")
    exp = [math.log(1 / (4 * (1 + 0.1 * i))) - math.log(0.5) for i in range(4)]
    assert w["raw_minus_measure"]["band_weighted_mean"] == pytest.approx(sum(exp) / 4)
    assert w["band_sd_d"] == pytest.approx(0.0)


def test_ka_summary_floors_and_weights_by_band():
    rows = [{"song": "bourbon", "label": "s1",
             "raw": {"S": {"A": 4.0, "B": 4.0}, "truth": {"A": 0.0, "B": 0.0}},
             "measure": {"S": {"A": 4.0, "B": 4.0}, "truth": {"A": 2.0, "B": 2.0}},
             "stored": {"measure_truth": {"A": 2.0, "B": 2.0}, "raw_S": {"A": 4.0, "B": 4.0}}}]
    s = DE.ka_summary(rows)
    assert s["raw"]["log_truth_minus_S"]["band_weighted_mean"] == pytest.approx(math.log(0.01 / 4))
    assert s["measure"]["truth_over_S_median"] == pytest.approx(0.5)
    assert s["stored_vs_fresh_measure_truth_max_dev"] == 0
