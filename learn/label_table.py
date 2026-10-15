"""Label table and stems for every clean and crunch development part (`docs/label-table-plan.md`).

    .venv/bin/python -m learn.label_table parts               # writes docs/label-table-parts.json
    .venv/bin/python -m learn.label_table render --shard 0/3
    .venv/bin/python -m learn.label_table stems-todo           # crop folders still needing a stem
    .venv/bin/python -m learn.label_table check
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

from learn import confirm_run as CR  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import phase2_set3 as P  # noqa: E402

HOME = K.HOME
OUT = HOME / "learn/label-table"
STEMS = OUT / "stems"
PARTS = PLUGIN_ROOT / "docs/label-table-parts.json"
S12_CROPS = HOME / "references/validation-crops"
OLD_STEMS = [HOME / "learn/poc/stems/htdemucs_6s", HOME / "learn/set3/stems/htdemucs_6s"]


def build_parts():
    """Every classed development part: sets 1–2 (waveform-passing, classified by set 3's rule)
    and set 3 (catalogue class)."""
    import numpy as np

    from analysis import io
    from learn import set3
    from learn import train as TR

    sys.path.insert(0, str(HOME / "references/datasets-set3/_tools"))
    import classify as C
    import gainmeasure as GM

    cat = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    lags = json.loads((PLUGIN_ROOT / "docs/validation-lags.json").read_text())["parts"]
    fold_of, band_of = TR.k3_folds()
    out = {}
    for s in cat["sessions"]:
        if s["split"] != "development":
            continue
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_") for x in (s["source"], s["song"], p["part"]))
            if slug not in lags:
                continue

            def load(name):
                a = io.load(HOME / "references/datasets" / s["path"] / name)
                assert a.sha256 == s["files"][name], name
                return np.asarray(a.mono(), np.float64)
            m = GM.measures(load(p["reference"]), load(p["di"]), P.SR, lags[slug]["lag_samples"])
            band = s.get("group") or f"{s['source']}/{s['song']}"
            out[slug] = {"set": 12, "band": band, "gain_class": C.classify(m)[0],
                         "judge_lag": lags[slug]["lag_samples"] - P.LATENCY, "crop": str(S12_CROPS / slug),
                         "fold": fold_of.get(band)}
    for p in set3.parts("development"):
        out[p["slug"]] = {"set": 3, "band": p["band"], "gain_class": p["gain_class"],
                          "judge_lag": p["judge_lag_samples"], "crop": str(P.CROPS / p["slug"]), "fold": None}
    keep = {k: v for k, v in out.items() if v["gain_class"] in ("clean", "crunch")}
    doc = {"rule": "docs/label-table-plan.md", "classed": len(out), "clean_or_crunch": len(keep),
           "classes_all": {k: v["gain_class"] for k, v in sorted(out.items())}, "parts": dict(sorted(keep.items()))}
    PARTS.write_text(json.dumps(doc, indent=1) + "\n")
    print(doc["classed"], "classed;", doc["clean_or_crunch"], "clean or crunch")


def parts():
    return json.loads(PARTS.read_text())["parts"]


def stem_path(slug):
    for d in [STEMS] + OLD_STEMS:
        for name in ("instrumental_guitar.wav", "mix_instrumental_guitar.wav"):
            f = d / slug / name
            if f.exists():
                return f
    return None


def judge2(ref, y, di, lag):
    from analysis.aligned import JUDGE_V3, aligned_distance

    out = {}
    for name, opts in (("flat", {}), ("v3", JUDGE_V3)):
        out[name] = {}
        for h, (a, b) in K.R.HALVES.items():
            x = aligned_distance(ref, y, di, lag=lag, render_latency=P.LATENCY, start_s=a, end_s=b, **opts).distance
            out[name][h] = math.inf if x is None else x
    return out


def render(shard):
    import numpy as np
    import soundfile as sf

    ps = parts()
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for slug in sorted(ps)[shard[0]::shard[1]]:
            d = OUT / slug
            if (d / "menu.json").exists():
                continue
            if not __import__("learn.knob_ceiling2", fromlist=["disk_ok"]).disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            part = ps[slug]
            di = K.measure_di({"crop": pathlib.Path(part["crop"])})
            ref = CR.mono(pathlib.Path(part["crop"]) / "reference.wav")
            di32 = di.astype(np.float32)
            res, best = {}, {}
            for amp, m in menu.items():
                first = next(iter(m.values()))
                rr.render(di32, *first)                                    # warm-up
                res[amp] = {}
                for name, (sel, ed) in m.items():
                    y = rr.render(di32, sel, ed)
                    res[amp][name] = judge2(ref, y, di, part["judge_lag"])
                    score = sum(res[amp][name]["flat"].values())
                    if amp not in best or score < best[amp][0]:
                        best[amp] = (score, name, y)
            d.mkdir(parents=True, exist_ok=True)
            for amp, (_, name, y) in best.items():
                y = y[int(0.25 * P.SR):]
                sf.write(str(d / f"best-{amp}.flac"), y * (0.99 / max(np.abs(y).max(), 1e-12)), P.SR,
                         subtype="PCM_16")
            K._atomic(d / "menu.json", res)
            print(slug, rr.count, flush=True)
    finally:
        rr.close()


def stems_todo():
    for slug, p in sorted(parts().items()):
        if stem_path(slug) is None:
            print(p["crop"])


def check():
    """The plan's checks: repeat renders (3 parts × 5 presets, a second order) and agreement with
    stored songs-check / gap-split distances."""
    import numpy as np

    ps = parts()
    out = {"repeat": {}, "vs_stored": {}}
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for slug in sorted(ps)[:3]:
            part = ps[slug]
            di = K.measure_di({"crop": pathlib.Path(part["crop"])})
            ref = CR.mono(pathlib.Path(part["crop"]) / "reference.wav")
            stored = json.loads((OUT / slug / "menu.json").read_text())
            names = list(menu["pr12"])[::-1][:5]
            for n in names:
                sel, ed = menu["pr12"][n]
                d = judge2(ref, rr.render(di.astype(np.float32), sel, ed), di, part["judge_lag"])
                out["repeat"][f"{slug}|{n}"] = max(abs(math.log(d["flat"][h] / stored["pr12"][n]["flat"][h]))
                                                  for h in "AB" if math.isfinite(d["flat"][h]))
    finally:
        rr.close()
    from learn import songs_check as SC
    D = json.loads((SC.OUT / "distances.json").read_text())
    for slug in ps:
        f = OUT / slug / "menu.json"
        if slug not in D or not f.exists():
            continue
        mine = json.loads(f.read_text())
        dev = []
        for amp in K.AMPS:
            for h in "AB":
                st = D[slug].get(f"flat|{amp}|measfix_{h}", {})
                for n, v in st.items():
                    a = mine[amp].get(n, {}).get("flat", {}).get(h)
                    if a and v[0] and math.isfinite(a):
                        dev.append(abs(math.log(a / v[0])))
        if dev:
            out["vs_stored"][slug] = {"max": max(dev), "median": float(np.median(dev))}
    K._atomic(OUT / "check.json", out)
    print("repeat max", max(out["repeat"].values()))
    for s, v in sorted(out["vs_stored"].items(), key=lambda x: -x[1]["max"])[:6]:
        print(s, v)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("parts", "render", "stems-todo", "check"))
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    i, n = map(int, a.shard.split("/"))
    {"parts": build_parts, "render": lambda: render((i, n)), "stems-todo": stems_todo, "check": check}[a.step]()


if __name__ == "__main__":
    main()
