"""C1b (docs/full-controls-plan.md, "C1b in detail"): learn/full_controls_c1b.py."""
import json
import math
import re

import pytest

pytest.importorskip("numpy")

from learn import every_control as E  # noqa: E402
from learn import full_controls as F  # noqa: E402
from learn import full_controls_c1b as C  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import knob_ceiling2 as K2  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import pipeline_fix as P  # noqa: E402


def full_start(amp="pr12"):
    """A whole Morgan setting from the table's neutral values: the amp EQ and every section on, dry, both cabs on."""
    x = {c.path: c.neutral for c in E.table("morgan") if c.neutral is not None and c.module}
    x.update(K2.HELD_ON)
    for k in (("ampParameters", "sectionActive"), ("cabParameters", "sectionActive"), ("fxParameters", "sectionActive"),
              (f"{amp}EQ", f"{amp}EQActive"), ("cabParameters", "leftCabActive"), ("cabParameters", "rightCabActive")):
        x[k] = "true"
    x[("delay", "delaySync")] = "1"                                             # as S stores it (inert while off)
    x[("cabParameters", "leftMicType")], x[("cabParameters", "rightMicType")] = "0", "3"
    if amp in K2.SPRING:
        x[next(iter(K2.SPRING[amp][0]))] = "0"
    return x


# --- records ----------------------------------------------------------------------------------------------------------

def test_c1b_records_carry_c1a_records_and_name_those_left_out():
    base = {"set": "n12", "unit": "u", "amp": "pr12", "cls": "clean", "cluster": "c", "real_out": False, "prt": {}}
    c1a = [dict(base, key=k) for k in ("a", "b", "c", "d")]
    outs = {"a": {"label": {"x": 1}, "_path": "/p/a"}, "b": {"label": None, "_path": "/p/b"},
            "c": {"refused": {}, "label": None, "_path": "/p/c"}}
    recs, left = C.c1b_records(c1a, outs)
    assert [r["key"] for r in recs] == ["a"] and recs[0]["source"] == "/p/a" and recs[0]["measurement_only"]
    assert {(x["key"], x["why"]) for x in left} == {("b", "C1a label fell back"), ("c", "refused in C1a"),
                                                    ("d", "no C1a output")}
    bks = C.c1b_records([dict(base, key="e", set="bks")], {"e": {"label": {}, "_path": "/p/e"}})[0][0]
    assert bks["measurement_only"] is False


# --- the start, the spaces, the canonical form ------------------------------------------------------------------------

def test_make_canon_neutralises_off_rooms_and_sets_off_effects_and_free_sync():
    x = full_start()
    x[("cabParameters", "leftRoomMicLevel")] = "-30"                            # the room is off
    x[("reverb", "reverbMix")] = "0.9"                                          # the reverb is off
    y = C.make_canon("pr12")(x)
    assert y[("cabParameters", "leftRoomMicLevel")] == "-6"
    assert y[("reverb", "reverbMix")] == K2.EFFECTS["reverb"][1][("reverb", "reverbMix")]
    assert y[("delay", "delaySync")] == "0"
    on = {**x, ("cabParameters", "leftRoomActive"): "true", ("reverb", "reverbActive"): "true"}
    z = C.make_canon("pr12")(on)
    assert z[("cabParameters", "leftRoomMicLevel")] == "-30" and z[("reverb", "reverbMix")] == "0.9"
    assert C.make_canon("pr12")(y) == y


def test_with_spring_reads_the_level_and_plugin_makes_it_real():
    x = full_start("pr12")
    assert C.with_spring(x, "pr12")[C.SPRING_KEY] == "false"
    x[("pr12Amp", "pr12Reverb")] = "0.3"
    assert C.with_spring(x, "pr12")[C.SPRING_KEY] == "true"
    assert C.SPRING_KEY not in C.with_spring(full_start("ac20"), "ac20")
    off = C.with_spring(full_start("pr12"), "pr12")
    off[("pr12Amp", "pr12Reverb")] = "0.2"                                      # canonical while off
    assert C.plugin(off, "pr12")[("pr12Amp", "pr12Reverb")] == "0" and C.SPRING_KEY not in C.plugin(off, "pr12")


def test_c1b_start_changes_nothing_that_sounds_and_raw_start_changes_nothing():
    lab = LO.sdict(full_start("pr12"))
    st = C.c1b_start(lab, "pr12")
    assert st[("delay", "delaySync")] == "0" and C.audible_change(st, lab, "pr12") == []
    raw = C.raw_start(lab, "pr12")
    assert {k: v for k, v in raw.items() if k != C.SPRING_KEY} == LO.tdict(lab)
    assert C.audible_change(raw, lab, "pr12") == []


def test_rooms_dims_on_two_cabs_and_on_one():
    x = full_start()
    names = [d.name for d in C.rooms_dims(x)]
    assert names == ["cabParameters/leftCabActive", "cabParameters/leftCabMicLevel", "cabParameters/leftRoomActive",
                     "cabParameters/leftRoomMicLevel", "cabParameters/rightRoomActive", "cabParameters/rightRoomMicLevel",
                     "cabParameters/rightCabPhase"]
    x[("cabParameters", "rightCabActive")] = "false"                           # one cab: no left switch, level or phase
    assert [d.name for d in C.rooms_dims(x)] == ["cabParameters/leftRoomActive", "cabParameters/leftRoomMicLevel"]
    lvl = next(d for d in C.rooms_dims(full_start()) if d.key == "leftRoomMicLevel")
    assert (lvl.kind, lvl.lo, lvl.hi) == ("cont", -40.0, 6.0)
    ph = next(d for d in C.rooms_dims(full_start()) if d.key == "rightCabPhase")
    assert ph.kind == "switch"


LISTS = {"pr12": {"leftMicType": ["3", "9"], "rightMicType": ["3", "8"]},
         "sw50r": {"leftMicType": ["3", "9", "0", "6"], "rightMicType": ["3", "5", "2"]},
         "ac20": {"leftMicType": ["3"], "rightMicType": ["4"]}}


def test_mics_eq_dims_are_the_cabs_on_short_list_mics_with_the_amp_eq():
    x = full_start("sw50r")
    dims = C.mics_eq_dims(x, "sw50r", LISTS)
    assert [d.name for d in dims[:2]] == ["cabParameters/leftMicType", "cabParameters/rightMicType"]
    assert dims[0].values == ("0", "3", "6", "9") and dims[1].values == ("2", "3", "5")       # the current mic kept
    assert {d.name for d in dims[2:]} == {d.name for d in K.eq_space("sw50r")} and len(dims) == 13
    x[("cabParameters", "leftCabActive")] = "false"
    assert C.mics_eq_dims(x, "sw50r", LISTS)[0].name == "cabParameters/rightMicType"
    pr = C.mics_eq_dims(full_start("pr12"), "pr12", LISTS)                         # the current "0" is not listed
    assert pr[0].values == ("0", "3", "9") and pr[1].values == ("3", "8")


@pytest.mark.parametrize("amp, spring", [("pr12", 7), ("sw50r", 4), ("ac20", None)])
def test_effect_plan_budgets_by_knobs(amp, spring):
    plan = C.effect_plan(amp)
    assert plan["reverb"][2] == 18 and plan["delay"][2] == 21 and plan["tremolo"][2] == 10
    assert "delay/delayTapeDrive" in [d.name for d in plan["delay"][1]]
    assert "tremolo/tremoloLevel" in [d.name for d in plan["tremolo"][1]]
    assert (plan["spring"][2] if spring else "spring" in plan) == (spring if spring else False)
    assert plan["reverb"][0] == ("reverb", "reverbActive") and all(d.kind != "switch" for d in plan["reverb"][1])


def test_effect_start_canonical_and_raw():
    dry = C.make_canon("pr12")(C.with_spring(full_start("pr12"), "pr12"))
    on = C.effect_start(dry, ("delay", "delayActive"), "pr12")
    assert on[("delay", "delayActive")] == "true" and on[("delay", "delaySync")] == "0"
    raw_dry = C.raw_start(LO.sdict(full_start("pr12")), "pr12")
    r = C.effect_start(raw_dry, ("delay", "delayActive"), "pr12", raw=True)
    assert r[("delay", "delayActive")] == "true" and r[("delay", "delaySync")] == "0"
    assert all(r[k] == v for k, v in K2.EFFECTS["delay"][1].items())
    assert r[("tremolo", "tremoloSync")] == raw_dry[("tremolo", "tremoloSync")]       # another effect untouched
    assert r[("delay", "delayTapeDrive")] == "0"
    t = C.effect_start({**raw_dry, ("tremolo", "tremoloLevel"): "0.9"}, ("tremolo", "tremoloActive"), "pr12", raw=True)
    assert t[("tremolo", "tremoloLevel")] == "0.5"
    sp = C.effect_start(raw_dry, C.SPRING_KEY, "pr12", raw=True)
    assert sp[C.SPRING_KEY] == "true" and sp[("pr12Amp", "pr12Reverb")] == "0.2"


# --- the keep rule, the choice, the ablations, the flags --------------------------------------------------------------

def test_passes_and_choose():
    assert C.KEEP_MARGIN == 0.02
    assert C.passes(2.0 * math.exp(-0.021), 2.0) and not C.passes(2.0 * math.exp(-0.019), 2.0)
    assert not C.passes(float("nan"), 2.0) and not C.passes(1.0, 0.0)
    dry = 2.0
    assert C.choose({"reverb": 1.9, "delay": 1.8, "tremolo": 1.99}, dry) == "delay"
    assert C.choose({"tremolo": 1.99}, dry) is None and C.choose({}, dry) is None


def test_ablations_reset_their_own_keys_and_effects_reset_is_the_dry_best():
    st = C.make_canon("pr12")(C.with_spring(full_start(), "pr12"))
    final = {**st, ("cabParameters", "leftRoomActive"): "true", ("cabParameters", "leftMicType"): "5",
             ("pr12EQ", "pr12EQBand2"): "3", ("reverb", "reverbActive"): "true", C.PHASE_KEY: "true"}
    dry = {**final, ("reverb", "reverbActive"): "false"}
    ab = C.ablation_settings(final, st, dry, "pr12")
    assert set(ab) == set(C.ABLATIONS)
    assert ab["rooms_reset"][("cabParameters", "leftRoomActive")] == "false"
    assert ab["rooms_reset"][C.PHASE_KEY] == st[C.PHASE_KEY] != "true"               # the phase is stage A's too
    assert ab["mics_eq_reset"][C.PHASE_KEY] == "true"
    assert ab["rooms_reset"][("cabParameters", "leftMicType")] == "5" and ab["rooms_reset"][("reverb", "reverbActive")] == "true"
    m = ab["mics_eq_reset"]
    assert m[("cabParameters", "leftMicType")] == "0" and m[("pr12EQ", "pr12EQBand2")] == st[("pr12EQ", "pr12EQBand2")]
    assert m[("cabParameters", "leftRoomActive")] == "true"
    assert ab["effects_reset"] == dry


def test_drift_and_nonfinite_ablations():
    assert C.drifted(-3.0, -14.0) and not C.drifted(-3.0, -12.0) and not C.drifted(None, -20.0)
    rs = [{"unit": "u1", "held": "B", "fresh": {"ablations": {"rooms_reset": {"judge": {"B": 1.0}},
                                                               "mics_eq_reset": {"judge": {"B": float("inf")}}}}},
          {"unit": "u2", "held": "A", "fresh": {"ablations": {"effects_reset": {"judge": {"A": 0.0}}}}}]
    assert C.nonfinite_ablations(rs) == [("u1", "mics_eq_reset"), ("u2", "effects_reset")]


# --- the rows ----------------------------------------------------------------------------------------------------------

def done(cluster, cls, c1a_h, fin_h, abl=None, kept=None, held="B", mics=False):
    j = lambda v: {"A": 9.0, "B": v} if held == "B" else {"A": v, "B": 9.0}          # noqa: E731
    return {"cluster": cluster, "unit": f"u-{cluster}", "cls": cls, "held": held, "label": {}, "c1a_fresh_best": j(c1a_h),
            "fresh": {"final": {"judge": j(fin_h)},
                      "ablations": {a: {"judge": j(fin_h * (abl or {}).get(a, 1.0))} for a in C.ABLATIONS}},
            "effect_kept": kept, "mics_changed": mics}


def test_report_rows_read_the_held_half_with_both_weightings():
    rs = [done("d1", "clean", 4.0, 3.0, abl={"effects_reset": 1.1}, kept="reverb", mics=True),
          done("d2", "crunch", 4.0, 4.0), done("d3", "clean", 2.0, 1.0, held="A", kept="reverb")]
    out = C.report_rows(rs, lambda df: 2.0, P.clustered)
    p = out["all"]["primary"]
    assert math.isclose(p["mean"], (math.log(0.75) + 0.0 + math.log(0.5)) / 3) and p["clusters"] == 3
    assert p["band_weighted"]["clusters"] == 3 and math.isclose(p["band_weighted"]["per_cluster"]["d3"], math.log(0.5))
    assert math.isclose(out["all"]["ablations"]["effects_reset"]["mean"], math.log(1.1) / 3)
    assert out["all"]["effects_kept"] == {"reverb": 2} and out["all"]["mics_changed"] == 1
    assert out["crunch"]["records"] == 1 and out["clean"]["effects_kept"] == {"reverb": 2}
    assert C.report_rows([dict(rs[0], label=None)], lambda df: 2.0, P.clustered)["records"] == 0
    broken = dict(rs[0], c1a_fresh_best={"A": 9.0, "B": float("nan")})
    assert C.report_rows([broken], lambda df: 2.0, P.clustered)["records"] == 0


def test_the_search_is_a_render_command_and_the_rest_are_not():
    assert any(re.search(p, "python -u -m learn.full_controls_c1b c1b-search --shard 0/3") for p in LO.RENDERS)
    for cmd in ("c1b-draw", "c1b-report"):
        assert not any(re.search(p, f"python -m learn.full_controls_c1b {cmd}") for p in LO.RENDERS)


# --- the search on a stub renderer -------------------------------------------------------------------------------------

SYNC_COST = {"v": 0.0}                     # a canonical change that sounds, when set (the raw path)


def _value(x):
    """The stub's distance: the left room on near -10 dB helps, EQ band 3 near +4 helps, the reverb on near mix 0.5
    helps a lot; a free delay sync costs SYNC_COST."""
    v = 2.0 + (float(x[("pr12EQ", "pr12EQBand3")]) - 4) ** 2 / 500
    if str(x.get(("cabParameters", "leftRoomActive"))).lower() == "true":
        v += (float(x[("cabParameters", "leftRoomMicLevel")]) + 10) ** 2 / 1000 - 0.05
    if str(x.get(("reverb", "reverbActive"))).lower() == "true":
        v += -0.2 + (float(x[("reverb", "reverbMix")]) - 0.5) ** 2
    if str(x.get(("delay", "delaySync"))) == "0":
        v += SYNC_COST["v"]
    return v


def _stub(tmp_path, monkeypatch, n=1, miss=(), sync_cost=0.0, fresh_offset=0.0, full=None, value=None):
    np = pytest.importorskip("numpy")
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import pretrain_set as PS
    from learn import song_bank as B

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
    monkeypatch.setitem(SYNC_COST, "v", sync_cost)
    monkeypatch.setattr(C, "mic_lists", lambda: LISTS)
    full = full or full_start
    value = value or _value
    calls = {"n": 0, "procs": 0}

    class R:
        def render(self, di, sel, x):
            assert C.SPRING_KEY not in x                                        # the plugin gets real settings
            calls["n"] += 1
            return np.full(4, value(x))

        def close(self):
            pass

    def new():
        calls["procs"] += 1
        return R()

    def fresh(make, di, sel, xp, x):                                            # fresh_offset: a process position
        calls["n"] += 2
        return np.full(4, value(x) + fresh_offset)
    monkeypatch.setattr(CB, "new_renderer", new)
    monkeypatch.setattr(AM, "fresh_render", fresh)
    monkeypatch.setattr(K, "judge", lambda ref, y, di, lag: {"A": float(y[0]), "B": float(y[0]) + 0.5})
    label = LO.sdict(full("pr12"))
    v0 = value(LO.tdict(label))
    rows = []
    for i in range(n):
        unit = f"cap/u{i}"
        src = tmp_path / "c1a" / f"u{i}.json"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(json.dumps({"unit": unit, "amp": "pr12", "select": 0, "search": "A", "held": "B", "lag": 0,
                                   "label": label, "rig": "r", "di": "d",
                                   "best": {"judge": {"A": v0 * (1.1 if i in miss else 1.0), "B": v0 + 0.5}},
                                   "fresh": {"best": {"judge": {"A": v0, "B": v0 + 0.5}, "peak_dbfs": 6.0}}}))
        rows.append({"set": "n12", "key": f"{unit}|pr12", "unit": unit, "amp": "pr12", "cls": "clean", "cluster": f"c{i}",
                     "real_out": False, "measurement_only": True, "source": str(src),
                     "prt": {"di_path": "", "start_s": 0.0, "sd": "", "track": ""}})
    (tmp_path / "c1b").mkdir(exist_ok=True)
    (tmp_path / "c1b" / "records.json").write_text(json.dumps({"records": rows}))
    return rows, calls


def _out(tmp_path, r):
    root, sub = C.OUT_DIRS[r["set"]]
    return tmp_path / root / sub / f"{r['key'].replace('/', '__')}.json"


def test_c1b_search_runs_the_stages_keeps_a_clear_effect_and_counts_renders(tmp_path, monkeypatch, capsys):
    import argparse
    (row,), calls = _stub(tmp_path, monkeypatch)
    used = {"coord": [], "knob": []}
    real_coord, real_knob = K.coord_search, K.knob_search

    def coord(dims, x0, f, budget, seed, **kw):
        used["coord"].append((tuple(d.name for d in dims), budget))
        return real_coord(dims, x0, f, budget, seed, **kw)

    def knob(dims, x0, f, budget, seed, **kw):
        used["knob"].append((tuple(d.name for d in dims), budget, kw.get("shares")))
        return real_knob(dims, x0, f, budget, seed, **kw)
    monkeypatch.setattr(K, "coord_search", coord)
    monkeypatch.setattr(K, "knob_search", knob)
    C.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, row).read_text())
    assert r["start_kind"] == "canonical" and r["first_start_miss"] is None
    assert r["label"]["cabParameters/leftRoomActive"] == "true"                    # stage A turned the room on
    assert r["label"]["pr12EQ/pr12EQBand3"] != "0"                                 # stage B moved the EQ
    assert r["stage_a_settings"]["pr12EQ/pr12EQBand3"] == "0" and r["stage_b_settings"]["pr12EQ/pr12EQBand3"] != "0"
    assert r["stage_a_settings"]["cabParameters/leftRoomActive"] == "true"
    assert r["stage_a_changed"] == {"left_cab_off": False, "rooms_on": 1, "phase_flipped": False}
    assert r["mic_lists"] == LISTS["pr12"]
    assert r["effect_kept"] == "reverb" and r["label"]["reverb/reverbActive"] == "true"
    assert "spring/springOn" not in r["label"] and r["label"]["pr12Amp/pr12Reverb"] == "0"       # the plugin's settings
    assert "spring/springOn" not in r["searched_keys"] and "reverb/reverbMix" in r["searched_keys"]
    assert {"cabParameters/leftMicType", "pr12EQ/pr12EQBand3", "cabParameters/leftRoomMicLevel"} <= set(r["searched_keys"])
    assert r["effects"]["reverb"]["passed_in_process"] and "fresh" in r["effects"]["reverb"]
    assert not r["effects"]["tremolo"]["passed_in_process"] and "fresh" not in r["effects"]["tremolo"]
    assert r["fresh"]["ablations"]["effects_reset"].get("same_as_dry") and not r["drift"]
    assert calls["procs"] == 1 + len(C.effect_plan("pr12"))                         # each effect in its own process
    for name, (sw, dims, budget) in C.effect_plan("pr12").items():                # plain coord_search per effect
        assert (tuple(d.name for d in dims), budget) in used["coord"]
    (b,) = [u for u in used["knob"] if u[1] == C.BUDGET_MICS_EQ]
    assert b[2] == C.STAGE_B_SHARES and b[0][0] == "cabParameters/leftMicType"
    stage_ab = 1 + len(r["trace"])
    fx = sum(1 + v["renders"] for v in r["effects"].values())
    confirms = 2 * sum("fresh" in v for v in r["effects"].values())
    abl = 2 * sum(not (v.get("same_as_final") or v.get("same_as_dry")) for v in r["fresh"]["ablations"].values())
    want = stage_ab + 2 + fx + confirms + abl
    out = capsys.readouterr().out
    assert f"C1B-SEARCH DONE 0/1: {want} renders" in out and calls["n"] == want
    assert "starts {'canonical': 1, 'raw_after_miss': 0, 'refused': 0}" in out
    C.cmd_search(argparse.Namespace(shard=(0, 1)))                                 # resume: skipped
    assert "C1B-SEARCH DONE 0/1: 0 renders" in capsys.readouterr().out


def test_c1b_search_refuses_a_miss_neither_start_explains_and_continues(tmp_path, monkeypatch, capsys):
    import argparse
    rows, calls = _stub(tmp_path, monkeypatch, n=2, miss={0})
    C.cmd_search(argparse.Namespace(shard=(0, 1)))
    bad, good = (json.loads(_out(tmp_path, r).read_text()) for r in rows)
    assert bad["start_kind"] == "refused" and bad["label"] is None and "raw_value" in bad["refused"]
    assert good["start_kind"] == "canonical" and good["label"] is not None
    assert "starts {'canonical': 1, 'raw_after_miss': 0, 'refused': 1}" in capsys.readouterr().out


def test_c1b_search_runs_from_the_raw_label_when_only_the_canonical_form_missed(tmp_path, monkeypatch):
    import argparse
    (row,), calls = _stub(tmp_path, monkeypatch, sync_cost=0.1)
    C.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, row).read_text())
    assert r["start_kind"] == "raw_after_miss" and r["start_settings"]["delay/delaySync"] == "1"
    assert r["label"] is not None and r["label"]["delay/delaySync"] == "1"           # nothing canonicalised on the raw path
    assert r["effect_kept"] == "reverb"
    m = r["first_start_miss"]
    assert not F.within(m["value"], m["ref_value"]) and "raw_value" not in m


def test_c1b_search_refuses_a_c1a_record_of_another_amp(tmp_path, monkeypatch):
    import argparse
    (row,), _ = _stub(tmp_path, monkeypatch)
    src = json.loads(open(row["source"]).read())
    src["amp"] = "sw50r"
    open(row["source"], "w").write(json.dumps(src))
    with pytest.raises(SystemExit, match="does not fit"):
        C.cmd_search(argparse.Namespace(shard=(0, 1)))


def test_c1b_keeps_an_effect_on_fresh_against_fresh_not_against_the_in_process_dry(tmp_path, monkeypatch):
    import argparse
    (row,), _ = _stub(tmp_path, monkeypatch, fresh_offset=0.5)
    C.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, row).read_text())
    assert r["effect_kept"] == "reverb"                                          # fresh wet against fresh dry passes
    wet, dry = r["effects"]["reverb"]["fresh"]["judge"]["A"], r["fresh"]["dry"]["judge"]["A"]
    assert C.passes(wet, dry) and not C.passes(wet, r["stage_b"]["judge"]["A"])


def test_c1b_report_reads_the_search_outputs(tmp_path, monkeypatch, capsys):
    import argparse
    pytest.importorskip("scipy")
    rows, _ = _stub(tmp_path, monkeypatch, n=3, miss={2})
    C.cmd_search(argparse.Namespace(shard=(0, 1)))
    capsys.readouterr()
    C.cmd_report(None)
    rep = json.loads((tmp_path / "c1b" / "report.json").read_text())
    n12 = rep["n12"]
    assert rep["keep_margin"] == C.KEEP_MARGIN
    assert n12["starts"] == {"canonical": 2, "raw_after_miss": 0, "refused": 1} and n12["refused"][0]["unit"] == "cap/u2"
    assert n12["rows"]["records"] == 2 and n12["rows"]["all"]["effects_kept"] == {"reverb": 2}
    assert n12["drift"] == {"main": 0, "real_out": 0} and n12["nonfinite_ablations"] == []
    assert n12["rows"]["all"]["primary"]["mean"] < 0                                   # the stub's gains, on the held half
    printed = json.loads(capsys.readouterr().out)["n12"]
    assert printed["starts"]["refused"] == 1 and printed["effects_kept"] == {"reverb": 2}


def test_stage_a_turning_the_left_cab_off_with_a_nonneutral_level(tmp_path, monkeypatch):
    """The review's repro: the left cab off on a label whose leftCabMicLevel is not the neutral 0 (as 20 of C1a's 38
    both-cab records store it); each stage's best is looked up in its canonical form."""
    import argparse

    def full(amp="pr12"):
        x = full_start(amp)
        x[("cabParameters", "leftCabMicLevel")] = "6"
        return x

    def value(x):
        return _value(x) - (0.3 if str(x.get(("cabParameters", "leftCabActive"))).lower() == "false" else 0.0)
    (row,), _ = _stub(tmp_path, monkeypatch, full=full, value=value)
    C.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, row).read_text())
    assert r["stage_a_settings"]["cabParameters/leftCabActive"] == "false"
    assert r["label"]["cabParameters/leftCabActive"] == "false"
    assert r["stage_a_changed"]["left_cab_off"] is True


def test_dry_start_problems_name_effects_spring_and_doubler():
    x = full_start("pr12")
    assert C.dry_start_problems(x, "pr12") == []
    x[("delay", "delayActive")] = "true"
    x[("parameters", "doublerActive")] = "true"
    x[("pr12Amp", "pr12Reverb")] = "0.1"
    assert C.dry_start_problems(x, "pr12") == ["delay/delayActive", "parameters/doublerActive", "pr12Amp/pr12Reverb"]
    assert C.dry_start_problems(full_start("ac20"), "ac20") == []


def test_c1b_search_refuses_a_wet_start(tmp_path, monkeypatch):
    import argparse

    def full(amp="pr12"):
        return {**full_start(amp), ("tremolo", "tremoloActive"): "true"}
    _stub(tmp_path, monkeypatch, full=full)
    with pytest.raises(SystemExit, match="must be dry"):
        C.cmd_search(argparse.Namespace(shard=(0, 1)))


def test_make_canon_sets_the_extra_knobs_of_an_off_effect_and_neutralises_a_lone_cabs_phase():
    x = full_start("pr12")
    x[("tremolo", "tremoloLevel")] = "0.9"
    x[("delay", "delayTapeDrive")] = "0.7"
    y = C.make_canon("pr12")(x)
    assert y[("tremolo", "tremoloLevel")] == "0.5" and y[("delay", "delayTapeDrive")] == "0"
    on = {**x, ("tremolo", "tremoloActive"): "true"}
    assert C.make_canon("pr12")(on)[("tremolo", "tremoloLevel")] == "0.9"
    one = {**x, ("cabParameters", "rightCabActive"): "false", ("cabParameters", "rightCabPhase"): "true"}
    assert C.make_canon("pr12")(one)[("cabParameters", "rightCabPhase")] == "false"


def test_searched_union_and_dropped():
    st = C.c1b_start(LO.sdict(full_start("pr12")), "pr12")
    u = C.searched_union(["pr12Amp/pr12Volume", "pr12EQ/pr12EQBand1"], st, st, "pr12", LISTS)
    assert "pr12Amp/pr12Volume" in u and "cabParameters/rightCabPhase" in u and "delay/delayTapeDrive" in u
    assert "reverb/reverbActive" in u and "spring/springOn" not in u and u == sorted(set(u))
    ok = done("d1", "clean", 4.0, 3.0)
    assert C.dropped([ok, dict(ok, unit="u2", label=None), dict(ok, unit="u3", c1a_fresh_best={"B": float("nan")})]) == [
        ("u2", "fallback label"), ("u3", "non-finite final or C1a best")]


def test_stage_a_changes_and_their_counts():
    st = full_start()
    xa = {**st, ("cabParameters", "leftCabActive"): "false", ("cabParameters", "leftRoomActive"): "true",
          ("cabParameters", "rightRoomActive"): "true", C.PHASE_KEY: "true"}
    assert C.stage_a_changes(xa, st) == {"left_cab_off": True, "rooms_on": 2, "phase_flipped": True}
    assert C.stage_a_changes(st, st) == {"left_cab_off": False, "rooms_on": 0, "phase_flipped": False}
    off = {**st, ("cabParameters", "leftCabActive"): "false"}
    assert C.stage_a_changes(off, off)["left_cab_off"] is False                     # already off at the start
    rs = [dict(done("d1", "clean", 4.0, 3.0), stage_a_changed={"left_cab_off": True, "rooms_on": 2, "phase_flipped": True}),
          dict(done("d2", "clean", 4.0, 3.0), stage_a_changed={"left_cab_off": False, "rooms_on": 1, "phase_flipped": False})]
    out = C.report_rows(rs, lambda df: 2.0, P.clustered)["all"]
    assert (out["left_cab_off"], out["rooms_on"], out["phase_flipped"]) == (1, 3, 1)
