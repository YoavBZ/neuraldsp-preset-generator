"""Phase 2 of `docs/di-recovery-plan.md` on K1's 25 clean PR12 parts: choose a menu preset
through a DI rebuilt from the recording, and score it under the average-guitar measure.

Every DI that enters is built per part from that part's K3 fold, with the fold's frozen
average balance (`learn/direc.py` `fold_average`, from training DIs only):
- **measure:** the true DI re-equalised to the fold average, at its own level. Scoring
  (half B, the part's lag) and the oracle (half A) both use it.
- **flatref:** the amp track re-equalised to the fold average, at −22.9 LUFS.
- **flatstem:** the separated stem (htdemucs_6s, instrumental), likewise; usable parts
  only.
- **net:** the fold's network on the amp track, at −22.9 LUFS.
- **netstem:** the fold's network on the stem, at −22.9 LUFS.

Choosing through a rebuilt DI is done on half A against the recording it was rebuilt
from (amp track or stem), with lag −52. Renders are cached by (part, DI kind), so
the network's renders can be added after the others.

    $TORCH_PY -m learn.phase2 render --kinds measure flatref flatstem
    $TORCH_PY -m learn.phase2 render --kinds net netstem --models ~/ndsp-presets/learn/direc/models-final
    $TORCH_PY -m learn.phase2 score
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

SR, LATENCY = 48000, 52
KILL = pathlib.Path(os.path.expanduser("~/ndsp-presets/runs/kill"))
CROPS = pathlib.Path(os.path.expanduser("~/ndsp-presets/references/validation-crops"))
STEMS = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/poc/stems"))
CACHE = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/direc/cache"))
OUT = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/direc/phase2"))
HALF_A, HALF_B = (1.0, 5.5), (5.5, 10.0)
BAND_SETS = ("recording", "union")
REBUILT = {"flatref": "ref", "flatstem": "stem", "net": "ref", "netstem": "stem"}


def mono(path):
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    assert sr == SR
    return x.mean(axis=1)


def parts():
    j = json.loads((KILL / "k-judge-pr12-clean.json").read_text())
    rows = {r["part"]: r for r in j["k1"]["recording"]["rows"]}
    return sorted(rows), {p: rows[p]["band"] for p in rows}, {p: j["lags"][p]["lag"] for p in rows}


def stem_usable():
    m = json.loads((STEMS / "manifest.json").read_text())
    return {p for p, v in m["parts"].items() if v.get("usable")}


def recording(part, source):
    if source == "stem":
        return mono(STEMS / "htdemucs_6s" / part / "instrumental_guitar.wav")
    return mono(CROPS / part / "reference.wav")


def build_di(kind, part, fold, nets=None):
    import numpy as np

    from learn import direc as D
    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs

    avg = D.fold_average(CACHE, fold)
    if kind == "measure":
        di = mono(CROPS / part / "di.wav")
        own = smoothed_spectrum(di)
        y = eq_to(di, avg - (own - own.mean()))
        return y * math.sqrt(np.mean(di ** 2) / np.mean(y ** 2))
    rec = recording(part, REBUILT[kind])
    if kind.startswith("flat"):
        own = smoothed_spectrum(rec)
        return to_lufs(eq_to(rec, avg - (own - own.mean())))
    import torch

    y = D.rebuild(nets[fold], rec.astype(np.float32), device=torch.device("cpu")).astype(np.float64)
    return to_lufs(y)


def render(kinds, models):
    import numpy as np
    import soundfile as sf
    import torch

    import render_preset_panel as RP
    from learn import direc as D
    from learn import train as TR
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    ps, band, lags = parts()
    fold_of, _ = TR.k3_folds()
    usable = stem_usable()
    nets = {}
    if any(k.startswith("net") for k in kinds):
        for f in range(4):
            net = D.build_model()
            net.load_state_dict(torch.load(pathlib.Path(models).expanduser() / f"fold{f}.pt",
                                           map_location="cpu"))
            net.eval()
            nets[f] = net
    pack = load_pack("morgan")

    class PanelRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["panel"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    r = PanelRenderer("morgan", process_policy="reuse")
    panel = json.loads((KILL / "pr12-clean" / "index.json").read_text())
    names = sorted({x["candidate"] for x in panel["rows"] if "file" in x and x["candidate"] != "template"})
    menu = RP.candidates(argparse.Namespace(amp="pr12", factory_dir=RP.FACTORY), pack, r)
    PanelRenderer.commands = {n: RP.preset_edits(menu[n][0], pack, r, "pr12", menu[n][1]) for n in names}
    try:
        for p in ps:
            f = fold_of[band[p]]
            for kind in kinds:
                if REBUILT.get(kind) == "stem" and p not in usable:
                    continue
                d = OUT / kind / p
                if (d / "done").exists():
                    continue
                d.mkdir(parents=True, exist_ok=True)
                di = build_di(kind, p, f, nets)
                np.save(d / "di.npy", di)
                r.render(di.astype(np.float32), {"panel": "template+R"})        # warm-up
                for n in names:
                    sf.write(d / f"{RP._slug(n)}.wav", np.asarray(r.render(di.astype(np.float32),
                                                                         {"panel": n}).audio), SR,
                             subtype="FLOAT")
                (d / "done").write_text("")
                print(p, kind, flush=True)
    finally:
        r.close()


def score():
    import numpy as np

    import kill_tests as K
    import render_preset_panel as RP
    from analysis.aligned import aligned_distance

    ps, band, lags = parts()
    panel = json.loads((KILL / "pr12-clean" / "index.json").read_text())
    names = sorted({x["candidate"] for x in panel["rows"] if "file" in x and x["candidate"] != "template"})
    j = json.loads((KILL / "k-judge-pr12-clean.json").read_text())
    k1 = {bs: {x["part"]: x for x in j["k1"][bs]["rows"]} for bs in BAND_SETS}
    out = {}
    for bs in BAND_SETS:
        rows = []
        for p in ps:
            mdir = OUT / "measure" / p
            if not (mdir / "done").exists():
                continue
            mdi = np.load(mdir / "di.npy")
            ref = recording(p, "ref")
            dB = {n: aligned_distance(ref, mono(mdir / f"{RP._slug(n)}.wav"), mdi, lag=lags[p],
                                      render_latency=LATENCY, start_s=HALF_B[0], end_s=HALF_B[1],
                                      bands=bs).distance for n in names}
            dA = {n: aligned_distance(ref, mono(mdir / f"{RP._slug(n)}.wav"), mdi, lag=lags[p],
                                      render_latency=LATENCY, start_s=HALF_A[0], end_s=HALF_A[1],
                                      bands=bs).distance for n in names}
            if dB.get("template+R") is None:
                continue
            lt = math.log(dB["template+R"])
            row = {"part": p, "band": band[p]}

            def score_pick(n):
                return (math.log(dB[n]) - lt) if n and dB.get(n) else None

            okA = {n: v for n, v in dA.items() if v}
            row["oracle"] = score_pick(min(okA, key=okA.get)) if okA else None
            row["best_B"] = min((math.log(v) - lt for v in dB.values() if v), default=None)
            row["constant"] = score_pick(k1[bs][p]["constant_preset"]) if p in k1[bs] else None
            for kind, src in REBUILT.items():
                d = OUT / kind / p
                if not (d / "done").exists():
                    continue
                di = np.load(d / "di.npy")
                rec = recording(p, src)
                dk = {n: aligned_distance(rec, mono(d / f"{RP._slug(n)}.wav"), di, lag=-LATENCY,
                                          render_latency=LATENCY, start_s=HALF_A[0], end_s=HALF_A[1],
                                          bands=bs).distance for n in names}
                ok = {n: v for n, v in dk.items() if v}
                pick = min(ok, key=ok.get) if ok else None
                row[kind] = score_pick(pick)
                row[kind + "_pick"] = pick
            rows.append(row)
        keys = ["oracle", "best_B", "constant"] + list(REBUILT)
        summ = {k: K.band_stat(rows, k) for k in keys}
        for a, b in (("net", "flatref"), ("netstem", "flatstem")):
            pr = [dict(band=r["band"], x=r[a] - r[b]) for r in rows
                  if r.get(a) is not None and r.get(b) is not None]
            summ[f"{a}_minus_{b}"] = K.band_stat(pr, "x")
        out[bs] = {"summary": summ, "rows": rows}
        print(bs, json.dumps({k: (v["band_median_log_ratio"], v["parts_better"], v["parts"],
                                  v["sign_flip_p_two_sided"]) if v else None for k, v in summ.items()}))
    (OUT / "result.json").write_text(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("render", "score"))
    ap.add_argument("--kinds", nargs="*", default=["measure", "flatref", "flatstem"])
    ap.add_argument("--models", default="~/ndsp-presets/learn/direc/models-final")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "render":
        render(args.kinds, args.models)
    else:
        score()


if __name__ == "__main__":
    main()
