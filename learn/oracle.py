"""How much is a perfectly known transfer curve worth? (An oracle; it reads the DI.)

For each of K1's 25 parts, the real transfer curve is measured on half A (1.0–5.5 s) of
the amp track against the part's own DI. Settings are then chosen to reproduce it in
two ways:
- `forward`: through the learned stand-in (`learn/forward.py`);
- `library`: the rendered POC setting whose measured curve is nearest.

Each choice is rendered through the part's DI and judged on half B (5.5–10 s), against
template+R, exactly as K1 scored its split-half oracle over the clean factory menu. If
even a perfectly known curve does not get closer than the menu's oracle, learning to
estimate the curve from a song cannot either.

    .venv/bin/python -m learn.oracle --forward ~/ndsp-presets/learn/poc/forward-all.pt \\
        --out ~/ndsp-presets/learn/poc/oracle
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

from learn import pr12  # noqa: E402

KILL = pathlib.Path(os.path.expanduser("~/ndsp-presets/runs/kill"))
CROPS = pathlib.Path(os.path.expanduser("~/ndsp-presets/references/validation-crops"))
POC = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/poc"))
SR, LATENCY = 48000, 52
BAND_SETS = ("recording", "union")


def mono(path):
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    assert sr == SR
    return x.mean(axis=1)


class PartRenderer:
    """Renders a PR12 sample through a part's DI crop in one reused plugin process."""

    def __init__(self):
        from match.renderer_au import AudioUnitRenderer
        from packs.loader import load_pack

        pack = load_pack("morgan")
        writable = {k for k, spec in pack.parameters.items()
                    if spec.writable and spec.kind not in ("path", "string", "internal")}
        self.template = {k: v for k, v in pr12.template_state().items() if k in writable}

        class R(AudioUnitRenderer):
            command = None

            def _state_command(self, settings):
                return self.command

        self.r = R("morgan", process_policy="reuse")
        self.warm = False

    def render(self, part, sample, input_gain, path):
        import numpy as np
        import soundfile as sf

        if path.exists():
            return mono(path)
        di = mono(CROPS / part / "di.wav").astype(np.float32)
        if not self.warm:
            self.r.command = pr12.render_command(pr12.from_state(self.template, self.template),
                                                 self.template, 0.0)
            self.r.render(di, {})
            self.warm = True
        self.r.command = pr12.render_command(sample, self.template, input_gain)
        y = np.asarray(self.r.render(di, {}).audio, dtype=np.float64)
        y = y.mean(axis=1) if y.ndim == 2 else y
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(path, y, SR, subtype="FLOAT")
        return y

    def close(self):
        self.r.close()


def main():
    import numpy as np
    import torch

    from analysis.aligned import aligned_distance
    from learn import forward as FW
    from learn.transfer import long_term

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forward", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    args = ap.parse_args()
    out = args.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)

    j = json.loads((KILL / "k-judge-pr12-clean.json").read_text())
    k1 = {bs: {r["part"]: r for r in j["k1"][bs]["rows"]} for bs in BAND_SETS}
    parts = sorted(k1["recording"])
    lags = {p: j["lags"][p]["lag"] for p in parts}
    panel = json.loads((KILL / "pr12-clean" / "index.json").read_text())
    files = {(r["part"], r["candidate"]): r["file"] for r in panel["rows"] if "file" in r}

    net = FW.load(args.forward.expanduser())
    X, Tlib, _ = FW.load_xy(POC / "cache", POC / "renders")
    meta = json.loads((POC / "cache" / "meta.json").read_text())
    rows = {}
    for f in (POC / "renders").glob("index-w*.jsonl"):
        for line in f.read_text().splitlines():
            if line:
                r = json.loads(line)
                rows[r["id"]] = r
    tmpl = pr12.template_state()
    starts = [pr12.from_state(s, tmpl) for s in pr12.factory_presets().values()]
    rng = __import__("random").Random(0)
    starts += [pr12.sample_random(rng) for _ in range(60)]

    renderer = PartRenderer()
    results = {}
    try:
        for p in parts:
            ref, di = mono(CROPS / p / "reference.wav"), mono(CROPS / p / "di.wav")
            a, b = int(1.0 * SR), int(5.5 * SR)
            dA, act = long_term(di[a:b])
            rA, _ = long_term(ref[a:b], act)
            target = rA - dA
            target = target - target.mean()
            weights = (rA >= rA.max() - 30).astype(float)
            target = target - (target * weights).sum() / weights.sum()
            s_f, drive_f, err_f = FW.fit_settings(net, target, weights, starts=starts)
            libT = Tlib - (Tlib * weights).sum(1, keepdims=True) / weights.sum()
            lib_err = (np.abs(libT - target) * weights).sum(1) / weights.sum()
            best = int(lib_err.argmin())
            lib_row = rows[meta[best]["id"]]
            s_l, drive_l = lib_row["sample"], meta[best]["effective_drive"]
            x_f = renderer.render(p, s_f, drive_f, out / "renders" / f"{p}--forward.wav")
            x_l = renderer.render(p, s_l, drive_l, out / "renders" / f"{p}--library.wav")
            x_t = mono(files[(p, "template+R")])
            row = {"part": p, "band": k1["recording"][p]["band"], "fit_err": err_f,
                   "lib_err": float(lib_err[best]), "drive_forward": drive_f, "drive_library": drive_l}
            for bs in BAND_SETS:
                d = {name: aligned_distance(ref, x, di, lag=lags[p], render_latency=LATENCY,
                                            start_s=5.5, end_s=10.0, bands=bs).distance
                     for name, x in (("template", x_t), ("forward", x_f), ("library", x_l))}
                if None in d.values():
                    row[bs] = None
                    continue
                lt = math.log(d["template"])
                row[bs] = {"forward": math.log(d["forward"]) - lt,
                           "library": math.log(d["library"]) - lt,
                           "k1_oracle": k1[bs][p]["oracle"], "k1_template_check": None}
            results[p] = row
            print(p, {bs: ({k: round(v, 3) for k, v in row[bs].items() if isinstance(v, float)}
                           if row[bs] else None) for bs in BAND_SETS}, flush=True)
    finally:
        renderer.close()

    sys.path.insert(0, str(PLUGIN_ROOT / "research"))
    import kill_tests as K

    summary = {}
    for bs in BAND_SETS:
        rs = [dict(r[bs], band=r["band"]) for r in results.values() if r.get(bs)]
        summary[bs] = {k: K.band_stat(rs, k) for k in ("forward", "library", "k1_oracle")}
    (out / "oracle.json").write_text(json.dumps({"rows": results, "summary": summary}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
