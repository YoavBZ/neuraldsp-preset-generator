import math

import pytest

from learn import sep_s0 as S


def test_pan_law_and_strata():
    l, r = S.pan(0.0)
    assert abs(l - r) < 1e-12 and abs(l * l + r * r - 1) < 1e-12 and S.pan(-1.0) == (1.0, 0.0)
    seen = {S.draw_stratum(i)["stratum"] for i in range(60)}
    assert seen == set(S.STRATA)
    for i in range(60):
        d = S.draw_stratum(i)
        if d["stratum"] == "centred":
            assert abs(d["target"][0]) <= 0.15 and 0.6 <= abs(d["others"]) <= 1.0
        elif d["stratum"] == "off-centre":
            assert 0.4 <= abs(d["target"][0]) <= 0.8
        else:
            assert d["target"][0] > 0 > d["target"][1] and 12 <= d["target_offset_ms"] <= 30
    assert S.draw_stratum(7) == S.draw_stratum(7)


def test_backing_pan_centres_the_rhythm_section():
    import random

    rng = random.Random(0)
    assert S.backing_pan("03_Kick.wav", rng) == 0.0 and S.backing_pan("10_LeadVox.wav", rng) == 0.0
    assert abs(S.backing_pan("20_Keys.wav", rng)) <= 0.5


def test_metrics():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(0)
    t, o = rng.standard_normal(4800), rng.standard_normal(4800)
    assert S.si_sdr(2 * t, t) > 100
    assert abs(S.si_sdr(t + o, t)) < 0.5                         # equal power noise: about 0 dB
    assert S.leak_db(t + 0.1 * o, t, o) < -15 and S.leak_db(t + o, t, o) > -1
    b = S.band_boot([1.0, 1.0, 1.0, 1.0], ["a", "a", "b", "b"])
    assert b["mean"] == 1.0 and b["lo90"] == 1.0 and b["bands"] == 2


def test_linked_gain_draws_as_compress_does():
    np = pytest.importorskip("numpy")
    import random

    x = np.sin(np.linspace(0, 200, 48000)) * np.linspace(0.01, 1, 48000)
    r1, r2 = random.Random(5), random.Random(5)
    g, mk = S.linked_gain(x, r1, 48000)
    assert r1.random() == (r2.uniform(2, 4), r2.uniform(0, 4), r2.random())[2]   # the same two draws consumed
    assert g.max() <= 1.0 and 0 <= mk <= 4
