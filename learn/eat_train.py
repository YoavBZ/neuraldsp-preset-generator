"""EfficientAT tuned on W's plugin rows (`docs/efficientat-plan.md`, task S8). MPS, announced, one GPU job at a time.

    $TORCH_PY -m learn.eat_train head --seed 20261042      # W's heads on the frozen AudioSet body
    $TORCH_PY -m learn.eat_train body --seed 20261042      # the whole body at their fine-tuning rate
    $TORCH_PY -m learn.eat_train rand --seed 20261042      # the same net from random weights, the control
    $TORCH_PY -m learn.eat_train steps                     # one epoch's minutes, nothing saved

The reader stays the ridge that read best: a tuned body is embedded by `eat_embed` and read as `E-mix` is, so no real row reaches a
body and real folds stay clean, as with W. BKS's own DIs are among W's rows, so BKS is not zero-shot for these bodies, as for W.
The data is the rebuilt input: W's rows in their first 4 backings, against W's own and 24, a handicap the results state. Each half
is cropped to its last 350 frames, half A's whole length after its masked second. Runs resume: a finished checkpoint is left alone.
"""
from __future__ import annotations

import argparse
import pathlib
import random
import sys
import time

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import bakeoff_train as T  # noqa: E402
from learn import eat_build as EB  # noqa: E402
from learn import eat_embed as EE  # noqa: E402
from learn import eat_net as E  # noqa: E402

TAPS = (5, 11, 13, 15)                                  # the blocks `pub` reads
TAP_CHANNELS = (40, 112, 160, 160)                      # at width 1
TAP_BANDS = (16, 8, 4, 4)
MAPS = 32
FRAMES = 350
TUNE_LR = 6e-5                                          # their ESC-50 rate
VARIANT_SEED = 20261044


def crop(x):
    """A half's last FRAMES frames."""
    return x[..., -FRAMES:]


def variant_of(i, epoch):
    """Which of a row's backings an epoch shows, seeded by row and epoch as `WideData` seeds its draw."""
    return random.Random(f"{VARIANT_SEED}|{i}|{epoch}").randrange(EB.WIDE_K)


def build(body):
    """`body`, an `eat_net.network`, with W's heads over its taps: each tap reduced to MAPS maps by a 1×1 conv, mean and std over
    time, frequency kept. forward -> as `full_space.build_net`."""
    import torch
    import torch.nn as nn

    from learn import full_space as F
    from learn import song_model as SM

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.body = body
            self.reduce = nn.ModuleList([nn.Conv2d(c, MAPS, 1) for c in TAP_CHANNELS])
            feat = 2 * MAPS * sum(TAP_BANDS)
            d = feat + len(SM.AMPS) + len(SM.CLASSES) + 2
            n = len(F.CONT)
            self.amp = nn.Sequential(nn.Linear(feat, 256), nn.ReLU(), nn.Linear(256, len(F.AMPS)))
            self.trunk = nn.Sequential(nn.Linear(d, 256), nn.ReLU(), nn.Dropout(0.2), nn.Linear(256, 256), nn.ReLU())
            self.pi = nn.Linear(256, SM.K_MIX)
            self.mu = nn.Linear(256, SM.K_MIX * n)
            self.ls = nn.Linear(256, SM.K_MIX * n)
            self.sw = nn.Linear(256, len(F.SW))
            self.cat = nn.ModuleList([nn.Linear(256, len(F.MICS)) for _ in F.CAT])

        def forward(self, x, cond):
            got, h = [], x
            for i, layer in enumerate(self.body.features):
                h = layer(h)
                if i in TAPS:
                    r = self.reduce[len(got)](h)
                    got.append(torch.cat([r.mean(-1), r.std(-1)], 1).flatten(1))
                if i == TAPS[-1]:
                    break
            h = torch.cat(got, 1)
            amp = self.amp(h)
            h = self.trunk(torch.cat([h, cond], 1))
            n = len(F.CONT)
            return (torch.log_softmax(self.pi(h), -1), torch.sigmoid(self.mu(h)).view(-1, SM.K_MIX, n),
                    self.ls(h).view(-1, SM.K_MIX, n).clamp(-6, 1), self.sw(h), [c(h) for c in self.cat], amp)

    return Net()


class FrontData:
    """W's rows on the rebuilt input, for `bakeoff_train.train`: one half of one backing per row per epoch."""

    def __init__(self, rows):
        from learn import trusted_data_t3 as T3

        self.rows = rows
        self.X = np.zeros((len(rows), EB.WIDE_K, 2, 128, FRAMES), np.uint8)
        self.L = np.zeros((len(rows), EB.WIDE_K, 2), np.float32)
        for j, r in enumerate(rows):
            for k in range(EB.WIDE_K):
                z = np.load(EB.wide_path(r["i"], k))
                self.X[j, k, 0], self.X[j, k, 1], self.L[j, k] = crop(z["sA"]), crop(z["sB"]), z["lufs"]
        enc = T3.encode_for(T3.FULL)
        self.Y = [np.stack(z) for z in zip(*(enc(r["label"]) for r in rows))]

    def batch(self, idx, epoch, dev):
        import torch

        from learn import direct_stems as DS
        from learn import song_model as SM

        idx = np.asarray(idx)
        X, C = [], []
        for j in idx:
            r = self.rows[int(j)]
            k, h = variant_of(r["i"], epoch), DS.half_of(r["i"], epoch)
            X.append(self.X[j, k, h])
            C.append(SM.cond_vec(r["amp"], r["cls"], [float(self.L[j, k, h]), 0.0]))
        x = EB.dequant(np.stack(X))[:, None]
        c = np.stack(C)
        c[:, -1] = 0                                    # the input's mix slot, zero as `zero_inputs` leaves it
        y = [torch.tensor(z[idx], device=dev) for z in self.Y]
        return torch.tensor(x, device=dev), torch.tensor(c, device=dev), y


def plugin_rows():
    from learn import bakeoff as B

    return B.plugin_set()[0]


def run_path(stage, seed):
    return EB.front_root().parent / "runs" / f"{stage}-{seed}.pt"


def loss():
    return T.loss_of("A-ctl")


def fresh(seed):
    """A random net: their init, W's seed."""
    import torch

    torch.manual_seed(seed)
    body = E.network(1.0)
    for m in body.modules():
        if isinstance(m, torch.nn.Conv2d):
            torch.nn.init.kaiming_normal_(m.weight, mode="fan_out")
    return build(body)


def cmd_head(a):
    """W's heads on AudioSet's frozen body, eval mode, batch norm untouched."""
    import torch

    from learn import pipeline_fix as P

    out = run_path("head", a.seed)
    if out.exists():
        return print(out.name, "exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    data, tr = FrontData(plugin_rows()), None
    tr = np.arange(len(data.rows))
    torch.set_num_threads(2)
    torch.manual_seed(a.seed)
    net = build(E.load("mn10_as"))
    params = [q for n, q in net.named_parameters() if not n.startswith("body.")]
    for q in net.body.parameters():
        q.requires_grad_(False)
    net.eval()
    t0 = time.time()
    last = T.train(net, data, tr, loss(), a.seed, P.device(), T.HEAD_EPOCHS, T.PLUGIN_LR, params, f"head {a.seed}")
    T.save_state(net, out)
    T.run_record(out.with_suffix(".json"), stage="head", seed=a.seed, epochs=T.HEAD_EPOCHS, loss=last, minutes=(time.time() - t0) / 60)


def cmd_body(a):
    """The whole net from `head`, at their fine-tuning rate, W's 60 epochs, the final state, batch norm in training mode."""
    import torch

    from learn import pipeline_fix as P

    out = run_path("body", a.seed)
    if out.exists():
        return print(out.name, "exists")
    data = FrontData(plugin_rows())
    tr = np.arange(len(data.rows))
    torch.set_num_threads(2)
    net = build(E.load("mn10_as"))
    net.load_state_dict(torch.load(run_path("head", a.seed), map_location="cpu", weights_only=True))
    t0 = time.time()
    last = T.train(net, data, tr, loss(), a.seed, P.device(), T.BODY_EPOCHS, TUNE_LR, None, f"body {a.seed}")
    T.save_state(net, out)
    T.run_record(out.with_suffix(".json"), stage="body", seed=a.seed, epochs=T.BODY_EPOCHS, lr=TUNE_LR, loss=last, minutes=(time.time() - t0) / 60)


def cmd_rand(a):
    """The same net from random weights, W's rate and 60 epochs, the final state."""
    import torch

    from learn import pipeline_fix as P

    out = run_path("rand", a.seed)
    if out.exists():
        return print(out.name, "exists")
    data = FrontData(plugin_rows())
    tr = np.arange(len(data.rows))
    torch.set_num_threads(2)
    net = fresh(a.seed)
    t0 = time.time()
    last = T.train(net, data, tr, loss(), a.seed, P.device(), T.BODY_EPOCHS, T.PLUGIN_LR, None, f"rand {a.seed}")
    T.save_state(net, out)
    T.run_record(out.with_suffix(".json"), stage="rand", seed=a.seed, epochs=T.BODY_EPOCHS, lr=T.PLUGIN_LR, loss=last, minutes=(time.time() - t0) / 60)


def cmd_steps(a):
    """A short trial, nothing saved: the seconds an epoch takes, and that the loss falls."""
    import torch

    from learn import pipeline_fix as P

    rows = plugin_rows()[:256]
    data = FrontData(rows)
    net = build(E.load("mn10_as"))
    t0 = time.time()
    T.train(net, data, np.arange(len(rows)), loss(), a.seed, P.device(), a.epochs, TUNE_LR, None, "trial")
    print(f"{(time.time() - t0) / a.epochs * len(plugin_rows()) / len(rows) / 60:.2f} min an epoch at 1,787 rows", torch.__version__, flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("head", cmd_head), ("body", cmd_body), ("rand", cmd_rand), ("steps", cmd_steps)):
        s = sub.add_parser(name)
        s.add_argument("--seed", type=int, default=T.SEEDS[0], choices=T.SEEDS)
        s.add_argument("--epochs", type=int, default=3)
        s.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
