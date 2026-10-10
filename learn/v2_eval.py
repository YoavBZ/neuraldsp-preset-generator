"""Test a retrained DI network on set 3's development parts (`docs/di-network-v2-plan.md`).

Rebuilds each part's DI from its amp track with the given network (CPU), renders every
menu preset through it, picks on half A with the reference-proxy fallback, and scores
the pick with the stored average-guitar measure (`phase2-set3/measure`, half B).

    $TORCH_PY -m learn.v2_eval render --model .../models-v2b/fold2.pt --name v2b --shard 0/3
    $TORCH_PY -m learn.v2_eval score --name v2b
    $TORCH_PY -m learn.v2_eval summary --name v2b [--folds 2]
    $TORCH_PY -m learn.v2_eval render --name lp3k --lowpass 3000 --shard 0/3   # no network
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import phase2_set3 as P  # noqa: E402
from learn import set3_gap_split as G  # noqa: E402

SRC = P.OUT
ROOT = SRC.with_name("v2-eval")
CONSTANT = {"pr12": "factory:Neural DSP/Vintage Metal",
            "sw50r": "factory:Artists/Royce Whittaker/Wall Of Doom",
            "ac20": "factory:Artists/Charlie Robbins/Dirty Coil Rhythm"}


def parts(folds=None):
    from learn import set3

    ps = G.parts()
    return {s: p for s, p in ps.items() if folds is None or set3.fold_for_band(p["band"]) in folds}


def lowpassed(slug, hz):
    """The stored rebuilt DI (`phase2-set3/net`), low-passed at `hz`, back at −22.9 LUFS."""
    import numpy as np

    from learn.direc_check import to_lufs

    x = np.load(SRC / "net" / slug / "di.npy")
    f = np.fft.rfftfreq(len(x), 1 / P.SR)
    gain = 1 / np.sqrt(1 + (f / hz) ** 8)                       # 4th-order Butterworth magnitude
    return to_lufs(np.fft.irfft(np.fft.rfft(x) * gain, len(x)))


def render(model, name, shard, folds, lowpass=None):
    import numpy as np
    import soundfile as sf
    import torch

    import render_preset_panel as RP
    from learn import direc as D
    from learn.direc_check import to_lufs
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    if lowpass is None:
        net = D.load_model(model)
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
    M = P.menus(pack, r)
    PanelRenderer.commands = {f"{amp}|{n}": v for amp, m in M.items() for n, v in m.items()}
    out = ROOT / name
    try:
        for slug in sorted(parts(folds))[shard[0]::shard[1]]:
            base = out / slug
            if (base / "done").exists():
                continue
            base.mkdir(parents=True, exist_ok=True)
            if lowpass is not None:
                di = lowpassed(slug, lowpass)
            else:
                rec = P.recording(slug, "ref", P.RunConfig())
                di = to_lufs(D.rebuild(net, rec.astype(np.float32),
                                       device=torch.device("cpu")).astype(np.float64))
            np.save(base / "di.npy", di)
            d32 = di.astype(np.float32)
            for amp, m in M.items():
                (base / amp).mkdir(exist_ok=True)
                r.render(d32, {"panel": f"{amp}|template+R"})                # warm-up per amp
                for n in m:
                    y = np.asarray(r.render(d32, {"panel": f"{amp}|{n}"}).audio, np.float64)
                    sf.write(base / amp / f"{RP._slug(n)}.flac",
                             y * (0.99 / max(np.abs(y).max(), 1e-12)), P.SR, subtype="PCM_24")
            (base / "done").write_text(f"lowpass {lowpass}" if lowpass is not None else str(model))
            print(slug, flush=True)
    finally:
        r.close()


def _score_part(job):
    import numpy as np

    import render_preset_panel as RP
    from learn.rebuilt_judge import rebuilt_distance

    slug, names, dirs = job
    ref = P.recording(slug, "ref", P.RunConfig())
    res = {}
    for kind, d in dirs.items():
        d = d / slug
        di = np.load(d / "di.npy")
        for bs in P.BAND_SETS:
            for amp, ns in names.items():
                row, proxy = {}, False
                for n in ns:
                    x, used = rebuilt_distance(ref, P.mono(d / amp / f"{RP._slug(n)}.wav"), di,
                                               start_s=P.HALF_A[0], end_s=P.HALF_A[1], bands=bs)
                    row[n] = x.distance
                    proxy |= used
                res[f"{bs}|{amp}|{kind}_A"] = row
                res[f"{bs}|{amp}|{kind}_proxy"] = proxy
    print(slug, flush=True)
    return slug, res


def score(name, workers, folds):
    from concurrent.futures import ProcessPoolExecutor

    ps, names = parts(folds), G.menu_names()
    # The current network is re-scored the same way, so both use the fallback.
    dirs = {name: ROOT / name, "net": SRC / "net"}
    for s in ps:
        if not (ROOT / name / s / "done").exists():
            raise SystemExit(f"missing renders: {name}/{s}")
    with ProcessPoolExecutor(workers) as ex:
        D = dict(ex.map(_score_part, [(s, names, dirs) for s in sorted(ps)]))
    (ROOT / name / "distances.json").write_text(json.dumps(D, indent=1))


def summary(name, folds, against=None):
    base = json.loads((SRC / "distances.json").read_text())
    new = json.loads((ROOT / name / "distances.json").read_text())
    other = json.loads((ROOT / against / "distances.json").read_text()) if against else {}
    ps = parts(folds)
    out = {}
    for bs in P.BAND_SETS:
        pooled = {}
        for amp in P.AMPS:
            per = {}
            for slug, p in sorted(ps.items()):
                B = base[slug][f"{bs}|{amp}|measure_B"]
                rows = {"oracle": base[slug][f"{bs}|{amp}|measure_A"],
                        "net": new[slug][f"{bs}|{amp}|net_A"],
                        name: new[slug][f"{bs}|{amp}|{name}_A"]}
                if against:
                    rows[against] = other[slug][f"{bs}|{amp}|{against}_A"]
                lB = {}
                for kind, A in rows.items():
                    A = {n: v for n, v in A.items() if v}
                    pick = min(A, key=lambda n: (A[n], n)) if A else None
                    lB[kind] = math.log(B[pick]) if pick and B.get(pick) else None
                lB["constant"] = math.log(B[CONSTANT[amp]])
                lB["template"] = math.log(B["template+R"])
                for a, b in ((name, "net"), (name, "constant"), ("net", "constant"),
                             (name, "template"), ("oracle", name)) + (((name, against),) if against else ()):
                    if lB[a] is not None and lB[b] is not None:
                        per.setdefault(f"{a}_vs_{b}", []).append((p["band"], lB[a] - lB[b]))
            out[f"{bs}|{amp}"] = {k: G.describe(v) for k, v in per.items()}
            for k, v in per.items():
                pooled.setdefault(k, []).extend((f"{amp}|{b}", x) for b, x in v)
        out[f"{bs}|pooled"] = {k: G.describe(v) for k, v in pooled.items()}
    path = ROOT / name / ("summary.json" if not against else f"summary-vs-{against}.json")
    path.write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        print(k)
        for n, d in v.items():
            print(f"  {n:22s} mean {d['mean']:+.4f} W/T/L {d['wins']}/{d['ties']}/{d['losses']} "
                  f"bm {d['band_median']:+.4f} p {d['sign_flip_p']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("render", "score", "summary"))
    ap.add_argument("--name", required=True)
    ap.add_argument("--model", type=pathlib.Path)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--folds", type=int, nargs="*", help="set-3 folds to test (default: all)")
    ap.add_argument("--against", help="another tested network, on the same parts")
    ap.add_argument("--lowpass", type=float, help="render the stored rebuilt DI low-passed here (Hz)")
    args = ap.parse_args(argv)
    folds = set(args.folds) if args.folds else None
    if args.cmd == "render":
        render(args.model.expanduser() if args.model else None, args.name,
               tuple(int(v) for v in args.shard.split("/")), folds, args.lowpass)
    elif args.cmd == "score":
        score(args.name, args.workers, folds)
    else:
        summary(args.name, folds, args.against)


if __name__ == "__main__":
    main()
