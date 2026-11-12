"""T0, the effects route's zero-render test (`docs/full-controls-plan.md`, "T0 in detail"; ledger `pipeline-fix` `phase_t0`).
Can fixed, effect-aware features match a recording to effect settings made on *other* performances (render-and-compare's
core assumption), and does the separated stem keep them? On E1e's 770 wide draws (clean target, rebuilt mix, re-separated
stem; exact labels), by leave-one-song-out nearest neighbours, against the draw-aware prior and "off".

    .venv/bin/python -m learn.fx_t0 t0-features          # the features of every item's target, mix and stem (CPU)
    .venv/bin/python -m learn.fx_t0 t0-read              # the read and the rule (CPU)

The pure parts (the features on synthetic signals, the neighbours, the rule) are unit-tested.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time

PHASE = "phase_t0"
SR = 48000
HOP = 480                                   # 10 ms
WIN = 1920
BANDS = ((100, 400), (400, 1600), (1600, 6400))
K = 15                                      # neighbours
BOOT_N, BOOT_SEED = 2000, 20261131
ARMS = ("target", "stem", "mix")
EFFECTS = {                                 # effect -> (on column, strength column, knobs and their error scale)
    "reverb": ("ron", "rmix", {"rmix": "abs", "rdecay": "log2"}),
    "delay": ("don", "dmix", {"dmix": "abs", "dtime": "log2", "dfb": "abs"}),
    "tremolo": ("ton", "tdepth", {"tdepth": "abs", "trate": "log2"}),
}
FEATURES = ("fast_b1", "fast_b2", "fast_b3", "fill_b1", "fill_b2", "fill_b3", "late_early",
            "cep_lag", "cep_h", "acf_lag", "acf_p", "mod_f", "mod_p")


def root():
    return os.path.expanduser("~/ndsp-presets/learn/trusted-data/judge-v5/fx-reader")


def out_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "t0"


# --- the features (fixed before the read) ---------------------------------------------------------------------------------

def _mono(y):
    import numpy as np

    y = np.asarray(y, np.float64)
    return y.mean(1) if y.ndim == 2 else y


def band_db(y):
    """Each band's energy per 10 ms frame, in dB, floored 80 dB under its own peak. -> [bands, frames]."""
    import numpy as np

    y = _mono(y)
    if len(y) < WIN:
        y = np.pad(y, (0, WIN - len(y)))
    fr = np.lib.stride_tricks.sliding_window_view(y, WIN)[::HOP] * np.hanning(WIN)
    P = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(WIN, 1 / SR)
    out = []
    for lo, hi in BANDS:
        e = 10 * np.log10(P[:, (f >= lo) & (f < hi)].sum(1) + 1e-20)
        out.append(np.maximum(e, e.max() - 80))
    return np.stack(out)


def decay_fast(e, span=15, within=30.0):
    """The 10th percentile of the 150 ms least-squares slope (dB/s) where the band falls within `within` dB of its peak:
    the steepest decays, which a reverb makes shallower."""
    import numpy as np

    t = np.arange(span) * HOP / SR
    t = t - t.mean()
    sl = []
    for i in range(len(e) - span):
        seg = e[i:i + span]
        if seg[0] < e.max() - within:
            continue
        s = float(((seg - seg.mean()) * t).sum() / (t * t).sum())
        if s < 0:
            sl.append(s)
    return float(np.percentile(sl, 10)) if sl else 0.0


def fill(e):
    """The 10th percentile less the 90th (dB): how far the gaps fall, which a reverb or delay fills."""
    import numpy as np

    return float(np.percentile(e, 10) - np.percentile(e, 90))


def late_early(e_bb):
    """The median over onsets (a 6 dB rise within 30 ms) of the energy 200-500 ms after less 0-100 ms (dB)."""
    import numpy as np

    lin = 10 ** (e_bb / 10)
    v = []
    for i in range(3, len(e_bb) - 50):
        if e_bb[i] - e_bb[i - 3] >= 6 and e_bb[i] >= e_bb.max() - 30:
            early, late = lin[i:i + 10].mean(), lin[i + 20:i + 50].mean()
            v.append(10 * math.log10(late / early + 1e-12))
    return float(np.median(v)) if v else -30.0


def acf_peak(e_bb, lo=6, hi=80, side=10):
    """The broadband dB envelope's normalised autocorrelation: its highest local maximum at 60-800 ms (log2 ms) and its
    height over the lowest value within `side` frames (100 ms) either side; (log2 of 60 ms, 0) if none."""
    import numpy as np

    x = e_bb - e_bb.mean()
    n = len(x)
    f = np.fft.rfft(x, 2 * n)
    ac = np.fft.irfft(np.abs(f) ** 2)[: hi + side + 1]
    ac = ac / max(ac[0], 1e-12)
    best = None
    for k in range(lo, hi + 1):
        if ac[k] > ac[k - 1] and ac[k] >= ac[k + 1]:
            p = float(ac[k] - ac[max(1, k - side):k + side + 1].min())
            if best is None or ac[k] > best[2]:
                best = (k, p, ac[k])
    return (math.log2(10.0 * best[0]), best[1]) if best else (math.log2(10.0 * lo), 0.0)


def modulation(y, lo=0.8, hi=12.0):
    """The broadband amplitude envelope (10 ms), divided by its 1 s moving mean (notes removed): the power spectrum's
    peak in 0.8-12 Hz (log2 Hz) and its prominence over the band's median (dB). A tremolo shows here."""
    import numpy as np

    y = _mono(y)
    fr = np.lib.stride_tricks.sliding_window_view(np.pad(y, (0, max(0, WIN - len(y)))), WIN)[::HOP]
    env = np.sqrt((fr ** 2).mean(1)) + 1e-9
    k = 100
    mov = np.convolve(env, np.ones(k) / k, mode="same") + 1e-9
    r = env / mov - 1.0
    r = r[k:-k] if len(r) > 3 * k else r
    S = np.abs(np.fft.rfft(r * np.hanning(len(r)))) ** 2
    f = np.fft.rfftfreq(len(r), HOP / SR)
    m = (f >= lo) & (f <= hi)
    j = int(np.argmax(S[m]))
    return math.log2(float(f[m][j])), float(10 * np.log10(S[m][j] / (np.median(S[m]) + 1e-20)))


def features(y):
    """The fixed feature vector (FEATURES' order) of one recording."""
    from learn import fx_reader as FX

    e = band_db(y)
    bb = 10 * __import__("numpy").log10((10 ** (e / 10)).sum(0))
    lag, h = FX.cep_pick(FX.cepstrum(_mono(y)), FX.CEP_RANGE)
    al, ap = acf_peak(bb)
    mf, mp = modulation(y)
    return [decay_fast(e[0]), decay_fast(e[1]), decay_fast(e[2]), fill(e[0]), fill(e[1]), fill(e[2]), late_early(bb),
            math.log2(lag), h, al, ap, mf, mp]


# --- the labels, the neighbours and the read ------------------------------------------------------------------------------

def labels(s):
    """An item's truth from its stored settings: on/off, strength and the knobs (log2 for times, decays and rates)."""
    on = lambda k: s.get(k) == "true"            # noqa: E731
    nan = float("nan")
    ron, don, ton = on("reverb/reverbActive"), on("delay/delayActive"), on("tremolo/tremoloActive")
    return {"ron": float(ron), "don": float(don), "ton": float(ton),
            "rmix": float(s["reverb/reverbMix"]) if ron else nan,
            "rdecay": math.log2(float(s["reverb/reverbDecay"])) if ron else nan,
            "dmix": float(s["delay/delayMix"]) if don else nan,
            "dtime": math.log2(float(s["delay/delayTime"])) if don else nan,
            "dfb": float(s["delay/delayFeedback"]) if don else nan,
            "tdepth": float(s["tremolo/tremoloDepth"]) if ton else nan,
            "trate": math.log2(float(s["tremolo/tremoloRate"])) if ton else nan}


def standardise(lib, q):
    import numpy as np

    mu, sd = lib.mean(0), lib.std(0) + 1e-9
    return (lib - mu) / sd, (q - mu) / sd


def neighbours(lib_x, q_x, k=K):
    """Each query's k nearest library rows (Euclidean on features standardised by the library). -> [queries, k]."""
    import numpy as np

    L, Q = standardise(lib_x, q_x)
    d = ((Q[:, None, :] - L[None, :, :]) ** 2).sum(-1)
    return np.argsort(d, axis=1)[:, :k]


def loso(X_lib, X_q, Y, songs, k=K):
    """Leave-one-song-out predictions: for each query item, the k nearest of the other songs' library items. -> {col:
    predicted value} for on columns (the neighbours' on-share) and knobs (the median among neighbours with it on, or the
    draw-aware prior where none is), and the draw-aware prior itself."""
    import numpy as np

    n = len(songs)
    cols = list(Y)
    pred = {c: np.full(n, np.nan) for c in cols}
    prior = {c: np.full(n, np.nan) for c in cols}
    for s in sorted(set(songs)):
        te = np.where(songs == s)[0]
        tr = np.where(songs != s)[0]
        nb = tr[neighbours(X_lib[tr], X_q[te], k)]
        for c in cols:
            y = Y[c]
            prior[c][te] = np.nanmedian(y[tr]) if np.isfinite(y[tr]).any() else np.nan
            for j, row in zip(te, nb):
                v = y[row]
                if c in ("ron", "don", "ton"):
                    pred[c][j] = float(np.mean(v))
                else:
                    v = v[np.isfinite(v)]
                    pred[c][j] = float(np.median(v)) if len(v) else prior[c][j]
    return pred, prior


def err(kind, a, b):
    import numpy as np

    return np.abs(a - b)                      # log2 columns are already in log2, so abs is the log2 error


def boot(fn, songs, n=BOOT_N, seed=BOOT_SEED):
    """A 90% interval by resampling songs (the clusters)."""
    import numpy as np

    rng = np.random.default_rng(seed)
    u = np.array(sorted(set(songs)))
    vals = []
    for _ in range(n):
        pick = rng.choice(u, len(u), replace=True)
        idx = np.concatenate([np.where(songs == s)[0] for s in pick])
        v = fn(idx)
        if v == v:
            vals.append(v)
    return [float(np.percentile(vals, 5)), float(np.percentile(vals, 95))] if vals else [None, None]


def read_arm(pred, prior, Y, songs):
    """One arm's read: per effect, on/off AUC (all and the strong third) and each knob's error less the draw-aware
    prior's, on the strong third, with song-bootstrap intervals."""
    import numpy as np

    from learn import fx_reader as FX

    out = {}
    for eff, (oncol, strcol, knobs) in EFFECTS.items():
        y, s = Y[oncol], pred[oncol]
        strength = Y[strcol]
        ons = y == 1
        hi = float(np.nanpercentile(strength[ons], 200 / 3))
        strong = (y == 0) | (ons & (strength >= hi))
        r = {"strong_from": hi}
        for nm, m in (("all", np.ones_like(y, bool)), ("strong_third", strong)):
            r[nm] = {"auc": FX.auc(y[m], s[m]),
                     "auc_ci": boot(lambda b: FX.auc(y[b][m[b]], s[b][m[b]]), songs)}
        kn = {}
        so = ons & (strength >= hi)
        for k, kind in knobs.items():
            e_n, e_p = err(kind, pred[k], Y[k]), err(kind, prior[k], Y[k])
            kn[k] = {"n": int(so.sum()), "mae": float(np.mean(e_n[so])), "mae_prior": float(np.mean(e_p[so])),
                     "diff": float(np.mean(e_n[so]) - np.mean(e_p[so])),
                     "diff_ci": boot(lambda b: float(np.mean(e_n[b][so[b]]) - np.mean(e_p[b][so[b]])), songs)}
            if k == "dtime":
                kn[k]["within_10pct"] = float(np.mean(np.abs(2 ** (pred[k][so] - Y[k][so]) - 1) <= 0.10))
                kn[k]["within_10pct_prior"] = float(np.mean(np.abs(2 ** (prior[k][so] - Y[k][so]) - 1) <= 0.10))
        r["knobs"] = kn
        out[eff] = r
    return out


def passes(r):
    """A parameter passes on an arm: on/off if the strong third's AUC interval sits above 0.5; a knob if its error less
    the draw-aware prior's sits below 0 on the strong third."""
    out = {}
    for eff, d in r.items():
        lo = d["strong_third"]["auc_ci"][0]
        out[f"{eff} on/off"] = lo is not None and lo > 0.5
        for k, v in d["knobs"].items():
            hi = v["diff_ci"][1]
            out[k] = hi is not None and hi < 0
    return out


def rule(target_pass, stem_pass):
    """Per parameter: "R1" (both pass: declare render-and-compare with renders), "R3" (the target passes, the stem
    doesn't: the stem is the bottleneck, to the user), "R4" (the target fails: stays on song research)."""
    return {p: ("R1" if target_pass[p] and stem_pass[p] else "R3" if target_pass[p] else "R4") for p in target_pass}


# --- the commands -------------------------------------------------------------------------------------------------------

def items():
    import glob

    meta = json.loads(open(os.path.join(root(), "e1a", "meta.json")).read())["examples"]
    wide = [m for m in meta if m["mode"] == "wide"]
    ids = {m["i"] for m in wide}
    rows = {}
    cc = os.path.expanduser("~/ndsp-presets/learn/trusted-data/cc")
    for f in sorted(glob.glob(os.path.join(cc, "rows", "render-*.jsonl"))):
        for line in open(f):
            r = json.loads(line)
            if r["i"] in ids:
                rows[r["i"]] = r
    return [{**m, "settings": rows[m["i"]]["settings"]} for m in wide], cc


def cmd_features(_args):
    import numpy as np
    import soundfile as sf

    from learn import pipeline_fix as P

    P.require(PHASE)
    d = out_dir()
    if (d / "features.npz").exists():
        raise SystemExit("t0/features.npz exists")
    its, cc = items()
    X = {a: [] for a in ARMS}
    t0 = time.time()
    for n, it in enumerate(its):
        i = it["i"]
        y, sr = sf.read(os.path.join(cc, "audio", f"{i:07d}"[:4], f"{i:07d}-target.flac"))
        if sr != SR:
            raise SystemExit(f"{i}: target at {sr} Hz")
        z = np.load(os.path.join(root(), "e1e", "audio", f"{i:07d}.npz"))
        X["target"].append(features(y))
        X["stem"].append(features(z["stem"]))
        X["mix"].append(features(z["mix"]))
        if n % 100 == 0:
            print(f"t0 features {n + 1}/{len(its)}: {(time.time() - t0) / (n + 1):.2f} s each", flush=True)
    sep = os.path.expanduser("~/ndsp-presets/learn/trusted-data/judge-v5/separator-check/stems/xlance_g")
    dry = sorted(f for f in os.listdir(sep) if f.endswith("-S.npy"))
    Xd = [features(np.load(os.path.join(sep, f))) for f in dry]
    d.mkdir(parents=True, exist_ok=True)
    np.savez(d / "features.npz", **{a: np.array(X[a]) for a in ARMS}, dry=np.array(Xd),
             i=np.array([it["i"] for it in its]), songs=np.array([it["song"] for it in its]))
    P.save(d / "features-meta.json", {"phase": PHASE, "features": FEATURES, "dry_stems": dry, "n": len(its),
                                      "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"T0 FEATURES DONE: {len(its)} items x {len(ARMS)} arms, {len(dry)} dry stems", flush=True)


def cmd_read(_args):
    import numpy as np

    from learn import pipeline_fix as P

    P.require(PHASE)
    z = np.load(out_dir() / "features.npz")
    its, _ = items()
    if [it["i"] for it in its] != list(z["i"]):
        raise SystemExit("the items differ from the features'")
    L = [labels(it["settings"]) for it in its]
    Y = {c: np.array([l_[c] for l_ in L]) for c in L[0]}
    songs = z["songs"]
    lib = z["target"]                         # the library: other songs' clean targets with known settings
    rep = {"phase": PHASE, "n": len(its), "songs": {s: int((songs == s).sum()) for s in sorted(set(songs))}, "arms": {}}
    for a in ARMS:
        pred, prior = loso(lib, z[a], Y, songs)
        rep["arms"][a] = read_arm(pred, prior, Y, songs)
    rep["passes"] = {a: passes(rep["arms"][a]) for a in ARMS}
    rep["rule"] = rule(rep["passes"]["target"], rep["passes"]["stem"])
    # the negative control: E0's dry X-LANCE stems against every wide target
    nb = neighbours(lib, z["dry"])
    rep["negative_control"] = {eff: {"switched_on": int(sum(np.mean(Y[c][row]) > 0.5 for row in nb)), "of": len(nb)}
                               for eff, (c, _, _) in EFFECTS.items()}
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(out_dir() / "read.json", rep)
    print(json.dumps({"passes": rep["passes"], "rule": rep["rule"], "negative_control": rep["negative_control"]}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("t0-features").set_defaults(fn=cmd_features)
    sub.add_parser("t0-read").set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
