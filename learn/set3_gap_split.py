"""Where the rebuilt DI loses the preset choice (`docs/set3-gap-split-plan.md`).

Development parts only. Reuses `phase2_set3`'s stored `measure` and `net` DIs, renders
and distances, and adds:
- `netlvl`: the rebuilt DI at the measure DI's loudness;
- `netlvleq`: the rebuilt DI re-equalised to the measure DI's smoothed spectrum, at its
  loudness;
- `measfix`: the measure DI at −22.9 LUFS;
- `netmask` (no renders): the `net` renders judged with the measure DI as the mask.

    $TORCH_PY -m learn.set3_gap_split render --shard 0/3
    $TORCH_PY -m learn.set3_gap_split score
    $TORCH_PY -m learn.set3_gap_split summary
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import phase2_set3 as P  # noqa: E402

SRC = P.OUT                                                  # phase2-set3 (development)
OUT = SRC.with_name("gap-split")
KINDS = ("netlvl", "netlvleq", "measfix")
STEPS = (("level", "net", "netlvl"), ("balance", "netlvl", "netlvleq"),
         ("rest", "netlvleq", "oracle"), ("mask", "net", "netmask"),
         ("level_with_true_waveform", "measfix", "oracle"))


def lufs(x):
    import numpy as np
    import pyloudnorm

    return pyloudnorm.Meter(P.SR).integrated_loudness(np.asarray(x, np.float64))


def build_di(kind, slug):
    import numpy as np

    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs

    mdi = np.load(SRC / "measure" / slug / "di.npy")
    if kind == "measfix":
        return to_lufs(mdi)
    ndi = np.load(SRC / "net" / slug / "di.npy")
    if kind == "netlvleq":
        tgt, own = smoothed_spectrum(mdi), smoothed_spectrum(ndi)
        ndi = eq_to(ndi, (tgt - tgt.mean()) - (own - own.mean()))
    return to_lufs(ndi, lufs(mdi))


def parts():
    from learn import set3

    return {p["slug"]: p for p in set3.parts("development")}


def render(shard):
    import numpy as np
    import soundfile as sf

    import render_preset_panel as RP
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

    r = PanelRenderer("morgan", process_policy="reuse")
    M = P.menus(pack, r)
    PanelRenderer.commands = {f"{amp}|{n}": v for amp, m in M.items() for n, v in m.items()}
    try:
        for slug in sorted(parts())[shard[0]::shard[1]]:
            for kind in KINDS:
                base = OUT / kind / slug
                if (base / "done").exists():
                    continue
                base.mkdir(parents=True, exist_ok=True)
                di = build_di(kind, slug)
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


def shifted(x, by):
    """`x` delayed by `by` samples (advanced when negative), same length."""
    import numpy as np

    out = np.zeros_like(x)
    if by >= 0:
        out[by:] = x[:len(x) - by]
    else:
        out[:by] = x[-by:]
    return out


def _score_part(job):
    import numpy as np

    import render_preset_panel as RP
    from analysis.aligned import aligned_distance

    slug, lag, names = job
    ref = P.recording(slug, "ref", P.RunConfig())
    mdi = np.load(SRC / "measure" / slug / "di.npy")
    # The measure DI on the recording's timeline: recording[t] <-> mdi[t - lag - latency];
    # the rebuilt-DI scoring reads di[t] for recording[t] (lag -52, latency 52).
    mask = shifted(mdi, lag + P.LATENCY)
    res = {}
    for bs in P.BAND_SETS:
        for amp, ns in names.items():
            for kind in KINDS + ("netmask",):
                d = (SRC / "net" if kind == "netmask" else OUT / kind) / slug
                di = mask if kind == "netmask" else np.load(d / "di.npy")
                kl = lag if kind == "measfix" else -P.LATENCY
                res[f"{bs}|{amp}|{kind}_A"] = {
                    n: aligned_distance(ref, P.mono(d / amp / f"{RP._slug(n)}.wav"), di, lag=kl,
                                        render_latency=P.LATENCY, start_s=P.HALF_A[0],
                                        end_s=P.HALF_A[1], bands=bs).distance for n in ns}
            # `measfix` on half B: the alternative reading, the measure at a fixed level.
            d = OUT / "measfix" / slug
            di = np.load(d / "di.npy")
            res[f"{bs}|{amp}|measfix_B"] = {
                n: aligned_distance(ref, P.mono(d / amp / f"{RP._slug(n)}.wav"), di, lag=lag,
                                    render_latency=P.LATENCY, start_s=P.HALF_B[0],
                                    end_s=P.HALF_B[1], bands=bs).distance for n in ns}
    print(slug, flush=True)
    return slug, res


def menu_names():
    import render_preset_panel as RP
    from packs.loader import load_pack

    pack = load_pack("morgan")

    class Dummy:
        def _stored(self, pack, spec, value):
            return pack.to_stored(spec, value, warnings=[])

    return {amp: [n for n in RP.candidates(argparse.Namespace(amp=amp, factory_dir=RP.FACTORY),
                                           pack, Dummy()) if n != "template"] for amp in P.AMPS}


def score(workers):
    from concurrent.futures import ProcessPoolExecutor

    ps, names = parts(), menu_names()
    for s in ps:
        for k in KINDS:
            if not (OUT / k / s / "done").exists():
                raise SystemExit(f"missing renders: {k}/{s}")
    jobs = [(s, ps[s]["judge_lag_samples"], names) for s in sorted(ps)]
    with ProcessPoolExecutor(workers) as ex:
        D = dict(ex.map(_score_part, jobs))
    (OUT / "distances.json").write_text(json.dumps(D, indent=1))


def _sign_flip(vals):
    """Two-sided sign-flip p; exact up to 16 values, else 200,000 seeded random flips."""
    import itertools
    import random

    obs = abs(sum(vals))
    if len(vals) <= 16:
        flips = list(itertools.product((1, -1), repeat=len(vals)))
    else:
        rng = random.Random(20261009)
        flips = [[rng.choice((1, -1)) for _ in vals] for _ in range(200_000)]
    hits = sum(abs(sum(s * v for s, v in zip(signs, vals))) >= obs - 1e-12 for signs in flips)
    return hits / len(flips)


def describe(rows):
    """rows: (band, x). Mean, wins/ties/losses (|x| < 1e-9 ties), band median of medians."""
    if not rows:
        return None
    xs = [x for _, x in rows]
    by = {}
    for b, x in rows:
        by.setdefault(b, []).append(x)
    med = [statistics.median(v) for v in by.values()]
    return {"mean": round(statistics.fmean(xs), 4), "n": len(xs),
            "wins": sum(x < -1e-9 for x in xs), "ties": sum(abs(x) <= 1e-9 for x in xs),
            "losses": sum(x > 1e-9 for x in xs),
            "band_median": round(statistics.median(med), 4), "bands": len(med),
            "sign_flip_p": round(_sign_flip(med), 4)}


def summary():
    base = json.loads((SRC / "distances.json").read_text())
    new = json.loads((OUT / "distances.json").read_text())
    ps = parts()
    out = {}
    for bs in P.BAND_SETS:
        pooled = {s[0]: [] for s in STEPS}
        pooled["gap"] = []
        for amp in P.AMPS:
            per = {s[0]: [] for s in STEPS}
            per["gap"] = []
            for slug, p in sorted(ps.items()):
                rows = {**base[slug], **new[slug]}
                B = rows[f"{bs}|{amp}|measure_B"]
                picks = {}
                for kind in ("net", "netmask", "measfix", "netlvl", "netlvleq", "oracle"):
                    key = "measure_A" if kind == "oracle" else f"{kind}_A"
                    A = {n: v for n, v in rows[f"{bs}|{amp}|{key}"].items() if v}
                    pick = min(A, key=lambda n: (A[n], n)) if A else None
                    picks[kind] = math.log(B[pick]) if pick and B.get(pick) else None
                for name, a, b in STEPS + (("gap", "net", "oracle"),):
                    if picks[a] is not None and picks[b] is not None:
                        per[name].append((p["band"], picks[b] - picks[a]))
            out[f"{bs}|{amp}"] = {k: describe(v) for k, v in per.items()}
            for k, v in per.items():
                pooled[k] += [(f"{amp}|{b}", x) for b, x in v]
        out[f"{bs}|pooled"] = {k: describe(v) for k, v in pooled.items()}
        # The alternative reading: the measure's DI at −22.9 LUFS on half B.
        for amp in P.AMPS:
            alt = {}
            for kind in ("net", "oracle_fixed"):
                rows_k = []
                for slug, p in sorted(ps.items()):
                    rows = {**base[slug], **new[slug]}
                    B = rows[f"{bs}|{amp}|measfix_B"]
                    key = "measfix_A" if kind == "oracle_fixed" else "net_A"
                    A = {n: v for n, v in rows[f"{bs}|{amp}|{key}"].items() if v}
                    t = B.get("template+R")
                    if A and t:
                        pick = min(A, key=lambda n: (A[n], n))
                        if B.get(pick):
                            rows_k.append((p["band"], math.log(B[pick]) - math.log(t)))
                alt[kind] = describe(rows_k)
            out[f"{bs}|{amp}|fixed_level_measure_vs_template"] = alt
    (OUT / "summary.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        print(k)
        for name, d in v.items():
            print(f"  {name:28s} {d}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("render", "score", "summary"))
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args(argv)
    if args.cmd == "render":
        render(tuple(int(v) for v in args.shard.split("/")))
    elif args.cmd == "score":
        score(args.workers)
    else:
        summary()


if __name__ == "__main__":
    main()
