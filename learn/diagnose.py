"""In-domain diagnostic: per-control error on held-out-band renders, against a baseline
that always predicts the training median (or majority class). Renders only; no real
recording is read.

    $TORCH_PY -m learn.diagnose --cache ~/ndsp-presets/learn/poc/cache --model .../fold0.pt --fold 0
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import pr12, train as T  # noqa: E402


def main():
    import numpy as np
    import torch

    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=pathlib.Path, required=True)
    ap.add_argument("--model", type=pathlib.Path, required=True)
    ap.add_argument("--fold", type=int, required=True)
    ap.add_argument("--max", type=int, default=2000)
    args = ap.parse_args()
    cache = args.cache.expanduser()
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    X = np.load(cache / "audio.npy", mmap_mode="r")
    L = np.load(cache / "labels.npz")
    meta = json.loads((cache / "meta.json").read_text())
    fold_of, _ = T.k3_folds()
    f = np.array([fold_of.get(m["band"], -1) for m in meta])
    tr, va = np.where(f != args.fold)[0], np.where(f == args.fold)[0][:args.max]
    net = T.build_model().to(device)
    net.load_state_dict(torch.load(args.model.expanduser(), map_location=device))
    net.eval()
    fe = T.Frontend(device)
    cont, binp, cats = [], [], []
    with torch.no_grad():
        for s in range(0, len(va), 128):
            idx = va[s:s + 128]
            w = torch.tensor(X[idx, (T.CLIP - T.CROP) // 2:(T.CLIP - T.CROP) // 2 + T.CROP]
                             .astype(np.float32) / 32767, device=device)
            c, b, k = net(fe(w))
            cont.append(c.cpu().numpy()); binp.append(torch.sigmoid(b).cpu().numpy())
            cats.append([torch.softmax(x, -1).cpu().numpy() for x in k])
    cont = np.concatenate(cont); binp = np.concatenate(binp)
    print(f"{'control':40s} {'units':>6s} {'model MAE':>10s} {'median MAE':>11s} {'ratio':>6s}  n")
    for j, (name, lo, hi, warp, _) in enumerate(pr12.CONTINUOUS):
        m = L["mask"][va, j] > 0
        if m.sum() < 20:
            continue
        mt = L["mask"][tr, j] > 0
        y = L["cont"][va, j][m]
        med = np.median(L["cont"][tr, j][mt])
        if name == "cabParameters/rightCabMicLevel":
            lo, hi = pr12.MIC_DIFF
        if warp == "log":
            conv = lambda u: np.exp(np.log(lo) + u * (np.log(hi) - np.log(lo)))
            err = np.abs(np.log2(conv(cont[m, j]) / conv(y))).mean()
            base = np.abs(np.log2(conv(med) / conv(y))).mean()
            unit = "oct"
        else:
            err = np.abs(cont[m, j] - y).mean() * (hi - lo)
            base = np.abs(med - y).mean() * (hi - lo)
            unit = "dB" if hi - lo > 2 else "knob"
        print(f"{name:40s} {unit:>6s} {err:10.3f} {base:11.3f} {err / base:6.2f}  {m.sum()}")
    for j, name in enumerate(pr12.BINARY):
        m = L["bmask"][va, j] > 0
        y = L["binary"][va, j][m]
        maj = float(L["binary"][tr, j].mean() > 0.5)
        print(f"{name:40s} acc {((binp[m, j] > 0.5) == y).mean():.3f}  majority {(y == maj).mean():.3f}")
    for n, (name, k, _) in enumerate(pr12.CATEGORICAL):
        m = L["cmask"][va, n] > 0
        p = np.concatenate([c[n] for c in cats])[m]
        y = L["cat"][va, n][m]
        maj = np.bincount(L["cat"][tr, n], minlength=k).argmax()
        print(f"{name:40s} acc {(p.argmax(1) == y).mean():.3f}  majority {(y == maj).mean():.3f}")


if __name__ == "__main__":
    main()
