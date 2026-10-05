#!/usr/bin/env python3
"""Sandboxes for the song-only shortlist runs, and the render manifest from their results.

    python scripts/prepare_shortlist_runs.py prepare --sandbox-dir ~/shortlist-sandboxes \\
        --out-dir ~/ndsp-presets/runs/shortlists
    python scripts/prepare_shortlist_runs.py collect --sandbox-dir ~/shortlist-sandboxes \\
        --out-dir ~/ndsp-presets/runs/shortlists

`docs/song-only-shortlist-plan.md`. `prepare` writes one sandbox per song of the 25
development parts amp reach used, outside the data root and outside any checkout:

- `plugin/`: the plugin at HEAD without `docs/`, `tests/`, any script the skills
  don't use, or the files that link the project's repository (the README,
  `SECURITY.md`, `.claude-plugin/`), so nothing in it points at the validation data,
  the results or the documents that discuss them;
- `excerpts/part-N.wav`: each part's 10-second mix crop, renamed;
- `request.json`: the ask, with a description of how the part plays, measured from
  its DI (pace and how much of the excerpt it plays in), and the session's guitar
  tracks. Playing only: nothing about its tone;
- `data/`: a data root holding a copy of the user's learned notes;
- `bin/python-audio`: the interpreter with the analysis extra;
- `BRIEF.md`: what the run does and may read.

Which part each `part-N` is stays in `parts-map.json` under `--out-dir`.

`collect` checks every result against the brief and writes the manifest
`render_shortlists.py` takes. Each part needs four distinct generated presets, each
re-made here from the shipped template with the `apply_spec.py` arguments the run
recorded and required to match, and none equal to a factory preset. It also needs four
distinct factory presets named exactly as in the plugin's folder (never `User/`).
Each list must be on at least two amps, and all 25 parts must be present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

FACTORY = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite")
SOURCES = {"cambridge": "the Cambridge Music Technology \"Mixing Secrets\" multitrack library",
           "telefunken": "TELEFUNKEN Elektroakustik's \"Live From The Lab\" sessions"}
PYTHON = pathlib.Path("/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python")
NOTES = pathlib.Path("~/ndsp-presets/packs/morgan/learned-tones.md")
LIBRARY_CROPS = pathlib.Path("~/ndsp-presets/references/validation-crops-2")
TEMPLATE = "samples/Example_Clean_PR12.xml"
SEARCHES, FETCHES = 8, 12
# The scripts the skills name, and what they import; nothing else is exported.
EXPORTED_SCRIPTS = ("__init__", "_cli", "_listening_trials", "_swift", "apply_spec",
                    "bootstrap_pack", "build_observed", "build_rab_audition",
                    "export_match_audition", "fingerprint", "log_blind_verdict",
                    "match_preset", "probe", "probe_state", "render_paired_reference", "show")
APPLY_FLAGS = {"--recipe": True, "--spec": True, "--bpm": True, "--name": True,
               "--strip-irs": False, "--allow-out-of-range": False}

BRIEF = """\
# Brief: a song-only preset run

You are doing what the plugin's `generate` skill does for a user who supplies a song
and names a guitar part. Work only from this sandbox, the plugin's factory presets
and the web.

## Where things are

- The plugin: `{sandbox}/plugin`. Wherever the skill says `${{CLAUDE_PLUGIN_ROOT}}`,
  use that path. Its `docs/` folder and its maintainer scripts are left out on
  purpose; skip any link into them.
- The skill to follow: `{sandbox}/plugin/skills/generate/SKILL.md`, and the
  references it links. Read that file; don't invoke a skill through the Skill tool,
  which would load another copy.
- The request: `{sandbox}/request.json`. One entry per part, each naming its excerpt
  in `{sandbox}/excerpts/` and describing how the part plays.
- Your data root: `{sandbox}/data`. Pass `--data-dir {sandbox}/data` to `show.py`.
- Write everything you produce under `{sandbox}/out/`.
- Python: plain `python` runs the preset tools; for audio (`fingerprint.py`) use
  `{sandbox}/bin/python-audio`.
- The plugin's factory presets, read-only: `{factory}` (not its `User/` folder).

## Rules

- Read nothing on disk outside `{sandbox}` and the factory folder.
- Every Bash command starts with `cd {sandbox} &&` (each command starts somewhere
  else otherwise). Read, Grep and Glob always get an absolute path inside the sandbox
  or the factory folder.
- Web: WebSearch and WebFetch only, at most {searches} searches and {fetches} fetches
  for this song in total. Don't open github.com. Download no files.
- Do not install presets anywhere, and do not write learned notes. Skip the skill's
  steps 6 and 7.
- You cannot ask the user anything. Where the skill would ask, state the assumption
  you made instead.
- The pack is Morgan Amps Suite. The template is
  `{sandbox}/plugin/{template}`.
- The excerpts are a rough mix of the session (every track summed, vocals included),
  not a finished master. Fingerprint them with `--regime mix`.

## What to produce, per part

1. **Four generated presets, G1–G4,** each written with `apply_spec.py` from the
   template above (dry-run first, then write) to `{sandbox}/out/<part>/G1.xml` …
   `G4.xml`. Keep each one's spec as `{sandbox}/out/<part>/G1.spec.json` and so on.
   Use at least two of the three amps (AC20, PR12, SW50R), and make the four differ.
   G1 is the one preset you would deliver to the user today; G2–G4 are the
   alternatives you would want them to hear next to it.
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
                  "apply_spec_args": ["--recipe", "amp/...", "--spec",
                                      "out/part-1/G1.spec.json", "--strip-irs"],
                  "reason": "one line"}}],
  "factory": [{{"label": "F1", "preset": "Neural DSP/Blue Hotel", "amp": "PR12",
                "reason": "one line"}}],
  "files_read_outside_sandbox": ["every path you read outside {sandbox}"]
}}}}}}
```

`file` and paths inside `apply_spec_args` are relative to `{sandbox}`.
`apply_spec_args` is exactly what you passed to `apply_spec.py` for the written file,
less `--template`, `--out` and `--force`; it may hold only `--recipe`, `--spec`,
`--bpm`, `--name`, `--strip-irs` and `--allow-out-of-range`. `preset` is the path
inside the factory folder, without `.xml`, spelled as on disk. List all four of each,
in order.

Your final reply: one line per part with G1's amp and F1, then any rule you could not
keep.
"""


def _sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).strip("_").lower()


def part_slug(source, song, part) -> str:
    return "-".join(x.replace("/", "_").replace(" ", "_") for x in (source, song, part))


def parts_by_song():
    """{(source, song, band): ([(part slug, track name)], [every guitar track name])},
    for the parts amp reach used, in catalogue order."""
    from benchmark_recordings import CATALOG

    wanted = set(json.loads((PLUGIN_ROOT / "docs" / "amp-reach.json").read_text())["parts"])
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    out = {}
    for s in catalog["sessions"]:
        guitars = [p["part"] for p in s["parts"]]
        for p in s["parts"]:
            slug = part_slug(s["source"], s["song"], p["part"])
            if slug in wanted:
                if (p.get("split") or s.get("split")) != "development":
                    die(f"{slug} is not a development part")
                key = (s["source"], s["song"], s.get("group"))
                out.setdefault(key, ([], guitars))[0].append((slug, p["part"]))
    if sum(len(v[0]) for v in out.values()) != len(wanted):
        die("the catalogue does not list every part amp reach used")
    return out


def pace_cuts():
    """The note rates splitting the DI library's riffs into thirds (`build_di_library`)."""
    import statistics

    from analysis import io
    from build_di_library import MIN_PLAYING, describe

    rates = []
    for crop in sorted(LIBRARY_CROPS.expanduser().iterdir()):
        record = crop / "record.json"
        if record.exists() and json.loads(record.read_text())["split"] == "development":
            di = io.load(crop / "di.wav")
            playing, notes, _ = describe(di.mono(), di.sample_rate)
            if playing >= MIN_PLAYING:
                rates.append(notes)
    return statistics.quantiles(rates, n=3)


def playing_description(di_path, cuts) -> str:
    from analysis import io
    from build_di_library import describe

    di = io.load(di_path)
    playing, notes, _ = describe(di.mono(), di.sample_rate)
    pace = ("sparser than most guitar parts" if notes < cuts[0] else
            "busier than most guitar parts" if notes > cuts[1] else "of a middling pace")
    where = ("through the whole excerpt" if playing >= 0.9 else
             "through most of the excerpt" if playing >= 0.6 else "in part of the excerpt")
    return f"plays {where}, about {notes:.0f} notes a second: {pace}"


def export_plugin(dest: pathlib.Path):
    archive = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "archive", "--format=tar", "HEAD"],
                             capture_output=True, check=True).stdout
    dest.mkdir(parents=True)
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    for gone in ("docs", "tests", ".github", ".claude-plugin"):
        shutil.rmtree(dest / gone, ignore_errors=True)
    for gone in ("README.md", "SECURITY.md"):        # both link the project's repository
        (dest / gone).unlink(missing_ok=True)
    for script in (dest / "scripts").glob("*.py"):
        if script.stem not in EXPORTED_SCRIPTS:
            script.unlink()


def prepare(args):
    sandboxes, out = args.sandbox_dir.expanduser(), args.out_dir.expanduser()
    for d in (sandboxes, out):
        if d.exists() and any(d.iterdir()):
            die(f"{d} is not empty")
    for forbidden in (pathlib.Path("~/ndsp-presets").expanduser(), PLUGIN_ROOT.parents[2]):
        if forbidden == sandboxes or forbidden in sandboxes.parents:
            die(f"sandboxes must sit outside {forbidden}")
    crops = args.crops_dir.expanduser()
    notes = NOTES.expanduser()
    commit = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    cuts = pace_cuts()
    mapping = {"commit": commit, "crops_dir": str(crops), "sandbox_dir": str(sandboxes),
               "pace_cuts": cuts, "songs": {}}
    for (source, song, band), (parts, guitars) in parts_by_song().items():
        sandbox = sandboxes / _slug(song)
        export_plugin(sandbox / "plugin")
        for sub in ("excerpts", "out", "bin"):
            (sandbox / sub).mkdir()
        wrapper = sandbox / "bin" / "python-audio"
        wrapper.write_text(f'#!/bin/sh\nexec "{PYTHON}" "$@"\n')
        wrapper.chmod(0o755)
        (sandbox / "data" / "packs" / "morgan").mkdir(parents=True)
        if notes.exists():
            shutil.copy2(notes, sandbox / "data" / "packs" / "morgan" / "learned-tones.md")
        request = {"band": band, "song": song, "source": SOURCES[source],
                   "guitar_tracks_in_the_session": guitars, "parts": {}}
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
                "how_it_plays": playing_description(crops / slug / "di.wav", cuts),
                "ask": (f"A Morgan Amps Suite preset for the guitar part '{track}' in "
                        f"'{song}' by {band}, heard in this excerpt.")}
            mapping["songs"][sandbox.name][label] = {
                "part": slug, "mix_sha256": _sha(crops / slug / "mix.wav")}
        (sandbox / "request.json").write_text(json.dumps(request, indent=1) + "\n")
        (sandbox / "BRIEF.md").write_text(BRIEF.format(
            sandbox=sandbox, factory=FACTORY, searches=SEARCHES, fetches=FETCHES,
            template=TEMPLATE))
    out.mkdir(parents=True, exist_ok=True)
    (out / "parts-map.json").write_text(json.dumps(mapping, indent=1) + "\n")
    print(f"{len(mapping['songs'])} sandboxes, "
          f"{sum(map(len, mapping['songs'].values()))} parts, at {commit[:7]}")


def factory_names():
    """{name as in the panels (path inside the folder, no .xml): path}, exact case."""
    names = {}
    for path in FACTORY.rglob("*.xml"):
        rel = path.relative_to(FACTORY)
        if rel.parts[0] != "User":
            names[str(rel.with_suffix(""))] = path
    return names


def _amp_name(path: pathlib.Path) -> str:
    """The amp a Morgan preset selects, by the manifest's own names."""
    from format.parser import parse
    from format.structured import build

    members = json.loads((PLUGIN_ROOT / "packs" / "morgan" / "manifest.json").read_text())[
        "parameters"]["/selectedAmp"]["members"]
    stored = build(parse(path.read_bytes())).by_path.get(("", "selectedAmp"))
    return "none" if stored is None else members.get(str(int(float(stored.value))), "unknown")


def sound(path: pathlib.Path) -> frozenset:
    """A preset's stored controls, less its name: two presets that sound alike match."""
    from format.parser import parse
    from format.structured import build

    return frozenset((p.module_path, p.key, str(p.value))
                     for p in build(parse(path.read_bytes())).parameters
                     if (p.module_path, p.key) != ("", "name"))


def remade(sandbox: pathlib.Path, args) -> pathlib.Path | str:
    """The preset `apply_spec.py` writes from the shipped template with `args`, or why
    the arguments are refused."""
    i = 0
    while i < len(args):
        flag = args[i]
        if flag not in APPLY_FLAGS:
            return f"apply_spec argument {flag!r} is not allowed"
        if APPLY_FLAGS[flag]:
            if i + 1 >= len(args):
                return f"{flag} has no value"
            if flag == "--spec":
                spec = (sandbox / args[i + 1]).resolve()
                if sandbox.resolve() not in spec.parents or not spec.is_file():
                    return f"the spec {args[i + 1]} is not a file in the sandbox"
            i += 2
        else:
            i += 1
    out = pathlib.Path(tempfile.mkdtemp()) / "remade.xml"
    run = subprocess.run([sys.executable, str(sandbox / "plugin" / "scripts" / "apply_spec.py"),
                          "--template", str(sandbox / "plugin" / TEMPLATE), "--out", str(out),
                          *args], cwd=sandbox, capture_output=True, text=True)
    if run.returncode != 0:
        return f"apply_spec failed: {run.stderr.strip()[-300:]}"
    return out


def collect(args):
    sandboxes, out = args.sandbox_dir.expanduser(), args.out_dir.expanduser()
    mapping = json.loads((out / "parts-map.json").read_text())
    factory = factory_names()
    factory_sounds = {sound(p) for p in factory.values()}
    manifest, problems, amps = {"parts": {}}, [], {}
    for song, labels in mapping["songs"].items():
        sandbox = sandboxes / song
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
                sounds = []
                for r in rows:
                    where = f"{song}/{label}/{r['label']}"
                    if kind == "generated":
                        path = (sandbox / r["file"]).resolve()
                        if sandbox.resolve() not in path.parents or not path.is_file():
                            problems.append(f"{where}: not a file in the sandbox")
                            continue
                        again = remade(sandbox, r.get("apply_spec_args", []))
                        if isinstance(again, str):
                            problems.append(f"{where}: {again}")
                            continue
                        if sound(again) != sound(path):
                            problems.append(f"{where}: its recorded arguments make another preset")
                            continue
                        if sound(path) in factory_sounds:
                            problems.append(f"{where}: is a factory preset")
                            continue
                    else:
                        if r.get("preset") not in factory:
                            problems.append(f"{where}: {r.get('preset')!r} is not a factory preset")
                            continue
                        path = factory[r["preset"]]
                    sounds.append(sound(path))
                    presets[r["label"]] = str(path)
                if len(sounds) == 4 and len(set(sounds)) < 4:
                    problems.append(f"{song}/{label}: {kind} repeats a preset")
                found = {_amp_name(pathlib.Path(presets[r["label"]])) for r in rows
                         if r["label"] in presets}
                amps[f"{entry['part']}|{kind}"] = sorted(found)
                if not found <= {"AC20", "PR12", "SW50R"} or len(found) < 2:
                    problems.append(f"{song}/{label}: {kind} is on {sorted(found)}, "
                                    "not two or more of AC20, PR12 and SW50R")
            manifest["parts"][entry["part"]] = presets
    expected = sum(map(len, mapping["songs"].values()))
    if len(manifest["parts"]) != expected:
        problems.append(f"{len(manifest['parts'])} parts of {expected} have results")
    if problems:
        die("results do not follow the brief:\n  " + "\n  ".join(problems))
    path = out / "render-manifest.json"
    path.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(manifest['parts'])} parts; manifest at {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("prepare", "collect"))
    ap.add_argument("--sandbox-dir", type=pathlib.Path, required=True)
    ap.add_argument("--out-dir", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    args = ap.parse_args()
    (prepare if args.command == "prepare" else collect)(args)


if __name__ == "__main__":
    guarded(main)
