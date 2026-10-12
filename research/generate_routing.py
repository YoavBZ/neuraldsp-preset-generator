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
        try:
            result = json.loads((folder / "result.json").read_text())
            route = {"heavier": "heavier", "high-gain": "heavier"}.get(
                result["gain_class"], result["gain_class"])
        except (OSError, ValueError, KeyError):
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=["parts", "prepare", "route", "proxy", "analyze"])
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    if args.step == "prepare":
        return prepare()
    if args.step == "route":
        return route(args.only, args.workers)
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
