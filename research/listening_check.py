#!/usr/bin/env python3
"""Does a real ear pick well on the audition page? (`docs/listening-check-plan.md`)

    python research/listening_check.py inputs --json docs/listening-check-inputs.json
    python research/listening_check.py build --inputs docs/listening-check-inputs.json \\
        --inputs-sha SHA --out-dir ~/ndsp-presets/runs/listening-check
    python research/listening_check.py score --out-dir ~/ndsp-presets/runs/listening-check \\
        --key-sha SHA --answers ANSWERS.txt --answers-sha SHA \\
        --json docs/listening-check-score.json

`inputs` chooses the parts (one per song of the shortlist measurement, the one whose
amp track stands out most from the rest of the instrumental mix), the controls and the
practice part, measures each part's DI loudness, and scores every candidate with the
judge through the part's own DI, before any trial exists. `build` checks every preset
against the hash it was scored with, renders the candidates with R through the shipped
riffs, writes each sitting's page (no amp, preset, note or path on it) to
`<out-dir>/listen/`, and keeps the mapping in `<out-dir>/private/` for the scorer
alone; it prints the key's SHA-256, which is committed before the first sitting.
`score` checks the answers' and the key's committed hashes, requires exactly one answer
per built trial, and computes the declared statistics.
"""

from __future__ import annotations

import argparse
import collections
import functools
import hashlib
import html
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
CONTROLS = 4                    # two per sitting
MIN_CONTROLS_HIT = 3            # of 4: a guessing listener reaches it 5.1% of the time
CLEAR_PAIR = 0.15               # log distance at which the judge "clearly" separates two
RIFF_LUFS = -23.7
G = ("G1", "G2", "G3", "G4")
RIFFS = ("chords", "line")
LETTERS = "ABCD"
SILENT_PEAK = 1e-6
MAX_CANT_TELL = 8
DRAWS = 1_000_000
LEAKS = r"AC20|PR12|SW50R|\bG[1-4]\b|\.xml|factory|template\+R|Example_Clean"


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


def choose_controls(rest, exposure_of, reach, gain_of):
    """Controls and the practice part from the parts not under test.

    Controls: the most exposed parts that clear the floor, up to CONTROLS. Each has its
    closest factory preset not already used, and three of the opposite gain class
    (high-gain against clean, or the reverse), each more than CONTROL_GAP (log) farther
    under both band sets, the farthest first; no factory preset serves twice. Practice:
    the most exposed part left, with each amp's closest unused factory preset and one
    more unused clean one."""
    used, controls = set(), []
    by_exposure = sorted(rest, key=lambda p: (-exposure_of(p), p))

    def full(part):
        d = reach.get(part) or {}
        names = sorted({k.split("|")[0] for k in d if ":factory:" in k})
        out = {b: {c: d.get(f"{c}|full|{b}") for c in names} for b in BAND_SETS}
        if not names or any(v is None for b in BAND_SETS for v in out[b].values()):
            return None, None
        return names, out

    for part in by_exposure:
        if len(controls) == CONTROLS or exposure_of(part) < EXPOSURE_FLOOR_DB:
            break
        names, f = full(part)
        if names is None:
            continue
        for correct in sorted(names, key=lambda c: (f["recording"][c], c)):
            if correct in used:
                continue
            gap = {c: min(math.log(f[b][c] / f[b][correct]) for b in BAND_SETS)
                   for c in names if c not in used and c != correct
                   and gain_of(c) != gain_of(correct)}
            wrong = sorted((c for c, g in gap.items() if g > CONTROL_GAP),
                           key=lambda c: (-gap[c], c))[:3]
            if len(wrong) == 3:
                picks = [correct] + wrong
                controls.append({"part": part, "candidates": picks,
                                 "distances": {b: {c: f[b][c] for c in picks}
                                               for b in BAND_SETS}})
                used.update(picks)
                break
    practice = None
    for part in by_exposure:
        if any(c["part"] == part for c in controls):
            continue
        names, f = full(part)
        if names is None:
            continue
        ranked = sorted(names, key=lambda c: (f["recording"][c], c))
        by_amp = {}
        for c in ranked:
            if c not in used:
                by_amp.setdefault(c.split(":")[0], c)
        extra = next((c for c in ranked if c not in used and c not in by_amp.values()
                      and not gain_of(c)), None)
        if len(by_amp) == 3 and extra:
            practice = {"part": part, "candidates": list(by_amp.values()) + [extra]}
            break
    return controls, practice


def g1_chance_pass(distances, parts, draws: int = 20_000, seed: int = 20261006) -> float:
    """How often a random picker passes "median of log(d(pick)/d(G1)) <= 0 under both
    band sets" over each part twice: whether that rule can tell an ear from chance."""
    import numpy as np

    rng = np.random.default_rng(seed)
    gaps = {b: np.array([[math.log(distances[p][b][g] / distances[p][b]["G1"]) for g in G]
                         for p in parts for _ in RIFFS]) for b in BAND_SETS}
    picks = rng.integers(0, 4, size=(draws, len(parts) * len(RIFFS)))
    rows = np.arange(picks.shape[1])
    passed = np.ones(draws, dtype=bool)
    for b in BAND_SETS:
        passed &= np.median(gaps[b][rows, picks], axis=1) <= 0
    return float(passed.mean())


def inputs(args):
    from analysis import require

    require("the listening check's inputs")
    import kill_tests as K
    import kill_tests_judge as KJ
    from benchmark_recordings import lag_samples
    from analysis import io
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
    preset_sha = {p: {g: renders[p][g]["preset_sha256"] for g in G} for p in chosen}
    di_lufs = {p: round(io.loudness_lufs(io.load(crops / p / "di.wav")), 2) for p in chosen}
    # Controls and practice: the shortlist parts not chosen, scored from the panels.
    reach = json.loads(REACH.expanduser().read_text())["distances"]
    controls, practice = choose_controls(rest, lambda p: cues[p]["exposure_db"], reach,
                                         functools.lru_cache(maxsize=None)(high_gain))
    if len(controls) < CONTROLS or practice is None:
        die("not enough remaining parts for the controls and the practice trial")
    out = {"schema": "listening-check-inputs-2", "parts": chosen, "cues": cues,
           "distances": distances, "presets": presets, "preset_sha256": preset_sha,
           "di_lufs": di_lufs, "riff_lufs": RIFF_LUFS,
           "g1_rule_chance_pass": round(g1_chance_pass(distances, chosen), 4),
           "controls": controls, "practice": practice,
           "renders_index_sha256": _sha(SHORTLISTS.expanduser() / "renders" / "index.json"),
           "amp_reach_sha256": _sha(REACH.expanduser())}
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(chosen)} parts, {len(controls)} controls; a random picker passes the G1 "
          f"rule {out['g1_rule_chance_pass']:.1%} of the time; sha256 {_sha(args.json)}")


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
for the tone: gain, brightness, body. Answer every trial with a letter, or "?" if you
can't tell, on one line that starts with the sitting, exactly like this:</p>
<p><code>Sitting {sitting}: 1A 2C 3? 4B …</code></p>
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


def leak_check(folder: pathlib.Path, names=()) -> list:
    """Files in the listener's folder whose name or text names an amp, a candidate or one
    of `names` (the presets on trial): none may."""
    pattern = re.compile("|".join([LEAKS] + [rf"\b{re.escape(n)}\b" for n in names if n]),
                         re.I)
    bad = []
    for path in folder.rglob("*"):
        if pattern.search(path.name):
            bad.append(str(path))
        elif path.suffix in (".html", ".txt", ".json") and pattern.search(path.read_text()):
            bad.append(str(path))
    return bad


def plan_trials(parts, controls, practice, rng):
    """Two sittings. Each holds one riff of half the parts and the other riff of the rest,
    two controls (one in each half), and repeats; the practice trial opens sitting 1.
    Two of sitting 1's trials are repeated in sitting 2, and one later in sitting 1 with
    at least two trials between."""
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
    for s, pair in ((1, controls[0:2]), (2, controls[2:4])):
        riffs = list(RIFFS)
        rng.shuffle(riffs)
        mid = len(sittings[s]) // 2
        late = {"kind": "control", "part": pair[1]["part"], "riff": riffs[1]}
        sittings[s].insert(rng.randrange(mid + 1, len(sittings[s]) + 1), late)
        early = {"kind": "control", "part": pair[0]["part"], "riff": riffs[0]}
        sittings[s].insert(rng.randrange(0, mid + 1), early)
    mains = [i for i, t in enumerate(sittings[1]) if t["kind"] == "main"]
    within = rng.choice([i for i in mains if i <= len(sittings[1]) - 3])
    across = rng.sample([sittings[1][i] for i in mains if i != within], 2)
    sittings[1].insert(rng.randrange(within + 3, len(sittings[1]) + 1),
                       dict(sittings[1][within], kind="repeat"))
    for t in across:
        sittings[2].insert(rng.randrange(0, len(sittings[2]) + 1), dict(t, kind="repeat"))
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
    if _sha(SHORTLISTS.expanduser() / "renders" / "index.json") != data["renders_index_sha256"]:
        die("the shortlist renders index changed since the inputs were fixed")
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
    for p, by_g in candidates.items():
        for g, path in by_g.items():
            if _sha(path) != data["preset_sha256"][p][g]:
                die(f"{path} is not the preset the judge scored for {p}")
    for c in data["controls"]:
        candidates[c["part"]] = {f"C{i}": factory_path(x) for i, x in enumerate(c["candidates"])}
    pr = data["practice"]
    candidates[pr["part"]] = {f"P{i}": factory_path(x) for i, x in enumerate(pr["candidates"])}
    from concurrent.futures import ProcessPoolExecutor

    jobs = [(candidates[p], {r: riffs[r] for r in RIFFS}) for p in candidates]
    with ProcessPoolExecutor(args.workers) as ex:
        rendered = dict(zip(candidates, ex.map(render_part, jobs)))
    sittings = plan_trials(data["parts"], data["controls"], pr, rng)
    key = {"schema": "listening-check-key-2", "inputs_sha256": args.inputs_sha,
           "preset_sha256": {p: {label: _sha(path) for label, path in by_label.items()}
                             for p, by_label in candidates.items()},
           "sittings": {}}
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
    names = {x.rsplit("/", 1)[-1] for c in data["controls"] + [pr] for x in c["candidates"]}
    names |= {path.stem for by_label in candidates.values() for path in by_label.values()}
    leaks = leak_check(listen, sorted(names))
    if leaks:
        die(f"the listener's folder names what it must not: {leaks}")
    (private / "private-key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(f"built {sum(len(v) for v in sittings.values())} trials in two sittings at {listen}; "
          f"the key's sha256 is {_sha(private / 'private-key.json')}: commit it before "
          "the first sitting")


# --- score --------------------------------------------------------------------------

def parse_answers(text: str) -> dict:
    """{(sitting, trial number): letter or None} from lines like 'Sitting 1: 1A 2C 3?'.

    Strict, because the sheet's hash is committed before scoring and a slip cannot be
    corrected afterwards: every non-blank line must be a sitting line, every token a
    number and a letter or "?", and no trial may be answered twice."""
    out = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        m = re.fullmatch(r"\s*sitting\s*(\d+)\s*:(.*)", line, re.I)
        if not m:
            raise ValueError(f"not a sitting line: {line!r}")
        for token in m.group(2).split():
            t = re.fullmatch(r"(\d+)([A-Da-d?])", token)
            if not t:
                raise ValueError(f"not an answer: {token!r} in {line!r}")
            at = (int(m.group(1)), int(t.group(1)))
            if at in out:
                raise ValueError(f"sitting {at[0]}, trial {at[1]} is answered twice")
            out[at] = None if t.group(2) == "?" else t.group(2).upper()
    return out


def randomization_p(values, picks, draws: int | None = None) -> float:
    """One-sided p that a uniform pick per trial gives a sum at most the observed one.

    `values` holds each trial's four values, one per letter, lower meaning closer;
    `picks` each trial's letter index, or None for "can't tell", which contributes 0
    either way. Monte Carlo over `draws` redraws: 4^32 cannot be enumerated."""
    import numpy as np

    draws = draws or DRAWS
    values = np.array([v if p is not None else [0.0] * 4 for v, p in zip(values, picks)])
    observed = sum(v[p] for v, p in zip(values, picks) if p is not None)
    rng = np.random.default_rng(20261005)
    hits, done = 0, 0
    while done < draws:
        n = min(100_000, draws - done)
        drawn = rng.integers(0, 4, size=(n, len(values)))
        totals = values[np.arange(len(values)), drawn].sum(axis=1)
        hits += int((totals <= observed + 1e-12).sum())
        done += n
    return hits / draws


def binomial_p(k: int, n: int, chance: float = 0.25) -> float:
    """Exact one-sided P(X >= k) for X ~ Binomial(n, chance)."""
    return sum(math.comb(n, i) * chance ** i * (1 - chance) ** (n - i) for i in range(k, n + 1))


def _median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def readings(rows, draws: int | None = None) -> dict | None:
    """The declared readings over some main trials. Each row: `logs` (letter -> log d),
    `pick` (a letter or None), `g1` and `template` (log d)."""
    if not rows:
        return None
    picks = [None if r["pick"] is None else LETTERS.index(r["pick"]) for r in rows]
    centred, pairs, gain, perfect = [], [], 0.0, 0.0
    best = closer = clear = 0
    for r, p in zip(rows, picks):
        logs = [r["logs"][x] for x in LETTERS]
        mean = statistics.mean(logs)
        centred.append([v - mean for v in logs])
        # Pairs the judge separates clearly: a choice scores -1 for each candidate it
        # beats by more than CLEAR_PAIR, +1 for each that beats it by as much.
        pairs.append([sum((v > u + CLEAR_PAIR) - (u > v + CLEAR_PAIR) for v in logs)
                      * -1 for u in logs])
        perfect += min(logs) - mean
        if p is not None:
            gain += logs[p] - mean
            best += logs[p] == min(logs)
            closer += sum(v > logs[p] + CLEAR_PAIR for v in logs)
            clear += sum(abs(v - logs[p]) > CLEAR_PAIR for v in logs)
    # "Can't tell" delivers G1, the product's default.
    delivered = [r["g1"] if r["pick"] is None else r["logs"][r["pick"]] for r in rows]
    return {
        "trials": len(rows), "sum_c": gain, "p": randomization_p(centred, picks, draws),
        "best_of_four": best, "best_of_four_p": binomial_p(best, len(rows)),
        "clear_pairs": clear, "clear_pairs_closer": closer,
        "clear_pairs_share": closer / clear if clear else None,
        "clear_pairs_p": randomization_p(pairs, picks, draws),
        "captured_share": gain / perfect if perfect else None,
        "median_vs_g1": _median(d - r["g1"] for d, r in zip(delivered, rows)),
        "median_vs_template": _median(d - r["template"] for d, r in zip(delivered, rows)),
    }


def decide(by_band_set: dict, cant_tell: int, controls_hit: int) -> dict:
    """The declared decision from the readings, the "can't tell" count and the controls."""
    reasons = []
    if cant_tell > MAX_CANT_TELL:
        reasons.append(f"{cant_tell} \"can't tell\" answers, more than {MAX_CANT_TELL}")
    if controls_hit < MIN_CONTROLS_HIT:
        reasons.append(f"{controls_hit} of {CONTROLS} controls hit, fewer than "
                       f"{MIN_CONTROLS_HIT}")
    primary = not reasons and all(by_band_set[b]["all"]["p"] < 0.05 for b in BAND_SETS)
    return {"inconclusive": bool(reasons), "inconclusive_because": reasons,
            "primary_holds": primary, "main_path": primary}


def score(args):
    if _sha(args.answers) != args.answers_sha:
        die("the answers file is not the one whose hash was committed")
    out = args.out_dir.expanduser()
    key_path = out / "private" / "private-key.json"
    if _sha(key_path) != args.key_sha:
        die("the key is not the one whose hash was committed before the first sitting")
    key = json.loads(key_path.read_text())
    inputs_path = args.inputs or PLUGIN_ROOT / "docs" / "listening-check-inputs.json"
    if _sha(inputs_path) != key["inputs_sha256"]:
        die("the committed inputs changed since the trials were built")
    data = json.loads(inputs_path.read_text())
    try:
        answers = parse_answers(args.answers.read_text())
    except ValueError as e:
        die(f"the answer sheet cannot be scored: {e}")
    built = {(int(s), t["number"]) for s, rows in key["sittings"].items() for t in rows}
    if set(answers) != built:
        die(f"the answer sheet does not answer exactly the built trials: missing "
            f"{sorted(built - set(answers))}, extra {sorted(set(answers) - built)}")
    result = {"answers_sha256": args.answers_sha, "key_sha256": args.key_sha,
              "g1_rule_chance_pass": data["g1_rule_chance_pass"], "by_band_set": {}}
    gaps = {p: data["di_lufs"][p] - data["riff_lufs"] for p in data["parts"]}
    gap_median = statistics.median(gaps.values())
    controls, mains, repeats = collections.defaultdict(list), [], []
    for s, rows in key["sittings"].items():
        for t in rows:
            pick = answers[(int(s), t["number"])]
            if t["kind"] == "control":
                controls[s].append(pick is not None and t["letters"][pick] == "C0")
            elif t["kind"] in ("main", "repeat"):
                (mains if t["kind"] == "main" else repeats).append((t, pick))
    for bands in BAND_SETS:
        rows = []
        for t, pick in mains:
            d = data["distances"][t["part"]][bands]
            rows.append({"part": t["part"], "riff": t["riff"], "pick": pick,
                         "picked": None if pick is None else t["letters"][pick],
                         "logs": {x: math.log(d[t["letters"][x]]) for x in LETTERS},
                         "g1": math.log(d["G1"]), "template": math.log(d["template+R"]),
                         "hot_di": gaps[t["part"]] > gap_median})
        result["by_band_set"][bands] = {
            "all": readings(rows),
            "per_riff": {riff: readings([r for r in rows if r["riff"] == riff])
                         for riff in RIFFS},
            "di_hotter_than_median_gap": readings([r for r in rows if r["hot_di"]]),
            "di_nearer_the_riff": readings([r for r in rows if not r["hot_di"]]),
            "rows": rows}
    # Letters are drawn afresh for a repeat, so compare the presets they stand for.
    chosen = lambda t, pick: None if pick is None else t["letters"][pick]  # noqa: E731
    first = {(t["part"], t["riff"]): chosen(t, pick) for t, pick in mains}
    result["repeats_consistent"] = [first[(t["part"], t["riff"])] is not None
                                    and first[(t["part"], t["riff"])] == chosen(t, pick)
                                    for t, pick in repeats]
    result["di_to_riff_gap_median_db"] = round(gap_median, 2)
    result["cant_tell"] = sum(pick is None for _, pick in mains)
    result["controls_hit"] = {s: hits for s, hits in sorted(controls.items())}
    result["void_sittings"] = [s for s, hits in sorted(controls.items()) if not any(hits)]
    result.update(decide(result["by_band_set"], result["cant_tell"],
                         sum(sum(h) for h in controls.values())))
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
    ap.add_argument("--key-sha")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    {"inputs": inputs, "build": build, "score": score}[args.command](args)


if __name__ == "__main__":
    guarded(main)
