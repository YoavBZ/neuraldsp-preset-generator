import pytest

from learn import judge_v4 as V


def test_cells_reproduce_the_judge():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    from analysis.aligned import aligned_distance

    rng = np.random.default_rng(0)
    sr = 48000
    t = np.arange(4 * sr) / sr
    di = np.where((t % 1.0) < 0.6, np.sin(2 * np.pi * 196 * t), 0.0) * 0.3
    ref = np.tanh(3 * di) + 0.001 * rng.standard_normal(len(t))
    ren = np.tanh(5 * di) + 0.001 * rng.standard_normal(len(t))
    ref, ren = np.r_[np.zeros(52), ref][:len(t)], np.r_[np.zeros(52), ren][:len(t)]
    want = aligned_distance(ref, ren, di, lag=0, render_latency=52, start_s=1.0, end_s=4.0).distance
    c = V.cells(ref, ren, di, lag=0, render_latency=52, start_s=1.0, end_s=4.0)
    assert want is not None and abs(V.j0(c) - want) < 1e-9


def test_cross_group_gamma():
    items = [{"group": "a", "ear": 0, "s": 1.0}, {"group": "b", "ear": 2, "s": 2.0},
             {"group": "a", "ear": 2, "s": 0.5}, {"group": "b", "ear": 1, "s": 3.0}]
    # cross-group pairs with different ears: (a0,b2) +, (a0,b1) +, (b2,a2) skipped (same ear), (a2,b1) -
    assert V.cross_group_gamma(items, lambda it: it["s"]) == pytest.approx(1 / 3)
    assert V.cross_group_gamma(items[:1], lambda it: it["s"]) != V.cross_group_gamma(items[:1], lambda it: it["s"])


def test_note_windows():
    np = pytest.importorskip("numpy")
    hop, sr = 512, 48000
    p = np.zeros(400, bool)
    p[10:50] = True
    p[60:100] = True                                  # a gap of 10 frames (~0.11 s): too short
    p[200:240] = True                                 # then a long gap before the end
    w = V.note_windows(p, hop, sr)
    assert len(w) == 2                                 # after 50 (gap to 60 too short) dropped; 100 and 240 kept
    o, e, s = w[0]
    assert (o, e) == (60, 100) and s == min(100 + round(1.5 * sr / hop), 200)


def test_band_edges_and_bark():
    np = pytest.importorskip("numpy")
    e = V.band_edges([100.0, 200.0, 400.0])
    assert list(e) == [50.0, 150.0, 300.0, 500.0]
    assert abs(float(V.bark_to_hz(8.5)) - 1000) < 60
