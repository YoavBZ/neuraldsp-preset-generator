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
