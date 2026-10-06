"""The DI-free distance check's pure parts (`docs/di-free-distance-plan.md`)."""

from __future__ import annotations

import math
import pathlib
import random
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "research"))

import di_free_distance as D  # noqa: E402


def test_ranks_average_ties_and_spearman_reads_order():
    assert D.ranks([3.0, 1.0, 2.0, 1.0]) == [3.0, 0.5, 2.0, 0.5]
    assert D.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert D.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert D.spearman([1, 1, 1], [1, 2, 3]) == 0.0


def test_regret_is_the_log_gap_to_the_judges_best():
    judged = {"a": 2.0, "b": 4.0, "c": 3.0}
    assert D.regret_of(judged, "a") == 0.0
    assert D.regret_of(judged, "b") == pytest.approx(math.log(2))


def test_the_judge_is_read_from_one_window_and_band_set():
    reach = {"distances": {"p": {
        "pr12:factory:X|full|recording": 3.0, "pr12:factory:X|B|recording": 9.0,
        "pr12:factory:X|full|union": 4.0, "sw50r:factory:Y|full|recording": None,
        "ac20:template+R|full|recording": 5.0}}}
    assert D.judge(reach, "p", "recording") == {"pr12:factory:X": 3.0,
                                                 "ac20:template+R": 5.0}
    assert D.judge(reach, "p", "recording", "B") == {"pr12:factory:X": 9.0}


def test_the_band_statistic_counts_every_band_once():
    bands = {"a1": "A", "a2": "A", "a3": "A", "b": "B", "c": "C"}
    values = {"a1": 0.0, "a2": 0.0, "a3": 0.0, "b": 1.0, "c": 2.0}
    assert D.band_stat(values, bands) == 1.0          # not the parts' median, 0.0


def test_the_sign_flip_test_is_exact_and_one_sided():
    assert D.sign_flip_p([-1.0] * 9) == pytest.approx(1 / 512)
    assert D.sign_flip_p([1.0] * 9) == 1.0
    assert D.sign_flip_p([0.0, 0.0]) == 1.0


def test_holm_adjusts_in_order_and_stays_monotone():
    got = D.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert got == {"a": pytest.approx(0.03), "c": pytest.approx(0.06), "b": pytest.approx(0.06)}


def test_the_masked_distance_ignores_quiet_bands_and_level():
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    ref = np.array([0.0, -10.0, -20.0, -60.0])
    shifted = ref + 6.0                                   # the same shape, louder
    shifted[3] = 0.0                                      # and a band the mask drops
    assert D.masked(ref, None, shifted) == pytest.approx(0.0)
    assert D.masked(ref, None, ref + np.array([0, 0, 5.0, 0])) > 0


def test_the_lda_separates_labelled_clusters():
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    pytest.importorskip("scipy")
    rng = random.Random(1)
    X, y = [], []
    for label, centre in (("a", 0.0), ("b", 3.0), ("c", 6.0)):
        for _ in range(30):
            X.append([centre + rng.gauss(0, 0.3), rng.gauss(0, 5.0), rng.gauss(0, 5.0)])
            y.append(label)
    W = D.fit_lda(X, y, dims=1)
    projected = np.asarray(X) @ W
    means = [projected[[i for i, v in enumerate(y) if v == k]].mean() for k in "abc"]
    spread = projected[[i for i, v in enumerate(y) if v == "a"]].std()
    assert abs(means[2] - means[0]) > 10 * spread       # the noisy axes are ignored


def _block(row_bands, const_bands, regret, stems, rho, v3=1.0, const=1.0):
    bands = {f"p{i}": f"band{i}" for i in range(len(row_bands))}
    return bands, {
        "constant": {"regret": const, "per_part_regret": {
            p: const_bands[i] for i, p in enumerate(bands)}},
        "v3": {"reference": {"regret": v3}},
        **{name: {"reference": {"regret": 9.0, "agreement": 0.0,
                                "per_band_regret": {f"band{i}": 9.0 for i in range(len(row_bands))}},
                  "stem": {"regret": 9.0, "per_part_regret": {"p0": 9.0}}}
           for name in D.TESTED},
        "long_term_spectrum": {
            "reference": {"regret": regret, "agreement": rho,
                          "per_band_regret": {f"band{i}": v for i, v in enumerate(row_bands)}},
            "stem": {"regret": stems, "per_part_regret": {"p0": stems}}},
    }


def _result(**kw):
    bands, block = _block(**kw)
    return bands, {"by_band_set": {b: {m: block for m in D.MENUS} for b in D.BAND_SETS}}


def test_the_gate_needs_every_criterion_on_every_menu_and_band_set():
    good = dict(row_bands=[0.1] * 9, const_bands=[0.5] * 9, regret=0.1, stems=0.2, rho=0.7,
                const=0.5)
    bands, result = _result(**good)
    got = D.gate(result, bands)
    assert got["long_term_spectrum"]["passes"] and got["answer"] == "long_term_spectrum"
    for change in (dict(regret=0.8), dict(rho=0.5), dict(stems=0.9),
                   dict(row_bands=[0.1] * 5 + [0.9] * 4)):      # loses in four bands
        bands, result = _result(**{**good, **change})
        assert not D.gate(result, bands)["long_term_spectrum"]["passes"], change
    bands, result = _result(**{**good, "regret": 0.8})
    assert D.gate(result, bands)["answer"] is None


def test_the_stop_clause_reads_v3_on_every_menu_and_band_set():
    good = dict(row_bands=[0.1] * 9, const_bands=[0.5] * 9, regret=0.1, stems=0.2, rho=0.7)
    bands, result = _result(**good, v3=0.05)
    assert D.gate(result, bands)["stop_v3_is_enough"]
    bands, result = _result(**good, v3=0.2)
    assert not D.gate(result, bands)["stop_v3_is_enough"]


def test_the_log_mel_gate_keeps_only_frames_near_the_clips_loudest():
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    t = np.arange(D.RATE * 2) / D.RATE
    x = np.sin(2 * np.pi * 220 * t)
    x[D.RATE:] *= 1e-4                                   # a second 80 dB down
    stats = D.mel_stats(x)
    frames = (len(x) - D.N_FFT) // D.HOP + 1
    assert stats["mel"].shape[1] == D.MELS
    assert stats["mel"].shape[0] < frames * 0.6          # the quiet second is gated out
    assert (stats["floor_mean"] >= stats["mel_mean"]).all()
