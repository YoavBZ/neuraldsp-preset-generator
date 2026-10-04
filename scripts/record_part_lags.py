#!/usr/bin/env python3
"""Record one DI-to-amp-track lag per development part, measured on the panel's renders.

    python scripts/record_part_lags.py --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --json docs/validation-lags.json

The catalogue's `lag_ms` (`docs/validation-datasets.json`) comes from 10-ms envelopes,
so it is quantised to 10 ms and off by 2.5 ms or more on about one part in five. Here
each part's lag is `analysis.aligned.estimate_lag` pooled over every render of the part
in the panel, within ±15 ms of the catalogued lag less the plugin's latency (±50 ms
where that is refused), then expressed DI-to-amp-track by adding the latency back. Its
stability is measured too: the same estimate pooled over five random sets of nine of
the part's renders; a spread over 0.5 ms marks the lag ambiguous (the correlation has
two peaks), and the whole-panel value is still recorded. Held-out parts are never
opened. `lag_samples(part)` in `benchmark_recordings.py` reads the file.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

SR = 48000
LATENCY = 52            # Morgan's latency in samples: a render lags its DI by this
SUBSETS, SUBSET_SIZE, AMBIGUOUS_MS = 5, 9, 0.5


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path, required=True)
    ap.add_argument("--workers", type=int, default=3)
    return ap


def pooled_lag(ref, renders, hint):
    """(render lag, search half-width in ms): ±15 ms around the hint, else ±50 ms."""
    from analysis.aligned import estimate_lag

    for width in (0.015, 0.05):
        try:
            return estimate_lag(ref, renders, hint=hint, max_lag_s=width), width * 1000
        except ValueError:
            continue
    return None, None


def measure(job):
    part, files, catalogued, crops = job
    import soundfile as sf

    def mono(path):
        x, rate = sf.read(str(path), dtype="float64")
        assert rate == SR
        return x.mean(axis=1) if x.ndim == 2 else x

    ref = mono(crops / part / "reference.wav")
    names = sorted(files)
    renders = {n: mono(files[n]) for n in names}
    hint = catalogued - LATENCY
    lag, width = pooled_lag(ref, list(renders.values()), hint)
    rng = random.Random(part)                  # the subsets are fixed by the part's name
    subsets = []
    for _ in range(SUBSETS):
        pick = rng.sample(names, min(SUBSET_SIZE, len(names)))
        subsets.append(pooled_lag(ref, [renders[n] for n in pick], hint)[0])
    found = [s for s in subsets if s is not None]
    spread = (max(found) - min(found)) / SR * 1000 if found else None
    row = {"lag_samples": None if lag is None else lag + LATENCY,
           "search_ms": width, "renders": len(names),
           "catalogue_lag_samples": catalogued,
           "subset_lags": [None if s is None else s + LATENCY for s in subsets],
           "subset_spread_ms": None if spread is None else round(spread, 3),
           "ambiguous": spread is None or spread > AMBIGUOUS_MS}
    print(f"{part}: {row['lag_samples']} (catalogue {catalogued}); spread {row['subset_spread_ms']} ms",
          flush=True)
    return part, row


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("recording part lags")
    from benchmark_recordings import CATALOG

    panel = args.panel_dir.expanduser()
    crops = args.crops_dir.expanduser()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    meta = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            meta[slug] = {"split": p.get("split") or s.get("split"),
                          "lag": int(round((p.get("lag_ms") or 0) * SR / 1000))}
    index = json.loads((panel / "index.json").read_text())
    files = {}
    for row in index["rows"]:
        if "file" in row:
            files.setdefault(row["part"], {})[row["candidate"]] = pathlib.Path(row["file"])
    held_out = [p for p in files if meta[p]["split"] != "development"]
    if held_out:
        die(f"the panel holds parts that are not development material: {held_out}")
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(args.workers) as ex:
        lags = dict(ex.map(measure, [(p, files[p], meta[p]["lag"], crops)
                                     for p in sorted(files)]))
    document = {
        "schema": "validation-lags-1",
        "meaning": "lag_samples: samples the part's amp track lags its DI at 48 kHz "
                   "(recording[t] ~ di[t - lag_samples])",
        "method": "analysis.aligned.estimate_lag pooled over the part's panel renders, "
                  "±15 ms around the catalogued lag less 52 samples (±50 ms if refused), "
                  "plus 52; stability from five random nine-render subsets",
        "panel": str(args.panel_dir), "latency_samples": LATENCY, "parts": lags}
    args.json.expanduser().write_text(json.dumps(document, indent=1) + "\n")
    ambiguous = [p for p, r in lags.items() if r["ambiguous"]]
    print(f"{len(lags)} parts; ambiguous: {ambiguous}")


if __name__ == "__main__":
    guarded(main)
