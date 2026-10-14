"""Knob ceiling 2: pedals and time effects (`docs/knob-ceiling-2-plan.md`). Development only.

    .venv/bin/python -m learn.knob_ceiling2 control               # stage 1's realistic control
    .venv/bin/python -m learn.knob_ceiling2 stage1 --shard 0/4
    .venv/bin/python -m learn.knob_ceiling2 stage2 --shard 0/4
    .venv/bin/python -m learn.knob_ceiling2 report
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import shutil
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import confirm_run as CR  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn.knob_ceiling import Dim  # noqa: E402

OUT = K.HOME / "learn/knob-ceiling-2"
SEED1, SEED2 = 20261014, 20261015
BUDGET1, BUDGET2 = 200, 100
WET_MARGIN = 0.005
MIN_FREE_GB = 31.0
REPEAT_TOL = 0.005

# --- stage 1: pedals --------------------------------------------------------------------------

PEDALS = {  # module: (switch key, {knob key: neutral stored value})
    "compressor": ("compressorActive", {"compressorCompression": "0.4", "compressorLevel": "0.5",
                                        "compressorMix": "0.5"}),
    "drive1": ("drive1Active", {"drive1Drive": "0.3", "drive1Level": "0.5", "drive1Tone": "0.5"}),
    "drive2": ("drive2Active", {"drive2Gain": "0.3", "drive2Level": "0.5", "drive2Bass": "0.5",
                                "drive2Treble": "0.5"}),
}
HELD_ON = {("pedalParameters", "sectionActive"): "true", ("eqParameters", "sectionActive"): "true"}


def pedal_dims():
    out = []
    for m, (sw, knobs) in PEDALS.items():
        out.append(Dim(m, sw, "switch", values=("false", "true")))
        out += [Dim(m, k, "cont") for k in knobs]
    out.append(Dim("compressor", "compressorRelease", "switch", values=("false", "true")))
    return out


def _off(x, module, switch):
    return str(x.get((module, switch), "false")).lower() not in ("true", "1")


def canon_pedals(x):
    """An off pedal's knobs to the neutral values (the sound doesn't change)."""
    y = dict(x)
    for m, (sw, knobs) in PEDALS.items():
        if _off(y, m, sw):
            y.update({(m, k): v for k, v in knobs.items()})
            if m == "compressor":
                y[(m, "compressorRelease")] = "false"
    return y


def stage1_space(amp, start):
    """Core knobs (input gain −24 to +12 dB), the amp's EQ, the pedals; the mics held."""
    core = [d for d in K.space(amp, start) if d.kind != "cat" and d.key != "inputGain"]
    return [Dim("parameters", "inputGain", "cont", -24.0, 12.0)] + core + K.eq_space(amp) + pedal_dims()


def stage1_start(eq_settings, amp):
    x = K.eq_start(eq_settings, amp)
    x.update(HELD_ON)
    return canon_pedals(x)


# --- stage 2: time effects --------------------------------------------------------------------

EFFECTS = {  # name: (switch (module, key) or None, {(module, key): declared "on" value}, dims)
    "reverb": (("reverb", "reverbActive"),
               {("reverb", "reverbMix"): "0.2", ("reverb", "reverbDecay"): "1.8",
                ("reverb", "reverbPreDelay"): "20", ("reverb", "reverbLowCut"): "100",
                ("reverb", "reverbHighCut"): "6000"},
               [Dim("reverb", "reverbMix", "cont"), Dim("reverb", "reverbDecay", "log", 1.0, 6.0),
                Dim("reverb", "reverbPreDelay", "log", 1.0, 120.0), Dim("reverb", "reverbLowCut", "log", 50.0, 700.0),
                Dim("reverb", "reverbHighCut", "log", 1000.0, 10000.0)]),
    "delay": (("delay", "delayActive"),
              {("delay", "delayMix"): "0.2", ("delay", "delayFeedback"): "0.25", ("delay", "delayTime"): "350",
               ("delay", "delayLowCut"): "100", ("delay", "delayHighCut"): "4000"},
              [Dim("delay", "delayMix", "cont"), Dim("delay", "delayFeedback", "cont"),
               Dim("delay", "delayTime", "log", 60.0, 800.0), Dim("delay", "delayLowCut", "log", 60.0, 500.0),
               Dim("delay", "delayHighCut", "log", 1000.0, 5000.0)]),
    "tremolo": (("tremolo", "tremoloActive"),
                {("tremolo", "tremoloDepth"): "0.4", ("tremolo", "tremoloRate"): "4"},
                [Dim("tremolo", "tremoloDepth", "cont"), Dim("tremolo", "tremoloRate", "log", 1.0, 10.0)]),
}
SPRING = {"pr12": ({("pr12Amp", "pr12Reverb"): "0.2", ("pr12Amp", "pr12Dwell"): "0.5"},
                   [Dim("pr12Amp", "pr12Reverb", "cont"), Dim("pr12Amp", "pr12Dwell", "cont")]),
          "sw50r": ({("sw50rAmp", "sw50rReverb"): "0.2"}, [Dim("sw50rAmp", "sw50rReverb", "cont")])}
SPRING_SWITCH = "springOn"          # a pseudo-switch: spring level 0 (off) or the searched value
FREE_SYNC = {("delay", "delaySync"): "0", ("tremolo", "tremoloSync"): "false",
             ("fxParameters", "sectionActive"): "true"}


def stage2_space(amp):
    out = []
    for name, (sw, _, dims) in EFFECTS.items():
        out.append(Dim(*sw, "switch", values=("false", "true")))
        out += dims
    if amp in SPRING:
        out.append(Dim("spring", SPRING_SWITCH, "switch", values=("false", "true")))
        out += SPRING[amp][1]
    return out


def make_canon_effects(amp):
    def canon(x):
        y = dict(x)
        y.update(FREE_SYNC)
        for name, (sw, on, _) in EFFECTS.items():
            if _off(y, *sw):
                y.update(on)
        if amp in SPRING:
            if _off(y, "spring", SPRING_SWITCH):
                y.update(SPRING[amp][0])
        return y
    return canon


def plugin_settings(x, amp):
    """The pseudo spring switch made real: off means the spring's level at 0."""
    y = {k: v for k, v in x.items() if k[0] != "spring"}
    if amp in SPRING and _off(x, "spring", SPRING_SWITCH):
        level = next(iter(SPRING[amp][0]))
        y[level] = "0"
    return y


def stage2_start(x, amp):
    y = dict(x)
    for name, (sw, on, _) in EFFECTS.items():
        y[sw] = "false"
    y[("spring", SPRING_SWITCH)] = "false"
    return make_canon_effects(amp)(y)


# --- cells -----------------------------------------------------------------------------------

def kc_cells():
    out = {}
    for p in sorted((K.OUT / "cells").glob("*/*/result.json")):
        c = json.loads(p.read_text())
        out[(c["slug"], c["amp"])] = c
    return out


def best_amp(cells, slug, search):
    """The amp whose knob-ceiling EQ stage is lowest on the search half (no held half used)."""
    cands = [(c["runs"][search]["EQ"]["search"], a) for (s, a), c in cells.items()
             if s == slug and "skipped" not in c["runs"][search]]
    return min(cands)[1] if cands else None


def stage_cells():
    cells = kc_cells()
    out = []
    for slug in sorted({s for s, _ in cells}):
        for search, held in K.DIRECTIONS:
            amp = best_amp(cells, slug, search)
            if amp is not None:
                out.append((slug, search, held, amp))
    return out


def disk_ok():
    return shutil.disk_usage(pathlib.Path.home()).free / 1e9 >= MIN_FREE_GB


def _settings_json(x):
    return {f"{m}/{k}": v for (m, k), v in x.items()}


def _load_settings(path):
    return {tuple(k.rsplit("/", 1)): v for k, v in json.loads(path.read_text()).items()}


def search_cell(rr, menu, slug, amp, search, held, start, dims, budget, seed, canon, settings_fn=None):
    import numpy as np

    ps = K.parts()
    part = ps[slug]
    di = K.measure_di(part)
    ref = CR.mono(part["crop"] / "reference.wav")
    di32 = di.astype(np.float32)
    select = next(iter(menu[amp].values()))[0]
    conv = settings_fn or (lambda x: x)
    rr.render(di32, select, conv(start))                                   # warm-up
    evals = []

    def f(x):
        d = K.judge(ref, rr.render(di32, select, conv(x)), di, part["judge_lag"])
        evals.append(d)
        return d[search]

    x, best, hist, stages = K.knob_search(dims, start, f, budget, seed, canon=canon)
    inc = evals[0]
    for d in evals:
        if d[search] < inc[search] - 1e-12:
            inc = d
    return x, {"search": inc[search], "held": inc[held], "start_search": evals[0][search],
               "start_held": evals[0][held], "renders": len(evals), "stages": stages,
               "evals": [(d["A"], d["B"]) for d in evals],
               "changed": {f"{m}/{k}": v for (m, k), v in x.items() if start.get((m, k)) != v}}, \
        (rr, di32, select, ref, di, part)


def stage1(shard):
    cells = kc_cells()
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for slug, search, held, amp in stage_cells()[shard[0]::shard[1]]:
            d = OUT / "stage1" / slug
            if (d / f"{search}.json").exists():
                continue
            if not disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            eq = _load_settings(K.OUT / "cells" / slug / amp / f"EQ-{search}.json")
            start = stage1_start(eq, amp)
            dims = stage1_space(amp, start)
            x, res, (rr_, di32, select, ref, di, part) = search_cell(
                rr, menu, slug, amp, search, held, start, dims, BUDGET1, SEED1, canon_pedals)
            stored = cells[(slug, amp)]["runs"][search]["EQ"]["search"]
            res["repeat"] = abs(math.log(res["start_search"] / stored))
            if res["repeat"] > REPEAT_TOL:
                raise RuntimeError(f"repeat moved {res['repeat']:.4f} on {slug} {amp} {search}")
            # the ablation: pedals back to the start's; input gain clamped to −20 dB
            abl = {}
            pedals_back = dict(x)
            for m, (sw, knobs) in PEDALS.items():
                for k in [sw, *knobs]:
                    pedals_back[(m, k)] = start[(m, k)]
            pedals_back[("compressor", "compressorRelease")] = start[("compressor", "compressorRelease")]
            clamp = dict(x)
            clamp[("parameters", "inputGain")] = K.fmt(max(float(x[("parameters", "inputGain")]), -20.0))
            for name, y in (("pedals_reset", pedals_back), ("gain_clamped", clamp)):
                abl[name] = K.judge(ref, rr.render(di32, select, canon_pedals(y)), di, part["judge_lag"])
            res.update(slug=slug, amp=amp, search_half=search, held_half=held, band=part["band"],
                       gain_class=part["gain_class"], ablation=abl,
                       M=cells[(slug, amp)]["runs"][search]["M"],
                       M_held=cells[(slug, amp)]["menu"][cells[(slug, amp)]["runs"][search]["M"]][held],
                       KM_held=cells[(slug, amp)]["runs"][search]["K_M"]["held"])
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{search}-settings.json").write_text(json.dumps(_settings_json(x), indent=0))
            K._atomic(d / f"{search}.json", res)
            print(slug, amp, search, round(math.log(res["held"] / res["start_held"]), 4), rr.count, flush=True)
    finally:
        rr.close()


def stage2(shard):
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for slug, search, held, amp in stage_cells()[shard[0]::shard[1]]:
            d = OUT / "stage2" / slug
            s1 = OUT / "stage1" / slug / f"{search}-settings.json"
            if (d / f"{search}.json").exists() or not s1.exists():
                continue
            if not disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            start = stage2_start(_load_settings(s1), amp)
            canon = make_canon_effects(amp)
            x, res, (rr_, di32, select, ref, di, part) = search_cell(
                rr, menu, slug, amp, search, held, start, stage2_space(amp), BUDGET2, SEED2, canon,
                settings_fn=lambda y: plugin_settings(y, amp))
            s1res = json.loads((OUT / "stage1" / slug / f"{search}.json").read_text())
            res["repeat"] = abs(math.log(res["start_search"] / s1res["search"]))
            if res["repeat"] > REPEAT_TOL:
                raise RuntimeError(f"repeat moved {res['repeat']:.4f} on {slug} {amp} {search}")
            res["wet"] = math.log(res["search"] / res["start_search"]) <= -WET_MARGIN
            res.update(slug=slug, amp=amp, search_half=search, held_half=held, band=part["band"],
                       gain_class=part["gain_class"],
                       effects_on=[n for n, (sw, _, _) in EFFECTS.items() if not _off(x, *sw)]
                       + (["spring"] if amp in SPRING and not _off(x, "spring", SPRING_SWITCH) else []))
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{search}-settings.json").write_text(json.dumps(_settings_json(plugin_settings(x, amp)), indent=0))
            K._atomic(d / f"{search}.json", res)
            print(slug, amp, search, "wet" if res["wet"] else "dry", res["effects_on"], rr.count, flush=True)
    finally:
        rr.close()


# --- stage 1's realistic control ---------------------------------------------------------------

CONTROL_PARTS = ("cambridge-Drag_Me_Down-ElecGtr4", "cambridge-Prodigal-ElecGtr5")
CONTROL_MOVES = {("drive1", "drive1Active"): "true"}


def control():
    """Knob ceiling's realistic control on stage 1's space: the start with drive 1 switched on
    and moved (drive +0.21, level −0.13 from neutral), input gain +3.7 dB, the first amp knob
    −0.17 and EQ band 5 +2.3 dB, played with the raw DI; searched from the start with the
    measure DI on half A; scored on half B."""
    import numpy as np

    from learn.direc_check import to_lufs

    cells = kc_cells()
    ps = K.parts()
    rr = K.Renderer()
    out = {}
    try:
        menu = rr.menu()
        for slug in CONTROL_PARTS:
            part = ps[slug]
            di = K.measure_di(part)
            di32 = di.astype(np.float32)
            raw = to_lufs(CR.mono(part["crop"] / "di.wav")).astype(np.float32)
            for amp in K.AMPS:
                start = stage1_start(_load_settings(K.OUT / "cells" / slug / amp / "EQ-A.json"), amp)
                dims = stage1_space(amp, start)
                by = {(d.module, d.key): d for d in dims}
                knob = next(d for d in K.AMP_DIMS[amp] if d.kind == "cont")
                target = dict(start)
                target.update(CONTROL_MOVES)
                moves = {("drive1", "drive1Drive"): 0.21, ("drive1", "drive1Level"): -0.13,
                         ("parameters", "inputGain"): 3.7, (knob.module, knob.key): -0.17,
                         (f"{amp}EQ", f"{amp}EQBand5"): 2.3}
                target = K.perturbed(dims, target, moves)
                select = next(iter(menu[amp].values()))[0]
                rr.render(raw, select, start)
                fake = rr.render(raw, select, target)
                reach = K.judge(fake, rr.render(di32, select, target), di, 0)
                evals = []

                def f(x):
                    d = K.judge(fake, rr.render(di32, select, x), di, 0)
                    evals.append(d)
                    return d["A"]

                x, best, _, _ = K.knob_search(dims, start, f, BUDGET1, SEED1, canon=canon_pedals)
                inc = min(evals, key=lambda d: d["A"])
                out[f"{slug}|{amp}"] = {
                    "start": evals[0], "found_A": inc["A"], "found_B": inc["B"], "target": reach,
                    "gap_closed_B": (evals[0]["B"] - inc["B"]) / (evals[0]["B"] - reach["B"]),
                    "shortfall_B": math.log(inc["B"] / reach["B"]),
                    "drive1_on": not _off(x, "drive1", "drive1Active"),
                    "settings_error": {f"{m}/{k}": abs(by[(m, k)].to_unit(x[(m, k)]) - by[(m, k)].to_unit(target[(m, k)]))
                                       for (m, k) in moves}}
                r = out[f"{slug}|{amp}"]
                print(slug, amp, "gap", round(r["gap_closed_B"], 3), "shortfall", round(r["shortfall_B"], 3),
                      "drive1", r["drive1_on"], flush=True)
    finally:
        rr.close()
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "control.json", out)


# --- report ----------------------------------------------------------------------------------

def _per_part(rows):
    """rows: (slug, band, gain_class, value) per cell -> (band, gain_class, mean) per part."""
    by = {}
    for slug, band, cls, v in rows:
        by.setdefault((slug, band, cls), []).append(v)
    return [(band, cls, statistics.fmean(v)) for (slug, band, cls), v in by.items()]


def _stats(parts, keep=("clean", "crunch")):
    return CR.stats([(b, v) for b, c, v in parts if c in keep])


def report():
    s1 = [json.loads(p.read_text()) for p in sorted((OUT / "stage1").glob("*/[AB].json"))]
    s2 = [json.loads(p.read_text()) for p in sorted((OUT / "stage2").glob("*/[AB].json"))]
    out = {"stage1_cells": len(s1), "stage2_cells": len(s2)}
    lr = math.log
    comps1 = {
        "e_stage1_vs_EQstage": lambda r: lr(r["held"] / r["start_held"]),
        "f_stage1_vs_M": lambda r: lr(r["held"] / r["M_held"]),
        "stage1_vs_KM": lambda r: lr(r["held"] / r["KM_held"]),
        "ablation_pedals_reset_vs_stage1": lambda r: lr(r["ablation"]["pedals_reset"][r["held_half"]] / r["held"]),
        "ablation_gain_clamped_vs_stage1": lambda r: lr(r["ablation"]["gain_clamped"][r["held_half"]] / r["held"]),
    }
    for group, keep in (("clean+crunch", ("clean", "crunch")), ("clean", ("clean",)), ("crunch", ("crunch",))):
        g = {}
        for name, fn in comps1.items():
            g[name] = _stats(_per_part([(r["slug"], r["band"], r["gain_class"], fn(r)) for r in s1]), keep)
        if s2:
            g["stage2_vs_stage1 (judge)"] = _stats(_per_part(
                [(r["slug"], r["band"], r["gain_class"], lr(r["held"] / r["start_held"])) for r in s2]), keep)
        out[group] = g
    if s1:
        out["pedals_on"] = {m: sum(not _off({tuple(k.rsplit("/", 1)): v for k, v in json.loads(
            (OUT / "stage1" / r["slug"] / f"{r['search_half']}-settings.json").read_text()).items()}, m, sw) for r in s1)
            for m, (sw, _) in PEDALS.items()}
        out["input_gain_below_-20"] = sum(float(json.loads((OUT / "stage1" / r["slug"] / f"{r['search_half']}-settings.json")
                                                          .read_text())["parameters/inputGain"]) < -20 for r in s1)
        out["repeat_max"] = max(r["repeat"] for r in s1 + s2)
    if s2:
        out["wet_cells"] = sum(r["wet"] for r in s2)
        out["effects_on"] = {e: sum(e in r["effects_on"] for r in s2 if r["wet"])
                             for e in [*EFFECTS, "spring"]}
    K._atomic(OUT / "result.json", out)
    print(json.dumps({k: v for k, v in out.items() if not isinstance(v, dict) or k in ("pedals_on", "effects_on")}, indent=1))
    for group in ("clean+crunch", "clean", "crunch"):
        for name, s in out.get(group, {}).items():
            print(f"{group:13s} {name:36s} mean {s['mean']:+.3f} band-w {s['band_weighted_mean']:+.3f} "
                  f"90% [{s['lo90']:+.3f}, {s['hi90']:+.3f}] bands− {s['bands_negative']}/{s['bands']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("control", "stage1", "stage2", "report"))
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    i, n = map(int, a.shard.split("/"))
    {"control": lambda: control(), "stage1": lambda: stage1((i, n)), "stage2": lambda: stage2((i, n)),
     "report": lambda: report()}[a.step]()


if __name__ == "__main__":
    main()
