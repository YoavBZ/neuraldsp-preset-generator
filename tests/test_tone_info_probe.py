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


def _db(seed=3, bands=96, frames=346):
    return np.random.default_rng(seed).normal(-60, 6, (bands, frames))


def test_every_cell_kept_is_the_plain_summary():
    db = _db()
    assert np.allclose(P.masked_summary(db, np.ones_like(db, bool)), P.summary(db))
    e = np.random.default_rng(4).normal(size=300)
    assert np.allclose(P.autocorr_on(e, np.ones(300, bool), P.LAGS), P.autocorr(e, P.LAGS))


def test_cells_outside_the_map_do_not_move_the_summary():
    db = _db()
    keep = np.random.default_rng(5).random(db.shape) < 0.3
    moved = np.where(keep, db, db + 40.0)
    a, b = P.masked_summary(db, keep), P.masked_summary(moved, keep)
    assert np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a, b, equal_nan=True)


def test_a_thin_band_or_group_has_no_value_and_a_half_fills_the_other():
    db = _db(bands=8, frames=200)
    keep = np.zeros_like(db, bool)
    keep[0, :P.MIN_CELLS] = True
    keep[1, :P.MIN_CELLS - 1] = True
    s = P.masked_summary(db, keep, groups=2)
    assert np.isfinite(s[0]) and np.isnan(s[1]) and np.isnan(s[2:8]).all()
    none = P.masked_summary(db, np.zeros_like(db, bool), groups=2)
    assert np.isnan(none).all()
    assert P.mean_halves(s, none)[0] == s[0]
    m = P.mean_halves(np.array([1.0, np.nan, np.nan]), np.array([3.0, 5.0, np.nan]))
    assert m[0] == 2.0 and m[1] == 5.0 and np.isnan(m[2])


def test_the_maps():
    mix = np.array([[-20.0, -20.0], [-20.0, -20.0]])
    stem = np.array([[-20.0, -23.0], [-23.5, -60.0]])
    assert P.map_stem(mix, stem).tolist() == [[True, True], [False, False]]
    assert P.map_true(mix, stem - 6.0, 6.0).tolist() == [[True, True], [False, False]]
    assert P.map_top(mix, stem, 0.5).tolist() == [[True, True], [False, False]]
    assert P.map_top(mix, stem, 0.01).sum() == 1


def test_top_ties_go_to_a_seeded_draw():
    flat = np.full((8, 50), -30.0)
    a, b, c = P.map_top(flat, flat, 0.1), P.map_top(flat, flat, 0.1), P.map_top(flat, flat, 0.1, seed=(1, 2, 0))
    assert a.sum() == 40 and np.array_equal(a, b) and not np.array_equal(a, c)
    assert a[:, 0].sum() < 8 and a.sum(1).min() > 0                       # not the lowest bands, or the first frames
    loud = flat + np.arange(50.0)
    picks = [P.map_top(loud, loud, 0.1, seed=(1, n, 0)) for n in range(40)]
    assert np.abs(np.mean(picks, 0).mean(0)[:25].mean() - np.mean(picks, 0).mean(0)[25:].mean()) < 0.03   # not by mix level
    gap = np.array([[-1.0, 0.0, 0.0, -1.0]])
    mix = np.array([[-60.0, -50.0, -40.0, -30.0]])
    assert P.map_top(mix, mix + gap, 0.5).tolist() == [[False, True, True, False]]


def test_the_true_gain_follows_the_mastering():
    assert P.true_gain_db(5.0, False, -10.0, -20.0, -30.0, 2.0) == 5.0
    from learn import pretrain_set as PS
    want = -10.0 - PS.db_sum(-20.0, -28.0)
    assert P.true_gain_db(5.0, True, -10.0, -20.0, -30.0, 2.0) == pytest.approx(want)


def test_a_lag_with_too_few_pairs_has_no_value():
    x = np.random.default_rng(6).normal(size=60)
    have = np.zeros(60, bool)
    have[:30] = True
    v = P.autocorr_on(x, have, (1, 12))
    assert np.isfinite(v[0]) and np.isnan(v[1])
    assert np.isnan(P.autocorr_on(x, np.zeros(60, bool), (1, 2))).all()
    assert (P.autocorr_on(np.ones(60), np.ones(60, bool), (1, 2)) == 0).all()


def test_means_for_the_gaps_come_from_their_own_column():
    X = np.array([[1.0, np.nan, np.nan], [3.0, 5.0, np.nan]])
    assert P.fill_means(X).tolist() == [2.0, 5.0, 0.0]


def test_a_partner_is_seeded_and_from_another_section():
    ids = list(range(40))
    secs = [i // 7 for i in ids]
    a, b = P.partners(ids, secs), P.partners(ids, secs)
    assert a == b and set(a) == set(ids)
    assert all(secs[a[i]] != secs[i] for i in ids)
    assert P.partners(ids, secs, seed=1) != a


def test_the_sign_test():
    assert P.sign_p(0, 0) == 1.0
    assert P.sign_p(5, 0) == 1 / 32
    assert P.sign_p(3, 3) == pytest.approx(21 / 32)


def test_the_placebo_inputs_follow_the_maps():
    assert set(P.MASK) == {"b", "o", "g", "t", "po", "pg", "pt", "xo"}


def _row(better=0, worse=0):
    return {"better": better, "worse": worse, "sign_p": P.sign_p(better, worse)}


def _pairs(**ahead):
    keys = ("o-b", "g-b", "t-b", "po-b", "pg-b", "pt-b", "o-po", "g-pg", "t-pt", "o-xo", "xo-b", "xo-po", "o-b|x", "o-po|x")
    return {k: _row(9, 0) if ahead.get(k.replace("-", "_").replace("|", "_")) else _row(2, 2) for k in keys}


def test_ahead_needs_the_sign_test_and_more_than_chance():
    assert not P.is_ahead(_row(5, 0)) and P.is_ahead(_row(7, 0))
    assert not P.is_ahead(_row(8, 3)) and not P.is_ahead(_row(0, 9))


def test_the_reading_map_takes_the_first_match():
    assert P.reading(_pairs()) == ("no gain shown, stop", None)
    assert P.reading(_pairs(t_b=True, t_pt=True)) == ("stem map earns a step", "t")
    assert P.reading(_pairs(g_b=True, g_pg=True, t_b=True, t_pt=True))[1] == "g"
    assert P.reading(_pairs(g_b=True))[0] == "not credited to the map, stop"  # ahead of (b), not of its placebo
    assert P.reading(_pairs(o_b_x=True, o_po_x=True, o_b=True)) == ("better map next", None)
    assert P.reading(_pairs(o_po_x=True)) == ("denser read next", None)
    assert P.reading(_pairs(o_b=True)) == ("not credited to the map, stop", None)
    # all of (o)'s lead is on heads the map's shape wins alone: not credited, however (o) reads against (xo)
    assert P.reading(_pairs(o_b=True, o_po=True, o_xo=True)) == ("not credited to the map, stop", None)


def test_the_placebo_is_the_own_mix_over_the_partners_map(monkeypatch):
    def fake(root, i, lb, gb):
        out = {}
        for h, frames in (("A", 346), ("B", 446)):
            r = np.random.default_rng([i, frames])
            M = r.normal(-40, 5, (96, frames))
            out[h] = (M, {k: r.random(M.shape) < 0.4 for k in P.MAPS})
        return out
    monkeypatch.setattr(P, "example_maps", fake)
    i, d, q = P._mask_feats((None, 1, 2, (0.0, 0.0), (0.0, 0.0)))
    own, other = fake(None, 1, 0, 0), fake(None, 2, 0, 0)
    want = P.mean_halves(*(P.masked_summary(own[h][0], other[h][1]["t"]) for h in "AB"))
    assert np.allclose(d["pt"], want, equal_nan=True)
    want = P.mean_halves(*(P.masked_summary(other[h][0], own[h][1]["o"]) for h in "AB"))
    assert np.allclose(d["xo"], want, equal_nan=True)
    want = P.mean_halves(*(P.masked_summary(own[h][0], own[h][1]["g"]) for h in "AB"))
    assert np.allclose(d["g"], want, equal_nan=True)
    assert set(d) == set(P.MASK) - {"b"} | {"all"} and i == 1 and 0.3 < q["g"][0] < 0.5


def test_pair_counts_read_each_direction():
    heads = [("a", "today", "continuous", 0), ("b", "today", "switch", 1), ("c", "pedals", "mic", 2)]
    wins = {("p", "q", 0), ("q", "p", 1)}
    c = P.pair_counts(heads, "p", "q", lambda k2, p, q, j: {"reliable": (p, q, j) in wins})
    assert (c["better"], c["worse"]) == (1, 1) and c["better_heads"] == ["a"] and c["worse_heads"] == ["b"]
    assert c["family"]["today"] == {"better": 1, "worse": 1}
