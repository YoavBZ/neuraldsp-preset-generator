"""The transfer curve of a render: what the preset did to its DI's long-term spectrum.

T(θ) = long-term log-mel of the render − that of its DI, over the frames where the DI
plays, in the judge's 64 bands (50 Hz–16 kHz, `analysis/aligned.py`), with the mean
over bands removed (level is not a tone). For a clean preset it is nearly independent
of the DI, and the difference between a render's T and a recording's T is what the
judge's tonal part measures when both play the same DI.

    .venv/bin/python -m learn.transfer --renders ~/ndsp-presets/learn/poc/renders \\
        --cache ~/ndsp-presets/learn/poc/cache
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

SR = 48000
N_FFT = 2048


def long_term(x, active=None):
    """(64-band long-term dB, frame activity) of a 48 kHz mono signal."""
    import numpy as np

    from analysis.aligned import _frame_db, _logmel

    mel, _ = _logmel(np.asarray(x, np.float64), N_FFT, SR)
    if active is None:
        db = _frame_db(np.asarray(x, np.float64), N_FFT)
        active = db >= db.max() - 40
    n = min(len(mel), len(active))
    power = (10 ** (mel[:n][active[:n]] / 10)).mean(axis=0)
    return 10 * np.log10(power + 1e-12), active


def transfer(render, di):
    """Mean-removed T, scored over the DI's active frames."""
    d, active = long_term(di)
    r, _ = long_term(render, active)
    t = r - d
    return t - t.mean()


def main():
    import numpy as np
    import soundfile as sf

    from analysis import io

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--renders", type=pathlib.Path, required=True)
    ap.add_argument("--cache", type=pathlib.Path, required=True)
    args = ap.parse_args()
    renders, cache = args.renders.expanduser(), args.cache.expanduser()
    meta = json.loads((cache / "meta.json").read_text())
    rows = {}
    for f in renders.glob("index-w*.jsonl"):
        for line in f.read_text().splitlines():
            if line:
                r = json.loads(line)
                rows[r["id"]] = r
    order = sorted(range(len(meta)), key=lambda i: (rows[meta[i]["id"]]["file"], i))
    T = np.zeros((len(meta), 64), np.float32)
    current, x = None, None
    for n, i in enumerate(order):
        r = rows[meta[i]["id"]]
        if r["file"] != current:
            current, x = r["file"], np.asarray(io.load(r["file"]).mono(), np.float64)
        a = int((r["start_s"] + 2.0) * SR)
        di = x[a:a + 6 * SR]
        y, sr = sf.read(str(renders / f"{r['id']}.flac"), dtype="float64")
        T[i] = transfer(y[:len(di)], di)
        if n % 2000 == 0:
            print(f"transfer {n}/{len(meta)}", flush=True)
    np.save(cache / "transfer.npy", T)
    print(f"saved {T.shape}; mean |T| {np.abs(T).mean():.2f} dB, spread {np.abs(T - T.mean(0)).mean():.2f} dB")


if __name__ == "__main__":
    main()
