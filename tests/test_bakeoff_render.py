"""The score read's pure functions (`learn/bakeoff_render.py`)."""
import math

import pytest

np = pytest.importorskip("numpy")

from learn import bakeoff_render as R


def t90(_df):
    return 2.0


def test_directions_score_each_search_half_on_the_other():
    assert R.direction_rows(["k"]) == [("k", "A", "B"), ("k", "B", "A")]


def test_value_reads_a_search_half_or_a_centres_single_answer():
    judge = {"m": {"k": {"A": {"B": {"distance": 3.0}}}}, "c": {"k": {"*": {"A": {"distance": 2.0}, "B": None}}}}
    assert R.value(judge, "m", "k", "A", "B", "distance") == 3.0
    assert R.value(judge, "m", "k", "B", "A", "distance") is None
    assert R.value(judge, "c", "k", "B", "A", "distance") == 2.0
    assert R.value(judge, "c", "k", "A", "B", "distance") == "refused"


def test_contrast_scores_refusal_as_s_and_drops_a_refused_s():
    assert R.contrast("refused", 2.0, 4.0, "distance") == pytest.approx(math.log(2.0))
    assert R.contrast(2.0, 2.0, "refused", "distance") is None
    assert R.contrast(None, 2.0, 4.0, "distance") is None
    assert R.contrast(-0.5, 0.5, 1.0, "cross") == -1.0


def test_t_interval_means_clusters_first():
    got = R.t_interval([("a", 1.0), ("a", 3.0), ("b", 0.0), ("c", -1.0)], t90)
    assert got["mean"] == pytest.approx(1 / 3)
    assert got["clusters"] == 3 and got["closer"] == 1


def test_strata_are_even_and_ordered():
    got = R.strata({"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0, "e": 5.0, "f": 6.0})
    assert got == {"a": 0, "b": 0, "c": 1, "d": 1, "e": 2, "f": 2}


def test_overwrite_touches_only_named_knobs_and_clips():
    class D:
        module, key = "m", "k"

        def from_unit(self, u):
            return u * 10.0

    got = R.overwrite({("m", "k"): "1", ("m", "other"): "2"}, [(D(), 0)], np.array([0.9]), np.array([0.5]))
    assert got[("m", "other")] == "2"
    assert float(got[("m", "k")]) == 10.0
