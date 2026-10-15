"""Settings from a song (`docs/song-settings-plan.md`, ML plan step 3). Development only.

    .venv/bin/python -m learn.song_settings ks-convergence     # zero renders: K_S at 25/50/100/150
    $TORCH_PY -m learn.song_settings rebuild                   # C′ per fold, re-equalised (torch)
    .venv/bin/python -m learn.song_settings menu-pick --shard 0/4
    .venv/bin/python -m learn.song_settings arm-a --shard 0/4
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

from learn import confirm_run as CR  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402

OUT = K.HOME / "learn/song-settings"
CHECKPOINTS = (25, 50, 100, 150)


def per_part(rows):
    """rows: (slug, band, gain_class, value) per cell and direction -> (band, gain_class, mean)."""
    by = {}
    for slug, band, cls, v in rows:
        by.setdefault((slug, band, cls), []).append(v)
    return [(b, c, statistics.fmean(v)) for (s, b, c), v in by.items()]


def ks_convergence():
    rows = {n: [] for n in CHECKPOINTS}
    for p in sorted((K.OUT / "cells").glob("*/*/result.json")):
        c = json.loads(p.read_text())
        for search, held in K.DIRECTIONS:
            run = c["runs"][search]
            if "skipped" in run:
                continue
            s_held = c["menu"][c["start"]][held]
            curve = run["K_S"]["curve"]
            for n in CHECKPOINTS:
                kh = curve[min(n, len(curve)) - 1][2]
                if math.isfinite(kh) and math.isfinite(s_held):
                    rows[n].append((c["slug"], c["band"], c["gain_class"], math.log(kh / s_held)))
    out = {}
    for n, r in rows.items():
        pp = per_part(r)
        out[n] = {g: CR.stats([(b, v) for b, c, v in pp if c in keep])
                  for g, keep in (("clean+crunch", ("clean", "crunch")), ("clean", ("clean",)), ("crunch", ("crunch",)))}
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "ks-convergence.json", out)
    for n, g in out.items():
        s = g["clean+crunch"]
        print(f"K_S@{n:3d} vs S: band-w {s['band_weighted_mean']:+.3f} part-w {s['mean']:+.3f} "
              f"90% [{s['lo90']:+.3f}, {s['hi90']:+.3f}] bands- {s['bands_negative']}/{s['bands']}")


# --- arm A: rebuilt-DI search ------------------------------------------------------------------

SEED_A = 20261013
BUDGET_A = 150
MODELS = K.HOME / "learn/direc"


def folds():
    return json.loads((PLUGIN_ROOT / "docs/song-settings-folds.json").read_text())["folds"]


def cells():
    """(slug, amp, search, held) for every step-3 cell (Honey excluded)."""
    ps = K.parts()
    return [(s, a, sh, h) for s in sorted(ps) if s != "telefunken-Honey-GTR"
            for a in K.AMPS for sh, h in K.DIRECTIONS]


def stem(slug):
    from learn import songs_check as SC

    return CR.mono(SC.parts()[slug]["stem"])


def cprime(fold):
    return MODELS / ("models-cprime/fold2.pt" if fold == 2 else f"models-cprime-f{fold}/fold{fold}.pt")


def rebuild_all():
    """Each part's stem rebuilt by its fold's C′, re-equalised by (fold 2's average − fold f's),
    at −22.9 LUFS, saved to rebuilt/<part>.npy (the torch interpreter)."""
    import numpy as np
    import torch

    from learn import direc as D
    from learn.direc_check import eq_to, to_lufs

    fo = folds()
    ps = K.parts()
    avg = {f: np.load(MODELS / "cache" / f"average-fold{f}.npy") for f in range(4)}
    nets = {}
    (OUT / "rebuilt").mkdir(parents=True, exist_ok=True)
    for slug in sorted(ps):
        if slug == "telefunken-Honey-GTR":
            continue
        f = fo[ps[slug]["band"]]
        if f not in nets:
            nets[f] = D.load_model(cprime(f)).eval()
        x = D.rebuild(nets[f], stem(slug).astype(np.float32), device=torch.device("cpu")).astype(np.float64)
        x = to_lufs(eq_to(x, avg[2] - avg[f]))
        np.save(OUT / "rebuilt" / f"{slug}.npy", x)
        print(slug, "fold", f, flush=True)


def rebuilt_objective(stem_x, y, rebuilt, half, counter):
    from learn.rebuilt_judge import rebuilt_distance

    a, b = K.R.HALVES[half]
    d, proxy = rebuilt_distance(stem_x, y, rebuilt, start_s=a, end_s=b)
    counter["fallback"] += int(proxy)
    return math.inf if d.distance is None else d.distance


def arm_a(shard):
    """`knob_search` from S, 150 renders per direction, objective `rebuilt_distance` on the search
    half; the best rendered once through the measure DI and judged on both halves."""
    import numpy as np

    ps = K.parts()
    rr = K.Renderer()
    try:
        menu = rr.menu()
        cur = None
        for slug, amp, search, held in cells()[shard[0]::shard[1]]:
            d = OUT / "armA" / slug / amp
            if (d / f"{search}.json").exists():
                continue
            part = ps[slug]
            if cur != slug:
                rebuilt = np.load(OUT / "rebuilt" / f"{slug}.npy")
                stem_x = stem(slug)
                di = K.measure_di(part)
                ref = CR.mono(part["crop"] / "reference.wav")
                cur = slug
            start_name = K.START[part["gain_class"]][amp]
            sel, S = menu[amp][start_name]
            r32 = rebuilt.astype(np.float32)
            counter = {"fallback": 0}
            curve = []

            def f(x):
                v = rebuilt_objective(stem_x, rr.render(r32, sel, x), rebuilt, search, counter)
                curve.append(v)
                return v

            rr.render(r32, sel, S)                                          # warm-up
            x, best, _, stages = K.knob_search(K.space(amp, S), S, f, BUDGET_A, SEED_A)
            j = K.judge(ref, rr.render(di.astype(np.float32), sel, x), di, part["judge_lag"])
            res = {"slug": slug, "amp": amp, "search_half": search, "held_half": held, "band": part["band"],
                   "gain_class": part["gain_class"], "fold": folds()[part["band"]], "start": start_name,
                   "objective_best": best, "objective_curve": curve, "renders": len(curve),
                   "fallback": counter["fallback"], "judge": j, "stages": stages}
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{search}-settings.json").write_text(json.dumps({f"{m}/{k}": v for (m, k), v in x.items()}))
            K._atomic(d / f"{search}.json", res)
            print(slug, amp, search, round(j[held], 4), rr.count, flush=True)
    finally:
        rr.close()


def menu_pick(shard):
    """C′'s menu pick per amp: every menu preset through the rebuilt DI, `rebuilt_distance` on the
    search half; the pick's held score comes from step 4's stored menu (the same measure DI)."""
    import numpy as np

    ps = K.parts()
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for slug in sorted(s for s in ps if s != "telefunken-Honey-GTR")[shard[0]::shard[1]]:
            d = OUT / "menupick" / slug
            if (d / "result.json").exists():
                continue
            rebuilt = np.load(OUT / "rebuilt" / f"{slug}.npy")
            stem_x = stem(slug)
            r32 = rebuilt.astype(np.float32)
            res = {}
            for amp, m in menu.items():
                rr.render(r32, *next(iter(m.values())))
                counter = {"fallback": 0}
                scores = {}
                for name, (sel, ed) in m.items():
                    y = rr.render(r32, sel, ed)
                    scores[name] = {h: rebuilt_objective(stem_x, y, rebuilt, h, counter) for h in "AB"}
                res[amp] = {"scores": scores, "fallback": counter["fallback"],
                            "pick": {h: min(scores, key=lambda n: scores[n][h]) for h in "AB"}}
            d.mkdir(parents=True, exist_ok=True)
            K._atomic(d / "result.json", res)
            print(slug, {a: r["pick"] for a, r in res.items()}, rr.count, flush=True)
    finally:
        rr.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("ks-convergence", "rebuild", "arm-a", "menu-pick"))
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    i, n = map(int, a.shard.split("/"))
    {"ks-convergence": ks_convergence, "rebuild": rebuild_all, "arm-a": lambda: arm_a((i, n)),
     "menu-pick": lambda: menu_pick((i, n))}[a.step]()


if __name__ == "__main__":
    main()
