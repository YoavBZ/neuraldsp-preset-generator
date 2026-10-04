#!/usr/bin/env python3
"""Which automatic 20-s window holds the guitar, on a full song?

    python scripts/measure_excerpt_window_rules.py --json window-rules.json

Songs: every development multitrack session of Cambridge and Telefunken, its tracks
summed at their recorded levels into a rough mix, less the guitar DIs (a bass DI or a
keyboard's direct output is part of the sound and stays). Truth: a guitar part is in a
window when its amp track is active (`io.active_frames`, 45 dB under its own loudest
frame) in at least half the window's frames. Rules compared: the earliest of the
windows tied for activity (the old choice), the middle one of them (`excerpt_selection`
now), the song's midpoint, and two band rankings over active frames (300 Hz-3 kHz over
40-250 Hz; and over the louder of 40-250 Hz and 3-8 kHz). Only sessions whose every
part is development material are read.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import guarded

SECONDS = 20.0
GUITAR_DI = re.compile(r"(gtr|guitar).*di([ _.\d-]|$)|elecgtr.*di\.wav$", re.I)


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datasets-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/datasets"))
    ap.add_argument("--json", type=pathlib.Path)
    return ap


def band_db(x, sr, lo, hi):
    """Per-frame level in dB of the lo-hi Hz band, on the activity gate's frames."""
    import numpy as np

    from analysis import io

    n = io.FRAME
    count = 1 + (len(x) - n) // io.HOP
    keep = (np.fft.rfftfreq(n, 1 / sr) >= lo) & (np.fft.rfftfreq(n, 1 / sr) < hi)
    window, out = np.hanning(n), np.empty(count)
    for s in range(0, count, 4096):
        idx = np.arange(n)[None, :] + io.HOP * np.arange(s, min(s + 4096, count))[:, None]
        spec = np.abs(np.fft.rfft(x[idx] * window, axis=1)) ** 2
        out[s:s + 4096] = 10 * np.log10(spec[:, keep].sum(axis=1) + 1e-12)
    return out


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("measuring excerpt window rules")
    import numpy as np

    from analysis import io
    from benchmark_recordings import CATALOG

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    root = args.datasets_dir.expanduser()
    rows = []
    for s in catalog["sessions"]:
        splits = {s.get("split")} | {p.get("split") or s.get("split") for p in s["parts"]}
        if splits != {"development"} or s["source"] == "guitar-techs":
            continue                                      # checked before any audio
        dis = {p["di"] for p in s["parts"] if p.get("di")}
        mix, sr = None, None
        for name in s["files"]:
            if name in dis or GUITAR_DI.search(name):
                continue
            audio = io.load(root / s["path"] / name)
            if sr is not None and audio.sample_rate != sr:
                raise SystemExit(f"{s['path']}/{name} is at {audio.sample_rate} Hz")
            sr, x = audio.sample_rate, audio.mono()
            mix = x.copy() if mix is None else (
                np.pad(mix, (0, max(0, len(x) - len(mix))))
                + np.pad(x, (0, max(0, len(mix) - len(x)))))
        span = int(SECONDS * sr) // io.HOP
        active = io.active_frames(mix).astype(float)
        density = np.convolve(active, np.ones(span), mode="valid")
        tied = np.flatnonzero(density >= density.max() - 0.5)
        mid, low, high = (band_db(mix, sr, a, b) for a, b in ((300, 3000), (40, 250),
                                                              (3000, 8000)))

        def ranked(score):
            score = np.where(active[:len(score)] > 0, np.clip(score, -30, 30), -30)
            return int(np.argmax(np.convolve(score, np.ones(span) / span, mode="valid")))

        starts = {"earliest of the tie": int(tied[0]),
                  "middle of the tie (shipped)":
                      io.excerpt_selection(io.from_samples(mix, sr), SECONDS).start // io.HOP,
                  "song midpoint": (len(density) - 1) // 2,
                  "300 Hz-3 kHz over 40-250 Hz": ranked(mid - low),
                  "...over the louder of 40-250 Hz and 3-8 kHz": ranked(mid - np.maximum(low, high))}
        parts = {p["part"]: io.active_frames(io.load(root / s["path"] / p["reference"]).mono())
                 for p in s["parts"]}
        for rule, start in starts.items():
            rows.append({"song": f"{s['source']}/{s['song']}", "rule": rule,
                         "start_s": round(start * io.HOP / sr, 2),
                         "tie_share": round(len(tied) / len(density), 3),
                         "active_share": {k: round(float(a[start:start + span].mean()), 3)
                                          for k, a in parts.items()}})
        print(s["song"], {r: round(st * io.HOP / sr) for r, st in starts.items()}, flush=True)
    summary = {}
    for rule in dict.fromkeys(r["rule"] for r in rows):
        mine = [r for r in rows if r["rule"] == rule]
        shares = [v for r in mine for v in r["active_share"].values()]
        summary[rule] = {"parts_in": sum(v >= 0.5 for v in shares), "parts": len(shares),
                         "songs_with_one_in": sum(any(v >= 0.5 for v in r["active_share"].values())
                                                  for r in mine), "songs": len(mine)}
    print(json.dumps(summary, indent=1))
    if args.json:
        args.json.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
