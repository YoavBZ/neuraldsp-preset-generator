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


def build_pair_cache(pairs: pathlib.Path, cache: pathlib.Path):
    """The same cache layout from a `learn/render_pairs.py` folder (FLAC out + DI)."""
    import numpy as np
    import soundfile as sf

    from learn.di_robustness import smoothed_spectrum

    rows = []
    for f in sorted(pairs.glob("index-w*.jsonl")):
        rows += [json.loads(line) for line in f.read_text().splitlines() if line]
    rows.sort(key=lambda r: r["id"])
    rows = [r for r in rows if r["lufs"] >= -40]
    cache.mkdir(parents=True, exist_ok=True)
    X = np.lib.format.open_memmap(cache / "input.npy", mode="w+", dtype=np.int16, shape=(len(rows), CLIP))
    Y = np.lib.format.open_memmap(cache / "di.npy", mode="w+", dtype=np.int16, shape=(len(rows), CLIP))
    S = np.zeros((len(rows), SPEC_N // 2 + 1), np.float32)
    for i, r in enumerate(rows):
        x, _ = sf.read(str(pairs / f"{r['id']}-out.flac"), dtype="float32")
        y, _ = sf.read(str(pairs / f"{r['id']}-di.flac"), dtype="float32")
        X[i, :len(x)] = np.clip(x * 32767, -32767, 32767)
        Y[i, :len(y)] = np.clip(y * 32767, -32767, 32767)
        S[i] = smoothed_spectrum(y.astype(np.float64))
        if i % 2000 == 0:
            print(f"cached {i}/{len(rows)}", flush=True)
    X.flush(); Y.flush()
    np.save(cache / "di_spectrum.npy", S)
    (cache / "meta.json").write_text(json.dumps(rows))
    print(f"cached {len(rows)} pairs from {pairs}")


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

def build_model(channels=(32, 64, 128, 256, 512), lstm=256, norm=False, open_bottom=False):
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
            # A dilated-conv bottleneck (about ±0.3 s at this depth). An LSTM here trained
            # stably on CPU but diverged on MPS (measured 2026-10-06).
            # `norm` (v3, docs/di-network-v3-plan.md): without it the residual sum grew to
            # thousands and saturated dec.0's GLU gate shut, killing the bottom levels (86% of
            # the weights) in every network trained before 2026-10-10. Pre-norm keeps it bounded.
            self.mid = nn.ModuleList([nn.Sequential(*([nn.GroupNorm(1, cin)] if norm else []),
                                                    nn.Conv1d(cin, cin, 3, padding=d, dilation=d),
                                                    nn.GELU(), nn.Conv1d(cin, cin, 1))
                                      for d in (1, 3, 9, 27)])
            if norm:
                for block in self.mid:
                    with torch.no_grad():
                        block[-1].weight.mul_(0.1)
            outs = list(channels[:-1])[::-1] + [1]
            for k, (c, o) in enumerate(zip(channels[::-1], outs)):
                last = o == 1
                # `open_bottom` (v3b): the deepest level's GLU gate shut in training even with
                # `norm` (2% open by step 1,000); a GELU there cannot gate the path off.
                gate = ([nn.Conv1d(c, c, 3, padding=1), nn.GELU()] if open_bottom and k == 0
                        else [nn.Conv1d(c, 2 * c, 3, padding=1), nn.GLU(dim=1)])
                self.dec.append(nn.Sequential(*gate,
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
            for block in self.mid:
                h = h + block(h)
            for d in self.dec:
                s = skips.pop()
                h = d(h + s[..., :h.shape[-1]])
            return h[..., :n]

    return Net()


def complex_stft_loss(a, b, ffts=(512, 1024, 2048), power=0.3):
    """Phase-aware: L1 between power-law-compressed complex STFTs (magnitude^0.3 with the
    original phase), averaged over resolutions. Plain magnitude losses ignore phase."""
    import torch

    total = 0.0
    for n in ffts:
        w = torch.hann_window(n, device=a.device)
        A = torch.view_as_real(torch.stft(a, n, n // 4, window=w, return_complex=True))
        B = torch.view_as_real(torch.stft(b, n, n // 4, window=w, return_complex=True))
        # |z| from real parts with a floor: complex abs has an undefined gradient at 0,
        # which silent stretches reach (non-finite from step 31 on MPS, 2026-10-10).
        ma = torch.sqrt((A ** 2).sum(-1, keepdim=True) + 1e-4)
        mb = torch.sqrt((B ** 2).sum(-1, keepdim=True) + 1e-4)
        total = total + (A * ma ** (power - 1) - B * mb ** (power - 1)).abs().mean()
    return total / len(ffts)


def neg_si_sdr(a, b, eps=1e-8):
    """Negative scale-invariant SDR (dB), averaged over the batch."""
    import torch

    a = a - a.mean(-1, keepdim=True)
    b = b - b.mean(-1, keepdim=True)
    s = (a * b).sum(-1, keepdim=True) / ((b * b).sum(-1, keepdim=True) + eps) * b
    sdr = 10 * torch.log10((s * s).sum(-1) / (((a - s) ** 2).sum(-1) + eps) + eps)
    return -sdr.clamp(-50.0, 50.0).mean()           # a near-silent target can't blow it up


def training_loss(p, y, kind="default"):
    """`default`: 100·L1 + MR-STFT magnitude, as trained so far. `phase`
    (docs/di-loss-plan.md): plus a compressed complex-STFT term and SI-SDR, which keep
    the waveform the default loss lets drift."""
    loss = 100 * (p - y).abs().mean() + mrstft(p.squeeze(1), y.squeeze(1))
    if kind == "phase":
        loss = loss + PHASE_WEIGHTS[0] * complex_stft_loss(p.squeeze(1), y.squeeze(1)) \
            + PHASE_WEIGHTS[1] * neg_si_sdr(p.squeeze(1), y.squeeze(1))
    return loss


PHASE_WEIGHTS = (10.0, 0.5)              # set so each term is about 2 of a ~8 total (measured)


def load_model(path, device="cpu"):
    """A saved network, with the architecture its weights imply."""
    import torch

    state = torch.load(path, map_location=device)
    net = build_model(norm=state["mid.0.0.weight"].dim() == 1,
                      open_bottom=state["dec.0.0.weight"].shape[0] == state["dec.0.0.weight"].shape[1])
    net.load_state_dict(state)
    return net


def gate_open(net, x):
    """Fraction of dec.0's gate above 1e-3 on `x` (0 means the bottom levels are dead); with
    an open bottom, the fraction of its GELU outputs above 1e-3 in size."""
    import torch

    seen = {}
    h = net.dec[0][0].register_forward_hook(lambda m, i, o: seen.update(o=o.detach()))
    with torch.no_grad():
        net(x)
    h.remove()
    o = seen["o"]
    if not isinstance(net.dec[0][1], torch.nn.GLU):
        return float((torch.nn.functional.gelu(o).abs() > 1e-3).float().mean())
    c = o.shape[1] // 2
    return float((torch.sigmoid(o[:, c:]) > 1e-3).float().mean())


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

def fit(cache, fold, out, minutes, seed, batch=12, log_every=200, resume=None, lr=3e-4, lr_end=None,
        extra=None, norm=False, open_bottom=False, loss_kind="default"):
    import numpy as np
    import torch

    from learn import train as TR

    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    dev = torch.device(os.environ.get("DIREC_DEVICE") or ("mps" if torch.backends.mps.is_available() else "cpu"))
    # The first cache holds the fold's frozen average; extra caches add pairs.
    caches = [cache] + list(extra or [])
    Xs = [np.load(c / "input.npy", mmap_mode="r") for c in caches]
    Ys = [np.load(c / "di.npy", mmap_mode="r") for c in caches]
    S = np.concatenate([np.load(c / "di_spectrum.npy") for c in caches])
    meta = [m for c in caches for m in json.loads((c / "meta.json").read_text())]
    where = [(k, j) for k, c in enumerate(Xs) for j in range(len(c))]

    class _Rows:
        def __init__(self, arrays):
            self.arrays = arrays

        def __getitem__(self, i):
            k, j = where[i]
            return self.arrays[k][j]

    X, Y = _Rows(Xs), _Rows(Ys)
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

    net = build_model(norm=norm, open_bottom=open_bottom).to(dev)
    if resume:
        net.load_state_dict(torch.load(resume, map_location=dev))
        print(f"resumed from {resume}", flush=True)
    print(f"parameters {sum(p.numel() for p in net.parameters()) / 1e6:.1f}M", flush=True)
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-5)
    out.mkdir(parents=True, exist_ok=True)
    t0, step, skipped, streak, recoveries = time.time(), 0, 0, 0, 0
    window = []
    vidx = rng.choice(va, min(96, len(va)), replace=False)
    while time.time() - t0 < minutes * 60:
        if lr_end is not None:          # cosine decay over the run's wall-clock budget
            frac = min(1.0, (time.time() - t0) / (minutes * 60))
            for g in opt.param_groups:
                g["lr"] = lr_end + 0.5 * (lr - lr_end) * (1 + math.cos(math.pi * frac))
        idx = rng.choice(tr, batch, replace=False)
        x, y = make(idx, True)
        p = net(x)
        loss = training_loss(p, y, loss_kind)
        opt.zero_grad()
        loss.backward()
        # torch's clip_grad_norm_ produces NaN on MPS (2.8 and 2.14, measured); clip by hand
        # and skip a step whose gradient is not finite.
        grads = [q.grad for q in net.parameters() if q.grad is not None]
        total = torch.sqrt(sum((g.detach() ** 2).sum() for g in grads))
        window.append(not bool(torch.isfinite(total)))
        if len(window) > 200:
            window.pop(0)
        if len(window) == 200 and sum(window) > 40:
            # Scattered non-finite steps (more than 20% of the last 200) also count as a
            # failure: fold 2 lost half its updates this way on 2026-10-07 without one streak
            # of 25. Force the recovery below.
            streak = 25
            window.clear()
        if not torch.isfinite(total) or streak >= 25:
            skipped += 1
            streak += 1
            if os.environ.get("DIREC_DEBUG"):
                bad = [n for n, q in net.named_parameters() if q.grad is not None and not torch.isfinite(q.grad).all()]
                with open(out / "nonfinite.jsonl", "a") as fh:
                    fh.write(json.dumps({"step": step, "idx": [int(i) for i in idx],
                                         "loss": float(loss.detach()), "params": bad[:5],
                                         "pred_finite": bool(torch.isfinite(p).all()),
                                         "x_max": float(x.abs().max()), "y_max": float(y.abs().max())}) + "\n")
            if streak >= 25:
                # MPS sometimes falls into persistent non-finite gradients (measured
                # 2026-10-07; the same run is clean on CPU and when restarted). Reload the
                # last good weights, start a fresh optimiser, and carry on.
                ckpt = out / f"fold{fold}.pt"
                state = torch.load(ckpt, map_location=dev) if ckpt.exists() else (
                    torch.load(resume, map_location=dev) if resume else None)
                if state is not None:
                    net.load_state_dict(state)
                opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-5)
                recoveries += 1
                streak = 0
                print(f"fold {fold} recovery {recoveries} at step {step}", flush=True)
                if recoveries > 20:
                    raise RuntimeError("training keeps producing non-finite gradients")
            continue
        streak = 0
        if total > 5.0:
            for g in grads:
                g.mul_(5.0 / total)
        opt.step()
        step += 1
        if step % log_every == 0:
            net.eval()
            with torch.no_grad():
                vl, base = 0.0, 0.0
                for s in range(0, len(vidx), batch):
                    vx, vy = make(vidx[s:s + batch], False)
                    vp = net(vx)
                    vl += float(100 * (vp - vy).abs().mean() + mrstft(vp.squeeze(1), vy.squeeze(1)))
                    base += float(100 * (vx - vy).abs().mean() + mrstft(vx.squeeze(1), vy.squeeze(1)))
            gate = gate_open(net, vx)
            net.train()
            el = time.time() - t0
            print(f"fold {fold} step {step} {el / 60:.1f} min ({step / el:.2f} it/s) train {float(loss.detach()):.3f} "
                  f"val {vl:.3f} (input-as-DI {base:.3f}) skipped {skipped} gate {gate:.2f}", flush=True)
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
    cp = sub.add_parser("cache-pairs")
    cp.add_argument("--pairs", type=pathlib.Path, required=True)
    cp.add_argument("--cache", type=pathlib.Path, required=True)
    c = sub.add_parser("cache")
    c.add_argument("--renders", type=pathlib.Path, required=True)
    c.add_argument("--cache", type=pathlib.Path, required=True)
    f = sub.add_parser("fit")
    f.add_argument("--cache", type=pathlib.Path, required=True)
    f.add_argument("--fold", type=int, required=True)
    f.add_argument("--out", type=pathlib.Path, required=True)
    f.add_argument("--minutes", type=float, default=60)
    f.add_argument("--seed", type=int, default=0)
    f.add_argument("--log-every", type=int, default=200)
    f.add_argument("--resume", type=pathlib.Path)
    f.add_argument("--extra-cache", type=pathlib.Path, nargs="*", default=[])
    f.add_argument("--lr", type=float, default=3e-4)
    f.add_argument("--lr-end", type=float)
    f.add_argument("--norm", action="store_true", help="v3: normalised bottleneck")
    f.add_argument("--open-bottom", action="store_true", help="v3b: no GLU gate at the deepest level")
    f.add_argument("--loss", choices=("default", "phase"), default="default")
    args = ap.parse_args()
    if args.cmd == "cache-pairs":
        build_pair_cache(args.pairs.expanduser(), args.cache.expanduser())
    elif args.cmd == "cache":
        build_cache(args.renders.expanduser(), args.cache.expanduser())
    else:
        fit(args.cache.expanduser(), args.fold, args.out.expanduser(), args.minutes, args.seed,
            log_every=args.log_every, resume=args.resume, lr=args.lr, lr_end=args.lr_end,
            extra=[c.expanduser() for c in args.extra_cache], norm=args.norm,
            open_bottom=args.open_bottom, loss_kind=args.loss)


if __name__ == "__main__":
    main()
