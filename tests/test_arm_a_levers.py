"""Arm A's levers (`learn/arm_a_levers.py`, docs/arm-a-levers-plan.md): the variant table, the
main stage and the zero-render replays, fidelity, ensembles and the tie rule. Synthetic inputs,
plus the replay of every stored search where the data exist."""

import inspect
import json
import math
import random

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import arm_a_levers as L  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402

AMP = "sw50r"


def preset(seed, mics=("3", "5"), switches="false"):
    """A full preset over sw50r's searched space, plus settings outside it."""
    rng = random.Random(seed)
    x = {("parameters", "outputGain"): "5.96", ("delay", "delayActive"): "false",
         ("cabParameters", "leftCabActive"): "true"}
    for d in K.space(AMP):
        if d.kind == "cat":
            x[(d.module, d.key)] = mics[0] if d.key.startswith("left") else mics[1]
        elif d.kind == "switch":
            x[(d.module, d.key)] = switches
        else:
            x[(d.module, d.key)] = K.fmt(d.from_unit(rng.random()))
    return x


S = preset(1)
A = preset(2, mics=("7", "1"), switches="true")
A2 = preset(3, mics=("2", "8"), switches="false")
DIMS = K.space(AMP, S)
CONT = [d for d in DIMS if d.kind in ("cont", "log")]
CATS = [d for d in DIMS if d.kind == "cat"]
SWS = [d for d in DIMS if d.kind == "switch"]


def k(d):
    return (d.module, d.key)


# --- the variant table -------------------------------------------------------------------------------

def test_space_has_no_log_dims():
    assert all(d.kind != "log" for d in DIMS)


def test_shrink_endpoints_are_S_and_A():
    zero, one = L.shrink(DIMS, S, A, 0.0), L.shrink(DIMS, S, A, 1.0)
    assert all(zero[k(d)] == S[k(d)] for d in CONT)
    assert one == A


def test_shrink_moves_knobs_in_unit_space_and_keeps_A_mics_and_switches():
    x = L.shrink(DIMS, S, A, 0.5)
    for d in CONT:
        want = (d.to_unit(S[k(d)]) + d.to_unit(A[k(d)])) / 2
        assert d.to_unit(x[k(d)]) == pytest.approx(want, abs=1e-5)
    assert all(x[k(d)] == A[k(d)] for d in CATS + SWS)
    assert x[("parameters", "outputGain")] == S[("parameters", "outputGain")]


def test_s_mics_takes_only_the_mics_from_S():
    x = L.s_mics(DIMS, S, A)
    assert all(x[k(d)] == A[k(d)] for d in CONT + SWS)
    assert all(x[k(d)] == S[k(d)] for d in CATS)


def test_blend_keeps_S_mics_and_switches():
    x = L.blend(DIMS, S, A, 0.5)
    assert all(x[k(d)] == S[k(d)] for d in CATS + SWS)
    assert x == L.shrink(DIMS, S, A, 0.5) | {k(d): S[k(d)] for d in CATS + SWS}


def test_dirs_avg_is_symmetric_in_the_knobs_and_takes_this_directions_mics():
    a, b = L.dirs_avg(DIMS, S, A, A2), L.dirs_avg(DIMS, S, A2, A)
    assert all(a[k(d)] == b[k(d)] for d in CONT)
    assert all(a[k(d)] == A[k(d)] for d in CATS + SWS)
    assert all(b[k(d)] == A2[k(d)] for d in CATS + SWS)


def test_no_key_outside_the_space_changes_and_a_differing_source_is_refused():
    for x in L.variants(DIMS, S, A, A2, A2, A).values():
        inside = {k(d) for d in DIMS}
        assert {kk: v for kk, v in x.items() if kk not in inside} == {kk: v for kk, v in S.items() if kk not in inside}
    bad = dict(A)
    bad[("delay", "delayActive")] = "true"
    with pytest.raises(ValueError):
        L.shrink(DIMS, S, bad, 0.5)


def test_a_missing_key_counts_as_lo():
    d = CONT[0]
    s = {kk: v for kk, v in S.items() if kk != k(d)}
    a = dict(A)
    a[k(d)] = K.fmt(d.from_unit(0.5))
    x = L.shrink(DIMS, s, a, 0.5)
    assert d.to_unit(x[k(d)]) == pytest.approx(0.25, abs=1e-5)
    assert k(d) not in L.shrink(DIMS, s, a, 0.0)          # unchanged from S: S's (missing) value kept


def test_variants_table_names_and_levers():
    assert set(L.variants(DIMS, S, A, A2, A2, A)) == set(L.EXP1_RENDERED)
    assert L.lever("S-mics", DIMS, S, A) == L.s_mics(DIMS, S, A)
    assert L.lever("shrink-0.25", DIMS, S, A) == L.shrink(DIMS, S, A, 0.25)
    assert set(L.EXP1_ORDER) | set(L.REPORTED_ONLY) >= {"S", "menu_pick", "A"} | set(L.EXP1_RENDERED)
    assert "dirs-avg" not in L.EXP1_ORDER


# --- the main stage and the replays ----------------------------------------------------------------

def toy(target_seed=9):
    t = preset(target_seed, mics=("4", "6"), switches="true")

    def f(x):
        v = sum((d.to_unit(x[k(d)]) - d.to_unit(t[k(d)])) ** 2 for d in CONT)
        v += sum(0.05 * (x[k(d)] != t[k(d)]) for d in CATS + SWS)
        return 1.0 + v
    return f


class Rec:
    def __init__(self, f):
        self.f, self.xs, self.vs = f, [], []

    def __call__(self, x):
        v = self.f(x)
        self.xs.append(K.key(x))
        self.vs.append(v)
        return v


def test_main_stage_equals_knob_search_main_stage():
    full, main = Rec(toy()), Rec(toy())
    _, _, _, stages = K.knob_search(DIMS, S, full, 150, L.SEED)
    x, best, n = L.main_stage(DIMS, S, main)
    assert n == stages["main"]["renders"] == 52
    assert best == stages["main"]["best"]
    assert main.xs == full.xs[:n]


def test_replay_reproduces_a_live_search_with_zero_evaluations():
    live = Rec(toy(11))
    x, best, _, stages = K.knob_search(DIMS, S, live, 150, L.SEED)
    stored = {"objective_curve": live.vs, "objective_best": best, "stages": stages}
    rep = L.replay_arm_a(AMP, S, stored)
    assert L.replay_mismatches(rep, stored, x) == []
    mx, mbest, _ = L.main_stage(DIMS, S, Rec(toy(11)))
    assert rep["main_x"] == mx and rep["main_best"] == mbest


def test_replay_mismatch_is_reported():
    live = Rec(toy(12))
    x, best, _, stages = K.knob_search(DIMS, S, live, 150, L.SEED)
    stored = {"objective_curve": live.vs, "objective_best": best + 1e-6, "stages": stages}
    assert "objective_best" in L.replay_mismatches(L.replay_arm_a(AMP, S, stored), stored, x)


def test_replay_past_the_curve_raises():
    r = L.Replay([1.0])
    r({})
    with pytest.raises(RuntimeError):
        r({})


def test_replay_ks_pairs_settings_with_both_halves():
    live = Rec(toy(13))
    x, _, _, _ = K.knob_search(DIMS, S, live, 150, K.SEED)
    evals = [(v, v + 1) for v in live.vs]
    traj, xr = L.replay_ks(AMP, S, evals, "A")
    assert xr == x and len(traj) == len(evals)
    assert [K.key(s) for s, _ in traj] == live.xs
    assert traj[0][1] == {"A": evals[0][0], "B": evals[0][1]}


def _stored_data():
    return (L.SS_OUT / "armA").exists() and (L.SS_OUT / "armB" / "menu-S.json").exists()


@pytest.mark.skipif(not _stored_data(), reason="no stored song-settings data")
def test_every_stored_arm_a_search_replays_exactly():
    ms = L.menu_S()
    n = 0
    for f in sorted((L.SS_OUT / "armA").glob("*/*/[AB].json")):
        stored = json.loads(f.read_text())
        S0 = ms[stored["amp"]][stored["gain_class"]][1]
        x = L._settings(f.parent / f"{stored['search_half']}-settings.json")
        assert L.replay_mismatches(L.replay_arm_a(stored["amp"], S0, stored), stored, x) == [], f
        n += 1
    assert n == 144


@pytest.mark.skipif(not _stored_data() or not (K.OUT / "cells").exists(), reason="no stored knob-ceiling data")
def test_every_stored_ks_trajectory_replays_exactly():
    ms, ps = L.menu_S(), K.parts()
    n = 0
    for f in sorted((K.OUT / "cells").glob("*/*/result.json")):
        slug, amp = f.parent.parent.name, f.parent.name
        if slug not in ps:
            continue
        r = json.loads(f.read_text())
        for search, run in r["runs"].items():
            if "K_S" not in run:
                continue
            _, x = L.replay_ks(amp, ms[amp][ps[slug]["gain_class"]][1], run["K_S"]["evals"], search)
            st = L._settings(f.parent / f"K_S-{search}.json")
            assert all(x.get(kk) == st.get(kk) for kk in set(x) | set(st)), (slug, amp, search)
            n += 1
    assert n >= 144


def test_local_draw_dedupes_and_is_deterministic():
    xs = [({("m", "k"): str(i % 30)}, {"A": 1.0, "B": 1.0}) for i in range(90)]
    t = {("p", "pr12"): xs, ("q", "ac20"): xs[:10]}
    a, b = L.local_draw(t), L.local_draw(t)
    assert a == b
    assert len(a[("p", "pr12")]) == 30 and len(a[("q", "ac20")]) == 10
    assert len({K.key(x) for x, _ in a[("p", "pr12")]}) == 30


# --- objectives and fidelity -------------------------------------------------------------------------

def test_ensemble_is_the_mean_log_and_a_non_finite_member_makes_the_preset_inf():
    e = L.ensemble_objective([{"a": 2.0, "b": 3.0, "c": 1.0}, {"a": 8.0, "b": math.inf, "c": 1.0}])
    assert e["a"] == pytest.approx(math.log(4.0))
    assert e["b"] == math.inf and e["c"] == 0.0


def test_rank_fidelity_drops_non_finite_pairwise():
    obj = {"a": 1.0, "b": 2.0, "c": 3.0, "d": math.inf, "e": 5.0}
    true = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0, "e": float("nan")}
    assert L.rank_fidelity(obj, true) == pytest.approx(1.0)
    assert L.rank_fidelity({"a": 1.0, "b": 2.0}, {"a": 1.0, "b": 2.0}) is None


def test_objective_lag_matches_rebuilt_distance_default():
    from learn import rebuilt_judge as RJ

    assert inspect.signature(RJ.rebuilt_distance).parameters["lag"].default == -RJ.LATENCY == L.OBJ_LAG
    assert L.objective_lag(0) == -52 and L.objective_lag(3) == -55


def test_pick_is_the_lowest_finite():
    assert L.pick({"b": 1.0, "a": 1.0, "c": math.inf}) == "a"
    assert L.pick({"c": math.inf}) is None


# --- the decision ------------------------------------------------------------------------------------

def rows(values, bands=None):
    """{key: (slug, band, value)}: one part per band unless `bands` maps index -> band."""
    return {(f"p{i}", "pr12", "A"): (f"p{i}", (bands or {}).get(i, f"b{i}"), v) for i, v in enumerate(values)}


def test_choose_takes_the_cheapest_within_noise():
    rng = random.Random(0)
    vals = {"S": rows([0.0] * 14), "X": rows([rng.gauss(-0.01, 0.1) for _ in range(14)]),
            "Y": rows([rng.gauss(-0.30, 0.02) for _ in range(14)])}
    ch = L.choose(vals, ("S", "X", "Y"))
    assert ch["best"] == "Y" and ch["chosen"] == "Y"             # Y clearly better than S and X
    vals["Y"] = rows([v + rng.gauss(0.0, 0.2) for v in [-0.02] * 14])
    ch = L.choose(vals, ("S", "X", "Y"))
    assert "S" in ch["tied_with_best"] or ch["best"] == "S"
    assert ch["chosen"] == "S"


def test_choose_higher_is_better_for_fidelity():
    vals = {"C'": rows([0.70, 0.72, 0.71, 0.69]), "1a": rows([0.90, 0.92, 0.91, 0.93])}
    ch = L.choose(vals, ("C'", "1a"), lower=False)
    assert ch["best"] == "1a" and ch["chosen"] == "1a"


def test_wider_interval_uses_the_parts_when_three_bands_look_tight():
    # 3 bands with near-identical band means but parts that disagree: the band interval excludes
    # 0, the part interval (4 df) does not.
    bands = {0: "b0", 1: "b0", 2: "b1", 3: "b1", 4: "b2"}
    best = rows([0.0] * 5, bands)
    other = rows([0.40, -0.30, 0.45, -0.35, 0.05], bands)
    m, lo, hi = L.interval([(s, b, other[kk][2] - best[kk][2]) for kk, (s, b, _) in best.items()])
    assert lo > 0 or hi < 0
    m, lo, hi = L.interval([(s, b, other[kk][2] - best[kk][2]) for kk, (s, b, _) in best.items()], wider=True)
    assert lo <= 0 <= hi
    ch = L.choose({"C'": best, "1a": other}, ("C'", "1a"), lower=False, wider=True)
    assert ch["best"] == "1a" and ch["chosen"] == "C'"


def test_drop_follows_the_readout_rule_for_the_new_candidates():
    u = [{"slug": "p", "band": "b", "cls": "clean", "amp": "pr12", "search": "A", "held": "B",
          "d": {"S": 1.0, "A": 0.9, "shrink-0.5": math.inf}},
         {"slug": "q", "band": "c", "cls": "clean", "amp": "pr12", "search": "A", "held": "B",
          "d": {"S": 1.0, "A": 0.9, "shrink-0.5": 0.8}}]
    kept, dropped = L.drop(u, ("shrink-0.5",))
    assert [x["slug"] for x in kept] == ["q"] and dropped[0][0] == "p"


def test_log_rows_and_caps():
    u = [{"slug": "p", "band": "b", "amp": "pr12", "search": "A", "d": {"S": 2.0, "A": 1.0}}]
    assert L.log_rows(u, "A")[("p", "pr12", "A")][2] == pytest.approx(math.log(0.5))
    assert sum(L.CAPS.values()) == 20_550
