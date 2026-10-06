#!/usr/bin/env python3
"""Measure the "does not look like a guitar" check on real guitars and real basses.

    python research/calibrate_bass_window_check.py --json guitar-check.json

Positives: every development amp-track crop (`~/ndsp-presets/references/validation-crops`).
Negatives: every bass track (by name) in the sessions those crops come from, cut at the
same frames as the session's first crop, where it is not silent. Only sessions whose
every part is development material are read. Reports, for the floors in
`analysis/fingerprint.py`, how many guitars and basses the check flags, and the same for
the earlier either-or floors.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from _cli import guarded

BASS = re.compile(r"bass", re.I)
NOT_BASS = re.compile(r"vox|voc", re.I)        # a backing vocal named after the bassist


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--datasets-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/datasets"))
    ap.add_argument("--json", type=pathlib.Path)
    return ap


def measure(samples):
    from analysis import io
    from analysis.fingerprint import fingerprint

    f = fingerprint(io.from_samples(samples, 48000), regime="isolated_stem", excerpt_s=None)
    return (f.spectrum.get("centroid_hz") or {}).get("p50"), f.spectrum.get("hf_corner_hz")


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("calibrating the guitar check")
    import numpy as np
    import soundfile as sf

    from analysis import io
    from analysis.fingerprint import (BASS_CENTROID_UNDER_HZ, BASS_HF_CORNER_UNDER_HZ,
                                      Fingerprint)
    from benchmark_recordings import CATALOG

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    sessions = {(s["source"], s["song"]): s for s in catalog["sessions"]}
    crops = args.crops_dir.expanduser()
    guitars, basses, seen = [], [], set()
    for slug in sorted(os.listdir(crops)):
        record = json.loads((crops / slug / "record.json").read_text())
        key = (record["source"], record["song"])
        session = sessions[key]
        if record.get("split") != "development" or session.get("split") != "development":
            continue                                      # checked before any audio
        guitars.append({"part": slug, "m": measure(
            sf.read(str(crops / slug / "reference.wav"), dtype="float64")[0])})
        if key in seen:
            continue
        seen.add(key)
        a, b = record["excerpt_start_frame"], record["excerpt_end_frame"]
        for name in session["files"]:
            if not BASS.search(name) or NOT_BASS.search(name):
                continue
            x = io.load(args.datasets_dir.expanduser() / session["path"] / name).mono()
            cut = np.zeros(b - a)
            cut[: len(x[a:b])] = x[a:b]
            if np.sqrt(np.mean(cut ** 2)) >= 1e-4:
                basses.append({"session": "/".join(key), "track": name, "m": measure(cut)})

    def flagged(rows, rule):
        out = 0
        for r in rows:
            c, k = r["m"]
            if c is None or k is None:
                continue
            out += rule(c, k)
        return out

    def both(c, k):                                       # the shipped rule itself
        return Fingerprint(spectrum={"centroid_hz": {"p50": c},
                                     "hf_corner_hz": k})._implausible_for_guitar()
    either = lambda c, k: c < 250.0 or k < 500.0                                     # noqa: E731
    summary = {"guitars": len(guitars), "basses": len(basses),
               "thresholds": [BASS_CENTROID_UNDER_HZ, BASS_HF_CORNER_UNDER_HZ],
               "flagged_now": {"guitars": flagged(guitars, both), "basses": flagged(basses, both)},
               "flagged_by_either_250_500": {"guitars": flagged(guitars, either),
                                             "basses": flagged(basses, either)}}
    print(json.dumps(summary, indent=1))
    if args.json:
        args.json.write_text(json.dumps({**summary, "guitar_rows": guitars,
                                         "bass_rows": basses}, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
