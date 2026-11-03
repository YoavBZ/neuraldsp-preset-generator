"""The judge revised to weigh changes as the ear does (docs/pipeline-fix-plan.md; ledger `pipeline-fix`, key
`phase_judge_ear_v4`; descriptive, for one listener). Candidates beside the judge as it is (J0):

- J1: J0 with each scored mel band's |ΔdB| weighted by the reference's loudness share in it (Zwicker time-varying
  loudness, `mosqito`, on the reference only, its RMS set to 70 dB SPL; specific loudness per 0.1 Bark summed into
  the mel bands, normalised over the scored bands). Excess a render adds in a band quiet in the reference counts
  little (an asymmetry).
- J2: w_t x J1's tonal part + J1-weighted frame-wise residual + w_d x a decay part (after each DI note end, the
  energy in min(1.5 s, time to the next onset) over the note's own, per band, render against reference, |ΔdB|).
  J2-fallback: the decay part dropped and w_t refitted alone.

Stage A (zero renders) screens them in-sample on the judge-ear pages' stored renders and answers:

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    PYTHONPATH=. $MAIN -m learn.judge_v4 screen

`cells` re-traces `analysis.aligned.aligned_distance`'s default path (bands "recording", flat weighting, the
recording's floor) and keeps the cell differences; `j0` from them reproduces `aligned_distance` (tested).
"""

from __future__ import annotations

import argparse
import json
import math
import time

from learn import judge_ear as JE

W_T_GRID = [round(0.1 * i, 1) for i in range(11)]
W_D_GRID = [round(0.1 * i, 1) for i in range(21)]
SPL_DB = 70.0
DECAY_MAX_S = 1.5
MIN_WINDOW_S = 0.3
MIN_NOTE_ENDS = 8
RATING = {"same": 0, "barely": 1, "clearly": 2, "very": 3}


# --- the cells ------------------------------------------------------------------------------------------------------

def cells(recording, render, di, *, lag=0, render_latency=52, sample_rate=48000, start_s=1.0, end_s=None,
          tail_s=1.5, floor_db=30.0, mask_db=40.0, di_floor_db=40.0):
    """Per frame size, the judge's scored cell differences D (frames x bands, level and mean offset removed), the
    scored bands' centres, the playing and scored masks and the hop; plus the reference's normalised window.
    None where `aligned_distance` would refuse."""
    import numpy as np

    from analysis import aligned as AL

    recording, render, di = AL._signal(recording, "recording"), AL._signal(render, "render"), AL._signal(di, "di")
    shift = int(lag)
    end = min(len(recording), len(render) + shift)
    if end_s is not None:
        end = min(end, int(end_s * sample_rate))
    start = max(int(start_s * sample_rate), shift if shift > 0 else 0)
    if end - start < sample_rate:
        return None
    ref = recording[start:end]
    ren = render[start - shift: end - shift]
    di_start = start - shift - render_latency
    ref_n, ren_n = AL._normalise(ref, sample_rate), AL._normalise(ren, sample_rate)
    if ref_n is None or ren_n is None:
        return None
    out = []
    for n_fft in AL.FRAME_SIZES:
        hop = n_fft // 4
        R, centres = AL._logmel(ref_n, n_fft, sample_rate)
        X, _ = AL._logmel(ren_n, n_fft, sample_rate)
        k = min(len(R), len(X))
        R, X = R[:k], X[:k]
        tail = int(round(tail_s * sample_rate / hop))
        pre = int(math.ceil(tail_s * sample_rate / hop))
        dseg = AL._segment(di, di_start - pre * hop, len(ref) + pre * hop)
        playing = AL._frame_db(dseg, n_fft) >= AL._frame_db(di, n_fft).max() - di_floor_db
        scored = AL._extend(playing, tail)
        playing, scored = playing[pre: pre + k], scored[pre: pre + k]
        floor_r = np.maximum(R.max() - 70.0, R.max(axis=1, keepdims=True) - mask_db)
        audible = R >= floor_r
        ltas_r = 10 * np.log10(np.mean(10 ** (np.maximum(R, floor_r)[scored] / 10), axis=0))
        bins = ltas_r >= ltas_r.max() - floor_db
        cl = audible[playing][:, bins]
        if playing.sum() < 8 or cl.sum() < 8 * bins.sum():
            return None
        level = float(np.median((X[playing][:, bins] - R[playing][:, bins])[cl]))
        Rf, Xf = np.maximum(R, floor_r), np.maximum(X - level, floor_r)
        D = Xf[scored][:, bins] - Rf[scored][:, bins]
        D = D - D.mean()
        out.append({"n_fft": n_fft, "hop": hop, "D": D, "centres": np.asarray(centres)[bins],
                    "all_centres": np.asarray(centres), "bins": bins, "playing": playing, "scored": scored,
                    "R": Rf, "X": Xf})
    return {"frames": out, "ref": ref_n, "sr": sample_rate}


def j0(c):
    import numpy as np

    return float(np.mean([np.mean(np.abs(f["D"])) for f in c["frames"]]))


# --- J1's band weights ----------------------------------------------------------------------------------------------

def bark_to_hz(z):
    """Traunmüller (1990), inverted."""
    import numpy as np

    z = np.asarray(z, float)
    return 1960.0 * (z + 0.53) / (26.28 - z)


def band_edges(centres):
    """Mel bands' edges from their centres (midpoints; the outer edges mirrored)."""
    import numpy as np

    c = np.asarray(centres, float)
    mid = (c[1:] + c[:-1]) / 2
    return np.concatenate([[c[0] - (mid[0] - c[0])], mid, [c[-1] + (c[-1] - mid[-1])]])


def specific_loudness(ref, sr=48000):
    """Time-averaged Zwicker specific loudness (sone per 0.1 Bark) of `ref` at SPL_DB RMS, and the bins' Hz."""
    import numpy as np
    from mosqito.sq_metrics import loudness_zwtv

    x = np.asarray(ref, float)
    pa = x * (2e-5 * 10 ** (SPL_DB / 20)) / (np.sqrt(np.mean(x ** 2)) + 1e-20)
    _, Nspec, bark, t = loudness_zwtv(pa, sr, field_type="free")
    return np.asarray(Nspec)[:, np.asarray(t) >= 0.2].mean(axis=1), bark_to_hz(bark)


def loudness_weights(spec, spec_hz, all_centres, bins):
    """Per scored band, the share of the reference's specific loudness whose bins fall in it."""
    import numpy as np

    e = band_edges(all_centres)
    w = np.array([spec[(spec_hz >= e[i]) & (spec_hz < e[i + 1])].sum() for i in range(len(all_centres))])[bins]
    return w / w.sum() if w.sum() > 0 else np.full(len(w), 1.0 / len(w))


# --- the parts -------------------------------------------------------------------------------------------------------

def parts(c, spec, spec_hz):
    """J1 and J2's parts on one window: j1, tonal (weighted |per-band mean|), residual (weighted mean |D - mean|),
    and the decay part (None with no note end)."""
    import numpy as np

    tot, ton, res = [], [], []
    for f in c["frames"]:
        w = loudness_weights(spec, spec_hz, f["all_centres"], f["bins"])
        D = f["D"]
        pb = D.mean(axis=0)
        tot.append(float(np.sum(w * np.mean(np.abs(D), axis=0))))
        ton.append(float(np.sum(w * np.abs(pb))))
        res.append(float(np.sum(w * np.mean(np.abs(D - pb), axis=0))))
    mid = next(f for f in c["frames"] if f["n_fft"] == 2048)
    dec, n = decay_part(mid, c["sr"], loudness_weights(spec, spec_hz, mid["all_centres"], mid["bins"]))
    return {"j1": float(np.mean(tot)), "tonal": float(np.mean(ton)), "residual": float(np.mean(res)),
            "decay": dec, "note_ends": n}


def note_windows(playing, hop, sr):
    """(onset, end, window end) frame indices per note end: playing -> not playing, the window min(1.5 s, the next
    onset), kept if at least 0.3 s."""
    import numpy as np

    p = np.asarray(playing, bool)
    on = list(np.nonzero(p & ~np.r_[False, p[:-1]])[0])
    off = list(np.nonzero(~p & np.r_[False, p[:-1]])[0])
    out, maxf, minf = [], int(round(DECAY_MAX_S * sr / hop)), int(round(MIN_WINDOW_S * sr / hop))
    for e in off:
        prev = [o for o in on if o < e]
        nxt = [o for o in on if o > e]
        if not prev:
            continue
        stop = min(e + maxf, nxt[0] if nxt else len(p), len(p))
        if stop - e >= minf:
            out.append((prev[-1], e, stop))
    return out


def decay_part(f, sr, w):
    """Weighted mean over bands and note ends of |(window over note, render) - (window over note, reference)| in
    dB, on the floored levels the judge scores. -> (value or None, note ends)."""
    import numpy as np

    wins = note_windows(f["playing"], f["hop"], sr)
    if not wins:
        return None, 0
    R, X, b = f["R"][:, f["bins"]], f["X"][:, f["bins"]], f["bins"]
    vals = []
    for o, e, s in wins:
        def ratio(M):
            note = 10 * np.log10(np.mean(10 ** (M[o:e] / 10), axis=0))
            win = 10 * np.log10(np.mean(10 ** (M[e:s] / 10), axis=0))
            return win - note
        vals.append(np.sum(w * np.abs(ratio(X) - ratio(R))))
    return float(np.mean(vals)), len(wins)


def j2(p, w_t, w_d, fallback=False):
    if fallback or p["decay"] is None:
        return w_t * p["tonal"] + p["residual"]
    return w_t * p["tonal"] + p["residual"] + w_d * p["decay"]


# --- the statistic --------------------------------------------------------------------------------------------------

def cross_group_gamma(items, score):
    """Goodman-Kruskal gamma over item pairs from different groups with different ratings. items: [{group, ear}]."""
    c = d = 0
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if a["group"] == b["group"] or a["ear"] == b["ear"]:
                continue
            s = (score(a) - score(b)) * (a["ear"] - b["ear"])
            c += s > 0
            d += s < 0
    return (c - d) / (c + d) if c + d else float("nan")


def fit(items, value, wd_grid=None):
    """The grid's (w_t, w_d) with the highest gamma, ties to the larger w_t and the smaller w_d."""
    best = None
    for w_t in W_T_GRID:
        for w_d in (W_D_GRID if wd_grid is None else wd_grid):
            g = cross_group_gamma(items, lambda it: value(it, w_t, w_d))
            key = (g, w_t, -w_d)
            if best is None or key > best[0]:
                best = (key, w_t, w_d, g)
    return best[1], best[2], best[3]


# --- stage A's screen -------------------------------------------------------------------------------------------------

def screen_items():
    """The rated items: F44's 24 pairs (F45's re-heard ones with their headphone rating, a repeat averaged) and the
    9 anchors; catches and the anchors page's repeat of clean reverb 0.40 left out."""
    d = JE.out_dir()
    first = {r["pair"]: r for r in JE.load(d / "score.json")["rows"]}
    re_ = {}
    for r in JE.load(d / "score-recheck.json")["rows"]:
        re_.setdefault(r["pair"], []).append(RATING[r["rating"]])
    items = []
    for pair, r in first.items():
        if r["group"] == JE.CATCH:
            continue
        ear, src = (sum(re_[pair]) / len(re_[pair]), "headphones") if pair in re_ else (RATING[r["rating"]], "phone")
        items.append({"item": pair, "cls": r["cls"], "group": r["group"], "ear": ear, "source": src})
    for r in JE.load(d / "anchors-score.json")["rows"]:
        if "-anchor-" in r["item"]:
            items.append({"item": r["item"], "cls": r["item"].split("-")[0], "group": "anchor",
                          "ear": RATING[r["rating"]], "source": "headphones"})
    return items


def cmd_screen(args):
    JE.require_v4()
    import numpy as np

    from learn import knob_ceiling as K

    d = JE.out_dir()
    plan = JE.load(d / "plan.json")
    di = np.asarray(np.load(d / "di.npy"), np.float64)
    lo, hi = JE.trim()
    di = di[lo:hi]
    audio = JE.anchor_audio()
    for p in plan["pairs"]:
        if p["pair"] not in audio:
            audio[p["pair"]] = (np.load(JE.render_path(JE.DATA, f"{p['cls']}-S")),
                                np.load(JE.render_path(JE.DATA, JE.job_of(p))))
    items = screen_items()
    spec = {}
    per = {}
    for it in items:
        s, o = audio[it["item"]]
        halves = {}
        for h, (a, b) in K.R.HALVES.items():
            c = cells(s, o, di, lag=0, render_latency=K.P.LATENCY, start_s=a, end_s=b)
            key = (it["cls"], h)
            if key not in spec:
                spec[key] = specific_loudness(c["ref"])
            halves[h] = {"j0": j0(c), **parts(c, *spec[key])}
        it["halves"] = halves
        per[it["item"]] = halves
        print(f"{it['item']:24s} ear {it['ear']:.1f} j0 {np.mean([v['j0'] for v in halves.values()]):.3f} "
              f"j1 {np.mean([v['j1'] for v in halves.values()]):.3f} ends {[v['note_ends'] for v in halves.values()]}",
              flush=True)

    def mean(it, f):
        return float(np.mean([f(v) for v in it["halves"].values()]))

    def j2v(it, w_t, w_d):
        return mean(it, lambda v: j2(v, w_t, w_d))

    def j2f(it, w_t, _):
        return mean(it, lambda v: j2(v, w_t, 0, fallback=True))

    w_t, w_d, g2 = fit(items, j2v)
    w_tf, _, g2f = fit(items, j2f, wd_grid=[0.0])
    scores = {"J0": lambda it: mean(it, lambda v: v["j0"]), "J1": lambda it: mean(it, lambda v: v["j1"]),
              "J2": lambda it: j2v(it, w_t, w_d), "J2-fallback": lambda it: j2f(it, w_tf, 0)}
    rec = JE.load(d / "score-recheck.json")
    inv = rec["inversions"]
    distinct = {(x["heard"], x["quiet"]) for x in inv}
    within = {(x["heard"], x["quiet"]) for x in inv if x["both_halves"] and x["same_preset"]}
    by = {it["item"]: it for it in items}
    out = {}
    for name, f in scores.items():
        left = {k for k in distinct if f(by[k[0]]) < f(by[k[1]])}
        out[name] = {"gamma": cross_group_gamma(items, f), "inversions_left": len(left), "of": len(distinct),
                     "within_left": len(left & within), "within_of": len(within)}
        print(f"{name:12s} in-sample gamma {out[name]['gamma']:+.3f}  F45 inversions left {len(left)}/{len(distinct)}"
              f"  within-preset both-halves left {len(left & within)}/{len(within)}")
    print(f"J2 weights w_t {w_t} w_d {w_d}; J2-fallback w_t {w_tf}")
    JE.save(d / "v4-screen.json", {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "items": [
        {k: v for k, v in it.items()} for it in items], "weights": {"J2": [w_t, w_d], "J2-fallback": [w_tf]},
        "results": out})


def main(argv=None):
    ap = argparse.ArgumentParser(prog="judge_v4", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["screen"])
    args = ap.parse_args(argv)
    {"screen": cmd_screen}[args.cmd](args)


if __name__ == "__main__":
    main()
