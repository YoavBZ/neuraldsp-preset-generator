"""The rebuild gap's torch side (`docs/rebuild-gap-plan.md`): a differentiable proxy amp bank, B0's
proxy check, stage T's fine-tune (a proxy-ranking loss, with a matched-step control) and the arms'
rebuilds of the amp track. Run with the torch interpreter:

    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_gap_train b0                  # zero renders, CPU
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_gap_train phasecheck         # zero renders: C′'s rotation on PR12
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_gap_train train --fold 0 --arm rank
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_gap_train train --fold 0 --arm ctl
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_gap_train rebuild --arm rank   # CPU, zero renders
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_gap_train b0 --variants arm_rank,arm_ctl,cprime_ref --out b1.json

Everything spectral runs on the CPU: torch.stft's backward is wrong on MPS above 65,536 samples
(and the FFT filters are kept beside it). The network runs on MPS when available.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import shutil
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

SR = 48000
N_KNOBS = 7
N_CAND = 15                                  # S and S ± 1/8 on each of the 7 knobs
STEP = 1 / 8
DISPLACE = (0.15, 0.35)                      # S's distance from θ* on each of 3 knobs
MEL_N, MEL_HOP, MEL_BANDS, MEL_LO, MEL_HI = 2048, 512, 64, 50.0, 16000.0
FLOOR_DB, ACTIVE_DB = 40.0, 40.0
LEVEL = 0.1                                  # every DI enters the proxy at RMS 0.1
# Stage T (the plan's recipe)
BATCH, PROXY_CROPS, PROXY_SUB, PROXY_K = 12, 6, int(1.5 * SR), 8
WARMUP, LR, LR_END, MAX_STEPS, EVERY, PATIENCE, MIN_STEPS, MIN_GAIN = 200, 1e-4, 2e-5, 4000, 250, 1500, 1500, 0.005
VAL_CROPS, VAL_DRAWS, VAL_K = 96, 2, 9
CAL_BATCHES, CAL_SHARE = 50, 0.25
VAL_BANDS = {0: ("Eat The Feeder", "Zeno"), 1: ("Adam Buckley", "Starnes And Shah"),
             2: ("Starnes And Shah", "Swatkins"), 3: ("Swatkins", "Zeno")}   # cprime-sep's, per fold
B0_DRAWS = 32
HELD_OUT_MARKERS = ("Guitar-TECHS P3",)


def seed_int(text):
    return int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)


def home():
    return pathlib.Path("~/ndsp-presets").expanduser()


def out_dir():
    return home() / "learn/rebuild-gap"


# --- the proxy amp bank -------------------------------------------------------------------------------

def knob_values(theta):
    """θ (…, 7) in [0, 1] -> named knob values."""
    return {"gain_db": -6 + 36 * theta[..., 0], "pre_db": -6 + 12 * theta[..., 1], "bias": 0.3 * theta[..., 2],
            "low_db": -9 + 18 * theta[..., 3], "mid_db": -9 + 18 * theta[..., 4], "high_db": -9 + 18 * theta[..., 5],
            "cab_hz": 3000 + 4000 * theta[..., 6]}


def _shelf(f, fc, g_db, high=True):
    import torch

    x = torch.log2(torch.clamp(f, min=20.0) / fc)
    s = torch.sigmoid(3 * x) if high else torch.sigmoid(-3 * x)
    return g_db[..., None] * s


def _bell(f, fc, g_db, bw=1.0):
    import torch

    x = torch.log2(torch.clamp(f, min=20.0) / fc)
    return g_db[..., None] * torch.exp(-0.5 * (x / bw) ** 2)


def _lp_db(f, fc, order=1):
    import torch

    return -10 * order * torch.log10(1 + (f / fc) ** 2)


def _filt(x, db):
    import torch

    X = torch.fft.rfft(x)
    return torch.fft.irfft(X * 10 ** (db / 20), x.shape[-1])


def proxy(x, theta):
    """The proxy amp: x (B, n) at RMS 0.1, θ (B, 7) -> (B, n). Gain (split 0.6/0.4 over two tanh
    stages), a pre-emphasis shelf at 700 Hz with a fixed 60 Hz high-pass and 8 kHz low-pass, an
    asymmetric first stage (bias), a 6 kHz interstage low-pass, a symmetric second stage, a tone
    stack (low shelf 120 Hz, bell 600 Hz, high shelf 2.5 kHz), a cab low-pass (2nd order) and an
    80 Hz high-pass. Zero-phase FFT filters; CPU."""
    import torch

    k = knob_values(theta)
    n = x.shape[-1]
    f = torch.fft.rfftfreq(n, 1 / SR).to(x.dtype)
    hp60 = -10 * torch.log10(1 + (60.0 / torch.clamp(f, min=1.0)) ** 2)
    pre = _shelf(f, 700.0, k["pre_db"]) + (_lp_db(f, 8000.0) + hp60)[None]
    y = _filt(x * (10 ** (k["gain_db"] * 0.6 / 20))[:, None], pre)
    b = k["bias"][:, None]
    y = torch.tanh(y + b) - torch.tanh(b)
    y = _filt(y, _lp_db(f, 6000.0)[None].expand(y.shape[0], -1))
    y = torch.tanh(y * (10 ** (k["gain_db"] * 0.4 / 20))[:, None])
    hp80 = -10 * torch.log10(1 + (80.0 / torch.clamp(f, min=1.0)) ** 2)
    post = (_shelf(f, 120.0, k["low_db"], high=False) + _bell(f, 600.0, k["mid_db"]) + _shelf(f, 2500.0, k["high_db"])
            + _lp_db(f, k["cab_hz"][:, None], order=2) + hp80[None])
    return _filt(y, post)


_MEL = {}


def mel_matrix(n=MEL_N, bands=MEL_BANDS, lo=MEL_LO, hi=MEL_HI):
    import numpy as np
    import torch

    key = (n, bands, lo, hi)
    if key not in _MEL:
        fr = np.fft.rfftfreq(n, 1 / SR)
        m = lambda h: 2595 * np.log10(1 + h / 700)  # noqa: E731
        mi = lambda v: 700 * (10 ** (v / 2595) - 1)  # noqa: E731
        pts = mi(np.linspace(m(lo), m(hi), bands + 2))
        W = np.zeros((bands, len(fr)))
        for i in range(bands):
            a, b, c = pts[i:i + 3]
            W[i] = np.clip(np.minimum((fr - a) / (b - a), (c - fr) / (c - b)), 0, None)
        _MEL[key] = torch.tensor(W, dtype=torch.float32)
    return _MEL[key]


def logmel(y):
    """(B, n) -> (B, 64, frames) log-mel dB. CPU only."""
    import torch

    assert y.device.type == "cpu", "spectral terms stay on the CPU (MPS stft backward bug)"
    w = torch.hann_window(MEL_N, dtype=y.dtype)
    S = torch.stft(y, MEL_N, MEL_HOP, window=w, return_complex=True)
    P = S.real ** 2 + S.imag ** 2
    return 10 * torch.log10(mel_matrix().to(y.dtype) @ P + 1e-10)


def distance(A, R, floor_db=FLOOR_DB, active_db=ACTIVE_DB, eps=1e-4):
    """Judge-like distance of log-mel A from the reference R (both (B, bands, frames)), in the
    judge's order: the level difference taken out first (the mean over R's active cells above its
    floor), then both sides floored `floor_db` under R's loudest band per frame, then what is left of
    the mean removed; R's frames within `active_db` of its loudest; mean smooth |ΔdB|. -> (B,)."""
    import torch

    fl = R.max(1, keepdim=True).values - floor_db
    e = torch.logsumexp(R * (math.log(10) / 10), 1) / (math.log(10) / 10)          # frame level (dB)
    act = (e >= e.max(1, keepdim=True).values - active_db).to(A.dtype)[:, None, :]
    above = act * (R >= fl).to(A.dtype)
    off = ((A - R) * above).sum((1, 2)) / above.sum((1, 2)).clamp(min=1)
    A1 = A - off[:, None, None]
    d = torch.maximum(A1, fl) - torch.maximum(R, fl)
    n = (act.sum((1, 2)) * A.shape[1]).clamp(min=1)
    d = d - ((d * act).sum((1, 2)) / n)[:, None, None]
    return (torch.sqrt(d * d + eps) * act).sum((1, 2)) / n


def norm_rms(x, level=LEVEL):
    return x / (x.pow(2).mean(-1, keepdim=True).sqrt() + 1e-9) * level


def local_set(rng, n=N_KNOBS, step=STEP, displace=DISPLACE):
    """A proxy local set like Σ's neighbourhood: θ* uniform; S displaced from θ* by ±U(displace) on 3
    random knobs; candidates S and S ± step on each knob (clipped). -> (θ*, candidates (15, 7))."""
    import numpy as np

    star = rng.random(n)
    S = star.copy()
    for k in rng.choice(n, 3, replace=False):
        S[k] = star[k] + rng.choice([-1, 1]) * rng.uniform(*displace)
    S = np.clip(S, 0, 1)
    cands = [S]
    for k in range(n):
        for s in (-step, step):
            c = S.copy()
            c[k] = np.clip(c[k] + s, 0, 1)
            cands.append(c)
    return star, np.stack(cands)


def pearson(a, b, eps=1e-8):
    """Pearson correlation along the last axis (torch)."""
    a = a - a.mean(-1, keepdim=True)
    b = b - b.mean(-1, keepdim=True)
    return (a * b).sum(-1) / (a.norm(dim=-1) * b.norm(dim=-1) + eps)


def proxy_terms(p, y, rng, k=PROXY_K, crops=PROXY_CROPS, sub=PROXY_SUB):
    """Stage T's two terms on a training batch. p (net output) and y (true DI), (B, 1, n) on any
    device; computed on the CPU, the gradient flowing back to p. -> (1 − Pearson ranking term,
    output-match term)."""
    import numpy as np
    import torch

    B, n = p.shape[0], p.shape[-1]
    idx = rng.choice(B, min(crops, B), replace=False)
    offs = rng.integers(0, max(1, n - sub + 1), len(idx))
    pc = torch.stack([p[i, 0, o:o + sub] for i, o in zip(idx, offs)]).cpu().float()
    yc = torch.stack([y[i, 0, o:o + sub] for i, o in zip(idx, offs)]).cpu().float()
    pc, yc = norm_rms(pc), norm_rms(yc)
    stars, cands = [], []
    for _ in range(len(idx)):
        s, c = local_set(rng)
        stars.append(s)
        cands.append(c[rng.choice(len(c), k, replace=False)])
    th_star = torch.tensor(np.stack(stars), dtype=torch.float32)
    th = torch.tensor(np.concatenate(cands), dtype=torch.float32)                      # (crops·k, 7)
    with torch.no_grad():
        ref = logmel(proxy(yc, th_star)).repeat_interleave(k, 0)
        Ft = logmel(proxy(yc.repeat_interleave(k, 0), th))
        dt = distance(Ft, ref).view(len(idx), k)
    Fr = logmel(proxy(pc.repeat_interleave(k, 0), th))
    dr = distance(Fr, ref).view(len(idx), k)
    rank = (1 - pearson(dr, dt)).mean()
    match = distance(Fr, Ft).mean()
    return rank.to(p.device), match.to(p.device)


def proxy_fidelity(x, t, rng, draws, k=None):
    """Proxy fidelity of DI x against the true DI t (1-D numpy, same length): per draw, the Spearman
    of D(P(x, θ_c), P(t, θ*)) with D(P(t, θ_c), P(t, θ*)) over the candidates (all 15, or k of
    them); the mean over draws. No gradient."""
    import numpy as np
    import torch
    from scipy.stats import spearmanr

    xs = norm_rms(torch.tensor(np.asarray(x, np.float32))[None])
    ts = norm_rms(torch.tensor(np.asarray(t, np.float32))[None])
    out = []
    with torch.no_grad():
        for _ in range(draws):
            s, c = local_set(rng)
            if k:
                c = c[np.sort(rng.choice(len(c), k, replace=False))]
            th = torch.tensor(c, dtype=torch.float32)
            ref = logmel(proxy(ts, torch.tensor(s[None], dtype=torch.float32)))
            dt = distance(logmel(proxy(ts.expand(len(c), -1), th)), ref.expand(len(c), -1, -1)).numpy()
            dx = distance(logmel(proxy(xs.expand(len(c), -1), th)), ref.expand(len(c), -1, -1)).numpy()
            r = spearmanr(dx, dt).correlation
            if r is not None and math.isfinite(r):
                out.append(float(r))
    return float(np.mean(out)) if out else None


# --- B0 / B1: the proxy check on the 24 parts (zero renders) --------------------------------------------

def cmd_b0(variants=None, out_name="b0.json"):
    """Proxy fidelity per part of each rebuild (on the measure DI's timeline, its own rotation) and of
    each built probe, against the measure DI; the same draws for every variant of a part."""
    import numpy as np

    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import rebuild_gap as G

    ps = K.parts()
    path = out_dir() / out_name
    res = json.loads(path.read_text()) if path.exists() else {}
    names = variants or [*G.VARIANT_SOURCES, *[p for p in G.PROBES if p != "dep_rot"]]
    for slug in sorted(s for s in ps if s not in LO.EXCLUDED):
        t = K.measure_di(ps[slug])
        row = res.get(slug, {})
        for v in names:
            if v in row:
                continue
            if v in G.VARIANT_SOURCES:
                x, *_ = G.align(G.variant_di(v, slug), t, ps[slug]["judge_lag"])
            elif G.is_arm(v):
                x, *_ = G.align(np.load(G.probe_path(v, slug)), t, ps[slug]["judge_lag"])
            else:
                p = G.probe_path(v, slug)
                if not p.exists():
                    continue
                x = np.load(p)
            n = min(len(x), len(t))
            rng = np.random.default_rng(seed_int(f"rebuild-gap|b0|{slug}"))
            row[v] = proxy_fidelity(x[:n], t[:n], rng, B0_DRAWS)
        res[slug] = row
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(res, indent=1))
        tmp.replace(path)
        print(slug, {k: round(v, 3) if v is not None else None for k, v in row.items()}, flush=True)


# --- stage T: the fine-tune ---------------------------------------------------------------------------------

def schedule(step, lr=LR, lr_end=LR_END, warmup=WARMUP, total=MAX_STEPS):
    """A linear warm-up to lr, then a cosine to lr_end over `total` steps (the same in both arms)."""
    if step < warmup:
        return lr * (step + 1) / warmup
    frac = min(1.0, (step - warmup) / max(1, total - warmup))
    return lr_end + 0.5 * (lr - lr_end) * (1 + math.cos(math.pi * frac))


def is_best(value, best, min_gain=MIN_GAIN):
    return value is not None and (best is None or value >= best + min_gain)


def should_stop(step, best_step, patience=PATIENCE, min_steps=MIN_STEPS, max_steps=MAX_STEPS):
    return step >= max_steps or (step >= min_steps and step - best_step >= patience)


def cprime_path(fold):
    d = home() / "learn/direc"
    return d / ("models-cprime/fold2.pt" if fold == 2 else f"models-cprime-f{fold}/fold{fold}.pt")


def model_dir(arm, fold):
    return out_dir() / f"models-{arm}-f{fold}"


class Data:
    """C′'s data pipeline (`direc.fit`'s `make`, PR12 cache only), with the fold's validation bands
    out of training (rows and bleed), as cprime-sep did."""

    def __init__(self, fold, seed=0):
        import numpy as np
        import soundfile as sf

        from learn import direc as D
        from learn import train as TR

        self.D = D
        cache = home() / "learn/direc/cache"
        self.cache = cache
        self.X = np.load(cache / "input.npy", mmap_mode="r")
        self.Y = np.load(cache / "di.npy", mmap_mode="r")
        self.S = np.load(cache / "di_spectrum.npy")
        self.meta = json.loads((cache / "meta.json").read_text())
        assert not any(any(h in m["band"] for h in HELD_OUT_MARKERS) for m in self.meta), "held-out rows in the cache"
        fold_of, band_of = TR.k3_folds()
        f = np.array([fold_of.get(m["band"], -1) for m in self.meta])
        vb = set(VAL_BANDS[fold])
        assert all(fold_of[b] != fold for b in vb)
        held = np.array([m["band"] in vb for m in self.meta])
        self.tr = np.where((f != fold) & ~held)[0]
        self.va = np.where(held)[0]
        self.avg = D.fold_average(cache, fold)
        self.freqs = np.fft.rfftfreq(D.SPEC_N, 1 / D.SR)
        self.cfreq = np.fft.rfftfreq(D.CLIP, 1 / D.SR)
        self.rng = np.random.default_rng(seed)
        self.bleed = []
        for part, b in band_of.items():
            if fold_of[b] != fold and b not in vb and (D.CROPS / part / "backing_instrumental.wav").exists():
                y, _ = sf.read(str(D.CROPS / part / "backing_instrumental.wav"), dtype="float32", always_2d=True)
                self.bleed.append(y.mean(1))
        self.fold = fold

    def make(self, idx, train, dev):
        """`direc.fit`'s make(), unchanged (EQ to the fold's average, the tilt/bell, bleed and noise
        augmentation and a random 3-s crop in training; the centre crop otherwise)."""
        import numpy as np
        import torch

        D, rng = self.D, self.rng
        xs, ys = [], []
        for i in idx:
            x = self.X[i].astype(np.float32) / 32767
            y = self.Y[i].astype(np.float32) / 32767
            own = self.S[i] - self.S[i].mean()
            g = np.clip(self.avg - own, -15, 15)
            y = np.fft.irfft(np.fft.rfft(y) * 10 ** (np.interp(self.cfreq, self.freqs, g) / 20), D.CLIP).astype(np.float32)
            if train:
                lf = np.log2(np.maximum(self.cfreq, 20) / 1000)
                tilt = rng.uniform(-3, 3) * np.clip(lf / 3.3, -1, 1)
                fc, gb = rng.uniform(np.log2(200), np.log2(6000)), rng.uniform(-4, 4)
                bell = gb * np.exp(-0.5 * ((np.log2(np.maximum(self.cfreq, 20)) - fc) / 0.5) ** 2)
                x = np.fft.irfft(np.fft.rfft(x) * 10 ** ((tilt + bell) / 20), D.CLIP).astype(np.float32)
                if rng.random() < 0.5 and self.bleed:
                    b = self.bleed[rng.integers(len(self.bleed))]
                    s = rng.integers(0, max(1, len(b) - D.CLIP))
                    seg = np.zeros(D.CLIP, np.float32)
                    seg[:len(b[s:s + D.CLIP])] = b[s:s + D.CLIP]
                    x = x + seg / (seg.std() + 1e-9) * x.std() * 10 ** (-rng.uniform(12, 30) / 20)
                if rng.random() < 0.5:
                    x = x + rng.standard_normal(D.CLIP).astype(np.float32) * x.std() * 10 ** (-rng.uniform(45, 75) / 20)
                a = rng.integers(0, D.CLIP - D.CROP)
            else:
                a = (D.CLIP - D.CROP) // 2
            x, y = x[a:a + D.CROP], y[a:a + D.CROP]
            xs.append(x / (x.std() + 1e-9) * 0.1)
            ys.append(y / (y.std() + 1e-9) * 0.1)
        return (torch.tensor(np.stack(xs), device=dev).unsqueeze(1), torch.tensor(np.stack(ys), device=dev).unsqueeze(1))


def validate(net, data, vidx, vdraws, dev):
    """Proxy fidelity (and C′'s loss) on the fixed validation crops: per crop, its fixed draws. The
    data stream's generator is not touched (validation crops are centre crops)."""
    import numpy as np
    import torch
    from scipy.stats import spearmanr

    D = data.D
    net.eval()
    fids, recon = [], 0.0
    with torch.no_grad():
        for s in range(0, len(vidx), BATCH):
            vx, vy = data.make(vidx[s:s + BATCH], False, dev)
            vp = net(vx)
            recon += float(100 * (vp - vy).abs().mean() + D.mrstft(vp.squeeze(1), vy.squeeze(1)))
            pc, yc = norm_rms(vp[:, 0].cpu().float()), norm_rms(vy[:, 0].cpu().float())
            for j in range(len(pc)):
                for star, cand in vdraws[s + j]:
                    th = torch.tensor(cand, dtype=torch.float32)
                    ref = logmel(proxy(yc[j:j + 1], torch.tensor(star[None], dtype=torch.float32)))
                    dt = distance(logmel(proxy(yc[j:j + 1].expand(len(cand), -1), th)), ref.expand(len(cand), -1, -1))
                    dr = distance(logmel(proxy(pc[j:j + 1].expand(len(cand), -1), th)), ref.expand(len(cand), -1, -1))
                    r = spearmanr(dr.numpy(), dt.numpy()).correlation
                    if r is not None and math.isfinite(r):
                        fids.append(float(r))
    net.train()
    return (float(np.mean(fids)) if fids else None), recon


def fit(fold, arm, max_steps=MAX_STEPS, stop_at=None, device=None):
    """Stage T for one fold and arm. `rank`: C′'s loss + λ_rank·(1 − Pearson) + λ_out·match, λ fixed
    at step 0 by the share rule; keeps the best proxy-validation checkpoint, stops PATIENCE steps
    after it (at least MIN_STEPS, at most max_steps). `ctl`: λ = 0, the same data stream and
    schedule, run to `stop_at` (rank's best step) and saved there."""
    import numpy as np
    import torch

    from learn import direc as D

    torch.manual_seed(0)
    dev = torch.device(device or os.environ.get("DIREC_DEVICE") or ("mps" if torch.backends.mps.is_available() else "cpu"))
    out = model_dir(arm, fold)
    out.mkdir(parents=True, exist_ok=True)
    data = Data(fold, seed=0)
    prng = np.random.default_rng(1)                                    # the proxy draws: their own stream
    vr = np.random.default_rng(seed_int(f"rebuild-gap|val|{fold}"))
    vidx = vr.choice(data.va, min(VAL_CROPS, len(data.va)), replace=False)
    vdraws = []
    for _ in vidx:
        ds = []
        for _ in range(VAL_DRAWS):
            s, c = local_set(vr)
            ds.append((s, c[np.sort(vr.choice(len(c), VAL_K, replace=False))]))
        vdraws.append(ds)
    resume = cprime_path(fold)
    net = D.build_model().to(dev)
    net.load_state_dict(torch.load(resume, map_location=dev))
    opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=1e-5)
    lam = {"rank": 0.0, "match": 0.0}
    if arm == "rank":
        cr = np.random.default_rng(2)
        crng = np.random.default_rng(3)
        lc, lr_, lm = [], [], []
        saved = data.rng
        data.rng = cr                                                  # calibration leaves the data stream alone
        net.eval()
        with torch.no_grad():
            for _ in range(CAL_BATCHES):
                x, y = data.make(cr.choice(data.tr, BATCH, replace=False), True, dev)
                p = net(x)
                lc.append(float(D.training_loss(p, y)))
                a, b = proxy_terms(p, y, crng)
                lr_.append(float(a))
                lm.append(float(b))
        net.train()
        data.rng = saved
        lam = {"rank": float(CAL_SHARE * np.mean(lc) / max(np.mean(lr_), 1e-9)),
               "match": float(CAL_SHARE * np.mean(lc) / max(np.mean(lm), 1e-9))}
        print(f"fold {fold} calibration: C′ loss {np.mean(lc):.3f}, rank {np.mean(lr_):.3f}, match {np.mean(lm):.3f} "
              f"-> λ {lam}", flush=True)
    cfg = {"fold": fold, "arm": arm, "seed": 0, "proxy_seed": 1, "batch": BATCH, "lr": LR, "lr_end": LR_END,
           "warmup": WARMUP, "max_steps": max_steps, "stop_at": stop_at, "every": EVERY, "patience": PATIENCE,
           "min_steps": MIN_STEPS, "min_gain": MIN_GAIN, "lambda": lam, "resume": str(resume),
           "caches": [str(data.cache)], "val_bands": list(VAL_BANDS[fold]), "train_rows": int(len(data.tr)),
           "val_rows": int(len(data.va)), "proxy": {"crops": PROXY_CROPS, "sub": PROXY_SUB, "k": PROXY_K}}
    (out / "config.json").write_text(json.dumps(cfg, indent=1))
    print(f"fold {fold} {arm}: train {len(data.tr)} rows, validation {len(data.va)} rows "
          f"({VAL_BANDS[fold]}), bleed {len(data.bleed)}, device {dev}", flush=True)
    curve = []
    f0, r0 = validate(net, data, vidx, vdraws, dev)
    curve.append({"step": 0, "proxy_fidelity": f0, "recon": r0})
    print(f"fold {fold} {arm} step 0 proxy {f0:.4f} recon {r0:.3f}", flush=True)
    best, best_step = f0, 0
    torch.save(net.state_dict(), out / "best.pt")
    target = stop_at if arm == "ctl" else max_steps
    t0, step, skipped, streak, recoveries, window = time.time(), 0, 0, 0, 0, []
    while step < target:
        for g in opt.param_groups:
            g["lr"] = schedule(step, total=max_steps)
        x, y = data.make(data.rng.choice(data.tr, BATCH, replace=False), True, dev)
        p = net(x)
        loss = D.training_loss(p, y)
        if arm == "rank":
            a, b = proxy_terms(p, y, prng)
            loss = loss + lam["rank"] * a + lam["match"] * b
        opt.zero_grad()
        loss.backward()
        # clip_grad_norm_ gives NaN on MPS: clip by hand, skip non-finite steps (direc.fit's guard).
        grads = [q.grad for q in net.parameters() if q.grad is not None]
        total = torch.sqrt(sum((g.detach() ** 2).sum() for g in grads))
        bad = not bool(torch.isfinite(total))
        window.append(bad)
        if len(window) > 200:
            window.pop(0)
        if len(window) == 200 and sum(window) > 40:
            streak, window = 25, []
        if bad or streak >= 25:
            skipped += 1
            streak += 1
            if streak >= 25:
                net.load_state_dict(torch.load(out / "last.pt" if (out / "last.pt").exists() else resume, map_location=dev))
                opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=1e-5)
                recoveries += 1
                streak = 0
                print(f"fold {fold} {arm} recovery {recoveries} at step {step}", flush=True)
                if recoveries > 20:
                    raise RuntimeError("training keeps producing non-finite gradients")
            continue
        streak = 0
        if total > 5.0:
            for g in grads:
                g.mul_(5.0 / total)
        opt.step()
        step += 1
        if step % EVERY == 0 or (arm == "ctl" and step == target):
            fid, rec = validate(net, data, vidx, vdraws, dev)
            el = time.time() - t0
            curve.append({"step": step, "proxy_fidelity": fid, "recon": rec, "loss": float(loss.detach()),
                          "skipped": skipped, "minutes": el / 60})
            print(f"fold {fold} {arm} step {step} {el / 60:.1f} min ({step / el:.2f} it/s) loss {float(loss.detach()):.3f} "
                  f"proxy {fid:.4f} recon {rec:.3f} skipped {skipped}", flush=True)
            torch.save(net.state_dict(), out / "last.pt")
            if arm == "rank":
                if is_best(fid, best):
                    best, best_step = fid, step
                    torch.save(net.state_dict(), out / "best.pt")
                if should_stop(step, best_step, max_steps=max_steps):
                    print(f"fold {fold} rank stopped at step {step}: best {best:.4f} at {best_step}", flush=True)
                    break
            (out / "curve.json").write_text(json.dumps(curve, indent=1))
    if arm == "ctl":
        torch.save(net.state_dict(), out / "best.pt")
        best_step, best = step, curve[-1]["proxy_fidelity"]
    shutil.copyfile(out / "best.pt", out / f"fold{fold}.pt")
    (out / "curve.json").write_text(json.dumps(curve, indent=1))
    (out / "result.json").write_text(json.dumps({"best_step": best_step, "best_proxy": best, "step0_proxy": f0,
                                                 "steps_run": step, "skipped": skipped, "recoveries": recoveries,
                                                 "minutes": (time.time() - t0) / 60}, indent=1))
    (out / "DONE").write_text(time.strftime("%Y-%m-%d %H:%M:%S\n"))
    print(f"fold {fold} {arm} done: final = step {best_step} (proxy {best})", flush=True)


def cmd_phasecheck(folds=(0, 1, 2, 3), crops=VAL_CROPS):
    """Amendment 1, item 10 (zero renders): C′'s constant phase rotation, |c| and 80 Hz–2 kHz
    coherence against the true DI on PR12 validation crops (fold f's own validation rows, centre 3-s
    crops, C′'s own data pipeline), per fold. If C′ is phase-correct on PR12, the rotation on real
    amp tracks is a real-chain domain shift that a PR12-only fine-tune can't learn to remove."""
    import numpy as np
    import torch

    from learn import direc as D
    from learn import rebuild_gap as G
    from learn import train as TR

    res = {}
    for fold in folds:
        data = Data(fold, seed=0)
        fold_of, _ = TR.k3_folds()
        f = np.array([fold_of.get(m["band"], -1) for m in data.meta])
        rows = np.where(f == fold)[0]
        idx = np.random.default_rng(seed_int(f"rebuild-gap|phasecheck|{fold}")).choice(rows, min(crops, len(rows)), replace=False)
        net = D.load_model(cprime_path(fold)).eval()
        out = []
        with torch.no_grad():
            for s in range(0, len(idx), BATCH):
                x, y = data.make(idx[s:s + BATCH], False, torch.device("cpu"))
                p = net(x)
                for j in range(len(p)):
                    a, b = p[j, 0].numpy().astype(np.float64), y[j, 0].numpy().astype(np.float64)
                    lags = np.arange(-G.ALIGN_WINDOW, G.ALIGN_WINDOW + 1)
                    c = G.analytic_xcorr(a, b, lags)
                    i = int(np.argmax(np.abs(c)))
                    a2 = G.rotate(G.shift(a, -int(lags[i])), -float(np.angle(c[i])))
                    out.append({"lag": int(lags[i]), "phi_deg": float(np.degrees(np.angle(c[i]))), "abs_c": float(np.abs(c[i])),
                                "coh_80_2k": G.coherence(a2, b, 80, 2000)})
        ph = np.array([o["phi_deg"] for o in out])
        res[fold] = {"crops": len(out), "median_abs_phi_deg": float(np.median(np.abs(ph))),
                     "share_abs_phi_over_45": float(np.mean(np.abs(ph) > 45)),
                     "median_abs_c": float(np.median([o["abs_c"] for o in out])),
                     "median_coh_80_2k": float(np.median([o["coh_80_2k"] for o in out])),
                     "median_lag": float(np.median([o["lag"] for o in out])), "rows": out}
        print(fold, {k: v for k, v in res[fold].items() if k != "rows"}, flush=True)
    p = out_dir() / "phasecheck.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, indent=1))


def rank_best_step(fold):
    p = model_dir("rank", fold) / "result.json"
    if not p.exists():
        raise SystemExit(f"rank fold {fold} has not finished")
    return json.loads(p.read_text())["best_step"]


# --- the arms' rebuilds (zero renders) ------------------------------------------------------------------------

def cmd_rebuild(arm):
    """Each part's reference.wav rebuilt by its fold's `arm` network exactly as 1b (`rebuild_from`),
    with 2a's checks and experiment 4's leak assertion; writes arms/<arm_name>/check.json and the
    combined arms/check.json."""
    from learn import local_objective as LO

    from learn import confirm_run as CR

    from learn import di_fine_structure as DF

    name = f"arm_{arm}"
    d = out_dir() / "arms" / name

    def parent_pool(band, path, f):                    # the parent C′'s pool too (1d's amendment 4a)
        DF.assert_no_leak(band, f, f, DF.train_pool_bands(f, [DF.MODELS / c for c in DF.CACHES]))

    bad, missing = LO.rebuild_from(LO.MATCHED_DI, lambda slug, part: CR.mono(part["crop"] / "reference.wav"),
                                   net=lambda f: model_dir(arm, f) / f"fold{f}.pt", extra_leak=parent_pool,
                                   out_dir=d, gate=False)
    ok = {a: json.loads((out_dir() / "arms" / f"arm_{a}" / "check.json").read_text()).get("ok")
          if (out_dir() / "arms" / f"arm_{a}" / "check.json").exists() else False for a in ("rank", "ctl")}
    (out_dir() / "arms" / "check.json").write_text(json.dumps({"ok": all(ok.values()), "arms": ok}, indent=1))
    if bad or missing:
        raise SystemExit(f"{name} rebuilds fail the checks: {bad or missing}")
    print(f"{name}: all 24 rebuilds pass")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("b0")
    b.add_argument("--variants")
    b.add_argument("--out", default="b0.json")
    sub.add_parser("phasecheck")
    f = sub.add_parser("train")
    f.add_argument("--fold", type=int, required=True)
    f.add_argument("--arm", choices=("rank", "ctl"), required=True)
    f.add_argument("--max-steps", type=int, default=MAX_STEPS)
    f.add_argument("--device")
    r = sub.add_parser("rebuild")
    r.add_argument("--arm", choices=("rank", "ctl"), required=True)
    a = ap.parse_args(argv)
    if a.cmd == "b0":
        cmd_b0(a.variants.split(",") if a.variants else None, a.out)
    elif a.cmd == "phasecheck":
        cmd_phasecheck()
    elif a.cmd == "train":
        stop_at = rank_best_step(a.fold) if a.arm == "ctl" else None
        fit(a.fold, a.arm, a.max_steps, stop_at, a.device)
    else:
        cmd_rebuild(a.arm)


if __name__ == "__main__":
    main()
