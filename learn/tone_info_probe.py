"""Where the tone information is lost: one linear probe per head on F5's examples, from the target render, the mix,
the X-LANCE stem, the target with its DI, a richer target representation and the DI alone (`docs/tone-info-probe.md`;
ledger `trusted-data-t3`, amendment 2). Descriptive: zero renders, zero separations. Probe-trained on F5's training
examples, read on FS5 with R0's rule (`trusted_data_t3_r.r0_rows`). Outputs go to `tone-probe/` only; `t0/`, `t2/`
and `t3/` are read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -m learn.tone_info_probe features     # the summaries (4 processes), cached in tone-probe/features.npz
    $MAIN -m learn.tone_info_probe read         # the probes and the table, tone-probe/probe.json
    $MAIN -m learn.tone_info_probe audible      # the audibility addition, tone-probe/audible.json
    $MAIN -m learn.tone_info_probe posthoc      # the review's post-hoc inputs, tone-probe/posthoc.json
    $MAIN -m learn.tone_info_probe mixstem      # (f) mix + stem against (b), (c) and the conditioning, mixstem.json
    $MAIN -m learn.tone_info_probe mask-features  # the mix summarised on its dominant cells, mask-features.npz
    $MAIN -m learn.tone_info_probe mask           # those summaries against (b) and their placebos, mask.json
"""

from __future__ import annotations

import argparse
import math
import time

import numpy as np

OUT_NAME = "tone-probe"
DESIGN = "docs/tone-info-probe.md"
STATUS = "descriptive, zero renders and zero separations; decides nothing"
INPUTS = {"a": "target", "b": "mix", "c": "stem", "d": "target + DI", "e": "target, richer", "n": "DI alone"}
LAGS = (1, 2, 3, 4, 6, 8, 11, 16, 22, 30, 40, 55, 75, 100, 135, 180)   # frames at the mels' 10 ms hop
GROUPS = 8
ALPHAS = tuple(10.0 ** k for k in range(-1, 8))
FOLDS = 5
RICH = {"n_fft": 4096, "hop": 240, "bands": 160, "fmin": 30.0, "fmax": 24000.0}
STEPS = {"mix": ("a", "b"), "separator": ("b", "c"), "DI": ("d", "a"), "representation": ("e", "a")}
WORKERS = 4
LISTS = {}
MAPS = {"o": "true map", "g": "stem map, 3 dB", "t": "stem map, top tenth"}
MASK = {"b": INPUTS["b"], **MAPS, **{f"p{k}": f"another example's {v}" for k, v in MAPS.items()},
        "xo": "true map over another example's mix"}
MAP_DB = 3.0
MAP_TOP = 0.10
MIN_CELLS = 20
MIN_PAIRS = 20
CHANCE_HEADS = 6                     # heads reliably better by chance at 90% two-sided, of 116
MAP_SEED = 20261105
MASK_STATUS = "descriptive, zero renders and zero separations; its reading stops mask pooling or earns one declared step"
TODAY = "today"


# --- pure: the summaries ------------------------------------------------------------------------------------------

def autocorr(e, lags):
    """Normalised autocorrelation of an envelope at the given frame lags (0 where the lag does not fit)."""
    x = np.asarray(e, np.float64) - float(np.mean(e))
    v = float((x * x).mean())
    if v <= 0:
        return np.zeros(len(lags))
    return np.array([float((x[:-k] * x[k:]).mean()) / v if k < len(x) else 0.0 for k in lags])


def summary(db, lags=LAGS, groups=GROUPS):
    """One half's summary of a [bands, frames] dB array: per band mean, sd, p10/p50/p90 and mean |frame change|;
    per band group the power envelope's autocorrelation at `lags` and the p5/p25/p75/p95 of its frame change; the
    broadband envelope's mean, sd, p10 and p90."""
    db = np.asarray(db, np.float64)
    f = [db.mean(1), db.std(1), *np.percentile(db, [10, 50, 90], axis=1), np.abs(np.diff(db, axis=1)).mean(1)]
    p = 10.0 ** (db / 10.0)
    for g in np.array_split(np.arange(db.shape[0]), groups):
        e = 10.0 * np.log10(p[g].mean(0) + 1e-30)
        f += [autocorr(e, lags), np.percentile(np.diff(e), [5, 25, 75, 95])]
    e = 10.0 * np.log10(p.mean(0) + 1e-30)
    f.append(np.array([e.mean(), e.std(), *np.percentile(e, [10, 90])]))
    return np.concatenate([np.ravel(x) for x in f])


def mel_summary(halves):
    """The averaged summary of a stored example's two uint8 half mels ({"A", "B"}), half A's first second masked
    (dropped) as in training."""
    from learn import pretrain_set as PS

    s = [summary(PS.dequant(halves["A"])[:, PS.MASK_A_FRAMES:]), summary(PS.dequant(halves["B"]))]
    return (s[0] + s[1]) / 2


def rich_bands(n_fft=RICH["n_fft"], sr=48000, bands=RICH["bands"], fmin=RICH["fmin"], fmax=RICH["fmax"]):
    """For each log-spaced band, the STFT bins it pools (the nearest bin when none falls inside)."""
    f = np.arange(n_fft // 2 + 1) * sr / n_fft
    edges = np.geomspace(fmin, fmax, bands + 1)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        ix = np.where((f >= lo) & (f < hi))[0]
        out.append(ix if len(ix) else np.array([int(np.argmin(np.abs(f - math.sqrt(lo * hi))))]))
    return out


def rich_summary(y, sr=48000):
    """(e): the target audio's halves (1–5.5 s with its first second dropped, 5.5–10 s) as unquantised dB in 160
    log bands (4,096-point STFT, 5 ms hop), summarised as the mels, lags at the same times."""
    from scipy.signal import stft

    from learn import pretrain_set as PS

    hop, n_fft = RICH["hop"], RICH["n_fft"]
    bands = rich_bands(n_fft, sr)
    lags = tuple(int(round(k * 480 / hop)) for k in LAGS)
    out = []
    for h, sl in PS.half_slices(sr).items():
        x = np.asarray(y[sl], np.float64)
        if h == "A":
            x = x[int(PS.MASK_A_S * sr):]
        _, _, Z = stft(x, fs=sr, nperseg=n_fft, noverlap=n_fft - hop, boundary=None, padded=False)
        p = np.abs(Z) ** 2
        db = 10.0 * np.log10(np.stack([p[ix].mean(0) for ix in bands]) + 1e-16)
        out.append(summary(db, lags))
    return (out[0] + out[1]) / 2


# --- pure: the mix on its dominant cells ------------------------------------------------------------------------------

def map_true(mix, target, gain_db, db=MAP_DB):
    """The cells where the target, at its gain in the mix, is within `db` of the mix."""
    return np.asarray(target, np.float64) + gain_db >= np.asarray(mix, np.float64) - db


def map_stem(mix, stem, db=MAP_DB):
    """The cells where the stem is within `db` of the mix."""
    return np.asarray(stem, np.float64) >= np.asarray(mix, np.float64) - db


def map_top(mix, stem, share=MAP_TOP, seed=MAP_SEED):
    """The `share` of cells where the stem sits highest against the mix. Stem minus mix ties on the half-dB grid, so
    ties go to the louder mix cell, then to a seeded draw."""
    m = np.asarray(mix, np.float64).ravel()
    gap = np.asarray(stem, np.float64).ravel() - m
    keep = np.zeros(gap.size, bool)
    order = np.lexsort((np.random.default_rng(seed).random(gap.size), -m, -gap))
    keep[order[:max(1, int(round(share * gap.size)))]] = True
    return keep.reshape(np.shape(mix))


def true_gain_db(ga, mastered, lufs_mix, lufs_target, lufs_backing, gb):
    """The target's gain in one half of a mix: `ga`, and on a mastered mix what the mastering added, from the stored
    loudness of the mix against the target and backing's power sum at their gains."""
    from learn import pretrain_set as PS

    return lufs_mix - PS.db_sum(lufs_target, lufs_backing + gb) if mastered else ga


def autocorr_on(x, have, lags, min_pairs=MIN_PAIRS):
    """`autocorr` of an envelope held only on the frames `have`: mean and variance over those frames, each lag over
    the pairs held, NaN where there are under `min_pairs` (0 for a flat envelope, as `autocorr`)."""
    x, have = np.asarray(x, np.float64), np.asarray(have, bool)
    if not have.any():
        return np.full(len(lags), np.nan)
    c = x - float(x[have].mean())
    v = float((c[have] ** 2).mean())
    if v <= 0:
        return np.zeros(len(lags))
    out = []
    for k in lags:
        m = have[:-k] & have[k:] if k < len(x) else np.zeros(0, bool)
        out.append(float((c[:-k][m] * c[k:][m]).mean()) / v if m.sum() >= min_pairs else np.nan)
    return np.array(out)


def masked_summary(db, keep, lags=LAGS, groups=GROUPS, min_cells=MIN_CELLS):
    """`summary` from the cells `keep` marks: frame changes and lags over pairs of kept frames, NaN where a band holds
    under `min_cells` cells or a group or the broadband envelope under `min_cells` frames. With every cell kept it is
    `summary`. An envelope averages the bands kept in each frame, so which cells are kept moves it."""
    db, keep = np.asarray(db, np.float64), np.asarray(keep, bool)
    bands, frames = db.shape
    per_band = np.full((6, bands), np.nan)
    for j in range(bands):
        v = db[j, keep[j]]
        if len(v) < min_cells:
            continue
        per_band[:5, j] = [v.mean(), v.std(), *np.percentile(v, [10, 50, 90])]
        pair = keep[j, :-1] & keep[j, 1:]
        if pair.any():
            per_band[5, j] = np.abs(np.diff(db[j]))[pair].mean()
    f = list(per_band)
    p = 10.0 ** (db / 10.0)

    def envelope(g):
        n = keep[g].sum(0)
        have = n > 0
        e = np.zeros(frames)
        e[have] = 10.0 * np.log10((p[g] * keep[g]).sum(0)[have] / n[have] + 1e-30)
        return e, have

    for g in np.array_split(np.arange(bands), groups):
        e, have = envelope(g)
        pair = have[:-1] & have[1:]
        if have.sum() < min_cells or not pair.any():
            f += [np.full(len(lags), np.nan), np.full(4, np.nan)]
        else:
            f += [autocorr_on(e, have, lags), np.percentile(np.diff(e)[pair], [5, 25, 75, 95])]
    e, have = envelope(np.arange(bands))
    f.append(np.full(4, np.nan) if have.sum() < min_cells
             else np.array([e[have].mean(), e[have].std(), *np.percentile(e[have], [10, 90])]))
    return np.concatenate([np.ravel(x) for x in f])


def mean_halves(a, b):
    """Two halves' summaries averaged: one half's value where the other has none, NaN where neither has."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    return np.where(np.isnan(a), b, np.where(np.isnan(b), a, (a + b) / 2))


def fill_means(X):
    """Each column's mean over its held values (0 for a column with none), from the probe-training rows."""
    X = np.asarray(X, np.float64)
    n = (~np.isnan(X)).sum(0)
    return np.nansum(X, 0) / np.maximum(n, 1)


def partners(ids, sections, seed=MAP_SEED):
    """{id: a seeded partner from another section}, whose maps stand in as the placebo's."""
    ids, sections = list(ids), list(sections)
    order = np.random.default_rng(seed).permutation(len(ids)).tolist()
    out = {}
    for n, i in enumerate(ids):
        at = order.index(n)
        for k in range(1, len(ids)):
            m = order[(at + k) % len(ids)]
            if sections[m] != sections[n]:
                out[i] = ids[m]
                break
    return out


def sign_p(better, worse):
    """One-sided sign test among the heads with a reliable step: P(at least `better` of them go better) at one half."""
    n = better + worse
    return sum(math.comb(n, k) for k in range(better, n + 1)) / 2 ** n if n else 1.0


def is_ahead(c, chance=CHANCE_HEADS):
    """The declared "ahead": more heads reliably better than worse by the sign test at 5%, and more than chance gives."""
    return c["better"] > chance and c["sign_p"] < 0.05


def reading(pairs):
    """The declared map, first match wins, on `pair_counts` rows. -> (branch, the stem map that earned it or None)."""
    ahead = {k: is_ahead(c) for k, c in pairs.items()}
    earned = [k for k in ("g", "t") if ahead[f"{k}-b"] and ahead[f"{k}-p{k}"]]
    if earned:
        return "stem map earns a step", earned[0]
    if ahead["o-b"] and ahead["o-po"] and ahead["o-xo"]:
        return "better map next", None
    if ahead["o-po"] and ahead["o-xo"]:
        return "denser read next", None
    if ahead["o-b"] or ahead["g-b"] or ahead["t-b"]:
        return "not credited to the map, stop", None
    return "no gain shown, stop", None


# --- pure: the ridge probe ----------------------------------------------------------------------------------------

def group_folds(groups, k=FOLDS):
    """k section-grouped folds (sections sorted, dealt round-robin by size): -> [test index arrays]."""
    g = np.asarray(groups)
    secs, counts = np.unique(g, return_counts=True)
    order = secs[np.argsort(-counts, kind="stable")]
    load, fold_of = [0] * k, {}
    for s, c in zip(order, counts[np.argsort(-counts, kind="stable")]):
        j = int(np.argmin(load))
        fold_of[s] = j
        load[j] += int(c)
    f = np.array([fold_of[s] for s in g])
    return [np.where(f == j)[0] for j in range(k) if (f == j).any()]


class Ridge:
    """Ridge with an unpenalised intercept for several penalties at once (one eigendecomposition)."""

    def __init__(self, X, Y):
        self.mx, self.my = X.mean(0), Y.mean(0)
        Xc = X - self.mx
        lam, self.V = np.linalg.eigh(Xc.T @ Xc)
        self.lam = np.clip(lam, 0, None)
        self.b = self.V.T @ (Xc.T @ (Y - self.my))

    def predict(self, X, alpha):
        w = self.V @ (self.b / (self.lam + alpha)[:, None])
        return (X - self.mx) @ w + self.my


def auc(y, q):
    from learn import trusted_data_t3_r as R

    return R.auc(y, q)


def cv_pick(X, Y, groups, score, alphas=ALPHAS):
    """The penalty with the best mean section-grouped CV score (higher is better); ties go to the larger penalty.
    score(Y_true, Y_pred) -> float or None (a fold it cannot score)."""
    folds = group_folds(groups)
    tot = np.zeros(len(alphas))
    cnt = np.zeros(len(alphas))
    for te in folds:
        tr = np.setdiff1d(np.arange(len(X)), te)
        r = Ridge(X[tr], Y[tr])
        for a, al in enumerate(alphas):
            s = score(Y[te], r.predict(X[te], al))
            if s is not None:
                tot[a] += s
                cnt[a] += 1
    mean = np.where(cnt > 0, tot / np.maximum(cnt, 1), -np.inf)
    best = max(range(len(alphas)), key=lambda a: (mean[a], a))
    return alphas[best], [None if not math.isfinite(m) else float(m) for m in mean]


def fit_probe(Xtr, Xte, lab_tr, lab_te, const_tr, const_te, sec_tr, cond_tr, cond_te, amp_tr):
    """Every head's probe for one input. Xtr/Xte: summaries (standardised on Xtr here); lab_*: encoded labels
    (c, cm, s, sm, k, km) stacked; const_*: the constant's continuous answer per example ([n, CONT]); cond_*: the amp
    and class one-hot (not for the amp head); amp_tr: amp indices. -> (per-FS5-example readout arrays, penalties)."""
    from learn import full_space as F

    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd[sd < 1e-9] = 1.0
    A_tr, A_te = (Xtr - mu) / sd, (Xte - mu) / sd
    Z_tr, Z_te = np.hstack([A_tr, cond_tr]), np.hstack([A_te, cond_te])
    c, cm, s, sm, k, km = lab_tr[:6]
    nte = len(Xte)
    a2 = np.full((nte, len(F.CONT)), np.nan)
    sw_p = np.full((nte, len(F.SW)), 0.5)
    mic_p = [np.zeros((nte, len(F.MICS))) for _ in F.CAT]
    pen = {}

    for j, name in enumerate(F.CONT):
        m = (cm[:, j] > 0) & np.isfinite(const_tr[:, j])
        if m.sum() < 10:
            continue
        y, b = c[m, j], const_tr[m, j]
        X, Y, g = Z_tr[m], (y - b)[:, None], sec_tr[m]          # the residual from the constant
        al, _ = _pick_resid(X, Y, g, b, y)
        r = Ridge(X, Y)
        a2[:, j] = np.clip(const_te[:, j] + r.predict(Z_te, al)[:, 0], 0, 1)
        pen[name] = al

    for j, name in enumerate(F.SW):
        m = sm[:, j] > 0
        y = (s[m, j] > 0.5).astype(np.float64)
        if m.sum() < 10 or y.min() == y.max():
            continue
        X, Y, g = Z_tr[m], y[:, None], sec_tr[m]
        al, _ = cv_pick(X, Y, g, lambda Yt, Yp: auc(Yt[:, 0] > 0.5, Yp[:, 0]))
        sw_p[:, j] = Ridge(X, Y).predict(Z_te, al)[:, 0]
        pen[name] = al

    for j, name in enumerate(F.CAT):
        m = km[:, j] > 0
        if m.sum() < 10:
            continue
        Y = np.eye(len(F.MICS))[k[m, j].astype(int)]
        X, g = Z_tr[m], sec_tr[m]
        al, _ = cv_pick(X, Y, g, lambda Yt, Yp: float((Yt.argmax(1) == Yp.argmax(1)).mean()))
        mic_p[j] = Ridge(X, Y).predict(Z_te, al)
        pen[name] = al

    Y = np.eye(len(F.AMPS))[amp_tr]
    al, _ = cv_pick(A_tr, Y, sec_tr, lambda Yt, Yp: float((Yt.argmax(1) == Yp.argmax(1)).mean()))
    amp_p = Ridge(A_tr, Y).predict(A_te, al)
    pen["amp choice"] = al
    return {"a2": a2, "sw_p": sw_p, "mic_p": mic_p, "amp_p": amp_p}, pen


def _pick_resid(X, Y, g, base, y):
    """cv_pick for a knob: the residual's ridge scored by the clipped answer's negative mean absolute error."""
    folds = group_folds(g)
    tot = np.zeros(len(ALPHAS))
    for te in folds:
        tr = np.setdiff1d(np.arange(len(X)), te)
        r = Ridge(X[tr], Y[tr])
        for a, al in enumerate(ALPHAS):
            ans = np.clip(base[te] + r.predict(X[te], al)[:, 0], 0, 1)
            tot[a] -= float(np.abs(ans - y[te]).mean())
    best = max(range(len(ALPHAS)), key=lambda a: (tot[a], a))
    return ALPHAS[best], (tot / len(folds)).tolist()


# --- pure: the paired steps and the attribution -------------------------------------------------------------------

def paired_jackknife_auc(y, qp, qq, groups):
    """AUC(p) − AUC(q) on the same examples, with the delete-one-section jackknife's 90% t interval."""
    from learn import pretrain_set as PS

    y, qp, qq, g = np.asarray(y, bool), np.asarray(qp, float), np.asarray(qq, float), np.asarray(groups)
    ap, aq = auc(y, qp), auc(y, qq)
    secs = sorted(set(g.tolist()))
    out = {"point": None if ap is None or aq is None else ap - aq, "lo": None, "hi": None, "sections": len(secs)}
    if out["point"] is None or len(secs) < 2:
        return out
    th = []
    for s_ in secs:
        k = g != s_
        a, b = auc(y[k], qp[k]), auc(y[k], qq[k])
        if a is None or b is None:
            return out
        th.append(a - b)
    th = np.asarray(th)
    n = len(th)
    h = PS.t90(n - 1) * math.sqrt((n - 1) / n * float(((th - th.mean()) ** 2).sum()))
    out.update(lo=out["point"] - h, hi=out["point"] + h)
    return out


def step_row(kind, P, Q, ids, j, lab, sec, const, majority_amp=None):
    """P better than Q for one head, paired on FS5: knobs by the |error| difference (negative: P better), switches
    by the AUC difference, accuracies by the correct-answer difference; 90% section-clustered (jackknife for AUC).
    -> {point, lo, hi, sections, reliable} with `reliable` meaning P reliably better than Q."""
    from learn import trusted_data_t3_r as R

    if kind == "continuous":
        d = {}
        for n, i in enumerate(ids):
            y, c0 = lab[0][n, j], const[n, j]
            if lab[1][n, j] > 0 and math.isfinite(c0):
                d[i] = abs(P["a2"][n, j] - y) - abs(Q["a2"][n, j] - y)
        st = R.section_t(d, sec)
        st["reliable"] = st["hi"] is not None and st["hi"] < 0
        return st
    if kind == "switch":
        m = lab[3][:, j] > 0
        st = paired_jackknife_auc(lab[2][m, j] > 0.5, P["sw_p"][m, j], Q["sw_p"][m, j], [sec[i] for i, ok in zip(ids, m) if ok])
    elif kind == "mic":
        d = {}
        for n, i in enumerate(ids):
            if lab[5][n, j] > 0:
                t = int(lab[4][n, j])
                d[i] = float(int(np.argmax(P["mic_p"][j][n])) == t) - float(int(np.argmax(Q["mic_p"][j][n])) == t)
        st = R.section_t(d, sec)
    else:
        amps = lab[6]
        d = {i: float(int(np.argmax(P["amp_p"][n])) == amps[n]) - float(int(np.argmax(Q["amp_p"][n])) == amps[n])
             for n, i in enumerate(ids)}
        st = R.section_t(d, sec)
    st["reliable"] = st["lo"] is not None and st["lo"] > 0
    return st


def attribute(readable, steps):
    """The declared order. readable: {input: bool} for one head; steps: {step: reliable bool}. -> category."""
    if readable["c"]:
        return "survives"
    if not readable["a"]:
        if readable.get("e"):
            return "richer features"
        if readable.get("d"):
            return "needs the DI"
        return "not carried"
    mix, sep = steps["mix"], steps["separator"]
    if mix and sep:
        return "both"
    if mix:
        return "mix"
    if sep:
        return "separator"
    return "unresolved"


def family_table(rows):
    """{family: {heads, readable, median AUC gain (switches), median E gain (knobs, constant's E minus the probe's),
    median accuracy gain}} from R0-shaped rows."""
    from learn import trusted_data_t3_r as R

    out = {}
    for r in rows:
        f = out.setdefault(r["family"], {"heads": 0, "readable": 0, "sw": [], "knob": [], "acc": []})
        f["heads"] += 1
        f["readable"] += bool(r["readable"])
        if r["point"] is not None:
            if r["kind"] == "switch":
                f["sw"].append(r["point"] - 0.5)
            elif r["kind"] == "continuous":
                f["knob"].append(-r["point"])
            else:
                f["acc"].append(r["point"])
    order = [f for f in R.FAMILY_ORDER if f in out] + sorted(set(out) - set(R.FAMILY_ORDER))
    med = lambda v: float(np.median(v)) if v else None  # noqa: E731
    return {f: {"heads": out[f]["heads"], "readable": out[f]["readable"], "auc_gain": med(out[f]["sw"]),
                "e_gain": med(out[f]["knob"]), "acc_gain": med(out[f]["acc"])} for f in order}


# --- the stored data ----------------------------------------------------------------------------------------------

def out_dir(root):
    return root / OUT_NAME


def _example_feats(job):
    """One example's (a, b, c, e) summaries from its stored files."""
    from learn import direct_sound_gate as G
    from learn import trusted_data as T

    root, i, scale, sha = job
    d = {}
    for key, kind, p in (("a", "tgt-t3", "g"), ("b", "mix-t3", "m"), ("c", "xlance_g-t3", "s")):
        z = np.load(T.ex_path(root, "t3", i, kind))
        d[key] = mel_summary({"A": z[f"{p}A"], "B": z[f"{p}B"]})
    y = G.read_flac(T.flac_path(root, "t3", i, "target"), scale, sha)
    d["e"] = rich_summary(y)
    return i, d


def _di_feats(job):
    """One section's DI summary: the DI as rendered (`song_bank.measure` of the section), trimmed as the target."""
    from learn import pretrain_set as PS
    from learn import song_bank as B

    sid, path, start = job
    di = B.measure(PS.section_audio(path, start)).astype(np.float32)
    di = di[int(PS.TRIM_S * PS.SR):int((PS.TRIM_S + PS.SEC_S) * PS.SR)]
    return sid, mel_summary(PS.halves_mel(di))


def load_sets():
    """(root, train rows, FS5 rows, render rows) of D_F5, as R0 read them."""
    from learn import direct_stems as DS
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3
    from learn import verify_tracks as V

    root = V.OUT
    plan = V._load(T.plan_path(root, T3.STAGE))
    if not plan or plan.get("smoke"):
        raise SystemExit("T3's plan is missing")
    # T3's stored sets are read as planned. T0's lists may have moved on since (the ear's later sittings); they do not
    # change F5's stored examples, so the hash check is recorded, not enforced (`lists_check`).
    try:
        T.check_lists(root, plan, False)
        LISTS["check"] = "T0's lists match T3's plan"
    except SystemExit as e:
        LISTS["check"] = f"not enforced: {e}"
    ctx = DS.Ctx(quiet=True)
    tr, fs = T3.arm_rows(root, ctx, plan, T3.FULL)
    if set(r["section"] for r in tr) & set(r["section"] for r in fs):
        raise SystemExit("the probe-training and FS5 sections overlap")
    return root, ctx, tr, fs, T.rows_of(root, "t3", "render")


def cmd_features(args):
    from multiprocessing import Pool

    from learn import verify_tracks as V

    root, ctx, tr, fs, rend = load_sets()
    od = out_dir(root)
    od.mkdir(parents=True, exist_ok=True)
    rows = tr + fs
    jobs = [(root, r["i"], rend[r["i"]]["target"]["scale"], rend[r["i"]]["target"]["sha256"]) for r in rows]
    secs = sorted({r["section"] for r in rows})
    dijobs = [(s, ctx.sections[s]["path"], ctx.sections[s]["start_s"]) for s in secs]
    t0 = time.time()
    with Pool(WORKERS) as pool:
        di = dict(pool.map(_di_feats, dijobs))
        print(f"{len(di)} DI sections in {time.time() - t0:.0f} s", flush=True)
        feats = {}
        for n, (i, d) in enumerate(pool.imap_unordered(_example_feats, jobs, chunksize=16)):
            feats[i] = d
            if (n + 1) % 500 == 0:
                print(f"{n + 1}/{len(jobs)} examples, {time.time() - t0:.0f} s", flush=True)
    ids = [r["i"] for r in rows]
    np.savez(od / "features.npz", ids=np.array(ids), sections=np.array(secs),
             di=np.stack([di[s] for s in secs]), **{k: np.stack([feats[i][k] for i in ids]) for k in "abce"})
    V._save(od / "features.json", {"design": DESIGN, "status": STATUS, "examples": len(ids), "train": len(tr),
                                   "fs5": len(fs), "sections": len(secs), "minutes": round((time.time() - t0) / 60, 1),
                                   "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"FEATURES DONE: {len(ids)} examples, {len(secs)} DI sections, {time.time() - t0:.0f} s")


def prepare(root, tr, fs):
    """Everything the probes read: features, encoded labels, the constant, conditioning and the FS5 bookkeeping."""
    from learn import direct_sound_gate as G
    from learn import full_space as F
    from learn import song_model as SM
    from learn import trusted_data_t3 as T3
    from learn import trusted_data_t3_r as R

    od = out_dir(root)
    z = np.load(od / "features.npz")
    pos = {int(i): n for n, i in enumerate(z["ids"])}
    sec_ix = {s: n for n, s in enumerate(z["sections"].tolist())}
    fit = R.load_fit(root)
    f = fit["models"][T3.FULL]
    if [r["i"] for r in fs] != fit["fs5_ids"]:
        raise SystemExit("FS5 differs from the set fit.json read")
    const = G.const_from_json(f["constant_answers"])
    enc = T3.encode_for(T3.FULL)

    def labels(rows):
        L = [enc(r["label"])[:6] for r in rows]
        out = [np.stack([np.asarray(t[q], np.float64) for t in L]) for q in range(6)]
        out.append(np.array([F.AMPS.index(r["amp"]) for r in rows]))
        return out

    def cond(rows):
        return np.stack([SM.cond_vec(r["amp"], r["base"], [0.0, 0.0])[:len(SM.AMPS) + len(SM.CLASSES)] for r in rows])

    def X_of(key, rows):
        ix = [pos[r["i"]] for r in rows]
        di = z["di"][[sec_ix[r["section"]] for r in rows]]
        if key == "d":
            return np.hstack([z["a"][ix], di])
        if key == "n":
            return di
        return z[key][ix]

    lab_tr, lab_te = labels(tr), labels(fs)
    const_tr = np.stack([np.asarray(const[(r["amp"], r["base"])]["cont"], np.float64) for r in tr])
    const_te = np.stack([np.asarray(const[(r["amp"], r["base"])]["cont"], np.float64) for r in fs])
    sec_tr = np.array([r["section"] for r in tr])
    rates, majority = R.train_priors([enc(r["label"])[:6] for r in tr], [r["amp"] for r in tr])
    info = {r["i"]: {"section": r["section"], "cell": (r["amp"], r["base"]), "amp": r["amp"]} for r in fs}
    sec = {r["i"]: r["section"] for r in fs}
    ids = [r["i"] for r in fs]
    return {"X_of": X_of, "cond": cond, "lab_tr": lab_tr, "lab_te": lab_te, "const": const, "const_tr": const_tr,
            "const_te": const_te, "sec_tr": sec_tr, "rates": rates, "majority": majority, "info": info, "sec": sec,
            "ids": ids, "enc": enc}


def fit_input(S, key, tr, fs):
    """One input's probes (`fit_probe`) on the prepared set S. -> (predictions, penalties)."""
    return fit_probe(S["X_of"](key, tr), S["X_of"](key, fs), S["lab_tr"], S["lab_te"], S["const_tr"], S["const_te"],
                     S["sec_tr"], S["cond"](tr), S["cond"](fs), S["lab_tr"][6])


def cmd_read(args):
    from learn import full_space as F
    from learn import trusted_data_t3_r as R
    from learn import verify_tracks as V

    root, _, tr, fs, _ = load_sets()
    od = out_dir(root)
    if (od / "probe.json").exists() and not args.force:
        raise SystemExit(f"{od / 'probe.json'} exists: the probe is read once (--force to rewrite)")
    S = prepare(root, tr, fs)
    lab_te, const, rates, majority, info, sec, ids, const_te, sec_tr = (S[k] for k in (
        "lab_te", "const", "rates", "majority", "info", "sec", "ids", "const_te", "sec_tr"))
    preds, rows_by, pens = {}, {}, {}
    t0 = time.time()
    for key in INPUTS:
        P, pen = fit_input(S, key, tr, fs)
        preds[key], pens[key] = P, pen
        ex = {i: {"a2": P["a2"][n], "sw_p": P["sw_p"][n], "mic_p": [m[n] for m in P["mic_p"]],
                  "amp_p": P["amp_p"][n], "c": lab_te[0][n], "cm": lab_te[1][n], "s": lab_te[2][n],
                  "sm": lab_te[3][n], "k": lab_te[4][n], "km": lab_te[5][n]} for n, i in enumerate(ids)}
        rows_by[key] = R.r0_rows(ex, info, const, rates, majority)
        nread = sum(r["readable"] for r in rows_by[key])
        print(f"({key}) {INPUTS[key]}: {nread} of {len(rows_by[key])} readable ({time.time() - t0:.0f} s)", flush=True)

    names = [r["name"] for r in rows_by["a"]]
    kinds = {r["name"]: r["kind"] for r in rows_by["a"]}
    jix = {**{n: j for j, n in enumerate(F.CONT)}, **{n: j for j, n in enumerate(F.SW)},
           **{n: j for j, n in enumerate(F.CAT)}}
    heads = []
    for h, name in enumerate(names):
        kind = kinds[name]
        k2 = {"continuous": "continuous", "switch": "switch"}.get(kind, "amp" if name == R.AMP_NAME else "mic")
        steps = {s: step_row(k2, preds[p], preds[q], ids, jix.get(name), lab_te, sec, const_te)
                 for s, (p, q) in STEPS.items()}
        rd = {k: bool(rows_by[k][h]["readable"]) for k in INPUTS}
        heads.append({"name": name, "family": rows_by["a"][h]["family"], "kind": kind, "readable": rd,
                      "points": {k: rows_by[k][h]["point"] for k in INPUTS},
                      "steps": steps, "where": attribute(rd, {s: v["reliable"] for s, v in steps.items()})})

    r0 = R.load_r0(root)
    fam = {k: family_table(rows_by[k]) for k in INPUTS}
    fam["D_F5"] = family_table(r0["rows"])
    where = {}
    for hd in heads:
        where.setdefault(hd["family"], {}).setdefault(hd["where"], 0)
        where[hd["family"]][hd["where"]] += 1
    verdict = {f: max(sorted(w.items()), key=lambda kv: kv[1])[0] for f, w in where.items()}
    total_where = {}
    for hd in heads:
        total_where[hd["where"]] = total_where.get(hd["where"], 0) + 1
    rec = {"design": DESIGN, "status": STATUS, "inputs": INPUTS, "train": len(tr), "fs5": len(fs),
           "fs5_sections": len(set(sec.values())), "lists_check": LISTS.get("check"), "train_sections": len(set(sec_tr.tolist())),
           "readable": {k: sum(r["readable"] for r in rows_by[k]) for k in INPUTS},
           "negative_control_flag": sum(r["readable"] for r in rows_by["n"]) > 12,
           "families": fam, "where_by_family": where, "verdict_by_family": verdict, "where_total": total_where,
           "heads": heads, "rows": rows_by, "penalties": pens,
           "minutes": round((time.time() - t0) / 60, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    V._save(od / "probe.json", rec)
    print_table(rec)
    print(f"READ DONE: {od / 'probe.json'}")


def print_table(rec):
    cols = list(INPUTS) + ["D_F5"]
    fam = rec["families"]
    fmt = lambda v, s=1: "  -  " if v is None else f"{v * s:+.3f}"  # noqa: E731
    print("\nreadable / heads, then median AUC − 0.5 (switches) | median E gain ×100 (knobs) | accuracy gain")
    print(f"{'family':14s} " + " ".join(f"{c:>26s}" for c in cols))
    for f in fam["a"]:
        cells = []
        for c in cols:
            x = fam[c].get(f)
            cells.append("-" if x is None else f"{x['readable']:>2d}/{x['heads']:<2d} {fmt(x['auc_gain'])} "
                         f"{fmt(x['e_gain'], 100)} {fmt(x['acc_gain'])}")
        print(f"{f:14s} " + " ".join(f"{s:>26s}" for s in cells))
    print("readable totals:", rec["readable"])
    print("\nwhere lost, by family:")
    for f, w in rec["where_by_family"].items():
        print(f"  {f:14s} verdict {rec['verdict_by_family'][f]:16s} {w}")
    print("total:", rec["where_total"])


AUDIBLE = {"reverb/reverbActive": "reverb/reverbMix", "delay/delayActive": "delay/delayMix",
           "tremolo/tremoloActive": "tremolo/tremoloDepth", "pr12Amp/springOn": "pr12Amp/pr12Reverb",
           "sw50rAmp/springOn": "sw50rAmp/sw50rReverb"}
QS = (0, 10, 25, 50, 75, 90, 100)


def subset_mask(on, proxy, which, cuts):
    """FS5 examples kept for one restricted read: every "off", and the "on" ones in `which` by the proxy's cuts
    (`cuts`: {"t1", "med", "t2"} from the probe-training "on" labels)."""
    on, proxy = np.asarray(on, bool), np.asarray(proxy, float)
    keep_on = {"all on": np.ones_like(on), "top third": proxy >= cuts["t2"], "top half": proxy >= cuts["med"],
               "bottom third": proxy <= cuts["t1"]}[which]
    return ~on | (on & keep_on)


def cmd_audible(args):
    """The audibility addition: each effect's proxy among "on" labels, and the switches' readability on FS5 with
    "off" against only the "on" examples above the declared cuts, for (a), (b) and (c)."""
    from learn import full_space as F
    from learn import trusted_data_t3_r as R
    from learn import verify_tracks as V

    root, _, tr, fs, _ = load_sets()
    od = out_dir(root)
    S = prepare(root, tr, fs)
    rows = tr + fs
    lab_all = [S["enc"](r["label"])[:6] for r in rows]
    dist, cuts = {}, {}
    for sw, px in AUDIBLE.items():
        js, jp = F.SW.index(sw), F.CONT.index(px)
        on = [(r, t) for r, t in zip(rows, lab_all) if t[3][js] > 0 and t[2][js] > 0.5]
        n_scored = sum(1 for t in lab_all if t[3][js] > 0)
        d = {}
        for mode in ("factory", "start", "wide", "all"):
            sel = [(r, t) for r, t in on if mode == "all" or r["mode"] == mode]
            if not sel:
                continue
            u = np.array([float(t[0][jp]) for _, t in sel])
            raw = np.array([float(r["label"]["settings"].get(px, "nan")) for r, _ in sel])
            d[mode] = {"n_on": len(sel), "unit": dict(zip(map(str, QS), np.percentile(u, QS).round(4).tolist())),
                       "plugin": dict(zip(map(str, QS), np.nanpercentile(raw, QS).round(4).tolist()))}
        allraw = np.array([float(r["label"]["settings"].get(px, "nan")) for r, _ in on])
        d["on_rate"] = len(on) / max(1, n_scored)
        if "spring" in sw.lower():
            d["share_at_spring_min"] = float(np.mean(allraw <= F.SPRING_MIN * 1.0001))
        dist[sw] = d
        u_tr = np.array([float(t[0][jp]) for t in lab_all[:len(tr)] if t[3][js] > 0 and t[2][js] > 0.5])
        cuts[sw] = {"t1": float(np.percentile(u_tr, 100 / 3)), "med": float(np.median(u_tr)),
                    "t2": float(np.percentile(u_tr, 200 / 3)), "n_train_on": len(u_tr)}
    lab_te, sec, ids = S["lab_te"], S["sec"], S["ids"]
    read = {}
    t0 = time.time()
    for key in "abc":
        P, _ = fit_input(S, key, tr, fs)
        for sw, px in AUDIBLE.items():
            js, jp = F.SW.index(sw), F.CONT.index(px)
            m = lab_te[3][:, js] > 0
            on = lab_te[2][m, js] > 0.5
            proxy = lab_te[0][m, jp]
            q = P["sw_p"][m, js]
            g = np.array([sec[i] for i, ok in zip(ids, m) if ok])
            for which in ("all on", "top third", "top half", "bottom third"):
                k = subset_mask(on, proxy, which, cuts[sw])
                st = R.jackknife_auc(on[k], q[k], g[k])
                ok, _ = R.readable("switch", st)
                read.setdefault(sw, {}).setdefault(which, {})[key] = {
                    **st, "readable": ok, "n_on": int((on & k).sum()), "n_off": int((~on & k).sum())}
        print(f"({key}) done ({time.time() - t0:.0f} s)", flush=True)
    sharp = {sw: {key: (read[sw]["top third"][key]["point"] is not None and read[sw]["all on"][key]["point"] is not None
                        and read[sw]["top third"][key]["point"] - read[sw]["all on"][key]["point"] >= 0.10)
                  for key in "abc"} for sw in AUDIBLE}
    rec = {"design": DESIGN + "#addition-are-on-effects-audible-declared-2026-10-27-before-it-is-computed",
           "status": STATUS, "lists_check": LISTS.get("check"), "proxies": AUDIBLE, "cuts": cuts,
           "distribution": dist, "read": read, "rises_sharply": sharp, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    V._save(od / "audible.json", rec)
    for sw in AUDIBLE:
        print(f"\n{sw} (proxy {AUDIBLE[sw]}), on-rate {dist[sw]['on_rate']:.2f}, cuts {cuts[sw]}")
        for mode, d in dist[sw].items():
            if isinstance(d, dict):
                print(f"  {mode:8s} n_on {d['n_on']:5d} unit {d['unit']} plugin {d['plugin']}")
        if "share_at_spring_min" in dist[sw]:
            print(f"  share at SPRING_MIN {dist[sw]['share_at_spring_min']:.3f}")
        for which, v in read[sw].items():
            cells = []
            for key in "abc":
                x = v[key]
                iv = "no interval" if x["lo"] is None else f"[{x['lo']:.3f},{x['hi']:.3f}]"
                pt = "n/a" if x["point"] is None else f"{x['point']:.3f}"
                cells.append(f"{key} {pt} {iv}{' R' if x['readable'] else ''} ({x['n_on']}/{x['n_off']})")
            print(f"  {which:12s} " + " | ".join(cells))
        print(f"  rises sharply: {sharp[sw]}")
    print(f"AUDIBLE DONE: {od / 'audible.json'}")


POSTHOC = {"a_norm": "target, level removed", "level": "target loudness alone", "cond": "conditioning alone"}
# the summary's level-carrying entries: per band mean, p10, p50, p90; the broadband envelope's mean, p10, p90
LEVEL_IX = tuple(range(0, 96)) + tuple(range(192, 480)) + (736, 738, 739)


def level_removed(A, lufs):
    """The target's summaries with its loudness (mean of the halves' LUFS) taken off every level-carrying entry, as
    the mix is loudness-normalised; the shape statistics (sd, frame change, autocorrelation, change percentiles)
    are level-free already."""
    An = np.array(A, np.float64, copy=True)
    An[:, list(LEVEL_IX)] -= np.asarray(lufs, np.float64)[:, None]
    return An


def cmd_posthoc(args):
    """The review's post-hoc inputs (declared in the doc as post hoc): the target with its level removed, the
    target's loudness alone, and the conditioning alone (amp and class, no audio), each read as the main inputs."""
    from learn import trusted_data_t3 as T3
    from learn import trusted_data_t3_r as R
    from learn import verify_tracks as V

    root, _, tr, fs, _ = load_sets()
    od = out_dir(root)
    S = prepare(root, tr, fs)
    z = np.load(od / "features.npz")
    ids = [int(i) for i in z["ids"]]
    pos = {i: n for n, i in enumerate(ids)}
    lufs = np.array([float(np.mean(np.load(T3.tgt_path(root, i))["lufs"])) for i in ids])
    An = level_removed(z["a"], lufs)
    base = S["X_of"]

    def X_of(key, rows):
        ix = [pos[r["i"]] for r in rows]
        if key == "a_norm":
            return An[ix]
        if key == "level":
            return lufs[ix][:, None]
        if key == "cond":
            return np.zeros((len(rows), 1))
        return base(key, rows)

    S["X_of"] = X_of
    lab_te, out = S["lab_te"], {}
    for key in POSTHOC:
        P, _ = fit_input(S, key, tr, fs)
        ex = {i: {"a2": P["a2"][n], "sw_p": P["sw_p"][n], "mic_p": [m[n] for m in P["mic_p"]],
                  "amp_p": P["amp_p"][n], "c": lab_te[0][n], "cm": lab_te[1][n], "s": lab_te[2][n],
                  "sm": lab_te[3][n], "k": lab_te[4][n], "km": lab_te[5][n]} for n, i in enumerate(S["ids"])}
        rows = R.r0_rows(ex, S["info"], S["const"], S["rates"], S["majority"])
        out[key] = {"readable": sum(r["readable"] for r in rows),
                    "knobs": sum(r["readable"] for r in rows if r["kind"] == "continuous"),
                    "switches": sum(r["readable"] for r in rows if r["kind"] == "switch"),
                    "families": family_table(rows), "rows": rows}
        print(f"({key}) {POSTHOC[key]}: {out[key]['readable']} readable (knobs {out[key]['knobs']}, switches "
              f"{out[key]['switches']}); " + ", ".join(f"{f} {v['readable']}/{v['heads']}"
                                                         for f, v in out[key]["families"].items()), flush=True)
    V._save(od / "posthoc.json", {"design": DESIGN, "status": STATUS + "; post hoc (from the review of PR #307)",
                                  "inputs": POSTHOC, "lists_check": LISTS.get("check"), **out,
                                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"POSTHOC DONE: {od / 'posthoc.json'}")


MIXSTEM = {"f": "mix + stem", "b": INPUTS["b"], "c": INPUTS["c"], "cond": "conditioning alone"}


def cmd_mixstem(args):
    """(f), post hoc: the mix's and the stem's summaries side by side, read as (a)-(c), beside (b), (c) and the
    conditioning alone; the heads (f) reads that (b) does not, and the paired step (f) - (b)."""
    from learn import full_space as F
    from learn import trusted_data_t3_r as R
    from learn import verify_tracks as V

    root, _, tr, fs, _ = load_sets()
    od = out_dir(root)
    S = prepare(root, tr, fs)
    base = S["X_of"]

    def X_of(key, rows):
        if key == "f":
            return np.hstack([base("b", rows), base("c", rows)])
        if key == "cond":
            return np.zeros((len(rows), 1))
        return base(key, rows)

    S["X_of"] = X_of
    lab_te, ids, sec, const_te = S["lab_te"], S["ids"], S["sec"], S["const_te"]
    preds, rows_by = {}, {}
    for key in MIXSTEM:
        P, _ = fit_input(S, key, tr, fs)
        preds[key] = P
        ex = {i: {"a2": P["a2"][n], "sw_p": P["sw_p"][n], "mic_p": [m[n] for m in P["mic_p"]],
                  "amp_p": P["amp_p"][n], "c": lab_te[0][n], "cm": lab_te[1][n], "s": lab_te[2][n],
                  "sm": lab_te[3][n], "k": lab_te[4][n], "km": lab_te[5][n]} for n, i in enumerate(ids)}
        rows_by[key] = R.r0_rows(ex, S["info"], S["const"], S["rates"], S["majority"])
        print(f"({key}) {MIXSTEM[key]}: {sum(r['readable'] for r in rows_by[key])} readable", flush=True)
    jix = {**{n: j for j, n in enumerate(F.CONT)}, **{n: j for j, n in enumerate(F.SW)},
           **{n: j for j, n in enumerate(F.CAT)}}
    heads = []
    for h, r in enumerate(rows_by["f"]):
        name, kind = r["name"], r["kind"]
        k2 = {"continuous": "continuous", "switch": "switch"}.get(kind, "amp" if name == R.AMP_NAME else "mic")
        fb = step_row(k2, preds["f"], preds["b"], ids, jix.get(name), lab_te, sec, const_te)
        bf = step_row(k2, preds["b"], preds["f"], ids, jix.get(name), lab_te, sec, const_te)
        heads.append({"name": name, "family": r["family"], "kind": kind,
                      "readable": {k: bool(rows_by[k][h]["readable"]) for k in MIXSTEM},
                      "points": {k: rows_by[k][h]["point"] for k in MIXSTEM},
                      "f_better_than_b": fb["reliable"], "b_better_than_f": bf["reliable"], "step_f_minus_b": fb})
    fam = {k: family_table(rows_by[k]) for k in MIXSTEM}
    rec = {"design": DESIGN + "#addition-mix-plus-stem-f-declared-2026-10-27-post-hoc-before-it-is-computed",
           "status": STATUS + "; post hoc", "inputs": MIXSTEM, "lists_check": LISTS.get("check"),
           "readable": {k: sum(r["readable"] for r in rows_by[k]) for k in MIXSTEM},
           "knobs": {k: sum(r["readable"] for r in rows_by[k] if r["kind"] == "continuous") for k in MIXSTEM},
           "switches": {k: sum(r["readable"] for r in rows_by[k] if r["kind"] == "switch") for k in MIXSTEM},
           "f_not_b": [h["name"] for h in heads if h["readable"]["f"] and not h["readable"]["b"]],
           "f_not_b_nor_c": [h["name"] for h in heads if h["readable"]["f"] and not (h["readable"]["b"] or h["readable"]["c"])],
           "b_not_f": [h["name"] for h in heads if h["readable"]["b"] and not h["readable"]["f"]],
           "step_f_better": sum(h["f_better_than_b"] for h in heads),
           "step_b_better": sum(h["b_better_than_f"] for h in heads),
           "families": fam, "heads": heads, "rows": rows_by, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    V._save(od / "mixstem.json", rec)
    print({k: rec[k] for k in ("readable", "knobs", "switches", "step_f_better", "step_b_better")})
    print("f not b:", rec["f_not_b"]); print("f not b nor c:", rec["f_not_b_nor_c"]); print("b not f:", rec["b_not_f"])
    for f in fam["f"]:
        print(f"  {f:14s} " + "  ".join(f"{k} {fam[k][f]['readable']}/{fam[k][f]['heads']}" for k in MIXSTEM))
    print(f"MIXSTEM DONE: {od / 'mixstem.json'}")


def example_maps(root, i, lufs_backing, gb):
    """One example's cut half mels and maps: {half: (mix dB, {map: keep})}, half A's first second dropped."""
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    m, s, g = (np.load(T.ex_path(root, "t3", i, k)) for k in ("mix-t3", "xlance_g-t3", "tgt-t3"))
    out = {}
    for n, h in enumerate("AB"):
        cut = PS.MASK_A_FRAMES if h == "A" else 0
        M, S, G = (PS.dequant(z[f"{p}{h}"])[:, cut:] for z, p in ((m, "m"), (s, "s"), (g, "g")))
        gain = true_gain_db(float(m["gain_db"]), bool(m["mastered"]), float(m["lufs"][n]), float(g["lufs"][n]),
                            lufs_backing, gb)
        out[h] = (M, {"o": map_true(M, G, gain), "g": map_stem(M, S), "t": map_top(M, S)})
    return out


def _mask_feats(job):
    """One example's summaries through its own maps and its partner's, its true map over the partner's mix, the
    every-cell control, and the maps' shares."""
    root, i, j, bi, bj = job
    own, other = example_maps(root, i, *bi), example_maps(root, j, *bj)
    d, q = {}, {}
    for k in MAPS:
        d[k] = mean_halves(*(masked_summary(own[h][0], own[h][1][k]) for h in "AB"))
        d[f"p{k}"] = mean_halves(*(masked_summary(own[h][0], other[h][1][k]) for h in "AB"))
        kept = sum(int(own[h][1][k].sum()) for h in "AB")
        hit = sum(int((own[h][1][k] & own[h][1]["o"]).sum()) for h in "AB")
        q[k] = (kept / sum(own[h][0].size for h in "AB"), hit / max(kept, 1),
                hit / max(sum(int(own[h][1]["o"].sum()) for h in "AB"), 1))
    d["xo"] = mean_halves(*(masked_summary(other[h][0], own[h][1]["o"]) for h in "AB"))
    d["all"] = mean_halves(*(masked_summary(own[h][0], np.ones_like(own[h][1]["o"])) for h in "AB"))
    return i, d, q


def cmd_mask_features(args):
    """The mix summarised through each map and its placebo. Stops if the every-cell summary is not the stored (b)."""
    from multiprocessing import Pool

    from learn import pipeline_fix as PF
    from learn import trusted_data as T
    from learn import verify_tracks as V

    PF.require("phase_mask_read")
    root, _, tr, fs, _ = load_sets()
    od = out_dir(root)
    z = np.load(od / "features.npz")
    pos = {int(i): n for n, i in enumerate(z["ids"])}
    stored = z["b"]
    built = T.rows_of(root, "t3", "build")
    level = {i: (float(r["lufs_backing"]), float(r["gains_db"]["gb"])) for i, r in built.items() if "gains_db" in r}
    jobs = []
    for rows in (tr, fs):
        pair = partners([r["i"] for r in rows], [r["section"] for r in rows])
        jobs += [(root, r["i"], pair[r["i"]], level[r["i"]], level[pair[r["i"]]]) for r in rows]
    t0 = time.time()
    feats, shares = {}, {}
    with Pool(WORKERS) as pool:
        for n, (i, d, q) in enumerate(pool.imap_unordered(_mask_feats, jobs, chunksize=16)):
            feats[i], shares[i] = d, q
            if (n + 1) % 500 == 0:
                print(f"{n + 1}/{len(jobs)} examples, {time.time() - t0:.0f} s", flush=True)
    ids = [j[1] for j in jobs]
    worst = max(float(np.abs(feats[i]["all"] - stored[pos[i]]).max()) for i in ids)
    if worst > 1e-5:
        raise SystemExit(f"the every-cell summary is {worst} from the stored (b)")
    np.savez(od / "mask-features.npz", ids=np.array(ids),
             **{k: np.stack([feats[i][k] for i in ids]) for k in MASK if k != "b"})
    fs_ids = [r["i"] for r in fs]
    med = lambda m, c: float(np.median([shares[i][m][c] for i in fs_ids]))  # noqa: E731
    V._save(od / "mask-features.json", {
        "design": DESIGN, "status": MASK_STATUS, "examples": len(ids), "control_every_cell_worst": worst,
        "fs5_median": {m: {"share": med(m, 0), "precision": med(m, 1), "recall": med(m, 2)} for m in MAPS},
        "minutes": round((time.time() - t0) / 60, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"MASK FEATURES DONE: {len(ids)} examples, control {worst:.2e}, {time.time() - t0:.0f} s")


def pair_counts(heads, p, q, step_of):
    """{better, worse, sign_p, by family} of the paired step p against q over `heads` ((name, family, k2, j) tuples)."""
    out = {"better": 0, "worse": 0, "better_heads": [], "worse_heads": [], "family": {}}
    for name, family, k2, j in heads:
        better, worse = step_of(k2, p, q, j)["reliable"], step_of(k2, q, p, j)["reliable"]
        f = out["family"].setdefault(family, {"better": 0, "worse": 0})
        for hit, side in ((better, "better"), (worse, "worse")):
            if hit:
                out[side] += 1
                f[side] += 1
                out[f"{side}_heads"].append(name)
    out["sign_p"] = sign_p(out["better"], out["worse"])
    return out


def cmd_mask(args):
    """The mix read on its dominant cells against the plain mix and against each map's placebo (`mask-features`).
    Stops unless the plain mix read here reproduces the stored (b)."""
    from learn import full_space as F
    from learn import pipeline_fix as PF
    from learn import trusted_data_t3_r as R
    from learn import verify_tracks as V

    PF.require("phase_mask_read")
    root, _, tr, fs, _ = load_sets()
    od = out_dir(root)
    if (od / "mask.json").exists() and not args.force:
        raise SystemExit(f"{od / 'mask.json'} exists: the read is run once (--force to rewrite)")
    S = prepare(root, tr, fs)
    z = np.load(od / "mask-features.npz")
    pos = {int(i): n for n, i in enumerate(z["ids"])}
    tr_ix = [pos[r["i"]] for r in tr]
    fill = {k: fill_means(z[k][tr_ix]) for k in MASK if k != "b"}
    base = S["X_of"]

    def X_of(key, rows):
        if key == "b":
            return base(key, rows)
        X = z[key][[pos[r["i"]] for r in rows]]
        return np.where(np.isnan(X), fill[key], X)

    S["X_of"] = X_of
    lab_te, ids, sec, const_te = S["lab_te"], S["ids"], S["sec"], S["const_te"]
    stored = {r["name"]: r for r in V._load(od / "probe.json")["rows"]["b"]}
    preds, rows_by = {}, {}
    t0 = time.time()
    for key in MASK:
        P, _ = fit_input(S, key, tr, fs)
        preds[key] = P
        ex = {i: {"a2": P["a2"][n], "sw_p": P["sw_p"][n], "mic_p": [m[n] for m in P["mic_p"]],
                  "amp_p": P["amp_p"][n], "c": lab_te[0][n], "cm": lab_te[1][n], "s": lab_te[2][n],
                  "sm": lab_te[3][n], "k": lab_te[4][n], "km": lab_te[5][n]} for n, i in enumerate(ids)}
        rows_by[key] = R.r0_rows(ex, S["info"], S["const"], S["rates"], S["majority"])
        if key == "b":
            for r in rows_by["b"]:
                a, b = r["point"], stored[r["name"]]["point"]
                if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9):
                    raise SystemExit(f"the plain mix differs from the stored (b) on {r['name']}")
            print("CONTROL OK: the plain mix reproduces the stored (b)", flush=True)
        print(f"({key}) {MASK[key]}: {sum(r['readable'] for r in rows_by[key])} readable ({time.time() - t0:.0f} s)",
              flush=True)
    jix = {**{n: j for j, n in enumerate(F.CONT)}, **{n: j for j, n in enumerate(F.SW)},
           **{n: j for j, n in enumerate(F.CAT)}}
    heads = [(r["name"], r["family"], {"continuous": "continuous", "switch": "switch"}.get(
        r["kind"], "amp" if r["name"] == R.AMP_NAME else "mic"), jix.get(r["name"])) for r in rows_by["b"]]

    def step_of(k2, p, q, j):
        return step_row(k2, preds[p], preds[q], ids, j, lab_te, sec, const_te)

    pairs = {f"{k}-b": pair_counts(heads, k, "b", step_of) for k in MAPS}
    pairs.update({f"p{k}-b": pair_counts(heads, f"p{k}", "b", step_of) for k in MAPS})
    pairs.update({f"{k}-p{k}": pair_counts(heads, k, f"p{k}", step_of) for k in MAPS})
    pairs["o-xo"] = pair_counts(heads, "o", "xo", step_of)
    branch, earned = reading(pairs)
    rec = {"design": DESIGN + "#addition-the-mix-on-its-dominant-cells-declared-2026-11-05-before-it-is-computed",
           "status": MASK_STATUS, "inputs": MASK, "lists_check": LISTS.get("check"), "branch": branch, "earned": earned,
           "readable": {k: sum(r["readable"] for r in rows_by[k]) for k in MASK},
           "knobs": {k: sum(r["readable"] for r in rows_by[k] if r["kind"] == "continuous") for k in MASK},
           "switches": {k: sum(r["readable"] for r in rows_by[k] if r["kind"] == "switch") for k in MASK},
           "families": {k: family_table(rows_by[k]) for k in MASK}, "pairs": pairs, "rows": rows_by,
           "minutes": round((time.time() - t0) / 60, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    V._save(od / "mask.json", rec)
    print({k: rec[k] for k in ("readable", "knobs", "switches")})
    for name, c in pairs.items():
        t = c["family"].get(TODAY, {"better": 0, "worse": 0})
        print(f"  {name:6s} {'ahead' if is_ahead(c) else '     '} better {c['better']:3d} worse {c['worse']:3d} sign p {c['sign_p']:.3f}; "
              f"{TODAY} {t['better']}/{t['worse']}")
    print(f"BRANCH: {branch} {earned or ''}")
    print(f"MASK DONE: {od / 'mask.json'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("features")
    sub.add_parser("audible")
    sub.add_parser("posthoc")
    sub.add_parser("mixstem")
    sub.add_parser("mask-features")
    p = sub.add_parser("read")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("mask")
    p.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    {"features": cmd_features, "read": cmd_read, "audible": cmd_audible, "posthoc": cmd_posthoc, "mixstem": cmd_mixstem,
     "mask-features": cmd_mask_features, "mask": cmd_mask}[a.cmd](a)


if __name__ == "__main__":
    main()
