"""Score the POC model with K3's test (`docs/preset-model-poc-plan.md`).

    # 1. predictions (a torch interpreter)
    $TORCH_PY -m learn.evaluate predict --models ~/ndsp-presets/learn/poc/models \\
        --out ~/ndsp-presets/learn/poc/eval
    # 2. renders and the judge (main .venv; drives the plugin)
    .venv/bin/python -m learn.evaluate score --out ~/ndsp-presets/learn/poc/eval

For each of K3's 28 parts, the fold model that never saw the part's band reads the part's
real amp-track crop (1–10 s, 4-s windows every 0.5 s, outputs averaged). The prediction
is rendered through the part's DI crop and scored by the judge against the amp track.
The comparators are template+R (the panel's render, re-scored here) and K3's constant
(its rows). The shuffled control is the same model fed three other bands' amp tracks,
rendered through this part's DI.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import pr12  # noqa: E402

KILL = pathlib.Path(os.path.expanduser("~/ndsp-presets/runs/kill"))
CROPS = pathlib.Path(os.path.expanduser("~/ndsp-presets/references/validation-crops"))
BAND_SETS = ("recording", "union")
SR = 48000
LATENCY = 52


def k3():
    """K3's parts, bands, lags and rows (judge, both band sets), keyed by recogniser."""
    j = json.loads((KILL / "k-judge-pr12-clean.json").read_text())
    rows = {bs: {r["part"]: r for r in j["k3"][bs]["1nn"]["rows"]} for bs in BAND_SETS}
    rec = {bs: {name: {r["part"]: r for r in v["rows"]} for name, v in j["k3"][bs].items()}
           for bs in BAND_SETS}
    parts = sorted(rows["recording"])
    lags = {p: j["lags"][p]["lag"] for p in parts}
    band = {p: rows["recording"][p]["band"] for p in parts}
    return parts, band, lags, rows, rec


def shuffled_sources(parts, band, n=3):
    """One part from each of three other bands per part, fixed by a seed."""
    rng = random.Random(20261006)
    out = {}
    for p in parts:
        bands = sorted({band[o] for o in parts if band[o] != band[p]})
        out[p] = [rng.choice(sorted(o for o in parts if band[o] == b))
                  for b in rng.sample(bands, n)]
    return out


# --- predictions --------------------------------------------------------------

def predict(models: pathlib.Path, out: pathlib.Path, tag: str):
    import numpy as np
    import soundfile as sf
    import torch

    from learn import train as T

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    fold_of, _ = T.k3_folds()
    parts, band, lags, rows, rec = k3()
    frontend = T.Frontend(device)
    nets = {}
    for f in range(4):
        net = T.build_model().to(device)
        net.load_state_dict(torch.load(models / f"fold{f}.pt", map_location=device))
        net.eval()
        nets[f] = net

    def read(part):
        y, sr = sf.read(str(CROPS / part / "reference.wav"), dtype="float32", always_2d=True)
        y = y.mean(axis=1)
        return T.to32k(y, sr) if sr != T.SR else y

    def run(net, y):
        seg = y[int(1.0 * T.SR):int(10.0 * T.SR)]
        starts = range(0, len(seg) - T.CROP + 1, T.SR // 2)
        w = torch.tensor(np.stack([seg[s:s + T.CROP] for s in starts]), device=device)
        with torch.no_grad():
            cont, binary, cats = net(frontend(w))
        return {"cont": cont.mean(0).tolist(),
                "binary": torch.sigmoid(binary).mean(0).tolist(),
                "cat": [torch.softmax(c, -1).mean(0).tolist() for c in cats]}

    audio = {p: read(p) for p in parts}
    shuffled = shuffled_sources(parts, band)
    preds = {}
    for p in parts:
        net = nets[fold_of[band[p]]]
        preds[p] = {"own": run(net, audio[p]),
                    "shuffled": {o: run(net, audio[o]) for o in shuffled[p]}}
    out.mkdir(parents=True, exist_ok=True)
    (out / f"predictions-{tag}.json").write_text(json.dumps(preds))
    print(f"predicted {len(preds)} parts")


# --- renders and scoring ------------------------------------------------------------

def mono(path):
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    assert sr == SR
    return x.mean(axis=1)


def score(out: pathlib.Path, tag: str):
    import numpy as np
    import pyloudnorm
    import soundfile as sf

    from analysis.aligned import aligned_distance
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    parts, band, lags, rows, rec = k3()
    preds = json.loads((out / f"predictions-{tag}.json").read_text())
    panel = json.loads((KILL / "pr12-clean" / "index.json").read_text())
    files = {(r["part"], r["candidate"]): r["file"] for r in panel["rows"] if "file" in r}

    pack = load_pack("morgan")
    writable = {k for k, spec in pack.parameters.items()
                if spec.writable and spec.kind not in ("path", "string", "internal")}
    template = {k: v for k, v in pr12.template_state().items() if k in writable}

    class R(AudioUnitRenderer):
        command = None

        def _state_command(self, settings):
            return self.command

    renderer = R("morgan", process_policy="reuse")
    meter = pyloudnorm.Meter(SR)
    render_dir = out / f"renders-{tag}"
    render_dir.mkdir(parents=True, exist_ok=True)

    def render(part, pred, input_gain, name):
        path = render_dir / f"{part}--{name}.wav"
        if path.exists():
            return mono(path)
        s, _ = pr12.decode(pred["cont"], pred["binary"], pred["cat"])
        renderer.command = pr12.render_command(s, template, input_gain)
        di = mono(CROPS / part / "di.wav").astype(np.float32)
        y = np.asarray(renderer.render(di, {}).audio, dtype=np.float64)
        y = y.mean(axis=1) if y.ndim == 2 else y
        sf.write(path, y, SR, subtype="FLOAT")
        return y

    def dist(part, x):
        ref = mono(CROPS / part / "reference.wav")
        di = mono(CROPS / part / "di.wav")
        return {bs: aligned_distance(ref, x, di, lag=lags[part], render_latency=LATENCY,
                                     start_s=1.0, end_s=10.0, bands=bs).distance
                for bs in BAND_SETS}

    results = {}
    try:
        warm = mono(CROPS / parts[0] / "di.wav").astype(np.float32)
        renderer.command = pr12.render_command(pr12.from_state(template, template), template, 0.0)
        renderer.render(warm, {})                                    # warm-up, discarded
        for p in parts:
            di = mono(CROPS / p / "di.wav")
            di_lufs = float(meter.integrated_loudness(di[int(1.0 * SR):]))
            own = preds[p]["own"]
            _, drive = pr12.decode(own["cont"], own["binary"], own["cat"])
            d_t = dist(p, mono(files[(p, "template+R")]))
            d_m = dist(p, render(p, own, drive, "model"))
            d_l = dist(p, render(p, own, drive - (di_lufs - pr12.ASSUMED_LUFS), "model-level"))
            d_s = []
            for o, pred in preds[p]["shuffled"].items():
                _, dr = pr12.decode(pred["cont"], pred["binary"], pred["cat"])
                d_s.append(dist(p, render(p, pred, dr, f"shuffled-{o}")))
            row = {"part": p, "band": band[p], "di_lufs": di_lufs, "drive": drive}
            # Re-scoring K3's own 1-NN pick must reproduce its recorded row.
            pick = rows["recording"][p]["pick"]
            d_k = dist(p, mono(files[(p, pick)]))
            row["k3_check"] = {bs: (math.log(d_k[bs]) - math.log(d_t[bs]) - rows[bs][p]["model"])
                               if d_k[bs] and d_t[bs] else None for bs in BAND_SETS}
            for bs in BAND_SETS:
                if d_t[bs] is None or d_m[bs] is None:
                    row[bs] = None
                    continue
                lt = math.log(d_t[bs])
                sh = [math.log(d[bs]) - lt for d in d_s if d[bs] is not None]
                row[bs] = {"template": d_t[bs], "model": math.log(d_m[bs]) - lt,
                           "model_level": (math.log(d_l[bs]) - lt) if d_l[bs] else None,
                           "shuffled": statistics.mean(sh) if sh else None,
                           "constant": rows[bs][p]["constant"],
                           "k3": {name: r[p]["model"] for name, r in rec[bs].items()}}
            results[p] = row
            print(p, {bs: (round(row[bs]["model"], 3) if row[bs] else None) for bs in BAND_SETS},
                  flush=True)
    finally:
        renderer.close()
    summary = summarise(results)
    (out / f"results-{tag}.json").write_text(json.dumps({"rows": results, "summary": summary}, indent=1))
    print(json.dumps(summary, indent=1))


def summarise(results):
    """K3's rule and statistics. A part the judge refuses for the model, but not for
    template+R, counts as a loss rather than leaving the count."""
    sys.path.insert(0, str(PLUGIN_ROOT / "research"))
    import kill_tests as K

    out = {}
    for bs in BAND_SETS:
        rows, refused = [], []
        for r in results.values():
            v = r.get(bs)
            if v is None:
                refused.append(r["part"])
                continue
            rows.append(dict(v, band=r["band"]))
        n = len(rows) + len(refused)
        stat = K.band_stat(rows, "model")
        lt = lambda a, b: a is not None and b is not None and a < b
        better_t = sum(lt(r["model"], 0.0) for r in rows)
        better_s = sum(lt(r["model"], r["shuffled"]) for r in rows)
        better_c = sum(lt(r["model"], r["constant"]) for r in rows)
        m = stat["band_median_log_ratio"] if stat else None
        out[bs] = {
            "model_vs_templateR": stat,
            "model_level_informed_vs_templateR": K.band_stat(rows, "model_level"),
            "shuffled_vs_templateR": K.band_stat(rows, "shuffled"),
            "constant_vs_templateR": K.band_stat(rows, "constant"),
            "k3_vs_templateR": {name: K.band_stat([dict(r, x=r["k3"][name]) for r in rows], "x")
                                for name in rows[0]["k3"]} if rows else {},
            "part_median_log_ratio": round(statistics.median(r["model"] for r in rows), 4),
            "parts": n, "refused": refused,
            "parts_better_than_templateR": better_t,
            "parts_better_than_shuffled": better_s,
            "parts_better_than_constant": better_c,
            "pass": bool(m is not None and m <= math.log(0.9) and better_t > n / 2
                         and better_s > n / 2 and better_c > n / 2),
        }
    out["pass"] = all(out[bs]["pass"] for bs in BAND_SETS)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("predict")
    p.add_argument("--models", type=pathlib.Path, required=True)
    p.add_argument("--out", type=pathlib.Path, required=True)
    p.add_argument("--tag", default="run1")
    s = sub.add_parser("score")
    s.add_argument("--out", type=pathlib.Path, required=True)
    s.add_argument("--tag", default="run1")
    args = ap.parse_args()
    if args.cmd == "predict":
        predict(args.models.expanduser(), args.out.expanduser(), args.tag)
    else:
        score(args.out.expanduser(), args.tag)


if __name__ == "__main__":
    main()
