"""D1 (`learn/fx_d1.py`): the threshold choice and the time pick."""

import pytest

np = pytest.importorskip("numpy")
from learn import fx_d1 as D  # noqa: E402


def test_the_threshold_is_the_lowest_with_few_false_ons():
    s = np.array([0.9, 0.8, 0.6, 0.55, 0.4, 0.3, 0.7, 0.9])
    on = np.array([1, 1, 1, 1, 0, 0, 0, 0], bool)
    assert D.choose_threshold(s, on, max_false_on=0.25) == 0.75      # offs 0.4, 0.3, 0.7, 0.9: one of four at >= 0.75
    assert D.choose_threshold(s, on, max_false_on=0.0) == 0.95


def test_the_time_is_the_peak_when_the_halves_agree():
    assert D.time_pick((300.0, 310.0), 305.0, 120.0) == 305.0
    assert D.time_pick((300.0, 150.0), 305.0, 120.0) == 120.0
