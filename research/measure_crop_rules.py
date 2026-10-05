#!/usr/bin/env python3
"""How much of each development part's 10-s crop the part plays in, under each crop
rule, and how loud its amp track is where its DI is silent (bleed).

    python research/measure_crop_rules.py --json docs/validation-crop-rules.json

For every usable development part: the DI activity (2048-sample frames, hop 1024,
within 40 dB of the DI's loudest) of the window the first rule picks (gated loudness,
`build_validation_crops._window`) and of crop rule 2's (`_window_by_di`); and the
part's bleed, the median level of its amp track in the frames where its DI is more
than 60 dB under its loudest, less the median where the DI plays, over the whole
session (None where either has fewer than 50 frames; below about -100 dB the amp
track is digital silence there). Only sessions whose every part is development
material are read.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from _cli import guarded


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datasets-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/datasets"))
    ap.add_argument("--json", type=pathlib.Path)
    return ap


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("measuring crop rules")
    import numpy as np

    import build_validation_crops as B
    from analysis import io
    from benchmark_recordings import CATALOG

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    root = args.datasets_dir.expanduser()
    rate, frames = io.SAMPLE_RATE, 10 * io.SAMPLE_RATE
    parts = {}
    for s in catalog["sessions"]:
        splits = {s.get("split")} | {p.get("split") or s.get("split") for p in s["parts"]}
        if splits != {"development"}:
            continue                                      # checked before any audio
        for p in s["parts"]:
            if not p.get("usable"):
                continue
            di = io.load(root / s["path"] / p["di"]).mono().astype(np.float64)
            ref = B._fit(io.load(root / s["path"] / p["reference"]).mono(), len(di))
            ref = ref.astype(np.float64)
            ddb = io.frame_rms_db(di, 2048, 1024)
            playing = ddb >= ddb.max() - 40.0

            def activity(start):
                return float(np.mean(playing[start // 1024:(start + frames - 2048) // 1024 + 1]))

            first, _, _ = B._window(ref.astype(np.float32), rate)
            second, _, _, act = B._window_by_di(di, ref, rate)
            rdb = io.frame_rms_db(ref, 2048, 1024)
            k = min(len(ddb), len(rdb))
            silent = ddb[:k] < ddb.max() - 60.0
            bleed = (float(np.median(rdb[:k][silent]) - np.median(rdb[:k][playing[:k]]))
                     if silent.sum() >= 50 and playing[:k].sum() >= 50 else None)
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            parts[slug] = {"first_rule": {"start_s": first / rate, "di_activity": activity(first)},
                           "rule_2": {"start_s": second / rate, "di_activity": act},
                           "bleed_db": None if bleed is None else round(bleed, 2)}
            print(slug, parts[slug], flush=True)
    summary = {}
    for rule in ("first_rule", "rule_2"):
        v = [r[rule]["di_activity"] for r in parts.values()]
        summary[rule] = {"parts": len(v), "playing_half_or_more": sum(x >= 0.5 for x in v),
                         "playing_90_percent_or_more": sum(x >= 0.9 for x in v),
                         "median": statistics.median(v)}
    out = {"schema": "validation-crop-rules-1", "summary": summary, "parts": parts}
    print(json.dumps(summary, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
