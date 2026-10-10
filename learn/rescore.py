"""Re-score set-3 development choices under the fixed-level measure, both judge versions
and both halves (`docs/closeness-review-2026-10-10.md`, decisions of 2026-10-10).

No renders: every option is a stored render.
- `measfix`: the measure DI at −22.9 LUFS (`gap-split/measfix`), at the part's judge lag.
  It is both the oracle's chooser and the measure.
- `net`: the stored rebuilt DIs (`phase2-set3/net`), lag −52, with the fallback.
- `lp3k`: the same low-passed at 3 kHz (`v2-eval/lp3k`).

    $TORCH_PY -m learn.rescore score      # distances.json
    $TORCH_PY -m learn.rescore report     # summary.json and the printed table
"""

from __future__ import annotations

import json
import math
import pathlib
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import phase2_set3 as P  # noqa: E402
from learn import set3_gap_split as G  # noqa: E402

DIRS = {"measfix": G.OUT / "measfix", "net": P.OUT / "net", "lp3k": P.OUT.with_name("v2-eval") / "lp3k"}
OUT = P.OUT.with_name("rescore")
JUDGES = ("flat", "hearing")
HALVES = {"A": P.HALF_A, "B": P.HALF_B}
CONSTANT = {"pr12": "factory:Neural DSP/Vintage Metal",
            "sw50r": "factory:Artists/Royce Whittaker/Wall Of Doom",
            "ac20": "factory:Artists/Charlie Robbins/Dirty Coil Rhythm"}


def _score_part(job):
    import numpy as np

    import render_preset_panel as RP
    from analysis.aligned import aligned_distance
    from learn.rebuilt_judge import rebuilt_distance

    slug, lag, names = job
    ref = P.recording(slug, "ref", P.RunConfig())
    res = {}
    for kind, root in DIRS.items():
        d = root / slug
        di = np.load(d / "di.npy")
        for amp, ns in names.items():
            for n in ns:
                y = P.mono(d / amp / f"{RP._slug(n)}.wav")
                for judge in JUDGES:
                    for h, (a, b) in HALVES.items():
                        if kind == "measfix":
                            x = aligned_distance(ref, y, di, lag=lag, render_latency=P.LATENCY,
                                                 start_s=a, end_s=b, weighting=judge)
                        else:
                            x, _ = rebuilt_distance(ref, y, di, start_s=a, end_s=b, weighting=judge)
                        res.setdefault(f"{judge}|{amp}|{kind}_{h}", {})[n] = (
                            x.distance, x.tonal, x.temporal)
    print(slug, flush=True)
    return slug, res


def score(workers=7):
    from concurrent.futures import ProcessPoolExecutor

    ps, names = G.parts(), G.menu_names()
    with ProcessPoolExecutor(workers) as ex:
        D = dict(ex.map(_score_part, [(s, ps[s]["judge_lag_samples"], names) for s in sorted(ps)]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "distances.json").write_text(json.dumps(D))


def clustered(rows):
    """rows: (band, x). Part-weighted mean, band-clustered 90% interval (t, bands − 1 df),
    exact band sign flip on band totals, wins/ties/losses."""
    import itertools

    from scipy import stats

    xs = [x for _, x in rows]
    n, m = len(xs), statistics.fmean(xs)
    by = {}
    for b, x in rows:
        by.setdefault(b, []).append(x)
    g = len(by)
    se = math.sqrt(g / (g - 1) * sum(sum(x - m for x in v) ** 2 for v in by.values())) / n
    t = stats.t.ppf(0.95, g - 1)
    tot = [sum(v) for v in by.values()]
    obs = abs(sum(tot))
    p = sum(abs(sum(s * v for s, v in zip(sg, tot))) >= obs - 1e-12
            for sg in itertools.product((1, -1), repeat=g)) / 2 ** g
    return {"mean": round(m, 4), "lo90": round(m - t * se, 4), "hi90": round(m + t * se, 4),
            "p_band_flip": round(p, 4), "wins": sum(x < -1e-9 for x in xs),
            "ties": sum(abs(x) <= 1e-9 for x in xs), "losses": sum(x > 1e-9 for x in xs),
            "n": n, "bands": g}


def report():
    D = json.loads((OUT / "distances.json").read_text())
    ps = G.parts()
    out = {}

    def pick(row, exclude=()):
        row = {n: v[0] for n, v in row.items() if v[0]}
        return min(row, key=lambda n: (row[n], n)) if row else None

    for judge in JUDGES:
        comps = {}
        for amp in P.AMPS:
            # The leave-band-out constant: lowest median choosing-half measfix distance over
            # other bands' parts; recomputed for each scoring direction.
            for choose, scoreh in (("A", "B"), ("B", "A")):
                for slug, p in sorted(ps.items()):
                    meas = D[slug][f"{judge}|{amp}|measfix_{scoreh}"]
                    others = [s for s, q in ps.items() if q["band"] != p["band"]]
                    meds = {}
                    for n in meas:
                        if not n.startswith("factory:"):
                            continue
                        v = [D[s][f"{judge}|{amp}|measfix_{choose}"][n][0] for s in others]
                        v = [x for x in v if x]
                        if v:
                            meds[n] = statistics.median(v)
                    lbo = min(meds, key=lambda n: (meds[n], n))
                    picks = {k: pick(D[slug][f"{judge}|{amp}|{k}_{choose}"]) for k in ("measfix", "net", "lp3k")}
                    picks.update(constant=CONSTANT[amp], lbo_constant=lbo, template="template+R")
                    lB = {k: (math.log(meas[n][0]) if n and meas.get(n) and meas[n][0] else None)
                          for k, n in picks.items()}
                    tB = {k: (meas[n][1], meas[n][2]) if n and meas.get(n) and meas[n][0] else None
                          for k, n in picks.items()}
                    for a, b in (("lp3k", "net"), ("net", "lbo_constant"), ("lp3k", "lbo_constant"),
                                 ("measfix", "lbo_constant"), ("measfix", "net"), ("net", "constant"),
                                 ("lp3k", "constant"), ("lbo_constant", "template")):
                        if lB[a] is None or lB[b] is None:
                            continue
                        key = f"{a}_vs_{b}"
                        c = comps.setdefault(key, {})
                        c.setdefault((slug, amp), []).append(lB[a] - lB[b])
                        ct = comps.setdefault(key + "|tonal", {})
                        ct.setdefault((slug, amp), []).append(math.log(tB[a][0] / tB[b][0]))
                        cm = comps.setdefault(key + "|temporal", {})
                        cm.setdefault((slug, amp), []).append(math.log(tB[a][1] / tB[b][1]))
        res = {}
        for key, cells in comps.items():
            # Both scoring directions averaged per part-amp cell.
            rows = [(ps[s]["band"], statistics.fmean(v)) for (s, a), v in cells.items()]
            res[key] = clustered(rows)
        out[judge] = res
    (OUT / "summary.json").write_text(json.dumps(out, indent=1))
    for judge, res in out.items():
        print(f"== judge {judge} (fixed-level measure, both halves averaged)")
        for k, v in res.items():
            print(f"  {k:36s} mean {v['mean']:+.3f} 90% [{v['lo90']:+.3f}, {v['hi90']:+.3f}] "
                  f"p {v['p_band_flip']:.3f} W/T/L {v['wins']}/{v['ties']}/{v['losses']}")


if __name__ == "__main__":
    {"score": score, "report": report}[sys.argv[1]]()
