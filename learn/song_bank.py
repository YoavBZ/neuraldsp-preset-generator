"""Arm B's training-bank preparation (`docs/song-settings-plan.md`, arm B). CPU only, no renders.

    .venv/bin/python -m learn.song_bank windows    # DI windows by band and fold -> bank/windows.json
    .venv/bin/python -m learn.song_bank levels     # evaluation loudness and guitar-to-backing levels
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
DATASETS = HOME / "references/datasets"
DATA3 = HOME / "references/datasets-set3"
OUT = HOME / "learn/song-settings/bank"
SR = 48000
WIN_S, HOP_S, TRIM_S = 10.0, 5.0, 0.25
ACTIVE_SHARE = 0.6
GT = {"Guitar-TECHS P1": DATASETS / "guitar-techs/P1-downloads",
      "Guitar-TECHS P2": DATASETS / "guitar-techs/P2-downloads"}


def folds():
    return json.loads((PLUGIN_ROOT / "docs/song-settings-folds.json").read_text())["folds"]


def sources():
    """(band, fold, path) for every DI the bank may render from: the catalogue `di` file of every
    classed development part's session, and Guitar-TECHS P1 and P2 (fold "all"; P3 never)."""
    cat = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    classed = json.loads((PLUGIN_ROOT / "docs/label-table-parts.json").read_text())["classes_all"]
    fold_of = folds()
    out, seen = [], set()
    for s in cat["sessions"]:
        if s["split"] != "development":
            continue
        band = s.get("group") or f"{s['source']}/{s['song']}"
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_") for x in (s["source"], s["song"], p["part"]))
            if slug in classed and p.get("di"):
                f = DATASETS / s["path"] / p["di"]
                if f not in seen:
                    seen.add(f)
                    out.append((band, fold_of[band], f))
    s3 = json.loads((PLUGIN_ROOT / "docs/validation-set3.json").read_text())
    sessions = {x["key"]: x for x in s3["sessions"]}
    for p in s3["parts"]:
        if p["split"] != "development" or p["slug"] not in classed:
            continue
        di = next(d["di"] for d in sessions[p["session_key"]]["dis"] if d["part"] == p["part"])
        f = DATA3 / di
        if f not in seen:
            assert f.is_file(), f
            seen.add(f)
            out.append((p["band"], fold_of[p["band"]], f))
    for band, root in GT.items():
        for f in sorted(root.glob("*/audio/directinput/*.wav")):
            assert "P3" not in str(f)
            out.append((band, "all", f))
    return out


def track_windows(path):
    """Start frames (at 48 kHz) of 10.25-s windows whose last 10 s has the DI active in ≥ 60% of
    100-ms frames (within 40 dB of the track's loudest frame and above −60 dBFS)."""
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        g = np.gcd(SR, sr)
        x = resample_poly(x, SR // g, sr // g).astype(np.float32)
    fr = SR // 10
    n = len(x) // fr
    if n == 0:
        return []
    db = 10 * np.log10((x[:n * fr].reshape(n, fr) ** 2).mean(1) + 1e-20)
    active = (db >= db.max() - 40) & (db > -60)
    win, hop, trim = int(WIN_S * 10), int(HOP_S * 10), int(TRIM_S * 10)
    starts = []
    for i in range(0, n - win - trim + 1, hop):
        if active[i + trim:i + trim + win].mean() >= ACTIVE_SHARE:
            starts.append(i * fr)
    return starts


def windows():
    out = []
    for band, fold, f in sources():
        for st in track_windows(f):
            out.append({"band": band, "fold": fold, "path": str(f), "start": st})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "windows.json").write_text(json.dumps(out))
    from collections import Counter
    print(len(out), "windows from", len({w["path"] for w in out}), "tracks;", "per fold",
          dict(Counter(str(w["fold"]) for w in out)))


def eval_mix(slug):
    """The 10-s instrumental mix the stem was separated from: the crop's `mix_instrumental.wav`
    (sets 1–2), or the set-3 context's, cut at the crop."""
    import soundfile as sf

    crop = HOME / "references/validation-crops" / slug
    if (crop / "mix_instrumental.wav").exists():
        x, _ = sf.read(str(crop / "mix_instrumental.wav"), dtype="float64")
        return x
    ctx = json.loads((HOME / "learn/set3/stems/_work/contexts.json").read_text())[slug]
    x, _ = sf.read(str(HOME / "learn/set3/stems/_work/contexts" / slug / "mix_instrumental.wav"), dtype="float64")
    o = ctx["crop_offset_in_context"]
    return x[o:o + 480000]


def levels():
    """The evaluation inputs' loudness (step 3's stems and instrumental mixes) and the
    guitar-to-backing level of every classed development crop (reference against
    backing_instrumental, LUFS)."""
    import numpy as np
    import pyloudnorm
    import soundfile as sf

    from learn import knob_ceiling as K

    meter = pyloudnorm.Meter(SR)

    def lufs(path):
        x, sr = sf.read(str(path), dtype="float64", always_2d=True)
        assert sr == SR
        v = meter.integrated_loudness(x.mean(axis=1))
        return float(v) if np.isfinite(v) else None

    ps = K.parts()
    from learn import songs_check as SC
    sc = SC.parts()
    ev = {}
    for slug in ps:
        if slug == "telefunken-Honey-GTR":
            continue
        mix = eval_mix(slug)
        v = meter.integrated_loudness(mix)
        ev[slug] = {"stem": lufs(sc[slug]["stem"]), "mix_instrumental": float(v) if np.isfinite(v) else None}
    classed = json.loads((PLUGIN_ROOT / "docs/label-table-parts.json").read_text())["parts"]
    g2b = {}
    for slug, p in classed.items():
        crop = pathlib.Path(p["crop"])
        back = crop / "backing_instrumental.wav"
        back = back if back.exists() else crop / "backing.wav"
        if back.exists():
            a, b = lufs(crop / "reference.wav"), lufs(back)
            if a is not None and b is not None:
                g2b[slug] = a - b
    vals = sorted(g2b.values())
    doc = {"eval": ev, "guitar_to_backing_db": g2b,
           "summary": {"eval_stem_lufs_median": float(np.median([v["stem"] for v in ev.values() if v["stem"]])),
                       "eval_mix_lufs_median": float(np.median([v["mix_instrumental"] for v in ev.values()
                                                                if v["mix_instrumental"]])),
                       "g2b_quantiles": [round(vals[int(q * (len(vals) - 1))], 2) for q in (0, .1, .25, .5, .75, .9, 1)],
                       "g2b_n": len(vals)}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "levels.json").write_text(json.dumps(doc, indent=1))
    print(json.dumps(doc["summary"], indent=1))


# --- the bank: drawing and rendering ------------------------------------------------------------

N_BANK = 10000
SEED_BANK = 20261017
JITTER_SIGMA = 0.1
KEEP_MIC_P = 0.7


def backings():
    """(band, fold, path) of every classed development crop's instrumental backing."""
    fold_of = folds()
    out = []
    for slug, p in json.loads((PLUGIN_ROOT / "docs/label-table-parts.json").read_text())["parts"].items():
        crop = pathlib.Path(p["crop"])
        f = crop / "backing_instrumental.wav"
        f = f if f.exists() else crop / "backing.wav"
        if f.exists():
            out.append((p["band"], fold_of[p["band"]], str(f)))
    return out


def ks_optima():
    """fold -> [(amp, gain_class, settings path)] of knob ceiling's K_S bests."""
    from learn import knob_ceiling as K

    fold_of = folds()
    out = {}
    for p in sorted((K.OUT / "cells").glob("*/*/result.json")):
        c = json.loads(p.read_text())
        for search, _ in K.DIRECTIONS:
            f = p.parent / f"K_S-{search}.json"
            if "skipped" not in c["runs"][search] and f.exists():
                out.setdefault(fold_of[c["band"]], []).append((c["amp"], c["gain_class"], str(f)))
    return out


def draw():
    """The bank's examples, each with ONE fold: its DI window, backing, second guitar and jitter
    centre all come from that fold (a P1/P2 DI takes the example's drawn fold for the rest)."""
    import random

    rng = random.Random(SEED_BANK)
    win = json.loads((OUT / "windows.json").read_text())
    by_fold = {f: [w for w in win if str(w["fold"]) == str(f)] for f in range(4)}
    shared = [w for w in win if w["fold"] == "all"]
    back = backings()
    opt = ks_optima()
    from learn import knob_ceiling as K
    ex = []
    for i in range(N_BANK):
        fold = rng.randrange(4)
        w = rng.choice(by_fold[fold]) if rng.random() < 0.5 else rng.choice(shared)
        amp = rng.choice(K.AMPS)
        cls = rng.choice(("clean", "crunch"))
        mode = "broad" if i % 2 == 0 else "jitter"
        centre = None
        if mode == "jitter":
            cands = [o for o in opt.get(fold, []) if o[0] == amp and o[1] == cls]
            centre = rng.choice(cands)[2] if cands and rng.random() < 0.5 else "S"
        b = [x for x in back if x[1] == fold]
        ex.append({"i": i, "fold": fold, "window": w, "amp": amp, "class": cls, "mode": mode,
                   "centre": centre, "backing": rng.choice(b)[2] if b else None,
                   "second_guitar": rng.random() < 0.3, "mastered": rng.random() < 0.5,
                   "aac": rng.random() < 0.5, "separated": rng.random() < 0.5,
                   "seed": rng.randrange(2 ** 31)})
    (OUT / "examples.json").write_text(json.dumps(ex))
    from collections import Counter
    print(len(ex), dict(Counter(e["fold"] for e in ex)), dict(Counter(e["mode"] for e in ex)))


def settings_for(e, menu):
    """(select, settings, label) for an example: S for the amp and class, with the space's settings
    drawn broad (uniform) or jittered (σ 0.1 around S or a same-fold K_S optimum)."""
    import random

    from learn import knob_ceiling as K

    rng = random.Random(e["seed"])
    sel, S = menu[e["amp"]][K.START[e["class"]][e["amp"]]]
    centre = dict(S)
    if e["mode"] == "jitter" and e["centre"] not in (None, "S"):
        centre.update({tuple(k.rsplit("/", 1)): v for k, v in json.loads(pathlib.Path(e["centre"]).read_text()).items()})
    x, label = dict(S), {}
    for d in K.space(e["amp"], S):
        k = (d.module, d.key)
        if d.kind in ("cont", "log"):
            u = rng.random() if e["mode"] == "broad" else min(1.0, max(0.0, d.to_unit(centre.get(k, d.lo))
                                                                          + rng.gauss(0, JITTER_SIGMA)))
            x[k] = K.fmt(d.from_unit(u))
            label[d.name] = u
        else:
            if e["mode"] == "broad" or rng.random() > KEEP_MIC_P:
                v = rng.choice(d.values)
            else:
                v = centre.get(k, d.values[0])
            x[k] = v
            label[d.name] = v
    return sel, x, label


def load_window(w):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    info = sf.info(w["path"])
    n = int((WIN_S + TRIM_S) * info.samplerate)
    st = int(w["start"] * info.samplerate / SR)
    x, sr = sf.read(w["path"], start=st, frames=n, dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        g = np.gcd(SR, sr)
        x = resample_poly(x, SR // g, sr // g).astype(np.float32)
    return x


def measure(x):
    """The measure-DI treatment on an array: the average-guitar balance, then −22.9 LUFS."""
    import numpy as np

    from learn import confirm_run as CR
    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs

    avg = np.load(CR.AVERAGE)
    own = smoothed_spectrum(x.astype(np.float64))
    return to_lufs(eq_to(x.astype(np.float64), avg - (own - own.mean())))


def render(shard):
    import numpy as np
    import soundfile as sf

    from learn import knob_ceiling as K
    from learn import knob_ceiling2 as K2

    ex = json.loads((OUT / "examples.json").read_text())
    rr = K.Renderer()
    try:
        menu = rr.menu()
        d = OUT / "renders"
        d.mkdir(parents=True, exist_ok=True)
        for e in ex[shard[0]::shard[1]]:
            f = d / f"{e['i']:05d}.flac"
            if f.exists():
                continue
            if e["i"] % 50 == 0 and not K2.disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            sel, x, label = settings_for(e, menu)
            di = measure(load_window(e["window"])).astype(np.float32)
            y = np.asarray(rr.render(di, sel, x), np.float64)
            if y.ndim == 2:
                y = y.mean(axis=1)
            y = y[int(TRIM_S * SR):int((TRIM_S + WIN_S) * SR)]
            peak = max(np.abs(y).max(), 1e-12)
            sf.write(str(f), (y / peak * 0.99).astype(np.float32), SR, subtype="PCM_16")
            (d / f"{e['i']:05d}.json").write_text(json.dumps({"label": label, "peak": peak,
                                                              "settings": {f"{m}/{k}": v for (m, k), v in x.items()}}))
            if e["i"] % 100 == 0:
                print(e["i"], rr.count, flush=True)
    finally:
        rr.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("windows", "levels", "draw", "render"))
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    i, n = map(int, a.shard.split("/"))
    {"windows": windows, "levels": levels, "draw": draw, "render": lambda: render((i, n))}[a.step]()


if __name__ == "__main__":
    main()
