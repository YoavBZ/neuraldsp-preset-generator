"""Phase 2 on set 3's development parts (`docs/di-recovery-plan.md`, "Phase 2 on set 3").

Three menus, one per Morgan amp: its factory presets plus its template, all with R.
Every DI is built with K3 fold 2's frozen average balance, which leaves out the only band
set 3 shares with set 2:
- **measure:** the true DI re-equalised to that average, at its own level. Scoring is on
  half B at the part's judge lag; the oracle uses half A.
- **flatref / flatstem:** the amp track / separated stem re-equalised, at −22.9 LUFS.
- **net / netstem:** the set-3 network on the amp track / stem, at −22.9 LUFS.

Choosing through a rebuilt DI uses half A against the recording it came from, with lag
−52. Renders are cached per (kind, part, amp).

    $TORCH_PY -m learn.phase2_set3 render --kinds measure flatref
    $TORCH_PY -m learn.phase2_set3 render --kinds flatstem netstem net --model .../set3.pt
    $TORCH_PY -m learn.phase2_set3 score
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

SR, LATENCY = 48000, 52
CROPS = pathlib.Path(os.path.expanduser("~/ndsp-presets/references/validation-crops-set3"))
STEMS = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/set3/stems"))
CACHE = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/direc/cache"))
OUT = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/direc/phase2-set3"))
AVG_FOLD = 2
AMPS = ("pr12", "sw50r", "ac20")
HALF_A, HALF_B = (1.0, 5.5), (5.5, 10.0)
BAND_SETS = ("recording", "union")
REBUILT = {"flatref": "ref", "flatstem": "stem", "net": "ref", "netstem": "stem"}


def mono(path):
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    assert sr == SR, path
    return x.mean(axis=1)


def dev_parts():
    from learn import set3

    return {p["slug"]: p for p in set3.parts("development")}


def stem_usable():
    path = STEMS / "manifest.json"
    if not path.exists():
        return set()
    m = json.loads(path.read_text())
    return {p for p, v in m["parts"].items() if v.get("usable")}


def recording(slug, source):
    if source == "stem":
        return mono(STEMS / "htdemucs_6s" / slug / "instrumental_guitar.wav")
    return mono(CROPS / slug / "reference.wav")


def build_di(kind, slug, net=None):
    import numpy as np

    from learn import direc as D
    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs

    avg = D.fold_average(CACHE, AVG_FOLD)
    if kind == "measure":
        di = mono(CROPS / slug / "di.wav")
        own = smoothed_spectrum(di)
        y = eq_to(di, avg - (own - own.mean()))
        return y * math.sqrt(np.mean(di ** 2) / np.mean(y ** 2))
    rec = recording(slug, REBUILT[kind])
    if kind.startswith("flat"):
        own = smoothed_spectrum(rec)
        return to_lufs(eq_to(rec, avg - (own - own.mean())))
    import torch

    return to_lufs(D.rebuild(net, rec.astype(np.float32), device=torch.device("cpu")).astype(np.float64))


def menus(pack, renderer):
    import render_preset_panel as RP

    out = {}
    for amp in AMPS:
        m = RP.candidates(argparse.Namespace(amp=amp, factory_dir=RP.FACTORY), pack, renderer)
        out[amp] = {n: RP.preset_edits(path, pack, renderer, amp, rule)
                    for n, (path, rule) in m.items() if n != "template"}
    return out


def render(kinds, model, shard=(0, 1)):
    import numpy as np
    import soundfile as sf
    import torch

    import render_preset_panel as RP
    from learn import direc as D
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    parts = dev_parts()
    usable = stem_usable()
    net = None
    if any(k.startswith("net") for k in kinds):
        net = D.build_model()
        net.load_state_dict(torch.load(pathlib.Path(model).expanduser(), map_location="cpu"))
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

    r = PanelRenderer("morgan", process_policy="reuse")
    M = menus(pack, r)
    PanelRenderer.commands = {f"{amp}|{n}": v for amp, m in M.items() for n, v in m.items()}
    try:
        for slug in sorted(parts)[shard[0]::shard[1]]:
            for kind in kinds:
                if REBUILT.get(kind) == "stem" and slug not in usable:
                    continue
                base = OUT / kind / slug
                if (base / "done").exists():
                    continue
                base.mkdir(parents=True, exist_ok=True)
                di = build_di(kind, slug, net)
                np.save(base / "di.npy", di)
                d32 = di.astype(np.float32)
                for amp, m in M.items():
                    (base / amp).mkdir(exist_ok=True)
                    r.render(d32, {"panel": f"{amp}|template+R"})            # warm-up per amp
                    for n in m:
                        sf.write(base / amp / f"{RP._slug(n)}.wav",
                                 np.asarray(r.render(d32, {"panel": f"{amp}|{n}"}).audio), SR,
                                 subtype="FLOAT")
                (base / "done").write_text("")
                print(slug, kind, flush=True)
    finally:
        r.close()


def _score_part(job):
    import numpy as np

    import render_preset_panel as RP
    from analysis.aligned import aligned_distance

    slug, lag, names = job
    ref = recording(slug, "ref")
    res = {}
    mdir = OUT / "measure" / slug
    mdi = np.load(mdir / "di.npy")
    for bs in BAND_SETS:
        for amp, ns in names.items():
            dB = {n: aligned_distance(ref, mono(mdir / amp / f"{RP._slug(n)}.wav"), mdi, lag=lag,
                                      render_latency=LATENCY, start_s=HALF_B[0], end_s=HALF_B[1],
                                      bands=bs).distance for n in ns}
            dA = {n: aligned_distance(ref, mono(mdir / amp / f"{RP._slug(n)}.wav"), mdi, lag=lag,
                                      render_latency=LATENCY, start_s=HALF_A[0], end_s=HALF_A[1],
                                      bands=bs).distance for n in ns}
            res[f"{bs}|{amp}|measure_B"] = dB
            res[f"{bs}|{amp}|measure_A"] = dA
            for kind, src in REBUILT.items():
                d = OUT / kind / slug
                if not (d / "done").exists():
                    continue
                di = np.load(d / "di.npy")
                rec = recording(slug, src)
                res[f"{bs}|{amp}|{kind}_A"] = {
                    n: aligned_distance(rec, mono(d / amp / f"{RP._slug(n)}.wav"), di, lag=-LATENCY,
                                        render_latency=LATENCY, start_s=HALF_A[0], end_s=HALF_A[1],
                                        bands=bs).distance for n in ns}
    print(slug, flush=True)
    return slug, res


def score():
    from concurrent.futures import ProcessPoolExecutor

    import kill_tests as K
    from match.renderer_au import AudioUnitRenderer  # noqa: F401  (menus need a renderer object)
    from packs.loader import load_pack

    parts = dev_parts()
    pack = load_pack("morgan")

    class Dummy:
        def _stored(self, pack, spec, value):
            return pack.to_stored(spec, value, warnings=[])

    import render_preset_panel as RP
    names = {amp: [n for n in RP.candidates(argparse.Namespace(amp=amp, factory_dir=RP.FACTORY),
                                            pack, Dummy()) if n != "template"] for amp in AMPS}
    jobs = [(s, parts[s]["judge_lag_samples"], names) for s in sorted(parts)
            if (OUT / "measure" / s / "done").exists()]
    with ProcessPoolExecutor(6) as ex:
        D = dict(ex.map(_score_part, jobs))
    (OUT / "distances.json").write_text(json.dumps(D))
    summary_all = {}
    for bs in BAND_SETS:
        for amp in list(AMPS) + ["best-of-3"]:
            rows = []
            for slug, res in D.items():
                p = parts[slug]
                # weights: each band's parts count 1/n (validation-set3.md); band_stat takes band medians
                row = {"part": slug, "band": p["band"], "gain": p["gain_class"]}

                def pick(key, amps):
                    best = None
                    for a in amps:
                        dd = {n: v for n, v in res.get(f"{bs}|{a}|{key}", {}).items() if v}
                        for n, v in dd.items():
                            if best is None or v < best[2]:
                                best = (a, n, v)
                    return best

                amps = AMPS if amp == "best-of-3" else (amp,)
                # template+R of the amp (for best-of-3: PR12's template, the product's default)
                tamp = "pr12" if amp == "best-of-3" else amp
                tB = res[f"{bs}|{tamp}|measure_B"].get("template+R")
                if not tB:
                    continue
                lt = math.log(tB)

                def scored(b):
                    if b is None:
                        return None
                    v = res[f"{bs}|{b[0]}|measure_B"].get(b[1])
                    return math.log(v) - lt if v else None

                row["oracle"] = scored(pick("measure_A", amps))
                allB = [math.log(v) - lt for a in amps for v in res[f"{bs}|{a}|measure_B"].values() if v]
                row["best_B"] = min(allB) if allB else None
                for kind in REBUILT:
                    row[kind] = scored(pick(f"{kind}_A", amps))
                rows.append(row)
            summ = {k: K.band_stat(rows, k) for k in ["oracle", "best_B"] + list(REBUILT)}
            for a, b in (("net", "flatref"), ("netstem", "flatstem")):
                pr = [dict(band=r["band"], x=r[a] - r[b]) for r in rows
                      if r.get(a) is not None and r.get(b) is not None]
                summ[f"{a}_minus_{b}"] = K.band_stat(pr, "x")
            summary_all[f"{bs}|{amp}"] = {"summary": summ, "rows": rows}
            print(bs, amp, json.dumps({k: (v["band_median_log_ratio"], v["parts_better"], v["parts"],
                                           v["sign_flip_p_two_sided"]) if v else None
                                       for k, v in summ.items()}), flush=True)
    (OUT / "result.json").write_text(json.dumps(summary_all, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("render", "score"))
    ap.add_argument("--kinds", nargs="*", default=["measure", "flatref"])
    ap.add_argument("--model", default="~/ndsp-presets/learn/direc/models-set3/fold2.pt")
    ap.add_argument("--shard", default="0/1", help="i/n: render every n-th part from the i-th")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "render":
        i, n = (int(v) for v in args.shard.split("/"))
        render(args.kinds, args.model, (i, n))
    else:
        score()


if __name__ == "__main__":
    main()
