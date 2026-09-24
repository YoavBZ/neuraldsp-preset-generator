"""The committed RT60 control is reproducible, not a claim about real plugins."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")
pytest.importorskip("pyloudnorm", reason="needs the analysis extra")

from scripts.simulate_rt60_evidence import experiment


def _same_reading(actual, recorded):
    assert actual["passes_v1_rt60_gate"] == recorded["passes_v1_rt60_gate"]
    for key in ("rt60_s", "release_slope_agreement"):
        if recorded[key] is None:
            assert actual[key] is None
        else:
            # The artifact names its runtime versions. FFT/loudness libraries
            # can vary slightly across the supported Python matrix.
            assert actual[key] == pytest.approx(recorded[key], rel=0.05, abs=0.05)


def test_committed_rt60_synthetic_control_matches_the_protocol():
    recorded = json.loads((Path(__file__).parents[1] / "docs"
                           / "rt60-synthetic-evidence.json").read_text())
    current = experiment()
    assert current["schema"] == recorded["schema"]
    assert current["sample_rate"] == recorded["sample_rate"]
    assert current["loss_profile"] == recorded["loss_profile"]
    expected_inputs = ["noise-short", "noise-long", "synthetic-guitar"]
    assert [row["input"] for row in current["rows"]] == expected_inputs
    assert [row["input"] for row in recorded["rows"]] == expected_inputs
    for actual, expected in zip(current["rows"], recorded["rows"]):
        _same_reading(actual["dry_input"], expected["dry_input"])
        _same_reading(actual["rack_reverb_off"], expected["rack_reverb_off"])
        assert len(actual["rack_reverb_on"]) == len(expected["rack_reverb_on"]) == 2
        for measured, saved in zip(actual["rack_reverb_on"], expected["rack_reverb_on"]):
            assert measured["rack_decay_s"] == saved["rack_decay_s"]
            assert measured["rack_mix_percent"] == saved["rack_mix_percent"]
            _same_reading(measured["reading"], saved["reading"])
            assert measured["dry_vs_wet_ambience_terms"].keys() == \
                saved["dry_vs_wet_ambience_terms"].keys()
            for name, value in saved["dry_vs_wet_ambience_terms"].items():
                assert measured["dry_vs_wet_ambience_terms"][name] == \
                    pytest.approx(value, rel=0.05, abs=0.05)
            for key in ("dry_vs_wet_rt60_term", "dry_vs_wet_ambience"):
                if saved[key] is None:
                    assert measured[key] is None
                else:
                    assert measured[key] == pytest.approx(saved[key], rel=0.05, abs=0.05)
