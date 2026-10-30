"""Zero-render checks behind the ML pipeline review (docs/ml-pipeline-review.md, 2026-10-30).

The review lists the direct model's pipeline as 38 small steps. Each check here reads stored files only
(no render, no separation, no training, no model load) and is named after the step it supports: s05 is
step 5. A check that needs a file that is missing reports {"missing": path} and the others still run.

Run with the main checkout's .venv (stdlib only; from a worktree, call the main checkout's .venv/bin/python):

    .venv/bin/python -m learn.pipeline_review                      # every check, JSON to stdout
    .venv/bin/python -m learn.pipeline_review --out docs/ml-pipeline-review.json
    .venv/bin/python -m learn.pipeline_review --only s16 s32       # some checks
    .venv/bin/python -m learn.pipeline_review --data-dir PATH      # another data root (default ~/ndsp-presets)
"""

import argparse
import hashlib
import json
import math
import pathlib
import statistics
import sys
import time

DATA = pathlib.Path("~/ndsp-presets").expanduser()
REPO = pathlib.Path(__file__).resolve().parents[1]

# V-real-11 (T3's frozen membership, t3/plan.json "vreal"): band and gain class from stage F's label table
# (arm_a_mega53.f_part), and the T3 crop's entry for It Was My Fault ElecGtr1. s34 asserts the mapping by
# reproducing the report's D_F5 - S row from the stored judges.
VREAL = {
    "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3": ("Atlantis Bound", "clean"),
    "cambridge-Signs-ElecGtr3": ("Zeno", "crunch"),
    "cambridge-colour-me-red-elecgtr02": ("Diesel13", "clean"),
    "cambridge-colour-me-red-elecgtr03": ("Diesel13", "clean"),
    "cambridge-femme-elecgtr5": ("Wall Of Death", "crunch"),
    "cambridge-get-out-of-bed-elecgtr2": ("Magician's Nephew", "crunch"),
    "cambridge-let-s-dance-elecgtr3": ("Szymon Skiba", "crunch"),
    "cambridge-wickerman-elecgtr1": ("Eat The Feeder", "crunch"),
    "cambridge-wickerman-elecgtr2": ("Eat The Feeder", "crunch"),
    "cambridge-wickerman-elecgtr3": ("Eat The Feeder", "crunch"),
    "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1": ("Atlantis Bound", "clean"),
}
IN_GROUP_S = {"cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1"}   # T3's own crop: S rendered in its V-real group
AMPS = ("pr12", "sw50r", "ac20")
HELD = {"A": "B", "B": "A"}
SWITCHES = {
    "drive1": "drive1/drive1Active", "drive2": "drive2/drive2Active", "compressor": "compressor/compressorActive",
    "reverb": "reverb/reverbActive", "delay": "delay/delayActive", "tremolo": "tremolo/tremoloActive",
    "doubler": "parameters/doublerActive", "gate": "parameters/gateActive",
}
DELAY_FEEDBACK = "delay/delayFeedback"
T_95 = {6: 1.9431802803927816}                                    # t(0.95, df), for the 7-band intervals


# --- pure helpers (tested in tests/test_pipeline_review.py) ------------------------------------------------------

def on(v):
    """A stored switch value ("true"/"false", bool or number) as a bool."""
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "1.0", "on")
    return bool(v)


def quantiles(xs, qs=(0.1, 0.5, 0.9)):
    """Linear-interpolated quantiles of xs (None when empty)."""
    s = sorted(xs)
    if not s:
        return {str(q): None for q in qs}
    out = {}
    for q in qs:
        pos = q * (len(s) - 1)
        lo, hi = math.floor(pos), math.ceil(pos)
        out[str(q)] = s[lo] + (s[hi] - s[lo]) * (pos - lo)
    return out


def section_parts(section):
    """'set/session/file.wav@145.0' -> (di path, start seconds)."""
    di, _, start = section.rpartition("@")
    return di, float(start)


def es_overlap(train_sections, es_sections, length=10.0):
    """How the early-stopping sections sit against the training sections: sharing a session, a DI, and a DI
    with an overlapping window (|start difference| < length)."""
    tr = [section_parts(s) for s in set(train_sections)]
    di_starts = {}
    for di, st in tr:
        di_starts.setdefault(di, []).append(st)
    sessions = {di.rsplit("/", 1)[0] for di, _ in tr}
    out = {"es_sections": 0, "share_session": 0, "share_di": 0, "overlap_in_time": 0}
    for s in sorted(set(es_sections)):
        di, st = section_parts(s)
        out["es_sections"] += 1
        out["share_session"] += di.rsplit("/", 1)[0] in sessions
        out["share_di"] += di in di_starts
        out["overlap_in_time"] += any(abs(st - t) < length for t in di_starts.get(di, []))
    return out


def band_weighted(rows):
    """rows: [(band, part, value)] -> parts averaged within a band, then the mean of band means; the 90%
    band-clustered t interval when the t value for its df is known (song_readout.bw_stats' rule)."""
    by_part = {}
    for band, part, v in rows:
        by_part.setdefault((band, part), []).append(v)
    by_band = {}
    for (band, _), vs in by_part.items():
        by_band.setdefault(band, []).append(statistics.fmean(vs))
    means = {b: statistics.fmean(v) for b, v in by_band.items()}
    m = statistics.fmean(means.values())
    g = len(means)
    t = T_95.get(g - 1)
    half = t * statistics.stdev(means.values()) / math.sqrt(g) if t and g > 1 else None
    parts = {p: statistics.fmean(vs) for (_, p), vs in sorted(by_part.items())}
    lobo = {b: statistics.fmean(v for c, v in means.items() if c != b) for b in sorted(means)} if g > 1 else {}
    return {"band_weighted_mean": m, "lo90": None if half is None else m - half,
            "hi90": None if half is None else m + half, "bands": g,
            "bands_worse": sum(v > 0 for v in means.values()), "bands_better": sum(v < 0 for v in means.values()),
            "parts": len(parts), "parts_worse": sum(v > 0 for v in parts.values()),
            "leave_one_band_out": lobo, "per_part": parts}


def mismatch_share(pairs):
    """pairs: [(a, b)] of switch values -> (count differing, n)."""
    n = len(pairs)
    return sum(on(a) != on(b) for a, b in pairs), n


# --- loaders --------------------------------------------------------------------------------------------------

def _json(p):
    return json.loads(pathlib.Path(p).read_text())


def _jsonl(paths):
    out = []
    for p in sorted(paths):
        out += [json.loads(l) for l in pathlib.Path(p).read_text().splitlines() if l.strip()]
    return out


class Data:
    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.td = self.root / "learn/trusted-data"
        self._cache = {}

    def get(self, key, f):
        if key not in self._cache:
            self._cache[key] = f()
        return self._cache[key]

    def cc_plan(self):
        return self.get("cc_plan", lambda: _json(self.td / "cc/plan.json"))

    def cc_built(self):
        """{i: build row} for D_CC's built examples (the 3,033 kept)."""
        def f():
            rows = _jsonl((self.td / "cc/rows").glob("build-*.jsonl"))
            return {r["i"]: r for r in rows if not r.get("refused") and r.get("snr_audio_db") is not None}
        return self.get("cc_built", f)

    def cc_kept(self):
        """D_CC's kept plan examples, {i: example}, split by 'set' (train / fs)."""
        built = self.cc_built()
        return {x["i"]: x for x in self.cc_plan()["examples"] if x["i"] in built}


# --- checks, one per review step ------------------------------------------------------------------------------

def s04_pool(d):
    """Step 4: the pool's size (D_CC kept examples; F5's planned sections)."""
    kept = d.cc_kept()
    out = {}
    for name in ("train", "fs"):
        xs = [x for x in kept.values() if x["set"] == name]
        out[f"cc_{name}"] = {"examples": len(xs), "sections": len({x["section"] for x in xs}),
                             "dis": len({x["di"] for x in xs}), "bands": len({x["band"] for x in xs})}
    t3 = _json(d.td / "t3/plan.json")
    for name in ("F5", "FS5"):
        xs = [x for x in t3["examples"] if x.get("set") == name]
        out[f"t3_{name.lower()}_planned"] = {"examples": len(xs), "sections": len({x["section"] for x in xs}),
                                     "bands": sorted({x["band"] for x in xs})}
    return out


def s05_class_input(d):
    """Step 5: the class fed to the network in training is the draw's base (a coin), not the section's class."""
    kept = d.cc_kept().values()
    n = len(kept)
    differ = sum(x["base"] != x["cls"] for x in kept)
    code = (REPO / "learn/direct_stems.py").read_text().splitlines()
    uses_base = [i + 1 for i, l in enumerate(code) if "cond_vec(" in l and '["base"]' in l]
    return {"kept_examples": n, "base_differs_from_section_class": differ, "share": differ / n,
            "direct_stems_lines_conditioning_on_base": uses_base,
            "vreal_conditioning": "trusted_data_t3.cmd_vreal_predict: cls from part_info (the part's real class)"}


def s06_label_prior(d):
    """Step 6: what the training labels look like (D_CC kept training examples)."""
    xs = [x for x in d.cc_kept().values() if x["set"] == "train"]
    n = len(xs)
    modes = {}
    for x in xs:
        modes[x["mode"]] = modes.get(x["mode"], 0) + 1
    rates = {k: sum(on(x["settings"].get(p)) for x in xs) / n for k, p in SWITCHES.items()}
    by_mode = {m: {k: sum(on(x["settings"].get(p)) for x in xs if x["mode"] == m) / c
                   for k, p in (("reverb", SWITCHES["reverb"]), ("delay", SWITCHES["delay"]))}
               for m, c in modes.items()}
    fb = [float(x["settings"][DELAY_FEEDBACK]) for x in xs if on(x["settings"].get(SWITCHES["delay"]))]
    return {"examples": n, "modes": modes, "switch_on_rate": rates, "reverb_delay_on_by_mode": by_mode,
            "delay_feedback_when_on": {**quantiles(fb), "n": len(fb), "share_ge_0.75": sum(v >= 0.75 for v in fb) / len(fb)}}


def s07_silent_refusals(d):
    """Step 7: near-silent target refusals by draw mode (D_CC render rows)."""
    files = list((d.td / "cc/rows").glob("render-*.jsonl"))
    if not files:
        raise FileNotFoundError(2, "no render rows", str(d.td / "cc/rows/render-*.jsonl"))
    rows = _jsonl(files)
    out = {}
    for r in rows:
        m = out.setdefault(r["mode"], {"rendered": 0, "target_near_silent": 0, "other_guitar_near_silent": 0})
        why = str(r.get("refused") or "")
        m["rendered"] += 1
        m["target_near_silent"] += why.startswith("target: near-silent")
        m["other_guitar_near_silent"] += bool(why) and not why.startswith("target:")
    for m in out.values():
        m["share"] = m["target_near_silent"] / m["rendered"]
    total = sum(m["rendered"] for m in out.values())
    built = _jsonl((d.td / "cc/rows").glob("build-*.jsonl"))
    return {"by_mode": out, "all": sum(m["target_near_silent"] for m in out.values()) / total, "rendered": total,
            "refused_in_all": len({r["i"] for r in built if r.get("refused")}), "kept": len(d.cc_built())}


def s12_doubles(d):
    """Step 12: a DT double is rendered with the target's core setting (cc_build.py: `if o["dt"]`), not its full
    twin, so its pedals and time effects can differ from the target's label."""
    xs = [x for x in d.cc_kept().values() if any(o.get("dt") for o in x.get("others", []))]
    out = {"kept_with_dt_double": len(xs), "kept": len(d.cc_kept())}
    for k in ("drive1", "drive2", "compressor"):
        c, n = mismatch_share([(x["core"].get(SWITCHES[k]), x["settings"].get(SWITCHES[k])) for x in xs])
        out[f"{k}_switch_differs"] = {"count": c, "share": c / n if n else None}
    out["target_time_effect_on_double_dry"] = sum(
        any(on(x["settings"].get(SWITCHES[k])) for k in ("reverb", "delay", "tremolo")) for x in xs)
    code = (REPO / "learn/cc_build.py").read_text().splitlines()
    out["cc_build_line"] = next(i + 1 for i, l in enumerate(code) if 'if o["dt"]:' in l)
    return out


def s13_stand_ins(d):
    """Step 13: kept examples that carry recorded amp-track stand-ins."""
    kept = d.cc_kept().values()
    c = sum(bool(x.get("amp_tracks")) for x in kept)
    return {"with_stand_ins": c, "kept": len(kept), "share": c / len(kept)}


def s14_level_draws(d):
    """Step 14: the drawn target-to-backing ratio (dB) and mastering, D_CC kept examples."""
    kept = list(d.cc_kept().values())
    r = [x["draw"]["ratio_db"] for x in kept]
    prior = {}                                         # pretrain_set.ratio_values' source: passing rows per file
    for f in sorted((d.root / "learn/multi-section/sections").glob("*.json")):
        m = _json(f)
        n = sum(1 for x in m["rows"] if x.get("passes") and x.get("snr_db") is not None)
        if n:
            prior[f.stem] = (m.get("band") or f.stem, n)
    vreal_bands = {b for b, _ in VREAL.values()}
    return {"ratio_prior": {"bands": len({b for b, _ in prior.values()}), "values": sum(n for _, n in prior.values()),
                            "vreal_bands_in_it": sorted({b for b, _ in prior.values() if b in vreal_bands}),
                            "vreal_parts_in_it": {k: n for k, (_, n) in prior.items() if k in VREAL}},
            "ratio_db": {**quantiles(r), "min": min(r), "max": max(r), "n": len(r)},
            "mastered_share": sum(bool(x["draw"].get("mastered")) for x in kept) / len(kept),
            "vocals_share": sum(bool(x["draw"].get("vocals_drawn")) for x in kept) / len(kept)}


def s16_stem(d):
    """Step 16: what the separated stem holds. snr_audio_db is the target render against the stem (build rows)."""
    built, kept = d.cc_built(), d.cc_kept()
    snr = [built[i]["snr_audio_db"] for i in kept]
    by_n = {}
    for i, x in kept.items():
        n = len(x.get("others", [])) + len(x.get("amp_tracks", []))
        by_n.setdefault(min(n, 6), []).append(built[i]["snr_audio_db"])
    alone = sum(1 for x in kept.values() if not x.get("others") and not x.get("amp_tracks"))
    t3b = {r["i"]: r for r in _jsonl((d.td / "t3/rows").glob("build-*.jsonl"))
           if not r.get("refused") and r.get("snr_audio_db") is not None}
    f5 = [r["snr_audio_db"] for r in t3b.values()]
    return {"cc": {"n": len(snr), "median_db": statistics.median(snr), "share_below_0": sum(v < 0 for v in snr) / len(snr),
                   "share_below_-5": sum(v < -5 for v in snr) / len(snr)},
            "cc_by_other_guitars": {str(k) + ("+" if k == 6 else ""): {"n": len(v), "median_db": statistics.median(v)}
                                    for k, v in sorted(by_n.items())},
            "cc_target_is_the_only_guitar": alone,
            "f5": {"n": len(f5), "median_db": statistics.median(f5) if f5 else None}}


def s19_tone_probe(d):
    """Step 19: readable heads by input (the tone-information probe's stored output)."""
    p = _json(d.td / "tone-probe/probe.json")
    return {"readable_of_116": p["readable"], "inputs": p["inputs"], "where_lost": p["where_total"]}


def s22_training(d):
    """Steps 22-24: how much training each model got, from its run logs."""
    out = {}
    runs = sorted(list((d.td / "cc/runs").glob("*.json")) + list((d.td / "t3/runs").glob("*.json")))
    if not runs:
        raise FileNotFoundError(2, "no run logs", str(d.td / "{cc,t3}/runs/*.json"))
    for p in runs:
        r = _json(p)
        log = r["log"]
        steps = log[0].get("steps")
        out[p.stem] = {"train": r["train"], "early_stop": r["early_stop"], "steps_per_epoch": steps,
                       "epochs_run": r["epochs_run"], "best_epoch": r["best_epoch"],
                       "steps_to_best": None if steps is None else steps * (r["best_epoch"] + 1),
                       "minutes": r["minutes"], "device": r.get("device"), "augmented": r.get("augmented"),
                       "train_loss_first_last": [log[0]["train"], log[-1]["train"]],
                       "early_stop_first_best": [log[0]["early_stop"], r["best_early_stop_loss"]],
                       "logged_per_epoch": sorted(log[0].keys())}
    return out


def s23_early_stop(d):
    """Step 23: how independent the early-stopping sections are from training."""
    p = d.cc_plan()
    ex = {x["i"]: x for x in p["examples"]}
    out = {"cc": es_overlap([ex[i]["section"] for i in p["train"]], p["fs_sections"])}
    t3 = _json(d.td / "t3/plan.json")
    out["f5"] = es_overlap([x["section"] for x in t3["examples"] if x.get("set") == "F5"], t3["fs5_sections"])
    return out


def s26_pull(d):
    """Step 26: how far the pull takes knobs to the training average (b = 0 is the average itself)."""
    rep = _json(d.td / "t3/report.json")["pull"]
    cc = _json(d.td / "cc-readout/D_CC/fit.json")["model"]
    pick = ("fitted", "median_b", "share_b_0", "share_b_1")
    return {"D_F5": {k: rep["D_F5"]["summary"][k] for k in pick},
            "D_core5": {k: rep["D_core5"]["summary"][k] for k in pick},
            "D_CC": {k: cc["pull_summary"][k] for k in pick},
            "D_CC_folds_median_b": {f: v["median_b"] for f, v in cc["pull_folds"].items()}}


def s27_switch_readout(d):
    """Step 27: drive switches written on (count of 14 pr12-crunch directions) and pedals at S."""
    r = _json(d.td / "cc-readout/D_CC/followups/report.json")
    rows = {k: v["rows"]["all"]["all"] for k, v in r["contrasts"].items()}
    pedals = next(v for k, v in rows.items() if k.startswith("D_CC:at-S:pedals - D_CC"))
    own = next(v for k, v in rows.items() if k.startswith("D_CC - D_CC:constant"))
    return {"pr12_crunch_drives_on": {a: {k: v for k, v in r["drives"][a]["pr12 crunch"].items()}
                                      for a in r["drives"]},
            "D_CC_pedals_at_S_minus_D_CC": {k: pedals[k] for k in ("band_weighted_mean", "lo90", "hi90", "bands_negative")},
            "D_CC_minus_its_constant": {k: own[k] for k in ("band_weighted_mean", "lo90", "hi90", "bands_positive")}}


def s29_fake_song_test(d):
    """Step 29: D_F5 on its own held-out fake songs (FS5), R0's stored rows."""
    r = _json(d.td / "t3/followup-r/r0.json")
    cont = [x for x in r["rows"] if x["kind"] == "continuous"]
    by_kind = {}
    for x in r["rows"]:
        k = by_kind.setdefault(x["kind"], {"heads": 0, "readable": 0})
        k["heads"] += 1
        k["readable"] += bool(x["readable"])
    sw = {x["name"]: round(x["point"], 3) for x in r["rows"] if x["kind"] == "switch"
          and x["name"] in SWITCHES.values()}
    return {"by_kind": by_kind, "by_family": r["by_family"],
            "knobs_median_error_model_vs_constant": [statistics.median(x["e_model"] for x in cont),
                                                     statistics.median(x["e_constant"] for x in cont)],
            "knobs_reliably_worse_than_constant": sum(x["lo"] > 0 for x in cont),
            "switch_auc": sw}


def s32_vreal_inputs(d):
    """Step 32: V-real parts that hand the model the same input (identical stored stems) and get one answer."""
    man = _json(d.root / "learn/direct-stems/step4/stems/xlance_g/stems.json")["stems"]
    by_hash = {}
    for slug in VREAL:
        e = man.get(f"stagef/{slug}")
        if e:
            by_hash.setdefault(e["sha256"], []).append(slug)
    same = [v for v in by_hash.values() if len(v) > 1]
    pred = _json(d.td / "t3/vreal/predictions.json")["predictions"]["D_F5"]
    equal = {}
    for group in same:
        a, b = group[0], group[1]
        ka = sorted(k for k in pred if k.startswith(a + "|"))
        equal[f"{a} vs {b}"] = all(pred[k] == pred[k.replace(a, b, 1)] for k in ka)
    return {"stage_f_stems_checked": sum(len(v) for v in by_hash.values()), "identical_stem_groups": same,
            "D_F5_answers_identical": equal}


def _s_held(d, slug, amp, groups):
    if slug in IN_GROUP_S:
        g = groups[(slug, amp)]["judge"]
        return {"A": g["S|B"]["A"], "B": g["S|A"]["B"]}
    return _json(d.root / f"learn/arm-a-mega53/F/S/{slug}/{amp}.json")["judge"]


def _t3_groups(d):
    out = {}
    for p in (d.td / "t3/vreal/groups").glob("*.json"):
        slug, amp = p.stem.split("|")
        out[(slug, amp)] = _json(p)
    return out


def s34_vreal(d):
    """Steps 34, 35, 37: V-real rows recomputed from the stored judges (held half, ln ratio, band-weighted),
    checked against t3/report.json."""
    groups = _t3_groups(d)
    rep = _json(d.td / "t3/report.json")["contrasts"]

    def rows(arm, base):
        out = []
        for slug, (band, _) in VREAL.items():
            for amp in AMPS:
                g = groups[(slug, amp)]["judge"]
                s = _s_held(d, slug, amp, groups)
                for search, held in HELD.items():
                    a = g[f"{arm}|{search}"][held]
                    b = s[held] if base == "S" else g[f"{base}|{search}"][held]
                    out.append((band, slug, math.log(a / b)))
        return out

    out = {}
    for arm, base, name in (("D_F5", "S", "D_F5 - S"), ("constant", "S", None), ("D_core5", "S", "D_core5 - S"),
                            ("D_F5:at-S:time effects and spring", "S", None), ("D_F5", "constant", "D_F5 - constant")):
        bw = band_weighted(rows(arm, base))
        key = f"{arm} - {base}"
        out[key] = {k: bw[k] for k in ("band_weighted_mean", "lo90", "hi90", "bands", "bands_worse", "bands_better",
                                       "parts", "parts_worse", "leave_one_band_out")}
        out[key]["per_part"] = {k: round(v, 4) for k, v in bw["per_part"].items()}
        if name:
            r = rep[name]["rows"]["all"]["all"]
            out[key]["report"] = [r["band_weighted_mean"], r["lo90"], r["hi90"]]
            out[key]["reproduces_report"] = abs(r["band_weighted_mean"] - bw["band_weighted_mean"]) < 1e-9
    widths = {k: v["rows"]["all"]["all"]["hi90"] - v["rows"]["all"]["all"]["lo90"] for k, v in rep.items()
              if k in ("D_F5 - S", "D_core5 - S", "D_F5 - constant", "D_F5 - D_core5 (the gate)")}
    out["interval_widths"] = widths
    return out


def pick_start(files, parts, amp):
    """A start rule (clean-baseline-plan.md, crunch-baseline-plan.md) on stored distances: the factory preset with
    the lowest median, over the parts that have it on both halves, of the mean of its half-A and half-B `flat`
    measure-DI distances (the first of each stored [distance, tonal, temporal]); ties by name.
    files: [{slug: {key: {preset: [d, ...]}}}]. -> (preset, median, parts used)."""
    rows = []
    for p in parts:
        src = next((f[p] for f in files if p in f), None)
        if src is None:
            continue
        a, b = src.get(f"flat|{amp}|measfix_A", {}), src.get(f"flat|{amp}|measfix_B", {})
        if a and b:
            rows.append((a, b))
    if not rows:
        return None, None, 0
    cands = set.intersection(*[{k for k in a if k.startswith("factory:") and k in b} for a, b in rows])
    score = {c: statistics.median([(a[c][0] + b[c][0]) / 2 for a, b in rows]) for c in cands}
    best = min(sorted(score), key=lambda c: score[c])
    return best, score[best], len(rows)


def s36_s_selection(d):
    """Step 36: were V-real's clips among those the start presets were chosen on, with the same judge?"""
    choice = {c: _json(REPO / f"docs/{c}-baseline-choice.json") for c in ("clean", "crunch")}
    pinned = _json(REPO / "docs/sound-desc-test-parts.json")["parts"]
    files = {n: _json(d.root / f"learn/direc/{n}/distances.json") for n in ("rescore", "songs-check")}
    out = {}
    for slug, (_, cls) in VREAL.items():
        row = {"in": [n for n, f in files.items() if slug in f]}
        if row["in"] and slug not in IN_GROUP_S:
            dist = files[row["in"][0]][slug]
            devs = []
            for amp in AMPS:
                s = _json(d.root / f"learn/arm-a-mega53/F/S/{slug}/{amp}.json")["judge"]
                for h in ("A", "B"):
                    v = dist.get(f"flat|{amp}|measfix_{h}", {}).get(choice[cls]["presets"][amp])
                    if v is not None:                            # [distance, tonal, temporal]: the first is the judge
                        devs.append(abs(v[0] - s[h]))
            row["S_stored_vs_vreal_max_abs_diff"] = max(devs) if devs else None
        out[slug] = row
    rules = {}
    vreal_bands = {b for b, _ in VREAL.values()}
    for cls in ("clean", "crunch"):
        parts = sorted(p for p, v in pinned.items() if v["gain_class"] == cls)
        per_amp = {}
        for amp in AMPS:
            best, med, n = pick_start(list(files.values()), parts, amp)
            per_amp[amp] = {"picked": best, "median": med, "parts_used": n,
                            "matches_choice": best == choice[cls]["presets"][amp]
                            and n == choice[cls]["parts_used"][amp]}
        rules[cls] = {"parts": len(parts), "vreal_clips_in_set": sorted(p for p in parts if p in VREAL),
                      "parts_from_vreal_bands": sum(pinned[p]["band"] in vreal_bands for p in parts),
                      "per_amp": per_amp}
    return {"parts": out, "in_a_distance_file": sum(bool(v["in"]) for v in out.values()),
            "rules_reproduced": rules,
            "parts_list": "docs/sound-desc-test-parts.json (the pinned development clean and crunch parts)"}


def s38_headroom(d):
    """Step 38: the true-DI search on V-real-10's own parts (arm-a-mega53 stage F's ZT: 52 renders, the true DI,
    the amp track as target, shrunk 0.5 toward S), against S on the held half."""
    out = {}
    for which in ("judge_shrunk", "judge_best"):
        rows = []
        for slug, (band, _) in VREAL.items():
            if slug in IN_GROUP_S:
                continue
            for amp in AMPS:
                s = _json(d.root / f"learn/arm-a-mega53/F/S/{slug}/{amp}.json")["judge"]
                for search, held in HELD.items():
                    z = _json(d.root / f"learn/arm-a-mega53/F-perfect-sep/ZT/{slug}/{amp}/{search}.json")
                    rows.append((band, slug, math.log(z[which][held] / s[held])))
        bw = band_weighted(rows)
        out[which] = {k: bw[k] for k in ("band_weighted_mean", "lo90", "hi90", "bands", "bands_better")}
    return out


CHECKS = {f.__name__.split("_")[0]: f for f in (
    s04_pool, s05_class_input, s06_label_prior, s07_silent_refusals, s12_doubles, s13_stand_ins, s14_level_draws,
    s16_stem, s19_tone_probe, s22_training, s23_early_stop, s26_pull, s27_switch_readout, s29_fake_song_test,
    s32_vreal_inputs, s34_vreal, s36_s_selection, s38_headroom)}


def run(root, only=None):
    d = Data(root)
    out = {"design": "docs/ml-pipeline-review.md", "status": "zero renders, zero separations, no training; reads "
           "stored files only", "data_dir": "~/ndsp-presets" if pathlib.Path(root) == DATA else str(root),
           "checks": {}}
    for k, f in CHECKS.items():
        if only and k not in only:
            continue
        try:
            out["checks"][f.__name__] = {"step": int(k[1:]), "what": f.__doc__.split("\n")[0], **f(d)}
        except FileNotFoundError as e:
            out["checks"][f.__name__] = {"step": int(k[1:]), "missing": str(e.filename)}
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", default=str(DATA))
    ap.add_argument("--out")
    ap.add_argument("--only", nargs="*", help="check ids, e.g. s16 s32")
    a = ap.parse_args(argv)
    out = json.dumps(run(pathlib.Path(a.data_dir).expanduser(), a.only), indent=1, default=str) + "\n"
    if a.out:
        pathlib.Path(a.out).write_text(out)
        print(f"wrote {a.out} ({hashlib.sha256(out.encode()).hexdigest()[:12]})")
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
