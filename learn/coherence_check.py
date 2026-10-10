"""Waveform fidelity of DI networks on validation pairs (`docs/di-loss-plan.md`).

Coherence between each rebuilt DI and its true DI, and between the input (the render)
and the true DI, on held-out-fold pairs (K3 fold 2) from the PR12, SW50R and AC20
caches. Coherence ignores EQ and level, so the average-balance target doesn't matter.

    $TORCH_PY -m learn.coherence_check MODEL [MODEL ...]
"""

from __future__ import annotations

import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

D_ROOT = pathlib.Path("~/ndsp-presets/learn/direc").expanduser()
CACHES = ("cache", "cache-sw50r", "cache-ac20")
BANDS = ((80, 1000), (1000, 3000), (3000, 8000))
SR, CROP, CLIP = 48000, 3 * 48000, 6 * 48000


def clips(per_cache=32, seed=20261010):
    import numpy as np

    from learn import train as TR

    fold_of, _ = TR.k3_folds()
    rng = np.random.default_rng(seed)
    out = []
    for c in CACHES:
        meta = json.loads((D_ROOT / c / "meta.json").read_text())
        va = [i for i, m in enumerate(meta) if fold_of.get(m["band"], -1) == 2]
        X = np.load(D_ROOT / c / "input.npy", mmap_mode="r")
        Y = np.load(D_ROOT / c / "di.npy", mmap_mode="r")
        a = (CLIP - CROP) // 2
        for i in rng.choice(va, per_cache, replace=False):
            out.append((X[i][a:a + CROP].astype(np.float32) / 32767,
                        Y[i][a:a + CROP].astype(np.float32) / 32767))
    return out


def coherence(x, y):
    import numpy as np
    from scipy.signal import coherence as coh

    f, c = coh(x, y, fs=SR, nperseg=2048)
    return [float(np.mean(c[(f >= a) & (f < b)])) for a, b in BANDS]


def main(models):
    import numpy as np
    import torch

    from learn import direc as D

    data = clips()
    rows = {"input": [coherence(x, y) for x, y in data]}
    for m in models:
        net = D.load_model(m).eval()
        out = []
        with torch.no_grad():
            for x, y in data:
                xin = torch.tensor(x / (x.std() + 1e-9) * 0.1)[None, None]
                p = net(xin)[0, 0].numpy()
                out.append(coherence(p, y))
        rows[str(m)] = out
    for name, r in rows.items():
        r = np.array(r)
        print(f"{name[-60:]:60s} coherence 80-1k {r[:, 0].mean():.3f}  1-3k {r[:, 1].mean():.3f}  "
              f"3-8k {r[:, 2].mean():.3f}  (n {len(r)})")
    return rows


if __name__ == "__main__":
    main([pathlib.Path(a).expanduser() for a in sys.argv[1:]])
