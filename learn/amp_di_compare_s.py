"""A2s, A2's amp pick on the product's input (`docs/full-controls-plan.md`, "A2s in detail"; ledger `pipeline-fix`
`phase_a2s`): zero renders. A2 read the stock-DI pick against the song's guitar in its backing (D_fix variant 0, no
separator; the 2026-11-13 correction). The product reads the song's X-LANCE stem. A2s rebuilds each of A2's cap1, panel
GOAT and BKS units' variant-0 mix from its stored recipe (checked against the stored features), separates it by X-LANCE,
takes the product's input (`product_path`'s rule: the mix to -12.25 LUFS, the stem by the same gain), and re-runs A2's
frozen pick (the held-out fold model's floored body features, cosine to A2's stored stock-DI render mels) and A2's rows.
A unit whose backing isn't in the pool is skipped and counted (a dry check rebuilt every set, BKS's own backings too).

    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.amp_di_compare_s a2s-build --device mps
    $TORCH_PY -m learn.amp_di_compare_s a2s-read
"""

from __future__ import annotations

import argparse
import json
import time

from learn import amp_di_compare as A1
from learn import amp_di_compare_r as R

PHASE = "phase_a2s"
SETS = ("cap1", "panel", "goat", "bks")      # cap1 and the panel decide, as A2's
MIX_LEVEL = -12.25


def a2s_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "a2s"


def rebuild_v0(unit, prt, pool_by_id, stems):
    """A unit's D_fix variant-0 mix from its stored recipe (lender, gains, backing, vocals, mastering draw), checked:
    its half features must equal the stored ones exactly. -> mix, or None for an own-section backing (BKS)."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import pipeline_fix as P
    from learn import song_aug as SA

    d = np.load(P.dfix_input_path(unit, 0))
    ent = pool_by_id.get(str(d["backing"]))
    if ent is None:
        return None
    gtr = np.asarray(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64) * 10 ** (
        float(d["guitar_gain_db"]) / 20)
    voc = bool(d["vocals"])
    tracks = ent["tracks"]["v" if voc else "n"]
    back = np.asarray(stems.get(ent["id"], tracks) if ent["kind"] == "training"
                      else P.bare_backing(ent["sd"], tracks, ent["start_s"]), np.float64)
    gb, ga = (float(x) for x in d["gains"])
    mix = P.dfix_mix(gtr, back, gb, ga)
    mastered, mrng = DS.master_draw(int(d["lend"]))
    if mastered:
        mix = SA.compress(mix, mrng)
    f, _, _ = DS.half_features(mix)
    if not (np.array_equal(f["A"], d["sA"]) and np.array_equal(f["B"], d["sB"])):
        raise SystemExit(f"{unit}: the rebuilt variant-0 mix doesn't reproduce its stored features")
    return mix


def cmd_build(args):
    import argparse as AP
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import pipeline_fix as P
    from learn import trusted_data as T

    P.require(PHASE)
    _, units = R.state_units()
    pool = json.loads(P.wide_pool_path().read_text())["entries"]
    pool_by_id = {str(e["id"]): e for e in pool}
    stems = T.Stems(CB.ctx_for(AP.Namespace(out=None, smoke=False)))
    sep = DS.stem_separator(T.SEP, args.device)
    d = a2s_dir() / "stems"
    d.mkdir(parents=True, exist_ok=True)
    t0, done, own, by_set = time.time(), 0, 0, {}
    for u in [x for x in units if x["set"] in SETS]:
        p = d / f"{u['set']}__{u['unit'].replace('/', '__')}.npz"
        if p.exists():
            continue
        mix = rebuild_v0(u["unit"], u["prt"], pool_by_id, stems)
        if mix is None:
            own += 1
            continue
        stem = np.asarray(sep(mix), np.float64)
        if len(stem) != len(mix) or not np.isfinite(stem).all():
            raise SystemExit(f"{u['unit']}: bad stem")
        g = DE.inference_gain_db(mix, MIX_LEVEL)
        out = {}
        for h in ("A", "B"):
            s8, _, ls, _ = DS.step4_half(stem, mix, h, g)
            out[f"s{h}"], out[f"lufs{h}"] = s8, np.array([ls], np.float32)
        np.savez(p, **out)
        done += 1
        by_set[u["set"]] = by_set.get(u["set"], 0) + 1
        if done % 25 == 0:
            print(f"a2s build {done}: {(time.time() - t0) / done:.1f} s a unit", flush=True)
    P.save(a2s_dir() / "build.json", {"built": done, "by_set": by_set, "skipped (backing not in the pool)": own,
                                      "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"A2S BUILD DONE: {done} built {by_set}, {own} with a backing not in the pool skipped", flush=True)


def cmd_read(_args):
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import full_controls_c3 as X
    from learn import full_controls_c3r as R3
    from learn import full_space as FS
    from learn import pipeline_fix as P

    P.require(PHASE)
    st, units = R.state_units()
    base = R3.base_of("all", st)
    J = R.judges()
    head_p = json.loads((R.a2_dir() / "answers.json").read_text()).get("amp_p") or {}
    nets = {}

    def feats(name, x):
        with torch.no_grad():
            X_ = torch.tensor(np.asarray([x], np.float32))
            hs = []
            for net in nets[name]:
                h = net.body(X_)
                hs.append(torch.cat([h.mean(-1), h.std(-1)], dim=1).flatten(1)[0].numpy())
        return np.mean(hs, 0).tolist()

    def emb(name, m8, lu, sh, cls):
        m8 = np.maximum(m8, A1.FLOOR_U8)
        return feats(name, DS.model_input(m8, m8, lu, lu, sh, "sw50r", cls, "Dstem")[0])

    sets, picks_by = {}, {}
    for s in SETS:
        rows = {}
        for u in [x for x in units if x["set"] == s]:
            p = a2s_dir() / "stems" / f"{s}__{u['unit'].replace('/', '__')}.npz"
            if not p.exists() or any((s, u["unit"], a) not in J for a in A1.AMPS):
                continue
            name = P.ft_name(u["fold"], base=base)
            if name not in nets:
                nets[name] = [P.load_run(name, sd, "best")[0].eval() for sd in P.SEEDS]
            zs = np.load(p)
            zm = np.load(R.a2_dir() / "mels" / f"{s}__{u['unit'].replace('/', '__')}.npz")
            e = json.loads((R.a2_dir() / "embed" / f"{s}__{u['unit'].replace('/', '__')}.json").read_text())
            stem_pick = {}
            for sh in ("A", "B"):
                t = emb(name, zs[f"s{sh}"], float(zs[f"lufs{sh}"][0]), sh, u["cls"])
                n = sum(1 for k in zm.files if k.startswith(f"{sh}_{A1.AMPS[0]}_") and k.endswith(f"_{sh}"))
                renders = {a: [emb(name, zm[f"{sh}_{a}_{j}_{sh}"], float(zm[f"{sh}_{a}_{j}_{sh}_lufs"][0]), sh, u["cls"])
                               for j in range(n)] for a in A1.AMPS}
                stem_pick[sh] = A1.embed_pick(t, renders)
            picks = {"embedding": stem_pick, "embedding on the backed mix (A2's)": e["picks"]["stem"]}
            for nm, pk in picks.items():
                for sh in ("A", "B"):
                    picks_by.setdefault(s, {}).setdefault(nm, {a: 0 for a in A1.AMPS})[pk[sh]] += 1
            head = X.s2_picks(head_p, u["unit"], FS.AMPS)
            r, _ = A1.unit_rows(u["unit"], u["cluster"], u["cls"], {a: J[(s, u["unit"], a)] for a in A1.AMPS}, picks,
                                head if len(head) == 2 else {"A": "sw50r", "B": "sw50r"})
            for k, v in r.items():
                rows.setdefault(k, []).extend(v)
            judge = {a: J[(s, u["unit"], a)] for a in A1.AMPS}
            for sh, h in (("A", "B"), ("B", "A")):
                hv = {a: ((judge.get(a) or {}).get(sh) or {}).get(h) for a in A1.AMPS}
                if all(X.finite_pos(v) for v in hv.values()):
                    import math
                    rows.setdefault("the stem's pick - the backed mix's pick", []).append(
                        (u["cluster"], u["unit"], math.log(hv[stem_pick[sh]]) - math.log(hv[e["picks"]["stem"][sh]])))
        sets[s] = {k: P.clustered(v) for k, v in rows.items()}
    primary = {s: sets[s].get("DI-compare - always sw50r") for s in SETS}
    pool = R.deciding_pool(primary)
    deciding = [primary.get("cap1"), primary.get("panel"), pool]
    every = deciding + [primary.get("goat"), primary.get("bks")]
    worse = any(r and r.get("lo90") is not None and r["lo90"] > 0 for r in every)
    better = any(r and r.get("hi90") is not None and r["hi90"] < 0 for r in deciding)
    reading = "split" if worse and better else "worse" if worse else "learns" if better else "undecided"
    rep = {"phase": PHASE, "sets": sets, "deciding_pool": pool, "picks_by_amp": picks_by, "reading": reading,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(a2s_dir() / "a2s.json", rep)
    for s in SETS:
        for nm in ("DI-compare - always sw50r", "DI-compare by embedding on the backed mix (A2's) - always sw50r",
                   "the stem's pick - the backed mix's pick"):
            r = sets[s].get(nm) or {}
            print(f"{s} {nm}: {r.get('mean')} [{r.get('lo90')}, {r.get('hi90')}]")
    print(f"deciding pool: {pool}")
    print(f"A2S READING (DI-compare on the stem - always sw50r, deciding on cap1 and the panel): {reading}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("a2s-build")
    b.add_argument("--device", default="mps")
    b.set_defaults(fn=cmd_build)
    sub.add_parser("a2s-read").set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
