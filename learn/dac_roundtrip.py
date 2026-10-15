"""Step 0c of experiment 4 (docs/di-fine-structure-plan.md): the DAC ceiling check's round trips.

Runs in the DAC interpreter (Python 3.9, torch 2.8, descript-audio-codec, MIT), on the CPU, and
imports nothing from this project. It reads each cell's measure DI (48 kHz, written by
`learn.di_fine_structure dac-prep`) and writes, at 48 kHz and the input's length:

- `<tag>-q4.npy`, `<tag>-q9.npy`: the 44-kHz DAC round trip with 4 and 9 codebooks;
- `<tag>-rs.npy`: the resample-only control (48 → 44.1 → 48 kHz, no DAC);
- `shift.json`: the shift stability of the post-quantisation `z` (9 codebooks) under 1–8-sample
  delays: the mean cosine similarity of each frame's z with the undelayed z.

    ~/ndsp-presets/tools/dac-venv/bin/python learn/dac_roundtrip.py \\
        --inp ~/ndsp-presets/learn/di-fine-structure/dac/in --out ~/ndsp-presets/learn/di-fine-structure/dac/out

Resampling happens only around the model (the ML plan's 48-kHz rule).
"""

import argparse
import json
import pathlib

SR = 48000
DAC_SR = 44100
CODEBOOKS = (4, 9)
SHIFTS = tuple(range(1, 9))
WEIGHTS = pathlib.Path("~/.cache/descript/dac/weights_44khz_8kbps_0.0.1.pth").expanduser()  # as E0/E0b


def to44(x):
    from scipy.signal import resample_poly

    return resample_poly(x, 147, 160)


def to48(x, n):
    import numpy as np
    from scipy.signal import resample_poly

    y = resample_poly(x, 160, 147)[:n]
    return np.pad(y, (0, n - len(y))) if len(y) < n else y


def encode(model, x44, n_q):
    """(post-quantisation z, decoded 44.1-kHz audio) for one mono signal."""
    import torch

    with torch.no_grad():
        t = torch.tensor(x44, dtype=torch.float32)[None, None]
        t = model.preprocess(t, DAC_SR)
        z = model.encode(t, n_quantizers=n_q)[0]
        y = model.decode(z)[0, 0].numpy()
    return z[0].numpy(), y


def main():
    import numpy as np
    import torch

    import dac

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inp", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    inp, out = a.inp.expanduser(), a.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    if not WEIGHTS.exists():
        raise SystemExit(f"no DAC weights at {WEIGHTS}; downloading them needs the user's yes")
    model = dac.DAC.load(str(WEIGHTS)).eval()
    shift = {}
    for f in sorted(inp.glob("*.npy")):
        tag = f.stem
        x = np.load(f).astype(np.float64)
        n = len(x)
        peak = float(np.abs(x).max()) + 1e-12
        x44 = to44(x / peak * 0.5)                       # DAC's input range; level is restored below
        np.save(out / f"{tag}-rs.npy", to48(x44, n) / 0.5 * peak)
        for q in CODEBOOKS:
            if (out / f"{tag}-q{q}.npy").exists():
                continue
            _, y = encode(model, x44, q)
            np.save(out / f"{tag}-q{q}.npy", to48(y[:len(x44)], n) / 0.5 * peak)
        z0, _ = encode(model, x44, 9)
        sims = {}
        for d in SHIFTS:
            zd, _ = encode(model, np.concatenate([np.zeros(d), x44])[:len(x44)], 9)
            k = min(z0.shape[1], zd.shape[1])
            num = (z0[:, :k] * zd[:, :k]).sum(0)
            den = np.linalg.norm(z0[:, :k], axis=0) * np.linalg.norm(zd[:, :k], axis=0) + 1e-12
            sims[str(d)] = float((num / den).mean())
        shift[tag] = sims
        print(tag, {d: round(v, 3) for d, v in sims.items()}, flush=True)
    (out / "shift.json").write_text(json.dumps(shift, indent=1))


if __name__ == "__main__":
    main()
