"""Amendment 2's oracle-DI arm (`learn/oracle_di_arm.py`): the search renders through the true DI
and scores against the stem at the judge's lag; everything else is stage F's H. Fakes only."""

import math
import random

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import arm_a_mega53 as M  # noqa: E402
from learn import oracle_di_arm as O  # noqa: E402
from tests.test_arm_a_mega53 import AMP, S0, toy_units  # noqa: E402


class FakeRR:
    def __init__(self):
        self.count, self.dis = 0, []

    def render(self, di32, sel, x):
        self.count += 1
        self.dis.append(di32)
        return np.full(M.SR, 0.1)


def test_run_direction_searches_through_the_true_di_at_the_judge_lag(monkeypatch, tmp_path):
    di = np.random.default_rng(0).standard_normal(1000)
    stem = np.ones(1000)
    part = {"judge_lag": 77}
    ctx = {"part": part, "sel": "sel", "S": S0, "S_stored": S0, "di": di, "di32": di.astype(np.float32),
           "ref": np.zeros(1000)}
    calls = []

    def fake_objective(ref, y, rb, half, lag=M.OBJ_LAG):
        calls.append((ref is stem, rb is di, half, lag))
        return 1.0, False

    monkeypatch.setattr(M, "objective", fake_objective)
    monkeypatch.setattr(M.K, "judge", lambda ref, y, d, lag: (calls.append(("judge", d is di, lag)) or {"A": 1.0, "B": 2.0}))
    monkeypatch.setattr(M, "save_kept_flac", lambda p, y: 1.0)
    monkeypatch.setattr(M.L, "main_stage", lambda dims, S, f, seed: (f(S), f(S), (S, 1.0, 2))[2])
    rr = FakeRR()
    path = tmp_path / "XO" / "p" / AMP / "A.json"
    M.run_direction(rr, ctx, "F", O.ARM, "p", AMP, "A", "B", None, stem=stem, rb=di, lag=part["judge_lag"], path=path)
    rec = M._load(path)
    assert rec["status"] == "done" and rec["lag"] == 77 and rec["arm"] == "XO" and rec["renders"] == 5
    obj = [c for c in calls if c[0] != "judge"]
    assert obj and all(c == (True, True, "A", 77) for c in obj)            # stem reference, true DI, judge lag
    assert [c for c in calls if c[0] == "judge"] == [("judge", True, 77)] * 2
    assert all(d.dtype == np.float32 and np.array_equal(d, di.astype(np.float32)) for d in rr.dis)


def test_default_run_direction_keeps_lag_minus_52():
    import inspect

    sig = inspect.signature(M.run_direction)
    assert sig.parameters["lag"].default == M.OBJ_LAG == -52


def test_render_count_and_cap():
    assert O.expected_renders() == 63 + 126 * 55 == 6_993 < O.CAP
    assert any("oracle_di_arm" in p for p in M.RENDERS)                    # counted by the machine-wide gate


def test_report_contrasts_and_share_of_ceiling():
    units = toy_units()
    rng = random.Random(9)
    for u in units:
        u["d"]["XO"] = u["d"]["H"] * math.exp(-0.05 + 0.02 * rng.gauss(0, 1))
        u["d"]["XO_unshrunk"] = u["d"]["XO"]
        u["rec"] = {"XO": {"fallback": None, "activity_fallback": 0}}
    filt = {r: (lambda u: True) for r in O.ROWS}
    rep = O.report_from_units(units, {})
    want = M.contrast(units, "XO", "S", O.ROWS, filt)["rows"]["all"]["all"]
    got = rep["contrasts"]["XO_minus_S"]["rows"]["all"]["all"]
    assert got["band_weighted_mean"] == pytest.approx(want["band_weighted_mean"]) and got["band_weighted_mean"] < 0
    assert rep["contrasts"]["XO_minus_H"]["rows"]["all"]["all"]["band_weighted_mean"] < 0
    assert rep["share_of_ceiling"]["XO_minus_S"] == pytest.approx(got["band_weighted_mean"] / -0.293)
    assert rep["fallbacks"] == 0

