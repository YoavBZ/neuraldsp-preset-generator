#!/usr/bin/env python3
"""Sandboxes for the song-only shortlist runs, and the render manifest from their results.

    python scripts/prepare_shortlist_runs.py prepare --sandbox-dir ~/shortlist-sandboxes \\
        --out-dir ~/ndsp-presets/runs/shortlists
    python scripts/prepare_shortlist_runs.py redo SONG --sandbox-dir ... --out-dir ...
    python scripts/prepare_shortlist_runs.py collect --sandbox-dir ... --out-dir ... \\
        [--exclude SONG ...]

`docs/song-only-shortlist-plan.md`. `prepare` writes one sandbox per song of the 25
development parts amp reach used, outside the data root and outside any checkout:

- `plugin/`: the plugin at HEAD without `docs/`, `tests/`, any script the skills don't
  use, or the files that name or link the project (the README, `SECURITY.md`,
  `pyproject.toml`, `.claude-plugin/`). Nothing in it names the validation data or
  the results; `packs/paths.py` does name the default data root;
- `excerpts/part-N.wav`: each part's 10-second mix crop, renamed;
- `request.json`: the ask; the guitar tracks in the session's mix; and how the part
  plays, measured from its DI (pace, and how much of the excerpt it plays in).
  Playing only: nothing about its tone;
- `data/`: a data root holding a copy of the user's learned notes;
- `bin/python-audio`: the interpreter with the analysis extra;
- `BRIEF.md`: what the run does and may read.

Which part each `part-N` is, and a hash of each sandbox's plugin, stay in
`parts-map.json` under `--out-dir`. `redo` moves a flagged song's sandbox aside and
builds it afresh.

`collect` checks every result against the brief and writes the manifest
`render_shortlists.py` takes:

- **sandbox plugin:** it must still hash as built;
- **generated presets:** four per part, each re-made from a clean export of the declared
  commit with the `apply_spec.py` arguments the run recorded, and required to match;
- **factory presets:** four per part, named exactly as in the plugin's folder (never
  `User/`);
- **within each list:** distinct in what is scored (the selected amp's modules and the
  shared ones, less what the rule set R switches off); on at least two amps; no
  generated preset equal to a factory one in that sense;
- **coverage:** every part present, except songs passed with `--exclude`. More than 5
  parts excluded voids the measurement.
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
MAX_EXCLUDED = 5
# The scripts the skills name, and what they import; nothing else is exported.
EXPORTED_SCRIPTS = ("__init__", "_cli", "_listening_trials", "_swift", "apply_spec",
                    "bootstrap_pack", "build_observed", "build_rab_audition",
                    "export_match_audition", "fingerprint", "log_blind_verdict",
                    "match_preset", "probe", "probe_state", "render_paired_reference", "show")
STRIPPED = ("docs", "tests", ".github", ".claude-plugin", "README.md", "SECURITY.md",
            "pyproject.toml")
APPLY_FLAGS = {"--recipe": True, "--spec": True, "--bpm": True, "--name": True,
               "--pack": True, "--strip-irs": False, "--allow-out-of-range": False}
AMP_MODULES = {"AC20": ("ac20Amp", "ac20EQ"), "PR12": ("pr12Amp", "pr12EQ"),
               "SW50R": ("sw50rAmp", "sw50rEQ")}
# What the rule set R (render_preset_panel.RULE_SET) switches off or fixes, so it is
# never heard in a scored render.
UNSCORED_MODULES = {"delay", "tremolo", "reverb"}
UNSCORED_KEYS = {("parameters", "gateActive"), ("parameters", "gateThreshold"),
                 ("parameters", "doublerActive"), ("parameters", "doublerSpread"),
                 ("parameters", "transpose"), ("fxParameters", "sectionActive"),
                 ("sw50rAmp", "sw50rReverb"), ("pr12Amp", "pr12Reverb"), ("", "name")}

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
- Write everything you produce, scratch files included, under `{sandbox}/out/`
  (not `/tmp`). Write spec and result JSON files with the Write tool, not a Bash
  heredoc.
- Python: plain `python` runs the preset tools; for audio (`fingerprint.py`) use
  `{sandbox}/bin/python-audio`.
- The plugin's factory presets, read-only: `{factory}` (not its `User/` folder).

## Rules

- Read nothing on disk outside `{sandbox}` and the factory folder.
- Every Bash command starts with `cd {sandbox} &&` and uses paths inside the sandbox
  (or the factory folder); no other `cd`, no `..` out of the sandbox, no `~`, `$HOME`
  or command substitution. Read, Grep and Glob always get an absolute path inside the
  sandbox or the factory folder.
- Web: WebSearch and WebFetch only, at most {searches} searches and {fetches} fetches
  for this song in total. Pass `blocked_domains: ["github.com",
  "githubusercontent.com"]` on every WebSearch, and don't open github.com. Download
  nothing, and don't use curl, wget or Python to reach the web.
- Do not install presets anywhere, and do not write learned notes. Skip the skill's
  steps 6 and 7.
- You cannot ask the user anything. Where the skill would ask, state the assumption
  you made instead.
- The pack is Morgan Amps Suite. The template is
  `{sandbox}/plugin/{template}`.
- The excerpts are a rough mix of the session (every track summed, vocals included),
  not a finished master. Fingerprint them with `--regime mix`.

## What to produce, per part, in this order

1. **G1:** the one preset you would deliver to the user today, written as the skill
   says, with `apply_spec.py` from the template above (dry-run first, then write) to
   `{sandbox}/out/<part>/G1.xml`, its spec kept as `{sandbox}/out/<part>/G1.spec.json`.
2. **G2–G4:** three alternatives you would want the user to hear next to G1, written
   the same way (`G2.xml` … `G4.xml`). Across G1–G4 use at least two of the three amps
   (AC20, PR12, SW50R), and make them differ in amp, gain, drive, EQ or cab, not only
   in reverb, delay or modulation.
3. **Only after G1–G4 are written for every part, F1–F4:** four factory presets from
   the factory folder, on at least two amps, that you would play to the user as
   starting points. F1 is your first choice. Use `show.py --text` on any you consider.
   Don't open the factory folder before then.
4. Write `{sandbox}/out/result.json`:

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
`--bpm`, `--name`, `--pack`, `--strip-irs` and `--allow-out-of-range`. `preset` is the
path inside the factory folder, without `.xml`, spelled as on disk. List all four of
each, in order.

Your final reply: one line per part with G1's amp and F1, then any rule you could not
keep.
"""


def _sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def tree_sha(root: pathlib.Path) -> str:
    """One hash over every file under `root`: its relative path and its bytes."""
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(str(path.relative_to(root)).encode() + b"\0" + _sha(path).encode() + b"\n")
    return h.hexdigest()


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).strip("_").lower()


def part_slug(source, song, part) -> str:
    return "-".join(x.replace("/", "_").replace(" ", "_") for x in (source, song, part))


def main_checkout() -> pathlib.Path:
    """The repository's main checkout, whichever worktree this runs from."""
    common = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "--git-common-dir"],
                            capture_output=True, text=True, check=True).stdout.strip()
    return (PLUGIN_ROOT / common).resolve().parent


def parts_by_song():
    """{(source, song, band): [(part slug, track name)]}, for the parts amp reach used,
    in catalogue order."""
    from benchmark_recordings import CATALOG

    wanted = set(json.loads((PLUGIN_ROOT / "docs" / "amp-reach.json").read_text())["parts"])
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    out = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = part_slug(s["source"], s["song"], p["part"])
            if slug in wanted:
                if (p.get("split") or s.get("split")) != "development":
                    die(f"{slug} is not a development part")
                out.setdefault((s["source"], s["song"], s.get("group")), []).append(
                    (slug, p["part"]))
    if sum(map(len, out.values())) != len(wanted):
        die("the catalogue does not list every part amp reach used")
    return out


def guitar_tracks(record) -> list:
    """The guitar tracks in a crop's mix, by file name."""
    names = [pathlib.Path(t).stem for t in record.get("included_mix_tracks", [])]
    return [n for n in names if any(w in n.lower() for w in ("gtr", "guitar"))]


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
    return f"plays {where}, about {notes:.1f} notes a second: {pace}"


def export_plugin(dest: pathlib.Path, commit: str = "HEAD"):
    archive = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "archive", "--format=tar", commit],
                             capture_output=True, check=True).stdout
    dest.mkdir(parents=True)
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    for gone in STRIPPED:
        target = dest / gone
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    for script in (dest / "scripts").glob("*.py"):
        if script.stem not in EXPORTED_SCRIPTS:
            script.unlink()


def build_sandbox(sandbox, commit, source, song, band, parts, crops, cuts):
    """One song's sandbox; returns its parts-map entry."""
    export_plugin(sandbox / "plugin", commit)
    for sub in ("excerpts", "out", "bin"):
        (sandbox / sub).mkdir()
    wrapper = sandbox / "bin" / "python-audio"
    wrapper.write_text(f'#!/bin/sh\nexec "{PYTHON}" "$@"\n')
    wrapper.chmod(0o755)
    (sandbox / "data" / "packs" / "morgan").mkdir(parents=True)
    notes = NOTES.expanduser()
    if notes.exists():
        shutil.copy2(notes, sandbox / "data" / "packs" / "morgan" / "learned-tones.md")
    request = {"band": band, "song": song, "source": SOURCES[source], "parts": {}}
    entry = {"source": source, "song": song, "band": band, "parts": {}}
    for n, (slug, track) in enumerate(parts, start=1):
        label = f"part-{n}"
        record = json.loads((crops / slug / "record.json").read_text())
        if record["split"] != "development":
            die(f"{slug}'s crop is not a development crop")
        request.setdefault("guitar_tracks_in_the_mix", guitar_tracks(record))
        shutil.copy2(crops / slug / "mix.wav", sandbox / "excerpts" / f"{label}.wav")
        start = record["excerpt_start_s"]
        request["parts"][label] = {
            "track_name": track, "excerpt": f"excerpts/{label}.wav",
            "excerpt_starts_at": f"{int(start // 60)}:{int(start % 60):02d}",
            "excerpt_seconds": record["excerpt_duration_s"],
            "how_it_plays": playing_description(crops / slug / "di.wav", cuts),
            "ask": (f"A Morgan Amps Suite preset for the guitar part '{track}' in "
                    f"'{song}' by {band}, heard in this excerpt.")}
        entry["parts"][label] = {"part": slug, "track": track,
                                 "mix_sha256": _sha(crops / slug / "mix.wav")}
    (sandbox / "request.json").write_text(json.dumps(request, indent=1) + "\n")
    (sandbox / "BRIEF.md").write_text(BRIEF.format(
        sandbox=sandbox, factory=FACTORY, searches=SEARCHES, fetches=FETCHES,
        template=TEMPLATE))
    entry["plugin_sha256"] = tree_sha(sandbox / "plugin")
    return entry


def prepare(args):
    sandboxes, out = args.sandbox_dir.expanduser().resolve(), args.out_dir.expanduser()
    for d in (sandboxes, out):
        if d.exists() and any(d.iterdir()):
            die(f"{d} is not empty")
    for forbidden in (pathlib.Path("~/ndsp-presets").expanduser().resolve(), main_checkout()):
        if forbidden == sandboxes or forbidden in sandboxes.parents:
            die(f"sandboxes must sit outside {forbidden}")
    crops = args.crops_dir.expanduser()
    commit = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    cuts = pace_cuts()
    mapping = {"commit": commit, "crops_dir": str(crops), "sandbox_dir": str(sandboxes),
               "pace_cuts": cuts, "songs": {}}
    for (source, song, band), parts in parts_by_song().items():
        entry = build_sandbox(sandboxes / _slug(song), commit, source, song, band, parts,
                              crops, cuts)
        entry["attempt"] = 1
        mapping["songs"][_slug(song)] = entry
    out.mkdir(parents=True, exist_ok=True)
    (out / "parts-map.json").write_text(json.dumps(mapping, indent=1) + "\n")
    print(f"{len(mapping['songs'])} sandboxes, "
          f"{sum(len(s['parts']) for s in mapping['songs'].values())} parts, at {commit[:7]}")


def redo(args):
    """Move a flagged song's sandbox aside and build it afresh, at the declared commit."""
    out = args.out_dir.expanduser()
    mapping = json.loads((out / "parts-map.json").read_text())
    entry = mapping["songs"].get(args.song)
    if entry is None:
        die(f"no song {args.song!r}")
    sandboxes = pathlib.Path(mapping["sandbox_dir"])
    aside = sandboxes / "_flagged" / f"{args.song}-{entry['attempt']}"
    aside.parent.mkdir(exist_ok=True)
    shutil.move(str(sandboxes / args.song), str(aside))
    parts = [(p["part"], p["track"]) for p in entry["parts"].values()]
    fresh = build_sandbox(sandboxes / args.song, mapping["commit"], entry["source"],
                          entry["song"], entry["band"], parts,
                          pathlib.Path(mapping["crops_dir"]), mapping["pace_cuts"])
    fresh["attempt"] = entry["attempt"] + 1
    mapping["songs"][args.song] = fresh
    (out / "parts-map.json").write_text(json.dumps(mapping, indent=1) + "\n")
    print(f"{args.song}: attempt {fresh['attempt']}; the flagged run is at {aside}")


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


def sound(path: pathlib.Path, scored: bool = False) -> frozenset:
    """A preset's stored controls, less its name. With `scored`, only what a render under
    R can hear: the selected amp's modules and the shared ones, less what R turns off."""
    from format.parser import parse
    from format.structured import build

    params = build(parse(path.read_bytes())).parameters
    out = {(p.module_path, p.key, str(p.value)) for p in params
           if (p.module_path, p.key) != ("", "name")}
    if not scored:
        return frozenset(out)
    amp = _amp_name(path)
    others = {m for a, mods in AMP_MODULES.items() if a != amp for m in mods}
    return frozenset((m, k, v) for m, k, v in out
                     if m not in UNSCORED_MODULES and m not in others
                     and (m, k) not in UNSCORED_KEYS)


def remade(sandbox: pathlib.Path, clean: pathlib.Path, args) -> pathlib.Path | str:
    """The preset `apply_spec.py` writes from a clean export's template and recipes with
    `args` (spec paths relative to the sandbox), or why the arguments are refused."""
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
            if flag == "--pack" and args[i + 1] != "morgan":
                return "--pack must be morgan"
            i += 2
        else:
            i += 1
    out = pathlib.Path(tempfile.mkdtemp()) / "remade.xml"
    run = subprocess.run([sys.executable, str(clean / "scripts" / "apply_spec.py"),
                          "--template", str(clean / TEMPLATE), "--out", str(out), *args],
                         cwd=sandbox, capture_output=True, text=True)
    if run.returncode != 0:
        return f"apply_spec failed: {run.stderr.strip()[-300:]}"
    return out


def collect(args):
    sandboxes, out = args.sandbox_dir.expanduser(), args.out_dir.expanduser()
    mapping = json.loads((out / "parts-map.json").read_text())
    unknown = sorted(set(args.exclude) - set(mapping["songs"]))
    if unknown:
        die(f"no such songs to exclude: {unknown}")
    excluded = {s: [p["part"] for p in mapping["songs"][s]["parts"].values()]
                for s in args.exclude}
    if sum(map(len, excluded.values())) > MAX_EXCLUDED:
        die(f"{sum(map(len, excluded.values()))} parts excluded, more than {MAX_EXCLUDED}: "
            "the measurement is void")
    clean = pathlib.Path(tempfile.mkdtemp()) / "plugin"
    export_plugin(clean, mapping["commit"])
    factory = factory_names()
    factory_scored = {sound(p, scored=True) for p in factory.values()}
    manifest = {"parts": {}, "sha256": {}, "excluded": excluded}
    problems = []
    for song, entry in mapping["songs"].items():
        if song in excluded:
            continue
        sandbox = sandboxes / song
        if tree_sha(sandbox / "plugin") != entry["plugin_sha256"]:
            problems.append(f"{song}: the sandbox's plugin was changed")
        result_path = sandbox / "out" / "result.json"
        if not result_path.exists():
            problems.append(f"{song}: no result.json")
            continue
        result = json.loads(result_path.read_text())["parts"]
        for label, part in entry["parts"].items():
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
                scored = []
                for r in rows:
                    where = f"{song}/{label}/{r['label']}"
                    if kind == "generated":
                        path = (sandbox / str(r.get("file"))).resolve()
                        if sandbox.resolve() not in path.parents or not path.is_file():
                            problems.append(f"{where}: not a file in the sandbox")
                            continue
                        again = remade(sandbox, clean, r.get("apply_spec_args", []))
                        if isinstance(again, str):
                            problems.append(f"{where}: {again}")
                            continue
                        if sound(again) != sound(path):
                            problems.append(f"{where}: its recorded arguments make another preset")
                            continue
                        if sound(path, scored=True) in factory_scored:
                            problems.append(f"{where}: sounds as a factory preset does")
                            continue
                    else:
                        if r.get("preset") not in factory:
                            problems.append(f"{where}: {r.get('preset')!r} is not a factory preset")
                            continue
                        path = factory[r["preset"]]
                    scored.append(sound(path, scored=True))
                    presets[r["label"]] = str(path)
                if len(scored) == 4 and len(set(scored)) < 4:
                    problems.append(f"{song}/{label}: {kind} holds presets that sound the same")
                found = {_amp_name(pathlib.Path(presets[r["label"]])) for r in rows
                         if r["label"] in presets}
                if not found <= set(AMP_MODULES) or len(found) < 2:
                    problems.append(f"{song}/{label}: {kind} is on {sorted(found)}, "
                                    "not two or more of AC20, PR12 and SW50R")
            manifest["parts"][part["part"]] = presets
            manifest["sha256"][part["part"]] = {k: _sha(v) for k, v in presets.items()}
    expected = sum(len(s["parts"]) for n, s in mapping["songs"].items() if n not in excluded)
    if len(manifest["parts"]) != expected:
        problems.append(f"{len(manifest['parts'])} parts of {expected} have results")
    if problems:
        die("results do not follow the brief:\n  " + "\n  ".join(problems))
    path = out / "render-manifest.json"
    path.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(manifest['parts'])} parts ({sum(map(len, excluded.values()))} excluded); "
          f"manifest at {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("prepare", "redo", "collect"))
    ap.add_argument("song", nargs="?", help="for redo: the song's sandbox name")
    ap.add_argument("--sandbox-dir", type=pathlib.Path, required=True)
    ap.add_argument("--out-dir", type=pathlib.Path, required=True)
    ap.add_argument("--exclude", action="append", default=[], metavar="SONG")
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    args = ap.parse_args()
    if args.command == "redo" and not args.song:
        die("redo needs the song")
    {"prepare": prepare, "redo": redo, "collect": collect}[args.command](args)


if __name__ == "__main__":
    guarded(main)
