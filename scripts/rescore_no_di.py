#!/usr/bin/env python3
"""Re-score the no-DI answers against their starting presets under the judge.

    python scripts/rescore_no_di.py \\
        --runs-root ~/projects/neuraldsp-preset-generator/.claude/worktrees \\
        --json no-di-under-the-judge.json

Declared in `docs/no-di-rule-under-the-judge-plan.md`: every part's
log(d_arm / d_start) under `analysis.aligned.aligned_distance`, both band sets, over
1.0-10 s of its amp-track crop at its recorded lag (`docs/validation-lags.json`), and
at each render's own best lag within ±2 ms; band medians, their sum, the exact
two-sided band sign-flip p, Holm over the 16 comparisons in each band set; verdicts
(better, worse, not shown), three sensitivity readings, and the controls.
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

LIB = {"sw50r": "lib-sw50r-shipped", "pr12": "lib-pr12-shipped",
       "ac20": "lib-ac20-shipped", "toneking": "lib-tk-default"}
NO_DI = {"sw50r": "bench-nodi/runs/match-pipeline-template-s11",
         "pr12": "bench-nodi/runs/start-pr12-shipped",
         "ac20": "bench-tk/runs/start-ac20-shipped",
         "toneking": "bench-tk/runs/start-tk-default"}
# name -> (amp, start run, start file, arm run, arm file)
COMPARISONS = {
    **{f"{amp}|no_di": (amp, run, "template", run, "no_di") for amp, run in NO_DI.items()},
    **{f"{amp}|{arm}": (amp, f"bench-set2/runs/{LIB[amp]}", "template",
                        f"bench-set2/runs/{LIB[amp]}", arm)
       for amp in LIB for arm in ("library", "calc-library", "calc-noise")},
}
CONTROLS = {
    "sw50r|own_di (positive)": ("sw50r", "bench-set2/runs/set2-rehearsal", "template",
                                "bench-set2/runs/set2-rehearsal", "di"),
    "sw50r|no_di seed 0 (replicate)": ("sw50r", "bench-set2/runs/set2-rehearsal", "template",
                                       "bench-set2/runs/set2-rehearsal", "no_di"),
    "toneking|start vs start (null)": ("toneking", NO_DI["toneking"], "template",
                                       f"bench-set2/runs/{LIB['toneking']}", "template"),
}
LATENCY = {"sw50r": 52, "pr12": 52, "ac20": 52, "toneking": 51}
PACK = {"sw50r": "morgan", "pr12": "morgan", "ac20": "morgan", "toneking": "toneking"}
A_START, A_END = 48000, 480000            # the scored window, 1.0-10 s, in samples
OWN_SPAN = 96                             # ±2 ms
BAND_SETS = ("recording", "union")
LAG_MODES = ("recorded", "own")
LOSS = 1.0                    # log ratio given an arm with no measurable loudness
PAUSE_LIMIT = 0.2


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-root", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=3)
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
    """{(run, file): {lag mode: {band set: (distance, reason)}}} and checks for a part."""
    part, crops, lag, renders = job
    import soundfile as sf

    import numpy as np

    from analysis.aligned import aligned_distance
    from record_part_lags import correlation

    def mono(path):
        x, rate = sf.read(str(path), dtype="float64")
        if rate != 48000:
            raise ValueError(f"{path} is at {rate} Hz")
        return x.mean(axis=1) if x.ndim == 2 else x

    crop_di = crops / part / "di.wav"
    di_sha = _sha(crop_di)
    ref, di = mono(crops / part / "reference.wav"), mono(crop_di)
    out, mismatched = {}, []
    for (run, name), amp in renders.items():
        wav = run / part / f"{name}.wav"
        record = json.loads((run / part / f"{name}.wav.render.json").read_text())
        if record["di"]["sha256"] != di_sha or record["pack"] != PACK[amp]:
            mismatched.append(str(wav))
        x = mono(wav)
        latency = LATENCY[amp]
        recorded = lag - latency
        # Its own best lag: the 80 Hz-2 kHz correlation's peak within ±2 ms.
        lags, total = correlation(ref, [x], recorded, OWN_SPAN)
        own = int(lags[np.argmax(total)])
        entry = {"own_lag": own + latency}
        for mode, shift in (("recorded", recorded), ("own", own)):
            entry[mode] = {}
            for bands in BAND_SETS:
                r = aligned_distance(ref, x, di, lag=shift, render_latency=latency,
                                     start_s=A_START / 48000, end_s=A_END / 48000,
                                     bands=bands)
                entry[mode][bands] = (r.distance, r.reason)
        out[f"{run.name}/{name}"] = entry
    pauses = pause_share(di, A_START, lag, min(len(ref), A_END) - A_START)
    print(part, flush=True)
    return part, {"renders": out, "di_mismatched": mismatched, "pause_share": pauses}


def sign_flip_p(values):
    """Exact two-sided sign-flip p of the sum of the values (unrounded)."""
    obs = abs(sum(values))
    hits = sum(abs(sum(s * v for s, v in zip(signs, values))) >= obs - 1e-12
               for signs in itertools.product((1, -1), repeat=len(values)))
    return hits / 2 ** len(values)


def summarise(rows):
    """Band medians and their statistics for rows of {part, band, source, x}."""
    by = {}
    for r in rows:
        by.setdefault(r["band"], []).append(r["x"])
    medians = {b: statistics.median(v) for b, v in by.items()}
    vals = list(medians.values())
    if not vals:
        return None
    src = {}
    for r in rows:
        src.setdefault(r["source"], []).append(r["x"])
    return {"bands": len(vals), "band_median": statistics.median(vals), "band_sum": sum(vals),
            "p": sign_flip_p(vals), "bands_better": sum(v < 0 for v in vals),
            "parts": len(rows), "parts_better": sum(r["x"] < 0 for r in rows),
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


def verdicts(stats: dict) -> dict:
    """{comparison: verdict} under one band set's Holm family."""
    adjusted = holm({k: (s["p"] if s else 1.0) for k, s in stats.items()})
    out = {}
    for k, s in stats.items():
        if s and adjusted[k] < 0.05 and s["band_median"] < 0 and s["band_sum"] < 0:
            out[k] = "better"
        elif s and adjusted[k] < 0.05 and s["band_median"] > 0 and s["band_sum"] > 0:
            out[k] = "worse"
        else:
            out[k] = "not shown"
    return {k: {"verdict": v, "holm_p": adjusted[k]} for k, v in out.items()}


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
                          "source": s["source"]}
    root = args.runs_root.expanduser()
    every = {**COMPARISONS, **CONTROLS}
    renders = {}
    for amp, srun, sname, arun, aname in every.values():
        renders[(root / srun, sname)] = amp
        renders[(root / arun, aname)] = amp
    parts = sorted(p.name for p in (root / NO_DI["sw50r"]).iterdir() if p.is_dir())
    for run, _ in renders:
        if sorted(p.name for p in run.iterdir() if p.is_dir()) != parts:
            die(f"{run} does not hold the same parts")
    lags = {p: lag_record(p) for p in parts}
    if any(r is None for r in lags.values()):
        die(f"no recorded lag for {[p for p, r in lags.items() if r is None]}")
    from concurrent.futures import ProcessPoolExecutor

    crops = args.crops_dir.expanduser()
    with ProcessPoolExecutor(args.workers) as ex:
        scored = dict(ex.map(score_part, [(p, crops, lags[p]["lag_samples"], renders)
                                          for p in parts]))
    mismatched = [m for s in scored.values() for m in s["di_mismatched"]]
    if mismatched:
        die(f"renders not made from their part's DI crop, or by another pack: "
            f"{mismatched[:5]}")
    ambiguous = [p for p, r in lags.items() if r["ambiguous"]]
    pausy = [p for p, s in scored.items() if s["pause_share"] > PAUSE_LIMIT]

    def rows_for(spec, mode, bands, drop=()):
        amp, srun, sname, arun, aname = spec
        rows, refused = [], []
        for p in parts:
            if p in drop:
                continue
            got = scored[p]["renders"]
            ds, rs = got[f"{pathlib.Path(srun).name}/{sname}"][mode][bands]
            da, ra = got[f"{pathlib.Path(arun).name}/{aname}"][mode][bands]
            if ds is None:
                refused.append({"part": p, "reason": rs})
                continue
            if da is None:
                if ra and "loudness" in ra:
                    x = LOSS                               # a silent answer loses
                else:
                    refused.append({"part": p, "reason": ra})
                    continue
            else:
                x = math.log(da / ds)
            rows.append({"part": p, "band": meta[p]["band"], "source": meta[p]["source"],
                         "x": x, "d_start": ds, "d_arm": da})
        return rows, refused

    def reading(mode, drop=()):
        out = {}
        for bands in BAND_SETS:
            stats = {}
            for name, spec in COMPARISONS.items():
                rows, _ = rows_for(spec, mode, bands, drop)
                stats[name] = summarise(rows)
            v = verdicts(stats)
            out[bands] = {k: {**(stats[k] or {}), **v[k]} for k in stats}
        combined = {}
        for k in COMPARISONS:
            a, b = out["recording"][k]["verdict"], out["union"][k]["verdict"]
            combined[k] = a if a == b else "not shown"
        return {"by_band_set": out, "verdict": combined}

    main_reading = reading("recorded")
    sensitivities = {"ambiguous lags dropped": reading("recorded", ambiguous),
                     "own lags": reading("own"),
                     "pause-heavy parts dropped": reading("recorded", pausy)}
    fragile = {k: any(s["verdict"][k] != v for s in sensitivities.values())
               for k, v in main_reading["verdict"].items()}
    controls = {}
    for name, spec in CONTROLS.items():
        controls[name] = {bands: summarise(rows_for(spec, "recorded", bands)[0])
                          for bands in BAND_SETS}
    every_rows = {name: {bands: rows_for(spec, "recorded", bands)
                         for bands in BAND_SETS} for name, spec in every.items()}
    commit = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    out = {"plan": "docs/no-di-rule-under-the-judge-plan.md", "commit": commit,
           "lags_sha256": _sha(LAGS), "runs": {k: [v[1], v[3]] for k, v in every.items()},
           "parts": len(parts), "ambiguous_lags": ambiguous, "pause_heavy": pausy,
           "pause_share": {p: s["pause_share"] for p, s in scored.items()},
           "own_lags": {p: {k: v["own_lag"] for k, v in s["renders"].items()}
                        for p, s in scored.items()},
           "verdict": main_reading["verdict"], "fragile": fragile,
           "main": main_reading["by_band_set"],
           "sensitivities": {k: v["verdict"] for k, v in sensitivities.items()},
           "controls": controls,
           "rows": {k: {b: {"rows": r[0], "refused": r[1]} for b, r in v.items()}
                    for k, v in every_rows.items()}}
    print(json.dumps({"verdict": out["verdict"], "fragile": fragile,
                      "controls": {k: {b: (s or {}).get("band_median") for b, s in v.items()}
                                   for k, v in controls.items()}}, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
