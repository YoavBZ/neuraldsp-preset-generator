"""Rebuild a guitar's DI from its recorded (amped) sound (`docs/di-recovery-plan.md`).

The target is not the player's own DI but that DI at the average guitar's long-term
balance, frozen per K3 fold from the other folds' DIs. A song cannot reveal the original
guitar's balance, and the average-guitar measure doesn't ask for it.

    # cache (main .venv)
    .venv/bin/python -m learn.direc cache --renders ~/ndsp-presets/learn/poc/renders \\
        --cache ~/ndsp-presets/learn/direc/cache
    # train one fold (learn venv: torch)
    $TORCH_PY -m learn.direc fit --cache ~/ndsp-presets/learn/direc/cache --fold 0 \\
        --out ~/ndsp-presets/learn/direc/models --minutes 60
    # rebuild a DI
    $TORCH_PY -m learn.direc rebuild --model .../fold0.pt --input x.wav --output di.wav

Everything is 48 kHz mono. Input and target are each set to a fixed RMS. Level is set
by rule afterwards: a rebuilt DI is played at the assumed −22.9 LUFS.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

SR = 48000
CLIP = 6 * SR
CROP = 3 * SR
SPEC_N = 4096                      # resolution of the stored long-term spectra
CROPS = pathlib.Path(os.path.expanduser("~/ndsp-presets/references/validation-crops"))


# --- cache ------------------------------------------------------------------------

def build_cache(renders: pathlib.Path, cache: pathlib.Path):
    import numpy as np
    import soundfile as sf

    from analysis import io
    from learn.di_robustness import smoothed_spectrum

    meta_src = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/poc/cache/meta.json"))
    meta = json.loads(meta_src.read_text())            # the POC's kept clips, in order
    rows = {}
    for f in renders.glob("index-w*.jsonl"):
        for line in f.read_text().splitlines():
            if line:
                r = json.loads(line)
                rows[r["id"]] = r
    cache.mkdir(parents=True, exist_ok=True)
    X = np.lib.format.open_memmap(cache / "input.npy", mode="w+", dtype=np.int16, shape=(len(meta), CLIP))
    Y = np.lib.format.open_memmap(cache / "di.npy", mode="w+", dtype=np.int16, shape=(len(meta), CLIP))
    S = np.zeros((len(meta), SPEC_N // 2 + 1), np.float32)
    order = sorted(range(len(meta)), key=lambda i: (rows[meta[i]["id"]]["file"], i))
    current, x = None, None
    for n, i in enumerate(order):
        r = rows[meta[i]["id"]]
        if r["file"] != current:
            current, x = r["file"], np.asarray(io.load(r["file"]).mono(), np.float32)
        a = int((r["start_s"] + 2.0) * SR)
        di = x[a:a + CLIP]
        y, _ = sf.read(str(renders / f"{r['id']}.flac"), dtype="float32")
        X[i, :len(y)] = np.clip(y / (np.abs(y).max() + 1e-9) * 0.9 * 32767, -32767, 32767)
        Y[i, :len(di)] = np.clip(di / (np.abs(di).max() + 1e-9) * 0.9 * 32767, -32767, 32767)
        S[i] = smoothed_spectrum(di.astype(np.float64))
        if n % 2000 == 0:
            print(f"cached {n}/{len(meta)}", flush=True)
    X.flush(); Y.flush()
    np.save(cache / "di_spectrum.npy", S)
    (cache / "meta.json").write_text(json.dumps(meta))
    print(f"cached {len(meta)} pairs")


def fold_average(cache: pathlib.Path, fold: int):
    """The average guitar balance (dB, mean-removed, SPEC_N bins) over DIs from bands
    outside `fold`; frozen to a file the measure and the target share."""
    import numpy as np

    from learn import train as TR

    path = cache / f"average-fold{fold}.npy"
    if path.exists():
        return np.load(path)
    S = np.load(cache / "di_spectrum.npy")
    meta = json.loads((cache / "meta.json").read_text())
    fold_of, _ = TR.k3_folds()
    keep = np.array([fold_of.get(m["band"], -1) != fold for m in meta])
    s = S[keep]
    avg = 10 * np.log10((10 ** (s / 10)).mean(0) + 1e-20)   # power average
    avg = avg - avg.mean()
    np.save(path, avg)
    return avg


# --- model --------------------------------------------------------------------------

def build_model(channels=(32, 64, 128, 256, 512), lstm=256):
    import torch
    import torch.nn as nn

    class Net(nn.Module):
        """Wave U-Net in the style of Demucs v2: kernel 8, stride 4, GLU, a BLSTM at the
        bottom, skip connections; same-length output (input padded to a multiple of 4^5)."""

        def __init__(self):
            super().__init__()
            self.enc, self.dec = nn.ModuleList(), nn.ModuleList()
            cin = 1
            for c in channels:
                self.enc.append(nn.Sequential(nn.Conv1d(cin, c, 8, 4, padding=2), nn.GELU(),
                                              nn.Conv1d(c, 2 * c, 1), nn.GLU(dim=1)))
                cin = c
            self.lstm = nn.LSTM(cin, lstm, num_layers=2, bidirectional=True, batch_first=True)
            self.proj = nn.Linear(2 * lstm, cin)
            outs = list(channels[:-1])[::-1] + [1]
            for c, o in zip(channels[::-1], outs):
                last = o == 1
                self.dec.append(nn.Sequential(nn.Conv1d(c, 2 * c, 3, padding=1), nn.GLU(dim=1),
                                              nn.ConvTranspose1d(c, o, 8, 4, padding=2),
                                              *( [] if last else [nn.GELU()])))

        def forward(self, x):
            n = x.shape[-1]
            m = 4 ** len(self.enc)
            pad = (-n) % m
            x = torch.nn.functional.pad(x, (0, pad))
            skips = []
            h = x
            for e in self.enc:
                h = e(h)
                skips.append(h)
            z = self.lstm(h.transpose(1, 2))[0]
            h = h + self.proj(z).transpose(1, 2)
            for d in self.dec:
                s = skips.pop()
                h = d(h + s[..., :h.shape[-1]])
            return h[..., :n]

    return Net()


def mrstft(a, b, ffts=(256, 512, 1024, 2048, 4096)):
    import torch

    loss = 0.0
    for n in ffts:
        w = torch.hann_window(n, device=a.device)
        A = torch.stft(a, n, n // 4, window=w, return_complex=True).abs() + 1e-6
        B = torch.stft(b, n, n // 4, window=w, return_complex=True).abs() + 1e-6
        loss = loss + (A - B).norm() / (B.norm() + 1e-6) + (A.log() - B.log()).abs().mean()
    return loss / len(ffts)


# --- training -----------------------------------------------------------------------

def fit(cache, fold, out, minutes, seed, batch=12):
    import numpy as np
    import torch

    from learn import train as TR

    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    X = np.load(cache / "input.npy", mmap_mode="r")
    Y = np.load(cache / "di.npy", mmap_mode="r")
    S = np.load(cache / "di_spectrum.npy")
    meta = json.loads((cache / "meta.json").read_text())
    fold_of, band_of = TR.k3_folds()
    f = np.array([fold_of.get(m["band"], -1) for m in meta])
    tr, va = np.where(f != fold)[0], np.where(f == fold)[0]
    avg = fold_average(cache, fold)
    freqs = np.fft.rfftfreq(SPEC_N, 1 / SR)
    cfreq = np.fft.rfftfreq(CLIP, 1 / SR)
    # bleed: instrumental backings of training-fold development crops
    import soundfile as sf
    bleed = []
    for part, b in band_of.items():
        if fold_of[b] != fold and (CROPS / part / "backing_instrumental.wav").exists():
            y, _ = sf.read(str(CROPS / part / "backing_instrumental.wav"), dtype="float32", always_2d=True)
            bleed.append(y.mean(1))
    print(f"fold {fold}: train {len(tr)} val {len(va)} bleed {len(bleed)}", flush=True)

    def eq_curve(gain_bins):
        return np.interp(cfreq, freqs, gain_bins)

    def make(idx, train):
        xs, ys = [], []
        for i in idx:
            x = X[i].astype(np.float32) / 32767
            y = Y[i].astype(np.float32) / 32767
            own = S[i] - S[i].mean()
            g = np.clip(avg - own, -15, 15)
            Yf = np.fft.rfft(y) * 10 ** (eq_curve(g) / 20)
            y = np.fft.irfft(Yf, CLIP).astype(np.float32)
            if train:
                lf = np.log2(np.maximum(cfreq, 20) / 1000)
                tilt = rng.uniform(-3, 3) * np.clip(lf / 3.3, -1, 1)
                fc, gb = rng.uniform(np.log2(200), np.log2(6000)), rng.uniform(-4, 4)
                bell = gb * np.exp(-0.5 * ((np.log2(np.maximum(cfreq, 20)) - fc) / 0.5) ** 2)
                x = np.fft.irfft(np.fft.rfft(x) * 10 ** ((tilt + bell) / 20), CLIP).astype(np.float32)
                if rng.random() < 0.5 and bleed:
                    b = bleed[rng.integers(len(bleed))]
                    s = rng.integers(0, max(1, len(b) - CLIP))
                    seg = np.zeros(CLIP, np.float32)
                    seg[:len(b[s:s + CLIP])] = b[s:s + CLIP]
                    x = x + seg / (seg.std() + 1e-9) * x.std() * 10 ** (-rng.uniform(12, 30) / 20)
                if rng.random() < 0.5:
                    x = x + rng.standard_normal(CLIP).astype(np.float32) * x.std() * 10 ** (-rng.uniform(45, 75) / 20)
                a = rng.integers(0, CLIP - CROP)
            else:
                a = (CLIP - CROP) // 2
            x, y = x[a:a + CROP], y[a:a + CROP]
            xs.append(x / (x.std() + 1e-9) * 0.1)
            ys.append(y / (y.std() + 1e-9) * 0.1)
        return (torch.tensor(np.stack(xs), device=dev).unsqueeze(1),
                torch.tensor(np.stack(ys), device=dev).unsqueeze(1))

    net = build_model().to(dev)
    print(f"parameters {sum(p.numel() for p in net.parameters()) / 1e6:.1f}M", flush=True)
    opt = torch.optim.AdamW(net.parameters(), lr=3e-4, weight_decay=1e-5)
    out.mkdir(parents=True, exist_ok=True)
    t0, step = time.time(), 0
    vidx = rng.choice(va, min(96, len(va)), replace=False)
    while time.time() - t0 < minutes * 60:
        idx = rng.choice(tr, batch, replace=False)
        x, y = make(idx, True)
        p = net(x)
        loss = 100 * (p - y).abs().mean() + mrstft(p.squeeze(1), y.squeeze(1))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 5.0)
        opt.step()
        step += 1
        if step % 200 == 0:
            net.eval()
            with torch.no_grad():
                vl, base = 0.0, 0.0
                for s in range(0, len(vidx), batch):
                    vx, vy = make(vidx[s:s + batch], False)
                    vp = net(vx)
                    vl += float(100 * (vp - vy).abs().mean() + mrstft(vp.squeeze(1), vy.squeeze(1)))
                    base += float(100 * (vx - vy).abs().mean() + mrstft(vx.squeeze(1), vy.squeeze(1)))
            net.train()
            el = time.time() - t0
            print(f"fold {fold} step {step} {el / 60:.1f} min ({step / el:.2f} it/s) train {float(loss):.3f} "
                  f"val {vl:.3f} (input-as-DI {base:.3f})", flush=True)
            torch.save(net.state_dict(), out / f"fold{fold}.pt")
    torch.save(net.state_dict(), out / f"fold{fold}.pt")


def rebuild(net, x, device=None, window=6 * SR, hop=5 * SR):
    """Rebuilt DI for a whole mono 48-kHz signal: overlapping windows, crossfaded."""
    import numpy as np
    import torch

    device = device or next(net.parameters()).device
    n = len(x)
    out = np.zeros(n, np.float32)
    wsum = np.zeros(n, np.float32)
    fade = np.ones(window, np.float32)
    ov = window - hop
    fade[:ov] = np.linspace(0, 1, ov)
    fade[-ov:] = np.linspace(1, 0, ov)
    starts = list(range(0, max(1, n - window + 1), hop))
    if starts[-1] + window < n:
        starts.append(max(0, n - window))
    with torch.no_grad():
        for s in starts:
            seg = x[s:s + window].astype(np.float32)
            sc = seg.std() + 1e-9
            t = torch.tensor(seg / sc * 0.1, device=device)[None, None]
            y = net(t)[0, 0].cpu().numpy() / 0.1 * sc
            f = fade[:len(seg)].copy()
            if s == 0:
                f[:ov] = 1
            if s + window >= n:
                f[-min(ov, len(seg)):] = 1
            out[s:s + len(seg)] += y * f
            wsum[s:s + len(seg)] += f
    return out / np.maximum(wsum, 1e-6)


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
    f.add_argument("--minutes", type=float, default=60)
    f.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    if args.cmd == "cache":
        build_cache(args.renders.expanduser(), args.cache.expanduser())
    else:
        fit(args.cache.expanduser(), args.fold, args.out.expanduser(), args.minutes, args.seed)


if __name__ == "__main__":
    main()
