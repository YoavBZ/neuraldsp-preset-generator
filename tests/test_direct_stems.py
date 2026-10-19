"""learn/direct_stems.py: the pure parts of gate 1 (docs/direct-model-stems-plan.md)."""

import math

import pytest

np = pytest.importorskip("numpy")

from learn import direct_stems as DS  # noqa: E402


def _o(logpi, mu, ls=None, sw=(0.0,), cats=((1.0, 0.0),)):
    mu = np.asarray(mu, float)
    return (np.log(np.asarray(logpi, float)), mu, np.zeros_like(mu) if ls is None else np.asarray(ls, float),
            np.asarray(sw, float), [np.asarray(c, float) for c in cats])


def test_musdb_filter_matches_slugs():
    assert DS.is_musdb("cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3")
    assert DS.is_musdb("cambridge-femme-elecgtr5")
    assert DS.is_musdb("cambridge-Signs-ElecGtr3")
    assert not DS.is_musdb("cambridge-Passing_Ships-ElecGtr2")
    assert not DS.is_musdb("cambridge-designs-gtr")             # whole words only


def test_leak_draws_are_seeded_sorted_and_in_range():
    a = DS.leak_draws(["k2", "k1"])
    b = DS.leak_draws(["k1", "k2"])
    assert a == b and len(a["k1"]) == DS.N_LEAK
    assert all(0.0 <= v <= 6.0 for vs in a.values() for v in vs)


def test_training_stem_sets_the_leak_below_the_guitar():
    def lufs(x):                                                   # a power meter stand-in
        return 10 * math.log10(float(np.mean(np.asarray(x) ** 2)) + 1e-20)

    rng = np.random.default_rng(0)
    ref, back = rng.normal(size=4800), 3.0 * rng.normal(size=4800)
    st = DS.training_stem(ref, back, 4.0, lufs)
    leak = st - ref
    assert math.isclose(lufs(ref) - lufs(leak), 4.0, abs_tol=1e-9)
    assert np.allclose(leak / back, leak[0] / back[0])           # a scaled copy of the backing


def test_leak_gain_caps_a_silent_backing():
    assert DS.leak_gain_db(-20.0, -100.0, 3.0) == -20.0 - 3.0 - (-60.0)


def test_derangement_respects_groups_and_avoid():
    keys = list(range(12))
    p = DS.derangement_avoid(keys, lambda k: k % 2, lambda a, b: a == b, 7)
    assert sorted(p) == keys and sorted(p.values()) == keys
    assert all(a != b and a % 2 == b % 2 for a, b in p.items())
    assert p == DS.derangement_avoid(keys, lambda k: k % 2, lambda a, b: a == b, 7)
    with pytest.raises(SystemExit):
        DS.derangement_avoid([1], lambda k: 0, lambda a, b: a == b, 1, max_tries=5)


def test_movement_uses_top_components_and_masks():
    x = _o([0.7, 0.3], [[0.2, 0.5, 0.9], [0.0, 0.0, 0.0]], sw=(1.0, -1.0), cats=((2.0, 0.0),))
    y = _o([0.1, 0.9], [[0.9, 0.9, 0.9], [0.4, 0.5, 0.1]], sw=(1.0, 1.0), cats=((0.0, 2.0),))
    d, sw, mic = DS.movement(x, y, [1, 1, 0], [1, 1], [1])
    assert math.isclose(d, (0.2 + 0.0) / 2)                      # dims 0, 1 of x's comp 0 vs y's comp 1
    assert sw == 0.5 and mic == 0.0
    d0, _, _ = DS.movement(x, x, [1, 1, 1], [1, 1], [1])
    assert d0 == 0.0


def test_likelihood_shift_is_zero_on_itself_and_positive_otherwise():
    x = _o([0.5, 0.5], [[0.2, 0.2], [0.8, 0.8]], ls=[[-2, -2], [-2, -2]])
    y = _o([0.9, 0.1], [[0.5, 0.5], [0.8, 0.8]])
    assert DS.likelihood_shift(x, x, [1, 1]) == 0.0
    assert DS.likelihood_shift(x, y, [1, 1]) > 0


def test_mixture_logp_single_gaussian():
    o = _o([1.0], [[0.5, 0.5]], ls=[[0.0, 0.0]])
    lp = DS.mixture_logp(o, [0.5, 1.5], [1, 0])                  # only dim 0 counts
    assert math.isclose(lp, -0.5 * math.log(2 * math.pi))


def test_band_weighted_averages_parts_then_bands():
    rows = [("A", "p1", 1.0), ("A", "p1", 3.0), ("A", "p2", 0.0), ("B", "q", 10.0)]
    m, bm = DS.band_weighted(rows)
    assert bm == {"A": 1.0, "B": 10.0} and m == 5.5


def test_bootstrap_interval_contains_mean_and_is_seeded():
    rows = [(f"b{k}", "p", float(k)) for k in range(8)]
    s = DS.bootstrap(rows, n=500)
    assert s["lo90"] <= s["mean"] <= s["hi90"] and s["bands"] == 8
    assert s == DS.bootstrap(rows, n=500)
    assert DS.bootstrap([("b", "p", 1.0)])["lo90"] is None


def test_gate1_rules_on_toy_tables():
    pos = {"mean": 0.02, "lo90": 0.01, "hi90": 0.03}
    tie = {"mean": 0.0, "lo90": -0.01, "hi90": 0.01}
    none = {"d(a',b)-null": {"all": tie, "unseen_by_part_c": tie}, "d(a,b)-null": {"all": tie, "unseen_by_part_c": tie}}
    assert DS.gate1(none, tie) == ("MIX-ONLY", [])
    assert DS.gate1(none, pos) == ("STEM", ["audit (iii)-(i)"])
    one = {**none, "d(a,b)-null": {"all": tie, "unseen_by_part_c": pos}}
    assert DS.gate1(one, tie) == ("STEM", ["d(a,b)-null on unseen_by_part_c"])
    # an interval touching 0 is not "entirely above"
    assert DS.gate1(none, {"mean": 0.01, "lo90": 0.0, "hi90": 0.02})[0] == "MIX-ONLY"
