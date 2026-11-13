"""T1x, the exposure test (`docs/full-controls-plan.md`, "T1x in detail"; ledger `pipeline-fix` `phase_t1x`): zero renders.
F86 found the songs' stems lose their delay to the backing's masking at the draws' dense levels (the guitar a median 9 dB
under the backing). T1x rebuilds T1's 134 strong-third mixes by D_CC's own recipe (`trusted_data.self_built_mix`: the
stored target, the stored other guitars, the section's stems, the drawn leak, loudness and mastering) with only the
guitar-to-backing ratio changed, to -3 dB and to 0 dB, separates each by X-LANCE, and reads whether the stem's cepstrum
then peaks at the true delay; beside, T1's correlation pick and a peak-position pick on T1's clean candidates (arm B's
stored cepstra) against the new stems, with zero extra separations.

    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.fx_t1x t1x-build --device mps   # rebuild + separate (MPS)
    .venv/bin/python -m learn.fx_t1x t1x-read                                          # the read (CPU)
"""

from __future__ import annotations

import argparse
import json
import os
import time

PHASE = "phase_t1x"
RATIOS = (-3.0, 0.0)                         # dB, the guitar against the backing: exposed, as the product's scope
BOOT_N, BOOT_SEED = 2000, 20261136


def out_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "t1x"


def with_ratio(x, r):
    """A copy of a D_CC example with its drawn ratio replaced (every other draw kept)."""
    return {**x, "draw": {**x["draw"], "ratio_db": float(r)}}


def hit(ms, true_ms):
    return abs(ms / true_ms - 1) <= 0.10


def cmd_build(args):
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import fx_reader as FX
    from learn import fx_t1 as T1
    from learn import pipeline_fix as P
    from learn import trusted_data as T

    P.require(PHASE)
    t1 = json.loads((T1.out_dir() / "plan.json").read_text())
    ns = argparse.Namespace(out=None, smoke=False)
    root = CB.V.out_root(ns)
    plan = {x["i"]: x for x in CB.load_plan(ns)["examples"]}
    rend = T.rows_of(root, CB.STAGE, "render")
    stems = T.Stems(CB.ctx_for(ns))
    sep = DS.stem_separator(T.SEP, args.device)
    d = out_dir() / "items"
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for m, it in enumerate(t1["items"]):
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
        same, _, _ = T.self_built_mix(y, oth, st, x)                   # the recipe check: the drawn ratio rebuilds E1e's mix
        stored = np.load(os.path.join(T1.e1e(), "audio", f"{it['i']:07d}.npz"))["mix"]
        if not np.allclose(same.astype(np.float32), stored, atol=1e-5):
            raise SystemExit(f"{it['i']}: the rebuild at the drawn ratio differs from E1e's stored mix")
        rec = {"i": it["i"], "true_ms": it["true_ms"], "band": it["band"], "drawn_ratio_db": x["draw"]["ratio_db"],
               "mastered": x["draw"]["mastered"], "stem_peak_ms": {}}
        ceps = {}
        for r in RATIOS:
            mix, _, _ = T.self_built_mix(y, oth, st, with_ratio(x, r))
            s_ = np.asarray(sep(mix), np.float64)
            if len(s_) != len(mix) or not np.isfinite(s_).all():
                raise SystemExit(f"{it['i']}: bad stem")
            c = FX.cepstrum(s_)
            rec["stem_peak_ms"][f"{r:+.0f}"] = FX.cep_pick(c)[0]
            ceps[f"{r:+.0f}"] = c[T1.lag_slice()].astype(np.float32)
        np.savez(d / f"{it['i']:07d}-cep.npz", **ceps)
        P.save(p, rec)
        if m % 10 == 0:
            print(f"t1x {m + 1}/{len(t1['items'])}: {(time.time() - t0) / (m + 1):.1f} s an item", flush=True)
    print("T1X BUILD DONE", flush=True)


def cmd_read(_args):
    import numpy as np

    from learn import fx_reader as FX
    from learn import fx_t1 as T1
    from learn import pipeline_fix as P

    P.require(PHASE)
    t1 = json.loads((T1.out_dir() / "plan.json").read_text())
    e1e = T1.e1e()
    recs = [json.loads((out_dir() / "items" / f"{it['i']:07d}.json").read_text()) for it in t1["items"]]
    bands = np.array([r["band"] for r in recs])
    orig = np.array([hit(FX.cep_pick(FX.cepstrum(np.load(os.path.join(e1e, "audio", f"{r['i']:07d}.npz"))["stem"]))[0],
                         r["true_ms"]) for r in recs], float)
    rep = {"phase": PHASE, "n": len(recs), "drawn ratio median": float(np.median([r["drawn_ratio_db"] for r in recs])),
           "stem keeps the delay": {"as drawn": float(orig.mean())}, "exposed - as drawn": {}}
    grid = np.array(t1["grid_ms"])
    lo = T1.lag_slice().start
    rep["T1's pick on the clean candidates (arm B)"], rep["peak-position pick"] = {}, {}
    for r in RATIOS:
        k = f"{r:+.0f}"
        h = np.array([hit(x["stem_peak_ms"][k], x["true_ms"]) for x in recs], float)
        rep["stem keeps the delay"][f"at {k} dB"] = float(h.mean())
        rep["exposed - as drawn"][f"at {k} dB"] = {"diff": float(h.mean() - orig.mean()),
                                                  "ci": T1.boot(lambda b: float(h[b].mean() - orig[b].mean()), bands)}
        hb, hp = [], []
        for x in recs:
            sc = np.load(out_dir() / "items" / f"{x['i']:07d}-cep.npz")[k]
            B = np.load(T1.out_dir() / "items" / f"{x['i']:07d}-cep.npz")["B"]
            hb.append(hit(float(grid[T1.pick(sc, B)]), x["true_ms"]))
            sp = (lo + int(np.argmax(sc))) * 1000.0 / T1.SR
            own = [(lo + int(np.argmax(c))) * 1000.0 / T1.SR for c in B]
            j = int(np.argmin([abs(np.log(o / sp)) for o in own]))
            hp.append(hit(float(grid[j]), x["true_ms"]))
        hb, hp = np.array(hb, float), np.array(hp, float)
        rep["T1's pick on the clean candidates (arm B)"][f"at {k} dB"] = float(hb.mean())
        rep["peak-position pick"][f"at {k} dB"] = float(hp.mean())
        rep.setdefault("pick - stems' own (paired)", {})[f"at {k} dB"] = {
            "correlation": {"diff": float(hb.mean() - h.mean()), "ci": T1.boot(lambda b: float(hb[b].mean() - h[b].mean()), bands)},
            "peak position": {"diff": float(hp.mean() - h.mean()), "ci": T1.boot(lambda b: float(hp[b].mean() - h[b].mean()), bands)}}
        ms = np.array([bool(x["mastered"]) for x in recs])
        rep.setdefault("stems' own by mastering", {})[f"at {k} dB"] = {"mastered": float(h[ms].mean()),
                                                                        "unmastered": float(h[~ms].mean())}
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(out_dir() / "read.json", rep)
    print(json.dumps(rep, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("t1x-build")
    b.add_argument("--device", default="mps")
    b.set_defaults(fn=cmd_build)
    sub.add_parser("t1x-read").set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
