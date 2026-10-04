#!/usr/bin/env python3
"""Re-score the no-DI answers against their starting presets under the judge.

    python scripts/rescore_no_di.py --runs-root ~/projects/neuraldsp-preset-generator/.claude/worktrees \\
        --json no-di-under-the-judge.json

Declared in `docs/no-di-rule-under-the-judge-plan.md`. For each amp and arm, every part's
log(d_arm / d_start) under `analysis.aligned.aligned_distance` (default bands; the union
band set beside it), over 1.0-10 s of the part's amp-track crop, with the part's
recorded lag (`docs/validation-lags.json`) less the amp's latency; band medians, parts
closer, exact two-sided band sign-flip p, and Holm over the 16 comparisons.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

# (amp, arm) -> run directory under --runs-root, and the start's file in it.
RUNS = {
    ("sw50r", "no_di"): "bench-nodi/runs/match-pipeline-template-s11",
    ("pr12", "no_di"): "bench-nodi/runs/start-pr12-shipped",
    ("ac20", "no_di"): "bench-tk/runs/start-ac20-shipped",
    ("toneking", "no_di"): "bench-tk/runs/start-tk-default",
    **{(amp, arm): f"bench-set2/runs/lib-{run}"
       for amp, run in (("sw50r", "sw50r-shipped"), ("pr12", "pr12-shipped"),
                        ("ac20", "ac20-shipped"), ("toneking", "tk-default"))
       for arm in ("library", "calc-library", "calc-noise")},
}
LATENCY = {"sw50r": 52, "pr12": 52, "ac20": 52, "toneking": 51}
BAND_SETS = ("recording", "union")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-root", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=3)
    return ap


def score_part(job):
    """{(amp, arm): {band set: (d_start, d_arm, reason)}} for one part."""
    part, crops, lag, runs = job
    import soundfile as sf

    from analysis.aligned import aligned_distance

    def mono(path):
        x, rate = sf.read(str(path), dtype="float64")
        assert rate == 48000
        return x.mean(axis=1) if x.ndim == 2 else x

    ref, di = mono(crops / part / "reference.wav"), mono(crops / part / "di.wav")
    out = {}
    for (amp, arm), run in runs.items():
        d = {}
        for bands in BAND_SETS:
            pair = []
            for name in ("template", arm):
                r = aligned_distance(ref, mono(run / part / f"{name}.wav"), di,
                                     lag=lag - LATENCY[amp], render_latency=LATENCY[amp],
                                     start_s=1.0, end_s=10.0, bands=bands)
                pair.append((r.distance, r.reason))
            d[bands] = {"start": pair[0][0], "arm": pair[1][0],
                        "refused": pair[0][1] or pair[1][1]}
        out[f"{amp}|{arm}"] = d
    print(part, flush=True)
    return part, out


def holm(ps: dict) -> dict:
    order = sorted(ps, key=ps.get)
    adjusted, running = {}, 0.0
    for i, key in enumerate(order):
        running = max(running, min(1.0, (len(order) - i) * ps[key]))
        adjusted[key] = running
    return adjusted


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("re-scoring the no-DI answers")
    import kill_tests as K
    from benchmark_recordings import CATALOG, lag_record

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    band = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            band[slug] = s.get("group") or f"{s['source']}/{s['song']}"
    root = args.runs_root.expanduser()
    runs = {key: root / rel for key, rel in RUNS.items()}
    parts = sorted(p.name for p in runs[("sw50r", "no_di")].iterdir() if p.is_dir())
    for key, run in runs.items():
        if sorted(p.name for p in run.iterdir() if p.is_dir()) != parts:
            die(f"{run} does not hold the same parts")
    lags = {p: lag_record(p) for p in parts}
    missing = [p for p, r in lags.items() if r is None]
    if missing:
        die(f"no recorded lag for {missing}")
    from concurrent.futures import ProcessPoolExecutor

    crops = args.crops_dir.expanduser()
    with ProcessPoolExecutor(args.workers) as ex:
        scored = dict(ex.map(score_part, [(p, crops, lags[p]["lag_samples"], runs)
                                          for p in parts]))
    out = {"plan": "docs/no-di-rule-under-the-judge-plan.md", "parts": len(parts),
           "ambiguous_lags": [p for p, r in lags.items() if r["ambiguous"]],
           "comparisons": {}}
    pvalues = {}
    for (amp, arm) in RUNS:
        key = f"{amp}|{arm}"
        entry = {}
        for bands in BAND_SETS:
            rows, refused = [], []
            for p in parts:
                d = scored[p][key][bands]
                if d["refused"] or not d["start"] or not d["arm"]:
                    refused.append({"part": p, "reason": d["refused"]})
                    continue
                rows.append({"part": p, "band": band[p], "x": math.log(d["arm"] / d["start"])})
            stat = K.band_stat(rows, "x")
            entry[bands] = {"vs_start": stat, "refused": refused,
                            "ambiguous_lag_rows": [r for r in rows
                                                   if r["part"] in out["ambiguous_lags"]]}
        out["comparisons"][key] = entry
        s = entry["recording"]["vs_start"]
        pvalues[key] = s["sign_flip_p_two_sided"] if s else 1.0
    adjusted = holm(pvalues)
    for key, entry in out["comparisons"].items():
        s = entry["recording"]["vs_start"]
        entry["holm_p"] = adjusted[key]
        entry["beats_start"] = bool(s and s["band_median_log_ratio"] < 0 and adjusted[key] < 0.05)
    out["any_arm_beats_start"] = any(e["beats_start"] for e in out["comparisons"].values())
    summary = {k: {"band_median": e["recording"]["vs_start"]["band_median_log_ratio"]
                   if e["recording"]["vs_start"] else None,
                   "parts_better": e["recording"]["vs_start"]["parts_better"]
                   if e["recording"]["vs_start"] else None,
                   "holm_p": round(e["holm_p"], 4), "beats_start": e["beats_start"],
                   "union_band_median": e["union"]["vs_start"]["band_median_log_ratio"]
                   if e["union"]["vs_start"] else None,
                   "refused": len(e["recording"]["refused"])}
               for k, e in out["comparisons"].items()}
    print(json.dumps({"any_arm_beats_start": out["any_arm_beats_start"], "summary": summary},
                     indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
