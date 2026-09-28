"""The harmonic study's pieces that do not need the plugin."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import study_harmonic as H  # noqa: E402


def test_one_note_is_within_three_percent():
    assert H.same_note({"f0_hz": 110.0}, {"f0_hz": 113.0})
    assert not H.same_note({"f0_hz": 110.0}, {"f0_hz": 220.0})
    assert not H.same_note(None, {"f0_hz": 110.0})


def test_every_drive_step_names_a_control_of_its_amp():
    pytest.importorskip("numpy", reason="needs the analysis extra")
    from match import space as space_module

    for (pack, amp), steps in H.STEPS.items():
        paths = {dimension.path for dimension in space_module.build(pack, amp=amp).dimensions}
        assert 0 <= H.REFERENCE_STEP < len(steps)
        for _, changes in steps:
            assert set(changes) <= paths, (pack, amp, set(changes) - paths)


def test_rescoring_leaves_harmonic_out_of_every_total(tmp_path):
    pytest.importorskip("scipy", reason="needs the analysis extra")
    # Two targets. With `harmonic` the noise answer is far worse on target 0;
    # without it the two arms tie on timbre alone.
    def outcome(signal, index, harmonic):
        return {"signal": signal, "target_index": index,
                "objective_dimensions": {"timbre": 1.0, "harmonic": harmonic},
                "neutral_dimensions": {"timbre": 2.0, "harmonic": 0.0}}

    document = {"amp": "sw50r", "outcomes": [
        outcome("same", 0, 0.0), outcome("same", 1, 0.0),
        outcome("noise", 0, 100.0), outcome("noise", 1, 0.0)]}
    path = tmp_path / "recordings.json"
    path.write_text(json.dumps(document))
    rows = {(row["a"], row["b"]): row
            for row in H.rescore(path, "unpaired-v2")["rows"]}

    assert set(rows) == {("same", "neutral"), ("noise", "neutral")}
    noise = rows[("noise", "neutral")]
    assert noise["with_harmonic"]["mean_change"] > 1.0
    assert noise["without_harmonic"]["closer"] == 2
    assert noise["without_harmonic"]["mean_change"] == pytest.approx(-0.5)


def test_recovery_counts_the_targets_own_step_as_closest_and_ties_as_misses():
    # Passage "a" measures the step itself; passage "b" reads the step backwards,
    # so across passages the closest candidate is never the target's own step
    # except in the middle.
    reading = {"a": lambda step: step, "b": lambda step: 2 - step}

    def distance(target, candidate):
        return abs(reading[target[1]](target[0]) - reading[candidate[1]](candidate[0]))

    result = H.recovery(distance, 3, ["a", "b"])
    assert result["of"] == 6 and result["recovered"] == 2
    assert result["chance"] == pytest.approx(1 / 3, abs=1e-4) and result["chance_rank"] == 1.0

    flat = H.recovery(lambda target, candidate: 0.0, 3, ["a", "b"])
    assert flat["recovered"] == 0 and flat["mean_rank"] == 0.0
    gap = H.recovery(lambda target, candidate: None, 3, ["a", "b"])
    assert gap["of"] == 0 and gap["rate"] is None
