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
    lags = {"a": 60, "b": 91, "c": 49, "d": 140, "e": None}       # offsets 50, 51, 49, 115, none
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
