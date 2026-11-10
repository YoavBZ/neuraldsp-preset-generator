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
    assert not R3._apart(("c", "b|pr12", 0.0), units, wd, set())
    assert R3._apart(("c", "n|pr12", 0.0), units, wd, set())
    assert R3._apart(("c", "g|pr12", 0.0), units, wd, {"g"})
