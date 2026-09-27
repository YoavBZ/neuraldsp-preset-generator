"""Hidden reliability probes stay separate from objective agreement."""

import copy

import pytest

from scripts._listening_trials import consistency, plan_trials, primary_answer


PRIMARY = {"A": "first", "B": "second"}


def _answer_for(role, mapping):
    return next(label for label, source in mapping.items() if source == role)


def test_secret_order_and_remapped_repeat_have_one_primary():
    trials = plan_trials(23, PRIMARY, repeats=2, catch=True)
    assert trials == plan_trials(23, PRIMARY, repeats=2, catch=True)
    assert [row["ordinal"] for row in trials] == [1, 2, 3, 4]
    assert [row["kind"] for row in trials].count("primary") == 1
    assert [row["kind"] for row in trials].count("repeat") == 2
    assert [row["kind"] for row in trials].count("catch") == 1
    assert next(row for row in trials if row["kind"] == "primary")["blind_key"] == PRIMARY
    assert any(row["blind_key"] == {"A": "second", "B": "first"}
               for row in trials if row["kind"] == "repeat")
    assert plan_trials(23, PRIMARY) is None


def test_repeat_compares_resolved_source_and_catch_expects_a_tie():
    trials = plan_trials(23, PRIMARY, repeats=2, catch=True)
    answers = ["indistinguishable" if row["kind"] == "catch" else
               _answer_for("first", row["blind_key"]) for row in trials]
    assert primary_answer(trials, answers, PRIMARY) == "A"
    result = consistency(trials, answers, PRIMARY)
    assert result["repeat"] == {"trials_not_independent_n": 2,
                                "consistent": 2, "fraction": 1.0}
    assert result["catch"] == {"trials_not_independent_n": 1,
                               "indistinguishable": 1, "fraction": 1.0}

    wrong = answers.copy()
    repeat_index = next(i for i, row in enumerate(trials) if row["kind"] == "repeat")
    catch_index = next(i for i, row in enumerate(trials) if row["kind"] == "catch")
    wrong[repeat_index] = _answer_for("second", trials[repeat_index]["blind_key"])
    wrong[catch_index] = "A"
    result = consistency(trials, wrong, PRIMARY)
    assert result["repeat"]["consistent"] == 1
    assert result["catch"]["indistinguishable"] == 0

    tied = answers.copy()
    primary_index = next(i for i, row in enumerate(trials) if row["kind"] == "primary")
    tied[primary_index] = "indistinguishable"
    assert consistency(trials, tied, PRIMARY)["repeat"]["consistent"] == 0


def test_rejects_missing_answers_or_a_damaged_private_plan():
    trials = plan_trials(7, PRIMARY, repeats=1, catch=True)
    with pytest.raises(ValueError, match="exactly 3"):
        consistency(trials, ["A", "B"], PRIMARY)
    with pytest.raises(ValueError, match="between 0 and 3"):
        plan_trials(7, PRIMARY, repeats=4)
    damaged = copy.deepcopy(trials)
    catch = next(row for row in damaged if row["kind"] == "catch")
    catch["blind_key"]["B"] = "second" if catch["blind_key"]["A"] == "first" else "first"
    with pytest.raises(ValueError, match="catch trial"):
        consistency(damaged, ["A", "B", "indistinguishable"], PRIMARY)
    damaged = copy.deepcopy(trials)
    next(row for row in damaged if row["kind"] == "primary")["blind_key"] = {
        "A": "second", "B": "first"}
    with pytest.raises(ValueError, match="frozen objective mapping"):
        consistency(damaged, ["A", "B", "indistinguishable"], PRIMARY)
