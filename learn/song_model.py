"""Arm B's model: settings from a song's stem and mix (`docs/song-settings-plan.md`, arm B).

    $TORCH_PY -m learn.song_model train --fold 0 [--half-data]
    $TORCH_PY -m learn.song_model predict --fold 0            # step 3's parts of that fold

The input is one half (4.5 s) as a 2 × MELS × frames log-mel (stem and mix, level kept), the
two LUFS values, the amp (3) and the class start (2). Heads:
- continuous settings: a 4-component diagonal mixture density on the 0–1 scale, over the union of
  the three amps' settings; the loss masks the settings that don't exist on the example's amp;
- switches: a logit each;
- mics: a 10-way softmax each.
One preset = the heaviest component's mean, each switch > 0.5, each mic's top choice.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import knob_ceiling as K  # noqa: E402
from learn import song_bank as B  # noqa: E402

OUT = B.OUT.parent / "models"
K_MIX = 4
AMPS = list(K.AMPS)
CLASSES = ["clean", "crunch"]
EPOCHS, BATCH, LR, PATIENCE, SEED = 40, 64, 1e-3, 5, 20261018


def layout():
    """(continuous names, switch names, mic names) over the union of the amps' spaces."""
    cont, sw, cat = [], [], []
    for amp in AMPS:
        for d in K.space(amp):
            if d.kind in ("cont", "log") and d.name not in cont:
                cont.append(d.name)
            elif d.kind == "switch" and d.name not in sw:
                sw.append(d.name)
            elif d.kind == "cat" and d.name not in cat:
                cat.append(d.name)
    return cont, sw, cat


CONT, SW, CAT = layout()
MICS = list(K.MICS)


def encode(label):
    """label {name: unit float | stored string} -> (cont, cont_mask, sw, sw_mask, cat, cat_mask)."""
    import numpy as np

    c = np.zeros(len(CONT), np.float32)
    cm = np.zeros(len(CONT), np.float32)
    s = np.zeros(len(SW), np.float32)
    sm = np.zeros(len(SW), np.float32)
    k = np.zeros(len(CAT), np.int64)
    km = np.zeros(len(CAT), np.float32)
    for i, n in enumerate(CONT):
        if n in label:
            c[i], cm[i] = float(label[n]), 1.0
    for i, n in enumerate(SW):
        if n in label:
            s[i], sm[i] = float(str(label[n]).lower() in ("true", "1")), 1.0
    for i, n in enumerate(CAT):
        if n in label and str(label[n]) in MICS:
            k[i], km[i] = MICS.index(str(label[n])), 1.0
    return c, cm, s, sm, k, km


def build_model():
    import torch
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
            self.body = nn.Sequential(Block(2, 32), Block(32, 64), Block(64, 128), Block(128, 192))
            d = 192 * (96 // 16) * 2 + len(AMPS) + len(CLASSES) + 2
            self.trunk = nn.Sequential(nn.Linear(d, 512), nn.ReLU(), nn.Dropout(0.2), nn.Linear(512, 512), nn.ReLU())
            self.pi = nn.Linear(512, K_MIX)
            self.mu = nn.Linear(512, K_MIX * len(CONT))
            self.ls = nn.Linear(512, K_MIX * len(CONT))
            self.sw = nn.Linear(512, len(SW))
            self.cat = nn.ModuleList([nn.Linear(512, len(MICS)) for _ in CAT])

        def forward(self, x, cond):
            h = self.body(x)
            h = torch.cat([h.mean(-1), h.std(-1)], dim=1).flatten(1)
            h = self.trunk(torch.cat([h, cond], dim=1))
            n = len(CONT)
            return (torch.log_softmax(self.pi(h), -1), torch.sigmoid(self.mu(h)).view(-1, K_MIX, n),
                    self.ls(h).view(-1, K_MIX, n).clamp(-6, 1), self.sw(h), [c(h) for c in self.cat])

    return Net()


def norm_feat(f):
    """dB features to about unit scale."""
    return (f.astype("float32") + 60.0) / 30.0


def cond_vec(amp, cls, lufs):
    import numpy as np

    v = np.zeros(len(AMPS) + len(CLASSES) + 2, np.float32)
    v[AMPS.index(amp)] = 1
    v[len(AMPS) + CLASSES.index(cls)] = 1
    v[-2:] = (np.asarray(lufs, np.float32) + 20.0) / 10.0
    return v


def bank_index():
    """[(i, fold, band, amp, class, label)] for every example with features and a label."""
    ex = json.loads((B.OUT / "examples.json").read_text())
    out = []
    for e in ex:
        f = B.OUT / "features" / f"{e['i']:05d}.npz"
        lab = B.OUT / "renders" / f"{e['i']:05d}.json"
        if f.exists() and lab.exists():
            out.append((e["i"], e["fold"], e["window"]["band"], e["amp"], e["class"],
                        json.loads(lab.read_text())["label"]))
    return out


def loss_fn(out, c, cm, s, sm, k, km):
    import torch
    import torch.nn.functional as F

    logpi, mu, ls, swl, catl = out
    z = (c.unsqueeze(1) - mu) / ls.exp()
    lp = (-0.5 * z ** 2 - ls - 0.5 * math.log(2 * math.pi)) * cm.unsqueeze(1)
    nll = -torch.logsumexp(logpi + lp.sum(-1), dim=-1)
    nll = (nll / cm.sum(-1).clamp(min=1)).mean()
    bce = (F.binary_cross_entropy_with_logits(swl, s, reduction="none") * sm).sum() / sm.sum().clamp(min=1)
    ce = sum((F.cross_entropy(catl[j], k[:, j], reduction="none") * km[:, j]).sum() / km[:, j].sum().clamp(min=1)
             for j in range(len(CAT)))
    return nll + bce + ce


def train(fold, half_data=False):
    import numpy as np
    import torch

    torch.manual_seed(SEED + fold)
    rng = random.Random(SEED + fold)
    idx = [r for r in bank_index() if r[1] != fold]
    if half_data:
        rng.shuffle(idx)
        idx = idx[:len(idx) // 2]
    dev_bands = sorted({r[2] for r in idx if not r[2].startswith("Guitar-TECHS")})
    rng.shuffle(dev_bands)
    val_bands = set(dev_bands[:max(1, len(dev_bands) // 10)])
    tr = [r for r in idx if r[2] not in val_bands]
    va = [r for r in idx if r[2] in val_bands]
    assert not any(r[1] == fold for r in tr + va)

    def load(rows):
        X, C, Y = [], [], []
        for i, f, band, amp, cls, label in rows:
            d = np.load(B.OUT / "features" / f"{i:05d}.npz")
            for h in "AB":
                X.append(norm_feat(d[f"feat{h}"]))
                C.append(cond_vec(amp, cls, d[f"lufs{h}"]))
                Y.append(encode(label))
        return np.stack(X), np.stack(C), [np.stack(z) for z in zip(*Y)]

    Xt, Ct, Yt = load(tr)
    Xv, Cv, Yv = load(va)
    dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    net = build_model().to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    tag = f"fold{fold}" + ("-half" if half_data else "")
    out = OUT / tag
    out.mkdir(parents=True, exist_ok=True)
    best, bad, log = math.inf, 0, []

    def batches(X, C, Y, shuffle):
        order = np.random.default_rng(len(log)).permutation(len(X)) if shuffle else np.arange(len(X))
        for j in range(0, len(X), BATCH):
            b = order[j:j + BATCH]
            yield (torch.tensor(X[b], device=dev), torch.tensor(C[b], device=dev),
                   [torch.tensor(y[b], device=dev) for y in Y])

    for epoch in range(EPOCHS):
        net.train()
        tl = []
        for x, c, y in batches(Xt, Ct, Yt, True):
            loss = loss_fn(net(x, c), *y)
            opt.zero_grad()
            loss.backward()
            g = torch.nn.utils.clip_grad_norm_(net.parameters(), 1e9)          # the norm only
            if torch.isfinite(g):
                for p in net.parameters():                                       # clip by hand
                    if p.grad is not None:
                        p.grad.mul_(min(1.0, 5.0 / (float(g) + 1e-9)))
                opt.step()
            tl.append(float(loss))
        net.eval()
        with torch.no_grad():
            vl = [float(loss_fn(net(x, c), *y)) for x, c, y in batches(Xv, Cv, Yv, False)]
        v = sum(vl) / max(1, len(vl))
        log.append({"epoch": epoch, "train": sum(tl) / len(tl), "val": v})
        print(tag, log[-1], flush=True)
        if v < best - 1e-4:
            best, bad = v, 0
            torch.save(net.state_dict(), out / "model.pt")
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    (out / "log.json").write_text(json.dumps({"log": log, "train_examples": len(tr), "val_examples": len(va),
                                              "val_bands": sorted(val_bands)}, indent=1))


def load_net(fold, half=False):
    import torch

    net = build_model()
    net.load_state_dict(torch.load(OUT / (f"fold{fold}" + ("-half" if half else "")) / "model.pt", map_location="cpu"))
    return net.eval()


def predict_settings(net, feat, lufs_v, amp, cls, S):
    """(settings on top of S, diagnostics) from one half's features."""
    import numpy as np
    import torch

    x = torch.tensor(norm_feat(feat)[None])
    c = torch.tensor(cond_vec(amp, cls, lufs_v)[None])
    with torch.no_grad():
        logpi, mu, ls, swl, catl = net(x, c)
    pi = logpi.exp()[0].numpy()
    top = int(pi.argmax())
    mean = (pi[:, None] * mu[0].numpy()).sum(0)
    x_out = dict(S)
    space = {d.name: d for d in K.space(amp, S)}
    for i, n in enumerate(CONT):
        if n in space:
            d = space[n]
            x_out[(d.module, d.key)] = K.fmt(d.from_unit(float(mu[0, top, i])))
    for i, n in enumerate(SW):
        if n in space:
            d = space[n]
            x_out[(d.module, d.key)] = d.values[int(float(torch.sigmoid(swl[0, i])) > 0.5)]
    for j, n in enumerate(CAT):
        if n in space:
            d = space[n]
            x_out[(d.module, d.key)] = MICS[int(catl[j][0].argmax())]
    diag = {"top_weight": float(pi[top]),
            "top_vs_mixture_mean": float(np.abs(mu[0, top].numpy() - mean).mean())}
    return x_out, diag


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("train",))
    ap.add_argument("--fold", type=int, required=True)
    ap.add_argument("--half-data", action="store_true")
    a = ap.parse_args(argv)
    train(a.fold, a.half_data)


if __name__ == "__main__":
    main()
