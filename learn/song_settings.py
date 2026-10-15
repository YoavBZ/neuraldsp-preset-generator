"""Settings from a song (`docs/song-settings-plan.md`, ML plan step 3). Development only.

    .venv/bin/python -m learn.song_settings ks-convergence     # zero renders: K_S at 25/50/100/150
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import confirm_run as CR  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402

OUT = K.HOME / "learn/song-settings"
CHECKPOINTS = (25, 50, 100, 150)


def per_part(rows):
    """rows: (slug, band, gain_class, value) per cell and direction -> (band, gain_class, mean)."""
    by = {}
    for slug, band, cls, v in rows:
        by.setdefault((slug, band, cls), []).append(v)
    return [(b, c, statistics.fmean(v)) for (s, b, c), v in by.items()]


def ks_convergence():
    rows = {n: [] for n in CHECKPOINTS}
    for p in sorted((K.OUT / "cells").glob("*/*/result.json")):
        c = json.loads(p.read_text())
        for search, held in K.DIRECTIONS:
            run = c["runs"][search]
            if "skipped" in run:
                continue
            s_held = c["menu"][c["start"]][held]
            curve = run["K_S"]["curve"]
            for n in CHECKPOINTS:
                kh = curve[min(n, len(curve)) - 1][2]
                if math.isfinite(kh) and math.isfinite(s_held):
                    rows[n].append((c["slug"], c["band"], c["gain_class"], math.log(kh / s_held)))
    out = {}
    for n, r in rows.items():
        pp = per_part(r)
        out[n] = {g: CR.stats([(b, v) for b, c, v in pp if c in keep])
                  for g, keep in (("clean+crunch", ("clean", "crunch")), ("clean", ("clean",)), ("crunch", ("crunch",)))}
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "ks-convergence.json", out)
    for n, g in out.items():
        s = g["clean+crunch"]
        print(f"K_S@{n:3d} vs S: band-w {s['band_weighted_mean']:+.3f} part-w {s['mean']:+.3f} "
              f"90% [{s['lo90']:+.3f}, {s['hi90']:+.3f}] bands- {s['bands_negative']}/{s['bands']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("ks-convergence",))
    a = ap.parse_args(argv)
    {"ks-convergence": ks_convergence}[a.step]()


if __name__ == "__main__":
    main()
