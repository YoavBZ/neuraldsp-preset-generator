"""C3r (docs/full-controls-plan.md, "C2r and C3r in detail"): learn/full_controls_c3r.py's pure parts."""
import re

import pytest

pytest.importorskip("numpy")

from learn import full_controls_c3r as R3  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import pipeline_fix as P  # noqa: E402


# --- the folds ---------------------------------------------------------------------------------------------------------

def test_panel_band_folds_are_largest_first_by_name_to_the_emptiest_fold():
    counts = {"Jen Hartswick & Nick Cassarino": 5, "The Laminar Flow": 4, "Aimee Norwich": 3, "Port St Willow": 3,
              "Blue Manic": 2, "Big Troubles": 1}
    got = R3.band_folds(counts)
    assert got == {"Jen Hartswick & Nick Cassarino": 0, "The Laminar Flow": 1, "Aimee Norwich": 2,
                   "Port St Willow": 3, "Blue Manic": 2, "Big Troubles": 3}
    assert [sum(n for b, n in counts.items() if got[b] == f) for f in range(4)] == [5, 4, 5, 4]


def test_n12_creators_shared_with_batch_1_take_batch_1s_fold():
    fold1 = R3.batch1_creator_folds([{"creator": "a", "fold": 2}, {"creator": "a", "fold": 2}, {"creator": "b",
                                                                                                "fold": 0}])
    got = R3.creator_folds([{"unit": "u", "creator": "a", "fold": 3}, {"unit": "v", "creator": "c", "fold": 1}], fold1)
    assert got == {"u": 2, "v": 1}
    with pytest.raises(SystemExit):
        R3.batch1_creator_folds([{"creator": "a", "fold": 0}, {"creator": "a", "fold": 1}])


# --- the drops ----------------------------------------------------------------------------------------------------------

def _ents():
    E = R3.entry
    es = [E("bks", "b0", 0, "bd0"), E("bks", "b1", 1, "bd1"), E("goat", "g0", 0, "gi0"), E("goat", "g2", 2, "gi2"),
          E("goat", "g3", 3, "gi3"),
          E("cap1", "c1", 1, "gi0", creator="cr1"),          # a capture on GOAT fold 0's DI, in creator fold 1
          E("cap1", "c2", 2, "gi9", creator="cr2"),
          E("n12", "n0", 0, "lib1", creator="k0"),          # n12's own folds: lib1 straddles folds 0 and 1
          E("n12", "n1", 1, "lib1", creator="k1"),
          E("n12", "n3", 3, "lib3", creator="cr2"),         # creator cr2 also in fold 2 (cap1): straddles
          E("panel", "p2", 2, "pd2", band="B")]
    for e in es:
        e["n"] = 3 if e["set"] == "bks" else 1
    return es


def test_model_k_drops_every_row_sharing_a_di_or_creator_with_fold_k_its_own_set_included():
    tr, held, dr = R3.split(_ents(), 0, False, "all")
    names = lambda xs: sorted(e["unit"] for e in xs)  # noqa: E731
    assert names(held) == ["b0", "g0", "n0"]
    assert names(dr) == ["c1", "n1"]                    # c1 on g0's DI; n1 on n0's DI (within n12)
    assert names(tr) == ["b1", "c2", "g2", "g3", "n3", "p2"]
    tr, held, dr = R3.split(_ents(), 2, False, "all")
    assert names(held) == ["c2", "g2", "p2"] and names(dr) == ["n3"]   # n3 shares creator cr2 with c2


def test_inner_run_k_leaves_out_folds_k_and_j_and_everything_sharing_either():
    tr, held, dr = R3.split(_ents(), 3, True, "all")    # k 3, j 0
    names = lambda xs: sorted(e["unit"] for e in xs)  # noqa: E731
    assert names(held) == ["b0", "g0", "n0"]
    assert "n3" not in names(tr) and "g3" not in names(tr)
    assert names(dr) == ["c1", "c2", "n1"] and names(tr) == ["b1", "g2", "p2"]   # c2 shares creator cr2 with n3 (k)


def test_r_ctl_trains_on_bks_and_goat_only_and_holds_what_r_all_holds():
    for k in range(4):
        for inner in (False, True):
            ta, ha, _ = R3.split(_ents(), k, inner, "all")
            tc, hc, _ = R3.split(_ents(), k, inner, "ctl")
            assert [e["unit"] for e in ha] == [e["unit"] for e in hc]
            assert {e["set"] for e in tc} <= {"bks", "goat"}
            assert [e["unit"] for e in tc] == [e["unit"] for e in ta if e["set"] in ("bks", "goat")]


def test_the_all_labels_model_takes_every_row_and_holds_none():
    tr, held, dr = R3.split(_ents(), None, False, "all")
    assert len(tr) == len(_ents()) and held == [] and dr == []
    with pytest.raises(SystemExit):
        R3.split(_ents(), None, True, "all")


def test_a_read_only_unit_holds_its_identity_out_but_trains_no_row():
    es = _ents() + [R3.entry("goat", "g9", 0, "lib3", row=False)]
    tr, held, dr = R3.split(es, 0, False, "all")
    assert "n3" in [e["unit"] for e in dr] and "g9" not in [e["unit"] for e in held + tr]


def test_drop_counts_count_records_and_units():
    dc = R3.drop_counts(_ents(), "all")
    c = dc["FT_k0"]
    assert c["held"]["bks"] == 3 and c["held"]["all"] == 5 and c["units"]["held"] == 3
    assert c["dropped"]["cap1"] == 1 and c["dropped"]["n12"] == 1 and c["train"]["bks"] == 3
    assert set(dc) == {f"{t}_k{k}" for t in ("FT", "inner") for k in range(4)}


def test_check_rows_names_a_leak():
    st = {"entries": _ents()}
    ok = [{"real": u} for u in ("b1", "g2")]
    assert R3.check_rows("all", 0, False, ok, [{"real": "g0"}], st) == []
    bad = R3.check_rows("all", 0, False, ok + [{"real": "c1"}], [{"real": "g2"}], st)
    assert any("sharing" in b for b in bad) and any("outside fold" in b for b in bad)
    assert any("new row in R-ctl" in b for b in R3.check_rows("ctl", 0, False, [{"real": "c2"}], [], st))


# --- sources, the lift, players -----------------------------------------------------------------------------------------

def test_new_sources_fall_back_as_declared():
    assert R3.new_source("cap1", {"label": {"a": 1}, "searched_keys": ["m/k"]}, None) == {
        "kind": "c2", "label": {"a": 1}, "searched": ["m/k"]}
    assert R3.new_source("cap1", {"label": None}, {"label": {"s": 1}}) == {"kind": "stored", "label": {"s": 1}}
    assert R3.new_source("panel", {"label": None}, None, step0_label={"z": 1}) == {"kind": "stored", "label": {"z": 1}}
    assert R3.new_source("panel", {"label": None}, None, step0_label=None) is None
    got = R3.new_source("n12", {"label": None}, {"label": {"v2": 1}}, c1b=None, c1a={})
    assert got == {"kind": "stored", "label": {"v2": 1}}
    with pytest.raises(SystemExit):
        R3.new_source("cap1", None, None)


def test_n12s_measurement_only_is_lifted_explicitly_and_the_check_stays():
    assert R3.lift_measurement_only({"set": "n12", "measurement_only": True}, "k") == "k"
    for bad in ({"set": "n12", "measurement_only": False}, {"set": "bks", "measurement_only": True}, {"set": "n12"}):
        with pytest.raises(SystemExit):
            R3.lift_measurement_only(bad, "k")


def test_players_name_the_dis_band_the_way_goat_does():
    assert R3.player_of("cap1", {"player": "player1"}) == R3.player_of("goat", {"band": "GOAT player1"})
    assert R3.player_of("n12", {"player": "Ale Lak"}) == "Ale Lak"
    assert R3.player_of("panel", {"band": "Blue Manic"}) == "Blue Manic"


def test_each_source_is_cycled_to_at_least_300_and_a_longer_list_kept_whole():
    assert len(R3.cycled_to(list(range(7)))) == 300 and R3.cycled_to(list(range(301))) == list(range(301))


# --- the pools and the rule ----------------------------------------------------------------------------------------------

def _row(mean, half=0.01, clusters=20):
    return {"mean": mean, "lo90": mean - half, "hi90": mean + half, "clusters": clusters}


def test_pooled_weights_the_sets_equally():
    p = R3.pooled({"a": _row(0.0), "b": _row(0.3)})
    assert p["mean"] == pytest.approx(0.15) and p["lo90"] < 0.15 < p["hi90"] and p["sets"] == 2
    assert R3.pooled({"a": _row(0.0), "b": {"mean": None}}) is None


def test_adoption_is_vetoed_by_the_deciding_pool_or_bks_goat_or_the_panel_never_by_cap1_or_n12():
    good = {s: _row(-0.02) for s in R3.SETS}
    a = R3.adoption(good)
    assert a["replaces_c3"] and a["complete"] and a["five_set_pool"]["sets"] == 5 and a["deciding_pool"]["sets"] == 3
    for s in ("bks", "goat", "panel"):
        assert not R3.adoption(dict(good, **{s: _row(0.05)}))["replaces_c3"]
    for s in ("cap1", "n12"):
        assert R3.adoption(dict(good, **{s: _row(0.05)}))["replaces_c3"]
    undecided = dict(good, bks=_row(0.005), goat=_row(0.005), panel=_row(0.005))
    assert R3.adoption(undecided)["replaces_c3"]                                     # kept unless shown worse


def test_the_read_render_is_a_render_command_and_the_rest_are_not():
    assert any(re.search(p, "python -u -m learn.full_controls_c3r c3r-render --shard 0/3") for p in LO.RENDERS)
    for cmd in ("c3r-folds", "c3r-check", "c3r-predict", "c3r-report"):
        assert not any(re.search(p, f"python -m learn.full_controls_c3r {cmd}") for p in LO.RENDERS)


# --- on the stored data (zero renders; skipped where the data is not on this machine) ---------------------------------

def test_the_final_folds_drop_what_the_review_counted():
    if not (P.out_dir() / "c2" / "records.json").exists():
        pytest.skip("no stored data")
    st = R3.state(partial=True)
    dc = R3.drop_counts(st["entries"], "all")
    ft = [dc[f"FT_k{k}"] for k in range(4)]
    assert [c["dropped"]["goat"] for c in ft] == [36, 36, 35, 30]
    assert [c["dropped"]["cap1"] for c in ft] == [34, 46, 30, 31]
    assert [c["dropped"]["n12"] for c in ft] == [7, 2, 3, 7]
    assert [c["dropped"]["bks"] for c in ft] == [0, 0, 0, 0] and [c["dropped"]["panel"] for c in ft] == [0, 0, 0, 0]
    assert min(c["train"]["all"] for c in ft) == 415 and max(c["train"]["all"] for c in ft) == 507
    rows = {s: sum(e["n"] for e in st["entries"] if e["set"] == s and e["row"]) for s in R3.SETS}
    assert rows == {"bks": 306, "goat": 214, "cap1": 121, "n12": 31, "panel": 18} and sum(rows.values()) == 690
    assert st["band_folds"] == {"Jen Hartswick & Nick Cassarino": 0, "The Laminar Flow": 1, "Aimee Norwich": 2,
                                "Port St Willow": 3, "Blue Manic": 2, "Big Troubles": 3}
    assert len(st["measurement_only_lifted"]["records"]) == 31


# --- the read's rows ---------------------------------------------------------------------------------------------------

def test_half_value_reads_a_direction_or_an_any_half_answer_and_refuses_non_finite():
    assert R3.half_value({"A": {"B": 2.0}}, "A", "B") == 2.0
    assert R3.half_value({P.ANY_HALF: {"A": 1.5, "B": 2.5}}, "B", "A") == 1.5
    assert R3.half_value({"A": {"B": float("inf")}}, "A", "B") is None and R3.half_value(None, "A", "B") is None


def test_pair_rows_take_both_directions_a_set_judges_finite():
    import math
    units = [{"set": "cap1", "unit": "u", "amp": "pr12", "cluster": "cr"}, {"set": "goat", "unit": "g", "amp": "pr12",
                                                                             "cluster": "i"}]
    a = lambda ru, sh, h: 2.0 if sh == "A" else None    # noqa: E731
    b = lambda ru, sh, h: 1.0                           # noqa: E731
    rows, missing = R3.pair_rows({}, units, a, b, "cap1")
    assert rows == [("cr", "u|pr12", math.log(2.0))] and missing == 1


def test_w_di_units_are_read_apart_only_in_the_new_sets():
    units = [{"set": "bks", "unit": "b", "prt": {"di": "w1"}}, {"set": "n12", "unit": "n", "prt": {"di": "w1"}},
             {"set": "goat", "unit": "g", "prt": {"di": "x"}}]
    wd = {"w1"}
    assert not R3._apart(("c", "b|pr12", 0.0), units, wd)
    assert R3._apart(("c", "n|pr12", 0.0), units, wd)
    assert not R3._apart(("c", "g|pr12", 0.0), units, wd)                    # real_out stays in the main rows


# --- the source mix and an incomplete read (the code review) ------------------------------------------------------------

def test_each_sets_showings_match_its_share_of_the_source_within_one_row_whatever_the_order():
    import itertools
    for sizes in ((121, 52, 18), (130, 59, 21), (219, 13), (5, 3), (282, 14), (1, 1, 1), (200, 99, 1)):
        recs = [{"set": f"s{i}", "unit": f"s{i}/{j}"} for i, n in enumerate(sizes) for j in range(n)]
        for perm in itertools.permutations(range(len(sizes))):
            order = [r for i in perm for r in recs if r["set"] == f"s{i}"]
            got = R3.showings(R3.mixed(order, R3.mix_seed("all", 0, False, "captures")))
            tot = sum(got.values())
            assert tot == max(300, len(recs))
            for i, n in enumerate(sizes):
                assert abs(got[f"s{i}"] - tot * n / len(recs)) <= 1, (sizes, perm, i)


def test_the_mix_is_seeded_per_run_and_source_and_keeps_every_record():
    recs = [{"set": s, "unit": f"{s}/{j}"} for s in ("goat", "cap1") for j in range(20)]
    a = R3.mixed(recs, R3.mix_seed("all", 0, False, "captures"))
    assert a == R3.mixed(recs, R3.mix_seed("all", 0, False, "captures"))
    assert a != R3.mixed(recs, R3.mix_seed("all", 1, False, "captures"))
    assert sorted(r["unit"] for r in a) == sorted(r["unit"] for r in recs)
    one = [r for r in recs if r["set"] == "goat"]                              # one set: a seeded shuffle alone
    assert sorted(r["unit"] for r in R3.mixed(one, "x")) == sorted(r["unit"] for r in one)


def test_adoption_does_not_decide_on_an_incomplete_read():
    good = {s: _row(-0.02) for s in R3.SETS}
    for bad in ({"mean": None}, {"mean": -0.1, "lo90": None, "hi90": None, "clusters": 1}, _row(-0.1, clusters=1)):
        for s in ("bks", "goat", "panel"):
            a = R3.adoption(dict(good, **{s: bad}))
            assert a["replaces_c3"] is None and not a["complete"] and s in a["why"]
    a = R3.adoption(dict(good, cap1={"mean": None}))                            # a non-deciding set: still decided
    assert a["replaces_c3"] is True and a["five_set_pool"] is None and a["why"] is None


def test_c3s_n12_scores_are_refused_clearly_when_their_side_read_is_missing(tmp_path, monkeypatch):
    from learn import score_ear as SE
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    assert "no N12 scores for C3-ftm" in R3.c3_n12_refusal("C3-ftm")
    d = SE.wide_dir() / SE.H4_DIR / "C3-ftm"
    d.mkdir(parents=True)
    (d / "x.json").write_text("{}")
    assert R3.c3_n12_refusal("C3-ftm") is None
    assert "P2b-ftm" in R3.c3_n12_refusal(P.FTM_BASE)


# --- Amendment 1, the DI scope ----------------------------------------------------------------------------------------

def test_the_scope_takes_library_units_on_dropped_dis_out_after_the_folds_are_dealt():
    ents = _ents()
    src = {(e["unit"], "pr12"): {"kind": "c2"} for e in ents}
    rec = {(e["unit"], "pr12"): e["set"] for e in ents}
    e2, s2, r2, out = R3.scope_drop(ents, src, rec, frozenset({"lib1", "pd2", "gi0"}))
    assert out == {"n12": ["n0", "n1"], "panel": ["p2"]}                              # GOAT's gi0 is not checked
    assert {e["unit"] for e in e2} == {e["unit"] for e in ents} - {"n0", "n1", "p2"}
    assert all(e["fold"] == f["fold"] for e in e2 for f in ents if f["unit"] == e["unit"])   # no re-deal
    assert ("n0", "pr12") not in s2 and ("n0", "pr12") not in r2 and ("c1", "pr12") in s2


def test_with_no_panel_unit_left_bks_and_goat_decide():
    assert R3.deciding_sets(8) == ("bks", "goat", "panel") and R3.deciding_sets(0) == ("bks", "goat")
    rows = {s: _row(-0.02) for s in R3.SETS}
    rows["panel"] = {"mean": None}
    a = R3.adoption(rows, R3.deciding_sets(0))
    assert a["replaces_c3"] is True and a["deciding_pool"]["sets"] == 2 and a["deciding_sets"] == ["bks", "goat"]
    assert R3.adoption(rows)["replaces_c3"] is None                                  # the three-set rule would wait


# --- the review's guards: the panel's DI threshold and stale scope_out records ------------------------------------------

def test_the_panel_decides_only_with_three_di_files_left():
    assert R3.deciding_sets(1) == ("bks", "goat") and R3.deciding_sets(2) == ("bks", "goat")
    assert R3.deciding_sets(3) == ("bks", "goat", "panel") and R3.deciding_sets(8) == ("bks", "goat", "panel")


def test_seven_of_eight_panel_dis_dropped_still_decide_on_bks_and_goat():
    rows = {s: _row(-0.02) for s in R3.SETS}
    rows["panel"] = {"mean": -0.05, "lo90": None, "hi90": None, "clusters": 1}           # one DI file: no interval
    a = R3.adoption(rows, R3.deciding_sets(1))
    assert a["replaces_c3"] is True and a["why"] is None and "panel" not in a["shown_worse"]
    rows["panel"] = _row(0.3, half=0.1, clusters=2)                                    # 2 files: reported, no veto
    assert R3.adoption(rows, R3.deciding_sets(2))["replaces_c3"] is True


def test_a_scope_out_record_whose_di_is_kept_is_stale():
    recs = [{"key": "a", "set": "n12"}, {"key": "b", "set": "panel"}, {"key": "c", "set": "n12"}]
    outs = {"a": {"label": None, "scope_out": {"di": "lib/1"}}, "b": {"label": None, "scope_out": {"di": "lib/2"}},
            "c": {"label": {"x": 1}}}
    assert R3.stale_scope_out(recs, outs, frozenset({"lib/2"})) == ["a"]
    assert R3.stale_scope_out(recs, outs, frozenset({"lib/1", "lib/2"})) == []


def test_c3r_refuses_while_a_scope_out_records_di_is_kept(tmp_path, monkeypatch):
    import json

    from learn import di_scope as DS
    from learn import full_controls_c2 as C2
    from learn import full_controls_c2r as R
    from learn import full_controls_c3 as C3
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(C3, "N_C2", 1)
    c2 = [{"set": "goat", "block": "goat", "key": "goat/u|pr12", "unit": "goat/u", "amp": "pr12"}]
    (tmp_path / "c2").mkdir()
    (tmp_path / "c2" / "records.json").write_text(json.dumps({"records": c2}))
    C2.out_path(c2[0]).parent.mkdir(parents=True)
    C2.out_path(c2[0]).write_text(json.dumps({"label": {"a/b": "1"}}))
    c2r = [{"set": "n12", "block": "n12", "key": "cap/n#ac20|ac20", "unit": "cap/n#ac20", "amp": "ac20",
            "c1a_output": str(tmp_path / "c1a.json")}]
    (tmp_path / "c1a.json").write_text(json.dumps({"set": "n12", "measurement_only": True}))
    (tmp_path / "c2r").mkdir()
    (tmp_path / "c2r" / "records.json").write_text(json.dumps({"records": c2r}))
    R.out_path(c2r[0]).parent.mkdir(parents=True)
    R.out_path(c2r[0]).write_text(json.dumps({"label": None, "scope_out": {"build": DS.BUILD, "di": "lib/1",
                                                                            "verdict": "heavy"}}))
    (tmp_path / "c3").mkdir()
    (tmp_path / "c3" / "decision.json").write_text(json.dumps({"replaces_ftm": True, "tag": "C3-ftm"}))
    (tmp_path / DS.DIR).mkdir()
    (tmp_path / DS.DIR / "verdicts.json").write_text(json.dumps(
        {"build": DS.BUILD, "verdicts": {"lib/1": "keep", **{f"x{i}": "keep" for i in range(DS.N_CARDS - 1)}}}))
    R3._CACHE.clear()
    with pytest.raises(SystemExit, match="move each aside"):
        R3.state()
    R3._CACHE.clear()
