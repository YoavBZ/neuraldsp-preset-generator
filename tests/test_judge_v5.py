import pytest

from learn import judge_v5 as J


def _signals():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    from scipy.signal import fftconvolve, lfilter

    rng = np.random.default_rng(1)
    sr = 48000
    t = np.arange(6 * sr) / sr
    notes = [196, 247, 294, 330, 392, 440]
    di = np.zeros(len(t))
    for i in range(24):                               # notes every 0.25 s, each decaying
        f = notes[i % len(notes)]
        a, n = int(i * 0.25 * sr), int(0.25 * sr)
        tt = np.arange(n) / sr
        di[a:a + n] += 0.3 * np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.08)
    di += 1e-4 * rng.standard_normal(len(t))
    dry = np.tanh(3 * di)
    ir = rng.standard_normal(int(1.2 * sr)) * np.exp(-np.arange(int(1.2 * sr)) / (0.3 * sr))
    wet = dry + 0.5 * fftconvolve(dry, ir)[:len(t)] / np.sqrt(np.sum(ir ** 2))
    b, a = [1.0, -0.6], [1.0]                         # a static tilt (treble up)
    tilt = lfilter(b, a, dry)
    pad = lambda x: np.r_[np.zeros(52), x][:len(t)]
    return np, pad(dry), pad(wet), pad(tilt), di


def test_carry_sees_reverb_and_flips_sign():
    np, dry, wet, tilt, di = _signals()
    fwd = J.window(dry, wet, di, start_s=1.0, end_s=6.0)
    bwd = J.window(wet, dry, di, start_s=1.0, end_s=6.0)
    assert fwd["carry"] > 0.05
    assert fwd["carry"] == pytest.approx(-bwd["carry"], abs=1e-9)


def test_carry_ignores_a_static_tilt_and_a_repeat():
    np, dry, wet, tilt, di = _signals()
    same = J.window(dry, dry.copy(), di, start_s=1.0, end_s=6.0)
    assert same["j0"] == 0 and same["carry"] == pytest.approx(0, abs=1e-9)
    eq = J.window(dry, tilt, di, start_s=1.0, end_s=6.0)
    rev = J.window(dry, wet, di, start_s=1.0, end_s=6.0)
    assert abs(eq["carry"]) < 0.25 * abs(rev["carry"])


def test_depth():
    np = pytest.importorskip("numpy")
    r = np.array([0.0, -10.0, -20.0, 5.0, 0.0])
    assert list(J.depth(r, 2)) == [0.0, 10.0, 10.0, 0.0, 5.0]


def test_fit_ties_to_the_smaller():
    items = [{"group": "a", "ear": 0, "j0": 1.0, "c": 0.0}, {"group": "b", "ear": 2, "j0": 0.5, "c": 0.2}]
    w, g = J.fit(items, lambda it, w: it["j0"] + w * it["c"])
    assert g == 1.0 and w == 3                        # 0.5 + 0.2w > 1 first at w = 3


def test_items_and_unit_move():
    its = J.items_for("clean")
    assert len(its) == 15 and {it["group"] for it in its} == set(J.GROUPS) | {J.CATCH}
    dec = next(it for it in its if it["group"] == "reverb-decay")
    assert dec["ref"] == "clean-reverb-large" and dec["alt"] == "clean-reverb-decay"

    class D:
        lo, hi = 0.0, 1.0
        to_unit = staticmethod(lambda v: v)
        from_unit = staticmethod(lambda u: u)
    assert float(J.unit_move(D, "0.5", 0.3)) == pytest.approx(0.8)
    assert float(J.unit_move(D, "0.8", 0.3)) == pytest.approx(0.5)     # up would pass the top: down
    assert float(J.unit_move(D, "0.5", 0.7)) == pytest.approx(0.0)     # down, clipped


def test_j5_refuses_where_a_half_refuses():
    h = {"j0": 1.0, "carry": -0.1}
    assert J.j5([h, h], 2) == pytest.approx(1.2)
    assert J.j5([h, None], 2) is None
