"""Model comparison, the training arms (`docs/model-comparison-plan.md`, Phase 4).

    $TORCH_PY -m learn.bakeoff_train head --arm A-cat --seed 20261042     # new heads on W's frozen body, plugin rows (MPS)
    $TORCH_PY -m learn.bakeoff_train body --arm A-cnn --seed 20261042     # a new body from scratch, W's 60 epochs (MPS)
    $TORCH_PY -m learn.bakeoff_train tune --arm A-cat --fold 0 --seed 20261042   # FTm's recipe from the arm's start (MPS)
    $TORCH_PY -m learn.bakeoff_train answers --arm A-cat                  # held answers to PF/bakeoff/answers (CPU)

Each arm keeps W's plugin rows, FTm's real rows, the searched-head mask, the optimiser (Adam, batch 64, gradients scaled to
norm 5) and FTm's stored E(k, s), so no inner runs. No NS row is built: `plugin_rows` gets no held rows. W's stored body was
chosen on NS loss, which arms built on it inherit. Runs resume: a finished arm's file is left alone. Extra real rows come
through `extra_rows` and leave by `di`.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import subprocess
import sys
import time

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

SEEDS = (20261042, 20261043)
CTL_OFFSET = 2                          # A-ctl's training seeds: 20261044 and 20261045
BINS = 21
HEAD_EPOCHS = 30
BODY_EPOCHS = 60
PLUGIN_LR, TUNE_LR = 1e-3, 1e-4
SD_FLOOR = 0.07
MIC_WEIGHT = 0.1
ARMS = {"A-ctl": {"start": "W"}, "A-cat": {"start": "head"}, "A-k1": {"start": "head"}, "A-mic": {"start": "W"},
        "A-cnn": {"start": "body"}}                     # A-in joins if an input from Phase 3 moves on or leads


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def soft_bins(y, bins=BINS):
    """Unit labels [..., ] split between their two nearest bin centres on 0-1. -> [..., bins] summing to 1."""
    y = np.clip(np.asarray(y, np.float64), 0.0, 1.0) * (bins - 1)
    lo = np.minimum(np.floor(y).astype(int), bins - 2)
    w = y - lo
    out = np.zeros((*y.shape, bins), np.float32)
    np.put_along_axis(out, lo[..., None], (1 - w)[..., None], -1)
    np.put_along_axis(out, (lo + 1)[..., None], w[..., None], -1)
    return out


def bin_median(p):
    """The interpolated median of [..., bins] probabilities over centres on 0-1: where the piecewise-linear CDF of
    the point masses, each spread half a bin either way, crosses one half."""
    p = np.asarray(p, np.float64)
    p = p / p.sum(-1, keepdims=True)
    bins = p.shape[-1]
    cum = np.cumsum(p, -1)
    i = (cum >= 0.5).argmax(-1)
    before = np.where(i > 0, np.take_along_axis(cum, np.maximum(i - 1, 0)[..., None], -1)[..., 0], 0.0)
    mass = np.maximum(np.take_along_axis(p, i[..., None], -1)[..., 0], 1e-12)
    edge = (i - 0.5 + (0.5 - before) / mass) / (bins - 1)
    return np.clip(edge, 0.0, 1.0)


def stored_e(rec):
    """An FTm_k run record's E: chosen on inner runs that never saw fold k."""
    return int(rec["E"])


# --- nets ------------------------------------------------------------------------------------------------------------

def build_small(width=60):
    """A-cnn's body: two conv layers of 6 and 12 maps with pooling, mean and std over time, dense 120 and 60, the full
    heads on top. Same forward as `full_space.build_net`."""
    import torch
    import torch.nn as nn

    from learn import full_space as F
    from learn import song_model as SM

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.body = nn.Sequential(nn.Conv2d(2, 6, 5, padding=2), nn.BatchNorm2d(6), nn.ReLU(), nn.AvgPool2d(2),
                                      nn.Conv2d(6, 12, 5, padding=2), nn.BatchNorm2d(12), nn.ReLU(), nn.AvgPool2d(2))
            feat = 12 * (96 // 4) * 2
            d = feat + len(F.AMPS) + 2 + 2
            self.amp = nn.Sequential(nn.Linear(feat, 120), nn.ReLU(), nn.Linear(120, len(F.AMPS)))
            self.trunk = nn.Sequential(nn.Linear(d, 120), nn.ReLU(), nn.Dropout(0.2), nn.Linear(120, width), nn.ReLU())
            n = len(F.CONT)
            self.pi = nn.Linear(width, SM.K_MIX)
            self.mu = nn.Linear(width, SM.K_MIX * n)
            self.ls = nn.Linear(width, SM.K_MIX * n)
            self.sw = nn.Linear(width, len(F.SW))
            self.cat = nn.ModuleList([nn.Linear(width, len(F.MICS)) for _ in F.CAT])

        def forward(self, x, cond):
            h = self.body(x)
            h = torch.cat([h.mean(-1), h.std(-1)], dim=1).flatten(1)
            amp = self.amp(h)
            h = self.trunk(torch.cat([h, cond], dim=1))
            n = len(F.CONT)
            return (torch.log_softmax(self.pi(h), -1), torch.sigmoid(self.mu(h)).view(-1, SM.K_MIX, n),
                    self.ls(h).view(-1, SM.K_MIX, n).clamp(-6, 1), self.sw(h), [c(h) for c in self.cat], amp)

    return Net()


def build_arm(arm, base):
    """`base`, a `full_space.build_net` net or its state's copy, with the arm's knob heads. forward -> as `build_net`, its first
    three items the knob head's: A-cat's bin logits [B, knobs, bins] with two empty slots, A-k1's one-component mixture."""
    import torch
    import torch.nn as nn

    from learn import full_space as F

    n = len(F.CONT)

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.base = base
            if arm == "A-cat":
                self.knob = nn.Linear(256, n * BINS)
            else:
                self.mu = nn.Linear(256, n)
                self.ls = nn.Linear(256, n)

        def forward(self, x, cond):
            b = self.base
            h = b.body(x)
            h = torch.cat([h.mean(-1), h.std(-1)], dim=1).flatten(1)
            amp = b.amp(h)
            h = b.trunk(torch.cat([h, cond], dim=1))
            if arm == "A-cat":
                head = (self.knob(h).view(-1, n, BINS), None, None)
            else:
                head = (torch.zeros(len(h), 1, device=h.device), torch.sigmoid(self.mu(h)).view(-1, 1, n),
                        self.ls(h).view(-1, 1, n).clamp(math.log(SD_FLOOR), 1))
            return (*head, b.sw(h), [c(h) for c in b.cat], amp)

    return Net()


def loss_of(arm):
    """The arm's loss on `full_space.loss_fn`'s arguments."""
    import torch
    import torch.nn.functional as TF

    from learn import full_space as F

    if arm in ("A-ctl", "A-cnn", "A-k1"):
        return F.loss_fn
    if arm == "A-mic":
        def mic_light(out, c, cm, s, sm, k, km, a):
            logpi, mu, ls, swl, catl, ampl = out
            z = (c.unsqueeze(1) - mu) / ls.exp()
            lp = (-0.5 * z ** 2 - ls - 0.5 * math.log(2 * math.pi)) * cm.unsqueeze(1)
            nll = (-torch.logsumexp(logpi + lp.sum(-1), dim=-1) / cm.sum(-1).clamp(min=1)).mean()
            bce = (TF.binary_cross_entropy_with_logits(swl, s, reduction="none") * sm).sum() / sm.sum().clamp(min=1)
            ce = sum((TF.cross_entropy(catl[j], k[:, j], reduction="none") * km[:, j]).sum() / km[:, j].sum().clamp(min=1)
                     for j in range(len(catl)))
            keep = a >= 0
            return nll + bce + MIC_WEIGHT * ce + (TF.cross_entropy(ampl[keep], a[keep]) if keep.any() else ampl.sum() * 0.0)
        return mic_light

    def binned(out, c, cm, s, sm, k, km, a):
        logits, _, _, swl, catl, ampl = out
        t = torch.tensor(soft_bins(c.detach().cpu().numpy()), device=logits.device)
        ce_k = -(t * torch.log_softmax(logits, -1)).sum(-1)
        knob = ((ce_k * cm).sum(-1) / cm.sum(-1).clamp(min=1)).mean()
        bce = (TF.binary_cross_entropy_with_logits(swl, s, reduction="none") * sm).sum() / sm.sum().clamp(min=1)
        ce = sum((TF.cross_entropy(catl[j], k[:, j], reduction="none") * km[:, j]).sum() / km[:, j].sum().clamp(min=1)
                 for j in range(len(catl)))
        keep = a >= 0
        return knob + bce + ce + (TF.cross_entropy(ampl[keep], a[keep]) if keep.any() else ampl.sum() * 0.0)
    return binned


# --- the loop --------------------------------------------------------------------------------------------------------

def train(net, data, tr, loss, seed, dev, epochs, lr, params=None, label=""):
    """`pipeline_fix.fit`'s optimiser and order with no watched set. -> last epoch's mean training loss."""
    import torch

    from learn import direct_stems as DS
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    torch.manual_seed(seed)
    net = net.to(dev)
    params = None if params is None else list(params)
    opt = torch.optim.Adam(net.parameters() if params is None else params, lr=lr)
    rng = np.random.default_rng(seed)
    last = math.nan
    for epoch in range(epochs):
        if params is None:
            net.train()
        order = P.epoch_order(rng, tr, data, epoch)
        tl, skipped = [], 0
        for j in range(0, len(order), PS.BATCH):
            x, c, y = data.batch(order[j:j + PS.BATCH], epoch, dev)
            v = loss(net(x, c), *y)
            opt.zero_grad()
            v.backward()
            g = DS.grad_norm(net.parameters() if params is None else params)
            if torch.isfinite(g) and torch.isfinite(v):
                for q in (net.parameters() if params is None else params):
                    if q.grad is not None:
                        q.grad.mul_(min(1.0, 5.0 / (float(g) + 1e-9)))
                opt.step()
                tl.append(float(v.detach()))
            else:
                skipped += 1
        if skipped > PS.MAX_SKIP_SHARE * max(1, -(-len(order) // PS.BATCH)):
            raise PS.StepsSkipped(f"{label} epoch {epoch}: {skipped} steps non-finite")
        last = sum(tl) / max(1, len(tl))
        if epoch % 5 == 0 or epoch == epochs - 1:
            print(f"{label} epoch {epoch} loss {last:.4f}", flush=True)
    return last


def root():
    from learn import pipeline_fix as P

    return P.out_dir() / "bakeoff" / "runs"


def plugin_data(seed):
    """W's plugin rows as W read them, with no held row built. -> (data, training row indices)."""
    from learn import pipeline_fix as P

    e = P.require("phase_3")
    croot, kept, rend, sp, dropped = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    pa = argparse.Namespace(rung="b", fold=None, frac=1.0, sections=1.0, pc=False, pcsz=False, aug=False)
    tr, _, _, rows = P.plugin_rows(kept, sp, pa, lambda ids: P.rung_rows(kept, rend, ids) if ids is sp["train"] else [])
    wrec = json.loads((P.out_dir() / "runs" / f"P2b-wide24-{seed}.json").read_text())
    if tr != [i for i in wrec["train_ids"] if i < P.REAL_ROW0]:
        raise SystemExit("the plugin rows differ from W's")
    doubled = P.doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
    return P.WideData(rows, P.rung_path(croot, "b", doubled), set(tr)), np.arange(len(tr))


def real_data(k):
    """FTm's training rows on fold k, masked as FTm's, all plugin rows left out of the batches. -> (data, training row indices)."""
    from learn import pipeline_fix as P

    e = P.require("phase_3")
    croot, kept, rend, sp, dropped = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    rrows, _, _ = P.ft_real_rows(k, False)
    doubled = P.doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
    data = P.DfixData(rrows, P.rung_path(croot, "b", doubled), set(), {r["i"] for r in rrows}, 1.0)
    P.mask_searched(data.Y, rrows, P.A_menu_S())
    return data, np.arange(len(rrows))


def run_record(path, **kw):
    git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PLUGIN_ROOT).stdout.strip()
    path.write_text(json.dumps({"git": git, "command": " ".join(sys.argv), "pid": os.getpid(), "time": time.strftime("%Y-%m-%d %H:%M:%S"), **kw}, indent=1))


def save_state(net, out):
    """A checkpoint written whole, so `out.exists()` means a finished run."""
    import torch

    tmp = out.with_suffix(".tmp")
    torch.save({k: v.detach().cpu() for k, v in net.state_dict().items()}, tmp)
    tmp.replace(out)


def start_net(arm, seed):
    """The net an arm's plugin stage or tuning starts from, W's state for arms that keep it."""
    from learn import full_space as F
    from learn import pipeline_fix as P

    if arm == "A-cnn":
        return build_small()
    net = F.build_net()
    net.load_state_dict(P.ft_start_state(seed)[0])
    return net if arm in ("A-ctl", "A-mic") else build_arm(arm, net)


def cmd_head(a):
    """New knob heads on W's frozen body and trunk, eval mode, plugin rows."""
    import torch

    from learn import pipeline_fix as P

    root().mkdir(parents=True, exist_ok=True)
    out = root() / f"{a.arm}-head-{a.seed}.pt"
    if out.exists():
        return print(out.name, "exists")
    data, tr = plugin_data(a.seed)
    torch.set_num_threads(2)
    torch.manual_seed(a.seed)                           # the new heads' first weights
    net = start_net(a.arm, a.seed).to(P.device())
    net.eval()
    for q in net.base.parameters():
        q.requires_grad_(False)
    params = [q for q in net.parameters() if q.requires_grad]
    t0 = time.time()
    last = train(net, data, tr, loss_of(a.arm), a.seed, P.device(), HEAD_EPOCHS, PLUGIN_LR, params, f"{a.arm} head {a.seed}")
    save_state(net, out)
    run_record(out.with_suffix(".json"), arm=a.arm, seed=a.seed, stage="head", epochs=HEAD_EPOCHS, loss=last, minutes=(time.time() - t0) / 60)


def cmd_body(a):
    """A new body from scratch, W's recipe at its fixed 60 epochs, read at `final`; no tracked loss."""
    import torch

    from learn import pipeline_fix as P

    root().mkdir(parents=True, exist_ok=True)
    out = root() / f"{a.arm}-body-{a.seed}.pt"
    if out.exists():
        return print(out.name, "exists")
    data, tr = plugin_data(a.seed)
    torch.set_num_threads(2)
    torch.manual_seed(a.seed)                           # the new body's first weights
    net = start_net(a.arm, a.seed)
    t0 = time.time()
    last = train(net, data, tr, loss_of("A-ctl"), a.seed, P.device(), BODY_EPOCHS, PLUGIN_LR, None, f"{a.arm} body {a.seed}")
    save_state(net, out)
    run_record(out.with_suffix(".json"), arm=a.arm, seed=a.seed, stage="body", epochs=BODY_EPOCHS, loss=last, minutes=(time.time() - t0) / 60)


def arm_start(arm, seed):
    import torch

    net = start_net(arm, seed)
    stage = ARMS[arm]["start"]
    if stage != "W":
        net.load_state_dict(torch.load(root() / f"{arm}-{stage}-{seed}.pt", map_location="cpu"))
    return net


def cmd_tune(a):
    """FTm's recipe from the arm's start, for FTm's stored E(k, s)."""
    import torch

    from learn import pipeline_fix as P

    root().mkdir(parents=True, exist_ok=True)
    tag = "-same" if a.same_seed else ""
    out = root() / f"{a.arm}{tag}-k{a.fold}-{a.seed}.pt"
    if out.exists():
        return print(out.name, "exists")
    data, tr = real_data(a.fold)
    torch.set_num_threads(2)
    rec = json.loads((P.out_dir() / "runs" / f"P2b-ftm-k{a.fold}-{a.seed}.json").read_text())
    e = stored_e(rec)
    train_seed = a.seed + (CTL_OFFSET if a.arm == "A-ctl" and not a.same_seed else 0)
    t0 = time.time()
    net = arm_start(a.arm, a.seed)
    last = train(net, data, tr, loss_of(a.arm), train_seed, P.device(), e, TUNE_LR, None, f"{a.arm} k{a.fold} {a.seed}")
    want = rec["log"][-1]["train_mode_loss"]
    save_state(net, out)
    run_record(out.with_suffix(".json"), arm=a.arm, seed=a.seed, train_seed=train_seed, fold=a.fold, E=e, loss=last, ftm_loss=want, minutes=(time.time() - t0) / 60)
    print(f"{a.arm} k{a.fold} {a.seed}: last loss {last:.4f}, FTm's {want:.4f}", flush=True)


def read_outputs(net, d, arm, sd):
    """A net on a read's rows. -> per half (A, B as `both_halves`): (knob answers [n, knobs], `reads_v3.loss`'s output list).
    A-cat's knobs enter that list as one Gaussian at its median, sd the head's residual: its knob swap is another form."""
    import torch

    from learn import direct_stems as DS

    def one():
        ans, o = [], [[] for _ in range(5)]
        with torch.no_grad():
            for j in range(0, len(d.rows), 64):
                x, c, _ = d.batch(np.arange(j, min(j + 64, len(d.rows))), -1, "cpu")
                r = net(x, c)
                if arm == "A-cat":
                    m = bin_median(torch.softmax(r[0], -1).numpy())
                    head = (np.zeros((len(m), 1)), m[:, None], np.log(np.maximum(sd, 0.02))[None, None] * np.ones_like(m[:, None]))
                else:
                    head = (r[0].numpy(), r[1].numpy(), r[2].numpy())
                    m = DS.mixture_median(*head)
                ans.append(m)
                for q, v in enumerate((*head, r[3].numpy(), np.stack([z.numpy() for z in r[4]], 1))):
                    o[q].append(v)
        return np.concatenate(ans), [np.concatenate(z) for z in o]

    orig, a_ = DS.half_of, one()
    DS.half_of = lambda i, e: 1 - orig(i, e)
    try:
        return a_, one()
    finally:
        DS.half_of = orig


def own_swap(rows, outs, Y):
    """`reads_v3.read_fold`'s own against swap on rows {amp, cls, set, cluster}. outs: per seed, per half, a `read_outputs` list.
    -> [n, 3], NaN where no row can be swapped."""
    from learn import reads_v3 as R

    c, cm, s, sm, kk, km, _ = Y
    out = np.full((len(rows), 3), np.nan)
    for j, row in enumerate(rows):
        sk, ss, sc = R.searched(row["amp"], row["cls"])
        args = (c[j], cm[j] * sk, s[j], sm[j] * ss, kk[j], km[j] * sc)
        others = [i for i, q in enumerate(rows) if i != j and (q["amp"], q["cls"], q["set"]) == (row["amp"], row["cls"], row["set"])
                  and q["cluster"] != row["cluster"]]
        if others:
            mine = np.mean([[R.loss(h, j, *args) for h in o] for o in outs], (0, 1))
            out[j] = mine - np.mean([[[R.loss(h, i, *args) for h in o] for o in outs] for i in others], (0, 1, 2))
    return out


def load_arm(arm, k, seed):
    import torch

    from learn import full_space as F

    net = build_small() if arm == "A-cnn" else F.build_net() if arm in ("A-ctl", "A-mic") else build_arm(arm, F.build_net())
    net.load_state_dict(torch.load(root() / f"{arm}-k{k}-{seed}.pt", map_location="cpu"))
    return net.eval()


def cmd_answers(a):
    """Each fold's held answers and own against swap, seeds averaged, into `bakeoff`'s answer store."""
    from learn import bakeoff as B
    from learn import pipeline_fix as P
    from learn import reads_v3 as R
    from learn import trusted_data_t3 as T3

    rows, data = B.base_rows()
    enc = T3.encode_for(T3.FULL)
    for k in range(4):
        _, held, _ = P.dfix_rows_of(*data, k)
        mine = [r for r in rows if r["fold"] == k]
        assert [(h["amp"], h["cls"]) for h in held] == [(q["amp"], q["cls"]) for q in mine]
        d = R.make(held)
        rows_tr = B.training_set("real", k, data)[0]
        Y_tr = [np.stack(z) for z in zip(*(enc(h["label"]) for h in rows_tr))]
        sd = B.residual_sd(Y_tr[0], Y_tr[1], rows_tr, R.searched)
        outs = [read_outputs(load_arm(a.arm, k, s), d, a.arm, sd) for s in SEEDS]
        mu = np.mean([[h[0] for h in o] for o in outs], (0, 1))
        swap = own_swap(mine, [[h[1] for h in o] for o in outs], d.Y)
        B.save_answers(B.root() / "answers" / f"{a.arm}-k{k}.npz", mu=np.clip(mu, 0, 1), sd=sd, swap=swap)
        print(a.arm, "fold", k, "answers done", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("head", "body", "tune", "answers"))
    ap.add_argument("--arm", choices=tuple(ARMS), required=True)
    ap.add_argument("--seed", type=int, choices=SEEDS)
    ap.add_argument("--fold", type=int, choices=(0, 1, 2, 3))
    ap.add_argument("--same-seed", action="store_true", help="T4.2's control: A-ctl on FTm's own training seed")
    a = ap.parse_args(argv)
    {"head": cmd_head, "body": cmd_body, "tune": cmd_tune, "answers": cmd_answers}[a.step](a)


if __name__ == "__main__":
    main()
