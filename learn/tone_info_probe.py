"""Where the tone information is lost: one linear probe per head on F5's examples, from the target render, the mix,
the X-LANCE stem, the target with its DI, a richer target representation and the DI alone (`docs/tone-info-probe.md`;
ledger `trusted-data-t3`, amendment 2). Descriptive: zero renders, zero separations. Probe-trained on F5's training
examples, read on FS5 with R0's rule (`trusted_data_t3_r.r0_rows`). Outputs go to `tone-probe/` only; `t0/`, `t2/`
and `t3/` are read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -m learn.tone_info_probe features     # the summaries (4 processes), cached in tone-probe/features.npz
    $MAIN -m learn.tone_info_probe read         # the probes and the table, tone-probe/probe.json
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("features")
    sub.add_parser("audible")
    p = sub.add_parser("read")
    p.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    {"features": cmd_features, "read": cmd_read, "audible": cmd_audible}[a.cmd](a)


if __name__ == "__main__":
    main()
