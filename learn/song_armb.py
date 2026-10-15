"""Arm B's positive control, predictions and scoring (`docs/song-settings-plan.md`, arm B).

The steps alternate between the renderer's interpreter (.venv) and torch's ($TORCH_PY):

    .venv/bin/python -m learn.song_armb control-draw         # planted targets per fold
    .venv/bin/python -m learn.song_armb control-render       # planted renders through the raw DI
    $TORCH_PY      -m learn.song_armb control-features      # mix, master, separate, features
    $TORCH_PY      -m learn.song_armb predict               # control targets + step 3's cells + controls
    .venv/bin/python -m learn.song_armb score --shard 0/4    # every prediction through the measure DI
    .venv/bin/python -m learn.song_armb report
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import confirm_run as CR  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import song_bank as B  # noqa: E402

OUT = B.OUT.parent / "armB"
N_CONTROL = 36            # planted targets per fold; those with d_start − d_target < 0.1 are dropped
SEED = 20261019


def _settings_json(x):
    return {f"{m}/{k}": v for (m, k), v in x.items()}


def _settings(d):
    return {tuple(k.rsplit("/", 1)): v for k, v in d.items()}


# --- the positive control ---------------------------------------------------------------------

def control_draw():
    """Per fold: planted settings drawn like the bank's broad half, on P1/P2 windows that no bank
    example uses (held apart), with a same-fold backing."""
    rng = random.Random(SEED)
    win = json.loads((B.OUT / "windows.json").read_text())
    ex = json.loads((B.OUT / "examples.json").read_text())
    used = {(e["window"]["path"], e["window"]["start"]) for e in ex}
    free = [w for w in win if w["fold"] == "all" and (w["path"], w["start"]) not in used]
    back = B.backings()
    out = []
    for fold in range(4):
        b = [x for x in back if x[1] == fold]
        for j in range(N_CONTROL):
            w = rng.choice(free)
            out.append({"i": len(out), "fold": fold, "window": w, "amp": rng.choice(K.AMPS),
                        "class": rng.choice(("clean", "crunch")), "mode": "broad", "centre": None,
                        "backing": rng.choice(b)[2], "second_guitar": False, "mastered": rng.random() < 0.5,
                        "aac": rng.random() < 0.5, "separated": rng.random() < 0.5, "seed": rng.randrange(2 ** 31)})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "control-targets.json").write_text(json.dumps(out))
    print(len(out), "targets;", len(free), "free P1/P2 windows")


def control_render():
    """The planted settings through the window's raw DI (the clean target, also the input to the
    mixture) and through the measure DI, plus S and the fold's median label through the measure DI."""
    import numpy as np
    import soundfile as sf

    targets = json.loads((OUT / "control-targets.json").read_text())
    rr = K.Renderer()
    d = OUT / "control"
    d.mkdir(parents=True, exist_ok=True)
    try:
        menu = rr.menu()
        for t in sorted(targets, key=lambda t: (t["amp"], t["class"])):
            if (d / f"{t['i']:03d}.json").exists():
                continue
            sel, x, label = B.settings_for(t, menu)
            raw = B.load_window(t["window"])
            from learn.direc_check import to_lufs
            raw = to_lufs(raw.astype(np.float64)).astype(np.float32)
            meas = B.measure(B.load_window(t["window"])).astype(np.float32)
            trim = slice(int(B.TRIM_S * B.SR), int((B.TRIM_S + B.WIN_S) * B.SR))
            clean = np.asarray(rr.render(raw, sel, x), np.float64)
            clean = (clean.mean(axis=1) if clean.ndim == 2 else clean)[trim]
            peak = max(np.abs(clean).max(), 1e-12)
            sf.write(str(d / f"{t['i']:03d}-clean.flac"), (clean / peak * 0.99).astype(np.float32), B.SR, subtype="PCM_16")
            np.save(d / f"{t['i']:03d}-measure-di.npy", meas)
            (d / f"{t['i']:03d}.json").write_text(json.dumps({"label": label, "peak": peak,
                                                              "settings": _settings_json(x)}))
            print(t["i"], flush=True)
    finally:
        rr.close()


def control_features():
    """Mixture, mastering, separation and features for each control target, as the bank."""
    import numpy as np
    import soundfile as sf

    from learn import song_aug as A

    targets = json.loads((OUT / "control-targets.json").read_text())
    lv = json.loads((B.OUT / "levels.json").read_text())
    levels = list(lv["guitar_to_backing_db"].values())
    d = OUT / "control"
    sep = None
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for t in targets:
            f = d / f"{t['i']:03d}-features.npz"
            if f.exists():
                continue
            y, _ = sf.read(str(d / f"{t['i']:03d}-clean.flac"), dtype="float64")
            meta = json.loads((d / f"{t['i']:03d}.json").read_text())
            g = y / 0.99 * meta["peak"]
            rng = random.Random(t["seed"] ^ 0x5EED)
            back, _ = sf.read(t["backing"], dtype="float64")
            back = back.mean(axis=1) if back.ndim == 2 else back
            back = np.pad(back, (0, max(0, len(g) - len(back))))[:len(g)]
            g2b = rng.choice(levels)
            mix = g + back * 10 ** ((A.lufs(g) - g2b - A.lufs(back)) / 20)
            k = 10 ** ((lv["summary"]["eval_mix_lufs_median"] + rng.uniform(-3, 3) - A.lufs(mix)) / 20)
            g, mix = g * k, mix * k
            if t["mastered"]:
                mix = A.compress(mix, rng)
                if t["aac"]:
                    mix = A.aac(mix, rng, tmp)
            if t["separated"]:
                if sep is None:
                    from learn.separate import GuitarSeparator
                    sep = GuitarSeparator()
                stem = sep(mix.astype(np.float32)).astype(np.float64)
            else:
                stem = g
            ft = A.features(stem, mix)
            np.savez(f, featA=ft["A"][0], lufsA=ft["A"][1], featB=ft["B"][0], lufsB=ft["B"][1])
            print(t["i"], flush=True)


# --- predictions ------------------------------------------------------------------------------

def constant_settings(fold, amp, cls, menu_S):
    """The song-blind constant: per continuous setting the median (0–1 scale) of other folds' K_S
    optima for this amp and class; per switch and mic the most common value."""
    from collections import Counter

    opt = B.ks_optima()
    xs = [_settings(json.loads(pathlib.Path(p).read_text()))
          for f, rows in opt.items() if f != fold for a, c, p in rows if a == amp and c == cls]
    out = dict(menu_S)
    for d in K.space(amp, menu_S):
        k = (d.module, d.key)
        vals = [x[k] for x in xs if k in x]
        if not vals:
            continue
        if d.kind in ("cont", "log"):
            out[k] = K.fmt(d.from_unit(statistics.median(d.to_unit(v) for v in vals)))
        else:
            out[k] = Counter(vals).most_common(1)[0][0]
    return out


def bank_median(fold, amp, cls, S):
    """The median of the fold's training labels (the bank's examples outside `fold`) for this amp
    and class: per continuous setting on the 0–1 scale; per switch and mic the most common."""
    from collections import Counter

    ex = json.loads((B.OUT / "examples.json").read_text())
    labs = []
    for e in ex:
        if e["fold"] != fold and e["amp"] == amp and e["class"] == cls:
            f = B.OUT / "renders" / f"{e['i']:05d}.json"
            if f.exists():
                labs.append(json.loads(f.read_text())["label"])
    out = dict(S)
    for d in K.space(amp, S):
        vals = [lab[d.name] for lab in labs if d.name in lab]
        if not vals:
            continue
        if d.kind in ("cont", "log"):
            out[(d.module, d.key)] = K.fmt(d.from_unit(statistics.median(vals)))
        else:
            out[(d.module, d.key)] = Counter(vals).most_common(1)[0][0]
    return out


def predict_half():
    """The data-limit check's predictions: every step-3 cell from each fold's half-bank model
    (search half only, arm B's own prediction; no controls). Written to predictions-half.json."""
    import numpy as np

    from learn import song_model as M
    from learn import song_settings as SS

    fo = SS.folds()
    ps = K.parts()
    rr_menu = json.loads((OUT / "menu-S.json").read_text())
    nets = {f: M.load_net(f, half=True) for f in range(4)}
    ev = B.OUT.parent / "eval-features"
    out = {"control": {}, "cells": {}}
    for slug, amp, search, held in SS.cells():
        part = ps[slug]
        cls = part["gain_class"]
        S = _settings(rr_menu[amp][cls]["settings"])
        dz = np.load(ev / f"{slug}.npz")
        x, diag = M.predict_settings(nets[fo[part["band"]]], dz[f"feat{search}"], dz[f"lufs{search}"], amp, cls, S)
        out["cells"][f"{slug}|{amp}|{search}"] = {"B": {"settings": _settings_json(x), "diag": diag}}
    K._atomic(OUT / "predictions-half.json", out)
    print(len(out["cells"]), "cells (half bank)")


def predict():
    """Arm B's predictions (torch interpreter): the control targets, then every step-3 cell from
    the search half of the stem and mix, plus the shuffled-input, amp-track and constant
    controls. Written to predictions.json; nothing is rendered here."""
    import numpy as np

    from learn import song_model as M
    from learn import song_settings as SS

    fo = SS.folds()
    ps = K.parts()
    rr_menu = json.loads((OUT / "menu-S.json").read_text())        # amp -> class -> {select, settings}
    nets = {f: M.load_net(f) for f in range(4)}
    out = {"control": {}, "cells": {}}
    targets = json.loads((OUT / "control-targets.json").read_text())
    for t in targets:
        f = OUT / "control" / f"{t['i']:03d}-features.npz"
        if not f.exists():
            continue
        dz = np.load(f)
        S = _settings(rr_menu[t["amp"]][t["class"]]["settings"])
        res = {}
        for h in "AB":
            x, diag = M.predict_settings(nets[t["fold"]], dz[f"feat{h}"], dz[f"lufs{h}"], t["amp"], t["class"], S)
            res[h] = {"settings": _settings_json(x), "diag": diag}
        res["median"] = {"settings": _settings_json(bank_median(t["fold"], t["amp"], t["class"], S))}
        out["control"][str(t["i"])] = res
    ev = B.OUT.parent / "eval-features"
    ampf = B.OUT.parent / "eval-features-amp"
    rng = random.Random(SEED)
    for slug, amp, search, held in SS.cells():
        part = ps[slug]
        fold = fo[part["band"]]
        cls = part["gain_class"]
        S = _settings(rr_menu[amp][cls]["settings"])
        dz = np.load(ev / f"{slug}.npz")
        x, diag = M.predict_settings(nets[fold], dz[f"feat{search}"], dz[f"lufs{search}"], amp, cls, S)
        cell = {"B": {"settings": _settings_json(x), "diag": diag}}
        same = sorted(s for s in ps if s != slug and s != "telefunken-Honey-GTR"
                      and fo[ps[s]["band"]] == fold and ps[s]["band"] != part["band"])
        for j, other in enumerate(rng.sample(same, min(3, len(same)))):
            dzo = np.load(ev / f"{other}.npz")
            xo, _ = M.predict_settings(nets[fold], dzo[f"feat{search}"], dzo[f"lufs{search}"], amp, cls, S)
            cell[f"shuffled{j}"] = {"settings": _settings_json(xo), "source": other}
        if (ampf / f"{slug}.npz").exists():
            dza = np.load(ampf / f"{slug}.npz")
            xa, _ = M.predict_settings(nets[fold], dza[f"feat{search}"], dza[f"lufs{search}"], amp, cls, S)
            cell["amp_track"] = {"settings": _settings_json(xa)}
        cell["constant"] = {"settings": _settings_json(constant_settings(fold, amp, cls, S))}
        out["cells"][f"{slug}|{amp}|{search}"] = cell
    K._atomic(OUT / "predictions.json", out)
    print(len(out["control"]), "control;", len(out["cells"]), "cells")


def menu_S():
    """S's select and settings per amp and class (the renderer's interpreter), for `predict`."""
    rr = K.Renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    out = {amp: {cls: {"select": menu[amp][K.START[cls][amp]][0],
                       "settings": _settings_json(menu[amp][K.START[cls][amp]][1])} for cls in ("clean", "crunch")}
           for amp in K.AMPS}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "menu-S.json").write_text(json.dumps(out))


def amp_features():
    """The amp-track control's input: the part's reference amp track in place of the stem."""
    import numpy as np

    from learn import song_aug as A

    ps = K.parts()
    d = B.OUT.parent / "eval-features-amp"
    d.mkdir(parents=True, exist_ok=True)
    for slug in sorted(ps):
        if slug == "telefunken-Honey-GTR":
            continue
        f = A.features(CR.mono(ps[slug]["crop"] / "reference.wav"), B.eval_mix(slug))
        np.savez(d / f"{slug}.npz", featA=f["A"][0], lufsA=f["A"][1], featB=f["B"][0], lufsB=f["B"][1])


# --- scoring ----------------------------------------------------------------------------------

def score(shard, half=False):
    """Every prediction rendered through the measure DI and judged: the control targets against the
    clean planted render's held... both halves; step 3's cells on both halves of the reference."""
    import numpy as np
    import soundfile as sf

    pred = json.loads((OUT / ("predictions-half.json" if half else "predictions.json")).read_text())
    menu = json.loads((OUT / "menu-S.json").read_text())
    ps = K.parts()
    targets = {str(t["i"]): t for t in json.loads((OUT / "control-targets.json").read_text())}
    jobs = [("control", k) for k in sorted(pred["control"])] + [("cell", k) for k in sorted(pred["cells"])]
    rr = K.Renderer()
    d = OUT / ("scores-half" if half else "scores")
    d.mkdir(parents=True, exist_ok=True)
    try:
        for kind, key in jobs[shard[0]::shard[1]]:
            f = d / f"{kind}-{key.replace('|', '_')}.json"
            if f.exists():
                continue
            res = {}
            if kind == "control":
                t = targets[key]
                sel = menu[t["amp"]][t["class"]]["select"]
                di = np.load(OUT / "control" / f"{int(key):03d}-measure-di.npy")
                y, _ = sf.read(str(OUT / "control" / f"{int(key):03d}-clean.flac"), dtype="float64")
                ref = np.concatenate([np.zeros(int(B.TRIM_S * B.SR)), y])       # lag 0 against a render
                meta = json.loads((OUT / "control" / f"{int(key):03d}.json").read_text())
                S = menu[t["amp"]][t["class"]]["settings"]
                cands = {"target": meta["settings"], "S": S}
                for h in "AB":
                    cands[f"pred{h}"] = pred["control"][key][h]["settings"]
                cands["median"] = pred["control"][key]["median"]["settings"]
                for name, s in cands.items():
                    res[name] = K.judge(ref, rr.render(di, sel, _settings(s)), di.astype(np.float64), 0)
            else:
                slug, amp, search = key.split("|")
                part = ps[slug]
                sel = menu[amp][part["gain_class"]]["select"]
                di = K.measure_di(part)
                ref = CR.mono(part["crop"] / "reference.wav")
                for name, v in pred["cells"][key].items():
                    res[name] = K.judge(ref, rr.render(di.astype(np.float32), sel, _settings(v["settings"])), di,
                                        part["judge_lag"])
            K._atomic(f, res)
            print(kind, key, flush=True)
    finally:
        rr.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("control-draw", "control-render", "control-features", "menu-s", "amp-features",
                                     "predict", "predict-half", "score"))
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--half", action="store_true", help="score the half-bank predictions into scores-half/")
    a = ap.parse_args(argv)
    i, n = map(int, a.shard.split("/"))
    {"control-draw": control_draw, "control-render": control_render, "control-features": control_features,
     "menu-s": menu_S, "amp-features": amp_features, "predict": predict, "predict-half": predict_half,
     "score": lambda: score((i, n), a.half)}[a.step]()


if __name__ == "__main__":
    main()
