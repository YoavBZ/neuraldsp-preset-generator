#!/usr/bin/env python3
"""Kill tests K1 and K3 read again under the project's judge, `analysis/aligned.py`.

    python research/kill_tests_judge.py --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --freeze-lags docs/kill-tests-judge-lags.json            # once, before results
    python research/kill_tests_judge.py --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --lags docs/kill-tests-judge-lags.json --k-json k.json --k3-json k3.json \\
        --json k-judge.json

Declared in `docs/kill-test-k3-plan.md` ("Under the judge") before any K1–K3 result
on the float panel was read. K1 and K3 were declared under ALM and v3c; since then v3c
has been retired as a judge (`docs/measuring-closeness.md`). This script scores the
same choices with `aligned_distance`, under both band sets, with one lag per part,
frozen before any result was read (`estimate_lag` pooled over the part's whole panel
around the catalogued lag less the latency, ±15 ms, or ±50 ms around it where that is
refused). It also emits the declared verdict, which needs ALM's from the K1–K3 outputs.
K2 is not re-scored: its rule never used v3c, so it stands as declared under ALM.

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
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

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
    ap.add_argument("--k3-json", type=pathlib.Path,
                    help="kill_test_k3.py output (picks, shuffled picks, ALM results)")
    ap.add_argument("--k-json", type=pathlib.Path,
                    help="kill_tests.py output (K1 under ALM, and its verdicts)")
    ap.add_argument("--lags", type=pathlib.Path, help="frozen lag table (--freeze-lags)")
    ap.add_argument("--freeze-lags", type=pathlib.Path,
                    help="estimate one lag per part used by K1 or K3, write them here, stop")
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=3)
    return ap


def estimate_part_lag(job):
    """One lag per part, pooled over its whole panel, around the catalogued lag; ±50 ms
    around it where ±15 ms is refused; None (with the reason) where both are."""
    part, files, catalogued, crops = job
    from analysis.aligned import estimate_lag

    ref = K.mono(crops / part / "reference.wav")
    renders = [K.mono(f) for f in files.values()]
    hint = catalogued - LATENCY
    for width in (0.015, 0.05):
        try:
            return part, {"lag": estimate_lag(ref, renders, hint=hint, max_lag_s=width),
                          "window_ms": width * 1000}
        except ValueError as error:
            reason = str(error)
    return part, {"lag": None, "reason": reason}


def score_part(job):
    """Every candidate's distance to the part's amp track, per window and band set, and
    any refusal's reason."""
    part, files, lag, crops = job
    from analysis.aligned import aligned_distance

    ref = K.mono(crops / part / "reference.wav")
    di = K.mono(crops / part / "di.wav")
    out, refused = {}, {}
    for c, f in files.items():
        x = K.mono(f)
        for w, (a, b) in WINDOWS.items():
            for bands in BAND_SETS:
                r = aligned_distance(ref, x, di, lag=lag, render_latency=LATENCY,
                                     start_s=a, end_s=b, bands=bands)
                out[f"{c}|{w}|{bands}"] = r.distance
                if r.distance is None:
                    refused[f"{c}|{w}|{bands}"] = r.reason
    print(f"{part}: scored at lag {lag}", flush=True)
    return part, {"d": out, "refused": refused}


def unrounded_band_median(rows, key):
    by = {}
    for r in rows:
        if r.get(key) is not None:
            by.setdefault(r["band"], []).append(r[key])
    vals = [statistics.median(v) for v in by.values()]
    return statistics.median(vals) if vals else None


def k3_alm_pass(r):
    """The declared K3 rule for one recogniser under ALM, from kill_test_k3.py's output
    (its band median recomputed unrounded from the rows)."""
    s = r.get("model_vs_templateR")
    median = unrounded_band_median(r.get("rows", []), "model")
    return bool(s is not None and median is not None and median <= math.log(0.9)
                and s["parts_better"] > s["parts"] / 2
                and r["model_better_than_shuffled"] > r["parts"] / 2
                and r["model_better_than_constant"] > r["parts"] / 2)


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
    dis = {p: K.mono(crops / p / "di.wav") for p in parts}
    # Eligibility as declared: K1 needs the DI in at least half of each half, K3 in at
    # least half of 1.0-10 s.
    k1_parts = [p for p in parts
                if all(K.active_fraction(dis[p], *K.HALVES[h]) >= 0.5 for h in ("A", "B"))]
    k3_parts = [p for p in parts if K.active_fraction(dis[p], 1.0, 10.0) >= 0.5]
    used = sorted(set(k1_parts) | set(k3_parts))

    if args.freeze_lags:
        with ProcessPoolExecutor(args.workers) as ex:
            lags = dict(ex.map(estimate_part_lag,
                               [(p, files[p], meta[p]["lag"], crops) for p in used]))
        table = {"panel": str(args.panel_dir), "lags": lags}
        args.freeze_lags.expanduser().write_text(json.dumps(table, indent=1) + "\n")
        print(json.dumps(lags, indent=1))
        return
    if not (args.lags and args.k3_json and args.k_json):
        raise SystemExit("--lags, --k-json and --k3-json are needed to score")
    frozen = json.loads(args.lags.expanduser().read_text())
    lags = frozen["lags"]
    k3 = json.loads(args.k3_json.expanduser().read_text())
    kj = json.loads(args.k_json.expanduser().read_text())
    for source, name in ((frozen, "lag table"), (k3, "K3 output"), (kj, "K1-K2 output")):
        if pathlib.Path(source["panel"]).expanduser().resolve() != panel.resolve():
            raise SystemExit(f"the {name} is for another panel: {source['panel']}")
    # The panel was re-rendered in place: outputs older than its index are from the
    # earlier render and must not be scored against it.
    rendered = (panel / "index.json").stat().st_mtime
    for path, name in ((args.k_json, "K1-K2 output"), (args.k3_json, "K3 output")):
        if path.expanduser().stat().st_mtime < rendered:
            raise SystemExit(f"the {name} {path} is older than the panel's index.json")
    for name, chosen in k3["picks"].items():
        if set(chosen) - set(k3_parts):
            raise SystemExit(f"K3's {name} picks cover parts outside the declared eligibility")
    without_pick = sorted(set(k3_parts) - {p for c in k3["picks"].values() for p in c})
    if k3.get("eligible_parts") not in (None, len(k3_parts)):
        raise SystemExit("K3's eligible part count differs from the declared eligibility")
    if sorted(e["part"] for e in kj.get("k1_excluded", [])) != sorted(
            p for p in parts if p not in k1_parts):
        raise SystemExit("K1's excluded parts differ from the declared eligibility")
    skipped = {p: s["reason"] for p, s in lags.items() if s["lag"] is None}
    alternates = frozen.get("alternate", {})
    with ProcessPoolExecutor(args.workers) as ex:
        scored = dict(ex.map(score_part, [(p, files[p], lags[p]["lag"], crops)
                                          for p in used if p not in skipped]))
        scored_alt = dict(ex.map(score_part, [(p, files[p], lag, crops)
                                              for p, lag in alternates.items()
                                              if not p.startswith("_")]))

    def dist(part, cand, window, bands):
        return scored[part]["d"].get(f"{cand}|{window}|{bands}") if part in scored else None

    out = {"panel": str(panel), "k_json": str(args.k_json), "k3_json": str(args.k3_json),
           "lags": lags, "parts_without_lag": skipped,
           "k1_parts": k1_parts, "k1_excluded": [p for p in parts if p not in k1_parts],
           "k3_parts": k3_parts, "k3_parts_without_pick": without_pick,
           "refused": {p: s["refused"] for p, s in scored.items() if s["refused"]},
           "k1": {}, "k3": {}}

    # K1, as kill_tests.py, under the judge.
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
        median = unrounded_band_median(rows, "oracle")
        out["k1"][bands] = {
            "oracle_vs_templateR": K.band_stat(rows, "oracle"),
            "constant_vs_templateR": K.band_stat(rows, "constant"),
            "template_as_shipped_vs_templateR": K.band_stat(rows, "template"),
            "pass": median is not None and median <= math.log(0.75),
            "rows": rows}

    # K3, as kill_test_k3.py, under the judge.
    bands_sorted = sorted({meta[p]["band"] for p in parts})
    rng = random.Random(K.FOLD_SEED)
    rng.shuffle(bands_sorted)
    fold_of = {b: i % 4 for i, b in enumerate(bands_sorted)}
    picks, shuffled = k3["picks"], k3["shuffled_picks"]
    eligible = k3_parts
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
            median = unrounded_band_median(rows, "model")
            # Is it recognition, or one good preset for everything? The share of the
            # most common pick, and the picks moved one band along (each part gets the
            # pick made for a part of the next band in alphabetical order).
            counts = statistics.multimode([r["pick"] for r in rows]) if rows else []
            top_share = (max(sum(r["pick"] == c for r in rows) for c in counts) / len(rows)
                         if rows else None)
            by_band = {}
            for r in rows:
                by_band.setdefault(r["band"], []).append(r)
            band_order = sorted(by_band)
            moved = []
            for i, b in enumerate(band_order):
                donor = by_band[band_order[(i + 1) % len(band_order)]]
                for j, r in enumerate(by_band[b]):
                    c = donor[j % len(donor)]["pick"]
                    d_moved = dist(r["part"], c, "full", bands)
                    base = dist(r["part"], "template+R", "full", bands)
                    if d_moved is not None and base:
                        moved.append({"band": b, "moved": math.log(d_moved / base)})
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
                "picks_moved_one_band_vs_templateR": K.band_stat(moved, "moved"),
                "distinct_picks": len({r["pick"] for r in rows}),
                "most_common_pick_share": top_share,
                "parts": len(rows),
                "pass": (median is not None and median <= math.log(0.9)
                         and s["parts_better"] > s["parts"] / 2
                         and better_shuffled > len(rows) / 2
                         and better_constant > len(rows) / 2),
                "rows": rows}
        out["k3"][bands] = res

    # The declared verdict: ALM and the judge under both band sets; for K3 the same
    # recogniser, and not one that mostly picks a single preset.
    alm_median = unrounded_band_median(kj["k1_rows"]["alm"], "oracle")
    k1_alm_pass = alm_median is not None and alm_median <= math.log(0.75)
    k3_by = {}
    for name in picks:
        alm_ok = k3_alm_pass(k3["results"]["alm"][name])
        judge_ok = all(out["k3"][b][name]["pass"] for b in BAND_SETS)
        single = any((out["k3"][b][name]["most_common_pick_share"] or 0) > 0.5
                     for b in BAND_SETS)
        k3_by[name] = {"alm": alm_ok, "judge_both_band_sets": judge_ok,
                       "mostly_one_preset": single,
                       "pass": alm_ok and judge_ok and not single}
    out["verdict"] = {
        "k1": {"alm": k1_alm_pass, **{f"judge_{b}": out["k1"][b]["pass"] for b in BAND_SETS},
               "pass": k1_alm_pass and all(out["k1"][b]["pass"] for b in BAND_SETS)},
        "k3": {"by_recogniser": k3_by, "pass": any(v["pass"] for v in k3_by.values())},
        "k2": kj.get("k2_pass"),
        "as_first_declared": {"k1_alm_and_v3c": kj.get("k1_pass"),
                              "k2": kj.get("k2_pass"),
                              "k3_alm_and_v3c": k3.get("k3_pass")}}
    out["verdict"]["gate_open"] = bool(out["verdict"]["k1"]["pass"] and out["verdict"]["k2"]
                                       and out["verdict"]["k3"]["pass"])

    # Reported, not deciding: the parts whose pooled lag depends on which renders are
    # pooled, scored again at the other lag.
    out["alternate_lags"] = {}
    for part, s_alt in scored_alt.items():
        def dist_alt(cand, window, bands):
            return s_alt["d"].get(f"{cand}|{window}|{bands}")
        rep_ = {"lag": alternates[part], "frozen_lag": lags[part]["lag"]}
        for bands in BAND_SETS:
            row = {}
            if part in k1_parts:
                on_a = {c: dist_alt(c, "A", bands) for c in factory}
                on_a = {c: v for c, v in on_a.items() if v is not None}
                base = dist_alt("template+R", "B", bands)
                if on_a and base and dist_alt(min(on_a, key=on_a.get), "B", bands):
                    oracle = min(on_a, key=on_a.get)
                    row["k1_oracle"] = {"preset": oracle,
                                        "log_ratio": math.log(dist_alt(oracle, "B", bands) / base)}
            if part in k3_parts and all(part in picks[name] for name in picks):
                base = dist_alt("template+R", "full", bands)
                row["k3_model_log_ratio"] = {
                    name: math.log(dist_alt(picks[name][part], "full", bands) / base)
                    for name in picks if base and dist_alt(picks[name][part], "full", bands)}
            rep_[bands] = row
        out["alternate_lags"][part] = rep_

    summary = {"k1": {b: {k: v for k, v in r.items() if k != "rows"}
                      for b, r in out["k1"].items()},
               "k3": {b: {n: {k: v for k, v in r.items() if k != "rows"} for n, r in res.items()}
                      for b, res in out["k3"].items()},
               "verdict": out["verdict"], "parts_without_lag": skipped,
               "refused": {p: len(v) for p, v in out["refused"].items()}}
    print(json.dumps(summary, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
