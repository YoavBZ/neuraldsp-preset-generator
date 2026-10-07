"""Store float-WAV renders as level-normalised 24-bit FLAC, in place (the judge ignores
level; distances agree to 1e-7, measured 2026-10-07). Each FLAC is read back and checked
before its WAV is deleted.

    .venv/bin/python -m learn.compress_renders ~/ndsp-presets/learn/direc/phase2-set3 --workers 2
"""

import argparse
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor


def one(path):
    import numpy as np
    import soundfile as sf

    path = pathlib.Path(path)
    x, sr = sf.read(str(path), dtype="float64")
    peak = float(np.abs(x).max())
    scale = 0.99 / peak if peak > 0 else 1.0
    out = path.with_suffix(".flac")
    sf.write(str(out), x * scale, sr, subtype="PCM_24")
    y, _ = sf.read(str(out), dtype="float64")
    if y.shape != x.shape or float(np.abs(y - x * scale).max()) > 1e-6:
        out.unlink()
        return f"MISMATCH {path}"
    path.unlink()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    files = [str(p) for p in args.root.expanduser().rglob("*.wav")]
    print(f"{len(files)} WAVs under {args.root}", flush=True)
    with ProcessPoolExecutor(args.workers) as ex:
        bad = [r for r in ex.map(one, files, chunksize=64) if r]
    print(f"done; {len(bad)} mismatches", *bad[:5], sep="\n")


if __name__ == "__main__":
    main()
