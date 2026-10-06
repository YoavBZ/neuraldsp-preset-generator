#!/usr/bin/env python3
"""Listening check L: does the ear agree with the average-guitar measure?

Declared in `docs/avg-measure-listening-plan.md` (Phase 0 L of `docs/di-recovery-plan.md`).

    .venv/bin/python -m learn.build_avg_listening count     # pair counts only, no pair named
    .venv/bin/python -m learn.build_avg_listening build     # trials, audio, sheet, private key
    .venv/bin/python -m learn.build_avg_listening take      # the listener plays and answers
    .venv/bin/python -m learn.build_avg_listening phone     # or: one phone page per sitting
    .venv/bin/python -m learn.build_avg_listening check --answers SHEET   # public check
    .venv/bin/python -m learn.build_avg_listening score     # after the sheet's hash is committed

Nothing is rendered: every option is an existing render (the `avg` and `swap` renders
of `learn/di_robustness.py`, the clean PR12 panel). `count` and `build` first compute,
once, the true-DI judge and the swap-DI judge on half B (recording bands) for every
candidate, cached beside the outputs.

The listener's folder (`listen/`) holds numbered trial files and the answer sheet,
nothing else. The key (pairs, distances, A/B) is `private/trials.json`; the plan records
its sha256, and the scorer refuses any other key. The scorer records the answer sheet's
sha256 before it reads the key and refuses a different sheet afterwards.

`phone` builds, from the listener's folder alone (never the key), one self-contained
page per sitting, `listen/sitting-N-phone.html`, as `research/listening_check.py
phone-page` did: every clip embedded as mono AAC at PHONE_KBPS, tap-to-answer A/B
buttons, answers kept in the browser, and an answer line ("Sitting 1: 1A 2B ...") to
copy and send. The scorer reads a sheet of those lines as it reads `ANSWERS.md`; `check`
reads a sheet against the public trial numbers, before its hash is committed.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import pathlib
import random
import re
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))
sys.path.append(str(PLUGIN_ROOT / "scripts"))

from _cli import die, guarded  # noqa: E402

HOME = pathlib.Path(os.path.expanduser("~/ndsp-presets"))
KILL = HOME / "runs" / "kill"
CROPS = HOME / "references" / "validation-crops"
ROBUST = HOME / "learn" / "di-robust"
OUT = HOME / "listening" / "avg-measure"
PLAN = PLUGIN_ROOT / "docs" / "avg-measure-listening-plan.md"

SR, LATENCY = 48000, 52
HALF_B = (5.5, 10.0)
BANDS = "recording"
SEED = 20261006
MARGIN = 0.15                 # log distance
DISAGREE, SWAP, REPEATS, PER_PART = 24, 6, 6, 2
EXPOSED = 0.9                 # share of half B's frames where the DI plays
SITTING = 18
PASS_AGREE, MIN_CONSISTENT = 17, 5
FADE_S, GAP_S, CYCLE_GAP_S = 0.010, 0.5, 1.0
TARGET_LUFS, PEAK_CEILING_DBTP = -20.0, -1.0


def sha256(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def mono(path):
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    assert sr == SR, path
    return x.mean(axis=1)


def k1():
    """K1's 25 parts, their bands and lags, the 21 factory presets, and the true-DI files."""
    j = json.loads((KILL / "k-judge-pr12-clean.json").read_text())
    rows = {r["part"]: r for r in j["k1"]["recording"]["rows"]}
    lags = {p: j["lags"][p]["lag"] for p in rows}
    panel = json.loads((KILL / "pr12-clean" / "index.json").read_text())
    names = sorted({r["candidate"] for r in panel["rows"]
                    if "file" in r and r["candidate"] != "template"})
    files = {}
    for r in panel["rows"]:
        if "file" in r:
            files.setdefault(r["part"], {})[r["candidate"]] = pathlib.Path(r["file"])
    return sorted(rows), {p: rows[p]["band"] for p in rows}, lags, names, files


def render_path(variant: str, part: str, name: str) -> pathlib.Path:
    import render_preset_panel as RP

    return ROBUST / "renders" / variant / part / f"{RP._slug(name)}.wav"


def provenance() -> dict:
    return {"k_judge": sha256(KILL / "k-judge-pr12-clean.json"),
            "panel_index": sha256(KILL / "pr12-clean" / "index.json"),
            "avg_distances": sha256(ROBUST / "avg-yardstick-distances.json")}


# --- step 1: the true-DI and swap-DI judges on half B ---------------------------

def measure_part(job):
    import numpy as np

    import kill_tests as K
    from analysis.aligned import aligned_distance

    part, lag, names, files = job
    ref, di = mono(CROPS / part / "reference.wav"), mono(CROPS / part / "di.wav")
    swap_di = np.load(ROBUST / "di" / f"{part}--swap.npy")

    def judge(render, d):
        return aligned_distance(ref, mono(render), d, lag=lag, render_latency=LATENCY,
                                start_s=HALF_B[0], end_s=HALF_B[1], bands=BANDS).distance

    out = {"true": {n: judge(files[n], di) for n in names},
           "swap": {n: judge(render_path("swap", part, n), swap_di) for n in names},
           "exposure": K.active_fraction(di, *HALF_B)}
    print(part, flush=True)
    return part, out


def distances() -> dict:
    """{part: {"avg"|"true"|"swap": {candidate: distance}, "exposure": share}}, cached."""
    cache = OUT / "work" / "distances.json"
    prov = provenance()
    if cache.exists():
        cached = json.loads(cache.read_text())
        if cached["provenance"] != prov:
            die(f"{cache} was computed from other inputs; move it aside")
        return cached["parts"]
    from concurrent.futures import ProcessPoolExecutor

    parts, _, lags, names, files = k1()
    names = names + ["template+R"]
    with ProcessPoolExecutor(4) as ex:
        res = dict(ex.map(measure_part, [(p, lags[p], names, files[p]) for p in parts]))
    avg = json.loads((ROBUST / "avg-yardstick-distances.json").read_text())
    for p in parts:
        res[p]["avg"] = avg[p][f"{BANDS}|B"]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"provenance": prov, "parts": res}, indent=1) + "\n")
    return res


# --- step 2: the trials ---------------------------------------------------------

def pairs(dist, band, factory):
    """Every pair of factory presets on every part, with its log ratios (first / second)."""
    out = []
    for p in sorted(dist):
        d = dist[p]
        for c1, c2 in itertools.combinations(sorted(factory), 2):
            vals = [d[k].get(c) for k in ("avg", "true", "swap") for c in (c1, c2)]
            if any(v is None or v <= 0 for v in vals):
                continue
            lr = {k: math.log(d[k][c1] / d[k][c2]) for k in ("avg", "true", "swap")}
            out.append({"part": p, "band": band[p], "first": c1, "second": c2,
                        "log_ratio": lr, "exposure": d["exposure"]})
    return out


def disagreement(q) -> bool:
    """The average-guitar measure separates the two by >= MARGIN; the true-DI judge
    prefers the other."""
    a, t = q["log_ratio"]["avg"], q["log_ratio"]["true"]
    return abs(a) >= MARGIN and a * t < 0


def swap_agreement(q) -> bool:
    """The average-guitar measure and the swap-DI judge prefer the same one, each by >= MARGIN."""
    a, s = q["log_ratio"]["avg"], q["log_ratio"]["swap"]
    return abs(a) >= MARGIN and abs(s) >= MARGIN and a * s > 0


def counts(pool, qualifies) -> dict:
    q = [x for x in pool if qualifies(x)]
    per_part = {}
    for x in q:
        per_part[x["part"]] = per_part.get(x["part"], 0) + 1
    return {"pairs": len(q), "parts": len(per_part),
            "bands": len({x["band"] for x in q}),
            "exposed_parts": len({x["part"] for x in q if x["exposure"] >= EXPOSED}),
            "selectable_at_2_per_part": sum(min(PER_PART, n) for n in per_part.values())}


def select(cands, n, per_part, used, rng):
    """Up to n pairs, round-robin over bands, each band taking its best fitting pair:
    guitar-exposed parts first, then the largest average-guitar margin; ties by seed."""
    tie = {id(q): rng.random() for q in cands}

    def rank(q):
        return (q["exposure"] < EXPOSED, -abs(q["log_ratio"]["avg"]), tie[id(q)])

    cands = sorted(cands, key=rank)

    def fits(q):
        return (per_part.get(q["part"], 0) < PER_PART
                and (q["part"], q["first"], q["second"]) not in used)

    chosen = []
    while len(chosen) < n:
        best = {}
        for q in cands:
            if fits(q) and q["band"] not in best:
                best[q["band"]] = q
        if not best:
            break
        for band in sorted(best, key=lambda b: rank(best[b])):
            q = next((x for x in cands if x["band"] == band and fits(x)), None)
            if q is None:
                continue
            chosen.append(q)
            per_part[q["part"]] = per_part.get(q["part"], 0) + 1
            used.add((q["part"], q["first"], q["second"]))
            if len(chosen) == n:
                break
    return chosen


def choose(pool):
    """The 24 disagreement trials, the 6 swap trials and which 6 are repeated:
    deterministic in SEED."""
    rng = random.Random(SEED)
    per_part, used = {}, set()
    d = select([q for q in pool if disagreement(q)], DISAGREE, per_part, used, rng)
    s = select([q for q in pool if swap_agreement(q)], SWAP, per_part, used, rng)
    repeated = sorted(rng.sample(range(len(d)), min(REPEATS, len(d))))
    return d, s, repeated


# --- step 3: the audio ------------------------------------------------------------

def excerpt(ref, xa, xb, lag):
    """Half B of the amp track, and the two renders aligned to it as the judge aligns them
    (recording[t] <-> render[t - lag]), trimmed alike to where both renders cover it."""
    start = max(int(HALF_B[0] * SR), lag if lag > 0 else 0)
    end = min(len(ref), int(HALF_B[1] * SR), len(xa) + lag, len(xb) + lag)
    return ref[start:end], xa[start - lag:end - lag], xb[start - lag:end - lag]


def fade(x):
    import numpy as np

    n = int(round(FADE_S * SR))
    ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))
    y = x.copy()
    y[:n] *= ramp
    y[-n:] *= ramp[::-1]
    return y


def level(clips):
    """Each clip to one integrated loudness (EBU R128), one static gain each, the shared
    target lowered for every clip of the test if any would peak above the ceiling."""
    from analysis import io
    from build_rab_audition import _static_gain_to_lufs

    audios = [io.from_samples(c.reshape(-1, 1), SR) for c in clips]
    before = [io.loudness_lufs(a) for a in audios]
    if any(b is None for b in before):
        die("a clip has no measurable loudness")
    target = TARGET_LUFS
    for _ in range(12):
        out = [_static_gain_to_lufs(a, target, b) for a, b in zip(audios, before)]
        peak = max(io.true_peak_dbtp(o[1]) for o in out)
        if peak <= PEAK_CEILING_DBTP + 0.01:
            return target, [o[1].samples[:, 0] for o in out], [o[2] for o in out]
        target -= peak - PEAK_CEILING_DBTP
    die("could not meet the peak ceiling")


def write(path, x):
    import soundfile as sf

    sf.write(str(path), x, SR, subtype="PCM_24")


def montage(r, a, b):
    import numpy as np

    gap, cycle = np.zeros(int(GAP_S * SR)), np.zeros(int(CYCLE_GAP_S * SR))
    return np.concatenate([r, gap, a, gap, b, cycle, r, gap, a, gap, b])


# --- build -------------------------------------------------------------------------

def order(d, s, repeated, rng):
    """Two sittings of 18: the repeated trials' originals in the first, their repeats in
    the second, the swap trials 3 and 3; no part twice in a row within a sitting."""
    originals = [("disagreement", i) for i in repeated]
    others = [("disagreement", i) for i in range(len(d)) if i not in repeated]
    rng.shuffle(others)
    swaps = [("swap", i) for i in range(len(s))]
    rng.shuffle(swaps)
    half = len(swaps) // 2
    first = originals + others[:SITTING - len(originals) - half] + swaps[:half]
    second = (others[SITTING - len(originals) - half:] + swaps[half:]
              + [("repeat", i) for i in repeated])

    def part(t):
        return (s if t[0] == "swap" else d)[t[1]]["part"]

    for block in (first, second):
        for _ in range(10000):
            rng.shuffle(block)
            if all(part(x) != part(y) for x, y in zip(block, block[1:])):
                break
    return first, second


def build(args):
    import secrets

    import numpy as np

    parts, band, lags, factory, files = k1()
    dist = distances()
    pool = pairs(dist, band, factory)
    d, s, repeated = choose(pool)
    cd, cs = counts(pool, disagreement), counts(pool, swap_agreement)
    if len(d) < DISAGREE or len(s) < SWAP:
        die(f"only {len(d)} disagreement and {len(s)} swap trials can be chosen as declared "
            f"(qualifying: {cd} / {cs}); amend the plan, do not lower the bar here")
    listen, private = OUT / "listen", OUT / "private"
    for folder in (listen, private):
        if folder.exists() and any(folder.iterdir()):
            die(f"{folder} is not empty; the trials are built once")
        folder.mkdir(parents=True, exist_ok=True)
    rng = secrets.SystemRandom()
    first, second = order(d, s, repeated, rng)
    # The measure's option is A on exactly half the disagreement and half the swap trials;
    # a repeat plays its original with A and B swapped.
    measure_a = {("disagreement", i) for i in rng.sample(range(len(d)), len(d) // 2)}
    measure_a |= {("swap", i) for i in rng.sample(range(len(s)), len(s) // 2)}
    rows = []
    for sitting, block in ((1, first), (2, second)):
        for kind, i in block:
            q = (s if kind == "swap" else d)[i]
            measure = q["first"] if q["log_ratio"]["avg"] < 0 else q["second"]
            other = q["second"] if measure == q["first"] else q["first"]
            a_is_measure = ((kind, i) in measure_a if kind != "repeat"
                            else ("disagreement", i) not in measure_a)
            rows.append({"trial": len(rows) + 1, "sitting": sitting, "kind": kind,
                         "of": f"d{i:02d}" if kind == "repeat" else None,
                         "id": f"d{i:02d}" if kind == "disagreement" else
                         (f"s{i:02d}" if kind == "swap" else f"r{i:02d}"),
                         "part": q["part"], "band": q["band"], "lag": lags[q["part"]],
                         "exposure": q["exposure"],
                         "A": measure if a_is_measure else other,
                         "B": other if a_is_measure else measure,
                         "measure_pick": "A" if a_is_measure else "B",
                         "true_judge_pick": None, "swap_judge_pick": None,
                         "log_ratio_A_over_B": None, "_q": q})
    for r in rows:
        q = r.pop("_q")
        sign = 1 if r["A"] == q["first"] else -1
        r["log_ratio_A_over_B"] = {k: sign * v for k, v in q["log_ratio"].items()}
        r["true_judge_pick"] = "A" if r["log_ratio_A_over_B"]["true"] < 0 else "B"
        r["swap_judge_pick"] = "A" if r["log_ratio_A_over_B"]["swap"] < 0 else "B"
        if r["kind"] != "repeat":
            r.pop("of")
    clips, sources = [], []
    for r in rows:
        variant = "swap" if r["kind"] == "swap" else "avg"
        ref_path = CROPS / r["part"] / "reference.wav"
        paths = {"R": ref_path, "A": render_path(variant, r["part"], r["A"]),
                 "B": render_path(variant, r["part"], r["B"])}
        rr, aa, bb = excerpt(mono(paths["R"]), mono(paths["A"]), mono(paths["B"]), r["lag"])
        clips += [fade(rr), fade(aa), fade(bb)]
        r["sources"] = {k: {"path": str(v), "sha256": sha256(v)} for k, v in paths.items()}
        r["variant"] = variant
        r["excerpt_s"] = len(rr) / SR
    target, levelled, after = level(clips)
    for k, r in enumerate(rows):
        rr, aa, bb = levelled[3 * k: 3 * k + 3]
        n = f"{r['trial']:02d}"
        write(listen / f"trial-{n}.flac", montage(rr, aa, bb))
        for label, x in zip("RAB", (rr, aa, bb)):
            write(listen / f"trial-{n}-{label}.flac", x)
        r["lufs_after"] = dict(zip("RAB", (round(v, 3) for v in after[3 * k: 3 * k + 3])))
    key = {"schema": "avg-measure-listening-key-v1", "plan": PLAN.name, "seed": SEED,
           "margin": MARGIN, "bands": BANDS, "half": HALF_B, "provenance": provenance(),
           "qualifying": {"disagreement": cd, "swap": cs},
           "level": {"target_lufs": round(target, 3), "peak_ceiling_dbtp": PEAK_CEILING_DBTP,
                     "fade_s": FADE_S},
           "trials": rows}
    text = json.dumps(key, indent=1) + "\n"
    (private / "trials.json").write_text(text)
    lines = ["# Answers", "",
             "Each trial plays Reference, A, B, then again. Which of A and B is closer to the",
             "Reference? Write A or B (forced choice). Same headphones and level throughout.",
             "Run the test with: .venv/bin/python -m learn.build_avg_listening take", ""]
    for sitting in (1, 2):
        lines.append(f"## Sitting {sitting}")
        lines += [f"{r['trial']:02d}: " for r in rows if r["sitting"] == sitting]
        lines.append("")
    (listen / "ANSWERS.md").write_text("\n".join(lines))
    print(f"qualifying disagreement pairs: {cd}")
    print(f"qualifying swap pairs: {cs}")
    print(f"built {len(rows)} trials in {listen}; target {target:.2f} LUFS")
    print(f"key sha256 {hashlib.sha256(text.encode()).hexdigest()} (record it in {PLAN.name})")


def count(args):
    parts, band, lags, factory, files = k1()
    pool = pairs(distances(), band, factory)
    d, s, _ = choose(pool)
    print(f"factory pairs: {len(pool)} over {len({q['part'] for q in pool})} parts")
    print(f"disagreement pairs: {counts(pool, disagreement)}; choosable as declared: {len(d)}")
    print(f"swap pairs: {counts(pool, swap_agreement)}; choosable as declared: {len(s)}")


# --- take ---------------------------------------------------------------------------

PHONE_LINE = re.compile(r"\s*sitting\s*(\d+)\s*:(.*)", re.I)


def read_phone_lines(text: str) -> dict:
    """{trial: "A" | "B"} from the phone pages' answer lines ('Sitting 1: 1A 2B ...').

    Strict, because the sheet's hash is committed before scoring and a slip cannot be
    mended afterwards: every non-blank line is a sitting line, every token a trial number
    and A or B, each trial in its own sitting (1 to 18, then 19 to 36), none twice."""
    out = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        m = PHONE_LINE.fullmatch(line)
        if not m:
            raise ValueError(f"not a sitting line: {line!r}")
        sitting = int(m.group(1))
        for token in m.group(2).split():
            t = re.fullmatch(r"(\d+)([AaBb])", token)
            if not t:
                raise ValueError(f"not an answer: {token!r} in {line!r}")
            n = int(t.group(1))
            if not (sitting - 1) * SITTING < n <= sitting * SITTING:
                raise ValueError(f"trial {n} is not in sitting {sitting}")
            if n in out:
                raise ValueError(f"trial {n} is answered twice")
            out[n] = t.group(2).upper()
    return out


def read_sheet(path):
    """{trial: "A" | "B" | None} from `ANSWERS.md`, or from the phone pages' answer lines."""
    text = path.read_text()
    if any(PHONE_LINE.fullmatch(line) for line in text.splitlines()):
        try:
            return read_phone_lines(text)
        except ValueError as e:
            die(f"the answer sheet cannot be read: {e}")
    answers = {}
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s*:\s*([AB])?\s*$", line)
        if m:
            answers[int(m.group(1))] = m.group(2)
    return answers


def write_answer(path, n, answer):
    lines = path.read_text().splitlines()
    for k, line in enumerate(lines):
        if re.match(rf"\s*{n:02d}\s*:", line):
            lines[k] = f"{n:02d}: {answer}"
    path.write_text("\n".join(lines) + "\n")


def play(path):
    proc = subprocess.Popen(["afplay", str(path)])
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print()


def take(args):
    listen = args.listen_dir.expanduser()
    sheet = listen / "ANSWERS.md"
    answers = read_sheet(sheet)
    total = len(answers)
    print(f"{total} trials. Each plays Reference, A, B, twice (about 30 s). Answer A or B.\n"
          "Commands: a / b answer; Enter replays the trial; r, pa, pb play R, A or B alone;\n"
          "q stops (answers so far are kept; run again to resume). Ctrl-C stops playback.")
    for n in sorted(answers):
        if answers[n]:
            continue
        sitting = 1 if n <= SITTING else 2
        if n == SITTING + 1:
            input("\nEnd of sitting 1. Take a break, then press Enter for sitting 2. ")
        print(f"\nTrial {n:02d} of {total} (sitting {sitting})")
        play(listen / f"trial-{n:02d}.flac")
        while True:
            cmd = input("A or B? ").strip().lower()
            if cmd in ("a", "b"):
                write_answer(sheet, n, cmd.upper())
                break
            if cmd == "q":
                print(f"stopped; answers so far are in {sheet}")
                return
            if cmd == "":
                play(listen / f"trial-{n:02d}.flac")
            elif cmd in ("r", "pa", "pb"):
                play(listen / f"trial-{n:02d}-{ {'r': 'R', 'pa': 'A', 'pb': 'B'}[cmd]}.flac")
            else:
                print("a / b to answer; Enter, r, pa, pb to listen; q to stop")
    answers = read_sheet(sheet)
    if all(answers.values()):
        print(f"\nAll {total} answered. Sheet: {sheet}\nsha256 {sha256(sheet)}\n"
              "Commit that hash (docs/avg-measure-listening-answers.sha256) before scoring.")


# --- phone ----------------------------------------------------------------------------

PHONE_KBPS = 160              # mono AAC, as the earlier listening check's phone pages

PHONE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Listening check L, sitting {sitting}</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#fff;
        --on:#1d1d1b; --on-fg:#fff; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#171716; --fg:#ecebe6; --muted:#a19f97;
  --line:#34332f; --card:#201f1d; --on:#ecebe6; --on-fg:#171716; }} }}
body {{ margin:0; background:var(--bg); color:var(--fg);
        font:16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
main {{ max-width:760px; margin:0 auto; padding:24px 16px 48px; }}
section {{ border:1px solid var(--line); border-radius:10px; background:var(--card);
           padding:12px 16px; margin:16px 0; }}
h2 {{ font-size:1.05rem; margin:0 0 4px; }}
.cue {{ color:var(--muted); margin:0 0 8px; min-height:1.5em; }}
.row {{ display:grid; grid-template-columns:3.5rem 1fr; align-items:center; gap:8px;
        margin:6px 0; }}
audio {{ width:100%; height:40px; }}
.pick {{ display:flex; gap:8px; margin-top:10px; }}
.pick button {{ flex:1; padding:10px 0; font:inherit; border:1px solid var(--line);
               border-radius:8px; background:var(--bg); color:var(--fg); }}
.pick button[aria-pressed="true"] {{ background:var(--on); color:var(--on-fg); }}
#sheet {{ position:sticky; bottom:0; background:var(--card); border-top:1px solid var(--line);
          padding:12px 16px; }}
#line {{ width:100%; box-sizing:border-box; font:15px ui-monospace, monospace; padding:8px;
         border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--fg); }}
#copy, #clear {{ margin-top:8px; padding:10px 16px; font:inherit; border-radius:8px;
                border:1px solid var(--line); background:var(--on); color:var(--on-fg); }}
#clear {{ background:var(--bg); color:var(--fg); }}
</style></head><body><main>
<h1>Listening check L, sitting {sitting}</h1>
<p>For each trial, play <b>Trial</b>: it plays the Reference, then A, then B, and then
all three again (about 30 s). Which of A and B is closer to the Reference? Tap A or B;
you must choose one. To listen again, play Trial again, or R, A or B alone. Use the same
headphones and level throughout{brk}. The line at the bottom fills in as you go; when all
{count} are answered, copy it and send it.</p>
{trials}
</main>
<div id="sheet"><input id="line" readonly aria-label="Your answer line">
<button id="copy" type="button">Copy answer line</button>
<button id="clear" type="button">Clear answers</button></div>
<script>
const SITTING = {sitting}, FIRST = {first}, LAST = {last};
const KEY = "avg-{build}-sitting-" + SITTING;
let answers = {{}};
try {{ answers = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{}}
function render() {{
  document.querySelectorAll(".pick").forEach(group => {{
    const n = group.dataset.trial;
    group.querySelectorAll("button").forEach(b =>
      b.setAttribute("aria-pressed", String(answers[n] === b.dataset.value)));
  }});
  const parts = [];
  for (let n = FIRST; n <= LAST; n++) if (answers[n]) parts.push(n + answers[n]);
  const left = LAST - FIRST + 1 - parts.length;
  document.getElementById("line").value = "Sitting " + SITTING + ": " + parts.join(" ") +
    (left ? "   (" + left + " left)" : "");
}}
document.querySelectorAll(".pick button").forEach(b => b.addEventListener("click", () => {{
  answers[b.parentElement.dataset.trial] = b.dataset.value;
  try {{ localStorage.setItem(KEY, JSON.stringify(answers)); }} catch (e) {{}}
  render();
}}));
document.querySelectorAll("audio").forEach(a => a.addEventListener("play", () =>
  document.querySelectorAll("audio").forEach(o => {{ if (o !== a) o.pause(); }})));
// The trial file is R, gap, A, gap, B, longer gap, then again: name what is playing.
document.querySelectorAll("audio.trial").forEach(a => {{
  const cue = a.closest("section").querySelector(".cue");
  const len = Number(a.dataset.clip), gap = {gap}, cycle = {cycle};
  const at = t => {{
    for (let k = 0; k < 2; k++) {{
      const start = k * (3 * len + 2 * gap + cycle);
      for (let i = 0; i < 3; i++) {{
        const s = start + i * (len + gap);
        if (t >= s && t < s + len) return "Now playing: " + "RAB"[i] + (k ? " (again)" : "");
      }}
    }}
    return "";
  }};
  a.addEventListener("timeupdate", () => {{ cue.textContent = a.paused ? "" : at(a.currentTime); }});
  ["pause", "ended"].forEach(e => a.addEventListener(e, () => {{ cue.textContent = ""; }}));
}});
document.getElementById("clear").addEventListener("click", () => {{
  if (!confirm("Clear every answer on this page?")) return;
  answers = {{}};
  try {{ localStorage.removeItem(KEY); }} catch (e) {{}}
  render();
}});
document.getElementById("copy").addEventListener("click", async () => {{
  const line = document.getElementById("line");
  try {{ await navigator.clipboard.writeText(line.value); }}
  catch (e) {{ line.select(); document.execCommand("copy"); }}
}});
render();
</script></body></html>
"""


def public_trials(listen) -> dict:
    """{trial: sitting} from the listener's folder alone: the numbered trial files, the
    first SITTING trials in sitting 1 (as `take` and `ANSWERS.md` have them)."""
    found = sorted(int(m.group(1)) for f in listen.glob("trial-*.flac")
                   if (m := re.fullmatch(r"trial-(\d+)\.flac", f.name)))
    return {n: 1 if n <= SITTING else 2 for n in found}


def aac_data_uri(path, tmp) -> str:
    import base64

    encoded = pathlib.Path(tmp) / "clip.m4a"
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", str(PHONE_KBPS * 1000),
                    str(path), str(encoded)], check=True)
    return "data:audio/mp4;base64," + base64.b64encode(encoded.read_bytes()).decode()


def phone_leaks(page: str) -> list:
    """Names the page must not hold: any factory preset, part or amp, in its text or in
    any embedded clip (the names come from the panel, not the key)."""
    import base64

    parts, _, _, names, _ = k1()
    words = (set(parts) | {p.split("-")[1].replace("_", " ") for p in parts}
             | {seg for n in names for seg in n.split(":", 1)[-1].split("/")
                if seg != "Artists"})
    text_only = re.compile("|".join([r"\bAC20\b", r"\bPR12\b", r"\bSW50R\b", r"\.xml",
                                     "factory", r"template\+R", r"\bmeasure\b"]
                                    + [re.escape(w) for w in sorted(words)]), re.I)
    payloads = re.findall(r"base64,([A-Za-z0-9+/=]+)", page)
    bad = sorted(set(text_only.findall(re.sub(r"base64,[A-Za-z0-9+/=]+", "", page))))
    # Clips are binary: only the long names are looked for, where chance cannot match.
    binary = re.compile("|".join(re.escape(w) for w in sorted(words) if len(w) >= 6).encode(),
                        re.I)
    for p in payloads:
        bad += sorted({m.decode(errors="replace") for m in binary.findall(base64.b64decode(p))})
    return bad


def phone(args):
    import tempfile

    import soundfile as sf

    listen = args.listen_dir.expanduser()
    trials = public_trials(listen)
    if not trials:
        die(f"no trial files in {listen}")
    for sitting in args.sitting or sorted(set(trials.values())):
        numbers = sorted(n for n, s in trials.items() if s == sitting)
        files = [listen / f"trial-{n:02d}{x}.flac" for n in numbers for x in ("", "-R", "-A", "-B")]
        # Answers are kept in the browser per build of these clips and per sitting, so a
        # page of another build never opens pre-answered.
        build_id = hashlib.sha256("".join(sha256(f) for f in files).encode()).hexdigest()[:12]
        sections = []
        with tempfile.TemporaryDirectory() as tmp:
            for n in numbers:
                clip_s = sf.info(str(listen / f"trial-{n:02d}-R.flac")).frames / SR
                rows = [f'<div class="row"><b>Trial</b><audio class="trial" controls '
                        f'preload="none" data-clip="{clip_s:.4f}" '
                        f'src="{aac_data_uri(listen / f"trial-{n:02d}.flac", tmp)}"></audio></div>']
                rows += [f'<div class="row"><b>{x}</b><audio controls preload="none" '
                         f'src="{aac_data_uri(listen / f"trial-{n:02d}-{x}.flac", tmp)}">'
                         f'</audio></div>' for x in "RAB"]
                buttons = "".join(f'<button type="button" data-value="{x}">{x}</button>'
                                  for x in "AB")
                sections.append(f'<section><h2>Trial {n}</h2><p class="cue"></p>'
                                f'{"".join(rows)}<div class="pick" data-trial="{n}">'
                                f'{buttons}</div></section>')
        page = PHONE.format(sitting=sitting, first=numbers[0], last=numbers[-1],
                            count=len(numbers), build=build_id, gap=GAP_S, cycle=CYCLE_GAP_S,
                            brk=", with a break between the sittings" if sitting == 1 else "",
                            trials="\n".join(sections))
        leaks = phone_leaks(page)
        if leaks:
            die(f"the sitting {sitting} page names what it must not: {leaks}")
        out = listen / f"sitting-{sitting}-phone.html"
        out.write_text(page)
        print(f"{out} ({out.stat().st_size / 1e6:.1f} MB, {len(numbers)} trials, "
              f"AAC {PHONE_KBPS} kbps mono); sha256 {sha256(out)}")


def check(args):
    """Whether a sheet can be scored, from the listener's folder alone (never the key):
    run before its hash is committed, so a slip is mended while it still can be."""
    sheet = args.answers.expanduser()
    answers = read_sheet(sheet)
    shown = public_trials(OUT / "listen")
    missing = sorted(set(shown) - {n for n, a in answers.items() if a})
    extra = sorted(set(answers) - set(shown))
    if missing or extra:
        die(f"the sheet does not answer exactly the built trials: missing {missing}, "
            f"extra {extra}")
    print(f"the sheet answers all {len(shown)} trials; its sha256 is {sha256(sheet)}")


# --- score ----------------------------------------------------------------------------

def declared_key_sha256() -> str:
    found = re.findall(r"`([0-9a-f]{64})`", PLAN.read_text())
    if len(found) != 1:
        die(f"{PLAN} must record exactly one key sha256")
    return found[0]


def binomial_p(k: int, n: int) -> float:
    """One-sided P(X >= k) for X ~ Binomial(n, 0.5)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0


def score_rows(rows, answers) -> dict:
    chosen = {r["trial"]: r[answers[r["trial"]]] for r in rows}
    agree = {r["trial"]: answers[r["trial"]] == r["measure_pick"] for r in rows}
    dis = [r for r in rows if r["kind"] == "disagreement"]
    swp = [r for r in rows if r["kind"] == "swap"]
    by_id = {r["id"]: r for r in rows}
    repeats = []
    for r in rows:
        if r["kind"] == "repeat":
            original = by_id[r["of"]]
            repeats.append({"of": r["of"], "same": chosen[r["trial"]] == chosen[original["trial"]]})
    k, consistent = sum(agree[r["trial"]] for r in dis), sum(x["same"] for x in repeats)
    if consistent < MIN_CONSISTENT:
        outcome = "void"
    elif k >= PASS_AGREE:
        outcome = "passed"
    else:
        outcome = "failed"
    return {"outcome": outcome,
            "disagreement": {"agree_with_measure": k, "of": len(dis),
                             "agree_with_true_di_judge": len(dis) - k,
                             "p_one_sided": binomial_p(k, len(dis)),
                             "by_sitting": {s: sum(agree[r["trial"]] for r in dis
                                                   if r["sitting"] == s) for s in (1, 2)}},
            "repeats": {"consistent": consistent, "of": len(repeats), "rows": repeats},
            "swap": {"agree_with_measure": sum(agree[r["trial"]] for r in swp), "of": len(swp),
                     "p_one_sided": binomial_p(sum(agree[r["trial"]] for r in swp), len(swp))},
            "answered_A": sum(a == "A" for a in answers.values()),
            "per_trial": [{"trial": r["trial"], "kind": r["kind"], "answer": answers[r["trial"]],
                           "agrees_with_measure": agree[r["trial"]]} for r in rows]}


def score(args):
    private = OUT / "private"
    sheet = args.answers.expanduser()
    raw = sheet.read_bytes()
    answers = read_sheet(sheet)
    if not answers or not all(answers.values()):
        die("every trial needs an answer, A or B")
    if set(answers) != set(public_trials(OUT / "listen")):
        die("the sheet does not answer exactly the built trials (run `check` first)")
    answers_sha = hashlib.sha256(raw).hexdigest()
    committed = PLUGIN_ROOT / "docs" / "avg-measure-listening-answers.sha256"
    if committed.exists() and answers_sha not in committed.read_text():
        die(f"this sheet is not the one whose hash is committed in {committed.name}")
    recorded = private / "answers.sha256"
    if recorded.exists() and recorded.read_text().strip() != answers_sha:
        die("these answers differ from the ones already scored")
    recorded.write_text(answers_sha + "\n")
    # Only now, with the sheet's hash recorded, is the key read.
    text = (private / "trials.json").read_text()
    if hashlib.sha256(text.encode()).hexdigest() != declared_key_sha256():
        die("the key is not the one the plan declares")
    key = json.loads(text)
    if set(answers) != {r["trial"] for r in key["trials"]}:
        die("the sheet's trials are not the built trials")
    out = {"answers_sha256": answers_sha, **score_rows(key["trials"], answers)}
    text = json.dumps(out, indent=1) + "\n"
    print(text)
    if args.json:
        args.json.expanduser().write_text(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("count")
    sub.add_parser("build")
    t = sub.add_parser("take")
    t.add_argument("--listen-dir", type=pathlib.Path, default=OUT / "listen")
    ph = sub.add_parser("phone")
    ph.add_argument("--listen-dir", type=pathlib.Path, default=OUT / "listen")
    ph.add_argument("--sitting", type=int, action="append", choices=(1, 2),
                    help="one sitting's page (default: both)")
    c = sub.add_parser("check")
    c.add_argument("--answers", type=pathlib.Path, default=OUT / "listen" / "ANSWERS.md")
    s = sub.add_parser("score")
    s.add_argument("--answers", type=pathlib.Path, default=OUT / "listen" / "ANSWERS.md")
    s.add_argument("--json", type=pathlib.Path, default=OUT / "score.json")
    args = ap.parse_args()
    if args.cmd in ("count", "build"):
        from analysis import require

        require("the average-measure listening check")
    {"count": count, "build": build, "take": take, "phone": phone, "check": check,
     "score": score}[args.cmd](args)


if __name__ == "__main__":
    guarded(main)
