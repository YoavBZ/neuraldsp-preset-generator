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


def ladder_doc(sel=None):
    """centres.json as the ladder writes it (`preset_ladder.cmd_centres` at b9f2d25f)."""
    selects = {"pr12": 1, "sw50r": 2, "ac20": 0}
    st = lambda a: {"select": selects[a] if sel is None else sel, "settings": {f"{a}Amp/{a}Volume": "0.5",   # noqa: E731
                                                                               "parameters/inputGain": "0"}}
    return {"plan": "p", "hold": "C3-cabS", "model_sha256": ["s1", "s2"], "c3r_sha256": "c",
            "centres": {tag: {a: {"clean": st(a), "crunch": st(a)} for a in X.AMPS} for tag in ("cen", "aconst")},
            "records_used": {}, "time": "t"}


def test_centre_answers_read_the_ladders_shape():
    doc = ladder_doc()
    c = X.centre_answers(doc, "cen")
    assert c["pr12"]["crunch"]["select"] == 1 and c["ac20"]["clean"]["settings"]["ac20Amp/ac20Volume"] == "0.5"
    assert X.centre_answers(doc, "aconst")["sw50r"]["clean"]["select"] == 2
    assert X.CENTRE_NAMES == {"EX-C": "cen", "EX-Cown": "aconst"}
    alt = {"all_labels": {"Cen": doc["centres"]["cen"], "Aconst": doc["centres"]["aconst"]}}
    assert X.centre_answers(alt, "cen") == c                                  # the ladder's other shape, read alike
    with pytest.raises(SystemExit):
        X.centre_answers(ladder_doc(sel=2), "cen")                              # a pr12 centre selecting another amp
    bad = ladder_doc()
    del bad["centres"]["cen"]["ac20"]["crunch"]
    with pytest.raises(SystemExit):
        X.centre_answers(bad, "cen")
    with pytest.raises(SystemExit):
        X.centre_answers({}, "cen")


def test_centres_refusal_ties_them_to_the_adopted_pair():
    doc = ladder_doc()
    assert X.centres_refusal(doc, ["s1", "s2"]) is None
    assert "model_sha256" in X.centres_refusal(doc, ["s1", "x"])
    assert "hold" in X.centres_refusal(dict(doc, hold="K.space"), ["s1", "s2"])


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


def ev_use(i, name, inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": i, "name": name, "input": inp}]}}


def ev_res(i, content):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": i, "content": content}]}}


def test_audit_excludes_project_calls_and_flags_research_results():
    h = X.HOME
    run, plug, venv, runs = f"{h}/gtr-q/runs/abcde", f"{h}/gtr-q/plugin", f"{h}/gtr-q/venv", f"{h}/gtr-q/runs"
    allowed, own = (run, plug, venv, *X.ALLOWED_ROOTS), X.own_tmp(run)
    kw = {"allowed": allowed, "runs_root": runs, "own": own, "plugin_text": frozenset({f"{h}/ndsp-presets"})}
    init = {"type": "system", "subtype": "init", "session_id": "s1", "model": "m", "plugins": []}

    def audit(*evs):
        return X.audit_transcript([json.dumps(e) for e in (init, *evs)] + ["not json"], **kw)
    au = audit(ev_use("t1", "WebSearch", {"query": "Wickerman Eat The Feeder guitar"}),
               ev_use("t2", "Bash", {"command": "ls ~/ndsp-presets/learn/exam"}),
               ev_res("t1", "see github.com/YoavBZ/neuraldsp-preset-generator"),
               ev_res("t2", [{"type": "text", "text": "YoavBZ/neuraldsp-preset-generator"}]))
    assert au["init"] == ("s1", [], "m") and au["calls"] == 2
    assert "ndsp-presets" in au["leaks"] and au["seen"] == ["YoavBZ/neuraldsp-preset-generator"]   # web results only
    assert any("ndsp-presets" in p for p in au["outside_calls"]) and X.audit_why(au)
    assert own[:2] == (f"/private/tmp/claude-501/{run.replace('/', '-')}", f"/tmp/claude-501/{run.replace('/', '-')}")
    au = audit(ev_use("t3", "WebSearch", {"query": "Femme Wall Of Death guitar rig"}),
               ev_use("t4", "Bash", {"command": f"cd {run} && {venv}/bin/python {plug}/scripts/show.py "
                                                "'/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/Neural DSP/Hair Metal.xml'"}),
               ev_use("t5", "Read", {"file_path": f"{plug}/skills/generate/../../reference/preset-spec.md"}),
               ev_use("t6", "WebFetch", {"url": "https://example.com/learn/guitar", "prompt": "rig"}),
               ev_use("t7", "Read", {"file_path": f"{plug}/.claude-plugin/plugin.json"}),
               ev_use("t8", "Write", {"file_path": f"{own[0]}/spec.json", "content": "{}"}),
               ev_use("t9", "Write", {"file_path": "/tmp/spec.json", "content": "{}"}),
               ev_use("t10", "Bash", {"command": "python ./tmp/x.py && ls ./out"}),
               ev_res("t4", f"data_root_origin: ~/ndsp-presets (installed-plugin default)\nusing /opt/homebrew/lib/x"),
               ev_res("t10", "/var/folders/ab/T/x.wav"))
    assert X.audit_why(au) == [], X.audit_why(au)
    assert au["tmp_calls"] == ["/tmp/spec.json"] and au["tmp_results"] == ["/var/folders/ab/T/x.wav"]
    assert au["plugin_text_results"] == [f"{h}/ndsp-presets"] and au["result_paths"] == ["/opt/homebrew/lib/x"]
    for bad, why in ((ev_use("b1", "Bash", {"command": "cat ../xyzab/result.json"}), ".. that may leave"),
                     (ev_use("b2", "Bash", {"command": "cd .. && ls"}), ".. that may leave"),
                     (ev_use("b3", "Bash", {"command": "cd / && ls Users"}), "targets /"),
                     (ev_use("b4", "Bash", {"command": "find / -name result.json"}), "targets /"),
                     (ev_use("b5", "Read", {"file_path": f"{runs}/xyzab/result.json"}), "outside"),
                     (ev_use("b6", "Glob", {"pattern": "*", "path": f"{h}/gtr-session/runs"}), "gtr-session"),
                     (ev_use("b7", "WebSearch", {"query": "YoavBZ guitar presets"}), "account name"),
                     (ev_use("b8", "Bash", {"command": "ls ~"}), "outside"),
                     (ev_use("b9", "Write", {"file_path": "/tmp/claude-501/spec.json", "content": "{}"}), "outside"),
                     (ev_use("b12", "Write", {"file_path": "/tmp/claude/spec.json", "content": "{}"}), "outside"),
                     (ev_use("b10", "Read", {"file_path": f"{plug}/../runs/xyzab/prompt.txt"}), ".. that may leave"),
                     (ev_use("b11", "Read", {"file_path": f"{h}/shortlist-sandboxes/x/notes.md"}), "shortlist")):
        au = audit(bad)
        assert any(why in w for w in X.audit_why(au)), (bad, X.audit_why(au))
    for res_ in (f"{h}/gtr-session/runs/01", f"{runs}/xyzab/result.json", "/private/tmp/claude-501/x/scratchpad/a.md",
                 f"{h}/shortlist-sandboxes/drag_me_down/notes.md", f"{h}/.zsh_history"):
        au = audit(ev_use("t12", "Bash", {"command": "grep -r guitar ."}), ev_res("t12", f"found\n{res_}"))
        assert au["result_leaks"] == [res_] and X.audit_why(au), res_


def test_research_settings_reruns_and_the_run_picked():
    base = {"sandbox": {"enabled": True}, "permissions": {"deny": ["Read(~/ndsp-presets/**)"]}}
    s = X.run_settings("aaaaa", ["aaaaa", "bbbbb"], base, ["gtr-q", ".pyenv", "ndsp-presets", "shortlist-sandboxes",
                                                            ".codex", ".zsh_history", ".claude"],
                       ["projects", "plugins", "shell-snapshots", "session-env"],
                       {"/private/tmp/claude-501": [str(X.RUNS / "aaaaa").replace("/", "-"), "-Users-yoavbz-projects-x"]})
    deny = s["permissions"]["deny"]
    for e in ("shortlist-sandboxes", ".codex", ".zsh_history"):
        assert f"Read(~/{e})" in deny and f"Read(~/{e}/**)" in deny
    assert not any(f"~/{e}" in d for e in ("gtr-q", ".pyenv") for d in deny) and "Read(~/.claude)" not in deny
    assert "Read(~/.claude/plugins/**)" in deny and not any("shell-snapshots" in d or "session-env" in d for d in deny)
    assert "Read(//private/tmp/claude-501/-Users-yoavbz-projects-x/**)" in deny
    assert not any(str(X.RUNS / "aaaaa").replace("/", "-") in d for d in deny)            # its own temp folder
    assert f"Read(/{X.RUNS / 'bbbbb'}/**)" in deny and not any("runs/aaaaa" in d for d in deny)
    assert f"Edit(/{X.PLUGIN}/**)" in deny and f"Edit(/{X.VENV}/**)" in deny
    assert s["env"]["TMPDIR"] == str(X.RUNS / "aaaaa" / "tmp") and deny.count("Read(~/ndsp-presets/**)") == 1
    assert base["permissions"]["deny"] == ["Read(~/ndsp-presets/**)"]          # the routing study's own untouched
    assert X.pick_run([("2", "b", False), ("1", "a", False)]) == "a"          # the first that passed, never a later draw
    assert X.pick_run([("1", "a", True), ("2", "b", False)]) == "b" and X.pick_run([("1", "a", True)]) is None
    assert X.again_refusal([True]) is None
    assert X.again_refusal([False]) and X.again_refusal([True, True]) and X.again_refusal([])


def test_tree_sha_ignores_bytecode_and_sees_edits(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    h0 = X.tree_sha(tmp_path)
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "a.cpython-314.pyc").write_bytes(b"\0")
    assert X.tree_sha(tmp_path) == h0
    (tmp_path / "a.py").write_text("x = 2")
    assert X.tree_sha(tmp_path) != h0


def test_chain_argv_changes_one_stage_each():
    inp = {"units": {"u": {"mix": "/m.wav", "unity": "k", "offset_samples": 48000 * 3,
                           "crops": {"s": {"file_s": [20.0, 30.0]}}, "span": {"file_s": [10.0, 40.0],
                                                                                 "session_s": [13.0, 43.0]}}},
           "unity": {"k": {"file": "/u.wav"}}}
    res = {"units": {"u": {"cls_model": "crunch"}}}
    u = {"key": "u", "members": ["s"], "cls": "clean"}

    def arg(a, flag, **kw):
        v = X.chain_argv(a, u, inp, res, **kw)
        return v[v.index(flag) + 1] if flag in v else None
    assert arg("M", "--part") == "10.000000" and arg("M", "--cls") == "crunch" and arg("M", "--start") is None
    assert arg("Mlab", "--cls") == "clean" and arg("Mlab", "--part") == "10.000000"
    assert arg("Mcrop", "--start") == "20.000000"
    assert arg("Mx", "--start", m_start=25.0) == "25.000000" and arg("Mx", "--version", m_start=25.0) == "xlst_mdxc"
    assert arg("Munity", "--start", m_start=25.0) == "28.000000" and arg("Munity", "--song", m_start=25.0) == "/u.wav"
    assert arg("Munity", "--part", m_start=25.0) is None
    with pytest.raises(SystemExit):
        X.chain_argv("Mx", u, inp, res)


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
    specs = X.row_specs()
    names = [r[0] for r in specs]
    assert names[0] == "M - R (primary)" and len(names) == len(set(names))
    assert {r[3] for r in specs} == {"all", "v10", "lab", "r", "rroute"}
    assert all(r[3] in ("r", "rroute") for r in specs if "EX-R" in (r[1][0], r[2][0]) or "EX-Rroute" in (r[1][0], r[2][0]))
    assert any("oracle" in n for n in names if "best amp" in n)


def test_render_is_counted_against_the_cap():
    import re

    from learn import local_objective as LO

    assert any(re.search(p, "python -u -m learn.real_song_exam render --shard 0/3") for p in LO.RENDERS)
    for cmd in ("chain", "answers", "report", "c-pick"):
        assert not any(re.search(p, f"python -m learn.real_song_exam {cmd}") for p in LO.RENDERS)
    assert any(re.search(p, "/x/msst-venv/bin/python -m learn.product_path separate SONG --out D") for p in LO.SEPARATIONS)
    assert not any(re.search(p, f"/x/python -m learn.product_path {c} D") for p in LO.SEPARATIONS
                   for c in ("answers", "render", "pick"))


def test_guards_gate_what_follows(tmp_path, monkeypatch):
    g, r = tmp_path / "guards.json", tmp_path / "r1-repro.json"
    monkeypatch.setattr(X, "guard_files", lambda: {"guards_json": g, "r1_repro_json": r})
    with pytest.raises(SystemExit):
        X.require_guards()                                                  # neither has run
    g.write_text(json.dumps({"passes": True}))
    r.write_text(json.dumps({"passes": False}))
    with pytest.raises(SystemExit):
        X.require_guards()                                                  # the R1 reproduction failed
    r.write_text(json.dumps({"passes": True}))
    got = X.require_guards()
    assert set(got) == {"guards_json", "r1_repro_json"} and got["guards_json"] == X.sha_file(g)


def test_the_lock_refuses_a_changed_research_file(tmp_path, monkeypatch):
    res, inp = tmp_path / "research.json", tmp_path / "inputs.json"
    res.write_text("{}")
    inp.write_text("{}")
    lock = tmp_path / "lock.json"
    monkeypatch.setattr(X, "research_dir", lambda: tmp_path)
    monkeypatch.setattr(X, "inputs_path", lambda: inp)
    monkeypatch.setattr(X, "chain_lock", lambda: lock)
    with pytest.raises(SystemExit):
        X.check_lock()                                                      # the chain has not started
    lock.write_text(json.dumps({"hashes": {"research_json": X.sha_file(res), "inputs_json": X.sha_file(inp)}}))
    X.check_lock()
    res.write_text('{"units": {}}')
    with pytest.raises(SystemExit):
        X.check_lock()


def test_dotdot_follows_cd_and_root_ignores_division():
    h = X.HOME
    run, plug = f"{h}/gtr-q/runs/abcde", f"{h}/gtr-q/plugin"
    allowed = (run, plug, f"{h}/gtr-q/venv")
    assert X.dotdot(f"cd {plug}/scripts && cat ../packs/morgan/recipes.json", allowed, run, shell=True) == []
    assert X.dotdot("cat ../packs/morgan/recipes.json", allowed, run, shell=True) == ["../packs/morgan/recipes.json"]
    assert X.dotdot("cd out && cat ../spec.json", allowed, run, shell=True) == []
    assert X.dotdot("cd .. && ls", allowed, run, shell=True) == [".."]
    assert X.dotdot("out/../spec.json", allowed, run) == []
    for cmd in ("cd $HOME/a/b/c && cat ../../../../x", 'cd "$OLDPWD" && cat ../y', "cd && cat ../x", "cd - ; cat ../x",
                "cd `pwd` && cat ../x", "cat $D/../x"):
        assert X.dotdot(cmd, allowed, run, shell=True), cmd                    # an unknown folder: every .. after it
    assert X.dotdot(f"cd $X && cd {plug}/scripts && cat ../packs/a.json", allowed, run, shell=True) == []
    assert not X.targets_root("Bash", {"command": "python3 -c 'print(1 / 2)'"})
    assert not X.targets_root("Bash", {"command": "echo 'rock / stoner'"})
    assert X.targets_root("Bash", {"command": "cd / && ls"}) and X.targets_root("Bash", {"command": "find / -name x"})
    assert X.targets_root("Glob", {"pattern": "*", "path": "/"}) and not X.targets_root("WebSearch", {"query": "a / b"})


def test_venv_base_and_the_settings_folder(tmp_path):
    (tmp_path / "pyvenv.cfg").write_text("home = /Users/x/.pyenv/versions/3.14.6/bin\nversion = 3.14.6\n")
    assert X.venv_base(tmp_path) == ("/Users/x/.pyenv/versions/3.14.6",)
    assert X.venv_base(tmp_path / "none") == ()
    s = X.run_settings("aaaaa", [], {"permissions": {"deny": []}}, [], [], {})
    assert f"Read(/{X.SETTINGS_DIR}/**)" in s["permissions"]["deny"]


def test_runner_check_verdict():
    ents = ["drag_me_down", "bloomlight"]
    pairs = [("WebSearch", "Magilla Turbosauro guitar", "a bloomlight review"),       # an entry name elsewhere: ignored
             ("Bash", "echo $TMPDIR; ls ~/shortlist-sandboxes",
              f"{X.RUNS}/abcde/tmp\nls: /Users/x/shortlist-sandboxes: Operation not permitted"),
             ("Read", "/x/skills/generate/SKILL.md", "# Generate a preset")]
    v = X.check_verdict(pairs, ents, X.RUNS / "abcde" / "tmp",
                        ["shortlist-sandboxes", "a call names a path outside the run: /Users/x/shortlist-sandboxes"])
    assert v["fence"] == "refused" and v["probe_refused"] and v["tmpdir_own"] and v["other_audit_reasons"] == []
    v = X.check_verdict([("Bash", "ls ~/shortlist-sandboxes", "bloomlight\ndrag_me_down")], ents, "/elsewhere", ["x"])
    assert v["fence"] == "listed" and not v["probe_refused"] and v["probe_entries_seen"] == ["bloomlight", "drag_me_down"]
    assert not v["tmpdir_own"] and v["other_audit_reasons"] == ["x"]
    v = X.check_verdict([("Bash", "ls '~/shortlist-sandboxes'", "ls: ~/shortlist-sandboxes: No such file or directory")],
                        ents, "/t", [])
    assert v["fence"] == "not proven" and not v["probe_refused"]               # not the sandbox's denial
    v = X.check_verdict([("Bash", "ls ~/shortlist-sandboxes", "zsh: permission denied: /Users/x/shortlist-sandboxes")],
                        ents, "/t", [])
    assert v["fence"] == "refused"
    assert X.check_verdict([], ents, "/t", [])["fence"] == "not proven"
    ev = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t", "name": "Bash",
                                                          "input": {"command": "ls"}}]}},
          {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t", "content": "a"}]}}]
    assert X.tool_pairs([json.dumps(e) for e in ev] + ["junk"]) == [("Bash", "ls", "a")]
