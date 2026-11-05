"""The model comparison's pure functions (`learn/bakeoff.py`); no audio, no models."""
import numpy as np
import pytest

from learn import bakeoff as B


def test_pooled_gives_band_means_then_stds():
    x = np.array([[[0.0, 2.0], [1.0, 1.0]]])
    assert B.pooled(x).tolist() == [[1.0, 1.0, 1.0, 0.0]]


def test_inner_folds_keep_a_cluster_whole():
    clusters = ["a", "b", "a", "c", "b", "d"]
    f = B.inner_folds(clusters)
    assert f[0] == f[2] and f[1] == f[4]
    assert B.inner_folds(clusters).tolist() == f.tolist()


def test_centre_within_uses_stored_means_and_falls_back():
    v = np.array([[1.0], [3.0], [10.0]])
    out, means = B.centre_within(v, ["x", "x", "y"])
    assert out.ravel().tolist() == [-1.0, 1.0, 0.0]
    new, _ = B.centre_within(np.array([[2.0], [6.0]]), ["x", "z"], means)
    assert new.ravel().tolist() == [0.0, 0.0]          # z's fallback: the mean of the means, 6


def test_cell_centres_ignore_masked_rows():
    c = np.array([[0.2, 0.9], [0.4, 0.1], [1.0, 1.0]])
    m = np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
    got = B.cell_centres(c, m, ["x", "x", "y"])
    assert np.allclose(got["x"], [0.3, 0.5])
    assert np.allclose(got["y"], [1.0, 0.5])


def test_pca_is_capped_by_rows():
    m, comp = B.pca(np.random.default_rng(0).normal(size=(4, 10)), k=24)
    assert comp.shape == (3, 10) and m.shape == (10,)


def test_ridge_recovers_a_line_both_ways_round():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(200, 3))
    w = np.array([1.0, -2.0, 0.5])
    assert np.allclose(B.ridge(X, X @ w, 1e-6), w, atol=1e-5)
    wide = rng.normal(size=(5, 20))                    # fewer rows than columns goes through the dual
    y = wide @ np.ones(20)
    assert np.allclose(wide @ B.ridge(wide, y, 1e-8), y, atol=1e-4)


def test_choose_alpha_prefers_heavy_shrinkage_on_noise():
    rng = np.random.default_rng(2)
    X, y = rng.normal(size=(400, 8)), rng.normal(size=400)
    clusters = [str(i // 10) for i in range(400)]
    assert B.choose_alpha(X, y, clusters) >= 1000


def test_gaussian_output_has_reads_v3s_shape_and_a_floor():
    o = B.gaussian_output(np.zeros((2, 5)), np.array([0.5, 0.0, 0.5, 0.5, 0.5]), 3, (2, 10))
    assert [a.shape for a in o] == [(2, 1), (2, 1, 5), (2, 1, 5), (2, 3), (2, 2, 10)]
    assert np.isclose(np.exp(o[2][0, 0, 1]), B.SD_FLOOR)


def test_family_null_counts_draws_at_or_above():
    assert B.family_null({"tone": [0.1, 0.2, 0.3, 0.4]})("tone", 0.3) == 0.5


def test_unique_rows_keeps_each_record_once():
    rows = [{"real": "u", "amp": "a"}, {"real": "u", "amp": "a"}, {"real": "u", "amp": "b"}]
    recs = [{"di": 1}, {"di": 2}, {"di": 3}]
    r, q = B.unique_rows(rows, recs)
    assert len(r) == 2 and [x["di"] for x in q] == [1, 3]


def test_shuffled_within_stays_inside_its_cell():
    c = np.arange(6.0)[:, None]
    cm = np.ones((6, 1))
    got, _ = B.shuffled_within(c, cm, ["x", "x", "x", "y", "y", "y"], 3)
    assert sorted(got[:3].ravel().tolist()) == [0.0, 1.0, 2.0]
    assert sorted(got[3:].ravel().tolist()) == [3.0, 4.0, 5.0]


def test_rrr_recovers_a_rank_two_map_and_keeps_its_shape():
    rng = np.random.default_rng(4)
    Z = rng.normal(size=(300, 6))
    Y = Z[:, :2] @ rng.normal(size=(2, 9))
    clusters = [str(i // 10) for i in range(300)]
    got = B.rrr_fit(Z, Y, clusters, rank=2)(Z)
    assert got.shape == Y.shape and np.corrcoef(got.ravel(), Y.ravel())[0, 1] > 0.99


def test_max_t_lower_widens_as_contrasts_join():
    rng = np.random.default_rng(5)
    one = rng.normal(size=(4000, 1))
    many = rng.normal(size=(4000, 30))
    low1, q1 = B.max_t_lower(one, np.zeros(1))
    lowN, qN = B.max_t_lower(many, np.zeros(30))
    assert q1 == pytest.approx(1.645, abs=0.1)
    assert qN > 2.5 and lowN[0] < low1[0]


def test_declared_bound_uses_only_declared_labels():
    known = {*B.BASE, *B.CANDIDATES}
    assert all(a in known and b in known for a, b, _, _ in B.BOUND)
    assert all(a in known and b in known for a, b in B.PAIRS)
    assert len(B.CANDIDATES) == 16 and len(B.BOUND) == 30
