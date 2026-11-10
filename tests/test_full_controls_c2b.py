"""C2b (docs/full-controls-plan.md, "C2b in detail"): learn/full_controls_c2b.py and `pipeline_fix.first_eval_check`."""
import json
import math
import pathlib
import re

import pytest

pytest.importorskip("numpy")

from learn import full_controls_c2b as X  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import pipeline_fix as P  # noqa: E402

AMPS = ("ac20", "pr12", "sw50r")


def stored(unit, amp, search="A", item="goat/item_1", cls="clean"):
    return {"unit": unit, "amp": amp, "search": search, "held": "B" if search == "A" else "A", "cls": cls,
            "item": item}


def rec(search_v, held_v, peak=-20.0, label=True, search="A"):
    held = "B" if search == "A" else "A"
    return {"label": {"x": 1} if label else None, "search": search, "held": held,
            "best": {"judge": {search: search_v, held: held_v}, "peak_dbfs": peak}}


def test_records_two_other_amps_per_unit_sorted_by_key():
    recs = X.c2b_records([stored("goat/item_2@5.0#amp_1", "pr12"), stored("goat/item_1@5.0#amp_3", "ac20", "B")], AMPS)
    assert [r["key"] for r in recs] == ["goat/item_1@5.0#amp_3|pr12", "goat/item_1@5.0#amp_3|sw50r",
                                        "goat/item_2@5.0#amp_1|ac20", "goat/item_2@5.0#amp_1|sw50r"]
    assert all(r["amp"] != r["forced_amp"] for r in recs)
    assert recs[0]["search"] == "B" and recs[0]["held"] == "A"


def test_records_refuse_a_unit_stored_twice():
    with pytest.raises(SystemExit):
        X.c2b_records([stored("u", "pr12"), stored("u", "ac20")], AMPS)


def test_shards_are_a_round_robin_over_every_record():
    recs = X.c2b_records([stored(f"goat/item_{j}@5.0#amp_1", "pr12") for j in range(7)], AMPS)
    sh = [X.shard_records(recs, k, 3) for k in range(3)]
    assert sorted(r["key"] for s in sh for r in s) == sorted(r["key"] for r in recs)
    assert [len(s) for s in sh] == [5, 5, 4]
    assert sh[0][0]["key"] == recs[0]["key"] and sh[1][0]["key"] == recs[1]["key"]


def test_cost_per_record_is_priming_and_the_main_stage():
    assert X.PER_RECORD == 53 and X.EVALS == 52


def test_usable_needs_a_label_a_finite_search_half_and_no_near_silence():
    assert X.usable(rec(1.0, 1.0))
    assert not X.usable(rec(1.0, 1.0, label=False))
    assert not X.usable(rec(float("inf"), 1.0))
    assert not X.usable(rec(1.0, 1.0, peak=-57.3))
    assert X.usable(rec(1.0, 1.0, peak=-57.0))
    assert not X.usable(None)


def test_amp_choice_is_the_search_half_argmin_over_usable_labels_ties_sorted():
    by = {"ac20": rec(2.0, 1.0), "pr12": rec(1.0, 3.0), "sw50r": rec(0.5, 1.0, peak=-59.0)}
    assert X.amp_choice(by) == "pr12"                     # sw50r is near silent
    assert X.amp_choice({"pr12": rec(1.0, 1.0), "ac20": rec(1.0, 2.0)}) == "ac20"
    assert X.amp_choice({"pr12": rec(1.0, 1.0, label=False)}) is None


def test_amp_read_is_the_chosen_held_half_against_the_mean_over_usable_amps():
    by = {"ac20": rec(2.0, 1.0), "pr12": rec(1.0, math.e), "sw50r": rec(3.0, math.e ** 2)}
    assert X.amp_read(by, "pr12") == pytest.approx(1.0 - 1.0)
    assert X.amp_read(by, "ac20") == pytest.approx(0.0 - 1.0)
    assert X.amp_read({"pr12": rec(1.0, 1.0)}, "pr12") is None          # one usable amp: no blind choice
    assert X.amp_read(by, "nope") is None


def _cl(rows):
    return {"n": len(rows), "mean": sum(v for _, _, v in rows) / len(rows)}


def test_report_rows_count_the_choice_and_read_it_by_item():
    units = [{"unit": "u1", "item": "i1", "cls": "clean", "forced_amp": "ac20",
              "by_amp": {"ac20": rec(2.0, 1.0), "pr12": rec(1.0, math.e), "sw50r": rec(3.0, math.e ** 2)}},
             {"unit": "u2", "item": "i1", "cls": "crunch", "forced_amp": "pr12",
              "by_amp": {"ac20": rec(1.0, 1.0, label=False), "pr12": rec(1.0, 1.0), "sw50r": rec(2.0, math.e)}},
             {"unit": "u3", "item": "i2", "cls": "clean", "forced_amp": "pr12",
              "by_amp": {"ac20": rec(1.0, 1.0, label=False), "pr12": rec(1.0, 1.0, label=False),
                         "sw50r": rec(1.0, 1.0, label=False)}}]
    out = X.report_rows(units, _cl)
    c = out["counts"]
    assert c["units"] == 3 and c["chosen"] == 2 and c["no_choice"] == 1 and c["three_usable"] == 1
    assert c["withheld"] == 0
    assert out["labels"]["u1"]["amp"] == "pr12" and out["labels"]["u1"]["n_usable"] == 3
    assert out["labels"]["u2"]["amp"] == "pr12" and out["labels"]["u2"]["n_usable"] == 2
    assert out["labels"]["u3"] == {"amp": None, "n_usable": 0}
    assert c["chosen_is_forced"] == 1 and c["chosen_is_held_best"] == 1
    assert out["chosen_by_amp"] == {"pr12": 2}
    assert out["chosen_by_forced_amp"] == {"ac20": {"pr12": 1}, "pr12": {"pr12": 1}}
    assert out["chosen_minus_blind"]["all"]["n"] == 2
    assert out["chosen_minus_blind"]["clean"]["n"] == 1 and out["chosen_minus_blind"]["crunch"]["n"] == 1
    assert out["chosen_minus_blind"]["crunch"]["mean"] == pytest.approx(-0.5)
    assert out["forced_minus_blind"]["all"]["n"] == 2


def test_a_unit_with_a_refused_or_missing_record_gets_no_label():
    refused = dict(rec(0.1, 0.1), label=None, refused={"first_sha": "y"})
    units = [{"unit": "u1", "item": "i1", "cls": "clean", "forced_amp": "ac20",
              "by_amp": {"ac20": rec(2.0, 1.0), "pr12": refused, "sw50r": rec(3.0, 1.0)}},
             {"unit": "u2", "item": "i1", "cls": "clean", "forced_amp": "ac20",
              "by_amp": {"ac20": rec(2.0, 1.0), "pr12": None, "sw50r": rec(3.0, 1.0)}}]
    out = X.report_rows(units, _cl)
    assert out["labels"]["u1"] == {"amp": None, "withheld": "a record was refused"}
    assert out["labels"]["u2"] == {"amp": None, "withheld": "a record is missing"}
    assert out["counts"]["withheld"] == 2 and out["counts"]["chosen"] == 0


def test_dropped_reads_and_the_sensitivity_check_are_counted():
    units = [{"unit": "u1", "item": "i1", "cls": "clean", "forced_amp": "ac20",       # chosen held half infinite
              "by_amp": {"ac20": rec(1.0, float("inf")), "pr12": rec(2.0, 1.0), "sw50r": rec(3.0, 1.0)}},
             {"unit": "u2", "item": "i2", "cls": "clean", "forced_amp": "ac20",       # one usable amp
              "by_amp": {"ac20": rec(1.0, 1.0), "pr12": rec(2.0, 1.0, label=False),
                         "sw50r": rec(3.0, 1.0, label=False)}},
             {"unit": "u3", "item": "i3", "cls": "clean", "forced_amp": "ac20",       # -55.5 dBFS: out at -54
              "by_amp": {"ac20": rec(1.0, 1.0, peak=-55.5), "pr12": rec(2.0, 1.0), "sw50r": rec(3.0, 1.0)}}]
    c = X.report_rows(units, _cl)["counts"]
    assert c["read_dropped_held_nonfinite"] == 1 and c["read_dropped_one_amp"] == 1 and c["read"] == 1
    assert c["changed_at_sensitivity"] == 1


def test_quiet_is_the_near_silence_rule_alone():
    assert X.quiet(rec(1.0, 1.0, peak=-57.3))
    assert not X.quiet(rec(1.0, 1.0, peak=-20.0))
    assert not X.quiet(rec(float("inf"), 1.0, peak=-57.3))      # out for its search half, not for silence
    assert not X.quiet(rec(1.0, 1.0, peak=-57.3, label=False))


def test_systematic_miss_counts_misses_overall_and_per_amp():
    assert P.systematic_miss(10, 4, {"pr12": 5}, {"pr12": 2}, (5, 10), (3, 5)) is None
    assert "5 of the first 9" in P.systematic_miss(9, 5, {}, {}, (5, 10), None)
    assert P.systematic_miss(11, 5, {}, {}, (5, 10), None) is None           # past the first 10
    assert "pr12" in P.systematic_miss(6, 3, {"pr12": 4, "ac20": 2}, {"pr12": 3}, (5, 10), (3, 5))
    assert P.systematic_miss(9, 3, {"pr12": 6}, {"pr12": 3}, (5, 10), (3, 5)) is None    # past pr12's first 5
    assert P.systematic_miss(9, 9, {}, {}, None, None) is None


@pytest.mark.parametrize("sha,tol,value,expect", [
    ("x", None, 1.0, "ok"), ("y", None, 1.0, "raise"),
    ("x", 0.005, 2.0, "ok"), ("y", 0.005, 1.004, "sha_differs"), ("y", 0.005, 1.01, "refuse"),
    ("y", 0.005, float("nan"), "refuse"), ("y", 0.005, None, "refuse")])
def test_first_eval_check(sha, tol, value, expect):
    assert P.first_eval_check(sha, "x", value, 1.0, tol) == expect


def test_search_units_defaults_keep_earlier_callers():
    import inspect

    sig = inspect.signature(P.search_units)
    for name in ("sdir", "lag_phase", "first_tol", "miss_guard", "amp_guard"):
        assert sig.parameters[name].default is None
        assert sig.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["lags_stored"].default is False


def test_search_is_registered_as_a_render_command():
    assert any(re.search(p, "python -m learn.full_controls_c2b c2b-search --shard 0/3") for p in LO.RENDERS)


def test_ledger_declares_phase_c2b():
    led = json.loads((pathlib.Path(__file__).resolve().parents[1] / "docs" / "dev-test-ledger.json").read_text())
    pf = next(t for t in led["tests"] if t.get("test_id") == "pipeline-fix")
    assert "phase_c2b" in pf
