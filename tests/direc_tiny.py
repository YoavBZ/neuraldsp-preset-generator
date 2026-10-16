"""A tiny synthetic run of `learn.direc.fit` on the CPU, for the bit-identity tests
(`docs/di-fine-structure-plan.md`, review R9). Not a test module itself.

`tiny_fit` builds a 16-row pair cache with short clips, patches the module's clip length,
the K3 folds and the bleed folder, runs `fit`, and returns a hash of the saved weights and the
validation lines it printed. The expected values in `tests/test_direc_fine.py` were recorded
with `learn/direc.py` as of commit a707033, before any experiment-4 change."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import pathlib

CLIP = 16384
CROP = 8192
ROWS = 16
BANDS = ("Band A", "Band B", "Band C", "Band D")


def make_cache(root: pathlib.Path):
    import numpy as np

    rng = np.random.default_rng(1234)
    root.mkdir(parents=True, exist_ok=True)
    t = np.arange(CLIP) / 48000
    X = np.zeros((ROWS, CLIP), np.int16)
    Y = np.zeros((ROWS, CLIP), np.int16)
    for i in range(ROWS):
        f0 = 80 + 40 * i
        di = np.sin(2 * np.pi * f0 * t) * np.exp(-((t * 6) % 1) * 4) + 0.05 * rng.standard_normal(CLIP)
        amp = np.tanh(4 * di)
        X[i] = np.clip(amp / np.abs(amp).max() * 0.9 * 32767, -32767, 32767)
        Y[i] = np.clip(di / np.abs(di).max() * 0.9 * 32767, -32767, 32767)
    np.save(root / "input.npy", X)
    np.save(root / "di.npy", Y)
    S = rng.standard_normal((ROWS, 4096 // 2 + 1)).astype(np.float32)
    np.save(root / "di_spectrum.npy", S)
    meta = [{"id": f"r{i}", "band": BANDS[i % 4]} for i in range(ROWS)]
    (root / "meta.json").write_text(json.dumps(meta))
    return root


def tiny_fit(tmp: pathlib.Path, monkeypatch, out_name="out", **kw):
    """(sha256 of the saved state dict or None, the printed validation lines)."""
    import torch

    from learn import direc as D
    from learn import train as TR

    torch.set_num_threads(1)
    cache = tmp / "cache"
    if not (cache / "meta.json").exists():
        make_cache(cache)
    monkeypatch.setattr(D, "CLIP", CLIP)
    monkeypatch.setattr(D, "CROP", CROP)
    monkeypatch.setattr(D, "CROPS", tmp / "no-crops")
    monkeypatch.setattr(TR, "k3_folds", lambda: ({b: i for i, b in enumerate(BANDS)}, {}))
    monkeypatch.setenv("DIREC_DEVICE", "cpu")
    out = tmp / out_name
    args = dict(minutes=1, seed=0, batch=2, log_every=3, steps=3, lr=3e-4, lr_end=2e-5)
    args.update(kw)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        D.fit(cache, 0, out, **args)
    h = None
    if (out / "fold0.pt").exists():                     # the calibrate and eval modes save none
        state = torch.load(out / "fold0.pt", map_location="cpu")
        h = hashlib.sha256()
        for k in sorted(state):
            h.update(k.encode())
            h.update(state[k].detach().cpu().numpy().tobytes())
    import re

    pat = re.compile(r"train (\S+) val (\S+) \(input-as-DI (\S+)\) skipped (\d+) gate (\S+)")
    lines = [" ".join(m.groups()) for m in map(pat.search, buf.getvalue().splitlines()) if m]
    return (h.hexdigest() if h else None), lines
