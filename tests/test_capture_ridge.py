"""N9b's pure parts (`learn/capture_ridge.py`)."""

import pytest

np = pytest.importorskip("numpy")

from learn import capture_ridge as C  # noqa: E402


def test_a_unit_counts_once_in_a_ridge():
    rows = [{"real": "a", "i": 1}, {"real": "b", "i": 2}, {"real": "a", "i": 3}]
    assert C.unique_rows(rows) == [{"real": "a", "i": 1}, {"real": "b", "i": 2}]


def test_answers_join_by_recording_and_amp_or_refuse():
    rows = [{"rec": "r", "amp": "ac20"}]
    key = lambda r: (r["rec"], r["amp"])  # noqa: E731
    assert C.join_answers(rows, key, {("r", "ac20"): {"M-cap_ans": 1}})[0]["M-cap_ans"] == 1
    with pytest.raises(SystemExit, match="no answer"):
        C.join_answers(rows, key, {})


def test_the_arms_are_n9s_rows():
    assert set(C.ARMS.values()) <= set(C.CT.ARMS)
