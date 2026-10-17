"""Zero-render bleed measurement on amp tracks (reference.wav), v4.

Signals at 24 kHz (everything above 12 kHz dropped), STFT 2048/1024 Hann, context = crop +- 40 s.
Judge halves held out: A = 1.0-5.5 s, B = 5.5-10 s of the crop; fits use the context minus the
judged half.

Stage 1 (guitar's own share): per-bin complex ridge of the amp track on the part's DI:
  linear  u and u delayed 1,2,3,4,6 frames (a ~0.3 s FIR at frame resolution)
  nl      + tanh(3u), tanh(10u), u|u|, |u|, u^3, tanh(3u) delayed 1,2 frames (13 columns)
Stage 2 (bleed): the stage-1 training residual regressed on the other tracks, one complex
  weight per 4-bin band (47 Hz) per regressor, ridge. Regressors:
  DI    other direct tracks; guitar/bass DIs get u, tanh 3u, tanh 10u. An instrument's amp/mic
        tracks are dropped when its DI is present.
  mic   every other track, minus its own-DI-predictable part (per-bin fit over the context),
        so a live-room mic cannot hand the model this guitar's sound. A mic is excluded from the
        "clean" set when its held-out own-guitar share x (1 - stage-1 share) > -25 dB, i.e.
        when the guitar residual it still carries could pose as bleed ("full" keeps them).
Bleed = held-out drop in residual energy from stage 2, minus the mean of two nulls (all
non-own tracks circularly shifted by >= 30 s), relative to the amp track's energy in the half.
"""
import json
import pathlib
import re
import sys
import time
import zlib

import numpy as np
from scipy import signal

REPO = pathlib.Path("/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT")
sys.path.insert(0, str(REPO))
from analysis import io  # noqa: E402

SR0 = 48000
SR = 24000
CTX = 40.0
NFFT, HOP = 2048, 1024
NB = NFFT // 2 + 1
BAND = 4
MAXLAG = 1200
ALPHA = 3e-3
ALPHA_B = 1e-2
OWN_LAGS_U = [1, 2, 3, 4, 6]
OWN_LAGS_T = [1, 2]
NOWN = 6 + len(OWN_LAGS_U) + len(OWN_LAGS_T)
LIN = [0] + list(range(6, 6 + len(OWN_LAGS_U)))
SIL_DB = -50.0
SIL_GUARD = 24
PROXY_DB = -25.0
HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}
OUT = pathlib.Path(__file__).resolve().parent / "out4"
OUT.mkdir(exist_ok=True)
WIN = np.hanning(NFFT).astype(np.float32)


def catalog_for(rec):
    p = rec["catalog"].get("path", "")
    if "datasets-set3" in p:
        return json.load(open("/Users/yoavbz/ndsp-presets/references/datasets-set3/catalog.json"))
    return json.load(open(REPO / "docs/validation-datasets.json"))


def stem(name):
    s = pathlib.Path(name).stem
    s = re.sub(r"-Norm.*$", "", s)
    return re.sub(r"^\d+_", "", s)


DI_RE = re.compile(r"(?<![A-Za-z])DI(?![A-Za-z])|DI$|DTDI|MicDI|BassBI|TDP-|TDA-|DIRECT|Pedal Board", re.I)


def is_di(name):
    return bool(DI_RE.search(stem(name)))


def di_base(name):
    st = stem(name)
    for pat in (r"^(.*?)(Mic)?DI$", r"^(.*?)\s+DI(?![A-Za-z0-9])", r"^(.*?)BI$"):
        m = re.match(pat, st)
        if m and m.group(1):
            return m.group(1)
    return None


def covered(name, bases):
    st = stem(name)
    for b in bases:
        if st.startswith(b):
            rem = st[len(b):]
            if rem == "" or re.match(r"^[ _.]?(Amp|AMP|Mic|Close|Far)", rem):
                return b
    return None


def nl_di(name):
    return bool(re.search(r"gtr|guitar|bass", stem(name), re.I))


def session_info(crop):
    rec = json.load(open(crop / "record.json"))
    cat = catalog_for(rec)
    root = pathlib.Path(cat["root"]).expanduser()
    ss = [s for s in cat["sessions"] if s["source"] == rec["source"] and s["song"] == rec["song"]]
    assert len(ss) == 1, (rec["source"], rec["song"], len(ss))
    s = ss[0]
    pp = [p for p in s["parts"] if p["part"] == rec["part"]]
    assert len(pp) == 1
    p = pp[0]
    own = {p["di"], p["reference"], *p.get("alternate", []), *p.get("simulated", [])}
    wavs = sorted(n for n in s["files"] if n.lower().endswith(".wav"))
    others = [n for n in wavs if n not in own]
    dis = [n for n in others if is_di(n)]
    bases = [b for b in (di_base(n) for n in dis) if b]
    dropped = {n: covered(n, bases) for n in others if n not in dis and covered(n, bases)}
    mics = [n for n in others if n not in dis and n not in dropped]
    return rec, root / s["path"], p, dis, mics, dropped, sorted(own)


def load24(path):
    a = io.load(path).mono().astype(np.float32)
    return signal.resample_poly(a, 1, 2).astype(np.float32)


def gcc_lag(x, y, maxlag=MAXLAG):
    n = 1 << int(np.ceil(np.log2(len(x) + len(y))))
    R = np.fft.rfft(y, n) * np.conj(np.fft.rfft(x, n))
    R /= np.abs(R) + 1e-12
    r = np.fft.irfft(R, n)
    cand = np.concatenate([r[:maxlag + 1], r[-maxlag:]])
    lags = np.concatenate([np.arange(maxlag + 1), np.arange(-maxlag, 0)])
    i = int(np.argmax(np.abs(cand)))
    return int(lags[i]), float(np.abs(cand[i]) / (np.median(np.abs(cand)) + 1e-12))


def shift(x, L):
    if L == 0:
        return x
    out = np.zeros_like(x)
    if L > 0:
        out[L:] = x[:-L]
    else:
        out[:L] = x[-L:]
    return out


def frame_energy(x):
    n = (len(x) - NFFT) // HOP + 1
    e = np.empty(n)
    for i in range(0, n, 512):
        idx = np.arange(i, min(n, i + 512))[:, None] * HOP + np.arange(NFFT)[None, :]
        e[i:i + 512] = np.sum((x[idx] * WIN) ** 2, axis=1)
    return e


def feats(u, k):
    if k == 6:
        return [u, np.tanh(3 * u), np.tanh(10 * u), u * np.abs(u), np.abs(u), u ** 3]
    if k == 3:
        return [u, np.tanh(3 * u), np.tanh(10 * u)]
    return [u]


def stft_at(sigs, starts):
    idx = starts[:, None] + np.arange(NFFT)[None, :]
    fr = sigs[:, idx].astype(np.float32) * WIN
    S = np.fft.rfft(fr, axis=-1).astype(np.complex64)
    return np.transpose(S, (2, 1, 0))


def solve(G, b, idx, alpha=ALPHA, dn=None):
    Gs = G[:, idx][:, :, idx].astype(np.complex128)
    bs = b[:, idx].astype(np.complex128) if b.ndim == 2 else b
    d = np.real(np.einsum("bii->bi", Gs)) if dn is None else dn[:, idx]
    ok = d > 1e-14 * max(d.max(), 1e-30)
    d = np.where(ok, d, 1.0)
    s = 1 / np.sqrt(d)
    n = len(idx)
    Gn = Gs * s[:, :, None] * s[:, None, :]
    Gn = np.where((ok[:, :, None] & ok[:, None, :]), Gn, 0) + (alpha + (~ok)[:, :, None] * 1.0) * np.eye(n)[None]
    bn = np.where(ok, bs * s, 0)
    return np.linalg.solve(Gn, bn[..., None])[..., 0] * s


def quad(G, w, idx):
    Gs = G[:, idx][:, :, idx]
    return float(np.real(np.einsum("bp,bpq,bq->b", np.conj(w), Gs, w)).sum())


def res_energy(acc, w, idx):
    G, b, yy = acc
    return float(yy.sum() - 2 * np.real(np.einsum("bp,bp->", np.conj(w), b[:, idx])) + quad(G, w, idx))


def add(*xs):
    return [sum(x[i] for x in xs) for i in range(3)]


def pool(x):
    """sum over 4-bin bands along axis 0."""
    nb = x.shape[0]
    nbands = -(-nb // BAND)
    pad = nbands * BAND - nb
    if pad:
        x = np.concatenate([x, np.zeros((pad,) + x.shape[1:], x.dtype)])
    return x.reshape((nbands, BAND) + x.shape[1:]).sum(1)


def expand(w):
    return np.repeat(w, BAND, axis=0)[:NB]


def db(x):
    return float(10 * np.log10(max(x, 1e-9)))


class Part:
    def __init__(self, slug, crop):
        self.slug = slug
        rec, sdir, p, dis, mics, dropped, own = session_info(crop)
        self.rec, self.sdir, self.p = rec, sdir, p
        self.dis, self.mics, self.dropped, self.own = dis, mics, dropped, own
        s48, e48 = rec["excerpt_start_frame"], rec["excerpt_end_frame"]
        ref48 = io.load(sdir / p["reference"]).mono().astype(np.float32)
        di48 = io.load(sdir / p["di"]).mono().astype(np.float32)
        r = np.zeros(len(di48), np.float32)
        r[:min(len(r), len(ref48))] = ref48[:len(r)]
        self.chk = float(np.max(np.abs(r[s48:e48] - io.load(crop / "reference.wav").mono())))
        del ref48
        ref = signal.resample_poly(r, 1, 2).astype(np.float32)
        di = signal.resample_poly(di48, 1, 2).astype(np.float32)
        del r, di48
        self.length = len(di)
        self.start, self.end = s48 // 2, e48 // 2
        self.c0 = max(0, self.start - int(CTX * SR))
        self.c1 = min(self.length, self.end + int(CTX * SR))
        self.dlag, self.dprom = gcc_lag(di[self.c0:self.c1], ref[self.c0:self.c1])
        di = shift(di, self.dlag)
        # info: is the amp track digital silence where the DI is silent?
        e = frame_energy(di)
        act = e > np.percentile(e, 95) * 10 ** (SIL_DB / 10)
        near = np.convolve(act.astype(float), np.ones(2 * SIL_GUARD + 1), mode="same") > 0
        ref_e = frame_energy(ref)
        self.sil_session_s = float((~near).sum() * HOP / SR)
        self.sil_zero_frac = float(np.mean(ref_e[~near] <= 1e-12 * ref_e.max())) if (~near).any() else None
        self.sil_ref_db = float(10 * np.log10(np.median(ref_e[~near]) / np.median(ref_e[act]) + 1e-30)) if (~near).any() else None
        nctx = (self.c1 - self.c0 - NFFT) // HOP + 1
        self.starts = np.arange(nctx) * HOP
        self.centers = (self.c0 + self.starts + NFFT // 2 - self.start) / SR
        lab = np.full(nctx, "C")
        for h, (a, b) in HALVES.items():
            lab[(self.centers >= a) & (self.centers < b)] = h
        self.labels = lab
        self.y = ref[self.c0:self.c1].copy()
        pk = np.percentile(np.abs(di[self.c0:self.c1]), 99.9) + 1e-9
        u = di / pk
        oc = feats(u[self.c0:self.c1], 6)
        oc += [shift(u, k * HOP)[self.c0:self.c1] for k in OWN_LAGS_U]
        t3 = np.tanh(3 * u)
        oc += [shift(t3, k * HOP)[self.c0:self.c1] for k in OWN_LAGS_T]
        self.own_cols = np.stack(oc).astype(np.float16)
        self.groups = []
        P = NOWN
        for kind, names in (("di", dis), ("mic", mics)):
            for n in names:
                k = (3 if nl_di(n) else 1) if kind == "di" else 1
                self.groups.append((n, kind, list(range(P, P + k))))
                P += k
        self.P = P
        self._lag = {}
        del di, ref, u, t3, oc

    def columns(self, null_seed=None):
        rng = np.random.default_rng(null_seed) if null_seed is not None else None
        N = self.c1 - self.c0
        cols = np.zeros((self.P, N), np.float16)
        cols[:NOWN] = self.own_cols
        for n, kind, cs in self.groups:
            a48 = io.load(self.sdir / n).mono().astype(np.float32)
            a = signal.resample_poly(a48, 1, 2).astype(np.float32)
            del a48
            if len(a) < self.length:
                a = np.concatenate([a, np.zeros(self.length - len(a), np.float32)])
            a = a[:self.length]
            if not np.any(a):
                continue
            if rng is None:
                L, pr = gcc_lag(a[self.c0:self.c1], self.y)
                if pr < 8:
                    L = 0
                self._lag[n] = (L, round(pr, 1))
            L = self._lag.get(n, (0, 0))[0]
            a = shift(a, L)
            if rng is not None:
                a = np.roll(a, int(rng.integers(30 * SR, max(31 * SR, self.length - 30 * SR))))
            g = a[self.c0:self.c1]
            if kind == "di":
                pk = np.percentile(np.abs(g), 99.9) + 1e-9
                fs = feats(g / pk, len(cs))
            else:
                fs = [g]
            for c, f in zip(cs, fs):
                cols[c] = f
            del a
        return cols

    def accumulate(self, cols, keep=("A", "B")):
        P = cols.shape[0]
        acc = {g: [np.zeros((NB, P, P), np.complex128), np.zeros((NB, P), np.complex128), np.zeros(NB)] for g in "ABC"}
        kept = {}
        for f0 in range(0, len(self.starts), 32):
            st = self.starts[f0:f0 + 32]
            X = stft_at(cols, st)
            Y = stft_at(self.y[None], st)[..., 0]
            lab = self.labels[f0:f0 + 32]
            for g in "ABC":
                m = lab == g
                if not m.any():
                    continue
                Xg, Yg = X[:, m, :], Y[:, m]
                acc[g][0] += (np.conj(np.transpose(Xg, (0, 2, 1))) @ Xg).astype(np.complex128)
                acc[g][1] += np.einsum("btp,bt->bp", np.conj(Xg).astype(np.complex128), Yg.astype(np.complex128))
                acc[g][2] += np.sum(np.abs(Yg.astype(np.complex128)) ** 2, axis=1)
                if g in keep:
                    kept.setdefault(g, []).append((Xg, Yg))
        kept = {g: (np.concatenate([x for x, _ in v], 1), np.concatenate([y for _, y in v], 1)) for g, v in kept.items()}
        return acc, kept


def decontaminate(acc, kept, mic_idx, P):
    ctx = add(acc["A"], acc["B"], acc["C"])
    Fi = list(range(NOWN))
    T = np.tile(np.eye(P, dtype=np.complex128), (NB, 1, 1))
    share = {}
    G = ctx[0]
    Gc = acc["C"][0]
    Gh = add(acc["A"], acc["B"])[0]
    for m in mic_idx:
        c = solve(G, G[:, :, m], Fi, alpha=1e-3)
        T[:, Fi, m] = -c
        # held-out share: fit on C, test on A+B
        cc = solve(Gc, Gc[:, :, m], Fi, alpha=1e-3)
        me = float(np.real(Gh[:, m, m]).sum())
        re_ = me - 2 * float(np.real(np.einsum("bp,bp->", np.conj(cc), Gh[:, Fi, m]))) + quad(Gh, cc, Fi)
        share[m] = 1 - re_ / max(me, 1e-30)
    Th = np.conj(np.transpose(T, (0, 2, 1)))
    out = {g: [Th @ G_ @ T, np.einsum("bqp,bq->bp", np.conj(T), b_), yy] for g, (G_, b_, yy) in acc.items()}
    kp = {g: (np.einsum("btp,bpq->btq", X.astype(np.complex128), T), Y) for g, (X, Y) in kept.items()}
    return out, kp, share


def own_share(acc):
    Fi = list(range(NOWN))
    w = solve(acc["C"][0], acc["C"][1], Fi)
    te = add(acc["A"], acc["B"])
    return 1 - res_energy(te, w, Fi) / te[2].sum()


def evaluate(acc, kept, groups, clean, record_frames):
    Fi = list(range(NOWN))
    DN = np.real(np.einsum("bii->bi", add(*acc.values())[0]))
    sets = {"clean": [groups[i] for i in clean], "full": groups}
    res = {}
    for h in "AB":
        other = "B" if h == "A" else "A"
        tr = add(acc["C"], acc[other])
        te = acc[h]
        E = float(te[2].sum())
        if E <= 1e-9 * max(float(tr[2].sum()), 1e-30):
            res[h] = None
            continue
        e_lin = res_energy(te, solve(tr[0], tr[1], LIN, dn=DN), LIN)
        wF = solve(tr[0], tr[1], Fi, dn=DN)
        e_nl = res_energy(te, wF, Fi)
        r = dict(E=E, lin=1 - e_lin / E, nl=1 - e_nl / E)
        # stage-2 pooled Grams of the training residual
        G = tr[0]
        bR = tr[1] - np.einsum("bpf,bf->bp", G[:, :, Fi], wF)  # cross with residual, all cols
        Gp, bRp, DNp = pool(G), pool(bR), pool(DN)

        def fit(S):
            wb = expand(solve(Gp, bRp, S, alpha=ALPHA_B, dn=DNp))
            w = np.concatenate([wF, wb], 1)
            return w, res_energy(te, w, Fi + S)

        for name, gs in sets.items():
            Oi = [c for _, _, cs in gs for c in cs]
            if not Oi:
                r[name] = dict(gain=0.0, comp=0.0, unexpl=e_nl / E, top=[])
                continue
            w, e = fit(Oi)
            comp = quad(te[0], w[:, NOWN:], Oi) / E
            top = []
            if name == "clean":
                single = [(e_nl - fit(cs)[1]) / E for _, _, cs in gs]
                o = int(np.argmax(single))
                top = [(gs[o][0], single[o])]
                if len(gs) > 1:
                    sec = [-np.inf if j == o else (e_nl - fit(gs[o][2] + cs)[1]) / E - single[o]
                           for j, (_, _, cs) in enumerate(gs)]
                    j = int(np.argmax(sec))
                    top.append((gs[j][0], sec[j]))
            r[name] = dict(gain=(e_nl - e) / E, comp=comp, unexpl=e / E, top=top)
            if record_frames and name == "clean" and h in kept:
                X, Y = kept[h]
                B = np.einsum("btp,bp->bt", X[:, :, Oi], w[:, NOWN:])
                R = Y.astype(np.complex128) - np.einsum("btp,bp->bt", X[:, :, Fi], wF)
                r[name]["frames"] = (np.sum(np.abs(B) ** 2, 0), np.sum(np.abs(Y.astype(np.complex128)) ** 2, 0),
                                     np.sum(np.abs(R) ** 2, 0), np.sum(np.abs(R - B) ** 2, 0))
        res[h] = r
    return res


def analyse(slug, crop, nnull=2):
    t0 = time.time()
    P_ = Part(slug, crop)
    groups = P_.groups
    mic_idx = [cs[0] for _, k, cs in groups if k == "mic"]
    out = {}
    clean = None
    for tag, seed in [("real", None)] + [(f"null{i}", zlib.crc32(slug.encode()) + i) for i in range(nnull)]:
        cols = P_.columns(seed)
        acc, kept = P_.accumulate(cols, keep=("A", "B") if tag == "real" else ())
        del cols
        if tag == "real":
            osh = own_share(acc)
        acc, kept, share = decontaminate(acc, kept, mic_idx, P_.P)
        if clean is None:
            shares = {groups[i][0]: share[cs[0]] for i, (_, k, cs) in enumerate(groups) if k == "mic"}
            risk = {n: db(max(v, 0)) + db(max(1 - osh, 1e-9)) for n, v in shares.items()}
            clean = [i for i, (n, k, _) in enumerate(groups) if k == "di" or risk[n] <= PROXY_DB]
        out[tag] = evaluate(acc, kept, groups, clean, tag == "real")
        del acc, kept
    res = {"slug": slug, "source": P_.rec["source"], "song": P_.rec["song"], "part": P_.rec["part"],
           "crop_check_maxabs": P_.chk, "di_lag_24k": P_.dlag, "di_lag_prom": round(P_.dprom, 1),
           "own_tracks": P_.own, "di_tracks": P_.dis, "dropped_for_di": P_.dropped,
           "own_share_heldout_ctx": round(osh, 4),
           "mic_own_share_db": {n: round(db(max(v, 0)), 1) for n, v in shares.items()},
           "excluded_proxy_mics": sorted(n for n, (_, k, _) in zip([g[0] for g in groups], groups)
                                         if k == "mic" and groups.index((n, k, _)) not in clean) if False else
                                  sorted(groups[i][0] for i in range(len(groups)) if groups[i][1] == "mic" and i not in clean),
           "di_silent_s": round(P_.sil_session_s, 1), "amp_zero_where_di_silent_frac": P_.sil_zero_frac,
           "amp_level_where_di_silent_db": P_.sil_ref_db, "lags_24k": P_._lag, "halves": {}}
    nulls = [k for k in out if k.startswith("null")]
    for h in "AB":
        R = out["real"][h]
        if R is None:
            res["halves"][h] = {"silent": True}
            continue
        hd = {"guitar_share_linear": round(R["lin"], 4), "guitar_share_nl": round(R["nl"], 4),
              "residual_after_guitar_db": round(db(1 - R["nl"]), 1)}
        for m in ("clean", "full"):
            a = R[m]
            ng = float(np.mean([out[k][h][m]["gain"] for k in nulls if out[k][h] is not None]))
            frac = a["gain"] - max(ng, 0.0)
            corr = a["gain"] - ng if -0.005 <= ng <= 0 else None
            hd[m] = {"gain": round(a["gain"], 5), "gain_null_mean": round(ng, 5),
                     "gain_nulls": [round(out[k][h][m]["gain"], 5) for k in nulls if out[k][h] is not None],
                     "bleed_frac": round(frac, 5), "bleed_db": round(db(frac), 1),
                     "bleed_db_penalty_corrected": None if corr is None else round(db(corr), 1),
                     "comp_db": round(db(a["comp"]), 1),
                     "unexplained_frac": round(a["unexpl"] + min(0.0, 0.0), 4),
                     "unexplained_db": round(db(a["unexpl"]), 1),
                     "top": [(t, round(v, 5), round(db(v), 1)) for t, v in a["top"]]}
            if "frames" in a:
                bt, yt, rt, rbt = a["frames"]
                hd[m]["frames_t"] = [round(float(x), 3) for x in P_.centers[P_.labels == h]]
                hd[m]["frames_bleed_rel_db"] = [round(db(float(x) / max(float(z), 1e-20)), 1) for x, z in zip(bt, yt)]
                hd[m]["frames_ref_db"] = [round(10 * np.log10(float(z) + 1e-20), 1) for z in yt]
                hd[m]["frames_gain_rel_db"] = [round(db(float(x - q) / max(float(z), 1e-20)), 1) for x, q, z in zip(rt, rbt, yt)]
        res["halves"][h] = hd
    res["seconds"] = round(time.time() - t0, 1)
    return res


def summary(r):
    out = {}
    for h, v in r.get("halves", {}).items():
        if v.get("silent"):
            out[h] = "silent"
            continue
        out[h] = dict(nl=v["guitar_share_nl"], clean=v["clean"]["bleed_db"], cn=v["clean"]["gain_null_mean"],
                      full=v["full"]["bleed_db"], un=v["clean"]["unexplained_db"],
                      top=[t[0][:26] for t in v["clean"]["top"]])
    return out


if __name__ == "__main__":
    which = sys.argv[1]
    shard = sys.argv[2] if len(sys.argv) > 2 else "0/1"
    i, n = map(int, shard.split("/"))
    d = json.load(open(REPO / "docs/label-table-parts.json"))["parts"]
    slugs = sorted(d)
    if which not in ("all", "kc"):
        slugs = [s for s in slugs if s in which.split(",")]
    if which == "kc" or (len(sys.argv) > 3 and sys.argv[3] == "kcfirst"):
        kc = set(json.load(open(pathlib.Path(__file__).resolve().parent / "kc_parts.json")))
        slugs = sorted(s for s in slugs if s in kc) + ([] if which == "kc" else sorted(s for s in slugs if s not in kc))
    slugs = slugs[i::n]
    for s in slugs:
        f = OUT / f"{s}.json"
        if f.exists():
            continue
        try:
            r = analyse(s, pathlib.Path(d[s]["crop"]))
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            r = {"slug": s, "error": repr(e)}
        f.write_text(json.dumps(r, indent=1, default=float))
        print(s, r.get("seconds"), summary(r), r.get("excluded_proxy_mics"), flush=True)
