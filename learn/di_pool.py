"""The DI windows renders are made from, each tagged with its band.

Sources: every set-2 *development* session's DI tracks (13 bands; held-out sessions and
set 1 are never read) and Guitar-TECHS P1's direct-input chords and scales (one more
player, CC BY 4.0). A window is 8 s: 2 s of pre-roll that flushes the reused plugin
instance's history, then 6 s kept. It is used when the DI plays in at least 70% of the
kept frames (within 40 dB of the track's loudest frame and above −60 dBFS).

    python -m learn.di_pool --out ~/ndsp-presets/learn/poc/di-windows.json
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
DATASETS = pathlib.Path(os.path.expanduser("~/ndsp-presets/references/datasets"))
SR = 48000
PRE, KEEP, HOP = 2.0, 6.0, 4.0


def tracks():
    """(band, path) for every DI the POC may render from."""
    catalog = json.loads((PLUGIN_ROOT / "docs" / "validation-datasets.json").read_text())
    out = []
    for s in catalog["sessions"]:
        if s["split"] != "development" or s.get("set", 1) != 2:
            continue
        for p in s["parts"]:
            if p.get("di"):
                out.append((s["group"], DATASETS / s["path"] / p["di"]))
    gt = DATASETS / "guitar-techs" / "P1-downloads"
    for sub in ("P1_chords", "P1_scales"):
        for f in sorted((gt / sub / "audio" / "directinput").glob("*.wav")):
            out.append(("Guitar-TECHS P1", f))
    seen, unique = set(), []
    for band, f in out:
        if f not in seen:
            seen.add(f)
            unique.append((band, f))
    return unique


def windows(band, path):
    import numpy as np
    import pyloudnorm
    import soundfile as sf
    from scipy.signal import resample_poly

    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        g = np.gcd(SR, sr)
        x = resample_poly(x, SR // g, sr // g).astype(np.float32)
    n, hop = 2048, 1024
    frames = max(1, 1 + (len(x) - n) // hop)
    idx = np.arange(n)[None, :] + hop * np.arange(frames)[:, None]
    idx = np.minimum(idx, len(x) - 1)
    db = 10 * np.log10(np.mean(x[idx] ** 2, axis=1) + 1e-20)
    active = (db >= db.max() - 40) & (db >= -60)
    meter = pyloudnorm.Meter(SR)
    out = []
    start = 0.0
    total = len(x) / SR
    while start + PRE + KEEP <= total:
        a, b = int((start + PRE) * SR / hop), int((start + PRE + KEEP) * SR / hop)
        frac = float(active[a:b].mean()) if b > a else 0.0
        if frac >= 0.7:
            kept = x[int((start + PRE) * SR):int((start + PRE + KEEP) * SR)]
            lufs = float(meter.integrated_loudness(kept.astype(np.float64)))
            if np.isfinite(lufs):
                out.append({"band": band, "file": str(path), "start_s": round(start, 3),
                            "active": round(frac, 3), "lufs": round(lufs, 2)})
        start += HOP
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    args = ap.parse_args()
    rows = []
    for band, f in tracks():
        w = windows(band, f)
        print(f"{band:32s} {f.name:40s} {len(w)}", file=sys.stderr)
        rows.extend(w)
    out = args.out.expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"pre_s": PRE, "keep_s": KEEP, "windows": rows}, indent=0))
    from collections import Counter
    print(Counter(r["band"] for r in rows))


if __name__ == "__main__":
    main()
