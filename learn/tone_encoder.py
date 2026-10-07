"""A guitar tone encoder trained contrastively on crossed renders (`docs/tone-encoder-plan.md`).

The Open-Amp Fx-Encoder recipe (SimCLR-style: the same device on different clips are
positives), reimplemented on log-mel input and trained on our own renders only. No
Open-Amp weights are used.

    # 1. mel cache of the crossed renders, the four kill panels and the bleed sources
    .venv/bin/python -m learn.tone_encoder cache
    # 2. one encoder per K3 fold (CPU)
    PYTORCH_ENABLE_MPS_FALLBACK=0 $TORCH_PY -m learn.tone_encoder fit --fold 0
    # 3. the declared screens
    PYTORCH_ENABLE_MPS_FALLBACK=0 $TORCH_PY -m learn.tone_encoder identify
    PYTORCH_ENABLE_MPS_FALLBACK=0 $TORCH_PY -m learn.tone_encoder rerank

Frontend: 48 kHz mono, power STFT (Hann, 2048, hop 480 = 10 ms), 128 triangular mel
bands 30 Hz–16 kHz, stored as dB (float16) of the raw clip. Augmentation (post-amp EQ,
bleed, noise) is applied to mel power; then each view is loudness-normalised by its
mean total mel power over active frames (within 40 dB of its loudest frame), turned to
dB at absolute level, with no per-frequency normalisation.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
import time

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

ROOT = pathlib.Path(os.path.expanduser(os.environ.get("TONE_ROOT", "~/ndsp-presets/learn/tone-encoder")))
RENDERS = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/tone-encoder/renders"))
CACHE = ROOT / "cache"
MODELS = ROOT / "models"
KILL = pathlib.Path(os.path.expanduser("~/ndsp-presets/runs/kill"))
CROPS = pathlib.Path(os.path.expanduser("~/ndsp-presets/references/validation-crops"))
PANELS = ("pr12", "sw50r", "ac20", "pr12-clean")
SR, N_FFT, HOP, MELS = 48000, 2048, 480, 128
FPS = SR // HOP                        # 100 frames per second
HALF_A = (1.0, 5.5)
CROP = 300                             # training crop, frames (3 s)
STEPS, SEED = 4000, 20261008           # declared recipe (docs/tone-encoder-plan.md)
SILENT = -35.0                         # rerank-plan amendment: parts dropped from the panels


# --- frontend -----------------------------------------------------------------

def mel_matrix():
    import numpy as np

    def hz_to_mel(f):
        return 2595 * np.log10(1 + f / 700)

    def mel_to_hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    edges = mel_to_hz(np.linspace(hz_to_mel(30.0), hz_to_mel(16000.0), MELS + 2))
    m = np.zeros((MELS, len(freqs)), np.float32)
    for b in range(MELS):
        lo, c, hi = edges[b], edges[b + 1], edges[b + 2]
        up = (freqs - lo) / max(c - lo, 1e-9)
        down = (hi - freqs) / max(hi - c, 1e-9)
        m[b] = np.clip(np.minimum(up, down), 0, None)
    return m, edges[1:-1]


_MEL = None


def mel_db(x):
    """[MELS, frames] dB of mel power (float32) for a mono 48-kHz signal."""
    import numpy as np
    from scipy.signal import stft

    global _MEL
    if _MEL is None:
        _MEL = mel_matrix()[0]
    _, _, Z = stft(x.astype(np.float32), fs=SR, window="hann", nperseg=N_FFT,
                   noverlap=N_FFT - HOP, boundary=None, padded=False)
    P = (np.abs(Z) ** 2).astype(np.float32)
    return 10 * np.log10(_MEL @ P + 1e-12)


def read_mono(path):
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    assert sr == SR, (path, sr)
    return x.mean(axis=1)


# --- cache ----------------------------------------------------------------------

def build_cache():
    """mel dB (float16) of every crossed render, panel render and bleed source."""
    import numpy as np

    from learn import set3
    from learn import train as TR

    CACHE.mkdir(parents=True, exist_ok=True)
    fold_of, band_of = TR.k3_folds()
    rows = []
    for f in sorted(RENDERS.glob("index-w*.jsonl")):
        rows += [json.loads(line) for line in f.read_text().splitlines() if line]
    rows = sorted((r for r in rows if "bad" not in r and 20 * math.log10(r["gain"]) <= 60),
                  key=lambda r: r["id"])
    clips = [{"kind": "crossed", "id": r["id"], "group": r["block"], "setting": f"{r['block']}-s{r['setting']}",
              "amp": r["amp"], "band": r["band"], "di": f"{r['file']}@{r['start_s']}",
              "file": str(RENDERS / f"{r['id']}.flac")} for r in rows]
    for r in rows:
        assert not set3.is_held_out(r["file"])
    # Each PR12 setting's base, re-derived from its seed as pr12.sample draws it: "random",
    # or the factory preset it jittered (as "pr12|factory:<name>", the panels' naming).
    from learn import pr12
    names = list(pr12.factory_presets())
    seeds = {b["block"]: b["settings"] for b in json.loads((RENDERS / "plan.json").read_text())}
    for c, r in zip(clips, rows):
        if r["amp"] == "pr12":
            import random as _random
            g = _random.Random(seeds[r["block"]][r["setting"]])
            c["base"] = "random" if g.random() < 0.5 else f"pr12|factory:{names[g.randrange(len(names))]}"
    catalog = json.loads((PLUGIN_ROOT / "docs" / "validation-datasets.json").read_text())
    split = {"-".join(x.replace("/", "_").replace(" ", "_") for x in (s["source"], s["song"], p["part"])):
             s["split"] for s in catalog["sessions"] for p in s["parts"]}
    assert all(split[p] == "development" for p in band_of), "a panel or bleed part is not development"
    seen = set()
    for panel in PANELS:
        index = json.loads((KILL / panel / "index.json").read_text())
        amp = index["amp"]
        for r in index["rows"]:
            if "file" not in r or r["file"] in seen or r["candidate"] == "template":
                continue
            seen.add(r["file"])
            clips.append({"kind": "panel", "id": f"{amp}|{r['part']}|{r['candidate']}", "group": f"panel-{amp}",
                          "setting": f"{amp}|{r['candidate']}", "amp": amp, "band": band_of[r["part"]],
                          "di": r["part"], "part": r["part"], "candidate": r["candidate"], "file": r["file"]})
    import soundfile as sf
    lengths = [(sf.info(c["file"]).frames - N_FFT) // HOP + 1 for c in clips]
    offs = np.concatenate([[0], np.cumsum(lengths)])
    M = np.lib.format.open_memmap(CACHE / "mel.npy", mode="w+", dtype=np.float16,
                                  shape=(int(offs[-1]), MELS))
    for i, c in enumerate(clips):
        d = mel_db(read_mono(c["file"])).T
        assert len(d) == lengths[i], (c["file"], d.shape, lengths[i])
        M[offs[i]:offs[i] + len(d)] = np.maximum(d, -150)
        c["off"], c["len"] = int(offs[i]), int(len(d))
        if i % 2000 == 0:
            print(f"cached {i}/{len(clips)}", flush=True)
    M.flush()
    # Development parts silent over half A (rerank-plan amendment): template+R quieter
    # than -35 LUFS there.
    import pyloudnorm
    meter = pyloudnorm.Meter(SR)
    silent = []
    for r in json.loads((KILL / "pr12-clean" / "index.json").read_text())["rows"]:
        if r["candidate"] == "template+R" and "file" in r:
            y = read_mono(r["file"])[int(HALF_A[0] * SR):int(HALF_A[1] * SR)].astype("float64")
            if meter.integrated_loudness(y) <= SILENT:
                silent.append(r["part"])
    bleed = []
    for part, band in sorted(band_of.items()):
        f = CROPS / part / "backing_instrumental.wav"
        if f.exists():
            d = mel_db(read_mono(f)).T
            bleed.append({"part": part, "band": band, "mel": d.astype(np.float16)})
    np.savez(CACHE / "bleed.npz", mel=np.array([b["mel"] for b in bleed], dtype=object),
             band=np.array([b["band"] for b in bleed]))
    rng = np.random.default_rng(0)
    noise = 10 * np.log10((10 ** (mel_db(rng.standard_normal(10 * SR).astype(np.float32)) / 10)).mean(axis=1))
    np.save(CACHE / "noise_db.npy", noise)                  # white noise at unit variance
    (CACHE / "clips.json").write_text(json.dumps({"clips": clips, "silent_parts": sorted(silent)}))
    print(f"cached {len(clips)} clips ({sum(c['kind'] == 'crossed' for c in clips)} crossed), "
          f"{len(bleed)} bleed sources; silent parts {silent}")


# --- model --------------------------------------------------------------------------

def build_model(width=128, blocks=4, dim=64):
    """Fx-Encoder-style residual 1-D conv stack over time, with the 128 mel bands as
    input channels (so absolute spectral shape is seen directly), time pooling by 2
    after each block but the last, then mean and std over time and a 2-layer head."""
    import torch
    import torch.nn as nn

    class Conv(nn.Module):
        """Conv1d (kernel 3, same padding) as unfold + einsum: this torch build has no
        MKLDNN, and its Conv1d is ~20x slower on CPU than the matmul form."""

        def __init__(self, i, o, k=3):
            super().__init__()
            self.k = k
            self.weight = nn.Parameter(torch.randn(o, i, k) / math.sqrt(i * k))
            self.bias = nn.Parameter(torch.zeros(o))

        def forward(self, x):
            u = nn.functional.pad(x, (self.k // 2, self.k // 2)).unfold(2, self.k, 1)   # [B, C, T, k]
            return torch.einsum("bctk,ock->bot", u, self.weight) + self.bias[:, None]

    def conv(i, o):
        return nn.Sequential(Conv(i, o), nn.BatchNorm1d(o), nn.ReLU())

    class Res(nn.Module):
        def __init__(self, c, pool):
            super().__init__()
            self.a = conv(c, c)
            self.b = nn.Sequential(Conv(c, c), nn.BatchNorm1d(c))
            self.pool = nn.AvgPool1d(2) if pool else nn.Identity()

        def forward(self, x):
            return self.pool(torch.relu(x + self.b(self.a(x))))

    class Encoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.inp = conv(MELS, width)
            self.body = nn.Sequential(*[Res(width, k < blocks - 1) for k in range(blocks)])
            self.head = nn.Sequential(nn.Linear(2 * width, 128), nn.ReLU(), nn.Linear(128, dim))

        def forward(self, x):                         # x [B, 1, MELS, T]
            h = self.body(self.inp(x[:, 0]))          # [B, C, T']
            h = torch.cat([h.mean(-1), h.std(-1)], dim=1)
            return nn.functional.normalize(self.head(h), dim=1)

    return Encoder()


class Views:
    """Batches of augmented, loudness-normalised log-mel views, per fold."""

    def __init__(self, fold, seed, exclude_menu=False):
        import numpy as np

        from learn import train as TR

        self.np = np
        self.rng = np.random.default_rng(seed)
        meta = json.loads((CACHE / "clips.json").read_text())
        self.M = np.load(CACHE / "mel.npy", mmap_mode="r")
        fold_of, _ = TR.k3_folds()
        silent = set(meta["silent_parts"])
        menu = set()
        if exclude_menu:
            menu = {f"pr12|{r['candidate']}" for r in
                    json.loads((KILL / "pr12-clean" / "index.json").read_text())["rows"]}
        ok = lambda c: (fold_of.get(c["band"], -1) != fold and c.get("part") not in silent
                        and c["setting"] not in menu and c.get("base") not in menu)
        self.clips = [c for c in meta["clips"] if ok(c)]
        assert all(fold_of.get(c["band"], -1) != fold for c in self.clips)
        # groups: a crossed block, or a panel (amp); within a group, settings x DIs
        groups = {}
        for i, c in enumerate(self.clips):
            groups.setdefault(c["group"], {}).setdefault(c["di"], {})[c["setting"]] = i
        blocks = sorted(g for g in groups if not g.startswith("panel-"))
        vrng = np.random.default_rng(12345)              # 5% of blocks for monitoring
        self.val_blocks = set(vrng.choice(blocks, max(1, len(blocks) // 20), replace=False))
        self.groups = {g: v for g, v in groups.items() if g not in self.val_blocks}
        self.val = {g: groups[g] for g in sorted(self.val_blocks)}
        self.crossed = [g for g in self.groups if not g.startswith("panel-")]
        self.panels = [g for g in self.groups if g.startswith("panel-")]
        b = np.load(CACHE / "bleed.npz", allow_pickle=True)
        self.bleed = [10 ** (m.astype(np.float32) / 10) for m, band in zip(b["mel"], b["band"])
                      if fold_of[str(band)] != fold]
        self.noise = 10 ** (np.load(CACHE / "noise_db.npy") / 10)
        _, centres = mel_matrix()
        self.lf = np.log2(np.maximum(centres, 20) / 1000)
        self.settings = sorted({c["setting"] for c in self.clips})
        self.label = {s: k for k, s in enumerate(self.settings)}
        n_cross = sum(c["kind"] == "crossed" for c in self.clips)
        print(f"fold {fold}: {len(self.clips)} clips ({n_cross} crossed), {len(self.settings)} settings, "
              f"{len(self.crossed)} blocks + {len(self.panels)} panels, {len(self.val)} val blocks, "
              f"{len(self.bleed)} bleed", flush=True)

    def view(self, i, train, crop=CROP):
        np = self.np
        c = self.clips[i]
        n = c["len"]
        if train:
            a = int(self.rng.integers(0, n - crop + 1))
        else:
            a = (n - crop) // 2
        P = 10 ** (self.M[c["off"] + a:c["off"] + a + crop].astype(np.float32).T / 10)   # [MELS, T]
        if train:
            rng = self.rng
            tilt = rng.uniform(-3, 3) * np.clip(self.lf / 3.3, -1, 1)
            fc, gb = rng.uniform(np.log2(200), np.log2(6000)), rng.uniform(-4, 4)
            bell = gb * np.exp(-0.5 * ((self.lf + np.log2(1000) - fc) / 0.5) ** 2)
            P = P * 10 ** ((tilt + bell) / 10)[:, None]
            level = P.sum(0).mean()
            if rng.random() < 0.5 and self.bleed:
                B = self.bleed[rng.integers(len(self.bleed))]
                s = int(rng.integers(0, max(1, B.shape[0] - crop)))
                seg = B[s:s + crop].T
                if seg.shape[1] == crop:
                    P = P + seg / (seg.sum(0).mean() + 1e-12) * level * 10 ** (-rng.uniform(12, 30) / 10)
            if rng.random() < 0.5:
                P = P + (self.noise / self.noise.sum() * level * 10 ** (-rng.uniform(45, 75) / 10))[:, None]
        return normalise(P)

    def batch(self, groups=6, settings=8, views=3):
        """[groups*settings*views, 1, MELS, CROP] and labels. Within a group the views
        of all settings share the same DIs, so the other settings are hard negatives."""
        np = self.np
        rng = self.rng
        xs, ys = [], []
        n_panel = min(int(rng.binomial(groups, 1 / 3)), len(self.panels))
        names = ([self.panels[k] for k in rng.permutation(len(self.panels))[:n_panel]]
                 + [self.crossed[k] for k in rng.permutation(len(self.crossed))[:groups - n_panel]])
        for name in names:                                  # groups without replacement
            G = self.groups[name]
            dis = [d for d in G if len(G[d]) >= 2]
            dis = [dis[k] for k in rng.permutation(len(dis))]
            common = None
            chosen = []
            for d in dis:                                   # DIs sharing enough settings
                s = set(G[d]) if common is None else common & set(G[d])
                if len(s) >= min(settings, 4):
                    common, chosen = s, chosen + [d]
                if len(chosen) == views:
                    break
            if len(chosen) < 2:
                continue
            common = sorted(common)
            pick = [common[k] for k in rng.permutation(len(common))[:settings]]
            for s in pick:
                for d in chosen:
                    xs.append(self.view(G[d][s], True))
                    ys.append(self.label[s])
        return np.stack(xs)[:, None], np.array(ys)


def normalise(P):
    """Loudness-normalise mel power by active-frame mean total power; dB, scaled."""
    import numpy as np

    tot = P.sum(0)
    tdb = 10 * np.log10(tot + 1e-20)
    act = tdb >= tdb.max() - 40
    level = tot[act].mean()
    db = 10 * np.log10(P / level + 1e-12)
    return ((np.maximum(db, -100) + 40) / 20).astype(np.float32)


def supcon(z, y, tau):
    import torch

    sim = z @ z.T / tau
    n = len(y)
    eye = torch.eye(n, dtype=torch.bool)
    sim = sim.masked_fill(eye, -1e9)
    pos = (y[:, None] == y[None, :]) & ~eye
    logp = sim - torch.logsumexp(sim, dim=1, keepdim=True)
    return -(logp * pos).sum(1).div(pos.sum(1).clamp(min=1)).mean()


def fit(fold, steps, seed, threads, tag, exclude_menu):
    import numpy as np
    import torch

    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    dev = torch.device("cpu")
    V = Views(fold, seed, exclude_menu)
    net = build_model().to(dev)
    print(f"parameters {sum(p.numel() for p in net.parameters())}", flush=True)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-3, total_steps=steps, pct_start=0.05)
    MODELS.mkdir(parents=True, exist_ok=True)
    t0, run = time.time(), []
    for step in range(steps):
        net.train()
        x, y = V.batch()
        z = net(torch.from_numpy(x))
        loss = supcon(z, torch.from_numpy(y), 0.1)
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        run.append(loss.item())
        if step % 100 == 0 or step == steps - 1:
            print(f"fold {fold} step {step} loss {np.mean(run[-100:]):.3f} val8 {val8(net, V):.3f} "
                  f"{time.time() - t0:.0f}s", flush=True)
    torch.save({"state": net.state_dict(), "steps": steps, "seed": seed, "fold": fold,
                "exclude_menu": exclude_menu}, MODELS / f"{tag}fold{fold}.pt")
    print(f"done in {time.time() - t0:.0f}s", flush=True)


def val8(net, V):
    """Monitoring only: in the held-back training-fold blocks, 8-way leave-one-DI-out
    identification of each setting from its other DIs' mean embedding."""
    import numpy as np
    import torch

    net.eval()
    hits = tot = 0
    with torch.no_grad():
        for g, G in V.val.items():
            dis = sorted(G)
            sets = sorted(set.intersection(*[set(G[d]) for d in dis]))
            if len(sets) < 2 or len(dis) < 2:
                continue
            X = np.stack([V.view(G[d][s], False) for d in dis for s in sets])[:, None]
            Z = net(torch.from_numpy(X)).numpy().reshape(len(dis), len(sets), -1)
            for k in range(len(dis)):
                mu = np.delete(Z, k, axis=0).mean(0)
                hits += int((np.argmax(Z[k] @ mu.T, axis=1) == np.arange(len(sets))).sum())
                tot += len(sets)
    return hits / max(tot, 1)


# --- screens ----------------------------------------------------------------------------

def load_net(fold, tag=""):
    import torch

    net = build_model()
    ck = torch.load(MODELS / f"{tag}fold{fold}.pt", map_location="cpu")
    assert ck["steps"] == STEPS and ck["seed"] == SEED and ck["fold"] == fold, {k: ck[k] for k in ("steps", "seed", "fold")}
    net.load_state_dict(ck["state"])
    net.eval()
    return net


def embed(net, x):
    """Embedding of half A (1.0–5.5 s) of a mono 48-kHz signal."""
    import torch

    d = mel_db(x[int(HALF_A[0] * SR):int(HALF_A[1] * SR)])
    with torch.no_grad():
        return net(torch.from_numpy(normalise(10 ** (d / 10)))[None, None]).numpy()[0]


def panel_embeddings(tag=""):
    """{fold: {(part, candidate): embedding}} over pr12-clean (template excluded)."""
    import numpy as np

    import hashlib

    path = ROOT / f"{tag}panel-emb.npz"
    hashes = [hashlib.sha256((MODELS / f"{tag}fold{f}.pt").read_bytes()).hexdigest() for f in range(4)]
    if path.exists():
        d = np.load(path, allow_pickle=True)
        if d["hashes"].tolist() == hashes:
            return d["emb"].item()
    rows = [r for r in json.loads((KILL / "pr12-clean" / "index.json").read_text())["rows"]
            if "file" in r and r["candidate"] != "template"]
    nets = {f: load_net(f, tag) for f in range(4)}
    out = {f: {} for f in nets}
    for r in rows:
        x = read_mono(r["file"])
        for f, net in nets.items():
            out[f][(r["part"], r["candidate"])] = embed(net, x)
    np.savez(path, emb=np.array(out, dtype=object), hashes=np.array(hashes))
    return out


def identify(tag=""):
    """Screen 1: name each K1 part's render among the 22 from other-fold parts' renders."""
    import numpy as np

    from learn import phase2 as P2
    from learn import train as TR

    ps, band, _ = P2.parts()
    fold_of, band_of = TR.k3_folds()
    silent = set(json.loads((CACHE / "clips.json").read_text())["silent_parts"])
    assert len(silent) == 8 and not silent & set(ps), silent
    E = panel_embeddings(tag)
    rr = np.load(pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/rerank/features.npz")), allow_pickle=True)
    keys = rr["keys"].tolist()
    idx = {k: i for i, k in enumerate(keys)}
    names = sorted({c for (_, c) in E[0]})
    assert len(names) == 22
    res = {"enc": [], "mel": [], "panns": []}
    for p in ps:
        f = fold_of[band[p]]
        other = sorted({q for (q, _) in E[f] if fold_of[band_of[q]] != f and q not in silent})
        assert p not in other and all(band_of[q] != band[p] for q in other)
        # encoder: cosine to the mean of normalised embeddings
        mu = np.stack([np.mean([E[f][(q, n)] for q in other], axis=0) for n in names])
        mu /= np.linalg.norm(mu, axis=1, keepdims=True)
        # baselines, as learn/rerank.py: z-scored mel (Euclidean), PANNs (cosine)
        rows = np.array([idx[f"render|{q}|{n}"] for q in other for n in names])
        mel, pan = rr["mel"], rr["panns"]
        m0, s0 = mel[rows].mean(0), mel[rows].std(0) + 1e-12
        cm = np.stack([((mel[[idx[f"render|{q}|{n}"] for q in other]].mean(0)) - m0) / s0 for n in names])
        cp = np.stack([pan[[idx[f"render|{q}|{n}"] for q in other]].mean(0) for n in names])
        for t, n in enumerate(names):
            e = E[f][(p, n)]
            d_enc = 1 - mu @ (e / np.linalg.norm(e))
            zm = (mel[idx[f"render|{p}|{n}"]] - m0) / s0
            d_mel = np.linalg.norm(cm - zm, axis=1)
            v = pan[idx[f"render|{p}|{n}"]]
            d_pan = 1 - cp @ v / (np.linalg.norm(cp, axis=1) * np.linalg.norm(v))
            for k, d in (("enc", d_enc), ("mel", d_mel), ("panns", d_pan)):
                assert np.isfinite(d).all(), (k, p, n)
                rank = int((d <= d[t]).sum()) - 1          # ties count against the true candidate
                res[k].append({"part": p, "band": band[p], "fold": f, "candidate": n, "rank": rank})
    out = {}
    for k, rows in res.items():
        r = np.array([x["rank"] for x in rows])
        bands = sorted({x["band"] for x in rows})
        per_band = [np.mean([x["rank"] == 0 for x in rows if x["band"] == b]) for b in bands]
        per_fold = {f: float(np.mean([x["rank"] == 0 for x in rows if x["fold"] == f])) for f in range(4)}
        # band-cluster bootstrap of pooled top-1
        rng = np.random.default_rng(0)
        byb = {b: [x["rank"] == 0 for x in rows if x["band"] == b] for b in bands}
        boots = []
        for _ in range(2000):
            pick = rng.choice(bands, len(bands))
            v = np.concatenate([byb[b] for b in pick])
            boots.append(v.mean())
        out[k] = {"trials": len(r), "top1": float((r == 0).mean()), "top3": float((r < 3).mean()),
                  "mean_rank": float(r.mean() + 1), "band_mean_top1": float(np.mean(per_band)),
                  "per_fold_top1": per_fold, "top1_band_bootstrap_95": [float(np.quantile(boots, 0.025)),
                                                                        float(np.quantile(boots, 0.975))]}
    out["chance"] = 1 / 22
    out["gate_top1"] = 0.30
    out["passed"] = out["enc"]["top1"] >= 0.30
    out["rows"] = res
    (ROOT / f"{tag}identify.json").write_text(json.dumps(out, indent=1))
    for k in ("enc", "mel", "panns"):
        print(k, {a: b for a, b in out[k].items()})
    print("passed", out["passed"])
    return out


def rerank(tag=""):
    """Screen 2: learn/rerank.py with the encoder's picks added (amp track and stem)."""
    import numpy as np

    from learn import phase2 as P2
    from learn import rerank as RR
    from learn import train as TR

    ps, band, _ = P2.parts()
    fold_of, band_of = TR.k3_folds()
    usable = P2.stem_usable()
    silent = set(json.loads((CACHE / "clips.json").read_text())["silent_parts"])
    keys, mel, emb = RR.features()
    pk, names = RR.picks(keys, mel, emb)
    assert set(pk["_dropped"]) == silent, (pk["_dropped"], silent)
    E = panel_embeddings(tag)
    nets = {f: load_net(f, tag) for f in range(4)}
    for p in ps:
        f = fold_of[band[p]]
        other = sorted({q for (q, _) in E[f] if fold_of[band_of[q]] != f and q not in silent})
        mu = np.stack([np.mean([E[f][(q, n)] for q in other], axis=0) for n in names])
        mu /= np.linalg.norm(mu, axis=1, keepdims=True)
        for src in ("ref", "stem"):
            if src == "stem" and p not in usable:
                continue
            e = embed(nets[f], P2.recording(p, src))
            d = 1 - mu @ (e / np.linalg.norm(e))
            pk[(p, f"enc_{src}")] = names[int(np.argmin(d))]
    RR.RERANKERS = dict(RR.RERANKERS, enc_ref=("enc", "ref"), enc_stem=("enc", "stem"))
    res = RR.score(pk, names)
    res["picks"] = {f"{k[0]}|{k[1]}": v for k, v in pk.items()
                    if isinstance(k, tuple) and k[1].startswith("enc_")}
    (ROOT / f"{tag}rerank.json").write_text(json.dumps(res, indent=1))
    for bs in P2.BAND_SETS:
        for k, v in res[bs]["summary"].items():
            if v:
                print(bs, k, round(v["band_median_log_ratio"], 3), v["parts_better"], v["parts"],
                      round(v["sign_flip_p_two_sided"], 3))
    print("gate", res["gate"])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("cache")
    f = sub.add_parser("fit")
    f.add_argument("--fold", type=int, required=True)
    f.add_argument("--steps", type=int, default=STEPS)
    f.add_argument("--seed", type=int, default=SEED)
    f.add_argument("--threads", type=int, default=4)
    f.add_argument("--exclude-menu", action="store_true")
    for name in ("identify", "rerank"):
        s = sub.add_parser(name)
        s.add_argument("--exclude-menu", action="store_true")
    a = ap.parse_args()
    if a.cmd == "cache":
        build_cache()
    elif a.cmd == "fit":
        fit(a.fold, a.steps, a.seed, a.threads, "nomenu-" if a.exclude_menu else "", a.exclude_menu)
    elif a.cmd == "identify":
        identify("nomenu-" if a.exclude_menu else "")
    else:
        rerank("nomenu-" if a.exclude_menu else "")


if __name__ == "__main__":
    main()
