"""N10's pure parts (`learn/reads_fresh.py`)."""

import pytest

np = pytest.importorskip("numpy")

from learn import reads_fresh as F  # noqa: E402


def test_a_label_is_averaged_over_its_fold_models():
    a = [{"amp": "ac20", "x_ans": np.array([0.0, 2.0]), "x_swap": np.array([1.0])}, {"amp": "pr12", "x_ans": np.array([1.0, 1.0]), "x_swap": None}]
    b = [{"amp": "ac20", "x_ans": np.array([2.0, 0.0]), "x_swap": np.array([3.0])}, {"amp": "pr12", "x_ans": np.array([3.0, 3.0]), "x_swap": None}]
    got = F.mean_folds([a, b], "x")
    assert got[0]["x_ans"].tolist() == [1.0, 1.0] and got[0]["x_swap"].tolist() == [2.0]
    assert got[1]["x_ans"].tolist() == [2.0, 2.0] and got[1]["x_swap"] is None


def test_the_set_reads_as_one_fold():
    assert {r["fold"] for r in F.one_fold([{"fold": 2}, {"fold": 3}])} == {0}


def test_the_primary_pairs_are_the_capture_rows():
    assert F.PAIRS[0] == ("C-cap", "C-ctl") and F.PAIRS[1] == ("M-cap", "M-ctl")
