"""The real-song exam (Step 1 of the 2026-11-16 review's plan; `docs/real-song-exam-plan.md`; ledger `pipeline-fix`
`phase_exam`, `phase_exam_inputs`, `phase_exam_answers`, `phase_exam_ear`): the shipped model path run once on V-real's
released mixes, its one preset scored through the song's own DI against the real amp track, beside generate's research
preset, the starting preset S, the constants and the stored search label. A declared baseline: nothing is adopted.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -m learn.real_song_exam inputs              # the released mixes decoded, the spans, truth-side strata (no render)
    $MAIN -m learn.real_song_exam guards              # the leakage guard on C3r-all, the adopted pair, S's control
    $MAIN -m learn.real_song_exam r1-repro            # one stored R1 run's answers, renders and pick again (12 renders)
    $MAIN -m learn.real_song_exam research-prepare    # the blinded research folders (outside the data root)
    $MAIN -m learn.real_song_exam research-route      # one headless generate run each (agent credits)
    $MAIN -m learn.real_song_exam research-collect    # the transcript audit, R's class and its presets (no render)
    $MAIN -m learn.real_song_exam chain               # the model path's arms, one run at a time (separations, renders)
    $MAIN -m learn.real_song_exam c-pick              # the stock-DI pick on C's presets (24 renders)
    $MAIN -m learn.real_song_exam answers             # every arm's answers file and the zero-render tables
    $MAIN -u -m learn.real_song_exam render --shard k/3   # the judge renders, once the answers' hashes are in the ledger
    $MAIN -m learn.real_song_exam report --label exam     # the rows (no render)
    $MAIN -m learn.real_song_exam page                # the listening page (no render: it plays the judged renders)
    $MAIN -m learn.real_song_exam score --answers FILE    # the page's read

The arms (vreal/answers/EX-*.json, vreal/judge/EX-*/): R, R-wet and R-route from one blinded research run per unit; M,
M-x, M-crop, M-unity and M-lab from `scripts/model_preset.py`; M3 (M's answers on all three amps); C and C-own (Step 2's
all-labels constants, `ladder/centres.json`), C-pick (the stock-DI pick on C); L (the stored ZT label); S (stored, and
re-rendered on M's amp). The pure parts (the span rule, the pan fit, the values and rows, the centres' shape, the knob
distance, the audit, the page's draw and read) are unit-tested; the stages are not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import random
import re
import shutil
import statistics
import subprocess
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import pipeline_fix as P  # noqa: E402  (stdlib at import)
from learn import pipeline_review as PR  # noqa: E402

PLAN = "docs/real-song-exam-plan.md"
PHASE, PHASE_INPUTS, PHASE_ANSWERS, PHASE_EAR = ("phase_exam", "phase_exam_inputs", "phase_exam_answers",
                                                 "phase_exam_ear")
SEED = 20261161                       # the exam's draws (neutral names, research tags, the page); unused elsewhere
PAGE_SEED, BOOT_SEED = 20261162, 20261163
AMPS = PR.AMPS
OTHER = PR.HELD                       # a search half -> its held half (and back)
ANY = P.ANY_HALF
SELECT_AMP = {0: "ac20", 1: "pr12", 2: "sw50r"}   # the manifest's selectedAmp enum
SPAN_DB, SPAN_BLOCKS, BLOCK_S, EDGE_S = 25.0, 10, 1.0, 2.0   # the part's span (plan section 4)
PAN_LAG = 4800                        # the pan fit's lag search, +-100 ms (real mixes move single tracks)
CENTRED_P = 0.15                      # S0's centred stratum: |p| at most this on the constant-power pan scale
CROP_SD_TOL, CROP_R_TOL = 0.5, 0.005  # the decoded file's crop check against alignment.json's
MATCH_R = 0.999                       # a crop's mix and DI must correlate this well with the session's
TAG = "EX-"
ONE = ("EX-R", "EX-Rwet", "EX-Rroute", "EX-M", "EX-Mx", "EX-Mlab", "EX-Mcrop", "EX-Munity", "EX-Cpick", "EX-Cm",
       "EX-Cownm", "EX-S", "EX-Sm")   # one preset per slug, on its own amp
THREE = ("EX-M3", "EX-C", "EX-Cown")  # every amp
HALVED = ("EX-L",)                    # per search half
TAGS = ONE + THREE + HALVED
CHAIN = ("M", "Mcrop", "Munity", "Mlab", "Mx")    # the order the chain runs them (M first: M-unity and M-x read M's
CHAIN_TAG = {"M": "EX-M", "Mx": "EX-Mx", "Mlab": "EX-Mlab", "Mcrop": "EX-Mcrop", "Munity": "EX-Munity"}   # window)
STORED = {"FT": "FV-P2b-ft-stem", "D_fix": "DV-P2b-dfix-stem", "RcG": "DV-RcG"}   # F41/F42's renders, beside
CENTRES = "ladder/centres.json"       # Step 2's stage 0 writes it (the orchestrator's choice, 2026-11-16)
CENTRE_NAMES = {"EX-C": "cen", "EX-Cown": "aconst"}   # the ladder's `centres` keys
ADOPTED_BASE = "C3r-all"
WORK = pathlib.Path.home() / "gtr-q"  # a fresh root, outside the data root and the repo, holding only the venv, the
RUNS = WORK / "runs"                  # plugin, the runs' settings and this exam's runs
PLUGIN = WORK / "plugin"
VENV = WORK / "venv"
SETTINGS_DIR = WORK / "settings"
OLD_WORK = pathlib.Path.home() / "gtr-session"    # the routing study's runs on these songs: denied to every run
DENY = ("~/ndsp-presets/**", "//Users/yoavbz/ndsp-presets/**", "//Users/yoavbz/projects/**", "~/.claude/**",
        "//private/tmp/claude-501/**", "~/gtr-session/**", "//Users/yoavbz/gtr-session/**")
PLUGIN_PARTS = ("skills", "scripts", "packs", "reference", "analysis", "format", "match", "samples", ".claude-plugin",
                "pyproject.toml", "LICENSE", "NOTICE.md")   # the routing study's scrubbed plugin
LEAK_CALLS = ("ndsp-presets", "/Users/yoavbz/projects", "YoavBZ", "neuraldsp-preset-generator/docs", "validation-",
              "generate-routing", "real-song-exam", "mix-previews", "pipeline-fix", "learn/trusted-data",
              "gtr-session", ".claude/projects")
LEAK_RESULTS = ("YoavBZ/neuraldsp-preset-generator", "real-song-exam", "validation-crops")
ACCOUNT = "yoavbz"                    # the user's account name: never in a web search or fetch (case-insensitive)
RESEARCH_TOOLS = ("WebSearch", "WebFetch")
FILE_TOOLS = ("Bash", "Read", "Glob", "Grep", "Edit", "Write", "NotebookEdit")
ALLOWED_ROOTS = ("/Library/Audio/", "/tmp/", "/private/tmp/", "/private/var/folders/", "/var/folders/")   # the
#                 factory presets and the installed plugin, and scratch space, beside the run's own paths
PATH_RE = re.compile(r"""(?:^|(?<=[\s"'=(<>|;&,]))(~(?=/|\s|$|["'])[^\s"'\\;|&<>()]*|/(?:Users|private|tmp|var|Volumes|opt|"""
                     r"""home|Library|Applications|System)\b[^\s"'\\;|&<>()]*)""")
SENSITIVE_CALL = ("ndsp-presets", "/projects", "gtr-session", "/.claude", "claude-")   # a stop in a call, wherever
SENSITIVE_RESULT = ("/projects/", "gtr-session", "/.claude/", "claude-", "ndsp-presets/learn", "ndsp-presets/references",
                    "ndsp-presets/listening", "ndsp-presets/handover")   # a stop in a file tool's result (the plugin's
#                     own text names its default data root and its auditions and tools folders: recorded, no stop)
TITLE_NAMES = (r"wickerman", r"eat the feeder", r"femme", r"wall of death", r"colour me red", r"diesel ?13",
               r"let'?s dance", r"szymon", r"get out of bed", r"magician'?s nephew", r"zeno", r"it was my fault",
               r"atlantis bound", r"cambridge")
PROMPT = """I'd like a Morgan Amps Suite preset for the electric guitar in "{song}" by {artist}.

The file ./{audio} is the whole song; the part I mean is the electric guitar playing from {start} to {end} in that
file. Use the generate skill of the neuraldsp-preset-generator plugin.

To save you asking: the pack is Morgan Amps Suite; I don't want the listening page; don't install anything or save
notes. Run the plugin's Python scripts with {python} and pass --data-dir {data} where a script takes it.
Write whatever you would install to ./out/ instead of installing it.

When done, write ./result.json with these keys:
  "gain_class": "clean", "crunch" or "heavier" (the starting-preset class you chose),
  "amp": "pr12", "sw50r" or "ac20",
  "template": the starting preset file you used,
  "recipes": the --recipe values you applied, in order,
  "spec": the spec you applied (as JSON),
  "apply_command": the exact apply_spec.py command that wrote the preset (the main one, not a second starting point),
  "preset": the path of that preset file,
  "outputs": each file you wrote to ./out/ and the starting preset it was built from,
  "reasons": two or three sentences on why this class and amp.
"""


# --- the pure parts (tests/test_real_song_exam.py) --------------------------------------------------------------------

def units():
    """V-real-11's 10 units, Wickerman ElecGtr2 and 3 one (one input, two truths). -> [{key, members, band, cls}]."""
    by = {}
    for slug, (band, cls) in sorted(PR.VREAL.items()):
        k = P.vreal_part_key(slug)
        u = by.setdefault(k, {"key": k, "members": [], "band": band, "cls": cls})
        if (u["band"], u["cls"]) != (band, cls):
            raise SystemExit(f"{k}: its members differ in band or class")
        u["members"].append(slug)
    return [by[k] for k in sorted(by)]


def model_class(cls):
    """The class the model path is told: research's, a heavier route as crunch (the model knows two classes)."""
    if cls not in ("clean", "crunch", "heavier", "high-gain"):
        raise SystemExit(f"research's class {cls!r} is none of clean, crunch, heavier")
    return "crunch" if cls in ("heavier", "high-gain") else cls


def span_rule(crop, lo, hi, ok_at, max_blocks=SPAN_BLOCKS, block=BLOCK_S):
    """The part's span (plan section 4): 1-s blocks added outward from the crop (a, b) while `ok_at(t0, t1)` holds (the
    part's DI within SPAN_DB of its crop level) and the block stays inside [lo, hi], at most `max_blocks` a side.
    -> {span: [start, end], before, after, stopped: {before, after}} (the stop: "level", "edge" or "max")."""
    a, b = crop
    n, why = {"before": 0, "after": 0}, {}
    for side in ("before", "after"):
        why[side] = "max"
        for j in range(1, max_blocks + 1):
            t0, t1 = (a - j * block, a - (j - 1) * block) if side == "before" else (b + (j - 1) * block, b + j * block)
            if t0 < lo - 1e-9 or t1 > hi + 1e-9:
                why[side] = "edge"
                break
            if not ok_at(t0, t1):
                why[side] = "level"
                break
            n[side] = j
    return {"span": [a - n["before"] * block, b + n["after"] * block], "before": n["before"], "after": n["after"],
            "stopped": why}


def pan_position(gl, gr):
    """S0's constant-power pan scale, inverted: (L, R) gains -> p in [-1, 1] (0 centred, -1 hard left)."""
    if not (gl or gr):
        return None
    return 4 * math.atan2(abs(gr), abs(gl)) / math.pi - 1


def centred(p, tol=CENTRED_P):
    return p is not None and abs(p) <= tol


def fit_pan(ref, left, right, max_lag=PAN_LAG):
    """The target's place in a stereo mix: the lag (|lag| <= max_lag, mix[t] ~ g ref[t - lag]) that maximises the
    summed squared correlation with both channels, then each channel's least-squares gain at that lag. -> {lag, gl,
    gr, p, target_db (the target's power against the mix's, both channels), r2 (the share of the mix it explains)}."""
    import numpy as np

    x = np.asarray(ref, np.float64)
    ch = [np.asarray(c, np.float64) for c in (left, right)]
    n = min(len(x), *(len(c) for c in ch))
    x, ch = x[:n], [c[:n] for c in ch]
    m = 1 << int(np.ceil(np.log2(2 * n)))
    X = np.fft.rfft(x, m)
    cc = [np.fft.irfft(np.fft.rfft(c, m) * np.conj(X), m) for c in ch]
    lags = np.r_[np.arange(0, max_lag + 1), np.arange(-max_lag, 0)]
    score = sum(c[lags % m] ** 2 for c in cc)
    lag = int(lags[int(np.argmax(score))])

    def shifted(y):
        out = np.zeros(n)
        if lag >= 0:
            out[lag:] = y[:n - lag]
        else:
            out[:n + lag] = y[-lag:]
        return out

    xs = shifted(x)
    ee = float(np.dot(xs, xs)) or 1e-30
    g = [float(np.dot(c, xs) / ee) for c in ch]
    res = sum(float(np.sum((c - gi * xs) ** 2)) for c, gi in zip(ch, g))
    tot = sum(float(np.sum(c ** 2)) for c in ch) or 1e-30
    tp = (g[0] ** 2 + g[1] ** 2) / 2 * ee / n
    return {"lag": lag, "gl": g[0], "gr": g[1], "p": pan_position(*g), "r2": 1 - res / tot,
            "target_db": 10 * math.log10(max(tp, 1e-30) / (tot / (2 * n)))}


def held_value(group, held):
    """A judge group's distance on the held half: an any-half answer's, else the one searched on the other half."""
    if group is None:
        return None
    v = group.get(ANY) if ANY in group else group.get(OTHER[held])
    return None if v is None else v.get(held)


def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def spec_amps(amp_of, spec, slug):
    """(tag, [amps]) a row spec reads on one slug, or (tag, None) when the arm has no answer there. spec: (tag, rule[,
    override tag]); rule "own" (the slug's one amp in the tag's answers), "all", "best", "amp:<amp>", "at:<tag>" (the
    other tag's amp); an override tag with an answer for the slug replaces the spec by (override, "own")."""
    tag, rule = spec[0], spec[1]
    if len(spec) > 2 and slug in amp_of.get(spec[2], {}):
        tag, rule = spec[2], "own"
    if rule == "own":
        return tag, ([amp_of[tag][slug]] if slug in amp_of.get(tag, {}) else None)
    if rule in ("all", "best"):
        return tag, list(AMPS)
    if rule.startswith("amp:"):
        return tag, [rule[4:]]
    if rule.startswith("at:"):
        ref = rule[3:]
        return tag, ([amp_of[ref][slug]] if slug in amp_of.get(ref, {}) else None)
    raise SystemExit(f"unknown rule {rule!r}")


def spec_value(judge, amp_of, spec, slug, held, s_of):
    """One arm's ln distance on a slug's held half: the mean over the amps it reads ("best": the least). A refused
    (non-finite) answer scores as S on its amp (`s_of(amp)`, the established V-real rule). -> (value or None, refused)."""
    tag, amps = spec_amps(amp_of, spec, slug)
    best = spec[1] == "best" and tag == spec[0]
    if amps is None:
        return None, 0
    vals, refused = [], 0
    for a in amps:
        x = held_value(judge.get(tag, {}).get(f"{slug}|{a}"), held)
        if x is None:
            return None, 0
        if not finite(x):
            refused += 1
            x = s_of(a)
        vals.append(math.log(x))
    return (min(vals) if best else statistics.fmean(vals)), refused


def exam_rows(judge, amp_of, spec_a, spec_b, slugs, band_of, unit_of, base="S"):
    """[(band, unit, ln(d_a / d_b))] on each slug's held halves, for arms on any amps. A held half where S is not finite
    on some amp drops for every row; a missing answer leaves the row incomplete. -> (rows, counts)."""
    rows = []
    cnt = {"directions": 0, "base_dropped": 0, "missing": 0, "refused_scored_as_S": 0}
    for slug in sorted(slugs):
        for held in ("A", "B"):
            cnt["directions"] += 1
            s = {a: held_value(judge.get(base, {}).get(f"{slug}|{a}"), held) for a in AMPS}
            if not all(finite(v) for v in s.values()):
                cnt["base_dropped"] += 1
                continue
            va, ra = spec_value(judge, amp_of, spec_a, slug, held, s.get)
            vb, rb = spec_value(judge, amp_of, spec_b, slug, held, s.get)
            if va is None or vb is None:
                cnt["missing"] += 1
                continue
            cnt["refused_scored_as_S"] += ra + rb
            rows.append((band_of[slug], unit_of[slug], va - vb))
    cnt["complete"] = cnt["missing"] == 0 and cnt["base_dropped"] == 0
    return rows, cnt


def stratified(rows, attrs):
    """`pipeline_fix.clustered` on all rows and on each declared stratum of the unit's attributes."""
    out = {"all": P.clustered(rows)}
    for name, test in (("clean", lambda a: a["cls"] == "clean"), ("crunch", lambda a: a["cls"] == "crunch"),
                       ("dense", lambda a: a["density"] == "dense"), ("sparse", lambda a: a["density"] == "sparse"),
                       ("centred", lambda a: a["centred"] is True), ("off-centre", lambda a: a["centred"] is False),
                       ("v_real_10", lambda a: a["v10"])):
        sub = [r for r in rows if test(attrs[r[1]])]
        out[name] = P.clustered(sub) if sub else None
    return out


def centre_answers(doc, name):
    """Step 2's all-labels constant `name` ("cen", the labels' centre, or "aconst", the model's own constant) from
    ladder/centres.json, the ladder's shape: doc["centres"][name][amp][cls] = {"select", "settings": {"module/key":
    v}}. (The ladder's uncommitted all_labels.Cen / all_labels.Aconst variant is read the same.) -> {amp: {cls: {select
    (int), settings}}}; refuses anything else."""
    block = ((doc or {}).get("centres") or {}).get(name)
    if block is None:
        block = ((doc or {}).get("all_labels") or {}).get({"cen": "Cen", "aconst": "Aconst"}.get(name, name))
    if not isinstance(block, dict):
        raise SystemExit(f"{CENTRES}: no centres.{name}")
    out = {}
    for a in AMPS:
        for c in ("clean", "crunch"):
            v = (block.get(a) or {}).get(c) if isinstance(block.get(a), dict) else None
            if not isinstance(v, dict) or not isinstance(v.get("settings"), dict) or not v["settings"] \
                    or not all("/" in k for k in v["settings"]):
                raise SystemExit(f"{CENTRES}: centres.{name}.{a}.{c} is not a full {{select, settings}}")
            try:
                sel = int(v["select"])
            except (KeyError, TypeError, ValueError):
                raise SystemExit(f"{CENTRES}: centres.{name}.{a}.{c} has no amp select") from None
            if SELECT_AMP.get(sel) != a:
                raise SystemExit(f"{CENTRES}: centres.{name}.{a}.{c} selects {SELECT_AMP.get(sel)}")
            out.setdefault(a, {})[c] = {"select": sel, "settings": v["settings"]}
    return out


def centres_refusal(doc, adopted_sha, hold_prefix="C3-cabS"):
    """Why ladder/centres.json may not be read as the adopted pair's constants, or None: its `model_sha256` must be the
    adopted pair's (both seeds, adopted-model.json's order) and its `hold` C3-cabS. (Pure.)"""
    got = list((doc or {}).get("model_sha256") or [])
    if got != list(adopted_sha):
        return f"{CENTRES}: model_sha256 {[g[:12] for g in got]} is not the adopted pair's"
    if not str((doc or {}).get("hold") or "").startswith(hold_prefix):
        return f"{CENTRES}: hold {doc.get('hold')!r} is not {hold_prefix}"
    return None


def knob_distance(a, b, amp, params):
    """Two settings {"module/key": stored} on one amp, in the manifest's units: the continuous controls' mean and largest
    |difference| as a share of their range (frequencies on a log scale), and the switches and choices that differ. Other
    amps' modules are left out. params: the manifest's `parameters`."""
    others = tuple(x for x in AMPS if x != amp)
    cont, sw, en = [], 0, 0
    for k in sorted(set(a) & set(b)):
        mod = k.rsplit("/", 1)[0]
        if any(mod.startswith(o) for o in others):
            continue
        spec = params.get(k) or {}
        kind = spec.get("kind")
        try:
            x, y = float(a[k]), float(b[k])
        except (TypeError, ValueError):
            x = y = None
        if kind in ("rotation", "fraction") and x is not None:
            cont.append(abs(x - y))
        elif kind == "metered" and x is not None and spec.get("max") is not None:
            lo, hi = float(spec["min"]), float(spec["max"])
            if spec.get("unit") == "hz" and lo > 0:
                cont.append(abs(math.log(max(x, lo)) - math.log(max(y, lo))) / math.log(hi / lo))
            else:
                cont.append(abs(x - y) / (hi - lo))
        elif kind == "switch":
            sw += str(a[k]).lower() != str(b[k]).lower()
        elif kind == "enum":
            en += str(a[k]) != str(b[k])
    return {"cont_mean": statistics.fmean(cont) if cont else None, "cont_max": max(cont) if cont else None,
            "n_cont": len(cont), "switches_differ": sw, "choices_differ": en}


def text_of(obj):
    """Every string inside a tool call's input or a result's content, one a line (keys left out)."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return "\n".join(text_of(v) for v in obj.values())
    if isinstance(obj, list):
        return "\n".join(text_of(v) for v in obj)
    return "" if obj is None else str(obj)


def paths_in(text, home=str(pathlib.Path.home())):
    """The absolute (or ~) paths a tool call's or result's text names, each normalised (`..` resolved, ~ expanded)."""
    out = []
    for m in PATH_RE.finditer(text):
        p = m.group(1).rstrip(".,:")
        p = home + p[1:] if p.startswith("~") else p
        out.append(os.path.normpath(p))
    return out


def outside(paths, allowed):
    """The paths not under any of `allowed` (absolute roots: the run's own folder, the plugin, the venv, ALLOWED_ROOTS)."""
    roots = [os.path.normpath(str(a)) for a in allowed]
    return sorted({p for p in paths if not any(p == r or p.startswith(r.rstrip("/") + "/") for r in roots)})


def audit_transcript(lines, allowed=(), runs_root=None):
    """The research run's audit (plan guard 5). Excludes the run: a tool call naming the project's data, repository,
    tests or the earlier routing runs (LEAK_CALLS); a call naming a path outside `allowed` (the run's own folder, the
    plugin, the venv, the factory presets, scratch space) or under a sensitive root (SENSITIVE_CALL), or a relative
    `../`; the user's account name in a web search or fetch; a web result naming the project (LEAK_RESULTS); a file
    tool's result naming a path under SENSITIVE_RESULT or another run's folder (under `runs_root`). Every other outside
    path a result names is recorded ("result_paths"), not a stop: the plugin's own text names its default data root.
    lines: the stream-json text. -> {calls, leaks, seen, outside_calls, result_paths, result_leaks, tools, init}."""
    calls, web_calls, results, file_results, tools, init = [], [], [], [], {}, (None, None, None)
    names = {}
    for line in lines:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init" and init[0] is None:
            init = (ev.get("session_id"), ev.get("plugins"), ev.get("model"))
        content = ((ev.get("message") or {}).get("content")) or []
        if not isinstance(content, list):
            continue
        for c in content:
            if c.get("type") == "tool_use":
                text = text_of(c.get("input"))
                calls.append(text)
                names[c.get("id")] = c.get("name")
                tools[c.get("name")] = tools.get(c.get("name"), 0) + 1
                if c.get("name") in RESEARCH_TOOLS:
                    web_calls.append(text)
            elif c.get("type") == "tool_result":
                text = text_of(c.get("content"))
                tool = names.get(c.get("tool_use_id"))
                if tool in RESEARCH_TOOLS:
                    results.append(text)
                elif tool in FILE_TOOLS:
                    file_results.append(text)
    leaks = {m for m in LEAK_CALLS for call in calls if m in call}
    leaks |= {"account name in a web call" for w in web_calls if ACCOUNT in w.lower()}
    leaks |= {"../ in a call" for call in calls if re.search(r"(?<![\w/.])\.\./", call)}
    cp = [p for call in calls for p in paths_in(call)]
    oc = sorted(set(outside(cp, allowed) if allowed else []) | {p for p in cp if any(s in p for s in SENSITIVE_CALL)})
    rall = [p for r in file_results for p in paths_in(r)]
    rp = outside(rall, allowed) if allowed else []
    runs = os.path.normpath(str(runs_root or RUNS))
    rl = sorted({p for p in rall if any(s in p for s in SENSITIVE_RESULT)} | {p for p in rp if p.startswith(runs + "/")})
    seen = sorted({m for m in LEAK_RESULTS for r in results if m in r})
    return {"calls": len(calls), "leaks": sorted(leaks), "seen": seen, "outside_calls": oc, "result_paths": rp,
            "result_leaks": rl, "tools": tools, "init": init}


def audit_why(au):
    """The reasons an audited run is excluded (empty: it passes)."""
    return (list(au["leaks"]) + [f"seen in research results: {s}" for s in au["seen"]]
            + [f"a call names a path outside the run: {p}" for p in au["outside_calls"]]
            + [f"a file tool's result names {p}" for p in au["result_leaks"]])


def run_settings(tag, others, base):
    """One research run's sandbox settings: the routing study's (`base`), its reads also denied the earlier routing
    runs and every other run's folder of this exam."""
    s = json.loads(json.dumps(base))
    deny = list(s["permissions"]["deny"])
    for d in DENY + tuple(f"//{str(RUNS / o).lstrip('/')}/**" for o in sorted(others) if o != tag):
        r = f"Read({d})"
        if r not in deny:
            deny.append(r)
    s["permissions"]["deny"] = deny
    return s


def pick_run(runs):
    """A unit's research run: its first run that passed the audit (a rerun exists only when every earlier run was
    excluded), else None. runs: [(made, tag, excluded)]."""
    for made, tag, excluded in sorted(runs):
        if not excluded:
            return tag
    return None


def again_refusal(unit_runs):
    """Why a unit may not get a fresh research folder, or None: only when it has runs, all excluded, and at most one
    rerun (two runs in all). unit_runs: [excluded flags]."""
    if not unit_runs:
        return "it has no run yet"
    if not all(unit_runs):
        return "it has a run that passed"
    if len(unit_runs) >= 2:
        return "it was rerun once already"
    return None


def names_in(text, words=TITLE_NAMES):
    """The V-real titles and bands a text names (whole words, case-insensitive): the scrubbed plugin must name none."""
    return sorted({w for w in words if re.search(rf"\b{w}\b", text, re.I)})


def page_groups(cands):
    """{cand: (select, settings)} -> groups of candidates that play the same preset, in candidate order (identical
    presets share a letter)."""
    groups = []
    for c, v in cands.items():
        g = next((g for g in groups if cands[g[0]] == v), None)
        if g is None:
            groups.append([c])
        else:
            g.append(c)
    return [tuple(g) for g in groups]


def page_draw(units_, seed=PAGE_SEED, repeats=2, gap=4, letters="ABCD"):
    """The page's items: every unit once and `repeats` of them twice, in a seeded order, a repeat at least `gap` items
    after its first hearing; each item's preset groups on seeded letters, and in a repeat every group on another letter
    (when it has two or more). units_: [{slug, groups: [tuple of cands], ...}] -> [{**unit, id, n, letters: {letter:
    group}, repeat_of}]."""
    rng = random.Random(seed)
    by = {u["slug"]: u for u in units_}
    twice = rng.sample(sorted(by), repeats)
    seq = sorted(by) + twice
    while True:
        rng.shuffle(seq)
        if all(seq.index(t) + gap <= len(seq) - 1 - seq[::-1].index(t) for t in twice):
            break
    items, first = [], {}
    for n, slug in enumerate(seq, 1):
        gs = list(by[slug]["groups"])
        order = rng.sample(gs, len(gs))
        if slug in first and len(gs) > 1:
            before = first[slug]["letters"]
            for _ in range(1000):
                if all(before[letters[i]] != g for i, g in enumerate(order)):
                    break
                order = rng.sample(gs, len(gs))
            else:
                raise SystemExit(f"{slug}: no letter rotation found")
        it = {**by[slug], "id": f"i{n}", "n": n, "letters": {letters[i]: g for i, g in enumerate(order)},
              "repeat_of": first[slug]["id"] if slug in first else None}
        items.append(it)
        first.setdefault(slug, it)
    return items


def unblind(item, ans):
    """One item's answer -> {cand: {rank, close}} (ties allowed; a shared letter gives its candidates one rank), or None
    unless every letter holds a rank from 1 to the item's letter count."""
    from learn import ear_vreal as E

    r, c = (ans or {}).get("rank") or {}, (ans or {}).get("close") or {}
    n = len(item["letters"])
    if any(r.get(k) not in range(1, n + 1) for k in item["letters"]):
        return None
    return {cand: {"rank": r[k], "close": E.CLOSE_VALUE.get(c.get(k))}
            for k, g in item["letters"].items() for cand in g}


def pref(heard, a, b):
    """a over b: 1 above, 0 below, 0.5 tied (or one preset)."""
    x, y = heard[a]["rank"], heard[b]["rank"]
    return 1.0 if x < y else 0.0 if x > y else 0.5


EAR_PAIRS = (("M", "R"), ("M", "C"), ("M", "L"), ("R", "C"), ("R", "L"), ("C", "L"))   # the first is read first


def ear_read(items, got, n_boot=20000, seed=BOOT_SEED):
    """The declared read (plan section 8). items: the key's (band, judge {cand: held distance}); got: {id: answer}.
    Per pair on first hearings with both candidates: the share of units with a above (a tie a half), its 90% band
    bootstrap (L0's), the closeness gap where both are rated, J0 on the same clips; the repeats."""
    from learn import ear_vreal as E

    heard = {it["id"]: unblind(it, got.get(it["id"])) for it in items}
    first = [it for it in items if it["repeat_of"] is None]
    rows = {}
    for a, b in EAR_PAIRS:
        cards = [it for it in first if heard[it["id"]] and a in heard[it["id"]] and b in heard[it["id"]]]
        if not cards:
            rows[f"{a} over {b}"] = None
            continue
        pr = [(it["band"], pref(heard[it["id"]], a, b)) for it in cards]
        lo, hi = E.boot(pr, n=n_boot, seed=seed)
        cl = [(it["band"], heard[it["id"]][a]["close"] - heard[it["id"]][b]["close"]) for it in cards
              if heard[it["id"]][a]["close"] is not None and heard[it["id"]][b]["close"] is not None]
        j0 = [(it["band"], math.log(it["judge"][a] / it["judge"][b])) for it in cards]
        share = E.band_mean(pr)
        rows[f"{a} over {b}"] = {
            "units": len(cards), "share": share, "lo90": lo, "hi90": hi,
            "above": sum(p == 1.0 for _, p in pr), "ties": sum(p == 0.5 for _, p in pr),
            "below": sum(p == 0.0 for _, p in pr),
            "reading": ("heard above, one listener" if lo > 0.5 else "heard below, one listener" if hi < 0.5
                        else "not known by ear"),
            "rank_gap": E.band_mean([(it["band"], heard[it["id"]][b]["rank"] - heard[it["id"]][a]["rank"])
                                     for it in cards]),
            "closeness_gap": E.band_mean(cl) if cl else None, "closeness_rated": len(cl),
            "j0_on_clips": E.band_mean(j0), "j0_agrees": sum((v < 0) == (p == 1.0) for (_, v), (_, p) in zip(j0, pr)
                                                             if p != 0.5)}
    reps = []
    for it in items:
        if it["repeat_of"] and heard[it["id"]] and heard[it["repeat_of"]]:
            h0, h1 = heard[it["repeat_of"]], heard[it["id"]]
            same = [pref(h0, a, b) == pref(h1, a, b) for a, b in EAR_PAIRS if a in h0 and b in h0]
            reps.append({"id": it["id"], "repeat_of": it["repeat_of"], "pairs_same": sum(same), "pairs": len(same),
                         "primary_same": pref(h0, "M", "R") == pref(h1, "M", "R")})
    return {"answered": sum(v is not None for v in heard.values()), "items": len(items),
            "first_answered": sum(heard[it["id"]] is not None for it in first), "rows": rows, "repeats": reps}


# --- paths and small I/O ----------------------------------------------------------------------------------------------

def ex_dir():
    return P.out_dir() / "exam"


def inputs_path():
    return ex_dir() / "inputs.json"


def research_dir():
    return ex_dir() / "research"


def chain_dir(arm, key):
    return ex_dir() / "chain" / arm / key


def answers_path(tag):
    return P.out_dir() / P.VREAL_DIR / "answers" / f"{tag}.json"


def judge_dir(tag):
    return P.out_dir() / P.VREAL_DIR / "judge" / tag


def clip_path(tag, slug, amp, hk):
    return ex_dir() / "clips" / f"{tag}__{slug}__{amp}__{'any' if hk == ANY else hk}.npy"


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main_py():
    return os.environ.get("NDSP_MAIN_PY") or sys.executable


def torch_py():
    return os.environ.get("NDSP_TORCH_PY") or str(P.DATA / "tools/demucs-venv/bin/python")


def child_env():
    return dict(os.environ, NDSP_MAIN_PY=main_py(), NDSP_TORCH_PY=torch_py())


def _gr():
    root = PLUGIN_ROOT / "research"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import generate_routing as GR

    return GR


def entry():
    return P.require(PHASE)


def load_inputs(hashed=True):
    """inputs.json, and (with `hashed`) its sha256 the one the ledger's phase_exam_inputs records."""
    p = inputs_path()
    if not p.exists():
        raise SystemExit(f"{p}: run `inputs` first")
    if hashed:
        want = (P.ledger_entry() or {}).get(PHASE_INPUTS) or {}
        if not isinstance(want, dict) or want.get("inputs_json") != sha_file(p):
            raise SystemExit(f"{p.name}'s sha256 is not recorded under the ledger's {PHASE_INPUTS}: record it first")
    return json.loads(p.read_text())


def load_research():
    """research.json: every unit with its model class (research's, or the label's where no run passed); at least one
    unit with R, else a stop for the user (plan, "When research fails")."""
    p = research_dir() / "research.json"
    if not p.exists():
        raise SystemExit(f"{p}: run research-collect first")
    r = json.loads(p.read_text())
    if set(r["units"]) != {u["key"] for u in units()} or any(v.get("cls_model") not in ("clean", "crunch")
                                                           for v in r["units"].values()):
        raise SystemExit("research.json does not give every unit a model class")
    if not any(not v.get("no_research") for v in r["units"].values()):
        raise SystemExit("no unit has R: stop for the user's decision")
    return r


def guard_files():
    """{name: path} of the guards' records the chain, the renders and the report need passed."""
    return {"guards_json": ex_dir() / "guards.json", "r1_repro_json": ex_dir() / "r1-repro.json"}


def require_guards():
    """Guards 2, 3, 4 and 7's first half (exam/guards.json, exam/r1-repro.json) must exist and pass. -> {name: sha256}."""
    out = {}
    for name, p in guard_files().items():
        if not p.exists():
            raise SystemExit(f"{p.name} is missing: run `guards` and `r1-repro` first")
        if json.loads(p.read_text()).get("passes") is not True:
            raise SystemExit(f"{p.name} did not pass: stop")
        out[name] = sha_file(p)
    return out


def chain_lock():
    """The chain's record of the research and inputs it ran on (written at its first start): a later change of either
    refuses the answers (fix 6)."""
    return ex_dir() / "chain" / "lock.json"


def crop_dir(slug, parts):
    from learn import arm_a_mega53 as A

    return A.f_part(slug)["crop"] if parts[slug]["kind"] == "stagef" else pathlib.Path(parts[slug]["crop"])


def judge_lag(slug, parts):
    from learn import arm_a_mega53 as A

    return int((A.f_part(slug) if parts[slug]["kind"] == "stagef" else parts[slug])["judge_lag"])


def group_ctx(menu, ms, parts, slug, amp):
    from learn import arm_a_mega53 as A
    from learn import trusted_data_t3 as T3

    return (A.group_ctx(menu, ms, "F", slug, amp) if parts[slug]["kind"] == "stagef"
            else T3.t3_group_ctx(menu, ms, parts[slug], amp))


def attrs_of(inp):
    """{unit key: {cls, density, centred, v10}} (every slug its unit's), from inputs.json."""
    v10 = set(P.vreal_ctx()[1]["vreal"]["v_real_10"])
    out = {}
    for u in units():
        r = inp["units"][u["key"]]
        out[u["key"]] = {"cls": u["cls"], "density": r["density"], "centred": r["centred"],
                         "v10": all(m in v10 for m in u["members"])}
    return out


# --- inputs (zero renders, zero separations) --------------------------------------------------------------------------

def db_of(x):
    import numpy as np

    return 10 * math.log10(float(np.mean(np.asarray(x, np.float64) ** 2)) + 1e-20)


def corr(a, b):
    import numpy as np

    n = min(len(a), len(b))
    return float(np.corrcoef(np.asarray(a[:n], np.float64), np.asarray(b[:n], np.float64))[0, 1])


def playing_in(crop):
    """`trusted_data.vreal_playing` for any crop folder (T3's included): the guitars playing in its window."""
    from learn import trusted_data as T
    from learn import verify_tracks as V

    rec, base, cpart, _, mix = V.crop_session(crop)

    def name(x):
        return pathlib.PurePosixPath(x).name

    base = pathlib.Path(base) / pathlib.PurePosixPath(cpart.get("di") or "x").parent
    names = sorted(f.name for f in base.glob("*.wav"))
    mix = [name(m) for m in mix]
    tdi = name(cpart.get("di") or next((d for d in rec.get("excluded_guitar_dis") or []
                                        if V.guitar_part_key(name(d)) == V.guitar_part_key(rec["part"])), rec["part"]))
    parts = T.session_guitar_parts(names, mix, tdi, [name(o) for o in rec.get("removed_own_amp_tracks") or []])
    start, dur = float(rec["excerpt_start_s"]), float(rec["excerpt_duration_s"])
    files = {}
    act = {t: T.section_activity(base / t, start, files=files, dur_s=dur) for ts in parts.values() for t in ts}
    n = T.playing_count(parts, act)
    return {"playing": n, "density": T.density(n), "playing_parts": T.playing_parts(parts, act)}


def session_di(crop):
    """The part's whole-session DI file (the catalogue's), from its crop's record."""
    from learn import verify_tracks as V

    rec, base, cpart, _, _ = V.crop_session(crop)
    p = pathlib.Path(base) / cpart["di"]
    if not p.exists():
        raise SystemExit(f"{crop.name}: its session DI {p.name} is missing")
    return p


def cmd_inputs(args):
    """The released mixes decoded to neutral-named float WAVs (each preview's sha256 equal to alignment.json's), each
    crop's place in its file (alignment.json's crop offset, re-checked on the decoded file; T3's crop checked here),
    each unit's span, the unity sums, and the truth-side strata (pan, level, guitars playing) -> exam/inputs.json."""
    import numpy as np
    import soundfile as sf

    from analysis import io
    from learn import confirm_run as CR
    from learn import mix_previews as MPV
    from learn import product_path as PP
    from learn import trusted_data as T

    entry()
    if inputs_path().exists() and (P.ledger_entry() or {}).get(PHASE_INPUTS, {}).get("inputs_json"):
        raise SystemExit("inputs.json is recorded in the ledger: the inputs are built once")
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    al = json.loads((MPV.IN / "alignment.json").read_text())
    od = ex_dir() / "inputs"
    od.mkdir(parents=True, exist_ok=True)
    recs = {s: json.loads((crop_dir(s, parts) / "record.json").read_text()) for s in PR.VREAL}
    songs = sorted({r["song"] for r in recs.values()})
    order = songs[:]
    random.Random(f"{SEED}|names").shuffle(order)
    out = {"plan": PLAN, "ledger": f"{P.LEDGER_ID} {PHASE_INPUTS}", "songs": {}, "units": {}, "unity": {}}
    song_ctx = {}
    for song in songs:
        kind = "remix_mastered" if song == "Signs" else "preview_mastered"
        e = al[song][kind]
        src = MPV.IN / e["file"]
        if sha_file(src) != e["sha256"]:
            raise SystemExit(f"{src.name}: sha256 differs from alignment.json's")
        dst = od / f"mix-{order.index(song) + 1:02d}.wav"
        x, sr = sf.read(str(src), dtype="float32", always_2d=True)
        if not dst.exists():
            sf.write(str(dst), x, sr, subtype="FLOAT")
        y48 = io.load(dst).mono().astype(np.float64)
        srecs, folder = MPV.song_records(song)
        union, names, _ = MPV.unity_sum(srecs, folder)
        msp = [s for s in e["matched_spans"]]
        out["songs"][song] = {"file": str(dst), "sha256": sha_file(dst), "source_file": e["file"],
                              "source_sha256": e["sha256"], "kind": kind, "source_rate": int(sr),
                              "channels": int(x.shape[1]), "duration_s": len(x) / sr, "peak": float(np.abs(x).max())}
        song_ctx[song] = (dst, y48, union, msp, folder, len(x) / sr)
    unity_files = {}
    for u in units():
        first = u["members"][0]
        rec = recs[first]
        song = rec["song"]
        dst, y48, union, msp, folder, dur = song_ctx[song]
        e = al[song][out["songs"][song]["kind"]]
        crops, spans = {}, {}
        for slug in u["members"]:
            r = recs[slug]
            a, b = int(r["excerpt_start_frame"]), int(r["excerpt_end_frame"])
            crop = crop_dir(slug, parts)
            _, whole = MPV.covered(a, b, msp)
            if whole is None:
                raise SystemExit(f"{slug}: its crop is not inside one matched span; the plan drops it from the "
                                 "released-mix arms (decide before going on)")
            off = MPV.offset_at(whole, (a + b) // 2 - whole["offset_samples"])
            chk = MPV.crop_check(union, y48, a, b, off)
            ok = bool(chk and abs(chk["deviation_samples"]) <= MPV.CROP_OK_DEV and chk["peak_sd"] >= MPV.CROP_OK_SD)
            if not ok:
                raise SystemExit(f"{slug}: the crop check fails on the released mix ({chk}); the plan drops it from "
                                 "the released-mix arms (decide before going on)")
            stored = e["crops"].get(slug) or {}
            same = stored.get("crop_s") == [round(a / 48000, 2), round(b / 48000, 2)]   # T3's crop: another window
            if same:                                   # stage F's: the stored check must reproduce on the decoded file
                sc = stored.get("crop_gcc_check") or {}
                if (not stored.get("covered") or chk["deviation_samples"] != sc.get("deviation_samples")
                        or abs(chk["peak_sd"] - sc["peak_sd"]) > CROP_SD_TOL
                        or abs(chk["r_at_offset"] - sc["r_at_offset"]) > CROP_R_TOL
                        or off + chk["deviation_samples"] != stored["crop_offset_samples"]):
                    raise SystemExit(f"{slug}: the decoded file's crop check {chk} is not alignment.json's {sc}")
            coff = off + chk["deviation_samples"]
            cu = corr(union[a:b], CR.mono(crop / "mix.wav"))
            if cu < MATCH_R:
                raise SystemExit(f"{slug}: the session's unity sum and the crop's mix.wav correlate {cu:.5f}")
            crops[slug] = {"session_s": [a / 48000, b / 48000], "frames": [a, b], "offset_samples": coff,
                           "file_s": [(a - coff) / 48000, (b - coff) / 48000], "check": chk,
                           "in_alignment": same, "union_vs_crop_mix_r": cu}
            spans[slug] = whole
        offs = {c["offset_samples"] for c in crops.values()}
        if len(offs) != 1 or len({c["frames"][0] for c in crops.values()}) != 1:
            raise SystemExit(f"{u['key']}: its members sit at other offsets or crops")
        coff = offs.pop()
        a, b = crops[first]["frames"]
        span_main = spans[first]
        dis = {}
        for slug in u["members"]:
            crop = crop_dir(slug, parts)
            d = io.load(session_di(crop)).mono().astype(np.float64)
            r_ = corr(d[a:b], CR.mono(crop / "di.wav"))
            if r_ < MATCH_R:
                raise SystemExit(f"{slug}: the session DI and the crop's di.wav correlate {r_:.5f}")
            dis[slug] = (d, db_of(d[a:b]), r_)
        off_s = coff / 48000
        lo = max(span_main["session_start_s"], off_s + EDGE_S)
        hi = min(span_main["session_end_s"], off_s + dur - EDGE_S)

        def ok_at(t0, t1, dis=dis):
            i0, i1 = int(round(t0 * 48000)), int(round(t1 * 48000))
            return all(db_of(d[i0:i1]) >= c - SPAN_DB for d, c, _ in dis.values())

        sp = span_rule((a / 48000, b / 48000), lo, hi, ok_at)
        names = tuple(sorted(rec["included_mix_tracks"]))
        if any(tuple(sorted(recs[m]["included_mix_tracks"])) != names for m in u["members"]):
            raise SystemExit(f"{u['key']}: its members' mix tracks differ")
        uk = hashlib.sha256(json.dumps([song, names]).encode()).hexdigest()[:12]
        if uk not in unity_files:
            mix, nm, rates = MPV.unity_sum({first: {"record": rec}}, folder)
            p = od / f"unity-{len(unity_files) + 1:02d}.wav"
            if not p.exists():
                sf.write(str(p), mix.astype(np.float32), 48000, subtype="FLOAT")
            unity_files[uk] = {"file": str(p), "sha256": sha_file(p), "tracks": len(nm), "rates": rates,
                               "duration_s": len(mix) / 48000, "song": song}
        truth = {}
        for slug in u["members"]:
            crop = crop_dir(slug, parts)
            st = PP.load_stereo(str(dst), 48000, crops[slug]["file_s"][0], 10.0)
            fit = fit_pan(CR.mono(crop / "reference.wav"), st[:, 0], st[:, 1])
            if parts[slug]["kind"] == "stagef":
                pl = playing_in(crop)
                ref_pl = T.vreal_playing(slug)
                if pl["playing"] != ref_pl["playing"]:
                    raise SystemExit(f"{slug}: playing_in {pl['playing']} is not vreal_playing's {ref_pl['playing']}")
            else:
                pl = playing_in(crop)
            truth[slug] = {**fit, "centred": centred(fit["p"]), **pl, "di_crop_r": dis[slug][2],
                           "di_crop_db": dis[slug][1]}
        out["units"][u["key"]] = {
            "members": u["members"], "band": u["band"], "cls": u["cls"], "song": song, "artist": u["band"],
            "mix": out["songs"][song]["file"], "crops": crops, "offset_samples": coff,
            "span": {"session_s": sp["span"], "file_s": [sp["span"][0] - off_s, sp["span"][1] - off_s],
                     "before": sp["before"], "after": sp["after"], "stopped": sp["stopped"], "allowed_session_s": [lo, hi]},
            "unity": uk, "truth": truth,
            "centred": all(truth[m]["centred"] for m in u["members"]),
            "density": truth[first]["density"]}
    out["unity"] = unity_files
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(inputs_path(), out)
    rec = {"inputs_json": sha_file(inputs_path()),
           "units": {k: {"mix_sha256": out["songs"][v["song"]]["sha256"], "unity_sha256": unity_files[v["unity"]]["sha256"],
                         "span_file_s": [round(x, 3) for x in v["span"]["file_s"]],
                         "span_session_s": [round(x, 3) for x in v["span"]["session_s"]]}
                     for k, v in out["units"].items()}}
    for k, v in out["units"].items():
        t = v["truth"][v["members"][0]]
        print(f"{k:<52} span {v['span']['file_s'][0]:7.2f}-{v['span']['file_s'][1]:7.2f} s ({v['span']['before']}+10+"
              f"{v['span']['after']}) pan {t['p']:+.2f} r2 {t['r2']:.2f} level {t['target_db']:+.1f} dB playing "
              f"{t['playing']} {'centred' if v['centred'] else 'off-centre'}")
    print(f"record in the ledger's {P.LEDGER_ID} entry before any separation: \"{PHASE_INPUTS}\": "
          + json.dumps(rec, indent=1))
    print("EXAM INPUTS DONE")


# --- guards (zero renders) and the R1 reproduction (12 renders) -------------------------------------------------------

def c3r_sources(name="C3r-all"):
    """Every training input of the adopted pair (`pipeline_fix.dfix_training_sources`' rule widened to C3r's sets):
    its plugin and held rows (W's), every real unit of BKS, GOAT, cap1, n12 and the panel (`full_controls_c3r.state`'s
    entries; a capture unit by its DI's band, item and session), each real unit's DFIX_K backings by its stored inputs,
    and every backing-pool entry. -> (sources [(what, band, [names])], counts)."""
    import numpy as np

    from learn import cc_build as CB
    from learn import full_controls_c3r as C3R

    e = P.ledger_entry() or {}
    croot, kept, rend, sp, dropped = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    inv = CB.cc_inventory()
    recs = [json.loads((P.out_dir() / "runs" / f"{name}-{sd}.json").read_text()) for sd in P.SEEDS]
    by_sec, by_sd = {}, {}
    for x in kept.values():
        by_sec.setdefault(x["section"], x)
    for r_ in inv.values():
        if r_.get("session_dir"):
            by_sd.setdefault(r_["session_dir"], r_)

    def of_section(sec):
        x = by_sec.get(sec)
        names = [pathlib.Path(P.session_of(sec)).name]
        return (None, names) if x is None else (x["band"], names + [pathlib.Path(x["session_dir"]).name,
                                                                    inv[x["di"]].get("song")])
    src, cnt = [], {"plugin_rows": 0, "real_units": {}, "unit_backings": 0, "pool_entries": 0, "stock_dis": 0}
    ids = sorted({i for r_ in recs for i in r_["train_ids"] + r_["held_ids"] if i < P.REAL_ROW0})
    for i in ids:
        src.append((f"plugin row {i}", *of_section(kept[i]["section"])))
        cnt["plugin_rows"] += 1
    used = set(recs[0]["dfix"]["target_lufs"])
    if any(set(r_["dfix"]["target_lufs"]) != used for r_ in recs):
        raise SystemExit(f"{name}: the seeds' real units differ")
    st = C3R.state()
    ents = {x["unit"]: x for x in st["entries"]}
    pool = json.loads(P.wide_pool_path().read_text())["entries"]
    by_id = {x["id"]: x for x in pool}

    def of_entry(x):
        if x["kind"] == "training":
            return of_section(x["id"])
        r_ = by_sd.get(x["sd"]) or {}
        return r_.get("band"), [x["session"], r_.get("song")]
    for u in sorted(used):
        if u not in ents:
            raise SystemExit(f"{name}: real unit {u} is in no C3r entry")
        s = ents[u]["set"]
        prt = st["units"][s][u]
        cnt["real_units"][s] = cnt["real_units"].get(s, 0) + 1
        if s == "bks":
            band, names = prt["band"], [pathlib.Path(P.session_of(prt["section"])).name, pathlib.Path(prt["sd"]).name,
                                        inv.get(prt["di"], {}).get("song")]
        elif s == "goat":
            band, names = prt["band"], [prt.get("item")]
        elif s in ("cap1", "n12"):
            di = str(prt.get("di") or "")
            band = prt.get("player") or prt.get("band")
            names = [prt.get("item"), prt.get("name"), pathlib.PurePosixPath(di).parent.name, di]
        else:
            band, names = prt["band"], [prt.get("di"), pathlib.Path(str(prt.get("di_file") or "")).parent.name,
                                        pathlib.Path(str(prt.get("amp_file") or "")).name]
        src.append((f"real unit {u} ({s})", band, [n for n in names if n]))
        for v in range(P.DFIX_K):
            p = P.dfix_input_path(u, v)
            if not p.exists():
                raise SystemExit(f"{u} v{v}: no stored input")
            bid = str(np.load(p)["backing"])
            if bid in by_id:
                src.append((f"{u} v{v} backing {bid}", *of_entry(by_id[bid])))
            elif bid == prt.get("section"):
                src.append((f"{u} v{v} own backing", *of_section(bid)))
            else:
                raise SystemExit(f"{u} v{v}: backing {bid} is neither a pool entry nor its own section")
            cnt["unit_backings"] += 1
    for x in pool:
        src.append((f"pool entry {x['id']}", *of_entry(x)))
        cnt["pool_entries"] += 1
    from learn import amp_di_compare as A1

    n12 = st["units"].get("n12") or {}
    for cls, stock in json.loads((A1.a1_dir() / "plan.json").read_text())["stock"].items():
        for s in stock:                                # the amp pick's four stock DIs (A1's), by their sessions
            di = str(s["di"])
            band = (n12.get(s.get("unit")) or {}).get("player") or (inv.get(di) or {}).get("band") \
                or pathlib.PurePosixPath(di).parent.name
            src.append((f"stock DI {cls} {di}", band, [pathlib.PurePosixPath(di).parent.name, di,
                                                       (inv.get(di) or {}).get("song")]))
            cnt["stock_dis"] += 1
    return src, cnt, inv


def c3r_leak_guard(name=ADOPTED_BASE):
    """No V-real band or song (`vreal_songs`) in any training input of the adopted pair, nor in the amp pick's stock DIs;
    refuses on any."""
    a = json.loads((P.out_dir() / "adopted-model.json").read_text())
    if a["model"]["base"] != name:
        raise SystemExit(f"adopted-model.json's base is {a['model']['base']}, not {name}")
    src, cnt, inv = c3r_sources(name)
    songs = P.vreal_songs(inv)
    bad = P.leaks_of([(w, b, [n for n in ns if n]) for w, b, ns in src], P.VREAL_BANDS, songs)
    nameless = [w for w, b, ns in src if b is None]
    if bad:
        raise SystemExit(f"V-real in {name}'s training inputs ({len(bad)}): {bad[:20]}")
    return {**cnt, "sources": len(src), "vreal_bands": sorted(P.VREAL_BANDS), "vreal_song_keys": sorted(songs),
            "no_band": len(nameless)}


def adopted_hashes():
    """The adopted pair's checkpoints hash to their run records and to adopted-model.json (what `_adopted` checks)."""
    a = json.loads((P.out_dir() / "adopted-model.json").read_text())
    out = {}
    for sd in P.SEEDS:
        rec = json.loads((P.out_dir() / "runs" / f"{a['model']['base']}-{sd}.json").read_text())
        f = P.out_dir() / "runs" / rec["models"]["best"]
        got = sha_file(f)
        if not (got == rec["model_sha256"]["best"] == a["model"]["sha256"][str(sd)]["best"]):
            raise SystemExit(f"{f.name}: sha256 {got[:12]} is not its record's or adopted-model.json's")
        out[str(sd)] = got
    if not str(a.get("answer_hold", "")).startswith("C3-cabS"):
        raise SystemExit("adopted-model.json names another hold than C3-cabS")
    return {"base": a["model"]["base"], "sha256": out, "hold": a["answer_hold"]}


def stored_judge(tag):
    d = judge_dir(tag)
    return {f"{r['slug']}|{r['amp']}": r for r in (json.loads(p.read_text()) for p in d.glob("*.json"))}


def cmd_guards(_args):
    """Plan section 6's guards that need no judge render: 2 (the leakage guard on C3r-all), 3 (the adopted pair's
    hashes), 7's first half (S's positive control on the stored S renders). Each a stop. -> exam/guards.json."""
    entry()
    out = {"leakage": c3r_leak_guard(), "adopted": adopted_hashes()}
    sj = {k: r["judge"] for k, r in stored_judge("S").items()}
    pc = P.s_positive_control(sj)
    if not pc["passes"] or pc["n"] != P.S_CONTROL_N:
        raise SystemExit(f"S's positive control fails: {pc}")
    out["s_positive_control"] = pc
    out["passes"] = True                                # every guard above refuses on a failure
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(ex_dir() / "guards.json", out)
    print(json.dumps({k: (v if k != "leakage" else {x: y for x, y in v.items() if x != "vreal_song_keys"})
                      for k, v in out.items()}, indent=1))
    print("EXAM GUARDS DONE")


def run_model_preset(argv, log, env=None):
    """scripts/model_preset.py, as the product calls it, output appended to `log`. -> (exit code, seconds)."""
    t = time.time()
    with open(log, "a") as fh:
        fh.write(f"\n$ {' '.join(argv)}\n")
        fh.flush()
        done = subprocess.run(argv, cwd=PLUGIN_ROOT, stdout=fh, stderr=subprocess.STDOUT, env=env or child_env())
    return done.returncode, round(time.time() - t, 1)


R1_SONG = "cut-it-out"
REPRO_TOL = 1e-9                      # the stem features and the pick's distances: equal to float precision


def cmd_r1_repro(_args):
    """Plan guard 4, as the rules allow: the stored R1 run's window (its window.json and window.npz, R1's own files; the
    song's audio is not read) through the exam's wrapper of `scripts/model_preset.py` again: answers, the 12 stock-DI
    renders and the pick must equal r1/cut-it-out/model's. -> exam/r1-repro.json."""
    from packs.loader import load_pack

    from learn import r1_ear as R1E

    entry()
    src = P.out_dir() / "r1" / R1_SONG
    w = ex_dir() / "r1-repro" / "work"
    w.mkdir(parents=True, exist_ok=True)
    if sha_file(src / "window.json") != sha_file(src / "model" / "window.json"):
        raise SystemExit("the R1 run's window.json is not its model run's")
    for f in ("window.json", "window.npz"):
        if not (w / f).exists():
            shutil.copy2(src / f, w / f)
    win = json.loads((w / "window.json").read_text())
    ans0 = json.loads((src / "model" / "answers.json").read_text())
    argv = [main_py(), str(PLUGIN_ROOT / "scripts" / "model_preset.py"), "--song", win["song"], "--cls", ans0["cls"],
            "--part", str(win["part_s"][0]), str(win["part_s"][1]), "--part-from", win["part_from"],
            "--work", str(w), "--out", str(w / "model.xml"), "--force"]
    rc, sec = run_model_preset(argv, ex_dir() / "r1-repro" / "run.log")
    if rc:
        raise SystemExit(f"the wrapper failed ({rc}); see {ex_dir() / 'r1-repro' / 'run.log'}")
    a1, a0 = json.loads((w / "answers.json").read_text()), ans0
    r1, r0 = (json.loads((d / "renders.json").read_text()) for d in (w, src / "model"))
    p1, p0 = (json.loads((d / "preset.json").read_text()) for d in (w, src / "model"))
    pack = load_pack("morgan")
    x1, x0 = R1E.parse_preset(w / "model.xml", pack), R1E.parse_preset(src / "model" / "model.xml", pack)
    feat = max(abs(x - y) for x, y in zip(a1["stem_feat"], a0["stem_feat"]))
    out = {"song": R1_SONG, "seconds": sec,
           "answers_equal": P.answers_sha(a1["answers"]) == P.answers_sha(a0["answers"]),
           "gain_db": [a1["gain_db"], a0["gain_db"]], "stem_feat_max_abs_diff": feat,
           "render_lufs_equal": r1["lufs"] == r0["lufs"],
           "render_lufs_max_abs_diff": max(abs(x - y) for a in r1["lufs"] for x, y in zip(r1["lufs"][a], r0["lufs"][a])),
           "pick": [p1["amp"], p0["amp"]], "settings_equal": p1["settings"] == p0["settings"],
           "distances_max_abs_diff": max(abs(p1["distances"][a] - p0["distances"][a]) for a in AMPS),
           "output_gain": [p1["output_gain"], p0["output_gain"]],
           "preset_file_values_equal": R1E.same_preset(x1, x0)}
    out["passes"] = bool(out["answers_equal"] and out["pick"][0] == out["pick"][1] and out["settings_equal"]
                         and out["render_lufs_equal"] and out["preset_file_values_equal"]
                         and len(a1["stem_feat"]) == len(a0["stem_feat"]) and feat <= REPRO_TOL
                         and out["distances_max_abs_diff"] <= REPRO_TOL and a1["gain_db"] == a0["gain_db"])
    P.save(ex_dir() / "r1-repro.json", out)
    print(json.dumps(out, indent=1))
    if not out["passes"]:
        raise SystemExit("the R1 reproduction differs: stop")
    print("EXAM R1-REPRO DONE")


# --- research: blinded headless generate runs ------------------------------------------------------------------------

def research_map():
    p = research_dir() / "map.json"
    return json.loads(p.read_text()) if p.exists() else {"plan": PLAN, "runs": {}}


def check_inputs_files(inp):
    """The decoded mixes and unity sums still hash to inputs.json's (and so to the ledger's record)."""
    for song, s in inp["songs"].items():
        if sha_file(s["file"]) != s["sha256"]:
            raise SystemExit(f"{song}: the decoded mix changed since inputs.json")
    for k, u in inp["unity"].items():
        if sha_file(u["file"]) != u["sha256"]:
            raise SystemExit(f"unity sum {k}: changed since inputs.json")


def build_root():
    """The fresh research root (WORK): the routing study's venv copied in whole (no download), the scrubbed plugin (the
    routing study's parts at this checkout's HEAD), checked to name no V-real title or band. -> {commit, version, ...}."""
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PLUGIN_ROOT, capture_output=True, text=True,
                            check=True).stdout.strip()
    WORK.mkdir(exist_ok=True)
    extra = sorted(p.name for p in WORK.iterdir() if p.name not in ("venv", "plugin", "runs", "settings"))
    if extra:
        raise SystemExit(f"{WORK} holds more than the venv, the plugin, the settings and the runs: {extra}")
    if not VENV.exists():
        subprocess.run(["cp", "-a", str(OLD_WORK / "venv"), str(VENV)], check=True)
    chk = subprocess.run([str(VENV / "bin" / "python"), "-c", "import sys, numpy, scipy, soundfile; print(sys.prefix)"],
                         capture_output=True, text=True)
    if chk.returncode or os.path.normpath(chk.stdout.strip()) != os.path.normpath(str(VENV)):
        raise SystemExit(f"the copied venv does not run as itself: {chk.stdout.strip()} {chk.stderr.strip()[-200:]}")
    if not PLUGIN.exists():
        PLUGIN.mkdir(parents=True)
        arc = subprocess.run(["git", "archive", commit, *PLUGIN_PARTS], cwd=PLUGIN_ROOT, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(PLUGIN)], input=arc.stdout, check=True)
    hits, n = {}, 0
    for f in PLUGIN.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".md", ".json", ".py", ".txt", ".toml", ".yaml", ".yml", ".xml", ".csv",
                                                ".html", ".js", ".sh", ""):
            n += 1
            found = names_in(f.read_text(errors="ignore"))
            if found:
                hits[str(f.relative_to(PLUGIN))] = found
    if hits:
        raise SystemExit(f"the scrubbed plugin names V-real titles or bands: {hits}")
    version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"]
    return {"commit": commit, "version": version, "files_checked": n, "path": str(PLUGIN), "venv": str(VENV),
            "venv_prefix": chk.stdout.strip()}


def cmd_research_prepare(args):
    """One neutral run folder per unit (RUNS/<tag>: the whole song as song-NN.flac, rewritten with no metadata and
    clipped to +-1 for the copy only; the prompt; an empty data folder) in the fresh root. `--again KEY` adds one fresh
    folder for a unit whose runs were all excluded, once (plan, "When research fails"). The map from tag to unit stays
    in the data root, outside the agents' reach."""
    import numpy as np
    import soundfile as sf

    GR = _gr()
    entry()
    inp = load_inputs()
    check_inputs_files(inp)
    m = research_map()
    if "plugin" not in m:
        m["plugin"] = build_root()
    have = {r["unit"] for r in m["runs"].values()}
    if args.again:
        col = research_dir() / "research.json"
        done = json.loads(col.read_text())["runs"] if col.exists() else {}
        for k in args.again:
            mine = [t for t, r in m["runs"].items() if r["unit"] == k]
            if any(t not in done for t in mine):
                raise SystemExit(f"--again {k}: collect its runs first (research-collect)")
            why = again_refusal([done[t]["excluded"] for t in mine])
            if why:
                raise SystemExit(f"--again {k}: refused, {why}")
        todo = [u for u in units() if u["key"] in args.again]
        if len(todo) != len(set(args.again)):
            raise SystemExit(f"--again: unknown units {set(args.again) - {u['key'] for u in todo}}")
    else:
        todo = [u for u in units() if u["key"] not in have]
    rng = random.Random(f"{SEED}|research|{len(m['runs'])}")
    order = todo[:]
    rng.shuffle(order)
    taken = {p.name for p in RUNS.glob("*")} if RUNS.exists() else set()
    for u in order:
        while True:
            tag = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(5))
            if tag not in taken and tag not in m["runs"]:
                break
        nn = f"{len(m['runs']) + 1:02d}"
        r = inp["units"][u["key"]]
        folder = RUNS / tag
        (folder / "out").mkdir(parents=True, exist_ok=False)
        (folder / "data").mkdir()
        x, sr = sf.read(r["mix"], dtype="float32", always_2d=True)
        audio = f"song-{nn}.flac"
        sf.write(str(folder / audio), np.clip(x, -1.0, 1.0 - 2.0 ** -23), sr, subtype="PCM_24")
        a, b = r["span"]["file_s"]
        prompt = PROMPT.format(song=r["song"], artist=r["artist"], audio=audio, start=GR._clock(a), end=GR._clock(b),
                               python=VENV / "bin" / "python", data=folder / "data")
        (folder / "prompt.txt").write_text(prompt)
        m["runs"][tag] = {"unit": u["key"], "nn": nn, "span_file_s": [a, b], "audio_sha256": sha_file(folder / audio),
                          "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                          "made": time.strftime("%Y-%m-%d %H:%M:%S"), "again": bool(args.again)}
        print(f"{tag} {nn}: prepared ({a:.1f}-{b:.1f} s)")
    P.save(research_dir() / "map.json", m)
    print(f"EXAM RESEARCH-PREPARE DONE: {len(order)} folders under {RUNS}; plugin {m['plugin']['version']}")


def claude_run(folder, prompt, log, settings, resume=None):
    """The routing re-check's headless call (`generate_routing._claude`: its model, tools and flags) on this root: the
    run's own settings file, the plugin and the venv."""
    GR = _gr()
    argv = ["claude", "-p", prompt, "--model", GR.RECHECK_MODEL, "--settings", str(settings), "--setting-sources", "",
            "--plugin-dir", str(PLUGIN), "--add-dir", str(PLUGIN), "--add-dir", str(VENV),
            "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Skill",
            "--disallowedTools", "SendMessage,ListAgents,Task,Agent,Workflow,"
            "Artifact,ArtifactComments,ArtifactData,CronCreate,RemoteTrigger",
            "--permission-mode", "acceptEdits", "--output-format", "stream-json", "--verbose"]
    if resume:
        argv += ["--resume", resume]
    return subprocess.run(argv, cwd=folder, stdout=log, stderr=subprocess.STDOUT, timeout=3600)


def cmd_research_route(args):
    """Each prepared folder through a fresh sandboxed `claude -p` with the scrubbed plugin; its settings deny the data
    root, the repository, the session transcripts, the earlier routing runs and every other run's folder; a run with no
    result.json is asked once more with the re-check's non-answer. Wall time recorded."""
    from concurrent.futures import ThreadPoolExecutor

    GR = _gr()
    entry()
    m = research_map()
    todo = sorted(t for t in m["runs"] if not (RUNS / t / "transcript.jsonl").exists())
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    for tag in todo:
        P.save(SETTINGS_DIR / f"{tag}.json", run_settings(tag, list(m["runs"]), GR.SETTINGS))

    def one(tag):
        folder, st = RUNS / tag, SETTINGS_DIR / f"{tag}.json"
        t0 = time.time()
        with open(folder / "transcript.jsonl", "w") as log:
            claude_run(folder, (folder / "prompt.txt").read_text(), log, st)
        asked = False
        if not (folder / "result.json").exists():
            session, _, _ = GR._session_id(folder / "transcript.jsonl")
            if session:
                asked = True
                with open(folder / "transcript.jsonl", "a") as log:
                    claude_run(folder, GR.NON_ANSWER, log, st, resume=session)
        (folder / "asked.txt").write_text("yes\n" if asked else "no\n")
        (folder / "wall.json").write_text(json.dumps({"seconds": round(time.time() - t0, 1),
                                                      "end": time.strftime("%Y-%m-%d %H:%M:%S")}))
        return tag, ("result" if (folder / "result.json").exists() else "NO RESULT") + (", asked" if asked else "")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for tag, status in pool.map(one, todo):
            print(tag, status, flush=True)
    print(f"EXAM RESEARCH-ROUTE DONE: {len(todo)} runs")


def out_of(command, flag):
    import shlex

    argv = shlex.split(command)
    return argv[argv.index(flag) + 1] if flag in argv else None


def cmd_research_collect(_args):
    """Per run: the audit (guard 5, `audit_transcript`), the plugin version and model; R's class; its presets (R-wet the
    agent's file; R that file with its amp's dry recipe: its tonal edits kept, its time effects off, the routing
    study's tonal arm; R-route the agent's template made dry with the template's own amp; the agent's command replayed
    beside). A unit takes its first run that passed; a unit with none has no R (plan, "When research fails"). No unit
    with a pass: a stop for the user. -> research.json."""
    from packs.loader import load_pack

    from learn import local_objective as LO
    from learn import r1_ear as R1E

    GR = _gr()
    entry()
    m = research_map()
    pack = load_pack("morgan")
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    runs, by_unit = {}, {}
    for tag, r in sorted(m["runs"].items(), key=lambda kv: kv[1]["made"]):
        folder = RUNS / tag
        if not (folder / "transcript.jsonl").exists():
            raise SystemExit(f"{tag}: not run")
        au = audit_transcript((folder / "transcript.jsonl").read_text().splitlines(),
                              allowed=(folder, PLUGIN, VENV, *ALLOWED_ROOTS), runs_root=RUNS)
        session, plugins, model = au.pop("init")
        version = next((p.get("version") for p in plugins or [] if p.get("name") == "neuraldsp-preset-generator"), None)
        why = audit_why(au)
        if version != m["plugin"]["version"]:
            why.append(f"plugin version {version}")
        if model != GR.RECHECK_MODEL:
            why.append(f"model {model}")
        res = None
        try:
            res = json.loads((folder / "result.json").read_text())
        except (OSError, ValueError):
            why.append("no readable result.json")
        wall = json.loads((folder / "wall.json").read_text()) if (folder / "wall.json").exists() else {}
        row = {"unit": r["unit"], "made": r["made"], "audit": au, "version": version, "model": model, "why": why,
               "asked": (folder / "asked.txt").read_text().strip() == "yes" if (folder / "asked.txt").exists() else None,
               "seconds": wall.get("seconds"), "result": res}
        if not why:
            try:
                row.update(build_r(folder, res, r["unit"], pack, GR, R1E, LO))
            except (RuntimeError, SystemExit, ValueError, KeyError, TypeError) as e:
                why.append(f"presets: {e}")
        row["excluded"] = bool(why)
        runs[tag] = row
        by_unit.setdefault(r["unit"], []).append((r["made"], tag, row["excluded"]))
    out = {"plan": PLAN, "plugin": m["plugin"], "runs": runs, "units": {}}
    for u in units():
        tag = pick_run(by_unit.get(u["key"], []))
        if tag is None:
            n = len(by_unit.get(u["key"], []))
            out["units"][u["key"]] = {"cls": None, "cls_model": u["cls"], "label": u["cls"], "agrees": True,
                                      "no_research": True, "runs": n,
                                      "why": "no run passed" + ("" if n >= 2 else "; one rerun allowed (--again)")}
            continue
        row = runs[tag]
        sel_s, s_settings = ms[row["amp"]][u["cls"]] if row["cls_model"] == u["cls"] else (None, None)
        rt = row["presets"].get("route")
        out["units"][u["key"]] = {
            "tag": tag, "cls": row["cls"], "cls_model": row["cls_model"], "heavier": row["cls"] != row["cls_model"],
            "label": u["cls"], "agrees": row["cls_model"] == u["cls"], "amp": row["amp"], "template": row["template"],
            "presets": row["presets"], "route_error": row.get("route_error"), "no_research": False,
            "route_is_S": (None if s_settings is None or rt is None or rt["select"] != sel_s else
                           rt["settings"] == LO.sdict(s_settings))}
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(research_dir() / "research.json", out)
    for k, v in out["units"].items():
        print(f"{k:<52} {v.get('cls')!s:<8} label {v['label']:<7} amp {v.get('amp')} "
              f"{v['why'] if v.get('no_research') else ''}")
    print(f"excluded runs: {[(t, r['why']) for t, r in runs.items() if r['excluded']]}")
    secs = [r["seconds"] for r in runs.values() if r.get("seconds")]
    if secs:
        print(f"wall time per run: median {statistics.median(secs) / 60:.1f} min, {min(secs) / 60:.1f}-"
              f"{max(secs) / 60:.1f}")
    n_r = sum(not v["no_research"] for v in out["units"].values())
    print(f"units with R: {n_r} of {len(out['units'])}")
    if n_r == 0:
        raise SystemExit("no unit has a passing research run: the runner does not work here; stop for the user")
    print("EXAM RESEARCH-COLLECT DONE")


def build_r(folder, res, key, pack, GR, R1E, LO):
    """R-wet, R and R-route of one passed run (see `cmd_research_collect`). R-route failing leaves R and R-wet standing
    (`route_error`). -> {cls, cls_model, amp, template, presets, replay_equal, route_error}."""
    cmd = res["apply_command"]
    tpl = out_of(cmd, "--template")
    if tpl and not pathlib.Path(tpl).is_absolute():
        tpl = str((folder / tpl).resolve())
    wet = res.get("preset") or out_of(cmd, "--out")
    if not wet:
        raise ValueError("no preset named")
    wet = (folder / wet) if not pathlib.Path(wet).is_absolute() else pathlib.Path(wet)
    if not wet.exists() or folder.resolve() not in wet.resolve().parents:
        raise ValueError(f"the preset {wet} is not a file the run wrote")
    d = research_dir() / "presets" / key
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wet, d / "wet.xml")
    sel, _ = R1E.parse_preset(d / "wet.xml", pack)
    amp = SELECT_AMP[sel]
    if res.get("amp") and res["amp"] != amp:
        raise ValueError(f"result.json's amp {res['amp']} is not the preset's {amp}")
    GR._apply(["--template", str(d / "wet.xml"), "--recipe", f"dry/{amp}", "--strip-irs", "--out", str(d / "tonal.xml")],
              d)
    names, route_error, replay_equal = ["wet", "tonal"], None, None
    try:
        if not tpl or not pathlib.Path(tpl).exists():
            raise ValueError(f"the command's template {tpl!r} is missing")
        t_amp = SELECT_AMP[R1E.parse_preset(pathlib.Path(tpl), pack)[0]]
        GR._apply(["--template", tpl, "--recipe", f"dry/{t_amp}", "--strip-irs", "--out", str(d / "route.xml")], d)
        names.append("route")
        GR._replay(cmd, pathlib.Path(tpl), d / "replay.xml", folder)
        names.append("replay")
    except (RuntimeError, ValueError, KeyError) as e:
        route_error = str(e)
    presets = {}
    for name in names:
        s, ed = R1E.parse_preset(d / f"{name}.xml", pack)
        presets[name] = {"path": str(d / f"{name}.xml"), "sha256": sha_file(d / f"{name}.xml"), "select": s,
                         "settings": LO.sdict(ed)}
    if "replay" in presets:
        replay_equal = presets["replay"]["settings"] == presets["wet"]["settings"]
    cls = str(res.get("gain_class", "")).lower()
    return {"cls": cls, "cls_model": model_class(cls), "amp": amp, "template": tpl, "presets": presets,
            "replay_equal": replay_equal, "route_error": route_error}


# --- the chain (the model path's arms) --------------------------------------------------------------------------------

def mps_jobs(ps, own=()):
    """Other processes that may hold the MPS: any msst-venv python (a separation) and demucs-venv pythons that train or
    are told the MPS. ps: [(pid, command)]."""
    out = []
    for pid, cmd in ps:
        if pid in own or "python" not in cmd:
            continue
        if "msst-venv" in cmd or ("demucs-venv" in cmd and re.search(r"\btrain\b|train-ft|_train\b|--device mps", cmd)):
            out.append((pid, cmd[:160]))
    return out


def wait_mps(log=print):
    from learn import ks_extend as X

    t0, said = time.time(), 0.0
    while True:
        busy = mps_jobs(X._ps(), {os.getpid(), os.getppid()})
        if not busy:
            return round(time.time() - t0)
        if time.time() - said > 600:
            log(f"waiting for the MPS: {busy}")
            said = time.time()
        time.sleep(30)


def chain_argv(arm, u, inp, res, m_start=None):
    """The product's command for one arm on one unit (`scripts/model_preset.py`). M and M-lab: the span with
    `--part` (the selector); M-crop: `--start` at the crop; M-x and M-unity: `--start` at M's own window (`m_start`,
    in file time; M-unity's in session time), so each changes one stage."""
    r = inp["units"][u["key"]]
    w = chain_dir(arm, u["key"])
    cls = u["cls"] if arm == "Mlab" else res["units"][u["key"]]["cls_model"]
    song = inp["unity"][r["unity"]]["file"] if arm == "Munity" else r["mix"]
    argv = [main_py(), str(PLUGIN_ROOT / "scripts" / "model_preset.py"), "--song", song, "--cls", cls, "--work", str(w),
            "--out", str(w / "model.xml"), "--name", "exam", "--force"]
    if arm == "Mcrop":
        return argv + ["--start", f"{r['crops'][u['members'][0]]['file_s'][0]:.6f}"]
    if arm in ("Mx", "Munity"):
        if m_start is None:
            raise SystemExit(f"{arm} {u['key']}: needs M's window")
        s = m_start + (r["offset_samples"] / 48000 if arm == "Munity" else 0.0)
        return argv + ["--start", f"{s:.6f}"] + (["--version", "xlst_mdxc"] if arm == "Mx" else [])
    span = r["span"]["file_s"]
    return argv + ["--part", f"{span[0]:.6f}", f"{span[1]:.6f}", "--part-from", "the user"]


def needs_lab(u, res):
    return res["units"][u["key"]]["cls_model"] != u["cls"]


def cmd_chain(args):
    """Every chain arm on every unit, one run at a time, the MPS checked free before each separation: M, M-crop, M-unity,
    M-lab (where research's class is not the label's; M's window copied in, so only the class changes), M-x (CPU).
    A done run is kept. -> chain/<arm>/<unit>/, chain/log.json; the last line "EXAM CHAIN DONE"."""
    entry()
    require_guards()
    inp, res = load_inputs(), load_research()
    check_inputs_files(inp)
    lock = {"research_json": sha_file(research_dir() / "research.json"), "inputs_json": sha_file(inputs_path())}
    if chain_lock().exists():
        if json.loads(chain_lock().read_text())["hashes"] != lock:
            raise SystemExit("research.json or inputs.json changed since the chain started: stop")
    else:
        P.save(chain_lock(), {"hashes": lock, "start": time.strftime("%Y-%m-%d %H:%M:%S")})
    logp = ex_dir() / "chain" / "log.json"
    log = json.loads(logp.read_text()) if logp.exists() else {}
    arms = [a for a in CHAIN if not args.arms or a in args.arms.split(",")]
    failed = []
    for arm in arms:
        for u in units():
            if arm == "Mlab" and not needs_lab(u, res):
                continue
            w = chain_dir(arm, u["key"])
            if (w / "preset.json").exists():
                continue
            w.mkdir(parents=True, exist_ok=True)
            waited = 0
            if arm == "Mlab":
                m = chain_dir("M", u["key"])
                for f in ("window.json", "window.npz"):
                    if not (m / f).exists():
                        raise SystemExit(f"{u['key']}: M-lab needs M's {f}")
                    if not (w / f).exists():
                        shutil.copy2(m / f, w / f)
            else:
                waited = wait_mps(lambda s: print(s, flush=True))
            m_start = None
            if arm in ("Mx", "Munity"):
                mw = chain_dir("M", u["key"]) / "window.json"
                if not (chain_dir("M", u["key"]) / "preset.json").exists():
                    print(f"[{arm}] {u['key']}: M has no preset; skipped", flush=True)
                    failed.append(f"{arm}|{u['key']} (no M)")
                    continue
                m_start = float(json.loads(mw.read_text())["start_s"])
            print(f"[{arm}] {u['key']} start {time.strftime('%H:%M:%S')}", flush=True)
            rc, sec = run_model_preset(chain_argv(arm, u, inp, res, m_start), w / "run.log")
            log[f"{arm}|{u['key']}"] = {"rc": rc, "seconds": sec, "waited_mps_s": waited,
                                        "end": time.strftime("%Y-%m-%d %H:%M:%S")}
            P.save(logp, log)
            print(f"[{arm}] {u['key']} exit {rc} in {sec:.0f} s", flush=True)
            if rc:
                failed.append(f"{arm}|{u['key']}")
    print(f"EXAM CHAIN DONE: {len(log)} runs logged, failed {failed}", flush=True)


def cmd_cpick(_args):
    """C-pick: the model path's stock-DI pick on C's presets (Step 2's labels' centre): `product_path render` once per
    class the chain told the model (12 renders each), then `product_path pick` per unit with M's stem features and
    class. -> cpick/units/<unit>/preset.json."""
    entry()
    require_guards()
    inp, res = load_inputs(), load_research()
    check_lock()
    cen = load_centres()["EX-C"]
    classes = sorted({res["units"][u["key"]]["cls_model"] for u in units()})
    m0 = json.loads((chain_dir("M", units()[0]["key"]) / "answers.json").read_text())
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    for cls in classes:
        d = ex_dir() / "cpick" / f"class-{cls}"
        if (d / "renders.json").exists():
            continue
        d.mkdir(parents=True, exist_ok=True)
        ans = {a: {"select": cen[a][cls]["select"], "settings": cen[a][cls]["settings"], "amp_p": None} for a in AMPS}
        P.save(d / "answers.json", {"cls": cls, "gain_db": None, "model_lufs": m0["model_lufs"], "answers": ans,
                                    "stem_feat": [], "what": "C (ladder/centres.json centres.cen), for its renders",
                                    "centres_json": sha_file(P.out_dir() / CENTRES)})
        done = subprocess.run([main_py(), "-m", "learn.product_path", "render", str(d)], cwd=PLUGIN_ROOT, env=child_env())
        if done.returncode:
            raise SystemExit(f"C-pick's renders for {cls} failed")
    for u in units():
        d = ex_dir() / "cpick" / "units" / u["key"]
        if (d / "preset.json").exists():
            continue
        cls = res["units"][u["key"]]["cls_model"]
        t = ex_dir() / "cpick" / f"class-{cls}"
        mans = json.loads((chain_dir("M", u["key"]) / "answers.json").read_text())
        if mans["cls"] != cls or mans["model_lufs"] != m0["model_lufs"]:
            raise SystemExit(f"{u['key']}: M's class or model level is not C-pick's")
        d.mkdir(parents=True, exist_ok=True)
        a = json.loads((t / "answers.json").read_text())
        P.save(d / "answers.json", {**a, "stem_feat": mans["stem_feat"], "gain_db": mans["gain_db"]})
        for f in ("renders.json", "renders.npz"):
            shutil.copy2(t / f, d / f)
        done = subprocess.run([torch_py(), "-m", "learn.product_path", "pick", str(d)], cwd=PLUGIN_ROOT, env=child_env())
        if done.returncode:
            raise SystemExit(f"{u['key']}: C-pick's pick failed")
    print("EXAM C-PICK DONE")


# --- the answers files and the zero-render tables ---------------------------------------------------------------------

def load_centres():
    """Step 2's all-labels constants, checked to be the adopted pair's (its model_sha256 and C3-cabS hold).
    -> {"EX-C": cen, "EX-Cown": aconst}, each {amp: {cls: {select, settings}}}."""
    p = P.out_dir() / CENTRES
    if not p.exists():
        raise SystemExit(f"{p} does not exist yet: Step 2's stage 0 writes it; hand back")
    doc = json.loads(p.read_text())
    a = json.loads((P.out_dir() / "adopted-model.json").read_text())
    why = centres_refusal(doc, [a["model"]["sha256"][str(sd)]["best"] for sd in P.SEEDS])
    if why:
        raise SystemExit(why)
    return {t: centre_answers(doc, n) for t, n in CENTRE_NAMES.items()}


def check_lock():
    """research.json and inputs.json are the chain's (fix 6): refuses if either changed after the chain started."""
    if not chain_lock().exists():
        raise SystemExit("the chain has not started: no lock")
    want = json.loads(chain_lock().read_text())["hashes"]
    got = {"research_json": sha_file(research_dir() / "research.json"), "inputs_json": sha_file(inputs_path())}
    if want != got:
        raise SystemExit(f"research.json or inputs.json changed since the chain started ({want} vs {got}): stop")

def zt_label(slug, amp, search):
    return json.loads((P.DATA / f"learn/arm-a-mega53/F-perfect-sep/ZT/{slug}/{amp}/{search}.json").read_text())


def page_l_amp(slug, search):
    """L's amp on the page: the amp whose stored label scores best on the page's search half (its own objective)."""
    return min(AMPS, key=lambda a: zt_label(slug, a, search)["objective_best"])


def cmd_answers(_args):
    """Every arm's answers (zero renders) -> vreal/answers/EX-*.json, and the zero-render tables -> exam/tables.json.
    Refuses if research.json or inputs.json changed since the chain started, or if any chain run's or C-pick's class is
    not the one it should hold (research's model class; the label's for M-lab). Prints each file's sha256 (and the
    guards' records') for the ledger's phase_exam_answers (renders refuse without them)."""
    from learn import local_objective as LO

    e = entry()
    if (e.get(PHASE_ANSWERS) or {}).get("hashes"):
        raise SystemExit("the answers' hashes are in the ledger: answers are written once")
    gshas = require_guards()
    inp, res = load_inputs(), load_research()
    check_lock()
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    v10 = set(plan["vreal"]["v_real_10"])
    out = {t: {} for t in TAGS}
    meta = {t: {} for t in TAGS}
    model_cls, wrong = {}, []
    s_stored = json.loads(P.vreal_answers_path("S").read_text())["answers"]
    for u in units():
        k = u["key"]
        ru = res["units"][k]
        model_cls[k] = ru["cls_model"]
        for arm, tag in CHAIN_TAG.items():
            if arm == "Mlab" and not needs_lab(u, res):
                continue
            d = chain_dir(arm, k)
            if not (d / "preset.json").exists():
                raise SystemExit(f"{arm} {k}: no preset.json (the chain has not finished)")
            pr = json.loads((d / "preset.json").read_text())
            ans = json.loads((d / "answers.json").read_text())
            want = u["cls"] if arm == "Mlab" else ru["cls_model"]
            if pr["cls"] != want or ans["cls"] != want:
                wrong.append(f"{arm} {k}: class {pr['cls']}/{ans['cls']}, not {want}")
            for slug in u["members"]:
                out[tag][f"{slug}|{pr['amp']}"] = {ANY: {"select": pr["select"], "settings": pr["settings"]}}
            meta[tag][k] = {"preset_json": sha_file(d / "preset.json"), "answers_json": sha_file(d / "answers.json"),
                            "window_json": sha_file(d / "window.json"), "cls": pr["cls"]}
            if arm == "M":
                for slug in u["members"]:
                    for a in AMPS:
                        out["EX-M3"][f"{slug}|{a}"] = {ANY: {"select": ans["answers"][a]["select"],
                                                             "settings": ans["answers"][a]["settings"]}}
                    sel, S = ms[pr["amp"]][u["cls"]]
                    s_ans = s_stored[f"{slug}|{pr['amp']}"][ANY]
                    if P.answers_sha(s_ans) != P.answers_sha({"select": sel, "settings": LO.sdict(S)}):
                        raise SystemExit(f"{slug}: phase 4's stored S is not the live copy's")
                    out["EX-S"][f"{slug}|{pr['amp']}"] = {ANY: s_ans}
                    if ru["cls_model"] != u["cls"]:                # S of M's class on M's amp: the loudness row's
                        sel2, S2 = ms[pr["amp"]][ru["cls_model"]]
                        out["EX-Sm"][f"{slug}|{pr['amp']}"] = {ANY: {"select": sel2, "settings": LO.sdict(S2)}}
        if not ru.get("no_research"):
            for name, tag in (("tonal", "EX-R"), ("wet", "EX-Rwet"), ("route", "EX-Rroute")):
                p = ru["presets"].get(name)
                if p is None:                                  # R-route failed alone: R and R-wet stand
                    continue
                if sha_file(p["path"]) != p["sha256"]:
                    raise SystemExit(f"{k} {name}: the preset changed since research-collect")
                for slug in u["members"]:
                    out[tag][f"{slug}|{SELECT_AMP[p['select']]}"] = {ANY: {"select": p["select"],
                                                                           "settings": p["settings"]}}
        cp = ex_dir() / "cpick" / "units" / k / "preset.json"
        if not cp.exists():
            raise SystemExit(f"{k}: no C-pick preset (run c-pick)")
        pc = json.loads(cp.read_text())
        if pc["cls"] != ru["cls_model"]:
            wrong.append(f"C-pick {k}: class {pc['cls']}, not {ru['cls_model']}")
        meta["EX-Cpick"][k] = {"preset_json": sha_file(cp), "cls": pc["cls"]}
        for slug in u["members"]:
            out["EX-Cpick"][f"{slug}|{pc['amp']}"] = {ANY: {"select": pc["select"], "settings": pc["settings"]}}
    if wrong:
        raise SystemExit(f"classes paired wrongly: {wrong}")
    cen = load_centres()
    m_amp = {k.split("|")[0]: k.split("|")[1] for k in out["EX-M"]}
    for u in units():
        for slug in u["members"]:
            for tag in ("EX-C", "EX-Cown"):
                for a in AMPS:
                    out[tag][f"{slug}|{a}"] = {ANY: dict(cen[tag][a][u["cls"]])}
            if model_cls[u["key"]] != u["cls"]:
                a = m_amp[slug]
                for tag, base in (("EX-Cm", "EX-C"), ("EX-Cownm", "EX-Cown")):
                    out[tag][f"{slug}|{a}"] = {ANY: dict(cen[base][a][model_cls[u["key"]]])}
            if slug in v10:
                for a in AMPS:
                    sel, S = ms[a][u["cls"]]
                    for search in ("A", "B"):
                        best = zt_label(slug, a, search)["settings"]["best"]
                        if set(best) != set(LO.sdict(S)):
                            raise SystemExit(f"{slug} {a} {search}: the label's controls are not S's")
                        out["EX-L"].setdefault(f"{slug}|{a}", {})[search] = {"select": sel, "settings": best}
    shas = {}
    common = {"plan": PLAN, "ledger": f"{P.LEDGER_ID} {PHASE_ANSWERS}", "inputs_json": sha_file(inputs_path()),
              "research_json": sha_file(research_dir() / "research.json"),
              "centres_json": sha_file(P.out_dir() / CENTRES)}
    what = {"EX-R": "research's preset with the amp's dry recipe (tonal edits kept, time effects off)",
            "EX-Rwet": "research's preset as written", "EX-Rroute": "research's template made dry (its own amp's recipe)",
            "EX-M": "the model path (default version) on the released mix", "EX-M3": "M's answers on all three amps",
            "EX-Mx": "the model path with --version xlst_mdxc at M's window", "EX-Mlab": "M with the label's class (M's window)",
            "EX-Mcrop": "the model path with --start at the crop", "EX-Munity": "the model path on the unity sum at M's window",
            "EX-Cpick": "the stock-DI pick on C's presets", "EX-C": "Step 2's labels' centre (all labels), label class",
            "EX-Cown": "Step 2's model's own constant (all labels), label class",
            "EX-Cm": "C on M's class and amp, where research's class is not the label's",
            "EX-Cownm": "C-own on M's class and amp, where research's class is not the label's",
            "EX-S": "phase 4's S on M's amp, re-rendered (identical check)",
            "EX-Sm": "S of M's class on M's amp, where research's class is not the label's (the loudness row)",
            "EX-L": "the stored ZT label (settings.best)"}
    for t in TAGS:
        P.save(answers_path(t), {**common, "tag": t, "what": what[t], "meta": meta.get(t), "answers": out[t],
                                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        shas[t] = sha_file(answers_path(t))
    tables = zero_render_tables(inp, res, out)
    P.save(ex_dir() / "tables.json", tables)
    shas["tables_json"] = sha_file(ex_dir() / "tables.json")
    shas.update(gshas)
    print(json.dumps({k: v for k, v in tables.items() if k in ("classes", "picks")}, indent=1)[:4000])
    print(f"record in the ledger's {P.LEDGER_ID} entry before any judge render: \"{PHASE_ANSWERS}\": "
          + json.dumps({"hashes": shas}, indent=1))
    print(f"groups to render: {sum(len(v) for v in out.values())}, renders "
          f"{2 * sum(len(g) for v in out.values() for g in v.values())}")
    print("EXAM ANSWERS DONE")


def zero_render_tables(inp, res, out):
    """Plan section 7's zero-render tables: research's class against the label; each chain window (start, how, exposure,
    the crop's overlap, the target's DI activity in it); each amp pick and its cosine margin; M's knob distance from
    C and C-own; M's movement between its inputs against its movement between units."""
    import numpy as np

    from analysis import io
    from learn import clean_di as CD

    params = json.loads((PLUGIN_ROOT / "packs" / "morgan" / "manifest.json").read_text())["parameters"]
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    t = {"classes": {}, "windows": {}, "picks": {}, "knobs_M_vs_C": {}, "movement": {}}
    for u in units():
        k = u["key"]
        ru = res["units"][k]
        t["classes"][k] = {"label": u["cls"], "research": ru["cls"], "model": ru["cls_model"], "agrees": ru["agrees"],
                           "amp": ru.get("amp"), "no_research": bool(ru.get("no_research"))}
        r = inp["units"][k]
        first = u["members"][0]
        di = io.load(session_di(crop_dir(first, parts))).mono().astype(np.float64)
        play = CD.playing(CD.frame_db(di))
        ca, cb = r["crops"][first]["session_s"]
        for arm in CHAIN:
            d = chain_dir(arm, k)
            if not (d / "window.json").exists():
                continue
            w = json.loads((d / "window.json").read_text())
            s0 = float(w["start_s"]) + (0.0 if arm == "Munity" else r["offset_samples"] / 48000)
            fr = CD.frames_in(int(round(s0 * 48000)), int(round((s0 + 10) * 48000)), len(play))
            t["windows"][f"{arm}|{k}"] = {
                "start_session_s": s0, "chosen_by": w.get("chosen_by"), "candidates": w.get("candidates"),
                "steady_and_present": w.get("steady and present"), "exposure_db": (w.get("window") or {}).get("exposure_db"),
                "crop_overlap_s": max(0.0, min(cb, s0 + 10) - max(ca, s0)),
                "target_di_active": float(np.mean(play[fr.start:fr.stop])) if len(fr) else None}
            pr = json.loads((d / "preset.json").read_text())
            ds = sorted(pr["distances"].values())
            t["picks"][f"{arm}|{k}"] = {"amp": pr["amp"], "distances": pr["distances"], "margin": ds[1] - ds[0],
                                        "output_gain": pr["output_gain"]}
        cp = json.loads((ex_dir() / "cpick" / "units" / k / "preset.json").read_text())
        ds = sorted(cp["distances"].values())
        t["picks"][f"Cpick|{k}"] = {"amp": cp["amp"], "distances": cp["distances"], "margin": ds[1] - ds[0],
                                    "output_gain": cp["output_gain"]}
        m = json.loads((chain_dir("M", k) / "preset.json").read_text())
        for tag in ("EX-C", "EX-Cown"):                # C on M's class and amp (its EX-*m twin where they differ)
            key = f"{first}|{m['amp']}"
            c = (out[tag + "m"].get(key) or out[tag][key])[ANY]["settings"]
            t["knobs_M_vs_C"][f"{k}|{tag}"] = knob_distance(m["settings"], c, m["amp"], params)
    ans = {arm: {u["key"]: json.loads((chain_dir(arm, u["key"]) / "answers.json").read_text())["answers"]
                 for u in units() if (chain_dir(arm, u["key"]) / "answers.json").exists()} for arm in CHAIN}
    within, between = {}, []
    for arm in ("Mx", "Mcrop", "Munity"):
        vals = [knob_distance(ans["M"][k][a]["settings"], ans[arm][k][a]["settings"], a, params)["cont_mean"]
                for k in ans[arm] for a in AMPS]
        within[arm] = {"median": statistics.median(vals), "n": len(vals)} if vals else None
    ks = sorted(ans["M"])
    for i, k1 in enumerate(ks):
        for k2 in ks[i + 1:]:
            if res["units"][k1]["cls_model"] == res["units"][k2]["cls_model"]:
                between += [knob_distance(ans["M"][k1][a]["settings"], ans["M"][k2][a]["settings"], a, params)
                            ["cont_mean"] for a in AMPS]
    t["movement"] = {"M_vs_input_variant_same_unit": within,
                     "M_between_units_same_class": {"median": statistics.median(between), "n": len(between)}
                     if between else None}
    return t


# --- the judge renders -------------------------------------------------------------------------------------------------

def unhashed(e):
    want = ((e or {}).get(PHASE_ANSWERS) or {}).get("hashes") or {}
    bad = []
    for t in TAGS:
        p = answers_path(t)
        if not p.exists():
            bad.append(f"{t}: no answers file")
        elif want.get(t) != sha_file(p):
            bad.append(f"{t}: not the ledger's")
    for name, p in {"tables_json": ex_dir() / "tables.json", **guard_files()}.items():
        if not p.exists() or want.get(name) != sha_file(p):
            bad.append(f"{p.name}: not the ledger's")
    return bad


def page_clips(amp_of, page_units_):
    """The judged renders the page plays, kept at judge time: R, M and C-pick on their amps, L on its page amp and the
    page's search half. -> {(tag, slug, amp, half key)}."""
    out = set()
    for pu in page_units_:
        s = pu["slug"]
        for tag in ("EX-R", "EX-M", "EX-Cpick"):
            if s in amp_of.get(tag, {}):
                out.add((tag, s, amp_of[tag][s], ANY))
        if s in amp_of.get("EX-L-page", {}):
            out.add(("EX-L", s, amp_of["EX-L-page"][s], pu["search"]))
    return out


def load_answers():
    ans = {t: json.loads(answers_path(t).read_text())["answers"] for t in TAGS}
    amp_of = {t: {} for t in TAGS}
    for t in ONE:
        for k in ans[t]:
            s, a = k.split("|")
            if s in amp_of[t]:
                raise SystemExit(f"{t}: two amps for {s}")
            amp_of[t][s] = a
    return ans, amp_of


def page_units():
    """L0's stored units: one direction (search, held half) per V-real part (`ear_vreal` plan)."""
    return json.loads((P.out_dir() / "ear-vreal" / "plan.json").read_text())["units"]


def cmd_render(args):
    """One shard of (slug, amp) groups over every EX arm: each answer fresh and primed in its own process through the
    part's measure DI, judged against its amp track on both halves (`vreal_render`'s recipe), its LUFS recorded; EX-S's
    renders checked against phase 4's stored S renders; the page's renders kept. Refuses until every answers file's
    sha256 is the ledger's. -> vreal/judge/EX-*/<slug>|<amp>.json."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import trusted_data as T

    e = entry()
    require_guards()
    bad = unhashed(e)
    if bad:
        raise SystemExit(f"renders refuse until the answers' hashes are in the ledger: {bad}")
    ans, amp_of = load_answers()
    pu = page_units()
    amp_of["EX-L-page"] = {u["slug"]: page_l_amp(u["slug"], u["search"]) for u in pu
                           if any(k.startswith(u["slug"] + "|") for k in ans["EX-L"])}
    keep = page_clips(amp_of, pu)
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    groups = sorted({tuple(k.split("|")) for t in TAGS for k in ans[t]})
    k_, n_ = (int(x) for x in args.shard.split("/"))
    mine = [g for j, g in enumerate(groups) if j % n_ == k_]
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    for amp, by_cls in ms.items():
        for cls, (_, S) in by_cls.items():
            if K.key(dict(menu[amp][K.START[cls][amp]][1])) != K.key(S):
                raise SystemExit(f"{amp} {cls}: the live S differs from the stored copy")
    shas = {t: P.answers_sha(ans[t]) for t in TAGS}
    stored_s = stored_judge("S")
    renders, differ = 0, []
    for slug, amp in mine:
        key = f"{slug}|{amp}"
        ctx = None
        for t in TAGS:
            if key not in ans[t]:
                continue
            gp = judge_dir(t) / f"{key}.json"
            if gp.exists():
                if json.loads(gp.read_text()).get("answers_sha256") != shas[t]:
                    raise SystemExit(f"{gp}: rendered from other answers")
                continue
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            ctx = ctx or group_ctx(menu, ms, parts, slug, amp)
            rec = {"slug": slug, "amp": amp, "tag": t, "answers_sha256": shas[t], "judge": {}, "render_sha256": {},
                   "lufs": {}}
            for hk, a in sorted(ans[t][key].items()):
                st = LO.tdict(a["settings"])
                y = AM.fresh_render(CB.new_renderer, ctx["di32"], a["select"], st, st)
                renders += 2
                rec["judge"][hk] = K.judge(ctx["ref"], y, ctx["di"], ctx["part"]["judge_lag"])
                rec["render_sha256"][hk] = AM.audio_sha(y)
                mono = y.mean(axis=1) if y.ndim == 2 else y
                rec["lufs"][hk] = float(SA.lufs(mono))
                if (t, slug, amp, hk) in keep:
                    cp = clip_path(t, slug, amp, hk)
                    cp.parent.mkdir(parents=True, exist_ok=True)
                    np.save(cp, np.asarray(y, np.float64))
            rec["renders"] = 2 * len(ans[t][key])
            rec["time"] = time.strftime("%Y-%m-%d %H:%M:%S")       # the audit checks the hashes were in the ledger first
            if t == "EX-S":
                old = (stored_s.get(key) or {}).get("render_sha256")
                rec.update(recheck_of="S", recheck_sha256=old, identical=old == rec["render_sha256"])
                if not rec["identical"]:
                    differ.append(key)
            P.save(gp, rec)
        print(f"{key}: done; renders so far {renders}", flush=True)
    if differ:
        print(f"RECHECK: {len(differ)} S groups differ from phase 4's renders: {differ}", flush=True)
    print(f"EXAM RENDER DONE {k_}/{n_}: {renders} renders", flush=True)


# --- the report (zero renders) ----------------------------------------------------------------------------------------

def row_specs():
    """The declared rows (plan section 7): (name, spec a, spec b, scope). Scopes: "all" (every slug), "r" (the slugs with
    R: a unit with no passing research run leaves these rows), "rroute" (with R-route), "lab" (with M-lab), "v10"."""
    M, R = ("EX-M", "own"), ("EX-R", "own")
    S3 = ("S", "all")
    rows = [("M - R (primary)", M, R, "r"),
            ("M - S", M, S3, "all"), ("M - S on M's amp", M, ("S", "at:EX-M"), "all"),
            ("R - S", R, S3, "r"), ("R - S on R's amp", R, ("S", "at:EX-R"), "r"),
            ("R-wet - R", ("EX-Rwet", "own"), R, "r"), ("R - R-route", R, ("EX-Rroute", "own"), "rroute"),
            ("R-route - S", ("EX-Rroute", "own"), S3, "rroute")]
    rows += [(f"M3 - S on {a}", ("EX-M3", f"amp:{a}"), ("S", f"amp:{a}"), "all") for a in AMPS]
    rows += [("M3 - S (three amps)", ("EX-M3", "all"), S3, "all"),
             ("M - C on M's amp", M, ("EX-C", "at:EX-M", "EX-Cm"), "all"),
             ("M - C-own on M's amp", M, ("EX-Cown", "at:EX-M", "EX-Cownm"), "all"),
             ("M - C-pick", M, ("EX-Cpick", "own"), "all"),
             ("C - S", ("EX-C", "all"), S3, "all"), ("C-own - S", ("EX-Cown", "all"), S3, "all"),
             ("C-pick - S", ("EX-Cpick", "own"), S3, "all"),
             ("M-x - M", ("EX-Mx", "own"), M, "all"), ("M-lab - M", ("EX-Mlab", "own"), M, "lab"),
             ("M-crop - M", ("EX-Mcrop", "own"), M, "all"), ("M-unity - M", ("EX-Munity", "own"), M, "all"),
             ("M - M3 (three amps' mean)", M, ("EX-M3", "all"), "all"),
             ("M - M3's best amp (an oracle: the amp picked on the half it is scored on)", M, ("EX-M3", "best"), "all"),
             ("L - S", ("EX-L", "all"), S3, "v10"), ("M - S (V-real-10)", M, S3, "v10")]
    rows += [(f"M - {n} on M's amp (stored)", M, (t, "at:EX-M"), "all") for n, t in STORED.items()]
    return rows


def cmd_report(args):
    """The rows, once every judge record exists and the guards pass (plan section 6): the answers' hashes the ledger's,
    every record from today's answers, EX-S identical to phase 4's S renders, S's positive control; L's fresh values
    beside the stored ones; M against M3 on M's amp (the output gain is not scored). A held half where S is not finite
    drops from every row (counted); only a missing answer stops. Refuses if any report exists: V-real is read once.
    -> exam/report-<label>.json."""
    entry()
    require_guards()
    rp = ex_dir() / f"report-{args.label}.json"
    done = sorted(p.name for p in ex_dir().glob("report-*.json"))
    if done:
        raise SystemExit(f"{done} exists: V-real is read once")
    bad = unhashed(P.ledger_entry())
    if bad:
        raise SystemExit(f"the answers' hashes are not the ledger's: {bad}")
    inp = load_inputs()
    ans, amp_of = load_answers()
    judge, recs = {}, {}
    for t in TAGS:
        recs[t] = stored_judge(t)
        sha = P.answers_sha(ans[t])
        miss = [k for k in ans[t] if k not in recs[t]]
        stale = [k for k, r in recs[t].items() if r["answers_sha256"] != sha]
        if miss or stale:
            raise SystemExit(f"{t}: {len(miss)} groups unjudged, {len(stale)} from other answers; no row is read")
        judge[t] = {k: r["judge"] for k, r in recs[t].items()}
    for t in ("S", *STORED.values()):
        judge[t] = {k: r["judge"] for k, r in stored_judge(t).items()}
    differ = [k for k, r in recs["EX-S"].items() if not r.get("identical")]
    if differ:
        raise SystemExit(f"EX-S differs from phase 4's S renders on {differ}: stop")
    pc = P.s_positive_control(judge["S"])
    if not pc["passes"] or pc["n"] != P.S_CONTROL_N:
        raise SystemExit(f"S's positive control fails: {pc}")
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    v10 = set(plan["vreal"]["v_real_10"])
    attrs = attrs_of(inp)
    band_of = {s: PR.VREAL[s][0] for s in PR.VREAL}
    unit_of = {s: P.vreal_part_key(s) for s in PR.VREAL}
    scopes = {"all": set(PR.VREAL), "v10": v10, "lab": set(amp_of["EX-Mlab"]), "r": set(amp_of["EX-R"]),
              "rroute": set(amp_of["EX-Rroute"])}
    out_scope = {k: len(v) for k, v in scopes.items()}
    out = {"plan": PLAN, "ledger": f"{P.LEDGER_ID} {PHASE}", "s_positive_control": pc, "s_recheck_identical":
           len(recs["EX-S"]), "scope_slugs": out_scope,
           "units_without_R": sorted({unit_of[s] for s in scopes["all"] - scopes["r"]}), "rows": {}}
    for name, a, b, scope in row_specs():
        rows, cnt = exam_rows(judge, amp_of, a, b, scopes[scope], band_of, unit_of)
        if cnt["missing"]:
            raise SystemExit(f"{name}: {cnt['missing']} held halves without an answer {cnt}")
        out["rows"][name] = {"a": a, "b": b, "scope": scope, **cnt, **stratified(rows, attrs)} if rows else {
            "a": a, "b": b, "scope": scope, **cnt, "all": None}
    ms_ = out["rows"]["M - S (V-real-10)"]["all"]
    ls_ = out["rows"]["L - S"]["all"]
    out["share_of_headroom"] = {"(M - S) / (L - S), V-real-10": ms_["mean"] / ls_["mean"] if ls_["mean"] else None,
                                "leave_one_band_out": {bnd: ms_["leave_one_out"][bnd] / ls_["leave_one_out"][bnd]
                                                       for bnd in ls_["leave_one_out"] if ls_["leave_one_out"][bnd]}}
    lg = []
    for k, r in recs["EX-L"].items():
        slug, amp = k.split("|")
        for search, j in r["judge"].items():
            held = OTHER[search]
            stored = zt_label(slug, amp, search)["judge_best"][held]
            lg.append(abs(math.log(j[held] / stored)) if finite(j[held]) and finite(stored) else math.inf)
    from learn import knob_ceiling as K

    out["L_fresh_vs_stored"] = {"n": len(lg), "max_abs_log": max(lg), "median_abs_log": statistics.median(lg),
                                "over_tolerance": sum(x > K.REPEAT_TOL for x in lg), "tolerance": K.REPEAT_TOL,
                                "used": "the fresh values"}
    inv = []
    for s, a in amp_of["EX-M"].items():
        for h in ("A", "B"):
            x, y = held_value(judge["EX-M"][f"{s}|{a}"], h), held_value(judge["EX-M3"][f"{s}|{a}"], h)
            if finite(x) and finite(y):
                inv.append(abs(math.log(x / y)))
    out["output_gain_not_scored"] = {"M vs M3 on M's amp, max |ln ratio|": max(inv), "n": len(inv)}
    loud = {}
    for s, a in amp_of["EX-M"].items():                  # against S of M's own class (EX-Sm where the classes differ)
        sref = recs["EX-Sm"].get(f"{s}|{a}") or recs["EX-S"][f"{s}|{a}"]
        loud[s] = recs["EX-M"][f"{s}|{a}"]["lufs"][ANY] - sref["lufs"][ANY]
    out["loudness_M_minus_S_db"] = {"per_slug": loud, "median_abs": statistics.median(abs(v) for v in loud.values()),
                                    "band_mean": P.clustered([(band_of[s], unit_of[s], v) for s, v in loud.items()])}
    out["tables"] = json.loads((ex_dir() / "tables.json").read_text())
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(rp, out)
    for name, r in out["rows"].items():
        c = r.get("all")
        if not c or c["mean"] is None:
            print(f"{name}: no rows ({r.get('missing')} missing)")
            continue
        iv = "" if c["lo90"] is None else f" [{c['lo90']:+.3f}, {c['hi90']:+.3f}]"
        print(f"{name:<34} {c['mean']:+.3f}{iv}  bands {c['clusters_negative']}/{c['clusters']} better; parts "
              f"{c['parts_negative']}/{c['parts']}; part-weighted {c['part_weighted']:+.3f}")
    print(json.dumps({k: out[k] for k in ("share_of_headroom", "L_fresh_vs_stored", "output_gain_not_scored")}, indent=1))
    print("EXAM REPORT DONE")


# --- the listening page -----------------------------------------------------------------------------------------------

INTRO = """<h1>Which preset sounds most like the record?</h1>
<p class="intro">@@COUNT@@ items of about 5 seconds, looping. <b>Record</b> is the guitar as it was recorded through a real
amp. The lettered presets play <b>the very same performance</b>, so every note lines up and only the tone differs. Most
items have four letters, some fewer. Everything loops together and switches instantly at the same moment: tap a button,
or press R and the letters (or 1-5); Space stops. All clips are set to the same loudness. Headphones, please.</p>
<p class="intro">For each item, rank the letters: 1 is closest to the Record. If two or more sound the same to you, give
them the same rank. Rating how close each one is, and saying whether you are sure, are optional. Which preset is which is
hidden and shuffled per item, and a couple of items come back later.
Answers are saved in this browser as you go; tap <b>Export</b> any time and send the text.</p>"""

JS_EDITS = (
    ('const STORE = "ear-vreal:" + DATA.build;', 'const STORE = "real-song-exam:" + DATA.build;'),
    ('const XF = 0.012, KEYS = ["ref", "A", "B", "C", "D"];',
     'const XF = 0.012;\nfunction keysOf(it) { return ["ref"].concat(it.dataset.letters.split("")); }'),
    ("b = await Promise.all(KEYS.map(x => decode(it.dataset.id + \"-\" + x)));",
     "b = await Promise.all(keysOf(it).map(x => decode(it.dataset.id + \"-\" + x)));"),
    ("const srcs = [], gains = {};", "const srcs = [], gains = {}, keys = keysOf(it);"),
    ("g.gain.value = KEYS[j] === k ? 1 : 0;", "g.gain.value = keys[j] === k ? 1 : 0;"),
    ("gains[KEYS[j]] = g;", "gains[keys[j]] = g;"),
    ("cur = {it: it, srcs: srcs, gains: gains, k: k}; mark();", "cur = {it: it, srcs: srcs, gains: gains, k: k, keys: keys}; mark();"),
    ("  if (cur.k === k) return;", "  if (cur.k === k || cur.keys.indexOf(k) < 0) return;"),
    ("  KEYS.forEach(x => { const g = cur.gains[x].gain;", "  cur.keys.forEach(x => { const g = cur.gains[x].gain;"),
    ("    Object.keys(r).forEach(o => { if (o !== l && r[o] === v) delete r[o]; });   // a rank is held by one letter\n", ""),
    ('const full = ["A", "B", "C", "D"].every(l => r[l] && cl[l]) && a.conf;',
     'const full = it.dataset.letters.split("").every(l => r[l]);'),
    ('if (m[k]) { e.preventDefault(); pick(it, m[k]); }',
     'if (m[k] && keysOf(it).indexOf(m[k]) >= 0) { e.preventDefault(); pick(it, m[k]); }'),
    ('const order = ["A", "B", "C", "D"].filter(l => r[l]).sort((p, q) => r[p] - r[q]);',
     'const ls = it.dataset.letters.split(""); const order = ls.filter(l => r[l]).sort((p, q) => r[p] - r[q]);'),
    ('(order.join(">") || "-")', '(order.map(l => l + r[l]).join(" ") || "-")'),
    ('["A", "B", "C", "D"].map(l => l + ":" + (cl[l] || "-")).join(" ")', 'ls.map(l => l + ":" + (cl[l] || "-")).join(" ")'),
)


def player_js():
    """`ear_vreal`'s player with each item's own letters, ties allowed, closeness and confidence optional."""
    from learn import ear_vreal as E

    js = E.JS
    for old, new in JS_EDITS:
        if old not in js:
            raise SystemExit(f"ear_vreal's player changed: {old[:60]}")
        js = js.replace(old, new)
    if "KEYS" in js or "delete r[o]" in js:
        raise SystemExit("the player still holds the fixed letters or the one-letter-a-rank rule")
    return js


CSS_EXTRA = "".join(f".rank.n{n} {{ grid-template-columns:auto repeat({n}, 1fr); }}\n" for n in (2, 3, 4)) + \
    ".rank.close { grid-template-columns:auto repeat(4, 1fr); }\n"


def cards(items):
    """Each item's card: the Record and its letters to play; ranks 1 to n per letter (ties allowed); closeness,
    confidence and a note, optional."""
    from learn import ear_vreal as E

    out = []
    for it in items:
        ls = sorted(it["letters"])
        n = len(ls)
        rank = "".join(f'<span class="lab">{k}</span>' + "".join(
            f'<button type="button" data-l="{k}" data-r="{r}">{r}</button>' for r in range(1, n + 1)) for k in ls)
        close = "".join(f'<span class="lab">{k}</span>' + "".join(
            f'<button type="button" data-l="{k}" data-v="{v}">{t}</button>' for v, t in E.CLOSE) for k in ls)
        heads = '<span class="hd">closest</span>' + '<span class="hd"></span>' * (n - 2) + '<span class="hd">furthest</span>'
        out.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{it["n"]}" data-letters="{"".join(ls)}">'
            f'<div class="num">{it["n"]} / {len(items)}</div><h3>Recording {it["n"]}</h3><div class="plays">'
            '<button type="button" class="src" data-k="ref" aria-pressed="false">Record (R)</button>'
            + "".join(f'<button type="button" class="src" data-k="{k}" aria-pressed="false">{k}</button>' for k in ls)
            + '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div><p class="now"></p>'
            '<div class="q">Rank them, 1 closest to the Record (the same rank if you can\'t tell them apart)</div>'
            f'<div class="rank n{n}"><span></span>{heads}{rank}</div>'
            f'<div class="q">How close is each one to the Record? (optional)</div><div class="rank close">{close}</div>'
            '<div class="conf"><span>Confidence (optional):</span><button type="button" data-c="sure">Sure</button>'
            '<button type="button" data-c="unsure">Unsure</button></div>'
            '<input class="note" type="text" placeholder="Note (optional)" aria-label="Note">'
            '<div class="done"></div></article>')
    return "".join(out)


def page_html(items, clips, build):
    from learn import ear_vreal as E

    js, css = player_js(), E.CSS + CSS_EXTRA
    a, b = E.PAGE.index("<h1>"), E.PAGE.index("@@CARDS@@")
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in items]})
    page = (E.PAGE[:a] + INTRO + "\n" + E.PAGE[b:]).replace("@@COUNT@@", str(len(items))) \
        .replace("@@CARDS@@", cards(items)).replace("@@CSS@@", css).replace("@@DATA@@", data) \
        .replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", js)
    return page, css, js


def page_leaks(text, items):
    words = {"EX-", "research", "model path", "C-pick", "R-all", "adopted", "centre"}
    for it in items:
        words |= {it["slug"], it["key"], it["band"], P.vreal_part_key(it["slug"])}
    words |= {s for s in {r["song"] for r in json.loads(inputs_path().read_text())["units"].values()}}
    return sorted(w for w in words if len(w) > 2 and w in text)


def cmd_page(args):
    """The page (plan section 8; zero renders): L0's units on their stored held half; R, M, C-pick and L, each on its own
    amp, from the judged renders kept at judge time (each clip's hash the judge record's); identical presets share a
    letter; 2 repeats; every clip at -23 LUFS by `ear_vreal.level_group`. -> exam/page/key.json and the page under
    ~/ndsp-presets/listening/real-song-exam/ (index.html, artifact.html); not published."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import c1a_ear as C1
    from learn import ear_vreal as E
    from learn import rescore as R

    entry()
    P.require(PHASE_EAR)
    kp = ex_dir() / "page" / "key.json"
    if kp.exists() and not args.force:
        raise SystemExit(f"{kp} exists: a rebuild hides the listener's stored answers (--force)")
    ans, amp_of = load_answers()
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    tags = {"R": "EX-R", "M": "EX-M", "C": "EX-Cpick", "L": "EX-L"}
    ups = []
    for u in page_units():
        s = u["slug"]
        amps = {c: amp_of[t][s] for c, t in tags.items() if t != "EX-L" and s in amp_of[t]}   # a unit with no R: 3
        hk = {c: ANY for c in amps}
        if any(k.startswith(s + "|") for k in ans["EX-L"]):
            amps["L"], hk["L"] = page_l_amp(s, u["search"]), u["search"]
        cands, recs = {}, {}
        for c, a in amps.items():
            g = json.loads((judge_dir(tags[c]) / f"{s}|{a}.json").read_text())
            recs[c] = (a, hk[c], g)
            x = ans[tags[c]][f"{s}|{a}"][hk[c]]
            cands[c] = (x["select"], json.dumps(x["settings"], sort_keys=True))
        ups.append({**u, "cands": {c: {"amp": a, "half": h, "sha": g["render_sha256"][h],
                                       "judge": g["judge"][h][u["held"]]} for c, (a, h, g) in recs.items()},
                    "groups": page_groups(cands)})
    items = page_draw(ups)
    cache, od = ex_dir() / "page" / "aac-cache", P.DATA / "listening" / "real-song-exam"
    od.mkdir(parents=True, exist_ok=True)
    clips, kept = {}, []
    for it in items:
        s = it["slug"]
        lag = judge_lag(s, parts)
        ref = np.asarray(P.amp_track(s, parts[s]), np.float64)
        a0, b0 = (int(x * 48000) for x in R.HALVES[it["held"]])
        group, wins = {}, set()
        for letter, g in it["letters"].items():
            c = it["cands"][g[0]]
            y = np.load(clip_path(tags[g[0]], s, c["amp"], c["half"]))
            if AM.audio_sha(y) != c["sha"]:
                raise SystemExit(f"{s} {g[0]}: the kept clip is not the judged render")
            mono = y.mean(axis=1) if y.ndim == 2 else y
            w = E.window(a0, b0, len(ref), len(mono), lag)
            wins.add(w)
            group[letter] = mono[w[0] - lag:w[1] - lag]
        if len(wins) != 1:
            raise SystemExit(f"{s}: the renders' windows differ")
        s0, s1 = wins.pop()
        group["ref"] = ref[s0:s1]
        if len({len(v) for v in group.values()}) != 1:
            raise SystemExit(f"{s}: clip lengths differ")
        lev, info = E.level_group(group)
        for k, y in lev.items():
            clips[f"{it['id']}-{k}"] = E.encode(y, cache)
        kept.append({**it, "judge": {c: v["judge"] for c, v in it["cands"].items()}, "levels": info,
                     "window": [s0, s1]})
    build = hashlib.sha256((json.dumps([k["letters"] for k in kept], default=list) + os.urandom(8).hex())
                           .encode()).hexdigest()[:12]
    page, css, js = page_html(kept, clips, build)
    body = cards(kept) + json.dumps({"build": build})
    leaks = page_leaks(body, kept)
    if leaks:
        raise SystemExit(f"the page names {leaks}")
    P.save(kp, {"page": "real-song-exam", "build": build, "phase": PHASE_EAR, "items": kept,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    (od / "index.html").write_text(page)
    art = C1.artifact_page(page, css, js).replace("<title>Record A/B Check</title>", "<title>Record Tone Check</title>")
    (od / "artifact.html").write_text(art)
    print(f"EXAM PAGE DONE: {len(kept)} items, build {build}; {od / 'index.html'} "
          f"({(od / 'index.html').stat().st_size / 1e6:.1f} MB), {od / 'artifact.html'}")


def cmd_score(args):
    """The page's read (plan section 8) from the listener's export (its last JSON line) -> exam/page/score.json."""
    entry()
    P.require(PHASE_EAR)
    key = json.loads((ex_dir() / "page" / "key.json").read_text())
    for it in key["items"]:
        it["letters"] = {k: tuple(v) for k, v in it["letters"].items()}
    last = [ln for ln in pathlib.Path(args.answers).read_text().splitlines() if ln.startswith("{")][-1]
    ex = json.loads(last)
    if ex.get("build") != key["build"]:
        raise SystemExit(f"{args.answers}: build {ex.get('build')}, this page's is {key['build']}")
    rep = ear_read(key["items"], ex["answers"])
    rep["build"] = key["build"]
    P.save(ex_dir() / "page" / "score.json", rep)
    print(json.dumps(rep, indent=1, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inputs").set_defaults(fn=cmd_inputs)
    sub.add_parser("guards").set_defaults(fn=cmd_guards)
    sub.add_parser("r1-repro").set_defaults(fn=cmd_r1_repro)
    rp = sub.add_parser("research-prepare")
    rp.add_argument("--again", nargs="*", help="units whose run failed a guard: a fresh folder each")
    rp.set_defaults(fn=cmd_research_prepare)
    rr = sub.add_parser("research-route")
    rr.add_argument("--workers", type=int, default=3)
    rr.set_defaults(fn=cmd_research_route)
    sub.add_parser("research-collect").set_defaults(fn=cmd_research_collect)
    ch = sub.add_parser("chain")
    ch.add_argument("--arms", help="a subset of M,Mcrop,Munity,Mlab,Mx (default all, in that order)")
    ch.set_defaults(fn=cmd_chain)
    sub.add_parser("c-pick").set_defaults(fn=cmd_cpick)
    sub.add_parser("answers").set_defaults(fn=cmd_answers)
    r = sub.add_parser("render")
    r.add_argument("--shard", default="0/1")
    r.set_defaults(fn=cmd_render)
    rep = sub.add_parser("report")
    rep.add_argument("--label", required=True)
    rep.set_defaults(fn=cmd_report)
    pg = sub.add_parser("page")
    pg.add_argument("--force", action="store_true")
    pg.set_defaults(fn=cmd_page)
    sc = sub.add_parser("score")
    sc.add_argument("--answers", required=True)
    sc.set_defaults(fn=cmd_score)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
