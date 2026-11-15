"""S4's training (`docs/separation-plan.md`, ledger `separation` `phase_s4`): the MDX23C phantom-centre model in
`steer_xlmdxc`'s tail, fine-tuned on X-LANCE's output of steered training mixes. X-LANCE stays as it is.

- **s4-cache** (msst-venv, CPU or MPS, X-LANCE frozen): N_DRAWS fixed training draws by S3's recipe
  (`sep_s3_train.build_draw`, the whole 10 s: the same strata, jittered hint, dropped targets and mastering), each
  stored as X-LANCE's steered stereo output and the steered target (float16). Training bands only.
- **s4-val** (msst-venv, CPU): X-LANCE's output on S3's 200 fixed validation mixes, as `steer_xlmdxc` makes it.
- **s4-check** (msst-venv): the gradient check (one batch on MPS against the CPU, per parameter tensor, at the
  training crop) and the speed per batch size. The run goes on MPS only if the median relative error is < 1e-3 and
  the largest < 1e-2. Also checks that the spectral forward, inverted, is the model's own output.
- **s4-train** (msst-venv, MPS): crops of the model's own chunk (130,560 samples) from the cache, where the target
  plays; the loss is L1 on the model's output spectrogram against the target's (the model's own STFT), so no inverse
  STFT is differentiated. AdamW 1e-5, 500 warm-up steps, fp32, all parameters, no weight decay, a hand clip at norm
  1.0, non-finite steps skipped (S3's reload and abort rule). Validation every 1,000 steps on the 136 non-double
  validation mixes (the rule's strata): the median SI-SDR and the model's read; step 0 is the model as it is (the
  chain itself) and the first best. A new best needs a read at least 0.002 lower than the best's, with the median
  SI-SDR no lower than step 0's. It stops after 5 evaluations without one, the abort rule, or 48 h.
- **s4-pick** (after the stop): `run/pick.json` names best.pt with its sha256.
- **s4-apply** (msst-venv): on the held-out bands' items of a set: steer by the coarse hint, X-LANCE (CPU), the
  fine-tuned MDX23C, rotate back, average; 48 kHz stems in `stems/s4` with `stems/s4/pick.json`.

    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s4_train s4-cache --device mps|cpu [--k0 K --k1 K]
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s4_train s4-val
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s4_train s4-check
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s4_train s4-train --batch B --accum A
    .venv/bin/python -m learn.sep_s4_train s4-pick
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s4_train s4-apply --set main|split

The pure parts (the best rule, the stop check, the crop) are unit-tested.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time

from learn import sep_s0 as S0
from learn import sep_s3 as S3
from learn import sep_s3_train as TR

PHASE_S4 = "phase_s4"
SEED = 20261154
N_DRAWS = 2000
CROP = 130_560                    # the model's chunk_size: training crops are its inference chunks
LR, BETAS, WARMUP = 1e-5, (0.8, 0.99), 500
CLIP = 1.0
EVAL_EVERY, PATIENCE, MAX_HOURS = 1000, 5, 48.0
MIN_READ_GAIN = 0.002             # a new best's read under the best's by at least this
SI_FLOOR_DB = 0.0                 # and its median SI-SDR no lower than step 0's minus this
BAD_RELOAD, MAX_RELOADS = TR.BAD_RELOAD, TR.MAX_RELOADS
GRAD_MEDIAN, GRAD_MAX = TR.GRAD_MEDIAN, TR.GRAD_MAX
MIN_BATCH = 4
MIN_FREE_GB = 20.0                # the cache stops when the disk would fall under this


def out_dir():
    return S0.out_dir().parent / "s4"


# --- the pure parts -------------------------------------------------------------------------------------------------------

def is_better(ev, best, ev0, min_gain=MIN_READ_GAIN, si_floor=SI_FLOOR_DB):
    """A new best: a read at least `min_gain` under the best's, with the median SI-SDR no lower than step 0's minus
    `si_floor`. Each is {si_sdr_median, read}."""
    return ev["read"] <= best["read"] - min_gain and ev["si_sdr_median"] >= ev0["si_sdr_median"] - si_floor


def stop_reason(st, saved_at, user_stop=False):
    """How the run stopped by its own rule, judged from the state as saved (`saved_at`, state.json's mtime). -> a
    reason, or None while it hasn't stopped."""
    if len([e for e in st["evals"] if e["step"] > st["best_step"]]) >= PATIENCE:
        return "patience"
    if st.get("reloads", 0) > MAX_RELOADS:
        return "abort"
    if (saved_at - st["t_start"]) / 3600 > MAX_HOURS:
        return "hours"
    return "user" if user_stop else None


def crop_start(target_mid, input_mid, rng, silent, crop=CROP):
    """A crop where the target plays (S3's rule: its level within 20 dB of the model's input), or anywhere in a draw
    whose target was dropped."""
    n = len(input_mid)
    if silent:
        return rng.randrange(0, max(1, n - crop))
    return TR.pick_crop(target_mid, input_mid, rng, crop=crop, pre=0)


def paired_gain_lo90(base, new, n=2000, seed=SEED):
    """The paired item bootstrap's 5th percentile of the mean gain base - new (a read gain is a drop in cosine
    distance). Plain Python, so it is unit-tested without numpy."""
    if len(base) != len(new) or not base:
        raise ValueError("paired lists of equal, non-zero length")
    d = [b - a for b, a in zip(base, new)]
    rng = random.Random(f"{seed}|paired")
    ms = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(n))
    return ms[int(0.05 * n)]


def pick_verdict(st, n=2000):
    """s4-pick's gate before any held-out read: step 0 picked means S4 changed nothing ("not used"); else the pick's
    paired validation read gain over step 0 must be decided (lo90 > 0). -> (usable, lo90 or None)."""
    if st["best_step"] == 0:
        return False, None
    lo = paired_gain_lo90(st["ev0"]["reads"], st["best"]["reads"], n=n)
    return lo > 0, lo


def non_double(metas):
    """The validation mixes the curve reads: the rule's strata (the doubles are out of S3's rule, so out of S4's)."""
    return [k for k, m in enumerate(metas) if m.get("stratum") != "double"]


# --- the model ------------------------------------------------------------------------------------------------------------

def require_mps_free():
    """One MPS job at a time: S4's MPS steps wait until S3's run has stopped and been picked."""
    if not (TR.out_dir() / "run" / "pick.json").exists():
        raise SystemExit("S3's run hasn't stopped and been picked (run/pick.json): the MPS is S3's")


def load_centre(device):
    """The hash-checked MDX23C phantom-centre model (`stereo_side_screen.Centre`), trainable, on `device`. -> (model,
    config)."""
    from learn import stereo_side_screen as SSS

    c = SSS.Centre()
    c.config.inference.num_overlap = SSS.CENTRE_OVERLAP
    m = c.model.to(device)
    m.train()
    return m, c.config


def forward_spec(m, x):
    """TFC_TDF_net.forward up to its inverse STFT: the output spectrogram [b, 1, 4, dim_f, t]."""
    import torch

    x = m.stft(x)
    mix = x = m.cac2cws(x)
    first = x = m.first_conv(x)
    x = x.transpose(-1, -2)
    enc = []
    for block in m.encoder_blocks:
        x = block.tfc_tdf(x)
        enc.append(x)
        x = block.downscale(x)
    x = m.bottleneck_block(x)
    for block in m.decoder_blocks:
        x = block.upscale(x)
        x = torch.cat([x, enc.pop()], 1)
        x = block.tfc_tdf(x)
    x = x.transpose(-1, -2)
    x = x * first
    x = m.final_conv(torch.cat([mix, x], 1))
    x = m.cws2cac(x)
    b, c, f, t = x.shape
    return x.reshape(b, m.num_target_instruments, -1, f, t)


def spec_loss(m, x, y):
    """L1 between the model's output spectrogram and the target's (the model's own STFT, no gradient through it)."""
    import torch

    with torch.no_grad():
        ys = m.stft(y)
        ys = ys.reshape(ys.shape[0], 1, *ys.shape[1:])
    return (forward_spec(m, x) - ys).abs().mean()


def centre_run(m, config, st, device):
    """The model on a steered stereo stem [2, n] at 44.1 kHz (MSST's demix, the chain's overlap). -> [2, n]."""
    import sys

    import numpy as np
    import torch

    from learn import separator_screen as SCR

    repo = str(SCR.msst_root() / "repo")
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from utils.model_utils import demix

    with torch.no_grad():
        out = demix(config, m, np.ascontiguousarray(st, np.float32), torch.device(device), "mdx23c", pbar=False)
    return np.asarray(out["similarity"], np.float64)


# --- the cache ------------------------------------------------------------------------------------------------------------

def cmd_cache(args):
    import shutil

    import numpy as np

    from learn import direct_stems as DS
    from learn import trusted_data as T

    S3.require(PHASE_S4)
    if args.device == "mps":
        require_mps_free()
    pool = TR.Pool(val=False)
    order = list(pool.rows)                       # a seeded permutation, so the draws cover the examples
    random.Random(f"{SEED}|order").shuffle(order)
    bands = {r["band"] for r in pool.rows}
    if S3.VAL_BAND in bands or set(S3.HELD_BANDS) & bands:
        raise SystemExit("the validation or a held-out band in the training pool")
    d = out_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    sep = DS.stem_separator(T.SEP, args.device)
    n_done, t0 = 0, time.time()
    for k in range(args.k0, min(args.k1, N_DRAWS)):
        q = d / f"d_{k:05d}.npz"
        if q.exists():
            continue
        if shutil.disk_usage(d).free / 2 ** 30 < MIN_FREE_GB:
            raise SystemExit(f"under {MIN_FREE_GB} GB free: the cache stops at draw {k}")
        rng = random.Random(f"{SEED}|cache|{k}")
        x, y, phi, lay = TR.build_draw(pool, rng, full=True, row=order[k % len(order)])
        xl = np.asarray(DS.xl_run_chunked(sep._f, x), np.float32)
        np.savez(q.with_suffix(".tmp.npz"), xl=xl.astype(np.float16), y=y.astype(np.float16), phi=phi,
                 meta=json.dumps({"band": lay["band"], "i": lay["i"], "cls": lay["cls"], "stratum": lay["stratum"],
                                  "silent": lay["silent"]}))
        q.with_suffix(".tmp.npz").replace(q)
        n_done += 1
        if n_done % 25 == 0:
            print(f"s4-cache {k + 1}/{args.k1}: {time.time() - t0:.0f} s", flush=True)
    print(f"S4 CACHE DONE: {n_done} draws ({args.k0}-{args.k1})", flush=True)


def cmd_val(_args):
    import numpy as np

    from learn import direct_stems as DS
    from learn import trusted_data as T

    S3.require(PHASE_S4)
    z = np.load(TR.out_dir() / "val.npz")
    sep = DS.stem_separator(T.SEP, "cpu")
    xl = np.stack([np.asarray(DS.xl_run_chunked(sep._f, np.asarray(x, np.float32)), np.float32) for x in z["x"]])
    out_dir().mkdir(parents=True, exist_ok=True)
    np.savez(out_dir() / "val_xl.npz", xl=xl.astype(np.float16))
    print(f"S4 VAL DONE: {len(xl)} mixes", flush=True)


# --- the data -------------------------------------------------------------------------------------------------------------

try:                                             # module level, so spawned DataLoader workers can pickle it
    from torch.utils.data import IterableDataset as _Base
except ImportError:                              # CI without torch: the pure parts still import
    _Base = object


class Crops(_Base):
    """An endless stream of (input, target) batches cropped from the cache, seeded per worker and by the step a run
    resumes at."""

    def __init__(self, batch, seed, files):
        super().__init__()
        self.batch, self.seed, self.files = batch, seed, files

    def __iter__(self):
        import numpy as np
        import torch

        info = torch.utils.data.get_worker_info()
        wid = info.id if info else 0
        rng = random.Random(f"{SEED}|train|{self.seed}|{wid}")
        while True:
            xs, ys = [], []
            for _ in range(self.batch):
                z = np.load(rng.choice(self.files))
                meta = json.loads(str(z["meta"]))
                xl, y = np.asarray(z["xl"], np.float32), np.asarray(z["y"], np.float32)
                a = crop_start(y.mean(0), xl.mean(0), rng, meta["silent"])
                xs.append(xl[:, a:a + CROP])
                ys.append(y[:, a:a + CROP])
            yield torch.from_numpy(np.stack(xs)), torch.from_numpy(np.stack(ys))


def cache_files():
    fs = sorted((out_dir() / "cache").glob("d_*.npz"))
    if len(fs) < N_DRAWS:
        raise SystemExit(f"the cache holds {len(fs)} of {N_DRAWS} draws")
    return [str(f) for f in fs]


# --- the evaluation -------------------------------------------------------------------------------------------------------

def evaluate(m, config, device, nets, ks=None):
    """On the validation mixes `ks` (default: the 136 non-double ones): the median and mean SI-SDR (dB, 44.1 kHz) of
    the rotated-back mono estimate against the target's, and the model's read (mean cosine distance at 48 kHz, CPU),
    as S3's `evaluate`. -> {si_sdr_median, si_sdr_mean, read, n, ks, reads (per mix)}."""
    import numpy as np

    from learn import product_path as PP
    from learn import separator_screen as SCR

    z = np.load(TR.out_dir() / "val.npz")
    X, Y, P = z["x"], z["y"], z["phi"]            # each read once (an npz re-reads an array per access)
    xl = np.load(out_dir() / "val_xl.npz")["xl"]
    metas = json.loads((TR.out_dir() / "val.json").read_text())
    ks = non_double(metas) if ks is None else ks
    m.eval()
    si, rd = [], []
    for k in ks:
        phi = float(P[k])
        est = centre_run(m, config, np.asarray(xl[k], np.float32), device)
        e_m = TR.unsteer_mono(est, phi)
        r_m = TR.unsteer_mono(np.asarray(Y[k], np.float64), phi)
        m_m = TR.unsteer_mono(np.asarray(X[k], np.float64), phi)
        si.append(TR.si_sdr_t(e_m, r_m))
        n48 = int(round(len(m_m) * 48000 / TR.SR44))
        e8, r8, m8 = (SCR.to48(np.asarray(v, np.float64), n48) for v in (e_m, r_m, m_m))
        rd.append(PP.cosine_distance(S3.model_feats(nets, e8, m8, metas[k]["cls"]),
                                     S3.model_feats(nets, r8, m8, metas[k]["cls"])))
    m.train()
    return {"si_sdr_median": float(np.median(si)), "si_sdr_mean": float(np.mean(si)), "read": float(np.mean(rd)),
            "n": len(ks), "ks": list(ks), "reads": [float(v) for v in rd]}


# --- the checks -----------------------------------------------------------------------------------------------------------

def grad_compare(x, y):
    """One batch's gradients on the CPU and on MPS. -> S3's per-tensor relative errors."""
    import torch

    grads = {}
    for dev in ("cpu", "mps"):
        torch.manual_seed(0)
        m, _ = load_centre(dev)
        loss = spec_loss(m, x.to(dev), y.to(dev))
        loss.backward()
        grads[dev] = ({k: p.grad.detach().float().cpu() for k, p in m.named_parameters() if p.grad is not None},
                      float(loss.detach().cpu()), TR.grad_sq_norm(m))
        del m
    gc, lc, nc = grads["cpu"]
    gm, lm, nm = grads["mps"]
    norms = sorted(float(v.norm()) for v in gc.values())
    floor = 1e-3 * norms[len(norms) // 2]
    rel = {k: float((gm[k] - gc[k]).norm()) / max(float(gc[k].norm()), floor) for k in gc}
    vals = sorted(rel.values())
    return {"loss_cpu": lc, "loss_mps": lm, "grad_norm_cpu": math.sqrt(nc), "grad_norm_mps": math.sqrt(nm),
            "n_tensors": len(vals), "floor": floor, "rel_err_median": vals[len(vals) // 2], "rel_err_max": vals[-1],
            "worst": sorted(rel.items(), key=lambda t: -t[1])[:8]}


def cmd_check(args):
    import numpy as np
    import torch

    S3.require(PHASE_S4)
    require_mps_free()
    files = cache_files()
    ds = iter(Crops(args.grad_batch, -1, files))
    x, y = next(ds)
    rep = {}
    m, _ = load_centre("cpu")                     # the spectral forward, inverted, is the model's own output
    with torch.no_grad():
        a = m(x)
        b = m.stft.inverse(forward_spec(m, x))
    rep["forward_match_max_abs"] = float((a - b).abs().max())
    m = m.to("mps")                               # the full forward (inverse STFT included) on MPS against the CPU's
    with torch.no_grad():
        c = m(x.to("mps")).cpu()
    rep["mps_forward_max_abs"] = float((a - c).abs().max())
    rep["mps_forward_snr_db"] = float(10 * torch.log10((a ** 2).sum() / ((a - c) ** 2).sum().clamp_min(1e-30)))
    del m
    g = grad_compare(x, y)
    g["samples"], g["batch"] = CROP, args.grad_batch
    rep["crop"] = g
    rep["pass"] = bool(g["rel_err_median"] < GRAD_MEDIAN and g["rel_err_max"] < GRAD_MAX
                       and rep["forward_match_max_abs"] < 1e-4 and rep["mps_forward_snr_db"] > 60)
    print(f"S4 GRADIENT CHECK ({CROP} samples): loss cpu {g['loss_cpu']:.6f} mps {g['loss_mps']:.6f}; rel err median "
          f"{g['rel_err_median']:.2e} max {g['rel_err_max']:.2e}; forward match {rep['forward_match_max_abs']:.1e}; "
          f"MPS forward {rep['mps_forward_snr_db']:.0f} dB; "
          f"pass {rep['pass']}", flush=True)
    m, _ = load_centre("mps")
    opt = torch.optim.AdamW(m.parameters(), lr=LR, betas=BETAS, weight_decay=0.0)
    rep["params"] = sum(p.numel() for p in m.parameters())
    rep["speed"] = {}
    for bsz in args.batches:
        it = iter(Crops(bsz, -2, files))
        xb, yb = (t.to("mps") for t in next(it))
        try:
            for k in range(args.steps + 2):
                if k == 2:
                    torch.mps.synchronize()
                    t0 = time.time()
                opt.zero_grad()
                spec_loss(m, xb, yb).backward()
                opt.step()
            torch.mps.synchronize()
            dt = (time.time() - t0) / args.steps
            rep["speed"][bsz] = {"s_per_step": dt, "clips_per_s": bsz / dt,
                                 "mem_gb": torch.mps.driver_allocated_memory() / 2 ** 30}
            print(f"S4 SPEED batch {bsz}: {dt:.3f} s a step, {bsz / dt:.1f} clips/s, "
                  f"{rep['speed'][bsz]['mem_gb']:.1f} GB", flush=True)
        except RuntimeError as err:
            rep["speed"][bsz] = {"error": str(err)[:300]}
            print(f"S4 SPEED batch {bsz}: {str(err)[:200]}", flush=True)
            break
    out_dir().mkdir(parents=True, exist_ok=True)
    (out_dir() / "check.json").write_text(json.dumps(rep, indent=1))


# --- the training ---------------------------------------------------------------------------------------------------------

def cmd_train(args):
    import numpy as np
    import torch

    from learn import product_path as PP

    S3.require(PHASE_S4)
    if args.device == "mps":
        require_mps_free()
    d = out_dir() / "run"
    d.mkdir(parents=True, exist_ok=True)
    chk = json.loads((out_dir() / "check.json").read_text())
    if not chk["pass"] and args.device == "mps":
        raise SystemExit("the gradient check failed on MPS: not training there (the plan)")
    if args.batch * args.accum < MIN_BATCH:
        raise SystemExit(f"batch {args.batch} x accumulation {args.accum} < {MIN_BATCH} (the plan)")
    if args.device == "mps" and chk["crop"].get("batch") != args.batch:
        raise SystemExit(f"the gradient check ran at batch {chk['crop'].get('batch')}, not the training "
                         f"micro-batch {args.batch}: rerun s4-check --grad-batch {args.batch}")
    files = cache_files()
    nets, _, _ = PP._adopted()
    dev = torch.device(args.device)
    model, config = load_centre(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, betas=BETAS, weight_decay=0.0)
    st = {"step": 0, "best_step": 0, "best": None, "ev0": None, "evals": [], "reloads": 0, "t_start": time.time(),
          "skipped": 0, "batch": args.batch, "accum": args.accum}
    if (d / "last.pt").exists():
        ck = torch.load(d / "last.pt", map_location="cpu", weights_only=True)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        st = json.loads((d / "state.json").read_text())
        st["step"] = int(ck.get("step", st["step"]))
        if (st.get("batch", args.batch), st.get("accum", args.accum)) != (args.batch, args.accum):
            raise SystemExit("resumed with a different batch or accumulation than the run started with")
        print(f"resumed at step {st['step']}", flush=True)
    kw = {"persistent_workers": True, "prefetch_factor": 4} if args.workers > 0 else {}
    it = iter(torch.utils.data.DataLoader(Crops(args.batch, st["step"], files), batch_size=None,
                                          num_workers=args.workers, **kw))

    def save_last():
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "step": st["step"]}, d / "last.tmp")
        (d / "state.tmp").write_text(json.dumps(st, indent=1))
        (d / "last.tmp").replace(d / "last.pt")
        (d / "state.tmp").replace(d / "state.json")

    def line(ev):
        return (f"EVAL step {st['step']}: SI-SDR median {ev['si_sdr_median']:+.2f} mean {ev['si_sdr_mean']:+.2f} "
                f"read {ev['read']:.4f} (n {ev['n']}; best read {st['best']['read']:.4f} at {st['best_step']}; "
                f"step 0 {st['ev0']['si_sdr_median']:+.2f} / {st['ev0']['read']:.4f})")

    if not st["evals"]:                          # step 0: the model as it is (the chain itself), the first best
        ev = evaluate(model, config, args.device, nets)
        st["evals"].append({"step": 0, **ev, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        st["best"], st["ev0"] = ev, ev
        torch.save(model.state_dict(), d / "best.pt")
        save_last()
        print(line(ev), flush=True)
    bad, t_log, losses = 0, time.time(), []
    while True:
        hours = (time.time() - st["t_start"]) / 3600
        if hours > MAX_HOURS:
            print(f"S4 TRAIN STOP: {MAX_HOURS} h", flush=True)
            break
        lr = LR * min(1.0, (st["step"] + 1) / WARMUP)
        for g in opt.param_groups:
            g["lr"] = lr
        opt.zero_grad(set_to_none=True)
        lv, ok = 0.0, True
        for _ in range(args.accum):
            x, y = next(it)
            loss = spec_loss(model, x.to(dev), y.to(dev)) / args.accum
            li = float(loss.detach().cpu())
            if not math.isfinite(li):
                ok = False
                break
            loss.backward()
            lv += li
        if ok:
            sq = TR.grad_sq_norm(model)
            ok = math.isfinite(sq)
        if not ok:
            bad += 1
            st["skipped"] += 1
            if bad >= BAD_RELOAD:
                st["reloads"] += 1
                if st["reloads"] > MAX_RELOADS or not (d / "last.pt").exists():
                    print("S4 TRAIN ABORT: non-finite steps", flush=True)
                    break
                ck = torch.load(d / "last.pt", map_location="cpu", weights_only=True)
                model.load_state_dict(ck["model"])
                opt.load_state_dict(ck["opt"])
                st["step"] = int(ck.get("step", st["step"]))
                print(f"reloaded last.pt after {bad} bad steps (reload {st['reloads']})", flush=True)
                bad = 0
            continue
        bad = 0
        nrm = math.sqrt(sq)
        if nrm > CLIP:
            for p in model.parameters():
                if p.grad is not None:
                    p.grad.mul_(CLIP / (nrm + 1e-6))
        opt.step()
        st["step"] += 1
        losses.append(lv)
        if st["step"] % 50 == 0:
            dt = time.time() - t_log
            print(f"step {st['step']} loss {np.mean(losses):.5f} lr {lr:.1e} {50 / dt:.2f} steps/s "
                  f"skipped {st['skipped']} {hours:.1f} h", flush=True)
            t_log, losses = time.time(), []
        if st["step"] % EVAL_EVERY == 0:
            ev = evaluate(model, config, args.device, nets)
            st["evals"].append({"step": st["step"], **ev, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            if is_better(ev, st["best"], st["ev0"]):
                st["best"], st["best_step"] = ev, st["step"]
                torch.save(model.state_dict(), d / "best.tmp")
                (d / "best.tmp").replace(d / "best.pt")
            save_last()
            print(line(ev), flush=True)
            if len([e for e in st["evals"] if e["step"] > st["best_step"]]) >= PATIENCE:
                print(f"S4 TRAIN STOP: no new best in {PATIENCE} evaluations", flush=True)
                break
    save_last()
    print(f"S4 TRAIN DONE: step {st['step']}, best read {st['best']['read']:.4f} at {st['best_step']}", flush=True)


# --- after the stop -------------------------------------------------------------------------------------------------------

def cmd_pick(args):
    import hashlib

    S3.require(PHASE_S4)
    d = out_dir() / "run"
    st = json.loads((d / "state.json").read_text())
    why = stop_reason(st, (d / "state.json").stat().st_mtime, args.user_stop)
    if why is None:
        raise SystemExit("the run hasn't stopped by its rule yet (or pass --user-stop after the user stops it)")
    usable, lo = pick_verdict(st)
    out = {"step": st["best_step"], "path": str(d / "best.pt"),
           "sha256": hashlib.sha256((d / "best.pt").read_bytes()).hexdigest(),
           **{k: v for k, v in st["best"].items() if k not in ("ks", "reads")},
           "step0": {k: v for k, v in st["ev0"].items() if k not in ("ks", "reads")},
           "val_read_gain_lo90": lo, "usable": usable, "stop": why, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    (d / "pick.json").write_text(json.dumps(out, indent=1))
    print(f"S4 PICK: step {out['step']} (read {out['read']:.4f}, median {out['si_sdr_median']:+.2f}; step 0 "
          f"{st['ev0']['read']:.4f} / {st['ev0']['si_sdr_median']:+.2f}; paired read gain lo90 {lo}; stop {why}); "
          f"{'held-out read next' if usable else 'NOT USED: no held-out read'}", flush=True)


def cmd_apply(args):
    """s4-pick's checkpoint on the held-out bands' items of a set: steer by the coarse hint, X-LANCE (CPU, as
    steer_xlmdxc's stems), the fine-tuned MDX23C, rotate back, average; 48 kHz stems in `stems/s4`."""
    import hashlib
    import io
    import pathlib

    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import sep_s1b as S1B
    from learn import trusted_data as T

    S3.require(PHASE_S4)
    root = S1B.set_dir(args.set)
    pick = json.loads((out_dir() / "run" / "pick.json").read_text())
    if not pick.get("usable"):
        raise SystemExit("s4-pick found S4 not used (step 0, or no decided validation read gain): no held-out read")
    ck = pathlib.Path(pick["path"])
    b = ck.read_bytes()
    if hashlib.sha256(b).hexdigest() != pick["sha256"]:
        raise SystemExit(f"{ck} isn't the picked file (sha256)")
    prov = root / "stems" / "s4" / "pick.json"
    prov.parent.mkdir(parents=True, exist_ok=True)
    if any(prov.parent.glob("*.npz")) and (not prov.exists()
                                           or json.loads(prov.read_text())["sha256"] != pick["sha256"]):
        raise SystemExit(f"{prov.parent} holds stems from another checkpoint: move them aside first")
    prov.write_text(json.dumps({"step": pick["step"], "sha256": pick["sha256"]}, indent=1))
    model, config = load_centre(args.device)
    model.load_state_dict(torch.load(io.BytesIO(b), map_location="cpu", weights_only=True))
    model.eval()
    sep = DS.stem_separator(T.SEP, "cpu")
    print(f"s4-apply: step {pick['step']}", flush=True)
    n_done = 0
    for p in sorted((root / "items").glob("*.npz")):
        meta = json.loads(p.with_suffix(".json").read_text())
        if meta["band"] not in S3.HELD_BANDS:
            continue
        q = root / "stems" / "s4" / p.name
        if q.exists():
            continue
        z = np.load(p)
        L, R = np.asarray(z["L"], np.float64), np.asarray(z["R"], np.float64)
        np.savez(q, stem=stem_from(model, config, sep, L, R, meta, args.device).astype(np.float16))
        n_done += 1
    print(f"S4 APPLY DONE: {args.set}, {n_done} stems", flush=True)


def stem_from(model, config, sep, L, R, meta, device):
    """S4's stem of an item (48 kHz L, R): steer by the coarse hint, X-LANCE, the centre model, rotate back exactly
    and average (`unsteer_mono`, S3's apply: the fine-tuned output may hold a side part), back to 48 kHz."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import separator_screen as SCR

    phi = S3.steer_phi(S3.hint_of(meta))
    Ls, Rs = S3.rotate(L, R, phi)
    st = np.asarray(DS.xl_run_chunked(sep._f, np.stack([SCR.to44(Ls), SCR.to44(Rs)]).astype(np.float32)),
                    np.float32)
    return np.asarray(SCR.to48(TR.unsteer_mono(centre_run(model, config, st, device), phi), len(L)), np.float64)


def cmd_apply_check(_args):
    """The review: step 0 (the model as it is) through s4-apply's own path on S0 training-band items (Forkupines, BKS;
    centre and side hints), against the routed comparator's stored stems. -> check-apply.json."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import product_path as PP
    from learn import sep_s1b as S1B
    from learn import trusted_data as T

    S3.require(PHASE_S4)
    root = S1B.set_dir("main")
    model, config = load_centre("cpu")
    model.eval()
    sep = DS.stem_separator(T.SEP, "cpu")
    nets, _, _ = PP._adopted()
    picks = {"centre": [], "side": []}
    for p in sorted((root / "items").glob("*.npz")):
        meta = json.loads(p.with_suffix(".json").read_text())
        if meta["band"] not in ("Forkupines", "BKS") or meta["stratum"] == "double":
            continue
        k = "centre" if S3.hint_of(meta) == 0.0 else "side"
        if len(picks[k]) < 3:
            picks[k].append((p, meta))
    rows = []
    from learn import pretrain_set as PS

    h = PS.half_slices()["A"]
    for p, meta in picks["centre"] + picks["side"]:
        z = np.load(p)
        L, R = np.asarray(z["L"], np.float64), np.asarray(z["R"], np.float64)
        tgt = np.asarray(z["target"], np.float64)
        mix = (L + R) / 2
        comp = S3.routed(meta, "s4")
        s4 = stem_from(model, config, sep, L, R, meta, "cpu")
        sc = S3.stem_any(root, "main", comp, p.name)
        ref = S3.model_feats(nets, tgt, mix, meta["cls"])
        rows.append({"i": meta["i"], "band": meta["band"], "stratum": meta["stratum"], "comparator": comp,
                     "si_sdr_s4_step0": float(S0.si_sdr(s4[h], tgt[h])),
                     "si_sdr_comparator": float(S0.si_sdr(sc[h], tgt[h])),
                     "si_sdr_s4_vs_comparator": float(S0.si_sdr(s4[h], sc[h])),
                     "read_s4_step0": float(PP.cosine_distance(S3.model_feats(nets, s4, mix, meta["cls"]), ref)),
                     "read_comparator": float(PP.cosine_distance(S3.model_feats(nets, sc, mix, meta["cls"]), ref))})
        r = rows[-1]
        print(f"s4 apply check {meta['i']} {meta['stratum']} vs {comp}: SI-SDR {r['si_sdr_s4_step0']:+.2f} / "
              f"{r['si_sdr_comparator']:+.2f} (stems {r['si_sdr_s4_vs_comparator']:+.1f} dB apart), read "
              f"{r['read_s4_step0']:.4f} / {r['read_comparator']:.4f}", flush=True)
    out_dir().mkdir(parents=True, exist_ok=True)
    (out_dir() / "check-apply.json").write_text(json.dumps(rows, indent=1))
    print("S4 APPLY CHECK DONE", flush=True)


def check_stems(root):
    """A set's S4 stems were made by s4-pick's checkpoint (stems/s4/pick.json against run/pick.json)."""
    pick = json.loads((out_dir() / "run" / "pick.json").read_text())
    prov = root / "stems" / "s4" / "pick.json"
    if not prov.exists() or json.loads(prov.read_text())["sha256"] != pick["sha256"]:
        raise SystemExit(f"{root.name}'s S4 stems aren't from the picked checkpoint (step {pick['step']})")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="learn.sep_s4_train")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("s4-cache")
    s.add_argument("--device", default="cpu")
    s.add_argument("--k0", type=int, default=0)
    s.add_argument("--k1", type=int, default=N_DRAWS)
    s.set_defaults(fn=cmd_cache)
    sub.add_parser("s4-val").set_defaults(fn=cmd_val)
    s = sub.add_parser("s4-check")
    s.add_argument("--batches", type=int, nargs="+", default=[1, 2, 4])
    s.add_argument("--grad-batch", type=int, default=2, help="the gradient check's batch (the training micro-batch)")
    s.add_argument("--steps", type=int, default=6)
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("s4-train")
    s.add_argument("--batch", type=int, required=True)
    s.add_argument("--accum", type=int, default=1)
    s.add_argument("--workers", type=int, default=2)
    s.add_argument("--device", default="mps")
    s.set_defaults(fn=cmd_train)
    s = sub.add_parser("s4-pick")
    s.add_argument("--user-stop", action="store_true")
    s.set_defaults(fn=cmd_pick)
    sub.add_parser("s4-apply-check").set_defaults(fn=cmd_apply_check)
    s = sub.add_parser("s4-apply")
    s.add_argument("--set", choices=("main", "split"), required=True)
    s.add_argument("--device", default="cpu")
    s.set_defaults(fn=cmd_apply)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
