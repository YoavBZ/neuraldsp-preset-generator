"""Train the POC settings model, one per K3 band fold (`docs/preset-model-poc-plan.md`).

    # once, after rendering (main .venv: needs soundfile and scipy)
    .venv/bin/python -m learn.train cache --renders ~/ndsp-presets/learn/poc/renders \\
        --cache ~/ndsp-presets/learn/poc/cache
    # per fold (a torch interpreter; the Demucs venv has torch with MPS)
    $TORCH_PY -m learn.train fit --cache ~/ndsp-presets/learn/poc/cache --fold 0 \\
        --out ~/ndsp-presets/learn/poc/models

Audio is cached at 32 kHz as int16, 6 s per clip. Features are computed on the device:
the 4-s crop is loudness-normalised over its active frames, then a 1024-point STFT with
a 10-ms hop and 128 mel bands from 30 Hz to 15.5 kHz in dB. There is no per-frequency
normalisation, since the EQ is a label.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import pr12  # noqa: E402

SR = 32000
CLIP = 6 * SR
CROP = 4 * SR
N_FFT, HOP, MELS = 1024, 320, 128
CROPS = pathlib.Path(os.path.expanduser("~/ndsp-presets/references/validation-crops"))
FOLD_SEED = 20261003
PANEL_INDEX = pathlib.Path(os.path.expanduser("~/ndsp-presets/runs/kill/pr12-clean/index.json"))


# --- folds: K3's, reproduced --------------------------------------------------

def k3_folds():
    """(band -> fold, part -> band), exactly as `scripts/kill_test_k3.py` draws them."""
    catalog = json.loads((PLUGIN_ROOT / "docs" / "validation-datasets.json").read_text())
    meta = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            meta[slug] = s.get("group") or f"{s['source']}/{s['song']}"
    index = json.loads(PANEL_INDEX.read_text())
    parts = sorted({r["part"] for r in index["rows"] if "file" in r})
    bands = sorted({meta[p] for p in parts})
    rng = random.Random(FOLD_SEED)
    rng.shuffle(bands)
    return {b: i % 4 for i, b in enumerate(bands)}, {p: meta[p] for p in parts}


# --- cache --------------------------------------------------------------------

def to32k(x, sr):
    import numpy as np
    from scipy.signal import resample_poly

    g = math.gcd(SR, sr)
    return resample_poly(x, SR // g, sr // g).astype(np.float32)


def build_cache(renders: pathlib.Path, cache: pathlib.Path):
    import numpy as np
    import soundfile as sf

    rows = []
    for f in sorted(renders.glob("index-w*.jsonl")):
        rows += [json.loads(line) for line in f.read_text().splitlines() if line]
    rows.sort(key=lambda r: r["id"])
    # Excluded before any training (review, 2026-10-06): clips whose render was
    # numerical noise (peak-normalisation gain above 60 dB: a pedal or volume at 0),
    # DI windows quieter than -40 LUFS, and settings written with an exponent, which the
    # plugin may not have parsed.
    def ok(r):
        if 20 * math.log10(r["gain"]) > 60 or r["lufs"] < -40:
            return False
        return not any("e" in f"{v:.6g}" for v in r["sample"].values()
                       if isinstance(v, float))
    dropped = [r["id"] for r in rows if not ok(r)]
    rows = [r for r in rows if ok(r)]
    print(f"dropped {len(dropped)} rows", flush=True)
    cache.mkdir(parents=True, exist_ok=True)
    X = np.lib.format.open_memmap(cache / "audio.npy", mode="w+", dtype=np.int16,
                                  shape=(len(rows), CLIP))
    cont, mask, binary, bmask, cat, cmask = [], [], [], [], [], []
    for i, r in enumerate(rows):
        y, sr = sf.read(str(renders / f"{r['id']}.flac"), dtype="float32")
        y = to32k(y, sr)[:CLIP]
        X[i, :len(y)] = np.clip(y * 32767, -32768, 32767).astype(np.int16)
        c, m, b, bm, k, km = pr12.encode(r["sample"], r["effective_drive"])
        cont.append(c); mask.append(m); binary.append(b); bmask.append(bm)
        cat.append(k); cmask.append(km)
        if i % 2000 == 0:
            print(f"cached {i}/{len(rows)}", flush=True)
    X.flush()
    np.savez(cache / "labels.npz", cont=np.array(cont, np.float32), mask=np.array(mask, np.float32),
             binary=np.array(binary, np.float32), bmask=np.array(bmask, np.float32), cat=np.array(cat, np.int64),
             cmask=np.array(cmask, np.float32))
    (cache / "dropped.json").write_text(json.dumps(dropped))
    (cache / "meta.json").write_text(json.dumps(
        [{k: r[k] for k in ("id", "band", "source", "effective_drive", "lufs")} for r in rows]))
    # Bleed sources: the instrumental backing of every development crop, by band.
    fold_of, band_of = k3_folds()
    bleed = []
    for part, band in sorted(band_of.items()):
        f = CROPS / part / "backing_instrumental.wav"
        if f.exists():
            y, sr = sf.read(str(f), dtype="float32", always_2d=True)
            bleed.append({"part": part, "band": band,
                          "audio": to32k(y.mean(axis=1), sr)[:10 * SR].tolist()})
    (cache / "bleed.json").write_text(json.dumps(bleed))
    print(f"cached {len(rows)} clips, {len(bleed)} bleed sources")


# --- features and model ---------------------------------------------------------

def mel_matrix():
    import numpy as np

    def hz_to_mel(f):
        return 2595 * np.log10(1 + f / 700)

    def mel_to_hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    edges = mel_to_hz(np.linspace(hz_to_mel(30.0), hz_to_mel(15500.0), MELS + 2))
    m = np.zeros((MELS, len(freqs)), np.float32)
    for b in range(MELS):
        lo, c, hi = edges[b], edges[b + 1], edges[b + 2]
        up = (freqs - lo) / max(c - lo, 1e-9)
        down = (hi - freqs) / max(hi - c, 1e-9)
        m[b] = np.clip(np.minimum(up, down), 0, None)
    return m


class Frontend:
    def __init__(self, device):
        import torch

        self.torch = torch
        self.device = device
        self.mel = torch.tensor(mel_matrix(), device=device)
        self.window = torch.hann_window(N_FFT, device=device)

    def __call__(self, wave):
        """wave [B, T] float → [B, 1, MELS, frames] dB, loudness-normalised."""
        torch = self.torch
        frames = wave.unfold(1, 1024, 320)
        e = (frames ** 2).mean(-1) + 1e-10
        edb = 10 * torch.log10(e)
        active = edb >= (edb.max(dim=1, keepdim=True).values - 40)
        level = (e * active).sum(1) / active.sum(1).clamp(min=1)
        wave = wave / torch.sqrt(level).unsqueeze(1) * 0.1           # active RMS → −20 dBFS
        spec = torch.stft(wave, N_FFT, HOP, window=self.window, return_complex=True).abs() ** 2
        mel = torch.einsum("mf,bft->bmt", self.mel, spec)
        db = 10 * torch.log10(mel + 1e-10)
        return ((db.clamp(min=-100) + 40) / 20).unsqueeze(1)


def build_model():
    import torch.nn as nn

    class Block(nn.Module):
        def __init__(self, i, o):
            super().__init__()
            self.net = nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(),
                                     nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU())
            self.skip = nn.Conv2d(i, o, 1)
            self.pool = nn.AvgPool2d(2)

        def forward(self, x):
            return self.pool(self.net(x) + self.skip(x))

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.body = nn.Sequential(Block(1, 32), Block(32, 64), Block(64, 128), Block(128, 192))
            d = 192 * (MELS // 16) * 2
            self.trunk = nn.Sequential(nn.Linear(d, 512), nn.ReLU(), nn.Dropout(0.2),
                                       nn.Linear(512, 512), nn.ReLU())
            self.cont = nn.Linear(512, len(pr12.CONTINUOUS))
            self.binary = nn.Linear(512, len(pr12.BINARY))
            self.cat = nn.ModuleList([nn.Linear(512, n) for _, n, _ in pr12.CATEGORICAL])

        def forward(self, x):
            import torch

            h = self.body(x)                                   # [B, C, F, T]
            h = torch.cat([h.mean(-1), h.std(-1)], dim=1).flatten(1)
            h = self.trunk(h)
            return (torch.sigmoid(self.cont(h)), self.binary(h), [c(h) for c in self.cat])

    return Net()


# --- training -------------------------------------------------------------------

def fit(cache: pathlib.Path, fold: int, out: pathlib.Path, epochs: int, seed: int, bleed_on: bool):
    import numpy as np
    import torch
    import torch.nn.functional as F

    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    X = np.load(cache / "audio.npy", mmap_mode="r")
    L = np.load(cache / "labels.npz")
    meta = json.loads((cache / "meta.json").read_text())
    fold_of, _ = k3_folds()
    clip_fold = np.array([fold_of.get(m["band"], -1) for m in meta])   # -1: Guitar-TECHS
    train_idx = np.where(clip_fold != fold)[0]
    val_idx = np.where(clip_fold == fold)[0]
    bleed = [np.array(b["audio"], np.float32) for b in json.loads((cache / "bleed.json").read_text())
             if fold_of[b["band"]] != fold]
    print(f"fold {fold}: train {len(train_idx)} val {len(val_idx)} bleed {len(bleed)}", flush=True)

    labels = {k: torch.tensor(L[k]) for k in ("cont", "mask", "binary", "bmask", "cat", "cmask")}
    frontend = Frontend(device)
    model = build_model().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    batch = min(64, len(train_idx))
    steps = epochs * (len(train_idx) // batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-3, total_steps=steps)

    def make_batch(idx, train):
        waves = np.zeros((len(idx), CROP), np.float32)
        for j, i in enumerate(idx):
            a = rng.integers(0, CLIP - CROP + 1) if train else (CLIP - CROP) // 2
            x = X[i, a:a + CROP].astype(np.float32) / 32767
            if train and bleed_on:
                if rng.random() < 0.5:
                    b = bleed[rng.integers(len(bleed))]
                    s = rng.integers(0, len(b) - CROP + 1)
                    seg = b[s:s + CROP]
                    rel = 10 ** (-rng.uniform(12, 30) / 20)
                    seg = seg / (seg.std() + 1e-9) * x.std() * rel
                    x = x + seg
                if rng.random() < 0.5:
                    x = x + rng.standard_normal(CROP).astype(np.float32) * x.std() * 10 ** (-rng.uniform(45, 75) / 20)
            waves[j] = x
        w = torch.tensor(waves, device=device)
        lab = {k: v[idx].to(device) for k, v in labels.items()}
        return w, lab

    def loss_fn(outputs, lab):
        cont, binary, cats = outputs
        lc = (F.smooth_l1_loss(cont, lab["cont"], reduction="none", beta=0.05) * lab["mask"]).sum() \
            / lab["mask"].sum().clamp(min=1)
        lb = (F.binary_cross_entropy_with_logits(binary, lab["binary"], reduction="none")
              * lab["bmask"]).sum() / lab["bmask"].sum().clamp(min=1)
        lk = sum((F.cross_entropy(c, lab["cat"][:, n], reduction="none") * lab["cmask"][:, n]).mean()
                 for n, c in enumerate(cats))
        return 4 * lc + lb + 0.5 * lk, (lc.item(), lb.item(), float(lk.detach()))

    out.mkdir(parents=True, exist_ok=True)
    step = 0
    for epoch in range(epochs):
        model.train()
        perm = rng.permutation(train_idx)
        tot = np.zeros(3)
        for s in range(len(perm) // batch):
            idx = np.sort(perm[s * batch:(s + 1) * batch])
            w, lab = make_batch(idx, True)
            loss, parts = loss_fn(model(frontend(w)), lab)
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            tot += parts
            step += 1
        model.eval()
        with torch.no_grad():
            vt = np.zeros(3)
            n = 0
            for s in range(0, min(len(val_idx), 2048), 128):
                idx = np.sort(val_idx[s:s + 128])
                w, lab = make_batch(idx, False)
                _, parts = loss_fn(model(frontend(w)), lab)
                vt += parts
                n += 1
        print(f"fold {fold} epoch {epoch}: train {np.round(tot / (len(perm) // batch), 4)} "
              f"val {np.round(vt / max(n, 1), 4)}", flush=True)
    torch.save(model.state_dict(), out / f"fold{fold}.pt")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cache")
    c.add_argument("--renders", type=pathlib.Path, required=True)
    c.add_argument("--cache", type=pathlib.Path, required=True)
    f = sub.add_parser("fit")
    f.add_argument("--cache", type=pathlib.Path, required=True)
    f.add_argument("--fold", type=int, required=True)
    f.add_argument("--out", type=pathlib.Path, required=True)
    f.add_argument("--epochs", type=int, default=30)
    f.add_argument("--seed", type=int, default=0)
    f.add_argument("--no-bleed", action="store_true")
    args = ap.parse_args()
    if args.cmd == "cache":
        build_cache(args.renders.expanduser(), args.cache.expanduser())
    else:
        fit(args.cache.expanduser(), args.fold, args.out.expanduser(), args.epochs, args.seed,
            not args.no_bleed)


if __name__ == "__main__":
    main()
