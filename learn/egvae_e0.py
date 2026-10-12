"""EG-VAE-lite's E0 (`docs/egvae-lite-plan.md`, "Amendment after review" and "E0's bar"): no
training. The 18 development parts' true measure DIs go through DAC 44 kHz and back; the
round-tripped DIs pick per amp per half exactly as the oracle does with the true DI; the picks
are scored on the other half with the stored true-DI measure, against the leave-band-out fixed
preset of `learn/residual_eval.py`.

    $TORCH_PY -m learn.egvae_e0 prep                # true DI -> 44.1 kHz (resample_poly 147/160)
    $DAC_PY   learn/egvae_e0_dac.py roundtrip ~/ndsp-presets/learn/direc/egvae-e0
    $TORCH_PY -m learn.egvae_e0 post                # back to 48 kHz, align, −22.9 LUFS, coherence, lag
    $DAC_PY   learn/egvae_e0_dac.py mel ~/ndsp-presets/learn/direc/egvae-e0
    $TORCH_PY -m learn.egvae_e0 render 0 3          # shard 0 of 3 (the 111-preset dry menu)
    $TORCH_PY -m learn.egvae_e0 render-true SLUG    # check: the true DI through the same pipeline
    $TORCH_PY -m learn.egvae_e0 score
    $TORCH_PY -m learn.egvae_e0 report              # -> docs/egvae-e0-result.json
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
from learn import residual_eval as RE  # noqa: E402
from learn import set3_gap_split as G  # noqa: E402
from learn import sound_desc_eval as E  # noqa: E402

OUT = CR.HOME / "learn/direc/egvae-e0"
RESULT = PLUGIN_ROOT / "docs/egvae-e0-result.json"
BAR = -0.115


def parts():
    return {s: {**p, "crop": pathlib.Path(p["crop"])} for s, p in RE.parts().items()}


def prep():
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    for s, p in sorted(parts().items()):
        d = OUT / s
        d.mkdir(parents=True, exist_ok=True)
        di = CR.build_di("measfix", p)
        np.save(d / "true.npy", di)
        sf.write(d / "true44.wav", resample_poly(di, 147, 160).astype(np.float32), 44100, subtype="FLOAT")
        print(s, len(di), flush=True)


def post():
    """Back to 48 kHz, cut to the true DI's length, any lag taken out (and reported), −22.9 LUFS.
    Coherence and lag against the true DI as in `residual_eval.coherence` (hint 0)."""
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    from learn.direc_check import to_lufs

    res = {}
    for s, p in sorted(parts().items()):
        d = OUT / s
        true = np.load(d / "true.npy")
        y44, sr = sf.read(d / "dac44.wav", dtype="float64")
        assert sr == 44100
        y = resample_poly(y44, 160, 147)
        y = np.pad(y, (0, max(0, len(true) - len(y))))[: len(true)]
        _, _, k = RE._aligned(y, true, 0)             # samples y lags the true DI
        if k:
            y = np.pad(y[k:], (0, k)) if k > 0 else np.pad(y, (-k, 0))[: len(true)]
        y = to_lufs(y)
        np.save(d / "di.npy", y)
        a, b, k2 = RE._aligned(y, true, 0)
        res[s] = dict(band=p["band"], gain_class=p["gain_class"], lag=int(k), lag_after=int(k2),
                      coherence=RE._coherence(a, b))
        print(s, k, [round(c, 3) for c in res[s]["coherence"]], flush=True)
    (OUT / "post.json").write_text(json.dumps(res, indent=1))


class _Renderer:
    def __init__(self):
        from match.renderer_au import AudioUnitRenderer
        from packs.loader import load_pack

        class PanelRenderer(AudioUnitRenderer):
            commands: dict = {}

            def _state_command(self, settings):
                select, edits = self.commands[settings["panel"]]
                command = {"edits": edits}
                if select is not None:
                    command["selectAmp"] = select
                return command

        self.r = PanelRenderer("morgan", process_policy="reuse")
        self.M = P.menus(load_pack("morgan"), self.r)
        PanelRenderer.commands = {f"{amp}|{n}": v for amp, m in self.M.items() for n, v in m.items()}

    def run(self, di, base):
        """As `residual_eval.render`: warm-up per amp, FLAC 24-bit normalised."""
        import numpy as np
        import soundfile as sf

        import render_preset_panel as RP

        d32 = di.astype(np.float32)
        for amp, m in self.M.items():
            (base / amp).mkdir(parents=True, exist_ok=True)
            self.r.render(d32, {"panel": f"{amp}|template+R"})
            for n in m:
                y = np.asarray(self.r.render(d32, {"panel": f"{amp}|{n}"}).audio, np.float64)
                sf.write(base / amp / f"{RP._slug(n)}.flac",
                         y * (0.99 / max(np.abs(y).max(), 1e-12)), P.SR, subtype="PCM_24")
        (base / "done").write_text("")


def render(shard):
    import numpy as np

    R = _Renderer()
    try:
        for s in sorted(parts())[shard[0]::shard[1]]:
            base = OUT / s
            if not (base / "done").exists():
                R.run(np.load(base / "di.npy"), base)
                print(s, flush=True)
    finally:
        R.r.close()


def render_true(slug):
    import numpy as np

    R = _Renderer()
    try:
        R.run(np.load(OUT / slug / "true.npy"), OUT / "_truecheck" / slug)
    finally:
        R.r.close()


def _score_part(job):
    import numpy as np

    import render_preset_panel as RP
    from analysis.aligned import aligned_distance

    slug, part, names, base, di_name = job
    ref = CR.mono(pathlib.Path(part["crop"]) / "reference.wav")
    di = np.load(OUT / slug / di_name)
    res = {}
    for amp, ns in names.items():
        for n in ns:
            y = P.mono(pathlib.Path(base) / amp / f"{RP._slug(n)}.flac")
            for h, (a, b) in (("A", P.HALF_A), ("B", P.HALF_B)):
                x = aligned_distance(ref, y, di, lag=part["judge_lag"], render_latency=P.LATENCY,
                                     start_s=a, end_s=b)
                res.setdefault(f"e0|{amp}|{h}", {})[n] = (x.distance,)
    print(slug, flush=True)
    return slug, res


def score(workers=6, true_check=False):
    from concurrent.futures import ProcessPoolExecutor

    ps, names = parts(), G.menu_names()
    if true_check:
        slugs = [p.name for p in (OUT / "_truecheck").iterdir() if (p / "done").exists()]
        jobs = [(s, {**ps[s], "crop": str(ps[s]["crop"])}, names, str(OUT / "_truecheck" / s), "true.npy")
                for s in slugs]
    else:
        missing = [s for s in ps if not (OUT / s / "done").exists()]
        if missing:
            raise SystemExit(f"missing renders: {missing}")
        jobs = [(s, {**ps[s], "crop": str(ps[s]["crop"])}, names, str(OUT / s), "di.npy") for s in sorted(ps)]
    with ProcessPoolExecutor(workers) as ex:
        R = dict(ex.map(_score_part, jobs))
    if true_check:
        stored = {s: v["D"] for s, v in E.test_parts().items() if s in R}
        diffs = []
        for s, r in R.items():
            for key, row in r.items():
                _, amp, h = key.split("|")
                for n, (x,) in row.items():
                    y = stored[s][f"flat|{amp}|measfix_{h}"][n][0]
                    if x and y:
                        diffs.append(abs(math.log(x / y)))
                    elif bool(x) != bool(y):
                        diffs.append(float("inf"))
        out = {"parts": sorted(R), "n": len(diffs), "median_abs_log": statistics.median(diffs),
               "max_abs_log": max(diffs)}
        print("true-DI check against the stored measure:", out)
        (OUT / "truecheck.json").write_text(json.dumps(out, indent=1))
        return
    (OUT / "distances.json").write_text(json.dumps(R))


def _band_mean_interval(per_band):
    bm = list(per_band.values())
    mu = statistics.fmean(bm)
    se = statistics.stdev(bm) / math.sqrt(len(bm))
    t = 1.895                                       # t(0.95, 7)
    return {"band_mean": round(mu, 4), "lo90": round(mu - t * se, 4), "hi90": round(mu + t * se, 4),
            "bands_negative": sum(x < 0 for x in bm), "bands": len(bm)}


def report():
    import numpy as np

    ps = parts()
    tp = {s: v for s, v in E.test_parts().items() if s in json.loads(RE.PINNED.read_text())["parts"]}
    D = {s: tp[s]["D"] for s in tp}
    R = json.loads((OUT / "distances.json").read_text())
    Rres = json.loads((RE.OUT / "distances.json").read_text())        # C′ seed 0's stored picks

    def mean_halves(s, amp, n):
        a, b = D[s][f"flat|{amp}|measfix_A"][n][0], D[s][f"flat|{amp}|measfix_B"][n][0]
        return (a + b) / 2 if a and b else None

    def lbo_baseline(slug, amp):          # verbatim from residual_eval.report
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

    cells, agree = {}, []
    for s in ps:
        for amp in P.AMPS:
            per = {}
            for h, other in (("A", "B"), ("B", "A")):
                M = D[s][f"flat|{amp}|measfix_{other}"]
                picks = {"e0": pick(R[s][f"e0|{amp}|{h}"]), "Cp": pick(Rres[s][f"Cp|{amp}|{h}"]),
                         "oracle": pick(D[s][f"flat|{amp}|measfix_{h}"]), "base": lbo_baseline(s, amp)}
                agree.append(picks["e0"] == picks["oracle"])
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
        st["per_band"] = {bd: round(statistics.fmean(v), 4) for bd, v in sorted(by.items())}
        st["band_mean_interval"] = _band_mean_interval(st["per_band"]) if len(by) > 2 else None
        return st

    res = {f"{a}_vs_{b}|{cls or 'all'}": compare(a, b, cls)
           for cls in (None, "clean", "crunch")
           for a, b in (("e0", "base"), ("oracle", "base"), ("Cp", "base"), ("e0", "oracle"), ("e0", "Cp"))}

    post = json.loads((OUT / "post.json").read_text())
    mel = json.loads((OUT / "mel.json").read_text())
    coh = np.array([post[s]["coherence"] for s in sorted(post)])

    def band_wtd(vals):
        by = {}
        for s, v in vals.items():
            by.setdefault(ps[s]["band"], []).append(v)
        m = np.mean([np.mean(v, axis=0) for v in by.values()], axis=0)
        return round(float(m), 4) if np.ndim(m) == 0 else [round(float(x), 4) for x in m]

    roundtrip = {
        "mel_distance": {"median": round(float(np.median(list(mel.values()))), 4),
                         "mean": round(float(np.mean(list(mel.values()))), 4),
                         "band_weighted": band_wtd(mel), "per_part": {k: round(v, 4) for k, v in mel.items()}},
        "coherence_80_1k_1_3k_3_8k": {"median": [round(float(x), 4) for x in np.median(coh, axis=0)],
                                      "band_weighted": band_wtd({s: post[s]["coherence"] for s in post}),
                                      "min": [round(float(x), 4) for x in coh.min(axis=0)]},
        "lag_samples": {s: post[s]["lag"] for s in sorted(post)},
        "lag_after_alignment": sorted({post[s]["lag_after"] for s in post}),
    }
    e0 = res["e0_vs_base|all"]["band_weighted_mean"]
    out = {
        "experiment": "EG-VAE-lite E0: DAC 44 kHz round trip of the true measure DI (docs/egvae-lite-plan.md)",
        "parts": len(ps), "bands": len({p["band"] for p in ps.values()}),
        "bar": BAR,
        "e0_vs_base_band_weighted": e0,
        "e0_vs_base_part_weighted": res["e0_vs_base|all"]["mean"],
        "oracle_vs_base_band_weighted": res["oracle_vs_base|all"]["band_weighted_mean"],
        "Cp_seed0_vs_base_band_weighted": res["Cp_vs_base|all"]["band_weighted_mean"],
        "edge_kept": round((res["Cp_vs_base|all"]["band_weighted_mean"] - e0)
                           / (res["Cp_vs_base|all"]["band_weighted_mean"]
                              - res["oracle_vs_base|all"]["band_weighted_mean"]), 3),
        "picks_same_as_oracle": round(sum(agree) / len(agree), 3),
        "decision": "continue (E1)" if e0 <= BAR else "drop the DAC route",
        "roundtrip": roundtrip,
        "truecheck": json.loads((OUT / "truecheck.json").read_text()) if (OUT / "truecheck.json").exists() else None,
        "results": res,
    }
    RESULT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    for k, s_ in res.items():
        print(f"  {k:24s} band-wtd {s_['band_weighted_mean']:+.4f} part {s_['mean']:+.4f} "
              f"[{s_['lo90']:+.3f}, {s_['hi90']:+.3f}] W/T/L {s_['wins']}/{s_['ties']}/{s_['losses']}")
    print({k: v for k, v in out.items() if k not in ("results", "roundtrip")})
    print(json.dumps({k: v for k, v in roundtrip.items() if k != "mel_distance"} |
                     {"mel": {k: v for k, v in roundtrip["mel_distance"].items() if k != "per_part"}}))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "render":
        render((int(sys.argv[2]), int(sys.argv[3])))
    elif cmd == "render-true":
        render_true(sys.argv[2])
    elif cmd == "score-true":
        score(true_check=True)
    else:
        {"prep": prep, "post": post, "score": score, "report": report}[cmd]()
