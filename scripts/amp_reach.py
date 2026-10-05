#!/usr/bin/env python3
"""How close can each Morgan amp get to a recording, and what does a menu of all
three add? (`docs/amp-reach-plan.md`)

    python scripts/amp_reach.py --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --panel-dir ~/ndsp-presets/runs/kill/pr12 --panel-dir ~/ndsp-presets/runs/kill/ac20 \\
        --json amp-reach.json

K1's split-half oracle: for every development part whose DI plays in at least half of
each half (1.0-5.5 s and 5.5-10 s) and whose recorded lag is clear, the preset closest
to the amp track on half A is scored on half B, under the judge (`aligned_distance`,
both band sets, the recorded lag less the 52-sample latency). The two menus the kill
tests were given (all 44 SW50R factory presets; PR12's 21 clean ones) are each compared
with a joint menu drawn from all three amps: the same size, and in full.
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
ADDS_REACH = math.log(0.9)      # a size-matched joint menu at least 10% closer
CLEAR = 0.150                   # the judge's validated cut, per part
MINORITY, MIN_BANDS = 1 / 3, 3  # another amp clearly closer on a third of parts, 3 bands
DRAWS = 200
# Exact canaries: the earlier kill tests' K1 under the judge, on the same 25 parts.
CANARIES = {("sw50r", "all"): {"recording": -0.3888, "union": -0.3280},
            ("pr12", "clean"): {"recording": -0.2670, "union": -0.2064}}


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, action="append", required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=4)
    return ap


def scored(d, menu, bands):
    return [c for c in menu if d.get(f"{c}|A|{bands}") is not None
            and d.get(f"{c}|B|{bands}") is not None]


def oracle(d, menu, bands):
    """(the preset closest on half A, its half-B distance), or (None, None)."""
    menu = scored(d, menu, bands)
    if not menu:
        return None, None
    best = min(menu, key=lambda c: (d[f"{c}|A|{bands}"], c))
    return best, d[f"{best}|B|{bands}"]


def joint_sized(d, menus, bands, size, rng):
    """The mean half-B distance of the oracle over `size` presets drawn evenly from the
    three amps' menus (the remainder going to the amps in order), over DRAWS draws."""
    pools = {a: scored(d, menus[a], bands) for a in AMPS}
    shares = {a: size // 3 + (i < size % 3) for i, a in enumerate(AMPS)}
    if any(len(pools[a]) < shares[a] for a in AMPS):
        return None
    out = []
    for _ in range(DRAWS):
        menu = [c for a in AMPS for c in rng.sample(pools[a], shares[a])]
        out.append(oracle(d, menu, bands)[1])
    return statistics.mean(out)


def band_median(rows, key):
    by = collections.defaultdict(list)
    for r in rows:
        if r.get(key) is not None:
            by[r["band"]].append(r[key])
    vals = [statistics.median(v) for v in by.values()]
    return (statistics.median(vals) if vals else None), len(by), sum(map(len, by.values()))


def comparison(parts, meta, dist, menus, tested, bands, seeds):
    """The decision readings for one tested menu (an amp's menu in `menus`) against the
    joint menus drawn from all three, under one band set."""
    size = len(menus[tested])
    rows = []
    for p in parts:
        d = dist[p]
        _, own = oracle(d, menus[tested], bands)
        pick, full = oracle(d, [c for a in AMPS for c in menus[a]], bands)
        sized = joint_sized(d, menus, bands, size, random.Random(seeds[p]))
        template = d.get(f"{tested}:template+R|B|{bands}")
        rows.append({
            "part": p, "band": meta[p]["band"], "joint_pick": pick,
            "sized_gain": (None if own is None or sized is None else math.log(sized / own)),
            "full_gain": (None if own is None or full is None else math.log(full / own)),
            "other_amp_clearly_closer": (pick is not None and own is not None
                                         and not pick.startswith(f"{tested}:")
                                         and math.log(full / own) <= -CLEAR),
            "own_vs_template": (None if own is None or not template
                                else math.log(own / template))})
    sized, bands_n, parts_n = band_median(rows, "sized_gain")
    full, _, _ = band_median(rows, "full_gain")
    own_k1, k1_bands, k1_parts = band_median(rows, "own_vs_template")
    clearly = [r for r in rows if r["other_amp_clearly_closer"]]
    return {"menu_size": size, "parts": parts_n, "bands": bands_n,
            "sized_joint_vs_tested": sized, "full_joint_vs_tested": full,
            "other_amp_clearly_closer_parts": len(clearly),
            "other_amp_clearly_closer_bands": len({r["band"] for r in clearly}),
            "tested_vs_own_template": own_k1, "k1_parts": k1_parts, "k1_bands": k1_bands,
            "rows": rows}


def verdict(readings):
    """{tested menu: reasons the joint menu adds reach}, from both band sets."""
    out = {}
    for key, by_bands in readings.items():
        reasons = []
        if all(r["sized_joint_vs_tested"] is not None
               and r["sized_joint_vs_tested"] <= ADDS_REACH for r in by_bands.values()):
            reasons.append("a size-matched joint menu is at least 10% closer")
        if all(r["parts"] and r["other_amp_clearly_closer_parts"] >= MINORITY * r["parts"]
               and r["other_amp_clearly_closer_bands"] >= MIN_BANDS
               for r in by_bands.values()):
            reasons.append("another amp is clearly closer on a third of the parts")
        out[key] = reasons
    return out


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("measuring amp reach")
    import kill_tests as K
    import kill_tests_judge as KJ
    from benchmark_recordings import CATALOG, lag_samples
    from plan_listening_validation import high_gain, panel_files

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
    every = {a: [c for c in names if c.startswith(f"{a}:factory:")] for a in AMPS}
    clean = {a: [c for c in every[a] if not high_gain(c)] for a in AMPS}
    used = [c for a in AMPS for c in every[a]] + [f"{a}:template+R" for a in AMPS]
    parts, no_lag, quiet = [], [], []
    for p in sorted(files):
        di = K.mono(crops / p / "di.wav")
        if not all(K.active_fraction(di, *K.HALVES[h]) >= 0.5 for h in ("A", "B")):
            quiet.append(p)
        elif lag_samples(p) is None:
            no_lag.append(p)
        else:
            parts.append(p)
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(args.workers) as ex:
        scored_parts = dict(ex.map(KJ.score_part, [(p, {c: files[p][c] for c in used},
                                                    lag_samples(p) - K.LATENCY, crops)
                                                   for p in parts]))
    dist = {p: s["d"] for p, s in scored_parts.items()}
    seeds = {p: p for p in parts}             # the same draws under both band sets
    readings = {("sw50r", "all"): {}, ("pr12", "clean"): {}, ("ac20", "all"): {}}
    for bands in BAND_SETS:
        readings[("sw50r", "all")][bands] = comparison(parts, meta, dist, every, "sw50r",
                                                       bands, seeds)
        readings[("pr12", "clean")][bands] = comparison(parts, meta, dist, clean, "pr12",
                                                        bands, seeds)
        readings[("ac20", "all")][bands] = comparison(parts, meta, dist, every, "ac20",
                                                      bands, seeds)
    misses = {f"{a}/{m}/{b}": (readings[(a, m)][b]["tested_vs_own_template"], want)
              for (a, m), by in CANARIES.items() for b, want in by.items()
              if readings[(a, m)][b]["tested_vs_own_template"] is None
              or round(readings[(a, m)][b]["tested_vs_own_template"], 4) != want}
    decided = {f"{a}/{m}": reasons for (a, m), reasons in
               verdict({k: v for k, v in readings.items() if k != ("ac20", "all")}).items()}
    # Reported: the joint pick's amp, against the share menu size alone would give.
    shares = {}
    for menu_name, menus in (("all", every), ("clean", clean)):
        for bands in BAND_SETS:
            picks = collections.Counter(
                oracle(dist[p], [c for a in AMPS for c in menus[a]], bands)[0].split(":")[0]
                for p in parts
                if oracle(dist[p], [c for a in AMPS for c in menus[a]], bands)[0])
            n = sum(len(menus[a]) for a in AMPS)
            shares[f"{menu_name}/{bands}"] = {
                a: {"share": picks[a] / max(sum(picks.values()), 1),
                    "menu_size_share": len(menus[a]) / n} for a in AMPS}
    out = {"panels": index_hashes,
           "menus": {"all": {a: len(every[a]) for a in AMPS},
                     "clean": {a: len(clean[a]) for a in AMPS}},
           "parts": parts, "parts_without_clear_lag": no_lag,
           "parts_with_a_quiet_half": quiet,
           "canary_misses": misses, "adds_reach": decided,
           "rerun_kill_tests_jointly": (not misses) and any(decided.values()),
           "joint_pick_amp_shares": shares,
           "readings": {f"{a}/{m}": {b: {k: v for k, v in r.items() if k != "rows"}
                                     for b, r in by.items()}
                        for (a, m), by in readings.items()},
           "rows": {f"{a}/{m}": {b: r["rows"] for b, r in by.items()}
                    for (a, m), by in readings.items()},
           "refused": {p: s["refused"] for p, s in scored_parts.items() if s["refused"]},
           "distances": dist}
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("rows", "distances", "parts")}, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out) + "\n")
    if misses:
        die(f"the canaries do not reproduce the earlier K1: {misses}")


if __name__ == "__main__":
    guarded(main)
