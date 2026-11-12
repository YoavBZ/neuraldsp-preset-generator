"""T1, the masking-channel render-and-compare test (`docs/full-controls-plan.md`, "T1 in detail"; ledger `pipeline-fix`
`phase_t1`; the cloud researcher's first test, `docs/research/effects-estimation.md`). Does comparing candidates through
the song's own masking read delay time on the stem, where F52's cepstrum fails? On F52's strong-third wide delay-ons: each
item's true preset with the delay time on a 13-point grid, rendered through a stock DI of its class, loudness-matched to
the song's stem, added to the song's residual (mix less stem) and re-separated by X-LANCE; the candidate whose stem's
cepstrum correlates best with the song stem's is the pick.

    .venv/bin/python -m learn.fx_t1 t1-draw                          # the items (zero renders)
    .venv/bin/python -m learn.fx_t1 t1-render --shard 0/3            # the candidates (renders)
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.fx_t1 t1-separate --device mps   # re-separation (MPS)
    .venv/bin/python -m learn.fx_t1 t1-read                          # the read (CPU)

The pure parts (the items, the stock DI choice, the grid, the pick, the arms' fits, the rule) are unit-tested.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time

PHASE = "phase_t1"
GRID = tuple(66.0 * (733.0 / 66.0) ** (j / 12) for j in range(13))   # ms, ratio about 1.222: each point its own +-10% cell
LAG_MS = (60.0, 800.0)                                                # F52's primary range
ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)                        # arm C's residual weights
BOOT_N, BOOT_SEED = 2000, 20261133
CHECK_OUT = ("Forkupines", "BKS")           # a pass must hold with either left out (the review: about 3.8 effective bands)
F52_HITS = 38                               # F52's primary arm on this third: 38 of 134 within 10% (28.4%); checked first
SR = 48000


def out_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "t1"


def e1e():
    return os.path.expanduser("~/ndsp-presets/learn/trusted-data/judge-v5/fx-reader/e1e")


# --- the pure parts -----------------------------------------------------------------------------------------------------

def strong_third(meta, labels, keep):
    """F52's strong third: the wide delay-ons kept by E1e's rebuild, whose delay mix is in their top third. labels: E1a's
    [n, cols] array (cols: ron, don, rmix, rdecay, dmix, dtime, dfb, spring). -> (indices, the wide delay-on indices)."""
    import numpy as np

    wide = np.array([m["mode"] == "wide" for m in meta]) & np.asarray(keep, bool)
    don = labels[:, 1] == 1
    dmix = labels[:, 4]
    on = np.where(wide & don)[0]
    hi = np.nanpercentile(dmix[on], 200 / 3)
    return [int(i) for i in on if dmix[i] >= hi], [int(i) for i in on]


def stock_for(song, cls, stock):
    """The class's first stock DI, unless it comes from the item's own song (then the second): a candidate never plays the
    song's own session."""
    ss = stock[cls]
    for s in ss:
        if song not in s["di"]:
            return s
    raise SystemExit(f"{song}: every {cls} stock DI is from its own song")


def with_delay_time(settings, ms):
    out = dict(settings)
    out["delay/delayTime"] = f"{ms:.6g}"
    return out


def pick(song_cep, cand_ceps):
    """The grid index whose candidate cepstrum (over the lag range) correlates best with the song stem's."""
    import numpy as np

    a = song_cep - song_cep.mean()
    best, bi = -2.0, 0
    for j, c in enumerate(cand_ceps):
        b = c - c.mean()
        r = float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-12))
        if r > best:
            best, bi = r, j
    return bi


def within10(pred_ms, true_ms):
    return abs(pred_ms / true_ms - 1) <= 0.10


def rule(a_vs_f52, a_vs_prior):
    """The declared pass bar: arm A beats F52's cepstrum on within-10% (interval wholly above 0) and its log2 error
    beats the draw-aware prior's (interval wholly below 0); and both points stay on that side with each of CHECK_OUT's
    bands left out. Each argument: {"ci": [lo, hi], "without <band>": value}."""
    f, p = a_vs_f52, a_vs_prior
    return bool(f["ci"][0] is not None and f["ci"][0] > 0 and p["ci"][1] is not None and p["ci"][1] < 0
                and all(f[f"without {c}"] > 0 and p[f"without {c}"] < 0 for c in CHECK_OUT))


def boot(fn, bands, n=BOOT_N, seed=BOOT_SEED):
    import numpy as np

    rng = np.random.default_rng(seed)
    u = sorted(set(bands))
    bands = np.asarray(bands)
    v = []
    for _ in range(n):
        idx = np.concatenate([np.where(bands == u[j])[0] for j in rng.integers(0, len(u), len(u))])
        x = fn(idx)
        if x == x:
            v.append(x)
    return [float(np.percentile(v, 5)), float(np.percentile(v, 95))] if v else [None, None]


# --- the commands -------------------------------------------------------------------------------------------------------

def lag_slice():
    lo, hi = int(LAG_MS[0] * SR / 1000), int(LAG_MS[1] * SR / 1000)
    return slice(lo, hi + 1)


def item_dir():
    return out_dir() / "items"


def cmd_draw(_args):
    import glob

    import numpy as np

    from learn import amp_di_compare as A1
    from learn import fx_reader as FX
    from learn import pipeline_fix as P

    P.require(PHASE)
    p = out_dir() / "plan.json"
    if p.exists():
        raise SystemExit(f"{p} exists: drawn once")
    meta = json.loads((FX.E1A / "meta.json").read_text())["examples"]
    L = np.load(FX.E1A / "labels.npy")
    rows = {json.loads(x)["i"]: json.loads(x) for x in open(os.path.join(e1e(), "build-rows.jsonl"))}
    keep = [rows.get(m["i"], {}).get("mix_features_identical", False) for m in meta]
    strong, ons = strong_third(meta, L, keep)
    ids = {meta[j]["i"] for j in strong}
    cc = os.path.expanduser("~/ndsp-presets/learn/trusted-data/cc")
    st = {}
    for f in sorted(glob.glob(os.path.join(cc, "rows", "render-*.jsonl"))):
        for line in open(f):
            r = json.loads(line)
            if r["i"] in ids:
                st[r["i"]] = r["settings"]
    from learn import local_objective as LO
    from learn import trusted_data_t3 as T3

    stock = json.loads((A1.a1_dir() / "plan.json").read_text())["stock"]
    menus = T3.Menus()
    menus.gate_u = json.loads(open(os.path.join(cc, "plan.json")).read())["gate_cap"]["unit"]   # as cc_build's render
    items = []
    for j in strong:
        m = meta[j]
        amp, _, base, sel, xf, _, _, _ = T3.full_twin(m["i"], menus)    # D_CC's own render: the item's select and setting
        if amp != m["amp"] or base != m["base"] or LO.sdict(xf) != st[m["i"]]:
            raise SystemExit(f"{m['i']}: the full twin differs from the stored render's settings")
        s = stock_for(m["song"], m["base"], stock)
        items.append({"j": j, "i": m["i"], "song": m["song"], "band": m["band"], "amp": m["amp"], "cls": m["base"],
                      "select": sel, "true_ms": float(st[m["i"]]["delay/delayTime"]), "settings": st[m["i"]],
                      "stock": {"di": s["di"], "di_path": s["di_path"], "start_s": s["start_s"]}})
    out_dir().mkdir(parents=True, exist_ok=True)
    P.save(p, {"phase": PHASE, "grid_ms": GRID, "items": items, "wide_delay_ons": [meta[j]["i"] for j in ons],
               "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"T1 DRAW: {len(items)} strong-third delay-ons of {len(ons)}; {len(items) * len(GRID)} candidates")


def cmd_render(args):
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(PHASE)
    plan = json.loads((out_dir() / "plan.json").read_text())
    k, n = args.shard
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    item_dir().mkdir(parents=True, exist_ok=True)
    renders, dis = 0, {}
    for it in plan["items"][k::n]:
        out = item_dir() / f"{it['i']:07d}-cand.npz"
        if out.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        key = it["stock"]["di"]
        if key not in dis:
            dis[key] = B.measure(PS.section_audio(it["stock"]["di_path"], it["stock"]["start_s"])).astype(np.float32)
        sel = it["select"]                            # the item's own select (D_CC's full twin), checked at the draw
        cands = []
        for t in plan["grid_ms"]:
            st = LO.tdict(with_delay_time(it["settings"], t))
            y = np.asarray(AM.fresh_render(CB.new_renderer, dis[key], sel, st, st), np.float64)[trim[0]:trim[1]]
            renders += 2
            cands.append((np.mean(y, 1) if y.ndim == 2 else y).astype(np.float32))
        tmp = out.with_suffix(".tmp.npz")
        np.savez(tmp, cand=np.stack(cands))
        tmp.replace(out)                              # the resume marker
        print(f"{it['cls']}: renders so far {renders}", flush=True)
    print(f"T1 RENDER DONE {k}/{n}: {renders} renders", flush=True)


def cmd_separate(args):
    """Per item, once its candidates exist: the residual (mix less stem); each candidate loudness-matched to the song's
    stem, added to the residual and re-separated (arm A), and the candidate itself (arm B); every cepstrum over the lag
    range -> items/<i>-cep.npz. Waits for the renders (polls every 60 s) so the two overlap."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import fx_reader as FX
    from learn import song_aug as SA
    from learn import trusted_data as T

    plan = json.loads((out_dir() / "plan.json").read_text())
    sep = DS.stem_separator(T.SEP, args.device)
    ls = lag_slice()
    todo = [it for it in plan["items"] if not (item_dir() / f"{it['i']:07d}-cep.npz").exists()]
    t0, done = time.time(), 0
    while todo:
        ready = [it for it in todo if (item_dir() / f"{it['i']:07d}-cand.npz").exists()]
        if not ready:
            time.sleep(60)
            continue
        for it in ready:
            z = np.load(os.path.join(e1e(), "audio", f"{it['i']:07d}.npz"))
            mix, stem = np.asarray(z["mix"], np.float64), np.asarray(z["stem"], np.float64)
            res = mix - stem
            lu = SA.lufs(stem)
            cand = np.load(item_dir() / f"{it['i']:07d}-cand.npz")["cand"].astype(np.float64)
            A, Bc = [], []
            for c in cand:
                c = c[: len(res)] if len(c) >= len(res) else np.pad(c, (0, len(res) - len(c)))
                c = c * 10 ** ((lu - SA.lufs(c)) / 20)
                s_ = np.asarray(sep(c + res), np.float64)
                if len(s_) != len(res) or not np.isfinite(s_).all():
                    raise SystemExit(f"{it['i']}: bad re-separated stem")
                A.append(FX.cepstrum(s_)[ls])
                Bc.append(FX.cepstrum(c)[ls])
            np.savez(item_dir() / f"{it['i']:07d}-cep.npz", A=np.array(A, np.float32), B=np.array(Bc, np.float32),
                     stem=FX.cepstrum(stem)[ls].astype(np.float32), res=FX.cepstrum(res)[ls].astype(np.float32))
            done += 1
            print(f"t1 separate {done}/{len(plan['items'])}: {(time.time() - t0) / done:.1f} s an item", flush=True)
        todo = [it for it in todo if not (item_dir() / f"{it['i']:07d}-cep.npz").exists()]
    print("T1 SEPARATE DONE", flush=True)


def cmd_read(_args):
    import numpy as np

    from learn import fx_reader as FX
    from learn import pipeline_fix as P

    P.require(PHASE)
    plan = json.loads((out_dir() / "plan.json").read_text())
    grid = np.array(plan["grid_ms"])
    ls = lag_slice()
    lo = ls.start
    items = plan["items"]
    meta = json.loads((FX.E1A / "meta.json").read_text())["examples"]
    by_i = {m["i"]: m for m in meta}
    L = np.load(FX.E1A / "labels.npy")
    jof = {m["i"]: j for j, m in enumerate(meta)}
    # F52's primary arm (the stem's cepstrum less the other songs' mean wide delay-off stem cepstrum), recomputed
    kept = {json.loads(x)["i"] for x in open(os.path.join(e1e(), "build-rows.jsonl"))
            if json.loads(x).get("mix_features_identical")}
    wide = [m for m in meta if m["mode"] == "wide" and m["i"] in kept]        # F52's set: the rebuilds that matched
    C, R = {}, {}
    for m in wide:
        z = np.load(os.path.join(e1e(), "audio", f"{m['i']:07d}.npz"))
        C[m["i"]] = FX.cepstrum(z["stem"])
        R[m["i"]] = FX.cepstrum(np.asarray(z["mix"], np.float64) - np.asarray(z["stem"], np.float64))
    don = {m["i"]: L[jof[m["i"]], 1] == 1 for m in wide}
    off_mean = {s: np.mean([C[m["i"]] for m in wide if m["song"] != s and not don[m["i"]]], axis=0)
                for s in sorted({m["song"] for m in wide})}

    def ms_of(c, rng=FX.CEP_RANGE):
        return FX.cep_pick(c, rng)[0]

    f52 = {it["i"]: ms_of(C[it["i"]] - off_mean[it["song"]]) for it in items}
    # arm C, the free arm: the stem's cepstrum less alpha times the residual's, alpha fitted leaving the band out
    ons = [i for i in plan["wide_delay_ons"] if i in C]
    true = {i: 2 ** float(L[jof[i], 5]) for i in ons}
    bands_on = {i: by_i[i]["band"] for i in ons}

    def hit_rate(alpha, ids):
        return np.mean([within10(ms_of(C[i] - alpha * R[i]), true[i]) for i in ids]) if ids else float("nan")

    armc = {}
    for b in sorted(set(bands_on.values())):
        tr = [i for i in ons if bands_on[i] != b]
        a_best = max(ALPHAS, key=lambda a: hit_rate(a, tr))
        for i in ons:
            if bands_on[i] == b:
                armc[i] = (ms_of(C[i] - a_best * R[i]), a_best)
    # arms A and B
    pa, pb = {}, {}
    for it in items:
        z = np.load(item_dir() / f"{it['i']:07d}-cep.npz")
        pa[it["i"]] = float(grid[pick(z["stem"], z["A"])])
        pb[it["i"]] = float(grid[pick(z["stem"], z["B"])])
    bands = np.array([it["band"] for it in items])
    tm = np.array([it["true_ms"] for it in items])
    prior = np.array([np.median([true[i] for i in ons if bands_on[i] != it["band"]]) for it in items])
    P_ = {"A": np.array([pa[it["i"]] for it in items]), "B": np.array([pb[it["i"]] for it in items]),
          "C": np.array([armc[it["i"]][0] for it in items]), "F52": np.array([f52[it["i"]] for it in items]),
          "prior": prior}
    hit = {k: np.array([within10(p, t) for p, t in zip(v, tm)], float) for k, v in P_.items()}
    lerr = {k: np.abs(np.log2(v) - np.log2(tm)) for k, v in P_.items()}
    if int(hit["F52"].sum()) != F52_HITS or len(items) != 134:
        raise SystemExit(f"F52's recomputed arm hits {int(hit['F52'].sum())} of {len(items)}, not {F52_HITS} of 134: "
                         "the comparator is off, no read")

    def paired(a, b):
        out = {"diff": float(a.mean() - b.mean()), "ci": boot(lambda x: float(a[x].mean() - b[x].mean()), bands)}
        for c in CHECK_OUT:
            m = bands != c
            out[f"without {c}"] = float(a[m].mean() - b[m].mean())
        return out
    ceiling = float(np.mean([any(within10(g, t) for g in grid) for t in tm]))
    dr = np.array(["DarkRide" in it["stock"]["di"] for it in items])
    rep = {"phase": PHASE, "n": len(items), "bands": {b: int((bands == b).sum()) for b in sorted(set(bands))},
           "within_10pct": {k: float(v.mean()) for k, v in hit.items()},
           "log2_mae": {k: float(v.mean()) for k, v in lerr.items()},
           "A - F52, within 10%": paired(hit["A"], hit["F52"]),
           "A - prior, log2 error": paired(lerr["A"], lerr["prior"]),
           "A - B, within 10% (the channel)": paired(hit["A"], hit["B"]),
           "grid ceiling (a perfect cell pick within 10%)": ceiling,
           "Dark Ride 29 items apart": {"n": int(dr.sum()), **{k: float(v[dr].mean()) for k, v in hit.items() if dr.any()}},
           "C on all wide delay-ons": {"n": len(ons), "within_10pct": float(np.mean([within10(armc[i][0], true[i]) for i in ons])),
                                       "alphas": sorted({a for _, a in armc.values()})},
           "per_item": [{"i": it["i"], "band": it["band"], "true_ms": it["true_ms"], **{k: float(v[j]) for k, v in P_.items()}}
                        for j, it in enumerate(items)]}
    rep["passes"] = rule(rep["A - F52, within 10%"], rep["A - prior, log2 error"])
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(out_dir() / "read.json", rep)
    print(json.dumps({k: v for k, v in rep.items() if k != "per_item"}, indent=1))


def shard(s):
    a, b = s.split("/")
    return int(a), int(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("t1-draw").set_defaults(fn=cmd_draw)
    r = sub.add_parser("t1-render")
    r.add_argument("--shard", type=shard, default=(0, 1))
    r.set_defaults(fn=cmd_render)
    s = sub.add_parser("t1-separate")
    s.add_argument("--device", default="mps")
    s.set_defaults(fn=cmd_separate)
    sub.add_parser("t1-read").set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
