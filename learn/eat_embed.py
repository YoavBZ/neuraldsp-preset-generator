"""Frozen EfficientAT statistics of the rebuilt inputs (`docs/efficientat-plan.md`, task S1.2). MPS, announced.

    $TORCH_PY -m learn.eat_embed --net mn10_as --sets clean wide real
    $TORCH_PY -m learn.eat_embed --net mn04_as --sets clean wide --stats g16 f6      # the stats S3 chose

One array per statistic: PF/eat/embed/<net>/<set>/<stat>.npy, float16 [inputs, 2 halves, dims], in `keys_of(set)`'s order.
`gL`: each channel's mean and std at layer L over frequency and time. `fL`: the same over time only, frequency kept. `logits`:
AudioSet's 527 outputs. Half A's first second is left out, as W's input masks it. `mn10_rand`, the untrained control, and
`mn10_im`, whose batch norm learned image statistics, re-estimate batch norm on CAL_INPUTS inputs of `clean` and `wide`; the
AudioSet nets are used as trained.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import eat_build as EB  # noqa: E402
from learn import eat_net as E  # noqa: E402

G_LAYERS = (1, 3, 6, 12, 15, 16)
F_LAYERS = (3, 5, 6, 11, 12, 13, 15)                    # 5, 11, 13 and 15 are the blocks EfficientAT's embedding paper pools
STATS = (*(f"g{q}" for q in G_LAYERS), *(f"f{q}" for q in F_LAYERS), "logits")
SKIP_A = 100                                            # `pretrain_set.MASK_A_FRAMES`
BATCH = 64
RAND_SEED = 20261042
CAL_INPUTS = 512


def embed_root():
    return EB.front_root().parent / "embed"


def keys_of(kind):
    """[(key, path)] of a set's inputs, in a fixed order."""
    from learn import bakeoff as B
    from learn import pipeline_fix as P

    if kind == "real":
        return [((u, v), EB.real_path(u, v)) for u, _, _ in P.dfix_units() for v in range(P.DFIX_K)]
    if kind == "amp":
        return [((u, -1), EB.amp_path(u)) for u, _, _ in P.dfix_units()]
    if kind == "reads":                                 # read 2's units with no labelled row, variant 0 only
        return [((u, 0), EB.real_path(u, 0)) for u, _, _ in P.dfix_read_only(P.dfix_units(), P.goat_read_units())]
    rows, _ = B.plugin_set()
    if kind == "clean":
        return [((r["i"], -1), EB.clean_path(r["i"])) for r in rows]
    return [((r["i"], k), EB.wide_path(r["i"], k)) for r in rows for k in range(EB.WIDE_K)]


def stats_of(maps_, logits):
    """{stat: [n, dims]} from one batch's maps."""
    out = {"logits": logits}
    import torch

    for q in G_LAYERS:
        m = maps_[q]
        out[f"g{q}"] = torch.cat([m.mean((2, 3)), m.std((2, 3))], 1)
    for q in F_LAYERS:
        m = maps_[q]
        out[f"f{q}"] = torch.cat([m.mean(3), m.std(3)], 1).flatten(1)
    return out


def read_input(path):
    z = np.load(path)
    return EB.dequant(z["sA"])[:, SKIP_A:], EB.dequant(z["sB"])


def calibrate(net, paths, dev):
    """Batch norm's running statistics re-estimated on our inputs, weights untouched."""
    import torch

    for m in net.modules():
        if isinstance(m, torch.nn.BatchNorm2d):
            m.reset_running_stats()
            m.momentum = None                           # a plain average over the batches
    net.train()
    with torch.no_grad():
        for j in range(0, len(paths), BATCH):
            x = np.stack([read_input(p)[1] for p in paths[j:j + BATCH]])
            net(torch.tensor(x)[:, None].to(dev))
    return net.eval()


def build(name, dev):
    import torch

    if name == "mn10_rand":
        torch.manual_seed(RAND_SEED)
        net = E.network(1.0)
        for m in net.modules():
            if isinstance(m, torch.nn.Conv2d):
                torch.nn.init.kaiming_normal_(m.weight, mode="fan_out")
        keep = "calibrate"
    else:
        net = E.load(name)
        keep = "calibrate" if name == "mn10_im" else None
    net = net.to(dev)
    if keep:
        paths = [p for kind in ("clean", "wide") for _, p in keys_of(kind)]
        pick = np.random.default_rng(RAND_SEED).choice(len(paths), CAL_INPUTS, replace=False)
        net = calibrate(net, [paths[int(i)] for i in sorted(pick)], dev)
    return net.eval()


def run_set(net, name, kind, stats, dev):
    import torch

    keys = keys_of(kind)
    out = embed_root() / name / kind
    todo = [s for s in stats if not (out / f"{s}.npy").exists()]
    if not todo:
        return
    out.mkdir(parents=True, exist_ok=True)
    t0, arrays = time.time(), {}
    with ThreadPoolExecutor(4) as pool:
        for j in range(0, len(keys), BATCH):
            got = list(pool.map(read_input, [p for _, p in keys[j:j + BATCH]]))
            for half in (0, 1):
                x = torch.tensor(np.stack([g[half] for g in got]))[:, None].to(dev)
                maps_, logits = E.maps(net, x)
                for s, v in stats_of(maps_, logits).items():
                    if s not in todo:
                        continue
                    if s not in arrays:
                        arrays[s] = np.zeros((len(keys), 2, v.shape[1]), np.float16)
                    arrays[s][j:j + len(got), half] = v.cpu().numpy().astype(np.float16)
            if j % (BATCH * 100) == 0:
                print(f"{name} {kind} {j}/{len(keys)}: {(time.time() - t0) / max(1, j + BATCH) * 1000:.1f} ms an input", flush=True)
    for s, v in arrays.items():
        if not np.isfinite(v).all():
            raise SystemExit(f"{name} {kind} {s}: not finite")
        tmp = out / f"{s}.tmp.npy"
        np.save(tmp, v)
        tmp.replace(out / f"{s}.npy")
    (out / "keys.json").write_text(json.dumps([list(k) for k, _ in keys]))
    print(f"{name} {kind} done, {len(keys)} inputs, {(time.time() - t0) / 60:.1f} min", flush=True)


def main(argv=None):
    import torch

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--net", required=True, choices=(*E.NAMES, "mn10_rand"))
    ap.add_argument("--sets", nargs="+", choices=("clean", "wide", "real", "amp", "reads"), required=True)
    ap.add_argument("--stats", nargs="+", default=list(STATS), choices=STATS)
    ap.add_argument("--dev", default="mps" if torch.backends.mps.is_available() else "cpu")
    a = ap.parse_args(argv)
    net = build(a.net, a.dev)
    for kind in a.sets:
        run_set(net, a.net, kind, a.stats, a.dev)


if __name__ == "__main__":
    main()
