import pytest

from learn import sep_s1b as B


def test_masks_keep_the_centre_and_drop_independent_sides():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    rng = np.random.default_rng(0)
    n = 48000 * 2
    c, a, b = (rng.standard_normal(n) * 0.1 for _ in range(3))
    inner = slice(8192, n - 8192)
    for kind in ("psi", "coh"):
        y = B.post_mask(np.stack([c, c]), kind)                   # a centred source passes
        assert np.sum((y - c)[inner] ** 2) / np.sum(c[inner] ** 2) < 0.05
        z = B.post_mask(np.stack([a, b]), kind)                   # two independent takes, one each side, fall away
        assert np.sum(z[inner] ** 2) < 0.2 * np.sum(((a + b) / 2)[inner] ** 2)


def test_competing_mask_and_split_partner():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    rng = np.random.default_rng(1)
    g = rng.standard_normal(48000)
    assert np.allclose(B.competing_mask(g, np.zeros_like(g))[4096:-4096], g[4096:-4096], atol=1e-6)
    metas = [{"i": 1, "band": "x", "section": "s1"}, {"i": 2, "band": "x", "section": "s2"},
             {"i": 3, "band": "y", "section": "s3"}, {"i": 4, "band": "x", "section": "s1"}]
    assert B.split_partner(metas[0], metas) == 2 and B.split_partner(metas[2], metas) is None


def test_split_rules_and_fold():
    assert abs(B.fold(0.0) - 1.0) < 1e-12 and 0.70 < B.fold(1.0) < 0.72
    assert not B.split_ok({"stratum": "double"}, -20, -25, -25)
    assert not B.split_ok({"stratum": "centred"}, -20, -45, -25)        # the own take too quiet
    assert B.split_ok({"stratum": "off-centre"}, -20, -30, -35)


def test_leak3():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(2)
    t, o, q = (rng.standard_normal(4800) for _ in range(3))
    assert B.leak3_db(t + 0.1 * o + 0.1 * q, t, o, q) < -15 and B.leak3_db(t + o + q, t, o, q) > 1
