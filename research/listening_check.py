#!/usr/bin/env python3
"""Does a real ear pick well on the audition page? (`docs/listening-check-plan.md`)

    python research/listening_check.py inputs --json docs/listening-check-inputs.json
    python research/listening_check.py build --inputs docs/listening-check-inputs.json \\
        --inputs-sha SHA --out-dir ~/ndsp-presets/runs/listening-check
    python research/listening_check.py score --out-dir ~/ndsp-presets/runs/listening-check \\
        --answers ANSWERS.txt --answers-sha SHA --json docs/listening-check-score.json

`inputs` chooses the parts (one per song of the shortlist measurement, the one whose
amp track stands out most from the rest of the instrumental mix), the controls and the
practice part, and scores every candidate with the judge through the part's own DI,
before any trial exists. `build` renders the candidates with R through the shipped
riffs, writes each sitting's page (no amp, preset, note or path on it) to
`<out-dir>/listen/`, and keeps the mapping in `<out-dir>/private/` for the scorer
alone. `score` reads the answers, checks their committed hash, then the key, and
computes the declared statistics.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import html
import itertools
import json
import math
import pathlib
import random
import re
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.append(str(PLUGIN_ROOT / "scripts"))

from _cli import die, guarded

SHORTLISTS = pathlib.Path("~/ndsp-presets/runs/shortlists")
CROPS = pathlib.Path("~/ndsp-presets/references/validation-crops")
REACH = pathlib.Path("~/ndsp-presets/runs/kill/amp-reach.json")
SANDBOXES = pathlib.Path("~/shortlist-sandboxes")
FACTORY = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite")
BAND_SETS = ("recording", "union")
EXPOSURE_FLOOR_DB = -10.0
CONTROL_GAP = 0.5
G = ("G1", "G2", "G3", "G4")
RIFFS = ("chords", "line")
LETTERS = "ABCD"
SILENT_PEAK = 1e-6
MAX_CANT_TELL = 8
DRAWS = 1_000_000
LEAKS = re.compile(r"AC20|PR12|SW50R|\bG[1-4]\b|\.xml|factory|template\+R|Example_Clean", re.I)


def _sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


# --- inputs -------------------------------------------------------------------------

def exposure(part: str) -> float:
    """The part's amp track's loudness less the rest of the instrumental mix's, in dB."""
    from analysis import io

    crop = CROPS.expanduser() / part
    loud = [io.loudness_lufs(io.load(crop / f)) for f in ("reference.wav",
                                                          "backing_instrumental.wav")]
    return loud[0] - loud[1]


def inputs(args):
    from analysis import require

    require("the listening check's inputs")
    import kill_tests as K
    import kill_tests_judge as KJ
    from benchmark_recordings import lag_samples
    from plan_listening_validation import high_gain

    mapping = json.loads((SHORTLISTS.expanduser() / "parts-map.json").read_text())
    index = json.loads((SHORTLISTS.expanduser() / "renders" / "index.json").read_text())
    renders = collections.defaultdict(dict)
    for row in index["rows"]:
        if "file" in row and not row.get("repeat"):
            if _sha(row["file"]) != row["sha256"]:
                die(f"{row['file']} changed since it was rendered")
            renders[row["part"]][row["label"]] = row
    chosen, rest, cues = [], [], {}
    for song, entry in sorted(mapping["songs"].items()):
        request = json.loads((SANDBOXES.expanduser() / song / "request.json").read_text())
        ranked = sorted(((exposure(p["part"]), label, p["part"])
                         for label, p in entry["parts"].items()), reverse=True)
        for exp, label, part in ranked:
            how = request["parts"][label]
            cues[part] = {"song": request["song"], "band": request["band"],
                          "track": how["track_name"], "how_it_plays": how["how_it_plays"],
                          "exposure_db": round(exp, 2)}
        if ranked[0][0] < EXPOSURE_FLOOR_DB:
            die(f"{song}'s most exposed part is under the floor")
        chosen.append(ranked[0][2])
        rest += [p for _, _, p in ranked[1:]]
    crops = CROPS.expanduser()
    jobs = [(p, {g: renders[p][g]["file"] for g in G + ("template+R",)},
             lag_samples(p) - K.LATENCY, crops) for p in chosen]
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(args.workers) as ex:
        scored = dict(ex.map(KJ.score_part, jobs))
    distances = {p: {b: {c: scored[p]["d"][f"{c}|full|{b}"] for c in G + ("template+R",)}
                     for b in BAND_SETS} for p in chosen}
    home = str(pathlib.Path.home())
    # Stored home-relative: the repository is public, and the path names the user.
    presets = {p: {g: renders[p][g]["preset"].replace(home, "~", 1) for g in G} for p in chosen}
    # Controls and practice: the shortlist parts not chosen, scored from the panels.
    reach = json.loads(REACH.expanduser().read_text())["distances"]
    controls, practice = [], None
    for part in sorted(rest):
        d = reach.get(part)
        if not d:
            continue
        names = sorted({k.split("|")[0] for k in d if ":factory:" in k})
        full = {b: {c: d.get(f"{c}|full|{b}") for c in names} for b in BAND_SETS}
        if any(v is None for b in BAND_SETS for v in full[b].values()):
            continue
        best = min(names, key=lambda c: (full["recording"][c], c))
        far = [c for c in names if c != best and all(
            math.log(full[b][c] / full[b][best]) > CONTROL_GAP for b in BAND_SETS)]
        far = sorted(far, key=lambda c: (math.log(full["recording"][c] / full["recording"][best]), c))
        if len(controls) < 2 and len(far) >= 3:
            picks = [best] + far[:3]
            controls.append({"part": part, "candidates": picks,
                             "distances": {b: {c: full[b][c] for c in picks} for b in BAND_SETS}})
        elif practice is None:
            # Each amp's closest factory preset, and one more clean one.
            by_amp = {}
            for c in sorted(names, key=lambda c: (full["recording"][c], c)):
                by_amp.setdefault(c.split(":")[0], c)
            extra = next(c for c in names if c not in by_amp.values() and not high_gain(c))
            practice = {"part": part, "candidates": list(by_amp.values()) + [extra]}
    if len(controls) < 2 or practice is None:
        die("not enough remaining parts for the controls and the practice trial")
    out = {"schema": "listening-check-inputs-1", "parts": chosen, "cues": cues,
           "distances": distances, "presets": presets, "controls": controls,
           "practice": practice,
           "renders_index_sha256": _sha(SHORTLISTS.expanduser() / "renders" / "index.json"),
           "amp_reach_sha256": _sha(REACH.expanduser())}
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(chosen)} parts, {len(controls)} controls; sha256 {_sha(args.json)}")


# --- build --------------------------------------------------------------------------

def factory_path(candidate: str) -> pathlib.Path:
    return FACTORY / (candidate.split(":", 2)[2] + ".xml")


def render_part(job):
    """{(label, riff): mono audio} for one part's candidates through each riff, with R,
    in one fresh plugin process."""
    import numpy as np

    from analysis import io
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack
    from render_preset_panel import preset_edits
    from render_shortlists import amp_of

    labelled, riffs = job
    pack = load_pack("morgan")

    class CheckRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["label"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    renderer = CheckRenderer("morgan", process_policy="reuse")
    out = {}
    try:
        CheckRenderer.commands = {
            label: preset_edits(path, pack, renderer, amp_of(path, pack, renderer), True)
            for label, path in labelled.items()}
        for riff, path in riffs.items():
            di = io.load(path).mono().astype(np.float32)
            renderer.render(di, {"label": next(iter(labelled))})        # warm-up
            for label in labelled:
                audio = np.asarray(renderer.render(di, {"label": label}).audio, dtype=np.float32)
                if not np.isfinite(audio).all() or np.abs(audio).max() < SILENT_PEAK:
                    raise ValueError(f"{label} through {riff} rendered silence or non-finite audio")
                out[(label, riff)] = audio
    finally:
        renderer.close()
    return out


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Listening check, sitting {sitting}</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#fff; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#171716; --fg:#ecebe6; --muted:#a19f97;
  --line:#34332f; --card:#201f1d; }} }}
body {{ margin:0; background:var(--bg); color:var(--fg);
        font:16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
main {{ max-width:760px; margin:0 auto; padding:24px 16px 48px; }}
section {{ border:1px solid var(--line); border-radius:10px; background:var(--card);
           padding:12px 16px; margin:16px 0; }}
h2 {{ font-size:1.05rem; margin:0 0 4px; }}
.cue {{ color:var(--muted); margin:0 0 8px; }}
.row {{ display:grid; grid-template-columns:4.5rem 1fr; align-items:center; gap:8px;
        margin:4px 0; }}
audio {{ width:100%; height:36px; }}
</style></head><body><main>
<h1>Listening check, sitting {sitting}</h1>
<p>For each trial: play the song, then A to D. Which of A to D sounds most like the
guitar named in the song? A–D all play the same riff, not the song's part, so listen
for the tone: gain, brightness, body. Answer with a letter, or "?" if you can't tell.
Write your answers as one line, e.g. <code>1A 2C 3?</code>.</p>
{trials}
</main></body></html>
"""


def page(sitting: int, trials) -> str:
    sections = []
    for t in trials:
        rows = [f'<div class="row"><b>Song</b><audio controls preload="none" '
                f'src="{html.escape(t["song"])}"></audio></div>']
        rows += [f'<div class="row"><b>{x}</b><audio controls preload="none" '
                 f'src="{html.escape(t["clips"][x])}"></audio></div>' for x in LETTERS]
        sections.append(f'<section><h2>Trial {t["number"]}</h2>'
                        f'<p class="cue">{html.escape(t["cue"])}</p>{"".join(rows)}</section>')
    return PAGE.format(sitting=sitting, trials="\n".join(sections))


def leak_check(folder: pathlib.Path) -> list:
    """Files in the listener's folder whose name or text names an amp, a candidate or a
    preset: none may."""
    bad = []
    for path in folder.rglob("*"):
        if LEAKS.search(path.name):
            bad.append(str(path))
        elif path.suffix in (".html", ".txt", ".json") and LEAKS.search(path.read_text()):
            bad.append(str(path))
    return bad


def plan_trials(parts, controls, practice, rng):
    """Two sittings: each holds one riff of half the parts and the other riff of the
    rest, one control, and repeats; the practice trial opens sitting 1."""
    order = parts[:]
    rng.shuffle(order)
    half = len(order) // 2
    sittings = {1: [], 2: []}
    for i, part in enumerate(order):
        first, second = (RIFFS if i < half else RIFFS[::-1])
        sittings[1].append({"kind": "main", "part": part, "riff": first})
        sittings[2].append({"kind": "main", "part": part, "riff": second})
    for s in (1, 2):
        rng.shuffle(sittings[s])
    repeats = rng.sample(sittings[1], 3)
    sittings[2] += [dict(repeats[0], kind="repeat"), dict(repeats[1], kind="repeat")]
    sittings[1].append(dict(repeats[2], kind="repeat"))
    for s, control, riff in ((1, controls[0], "chords"), (2, controls[1], "line")):
        sittings[s].append({"kind": "control", "part": control["part"], "riff": riff})
    for s in (1, 2):
        mains = [t for t in sittings[s] if t["kind"] == "main"]
        others = [t for t in sittings[s] if t["kind"] != "main"]
        rng.shuffle(others)
        # A repeat comes after the trial it repeats; spread the rest through the sitting.
        merged = mains[:]
        for t in others:
            at = rng.randrange(len(merged) // 2, len(merged) + 1)
            merged.insert(at, t)
        sittings[s] = merged
    sittings[1].insert(0, {"kind": "practice", "part": practice["part"], "riff": "chords"})
    return sittings


def build(args):
    from analysis import require

    require("building the listening check")
    import numpy as np
    import soundfile as sf

    from analysis import io
    from audition import CEILING_DB, measure, page_level, shipped_riffs

    if _sha(args.inputs) != args.inputs_sha:
        die("the inputs file is not the one whose hash was committed")
    data = json.loads(args.inputs.read_text())
    out = args.out_dir.expanduser()
    if out.exists() and any(out.iterdir()):
        die(f"{out} is not empty")
    private, listen = out / "private", out / "listen"
    private.mkdir(parents=True)
    listen.mkdir()
    riffs = shipped_riffs()
    rng = random.SystemRandom()
    candidates = {p: {g: pathlib.Path(data["presets"][p][g]).expanduser() for g in G}
                  for p in data["parts"]}
    for c in data["controls"]:
        candidates[c["part"]] = {f"C{i}": factory_path(x) for i, x in enumerate(c["candidates"])}
    pr = data["practice"]
    candidates[pr["part"]] = {f"P{i}": factory_path(x) for i, x in enumerate(pr["candidates"])}
    from concurrent.futures import ProcessPoolExecutor

    jobs = [(candidates[p], {r: riffs[r] for r in RIFFS}) for p in candidates]
    with ProcessPoolExecutor(args.workers) as ex:
        rendered = dict(zip(candidates, ex.map(render_part, jobs)))
    sittings = plan_trials(data["parts"], data["controls"], pr, rng)
    key = {"schema": "listening-check-key-1", "inputs_sha256": args.inputs_sha, "sittings": {}}
    for s, trials in sittings.items():
        folder = listen / f"sitting-{s}"
        folder.mkdir()
        shown, number = [], 0
        for t in trials:
            number += 1
            part = t["part"]
            labels = list(candidates[part])
            rng.shuffle(labels)
            song = io.load(CROPS.expanduser() / part / "mix_instrumental.wav")
            clips = {"song": song.samples}
            for letter, label in zip(LETTERS, labels):
                clips[letter] = rendered[part][(label, t["riff"])]
            level = page_level([measure(a, 48000) for a in clips.values()])
            files = {}
            for name, audio in clips.items():
                loudness, _ = measure(audio, 48000)
                fname = f"trial-{number:02d}-{name}.wav"
                sf.write(str(folder / fname), (audio * 10 ** ((level - loudness) / 20)).astype(np.float32),
                         48000, subtype="PCM_16")
                files[name] = fname
            cue_info = (data["cues"].get(part) or {})
            cue = (f"{cue_info.get('song', 'Practice')}: the guitar track {cue_info.get('track', '')}, "
                   f"which {cue_info.get('how_it_plays', 'plays here')}." if cue_info else
                   "Practice: the main guitar.")
            shown.append({"number": number, "cue": cue, "song": files["song"],
                          "clips": {x: files[x] for x in LETTERS}})
            key["sittings"].setdefault(str(s), []).append(
                {"number": number, **t, "letters": dict(zip(LETTERS, labels)),
                 "level_lufs": round(level, 2),
                 "clips_sha256": {n: _sha(folder / f) for n, f in files.items()}})
        (folder / "index.html").write_text(page(s, shown))
    leaks = leak_check(listen)
    if leaks:
        die(f"the listener's folder names what it must not: {leaks}")
    (private / "private-key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(f"built {sum(len(v) for v in sittings.values())} trials in two sittings at {listen}")


# --- score --------------------------------------------------------------------------

def parse_answers(text: str) -> dict:
    """{(sitting, trial number): letter or None} from lines like 'sitting 1: 1A 2C 3?'."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"\s*sitting\s*(\d+)\s*:(.*)", line, re.I)
        if not m:
            continue
        for number, letter in re.findall(r"(\d+)\s*([A-Da-d?])", m.group(2)):
            out[(int(m.group(1)), int(number))] = None if letter == "?" else letter.upper()
    return out


def randomization_p(trials, draws: int = DRAWS) -> float:
    """One-sided p that a uniform pick per trial gives a sum of c at most the observed,
    from `draws` Monte Carlo redraws (a "can't tell" trial contributes 0 either way)."""
    import numpy as np

    observed = sum(t["c"] for t in trials)
    choices = np.array([t["choices"] if t["pick"] is not None else [0.0] * 4 for t in trials])
    rng = np.random.default_rng(20261005)
    hits, done = 0, 0
    while done < draws:
        n = min(100_000, draws - done)
        picks = rng.integers(0, 4, size=(n, len(trials)))
        totals = choices[np.arange(len(trials)), picks].sum(axis=1)
        hits += int((totals <= observed + 1e-12).sum())
        done += n
    return hits / draws


def score(args):
    if _sha(args.answers) != args.answers_sha:
        die("the answers file is not the one whose hash was committed")
    out = args.out_dir.expanduser()
    key = json.loads((out / "private" / "private-key.json").read_text())
    data = json.loads((PLUGIN_ROOT / "docs" / "listening-check-inputs.json").read_text())
    if _sha(PLUGIN_ROOT / "docs" / "listening-check-inputs.json") != key["inputs_sha256"]:
        die("the committed inputs changed since the trials were built")
    answers = parse_answers(args.answers.read_text())
    result = {"answers_sha256": args.answers_sha, "by_band_set": {}}
    control_hits, cant_tell, repeats = [], 0, []
    for bands in BAND_SETS:
        trials = []
        for s, rows in key["sittings"].items():
            for t in rows:
                pick = answers.get((int(s), t["number"]))
                if t["kind"] == "practice":
                    continue
                if t["kind"] == "control":
                    if bands == "recording":
                        control_hits.append(pick is not None and t["letters"][pick] == "C0")
                    continue
                d = data["distances"][t["part"]][bands]
                logs = {x: math.log(d[t["letters"][x]]) for x in LETTERS}
                mean = statistics.mean(logs.values())
                c = 0.0 if pick is None else logs[pick] - mean
                row = {"part": t["part"], "riff": t["riff"], "kind": t["kind"], "pick": pick,
                       "c": c, "choices": [v - mean for v in logs.values()],
                       "best": min(logs, key=logs.get) == pick,
                       "vs_g1": None if pick is None else logs[pick] - math.log(d["G1"]),
                       "vs_template": None if pick is None else logs[pick] - math.log(d["template+R"]),
                       "captured": None if pick is None or min(logs.values()) == mean
                       else (logs[pick] - mean) / (min(logs.values()) - mean)}
                if t["kind"] == "repeat":
                    if bands == "recording":
                        repeats.append(row)
                    continue
                trials.append(row)
                if bands == "recording" and pick is None:
                    cant_tell += 1
        p = randomization_p(trials)
        vs_g1 = statistics.median(r["vs_g1"] for r in trials if r["vs_g1"] is not None)
        result["by_band_set"][bands] = {
            "trials": len(trials), "sum_c": sum(r["c"] for r in trials), "p": p,
            "median_vs_g1": vs_g1,
            "median_vs_template": statistics.median(r["vs_template"] for r in trials
                                                    if r["vs_template"] is not None),
            "best_of_four": sum(r["best"] for r in trials),
            "captured_median": statistics.median(r["captured"] for r in trials
                                                 if r["captured"] is not None),
            "per_riff": {riff: sum(r["c"] for r in trials if r["riff"] == riff) for riff in RIFFS},
            "rows": trials}
    by = result["by_band_set"]
    result["cant_tell"] = cant_tell
    result["controls_hit"] = control_hits
    first = {(r["part"], r["riff"]): r for r in by["recording"]["rows"]}
    result["repeats_consistent"] = [
        first[(r["part"], r["riff"])]["pick"] == r["pick"] for r in repeats]
    result["primary_holds"] = all(by[b]["p"] < 0.05 for b in BAND_SETS)
    result["main_path"] = result["primary_holds"] and all(by[b]["median_vs_g1"] <= 0
                                                          for b in BAND_SETS)
    result["inconclusive"] = cant_tell > MAX_CANT_TELL
    args.json.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "by_band_set"}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("inputs", "build", "score"))
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--inputs", type=pathlib.Path)
    ap.add_argument("--inputs-sha")
    ap.add_argument("--out-dir", type=pathlib.Path)
    ap.add_argument("--answers", type=pathlib.Path)
    ap.add_argument("--answers-sha")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    {"inputs": inputs, "build": build, "score": score}[args.command](args)


if __name__ == "__main__":
    guarded(main)
