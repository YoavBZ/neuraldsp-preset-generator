"""EG-VAE-lite's E1 mapper (`docs/egvae-lite-plan.md`, "E1 after review", "E1 data", "E1:
codebooks predicted", "E1 mapper: declared before training"): the recording's 9 DAC 44 kHz
codebooks in, the average-balance DI's first 4 codebooks out, per frame, by cross-entropy.
DAC stays frozen at both ends; nothing STFT-based is in training.

    $LEARN_PY -m learn.egvae_e1 train                   # MPS; resumable; MPS-vs-CPU check first
    $LEARN_PY -m learn.egvae_e1 bench [DEVICE] [STEPS]  # seconds per training step, random codes
    $LEARN_PY -m learn.egvae_e1 precheck1               # decoded mel, 96 fold-2 clips, E1 against C′
    $LEARN_PY -m learn.egvae_e1 precheck2               # rebuild the 18 parts; 80 Hz–1 kHz coherence
    $LEARN_PY -m learn.egvae_e1 render K N              # shard K of N (N ≤ 3) of the 111-preset menu
    $LEARN_PY -m learn.egvae_e1 score
    $LEARN_PY -m learn.egvae_e1 report                  # -> docs/egvae-e1-result.json

($LEARN_PY = ~/ndsp-presets/tools/learn-venv/bin/python. The DAC half runs in the DAC venv
through `learn/egvae_e1_codec.py`, called here as a subprocess.)

**Data** (`learn/egvae_e1_data.py`): every C′ clip's recording and target codes, (9, 517)
each per 6-s clip. Training clips are folds ≠ 2 (38,709), validation fold 2 (10,097). Crops are
3 s: 258 frames at 44,100 / 512 = 86.13 frames/s. Training crops are fresh each step: for every
example in every batch a crop start drawn uniformly from frames 0–259 (the numpy sampling rng,
after the batch's clip draw; `random_crops`). Validation crops are fixed at C′'s centred one
(frame 129; `crop_frame` of the stored start). Training refuses to start until all shards are
encoded (`--partial` is for smoke tests only). ("E1 after code review" in the plan replaced the
first declaration's one fixed crop per training clip.)

**The mapper** (`build_model`, 18.7 M parameters):
- one 1024 × 384 embedding per input codebook, summed (scaled by 1/√9);
- a convolutional front end: two residual blocks of two kernel-5 convolutions with GELU;
- 6 pre-norm Transformer encoder blocks (d 384, 6 heads, feed-forward 1536, residual dropout
  0.1, attention dropout 0 so that the MPS check covers the training graph),
  bidirectional, with rotary (relative) positions and no absolute positions, so a 258-frame
  window at inference is what training saw, at any offset;
- a final LayerNorm and 4 softmax heads of 1024 classes.

**Loss:** cross-entropy per codebook, averaged over frames, summed over the 4 codebooks with
equal weights (declared: no index weighting).

**Training (declared):** batch 32 crops; AdamW (β 0.9/0.98, weight decay 0.01, none on norms,
biases and embeddings); learning rate 3e-4 after a 1,000-step linear warm-up, cosine to 3e-5 at
40,000 steps; seed 0 (torch and the numpy sampling rng); gradients clipped by hand at norm 1.0
(`clip_grad_norm_` gives NaN on MPS), a non-finite step skipped. Every 1,000 steps: the summed
cross-entropy on all 10,097 validation crops (eval mode), per-codebook accuracy, a checkpoint
(`last.pt`, with optimiser and rng state) and `best.pt` when validation improves by at least
0.002 nats. **Early stop:** 5 evaluations in a row (5,000 steps) without such an improvement,
or 40,000 steps. `best.pt` is the network evaluated. Before the first step, and again after
200 steps with the trained weights, `mps_check` compares MPS with the CPU on one real batch at
crop length and the training batch size (32 × 258, residual dropout off; attention dropout is
0 in training too): logits within 1e-4 relative, loss within 1e-5 relative, and every
parameter's gradient with cosine > 0.999 and relative norm difference < 1e-3; otherwise it
aborts. `last.pt` and `best.pt` are written atomically; resume restores the numpy, torch CPU and
(when available) MPS rng states.

**Rebuild** (`rebuild`, `rebuild_many`): 48 → 44.1 kHz (`resample_poly` 147/160); DAC encode
at −16 LUFS (the data encoder's path); the mapper over overlapping 258-frame windows (hop 129)
whose log-probabilities are crossfaded linearly (`stitch`), argmax per frame and codebook; the
4 codebooks decoded; 44.1 → 48 kHz; cut to the input's length; −22.9 LUFS
(`direc_check.to_lufs`). No alignment to the true DI: its lag is only reported.

**Evaluation** (the plan's pre-checks and test):
1. `precheck1`: C′'s own 96 validation clips (`fit`'s `vidx` for seed 0), centred 3-s crops.
   E1 maps the stored codes of the whole 6-s clip and decodes; C′ (models-cprime, seed 0)
   rebuilds the whole 6-s clip with `direc.rebuild`. Both are cut to the centred crop, set with
   the target to −22.9 LUFS, and scored with E0's mel distance (DAC's multi-scale log-mel,
   `egvae_e0_dac.py mel`) against the average-balance target. Passes if E1's mean (at
   `best.pt`) ≤ C′'s mean. Also reported, not gated: E1 at `last.pt` (its final weights, as C′
   is), since `best.pt` is selected on fold-2 validation, which contains these 96 clips.
2. `precheck2`: E1 rebuilds the 18 development parts' recordings; coherence with the true DI
   as `residual_eval.coherence` (aligned within ±50 ms of the judge lag plus latency, which is
   reported as the misalignment). Passes if the median 80 Hz–1 kHz coherence ≥ 0.472 (C′'s).
3. The pick test (`render`, `score`, `report`): the 18 rebuilt DIs through the 111-preset menu
   (≤ 3 renderer processes), picks per amp per half with `rebuilt_distance`, scored on the other
   half with the stored true-DI measure. E1 against C′ as the mean of seeds 0 and 1 per cell
   (`set5_test.evaluate`'s averaging: the log ratio to each seed, averaged, then over halves),
   on the band-mean rule with 7 df (`set5_test._band_gate`: helps / futile / inconclusive).
   **The set-5 rule:** E1 earns a held-out test only if both pre-checks pass, the band mean is
   ≤ −0.015 and the 90% upper bound < +0.03.
"""

from __future__ import annotations

import json
import math
import os
import pathlib
import statistics
import subprocess
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
DIREC = HOME / "learn/direc"
CODES = DIREC / "e1-codes"
RUN = DIREC / "egvae-e1"
DAC_PY = HOME / "tools/dac-venv/bin/python"
CODEC = PLUGIN_ROOT / "learn/egvae_e1_codec.py"
RESULT = PLUGIN_ROOT / "docs/egvae-e1-result.json"

SR48, SR44, HOP = 48000, 44100, 512
FRAMES = 517                       # frames per 6-s clip (264,600 samples, padded to 517 × 512)
CROP_FRAMES = 258                  # C′'s 3-s crop: 132,300 samples at 44.1 kHz / 512
VAL_FRAME = 129                    # C′'s centred validation crop (72,000 samples at 48 kHz)
N_IN, N_OUT, K = 9, 4, 1024
FOLD = 2
CPRIME0 = DIREC / "models-cprime/fold2.pt"
COHERENCE_BAR = 0.472              # C′'s median 80 Hz–1 kHz coherence (residual/coherence.json)
SET5_BAND_MEAN, SET5_HI90 = -0.015, 0.03

CFG = dict(d=384, layers=6, heads=6, ff=1536, conv_kernel=5, dropout=0.1, attn_dropout=0.0,
           batch=32, lr=3e-4, lr_end=3e-5, warmup=1000, weight_decay=0.01, betas=(0.9, 0.98),
           max_steps=40000, eval_every=1000, patience=5, min_delta=0.002, clip=1.0, seed=0,
           codebook_weights=(1.0, 1.0, 1.0, 1.0), window=CROP_FRAMES, window_hop=CROP_FRAMES // 2)


# --- crops and windows (numpy only) -------------------------------------------------------

def crop_frame(start48):
    """C′'s crop start (samples at 48 kHz) as a code frame: the same instant at 44.1 kHz over
    the 512 hop, rounded, kept inside the clip."""
    f = int(round(start48 * SR44 / SR48 / HOP))
    return min(max(f, 0), FRAMES - CROP_FRAMES)


def random_crops(X, Y, ix, rng):
    """Batch ix of full-clip codes, X (n, 9, 517) and Y (n, 4, 517), each example cropped to
    258 frames at its own start drawn uniformly from 0..FRAMES − CROP_FRAMES (0–259)."""
    import numpy as np

    starts = rng.integers(0, FRAMES - CROP_FRAMES + 1, len(ix))
    t = (starts[:, None] + np.arange(CROP_FRAMES))[:, None, :]
    return np.take_along_axis(X[ix], t, 2), np.take_along_axis(Y[ix], t, 2)


def window_starts(n, win, hop):
    """Window starts covering n frames; the last window ends at n."""
    if n <= win:
        return [0]
    starts = list(range(0, n - win + 1, hop))
    if starts[-1] + win < n:
        starts.append(n - win)
    return starts


def stitch(n, win, hop, fn):
    """Per-frame log-probabilities over n frames from overlapping windows: fn(start, length)
    gives (codebooks, length, K) for frames [start, start + length); overlaps are crossfaded
    with linear ramps (as `direc.rebuild` does for audio), full weight at the signal's ends."""
    import numpy as np

    starts = window_starts(n, win, hop)
    acc = wsum = None
    for s in starts:
        L = min(win, n - s)
        lp = fn(s, L)
        if acc is None:
            acc = np.zeros((lp.shape[0], n, lp.shape[-1]), np.float64)
            wsum = np.zeros(n, np.float64)
        w = np.ones(L)
        ov = min(win - hop, L)
        if len(starts) > 1 and ov > 0:
            w[:ov] = np.linspace(1 / ov, 1, ov)
            w[-ov:] = np.minimum(w[-ov:], np.linspace(1, 1 / ov, ov))
            if s == 0:
                w[:ov] = 1
            if s + L >= n:
                w[-ov:] = 1
        acc[:, s:s + L] += lp * w[None, :, None]
        wsum[s:s + L] += w
    return acc / wsum[None, :, None]


# --- the mapper ----------------------------------------------------------------------------

def _rope(q):
    """Rotary positions on (..., T, head_dim): attention scores then depend only on the
    frames' distance, not on where the window sits."""
    import torch

    T, dh = q.shape[-2], q.shape[-1]
    inv = 1.0 / (10000 ** (torch.arange(0, dh, 2, device=q.device, dtype=torch.float32) / dh))
    ang = torch.arange(T, device=q.device, dtype=torch.float32)[:, None] * inv[None]
    cos, sin = ang.cos(), ang.sin()
    a, b = q[..., 0::2], q[..., 1::2]
    return torch.stack((a * cos - b * sin, a * sin + b * cos), -1).flatten(-2)


def build_model(cfg=CFG):
    import torch
    from torch import nn
    import torch.nn.functional as F

    d, H = cfg["d"], cfg["heads"]

    class Block(nn.Module):
        def __init__(self):
            super().__init__()
            self.n1, self.n2 = nn.LayerNorm(d), nn.LayerNorm(d)
            self.qkv, self.proj = nn.Linear(d, 3 * d), nn.Linear(d, d)
            self.ff = nn.Sequential(nn.Linear(d, cfg["ff"]), nn.GELU(), nn.Linear(cfg["ff"], d))
            self.drop = nn.Dropout(cfg["dropout"])

        def forward(self, h):
            B, T, _ = h.shape
            q, k, v = self.qkv(self.n1(h)).view(B, T, 3, H, d // H).permute(2, 0, 3, 1, 4)
            a = F.scaled_dot_product_attention(_rope(q), _rope(k), v,
                                               dropout_p=cfg.get("attn_dropout", 0.0) if self.training else 0.0)
            h = h + self.drop(self.proj(a.transpose(1, 2).reshape(B, T, d)))
            return h + self.drop(self.ff(self.n2(h)))

    class Mapper(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.ModuleList(nn.Embedding(K, d) for _ in range(N_IN))
            kk = cfg["conv_kernel"]
            self.front = nn.ModuleList(nn.Sequential(nn.Conv1d(d, d, kk, padding=kk // 2), nn.GELU(),
                                                     nn.Conv1d(d, d, kk, padding=kk // 2))
                                       for _ in range(2))
            self.blocks = nn.ModuleList(Block() for _ in range(cfg["layers"]))
            self.norm = nn.LayerNorm(d)
            self.head = nn.Linear(d, N_OUT * K)

        def forward(self, codes):
            """codes (B, 9, T) int64 -> logits (B, 4, T, 1024)."""
            h = sum(e(codes[:, i]) for i, e in enumerate(self.emb)) / math.sqrt(N_IN)
            h = h.transpose(1, 2)
            for f in self.front:
                h = h + f(h)
            h = h.transpose(1, 2)
            for b in self.blocks:
                h = b(h)
            B, T, _ = h.shape
            return self.head(self.norm(h)).view(B, T, N_OUT, K).permute(0, 2, 1, 3)

    return Mapper()


def ce_loss(logits, y, weights=CFG["codebook_weights"]):
    """Summed (weighted) per-codebook cross-entropy, and the per-codebook values."""
    import torch.nn.functional as F

    per = [F.cross_entropy(logits[:, i].reshape(-1, K), y[:, i].reshape(-1)) for i in range(N_OUT)]
    return sum(w * p for w, p in zip(weights, per)), per


def load_net(path, device="cpu"):
    import torch

    state = torch.load(path, map_location=device, weights_only=False)
    net = build_model(state.get("cfg", CFG)).to(device)
    net.load_state_dict(state["model"])
    return net.eval()


# --- data ----------------------------------------------------------------------------------

def load_data(partial=False):
    """(Xtr, Ytr, Xva, Yva, gva) from the shards in index order, int16: training clips whole,
    X (n, 9, 517) and Y (n, 4, 517), for fresh crops each step (`random_crops`); validation
    clips at their fixed centred crop (frame 129), X (n, 9, 258) and Y (n, 4, 258); gva the
    validation clips' global row indices."""
    import numpy as np

    idx = json.loads((CODES / "index.json").read_text())
    rows = idx["rows"]
    have = [k for k in range(idx["shards"]) if (CODES / f"codes/shard-{k:05d}.npz").exists()]
    if len(have) < idx["shards"] and not partial:
        raise SystemExit(f"only {len(have)}/{idx['shards']} shards encoded; wait for the encoder")
    Xtr, Ytr, Xva, Yva, gva = [], [], [], [], []
    for k in have:
        z = np.load(CODES / f"codes/shard-{k:05d}.npz")
        part = rows[k * idx["shard_size"]:(k + 1) * idx["shard_size"]]
        assert [e["g"] for e in part] == z["g"].tolist(), f"shard {k} out of order"
        zx, zy, cs = z["x"], z["y"], z["crop_start"]
        assert zx.shape[-1] == FRAMES and zy.shape[-1] == FRAMES
        for i, e in enumerate(part):
            if e["train"]:
                Xtr.append(zx[i].copy())
                Ytr.append(zy[i, :N_OUT].copy())
            else:
                f = crop_frame(int(cs[i]))
                assert f == VAL_FRAME, f"validation crop at frame {f}"
                Xva.append(zx[i, :, f:f + CROP_FRAMES].copy())
                Yva.append(zy[i, :N_OUT, f:f + CROP_FRAMES].copy())
                gva.append(e["g"])
    return np.stack(Xtr), np.stack(Ytr), np.stack(Xva), np.stack(Yva), np.array(gva)


def unigram_ce(Ytr, Yva):
    """Validation cross-entropy of per-codebook code frequencies from training (a floor any
    useful mapper must beat), summed over the 4 codebooks."""
    import numpy as np

    tot = 0.0
    for i in range(N_OUT):
        p = (np.bincount(Ytr[:, i].ravel(), minlength=K) + 1.0)
        p /= p.sum()
        tot += float(-np.log(p[Yva[:, i].ravel()]).mean())
    return tot


# --- MPS against CPU -----------------------------------------------------------------------

def mps_check(state, x, y, cfg=CFG, devices=("cpu", "mps")):
    """Same weights and batch (dropout off) on CPU and MPS: logits, loss and every parameter's
    gradient. Returns the report; `ok` False means don't train."""
    import torch

    out = {}
    res = {}
    for dev, key in zip(devices, ("cpu", "mps")):
        net = build_model(cfg).to(dev)
        net.load_state_dict(state)
        net.eval()
        logits = net(x.to(dev))
        loss, _ = ce_loss(logits, y.to(dev))
        net.zero_grad()
        loss.backward()
        res[key] = (logits.detach().cpu(), float(loss.detach()),
                    {n: q.grad.detach().cpu() for n, q in net.named_parameters() if q.grad is not None})
    (lc, Lc, gc), (lm, Lm, gm) = res["cpu"], res["mps"]
    out["logits_rel"] = float((lc - lm).norm() / lc.norm())
    out["loss_rel"] = abs(Lc - Lm) / abs(Lc)
    worst_cos, worst_rel, bad = 1.0, 0.0, []
    for n, a in gc.items():
        b = gm.get(n)
        if b is None or not torch.isfinite(b).all():
            bad.append(n)
            continue
        na, nb = float(a.norm()), float(b.norm())
        if na == 0 and nb == 0:
            continue
        cos = float((a.flatten() @ b.flatten()) / (na * nb + 1e-30))
        rel = abs(na - nb) / max(na, 1e-30)
        worst_cos, worst_rel = min(worst_cos, cos), max(worst_rel, rel)
        if not (cos > 0.999 and rel < 1e-3):
            bad.append(n)
    out.update(params=len(gc), worst_cos=worst_cos, worst_rel_norm=worst_rel, bad=bad[:10],
               shape=list(x.shape))
    out["ok"] = out["logits_rel"] < 1e-4 and out["loss_rel"] < 1e-5 and not bad
    return out


# --- training ------------------------------------------------------------------------------

def _lr(step, cfg=CFG):
    if step < cfg["warmup"]:
        return cfg["lr"] * (step + 1) / cfg["warmup"]
    frac = min(1.0, (step - cfg["warmup"]) / max(1, cfg["max_steps"] - cfg["warmup"]))
    return cfg["lr_end"] + 0.5 * (cfg["lr"] - cfg["lr_end"]) * (1 + math.cos(math.pi * frac))


def _optimiser(net, cfg=CFG):
    import torch

    decay = [q for n, q in net.named_parameters() if q.dim() >= 2 and not n.startswith("emb.")]
    rest = [q for n, q in net.named_parameters() if not (q.dim() >= 2 and not n.startswith("emb."))]
    return torch.optim.AdamW([{"params": decay, "weight_decay": cfg["weight_decay"]},
                              {"params": rest, "weight_decay": 0.0}], lr=cfg["lr"], betas=cfg["betas"])


def validate(net, Xva, Yva, dev, batch=64):
    import numpy as np
    import torch

    net.eval()
    tot, per, acc, n = 0.0, np.zeros(N_OUT), np.zeros(N_OUT), 0
    with torch.no_grad():
        for s in range(0, len(Xva), batch):
            x = torch.from_numpy(Xva[s:s + batch].astype(np.int64)).to(dev)
            y = torch.from_numpy(Yva[s:s + batch].astype(np.int64)).to(dev)
            lg = net(x)
            loss, p = ce_loss(lg, y)
            m = len(x)
            tot += float(loss) * m
            per += np.array([float(v) for v in p]) * m
            acc += (lg.argmax(-1) == y).float().mean(dim=(0, 2)).cpu().numpy() * m
            n += m
    net.train()
    return tot / n, (per / n).tolist(), (acc / n).tolist()


def _save(obj, path):
    """torch.save to a temporary file, then os.replace: a crash never leaves a torn checkpoint."""
    import torch

    tmp = path.with_name(path.name + ".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)


def _mps_rng(dev):
    import torch

    if dev.type == "mps" and hasattr(torch, "mps") and hasattr(torch.mps, "get_rng_state"):
        return torch.mps.get_rng_state()
    return None


def train(out=RUN / "model", partial=False, device=None, cfg=CFG, max_steps=None):
    import numpy as np
    import torch

    max_steps = max_steps or cfg["max_steps"]
    dev = torch.device(device or ("mps" if torch.backends.mps.is_available() else "cpu"))
    out.mkdir(parents=True, exist_ok=True)
    if (out / "DONE").exists():
        raise SystemExit(f"{out} is finished ({(out / 'DONE').read_text().strip()})")
    log = open(out / "log.jsonl", "a")

    def note(**kw):
        kw["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        print(json.dumps(kw), flush=True)
        log.write(json.dumps(kw) + "\n")
        log.flush()

    t_load = time.time()
    Xtr, Ytr, Xva, Yva, _ = load_data(partial)
    note(event="data", train=len(Xtr), validation=len(Xva), seconds=round(time.time() - t_load, 1),
         unigram_val_ce=round(unigram_ce(Ytr, Yva), 4), device=str(dev), cfg=cfg)
    torch.manual_seed(cfg["seed"])
    rng = np.random.default_rng(cfg["seed"])
    net = build_model(cfg).to(dev)
    note(event="model", parameters=sum(q.numel() for q in net.parameters()))
    opt = _optimiser(net, cfg)
    step, best, bad_evals, skipped = 0, float("inf"), 0, 0
    if (out / "last.pt").exists():
        st = torch.load(out / "last.pt", map_location=dev, weights_only=False)
        net.load_state_dict(st["model"])
        opt.load_state_dict(st["opt"])
        rng.bit_generator.state = st["rng"]
        torch.set_rng_state(st["torch_rng"])
        if st.get("mps_rng") is not None and dev.type == "mps":
            torch.mps.set_rng_state(st["mps_rng"])
        step, best, bad_evals, skipped = st["step"], st["best"], st["bad_evals"], st["skipped"]
        note(event="resumed", step=step, best=best)

    def batch(ix, r):
        x, y = random_crops(Xtr, Ytr, ix, r)
        return (torch.from_numpy(x.astype(np.int64)).to(dev),
                torch.from_numpy(y.astype(np.int64)).to(dev))

    def check(tag):
        """At the training batch size and crop length; its own rng, so training's is untouched."""
        if dev.type != "mps":
            return
        r = np.random.default_rng(12345)
        cx, cy = batch(r.choice(len(Xtr), cfg["batch"], replace=False), r)
        cpu_state = {k: v.detach().cpu() for k, v in net.state_dict().items()}
        r = mps_check(cpu_state, cx.cpu(), cy.cpu(), cfg)
        (out / f"mps-check-{tag}.json").write_text(json.dumps(r, indent=1))
        note(event="mps_check", tag=tag, **r)
        if not r["ok"]:
            raise SystemExit(f"MPS against CPU check failed ({tag}); not training on MPS")

    if step == 0:
        check("start")
    net.train()
    t0, s0 = time.time(), step
    while step < max_steps:
        for g in opt.param_groups:
            g["lr"] = _lr(step, cfg)
        x, y = batch(rng.choice(len(Xtr), cfg["batch"], replace=False), rng)
        loss, _ = ce_loss(net(x), y)
        opt.zero_grad()
        loss.backward()
        grads = [q.grad for q in net.parameters() if q.grad is not None]
        total = torch.sqrt(sum((g.detach() ** 2).sum() for g in grads))
        if not torch.isfinite(total):
            skipped += 1
            if skipped > 200:
                raise RuntimeError("too many non-finite gradients")
            continue
        if total > cfg["clip"]:
            for g in grads:
                g.mul_(cfg["clip"] / total)
        opt.step()
        step += 1
        if step == 200 and s0 < 200:
            check("step200")
        if step % cfg["eval_every"] == 0 or step == max_steps:
            vl, per, acc = validate(net, Xva, Yva, dev)
            improved = vl < best - cfg["min_delta"]
            if improved:
                best, bad_evals = vl, 0
                _save({"model": net.state_dict(), "cfg": cfg, "step": step, "val": vl}, out / "best.pt")
            else:
                bad_evals += 1
            el = time.time() - t0
            note(event="eval", step=step, train=round(float(loss.detach()), 4), val=round(vl, 4),
                 val_per_codebook=[round(v, 4) for v in per], val_acc=[round(v, 4) for v in acc],
                 lr=_lr(step, cfg), best=round(best, 4), bad_evals=bad_evals, skipped=skipped,
                 s_per_step=round(el / max(1, step - s0), 4))
            _save({"model": net.state_dict(), "opt": opt.state_dict(), "rng": rng.bit_generator.state,
                   "torch_rng": torch.get_rng_state(), "mps_rng": _mps_rng(dev), "step": step,
                   "best": best, "bad_evals": bad_evals, "skipped": skipped, "cfg": cfg}, out / "last.pt")
            if bad_evals >= cfg["patience"]:
                note(event="early_stop", step=step, best=best)
                break
    reason = "early stop" if bad_evals >= cfg["patience"] else f"{step} steps"
    (out / "DONE").write_text(f"{reason}, best val {best:.4f}\n")
    note(event="done", reason=reason, best=best)


def bench(device="cpu", steps=10, cfg=CFG):
    """Seconds per training step on random codes (no data needed)."""
    import torch

    dev = torch.device(device)
    torch.manual_seed(0)
    net = build_model(cfg).to(dev)
    opt = _optimiser(net, cfg)
    x = torch.randint(0, K, (cfg["batch"], N_IN, CROP_FRAMES), device=dev)
    y = torch.randint(0, K, (cfg["batch"], N_OUT, CROP_FRAMES), device=dev)
    times = []
    for i in range(steps + 2):
        t = time.time()
        loss, _ = ce_loss(net(x), y)
        opt.zero_grad()
        loss.backward()
        opt.step()
        float(loss.detach())           # sync
        times.append(time.time() - t)
    r = {"device": device, "parameters": sum(q.numel() for q in net.parameters()),
         "s_per_step": round(statistics.median(times[2:]), 4), "batch": cfg["batch"]}
    print(json.dumps(r))
    return r


# --- rebuild -------------------------------------------------------------------------------

def map_codes(net, codes, cfg=CFG):
    """(9, n) recording codes -> (4, n) int16 DI codes: windowed, crossfaded, argmax."""
    import numpy as np
    import torch

    dev = next(net.parameters()).device
    c = torch.from_numpy(np.asarray(codes, np.int64))[None].to(dev)

    def fn(s, L):
        with torch.no_grad():
            return torch.log_softmax(net(c[:, :, s:s + L])[0].float(), -1).cpu().numpy()

    return stitch(c.shape[-1], cfg["window"], cfg["window_hop"], fn).argmax(-1).astype(np.int16)


def _codec(cmd, work, device="cpu"):
    subprocess.run([str(DAC_PY), str(CODEC), cmd, str(work), device], check=True)


def decode_many(preds, work, lengths48, device="cpu"):
    """{name: (4, n) codes} -> {name: 48-kHz float64 at −22.9 LUFS, cut/padded to lengths48}."""
    import numpy as np
    from scipy.signal import resample_poly

    from learn.direc_check import to_lufs

    work.mkdir(parents=True, exist_ok=True)
    for name, p in preds.items():
        np.save(work / f"{name}.pred.npy", p)
        (work / f"{name}.out44.npy").unlink(missing_ok=True)       # never reuse a stale decode
    _codec("decode", work, device)
    out = {}
    for name in preds:
        y = resample_poly(np.load(work / f"{name}.out44.npy").astype(np.float64), 160, 147)
        n = lengths48[name]
        y = np.pad(y, (0, max(0, n - len(y))))[:n]
        out[name] = to_lufs(y)
    return out


def rebuild_many(net, recs, work, device="cpu"):
    """{name: 48-kHz mono recording} -> {name: rebuilt DI, 48 kHz, −22.9 LUFS}. `work` keeps the
    intermediate files (44.1-kHz input, codes, predicted codes, decoded audio)."""
    import numpy as np
    from scipy.signal import resample_poly

    work.mkdir(parents=True, exist_ok=True)
    for name, x in recs.items():
        np.save(work / f"{name}.in44.npy", resample_poly(np.asarray(x, np.float64), 147, 160).astype(np.float32))
        (work / f"{name}.codes.npy").unlink(missing_ok=True)
    _codec("encode", work, device)
    preds = {name: map_codes(net, np.load(work / f"{name}.codes.npy")) for name in recs}
    return decode_many(preds, work, {name: len(x) for name, x in recs.items()}, device)


def rebuild(net, x, work=None):
    """One recording (e.g. a 10-s crop, 48 kHz mono) -> its rebuilt DI (48 kHz, −22.9 LUFS)."""
    import tempfile

    if work is None:
        with tempfile.TemporaryDirectory() as t:
            return rebuild_many(net, {"x": x}, pathlib.Path(t))["x"]
    return rebuild_many(net, {"x": x}, work)["x"]


# --- evaluation ----------------------------------------------------------------------------

EVAL = RUN / "eval"


def _net(which="best"):
    return load_net(RUN / f"model/{which}.pt", "cpu")


def cprime_vidx():
    """C′'s validation sample in `fit` (seed 0): rng.choice(va, 96) with va the fold-2 global
    rows; nothing draws from fit's rng before it."""
    import numpy as np

    idx = json.loads((CODES / "index.json").read_text())
    va = np.array(sorted(e["g"] for e in idx["rows"] if e["pass"] == 0 and e["fold"] == FOLD))
    return np.random.default_rng(0).choice(va, min(96, len(va)), replace=False)


def precheck1():
    """Decoded mel on C′'s 96 validation clips: E1 against C′ seed 0, same crop, level and mel.
    E1 at `best.pt` (gated) and at `last.pt` (its final weights, as C′'s are; reported only)."""
    import numpy as np
    import torch

    from learn import direc as D
    from learn import egvae_e1_data as ED
    from learn.direc_check import to_lufs

    idx = json.loads((CODES / "index.json").read_text())
    by_g = {e["g"]: e for e in idx["rows"] if e["pass"] == 0}
    vidx = [int(g) for g in cprime_vidx()]
    mm = {"pr12": (np.load(DIREC / "cache/input.npy", mmap_mode="r"), np.load(DIREC / "cache/di.npy", mmap_mode="r"))}
    S = {name: np.load(DIREC / cache / "di_spectrum.npy", mmap_mode="r") for name, cache, _ in ED.SOURCES}
    pairs = {name: DIREC / p for name, _, p in ED.SOURCES if p}
    avg = D.fold_average(DIREC / "cache", FOLD)
    nets, cp = {"e1": _net("best"), "e1_last": _net("last")}, D.load_model(CPRIME0).eval()
    a0 = (D.CLIP - D.CROP) // 2
    preds, clips = {k: {} for k in nets}, {}
    for g in vidx:
        e = by_g[g]
        z = np.load(CODES / f"codes/shard-{e['shard']:05d}.npz")
        assert int(z["g"][e["slot"]]) == g and not e["train"]
        if e["source"] == "pr12":
            x16, y16 = (np.asarray(a[e["row"]]) for a in mm["pr12"])
        else:
            x16, y16 = ED.pair_int16(pairs[e["source"]], e["id"])
        x, y, a = D.make_clip(x16, y16, S[e["source"]][e["row"]], avg, np.random.default_rng(e["seed"]), False, None)
        assert a == a0 and int(z["crop_start"][e["slot"]]) == a0
        clips[g] = (x, y)
        for k, net in nets.items():
            preds[k][f"v{g:06d}"] = map_codes(net, z["x"][e["slot"]])
    dec = {k: decode_many(preds[k], EVAL / "precheck1" / f"codec-{k}", {n: D.CLIP for n in preds[k]})
           for k in nets}
    res = {}
    for kind in ("e1", "e1_last", "cp"):
        for g, (x, y) in clips.items():
            d = EVAL / "precheck1" / kind / f"v{g:06d}"
            d.mkdir(parents=True, exist_ok=True)
            if kind in dec:
                est = dec[kind][f"v{g:06d}"]
            else:
                est = D.rebuild(cp, x, device=torch.device("cpu")).astype(np.float64)
            np.save(d / "di.npy", to_lufs(est[a0:a0 + D.CROP]).astype(np.float32))
            np.save(d / "true.npy", to_lufs(y[a0:a0 + D.CROP].astype(np.float64)).astype(np.float32))
        subprocess.run([str(DAC_PY), str(PLUGIN_ROOT / "learn/egvae_e0_dac.py"), "mel",
                        str(EVAL / "precheck1" / kind)], check=True)
        mel = json.loads((EVAL / "precheck1" / kind / "mel.json").read_text())
        res[kind] = {"mean": statistics.fmean(mel.values()), "median": statistics.median(mel.values()), "n": len(mel)}
    res["pass"] = res["e1"]["mean"] <= res["cp"]["mean"]               # gated on best.pt, as declared
    res["pass_at_last"] = res["e1_last"]["mean"] <= res["cp"]["mean"]  # final weights; reported only
    res["checkpoints"] = {"e1": "best.pt", "e1_last": "last.pt"}
    (EVAL / "precheck1.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return res


def precheck2():
    """Rebuild the 18 development parts (kept for rendering); coherence and lag against the
    true DI exactly as `residual_eval.coherence`."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import phase2_set3 as P
    from learn import residual_eval as RE

    ps = RE.parts()
    recs = {s: CR.mono(pathlib.Path(p["crop"]) / "reference.wav") for s, p in sorted(ps.items())}
    dis = rebuild_many(_net(), recs, EVAL / "parts-codec")
    rows, lags = {}, {}
    for s, di_hat in dis.items():
        d = EVAL / "parts" / s
        d.mkdir(parents=True, exist_ok=True)
        np.save(d / "di.npy", di_hat)
        di = CR.mono(pathlib.Path(ps[s]["crop"]) / "di.wav")
        hint = ps[s]["judge_lag"] + P.LATENCY
        try:
            a, b, k = RE._aligned(di_hat, di, hint)
            lags[s] = int(k - hint)
        except ValueError:          # no correlation peak within ±50 ms: score at the hint, lag None
            n = min(len(di_hat), len(di))
            a, b = (di_hat[hint:n], di[:n - hint]) if hint >= 0 else (di_hat[:n + hint], di[-hint:n])
            lags[s] = None
        rows[s] = RE._coherence(a, b)
    med = [round(float(np.median([c[i] for c in rows.values()])), 4) for i in range(3)]
    res = {"median_80_1k_1_3k_3_8k": med, "bar_80_1k": COHERENCE_BAR, "pass": med[0] >= COHERENCE_BAR,
           "misalignment_median": (float(np.median([v for v in lags.values() if v is not None]))
                                   if any(v is not None for v in lags.values()) else None),
           "no_lag_found": sorted(s for s, v in lags.items() if v is None), "misalignment": lags,
           "per_part": {s: [round(c, 4) for c in v] for s, v in rows.items()}}
    (EVAL / "precheck2.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "per_part"}))
    return res


def render(shard):
    import numpy as np

    from learn import egvae_e0 as E0
    from learn import residual_eval as RE

    assert shard[1] <= 3, "at most 3 renderer processes"
    R = E0._Renderer()
    try:
        for s in sorted(RE.parts())[shard[0]::shard[1]]:
            base = EVAL / "parts" / s
            if not (base / "done").exists():
                R.run(np.load(base / "di.npy"), base)
                print(s, flush=True)
    finally:
        R.r.close()


def _score_part(job):
    import numpy as np

    import render_preset_panel as RP
    from learn import confirm_run as CR
    from learn import phase2_set3 as P
    from learn.rebuilt_judge import rebuilt_distance

    slug, crop, names = job
    ref = CR.mono(pathlib.Path(crop) / "reference.wav")
    d = EVAL / "parts" / slug
    di = np.load(d / "di.npy")
    res = {}
    for amp, ns in names.items():
        for n in ns:
            y = P.mono(d / amp / f"{RP._slug(n)}.flac")
            for h, (a, b) in (("A", P.HALF_A), ("B", P.HALF_B)):
                x, proxy = rebuilt_distance(ref, y, di, start_s=a, end_s=b)
                res.setdefault(f"E1|{amp}|{h}", {})[n] = (x.distance, proxy)
    print(slug, flush=True)
    return slug, res


def score(workers=6):
    from concurrent.futures import ProcessPoolExecutor

    from learn import residual_eval as RE
    from learn import set3_gap_split as G

    ps, names = RE.parts(), G.menu_names()
    missing = [s for s in ps if not (EVAL / "parts" / s / "done").exists()]
    if missing:
        raise SystemExit(f"missing renders: {missing}")
    with ProcessPoolExecutor(workers) as ex:
        R = dict(ex.map(_score_part, [(s, str(ps[s]["crop"]), names) for s in sorted(ps)]))
    (EVAL / "distances.json").write_text(json.dumps(R))


def _pick(row):
    row = {n: v[0] for n, v in row.items() if v[0]}
    return min(row, key=lambda n: (row[n], n)) if row else None


def cell_ratio(per, a, b):
    """`set5_test.evaluate`'s per-cell averaging: per half, the mean over the (a, b) kind pairs
    of log(a / b); then the mean of the two halves. None if any value is missing."""
    a = a if isinstance(a, tuple) else (a,)
    b = b if isinstance(b, tuple) else (b,)
    vals = []
    for i in range(2):
        xs = [per[k][i] for k in a + b]
        if not all(xs):
            return None
        vals.append(statistics.fmean(math.log(per[p][i] / per[q][i]) for p in a for q in b))
    return statistics.fmean(vals)


def report():
    from learn import phase2_set3 as P
    from learn import residual_eval as RE
    from learn import set5_test as S5
    from learn import sound_desc_eval as E

    ps = RE.parts()
    tp = {s: v for s, v in E.test_parts().items() if s in json.loads(RE.PINNED.read_text())["parts"]}
    D = {s: tp[s]["D"] for s in tp}
    R1 = json.loads((EVAL / "distances.json").read_text())
    Rres = json.loads((RE.OUT / "distances.json").read_text())       # C′ seeds 0 ("Cp") and 1 ("Cp1")

    def mean_halves(s, amp, n):
        a, b = D[s][f"flat|{amp}|measfix_A"][n][0], D[s][f"flat|{amp}|measfix_B"][n][0]
        return (a + b) / 2 if a and b else None

    def lbo_baseline(slug, amp):          # verbatim from residual_eval.report
        cls, band = tp[slug]["gain_class"], tp[slug]["band"]
        others = [s for s in tp if tp[s]["gain_class"] == cls and tp[s]["band"] != band]
        meds = {}
        for n in [n for n in D[slug][f"flat|{amp}|measfix_A"] if n.startswith("factory:")]:
            v = [mean_halves(s, amp, n) for s in others]
            if v and all(x is not None for x in v):
                meds[n] = statistics.median(v)
        return min(meds, key=lambda n: (meds[n], n))

    cells, agree = {}, []
    for s in ps:
        for amp in P.AMPS:
            per, ok = {}, True
            base = lbo_baseline(s, amp)
            for h, other in (("A", "B"), ("B", "A")):
                M = D[s][f"flat|{amp}|measfix_{other}"]
                picks = {"E1": _pick(R1[s][f"E1|{amp}|{h}"]), "Cp0": _pick(Rres[s][f"Cp|{amp}|{h}"]),
                         "Cp1": _pick(Rres[s][f"Cp1|{amp}|{h}"]),
                         "oracle": _pick(D[s][f"flat|{amp}|measfix_{h}"]), "base": base}
                agree.append(picks["E1"] == picks["oracle"])
                for k, n in picks.items():
                    v = M[n][0] if n and M.get(n) and M[n][0] else None
                    ok = ok and v is not None
                    per.setdefault(k, []).append(v)
            if ok:                                   # one common set of cells, as set5_test.evaluate
                cells[(s, amp)] = per

    seeds = ("Cp0", "Cp1")

    def rows(a, b, cls=None):
        out = []
        for (s, amp), per in cells.items():
            if cls and ps[s]["gain_class"] != cls:
                continue
            x = cell_ratio(per, a, b)
            if x is not None:
                out.append((ps[s]["band"], x))
        return out

    res = {}
    for tag, cls in (("all", None), ("clean", "clean"), ("crunch", "crunch")):
        for name, a, b in (("E1_vs_Cp", "E1", seeds), ("E1_vs_base", "E1", "base"),
                           ("Cp_vs_base", seeds, "base"), ("oracle_vs_base", "oracle", "base"),
                           ("E1_vs_oracle", "E1", "oracle"), ("E1_vs_Cp0", "E1", "Cp0"),
                           ("E1_vs_Cp1", "E1", "Cp1"), ("Cp0_vs_base", "Cp0", "base"),
                           ("Cp1_vs_base", "Cp1", "base")):
            res[f"{name}|{tag}"] = S5._band_gate(rows(a, b, cls))
    gate = res["E1_vs_Cp|all"]
    pre = {k: json.loads((EVAL / f"{k}.json").read_text()) if (EVAL / f"{k}.json").exists() else None
           for k in ("precheck1", "precheck2")}
    pre_ok = all(v and v["pass"] for v in pre.values())
    qualifies = bool(pre_ok and gate.get("band_mean", 1) <= SET5_BAND_MEAN and gate.get("hi90", 1) < SET5_HI90)
    cp, e1, orc = (res[f"{k}|all"].get("band_mean") for k in ("Cp_vs_base", "E1_vs_base", "oracle_vs_base"))
    out = {
        "experiment": "EG-VAE-lite E1: DAC codes-to-codes mapper, 4 codebooks (docs/egvae-lite-plan.md)",
        "network": str(RUN / "model/best.pt"), "cells": len(cells), "seeds_compared": list(seeds),
        "gate_E1_vs_Cp": gate,
        "prechecks": {k: (None if v is None else {kk: vv for kk, vv in v.items()
                                                  if kk not in ("per_part", "misalignment")})
                      for k, v in pre.items()},
        "set5_rule": {"band_mean_max": SET5_BAND_MEAN, "hi90_max": SET5_HI90, "prechecks_pass": pre_ok,
                      "qualifies": qualifies},
        "share_of_Cp_to_oracle_gap_closed": (round((cp - e1) / (cp - orc), 3)
                                              if None not in (cp, e1, orc) and cp != orc else None),
        "picks_same_as_oracle": round(sum(agree) / len(agree), 3),
        "results": res,
    }
    RESULT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print("GATE E1 vs C′ (seeds 0, 1):", gate.get("outcome"),
          {k: gate.get(k) for k in ("band_mean", "lo90", "hi90", "bands_negative", "bands")})
    print("set-5 rule:", out["set5_rule"])
    for k, v in res.items():
        if "band_mean" in v:
            print(f"  {k:24s} band {v['band_mean']:+.4f} [{v['lo90']:+.4f}, {v['hi90']:+.4f}] "
                  f"part {v['part_weighted']:+.4f} neg {v['bands_negative']}/{v['bands']} {v['outcome']}")
    return out


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "train":
        train(partial="--partial" in args, device=os.environ.get("E1_DEVICE"))
    elif cmd == "bench":
        bench(*(args[:1] or ["cpu"]), *(int(a) for a in args[1:2]))
    elif cmd == "render":
        render((int(args[0]), int(args[1])))
    else:
        {"precheck1": precheck1, "precheck2": precheck2, "score": score, "report": report}[cmd]()
