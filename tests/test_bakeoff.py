"""The model comparison's pure functions (`learn/bakeoff.py`); no audio, no models."""
import numpy as np

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
