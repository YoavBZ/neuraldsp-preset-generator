#!/usr/bin/env python3
"""Score the song-only shortlists against the factory panels (`docs/song-only-shortlist-plan.md`).

    python research/score_shortlists.py --renders ~/ndsp-presets/runs/shortlists/renders \\
        --reach-json ~/ndsp-presets/runs/kill/amp-reach.json --json shortlists.json

Scores every render `render_shortlists.py` made with the judge (half A, half B and
1.0-10 s; both band sets; the recorded lag less the 52-sample latency), checks the
canaries, and compares the arms. One preset's distance is the mean of its half-A and
half-B distances. A list's, as a perfect ear would pick, is the preset chosen on one
half scored on the other, both directions averaged. Random arms are the median of
their distribution on the part (a list drawn by chance, scored the same way), so a
single list is not compared with an average. A comparison passes when, under both
band sets, the median of band medians of its log ratio is at most log 0.9 and the
first arm is closer on more than half the parts; a "not worse" comparison, when the
median is at most 0 and the first arm is closer on at least half. It is inconclusive
when moving the median by 0.03, or the count by one part, would change that.
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
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from _cli import die, guarded

BAND_SETS = ("recording", "union")
AMPS = ("ac20", "pr12", "sw50r")
PASS = math.log(0.9)
NEAR = 0.03                 # a median this close to the bar reads as inconclusive
CLEAR = 0.150
LOSS = 5.0                  # the log ratio a refused render counts as
REPRO, DRIFT_DB = 0.01, 0.1
SILENT_PEAK = 1e-6
DRAWS = 50_000
G = [f"G{i}" for i in range(1, 5)]
F = [f"F{i}" for i in range(1, 5)]
M = ["G1", "G2", "F1", "F2"]
FACTORY_ROOT = "/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/"
ARMS = ("G1", "F1", "template+R", "random-1", "G4", "F4", "M4", "house-4", "random-4",
        "random-4 clean", "oracle")
MAX_EXCLUDED = 5
REPORTED = {"G1 vs F1": ("G1", "F1"), "G1 vs random-1": ("G1", "random-1"),
            "G4 vs template+R": ("G4", "template+R"), "F4 vs template+R": ("F4", "template+R"),
            "random-4 vs template+R": ("random-4", "template+R"),
            "house-4 vs random-4": ("house-4", "random-4"),
            "S4 vs random-4 clean": ("S4", "random-4 clean"), "S4 vs oracle": ("S4", "oracle")}
LISTS = {"G4": "G1", "F4": "F1", "M4": "G1"}       # each list and its first choice


def one(d, c, bands):
    a, b = d.get(f"{c}|A|{bands}"), d.get(f"{c}|B|{bands}")
    return None if a is None or b is None else (a + b) / 2


def best(d, menu, bands):
    """The split-half pick of a perfect ear: chosen on A scored on B, and the reverse.
    A preset not scored on both halves is never picked."""
    menu = [c for c in menu if one(d, c, bands) is not None]
    if not menu:
        return None
    on_a = min(menu, key=lambda c: (d[f"{c}|A|{bands}"], c))
    on_b = min(menu, key=lambda c: (d[f"{c}|B|{bands}"], c))
    return (d[f"{on_a}|B|{bands}"] + d[f"{on_b}|A|{bands}"]) / 2


def random_median(d, menu, bands, size, seed):
    """The median split-half distance of a `size`-list drawn at random from `menu`."""
    import numpy as np

    menu = [c for c in menu if one(d, c, bands) is not None]
    a = np.array([d[f"{c}|A|{bands}"] for c in menu])
    b = np.array([d[f"{c}|B|{bands}"] for c in menu])
    rng = np.random.default_rng(int(hashlib.sha256(seed.encode()).hexdigest()[:12], 16))
    draws = np.argsort(rng.random((DRAWS, len(menu))), axis=1)[:, :size]
    rows = np.arange(DRAWS)
    on_a = draws[rows, np.argmin(a[draws], axis=1)]
    on_b = draws[rows, np.argmin(b[draws], axis=1)]
    return float(np.median((b[on_a] + a[on_b]) / 2))


def house_lists(dist, parts, band_of, factory, bands, random1):
    """{held-out band: the fixed 4-list}, each built greedily on the other bands' parts:
    at each step the preset that most lowers the median of band medians of
    log(the list's split-half distance / the part's random-1), ties broken by the
    mean over the parts and then by name."""
    out = {}
    for held in sorted(set(band_of[p] for p in parts)):
        train = [p for p in parts if band_of[p] != held]
        chosen = []
        for _ in range(4):
            def score(c):
                by = collections.defaultdict(list)
                for p in train:
                    v = best(dist[p], chosen + [c], bands)
                    if v is not None:
                        by[band_of[p]].append(math.log(v / random1[p]))
                return (statistics.median(statistics.median(v) for v in by.values()),
                        statistics.mean(x for v in by.values() for x in v), c)
            chosen.append(min((c for c in factory if c not in chosen), key=score))
        out[held] = chosen
    return out


def capped(x):
    return max(-LOSS, min(LOSS, x))


def sign_flip_p(values):
    """Exact one-sided sign-flip p that the mean of `values` is below 0."""
    import itertools

    obs = sum(values)
    hits = sum(sum(s * v for s, v in zip(signs, values)) <= obs + 1e-12
               for signs in itertools.product((1, -1), repeat=len(values)))
    return hits / 2 ** len(values)


def passes(m, closer, n, rule):
    if rule == "better":
        return m <= PASS + 1e-12 and closer > n / 2
    return m <= 1e-12 and closer >= n / 2                  # "not worse"


def compare(rows, first, second, bands, rule="better"):
    """The log ratio first/second per part, its median of band medians, the parts the
    first is closer on, and a band sign-flip p. A refused render counts as LOSS against
    its own arm, whichever side it is on; two refused arms tie."""
    logs = []
    for r in rows:
        a, b = r["arms"][bands][first], r["arms"][bands][second]
        fa = a is not None and math.isfinite(a)
        fb = b is not None and math.isfinite(b)
        x = capped(math.log(a / b)) if fa and fb else LOSS if fb else -LOSS if fa else 0.0
        logs.append((r["band"], x))
    by = collections.defaultdict(list)
    for band, x in logs:
        by[band].append(x)
    medians = {k: statistics.median(v) for k, v in by.items()}
    m = statistics.median(medians.values()) if medians else None
    closer, n = sum(x < 0 for _, x in logs), len(logs)
    verdict = m is not None and passes(m, closer, n, rule)
    near = m is not None and any(passes(mm, cc, n, rule) != verdict for mm, cc in
                                 ((m - NEAR, closer), (m + NEAR, closer),
                                  (m, closer - 1), (m, closer + 1)))
    return {"median_of_band_medians": m, "parts": n, "bands": len(medians),
            "closer_on": closer, "rule": rule,
            "sign_flip_p": sign_flip_p(list(medians.values())) if medians else None,
            "passes": bool(verdict), "near": bool(near)}


def decide(rows, first, second, rule="better"):
    out = {"comparison": f"{first} vs {second}",
           **{bands: compare(rows, first, second, bands, rule) for bands in BAND_SETS}}
    out["passes"] = all(out[b]["passes"] for b in BAND_SETS)
    out["inconclusive"] = any(out[b]["near"] for b in BAND_SETS)
    out["holds"] = out["passes"] and not out["inconclusive"]
    return out


def headroom(rows, arm, bands):
    """The median of band medians of the share of random-4's distance to the oracle
    that `arm` closes (1 is the oracle, 0 random-4)."""
    by = collections.defaultdict(list)
    for r in rows:
        a, r4, o = (r["arms"][bands][k] for k in (arm, "random-4", "oracle"))
        if r4 <= o:
            continue
        span = math.log(r4) - math.log(o)
        # A refused arm counts as LOSS past random-4, as in compare().
        by[r["band"]].append(-LOSS / span if a is None or not math.isfinite(a)
                             else (math.log(r4) - math.log(a)) / span)
    return statistics.median(statistics.median(v) for v in by.values()) if by else None


def within_share(rows, arm, bands):
    """The band-weighted share of parts where `arm` is within CLEAR of the oracle."""
    from reach_sets import band_weighted_share

    flags = {}
    for r in rows:
        a, o = r["arms"][bands][arm], r["arms"][bands]["oracle"]
        flags[r["part"]] = bool(a is not None and math.isfinite(a) and math.log(a / o) <= CLEAR + 1e-12)
    return band_weighted_share(flags, {r["part"]: r["band"] for r in rows})


def band_weighted_mean(values, band_of):
    """The mean of `values[part]`, each band weighing one."""
    by = collections.defaultdict(list)
    for p, v in values.items():
        by[band_of[p]].append(v)
    return statistics.mean(statistics.mean(v) for v in by.values()) if by else None


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
    from plan_listening_validation import high_gain

    renders = args.renders.expanduser()
    index = json.loads((renders / "index.json").read_text())
    manifest = json.loads(pathlib.Path(index["manifest"]).expanduser().read_text())
    excluded = [p for parts in manifest.get("excluded", {}).values() for p in parts]
    if len(excluded) > MAX_EXCLUDED:
        die(f"{len(excluded)} parts excluded, more than {MAX_EXCLUDED}: the measurement is void")
    reach = json.loads(args.reach_json.expanduser().read_text())
    stored, band_of = reach["distances"], {r["part"]: r["band"]
                                          for r in reach["rows"]["sw50r/all"]["recording"]}
    crops = pathlib.Path(index["crops_dir"])
    files, info = collections.defaultdict(dict), collections.defaultdict(dict)
    problems = []
    for row in index["rows"]:
        if "file" not in row:
            continue
        if _sha(row["file"]) != row["sha256"]:
            die(f"{row['file']} changed since it was rendered")
        label = f"{row['label']}#repeat" if row.get("repeat") else row["label"]
        files[row["part"]][label] = row["file"]
        info[row["part"]][label] = row
    drifts = [r for r in index["rows"] if "canary" in r]
    problems += [f"{r['canary']}: the repeated template drifts {r['rms_drift_db']} dB"
                 for r in drifts if abs(r["rms_drift_db"]) >= DRIFT_DB]
    if set(files) != set(manifest["parts"]):
        die("the renders do not cover the manifest's parts")
    if set(files) - set(stored):
        die(f"parts amp reach did not score: {sorted(set(files) - set(stored))}")
    with ProcessPoolExecutor(args.workers) as ex:
        scored = dict(ex.map(KJ.score_part, [(p, files[p], lag_samples(p) - K.LATENCY, crops)
                                             for p in sorted(files)]))
    names = sorted({k.split("|")[0] for d in stored.values() for k in d})
    factory = [c for c in names if any(c.startswith(f"{a}:factory:") for a in AMPS)]
    if len(factory) != 108:
        die(f"expected the 108 factory presets, found {len(factory)}")
    clean = [c for c in factory if not high_gain(c)]
    readings, dists = [], {}
    refused_g = {"silent": collections.Counter(), "refused by the judge": collections.Counter()}
    for p in sorted(files):
        new = dict(scored[p]["d"])
        # A silent render is refused outright, whatever the judge made of it; silent on
        # one pass only is the renderer failing, and stops the run.
        for label in [x for x in info[p] if "#" not in x]:
            silent = [info[p][x]["peak"] < SILENT_PEAK for x in (label, f"{label}#repeat")
                      if x in info[p]]
            if any(silent) and not all(silent):
                problems.append(f"{p}: {label} is silent on one pass only")
            elif all(silent):
                for k in [k for k in new if k.split("|")[0] in (label, f"{label}#repeat")]:
                    new[k] = None
                if label in G:
                    refused_g["silent"][label] += 1
        # Every render repeats itself, in reverse order in the same process.
        for label in [x for x in info[p] if "#" not in x]:
            if label == "template+R":
                continue
            for w in ("A", "B", "full"):
                for bands in BAND_SETS:
                    a, b = new.get(f"{label}|{w}|{bands}"), new.get(f"{label}#repeat|{w}|{bands}")
                    if (a is None) != (b is None):
                        problems.append(f"{p}: {label} {w}/{bands} refused on one pass only")
                    elif a is not None and abs(math.log(a / b)) > REPRO:
                        problems.append(f"{p}: {label} {w}/{bands} repeats {math.log(a / b):+.4f} away")
        # The template and every factory pick against their stored distances.
        checks = {"template+R": "pr12:template+R"}
        for label in F:
            preset = info[p][label]["preset"]
            name = preset[len(FACTORY_ROOT):-len(".xml")] if preset.startswith(FACTORY_ROOT) else None
            match = [c for c in factory if name is not None and c.split(":", 2)[2] == name]
            if len(match) != 1:
                problems.append(f"{p}: {label} ({preset}) is not one of the 108 factory presets")
                continue
            checks[label] = match[0]
        for label, key in checks.items():
            for w in ("A", "B", "full"):
                for bands in BAND_SETS:
                    a, b = new.get(f"{label}|{w}|{bands}"), stored[p].get(f"{key}|{w}|{bands}")
                    if a is None or b is None:
                        problems.append(f"{p}: {label} {w}/{bands} refused "
                                        f"({'here' if a is None else 'in the panel'})")
                    else:
                        readings.append(abs(math.log(a / b)))
                        if abs(math.log(a / b)) > REPRO:
                            problems.append(f"{p}: {label} {w}/{bands} moved {math.log(a / b):+.4f}")
        for label in G:
            if any(new.get(f"{label}|{h}|{b}") is None for h in ("A", "B") for b in BAND_SETS) \
                    and info[p][label]["peak"] >= SILENT_PEAK:
                refused_g["refused by the judge"][label] += 1
        d = {k: v for k, v in stored[p].items() if k.split("|")[0] in factory}
        d.update({k: v for k, v in new.items() if "#repeat" not in k})
        dists[p] = d
    if problems:
        die("canaries failed; nothing is scored:\n  " + "\n  ".join(problems))
    parts = sorted(dists)
    rows = []
    houses = {}
    # The house list is trained on every part amp reach stored, whichever were rendered.
    trained = reach["parts"]
    panel = {p: {k: v for k, v in stored[p].items() if k.split("|")[0] in factory}
             for p in trained}
    for bands in BAND_SETS:
        random1 = {p: statistics.median(v for v in (one(panel[p], c, bands) for c in factory)
                                        if v is not None) for p in trained}
        houses[bands] = house_lists(panel, trained, band_of, factory, bands, random1)
    for p in parts:
        d, arms = dists[p], {}
        for bands in BAND_SETS:
            singles = [v for v in (one(d, c, bands) for c in factory) if v is not None]
            g1 = one(d, "G1", bands)
            arms[bands] = {
                "G1": math.inf if g1 is None else g1, "F1": one(d, "F1", bands),
                "template+R": one(d, "template+R", bands),
                "random-1": statistics.median(singles),
                "G4": best(d, G, bands) or math.inf, "F4": best(d, F, bands),
                "M4": best(d, M, bands) or math.inf,
                "house-4": best(d, houses[bands][band_of[p]], bands),
                "random-4": random_median(d, factory, bands, 4, f"{p}|{bands}|all"),
                "random-4 clean": random_median(d, clean, bands, 4, f"{p}|{bands}|clean"),
                "oracle": best(d, factory, bands)}
        rows.append({"part": p, "band": band_of[p],
                     "amps": {label: info[p][label]["amp"] for label in G + F}, "arms": arms,
                     "refused": {k: v for k, v in scored[p]["refused"].items()
                                 if "#repeat" not in k}})
    out = {"inputs": {"renders_index": _sha(renders / "index.json"),
                      "reach_json": _sha(args.reach_json.expanduser()),
                      "reach_sets": _sha(args.reach_sets)},
           "commit": subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "HEAD"],
                                    capture_output=True, text=True).stdout.strip(),
           "canaries": {"max_abs_log_change_vs_panels": max(readings), "readings": len(readings),
                        "max_template_drift_db": max(abs(r["rms_drift_db"]) for r in drifts)},
           "excluded_parts": excluded,
           "refused_generated": {k: dict(v) for k, v in refused_g.items()},
           "house_lists": houses, "decisions": {}, "reported": {},
           "within_0.150_of_oracle": {}, "amps": {}}
    dec = out["decisions"]
    dec["D1"] = decide(rows, "G1", "template+R")
    dec["D2 F4 vs G4"] = decide(rows, "F4", "G4")
    dec["D2 M4 vs G4"] = decide(rows, "M4", "G4")
    held = [k for k in ("F4", "M4") if dec[f"D2 {k} vs G4"]["holds"]]
    source = min(held, key=lambda k: max(dec[f"D2 {k} vs G4"][b]["median_of_band_medians"]
                                         for b in BAND_SETS)) if held else "G4"
    out["shortlist_source"] = {"G4": "generated", "F4": "factory", "M4": "two generated, two factory"}[source]
    for r in rows:
        for bands in BAND_SETS:
            r["arms"][bands]["S4"] = r["arms"][bands][source]
    dec["D3 S4 not worse than house-4"] = decide(rows, "S4", "house-4", "not worse")
    dec["D3 S4 vs random-4"] = decide(rows, "S4", "random-4")
    # Every list against its own first choice, the house list and random-4, so the
    # choice of S hides nothing.
    for arm, first in LISTS.items():
        out["reported"][f"{arm} vs {first}"] = decide(rows, arm, first)
        out["reported"][f"{arm} not worse than house-4"] = decide(rows, arm, "house-4", "not worse")
        out["reported"][f"{arm} vs random-4"] = decide(rows, arm, "random-4")
    for key, (a, b) in REPORTED.items():
        out["reported"][key] = {bands: compare(rows, a, b, bands) for bands in BAND_SETS}
    out["headroom_closed"] = {arm: {bands: headroom(rows, arm, bands) for bands in BAND_SETS}
                              for arm in ("G1", "F1", "template+R", "G4", "F4", "M4", "house-4",
                                          "S4")}
    for arm in ARMS[:-1] + ("S4",):
        out["within_0.150_of_oracle"][arm] = {bands: within_share(rows, arm, bands)
                                              for bands in BAND_SETS}
    sets = json.loads(args.reach_sets.read_text())["acceptable_amps"]
    weights = {r["part"]: r["band"] for r in rows}
    for kind, labels in (("G", G), ("F", F)):
        out["amps"][kind] = {
            "counts": dict(collections.Counter(r["amps"][x] for r in rows for x in labels)),
            "first_choice": dict(collections.Counter(r["amps"][labels[0]] for r in rows)),
            # Band-weighted, under the clean menus' acceptable amps (docs/reach-sets.json):
            # each part's share of entries on one, averaged within its band, then over
            # bands. (band_weighted_share takes flags, so it can't average fractions.)
            **{f"share_on_acceptable_amps/{bands}": band_weighted_mean(
                {r["part"]: statistics.mean(
                    bool(sets[f"clean/{bands}"]["rows"].get(r["part"], {}).get(r["amps"][x]))
                    for x in labels) for r in rows}, weights)
               for bands in BAND_SETS}}
    out["rows"] = rows
    brief = {k: v for k, v in out.items() if k != "rows"}
    print(json.dumps(brief, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
