"""E1's DAC helper at inference (`learn/egvae_e1.py`, `rebuild` and `evaluate`). Run with the
DAC venv, which can't import `learn`; the two halves meet only through files in DIR.

    $DAC_PY learn/egvae_e1_codec.py encode DIR [DEVICE]   # DIR/NAME.in44.npy -> DIR/NAME.codes.npy
    $DAC_PY learn/egvae_e1_codec.py decode DIR [DEVICE]   # DIR/NAME.pred.npy -> DIR/NAME.out44.npy

`encode` is the E1 data encoder's own path (`egvae_e1_dac.normalise` and `encode`: −16 LUFS as
DAC's `compress`, padding on, all 9 codebooks), one signal at a time: a 1-D float32 signal at
44.1 kHz becomes (9, frames) int16 codes. `decode` takes (n, frames) int16 codes (E1 predicts
n = 4) through `quantizer.from_codes` and `decode`, as `decompress` does for one unchunked
window, and writes float32 at 44.1 kHz (frames × 512 samples; the caller trims). DAC's
loudness restore is not applied: the caller sets the level. Files already done are skipped.
Default device: CPU (equal codes to MPS, `e1-codes/mps-check.json`).
"""

import pathlib
import sys

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import egvae_e1_dac as E  # noqa: E402


def encode(root, device="cpu"):
    model = E.load_model(device)
    for f in sorted(root.glob("*.in44.npy")):
        out = f.with_name(f.name.replace(".in44.npy", ".codes.npy"))
        if out.exists():
            continue
        sig, _ = E.normalise(np.load(f).astype(np.float32)[None])
        np.save(out, E.encode(model, sig, device)[0])
        print(out.name, flush=True)


def decode(root, device="cpu"):
    model = E.load_model(device)
    for f in sorted(root.glob("*.pred.npy")):
        out = f.with_name(f.name.replace(".pred.npy", ".out44.npy"))
        if out.exists():
            continue
        c = torch.from_numpy(np.load(f).astype(np.int64))[None].to(device)
        z = model.quantizer.from_codes(c)[0]
        np.save(out, model.decode(z)[0, 0].cpu().numpy().astype(np.float32))
        print(out.name, flush=True)


if __name__ == "__main__":
    {"encode": encode, "decode": decode}[sys.argv[1]](pathlib.Path(sys.argv[2]).expanduser(), *sys.argv[3:4])
