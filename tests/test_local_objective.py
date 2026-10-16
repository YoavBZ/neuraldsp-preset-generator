"""Arm A's local objective (`learn/local_objective.py`, docs/local-objective-plan.md): Σ, the scoring
factorial, the fidelity measures, the step-0 statistics and the guards. Fakes, plus one check on
the stored knob-ceiling and arm A data where it exists (zero renders)."""

import math
import random
import statistics

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import arm_a_levers as L  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as M  # noqa: E402

AMP = "pr12"


def preset(seed, amp=AMP, mics=("3", "5"), switch="false", left="true"):
    rng = random.Random(seed)
    x = {("parameters", "outputGain"): "5.96", ("cabParameters", "leftCabActive"): left,
         M.INPUT_GAIN: "0"}
    for d in K.space(amp):
        if (d.module, d.key) == M.INPUT_GAIN:
            continue
        if d.kind == "cat":
            x[(d.module, d.key)] = mics[0] if d.key.startswith("left") else mics[1]
        elif d.kind == "switch":
            x[(d.module, d.key)] = switch
        else:
            x[(d.module, d.key)] = K.fmt(d.from_unit(0.2 + 0.6 * rng.random()))
    return x


S = preset(1)
DIMS = K.space(AMP, S)


def k(d):
    return (d.module, d.key)


# --- Σ ------------------------------------------------------------------------------------------------

def test_neighbourhood_counts_single_moves_and_format():
    nb = M.neighbourhood(DIMS, S)
    cont = [d for d in DIMS if d.kind in ("cont", "log")]
    sw = [d for d in DIMS if d.kind == "switch"]
    assert len(nb) == 1 + 2 * len(cont) + len(sw)          # pr12: 1 + 18 + 1 = 20
    assert nb[0][0]["source"] == "S" and nb[0][1] == S
    assert len({K.key(x) for _, x in nb}) == len(nb)
    for tag, x in nb[1:]:
        diff = [kk for kk in set(x) | set(S) if x.get(kk) != S.get(kk)]
        assert len(diff) == 1 and "/".join(diff[0]) == tag["dim"]
        d = next(d for d in DIMS if d.name == tag["dim"])
        if d.kind == "cont":
            step = L.unit(d, x) - L.unit(d, S)
            assert step == pytest.approx(M.STEP if tag["side"] == "+" else -M.STEP, abs=1e-6)
            # the same string `coord_search` would build for this candidate
            assert x[k(d)] == K.fmt(d.from_unit(L.unit(d, S) + (M.STEP if tag["side"] == "+" else -M.STEP)))
        else:
            assert tag["side"] == "flip"
    assert not any(d.kind == "cat" and t["dim"] == d.name for t, _ in nb for d in DIMS)


def test_neighbourhood_drops_a_clamped_side():
    x = dict(S)
    x[M.INPUT_GAIN] = "-20"                                   # at the floor
    nb = M.neighbourhood(K.space(AMP, x), x)
    sides = [t["side"] for t, _ in nb if t["dim"] == "parameters/inputGain"]
    assert sides == ["+"]


def test_neighbourhood_input_gain_step_is_4_db():
    nb = dict(((t["dim"], t["side"]), x) for t, x in M.neighbourhood(DIMS, S))
    assert float(nb[("parameters/inputGain", "+")][M.INPUT_GAIN]) == pytest.approx(4.0)
    assert float(nb[("parameters/inputGain", "-")][M.INPUT_GAIN]) == pytest.approx(-4.0)


def toy_paths(seed, n, halves=("A", "B")):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        x = preset(1000 + seed * 100 + i)
        out.append((x, {h: 1 + rng.random() for h in halves}))
    return out


def test_cell_sigma_fill_draw_and_annotations():
    ks = [toy_paths(1, 30), toy_paths(2, 30)]
    ks[1].append(ks[0][0])                                    # a duplicate across directions
    aa = [[(x, {"A": d["A"]}) for x, d in toy_paths(3, 20)], [(x, {"B": d["B"]}) for x, d in toy_paths(4, 20)]]
    aa[1].append((ks[0][1][0], {"B": 7.0}))                   # an arm A point K_S also evaluated
    pts = M.cell_sigma("part", AMP, DIMS, S, ks, aa)
    assert len(pts) == M.N_FILL + M.N_ARM_A
    assert len({p["key"] for p in pts}) == len(pts)
    src = [p["source"] for p in pts]
    assert src[0] == "S" and src.count("S") == 1
    nb = len(M.neighbourhood(DIMS, S))
    assert src[1:nb] == ["nbr"] * (nb - 1)
    assert src[nb:M.N_FILL] == ["ks"] * (M.N_FILL - nb) and src[M.N_FILL:] == ["armA"] * M.N_ARM_A
    for p in pts:
        if p["source"] == "ks":
            assert p["true_stored"] is not None
        if p["source"] == "armA":
            assert p["obj_stored"] is not None
    again = M.cell_sigma("part", AMP, DIMS, S, ks, aa)
    assert [p["key"] for p in again] == [p["key"] for p in pts]
    other = M.cell_sigma("part2", AMP, DIMS, S, ks, aa)        # seeded per cell
    assert [p["key"] for p in other] != [p["key"] for p in pts]


def test_cell_sigma_small_pools_and_merged_halves():
    ks = [toy_paths(5, 3)]
    pts = M.cell_sigma("p", AMP, DIMS, S, ks, [toy_paths(6, 2, ("A",))])
    assert len(pts) == len(M.neighbourhood(DIMS, S)) + 3 + 2
    x = preset(77)
    pool = M.pool([[(x, {"A": 1.0})], [(x, {"B": 2.0}), (x, {"A": 9.0})]])
    assert pool[K.key(x)][1] == {"A": 1.0, "B": 2.0}


def test_sigma_json_hash_and_expected_renders():
    pts = M.cell_sigma("p", AMP, DIMS, S, [toy_paths(1, 40)], [toy_paths(2, 10, ("A",))])
    sj = M.sigma_json({("p", AMP): pts, ("q", AMP): pts})
    assert set(sj) == {"p|pr12", "q|pr12"}
    assert all("/" in kk for kk in sj["p|pr12"][0]["x"])
    assert M.sigma_hash(sj) == M.sigma_hash(M.sigma_json({("q", AMP): pts, ("p", AMP): pts}))
    assert M.expected_renders(sj) == 2 * 48 * 2 + 2 * 2
    assert M.expected_renders(sj, dis=("dac9",), cells={"p|pr12"}) == 48 + 1


def test_arm_a_path_replays_the_search():
    def f(x):
        return 1.0 + sum((L.unit(d, x) - 0.3) ** 2 for d in DIMS if d.kind == "cont") + 0.1 * (x.get(("cabParameters", "leftMicType")) != "4")
    seen = []

    def g(x):
        seen.append(dict(x))
        return f(x)
    xf, _, _, _ = K.knob_search(DIMS, S, g, 40, L.SEED)
    curve = [f(x) for x in seen]
    path, x = M.arm_a_path(AMP, S, curve, budget=40)
    assert x == xf and [p for p, _ in path] == seen and [v for _, v in path] == curve


# --- scoring --------------------------------------------------------------------------------------------

def test_configs_and_corners():
    assert len(M.configs("measure")) == 12 and len(M.configs("dac9")) == 12
    assert len(set(M.configs("cprime"))) == 16                      # plus the GCC-aligned lag
    assert M.CURRENT in M.configs("cprime") and M.TRUE in M.configs("measure") and M.DECISIVE in M.configs("measure")
    assert not any(c[2] == "gcc" for c in M.configs("measure"))


def test_lag_levels_are_relative_to_each_di():
    """Amendment 1: native is −52 for a rebuild and judge_lag for the measure DI and DAC-9."""
    assert M.lag_value("native", "cprime", -36) == -52 and M.lag_value("other", "cprime", -36) == -36
    assert M.lag_value("native", "measure", 914) == 914 and M.lag_value("other", "measure", 914) == -52
    assert M.lag_value("native", "dac9", -36) == -36 and M.lag_value("zero", "measure", -36) == 0
    assert M.lag_value("gcc", "cprime", -36, gcc=-53) == 1 and M.lag_value("gcc", "cprime", -36, gcc=0) == -52
    with pytest.raises(ValueError):
        M.lag_value("gcc", "measure", -36, gcc=0)
    with pytest.raises(ValueError):
        M.lag_value("gcc", "cprime", -36)


def test_in_di_time():
    import numpy as np

    rec = np.arange(10.0)
    assert np.array_equal(M.in_di_time(rec, -52), rec)               # identity at the rebuild's lag
    assert np.array_equal(M.in_di_time(rec, -49), [3, 4, 5, 6, 7, 8, 9, 0, 0, 0])
    assert np.array_equal(M.in_di_time(rec, -54), [0, 0, 0, 1, 2, 3, 4, 5, 6, 7])
    assert not M.in_di_time(rec, 100).any()


def test_in_di_time_matches_the_judges_indexing():
    """aligned_distance reads the mask at DI time t − lag − 52 for recording time t: the moved
    recording, read there, is the recording itself."""
    import numpy as np

    rec = np.random.default_rng(1).standard_normal(5000)
    for lag in (-52, -36, 0, 914, -100):
        m = M.in_di_time(rec, lag)
        t = np.arange(2000, 3000)
        assert np.array_equal(m[t - lag - 52], rec[t])


def fake_judge(log):
    def aligned(rec, y, mask, lag, a, b):
        log.append((rec if isinstance(rec, str) else "arr", mask if isinstance(mask, str) else "arr", lag, a, b))
        if isinstance(mask, str) and mask == "silent":
            return None, "the DI plays in too few frames"
        return 1.0 + 0.001 * lag + (0.5 if rec == "ref" else 0.0) + (0.25 if not isinstance(mask, str) else 0.0), None
    return aligned


def test_score_render_masks_lags_and_fallback(monkeypatch):
    import numpy as np

    shifted = []
    monkeypatch.setattr(M, "in_di_time", lambda rec, lag: shifted.append((rec, lag)) or np.zeros(3))
    log = []
    aligned = fake_judge(log)
    sig = {"di": "di", "stem": "stem", "reference": "ref"}
    out, fb = M.score_render("y", "measure", sig, -36, aligned)
    assert set(out) == {M.cname(c) for c in M.configs("measure")}
    assert out["measure|reference|native|own"]["A"] == pytest.approx(1.0 - 0.036 + 0.5)
    assert out["measure|stem|other|own"]["A"] == pytest.approx(1.0 - 0.052)
    assert out["measure|stem|zero|record"]["A"] == pytest.approx(1.25)
    assert sum(fb.values()) == 0 and {(e[3], e[4]) for e in log} == set(K.R.HALVES.values())
    assert ("stem", -36) in shifted and ("ref", 0) in shifted and ("stem", -52) in shifted   # record masks moved
    shifted.clear()
    out, fb = M.score_render("y", "cprime", {**sig, "di": "silent"}, -36, aligned, gcc=-53)
    assert fb["cprime|stem|native|own"] == 2 and out["cprime|stem|native|own"]["A"] == pytest.approx(1.0 - 0.052 + 0.25)
    assert ("stem", -52) in shifted and ("stem", -36) in shifted                            # the fallback too
    assert out["cprime|stem|gcc|own"]["A"] == pytest.approx(1.0 + 0.001 + 0.25)
    out, fb = M.score_render("y", "measure", {**sig, "di": "silent"}, -36, aligned)
    assert out["measure|reference|native|own"]["A"] == math.inf and sum(fb.values()) == 0  # no fallback
    only, _ = M.score_render("y", "cprime", sig, -36, aligned, only={M.CURRENT})
    assert list(only) == [M.cname(M.CURRENT)]


def test_score_render_own_mask_matches_rebuilt_distance_at_minus_52():
    """The current corner equals `rebuilt_distance` (fallback included) on real signals."""
    import numpy as np

    pytest.importorskip("soundfile")
    from learn.rebuilt_judge import rebuilt_distance

    rng = np.random.default_rng(2)
    n = 48000 * 10
    t = np.arange(n) / 48000
    env = (np.sin(2 * np.pi * 0.7 * t) > -0.2).astype(float)
    di = env * np.sin(2 * np.pi * 220 * t) * 0.1
    quiet = di * (np.arange(n) % 96000 < 20000)                     # a DI that pauses: the fallback fires
    rec = np.roll(di, 52) + 1e-4 * rng.standard_normal(n)
    y = np.roll(np.tanh(5 * di), 52)
    aligned = M.judge_fns()
    for d in (di, quiet):
        sig = {"di": d, "stem": rec, "reference": rec}
        out, fb = M.score_render(y, "cprime", sig, -36, aligned, only={M.CURRENT})
        for h, (a, b) in K.R.HALVES.items():
            r, proxy = rebuilt_distance(rec, y, d, start_s=a, end_s=b, lag=-52)
            v = math.inf if r.distance is None else r.distance
            assert out[M.cname(M.CURRENT)][h] == pytest.approx(v)


def test_deviation_and_corner_checks():
    assert M.deviation(math.inf, math.inf) == 0.0 and M.deviation(1.0, math.inf) == math.inf
    assert M.deviation(math.e, 1.0) == pytest.approx(1.0)
    pts = [{"true_stored": {"A": 2.0, "B": 3.0}, "obj_stored": None},
           {"true_stored": None, "obj_stored": {"B": 5.0}, "obj_2b": {"A": 4.0, "B": 5.0}}]
    sc = [{M.cname(M.TRUE): {"A": 2.0, "B": 3.03}, M.cname(M.CURRENT): {"A": 1, "B": 1}},
          {M.cname(M.TRUE): {"A": 1, "B": 1}, M.cname(M.CURRENT): {"A": 4.0, "B": 5.0}}]
    m = M.corner_checks(pts, sc, "measure")
    assert [(i, w, h) for i, w, h, _ in m] == [(0, "true_vs_KS", "A"), (0, "true_vs_KS", "B")]
    assert m[1][3] == pytest.approx(math.log(1.01))
    c = M.corner_checks(pts, sc, "cprime")
    assert {w for _, w, _, _ in c} == {"current_vs_armA", "current_vs_2b"} and all(v == 0 for *_, v in c)


# --- fidelity ------------------------------------------------------------------------------------------

def test_rho_pairwise_and_worst():
    assert M.rho([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(1.0)
    assert M.rho([1, 2, math.inf, 4], [1, 2, 3, 4]) == pytest.approx(1.0)
    assert M.rho([1, 2], [1, 2]) is None and M.rho([1, 1, 1], [1, 2, 3]) is None
    assert M.rho_worst([1, 2, math.inf, 4], [1, 2, 3, 4]) < 1.0
    assert M.rho_worst([1, 2, 3, math.inf], [1, 2, 3, math.inf]) == pytest.approx(1.0)


def test_same_cross_and_ceiling():
    true = {"A": [1, 2, 3, 4, 5], "B": [5, 4, 3, 2, 1]}
    obj = {"A": [1, 2, 3, 4, 5], "B": [1, 2, 3, 4, 5]}
    assert M.same_half(obj, true) == pytest.approx(0.0)              # +1 on A, −1 on B
    assert M.cross_half(obj, true) == pytest.approx(0.0)
    assert M.ceiling(true) == pytest.approx(-1.0)
    assert M.cross_half(true, true) == pytest.approx(M.ceiling(true))


def test_reliable_pairs_and_accuracy():
    true = {"A": [1, 2, 3, 4], "B": [1, 3, 2, 4]}                     # (1, 2) flips between halves
    pairs = M.reliable_pairs(true)
    assert len(pairs) == 5 and all(p[:2] != (1, 2) for p in pairs)
    assert M.reliable_accuracy(true, true) == pytest.approx(1.0)
    rev = {h: [-v for v in vs] for h, vs in true.items()}
    assert M.reliable_accuracy(rev, true) == pytest.approx(0.0)
    tie = {h: [1, 1, 1, 1] for h in "AB"}
    assert M.reliable_accuracy(tie, true) == pytest.approx(0.5)
    assert M.reliable_accuracy(tie, {"A": [1, 1], "B": [1, 1]}) is None


def test_partial_rho():
    rng = random.Random(3)
    z = [rng.random() for _ in range(200)]
    x = [a + 0.1 * rng.random() for a in z]
    y = [a + 0.1 * rng.random() for a in z]
    assert M.rho(x, [v + 1 for v in y]) > 0.8
    assert abs(M.partial_rho(x, y, z)) < 0.3                           # the shared driver removed
    assert M.partial_rho([1, 2, 3], [1, 2, 3], [1, 2, 3]) is None


def three_points():
    """S, ±1/8 on two dims: indices 0 = S, 1/2 = dim a −/+, 3/4 = dim b −/+."""
    return [{"source": "S", "dim": None}, {"source": "nbr", "dim": "a"}, {"source": "nbr", "dim": "a"},
            {"source": "nbr", "dim": "b"}, {"source": "nbr", "dim": "b"}]


def test_coord_pick_and_three_way():
    assert M.coord_pick([1, 2], [1.0, 0.5, 0.7], 0) == 1
    assert M.coord_pick([1, 2], [1.0, 1.0 - 1e-13, 2.0], 0) == 0      # not beyond 1e-12
    assert M.coord_pick([1, 2], [1.0, math.inf, math.inf], 0) == 0
    pts = three_points()
    true = {h: [1.0, 0.5, 2.0, 2.0, 3.0] for h in "AB"}               # a: −; b: stay
    obj = {h: [1.0, 2.0, 0.5, 0.9, 3.0] for h in "AB"}                # a: + (wrong); b: − (wrong)
    tw = M.three_way(pts, obj, true)
    assert [t[0] for t in tw["a"]] == [False, False] and tw["a"][0][1] == pytest.approx(math.log(2.0 / 0.5))
    assert tw["b"][0] == (False, pytest.approx(math.log(2.0 / 1.0)), pytest.approx(1 / 3))
    tw = M.three_way(pts, true, true)
    assert all(a and r == 0 for v in tw.values() for a, r, _ in v)
    clamped = pts[:4]                                                  # dim b has one side only
    tw = M.three_way(clamped, {h: v[:4] for h, v in obj.items()}, {h: v[:4] for h, v in true.items()})
    assert tw["b"][0][2] == pytest.approx(0.5) and tw["a"][0][2] == pytest.approx(1 / 3)
    assert M.neighbourhood_regret(pts, obj, true) == pytest.approx(math.log(2.0 / 0.5))


def test_pair_class():
    x = dict(S)
    y = dict(S)
    d = next(d for d in DIMS if d.kind == "cont")
    y[k(d)] = K.fmt(d.from_unit(L.unit(d, S) + 0.3))
    assert M.pair_class(DIMS, x, y) == "coarse"
    y[k(d)] = K.fmt(d.from_unit(L.unit(d, S) + 0.05))
    assert M.pair_class(DIMS, x, y) == "fine"
    y[k(d)] = K.fmt(d.from_unit(L.unit(d, S) + 0.2))
    assert M.pair_class(DIMS, x, y) == "mid"
    y[("cabParameters", "rightMicType")] = "7"
    assert M.pair_class(DIMS, x, y) == "categorical"


def test_concordance_by_class():
    d = next(d for d in DIMS if d.kind == "cont")
    xs = [dict(S) for _ in range(3)]
    for i, u in enumerate((0.1, 0.15, 0.6)):
        xs[i][k(d)] = K.fmt(d.from_unit(u))
    true = {h: [1.0, 2.0, 3.0] for h in "AB"}
    obj = {h: [2.0, 1.0, 3.0] for h in "AB"}                           # the fine pair inverted
    c = M.concordance_by_class(DIMS, xs, obj, true)
    assert c["fine"] == (0.0, 1) and c["coarse"] == (1.0, 2) and c["categorical"] == (None, 0)


def test_cell_measures_runs_on_a_sigma():
    rng = random.Random(4)
    pts = M.cell_sigma("p", AMP, DIMS, S, [toy_paths(1, 40)], [toy_paths(2, 10, ("A",))])
    true = {h: [1 + rng.random() for _ in pts] for h in "AB"}
    obj = {h: [v + 0.01 * rng.random() for v in true[h]] for h in "AB"}
    m = M.cell_measures(pts, DIMS, obj, true)
    assert m["same_half"] > 0.9 and m["reliable_accuracy"] > 0.9
    assert "parameters/inputGain" in m["three_way"]
    assert set(m["by_class"]) == {"coarse", "mid", "fine", "categorical"}


# --- aggregation -------------------------------------------------------------------------------------

def test_agg_is_band_weighted_over_part_means():
    rows = {("p1", "pr12"): ("p1", "b1", "clean", 1.0), ("p1", "sw50r"): ("p1", "b1", "clean", 3.0),
            ("p2", "pr12"): ("p2", "b1", "crunch", 0.0), ("p3", "pr12"): ("p3", "b2", "clean", 4.0),
            ("p4", "pr12"): ("p4", "b3", "clean", None)}
    a = M.agg(rows)
    assert a["band_weighted_mean"] == pytest.approx((1.0 + 4.0) / 2)   # b1: mean(2, 0) = 1; b2: 4
    assert a["bands"] == 2 and a["cells"] == 4 and a["lo90"] < a["band_weighted_mean"] < a["hi90"]
    assert a["per_amp"]["sw50r"] == pytest.approx(3.0) and a["per_class"]["crunch"] == pytest.approx(0.0)
    assert M.agg({})["band_weighted_mean"] is None


def test_paired_and_main_effects():
    a = {("p", "x"): ("p", "b", "clean", 0.5), ("q", "x"): ("q", "b", "clean", None)}
    b = {("p", "x"): ("p", "b", "clean", 0.2), ("q", "x"): ("q", "b", "clean", 0.1)}
    assert M.paired(a, b) == {("p", "x"): ("p", "b", "clean", pytest.approx(0.3))}
    per = {}
    for cell in ("c1", "c2"):
        per[cell] = {}
        for d in M.DIS:
            for c in M.configs(d):
                v = 0.1 + (0.3 if c[0] == "measure" else 0) + (0.2 if c[1] == "reference" else 0) \
                    + (0.1 if c[0] == "measure" and c[1] == "reference" else 0) - (0.05 if c[3] == "record" else 0) \
                    - (0.2 if c[2] == "other" and c[0] == "cprime" else 0) + (0.04 if c[2] == "gcc" else 0)
                per[cell][c] = {"cross_half": v}
    me = M.main_effects(per)
    assert me["DI measure-cprime"]["c1"] == pytest.approx(0.35)       # at native lags: "other" is diagnostic
    assert me["reference reference-stem"]["c2"] == pytest.approx(0.25)
    assert me["mask record-own"]["c1"] == pytest.approx(-0.05)
    assert me["lag other-native [cprime]"]["c1"] == pytest.approx(-0.2)
    assert me["lag other-native [measure]"]["c1"] == pytest.approx(0.0)
    assert me["lag gcc-native [cprime]"]["c1"] == pytest.approx(0.04)
    assert me["DI x reference"]["c1"] == pytest.approx(0.1)
    assert "DI dac9-cprime" not in me and "lag other-native [dac9]" not in me


def test_agg_sigma_d_agg2_and_large_offset():
    rows = {("p1", "a"): ("p1", "b1", "clean", 1.0), ("p2", "a"): ("p2", "b2", "clean", 3.0),
            ("p3", "a"): ("p3", "b3", "clean", 8.0)}
    assert M.agg(rows)["sigma_d"] == pytest.approx(statistics.stdev([1.0, 3.0, 8.0]))
    two = M.agg2(rows, large=("p3",))
    assert two["all"]["band_weighted_mean"] == pytest.approx(4.0)
    assert two["without_large_offset"]["band_weighted_mean"] == pytest.approx(2.0)
    parts = {"a": {"judge_lag": -36}, "b": {"judge_lag": 914}, "c": {"judge_lag": 521}, "d": {"judge_lag": -153},
             "e": {"judge_lag": 47}}
    assert M.large_offset_parts(parts) == ["b", "c", "d"]


def test_wide_undecided_and_dac_extension():
    rows = {("p1", "a"): ("p1", "b1", "clean", 0.1), ("p2", "a"): ("p2", "b2", "clean", 0.3),
            ("p3", "a"): ("p3", "b3", "clean", 0.2), ("p4", "a"): ("p4", "b3", "clean", 0.25)}
    w = M.wide(rows)
    m, lo, hi = L.interval([(s, b, v) for s, b, _, v in rows.values()], wider=True)
    assert (w["mean"], w["lo90"], w["hi90"]) == (m, lo, hi) and w["bands"] == 3
    assert M.undecided({"lo90": -0.1, "hi90": 0.2}) and not M.undecided({"lo90": 0.05, "hi90": 0.2})
    assert M.undecided({"lo90": None})
    yes, no = {"lo90": 0.05, "hi90": 0.2}, {"lo90": -0.05, "hi90": 0.2}
    assert not M.dac_extension_due(yes, yes)
    assert M.dac_extension_due(no, yes) and M.dac_extension_due(yes, no)


# --- breakage and render-time checks (amendment 1) -------------------------------------------------

def test_render_checks(monkeypatch):
    calls = []

    def fake_score(y, di, sig, jl, aligned, gcc=None, only=None):
        calls.append((di, tuple(only)))
        return {M.cname(next(iter(only))): {"A": 2.0, "B": 3.0}}, {}
    monkeypatch.setattr(M, "score_render", fake_score)
    p = {"true_stored": {"A": 2.0, "B": 3.03}, "obj_stored": {"B": 3.0}, "obj_2b": {"A": 2.0, "B": 3.0}}
    out = M.render_checks(p, "measure", None, None, -36, None)
    assert [(w, h) for w, h, _ in out] == [("true_vs_KS", "A"), ("true_vs_KS", "B")]
    assert out[1][2] == pytest.approx(math.log(1.01)) and calls[-1] == ("measure", (M.TRUE,))
    out = M.render_checks(p, "cprime", None, None, -36, None)
    assert {w for w, _, _ in out} == {"current_vs_armA", "current_vs_2b"} and all(d == 0 for *_, d in out)
    assert calls[-1] == ("cprime", (M.CURRENT,))
    assert M.render_checks({"true_stored": None, "obj_stored": None}, "cprime", None, None, -36, None) == []


def test_breakage_stops_every_shard(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "OUT", tmp_path)
    M.check_stop()                                                     # nothing to stop yet
    rec_path = tmp_path / "renders" / "measure" / "p" / "pr12.json"
    rec_path.parent.mkdir(parents=True)
    with pytest.raises(SystemExit):
        M.breakage(rec_path, {"slug": "p", "amp": "pr12", "di": "measure", "renders": 5}, "true_vs_KS moved")
    import json

    assert json.loads(rec_path.read_text())["status"] == "check_failed"
    assert not M._done("measure", "p", "pr12")
    with pytest.raises(SystemExit):
        M.check_stop()


def test_load_sigma_recomputes_the_hash(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(M, "OUT", tmp_path)
    pts = M.cell_sigma("p", AMP, DIMS, S, [toy_paths(1, 40)], [toy_paths(2, 10, ("A",))])
    sj = M.sigma_json({("p", AMP): pts})
    (tmp_path / "sigma.json").write_text(json.dumps({"hash": M.SIGMA_HASH, "cells": sj}))
    with pytest.raises(SystemExit):
        M.load_sigma()                                                 # the toy set is not the plan's Σ


def test_alignment_row():
    r = M.alignment_row(-36, 0, -53, -1, 16)
    assert r["judge_offset"] == 16 and r["judge_vs_gcc"] == 0 and r["gcc_lag_cprime"] == 1
    assert r["closure"] == 16 - (1 + 53 + 0) and not r["large_offset"]
    big = M.alignment_row(914, 0, 0, -1, -2)
    assert big["large_offset"] and big["judge_vs_gcc"] == 968


# --- step 0 ----------------------------------------------------------------------------------------------

def test_pregain_plan():
    plan = M.pregain_plan(S, dims=DIMS)
    assert [n for n, _, _ in plan] == ["warm-up", "di+6dB", "knob+6dB", "di-6dB", "knob-6dB"]
    by = {n: (s, x) for n, s, x in plan}
    assert by["di+6dB"][0] == pytest.approx(10 ** 0.3) and by["di+6dB"][1] == S
    assert by["knob+6dB"] == (1.0, {**S, M.INPUT_GAIN: "6"}) and by["warm-up"] == by["knob+6dB"]
    assert by["knob-6dB"][1][M.INPUT_GAIN] == "-6" and by["di-6dB"][0] == pytest.approx(10 ** -0.3)
    with pytest.raises(ValueError):
        M.pregain_plan({**S, M.INPUT_GAIN: "-18"}, dims=DIMS)


def test_residual_db():
    import numpy as np

    y = np.sin(np.arange(1000) / 7.0)
    assert M.residual_db(y, y) == -math.inf
    assert M.residual_db(y * 1.1, y) == pytest.approx(20 * math.log10(0.1), abs=1e-6)
    z = y.copy()
    z[:100] = 5
    assert M.residual_db(z, y, skip=100) == -math.inf


def test_sign3_and_knob_regression():
    assert M.sign3(1.0, 0.5) == "+" and M.sign3(-1.0, 0.5) == "-" and M.sign3(0.2, 0.5) == "0"
    assert M.sign3(1.0, float("nan")) == "0"
    rng = random.Random(5)
    ig = next(d for d in DIMS if k(d) == M.INPUT_GAIN)
    tr = next(d for d in DIMS if d.key == "pr12Treble")
    xs, true, obj = [], {"A": [], "B": []}, {"A": [], "B": []}
    for _ in range(60):
        x = dict(S)
        a, b = rng.choice((-2, -1, 0, 1, 2)) / 8, rng.choice((-2, -1, 0, 1, 2)) / 8
        x[k(ig)] = K.fmt(ig.from_unit(L.unit(ig, S) + a))
        x[k(tr)] = K.fmt(tr.from_unit(L.unit(tr, S) + b))
        xs.append(x)
        for h in "AB":
            lt = 1.0 + 2.0 * a - 1.0 * b + 0.01 * rng.random()
            true[h].append(math.exp(lt))
            obj[h].append(math.exp(lt - 3.0 * a))                     # obj prefers more input gain
    reg = M.knob_regression(DIMS, S, xs, obj, true)
    for h in "AB":
        assert set(reg[h]) == {"parameters/inputGain", "pr12Amp/pr12Treble"}
        g = reg[h]["parameters/inputGain"]
        assert g["bias"] == pytest.approx(-3.0, abs=0.05) and g["true"] == "+" and g["obj"] == "-"
        t = reg[h]["pr12Amp/pr12Treble"]
        assert t["bias"] == pytest.approx(0.0, abs=0.05) and t["true"] == t["obj"] == "-"


def test_first_divergence():
    a, b = dict(S), dict(S)
    d1, d2 = DIMS[0], DIMS[1]
    p1 = {**S, k(d1): "4"}
    p2 = {**S, k(d2): K.fmt(d2.from_unit(0.9))}
    path_a = [(S, 1), (p1, 1), (p2, 1), ({**p2, k(d1): "8"}, 1)]
    path_b = [(S, 1), (p1, 1), (p2, 1), ({**S, k(d1): "8"}, 1)]
    n, agreed, diff = M.first_divergence(path_a, path_b)
    assert n == 3 and diff == [k(d2)] and agreed == [k(d1)]
    assert M.first_divergence(path_a, path_a)[0] == 4 and M.first_divergence(path_a, path_a)[2] == []
    del a, b


def test_knob_order():
    names = ["cabParameters/rightCabActive", "cabParameters/leftCabPosition", "pr12Amp/pr12Treble",
             "sw50rAmp/sw50rBright", "parameters/inputGain"]
    assert sorted(names, key=M.knob_order) == ["parameters/inputGain", "pr12Amp/pr12Treble",
                                               "cabParameters/leftCabPosition", "sw50rAmp/sw50rBright",
                                               "cabParameters/rightCabActive"]


def test_limit_side():
    ig = next(d for d in DIMS if k(d) == M.INPUT_GAIN)
    assert M.limit_side(ig, {M.INPUT_GAIN: "-20"}) == "lo" and M.limit_side(ig, {M.INPUT_GAIN: "12"}) == "hi"
    assert M.limit_side(ig, {M.INPUT_GAIN: "0"}) == "interior"


# --- guards and audio ----------------------------------------------------------------------------------

def test_disk_guard():
    assert M.disk_ok(36.7, 7056)                                     # 36.7 − 4.9 ≥ 31
    assert not M.disk_ok(35.0, 7056)
    assert M.disk_ok(31.1, 97) and not M.disk_ok(31.05, 97)


def test_render_process_patterns():
    py = "/Users/x/.venv/bin/python"
    assert M.is_render_process(f"{py} -m learn.local_objective render --shard 0/3")
    assert M.is_render_process(f"{py} -m learn.local_objective pregain")
    assert not M.is_render_process(f"{py} -m learn.local_objective score --workers 3")
    assert M.is_render_process(f"{py} -m learn.ks_extend run --shard 1/3")
    assert M.is_render_process(f"{py} -m learn.song_soundspace score-targets --arm B1 --shard 0/3")
    assert not M.is_render_process(f"{py} -m learn.song_soundspace train --arm B1 --fold 2")
    assert not M.is_render_process("zsh -c 'python -m learn.local_objective render'")
    assert M.others_rendering([(1, f"{py} -m learn.local_objective render"), (2, "vim")], own={3}) == [1]


def test_flac_roundtrip(tmp_path):
    import numpy as np

    pytest.importorskip("soundfile")
    rng = np.random.default_rng(0)
    y = 0.03 * rng.standard_normal(48000)
    sc = M.save_flac(tmp_path / "a" / "00.flac", y)
    z = M.load_flac(tmp_path / "a" / "00.flac", sc)
    assert sc == pytest.approx(np.abs(y).max() / M.PEAK_TO)
    assert np.max(np.abs(z - y)) <= sc / 2 ** 15 + 1e-12          # within half a 16-bit step
    assert not list((tmp_path / "a").glob("*.tmp*"))


# --- the stored data, where it exists (zero renders) ----------------------------------------------------

STORED = (K.OUT / "cells" / "cambridge-Prodigal-ElecGtr5" / "pr12" / "result.json").exists() and \
    (L.SS_OUT / "armA" / "cambridge-Prodigal-ElecGtr5" / "pr12" / "A.json").exists()


@pytest.mark.skipif(not STORED, reason="needs the Mac's stored knob-ceiling and arm A files")
def test_stored_cell_sigma_replays_exactly():
    slug, amp = "cambridge-Prodigal-ElecGtr5", "pr12"
    ps = K.parts()
    S0 = L.menu_S()[amp][ps[slug]["gain_class"]][1]
    c = M._kc(slug, amp)
    ks, aa = [], []
    for search, _ in K.DIRECTIONS:
        t, x = L.replay_ks(amp, S0, c["runs"][search]["K_S"]["evals"], search)
        assert x == L._settings(K.OUT / "cells" / slug / amp / f"K_S-{search}.json")
        ks.append(t)
        stored, xa = L.stored_a(slug, amp, search)
        path, x = M.arm_a_path(amp, S0, stored["objective_curve"])
        assert x == xa
        aa.append([(xx, {search: v}) for xx, v in path])
    pts = M.cell_sigma(slug, amp, K.space(amp, S0), S0, ks, aa)
    assert len(pts) == 48 and pts[0]["source"] == "S"
    # S's stored true d is K_S's first render, a repeat of the stored menu render (within 0.005)
    assert all(M.deviation(pts[0]["true_stored"][h], c["menu"][c["start"]][h]) < M.CHECK_TOL for h in "AB")
