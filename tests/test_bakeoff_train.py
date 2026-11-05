"""The training arms' pure functions (`learn/bakeoff_train.py`)."""
import pytest

np = pytest.importorskip("numpy")

from learn import bakeoff_train as T


def test_soft_bins_split_between_the_two_nearest_and_sum_to_one():
    p = T.soft_bins(np.array([0.0, 0.025, 0.5, 1.0]))
    assert p.shape == (4, 21)
    assert np.allclose(p.sum(-1), 1.0)
    assert p[0, 0] == 1.0 and p[3, 20] == 1.0
    assert p[1, 0] == pytest.approx(0.5) and p[1, 1] == pytest.approx(0.5)
    assert p[2, 10] == 1.0


def test_soft_bins_keep_the_label_as_their_mean():
    y = np.array([0.13, 0.37, 0.25, 0.91])
    centres = np.arange(21) / 20
    assert np.allclose(T.soft_bins(y) @ centres, y)


def test_bin_median_of_one_bin_is_its_centre():
    p = np.zeros(21)
    p[10] = 1.0
    assert T.bin_median(p) == pytest.approx(0.5)


def test_bin_median_interpolates_between_two_equal_bins():
    p = np.zeros(21)
    p[10] = p[11] = 0.5
    assert T.bin_median(p) == pytest.approx(0.525, abs=0.03)


def test_bin_median_works_on_batches_and_stays_in_range():
    p = np.random.default_rng(0).dirichlet(np.ones(21), size=(5, 3))
    m = T.bin_median(p)
    assert m.shape == (5, 3) and ((m >= 0) & (m <= 1)).all()
    edge = np.zeros(21)
    edge[0] = 1.0
    assert T.bin_median(edge) == 0.0


def test_stored_e_reads_the_record():
    assert T.stored_e({"E": 58}) == 58
