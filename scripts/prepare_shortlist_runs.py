#!/usr/bin/env python3
"""Sandboxes for the song-only shortlist runs, and the render manifest from their results.

    python scripts/prepare_shortlist_runs.py prepare --out-dir ~/ndsp-presets/runs/shortlists
    python scripts/prepare_shortlist_runs.py collect --out-dir ~/ndsp-presets/runs/shortlists

`docs/song-only-shortlist-plan.md`. `prepare` writes one sandbox per song of the 25
development parts amp reach used: an export of the plugin at HEAD without `docs/` and
`tests/`, each part's 10-second mix crop renamed `part-N.wav`, the request, a data root
holding a copy of the user's learned notes, and the brief the run follows. Which part
each `part-N` is stays in `parts-map.json`, outside the sandboxes.

`collect` checks every sandbox's `out/result.json` against the brief (four generated
presets and four factory ones per part, each list on at least two amps, factory
presets from the plugin's own folder and never `User/`) and writes the manifest
`render_shortlists.py` takes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

FACTORY = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite")
SOURCES = {"cambridge": "the Cambridge Music Technology \"Mixing Secrets\" multitrack library",
           "telefunken": "TELEFUNKEN Elektroakustik's \"Live From The Lab\" sessions"}
PYTHON = pathlib.Path("/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python")
NOTES = pathlib.Path("~/ndsp-presets/packs/morgan/learned-tones.md")
SEARCHES, FETCHES = 8, 12

BRIEF = """\
# Brief: a song-only preset run, under measurement

You are doing what the plugin's `generate` skill does for a user who supplies a song
and names a guitar part. Your presets will be measured afterwards; nothing you can
see here tells you how close they are, so don't look for that.

## Where things are

- The plugin: `{sandbox}/plugin`. Wherever the skill says `${{CLAUDE_PLUGIN_ROOT}}`,
  use that path.
- The skill to follow: `{sandbox}/plugin/skills/generate/SKILL.md`, and the
  references it links.
- The request: `{sandbox}/request.json`. One entry per part; each names the part's
  excerpt in `{sandbox}/excerpts/`.
- Your data root: `{sandbox}/data`. Pass `--data-dir {sandbox}/data` to `show.py`.
- Write everything you produce under `{sandbox}/out/`.
- Python: plain `python` runs the preset tools; for audio (`fingerprint.py`) use
  `{python}`.
- The plugin's factory presets, read-only: `{factory}` (never its `User/` folder).

## Rules

- Read nothing on disk outside `{sandbox}` and the factory folder above. In
  particular, nothing under `~/ndsp-presets` other than this sandbox, and nothing in
  any git checkout of this project. The measurement is void if you do.
- On the web, do not open this project's own repository or anything quoting it
  (`github.com/YoavBZ/neuraldsp-preset-generator`): its documents discuss these very
  recordings.
- Web: WebSearch and WebFetch only, at most {searches} searches and {fetches} fetches
  for this song in total. Download no files.
- Do not install presets anywhere, and do not write learned notes. Skip the skill's
  steps 6 and 7.
- You cannot ask the user anything. Where the skill would ask, state the assumption
  you made instead.
- The pack is Morgan Amps Suite. The template is the shipped
  `{sandbox}/plugin/samples/Example_Clean_PR12.xml`.
- The excerpts are a rough mix of the session (every track summed, vocals included),
  not a finished master. Fingerprint them with `--regime mix`.

## What to produce, per part

1. **Four generated presets, G1–G4,** written with `apply_spec.py` (dry-run first,
   then write) to `{sandbox}/out/<part>/G1.xml` … `G4.xml`. Use at least two of the
   three amps (AC20, PR12, SW50R). G1 is the one preset you would deliver to the user
   today; G2–G4 are the alternatives you would want them to hear next to it.
2. **Four factory presets, F1–F4,** from the factory folder, also on at least two
   amps: the ones you would play to the user as starting points. F1 is your first
   choice. Use `show.py --text` on any you consider.
3. Write `{sandbox}/out/result.json`:

```json
{{"parts": {{"part-1": {{
  "assumptions": "what you assumed about the part, and why",
  "fingerprint": {{"regime": "mix", "caveats": ["..."]}},
  "research": [{{"url": "...", "finding": "..."}}],
  "generated": [{{"label": "G1", "file": "out/part-1/G1.xml", "amp": "PR12",
                  "reason": "one line"}}],
  "factory": [{{"label": "F1", "preset": "Neural DSP/Blue Hotel", "amp": "PR12",
                "reason": "one line"}}],
  "files_read_outside_sandbox": ["every path you read outside {sandbox}"]
}}}}}}
```

`file` is relative to `{sandbox}`; `preset` is the path inside the factory folder,
without `.xml`. List all four of each, in order.

Your final reply: one line per part with G1's amp and F1, then any rule you could not
keep.
"""


def _sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).strip("_").lower()


def parts_by_song():
    """{(source, song, band): [(part slug, track name, excerpt start s)]}, for the parts
    amp reach used, in catalogue order."""
    from benchmark_recordings import CATALOG

    wanted = set(json.loads((PLUGIN_ROOT / "docs" / "amp-reach.json").read_text())["parts"])
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    out = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            if slug in wanted:
                if (p.get("split") or s.get("split")) != "development":
                    die(f"{slug} is not a development part")
                out.setdefault((s["source"], s["song"], s.get("group")), []).append(
                    (slug, p["part"]))
    if sum(map(len, out.values())) != len(wanted):
        die("the catalogue does not list every part amp reach used")
    return out


def prepare(args):
    out = args.out_dir.expanduser()
    if out.exists() and any(out.iterdir()):
        die(f"{out} is not empty")
    crops = args.crops_dir.expanduser()
    notes = NOTES.expanduser()
    commit = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    archive = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "archive", "--format=tar", "HEAD"],
                             capture_output=True, check=True).stdout
    mapping = {"commit": commit, "crops_dir": str(crops), "songs": {}}
    for (source, song, band), parts in parts_by_song().items():
        sandbox = out / "sandboxes" / _slug(song)
        plugin = sandbox / "plugin"
        plugin.mkdir(parents=True)
        subprocess.run(["tar", "-x", "-C", str(plugin), "--exclude", "docs",
                        "--exclude", "tests"], input=archive, check=True)
        (sandbox / "excerpts").mkdir()
        (sandbox / "out").mkdir()
        if notes.exists():
            (sandbox / "data" / "packs" / "morgan").mkdir(parents=True)
            shutil.copy2(notes, sandbox / "data" / "packs" / "morgan" / "learned-tones.md")
        request = {"band": band, "song": song, "source": SOURCES[source], "parts": {}}
        mapping["songs"][sandbox.name] = {}
        for n, (slug, track) in enumerate(parts, start=1):
            label = f"part-{n}"
            record = json.loads((crops / slug / "record.json").read_text())
            if record["split"] != "development":
                die(f"{slug}'s crop is not a development crop")
            shutil.copy2(crops / slug / "mix.wav", sandbox / "excerpts" / f"{label}.wav")
            start = record["excerpt_start_s"]
            request["parts"][label] = {
                "track_name": track, "excerpt": f"excerpts/{label}.wav",
                "excerpt_starts_at": f"{int(start // 60)}:{int(start % 60):02d}",
                "excerpt_seconds": record["excerpt_duration_s"],
                "ask": (f"A Morgan Amps Suite preset for the guitar part '{track}' in "
                        f"'{song}' by {band}, heard in this excerpt.")}
            mapping["songs"][sandbox.name][label] = {
                "part": slug, "mix_sha256": _sha(crops / slug / "mix.wav")}
        (sandbox / "request.json").write_text(json.dumps(request, indent=1) + "\n")
        (sandbox / "BRIEF.md").write_text(BRIEF.format(
            sandbox=sandbox, python=PYTHON, factory=FACTORY, searches=SEARCHES,
            fetches=FETCHES))
    (out / "parts-map.json").write_text(json.dumps(mapping, indent=1) + "\n")
    print(f"{len(mapping['songs'])} sandboxes, "
          f"{sum(map(len, mapping['songs'].values()))} parts, at {commit[:7]}")


def _amp_name(path: pathlib.Path) -> str:
    """The amp a Morgan preset selects, by the manifest's own names."""
    from format.parser import parse
    from format.structured import build

    members = json.loads((PLUGIN_ROOT / "packs" / "morgan" / "manifest.json").read_text())[
        "parameters"]["/selectedAmp"]["members"]
    stored = build(parse(path.read_bytes())).by_path.get(("", "selectedAmp"))
    return "none" if stored is None else members.get(str(int(float(stored.value))), "unknown")


def collect(args):
    out = args.out_dir.expanduser()
    mapping = json.loads((out / "parts-map.json").read_text())
    manifest, problems, amps = {"parts": {}}, [], {}
    for song, labels in mapping["songs"].items():
        sandbox = out / "sandboxes" / song
        result_path = sandbox / "out" / "result.json"
        if not result_path.exists():
            problems.append(f"{song}: no result.json")
            continue
        result = json.loads(result_path.read_text())["parts"]
        for label, entry in labels.items():
            got = result.get(label)
            if got is None:
                problems.append(f"{song}/{label}: missing")
                continue
            presets = {}
            for kind, prefix in (("generated", "G"), ("factory", "F")):
                rows = got.get(kind, [])
                if [r.get("label") for r in rows] != [f"{prefix}{i}" for i in range(1, 5)]:
                    problems.append(f"{song}/{label}: {kind} is not {prefix}1-{prefix}4")
                    continue
                for r in rows:
                    if kind == "generated":
                        path = (sandbox / r["file"]).resolve()
                        if sandbox.resolve() not in path.parents:
                            problems.append(f"{song}/{label}: {r['label']} is outside the sandbox")
                            continue
                    else:
                        path = (FACTORY / f"{r['preset']}.xml").resolve()
                        if FACTORY.resolve() not in path.parents or \
                                "User" in path.relative_to(FACTORY.resolve()).parts:
                            problems.append(f"{song}/{label}: {r['label']} is not a factory preset")
                            continue
                    if not path.exists():
                        problems.append(f"{song}/{label}: {r['label']} does not exist ({path})")
                        continue
                    presets[r["label"]] = str(path)
                found = {_amp_name(pathlib.Path(presets[r["label"]])) for r in rows
                         if r["label"] in presets}
                amps[f"{entry['part']}|{kind}"] = sorted(found)
                if len(found) < 2:
                    problems.append(f"{song}/{label}: {kind} uses one amp ({sorted(found)})")
            manifest["parts"][entry["part"]] = presets
    if problems:
        die("results do not follow the brief:\n  " + "\n  ".join(problems))
    path = out / "render-manifest.json"
    path.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(manifest['parts'])} parts; manifest at {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("prepare", "collect"))
    ap.add_argument("--out-dir", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    args = ap.parse_args()
    (prepare if args.command == "prepare" else collect)(args)


if __name__ == "__main__":
    guarded(main)
