"""Does the DI network rebuild real amps worse than plugin renders? (`docs/sim-real-gap-plan.md`)

    $TORCH_PY -m learn.sim_real_gap run
"""

from __future__ import annotations

import json
import math
import pathlib
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import phase2_set3 as P  # noqa: E402
from learn import set3_gap_split as G  # noqa: E402

SRC = P.OUT
OUT = SRC.with_name("sim-real")
BANDS = ((80, 1000), (1000, 3000), (3000, 8000))


def align(x, ref, span=2000):
    """`x` shifted (zero-padded) to best match `ref` by cross-correlation within ±span."""
    import numpy as np
    from scipy.signal import correlate

    n = min(len(x), len(ref))
    c = correlate(ref[:n], x[:n], mode="full", method="fft")
    mid = n - 1
    k = int(np.argmax(np.abs(c[mid - span: mid + span + 1]))) - span
    return G.shifted(x[:n], k), ref[:n], k


def compare(x, ref):
    import numpy as np
    from scipy.signal import coherence

    from learn.di_robustness import N_FFT, smoothed_spectrum

    x, ref, k = align(x, ref)
    f, c = coherence(x, ref, fs=P.SR, nperseg=2048)
    coh = [float(np.mean(c[(f >= a) & (f < b)])) for a, b in BANDS]
    fs = np.fft.rfftfreq(N_FFT, 1 / P.SR)
    sx, sr = smoothed_spectrum(x), smoothed_spectrum(ref)
    m = (fs >= 80) & (fs <= 8000)
    d = (sx - sx[m].mean()) - (sr - sr[m].mean())
    return {"coherence": coh, "lsd": float(np.sqrt(np.mean(d[m] ** 2))), "lag": k}


def run():
    import numpy as np
    import torch

    import render_preset_panel as RP
    from learn import direc as D

    net = D.load_model(P.MODEL).eval()
    base = json.loads((SRC / "distances.json").read_text())
    ps = G.parts()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for slug in sorted(ps):
        mdi = np.load(SRC / "measure" / slug / "di.npy")
        real = np.load(SRC / "net" / slug / "di.npy")
        real_cmp = compare(real, mdi)
        for amp in P.AMPS:
            A = {n: v for n, v in base[slug][f"recording|{amp}|measure_A"].items() if v}
            pick = min(A, key=lambda n: (A[n], n))
            render = P.mono(SRC / "measure" / slug / amp / f"{RP._slug(pick)}.wav")
            sim = D.rebuild(net, render.astype(np.float32), device=torch.device("cpu")).astype(np.float64)
            rows.append({"part": slug, "band": ps[slug]["band"], "amp": amp, "pick": pick,
                         "sim": compare(sim, mdi), "real": real_cmp})
        print(slug, flush=True)
    (OUT / "rows.json").write_text(json.dumps(rows, indent=1))
    summarise(rows)


def summarise(rows):
    out = {}
    for amp in P.AMPS + ("pooled",):
        rs = [r for r in rows if amp == "pooled" or r["amp"] == amp]
        res = {}
        for i, (a, b) in enumerate(BANDS):
            s = [r["sim"]["coherence"][i] for r in rs]
            q = [r["real"]["coherence"][i] for r in rs]
            dif = [x - y for x, y in zip(s, q)]
            res[f"coh {a}-{b}"] = {"sim": round(statistics.median(s), 3), "real": round(statistics.median(q), 3),
                                   "median diff": round(statistics.median(dif), 3),
                                   "sim wins": sum(d > 0 for d in dif), "n": len(dif)}
        s = [r["sim"]["lsd"] for r in rs]
        q = [r["real"]["lsd"] for r in rs]
        dif = [x - y for x, y in zip(s, q)]
        res["lsd dB"] = {"sim": round(statistics.median(s), 2), "real": round(statistics.median(q), 2),
                         "median diff": round(statistics.median(dif), 2),
                         "sim wins": sum(d < 0 for d in dif), "n": len(dif)}
        out[amp] = res
    (OUT / "summary.json").write_text(json.dumps(out, indent=1))
    for amp, res in out.items():
        print(amp)
        for k, v in res.items():
            print(f"  {k:16s} {v}")


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        run()
    else:
        summarise(json.loads((OUT / "rows.json").read_text()))
