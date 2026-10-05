#!/usr/bin/env python3
"""Score the song-only shortlists against the factory panels (`docs/song-only-shortlist-plan.md`).

    python scripts/score_shortlists.py --renders ~/ndsp-presets/runs/shortlists/renders \\
        --reach-json ~/ndsp-presets/runs/kill/amp-reach.json --json shortlists.json

Scores every render `render_shortlists.py` made with the judge (half A, half B and
1.0-10 s; both band sets; the recorded lag less the 52-sample latency), checks the
canaries, and compares the arms. One preset's distance is the mean of its half-A and
half-B distances. A list's, as a perfect ear would pick, is the preset chosen on one
half scored on the other, both directions averaged; random-4's is the exact
expectation over every 4-preset subset of the 108 factory presets. A comparison passes
when, under both band sets, the median of band medians of its log ratio is at most
log 0.9 and the first arm is closer on more than half the parts.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import pathlib
import statistics
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

BAND_SETS = ("recording", "union")
AMPS = ("ac20", "pr12", "sw50r")
PASS = math.log(0.9)
CLEAR = 0.150
REPRO, DRIFT_DB = 0.01, 0.1
G = [f"G{i}" for i in range(1, 5)]
F = [f"F{i}" for i in range(1, 5)]
DECIDING = {"D1": ("G1", "template+R"), "D2": ("G4", "random-4"), "D3": ("F4", "random-4")}
REPORTED = {"G4 vs F4": ("G4", "F4"), "G1 vs F1": ("G1", "F1"),
            "G1 vs random-1": ("G1", "random-1"), "random-4 vs template+R": ("random-4", "template+R"),
            "G4 vs oracle": ("G4", "oracle")}


def one(d, c, bands):
    a, b = d.get(f"{c}|A|{bands}"), d.get(f"{c}|B|{bands}")
    return None if a is None or b is None else (a + b) / 2


def best(d, menu, bands):
    """The split-half pick of a perfect ear: chosen on A scored on B, and the reverse."""
    menu = [c for c in menu if one(d, c, bands) is not None]
    if not menu:
        return None
    on_a = min(menu, key=lambda c: (d[f"{c}|A|{bands}"], c))
    on_b = min(menu, key=lambda c: (d[f"{c}|B|{bands}"], c))
    return (d[f"{on_a}|B|{bands}"] + d[f"{on_b}|A|{bands}"]) / 2


def arms(d, factory, bands):
    """{arm: distance} for one part under one band set; `d` holds the part's own renders
    (G1-G4, F1-F4, template+R) and the stored factory distances, keyed by name."""
    from reach_sets import expected_oracle

    ab = expected_oracle(d, factory, "A", "B", bands, 4)
    ba = expected_oracle(d, factory, "B", "A", bands, 4)
    singles = [one(d, c, bands) for c in factory]
    singles = [s for s in singles if s is not None]
    return {"G1": one(d, "G1", bands), "F1": one(d, "F1", bands),
            "template+R": one(d, "template+R", bands),
            "random-1": statistics.mean(singles) if singles else None,
            "G4": best(d, G, bands), "F4": best(d, F, bands),
            "random-4": None if ab is None or ba is None else (ab + ba) / 2,
            "oracle": best(d, factory, bands)}


def sign_flip_p(values):
    """Exact one-sided sign-flip p that the mean of `values` is below 0."""
    import itertools

    obs = sum(values)
    hits = sum(sum(s * v for s, v in zip(signs, values)) <= obs + 1e-12
               for signs in itertools.product((1, -1), repeat=len(values)))
    return hits / 2 ** len(values)


def compare(rows, first, second, bands):
    """The log ratio first/second per part, its median of band medians, the parts the
    first is closer on, and a band sign-flip p."""
    logs = [(r["band"], math.log(r["arms"][bands][first] / r["arms"][bands][second]))
            for r in rows if r["arms"][bands][first] and r["arms"][bands][second]]
    by = collections.defaultdict(list)
    for band, x in logs:
        by[band].append(x)
    medians = {b: statistics.median(v) for b, v in by.items()}
    m = statistics.median(medians.values()) if medians else None
    closer = sum(x < 0 for _, x in logs)
    return {"median_of_band_medians": m, "parts": len(logs), "bands": len(medians),
            "closer_on": closer, "sign_flip_p": sign_flip_p(list(medians.values())) if medians else None,
            "passes": bool(m is not None and m <= PASS + 1e-12 and closer > len(logs) / 2)}


def within_share(rows, arm, bands):
    """The band-weighted share of parts where `arm` is within CLEAR of the oracle."""
    from reach_sets import band_weighted_share

    flags = {r["part"]: math.log(r["arms"][bands][arm] / r["arms"][bands]["oracle"]) <= CLEAR + 1e-12
             for r in rows if r["arms"][bands][arm] and r["arms"][bands]["oracle"]}
    return band_weighted_share(flags, {r["part"]: r["band"] for r in rows})


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--renders", type=pathlib.Path, required=True)
    ap.add_argument("--reach-json", type=pathlib.Path, required=True)
    ap.add_argument("--reach-sets", type=pathlib.Path,
                    default=PLUGIN_ROOT / "docs" / "reach-sets.json")
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    from analysis import require

    require("scoring shortlists")
    from concurrent.futures import ProcessPoolExecutor

    import kill_tests as K
    import kill_tests_judge as KJ
    from benchmark_recordings import lag_samples

    renders = args.renders.expanduser()
    index = json.loads((renders / "index.json").read_text())
    reach = json.loads(args.reach_json.expanduser().read_text())
    stored, band_of = reach["distances"], {r["part"]: r["band"]
                                          for r in reach["rows"]["sw50r/all"]["recording"]}
    crops = pathlib.Path(index["crops_dir"])
    files, rows_by = collections.defaultdict(dict), collections.defaultdict(dict)
    for row in index["rows"]:
        if "file" in row:
            if _sha(row["file"]) != row["sha256"]:
                die(f"{row['file']} changed since it was rendered")
            files[row["part"]][row["label"]] = row["file"]
            rows_by[row["part"]][row["label"]] = row
    problems = []
    drifts = [r for r in index["rows"] if "canary" in r]
    problems += [f"{r['canary']}: the repeated template drifts {r['rms_drift_db']} dB"
                 for r in drifts if abs(r["rms_drift_db"]) >= DRIFT_DB]
    if set(files) - set(stored):
        die(f"parts amp reach did not score: {sorted(set(files) - set(stored))}")
    with ProcessPoolExecutor(args.workers) as ex:
        scored = dict(ex.map(KJ.score_part, [(p, files[p], lag_samples(p) - K.LATENCY, crops)
                                             for p in sorted(files)]))
    factory_root = "/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/"
    names = sorted({k.split("|")[0] for d in stored.values() for k in d})
    factory = [c for c in names if any(c.startswith(f"{a}:factory:") for a in AMPS)]
    if len(factory) != 108:
        die(f"expected the 108 factory presets, found {len(factory)}")
    repro, rows = [], []
    for p in sorted(files):
        new = scored[p]["d"]
        d = {k: v for k, v in stored[p].items() if k.split("|")[0] in factory}
        d.update({k: v for k, v in new.items()})
        # Canaries: the template and every factory pick against their stored distances.
        checks = {"template+R": "pr12:template+R"}
        for label in F:
            preset = rows_by[p][label]["preset"]
            name = preset[len(factory_root):-len(".xml")] if preset.startswith(factory_root) else None
            match = [c for c in factory if name and c.split(":", 2)[2] == name]
            if len(match) != 1:
                problems.append(f"{p}: {label} ({preset}) is not one of the 108 factory presets")
                continue
            checks[label] = match[0]
        for label, key in checks.items():
            for w in ("A", "B", "full"):
                for bands in BAND_SETS:
                    a, b = new.get(f"{label}|{w}|{bands}"), stored[p].get(f"{key}|{w}|{bands}")
                    if (a is None) != (b is None):
                        problems.append(f"{p}: {label} {w}/{bands} scored on one side only")
                    elif a is not None:
                        repro.append(abs(math.log(a / b)))
                        if abs(math.log(a / b)) > REPRO:
                            problems.append(f"{p}: {label} {w}/{bands} moved {math.log(a / b):+.4f}")
        rows.append({"part": p, "band": band_of[p],
                     "amps": {label: rows_by[p][label]["amp"] for label in G + F},
                     "arms": {bands: arms(d, factory, bands) for bands in BAND_SETS}})
    if problems:
        die("canaries failed; nothing is scored:\n  " + "\n  ".join(problems))
    out = {"inputs": {"renders_index": _sha(renders / "index.json"),
                      "reach_json": _sha(args.reach_json.expanduser()),
                      "reach_sets": _sha(args.reach_sets)},
           "commit": subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "HEAD"],
                                    capture_output=True, text=True).stdout.strip(),
           "canaries": {"max_abs_log_change": max(repro) if repro else None,
                        "readings": len(repro),
                        "max_drift_db": max((abs(r["rms_drift_db"]) for r in drifts), default=None)},
           "decisions": {}, "reported": {}, "within_0.150_of_oracle": {}, "amps": {}}
    for key, (a, b) in DECIDING.items():
        out["decisions"][key] = {"comparison": f"{a} vs {b}",
                                 **{bands: compare(rows, a, b, bands) for bands in BAND_SETS}}
        out["decisions"][key]["passes"] = all(out["decisions"][key][bands]["passes"]
                                              for bands in BAND_SETS)
    for key, (a, b) in REPORTED.items():
        out["reported"][key] = {bands: compare(rows, a, b, bands) for bands in BAND_SETS}
    for arm in ("G1", "F1", "template+R", "G4", "F4", "random-4"):
        out["within_0.150_of_oracle"][arm] = {bands: within_share(rows, arm, bands)
                                              for bands in BAND_SETS}
    sets = json.loads(args.reach_sets.read_text())["acceptable_amps"]
    for label in ("G1", "F1"):
        out["amps"][label] = {
            "counts": dict(collections.Counter(r["amps"][label] for r in rows)),
            **{f"acceptable_under_clean/{bands}": sum(
                bool(sets[f"clean/{bands}"]["rows"].get(r["part"], {}).get(r["amps"][label]))
                for r in rows) for bands in BAND_SETS}}
    for kind, labels in (("G1-G4", G), ("F1-F4", F)):
        out["amps"][kind] = dict(collections.Counter(r["amps"][x] for r in rows for x in labels))
    d2, d3 = out["decisions"]["D2"]["passes"], out["decisions"]["D3"]["passes"]
    out["shortlist_source"] = ("two generated and two factory" if d2 and d3 else
                               "generated" if d2 else "factory" if d3 else
                               "factory, chosen for spread across the acceptable amps")
    out["rows"] = rows
    brief = {k: v for k, v in out.items() if k != "rows"}
    print(json.dumps(brief, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
