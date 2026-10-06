"""Phase 0 T of `docs/di-recovery-plan.md`: before an overnight run, does choosing through
the network's rebuilt DI beat choosing through `flatref` on held-out-band renders?

The "recording" is a POC render from a band in the held-out fold (a sampled PR12 setting
through that band's DI). The candidates are the 21 clean factory presets plus template+R.
- Choosing is on 0.5–3.0 s, by the judge through:
  - the rebuilt DI (the network on the recording, at −22.9 LUFS);
  - `flatref` (the recording re-equalised to the fold's average balance, at −22.9 LUFS);
  - the measure's own DI, which gives the oracle.
- Scoring is on 3.0–6.0 s under the average-guitar measure: the true DI re-equalised to
  the fold average, at its own level.

    $TORCH_PY -m learn.direc_check --model ~/ndsp-presets/learn/direc/models-1h/fold0.pt \\
        --fold 0 --out ~/ndsp-presets/learn/direc/check-1h
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

SR = 48000
CACHE = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/direc/cache"))
KILL = pathlib.Path(os.path.expanduser("~/ndsp-presets/runs/kill"))
A, B = (0.5, 3.0), (3.0, 6.0)
LAG = -52           # a DI aligned with the recording (measured; di-recovery-plan.md)


def to_lufs(x, target=-22.9):
    import numpy as np
    import pyloudnorm

    l = pyloudnorm.Meter(SR).integrated_loudness(np.asarray(x, np.float64))
    return x * 10 ** ((target - l) / 20)


def eq_to(x, gain_bins):
    import numpy as np

    from learn.direc import SPEC_N

    n = len(x)
    g = np.interp(np.fft.rfftfreq(n, 1 / SR), np.fft.rfftfreq(SPEC_N, 1 / SR), np.clip(gain_bins, -15, 15))
    return np.fft.irfft(np.fft.rfft(x) * 10 ** (g / 20), n)


def main():
    import numpy as np
    import torch

    import render_preset_panel as RP
    from analysis.aligned import aligned_distance
    from learn import direc as D
    from learn import train as TR
    from learn.di_robustness import smoothed_spectrum
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=pathlib.Path, required=True)
    ap.add_argument("--fold", type=int, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--clips", type=int, default=16)
    args = ap.parse_args()
    out = args.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)

    X = np.load(CACHE / "input.npy", mmap_mode="r")
    Y = np.load(CACHE / "di.npy", mmap_mode="r")
    S = np.load(CACHE / "di_spectrum.npy")
    meta = json.loads((CACHE / "meta.json").read_text())
    fold_of, _ = TR.k3_folds()
    avg = D.fold_average(CACHE, args.fold)
    held = [i for i, m in enumerate(meta) if fold_of.get(m["band"], -1) == args.fold]
    rng = np.random.default_rng(20261006)
    clips = sorted(rng.choice(held, args.clips, replace=False).tolist())

    net = D.build_model()
    net.load_state_dict(torch.load(args.model.expanduser(), map_location="cpu"))
    net.eval()

    pack = load_pack("morgan")

    class PanelRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["panel"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    renderer = PanelRenderer("morgan", process_policy="reuse")
    panel = json.loads((KILL / "pr12-clean" / "index.json").read_text())
    names = sorted({r["candidate"] for r in panel["rows"] if "file" in r and r["candidate"] != "template"})
    menu = RP.candidates(argparse.Namespace(amp="pr12", factory_dir=RP.FACTORY), pack, renderer)
    PanelRenderer.commands = {n: RP.preset_edits(menu[n][0], pack, renderer, "pr12", menu[n][1]) for n in names}

    rows = []
    try:
        for i in clips:
            rec = X[i].astype(np.float64) / 32767
            di = Y[i].astype(np.float64) / 32767
            own = S[i] - S[i].mean()
            measure_di = eq_to(di, avg - own)
            measure_di *= np.sqrt(np.mean(di ** 2)) / np.sqrt(np.mean(measure_di ** 2))
            rebuilt = D.rebuild(net, rec.astype(np.float32), device=torch.device("cpu")).astype(np.float64)
            rebuilt = to_lufs(rebuilt)
            fr = smoothed_spectrum(rec)
            flatref = to_lufs(eq_to(rec, avg - (fr - fr.mean())))
            # how close is each DI to the measure's DI (log-mel, level removed)
            dis = {"rebuilt": rebuilt, "flatref": flatref, "measure": measure_di}
            renders = {}
            for k, d in dis.items():
                renderer.render(d.astype(np.float32), {"panel": "template+R"})   # warm-up
                renders[k] = {n: np.asarray(renderer.render(d.astype(np.float32), {"panel": n}).audio,
                                            np.float64) for n in names}
            def pick(k):
                lag = LAG
                dA = {n: aligned_distance(rec, renders[k][n], dis[k], lag=lag, render_latency=52,
                                          start_s=A[0], end_s=A[1]).distance for n in names}
                ok = {n: v for n, v in dA.items() if v is not None}
                return min(ok, key=ok.get) if ok else None
            dB = {n: aligned_distance(rec, renders["measure"][n], measure_di, lag=LAG, render_latency=52,
                                      start_s=B[0], end_s=B[1]).distance for n in names}
            if dB.get("template+R") is None:
                continue
            row = {"clip": meta[i]["id"], "band": meta[i]["band"]}
            for k in dis:
                p = pick(k)
                row[k] = (math.log(dB[p]) - math.log(dB["template+R"])) if p and dB.get(p) else None
                row[k + "_pick"] = p
            best = min((v for v in dB.values() if v), default=None)
            row["best_B"] = math.log(best) - math.log(dB["template+R"]) if best else None
            rows.append(row)
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items() if not k.endswith("_pick")}, flush=True)
    finally:
        renderer.close()
    summ = {}
    for k in ("rebuilt", "flatref", "measure", "best_B"):
        v = [r[k] for r in rows if r.get(k) is not None]
        summ[k] = {"median": round(statistics.median(v), 4), "mean": round(statistics.mean(v), 4), "n": len(v)}
    paired = [r["rebuilt"] - r["flatref"] for r in rows if r.get("rebuilt") is not None and r.get("flatref") is not None]
    summ["rebuilt_minus_flatref"] = {"median": round(statistics.median(paired), 4),
                                     "better": sum(x < 0 for x in paired), "worse": sum(x > 0 for x in paired),
                                     "n": len(paired)}
    (out / "check.json").write_text(json.dumps({"rows": rows, "summary": summ}, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
