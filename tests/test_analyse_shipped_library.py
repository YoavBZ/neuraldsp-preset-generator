"""The library-arm analysis: its band test, its decision rule and its spec."""

from __future__ import annotations

import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "research"))

import analyse_shipped_library as A  # noqa: E402


def test_the_band_sign_flip_is_exact_and_two_sided():
    # Every band leans the same way: only the all-plus and all-minus patterns
    # are as extreme, so p = 2 / 2**n.
    same = {f"b{i}": [-0.1, -0.2] for i in range(5)}
    assert A.sign_flip(same) == 2 / 2 ** 5
    # Balanced bands are no evidence at all.
    assert A.sign_flip({"a": [0.1], "b": [-0.1]}) == 1.0


def test_an_unmeasurable_render_loses_its_pair_whatever_its_distance():
    rows = [{"band": "a", "lost": (True, False), "stored": (0.5, 1.0), "corrected": (None, 1.0)},
            {"band": "b", "lost": (False, False), "stored": (0.5, 1.0), "corrected": (0.5, 1.0)},
            {"band": "c", "lost": (False, True), "stored": (2.0, 1.0), "corrected": (2.0, None)},
            {"band": "d", "lost": (True, True), "stored": (0.5, 1.0), "corrected": (0.5, 1.0)}]
    out = A.summarise(rows, "library", "template")
    for reading in ("stored", "corrected"):
        assert out[reading]["of"] == 3                   # both-unmeasurable left out
        assert out[reading]["first_closer"] == 2         # b by distance, c by default
        assert out[reading]["median_change"] == -0.5     # only the measured pair
    assert out["corrected"]["bands_first_closer"] == 2


def test_a_pair_is_scored_over_the_dimensions_both_sides_measured(monkeypatch):
    from analysis import compare as C
    from analysis.compare import Objectives

    a = Objectives(values={"timbre": 1.0, "ambience": None, "level": 3.0}, profile="unpaired-v3")
    b = Objectives(values={"timbre": 2.0, "ambience": 0.1, "level": 0.0}, profile="unpaired-v3")
    answers = iter((a, b))
    monkeypatch.setattr(C, "compare", lambda *args, **kw: next(answers))
    first, second = A.corrected_pair(None, None, None)
    # Ambience is measured on one side only, and level is left out: timbre alone.
    assert (first, second) == (1.0, 2.0)


def _pair(stored, corrected, p):
    return {"stored": {"first_closer": stored, "of": 43},
            "corrected": {"first_closer": corrected, "of": 43, "band_sign_flip_p": p}}


def test_the_decision_needs_both_readings_and_the_band_test():
    assert A.decide(_pair(30, 28, 0.01)) == "adopt the library search"
    assert A.decide(_pair(30, 28, 0.2)).startswith("not shown")
    assert A.decide(_pair(30, 21, 0.01)) == "the template"


def test_starting_settings_become_apply_specs_parameters():
    spec = A.spec_of({"/selectedAmp": "PR12", "parameters/outputGain": 2.5,
                      "pr12EQ/pr12EQBand1": -12.0})
    assert spec == [{"module": "", "key": "selectedAmp", "value": "PR12"},
                    {"module": "parameters", "key": "outputGain", "value": 2.5},
                    {"module": "pr12EQ", "key": "pr12EQBand1", "value": -12.0}]
    assert math.isclose(spec[1]["value"], 2.5)
