#!/usr/bin/env python3
"""How close can each Morgan amp get to a recording, and what does a menu of all
three add? (`docs/amp-reach-plan.md`)

    python scripts/amp_reach.py --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --panel-dir ~/ndsp-presets/runs/kill/pr12 --panel-dir ~/ndsp-presets/runs/kill/ac20 \\
        --json amp-reach.json

K1's split-half oracle, per amp and over the three amps together: for every
development part whose DI plays in at least half of each half (1.0-5.5 s and
5.5-10 s) and whose recorded lag is clear, the factory preset closest to the amp track
on half A is scored on half B, under the judge (`aligned_distance`, both band sets, the
recorded lag less the 52-sample latency). Every factory preset of each amp is on the
menu; each amp's template with time effects off is a reference point.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import random
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

AMPS = ("ac20", "pr12", "sw50r")
BAND_SETS = ("recording", "union")
ADDS_REACH = math.log(0.9)          # the joint menu at least 10% closer than the best amp's
VARIES = 2 / 3                      # no amp holds the joint pick on more than this share
SUBSET, SUBSETS = 30, 50            # the size-matched reading: 30 presets per amp, 50 draws


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, action="append", required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=4)
    return ap


def oracle(d, menu, bands):
    """(the preset closest on half A, its half-B distance), or (None, None)."""
    scored = [c for c in menu if d.get(f"{c}|A|{bands}") is not None
              and d.get(f"{c}|B|{bands}") is not None]
    if not scored:
        return None, None
    best = min(scored, key=lambda c: (d[f"{c}|A|{bands}"], c))
    return best, d[f"{best}|B|{bands}"]


def part_row(d, menus, bands, rng):
    """One part's per-amp and joint oracles under one band set."""
    row = {}
    for amp in AMPS:
        pick, score = oracle(d, menus[amp], bands)
        row[amp] = {"pick": pick, "half_b": score,
                    "template_r": d.get(f"{amp}:template+R|B|{bands}")}
        sized = [oracle(d, rng.sample(menus[amp], min(SUBSET, len(menus[amp]))), bands)[1]
                 for _ in range(SUBSETS)]
        sized = [s for s in sized if s is not None]
        row[amp]["half_b_30_presets"] = statistics.mean(sized) if sized else None
    pick, score = oracle(d, [c for amp in AMPS for c in menus[amp]], bands)
    row["joint"] = {"pick": pick, "half_b": score,
                    "amp": None if pick is None else pick.split(":", 1)[0]}
    return row


def band_median(values_by_band):
    vals = [statistics.median(v) for v in values_by_band.values() if v]
    return statistics.median(vals) if vals else None


def summarise(rows):
    """The plan's statistics for one band set, from rows of {band, row}."""
    out = {}
    gain = {a: collections.defaultdict(list) for a in AMPS}
    for r in rows:
        j = r["row"]["joint"]["half_b"]
        for a in AMPS:
            s = r["row"][a]["half_b"]
            if j is not None and s is not None:
                gain[a][r["band"]].append(math.log(j / s))
    out["joint_vs_amp_band_median"] = {a: band_median(gain[a]) for a in AMPS}
    present = {a: v for a, v in out["joint_vs_amp_band_median"].items() if v is not None}
    best = max(present, key=present.get) if present else None
    out["best_single_amp"] = best
    out["joint_vs_best_amp"] = present.get(best)
    winners = collections.Counter(r["row"]["joint"]["amp"] for r in rows
                                  if r["row"]["joint"]["amp"])
    total = sum(winners.values())
    out["joint_pick_amp_share"] = {a: winners[a] / total for a in AMPS} if total else {}
    for a in AMPS:
        own = collections.defaultdict(list)
        sized = collections.defaultdict(list)
        for r in rows:
            x = r["row"][a]
            if x["half_b"] is not None and x["template_r"]:
                own[r["band"]].append(math.log(x["half_b"] / x["template_r"]))
            refs = [r["row"][b]["template_r"] for b in AMPS if r["row"][b]["template_r"]]
            if x["half_b_30_presets"] is not None and refs:
                sized[r["band"]].append(math.log(x["half_b_30_presets"] / min(refs)))
        out.setdefault("amp_vs_own_template", {})[a] = band_median(own)
        out.setdefault("amp_30_presets_vs_best_template", {})[a] = band_median(sized)
    return out


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("measuring amp reach")
    import kill_tests as K
    import kill_tests_judge as KJ
    from benchmark_recordings import CATALOG, lag_samples
    from plan_listening_validation import panel_files

    files, index_hashes = panel_files(args.panel_dir)
    names = sorted({c for d in files.values() for c in d})
    if sorted({c.split(":", 1)[0] for c in names}) != list(AMPS):
        die("pass the three Morgan panels")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    meta = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            meta[slug] = {"band": s.get("group") or f"{s['source']}/{s['song']}",
                          "split": p.get("split") or s.get("split")}
    if any(p not in meta or meta[p]["split"] != "development" for p in files):
        die("a panel holds a part the catalogue does not list as development")
    crops = args.crops_dir.expanduser()
    menus = {a: [c for c in names if c.startswith(f"{a}:factory:")] for a in AMPS}
    used = [c for a in AMPS for c in menus[a]] + [f"{a}:template+R" for a in AMPS]
    parts, no_lag = [], []
    for p in sorted(files):
        di = K.mono(crops / p / "di.wav")
        if not all(K.active_fraction(di, *K.HALVES[h]) >= 0.5 for h in ("A", "B")):
            continue
        if lag_samples(p) is None:
            no_lag.append(p)
            continue
        parts.append(p)
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(args.workers) as ex:
        scored = dict(ex.map(KJ.score_part, [(p, {c: files[p][c] for c in used},
                                              lag_samples(p) - K.LATENCY, crops)
                                             for p in parts]))
    readings, rows_out = {}, {}
    for bands in BAND_SETS:
        rows = []
        for p in parts:
            rng = random.Random(f"{p}|{bands}")
            rows.append({"part": p, "band": meta[p]["band"],
                         "row": part_row(scored[p]["d"], menus, bands, rng)})
        readings[bands] = summarise(rows)
        rows_out[bands] = rows
    default = readings["recording"]
    adds = all(readings[b]["joint_vs_best_amp"] is not None
               and readings[b]["joint_vs_best_amp"] <= ADDS_REACH for b in BAND_SETS)
    varies = bool(default["joint_pick_amp_share"]) and max(
        default["joint_pick_amp_share"].values()) <= VARIES
    out = {"panels": index_hashes, "menu_sizes": {a: len(m) for a, m in menus.items()},
           "parts": parts, "parts_without_clear_lag": no_lag,
           "joint_menu_adds_reach": adds, "best_amp_varies": varies,
           "rerun_kill_tests_jointly": adds or varies,
           "readings": readings, "rows": rows_out,
           "refused": {p: s["refused"] for p, s in scored.items() if s["refused"]},
           "distances": {p: s["d"] for p, s in scored.items()}}
    print(json.dumps({k: v for k, v in out.items() if k not in ("rows", "distances")},
                     indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out) + "\n")


if __name__ == "__main__":
    guarded(main)
