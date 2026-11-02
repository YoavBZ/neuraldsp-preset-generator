import argparse
import json
import math

import pytest

from learn import pipeline_fix as P
from learn import pipeline_review as PR


def test_t95_matches_the_reviews_seven_band_value_and_falls_back_to_the_normal():
    assert P.t95(6) == pytest.approx(PR.T_95[6], abs=1e-4)
    assert P.t95(200) == pytest.approx(1.6449)
    assert P.t95(0) is None


def test_clustered_averages_parts_then_clusters_with_a_t_interval():
    rows = [("b1", "p1", 1.0), ("b1", "p1", 3.0), ("b1", "p2", 0.0), ("b2", "p3", -1.0), ("b3", "p4", 0.0)]
    r = P.clustered(rows)
    means = [1.0, -1.0, 0.0]
    half = P.t95(2) * math.sqrt(sum((m - 0.0) ** 2 for m in means) / 2) / math.sqrt(3)
    assert r["mean"] == 0.0 and r["clusters"] == 3
    assert r["hi90"] == pytest.approx(half) and r["lo90"] == pytest.approx(-half)
    assert r["part_weighted"] == pytest.approx((2.0 + 0.0 - 1.0 + 0.0) / 4)
    assert r["clusters_negative"] == 1 and r["clusters_positive"] == 1
    assert r["leave_one_out"]["b1"] == pytest.approx(-0.5)


def test_clustered_of_nothing_is_empty():
    assert P.clustered([])["mean"] is None


def _dist(**presets):
    return {f"flat|{amp}|measfix_{h}": {p: [v] for p, v in presets.items()} for amp in PR.AMPS for h in "AB"}


def test_start_rules_drop_the_excluded_parts():
    files = [{"a": _dist(**{"factory:X": 1.0, "factory:Y": 2.0}),
              "b": _dist(**{"factory:X": 5.0, "factory:Y": 2.0}),
              "c": _dist(**{"factory:X": 5.0, "factory:Y": 2.0})}]
    pinned = {p: {"gain_class": "clean", "band": "B"} for p in "abc"}
    full = P.start_rules(files, pinned, set())
    assert full["clean"]["per_amp"]["pr12"][0] == "factory:Y"           # medians X 5, Y 2
    less = P.start_rules(files, pinned, {"b", "c"})
    assert less["clean"]["per_amp"]["pr12"] == ("factory:X", 1.0, 1)
    assert less["crunch"]["parts"] == 0


def test_s_prime_rows_reads_stored_distances_and_lists_what_needs_renders():
    choice = {c: {"presets": {a: "factory:S" for a in PR.AMPS}} for c in ("clean", "crunch")}
    rules = {"clean": {"per_amp": {a: ("factory:N" if a == "pr12" else "factory:S", 0, 1) for a in PR.AMPS}},
             "crunch": {"per_amp": {a: ("factory:S", 0, 1) for a in PR.AMPS}}}
    vreal = {"p": ("B1", "clean"), "q": ("B2", "crunch"), "r": ("B3", "clean")}
    files = [{"p": _dist(**{"factory:S": 2.0, "factory:N": 1.0})}]
    rows, missing = P.s_prime_rows(files, vreal, choice, rules)
    vals = [v for b, s, v in rows if s == "p"]
    assert vals.count(0.0) == 4 and sorted(vals)[:2] == [pytest.approx(math.log(0.5))] * 2
    assert all(v == 0.0 for _, s, v in rows if s == "q")
    assert missing == [("r", "pr12")]


def test_s_prime_rows_never_reads_t3s_own_crop_from_the_distance_files():
    slug = next(iter(PR.IN_GROUP_S))
    choice = {c: {"presets": {a: "factory:S" for a in PR.AMPS}} for c in ("clean", "crunch")}
    rules = {c: {"per_amp": {a: ("factory:N", 0, 1) for a in PR.AMPS}} for c in ("clean", "crunch")}
    files = [{slug: _dist(**{"factory:S": 2.0, "factory:N": 1.0})}]
    _, missing = P.s_prime_rows(files, {slug: ("B", "clean")}, choice, rules)
    assert len(missing) == 3


def test_double_status_compares_the_doubles_setting_with_the_label():
    lab = {PR.SWITCHES[k]: "false" for k in P.DOUBLE_SWITCHES}
    lab.update({PR.SWITCHES["drive2"]: "true", PR.SWITCHES["delay"]: "true", "x/knob": "0.5"})
    core = dict(lab, **{PR.SWITCHES["delay"]: "false", "x/knob": "0.6"})
    assert P.double_status({"others": [{"dt": False}], "core": core, "settings": lab}) is None
    st = P.double_status({"others": [{"dt": True}], "core": core, "settings": lab})
    assert st == {"switches_differ": ["delay"], "settings_differ": 2}


def test_auc_counts_ties_half_and_needs_both_classes():
    assert P.auc([0.9, 0.1], [True, False]) == 1.0
    assert P.auc([0.5, 0.5], [True, False]) == 0.5
    assert P.auc([0.2, 0.9, 0.4], [True, False, False]) == 0.0
    assert P.auc([0.2], [True]) is None


def test_cluster_boot_is_seeded_and_brackets_a_constant_statistic():
    items = list(range(20))
    clusters = [i % 5 for i in items]
    lo, hi = P.cluster_boot(items, lambda xs: 1.0, clusters, n=50)
    assert lo == hi == 1.0
    a = P.cluster_boot(items, lambda xs: sum(xs) / len(xs), clusters, n=200)
    assert a == P.cluster_boot(items, lambda xs: sum(xs) / len(xs), clusters, n=200)
    assert a[0] <= 9.5 <= a[1]


def test_real_runs_refuse_without_the_phase_in_the_ledger(monkeypatch):
    monkeypatch.setattr(P, "ledger_entry", lambda: {"test_id": P.LEDGER_ID})
    with pytest.raises(SystemExit):
        P.require("phase_1")


def test_session_of_a_section():
    assert P.session_of("cambridge/AdamBuckley_DragMeDown_Full/31_ElecGtr3DI.wav@130.0") == \
        "cambridge/AdamBuckley_DragMeDown_Full"


def test_recipe_split_holds_out_whole_songs_and_drops_dirty_examples():
    ns = P.NS_SESSIONS[0]
    kept = {1: {"section": f"{ns}/a.wav@0.0"}, 2: {"section": "s/Other_Full/a.wav@0.0"},
            3: {"section": f"{ns}/b.wav@5.0"}, 4: {"section": "s/Other_Full/a.wav@5.0"},
            5: {"section": "s/Other_Full/b.wav@0.0"}}
    sp = P.recipe_split(kept, tr_ids=[1, 2, 5], fs_ids=[3, 4], drop={5})
    assert sp["ns"] == [1, 3] and sp["train"] == [2] and sp["fs"] == [4]
    assert sp["dropped"] == {"train": 1, "fs": 0, "ns": 0}


def test_nested_subset_keeps_one_per_section_and_nests():
    sec = {i: f"s{i % 4}" for i in range(40)}
    a = P.nested_subset(list(range(40)), sec, 0.25)
    b = P.nested_subset(list(range(40)), sec, 0.5)
    c = P.nested_subset(list(range(40)), sec, 1.0)
    assert set(a) <= set(b) <= set(c) and len(c) == 40
    assert len(a) == 4 * 3 and len({sec[i] for i in a}) == 4
    assert len(P.nested_subset([0, 4], sec, 0.01)) == 1          # one section, at least one example


def test_gmm1d_fits_two_clusters_and_its_nll_is_lower_on_the_data():
    np = pytest.importorskip("numpy")

    rng = np.random.default_rng(0)
    x = np.concatenate([rng.normal(0.2, 0.02, 200), rng.normal(0.8, 0.02, 200)])
    w, mu, sd = P.gmm1d(x)
    assert abs(sum(w) - 1) < 1e-9 and np.all(sd >= math.exp(-6) - 1e-12)
    assert P.gmm1d_nll(0.2, w, mu, sd) < P.gmm1d_nll(0.5, w, mu, sd)
    w1, mu1, sd1 = P.gmm1d([0.3])
    assert list(mu1) == [0.3]


def test_baseline_switch_rate_and_amp_frequency():
    np = pytest.importorskip("numpy")

    from learn import full_space as F

    n, nk, ns, nc = 4, len(F.CONT), len(F.SW), len(F.CAT)
    Y = (np.zeros((n, nk), np.float32), np.zeros((n, nk), np.float32),
         np.array([[1.0] * ns, [1.0] * ns, [0.0] * ns, [1.0] * ns], np.float32), np.ones((n, ns), np.float32),
         np.zeros((n, nc), np.int64), np.ones((n, nc), np.float32), np.array([0, 0, 1, 2]))
    cells = [("pr12", "clean")] * n
    b = P.Baseline(Y, cells)
    assert b.sw[cells[0]][0] == (3 + 0.5) / (4 + 1)
    assert b.amp[0] == (2 + 0.5) / (4 + 1.5)
    out = b.losses(Y, cells)
    assert out["amp_n"] == 4 and out["sw_n"][0] == 4 and out["knob_n"].sum() == 0
    fam = P.family_means(out)
    assert fam["knob_marginal"] is None and fam["switch"] > 0


def test_draw_order_spreads_over_sections_and_is_stable():
    sec = {i: f"s{i % 3}" for i in range(9)}
    o = P.draw_order(list(range(9)), sec, n=6)
    assert len(o) == 6 and len(set(o)) == 6
    assert sorted(sec[i] for i in o[:3]) == ["s0", "s1", "s2"]          # one per section per round
    assert o == P.draw_order(list(range(9)), sec, n=6)
    assert P.draw_order(list(range(9)), sec, n=20)[:6] == o              # growing keeps the first ones


def test_log_ratio_averages_halves_and_refuses_missing():
    assert P.log_ratio({"A": 2.0, "B": 2.0}, {"A": 1.0, "B": 1.0}) == pytest.approx(math.log(2))
    assert P.log_ratio({"A": 2.0, "B": math.inf}, {"A": 1.0, "B": 1.0}) is None
    assert P.log_ratio(None, {"A": 1.0, "B": 1.0}) is None


def test_fold_split_and_section_share():
    kept = {1: {"band": "Forkupines"}, 2: {"band": "BKS"}, 3: {"band": "Hazael"}}
    assert P.fold_split(kept, [1, 2, 3], 0) == ([2, 3], [1])
    assert set().union(*(set(v) for v in P.FOLDS.values())) >= {"Forkupines", "BKS", "Hazael", "Adam Buckley"}
    sec = {i: f"s{i // 2}" for i in range(10)}
    half = P.section_share(list(range(10)), sec, 0.4)
    assert len({sec[i] for i in half}) == 2 and all(sec[j] in {sec[i] for i in half} for j in half)
    assert all(sum(1 for j in half if sec[j] == sec[i]) == 2 for i in half)   # every example of a kept section


def test_run_names():
    assert P.run_name("a") == "P2a"
    assert P.run_name("d", aug=True) == "P2d-aug"
    assert P.run_name("a", frac=0.25) == "P2a-f25"
    assert P.run_name("d", sections=0.5) == "P2d-s50"
    assert P.run_name("a", fold=3) == "P2a-k3"


def test_rung_mixes_rebuild_the_mix_and_drop_every_other_guitar():
    np = pytest.importorskip("numpy")

    y, oth, stems = np.ones(4), np.full(4, 2.0), np.full(4, 3.0)
    gains = {"ga": 20 * math.log10(2), "gb": 20 * math.log10(0.5)}
    a, b, c = P.rung_mixes(y, oth, stems, {}, gains, lambda z: z)
    assert np.allclose(a, 2.0)                          # the target at its gain in the mix
    assert np.allclose(b, (1 + 3 * 0.5) * 2)            # no other guitar, the same gains
    assert np.allclose(c, (1 + 5 * 0.5) * 2)            # the full mix


def test_every_run_and_read_conditions_on_the_section_class():
    import inspect

    src = inspect.getsource(P.RungData.batch) + inspect.getsource(P.read_inputs)
    assert 'r["cls"]' in src and 'r["base"]' not in src
    assert 'base=r["cls"]' in inspect.getsource(P.arm_data)
    assert 'base=r["cls"]' in inspect.getsource(P.constant_of)


def test_vreal_rows_count_wickerman_2_and_3_as_one_input_and_use_any_half_comparators():
    units = [("cambridge-wickerman-elecgtr2", "pr12", "A", "B"), ("cambridge-wickerman-elecgtr3", "pr12", "A", "B"),
             ("cambridge-femme-elecgtr5", "pr12", "B", "A")]
    judge = {"m": {"cambridge-wickerman-elecgtr2|pr12": {"A": {"B": 1.0}},
                   "cambridge-wickerman-elecgtr3|pr12": {"A": {"B": 4.0}},
                   "cambridge-femme-elecgtr5|pr12": {"B": {"A": 2.0}}},
             "S": {"cambridge-wickerman-elecgtr2|pr12": {"*": {"A": 9.0, "B": 2.0}},
                   "cambridge-wickerman-elecgtr3|pr12": {"*": {"A": 9.0, "B": 2.0}},
                   "cambridge-femme-elecgtr5|pr12": {"*": {"A": 1.0, "B": 9.0}}}}
    rows, cnt = P.vreal_rows(judge, "m", "S", units)
    assert cnt["complete"] and cnt["missing"] == 0
    assert {r[1] for r in rows} == {"cambridge-wickerman-elecgtr2+3", "cambridge-femme-elecgtr5"}
    assert sorted(round(r[2], 6) for r in rows) == sorted([round(math.log(0.5), 6), round(math.log(2.0), 6),
                                                           round(math.log(2.0), 6)])
    own, _ = P.vreal_rows(judge, "m", "S", units, own_inputs=True)
    assert {r[1] for r in own} == {"cambridge-wickerman-elecgtr2", "cambridge-wickerman-elecgtr3",
                                   "cambridge-femme-elecgtr5"}
    c = P.clustered(rows)
    assert c["parts"] == 2 and c["clusters"] == 2
    assert P.part_members("cambridge-wickerman-elecgtr2+3") == ["cambridge-wickerman-elecgtr2",
                                                                "cambridge-wickerman-elecgtr3"]


def test_vreal_rows_score_a_refused_answer_as_s_drop_s_refusals_and_flag_missing():
    u1 = ("cambridge-femme-elecgtr5", "pr12", "A", "B")
    u2 = ("cambridge-femme-elecgtr5", "ac20", "A", "B")
    u3 = ("cambridge-femme-elecgtr5", "sw50r", "A", "B")
    judge = {"m": {"cambridge-femme-elecgtr5|pr12": {"A": {"B": math.inf}},
                   "cambridge-femme-elecgtr5|ac20": {"A": {"B": 1.0}}},
             "S": {"cambridge-femme-elecgtr5|pr12": {"*": {"B": 2.0}},
                   "cambridge-femme-elecgtr5|ac20": {"*": {"B": math.inf}},
                   "cambridge-femme-elecgtr5|sw50r": {"*": {"B": 2.0}}}}
    rows, cnt = P.vreal_rows(judge, "m", "S", [u1, u2, u3])
    assert [round(r[2], 9) for r in rows] == [0.0]            # u1: refused, scored as S
    assert cnt == {"directions": 3, "base_dropped": 1, "missing": 1, "refused_scored_as_S": 1, "complete": False}


def test_backing_draws_never_use_the_examples_own_song():
    kept = {1: {"section": "s/A_Full/a.wav@0.0"}, 2: {"section": "s/A_Full/b.wav@5.0"},
            3: {"section": "s/B_Full/a.wav@0.0"}, 4: {"section": "s/C_Full/a.wav@0.0"}}
    d = P.backing_draws([1, 2, 3, 4], kept, k=20)
    for i, draws in d.items():
        assert len(draws) == 20
        assert all(P.session_of(sec) != P.session_of(kept[i]["section"]) for sec, _ in draws)
    assert d == P.backing_draws([1, 2, 3, 4], kept, k=20)
    only = P.backing_draws([1], kept, k=5, secs=["s/C_Full/a.wav@0.0"])
    assert {sec for sec, _ in only[1]} == {"s/C_Full/a.wav@0.0"}


def test_wide_draws_never_use_the_examples_own_song():
    kept = {1: {"section": "s/A_Full/a.wav@0.0"}, 2: {"section": "s/B_Full/x/a.wav@5.0"}}
    entries = [{"session": "s/A_Full"}, {"session": "s/B_Full/x"}, {"session": "A_Full"}, {"session": "C_Full"},
               {"session": "D_Full"}]
    d = P.wide_draws([1, 2], kept, entries, k=30, seed=7)
    for i, draws in d.items():
        assert len(draws) == 30
        own = P.session_of(kept[i]["section"])
        for j, _ in draws:
            assert entries[j]["session"] not in (own, own.split("/")[-1])
    assert {entries[j]["session"] for j, _ in d[1]} <= {"s/B_Full/x", "C_Full", "D_Full"}
    assert "s/B_Full/x" not in {entries[j]["session"] for j, _ in d[2]}
    assert d == P.wide_draws([1, 2], kept, entries, k=30, seed=7)


def test_shifted_amp_cycles_through_the_other_amps():
    from learn import full_space as F

    for a in F.AMPS:
        assert P.shifted_amp(a, 0) == a
        assert {P.shifted_amp(a, 1), P.shifted_amp(a, 2)} == set(F.AMPS) - {a}
    assert P.amp_tag(0) == "" and P.amp_tag(2) == "-amp+2"


def test_sc_cont_is_S_when_the_model_reads_its_constant(monkeypatch):
    np = pytest.importorskip("numpy")
    from learn import full_space as F

    n = 6
    s_c = np.array([0.2, 0.5, 0.98, 0.0, 0.7, 0.3])
    s_cm = np.array([1.0, 1.0, 1.0, 1.0, 0.0, 0.0])                     # the last two do not sound in S
    monkeypatch.setattr(F, "encode", lambda x, amp: (s_c, s_cm))
    const = np.linspace(0.1, 0.9, n)
    on = s_cm > 0
    out = P.sc_cont({}, "pr12", const, const)
    assert np.allclose(out[on], s_c[on]) and np.allclose(out[~on], const[~on])
    shifted = P.sc_cont({}, "pr12", const + 0.05, const)
    assert np.allclose(shifted[on], np.clip(s_c[on] + 0.05, 0, 1))      # 0.98 + 0.05 clips to 1
    assert np.allclose(shifted[~on], (const + 0.05)[~on])
    nan_c = const.copy()
    nan_c[0] = np.nan
    assert P.sc_cont({}, "pr12", const + 0.05, nan_c)[0] == pytest.approx(0.15)   # no constant: the model's value


def test_search_halves_alternate_within_each_di():
    parts = [{"unit": f"u{j}", "di": d} for j, d in enumerate("aabab")]
    assert P.search_halves(parts) == {"u0": "A", "u1": "B", "u2": "A", "u3": "A", "u4": "B"}


def test_real_folds_pair_the_dis_and_balance_the_read_units():
    counts = {"d1": 6, "d2": 3, "d3": 4, "d4": 7, "d5": 4, "d6": 3, "d7": 3, "d8": 10}
    read = [{"di": d} for d, n in counts.items() for _ in range(n)]
    folds = P.real_folds(read, read)
    assert sorted(folds) == sorted(counts) and sorted(folds.values()) == [0, 0, 1, 1, 2, 2, 3, 3]
    per = [sum(counts[d] for d in folds if folds[d] == f) for f in range(4)]
    assert max(per) - min(per) == 5                     # d8 (10) pairs with a 3 at best: 13 against 8 at worst
    assert folds == P.real_folds(read, read)            # deterministic
    with pytest.raises(SystemExit):
        P.real_folds(read[:3], read[:3])


def test_preset_centred_drops_wide_draws_and_its_size_control_matches_by_section():
    modes = ["factory", "wide", "start", "wide", "factory", "start", "wide", "factory"]
    kept = {i: {"mode": m, "section": f"s{i % 3}"} for i, m in enumerate(modes)}
    ids = sorted(kept)
    pc = P.preset_centred(ids, kept)
    assert pc == [i for i in ids if modes[i] != "wide"]
    sz = P.preset_centred(ids, kept, sized=True)
    by = lambda xs: sorted(kept[i]["section"] for i in xs)                       # noqa: E731
    assert by(sz) == by(pc) and sz == P.preset_centred(ids, kept, sized=True)


def test_ceiling_rows_drop_a_refused_S_and_score_a_refused_answer_as_S():
    def rec(unit, s, best, shrunk):
        return {"unit": unit, "di": "d", "rig": "r", "held": "B", "s_judge": {"A": 1.0, "B": s},
                "best": {"judge": {"B": best}}, "shrunk": {"judge": {"B": shrunk}}}

    by_di, by_rig, cnt = P.ceiling_rows([rec("u1", 2.0, 1.0, math.inf), rec("u2", math.inf, 1.0, 1.0)])
    assert cnt == {"s_dropped": 1, "refused_as_S": 1}
    assert by_di["best"] == [("d", "u1", pytest.approx(math.log(0.5)))]
    assert by_di["shrunk"] == [("d", "u1", 0.0)] and by_rig["best"][0][0] == "r"


def test_cycled_repeats_in_order_to_a_fixed_count():
    assert P.cycled([1, 2, 3], 7) == [1, 2, 3, 1, 2, 3, 1] and P.cycled([], 5) == []


def test_rc_setting_moves_S_by_the_mean_deviation_and_takes_the_majority_switch():
    from learn import knob_ceiling as K

    knob = next(d for d in K.space("pr12") if d.kind == "cont")
    sw = next((d for d in K.space("pr12") if d.kind not in ("cont", "log", "cat")), None)
    dims = [knob] + ([sw] if sw else [])
    k = (knob.module, knob.key)
    S = {k: K.fmt(knob.from_unit(0.5))}
    labels = [{k: K.fmt(knob.from_unit(0.6))}, {k: K.fmt(knob.from_unit(0.8))}]
    if sw:
        ks = (sw.module, sw.key)
        S[ks] = sw.values[0]
        labels[0][ks] = labels[1][ks] = sw.values[1]
    out = P.rc_setting(dims, S, labels)
    assert knob.to_unit(out[k]) == pytest.approx(0.7, abs=1e-6)
    if sw:
        assert out[ks] == sw.values[1]
    assert P.rc_setting(dims, S, []) == S


def _real_records():
    """Four DIs in two folds, two classes, two amps: one labelled record per (unit, amp)."""
    by_unit = {f"u{j}": {"unit": f"u{j}", "di": f"d{j % 4}", "cls": "clean" if j % 2 else "crunch"} for j in range(8)}
    folds = {"d0": 0, "d1": 0, "d2": 1, "d3": 1}
    recs = [{"unit": u, "amp": amp, "label": {}} for u in by_unit for amp in ("pr12", "ac20")]
    return recs, by_unit, folds


def test_fold_records_never_hold_the_folds_own_dis_and_always_fill_an_epoch():
    recs, by_unit, folds = _real_records()
    for f in (0, 1):
        rows = P.fold_records(recs, by_unit, folds, f)
        assert len(rows) == P.REAL_PER_EPOCH
        assert all(folds[by_unit[r["unit"]]["di"]] != f for r in rows)
        assert {r["unit"] for r in rows} == {u for u, p in by_unit.items() if folds[p["di"]] != f}


def test_rc_records_take_only_other_fold_labels_of_the_same_amp_and_class():
    recs, by_unit, folds = _real_records()
    for prt in by_unit.values():
        for amp in ("pr12", "ac20"):
            got = P.rc_records(recs, by_unit, folds, prt, amp)
            assert got and all(r["amp"] == amp and by_unit[r["unit"]]["cls"] == prt["cls"]
                               and folds[by_unit[r["unit"]]["di"]] != folds[prt["di"]] for r in got)
            assert len(got) == sum(r["amp"] == amp and by_unit[r["unit"]]["cls"] == prt["cls"]
                                   and folds[by_unit[r["unit"]]["di"]] != folds[prt["di"]] for r in recs)


def test_lag_refused_takes_only_windows_off_their_recordings_lag():
    def recs(rig, lags):
        return [{"unit": f"{rig}@{j}", "rig": rig, "amp": amp, "lag": lag}
                for j, lag in enumerate(lags) for amp in ("pr12", "ac20")]

    got = P.lag_refused(recs("a", [93, 96, 91, 498, 93]) + recs("b", [-21, -94, -57, -57, -56, -56, -56, -57])
                        + recs("c", [84, 84]) + recs("d", [111, None, 109]) + recs("e", [87, 120]))
    assert got == {"a@3", "b@0", "b@1", "e@0", "e@1"}


def test_rigo_records_take_only_the_recordings_windows_clear_of_the_unit():
    starts = {"u0": 200.0, "u1": 205.0, "u2": 210.0, "u3": 215.0, "v0": 200.0}
    by_unit = {u: {"unit": u, "start_s": s} for u, s in starts.items()}
    recs = [{"unit": u, "rig": u[0], "amp": amp} for u in starts for amp in ("pr12", "ac20")]
    got = P.rigo_records(recs, by_unit, {"unit": "u1", "rig": "u", "start_s": 205.0}, "pr12")
    assert [(r["unit"], r["amp"]) for r in got] == [("u3", "pr12")]
    assert P.rigo_records(recs, by_unit, {"unit": "v0", "rig": "v", "start_s": 200.0}, "pr12") == []


def test_goat_window_takes_only_clean_active_windows_and_is_seeded():
    rows = [{"start_s": 0.0, "passes_activity": True}, {"start_s": 5.0, "passes_activity": True, "clip_runs": 1},
            {"start_s": 10.0, "passes_activity": False}, {"start_s": 15.0, "passes_activity": True, "dropouts": 0},
            {"start_s": 20.0, "passes_activity": True, "hard_cuts": 2}, {"start_s": 25.0, "passes_activity": True},
            {"start_s": 30.0, "passes_activity": True, "hum_rel_db": -50.0},
            {"start_s": 35.0, "passes_activity": True, "hiss_rel_db": -60.0}]
    got = {P.goat_window(rows, f"item_{k}") for k in range(40)}
    assert got <= {15.0, 25.0} and len(got) == 2
    assert P.goat_window(rows, "item_3") == P.goat_window(rows, "item_3")
    assert P.goat_window(rows[:3], "item_1") is None
    assert P.goat_renders("item_1", [1, 3, 4]) == P.goat_renders("item_1", [4, 1, 3])
    assert len(P.goat_renders("item_1", [1, 3, 4])) == 2 and P.goat_renders("item_2", [5]) == [5]
    assert P.goat_renders("item_2", []) == []


def test_goat_assign_keeps_an_items_renders_in_one_fold_and_balances_amps():
    items = {f"item_{k}": [f"u{k}a", f"u{k}b"] if k % 3 else [f"u{k}a"] for k in range(30)}
    fold, amp = P.goat_assign(items)
    assert set(fold) == set(items) and set(fold.values()) == {0, 1, 2, 3}
    units = [u for us in items.values() for u in us]
    counts = [sum(amp[u] == a for u in units) for a in P.AMPS3]
    assert max(counts) - min(counts) <= 1 and set(amp) == set(units)
    assert P.goat_assign(items) == (fold, amp)


def test_goat_lag_refused_keeps_units_whose_lag_follows_their_item_lag():
    item = {"a": 10, "b": 40, "c": 0, "d": 25, "e": 5}
    lags = {"a": 60, "b": 91, "c": 49, "d": 150, "e": None}       # offsets 50, 51, 49, 125, none
    assert P.goat_lag_refused(lags, item) == {"d", "e"}
    assert P.goat_lag_refused({"a": 60}, {"a": None}) == {"a"}


def _goat_records():
    units = {f"g{j}": {"unit": f"g{j}", "fold": j % 4, "cls": "clean" if j % 2 else "crunch"} for j in range(24)}
    recs = [{"unit": u, "amp": ("pr12", "ac20")[j % 2], "label": {"k": str(j)}} for j, u in enumerate(sorted(units))]
    return recs, units


def test_goat_fold_records_never_hold_the_folds_own_items_and_fill_an_epoch():
    recs, units = _goat_records()
    for f in range(4):
        rows = P.goat_fold_records(recs, units, f)
        assert len(rows) == P.GOAT_PER_EPOCH and all(units[r["unit"]]["fold"] != f for r in rows)


def test_goat_centres_use_exactly_model_ks_training_lists():
    grecs, gunits = _goat_records()
    by_unit = {f"b{j}": {"unit": f"b{j}", "di": f"d{j % 8}", "cls": "clean"} for j in range(16)}
    brecs = [{"unit": u, "amp": "pr12", "label": {"k": u}} for u in sorted(by_unit)]
    folds = {f"d{j}": j // 2 for j in range(8)}
    for k in range(4):
        src = P.centre_records(brecs, by_unit, folds, grecs, gunits, k)
        assert src["RcBG"] == P.fold_records(brecs, by_unit, folds, k) + P.goat_fold_records(grecs, gunits, k)
        assert src["RcGk"] == P.goat_fold_records(grecs, gunits, k) and src["RcG"] == grecs
        assert all(folds[by_unit[r["unit"]]["di"]] != k for r in src["RcBG"] if r["unit"] in by_unit)
        assert all(gunits[r["unit"]]["fold"] != k for r in src["RcGk"])


def test_real_report_reads_5c_with_5b2s_folds():
    for tags in ({"P2a-goat", "S"}, {"P2a-goatshuf", "RcBG", "S"}, {"RcG", "S"}):
        assert P.report_phase(tags) == "phase_5c" and P.report_phase(tags).startswith(P.ARM_FOLD_PHASES)
    assert P.report_phase({"Rcs2", "S"}) == "phase_5b2" and P.report_phase({"RigO", "S"}).startswith(P.ARM_FOLD_PHASES)
    assert not P.report_phase({"P2a-Sc", "S"}).startswith(P.ARM_FOLD_PHASES)


def test_goat_shuffle_stays_inside_each_folds_training_units():
    recs, units = _goat_records()
    for f in range(4):
        rows = P.goat_fold_records(recs, units, f, n=1000, shuffle=True)
        own = {r["label"]["k"] for r in recs if units[r["unit"]]["fold"] == f}
        assert all(units[r["unit"]]["fold"] != f and r["label"]["k"] not in own for r in rows)


def test_goat_shuffled_permutes_labels_only_within_amp_and_class():
    recs, units = _goat_records()
    sh = P.goat_shuffled(recs, units)
    assert sh == P.goat_shuffled(recs, units) and sh != recs
    for r, s in zip(recs, sh):
        assert {k: v for k, v in r.items() if k != "label"} == {k: v for k, v in s.items() if k != "label"}
    group = lambda rs: sorted((r["amp"], units[r["unit"]]["cls"], r["label"]["k"]) for r in rs)
    assert group(recs) == group(sh)


def test_goat_heard_passes_only_amp_verdicts_and_lists_the_unheard():
    v = {"a": {"verdict": "amp"}, "b": {"verdict": "unsure"}, "c": {"verdict": "odd"}, "d": {"verdict": "di_bad"}}
    ok, missing = P.goat_heard(["a", "b", "c", "d", "e"], v)
    assert ok == {"a"} and missing == ["e"]


def test_goat_run_name_takes_only_reals2s_recipe():
    import pytest

    assert P.goat_run_name("P2a-real2s2", 2, 2, False) == "P2a-goat2"
    assert P.goat_run_name("P2a-real0s2", 0, 2, True) == "P2a-goatshuf0"
    for base, k, st in (("P2a-real2", 2, 1), ("P2a-real2s2-pc", 2, 2), ("P2a", None, 0)):
        with pytest.raises(SystemExit):
            P.goat_run_name(base, k, st, False)


def test_goat_rows_and_records_stay_apart_from_bks():
    assert P.GOAT_ROW0 >= P.REAL_ROW0 + 10 * P.REAL_PER_EPOCH and P.GOAT_ROW0 + 10 * P.GOAT_PER_EPOCH < 10 ** 7
    assert P.GOAT_DIR != P.REAL_DIR


def test_setting_gap_is_zero_on_itself_and_counts_switch_agreement():
    from learn import knob_ceiling as K

    knob = next(d for d in K.space("pr12") if d.kind == "cont")
    sw = next((d for d in K.space("pr12") if d.kind not in ("cont", "log")), None)
    dims = [knob] + ([sw] if sw else [])
    k = (knob.module, knob.key)
    x = {k: K.fmt(knob.from_unit(0.2))}
    y = {k: K.fmt(knob.from_unit(0.5))}
    if sw:
        ks = (sw.module, sw.key)
        x[ks], y[ks] = sw.values[0], sw.values[1]
    assert P.setting_gap(dims, x, x) == (0.0, 1.0 if sw else None)
    rms, agree = P.setting_gap(dims, x, y)
    assert rms == pytest.approx(0.3, abs=1e-6)
    assert agree == (0.0 if sw else None)


def test_goat_heavy_out_keeps_only_keep_verdicts_and_lists_the_unheard():
    v = {"a": {"verdict": "keep"}, "b": {"verdict": "heavy"}, "c": {"verdict": "unsure"}}
    out, missing = P.goat_heavy_out(["a", "b", "c", "d"], v)
    assert out == {"b", "c", "d"} and missing == ["d"]


def test_goat_short_cells_counts_every_amp_and_class():
    parts = [{"amp": a, "cls": c} for a in P.AMPS3 for c in ("clean", "crunch") for _ in range(30)]
    assert P.goat_short_cells(parts) == {}
    assert P.goat_short_cells(parts[1:]) == {("pr12", "clean"): 29}
    assert P.goat_short_cells([]) == {(a, c): 0 for a in P.AMPS3 for c in ("clean", "crunch")}


def test_goat_ear_passed_waits_for_the_heavy_check(tmp_path, monkeypatch):
    import json

    import pytest

    from learn import goat_ear_page as G

    gd = tmp_path / P.GOAT_DIR
    gd.mkdir()
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(G, "heavy_candidates", lambda: ["b", "c"])
    (gd / "ear.json").write_text(json.dumps({"verdicts": {u: {"verdict": "amp"} for u in "abc"} |
                                             {"d": {"verdict": "odd"}}}))
    with pytest.raises(SystemExit, match="not built"):
        P.goat_ear_passed(["a", "b", "c", "d"])
    (gd / "heavy-key.json").write_text(json.dumps({"build": "k1", "items": [{"unit": "b"}, {"unit": "c"}]}))
    with pytest.raises(SystemExit, match="not yet heard"):
        P.goat_ear_passed(["a", "b", "c", "d"])
    (gd / "heavy.json").write_text(json.dumps({"build": "k1", "verdicts": {"b": {"verdict": "keep"}}}))
    with pytest.raises(SystemExit, match="not yet heard"):
        P.goat_ear_passed(["a", "b", "c", "d"])
    (gd / "heavy.json").write_text(json.dumps({"build": "k0", "verdicts": {"b": {"verdict": "keep"},
                                                                          "c": {"verdict": "heavy"}}}))
    with pytest.raises(SystemExit, match="build"):
        P.goat_ear_passed(["a", "b", "c", "d"])
    (gd / "heavy.json").write_text(json.dumps({"build": "k1", "verdicts": {"b": {"verdict": "keep"},
                                                                          "c": {"verdict": "heavy"}}}))
    assert P.goat_ear_passed(["a", "b", "c", "d"]) == {"a", "b"}
    monkeypatch.setattr(G, "heavy_candidates", lambda: ["b", "c", "e"])
    with pytest.raises(SystemExit, match="rebuild"):
        P.goat_ear_passed(["a", "b", "c", "d"])


def test_goat_lag_rule_tolerance_is_the_diagnostic_span():
    lags = {"a": -90, "b": -90 + 72, "c": -90 - 73, "d": -90}
    item = {u: 0 for u in lags}
    assert P.GOAT_LAG_TOL == 72
    assert P.goat_lag_refused(lags, item) == {"c"}


def test_goat_lags_refused_reads_every_heard_unit_and_takes_a_narrower_tolerance(tmp_path, monkeypatch):
    import json

    ld = tmp_path / P.GOAT_DIR / "lags"
    ld.mkdir(parents=True)
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    offs = {"g/a": -90, "g/b": -90, "g/c": -88, "g/g": -91, "g/d": -45, "g/e": -45, "g/f": 800}
    for u, o in offs.items():
        (ld / f"{u.replace('/', '__')}.json").write_text(json.dumps({"lag": o, "item_lag": 0}))
    units = {u: {"item_lag": 0} for u in offs}
    lags, off = P.goat_lags_refused(units, list(offs))
    assert lags == offs and off == {"g/f"}                      # the median (-88) from every heard unit
    assert P.goat_lags_refused(units, list(offs), 14)[1] == {"g/d", "g/e", "g/f"}
    # a subset (as after a third of the searches) would centre elsewhere; the rule never sees one
    assert P.goat_lag_refused({u: offs[u] for u in ("g/d", "g/e", "g/a")}, {u: 0 for u in offs}, 14) == {"g/a"}


def test_panel_windows_are_seeded_apart_and_capped():
    rows = [{"start_s": float(s), "passes_activity": True} for s in range(0, 200, 5)]
    a = P.panel_windows(rows, {}, "band|part")
    assert a == P.panel_windows(rows, {}, "band|part") and len(a) == P.PANEL_WINDOWS
    assert all(abs(x - y) >= 10 + P.PANEL_GAP_S for x in a for y in a if x != y) and min(a) >= 1.0
    assert P.panel_windows(rows, {}, "band|part", k=1) != [] and len(P.panel_windows(rows[:3], {}, "b|p")) == 1


def test_panel_folds_balance_across_bands():
    dis = {"A": {f"a{j}" for j in range(5)}, "B": {"b0", "b1"}, "C": {"c0"}}
    f = P.panel_folds(dis)
    assert f == P.panel_folds(dis) and set(f) == set().union(*dis.values())
    counts = [list(f.values()).count(k) for k in range(P.REAL_FOLDS)]
    assert max(counts) - min(counts) <= 1


def test_panel_bleed_reads_the_amp_where_the_di_is_silent():
    np = pytest.importorskip("numpy")
    sr = 48000
    di = np.concatenate([np.sin(np.arange(sr) * 0.05), np.zeros(sr)])
    clean = np.concatenate([np.sin(np.arange(sr) * 0.05), np.zeros(sr) + 1e-6])
    bleed = clean + np.concatenate([np.zeros(sr), 0.1 * np.sin(np.arange(sr) * 0.3)])
    assert P.panel_bleed_db(bleed, di, sr) > P.panel_bleed_db(clean, di, sr) + 40


def test_panel_pairs_are_the_declared_sources_and_never_training_or_v_real():
    pairs = P.panel_pairs()
    assert {p["band"] for p in pairs} == {"Blue Manic", "Sonnet & Alcohol", "The Laminar Flow", "Little Tybee",
                                          "Port St Willow", "Big Troubles", "Guitar-TECHS P3", "Aimee Norwich",
                                          "Dahka Band", "Jen Hartswick & Nick Cassarino"}
    import json
    files = {a["path"] for p in pairs for a in p["amps"]} | {p["di"]["path"] for p in pairs}
    assert not any("v-real" in f.lower() or "datasets-set5" in f for f in files)


def test_panel_leaks_catch_a_pool_copy_and_an_out_band(tmp_path):
    a, b, c = tmp_path / "di.wav", tmp_path / "amp.wav", tmp_path / "copy.wav"
    a.write_bytes(b"x" * 5000), b.write_bytes(b"y" * 5000), c.write_bytes(b"x" * 5000)
    pairs = [{"band": "New", "di": {"path": str(a)}, "amps": [{"path": str(b)}]}]
    assert P.panel_leaks(pairs, [], set()) == []
    assert any("pool file" in x for x in P.panel_leaks(pairs, [str(c)], set()))
    assert P.panel_leaks(pairs, [str(a)], set()) and P.panel_leaks(pairs, [], {"New"}) == ["band New is out"]


def test_panel_lets_di_hum_through_and_nothing_else(monkeypatch):
    from learn import clean_di as CD
    monkeypatch.setattr(CD, "section_flags", lambda r, t: (r["f"], []))
    assert not P.panel_di_flagged({"f": ["hum"]}, {}) and not P.panel_di_flagged({"f": []}, {})
    assert P.panel_di_flagged({"f": ["hum", "hiss"]}, {}) and P.panel_di_flagged({"f": ["clipping"]}, {})


def test_panel_heard_passes_only_amp_verdicts():
    v = {"a": {"verdict": "amp"}, "b": {"verdict": "bleed"}, "c": {"verdict": "unsure"}, "d": {"verdict": "odd"}}
    ok, missing = P.panel_heard(["a", "b", "c", "d", "e"], v)
    assert ok == {"a"} and missing == ["e"]


def test_panel_read_units_wait_for_the_ear(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    (tmp_path / P.PANEL_DIR).mkdir()
    (tmp_path / P.PANEL_DIR / "units.json").write_text(json.dumps({"units": [{"unit": "x", "band": "A"}, {"unit": "y", "band": "B"}]}))
    with pytest.raises(SystemExit):
        P.panel_read_units()
    (tmp_path / P.PANEL_DIR / "ear.json").write_text(json.dumps({"verdicts": {"x": {"verdict": "amp"}}}))
    with pytest.raises(SystemExit):
        P.panel_read_units()
    (tmp_path / P.PANEL_DIR / "ear.json").write_text(json.dumps({"verdicts": {"x": {"verdict": "amp"},
                                                                              "y": {"verdict": "bleed"}}}))
    assert [u["unit"] for u in P.panel_read_units()] == ["x"]
    (tmp_path / P.PANEL_DIR / "recheck.json").write_text(json.dumps({"verdicts": {"y": {"verdict": "amp"},
                                                                                  "x": {"verdict": "unsure"}}}))
    assert [u["unit"] for u in P.panel_read_units()] == ["y"]


def test_panel_cut_lines_the_amp_window_up_with_the_di_for_either_sign():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(0)
    di = rng.standard_normal(5000)
    for lag in (37, -23):
        amp = np.roll(di, lag)                              # amp[t] = di[t - lag]
        d, a = P.panel_cut(di, amp, 1000, 2000, lag)
        assert len(d) == len(a) == 2000 and np.allclose(d, a)
    assert len(P.panel_cut(di, di, 10, 100, -50)[1]) == 0


def test_panel_halves_alternate_within_each_di():
    units = [{"unit": f"d{j % 2}@{j}", "di": f"d{j % 2}"} for j in range(6)]
    h = P.panel_halves(units)
    for d in ("d0", "d1"):
        assert [h[u["unit"]] for u in sorted(units, key=lambda u: u["unit"]) if u["di"] == d] == ["A", "B", "A"]


def test_weighted_clustered_matches_the_plain_mean_and_counts_effective_clusters():
    rows = [("a", -0.1), ("a", -0.3), ("b", 0.0), ("c", -0.1)]
    eq = P.weighted_clustered(rows, {"a": 1, "b": 1, "c": 1})
    assert abs(eq["mean"] - (-0.2 + 0.0 - 0.1) / 3) < 1e-12 and abs(eq["n_eff"] - 3) < 1e-12
    sk = P.weighted_clustered(rows, {"a": 2, "b": 1, "c": 1})
    assert abs(sk["mean"] - (2 * -0.2 + 0 - 0.1) / 4) < 1e-12 and sk["n_eff"] < 3 and sk["lo90"] < sk["mean"] < sk["hi90"]


def test_panel_weights_cap_a_band_at_four_dis():
    units = [{"band": "big", "di": f"b{j}"} for j in range(8)] + [{"band": "one", "di": "o"}]
    w = P.panel_weights(units)
    assert abs(sum(v for d, v in w.items() if d.startswith("b")) - 4) < 1e-12 and w["o"] == 1
    assert abs(sum(v for d, v in P.panel_weights(units, capped=False).items() if d.startswith("b")) - 1) < 1e-12


def test_panel_rows_read_the_held_half_and_drop_missing():
    units = [{"unit": "u", "di": "d"}]
    judge = {"M": {f"u|{a}": {"A": {"A": 1.0, "B": 2.0}} for a in P.AMPS3},
             "C": {f"u|{a}": {P.ANY_HALF: {"A": 9.0, "B": 4.0}} for a in P.AMPS3[:2]}}
    rows, dropped = P.panel_rows("M", "C", units, {"u": "A"}, judge)
    assert dropped == 1 and all(abs(v - math.log(2.0 / 4.0)) < 1e-12 for _, _, v in rows) and len(rows) == 2


def test_panel_ceiling_takes_one_seeded_unit_per_band():
    units = [{"unit": f"{b}{j}", "band": b} for b in "xyz" for j in range(4)]
    c = P.panel_ceiling_units(units)
    assert c == P.panel_ceiling_units(units) and [p["band"] for p, _ in c] == ["x", "y", "z"]
    assert all(a in P.AMPS3 for _, a in c)


def test_panel_read_units_drop_the_di_like_bands(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    (tmp_path / P.PANEL_DIR).mkdir()
    units = [{"unit": "x", "band": "Dahka Band"}, {"unit": "y", "band": "Other"}]
    (tmp_path / P.PANEL_DIR / "units.json").write_text(json.dumps({"units": units}))
    (tmp_path / P.PANEL_DIR / "ear.json").write_text(json.dumps({"verdicts": {u["unit"]: {"verdict": "amp"}
                                                                              for u in units}}))
    assert "Dahka Band" in P.PANEL_DI_LIKE and [u["unit"] for u in P.panel_read_units()] == ["y"]


# --- D_fix -----------------------------------------------------------------------------------------------------------

def _train_args(**kw):
    import argparse

    base = dict(rung="b", aug=False, backings=False, dd=False, pc=False, pcsz=False, wide=False, goat=False,
                goat_shuffle=False, fold=None, frac=1.0, sections=1.0, stage=0, real_fold=None, dfix=False,
                seed=P.SEEDS[0])
    base.update(kw)
    return argparse.Namespace(**base)


def _dfix_kept():
    secs = ["s/A_Full/di.wav@0.0", "s/A_Full/di.wav@10.0", "s/B_Full/x.wav@5.0", "s/C_Full/y.wav@0.0"]
    return {i: {"section": secs[i % 4], "cls": "clean" if i % 3 else "crunch", "band": f"b{i % 4}"}
            for i in range(40)}


def test_dfix_lend_is_seeded_and_same_section_else_same_class():
    kept = _dfix_kept()
    tr = [i for i in kept if i != 3 and i % 4 != 1]            # no training example of section 1
    for u in ("u0", "u1", "u2"):
        i, rule = P.dfix_lend(u, "clean", tr, kept, section="s/A_Full/di.wav@0.0")
        assert rule == "section" and kept[i]["section"] == "s/A_Full/di.wav@0.0" and i in tr
        assert P.dfix_lend(u, "clean", tr, kept, section="s/A_Full/di.wav@0.0") == (i, rule)
        j, rule = P.dfix_lend(u, "crunch", tr, kept, section="s/A_Full/di.wav@10.0")
        assert rule == "class" and kept[j]["cls"] == "crunch" and j in tr
        g, rule = P.dfix_lend(u, "crunch", tr, kept)                 # GOAT: class always
        assert rule == "class" and kept[g]["cls"] == "crunch"
    assert len({P.dfix_lend(f"u{k}", "clean", tr, kept)[0] for k in range(30)}) > 1
    with pytest.raises(SystemExit):
        P.dfix_lend("u", "heavy", tr, kept)


def test_dfix_draws_never_pick_the_units_own_session_and_lead_with_the_own_backing():
    entries = [{"session": "s/A_Full"}, {"session": "A_Full"}, {"session": "s/B_Full"}, {"session": "C_Full"},
               {"session": "D_Full"}, {"session": "D_Full"}]
    d = P.dfix_draws("s/A_Full/di.wav@0.0#amp.wav", "s/A_Full/di.wav@0.0", entries, own=True, k=P.DFIX_K)
    assert len(d) == P.DFIX_K and d[0] == (None, None)
    assert all(j is not None and entries[j]["session"] not in ("s/A_Full", "A_Full") for j, _ in d[1:])
    assert {entries[j]["session"] for j, _ in d[1:]} == {"s/B_Full", "C_Full", "D_Full"}
    assert d == P.dfix_draws("s/A_Full/di.wav@0.0#amp.wav", "s/A_Full/di.wav@0.0", entries, own=True)
    g = P.dfix_draws("goat/item_0@140.0#amp_3", "goat/item_0@140.0", entries, own=False)
    assert len(g) == P.DFIX_K and all(j is not None for j, _ in g)
    assert {v for _, v in g} == {True, False}


def test_dfix_mix_brings_the_guitar_to_the_lenders_target_and_the_backing_to_its_own_level():
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    from learn import song_aug as SA

    rng = np.random.default_rng(0)
    y_e = 0.05 * rng.standard_normal(48000 * 4)            # the lending example's stored target
    real = 0.4 * rng.standard_normal(48000 * 4)            # the real amp track, far louder
    back = 0.2 * rng.standard_normal(48000 * 4)            # a pool backing
    gtr, g = P.dfix_level(real, SA.lufs(y_e), SA.lufs)
    assert SA.lufs(gtr) == pytest.approx(SA.lufs(y_e), abs=0.01) and g < 0
    e_gb, e_own, ga = -3.0, -20.0, -6.0
    gb = P.dfix_backing_gain(e_gb, e_own, SA.lufs(back))
    assert SA.lufs(back * 10 ** (gb / 20)) == pytest.approx(e_own + e_gb, abs=0.01)
    assert P.dfix_backing_gain(e_gb, e_own, e_own) == e_gb        # its own backing: the lender's gb exactly
    mix = P.dfix_mix(gtr, back, gb, ga)
    assert np.allclose(mix * 10 ** (-ga / 20) - back * 10 ** (gb / 20), gtr)
    with pytest.raises(SystemExit):
        P.dfix_level(np.zeros(48000), -20.0, SA.lufs)


def test_dfix_own_backing_guard_lists_every_track_of_the_di():
    inv = {"s/A_Full/19_Gtr1aDI.wav": {"own": ["21_Gtr1cReamp.wav", "20_Gtr1bGR4.wav"]}}
    prt = {"di": "s/A_Full/19_Gtr1aDI.wav", "track": "21_Gtr1cReamp.wav"}
    assert P.dfix_di_tracks(prt, inv) == {"19_Gtr1aDI.wav", "21_Gtr1cReamp.wav", "20_Gtr1bGR4.wav"}


def test_dfix_variant_is_seeded_per_row_and_epoch_and_variant_0_at_eval():
    assert all(P.dfix_variant(i, -1) == 0 for i in range(50))
    v = [P.dfix_variant(P.REAL_ROW0 + 7, ep) for ep in range(200)]
    assert v == [P.dfix_variant(P.REAL_ROW0 + 7, ep) for ep in range(200)]
    assert set(v) == set(range(P.DFIX_K))
    assert v != [P.dfix_variant(P.REAL_ROW0 + 8, ep) for ep in range(200)]
    d = object.__new__(P.DfixData)
    d.rows = [{"i": 5}, {"i": P.REAL_ROW0, "real": "u"}, {"i": P.GOAT_ROW0 + 1, "real": "g"}]
    d.RJ = {1: "u", 2: "g"}
    assert d.real_choices([0, 1, 2], 3) == {1: ("u", P.dfix_variant(P.REAL_ROW0, 3)),
                                            2: ("g", P.dfix_variant(P.GOAT_ROW0 + 1, 3))}
    assert d.real_choices([0, 1, 2], -1) == {1: ("u", 0), 2: ("g", 0)}


def test_dfix_refuses_every_other_flag_and_wide_with_a_real_fold():
    assert P.dfix_refusal(_train_args(dfix=True)) is None
    assert P.dfix_refusal(_train_args(dfix=True, real_fold=2, stage=2)) is None
    for kw in ({"rung": "a"}, {"aug": True}, {"backings": True}, {"dd": True}, {"pc": True}, {"pcsz": True},
               {"wide": True}, {"goat": True}, {"goat_shuffle": True}, {"fold": 1}, {"frac": 0.5},
               {"sections": 0.5}, {"stage": 1}):
        assert P.dfix_refusal(_train_args(dfix=True, **kw)), kw
    assert P.dfix_refusal(_train_args(wide=True, real_fold=0))
    assert P.dfix_refusal(_train_args(wide=True)) is None and P.dfix_refusal(_train_args(rung="a", real_fold=1)) is None


def test_dfix_run_names_take_no_other_runs_name():
    assert P.dfix_run_name(None) == "P2b-dfix" and P.dfix_run_name(3) == "P2b-dfix3"
    others = {P.run_name(r, f, a, k, s) for r in "abcd" for f in (1.0, 0.5) for a in (False, True)
              for k in (None, *P.FOLDS) for s in (1.0, 0.5)}
    others |= {f"P2b-wide{P.WIDE_K}", "P2a-goat0", "P2a-real0s2"}
    assert not {P.dfix_run_name(k) for k in (None, 0, 1, 2, 3)} & others


def test_dfix_plugin_rows_with_the_real_rows_off_are_wides():
    kept = _dfix_kept()
    sp = {"train": list(range(0, 30)), "fs": list(range(30, 35)), "ns": list(range(35, 40))}
    rows_of = lambda ids: [{"i": i, "section": kept[i]["section"]} for i in ids]   # noqa: E731
    wide = P.plugin_rows(kept, sp, _train_args(wide=True), rows_of)
    tr, held, held_name, rows = P.plugin_rows(kept, sp, _train_args(dfix=True), rows_of)
    assert (tr, held, held_name, rows) == wide and tr == sp["train"] and held_name == "ns"
    assert P.with_rows(tr, rows, []) == (wide[0], wide[3])
    extra = [{"i": P.REAL_ROW0, "real": "u"}]
    t2, r2 = P.with_rows(tr, rows, extra)
    assert t2 == tr + [P.REAL_ROW0] and r2[len(tr)] == extra[0] and r2[:len(tr)] == rows[:len(tr)]
    assert r2[len(tr) + 1:] == rows[len(tr):] and all(r.get("held") for r in r2[len(tr) + 1:])


def test_dfix_real_rows_keep_every_label_and_hold_only_the_folds_own():
    by_unit = {f"b{j}": {"unit": f"b{j}", "di": f"d{j % 8}", "cls": "clean", "section": f"s{j}", "band": "BKS"}
               for j in range(16)}
    brecs = [{"unit": u, "amp": amp, "label": {}} for u in sorted(by_unit) for amp in ("pr12", "ac20")] * 10
    folds = {f"d{j}": j // 2 for j in range(8)}
    grecs, gunits = _goat_records()
    for u in gunits.values():
        u.update(section=u["unit"], band="GOAT")
    lab = lambda rec: rec["amp"]                                     # noqa: E731
    tr, held, n = P.dfix_rows_of(brecs, by_unit, folds, grecs, gunits, None, label_of=lab)
    assert len(brecs) > P.REAL_PER_EPOCH and n["real_rows"] == len(brecs) and held == []
    assert n["goat_rows"] == P.GOAT_PER_EPOCH
    for k in range(4):
        tr, held, n = P.dfix_rows_of(brecs, by_unit, folds, grecs, gunits, k, label_of=lab)
        assert n["real_rows"] == P.REAL_PER_EPOCH and n["goat_rows"] == P.GOAT_PER_EPOCH
        ids = [r["i"] for r in tr + held]
        assert len(set(ids)) == len(ids)
        assert all(r["i"] < P.REAL_ROW0 + P.DFIX_HELD0 or P.GOAT_ROW0 <= r["i"] < P.GOAT_ROW0 + P.DFIX_HELD0
                   for r in tr)
        bt = [r for r in tr if r["i"] < P.GOAT_ROW0]
        assert all(folds[by_unit[r["real"]]["di"]] != k for r in bt)
        assert all(gunits[r["real"]]["fold"] != k for r in tr if r["i"] >= P.GOAT_ROW0)
        bh = [r for r in held if r["i"] < P.GOAT_ROW0]
        assert bh and all(folds[by_unit[r["real"]]["di"]] == k for r in bh)
        assert all(gunits[r["real"]]["fold"] == k for r in held if r["i"] >= P.GOAT_ROW0)
        assert {r["real"] for r in bt} == {u for u, p in by_unit.items() if folds[p["di"]] != k}


def test_dfix_reads_are_fold_wise_and_reported_with_5b2s_folds():
    assert {"P2b-dfix", "P2b-dfix-clean"} <= P.DFIX_READS and len(P.DFIX_READS) == 2 * len(P.DFIX_BASES)
    for t in P.DFIX_READS:
        assert P.report_phase({t, "Rcs2", "S"}) == "phase_dfix"
        assert P.report_phase({t, "S"}).startswith(P.ARM_FOLD_PHASES)


def test_model_input_lufs_reads_the_runs_own_rung(monkeypatch):
    seen = []
    monkeypatch.setattr(P, "rung_median_lufs", lambda ids, rung: seen.append((tuple(ids), rung)) or -13.7)
    assert P.model_input_lufs({"train_ids": [1, 2, P.REAL_ROW0 + 1], "rung": "b"}) == -13.7
    assert seen == [((1, 2), "b")]
    P.model_input_lufs({"train_ids": [3]})
    assert seen[-1] == ((3,), "a")


def test_dfix_read_only_units_are_the_read_units_with_no_row():
    units = [("goat/a#amp_1", "goat", {"unit": "goat/a#amp_1"}), ("bks/b", "bks", {"unit": "bks/b"})]
    read = [{"unit": "goat/c#amp_5", "fold": 1}, {"unit": "goat/a#amp_1", "fold": 0}]
    assert P.dfix_read_only(units, read) == [("goat/c#amp_5", "goat", {"unit": "goat/c#amp_5", "fold": 1})]
    assert P.dfix_read_only(units, read[1:]) == []


def test_dfix_share_names_never_collide_and_map_to_their_folds():
    names = [P.dfix_run_name(k, s) for s in (None, *P.DFIX_SHARES) for k in (None, 0, 1, 2, 3)]
    assert len(set(names)) == len(names)
    assert P.dfix_run_name(0, "p10") == "P2b-dfixp10-k0" and P.dfix_run_name(None, "p33") == "P2b-dfixp33"
    assert P.dfix_run_name(2) == "P2b-dfix2"
    assert P.dfix_fold_name("P2b-dfixp33-clean", 1) == "P2b-dfixp33-k1"
    assert P.dfix_fold_name("P2b-dfix-clean", 1) == "P2b-dfix1"
    assert P.dfix_share_of("P2b-dfix") == 1.0 and P.dfix_share_of("P2b-dfixp10-clean") == 0.1
    for s, p in ((None, 1.0), *P.DFIX_SHARES.items()):
        for k in (None, 0, 1, 2, 3):
            assert P.dfix_share_of(P.dfix_run_name(k, s)) == p
            assert P.dfix_phase(P.dfix_run_name(k, s)) == ("phase_dfix" if p == 1 else "phase_dfix_share")
    with pytest.raises(SystemExit):
        P.dfix_fold_name("P2b-dfixp50", 0)
    with pytest.raises(SystemExit):
        P.dfix_run_name(None, "p50")
    for b in P.DFIX_BASES:
        assert {b, f"{b}-clean"} <= P.DFIX_READS and P.report_phase({b, "Rcs2"}) == "phase_dfix"


def test_dfix_share_refuses_without_dfix_and_unknown_shares():
    a = _train_args(dfix=False, dfix_share="p33")
    assert "--dfix-share" in P.dfix_refusal(a)
    assert P.dfix_refusal(_train_args(dfix=True, rung="b", dfix_share="p33")) is None
    assert "--dfix-share in" in P.dfix_refusal(_train_args(dfix=True, rung="b", dfix_share="p50"))


def test_dfix_shown_is_seeded_at_rate_p_and_independent_of_the_variant():
    import random

    assert all(P.dfix_shown(i, e, 1.0) for i in range(50) for e in range(5))
    draws = [(i, e) for i in range(4000) for e in range(5)]
    shown = [P.dfix_shown(i, e, 1 / 3) for i, e in draws]
    assert shown == [P.dfix_shown(i, e, 1 / 3) for i, e in draws]
    assert abs(sum(shown) / len(shown) - 1 / 3) < 0.01
    var0 = [P.dfix_variant(i, e) == 0 for i, e in draws]
    a = sum(v for v, s in zip(var0, shown) if s) / sum(shown)
    b = sum(v for v, s in zip(var0, shown) if not s) / (len(shown) - sum(shown))
    assert abs(a - b) < 0.015 and abs(a - 1 / P.DFIX_K) < 0.015
    assert random.Random(f"{P.DFIX_SEED}|show|7|3").random() != random.Random(f"{P.DFIX_SEED}|7|3").random()


def test_epoch_order_keeps_the_rng_stream_and_at_p1_the_batches():
    np = pytest.importorskip("numpy")

    class Plain:
        pass

    class Share:
        def __init__(self, rj, rows, p):
            self.RJ, self.rows, self.share = rj, rows, p

        def epoch_keep(self, order, epoch):
            return P.DfixData._epoch_keep(self, order, epoch)

    tr = np.arange(40)
    rows = [{"i": 1000 + j} for j in range(40)]
    rj = {j: "u" for j in range(30, 40)}
    r0, r1, r2 = (np.random.default_rng(5) for _ in range(3))
    for e in range(4):
        base = P.epoch_order(r0, tr, Plain(), e)
        full = P.epoch_order(r1, tr, Share(rj, rows, 1.0), e)
        part = P.epoch_order(r2, tr, Share(rj, rows, 0.3), e)
        assert list(full) == list(base)
        assert [j for j in part] == [j for j in base if j not in rj or P.dfix_shown(rows[j]["i"], e, 0.3)]
        assert all(j in part for j in base if j not in rj)


# --- D_fix to V-real (phase_dfix_vreal) ---------------------------------------------------------------------------

def test_dfix_vreal_takes_only_the_declared_tags_and_models():
    assert P.dfix_vreal_tags("") == list(P.DFIX_VREAL_TAGS) and len(P.DFIX_VREAL_TAGS) == 6
    assert P.dfix_vreal_tags("DV-RcG,S-recheck-dfix") == ["DV-RcG", "S-recheck-dfix"]
    for bad in ("S", "P4-P2a-best", "DV-P2b-dfixp10-stem", "DV-RcG,P2b-dfix"):
        with pytest.raises(SystemExit):
            P.dfix_vreal_tags(bad)
    assert {m for m, _, _ in P.DFIX_VREAL_TAGS.values()} - {None} == set(P.DFIX_VREAL_MODELS)
    for name in ("P2b-dfixp10", "P2b-dfixp33", "P2b-dfix0", "P2a", "P2d", "P2b"):
        with pytest.raises(SystemExit, match="reads only"):
            P.dfix_vreal_load(name)
    assert P.DFIX_VREAL_BASE != "S"         # phase 4's S groups are kept, so S is rendered again under its own tag


def test_dfix_vreal_predict_refuses_other_tags_and_checkpoints(monkeypatch):
    pytest.importorskip("numpy")
    monkeypatch.setattr(P, "require", lambda k: {})
    monkeypatch.setattr(P, "recipe_inputs", lambda **kw: pytest.fail("refusals come before any data is read"))
    with pytest.raises(SystemExit, match="declares only"):
        P.cmd_dfix_vreal_predict(argparse.Namespace(names="P4-P2a-best", which="best"))
    with pytest.raises(SystemExit, match="NS-best"):
        P.cmd_dfix_vreal_predict(argparse.Namespace(names="", which="final"))


def test_vreal_mix_target_is_asserted_the_declared_level(tmp_path):
    p = tmp_path / "levels.json"
    p.write_text(json.dumps({"summary": {"eval_mix_lufs_median": -12.250616791893322}}))
    assert P.vreal_mix_target(p) == pytest.approx(-12.2506, abs=1e-4)
    p.write_text(json.dumps({"summary": {"eval_mix_lufs_median": -12.26}}))
    with pytest.raises(SystemExit):
        P.vreal_mix_target(p)


def test_vreal_input_path_reads_a_stored_fs_stem_half_exactly_as_rungdata():
    """The known answer: an FS example's stored xlance_g-cc halves through the V-real input path give exactly the
    X and C `RungData` (`read_inputs`) gives; and audio through `step4_half` at 0 dB gives exactly the build's
    `half_features` (the stems' audio is not stored, so the FS example's target stands in for the signal)."""
    np = pytest.importorskip("numpy")
    try:
        croot, kept, rend, sp, _ = P.recipe_inputs(pin=P.ledger_entry().get("phase_3_doubles"))
    except (SystemExit, OSError):
        pytest.skip("no D_CC data here")
    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import trusted_data as T

    i = sp["fs"][0]
    path_of = P.rung_path(croot, "d")
    row = P.rung_rows(kept, rend, [i])
    X, C, who = P.read_inputs(P.RungData(row, path_of))
    d = np.load(path_of(i))
    assert who == [i, i]
    for k, h in enumerate("AB"):
        x, c = P.vreal_model_input(d[f"s{h}"], float(d["lufs"][k]), h, row[0]["amp"], row[0]["cls"])
        assert np.array_equal(np.asarray(x, np.float32), X[k]) and np.array_equal(c, C[k])
    y = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "target"), rend[i]["target"]["scale"],
                               rend[i]["target"]["sha256"]), np.float64)
    mels, lu, _ = DS.half_features(y)
    for h in "AB":
        s8, _, ls, _ = DS.step4_half(y, y, h, 0.0)
        assert np.array_equal(s8, mels[h]) and ls == lu[h]


def test_leakage_guard_flags_a_v_real_band_or_song_and_nothing_else():
    inv = {f"di{j}": {"slug": s, "song": f"Song {j}", "session_dir": f"/x/Band{j}_Song{j}_Full"}
           for j, s in enumerate(PR.VREAL)}
    songs = P.vreal_songs(inv)
    assert "song0" in songs and "band0song0full" in songs
    src = [("plugin row 1", "Forkupines", ["Forkupines_SugarFaith_Full", "Sugar Faith"]),
           ("pool entry a", None, ["Other_Session", None]),
           ("real unit u", "Diesel13", ["x"]),
           ("pool entry b", "Someone", ["Band3_Song3_Full"]),
           ("own backing", "BKS", ["Song 4"])]
    assert P.leaks_of(src, P.VREAL_BANDS, songs) == ["own backing: song Song 4", "pool entry a: no band",
                                                     "pool entry b: song Band3_Song3_Full", "real unit u: band Diesel13"]
    assert P.leaks_of(src[:1], P.VREAL_BANDS, songs) == []
    with pytest.raises(SystemExit):
        P.vreal_songs({k: v for k, v in inv.items() if k != "di0"})


def test_leakage_guard_reads_every_training_input_of_both_runs(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "DFIX_K", 2)
    (tmp_path / "runs").mkdir()
    for sd in P.SEEDS:
        (tmp_path / "runs" / f"P2b-dfix-{sd}.json").write_text(json.dumps({
            "train_ids": [1, P.REAL_ROW0, P.GOAT_ROW0], "held_ids": [2], "dfix": {"target_lufs": {"bks/u": 0, "g/u": 0}}}))
    kept = {1: {"section": "s1/Band1_Song_Full/di.wav@5.0", "band": "B1", "session_dir": "/d/Band1_Song_Full", "di": "d1"},
            2: {"section": "s1/NS_Full/di.wav@5.0", "band": "NS", "session_dir": "/d/NS_Full", "di": "d2"}}
    inv = {"d1": {"song": "Song"}, "d2": {"song": "NS"}, "d3": {"song": "Real", "session_dir": "/e/Pool_Full",
                                                              "band": "PoolBand"}}
    monkeypatch.setattr(P, "dfix_real_rows", lambda k: ([{"i": P.REAL_ROW0, "real": "bks/u"},
                                                         {"i": P.GOAT_ROW0, "real": "g/u"}], [], {}))
    monkeypatch.setattr(P, "dfix_units", lambda: [
        ("bks/u", "bks", {"band": "BKS", "section": "s1/BKS_Full/di.wav@1.0", "sd": "/d/BKS_Full", "di": "d3"}),
        ("g/u", "goat", {"band": "GOAT player1", "item": "item_0"})])
    (tmp_path / "inputs").mkdir()
    pool = [{"id": "s1/Band1_Song_Full/di.wav@5.0", "kind": "training", "session": "s1/Band1_Song_Full"},
            {"id": "Pool_Full@5.0", "kind": "extra", "session": "Pool_Full", "sd": "/e/Pool_Full"}]
    (tmp_path / "inputs" / "backings-wide-pool.json").write_text(json.dumps({"entries": pool}))
    for u, bids in (("bks/u", ["s1/BKS_Full/di.wav@1.0", "Pool_Full@5.0"]), ("g/u", ["Pool_Full@5.0"] * 2)):
        for v, b in enumerate(bids):
            p = P.dfix_input_path(u, v)
            p.parent.mkdir(parents=True, exist_ok=True)
            np.savez(p, backing=b)
    src, cnt = P.dfix_training_sources(kept, inv)
    assert cnt == {"plugin_rows": 2, "real_rows": 2, "real_units": 2, "unit_backings": 4, "pool_entries": 2}
    assert ("pool entry Pool_Full@5.0", "PoolBand", ["Pool_Full", "Real"]) in src
    assert any(x.startswith("bks/u v1 backing Pool_Full@5.0: band PoolBand") for x in P.leaks_of(src, {"PoolBand"}, set()))
    np.savez(P.dfix_input_path("g/u", 1), backing="Elsewhere@1.0")
    with pytest.raises(SystemExit, match="neither a pool entry"):
        P.dfix_training_sources(kept, inv)


def _answers(tmp_path, tags):
    d = tmp_path / P.VREAL_DIR / "answers"
    d.mkdir(parents=True, exist_ok=True)
    for t in tags:
        (d / f"{t}.json").write_text(json.dumps({"tag": t, "answers": {"k": t}}))


def test_dfix_vreal_render_refuses_until_every_answers_hash_is_in_the_ledger(tmp_path, monkeypatch):
    from learn import direct_stems as DS

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    tags = list(P.DFIX_VREAL_TAGS)
    _answers(tmp_path, tags)
    shas = {t: DS.hashlib_file(P.vreal_answers_path(t)) for t in tags}
    calls = []
    monkeypatch.setattr(P, "vreal_render", lambda tags, shard, recheck=None: calls.append((tags, shard, recheck)))
    args = argparse.Namespace(names="", shard=(0, 3))
    for entry in ({}, {P.DFIX_VREAL_HASHES: {t: s for t, s in shas.items() if t != "DV-RcG"}},
                  {P.DFIX_VREAL_HASHES: dict(shas, **{"DV-P2b-dfix-stem": "0" * 64})}):
        monkeypatch.setattr(P, "require", lambda k, entry=entry: entry)
        with pytest.raises(SystemExit, match="ledger"):
            P.cmd_dfix_vreal_render(args)
    assert not calls
    monkeypatch.setattr(P, "require", lambda k: {P.DFIX_VREAL_HASHES: shas})
    P.cmd_dfix_vreal_render(args)
    assert calls == [(tags, (0, 3), {P.DFIX_VREAL_BASE: "S"})]
    with pytest.raises(SystemExit, match="declares only"):
        P.cmd_dfix_vreal_render(argparse.Namespace(names="S", shard=(0, 1)))


def _vreal_dirs():
    return [(s, a, sh, h) for s in sorted(PR.VREAL) for a in PR.AMPS for sh, h in (("A", "B"), ("B", "A"))]


def _vreal_judge(dirs, d_of):
    """{tag: {slug|amp: {half: {held: d}}}} with d = d_of(tag, slug) (ANY_HALF for S, RcG and the base)."""
    judge = {}
    for t in list(P.DFIX_VREAL_TAGS) + [P.DFIX_VREAL_P4]:
        for s, a, sh, h in dirs:
            half = P.ANY_HALF if P.DFIX_VREAL_TAGS.get(t, ("m",))[0] is None else sh
            judge.setdefault(t, {}).setdefault(f"{s}|{a}", {}).setdefault(half, {})[h] = d_of(t, s)
    return judge


def test_dfix_vreal_read_rows_on_synthetic_judges():
    dirs = _vreal_dirs()
    wick = {"cambridge-wickerman-elecgtr2": 0.5, "cambridge-wickerman-elecgtr3": 2.0}

    def d_of(t, s):
        if t == "DV-P2b-dfix-stem":
            return 0.5
        if t == "DV-P2b-dfix-amp":
            return wick.get(s, 1.0)
        if t == "DV-P2b-wide24-stem" and s == "cambridge-femme-elecgtr5":
            return float("nan")                 # refused: scored as S
        return 1.0
    judge = _vreal_judge(dirs, d_of)
    rows = P.dfix_vreal_read(judge, dirs, quiet=["cambridge-femme-elecgtr5"])
    assert list(rows) == [r[0] for r in P.DFIX_VREAL_PAIRS]
    prim = rows["D_fix - S (primary)"]
    assert prim["all"]["mean"] == pytest.approx(math.log(0.5)) and prim["all"]["clusters"] == 7
    assert prim["all"]["parts"] == 10 and prim["base_dropped"] == 0 and prim["complete"]
    assert prim["clean"]["clusters"] == 2 and prim["crunch"]["clusters"] == 5
    assert prim["without_quiet_inputs"]["parts"] == 9
    assert set(prim["all"]["leave_one_out"]) == set(P.VREAL_BANDS)
    assert rows["W - S"]["refused_scored_as_S"] == 6 and rows["W - S"]["all"]["mean"] == 0.0
    apart = rows["amp track - S (Wickerman 2 and 3 apart)"]["all"]
    one = rows["amp track - S (Wickerman 2 and 3 one part)"]["all"]
    assert apart["parts"] == 11 and one["parts"] == 10
    assert one["per_part"]["cambridge-wickerman-elecgtr2+3"] == pytest.approx(0.0)
    assert rows["amp track - P4"]["b"] == P.DFIX_VREAL_P4
    del judge["DV-RcG"]["cambridge-Signs-ElecGtr3|ac20"]
    with pytest.raises(SystemExit, match="incomplete"):
        P.dfix_vreal_read(judge, dirs, [])


def test_dfix_vreal_recheck_lists_groups_whose_s_render_differs():
    stored = {"a|pr12": {"render_sha256": {"*": "x"}}, "b|pr12": {"render_sha256": {"*": "y"}}}
    assert P.dfix_vreal_recheck({"a|pr12": {"render_sha256": {"*": "x"}}}, stored) == []
    assert P.dfix_vreal_recheck({"a|pr12": {"render_sha256": {"*": "z"}}, "c|pr12": {"render_sha256": {"*": "x"}}},
                                stored) == ["a|pr12", "c|pr12"]


def test_dfix_vreal_report_stops_on_a_changed_s_render_and_reads_synthetic_judges(tmp_path, monkeypatch):
    from learn import direct_stems as DS

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    dirs = _vreal_dirs()
    monkeypatch.setattr(P, "vreal_ctx", lambda: (None, None, None, dirs, None, None))
    monkeypatch.setattr(P, "s_positive_control", lambda sj: {"n": P.S_CONTROL_N, "passes": True, "max_abs_log": 0.0})
    judge = _vreal_judge(dirs, lambda t, s: 0.8 if t == "DV-P2b-dfix-stem" else 1.0)
    judge["S"] = judge[P.DFIX_VREAL_BASE]
    tags = list(P.DFIX_VREAL_TAGS) + [P.DFIX_VREAL_P4, "S"]
    d = tmp_path / P.VREAL_DIR / "answers"
    d.mkdir(parents=True)
    for t in tags:
        extra = {"floor_frame_share": {s: {"A": 0.3 if s == "cambridge-Signs-ElecGtr3" else 0.0, "B": 0.0}
                                       for s in PR.VREAL}, "stem_half_lufs": {}, "p2d_stems_median_lufs": -14.7} \
            if t == "DV-P2b-dfix-stem" else {"labels_used": {}} if t == "DV-RcG" else {}
        (d / f"{t}.json").write_text(json.dumps({"tag": t, "answers": {"t": t}, **extra}))
        for key, j in judge[t].items():
            slug, amp = key.split("|")
            p = tmp_path / P.VREAL_DIR / "judge" / t / f"{key}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"slug": slug, "amp": amp, "judge": j, "render_sha256": {"*": key},
                                     "answers_sha256": P.answers_sha({"t": t})}))
    shas = {t: DS.hashlib_file(d / f"{t}.json") for t in P.DFIX_VREAL_TAGS}
    monkeypatch.setattr(P, "require", lambda k: {P.DFIX_VREAL_HASHES: shas})
    args = argparse.Namespace(label="t")
    bad = tmp_path / P.VREAL_DIR / "judge" / P.DFIX_VREAL_BASE / "cambridge-Signs-ElecGtr3|ac20.json"
    rec = json.loads(bad.read_text())
    bad.write_text(json.dumps(dict(rec, render_sha256={"*": "other"})))
    with pytest.raises(SystemExit, match="cambridge-Signs-ElecGtr3\\|ac20"):
        P.cmd_dfix_vreal_report(args)
    assert not (tmp_path / P.VREAL_DIR / "report-t.json").exists()
    bad.write_text(json.dumps(rec))
    P.cmd_dfix_vreal_report(args)
    out = json.loads((tmp_path / P.VREAL_DIR / "report-t.json").read_text())
    assert out["rows"]["D_fix - S (primary)"]["all"]["mean"] == pytest.approx(math.log(0.8))
    assert out["side_row_without"]["parts"] == ["cambridge-Signs-ElecGtr3"]
    with pytest.raises(SystemExit, match="read once"):
        P.cmd_dfix_vreal_report(args)


def test_dfix_vreal_predict_end_to_end_on_synthetic_audio(tmp_path, monkeypatch, capsys):
    """The answers command with stand-ins for the models, the V-real context and its audio (noise): every declared
    tag written per half (models) or for any half (RcG, S again), S copied from phase 4's answers, the stem input at
    the mix's gain, the amp track at D_fix's input level, the per-tag records."""
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    from learn import arm_a_mega53 as A
    from learn import cc_build as CB
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import song_aug as SA
    from learn import song_model as SM

    if not (A.L.SS_OUT / "armB" / "menu-S.json").exists():
        pytest.skip("needs the local data root's stored menu S")
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    ms = A.L.menu_S()
    slugs = ["cambridge-Signs-ElecGtr3", "cambridge-wickerman-elecgtr2"]
    dirs = [(s, a, sh, h) for s in slugs for a in PR.AMPS for sh, h in (("A", "B"), ("B", "A"))]
    monkeypatch.setattr(P, "vreal_ctx", lambda: (None, None, "drift", dirs, {s: {"kind": "stagef"} for s in slugs}, ms))
    rng = np.random.default_rng(0)
    audio = {s: rng.normal(0, 0.05, 480_000) for s in slugs}
    mixes = {s: 2 * a for s, a in audio.items()}
    monkeypatch.setattr(DE, "f_inputs", lambda slug, sep=None: (mixes[slug], None, {"context": "c"}))
    monkeypatch.setattr(DS, "_load", lambda p: {"stems": {f"stagef/{s}": {"sha256": s} for s in slugs}})
    monkeypatch.setattr(DS, "stored_stem", lambda man, key: audio[key.split("/")[1]])
    monkeypatch.setattr(P, "amp_track", lambda slug, info: 0.5 * audio[slug])
    monkeypatch.setattr(P, "require", lambda k: {})
    monkeypatch.setattr(P, "recipe_inputs", lambda **kw: (None, {}, {}, {}, {"doubles": "dropped"}))
    monkeypatch.setattr(CB, "cc_inventory", lambda: {})
    monkeypatch.setattr(P, "dfix_vreal_leaks", lambda kept, inv: {"checked": 1})
    monkeypatch.setattr(P, "vreal_mix_target", lambda: -12.25)
    monkeypatch.setattr(P, "model_input_lufs", lambda rec: -13.7)
    np.savez(tmp_path / "d.npz", lufs=[-15.0, -14.0])
    monkeypatch.setattr(P, "rung_path", lambda croot, rung, doubled=frozenset(): lambda i: tmp_path / "d.npz")
    recs = [{"train_ids": [1, 2, P.REAL_ROW0], "seed": sd, "model_sha256": {"best": f"m{sd}"}, "rung": "b"}
            for sd in P.SEEDS]
    monkeypatch.setattr(P, "dfix_vreal_load", lambda m: ([m], recs))
    (tmp_path / "runs").mkdir()
    for sd in P.SEEDS:
        (tmp_path / "runs" / f"P2b-wide24-{sd}.json").write_text(json.dumps({"train_ids": [1, 2]}))
    monkeypatch.setattr(P, "rung_rows", lambda kept, rend, ids: ids)
    enc = {(a, c): F.encode(dict(ms[a][c][1]), a) for a in PR.AMPS for c in ("clean", "crunch")}
    monkeypatch.setattr(P, "constant_of", lambda rows: {k: {"cont": v[0]} for k, v in enc.items()})
    monkeypatch.setattr(P, "goat_labels", lambda: ([], {}, set()))
    seen, cell = [], []
    real_input = P.vreal_model_input
    monkeypatch.setattr(P, "vreal_model_input", lambda s8, lu, h, amp, cls: cell.append((amp, cls)) or real_input(
        s8, lu, h, amp, cls))
    monkeypatch.setattr(F, "run_nets", lambda nets, X, C: seen.append((nets[0], X[0], C[0])) or [[None]])
    monkeypatch.setattr(F, "readout", lambda outs: {"a2": enc[cell[-1]][0], "mics": [int(v) for v in enc[cell[-1]][4]],
                                                    "sw_p": [float(v) for v in enc[cell[-1]][2]]})
    s_ans = {f"{s}|{a}": {P.ANY_HALF: {"select": ms[a][PR.VREAL[s][1]][0],
                                       "settings": LO.sdict(ms[a][PR.VREAL[s][1]][1])}} for s in slugs for a in PR.AMPS}
    (tmp_path / P.VREAL_DIR / "answers").mkdir(parents=True)
    P.vreal_answers_path("S").write_text(json.dumps({"answers": s_ans}))
    P.cmd_dfix_vreal_predict(argparse.Namespace(names="", which="best"))
    out = {t: json.loads(P.vreal_answers_path(t).read_text()) for t in P.DFIX_VREAL_TAGS}
    for t, (m, kind, ro) in P.DFIX_VREAL_TAGS.items():
        a = out[t]["answers"]
        assert len(a) == 6 and all(set(v) == ({"A", "B"} if m else {P.ANY_HALF}) for v in a.values())
        if m:
            assert out[t]["model"] == m and out[t]["model_sha256"] == [f"m{sd}" for sd in P.SEEDS]
    assert out[P.DFIX_VREAL_BASE]["answers"] == s_ans
    assert out["DV-RcG"]["labels_used"] == {k: 0 for k in s_ans} and out["DV-RcG"]["answers"] == s_ans
    st = out["DV-P2b-dfix-stem"]
    assert st["input_lufs"] == -12.25 and st["p2d_stems_median_lufs"] == -14.5
    w = "cambridge-Signs-ElecGtr3"
    g = st["gains_db"][w]
    assert g == pytest.approx(-12.25 - SA.lufs(mixes[w]))
    lu = st["stem_half_lufs"][w]["A"]
    assert lu == pytest.approx(DS.step4_half(audio[w], mixes[w], "A", g)[2]) and lu == pytest.approx(
        -12.25 - 6.02, abs=0.2)                          # the stem is the mix less 6 dB, at the mix's gain
    amp = out["DV-P2b-dfix-amp"]
    assert amp["input_lufs"] == -13.7 and amp["amp_half_lufs"][w]["A"] == pytest.approx(-13.7, abs=0.2)
    assert set(amp["gains_db"]) == set(slugs)          # Wickerman ElecGtr2 read from its own amp track
    assert len(seen) == 3 * len(dirs)                    # D_fix on the stem and the amp track, W on the stem
    assert sorted({round(float(c[-2]), 6) for m_, x, c in seen if m_ == "P2b-wide24"}) == sorted(
        {round(float(SM.cond_vec("pr12", "clean", [v, 0.0])[-2]), 6) for s in slugs
         for v in st["stem_half_lufs"][s].values()})            # W read the stems at their recorded loudness
    assert all(float(c[-1]) == 0.0 for _, _, c in seen)
    assert P.DFIX_VREAL_HASHES in capsys.readouterr().out
    monkeypatch.setattr(P, "require", lambda k: {P.DFIX_VREAL_HASHES: {"DV-RcG": "x"}})
    with pytest.raises(SystemExit, match="read once"):
        P.cmd_dfix_vreal_predict(argparse.Namespace(names="", which="best"))


def test_vreal_render_records_s_render_hashes_beside_phase_4s(tmp_path, monkeypatch, capsys):
    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    slugs = ["cambridge-Signs-ElecGtr3", "cambridge-femme-elecgtr5"]
    dirs = [(s, "pr12", sh, h) for s in slugs for sh, h in (("A", "B"), ("B", "A"))]
    monkeypatch.setattr(P, "vreal_ctx", lambda: (None, None, None, dirs, {s: {"kind": "stagef"} for s in slugs},
                                                 {"pr12": {"crunch": (0, {})}}))

    class Menu(dict):
        def __missing__(self, k):
            return (0, {})

    class R:
        def menu(self):
            return {"pr12": Menu()}

        def close(self):
            pass
    monkeypatch.setattr(LO, "_wait_cap", lambda *a: None)
    monkeypatch.setattr(CB, "new_renderer", lambda: R())
    monkeypatch.setattr(K, "key", lambda st: 0)
    monkeypatch.setattr(PS, "free_gb", lambda: 1e9)
    monkeypatch.setattr(A, "group_ctx", lambda *a: {"di32": None, "ref": None, "di": None, "part": {"judge_lag": 0}})
    monkeypatch.setattr(AM, "fresh_render", lambda *a: "y")
    monkeypatch.setattr(AM, "audio_sha", lambda y: "h")
    monkeypatch.setattr(K, "judge", lambda *a: {"A": 1.0, "B": 1.0})
    _answers(tmp_path, [])
    ans = {f"{s}|pr12": {P.ANY_HALF: {"select": 0, "settings": {}}} for s in slugs}
    P.vreal_answers_path(P.DFIX_VREAL_BASE).write_text(json.dumps({"answers": ans}))
    with pytest.raises(SystemExit, match="no stored S render"):
        P.vreal_render([P.DFIX_VREAL_BASE], (0, 1), recheck={P.DFIX_VREAL_BASE: "S"})
    for s, h in zip(slugs, ("h", "other")):
        p = tmp_path / P.VREAL_DIR / "judge" / "S" / f"{s}|pr12.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"render_sha256": {P.ANY_HALF: h}}))
    P.vreal_render([P.DFIX_VREAL_BASE], (0, 1), recheck={P.DFIX_VREAL_BASE: "S"})
    got = {s: json.loads((tmp_path / P.VREAL_DIR / "judge" / P.DFIX_VREAL_BASE / f"{s}|pr12.json").read_text())
           for s in slugs}
    assert got[slugs[0]]["identical"] and not got[slugs[1]]["identical"]
    assert got[slugs[1]]["recheck_sha256"] == {P.ANY_HALF: "other"} and got[slugs[1]]["renders"] == 2
    assert "RECHECK: 1 groups" in capsys.readouterr().out


# --- FT (phase_ft): plugin pretraining, the real rows alone tune it -------------------------------------------------

def _ft_records():
    by_unit = {f"b{j}": {"unit": f"b{j}", "di": f"d{j % 8}", "cls": "clean", "section": f"s{j}", "band": "BKS"}
               for j in range(16)}
    brecs = [{"unit": u, "amp": amp, "label": {}} for u in sorted(by_unit) for amp in ("pr12", "ac20")] * 10
    folds = {f"d{j}": j // 2 for j in range(8)}
    grecs, gunits = _goat_records()
    for u in gunits.values():
        u.update(section=u["unit"], band="GOAT")
    return brecs, by_unit, folds, grecs, gunits


def test_ft_names_are_their_own():
    assert [P.ft_name(k) for k in (None, 0, 3)] == ["P2b-ft", "P2b-ft-k0", "P2b-ft-k3"]
    assert P.ft_name(1, inner=True) == "P2b-ft-k1-inner"
    with pytest.raises(SystemExit):
        P.ft_name(None, inner=True)
    with pytest.raises(SystemExit):
        P.ft_name(4)
    ft = {P.ft_name(k, i) for k in range(4) for i in (False, True)} | {P.FT_BASE}
    assert not ft & ({P.dfix_run_name(k) for k in (None, 0, 1, 2, 3)} | set(P.DFIX_READS))
    assert P.read_phase("P2b-ft") == "phase_ft" and P.read_phase("P2b-dfix") == "phase_dfix"
    assert P.read_phase("P2b-dfixp10") == "phase_dfix_share" and P.read_phase("P2a-goat") == "phase_5c"
    assert P.report_phase({"P2b-ft", "P2b-dfix", "S"}) == "phase_ft"
    assert P.report_phase({"P2b-dfix", "S"}) == "phase_dfix"
    assert "phase_ft" in P.ARM_FOLD_PHASES


def test_ft_k_rows_are_dfix_ks_and_the_inner_run_never_holds_fold_k():
    brecs, by_unit, folds, grecs, gunits = _ft_records()
    lab = lambda rec: rec["amp"]                                     # noqa: E731
    bfold = lambda r: folds[by_unit[r["real"]]["di"]]                # noqa: E731
    gfold = lambda r: gunits[r["real"]]["fold"]                      # noqa: E731
    for k in range(4):
        assert P.ft_rows_of(brecs, by_unit, folds, grecs, gunits, k, False, lab) == \
            P.dfix_rows_of(brecs, by_unit, folds, grecs, gunits, k, lab)
        j = (k + 1) % 4
        tr, held, n = P.ft_rows_of(brecs, by_unit, folds, grecs, gunits, k, True, lab)
        fold_of = lambda r: bfold(r) if r["i"] < P.GOAT_ROW0 else gfold(r)   # noqa: E731
        assert tr and held and n["real_rows"] == P.REAL_PER_EPOCH and n["goat_rows"] == P.GOAT_PER_EPOCH
        assert all(fold_of(r) not in (k, j) for r in tr)
        assert all(fold_of(r) == j for r in held)
        assert {r["real"] for r in held if r["i"] < P.GOAT_ROW0} == \
            {u for u, p in by_unit.items() if folds[p["di"]] == j}
        assert not {r["real"] for r in tr} & {r["real"] for r in held}


def test_ft_epochs_median_rounds_half_up():
    E = lambda *es: P.ft_epoch_of([{"log": _inner_log([1.0] * (e - 1) + [0.5])} for e in es])   # noqa: E731
    assert E(7) == 7 and E(3, 4) == 4 and E(1, 2, 3, 4, 5, 6, 7, 8) == 5 and E(2, 9, 9, 30) == 9
    assert E(10, 11, 12, 13, 14, 15, 16, 17) == 14
    with pytest.raises(SystemExit):
        E()


def test_ft_rate_takes_only_the_declared_values_and_a_fallback_needs_the_ledger(monkeypatch):
    a = lambda lr=None, cap=None: argparse.Namespace(ft_lr=lr, ft_cap=cap)   # noqa: E731
    seen = []
    monkeypatch.setattr(P, "require", lambda key: seen.append(key) or {})
    assert P.ft_rate(a()) == (1e-4, 100) and seen == []
    assert P.ft_rate(a(3e-5)) == (3e-5, 100) and seen == ["phase_ft_fallback"]
    assert P.ft_rate(a(cap=300)) == (1e-4, 300)
    for bad in (a(1e-3), a(cap=200)):
        with pytest.raises(SystemExit):
            P.ft_rate(bad)


def test_ft_layout_takes_only_the_real_training_rows():
    pytest.importorskip("numpy")
    ti, hi, rh = P.ft_layout(10, 4, 20, 3)
    assert list(ti) == [10, 11, 12, 13] and list(hi) == list(range(14, 17)) and list(rh) == [17, 18, 19]
    ti, hi, rh = P.ft_layout(10, 4, 17, 0)
    assert len(rh) == 0 and list(hi) == [14, 15, 16]


def test_ft_read_check_takes_only_the_state_after_e_epochs():
    ok = {"test": "P2b-ft-k1", "seed": 1, "inner": False, "E": 12, "epochs_run": 12,
          "models": {"final": "m.pt", "best": "m.pt"}, "model_sha256": {"final": "h", "best": "h"}}
    P.ft_read_check(ok)
    P.ft_read_check({"test": "P2b-dfix1"})                       # not FT: untouched
    for bad in ({"inner": True}, {"models": {"final": "m.pt", "best": "b.pt"}},
                {"model_sha256": {"final": "h", "best": "g"}}, {"epochs_run": 13}):
        with pytest.raises(SystemExit):
            P.ft_read_check({**ok, **bad})


def _inner_log(vals):
    return [{"epoch": e, "real_val_smoothed": v} for e, v in enumerate(vals)]


def test_ft_inner_e_is_the_first_argmin_of_the_smoothed_loss_not_the_stop_rules():
    assert P.ft_inner_E(_inner_log([3.0, 2.0, 1.0, 0.9995, 1.2])) == 4        # a dip below 1e-3 still counts
    assert P.ft_inner_E(_inner_log([3.0, 1.0, 2.0, 1.0])) == 2                # ties: the first
    assert P.ft_inner_E(_inner_log([float("nan"), 2.0, 1.5])) == 3
    assert P.ft_inner_E(_inner_log([0.5, 1.0])) == 1
    with pytest.raises(SystemExit):
        P.ft_inner_E([{"epoch": 0, "real_val": {"total": 1.0}}])


def test_ft_fallbacks_settle_in_the_declared_order():
    def recs(E, at_cap, n=8):
        return [{"log": _inner_log([1.0] * (E - 1) + [0.5] + [0.6]), "at_cap": a} for a in [at_cap] * n]

    def getter(table):
        return lambda lr, cap: table.get((lr, cap))

    lo, hi, slow, long = P.FT_LR, P.FT_FALLBACK_LR, P.FT_CAP, P.FT_FALLBACK_CAP
    plain = recs(40, False)
    assert "not all done" in P.ft_fallback_refusal(getter({}), lo, slow)
    assert P.ft_fallback_refusal(getter({(lo, slow): plain}), lo, slow) is None
    assert "settled" in P.ft_fallback_refusal(getter({(lo, slow): plain}), lo, long)    # no unprompted fallback
    capped = recs(97, True)
    assert "cap rule fired" in P.ft_fallback_refusal(getter({(lo, slow): capped}), lo, slow)
    assert P.ft_fallback_refusal(getter({(lo, slow): capped, (lo, long): plain}), lo, long) is None
    fast = recs(1, False)
    t = {(lo, slow): fast}
    assert "rate rule fired" in P.ft_fallback_refusal(getter(t), lo, slow)
    t[(hi, slow)] = capped                                                   # rate first, then the cap at the new rate
    assert "cap rule fired" in P.ft_fallback_refusal(getter(t), hi, slow)
    t[(hi, long)] = capped                                                   # each at most once: no third step
    assert P.ft_fallback_refusal(getter(t), hi, long) is None
    assert P.ft_name(0, True, hi, long) == "P2b-ft-k0-inner-lr3e-05-cap300"
    assert P.ft_name(0, True) == "P2b-ft-k0-inner" and P.ft_name(0, False, hi, long) == "P2b-ft-k0"


def test_ft_epochs_come_from_the_inner_logs():
    assert P.ft_epoch_of([{"log": _inner_log([2.0, 1.0, 1.5]), "E": 99}]) == 2


# --- FT to V-real (phase_ft's map, after phase_ft_carry) -------------------------------------------------------------

def test_ft_vreal_reads_ft_against_f41s_stored_tags_with_s_as_base():
    assert P.FT_VREAL_PAIRS[0] == ("FT - S (primary)", P.FT_VREAL_TAG, P.DFIX_VREAL_BASE)
    assert {b for _, a, b in P.FT_VREAL_PAIRS} == set(P.FT_VREAL_STORED)
    assert all(a == P.FT_VREAL_TAG for _, a, _ in P.FT_VREAL_PAIRS)
    assert set(P.FT_VREAL_STORED) <= set(P.DFIX_VREAL_TAGS)                  # zero new renders for the comparators
    assert not set(P.FT_VREAL_TAGS) & (set(P.DFIX_VREAL_TAGS) | {"S"})       # FT's own tags never overwrite F41's
    assert P.FT_VREAL_RECHECK_N * 2 == 20                                    # the declared 20 recheck renders


def test_ft_vreal_recheck_groups_are_a_fixed_seeded_ten():
    groups = {f"part{i}|{a}" for i in range(11) for a in ("pr12", "sw50r", "ac20")}
    pick = P.ft_vreal_recheck_groups(groups)
    assert len(pick) == 10 and set(pick) <= groups and pick == sorted(pick)
    assert P.ft_vreal_recheck_groups(set(sorted(groups, reverse=True))) == pick
    assert P.ft_vreal_recheck_groups({"a|pr12", "b|pr12"}) == ["a|pr12", "b|pr12"]


def test_ft_vreal_inputs_must_equal_read_3s():
    f41 = {"input_lufs": -12.25, "gains_db": {"p": 1.5}, "input_hashes": {"p": {"stem": "h"}},
           "floor_frame_share": {"p": {"A": 0.0, "B": 0.1}}, "stem_half_lufs": {"p": {"A": -14.0, "B": -15.0}},
           "answers": {"other": 1}}
    mine = {k: v for k, v in f41.items() if k != "answers"}
    assert P.ft_vreal_input_drift(mine, f41) == []
    assert P.ft_vreal_input_drift({**mine, "gains_db": {"p": 1.6}}, f41) == ["gains_db"]
    assert P.ft_vreal_input_drift({**mine, "input_hashes": {"p": {"stem": "g"}}}, f41) == ["input_hashes"]
    assert P.ft_vreal_input_drift({k: v for k, v in mine.items() if k != "stem_half_lufs"}, f41) == ["stem_half_lufs"]


def test_two_look_interval_is_the_95_percent_cluster_t_interval():
    pytest.importorskip("scipy")
    per = {"b1": -0.1, "b2": 0.05, "b3": -0.2, "b4": 0.0, "b5": -0.05, "b6": -0.12, "b7": 0.02}
    lo, hi = P.two_look_interval(per)
    c = P.clustered([(b, b, v) for b, v in per.items()])
    assert (lo + hi) / 2 == pytest.approx(c["mean"])
    assert lo < c["lo90"] and hi > c["hi90"]                                   # wider than the 90% interval
    half90 = c["hi90"] - c["mean"]
    assert (hi - c["mean"]) / half90 == pytest.approx(2.4469 / 1.9432, abs=1e-3)   # t(0.975, 6) / t(0.95, 6)
    assert P.two_look_interval({"b1": 0.1}) == (None, None)


def test_ft_vreal_predict_refuses_before_the_carry_and_once_recorded(monkeypatch):
    def ledger(entry):
        def req(k):
            if k not in entry:
                raise SystemExit(f"no {k}")
            return entry
        return req

    monkeypatch.setattr(P, "recipe_inputs", lambda **kw: pytest.fail("refusals come before any data is read"))
    monkeypatch.setattr(P, "require", ledger({"phase_ft": "x"}))
    with pytest.raises(SystemExit, match="phase_ft_carry"):
        P.cmd_ft_vreal_predict(argparse.Namespace())
    monkeypatch.setattr(P, "require", ledger({"phase_ft": "x", "phase_ft_carry": "x",
                                              P.FT_VREAL_HASHES: {P.FT_VREAL_TAG: "h"}}))
    with pytest.raises(SystemExit, match="read once"):
        P.cmd_ft_vreal_predict(argparse.Namespace())


def test_ft_vreal_unhashed_checks_fts_and_f41s_answers(tmp_path, monkeypatch):
    from learn import direct_stems as DS

    monkeypatch.setattr(P, "out_dir", lambda: tmp_path)
    d = tmp_path / P.VREAL_DIR / "answers"
    d.mkdir(parents=True)
    for t in (*P.FT_VREAL_TAGS, *P.FT_VREAL_STORED):
        (d / f"{t}.json").write_text(json.dumps({"tag": t}))
    sha = {t: DS.hashlib_file(d / f"{t}.json") for t in (*P.FT_VREAL_TAGS, *P.FT_VREAL_STORED)}
    entry = {P.FT_VREAL_HASHES: {t: sha[t] for t in P.FT_VREAL_TAGS},
             P.DFIX_VREAL_HASHES: {t: sha[t] for t in P.FT_VREAL_STORED}}
    assert P.ft_vreal_unhashed(entry) == []
    (d / f"{P.FT_VREAL_TAG}.json").write_text(json.dumps({"tag": "changed"}))
    assert [p.split(":")[0] for p in P.ft_vreal_unhashed(entry)] == [P.FT_VREAL_TAG]
    (d / "DV-RcG.json").unlink()
    assert len(P.ft_vreal_unhashed(entry)) == 2
    assert P.ft_vreal_unhashed({}) and len(P.ft_vreal_unhashed({})) == 5


def test_ft_vreal_render_and_report_refuse_before_the_hashes(monkeypatch):
    monkeypatch.setattr(P, "require", lambda k: {})
    monkeypatch.setattr(P, "ft_vreal_unhashed", lambda e: ["x: not recorded"])
    monkeypatch.setattr(P, "vreal_render", lambda *a, **k: pytest.fail("no render before the hashes"))
    with pytest.raises(SystemExit, match="hashes"):
        P.cmd_ft_vreal_render(argparse.Namespace(shard=(0, 3)))
    monkeypatch.setattr(P, "out_dir", lambda: __import__("pathlib").Path("/nonexistent-ft-vreal"))
    with pytest.raises(SystemExit, match="hashes"):
        P.cmd_ft_vreal_report(argparse.Namespace(label="t"))
    with pytest.raises(SystemExit, match="label"):
        P.cmd_ft_vreal_report(argparse.Namespace(label=""))


def test_ft_inner_runs_are_checked_against_their_own_seeds_w():
    w = {1: "w1", 2: "w2"}
    inners = [{"real_fold": k, "seed": sd, "init": {"sha256": w[sd]}} for k in range(4) for sd in (1, 2)]
    assert P.ft_inner_init_refusal(inners, w.get) == []                     # both seeds, as the all-labels FT takes
    inners[3]["init"]["sha256"] = "w1"
    assert P.ft_inner_init_refusal(inners, w.get) == [(1, 2)]


def _ft_world(cap300=False):
    """Synthetic W, D_fix, inner and all-labels FT records for `ft_vreal_provenance`."""
    r0 = P.REAL_ROW0
    w = {sd: {"model_sha256": {"best": f"w{sd}"}, "train_ids": [1, 2], "held_ids": [9]} for sd in P.SEEDS}
    d = {sd: {"train_ids": [1, 2, r0, r0 + 1], "held_ids": [9], "dfix": {"inputs_sha256": "x"}} for sd in P.SEEDS}
    es = [10, 12, 14, 16, 18, 20, 22, 24]                                    # median 17
    inner = [{"real_fold": k, "seed": sd, "init": {"sha256": f"w{sd}"}, "at_cap": False,
              "log": _inner_log([1.0] * (es[2 * k + j] - 1) + [0.5, 0.6])}
             for k in range(P.REAL_FOLDS) for j, sd in enumerate(P.SEEDS)]
    capped = [dict(r_, at_cap=True) for r_ in inner]
    cap = P.FT_FALLBACK_CAP if cap300 else P.FT_CAP
    sets = {(P.FT_LR, P.FT_CAP): capped if cap300 else inner}
    if cap300:
        sets[(P.FT_LR, P.FT_FALLBACK_CAP)] = inner
    recs = [{"seed": sd, "lr": P.FT_LR, "cap": cap, "E": 17, "init": {"sha256": f"w{sd}"},
             "train_ids": [1, 2, r0, r0 + 1], "held_ids": [9], "ft_train_ids": [r0, r0 + 1],
             "dfix": {"inputs_sha256": "x"}} for sd in P.SEEDS]
    return recs, sets.get, lambda lr, cap_: sets.get((lr, cap_)), w.get, d.get


def test_ft_vreal_provenance_takes_only_the_declared_all_labels_runs():
    for cap300 in (False, True):
        recs, _, get, w_of, d_of = _ft_world(cap300)
        assert P.ft_vreal_provenance(recs, get, w_of, d_of) == recs
    recs, _, get, w_of, d_of = _ft_world(True)
    bad_cap = [dict(r_, cap=P.FT_CAP) for r_ in recs]                        # the cap rule fired: 100 is not settled
    with pytest.raises(SystemExit, match="settled"):
        P.ft_vreal_provenance(bad_cap, get, w_of, d_of)
    recs, _, get, w_of, d_of = _ft_world()
    r0 = P.REAL_ROW0
    for change, why in (({"E": 18}, "inner median"), ({"init": {"sha256": "other"}}, "best"),
                        ({"train_ids": [1, 2, r0]}, "D_fix's training labels"),          # a subset is not enough
                        ({"ft_train_ids": [r0]}, "D_fix's training labels"),
                        ({"held_ids": [8]}, "held rows"),
                        ({"train_ids": [1, 3, r0, r0 + 1]}, "plugin or held rows"),
                        ({"dfix": {"inputs_sha256": "y"}}, "D_fix's training labels")):
        with pytest.raises(SystemExit, match=why):
            P.ft_vreal_provenance([dict(recs[0], **change), recs[1]], get, w_of, d_of)
    moved = get(P.FT_LR, P.FT_CAP)
    moved[1]["init"] = {"sha256": "w-other"}
    with pytest.raises(SystemExit, match="own seed's W"):
        P.ft_vreal_provenance(recs, lambda lr, cap: moved if (lr, cap) == (P.FT_LR, P.FT_CAP) else None, w_of, d_of)


def test_ft_vreal_load_refuses_inner_fold_and_split_runs(monkeypatch):
    recs, _, _, _, _ = _ft_world()
    ok = {"test": P.FT_BASE, "inner": False, "real_fold": None, "epochs_run": 17,
          "models": {"final": "m.pt", "best": "m.pt"}, "model_sha256": {"final": "h", "best": "h"}}
    runs = {sd: dict(r_, **ok) for sd, r_ in zip(P.SEEDS, recs)}
    monkeypatch.setattr(P, "load_run", lambda name, sd, which: (None, runs[sd]))
    monkeypatch.setattr(P, "ft_vreal_provenance", lambda recs_, *a: recs_)
    assert len(P.ft_vreal_load()[1]) == 2
    sd = P.SEEDS[1]
    for change, why in (({"inner": True}, "read checkpoint"), ({"real_fold": 2}, "all-labels"),
                        ({"held_ids": [7]}, "one training set"), ({"cap": P.FT_FALLBACK_CAP}, "rate and cap"),
                        ({"models": {"final": "m.pt", "best": "b.pt"}}, "read checkpoint")):
        old = runs[sd]
        runs[sd] = dict(old, **change)
        with pytest.raises(SystemExit, match=why):
            P.ft_vreal_load()
        runs[sd] = old


def test_ft_vreal_report_reads_synthetic_judges_and_stops_on_the_recheck(tmp_path, monkeypatch):
    pytest.importorskip("scipy")
    from learn import direct_stems as DS

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    dirs = _vreal_dirs()
    monkeypatch.setattr(P, "vreal_ctx", lambda: (None, None, None, dirs, None, None))
    monkeypatch.setattr(P, "s_positive_control", lambda sj: {"n": P.S_CONTROL_N, "passes": True, "max_abs_log": 0.0})
    pick = P.ft_vreal_recheck_groups({f"{s}|{a}" for s, a, _, _ in dirs})
    per_half = {P.FT_VREAL_TAG, "DV-P2b-dfix-stem"}
    dval = {P.FT_VREAL_TAG: 0.8, "DV-P2b-dfix-stem": 0.9}
    tags = [*P.FT_VREAL_TAGS, *P.FT_VREAL_STORED, "S"]
    d = tmp_path / P.VREAL_DIR / "answers"
    d.mkdir(parents=True)
    quiet = "cambridge-Signs-ElecGtr3"
    for t in tags:
        extra = {"floor_frame_share": {s: {"A": 0.3 if s == quiet else 0.0, "B": 0.0} for s in PR.VREAL}} \
            if t == P.FT_VREAL_TAG else {}
        (d / f"{t}.json").write_text(json.dumps({"tag": t, "answers": {"t": t}, **extra}))
        for s, a, sh, h in dirs:
            key = f"{s}|{a}"
            if t == P.FT_VREAL_RECHECK and key not in pick:
                continue
            p = tmp_path / P.VREAL_DIR / "judge" / t / f"{key}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            rec = json.loads(p.read_text()) if p.exists() else {
                "slug": s, "amp": a, "judge": {}, "render_sha256": {"*": key}, "answers_sha256": P.answers_sha({"t": t})}
            rec["judge"].setdefault(sh if t in per_half else P.ANY_HALF, {})[h] = dval.get(t, 1.0)
            p.write_text(json.dumps(rec))
    ft_sha = {t: DS.hashlib_file(d / f"{t}.json") for t in P.FT_VREAL_TAGS}
    st_sha = {t: DS.hashlib_file(d / f"{t}.json") for t in P.FT_VREAL_STORED}
    monkeypatch.setattr(P, "require", lambda k: {P.FT_VREAL_HASHES: ft_sha, P.DFIX_VREAL_HASHES: st_sha})
    args = argparse.Namespace(label="t")
    rp = tmp_path / P.VREAL_DIR / "report-t.json"
    f41 = tmp_path / P.VREAL_DIR / P.FT_VREAL_F41[0]
    f41.write_text(json.dumps({"rows": {"D_fix - S (primary)": {"all": {"mean": math.log(0.9)}},
                                        "D_fix - RcG": {"all": {"mean": math.log(0.9) + 0.01}}}}))
    with pytest.raises(SystemExit, match="D_fix - RcG"):                    # comparators must reproduce F41's rows
        P.cmd_ft_vreal_report(args)
    f41.write_text(json.dumps({"rows": {"D_fix - S (primary)": {"all": {"mean": math.log(0.9)}},
                                        "D_fix - RcG": {"all": {"mean": math.log(0.9)}}}}))
    jd = tmp_path / P.VREAL_DIR / "judge" / P.FT_VREAL_RECHECK
    one = jd / f"{pick[0]}.json"
    rec = json.loads(one.read_text())
    one.write_text(json.dumps(dict(rec, render_sha256={"*": "other"})))
    with pytest.raises(SystemExit, match="recheck"):
        P.cmd_ft_vreal_report(args)
    one.unlink()
    with pytest.raises(SystemExit, match="recheck"):
        P.cmd_ft_vreal_report(args)
    extra_g = sorted({f"{s}|{a}" for s, a, _, _ in dirs} - set(pick))[0]
    (jd / f"{extra_g}.json").write_text(json.dumps(dict(rec, slug=extra_g.split("|")[0], amp=extra_g.split("|")[1],
                                                        render_sha256={"*": extra_g})))
    one.write_text(json.dumps(rec))
    with pytest.raises(SystemExit, match="recheck"):
        P.cmd_ft_vreal_report(args)
    (jd / f"{extra_g}.json").unlink()
    monkeypatch.setattr(P, "s_positive_control", lambda sj: {"n": P.S_CONTROL_N, "passes": False})
    with pytest.raises(SystemExit, match="positive control"):
        P.cmd_ft_vreal_report(args)
    assert not rp.exists()
    monkeypatch.setattr(P, "s_positive_control", lambda sj: {"n": P.S_CONTROL_N, "passes": True, "max_abs_log": 0.0})
    P.cmd_ft_vreal_report(args)
    out = json.loads(rp.read_text())
    rows = out["rows"]
    assert rows["FT - S (primary)"]["all"]["mean"] == pytest.approx(math.log(0.8))
    assert rows["FT - D_fix"]["all"]["mean"] == pytest.approx(math.log(0.8 / 0.9))
    assert rows["FT - RcG"]["all"]["mean"] == pytest.approx(math.log(0.8))
    assert rows["FT - S (primary)"]["base_dropped"] == 0 and rows["FT - S (primary)"]["missing"] == 0
    lo, hi = rows["FT - S (primary)"]["two_look_95"]
    assert (lo + hi) / 2 == pytest.approx(math.log(0.8))
    assert out["side_row_without"]["parts"] == [quiet] and out["positive_control_S"]["passes"]
    with pytest.raises(SystemExit, match="read once"):
        P.cmd_ft_vreal_report(args)


def test_leakage_guard_reads_the_all_labels_ft_run(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "DFIX_K", 1)
    (tmp_path / "runs").mkdir()
    for sd in P.SEEDS:                                       # shaped as cmd_train_ft's all-labels output
        (tmp_path / "runs" / f"{P.FT_BASE}-{sd}.json").write_text(json.dumps({
            "train_ids": [1, P.REAL_ROW0, P.GOAT_ROW0], "held_ids": [2], "ft_train_ids": [P.REAL_ROW0, P.GOAT_ROW0],
            "real_fold": None, "inner": False, "dfix": {"target_lufs": {"bks/u": 0, "g/u": 0}}}))
    kept = {1: {"section": "s1/Band1_Song_Full/di.wav@5.0", "band": "B1", "session_dir": "/d/Band1_Song_Full", "di": "d1"},
            2: {"section": "s1/NS_Full/di.wav@5.0", "band": "NS", "session_dir": "/d/NS_Full", "di": "d2"},
            3: {"section": "s1/BKS_Full/di.wav@1.0", "band": "BKS", "session_dir": "/d/BKS_Full", "di": "d3"}}
    inv = {"d1": {"song": "Song"}, "d2": {"song": "NS"}, "d3": {"song": "Real"}}
    monkeypatch.setattr(P, "dfix_real_rows", lambda k: ([{"i": P.REAL_ROW0, "real": "bks/u"},
                                                         {"i": P.GOAT_ROW0, "real": "g/u"}], [], {}))
    units = [("bks/u", "bks", {"band": "BKS", "section": "s1/BKS_Full/di.wav@1.0", "sd": "/d/BKS_Full", "di": "d3"}),
             ("g/u", "goat", {"band": "GOAT player1", "item": "item_0"})]
    monkeypatch.setattr(P, "dfix_units", lambda: units)
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs" / "backings-wide-pool.json").write_text(json.dumps({"entries": [
        {"id": "s1/Band1_Song_Full/di.wav@5.0", "kind": "training", "session": "s1/Band1_Song_Full"}]}))
    for u, b in (("bks/u", "s1/BKS_Full/di.wav@1.0"), ("g/u", "s1/Band1_Song_Full/di.wav@5.0")):
        p = P.dfix_input_path(u, 0)
        p.parent.mkdir(parents=True, exist_ok=True)
        np.savez(p, backing=b)
    src, cnt = P.dfix_training_sources(kept, inv, P.FT_BASE)
    assert cnt["plugin_rows"] == 2 and cnt["real_rows"] == 2 and cnt["real_units"] == 2
    monkeypatch.setattr(P, "vreal_songs", lambda inv_: set())
    assert P.dfix_vreal_leaks(kept, inv, P.FT_BASE) == cnt
    units[0][2]["band"] = sorted(P.VREAL_BANDS)[0]          # a V-real band among FT's real units
    with pytest.raises(SystemExit, match=f"V-real in {P.FT_BASE}"):
        P.dfix_vreal_leaks(kept, inv, P.FT_BASE)


# --- FT's score by control group (phase_ft_groups) ---------------------------------------------------------------------

def test_ftg_groups_cover_every_model_key_in_the_declared_groups():
    from learn import full_space as F

    keys = list(F.CONT) + list(F.SW) + list(F.CAT)
    got = {k: P.ftg_group(k) for k in keys}
    assert set(got.values()) <= set(P.FTG_ALL) and set(P.FTG_GROUPS) == {"drive", "tone", "cab"}
    for k, g in (("parameters/inputGain", "drive"), ("drive2/drive2Gain", "drive"), ("sw50rAmp/sw50rLevel", "drive"),
                 ("ac20Amp/ac20Power", "drive"), ("compressor/compressorMix", "drive"),
                 ("pr12Amp/pr12Treble", "tone"), ("sw50rEQ/sw50rEQBand4", "tone"), ("ac20Amp/ac20Cut", "tone"),
                 ("cabParameters/leftMicType", "cab"), ("cabParameters/rightRoomMicLevel", "cab"),
                 ("reverb/reverbMix", "effects"), ("pr12Amp/pr12Reverb", "effects"), ("pr12Amp/springOn", "effects"),
                 ("parameters/doublerSpread", "effects"), ("tremolo/tremoloDepth", "effects"),
                 ("parameters/outputGain", "other"), ("parameters/gateThreshold", "other")):
        assert P.ftg_group(k) == g, k
    assert all(got[k] != "other" for k in keys if not k.startswith("parameters/gate"))


def test_ftg_hybrids_swap_exactly_one_group():
    s = {"select": 1, "settings": {"parameters/inputGain": 0.0, "pr12Amp/pr12Treble": 0.5, "reverb/reverbMix": 0.1,
                                   "cabParameters/leftCabDistance": 0.3, "parameters/outputGain": 0.0}}
    a = {"select": 1, "settings": {"parameters/inputGain": 3.0, "pr12Amp/pr12Treble": 0.7, "reverb/reverbMix": 0.1,
                                   "cabParameters/leftCabDistance": 0.4, "parameters/outputGain": 0.0}}
    out, differ = P.ftg_answers({"u|pr12": {"A": a, "B": a}}, {"u|pr12": {P.ANY_HALF: s}})
    assert set(out) == {P.ftg_tag(w, g) for w in P.FTG_WAYS for g in P.FTG_GROUPS}
    assert {g: r["any_key"] for g, r in differ.items()} == {"drive": 2, "tone": 2, "cab": 2, "effects": 0, "other": 0}
    rev = out["FTg-rev-drive"]["u|pr12"]["A"]["settings"]
    add = out["FTg-add-drive"]["u|pr12"]["B"]["settings"]
    assert rev == dict(a["settings"], **{"parameters/inputGain": 0.0})
    assert add == dict(s["settings"], **{"parameters/inputGain": 3.0})
    assert out["FTg-rev-cab"]["u|pr12"]["A"]["settings"] == dict(a["settings"], **{"cabParameters/leftCabDistance": 0.3})
    with pytest.raises(SystemExit, match="select"):
        P.ftg_answers({"u|pr12": {"A": dict(a, select=2)}}, {"u|pr12": {P.ANY_HALF: s}})
    with pytest.raises(SystemExit, match="different keys"):
        P.ftg_mix(a["settings"], {"x": 1}, "drive")


def test_ftg_reads_under_their_own_phase_and_need_the_ledger(monkeypatch):
    assert P.report_phase({"P2b-ft", "FTg-rev-drive"}) == "phase_ft_groups"
    assert P.report_phase({"FTg-add-cab", "S"}) == "phase_ft_groups"
    assert P.report_phase({"P2b-ft", "S"}) == "phase_ft"

    def req(k):
        raise SystemExit(f"no {k}")
    monkeypatch.setattr(P, "require", req)
    with pytest.raises(SystemExit, match="phase_ft_groups"):
        P.cmd_ft_groups(argparse.Namespace())


def _stored_pair():
    ad = P.out_dir() / P.REAL_DIR / "answers"
    if not (ad / "P2b-ft.json").exists():
        pytest.skip("needs the stored BKS answers")
    ft = json.loads((ad / "P2b-ft.json").read_text())["answers"]
    s = json.loads((ad / "S.json").read_text())["answers"]
    key = next(k for k in ft if k.endswith("|pr12"))
    return ft[key]["A"]["settings"], s[key][P.ANY_HALF]["settings"]


def test_ftg_change_counts_only_what_can_sound():
    pytest.importorskip("numpy")
    a, s = _stored_pair()
    same = P.ftg_change(s, s, "pr12")
    assert all(not c and (m is None or m == 0) for c, m in same.values())
    off_amp = dict(s, **{"ac20Amp/ac20Cut": 0.123, "sw50rEQ/sw50rEQBand3": 0.9})          # other amps' keys
    assert not any(c for c, _ in P.ftg_change(off_amp, s, "pr12").values())
    assert s["reverb/reverbActive"] in (False, "false", 0, "0")
    assert not P.ftg_change(dict(s, **{"reverb/reverbMix": 0.9}), s, "pr12")["effects"][0]   # reverb off
    assert s["parameters/gateActive"] in (False, "false", 0, "0")
    assert not P.ftg_change(dict(s, **{"parameters/gateThreshold": -10.0}), s, "pr12")["other"][0]   # gate off
    moved = P.ftg_change(dict(s, **{"parameters/inputGain": float(s["parameters/inputGain"]) + 6.0}), s, "pr12")
    assert moved["drive"][0] and moved["drive"][1] > 0 and not moved["tone"][0]


def test_ftg_renders_and_reports_refuse_until_the_hashes_are_in_the_ledger(tmp_path, monkeypatch):
    from learn import direct_stems as DS

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    d = tmp_path / P.REAL_DIR / "answers"
    d.mkdir(parents=True)
    tag = P.ftg_tag("add", "drive")
    (d / f"{tag}.json").write_text(json.dumps({"answers": {}}))
    assert P.ftg_unhashed(["S", "P2b-ft", tag], {}) == [f"{tag}: sha256 not recorded under {P.FTG_HASHES}"]
    assert P.ftg_unhashed([tag], {P.FTG_HASHES: {tag: DS.hashlib_file(d / f"{tag}.json")}}) == []
    assert P.ftg_unhashed(["FTg-rev-cab"], {}) == ["FTg-rev-cab: no answers file"]
    monkeypatch.setattr(P, "require", lambda k: {})
    with pytest.raises(SystemExit, match="hashes"):
        P.cmd_real_render(argparse.Namespace(names=tag, shard=(0, 3)))
    with pytest.raises(SystemExit, match="hashes"):
        P.cmd_real_report(argparse.Namespace(pairs=f"{tag}:S", label="t", within=""))
