#!/usr/bin/env python3
"""Does a real ear pick well on the audition page? (`docs/listening-check-plan.md`)

    python research/listening_check.py inputs --json docs/listening-check-inputs.json
    python research/listening_check.py build --inputs docs/listening-check-inputs.json \\
        --inputs-sha SHA --out-dir ~/ndsp-presets/runs/listening-check
    python research/listening_check.py phone-page --out-dir ~/ndsp-presets/runs/listening-check \\
        --inputs docs/listening-check-inputs.json --sitting 1
    python research/listening_check.py check-sheet --out-dir ~/ndsp-presets/runs/listening-check \\
        --answers ANSWERS.txt
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
DRIVE_HIGH = 0.7               # a drive pedal's gain from which a control calls it high-gain
CLEAN_VOLUME = 0.5             # the amp volume at or under which, with no drive, it is clean
CLEAR_PAIR = 0.15               # log distance at which the judge "clearly" separates two
TASTE_RIDGE = 0.5               # the taste fit's penalty: 14 to 18 answers per riff, 9 features
RIFF_LUFS = -23.7
STYLE_MARGIN = 0.15             # a part's chord share this near the split is reported apart
DYAD_SHARE = 0.9                # two notes or more in this share of frames: two-note shapes
G = ("G1", "G2", "G3", "G4")
RIFFS = ("chords", "line")
LETTERS = "ABCD"
SILENT_PEAK = 1e-6
RENDER_DRIFT = 0.01             # log distance; the judge agreed to three decimals in trials
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


def choose_controls(parts, main, exposure_of, reach, gain_of, song_of, clear_song):
    """Controls and the practice part.

    Controls, up to CONTROLS, one per song: parts that clear the floor, those not under
    test first, then the parts under test, each most exposed first. A part's answer is
    its closest unused factory preset of a clear gain class (`gain_of` is "clean" or
    "high", not None), and the part qualifies when every other guitar in its song shares
    that class (`clear_song`), so the cue cannot point the ear at a guitar of the other
    class. It
    offers that preset against three of the other class, each more than CONTROL_GAP
    (log) farther under both band sets, the farthest first; no factory preset serves
    twice. Practice: the most exposed part not under test and not a control, with each
    amp's closest unused factory preset and one more unused clean one."""
    used, controls, songs = set(), [], set()
    by_exposure = sorted(parts, key=lambda p: (p in main, -exposure_of(p), p))

    def full(part):
        d = reach.get(part) or {}
        names = sorted({k.split("|")[0] for k in d if ":factory:" in k})
        out = {b: {c: d.get(f"{c}|full|{b}") for c in names} for b in BAND_SETS}
        if not names or any(v is None for b in BAND_SETS for v in out[b].values()):
            return None, None
        return names, out

    for part in by_exposure:
        if len(controls) == CONTROLS:
            break
        if exposure_of(part) < EXPOSURE_FLOOR_DB or song_of(part) in songs:
            continue
        names, f = full(part)
        if names is None:
            continue
        for correct in sorted(names, key=lambda c: (f["recording"][c], c)):
            kind = gain_of(correct)
            if correct in used or kind is None:
                continue
            if not clear_song(part, kind):
                break
            gap = {c: min(math.log(f[b][c] / f[b][correct]) for b in BAND_SETS)
                   for c in names if c not in used and gain_of(c) not in (None, kind)}
            wrong = sorted((c for c, g in gap.items() if g > CONTROL_GAP),
                           key=lambda c: (-gap[c], c))[:3]
            if len(wrong) == 3:
                picks = [correct] + wrong
                controls.append({"part": part, "candidates": picks,
                                 "distances": {b: {c: f[b][c] for c in picks}
                                               for b in BAND_SETS}})
                used.update(picks)
                songs.add(song_of(part))
            break
    practice = None
    for part in by_exposure:
        if part in main or any(c["part"] == part for c in controls):
            continue
        names, f = full(part)
        if names is None:
            continue
        ranked = sorted(names, key=lambda c: (f["recording"][c], c))
        by_amp = {}
        for c in ranked:
            if c not in used and not re.search(r"\bbass\b", c, re.I):
                by_amp.setdefault(c.split(":")[0], c)
        extra = next((c for c in ranked if c not in used and c not in by_amp.values()
                      and gain_of(c) == "clean"), None)
        if len(by_amp) == 3 and extra:
            practice = {"part": part, "candidates": list(by_amp.values()) + [extra]}
            break
    return controls, practice


def notes_per_frame(x, rate: int, n: int = 8192, hop: int = 2048, harmonics: int = 8,
                    floor_db: float = -40.0, rel: float = 0.25, lowest: int = 33):
    """How many notes sound in each active frame of a clean guitar recording.

    In each frame (those within `floor_db` of the loudest), the strongest fundamental
    from A1 (MIDI `lowest`, low enough for drop tunings) to C#6 is found by its harmonic
    sum, its harmonics are removed, and that
    repeats while a fundamental keeps at least `rel` of the first one's strength."""
    import numpy as np

    x = np.asarray(x, dtype=float)
    if x.ndim > 1:
        x = x.mean(axis=1)
    window = np.hanning(n)
    f0s = 440 * 2 ** ((np.arange(lowest, 85) - 69) / 12)
    starts = range(0, len(x) - n, hop)
    rms = np.array([np.sqrt(np.mean(x[i:i + n] ** 2)) for i in starts])
    active = rms > rms.max() * 10 ** (floor_db / 20)
    counts = []
    for k, i in enumerate(starts):
        if not active[k]:
            continue
        mag = np.abs(np.fft.rfft(x[i:i + n] * window))
        found, first = 0, None
        for _ in range(8):
            salience = []
            for f0 in f0s:
                bins = [round(h * f0 * n / rate) for h in range(1, harmonics + 1)]
                salience.append(sum(mag[b - 1:b + 2].max() / h
                                    for h, b in enumerate(bins, 1) if b + 2 < len(mag)))
            j = int(np.argmax(salience))
            first = salience[j] if first is None else first
            if salience[j] < rel * first or salience[j] <= 0:
                break
            found += 1
            for h in range(1, harmonics + 1):
                b = round(h * f0s[j] * n / rate)
                mag[max(0, b - 3):b + 4] = 0
        counts.append(found)
    return np.array(counts)


def chord_share(x, rate: int, notes: int = 3) -> float:
    """The share of a clean recording's active frames in which `notes` or more notes
    sound. With three: near 1 for strummed chords, near 0 for a single-note line. An
    octave reads as part of the lower note, so double stops and power chords read as
    two notes: a part of mostly two-note shapes reads low on three and high on two."""
    counts = notes_per_frame(x, rate)
    return float((counts >= notes).mean()) if len(counts) else 0.0


def preset_values(path) -> dict:
    from format.parser import parse
    from format.structured import build

    preset = build(parse(pathlib.Path(path).read_bytes()))
    return {(p.module_path, p.key): p.value for p in preset.parameters}


def _drives(v: dict) -> list:
    """The gain of each active drive pedal."""
    out = []
    for slot, knob in ((1, "drive1Drive"), (2, "drive2Gain")):
        if str(v.get((f"drive{slot}", f"drive{slot}Active"), "false")).lower() == "true":
            out.append(float(v.get((f"drive{slot}", knob), 0.0)))
    return out


def gain_class(path, amp: str):
    """ "high" (a drive pedal at DRIVE_HIGH or more, or a PR12, whose volume is its gain,
    above HIGH_GAIN_VOLUME), "clean" (no drive pedal on and the volume at most
    CLEAN_VOLUME), or None for anything between, and for presets made for a bass: a
    control needs a difference any riff makes audible."""
    from plan_listening_validation import HIGH_GAIN_VOLUME

    if re.search(r"\bbass\b", pathlib.Path(path).stem, re.I):
        return None
    v = preset_values(path)
    drives = _drives(v)
    volume = float(v.get((f"{amp}Amp", f"{amp}Volume"), 0.0))
    if any(g >= DRIVE_HIGH for g in drives) or (amp == "pr12" and volume > HIGH_GAIN_VOLUME):
        return "high"
    return "clean" if not drives and volume <= CLEAN_VOLUME else None


def taste_features(path, amp: str) -> dict:
    """What a song-blind taste could follow in a preset: its amp, whether a drive pedal is
    on, the amp's volume and the highest active drive level."""
    v = preset_values(path)
    drives = _drives(v)
    return {"amp": amp, "drive_on": bool(drives), "drive": max(drives, default=0.0),
            "volume": float(v.get((f"{amp}Amp", f"{amp}Volume"), 0.0))}


def taste_class(path, amp: str) -> str:
    """The class a song-blind taste could prefer: the amp, and whether a drive is on."""
    return f"{amp}|{'drive' if _drives(preset_values(path)) else 'no drive'}"


def song_guitars(crops: pathlib.Path) -> dict:
    """{part: (song key, the song's guitar amp tracks in the instrumental mix, the
    part's own amp tracks)} for every crop."""
    out = {}
    for folder in sorted(crops.iterdir()):
        record_path = folder / "record.json"
        if not record_path.exists():
            continue
        r = json.loads(record_path.read_text())
        if r.get("split") != "development":
            continue
        vocals = set(r.get("vocal_tracks", []))
        guitars = {t for t in r.get("included_mix_tracks", []) if t not in vocals
                   and re.search(r"gtr|guit", t, re.I) and not re.search(r"bass", t, re.I)}
        out[folder.name] = ((r["source"], r["song"]), guitars | set(r["removed_own_amp_tracks"]),
                            set(r["removed_own_amp_tracks"]))
    return out


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
    from plan_listening_validation import preset_path

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
    from audition import shipped_riffs

    riff_share = {}
    for name, path in shipped_riffs().items():
        audio = io.load(path)
        riff_share[name] = round(chord_share(audio.mono(), audio.sample_rate), 3)
    split = (riff_share["chords"] + riff_share["line"]) / 2
    tastes = {p: {g: taste_class(renders[p][g]["preset"], renders[p][g]["amp"]) for g in G}
              for p in chosen}
    features = {p: {g: taste_features(renders[p][g]["preset"], renders[p][g]["amp"])
                    for g in G} for p in chosen}
    # Controls and practice, scored from the panels.
    reach = json.loads(REACH.expanduser().read_text())["distances"]
    gain_of = functools.lru_cache(maxsize=None)(
        lambda c: gain_class(preset_path(c), c.split(":", 1)[0]))
    guitars = song_guitars(crops)

    def closest(part):
        """The part's closest factory preset of a clear gain class."""
        d = reach.get(part) or {}
        names = {k.split("|")[0] for k in d if ":factory:" in k and gain_of(k.split("|")[0])}
        return min(names, key=lambda c: (d[f"{c}|full|recording"], c)) if names else None

    def clear_song(part, kind):
        """Every other guitar in the part's song is a part with a panel whose closest
        factory preset is of the same gain class."""
        song, tracks, _ = guitars[part]
        others = [q for q, (s2, _, _) in guitars.items() if s2 == song and q != part]
        known = set().union(*(guitars[q][2] for q in others + [part]))
        return tracks <= known and all(
            closest(q) is not None and gain_of(closest(q)) == kind for q in others)

    controls, practice = choose_controls(
        chosen + rest, set(chosen), lambda p: cues[p]["exposure_db"], reach, gain_of,
        lambda p: guitars[p][0], clear_song)
    if len(controls) < CONTROLS or practice is None:
        die("not enough parts for the controls and the practice trial")
    factory = {c: _sha(preset_path(c)) for x in controls + [practice] for c in x["candidates"]}
    # Each part plays through the riff in its own style: strummed chords or single notes.
    shares, pairs = {}, {}
    for p in chosen + [c["part"] for c in controls] + [practice["part"]]:
        audio = io.load(crops / p / "di.wav")
        shares[p] = round(chord_share(audio.mono(), audio.sample_rate), 3)
        pairs[p] = round(chord_share(audio.mono(), audio.sample_rate, notes=2), 3)
    styles = {p: "chords" if share >= split else "line" for p, share in shares.items()}
    audio = {p: {f: _sha(crops / p / f) for f in ("di.wav", "mix_instrumental.wav")}
             for p in chosen + [c["part"] for c in controls] + [practice["part"]]}
    out = {"schema": "listening-check-inputs-7", "parts": chosen, "cues": cues,
           "distances": distances, "presets": presets, "preset_sha256": preset_sha,
           "di_lufs": di_lufs, "riff_lufs": RIFF_LUFS, "taste_classes": tastes,
           "taste_features": features,
           "factory_sha256": factory, "audio_sha256": audio,
           "riff_chord_share": riff_share, "chord_share": shares,
           "two_note_share": pairs, "styles": styles,
           "g1_rule_chance_pass": round(g1_chance_pass(distances, chosen), 4),
           "controls": controls, "practice": practice,
           "renders_index_sha256": _sha(SHORTLISTS.expanduser() / "renders" / "index.json"),
           "amp_reach_sha256": _sha(REACH.expanduser())}
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(chosen)} parts, {len(controls)} controls; a random picker passes the G1 "
          f"rule {out['g1_rule_chance_pass']:.1%} of the time; sha256 {_sha(args.json)}")


# --- build --------------------------------------------------------------------------

def render_unchanged(data, part: str, out: pathlib.Path) -> float:
    """The largest change, in log, between the judge's distances for `part`'s four
    candidates rendered now through its own DI and the distances fixed in the inputs:
    whether the plugin still renders what the judge scored. (A fresh render differs from
    the stored one sample by sample, by about 10% RMS on the parts tried, while the
    judge's distances agree to three decimals.)"""
    import numpy as np
    import soundfile as sf

    import kill_tests as K
    import kill_tests_judge as KJ
    from benchmark_recordings import lag_samples

    crops = CROPS.expanduser()
    labelled = {g: pathlib.Path(data["presets"][part][g]).expanduser() for g in G}
    rendered = render_part((labelled, {"own": str(crops / part / "di.wav")}))
    files = {}
    for g in G:
        files[g] = out / f"render-check-{g}.wav"
        sf.write(str(files[g]), np.asarray(rendered[(g, "own")], dtype=np.float32), 48000,
                 subtype="FLOAT")
    _, scored = KJ.score_part((part, {g: str(f) for g, f in files.items()},
                               lag_samples(part) - K.LATENCY, crops))
    now = {(g, b): scored["d"].get(f"{g}|full|{b}") for g in G for b in BAND_SETS}
    if any(v is None for v in now.values()):
        die(f"the judge refused a fresh render of {part}: {sorted(k for k, v in now.items() if v is None)}")
    return max(abs(math.log(now[(g, b)] / data["distances"][part][b][g]))
               for g in G for b in BAND_SETS)


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
                if audio.ndim == 2:            # identical channels: mono, as the song is
                    audio = audio.mean(axis=1)
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
<p><code>Sitting {sitting}: 1A 2C 3? 4B</code> and so on, one answer for every trial.
Before you send it, it is checked against this page's trial numbers.</p>
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
    pattern = re.compile("|".join([LEAKS] + [rf"(?<!\w){re.escape(n)}(?!\w)"
                                            for n in names if n]), re.I)
    bad = []
    for path in folder.rglob("*"):
        if pattern.search(path.name):
            bad.append(str(path))
        elif path.suffix in (".html", ".txt", ".json"):
            # Embedded audio is base64, whose letters can spell anything ("/g3+").
            text = re.sub(r"data:[\w/+.-]+;base64,[A-Za-z0-9+/=]*", "", path.read_text())
            if pattern.search(text):
                bad.append(str(path))
    return bad


def plan_trials(parts, styles, controls, practice, rng):
    """Two sittings, each playing every part once through the riff in its own style
    (`styles[part]`), in its own shuffled order, so each part is heard twice, a sitting
    apart, with fresh letters. The practice trial opens sitting 1. Last, each sitting
    gets two controls, one in each half, each through its own style's riff."""
    sittings = {}
    for s in (1, 2):
        order = parts[:]
        rng.shuffle(order)
        sittings[s] = [{"kind": "main", "part": p, "riff": styles[p]} for p in order]
    sittings[1].insert(0, {"kind": "practice", "part": practice["part"],
                           "riff": styles[practice["part"]]})
    for s, pair in ((1, controls[0:2]), (2, controls[2:4])):
        # With n trials and two controls, the sitting has n + 2: the first half is
        # positions below (n + 2) // 2, and the early control goes after the practice.
        n = len(sittings[s])
        half_at = (n + 2) // 2
        sittings[s].insert(rng.randrange(1 if s == 1 else 0, half_at),
                           {"kind": "control", "part": pair[0]["part"],
                            "riff": styles[pair[0]["part"]]})
        sittings[s].insert(rng.randrange(half_at, n + 2),
                           {"kind": "control", "part": pair[1]["part"],
                            "riff": styles[pair[1]["part"]]})
    return sittings


def preset_names(data) -> list:
    """Every preset on trial by name: none may appear in the listener's folder."""
    names = {x.rsplit("/", 1)[-1] for c in data["controls"] + [data["practice"]]
             for x in c["candidates"]}
    names |= {path.stem for by_label in trial_candidates(data).values()
              for path in by_label.values()}
    return sorted(names)


def group_of(trial: dict) -> str:
    """Which candidate set a trial plays."""
    return "main" if trial["kind"] == "main" else trial["kind"]


def trial_candidates(data) -> dict:
    """{(group, part): {label: preset path}} for every candidate set. Keyed by the group
    as well as the part, since a part under test can also be a control."""
    out = {("main", p): {g: pathlib.Path(data["presets"][p][g]).expanduser() for g in G}
           for p in data["parts"]}
    for c in data["controls"]:
        out[("control", c["part"])] = {f"C{i}": factory_path(x)
                                       for i, x in enumerate(c["candidates"])}
    pr = data["practice"]
    out[("practice", pr["part"])] = {f"P{i}": factory_path(x)
                                     for i, x in enumerate(pr["candidates"])}
    return out


def unchanged(data) -> None:
    """Stop unless everything the inputs fixed is as it was: the shortlist renders index,
    the factory-preset panels, every factory and generated preset, and every song
    excerpt and DI the trials play."""
    if _sha(SHORTLISTS.expanduser() / "renders" / "index.json") != data["renders_index_sha256"]:
        die("the shortlist renders index changed since the inputs were fixed")
    if _sha(REACH.expanduser()) != data["amp_reach_sha256"]:
        die("the factory-preset panels changed since the inputs were fixed")
    for candidate, sha in data["factory_sha256"].items():
        if _sha(factory_path(candidate)) != sha:
            die(f"{factory_path(candidate)} is not the factory preset the panel scored")
    for p in data["parts"]:
        for g in G:
            path = pathlib.Path(data["presets"][p][g]).expanduser()
            if _sha(path) != data["preset_sha256"][p][g]:
                die(f"{path} is not the preset the judge scored for {p}")
    for part, files in data["audio_sha256"].items():
        for name, sha in files.items():
            if _sha(CROPS.expanduser() / part / name) != sha:
                die(f"{part}'s {name} changed since the inputs were fixed")


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
    unchanged(data)
    out = args.out_dir.expanduser()
    if out.exists() and any(out.iterdir()):
        die(f"{out} is not empty")
    private, listen = out / "private", out / "listen"
    candidates = trial_candidates(data)
    private.mkdir(parents=True)
    listen.mkdir()
    drift = render_unchanged(data, data["parts"][0], private)
    if drift > RENDER_DRIFT:
        die(f"the plugin no longer renders what the judge scored (a change of {drift:.3f} "
            f"in log distance, more than {RENDER_DRIFT})")
    riffs = shipped_riffs()
    rng = random.SystemRandom()
    pr = data["practice"]
    from concurrent.futures import ProcessPoolExecutor

    jobs = [(candidates[k], {r: riffs[r] for r in RIFFS}) for k in candidates]
    with ProcessPoolExecutor(args.workers) as ex:
        rendered = dict(zip(candidates, ex.map(render_part, jobs)))
    sittings = plan_trials(data["parts"], data["styles"], data["controls"], pr, rng)
    key = {"schema": "listening-check-key-3", "inputs_sha256": args.inputs_sha,
           "render_check_drift": drift,
           "preset_sha256": {f"{group}:{p}": {label: _sha(path)
                                               for label, path in by_label.items()}
                             for (group, p), by_label in candidates.items()},
           "sittings": {}}
    for s, trials in sittings.items():
        folder = listen / f"sitting-{s}"
        folder.mkdir()
        shown, number = [], 0
        for t in trials:
            number += 1
            part = t["part"]
            group = group_of(t)
            labels = list(candidates[(group, part)])
            rng.shuffle(labels)
            song = io.load(CROPS.expanduser() / part / "mix_instrumental.wav").mono()
            clips = {"song": np.asarray(song, dtype=np.float32)}
            for letter, label in zip(LETTERS, labels):
                clips[letter] = rendered[(group, part)][(label, t["riff"])]
            level = page_level([measure(a, 48000) for a in clips.values()])
            files = {}
            for name, audio in clips.items():
                loudness, _ = measure(audio, 48000)
                gained = np.asarray(audio, dtype=np.float64) * 10 ** ((level - loudness) / 20)
                # Fresh dither on every clip (TPDF, one 16-bit step), so a part's two
                # showings never match byte for byte.
                noise = np.random.default_rng(rng.getrandbits(64))
                lsb = 1 / 32768
                gained = gained + (noise.random(gained.shape) - noise.random(gained.shape)) * lsb
                fname = f"trial-{number:02d}-{name}.wav"
                sf.write(str(folder / fname), gained.astype(np.float32), 48000, subtype="PCM_16")
                files[name] = fname
            info = data["cues"][part]
            cue = (f"{info['song']}: the guitar track {info['track']}, which "
                   f"{info['how_it_plays']}.")
            if t["kind"] == "practice":
                cue = f"Practice, not scored. {cue}"
            shown.append({"number": number, "cue": cue, "song": files["song"],
                          "clips": {x: files[x] for x in LETTERS}})
            key["sittings"].setdefault(str(s), []).append(
                {"number": number, **t, "letters": dict(zip(LETTERS, labels)),
                 "level_lufs": round(level, 2),
                 "clips_sha256": {n: _sha(folder / f) for n, f in files.items()}})
        (folder / "index.html").write_text(page(s, shown))
    leaks = leak_check(listen, preset_names(data))
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


def block_p(blocks, draws: int | None = None) -> float:
    """One-sided p that a song-blind pick gives a sum at most the observed one.

    `blocks` holds one (values, picks, weights) per part: the four candidates' values in
    G order, lower meaning closer; the listener's answered picks on that part's trials
    (0, 1 or 2 indices; "can't tell" is left out, contributing 0 either way); and, for
    each answered trial, the four pick probabilities the null draws from (None for
    uniform). A part's two trials offer the same four presets, so they are not
    independent: the null draws the pair from its distribution given whether the two
    picks agree. Agreeing, one preset i is drawn in proportion to w1[i] * w2[i] and
    counted twice; differing, an ordered pair i != j in proportion to w1[i] * w2[j].
    Monte Carlo over `draws` redraws."""
    import numpy as np

    draws = draws or DRAWS
    observed = sum(values[p] for values, picks, _ in blocks for p in picks)
    rng = np.random.default_rng(20261005)
    plans = []
    for values, picks, weights in blocks:
        if not picks:
            continue
        values = np.asarray(values, dtype=float)
        w = [np.full(4, 0.25) if x is None else np.asarray(x, dtype=float) for x in weights]
        if len(picks) == 1:
            outcomes, prob = [values[i] for i in range(4)], w[0]
        elif picks[0] == picks[1]:
            outcomes, prob = [2 * values[i] for i in range(4)], w[0] * w[1]
        else:
            pairs = [(i, j) for i in range(4) for j in range(4) if i != j]
            outcomes = [values[i] + values[j] for i, j in pairs]
            prob = np.array([w[0][i] * w[1][j] for i, j in pairs])
        plans.append((np.asarray(outcomes), np.cumsum(prob / prob.sum())))
    hits, done = 0, 0
    while done < draws:
        n = min(50_000, draws - done)
        total = np.zeros(n)
        for outcomes, cum in plans:
            index = (rng.random((n, 1)) > cum[None]).sum(axis=1).clip(0, len(outcomes) - 1)
            total += outcomes[index]
        hits += int((total <= observed + 1e-12).sum())
        done += n
    return hits / draws


def taste_weights(features, picks, ridge: float = TASTE_RIDGE):
    """A song-blind taste fitted to the listener's own picks: a conditional logit over
    each candidate's preset features (`features[k]` is block k's four feature rows,
    `picks[k]` its answered picks), ridge-penalised. Returns each block's four pick
    probabilities. The fit sees the picks but never the song or the judge."""
    import numpy as np

    X = np.asarray(features, dtype=float)
    beta = np.zeros(X.shape[2])
    for _ in range(100):
        u = X @ beta
        prob = np.exp(u - u.max(axis=1, keepdims=True))
        prob /= prob.sum(axis=1, keepdims=True)
        grad, hess = -ridge * beta, -ridge * np.eye(len(beta))
        for k, block_picks in enumerate(picks):
            mean = prob[k] @ X[k]
            for p in block_picks:
                grad += X[k][p] - mean
                hess -= (X[k].T * prob[k]) @ X[k] - np.outer(mean, mean)
        step = np.linalg.solve(hess, grad)
        beta -= step
        if np.abs(step).max() < 1e-9:
            break
    u = X @ beta
    prob = np.exp(u - u.max(axis=1, keepdims=True))
    return prob / prob.sum(axis=1, keepdims=True)


def _ranks(values) -> list:
    """Each value's rank among the four, ties averaged, centred on 0 (-1.5 to 1.5)."""
    order = sorted(values)
    return [statistics.mean(i for i, u in enumerate(order) if u == v) - 1.5 for v in values]


def feature_rows(features: dict, parts) -> dict:
    """{part: four feature rows in G order}: PR12, SW50R (AC20 is the baseline), a drive
    pedal on, the amp's volume and the highest drive level (both standardised over every
    main candidate, so the scale never depends on the answers), and, within the part,
    the volume's and the drive level's ranks and whether each is the part's lowest: a
    taste for "the least gain of these four" is a within-part taste."""
    flat = [features[p][g] for p in parts for g in G]
    scale = {}
    for name in ("volume", "drive"):
        values = [f[name] for f in flat]
        mean = statistics.mean(values)
        scale[name] = (mean, statistics.pstdev(values) or 1.0)
    out = {}
    for p in parts:
        four = [features[p][g] for g in G]
        rank = {name: _ranks([f[name] for f in four]) for name in ("volume", "drive")}
        low = {name: min(f[name] for f in four) for name in ("volume", "drive")}
        out[p] = [[f["amp"] == "pr12", f["amp"] == "sw50r", f["drive_on"],
                   (f["volume"] - scale["volume"][0]) / scale["volume"][1],
                   (f["drive"] - scale["drive"][0]) / scale["drive"][1],
                   rank["volume"][i], rank["drive"][i],
                   f["volume"] == low["volume"], f["drive"] == low["drive"]]
                  for i, f in enumerate(four)]
    return out


def binomial_p(k: int, n: int, chance: float = 0.25) -> float:
    """Exact one-sided P(X >= k) for X ~ Binomial(n, chance)."""
    return sum(math.comb(n, i) * chance ** i * (1 - chance) ** (n - i) for i in range(k, n + 1))


def _median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def readings(rows, taste=None, draws: int | None = None) -> dict | None:
    """The declared readings over some main trials. Each row: `part`, `logs` (G label ->
    log d), `pick` (a G label or None), `classes` (G label -> taste class), `g1` and
    `template` (log d). `taste` is {riff: {part: four pick probabilities}} from
    `taste_weights`, fitted per riff; without it the taste p is not computed."""
    if not rows:
        return None
    by_part = collections.defaultdict(list)
    for r in rows:
        by_part[r["part"]].append(r)
    centred, pairs, picks, riffs = [], [], [], []
    gain = perfect = between = 0.0
    best = closer = clear = 0
    for part, part_rows in by_part.items():
        logs = [part_rows[0]["logs"][g] for g in G]
        mean = statistics.mean(logs)
        centred.append([v - mean for v in logs])
        # Pairs the judge separates clearly: a choice scores -1 for each candidate it
        # beats by more than CLEAR_PAIR, +1 for each that beats it by as much.
        pairs.append([-sum((v > u + CLEAR_PAIR) - (u > v + CLEAR_PAIR) for v in logs)
                      for u in logs])
        answered = [r for r in part_rows if r["pick"] is not None]
        picks.append([G.index(r["pick"]) for r in answered])
        riffs.append([(r["riff"], part) for r in answered])
        for r in part_rows:
            perfect += min(logs) - mean
            if r["pick"] is None:
                continue
            p = G.index(r["pick"])
            gain += logs[p] - mean
            # The part of c that choosing the class carries: the mean of the pick's
            # class among the four, less the mean of all four.
            mine = [v for g, v in zip(G, logs) if r["classes"][g] == r["classes"][r["pick"]]]
            between += statistics.mean(mine) - mean
            best += logs[p] == min(logs)
            closer += sum(v > logs[p] + CLEAR_PAIR for v in logs)
            clear += sum(abs(v - logs[p]) > CLEAR_PAIR for v in logs)
    # "Can't tell" delivers G1, the product's default.
    delivered = [r["g1"] if r["pick"] is None else r["logs"][r["pick"]] for r in rows]
    uniform = [[None] * len(x) for x in picks]
    tasted = None if taste is None else [[taste[r][p] for r, p in x] for x in riffs]
    return {
        "trials": len(rows), "sum_c": gain,
        "p": block_p(list(zip(centred, picks, uniform)), draws),
        "taste_p": None if taste is None else block_p(list(zip(centred, picks, tasted)),
                                                      draws),
        "sum_c_by_class": between, "sum_c_within_class": gain - between,
        "best_of_four": best, "best_of_four_p": binomial_p(best, len(rows)),
        "clear_pairs": clear, "clear_pairs_closer": closer,
        "clear_pairs_share": closer / clear if clear else None,
        # The p is for the net count (pairs the pick wins less pairs it loses).
        "clear_pairs_net_p": block_p(list(zip(pairs, picks, uniform)), draws),
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
    primary = not reasons and all(by_band_set[b]["all"]["p"] < 0.05
                                  and by_band_set[b]["all"]["taste_p"] < 0.05
                                  for b in BAND_SETS)
    return {"inconclusive": bool(reasons), "inconclusive_because": reasons,
            "primary_holds": primary, "main_path": primary}


def clear_style(data, part: str, split: float) -> bool:
    """Whether a part's style is clear: its chord share is more than STYLE_MARGIN from
    the split, and it is not a part of two-note shapes (most frames holding two notes
    or more while its chord share falls on the line side), which the measure reads as
    single notes."""
    share = data["chord_share"][part]
    two_note = data["two_note_share"][part] >= DYAD_SHARE and share < split
    return abs(share - split) > STYLE_MARGIN and not two_note


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
    for s, rows in key["sittings"].items():
        for t in rows:
            for name, sha in t["clips_sha256"].items():
                clip = out / "listen" / f"sitting-{s}" / f"trial-{t['number']:02d}-{name}.wav"
                if _sha(clip) != sha:
                    die(f"{clip} is not the clip that was built")
    built = {(int(s), t["number"]) for s, rows in key["sittings"].items() for t in rows}
    if set(answers) != built:
        die(f"the answer sheet does not answer exactly the built trials: missing "
            f"{sorted(built - set(answers))}, extra {sorted(set(answers) - built)}")
    result = {"answers_sha256": args.answers_sha, "key_sha256": args.key_sha,
              "g1_rule_chance_pass": data["g1_rule_chance_pass"], "by_band_set": {}}
    gaps = {p: data["di_lufs"][p] - data["riff_lufs"] for p in data["parts"]}
    gap_median = statistics.median(gaps.values())
    split = (data["riff_chord_share"]["chords"] + data["riff_chord_share"]["line"]) / 2
    controls, mains = collections.defaultdict(list), []
    for s, rows in key["sittings"].items():
        for t in rows:
            pick = answers[(int(s), t["number"])]
            if t["kind"] == "control":
                controls[s].append(pick is not None and t["letters"][pick] == "C0")
            elif t["kind"] == "main":
                mains.append((t, pick))
    # The song-blind taste, fitted to the main answers through each riff apart, so a
    # taste that changes with the riff is modelled too.
    features = feature_rows(data["taste_features"], data["parts"])
    taste = {}
    for riff in RIFFS:
        answered = collections.defaultdict(list)
        for t, pick in mains:
            if pick is not None and t["riff"] == riff:
                answered[t["part"]].append(G.index(t["letters"][pick]))
        fitted = taste_weights([features[p] for p in data["parts"]],
                               [answered[p] for p in data["parts"]])
        taste[riff] = {p: list(map(float, w)) for p, w in zip(data["parts"], fitted)}
    result["taste_weights"] = taste
    for bands in BAND_SETS:
        rows = []
        for t, pick in mains:
            d = data["distances"][t["part"]][bands]
            rows.append({"part": t["part"], "riff": t["riff"], "letter": pick,
                         "pick": None if pick is None else t["letters"][pick],
                         "logs": {g: math.log(d[g]) for g in G},
                         "classes": data["taste_classes"][t["part"]],
                         "g1": math.log(d["G1"]), "template": math.log(d["template+R"]),
                         "hot_di": gaps[t["part"]] > gap_median,
                         "clear_style": clear_style(data, t["part"], split)})
        result["by_band_set"][bands] = {
            "all": readings(rows, taste),
            "per_style": {riff: readings([r for r in rows if r["riff"] == riff], taste)
                         for riff in RIFFS},
            "clear_style": readings([r for r in rows if r["clear_style"]], taste),
            "style_unclear": readings([r for r in rows if not r["clear_style"]], taste),
            "di_hotter_than_median_gap": readings([r for r in rows if r["hot_di"]], taste),
            "di_nearer_the_riff": readings([r for r in rows if not r["hot_di"]], taste),
            "rows": rows}
    # Each part is heard twice with fresh letters: compare the presets picked.
    picked = collections.defaultdict(list)
    for t, pick in mains:
        picked[t["part"]].append(None if pick is None else t["letters"][pick])
    result["same_preset_both_times"] = {
        p: (None if None in v else v[0] == v[1]) for p, v in sorted(picked.items())}
    result["di_to_riff_gap_median_db"] = round(gap_median, 2)
    result["cant_tell"] = sum(pick is None for _, pick in mains)
    result["controls_hit"] = {s: hits for s, hits in sorted(controls.items())}
    result["void_sittings"] = [s for s, hits in sorted(controls.items()) if not any(hits)]
    result.update(decide(result["by_band_set"], result["cant_tell"],
                         sum(sum(h) for h in controls.values())))
    args.json.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "by_band_set"}, indent=1))


def listed_trials(listen: pathlib.Path) -> set:
    """{(sitting, trial number)} as the listener's pages show them: public, so checking
    a sheet against them reveals nothing about the key."""
    out = set()
    for page_path in sorted(listen.glob("sitting-*/index.html")):
        sitting = int(page_path.parent.name.split("-")[1])
        out |= {(sitting, int(n)) for n in re.findall(r"<h2>Trial (\d+)</h2>",
                                                      page_path.read_text())}
    return out


MOBILE_KBPS = 160             # mono AAC; keeps a sitting under 30 MiB for a phone

MOBILE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Listening check, sitting {sitting}</title>
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
.cue {{ color:var(--muted); margin:0 0 8px; }}
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
<h1>Listening check, sitting {sitting}</h1>
<p>For each trial: play the song, then A to D. Which of A to D sounds most like the
guitar named in the song? A–D all play the same riff, not the song's part, so listen
for the tone: gain, brightness, body. Tap a letter, or "?" if you can't tell. Answer
every trial; the line at the bottom fills in as you go. When all {count} are answered,
copy it and send it.</p>
{trials}
</main>
<div id="sheet"><input id="line" readonly aria-label="Your answer line">
<button id="copy" type="button">Copy answer line</button>
<button id="clear" type="button">Clear answers</button></div>
<script>
const SITTING = {sitting}, COUNT = {count}, KEY = "lc-{build}-sitting-" + SITTING;
let answers = {{}};
try {{ answers = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{}}
function render() {{
  document.querySelectorAll(".pick").forEach(group => {{
    const n = group.dataset.trial;
    group.querySelectorAll("button").forEach(b =>
      b.setAttribute("aria-pressed", String(answers[n] === b.dataset.value)));
  }});
  const done = Object.keys(answers).length;
  const parts = [];
  for (let n = 1; n <= COUNT; n++) if (answers[n]) parts.push(n + answers[n]);
  document.getElementById("line").value = "Sitting " + SITTING + ": " + parts.join(" ") +
    (done < COUNT ? "   (" + (COUNT - done) + " left)" : "");
}}
document.querySelectorAll(".pick button").forEach(b => b.addEventListener("click", () => {{
  answers[b.parentElement.dataset.trial] = b.dataset.value;
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


def mobile_page(args):
    """One self-contained page per sitting for a phone, built from the listener's own
    folder alone (never the key): each letter-named clip encoded as AAC at MOBILE_KBPS
    and embedded, with buttons that assemble the answer line."""
    import base64
    import subprocess
    import tempfile

    listen = args.out_dir.expanduser() / "listen"
    folder = listen / f"sitting-{args.sitting}"
    text = (folder / "index.html").read_text()
    found = re.findall(r'<section><h2>Trial (\d+)</h2><p class="cue">(.*?)</p>', text)
    if not found:
        die(f"no trials found in {folder / 'index.html'}")
    sections = []
    with tempfile.TemporaryDirectory() as tmp:
        for number, cue in found:
            rows = []
            for name in ("song", *LETTERS):
                clip = folder / f"trial-{int(number):02d}-{name}.wav"
                encoded = pathlib.Path(tmp) / "clip.m4a"
                subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b",
                                str(MOBILE_KBPS * 1000), str(clip), str(encoded)], check=True)
                data = base64.b64encode(encoded.read_bytes()).decode()
                label = "Song" if name == "song" else name
                rows.append(f'<div class="row"><b>{label}</b><audio controls preload="none" '
                            f'src="data:audio/mp4;base64,{data}"></audio></div>')
            buttons = "".join(f'<button type="button" data-value="{x}">{x}</button>'
                              for x in (*LETTERS, "?"))
            sections.append(f'<section><h2>Trial {number}</h2><p class="cue">{cue}</p>'
                            f'{"".join(rows)}<div class="pick" data-trial="{number}">'
                            f'{buttons}</div></section>')
    out = listen / f"sitting-{args.sitting}-phone.html"
    # Answers are saved in the browser per build and sitting, so a page from another
    # build never shows this one's trials pre-answered.
    build_id = hashlib.sha256(text.encode()).hexdigest()[:12]
    out.write_text(MOBILE.format(sitting=args.sitting, count=len(found), build=build_id,
                                 trials="\n".join(sections)))
    if not args.inputs:
        die("phone-page needs --inputs, to check the page for every preset's name")
    leaks = leak_check(listen, preset_names(json.loads(args.inputs.read_text())))
    if leaks:
        out.unlink()
        die(f"the phone page names what it must not: {leaks}")
    print(f"{out} ({out.stat().st_size / 1e6:.1f} MB, {len(found)} trials); "
          f"sha256 {_sha(out)}")


def check_sheet(args):
    """Whether an answer sheet can be scored, from the public pages alone: run before its
    hash is committed, so a format slip is mended while it still can be."""
    try:
        answers = parse_answers(args.answers.read_text())
    except ValueError as e:
        die(f"the sheet cannot be read: {e}")
    shown = listed_trials(args.out_dir.expanduser() / "listen")
    if not shown:
        die("no trial pages found")
    # A sheet may hold one sitting, checked as soon as that sitting ends.
    sittings = {s for s, _ in answers}
    shown = {t for t in shown if t[0] in sittings}
    missing, extra = sorted(shown - set(answers)), sorted(set(answers) - shown)
    if missing or extra:
        die(f"the sheet does not answer exactly the trials shown: missing {missing}, "
            f"extra {extra}")
    print(f"the sheet answers all {len(shown)} trials; its sha256 is {_sha(args.answers)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("inputs", "build", "phone-page", "check-sheet",
                                        "score"))
    ap.add_argument("--sitting", type=int, default=1)
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--inputs", type=pathlib.Path)
    ap.add_argument("--inputs-sha")
    ap.add_argument("--out-dir", type=pathlib.Path)
    ap.add_argument("--answers", type=pathlib.Path)
    ap.add_argument("--answers-sha")
    ap.add_argument("--key-sha")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    {"inputs": inputs, "build": build, "phone-page": mobile_page,
     "check-sheet": check_sheet, "score": score}[args.command](args)


if __name__ == "__main__":
    guarded(main)
