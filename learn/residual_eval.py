"""The residual DI network's test (`docs/residual-di-plan.md`): R against C (and L) as
rebuilt-DI choosers on the 18 pinned development parts no fold-2 network trained on.

    $TORCH_PY -m learn.residual_eval coherence MODEL [MODEL ...]   # pre-check, real recordings
    $TORCH_PY -m learn.residual_eval render 0 6                    # shard 0 of 6
    $TORCH_PY -m learn.residual_eval score
    $TORCH_PY -m learn.residual_eval report
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

from learn import confirm_run as CR  # noqa: E402
from learn import phase2_set3 as P  # noqa: E402
from learn import set3_gap_split as G  # noqa: E402
from learn import songs_check as SC  # noqa: E402
from learn import sound_desc_eval as E  # noqa: E402

D3 = CR.HOME / "learn/direc"
OUT = D3 / "residual"
PINNED = PLUGIN_ROOT / "docs/sound-desc-test-parts.json"
NETS = {"R": D3 / "models-resid/fold2.pt", "C": D3 / "models-set3/fold2.pt", "L": D3 / "models-linear/fold2.pt"}
BANDS_HZ = ((80, 1000), (1000, 3000), (3000, 8000))


def parts():
    """The pinned clean and crunch parts whose bands no fold-2 network trained on (set 3's,
    K3 fold −1, and fold 2's), with their crops and Morgan-convention judge lags."""
    from learn import train as TR

    fold_of, _ = TR.k3_folds()
    pin = json.loads(PINNED.read_text())["parts"]
    s3, s12 = G.parts(), SC.parts()
    out = {}
    for slug, meta in pin.items():
        if fold_of.get(meta["band"], -1) not in (-1, 2):
            continue
        if slug in s3:
            out[slug] = dict(crop=P.CROPS / slug, judge_lag=s3[slug]["judge_lag_samples"], **meta)
        else:
            out[slug] = dict(crop=s12[slug]["crop"], judge_lag=s12[slug]["judge_lag"], **meta)
    assert len(out) == 18 and len({p["band"] for p in out.values()}) == 8, len(out)
    return out


def rebuild(kind, part, net):
    import numpy as np
    import torch

    from learn import direc as D
    from learn.direc_check import to_lufs

    rec = CR.mono(pathlib.Path(part["crop"]) / "reference.wav")
    return to_lufs(D.rebuild(net, rec.astype(np.float32), device=torch.device("cpu")).astype(np.float64))


def _coherence(a, b):
    import numpy as np
    from scipy.signal import coherence

    f, c = coherence(a, b, fs=P.SR, nperseg=4096)
    return [float(np.mean(c[(f >= lo) & (f < hi)])) for lo, hi in BANDS_HZ]


def _aligned(x, di, hint):
    """x and the true DI cut to a common timeline. The lag (samples x lags di) is searched
    within ±50 ms of `hint`: the part's measured lag plus the plugin latency for a recording,
    0 for a rebuilt DI (the networks learned to advance by the latency)."""
    from analysis.aligned import estimate_lag

    k = estimate_lag(x, [di], hint=hint)                 # samples x lags di
    n = min(len(x), len(di))
    if k >= 0:
        return x[k:n], di[:n - k], k
    return x[:n + k], di[-k:n], k


def coherence(models):
    """Median coherence with the true DI over the 18 parts, per band: the recording itself
    and each network's rebuild (aligned by cross-correlation)."""
    import numpy as np

    from learn import direc as D

    ps = parts()
    nets = {str(m): D.load_model(m).eval() for m in models}
    rows = {"recording": []} | {k: [] for k in nets}
    lags = {k: [] for k in rows}
    for s in sorted(ps):
        di = CR.mono(pathlib.Path(ps[s]["crop"]) / "di.wav")
        rec = CR.mono(pathlib.Path(ps[s]["crop"]) / "reference.wav")
        a, b, k_ = _aligned(rec, di, ps[s]["judge_lag"] + P.LATENCY)
        rows["recording"].append((ps[s]["band"], _coherence(a, b)))
        # Misalignment the judge would see, in samples (0 is right). The judge reads the
        # recording at t against a rebuilt DI at t (lag −52, latency 52), so a rebuild should
        # lag the true DI by as much as the recording does: judge_lag + 52. The recording's
        # own row is a check of the stored lag.
        lags["recording"].append(k_ - (ps[s]["judge_lag"] + P.LATENCY))
        for k, net in nets.items():
            a, b, k_ = _aligned(rebuild(k, ps[s], net), di, ps[s]["judge_lag"] + P.LATENCY)
            rows[k].append((ps[s]["band"], _coherence(a, b)))
            lags[k].append(k_ - (ps[s]["judge_lag"] + P.LATENCY))

    def band_median(v, i):
        by = {}
        for band, c in v:
            by.setdefault(band, []).append(c[i])
        return float(np.median([np.mean(x) for x in by.values()]))

    out = {k: {"median": [round(float(np.median([c[i] for _, c in v])), 3) for i in range(3)],
               "band_median": [round(band_median(v, i), 3) for i in range(3)],
               "misalignment_median": float(np.median(lags[k]))} for k, v in rows.items()}
    for k, v in out.items():
        m, bm = v["median"], v["band_median"]
        print(f"{k[-50:]:50s} 80-1k {m[0]:.3f}  1-3k {m[1]:.3f}  3-8k {m[2]:.3f} | band-wtd 1-3k {bm[1]:.3f} "
              f"| misaligned {v['misalignment_median']:+.0f}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "coherence.json").write_text(json.dumps(out, indent=1))
    return out


def render(shard):
    import numpy as np
    import soundfile as sf

    import render_preset_panel as RP
    from learn import direc as D
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    pack = load_pack("morgan")

    class PanelRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["panel"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    nets = {k: D.load_model(v).eval() for k, v in NETS.items()}
    r = PanelRenderer("morgan", process_policy="reuse")
    M = P.menus(pack, r)
    PanelRenderer.commands = {f"{amp}|{n}": v for amp, m in M.items() for n, v in m.items()}
    ps = parts()
    try:
        for slug in sorted(ps)[shard[0]::shard[1]]:
            for kind, net in nets.items():
                base = OUT / kind / slug
                if (base / "done").exists():
                    continue
                base.mkdir(parents=True, exist_ok=True)
                di = rebuild(kind, ps[slug], net)
                np.save(base / "di.npy", di)
                d32 = di.astype(np.float32)
                for amp, m in M.items():
                    (base / amp).mkdir(exist_ok=True)
                    r.render(d32, {"panel": f"{amp}|template+R"})            # warm-up per amp
                    for n in m:
                        y = np.asarray(r.render(d32, {"panel": f"{amp}|{n}"}).audio, np.float64)
                        sf.write(base / amp / f"{RP._slug(n)}.flac",
                                 y * (0.99 / max(np.abs(y).max(), 1e-12)), P.SR, subtype="PCM_24")
                (base / "done").write_text("")
                print(slug, kind, flush=True)
    finally:
        r.close()


def _score_part(job):
    import numpy as np

    import render_preset_panel as RP
    from learn.rebuilt_judge import rebuilt_distance

    slug, part, names = job
    ref = CR.mono(pathlib.Path(part["crop"]) / "reference.wav")
    res = {}
    for kind in NETS:
        d = OUT / kind / slug
        di = np.load(d / "di.npy")
        for amp, ns in names.items():
            for n in ns:
                y = P.mono(d / amp / f"{RP._slug(n)}.flac")
                for h, (a, b) in (("A", P.HALF_A), ("B", P.HALF_B)):
                    x, proxy = rebuilt_distance(ref, y, di, start_s=a, end_s=b)
                    res.setdefault(f"{kind}|{amp}|{h}", {})[n] = (x.distance, proxy)
    print(slug, flush=True)
    return slug, res


def score(workers=7):
    from concurrent.futures import ProcessPoolExecutor

    ps, names = parts(), G.menu_names()
    for s in ps:
        for k in NETS:
            if not (OUT / k / s / "done").exists():
                raise SystemExit(f"missing renders: {k}/{s}")
    jobs = [(s, {**ps[s], "crop": str(ps[s]["crop"])}, names) for s in sorted(ps)]
    with ProcessPoolExecutor(workers) as ex:
        R = dict(ex.map(_score_part, jobs))
    (OUT / "distances.json").write_text(json.dumps(R))


def _sign_flip(by_band):
    """Exact two-sided band sign-flip p for the mean of band means."""
    import itertools

    m = [statistics.fmean(v) for v in by_band.values()]
    obs = abs(statistics.fmean(m))
    flips = list(itertools.product((1, -1), repeat=len(m)))
    return sum(abs(statistics.fmean([s * x for s, x in zip(f, m)])) >= obs - 1e-12 for f in flips) / len(flips)


def report():
    ps = parts()
    tp = {s: v for s, v in E.test_parts().items() if s in json.loads(PINNED.read_text())["parts"]}
    D = {s: tp[s]["D"] for s in tp}
    R = json.loads((OUT / "distances.json").read_text())

    def mean_halves(s, amp, n):
        a, b = D[s][f"flat|{amp}|measfix_A"][n][0], D[s][f"flat|{amp}|measfix_B"][n][0]
        return (a + b) / 2 if a and b else None

    def lbo_baseline(slug, amp):          # as in sound_desc_eval: other bands, same class, all 35 pinned parts
        cls, band = tp[slug]["gain_class"], tp[slug]["band"]
        others = [s for s in tp if tp[s]["gain_class"] == cls and tp[s]["band"] != band]
        meds = {}
        for n in [n for n in D[slug][f"flat|{amp}|measfix_A"] if n.startswith("factory:")]:
            v = [mean_halves(s, amp, n) for s in others]
            if v and all(x is not None for x in v):
                meds[n] = statistics.median(v)
        return min(meds, key=lambda n: (meds[n], n))

    def pick(row):
        row = {n: v[0] for n, v in row.items() if v[0]}
        return min(row, key=lambda n: (row[n], n)) if row else None

    cells = {}
    proxies = 0
    for s in ps:
        for amp in P.AMPS:
            b = lbo_baseline(s, amp)
            per = {}
            for h, other in (("A", "B"), ("B", "A")):
                M = D[s][f"flat|{amp}|measfix_{other}"]
                picks = {k: pick(R[s][f"{k}|{amp}|{h}"]) for k in NETS}
                proxies += sum(v[1] for k in NETS for v in R[s][f"{k}|{amp}|{h}"].values())
                picks["oracle"] = pick({n: v for n, v in D[s][f"flat|{amp}|measfix_{h}"].items()})
                picks["base"] = b
                for k, n in picks.items():
                    per.setdefault(k, []).append(M[n][0] if n and M.get(n) and M[n][0] else None)
            cells[(s, amp)] = per

    def compare(a, b, cls=None):
        rows = []
        for (s, amp), per in cells.items():
            if cls and ps[s]["gain_class"] != cls:
                continue
            v = [math.log(x / y) for x, y in zip(per[a], per[b]) if x and y]
            if len(v) == 2:
                rows.append((ps[s]["band"], statistics.fmean(v)))
        st = CR.stats(rows)
        by = {}
        for bd, x in rows:
            by.setdefault(bd, []).append(x)
        st["sign_flip_p"] = round(_sign_flip(by), 4)
        st["per_band"] = {bd: round(statistics.fmean(v), 4) for bd, v in sorted(by.items())}
        return st

    res = {}
    for cls in (None, "clean", "crunch"):
        tag = cls or "all"
        for a, b in (("R", "C"), ("L", "C"), ("R", "L"), ("R", "base"), ("C", "base"), ("L", "base"),
                     ("oracle", "base")):
            res[f"{a}_vs_{b}|{tag}"] = compare(a, b, cls)
    # The gate (after review): a t-interval on the 8 band means (7 df), and most bands negative.
    g = res["R_vs_C|all"]
    bm = list(g["per_band"].values())
    mu = statistics.fmean(bm)
    se = statistics.stdev(bm) / math.sqrt(len(bm))
    t = 1.895                                    # t(0.95, 7)
    gate = {"band_mean": round(mu, 4), "lo90": round(mu - t * se, 4), "hi90": round(mu + t * se, 4),
            "bands_negative": sum(x < 0 for x in bm), "bands": len(bm),
            "smallest_detectable": round(-t * se, 4)}
    outcome = ("helps" if gate["hi90"] < 0 and gate["bands_negative"] > len(bm) / 2 else
               "futile" if gate["lo90"] > -0.02 else "inconclusive")
    g = gate
    coh = json.loads((OUT / "coherence.json").read_text()) if (OUT / "coherence.json").exists() else None
    out = {"gate": {"result": g, "outcome": outcome}, "proxy_uses": proxies, "coherence": coh, "results": res}
    (OUT / "result.json").write_text(json.dumps(out, indent=1, default=float))
    print("GATE (R vs C, band means):", outcome, g)
    for k, s_ in res.items():
        print(f"  {k:22s} mean {s_['mean']:+.3f} [{s_['lo90']:+.3f}, {s_['hi90']:+.3f}] band-wtd "
              f"{s_['band_weighted_mean']:+.3f} W/T/L {s_['wins']}/{s_['ties']}/{s_['losses']} "
              f"bands {s_['bands']} p {s_['sign_flip_p']}")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "coherence":
        coherence([pathlib.Path(m).expanduser() for m in sys.argv[2:]])
    elif cmd == "render":
        render((int(sys.argv[2]), int(sys.argv[3])))
    else:
        {"score": score, "report": report}[cmd]()
