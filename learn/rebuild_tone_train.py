"""The rebuild-tone step's torch side (`docs/rebuild-tone-plan.md`): a short-time treble loss for C′
(each bin's long-term offset removed, so no EQ can meet it), its matched-step control, a second
seed of the rebuild-gap study's `rank` and `ctl`, the zero-render gate on held-out training-fold
bands, and the arms' rebuilds of the amp track. Run with the torch interpreter:

    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_tone_train train --fold 0 --arm stm --seed 0
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_tone_train train --fold 0 --arm ctl --seed 0   # stops at stm's best step
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_tone_train train --fold 0 --arm rank --seed 1
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_tone_train train --fold 0 --arm ctl --seed 1   # stops at rank s1's best
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_tone_train gate --nets stm_s0,ctl_s0      # zero renders, CPU
    OMP_NUM_THREADS=2 $TORCH_PY -m learn.rebuild_tone_train rebuild --arm arm_stm           # CPU, zero renders

Everything spectral runs on the CPU (torch.stft's backward is wrong on MPS above 65,536 samples);
the network runs on MPS when available. The stage-T machinery (data pipeline, proxy terms,
schedule, stopping rule, MPS guards) is the rebuild-gap study's, unchanged
(`learn/rebuild_gap_train.py`).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import shutil
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import rebuild_gap_train as T  # noqa: E402

SR = 48000
# The short-time treble loss (the plan's `stm` term)
ST_FFTS = (256, 512, 1024, 2048)             # 5, 11, 21 and 43 ms
ST_BAND = (2000.0, 8000.0)
ST_RAMP_OCT = 1 / 3                          # raised-cosine edges outside the band
ST_FLOOR_DB, ST_ACTIVE_DB = 60.0, 40.0       # bins within 60 dB of the frame's loudest target bin; frames within 40 dB
ST_SHARE = 0.5                               # λ: the term's weighted mean is half C′'s loss at step 0
# The declared metric E_st (the gate, the selection and the 24-part diagnostic)
EST_N, EST_HOP = 1024, 256
# Selection and stopping: stage T's rule, on E_st for `stm` (lower is better) and proxy fidelity for `rank`
ST_MIN_GAIN = 0.02                           # dB
GATE_CROPS = 192                             # per fold, held-out band rows outside the 96 selection crops
SEEDS = {0: (0, 1), 1: (100, 101)}           # seed -> (data stream, proxy draws); seed 0 is stage T's own
ARMS = ("stm", "ctl", "rank")
CONTROL_OF = {0: "stm", 1: "rank"}           # each seed's `ctl` stops at this arm's best step
# The networks the gate can read: name -> (folder, file) per fold
TR_DIR = T.out_dir()


def home():
    return pathlib.Path("~/ndsp-presets").expanduser()


def out_dir():
    return home() / "learn/rebuild-tone"


def model_dir(arm, seed, fold):
    return out_dir() / f"models-{arm}-s{seed}-f{fold}"


def net_path(name, fold):
    """Gate/rebuild network names: cprime (C′), stm_s0, ctl_s0, rank_s1, ctl_s1 (this step), rank_s0
    and ctl_tr (the rebuild-gap study's stage T)."""
    if name == "cprime":
        return T.cprime_path(fold)
    if name == "rank_s0":
        return T.model_dir("rank", fold) / f"fold{fold}.pt"
    if name == "ctl_tr":
        return T.model_dir("ctl", fold) / f"fold{fold}.pt"
    arm, s = name.rsplit("_s", 1)
    return model_dir(arm, int(s), fold) / f"fold{fold}.pt"


# --- the loss and the metric ------------------------------------------------------------------------------

def st_weights(freqs, band=ST_BAND, ramp=ST_RAMP_OCT):
    """1 inside the band, a raised-cosine fall to 0 over `ramp` octaves outside each edge (numpy or torch)."""
    import numpy as np

    f = np.maximum(np.asarray(freqs, np.float64), 1.0)
    w = np.ones_like(f)
    lo = np.log2(band[0] / f) / ramp
    hi = np.log2(f / band[1]) / ramp
    for x in (lo, hi):
        m = x > 0
        w[m] = np.where(x[m] < 1, 0.5 * (1 + np.cos(np.pi * x[m])), 0.0)
    return w


def st_mask_np(B_db, band_w, floor_db=ST_FLOOR_DB, active_db=ST_ACTIVE_DB):
    """B_db (bins, frames): the target's dB magnitude. -> (bins, frames) weights: active frames ×
    bins within `floor_db` of the frame's loudest bin × the band weight."""
    import numpy as np

    e = 10 * np.log10((10 ** (B_db / 10)).sum(0) + 1e-20)
    act = e >= e.max() - active_db
    ok = B_db >= B_db.max(0, keepdims=True) - floor_db
    return (ok & act[None]) * band_w[:, None]


def est(x, t, band=ST_BAND):
    """The declared metric E_st (dB): the mean |ΔdB| of the STFT magnitudes (Hann 1,024, hop 256) of x
    against the target t, over 2–8 kHz (hard edges), on t's frames within 40 dB of its loudest and
    bins within 60 dB of each frame's loudest t bin, after removing each bin's mean offset over
    those frames (so no fixed EQ changes it). x and t are on one timeline, same length."""
    import numpy as np
    from scipy.signal import stft

    n = min(len(x), len(t))
    kw = dict(fs=SR, window="hann", nperseg=EST_N, noverlap=EST_N - EST_HOP)
    f, _, X = stft(np.asarray(x[:n], np.float64), **kw)
    _, _, Tt = stft(np.asarray(t[:n], np.float64), **kw)
    A, B = 20 * np.log10(np.abs(X) + 1e-9), 20 * np.log10(np.abs(Tt) + 1e-9)
    inband = ((f >= band[0]) & (f <= band[1])).astype(np.float64)
    m = st_mask_np(B, inband) > 0
    d = np.where(m, A - B, 0.0)
    off = d.sum(1) / np.maximum(m.sum(1), 1)
    r = np.abs(d - off[:, None])[m]
    return float(r.mean()) if r.size else None


def st_loss(p, y, ffts=ST_FFTS, eps=1e-4):
    """The `stm` term on a batch: p (net output) and y (target DI), (B, 1, n) on any device; computed
    on the CPU with the gradient flowing back to p. Per resolution: dB magnitudes, the mask of
    `st_mask_np` (from the target, no gradient) with the 2–8 kHz weight and its ramps, each bin's
    long-term offset (its masked mean over the crop's frames) removed, then the masked mean of a
    smooth |ΔdB|; averaged over resolutions."""
    import torch

    from learn import direc as D

    if p.device.type != "cpu":
        return st_loss(p.cpu(), y.cpu(), ffts, eps).to(p.device)
    a, b = p.squeeze(1), y.squeeze(1)
    tot = 0.0
    for n in ffts:
        w = torch.hann_window(n, dtype=a.dtype)
        A = D._magnitude(torch.stft(a, n, n // 4, window=w, return_complex=True))
        with torch.no_grad():
            Bm = D._magnitude(torch.stft(b, n, n // 4, window=w, return_complex=True))
            Bd = 20 * torch.log10(Bm + 1e-7)
            e = 10 * torch.log10((Bm ** 2).sum(1) + 1e-20)                       # (B, frames)
            act = (e >= e.max(1, keepdim=True).values - ST_ACTIVE_DB).to(a.dtype)
            ok = (Bd >= Bd.max(1, keepdim=True).values - ST_FLOOR_DB).to(a.dtype)
            fw = torch.tensor(st_weights(torch.fft.rfftfreq(n, 1 / SR).numpy()), dtype=a.dtype)
            M = ok * act[:, None, :] * fw[None, :, None]
        d = 20 * torch.log10(A + 1e-7) - Bd
        off = (d * M).sum(-1, keepdim=True) / M.sum(-1, keepdim=True).clamp(min=1e-6)
        r = torch.sqrt((d - off) ** 2 + eps)
        tot = tot + (r * M).sum() / M.sum().clamp(min=1e-6)
    return tot / len(ffts)


# --- validation (zero renders) ----------------------------------------------------------------------------

def crop_metrics(p, y):
    """Per crop of a validation batch (numpy, 1-D): E_st, LSD (80 Hz–8 kHz) and coherence 1–3 kHz and
    3–8 kHz against the target."""
    from learn import rebuild_gap as G

    return {"est": est(p, y), "lsd": G.lsd_db(p, y), "coh_1_3k": G.coherence(p, y, 1000, 3000),
            "coh_3_8k": G.coherence(p, y, 3000, 8000)}


def val_est(net, data, vidx, dev):
    """Mean E_st and C′'s reconstruction loss on fixed centre crops (the data stream is untouched)."""
    import numpy as np
    import torch

    D = data.D
    net.eval()
    ests, recon = [], 0.0
    with torch.no_grad():
        for s in range(0, len(vidx), T.BATCH):
            vx, vy = data.make(vidx[s:s + T.BATCH], False, dev)
            vp = net(vx)
            recon += float(100 * (vp - vy).abs().mean() + D.mrstft(vp.squeeze(1), vy.squeeze(1)))
            P, Y = vp[:, 0].cpu().double().numpy(), vy[:, 0].cpu().double().numpy()
            for j in range(len(P)):
                v = est(P[j], Y[j])
                if v is not None:
                    ests.append(v)
    net.train()
    return (float(np.mean(ests)) if ests else None), recon


def selection_crops(data, fold):
    """Stage T's 96 fixed validation crops and their proxy draws (`rebuild-gap|val|<fold>`), so the
    second seed of `rank` selects exactly as stage T did, and `stm` selects on the same crops."""
    import numpy as np

    vr = np.random.default_rng(T.seed_int(f"rebuild-gap|val|{fold}"))
    vidx = vr.choice(data.va, min(T.VAL_CROPS, len(data.va)), replace=False)
    vdraws = []
    for _ in vidx:
        ds = []
        for _ in range(T.VAL_DRAWS):
            s, c = T.local_set(vr)
            ds.append((s, c[np.sort(vr.choice(len(c), T.VAL_K, replace=False))]))
        vdraws.append(ds)
    return vidx, vdraws


def gate_crops(data, fold, vidx, n=GATE_CROPS):
    """The gate's crops: held-out band rows outside the selection crops, seeded per fold."""
    import numpy as np

    rest = np.setdiff1d(data.va, vidx)
    rng = np.random.default_rng(T.seed_int(f"rebuild-tone|gate|{fold}"))
    return np.sort(rng.choice(rest, min(n, len(rest)), replace=False))


def better(arm, value, best):
    """`stm`: E_st at least ST_MIN_GAIN dB lower; `rank`: stage T's rule (proxy fidelity 0.005 higher)."""
    if value is None:
        return False
    if arm == "stm":
        return best is None or value <= best - ST_MIN_GAIN
    return T.is_best(value, best)


def step_batch(data, data_seed, step):
    """The batch of training step `step`: its rows and its augmentation drawn from a generator seeded
    by (data stream, step) alone, so an arm and its control see the same batch at every step whatever
    either skipped before (a skipped step still counts as a step). Sets `data.rng`."""
    import numpy as np

    data.rng = np.random.default_rng([data_seed, step])
    return data.rng.choice(data.tr, T.BATCH, replace=False)


def matched_step(seed, fold):
    """`ctl`'s stopping step: the best step of this seed's controlled arm on this fold."""
    p = model_dir(CONTROL_OF[seed], seed, fold) / "result.json"
    if not p.exists():
        raise SystemExit(f"{CONTROL_OF[seed]} seed {seed} fold {fold} has not finished")
    return json.loads(p.read_text())["best_step"]


# --- training ----------------------------------------------------------------------------------------------

def fit(fold, arm, seed=0, max_steps=T.MAX_STEPS, stop_at=None, device=None, out=None):
    """One fold, arm and seed. `stm`: C′'s loss + λ_st·st_loss (λ by the share rule at step 0),
    selected on E_st over the 96 selection crops. `rank`: stage T's recipe exactly, on this seed's
    streams. `ctl`: C′'s loss only, the same stream and schedule, run to `stop_at` and saved there.
    Every arm logs E_st and recon at each check; `rank` and `ctl` also the proxy fidelity."""
    import numpy as np
    import torch

    from learn import direc as D

    data_seed, proxy_seed = SEEDS[seed]
    torch.manual_seed(seed)
    dev = torch.device(device or os.environ.get("DIREC_DEVICE") or ("mps" if torch.backends.mps.is_available() else "cpu"))
    out = pathlib.Path(out) if out else model_dir(arm, seed, fold)
    out.mkdir(parents=True, exist_ok=True)
    data = T.Data(fold, seed=data_seed)
    vidx, vdraws = selection_crops(data, fold)
    resume = T.cprime_path(fold)
    net = D.build_model().to(dev)
    net.load_state_dict(torch.load(resume, map_location=dev))
    opt = torch.optim.AdamW(net.parameters(), lr=T.LR, weight_decay=1e-5)
    lam = {"rank": 0.0, "match": 0.0, "st": 0.0}
    if arm in ("rank", "stm"):
        cr, crng = np.random.default_rng(2), np.random.default_rng(3)        # stage T's calibration seeds
        lc, la, lb = [], [], []
        saved = data.rng
        data.rng = cr
        net.eval()
        with torch.no_grad():
            for _ in range(T.CAL_BATCHES):
                x, y = data.make(cr.choice(data.tr, T.BATCH, replace=False), True, dev)
                p = net(x)
                lc.append(float(D.training_loss(p, y)))
                if arm == "rank":
                    a, b = T.proxy_terms(p, y, crng)
                    la.append(float(a))
                    lb.append(float(b))
                else:
                    la.append(float(st_loss(p, y)))
        net.train()
        data.rng = saved
        if arm == "rank":
            lam.update(rank=float(T.CAL_SHARE * np.mean(lc) / max(np.mean(la), 1e-9)),
                       match=float(T.CAL_SHARE * np.mean(lc) / max(np.mean(lb), 1e-9)))
        else:
            lam["st"] = float(ST_SHARE * np.mean(lc) / max(np.mean(la), 1e-9))
        print(f"fold {fold} {arm} s{seed} calibration: C′ loss {np.mean(lc):.3f}, terms {np.mean(la):.3f}"
              f"{'' if not lb else f' / {np.mean(lb):.3f}'} -> λ {lam}", flush=True)
    cfg = {"fold": fold, "arm": arm, "seed": seed, "data_seed": data_seed, "proxy_seed": proxy_seed, "batch": T.BATCH,
           "lr": T.LR, "lr_end": T.LR_END, "warmup": T.WARMUP, "max_steps": max_steps, "stop_at": stop_at,
           "every": T.EVERY, "patience": T.PATIENCE, "min_steps": T.MIN_STEPS,
           "min_gain": ST_MIN_GAIN if arm == "stm" else T.MIN_GAIN, "lambda": lam, "resume": str(resume),
           "caches": [str(data.cache)], "val_bands": list(T.VAL_BANDS[fold]), "train_rows": int(len(data.tr)),
           "val_rows": int(len(data.va)), "st": {"ffts": ST_FFTS, "band": ST_BAND, "ramp_oct": ST_RAMP_OCT,
                                                  "floor_db": ST_FLOOR_DB, "active_db": ST_ACTIVE_DB, "share": ST_SHARE}}
    (out / "config.json").write_text(json.dumps(cfg, indent=1))
    print(f"fold {fold} {arm} s{seed}: train {len(data.tr)} rows, validation {len(data.va)} rows "
          f"({T.VAL_BANDS[fold]}), bleed {len(data.bleed)}, device {dev}", flush=True)
    proxy_val = arm in ("rank", "ctl")

    def check(step):
        e, rec = val_est(net, data, vidx, dev)
        fid = T.validate(net, data, vidx, vdraws, dev)[0] if proxy_val else None
        return {"step": step, "est": e, "proxy_fidelity": fid, "recon": rec}

    curve = [check(0)]
    print(f"fold {fold} {arm} s{seed} step 0 {curve[0]}", flush=True)
    key = "est" if arm == "stm" else "proxy_fidelity"
    best, best_step = curve[0][key], 0
    torch.save(net.state_dict(), out / "best.pt")
    target = stop_at if arm == "ctl" else max_steps
    t0, step, skipped, streak, recoveries, window = time.time(), 0, 0, 0, 0, []
    while step < target:
        for g in opt.param_groups:
            g["lr"] = T.schedule(step, total=max_steps)
        x, y = data.make(step_batch(data, data_seed, step), True, dev)
        p = net(x)
        loss = D.training_loss(p, y)
        if arm == "rank":
            a, b = T.proxy_terms(p, y, np.random.default_rng([proxy_seed, step]))
            loss = loss + lam["rank"] * a + lam["match"] * b
        elif arm == "stm":
            loss = loss + lam["st"] * st_loss(p, y)
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
            skipped += 1                               # the step is spent unapplied: its batch was drawn by
            streak += 1                                # step index, so the arm and its control stay matched
            if streak >= 25:
                net.load_state_dict(torch.load(out / "last.pt" if (out / "last.pt").exists() else resume, map_location=dev))
                opt = torch.optim.AdamW(net.parameters(), lr=T.LR, weight_decay=1e-5)
                recoveries += 1
                streak = 0
                print(f"fold {fold} {arm} s{seed} recovery {recoveries} at step {step}", flush=True)
                if recoveries > 20:
                    raise RuntimeError("training keeps producing non-finite gradients")
        else:
            streak = 0
            if total > 5.0:
                for g in grads:
                    g.mul_(5.0 / total)
            opt.step()
        step += 1
        if step % T.EVERY == 0 or (arm == "ctl" and step == target):
            c = check(step)
            el = time.time() - t0
            c.update(loss=float(loss.detach()), skipped=skipped, minutes=el / 60)
            curve.append(c)
            print(f"fold {fold} {arm} s{seed} step {step} {el / 60:.1f} min ({step / el:.2f} it/s) "
                  f"loss {float(loss.detach()):.3f} est {c['est']} proxy {c['proxy_fidelity']} recon {c['recon']:.3f} "
                  f"skipped {skipped}", flush=True)
            torch.save(net.state_dict(), out / "last.pt")
            if arm != "ctl":
                if better(arm, c[key], best):
                    best, best_step = c[key], step
                    torch.save(net.state_dict(), out / "best.pt")
                if T.should_stop(step, best_step, max_steps=max_steps):
                    print(f"fold {fold} {arm} s{seed} stopped at step {step}: best {best:.4f} at {best_step}", flush=True)
                    break
            (out / "curve.json").write_text(json.dumps(curve, indent=1))
    if arm == "ctl":
        torch.save(net.state_dict(), out / "best.pt")
        best_step, best = step, curve[-1][key]
    shutil.copyfile(out / "best.pt", out / f"fold{fold}.pt")
    (out / "curve.json").write_text(json.dumps(curve, indent=1))
    (out / "result.json").write_text(json.dumps({"best_step": best_step, "best": best, "selected_on": key,
                                                 "step0": curve[0], "steps_run": step, "skipped": skipped,
                                                 "recoveries": recoveries, "minutes": (time.time() - t0) / 60}, indent=1))
    (out / "DONE").write_text(time.strftime("%Y-%m-%d %H:%M:%S\n"))
    print(f"fold {fold} {arm} s{seed} done: final = step {best_step} ({key} {best})", flush=True)


# --- the zero-render gate ------------------------------------------------------------------------------------

def cmd_gate(names, folds=(0, 1, 2, 3)):
    """Per fold, every named network on the gate crops (held-out training-fold bands, outside the
    selection crops): E_st, LSD and coherence against the target, per crop with its band and
    recording. Writes gate-crops.json (merged with earlier runs); the contrasts and the render
    decision are `learn.rebuild_tone gate-report`'s."""
    import numpy as np
    import torch

    from learn import direc as D

    path = out_dir() / "gate-crops.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    rec = recordings()
    for fold in folds:
        data = T.Data(fold, seed=0)
        vidx, _ = selection_crops(data, fold)
        gidx = gate_crops(data, fold, vidx)
        assert not set(gidx.tolist()) & set(vidx.tolist())
        for name in names:
            key = f"{name}|{fold}"
            if key in res:
                continue
            p = net_path(name, fold)
            if not p.exists():
                print(f"gate: {name} fold {fold} missing ({p}); skipped", flush=True)
                continue
            net = D.load_model(p).eval()
            rows = []
            with torch.no_grad():
                for s in range(0, len(gidx), T.BATCH):
                    idx = gidx[s:s + T.BATCH]
                    x, y = data.make(idx, False, torch.device("cpu"))
                    pp = net(x)
                    for j, i in enumerate(idx):
                        m = crop_metrics(pp[j, 0].double().numpy(), y[j, 0].double().numpy())
                        rows.append({"row": int(i), "band": data.meta[i]["band"], "recording": rec.get(data.meta[i]["id"]), **m})
            res[key] = {"network": str(p), "rows": rows}
            out_dir().mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(res))
            tmp.replace(path)
            print(f"gate {name} fold {fold}: E_st {np.mean([r['est'] for r in rows if r['est'] is not None]):.3f} "
                  f"({len(rows)} crops)", flush=True)


def recordings():
    """cache row id -> its DI recording (from the PR12 render index), for recording-clustered rows."""
    import glob

    out = {}
    for f in glob.glob(str(home() / "learn/poc/renders/index-w*.jsonl")):
        for line in pathlib.Path(f).read_text().splitlines():
            if line:
                r = json.loads(line)
                out[r["id"]] = r["file"]
    return out


# --- the arms' rebuilds (zero renders) -------------------------------------------------------------------------

TRAINED_ARMS = {"arm_stm": "stm_s0", "arm_ctl_stm": "ctl_s0", "arm_rank_s1": "rank_s1", "arm_ctl_s1": "ctl_s1"}


def cmd_rebuild(arm):
    """Each part's reference.wav rebuilt by its fold's network exactly as 1b (`rebuild_from`), with
    2a's checks and experiment 4's leak assertion (the parent C′'s pool too); writes
    arms/<arm>/check.json."""
    from learn import confirm_run as CR
    from learn import di_fine_structure as DF
    from learn import local_objective as LO

    name = TRAINED_ARMS[arm]
    d = out_dir() / "arms" / arm

    def parent_pool(band, path, f):
        DF.assert_no_leak(band, f, f, DF.train_pool_bands(f, [DF.MODELS / c for c in DF.CACHES]))

    bad, missing = LO.rebuild_from(LO.MATCHED_DI, lambda slug, part: CR.mono(part["crop"] / "reference.wav"),
                                   net=lambda f: net_path(name, f), extra_leak=parent_pool, out_dir=d, gate=False)
    if bad or missing:
        raise SystemExit(f"{arm} rebuilds fail the checks: {bad or missing}")
    print(f"{arm}: all 24 rebuilds pass")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("train")
    f.add_argument("--fold", type=int, required=True)
    f.add_argument("--arm", choices=ARMS, required=True)
    f.add_argument("--seed", type=int, choices=tuple(SEEDS), default=0)
    f.add_argument("--max-steps", type=int, default=T.MAX_STEPS)
    f.add_argument("--stop-at", type=int)
    f.add_argument("--device")
    f.add_argument("--out")
    g = sub.add_parser("gate")
    g.add_argument("--nets", required=True)
    r = sub.add_parser("rebuild")
    r.add_argument("--arm", choices=tuple(TRAINED_ARMS), required=True)
    a = ap.parse_args(argv)
    if a.cmd == "train":
        stop_at = a.stop_at if a.stop_at is not None else (matched_step(a.seed, a.fold) if a.arm == "ctl" else None)
        fit(a.fold, a.arm, a.seed, a.max_steps, stop_at, a.device, a.out)
    elif a.cmd == "gate":
        cmd_gate([n for n in a.nets.split(",") if n])
    else:
        cmd_rebuild(a.arm)


if __name__ == "__main__":
    main()
