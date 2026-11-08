import math

import pytest

np = pytest.importorskip("numpy")

from learn import judge_screen as J


def rig(lag, n=48000 * 10, seed=3):
    """A DI of plucked bursts, a render that lags it by the plugin's latency, and a reference that lags the render by `lag`."""
    rng = np.random.default_rng(seed)
    di = np.zeros(n)
    for start in range(4800, n - 48000, 24000):
        k = np.arange(19200)
        di[start:start + len(k)] = rng.standard_normal(len(k)) * np.exp(-k / 6000)
    ren = np.concatenate([np.zeros(52), np.tanh(3 * di)[:-52]])
    ref = np.zeros(n)
    lo, hi = max(0, lag), min(n, n + lag)
    ref[lo:hi] = 0.8 * ren[lo - lag:hi - lag] + 0.01 * rng.standard_normal(hi - lo)
    return ref, ren, di


@pytest.mark.parametrize("lag", [-30, 0, 27])
def test_a_placed_clip_judges_as_the_whole_render_does(lag):
    pytest.importorskip("scipy")
    from analysis import aligned as A
    from learn import ear_vreal as E

    ref, ren, di = rig(lag)
    a, b = 48000, 264000
    whole = A.aligned_distance(ref, ren, di, lag=lag, render_latency=52, start_s=a / 48000, end_s=b / 48000).distance
    s0, s1 = E.window(a, b, len(ref), len(ren), lag)
    y = J.placed(ren[s0 - lag:s1 - lag].astype(np.float32), s0, s1, len(ref))
    start, end = J.window_s(s0, s1)
    again = A.aligned_distance(ref, y, J.shifted(di, lag), lag=0, render_latency=52, start_s=start, end_s=end).distance
    assert abs(math.log(again / whole)) < J.CONTROL_TOL


def test_shifted_moves_the_di_by_the_lag():
    di = np.arange(10.0)
    assert J.shifted(di, -2).tolist() == [2, 3, 4, 5, 6, 7, 8, 9, 0, 0]
    assert J.shifted(di, 3).tolist() == [0, 0, 0, 0, 1, 2, 3, 4, 5, 6]
    s0, s1 = 48001, 263970
    a, b = J.window_s(s0, s1)
    assert (int(a * J.SR), int(b * J.SR)) == (s0, s1)


def test_agreement_counts_ties_as_half():
    assert J.agreement(1.0, 2.0, True) == 1.0
    assert J.agreement(1.0, 2.0, False) == 0.0
    assert J.agreement(2.0, 2.0, True) == 0.5


def card(page, cluster, ear, d):
    return {"page": page, "id": cluster + page, "cluster": cluster, "ear": ear, "d": d}


def test_pairs_take_closeness_where_it_differs_and_drop_labels():
    ear = {"S": {"rank": 3, "close": 0}, "FTm": {"rank": 1, "close": 2}, "M-pcs": {"rank": 2, "close": 2}, "label": {"rank": 4, "close": 3}}
    d = {"J0": {"S": 3.0, "FTm": 2.0, "M-pcs": 1.9, "label": 1.0}, "v2": {"S": 3.0, "FTm": 1.0, "M-pcs": None, "label": 1.0}}
    rows = J.pairs_of([card("N12", "x", ear, d)], ("v2",))
    assert {(r["a"], r["b"]) for r in rows} == {("S", "FTm"), ("S", "M-pcs"), ("FTm", "M-pcs")}
    by = {(r["a"], r["b"]): r for r in rows}
    assert by[("S", "FTm")]["heard"] and by[("S", "FTm")]["agree"]["J0"]["close"] == 1.0
    assert not by[("FTm", "M-pcs")]["heard"] and by[("FTm", "M-pcs")]["agree"]["J0"]["rank"] == 0.0
    assert by[("S", "M-pcs")]["agree"]["v2"]["close"] is None and by[("S", "M-pcs")]["agree"]["v2"]["rank"] is None
    assert by[("FTm", "M-pcs")]["models"] and not by[("S", "FTm")]["models"]
    assert len(J.pairs_of([card("N12", "x", ear, d)], ("v2",), drop=())) == 6


def test_jackknife_on_equal_clusters_and_holm():
    t90 = lambda df: 2.0  # noqa: E731
    rows = [{"cluster": c, "v": v} for c, v in (("a", 1.0), ("a", 0.0), ("b", 1.0), ("c", 0.0))]
    got = J.jackknife(rows, lambda r: r["v"], t90)
    assert got["mean"] == 0.5 and got["clusters"] == 3 and got["df"] == 2
    thetas = [1 / 2, 1 / 3, 2 / 3]
    tb = sum(thetas) / 3
    assert math.isclose(got["se"], math.sqrt(2 / 3 * sum((t - tb) ** 2 for t in thetas)))
    assert J.holm({"a": 0.01, "b": 0.04, "c": 0.03}) == {"a": 0.03, "c": 0.06, "b": 0.06}


def test_named_takes_the_highest_mean_above_zero_with_the_declared_ties():
    assert J.named({"v2": {"mean": 0.02, "holm": 1}, "v3": {"mean": 0.05, "holm": 1}, "J5": None}, {}) == "v3"
    assert J.named({"v2": {"mean": -0.02}, "v3": {"mean": 0.0}}, {}) is None
    tie = {"v2": {"mean": 0.025, "holm": 0.5}, "v3": {"mean": 0.025, "holm": 0.2}}
    assert J.named(tie, {"v2": {"mean": 0.01}, "v3": {"mean": 0.0}}) == "v2"
    assert J.named(tie, {"v2": {"mean": 0.0}, "v3": {"mean": 0.0}}) == "v3"
    assert J.named({"v3": {"mean": 0.01, "holm": 1}, "v2": {"mean": 0.01, "holm": 1}}, {}) == "v2"


def test_s_last_puts_s_farthest_and_keeps_j0_otherwise():
    c = {"d": {"J0": {"S": 1.0, "FTm": 2.0, "M-pcs": 3.0}}}
    got = J.s_last(c)
    assert got["S"] > got["M-pcs"] > got["FTm"]
