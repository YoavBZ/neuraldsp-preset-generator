#!/usr/bin/env python3
"""Re-score the no-DI answers against their starting presets under the judge.

    python scripts/rescore_no_di.py \\
        --runs-root ~/projects/neuraldsp-preset-generator/.claude/worktrees \\
        --json no-di-under-the-judge.json

Declared in `docs/no-di-rule-under-the-judge-plan.md`: every part's
log(d_arm / d_start) under `analysis.aligned.aligned_distance`, both band sets, over
1.0-10 s of its amp-track crop at its recorded lag (`docs/validation-lags.json`), and
at each render's own best lag within ±2 ms; band medians, their sum, the exact
two-sided band sign-flip p, Holm within each family of 8 comparisons and band set;
verdicts (better, worse, not shown), the controls' criteria, and three sensitivity
readings. `--design-counts` scores the start renders only and prints how many parts
and bands each reading keeps, which depends on no arm.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import pathlib
import statistics
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

LIB = {"sw50r": "bench-set2/runs/lib-sw50r-shipped", "pr12": "bench-set2/runs/lib-pr12-shipped",
       "ac20": "bench-set2/runs/lib-ac20-shipped", "toneking": "bench-set2/runs/lib-tk-default"}
NO_DI = {"sw50r": "bench-nodi/runs/match-pipeline-template-s11",
         "pr12": "bench-nodi/runs/start-pr12-shipped",
         "ac20": "bench-tk/runs/start-ac20-shipped",
         "toneking": "bench-tk/runs/start-tk-default"}
REHEARSAL = "bench-set2/runs/set2-rehearsal"
# name -> (amp, start run, start file, arm run, arm file); each arm against its own run's start.
COMPARISONS = {
    **{f"{amp}|no_di": (amp, run, "template", run, "no_di") for amp, run in NO_DI.items()},
    **{f"{amp}|{arm}": (amp, run, "template", run, arm)
       for amp, run in LIB.items() for arm in ("calc-noise", "library", "calc-library")},
}
# The no-DI search and the noise probe's answer could ship; the library's probe is made
# from the project's own development DIs, so its two arms cannot.
FAMILIES = {"product": [k for k in COMPARISONS if k.endswith(("|no_di", "|calc-noise"))],
            "research": [k for k in COMPARISONS if k.endswith(("|library", "|calc-library"))]}
CONTROLS = {
    "positive": ("sw50r", REHEARSAL, "template", REHEARSAL, "di"),
    "replicate": ("sw50r", REHEARSAL, "template", REHEARSAL, "no_di"),
    "null": ("toneking", NO_DI["toneking"], "template", LIB["toneking"], "template"),
}
LATENCY = {"sw50r": 52, "pr12": 52, "ac20": 52, "toneking": 51}
PACK = {"sw50r": "morgan", "pr12": "morgan", "ac20": "morgan", "toneking": "toneking"}
AMP_MODEL = {"sw50r": "SW50R", "pr12": "PR12", "ac20": "AC20", "toneking": "Rhythm Channel"}
A_START, A_END = 48000, 480000            # the scored window, 1.0-10 s, in samples
OWN_SPAN = 96                             # ±2 ms
BAND_SETS = ("recording", "union")
LOSS = 1.0                                # the log ratio an arm that loses outright gets
QUIET_LU = 20.0                           # an arm this far under its start loses
PAUSE_LIMIT = 0.2
ALPHA = 0.05


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-root", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--design-counts", action="store_true",
                    help="score the start renders only: the parts and bands of each reading")
    return ap


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pause_share(di, start, lag, length, n_fft=2048, tail_s=1.5, di_floor_db=40.0):
    """Share of the judge's scored frames that are pauses, at 2048 points: its own
    computation (`aligned_distance`), for a window of `length` samples from `start` of
    the recording, which lags the DI by `lag`."""
    from analysis import aligned as A

    sr = A.SAMPLE_RATE
    hop = n_fft // 4
    pre = math.ceil(tail_s * sr / hop)
    seg = A._segment(di, start - lag - pre * hop, length + pre * hop)
    playing = A._frame_db(seg, n_fft) >= A._frame_db(di, n_fft).max() - di_floor_db
    scored = A._extend(playing, int(round(tail_s * sr / hop)))
    k = 1 + (length - n_fft) // hop
    playing, scored = playing[pre: pre + k], scored[pre: pre + k]
    return float(1.0 - playing.sum() / scored.sum()) if scored.any() else 1.0


def score_part(job):
    """Every listed render of one part: its own lag, its loudness over the window, and
    the judge's (distance, reason, offset dB) at each lag mode and band set."""
    part, crops, lag, renders = job
    import numpy as np
    import soundfile as sf

    from analysis import io
    from analysis.aligned import aligned_distance
    from record_part_lags import correlation

    def mono(path):
        x, rate = sf.read(str(path), dtype="float64")
        if rate != 48000:
            raise ValueError(f"{path} is at {rate} Hz")
        return x.mean(axis=1) if x.ndim == 2 else x

    record = json.loads((crops / part / "record.json").read_text())["outputs"]
    problems = []
    for name in ("di", "reference"):
        if _sha(crops / part / f"{name}.wav") != record[name]["sha256"]:
            problems.append(f"{part}/{name}.wav differs from its crop record")
    di_sha = record["di"]["sha256"]
    ref, di = mono(crops / part / "reference.wav"), mono(crops / part / "di.wav")
    out = {}
    for key, (path, amp) in renders.items():
        meta = json.loads(pathlib.Path(f"{path}.render.json").read_text())
        if (meta["di"]["sha256"] != di_sha or meta["pack"] != PACK[amp]
                or meta["amp_model"] != AMP_MODEL[amp]):
            problems.append(f"{path}: not this part's DI, or another pack or amp")
        x = mono(path)
        latency = LATENCY[amp]
        recorded = lag - latency
        lags, total = correlation(ref, [x], recorded, OWN_SPAN)
        own = int(lags[np.argmax(total)])
        entry = {"own_lag": own + latency,
                 "lufs": io.loudness_lufs(io.from_samples(x[A_START:A_END], 48000))}
        for mode, shift in (("recorded", recorded), ("own", own)):
            entry[mode] = {}
            for bands in BAND_SETS:
                r = aligned_distance(ref, x, di, lag=shift, render_latency=latency,
                                     start_s=A_START / 48000, end_s=A_END / 48000,
                                     bands=bands)
                entry[mode][bands] = [r.distance, r.reason, r.offset_db]
        out[key] = entry
    pauses = pause_share(di, A_START, lag, min(len(ref), A_END) - A_START)
    print(part, flush=True)
    return part, {"renders": out, "problems": problems, "pause_share": pauses}


def sign_flip_p(values):
    """Exact two-sided sign-flip p of the sum of the values (unrounded)."""
    obs = abs(sum(values))
    hits = sum(abs(sum(s * v for s, v in zip(signs, values))) >= obs - 1e-12
               for signs in itertools.product((1, -1), repeat=len(values)))
    return hits / 2 ** len(values)


def summarise(rows):
    """Band medians and their statistics for rows of {part, band, source, x, loss}."""
    by = {}
    for r in rows:
        by.setdefault(r["band"], []).append(r["x"])
    medians = {b: statistics.median(v) for b, v in sorted(by.items())}
    vals = list(medians.values())
    if not vals:
        return None
    src = {}
    for r in rows:
        src.setdefault(r["source"], []).append(r["x"])
    return {"bands": len(vals), "band_medians": medians,
            "band_median": statistics.median(vals), "band_sum": sum(vals),
            "p": sign_flip_p(vals), "bands_better": sum(v < 0 for v in vals),
            "parts": len(rows), "parts_better": sum(r["x"] < 0 for r in rows),
            "losses": sum(r["loss"] is not None for r in rows),
            "part_median": statistics.median(r["x"] for r in rows),
            "by_source": {s: {"parts": len(v), "parts_better": sum(x < 0 for x in v),
                              "part_median": statistics.median(v)} for s, v in src.items()}}


def holm(ps: dict) -> dict:
    order = sorted(ps, key=ps.get)
    adjusted, running = {}, 0.0
    for i, key in enumerate(order):
        running = max(running, min(1.0, (len(order) - i) * ps[key]))
        adjusted[key] = running
    return adjusted


def direction(s, p):
    """better / worse / not shown, for one comparison's statistics and its p."""
    if s and p < ALPHA and s["band_median"] < 0 and s["band_sum"] < 0:
        return "better"
    if s and p < ALPHA and s["band_median"] > 0 and s["band_sum"] > 0:
        return "worse"
    return "not shown"


def verdicts(stats: dict) -> dict:
    """{comparison: {verdict, holm_p}} under one band set, Holm within each family."""
    out = {}
    for members in FAMILIES.values():
        adjusted = holm({k: (stats[k]["p"] if stats[k] else 1.0) for k in members})
        for k in members:
            out[k] = {"verdict": direction(stats[k], adjusted[k]), "holm_p": adjusted[k]}
    return out


def informative(bands: int, family_size: int = 8) -> bool:
    """Whether a reading with this many bands can reach significance at all."""
    return family_size * 2 / 2 ** bands < ALPHA


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("re-scoring the no-DI answers")
    from benchmark_recordings import CATALOG, LAGS, lag_record

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    meta = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            meta[slug] = {"band": s.get("group") or f"{s['source']}/{s['song']}",
                          "source": s["source"], "split": p.get("split") or s.get("split")}
    root = args.runs_root.expanduser()
    every = {**COMPARISONS, **CONTROLS}
    starts = {f"{srun}/{sname}" for _, srun, sname, _, _ in every.values()}
    wanted = {}
    for amp, srun, sname, arun, aname in every.values():
        wanted[f"{srun}/{sname}"] = amp
        if not args.design_counts:
            wanted[f"{arun}/{aname}"] = amp
    runs = {key.rsplit("/", 1)[0] for key in wanted}
    parts = sorted(p.name for p in (root / NO_DI["sw50r"]).iterdir() if p.is_dir())
    for run in runs:
        if sorted(p.name for p in (root / run).iterdir() if p.is_dir()) != parts:
            die(f"{run} does not hold the same parts")
    if any(meta[p]["split"] != "development" for p in parts):
        die("a run holds a part that is not development material")
    lags = {p: lag_record(p) for p in parts}
    if any(r is None for r in lags.values()):
        die(f"no recorded lag for {[p for p, r in lags.items() if r is None]}")
    from concurrent.futures import ProcessPoolExecutor

    crops = args.crops_dir.expanduser()
    jobs = [(p, crops, lags[p]["lag_samples"],
             {key: (root / key.rsplit("/", 1)[0] / p / f"{key.rsplit('/', 1)[1]}.wav", amp)
              for key, amp in wanted.items()}) for p in parts]
    with ProcessPoolExecutor(args.workers) as ex:
        scored = dict(ex.map(score_part, jobs))
    problems = [m for s in scored.values() for m in s["problems"]]
    if problems:
        die(f"renders or crops that are not what they should be: {problems[:5]}")

    def refused_start(p, mode):
        """The start renders' refusals of part p at this lag mode, under either band set."""
        return sorted({f"{k}: {v[mode][b][1]}" for k, v in scored[p]["renders"].items()
                       if k in starts for b in BAND_SETS if v[mode][b][0] is None})

    excluded = {p: refused_start(p, "recorded") for p in parts if refused_start(p, "recorded")}
    ambiguous = sorted(p for p, r in lags.items() if r["ambiguous"])
    pausy = sorted(p for p, s in scored.items() if s["pause_share"] > PAUSE_LIMIT)
    drops = {"main": set(), "ambiguous lags dropped": set(ambiguous),
             "own lags": set(), "pause-heavy parts dropped": set(pausy)}

    def kept(reading):
        mode = "own" if reading == "own lags" else "recorded"
        return [p for p in parts if p not in excluded and p not in drops[reading]
                and not refused_start(p, mode)]

    counts = {r: {"parts": len(kept(r)), "bands": len({meta[p]["band"] for p in kept(r)}),
                  "informative": informative(len({meta[p]["band"] for p in kept(r)}))}
              for r in drops}
    if args.design_counts:
        print(json.dumps({"excluded": excluded, "ambiguous": ambiguous, "pause_heavy": pausy,
                          "readings": counts}, indent=1))
        return

    def rows_for(spec, reading, bands):
        amp, srun, sname, arun, aname = spec
        mode = "own" if reading == "own lags" else "recorded"
        rows = []
        for p in kept(reading):
            got = scored[p]["renders"]
            start, arm = got[f"{srun}/{sname}"], got[f"{arun}/{aname}"]
            ds, da, reason = start[mode][bands][0], arm[mode][bands][0], arm[mode][bands][1]
            loss = None
            if arm["lufs"] is None:
                loss = "no measurable loudness"
            elif start["lufs"] is not None and arm["lufs"] < start["lufs"] - QUIET_LU:
                loss = f"{start['lufs'] - arm['lufs']:.1f} LU under its start"
            elif da is None:
                loss = f"refused: {reason}"
            rows.append({"part": p, "band": meta[p]["band"], "source": meta[p]["source"],
                         "x": LOSS if loss else math.log(da / ds), "loss": loss,
                         "d_start": ds, "d_arm": da,
                         "offset_db_start": start[mode][bands][2],
                         "offset_db_arm": arm[mode][bands][2],
                         "lufs_start": start["lufs"], "lufs_arm": arm["lufs"]})
        return rows

    def reading(name):
        out = {}
        for bands in BAND_SETS:
            stats = {k: summarise(rows_for(spec, name, bands)) for k, spec in COMPARISONS.items()}
            v = verdicts(stats)
            out[bands] = {k: {**(stats[k] or {}), **v[k]} for k in stats}
        combined = {}
        for k in COMPARISONS:
            a, b = out["recording"][k]["verdict"], out["union"][k]["verdict"]
            combined[k] = a if a == b else "not shown"
        return {"by_band_set": out, "verdict": combined}

    readings = {name: reading(name) for name in drops}
    main_reading = readings.pop("main")

    controls = {}
    for name, spec in CONTROLS.items():
        stats = {b: summarise(rows_for(spec, "main", b)) for b in BAND_SETS}
        controls[name] = {"by_band_set": stats}
    pos = controls["positive"]["by_band_set"]
    controls["positive"]["passes"] = all(
        direction(pos[b], pos[b]["p"] if pos[b] else 1.0) == "better" for b in BAND_SETS)
    null = controls["null"]["by_band_set"]
    controls["null"]["passes"] = all(null[b] and null[b]["p"] >= ALPHA for b in BAND_SETS)
    rep = controls["replicate"]["by_band_set"]
    s11 = main_reading["by_band_set"]
    controls["replicate"]["same_sign_as_seed_11"] = all(
        rep[b] and (rep[b]["band_median"] > 0) == (s11[b]["sw50r|no_di"]["band_median"] > 0)
        for b in BAND_SETS)

    final = {}
    for k, v in main_reading["verdict"].items():
        why = [name for name, r in readings.items()
               if counts[name]["informative"] and r["verdict"][k] != v]
        if k == "sw50r|no_di" and not controls["replicate"]["same_sign_as_seed_11"]:
            why.append("seed 0 points the other way")
        if not controls["positive"]["passes"]:
            final[k] = {"verdict": "void: the positive control fails", "fragile": why}
        elif k.startswith("toneking|") and not controls["null"]["passes"]:
            final[k] = {"verdict": "not read: the null control fails", "fragile": why}
        else:
            final[k] = {"verdict": v, "fragile": why,
                        "for the wording": "not shown" if why else v}
    own_drift = {p: {k: v["own_lag"] - lags[p]["lag_samples"] for k, v in s["renders"].items()
                     if abs(v["own_lag"] - lags[p]["lag_samples"]) > 24}
                 for p, s in scored.items()}
    commit = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    out = {"plan": "docs/no-di-rule-under-the-judge-plan.md", "commit": commit,
           "lags_sha256": _sha(LAGS), "runs": {k: [v[1], v[3]] for k, v in every.items()},
           "parts": len(parts), "excluded": excluded, "ambiguous_lags": ambiguous,
           "pause_heavy": pausy, "readings": counts,
           "pause_share": {p: s["pause_share"] for p, s in scored.items()},
           "own_lags_over_half_a_ms_away": {p: d for p, d in own_drift.items() if d},
           "final": final, "controls": controls, "main": main_reading,
           "sensitivities": readings,
           "rows": {k: {b: rows_for(spec, "main", b) for b in BAND_SETS}
                    for k, spec in every.items()}}
    print(json.dumps({"final": final,
                      "controls": {k: {kk: vv for kk, vv in v.items() if kk != "by_band_set"}
                                   for k, v in controls.items()}}, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
