#!/usr/bin/env python3
"""The supervised plan's kill tests K1 and K2 on a rendered preset panel.

    python scripts/kill_tests.py --panel-dir ~/ndsp-presets/runs/kill/sw50r --json k.json

`docs/supervised-model-plan.md` §0 defines both; this script implements them on the
renders of `render_preset_panel.py` (every factory preset of one amp, with the
rule set R, and the template with R, through each set-2 development part's DI).

Distances, level left out:
  v3c  `unpaired-v3` restricted to timbre (with `band_shape` over the reference's
       bands within 30 dB of its peak) and dynamics without the decay term, the
       audit's corrections (D-H3, D-M10, D-M11); weights 1.0 and 0.4 as in v3
  ALM  an aligned log-mel distance: render and reference loudness-normalised and
       aligned by the part's catalogued lag less the plugin's 52-sample latency;
       64 mel bands 50 Hz–10 kHz at three resolutions (1024/2048/4096-point
       frames); frames where the DI plays (within 40 dB of its loudest frame);
       bins within 30 dB of the reference's long-term peak; mean |ΔdB|

K1 (headroom): per part, the factory preset closest on half A (1.0–5.5 s) scored
on half B (5.5–10 s) against the template with R; and the best constant preset,
chosen leave-one-band-out on half A of the other bands' parts. Statistic: the
median across bands of each band's median log ratio. Stop unless the oracle's is
≤ log 0.75 under both distances.

Parts whose DI plays in under half the frames of either half are left out of K1
(written into this docstring before any result was read, 2026-10-03: 13 of 43
set-2 crops are mostly silent, audit D-M6, and a split-half oracle on a silent
half measures nothing). They are listed in the output.

K2 (identifiability across players): features of each factory-preset render —
long-term log-mel mean and spread over the frames where the DI plays, 128
values — labelled by preset; 4 folds of bands (seeded); 1-NN, LDA and LDA+1-NN
trained on the training bands' renders predict the preset of a held-out band's
render. Top-1/top-5 accuracy against chance, and the regret: ALM and v3c between
the predicted preset's render and the true preset's render through the same DI,
against the same for the K1 constant (chosen on the training bands). Stop unless a
row reaches ≥3× chance top-1 accuracy and ≤0.75× the constant's median ALM regret.
"""

from __future__ import annotations

import argparse
import itertools
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

SR = 48000
LATENCY = 52
HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}
FOLD_SEED = 20261003


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path)
    return ap


# --- signals -----------------------------------------------------------------

def mono(path):
    import numpy as np
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float64")
    assert sr == SR, path
    return x.mean(axis=1) if x.ndim == 2 else x


def frame_rms_db(x, n, hop):
    import numpy as np

    frames = max(1, 1 + (len(x) - n) // hop)
    idx = np.arange(n)[None, :] + hop * np.arange(frames)[:, None]
    idx = np.minimum(idx, len(x) - 1)
    return 10 * np.log10(np.mean(x[idx] ** 2, axis=1) + 1e-20)


def active_fraction(di, start_s, end_s, floor_db=40.0):
    import numpy as np

    db = frame_rms_db(di, 2048, 1024)
    peak = db.max()
    lo, hi = int(start_s * SR / 1024), int(end_s * SR / 1024)
    return float(np.mean(db[lo:hi] >= peak - floor_db))


def _mel_matrix(n_fft, bands=64, fmin=50.0, fmax=10000.0):
    import numpy as np

    def hz_to_mel(f):
        return 2595 * np.log10(1 + f / 700)

    def mel_to_hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    freqs = np.fft.rfftfreq(n_fft, 1 / SR)
    edges = mel_to_hz(np.linspace(hz_to_mel(fmin), hz_to_mel(fmax), bands + 2))
    m = np.zeros((bands, len(freqs)))
    for b in range(bands):
        lo, c, hi = edges[b], edges[b + 1], edges[b + 2]
        up = (freqs - lo) / max(c - lo, 1e-9)
        down = (hi - freqs) / max(hi - c, 1e-9)
        m[b] = np.clip(np.minimum(up, down), 0, None)
    return m


_MELS = {}


def logmel(x, n_fft):
    import numpy as np

    if n_fft not in _MELS:
        _MELS[n_fft] = _mel_matrix(n_fft)
    hop = n_fft // 4
    frames = max(1, 1 + (len(x) - n_fft) // hop)
    idx = np.arange(n_fft)[None, :] + hop * np.arange(frames)[:, None]
    idx = np.minimum(idx, len(x) - 1)
    spec = np.abs(np.fft.rfft(x[idx] * np.hanning(n_fft), axis=1)) ** 2
    return 10 * np.log10(spec @ _MELS[n_fft].T + 1e-12)          # frames × bands


def loudness_normalise(x):
    from analysis import io

    lufs = io.loudness_lufs(io.from_samples(x, SR))
    if lufs is None:
        return None
    return x * 10 ** ((-23.0 - lufs) / 20)


def alm(reference, render, di, shift, start_s, end_s):
    """Aligned log-mel distance over [start_s, end_s) of the reference's timeline.

    A DI sample at time u reaches the render at u + 52 (the plugin's latency) and
    the reference at u + lag, so reference[t] corresponds to render[t - shift] with
    shift = lag - 52, and to DI[t - shift - 52]. Between two renders through one DI,
    shift is 0.
    """
    import numpy as np

    a, b = int(start_s * SR), int(end_s * SR)
    ref = reference[a:b]
    lo = a - shift
    ren = render[max(lo, 0): max(lo, 0) + len(ref)]
    if lo < 0 or len(ren) < len(ref):
        ref = ref[: len(ren)]
    dsh = shift + LATENCY                       # reference[t] <-> DI[t - dsh]
    dseg = di[max(a - dsh, 0): max(a - dsh, 0) + len(ref)]
    ref, ren = loudness_normalise(ref), loudness_normalise(ren)
    if ref is None or ren is None:
        return None
    total = []
    for n in (1024, 2048, 4096):
        R, X = logmel(ref, n), logmel(ren, n)
        k = min(len(R), len(X))
        R, X = R[:k], X[:k]
        d = frame_rms_db(np.pad(dseg, (0, max(0, len(ref) - len(dseg)))), n, n // 4)[:k]
        frames = d >= frame_rms_db(di, n, n // 4).max() - 40
        if frames.sum() < 4:
            return None
        ltas = 10 * np.log10(np.mean(10 ** (R[frames] / 10), axis=0))
        bins = ltas >= ltas.max() - 30
        total.append(float(np.mean(np.abs(R[frames][:, bins] - X[frames][:, bins]))))
    return float(np.mean(total))


# --- v3c -----------------------------------------------------------------------

def _v3c_compare():
    from analysis import compare as C

    original_timbre, original_dynamics = C._timbre, C._dynamics

    def timbre(target, candidate, scales):
        centres = target.spectrum.get("band_centres_hz") or []
        levels = target.spectrum.get("band_db") or []
        keep = [i for i, v in enumerate(levels) if v >= max(levels) - 30] if levels else []
        proxy = type("Restricted", (), {})()
        proxy.__dict__.update(target.__dict__)
        proxy.spectrum = {**target.spectrum, "band_centres_hz": [centres[i] for i in keep],
                          "band_db": [levels[i] for i in keep]}
        return original_timbre(proxy, candidate, scales)

    def dynamics(target, candidate, scales):
        terms = original_dynamics(target, candidate, scales)
        terms.pop("decay", None)
        return terms

    def v3c(reference_fp, render_fp):
        from analysis.compare import Objectives, compare, scalar

        C._timbre, C._dynamics = timbre, dynamics
        try:
            o = compare(reference_fp, render_fp, profile="unpaired-v3")
        finally:
            C._timbre, C._dynamics = original_timbre, original_dynamics
        values = {k: o.values.get(k) for k in ("timbre", "dynamics")}
        if any(v is None for v in values.values()):
            return None
        return scalar(Objectives(values=values, profile="unpaired-v3"))

    return v3c


def fp(x, regime):
    from analysis import io
    from analysis.fingerprint import fingerprint

    return fingerprint(io.from_samples(x, SR), regime=regime, excerpt_s=None)


# --- statistics ----------------------------------------------------------------

def band_stat(rows, key):
    by = {}
    for r in rows:
        if r.get(key) is not None:
            by.setdefault(r["band"], []).append(r[key])
    medians = {b: statistics.median(v) for b, v in by.items()}
    vals = list(medians.values())
    if not vals:
        return None
    obs = abs(sum(vals))
    hits = sum(abs(sum(s * v for s, v in zip(signs, vals))) >= obs - 1e-12
               for signs in itertools.product((1, -1), repeat=len(vals)))
    stat = statistics.median(vals)
    return {"band_median_log_ratio": round(stat, 4), "gain": round(1 - math.exp(stat), 4),
            "bands": len(vals), "bands_better": sum(v < 0 for v in vals),
            "parts_better": sum(1 for r in rows if r.get(key) is not None and r[key] < 0),
            "parts": sum(1 for r in rows if r.get(key) is not None),
            "sign_flip_p_two_sided": round(hits / 2 ** len(vals), 4)}


# --- main --------------------------------------------------------------------

def main():
    import numpy as np

    args = build_parser().parse_args()
    from analysis import require

    require("the kill tests")
    from benchmark_recordings import CATALOG

    panel = args.panel_dir.expanduser()
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
    crops = args.crops_dir.expanduser()
    v3c = _v3c_compare()

    # Distances of every candidate to each part's reference, per half.
    D = {}            # (part, candidate, half, metric) -> distance
    excluded, renders = [], {}
    for part, cands in sorted(files.items()):
        ref = mono(crops / part / "reference.wav")
        di = mono(crops / part / "di.wav")
        shift = meta[part]["lag"] - LATENCY
        act = {h: active_fraction(di, *span) for h, span in HALVES.items()}
        use_k1 = all(v >= 0.5 for v in act.values())
        if not use_k1:
            excluded.append({"part": part, "active_fraction": act})
        ref_fps = {h: fp(ref[int(a * SR):int(b * SR)], "isolated_stem") for h, (a, b) in HALVES.items()}
        for cand, path in cands.items():
            x = mono(path)
            renders[(part, cand)] = x
            if not use_k1:
                continue
            for h, (a, b) in HALVES.items():
                D[(part, cand, h, "alm")] = alm(ref, x, di, shift, a, b)
                seg = x[max(int(a * SR) - shift, 0): max(int(b * SR) - shift, 0)]
                D[(part, cand, h, "v3c")] = v3c(ref_fps[h], fp(seg, "probe"))
        print(f"{part}: {'K1' if use_k1 else 'K2 only'}", flush=True)

    k1_parts = sorted({k[0] for k in D})
    out = {"panel": str(panel), "amp": index.get("amp"), "factory_presets": len(factory),
           "k1_parts": len(k1_parts), "k1_excluded": excluded}

    # K1
    k1 = {}
    for metric in ("alm", "v3c"):
        rows = []
        for part in k1_parts:
            band = meta[part]["band"]
            base = D.get((part, "template+R", "B", metric))
            scored = {c: D.get((part, c, "A", metric)) for c in factory}
            scored = {c: v for c, v in scored.items() if v is not None}
            if base is None or not scored:
                continue
            oracle = min(scored, key=scored.get)
            others = [p for p in k1_parts if meta[p]["band"] != band]
            med = {c: statistics.median([D[(p, c, "A", metric)] for p in others
                                         if D.get((p, c, "A", metric)) is not None])
                   for c in factory}
            const = min(med, key=med.get)
            row = {"part": part, "band": band, "oracle_preset": oracle,
                   "constant_preset": const}
            for name, cand in (("oracle", oracle), ("constant", const), ("template", "template")):
                v = D.get((part, cand, "B", metric))
                row[name] = None if v is None else math.log(v / base)
            rows.append(row)
        k1[metric] = {"oracle_vs_templateR": band_stat(rows, "oracle"),
                      "constant_vs_templateR": band_stat(rows, "constant"),
                      "template_as_shipped_vs_templateR": band_stat(rows, "template"),
                      "rows": rows}
    out["k1"] = {m: {k: v for k, v in r.items() if k != "rows"} for m, r in k1.items()}
    out["k1_pass"] = all(k1[m]["oracle_vs_templateR"] is not None and
                         k1[m]["oracle_vs_templateR"]["band_median_log_ratio"] <= math.log(0.75)
                         for m in k1)
    out["k1_rows"] = {m: r["rows"] for m, r in k1.items()}

    # K2
    parts = sorted(files)
    bands = sorted({meta[p]["band"] for p in parts})
    rng = random.Random(FOLD_SEED)
    rng.shuffle(bands)
    fold_of = {b: i % 4 for i, b in enumerate(bands)}
    feats, labels, owners = [], [], []
    for (part, cand), x in renders.items():
        if not cand.startswith("factory:"):
            continue
        di = mono(crops / part / "di.wav")
        xs = x[SR:]
        M = logmel(loudness_normalise(xs) if loudness_normalise(xs) is not None else xs, 2048)
        d = frame_rms_db(di[SR - LATENCY:], 2048, 512)[:len(M)]
        act = d >= frame_rms_db(di, 2048, 512).max() - 40
        if act.sum() < 20:
            continue
        M = M[: len(act)][act]
        f = np.concatenate([M.mean(0) - M.mean(), M.std(0)])
        feats.append(f); labels.append(factory.index(cand)); owners.append(part)
    X, y = np.array(feats), np.array(labels)
    fold = np.array([fold_of[meta[p]["band"]] for p in owners])

    def lda_fit(Xtr, ytr, shrink=0.1):
        classes = np.unique(ytr)
        mu = X.mean(0) * 0 + Xtr.mean(0)
        Sw = np.zeros((Xtr.shape[1],) * 2)
        means = {}
        for c in classes:
            Z = Xtr[ytr == c]; means[c] = Z.mean(0); Sw += (Z - means[c]).T @ (Z - means[c])
        Sw /= len(Xtr)
        Sw = (1 - shrink) * Sw + shrink * np.trace(Sw) / len(Sw) * np.eye(len(Sw))
        Sb = sum((ytr == c).sum() * np.outer(means[c] - mu, means[c] - mu) for c in classes) / len(Xtr)
        w, V = np.linalg.eig(np.linalg.solve(Sw, Sb))
        order = np.argsort(-w.real)[: len(classes) - 1]
        return V[:, order].real, means

    k2 = {"chance_top1": round(1 / len(factory), 4), "rows": {}}
    preds = {name: np.zeros(len(y), dtype=int) for name in ("1nn", "lda", "lda+1nn")}
    ranks = {name: np.zeros(len(y), dtype=int) for name in preds}
    consts = np.zeros(len(y), dtype=int)
    for f_ in range(4):
        tr, te = fold != f_, fold == f_
        if te.sum() == 0:
            continue
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        Xtr, Xte = (X[tr] - mu) / sd, (X[te] - mu) / sd
        dist = ((Xte[:, None] - Xtr[None]) ** 2).sum(-1)
        # 1-NN: class order by each class's nearest training render
        cls = np.unique(y[tr])
        best = np.stack([dist[:, y[tr] == c].min(1) for c in cls], 1)
        order = cls[np.argsort(best, 1)]
        preds["1nn"][te], ranks["1nn"][te] = order[:, 0], [list(o).index(t) for o, t in zip(order, y[te])]
        W, means = lda_fit(Xtr, y[tr])
        Ptr, Pte = Xtr @ W, Xte @ W
        cm = np.stack([means[c] @ W for c in cls])
        dm = ((Pte[:, None] - cm[None]) ** 2).sum(-1)
        order = cls[np.argsort(dm, 1)]
        preds["lda"][te], ranks["lda"][te] = order[:, 0], [list(o).index(t) for o, t in zip(order, y[te])]
        dl = ((Pte[:, None] - Ptr[None]) ** 2).sum(-1)
        best = np.stack([dl[:, y[tr] == c].min(1) for c in cls], 1)
        order = cls[np.argsort(best, 1)]
        preds["lda+1nn"][te], ranks["lda+1nn"][te] = order[:, 0], [list(o).index(t) for o, t in zip(order, y[te])]
        # the K1 constant chosen on the training bands (ALM, half A)
        train_parts = [p for p in k1_parts if fold_of[meta[p]["band"]] != f_]
        med = {c: statistics.median([D[(p, c, "A", "alm")] for p in train_parts
                                     if D.get((p, c, "A", "alm")) is not None] or [1e9])
               for c in factory}
        consts[te] = factory.index(min(med, key=med.get))

    def regret(i, q):
        part, true = owners[i], factory[y[i]]
        a, b = renders[(part, factory[q])], renders[(part, true)]
        di = mono(crops / part / "di.wav")
        return alm(b, a, di, 0, 1.0, 10.0) if q != y[i] else 0.0

    const_reg = [regret(i, consts[i]) for i in range(len(y))]
    for name in preds:
        reg = [regret(i, preds[name][i]) for i in range(len(y))]
        pairs = [(r, c) for r, c in zip(reg, const_reg) if r is not None and c is not None]
        k2["rows"][name] = {
            "top1": round(float(np.mean(ranks[name] == 0)), 4),
            "top5": round(float(np.mean(ranks[name] < 5)), 4),
            "median_alm_regret": round(statistics.median([r for r, _ in pairs]), 4),
            "constant_median_alm_regret": round(statistics.median([c for _, c in pairs]), 4)}
        row = k2["rows"][name]
        row["regret_ratio"] = round(row["median_alm_regret"] / row["constant_median_alm_regret"], 4)
        row["pass"] = row["top1"] >= 3 * k2["chance_top1"] and row["regret_ratio"] <= 0.75
    k2["renders"] = int(len(y)); k2["folds"] = {b: fold_of[b] for b in bands}
    out["k2"] = k2
    out["k2_pass"] = any(r["pass"] for r in k2["rows"].values())
    print(json.dumps({k: v for k, v in out.items() if k != "k1_rows"}, indent=1))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
