#!/usr/bin/env python3
"""Kill test K3: preset recognition trained on renders, applied to real amp tracks.

    python scripts/kill_test_k3.py --panel-dir ~/ndsp-presets/runs/kill/sw50r --json k3.json

Declared in `docs/kill-test-k3-plan.md` before it was computed. The recognisers,
features and folds are K2's (`kill_tests.py`): trained on the panel renders of the
training bands, they pick a preset from each held-out part's real amp-track crop.
That preset's render through the part's own DI is scored against the amp track,
against template+R, under ALM and v3c over 1.0–10 s, level left out. Comparators:
the K1 constant chosen on the training bands, a shuffled control (the recogniser
given another held-out part's amp track) and, where K1 scored the part, the split-
half oracle's pick.
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


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--k1-json", type=pathlib.Path,
                    help="kill_tests.py output, for the split-half oracle's picks")
    ap.add_argument("--json", type=pathlib.Path)
    return ap


def features(x, di, offset):
    """K2's features of audio `x` (from 1.0 s), frames where the DI plays.

    `offset`: x[t] corresponds to DI[t - offset] (52 for a render, the lag for an
    amp track)."""
    import numpy as np

    xs = x[SR:]
    norm = K.loudness_normalise(xs)
    M = K.logmel(norm if norm is not None else xs, 2048)
    d = K.frame_rms_db(di[max(SR - offset, 0):], 2048, 512)[:len(M)]
    act = d >= K.frame_rms_db(di, 2048, 512).max() - 40
    if act.sum() < 20:
        return None
    M = M[: len(act)][act]
    return np.concatenate([M.mean(0) - M.mean(), M.std(0)])


def main():
    import numpy as np

    args = build_parser().parse_args()
    from analysis import require

    require("kill test K3")
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
    bands = sorted({meta[p]["band"] for p in parts})
    rng = random.Random(K.FOLD_SEED)
    rng.shuffle(bands)
    fold_of = {b: i % 4 for i, b in enumerate(bands)}
    v3c = K._v3c_compare()

    dis = {p: K.mono(crops / p / "di.wav") for p in parts}
    refs = {p: K.mono(crops / p / "reference.wav") for p in parts}
    eligible = [p for p in parts if K.active_fraction(dis[p], 1.0, 10.0) >= 0.5]

    # Training features: K2's, from the factory-preset renders.
    X, y, owner = [], [], []
    for p in parts:
        for c in factory:
            f = features(K.mono(files[p][c]), dis[p], LATENCY)
            if f is not None:
                X.append(f); y.append(factory.index(c)); owner.append(p)
    X, y = np.array(X), np.array(y)
    fold = np.array([fold_of[meta[p]["band"]] for p in owner])

    # Full-window distances, cached.
    cache = {}

    def distance(part, cand, metric):
        key = (part, cand, metric)
        if key not in cache:
            x = K.mono(files[part][cand])
            shift = meta[part]["lag"] - LATENCY
            if metric == "alm":
                cache[key] = K.alm(refs[part], x, dis[part], shift, 1.0, 10.0)
            else:
                ref_fp = cache.setdefault((part, "ref_fp"), K.fp(refs[part][SR:], "isolated_stem"))
                seg = x[max(SR - shift, 0): max(10 * SR - shift, 0)]
                cache[key] = v3c(ref_fp, K.fp(seg, "probe"))
        return cache[key]

    picks = {name: {} for name in ("1nn", "lda", "lda+1nn")}
    shuffled = {name: {} for name in picks}
    constants = {}
    for f_ in range(4):
        tr = fold != f_
        test_parts = [p for p in eligible if fold_of[meta[p]["band"]] == f_]
        if not test_parts:
            continue
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        Xtr = (X[tr] - mu) / sd
        cls = np.unique(y[tr])
        W, means = None, {}
        # LDA, as in K2
        Sw = np.zeros((Xtr.shape[1],) * 2)
        for c in cls:
            Z = Xtr[y[tr] == c]; means[c] = Z.mean(0); Sw += (Z - means[c]).T @ (Z - means[c])
        Sw /= len(Xtr)
        Sw = 0.9 * Sw + 0.1 * np.trace(Sw) / len(Sw) * np.eye(len(Sw))
        gm = Xtr.mean(0)
        Sb = sum((y[tr] == c).sum() * np.outer(means[c] - gm, means[c] - gm) for c in cls) / len(Xtr)
        w, V = np.linalg.eig(np.linalg.solve(Sw, Sb))
        W = V[:, np.argsort(-w.real)[: len(cls) - 1]].real
        Ptr = Xtr @ W
        cm = np.stack([means[c] @ W for c in cls])
        qf = {}
        for p in test_parts:
            f = features(refs[p], dis[p], meta[p]["lag"])
            if f is not None:
                qf[p] = (f - mu) / sd
        order = [p for p in test_parts if p in qf]
        for i, p in enumerate(order):
            q = qf[p]
            other = qf[order[(i + 1) % len(order)]] if len(order) > 1 else q
            for target, store in ((q, picks), (other, shuffled)):
                d1 = ((Xtr - target) ** 2).sum(1)
                store["1nn"][p] = factory[int(y[tr][np.argmin(d1)])]
                pt = target @ W
                store["lda"][p] = factory[int(cls[np.argmin(((cm - pt) ** 2).sum(1))])]
                store["lda+1nn"][p] = factory[int(y[tr][np.argmin(((Ptr - pt) ** 2).sum(1))])]
        train_parts = [p for p in eligible if fold_of[meta[p]["band"]] != f_]
        med = {c: statistics.median([distance(p, c, "alm") for p in train_parts
                                     if distance(p, c, "alm") is not None] or [1e9])
               for c in factory}
        best = min(med, key=med.get)
        for p in order:
            constants[p] = best
        print(f"fold {f_}: {len(order)} parts", flush=True)

    oracle = {}
    if args.k1_json and args.k1_json.expanduser().exists():
        k1 = json.loads(args.k1_json.expanduser().read_text())
        for r in k1.get("k1_rows", {}).get("alm", []):
            if isinstance(r.get("oracle_preset"), str):
                oracle[r["part"]] = r["oracle_preset"]

    out = {"panel": str(panel), "eligible_parts": len(eligible), "picks": picks,
           "shuffled_picks": shuffled, "constants": constants, "results": {}}
    for metric in ("alm", "v3c"):
        res = {}
        for name in picks:
            rows = []
            for p, cand in picks[name].items():
                base = distance(p, "template+R", metric)
                d = distance(p, cand, metric)
                ds = distance(p, shuffled[name][p], metric)
                dc = distance(p, constants[p], metric)
                if None in (base, d, ds, dc):
                    continue
                row = {"part": p, "band": meta[p]["band"], "pick": cand,
                       "model": math.log(d / base), "shuffled": math.log(ds / base),
                       "constant": math.log(dc / base), "model_vs_shuffled": math.log(d / ds)}
                if p in oracle and distance(p, oracle[p], metric) is not None:
                    row["oracle"] = math.log(distance(p, oracle[p], metric) / base)
                rows.append(row)
            res[name] = {
                "model_vs_templateR": K.band_stat(rows, "model"),
                "shuffled_vs_templateR": K.band_stat(rows, "shuffled"),
                "constant_vs_templateR": K.band_stat(rows, "constant"),
                "oracle_vs_templateR": K.band_stat(rows, "oracle"),
                "model_better_than_shuffled": sum(r["model_vs_shuffled"] < 0 for r in rows),
                "parts": len(rows), "rows": rows}
        out["results"][metric] = res
    passed = []
    for name in picks:
        ok = True
        for metric in ("alm", "v3c"):
            r = out["results"][metric][name]
            s = r["model_vs_templateR"]
            ok &= (s is not None and s["band_median_log_ratio"] <= math.log(0.9)
                   and s["parts_better"] > s["parts"] / 2
                   and r["model_better_than_shuffled"] > r["parts"] / 2)
        if ok:
            passed.append(name)
    out["k3_pass"] = bool(passed)
    out["passing_recognisers"] = passed
    print(json.dumps({"k3_pass": out["k3_pass"], "passing": passed,
                      "summary": {m: {n: {k: v for k, v in r.items() if k != "rows"}
                                      for n, r in res.items()}
                                  for m, res in out["results"].items()}}, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
