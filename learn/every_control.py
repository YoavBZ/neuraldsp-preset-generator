"""Every control, stages 0 and 1 (`docs/every-control-plan.md`). Development only, the true DI
(the measure DI), no model, no training.

    .venv/bin/python -m learn.every_control table                      # 0a: the full-space table (zero renders)
    .venv/bin/python -m learn.every_control amp-choice                 # 0b: amp choice from stored K_S cells (zero renders)
    .venv/bin/python -m learn.every_control screen                     # 0c: what the judge can hear (60 renders, 1 process)
    .venv/bin/python -m learn.every_control tk-smoke                   # 0d: Tone King renderer, 30 renders, speed and repeat
    .venv/bin/python -m learn.every_control stage1 --shard i/n         # 1: Morgan's unmeasured groups (48 cells)
    .venv/bin/python -m learn.every_control tk-stage1 --shard i/n      # 1: Tone King's whole space (48 cells)
    .venv/bin/python -m learn.every_control listening build            # 1: the blind page (8 trials)
    .venv/bin/python -m learn.every_control listening score --answers "1A 2B ..."
    .venv/bin/python -m learn.every_control report

Outputs go to ~/ndsp-presets/learn/every-control/ (`--out` moves them, e.g. for a smoke run).

Shared with knob ceiling 2 (`learn/knob_ceiling2.py`): its 24 parts and 48 cells (part ×
direction, each on the amp knob ceiling 2 used), `knob_ceiling.Renderer` (isolate=True, process
reuse, the bounded render server), `knob_ceiling.judge`, `knob_ceiling.knob_search` with `canon`,
one discarded priming render per cell, the repeat check against the stored score (|log| ≤ 0.005),
held halves, band-clustered 90% intervals (`confirm_run.stats`). Renders are scored, not kept:
only the listening page keeps audio (the first 0.25 s, the isolate fade-in, zeroed).

The machine: every render command waits for a slot under `local_objective.CAP` (3 render
processes machine-wide, counted by `local_objective.RENDERS`, which lists these commands) and
stops below 31 GB free. Every cell is written atomically, so a stopped shard resumes.

The pure parts (the table, the gates, the neutral values, the canonical form, the spaces, the
moves, the readings and the selections) are unit-tested; the commands that render are not.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import shutil
import statistics
import sys
from dataclasses import dataclass

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import knob_ceiling as K  # noqa: E402
from learn.knob_ceiling import Dim  # noqa: E402

OUT = K.HOME / "learn/every-control"
MIN_FREE_GB = 31.0
REPEAT_TOL = 0.005               # |log| against a stored score; also the screen's "cannot see" bound
WET_MARGIN = 0.005               # a group's setting is adopted only if it beats the start by this (search half)
GROUP_BUDGET = 30                # Morgan, renders per group and cell
TK_BUDGET = 150                  # Tone King, renders per cell
SEED_STAGE1 = 20261023           # + the group's index
SEED_TK = 20261024
SEED_LISTEN = 20261025
TRIM_S = 0.25                    # the isolate fade-in, zeroed in kept audio
TK_PREROLL_S = 1.0               # as tk_baseline: a Tone King instance may start muted for up to 0.87 s
TK_LATENCY = 51                  # samples (Morgan 52)

# ============================================================== 0a: the full-space table

MORGAN_AMPS = {"ac20": "0", "pr12": "1", "sw50r": "2"}        # selectedAmp's stored index


@dataclass(frozen=True)
class Control:
    """One manifest control. `source`: searched (today's space, both routes), measured (worth
    measured with the true DI: EQ, pedals, the searched time-effect knobs, the spring), stage1
    (a stage-1 group), screen (0c decides: a rule if the judge can't see it, else its stage-1
    group), stage0b (amp choice), rule, never (a manifest exception). `group`: the stage-1
    group for stage1/screen; the rule's text for rule. `amp`: the Morgan amp whose module it is
    (None: every amp). `gate`: the conditions under which it sounds (all must hold):
    ("on", path), ("off", path), ("nonzero", path), ("amp", amp), ("channel", stored),
    ("both_cabs",), ("both_cabs_mono",) (only for a mono judge). `neutral`: its value when it
    can't sound (the canonical form and a written preset)."""
    pack: str
    module: str
    key: str
    family: str
    source: str
    group: str = ""
    amp: str | None = None
    gate: tuple = ()
    neutral: str | None = None

    @property
    def path(self):
        return (self.module, self.key)


def _m(module, key, family, source, group="", amp=None, gate=(), neutral=None):
    return Control("morgan", module, key, family, source, group, amp, tuple(gate), neutral)


# The plugin's Default.xml for the values knob ceiling 2 did not declare; knob ceiling 2's
# declared neutrals (pedals, effects' "on" values, the spring) and knob ceiling's flat EQ where it did.
_AMP_DEFAULTS = {
    "pr12": {"pr12Volume": "0.446343", "pr12Treble": "0.5", "pr12Bass": "0.399422"},
    "sw50r": {"sw50rVolume": "0.273578", "sw50rLevel": "0.299563", "sw50rTreble": "0.637797",
              "sw50rMid": "0.632109", "sw50rBass": "0.5", "sw50rBright": "true", "sw50rTrebleBoost": "true",
              "sw50rInputMode": "false"},
    "ac20": {"ac20Volume": "0.5", "ac20Cut": "0.5", "ac20Power": "1", "ac20Bright": "true", "ac20BassTreble": "true"},
}
_AMP_SECTION = ("on", ("ampParameters", "sectionActive"))
_EQ_SECTION = ("on", ("eqParameters", "sectionActive"))
_PEDALS = ("on", ("pedalParameters", "sectionActive"))
_FX = ("on", ("fxParameters", "sectionActive"))
_CABS = ("on", ("cabParameters", "sectionActive"))


def _morgan_table():
    T = []
    # today's space: input gain, the amp's knobs and switches, both mics and placements, the right cab
    T.append(_m("parameters", "inputGain", "today", "searched", neutral="0"))
    for amp, knobs in _AMP_DEFAULTS.items():
        for k, v in knobs.items():
            T.append(_m(f"{amp}Amp", k, "today", "searched", amp=amp, gate=[("amp", amp), _AMP_SECTION], neutral=v))
    for side in ("left", "right"):
        cab = ("on", ("cabParameters", f"{side}CabActive"))
        T.append(_m("cabParameters", f"{side}MicType", "today", "searched", gate=[_CABS, cab], neutral="0"))
        T.append(_m("cabParameters", f"{side}CabPosition", "today", "searched", gate=[_CABS, cab], neutral="0.3"))
        T.append(_m("cabParameters", f"{side}CabDistance", "today", "searched", gate=[_CABS, cab], neutral="0.1"))
    right = ("on", ("cabParameters", "rightCabActive"))
    T.append(_m("cabParameters", "rightCabMicLevel", "today", "searched", gate=[_CABS, right], neutral="0"))
    T.append(_m("cabParameters", "rightCabActive", "today", "searched", gate=[_CABS], neutral="true"))
    # the amp's EQ (measured: knob ceiling (d))
    for amp in MORGAN_AMPS:
        m = f"{amp}EQ"
        T.append(_m(m, f"{amp}EQActive", "amp_eq", "measured", amp=amp, gate=[("amp", amp), _EQ_SECTION],
                    neutral="false"))
        on = ("on", (m, f"{amp}EQActive"))
        for i in range(1, 10):
            T.append(_m(m, f"{amp}EQBand{i}", "amp_eq", "measured", amp=amp,
                        gate=[("amp", amp), _EQ_SECTION, on], neutral=K.EQ_NEUTRAL["band"]))
        T.append(_m(m, f"{amp}EQHpf", "amp_eq", "measured", amp=amp, gate=[("amp", amp), _EQ_SECTION, on],
                    neutral=K.EQ_NEUTRAL["hpf"]))
        T.append(_m(m, f"{amp}EQLpf", "amp_eq", "measured", amp=amp, gate=[("amp", amp), _EQ_SECTION, on],
                    neutral=K.EQ_NEUTRAL["lpf"]))
    # the pedals (measured: knob ceiling 2, stage 1), knob ceiling 2's neutrals
    from learn import knob_ceiling2 as K2

    for mod, (sw, knobs) in K2.PEDALS.items():
        T.append(_m(mod, sw, "pedals", "measured", gate=[_PEDALS], neutral="false"))
        for k, v in knobs.items():
            T.append(_m(mod, k, "pedals", "measured", gate=[_PEDALS, ("on", (mod, sw))], neutral=v))
    T.append(_m("compressor", "compressorRelease", "pedals", "measured",
                gate=[_PEDALS, ("on", ("compressor", "compressorActive"))], neutral="false"))
    # time effects: the searched knobs measured (knob ceiling 2, stage 2), at its "on" values
    for name, (sw, on_vals, _) in K2.EFFECTS.items():
        T.append(_m(*sw, "time_effects", "measured", gate=[_FX], neutral="false"))
        for (mod, k), v in on_vals.items():
            T.append(_m(mod, k, "time_effects", "measured", gate=[_FX, ("on", sw)]
                        + ([("off", ("delay", "delaySync"))] if k == "delayTime" else [])
                        + ([("off", ("tremolo", "tremoloSync"))] if k == "tremoloRate" else []), neutral=v))
    d_on, t_on = ("on", ("delay", "delayActive")), ("on", ("tremolo", "tremoloActive"))
    T.append(_m("delay", "delaySync", "time_effects", "rule", "off: the time in ms (packs/timing.py)",
                gate=[_FX, d_on], neutral="0"))
    T.append(_m("delay", "delayTempo", "time_effects", "rule", "S's value (sync off)",
                gate=[_FX, d_on, ("on", ("delay", "delaySync"))], neutral="120"))
    T.append(_m("delay", "delaySyncNote", "time_effects", "rule", "S's value (sync off)",
                gate=[_FX, d_on, ("on", ("delay", "delaySync"))], neutral="13"))
    T.append(_m("tremolo", "tremoloSync", "time_effects", "rule", "off: the rate in Hz",
                gate=[_FX, t_on], neutral="false"))
    T.append(_m("tremolo", "tremoloSyncNote", "time_effects", "rule", "S's value (sync off)",
                gate=[_FX, t_on, ("on", ("tremolo", "tremoloSync"))], neutral="11"))
    T.append(_m("tremolo", "tremoloLevel", "time_effects", "stage1", "effects", gate=[_FX, t_on], neutral="0.5"))
    T.append(_m("delay", "delayTapeDrive", "time_effects", "stage1", "effects", gate=[_FX, d_on], neutral="0"))
    T.append(_m("delay", "delayWidth", "time_effects", "screen", "effects", gate=[_FX, d_on], neutral="1"))
    T.append(_m("delay", "delayPingPong", "time_effects", "screen", "effects", gate=[_FX, d_on], neutral="true"))
    # the amp's spring: level 0 is off (knob ceiling 2's pseudo-switch)
    T.append(_m("pr12Amp", "pr12Reverb", "spring", "measured", amp="pr12", gate=[("amp", "pr12"), _AMP_SECTION],
                neutral="0"))
    T.append(_m("pr12Amp", "pr12Dwell", "spring", "measured", amp="pr12",
                gate=[("amp", "pr12"), _AMP_SECTION, ("nonzero", ("pr12Amp", "pr12Reverb"))],
                neutral=K2.SPRING["pr12"][0][("pr12Amp", "pr12Dwell")]))
    T.append(_m("sw50rAmp", "sw50rReverb", "spring", "measured", amp="sw50r", gate=[("amp", "sw50r"), _AMP_SECTION],
                neutral="0"))
    T.append(_m("", "selectedAmp", "amp_choice", "stage0b"))
    # gate and doubler
    T.append(_m("parameters", "gateActive", "gate_doubler", "stage1", "gate", neutral="false"))
    T.append(_m("parameters", "gateThreshold", "gate_doubler", "stage1", "gate",
                gate=[("on", ("parameters", "gateActive"))], neutral="-80"))
    T.append(_m("parameters", "doublerActive", "gate_doubler", "stage1", "doubler", neutral="false"))
    T.append(_m("parameters", "doublerSpread", "gate_doubler", "screen", "doubler",
                gate=[("on", ("parameters", "doublerActive"))], neutral="6"))
    # the rest of the cab
    left = ("on", ("cabParameters", "leftCabActive"))
    T.append(_m("cabParameters", "leftCabActive", "cab_rest", "stage1", "rooms", gate=[_CABS], neutral="true"))
    T.append(_m("cabParameters", "leftCabMicLevel", "cab_rest", "stage1", "rooms", gate=[_CABS, left], neutral="0"))
    for side, cab in (("left", left), ("right", right)):
        T.append(_m("cabParameters", f"{side}CabPhase", "cab_rest", "screen", "phase",
                    gate=[_CABS, cab, ("both_cabs",)], neutral="false"))
        T.append(_m("cabParameters", f"{side}CabStereo", "cab_rest", "screen", "phase",
                    gate=[_CABS, cab, ("both_cabs_mono",)], neutral="false"))
        T.append(_m("cabParameters", f"{side}CabPan", "cab_rest", "screen", "phase",
                    gate=[_CABS, cab, ("both_cabs_mono",)], neutral="0"))
        T.append(_m("cabParameters", f"{side}RoomActive", "cab_rest", "stage1", "rooms", gate=[_CABS, cab],
                    neutral="false"))
        T.append(_m("cabParameters", f"{side}RoomMicLevel", "cab_rest", "stage1", "rooms",
                    gate=[_CABS, cab, ("on", ("cabParameters", f"{side}RoomActive"))], neutral="-6"))
    T.append(_m("parameters", "outputGain", "output", "rule", "matched to S's loudness (the judge removes level)",
                neutral="0"))
    for sec in ("ampParameters", "eqParameters", "pedalParameters", "cabParameters", "fxParameters"):
        T.append(_m(sec, "sectionActive", "sections", "rule", "held on", neutral="true"))
    T.append(_m("", "name", "never", "never", "the preset's name"))
    T.append(_m("parameters", "transpose", "never", "never", "pitch, not tone (searchable: false)"))
    for side in ("left", "right"):
        T.append(_m("cabParameters", f"{side}RoomMicType", "never", "never", "no control in the plugin's UI"))
        T.append(_m("cabParameters", f"{side}ChosenIRFilePath", "never", "never", "empty: the internal mics"))
    return T


def _t(key, family, source, group="", gate=(), neutral=None):
    return Control("toneking", "", key, family, source, group, None, tuple(gate), neutral)


# Tone King's Default.xml (`/Library/Audio/Presets/Neural DSP/Tone King Imperial MKII/Default.xml`).
TK_DEFAULTS = {
    "ampAttenuation": "5", "ampHfc": "0", "ampReverb": "0", "ampTremoloDepth": "0", "ampTremoloSpeed": "0.73",
    "ampType": "0", "ampsActive": "1", "rhythmAmpBass": "0.34", "rhythmAmpTreble": "0.35",
    "rhythmAmpVolume": "0.38", "rhythmAttBypass": "0", "leadAmpMidBite": "0.81", "leadAmpTone": "0.23",
    "leadAmpVolume": "0.5",
    "compActive": "0", "compBlend": "1", "compCompression": "0.5", "compSpeed": "1", "compVolume": "0",
    "drive1Active": "0", "drive1Bass": "0.5", "drive1Overdrive": "0.5", "drive1Treble": "0.5", "drive1Volume": "0.5",
    "drive2Active": "0", "drive2Bass": "0.5", "drive2Overdrive": "0.5", "drive2Treble": "0.5", "drive2Volume": "0.5",
    "wahActive": "0", "wahAtt": "500", "wahMode": "0", "wahPosition": "0", "wahRel": "500", "wahSens": "50",
    "pedalSectionActive": "1",
    "eqActive": "1", **{f"eqBand{i}": "0" for i in range(1, 10)}, "eqSectionActive": "1",
    "cab1Active": "1", "cab1Distance": "0", "cab1Level": "-12", "cab1MicIR": "0", "cab1Pan": "0", "cab1Phase": "0",
    "cab1Position": "0.5", "cab1RoomActive": "0", "cab1RoomIRLevel": "-12",
    "cab2Active": "1", "cab2Distance": "0", "cab2Level": "-12", "cab2MicIR": "6", "cab2Pan": "0", "cab2Phase": "0",
    "cab2Position": "0.5", "cab2RoomActive": "0", "cab2RoomIRLevel": "-12", "cabSectionActive": "1",
    "chorusActive": "0", "chorusDepth": "0", "chorusMix": "1", "chorusRate": "0.5",
    "delayActive": "1", "delayFeedback": "0.14", "delayHPF": "0.505", "delayLPF": "0.249", "delayMix": "0.14",
    "delayNoteMs": "0", "delayStereoMode": "0", "delaySync": "0", "delaySyncNoteL": "13", "delaySyncNoteR": "12",
    "delayTapTempo": "0", "delayTempo": "120", "delayTimeMSL": "500", "delayTimeMSR": "375",
    "reverbActive": "1", "reverbDecay": "1.87", "reverbHPF": "395", "reverbLPF": "4938", "reverbMix": "0.16",
    "reverbPreDelay": "0", "timeSectionActive": "1",
    "gateThreshold": "-95", "inputGain": "0", "outputGain": "0",
}
TK_DELAY_RULES = ("delaySync", "delayNoteMs", "delaySyncNoteL", "delaySyncNoteR", "delayTapTempo", "delayTempo")
TK_SECTIONS = ("ampsActive", "pedalSectionActive", "eqSectionActive", "cabSectionActive", "timeSectionActive")
# A section the start has off is held on with its features switched off (the same sound).
TK_SECTION_MEMBERS = {"ampsActive": (), "cabSectionActive": (), "eqSectionActive": ("eqActive",),
                      "pedalSectionActive": ("compActive", "drive1Active", "drive2Active", "wahActive"),
                      "timeSectionActive": ("chorusActive", "delayActive", "reverbActive")}


def _toneking_table():
    T = []
    amp = ("on", ("", "ampsActive"))
    sec = {"comp": "pedalSectionActive", "drive1": "pedalSectionActive", "drive2": "pedalSectionActive",
           "wah": "pedalSectionActive", "chorus": "timeSectionActive", "delay": "timeSectionActive",
           "reverb": "timeSectionActive"}
    fam = {"comp": "pedals", "drive1": "pedals", "drive2": "pedals", "wah": "pedals", "chorus": "time_effects",
           "delay": "time_effects", "reverb": "time_effects"}

    def nt(k):
        return TK_DEFAULTS[k]

    for k in ("ampAttenuation", "ampHfc", "ampReverb", "ampTremoloDepth"):
        T.append(_t(k, "amp", "tk_stage1", gate=[amp], neutral=nt(k)))
    # Not gated by depth 0: the speed moved the score at depth 0 (smoke, 2026-10-22: 0.00036 log).
    T.append(_t("ampTremoloSpeed", "amp", "tk_stage1", gate=[amp], neutral=nt("ampTremoloSpeed")))
    T.append(_t("ampType", "amp", "tk_stage1", gate=[amp], neutral=nt("ampType")))
    for k in ("rhythmAmpBass", "rhythmAmpTreble", "rhythmAmpVolume", "rhythmAttBypass"):
        T.append(_t(k, "amp", "tk_stage1", gate=[amp, ("channel", "0")], neutral=nt(k)))
    for k in ("leadAmpMidBite", "leadAmpTone", "leadAmpVolume"):
        T.append(_t(k, "amp", "tk_stage1", gate=[amp, ("channel", "1")], neutral=nt(k)))
    for prefix, knobs in (("comp", ("Blend", "Compression", "Speed", "Volume")),
                          ("drive1", ("Bass", "Overdrive", "Treble", "Volume")),
                          ("drive2", ("Bass", "Overdrive", "Treble", "Volume")),
                          ("wah", ("Att", "Mode", "Position", "Rel", "Sens")),
                          ("chorus", ("Depth", "Mix", "Rate")),
                          ("delay", ("Feedback", "HPF", "LPF", "Mix", "StereoMode", "TimeMSL", "TimeMSR")),
                          ("reverb", ("Decay", "HPF", "LPF", "Mix", "PreDelay"))):
        s = ("on", ("", sec[prefix]))
        T.append(_t(f"{prefix}Active", fam[prefix], "tk_stage1", gate=[s], neutral="0"))
        for k in knobs:
            key = prefix + k
            gate = [s, ("on", ("", f"{prefix}Active"))]
            if key in ("delayTimeMSL", "delayTimeMSR"):
                gate.append(("off", ("", "delaySync")))
            src, grp = ("screen", "tk") if key == "delayStereoMode" else ("tk_stage1", "")
            T.append(_t(key, fam[prefix], src, grp, gate=gate, neutral=nt(key)))
    for k in TK_DELAY_RULES:
        rule = "off: the time in ms" if k == "delaySync" else "the start's value (sync off)"
        gate = [("on", ("", "timeSectionActive")), ("on", ("", "delayActive"))]
        if k not in ("delaySync", "delayNoteMs"):                          # sync-only controls
            gate.append(("on", ("", "delaySync")))
        T.append(_t(k, "time_effects", "rule", rule, gate=gate, neutral="0" if k == "delaySync" else nt(k)))
    eq = ("on", ("", "eqSectionActive"))
    T.append(_t("eqActive", "eq", "tk_stage1", gate=[eq], neutral="0"))
    for i in range(1, 10):
        T.append(_t(f"eqBand{i}", "eq", "tk_stage1", gate=[eq, ("on", ("", "eqActive"))], neutral="0"))
    cabs = ("on", ("", "cabSectionActive"))
    for n in ("1", "2"):
        cab = ("on", ("", f"cab{n}Active"))
        T.append(_t(f"cab{n}Active", "cab", "tk_stage1", gate=[cabs], neutral="1"))
        for k in ("Distance", "Level", "MicIR", "Position", "RoomActive"):
            T.append(_t(f"cab{n}{k}", "cab", "tk_stage1", gate=[cabs, cab],
                        neutral="0" if k == "RoomActive" else nt(f"cab{n}{k}")))
        T.append(_t(f"cab{n}RoomIRLevel", "cab", "tk_stage1",
                    gate=[cabs, cab, ("on", ("", f"cab{n}RoomActive"))], neutral=nt(f"cab{n}RoomIRLevel")))
        T.append(_t(f"cab{n}Phase", "cab", "screen", "tk", gate=[cabs, cab, ("both_cabs",)], neutral="0"))
        T.append(_t(f"cab{n}Pan", "cab", "screen", "tk", gate=[cabs, cab, ("both_cabs_mono",)], neutral="0"))
    for k in TK_SECTIONS:
        T.append(_t(k, "sections", "rule", "held on", neutral="1"))
    T.append(_t("inputGain", "io", "tk_stage1", neutral="0"))
    T.append(_t("gateThreshold", "io", "tk_stage1", neutral=nt("gateThreshold")))
    T.append(_t("outputGain", "io", "rule", "matched to S's loudness (the judge removes level)", neutral="0"))
    for k in ("presetNameProp", "presetPathProp", "presetUIDProp", "presetVersionProp"):
        T.append(_t(k, "never", "never", "the preset's own bookkeeping"))
    for k in ("filePath1", "filePath2"):
        T.append(_t(k, "never", "never", "empty: the internal mics"))
    return T


_TABLE = []


def table(pack=None):
    if not _TABLE:
        _TABLE.extend(_morgan_table() + _toneking_table())
    return [c for c in _TABLE if pack is None or c.pack == pack]


def manifest_writable(pack):
    """(module, key) of every writable manifest control."""
    m = json.loads((PLUGIN_ROOT / "packs" / pack / "manifest.json").read_text())["parameters"]
    out = []
    for path, spec in m.items():
        if spec.get("writable", True) is False:
            continue
        module, _, key = path.rpartition("/")
        out.append((module, key))
    return out


def counts(pack, amp=None):
    """{family: n} of the controls that sound (for Morgan: for `amp`), never excluded."""
    out = {}
    for c in table(pack):
        if c.source == "never" or (c.amp is not None and c.amp != amp):
            continue
        out[c.family] = out.get(c.family, 0) + 1
    return out


# ============================================================== the gates: switched-off features

def _truthy(v):
    return str(v).strip().lower() in ("true", "1")


def _cab_keys(pack):
    return ((("cabParameters", "leftCabActive"), ("cabParameters", "rightCabActive")) if pack == "morgan"
            else (("", "cab1Active"), ("", "cab2Active")))


def _value(x, path, by):
    if path in x:
        return x[path]
    c = by.get(path)
    return c.neutral if c is not None else None


def sounds(c, x, amp=None, mono=True, by=None):
    """Does control `c` change the sound in setting `x`? `amp`: Morgan's selected amp, when it
    isn't in `x` (knob_ceiling.Renderer passes it apart). Missing keys read as their neutral."""
    by = by if by is not None else {cc.path: cc for cc in table(c.pack)}
    for cond in c.gate:
        kind = cond[0]
        if kind == "on" and not _truthy(_value(x, cond[1], by)):
            return False
        if kind == "off" and _truthy(_value(x, cond[1], by)):
            return False
        if kind == "nonzero":
            try:
                if float(_value(x, cond[1], by)) <= 0:
                    return False
            except (TypeError, ValueError):
                return False
        if kind == "amp":
            sel = amp if amp is not None else {v: a for a, v in MORGAN_AMPS.items()}.get(str(x.get(("", "selectedAmp"))))
            if sel != cond[1]:
                return False
        if kind == "channel" and str(_value(x, ("", "ampType"), by)) != cond[1]:
            return False
        if kind in ("both_cabs", "both_cabs_mono"):
            if kind == "both_cabs_mono" and not mono:
                continue
            if not all(_truthy(_value(x, p, by)) for p in _cab_keys(c.pack)):
                return False
    return True


def mask(x, pack, amp=None, mono=True):
    """{(module, key): sounds?} for every control of `pack` but the manifest exceptions: the
    weights for a loss or a knob score (a switched-off feature's knobs are left out)."""
    T = [c for c in table(pack) if c.source != "never"]
    by = {c.path: c for c in T}
    return {c.path: sounds(c, x, amp, mono, by) for c in T}


def neutralise(x, pack, amp=None, only=None, mono=False):
    """The canonical form: every control that can't sound set to its neutral value (`only`: just
    these paths). Decided on `x` as given, in one pass (every control's gate names its parents)."""
    T = [c for c in table(pack) if c.neutral is not None and (only is None or c.path in only)]
    by = {c.path: c for c in table(pack)}
    y = dict(x)
    for c in T:
        if c.path in x and not sounds(c, x, amp, mono, by):
            y[c.path] = c.neutral
    return y


# ============================================================== 0b: amp choice (zero renders)

def amp_choice_rows(cells):
    """cells: knob ceiling's result.json dicts. Per part and direction with all three amps
    usable and finite: log(held of the amp with the lowest K_S search half) minus the mean log
    held over the three (an amp chosen blind). -> [(slug, band, gain_class, value)], one per
    part (the mean over its directions)."""
    by = {}
    for c in cells:
        by.setdefault(c["slug"], []).append(c)
    rows = []
    for slug, group in sorted(by.items()):
        xs = []
        for search, held in K.DIRECTIONS:
            runs = [(c["amp"], c["runs"].get(search, {})) for c in group]
            ok = [(a, r["K_S"]) for a, r in runs if "skipped" not in r and "K_S" in r
                  and K.finite(r["K_S"]["search"], r["K_S"]["held"]) and r["K_S"]["held"] > 0]
            if len(ok) != len(K.AMPS) or len(group) != len(K.AMPS):
                continue
            pick = min(ok, key=lambda t: (t[1]["search"], t[0]))
            xs.append(math.log(pick[1]["held"]) - statistics.fmean(math.log(k["held"]) for _, k in ok))
        if xs:
            rows.append((slug, group[0]["band"], group[0]["gain_class"], statistics.fmean(xs)))
    return rows


def amp_choice(out):
    from learn import confirm_run as CR

    cells = [json.loads(p.read_text()) for p in sorted((K.OUT / "cells").glob("*/*/result.json"))]
    rows = amp_choice_rows(cells)
    res = {"parts": len(rows), "rule": "picked (lowest K_S search half) minus the blind mean, held half, log"}
    for name, keep in (("clean+crunch", ("clean", "crunch")), ("clean", ("clean",)), ("crunch", ("crunch",))):
        sel = [(b, v) for _, b, c, v in rows if c in keep]
        if len({b for b, _ in sel}) >= 2:
            res[name] = CR.stats(sel)
    res["reading"] = reading(res.get("clean+crunch"))
    out.mkdir(parents=True, exist_ok=True)
    K._atomic(out / "amp-choice.json", res)
    print(json.dumps(res.get("clean+crunch"), indent=1), res["reading"])


def reading(s):
    """The declared rule: interval below 0 -> enters; else a tie (the cheaper option) or worse."""
    if not s or "hi90" not in s:
        return "no reading"
    if s["hi90"] < 0:
        return "gain: enters"
    if s["lo90"] > 0:
        return "worse: keeps its rule"
    return "tie (not shown at this power): keeps its rule"


# ============================================================== 0c: what the judge can hear

MORGAN_SCREEN = ("leftCabPan", "rightCabPan", "leftCabStereo", "rightCabStereo", "leftCabPhase",
                 "rightCabPhase", "delayWidth", "delayPingPong", "doublerSpread")
TK_SCREEN = ("cab1Pan", "cab2Pan", "cab1Phase", "cab2Phase", "delayStereoMode")
SCREEN_DIMS = {  # the range each screened control moves over
    ("cabParameters", "leftCabPan"): Dim("cabParameters", "leftCabPan", "cont", -50.0, 50.0),
    ("cabParameters", "rightCabPan"): Dim("cabParameters", "rightCabPan", "cont", -50.0, 50.0),
    ("cabParameters", "leftCabStereo"): Dim("cabParameters", "leftCabStereo", "switch", values=("false", "true")),
    ("cabParameters", "rightCabStereo"): Dim("cabParameters", "rightCabStereo", "switch", values=("false", "true")),
    ("cabParameters", "leftCabPhase"): Dim("cabParameters", "leftCabPhase", "switch", values=("false", "true")),
    ("cabParameters", "rightCabPhase"): Dim("cabParameters", "rightCabPhase", "switch", values=("false", "true")),
    ("delay", "delayWidth"): Dim("delay", "delayWidth", "cont"),
    ("delay", "delayPingPong"): Dim("delay", "delayPingPong", "switch", values=("false", "true")),
    ("parameters", "doublerSpread"): Dim("parameters", "doublerSpread", "cont", 3.0, 20.0),
    ("", "cab1Pan"): Dim("", "cab1Pan", "cont", -1.0, 1.0),
    ("", "cab2Pan"): Dim("", "cab2Pan", "cont", -1.0, 1.0),
    ("", "cab1Phase"): Dim("", "cab1Phase", "switch", values=("0", "1")),
    ("", "cab2Phase"): Dim("", "cab2Phase", "switch", values=("0", "1")),
    ("", "delayStereoMode"): Dim("", "delayStereoMode", "switch", values=("0", "1")),
}


def far(d, v):
    """A screened control's move: a switch flipped, a knob to the end of its range further away."""
    if d.kind == "switch":
        cur = str(v).lower()
        on = cur in ("true", "1")
        return d.values[0] if on else d.values[1]
    u = d.to_unit(v)
    return K.fmt(d.hi if u <= 0.5 else d.lo)


def screen_base(kind, x, pack):
    """The screen's bases from S: both cabs on, or the delay on (sync off), or the doubler on."""
    y = dict(x)
    if kind == "cab":
        y.update({p: ("true" if pack == "morgan" else "1") for p in _cab_keys(pack)})
    elif kind == "delay":
        if pack == "morgan":
            from learn import knob_ceiling2 as K2

            y.update(K2.FREE_SYNC)
            y[("delay", "delayActive")] = "true"
            y.update(K2.EFFECTS["delay"][1])
        else:
            y[("", "delayActive")] = "1"
            y[("", "delaySync")] = "0"
    elif kind == "doubler":
        y[("parameters", "doublerActive")] = "true"
        y[("parameters", "doublerSpread")] = "6"
    return y


def screen_plan(pack):
    """[(base kind, control path or None)]: per base, the base itself, then its moves. The
    cab base is rendered twice (its repeat)."""
    if pack == "morgan":
        cab = [p for p in SCREEN_DIMS if p[0] == "cabParameters"]
        return ([("cab", None), ("cab", "repeat")] + [("cab", p) for p in cab]
                + [("delay", None), ("delay", ("delay", "delayWidth")), ("delay", ("delay", "delayPingPong"))]
                + [("doubler", None), ("doubler", ("parameters", "doublerSpread"))])
    cab = [("", k) for k in ("cab1Pan", "cab2Pan", "cab1Phase", "cab2Phase")]
    return ([("cab", None), ("cab", "repeat")] + [("cab", p) for p in cab]
            + [("delay", None), ("delay", ("", "delayStereoMode"))])


def screen_cells(slugs, gain_class):
    """3 Morgan cells (every 8th part, sorted, on pr12, sw50r, ac20) and 2 Tone King cells (the
    first clean and the first crunch part, each on its class start)."""
    s = sorted(slugs)
    morgan = [("morgan", slug, amp) for slug, amp in zip(s[::8][:3], K.AMPS)]
    tk = [("toneking", next(x for x in s if gain_class[x] == c), c) for c in ("clean", "crunch")]
    return morgan + tk


def invisible(rows, tol=REPEAT_TOL):
    """rows: {control: [max over halves |log(moved/base)| against the record, per cell]} ->
    {control: True if the judge's score never moved beyond `tol`}."""
    return {k: bool(v) and all(x <= tol for x in v) for k, v in rows.items()}


def visible_set(screen_path, assume_visible=False):
    """{(module, key)} of the screened controls the judge can see (from screen.json)."""
    if assume_visible:
        return set(SCREEN_DIMS)
    res = json.loads(pathlib.Path(screen_path).read_text())
    return {tuple(k.split("|", 1)) for k, inv in res["invisible"].items() if not inv}


# ============================================================== 1: Morgan's groups

GROUPS = ("gate", "doubler", "rooms", "phase", "effects")


def _dim(path):
    m, k = path
    if path in SCREEN_DIMS:
        return SCREEN_DIMS[path]
    return {("parameters", "gateThreshold"): Dim(m, k, "cont", -96.0, 0.0),
            ("cabParameters", "leftCabMicLevel"): Dim(m, k, "cont", -40.0, 6.0),
            ("cabParameters", "leftRoomMicLevel"): Dim(m, k, "cont", -40.0, 6.0),
            ("cabParameters", "rightRoomMicLevel"): Dim(m, k, "cont", -40.0, 6.0),
            ("tremolo", "tremoloLevel"): Dim(m, k, "cont"),
            ("delay", "delayTapeDrive"): Dim(m, k, "cont")}.get(path) or Dim(m, k, "switch", values=("false", "true"))


def group_plan(group, base, visible):
    """(start, dims) for one Morgan stage-1 group on a cell's stored stage-2 setting `base`, or
    None when the group can't apply. The start switches the group's feature on (at its stored
    knobs if it was on, else its neutral values); `dims` are the group's controls that can sound
    in the start, less any the screen found the judge can't see (those keep S's values)."""
    on = lambda p: _truthy(base.get(p))                                   # noqa: E731
    by = {c.path: c for c in table("morgan")}
    x = dict(base)
    if group == "gate":
        if not on(("parameters", "gateActive")):
            x[("parameters", "gateActive")] = "true"
            x[("parameters", "gateThreshold")] = by[("parameters", "gateThreshold")].neutral
        return x, [_dim(("parameters", "gateThreshold"))]
    if group == "doubler":
        if not on(("parameters", "doublerActive")):
            x[("parameters", "doublerActive")] = "true"
            x[("parameters", "doublerSpread")] = by[("parameters", "doublerSpread")].neutral
        return x, [_dim(p) for p in [("parameters", "doublerSpread")] if p in visible]
    if group == "rooms":
        dims = [_dim(("cabParameters", "leftCabActive")), _dim(("cabParameters", "leftCabMicLevel"))]
        for side in ("left", "right"):
            if on(("cabParameters", f"{side}CabActive")) and not on(("cabParameters", f"{side}RoomActive")):
                x[("cabParameters", f"{side}RoomActive")] = "true"
                x[("cabParameters", f"{side}RoomMicLevel")] = by[("cabParameters", f"{side}RoomMicLevel")].neutral
            dims += [_dim(("cabParameters", f"{side}RoomActive")), _dim(("cabParameters", f"{side}RoomMicLevel"))]
        if not on(("cabParameters", "rightCabActive")):              # the right cab's room can't sound,
            dims = [d for d in dims if not d.key.startswith("rightRoom")    # and the left cab must stay on
                    and d.key != "leftCabActive"]
        return x, dims
    if group == "phase":
        if not (on(("cabParameters", "leftCabActive")) and on(("cabParameters", "rightCabActive"))):
            return None
        keys = [("cabParameters", f"{s}Cab{k}") for k in ("Phase", "Pan", "Stereo") for s in ("left", "right")]
        dims = [_dim(p) for p in keys if p in visible]
        return (x, dims) if dims else None
    if group == "effects":
        keys = []
        if on(("tremolo", "tremoloActive")):
            keys.append(("tremolo", "tremoloLevel"))
        if on(("delay", "delayActive")):
            keys += [("delay", "delayTapeDrive")] + [p for p in (("delay", "delayWidth"), ("delay", "delayPingPong"))
                                                     if p in visible]
        return (x, [_dim(p) for p in keys]) if keys else None
    raise ValueError(group)


def group_canon(group, amp):
    """The group's own controls to neutral when they can't sound (the rest stays as stored)."""
    own = {c.path for c in table("morgan") if c.group == group}
    return lambda x: neutralise(x, "morgan", amp=amp, only=own)


def adopt(base_search, best_search, margin=WET_MARGIN):
    return math.log(best_search / base_search) <= -margin


def group_result(base, evals, search, held, margin=WET_MARGIN):
    """base: the stage-2 setting's judge {A, B}; evals: the group's judge dicts. -> the group's
    reading on the held half: adopted (on the search half), its held value, the log ratios."""
    best = min(evals, key=lambda d: d[search]) if evals else None
    ok = best is not None and K.finite(best[search], best[held], base[search], base[held]) \
        and adopt(base[search], best[search], margin)
    chosen = best if ok else base
    return {"adopted": bool(ok), "search": chosen[search], "held": chosen[held],
            "best_search": best[search] if best else None, "best_held": best[held] if best else None,
            "log_held": math.log(chosen[held] / base[held]),
            "log_held_best": (math.log(best[held] / base[held]) if best and K.finite(best[held]) else None),
            "renders": len(evals)}


# ============================================================== Tone King: the search renderer and space

TK_DIMS = {
    "inputGain": ("cont", -24.0, 12.0), "gateThreshold": ("cont", -96.0, 0.0),
    "ampAttenuation": ("cat", tuple(str(i) for i in range(6))), "ampHfc": ("switch",), "ampType": ("switch",),
    "ampReverb": ("cont", 0.0, 1.0), "ampTremoloDepth": ("cont", 0.0, 1.0), "ampTremoloSpeed": ("cont", 0.0, 1.0),
    "rhythmAmpBass": ("cont", 0.0, 1.0), "rhythmAmpTreble": ("cont", 0.0, 1.0), "rhythmAmpVolume": ("cont", 0.0, 1.0),
    "rhythmAttBypass": ("switch",), "leadAmpMidBite": ("cont", 0.0, 1.0), "leadAmpTone": ("cont", 0.0, 1.0),
    "leadAmpVolume": ("cont", 0.0, 1.0),
    "compActive": ("switch",), "compBlend": ("cont", 0.0, 1.0), "compCompression": ("cont", 0.0, 1.0),
    "compSpeed": ("switch",), "compVolume": ("cont", -12.0, 12.0),
    **{f"drive{n}{k}": ("cont", 0.0, 1.0) for n in (1, 2) for k in ("Bass", "Overdrive", "Treble", "Volume")},
    "drive1Active": ("switch",), "drive2Active": ("switch",),
    "wahActive": ("switch",), "wahAtt": ("log", 10.0, 1000.0), "wahMode": ("switch",), "wahPosition": ("cont", 0.0, 1.0),
    "wahRel": ("log", 10.0, 1000.0), "wahSens": ("cont", 0.0, 100.0),
    "eqActive": ("switch",), **{f"eqBand{i}": ("cont", -12.0, 12.0) for i in range(1, 10)},
    **{f"cab{n}{k}": v for n in (1, 2) for k, v in (
        ("Active", ("switch",)), ("Distance", ("cont", 0.0, 1.0)), ("Level", ("cont", -40.0, 6.0)),
        ("MicIR", ("cat", tuple(str(i) for i in range(16)))), ("Position", ("cont", 0.0, 1.0)),
        ("RoomActive", ("switch",)), ("RoomIRLevel", ("cont", -40.0, 6.0)), ("Phase", ("switch",)),
        ("Pan", ("cont", -1.0, 1.0)))},
    "chorusActive": ("switch",), "chorusDepth": ("cont", 0.0, 1.0), "chorusMix": ("cont", 0.0, 1.0),
    "chorusRate": ("cont", 0.0, 1.0),
    "delayActive": ("switch",), "delayFeedback": ("cont", 0.0, 0.5), "delayHPF": ("cont", 0.0, 1.0),
    "delayLPF": ("cont", 0.0, 1.0), "delayMix": ("cont", 0.0, 1.0), "delayStereoMode": ("switch",),
    "delayTimeMSL": ("log", 100.0, 1100.0), "delayTimeMSR": ("log", 100.0, 1100.0),
    "reverbActive": ("switch",), "reverbDecay": ("log", 0.5, 8.0), "reverbHPF": ("log", 50.0, 700.0),
    "reverbLPF": ("log", 1000.0, 10000.0), "reverbMix": ("cont", 0.0, 1.0), "reverbPreDelay": ("cont", 0.0, 1.0),
}


def tk_dim(key):
    spec = TK_DIMS[key]
    if spec[0] == "switch":
        return Dim("", key, "switch", values=("0", "1"))
    if spec[0] == "cat":
        return Dim("", key, "cat", values=spec[1])
    return Dim("", key, spec[0], spec[1], spec[2])


def tk_space(visible):
    """Tone King's searched dims: every tk_stage1 control, and the screened ones the judge sees."""
    return [tk_dim(c.key) for c in table("toneking")
            if c.source == "tk_stage1" or (c.source == "screen" and c.path in visible)]


def tk_start(state):
    """The class start's writable values {("", key): stored}: the delay's sync off and the
    sections held on (rules); a section the start has off comes on with its features off."""
    x = {c.path: state[c.key] for c in table("toneking") if c.source != "never"}
    x[("", "delaySync")] = "0"
    for k, members in TK_SECTION_MEMBERS.items():
        if not _truthy(x[("", k)]):
            if not members:
                raise ValueError(f"the start has {k} off")
            x[("", k)] = "1"
            x.update({("", m): "0" for m in members})
    return x


def tk_canon(x):
    return neutralise(x, "toneking")


def tk_lag(judge_lag):
    """tk_baseline's judge lag: the part's lag less the plugin latency difference."""
    from learn import phase2_set3 as P

    return judge_lag + P.LATENCY - TK_LATENCY


def tk_diff(x, base):
    """Only the controls that differ from the base blob's values: untouched ones keep its bytes."""
    return {k: v for k, v in x.items() if base.get(k) != v}


class ToneKingRenderer:
    """Tone King with per-render edits: the class start's dry preset is the base state, every
    render writes the edits onto it (`AudioUnitRenderer._record_command`), in a reused process
    with isolate=True and the bounded server; a 1-s preroll is cut off (as tk_baseline)."""

    def __init__(self, dry_path):
        import tempfile

        from format.parser import parse
        from format.structured import build
        from match.renderer_au import AudioUnitRenderer

        blob = pathlib.Path(dry_path).read_bytes()
        self.state = {p.key: p.value for p in build(parse(blob)).parameters if not p.module_path}

        class _R(AudioUnitRenderer):
            def _base_state_blob(self):
                return blob

            def _di_file(self, di):
                path = super()._di_file(di)
                K.keep_recent_dis(self._di_files, path)
                return path

        self._bin_dir = pathlib.Path(tempfile.mkdtemp(prefix="au-bounded-tk-"))
        try:
            binary = K.build_bounded_server(self._bin_dir)
            self.r = _R("toneking", process_policy="reuse", isolate=True, binary=binary)
        except BaseException:
            shutil.rmtree(self._bin_dir, ignore_errors=True)
            raise
        self.base = {("", k): v for k, v in self.state.items()}
        self.count = 0

    def render(self, di32, x):
        import numpy as np

        self.count += 1
        pre = int(TK_PREROLL_S * 48000)
        xin = np.concatenate([np.zeros(pre, np.float32), di32])
        y = np.asarray(self.r.render(xin, tk_diff(x, self.base)).audio, np.float64)
        mono = y.mean(1) if y.ndim > 1 else y
        nz = np.flatnonzero(mono)
        if not len(nz) or nz[0] >= pre:
            raise RuntimeError(f"Tone King output starts at {nz[0] if len(nz) else None}: muted past the preroll")
        return y[pre:pre + len(di32)]

    def close(self):
        try:
            self.r.close()
        finally:
            shutil.rmtree(self._bin_dir, ignore_errors=True)


def tk_judge(ref, y, di, judge_lag):
    from analysis.aligned import aligned_distance

    out = {}
    for h, (a, b) in K.R.HALVES.items():
        d = aligned_distance(ref, y, di, lag=tk_lag(judge_lag), render_latency=TK_LATENCY,
                             start_s=a, end_s=b).distance
        out[h] = math.inf if d is None else d
    return out


def tk_starts():
    """class -> (preset name, dry path), from docs/toneking-baseline-choice.json."""
    from learn import tk_baseline as TB

    choice = json.loads(TB.CHOICE.read_text())["presets"]
    menu = TB.load_menu()
    return {c: (n, menu[n]["dry"]) for c, n in choice.items()}


def tk_parts():
    """The 24 parts' Tone King inputs: tk_baseline's development parts (lag, crop) and its stored
    measure DIs, for knob ceiling 2's slugs only (the held-out ones are never read)."""
    from learn import knob_ceiling2 as K2
    from learn import tk_baseline as TB

    slugs = sorted({s for s, _, _, _ in K2.stage_cells()})
    dev = TB.parts("dev")
    assert set(slugs) <= set(dev), sorted(set(slugs) - set(dev))
    return {s: dev[s] for s in slugs}


def tk_di(slug):
    import numpy as np
    from learn import tk_baseline as TB

    return np.load(TB.OUT / "di" / f"{slug}.npy")


def tk_cells():
    """(slug, search, held, class): the 48 cells, by class (one renderer per class start)."""
    ps = tk_parts()
    out = [(s, se, h, ps[s]["gain_class"]) for s in sorted(ps) for se, h in K.DIRECTIONS]
    return sorted(out, key=lambda c: (c[3], c[0], c[1]))


def tk_stored(slug, name, half):
    from learn import tk_baseline as TB

    D = json.loads((TB.OUT / "distances-dev.json").read_text())
    return D[slug][name][half]


# ============================================================== the machine

def disk_ok():
    return shutil.disk_usage(pathlib.Path.home()).free / 1e9 >= MIN_FREE_GB


def wait_slot():
    """Block until fewer than 3 other render processes run (local_objective.RENDERS) and no
    separation runs."""
    from learn import local_objective as LO

    LO._wait_cap(LO.CAP)


def shard(items, i, n):
    return items[i::n]


def _load(path):
    return {tuple(k.rsplit("/", 1)) if "/" in k else ("", k): v for k, v in json.loads(path.read_text()).items()}


def _save_settings(path, x):
    path.write_text(json.dumps({f"{m}/{k}" if m else k: v for (m, k), v in x.items()}, indent=0))


# ============================================================== commands that render

def screen(out, limit=None):
    """0c: per cell, S's bases and one control moved at a time, judged against the record."""
    import numpy as np

    from learn import confirm_run as CR

    wait_slot()
    ps = K.parts()
    from learn import knob_ceiling2 as K2

    slugs = sorted({s for s, _, _, _ in K2.stage_cells()})
    cells = screen_cells(slugs, {s: ps[s]["gain_class"] for s in slugs})[:limit]
    res = {"cells": [], "renders": 0}
    neutral = {c.path: c.neutral for c in table()}
    rr, menu = None, None
    try:
        for pack, slug, which in cells:
            if not disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            part = ps[slug]
            ref = CR.mono(part["crop"] / "reference.wav")
            if pack == "morgan":
                if rr is None or not isinstance(rr, K.Renderer):
                    rr and rr.close()
                    rr = K.Renderer()
                    menu = rr.menu()
                select, S = menu[which][K.START[part["gain_class"]][which]]
                di = K.measure_di(part)
                di32 = di.astype(np.float32)
                ren = lambda x: rr.render(di32, select, x)                    # noqa: E731
                jud = lambda y: K.judge(ref, y, di, part["judge_lag"])         # noqa: E731
            else:
                rr and rr.close()
                name, dry = tk_starts()[which]
                rr = ToneKingRenderer(dry)
                S = tk_start(rr.state)
                tp = tk_parts()[slug]
                di = tk_di(slug)
                di32 = di.astype(np.float32)
                ref = CR.mono(pathlib.Path(tp["crop"]) / "reference.wav")
                ren = lambda x: rr.render(di32, x)                             # noqa: E731
                jud = lambda y: tk_judge(ref, y, di, tp["judge_lag"])          # noqa: E731
            n0 = rr.count
            ren(screen_base("cab", S, pack))                                   # priming
            cell = {"pack": pack, "slug": slug, "amp_or_class": which, "band": part["band"], "moves": {}}
            bases = {}
            for kind, what in screen_plan(pack):
                base = screen_base(kind, S, pack)
                if what is None:
                    y = ren(base)
                    bases[kind] = (base, jud(y), y)
                    continue
                b, bj, by_ = bases[kind]
                if what == "repeat":
                    y = ren(b)
                    cell["repeat"] = {h: abs(math.log(jud(y)[h] / bj[h])) for h in bj}
                    continue
                x = dict(b)
                x[what] = far(SCREEN_DIMS[what], b.get(what, neutral[what]))
                y = ren(x)
                j = jud(y)
                lag0 = K.judge(by_, y, di, 0) if pack == "morgan" else None
                cell["moves"]["|".join(what)] = {
                    "from": b.get(what), "to": x[what], "base": bj, "moved": j,
                    "delta": max(abs(math.log(j[h] / bj[h])) if K.finite(j[h], bj[h]) else math.inf for h in bj),
                    "self_distance": lag0}
            cell["renders"] = rr.count - n0
            res["renders"] += cell["renders"]
            res["cells"].append(cell)
            print(pack, slug, which, {k: round(v["delta"], 4) for k, v in cell["moves"].items()}, flush=True)
    finally:
        if rr is not None:
            rr.close()
    rows = {}
    for c in res["cells"]:
        for k, v in c["moves"].items():
            rows.setdefault(k, []).append(v["delta"])
    res["invisible"] = invisible(rows)
    res["rule"] = f"invisible: |log(moved/base)| <= {REPEAT_TOL} on both halves in every cell"
    res["by_maths"] = {"parameters|outputGain": "level only (the judge removes level)",
                       "a single cab's pan": "level only after the mono fold"}
    out.mkdir(parents=True, exist_ok=True)
    K._atomic(out / "screen.json", res)
    print("invisible:", sorted(k for k, v in res["invisible"].items() if v), "renders", res["renders"])


def tk_smoke(out, renders=30, slug=None):
    """0d's smoke: the class start rendered against its stored score (repeat), then `renders`
    renders of the search on one cell, timed."""
    import time

    import numpy as np

    from learn import confirm_run as CR

    wait_slot()
    ps = tk_parts()
    slug = slug or sorted(ps)[0]
    cls = ps[slug]["gain_class"]
    name, dry = tk_starts()[cls]
    rr = ToneKingRenderer(dry)
    try:
        di = tk_di(slug)
        di32 = di.astype(np.float32)
        ref = CR.mono(pathlib.Path(ps[slug]["crop"]) / "reference.wav")
        x0 = tk_start(rr.state)
        t0 = time.time()
        rr.render(di32, x0)                                                    # priming
        first = tk_judge(ref, rr.render(di32, x0), di, ps[slug]["judge_lag"])
        canon0 = tk_judge(ref, rr.render(di32, tk_canon(x0)), di, ps[slug]["judge_lag"])
        stored = {h: tk_stored(slug, name, h) for h in ("A", "B")}
        rep = {h: abs(math.log(first[h] / stored[h])) for h in stored}
        rep_canon = {h: abs(math.log(canon0[h] / first[h])) for h in stored}
        times, evals = [], []

        def f(x):
            t = time.time()
            d = tk_judge(ref, rr.render(di32, x), di, ps[slug]["judge_lag"])
            times.append(time.time() - t)
            evals.append(d)
            return d["A"]

        K.knob_search(tk_space(set(SCREEN_DIMS)), x0, f, renders, SEED_TK, canon=tk_canon)
        again = tk_judge(ref, rr.render(di32, x0), di, ps[slug]["judge_lag"])
        res = {"slug": slug, "class": cls, "start": name, "stored": stored, "first": first,
               "repeat_vs_stored": rep, "canon_vs_raw_start": rep_canon,
               "after_search_vs_first": {h: abs(math.log(again[h] / first[h])) for h in first},
               "search_renders": len(evals), "median_s": statistics.median(times) if times else None,
               "renders": rr.count, "wall_s": time.time() - t0,
               "best_A": min(d["A"] for d in evals) if evals else None}
    finally:
        rr.close()
    out.mkdir(parents=True, exist_ok=True)
    K._atomic(out / "tk-smoke.json", res)
    print(json.dumps(res, indent=1))


def stage1(out, i, n, screen_path, assume_visible=False, budget=GROUP_BUDGET, limit=None):
    """Morgan: per cell, the stored stage-2 setting (rendered once more, the repeat check), then
    each group searched on its own from it."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import knob_ceiling2 as K2

    wait_slot()
    visible = visible_set(screen_path, assume_visible)
    ps = K.parts()
    rr = K.Renderer()
    done = 0
    try:
        menu = rr.menu()
        for slug, search, held, amp in shard(K2.stage_cells(), i, n):
            if limit is not None and done >= limit:
                break
            path = out / "stage1" / slug / f"{search}.json"
            if path.exists():
                continue
            if not disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            part = ps[slug]
            di = K.measure_di(part)
            di32 = di.astype(np.float32)
            ref = CR.mono(part["crop"] / "reference.wav")
            select = next(iter(menu[amp].values()))[0]
            base = _load(K2.OUT / "stage2" / slug / f"{search}-settings.json")
            stored = json.loads((K2.OUT / "stage2" / slug / f"{search}.json").read_text())
            n0 = rr.count
            rr.render(di32, select, base)                                       # priming
            b = K.judge(ref, rr.render(di32, select, base), di, part["judge_lag"])
            repeat = abs(math.log(b[search] / stored["search"]))
            repeat_held = abs(math.log(b[held] / stored["held"]))           # logged, not gating
            if repeat > REPEAT_TOL:
                raise RuntimeError(f"repeat moved {repeat:.4f} on {slug} {amp} {search}")
            res = {"slug": slug, "amp": amp, "search_half": search, "held_half": held, "band": part["band"],
                   "gain_class": part["gain_class"], "base": b, "repeat": repeat, "repeat_held": repeat_held,
                   "groups": {}}
            settings = {}
            for gi, group in enumerate(GROUPS):
                plan = group_plan(group, base, visible)
                if plan is None:
                    res["groups"][group] = {"applies": False}
                    continue
                start, dims = plan
                evals = []

                def f(x):
                    d = K.judge(ref, rr.render(di32, select, x), di, part["judge_lag"])
                    evals.append(d)
                    return d[search]

                x, _, _, stages = K.knob_search(dims, start, f, budget, SEED_STAGE1 + gi,
                                                canon=group_canon(group, amp))
                g = group_result(b, evals, search, held)
                g.update(applies=True, dims=[d.name for d in dims], stages=stages,
                         evals=[(d["A"], d["B"]) for d in evals],
                         changed={f"{m}/{k}": v for (m, k), v in x.items() if base.get((m, k)) != v})
                res["groups"][group] = g
                settings[group] = x
            res["renders"] = rr.count - n0
            path.parent.mkdir(parents=True, exist_ok=True)
            for group, x in settings.items():
                if res["groups"][group]["adopted"]:
                    _save_settings(path.parent / f"{search}-{group}-settings.json", x)
            K._atomic(path, res)
            done += 1
            print(slug, amp, search, {g: round(v["log_held"], 4) for g, v in res["groups"].items() if v.get("applies")},
                  res["renders"], f"repeat {repeat:.2g} held {repeat_held:.2g}", flush=True)
    finally:
        rr.close()


def tk_stage1(out, i, n, screen_path, assume_visible=False, budget=TK_BUDGET, limit=None):
    """Tone King: per cell, the class start (repeat check against tk_baseline's stored score),
    then the whole searched space, `budget` renders."""
    import numpy as np

    from learn import confirm_run as CR

    wait_slot()
    visible = visible_set(screen_path, assume_visible)
    dims = tk_space(visible)
    ps, starts = tk_parts(), tk_starts()
    rr, rr_cls, done = None, None, 0
    try:
        for slug, search, held, cls in shard(tk_cells(), i, n):
            if limit is not None and done >= limit:
                break
            path = out / "tk-stage1" / slug / f"{search}.json"
            if path.exists():
                continue
            if not disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            name, dry = starts[cls]
            if rr_cls != cls:
                rr and rr.close()
                rr, rr_cls = ToneKingRenderer(dry), cls
            p = ps[slug]
            di = tk_di(slug)
            di32 = di.astype(np.float32)
            ref = CR.mono(pathlib.Path(p["crop"]) / "reference.wav")
            x0 = tk_start(rr.state)
            n0 = rr.count
            rr.render(di32, tk_canon(x0))                                       # priming
            evals = []

            stored = tk_stored(slug, name, search)

            def f(x):
                d = tk_judge(ref, rr.render(di32, x), di, p["judge_lag"])
                evals.append(d)
                if len(evals) == 1:                    # the canonical start against tk_baseline's score
                    rep = abs(math.log(d[search] / stored))
                    if rep > REPEAT_TOL:
                        raise RuntimeError(f"Tone King repeat moved {rep:.4f} on {slug} {search}")
                return d[search]

            x, _, _, stages = K.knob_search(dims, x0, f, budget, SEED_TK, canon=tk_canon)
            repeat = abs(math.log(evals[0][search] / stored))
            inc = min(evals, key=lambda d: d[search])
            res = {"slug": slug, "class": cls, "start": name, "search_half": search, "held_half": held,
                   "band": p["band"], "gain_class": p["gain_class"], "repeat": repeat,
                   "start_search": evals[0][search], "start_held": evals[0][held],
                   "search": inc[search], "held": inc[held], "stages": stages,
                   "evals": [(d["A"], d["B"]) for d in evals], "renders": rr.count - n0,
                   "channel": x[("", "ampType")],
                   "changed": {k: v for (_, k), v in x.items() if x0.get(("", k)) != v}}
            path.parent.mkdir(parents=True, exist_ok=True)
            _save_settings(path.parent / f"{search}-settings.json", x)
            K._atomic(path, res)
            done += 1
            print(slug, cls, search, round(math.log(res["held"] / res["start_held"]), 4), res["renders"], flush=True)
    finally:
        if rr is not None:
            rr.close()


# ============================================================== listening (stage 1)

LISTEN_GROUPS = ("gate", "doubler", "rooms")
TOP_PER_GROUP = 2
NEAR_TIES = 2
NEAR_TIE = 0.005


def listen_choose(rows, seed=SEED_LISTEN):
    """rows: [(slug, search, group, log_held)] of adopted gate/doubler/room cells. Declared:
    per group the TOP_PER_GROUP largest held gains (most negative, below 0; one direction per
    part, at most one trial per part overall), slots left over filled from any group by the
    next largest gains; then NEAR_TIES near-ties (|log_held| < 0.005) on parts not yet used,
    drawn with random.Random(seed), the smallest |log_held| if none. -> [(row, why)], 8 at most."""
    rows = sorted(rows, key=lambda r: (r[3], r[0], r[1], r[2]))
    picks, used = [], set()
    for g in LISTEN_GROUPS:
        for r in [r for r in rows if r[2] == g and r[3] < 0]:
            if len([p for p in picks if p[0][2] == g]) >= TOP_PER_GROUP:
                break
            if r[0] not in used:
                picks.append((r, "gain"))
                used.add(r[0])
    for r in rows:
        if len(picks) >= len(LISTEN_GROUPS) * TOP_PER_GROUP:
            break
        if r[3] < 0 and r[0] not in used:
            picks.append((r, "gain-fill"))
            used.add(r[0])
    rest = [r for r in rows if r[0] not in used]
    ties = sorted((r for r in rest if abs(r[3]) < NEAR_TIE), key=lambda r: (r[0], r[1], r[2]))
    chosen = random.Random(seed).sample(ties, min(NEAR_TIES, len(ties)))
    if len(chosen) < NEAR_TIES:
        others = sorted((r for r in rest if r not in chosen and r[0] not in {c[0] for c in chosen}),
                        key=lambda r: (abs(r[3]), r[0], r[1], r[2]))
        chosen += others[:NEAR_TIES - len(chosen)]
    seen = set()
    for r in chosen:
        if r[0] not in seen:
            picks.append((r, "near-tie"))
            seen.add(r[0])
    return picks


def letters(n_trials, seed=SEED_LISTEN + 1):
    """Per trial, the position (0 = A, 1 = B) of the group's setting, drawn at random."""
    rng = random.Random(seed)
    return [rng.randrange(2) for _ in range(n_trials)]


def listening_build(out):
    import tempfile

    import numpy as np

    from learn import build_knob_listening as B
    from learn import confirm_run as CR
    from learn import knob_ceiling2 as K2

    wait_slot()
    rows = []
    for p in sorted((out / "stage1").glob("*/[AB].json")):
        r = json.loads(p.read_text())
        for g in LISTEN_GROUPS:
            v = r["groups"].get(g, {})
            if v.get("adopted"):
                rows.append((r["slug"], r["search_half"], g, v["log_held"]))
    picks = listen_choose(rows)
    random.Random(SEED_LISTEN).shuffle(picks)
    pos = letters(len(picks))
    ps = K.parts()
    dest = K.HOME / "listening" / "every-control"
    rr = K.Renderer()
    key, sections = {"seed": SEED_LISTEN, "trials": {}}, []
    try:
        menu = rr.menu()
        with tempfile.TemporaryDirectory() as tmp:
            for n, ((slug, search, group, lg), why) in enumerate(picks, 1):
                res = json.loads((out / "stage1" / slug / f"{search}.json").read_text())
                amp, held = res["amp"], res["held_half"]
                part = ps[slug]
                di32 = K.measure_di(part).astype(np.float32)
                select = next(iter(menu[amp].values()))[0]
                base = _load(K2.OUT / "stage2" / slug / f"{search}-settings.json")
                new = _load(out / "stage1" / slug / f"{search}-{group}-settings.json")
                rr.render(di32, select, base)                                    # priming
                opts = {"base": rr.render(di32, select, base), "group": rr.render(di32, select, new)}
                names = ["base"]
                names.insert(pos[n - 1], "group")
                ref = B.fade(B.level(B.clip(CR.mono(part["crop"] / "reference.wav"), held)))
                html = [f'<div class="row"><b>Record</b><audio controls preload="none" src="{B.aac(ref, tmp)}">'
                        f'</audio></div>']
                for L, nm in zip("AB", names):
                    y = np.array(opts[nm], np.float64)
                    y[:int(TRIM_S * 48000)] = 0
                    x = B.fade(B.level(B.clip(y, held)))
                    html.append(f'<div class="row"><b>{L}</b><audio controls preload="none" '
                                f'src="{B.aac(x, tmp)}"></audio></div>')
                buttons = "".join(f'<button type="button" data-value="{L}">{L}</button>' for L in "AB")
                sections.append(f'<section><h2>Trial {n}</h2>{"".join(html)}'
                                f'<div class="pick" data-trial="{n}">{buttons}</div></section>')
                key["trials"][str(n)] = {"slug": slug, "amp": amp, "search": search, "held": held, "group": group,
                                         "why": why, "log_held": lg, "letters": dict(zip("AB", names))}
                print(n, slug, amp, search, group, why, round(lg, 4), flush=True)
    finally:
        rr.close()
    import hashlib
    import re

    build_id = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]
    page = B.PAGE.format(count=len(sections), build=build_id, trials="\n".join(sections))
    page = page.replace("Knob listening check", "Every-control listening check")
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", page).lower()
    for word in {p[0][0] for p in picks} | {"pr12", "sw50r", "ac20", "gate", "doubler", "room"}:
        assert word.lower() not in text, word
    (dest / "private").mkdir(parents=True, exist_ok=True)
    old = dest / "private" / "key.json"
    if old.exists():
        old.rename(old.with_name(f"key-{int(old.stat().st_mtime)}.json"))
    (dest / "private" / "key.json").write_text(json.dumps(key, indent=1))
    (dest / "every-control-listening.html").write_text(page)
    print(dest / "every-control-listening.html")


EAR_GROUPS = ("gate", "doubler")          # enter only where the ear agrees; rooms by the judge


def listening_verdict(trials, answers):
    """The declared rule per group. trials: {n: key trial}; answers: {n: letter}. A group's own
    clear-gain trials are its "gain" trials (not the fill, not the near-ties). Gate and doubler:
    fewer than 2 -> keeps its rule (not shown by ear); the group's setting picked on both -> the
    ear agrees (it enters if the judge's interval is also below 0); else the ear disagrees ->
    keeps its rule. Rooms: descriptive."""
    out = {}
    for g in LISTEN_GROUPS:
        own = [n for n, t in trials.items() if t["group"] == g and t["why"] == "gain"]
        picks = [t_pick for t_pick in (trials[n]["letters"].get(answers.get(n, "?")) for n in own)]
        got = sum(p == "group" for p in picks)
        if g not in EAR_GROUPS:
            verdict = "descriptive (decided by the judge)"
        elif len(own) < TOP_PER_GROUP:
            verdict = "fewer than 2 clear-gain trials: keeps its rule (not shown by ear)"
        elif got == len(own):
            verdict = "ear agrees: enters if the judge's interval is below 0"
        else:
            verdict = "ear disagrees: keeps its rule"
        out[g] = {"trials": len(own), "picked_group": got, "verdict": verdict}
    return out


def listening_score(answers):
    key = json.loads((K.HOME / "listening" / "every-control" / "private" / "key.json").read_text())
    ans = dict((t[:-1], t[-1]) for t in answers.split())
    wins = {"group": 0, "base": 0}
    for n, t in sorted(key["trials"].items(), key=lambda kv: int(kv[0])):
        pick = t["letters"].get(ans.get(n, "?"))
        if pick:
            wins[pick] += 1
        print(n, t["slug"], t["group"], t["why"], round(t["log_held"], 4), "picked", pick)
    print("picked:", wins, "of", len(key["trials"]))
    for g, v in listening_verdict(key["trials"], ans).items():
        print(f"{g}: {v['picked_group']}/{v['trials']} own clear-gain trials -> {v['verdict']}")


# ============================================================== report

def _per_part(rows):
    by = {}
    for slug, band, cls, v in rows:
        by.setdefault((slug, band, cls), []).append(v)
    return [(slug, band, cls, statistics.fmean(v)) for (slug, band, cls), v in by.items()]


def _stats(rows, keep):
    from learn import confirm_run as CR

    sel = [(b, v) for _, b, c, v in _per_part(rows) if c in keep]
    if len({b for b, _ in sel}) < 2:
        return {"n": len(sel), "note": "too few bands"}
    s = CR.stats(sel)
    s["reading"] = reading(s)
    return s


def report(out):
    from learn import knob_ceiling2 as K2

    res = {}
    for name in ("screen.json", "amp-choice.json", "tk-smoke.json"):
        if (out / name).exists():
            res[name.split(".")[0]] = json.loads((out / name).read_text())
    s1 = [json.loads(p.read_text()) for p in sorted((out / "stage1").glob("*/[AB].json"))]
    tk = [json.loads(p.read_text()) for p in sorted((out / "tk-stage1").glob("*/[AB].json"))]
    res["stage1_cells"], res["tk_cells"] = len(s1), len(tk)
    res["renders"] = {"stage1": sum(r["renders"] for r in s1), "tk_stage1": sum(r["renders"] for r in tk),
                      "screen": res.get("screen", {}).get("renders", 0)}
    groups = (("clean+crunch", ("clean", "crunch")), ("clean", ("clean",)), ("crunch", ("crunch",)))
    for g in GROUPS:
        rows = [(r["slug"], r["band"], r["gain_class"], r["groups"][g]["log_held"])
                for r in s1 if r["groups"].get(g, {}).get("applies")]
        res[f"group_{g}"] = {name: _stats(rows, keep) for name, keep in groups}
        res[f"group_{g}"]["cells"] = len(rows)
        res[f"group_{g}"]["adopted"] = sum(r["groups"][g]["adopted"] for r in s1 if r["groups"].get(g, {}).get("applies"))
    if tk:
        k2 = {}
        for p in sorted((K2.OUT / "stage2").glob("*/[AB].json")):
            r = json.loads(p.read_text())
            k2[(r["slug"], r["search_half"])] = r
        rows = [(r["slug"], r["band"], r["gain_class"], math.log(r["held"] / r["start_held"])) for r in tk]
        res["tk_searched_vs_start"] = {name: _stats(rows, keep) for name, keep in groups}
        rows = [(r["slug"], r["band"], r["gain_class"], math.log(r["held"] / k2[(r["slug"], r["search_half"])]["held"]))
                for r in tk if (r["slug"], r["search_half"]) in k2]
        res["tk_searched_vs_morgan_stage2 (descriptive)"] = {name: _stats(rows, keep) for name, keep in groups}
        res["tk_repeat_max"] = max(r["repeat"] for r in tk)
    if s1:
        res["stage1_repeat_max"] = max(r["repeat"] for r in s1)
    out.mkdir(parents=True, exist_ok=True)
    K._atomic(out / "result.json", res)
    for k, v in res.items():
        if isinstance(v, dict) and "clean+crunch" in v and "mean" in v["clean+crunch"]:
            s = v["clean+crunch"]
            print(f"{k:45s} mean {s['mean']:+.3f} band-w {s['band_weighted_mean']:+.3f} "
                  f"90% [{s['lo90']:+.3f}, {s['hi90']:+.3f}] bands- {s['bands_negative']}/{s['bands']} {s['reading']}")
    print("renders", res["renders"])


# ============================================================== main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("table", "amp-choice", "screen", "tk-smoke", "stage1", "tk-stage1",
                                     "listening", "report"))
    ap.add_argument("what", nargs="?", choices=("build", "score"))
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--screen", type=pathlib.Path, help="screen.json (default: <out>/screen.json)")
    ap.add_argument("--assume-visible", action="store_true",
                    help="smoke only: treat every screened control as visible (refused for the real output)")
    ap.add_argument("--budget", type=int, help="smoke only: renders per group (Morgan) or cell (Tone King)")
    ap.add_argument("--limit", type=int, help="smoke only: at most this many cells")
    ap.add_argument("--renders", type=int, default=30)
    ap.add_argument("--answers", default="")
    a = ap.parse_args(argv)
    smoke = a.assume_visible or a.budget is not None or a.limit is not None
    if smoke and a.out.resolve() == OUT.resolve():
        raise SystemExit("smoke options write to a scratch --out only")
    i, n = map(int, a.shard.split("/"))
    scr = a.screen or a.out / "screen.json"
    if a.step == "table":
        T = table()
        a.out.mkdir(parents=True, exist_ok=True)
        K._atomic(a.out / "table.json", [c.__dict__ | {"gate": [list(map(str, g)) for g in c.gate]} for c in T])
        for amp in MORGAN_AMPS:
            print("morgan", amp, counts("morgan", amp))
        print("toneking", counts("toneking"))
    elif a.step == "amp-choice":
        amp_choice(a.out)
    elif a.step == "screen":
        screen(a.out, a.limit)
    elif a.step == "tk-smoke":
        tk_smoke(a.out, a.renders)
    elif a.step == "stage1":
        stage1(a.out, i, n, scr, a.assume_visible, a.budget or GROUP_BUDGET, a.limit)
    elif a.step == "tk-stage1":
        tk_stage1(a.out, i, n, scr, a.assume_visible, a.budget or TK_BUDGET, a.limit)
    elif a.step == "listening":
        listening_build(a.out) if a.what == "build" else listening_score(a.answers)
    else:
        report(a.out)


if __name__ == "__main__":
    main()
