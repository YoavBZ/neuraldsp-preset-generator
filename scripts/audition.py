#!/usr/bin/env python3
"""Hear a shortlist before choosing: render each preset through a guitar DI and put the
renders on one local page beside the song.

    python scripts/audition.py --song SONG.mp3 --start 83 --out-dir DIR \\
        --preset A.xml --note "PR12 at the edge of breakup" \\
        --preset B.xml --note "SW50R, clean and bright" \\
        [--riff chords] [--di YOUR-DI.wav] [--open]

Without `--riff` or `--di` it plays the presets through every riff that ships in
`samples/riffs/` (a strummed chord progression and a single-note line, CC BY 4.0, see
`riffs.json`).

    python scripts/audition.py --add DIR --preset C2.xml --note "C, darker" [--open]

Every preset is rendered as it is, time effects included, each in a fresh plugin
process. A Tone King one gets a second of silence first, cut from the output, because a
fresh Tone King process starts muted. The song excerpt and every render play at one
loudness, so the page compares tone, not level: -20 LUFS, or lower when a clip could
not reach it without peaking above -1 dBFS, since every clip moves to the same level.
The raw renders are kept in `raw/`, so a page re-levels itself when a candidate is
added. Nothing is installed and no preset is changed. The page, the clips and
`audition.json` (which binds every clip to the preset, DI and song it came from, and
is saved after each candidate) are written to DIR.

The renders play another performance than the song's: the DI is not the song's
guitar. Listen for the tone (gain, brightness, body, space), not the notes.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import pathlib
import string
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

SCHEMA = "audition-v1"
TARGET_LUFS = -20.0
CEILING_DB = -1.0            # no clip peaks above this, after the loudness match
TONEKING_PREROLL_S = 1.0     # a fresh Tone King process is muted for up to 0.87 s
LETTERS = string.ascii_uppercase


def _sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def render(preset: pathlib.Path, di):
    """(mono float32 audio, pack id, amp or channel) for one preset through one DI, in
    a fresh plugin process."""
    import numpy as np

    from format.parser import parse
    from format.structured import build
    from match.renderer import _hash_audio
    from match.renderer_au import AudioUnitRenderer
    from match.renderer_preset import ToneKingPresetRenderer, toneking_channel
    from packs.loader import detect_pack
    from render_listening_guitar import SILENCE_PEAK, _amp, _settings_from_preset, _silent_preroll

    blob = preset.read_bytes()
    pack = detect_pack(build(parse(blob)).file_header)
    if pack is None:
        raise ValueError(f"{preset} is not a preset of any known pack")
    if pack.pack_id == "toneking":
        renderer = ToneKingPresetRenderer(preset, process_policy="fresh")
        settings, amp, preroll = {}, toneking_channel(blob), TONEKING_PREROLL_S
    elif pack.pack_id == "morgan":
        renderer = AudioUnitRenderer("morgan", process_policy="fresh")
        settings = _settings_from_preset(preset, pack, None)
        amp, preroll = _amp(settings, pack), 0.0
    else:
        raise ValueError(f"auditions render Morgan and Tone King presets, not {pack.display_name}")
    try:
        if pack.pack_id == "toneking":
            renderer.verify_preset_state()
        rate = renderer.metadata().sample_rate
        if rate != di.sample_rate:
            raise ValueError(f"the DI is at {di.sample_rate} Hz and the plugin renders at {rate}")
        source, frames = _silent_preroll(di.mono().astype(np.float32), rate, preroll)
        result = renderer.render(source, settings, di_sha256=_hash_audio(source))
        audio = np.asarray(result.audio, dtype=np.float32)[frames:]
    finally:
        renderer.close()
    if not len(audio) or float(np.abs(audio).max()) < SILENCE_PEAK:
        raise ValueError(f"{preset.name} rendered silence")
    return audio, pack.pack_id, amp


def measure(audio, rate):
    """(integrated loudness in LUFS, peak in dBFS) of a clip."""
    import numpy as np
    import pyloudnorm

    loudness = pyloudnorm.Meter(rate).integrated_loudness(audio)
    peak = float(np.abs(audio).max())
    if not np.isfinite(loudness) or peak <= 0:
        raise ValueError("a clip is too quiet to measure")
    return float(loudness), 20 * float(np.log10(peak))


def page_level(clips) -> float:
    """The one loudness every clip can reach without a peak above CEILING_DB, at most
    TARGET_LUFS. `clips` are (loudness, peak) pairs."""
    return min([TARGET_LUFS] + [loudness + CEILING_DB - peak for loudness, peak in clips])


def write_clip(path: pathlib.Path, audio, rate) -> None:
    import soundfile as sf

    sf.write(str(path), audio, rate, subtype="PCM_16")


def write_raw(path: pathlib.Path, audio, rate) -> None:
    import soundfile as sf

    path.parent.mkdir(exist_ok=True)
    sf.write(str(path), audio, rate, subtype="FLOAT")


def level_page(out: pathlib.Path, record: dict) -> None:
    """Write every clip from its raw render at the page's one loudness."""
    from analysis import io

    raws = {"song.wav": out / "raw" / "song.wav"}
    raws.update({name: out / "raw" / name for c in record["candidates"]
                 for name in c["renders"].values()})
    loaded = {name: io.load(path) for name, path in raws.items()}
    level = page_level([measure(a.samples, a.sample_rate) for a in loaded.values()])
    record["loudness_lufs"], record["gain_db"] = round(level, 2), {}
    for name, audio in loaded.items():
        loudness, _ = measure(audio.samples, audio.sample_rate)
        gain = level - loudness
        write_clip(out / name, audio.samples * 10 ** (gain / 20), audio.sample_rate)
        record["gain_db"][name] = round(gain, 2)


def save(out: pathlib.Path, record: dict) -> None:
    (out / "audition.json").write_text(json.dumps(record, indent=1) + "\n")


def add_candidates(out: pathlib.Path, record: dict, presets, notes, dis) -> None:
    """Render each preset through every DI of the audition, and record it, saving the
    record after each one so a failure leaves an audition `--add` can extend."""
    taken = {c["id"] for c in record["candidates"]}
    free = [x for x in LETTERS if x not in taken]
    if len(presets) > len(free):
        die(f"an audition holds at most {len(LETTERS)} candidates")
    for letter, preset, note in zip(free, presets, notes):
        preset = preset.expanduser().resolve()
        if not preset.is_file():
            die(f"no preset at {preset}")
        before = _sha(preset)
        entry = {"id": letter, "note": note, "preset": {"path": str(preset), "sha256": before},
                 "renders": {}}
        for d in record["dis"]:
            audio, pack_id, amp = render(preset, dis[d["id"]])
            name = f"{letter}-{d['id']}.wav"
            write_raw(out / "raw" / name, audio, dis[d["id"]].sample_rate)
            entry["renders"][d["id"]] = name
            entry["pack"], entry["amp"] = pack_id, amp
        if _sha(preset) != before:
            die(f"{preset} changed while it was rendered")
        record["candidates"].append(entry)
        save(out, record)
        print(f"{letter}: {preset.name} ({entry['amp']})", flush=True)


def _clock(seconds: float) -> str:
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Preset audition</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#ffffff;
        --accent:#9a4b16; --active:#fff3e6; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
        --bg:#171716; --fg:#ecebe6; --muted:#a19f97; --line:#34332f; --card:#201f1d;
        --accent:#f0a463; --active:#2c241c; }} }}
:root[data-theme="dark"] {{ --bg:#171716; --fg:#ecebe6; --muted:#a19f97; --line:#34332f;
        --card:#201f1d; --accent:#f0a463; --active:#2c241c; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg);
        font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
main {{ max-width: 760px; margin: 0 auto; padding: 24px 16px 48px; }}
h1 {{ font-size: 1.4rem; margin: 0 0 4px; }}
h2 {{ font-size: 1rem; margin: 28px 0 8px; color: var(--muted); font-weight: 600; }}
p.sub {{ color: var(--muted); margin: 0 0 16px; }}
.row {{ display:grid; grid-template-columns: 2.2rem 1fr; gap: 4px 12px; align-items:center;
        padding: 10px 12px; border:1px solid var(--line); border-radius: 10px;
        background: var(--card); margin-bottom: 8px; }}
.row.playing {{ background: var(--active); border-color: var(--accent); }}
.key {{ grid-row: span 2; font-weight: 700; font-size: 1.2rem; color: var(--accent);
        text-align:center; }}
.what {{ min-width: 0; overflow-wrap: anywhere; }}
.what .amp {{ font-weight: 600; }}
.what .note {{ color: var(--muted); }}
audio {{ width: 100%; height: 36px; }}
kbd {{ border:1px solid var(--line); border-radius:4px; padding:0 4px; font-size:.85em; }}
</style></head>
<body><main>
<h1>Preset audition</h1>
<p class="sub">{song_line}</p>
<p class="sub">Every candidate plays the same guitar riff, not the song's own part, and
every clip plays at one loudness. Listen for the tone (gain, brightness, body, space),
not the notes. Keys: <kbd>0</kbd> the song, <kbd>1</kbd>–<kbd>9</kbd> the candidates
of the riff you last played, switching at the same moment; <kbd>space</kbd> pause.</p>
<h2>The song</h2>
<div class="row" data-group="song" data-index="0"><div class="key">0</div>
<div class="what"><span class="amp">The song</span> <span class="note">{song_name}</span></div>
<audio controls loop preload="auto" src="{song_file}"></audio></div>
{sections}
</main>
<script>
const rows = [...document.querySelectorAll('.row')];
let group = rows.find(r => r.dataset.group !== 'song')?.dataset.group;
function play(row, at) {{
  const now = rows.find(r => r.classList.contains('playing'));
  const audio = row.querySelector('audio');
  if (now && now !== row) {{ now.querySelector('audio').pause(); }}
  if (at !== undefined && isFinite(at)) {{ try {{ audio.currentTime = at; }} catch (e) {{}} }}
  audio.play();
}}
rows.forEach(row => {{
  const audio = row.querySelector('audio');
  audio.addEventListener('play', () => {{
    rows.forEach(r => {{ if (r !== row) {{ r.classList.remove('playing'); r.querySelector('audio').pause(); }} }});
    row.classList.add('playing');
    if (row.dataset.group !== 'song') group = row.dataset.group;
  }});
  audio.addEventListener('pause', () => row.classList.remove('playing'));
}});
document.addEventListener('keydown', e => {{
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.target.closest('input, textarea')) return;
  const now = rows.find(r => r.classList.contains('playing'));
  if (e.key === ' ') {{ if (now) {{ e.preventDefault(); now.querySelector('audio').pause(); }} return; }}
  if (!/^[0-9]$/.test(e.key)) return;
  const n = Number(e.key);
  const target = n === 0 ? rows[0]
    : rows.find(r => r.dataset.group === group && Number(r.dataset.index) === n);
  if (!target) return;
  e.preventDefault();
  const sameGroup = now && now.dataset.group === target.dataset.group;
  play(target, sameGroup ? now.querySelector('audio').currentTime : undefined);
}});
</script>
</body></html>
"""


def page(record: dict) -> str:
    song = record["song"]
    song_line = (f"{html.escape(pathlib.Path(song['path']).name)}, "
                 f"{_clock(song['start_s'])}–{_clock(song['start_s'] + song['seconds'])}")
    sections = []
    for d in record["dis"]:
        rows = []
        for i, c in enumerate(record["candidates"], start=1):
            key = str(i) if i <= 9 else ""
            rows.append(
                f'<div class="row" data-group="{html.escape(d["id"])}" data-index="{i}">'
                f'<div class="key">{html.escape(c["id"])}<br><small>{key}</small></div>'
                f'<div class="what"><span class="amp">{html.escape(str(c["amp"]))}</span> '
                f'<span class="note">{html.escape(c["note"] or "")}</span></div>'
                f'<audio controls loop preload="auto" src="{html.escape(c["renders"][d["id"]])}">'
                f'</audio></div>')
        sections.append(f'<h2>Riff: {html.escape(d["name"])}</h2>\n' + "\n".join(rows))
    return PAGE.format(song_line=song_line, song_name=song_line,
                       song_file=html.escape(song["file"]), sections="\n".join(sections))


RIFFS = PLUGIN_ROOT / "samples" / "riffs"


def shipped_riffs() -> dict:
    """{name: path} of the riffs in samples/riffs/, each checked against riffs.json."""
    index = RIFFS / "riffs.json"
    if not index.exists():
        return {}
    out = {}
    for name, entry in json.loads(index.read_text())["riffs"].items():
        path = RIFFS / entry["file"]
        if path.exists() and _sha(path) == entry["sha256"]:
            out[name] = path
    return out


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--song", type=pathlib.Path, help="the song, any common audio format")
    ap.add_argument("--start", type=float, help="where in the song the part plays, in seconds")
    ap.add_argument("--seconds", type=float, default=12.0, help="how much of the song (default 12)")
    ap.add_argument("--riff", action="append", choices=sorted(shipped_riffs()),
                    help="a shipped riff to play the presets through; repeat for more "
                         "(default: every shipped riff, unless --di is given)")
    ap.add_argument("--di", type=pathlib.Path, action="append",
                    help="a guitar DI of your own to play the presets through; repeatable")
    ap.add_argument("--out-dir", type=pathlib.Path, help="a new folder for the audition")
    ap.add_argument("--add", type=pathlib.Path, metavar="DIR",
                    help="add presets to the audition in DIR, through its own DIs")
    ap.add_argument("--preset", type=pathlib.Path, action="append", required=True)
    ap.add_argument("--note", action="append", default=[],
                    help="one line per --preset, in order: why it is on the list")
    ap.add_argument("--open", action="store_true", help="open the page when done (macOS)")
    return ap


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("rendering an audition")
    from analysis import io

    if args.note and len(args.note) != len(args.preset):
        die("give one --note per --preset, or none")
    notes = args.note or [""] * len(args.preset)
    if args.add:
        if any(x is not None for x in (args.song, args.start, args.di, args.riff, args.out_dir)):
            die("--add takes only --preset, --note and --open")
        out = args.add.expanduser().resolve()
        record = json.loads((out / "audition.json").read_text())
        if record.get("schema") != SCHEMA:
            die(f"{out} is not an audition")
        dis = {}
        for d in record["dis"]:
            if _sha(d["path"]) != d["sha256"]:
                die(f"the DI {d['path']} changed since the audition was made")
            dis[d["id"]] = io.load(d["path"])
    else:
        if args.song is None or args.start is None or args.out_dir is None:
            die("a new audition needs --song, --start and --out-dir")
        riffs = shipped_riffs()
        chosen = args.riff or ([] if args.di else sorted(riffs))
        sources = [(name, riffs[name]) for name in chosen]
        for path in args.di or []:
            path = path.expanduser().resolve()
            sources.append((path.stem, path))
        out = args.out_dir.expanduser().resolve()
        if out.exists() and any(out.iterdir()):
            die(f"{out} is not empty; use --add to extend an audition")
        song_path = args.song.expanduser().resolve()
        song = io.load(song_path)
        first = round(args.start * song.sample_rate)
        last = first + round(args.seconds * song.sample_rate)
        if args.start < 0 or args.seconds <= 0 or last > song.frames:
            die(f"the song is {song.duration_s:.1f} s long; "
                f"{args.start:g}+{args.seconds:g} s does not fit")
        out.mkdir(parents=True, exist_ok=True)
        write_raw(out / "raw" / "song.wav", song.samples[first:last], song.sample_rate)
        record = {"schema": SCHEMA,
                  "song": {"path": str(song_path), "sha256": _sha(song_path),
                           "start_s": args.start, "seconds": args.seconds, "file": "song.wav"},
                  "dis": [], "candidates": []}
        dis = {}
        for i, (name, path) in enumerate(sources, start=1):
            dis[f"riff-{i}"] = io.load(path)
            record["dis"].append({"id": f"riff-{i}", "name": name, "path": str(path),
                                  "sha256": _sha(path)})
        save(out, record)
    add_candidates(out, record, args.preset, notes, dis)
    level_page(out, record)
    save(out, record)
    (out / "index.html").write_text(page(record))
    print(f"page: {out / 'index.html'}")
    if args.open:
        subprocess.run(["open", str(out / "index.html")], check=False)


if __name__ == "__main__":
    guarded(main)
