"""Step 2, the preset ladder (docs/preset-ladder-plan.md): learn/preset_ladder.py's pure parts."""
import math
import re

import pytest

from learn import preset_ladder as L  # noqa: E402


# --- the rows -----------------------------------------------------------------------------------------------------------

def test_rows_carry_their_stage_kind_and_input_style():
    assert L.row_info("mix-drawn") == {"stage": 0, "kind": "stored", "style": "train"}
    assert L.row_info("cen")["kind"] == L.row_info("aconst")["kind"] == "constant"
    assert L.row_info("clean-kind") == {"stage": 1, "kind": "input", "style": "train"}
    assert L.row_info("mix@-3")["stage"] == 1 and L.row_info("mix@-3")["style"] == "train"
    assert L.row_info("mix@0")["stage"] == L.row_info("mix@drawn")["stage"] == 3
    assert L.row_info("xl@-3") == {"stage": 2, "kind": "input", "style": "product", "exposure": "-3", "sep": True}
    assert L.row_info("xlnoG@-3")["stage"] == 2 and L.row_info("clean@-3")["stage"] == 2
    assert "sep" not in L.row_info("clean@-3")                     # a perfect separator needs no separation
    assert L.row_info("xlmdxc@-3")["stage"] == 3 and L.row_info("full@-3")["stage"] == 3
    assert L.row_info("xl-v0")["stage"] == 2
    for bad in ("mix@-6", "xl", "stem@-3", "mix@"):
        with pytest.raises(SystemExit):
            L.row_info(bad)
    assert L.parse_rows("cen,aconst,,mix@-3") == ["cen", "aconst", "mix@-3"]


def test_exposure_tags_are_declared_ones():
    assert L.exposure_value("drawn") is None
    assert L.exposure_value("-3") == -3.0 and L.exposure_value("0") == 0.0
    with pytest.raises(SystemExit):
        L.exposure_value("-6")


def test_every_declared_pair_names_rows_or_comparators_the_report_knows():
    known = {"S", "label", "RcBG", "RcGk", "Rcs2"}
    for stage, pairs in L.STAGE_PAIRS.items():
        for a, b in pairs:
            for nm in (a, b):
                if nm not in known:
                    assert L.row_info(nm)["stage"] <= stage
    for stage, pairs in L.PRIMARY.items():
        assert set(pairs) <= set(L.STAGE_PAIRS[stage])


# --- the lenders --------------------------------------------------------------------------------------------------------

def _cands():
    C = lambda i, cls, band, sec, lv: {"i": i, "cls": cls, "band": band, "section": sec,     # noqa: E731
                                       "session": sec.split("@")[0].rsplit("/", 1)[0], "others_lufs": lv}
    return [C(1, "clean", "A", "s/A_Full/x.wav@10.0", -20.0), C(2, "clean", "A", "s/A_Full/x.wav@10.0", -25.0),
            C(3, "clean", "B", "s/B_Full/y.wav@20.0", -30.0), C(4, "clean", "B", "s/B_Full/y.wav@30.0", -60.0),
            C(5, "crunch", "A", "s/A_Full/z.wav@40.0", -18.0), C(6, "crunch", "C", "s/C_Full/w.wav@50.0", None)]


def test_the_pool_keeps_lenders_whose_other_guitars_sound_grouped_by_section():
    pool = L.lender_pool(_cands())
    assert pool == {"clean": {"s/A_Full/x.wav@10.0": [1, 2], "s/B_Full/y.wav@20.0": [3]},
                    "crunch": {"s/A_Full/z.wav@40.0": [5]}}        # -60 LUFS and None (no other guitar) are out
    with pytest.raises(SystemExit):
        L.lender_pool(_cands() + [{"i": 9, "cls": "clean", "band": "BKS", "section": "b@1.0", "session": "b",
                                   "others_lufs": -20.0}])


def test_the_lender_is_a_seeded_section_then_an_example_never_from_the_units_own_session():
    pool = L.lender_pool(_cands())
    sess = {c["section"]: c["session"] for c in _cands()}
    got = {L.draw_lender(f"u{j}", "clean", pool, sess, "elsewhere") for j in range(60)}
    assert {s for s, _ in got} == {"s/A_Full/x.wav@10.0", "s/B_Full/y.wav@20.0"}
    assert {i for _, i in got} == {1, 2, 3}
    assert L.draw_lender("u7", "clean", pool, sess, "x") == L.draw_lender("u7", "clean", pool, sess, "x")
    for j in range(30):                                            # a unit on session A's DI never lends from A
        assert L.draw_lender(f"u{j}", "clean", pool, sess, "s/A_Full")[0] == "s/B_Full/y.wav@20.0"
    with pytest.raises(SystemExit):
        L.draw_lender("u", "crunch", pool, sess, "s/A_Full")       # crunch has only session A
    assert L.session_of_di("cambridge/TheTravellingBand_Quicksand_Full/16_ElecGtr1DI.wav") == \
        "cambridge/TheTravellingBand_Quicksand_Full"


def test_the_layout_is_s0s_centred_stratum_seeded_by_the_unit():
    for j in range(50):
        lay = L.draw_layout(f"unit{j}")
        assert len(lay["target"]) == 1 and abs(lay["target"][0]) <= L.TARGET_PAN
        assert L.OTHERS_PAN[0] <= abs(lay["others"]) <= L.OTHERS_PAN[1]
    assert L.draw_layout("a") == L.draw_layout("a") and L.draw_layout("a") != L.draw_layout("b")
    assert L.backing_rng("a").random() == L.backing_rng("a").random()


def test_the_gains_set_the_declared_ratio_on_the_mid_and_keep_the_drawn_loudness():
    from learn import pretrain_set as PS

    draw = {"ratio_db": -9.0, "leak_db": 5.0, "target_lufs": -11.0, "vocals_drawn": True, "mastered": False}
    lg, lb = -20.0, -15.0
    gb, ga = L.ladder_gains(lg, lb, draw, "-3")
    assert lg - (lb + gb) == pytest.approx(-3.0)                   # the target 3 dB under everything else
    assert PS.db_sum(lg, lb + gb) + ga == pytest.approx(-11.0)     # the mix at the lender's drawn loudness
    gb0, _ = L.ladder_gains(lg, lb, draw, "drawn")
    assert lg - (lb + gb0) == pytest.approx(-9.0)
    assert draw["ratio_db"] == -9.0                                # the lender's draw is not changed


# --- the stereo mix -----------------------------------------------------------------------------------------------------

def test_a_centred_source_folds_to_itself_and_the_others_sit_on_their_side():
    np = pytest.importorskip("numpy")
    y = np.ones(8)
    l, r = L.place(y, 0.0)
    assert np.allclose((l + r) / 2, y)
    l, r = L.place(y, 0.8)
    assert r[0] > l[0] > 0


def test_the_assembly_keeps_other_guitars_apart_and_the_no_guitar_mix_drops_them_at_the_same_gains():
    np = pytest.importorskip("numpy")
    import random

    n = 16
    y = np.ones(n)
    oth = 2 * np.ones(n)
    mono = np.ones((n, 2)) * 3
    stereo = np.stack([np.ones(n) * 4, np.ones(n) * 5], 1)
    tracks = [("01_Kick.wav", mono, 1), ("05_Keys.wav", stereo, 2), ("35_ElecGtr7.wav", mono, 1)]
    lay = {"target": [0.0], "others": 1.0}
    parts = L.assemble(y, oth, tracks, {"35_ElecGtr7.wav"}, lay, random.Random(0), n)
    assert parts["pans"] == {"01_Kick.wav": 0.0, "05_Keys.wav": "stereo", "35_ElecGtr7.wav": 1.0}
    assert np.allclose(L.mid(parts["t"]), y)
    c = math.cos(math.pi / 4)                                     # a centred mono track folds as the recipe's Stems
    assert np.allclose(L.mid(parts["s"]), (3 * c + 4.5) * np.ones(n))   # the kick centred, the keys' own image
    assert np.allclose(parts["a"][0], 0) and np.all(parts["a"][1] > 0)   # the amp-track guitar with the others, hard R
    full = L.mixdown(parts, -6.0, 2.0, True)
    nog = L.mixdown(parts, -6.0, 2.0, False)
    assert np.allclose(nog["guitars"], 0) and np.any(full["guitars"] > 0)
    g_b, g_a = 10 ** (-6 / 20), 10 ** (2 / 20)
    assert np.allclose((nog["L"] + nog["R"]) / 2, (y + L.mid(parts["s"]) * g_b) * g_a)
    assert np.allclose(full["target"], nog["target"])
    assert np.allclose((full["L"] + full["R"]) / 2 - full["target"] - full["guitars"],
                       (nog["L"] + nog["R"]) / 2 - nog["target"])   # the stems are the same in both


def test_mastering_is_one_linked_gain_on_both_channels_and_the_references():
    np = pytest.importorskip("numpy")
    import random

    rng = np.random.default_rng(0)
    n = 48000
    m = {"L": rng.normal(0, 0.1, n), "R": rng.normal(0, 0.1, n), "target": rng.normal(0, 0.05, n)}
    same = L.master(m, False, random.Random(1), 48000)
    assert all(np.array_equal(same[k], m[k]) for k in m)
    got = L.master(m, True, random.Random(1), 48000)
    ratio = got["target"] / m["target"]
    assert np.allclose(got["L"][np.abs(got["L"]) < 0.89] / m["L"][np.abs(got["L"]) < 0.89],
                       ratio[np.abs(got["L"]) < 0.89])
    assert np.max(np.abs(got["L"])) <= 10 ** (-1 / 20) + 1e-12


# --- the constants ------------------------------------------------------------------------------------------------------

def test_the_labels_centre_is_the_masked_mean_the_majority_and_the_mode():
    rows = [((0.2, 0.9), (1, 1), (1.0, 0.0), (1, 1), (2, 1), (1, 1)),
            ((0.4, 0.1), (1, 0), (1.0, 1.0), (1, 1), (2, 1), (1, 0)),
            ((0.6, 0.5), (1, 0), (0.0, 1.0), (1, 0), (1, 3), (1, 0))]
    cont, sw, mics = L.centre_of(rows, 2, 2, 2, s_mics=[1, 3])
    assert cont[0] == pytest.approx(0.4) and cont[1] == pytest.approx(0.9)   # head 1 masked on rows 2 and 3
    assert sw == [pytest.approx(2 / 3), pytest.approx(0.5)]       # switch 1: 1 of 2 masked on, a tie (answered off)
    assert mics == [2, 1]
    cont, sw, mics = L.centre_of([((0.1,), (0,), (1.0,), (0,), (0,), (0,))], 1, 1, 1)
    assert math.isnan(cont[0]) and sw == [None] and mics == [None]   # nothing labels it: S's value stays


def test_a_mic_tie_goes_to_ss_mic_when_among_the_tied_else_the_lowest():
    rows = [((), (), (), (), (4,), (1,)), ((), (), (), (), (2,), (1,))]
    assert L.centre_of(rows, 0, 0, 1, s_mics=[4])[2] == [4]
    assert L.centre_of(rows, 0, 0, 1, s_mics=[0])[2] == [2]
    assert L.centre_of(rows, 0, 0, 1)[2] == [2]


def test_the_models_own_constant_averages_its_answers_and_votes_its_switches():
    outs = [([0.1, 0.5], [0.9], [1]), ([0.3, 0.5], [0.2], [1]), ([0.5, 0.2], [0.7], [0])]
    cont, sw, mics = L.answers_centre(outs, 2, 1, 1)
    assert cont == [pytest.approx(0.3), pytest.approx(0.4)]
    assert sw == [pytest.approx(2 / 3)] and mics == [1]


def test_showings_count_a_cycled_list():
    recs = [{"unit": "a", "amp": "x"}, {"unit": "b", "amp": "x"}, {"unit": "a", "amp": "x"}]
    assert L.showing_counts(recs) == {("a", "x"): 2, ("b", "x"): 1}


# --- the subset ---------------------------------------------------------------------------------------------------------

def test_the_subset_keeps_bks_and_the_panel_whole_and_balances_goat_and_cap1_by_fold_and_class():
    us = [{"set": "bks", "unit": f"b{j}", "fold": j % 4, "cls": "clean", "item": None, "creator": None}
          for j in range(5)]
    us += [{"set": "panel", "unit": "p0", "fold": 0, "cls": "crunch", "item": None, "creator": None}]
    for f in range(4):
        for j in range(20):                                   # 10 items, two units each, both classes
            us.append({"set": "goat", "unit": f"g{f}-{j}", "fold": f, "cls": ("clean", "crunch")[j % 2],
                       "item": f"i{f}-{j // 2}", "creator": None})
        for j in range(24):                                   # 4 creators, 6 units each
            us.append({"set": "cap1", "unit": f"c{f}-{j}", "fold": f, "cls": ("clean", "crunch")[j % 2],
                       "item": None, "creator": f"cr{f}-{j % 4}"})
    got = set(L.subset_draw(us))
    assert {f"b{j}" for j in range(5)} | {"p0"} <= got
    by = {u["unit"]: u for u in us}
    for f in range(4):
        g = [by[u] for u in got if by[u]["set"] == "goat" and by[u]["fold"] == f]
        assert sorted(u["cls"] for u in g) == ["clean"] * 5 + ["crunch"] * 5 or \
            sum(u["cls"] == "clean" for u in g) <= 6
        assert len({u["item"] for u in g}) == len(g)            # one a GOAT item
        c = [by[u] for u in got if by[u]["set"] == "cap1" and by[u]["fold"] == f]
        assert sum(u["cls"] == "clean" for u in c) == 6 and sum(u["cls"] == "crunch" for u in c) == 6
        per = {}
        for u in c:
            per[u["creator"]] = per.get(u["creator"], 0) + 1
        assert max(per.values()) <= L.SUBSET_CAP1_PER_CREATOR
    assert L.subset_draw(us) == L.subset_draw(list(reversed(us)))   # seeded, order-free


# --- the reads ----------------------------------------------------------------------------------------------------------

def test_ratio_bins_follow_the_planners_edges():
    assert L.ratio_bin(-13.0) == "under -12 dB"
    assert L.ratio_bin(-12.0) == L.ratio_bin(-6.5) == "-12 to -6 dB"
    assert L.ratio_bin(-6.0) == L.ratio_bin(1.0) == "-6 dB and over"
    assert L.ratio_bin(None) is None


def test_the_gap_share_is_the_rows_mean_over_the_labels_on_shared_directions():
    row = {"a": -0.1, "b": -0.3, "c": 5.0}
    lab = {"a": -0.4, "b": -0.4}
    share, n = L.gap_share(row, lab)
    assert n == 2 and share == pytest.approx(0.5)
    assert L.gap_share(row, {}) == (None, 0)


def test_within_cell_demeans_and_drops_single_value_cells():
    got = L.within_cell([("c1", "u1", 1.0), ("c1", "u2", 3.0), ("c2", "u3", 5.0)])
    assert got == {"u1": -1.0, "u2": 1.0}
    assert L.corr([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0) and L.corr([1, 1, 1], [1, 2, 3]) is None
    assert L.slope([0, 1, 2], [1, 3, 5]) == pytest.approx(2.0) and L.slope([1, 2], [1, 2]) is None


def test_decided_reads_the_interval_only():
    assert L.decided({"lo90": -0.2, "hi90": -0.01}) == "better"
    assert L.decided({"lo90": 0.01, "hi90": 0.2}) == "worse"
    assert L.decided({"lo90": -0.1, "hi90": 0.1}) == "undecided"
    assert L.decided(None) is None and L.decided({"lo90": None, "hi90": None}) is None


# --- the machine --------------------------------------------------------------------------------------------------------

def test_renders_and_separations_are_registered_with_the_cap():
    from learn import local_objective as LO

    py = "/x/.venv/bin/python"
    assert any(re.search(p, f"{py} -u -m learn.preset_ladder render --rows cen --shard 0/3") for p in LO.RENDERS)
    assert any(re.search(p, f"{py} -u -m learn.preset_ladder replay") for p in LO.RENDERS)
    for cmd in ("report --stage 1", "build --rows mix@-3", "predict --rows mix@-3", "stage0", "lends"):
        assert not any(re.search(p, f"{py} -m learn.preset_ladder {cmd}") for p in LO.RENDERS)
    assert any(re.search(p, f"{py} -u -m learn.preset_ladder sep --rows xl@-3") for p in LO.SEPARATIONS)
    assert not any(re.search(p, f"{py} -m learn.preset_ladder render --rows cen") for p in LO.SEPARATIONS)


def test_the_module_imports_without_numpy_at_its_top():
    import ast
    import pathlib

    src = pathlib.Path(L.__file__).read_text()
    top = [n for n in ast.parse(src).body if isinstance(n, (ast.Import, ast.ImportFrom))]
    names = {a.name for n in top for a in n.names} | {getattr(n, "module", None) for n in top}
    assert not names & {"numpy", "torch", "scipy", "soundfile"}
