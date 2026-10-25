"""Stem contamination from stored mels only (zero renders).

For each example: true render mel g (part C, isolated guitar) vs the separator stem mel s
(direct-stems build). Both log-mel dB on part C's grid. offset = median(s - g) over the guitar's
active cells (g within 50 dB of its max). leak_share = share of stem power above the level-shifted
guitar power (power not explained by the true guitar). spec_err = mean |s - g - offset| on active
cells (dB). Usage: python stem_contam.py vsep|train [sep]
"""
import glob, json, os, sys, pathlib
import numpy as np

HOME = pathlib.Path("~/ndsp-presets/learn").expanduser()
part = sys.argv[1]
sep = sys.argv[2] if len(sys.argv) > 2 else "xlance_g"
OUT = pathlib.Path(__file__).with_name(f"contam-{part}-{sep}.jsonl")
done = set()
if OUT.exists():
    done = {json.loads(l)["i"] for l in OUT.open()}

rows = {}
pat = "vsep-mix-*.jsonl" if part == "vsep" else "*-mix-*.jsonl"
for f in glob.glob(str(HOME / "direct-stems/build/rows" / pat)):
    if part == "train" and "vsep" in f:
        continue
    for l in open(f):
        r = json.loads(l)
        if r.get("refused"):
            continue
        rows[r["i"]] = r


def dq(q):
    return q.astype(np.float32) * 0.5 - 112.0


with OUT.open("a") as fh:
    n = 0
    for i, r in sorted(rows.items()):
        if i in done:
            continue
        sp = HOME / f"direct-stems/build/ex/{i // 1000:04d}/{i:07d}-{sep}.npz" if i < 1_000_000 else HOME / f"direct-stems/build/ex/{i // 1000:04d}/{i}-{sep}.npz"
        gp = HOME / f"pretrain-set/examples/{i // 1000:04d}/{i:07d}.npz"
        if not (sp.exists() and gp.exists()):
            continue
        S, G = np.load(sp), np.load(gp)
        out = {"i": i, "section": r["section"], "band": r["band"], "split": r["split"], "ratio_db": r["ratio_db"],
               "vocals": r["vocals"], "mastered": r["mastered"], "base": r["base"], "amp": r["amp"]}
        for h in "AB":
            g, s = dq(G[f"g{h}"]), dq(S[f"s{h}"])
            n_ = min(g.shape[1], s.shape[1])
            g, s = g[:, :n_], s[:, :n_]
            if h == "A":
                g, s = g[:, 100:], s[:, 100:]      # half A's first second is masked in training
            act = g > g.max() - 50
            if act.sum() < 50:
                out[f"leak_{h}"] = None
                continue
            off = float(np.median((s - g)[act]))
            pg = 10 ** ((g + off) / 10)
            ps = 10 ** (s / 10)
            out[f"leak_{h}"] = round(float(np.maximum(ps - pg, 0).sum() / ps.sum()), 4)
            out[f"err_{h}"] = round(float(np.abs(s - g - off)[act].mean()), 3)
            out[f"off_{h}"] = round(off, 2)
            out[f"act_{h}"] = round(float(act.mean()), 3)
        fh.write(json.dumps(out) + "\n")
        n += 1
        if n % 2000 == 0:
            fh.flush()
            print(n, flush=True)
print("done", n)
