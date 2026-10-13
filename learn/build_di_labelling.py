#!/usr/bin/env python3
"""Set 6: which MedleyDB raw guitar track is the DI? Labelled by ear.

Declared in `docs/set6-di-labelling-plan.md`, before this page was built.

    .venv/bin/python -m learn.build_di_labelling build --dry-run   # counts only, nothing written
    .venv/bin/python -m learn.build_di_labelling build             # page, private key, key hash
    .venv/bin/python -m learn.build_di_labelling score --answers SHEET   # after the hash is committed
    .venv/bin/python -m learn.build_di_labelling build-validation [--dry-run]   # validation round
    .venv/bin/python -m learn.build_di_labelling score-validation --answers SHEET

**Questions.** One per group of a MedleyDB song's electric-guitar raw tracks proven to be one
performance by set 4's same-take test (the stored waveform test of
`datasets-medleydb/_tools/pairs/`; a pair that passes the envelope test only is not used, as
in `docs/validation-set6.md`). A group is a connected set of same-take pairs. Tracks whose
audio is identical are shown once: byte-identical files (`_tools/files.json`) and files whose
samples are identical (MedleyDB holds copies whose headers differ); the key lists every copy,
and a label applies to all of them. Steven Clark's raw tracks (labelled electric bass) are
left out.

**Hidden checks.** N_CONTROLS development parts whose DI is known from the session's track
names (`di_role_calibration/dev_pairs.json`, sessions of sets 1-2 development and set 3
development only, as `research/set6_di_role_calibration.py` lists them): the DI and every
amp track of the same part that is a same-take pair with it (two microphones preferred),
one part per band, drawn with a fixed seed by the DI -> amp gain class (CONTROL_QUOTA).

**Each question.** The group's tracks as A, B, C..., in an order drawn at build time; one
CLIP_S window where every track of the group plays, chosen from track activity alone
(frame RMS against each track's loudest frame; no spectrum, no tone); every clip at one
loudness (`L.level`, EBU R128). Clips are resampled to 48 kHz and embedded as mono AAC at
KBPS, so sample rate and format say nothing. The page is one self-contained HTML file;
the answer line is "1B 2none 3C ...".

**The key** is `private/key.json`, outside the page folder; its sha256 is committed in
`docs/set6-di-labelling-key.sha256` before the page is sent, and `score` refuses any other
key. The question order and letters are drawn from a seed taken from the system's random
source at build time and stored in the key.

**Score.** The labels are used only if at least MIN_CORRECT of the N_CONTROLS hidden checks
are right (plan, rule 1). A song's label counts only if its labelled DI forms a same-take
pair with another track of the group (rule 2); "none" excludes the group.

Nothing is rendered, measured by the judge or compared in tone: the listener hears raw
guitar tracks only, to say which one is the DI.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import random
import re
import secrets
import subprocess
import sys
import tempfile

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))
sys.path.append(str(PLUGIN_ROOT / "scripts"))

from _cli import die, guarded  # noqa: E402
from learn import build_avg_listening as L  # noqa: E402

HOME = pathlib.Path(os.path.expanduser("~/ndsp-presets"))
MDB = HOME / "references" / "datasets-medleydb"
PAIRS = MDB / "_tools" / "pairs"
FILES = MDB / "_tools" / "files.json"
INVENTORY = MDB / "inventory.json"
DEV_PAIRS = MDB / "_tools" / "di_role_calibration" / "dev_pairs.json"
CALIBRATION = PLUGIN_ROOT / "docs" / "validation-set6-di-calibration.json"
OUT = HOME / "listening" / "di-labelling"
PAGE_DIR = OUT / "page"
PRIVATE = OUT / "private"
KEY = PRIVATE / "key.json"
PAGE = PAGE_DIR / "index.html"
PLAN = PLUGIN_ROOT / "docs" / "set6-di-labelling-plan.md"
KEY_SHA = PLUGIN_ROOT / "docs" / "set6-di-labelling-key.sha256"

SR = L.SR                                   # 48 kHz: every clip, whatever its source rate
CLIP_S = 6.0
KBPS = 128                                  # mono AAC
FRAME, HOP = 2048, 512
ACTIVE_FLOOR_DB = -30.0                     # a frame plays: within 30 dB of the track's loudest
MAX_TRACKS = 5
MIN_ACTIVE = 0.75                           # the window: every track plays in >= 75% of its frames
GUITAR = {"clean electric guitar", "distorted electric guitar"}
EXCLUDED_SONGS = {"StevenClark_Bounty"}     # RAW_01 labelled electric bass
N_CONTROLS, MIN_CORRECT = 6, 5
CONTROL_QUOTA = {"clean": 3, "crunch": 2, "high-gain": 1}
CONTROL_SEED = 20261013
LETTERS = "ABCDE"
QUESTION = ("Which track is the DI (the plain guitar signal before any amp — thin, dry, "
            "no speaker or room)? Answer A/B/C… or none.")
LISTENS, DECIDE_S = 2, 8                    # for the time estimate: each clip twice, 8 s to answer


def sha256(path) -> str:
    return L.sha256(path)


def pcm_sha256(path) -> str:
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="int32", always_2d=True)
    return hashlib.sha256(f"{sr}:{x.shape}".encode() + x.tobytes()).hexdigest()


# --- the MedleyDB groups ------------------------------------------------------------------

def _components(nodes, edges):
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        parent[find(a)] = find(b)
    out = {}
    for n in sorted(nodes):
        out.setdefault(find(n), []).append(n)
    return sorted(out.values())


def medleydb_groups(pcm_cache: dict) -> list:
    """[{song, tracks: {shown_name: {copies, path, ...}}, pairs}], one per same-take group."""
    files = json.loads(FILES.read_text())["files"]
    groups = []
    for f in sorted(PAIRS.glob("*.json")):
        d = json.loads(f.read_text())
        song = d["song"]
        if song in EXCLUDED_SONGS:
            continue
        guitar = {t for t, v in d["tracks"].items() if v["label"] in GUITAR}
        same = [p for p in d["pairs"] if p["waveform_pass"] and p["x"] in guitar and p["y"] in guitar]
        for comp in _components({t for p in same for t in (p["x"], p["y"])},
                                [(p["x"], p["y"]) for p in same]):
            # Identical audio is shown once: the file hash first, then the samples.
            by_audio = {}
            for t in comp:
                rel = d["tracks"][t]["file"]
                fsha = files[rel]["sha256"]
                key = pcm_cache.get(fsha)
                if key is None:
                    key = pcm_cache[fsha] = pcm_sha256(MDB / rel)
                by_audio.setdefault(key, []).append(t)
            tracks = {}
            for key, copies in sorted(by_audio.items(), key=lambda kv: sorted(kv[1])[0]):
                shown = sorted(copies)[0]
                rel = d["tracks"][shown]["file"]
                tracks[shown] = {"copies": sorted(copies), "path": str(MDB / rel),
                                 "file_sha256": {c: files[d["tracks"][c]["file"]]["sha256"]
                                                 for c in sorted(copies)},
                                 "pcm_sha256": key, "label": d["tracks"][shown]["label"],
                                 "stem": d["tracks"][shown]["stem"]}
            if len(tracks) < 2:
                continue        # copies of one recording only: nothing to tell apart
            groups.append({"kind": "song", "song": song, "source": f"medleydb/{d['dir']}",
                           "tracks": tracks,
                           "pairs": [{"x": p["x"], "y": p["y"],
                                      "lag_samples": p["waveform"]["median_lag_samples"],
                                      "windows": p["waveform"]["windows"],
                                      "peak_to_sidelobe": p["waveform"]["median_peak_to_sidelobe"]}
                                     for p in same if p["x"] in comp]})
    return groups


# --- the hidden checks --------------------------------------------------------------------

def control_candidates() -> list:
    """Development parts with a known DI and its same-take amp tracks, as groups."""
    from set6_di_role_calibration import development_sessions

    dev = {s["key"]: s for s in development_sessions()}
    out = []
    for s in json.loads(DEV_PAIRS.read_text())["sessions"]:
        if s["key"] not in dev:
            die(f"{s['key']} is not a development session; the checks use development data only")
        root = pathlib.Path(dev[s["key"]]["root"])
        same = [p for p in s["pairs"] if p["same_take"]]
        parts = {}
        for p in same:
            for t, role in ((p["a"], p["role_a"]), (p["b"], p["role_b"])):
                parts.setdefault(role[1], {}).setdefault(role[0], set()).add(t)
        for part, roles in sorted(parts.items()):
            dis = sorted(roles.get("di", ()))
            if len(dis) != 1 or "keys" in part.lower():
                continue
            di = dis[0]
            amps, classes = [], []
            for p in same:
                if p["label"] != "di_amp" or di not in (p["a"], p["b"]):
                    continue
                amp, role = (p["b"], p["role_b"]) if p["a"] == di else (p["a"], p["role_a"])
                if role[1] != part:
                    continue
                amps.append(amp)
                classes.append((p["a_as_di"] if p["a"] == di else p["b_as_di"])["gain_class"])
            if not amps or len(set(classes)) != 1:
                continue
            amps = sorted(amps)
            if len(amps) == 2:      # two microphones: they must be one take with each other too
                if not any({p["a"], p["b"]} == set(amps) for p in same):
                    continue
            if len(amps) + 1 > MAX_TRACKS:
                continue
            tracks = {t: {"copies": [t], "path": str(root / t), "file_sha256": {t: None},
                          "role": "di" if t == di else "amp"} for t in [di, *amps]}
            out.append({"kind": "control", "song": s["key"], "band": s["band"], "part": part,
                        "source": s["key"], "gain_class": classes[0], "di": di, "tracks": tracks})
    return out


def choose_controls(cands: list) -> list:
    """CONTROL_QUOTA by gain class, one part per band, two microphones preferred."""
    rng = random.Random(CONTROL_SEED)
    rng.shuffle(cands)
    chosen, bands = [], set()
    for cls, n in CONTROL_QUOTA.items():
        pool = sorted([c for c in cands if c["gain_class"] == cls],
                      key=lambda c: -len(c["tracks"]))          # stable: shuffled within size
        got = 0
        for c in pool:
            if got == n:
                break
            if c["band"] in bands:
                continue
            chosen.append(c)
            bands.add(c["band"])
            got += 1
        if got < n:
            die(f"only {got} {cls} hidden checks in distinct bands; the plan wants {n}")
    return chosen


# --- the window -----------------------------------------------------------------------------

def _mono(path, start=0, frames=-1):
    import numpy as np
    import soundfile as sf

    x, sr = sf.read(str(path), start=start, frames=frames, dtype="float64", always_2d=True)
    return x.mean(axis=1).astype(np.float64), int(sr)


def activity(group):
    """{shown track: frame mask where it plays}, and the sample rate: activity only."""
    from analysis import io

    active, srs = {}, set()
    for name, t in group["tracks"].items():
        x, sr = _mono(t["path"])
        srs.add(sr)
        db = io.frame_rms_db(x, FRAME, HOP)
        active[name] = db > db.max() + ACTIVE_FLOOR_DB
    if len(srs) != 1:
        die(f"{group['song']}: the group's tracks differ in sample rate")
    return active, srs.pop()


def best_window(active, names, sr):
    """The CLIP_S window where every named track plays most; the middle one of equals."""
    import numpy as np

    n = min(len(active[t]) for t in names)
    every = np.all([active[t][:n] for t in names], axis=0).astype(float)
    w = int(round(CLIP_S * sr / HOP))
    if n < w:
        die("a track is shorter than one clip")
    frac = np.convolve(every, np.ones(w), "valid") / w
    best = frac.max()
    ties = np.flatnonzero(frac >= best - 1e-9)
    k = int(ties[len(ties) // 2])
    return {"sample_rate": sr, "start_s": round(k * HOP / sr, 4),
            "all_active_fraction": round(float(best), 4),
            "per_track_active_fraction": {t: round(float(active[t][k:k + w].mean()), 4) for t in names}}


def windowed(group) -> list:
    """The group with its window, or, when its tracks never all play together (a chain of
    same-take pairs across sections), the fewest connected subsets that each have a window
    with every track playing, largest first, until every track is in one."""
    import itertools

    active, sr = activity(group)
    names = list(group["tracks"])
    whole = best_window(active, names, sr)
    if whole["all_active_fraction"] >= MIN_ACTIVE:
        return [{**group, "window": whole}]
    shown = {c: name for name, t in group["tracks"].items() for c in t["copies"]}
    edges = {frozenset((shown[p["x"]], shown[p["y"]])) for p in group.get("pairs", [])
             if shown[p["x"]] != shown[p["y"]]}

    def connected(sub):
        seen, todo = {sub[0]}, [sub[0]]
        while todo:
            a = todo.pop()
            for b in sub:
                if b not in seen and frozenset((a, b)) in edges:
                    seen.add(b)
                    todo.append(b)
        return len(seen) == len(sub)

    cands = []
    for size in range(len(names) - 1, 1, -1):
        for sub in itertools.combinations(names, size):
            if connected(sub):
                w = best_window(active, sub, sr)
                if w["all_active_fraction"] >= MIN_ACTIVE:
                    cands.append((sub, w))
    out, covered = [], set()
    for sub, w in sorted(cands, key=lambda c: (-len(c[0]), -c[1]["all_active_fraction"], c[0])):
        if set(sub) <= covered:
            continue
        out.append({**group, "tracks": {t: group["tracks"][t] for t in sub}, "window": w,
                    "subset_of": names})
        covered |= set(sub)
    if covered != set(names):
        die(f"{group['song']}: tracks {sorted(set(names) - covered)} never play with a partner")
    return out


def clip(path, sr, start_s):
    import numpy as np
    from scipy.signal import resample_poly

    x, got = _mono(path, int(round(start_s * sr)), int(round(CLIP_S * sr)))
    if got != sr or len(x) != int(round(CLIP_S * sr)):
        die(f"{path}: could not read the window")
    if sr != SR:
        g = np.gcd(SR, sr)
        x = resample_poly(x, SR // g, sr // g)
    return L.fade(x[: int(round(CLIP_S * SR))])


# --- the page -------------------------------------------------------------------------------

PAGE_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Which track is the DI?</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#fff;
        --on:#1d1d1b; --on-fg:#fff; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#171716; --fg:#ecebe6; --muted:#a19f97;
  --line:#34332f; --card:#201f1d; --on:#ecebe6; --on-fg:#171716; }} }}
body {{ margin:0; background:var(--bg); color:var(--fg);
        font:16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
main {{ max-width:760px; margin:0 auto; padding:24px 16px 140px; }}
section {{ border:1px solid var(--line); border-radius:10px; background:var(--card);
           padding:12px 16px; margin:16px 0; }}
h2 {{ font-size:1.05rem; margin:0 0 4px; }}
.q {{ color:var(--muted); margin:0 0 8px; font-size:.95rem; }}
.row {{ display:grid; grid-template-columns:2rem 1fr; align-items:center; gap:8px; margin:6px 0; }}
audio {{ width:100%; height:40px; }}
.pick {{ display:flex; gap:6px; margin-top:10px; }}
.pick button {{ flex:1; padding:10px 0; font:inherit; border:1px solid var(--line);
               border-radius:8px; background:var(--bg); color:var(--fg); }}
.pick button[aria-pressed="true"] {{ background:var(--on); color:var(--on-fg); }}
#sheet {{ position:fixed; left:0; right:0; bottom:0; background:var(--card);
          border-top:1px solid var(--line); padding:10px 16px; }}
#line {{ width:100%; box-sizing:border-box; font:14px ui-monospace, monospace; padding:8px;
         border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--fg); }}
#copy, #clear {{ margin-top:8px; padding:10px 16px; font:inherit; border-radius:8px;
                border:1px solid var(--line); background:var(--on); color:var(--on-fg); }}
#clear {{ background:var(--bg); color:var(--fg); }}
</style></head><body><main>
<h1>Which track is the DI?</h1>
<p>{count} questions, about {minutes} minutes; you can stop and come back, answers stay in
this browser. Each question has two to five clips of one guitar part, recorded at the same
moment through different paths, all at the same loudness. One of them may be the DI, as
each question describes. Tap the DI's letter, or <b>none</b> if no clip is a DI or you are
not sure. Use headphones, at one level
throughout. When every question is answered, copy the line at the bottom and send it.</p>
{questions}
</main>
<div id="sheet"><input id="line" readonly aria-label="Your answer line">
<button id="copy" type="button">Copy answer line</button>
<button id="clear" type="button">Clear answers</button></div>
<script>
const COUNT = {count};
const KEY = "dilabel-{build}";
let answers = {{}};
try {{ answers = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{}}
function render() {{
  document.querySelectorAll(".pick").forEach(group => {{
    const n = group.dataset.q;
    group.querySelectorAll("button").forEach(b =>
      b.setAttribute("aria-pressed", String(answers[n] === b.dataset.value)));
  }});
  const parts = [];
  for (let n = 1; n <= COUNT; n++) if (answers[n]) parts.push(n + answers[n]);
  const left = COUNT - parts.length;
  document.getElementById("line").value = "DI labelling: " + parts.join(" ") +
    (left ? "   (" + left + " left)" : "");
}}
document.querySelectorAll(".pick button").forEach(b => b.addEventListener("click", () => {{
  answers[b.parentElement.dataset.q] = b.dataset.value;
  try {{ localStorage.setItem(KEY, JSON.stringify(answers)); }} catch (e) {{}}
  render();
}}));
document.querySelectorAll("audio").forEach(a => a.addEventListener("play", () =>
  document.querySelectorAll("audio").forEach(o => {{ if (o !== a) o.pause(); }})));
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


def aac(wav: pathlib.Path) -> bytes:
    out = wav.with_suffix(".m4a")
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", str(KBPS * 1000), str(wav), str(out)],
                   check=True)
    return out.read_bytes()


def section(n, letters, payloads) -> str:
    rows = "".join(f'<div class="row"><b>{x}</b><audio controls preload="none" '
                   f'src="data:audio/mp4;base64,{base64.b64encode(p).decode()}"></audio></div>'
                   for x, p in zip(letters, payloads))
    buttons = "".join(f'<button type="button" data-value="{x}">{x}</button>' for x in letters)
    buttons += '<button type="button" data-value="none">none</button>'
    return (f'<section><h2>Question {n}</h2><p class="q">{QUESTION}</p>{rows}'
            f'<div class="pick" data-q="{n}">{buttons}</div></section>')


def leak_words(groups) -> set:
    """Everything that could name a song, a band, a session, a part or a track's role."""
    words = set()
    for g in groups:
        words |= {g["song"], *re.split(r"[/_]", g["song"]), *re.split(r"[/_ ]", g["source"])}
        if g.get("band"):
            words.add(g["band"])
        for name, t in g["tracks"].items():
            for c in t["copies"]:
                stem = pathlib.Path(c).stem
                words |= {c, stem, *re.split(r"[/_ .\-]", stem)}
            words.add(pathlib.Path(t["path"]).name)
    words |= {"RAW", "STEM", "ElecGtr", "Amp", "Mic", "TDP", "M80", "TF11", "TF51", "M81",
              "directinput", "micamp", "Close", "Far", "control", "hidden", "check", "medleydb",
              "cambridge", "telefunken", "techs", "set3", "sets12", "Weathervane", "wav"}
    return {w for w in words if len(w) >= 3 and not w.isdigit()}


def phone_leaks(page: str, words: set) -> list:
    """Names the page must not hold, in its text (with the question's own words set aside)
    or in any embedded clip."""
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", page).replace(QUESTION, "")
    allowed = {"the", "and", "are", "one", "two", "DI", "audio"}    # "audio": the HTML tag
    pat = re.compile("|".join(r"\b" + re.escape(w) + r"\b"
                              for w in sorted(words - allowed, key=len, reverse=True)), re.I)
    bad = sorted(set(pat.findall(text)))
    binary = re.compile("|".join(re.escape(w) for w in sorted(words) if len(w) >= 6).encode(), re.I)
    for p in re.findall(r"base64,([A-Za-z0-9+/=]+)", page):
        bad += sorted({m.decode(errors="replace") for m in binary.findall(base64.b64decode(p))})
    return bad


def minutes(groups) -> int:
    s = sum(len(g["tracks"]) * CLIP_S * LISTENS + DECIDE_S for g in groups)
    return int(round(s / 60))


def provenance() -> dict:
    return {"plan": sha256(PLAN), "files_json": sha256(FILES), "inventory": sha256(INVENTORY),
            "dev_pairs": sha256(DEV_PAIRS), "calibration": sha256(CALIBRATION),
            "pairs": {f.name: sha256(f) for f in sorted(PAIRS.glob("*.json"))}}


def build(args):
    from analysis import require

    require("the DI-labelling page")
    if not args.dry_run:
        for folder in (PAGE_DIR, PRIVATE):
            if folder.exists() and any(folder.iterdir()):
                die(f"{folder} is not empty; the page is built once")
    cache_path = OUT / ".pcm_sha256.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    songs = medleydb_groups(cache)
    OUT.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=1) + "\n")
    big = [(g["song"], list(g["tracks"])) for g in songs if len(g["tracks"]) > MAX_TRACKS]
    if big:
        die(f"groups above {MAX_TRACKS} tracks after identical audio is collapsed: {big}")
    controls = choose_controls(control_candidates())
    groups = songs + controls
    songs = [w for g in songs for w in windowed(g)]
    controls = [w for g in controls for w in windowed(g)]
    groups = songs + controls
    weak = [(g["song"], g["window"]["all_active_fraction"]) for g in groups
            if g["window"]["all_active_fraction"] < 0.9]
    n_tracks = sum(len(g["tracks"]) for g in groups)
    print(f"{len(songs)} song groups from {len({g['song'] for g in songs})} songs "
          f"({sum(len(g['tracks']) for g in songs)} tracks; sizes "
          f"{sorted(len(g['tracks']) for g in songs)}), {len(controls)} hidden checks "
          f"({', '.join(c['gain_class'] + ' ' + str(len(c['tracks'])) for c in controls)}); "
          f"{n_tracks} clips; about {minutes(groups)} min")
    print("all-tracks-active fraction of the chosen windows: min "
          f"{min(g['window']['all_active_fraction'] for g in groups):.2f}; below 0.9: {weak}; split groups: {sorted({g['song'] for g in groups if g.get('subset_of')})}")
    if args.dry_run:
        return
    seed = secrets.randbits(64)
    rng = random.Random(seed)
    rng.shuffle(groups)
    rows, clips = [], []
    for n, g in enumerate(groups, 1):
        names = list(g["tracks"])
        rng.shuffle(names)
        letters = LETTERS[: len(names)]
        sr, start = g["window"]["sample_rate"], g["window"]["start_s"]
        for name in names:
            clips.append(clip(g["tracks"][name]["path"], sr, start))
            t = g["tracks"][name]
            if t["file_sha256"].get(name) is None:
                t["file_sha256"] = {name: sha256(t["path"])}
        row = {"question": n, "kind": g["kind"], "song": g["song"], "source": g["source"],
               "letters": dict(zip(letters, names)), "tracks": g["tracks"], "window": g["window"],
               "clip_s": CLIP_S}
        if g["kind"] == "control":
            row.update({"band": g["band"], "part": g["part"], "gain_class": g["gain_class"],
                        "answer": letters[names.index(g["di"])]})
        else:
            row["pairs"] = g["pairs"]
            if g.get("subset_of"):
                row["subset_of"] = g["subset_of"]
        rows.append(row)
    target, levelled, after = L.level(clips)
    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    sections, k = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for r in rows:
            payloads = []
            for x in r["letters"]:
                wav = pathlib.Path(tmp) / f"clip-{k:03d}.wav"
                L.write(wav, levelled[k])
                payloads.append(aac(wav))
                r.setdefault("lufs_after", {})[x] = round(after[k], 3)
                k += 1
            sections.append(section(r["question"], list(r["letters"]), payloads))
    build_id = secrets.token_hex(6)
    page = PAGE_HTML.format(count=len(rows), minutes=minutes(groups), build=build_id,
                            questions="\n".join(sections))
    leaks = phone_leaks(page, leak_words(groups))
    if leaks:
        die(f"the page names what it must not: {leaks[:20]}")
    PAGE.write_text(page)
    stray = [p.name for p in PAGE_DIR.iterdir() if p.name != PAGE.name]
    if stray:
        die(f"the page folder holds more than the page: {stray}")
    key = {"schema": "set6-di-labelling-key-v1", "plan": PLAN.name, "seed": seed,
           "control_seed": CONTROL_SEED, "control_quota": CONTROL_QUOTA,
           "min_correct": MIN_CORRECT, "clip_s": CLIP_S, "active_floor_db": ACTIVE_FLOOR_DB,
           "frame": FRAME, "hop": HOP, "sample_rate": SR, "aac_kbps": KBPS,
           "level": {"target_lufs": round(target, 3), "peak_ceiling_dbtp": L.PEAK_CEILING_DBTP,
                     "fade_s": L.FADE_S},
           "page_sha256": hashlib.sha256(page.encode()).hexdigest(), "build_id": build_id,
           "provenance": provenance(), "questions": rows}
    text = json.dumps(key, indent=1) + "\n"
    KEY.write_text(text)
    key_sha = hashlib.sha256(text.encode()).hexdigest()
    KEY_SHA.write_text(f"{key_sha}  key.json\n{key['page_sha256']}  index.html\n")
    print(f"page {PAGE} ({PAGE.stat().st_size / 1e6:.1f} MB, {len(rows)} questions, "
          f"AAC {KBPS} kbps mono); target {target:.2f} LUFS")
    print(f"key {KEY}\nkey sha256 {key_sha} (written to {KEY_SHA.relative_to(PLUGIN_ROOT)}; "
          "commit it before the page is sent)")


# --- score ------------------------------------------------------------------------------------

ANSWER = re.compile(r"(?<![\d])(\d{1,3})\s*(none|[A-E])\b", re.I)


def read_answers(text: str) -> dict:
    out = {}
    for n, a in ANSWER.findall(text):
        n, a = int(n), ("none" if a.lower() == "none" else a.upper())
        if n in out and out[n] != a:
            die(f"question {n} is answered twice, differently")
        out[n] = a
    return out


def declared_key_sha256() -> str:
    found = re.findall(r"^([0-9a-f]{64})\s+key\.json$", KEY_SHA.read_text(), re.M)
    if len(found) != 1:
        die(f"{KEY_SHA} must record exactly one key sha256")
    return found[0]


def score_rows(rows, answers) -> dict:
    controls = [r for r in rows if r["kind"] == "control"]
    right = sum(answers[r["question"]] == r["answer"] for r in controls)
    usable = right >= MIN_CORRECT
    labels = []
    for r in rows:
        if r["kind"] != "song":
            continue
        a = answers[r["question"]]
        entry = {"question": r["question"], "song": r["song"], "answer": a,
                 "tracks": {x: r["tracks"][t]["copies"] for x, t in r["letters"].items()}}
        if a == "none":
            entry.update({"di": None, "counts": False, "reason": "none / not sure"})
        elif a not in r["letters"]:
            entry.update({"di": None, "counts": False, "reason": f"no track {a} in this question"})
        else:
            di = r["letters"][a]
            copies = set(r["tracks"][di]["copies"])
            partners = sorted({p["y"] if p["x"] in copies else p["x"] for p in r["pairs"]
                               if (p["x"] in copies) != (p["y"] in copies)})
            entry.update({"di": di, "di_copies": sorted(copies), "same_take_partners": partners,
                          "counts": bool(partners) and usable,
                          "reason": ("labels unusable: hidden checks failed" if not usable else
                                     "" if partners else "no same-take partner in the group")})
        entry["subset_of"] = r.get("subset_of")
        labels.append(entry)
    # A split group (plan amendment 4): if both halves name a DI, the group is flagged and left out.
    halves = {}
    for e in labels:
        if e["subset_of"]:
            halves.setdefault(tuple(e["subset_of"]), []).append(e)
    for es in halves.values():
        if sum(e["di"] is not None for e in es) > 1:
            for e in es:
                e.update(counts=False, reason="split group: a DI was named in both halves")
    return {"hidden_checks": {"right": right, "of": len(controls), "min_correct": MIN_CORRECT,
                              "per_check": [{"question": r["question"], "answer": answers[r["question"]],
                                             "di": r["answer"], "gain_class": r["gain_class"]}
                                            for r in controls]},
            "labels_usable": usable,
            "songs_counted": sorted({e["song"] for e in labels if e["counts"]}),
            "groups_counted": sum(e["counts"] for e in labels),
            "groups_none": sum(e["answer"] == "none" for e in labels),
            "labels": labels}


def score(args):
    raw = pathlib.Path(args.answers).expanduser().read_bytes() if args.answers else args.line.encode()
    answers = read_answers(raw.decode())
    text = KEY.read_text()
    if hashlib.sha256(text.encode()).hexdigest() != declared_key_sha256():
        die("the key is not the one whose hash was committed")
    key = json.loads(text)
    built = {r["question"] for r in key["questions"]}
    missing, extra = sorted(built - set(answers)), sorted(set(answers) - built)
    if missing or extra:
        die(f"the answers do not cover exactly the built questions: missing {missing}, extra {extra}")
    out = {"schema": "set6-di-labels-v1", "plan": PLAN.name,
           "key_sha256": declared_key_sha256(),
           "answers_sha256": hashlib.sha256(raw).hexdigest(),
           **score_rows(key["questions"], answers)}
    text = json.dumps(out, indent=1) + "\n"
    dest = pathlib.Path(args.json).expanduser()
    dest.write_text(text)
    h = out["hidden_checks"]
    print(f"hidden checks {h['right']}/{h['of']} (need {MIN_CORRECT}): labels "
          f"{'usable' if out['labels_usable'] else 'NOT usable; set 6 stays unusable'}; "
          f"{out['groups_counted']} groups from {len(out['songs_counted'])} songs count; "
          f"{out['groups_none']} answered none. Written to {dest}")


# --- the validation round -----------------------------------------------------------------------
#
# Plan, last section ("Result of the first round, and a validation round"), declared before
# this page was built. Development parts only (the sessions `control_candidates` reads: sets
# 1-2 development and set 3 development), none of the first round's six checks, and none of
# their bands where enough other bands exist.
#
#   * VAL_QUOTA crunch / high-gain questions: a known DI and its same-take amp tracks of one
#     part (as the first round's checks), the class from set 3's classifier (DI -> amp).
#   * N_DECOYS decoys: two or three amp/microphone tracks of one part, same-take with each
#     other by the stored waveform test, NO DI shown; the right answer is "none". A decoy part
#     must read crunch or high-gain for at least one of its DI -> amp pairs, so that decoys
#     sound like the questions.
#   * Selection by VAL_SEED: decoys first, then questions by class; each pass takes a new band
#     first, then a second part of a band already in its own pool, then (only if still short)
#     a first-round band. Decoy bands and question bands never overlap.
#   * Clips exactly as in the first round (CLIP_S window with every track playing in at least
#     MIN_ACTIVE of its frames, one loudness, 48 kHz mono AAC KBPS, order and letters shuffled
#     from a seed stored in the key, no names on the page).
#
# Score (declared): at least VAL_MIN_CONFIDENT confident answers (a letter), at least
# VAL_MIN_SHARE of them right; a letter on a decoy is wrong. If it passes, the first round's
# confident MedleyDB labels count, but only for groups whose gain class (set 3's classifier on
# the reference amp track against the labelled DI, whole tracks, as sets 4 and 5) is crunch or
# high-gain. The reference among the DI's same-take partners: smallest |lag|, then the higher
# peak-to-sidelobe ratio (set 6's rule 4, its reading of set 4/5's "Close" preference; MedleyDB
# names no amp or microphone).

VAL_DIR = OUT / "validation"
VAL_PAGE = VAL_DIR / "index.html"
VAL_KEY = PRIVATE / "validation-key.json"
VAL_KEY_SHA = PLUGIN_ROOT / "docs" / "set6-di-labelling-validation-key.sha256"
VAL_RESULT = OUT / "validation-result.json"
FIRST_ANSWERS = OUT / "answers-2026-10-13.txt"
GAIN_TOOLS = HOME / "references" / "datasets-set4" / "_tools"   # set 3's classify/gainmeasure
VAL_QUOTA = {"crunch": 6, "high-gain": 4}       # majority crunch
N_DECOYS = 4
VAL_SEED = 20261014
VAL_MIN_CONFIDENT, VAL_MIN_SHARE = 8, 0.90
DRIVEN = ("crunch", "high-gain")
VAL_INTRO = "Answer only when you're sure; otherwise choose none."
HF_BAND, HF_COH_MAX = (3000.0, 6000.0), 0.3   # an amp track must differ from its DI above 3 kHz
VAL_PAGE_HTML = (PAGE_HTML
                 .replace("two to five clips", "two clips")
                 .replace("\n{questions}\n", f"\n<p><b>{VAL_INTRO}</b></p>\n{{questions}}\n")
                 .replace('"DI labelling: "', '"DI validation: "')
                 .replace('"dilabel-{build}"', '"dilabel-validation-{build}"'))


def first_round_key() -> dict:
    text = KEY.read_text()
    if hashlib.sha256(text.encode()).hexdigest() != declared_key_sha256():
        die("the first-round key is not the one whose hash was committed")
    return json.loads(text)


def decoy_candidates() -> list:
    """Development parts' same-take groups of amp tracks only (no DI), driven by their DI."""
    from set6_di_role_calibration import development_sessions

    dev = {s["key"]: s for s in development_sessions()}
    out = []
    for s in json.loads(DEV_PAIRS.read_text())["sessions"]:
        if s["key"] not in dev:
            die(f"{s['key']} is not a development session; the decoys use development data only")
        root = pathlib.Path(dev[s["key"]]["root"])
        same = [p for p in s["pairs"] if p["same_take"]]
        amp_amp = [p for p in same if p["label"] == "amp_amp_same_part"]
        for comp in _components({t for p in amp_amp for t in (p["a"], p["b"])},
                                [(p["a"], p["b"]) for p in amp_amp]):
            parts = {p["role_a"][1] for p in amp_amp if p["a"] in comp}
            if len(parts) != 1 or len(comp) > 3:
                continue
            part = parts.pop()
            if "keys" in part.lower():
                continue
            classes = sorted({(p["a_as_di"] if p["role_a"][0] == "di" else p["b_as_di"])["gain_class"]
                              for p in same if p["label"] == "di_amp" and (p["a"] in comp or p["b"] in comp)}
                             - {None})
            if not set(classes) & set(DRIVEN):
                continue
            tracks = {t: {"copies": [t], "path": str(root / t), "file_sha256": {t: None}, "role": "amp"}
                      for t in sorted(comp)}
            out.append({"kind": "decoy", "song": s["key"], "band": s["band"], "part": part,
                        "source": s["key"], "gain_classes": classes, "tracks": tracks})
    return out


def hf_coherence(di_path, amp_path, lag, pol) -> float | None:
    """Mean magnitude-squared coherence DI -> amp over HF_BAND, on the WHOLE tracks: frames
    where both play (within 40 dB of their loudest), amp shifted back by the waveform lag and
    polarity-corrected; set 6 calibration's cue (`oriented_cues`), in this band."""
    import numpy as np

    x, sr = _mono(di_path)
    y, sr_y = _mono(amp_path)
    if sr != sr_y:
        die(f"{amp_path}: sample rate differs from its DI")
    if lag > 0:
        y = y[lag:]
    elif lag < 0:
        y = np.concatenate([np.zeros(-lag), y])
    y = (pol or 1) * y
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    F = 4096 if sr < 60000 else 8192
    H = F // 2
    nf = (n - F) // H + 1
    idx = np.arange(F)[None, :] + H * np.arange(nf)[:, None]
    rx = 20 * np.log10(np.sqrt(np.mean(x[idx] ** 2, axis=1)) + 1e-12)
    ry = 20 * np.log10(np.sqrt(np.mean(y[idx] ** 2, axis=1)) + 1e-12)
    act = np.flatnonzero((rx >= rx.max() - 40) & (ry >= ry.max() - 40))
    if len(act) < 20:
        return None
    w = np.hanning(F)
    Sxx = Syy = 0.0
    Sxy = 0j
    for chunk in np.array_split(act, max(1, len(act) // 500)):
        X = np.fft.rfft(x[idx[chunk]] * w, axis=1)
        Y = np.fft.rfft(y[idx[chunk]] * w, axis=1)
        Sxx = Sxx + (np.abs(X) ** 2).sum(0)
        Syy = Syy + (np.abs(Y) ** 2).sum(0)
        Sxy = Sxy + (Y * np.conj(X)).sum(0)
    f = np.fft.rfftfreq(F, 1 / sr)
    m = (f >= HF_BAND[0]) & (f < HF_BAND[1])
    return float(np.mean(np.abs(Sxy[m]) ** 2 / (Sxx[m] * Syy[m] + 1e-30)))


def _amps_differ(g) -> dict | None:
    """The guard on a known-DI question: every amp track's coherence with the DI over
    HF_BAND (whole tracks) is below HF_COH_MAX. {amp: coherence}, or None if one fails."""
    s = next(s for s in json.loads(DEV_PAIRS.read_text())["sessions"] if s["key"] == g["song"])
    out = {}
    for amp in g["tracks"]:
        if amp == g["di"]:
            continue
        p = next(p for p in s["pairs"] if p["same_take"] and {p["a"], p["b"]} == {g["di"], amp})
        lag = p["waveform"]["median_lag_samples"]           # positive: b later than a
        lag = lag if p["a"] == g["di"] else -lag            # positive: amp later than the DI
        c = hf_coherence(g["tracks"][g["di"]]["path"], g["tracks"][amp]["path"], lag,
                         p["waveform"].get("polarity"))
        out[amp] = None if c is None else round(c, 4)
        if c is None or c >= HF_COH_MAX:
            return None
    return out


def _window_ok(g, cache):
    k = (g["song"], g["part"])
    if k not in cache:
        names = list(g["tracks"])
        if len({pcm_sha256(g["tracks"][t]["path"]) for t in names}) != len(names):
            cache[k] = None                     # identical audio: nothing to tell apart
        else:
            active, sr = activity(g)
            w = best_window(active, names, sr)
            cache[k] = w if w["all_active_fraction"] >= MIN_ACTIVE else None
    return cache[k]


def _pick(pool, n, rng, round1_bands, round1_parts, forbidden, taken, cache, log, guard=None):
    """n groups from pool: a new band first, then another part of a band this pick already
    took (the band with the fewest parts first), then a first-round band; never a forbidden
    band or a first-round part."""
    pool = [g for g in pool if (g["song"], g["part"]) not in round1_parts and g["band"] not in forbidden]
    rng.shuffle(pool)
    pool.sort(key=lambda g: -len(g["tracks"]))           # stable: shuffled within size
    chosen, own = [], set()
    passes = (lambda g: g["band"] not in round1_bands and g["band"] not in taken,
              lambda g: g["band"] not in round1_bands and g["band"] in own,
              lambda g: g["band"] in round1_bands and g["band"] not in taken | own)
    rejected = set()
    for i, ok in enumerate(passes):
        while len(chosen) < n:
            per_band = {}
            for c in chosen:
                per_band[c["band"]] = per_band.get(c["band"], 0) + 1
            done = {(c["song"], c["part"]) for c in chosen} | rejected
            # the band with the fewest parts drawn so far first, then the shuffled order
            elig = sorted((k, g) for k, g in enumerate(pool)
                          if (g["song"], g["part"]) not in done and ok(g)
                          and not (i == 0 and g["band"] in own))
            elig.sort(key=lambda kg: per_band.get(kg[1]["band"], 0))
            if not elig:
                break
            g = elig[0][1]
            w = _window_ok(g, cache)
            if w is None:
                log.append(f"skipped {g['song']} {g['part']}: no window with every track playing")
                rejected.add((g["song"], g["part"]))
                continue
            extra = {}
            if guard is not None:
                gk = ("guard", g["song"], g["part"])
                if gk not in cache:
                    cache[gk] = guard(g)
                if cache[gk] is None:
                    log.append(f"skipped {g['song']} {g['part']}: an amp track is coherent with the DI "
                               f"above 3 kHz (>= {HF_COH_MAX}): no speaker")
                    rejected.add((g["song"], g["part"]))
                    continue
                extra = {"hf_coherence_3_6k": cache[gk]}
            chosen.append({**g, "window": w, "pick_pass": i + 1, **extra})
            own.add(g["band"])
    if len(chosen) < n:
        die(f"only {len(chosen)} of {n} groups could be drawn")
    taken |= own
    return chosen


def validation_groups(round1) -> tuple[list, list]:
    checks = [r for r in round1["questions"] if r["kind"] == "control"]
    round1_bands = {r["band"] for r in checks}
    round1_parts = {(r["song"], r["part"]) for r in checks}
    rng = random.Random(VAL_SEED)
    taken, cache, log = set(), {}, []
    decoys = _pick(decoy_candidates(), N_DECOYS, rng, round1_bands, round1_parts, set(), taken,
                   cache, log)
    decoy_bands = {g["band"] for g in decoys}
    cands = control_candidates()
    questions = []
    for cls, n in VAL_QUOTA.items():
        pool = [c for c in cands if c["gain_class"] == cls]
        questions += _pick(pool, n, rng, round1_bands, round1_parts, decoy_bands, taken, cache, log,
                           guard=_amps_differ)
    for line in log:
        print(line)
    return questions, decoys


def build_validation(args):
    from analysis import require

    require("the DI-labelling validation page")
    if not args.dry_run:
        if VAL_DIR.exists() and any(VAL_DIR.iterdir()):
            die(f"{VAL_DIR} is not empty; the page is built once")
        if VAL_KEY.exists():
            die(f"{VAL_KEY} exists; the page is built once")
    round1 = first_round_key()
    questions, decoys = validation_groups(round1)
    groups = questions + decoys
    print(f"{len(questions)} questions ("
          + ", ".join(f"{c} {sum(q['gain_class'] == c for q in questions)}" for c in VAL_QUOTA)
          + f"), {len(decoys)} decoys; {sum(len(g['tracks']) for g in groups)} clips; "
          f"about {minutes(groups)} min")
    for g in groups:
        print(f"  {g['kind']:8} {g.get('gain_class') or '/'.join(g['gain_classes']):18} {g['band']:24} "
              f"{g['part']:10} {len(g['tracks'])} tracks, window {g['window']['all_active_fraction']:.2f}, "
              f"pass {g['pick_pass']}" + (f", 3-6 kHz coherence {g['hf_coherence_3_6k']}" if g.get('hf_coherence_3_6k') else ""))
    if any(len(g["tracks"]) != 2 for g in groups):
        die("the validation page's intro says every question has two clips")
    if args.dry_run:
        return
    seed = secrets.randbits(64)
    rng = random.Random(seed)
    rng.shuffle(groups)
    rows, clips = [], []
    for n, g in enumerate(groups, 1):
        names = list(g["tracks"])
        rng.shuffle(names)
        letters = LETTERS[: len(names)]
        sr, start = g["window"]["sample_rate"], g["window"]["start_s"]
        for name in names:
            clips.append(clip(g["tracks"][name]["path"], sr, start))
            t = g["tracks"][name]
            t["file_sha256"] = {name: sha256(t["path"])}
        row = {"question": n, "kind": g["kind"], "song": g["song"], "source": g["source"],
               "band": g["band"], "part": g["part"], "letters": dict(zip(letters, names)),
               "tracks": g["tracks"], "window": g["window"], "clip_s": CLIP_S,
               "pick_pass": g["pick_pass"]}
        if g["kind"] == "control":
            row.update({"gain_class": g["gain_class"], "answer": letters[names.index(g["di"])],
                        "hf_coherence_3_6k": g["hf_coherence_3_6k"]})
        else:
            row.update({"gain_classes": g["gain_classes"], "answer": "none"})
        rows.append(row)
    target, levelled, after = L.level(clips)
    VAL_DIR.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    sections, k = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for r in rows:
            payloads = []
            for x in r["letters"]:
                wav = pathlib.Path(tmp) / f"clip-{k:03d}.wav"
                L.write(wav, levelled[k])
                payloads.append(aac(wav))
                r.setdefault("lufs_after", {})[x] = round(after[k], 3)
                k += 1
            sections.append(section(r["question"], list(r["letters"]), payloads))
    build_id = secrets.token_hex(6)
    page = VAL_PAGE_HTML.format(count=len(rows), minutes=minutes(groups), build=build_id,
                                questions="\n".join(sections))
    leaks = phone_leaks(page, leak_words(groups))
    if leaks:
        die(f"the page names what it must not: {leaks[:20]}")
    VAL_PAGE.write_text(page)
    stray = [p.name for p in VAL_DIR.iterdir() if p.name != VAL_PAGE.name]
    if stray:
        die(f"the page folder holds more than the page: {stray}")
    key = {"schema": "set6-di-labelling-validation-key-v1", "plan": PLAN.name,
           "plan_section": "Result of the first round, and a validation round",
           "seed": seed, "selection_seed": VAL_SEED, "quota": VAL_QUOTA, "decoys": N_DECOYS,
           "rule": {"min_confident": VAL_MIN_CONFIDENT, "min_share_right": VAL_MIN_SHARE,
                    "decoy_letter": "wrong", "first_round_classes_counted": list(DRIVEN)},
           "first_round_key_sha256": declared_key_sha256(),
           "clip_s": CLIP_S, "active_floor_db": ACTIVE_FLOOR_DB, "min_active": MIN_ACTIVE,
           "frame": FRAME, "hop": HOP, "sample_rate": SR, "aac_kbps": KBPS,
           "level": {"target_lufs": round(target, 3), "peak_ceiling_dbtp": L.PEAK_CEILING_DBTP,
                     "fade_s": L.FADE_S},
           "intro": VAL_INTRO, "question_text": QUESTION,
           "amp_guard": {"band_hz": list(HF_BAND), "coherence_below": HF_COH_MAX,
                         "on": "whole tracks, frames where both play, lag- and polarity-aligned"},
           "page_sha256": hashlib.sha256(page.encode()).hexdigest(), "build_id": build_id,
           "provenance": provenance(), "questions": rows}
    text = json.dumps(key, indent=1) + "\n"
    VAL_KEY.write_text(text)
    key_sha = hashlib.sha256(text.encode()).hexdigest()
    VAL_KEY_SHA.write_text(f"{key_sha}  validation-key.json\n{key['page_sha256']}  index.html\n")
    print(f"page {VAL_PAGE} ({VAL_PAGE.stat().st_size / 1e6:.1f} MB, {len(rows)} questions); "
          f"target {target:.2f} LUFS")
    print(f"key {VAL_KEY}\nkey sha256 {key_sha} (written to {VAL_KEY_SHA.relative_to(PLUGIN_ROOT)}; "
          "commit it before the page is sent)")


def score_validation_rows(rows, answers) -> dict:
    per, confident, right = [], 0, 0
    for r in rows:
        a = answers[r["question"]]
        conf = a != "none"
        ok = conf and a == r["answer"]          # a letter on a decoy (answer "none") is wrong
        confident += conf
        right += ok
        per.append({"question": r["question"], "kind": r["kind"], "answer": a, "key": r["answer"],
                    "confident": conf, "right": ok if conf else None,
                    "gain_class": r.get("gain_class") or r.get("gain_classes")})
    share = right / confident if confident else 0.0
    passes = confident >= VAL_MIN_CONFIDENT and share >= VAL_MIN_SHARE
    return {"confident": confident, "right": right, "share_right": round(share, 4),
            "min_confident": VAL_MIN_CONFIDENT, "min_share_right": VAL_MIN_SHARE,
            "decoy_letters": sum(p["kind"] == "decoy" and p["confident"] for p in per),
            "passes": passes, "per_question": per}


def _gain_class_of(song: str, di_copies: list, partners: list) -> dict:
    """Set 3's classifier on the reference amp track against the labelled DI, whole tracks."""
    sys.path[:0] = [str(GAIN_TOOLS)]
    import gainmeasure
    from classify import classify

    d = json.loads((PAIRS / f"{song}.json").read_text())
    cands = []
    for p in d["pairs"]:
        if not p["waveform_pass"] or (p["x"] in di_copies) == (p["y"] in di_copies):
            continue
        di, amp = (p["x"], p["y"]) if p["x"] in di_copies else (p["y"], p["x"])
        if amp not in partners:
            continue
        lag = p["waveform"]["median_lag_samples"]           # positive: y later than x
        lag = lag if p["x"] == di else -lag                 # positive: amp later than the DI
        cands.append((abs(lag), -p["waveform"]["median_peak_to_sidelobe"], amp, di, lag))
    if not cands:
        die(f"{song}: no stored same-take pair for {di_copies}")
    _, _, amp, di, lag = min(cands)
    x_amp, sr = _mono(MDB / d["tracks"][amp]["file"])
    x_di, sr_di = _mono(MDB / d["tracks"][di]["file"])
    if sr != sr_di:
        die(f"{song}: {amp} and {di} differ in sample rate")
    m = gainmeasure.measures(x_amp, x_di, sr, lag)
    cls, conf, why, cvd = classify(m) if m else (None, None, [], None)
    return {"reference": amp, "di_file": di, "lag_samples": lag, "gain_class": cls, "gain_confidence": conf,
            "clean_vs_driven": cvd, "gain_measures": m}


def score_validation(args):
    raw = pathlib.Path(args.answers).expanduser().read_bytes() if args.answers else args.line.encode()
    answers = read_answers(raw.decode())
    text = VAL_KEY.read_text()
    found = re.findall(r"^([0-9a-f]{64})\s+validation-key\.json$", VAL_KEY_SHA.read_text(), re.M)
    if len(found) != 1 or hashlib.sha256(text.encode()).hexdigest() != found[0]:
        die("the validation key is not the one whose hash was committed")
    key = json.loads(text)
    built = {r["question"] for r in key["questions"]}
    missing, extra = sorted(built - set(answers)), sorted(set(answers) - built)
    if missing or extra:
        die(f"the answers do not cover exactly the built questions: missing {missing}, extra {extra}")
    val = score_validation_rows(key["questions"], answers)
    out = {"schema": "set6-di-labelling-validation-result-v1", "plan": PLAN.name,
           "validation_key_sha256": found[0], "answers_sha256": hashlib.sha256(raw).hexdigest(),
           "validation": val, "first_round": None}
    if val["passes"]:
        round1 = first_round_key()
        raw1 = FIRST_ANSWERS.read_bytes()
        a1 = read_answers(raw1.decode())
        rows1 = round1["questions"]
        if set(a1) != {r["question"] for r in rows1}:
            die("the first-round answers do not cover exactly the first-round questions")
        labels = score_rows(rows1, a1)["labels"]
        for e in labels:
            split = e["reason"] == "split group: a DI was named in both halves"
            e["counts"] = False
            if e["di"] is None or split:
                continue
            if not e["same_take_partners"]:
                e["reason"] = "no same-take partner in the group"
                continue
            g = _gain_class_of(e["song"], e["di_copies"], e["same_take_partners"])
            e.update(gain=g, counts=g["gain_class"] in DRIVEN,
                     reason="" if g["gain_class"] in DRIVEN else
                     f"gain class {g['gain_class']}: only crunch and high-gain labels count")
        out["first_round"] = {
            "key_sha256": declared_key_sha256(), "answers": str(FIRST_ANSWERS),
            "answers_sha256": hashlib.sha256(raw1).hexdigest(),
            "confident_labels": sum(e["di"] is not None for e in labels),
            "groups_counted": sum(e["counts"] for e in labels),
            "songs_counted": sorted({e["song"] for e in labels if e["counts"]}),
            "labels": [e for e in labels if e["answer"] != "none"]}
    dest = pathlib.Path(args.json).expanduser()
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(f"validation: {val['right']}/{val['confident']} confident answers right "
          f"({val['decoy_letters']} letters on decoys); need >= {VAL_MIN_CONFIDENT} confident and "
          f">= {VAL_MIN_SHARE:.0%} right: {'PASSES' if val['passes'] else 'FAILS; set 6 stays unusable'}")
    if out["first_round"]:
        f = out["first_round"]
        print(f"first round: {f['confident_labels']} confident labels, {f['groups_counted']} groups from "
              f"{len(f['songs_counted'])} songs count (crunch or high-gain)")
    print(f"written to {dest}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--dry-run", action="store_true", help="groups, windows and counts only")
    s = sub.add_parser("score")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--answers", help="a file holding the answer line")
    g.add_argument("--line", help="the answer line itself, e.g. '1B 2none 3C ...'")
    s.add_argument("--json", default=str(OUT / "labels.json"))
    bv = sub.add_parser("build-validation", help="the validation round's page (plan, last section)")
    bv.add_argument("--dry-run", action="store_true", help="the draw and counts only")
    sv = sub.add_parser("score-validation")
    g = sv.add_mutually_exclusive_group(required=True)
    g.add_argument("--answers", help="a file holding the validation answer line")
    g.add_argument("--line", help="the answer line itself")
    sv.add_argument("--json", default=str(VAL_RESULT))
    args = ap.parse_args()
    {"build": build, "score": score, "build-validation": build_validation,
     "score-validation": score_validation}[args.cmd](args)


if __name__ == "__main__":
    guarded(main)
