"""From a song, not an amp track (`docs/songs-check-plan.md`). Development only.

    .venv/bin/python -m learn.songs_check prep            # sets 1–2 gain classes (no renders)
    $TORCH_PY -m learn.songs_check render --shard 0/3
    $TORCH_PY -m learn.songs_check score
    $TORCH_PY -m learn.songs_check report
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import confirm_run as CR  # noqa: E402
from learn import phase2_set3 as P  # noqa: E402
from learn import rescore as R  # noqa: E402
from learn import set3_gap_split as G  # noqa: E402

HOME = pathlib.Path("~/ndsp-presets").expanduser()
D3 = HOME / "learn/direc"
OUT = D3 / "songs-check"
PREP = OUT / "prep-sets12.json"
S12_STEMS = HOME / "learn/poc/stems"
S12_CROPS = HOME / "references/validation-crops"
S3_STEMS = HOME / "learn/set3/stems"
MODELS = D3 / "models-final"
KINDS = ("measfix", "amp", "stem")
EXISTING_S3 = {"measfix": D3 / "gap-split/measfix", "amp": D3 / "v2-eval/lp3k"}


def _usable(manifest):
    return sorted(p for p, v in json.loads(manifest.read_text())["parts"].items() if v.get("usable"))


def prep():
    """Session-level gain class of the sets 1–2 development stem parts, set 3's rule."""
    import numpy as np

    from analysis import io

    sys.path.insert(0, str(HOME / "references/datasets-set3/_tools"))
    import classify as C
    import gainmeasure as GM

    cat = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    entries = {(s["source"], s["song"], p["part"]): (s, p) for s in cat["sessions"] for p in s["parts"]}
    lags = json.loads((PLUGIN_ROOT / "docs/validation-lags.json").read_text())["parts"]
    out = {}
    for part in _usable(S12_STEMS / "manifest.json"):
        rec = json.loads((S12_CROPS / part / "record.json").read_text())
        s, p = entries[(rec["source"], rec["song"], rec["part"])]
        assert s["split"] == "development", part

        def load(name):
            a = io.load(HOME / "references/datasets" / s["path"] / name)
            assert a.sha256 == s["files"][name], name
            return np.asarray(a.mono(), np.float64)

        # validation-lags.json: samples the amp track lags its DI (gainmeasure's convention)
        m = GM.measures(load(p["reference"]), load(p["di"]), P.SR, lags[part]["lag_samples"])
        cls, conf, why, split = C.classify(m)
        out[part] = {"gain_class": cls, "gain_confidence": conf, "clean_vs_driven": split}
        print(part, cls, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    PREP.write_text(json.dumps(out, indent=1))


def parts():
    """slug -> {crop, stem, judge_lag, band, gain_class, set, fold}."""
    from learn import set3
    from learn import train as TR

    out = {}
    s3 = {p["slug"]: p for p in set3.parts("development")}
    for slug in _usable(S3_STEMS / "manifest.json"):
        p = s3[slug]
        out[slug] = dict(crop=P.CROPS / slug, stem=S3_STEMS / "htdemucs_6s" / slug / "instrumental_guitar.wav",
                         judge_lag=p["judge_lag_samples"], band=p["band"], gain_class=p["gain_class"],
                         set=3, fold=None, flags=[])
    fold_of, band_of = TR.k3_folds()
    lags = json.loads((PLUGIN_ROOT / "docs/validation-lags.json").read_text())["parts"]
    classes = json.loads(PREP.read_text())
    for slug in _usable(S12_STEMS / "manifest.json"):
        out[slug] = dict(crop=S12_CROPS / slug, stem=S12_STEMS / "htdemucs_6s" / slug / "instrumental_guitar.wav",
                         # the judge's lag is behind the render, which lags the DI by the latency
                         judge_lag=lags[slug]["lag_samples"] - P.LATENCY, band=band_of[slug],
                         gain_class=classes[slug]["gain_class"], set=12, fold=fold_of[band_of[slug]], flags=[])
    return out


def kind_dir(kind, slug, part):
    if part["set"] == 3 and kind in EXISTING_S3:
        return EXISTING_S3[kind] / slug
    return OUT / kind / slug


def build_di(kind, part, nets):
    import numpy as np
    import torch

    from learn import direc as D
    from learn.direc_check import to_lufs
    from learn.rebuilt_judge import lowpass

    if kind == "measfix":
        return CR.build_di("measfix", part)
    net = nets["set3"] if part["set"] == 3 else nets[part["fold"]]
    src = part["stem"] if kind == "stem" else part["crop"] / "reference.wav"
    rec = CR.mono(src)
    return lowpass(to_lufs(D.rebuild(net, rec.astype(np.float32), device=torch.device("cpu")).astype(np.float64)))


def render(shard):
    import numpy as np
    import soundfile as sf

    import render_preset_panel as RP
    from learn import direc as D
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    nets = {k: D.load_model(MODELS / f"fold{k}.pt").eval() for k in range(4)}
    nets["set3"] = D.load_model(CR.MODEL).eval()
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
                base = kind_dir(kind, slug, ps[slug])
                if (base / "done").exists():
                    continue
                base.mkdir(parents=True, exist_ok=True)
                di = build_di(kind, ps[slug], nets)
                np.save(base / "di.npy", di)
                d32 = di.astype(np.float32)
                for amp, m in M.items():
                    (base / amp).mkdir(exist_ok=True)
                    r.render(d32, {"panel": f"{amp}|template+R"})
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
    ref = CR.mono(part["crop"] / "reference.wav")
    res = {}
    for kind in KINDS:
        d = kind_dir(kind, slug, part)
        di = np.load(d / "di.npy")
        for amp, ns in names.items():
            for n in ns:
                y = P.mono(d / amp / f"{RP._slug(n)}.wav")
                for h, (a, b) in R.HALVES.items():
                    if kind == "measfix":
                        x = aligned_distance(ref, y, di, lag=part["judge_lag"], render_latency=P.LATENCY,
                                             start_s=a, end_s=b)
                    else:
                        x, _ = rebuilt_distance(ref, y, di, start_s=a, end_s=b)
                    res.setdefault(f"flat|{amp}|{kind}_{h}", {})[n] = (x.distance, x.tonal, x.temporal)
    print(slug, flush=True)
    return slug, res


def score(workers=7):
    from concurrent.futures import ProcessPoolExecutor

    ps, names = parts(), G.menu_names()
    for s, p in ps.items():
        for k in KINDS:
            if not (kind_dir(k, s, p) / "done").exists():
                raise SystemExit(f"missing renders: {k}/{s}")
    with ProcessPoolExecutor(workers) as ex:
        D = dict(ex.map(_score_part, [(s, ps[s], names) for s in sorted(ps)]))
    (OUT / "distances.json").write_text(json.dumps(D))


def report():
    D = json.loads((OUT / "distances.json").read_text())
    ps = parts()

    def baseline(slug, amp, choose):
        return "template+R" if ps[slug]["gain_class"] == "clean" else CR.SHIPPED[amp]

    C = CR.cells(D, ps, "flat", baseline, kinds=KINDS)
    out = {}
    for name, keep in (("clean+crunch", ("clean", "crunch")), ("clean", ("clean",)),
                       ("crunch", ("crunch",)), ("high-gain", ("high-gain",))):
        sel = {k: v for k, v in C.items() if ps[k[0]]["gain_class"] in keep}
        if not sel:
            continue
        row = lambda key: [(ps[s]["band"], v[key]) for (s, a), v in sel.items()]
        out[name] = {k: CR.stats(row(k)) for k in KINDS}
        out[name]["stem_minus_amp"] = CR.stats([(ps[s]["band"], v["stem"] - v["amp"]) for (s, a), v in sel.items()])
        for src in (3, 12):
            r = [(ps[s]["band"], v["stem"]) for (s, a), v in sel.items() if ps[s]["set"] == src]
            if r:
                out[name][f"stem_set{src}"] = CR.stats(r)
    cc = out.get("clean+crunch")
    if cc:
        go = cc["stem"]["hi90"] < 0 and cc["stem"]["mean"] <= 0.5 * cc["amp"]["mean"]
        out["decision"] = "product step" if go else "improve the stem path first"
    (OUT / "result.json").write_text(json.dumps(out, indent=1, default=float))
    print("DECISION:", out.get("decision"))
    for name, v in out.items():
        if not isinstance(v, dict):
            continue
        for k, s in v.items():
            print(f"  {name:13s} {k:15s} mean {s['mean']:+.3f} 90% [{s['lo90']:+.3f}, {s['hi90']:+.3f}] "
                  f"W/T/L {s['wins']}/{s['ties']}/{s['losses']} bands {s['bands']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("prep", "render", "score", "report"))
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    if a.cmd == "prep":
        prep()
    elif a.cmd == "render":
        render(tuple(int(v) for v in a.shard.split("/")))
    elif a.cmd == "score":
        score()
    else:
        report()


if __name__ == "__main__":
    main()
