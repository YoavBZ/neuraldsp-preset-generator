"""T1's arm P (`docs/full-controls-plan.md`, "T1 in detail", arm P; ledger `pipeline-fix` `phase_t1p`): the positive
control the cloud researcher's report proposes (`docs/research/effects-estimation.md`). T1's masking-channel compare with
each item's *own* DI section (the performance the song was rendered from) in place of the stock DI, on 40 of T1's 134
items. With the content matched as well as the masking, it is T1's upper bound: A_P - A is what the generic DI costs.
Descriptive, no pass rule. Read only after T1's own read.

    .venv/bin/python -m learn.fx_t1p t1p-draw                        # the 40 items (zero renders)
    .venv/bin/python -m learn.fx_t1p t1p-render --shard 0/3          # the candidates (renders)
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.fx_t1p t1p-separate --device mps
    .venv/bin/python -m learn.fx_t1p t1p-read                        # the read (CPU)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time

from learn import fx_t1 as T1

PHASE = "phase_t1p"
N_ITEMS = 40
DRAW_SEED = 20261135


def out_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "t1p"


def item_dir():
    return out_dir() / "items"


def draw(items, n=N_ITEMS, seed=DRAW_SEED):
    """n of T1's items, seeded, in T1's order."""
    rng = random.Random(seed)
    keep = set(rng.sample(sorted(it["i"] for it in items), n))
    return [it for it in items if it["i"] in keep]


def cmd_draw(_args):
    from learn import cc_build as CB
    from learn import pipeline_fix as P

    P.require(PHASE)
    p = out_dir() / "plan.json"
    if p.exists():
        raise SystemExit(f"{p} exists: drawn once")
    t1 = json.loads((T1.out_dir() / "plan.json").read_text())
    if not (T1.out_dir() / "read.json").exists():
        raise SystemExit("T1's own read comes first")
    cc = json.loads(open(os.path.expanduser("~/ndsp-presets/learn/trusted-data/cc/plan.json")).read())
    sec = {e["i"]: e["section"] for e in cc["examples"]}
    ctx = CB.ctx_for(argparse.Namespace(out=None, smoke=False))
    items = []
    for it in draw(t1["items"]):
        s = ctx.sections[sec[it["i"]]]
        items.append({**it, "own": {"section": sec[it["i"]], "path": s["path"], "start_s": s["start_s"]}})
    out_dir().mkdir(parents=True, exist_ok=True)
    P.save(p, {"phase": PHASE, "grid_ms": t1["grid_ms"], "items": items, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"T1P DRAW: {len(items)} items; {len(items) * len(t1['grid_ms'])} candidates")


def cmd_render(args):
    """As T1's render, through each item's own DI section."""
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
    renders = 0
    for it in plan["items"][k::n]:
        out = item_dir() / f"{it['i']:07d}-cand.npz"
        if out.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        di = B.measure(PS.section_audio(it["own"]["path"], it["own"]["start_s"])).astype(np.float32)
        cands = []
        for t in plan["grid_ms"]:
            st = LO.tdict(T1.with_delay_time(it["settings"], t))
            y = np.asarray(AM.fresh_render(CB.new_renderer, di, it["select"], st, st), np.float64)[trim[0]:trim[1]]
            renders += 2
            cands.append((np.mean(y, 1) if y.ndim == 2 else y).astype(np.float32))
        tmp = out.with_suffix(".tmp.npz")
        np.savez(tmp, cand=np.stack(cands))
        tmp.replace(out)
        print(f"{it['cls']}: renders so far {renders}", flush=True)
    print(f"T1P RENDER DONE {k}/{n}: {renders} renders", flush=True)


def cmd_separate(args):
    """As T1's separation (the residual, loudness match, X-LANCE, cepstra), on arm P's candidates."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import fx_reader as FX
    from learn import song_aug as SA
    from learn import trusted_data as T

    plan = json.loads((out_dir() / "plan.json").read_text())
    sep = DS.stem_separator(T.SEP, args.device)
    ls = T1.lag_slice()
    todo = [it for it in plan["items"] if not (item_dir() / f"{it['i']:07d}-cep.npz").exists()]
    t0, done = time.time(), 0
    while todo:
        ready = [it for it in todo if (item_dir() / f"{it['i']:07d}-cand.npz").exists()]
        if not ready:
            time.sleep(60)
            continue
        for it in ready:
            z = np.load(os.path.join(T1.e1e(), "audio", f"{it['i']:07d}.npz"))
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
                     stem=FX.cepstrum(stem)[ls].astype(np.float32))
            done += 1
            print(f"t1p separate {done}/{len(plan['items'])}: {(time.time() - t0) / done:.1f} s an item", flush=True)
        todo = [it for it in todo if not (item_dir() / f"{it['i']:07d}-cep.npz").exists()]
    print("T1P SEPARATE DONE", flush=True)


def cmd_read(_args):
    import numpy as np

    from learn import pipeline_fix as P

    P.require(PHASE)
    plan = json.loads((out_dir() / "plan.json").read_text())
    t1 = json.loads((T1.out_dir() / "read.json").read_text())
    per = {r["i"]: r for r in t1["per_item"]}
    grid = np.array(plan["grid_ms"])
    items = plan["items"]
    pa = np.array([grid[T1.pick(*(lambda z: (z["stem"], z["A"]))(np.load(item_dir() / f"{it['i']:07d}-cep.npz")))]
                   for it in items])
    pb = np.array([grid[T1.pick(*(lambda z: (z["stem"], z["B"]))(np.load(item_dir() / f"{it['i']:07d}-cep.npz")))]
                   for it in items])
    tm = np.array([it["true_ms"] for it in items])
    bands = np.array([it["band"] for it in items])
    P_ = {"A_P": pa, "B_P": pb, **{k: np.array([per[it["i"]][k] for it in items]) for k in ("A", "B", "F52", "prior")}}
    hit = {k: np.array([T1.within10(p, t) for p, t in zip(v, tm)], float) for k, v in P_.items()}
    lerr = {k: np.abs(np.log2(v) - np.log2(tm)) for k, v in P_.items()}

    def paired(a, b):
        return {"diff": float(a.mean() - b.mean()), "ci": T1.boot(lambda x: float(a[x].mean() - b[x].mean()), bands)}
    rep = {"phase": PHASE, "n": len(items), "within_10pct": {k: float(v.mean()) for k, v in hit.items()},
           "log2_mae": {k: float(v.mean()) for k, v in lerr.items()},
           "A_P - A, within 10% (what the stock DI costs)": paired(hit["A_P"], hit["A"]),
           "A_P - prior, log2 error": paired(lerr["A_P"], lerr["prior"]),
           "A_P - B_P, within 10% (the channel, own DI)": paired(hit["A_P"], hit["B_P"]),
           "per_item": [{"i": it["i"], "true_ms": it["true_ms"], **{k: float(v[j]) for k, v in P_.items()}}
                        for j, it in enumerate(items)],
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(out_dir() / "read.json", rep)
    print(json.dumps({k: v for k, v in rep.items() if k != "per_item"}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("t1p-draw").set_defaults(fn=cmd_draw)
    r = sub.add_parser("t1p-render")
    r.add_argument("--shard", type=T1.shard, default=(0, 1))
    r.set_defaults(fn=cmd_render)
    s = sub.add_parser("t1p-separate")
    s.add_argument("--device", default="mps")
    s.set_defaults(fn=cmd_separate)
    sub.add_parser("t1p-read").set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
