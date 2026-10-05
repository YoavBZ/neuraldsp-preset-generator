#!/usr/bin/env python3
"""Does a cheap fix for the render-to-real gap rescue K3's recognisers?
(`docs/quick-checks-plan.md`)

    python scripts/k3_hub_fixes.py --reach-json ~/ndsp-presets/runs/kill/amp-reach.json \\
        --json k3-hub-fixes.json

K3's recognisers (`scripts/kill_test_k3.py`: K2's features, its four folds of bands,
1-NN, LDA, LDA+1-NN) are re-run on the SW50R panel and the clean PR12 panel, as K3 ran
them, and with four fixes, each fitted on the training folds' real amp tracks only:

- `realnorm`: a real track's features standardised by the training folds' real tracks
  (their mean and spread) instead of the renders';
- `csls`: hubness correction (CSLS): a candidate's distance is doubled, less its mean
  distance to its 10 nearest training real tracks and the target's mean distance to its
  10 nearest candidates;
- `bias`: each candidate's distances centred by its mean distance to the training real
  tracks;
- `realnorm+csls`.

Each pick is scored by the judge against the part's amp track over 1.0-10 s, at the
recorded lag, against template+R.
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

VARIANTS = ("baseline", "realnorm", "csls", "bias", "realnorm+csls")
RECOGNISERS = ("1nn", "lda", "lda+1nn")
BAND_SETS = ("recording", "union")
K_NEAR = 10
GAIN_STEP = 0.05          # at least 5 points better than the unfixed recogniser
TOP_SHARE = 0.25          # and its most common pick under a quarter of its picks
MENUS = {"sw50r": ("~/ndsp-presets/runs/kill/sw50r", "sw50r", "k3-sw50r-run2.json"),
         "pr12-clean": ("~/ndsp-presets/runs/kill/pr12-clean", "pr12", "k3-pr12-clean.json")}


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reach-json", type=pathlib.Path, required=True)
    ap.add_argument("--kill-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/runs/kill"))
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--workers", type=int, default=4)
    return ap


def sqdist(A, b):
    return ((A - b) ** 2).sum(-1)


def recognise(X, y, fold, real, real_fold, targets, factory, variant):
    """({part: {recogniser: pick}} for the parts in `targets` ({part: (fold, features)}),
    {fold: {part: {recogniser: pick}}} for every target's track under each fold's model),
    trained on the renders of the other folds; `real` are every eligible part's real-track
    features with their folds, used only from the training folds. The second is for the
    shuffled control: a part's recogniser given other bands' tracks."""
    import numpy as np

    out, every_fold = {}, {}
    for f_ in sorted({f for f, _ in targets.values()}):
        tr = fold != f_
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        Xtr = (X[tr] - mu) / sd
        ytr = y[tr]
        cls = np.unique(ytr)
        means = {}
        Sw = np.zeros((Xtr.shape[1],) * 2)
        for c in cls:
            Z = Xtr[ytr == c]
            means[c] = Z.mean(0)
            Sw += (Z - means[c]).T @ (Z - means[c])
        Sw /= len(Xtr)
        Sw = 0.9 * Sw + 0.1 * np.trace(Sw) / len(Sw) * np.eye(len(Sw))
        gm = Xtr.mean(0)
        Sb = sum((ytr == c).sum() * np.outer(means[c] - gm, means[c] - gm) for c in cls) / len(Xtr)
        w, V = np.linalg.eig(np.linalg.solve(Sw, Sb))
        W = V[:, np.argsort(-w.real)[: len(cls) - 1]].real
        Ptr = Xtr @ W
        cm = np.stack([means[c] @ W for c in cls])
        train_real = real[real_fold != f_]
        if variant.startswith("realnorm"):
            rmu, rsd = train_real.mean(0), train_real.std(0) + 1e-9
            norm = lambda t: (t - rmu) / rsd                               # noqa: E731
        else:
            norm = lambda t: (t - mu) / sd                                 # noqa: E731
        R = np.stack([norm(t) for t in train_real])

        def corrected(dist_to_cands, cands_space, target_space_fn):
            """Apply the variant's correction to a target's candidate distances."""
            if variant.endswith("csls"):
                Rs = np.stack([target_space_fn(r) for r in R])
                hub = np.array([np.sort(sqdist(Rs, c))[:K_NEAR].mean() for c in cands_space])
                own = np.sort(dist_to_cands)[:K_NEAR].mean()
                return 2 * dist_to_cands - hub - own
            if variant == "bias":
                Rs = np.stack([target_space_fn(r) for r in R])
                centre = np.array([sqdist(Rs, c).mean() for c in cands_space])
                return dist_to_cands - centre
            return dist_to_cands

        ident = lambda r: r                                                # noqa: E731
        proj = lambda r: r @ W                                             # noqa: E731

        def pick(feat):
            t = norm(feat)
            d1 = corrected(sqdist(Xtr, t), Xtr, ident)
            pt = t @ W
            dl = corrected(sqdist(cm, pt), cm, proj)
            dp = corrected(sqdist(Ptr, pt), Ptr, proj)
            return {"1nn": factory[int(ytr[np.argmin(d1)])],
                    "lda": factory[int(cls[np.argmin(dl)])],
                    "lda+1nn": factory[int(ytr[np.argmin(dp)])]}

        every_fold[f_] = {p: pick(feat) for p, (_, feat) in targets.items()}
        for p, (fp, _) in targets.items():
            if fp == f_:
                out[p] = every_fold[f_][p]
    return out, every_fold


def band_median(rows):
    by = collections.defaultdict(list)
    for band, x in rows:
        by[band].append(x)
    return statistics.median(statistics.median(v) for v in by.values())


def band_medians(rows):
    by = collections.defaultdict(list)
    for band, x in rows:
        by[band].append(x)
    return {b: statistics.median(v) for b, v in by.items()}


def sign_flip_p(values):
    """Exact one-sided sign-flip p that the mean of `values` is below 0."""
    import itertools

    obs = sum(values)
    hits = sum(sum(s * v for s, v in zip(signs, values)) <= obs + 1e-12
               for signs in itertools.product((1, -1), repeat=len(values)))
    return hits / 2 ** len(values)


def holm(ps):
    order = sorted(ps, key=ps.get)
    adjusted, running = {}, 0.0
    for i, key in enumerate(order):
        running = max(running, min(1.0, (len(order) - i) * ps[key]))
        adjusted[key] = running
    return adjusted


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("testing hub fixes for K3")
    import numpy as np

    import kill_test_k3 as K3
    import kill_tests as K
    import kill_tests_judge as KJ
    from benchmark_recordings import CATALOG, lag_samples

    reach = json.loads(args.reach_json.expanduser().read_text())
    if reach["canary_misses"]:
        die("the amp-reach canaries missed")
    judged = reach["distances"]
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    meta = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            meta[slug] = {"band": s.get("group") or f"{s['source']}/{s['song']}",
                          "lag": int(round((p.get("lag_ms") or 0) * K.SR / 1000))}
    crops = args.crops_dir.expanduser()
    kill = args.kill_dir.expanduser()
    out = {"menus": {}}
    for menu_name, (panel_dir, amp, k3_name) in MENUS.items():
        panel = pathlib.Path(panel_dir).expanduser()
        index = json.loads((panel / "index.json").read_text())
        files = {}
        for row in index["rows"]:
            if "file" in row:
                files.setdefault(row["part"], {})[row["candidate"]] = pathlib.Path(row["file"])
        factory = sorted({c for d in files.values() for c in d if c.startswith("factory:")})
        parts = sorted(files)
        bands = sorted({meta[p]["band"] for p in parts})
        rng = random.Random(K.FOLD_SEED)
        rng.shuffle(bands)
        fold_of = {b: i % 4 for i, b in enumerate(bands)}
        dis = {p: K.mono(crops / p / "di.wav") for p in parts}
        eligible = [p for p in parts if K.active_fraction(dis[p], 1.0, 10.0) >= 0.5]
        X, y, owner = [], [], []
        for p in parts:
            for c in factory:
                f = K3.features(K.mono(files[p][c]), dis[p], K3.LATENCY)
                if f is not None:
                    X.append(f)
                    y.append(factory.index(c))
                    owner.append(p)
        X, y = np.array(X), np.array(y)
        fold = np.array([fold_of[meta[p]["band"]] for p in owner])
        real_feat = {p: K3.features(K.mono(crops / p / "reference.wav"), dis[p], meta[p]["lag"])
                     for p in eligible}
        real_parts = [p for p in eligible if real_feat[p] is not None]
        real = np.stack([real_feat[p] for p in real_parts])
        real_fold = np.array([fold_of[meta[p]["band"]] for p in real_parts])
        targets = {p: (fold_of[meta[p]["band"]], real_feat[p]) for p in real_parts}
        recognised = {v: recognise(X, y, fold, real, real_fold, targets, factory, v)
                      for v in VARIANTS}
        picks = {v: r[0] for v, r in recognised.items()}
        earlier_doc = json.loads((kill / k3_name).read_text())
        if pathlib.Path(earlier_doc["panel"]).expanduser().resolve() != panel.resolve():
            die(f"{k3_name} was not run on {panel}")
        earlier = earlier_doc["picks"]
        misses = [(r, p) for r in RECOGNISERS for p, c in earlier[r].items()
                  if picks["baseline"].get(p, {}).get(r) != c]
        if misses or any(set(earlier[r]) != set(picks["baseline"]) for r in RECOGNISERS):
            die(f"{menu_name}: the unfixed recognisers do not reproduce K3's picks: {misses[:5]}")
        # Judge distances for every candidate on the K3 parts with a clear lag: from the
        # amp-reach run where it scored the part, else scored here.
        scored_parts = [p for p in real_parts if lag_samples(p) is not None]
        missing = [p for p in scored_parts
                   if f"{amp}:template+R|full|recording" not in judged.get(p, {})]
        if missing:
            from concurrent.futures import ProcessPoolExecutor

            need = factory + ["template+R"]
            with ProcessPoolExecutor(args.workers) as ex:
                for p, s in ex.map(KJ.score_part,
                                   [(p, {c: files[p][c] for c in need},
                                     lag_samples(p) - K.LATENCY, crops) for p in missing]):
                    judged.setdefault(p, {}).update({f"{amp}:{k}": v
                                                     for k, v in s["d"].items()})
        band_of = {p: meta[p]["band"] for p in scored_parts}

        def lr(p, c, bands):
            d = judged[p].get(f"{amp}:{c}|full|{bands}")
            base = judged[p].get(f"{amp}:template+R|full|{bands}")
            return math.log(d / base) if d and base else None

        # The no-information pick: a preset drawn from the menu at random (exact mean).
        no_info = {b: band_median([(band_of[p], statistics.mean(lr(p, c, b) for c in factory))
                                   for p in scored_parts]) for b in BAND_SETS}
        # The constant: the preset with the lowest median distance over the training bands.
        constant = {}
        for b in BAND_SETS:
            for f_ in set(fold_of.values()):
                train = [p for p in scored_parts if fold_of[band_of[p]] != f_]
                best = min(factory, key=lambda c: (statistics.median(
                    judged[p][f"{amp}:{c}|full|{b}"] for p in train), c))
                for p in scored_parts:
                    if fold_of[band_of[p]] == f_:
                        constant[(p, b)] = best
        readings, per_part = {}, {}
        for v in VARIANTS:
            folds = recognised[v][1]
            for r in RECOGNISERS:
                for bands in BAND_SETS:
                    rows, chosen, beats_shuffled, beats_constant, mine = [], [], [], [], {}
                    for p in scored_parts:
                        c = picks[v][p][r]
                        x = lr(p, c, bands)
                        if x is None:
                            continue
                        rows.append((band_of[p], x))
                        mine[p] = x
                        chosen.append(c)
                        others = [picked[r] for o, picked in folds[fold_of[band_of[p]]].items()
                                  if meta[o]["band"] != band_of[p]]
                        shuffled = statistics.mean(lr(p, o, bands) for o in others)
                        beats_shuffled.append(1.0 if x < shuffled else 0.5 if x == shuffled
                                              else 0.0)
                        beats_constant.append(x < lr(p, constant[(p, bands)], bands))
                    per_part[f"{v}/{r}/{bands}"] = mine
                    top = max(collections.Counter(chosen).values()) / len(chosen)
                    readings[f"{v}/{r}/{bands}"] = {
                        "parts": len(rows), "band_median_vs_templateR": band_median(rows),
                        "closer_than_templateR": sum(x < 0 for _, x in rows),
                        "better_than_shuffled": sum(beats_shuffled),
                        "closer_than_constant": sum(beats_constant),
                        "most_common_pick_share": top, "distinct_picks": len(set(chosen))}
        fixes, ps = {}, {b: {} for b in BAND_SETS}
        for v in VARIANTS[1:]:
            for r in RECOGNISERS:
                for b in BAND_SETS:
                    diff = band_medians([(band_of[p], per_part[f"{v}/{r}/{b}"][p]
                                          - per_part[f"baseline/{r}/{b}"][p])
                                         for p in scored_parts
                                         if p in per_part[f"{v}/{r}/{b}"]
                                         and p in per_part[f"baseline/{r}/{b}"]])
                    ps[b][f"{v}/{r}"] = sign_flip_p(list(diff.values()))

                def holds(b):
                    x, base = readings[f"{v}/{r}/{b}"], readings[f"baseline/{r}/{b}"]
                    return (x["most_common_pick_share"] < TOP_SHARE
                            and x["band_median_vs_templateR"]
                            <= base["band_median_vs_templateR"] - GAIN_STEP
                            and x["band_median_vs_templateR"] < no_info[b]
                            and x["better_than_shuffled"] > x["parts"] / 2)
                fixes[f"{v}/{r}"] = all(holds(b) for b in BAND_SETS)
        out["menus"][menu_name] = {
            "parts": len(scored_parts), "no_information_band_median": no_info,
            "readings": readings, "fix_passes": fixes,
            "fix_minus_baseline_holm_p": {b: holm(ps[b]) for b in BAND_SETS},
            "picks": picks}
    rescued = {k: v for k, v in out["menus"]["pr12-clean"]["fix_passes"].items() if v}
    out["pr12_clean_rescued_by"] = sorted(rescued)
    sw = out["menus"]["sw50r"]["readings"]
    out["sw50r_worse_by_more_than_0.05"] = sorted(
        k for k in rescued if any(
            sw[f"{k}/{b}"]["band_median_vs_templateR"]
            > sw[f"baseline/{k.split('/', 1)[1]}/{b}"]["band_median_vs_templateR"] + GAIN_STEP
            for b in BAND_SETS))
    import hashlib
    import subprocess

    out["inputs"] = {str(args.reach_json): hashlib.sha256(
        args.reach_json.expanduser().read_bytes()).hexdigest()}
    out["commit"] = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "HEAD"],
                                   capture_output=True, text=True).stdout.strip()
    print(json.dumps({"pr12_clean_rescued_by": out["pr12_clean_rescued_by"],
                      "readings": {m: v["readings"] for m, v in out["menus"].items()}},
                     indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
