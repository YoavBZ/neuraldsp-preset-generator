#!/usr/bin/env python3
"""Score the match-pipeline benchmark's `library` arm against its starting preset.

    python scripts/analyse_shipped_library.py render-calc --run runs/lib-pr12-shipped \\
      --no-di-run runs/start-pr12-shipped --template samples/Example_Clean_PR12.xml
    python scripts/analyse_shipped_library.py score --run runs/lib-pr12-shipped \\
      --no-di-run runs/start-pr12-shipped --json lib-pr12.json

The analysis was fixed before the runs' final results were read (recorded in
`docs/tone-matching-plan.md`, "The real-guitar probe from the shipped presets").

`render-calc` renders, for every part of a `--arm library` run, the shipped preset
with a match's calculated settings applied and no search (`search.starting_settings`
of its summary.json), through the part's DI in a fresh process exactly as the
run's own renders (`render_listening_guitar.py --preroll-s 0`): `calc-library` from
the run's library match and `calc-noise` from the no-DI match of `--no-di-run`.

`score` compares, per part and level left out, under two readings:
  stored     `v3_no_level` as the benchmark scores it
  corrected  the audit's fixes, applied to both sides alike: `band_shape` over
             the bands within 30 dB of the reference's peak band only; each pair
             over the dimensions measured on both sides; and with `--cut-s`
             (1.0 for Tone King, whose fresh processes start muted) that much
             removed from the start of reference and render
It reports how many parts the first arm ends closer on, the median change, and
an exact two-sided sign-flip test over the bands (catalog `group`) of each
band's median log ratio. An answer with no measurable loudness counts as a loss.
The decision rule: the library search is adopted if it is closer than the
template on a majority of parts under both readings and the corrected band p is
under 0.05; "not shown" if only the majority holds; the template otherwise.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import pathlib
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

CATALOG = PLUGIN_ROOT / "docs" / "validation-datasets.json"
PAIRS = (("library", "template"), ("calc-library", "template"),
         ("library", "calc-library"), ("calc-noise", "template"),
         ("calc-library", "calc-noise"), ("library", "no_di"))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("render-calc", "score"):
        p = sub.add_parser(name)
        p.add_argument("--run", type=pathlib.Path, required=True,
                       help="the --arm library run's --out-dir")
        p.add_argument("--no-di-run", type=pathlib.Path, required=True,
                       help="the no-DI (noise) run of the same template and seed")
        p.add_argument("--crops-dir", type=pathlib.Path,
                       default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    render = sub.choices["render-calc"]
    render.add_argument("--template", required=True)
    render.add_argument("--pack", default="morgan")
    render.add_argument("--workers", type=int, default=2)
    score = sub.choices["score"]
    score.add_argument("--cut-s", type=float, default=0.0)
    score.add_argument("--json", type=pathlib.Path)
    return ap


def _parts(run: pathlib.Path):
    return sorted(d for d in run.iterdir() if (d / "result.json").exists())


def spec_of(settings: dict) -> list:
    """`search.starting_settings` ("module/key" -> value) as apply_spec's parameters."""
    return [{"module": path.rsplit("/", 1)[0], "key": path.rsplit("/", 1)[1],
             "value": value} for path, value in settings.items()]


def render_calc(args) -> None:
    def one(part_dir, name, summary):
        wav = part_dir / f"{name}.wav"
        if wav.exists():
            return "exists"
        if not summary.exists():
            return f"no summary {summary}"
        settings = json.loads(summary.read_text())["search"].get("starting_settings")
        if not settings:
            return "no starting_settings"
        spec, xml = part_dir / f"{name}.json", part_dir / f"{name}.xml"
        spec.write_text(json.dumps({"name": name, "parameters": spec_of(settings)}, indent=1))
        di = args.crops_dir.expanduser() / part_dir.name / "di.wav"
        for argv, log in (
                (["scripts/apply_spec.py", "--template", args.template, "--spec", str(spec),
                  "--out", str(xml)], part_dir / f"{name}-preset.log"),
                (["scripts/render_listening_guitar.py", "--pack", args.pack, "--di", str(di),
                  "--preset", str(xml), "--preroll-s", "0", "--out", str(wav)],
                 part_dir / f"{name}-render.log")):
            with log.open("w") as handle:
                if subprocess.run([sys.executable, *argv], cwd=PLUGIN_ROOT, stdout=handle,
                                  stderr=subprocess.STDOUT).returncode:
                    return f"failed: see {log}"
        return "ok"

    jobs = []
    for part_dir in _parts(args.run):
        jobs.append((part_dir, "calc-library", part_dir / "library" / "summary.json"))
        jobs.append((part_dir, "calc-noise",
                     args.no_di_run / part_dir.name / "no_di" / "summary.json"))
    with ThreadPoolExecutor(args.workers) as pool:
        for (part_dir, name, _), outcome in zip(jobs, pool.map(lambda j: one(*j), jobs)):
            print(f"{part_dir.name} {name} {outcome}", flush=True)


def _loader(cut_s: float):
    from analysis import io
    from analysis.fingerprint import fingerprint

    def load(path, regime):
        audio = io.load(path)
        if cut_s:
            audio = audio.replace(audio.samples[int(cut_s * audio.sample_rate):])
        return fingerprint(audio, regime=regime, excerpt_s=None)

    return load


def _within_30_db(original):
    """`compare._timbre` with the reference's bands more than 30 dB under its peak
    band left out of `band_shape`."""
    def timbre(target, candidate, scales):
        centres = target.spectrum.get("band_centres_hz") or []
        levels = target.spectrum.get("band_db") or []
        keep = [i for i, level in enumerate(levels) if level >= max(levels) - 30]
        proxy = type("Restricted", (), {})()
        proxy.__dict__.update(target.__dict__)
        proxy.spectrum = {**target.spectrum,
                          "band_centres_hz": [centres[i] for i in keep],
                          "band_db": [levels[i] for i in keep]}
        return original(proxy, candidate, scales)

    return timbre


def corrected_pair(reference, first, second):
    """No-level distances of two renders, with the audit's corrections."""
    from analysis import compare as C
    from analysis.compare import Objectives, compare, scalar

    original = C._timbre
    C._timbre = _within_30_db(original)
    try:
        a, b = (compare(reference, x, profile="unpaired-v3") for x in (first, second))
    finally:
        C._timbre = original
    keys = (set(a.values) & set(b.values)) - {"level"}
    return tuple(scalar(Objectives(values={k: o.values[k] for k in keys},
                                   profile="unpaired-v3")) for o in (a, b))


def stored_distance(reference, render):
    from analysis.compare import Objectives, compare, scalar

    objectives = compare(reference, render, profile="unpaired-v3")
    return scalar(Objectives(values={k: v for k, v in objectives.values.items()
                                     if k != "level"}, profile="unpaired-v3"))


def sign_flip(by_band: dict) -> float:
    """Exact two-sided sign-flip p over the bands' median log ratios."""
    medians = [statistics.median(values) for values in by_band.values()]
    observed = abs(sum(medians))
    hits = sum(abs(sum(s * m for s, m in zip(signs, medians))) >= observed - 1e-12
               for signs in itertools.product((1, -1), repeat=len(medians)))
    return hits / 2 ** len(medians)


def summarise(rows, first, second) -> dict:
    """`rows`: per part, {"band", "lost" (first arm unmeasurable), "stored": (a, b),
    "corrected": (a, b)}."""
    out = {"first": first, "second": second}
    for reading in ("stored", "corrected"):
        both = [r for r in rows if None not in r[reading]]
        by_band = {}
        for r in both:
            a, b = r[reading]
            ratio = math.log(a / b)
            by_band.setdefault(r["band"], []).append(abs(ratio) + 1e-9 if r["lost"] else ratio)
        out[reading] = {
            "first_closer": sum(r[reading][0] < r[reading][1] and not r["lost"] for r in both),
            "of": len(both),
            "median_change": (round(statistics.median(a / b - 1 for a, b in
                                                      (r[reading] for r in both)), 3)
                              if both else None),
            "bands_first_closer": sum(statistics.median(v) < 0 for v in by_band.values()),
            "bands": len(by_band),
            "band_sign_flip_p": round(sign_flip(by_band), 4) if by_band else None}
    return out


def decide(main: dict) -> str:
    majority = all(main[r]["first_closer"] > main[r]["of"] / 2
                   for r in ("stored", "corrected"))
    if majority and main["corrected"]["band_sign_flip_p"] < 0.05:
        return "adopt the library search"
    if majority:
        return "not shown: the template by default, the library search as an option"
    return "the template"


def score(args) -> dict:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    band = {(s["source"], s["song"]): s.get("group") or f"{s['source']}/{s['song']}"
            for s in catalog["sessions"]}
    load_cut, load_whole = _loader(args.cut_s), _loader(0.0)
    crops = args.crops_dir.expanduser()
    per_pair = {pair: [] for pair in PAIRS}
    stored_rows = []
    for part_dir in _parts(args.run):
        result = json.loads((part_dir / "result.json").read_text())
        source, song = result["part"].split("/")[:2]
        reference = crops / part_dir.name / "reference.wav"
        renders = {"template": part_dir / "template.wav", "library": part_dir / "library.wav",
                   "calc-library": part_dir / "calc-library.wav",
                   "calc-noise": part_dir / "calc-noise.wav",
                   "no_di": args.no_di_run / part_dir.name / "no_di.wav"}
        renders = {arm: path for arm, path in renders.items() if path.exists()}
        ref_cut, ref_whole = load_cut(reference, "isolated_stem"), load_whole(reference, "isolated_stem")
        cut = {arm: load_cut(path, "probe") for arm, path in renders.items()}
        stored = {arm: stored_distance(ref_whole, load_whole(path, "probe"))
                  for arm, path in renders.items()}
        lost = {"library": (result.get("library") or {}).get("lufs", 0) is None}
        for first, second in PAIRS:
            pair = (corrected_pair(ref_cut, cut[first], cut[second])
                    if first in cut and second in cut else (None, None))
            per_pair[(first, second)].append({
                "band": band[(source, song)], "lost": lost.get(first, False),
                "stored": (stored.get(first), stored.get(second)), "corrected": pair})
        stored_rows.append({"part": result["part"], "band": band[(source, song)],
                            "stored_v3_no_level": stored})
    pairs = [summarise(per_pair[pair], *pair) for pair in PAIRS]
    return {"run": str(args.run), "no_di_run": str(args.no_di_run), "cut_s": args.cut_s,
            "parts": len(stored_rows),
            "missing": {arm: [r["part"] for r in stored_rows
                              if arm not in r["stored_v3_no_level"]]
                        for arm in ("calc-library", "calc-noise", "no_di")},
            "pairs": pairs, "decision": decide(pairs[0]), "rows": stored_rows}


def main() -> None:
    args = build_parser().parse_args()
    for name in ("run", "no_di_run"):
        path = getattr(args, name).expanduser().absolute()
        if not path.is_dir():
            die(f"--{name.replace('_', '-')} {path} is not a directory")
        setattr(args, name, path)
    if args.command == "render-calc":
        render_calc(args)
        return
    from analysis import require

    require("scoring the library arm")
    report = score(args)
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=1))
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    guarded(main)
