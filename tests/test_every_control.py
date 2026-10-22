"""Every control, stages 0 and 1 (`learn/every_control.py`): the pure parts."""

import math
import pathlib
import re

import pytest

pytest.importorskip("numpy")

from learn import every_control as E  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import knob_ceiling2 as K2  # noqa: E402

MORGAN_DEFAULT = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/Default.xml")
TK_DEFAULT = pathlib.Path("/Library/Audio/Presets/Neural DSP/Tone King Imperial MKII/Default.xml")


# --- 0a: the table -------------------------------------------------------------------------------

@pytest.mark.parametrize("pack", ["morgan", "toneking"])
def test_table_lists_every_writable_manifest_control_once(pack):
    paths = [c.path for c in E.table(pack)]
    assert len(paths) == len(set(paths))
    assert sorted(paths) == sorted(E.manifest_writable(pack))


def test_morgan_counts_match_the_plan():
    today = {"pr12": 12, "sw50r": 17, "ac20": 14}
    add = {"pr12": 75, "sw50r": 74, "ac20": 73}
    for amp in E.MORGAN_AMPS:
        c = E.counts("morgan", amp)
        assert c["today"] == today[amp]
        assert sum(c.values()) - c["today"] == add[amp]
    assert sum(E.counts("toneking").values()) == 94


def test_todays_space_is_knob_ceilings():
    for amp in E.MORGAN_AMPS:
        mine = {c.path for c in E.table("morgan") if c.source == "searched" and c.amp in (None, amp)}
        assert mine == {(d.module, d.key) for d in K.space(amp)}


def test_never_and_rules_are_the_plans():
    never = {c.key for c in E.table("morgan") if c.source == "never"}
    assert never == {"name", "transpose", "leftRoomMicType", "rightRoomMicType", "leftChosenIRFilePath",
                     "rightChosenIRFilePath"}
    rules = {c.key for c in E.table("morgan") if c.source == "rule" and c.family == "time_effects"}
    assert rules == {"delaySync", "delayTempo", "delaySyncNote", "tremoloSync", "tremoloSyncNote"}
    tk_rules = {c.key for c in E.table("toneking") if c.source == "rule" and c.family == "time_effects"}
    assert tk_rules == set(E.TK_DELAY_RULES) and len(tk_rules) == 6
    screened = {c.key for c in E.table() if c.source == "screen"}
    assert screened == set(E.MORGAN_SCREEN) | set(E.TK_SCREEN)


def test_every_gate_names_a_listed_control_and_everything_writable_has_a_neutral():
    for pack in ("morgan", "toneking"):
        T = E.table(pack)
        paths = {c.path for c in T}
        for c in T:
            for g in c.gate:
                if g[0] in ("on", "off", "nonzero"):
                    assert g[1] in paths, (c.key, g)
                if g[0] == "amp":
                    assert g[1] in E.MORGAN_AMPS
            if c.source not in ("never", "stage0b"):
                assert c.neutral is not None, c.key


def test_neutrals_follow_knob_ceiling_2_where_it_declared_them():
    by = {c.path: c.neutral for c in E.table("morgan")}
    for m, (sw, knobs) in K2.PEDALS.items():
        assert by[(m, sw)] == "false"
        for k, v in knobs.items():
            assert by[(m, k)] == v
    for name, (sw, on, _) in K2.EFFECTS.items():
        for p, v in on.items():
            assert by[p] == v
    assert by[("pr12Amp", "pr12Dwell")] == K2.SPRING["pr12"][0][("pr12Amp", "pr12Dwell")]


def _state(path):
    from format.parser import parse_file
    from format.structured import build

    return {(p.module_path, p.key): p.value for p in build(parse_file(str(path))).parameters}


@pytest.mark.skipif(not MORGAN_DEFAULT.exists(), reason="Morgan's Default.xml is not installed")
def test_morgan_neutrals_otherwise_are_the_plugins_defaults():
    st = _state(MORGAN_DEFAULT)
    by = {c.path: c.neutral for c in E.table("morgan")}
    for p in [("parameters", "gateThreshold"), ("parameters", "doublerSpread"), ("tremolo", "tremoloLevel"),
              ("delay", "delayWidth"), ("delay", "delayPingPong"), ("delay", "delayTapeDrive"),
              ("delay", "delayTempo"), ("delay", "delaySyncNote"), ("tremolo", "tremoloSyncNote"),
              ("cabParameters", "leftRoomMicLevel"), ("cabParameters", "rightRoomMicLevel")]:
        assert by[p] == st[p], p
    for amp, knobs in E._AMP_DEFAULTS.items():
        for k, v in knobs.items():
            assert st[(f"{amp}Amp", k)] == v


@pytest.mark.skipif(not TK_DEFAULT.exists(), reason="Tone King's Default.xml is not installed")
def test_tone_king_defaults_are_the_plugins():
    st = {k: v for (m, k), v in _state(TK_DEFAULT).items() if not m}
    for k, v in E.TK_DEFAULTS.items():
        assert math.isclose(float(st[k]), float(v), abs_tol=1e-6), k


# --- the gates and the canonical form ------------------------------------------------------------

def _morgan_x():
    by = {c.path: c.neutral for c in E.table("morgan") if c.neutral is not None}
    return dict(by)


def test_an_off_pedal_is_masked_but_its_switch_is_scored():
    x = _morgan_x()
    x[("drive1", "drive1Active")] = "false"
    m = E.mask(x, "morgan", amp="pr12")
    assert m[("drive1", "drive1Active")] and not m[("drive1", "drive1Drive")]
    x[("drive1", "drive1Active")] = "true"
    assert E.mask(x, "morgan", amp="pr12")[("drive1", "drive1Drive")]


def test_other_amps_and_the_section_switches_mask():
    x = _morgan_x()
    m = E.mask(x, "morgan", amp="pr12")
    assert m[("pr12Amp", "pr12Volume")] and not m[("sw50rAmp", "sw50rVolume")]
    assert not m[("ac20EQ", "ac20EQBand3")]
    x[("pedalParameters", "sectionActive")] = "false"
    x[("compressor", "compressorActive")] = "true"
    assert not E.mask(x, "morgan", amp="pr12")[("compressor", "compressorLevel")]
    x[("", "selectedAmp")] = E.MORGAN_AMPS["sw50r"]
    assert E.mask(x, "morgan")[("sw50rAmp", "sw50rVolume")]


def test_cab_gates_spring_dwell_and_sync():
    x = _morgan_x()
    x[("cabParameters", "leftCabActive")] = "false"
    m = E.mask(x, "morgan", amp="pr12")
    assert not m[("cabParameters", "leftMicType")] and not m[("cabParameters", "rightCabPhase")]
    assert not m[("cabParameters", "rightCabPan")]                       # mono: one cab's pan is level only
    assert E.mask(x, "morgan", amp="pr12", mono=False)[("cabParameters", "rightCabPan")]
    x[("pr12Amp", "pr12Reverb")] = "0"
    assert not E.mask(x, "morgan", amp="pr12")[("pr12Amp", "pr12Dwell")]
    x[("pr12Amp", "pr12Reverb")] = "0.3"
    assert E.mask(x, "morgan", amp="pr12")[("pr12Amp", "pr12Dwell")]
    x[("delay", "delayActive")] = "true"
    x[("delay", "delaySync")] = "0"
    m = E.mask(x, "morgan", amp="pr12")
    assert m[("delay", "delayTime")] and not m[("delay", "delaySyncNote")]


def test_tone_king_channel_gates_the_other_channels_knobs():
    x = {c.path: c.neutral for c in E.table("toneking") if c.neutral is not None}
    x[("", "ampType")] = "1"
    m = E.mask(x, "toneking")
    assert m[("", "leadAmpTone")] and not m[("", "rhythmAmpBass")]
    x[("", "ampTremoloDepth")] = "0"
    assert E.mask(x, "toneking")[("", "ampTremoloSpeed")]                # audible at depth 0 (smoke)


def test_neutralise_matches_knob_ceiling_2s_canon_and_is_idempotent():
    x = _morgan_x()
    for m, (sw, knobs) in K2.PEDALS.items():
        x[(m, sw)] = "false"
        for k in knobs:
            x[(m, k)] = "0.97"
    x[("compressor", "compressorRelease")] = "true"
    x[("reverb", "reverbActive")] = "false"
    x[("reverb", "reverbMix")] = "0.9"
    y = E.neutralise(x, "morgan", amp="pr12")
    assert {k: y[k] for k in y if k[0] in K2.PEDALS} == {k: v for k, v in K2.canon_pedals(x).items() if k[0] in K2.PEDALS}
    assert y[("reverb", "reverbMix")] == K2.make_canon_effects("pr12")(x)[("reverb", "reverbMix")]
    assert E.neutralise(y, "morgan", amp="pr12") == y
    on = dict(x)
    on[("drive1", "drive1Active")] = "true"
    assert E.neutralise(on, "morgan", amp="pr12")[("drive1", "drive1Drive")] == "0.97"   # sounding: untouched


def test_tk_canon_makes_an_off_pedals_moves_free():
    x = E.tk_start({c.key: (c.neutral or "0") for c in E.table("toneking")})
    x[("", "drive1Active")] = "0"
    dims = [E.tk_dim("drive1Overdrive"), E.tk_dim("inputGain")]
    seen = []

    def f(y):
        seen.append(y)
        return abs(float(y[("", "inputGain")]) - 3.0)

    K.knob_search(dims, x, f, 40, 0, canon=E.tk_canon)
    assert all(y[("", "drive1Overdrive")] == E.TK_DEFAULTS["drive1Overdrive"] for y in seen)


# --- 0b: amp choice ------------------------------------------------------------------------------

def _cell(slug, amp, ks):
    return {"slug": slug, "amp": amp, "band": "b" + slug, "gain_class": "clean",
            "runs": {s: {"K_S": {"search": ks[s][0], "held": ks[s][1]}} for s in ("A", "B")}}


def test_amp_choice_reads_the_picked_amp_against_the_blind_mean():
    cells = [_cell("p", "pr12", {"A": (1.0, 2.0), "B": (3.0, 3.0)}),
             _cell("p", "sw50r", {"A": (2.0, 1.0), "B": (1.0, 1.0)}),
             _cell("p", "ac20", {"A": (3.0, 4.0), "B": (2.0, 2.0)})]
    (slug, band, cls, v), = E.amp_choice_rows(cells)
    a = math.log(2.0) - (math.log(2) + math.log(1) + math.log(4)) / 3        # A: pr12 picked
    b = math.log(1.0) - (math.log(3) + math.log(1) + math.log(2)) / 3        # B: sw50r picked
    assert math.isclose(v, (a + b) / 2)
    cells[0]["runs"]["B"] = {"skipped": "x"}
    (_, _, _, v2), = E.amp_choice_rows(cells)
    assert math.isclose(v2, a)


def test_reading_is_the_declared_rule():
    assert E.reading({"lo90": -0.2, "hi90": -0.01}) == "gain: enters"
    assert E.reading({"lo90": -0.2, "hi90": 0.01}).startswith("tie")
    assert E.reading({"lo90": 0.01, "hi90": 0.2}).startswith("worse")


# --- 0c: the screen ------------------------------------------------------------------------------

def test_screen_moves_and_plan():
    assert E.far(E.SCREEN_DIMS[("cabParameters", "leftCabPan")], "0") == "50"
    assert E.far(E.SCREEN_DIMS[("cabParameters", "leftCabPan")], "30") == "-50"
    assert E.far(E.SCREEN_DIMS[("cabParameters", "leftCabPhase")], "false") == "true"
    assert E.far(E.SCREEN_DIMS[("", "cab1Phase")], "1") == "0"
    assert E.far(E.SCREEN_DIMS[("parameters", "doublerSpread")], "6") == "20"
    mp, tp = E.screen_plan("morgan"), E.screen_plan("toneking")
    assert {w for _, w in mp if isinstance(w, tuple)} == {p for p in E.SCREEN_DIMS if p[0]}
    assert {w for _, w in tp if isinstance(w, tuple)} == {("", k) for k in E.TK_SCREEN}
    assert 3 * (len(mp) + 1) + 2 * (len(tp) + 1) == 60                    # with one priming render per cell


def test_screen_cells_and_bases():
    slugs = [f"s{i:02d}" for i in range(24)]
    cls = {s: ("crunch" if s in ("s05", "s17") else "clean") for s in slugs}
    cells = E.screen_cells(slugs, cls)
    assert cells[:3] == [("morgan", "s00", "pr12"), ("morgan", "s08", "sw50r"), ("morgan", "s16", "ac20")]
    assert cells[3:] == [("toneking", "s00", "clean"), ("toneking", "s05", "crunch")]
    x = {("cabParameters", "leftCabActive"): "false"}
    assert E.screen_base("cab", x, "morgan")[("cabParameters", "leftCabActive")] == "true"
    d = E.screen_base("delay", {}, "morgan")
    assert d[("delay", "delayActive")] == "true" and d[("delay", "delaySync")] == "0"


def test_invisible_rule():
    out = E.invisible({"a": [0.001, 0.004], "b": [0.001, 0.02], "c": []})
    assert out == {"a": True, "b": False, "c": False}


# --- stage 1: Morgan's groups --------------------------------------------------------------------

def _base(**kw):
    x = _morgan_x()
    x[("cabParameters", "leftCabActive")] = "true"
    x[("cabParameters", "rightCabActive")] = "true"
    for k, v in kw.items():
        m, key = k.split("__")
        x[(m, key)] = v
    return x


def test_group_plans():
    vis = set(E.SCREEN_DIMS)
    x, dims = E.group_plan("gate", _base(), vis)
    assert x[("parameters", "gateActive")] == "true" and x[("parameters", "gateThreshold")] == "-80"
    assert [d.key for d in dims] == ["gateThreshold"]
    x, dims = E.group_plan("doubler", _base(), set())
    assert x[("parameters", "doublerActive")] == "true" and dims == []           # spread invisible: 1 render
    assert E.group_plan("phase", _base(cabParameters__rightCabActive="false"), vis) is None
    assert E.group_plan("phase", _base(), set()) is None
    _, dims = E.group_plan("phase", _base(), {("cabParameters", "leftCabPhase")})
    assert [d.key for d in dims] == ["leftCabPhase"]
    assert E.group_plan("effects", _base(), vis) is None
    _, dims = E.group_plan("effects", _base(delay__delayActive="true"), set())
    assert [d.key for d in dims] == ["delayTapeDrive"]
    x, dims = E.group_plan("rooms", _base(cabParameters__rightCabActive="false"), vis)
    assert x[("cabParameters", "leftRoomActive")] == "true" and x[("cabParameters", "rightRoomActive")] == "false"
    assert not any(d.key.startswith("rightRoom") for d in dims)


def test_group_canon_only_touches_its_own_controls():
    x = _base(parameters__gateActive="false", parameters__gateThreshold="-20", drive1__drive1Active="false",
              drive1__drive1Drive="0.9")
    y = E.group_canon("gate", "pr12")(x)
    assert y[("parameters", "gateThreshold")] == "-80" and y[("drive1", "drive1Drive")] == "0.9"


def test_group_result_adopts_only_past_the_margin():
    base = {"A": 1.0, "B": 1.0}
    r = E.group_result(base, [{"A": 0.999, "B": 0.5}], "A", "B")
    assert not r["adopted"] and r["log_held"] == 0.0 and r["log_held_best"] < 0
    r = E.group_result(base, [{"A": 0.99, "B": 0.9}, {"A": 0.98, "B": 1.1}], "A", "B")
    assert r["adopted"] and math.isclose(r["log_held"], math.log(1.1))
    assert E.group_result(base, [], "A", "B")["log_held"] == 0.0


# --- Tone King ------------------------------------------------------------------------------------

def test_tk_space_and_dims():
    for c in E.table("toneking"):
        if c.source in ("tk_stage1", "screen"):
            assert c.key in E.TK_DIMS, c.key
    assert len(E.tk_space(set())) == 77 and len(E.tk_space(set(E.SCREEN_DIMS))) == 82
    assert E.tk_dim("cab1Active").values == ("0", "1")
    assert E.tk_dim("cab1MicIR").kind == "cat" and "16" not in E.tk_dim("cab1MicIR").values
    assert E.tk_lag(100) == 101


def test_tk_start_and_diff():
    state = {c.key: (c.neutral or "x") for c in E.table("toneking")}
    state["delaySync"] = "1"
    state["eqSectionActive"] = "0"
    state["eqActive"] = "1"
    x = E.tk_start(state)
    assert x[("", "delaySync")] == "0" and x[("", "eqSectionActive")] == "1" and x[("", "eqActive")] == "0"
    assert ("", "presetNameProp") not in x
    base = {("", k): v for k, v in state.items()}
    assert E.tk_diff(x, base) == {("", "delaySync"): "0", ("", "eqSectionActive"): "1", ("", "eqActive"): "0"}
    state["ampsActive"] = "0"
    with pytest.raises(ValueError):
        E.tk_start(state)


def test_tk_values_go_through_the_pack():
    from packs.loader import load_pack

    pack = load_pack("toneking")
    w = []
    for key, v in (("cab1Active", "1"), ("ampType", "1"), ("cab2MicIR", "15"), ("delayTimeMSL", "433.33")):
        assert pack.to_stored(pack.parameters["/" + key], v, warnings=w) == v
    assert not w


# --- listening and the machine --------------------------------------------------------------------

def test_listen_choose():
    rows = [("p1", "A", "gate", -0.10), ("p1", "B", "gate", -0.08), ("p2", "A", "gate", -0.05),
            ("p3", "A", "gate", -0.04), ("p4", "A", "rooms", -0.07), ("p5", "B", "rooms", -0.01),
            ("p6", "A", "doubler", 0.02), ("p7", "A", "rooms", 0.001), ("p8", "B", "gate", -0.002),
            ("p9", "A", "doubler", 0.0001)]
    picks = E.listen_choose(rows)
    assert picks == E.listen_choose(list(reversed(rows)))
    slugs = [r[0] for r, _ in picks]
    assert len(slugs) == len(set(slugs)) <= 8
    assert [r[0] for r, w in picks if w == "gain"] == ["p1", "p2", "p4", "p5"]
    assert {r[0] for r, w in picks if w == "gain-fill"} == {"p3", "p8"}
    assert {r[0] for r, w in picks if w == "near-tie"} == {"p7", "p9"}
    assert len(E.letters(8)) == 8 and set(E.letters(50)) == {0, 1}


def test_render_commands_are_counted_by_the_machine_wide_cap():
    from learn import local_objective as LO

    for cmd in ("screen", "tk-smoke", "stage1 --shard 0/3", "tk-stage1 --shard 2/3", "listening build"):
        assert any(re.search(p, f"python -m learn.every_control {cmd}") for p in LO.RENDERS), cmd
    for cmd in ("table", "amp-choice", "report", "listening score --answers 1A"):
        assert not any(re.search(p, f"python -m learn.every_control {cmd}") for p in LO.RENDERS), cmd


def test_smoke_options_refuse_the_real_output():
    with pytest.raises(SystemExit):
        E.main(["stage1", "--assume-visible"])


def test_rooms_keeps_at_least_one_cab_on():
    _, dims = E.group_plan("rooms", _base(cabParameters__rightCabActive="false"), set(E.SCREEN_DIMS))
    assert "leftCabActive" not in [d.key for d in dims]
    _, dims = E.group_plan("rooms", _base(), set(E.SCREEN_DIMS))
    assert "leftCabActive" in [d.key for d in dims]


def test_listening_verdict_is_the_declared_rule():
    def t(g, why, group_letter="A"):
        return {"group": g, "why": why, "letters": {group_letter: "group", "AB".replace(group_letter, ""): "base"}}
    trials = {"1": t("gate", "gain"), "2": t("gate", "gain", "B"), "3": t("doubler", "gain"),
              "4": t("doubler", "gain-fill"), "5": t("rooms", "gain"), "6": t("gate", "near-tie")}
    v = E.listening_verdict(trials, {"1": "A", "2": "B", "3": "A", "4": "A", "5": "B", "6": "B"})
    assert v["gate"]["verdict"].startswith("ear agrees") and v["gate"]["trials"] == 2
    assert v["doubler"]["verdict"].startswith("fewer than 2")              # the fill doesn't count
    assert v["rooms"]["verdict"].startswith("descriptive")
    v = E.listening_verdict(trials, {"1": "A", "2": "A"})
    assert v["gate"]["verdict"].startswith("ear disagrees")
