"""Stage 1 of `docs/sound-desc-plan.md` (v2 + amendments): the translator, leave-band-out,
on real recordings.

    $TORCH_PY -m learn.sound_desc evaluate
"""

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
DESC, GATE = "D130", 40


def test_parts():
    """slug -> {band, gain_class, D (distances), chooser kind} for the development clean and
    crunch parts (the pinned list is a subset)."""
    from learn import train as TR

    _, band_of = TR.k3_folds()
    d3 = json.loads((R.OUT / "distances.json").read_text())
    d12 = json.loads((SC.OUT / "distances.json").read_text())
    out = {}
    for s, p in G.parts().items():
        if p["gain_class"] in ("clean", "crunch"):
            out[s] = dict(band=p["band"], gain_class=p["gain_class"], D=d3[s], chooser="lp3k")
    for s, p in SC.parts().items():
        if p["set"] == 12 and p["gain_class"] in ("clean", "crunch"):
            out[s] = dict(band=band_of[s], gain_class=p["gain_class"], D=d12[s], chooser="amp")
    return out


def _ridge(X, Y, alpha):
    import numpy as np

    Xa = np.hstack([X, np.ones((len(X), 1))])
    A = Xa.T @ Xa + alpha * np.eye(Xa.shape[1])
    A[-1, -1] -= alpha
    return np.linalg.solve(A, Xa.T @ Y)


def _apply(W, X):
    import numpy as np

    return np.hstack([X, np.ones((len(X), 1))]) @ W


def load_training():
    import numpy as np

    ws = {w["id"]: w for w in json.loads((S.OUT / "windows.json").read_text())}
    TF = json.loads((S.OUT / "targets-frames.json").read_text())[DESC][str(GATE)]
    T = {k: np.array(v, np.float64) for k, v in TF.items()}
    rows = []
    for wid, w in ws.items():
        z = np.load(S.OUT / "renders" / f"{wid}.npz")
        for k, x, xa in zip(z["keys"], z["X"], z["Xa"]):
            rows.append((w["band"], str(k), x.astype(np.float64), xa.astype(np.float64)))
    return rows, T


def fit_fold(rows, T, held_band):
    """Ridge (primary), bias-only and MLP (secondary), on windows not from `held_band`;
    standardisation fitted on the fold's training inputs."""
    import numpy as np

    tr = [r for r in rows if r[0] != held_band]
    assert all(r[0] != held_band for r in tr)
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
            mu_f, sd_f = X[~m].mean(0), X[~m].std(0) + 1e-6
            W = _ridge((X[~m] - mu_f) / sd_f, (Y[~m] - mu_f) / sd_f, a)
            err += float((((_apply(W, (X[m] - mu_f) / sd_f)) - (Y[m] - mu_f) / sd_f) ** 2).mean())
        if best is None or err < best[0]:
            best = (err, a)
    W = _ridge(Xs, Ys, best[1])
    bias = (Ys - Xs).mean(0)
    mlp = _mlp(Xs, Ys, bands)
    return {"mu": mu, "sd": sd, "alpha": best[1],
            "ridge": lambda z: _apply(W, z[None])[0], "bias": lambda z: z + bias, "mlp": mlp}


def _mlp(Xs, Ys, bands):
    import numpy as np
    import torch

    torch.manual_seed(S.SEED)
    groups = sorted(set(bands))
    val = np.isin(bands, groups[::5])
    Xt, Yt = torch.tensor(Xs[~val], dtype=torch.float32), torch.tensor(Ys[~val], dtype=torch.float32)
    Xv, Yv = torch.tensor(Xs[val], dtype=torch.float32), torch.tensor(Ys[val], dtype=torch.float32)
    d = Xs.shape[1]
    net = torch.nn.Sequential(torch.nn.Linear(d, 256), torch.nn.GELU(), torch.nn.Linear(256, 256),
                              torch.nn.GELU(), torch.nn.Linear(256, d))
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)
    best, state, bad = 1e9, None, 0
    for _ in range(200):
        perm = torch.randperm(len(Xt))
        for i in range(0, len(Xt), 512):
            b = perm[i:i + 512]
            opt.zero_grad()
            ((net(Xt[b]) - Yt[b]) ** 2).mean().backward()
            opt.step()
        with torch.no_grad():
            v = float(((net(Xv) - Yv) ** 2).mean())
        if v < best - 1e-4:
            best, state, bad = v, {k: t.clone() for k, t in net.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= 10:
                break
    net.load_state_dict(state)
    net.eval()
    return lambda z: net(torch.tensor(z[None], dtype=torch.float32)).detach().numpy()[0]


def evaluate():
    import numpy as np

    from learn import sound_desc_stage0 as S0

    pin = json.loads(S0.PINNED.read_text())
    tp = {s: v for s, v in test_parts().items() if s in pin["parts"]}
    feats = {s: json.loads((S0.CACHE / f"{s}.json").read_text()) for s in tp}
    rows, T = load_training()
    win_bands = {r[0] for r in rows}
    test_bands = sorted({p["band"] for p in tp.values()})
    D = {s: tp[s]["D"] for s in tp}

    def mean_halves(s, amp, n):
        a, b = D[s][f"flat|{amp}|measfix_A"][n][0], D[s][f"flat|{amp}|measfix_B"][n][0]
        return (a + b) / 2 if a and b else None

    def lbo_baseline(slug, amp):            # amendment 3
        cls, band = tp[slug]["gain_class"], tp[slug]["band"]
        others = [s for s in tp if tp[s]["gain_class"] == cls and tp[s]["band"] != band]
        meds = {}
        for n in [n for n in D[slug][f"flat|{amp}|measfix_A"] if n.startswith("factory:")]:
            v = [mean_halves(s, amp, n) for s in others]
            if v and all(x is not None for x in v):
                meds[n] = statistics.median(v)
        return min(meds, key=lambda n: (meds[n], n))

    def stored_pick(slug, amp, h, kind):
        row = {n: v[0] for n, v in D[slug][f"flat|{amp}|{kind}_{h}"].items() if v[0]}
        return min(row, key=lambda n: (row[n], n)) if row else None

    base = {(s, a): lbo_baseline(s, a) for s in tp for a in P.AMPS}
    cells = {}                                  # (slug, amp) -> {kind: [ratio per direction]}
    control = {}
    alphas = {}
    for band in test_bands:
        m = fit_fold(rows, T, band)
        alphas[band] = m["alpha"]
        mu, sd = m["mu"], m["sd"]
        others = [o for o in tp if tp[o]["band"] != band]
        for s in [x for x in tp if tp[x]["band"] == band]:
            for amp in P.AMPS:
                names = list(D[s][f"flat|{amp}|measfix_A"])
                Ts = {n: (T[f"{amp}|{n}"] - mu) / sd for n in names if f"{amp}|{n}" in T}
                cen = {}
                for h, other in (("A", "B"), ("B", "A")):
                    M, b = D[s][f"flat|{amp}|measfix_{other}"], base[(s, amp)]

                    def score(pick):
                        return math.log(M[pick][0] / M[b][0]) if pick and M.get(pick) and M[pick][0] and M[b][0] else None

                    def nearest(cands, z):
                        return min(cands, key=lambda n: float(((cands[n] - z) ** 2).sum()))

                    rec = (np.array(feats[s]["rec"][h][str(GATE)][DESC]) - mu) / sd
                    cen = {n: (np.mean([feats[o]["render"][f"{amp}|{n}|{h}"][str(GATE)][DESC] for o in others],
                                       axis=0) - mu) / sd for n in names}
                    ceil = {n: (np.array(feats[s]["render"][f"{amp}|{n}|{h}"][str(GATE)][DESC]) - mu) / sd
                            for n in names}
                    picks = {"ridge": nearest(Ts, m["ridge"](rec)), "bias": nearest(Ts, m["bias"](rec)),
                             "mlp": nearest(Ts, m["mlp"](rec)), "none": nearest(Ts, rec),
                             "centroid": nearest(cen, rec), "ceiling": nearest(ceil, rec),
                             "chooser": stored_pick(s, amp, h, tp[s]["chooser"]),
                             "oracle": stored_pick(s, amp, h, "measfix"), "base": b}
                    for k, n in picks.items():
                        v = score(n)
                        if v is not None:
                            cells.setdefault((s, amp), {}).setdefault(k, []).append(v)
                    # Positive control (amendment 5): the oracle preset's own stored render as
                    # the input, a synthetic record with a known best.
                    o = stored_pick(s, amp, h, "measfix")
                    if o:
                        z = ceil[o]
                        for k, n in (("ridge", nearest(Ts, m["ridge"](z))), ("centroid", nearest(cen, z))):
                            v = score(n)
                            if v is not None:
                                control.setdefault((s, amp), {}).setdefault(k, []).append(v)
        print("fold done:", band, "alpha", m["alpha"], flush=True)

    def comp(a, b, cls=None, src=cells):
        rs = []
        for (s, amp), v in src.items():
            if cls and tp[s]["gain_class"] != cls:
                continue
            if len(v.get(a, [])) == 2 and len(v.get(b, [])) == 2:
                rs.append((tp[s]["band"], statistics.fmean(v[a]) - statistics.fmean(v[b])))
        return CR.stats(rs) if rs else None

    res = {}
    for a, b in (("ridge", "none"), ("ridge", "centroid"), ("ridge", "base"), ("mlp", "base"), ("bias", "base"),
                 ("none", "base"), ("centroid", "base"), ("ceiling", "base"), ("chooser", "base"),
                 ("oracle", "base"), ("ridge", "chooser")):
        for cls in (None, "clean", "crunch"):
            r = comp(a, b, cls)
            if r:
                res[f"{a}_vs_{b}|{cls or 'all'}"] = r
    ctrl = comp("ridge", "centroid", None, control)
    better = min(("none", "centroid"), key=lambda k: res[f"{k}_vs_base|all"]["mean"])
    g1 = res[f"ridge_vs_{better}|all"]
    g1_out = "helps" if g1["hi90"] < 0 else "futile" if g1["lo90"] > -0.02 else "inconclusive"
    if g1_out == "futile" and not (ctrl and ctrl["mean"] <= 0):
        g1_out = "inconclusive (positive control failed)"
    g2 = res["ridge_vs_base|crunch"]
    g2_out = "helps" if g2["hi90"] < 0 else "futile" if g2["lo90"] > -0.03 else "inconclusive"
    ceil_gap = res[f"ceiling_vs_base|all"]["mean"] - res[f"{better}_vs_base|all"]["mean"]
    share = (g1["mean"] / ceil_gap) if ceil_gap < 0 else None
    out = {"gate1": {"against": better, "result": g1, "outcome": g1_out, "gap_share_closed": share},
           "gate2_crunch": {"result": g2, "outcome": g2_out},
           "phase_b": g1_out == "helps" and g2_out != "futile",
           "positive_control_ridge_vs_centroid": ctrl, "alphas": alphas,
           "windows": len({r[1] for r in rows}), "test_bands_in_windows": sorted(set(test_bands) & win_bands),
           "results": res}
    (S.OUT / "stage1-result.json").write_text(json.dumps(out, indent=1, default=float))
    print("GATE 1:", g1_out, "vs", better, g1["mean"], g1["lo90"], g1["hi90"], "gap share", share)
    print("GATE 2 (crunch):", g2_out, g2["mean"], g2["lo90"], g2["hi90"])
    print("PHASE B:", out["phase_b"], "| positive control ridge vs centroid:", ctrl and ctrl["mean"])
    for k in sorted(res):
        s_ = res[k]
        print(f"  {k:28s} mean {s_['mean']:+.3f} [{s_['lo90']:+.3f}, {s_['hi90']:+.3f}] "
              f"W/T/L {s_['wins']}/{s_['ties']}/{s_['losses']} bands {s_['bands']}")
    return out
