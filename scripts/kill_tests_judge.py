#!/usr/bin/env python3
"""Kill tests K1 and K3 read again under the project's judge, `analysis/aligned.py`.

    python scripts/kill_tests_judge.py --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --k3-json k3.json --json k-judge.json

Declared in `docs/kill-test-k3-plan.md` ("Under the judge") before any K1–K3 result
on the float panel was read. K1 and K3 were declared under ALM and v3c; since then v3c
has been retired as a judge (`docs/measuring-closeness.md`). This script scores the
same choices with `aligned_distance`, under both band sets, with one lag per part:
`estimate_lag` pooled over the part's whole panel around the catalogued lag less the
latency (±15 ms), or without the hint (±50 ms) where that is refused, recorded in the
output. K2 is not re-scored: its accuracy needs no distance, and its picks are not
stored.

- **K1**: per part (DI playing in at least half of each half, as in `kill_tests.py`),
  the factory preset closest on half A, scored on half B against template+R; the
  constant is the preset with the best half-A median on the other bands' parts.
- **K3**: the recognisers' picks, shuffled picks and folds from `kill_test_k3.py`,
  scored over 1.0–10 s; the constant re-chosen under the judge on the training bands.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import guarded
import kill_tests as K

SR, LATENCY = K.SR, K.LATENCY
WINDOWS = {"A": K.HALVES["A"], "B": K.HALVES["B"], "full": (1.0, 10.0)}
BAND_SETS = ("recording", "union")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--k3-json", type=pathlib.Path, required=True,
                    help="kill_test_k3.py output (picks and shuffled picks)")
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=3)
    return ap


def part_lag(ref, renders, catalogued):
    """One lag per part: pooled over its renders, around the catalogued lag."""
    from analysis.aligned import estimate_lag

    try:
        return estimate_lag(ref, renders, hint=catalogued - LATENCY, max_lag_s=0.015), False
    except ValueError:
        return estimate_lag(ref, renders, max_lag_s=0.05), True


def score_part(job):
    """Every candidate's distance to the part's amp track, per window and band set."""
    part, files, catalogued, crops = job
    from analysis.aligned import aligned_distance

    ref = K.mono(crops / part / "reference.wav")
    di = K.mono(crops / part / "di.wav")
    renders = {c: K.mono(f) for c, f in files.items()}
    lag, fallback = part_lag(ref, list(renders.values()), catalogued)
    out = {}
    for c, x in renders.items():
        for w, (a, b) in WINDOWS.items():
            for bands in BAND_SETS:
                r = aligned_distance(ref, x, di, lag=lag, render_latency=LATENCY,
                                     start_s=a, end_s=b, bands=bands)
                out[f"{c}|{w}|{bands}"] = r.distance
    active = {h: K.active_fraction(di, *K.HALVES[h]) for h in ("A", "B")}
    print(f"{part}: lag {lag}{' (no hint)' if fallback else ''}", flush=True)
    return part, {"lag": lag, "fallback": fallback, "active": active, "d": out}


def main():
    from concurrent.futures import ProcessPoolExecutor

    args = build_parser().parse_args()
    from analysis import require

    require("the kill tests under the judge")
    from benchmark_recordings import CATALOG

    panel = args.panel_dir.expanduser()
    crops = args.crops_dir.expanduser()
    index = json.loads((panel / "index.json").read_text())
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    meta = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            meta[slug] = {"band": s.get("group") or f"{s['source']}/{s['song']}",
                          "lag": int(round((p.get("lag_ms") or 0) * SR / 1000))}
    files = {}
    for row in index["rows"]:
        if "file" in row:
            files.setdefault(row["part"], {})[row["candidate"]] = pathlib.Path(row["file"])
    factory = sorted({c for d in files.values() for c in d if c.startswith("factory:")})
    parts = sorted(files)
    k3 = json.loads(args.k3_json.expanduser().read_text())

    with ProcessPoolExecutor(args.workers) as ex:
        scored = dict(ex.map(score_part, [(p, files[p], meta[p]["lag"], crops) for p in parts]))

    def dist(part, cand, window, bands):
        return scored[part]["d"].get(f"{cand}|{window}|{bands}")

    out = {"panel": str(panel), "k3_json": str(args.k3_json),
           "lags": {p: {k: v for k, v in s.items() if k in ("lag", "fallback")}
                    for p, s in scored.items()},
           "k1": {}, "k3": {}}

    # K1, as kill_tests.py, under the judge.
    k1_parts = [p for p in parts if all(v >= 0.5 for v in scored[p]["active"].values())]
    for bands in BAND_SETS:
        rows = []
        for part in k1_parts:
            band = meta[part]["band"]
            base = dist(part, "template+R", "B", bands)
            on_a = {c: dist(part, c, "A", bands) for c in factory}
            on_a = {c: v for c, v in on_a.items() if v is not None}
            if base is None or not on_a:
                continue
            oracle = min(on_a, key=on_a.get)
            others = [p for p in k1_parts if meta[p]["band"] != band]
            med = {c: statistics.median([dist(p, c, "A", bands) for p in others
                                         if dist(p, c, "A", bands) is not None] or [1e9])
                   for c in factory}
            const = min(med, key=med.get)
            row = {"part": part, "band": band, "oracle_preset": oracle, "constant_preset": const}
            for name, cand in (("oracle", oracle), ("constant", const), ("template", "template")):
                v = dist(part, cand, "B", bands)
                row[name] = None if v is None else math.log(v / base)
            rows.append(row)
        oracle_stat = K.band_stat(rows, "oracle")
        out["k1"][bands] = {
            "oracle_vs_templateR": oracle_stat,
            "constant_vs_templateR": K.band_stat(rows, "constant"),
            "template_as_shipped_vs_templateR": K.band_stat(rows, "template"),
            "pass": oracle_stat is not None
            and oracle_stat["band_median_log_ratio"] <= math.log(0.75),
            "rows": rows}

    # K3, as kill_test_k3.py, under the judge.
    bands_sorted = sorted({meta[p]["band"] for p in parts})
    rng = random.Random(K.FOLD_SEED)
    rng.shuffle(bands_sorted)
    fold_of = {b: i % 4 for i, b in enumerate(bands_sorted)}
    picks, shuffled = k3["picks"], k3["shuffled_picks"]
    eligible = sorted({p for name in picks for p in picks[name]})
    for bands in BAND_SETS:
        constants = {}
        for f_ in range(4):
            train = [p for p in eligible if fold_of[meta[p]["band"]] != f_]
            med = {c: statistics.median([dist(p, c, "full", bands) for p in train
                                         if dist(p, c, "full", bands) is not None] or [1e9])
                   for c in factory}
            best = min(med, key=med.get)
            for p in eligible:
                if fold_of[meta[p]["band"]] == f_:
                    constants[p] = best
        res = {}
        for name in picks:
            rows = []
            for p, cand in picks[name].items():
                base = dist(p, "template+R", "full", bands)
                d = dist(p, cand, "full", bands)
                dc = dist(p, constants[p], "full", bands)
                dss = [dist(p, c, "full", bands) for c in shuffled[name][p]]
                dss = [v for v in dss if v is not None]
                if None in (base, d, dc) or not dss or base <= 0:
                    continue
                shuffled_log = statistics.mean(math.log(v / base) for v in dss)
                rows.append({"part": p, "band": meta[p]["band"], "pick": cand,
                             "model": math.log(d / base), "shuffled": shuffled_log,
                             "constant": math.log(dc / base),
                             "model_vs_shuffled": math.log(d / base) - shuffled_log,
                             "model_vs_constant": math.log(d / dc)})
            s = K.band_stat(rows, "model")
            better_shuffled = sum(1.0 if r["model_vs_shuffled"] < 0 else
                                  0.5 if r["model_vs_shuffled"] == 0 else 0.0 for r in rows)
            better_constant = sum(1.0 if r["model_vs_constant"] < 0 else
                                  0.5 if r["model_vs_constant"] == 0 else 0.0 for r in rows)
            res[name] = {
                "model_vs_templateR": s,
                "shuffled_vs_templateR": K.band_stat(rows, "shuffled"),
                "constant_vs_templateR": K.band_stat(rows, "constant"),
                "model_better_than_shuffled": better_shuffled,
                "model_better_than_constant": better_constant,
                "parts": len(rows),
                "pass": (s is not None and s["band_median_log_ratio"] <= math.log(0.9)
                         and s["parts_better"] > s["parts"] / 2
                         and better_shuffled > len(rows) / 2
                         and better_constant > len(rows) / 2),
                "rows": rows}
        out["k3"][bands] = res

    summary = {"k1": {b: {k: v for k, v in r.items() if k != "rows"}
                      for b, r in out["k1"].items()},
               "k3": {b: {n: {k: v for k, v in r.items() if k != "rows"} for n, r in res.items()}
                      for b, res in out["k3"].items()},
               "lag_fallbacks": [p for p, s in out["lags"].items() if s["fallback"]]}
    print(json.dumps(summary, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
