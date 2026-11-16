import json
import math

import pytest

from learn import real_song_exam as X


def test_units_are_v_real_elevens_ten():
    us = X.units()
    assert len(us) == 10 and len({u["band"] for u in us}) == 7
    wk = [u for u in us if len(u["members"]) == 2]
    assert len(wk) == 1 and wk[0]["key"] == "cambridge-wickerman-elecgtr2+3"
    assert sum(u["cls"] == "clean" for u in us) == 4 and sum(u["cls"] == "crunch" for u in us) == 6


def test_model_class():
    assert X.model_class("clean") == "clean" and X.model_class("heavier") == "crunch"
    assert X.model_class("high-gain") == "crunch"
    with pytest.raises(SystemExit):
        X.model_class("metal")


def test_span_rule_stops_on_level_edge_and_max():
    always = lambda t0, t1: True                                  # noqa: E731
    r = X.span_rule((100.0, 110.0), 0.0, 1000.0, always)
    assert r["span"] == [90.0, 120.0] and r["stopped"] == {"before": "max", "after": "max"}
    quiet = lambda t0, t1: not (t0 >= 113.0)                      # noqa: E731  (the DI rests from 113 s)
    r = X.span_rule((100.0, 110.0), 96.5, 1000.0, quiet)
    assert r["before"] == 3 and r["stopped"]["before"] == "edge"   # 97-98 fits, 96-97 starts before 96.5
    assert r["after"] == 3 and r["stopped"]["after"] == "level" and r["span"] == [97.0, 113.0]
    r = X.span_rule((3.15, 13.15), 2.0, 1000.0, always)
    assert r["before"] == 1 and r["span"][0] == pytest.approx(2.15)


def test_pan_position_is_s0s_scale():
    assert X.pan_position(1.0, 1.0) == pytest.approx(0.0)
    assert X.pan_position(1.0, 0.0) == pytest.approx(-1.0) and X.pan_position(0.0, 1.0) == pytest.approx(1.0)
    p = 0.3
    th = (p + 1) * math.pi / 4
    assert X.pan_position(math.cos(th), math.sin(th)) == pytest.approx(p)
    assert X.pan_position(-math.cos(th), math.sin(th)) == pytest.approx(p)      # a flipped channel
    assert X.centred(0.1) and not X.centred(0.2) and not X.centred(None)


def test_fit_pan_finds_lag_gain_and_pan():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(0)
    ref = rng.standard_normal(48000)
    th = (0.5 + 1) * math.pi / 4
    gl, gr, lag = 0.4 * math.cos(th), 0.4 * math.sin(th), 120
    other = rng.standard_normal(48000) * 0.2
    left = np.r_[np.zeros(lag), ref[:-lag]] * gl + other
    right = -np.r_[np.zeros(lag), ref[:-lag]] * gr + other              # one channel flipped
    f = X.fit_pan(ref, left, right, max_lag=480)
    assert f["lag"] == lag and f["p"] == pytest.approx(0.5, abs=0.02)
    assert f["gl"] == pytest.approx(gl, rel=0.05) and f["gr"] == pytest.approx(-gr, rel=0.05)
    assert 0.3 < f["r2"] < 1 and f["target_db"] < 0
    f2 = X.fit_pan(ref, np.r_[ref[60:], np.zeros(60)], np.r_[ref[60:], np.zeros(60)], max_lag=480)
    assert f2["lag"] == -60 and f2["p"] == pytest.approx(0.0, abs=1e-6)


def J(d):
    """A judge group: an any-half answer's distances on both halves."""
    return {"*": {"A": d[0], "B": d[1]}}


def test_held_value_reads_any_half_and_search_halves():
    assert X.held_value(J((2.0, 3.0)), "B") == 3.0
    g = {"A": {"A": 9.0, "B": 2.5}, "B": {"A": 1.5, "B": 9.0}}
    assert X.held_value(g, "B") == 2.5 and X.held_value(g, "A") == 1.5
    assert X.held_value(None, "A") is None and X.held_value({"A": {"B": 1.0}}, "B") == 1.0


def test_rows_across_amps():
    s = {f"x|{a}": J((2.0, 2.0)) for a in X.AMPS} | {f"y|{a}": J((4.0, 4.0)) for a in X.AMPS}
    s["x|ac20"] = J((1.0, 1.0))
    judge = {"S": s, "M": {"x|sw50r": J((1.0, 1.0)), "y|pr12": J((2.0, math.inf))},
             "R": {"x|ac20": J((2.0, 2.0)), "y|ac20": J((2.0, 2.0))}}
    amp_of = {"M": {"x": "sw50r", "y": "pr12"}, "R": {"x": "ac20", "y": "ac20"}}
    band, unit = {"x": "b1", "y": "b2"}, {"x": "u1", "y": "u2"}
    rows, cnt = X.exam_rows(judge, amp_of, ("M", "own"), ("R", "own"), ["x", "y"], band, unit)
    assert cnt["complete"] and cnt["refused_scored_as_S"] == 1
    got = {(r[1], round(r[2], 6)) for r in rows}
    assert ("u1", round(math.log(1 / 2), 6)) in got and ("u2", round(math.log(4 / 2), 6)) in got   # inf -> S on pr12
    rows, _ = X.exam_rows(judge, amp_of, ("M", "own"), ("S", "all"), ["x"], band, unit)
    s3 = (math.log(2) + math.log(2) + math.log(1)) / 3
    assert rows[0][2] == pytest.approx(math.log(1) - s3)
    rows, _ = X.exam_rows(judge, amp_of, ("M", "own"), ("S", "at:R"), ["x"], band, unit)
    assert rows[0][2] == pytest.approx(math.log(1) - math.log(1))          # S on R's amp, ac20
    rows, _ = X.exam_rows(judge, amp_of, ("S", "best"), ("S", "amp:pr12"), ["x"], band, unit)
    assert rows[0][2] == pytest.approx(math.log(1) - math.log(2))
    rows, cnt = X.exam_rows(judge, amp_of, ("M", "own"), ("Q", "own"), ["x"], band, unit)
    assert not rows and cnt["missing"] == 2 and not cnt["complete"]
    judge["S"]["x|pr12"] = J((math.inf, 2.0))
    rows, cnt = X.exam_rows(judge, amp_of, ("M", "own"), ("R", "own"), ["x"], band, unit)
    assert cnt["base_dropped"] == 1 and len(rows) == 1


def test_override_spec_takes_the_twin_where_it_exists():
    judge = {"S": {f"x|{a}": J((1.0, 1.0)) for a in X.AMPS} | {f"y|{a}": J((1.0, 1.0)) for a in X.AMPS},
             "C": {f"{s}|{a}": J((2.0, 2.0)) for s in "xy" for a in X.AMPS}, "Cm": {"y|pr12": J((3.0, 3.0))},
             "M": {"x|pr12": J((1.0, 1.0)), "y|pr12": J((1.0, 1.0))}}
    amp_of = {"M": {"x": "pr12", "y": "pr12"}, "Cm": {"y": "pr12"}}
    rows, cnt = X.exam_rows(judge, amp_of, ("M", "own"), ("C", "at:M", "Cm"), ["x", "y"], {"x": "b", "y": "b"},
                            {"x": "x", "y": "y"})
    v = {r[1]: r[2] for r in rows}
    assert cnt["complete"] and v["x"] == pytest.approx(-math.log(2)) and v["y"] == pytest.approx(-math.log(3))


def test_stratified_uses_unit_attributes():
    rows = [("b1", "u1", -0.1), ("b2", "u2", 0.2), ("b2", "u3", 0.0)]
    attrs = {"u1": {"cls": "clean", "density": "dense", "centred": True, "v10": True},
             "u2": {"cls": "crunch", "density": "sparse", "centred": False, "v10": True},
             "u3": {"cls": "crunch", "density": "dense", "centred": False, "v10": False}}
    r = X.stratified(rows, attrs)
    assert r["all"]["clusters"] == 2 and r["clean"]["parts"] == 1 and r["dense"]["parts"] == 2
    assert r["centred"]["mean"] == pytest.approx(-0.1) and r["v_real_10"]["parts"] == 2


def test_centre_answers_shape():
    st = {"select": 1, "settings": {"parameters/inputGain": "0"}}
    doc = {"all_labels": {"Cen": {a: {"clean": st, "crunch": st} for a in X.AMPS},
                          "Aconst": {f"{a}|{c}": st for a in X.AMPS for c in ("clean", "crunch")}}}
    assert X.centre_answers(doc, "Cen")["pr12"]["crunch"] == st
    assert X.centre_answers(doc, "Aconst")["ac20"]["clean"] == st
    with pytest.raises(SystemExit):
        X.centre_answers({"all_labels": {"Cen": {"pr12": {"clean": st}}}}, "Cen")
    with pytest.raises(SystemExit):
        X.centre_answers({}, "Cen")


def test_knob_distance():
    params = {"pr12Amp/pr12Volume": {"kind": "rotation"}, "pr12EQ/pr12EQBand1": {"kind": "metered", "min": -12,
                                                                                    "max": 12, "unit": "db"},
              "pr12EQ/pr12EQHpf": {"kind": "metered", "min": 20, "max": 500, "unit": "hz"},
              "drive1/drive1Active": {"kind": "switch"}, "cabParameters/leftMicType": {"kind": "enum"},
              "ac20Amp/ac20Volume": {"kind": "rotation"}}
    a = {"pr12Amp/pr12Volume": "0.5", "pr12EQ/pr12EQBand1": "0", "pr12EQ/pr12EQHpf": "20",
         "drive1/drive1Active": "true", "cabParameters/leftMicType": "1", "ac20Amp/ac20Volume": "0"}
    b = dict(a, **{"pr12Amp/pr12Volume": "0.7", "pr12EQ/pr12EQBand1": "6", "pr12EQ/pr12EQHpf": "500",
                   "drive1/drive1Active": "false", "ac20Amp/ac20Volume": "1"})
    d = X.knob_distance(a, b, "pr12", params)
    assert d["n_cont"] == 3 and d["cont_max"] == pytest.approx(1.0)
    assert d["cont_mean"] == pytest.approx((0.2 + 0.25 + 1.0) / 3)
    assert d["switches_differ"] == 1 and d["choices_differ"] == 0


def test_audit_excludes_project_calls_and_flags_research_results():
    ev = [{"type": "system", "subtype": "init", "session_id": "s1", "model": "m", "plugins": []},
          {"type": "assistant", "message": {"content": [
              {"type": "tool_use", "id": "t1", "name": "WebSearch", "input": {"query": "Wickerman Eat The Feeder guitar"}},
              {"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": "ls ~/ndsp-presets/learn/exam"}}]}},
          {"type": "user", "message": {"content": [
              {"type": "tool_result", "tool_use_id": "t1", "content": "see github.com/YoavBZ/neuraldsp-preset-generator"},
              {"type": "tool_result", "tool_use_id": "t2", "content": "YoavBZ/neuraldsp-preset-generator"}]}}]
    au = X.audit_transcript([json.dumps(e) for e in ev] + ["not json"])
    assert au["init"] == ("s1", [], "m") and au["calls"] == 2
    assert "ndsp-presets" in au["leaks"] and "/learn/" in au["leaks"]
    assert au["seen"] == ["YoavBZ/neuraldsp-preset-generator"]                  # from WebSearch only
    clean = X.audit_transcript([json.dumps(ev[0]), json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t3", "name": "WebSearch", "input": {"query": "Femme Wall Of Death"}}]}})])
    assert clean["leaks"] == [] and clean["seen"] == []


def test_names_in_and_the_prompt():
    assert X.names_in("Zenodo record 7044411") == []
    assert X.names_in("Signs by Zeno, and Colour Me Red") == ["colour me red", "zeno"]
    p = X.PROMPT.format(song="S", artist="A", audio="song-01.flac", start="1:00.0", end="1:30.0", python="py", data="d")
    assert "cambridge" not in p.lower() and "ElecGtr" not in p and "result.json" in p and "listening page" in p


def test_mps_jobs():
    ps = [(1, "/x/tools/msst-venv/bin/python -m learn.product_path separate"),
          (2, "/x/tools/demucs-venv/bin/python -m learn.product_path answers DIR"),
          (3, "/x/tools/demucs-venv/bin/python -m learn.pipeline_fix train-ft --masked"),
          (4, "/x/.venv/bin/python -m learn.real_song_exam render"), (5, "/x/tools/msst-venv/bin/python x.py")]
    assert [p for p, _ in X.mps_jobs(ps, own={5})] == [1, 3]


def test_page_groups_and_draw():
    g = X.page_groups({"R": (1, "a"), "M": (1, "b"), "C": (1, "a"), "L": (2, "c")})
    assert g == [("R", "C"), ("M",), ("L",)]
    units = [{"slug": f"s{i}", "band": f"b{i % 7}", "groups": [("R",), ("M",), ("C",), ("L",)] if i else [("R",), ("M", "C")]}
             for i in range(10)]
    items = X.page_draw(units)
    assert len(items) == 12 and sum(it["repeat_of"] is not None for it in items) == 2
    first = {it["id"]: it for it in items}
    for it in items:
        assert sorted(it["letters"]) == list("ABCD"[:len(it["groups"])])
        if it["repeat_of"]:
            f = first[it["repeat_of"]]
            assert it["n"] - f["n"] >= 4
            assert all(f["letters"][k] != v for k, v in it["letters"].items())
    assert X.page_draw(units) == items                                          # seeded


def test_unblind_ties_and_the_read():
    def item(i, band, letters, rep=None, judge=None):
        return {"id": f"i{i}", "band": band, "letters": letters, "repeat_of": rep,
                "judge": judge or {"R": 2.0, "M": 1.0, "C": 1.5, "L": 1.0}}
    it = item(1, "b1", {"A": ("R", "C"), "B": ("M",), "C": ("L",)})
    h = X.unblind(it, {"rank": {"A": 2, "B": 1, "C": 1}})
    assert h["R"]["rank"] == h["C"]["rank"] == 2 and h["M"]["rank"] == 1 and h["M"]["close"] is None
    assert X.unblind(it, {"rank": {"A": 2, "B": 4, "C": 1}}) is None
    assert X.pref(h, "M", "R") == 1.0 and X.pref(h, "R", "C") == 0.5 and X.pref(h, "R", "M") == 0.0
    items = [item(1, "b1", {"A": ("R",), "B": ("M",)}), item(2, "b2", {"A": ("M",), "B": ("R",)}),
             item(3, "b3", {"A": ("R",), "B": ("M",)}), item(4, "b1", {"A": ("M",), "B": ("R",)}, rep="i1")]
    got = {"i1": {"rank": {"A": 2, "B": 1}, "close": {"A": "far", "B": "close"}}, "i2": {"rank": {"A": 1, "B": 2}},
           "i3": {"rank": {"A": 1, "B": 1}}, "i4": {"rank": {"A": 1, "B": 2}}}
    rep = X.ear_read(items, got, n_boot=2000)
    row = rep["rows"]["M over R"]
    assert row["units"] == 3 and row["above"] == 2 and row["ties"] == 1 and row["share"] == pytest.approx(5 / 6)
    assert row["closeness_rated"] == 1 and row["closeness_gap"] == pytest.approx(2.0)
    assert rep["rows"]["M over C"] is None and rep["repeats"][0]["primary_same"]
    assert row["reading"] in ("heard above, one listener", "not known by ear")


def test_page_player_and_cards():
    js = X.player_js()
    assert "keysOf(it)" in js and "real-song-exam:" in js and "delete r[o]" not in js
    html = X.cards([{"id": "i1", "n": 1, "letters": {"A": ("R",), "B": ("M",), "C": ("C",)}}])
    assert 'data-letters="ABC"' in html and 'class="rank n3"' in html and 'data-r="4"' not in html


def test_row_specs_are_declared_once():
    names = [r[0] for r in X.row_specs()]
    assert names[0] == "M - R (primary)" and len(names) == len(set(names))
    assert {r[3] for r in X.row_specs()} == {"all", "v10", "lab"}


def test_render_is_counted_against_the_cap():
    import re

    from learn import local_objective as LO

    assert any(re.search(p, "python -u -m learn.real_song_exam render --shard 0/3") for p in LO.RENDERS)
    for cmd in ("chain", "answers", "report", "c-pick"):
        assert not any(re.search(p, f"python -m learn.real_song_exam {cmd}") for p in LO.RENDERS)
