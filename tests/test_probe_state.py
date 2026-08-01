"""Adaptive record-state probing decisions that do not require a plugin."""

from types import SimpleNamespace

from packs.loader import ParamSpec
from scripts.probe_state import (
    candidate_values,
    classify_attempt,
    summarize_attempts,
)


def _moved(address=7, name="Control"):
    return [{"address": address, "name": name}]


def test_candidates_prefer_diverse_values_seen_in_real_presets():
    param = SimpleNamespace(value="0.5")
    spec = ParamSpec(module="", key="gain", kind="rotation", needs_review=True)

    assert candidate_values(param, spec, ["0.2", "0.8", "0.6"], maximum=4) == [
        "0.2",
        "0.8",
        "0.6",
        "0",
    ]


def test_candidates_never_repeat_the_baseline_or_each_other():
    param = SimpleNamespace(value="0")
    spec = ParamSpec(module="", key="active", kind="switch")

    candidates = candidate_values(param, spec, ["0", "1", "1.0"], maximum=4)

    assert candidates[0] == "1"
    assert "0" not in candidates
    assert len(candidates) == len(set(candidates))


def test_attempt_classification_uses_returned_state_and_control_movement():
    assert classify_attempt("0", "1", "1", _moved()) == "mapped"
    assert classify_attempt("0", "1", "1", []) == "state_only"
    assert classify_attempt("0", "1", "0", []) == "rejected"
    assert classify_attempt("0", "0", "0", []) == "no_op"
    assert classify_attempt("0", "1", None, []) == "unsupported"
    assert classify_attempt("0", "1", "1", _moved() + _moved(8)) == "ambiguous"


def test_consistent_attempts_produce_one_mapping():
    attempts = [
        {"outcome": "mapped", "moved": _moved(42, "Amp Gain")},
        {"outcome": "mapped", "moved": _moved(42, "Amp Gain")},
        {"outcome": "rejected", "moved": []},
    ]

    assert summarize_attempts(attempts) == {
        "status": "mapped",
        "address": 42,
        "control": "Amp Gain",
    }


def test_different_controls_are_ambiguous_even_when_each_write_moves_one():
    attempts = [
        {"outcome": "mapped", "moved": _moved(1)},
        {"outcome": "mapped", "moved": _moved(2)},
    ]

    assert summarize_attempts(attempts) == {"status": "ambiguous"}


def test_any_accepted_state_only_value_beats_rejected_candidates():
    attempts = [
        {"outcome": "state_only", "moved": []},
        {"outcome": "rejected", "moved": []},
    ]

    assert summarize_attempts(attempts) == {"status": "state_only"}
