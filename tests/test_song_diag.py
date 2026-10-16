"""Experiment 1's rules, guards and readings (`learn/song_diag.py`), on synthetic inputs only.
Nothing here renders, draws from the real catalogue or loads a stored model."""

import json
import math
import random

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import knob_ceiling as K  # noqa: E402
from learn import song_diag as D  # noqa: E402

INF = math.inf


# ------------------------------------------------------------------------------ helpers

def S_for(amp):
    """A synthetic start: every setting in the amp's space at a mid value, both cabs on."""
    S = {("cabParameters", "leftCabActive"): "true"}
    for d in K.space(amp, S):
        S[(d.module, d.key)] = K.fmt(d.from_unit(0.5)) if d.kind in ("cont", "log") else d.values[0]
    return S


def win(band, fold, path, start):
    return {"band": band, "fold": fold, "path": path, "start": start}


def unit(fold=0, band="b0", target=0, search="A", typ="broad", dS=1.0, d=None, s=None, knob=None, mics=None,
         keys=None):
    """A unit with d_S, d_T = 0 and given held (d) and search (s) distances."""
    dd = {"target": 0.0, "target_repeat": 0.0, "S": dS, "median": dS}
    dd.update(d or {})
    ss = {n: 1.0 for n in dd}
    ss.update(s or {})
    return {"fold": fold, "band": band, "target": target, "type": typ, "search": search,
            "held": "B" if search == "A" else "A", "d": dd, "s": ss,
            "key": keys or {n: n for n in dd}, "knob": knob or {n: 0.0 for n in dd},
            "mic_match": mics or {n: True for n in dd}}


def good_unit(fold, band, target, search="A", view="1b", k=8, close=True, typ="broad"):
    """A unit where (if close) the top mean and the MDN pick close 80% and beat every baseline."""
    v = 0.2 if close else 0.9
    d = {f"{view}:{search}:top": v, "median": 0.95}
    s = {}
    for j in range(k):
        d[f"{view}:{search}:s{j}"] = v if j == 0 else 0.99
        s[f"{view}:{search}:s{j}"] = 0.1 if j == 0 else 0.9
    for j in range(8):
        d[f"rand{j}"] = d[f"jS{j}"] = 0.9
    for j in range(4):
        d[f"jTc{j}"] = 0.3
    return unit(fold, band, target, search, typ, d=d, s=s)


def fold_units(fold, n_close, n_far, bands=("x", "y"), view="1b", k=8):
    us = []
    for i in range(n_close + n_far):
        us.append(good_unit(fold, bands[i % len(bands)], i, view=view, k=k, close=i < n_close))
    return us


# ------------------------------------------------------------------------------ the draw

def test_eligible_windows_excludes_tracks_bands_and_guitar_techs():
    fold_of = {"A": 0, "B": 1, "Eggy": 3}
    ws = [win("A", 0, "a.wav", 0), win("A", 0, "kc.wav", 0), win("Eggy", 3, "e.wav", 0),
          win("Guitar-TECHS P1", "all", "p1.wav", 0), win("B", 1, "b.wav", 0)]
    out = D.eligible_windows(ws, fold_of, {"kc.wav"}, set(D.STEP5_BANDS))
    assert [w["path"] for w in out] == ["a.wav", "b.wav"]


def test_eligible_windows_asserts_the_band_fold():
    with pytest.raises(AssertionError):
        D.eligible_windows([win("A", 1, "a.wav", 0)], {"A": 0}, set(), set())


def test_exclusions_require_every_knob_ceiling_part():
    cat = {"p1": {"di": "d1", "crop": "/c/p1"}, "p2": {"di": "d2", "crop": None}}
    tr, cr, bands = D.exclusions(cat, ["p1", "p2"])
    assert tr == {"d1", "d2"} and cr == {"/c/p1"} and "Eggy" in bands
    with pytest.raises(AssertionError):
        D.exclusions(cat, ["p1", "missing"])


def test_window_order_is_seeded_round_robin_without_replacement():
    by = {0: [win(b, 0, f"{b}.wav", s * D.WIN_LEN) for b in ("x", "y") for s in range(3)]}
    o1, o2 = D.window_order(by), D.window_order(by)
    assert o1 == o2
    seq = o1[0]
    assert len(seq) == 6 and len({(w["path"], w["start"]) for w in seq}) == 6
    assert [w["band"] for w in seq[:2]] in (["x", "y"], ["y", "x"])          # bands in turn
    assert seq[0]["band"] != seq[1]["band"] and seq[2]["band"] != seq[3]["band"]


def test_round_robin_band_that_runs_out_passes_its_turn():
    by = {0: [win("x", 0, "x.wav", 0)] + [win("y", 0, "y.wav", s * D.WIN_LEN) for s in range(3)]}
    seq = D.window_order(by)[0]
    assert sum(w["band"] == "x" for w in seq) == 1 and len(seq) == 4


def test_pick_windows_skips_any_overlap():
    hop = int(5.0 * D.SR)
    seq = [win("x", 0, "t.wav", i * hop) for i in range(6)]          # 10.25-s windows on a 5-s hop
    got = D.pick_windows(seq, 10)
    assert [w["start"] for w in got] == [0, 3 * hop]                  # starts ≥ 10.25 s apart
    assert not any(D.overlaps(a, b) for i, a in enumerate(got) for b in got[i + 1:])
    assert D.pick_windows(seq, 10, taken=[win("x", 0, "t.wav", 0)])[0]["start"] == 3 * hop


def test_target_attrs_are_per_target_alternate_types_and_avoid_the_own_song(tmp_path):
    w = win("x", 0, "di.wav", 0)
    back = [("x", 0, "own/backing.wav"), ("y", 0, "other/backing.wav"), ("z", 1, "f1/backing.wav")]
    song_of = {"di.wav": "songA", "own/backing.wav": "songA", "other/backing.wav": "songB", "f1/backing.wav": "s"}
    opt = {0: [("pr12", "clean", "own-fold.json")], 1: [(a, c, f"f1-{a}-{c}.json") for a in K.AMPS
                                                        for c in ("clean", "crunch")]}
    ts = [D.target_attrs(i, 0, j, w, back, song_of, opt, None) for i, j in enumerate(range(6))]
    assert [t["type"] for t in ts] == ["broad", "ks_prior"] * 3
    assert all(t["backing"] == "other/backing.wav" for t in ts)
    assert all(t["centre"].startswith("f1-") for t in ts if t["type"] == "ks_prior")
    again = D.target_attrs(99, 0, 3, w, back, song_of, opt, None)
    assert {k: again[k] for k in ("amp", "class", "centre", "seed")} == {k: ts[3][k] for k in ("amp", "class", "centre",
                                                                                                  "seed")}
    with pytest.raises(AssertionError):
        D.target_attrs(0, 0, 0, w, [("x", 0, "own/backing.wav")], song_of, opt, None)


def test_assert_fold_clean_catches_a_leak():
    t = {"i": 0, "fold": 1, "window": {"path": "a.wav"}, "backing": "b.wav"}
    D.assert_fold_clean([t], [{"fold": 1, "window": {"path": "a.wav"}, "backing": "b.wav"},
                              {"fold": 0, "window": {"path": "z.wav"}, "backing": "y.wav"}])
    with pytest.raises(AssertionError):
        D.assert_fold_clean([t], [{"fold": 0, "window": {"path": "a.wav"}, "backing": "y.wav"}])
    with pytest.raises(AssertionError):
        D.assert_fold_clean([t], [{"fold": 2, "window": {"path": "z.wav"}, "backing": "b.wav"}])


def test_broad_and_jitter_settings():
    S = S_for("sw50r")
    dims = K.space("sw50r", S)
    x, lab = D.broad(dims, S, random.Random(1))
    assert all(0 <= lab[d.name] <= 1 for d in dims if d.kind in ("cont", "log"))
    target = D.broad(dims, S, random.Random(2))[0]
    cats = [(d.module, d.key) for d in dims if d.kind in ("cat", "switch")]
    for seed in range(20):
        xc, _ = D.jitter(dims, S, target, random.Random(seed), 1.0)
        assert all(xc[k] == target[k] for k in cats)                       # continuous-only
    changed = sum(any(D.jitter(dims, S, target, random.Random(s), D.KEEP_P)[0][k] != target[k] for k in cats)
                  for s in range(200))
    assert changed > 100                                                    # bank-style changes cats often


# ------------------------------------------------------------------------------ the sampler

def heads(K_=3, n=None, seed=0):
    CONT, SW, CAT, MICS = D._layout()
    n = len(CONT) if n is None else n
    r = np.random.default_rng(seed)
    pi = r.random(K_)
    return {"pi": pi / pi.sum(), "mu": r.random((K_, n)), "sigma": r.uniform(0.05, math.e, (K_, n)),
            "sw_p": r.random(len(SW)), "mic_p": [r.dirichlet(np.ones(10)) for _ in CAT]}


def test_truncnorm_stays_in_range_even_with_wide_sigma():
    r = np.random.default_rng(0)
    v = [D.truncnorm(r, 0.95, math.e) for _ in range(2000)]
    assert min(v) >= 0 and max(v) <= 1
    vv = D.truncnorm_vec(r, np.array([0.0, 1.0, 0.5]), np.array([math.e, 2.0, 0.01]), 500)
    assert vv.shape == (500, 3) and vv.min() >= 0 and vv.max() <= 1
    assert sum(x >= 0.99 for x in v) / len(v) < 0.1                       # no pile-up at the limit


def test_sample_units_seeded_and_component_by_pi():
    h = heads(seed=1)
    a = D.sample_units(h, D.sample_rng(7, "1b", "A"))
    b = D.sample_units(h, D.sample_rng(7, "1b", "A"))
    c = D.sample_units(h, D.sample_rng(7, "1b", "B"))
    assert a == b and a != c
    assert all(0 <= u <= 1 for u in a[0])
    h1 = dict(h, pi=np.array([0.0, 1.0, 0.0]), sigma=np.full_like(h["sigma"], 1e-4))
    cont, _, _ = D.sample_units(h1, np.random.default_rng(0))
    assert np.allclose(cont, np.clip(h1["mu"][1], 0, 1), atol=1e-3)


def test_top_and_mixture_mean():
    S = S_for("pr12")
    h = heads(seed=2)
    CONT, SW, CAT, MICS = D._layout()
    x = D.top_mean_settings(h, "pr12", S)
    top = int(np.argmax(h["pi"]))
    d = next(dd for dd in K.space("pr12", S) if dd.name == "pr12Amp/pr12Treble")
    assert x[(d.module, d.key)] == K.fmt(d.from_unit(float(h["mu"][top][CONT.index(d.name)])))
    m = D.mixture_mean_settings(h, "pr12", S)
    mean = (h["pi"][:, None] * h["mu"]).sum(0)[CONT.index(d.name)]
    assert m[(d.module, d.key)] == K.fmt(d.from_unit(float(mean)))


def test_mode_separation_and_collapse_flag():
    n = 3
    same = {"pi": np.array([0.5, 0.5]), "mu": np.full((2, n), 0.4), "sigma": np.full((2, n), 0.1)}
    apart = {"pi": np.array([0.5, 0.5]), "mu": np.array([[0.1] * n, [0.9] * n]), "sigma": np.full((2, n), 0.1)}
    assert D.mode_separation(same) == 0
    assert D.mode_separation(apart) == pytest.approx(4.0)
    assert D.mode_separation(apart, [True, False, False]) == pytest.approx(4.0)
    assert D.collapse_flag({0: 0.1, 1: 0.2, 2: 0.49, 3: 2.0})
    assert not D.collapse_flag({0: 0.1, 1: 0.2, 2: 0.5, 3: 2.0})                 # 0.5 is not below
    assert D.effective_components([1, 0, 0]) == pytest.approx(1)
    assert D.effective_components([0.25] * 4) == pytest.approx(4)


def test_pit_tarp_and_ece_on_calibrated_inputs():
    r = np.random.default_rng(0)
    pits = [D.pit_truncated([1.0], [0.3], [0.2], D.truncnorm(r, 0.3, 0.2)) for _ in range(3000)]
    s = D.pit_summary(pits)
    assert s["n"] == 3000 and s["max_dev"] < 0.03
    truths = r.random((400, 3))
    samples = r.random((400, 100, 3))                                        # prior = posterior here
    t = D.tarp(samples, truths, np.random.default_rng(1))
    assert abs(t["atc"]) < 1.0
    p = r.random(5000)
    assert D.ece(p, r.random(5000) < p) < 0.03
    assert D.ece([0.9] * 100, [0] * 100) == pytest.approx(0.9)


# ------------------------------------------------------------------------------ candidates

def test_baselines_counts_names_and_per_target_seed():
    S = S_for("ac20")
    dims = K.space("ac20", S)
    target = D.broad(dims, S, random.Random(3))[0]
    bank = [D.sj(D.broad(dims, S, random.Random(100 + i))[0]) for i in range(20)]
    t = {"amp": "ac20"}
    b1 = D.baselines(t, S, target, bank, D.baseline_rng(5))
    b2 = D.baselines(t, S, target, list(reversed(bank)), D.baseline_rng(5))
    assert sorted(b1) == sorted([f"rand{k}" for k in range(8)] + [f"jS{k}" for k in range(8)]
                                + [f"jTc{k}" for k in range(4)] + [f"jTb{k}" for k in range(4)])
    assert {k: D.sj(v) for k, v in b1.items()} == {k: D.sj(v) for k, v in b2.items()}
    cats = [(d.module, d.key) for d in dims if d.kind in ("cat", "switch")]
    assert all(b1[f"jTc{k}"][c] == target[c] for k in range(4) for c in cats)
    with pytest.raises(AssertionError):
        D.baselines(t, S, target, bank[:3], D.baseline_rng(5))


def test_model_candidates_names_and_sample_counts():
    S = S_for("pr12")
    hs = {(v, h): heads(seed=i) for i, (v, h) in enumerate((v, h) for v in D.VIEWS for h in "AB")}
    c = D.model_candidates(hs, 3, "pr12", S)
    for h in "AB":
        assert sum(n.startswith(f"1a:{h}:s") for n in c) == 4
        assert sum(n.startswith(f"1b:{h}:s") for n in c) == 8
        assert f"1b:{h}:mixmean" in c and f"1a:{h}:mixmean" not in c
    assert len(c) == 2 * (1 + 4) + 2 * (1 + 8 + 1)                          # 30 per target


def test_render_plan_dedupes_but_always_repeats_the_target():
    S = S_for("pr12")
    c = {"target": S, "target_repeat": S, "S": S, "a": S_for("pr12")}
    first, of = D.render_plan(c)
    assert len(first) == 2 and of["target_repeat"] != of["target"] and of["S"] == of["target"] == of["a"]
    assert D.planned_renders([c], n_sens=10, n_pre=0) == 12
    assert D.budget_ok(8200) and not D.budget_ok(8201)


def test_full_candidate_set_is_59_renders_at_most():
    n = 2 + 1 + 10 + 20 + 2 + 8 + 8 + 8
    assert n == 59 and 120 * n == 7080


# ------------------------------------------------------------------------------ sensitivity

def test_sens_moves_counts_and_direction():
    counts = {amp: len(D.sens_moves(amp, S_for(amp))) for amp in K.AMPS}
    assert counts == {"pr12": 10, "sw50r": 15, "ac20": 12}                   # + the base: 11, 16, 13
    S = S_for("pr12")
    d = next(dd for dd in K.space("pr12", S) if dd.name == "parameters/inputGain")
    lo = dict(S)
    lo[(d.module, d.key)] = K.fmt(d.from_unit(0.1))
    assert d.to_unit(D.sens_moves("pr12", lo)[d.name][(d.module, d.key)]) == pytest.approx(0.25)
    hi = dict(S)
    hi[(d.module, d.key)] = K.fmt(d.from_unit(0.9))
    assert d.to_unit(D.sens_moves("pr12", hi)[d.name][(d.module, d.key)]) == pytest.approx(0.75)


def test_flat_settings_and_jacobian():
    assert D.flat_settings({"pr12": {"a": [0.01, 0.04, 0.2], "b": [0.05, 0.06, 0.07]}}) == {"pr12": ["a"]}
    g = np.diag([4.0, 1.0, 0.0])
    s = D.jacobian_summary([g, g])
    assert s["participation_ratio"] == pytest.approx(25 / 17)
    assert abs(s["smallest"][2]) == pytest.approx(1)


# ------------------------------------------------------------------------------ the readings

def test_knob_distance_drops_flat_settings_and_ignores_mics():
    S = S_for("pr12")
    dims = K.space("pr12", S)
    t = dict(S)
    x = dict(S)
    d = next(dd for dd in dims if dd.name == "pr12Amp/pr12Volume")
    x[(d.module, d.key)] = K.fmt(d.from_unit(0.9))
    n_cont = sum(dd.kind in ("cont", "log") for dd in dims)
    assert D.knob_distance(x, t, dims) == pytest.approx(0.4 / n_cont)
    assert D.knob_distance(x, t, dims, flat=("pr12Amp/pr12Volume",)) == 0
    m = next(dd for dd in dims if dd.kind == "cat")
    x[(m.module, m.key)] = "9" if t[(m.module, m.key)] != "9" else "8"
    assert D.knob_distance(x, t, dims, flat=("pr12Amp/pr12Volume",)) == 0 and not D.mics_match(x, t, dims)


def test_informative_and_non_finite_handling():
    assert D.informative(unit(dS=0.1))
    assert not D.informative(unit(dS=0.09))
    assert not D.informative(unit(d={"S": INF}))
    assert not D.informative(unit(d={"target_repeat": INF}))
    u = unit(d={"x": INF, "y": 0.4}, s={"x": 0.0, "y": 0.5})
    assert not D.closes(u, "x") and D.gap(u, "x") is None
    assert D.best_of(u, ["x", "y"]) == "x"                         # x's search half is finite
    u2 = unit(d={"x": 0.1, "y": 0.4}, s={"x": INF, "y": 0.5})
    assert D.best_of(u2, ["x", "y"]) == "y"                         # never a non-finite search half
    assert D.best_of(unit(s={"x": INF}, d={"x": 0.1}), ["x"]) is None


def test_r1_counts_inclusive_and_strictly_closer():
    us = fold_units(0, 4, 2)                                       # 4 of 6 = 2/3 exactly
    r = D.r1_fold(us, "1b")
    assert r["closed"] == 4 and r["passes"]
    us = fold_units(0, 3, 2)
    assert not D.r1_fold(us, "1b")["passes"]
    tie = fold_units(0, 6, 0)
    for u in tie[:3]:
        u["d"]["median"] = u["d"]["1b:A:top"]                       # equal is not closer
    assert not D.r1_fold(tie, "1b")["passes"]
    ref = fold_units(0, 6, 0)
    for u in ref[:3]:
        u["d"]["1b:A:top"] = INF                                    # refused: not closing
    assert not D.r1_fold(ref, "1b")["passes"]
    assert not D.r1_fold([], "1b")["passes"]


def test_r2_margins_against_both_baselines():
    us = fold_units(0, 6, 0)
    r = D.r2_fold(us, "1b")
    assert r["passes"] and r["vs_random"] < -0.03
    edge = fold_units(0, 6, 0)
    for u in edge:
        for j in range(8):
            u["d"][f"jS{j}"] = 0.2 * math.exp(0.03)                 # exactly -0.03: passes
    assert D.r2_fold(edge, "1b")["passes"]
    worse = fold_units(0, 6, 0)
    for u in worse:
        for j in range(8):
            u["d"][f"rand{j}"] = 0.2 * math.exp(0.02)
    assert not D.r2_fold(worse, "1b")["passes"]


def test_r2_uses_the_first_k_and_picks_on_the_search_half():
    u = good_unit(0, "x", 0, k=8)
    u["s"]["1b:A:s0"], u["s"]["1b:A:s5"] = 0.9, 0.05               # s5 picked at K = 8 only
    u["d"]["1b:A:s5"] = 0.95
    us = [json.loads(json.dumps(u)) for _ in range(3)]
    assert D.r2_fold(us, "1b", k=8)["closed"] == 0
    assert D.r2_fold(us, "1b", k=4)["closed"] == 3


def test_fragility_and_view_status():
    us = [good_unit(0, "x", i) for i in range(3)] + [good_unit(0, "y", 3)] + \
        [good_unit(0, "y", 4 + i, close=False) for i in range(2)]      # 4 of 6; without x, 1 of 3
    r = D.r1_fold(us, "1b")
    assert r["passes"] and r["fragile"]
    solid = fold_units(0, 6, 0, bands=("x", "y"))
    assert not D.r1_fold(solid, "1b")["fragile"]
    P = {"passes": True, "fragile": False}
    Fr = {"passes": True, "fragile": True}
    X = {"passes": False, "fragile": False}
    assert D.view_status({0: P, 1: P, 2: P, 3: P}) == "pass"
    assert D.view_status({0: P, 1: P, 2: P, 3: Fr}) == "undecided"          # fold 3's fragility
    assert D.view_status({0: P, 1: P, 2: P, 3: X}) == "undecided"           # 3 of 4
    assert D.view_status({0: P, 1: X, 2: P, 3: X}) == "fail"


def r4_unit(fold, band, target, far_good=0, near_good=0, bad=0, jit_close=4, match=True):
    d, knob, mics = {}, {}, {}
    for i in range(far_good):
        d[f"f{i}"], knob[f"f{i}"] = 0.2, 0.5
    for i in range(near_good):
        d[f"n{i}"], knob[f"n{i}"] = 0.2, 0.05
    for i in range(bad):
        d[f"b{i}"], knob[f"b{i}"] = 0.9, 0.6 + i * 0.01
    for j in range(4):
        d[f"jTc{j}"], knob[f"jTc{j}"] = (0.3 if j < jit_close else 0.9), 0.06
    u = unit(fold, band, target, d=d, knob=knob)
    u["mic_match"] = {n: match for n in u["d"]}
    return u


def test_r4_share_jitter_clause_and_dedupe():
    us = [r4_unit(0, "x", i, far_good=3, near_good=1, bad=2) for i in range(3)]
    r = D.r4_fold(us)
    assert r["share"] == pytest.approx(3 / 8) and r["jitter_clause"] and r["R4"]
    for u in us:
        u["key"]["f1"] = u["key"]["f0"]                             # identical settings count once
        u["key"]["f2"] = u["key"]["S"]                              # S's settings are not in the pool
    assert D.r4_fold(us)["share"] == pytest.approx(1 / 6)
    few = [r4_unit(0, "x", i, far_good=3, jit_close=1) for i in range(3)]
    assert not D.r4_fold(few)["R4"]                                 # 1 of 4 jitters close


def test_r4_prime_and_landscape():
    us = [r4_unit(0, "x", i, near_good=6, bad=4) for i in range(3)]
    r = D.r4_fold(us)
    assert r["share"] == 0 and r["spearman_bw"] <= -0.5 and r["R4p"] and not r["R4"]
    assert D.landscape({0: r, 1: r}) == "R4p"
    r4 = D.r4_fold([r4_unit(0, "x", i, far_good=3, near_good=1) for i in range(3)])
    assert D.landscape({0: r4, 1: r4}) == "R4"
    assert D.landscape({0: r4, 1: r}) == "between"


def test_r4_share_split_by_mic_match():
    us = [r4_unit(0, "x", 0, far_good=2, match=False), r4_unit(0, "x", 1, near_good=2, match=True)]
    r = D.r4_fold(us)
    assert r["share_mics_differ"] > r["share_mics_match"]


SETUP_OK = {"passes": True}
ALL_FAIL = {f"{r}:{v}": "fail" for r in ("R1", "R2", "R2k4") for v in D.VIEWS}


def test_trigger_rows_in_order():
    s = dict(ALL_FAIL)
    assert D.trigger({"passes": False}, s, False, "R4") == 0
    assert D.trigger(SETUP_OK, dict(s, **{"R1:1b": "pass", "R2:1b": "pass"}), False, "R4") == 1
    assert D.trigger(SETUP_OK, dict(s, **{"R2:1b": "pass"}), False, "R4") == 2
    assert D.trigger(SETUP_OK, dict(s, **{"R1:1a": "undecided"}), False, "R4") == 3
    assert D.trigger(SETUP_OK, dict(s, **{"R1:1a": "pass"}), True, "R4") == 4
    assert D.trigger(SETUP_OK, s, False, "R4") == 5
    assert D.trigger(SETUP_OK, s, False, "R4p") == 6
    assert D.trigger(SETUP_OK, s, False, "between") == 7
    assert D.trigger(SETUP_OK, dict(s, **{"R2:1a": "pass"}), False, "R4") == 3   # 1a pass outside R3: ask


def all_folds(make):
    return [u for f in range(4) for u in make(f)]


def test_readings_r3_at_matched_k():
    def make(f):
        us = []
        for i in range(6):
            a = good_unit(f, "xy"[i % 2], 100 * f + i, view="1a", k=4)
            b = good_unit(f, "xy"[i % 2], 100 * f + i, view="1b", k=8, close=False)
            for f_ in ("d", "s", "key", "knob", "mic_match"):
                a[f_] = {**b[f_], **a[f_]}
            a["d"]["median"] = 0.95
            us.append(a)
        return us
    rd = D.readings(all_folds(make), SETUP_OK)
    assert rd["status"]["R1:1a"] == "pass" and rd["status"]["R1:1b"] == "fail"
    assert rd["status"]["R2k4:1a"] == "pass" and rd["status"]["R2k4:1b"] == "fail"
    assert rd["R3"] and rd["trigger"] == 4


def test_readings_drop_non_informative_units():
    def make(f):
        us = fold_units(f, 6, 0, bands=("x", "y", "z"))
        us[0]["d"]["S"] = INF
        return us
    rd = D.readings(all_folds(make), SETUP_OK)
    assert rd["informative"] == {f: 5 for f in range(4)} and len(rd["dropped_non_informative"]) == 4


def test_label_sampling_flag():
    def make(f):
        return ([good_unit(f, "x", i, typ="ks_prior") for i in range(3)]
                + [good_unit(f, "y", 10 + i, typ="broad", close=False) for i in range(3)])
    by = {f: [u for u in all_folds(make) if u["fold"] == f] for f in range(4)}
    assert D.label_sampling_flag(by)
    by_both = {f: fold_units(f, 6, 0) for f in range(4)}
    assert not D.label_sampling_flag(by_both)


def test_setup_check():
    ok = D.setup_check([0.0, 1e-4], {i: (0.0, 0.0) for i in range(100)}, {f: 40 for f in range(4)}, True)
    assert ok["passes"]
    reps = {i: (0.0, 0.0) for i in range(100)}
    reps.update({i: (0.01, 0.0) for i in range(5)})
    assert D.setup_check([0.0], reps, {f: 40 for f in range(4)}, True)["passes"]          # 95% exactly
    reps[5] = (INF, 0.0)                     # a refused half is a non-finite unit, not a repeat failure
    r = D.setup_check([0.0], reps, {f: 40 for f in range(4)}, True)
    assert r["passes"] and len(r["targets_dropped_repeat"]) == 5
    reps[6] = (0.01, 0.0)
    r = D.setup_check([0.0], reps, {f: 40 for f in range(4)}, True)
    assert not r["passes"] and len(r["targets_dropped_repeat"]) == 6
    assert not D.setup_check([0.002], {0: (0, 0)}, {0: 40}, True)["passes"]
    assert D.setup_check([0.0], {0: (0, 0)}, {0: 39}, True)["folds_short"] == {0: 39}
    assert not D.setup_check([0.0], {0: (0, 0)}, {0: 40}, False)["passes"]


# ------------------------------------------------------------------------------ the K_S replay

def test_replay_reproduces_a_synthetic_search_and_sets():
    S = S_for("pr12")
    dims = K.space("pr12", S)
    rng = random.Random(0)
    w = {d.name: rng.random() for d in dims}

    def score(x, h):
        return 1 + sum((d.to_unit(x[(d.module, d.key)]) - w[d.name]) ** 2 for d in dims if d.kind in ("cont", "log")) \
            + 0.01 * h + sum(x[(d.module, d.key)] != d.values[0] for d in dims if d.kind == "cat") * 0.1

    evals = []

    def f(x):
        evals.append((score(x, 0), score(x, 1)))
        return evals[-1][0]

    best, _, _, _ = K.knob_search(dims, S, f, 60, 5)
    x, xs, ok = D.replay_run(dims, S, evals, "A", budget=60, seed=5)
    assert ok and D.sj(x) == D.sj(best) and len(xs) == len(evals)
    sets = D.equal_score_sets(xs, evals, "B", dims)
    assert sets["0.03"]["n"] >= 1 and sets["0.1"]["n"] >= sets["0.03"]["n"]
    _, _, ok_short = D.replay_run(dims, S, evals[:-1], "A", budget=60, seed=5)
    assert not ok_short                                              # a missing evaluation is caught


# ------------------------------------------------------------------------------ step 1.3

def test_step13_refuses_without_the_flag():
    with pytest.raises(SystemExit):
        D.main(["step13-propose"])
    with pytest.raises(SystemExit):
        D.main(["step13-score", "--shard", "0/3"])
    with pytest.raises(SystemExit):
        D.main(["step13-report"])
    D.require_user_approval(True)


def test_step13_reading():
    rows = [{"band": b, "pick": 0.9, "KS16": 1.0, "S": 1.2} for b in "abcde"]
    assert D.step13_reading(rows)["reading"] == "covers records"
    rows[0].update(pick=2.0)
    rows[1].update(pick=2.0)
    assert D.step13_reading(rows)["reading"] == "renders only"               # beats S in 3 of 5 = 60%, but vs K_S
    rows = [{"band": b, "pick": 0.99, "KS16": 1.0, "S": (1.2 if b in "abc" else 0.5)} for b in "abcde"]
    assert D.step13_reading(rows)["reading"] == "covers records"              # 3 of 5 bands is 60%
    rows[2]["S"] = 0.5
    assert D.step13_reading(rows)["reading"] == "renders only"


# ------------------------------------------------------------------------------ guards

VM = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                               100000.
Pages active:                             900000.
Pages inactive:                           200000.
Pages speculative:                         50000.
"""


def test_vm_stat_and_swap_parsing():
    assert D.parse_vm_stat(VM) == 350000 * 16384
    assert D.parse_swapusage("vm.swapusage: total = 2048.00M  used = 1024.50M  free = 1023.50M") == 1024.5
    assert D.parse_swapusage("vm.swapusage: total = 4G  used = 1.50G  free = 2.5G") == 1536.0


def test_memory_guard_start_pause_and_exit():
    with pytest.raises(SystemExit):
        D.MemoryGuard(read=lambda: (5e9, 0.0))
    state = {"avail": 8e9, "t": 0.0}
    slept = []

    def sleep(s):
        slept.append(s)
        state["t"] += s
    g = D.MemoryGuard(every=2, read=lambda: (state["avail"], 0.0), sleep=sleep, clock=lambda: state["t"])
    g.tick()
    g.tick()
    assert not slept
    state["avail"] = 2e9
    g.tick()
    with pytest.raises(SystemExit):
        g.tick()
    assert len(slept) == 15
    g2 = D.MemoryGuard(every=1, read=lambda: (8e9, 100.0 if state.get("swap") else 0.0), sleep=sleep,
                       clock=lambda: state["t"])
    state["swap"] = True
    assert not g2.low()                                              # 100 MB of growth is fine


def test_training_slowdown_and_shards():
    assert D.training_slowdown(1.0, 1.26) and not D.training_slowdown(1.0, 1.25)
    D.check_shards(3)
    with pytest.raises(SystemExit):
        D.check_shards(4)


# ------------------------------------------------------------------------------ audio paths

def test_one_timeline():
    from learn import rescore as R
    from learn import song_aug as A

    assert A.HALVES == {h: tuple(v) for h, v in R.HALVES.items()}
    y = np.arange(D.WIN_LEN, dtype=np.float64)
    t = D.trim(y)
    assert len(t) == D.CLIP and t[0] == D.TRIM
    assert np.array_equal(D.trim(np.stack([y, y], axis=1)), t)


def test_flac_round_trip_matches_the_bank_loader(tmp_path, monkeypatch):
    pytest.importorskip("soundfile")
    from learn import song_aug as A

    y = np.sin(np.linspace(0, 200, 48000)) * 0.3
    peak = D.save_flac(tmp_path / "00007.flac", y, "PCM_16")
    (tmp_path / "00007.json").write_text(json.dumps({"peak": peak}))
    monkeypatch.setattr(A.B, "OUT", tmp_path.parent)
    (tmp_path.parent / "renders").mkdir(exist_ok=True)
    for ext in ("flac", "json"):
        (tmp_path.parent / "renders" / f"00007.{ext}").write_bytes((tmp_path / f"00007.{ext}").read_bytes())
    assert np.array_equal(D.load_flac(tmp_path / "00007.flac", peak), A.load_render(7))
    p24 = D.save_flac(tmp_path / "x.flac", y, "PCM_24")
    assert np.abs(D.load_flac(tmp_path / "x.flac", p24) - y).max() < 1e-6


def test_mixture_views_share_guitar_and_backing():
    pytest.importorskip("pyloudnorm")
    r = np.random.default_rng(0)
    g = r.normal(0, 0.1, 48000 * 2)
    back = r.normal(0, 0.1, 48000 * 2)
    seen = []

    def sep(m):
        seen.append(m)
        return m * 0.5
    v = D.mixture_views(g, back, random.Random(1), [3.0], -20.0, None, False, sep)
    stem_a, mix_a = v["1a"]
    stem_b, mix_b = v["1b"]
    assert np.allclose(stem_a / np.abs(stem_a).max(), g / np.abs(g).max())   # 1a: the guitar itself
    assert np.allclose(stem_b, mix_b * 0.5) and len(seen) == 1               # 1b: separated master
    assert np.abs(mix_b).max() <= 10 ** (-1 / 20) + 1e-9                      # limiter


# ------------------------------------------------------------------------------ torch: parity

def test_top_mean_matches_predict_settings():
    torch = pytest.importorskip("torch")
    from learn import song_model as M

    torch.manual_seed(0)
    net = M.build_model().eval()
    S = S_for("sw50r")
    feat = np.random.default_rng(0).normal(-40, 10, (2, 96, 446)).astype(np.float16)
    lufs = np.array([-20.0, -14.0], np.float32)
    a, _ = M.predict_settings(net, feat, lufs, "sw50r", "crunch", S)
    h = D.net_heads(net, feat, lufs, "sw50r", "crunch")
    assert D.sj(D.top_mean_settings(h, "sw50r", S)) == D.sj(a)
    assert h["pi"].shape == (M.K_MIX,) and h["sigma"].min() > 0 and len(h["mic_p"]) == len(M.CAT)
