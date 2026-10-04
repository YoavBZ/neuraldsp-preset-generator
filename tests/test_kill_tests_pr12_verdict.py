"""The clean-PR12 kill tests' verdict counts as `docs/kill-tests-pr12-plan.md` declares."""

from __future__ import annotations

import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import kill_tests_pr12_verdict as V  # noqa: E402


def test_the_verdict_counts_as_declared():
    def row(band, model, vs_shuffled, vs_constant, pick):
        return {"band": band, "model": model, "model_vs_shuffled": vs_shuffled,
                "model_vs_constant": vs_constant, "pick": pick}

    rows = [row("b1", -0.3, -0.1, -0.1, "x"), row("b2", -0.2, 0.0, 0.0, "y"),
            row("b3", -0.4, -0.2, 0.1, "z"), row("b4", -0.2, -0.1, -0.2, "w")]
    r = V.k3_reading(rows)
    assert r["better_than_shuffled_ties_half"] == 3.5          # a shuffled tie is half
    assert r["closer_than_constant"] == 2 and r["constant_ties"] == 1
    assert not r["pass"], "2 of 4 against the constant is not a majority"
    rows[2] = row("b3", -0.4, -0.2, -0.1, "z")
    assert V.k3_reading(rows)["pass"]
    rows = [dict(r, model=-0.12) for r in rows]                # above the clear cut
    assert not V.k3_reading(rows)["pass"]


def _rows(model, n=4):
    return [{"part": f"p{i}", "band": f"b{i}", "model": model, "model_vs_shuffled": -0.1,
             "model_vs_constant": -0.1, "pick": f"x{i}"} for i in range(n)]


def test_a_dropped_part_counts_as_not_closer():
    rows = _rows(-0.3)
    assert V.k3_reading(rows, expected=["p0", "p1", "p2", "p3"])["pass"]
    out = V.k3_reading(rows[:2], expected=["p0", "p1", "p2", "p3"])
    assert out["dropped_parts"] == ["p2", "p3"] and not out["pass"]


def test_the_same_recogniser_must_pass_both_band_sets_and_k1_sits_on_its_line():
    good, bad = _rows(-0.3), _rows(-0.12)
    k1_rows = [{"part": "p0", "band": "b0", "oracle": math.log(0.75)}]
    judge = {"k1": {"recording": {"rows": k1_rows}, "union": {"rows": k1_rows}},
             "k3": {"recording": {"1nn": {"rows": good}}, "union": {"1nn": {"rows": bad}}}}
    out = V.verdict({"k2_pass": True}, judge)
    assert out["k1"]["pass"], "exactly log 0.75 passes"
    assert not out["k3"]["pass"] and not out["passes_on_clean_pr12"]
    same = [dict(r, pick="one") for r in good]
    judge["k3"] = {"recording": {"1nn": {"rows": same}}, "union": {"1nn": {"rows": same}}}
    assert not V.verdict({"k2_pass": True}, judge)["k3"]["pass"], "one preset for every part"
