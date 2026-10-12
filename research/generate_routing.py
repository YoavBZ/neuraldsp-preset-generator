"""The generate routing and research-edits check (docs/generate-routing-plan.md).

    parts     write docs/generate-routing-parts.json: the development parts, each once,
              with a neutral description and the excerpt, before any agent runs.
    prepare   one neutral run folder per routing input under ~/gtr-session/runs: the
              excerpt of the mix as song-NN.wav (rewritten, no metadata), a prompt,
              an empty data folder. The map from NN to parts stays outside it.
    route     run each prepared folder through a fresh, sandboxed `claude -p` with the
              scrubbed plugin (plan, part 1, blinding); --only NN for a pilot.
    analyze   part 1's readings (leave-band-out truth, regrets, confusion, bootstrap),
              written to docs/generate-routing-results.json.
    edits     part 2: build the dry, tonal and full arms from each agent's recorded
              apply_spec command on the leave-band-out start, render them through the
              part's own measfix DI and score them with the flat judge. --check runs
              only the declared reproduction check first.
    recheck-prepare / recheck-route / recheck-analyze
              the re-check (docs/generate-routing-recheck-plan.md): the old and new
              skill on the same inputs, one prompt, interleaved, then the readings.
    proxy     the cheap router: one short fixed question per run (title, artist, part,
              the excerpt's fingerprint text), web search only, one word back.

Development parts only. Every part is checked against the split it was declared in;
nothing held-out is opened.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DIREC = pathlib.Path.home() / "ndsp-presets" / "learn" / "direc"
SOURCES = (DIREC / "rescore" / "distances.json", DIREC / "songs-check" / "distances.json")
PARTS = ROOT / "docs" / "generate-routing-parts.json"
AMPS = ("pr12", "sw50r", "ac20")
BASELINES = {
    "clean": json.loads((ROOT / "docs/clean-baseline-choice.json").read_text())["presets"],
    "crunch": json.loads((ROOT / "docs/crunch-baseline-choice.json").read_text())["presets"],
    "heavier": {"pr12": "factory:Neural DSP/Vintage Metal",
                "sw50r": "factory:Artists/Royce Whittaker/Wall Of Doom",
                "ac20": "factory:Artists/Charlie Robbins/Dirty Coil Rhythm"},
}


def scored(entry) -> bool:
    """All nine starting presets on both halves of the flat measfix judge."""
    for amp in AMPS:
        for half in ("A", "B"):
            row = entry.get(f"flat|{amp}|measfix_{half}") or {}
            if any(BASELINES[c][amp] not in row for c in BASELINES):
                return False
    return True


def crop_dirs():
    """slug -> (crop folder, label, label source, band, set) for development parts."""
    from learn import set3
    from learn import songs_check as SC
    crops3 = pathlib.Path.home() / "ndsp-presets" / "references" / "validation-crops-set3"

    out = {}
    for p in set3.parts("development"):
        out[p["slug"]] = (crops3 / p["slug"], p["gain_class"], "set-3 catalogue",
                          p["band"], 3)
    for slug, p in SC.parts().items():
        if p["set"] == 12:
            out[slug] = (p["crop"], p["gain_class"], "gain classifier (prep-sets12.json)",
                         p["band"], 12)
    return out


def build_parts():
    entries = {}
    for source in SOURCES:
        for slug, entry in json.loads(source.read_text()).items():
            entries.setdefault(slug, entry)          # set-3 parts in both are identical
    known = crop_dirs()
    rows, dropped = [], []
    for slug in sorted(entries):
        if slug not in known:
            dropped.append((slug, "not a known development part"))
            continue
        if not scored(entries[slug]):
            dropped.append((slug, "not all nine starting presets scored on both halves"))
            continue
        crop, label, label_source, band, set_id = known[slug]
        record = json.loads((pathlib.Path(crop) / "record.json").read_text())
        # Set 3's crops record no split; its declaration (`set3.parts("development")`,
        # which `crop_dirs` reads) is what makes them development.
        if set_id == 12 and record.get("split") != "development":
            raise SystemExit(f"{slug}: split {record.get('split')!r}, refusing")
        rows.append(dict(slug=slug, song=record.get("song"), part=record.get("part"),
                         source=record.get("source"), band=band, set=set_id,
                         label=label, label_source=label_source,
                         start_s=record["excerpt_start_s"],
                         duration_s=record["excerpt_duration_s"],
                         crop=str(crop)))
    # Parts of one song whose excerpts overlap play at the same time: a time range alone
    # cannot say which guitar is meant, so they are unroutable from the input (plan R7).
    by_song = {}
    for row in rows:
        by_song.setdefault((row["source"], row["song"]), []).append(row)
    for group in by_song.values():
        for row in group:
            others = [o for o in group if o is not row
                      and o["start_s"] < row["start_s"] + row["duration_s"]
                      and row["start_s"] < o["start_s"] + o["duration_s"]]
            row["overlaps"] = [o["slug"] for o in others]
            row["routable"] = not any(o["label"] != row["label"] for o in others)
            row["description"] = (
                f"the electric guitar in the excerpt starting at "
                f"{int(row['start_s'] // 60)}:{row['start_s'] % 60:04.1f}, "
                f"{row['duration_s']:.0f} s long")
    return rows, dropped


WORK = pathlib.Path.home() / "gtr-session"
MAP = ROOT / "docs" / "generate-routing-runs.json"      # NN -> parts; never inside WORK
SETTINGS = {
    "sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True,
                "allowUnsandboxedCommands": False},
    "permissions": {"deny": [
        "Read(~/ndsp-presets/**)", "Read(//Users/yoavbz/ndsp-presets/**)",
        "Read(//Users/yoavbz/projects/**)", "Read(~/.claude/projects/**)",
        "Read(//private/tmp/claude-501/**)",
        "WebFetch(domain:github.com)", "WebFetch(domain:raw.githubusercontent.com)",
    ]},
}

PROMPT = """I'd like a Morgan Amps Suite preset for the electric guitar in "{song}" by {artist}.

The file ./{wav} is an excerpt of the song ({start}–{end}); the part I mean is {description}.
Use the generate skill of the neuraldsp-preset-generator plugin.

To save you asking: the pack is Morgan Amps Suite; I don't want the listening page; don't
install the preset or save notes. Run the plugin's Python scripts with
{python} and pass --data-dir {data} where a script takes it.
Write the preset to ./out/ instead of installing it.

When done, write ./result.json with these keys:
  "gain_class": "clean", "crunch" or "heavier" (the starting-preset class you chose),
  "amp": "pr12", "sw50r" or "ac20",
  "template": the starting preset file you used,
  "recipes": the --recipe values you applied, in order,
  "spec": the spec you applied (as JSON),
  "apply_command": the exact apply_spec.py command you ran,
  "reasons": two or three sentences on why this class and amp.
"""


def _clock(seconds: float) -> str:
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def prepare():
    import random

    import soundfile as sf

    if MAP.exists():
        raise SystemExit(f"{MAP} exists; runs are prepared once")
    rows = [r for r in json.loads(PARTS.read_text())["parts"] if r["routable"]]
    groups = {}
    for r in rows:
        groups.setdefault((r["source"], r["song"], r["start_s"]), []).append(r)
    keys = sorted(groups)
    random.Random(20261012).shuffle(keys)        # numbering says nothing about sets
    runs = {}
    for n, key in enumerate(keys, 1):
        nn = f"{n:02d}"
        group = groups[key]
        first = group[0]
        folder = WORK / "runs" / nn
        (folder / "out").mkdir(parents=True, exist_ok=False)
        (folder / "data").mkdir()
        audio, rate = sf.read(str(pathlib.Path(first["crop"]) / "mix.wav"), dtype="float32")
        wav = f"song-{nn}.wav"
        sf.write(str(folder / wav), audio, rate, subtype="FLOAT")
        (folder / "prompt.txt").write_text(PROMPT.format(
            song=first["song"], artist=first["band"], wav=wav,
            start=_clock(first["start_s"]), end=_clock(first["start_s"] + first["duration_s"]),
            description=first["description"], python=WORK / "venv" / "bin" / "python",
            data=folder / "data"))
        runs[nn] = [r["slug"] for r in group]
    (WORK / "settings.json").write_text(json.dumps(SETTINGS, indent=1))
    MAP.write_text(json.dumps({"plan": "docs/generate-routing-plan.md", "runs": runs},
                              indent=1) + "\n")
    print(f"{len(runs)} runs prepared in {WORK / 'runs'}")


def route(only=None, workers=3):
    import subprocess
    from concurrent.futures import ThreadPoolExecutor

    runs = sorted(json.loads(MAP.read_text())["runs"])
    if only:
        runs = [nn for nn in runs if nn in only]

    def one(nn):
        folder = WORK / "runs" / nn
        if (folder / "transcript.jsonl").exists():
            return nn, "skipped (already run)"
        with open(folder / "transcript.jsonl", "w") as log:
            done = subprocess.run(
                ["claude", "-p", (folder / "prompt.txt").read_text(),
                 "--settings", str(WORK / "settings.json"), "--setting-sources", "",
                 "--plugin-dir", str(WORK / "plugin"),
                 "--add-dir", str(WORK / "plugin"), "--add-dir", str(WORK / "venv"),
                 "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Skill",
                 "--disallowedTools", "SendMessage,ListAgents,Task,Agent,Workflow,"
                 "Artifact,ArtifactComments,ArtifactData,CronCreate,RemoteTrigger",
                 "--permission-mode", "acceptEdits",
                 "--output-format", "stream-json", "--verbose"],
                cwd=folder, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
        ok = (folder / "result.json").exists()
        return nn, f"exit {done.returncode}, result {'written' if ok else 'missing'}"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for nn, status in pool.map(one, runs):
            print(nn, status, flush=True)


PROXY_PROMPT = """A guitarist wants a Neural DSP Morgan Amps Suite preset for the electric
guitar in "{song}" by {artist}, the part being {description} ({start}–{end}).
A measurement of that excerpt of the song's mix:

{fingerprint}

You may search the web about the song and artist. Which starting point fits the guitar
tone: clean, crunch, or heavier (high-gain)? Answer with exactly one word on the last
line: clean, crunch or heavier.
"""


def proxy(only=None, workers=3):
    import subprocess
    from concurrent.futures import ThreadPoolExecutor

    parts = {r["slug"]: r for r in json.loads(PARTS.read_text())["parts"]}
    runs = json.loads(MAP.read_text())["runs"]
    todo = sorted(nn for nn in runs if not only or nn in only)

    def one(nn):
        folder = WORK / "runs" / nn
        out = folder / "proxy.txt"
        if out.exists():
            return nn, "skipped"
        first = parts[runs[nn][0]]
        fp = subprocess.run(
            [str(WORK / "venv" / "bin" / "python"), str(WORK / "plugin" / "scripts" / "fingerprint.py"),
             f"song-{nn}.wav", "--regime", "mix", "--text", "--excerpt", "0"],
            cwd=folder, capture_output=True, text=True, timeout=600)
        text = fp.stdout.strip() or fp.stderr.strip()
        (folder / "fingerprint.txt").write_text(text + "\n")
        prompt = PROXY_PROMPT.format(
            song=first["song"], artist=first["band"], description=first["description"],
            start=_clock(first["start_s"]),
            end=_clock(first["start_s"] + first["duration_s"]), fingerprint=text)
        proxy_dir = folder / "proxy"
        proxy_dir.mkdir(exist_ok=True)
        done = subprocess.run(
            ["claude", "-p", prompt, "--settings", str(WORK / "settings.json"),
             "--setting-sources", "", "--tools", "WebSearch",
             "--allowedTools", "WebSearch", "--output-format", "text"],
            cwd=proxy_dir, capture_output=True, text=True, timeout=900)
        out.write_text(done.stdout)
        last = (done.stdout.strip().splitlines() or [""])[-1].strip().strip(".*").lower()
        return nn, last

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for nn, answer in pool.map(one, todo):
            print(nn, answer, flush=True)


CLASSES = ("clean", "crunch", "heavier")
GROUP = {"clean": "clean", "crunch": "not-clean", "heavier": "not-clean"}
LABEL_CLASS = {"clean": "clean", "crunch": "crunch", "high-gain": "heavier"}
NEIGHBOUR = {"clean": "crunch", "crunch": "clean", "heavier": "crunch"}
RESULTS = ROOT / "docs" / "generate-routing-results.json"


def _distances():
    entries = {}
    for source in SOURCES:
        for slug, entry in json.loads(source.read_text()).items():
            entries.setdefault(slug, entry)
    return entries


def _raw(entries, slug, amp, preset, half):
    value = (entries[slug].get(f"flat|{amp}|measfix_{half}") or {}).get(preset)
    return value[0] if value and value[0] else None


def _choose(entries, parts, amp, label, exclude_band):
    """The clean or crunch rule: lowest median over parts of the halves' mean distance
    among factory presets scored on every part, ties by name (the declared rules)."""
    import statistics as st

    use = [p for p in parts if p["label"] == label and p["band"] != exclude_band]
    names = sorted(n for n in entries[use[0]["slug"]][f"flat|{amp}|measfix_A"]
                   if n.startswith("factory:"))
    names = [n for n in names if all(_raw(entries, p["slug"], amp, n, h)
                                     for p in use for h in "AB")]
    return min(names, key=lambda n: st.median(
        (_raw(entries, p["slug"], amp, n, "A") + _raw(entries, p["slug"], amp, n, "B")) / 2
        for p in use))


def _band_boot(values, n=4000, seed=20261012):
    """Band-weighted mean of (band, value) pairs and its 90% band bootstrap."""
    import random
    import statistics as st

    groups = {}
    for band, value in values:
        groups.setdefault(band, []).append(value)
    bands = sorted(groups)
    mean = st.mean(st.mean(groups[b]) for b in bands)
    rng = random.Random(seed)
    draws = sorted(st.mean(st.mean(groups[b]) for b in (rng.choice(bands) for _ in bands))
                   for _ in range(n))
    return {"band_mean": round(mean, 4), "lo": round(draws[int(0.05 * n)], 4),
            "hi": round(draws[int(0.95 * n)], 4),
            "part_mean": round(st.mean(v for _, v in values), 4), "n": len(values),
            "bands": len(bands)}


def analyze():
    import math
    from functools import lru_cache

    entries = _distances()
    doc = json.loads(PARTS.read_text())
    runs = json.loads(MAP.read_text())["runs"]
    parts = [p for p in doc["parts"]
             if all(_raw(entries, p["slug"], a, BASELINES[c][a], h)
                    for a in AMPS for c in BASELINES for h in "AB")]
    unscored = [p["slug"] for p in doc["parts"] if p not in parts]
    choose = lru_cache(None)(lambda amp, label, band: _choose(entries, parts, amp, label, band))

    route_of, proxy_of, audit = {}, {}, {}
    for nn, slugs in runs.items():
        folder = WORK / "runs" / nn
        if not (folder / "result.json").exists():
            raise SystemExit(f"{folder}: no result.json; refusing to overwrite the results")
        try:
            result = json.loads((folder / "result.json").read_text())
            route = {"heavier": "heavier", "high-gain": "heavier"}.get(
                result["gain_class"], result["gain_class"])
        except (ValueError, KeyError):
            route = None
        # A leak is something the agent *asked for*: a tool call naming the project's
        # data, its repository or its GitHub page. Text the plugin prints (its --help
        # names ~/ndsp-presets as a default) and public pages about the songs are not.
        calls = []
        if (folder / "transcript.jsonl").exists():
            for line in (folder / "transcript.jsonl").read_text().splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "assistant":
                    calls += [json.dumps(c.get("input")) for c in event["message"]["content"]
                              if c.get("type") == "tool_use"]
        leaks = sorted({m for m in ("ndsp-presets", "/Users/yoavbz/projects",
                                    "YoavBZ", "neuraldsp-preset-generator/docs",
                                    "validation-")
                        for call in calls if m in call})
        audit[nn] = leaks
        last = ""
        if (folder / "proxy.txt").exists():
            lines = (folder / "proxy.txt").read_text().strip().splitlines()
            last = lines[-1].strip().strip(".*").lower() if lines else ""
        for slug in slugs:
            route_of[slug] = None if leaks else route
            proxy_of[slug] = last if last in CLASSES else None

    rows = []
    for p in parts:
        if not p["routable"]:
            continue
        for amp in AMPS:
            presets = {"clean": choose(amp, "clean", p["band"]),
                       "crunch": choose(amp, "crunch", p["band"]),
                       "heavier": BASELINES["heavier"][amp]}
            shipped = {c: BASELINES[c][amp] for c in BASELINES}
            for truth, chosen in (("primary", presets), ("shipped", shipped)):
                m = {c: sum(math.log(_raw(entries, p["slug"], amp, chosen[c], h))
                            for h in "AB") / 2 for c in CLASSES}
                rows.append(dict(slug=p["slug"], band=p["band"], label=p["label"],
                                 amp=amp, truth=truth, m=m,
                                 best=min(CLASSES, key=m.get),
                                 route=route_of.get(p["slug"]),
                                 proxy=proxy_of.get(p["slug"])))

    def regret(row, cls, two_group=True):
        if cls is None:
            return None
        if two_group and GROUP[cls] == GROUP[row["best"]]:
            return 0.0
        return row["m"][cls] - row["m"][row["best"]]

    routers = {
        "agent": lambda r: r["route"],
        "ceiling (label)": lambda r: LABEL_CLASS[r["label"]],
        "always clean": lambda r: "clean",
        "proxy": lambda r: r["proxy"],
    }
    out = {"plan": "docs/generate-routing-plan.md", "unscored_parts": unscored,
           "excluded_runs_for_leaks": {k: v for k, v in audit.items() if v},
           "readings": {}}
    for truth in ("primary", "shipped"):
        decide = [r for r in rows if r["truth"] == truth and r["label"] in ("clean", "crunch")]
        block = {}
        for name, f in routers.items():
            vals = [(r["band"], regret(r, f(r))) for r in decide if f(r) is not None]
            per_part = {}
            for r in decide:
                g = regret(r, f(r))
                if g is not None:
                    per_part.setdefault((r["band"], r["slug"]), []).append(g)
            averaged = [(b, sum(v) / len(v)) for (b, _), v in per_part.items()]
            three = [(r["band"], regret(r, f(r), two_group=False)) for r in decide
                     if f(r) is not None]
            block[name] = {
                "regret_clean_vs_not": _band_boot(averaged) if averaged else None,
                "rows_costly_over_0.15": sum(v > 0.15 for _, v in vals),
                "rows": len(vals),
                "regret_three_class_report": _band_boot(three) if three else None,
            }
        # paired: agent minus ceiling, per part averaged over amps
        pairs = {}
        for r in decide:
            a, c = regret(r, r["route"]), regret(r, LABEL_CLASS[r["label"]])
            if a is not None:
                pairs.setdefault((r["band"], r["slug"]), []).append(a - c)
        block["agent_minus_ceiling"] = _band_boot(
            [(b, sum(v) / len(v)) for (b, _), v in pairs.items()]) if pairs else None
        best2 = {}
        for r in decide:
            if r["route"]:
                g = min(regret(r, r["route"]), regret(r, NEIGHBOUR[r["route"]]))
                best2.setdefault((r["band"], r["slug"]), []).append(g)
        block["best_of_two_bound"] = _band_boot(
            [(b, sum(v) / len(v)) for (b, _), v in best2.items()]) if best2 else None
        confusion = {}
        for r in (x for x in rows if x["truth"] == truth):
            key = f"{r['label']} | routed {r['route']} | best {r['best']}"
            confusion[key] = confusion.get(key, 0) + 1
        block["confusion_rows"] = dict(sorted(confusion.items()))
        out["readings"][truth] = block
    agree = [(r["route"], r["proxy"]) for r in rows if r["truth"] == "primary"
             and r["amp"] == "pr12" and r["route"] and r["proxy"]]
    out["proxy_agreement"] = {"parts": len(agree),
                              "same_class": sum(a == b for a, b in agree)}
    a = out["readings"]["primary"]
    diff = a["agent_minus_ceiling"]
    if diff is None:
        verdict = "no agent routes"
    elif diff["band_mean"] > 0.05 and diff["lo"] > 0:
        verdict = "routing costs"
    elif diff["hi"] < 0.05:
        verdict = "routing is fine"
    else:
        verdict = "undecided"
    out["decision"] = verdict
    RESULTS.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"decision": verdict, "agent_minus_ceiling": diff,
                      "agent": a["agent"], "ceiling": a["ceiling (label)"],
                      "always clean": a["always clean"], "proxy": a["proxy"],
                      "best_of_two": a["best_of_two_bound"],
                      "proxy_agreement": out["proxy_agreement"],
                      "leaks": out["excluded_runs_for_leaks"],
                      "unscored": unscored}, indent=1))


EDITS = ROOT / "docs" / "generate-edits-results.json"
ARMS = WORK / "arms"
VENV_PY = ROOT / ".venv" / "bin" / "python"
if not VENV_PY.exists():                          # a worktree: the main checkout's venv
    VENV_PY = pathlib.Path.home() / "projects/neuraldsp-preset-generator/.venv/bin/python"
FACTORY = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite")


def _factory_file(preset: str) -> pathlib.Path:
    return FACTORY / (preset.split("factory:", 1)[1] + ".xml")


def _apply(args, cwd):
    import subprocess

    done = subprocess.run([str(VENV_PY), str(ROOT / "scripts" / "apply_spec.py"), *args],
                          cwd=cwd, capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"apply_spec failed in {cwd}: {done.stderr.strip()[-400:]}")


def _replay(command: str, template: pathlib.Path, out: pathlib.Path, cwd: pathlib.Path):
    """The agent's own apply_spec command, with only --template and --out swapped."""
    import shlex

    argv = shlex.split(command)
    i = next(k for k, a in enumerate(argv) if a.endswith("apply_spec.py"))
    args = argv[i + 1:]
    for flag, value in (("--template", str(template)), ("--out", str(out))):
        if flag not in args:
            raise RuntimeError(f"{cwd}: the recorded command has no {flag}")
        args[args.index(flag) + 1] = value
    _apply(args, cwd)


def _context(slug, set_id):
    """(reference, measfix DI, judge lag) exactly as the stored scores used them."""
    import numpy as np

    from learn import phase2_set3 as P
    from learn import set3
    from learn import songs_check as SC

    if set_id == 3:
        part = {p["slug"]: p for p in set3.parts("development")}[slug]
        ref = P.recording(slug, "ref", P.RunConfig())
        di = np.load(SC.EXISTING_S3["measfix"] / slug / "di.npy")
        return ref, di, part["judge_lag_samples"]
    part = SC.parts()[slug]
    ref = SC.CR.mono(part["crop"] / "reference.wav")
    di = np.load(SC.kind_dir("measfix", slug, part) / "di.npy")
    return ref, di, part["judge_lag"]


def _jobs(check: bool):
    """(slug, set, amp, arm, xml) to render; building the arms' XML on the way."""
    from functools import lru_cache

    entries = _distances()
    doc = json.loads(PARTS.read_text())
    scored = [p for p in doc["parts"]
              if all(_raw(entries, p["slug"], a, BASELINES[c][a], h)
                     for a in AMPS for c in BASELINES for h in "AB")]
    by_slug = {p["slug"]: p for p in scored}
    choose = lru_cache(None)(lambda amp, label, band: _choose(entries, scored, amp, label, band))
    jobs = []
    if check:
        picks = ([p for p in scored if p["set"] == 3][:2] + [p for p in scored if p["set"] == 12][:1])
        for p in picks:
            for amp in AMPS:
                folder = ARMS / "check" / p["slug"] / amp
                folder.mkdir(parents=True, exist_ok=True)
                xml = folder / "dry.xml"
                _apply(["--template", str(_factory_file(BASELINES["clean"][amp])),
                        "--recipe", f"dry/{amp}", "--strip-irs", "--out", str(xml)], folder)
                jobs.append((p["slug"], p["set"], amp, "check", xml, BASELINES["clean"][amp]))
        return jobs
    runs = json.loads(MAP.read_text())["runs"]
    for nn, slugs in sorted(runs.items()):
        result = json.loads((WORK / "runs" / nn / "result.json").read_text())
        cls = {"high-gain": "heavier"}.get(result["gain_class"], result["gain_class"])
        amp = result["amp"]
        for slug in slugs:
            p = by_slug.get(slug)
            if p is None or p["label"] not in ("clean", "crunch") or not p["routable"]:
                continue
            start = (BASELINES["heavier"][amp] if cls == "heavier"
                     else choose(amp, cls, p["band"]))
            folder = ARMS / slug
            folder.mkdir(parents=True, exist_ok=True)
            template = _factory_file(start)
            _apply(["--template", str(template), "--recipe", f"dry/{amp}", "--strip-irs",
                    "--out", str(folder / "dry.xml")], folder)
            _replay(result["apply_command"], template, folder / "full.xml", WORK / "runs" / nn)
            _apply(["--template", str(folder / "full.xml"), "--recipe", f"dry/{amp}",
                    "--strip-irs", "--out", str(folder / "tonal.xml")], folder)
            for arm in ("dry", "tonal", "full"):
                jobs.append((slug, p["set"], amp, arm, folder / f"{arm}.xml", start))
    return jobs


def edits(check: bool):
    import math

    import numpy as np

    sys.path.insert(0, str(ROOT / "research"))
    import render_preset_panel as RP
    from analysis.aligned import aligned_distance
    from learn import phase2_set3 as P
    from learn import rescore as R
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    pack = load_pack("morgan")

    class ArmRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edit_list = self.commands[settings["arm"]]
            command = {"edits": edit_list}
            if select is not None:
                command["selectAmp"] = select
            return command

    jobs = _jobs(check)
    entries = _distances()
    r = ArmRenderer("morgan", process_policy="reuse")
    out, last_amp = [], None
    try:
        for slug, set_id, amp, arm, xml, start in jobs:
            ref, di, lag = _context(slug, set_id)
            key = f"{slug}|{amp}|{arm}"
            ArmRenderer.commands[key] = RP.preset_edits(xml, pack, r, amp, False)
            d32 = di.astype(np.float32)
            if amp != last_amp:                   # as the stored panels did per amp
                r.render(d32, {"arm": key})
                last_amp = amp
            y = np.asarray(r.render(d32, {"arm": key}).audio, np.float64)
            if y.ndim > 1:
                y = y.mean(axis=1)
            if not np.any(y):
                raise RuntimeError(f"{key}: silent render")
            halves = {}
            for h, (a, b) in R.HALVES.items():
                x = aligned_distance(ref, y, di, lag=lag, render_latency=P.LATENCY,
                                     start_s=a, end_s=b)
                halves[h] = x.distance
            row = dict(slug=slug, amp=amp, arm=arm, start=start, halves=halves)
            if check:
                stored = {h: _raw(entries, slug, amp, start, h) for h in "AB"}
                row["stored"] = stored
                row["dlog"] = max(abs(math.log(halves[h]) - math.log(stored[h])) for h in "AB")
                print(slug, amp, "Δlog", round(row["dlog"], 5), flush=True)
            else:
                print(key, {h: round(v, 4) for h, v in halves.items()}, flush=True)
            out.append(row)
    finally:
        r.close()
    if check:
        worst = max(row["dlog"] for row in out)
        verdict = "passes" if worst < 0.005 else "fails"
        (ARMS / "check.json").write_text(json.dumps({"worst_dlog": worst, "verdict": verdict,
                                                     "rows": out}, indent=1))
        print("reproduction check", verdict, "worst Δlog", round(worst, 5))
        return
    EDITS.write_text(json.dumps({"plan": "docs/generate-routing-plan.md", "rows": out},
                                indent=1) + "\n")


def edits_analyze():
    import math
    from functools import lru_cache

    data = json.loads(EDITS.read_text())
    entries = _distances()
    doc = json.loads(PARTS.read_text())
    scored = [p for p in doc["parts"]
              if all(_raw(entries, p["slug"], a, BASELINES[c][a], h)
                     for a in AMPS for c in BASELINES for h in "AB")]
    by_slug = {p["slug"]: p for p in scored}
    choose = lru_cache(None)(lambda amp, label, band: _choose(entries, scored, amp, label, band))
    runs = json.loads(MAP.read_text())["runs"]
    route = {}
    for nn, slugs in runs.items():
        result = json.loads((WORK / "runs" / nn / "result.json").read_text())
        for slug in slugs:
            route[slug] = {"high-gain": "heavier"}.get(result["gain_class"], result["gain_class"])

    def logm(row):
        return sum(math.log(v) for v in row["halves"].values()) / 2

    arms = {}
    for row in data["rows"]:
        arms.setdefault(row["slug"], {})[row["arm"]] = row
    tonal, full, same_start, right = [], [], [], []
    for slug, a in sorted(arms.items()):
        p = by_slug[slug]
        t = logm(a["tonal"]) - logm(a["dry"])
        f = logm(a["full"]) - logm(a["tonal"])
        tonal.append((p["band"], t))
        full.append((p["band"], f))
        amp, start = a["dry"]["amp"], a["dry"]["start"]
        if start == BASELINES.get(route[slug], {}).get(amp):
            same_start.append((p["band"], t))
        m = {c: sum(math.log(_raw(entries, slug, amp,
                                  BASELINES["heavier"][amp] if c == "heavier"
                                  else choose(amp, c, p["band"]), h)) for h in "AB") / 2
             for c in CLASSES}
        if GROUP[min(CLASSES, key=m.get)] == GROUP[route[slug]]:
            right.append((p["band"], t))
    tonal_r = _band_boot(tonal)
    verdict = ("edits hurt" if tonal_r["lo"] > 0 else
               "edits help" if tonal_r["hi"] < 0 else "undecided")
    out = {"plan": "docs/generate-routing-plan.md", "decision": verdict,
           "tonal_vs_dry": tonal_r,
           "tonal_wins_losses": [sum(v < 0 for _, v in tonal), sum(v > 0 for _, v in tonal)],
           "full_vs_tonal_report": _band_boot(full),
           "sensitivity_same_start": _band_boot(same_start) if same_start else None,
           "secondary_correctly_routed": _band_boot(right) if right else None}
    summary = EDITS.with_name("generate-edits-summary.json")
    summary.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


RECHECK_MAP = ROOT / "docs" / "generate-routing-recheck-runs.json"
RECHECK_RESULTS = ROOT / "docs" / "generate-routing-recheck-results.json"
NEW_COMMIT = "1d2ae4c"
RECHECK_MODEL = "claude-opus-5-5"
NON_ANSWER = "I can't say; decide yourself."
# Neutral names: an agent sees its plugin's path, which must not say which arm it is.
# plugin-m is a byte copy of run 1's plugin (0.7.105); plugin-k is main at NEW_COMMIT.
ARM_PLUGIN = {"old": WORK / "plugin-m", "new": WORK / "plugin-k"}
ARM_VERSION = {"old": "0.7.105", "new": None}         # new: read from its copy


def _recheck_prompt(old_prompt: str) -> str:
    a = """install the preset or save notes."""
    b = """Write the preset to ./out/ instead of installing it."""
    if a not in old_prompt or b not in old_prompt:
        raise SystemExit("run 1's prompt changed; refusing")
    text = old_prompt.replace(a, "install anything or save notes.")
    text = text.replace(b, "Write whatever you would install to ./out/ instead of installing it.")
    key = """  "reasons": two or three sentences on why this class and amp.\n"""
    if key not in text:
        raise SystemExit("run 1's result keys changed; refusing")
    return text.replace(key, key + """  "outputs": each file you wrote to ./out/ and the starting preset it was built from.\n""")


def recheck_prepare():
    import random
    import shutil
    import subprocess

    if RECHECK_MAP.exists():
        raise SystemExit(f"{RECHECK_MAP} exists; the re-check is prepared once")
    new = WORK / "plugin-new"                 # renamed to plugin-k after preparing
    if new.exists() or ARM_PLUGIN["new"].exists():
        raise SystemExit(f"{new} exists")
    new.mkdir(parents=True)
    archive = subprocess.run(
        ["git", "archive", NEW_COMMIT, "skills", "scripts", "packs", "reference", "analysis",
         "format", "match", "samples", ".claude-plugin", "pyproject.toml", "LICENSE",
         "NOTICE.md"], cwd=ROOT, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(new)], input=archive.stdout, check=True)
    runs = json.loads(MAP.read_text())["runs"]
    labels = {r["slug"]: r["label"] for r in json.loads(PARTS.read_text())["parts"]}
    jobs = []
    for nn, slugs in sorted(runs.items()):
        has_cc = any(labels[s] in ("clean", "crunch") for s in slugs)
        for arm in ("old", "new"):
            if arm == "old" and not has_cc:
                continue
            folder = WORK / f"runs-{arm}" / nn
            (folder / "out").mkdir(parents=True)
            (folder / "data").mkdir()
            src = WORK / "runs" / nn
            shutil.copy2(src / f"song-{nn}.wav", folder / f"song-{nn}.wav")
            prompt = _recheck_prompt((src / "prompt.txt").read_text())
            prompt = prompt.replace(str(src / "data"), str(folder / "data"))
            (folder / "prompt.txt").write_text(prompt)
            jobs.append([arm, nn])
    random.Random(20261013).shuffle(jobs)
    version = json.loads((new / ".claude-plugin" / "plugin.json").read_text())["version"]
    RECHECK_MAP.write_text(json.dumps({"plan": "docs/generate-routing-recheck-plan.md",
                                       "new_commit": NEW_COMMIT, "new_version": version,
                                       "model": RECHECK_MODEL, "order": jobs}, indent=1) + "\n")
    prompts = {(WORK / f"runs-{a}" / n / "prompt.txt").read_text() for a, n in jobs if n == "01"}
    print(f"{len(jobs)} runs prepared; new plugin {version}; prompts identical across arms: "
          f"{len(prompts) == 1}")


def _claude(folder, plugin, prompt, log, resume=None):
    import subprocess

    argv = ["claude", "-p", prompt, "--model", RECHECK_MODEL,
            "--settings", str(WORK / "settings.json"), "--setting-sources", "",
            "--plugin-dir", str(plugin), "--add-dir", str(plugin),
            "--add-dir", str(WORK / "venv"),
            "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Skill",
            "--disallowedTools", "SendMessage,ListAgents,Task,Agent,Workflow,"
            "Artifact,ArtifactComments,ArtifactData,CronCreate,RemoteTrigger",
            "--permission-mode", "acceptEdits", "--output-format", "stream-json", "--verbose"]
    if resume:
        argv += ["--resume", resume]
    return subprocess.run(argv, cwd=folder, stdout=log, stderr=subprocess.STDOUT, timeout=3600)


def _session_id(transcript: pathlib.Path):
    for line in transcript.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            return event.get("session_id"), event.get("plugins"), event.get("model")
    return None, None, None


def recheck_route(workers=3):
    from concurrent.futures import ThreadPoolExecutor

    doc = json.loads(RECHECK_MAP.read_text())

    def one(job):
        arm, nn, tag = job                    # neutral folder names: the arm is not in any path
        folder = WORK / "runs2" / tag
        transcript = folder / "transcript.jsonl"
        if transcript.exists():
            return arm, nn, "skipped"
        with open(transcript, "w") as log:
            _claude(folder, ARM_PLUGIN[arm], (folder / "prompt.txt").read_text(), log)
        asked = False
        if not (folder / "result.json").exists():
            session, _, _ = _session_id(transcript)
            if session:
                asked = True
                with open(transcript, "a") as log:
                    _claude(folder, ARM_PLUGIN[arm], NON_ANSWER, log, resume=session)
        (folder / "asked.txt").write_text("yes\n" if asked else "no\n")
        return arm, nn + "/" + tag, ("result" if (folder / "result.json").exists() else "NO RESULT") + (
            ", resumed" if asked else "")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for arm, nn, status in pool.map(one, [tuple(j) for j in doc["order"]]):
            print(arm, nn, status, flush=True)


def _preset_values(path):
    from format.parser import parse
    from format.structured import build

    preset = build(parse(pathlib.Path(path).read_bytes()))
    return {(q.module_path, q.key): str(q.value) for q in preset.parameters}


def _dry_baselines(folder: pathlib.Path):
    """(class, amp) -> values of each starting preset made dry, as step 4 writes it."""
    folder.mkdir(parents=True, exist_ok=True)
    out = {}
    for cls, by_amp in BASELINES.items():
        for amp, preset in by_amp.items():
            xml = folder / f"{cls}-{amp}.xml"
            if not xml.exists():
                _apply(["--template", str(_factory_file(preset)), "--recipe", f"dry/{amp}",
                        "--strip-irs", "--out", str(xml)], folder)
            out[(cls, amp)] = _preset_values(xml)
    return out


def _starts_written(out_dir: pathlib.Path, dry):
    """The starting-point classes among the files the agent wrote: a file counts as a
    class's start when at least 95% of the dry baseline's values match it."""
    found = set()
    for xml in sorted(out_dir.glob("*.xml")):
        try:
            values = _preset_values(xml)
        except Exception:
            continue
        for (cls, _amp), base in dry.items():
            same = sum(values.get(k) == v for k, v in base.items())
            if base and same / len(base) >= 0.95:
                found.add(cls)
    return found


def recheck_analyze():
    import math
    from functools import lru_cache

    doc = json.loads(RECHECK_MAP.read_text())
    runs = json.loads(MAP.read_text())["runs"]
    entries = _distances()
    parts_doc = json.loads(PARTS.read_text())
    scored = [p for p in parts_doc["parts"]
              if all(_raw(entries, p["slug"], a, BASELINES[c][a], h)
                     for a in AMPS for c in BASELINES for h in "AB")]
    choose = lru_cache(None)(lambda amp, label, band: _choose(entries, scored, amp, label, band))
    dry = _dry_baselines(WORK / "dry-baselines")
    norm = {"high-gain": "heavier"}

    arms = {"old": {}, "new": {}}
    status = {}
    for arm, nn, tag in doc["order"]:
        folder = WORK / "runs2" / tag
        transcript = folder / "transcript.jsonl"
        text = transcript.read_text() if transcript.exists() else ""
        _, plugins, model = _session_id(transcript) if transcript.exists() else (None, None, None)
        version = next((p.get("version") for p in plugins or []
                        if p["name"] == "neuraldsp-preset-generator"), None)
        calls = []
        for line in text.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "assistant":
                calls += [json.dumps(c.get("input")) for c in event["message"]["content"]
                          if c.get("type") == "tool_use"]
        leaks = sorted({m for m in ("ndsp-presets", "/Users/yoavbz/projects", "YoavBZ",
                                    "neuraldsp-preset-generator/docs", "validation-",
                                    "generate-routing")
                        for call in calls if m in call})
        want = "0.7.105" if arm == "old" else doc["new_version"]
        excluded = (leaks or version != want or model != RECHECK_MODEL)
        result = None
        if (folder / "result.json").exists():
            try:
                result = json.loads((folder / "result.json").read_text())
            except ValueError:
                result = None
        route = norm.get(result.get("gain_class"), result.get("gain_class")) if result else None
        written = _starts_written(folder / "out", dry)
        asked = (folder / "asked.txt").read_text().strip() == "yes" if (
            folder / "asked.txt").exists() else False
        status[f"{arm}/{nn}"] = {"route": route, "starts_written": sorted(written),
                                 "asked": asked, "excluded": bool(excluded),
                                 "why_excluded": leaks or ([f"version {version}"] if version != want else [])
                                 + ([f"model {model}"] if model != RECHECK_MODEL else [])}
        for slug in runs[nn]:
            arms[arm][slug] = None if excluded or route not in CLASSES else (
                route, written | {route})
    run1 = {}
    for nn, slugs in runs.items():
        r = json.loads((WORK / "runs" / nn / "result.json").read_text())
        for slug in slugs:
            run1[slug] = norm.get(r["gain_class"], r["gain_class"])

    def regret(m, best, cls):
        if GROUP[cls] == GROUP[best]:
            return 0.0
        return m[cls] - m[best]

    per = {}
    guards = {"old": {}, "new": {}}
    for p in scored:
        if not p["routable"]:
            continue
        rows = []
        for amp in AMPS:
            presets = {"clean": choose(amp, "clean", p["band"]),
                       "crunch": choose(amp, "crunch", p["band"]),
                       "heavier": BASELINES["heavier"][amp]}
            m = {c: sum(math.log(_raw(entries, p["slug"], amp, presets[c], h))
                        for h in "AB") / 2 for c in CLASSES}
            rows.append((m, min(CLASSES, key=m.get)))
        def avg(cls_or_set):
            if cls_or_set is None:
                return None
            if isinstance(cls_or_set, str):
                return sum(regret(m, b, cls_or_set) for m, b in rows) / len(rows)
            return sum(min(regret(m, b, c) for c in cls_or_set) for m, b in rows) / len(rows)
        entry = {"band": p["band"], "label": p["label"]}
        for arm in ("old", "new"):
            got = arms[arm].get(p["slug"])
            entry[arm] = avg(got[0]) if got else None
            entry[f"{arm}_two"] = avg(got[1]) if got else None
            if got:
                key = f"{p['label']} -> {got[0]}"
                guards[arm][key] = guards[arm].get(key, 0) + 1
        entry["run1"] = avg(run1.get(p["slug"]))
        entry["label_route"] = avg(LABEL_CLASS[p["label"]])
        per[p["slug"]] = entry

    decide = {s: e for s, e in per.items() if e["label"] in ("clean", "crunch")}

    def boot(key):
        vals = [(e["band"], e[key]) for e in decide.values() if e[key] is not None]
        return _band_boot(vals) if vals else None

    def paired(a, b):
        vals = [(e["band"], e[a] - e[b]) for e in decide.values()
                if e[a] is not None and e[b] is not None]
        return _band_boot(vals) if vals else None

    diff = paired("new", "old")
    if diff is None:
        verdict = "no routes"
    elif diff["hi"] < 0:
        verdict = "the rule helps"
    elif diff["lo"] > 0:
        verdict = "the rule hurts"
    else:
        verdict = "undecided"
    asked_runs = [k for k, v in status.items() if v["asked"]]
    # Report only: the product with the question, if asked runs had been told the label.
    answered = {s: dict(e) for s, e in decide.items()}
    asked_slugs = {slug for k in asked_runs if k.startswith("new/")
                   for slug in runs[k.split("/")[1]]}
    for s, e in answered.items():
        if s in asked_slugs:
            e["new"] = e["label_route"]
    out = {"plan": "docs/generate-routing-recheck-plan.md", "decision": verdict,
           "new_minus_old": diff, "old_minus_run1_noise": paired("old", "run1"),
           "regret": {k: boot(k) for k in ("new", "old", "run1", "label_route",
                                           "new_two", "old_two")},
           "if_the_question_were_answered_new": _band_boot(
               [(e["band"], e["new"]) for e in answered.values() if e["new"] is not None]),
           "asked_runs": asked_runs,
           "second_start_written": {arm: sum(len(v["starts_written"]) > 1
                                             or (v["route"] and v["starts_written"]
                                                 and v["route"] not in v["starts_written"])
                                             for k, v in status.items() if k.startswith(arm))
                                    for arm in ("old", "new")},
           "guards_routes_by_label_parts": guards,
           "excluded_runs": {k: v["why_excluded"] for k, v in status.items() if v["excluded"]},
           "failed_routes": [k for k, v in status.items() if v["route"] not in CLASSES],
           "runs": status, "parts": per}
    RECHECK_RESULTS.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("decision", "new_minus_old", "old_minus_run1_noise",
                                          "regret", "if_the_question_were_answered_new",
                                          "asked_runs", "second_start_written",
                                          "guards_routes_by_label_parts", "excluded_runs",
                                          "failed_routes")}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=["parts", "prepare", "route", "proxy", "analyze", "edits", "edits-analyze",
                                       "recheck-prepare", "recheck-route",
                                       "recheck-analyze"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    if args.step == "prepare":
        return prepare()
    if args.step == "route":
        return route(args.only, args.workers)
    if args.step == "recheck-prepare":
        return recheck_prepare()
    if args.step == "recheck-analyze":
        return recheck_analyze()
    if args.step == "recheck-route":
        return recheck_route(args.workers)
    if args.step == "edits-analyze":
        return edits_analyze()
    if args.step == "edits":
        return edits(args.check)
    if args.step == "analyze":
        return analyze()
    if args.step == "proxy":
        return proxy(args.only, args.workers)
    if args.step == "parts":
        if PARTS.exists():
            raise SystemExit(f"{PARTS} exists; the part list is written once")
        rows, dropped = build_parts()
        PARTS.write_text(json.dumps({"plan": "docs/generate-routing-plan.md",
                                     "parts": rows, "dropped": dropped}, indent=1) + "\n")
        classes = {}
        for row in rows:
            classes[row["label"]] = classes.get(row["label"], 0) + 1
        print(f"{len(rows)} parts in {len({(r['source'], r['song']) for r in rows})} songs; "
              f"{classes}; unroutable {sum(not r['routable'] for r in rows)}; "
              f"dropped {len(dropped)}")


if __name__ == "__main__":
    main()
