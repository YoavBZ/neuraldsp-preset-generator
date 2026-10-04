"""Stage 0b's listening validation: how trials are split into sittings, how answers
are read, and how they are scored against each distance."""

from __future__ import annotations

import math
import pathlib
import random
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_listening_validation as B  # noqa: E402
import score_listening_validation as S  # noqa: E402


def _plan():
    tests = [{"kind": "test", "id": f"t{i:02d}", "part": f"p{i}", "first": f"c{i}a",
              "second": f"c{i}b", "disagree": i < 10,
              "log_ratio": {d: -0.3 for d in ("judge", "alm", "judge_union", "v3c")}}
             for i in range(24)]
    for t in tests[:10]:
        t["log_ratio"]["v3c"] = 0.3                     # v3c disagrees on the first ten
    hidden = [{"kind": "hidden_reference", "part": f"h{i}", "first": "reference",
               "second": f"x{i}"} for i in range(3)]
    repeats = [{"kind": "repeat", "of": f"t{i:02d}"} for i in (0, 1, 2)]
    return {"trials": tests + hidden + repeats}


def test_repeats_follow_their_originals_and_each_sitting_has_a_hidden_reference():
    plan = _plan()
    for seed in range(20):
        first, second = B.sittings(list(plan["trials"]), random.Random(seed))
        assert len(first) == len(second) == 15
        ids_first = {t.get("id") for t in first}
        assert all(t["of"] in ids_first for t in second if t["kind"] == "repeat")
        assert not any(t["kind"] == "repeat" for t in first)
        for block in (first, second):
            assert any(t["kind"] == "hidden_reference" for t in block)


def test_every_trial_must_be_answered_once():
    assert S.parse_answers("1: A\n2: b\n3 ?\n", 3) == {1: "A", 2: "B", 3: "?"}
    with pytest.raises(ValueError, match="no answer"):
        S.parse_answers("1: A\n3: B\n", 3)
    with pytest.raises(ValueError, match="twice"):
        S.parse_answers("1: A\n1: B\n2: A\n", 2)


def test_the_binomial_and_holm_steps_are_exact():
    assert S.binomial_p(17, 22) == pytest.approx(0.00845, abs=1e-5)
    assert S.binomial_p(16, 22) == pytest.approx(0.02624, abs=1e-5)
    out = S.holm({"judge": 0.02, "alm": 0.04})
    assert out["judge"]["threshold"] == 0.025 and out["judge"]["passed"]
    assert out["alm"]["threshold"] == 0.05 and out["alm"]["passed"]
    out = S.holm({"judge": 0.03, "alm": 0.04})              # the first step fails, so both do
    assert not out["judge"]["passed"] and not out["alm"]["passed"]


def _order_and_keys(plan, pick_first, missed_references=0):
    order, keys = [], {}
    for n, t in enumerate(plan["trials"], start=1):
        pair = (next(x for x in plan["trials"] if x.get("id") == t["of"])
                if t["kind"] == "repeat" else t)
        order.append({"trial": n, "kind": t["kind"], "id": t.get("id"), "of": t.get("of"),
                      "first": pair["first"], "second": pair["second"]})
        keys[n] = {"blind_key": {"A": "first", "B": "second"}}
    answers = {}
    for row in order:
        if row["kind"] == "hidden_reference":
            answers[row["trial"]] = "B" if missed_references > 0 else "A"
            missed_references -= 1
        else:
            answers[row["trial"]] = "A" if pick_first(row) else "B"
    return order, keys, answers


def test_a_listener_who_agrees_with_the_judge_validates_it():
    plan = _plan()
    order, keys, answers = _order_and_keys(plan, lambda row: True)  # always the first (closer)
    out = S.score(plan, order, keys, answers)
    assert out["valid"] and out["decided"] == 24
    assert out["agreement"]["judge"]["agree"] == 24 and out["validated"]["judge"]
    assert out["agreement"]["v3c"]["agree"] == 14                  # v3c wrong on its ten
    assert out["judge_vs_v3c_where_they_disagree"]["listener_with_judge"] == 10
    assert all(r["same"] for r in out["repeats"])


def test_missed_hidden_references_void_the_test_and_cant_tell_is_not_half():
    plan = _plan()
    order, keys, answers = _order_and_keys(plan, lambda row: True, missed_references=2)
    assert not S.score(plan, order, keys, answers)["valid"]
    order, keys, answers = _order_and_keys(plan, lambda row: True)
    for row in order[:8]:
        answers[row["trial"]] = "?"
    out = S.score(plan, order, keys, answers)
    assert out["decided"] == 16 and out["agreement"]["judge"]["of"] == 16
    assert out["cant_tell_rate"] == pytest.approx(8 / 24)
    assert not math.isnan(out["agreement"]["judge"]["p_one_sided"])
