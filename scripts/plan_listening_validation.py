#!/usr/bin/env python3
"""Stage 0b: choose the listening-validation trials (`docs/listening-validation-plan.md`).

    python scripts/plan_listening_validation.py --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --cache ~/ndsp-presets/runs/listening-validation/pool.json \\
        --out ~/ndsp-presets/runs/listening-validation/draw/trials.json

For every development part with a 4-s window where its DI plays in at least 90% of the
frames, every panel candidate's distance to the part's amp track over exactly that
window: the judge (`analysis/aligned.py`, both band sets, one lag per part pooled over
its whole panel), ALM and v3c (`kill_tests.py`). Then, with a private seed, 24 test pairs
above the judge's median |log(dA/dB)| (at least 10 where the judge and v3c disagree, at
most 2 per part, at least 8 bands, no candidate in more than 3), 3 hidden references and
3 hidden repeats. The seed is drawn from the system's randomness and kept with the
output, which names the pairs and every distance's prediction: both stay private until
every answer is in (the plan records only the file's sha256), since a listener who saw
the pairs could tell the options apart. Trial numbers and A/B are drawn when the files
are built.
"""

from __future__ import annotations

import argparse
import itertools
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
import kill_tests as K

SR, LATENCY = K.SR, K.LATENCY
WINDOW_S, STEP_S, FIRST_S, MIN_ACTIVE = 4.0, 0.25, 0.5, 0.9
TEST_PAIRS, MIN_DISAGREE, PER_PART, MIN_BANDS, PER_CANDIDATE = 24, 10, 2, 8, 3
HIDDEN_REFERENCES, REPEATS = 3, 3
DISTANCES = ("judge", "judge_union", "alm", "v3c")
# The two live-room parts whose amp track's top octave is mostly cymbals: hard to hear
# a guitar's tone through, and bleed the judge does not handle (measuring-closeness.md).
BLEED_HEAVY = ("telefunken-Lost_Alive-GTR", "telefunken-Until_I_Get_Back-GTR")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--cache", type=pathlib.Path, required=True,
                    help="the pool's distances (computed once, reused when present)")
    ap.add_argument("--out", type=pathlib.Path, required=True,
                    help="the private trial list (refused if it exists)")
    ap.add_argument("--workers", type=int, default=3)
    return ap


def window(di):
    """The first 4-s window from 0.5 s, in 0.25-s steps, where the DI plays in at least
    90% of its 2048-sample frames (hop 512) within 40 dB of its peak."""
    db = K.frame_rms_db(di, 2048, 512)
    active = db >= db.max() - 40
    hop = 512 / SR
    start = FIRST_S
    while start + WINDOW_S <= len(di) / SR + 1e-9:
        a, b = int(round(start / hop)), int(round((start + WINDOW_S) / hop))
        if active[a:b].mean() >= MIN_ACTIVE:
            return start
        start += STEP_S
    return None


def score_part(job):
    """Every candidate's distances over the part's window, or None if it has none."""
    part, files, catalogued, crops = job
    from analysis.aligned import aligned_distance, estimate_lag

    di, ref = K.mono(crops / part / "di.wav"), K.mono(crops / part / "reference.wav")
    w = window(di)
    if w is None:
        return part, None
    renders = {c: K.mono(f) for c, f in files.items()}
    try:
        lag = estimate_lag(ref, list(renders.values()), hint=catalogued - LATENCY,
                           max_lag_s=0.015)
    except ValueError:
        lag = estimate_lag(ref, list(renders.values()), hint=catalogued - LATENCY,
                           max_lag_s=0.05)
    a, b = int(w * SR), int((w + WINDOW_S) * SR)
    ref_fp = K.fp(ref[a:b], "isolated_stem")
    v3c = K._v3c_compare()
    out = {}
    for c, x in renders.items():
        judge = {bands: aligned_distance(ref, x, di, lag=lag, render_latency=LATENCY,
                                         start_s=w, end_s=w + WINDOW_S, bands=bands).distance
                 for bands in ("recording", "union")}
        seg = x[max(a - lag, 0): max(b - lag, 0)]
        out[c] = {"judge": judge["recording"], "judge_union": judge["union"],
                  "alm": K.alm(ref, x, di, catalogued - LATENCY, w, w + WINDOW_S),
                  "v3c": v3c(ref_fp, K.fp(seg, "probe"))}
    print(f"{part}: window {w} s, lag {lag}", flush=True)
    return part, {"window_s": w, "lag": lag, "candidates": out}


def draw(pool, meta, seed):
    """The trials, by the plan's rules, deterministic in `seed`."""
    rng = random.Random(seed)
    pairs = []
    pool = {part: p for part, p in pool.items() if part not in BLEED_HEAVY}
    for part, p in sorted(pool.items()):
        ok = {c: v for c, v in p["candidates"].items()
              if all(v.get(d) is not None and v[d] > 0 for d in DISTANCES)}
        for c1, c2 in itertools.combinations(sorted(ok), 2):
            lr = {d: math.log(ok[c1][d] / ok[c2][d]) for d in DISTANCES}
            pairs.append({"part": part, "band": meta[part]["band"], "first": c1, "second": c2,
                          "log_ratio": lr, "disagree": (lr["judge"] > 0) != (lr["v3c"] > 0)})
    median = statistics.median(abs(q["log_ratio"]["judge"]) for q in pairs)
    clear = [q for q in pairs if abs(q["log_ratio"]["judge"]) > median]
    rng.shuffle(clear)
    chosen, per_part, per_cand, bands = [], {}, {}, set()

    def fits(q):
        return (per_part.get(q["part"], 0) < PER_PART
                and per_cand.get(q["first"], 0) < PER_CANDIDATE
                and per_cand.get(q["second"], 0) < PER_CANDIDATE and q not in chosen)

    def take(q):
        chosen.append(q)
        per_part[q["part"]] = per_part.get(q["part"], 0) + 1
        bands.add(q["band"])
        for c in (q["first"], q["second"]):
            per_cand[c] = per_cand.get(c, 0) + 1

    for band in sorted({q["band"] for q in clear}):        # spread over bands first
        for q in clear:
            if q["band"] == band and fits(q):
                take(q)
                break
    for q in clear:                                          # then the disagreements
        if sum(c["disagree"] for c in chosen) >= MIN_DISAGREE or len(chosen) >= TEST_PAIRS:
            break
        if q["disagree"] and fits(q):
            take(q)
    for q in clear:                                          # then fill
        if len(chosen) >= TEST_PAIRS:
            break
        if fits(q):
            take(q)
    if (len(chosen) < TEST_PAIRS or len(bands) < MIN_BANDS
            or sum(c["disagree"] for c in chosen) < MIN_DISAGREE):
        die(f"could not draw the declared trials: {len(chosen)} pairs, {len(bands)} bands, "
            f"{sum(c['disagree'] for c in chosen)} disagreements")
    tests = [{"kind": "test", "id": f"t{i:02d}", **q} for i, q in enumerate(chosen)]
    parts = sorted(pool)
    rng.shuffle(parts)
    hidden = []
    for part in parts[:HIDDEN_REFERENCES]:
        cands = sorted(pool[part]["candidates"])
        hidden.append({"kind": "hidden_reference", "part": part, "band": meta[part]["band"],
                       "first": "reference", "second": cands[rng.randrange(len(cands))]})
    repeats = [{"kind": "repeat", "of": q["id"]} for q in rng.sample(tests, REPEATS)]
    return {"excluded_bleed_heavy": [p for p in BLEED_HEAVY], "median_abs_log_ratio": median,
            "pairs_in_pool": len(pairs),
            "clear_pairs": len(clear), "trials": tests + hidden + repeats}


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("planning the listening validation")
    from benchmark_recordings import CATALOG

    panel = args.panel_dir.expanduser()
    crops = args.crops_dir.expanduser()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    meta = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            meta[slug] = {"band": s.get("group") or f"{s['source']}/{s['song']}",
                          "lag": int(round((p.get("lag_ms") or 0) * SR / 1000)),
                          "split": p.get("split") or s.get("split")}
    index = json.loads((panel / "index.json").read_text())
    files = {}
    for row in index["rows"]:
        if "file" in row:
            files.setdefault(row["part"], {})[row["candidate"]] = pathlib.Path(row["file"])
    if any(meta[p]["split"] != "development" for p in files):
        die("the panel holds a part that is not development material")
    cache = args.cache.expanduser()
    if cache.exists():
        pool = json.loads(cache.read_text())["pool"]
    else:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(args.workers) as ex:
            scored = dict(ex.map(score_part, [(p, files[p], meta[p]["lag"], crops)
                                              for p in sorted(files)]))
        pool = {p: s for p, s in scored.items() if s is not None}
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"panel": str(args.panel_dir), "pool": pool}) + "\n")
    import secrets

    out_path = args.out.expanduser()
    if out_path.exists():
        die(f"{out_path} exists; the trials are drawn once")
    seed = secrets.randbits(32)
    out = draw(pool, meta, seed)
    for trial in out["trials"]:
        if trial["kind"] != "repeat":
            p = pool[trial["part"]]
            trial.update(window_s=p["window_s"], lag=p["lag"])
            trial["predictions"] = {
                c: p["candidates"].get(c) for c in (trial["first"], trial["second"])
                if c != "reference"}
    used = [p for p in pool if p not in BLEED_HEAVY]
    out.update(seed=seed, panel=str(args.panel_dir), parts=len(used),
               bands=len({meta[p]["band"] for p in used}))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=1) + "\n"
    out_path.write_text(text)
    import hashlib

    tests = [t for t in out["trials"] if t["kind"] == "test"]
    # Counts only: the pairs themselves stay private.
    print(f"{len(used)} parts, {out['clear_pairs']} clear pairs; {len(tests)} test pairs over "
          f"{len({t['band'] for t in tests})} bands, {sum(t['disagree'] for t in tests)} where "
          f"the judge and v3c disagree; sha256 {hashlib.sha256(text.encode()).hexdigest()}")


if __name__ == "__main__":
    guarded(main)
