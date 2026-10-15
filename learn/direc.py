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

FIR_TAPS = 513                           # the residual path's linear filter, centred (±5 ms)


def build_model(channels=(32, 64, 128, 256, 512), lstm=256, norm=False, open_bottom=False,
                residual=False, linear_only=False, fullrate_head=False):
    """`residual` (docs/residual-di-plan.md): FIR(x) + U-Net(x), starting as the input, so the
    output cannot begin less coherent with the true DI than the recording. `linear_only`:
    the FIR alone (the plan's control L). `fullrate_head` (docs/di-fine-structure-plan.md, arm
    1e): base(x) + h(base(x), x), h three 48-kHz convolutions and a zero-initialised 1×1 output,
    so the model starts out identical to its base."""
    import torch
    import torch.nn as nn

    if fullrate_head:
        base = build_model(channels, lstm, norm=norm, open_bottom=open_bottom, residual=residual,
                           linear_only=linear_only)

        class FullRate(nn.Module):
            def __init__(self):
                super().__init__()
                self.base = base
                self.head = nn.Sequential(
                    nn.Conv1d(2, 32, 9, padding=4), nn.GELU(),
                    nn.Conv1d(32, 32, 9, padding=8, dilation=2), nn.GELU(),
                    nn.Conv1d(32, 32, 9, padding=16, dilation=4), nn.GELU(),
                    nn.Conv1d(32, 1, 1))
                with torch.no_grad():
                    self.head[-1].weight.zero_()
                    self.head[-1].bias.zero_()

            def forward(self, x):
                y = self.base(x)
                return y + self.head(torch.cat([y, x], 1))

        return FullRate()

    if residual or linear_only:
        unet = None if linear_only else build_model(channels, lstm, norm=norm, open_bottom=open_bottom)

        class Residual(nn.Module):
            def __init__(self):
                super().__init__()
                self.fir = nn.Conv1d(1, 1, FIR_TAPS, padding=FIR_TAPS // 2, bias=False)
                with torch.no_grad():
                    self.fir.weight.zero_()
                    self.fir.weight[0, 0, FIR_TAPS // 2] = 1.0
                self.unet = unet
                if unet is not None:
                    last = unet.dec[-1][-1]          # the final ConvTranspose1d
                    with torch.no_grad():
                        last.weight.mul_(0.01)
                        last.bias.mul_(0.01)

            def forward(self, x):
                y = self.fir(x)
                return y if self.unet is None else y + self.unet(x)

        return Residual()

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


_KERNELS: dict = {}


def _real_stft(x, n):
    """Windowed cosine and sine projections (an STFT's real and imaginary parts) as real
    matrix products with hop n/4: x (batch, samples) -> (batch, 2·bins, frames)."""
    import math

    import torch

    key = (n, str(x.device))
    if key not in _KERNELS:
        t = torch.arange(n, dtype=torch.float32)
        k = torch.arange(1, n // 2, dtype=torch.float32)[:, None]   # no DC, no Nyquist
        w = torch.hann_window(n)
        ang = 2 * math.pi * k * t / n
        _KERNELS[key] = torch.cat([w * torch.cos(ang), -w * torch.sin(ang)]).T.contiguous().to(x.device)
    # Frames then a matrix product: a conv1d with 2,048-tap kernels failed on MPS.
    return (x.unfold(-1, n, n // 4) @ _KERNELS[key]).transpose(1, 2)


def complex_stft_loss(a, b, ffts=(512, 1024, 2048)):
    """Phase-aware: L1 between the real and imaginary parts of the STFTs, averaged over
    resolutions. Plain magnitude losses ignore phase. Computed with real matrix products:
    gradients through torch.stft's complex output were non-finite on MPS (2026-10-10)."""
    if a.device.type == "mps":
        # MPS matmul on the unfolded (overlapping) frames is wrong even in the forward pass.
        return complex_stft_loss(a.cpu(), b.cpu(), ffts).to(a.device)
    total = 0.0
    for n in ffts:
        total = total + (_real_stft(a, n) - _real_stft(b, n)).abs().mean()
    return total / len(ffts)


def neg_si_sdr(a, b, eps=1e-8):
    """Negative scale-invariant SDR (dB), averaged over the batch."""
    import torch

    a = a - a.mean(-1, keepdim=True)
    b = b - b.mean(-1, keepdim=True)
    s = (a * b).sum(-1, keepdim=True) / ((b * b).sum(-1, keepdim=True) + eps) * b
    sdr = 10 * torch.log10((s * s).sum(-1) / (((a - s) ** 2).sum(-1) + eps) + eps)
    return -sdr.clamp(-50.0, 50.0).mean()           # a near-silent target can't blow it up


def training_loss(p, y, kind="default", terms=None):
    """`default`: 100·L1 + MR-STFT magnitude, as trained so far. `phase`
    (docs/di-loss-plan.md): plus a compressed complex-STFT term and SI-SDR, which keep
    the waveform the default loss lets drift. `terms` (docs/di-fine-structure-plan.md):
    {name: weight} of `FINE_TERMS` added on top; None leaves the loss exactly as it was."""
    loss = 100 * (p - y).abs().mean() + mrstft(p.squeeze(1), y.squeeze(1))
    if kind == "phase":
        loss = loss + PHASE_WEIGHTS[0] * complex_stft_loss(p.squeeze(1), y.squeeze(1)) \
            + PHASE_WEIGHTS[1] * neg_si_sdr(p.squeeze(1), y.squeeze(1))
    elif kind == "sisdr":
        loss = loss + PHASE_WEIGHTS[1] * neg_si_sdr(p.squeeze(1), y.squeeze(1))
    if terms:
        values = fine_terms(p, y, terms)
        for name, w in terms.items():
            loss = loss + w * values[name]
    return loss


PHASE_WEIGHTS = (10.0, 0.5)              # set so each term is about 2 of a ~8 total (measured)


def load_model(path, device="cpu"):
    """A saved network, with the architecture its weights imply."""
    import torch

    state = torch.load(path, map_location=device)
    if "head.6.weight" in state:                       # arm 1e: a plain U-Net base + the head
        net = build_model(norm=state["base.mid.0.0.weight"].dim() == 1, fullrate_head=True,
                          open_bottom=state["base.dec.0.0.weight"].shape[0]
                          == state["base.dec.0.0.weight"].shape[1])
        net.load_state_dict(state)
        return net
    if "fir.weight" in state:
        if "unet.mid.0.0.weight" not in state:
            net = build_model(linear_only=True)
        else:
            net = build_model(norm=state["unet.mid.0.0.weight"].dim() == 1, residual=True,
                              open_bottom=state["unet.dec.0.0.weight"].shape[0]
                              == state["unet.dec.0.0.weight"].shape[1])
        net.load_state_dict(state)
        return net
    net = build_model(norm=state["mid.0.0.weight"].dim() == 1,
                      open_bottom=state["dec.0.0.weight"].shape[0] == state["dec.0.0.weight"].shape[1])
    net.load_state_dict(state)
    return net


def gate_open(net, x):
    """Fraction of dec.0's gate above 1e-3 on `x` (0 means the bottom levels are dead); with
    an open bottom, the fraction of its GELU outputs above 1e-3 in size."""
    import torch

    if hasattr(net, "head"):
        net = net.base
    if hasattr(net, "fir"):
        if net.unet is None:
            return 1.0
        net = net.unet
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


def _magnitude(z):
    """|z| with a finite gradient everywhere. Complex `abs` has a NaN gradient at 0, and on
    MPS near it too: the likely cause of the 'MPS non-finite gradient' episodes since
    2026-10-06 (found 2026-10-10, docs/di-loss-plan.md). Same values to ~1e-6."""
    import torch

    r = torch.view_as_real(z)
    return torch.sqrt((r ** 2).sum(-1) + 1e-12)


def mrstft(a, b, ffts=(256, 512, 1024, 2048, 4096)):
    """Multi-resolution STFT magnitude loss. On MPS it is computed on the CPU and the
    gradient flows back: torch.stft's gradient on MPS is wrong for signals longer than
    65,536 samples (81–100% off the CPU's; the forward is right; torch 2.8 and 2.14,
    measured 2026-10-11). Training crops are 144,000 samples, so every DI network trained
    on MPS before that date learned from a wrong spectral gradient
    (docs/residual-di-plan.md)."""
    import torch

    if a.device.type == "mps":
        return mrstft(a.cpu(), b.cpu(), ffts).to(a.device)
    loss = 0.0
    for n in ffts:
        w = torch.hann_window(n, device=a.device)
        A = _magnitude(torch.stft(a, n, n // 4, window=w, return_complex=True)) + 1e-6
        B = _magnitude(torch.stft(b, n, n // 4, window=w, return_complex=True)) + 1e-6
        loss = loss + (A - B).norm() / (B.norm() + 1e-6) + (A.log() - B.log()).abs().mean()
    return loss / len(ffts)


# --- experiment 4: fine-structure terms (docs/di-fine-structure-plan.md) ------------------
#
# Every term takes (batch, 1, samples) tensors at the training scale (std 0.1 per crop).
# The STFT and phase terms run on the CPU whatever the device (torch.stft's MPS gradient is
# wrong above 65,536 samples; MPS matmul on unfolded frames is wrong even in the forward).
# Peakiness and the gap guard use reshapes only, so they stay on the device.

SHORT_FFTS = (32, 64, 128)
PHASE_FFTS = (256, 512, 1024)
PEAK_FRAMES = (48, 120)                  # 1 ms and 2.5 ms
GAP_FRAME = 240                          # 5 ms
WITHIN_DB = 35.0                         # peakiness frames: within this of the loudest frame
GAP_BELOW_DB = 35.0                      # gap frames: further than this under the loudest
FLOOR_DB = -90.0
FINE_TERMS = ("short", "peak", "gap", "phase")


def short_mrstft(a, b):
    """C′'s MR-STFT form (spectral convergence + log-magnitude L1) at FFT 32, 64, 128."""
    return mrstft(a, b, SHORT_FFTS)


def _frame_view(x, n):
    k = x.shape[-1] // n
    return x[..., :k * n].reshape(*x.shape[:-1], k, n)


def _crest_frames(F):
    import torch

    rms = torch.sqrt((F ** 2).mean(-1) + 1e-12)
    return 20 * torch.log10((F.abs().amax(-1) + 1e-9) / rms)


def peakiness_loss(p, y, frames=PEAK_FRAMES, within_db=WITHIN_DB):
    """Mean |crest_pred − crest_true| in dB on non-overlapping frames (1 and 2.5 ms), over the
    target's frames within `within_db` of its loudest frame."""
    import torch

    total = 0.0
    for n in frames:
        P, Y = _frame_view(p, n), _frame_view(y, n)
        ly = 10 * torch.log10((Y ** 2).mean(-1) + 1e-20)
        mask = (ly >= ly.amax(-1, keepdim=True) - within_db).float()
        err = (_crest_frames(P) - _crest_frames(Y)).abs()
        total = total + (err * mask).sum() / mask.sum().clamp_min(1.0)
    return total / len(frames)


def gap_guard(p, y, frame=GAP_FRAME, below_db=GAP_BELOW_DB, floor_db=FLOOR_DB):
    """Mean relu(L_pred − L_true), L in dB re the target crop's power on 5-ms frames (floored at
    −90 dB), over the target's frames more than `below_db` under its loudest. 0 if none."""
    import torch

    ref = (y ** 2).mean(-1, keepdim=True) + 1e-20

    def level(x):
        return (10 * torch.log10((_frame_view(x, frame) ** 2).mean(-1) / ref + 1e-30)).clamp_min(floor_db)

    lp, ly = level(p), level(y)
    mask = (ly < ly.amax(-1, keepdim=True) - below_db).float()
    return (torch.relu(lp - ly) * mask).sum() / mask.sum().clamp_min(1.0)


def _phasor_term(ar, ai, br, bi, dim, eps):
    """Target-magnitude-weighted 1 − cos of the difference between the predicted and target
    phase derivatives along `dim`, as phasor products z_k · conj(z_{k−1})."""
    import torch

    def diff(r, i):
        n = r.shape[dim] - 1
        r1, i1, r0, i0 = r.narrow(dim, 1, n), i.narrow(dim, 1, n), r.narrow(dim, 0, n), i.narrow(dim, 0, n)
        return r1 * r0 + i1 * i0, i1 * r0 - r1 * i0

    ur, ui = diff(ar, ai)
    vr, vi = diff(br, bi)
    nu = torch.sqrt(ur ** 2 + ui ** 2 + eps)
    nv = torch.sqrt(vr ** 2 + vi ** 2 + eps)
    cos = (ur * vr + ui * vi) / (nu * nv)
    w = nv.detach()
    return ((1 - cos) * w).sum() / w.sum().clamp_min(1e-12)


def phase_deriv_loss(a, b, ffts=PHASE_FFTS, eps=1e-10):
    """Instantaneous frequency (across time) and group delay (across frequency), each as a
    magnitude-weighted phasor cosine, averaged over FFT 256, 512, 1024 (hop n/4). Real-valued
    (no complex autograd, no atan2), and always on the CPU."""
    if a.device.type != "cpu":
        return phase_deriv_loss(a.cpu(), b.cpu(), ffts, eps).to(a.device)
    total = 0.0
    for n in ffts:
        A, B = _real_stft(a, n), _real_stft(b, n)          # (batch, 2·bins, frames)
        h = A.shape[1] // 2
        for dim in (2, 1):
            total = total + _phasor_term(A[:, :h], A[:, h:], B[:, :h], B[:, h:], dim, eps)
    return total / (2 * len(ffts))


def fine_terms(p, y, names=FINE_TERMS):
    """{name: unweighted value} for the requested fine-structure terms."""
    fns = {"short": lambda: short_mrstft(p.squeeze(1), y.squeeze(1)),
           "peak": lambda: peakiness_loss(p, y),
           "gap": lambda: gap_guard(p, y),
           "phase": lambda: phase_deriv_loss(p.squeeze(1), y.squeeze(1))}
    unknown = set(names) - set(fns)
    if unknown:
        raise ValueError(f"unknown loss terms {sorted(unknown)}")
    return {k: fns[k]() for k in names}


def parse_terms(text):
    """'short=1,peak=0.1' -> {'short': 1.0, 'peak': 0.1}; '' or None -> None."""
    if not text:
        return None
    out = {}
    for item in text.split(","):
        k, v = item.split("=")
        out[k.strip()] = float(v)
    fine_terms_check = set(out) - set(FINE_TERMS)
    if fine_terms_check:
        raise ValueError(f"unknown loss terms {sorted(fine_terms_check)}")
    return out


FINE_MS = (0.5, 1.0, 2.5, 5.0, 10.0)


def fine_metrics(pred, true, sr=SR):
    """Numpy fine-structure metrics of `pred` against `true` (1-D, or rows), averaged over rows:
    per-frame crest (dB) at FINE_MS over the target's frames within 35 dB of its loudest; the
    5-ms level of the prediction over the target's gap frames (> 35 dB under the loudest) and
    quiet frames (≥ 20 dB under), dB re the target crop; the waveform SNR; and the 3–8 kHz
    share of power (pred − true, dB)."""
    import numpy as np

    P = np.atleast_2d(np.asarray(pred, np.float64))
    T = np.atleast_2d(np.asarray(true, np.float64))
    n = min(P.shape[-1], T.shape[-1])
    P, T = P[:, :n], T[:, :n]
    out = {}

    def frames(x, k):
        m = x.shape[-1] // k
        return x[:, :m * k].reshape(x.shape[0], m, k)

    def crest(F):
        return 20 * np.log10((np.abs(F).max(-1) + 1e-12) / (np.sqrt((F ** 2).mean(-1)) + 1e-12))

    for ms in FINE_MS:
        k = int(round(ms * sr / 1000))
        FP, FT = frames(P, k), frames(T, k)
        lt = 10 * np.log10((FT ** 2).mean(-1) + 1e-20)
        act = lt >= lt.max(-1, keepdims=True) - WITHIN_DB
        cp = np.array([crest(FP)[i][act[i]].mean() for i in range(len(P))])
        ct = np.array([crest(FT)[i][act[i]].mean() for i in range(len(P))])
        out[f"crest_{ms:g}ms_pred"] = float(cp.mean())
        out[f"crest_{ms:g}ms_true"] = float(ct.mean())
        out[f"crest_{ms:g}ms_err"] = float((cp - ct).mean())
    ref = (T ** 2).mean(-1, keepdims=True) + 1e-20
    FP, FT = frames(P, GAP_FRAME), frames(T, GAP_FRAME)
    lp = np.maximum(10 * np.log10((FP ** 2).mean(-1) / ref + 1e-30), FLOOR_DB)
    lt = np.maximum(10 * np.log10((FT ** 2).mean(-1) / ref + 1e-30), FLOOR_DB)
    for name, below in (("gap", GAP_BELOW_DB), ("quiet", 20.0)):
        m = lt < lt.max(-1, keepdims=True) - below
        out[f"{name}_frames"] = int(m.sum())
        out[f"{name}_db"] = float((lp - lt)[m].mean()) if m.any() else None
    err = ((P - T) ** 2).sum(-1)
    out["snr_db"] = float(np.mean(10 * np.log10((T ** 2).sum(-1) / (err + 1e-20) + 1e-20)))
    f = np.fft.rfftfreq(n, 1 / sr)
    band = (f >= 3000) & (f < 8000)

    def share(x):
        s = np.abs(np.fft.rfft(x, axis=-1)) ** 2
        return 10 * np.log10(s[:, band].sum(-1) / (s.sum(-1) + 1e-20) + 1e-20)

    out["hf_3_8k_db"] = float(np.mean(share(P) - share(T)))
    return out


# --- experiment 4, arm 1c: HiFi-GAN discriminators and an EnCodec-style balancer ------------

def build_discriminators(periods=(2, 3, 5, 7, 11), scales=3):
    """HiFi-GAN's MPD (periods 2, 3, 5, 7, 11) and MSD (3 scales), weight-normed (MIT,
    reimplemented). forward(x) -> [(logits, [feature maps])] for each sub-discriminator."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.nn.utils.parametrizations import weight_norm as wn

    class DP(nn.Module):
        def __init__(self, period):
            super().__init__()
            self.period = period
            ch = [1, 32, 128, 512, 1024, 1024]
            self.convs = nn.ModuleList([wn(nn.Conv2d(ch[i], ch[i + 1], (5, 1), (3, 1) if i < 4 else 1,
                                                     padding=(2, 0))) for i in range(5)])
            self.post = wn(nn.Conv2d(1024, 1, (3, 1), 1, padding=(1, 0)))

        def forward(self, x):
            b, c, t = x.shape
            pad = (-t) % self.period
            if pad:
                x = F.pad(x, (0, pad), "reflect")
            x = x.view(b, c, -1, self.period)
            feats = []
            for conv in self.convs:
                x = F.leaky_relu(conv(x), 0.1)
                feats.append(x)
            x = self.post(x)
            feats.append(x)
            return x.flatten(1), feats

    class DS(nn.Module):
        def __init__(self):
            super().__init__()
            spec = [(1, 128, 15, 1, 1, 7), (128, 128, 41, 2, 4, 20), (128, 256, 41, 2, 16, 20),
                    (256, 512, 41, 4, 16, 20), (512, 1024, 41, 4, 16, 20), (1024, 1024, 41, 1, 16, 20),
                    (1024, 1024, 5, 1, 1, 2)]
            self.convs = nn.ModuleList([wn(nn.Conv1d(i, o, k, s, groups=g, padding=p)) for i, o, k, s, g, p in spec])
            self.post = wn(nn.Conv1d(1024, 1, 3, 1, padding=1))

        def forward(self, x):
            feats = []
            for conv in self.convs:
                x = F.leaky_relu(conv(x), 0.1)
                feats.append(x)
            x = self.post(x)
            feats.append(x)
            return x.flatten(1), feats

    class Multi(nn.Module):
        def __init__(self):
            super().__init__()
            self.mpd = nn.ModuleList([DP(p) for p in periods])
            self.msd = nn.ModuleList([DS() for _ in range(scales)])
            self.pool = nn.AvgPool1d(4, 2, padding=2)

        def forward(self, x):
            outs = [d(x) for d in self.mpd]
            for i, d in enumerate(self.msd):
                if i:
                    x = self.pool(x)
                outs.append(d(x))
            return outs

    return Multi()


def disc_loss(outs_real, outs_fake):
    """LSGAN: Σ mean((D(real) − 1)²) + mean(D(fake)²)."""
    return sum(((r - 1) ** 2).mean() + (f ** 2).mean() for (r, _), (f, _) in zip(outs_real, outs_fake))


def gen_adv_loss(outs_fake):
    return sum(((f - 1) ** 2).mean() for f, _ in outs_fake)


def feature_loss(outs_real, outs_fake):
    """L1 between real (detached) and fake feature maps: mean over layers, summed over
    sub-discriminators."""
    total = 0.0
    for (_, fr), (_, ff) in zip(outs_real, outs_fake):
        total = total + sum((a.detach() - b).abs().mean() for a, b in zip(fr, ff)) / len(fr)
    return total


ADV_DEFAULT = {"warm": 500, "lr": 1e-4, "shares": {"recon": 0.7, "fm": 0.2, "adv": 0.1},
               "decay": 0.999, "micro": 1}


class Balancer:
    """EnCodec's gradient balancer, on the output waveform: each term's gradient is divided by
    an EMA of its norm and scaled by its share. The reference norm is the reconstruction
    term's own EMA, so with shares (0.7, 0.2, 0.1) the reconstruction gradient keeps about 0.7
    of its unbalanced size."""

    def __init__(self, shares, decay=0.999):
        self.shares, self.decay, self.ema = dict(shares), decay, {}

    def combine(self, grads):
        norms = {k: float(g.norm()) for k, g in grads.items()}
        for k, n in norms.items():
            self.ema[k] = n if k not in self.ema else self.decay * self.ema[k] + (1 - self.decay) * n
        ref = self.ema.get("recon", 1.0)
        return sum(self.shares[k] * ref * g / (self.ema[k] + 1e-12) for k, g in grads.items())


def _adv_generator_backward(p, y, discs, balancer, terms, loss_kind, micro):
    """Reconstruction + feature matching + adversarial, balanced on ∂/∂p; backpropagates into
    the generator only. Returns the reconstruction loss (for logging)."""
    import torch

    recon = training_loss(p, y, loss_kind, terms)
    g_recon = torch.autograd.grad(recon, p, retain_graph=True)[0]
    g_fm, g_adv = torch.zeros_like(p), torch.zeros_like(p)
    for sl in _chunks(p.shape[0], micro):
        with torch.no_grad():
            real = discs(y[sl])
        fake = discs(p[sl])
        fm, adv = feature_loss(real, fake), gen_adv_loss(fake)
        a = torch.autograd.grad(fm, p, retain_graph=True)[0]
        b = torch.autograd.grad(adv, p, retain_graph=True)[0]
        g_fm, g_adv = g_fm + a, g_adv + b
    p.backward(balancer.combine({"recon": g_recon, "fm": g_fm, "adv": g_adv}))
    return recon.detach()


def _chunks(n, micro):
    size = -(-n // max(1, micro))
    return [slice(i, min(n, i + size)) for i in range(0, n, size)]


def _disc_step(discs, dopt, fake, real, micro, lr):
    import torch

    for g in dopt.param_groups:
        g["lr"] = lr
    dopt.zero_grad()
    for sl in _chunks(fake.shape[0], micro):
        loss = disc_loss(discs(real[sl]), discs(fake[sl])) / max(1, micro)
        loss.backward()
    grads = [q.grad for q in discs.parameters() if q.grad is not None]
    total = torch.sqrt(sum((g.detach() ** 2).sum() for g in grads))
    if not torch.isfinite(total):
        return False
    if total > 5.0:
        for g in grads:
            g.mul_(5.0 / total)
    dopt.step()
    return True


# --- training -----------------------------------------------------------------------

def fit(cache, fold, out, minutes, seed, batch=12, log_every=200, resume=None, lr=3e-4, lr_end=None,
        extra=None, norm=False, open_bottom=False, loss_kind="default", residual=False, linear_only=False,
        steps=None, fir_lr_scale=0.1, terms=None, warmup=0, adv=None, fullrate_head=False, overfit=0,
        log_fine=False, calibrate=0, eval_only=False, mark_done=False):
    """`steps` (residual-di-plan.md): stop after this many optimiser steps instead of
    `minutes`, with any cosine decay by step, so a slower model gets the same updates.

    Experiment 4 (docs/di-fine-structure-plan.md); every option is off by default, and off
    leaves C′'s training bit-identical (tests/test_direc_fine.py):
    - `terms` {name: weight}: fine-structure terms added to the loss (`training_loss`);
    - `warmup` N: a linear ramp from 0 to `lr` over N steps, then the cosine over the rest;
    - `adv` (a dict like ADV_DEFAULT): MPD/MSD from step `warm`, balanced; the discriminators
      train every step on the detached output;
    - `fullrate_head`: arm 1e's head; `resume` may be a plain C′ checkpoint (loaded into base);
    - `overfit` N: N fixed training-split crops, no augmentation, every step (step 0e); writes
      `overfit.json` with the fine metrics before and after;
    - `log_fine`: fine metrics on the validation crops at each validation (uses no randomness);
    - `calibrate` N: no training; the mean of C′'s loss and every fine term over the first N
      training batches, written to `calibrate.json` (step 0d);
    - `eval_only`: no training; validation and fine metrics of `resume` on the 96 validation
      crops, written to `eval.json` (step 1d);
    - `mark_done`: touch `DONE` in `out` when training ends."""
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

    net = build_model(norm=norm, open_bottom=open_bottom, residual=residual, linear_only=linear_only,
                      fullrate_head=fullrate_head).to(dev)

    def load_state(state):
        # Arm 1e starts from a plain C′ checkpoint: its weights go into the base.
        if fullrate_head and not any(k.startswith("base.") for k in state):
            net.base.load_state_dict(state)
        else:
            net.load_state_dict(state)

    if resume:
        load_state(torch.load(resume, map_location=dev))
        print(f"resumed from {resume}", flush=True)
    print(f"parameters {sum(p.numel() for p in net.parameters()) / 1e6:.1f}M", flush=True)
    def optimiser():
        # The residual path's FIR learns at a lower rate: Adam moves every tap at about the
        # learning rate, and a smeared tail would reach the presets unseen by coherence.
        fir = [q for n_, q in net.named_parameters() if n_.startswith("fir.")]
        rest = [q for n_, q in net.named_parameters() if not n_.startswith("fir.")]
        groups = ([{"params": rest, "scale": 1.0}] if rest else []) + \
                 ([{"params": fir, "scale": fir_lr_scale}] if fir else [])
        for g in groups:
            g["lr"] = lr * g["scale"]
        if not fir:                      # no FIR: exactly the original optimiser
            return torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-5)
        return torch.optim.AdamW(groups, lr=lr, weight_decay=1e-5)

    opt = optimiser()
    out.mkdir(parents=True, exist_ok=True)
    t0, step, skipped, streak, recoveries = time.time(), 0, 0, 0, 0
    window = []
    vidx = rng.choice(va, min(96, len(va)), replace=False)
    # Experiment 4 (all off by default; nothing below this line runs for C′'s recipe).
    if warmup and not steps:
        raise ValueError("--warmup needs --steps")
    if terms or warmup or adv or fullrate_head or overfit or log_fine or calibrate or eval_only or mark_done:
        (out / ("config-eval.json" if eval_only else "config-calibrate.json" if calibrate else "config.json")).write_text(
            json.dumps({"fold": fold, "seed": seed, "batch": batch, "steps": steps, "lr": lr, "lr_end": lr_end,
                        "warmup": warmup, "terms": terms, "adv": adv, "fullrate_head": fullrate_head,
                        "overfit": overfit, "resume": str(resume) if resume else None,
                        "caches": [str(c) for c in caches]}, indent=1))
    if eval_only:
        _evaluate(net, make, vidx, batch, out / "eval.json", fold, resume)
        return
    if calibrate:
        _calibrate(net, make, rng, tr, batch, calibrate, out / "calibrate.json", loss_kind)
        return
    ov_idx = rng.choice(tr, overfit, replace=False) if overfit else None
    if overfit:
        ov_start = _fine_on(net, make, ov_idx, batch)
    discs = dopt = balancer = None
    if adv:
        discs = build_discriminators().to(dev)
        dopt = torch.optim.AdamW(discs.parameters(), lr=adv["lr"], betas=(0.8, 0.99), weight_decay=1e-5)
        balancer = Balancer(adv["shares"], adv.get("decay", 0.999))
    while (step < steps) if steps else (time.time() - t0 < minutes * 60):
        if warmup and step < warmup:
            for g in opt.param_groups:
                g["lr"] = lr * (step + 1) / warmup * g.get("scale", 1.0)
        elif lr_end is not None:          # cosine decay over the run's budget (steps, or wall clock)
            frac = (min(1.0, (step - warmup) / max(1, steps - warmup)) if warmup else
                    min(1.0, step / steps if steps else (time.time() - t0) / (minutes * 60)))
            for g in opt.param_groups:
                g["lr"] = (lr_end + 0.5 * (lr - lr_end) * (1 + math.cos(math.pi * frac))) * g.get("scale", 1.0)
        if overfit:
            idx = ov_idx
            x, y = make(idx, False)
        else:
            idx = rng.choice(tr, batch, replace=False)
            x, y = make(idx, True)
        p = net(x)
        if adv and step >= adv["warm"]:
            opt.zero_grad()
            loss = _adv_generator_backward(p, y, discs, balancer, terms, loss_kind, adv.get("micro", 1))
        else:
            loss = training_loss(p, y, loss_kind, terms)
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
                    load_state(state)
                opt = optimiser()
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
        if adv:
            d_lr = adv["lr"] if lr_end is None else (
                lr_end + 0.5 * (adv["lr"] - lr_end) * (1 + math.cos(math.pi * min(1.0, step / steps))))
            _disc_step(discs, dopt, p.detach(), y, adv.get("micro", 1), d_lr)
        step += 1
        if step % log_every == 0:
            net.eval()
            fine_p, fine_y = [], []
            with torch.no_grad():
                vl, base = 0.0, 0.0
                for s in range(0, len(vidx), batch):
                    vx, vy = make(vidx[s:s + batch], False)
                    vp = net(vx)
                    vl += float(100 * (vp - vy).abs().mean() + mrstft(vp.squeeze(1), vy.squeeze(1)))
                    base += float(100 * (vx - vy).abs().mean() + mrstft(vx.squeeze(1), vy.squeeze(1)))
                    if log_fine:
                        fine_p.append(vp[:, 0].cpu().numpy())
                        fine_y.append(vy[:, 0].cpu().numpy())
            gate = gate_open(net, vx)
            net.train()
            el = time.time() - t0
            print(f"fold {fold} step {step} {el / 60:.1f} min ({step / el:.2f} it/s) train {float(loss.detach()):.3f} "
                  f"val {vl:.3f} (input-as-DI {base:.3f}) skipped {skipped} gate {gate:.2f}", flush=True)
            if log_fine:
                print(f"fold {fold} step {step} fine " + json.dumps(_round(fine_metrics(
                    np.concatenate(fine_p), np.concatenate(fine_y)))), flush=True)
            torch.save(net.state_dict(), out / f"fold{fold}.pt")
    torch.save(net.state_dict(), out / f"fold{fold}.pt")
    if overfit:
        (out / "overfit.json").write_text(json.dumps(
            {"crops": [int(i) for i in ov_idx], "start": ov_start, "end": _fine_on(net, make, ov_idx, batch)}, indent=1))
    if mark_done:
        (out / "DONE").write_text(time.strftime("%Y-%m-%d %H:%M:%S\n"))
    if hasattr(net, "fir"):             # the learned linear path, for the record
        w = net.fir.weight.detach().cpu().numpy()[0, 0]
        np.save(out / f"fold{fold}-fir.npy", w)
        mag = 20 * np.log10(np.abs(np.fft.rfft(w, 8192)) + 1e-12)
        print(f"FIR peak tap {int(np.argmax(np.abs(w))) - FIR_TAPS // 2:+d}, magnitude dB at "
              f"100 Hz/1 kHz/5 kHz: {mag[17]:.1f}/{mag[171]:.1f}/{mag[853]:.1f}", flush=True)


def _round(d, k=4):
    return {a: (round(b, k) if isinstance(b, float) else b) for a, b in d.items()}


def _predict(net, make, idx, batch):
    """(input, prediction, target) arrays (rows × samples) for `idx`, unaugmented, no grad."""
    import numpy as np
    import torch

    xs, ps, ys = [], [], []
    was = net.training
    net.eval()
    with torch.no_grad():
        for s in range(0, len(idx), batch):
            x, y = make(idx[s:s + batch], False)
            xs.append(x[:, 0].cpu().numpy())
            ps.append(net(x)[:, 0].cpu().numpy())
            ys.append(y[:, 0].cpu().numpy())
    net.train(was)
    return np.concatenate(xs), np.concatenate(ps), np.concatenate(ys)


def _fine_on(net, make, idx, batch):
    _, p, y = _predict(net, make, idx, batch)
    return fine_metrics(p, y)


def _evaluate(net, make, vidx, batch, path, fold, resume):
    """Step 1d's numbers for one network: C′'s validation measure and its input-as-DI baseline
    on the fit's own 96 validation crops, the ratio, the fine metrics and the gate."""
    import torch

    x, p, y = _predict(net, make, vidx, batch)
    vl = base = 0.0
    for s in range(0, len(vidx), batch):
        tx, tp, ty = (torch.tensor(a[s:s + batch])[:, None] for a in (x, p, y))
        vl += float(100 * (tp - ty).abs().mean() + mrstft(tp.squeeze(1), ty.squeeze(1)))
        base += float(100 * (tx - ty).abs().mean() + mrstft(tx.squeeze(1), ty.squeeze(1)))
    dev = next(net.parameters()).device
    gate = gate_open(net.eval(), torch.tensor(x[:batch], device=dev)[:, None])
    res = {"fold": fold, "model": str(resume), "crops": len(vidx), "val": vl, "input_as_di": base,
           "ratio": vl / base, "gate": gate, "fine": fine_metrics(p, y)}
    path.write_text(json.dumps(res, indent=1))
    print(json.dumps(_round({k: v for k, v in res.items() if k != "fine"})), flush=True)
    return res


def _calibrate(net, make, rng, tr, batch, n, path, loss_kind):
    """Step 0d: the mean of C′'s loss and of every fine term over the first `n` training batches
    (the same batches, in the same order, as a training run with this seed sees first)."""
    import torch

    sums = {"L_C": 0.0, "mrstft": 0.0, **{k: 0.0 for k in FINE_TERMS}}
    net.eval()
    with torch.no_grad():
        for _ in range(n):
            idx = rng.choice(tr, batch, replace=False)
            x, y = make(idx, True)
            p = net(x)
            sums["L_C"] += float(training_loss(p, y, loss_kind))
            sums["mrstft"] += float(mrstft(p.squeeze(1), y.squeeze(1)))
            for k, v in fine_terms(p, y).items():
                sums[k] += float(v)
    means = {k: v / n for k, v in sums.items()}
    path.write_text(json.dumps({"batches": n, "batch": batch, "means": means}, indent=1))
    print(json.dumps(_round(means)), flush=True)
    return means


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
    f.add_argument("--loss", choices=("default", "phase", "sisdr"), default="default")
    f.add_argument("--residual", action="store_true", help="FIR(x) + U-Net(x) (residual-di-plan.md)")
    f.add_argument("--linear-only", action="store_true", help="the FIR alone (control L)")
    f.add_argument("--steps", type=int, help="stop after this many steps (cosine by step)")
    f.add_argument("--fir-lr-scale", type=float, default=0.1)
    # experiment 4 (docs/di-fine-structure-plan.md); all off by default
    f.add_argument("--terms", help="fine-structure terms, e.g. short=1,peak=0.1,gap=0.02,phase=1")
    f.add_argument("--warmup", type=int, default=0, help="linear warm-up steps (needs --steps)")
    f.add_argument("--adv", action="store_true", help="arm 1c: MPD/MSD with the balancer")
    f.add_argument("--adv-warm", type=int, default=ADV_DEFAULT["warm"])
    f.add_argument("--adv-lr", type=float, default=ADV_DEFAULT["lr"])
    f.add_argument("--adv-shares", default="0.7,0.2,0.1", help="recon,fm,adv")
    f.add_argument("--adv-micro", type=int, default=1, help="split the discriminators' batch (memory)")
    f.add_argument("--fullrate-head", action="store_true", help="arm 1e: zero-initialised full-rate head")
    f.add_argument("--overfit", type=int, default=0, help="step 0e: train on N fixed crops")
    f.add_argument("--log-fine", action="store_true", help="fine metrics at each validation")
    f.add_argument("--calibrate", type=int, default=0, help="step 0d: term means over N batches, no training")
    f.add_argument("--eval-only", action="store_true", help="step 1d: evaluate --resume, no training")
    f.add_argument("--mark-done", action="store_true", help="touch DONE in --out when training ends")
    f.add_argument("--batch", type=int, default=12)
    args = ap.parse_args()
    if args.cmd == "cache-pairs":
        build_pair_cache(args.pairs.expanduser(), args.cache.expanduser())
    elif args.cmd == "cache":
        build_cache(args.renders.expanduser(), args.cache.expanduser())
    else:
        fit(args.cache.expanduser(), args.fold, args.out.expanduser(), args.minutes, args.seed,
            log_every=args.log_every, resume=args.resume, lr=args.lr, lr_end=args.lr_end,
            extra=[c.expanduser() for c in args.extra_cache], norm=args.norm,
            open_bottom=args.open_bottom, loss_kind=args.loss, residual=args.residual,
            linear_only=args.linear_only, steps=args.steps, fir_lr_scale=args.fir_lr_scale,
            batch=args.batch, terms=parse_terms(args.terms), warmup=args.warmup,
            adv=_adv_config(args) if args.adv else None, fullrate_head=args.fullrate_head,
            overfit=args.overfit, log_fine=args.log_fine, calibrate=args.calibrate,
            eval_only=args.eval_only, mark_done=args.mark_done)


def _adv_config(args):
    r, fm, a = (float(v) for v in args.adv_shares.split(","))
    return {**ADV_DEFAULT, "warm": args.adv_warm, "lr": args.adv_lr, "micro": args.adv_micro,
            "shares": {"recon": r, "fm": fm, "adv": a}}


if __name__ == "__main__":
    main()
