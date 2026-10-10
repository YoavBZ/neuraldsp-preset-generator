"""Stage 0 of `docs/sound-desc-plan.md` (v2): can any sound description track the judge?

Same-notes ceiling, no-learning and centroid picks for four declared descriptions, on the
pinned development test parts, from stored audio only (plus T(p) from `sound_desc targets`).

    $TORCH_PY -m learn.sound_desc_stage0 features     # cache frame features (CPU, parallel)
    $TORCH_PY -m learn.sound_desc_stage0 report
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

from learn import confirm_run as CR  # noqa: E402
from learn import phase2_set3 as P  # noqa: E402
from learn import set3_gap_split as G  # noqa: E402
from learn import songs_check as SC  # noqa: E402
from learn import sound_desc as S  # noqa: E402
from learn import sound_desc_eval as E  # noqa: E402

PINNED = PLUGIN_ROOT / "docs/sound-desc-test-parts.json"
CACHE = S.OUT / "stage0"
GATES = (40, 30, 25)
NAMES = ("D130", "Dlevel", "Dpct", "Dall")


def frames(x):
    """(log-mel frames, frame RMS dB) of RMS-normalised audio."""
    import numpy as np

    x = np.asarray(x, np.float64)
    x = x / (np.sqrt(np.mean(x ** 2)) + 1e-12)
    n = 1 + (len(x) - S.NFFT) // S.HOP
    idx = np.arange(S.NFFT)[None, :] + S.HOP * np.arange(n)[:, None]
    fr = x[idx]
    rms = 10 * np.log10(np.mean(fr ** 2, axis=1) + 1e-20)
    L = 10 * np.log10((np.abs(np.fft.rfft(fr * np.hanning(S.NFFT), axis=1)) ** 2) @ S._mel().T + 1e-12)
    crest = 20 * np.log10(np.abs(x).max() + 1e-12)
    return L.astype(np.float32), rms.astype(np.float32), float(crest)


def descriptors(L, rms, crest, gate):
    import numpy as np

    play = rms >= rms.max() - gate
    Lp, rp = L[play], rms[play]
    tone = Lp.mean(0)
    dyn = [crest, float(np.percentile(rp, 90) - np.percentile(rp, 10))]
    d130 = np.concatenate([tone - tone.mean(), Lp.std(0), dyn])
    q = np.quantile(rp, [1 / 3, 2 / 3])
    terc = []
    for lo, hi in ((-np.inf, q[0]), (q[0], q[1]), (q[1], np.inf)):
        m = (rp >= lo) & (rp <= hi) if np.isfinite(lo) else rp <= hi
        t = Lp[m].mean(0) if m.any() else tone
        terc.append(t - t.mean())
    dlevel = np.concatenate(terc)
    pct = np.percentile(Lp, [10, 50, 90], axis=0)
    dpct = np.concatenate([p - p.mean() for p in pct])
    return {"D130": d130, "Dlevel": dlevel, "Dpct": dpct, "Dall": np.concatenate([dlevel, dpct, dyn])}


def _part_sources():
    pin = json.loads(PINNED.read_text())
    s3, s12 = G.parts(), SC.parts()
    out = {}
    for slug, meta in pin["parts"].items():
        if slug in s3:
            out[slug] = dict(meta, ref=P.CROPS / slug / "reference.wav", meas=SC.D3 / "gap-split/measfix" / slug)
        else:
            out[slug] = dict(meta, ref=s12[slug]["crop"] / "reference.wav", meas=SC.OUT / "measfix" / slug)
    return out, pin


def _features_part(job):
    import numpy as np

    import render_preset_panel as RP

    slug, src, names = job
    halves = {"A": P.HALF_A, "B": P.HALF_B}
    rec = CR.mono(src["ref"])
    out = {"rec": {}, "render": {}}
    for h, (a, b) in halves.items():
        f = frames(rec[int(a * S.SR):int(b * S.SR)])
        out["rec"][h] = {g: {k: v.tolist() for k, v in descriptors(*f, g).items()} for g in GATES}
    for amp, ns in names.items():
        for n in ns:
            y = P.mono(src["meas"] / amp / f"{RP._slug(n)}.wav")
            for h, (a, b) in halves.items():
                f = frames(y[int(a * S.SR):int(b * S.SR)])
                out["render"][f"{amp}|{n}|{h}"] = {g: {k: v.tolist() for k, v in descriptors(*f, g).items()}
                                                   for g in GATES}
    print(slug, flush=True)
    return slug, out


def features(workers=7):
    from concurrent.futures import ProcessPoolExecutor

    srcs, _ = _part_sources()
    names = G.menu_names()
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = [s for s in srcs if not (CACHE / f"{s}.json").exists()]
    with ProcessPoolExecutor(workers) as ex:
        for slug, out in ex.map(_features_part, [(s, srcs[s], names) for s in todo]):
            (CACHE / f"{slug}.json").write_text(json.dumps(out))


def target_descriptors():
    """T(p) under each description and gate, from G's renders (computed by `targets`)."""
    import numpy as np

    path = S.OUT / "targets-frames.json"
    if path.exists():
        return {k: {int(g): {n: np.array(v) for n, v in d.items()} for g, d in gd.items()}
                for k, gd in json.loads(path.read_text()).items()}
    raise SystemExit("run `sound_desc targets` (stage-0 version) first")


def report():
    import numpy as np

    srcs, pin = _part_sources()
    feats = {s: json.loads((CACHE / f"{s}.json").read_text()) for s in srcs}
    T = target_descriptors()
    tp = E.test_parts()
    D = {s: tp[s]["D"] for s in srcs}

    def mean_halves(s, amp, n):
        a, b = D[s][f"flat|{amp}|measfix_A"][n][0], D[s][f"flat|{amp}|measfix_B"][n][0]
        return (a + b) / 2 if a and b else None

    def lbo_baseline(slug, amp):
        cls, band = srcs[slug]["gain_class"], srcs[slug]["band"]
        others = [s for s in srcs if srcs[s]["gain_class"] == cls and srcs[s]["band"] != band]
        names = [n for n in D[slug][f"flat|{amp}|measfix_A"] if n.startswith("factory:")]
        meds = {}
        for n in names:
            v = [mean_halves(s, amp, n) for s in others]
            if all(x is not None for x in v) and v:
                meds[n] = statistics.median(v)
        return min(meds, key=lambda n: (meds[n], n))

    base = {(s, a): lbo_baseline(s, a) for s in srcs for a in P.AMPS}

    def stdz(gate, desc, bands):
        allr = np.array([feats[s]["render"][k][str(gate)][desc] for s in srcs if srcs[s]["band"] in bands
                         for k in feats[s]["render"]])
        return allr.mean(0), allr.std(0) + 1e-6

    def cell_rows(gate, desc, mu, sd, parts):
        """{kind: [(slug, band, class, value)]}: part-amp cells, both directions averaged."""
        rows = {"ceiling": [], "none": [], "centroid": []}
        for s in parts:
            others = [o for o in srcs if srcs[o]["band"] != srcs[s]["band"]]
            for amp in P.AMPS:
                names = list(D[s][f"flat|{amp}|measfix_A"])
                vals = {k: [] for k in rows}
                for h, other in (("A", "B"), ("B", "A")):
                    r = (np.array(feats[s]["rec"][h][str(gate)][desc]) - mu) / sd
                    cand = {
                        "ceiling": {n: (np.array(feats[s]["render"][f"{amp}|{n}|{h}"][str(gate)][desc]) - mu) / sd
                                    for n in names},
                        "none": {n: (T[desc][gate][f"{amp}|{n}"] - mu) / sd for n in names
                                 if f"{amp}|{n}" in T[desc][gate]},
                        "centroid": {n: (np.mean([feats[o]["render"][f"{amp}|{n}|{h}"][str(gate)][desc]
                                                  for o in others], axis=0) - mu) / sd for n in names}}
                    M, b = D[s][f"flat|{amp}|measfix_{other}"], base[(s, amp)]
                    for k in rows:
                        pick = min(cand[k], key=lambda n: float(((cand[k][n] - r) ** 2).sum()))
                        if M.get(pick) and M[pick][0] and M[b][0]:
                            vals[k].append(math.log(M[pick][0] / M[b][0]))
                for k in rows:
                    if len(vals[k]) == 2:
                        rows[k].append((s, srcs[s]["band"], srcs[s]["gain_class"], statistics.fmean(vals[k])))
        return rows

    bands = sorted({v["band"] for v in srcs.values()})
    results, chosen = {}, {}
    for gate in GATES:
        # Amendment 1: leave-one-band-out selection, standardised on the selecting bands.
        lobo = {"ceiling": [], "none": [], "centroid": []}
        for b in bands:
            rest = [x for x in bands if x != b]
            best = None
            for desc in NAMES:
                mu, sd = stdz(gate, desc, rest)
                rr = cell_rows(gate, desc, mu, sd, [s for s in srcs if srcs[s]["band"] != b])
                m = statistics.fmean(x[3] for x in rr["ceiling"])
                if best is None or m < best[0]:
                    best = (m, desc, mu, sd)
            chosen[f"{gate}|{b}"] = best[1]
            held = cell_rows(gate, best[1], best[2], best[3], [s for s in srcs if srcs[s]["band"] == b])
            for k in lobo:
                lobo[k] += held[k]
        for k, rs in lobo.items():
            for stratum in ("all", "clean", "crunch"):
                sel = [(bd, x) for s, bd, c, x in rs if stratum == "all" or c == stratum]
                if sel:
                    results[f"{gate}|LOBO|{k}|{stratum}"] = CR.stats(sel)
        # Each description over all 15 bands (reported; the best is carried into stage 1).
        for desc in NAMES:
            mu, sd = stdz(gate, desc, bands)
            rr = cell_rows(gate, desc, mu, sd, list(srcs))
            for k, rs in rr.items():
                for stratum in ("all", "clean", "crunch"):
                    sel = [(bd, x) for s, bd, c, x in rs if stratum == "all" or c == stratum]
                    if sel:
                        results[f"{gate}|{desc}|{k}|{stratum}"] = CR.stats(sel)
    v = results["40|LOBO|ceiling|crunch"]
    passed = v["mean"] <= -0.04 and v["wins"] > v["losses"]
    carried = min(NAMES, key=lambda d: results[f"40|{d}|ceiling|all"]["mean"])
    out = {"passes": passed, "deciding": v, "carried_description": carried, "lobo_choices": chosen,
           "results": results, "baselines": {f"{s}|{a}": n for (s, a), n in base.items()}}
    (S.OUT / "stage0-result.json").write_text(json.dumps(out, indent=1, default=float))
    print("STAGE 0:", "PASSES" if passed else "FAILS", "| crunch LOBO ceiling", v["mean"], v["lo90"], v["hi90"],
          f"W/T/L {v['wins']}/{v['ties']}/{v['losses']}", "| carried:", carried)
    for k in sorted(results):
        if k.startswith("40|"):
            s_ = results[k]
            print(f"  {k:34s} mean {s_['mean']:+.3f} [{s_['lo90']:+.3f}, {s_['hi90']:+.3f}] "
                  f"W/T/L {s_['wins']}/{s_['ties']}/{s_['losses']} bands {s_['bands']}")
    return out


if __name__ == "__main__":
    {"features": features, "report": report}[sys.argv[1]]()
