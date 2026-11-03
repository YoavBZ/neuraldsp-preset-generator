"""The judge against the ear, control by control (docs/pipeline-fix-plan.md; ledger `pipeline-fix`, key
`phase_judge_ear`; descriptive). Does the judge (`analysis.aligned.aligned_distance` as `knob_ceiling.judge` wraps
it) weigh each kind of preset change as the listener's ear does? One clean lead DI through two starting presets,
six control groups moved from S one at a time at two sizes: 24 pairs (S against S + step) and 2 catches (S against
S rendered again). Per pair the judge's distance and a blind A/B rating from the listener. Outputs go to
`~/ndsp-presets/learn/trusted-data/judge-ear/` and `~/ndsp-presets/listening/judge-ear/` only.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -m learn.judge_ear plan                   # zero renders: the 26 pairs from S's stored settings
    $MAIN -u -m learn.judge_ear render --shard k/3  # 28 kept renders, each in its own fresh primed process (56)
    $MAIN -m learn.judge_ear measure                # zero renders: the judge's distance per pair, the catches
    $MAIN -m learn.judge_ear page                   # the blind A/B page and its key (private/, outside the page)
    $MAIN -m learn.judge_ear score --answers FILE   # the ear beside the judge, and the mis-weighting reading
    $MAIN -m learn.judge_ear page --recheck         # the headphone recheck page (`phase_judge_ear_recheck`)
    $MAIN -m learn.judge_ear score --recheck --answers FILE
    $MAIN -m learn.judge_ear anchors                # `phase_judge_ear_v4` stage A: the tonal-anchor page (0 renders)
    $MAIN -m learn.judge_ear anchors-score --answers FILE

**The pairs (as declared).** S: `arm_a_mega53.L.menu_S()`, clean on PR12 and crunch on SW50R. Steps:
- drive: `parameters/inputGain` +4 and +10 dB (clipped to `full_space`'s range, -20..12 dB);
- tone: the amp's treble (`pr12Amp/pr12Treble`, `sw50rAmp/sw50rTreble`) +0.15 and +0.35 in unit range
  (`Dim.to_unit` / `Dim.from_unit`); where the step up would pass the top of the range it goes down by the same
  amount instead (`phase_judge_ear_amendment`: SW50R crunch's S has treble at 1.0, so as first declared both of its
  tone pairs were S against S);
- cab: small, `cabParameters/leftCabDistance` +0.25 in unit range, clipped; large, `cabParameters/leftMicType` the
  next mic in `knob_ceiling.MICS` order (wrapping from 9 to 0);
- reverb: `reverb/reverbActive` on, `reverb/reverbMix` 0.15 and 0.40, the reverb's other controls at the plugin's
  defaults;
- delay: `delay/delayActive` on, `delay/delayMix` 0.15 and 0.40, the delay's other controls at the plugin's
  defaults;
- spring: the amp's spring level (`pr12Amp/pr12Reverb`, `sw50rAmp/sw50rReverb`) set to 0.2 and 0.5 (both S have it at
  0: the spring off). `full_space.spring_on` counts a level above 0 as on; PR12's dwell stays at S's value (0.79), so
  the spring sounds; the plan checks every stepped key sounds (`full_space.sounding`).

**Choices beyond the declaration** (also in the plan JSON's `choices` and the page key):
- "The plugin's defaults" are the plugin's own `Default.xml` factory preset (its reverb and delay values; the file's
  sha256 is recorded). One exception: the delay is written free-running (`delaySync` 0, the project's convention,
  `full_space.FREE`) with `Default.xml`'s `delayTime` (500 ms). The default `delaySync` is 1 (DAW), which follows a
  host tempo the offline renderer does not have; `Default.xml`'s DAW note (1/4 at 120 BPM) is the same 500 ms.
- The DI: 109.75-120 s of the file (the 0.25 s before 110 s is the trimmed pre-roll, as `cmd_real_render` reads a
  section), mono (channel mean), resampled 44.1 -> 48 kHz with soxr VHQ (the v2 page's stand-in), then one gain that
  puts 110-120 s at -22.9 LUFS (`direc_check.to_lufs`, BS.1770 integrated). Not `song_bank.measure`: that also EQs the
  DI to the average guitar, which the declaration does not ask for and the v2 stand-in did not do.
- Renders: `audibility_measure.fresh_render(cc_build.new_renderer, di32, select, st, st)`, folded to mono (channel
  mean), the first 0.25 s trimmed: 10 s, 110-120 s of the DI.
- The judge's lag is 0: both sides are renders of the same DI through the same plugin path, so the plugin latency
  (52 samples) is common to both. `measure` checks it: `analysis.aligned.estimate_lag` per preset (all its renders
  pooled against S) and per pair, recorded beside the distances.
- A pair's judge distance is the mean of halves A and B (`knob_ceiling.judge`).
- Page: the pairs' order and each pair's A/B order drawn from `PAGE_SEED`; each pair level-matched as the earlier
  pages did (`audibility_measure.pair_clips`: each clip at -23 LUFS on its own, a common true-peak cut, 10-ms fades,
  AAC 256 kbps), embedded in the page.
- Mis-weighting reading: pairs of both presets pooled; only pairs of different groups compared; "below" is strictly
  below; catches stand outside the rule (they are reported). Unsure answers count, flagged.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import pathlib
import random
import re
import time

LEDGER_KEY = "phase_judge_ear"
AMENDMENT_KEY = "phase_judge_ear_amendment"
DATA = pathlib.Path("~/ndsp-presets").expanduser()
OUT = "learn/trusted-data/judge-ear"
PAGE = "listening/judge-ear"
RECHECK_PAGE = "listening/judge-ear-recheck"
ANCHOR_PAGE = "listening/judge-ear-anchors"
PAGE_NAME = "judge-ear"
DI_REL = "references/datasets/cambridge/AleLak_NossoMundoDeixouDeExistir_Full/24_ElecGtr05DI.wav"
DI_START_S = 110.0
DI_LUFS = -22.9
SR = 48000
SEC_S = 10.0                           # pretrain_set.SEC_S
TRIM_S = 0.25                          # pretrain_set.TRIM_S: the rendered pre-roll, trimmed
DEFAULT_PRESET = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/Default.xml")
PRESETS = (("clean", "pr12"), ("crunch", "sw50r"))
GROUPS = ("drive", "tone", "cab", "reverb", "delay", "spring")
SIZES = ("small", "large")
STEPS = {"drive": (4.0, 10.0), "tone": (0.15, 0.35), "cab": (0.25, "next mic"), "reverb": (0.15, 0.40),
         "delay": (0.15, 0.40), "spring": (0.2, 0.5)}
EFFECT_SWITCH = {"reverb": ("reverb", "reverbActive"), "delay": ("delay", "delayActive")}
FREE_DELAY = {("delay", "delaySync"): "0"}          # full_space.FREE's delay half: syncMode 0 is Free
CATCH = "catch"
PAGE_SEED = 20261120
# The headphone recheck (`phase_judge_ear_recheck`): the first sitting was heard on phone speakers. The pairs where the
# ear and every measure tried disagreed most, every pair in one of F44's inversions, one small drive step as a low
# comparator, one catch, and one pair twice.
RECHECK_KEY = "phase_judge_ear_recheck"
RECHECK_SEED = 20261103
RECHECK_PAIRS = ("clean-tone-large", "clean-tone-small", "crunch-tone-large", "clean-drive-large",
                 "crunch-drive-large", "clean-reverb-large", "crunch-reverb-large", "clean-delay-large",
                 "crunch-delay-large", "clean-spring-large", "clean-drive-small", "clean-catch", "clean-tone-large")
RECHECK_NOTE = "Please listen on headphones (not phone or laptop speakers), at a comfortable level."
# `phase_judge_ear_v4` stage A: S's stored render against itself through an RBJ shelf (slope 1) of known gain,
# applied before the page's clip rule sets each clip to -23 LUFS. (preset, shelf, dB); with a known-heard pair and a
# catch from the first page.
V4_KEY = "phase_judge_ear_v4"
ANCHOR_SEED = 20261104
SHELF_HZ = {"low": 250.0, "high": 3000.0}
ANCHORS = (("clean", "high", 3), ("clean", "high", 6), ("clean", "high", -6), ("clean", "low", -6),
           ("clean", "high", 12), ("crunch", "high", 6), ("crunch", "low", -6), ("crunch", "low", 6),
           ("crunch", "high", -3))
ANCHOR_PAIRS = ("clean-reverb-large", "clean-catch")
RATINGS = ("same", "barely", "clearly", "very")
RATING_TEXT = {"same": "Same", "barely": "Barely different", "clearly": "Clearly different", "very": "Very different"}
CONFS = ("sure", "unsure")
LOUD = ("clearly", "very")
QUIET = ("same", "barely")
XFADE_S = 0.012
# Words that would unblind the page (group, size, preset and control names); checked with base64 stripped.
# ("catch" and "null" are left out: the player's script uses both as JavaScript words.)
FORBIDDEN = GROUPS + SIZES + ("clean", "crunch", "pr12", "sw50r", "treble", "mic", "dwell", "inputgain", "distance",
                              "step", "preset")
CHOICES = [
    "plugin defaults = Default.xml (the plugin's own factory default preset), its reverb and delay values",
    "delay written free-running (delaySync 0, full_space.FREE) at Default.xml's delayTime 500 ms; Default.xml's "
    "delaySync is 1 (DAW, 1/4 at 120 BPM = 500 ms), which needs a host tempo the offline renderer lacks",
    "a tone step that would pass the top of the treble's range goes down instead (amendment; SW50R crunch: treble at 1.0)",
    "cab large = the left mic type moved to the next mic in knob_ceiling.MICS order (wrapping 9 -> 0)",
    "DI: 109.75-120 s, mono, soxr VHQ 44.1 -> 48 kHz, one gain putting 110-120 s at -22.9 LUFS "
    "(direc_check.to_lufs); no average-guitar EQ (song_bank.measure is not used)",
    "renders folded to mono (channel mean), first 0.25 s trimmed",
    "judge lag 0 (both sides renders of the same DI through the same path); estimate_lag recorded as a check",
    "pair distance = mean of the judge's halves A and B",
    "mis-weighting: both presets pooled, different groups only, strictly below; catches outside the rule",
]


# --- pure: the steps --------------------------------------------------------------------------------------------------

def _dim(path):
    from learn import full_space as F

    return F.dims()[path]


def treble(amp):
    return (f"{amp}Amp", f"{amp}Treble")


def spring_level(amp):
    from learn import full_space as F

    return F.SPRING[amp]


def group_keys(amp, group, defaults=None):
    """The keys a group's step may change (a pair differs from S in these only)."""
    if group == "drive":
        return {("parameters", "inputGain")}
    if group == "tone":
        return {treble(amp)}
    if group == "cab":
        return {("cabParameters", "leftCabDistance"), ("cabParameters", "leftMicType")}
    if group in EFFECT_SWITCH:
        return {EFFECT_SWITCH[group], (group, f"{group}Mix")} | {k for k in (defaults or {}) if k[0] == group}
    if group == "spring":
        return {spring_level(amp)}
    raise ValueError(group)


def unit_step(d, stored, du):
    """`stored` moved by `du` in unit range, clipped to the dim's range; the plugin's stored string."""
    from learn import knob_ceiling as K

    return K.fmt(d.from_unit(d.to_unit(stored) + du))


def step_settings(amp, S, group, size, defaults):
    """S with `group` moved by its `size` step. S: {(module, key): stored}; defaults: the plugin's default values of
    the reverb's and delay's controls {(module, key): stored}. -> (settings, {key: [from, to]} of the keys changed)."""
    from learn import knob_ceiling as K

    j = SIZES.index(size)
    v = STEPS[group][j]
    x = dict(S)
    if group == "drive":
        p = ("parameters", "inputGain")
        d = _dim(p)
        x[p] = K.fmt(min(max(float(S[p]) + v, d.lo), d.hi))
    elif group == "tone":                             # amendment (2026-11-02): down where up would clip at the top
        p = treble(amp)
        d = _dim(p)
        x[p] = unit_step(d, S[p], v if d.to_unit(S[p]) + v <= 1.0 else -v)
    elif group == "cab" and size == "small":
        p = ("cabParameters", "leftCabDistance")
        x[p] = unit_step(_dim(p), S[p], v)
    elif group == "cab":
        p = ("cabParameters", "leftMicType")
        x[p] = K.MICS[(K.MICS.index(str(S[p])) + 1) % len(K.MICS)]
    elif group in EFFECT_SWITCH:
        x.update({k: val for k, val in defaults.items() if k[0] == group})
        if group == "delay":
            x.update(FREE_DELAY)
        x[EFFECT_SWITCH[group]] = "true"
        x[(group, f"{group}Mix")] = K.fmt(v)
    elif group == "spring":
        x[spring_level(amp)] = K.fmt(v)
    else:
        raise ValueError(group)
    changes = {f"{k[0]}/{k[1]}": [S.get(k), x[k]] for k in sorted(x) if S.get(k) != x[k]}
    return x, changes


def sdict(x):
    """{(module, key): v} -> {"module/key": v} (JSON; local_objective.sdict)."""
    return {f"{a}/{b}": v for (a, b), v in sorted(x.items())}


def tdict(x):
    """{"module/key": v} -> {(module, key): v} (local_objective.tdict)."""
    return {tuple(k.rsplit("/", 1)): v for k, v in x.items()}


def pair_id(cls, group, size=None):
    return f"{cls}-{CATCH}" if group == CATCH else f"{cls}-{group}-{size}"


def preset_pairs(cls, amp, S, defaults):
    """The 12 steps and the catch of one preset: [{pair, cls, amp, group, size, settings, changes, null}]."""
    out = []
    for g in GROUPS:
        for s in SIZES:
            x, ch = step_settings(amp, S, g, s, defaults)
            out.append({"pair": pair_id(cls, g, s), "cls": cls, "amp": amp, "group": g, "size": s,
                        "step": STEPS[g][SIZES.index(s)], "changes": ch, "null": not ch,
                        "settings": sdict(x)})
    out.append({"pair": pair_id(cls, CATCH), "cls": cls, "amp": amp, "group": CATCH, "size": None, "step": None,
                "changes": {}, "null": True, "settings": sdict(S)})
    return out


def render_jobs(plan):
    """The kept renders: per preset S, S again (the catch's B), then each step. -> [(job, cls, settings)]."""
    jobs = []
    for pr in plan["presets"]:
        jobs.append((f"{pr['cls']}-S", pr["cls"], pr["S"]))
        jobs.append((f"{pr['cls']}-S2", pr["cls"], pr["S"]))
    for p in plan["pairs"]:
        if p["group"] != CATCH:
            jobs.append((p["pair"], p["cls"], p["settings"]))
    return jobs


def job_of(p):
    """The render compared against S's render for a pair (the catch: S rendered again)."""
    return f"{p['cls']}-S2" if p["group"] == CATCH else p["pair"]


def parse_shard(s):
    k, n = (int(v) for v in s.split("/"))
    if not 0 <= k < n:
        raise argparse.ArgumentTypeError(s)
    return k, n


# --- pure: the anchors -----------------------------------------------------------------------------------------------

def anchor_id(cls, shelf, db):
    return f"{cls}-anchor-{shelf}{db:+d}"


def rbj_shelf(kind, f0, gain_db, sr=48000):
    """RBJ Audio EQ Cookbook shelf, slope S = 1 -> (b, a) normalised by a0."""
    import math
    A = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / sr
    c, alpha = math.cos(w0), math.sin(w0) / 2 * math.sqrt(2)
    r = 2 * math.sqrt(A) * alpha
    if kind == "low":
        b = [A * ((A + 1) - (A - 1) * c + r), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - r)]
        a = [(A + 1) + (A - 1) * c + r, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - r]
    elif kind == "high":
        b = [A * ((A + 1) + (A - 1) * c + r), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - r)]
        a = [(A + 1) - (A - 1) * c + r, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - r]
    else:
        raise ValueError(kind)
    return [x / a[0] for x in b], [x / a[0] for x in a]


def shelve(y, kind, gain_db, sr=48000):
    from scipy.signal import lfilter

    b, a = rbj_shelf(kind, SHELF_HZ[kind], gain_db, sr)
    return lfilter(b, a, y)


# --- pure: the page, the answers, the score --------------------------------------------------------------------------

def page_order(pairs, seed=PAGE_SEED):
    """The page's items: the pairs shuffled, each with its A side drawn ("S" or "step"). -> [{page_id, pair, a}]."""
    rng = random.Random(seed)
    order = sorted(pairs)
    rng.shuffle(order)
    return [{"page_id": f"p{n + 1:02d}", "pair": p, "a": rng.choice(("S", "step"))} for n, p in enumerate(order)]


def strip_audio(text):
    """The page's text with the clips' script and any long base64 run removed (what a reader could see or grep)."""
    text = re.sub(r'<script id="clips"[^>]*>.*?</script>', "", text, flags=re.S)
    return re.sub(r"[A-Za-z0-9+/=]{200,}", "", text)


def leaks(text, words=FORBIDDEN):
    """The forbidden words (whole words, any case) left in the page once the audio is stripped."""
    pat = re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)
    return sorted({m.group(1).lower() for m in pat.finditer(strip_audio(text))})


def parse_answers(text, build=None):
    """An export (`page`'s Export text or file) -> {page_id: {"rating", "conf", "note"}}. The last line that parses
    as JSON with `answers` is read; a different build refuses; ratings and confidences outside the scale are
    dropped (left unanswered)."""
    blob = None
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if isinstance(d, dict) and "answers" in d:
                blob = d
                break
    if blob is None:
        raise ValueError("no answers line (a JSON object with 'answers') in the export")
    if build is not None and blob.get("build") != build:
        raise ValueError(f"the export is from build {blob.get('build')}, the page key is build {build}")
    out = {}
    for pid, a in (blob.get("answers") or {}).items():
        if not isinstance(a, dict):
            continue
        r = a.get("rating") if a.get("rating") in RATINGS else None
        c = a.get("conf") if a.get("conf") in CONFS else None
        out[pid] = {"rating": r, "conf": c, "note": str(a.get("note") or "")}
    return out


def score_rows(items, judged, answers, halves=None):
    """items: the key's [{page_id, pair, cls, group, size, null}]; judged: {pair: mean distance}; answers: from
    `parse_answers`. -> rows in group, size, preset order, unanswered pairs with rating None."""
    rows = []
    for it in items:
        a = answers.get(it["page_id"], {})
        rows.append({"pair": it["pair"], "page_id": it["page_id"], "cls": it["cls"], "group": it["group"],
                     "size": it["size"], "null": it.get("null", False), "judge": judged.get(it["pair"]),
                     "halves": (halves or {}).get(it["pair"]),
                     "rating": a.get("rating"), "conf": a.get("conf"), "note": a.get("note", "")})
    gi = {g: i for i, g in enumerate(GROUPS + (CATCH,))}
    return sorted(rows, key=lambda r: (gi[r["group"]], SIZES.index(r["size"]) if r["size"] else 9, r["cls"]))


def misweights(rows):
    """The declared reading: every (heard, quiet) pair of rows from different groups where the ear calls `heard`
    clearly or very different and `quiet` same or barely, yet the judge puts `heard` strictly below `quiet`. Catches
    and unrated or unjudged rows stand outside. -> (inversions, {group: {"under": [...], "over": [...]}}): `under`,
    the group's heard pairs below another's quiet ones (the judge weighs it less than the ear); `over`, its quiet
    pairs above another's heard ones (more)."""
    ok = [r for r in rows if r["group"] in GROUPS and r["rating"] and r["judge"] is not None
          and math.isfinite(r["judge"])]
    loud = [r for r in ok if r["rating"] in LOUD]
    quiet = [r for r in ok if r["rating"] in QUIET]
    inv, by = [], {}
    for p in loud:
        for q in quiet:
            if p["group"] != q["group"] and p["judge"] < q["judge"]:
                hp, hq = p.get("halves") or {}, q.get("halves") or {}
                inv.append({"heard": p["pair"], "heard_rating": p["rating"], "heard_judge": p["judge"],
                            "quiet": q["pair"], "quiet_rating": q["rating"], "quiet_judge": q["judge"],
                            "unsure": "unsure" in (p["conf"], q["conf"]), "same_preset": p.get("cls") == q.get("cls"),
                            "both_halves": bool(hp and hq) and all(hp[h] < hq[h] for h in hp if h in hq),
                            "ratio": q["judge"] / p["judge"] if p["judge"] > 0 else math.inf})
                by.setdefault(p["group"], {"under": set(), "over": set()})["under"].add(p["pair"])
                by.setdefault(q["group"], {"under": set(), "over": set()})["over"].add(q["pair"])
    return inv, {g: {k: sorted(v) for k, v in d.items()} for g, d in by.items()}


# --- I/O ------------------------------------------------------------------------------------------------------------

def out_dir(root=DATA):
    return pathlib.Path(root) / OUT


def page_dir(root=DATA, recheck=False, anchors=False):
    return pathlib.Path(root) / (ANCHOR_PAGE if anchors else RECHECK_PAGE if recheck else PAGE)


def key_path(root=DATA, recheck=False, anchors=False):
    return page_dir(root, recheck, anchors) / "private" / "page-key.json"


def save(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")            # per process: shards may race
    tmp.write_text(json.dumps(obj, indent=1, default=str) + "\n")
    tmp.replace(path)


def save_npy(path, a):
    import numpy as np

    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp.npy")
    np.save(tmp, a)
    tmp.replace(path)


def load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else None


def require():
    """Real runs refuse unless the ledger's `pipeline-fix` entry declares `phase_judge_ear` and its amendment (the tone
    step's rule)."""
    from learn import pipeline_fix as P

    P.require(AMENDMENT_KEY)
    return P.require(LEDGER_KEY)


def require_v4():
    """Stage A refuses unless the ledger also declares `phase_judge_ear_v4`."""
    from learn import pipeline_fix as P

    require()
    return P.require(V4_KEY)


def require_recheck():
    """The recheck page and its score refuse unless the ledger also declares `phase_judge_ear_recheck`."""
    from learn import pipeline_fix as P

    require()
    return P.require(RECHECK_KEY)


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def plugin_defaults(path=DEFAULT_PRESET):
    """The reverb's and delay's controls in the plugin's Default.xml, less their on switches and mixes (the steps
    set those). -> {(module, key): stored}."""
    import sys

    repo = pathlib.Path(__file__).resolve().parents[1]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from format.parser import parse
    from format.structured import build

    p = build(parse(pathlib.Path(path).read_bytes()))
    skip = {EFFECT_SWITCH["reverb"], EFFECT_SWITCH["delay"], ("reverb", "reverbMix"), ("delay", "delayMix")}
    return {k: str(v.value) for k, v in p.by_path.items() if k[0] in ("reverb", "delay") and k not in skip}


def di_audio(root=DATA):
    """The DI as rendered: 109.75-120 s, mono, soxr VHQ to 48 kHz, one gain putting 110-120 s at -22.9 LUFS.
    -> float32 array of (TRIM_S + SEC_S) * SR samples."""
    import numpy as np
    import pyloudnorm
    import soundfile as sf
    import soxr

    path = pathlib.Path(root) / DI_REL
    sr = sf.info(str(path)).samplerate
    x, _ = sf.read(str(path), start=int(round((DI_START_S - TRIM_S) * sr)), frames=int(round((SEC_S + TRIM_S) * sr)),
                   dtype="float64", always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        x = soxr.resample(x, sr, SR, quality="VHQ")
    n = int(round((SEC_S + TRIM_S) * SR))
    x = np.pad(x, (0, max(0, n - len(x))))[:n]
    t = int(TRIM_S * SR)
    lufs = pyloudnorm.Meter(SR).integrated_loudness(x[t:])     # direc_check.to_lufs's measure, on 110-120 s
    return (x * 10 ** ((DI_LUFS - lufs) / 20)).astype(np.float32)


def trim():
    return int(TRIM_S * SR), int((TRIM_S + SEC_S) * SR)


def render_path(root, job):
    return out_dir(root) / "renders" / f"{job}.npy"


# --- commands -------------------------------------------------------------------------------------------------------

def cmd_plan(args):
    """The 26 pairs from S's stored settings (zero renders) -> plan.json."""
    e = require()
    from learn import arm_a_mega53 as A
    from learn import full_space as F
    p = out_dir() / "plan.json"
    if p.exists() and not args.force:
        raise SystemExit(f"{p} exists (--force to rebuild it)")
    ms = A.L.menu_S()
    defaults = plugin_defaults()
    presets, pairs = [], []
    for cls, amp in PRESETS:
        sel, S = ms[amp][cls]
        presets.append({"cls": cls, "amp": amp, "select": sel, "S": sdict(S)})
        for q in preset_pairs(cls, amp, S, defaults):
            q["select"] = sel
            if q["group"] in GROUPS and q["changes"]:
                x = tdict(q["settings"])
                snd = F.sounding(x, amp)
                mute = [k for k in q["changes"] if tuple(k.rsplit("/", 1)) in snd and not snd[tuple(k.rsplit("/", 1))]]
                if mute:
                    raise SystemExit(f"{q['pair']}: stepped controls that do not sound: {mute}")
            pairs.append(q)
    plan = {"page": PAGE_NAME, "ledger": {"test_id": "pipeline-fix", "key": LEDGER_KEY, "text": e[LEDGER_KEY],
                                          "amendment": {"key": AMENDMENT_KEY, "text": e[AMENDMENT_KEY]}},
            "time": time.strftime("%Y-%m-%d %H:%M:%S"), "presets": presets, "pairs": pairs,
            "defaults": {"file": str(DEFAULT_PRESET), "sha256": file_sha256(DEFAULT_PRESET),
                         "values": sdict(defaults)},
            "di": {"path": str(DATA / DI_REL), "start_s": DI_START_S, "sec_s": SEC_S, "trim_s": TRIM_S,
                   "lufs": DI_LUFS},
            "choices": CHOICES}
    plan["renders_declared"] = 2 * len(render_jobs(plan))
    save(p, plan)
    for q in pairs:
        ch = "; ".join(f"{k} {a} -> {b}" for k, (a, b) in q["changes"].items()) or "(same as S)"
        print(f"{q['pair']:22s} {'NULL ' if q['null'] and q['group'] != CATCH else ''}{ch}")
    print(f"PLAN DONE: {len(pairs)} pairs, {len(render_jobs(plan))} kept renders "
          f"({plan['renders_declared']} with priming) -> {p}")


def cmd_render(args):
    """One shard of the kept renders, each in its own fresh primed process (`AM.fresh_render`), mono, trimmed."""
    require()
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    plan = load(out_dir() / "plan.json")
    if not plan:
        raise SystemExit("run `plan` first")
    ms = A.L.menu_S()
    for pr in plan["presets"]:                       # the plan's S must be the stored S
        if K.key(tdict(pr["S"])) != K.key(ms[pr["amp"]][pr["cls"]][1]):
            raise SystemExit(f"{pr['amp']} {pr['cls']}: the plan's S differs from the stored copy")
    di32 = di_audio()
    di_rec = {"path": str(DATA / DI_REL), "file_sha256": file_sha256(DATA / DI_REL),
              "audio_sha256": AM.audio_sha(di32), "samples": len(di32), "choices": CHOICES[4]}
    dp = out_dir() / "di.json"
    old = load(dp)
    if old and old["audio_sha256"] != di_rec["audio_sha256"]:
        raise SystemExit(f"{dp}: another DI was rendered before")
    if not old:
        save_npy(out_dir() / "di.npy", di32)
        save(dp, di_rec)
    k, n = args.shard
    mine = [j for i, j in enumerate(render_jobs(plan)) if i % n == k]
    lo, hi = trim()
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    for amp, by_cls in ms.items():                   # the live S must equal the stored copy (cc_readout's check)
        for cls, (_, S) in by_cls.items():
            if K.key(dict(menu[amp][K.START[cls][amp]][1])) != K.key(S):
                raise SystemExit(f"{amp} {cls}: the live S differs from the stored copy")
    sel_of = {pr["cls"]: pr["select"] for pr in plan["presets"]}
    renders = 0
    for job, cls, st in mine:
        jp = out_dir() / "renders" / f"{job}.json"
        st_t = tdict(st)
        rec = load(jp)
        if rec:
            if rec["settings_key"] != K.key(st_t):
                raise SystemExit(f"{jp}: rendered from other settings")
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        t0 = time.time()
        y = AM.fresh_render(CB.new_renderer, di32, sel_of[cls], st_t, st_t)
        renders += 2
        y = (y.mean(axis=1) if y.ndim == 2 else y)[lo:hi]
        save_npy(render_path(DATA, job), np.asarray(y, np.float64))
        save(jp, {"job": job, "cls": cls, "select": sel_of[cls], "settings_key": K.key(st_t),
                  "render_sha256": AM.audio_sha(y), "samples": len(y), "peak": float(np.max(np.abs(y))),
                  "secs": round(time.time() - t0, 1), "renders": 2, "di_audio_sha256": di_rec["audio_sha256"],
                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{job}: {time.time() - t0:.0f} s; renders so far {renders}", flush=True)
    print(f"JUDGE-EAR RENDER DONE {k}/{n}: {renders} renders")


def cmd_measure(args):
    """The judge's distance per pair against S's render (zero renders) -> measure.json. The catches must score 0 on
    both halves or be bit-identical, else it refuses."""
    require()
    import numpy as np

    from analysis.aligned import estimate_lag
    from learn import knob_ceiling as K

    plan = load(out_dir() / "plan.json")
    jobs = render_jobs(plan)
    rows = {j: load(out_dir() / "renders" / f"{j}.json") for j, _, _ in jobs}
    missing = [j for j, r in rows.items() if not r]
    if missing:
        raise SystemExit(f"renders missing: {missing}")
    di_rec = load(out_dir() / "di.json")
    di = np.asarray(np.load(out_dir() / "di.npy"), np.float64)
    lo, hi = trim()
    di = di[lo:hi]
    y = {j: np.load(render_path(DATA, j)) for j in rows}
    res, lags, bad = {}, {}, []
    for pr in plan["presets"]:
        cls = pr["cls"]
        ref = y[f"{cls}-S"]
        mine = [p for p in plan["pairs"] if p["cls"] == cls]
        try:
            lags[cls] = int(estimate_lag(ref, [y[job_of(p)] for p in mine]))
        except ValueError as err:
            lags[cls] = f"no lag: {err}"
        for p in mine:
            j = job_of(p)
            h = K.judge(ref, y[j], di, 0)
            try:
                own = int(estimate_lag(ref, y[j]))
            except ValueError as err:
                own = f"no lag: {err}"
            identical = rows[j]["render_sha256"] == rows[f"{cls}-S"]["render_sha256"]
            res[p["pair"]] = {"pair": p["pair"], "cls": cls, "group": p["group"], "size": p["size"],
                              "null": p["null"], "judge": h, "mean": (h["A"] + h["B"]) / 2, "lag_check": own,
                              "identical_to_S": identical, "render": j}
            if p["group"] == CATCH and not (identical or all(v == 0 for v in h.values())):
                bad.append(p["pair"])
    out = {"page": PAGE_NAME, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "lag_used": 0,
           "lag_estimates_pooled": lags, "di_audio_sha256": di_rec["audio_sha256"],
           "renders": sum(r["renders"] for r in rows.values()), "pairs": res,
           "render_sha256": {j: r["render_sha256"] for j, r in rows.items()}}
    if bad:
        save(out_dir() / "measure-refused.json", out)
        raise SystemExit(f"catches not 0 and not bit-identical: {bad} (-> measure-refused.json)")
    save(out_dir() / "measure.json", out)
    for p in plan["pairs"]:
        r = res[p["pair"]]
        print(f"{p['pair']:22s} A {r['judge']['A']:.4f}  B {r['judge']['B']:.4f}  mean {r['mean']:.4f}"
              f"  lag {r['lag_check']}{'  identical to S' if r['identical_to_S'] else ''}")
    print(f"MEASURE DONE: {len(res)} pairs; pooled lags {lags}; {out['renders']} renders")


def cmd_page(args):
    """The blind A/B page and its key (private/page-key.json, outside the page's audio and HTML); with --recheck, the
    headphone recheck's page from the same renders."""
    recheck = getattr(args, "recheck", False)
    require_recheck() if recheck else require()
    import numpy as np

    from learn import audibility_measure as AM

    plan = load(out_dir() / "plan.json")
    meas = load(out_dir() / "measure.json")
    if not meas:
        raise SystemExit("run `measure` first")
    kp = key_path(recheck=recheck)
    if kp.exists() and not args.force:
        raise SystemExit(f"{kp} exists: a rebuild hides the listener's stored answers (--force)")
    by = {p["pair"]: p for p in plan["pairs"]}
    items = page_order(list(RECHECK_PAIRS), RECHECK_SEED) if recheck else page_order(list(by))
    clips, key_items = {}, []
    for it in items:
        p = by[it["pair"]]
        s = np.load(render_path(DATA, f"{p['cls']}-S"))
        o = np.load(render_path(DATA, job_of(p)))
        for job, y in ((f"{p['cls']}-S", s), (job_of(p), o)):   # the audio must be what `measure` judged
            if AM.audio_sha(y) != meas["render_sha256"][job]:
                raise SystemExit(f"{job}: its render is not the one `measure` judged; run `measure` first")
        a, b = (s, o) if it["a"] == "S" else (o, s)
        clips[it["page_id"] + "-1"], clips[it["page_id"] + "-2"] = AM.pair_clips(a, b, out_dir() / "page-cache")
        key_items.append({**it, "cls": p["cls"], "amp": p["amp"], "group": p["group"], "size": p["size"],
                          "null": p["null"], "changes": p["changes"], "b": "step" if it["a"] == "S" else "S",
                          "render_a": f"{p['cls']}-S" if it["a"] == "S" else job_of(p),
                          "render_b": job_of(p) if it["a"] == "S" else f"{p['cls']}-S"})
    seed = RECHECK_SEED if recheck else PAGE_SEED
    build = hashlib.sha256((json.dumps(key_items, sort_keys=True) + str(seed)).encode()).hexdigest()[:12]
    page = page_html([it["page_id"] for it in items], clips, build, RECHECK_NOTE if recheck else None)
    bad = leaks(page)
    if bad:
        raise SystemExit(f"the page names {bad}: not blind")
    save(kp, {"page": PAGE_NAME + ("-recheck" if recheck else ""), "build": build, "seed": seed, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
              "shuffle_rule": f"random.Random({'RECHECK_SEED' if recheck else 'PAGE_SEED'}).shuffle of the sorted pair ids, then one choice of A's side "
                              "per item in page order",
              "clip_rule": "mono; 0.25 s trimmed; each clip -23 LUFS on its own (build_data_review.level_clip), the "
                           "pair's larger true-peak cut on both; 10-ms fades; AAC 256 kbps (audibility_measure."
                           "pair_clips)",
              "render_sha256": meas["render_sha256"], "choices": CHOICES, "items": key_items})
    pd = page_dir(recheck=recheck)
    pd.mkdir(parents=True, exist_ok=True)
    out = pd / "index.html"
    out.write_text(page)
    print(f"PAGE DONE: {len(items)} pairs, {out.stat().st_size / 1e6:.1f} MB -> {out}; build {build}; "
          f"key {kp}")


def cmd_score(args):
    """The ear's rating beside the judge's distance per group and size, and the declared mis-weighting reading."""
    recheck = getattr(args, "recheck", False)
    if recheck:
        require_recheck()
    key = load(key_path(recheck=recheck))
    meas = load(out_dir() / "measure.json")
    if not key or not meas:
        raise SystemExit("run `page` first")
    ans = parse_answers(pathlib.Path(args.answers).read_text(), key["build"])
    judged = {k: v["mean"] for k, v in meas["pairs"].items()}
    rows = score_rows(key["items"], judged, ans, {k: v["judge"] for k, v in meas["pairs"].items()})
    for r in rows:                                       # a catch heard as different: a listener-reliability caveat
        if r["group"] == CATCH and r["rating"] in LOUD:
            print(f"CAVEAT: the catch {r['pair']} (identical audio) was rated {r['rating']}")
    inv, by = misweights(rows)
    print(f"{'group':8s} {'size':6s} {'preset':7s} {'judge':>8s}  ear")
    for r in rows:
        j = "-" if r["judge"] is None else f"{r['judge']:.4f}"
        ear = f"{r['rating'] or '(unanswered)'}{', ' + r['conf'] if r['conf'] else ''}"
        print(f"{r['group']:8s} {r['size'] or '':6s} {r['cls']:7s} {j:>8s}  {ear}"
              f"{'  [step equals S]' if r['null'] and r['group'] != CATCH else ''}"
              f"{'  | ' + r['note'] if r['note'] else ''}")
    print()
    if inv:
        print(f"MIS-WEIGHTING: {len(inv)} inversions (a pair heard clearly/very different below another group's "
              f"pair heard same/barely):")
        for x in inv:
            print(f"  {x['heard']} ({x['heard_rating']}, {x['heard_judge']:.4f}) < {x['quiet']} "
                  f"({x['quiet_rating']}, {x['quiet_judge']:.4f}); ratio {x['ratio']:.2f}"
                  f"{'; on both halves' if x['both_halves'] else '; not on both halves'}"
                  f"{'; same preset' if x['same_preset'] else '; across presets'}"
                  f"{'  [an unsure answer]' if x['unsure'] else ''}")
        for g, d in sorted(by.items()):
            print(f"  {g}: judged below the ear {d['under'] or '-'}; judged above the ear {d['over'] or '-'}")
    else:
        print("NO MIS-WEIGHTING: no pair heard clearly/very different sits below another group's pair heard "
              "same/barely; the judge's weighting stands on these two presets.")
    out = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "answers_file": str(args.answers), "build": key["build"],
           "rows": rows, "inversions": inv, "by_group": by}
    if recheck:                                          # each pair beside the first sitting's (phone speakers) answer
        first = {r["pair"]: r["rating"] for r in (load(out_dir() / "score.json") or {}).get("rows", [])}
        out["first_sitting"] = first
        print("\nRECHECK (headphones) beside the first sitting (phone speakers):")
        for r in rows:
            print(f"  {r['page_id']} {r['pair']:22s} now {r['rating'] or '-':8s} first {first.get(r['pair']) or '-'}")
    save(out_dir() / ("score-recheck.json" if recheck else "score.json"), out)


# --- the page -------------------------------------------------------------------------------------------------------

CSS = """
:root { --bg:#fbfaf7; --card:#ffffff; --fg:#1d1d1f; --mute:#6b6b70; --line:#dcdad3; --on:#2f5d8a; --on-fg:#fff; }
@media (prefers-color-scheme: dark) { :root { --bg:#141416; --card:#1d1d20; --fg:#ececee; --mute:#9a9aa2;
  --line:#34343a; --on:#6f9fd0; --on-fg:#0d1117; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI",
  Roboto, sans-serif; }
main { max-width:760px; margin:0 auto; padding:16px 16px 120px; }
h1 { font-size:1.35rem; margin:.4rem 0 .6rem; }
.intro { color:var(--mute); }
.item { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; margin:18px 0; }
.item.current { border-color:var(--on); }
.num { color:var(--mute); font-size:.85rem; }
.plays { display:flex; flex-wrap:wrap; gap:8px; margin-top:.4rem; }
.plays button { min-height:52px; border-radius:10px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); padding:0 14px; font-weight:600; font-size:1rem; flex:1 1 70px; cursor:pointer; }
.plays .src[aria-pressed="true"] { background:var(--on); color:var(--on-fg); border-color:var(--on); }
.plays .sw { flex:1 1 40%; }
.plays .stop { flex:0 0 64px; }
.now { min-height:1.4em; color:var(--mute); font-size:.9rem; margin:.5rem 0; }
.q { font-weight:600; margin:.6rem 0 .3rem; }
.rate, .conf { display:flex; gap:8px; flex-wrap:wrap; margin:.3rem 0 .5rem; }
.rate button, .conf button { min-height:44px; border-radius:9px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); font-size:.95rem; cursor:pointer; flex:1 1 120px; }
.rate button[aria-pressed="true"], .conf button[aria-pressed="true"] { background:var(--on); color:var(--on-fg);
  border-color:var(--on); }
.note { width:100%; min-height:44px; border-radius:9px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); padding:8px 10px; font-size:.95rem; }
.done { color:var(--on); font-size:.85rem; min-height:1.2em; }
footer { position:fixed; left:0; right:0; bottom:0; background:var(--card); border-top:1px solid var(--line);
  padding:10px 16px calc(10px + env(safe-area-inset-bottom)); display:flex; gap:8px; justify-content:center; }
footer button { min-height:48px; border-radius:10px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); padding:0 18px; font-weight:600; font-size:1rem; }
footer .primary { background:var(--on); color:var(--on-fg); border-color:var(--on); }
#exp { display:none; position:fixed; inset:10% 5% auto 5%; max-width:640px; margin:0 auto; background:var(--card);
  border:1px solid var(--line); border-radius:14px; padding:16px; z-index:5; }
#exp textarea { width:100%; height:220px; font:12px/1.4 ui-monospace, monospace; background:var(--bg);
  color:var(--fg); border:1px solid var(--line); border-radius:8px; }
#exp .row { display:flex; gap:8px; margin-top:8px; }
#exp .row button { flex:1; min-height:44px; border-radius:9px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); }
"""

# Both clips of an item decode and start together on loop, each through its own gain; A and B set which one is heard
# with a short crossfade, so a switch keeps the playback position (build_page2's and cc_drive_page's player).
JS = r"""
const DATA = JSON.parse(document.getElementById("data").textContent);
const CLIPS = JSON.parse(document.getElementById("clips").textContent);
const STORE = "judge-ear:" + DATA.build;
const XF = XFADE_S, SIDES = ["1", "2"], RATINGS = RATINGS_JSON;
let ans = {};
try { ans = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { ans = {}; }
function save() { try { localStorage.setItem(STORE, JSON.stringify(ans)); } catch (e) {} }
const items = Array.from(document.querySelectorAll(".item"));
let actx = null, cur = null, token = 0;
const bufs = {};
try { if (navigator.audioSession) navigator.audioSession.type = "playback"; } catch (e) {}
function bytes(k) { const b = atob(CLIPS[k]); const u = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u.buffer; }
function decode(k) { if (!bufs[k]) bufs[k] = new Promise((ok, no) => actx.decodeAudioData(bytes(k), ok, no));
  return bufs[k]; }
function mark() {
  items.forEach(it => it.querySelectorAll(".src").forEach(b => b.setAttribute("aria-pressed",
    String(!!cur && cur.it === it && Number(b.dataset.side) === cur.side))));
  if (cur) cur.it.querySelector(".now").textContent = "Playing " + "AB"[cur.side] + " (loops; switch any time)";
}
function stop() {
  token++;
  if (!cur) return;
  cur.srcs.forEach(s => { try { s.stop(); } catch (e) {} });
  cur.it.querySelector(".now").textContent = ""; cur = null; mark();
}
async function start(it, side) {
  stop();
  const my = token;
  items.forEach(i => i.classList.remove("current")); it.classList.add("current");
  if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
  try { await actx.resume(); } catch (e) {}
  it.querySelector(".now").textContent = "Loading...";
  let b;
  try { b = await Promise.all(SIDES.map(x => decode(it.dataset.id + "-" + x))); }
  catch (e) { it.querySelector(".now").textContent = "This browser could not decode the clips."; return; }
  if (my !== token) return;
  const end = Math.min(...b.map(x => x.duration)), t0 = actx.currentTime + 0.05;
  const srcs = [], gains = [];
  b.forEach((buf, j) => {
    const s = actx.createBufferSource(); s.buffer = buf; s.loop = true; s.loopStart = 0; s.loopEnd = end;
    const g = actx.createGain(); g.gain.value = j === side ? 1 : 0;
    s.connect(g); g.connect(actx.destination); s.start(t0); srcs.push(s); gains.push(g);
  });
  cur = {it: it, srcs: srcs, gains: gains, side: side}; mark();
}
function pick(it, side) {
  if (!cur || cur.it !== it) { start(it, side); return; }
  if (cur.side === side) return;
  const t = actx.currentTime;
  cur.gains.forEach((g, j) => { g.gain.cancelScheduledValues(t); g.gain.setValueAtTime(g.gain.value, t);
    g.gain.linearRampToValueAtTime(j === side ? 1 : 0, t + XF); });
  cur.side = side; mark();
}
function flip(it) { if (cur && cur.it === it) pick(it, 1 - cur.side); else start(it, 0); }
function paint() {
  let n = 0;
  items.forEach(it => {
    const a = ans[it.dataset.id] || {};
    it.querySelectorAll(".rate button").forEach(b => b.setAttribute("aria-pressed", String(a.rating === b.dataset.r)));
    it.querySelectorAll(".conf button").forEach(b => b.setAttribute("aria-pressed", String(a.conf === b.dataset.c)));
    const full = !!(a.rating && a.conf);
    it.querySelector(".done").textContent = full ? "Answered" : "";
    if (full) n++;
    const note = it.querySelector(".note"); if (document.activeElement !== note) note.value = a.note || "";
  });
  document.getElementById("count").textContent = n + " of " + items.length + " answered";
}
items.forEach(it => {
  const id = it.dataset.id;
  it.querySelectorAll(".src").forEach(b => b.addEventListener("click", () => pick(it, Number(b.dataset.side))));
  it.querySelector(".sw").addEventListener("click", () => flip(it));
  it.querySelector(".stop").addEventListener("click", stop);
  it.querySelectorAll(".rate button").forEach(b => b.addEventListener("click", () => {
    const a = ans[id] = ans[id] || {}; a.rating = a.rating === b.dataset.r ? undefined : b.dataset.r; save(); paint();
  }));
  it.querySelectorAll(".conf button").forEach(b => b.addEventListener("click", () => {
    const a = ans[id] = ans[id] || {}; a.conf = a.conf === b.dataset.c ? undefined : b.dataset.c; save(); paint();
  }));
  it.querySelector(".note").addEventListener("input", e => {
    const a = ans[id] = ans[id] || {}; a.note = e.target.value; save(); paint(); });
});
document.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey || (e.target.closest && e.target.closest("input, textarea"))) return;
  const it = cur ? cur.it : document.querySelector(".item.current") || items[0];
  const k = (e.key || "").toLowerCase();
  if (k === "a" || k === "1") { e.preventDefault(); pick(it, 0); }
  else if (k === "b" || k === "2") { e.preventDefault(); pick(it, 1); }
  else if (k === "s") { e.preventDefault(); flip(it); }
  else if (k === "escape" || k === " ") { e.preventDefault(); stop(); }
});
function exportText() {
  const lines = ["judge-ear build " + DATA.build + " " + new Date().toISOString()];
  items.forEach(it => {
    const a = ans[it.dataset.id] || {};
    lines.push(it.dataset.n + " " + it.dataset.id + " " + (a.rating || "-") + " " + (a.conf || "-")
      + (a.note ? " | " + a.note : ""));
  });
  lines.push(JSON.stringify({page: "judge-ear", build: DATA.build, answers: ans}));
  return lines.join("\n");
}
document.getElementById("next").addEventListener("click", () => {
  const it = items.find(i => { const a = ans[i.dataset.id] || {}; return !(a.rating && a.conf); });
  if (it) { it.scrollIntoView({behavior: "smooth", block: "start"}); items.forEach(i => i.classList.remove("current"));
    it.classList.add("current"); }
});
document.getElementById("export").addEventListener("click", () => { stop();
  document.getElementById("out").value = exportText(); document.getElementById("exp").style.display = "block"; });
document.getElementById("close").addEventListener("click", () => document.getElementById("exp").style.display = "none");
document.getElementById("copy").addEventListener("click", async () => {
  const t = document.getElementById("out"); t.select();
  try { await navigator.clipboard.writeText(t.value); } catch (e) { document.execCommand("copy"); } });
document.getElementById("save").addEventListener("click", () => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([exportText()], {type: "text/plain"}));
  a.download = "judge-ear-answers-" + DATA.build + ".txt"; a.click(); });
paint();
"""


def page_html(ids, clips, build, note=None):
    """The page: per item A and B looping together with an instant switch, "How different do these sound?" (same /
    barely / clearly / very) and sure or unsure; answers in localStorage, Export as text or a file."""
    e = html.escape
    total = len(ids)
    cards = []
    for n, pid in enumerate(ids, 1):
        rate = "".join(f'<button type="button" data-r="{r}">{e(RATING_TEXT[r])}</button>' for r in RATINGS)
        cards.append(
            f'<article class="item" data-id="{pid}" data-n="{n}"><div class="num">{n} / {total}</div>'
            '<div class="plays">'
            '<button type="button" class="src" data-side="0" aria-pressed="false">A</button>'
            '<button type="button" class="src" data-side="1" aria-pressed="false">B</button>'
            '<button type="button" class="sw">Switch A/B (S)</button>'
            '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div>'
            '<p class="now"></p>'
            f'<div class="q">How different do these sound?</div><div class="rate">{rate}</div>'
            '<div class="conf"><button type="button" data-c="sure">Sure</button>'
            '<button type="button" data-c="unsure">Unsure</button></div>'
            '<input class="note" type="text" placeholder="Note (optional)" aria-label="Note">'
            '<div class="done"></div></article>')
    data = json.dumps({"build": build, "items": ids}).replace("</", "<\\/")
    js = JS.replace("XFADE_S", repr(XFADE_S)).replace("RATINGS_JSON", json.dumps(list(RATINGS)))
    minutes = round(total * 30 / 60)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>How different do these sound?</title>
<style>{CSS}</style></head><body>
<main>
<h1>How different do these sound?</h1>
<p class="intro">{total} pairs, about {minutes} minutes. Each pair is the same 10 seconds of one guitar, played alone,
as A and B. A and B loop together and the switch is instant: it lands at the same moment of the playing. Tap A or B,
or Switch, or press A, B or S (Space stops). Switch as often as you like.</p>
<p class="intro">For each pair, say how different A and B sound: the same, barely different, clearly different or very
different, then whether you are sure. Some pairs may be the very same sound twice. A and B are set to the same
loudness, so listen for the sound itself, not a volume change. Headphones help. Answers are saved in this browser as
you go; tap <b>Export</b> any time, even halfway, and send the text or the file.</p>
{f'<p class="intro"><b>{e(note)}</b></p>' if note else ""}
{"".join(cards)}
</main>
<footer><span id="count" style="align-self:center;color:var(--mute)"></span>
<button type="button" id="next">Next unanswered</button>
<button type="button" id="export" class="primary">Export</button></footer>
<div id="exp"><b>Your answers</b><p class="intro">Copy it or save it as a file, and send it.</p>
<textarea id="out" readonly></textarea>
<div class="row"><button type="button" id="copy">Copy</button><button type="button" id="save">Save file</button>
<button type="button" id="close">Close</button></div></div>
<script id="data" type="application/json">{data}</script>
<script id="clips" type="application/json">{json.dumps(clips)}</script>
<script>{js}</script></body></html>"""


def anchor_audio():
    """{item: (S render, the other side)} for stage A: each anchor from S's stored render, the two first-page pairs."""
    import numpy as np

    plan = load(out_dir() / "plan.json")
    meas = load(out_dir() / "measure.json")
    from learn import audibility_measure as AM

    S = {}
    for cls in ("clean", "crunch"):
        S[cls] = np.load(render_path(DATA, f"{cls}-S"))
        if AM.audio_sha(S[cls]) != meas["render_sha256"][f"{cls}-S"]:
            raise SystemExit(f"{cls}-S: not the render `measure` judged")
    out = {anchor_id(c, k, d): (S[c], shelve(np.asarray(S[c], np.float64), k, d)) for c, k, d in ANCHORS}
    by = {p["pair"]: p for p in plan["pairs"]}
    for pid in ANCHOR_PAIRS:
        p = by[pid]
        out[pid] = (S[p["cls"]], np.load(render_path(DATA, job_of(p))))
    return out


def cmd_anchors(args):
    """Stage A's tonal-anchor page and key, and J0's distance per item (anchors.json); zero plugin renders."""
    require_v4()
    import numpy as np

    from learn import audibility_measure as AM
    from learn import knob_ceiling as K

    kp = key_path(anchors=True)
    if kp.exists() and not args.force:
        raise SystemExit(f"{kp} exists: a rebuild hides the listener's stored answers (--force)")
    audio = anchor_audio()
    di = np.asarray(np.load(out_dir() / "di.npy"), np.float64)
    lo, hi = trim()
    di = di[lo:hi]
    judged = {}
    for item, (s, o) in audio.items():
        h = K.judge(s, o, di, 0)
        judged[item] = {"judge": h, "mean": (h["A"] + h["B"]) / 2}
    items = page_order(list(audio), ANCHOR_SEED)
    clips, key_items = {}, []
    for it in items:
        s, o = audio[it["pair"]]
        a, b = (s, o) if it["a"] == "S" else (o, s)
        clips[it["page_id"] + "-1"], clips[it["page_id"] + "-2"] = AM.pair_clips(a, b, out_dir() / "page-cache")
        cls = it["pair"].split("-")[0]
        key_items.append({**it, "cls": cls, "group": "anchor" if "-anchor-" in it["pair"] else it["pair"].split("-")[1],
                          "b": "step" if it["a"] == "S" else "S"})
    build = hashlib.sha256((json.dumps(key_items, sort_keys=True) + str(ANCHOR_SEED)).encode()).hexdigest()[:12]
    page = page_html([it["page_id"] for it in items], clips, build, RECHECK_NOTE)
    bad = leaks(page)
    if bad:
        raise SystemExit(f"the page names {bad}: not blind")
    save(kp, {"page": PAGE_NAME + "-anchors", "build": build, "seed": ANCHOR_SEED,
              "time": time.strftime("%Y-%m-%d %H:%M:%S"),
              "shuffle_rule": "random.Random(ANCHOR_SEED).shuffle of the sorted item ids, then one choice of A's side",
              "anchor_rule": "RBJ shelf slope 1 at SHELF_HZ on S's stored render (scipy lfilter), before the clip rule",
              "items": key_items})
    save(out_dir() / "anchors.json", {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "build": build, "items": judged})
    pd = page_dir(anchors=True)
    pd.mkdir(parents=True, exist_ok=True)
    (pd / "index.html").write_text(page)
    print(f"ANCHORS PAGE DONE: {len(items)} items -> {pd / 'index.html'}; build {build}; key {kp}")


def cmd_anchors_score(args):
    """Each anchor's rating beside J0's distance, and the declared outcome."""
    require_v4()
    key = load(key_path(anchors=True))
    judged = load(out_dir() / "anchors.json")
    if not key or not judged:
        raise SystemExit("run `anchors` first")
    ans = parse_answers(pathlib.Path(args.answers).read_text(), key["build"])
    rows = []
    for it in key["items"]:
        a = ans.get(it["page_id"], {})
        rows.append({"item": it["pair"], "page_id": it["page_id"], "judge": judged["items"][it["pair"]]["mean"],
                     "rating": a.get("rating"), "conf": a.get("conf")})
    for r in sorted(rows, key=lambda r: r["item"]):
        print(f"  {r['page_id']} {r['item']:24s} J0 {r['judge']:.3f}  {r['rating'] or '-'}")
    by = {r["item"]: r["rating"] for r in rows}
    six = [i for i in by if "-anchor-" in i and i.endswith(("+6", "-6"))]
    heard = sum(by[i] in LOUD for i in six)
    ctl = by[anchor_id("clean", "high", 12)]
    if ctl in QUIET:
        outcome = "the +12 dB control heard as same/barely: the page or the bias is the problem; stage B waits"
    elif heard >= 4:
        outcome = f"{heard} of {len(six)} 6-dB anchors heard: steady tilts heard; stage B keeps F44's tone sizes"
    elif heard <= 2:
        outcome = f"{heard} of {len(six)} 6-dB anchors heard: not heard on this page; stage B's tone steps doubled"
    else:
        outcome = f"{heard} of {len(six)} 6-dB anchors heard: mixed; F44's sizes kept, the split reported"
    print("OUTCOME:", outcome)
    save(out_dir() / "anchors-score.json", {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "build": key["build"],
                                            "answers_file": str(args.answers), "rows": rows, "outcome": outcome})


COMMANDS = {"plan": cmd_plan, "render": cmd_render, "measure": cmd_measure, "page": cmd_page, "score": cmd_score,
            "anchors": cmd_anchors, "anchors-score": cmd_anchors_score}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="judge_ear", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=parse_shard, default=(0, 1))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--answers", default=None)
    ap.add_argument("--recheck", action="store_true")
    args = ap.parse_args(argv)
    if args.shard != (0, 1) and args.cmd != "render":
        raise SystemExit("--shard is for render")
    if args.force and args.cmd not in ("plan", "page", "anchors"):
        raise SystemExit("--force is for plan and page")
    if args.recheck and args.cmd not in ("page", "score"):
        raise SystemExit("--recheck is for page and score")
    if args.cmd in ("score", "anchors-score") and not args.answers:
        raise SystemExit("score needs --answers FILE")
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
