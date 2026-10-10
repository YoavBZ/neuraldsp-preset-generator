"""Leave-band-out evaluation of the sound-description translator on real recordings
(`docs/sound-desc-plan.md`)."""

from __future__ import annotations

import json
import math
import statistics

from learn import confirm_run as CR
from learn import phase2_set3 as P
from learn import rescore as R
from learn import set3_gap_split as G
from learn import songs_check as SC
from learn import sound_desc as S

ALPHAS = (0.1, 1.0, 10.0, 100.0, 1000.0)


def test_parts():
    """slug -> {band, gain_class, ref, stem, D (distances), chooser kind}."""
    from learn import train as TR

    _, band_of = TR.k3_folds()
    d3 = json.loads((R.OUT / "distances.json").read_text())
    d12 = json.loads((SC.OUT / "distances.json").read_text())
    out = {}
    for s, p in G.parts().items():
        if p["gain_class"] in ("clean", "crunch"):
            out[s] = dict(band=p["band"], gain_class=p["gain_class"], ref=P.CROPS / s / "reference.wav",
                          stem=None, D=d3[s], chooser="lp3k")
    for s, p in SC.parts().items():
        if p["set"] == 12 and p["gain_class"] in ("clean", "crunch"):
            out[s] = dict(band=band_of[s], gain_class=p["gain_class"], ref=p["crop"] / "reference.wav",
                          stem=p["stem"], D=d12[s], chooser="amp")
    return out


def load_training():
    import numpy as np

    ws = {w["id"]: w for w in json.loads((S.OUT / "windows.json").read_text())}
    T = json.loads((S.OUT / "targets.json").read_text())["T"]
    rows = []
    for wid, w in ws.items():
        z = np.load(S.OUT / "renders" / f"{wid}.npz")
        for k, x, xa in zip(z["keys"], z["X"], z["Xa"]):
            rows.append((w["band"], str(k), x, xa))
    return rows, {k: np.array(v, np.float32) for k, v in T.items()}


def _ridge(X, Y, alpha):
    import numpy as np

    Xa = np.hstack([X, np.ones((len(X), 1))])
    A = Xa.T @ Xa + alpha * np.eye(Xa.shape[1])
    A[-1, -1] -= alpha
    return np.linalg.solve(A, Xa.T @ Y)


def _apply(W, X):
    import numpy as np

    return np.hstack([X, np.ones((len(X), 1))]) @ W


def fit(rows, T, exclude_band):
    """Standardise on the training inputs, choose the ridge penalty by leave-band-out CV
    inside the training bands, and fit. Returns (mu, sd, W)."""
    import numpy as np

    tr = [r for r in rows if r[0] != exclude_band]
    X = np.array([r[2] for r in tr] + [r[3] for r in tr])
    Y = np.array([T[r[1]] for r in tr] * 2)
    bands = np.array([r[0] for r in tr] * 2)
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Xs, Ys = (X - mu) / sd, (Y - mu) / sd
    groups = sorted(set(bands))
    folds = [groups[i::5] for i in range(5)]
    best = None
    for a in ALPHAS:
        err = 0.0
        for f in folds:
            m = np.isin(bands, f)
            W = _ridge(Xs[~m], Ys[~m], a)
            err += float(((_apply(W, Xs[m]) - Ys[m]) ** 2).mean())
        if best is None or err < best[0]:
            best = (err, a)
    return mu, sd, _ridge(Xs, Ys, best[1]), best[1]


def fit_mlp(rows, T, exclude_band, mu, sd, seed=S.SEED):
    import numpy as np
    import torch

    torch.manual_seed(seed)
    tr = [r for r in rows if r[0] != exclude_band]
    bands = sorted({r[0] for r in tr})
    val_b = set(bands[::5])
    def mats(rs):
        X = np.array([r[2] for r in rs] + [r[3] for r in rs])
        Y = np.array([T[r[1]] for r in rs] * 2)
        return torch.tensor((X - mu) / sd, dtype=torch.float32), torch.tensor((Y - mu) / sd, dtype=torch.float32)
    Xt, Yt = mats([r for r in tr if r[0] not in val_b])
    Xv, Yv = mats([r for r in tr if r[0] in val_b])
    d = Xt.shape[1]
    net = torch.nn.Sequential(torch.nn.Linear(d, 256), torch.nn.GELU(), torch.nn.Linear(256, 256),
                              torch.nn.GELU(), torch.nn.Linear(256, d))
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)
    best, best_state, bad = 1e9, None, 0
    for epoch in range(200):
        perm = torch.randperm(len(Xt))
        for i in range(0, len(Xt), 512):
            b = perm[i:i + 512]
            opt.zero_grad()
            loss = ((net(Xt[b]) - Yt[b]) ** 2).mean()
            loss.backward()
            opt.step()
        with torch.no_grad():
            v = float(((net(Xv) - Yv) ** 2).mean())
        if v < best - 1e-4:
            best, best_state, bad = v, {k: t.clone() for k, t in net.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= 10:
                break
    net.load_state_dict(best_state)
    net.eval()
    return lambda Xs: net(torch.tensor(Xs, dtype=torch.float32)).detach().numpy()


def evaluate():
    import numpy as np

    rows, T = load_training()
    tp = test_parts()
    win_bands = {r[0] for r in rows}
    clean = json.loads((CR.PLUGIN_ROOT / "docs/clean-baseline-choice.json").read_text())["presets"]
    crunch = json.loads((CR.PLUGIN_ROOT / "docs/crunch-baseline-choice.json").read_text())["presets"]
    halves = {"A": P.HALF_A, "B": P.HALF_B}
    picks = {}
    log = {"test_bands_in_windows": sorted({p["band"] for p in tp.values()} & win_bands), "alpha": {}}
    models = {}
    for band in sorted({p["band"] for p in tp.values()}):
        mu, sd, W, a = fit(rows, T, band)
        mlp = fit_mlp(rows, T, band, mu, sd)
        models[band] = (mu, sd, W, mlp)
        log["alpha"][band] = a
        print("fitted, leaving out", band, "alpha", a, flush=True)
    for slug, p in tp.items():
        mu, sd, W, mlp = models[p["band"]]
        for src in ("ref", "stem"):
            if p[src] is None:
                continue
            x = CR.mono(p[src])
            for h, (a, b) in halves.items():
                d = S.describe(x[int(a * S.SR):int(b * S.SR)])
                xs = (d - mu) / sd
                preds = {"none": xs, "ridge": _apply(W, xs[None])[0], "mlp": mlp(xs[None])[0]}
                for amp in P.AMPS:
                    names = [n for n in p["D"][f"flat|{amp}|measfix_A"]]
                    Ts = {n: (T[f"{amp}|{n}"] - mu) / sd for n in names if f"{amp}|{n}" in T}
                    for model, yhat in preds.items():
                        best = min(Ts, key=lambda n: float(((Ts[n] - yhat) ** 2).sum()))
                        picks[(slug, src, amp, model, h)] = best
    # Scoring: choose on one half, measure on the other (fixed level, flat judge).
    def ratio(slug, amp, pick, base, other):
        M = tp[slug]["D"][f"flat|{amp}|measfix_{other}"]
        return math.log(M[pick][0] / M[base][0]) if M.get(pick) and M[pick][0] and M[base][0] else None

    def baseline(slug, amp):
        return (clean if tp[slug]["gain_class"] == "clean" else crunch)[amp]

    def chooser_pick(slug, amp, h):
        row = {n: v[0] for n, v in tp[slug]["D"][f"flat|{amp}|{tp[slug]['chooser']}_{h}"].items() if v[0]}
        return min(row, key=lambda n: (row[n], n)) if row else None

    def oracle_pick(slug, amp, h):
        row = {n: v[0] for n, v in tp[slug]["D"][f"flat|{amp}|measfix_{h}"].items() if v[0]}
        return min(row, key=lambda n: (row[n], n)) if row else None

    comps = {}
    for slug, p in tp.items():
        for amp in P.AMPS:
            for src in ("ref", "stem"):
                if (slug, src, amp, "ridge", "A") not in picks:
                    continue
                vals = {}
                for h, other in (("A", "B"), ("B", "A")):
                    base = baseline(slug, amp)
                    cand = {"ridge": picks[(slug, src, amp, "ridge", h)], "mlp": picks[(slug, src, amp, "mlp", h)],
                            "none": picks[(slug, src, amp, "none", h)], "base": base,
                            "chooser": chooser_pick(slug, amp, h), "oracle": oracle_pick(slug, amp, h)}
                    for k, n in cand.items():
                        if n is None:
                            continue
                        rv = ratio(slug, amp, n, base, other)
                        if rv is not None:
                            vals.setdefault(k, []).append(rv)
                full = {k: statistics.fmean(v) for k, v in vals.items() if len(v) == 2}
                for a_, b_ in (("ridge", "none"), ("ridge", "base"), ("ridge", "chooser"), ("mlp", "none"),
                               ("mlp", "base"), ("none", "base"), ("oracle", "base"), ("chooser", "base")):
                    if a_ in full and b_ in full:
                        comps.setdefault(f"{src}|{a_}_vs_{b_}", []).append((p["band"], full[a_] - full[b_]))
    res = {k: CR.stats(v) for k, v in comps.items()}
    prim = res.get("ref|ridge_vs_none"), res.get("ref|ridge_vs_base")
    go = bool(prim[0] and prim[1] and prim[0]["hi90"] < 0 and prim[1]["mean"] < 0)
    out = {"decision": "phase B worth starting" if go else "stop at this stage", "log": log,
           "n_test_parts": len(tp), "test_bands": len({p["band"] for p in tp.values()}), "results": res}
    (S.OUT / "result.json").write_text(json.dumps(out, indent=1, default=float))
    print("DECISION:", out["decision"])
    for k, s in sorted(res.items()):
        print(f"  {k:28s} mean {s['mean']:+.3f} 90% [{s['lo90']:+.3f}, {s['hi90']:+.3f}] "
              f"W/T/L {s['wins']}/{s['ties']}/{s['losses']} bands {s['bands']}")
    return out
