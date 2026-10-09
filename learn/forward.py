"""A learned stand-in for PR12: settings → transfer curve, and its inverse by search.

F(θ) predicts the transfer curve (`learn/transfer.py`) a setting gives an average
player. It is fitted on the POC renders, each measured through one DI, so it averages
over players. `fit_settings` finds settings whose F matches a target curve. Gradient
descent over the continuous controls runs from many starts that enumerate the switches
and mic types, and keeps the best.

    $TORCH_PY -m learn.forward fit --cache ~/ndsp-presets/learn/poc/cache \\
        --renders ~/ndsp-presets/learn/poc/renders --out ~/ndsp-presets/learn/poc/forward.pt
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import pr12  # noqa: E402

N_CONT = len(pr12.CONTINUOUS)
N_BIN = len(pr12.BINARY)
DIM = N_CONT + N_BIN + 2 * pr12.MICS
BANDS = 64


def features(s, effective_drive):
    """θ as F's input: continuous controls in unit range (gated ones zeroed when off), the
    switches, and both mic types one-hot (the right one zeroed when its cab is off)."""
    cont, mask, binary, _, cat, _ = pr12.encode(s, effective_drive)
    x = [c * m if g is not None else c
         for c, m, (_, _, _, _, g) in zip(cont, mask, pr12.CONTINUOUS)]
    for j, (name, *_rest) in enumerate(pr12.CONTINUOUS):
        if name == "cabParameters/leftCabMicLevel":
            x[j] = 0.0
    left = [0.0] * pr12.MICS
    left[cat[0]] = 1.0
    right = [0.0] * pr12.MICS
    if s["cabParameters/rightCabActive"]:
        right[cat[1]] = 1.0
    return x + binary + left + right


def build_model():
    import torch.nn as nn

    return nn.Sequential(nn.Linear(DIM, 512), nn.GELU(), nn.Linear(512, 512), nn.GELU(),
                         nn.Linear(512, 512), nn.GELU(), nn.Linear(512, BANDS))


def load_xy(cache, renders):
    import numpy as np

    meta = json.loads((cache / "meta.json").read_text())
    rows = {}
    for f in renders.glob("index-w*.jsonl"):
        for line in f.read_text().splitlines():
            if line:
                r = json.loads(line)
                rows[r["id"]] = r
    X = np.array([features(rows[m["id"]]["sample"], m["effective_drive"]) for m in meta],
                 np.float32)
    T = np.load(cache / "transfer.npy").astype(np.float32)
    bands = [m["band"] for m in meta]
    return X, T, bands


def fit(cache, renders, out, holdout_fold=None, epochs=300):
    import numpy as np
    import torch

    from learn import train as TR

    X, T, bands = load_xy(cache, renders)
    fold_of, _ = TR.k3_folds()
    f = np.array([fold_of.get(b, -1) for b in bands])
    tr = f != holdout_fold if holdout_fold is not None else np.ones(len(X), bool)
    va = ~tr
    torch.manual_seed(0)
    net = build_model()
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    Xt, Tt = torch.tensor(X[tr]), torch.tensor(T[tr])
    for epoch in range(epochs):
        perm = torch.randperm(len(Xt))
        for s in range(0, len(Xt), 256):
            idx = perm[s:s + 256]
            loss = torch.nn.functional.smooth_l1_loss(net(Xt[idx]), Tt[idx], beta=1.0)
            opt.zero_grad()
            loss.backward()
            opt.step()
        sched.step()
    net.eval()
    report = {}
    if va.any():
        with torch.no_grad():
            P = net(torch.tensor(X[va])).numpy()
        report = {"heldout_mae_db": float(np.abs(P - T[va]).mean()),
                  "constant_mae_db": float(np.abs(T[tr].mean(0) - T[va]).mean()),
                  "n": int(va.sum())}
        print(json.dumps(report))
    torch.save(net.state_dict(), out)
    return report


def load(path):
    import torch

    net = build_model()
    net.load_state_dict(torch.load(path, map_location="cpu"))
    net.eval()
    return net


def fit_settings(net, target, weights, effective_drive=None, steps=150, starts=None, seed=0):
    """Settings whose F best matches `target` (64 dB values, mean-removed) under per-band
    `weights`. Returns (sample dict, effective drive, weighted MAE).

    The continuous controls are optimised by Adam in unit range (through a sigmoid) from
    one start per switch-and-mic combination drawn from `starts` (a list of samples, e.g.
    the factory presets plus random draws). With `effective_drive` given, drive is held
    fixed at it."""
    import numpy as np
    import torch

    rng = np.random.default_rng(seed)
    tgt = torch.tensor(np.asarray(target, np.float32))
    w = torch.tensor(np.asarray(weights, np.float32))
    w = w / w.sum()
    inits = []
    for s in starts:
        drive = effective_drive if effective_drive is not None else float(s["parameters/inputGain"])
        inits.append(np.array(features(s, drive), np.float32))
    base = torch.tensor(np.stack(inits))
    cont0 = base[:, :N_CONT].clamp(1e-3, 1 - 1e-3)
    z = torch.logit(cont0).clone().requires_grad_(True)
    fixed = base[:, N_CONT:]
    gate_cols = {j: pr12.BINARY.index(g) for j, (_, _, _, _, g) in enumerate(pr12.CONTINUOUS)
                 if g is not None}
    drive_col = [n for n, *_ in pr12.CONTINUOUS].index("parameters/inputGain")
    opt = torch.optim.Adam([z], lr=0.05)

    def forward():
        u = torch.sigmoid(z)
        if effective_drive is not None:
            lo, hi = pr12.CONTINUOUS[drive_col][1:3]
            u = u.clone()
            u[:, drive_col] = (effective_drive - lo) / (hi - lo)
        cols = []
        for j in range(N_CONT):
            c = u[:, j]
            if j in gate_cols:
                c = c * fixed[:, gate_cols[j]]
            cols.append(c)
        x = torch.cat([torch.stack(cols, 1), fixed], 1)
        pred = net(x)
        err = ((pred - tgt).abs() * w).sum(1)
        return u, err

    for _ in range(steps):
        _, err = forward()
        opt.zero_grad()
        err.sum().backward()
        opt.step()
    with torch.no_grad():
        u, err = forward()
    best = int(err.argmin())
    s = dict(starts[best])
    for j, (name, lo, hi, warp, _) in enumerate(pr12.CONTINUOUS):
        v = float(u[best, j])
        if name == "cabParameters/leftCabMicLevel":
            s[name] = 0.0
        elif name == "cabParameters/rightCabMicLevel":
            s[name] = min(hi, max(lo, pr12.from_unit(v, *pr12.MIC_DIFF, "lin")))
        else:
            s[name] = pr12.from_unit(v, lo, hi, warp)
    drive = s["parameters/inputGain"]
    return s, float(drive), float(err[best])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--cache", type=pathlib.Path, required=True)
    f.add_argument("--renders", type=pathlib.Path, required=True)
    f.add_argument("--out", type=pathlib.Path, required=True)
    f.add_argument("--holdout-fold", type=int)
    f.add_argument("--epochs", type=int, default=300)
    args = ap.parse_args()
    fit(args.cache.expanduser(), args.renders.expanduser(), args.out.expanduser(),
        args.holdout_fold, args.epochs)


if __name__ == "__main__":
    main()
