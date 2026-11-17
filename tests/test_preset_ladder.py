"""Step 2, the preset ladder (docs/preset-ladder-plan.md): learn/preset_ladder.py's pure parts."""
import math
import re

import pytest

from learn import preset_ladder as L  # noqa: E402


# --- the rows -----------------------------------------------------------------------------------------------------------

def test_rows_carry_their_stage_kind_and_input_style():
    assert L.row_info("mix-drawn") == {"stage": 0, "kind": "stored", "style": "train"}
    assert L.row_info("cen")["kind"] == L.row_info("aconst")["kind"] == "constant"
    assert L.row_info("clean-kind") == {"stage": 1, "kind": "input", "style": "train", "built_by": "clean-kind"}
    assert L.row_info("mix@-3")["stage"] == 1 and L.row_info("mix@-3")["style"] == "train"
    assert L.row_info("mix@0")["stage"] == 3
    assert L.row_info("mix@drawn")["stage"] == 2                  # stage 2 under Q1's outcome 4, else stage 3's subset
    assert L.row_info("xl@-3") == {"stage": 2, "kind": "input", "style": "product", "exposure": "-3", "sep": True}
    assert L.row_info("xlnoG@-3")["stage"] == 2 and L.row_info("clean@-3")["stage"] == 2
    assert "sep" not in L.row_info("clean@-3")                     # a perfect separator needs no separation
    assert L.row_info("mixp@-3") == {"stage": 2, "kind": "input", "style": "product", "exposure": "-3",
                                     "built_by": "mix@-3"}         # the level step alone, built beside mix@-3
    for r in ("full@-3", "clean@-3", "mixp@-3"):
        assert L.row_info(r)["built_by"] == "mix@-3"
    assert L.row_info("xlmdxc@-3")["stage"] == 3 and L.row_info("full@-3")["stage"] == 3
    assert L.row_info("xl-v0") == {"stage": 0, "kind": "input", "style": "product", "render": False}
    for bad in ("mix@-6", "xl", "stem@-3", "mix@", "sic-cen", "sic-xlnoG@-3"):
        with pytest.raises(SystemExit):
            L.row_info(bad)
    assert L.parse_rows("cen,aconst,,mix@-3") == ["cen", "aconst", "mix@-3"]


def test_same_input_constants_are_rendered_in_their_inputs_stage():
    assert L.row_info("sic-mix-drawn") == {"stage": 1, "kind": "constant", "style": None, "base": "mix-drawn"}
    assert L.row_info("sic-clean-kind")["stage"] == L.row_info("sic-mix@-3")["stage"] == 1
    assert L.row_info("sic-xl@-3")["stage"] == L.row_info("sic-mix@drawn")["stage"] == 2
    for a, b in L.OUTCOME4_PAIRS:
        assert L.row_info(a)["stage"] <= 2 and (b in ("cen", "mix-drawn") or L.row_info(b)["stage"] <= 2)


def test_the_same_input_pool_is_the_parts_own_fold_with_no_shared_cluster_di_or_creator():
    P_ = lambda k, f, amp, cls, cl, ids: {"key": k, "fold": f, "amp": amp, "cls": cls, "cluster": cl,   # noqa: E731
                                          "ids": set(ids)}
    parts = [P_("a", 0, "sw50r", "clean", "goat|i1", {("di", "goat/i1")}),
             P_("b", 0, "sw50r", "clean", "goat|i1", {("di", "goat/i1")}),          # the same cluster
             P_("c", 0, "sw50r", "clean", "cap1|cr", {("di", "goat/i1"), ("creator", "cr")}),   # the same DI file
             P_("d", 0, "sw50r", "clean", "goat|i2", {("di", "goat/i2")}),
             P_("e", 0, "pr12", "clean", "goat|i3", {("di", "goat/i3")}),           # another amp
             P_("f", 0, "sw50r", "crunch", "goat|i4", {("di", "goat/i4")}),         # another class
             P_("g", 0, "sw50r", "clean", "bks|x", {("di", "x.wav")}),
             P_("h", 1, "sw50r", "clean", "goat|i5", {("di", "goat/i5")})]          # another fold's model
    assert [q["key"] for q in L.sic_pool(parts, parts[0])] == ["d", "g"]
    n = [P_("n", 0, "sw50r", "clean", "n12|cr", {("di", "lib.wav"), ("creator", "cr")}),
         P_("m", 0, "sw50r", "clean", "cap1|cr", {("di", "goat/i9"), ("creator", "cr")}),    # the same creator
         P_("o", 0, "sw50r", "clean", "cap1|zz", {("di", "goat/i8"), ("creator", "zz")})]
    assert [q["key"] for q in L.sic_pool(n, n[0])] == ["o"]


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


# --- the controls and the outputs' shapes -------------------------------------------------------------------------------

def test_a_command_refuses_until_its_stages_controls_passed_on_todays_state():
    ok = {"ok": True, "c3r_sha256": "s"}
    assert L.guarding(0) == ["check0"] and L.guarding(1) == ["check0", "check1", "replay"]
    assert L.guarding(2) == L.guarding(1)
    assert L.control_refusal(["check0"], "s", {"check0": ok}) is None
    assert "has not run" in L.control_refusal(["check0"], "s", {})
    assert "failed" in L.control_refusal(["check0"], "s", {"check0": {"ok": False, "c3r_sha256": "s"}})
    assert "another C3r state" in L.control_refusal(["check0"], "t", {"check0": ok})
    assert "replay" in L.control_refusal(L.guarding(1), "s", {"check0": ok, "check1": ok})


def _centres():
    x = {"select": 1, "settings": {"parameters/inputGain": "-3"}}      # select: the pipeline's int, as C3r's
    return {t: {a: {c: x for c in ("clean", "crunch")} for a in ("pr12", "sw50r", "ac20")} for t in ("cen", "aconst")}


def test_centres_json_keeps_the_shape_step_1_reads():
    doc = L.centres_doc(_centres(), hold="C3-cabS", model_sha256=["a", "b"])
    assert set(doc["centres"]) == {"cen", "aconst"} and doc["hold"] == "C3-cabS" and doc["model_sha256"] == ["a", "b"]
    assert doc["centres"]["cen"]["sw50r"]["clean"] == {"select": 1, "settings": {"parameters/inputGain": "-3"}}
    bad = _centres()
    del bad["aconst"]["ac20"]["crunch"]
    with pytest.raises(SystemExit):
        L.centres_doc(bad, hold="C3-cabS", model_sha256=["a"])
    bad = _centres()
    bad["cen"]["pr12"]["clean"] = {"select": "x", "settings": {"inputGain": "0"}}   # not "module/key"
    with pytest.raises(SystemExit):
        L.centres_doc(bad, hold="C3-cabS", model_sha256=["a"])
    with pytest.raises(SystemExit):
        L.centres_doc(dict(_centres(), extra={}), hold="C3-cabS", model_sha256=["a"])
    with pytest.raises(SystemExit):
        L.centres_doc(_centres(), hold="C3-cabS")                     # no model_sha256
    for bad_sel in ("1", True, None):
        bad = _centres()
        bad["aconst"]["sw50r"]["crunch"] = {"select": bad_sel, "settings": {"parameters/inputGain": "0"}}
        with pytest.raises(SystemExit):
            L.centres_doc(bad, hold="C3-cabS", model_sha256=["a"])


def test_a_failed_control_record_is_never_overwritten():
    assert L.overwrite_refusal(None) is None and L.overwrite_refusal({"ok": True}) is None
    assert "amendment" in L.overwrite_refusal({"ok": False})


def test_a_separation_waits_for_renders_and_any_mps_user():
    ps = [(1, "/x/python -m learn.preset_ladder sep --rows xl@-3 --device mps"), (2, "au_render_server x"),
          (3, "/x/python -m learn.other render"), (4, "/x/python train.py --device mps")]
    rend = lambda ps_, own: [p for p, c in ps_ if p not in own and "render" in c and "au_" not in c]   # noqa: E731
    mps = lambda ps_, own: [p for p, c in ps_ if p not in own and "--device mps" in c]               # noqa: E731
    why = L.sep_blockers(ps, {1}, rend, mps)
    assert len(why) == 2 and "[3]" in why[0] and "[2]" in why[0] and "[4]" in why[1]
    assert L.sep_blockers(ps[:1], {1}, rend, mps) == []
    cpu = L.sep_blockers(ps, {1}, rend, None)                     # on the CPU the renders still block, the MPS doesn't
    assert len(cpu) == 1 and "renders" in cpu[0]


# --- the outcome rules --------------------------------------------------------------------------------------------------

def _rows(better=(), worse=(), set_better=()):
    """Report rows: every named row 'better' or 'worse' on the deciding pool, the rest undecided; set_better: (row, set)."""
    names = {f"{a} - {b}" for a, b in L.STAGE_PAIRS[1] + L.STAGE_PAIRS[2]}
    iv = lambda r: ({"mean": -0.1, "lo90": -0.2, "hi90": -0.01} if r == "b" else      # noqa: E731
                    {"mean": 0.1, "lo90": 0.01, "hi90": 0.2} if r == "w" else {"mean": 0.0, "lo90": -0.1, "hi90": 0.1})
    out = {}
    for n in names:
        r = "b" if n in better else "w" if n in worse else "u"
        out[n] = {"deciding_pool": iv(r), **{s: iv("b" if (n, s) in set_better else "u") for s in ("bks", "goat", "panel")}}
    return out


def test_q1s_outcome_needs_a_per_unit_reading_to_call_it_reading():
    dec = ("bks", "goat", "panel")
    q = L.q1_outcome(_rows(better={"mix@-3 - sic-mix@-3"}), dec)
    assert q["outcome"] == "reads in the exposed backed mix"
    q = L.q1_outcome(_rows(better={"mix@-3 - cen", "aconst - cen"}), dec)       # a better constant, not reading
    assert q["outcome"] == "a better constant, no per-unit reading" and q["constant_for_steps_1_and_3"] == "Aconst"
    assert L.q1_outcome(_rows(better={"clean-kind - sic-clean-kind"}), dec)["outcome"] == "reads only the isolated guitar"
    q = L.q1_outcome(_rows(better={"mix-drawn - cen"}), dec)        # a better constant on the training input
    assert q["outcome"] == "a better constant, no per-unit reading" and q["constant_for_steps_1_and_3"] == "Cen"
    q = L.q1_outcome(_rows(better={"mix-drawn - sic-mix-drawn"}, worse={"mix@-3 - mix-drawn"}), dec)
    assert q["outcome"] == "the ladder's build loses a reading" and q["build_loss_decided"]
    q = L.q1_outcome(_rows(better={"mix-drawn - sic-mix-drawn"}), dec)                 # no loss decided
    assert q["outcome"] == "reads per unit on the training input only"
    q = L.q1_outcome(_rows(set_better={("mix@-3 - sic-mix@-3", "goat")}), dec)
    assert q["outcome"] == "reads on one deciding set only" and q["one_set"]["mix@-3"] == ["goat"]
    q = L.q1_outcome(_rows(set_better={("mix@-3 - sic-mix@-3", "goat")}, worse={"mix@-3 - sic-mix@-3"}), dec)
    assert q["outcome"] == "no gain shown" and q["one_set"]["mix@-3"] == []    # one set needs the pool undecided
    q = L.q1_outcome(_rows(), dec)
    assert q["outcome"] == "no gain shown" and q["constant_for_steps_1_and_3"] == "Cen"
    assert L.q1_outcome(_rows(worse={"aconst - cen"}), dec)["constant_for_steps_1_and_3"] == "Cen"
    q = L.q1_outcome(_rows(worse={"mix@-3 - sic-mix@-3"}), dec)
    assert q["per_unit_worse"]["mix@-3"] and q["outcome"] == "no gain shown"
    assert set(L.Q1_OUTCOMES) == {"reads in the exposed backed mix", "reads only the isolated guitar",
                                  "the ladder's build loses a reading", "reads per unit on the training input only",
                                  "reads on one deciding set only", "a better constant, no per-unit reading",
                                  "no gain shown"}
    assert "xl@-3 - cen decides" in L.Q1_OUTCOMES["a better constant, no per-unit reading"]


def test_stage_2s_readings_and_stage_3s_triggers_are_one_stated_rule():
    s1 = _rows()
    q = L.q2q3_outcome(_rows(), s1, {"outcome": "no gain shown"})
    assert q["stage3"] == {"xlmdxc_and_xl_real": False, "exposure_rows": False, "exposure_because": [], "pool": False,
                           "pool_because": []}
    q = L.q2q3_outcome(_rows(worse={"xl@-3 - xlnoG@-3"}, better={"xl@-3 - cen"}), s1)
    assert q["stage3"]["xlmdxc_and_xl_real"] and q["stage3"]["exposure_because"] == ["xl@-3 - cen"]
    assert q["q3"]["other guitars"] == "worse" and q["q2"]["xl@-3 - cen"] == "better"
    q = L.q2q3_outcome(_rows(), _rows(worse={"mix@-3 - mix-drawn"}))
    assert q["stage3"]["exposure_rows"] and not q["stage3"]["pool"]
    q = L.q2q3_outcome(_rows(), _rows(better={"clean-kind - sic-clean-kind"}),
                       {"outcome": "reads only the isolated guitar"})
    assert q["stage3"]["pool_because"] == ["clean-kind - sic-clean-kind"]
    assert "clean-kind - sic-clean-kind" in q["stage3"]["exposure_because"]          # outcome 2 is Step 4's case
    assert "Q1: reads only the isolated guitar" in q["stage3"]["exposure_because"]
    for n in ("clean-kind - cen",):
        assert L.q2q3_outcome(_rows(), _rows(better={n}))["stage3"]["exposure_because"] == [n]
    for n in ("clean@-3 - cen", "xl@-3 - sic-xl@-3"):
        assert n in L.q2q3_outcome(_rows(better={n}), s1)["stage3"]["exposure_because"]
    assert L.q2q3_outcome(_rows(better={"xl@-3 - sic-xl@-3"}), s1)["stage3"]["pool_because"] == ["xl@-3 - sic-xl@-3"]
    assert set(L.PRIMARY[1]) <= set(L.STAGE_PAIRS[1]) and set(L.PRIMARY[2]) <= set(L.STAGE_PAIRS[2])
    assert ("mix@-3", "mix-drawn") in L.PRIMARY[1]
    assert ("clean@-3", "xl@-3") in L.NEGATIVES[2] and ("xl@-3", "xlnoG@-3") in L.NEGATIVES[2]
    stage1_rows = {f"{a} - {b}" for a, b in L.STAGE_PAIRS[1]}
    stage2_rows = {f"{a} - {b}" for a, b in L.STAGE_PAIRS[2]}
    assert set(L.EXPOSURE_TRIGGERS[1]) | set(L.POOL_TRIGGERS[1]) <= stage1_rows
    assert set(L.EXPOSURE_TRIGGERS[2]) | set(L.POOL_TRIGGERS[2]) <= stage2_rows
    assert set(L.EXPOSURE_TRIGGERS[2]) | set(L.POOL_TRIGGERS[2]) <= {f"{a} - {b}" for a, b in L.NEGATIVES[2]}
    assert not any("xl-v0" in a or "xl-v0" in b for a, b in L.STAGE_PAIRS[2])   # xl-v0 is answered, not rendered


def test_the_swap_row_is_another_pool_parts_real_answer_drawn_per_direction():
    assert L.row_info("swap-mix@-3") == {"stage": 2, "kind": "swap", "style": None, "base": "mix@-3"}
    assert L.row_info("swap-xl@-3")["stage"] == 2
    for bad in ("swap-clean-kind", "swap-cen", "swap-"):
        with pytest.raises(SystemExit):
            L.row_info(bad)
    pool = ["b", "c", "d", "a"]
    got = {L.swap_draw(pool, "a", "swap-mix@-3", h) for h in ("A", "B")}
    assert got <= {"b", "c", "d"}                                  # never the part itself
    assert L.swap_draw(pool, "a", "swap-mix@-3", "A") == L.swap_draw(list(reversed(pool)), "a", "swap-mix@-3", "A")
    draws = {L.swap_draw(pool, f"p{j}", "swap-mix@-3", "A") for j in range(40)}
    assert draws == {"a", "b", "c", "d"}                           # a uniform draw over the pool
    assert L.swap_draw(["a"], "a", "swap-mix@-3", "A") is None
    assert not L.is_constant("swap-mix@-3") and L.is_swap("swap-mix@-3")
    for i, (a, b) in L.SWAP_PAIRS.items():
        assert tuple(a.split(" - ")) in L.STAGE_PAIRS[2] and (b in {f"{x} - {y}" for x, y in L.STAGE_PAIRS[1]}
                                                              or tuple(b.split(" - ")) in L.STAGE_PAIRS[2])


def test_the_two_ceilings_open_or_park_separator_work_only_as_declared():
    T = L.ceiling_together
    assert T("heard-size gain", "small")["reading"] == "opens separator work"
    assert T("undecided, not shown", "heard-size gain")["because"] == ["mixp@-3 - xl@-3"]
    assert T("small", "small")["reading"] == "parks separator work"
    assert T("undecided, not shown", "small")["reading"] == "parks separator work"
    for shown in ("a gain shown, heard size undecided", "a gain shown, not of heard size"):   # a shown gain: the user's
        for got in (T(shown, "small"), T("small", shown)):                                     # call, never a park
            assert not got["reading"].startswith("parks") and got["for_the_user"]
    worse = T("undecided, not shown", "small", "worse")            # the stem beats the backed mix: mixp bounds nothing
    assert worse["reading"].startswith("not settled") and "worse" in worse["reading"]
    assert T("small", "small", "undecided")["reading"] == "parks separator work"
    for clean in ("small", "undecided, not shown", "a gain shown, not of heard size"):   # the confounded pair alone
        assert T(clean, "undecided, not shown")["reading"].startswith("not settled")    # never parks
    got = T("a gain shown, heard size undecided", "a gain shown, not of heard size")
    assert got["reading"].startswith("not settled") and len(got["for_the_user"]) == 2
    assert ("mixp@-3", "xl@-3") in L.NEGATIVES[2] and ("clean@-3", "xl@-3") in L.NEGATIVES[2]
    assert set(L.Q2_STEP3) == {"better", "undecided", "worse"} and "Cen" in L.Q2_STEP3["undecided"]
    q = L.q2q3_outcome(_rows(), _rows())
    assert q["q2_step3"] == L.Q2_STEP3["undecided"] and q["ceiling"]["reading"].startswith("not settled")
    assert set(q["swap"]) == {"mix@-3", "xl@-3"}
    assert set(q["swap"]["xl@-3"]["size_from_swap"]) == {"mean", "lo90", "hi90"} and q["swap"]["xl@-3"]["goat"]
    assert q["swap"]["mix@-3"]["expected_half_width"] == {"pool": 0.054, "goat": 0.029}
    with pytest.raises(SystemExit):
        L.q2_step3(None)                                          # a missing Q2 row refuses, no silent fallback


def test_the_swap_assembly_uses_a_pool_parts_own_half_and_never_the_parts_own_answer():
    P_ = lambda k, f, cl, di, s="goat": {"key": k, "set": s, "fold": f, "amp": "sw50r", "cls": "clean",  # noqa: E731
                                         "cluster": f"{s}|{cl}", "ids": {("di", di)}}
    parts = [P_("a", 0, "c1", "d1"), P_("b", 0, "c2", "d2"), P_("c", 0, "c3", "d3"), P_("d", 1, "c4", "d4"),
             P_("e", 0, "c5", "d1"), P_("f", 0, "c6", "d6", s="cap1")]
    ans = {"goat": {k: {h: {"select": 2, "settings": {"x/y": f"{k}{h}"}} for h in ("A", "B")}
                    for k in ("a", "b", "c", "d", "e")}}             # f has no answer of its own
    out, drawn, missing = L.swap_assemble(parts, ans, "swap-mix@-3")
    assert missing == ["d", "f"]                                   # d: alone in its fold; f: no answer of its own
    for k, hs in drawn.items():
        pool = {q["key"] for q in L.sic_pool(parts, next(pp for pp in parts if pp["key"] == k))}
        for h, q in hs.items():
            assert q in pool and q != k
            assert out["goat"][k][h] == ans["goat"][q][h]          # q's own half-h answer
            assert out["goat"][k][h] != ans["goat"][k][h]          # never p's own
    assert "e" not in {q for hs in drawn.get("a", {}).values() for q in [hs]}   # e shares a's DI file


def test_the_perfect_separators_ceiling_calls_only_a_ruled_out_gain_small():
    assert L.separator_ceiling({"mean": -0.1, "lo90": -0.18, "hi90": -0.02}) == "heard-size gain"
    assert L.separator_ceiling({"mean": -0.03, "lo90": -0.045, "hi90": -0.01}) == "a gain shown, not of heard size"
    assert L.separator_ceiling({"mean": -0.03, "lo90": -0.07, "hi90": -0.01}) == \
        "a gain shown, heard size undecided"                        # the interval still holds heard-size gains
    assert L.separator_ceiling({"mean": 0.0, "lo90": -0.04, "hi90": 0.04}) == "small"
    assert L.separator_ceiling({"mean": -0.02, "lo90": -0.09, "hi90": 0.05}) == "undecided, not shown"
    assert L.separator_ceiling(None) is None


def test_negatives_say_what_the_interval_rules_out_and_read_each_set_left_out():
    iv = lambda m, lo, hi, n: {"mean": m, "lo90": lo, "hi90": hi, "clusters": n,          # noqa: E731
                               "clean": None, "crunch": None, "half_A": None}
    row = {"bks": iv(-0.02, -0.06, 0.02, 8), "goat": iv(0.0, -0.02, 0.02, 130), "panel": iv(-0.05, -0.2, 0.1, 5),
           "deciding_pool": {"mean": -0.023, "lo90": -0.07, "hi90": 0.024}}
    n = L.negatives(row, ("bks", "goat", "panel"))
    assert n["reading"] == "undecided" and n["rules_out_gains_beyond"] == -0.07
    assert set(n["pool_leaving_out"]) == {"bks", "goat", "panel"}
    assert n["pool_leaving_out"]["panel"]["mean"] == pytest.approx(-0.01)
    assert n["per_set"]["goat"]["reading"] == "undecided"


def test_the_summary_reads_each_lender_band_by_class_and_refuses_a_missing_lender():
    units = [{"set": s, "unit": f"{s}{j}", "amp": "sw50r", "cluster": f"{s}c{j % 3}",
              "prt": {"cls": ("clean", "crunch")[j % 2], "di": f"{s}d{j % 3}"}} for s in L.SETS for j in range(6)]
    rows = {s: [(u["cluster"], u["unit"] + "|sw50r", -0.01 * (1 + j % 4), h) for j, u in
                enumerate(x for x in units if x["set"] == s) for h in ("A", "B")] for s in L.SETS}
    band = {u["unit"]: ("Forkupines" if j % 3 else "Ale Lak") for j, u in enumerate(units)}
    for u in units:
        if u["set"] == "panel":
            u["band"] = "B" + u["cluster"][-1]
    got = L.summarise(rows, units, band, wd=set(), real_out={"bks0"})
    assert set(got["bks"]["by_lender_band"]) == {"clean", "crunch"}
    assert "Ale Lak" in got["every_set_by_lender_band"]["crunch"] or "Ale Lak" in got["every_set_by_lender_band"]["clean"]
    assert got["bks"]["without_heavy_lenders"]["parts"] < got["bks"]["parts"]
    assert got["deciding_pool_without_heavy_lenders"] is not None
    assert got["bks"]["without_real_out"]["directions"] == got["bks"]["directions"] - 2   # bks0's two halves out
    assert got["panel"]["band_weighted"]["clusters"] == 3
    with pytest.raises(SystemExit):
        L.summarise(rows, units, {}, wd=set(), real_out=set())
    plain = L.summarise(rows, units, None, wd=set(), real_out=set())
    assert "by_lender_band" not in plain["bks"] and "every_set_by_lender_band" not in plain


# --- the knob reads -----------------------------------------------------------------------------------------------------

def test_knob_groups_cover_the_trained_continuous_heads_and_leave_the_effects_out():
    assert L.knob_group("parameters", "inputGain") == "drive" and L.knob_group("sw50rAmp", "sw50rMid") == "tone"
    assert L.knob_group("cabParameters", "rightCabMicLevel") == "cab"
    assert L.knob_group("ac20EQ", "ac20EQBand4") == "eq" and L.knob_group("pr12EQ", "pr12EQHpf") == "eq"
    assert L.knob_group("drive2", "drive2Gain") == L.knob_group("compressor", "compressorMix") == "pedals"
    for m, k in (("delay", "delayMix"), ("reverb", "reverbMix"), ("parameters", "gateThreshold"),
                 ("parameters", "doublerSpread"), ("cabParameters", "leftCabPan")):
        assert L.knob_group(m, k) is None


def test_the_mean_shift_is_the_cells_mean_answer_less_the_constant():
    pytest.importorskip("numpy")                           # group_of reads full_space's head table
    from learn import full_space as F

    tone = next(n for n in F.CONT if F.by_name()[n].key == "sw50rMid")
    drive = next(n for n in F.CONT if F.by_name()[n].key == "inputGain")
    cell = (0, "sw50r", "clean")
    per = [(cell, "p1", tone, 0.6), (cell, "p2", tone, 0.4), (cell, "p1", drive, 0.9)]
    const = {("p1", tone): 0.3, ("p2", tone): 0.3, ("p1", drive): 0.9}
    got = L.mean_shift(per, const)
    assert got["tone"]["cells"] == 1 and got["tone"]["rms_shift"] == pytest.approx(0.2)
    assert got["drive"]["rms_shift"] == pytest.approx(0.0) and got["cab"]["cells"] == 0


def test_a_rebuilt_mix_must_give_the_stored_features_exactly():
    np = pytest.importorskip("numpy")
    from learn import direct_stems as DS

    rng = np.random.default_rng(1)
    m = {k: {"L": rng.normal(0, 0.1, 480000), "R": rng.normal(0, 0.1, 480000)} for k in ("full", "noG")}
    feats = {}
    for k, v in m.items():
        mels, lu, _ = DS.half_features((v["L"] + v["R"]) / 2)
        feats[k] = {h: (mels[h], lu[h]) for h in ("A", "B")}
    assert L.rebuild_refusal(m, feats) is None
    m2 = {"full": dict(m["full"], L=m["full"]["L"] * 1.5), "noG": m["noG"]}
    assert "differ" in L.rebuild_refusal(m2, feats)
    assert "no stored" in L.rebuild_refusal(m, {"full": feats["full"], "noG": None})


# --- the machine --------------------------------------------------------------------------------------------------------

def test_renders_and_separations_are_registered_with_the_cap():
    from learn import local_objective as LO

    py = "/x/.venv/bin/python"
    assert any(re.search(p, f"{py} -u -m learn.preset_ladder render --rows cen --shard 0/3") for p in LO.RENDERS)
    assert any(re.search(p, f"{py} -u -m learn.preset_ladder replay") for p in LO.RENDERS)
    for cmd in ("report --stage 1", "build --rows mix@-3", "predict --rows mix@-3", "stage0", "lends",
                "sic --rows sic-mix@-3"):
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


# --- the re-centred answer ----------------------------------------------------------------------------------------------

def _enc(c, cm, sw, swm, k, km):
    return (c, cm, sw, swm, k, km)


def test_recentring_moves_each_knob_by_the_answers_deviation_from_its_constant_onto_cen():
    a = _enc([0.6, 0.9, 0.2, 0.5], [1, 1, 1, 0], [1.0, 0.0], [1, 1], [2, 3], [1, 1])
    s = _enc([0.5, 0.4, 0.3, 0.5], [1, 1, 0, 1], [1.0, 1.0], [1, 1], [2, 1], [1, 1])
    e = _enc([0.3, 0.8, 0.1, 0.7], [1, 1, 1, 1], [0.0, 1.0], [1, 1], [0, 0], [1, 1])
    cont, sw, mics = L.recentre(a, s, e, "rule")
    assert cont[0] == pytest.approx(0.4)                          # 0.6 - 0.5 + 0.3
    assert cont[1] == 1.0                                         # 0.9 - 0.4 + 0.8, clipped to the control's range
    assert cont[2] == pytest.approx(0.2)                          # the constant doesn't sound: the answer's own
    assert cont[3] == pytest.approx(0.7)                          # the answer doesn't sound: Cen's (Cen may switch it on)
    assert sw == [0.0, 0.0]                                       # equal to the constant: Cen's; deviating: the answer's
    assert mics == [0, 3]
    cont2, sw2, mics2 = L.recentre(a, s, e, "answer")
    assert cont2 == cont and sw2 == [1.0, 0.0] and mics2 == [2, 3]   # "answer": every discrete the answer's own


def test_an_answer_equal_to_its_constant_becomes_cen_and_nothing_sounds_from_nowhere():
    a = _enc([0.42, 0.1], [1, 0], [1.0], [1], [4], [1])
    e = _enc([0.25, 0.6], [1, 0], [0.0], [1], [1], [1])
    cont, sw, mics = L.recentre(a, a, e, "rule")
    assert cont[0] == pytest.approx(0.25) and math.isnan(cont[1])  # a - a + e = e; no head sounds: none (S's)
    assert sw == [0.0] and mics == [1]                            # no deviation anywhere: Cen exactly
    none = L.recentre(_enc([0.5], [1], [1.0], [0], [2], [0]), a, e, "rule")
    assert none[1] == [None] and none[2] == [None]                # a discrete the answer doesn't hold stays S's


def test_the_recentred_swap_twin_uses_the_swap_rows_own_draws():
    P_ = lambda k, cl, di: {"key": k, "set": "goat", "fold": 0, "amp": "sw50r", "cls": "clean",   # noqa: E731
                            "cluster": f"goat|{cl}", "ids": {("di", di)}}
    parts = [P_("a", "c1", "d1"), P_("b", "c2", "d2"), P_("c", "c3", "d3")]
    rc = {"goat": {k: {h: {"select": 2, "settings": {"x/y": f"rc-{k}{h}"}} for h in ("A", "B")} for k in "abc"}}
    base = {"goat": {k: {h: {"select": 2, "settings": {"x/y": f"{k}{h}"}} for h in ("A", "B")} for k in "abc"}}
    ans, drawn, missing = L.rcs_from(rc, parts, "mix@-3")
    _, swap_drawn, _ = L.swap_assemble(parts, base, "swap-mix@-3")
    assert drawn == swap_drawn and not missing                    # the same q as swap-mix@-3, direction by direction
    for k, hs in drawn.items():
        for h, q in hs.items():
            assert ans["goat"][k][h] == rc["goat"][q][h] and q != k


def test_the_recentred_rows_are_gated_by_their_own_phase(monkeypatch):
    assert set(L.RC_ROWS) == {"rc-mix@-3", "rc-xl@-3", "rca-mix@-3", "rcs-mix@-3"}
    for r in L.RC_ROWS:
        info = L.row_info(r)
        assert info["kind"] == "rc" and info["phase"] == L.RC_PHASE == "phase_lrc" and info["stage"] == 2
    monkeypatch.setattr(L, "ledger_entry", lambda: {"phase_l0": 1, "phase_l1": 1, "phase_l2": 1, "phase_lrc_draft": 1})
    with pytest.raises(SystemExit):
        L.require_row("rc-xl@-3")                                 # the draft key refuses
    L.require_row("xl@-3")                                        # a stage 2 row is unaffected
    monkeypatch.setattr(L, "ledger_entry", lambda: {"phase_l0": 1, "phase_l1": 1, "phase_l2": 1, "phase_lrc": 1})
    L.require_row("rc-xl@-3")


def test_the_recentred_reading_acts_only_on_its_two_product_rows():
    iv = lambda r: ({"mean": -0.1, "lo90": -0.2, "hi90": -0.01} if r == "b" else      # noqa: E731
                    {"mean": 0.1, "lo90": 0.01, "hi90": 0.2} if r == "w" else {"mean": 0.0, "lo90": -0.1, "hi90": 0.1})
    rows = {f"{a} - {b}": {"deciding_pool": iv("u")} for a, b in L.RC_PAIRS}
    got = L.rc_outcome(rows)
    assert got["goal"]["reading"] == got["own"]["reading"] == "undecided"
    assert "not adopted" in got["goal"]["next"]
    rows["rc-xl@-3 - cen"]["deciding_pool"] = iv("b")
    assert L.rc_outcome(rows)["goal"]["reading"] == "better"
    rows["rc-mix@-3 - cen"]["deciding_pool"] = iv("w")           # a mechanism row changes no action
    assert L.rc_outcome(rows)["goal"]["reading"] == "better"
    assert set(L.RC_ACTION) <= set(L.RC_PAIRS)
    del rows["rc-xl@-3 - xl@-3"]
    with pytest.raises(SystemExit):
        L.rc_outcome(rows)                                        # a missing action row refuses
    for a, b in L.RC_PAIRS:
        for nm in (a, b):
            if nm not in ("S", "cen"):
                L.row_info(nm)
