"""C′ for every fold (`docs/cprime-folds-plan.md`): the preflight and the network check.

    .venv/bin/python -m learn.cprime_folds preflight --fold 0     # asserts the split, exits non-zero
    $TORCH_PY -m learn.cprime_folds check MODEL [MODEL ...]       # coherence on set-3 stems
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
D = HOME / "learn/direc"
CACHES = [D / "cache", D / "cache-sw50r", D / "cache-ac20"]
OUT = D / "cprime-folds"
# (train, val, bleed) per fold, recounted by the plan's review from the caches as they were
# built; fold 2 reproduces C′'s own log (38,709 / 10,097 / 37).
EXPECTED = {0: (34792, 14014, 27), 1: (38188, 10618, 29), 2: (38709, 10097, 37), 3: (38204, 10602, 33)}
OUTSIDE_K3 = {"Guitar-TECHS P1"}          # the one band outside the K3 folds; it trains every fold


def split(fold, caches=CACHES):
    """(train, val, bleed, bands outside K3), counted exactly as `learn/direc.py` `fit` does."""
    from learn import train as TR
    from learn.direc import CROPS

    meta = [m for c in caches for m in json.loads((c / "meta.json").read_text())]
    fold_of, band_of = TR.k3_folds()
    f = [fold_of.get(m["band"], -1) for m in meta]
    outside = sorted({m["band"] for m, x in zip(meta, f) if x == -1})
    bleed = sum(1 for part, b in band_of.items()
                if fold_of[b] != fold and (CROPS / part / "backing_instrumental.wav").exists())
    return sum(x != fold for x in f), sum(x == fold for x in f), bleed, outside


def preflight(fold):
    tr, va, bl, outside = split(fold)
    want = EXPECTED[fold]
    ok = (tr, va, bl) == want and set(outside) <= OUTSIDE_K3
    print(f"fold {fold}: train {tr} val {va} bleed {bl} (expected {want}); outside K3 {outside}",
          "OK" if ok else "MISMATCH", flush=True)
    if not ok:
        raise SystemExit(1)


BAND_1_3K = 1


def check(models):
    """The declared network check: the mean, over set 3's 5 usable clean and crunch stem parts
    (which no fold's network trained on; step 3's set-3 parts), of the 1–3 kHz coherence
    between the stem-rebuilt DI and the true DI. As `residual_eval.coherence`, but from the
    stem. (High-gain parts are left out: distortion leaves even the amp track at about 0.03.)"""
    import numpy as np
    import torch

    from learn import confirm_run as CR
    from learn import direc as Dm
    from learn import phase2_set3 as P
    from learn import set3
    from learn.direc_check import to_lufs
    from learn.residual_eval import _aligned, _coherence

    man = json.loads((HOME / "learn/set3/stems/manifest.json").read_text())["parts"]
    ps = {p["slug"]: p for p in set3.parts("development")}
    slugs = sorted(s for s, v in man.items() if v.get("usable") and ps[s]["gain_class"] in ("clean", "crunch"))
    assert len(slugs) == 5, slugs
    nets = {str(m): Dm.load_model(pathlib.Path(m).expanduser()).eval() for m in models}
    out = {}
    for k, net in nets.items():
        rows = []
        for s in slugs:
            di = CR.mono(P.CROPS / s / "di.wav")
            stem = CR.mono(HOME / "learn/set3/stems/htdemucs_6s" / s / "instrumental_guitar.wav")
            rb = to_lufs(Dm.rebuild(net, stem.astype(np.float32), device=torch.device("cpu")).astype(np.float64))
            a, b, _ = _aligned(rb, di, ps[s]["judge_lag_samples"] + P.LATENCY)
            rows.append(_coherence(a, b)[BAND_1_3K])
        out[k] = {"mean_1_3k": round(float(np.mean(rows)), 4), "per_part": dict(zip(slugs, rows))}
        print(f"{k[-60:]:60s} mean 1-3 kHz coherence {out[k]['mean_1_3k']:.4f}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "check.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    old.update(out)
    path.write_text(json.dumps(old, indent=1))
    return out


def verdict(new, seeds):
    """One-sided: a new fold fails if it is below the fold-2 seeds' minimum by more than
    max(the seeds' range, 0.02)."""
    margin = max(max(seeds) - min(seeds), 0.02)
    return new >= min(seeds) - margin


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="step", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--fold", type=int, required=True)
    c = sub.add_parser("check")
    c.add_argument("models", nargs="+")
    a = ap.parse_args(argv)
    preflight(a.fold) if a.step == "preflight" else check(a.models)


if __name__ == "__main__":
    main()
