"""C2 (docs/full-controls-plan.md, "C2 in detail"): learn/full_controls_c2.py."""
import json
import math
import re

import pytest

pytest.importorskip("numpy")

from learn import every_control as E  # noqa: E402
from learn import full_controls as F  # noqa: E402
from learn import full_controls_c1b as C  # noqa: E402
from learn import full_controls_c2 as X  # noqa: E402
from learn import knob_ceiling2 as K2  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import pipeline_fix as P  # noqa: E402


def full_start(amp="pr12"):
    """A whole Morgan setting from the table's neutral values: the amp EQ and every section on, dry, both cabs on, the
    gate off (as every stored label has it)."""
    x = {c.path: c.neutral for c in E.table("morgan") if c.neutral is not None and c.module}
    x.update(K2.HELD_ON)
    for k in (("ampParameters", "sectionActive"), ("cabParameters", "sectionActive"), ("fxParameters", "sectionActive"),
              (f"{amp}EQ", f"{amp}EQActive"), ("cabParameters", "leftCabActive"), ("cabParameters", "rightCabActive")):
        x[k] = "true"
    x[("delay", "delaySync")] = "1"
    x[("parameters", "gateActive")] = "false"
    x[("cabParameters", "leftMicType")], x[("cabParameters", "rightMicType")] = "0", "3"
    if amp in K2.SPRING:
        x[next(iter(K2.SPRING[amp][0]))] = "0"
    return x


# --- records, order, known keys ---------------------------------------------------------------------------------------

def test_goat_records_and_the_ones_left_out():
    units = {"g/u1": {"di": "g/i1", "unit": "g/u1"}, "g/u2": {"di": "g/i1", "unit": "g/u2"}}
    lab = [{"unit": "g/u1", "amp": "ac20", "cls": "clean", "label": {}}]
    recs = X.goat_records(lab, units, {"g/u1"}, lambda key: f"/s/{key}")
    assert recs == [{"set": "goat", "block": "goat", "key": "g/u1|ac20", "unit": "g/u1", "amp": "ac20", "cls": "clean",
                     "cluster": "g/i1", "source": "/s/g/u1|ac20", "prt": units["g/u1"], "real_out": True}]
    stored = lab + [{"unit": "g/u2", "amp": "pr12", "label": None, "why": "the one-window lag rule"},
                    {"unit": "g/u3", "amp": "pr12", "label": None, "best": {"fallback": "silent"}}]
    left = X.goat_left_out(stored, {r["key"] for r in recs})
    assert left == [{"key": "g/u2|pr12", "block": "goat", "why": "the one-window lag rule"},
                    {"key": "g/u3|pr12", "block": "goat", "why": "fallback: silent"}]


def test_bks_records_are_ft2s_rows_less_c1a_and_name_the_rest():
    parts = {"b/u1": {"unit": "b/u1", "di": "b/d1", "cls": "crunch"}, "b/u2": {"unit": "b/u2", "di": "b/d2", "cls": "clean"}}
    lab = [{"unit": "b/u1", "amp": "pr12", "stage": 1, "cls": "crunch"}, {"unit": "b/u1", "amp": "sw50r", "stage": 1,
                                                                           "cls": "crunch"},
           {"unit": "b/u2", "amp": "ac20", "stage": 2, "cls": "clean"}]
    recs = X.bks_records(lab, parts, {"b/u1|pr12"}, {"b/u2"}, lambda key: f"/r/{key}")
    assert [(r["key"], r["block"], r["cluster"], r["real_out"]) for r in recs] == [("b/u1|sw50r", "bks1", "b/d1", False),
                                                                                 ("b/u2|ac20", "bks2", "b/d2", True)]
    stored = lab + [{"unit": "b/u3", "amp": "pr12", "stage": 2, "label": {}}, {"unit": "b/u4", "amp": "pr12", "stage": 2,
                                                                               "label": None}]
    left = X.bks_left_out(stored, {f"{r['unit']}|{r['amp']}" for r in lab}, {"b/u3"})
    assert [(x["key"], x["block"], x["why"][:11]) for x in left] == [("b/u3|pr12", "bks2", "the lag rul"),
                                                                     ("b/u4|pr12", "bks2", "no label")]


def test_c1a_block_continues_c1a_records_and_names_those_left_out():
    base = {"set": "bks", "unit": "u", "amp": "pr12", "cls": "clean", "cluster": "c", "real_out": False, "prt": {},
            "source": "/s", "budget": 100}
    c1a = [dict(base, key=k) for k in ("a", "b", "c")]
    outs = {"a": {"label": {}, "_path": "/p/a"}, "b": {"label": None, "_path": "/p/b"}}
    recs, left = X.c1a_block(c1a, outs)
    assert [(r["key"], r["block"], r["c1a_output"], r["c1a_budget"]) for r in recs] == [("a", "c1a", "/p/a", 100)]
    assert {(x["key"], x["why"]) for x in left} == {("b", "C1a label fell back"), ("c", "no C1a output")}


def test_the_order_is_goat_then_bks_stage_1_then_stage_2_in_every_shard():
    recs = ([{"block": "bks2", "key": f"z{i}"} for i in range(4)] + [{"block": "bks1", "key": f"m{i}"} for i in range(3)]
            + [{"block": "c1a", "key": f"b{i}"} for i in range(3)] + [{"block": "goat", "key": f"a{i}"} for i in range(6)])
    assert [r["block"] for r in X.order(recs)] == ["goat"] * 6 + ["bks1"] * 3 + ["bks2"] * 4 + ["c1a"] * 3
    shards = [X.shard_records(recs, k, 3) for k in range(3)]
    assert sorted(r["key"] for s in shards for r in s) == sorted(r["key"] for r in recs)
    for s in shards:
        assert [r["block"] for r in s][:2] == ["goat", "goat"]
        assert [r["block"] for r in s] == sorted((r["block"] for r in s), key=X.BLOCKS.index) and s[-1]["block"] == "c1a"


def test_known_keys_are_the_effects_doubler_and_spring_off():
    pr = X.known_keys("pr12")
    assert pr == {"reverb/reverbActive": "false", "delay/delayActive": "false", "tremolo/tremoloActive": "false",
                  "parameters/doublerActive": "false", "spring/springOn": "false"}
    assert "spring/springOn" not in X.known_keys("ac20") and "spring/springOn" in X.known_keys("sw50r")
    assert "off by source" in X.KNOWN_WHY
    dry = LO.sdict(full_start("pr12"))
    assert X.known_problems(dry, "pr12") == []
    assert X.known_problems({**dry, "reverb/reverbActive": "true", "pr12Amp/pr12Reverb": "0.3"}, "pr12") == \
        ["reverb/reverbActive", "spring/springOn"]
    assert X.known_problems({}, "sw50r") == []


def test_start_problems_pass_a_dry_label_and_name_what_fails():
    lab = LO.sdict(full_start("pr12"))
    src = {"label": lab, "select": 0, "search": "A", "best": {"settings": lab, "judge": {"A": 2.0}}}
    assert X.start_problems(src, "pr12", 0) == []
    assert X.start_problems({**src, "label": None}, "pr12", 0) == ["no label"]
    wet = {**lab, "delay/delayActive": "true"}
    bad = X.start_problems({**src, "select": 1, "label": wet, "best": {"settings": lab, "judge": {"A": float("nan")}}},
                           "pr12", 0)
    assert bad[:2] == ["select", "stored best not finite"] and bad[2].startswith("wet")


def test_searched_keys_join_step_1_and_stages_a_and_b_with_no_effect_key():
    x = {**full_start("pr12"), C.SPRING_KEY: "false"}
    lists = {"pr12": {"leftMicType": ["3"], "rightMicType": ["3"]}}
    keys = X.searched_keys(["parameters/inputGain"], x, x, "pr12", lists)
    assert {"parameters/inputGain", "cabParameters/leftRoomMicLevel", "cabParameters/leftMicType",
            "pr12EQ/pr12EQBand3"} <= set(keys)
    assert not any(k.split("/")[0] in ("reverb", "delay", "tremolo", "spring") for k in keys)


def test_unusable_is_non_finite_on_either_half_or_a_peak_near_j0s_floor():
    from learn import arm_a_mega53 as A
    assert X.SILENT_DBFS == A.SILENT_DBFS
    ok = {"A": 2.0, "B": 3.0}
    assert X.unusable(ok, -40.0) is None and X.unusable(ok, -56.9) is None
    assert "floor" in X.unusable(ok, -57.1) and "floor" in X.unusable(ok, None)
    assert X.unusable({"A": 2.0, "B": float("nan")}, -20.0) == "non-finite on half B"
    assert X.unusable({"A": 2.0}, -20.0) == "non-finite on half B"
    assert X.quiet(-50.5) and not X.quiet(-49.0) and not X.quiet(None)
    assert X.unusable(ok, None, check_peak=False) is None                       # a replayed best: the halves alone
    for p in (-56.9, -52.0, -49.0):                                             # the -57 to -49 dBFS labels stand
        assert X.unusable(ok, p) is None


def test_renders_upper_is_the_declared_per_record_cost():
    assert X.renders_upper([{"block": "goat"}]) == 1 + 200 + 1 + 16 + 48 + 2 == 268
    assert X.renders_upper([{"block": "c1a", "c1a_budget": 100}]) == 2 + 100 + 65 + 2
    assert X.renders_upper([{"block": "c1a", "c1a_budget": 300}]) == 65 + 2


def test_systematic_miss_stops_after_five_refusals_in_the_first_ten():
    assert not X.systematic_miss(["refused"] * 4 + ["ok"] * 6)
    assert X.systematic_miss(["refused", None, "refused", "ok", "refused", "refused", "refused"])
    assert not X.systematic_miss(["ok"] * 10 + ["refused"] * 5)


def test_replaying_returns_stored_values_checks_settings_then_renders():
    trials = [{"x": {"m/a": "1"}, "judge": {"A": 3.0}}, {"x": {"m/a": "2"}, "judge": {"A": 2.0}}]
    f = X.replaying(trials, ["m/a"], "A", lambda x: 9.0)
    assert f({("m", "a"): "1"}) == 3.0 and f({("m", "a"): "2"}) == 2.0 and f({("m", "a"): "3"}) == 9.0
    assert f.state["i"] == 2
    g = X.replaying(trials, ["m/a"], "A", lambda x: 9.0)
    with pytest.raises(X.ReplayMismatch):
        g({("m", "a"): "5"})


def test_record_values_read_the_final_against_the_start_and_beside_rows():
    r = {"held": "B", "label": {"x": 1}, "fresh": {"final": {"judge": {"B": 9.0}}, "label": {"judge": {"B": 2.0}}},
         "step1": {"trials": [{"judge": {"B": 4.0}}], "checkpoints": {"100": {"judge": {"B": 3.2}},
                                                                         "200": {"judge": {"B": 2.4}}}},
         "source_best_judge": {"B": 3.0}, "s_judge": {"B": 5.0}}
    v = X.record_values(r)
    assert math.isclose(v["primary"], math.log(0.5)) and math.isclose(v["vs_stored_label"], math.log(2 / 3))
    assert math.isclose(v["vs_S"], math.log(0.4)) and math.isclose(v["held_gain_at_100"], math.log(0.8))
    assert math.isclose(v["held_gain_at_200"], math.log(0.6))
    assert X.record_values(dict(r, label=None)) is None
    assert X.record_values(dict(r, fresh={"label": {"judge": {"B": float("nan")}}})) is None


def test_the_search_is_a_render_command_and_the_rest_are_not():
    assert any(re.search(p, "python -u -m learn.full_controls_c2 c2-search --shard 0/3") for p in LO.RENDERS)
    for cmd in ("c2-draw", "c2-report"):
        assert not any(re.search(p, f"python -m learn.full_controls_c2 {cmd}") for p in LO.RENDERS)


# --- the search on a stub renderer -------------------------------------------------------------------------------------

LISTS = {"pr12": {"leftMicType": ["3", "9"], "rightMicType": ["3", "8"]}}
SYNC_COST = {"v": 0.0}                     # a canonical change in step 2 that sounds, when set (its raw path)


def _value(x):
    """The stub's distance: EQ band 3 near +4 and band 5 near -2 help, the left room on near -10 dB helps; a free delay
    sync costs SYNC_COST."""
    v = 2.0 + (float(x[("pr12EQ", "pr12EQBand3")]) - 4) ** 2 / 500 + (float(x[("pr12EQ", "pr12EQBand5")]) + 2) ** 2 / 500
    if str(x.get(("cabParameters", "leftRoomActive"))).lower() == "true":
        v += (float(x[("cabParameters", "leftRoomMicLevel")]) + 10) ** 2 / 1000 - 0.05
    if str(x.get(("delay", "delaySync"))) == "0":
        v += SYNC_COST["v"]
    return v


def _stub(tmp_path, monkeypatch, n=1, miss=(), offsets=(), sync_cost=0.0, fresh_nan=False, peak=None):
    """cmd_search on stub audio and a stub renderer; `offsets`: render processes (1 on) whose renders read higher."""
    np = pytest.importorskip("numpy")
    from learn import arm_a_levers as L
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import pretrain_set as PS
    from learn import song_bank as B

    S = full_start("pr12")
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda k: {})
    monkeypatch.setattr(LO, "_wait_cap", lambda *a: None)
    monkeypatch.setattr(PS, "free_gb", lambda: 1e9)
    monkeypatch.setattr(PS, "TRIM_S", 0.0)
    monkeypatch.setattr(PS, "SEC_S", 1.0)
    monkeypatch.setattr(PS, "SR", 4)
    monkeypatch.setattr(PS, "section_audio", lambda path, start: np.zeros(4))
    monkeypatch.setattr(B, "measure", lambda a: np.zeros(4))
    monkeypatch.setattr(P, "real_amp_track", lambda sd, track, start: np.zeros(4))
    monkeypatch.setattr(L, "menu_S", lambda: {"pr12": {"clean": (0, S)}})
    monkeypatch.setattr(C, "mic_lists", lambda: LISTS)
    monkeypatch.setitem(SYNC_COST, "v", sync_cost)
    calls = {"n": 0, "procs": 0}

    class R:
        def __init__(self, off):
            self.off = off

        def render(self, di, sel, x):
            assert C.SPRING_KEY not in x
            calls["n"] += 1
            return np.full(4, _value(x) + self.off)

        def close(self):
            pass

    def new():
        calls["procs"] += 1
        return R(0.5 if calls["procs"] in offsets else 0.0)

    def fresh(make, di, sel, xp, x):                                            # fresh_nan: a final J0 refuses
        calls["n"] += 2
        return np.full(4, math.nan if fresh_nan else _value(x))
    monkeypatch.setattr(CB, "new_renderer", new)
    if peak is not None:
        from learn import arm_a_mega53 as A
        monkeypatch.setattr(A, "peak_dbfs", lambda y, trim_s=0.0: peak)
    monkeypatch.setattr(AM, "fresh_render", fresh)
    monkeypatch.setattr(K, "judge", lambda ref, y, di, lag: {"A": float(y[0]), "B": float(y[0]) + 0.5})
    label = LO.sdict(S)
    v0 = _value(S)
    rows = []
    for i in range(n):
        unit = f"goat/u{i}"
        src = tmp_path / "src" / f"u{i}.json"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(json.dumps({"unit": unit, "amp": "pr12", "select": 0, "search": "A", "held": "B", "lag": 0,
                                   "label": label, "rig": "r", "di": "d", "s_judge": {"A": v0 + 0.1, "B": v0 + 0.6},
                                   "best": {"settings": label, "render_sha256": "s", "peak_dbfs": -20.0,
                                            "judge": {"A": v0 * (1.1 if i in miss else 1.0), "B": v0 + 0.5}}}))
        rows.append({"set": "goat", "block": "goat", "key": f"{unit}|pr12", "unit": unit, "amp": "pr12", "cls": "clean",
                     "cluster": f"i{i}", "real_out": False, "source": str(src),
                     "prt": {"di_path": "", "start_s": 0.0, "sd": "", "track": ""}})
    (tmp_path / "c2").mkdir(exist_ok=True)
    (tmp_path / "c2" / "records.json").write_text(json.dumps({"records": rows, "left_out": []}))
    return rows, calls


def _out(tmp_path, r):
    root, sub = X.OUT_DIRS[r["set"]]
    return tmp_path / root / sub / f"{r['key'].replace('/', '__')}.json"


def test_c2_search_chains_c1a_then_stages_a_and_b_with_no_effect_stage(tmp_path, monkeypatch, capsys):
    import argparse
    from learn import knob_ceiling as K
    (row,), calls = _stub(tmp_path, monkeypatch)
    used = {"coord": [], "knob": []}
    real_coord, real_knob = K.coord_search, K.knob_search

    def coord(dims, x0, f, budget, seed, **kw):
        used["coord"].append((len(dims), budget, seed))
        return real_coord(dims, x0, f, budget, seed, **kw)

    def knob(dims, x0, f, budget, seed, **kw):
        used["knob"].append((len(dims), budget, seed, kw.get("shares")))
        return real_knob(dims, x0, f, budget, seed, **kw)
    monkeypatch.setattr(K, "coord_search", coord)
    monkeypatch.setattr(K, "knob_search", knob)
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, row).read_text())
    assert [(b, s) for _, b, s in used["coord"][:2]] == [(X.BUDGET, F.SEED), (C.BUDGET_ROOMS, C.SEED)]   # knob_search
    assert not any(b == X.BUDGET for _, b, _ in used["coord"][2:])                       # calls coord_search itself
    assert [(b, s, sh) for _, b, s, sh in used["knob"]] == [(C.BUDGET_MICS_EQ, C.SEED + 1, C.STAGE_B_SHARES)]
    assert calls["procs"] == 2                                                  # step 1's process and step 2's
    assert r["step1"]["start_gate"] == "on" and r["step1"]["start"]["value"] == pytest.approx(_value(full_start()))
    assert r["step1"]["start_settings"]["parameters/gateActive"] == "true"
    assert r["step1"]["start_settings"]["parameters/gateThreshold"] == F.GATE_ON_DB
    assert r["step2"]["start_kind"] == "canonical" and r["step2"]["stage_a_changed"]["rooms_on"] == 1
    assert r["label"]["cabParameters/leftRoomActive"] == "true"
    assert float(r["label"]["pr12EQ/pr12EQBand3"]) != 0 and float(r["label"]["pr12EQ/pr12EQBand5"]) != 0
    assert X.known_problems(r["label"], "pr12") == [] and r["known_keys"] == X.known_keys("pr12")
    assert "spring/springOn" not in r["label"] and "effects" not in r and "effect_kept" not in r
    assert set(r["step1"]["searched_keys"]) < set(r["searched_keys"])
    assert "cabParameters/leftMicType" in r["searched_keys"] and "reverb/reverbMix" not in r["searched_keys"]
    want = (1 + r["step1"]["evaluations"]) + (1 + len(r["step2"]["trace"])) + 2
    out = capsys.readouterr().out
    assert f"C2-SEARCH DONE 0/1: {want} renders" in out and calls["n"] == want
    assert r["fresh"]["final"]["judge"]["A"] < r["step1"]["start"]["value"] and not r["drift"]
    X.cmd_search(argparse.Namespace(shard=(0, 1)))                                 # resume: skipped
    assert "C2-SEARCH DONE 0/1: 0 renders" in capsys.readouterr().out


def test_c2_search_refuses_a_step_1_miss_neither_start_explains_and_continues(tmp_path, monkeypatch, capsys):
    import argparse
    rows, _ = _stub(tmp_path, monkeypatch, n=2, miss={0})
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    bad, good = (json.loads(_out(tmp_path, r).read_text()) for r in rows)
    assert bad["step1"]["start_gate"] == "refused" and bad["label"] is None and "gate_off_value" in bad["refused"]
    assert good["step1"]["start_gate"] == "on" and good["label"] is not None
    assert "'refused': 1" in capsys.readouterr().out


def test_c2_step_2_runs_from_the_raw_label_when_only_its_canonical_form_missed(tmp_path, monkeypatch):
    import argparse
    (row,), _ = _stub(tmp_path, monkeypatch, sync_cost=0.1)
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, row).read_text())
    assert r["step2"]["start_kind"] == "raw_after_miss" and r["label"]["delay/delaySync"] == "1"
    m = r["step2"]["first_start_miss"]
    assert not F.within(m["value"], m["ref_value"]) and "raw_value" not in m


def test_c2_keeps_step_1s_label_when_step_2_is_refused(tmp_path, monkeypatch):
    import argparse
    (row,), calls = _stub(tmp_path, monkeypatch, offsets={2, 3})
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, row).read_text())
    assert r["step2"]["start_kind"] == "refused" and "raw_value" in r["step2"]["refused"]
    assert r["label"] == r["step1"]["best"]["settings"] and r["searched_keys"] == r["step1"]["searched_keys"]
    assert calls["procs"] == 3


def test_c2_falls_back_to_step_1s_best_when_the_final_is_unusable(tmp_path, monkeypatch):
    import argparse
    (row,), _ = _stub(tmp_path, monkeypatch, fresh_nan=True)
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, row).read_text())
    assert r["fallback_stage"] == "step1" and r["fallback_reason"].startswith("the final unusable: non-finite")
    assert r["label"] == r["step1"]["best"]["settings"] and r["searched_keys"] == r["step1"]["searched_keys"]
    assert r["fresh"]["label"] == r["step2"]["start"] and "final_fresh" in r["peaks"]
    assert X.record_values(r) is not None


def test_c2_falls_back_to_the_start_when_step_1s_best_is_unusable_too(tmp_path, monkeypatch):
    import argparse
    (row,), _ = _stub(tmp_path, monkeypatch, fresh_nan=True, offsets={2, 3})
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, row).read_text())
    assert r["step2"]["start_kind"] == "refused" and r["fallback_stage"] == "start"
    assert r["label"] is None and r["searched_keys"] is None and X.record_values(r) is None


def test_c2_refuses_a_record_whose_start_is_unusable_and_flags_quiet_labels(tmp_path, monkeypatch, capsys):
    import argparse
    (row,), calls = _stub(tmp_path, monkeypatch, peak=-58.0)
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, row).read_text())
    assert r["step1"]["start_gate"] == "refused" and "floor" in r["refused"]["unusable"] and r["label"] is None
    assert calls["n"] == 2                                                       # the priming and the first evaluation
    assert "renders so far 2" in capsys.readouterr().out
    (row,), _ = _stub(tmp_path / "q", monkeypatch, peak=-55.0)
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    q = json.loads(_out(tmp_path / "q", row).read_text())
    assert q["quiet"] is True and q["fallback_stage"] is None and q["peaks"]["start"] == -55.0


def test_c2_report_reads_the_search_outputs_by_block(tmp_path, monkeypatch, capsys):
    import argparse
    pytest.importorskip("scipy")
    rows, _ = _stub(tmp_path, monkeypatch, n=3, miss={2})
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    capsys.readouterr()
    X.cmd_report(None)
    rep = json.loads((tmp_path / "c2" / "report.json").read_text())
    g = rep["goat"]
    assert g["written"] == 3 and g["drawn"] == 3 and rep["bks1"]["written"] == 0
    assert g["step1_starts"] == {"on": 2, "off_after_miss": 0, "refused": 1} and g["refused"][0]["unit"] == "goat/u2"
    assert g["step2_starts"]["canonical"] == 2
    assert g["rows"]["records"] == 2 and g["rows"]["all"]["primary"]["mean"] < 0
    assert g["rows"]["all"]["counts"]["rooms_on"] == 2 and g["rows"]["left_out_of_primary"][0]["why"] == "refused"
    printed = json.loads(capsys.readouterr().out)
    assert printed["goat"]["written"] == 3


def _c1a_output(tmp_path, budget=100, nudge=None):
    """A C1a output for the stub's label: C1a's own search run on the stub's distance (zero renders), as C1a stores it.
    nudge: an evaluation index whose stored setting is altered (a replay that is not exact)."""
    from learn import knob_ceiling as K
    label = LO.sdict(full_start("pr12"))
    start = F.c1a_start(label, "pr12")
    dims = F.c1a_space("pr12", start)
    names = [d.name for d in dims]
    trials = []

    def f(x):
        v = _value(x)
        trials.append({"x": {nm: x.get(tuple(nm.rsplit("/", 1))) for nm in names}, "judge": {"A": v, "B": v + 0.5}})
        return v
    K.coord_search(dims, start, f, budget, F.SEED, cats="levels", canon=F.make_canon("pr12"))
    if nudge is not None:
        trials[nudge]["x"][names[0]] = "11.5"
    p = tmp_path / "c1a-out.json"
    p.write_text(json.dumps({"start_settings": LO.sdict(start), "searched_keys": names, "trials": trials, "search": "A",
                             "start_gate": "on", "start": {"value": trials[0]["judge"]["A"]}, "label": label}))
    return p, trials


def _with_c1a(tmp_path, rows, budget=100, nudge=None):
    p, trials = _c1a_output(tmp_path, budget, nudge)
    c = dict(rows[-1], set="bks", block="c1a", key="set5/x@1#y|pr12", unit="set5/x@1#y", c1a_output=str(p),
             c1a_budget=budget)
    src = json.loads(open(rows[-1]["source"]).read())
    src["unit"] = c["unit"]
    q = tmp_path / "src" / "c1a-src.json"
    q.write_text(json.dumps(src))
    c["source"] = str(q)
    recs = json.loads((tmp_path / "c2" / "records.json").read_text())
    recs["records"].append(c)
    (tmp_path / "c2" / "records.json").write_text(json.dumps(recs))
    return c, trials


def test_c2_continues_c1as_search_to_200_exactly_as_one_run_would(tmp_path, monkeypatch, capsys):
    import argparse
    (row,), calls = _stub(tmp_path, monkeypatch)
    c, trials = _with_c1a(tmp_path, [row])
    assert X.replay_check(json.loads(open(c["c1a_output"]).read()), "pr12") == ([], F.incumbent_at(
        [t["judge"]["A"] for t in trials], len(trials)))
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    g, r = (json.loads(_out(tmp_path, x).read_text()) for x in (row, c))
    assert r["step1"]["curve"] == g["step1"]["curve"]                            # the continuation is the 200 run
    assert r["step1"]["best"]["settings"] == g["step1"]["best"]["settings"]
    cont = r["step1"]["continuation"]
    assert cont["stored"] == 100 and cont["replayed"] == 100 and cont["start_check"]["ok"]
    assert cont["rendered"] == r["step1"]["evaluations"] - 100
    assert r["label"] == g["label"] and r["block"] == "c1a"
    out = capsys.readouterr().out
    total = int(re.search(r"C2-SEARCH DONE 0/1: (\d+) renders", out).group(1))
    want_g = (1 + g["step1"]["evaluations"]) + (1 + len(g["step2"]["trace"])) + 2
    want_c = 2 + cont["rendered"] + (1 + len(r["step2"]["trace"])) + 2
    assert total == want_g + want_c == calls["n"] and "'continued': 1" in out


def test_c2_takes_a_subset_records_200_incumbent_at_zero_step_1_renders(tmp_path, monkeypatch, capsys):
    import argparse
    (row,), calls = _stub(tmp_path, monkeypatch)
    c, _ = _with_c1a(tmp_path, [row], budget=300)
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    g, r = (json.loads(_out(tmp_path, x).read_text()) for x in (row, c))
    assert r["step1"]["curve"] == g["step1"]["curve"] and r["step1"]["continuation"]["rendered"] == 0
    assert r["step1"]["continuation"]["start_check"] is None and r["step1"]["best"]["replayed"] in (True, False)


def test_c2_refuses_a_continuation_whose_replay_is_not_exact(tmp_path, monkeypatch):
    import argparse
    (row,), _ = _stub(tmp_path, monkeypatch)
    c, _ = _with_c1a(tmp_path, [row], nudge=5)
    assert X.replay_check(json.loads(open(c["c1a_output"]).read()), "pr12")[0] == ["evaluation 5 differs"]
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, c).read_text())
    assert r["refused"] == {"replay_mismatch": 5} and r["label"] is None


def test_c2_resumes_at_step_2_from_the_saved_step_1(tmp_path, monkeypatch, capsys):
    import argparse
    (row,), calls = _stub(tmp_path, monkeypatch)
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    first = json.loads(_out(tmp_path, row).read_text())
    assert (_out(tmp_path, row).parent / "step1" / _out(tmp_path, row).name).exists()
    _out(tmp_path, row).unlink()                                                # a stop after step 1
    capsys.readouterr()
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    again = json.loads(_out(tmp_path, row).read_text())
    out = capsys.readouterr().out
    assert again["label"] == first["label"] and "'resumed': 1" in out
    assert f"C2-SEARCH DONE 0/1: {1 + len(again['step2']['trace']) + 2} renders" in out


def test_c2_stops_a_shard_on_systematic_start_misses(tmp_path, monkeypatch):
    import argparse
    _stub(tmp_path, monkeypatch, n=7, miss={0, 1, 2, 3, 4})
    with pytest.raises(SystemExit, match="SYSTEMATIC MISS"):
        X.cmd_search(argparse.Namespace(shard=(0, 1)))


def test_c2_refuses_a_continuation_whose_start_is_near_silent(tmp_path, monkeypatch):
    import argparse
    (row,), calls = _stub(tmp_path, monkeypatch, peak=-58.0)
    c, _ = _with_c1a(tmp_path, [row])
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, c).read_text())
    assert r["label"] is None and "floor" in r["refused"]["unusable"]
