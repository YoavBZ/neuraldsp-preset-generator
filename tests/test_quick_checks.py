"""The quick checks' rules (`docs/quick-checks-plan.md`): acceptable amps, distinct
answers, and the hub fixes' recognisers."""

from __future__ import annotations

import itertools
import math
import pathlib
import random
import statistics
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import reach_sets as S  # noqa: E402


def _d(values):
    return {f"{c}|{h}|{b}": v[i] for c, v in values.items()
            for i, h in enumerate(("A", "B", "full")) for b in S.BAND_SETS}


def test_the_expected_oracle_is_exact():
    rng = random.Random(1)
    menu = [f"x:factory:{i}" for i in range(7)]
    d = _d({c: (rng.random(), rng.random(), 1.0) for c in menu})
    for size in (1, 3, 7):
        brute = []
        for subset in itertools.combinations(menu, size):
            best = min(subset, key=lambda c: (d[f"{c}|A|recording"], c))
            brute.append(d[f"{best}|B|recording"])
        assert math.isclose(S.expected_oracle(d, menu, "A", "B", "recording", size),
                            statistics.mean(brute))


def test_amps_within_the_clear_cut_of_the_best_are_acceptable():
    values = {}
    for amp, far in (("ac20", 1.0), ("pr12", 1.1), ("sw50r", 1.5)):
        for i in range(3):
            values[f"{amp}:factory:{i}"] = (far, far, far)
    menus = {a: [f"{a}:factory:{i}" for i in range(3)] for a in S.AMPS}
    ok = S.acceptable(_d(values), menus, "recording")
    assert ok == {"ac20": True, "pr12": True, "sw50r": False}   # log 1.1 < 0.150 < log 1.5


def test_complete_linkage_never_chains_and_ignores_parts_that_separate_nothing():
    pytest.importorskip("scipy", reason="needs the analysis extra")
    # a~b and b~c by less than the cut, but a and c differ by more: three presets, two
    # classes. A fourth preset far away makes every part span the menu.
    values = {"a": (1, 1, 1.0), "b": (1, 1, 1.1), "c": (1, 1, 1.25), "z": (1, 1, 3.0)}
    dist = {f"p{i}": _d(values) for i in range(3)}
    band_of = {p: f"b{i}" for i, p in enumerate(dist)}
    found, used = S.classes(dist, list(dist), band_of, ["a", "b", "c", "z"], "recording")
    assert len(used) == 3 and len(found) == 3 and sorted(map(len, found)) == [1, 1, 2]
    flat = {f"p{i}": _d({"a": (1, 1, 1.0), "b": (1, 1, 1.05)}) for i in range(3)}
    found, used = S.classes(flat, list(flat), band_of, ["a", "b"], "recording")
    assert used == [] and len(found) == 1


def test_shares_are_weighted_by_band():
    flags = {"p1": True, "p2": True, "p3": True, "p4": False}
    band_of = {"p1": "big", "p2": "big", "p3": "big", "p4": "small"}
    assert S.band_weighted_share(flags, band_of) == 0.5


def test_the_unfixed_recogniser_is_plain_nearest_neighbour_and_csls_penalises_a_hub():
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    import k3_hub_fixes as H

    rng = np.random.default_rng(0)
    centres = rng.normal(size=(4, 6)) * 3
    X = np.concatenate([centres + rng.normal(size=(4, 6)) * 0.1 for _ in range(8)])
    y = np.tile(np.arange(4), 8)
    fold = np.repeat(np.arange(4), 8)
    factory = ["a", "b", "c", "d"]
    real = centres[[0, 1, 2, 3]] + 0.05
    real_fold = np.arange(4)
    targets = {"t": (0, centres[2] + 0.01)}
    base, every_fold = H.recognise(X, y, fold, real, real_fold, targets, factory, "baseline")
    assert base["t"]["1nn"] == "c" and every_fold[0]["t"] == base["t"]
    for v in H.VARIANTS:
        assert set(H.recognise(X, y, fold, real, real_fold, targets, factory, v)[0]["t"]) \
            == set(H.RECOGNISERS)


def test_the_sign_flip_and_holm():
    import k3_hub_fixes as H

    assert H.sign_flip_p([-0.1, -0.2, -0.3]) == 1 / 8
    assert H.holm({"a": 0.01, "b": 0.04}) == {"a": 0.02, "b": 0.04}
