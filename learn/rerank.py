"""A DI-free reranker on K1's 25 clean PR12 parts, as declared in `docs/rerank-plan.md`.

A candidate's sound for part p is its panel renders through the DIs of development parts in
other K3 folds than p's. The recording (amp track or stem) is compared with each
candidate's mean feature on half A; the nearest candidate is the pick, scored exactly as
`learn/phase2.py` `score()` scores a pick (half B, measure DI, log ratio to template+R).

Features: (a) log-mel mean and std over loud frames; (b) PANNs CNN14 embeddings.
CPU only. Run with the rerank venv:

    PYTORCH_ENABLE_MPS_FALLBACK=0 ~/ndsp-presets/tools/rerank-venv/bin/python -m learn.rerank
"""

from __future__ import annotations

import importlib
import json
import math
import os
import pathlib
import sys
import time
import types

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import phase2 as P2  # noqa: E402

OUT = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/rerank"))
VENV = pathlib.Path(os.path.expanduser("~/ndsp-presets/tools/rerank-venv"))
CKPT = VENV / "panns" / "Cnn14_mAP=0.431.pth"
SR = P2.SR
LUFS = -22.9
GATE = math.log(0.95)
SILENT = -35.0          # amendment: parts whose template+R render is quieter over half A are dropped
RERANKERS = {"mel_ref": ("mel", "ref"), "panns_ref": ("panns", "ref"),
             "mel_stem": ("mel", "stem"), "panns_stem": ("panns", "stem")}
BASE = {"ref": "flatref", "stem": "flatstem"}
NETB = {"ref": "net", "stem": "netstem"}


def half_a(x):
    """Half A, loudness-normalised, and its loudness before normalising."""
    import pyloudnorm

    y = x[int(P2.HALF_A[0] * SR):int(P2.HALF_A[1] * SR)].astype("float64")
    l = pyloudnorm.Meter(SR).integrated_loudness(y)
    return (y * 10 ** ((LUFS - l) / 20) if l > SILENT else None), l


def mel_feature(y):
    import librosa
    import numpy as np

    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=480, window="hann")) ** 2
    M = librosa.filters.mel(sr=SR, n_fft=4096, n_mels=64, fmin=50, fmax=16000) @ S
    tot = 10 * np.log10(M.sum(axis=0) + 1e-20)
    keep = tot >= tot.max() - 40
    L = 10 * np.log10(M[:, keep] + 1e-10)
    return np.concatenate([L.mean(axis=1), L.std(axis=1)])


def panns_model():
    import torch

    torch.set_num_threads(4)
    pkg_dir = VENV / "lib" / "python3.9" / "site-packages" / "panns_inference"
    pkg = types.ModuleType("pannsm")          # skip the package __init__, which writes ~/panns_data
    pkg.__path__ = [str(pkg_dir)]
    sys.modules["pannsm"] = pkg
    models = importlib.import_module("pannsm.models")
    net = models.Cnn14(sample_rate=32000, window_size=1024, hop_size=320, mel_bins=64,
                       fmin=50, fmax=14000, classes_num=527)
    net.load_state_dict(torch.load(CKPT, map_location="cpu")["model"])
    net.eval()
    return net


def panns_feature(net, y):
    import numpy as np
    import torch
    from scipy.signal import resample_poly

    z = resample_poly(y, 2, 3).astype(np.float32)          # 48 kHz -> 32 kHz
    win, hop = 32000, 16000
    w = np.stack([z[s:s + win] for s in range(0, len(z) - win + 1, hop)])
    with torch.no_grad():
        e = net(torch.from_numpy(w).to("cpu"), None)["embedding"].numpy()
    return e.mean(axis=0)


def clips():
    """Every clip that needs features: (key, path)."""
    ps, band, lags = P2.parts()
    usable = P2.stem_usable()
    panel = json.loads((P2.KILL / "pr12-clean" / "index.json").read_text())
    out = [(f"render|{r['part']}|{r['candidate']}", r["file"]) for r in panel["rows"]
           if "file" in r and r["candidate"] != "template"]
    for p in ps:
        out.append((f"rec|{p}|ref", str(P2.CROPS / p / "reference.wav")))
        if p in usable:
            out.append((f"rec|{p}|stem", str(P2.STEMS / "htdemucs_6s" / p / "instrumental_guitar.wav")))
    return out


def features():
    import numpy as np

    path = OUT / "features.npz"
    if path.exists():
        d = np.load(path, allow_pickle=True)
        return d["keys"].tolist(), d["mel"], d["panns"]
    net = panns_model()
    keys, mel, emb, lufs = [], [], [], []
    for i, (k, f) in enumerate(clips()):
        y, l = half_a(P2.mono(f))
        keys.append(k)
        lufs.append(l)
        mel.append(mel_feature(y) if y is not None else np.full(128, np.nan))
        emb.append(panns_feature(net, y) if y is not None else np.full(2048, np.nan))
        if i % 100 == 0:
            print("features", i, flush=True)
    mel, emb = np.array(mel), np.array(emb)
    np.savez(path, keys=np.array(keys, dtype=object), mel=mel, panns=emb, lufs=np.array(lufs))
    return keys, mel, emb


def picks(keys, mel, emb):
    import numpy as np

    from learn import train as TR

    ps, band, _ = P2.parts()
    fold_of, band_of = TR.k3_folds()
    usable = P2.stem_usable()
    idx = {k: i for i, k in enumerate(keys)}
    renders = [k.split("|")[1:] for k in keys if k.startswith("render|")]
    dropped = {q for q, c in renders if c == "template+R" and np.isnan(mel[idx[f"render|{q}|{c}"]]).any()}
    print("dropped development parts:", sorted(dropped), flush=True)
    renders = [(q, c) for q, c in renders if q not in dropped]
    assert not any(np.isnan(mel[idx[f"render|{q}|{c}"]]).any() for q, c in renders)
    assert not dropped & set(ps)
    names = sorted({c for _, c in renders})
    out = {}
    for p in ps:
        f = fold_of[band[p]]
        other = [(q, c) for q, c in renders if fold_of[band_of[q]] != f]
        assert all(band_of[q] != band[p] and q != p for q, _ in other)
        rows = np.array([idx[f"render|{q}|{c}"] for q, c in other])
        mu, sd = mel[rows].mean(axis=0), mel[rows].std(axis=0) + 1e-12
        cand = {}
        for n in names:
            ri = [idx[f"render|{q}|{c}"] for q, c in other if c == n]
            cand[n] = ((mel[ri].mean(axis=0) - mu) / sd, emb[ri].mean(axis=0), len(ri))
        for src in ("ref", "stem"):
            if src == "stem" and p not in usable:
                continue
            k = idx[f"rec|{p}|{src}"]
            zm = (mel[k] - mu) / sd
            e = emb[k]
            dm = {n: float(np.linalg.norm(zm - cand[n][0])) for n in names}
            dp = {n: float(1 - e @ cand[n][1] / (np.linalg.norm(e) * np.linalg.norm(cand[n][1])))
                  for n in names}
            out[(p, f"mel_{src}")] = min(dm, key=dm.get)
            out[(p, f"panns_{src}")] = min(dp, key=dp.get)
        out[(p, "_n_other_parts")] = len({q for q, _ in other})
    out["_dropped"] = sorted(dropped)
    return out, names


def score(pk, names):
    import numpy as np

    import kill_tests as K
    import render_preset_panel as RP
    from analysis.aligned import aligned_distance

    ps, band, lags = P2.parts()
    prev = json.loads((P2.OUT / "result.json").read_text())
    result, check = {}, []
    for bs in P2.BAND_SETS:
        prow = {r["part"]: r for r in prev[bs]["rows"]}
        rows = []
        for p in ps:
            mdir = P2.OUT / "measure" / p
            mdi = np.load(mdir / "di.npy")
            ref = P2.recording(p, "ref")
            wav = {n: P2.mono(mdir / f"{RP._slug(n)}.wav") for n in names}

            def dist(n, half):
                return aligned_distance(ref, wav[n], mdi, lag=lags[p], render_latency=P2.LATENCY,
                                        start_s=half[0], end_s=half[1], bands=bs).distance

            dB = {n: dist(n, P2.HALF_B) for n in names}
            dA = {n: dist(n, P2.HALF_A) for n in names}
            lt = math.log(dB["template+R"])

            def score_pick(n):
                return (math.log(dB[n]) - lt) if n and dB.get(n) else None

            okA = {n: v for n, v in dA.items() if v}
            oracle = score_pick(min(okA, key=okA.get)) if okA else None
            row = {"part": p, "band": band[p], "template+R": 0.0}
            for k in ("oracle", "flatref", "flatstem", "net", "netstem"):
                row[k] = prow[p].get(k)
                if k != "oracle":
                    row[k + "_pick"] = prow[p].get(k + "_pick")
            check.append((bs, p, "oracle", oracle, row["oracle"]))
            check.append((bs, p, "flatref", score_pick(row["flatref_pick"]), row["flatref"]))
            for rk, (_, src) in RERANKERS.items():
                if (p, rk) in pk:
                    row[rk + "_pick"] = pk[(p, rk)]
                    row[rk] = score_pick(pk[(p, rk)])
            rows.append(row)
        summ = {k: K.band_stat(rows, k)
                for k in ["oracle", "flatref", "flatstem", "net", "netstem"] + list(RERANKERS)}
        for rk, (_, src) in RERANKERS.items():
            for b in (BASE[src], NETB[src]):
                pr = [dict(band=r["band"], x=r[rk] - r[b]) for r in rows
                      if r.get(rk) is not None and r.get(b) is not None]
                summ[f"{rk}_minus_{b}"] = K.band_stat(pr, "x")
        result[bs] = {"summary": summ, "rows": rows}
    bad = [c for c in check if (c[3] is None) != (c[4] is None)
           or (c[3] is not None and abs(c[3] - c[4]) > 1e-9)]
    assert not bad, bad[:5]
    gate = {}
    for rk, (_, src) in RERANKERS.items():
        ok = []
        for bs in P2.BAND_SETS:
            s = result[bs]["summary"][f"{rk}_minus_{BASE[src]}"]
            ok.append(s is not None and s["band_median_log_ratio"] <= GATE
                      and s["sign_flip_p_two_sided"] < 0.1)
        gate[rk] = all(ok)
    result["gate"] = gate
    result["scoring_check"] = f"{len(check)} recomputed oracle/flatref scores match result.json"
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0, w0 = time.process_time(), time.time()
    keys, mel, emb = features()
    t1 = time.process_time()
    pk, names = picks(keys, mel, emb)
    res = score(pk, names)
    res["dropped_development_parts"] = pk["_dropped"]
    res["cpu_seconds"] = {"features": round(t1 - t0, 1), "picks_and_scoring": round(time.process_time() - t1, 1),
                          "wall": round(time.time() - w0, 1)}
    (OUT / "result.json").write_text(json.dumps(res, indent=1))
    for bs in P2.BAND_SETS:
        for k, v in res[bs]["summary"].items():
            print(bs, k, (v["band_median_log_ratio"], v["parts_better"], v["parts"],
                          v["sign_flip_p_two_sided"]) if v else None)
    print("gate", res["gate"], res["cpu_seconds"], res["scoring_check"])


if __name__ == "__main__":
    main()
