#!/usr/bin/env python3
"""Run match_preset.py as shipped on amp recordings, with and without a DI.

    python scripts/benchmark_match_pipeline.py --set 2 --parallel 3 \\
      --json match-pipeline-set2-sw50r.json

`benchmark_recordings.py` measures the search through different signals with
everything else held; this measures the whole tool a player runs. For every
usable development part of `docs/validation-datasets.md` (with `--set`, of those
validation sets) it cuts the part's declared crops with `build_validation_crops.py`
(once, then verified by hash, as the recordings benchmark does), and then:

  template  renders the template through the part's own DI
  no_di     match_preset.py against the amp track with no DI: the noise-probe
            search, the guitar check and the level trim, as shipped
  di        match_preset.py with the part's own DI (`paired_di`), a same-take
            reamp: the best case a player's DI can reach

`--process-policy fresh` runs every search candidate in its own plugin process,
as AC20 needs; a finished arm searched under another policy is refused, not reused.
Each answer becomes a preset (apply_spec.py, or the template when the match says
nothing beat it) and is rendered through the part's DI with
render_listening_guitar.py, a fresh plugin process. Each render is scored against
the amp track: its loudness gap in LU, and the unpaired-v3 and -v2 distances with
and without the level term (the reference fingerprinted as `isolated_stem`, the
render as `probe`, as listening scoring does). Every part's `no_di` arm runs before
any `di` arm. Results go to `--out-dir`, one directory and `result.json` per part,
kept between runs: a finished arm is not run again. Held-out parts are refused.
The output directory must be under this checkout's `runs/`, which
render_listening_guitar.py requires. Run it from a clean checkout of the commit
it measures.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

SCHEMA = "match-pipeline-benchmark-1"
MEASUREMENT_CAVEAT = (
    "each search ran in one reused plugin process, which the Swift backend reports "
    "as reproducible=False (identical states can render slightly differently); the "
    "template and every answer were then rendered through the DI in a fresh process "
    "each. `measured_commit` on each arm is the checkout that ran it; `source_commit` "
    "is the one that wrote this summary")
TONE_KING_CAVEAT = (
    "; Tone King's renders are not sample-exact even in a fresh process (its "
    "manifest: fresh_process_reproducible false), so its scoring renders carry "
    "that noise too")
FRESH_CAVEAT = (
    "each search rendered every candidate in a fresh plugin process, as were the "
    "template and every answer rendered through the DI. `measured_commit` on each "
    "arm is the checkout that ran it; `source_commit` is the one that wrote this "
    "summary")
ARMS = ("no_di", "di")
NOTHING_BEAT = "nothing beat the preset you started from"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", default="samples/SW50R_Atlas_Topology.xml")
    ap.add_argument("--pack", default="morgan")
    ap.add_argument("--amp", default="sw50r")
    ap.add_argument("--set", type=int, choices=(1, 2), action="append", dest="sets",
                    help="repeatable; only parts of these validation sets (default: all)")
    ap.add_argument("--part", action="append", metavar="SOURCE/SONG/PART",
                    help="only these development parts (default: every usable one)")
    ap.add_argument("--arm", action="append", choices=ARMS,
                    help="repeatable (default: both); the template is always rendered")
    ap.add_argument("--budget", default="300")
    ap.add_argument("--seed", default="0")
    ap.add_argument("--process-policy", choices=("reuse", "fresh"), default="reuse",
                    help="for the searches; fresh for AC20 or a template with the "
                         "tremolo on, and for the rack reverb when a DI is played "
                         "(skills/match/SKILL.md)")
    ap.add_argument("--parallel", type=int, default=1, help="parts at once")
    ap.add_argument("--out-dir", type=pathlib.Path,
                    help="under this checkout's runs/ (default: runs/match-pipeline-PACK-AMP)")
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path, help="write the summary here")
    return ap


def slug(part) -> str:
    return "-".join(piece.replace("/", "_").replace(" ", "_") for piece in part)


def score(reference_path, wav) -> dict:
    """Loudness gap and audio distances of one render against the amp track."""
    from analysis import io
    from analysis.compare import Objectives, compare, scalar
    from analysis.fingerprint import fingerprint

    reference, audio = io.load(reference_path), io.load(wav)
    ref_lufs, lufs = io.loudness_lufs(reference), io.loudness_lufs(audio)
    target = fingerprint(reference, regime="isolated_stem", excerpt_s=None)
    got = fingerprint(audio, regime="probe", excerpt_s=None)
    row = {"lufs": None if lufs is None else round(lufs, 2),
           "vs_reference_lu": (None if lufs is None or ref_lufs is None
                               else round(lufs - ref_lufs, 2))}
    for profile in ("unpaired-v3", "unpaired-v2"):
        objectives = compare(target, got, profile=profile)
        without = Objectives(values={k: v for k, v in objectives.values.items()
                                     if k != "level"}, profile=profile)
        tag = profile.split("-")[1]
        row[tag] = scalar(objectives)
        row[f"{tag}_no_level"] = scalar(without)
    return row


class Runner:
    def __init__(self, args, out_dir: pathlib.Path, commit: str | None = None):
        self.args, self.out_dir, self.commit = args, out_dir, commit
        self.python = sys.executable
        self.lock = threading.Lock()

    def log(self, message: str) -> None:
        with self.lock:
            print(f"{time.strftime('%F %T')} {message}", flush=True)

    def run(self, argv, log_path) -> None:
        with log_path.open("w") as handle:
            done = subprocess.run(argv, cwd=PLUGIN_ROOT, stdout=handle,
                                  stderr=subprocess.STDOUT)
        if done.returncode:
            raise RuntimeError(f"{pathlib.Path(argv[1]).name} exit {done.returncode}; "
                               f"see {log_path}")

    def render(self, crop, preset, wav, out) -> None:
        if not wav.exists():
            self.run([self.python, "scripts/render_listening_guitar.py", "--pack",
                      self.args.pack, "--di", crop["outputs"]["di"]["path"], "--preset",
                      str(preset), "--preroll-s", "0", "--out", str(wav)],
                     out / f"{wav.stem}-render.log")

    def match(self, crop, out, arm):
        a = self.args
        argv = [self.python, "scripts/match_preset.py", "--template", a.template,
                "--reference", crop["outputs"]["reference"]["path"], "--excerpt", "0",
                "--loss-profile", "unpaired-v3", "--pack", a.pack, "--amp", a.amp,
                "--renderer", "swift", "--process-policy", a.process_policy, "--budget",
                a.budget, "--shortlist", "3", "--seed", a.seed, "--out-dir", str(out / arm)]
        argv += (["--reference-mode", "paired_di", "--probe-di",
                  crop["outputs"]["di"]["path"]] if arm == "di"
                 else ["--reference-mode", "isolated_stem"])
        if not (out / arm / "summary.json").exists():
            self.run(argv, out / f"{arm}-match.log")
        summary = json.loads((out / arm / "summary.json").read_text())
        caveats = summary.get("caveats") or []
        fallback = any(c.startswith(NOTHING_BEAT) for c in caveats)
        preset = out / f"{arm}.xml"
        if not preset.exists():
            if fallback:
                shutil.copyfile(PLUGIN_ROOT / a.template, preset)
            else:
                self.run([self.python, "scripts/apply_spec.py", "--template", a.template,
                          "--spec", str(out / arm / "match-1.json"), "--out", str(preset)],
                         out / f"{arm}-preset.log")
        return summary, fallback

    def part(self, part, arms, catalog_path, data_root) -> dict:
        """One part's crops, template render and arms; each stage's failure is kept
        under `errors` until that stage succeeds, and never stops the other parts."""
        from benchmark_recordings import crops_for

        name = "/".join(part)
        out = self.out_dir / slug(part)
        out.mkdir(parents=True, exist_ok=True)
        result_path = out / "result.json"
        result = (json.loads(result_path.read_text()) if result_path.exists()
                  else {"part": name})
        errors = result.setdefault("errors", {})
        stage = "crops"
        try:
            crop = crops_for(catalog_path, data_root, self.args.crops_dir, *part)
            errors.pop(stage, None)
            reference = crop["outputs"]["reference"]["path"]
            result["reference_lufs"] = crop["reference_lufs"]
            result["crops"] = {role: output["sha256"]
                               for role, output in crop["outputs"].items()}
            stage = "template"
            if "template" not in result:
                self.render(crop, PLUGIN_ROOT / self.args.template, out / "template.wav", out)
                result["template"] = {**score(reference, out / "template.wav"),
                                      "measured_commit": self.commit}
            errors.pop(stage, None)
            for arm in arms:
                stage = arm
                if arm in result:
                    found = result[arm].get("process_policy", "reuse")
                    if found != self.args.process_policy:
                        raise RuntimeError(
                            f"this directory's {arm} arm searched with --process-policy "
                            f"{found}; choose another --out-dir for {self.args.process_policy}")
                    continue
                started = time.time()
                summary, fallback = self.match(crop, out, arm)
                search = summary.get("search") or {}
                check = search.get("guitar_check")
                if (check is not None and check.get("template_lufs") is None
                        and result["template"].get("lufs") is not None):
                    # The starting preset plays through the DI but was silent in the
                    # match's own guitar check: the plugin went silent mid-match, as
                    # when its licence daemon dies. Set the attempt aside so a rerun
                    # redoes it rather than keeping a search of silent renders.
                    _set_aside(out, arm)
                    raise RuntimeError("the plugin went silent during the match (the "
                                       "starting preset plays through its DI but not "
                                       "in the guitar check); rerun this part")
                self.render(crop, out / f"{arm}.xml", out / f"{arm}.wav", out)
                entry = score(reference, out / f"{arm}.wav")
                entry.update(silent_trials=(search.get("accounting") or {}).get("silent"),
                             fallback_to_template=fallback,
                             minutes=round((time.time() - started) / 60, 1),
                             measured_commit=self.commit,
                             process_policy=self.args.process_policy,
                             caveats=summary.get("caveats"),
                             guitar_check=(summary.get("search") or {}).get("guitar_check"))
                result[arm] = entry
                errors.pop(arm, None)
                result_path.write_text(json.dumps(result, indent=1))
                self.log(f"{name} {arm}: {entry['vs_reference_lu']} LU, "
                         f"v3 {entry['v3_no_level']:.3f} ({entry['minutes']} min)")
        except Exception as error:  # noqa: BLE001 - one part must not stop the rest
            errors[stage] = f"{type(error).__name__}: {error}"
            self.log(f"{name} {stage} FAILED: {errors[stage]}")
        if not errors:
            result.pop("errors")
        result_path.write_text(json.dumps(result, indent=1))
        return result


def _set_aside(out: pathlib.Path, arm: str) -> None:
    """Move an arm's match, preset and render out of the way, keeping them."""
    aside = out / f"{arm}.silent-attempt"
    shutil.rmtree(aside, ignore_errors=True)
    aside.mkdir()
    for name in (arm, f"{arm}.xml", f"{arm}.wav", f"{arm}.wav.render.json"):
        if (out / name).exists():
            shutil.move(str(out / name), str(aside / name))


def _spread(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {"n": len(values), "min": round(min(values), 3),
            "median": round(statistics.median(values), 3), "max": round(max(values), 3)}


def match_one_trim(entry) -> dict | None:
    """The level trim's record for match-1, when the guitar check ran."""
    check = (entry or {}).get("guitar_check") or {}
    return next((record for record in (check.get("level_trim") or {}).get("records", [])
                 if record["match"] == 1), None)


def summarise(results) -> dict:
    """Per arm: loudness gaps and distances; the guitar check and level trim; and
    each arm's distance paired against the others', level left out."""
    summary = {"parts": len(results),
               "failed": [f"{r['part']}: {stage}" for r in results
                          for stage in sorted(r.get("errors", {}))]}
    for arm in ("template", *ARMS):
        done = [r for r in results if arm in r]
        levels = [r[arm]["vs_reference_lu"] for r in done]
        summary[arm] = {
            "parts": len(done),
            "vs_reference_lu": _spread(levels),
            "within_3_lu": sum(1 for v in levels if v is not None and abs(v) <= 3),
            "unmeasurable": [r["part"] for r in done if r[arm]["lufs"] is None],
            "v3_no_level": _spread([r[arm]["v3_no_level"] for r in done]),
            "v3": _spread([r[arm]["v3"] for r in done]),
        }
        if arm != "template":
            summary[arm]["fell_back_to_template"] = sum(
                r[arm]["fallback_to_template"] for r in done)
    no_di = [r for r in results if "no_di" in r]
    fired, moves, before, off = [], [], [], []
    for r in no_di:
        candidates = (r["no_di"].get("guitar_check") or {}).get("candidates", [])
        if any(c.get("passes") is False for c in candidates):
            fired.append(r["part"])
        trim = match_one_trim(r["no_di"])
        if trim and trim["applied"] and not r["no_di"]["fallback_to_template"]:
            moved = trim["after"] - trim["before"]
            if not trim["clamped"] and abs(trim.get("residual_db") or 0) > 1:
                off.append(r["part"])
            moves.append(moved)
            if r["no_di"]["vs_reference_lu"] is not None:
                before.append(r["no_di"]["vs_reference_lu"] - moved)
    summary["guitar_check_failed_a_candidate"] = fired
    summary["no_di_silent_trials"] = [r["part"] for r in no_di
                                      if r["no_di"].get("silent_trials")]
    # "before the trim" is the measured level less the move, which holds only if
    # the output gain acts linearly: `landed_off_target` lists where, through the
    # synthetic guitar, the trimmed level missed its target by more than 1 dB.
    summary["level_trim_on_match_1"] = {
        "applied": len(moves), "moved_db": _spread(moves),
        "landed_off_target": off,
        "vs_reference_lu_before_trim": _spread(before),
        "clamped": sum(bool((match_one_trim(r["no_di"]) or {}).get("clamped"))
                       for r in no_di)}
    pairs = {}
    for first, second in (("di", "no_di"), ("di", "template"), ("no_di", "template")):
        both = [r for r in results if first in r and second in r]
        if both:
            pairs[f"{first}_closer_than_{second}"] = {
                "closer": sum(r[first]["v3_no_level"] < r[second]["v3_no_level"]
                              for r in both),
                "of": len(both),
                "median_change": round(statistics.median(
                    r[first]["v3_no_level"] / r[second]["v3_no_level"] - 1
                    for r in both), 3)}
    summary["paired_v3_no_level"] = pairs
    return summary


def main() -> None:
    args = build_parser().parse_args()
    out_dir = (args.out_dir or PLUGIN_ROOT / "runs" /
               f"match-pipeline-{args.pack}-{args.amp}"
               f"{'-fresh' if args.process_policy == 'fresh' else ''}"
               ).expanduser().absolute()
    if not out_dir.is_relative_to(PLUGIN_ROOT / "runs"):
        die("--out-dir must be under this checkout's runs/, which the renders require")
    from analysis import require

    require("running the match-pipeline benchmark")
    from benchmark_match import _source_commit
    from benchmark_recordings import CATALOG, development_parts

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    parts = development_parts(catalog, args.part, args.sets)
    if not parts:
        die("no usable development parts selected")
    data_root = pathlib.Path(catalog["root"]).expanduser()
    arms = args.arm or list(ARMS)
    runner = Runner(args, out_dir, _source_commit())
    runner.log(f"{len(parts)} parts, arms {arms}, {args.parallel} at once, {out_dir}")
    results = {}
    for arm in arms:  # every part's no-DI arm before any DI arm
        with ThreadPoolExecutor(args.parallel) as pool:
            for part, result in zip(parts, pool.map(
                    lambda p: runner.part(p, [arm], CATALOG, data_root), parts)):
                results[part] = result
    summary = summarise([results[part] for part in parts])
    print(json.dumps(summary, indent=1))
    if args.json:
        args.json.write_text(json.dumps({
            "schema": SCHEMA, "source_commit": _source_commit(),
            "command": " ".join(sys.argv), "template": args.template,
            "pack": args.pack, "amp": args.amp, "budget": args.budget, "seed": args.seed,
            "loss_profile": "unpaired-v3",
            "process_policy": {"search": args.process_policy, "scoring_renders": "fresh"},
            "measurement_caveat": (MEASUREMENT_CAVEAT if args.process_policy == "reuse"
                                   else FRESH_CAVEAT)
                                  + (TONE_KING_CAVEAT if args.pack == "toneking" else ""),
            "summary": summary,
            # Each arm's caveats stay in its part's result.json; they repeat.
            "parts": [{key: ({k: v for k, v in value.items() if k != "caveats"}
                             if key in ARMS else value)
                       for key, value in results[part].items()}
                      for part in parts]}, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {args.json}")


if __name__ == "__main__":
    guarded(main)
