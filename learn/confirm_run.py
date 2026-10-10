"""Confirming the rebuilt-DI chooser on fresh material (`docs/set4-confirmation-plan.md`).

Parts: the sets 1–2 held-out parts that pass the waveform rule (`prep.json` of
`learn/confirm_prep.py`) and set 4's declared parts (`docs/validation-set4.json`, pinned).

Kinds, each rendered through every menu preset over the whole 10-s crop:
- `measfix`: the true DI re-equalised to K3 fold 2's average balance (the pinned file), at
  −22.9 LUFS: the measure, and the oracle's chooser;
- `lp3k`: the set-3 network's rebuilt DI, low-passed at 3 kHz, at −22.9 LUFS: the chooser;
- `net`: the same rebuilt DI uncut (report only).

    $TORCH_PY -m learn.confirm_run dev-check            # reproduce development, no new audio
    $TORCH_PY -m learn.confirm_run render --shard 0/3
    $TORCH_PY -m learn.confirm_run score
    $TORCH_PY -m learn.confirm_run report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import phase2_set3 as P  # noqa: E402
from learn import rescore as R  # noqa: E402
from learn import set3_gap_split as G  # noqa: E402

HOME = pathlib.Path("~/ndsp-presets").expanduser()
PREP = HOME / "references/validation-crops-confirm/prep.json"
SET4 = PLUGIN_ROOT / "docs/validation-set4.json"
SET4_CROPS = HOME / "references/validation-crops-set4"
OUT = HOME / "learn/direc/confirm"
AVERAGE = HOME / "learn/direc/cache/average-fold2.npy"
MODEL = HOME / "learn/direc/models-set3/fold2.pt"
KINDS = ("measfix", "lp3k", "net")
JUDGES = ("flat", "fixed")
SHIPPED = {"pr12": "factory:Neural DSP/Vintage Metal",
           "sw50r": "factory:Artists/Royce Whittaker/Wall Of Doom",
           "ac20": "factory:Artists/Charlie Robbins/Dirty Coil Rhythm"}
RULE = {"pr12": "factory:Artists/Keyan Houshmand/Modern Metal (Pick Hard)",
        "sw50r": "factory:Artists/Royce Whittaker/Wall Of Doom",
        "ac20": "factory:Artists/Danny Dela Cruz/Raw N Crunchy"}
FLAGGED_SET4 = {"di_touches_full_scale", "amp_earlier_than_di", "late_amp_track"}


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def parts():
    """slug -> {crop, judge_lag, band, gain_class, source, flags}."""
    out = {}
    for slug, v in json.loads(PREP.read_text()).items():
        if v["waveform_pass"]:
            out[slug] = dict(crop=pathlib.Path(v["crop"]), judge_lag=v["judge_lag_samples"],
                             band=v["band"], gain_class=v["gain_class"], source="sets12", flags=[])
    for p in json.loads(SET4.read_text())["parts"]:
        out[p["slug"]] = dict(crop=SET4_CROPS / p["slug"], judge_lag=p["judge_lag_samples"],
                              band=p["band"], gain_class=p["gain_class"], source="set4",
                              flags=sorted(set(p.get("marks", [])) | set(p.get("catalog_flags", []))))
    return out


def mono(path):
    import numpy as np
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    assert sr == P.SR, path
    return x.mean(axis=1)


def build_di(kind, part, net=None):
    import numpy as np
    import torch

    from learn import direc as D
    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs
    from learn.rebuilt_judge import lowpass

    if kind == "measfix":
        avg = np.load(AVERAGE)
        di = mono(part["crop"] / "di.wav")
        own = smoothed_spectrum(di)
        return to_lufs(eq_to(di, avg - (own - own.mean())))
    rec = mono(part["crop"] / "reference.wav")
    rebuilt = to_lufs(D.rebuild(net, rec.astype(np.float32), device=torch.device("cpu")).astype(np.float64))
    return lowpass(rebuilt) if kind == "lp3k" else rebuilt


def render(shard):
    import numpy as np
    import soundfile as sf

    import render_preset_panel as RP
    from learn import direc as D
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    net = D.load_model(MODEL).eval()
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
    ps = parts()
    try:
        for slug in sorted(ps)[shard[0]::shard[1]]:
            for kind in KINDS:
                base = OUT / kind / slug
                if (base / "done").exists():
                    continue
                base.mkdir(parents=True, exist_ok=True)
                di = build_di(kind, ps[slug], net)
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
    from analysis.aligned import aligned_distance
    from learn.rebuilt_judge import rebuilt_distance

    slug, part, names = job
    ref = mono(part["crop"] / "reference.wav")
    res = {}
    for kind in KINDS:
        d = OUT / kind / slug
        di = np.load(d / "di.npy")
        for amp, ns in names.items():
            for n in ns:
                y = P.mono(d / amp / f"{RP._slug(n)}.wav")
                for judge in JUDGES:
                    kw = R.JUDGE_OPTIONS[judge]
                    for h, (a, b) in R.HALVES.items():
                        if kind == "measfix":
                            x = aligned_distance(ref, y, di, lag=part["judge_lag"],
                                                 render_latency=P.LATENCY, start_s=a, end_s=b, **kw)
                        else:
                            x, _ = rebuilt_distance(ref, y, di, start_s=a, end_s=b, **kw)
                        res.setdefault(f"{judge}|{amp}|{kind}_{h}", {})[n] = (
                            x.distance, x.tonal, x.temporal)
    print(slug, flush=True)
    return slug, res


def score(workers=7):
    from concurrent.futures import ProcessPoolExecutor

    ps, names = parts(), G.menu_names()
    for s in ps:
        for k in KINDS:
            if not (OUT / k / s / "done").exists():
                raise SystemExit(f"missing renders: {k}/{s}")
    jobs = [(s, {k: (str(v) if isinstance(v, pathlib.Path) else v) for k, v in ps[s].items()}, names)
            for s in sorted(ps)]
    for j in jobs:
        j[1]["crop"] = pathlib.Path(j[1]["crop"])
    with ProcessPoolExecutor(workers) as ex:
        D = dict(ex.map(_score_part, jobs))
    (OUT / "distances.json").write_text(json.dumps(D))


# --- the comparisons -------------------------------------------------------------------

def _pick(row):
    row = {n: v[0] for n, v in row.items() if v[0]}
    return min(row, key=lambda n: (row[n], n)) if row else None


def cells(D, ps, judge, baseline, kinds=("measfix", "lp3k", "net")):
    """{(slug, amp): {kind: mean over both directions of log(d(pick)/d(baseline))}},
    the measure taken on the other half with `measfix`. `baseline(slug, amp, choose)` names
    the baseline preset. A kind whose pick is fully refused takes the baseline (0); a cell
    whose measure is refused for the baseline or a pick is dropped."""
    out = {}
    for slug, part in ps.items():
        for amp in P.AMPS:
            vals = {k: [] for k in kinds}
            for choose, other in (("A", "B"), ("B", "A")):
                meas = D[slug][f"{judge}|{amp}|measfix_{other}"]
                b = baseline(slug, amp, choose)
                if not meas.get(b) or not meas[b][0]:
                    vals = None
                    break
                for k in kinds:
                    p = _pick(D[slug][f"{judge}|{amp}|{k}_{choose}"]) or b
                    if not meas[p][0]:
                        vals = None
                        break
                    vals[k].append(math.log(meas[p][0]) - math.log(meas[b][0]))
                if vals is None:
                    break
            if vals is not None:
                out[(slug, amp)] = {k: statistics.fmean(v) for k, v in vals.items()}
    return out


def stats(rows):
    """rows: (band, x). The declared statistics, with the leave-one-band-out range."""
    s = R.clustered(rows)
    by = {}
    for b, x in rows:
        by.setdefault(b, []).append(x)
    s["band_weighted_mean"] = round(statistics.fmean(statistics.fmean(v) for v in by.values()), 4)
    s["bands_negative"] = sum(statistics.fmean(v) < 0 for v in by.values())
    s["leave_one_band_out"] = [round(statistics.fmean([x for bb, x in rows if bb != b]), 4) for b in by] \
        if len(by) > 1 else []
    return s


def outcome(oracle, chooser):
    if not oracle["hi90"] < 0:
        return "uninformative"
    robust = (chooser["leave_one_band_out"] and max(chooser["leave_one_band_out"]) < 0
              and chooser["bands_negative"] > chooser["bands"] / 2)
    if chooser["hi90"] < 0 and robust:
        return "confirmed"
    if chooser["lo90"] > -0.05:
        return "no meaningful edge"
    return "inconclusive"


def summarise(D, ps, judge="flat", constants=SHIPPED, exclude_flagged=False):
    def baseline(slug, amp, choose):
        return "template+R" if ps[slug]["gain_class"] == "clean" else constants[amp]

    use = {s: p for s, p in ps.items() if not (exclude_flagged and set(p["flags"]) & FLAGGED_SET4)}
    C = cells(D, use, judge, baseline)
    res = {}
    strata = {"clean+crunch": ("clean", "crunch"), "clean": ("clean",), "crunch": ("crunch",),
              "high-gain": ("high-gain",)}
    for name, classes in strata.items():
        rows = {k: [(use[s]["band"], v[k]) for (s, a), v in C.items() if use[s]["gain_class"] in classes]
                for k in ("measfix", "lp3k", "net")}
        if rows["lp3k"]:
            res[name] = {"oracle": stats(rows["measfix"]), "chooser": stats(rows["lp3k"]),
                         "uncut": stats(rows["net"])}
    if "clean+crunch" in res:
        res["outcome"] = outcome(res["clean+crunch"]["oracle"], res["clean+crunch"]["chooser"])
    for amp in P.AMPS:
        rows = [(use[s]["band"], v["lp3k"]) for (s, a), v in C.items()
                if a == amp and use[s]["gain_class"] != "high-gain"]
        if rows:
            res[f"clean+crunch|{amp}"] = stats(rows)
    res["cells"] = len(C)
    return res


def dev_check():
    """The development figures the plan names, from the stored set-3 distances, through
    the same comparison code: −0.162 (clean and crunch vs baseline, leave-band-out constant
    for crunch), −0.143 (the chooser vs the leave-band-out constant, all parts), −0.260 (the
    oracle vs that constant)."""
    D = json.loads((R.OUT / "distances.json").read_text())
    ps = {s: dict(band=p["band"], gain_class=p["gain_class"], flags=[]) for s, p in G.parts().items()}

    def lbo(slug, amp, choose):
        others = [x for x, q in ps.items() if q["band"] != ps[slug]["band"]]
        meds = {n: statistics.median([D[x][f"flat|{amp}|measfix_{choose}"][n][0] for x in others
                                      if D[x][f"flat|{amp}|measfix_{choose}"][n][0]])
                for n in D[slug][f"flat|{amp}|measfix_{choose}"] if n.startswith("factory:")}
        return min(meds, key=lambda n: (meds[n], n))

    def product(slug, amp, choose):
        return "template+R" if ps[slug]["gain_class"] == "clean" else lbo(slug, amp, choose)

    out = {}
    C = cells(D, {s: p for s, p in ps.items() if p["gain_class"] != "high-gain"}, "flat", product)
    out["clean+crunch chooser vs product baseline"] = R.clustered(
        [(ps[s]["band"], v["lp3k"]) for (s, a), v in C.items()])["mean"]
    C = cells(D, ps, "flat", lbo)
    out["chooser vs leave-band-out constant"] = R.clustered(
        [(ps[s]["band"], v["lp3k"]) for (s, a), v in C.items()])["mean"]
    out["oracle vs leave-band-out constant"] = R.clustered(
        [(ps[s]["band"], v["measfix"]) for (s, a), v in C.items()])["mean"]
    print(json.dumps(out, indent=1))
    return out


def manifest():
    import importlib.metadata
    import subprocess

    ps = parts()
    m = {"network_sha256": sha256(MODEL), "average_sha256": sha256(AVERAGE),
         "set4_declaration_sha256": sha256(SET4), "prep_sha256": sha256(PREP),
         "code_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=PLUGIN_ROOT,
                                       capture_output=True, text=True).stdout.strip(),
         "parts": {s: {"band": p["band"], "gain_class": p["gain_class"], "source": p["source"],
                       "judge_lag": p["judge_lag"], "flags": p["flags"],
                       "reference_sha256": sha256(p["crop"] / "reference.wav"),
                       "di_sha256": sha256(p["crop"] / "di.wav")} for s, p in sorted(ps.items())},
         "shipped_presets": SHIPPED, "rule_presets": RULE,
         "torch": importlib.metadata.version("torch")}
    return m


def report():
    D = json.loads((OUT / "distances.json").read_text())
    ps = parts()
    out = {"primary": summarise(D, ps),
           "sensitivity": {"rule_presets": summarise(D, ps, constants=RULE),
                           "without_flagged": summarise(D, ps, exclude_flagged=True),
                           "judge_v2": summarise(D, ps, judge="fixed")}}
    (OUT / "result.json").write_text(json.dumps(out, indent=1, default=float))
    p = out["primary"]
    print("OUTCOME:", p.get("outcome"))
    for k in ("clean+crunch", "clean", "crunch", "high-gain"):
        if k in p:
            for role in ("oracle", "chooser", "uncut"):
                s = p[k][role]
                print(f"  {k:13s} {role:8s} mean {s['mean']:+.3f} 90% [{s['lo90']:+.3f}, {s['hi90']:+.3f}] "
                      f"W/T/L {s['wins']}/{s['ties']}/{s['losses']} bands {s['bands']} "
                      f"neg {s['bands_negative']} LOBO {min(s['leave_one_band_out'] or [0]):+.3f}..{max(s['leave_one_band_out'] or [0]):+.3f}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("dev-check", "manifest", "render", "score", "report"))
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--workers", type=int, default=7)
    a = ap.parse_args(argv)
    if a.cmd == "dev-check":
        dev_check()
    elif a.cmd == "manifest":
        print(json.dumps(manifest(), indent=1))
    elif a.cmd == "render":
        render(tuple(int(v) for v in a.shard.split("/")))
    elif a.cmd == "score":
        score(a.workers)
    else:
        report()


if __name__ == "__main__":
    main()
