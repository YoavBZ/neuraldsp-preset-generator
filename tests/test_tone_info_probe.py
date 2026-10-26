"""The tone-information probe's pure parts (`learn/tone_info_probe.py`, `docs/tone-info-probe.md`)."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import tone_info_probe as P  # noqa: E402


def test_summary_has_a_fixed_length_and_reads_a_delay():
    rng = np.random.default_rng(0)
    db = rng.normal(-60, 3, (96, 446))
    assert P.summary(db).shape == (96 * 6 + 8 * (len(P.LAGS) + 4) + 4,)
    e = np.zeros(400)
    e[::40] = 1.0
    ac = P.autocorr(e, P.LAGS)
    assert ac[P.LAGS.index(40)] > 0.9 and abs(ac[P.LAGS.index(22)]) < 0.2
    assert np.all(P.autocorr(np.ones(50), (1, 2)) == 0)


def test_rich_bands_cover_every_band():
    b = P.rich_bands()
    assert len(b) == P.RICH["bands"] and all(len(ix) >= 1 for ix in b)


def test_group_folds_keep_sections_whole():
    g = np.repeat(np.arange(13), np.arange(1, 14))
    folds = P.group_folds(g)
    assert len(folds) == P.FOLDS
    assert sorted(np.concatenate(folds).tolist()) == list(range(len(g)))
    seen = [set(g[f].tolist()) for f in folds]
    assert all(not (a & b) for n, a in enumerate(seen) for b in seen[n + 1:])


def test_ridge_matches_the_closed_form_and_shrinks_to_the_mean():
    rng = np.random.default_rng(1)
    X, Y = rng.normal(size=(60, 5)), rng.normal(size=(60, 2))
    r = P.Ridge(X, Y)
    Xc, Yc = X - X.mean(0), Y - Y.mean(0)
    w = np.linalg.solve(Xc.T @ Xc + 3.0 * np.eye(5), Xc.T @ Yc)
    assert np.allclose(r.predict(X, 3.0), Xc @ w + Y.mean(0))
    assert np.allclose(r.predict(X, 1e12), Y.mean(0), atol=1e-6)


def test_paired_auc_difference_is_zero_for_the_same_scores():
    rng = np.random.default_rng(2)
    y = rng.random(80) > 0.5
    q = rng.random(80)
    g = np.repeat(np.arange(8), 10)
    st = P.paired_jackknife_auc(y, q, q, g)
    assert st["point"] == 0 and st["lo"] == 0 and st["hi"] == 0
    better = P.paired_jackknife_auc(y, y + 0.1 * q, q, g)
    assert better["lo"] > 0


def test_attribution_follows_the_declared_order():
    steps = {"mix": False, "separator": False}
    rd = {k: False for k in P.INPUTS}
    assert P.attribute({**rd, "c": True}, steps) == "survives"
    assert P.attribute({**rd, "e": True, "d": True}, steps) == "richer features"
    assert P.attribute({**rd, "d": True}, steps) == "needs the DI"
    assert P.attribute(rd, steps) == "not carried"
    a = {**rd, "a": True}
    assert P.attribute(a, {"mix": True, "separator": False}) == "mix"
    assert P.attribute(a, {"mix": False, "separator": True}) == "separator"
    assert P.attribute(a, {"mix": True, "separator": True}) == "both"
    assert P.attribute(a, steps) == "unresolved"


def test_level_removed_shifts_only_the_level_entries():
    rng = np.random.default_rng(3)
    A = rng.normal(size=(4, 740))
    An = P.level_removed(A, [1.0, 2.0, 3.0, 4.0])
    moved = np.where(~np.isclose(An, A).all(0))[0].tolist()
    assert moved == list(P.LEVEL_IX)
    assert np.allclose(A[:, 736] - An[:, 736], [1, 2, 3, 4])
