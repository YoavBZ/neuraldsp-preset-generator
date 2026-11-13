"""T0x, T0 at the product's exposure (`docs/full-controls-plan.md`, "T0x in detail"; ledger `pipeline-fix` `phase_t0x`):
zero renders. F87 found the stems keep an audible delay about twice as often with the guitar exposed. T0x rebuilds all
of E1e's 770 wide draws by D_CC's own recipe with only the guitar-to-backing ratio set to -3 dB, separates each by
X-LANCE, and reruns T0's declared read on the new stems (the same features, library, matching, strong third, prior,
large-band checks and rule), with the direct delay-time reader (the stem's own cepstral peak) beside on every delay-on.

    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.fx_t0x t0x-build --device mps   # rebuild + separate + features
    .venv/bin/python -m learn.fx_t0x t0x-read                                          # T0's read on the new stems
"""

from __future__ import annotations

import argparse
import json
import os
import time

PHASE = "phase_t0x"
RATIO_DB = -3.0


def out_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "t0x"


def cmd_build(args):
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import fx_reader as FX
    from learn import fx_t0 as T0
    from learn import fx_t1x as T1X
    from learn import pipeline_fix as P
    from learn import trusted_data as T

    P.require(PHASE)
    its, _ = T0.items()
    ns = argparse.Namespace(out=None, smoke=False)
    root = CB.V.out_root(ns)
    plan = {x["i"]: x for x in CB.load_plan(ns)["examples"]}
    rend = T.rows_of(root, CB.STAGE, "render")
    stems = T.Stems(CB.ctx_for(ns))
    sep = DS.stem_separator(T.SEP, args.device)
    d = out_dir() / "items"
    d.mkdir(parents=True, exist_ok=True)
    e1e = os.path.join(T0.root(), "e1e", "audio")
    t0 = time.time()
    for m, it in enumerate(its):
        p = d / f"{it['i']:07d}.json"
        if p.exists():
            continue
        x, rw = plan[it["i"]], rend[it["i"]]
        y = G.read_flac(T.flac_path(root, CB.STAGE, it["i"], "target"), rw["target"]["scale"], rw["target"]["sha256"])
        oth = G.read_flac(T.flac_path(root, CB.STAGE, it["i"], "others"), rw["others_file"]["scale"],
                          rw["others_file"]["sha256"])
        voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
        st = stems.get(x["section"], T.backing_tracks(x, voc))
        y, oth = np.asarray(y, np.float64), np.asarray(oth, np.float64)
        same, _, _ = T.self_built_mix(y, oth, st, x)              # the recipe check, as T1x's
        if not np.allclose(same.astype(np.float32), np.load(os.path.join(e1e, f"{it['i']:07d}.npz"))["mix"], atol=1e-5):
            raise SystemExit(f"{it['i']}: the rebuild at the drawn ratio differs from E1e's stored mix")
        mix, _, _ = T.self_built_mix(y, oth, st, T1X.with_ratio(x, RATIO_DB))
        s_ = np.asarray(sep(mix), np.float64)
        if len(s_) != len(mix) or not np.isfinite(s_).all():
            raise SystemExit(f"{it['i']}: bad stem")
        P.save(p, {"i": it["i"], "stem": T0.features(s_), "mix": T0.features(mix),
                   "stem_cep_peak_ms": FX.cep_pick(FX.cepstrum(s_))[0], "drawn_ratio_db": x["draw"]["ratio_db"]})
        if m % 25 == 0:
            print(f"t0x {m + 1}/{len(its)}: {(time.time() - t0) / (m + 1):.1f} s an item", flush=True)
    print("T0X BUILD DONE", flush=True)


def cmd_read(_args):
    import numpy as np

    from learn import fx_t0 as T0
    from learn import pipeline_fix as P

    P.require(PHASE)
    its, _ = T0.items()
    z = np.load(T0.out_dir() / "features.npz")                  # T0's own: the library (clean targets) and as-drawn arms
    if [it["i"] for it in its] != list(z["i"]):
        raise SystemExit("the items differ from T0's features")
    recs = [json.loads((out_dir() / "items" / f"{it['i']:07d}.json").read_text()) for it in its]
    X = {"stem": np.array([r["stem"] for r in recs]), "mix": np.array([r["mix"] for r in recs])}
    L = [T0.labels(it["settings"]) for it in its]
    Y = {c: np.array([l_[c] for l_ in L]) for c in L[0]}
    bands = np.array([it["band"] for it in its])
    amps = np.array([it["amp"] for it in its])
    lib = z["target"]
    off = (Y["ron"] == 0) & (Y["don"] == 0) & (Y["ton"] == 0)
    rep = {"phase": PHASE, "ratio_db": RATIO_DB, "n": len(its), "arms": {}, "negative_control": {}}
    for a in ("stem", "mix"):
        own = {eff: T0.predict(eff, lib, X[a], Y, bands, amps, T0.OWN[eff]) for eff in T0.EFFECTS}
        rep["arms"][a] = {eff: T0.read_effect(eff, *own[eff], Y, bands) for eff in T0.EFFECTS}
        rep["negative_control"][a] = T0.false_on({e: own[e][0] for e in T0.EFFECTS}, Y, off)
    t0r = json.loads((T0.out_dir() / "read.json").read_text())
    rep["passes"] = {"target (T0's)": t0r["passes"]["target"], "stem at -3 dB": T0.passes(rep["arms"]["stem"])}
    rep["rule"] = T0.rule(rep["passes"]["target (T0's)"], rep["passes"]["stem at -3 dB"])
    # beside: the direct delay-time reader (the stem's own cepstral peak) on every delay-on, and on the strong third
    don = Y["don"] == 1
    hi = np.nanpercentile(Y["dmix"][don], 200 / 3)
    t = 2 ** Y["dtime"]
    pk = np.array([r["stem_cep_peak_ms"] for r in recs])
    prior = np.array([np.nanmedian(Y["dtime"][(bands != b) & don]) for b in bands])
    for nm, m in (("all delay-ons", don), ("strong third", don & (Y["dmix"] >= hi))):
        hit = (np.abs(pk / t - 1) <= 0.10).astype(float)
        le, lp = np.abs(np.log2(pk) - Y["dtime"]), np.abs(prior - Y["dtime"])
        rep.setdefault("direct delay-time reader", {})[nm] = {
            "n": int(m.sum()), "within_10pct": float(hit[m].mean()),
            "log2 error - prior": T0._stats(lambda b, le=le, lp=lp, m=m: float(np.mean(le[b][m[b]]) - np.mean(lp[b][m[b]])),
                                            bands)}
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(out_dir() / "read.json", rep)
    print(json.dumps({k: rep[k] for k in ("passes", "rule", "negative_control", "direct delay-time reader")}, indent=1,
                     default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("t0x-build")
    b.add_argument("--device", default="mps")
    b.set_defaults(fn=cmd_build)
    sub.add_parser("t0x-read").set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
