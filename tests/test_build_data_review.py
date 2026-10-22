import json
import pathlib

import numpy as np
import pytest

from learn import build_data_review as M

ROOT = pathlib.Path(__file__).resolve().parents[1]


# --- names ------------------------------------------------------------------------------------------

def test_track_names():
    assert M.track_stem("14_ElecGtr02DT.wav") == "ElecGtr02DT"
    assert M.track_stem("GTR Pre Rec.L.wav") == "GTR Pre Rec"
    assert M.track_stem("GTR 2 Amp M80-Norm_03-01.wav") == "GTR 2 Amp M80-Norm_03-01"
    files = ["GTR Pre Rec.L.wav", "GTR Pre Rec.R.wav", "OH.L.wav"]
    assert M.stereo_siblings("GTR Pre Rec.L.wav", files) == ["GTR Pre Rec.L.wav", "GTR Pre Rec.R.wav"]
    assert M.stereo_siblings("OH.L.wav", files) == ["OH.L.wav"]
    assert M.stereo_siblings("13_ElecGtr3.wav", files) == ["13_ElecGtr3.wav"]
    assert M.dt_counterpart("ElecGtr02") == "ElecGtr02DT"
    assert M.dt_counterpart("ElecGtr02DT") == "ElecGtr02"


def test_guitar_tracks_exclude_dis():
    assert M.is_guitar_track("28_ElecGtr3Mic2.wav")
    assert M.is_guitar_track("GTR Pre Rec.L.wav")
    assert M.is_guitar_track("16_AcousticGtr.wav")
    assert not M.is_guitar_track("20_ElecGtr03DI.wav")
    assert not M.is_guitar_track("GTR DI_TDP-1.wav")
    assert not M.is_guitar_track("35_ElecGtr6D.wav")
    assert not M.is_guitar_track("Leslie Top TF11 Stereo Set_02.wav")


def test_plain_names():
    assert M.plain_song("Dark Ride", "DarkRide_DeadEnemies_Full") == "Dead Enemies"
    assert M.plain_song("Ale Lak", "Nosso Mundo Deixou De Existir") == "Nosso Mundo Deixou De Existir"
    assert M.mmss(0) == "0:00" and M.mmss(125.4) == "2:05" and M.mmss(-3) == "0:00"


# --- section 1 --------------------------------------------------------------------------------------

def test_amp_parts_union_and_where_used():
    out = M.amp_parts(["a", "b"], kc2=("b", "c"), pages={"p1": ("c", "d"), "p2": ("d",)})
    assert out == {"a": ["stage F"], "b": ["stage F", "knob ceiling 2"],
                   "c": ["knob ceiling 2", "listening pages"], "d": ["listening pages"]}


def test_part_lists_are_development_label_table_parts():
    lt = json.loads((ROOT / "docs/label-table-parts.json").read_text())["parts"]
    assert len(M.KC2_PARTS) == len(set(M.KC2_PARTS)) == 24
    every = set(M.KC2_PARTS) | {s for v in M.PAGE_PARTS.values() for s in v}
    assert every <= set(lt)
    assert all(lt[s]["set"] in (12, 3) for s in every)
    assert M.USER_HUM_PART in lt


def test_half_flags_and_rank():
    assert M.half_flags({"flag": "high"}, None) == ["bleed_high"]
    assert M.half_flags({"flag": "low"}, {"onset_ref_di": 0.29, "di_play_share": 1.0}) == ["onsets_differ"]
    assert M.half_flags({"flag": "low"}, {"onset_ref_di": -1.0, "di_play_share": 0.0}) == ["di_mostly_silent"]
    assert M.half_flags({"flag": "low"}, {"onset_ref_di": 0.8, "ref_active_di_silent": 0.48,
                                          "di_play_share": 0.52}) == ["reference_without_di"]
    assert M.half_flags({"flag": "low"}, {"onset_ref_di": 0.8, "di_play_share": 0.9}) == []
    assert M.part_rank({"A": ["bleed_moderate"], "B": ["bleed_high"]}) == 0
    assert M.part_rank({"A": ["bleed_moderate"], "B": []}) == 1
    assert M.part_rank({"A": [], "B": ["onsets_differ"]}) == 2
    assert M.part_rank({"A": [], "B": []}) == 3


def _part(band, flags_a, flags_b, bleed_a, bleed_b, onset=0.8):
    return {"band": band, "flags": {"A": flags_a, "B": flags_b}, "bleed_db": {"A": bleed_a, "B": bleed_b},
            "onset": {"A": onset, "B": onset}}


def test_order_amp_parts_flagged_first_with_calibration_spread():
    parts = {f"h{k}": _part(f"H{k}", ["bleed_high"], [], -10 - k, -90) for k in range(4)}
    parts.update({f"m{k}": _part(f"M{k}", ["bleed_moderate"], [], -25 - k, -90) for k in range(4)})
    parts.update({f"l{k}": _part(f"L{k % 3}", [], [], -90 if k < 4 else -31 - k, -90, onset=0.5 + k / 100)
                  for k in range(8)})
    order, calib = M.order_amp_parts(parts, n_calib=2)
    assert len(order) == len(parts) and set(order) == set(parts)
    assert order[:2] == ["h0", "h1"]                                   # louder bleed first
    assert len(calib) == 2 and len({parts[s]["band"] for s in calib}) == 2   # one per band
    assert all(parts[s]["bleed_db"]["A"] == -90 for s in calib)        # the cleanest lows
    flagged = [s for s in order if s[0] in "hm"]
    last_flag = max(order.index(s) for s in flagged)
    assert all(order.index(c) < last_flag for c in calib)              # mixed in among the flagged
    rest = [s for s in order if s[0] == "l" and s not in calib]
    loud = [max(parts[s]["bleed_db"].values()) for s in rest]
    assert loud == sorted(loud, reverse=True)                          # borderline lows next


# --- section 2: the doubles rules -------------------------------------------------------------------

def _inv():
    sd = "/s/AleLak"
    sd2 = "/s/Renesans"
    return {
        "a/09_ElecGtr01DI.wav": {"part": "ElecGtr01", "own": ["08_ElecGtr01.wav"], "session_dir": sd,
                                 "source": "cambridge"},
        "a/11_ElecGtr01DTDI.wav": {"part": "ElecGtr01DT", "own": ["10_ElecGtr01DT.wav"], "session_dir": sd,
                                   "source": "cambridge"},
        "a/13_ElecGtr02DI.wav": {"part": "ElecGtr02", "own": ["12_ElecGtr02.wav"], "session_dir": sd,
                                 "source": "cambridge"},
        "r/GTR 1 DI.wav": {"part": "GTR 1", "own": ["GTR 1 Amp.wav"], "session_dir": sd2, "source": "telefunken"},
    }


def test_doubles_candidates_rules():
    inv = _inv()
    files = {"/s/AleLak": ["08_ElecGtr01.wav", "10_ElecGtr01DT.wav", "12_ElecGtr02.wav", "14_ElecGtr02DT.wav"],
             "/s/Renesans": ["GTR 1 Amp.wav", "GTR Pre Rec.L.wav", "GTR Pre Rec.R.wav", "Keys.wav"]}
    summary = {
        "a/13_ElecGtr02DI.wav": {"n": 21, "better": 0.0, "top": [], "hi_other": {"14_ElecGtr02DT.wav": 9}},
        "r/GTR 1 DI.wav": {"n": 43, "better": 0.47, "top": [["GTR Pre Rec.L.wav", 10]], "hi_other": {}},
        "a/09_ElecGtr01DI.wav": {"n": 8, "better": 0.5, "top": [["12_ElecGtr02.wav", 4]], "hi_other": {}},
    }
    scope = {k: ["training pool"] for k in inv}
    got = {(c["di"], c["partner"], c["rule"]) for c in M.doubles_candidates(scope, summary, inv, files)}
    assert got == {
        ("a/09_ElecGtr01DI.wav", "10_ElecGtr01DT.wav", "dt_naming"),
        ("a/11_ElecGtr01DTDI.wav", "08_ElecGtr01.wav", "dt_naming"),
        ("a/13_ElecGtr02DI.wav", "14_ElecGtr02DT.wav", "dt_naming"),       # no DT DI: by file name
        ("a/13_ElecGtr02DI.wav", "14_ElecGtr02DT.wav", "onsets_follow"),
        ("r/GTR 1 DI.wav", "GTR Pre Rec.L.wav", "beats_own_amp"),
    }                                                                      # 8 windows: not "beats"


def test_beats_rule_needs_a_guitar_on_top():
    inv = {"x/GTR DI.wav": {"part": "GTR", "own": ["GTR Amp.wav"], "session_dir": "/s", "source": "telefunken"}}
    summary = {"x/GTR DI.wav": {"n": 40, "better": 0.6, "top": [["Synth.wav", 20]], "hi_other": {}}}
    assert M.doubles_candidates({"x/GTR DI.wav": ["V_sep"]}, summary, inv, {"/s": []}) == []


def test_pairs_are_unordered_takes():
    inv = _inv()
    files = {"/s/AleLak": ["08_ElecGtr01.wav", "10_ElecGtr01DT.wav"], "/s/Renesans": []}
    scope = {"a/09_ElecGtr01DI.wav": ["training pool"], "a/11_ElecGtr01DTDI.wav": ["training pool"]}
    cands = M.doubles_candidates(scope, {}, inv, files)
    for c in cands:
        c["session"] = "/s/AleLak"
    groups = M.group_pairs(cands)
    assert len(groups) == 1 and groups[0]["takes"] == ("ElecGtr01", "ElecGtr01DT")
    assert groups[0]["rules"] == ["dt_naming"] and len(groups[0]["cands"]) == 2


def test_take_of_track():
    dis = list(_inv().values())
    assert M.take_of_track("10_ElecGtr01DT.wav", dis) == "ElecGtr01DT"
    assert M.take_of_track("GTR Pre Rec.R.wav", dis) == "GTR Pre Rec"


def test_direction_options_and_pick():
    cands = [{"di": "a", "partner": "B", "rule": "dt_naming"}, {"di": "a", "partner": "B", "rule": "onsets_follow"},
             {"di": "b", "partner": "A", "rule": "dt_naming"}, {"di": "c", "partner": "X", "rule": "dt_naming"}]
    opts = M.direction_options(cands, lambda c: c["di"] != "c")
    assert [(o["di"], o["partner"]) for o in opts] == [("a", "B"), ("b", "A")]
    assert opts[0]["rules"] == ["dt_naming", "onsets_follow"]
    assert M.direction_options(cands, lambda c: False) == []
    a, b = {"di": "a"}, {"di": "b"}
    # both playing beats a stored render; then a stored render beats more overlap
    assert M.pick_play([(a, True, 0.2, 0.9), (b, False, 0.8, 0.0)])[0] is b
    assert M.pick_play([(a, True, 0.7, 0.0), (b, False, 1.0, 0.9)])[0] is a
    assert M.pick_play([(a, True, 0.9, 0.1), (b, True, 0.9, 0.5)])[0] is b


def test_interleave():
    assert M.interleave([1, 2, 3, 4], ["x", "y"], (1, 10)) == [1, "x", 2, 3, 4, "y"]


# --- windows ----------------------------------------------------------------------------------------

def test_busiest_window_prefers_steady_playing_and_ignores_silence():
    lv = np.full(400, -100.0)
    lv[50:120] = -20.0
    lv[200:330] = -25.0
    start, share = M.busiest_window(lv, 120)
    assert 200 <= start <= 210 and share == 1.0
    _, share = M.busiest_window(np.full(400, -100.0), 120)
    assert share == 0.0                                                # digital silence never plays


def test_pair_window_needs_both_playing():
    a = np.full(400, -30.0)
    b = np.full(400, -100.0)
    b[250:400] = -28.0
    start, both, _ = M.pair_window(a, b, 100)
    assert 250 <= start <= 300 and both == 1.0
    _, both, _ = M.pair_window(a, np.full(400, -95.0), 100)
    assert both == 0.0                                                 # a silent partner is not playing


# --- sittings, ids, export --------------------------------------------------------------------------

def test_split_sittings_contiguous_and_balanced():
    d = [10.0] * 201
    s = M.split_sittings(d, max_s=900)
    assert [i for x in s for i in x] == list(range(201))
    assert len(s) == 3
    sums = [sum(d[i] for i in x) for x in s]
    assert max(sums) - min(sums) <= 10.0 and max(sums) <= 900
    assert M.split_sittings([5.0] * 10, max_s=900) == [list(range(10))]
    assert M.split_sittings([]) == []


def test_item_ids_stable_and_distinct():
    assert M.item_id("amp", "x", "A") == M.item_id("amp", "x", "A")
    assert M.item_id("amp", "x", "A") != M.item_id("amp", "x", "B")
    assert M.item_id("di", "x").startswith("di-")


def _items():
    return [{"id": "amp-1", "section": "amp"}, {"id": "pair-1", "section": "pair"}, {"id": "di-1", "section": "di"}]


def test_check_export():
    obj = {"page": M.PAGE, "answers": [
        {"id": "amp-1", "verdict": "bleed", "note": " drums "},
        {"id": "pair-1", "verdict": None, "note": ""},
        {"id": "di-1", "verdict": None, "note": "odd click at the end"}]}
    got, probs = M.check_export(obj, _items())
    assert probs == []
    assert got == {"amp-1": {"verdict": "bleed", "note": "drums"},
                   "di-1": {"verdict": None, "note": "odd click at the end"}}
    _, probs = M.check_export({"page": M.PAGE, "answers": [{"id": "pair-1", "verdict": "clean"},
                                                           {"id": "zzz", "verdict": "clean"}]}, _items())
    assert len(probs) == 2
    assert M.check_export({"page": "other"}, _items())[1]


def test_merge_verdicts_later_wins():
    old = {"amp-1": {"verdict": "clean", "note": "", "merged": "t0"}}
    new = {"amp-1": {"verdict": "bleed", "note": "x"}, "di-1": {"verdict": "hum", "note": ""}}
    out = M.merge_verdicts(old, new, "t1")
    assert out["amp-1"] == {"verdict": "bleed", "note": "x", "merged": "t1"} and out["di-1"]["merged"] == "t1"


# --- the page ---------------------------------------------------------------------------------------

def _public():
    return [
        {"id": "amp-1", "section": "amp", "title": "Band · Song · GTR 1", "subtitle": "First half",
         "clip_s": 6.0, "clip": "amp-1", "extra": [["Its DI", "amp-1-di"]]},
        {"id": "pair-1", "section": "pair", "title": "Band · Song · A and B </script>", "subtitle": "at 1:00",
         "clip_s": 8.5, "clip": "pair-1", "extra": [["Render only", "pair-1-render"]]},
        {"id": "di-1", "section": "di", "title": "Band · Song · GTR DI", "subtitle": "x.wav at 0:10",
         "clip_s": 6.0, "clip": "di-1", "extra": []},
    ]


def test_page_has_every_item_verdict_and_no_detector_words():
    items = _public()
    audio = {k: "QUFB" for k in ("amp-1", "amp-1-di", "pair-1", "pair-1-render", "di-1")}
    page = M.page_html(2, 3, items, audio, "abc")
    assert page.count('class="item"') == 3
    for sec in M.SECTIONS.values():
        for v, _ in sec["verdicts"]:
            assert f'data-v="{v}"' in page
    assert "sitting 2 of 3" in page and 'data-cue="4.00,0.50"' in page
    assert M.page_leaks(page) == []
    data = page.split('<script id="data" type="application/json">', 1)[1].split("</script>", 1)[0]
    assert json.loads(data.replace("<\\/", "</"))["items"][1]["title"].endswith("</script>")
    bad = [dict(items[0], subtitle="bleed_db -9, calibration")]
    assert set(M.page_leaks(M.page_html(1, 1, bad, audio, "abc"))) >= {"bleed_db", "calibration"}


def test_est_seconds():
    assert M.est_seconds({"clip_s": 6.0}) == pytest.approx(6.0 + M.DECIDE_S)
