"""A2, A1's confirmation on the adopted model (`docs/full-controls-plan.md`, "A2 in detail"; ledger `pipeline-fix`
`phase_a2`): A1's stock-DI pick, frozen, on R-all's out-of-fold answers, read on units no A1 choice was made on (C3r's cap1
and panel units), with GOAT and BKS beside. n12 is left out: its units are the stock DIs' source.

    $TORCH_PY -m learn.amp_di_compare_r a2-predict                      # R-all's answers on all three amps (CPU)
    .venv/bin/python -m learn.amp_di_compare_r a2-judge --shard 0/3     # the other two amps through the unit's DI (renders)
    .venv/bin/python -m learn.amp_di_compare_r a2-render --shard 0/3    # each amp's answer through the stock DIs (renders)
    $TORCH_PY -m learn.amp_di_compare_r a2-embed                        # A1's floored features (CPU, zero renders)
    .venv/bin/python -m learn.amp_di_compare_r a2-rows                  # the read (zero renders)

A1's pure parts are reused (`amp_di_compare`); A2's own pure parts (the units and the deciding pool) are unit-tested.
"""

from __future__ import annotations

import argparse
import json
import math
import time

from learn import amp_di_compare as A1

PHASE = "phase_a2"
SETS = ("cap1", "panel", "goat", "bks")       # the first two decide (fresh to A1); GOAT and BKS beside
DECIDING = ("cap1", "panel")
AMPS = A1.AMPS


def a2_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "a2"


def fname(key):
    return key.replace("/", "__").replace(" ", "_")


def units_of(read_units):
    """C3r's read units, one per unit, outside n12: {set, unit, forced amp, fold, lag, cluster, cls, prt}."""
    out, seen = [], set()
    for ru in read_units:
        if ru["set"] not in SETS or (ru["set"], ru["unit"]) in seen:
            continue
        seen.add((ru["set"], ru["unit"]))
        out.append({"set": ru["set"], "unit": ru["unit"], "amp": ru["amp"], "fold": ru["fold"], "lag": ru["lag"],
                    "cluster": ru["cluster"], "cls": ru["prt"]["cls"], "prt": ru["prt"]})
    return out


def deciding_pool(rows_by_set):
    """The deciding pool: cap1 and the panel, weighted equally (C3's `pooled`). rows_by_set: {set: clustered row}."""
    from learn import full_controls_c3 as X

    return X.pooled(rows_by_set.get("cap1") or {}, rows_by_set.get("panel") or {})


def reading(rows_by_set, pool):
    """C3's test on "DI-compare - always sw50r": "learns" if better on cap1, the panel or their pool, and worse on none
    of cap1, the panel, their pool, GOAT or BKS; otherwise "worse", "split" or "undecided"."""
    deciding = [rows_by_set.get(s) for s in DECIDING] + [pool]
    every = deciding + [rows_by_set.get("goat"), rows_by_set.get("bks")]
    worse = any(r and r.get("lo90") is not None and r["lo90"] > 0 for r in every)
    better = any(r and r.get("hi90") is not None and r["hi90"] < 0 for r in deciding)
    return "split" if worse and better else "worse" if worse else "learns" if better else "undecided"


# --- the commands -------------------------------------------------------------------------------------------------------

def target_lufs():
    """R-all's own input loudness (its fold models'), the gain the renders and the clean track are read at."""
    from learn import pipeline_fix as P

    rec = json.loads((P.out_dir() / "runs" / f"C3r-all-k0-{P.SEEDS[0]}.json").read_text())
    return P.model_input_lufs(rec)


def state_units():
    from learn import full_controls_c3r as R3

    st = R3.state()
    return st, units_of(R3.read_units(st))


def cmd_predict(_args):
    """R-all's answers (zero renders, CPU): each unit by the C3r FT_k that held it out, both seeds pooled, on its D_fix
    variant 0, per search half, on all three amps, held as C3r's read holds them. -> a2/answers.json."""
    from learn import direct_stems as DS
    from learn import full_controls_c3r as R3
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    P.require(PHASE)
    st, units = state_units()
    base, hold, ms = R3.base_of("all", st), R3.answer_hold(st), P.A_menu_S()
    models = {}
    out = {}
    for u in units:
        k = u["fold"]
        if k not in models:
            models[k] = [P.load_run(P.ft_name(k, base=base), sd, "best")[0] for sd in P.SEEDS]
        backed = P.dfix_backed(u["unit"])
        for a in AMPS:
            sel, S = ms[a][u["cls"]]
            for sh in ("A", "B"):
                s8, ls = backed[sh]
                x, c = DS.model_input(s8, s8, ls, ls, sh, a, u["cls"], "Dstem")
                r = F.readout([o[0] for o in F.run_nets(models[k], [x], [c])])
                stg = F.answer_settings(a, S, r["a2"], r["sw_p"], r["mics"])
                stg = P.hold_outside_space(stg, S, a) if hold is None else P.hold_outside_space(stg, S, a, hold)
                out.setdefault(u["set"], {}).setdefault(f"{u['unit']}|{a}", {})[sh] = {"select": sel, "settings": LO.sdict(stg)}
    P.save(a2_dir() / "answers.json", {"phase": PHASE, "base": base, "c3r_sha256": st["sha256"], "answers": out,
                                       "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"A2 PREDICT DONE: {len(units)} units x 3 amps")


def cmd_judge(args):
    """Each unit's answer on every amp but its own (whose render C3r's read holds), through the unit's DI, fresh and
    primed, judged on both halves at its lag -> a2/judge/<set>/<unit>|<amp>.json. BKS's 40 are on all three already."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(PHASE)
    _, units = state_units()
    ans = json.loads((a2_dir() / "answers.json").read_text())["answers"]
    k, n = args.shard
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for u in [x for x in units if x["set"] != "bks"][k::n]:
        if u["lag"] is None:
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        prt, di32 = u["prt"], None
        for a in [x for x in AMPS if x != u["amp"]]:
            key = f"{u['unit']}|{a}"
            gp = a2_dir() / "judge" / u["set"] / f"{fname(key)}.json"
            if gp.exists():
                continue
            if di32 is None:
                di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
                di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
                ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            rec = {"set": u["set"], "unit": u["unit"], "amp": a, "lag": u["lag"], "judge": {}}
            for sh, x in sorted(ans[u["set"]][key].items()):
                st = LO.tdict(x["settings"])
                y = np.asarray(AM.fresh_render(CB.new_renderer, di32, x["select"], st, st), np.float64)[trim[0]:trim[1]]
                renders += 2
                rec["judge"][sh] = K.judge(ref, y, di, u["lag"])
            P.save(gp, rec)
        print(f"{u['set']}: renders so far {renders}", flush=True)
    print(f"A2 JUDGE DONE {k}/{n}: {renders} renders", flush=True)


def judges():
    """{(set, unit, amp): judge} for every unit and amp: C3r's read for each unit's own amp (and BKS's three), A2's for
    the rest. The forced amp's answer in a2/answers.json must equal C3r's read's (checked)."""
    from learn import full_controls_c3r as R3

    st, units = state_units()
    a2 = json.loads((a2_dir() / "answers.json").read_text())["answers"]
    c3r = json.loads(R3.answers_path("all").read_text())["answers"]
    out, mism = {}, []
    for u in units:
        for a in AMPS:
            key = f"{u['unit']}|{a}"
            if u["set"] == "bks" or a == u["amp"]:
                if c3r[u["set"]].get(key) != a2[u["set"]][key]:
                    mism.append(key)
                p = R3.judge_path("all", {"set": u["set"], "unit": u["unit"], "amp": a})
            else:
                p = a2_dir() / "judge" / u["set"] / f"{fname(key)}.json"
            if p.exists():
                out[(u["set"], u["unit"], a)] = json.loads(p.read_text())["judge"]
    if mism:
        raise SystemExit(f"{len(mism)} of A2's answers differ from C3r's read (first {mism[0]})")
    return out


def cmd_render(args):
    """A1's stock-DI render on R-all's answers (A1's plan's stock DIs) -> a2/shapes, a2/mels."""
    from learn import pipeline_fix as P

    P.require(PHASE)
    _, units = state_units()
    ans = json.loads((a2_dir() / "answers.json").read_text())["answers"]
    A1.render_units([{"set": u["set"], "unit": u["unit"], "cls": u["cls"],
                      "answers": {a: ans[u["set"]][f"{u['unit']}|{a}"] for a in AMPS}} for u in units],
                    a2_dir(), args.shard, target=target_lufs())


def cmd_embed(_args):
    """A1's floored features on R-all's renders, by the C3r FT_k that held each unit out -> a2/embed."""
    from learn import full_controls_c3r as R3
    from learn import pipeline_fix as P

    P.require(PHASE)
    st, units = state_units()
    base = R3.base_of("all", st)
    A1.embed_units([{**u, "model": P.ft_name(u["fold"], base=base)} for u in units], a2_dir(), target=target_lufs())


def cmd_rows(_args):
    """The read (zero renders) -> a2/a2.json: per set, A1's pick rows on R-all's own per-amp renders; the deciding pool."""
    from learn import pipeline_fix as P

    P.require(PHASE)
    _, units = state_units()
    J = judges()
    sets, counts = {}, {}
    for s in SETS:
        rows, dropped, by_amp = {}, 0, {}
        for u in [x for x in units if x["set"] == s]:
            if any((s, u["unit"], a) not in J for a in AMPS):
                dropped += 2
                continue
            e = json.loads((a2_dir() / "embed" / f"{s}__{u['unit'].replace('/', '__')}.json").read_text())
            picks = {"embedding": e["picks"]["stem"], "embedding on the clean amp track": e["picks"]["clean amp track"]}
            for nm, p_ in picks.items():
                for sh in ("A", "B"):
                    by_amp.setdefault(nm, {a: 0 for a in AMPS})[p_[sh]] += 1
            r, dr = A1.unit_rows(u["unit"], u["cluster"], u["cls"], {a: J[(s, u["unit"], a)] for a in AMPS}, picks,
                                 {"A": "sw50r", "B": "sw50r"})
            dropped += dr
            for k, v in r.items():
                rows.setdefault(k, []).extend(v)
        sets[s] = {k: P.clustered(v) for k, v in rows.items()}
        counts[s] = {"picks_by_amp": by_amp, "dropped": dropped}
    primary = {s: sets[s].get("DI-compare - always sw50r") for s in SETS}
    pool = deciding_pool(primary)
    rd = reading(primary, pool)
    rec = {"phase": PHASE, "sets": sets, "deciding_pool": pool, "counts": counts, "reading": rd,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(a2_dir() / "a2.json", rec)
    for s in SETS:
        for nm in ("DI-compare - always sw50r", "DI-compare by embedding on the clean amp track - always sw50r"):
            r = sets[s].get(nm) or {}
            print(f"{s} {nm}: {r.get('mean')} [{r.get('lo90')}, {r.get('hi90')}]")
    print(f"deciding pool: {pool}")
    print(f"A2 READING (DI-compare - always sw50r, deciding on cap1 and the panel): {rd}")


def shard(s):
    a, b = s.split("/")
    return int(a), int(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("a2-predict").set_defaults(fn=cmd_predict)
    for c, f in (("a2-judge", cmd_judge), ("a2-render", cmd_render)):
        r = sub.add_parser(c)
        r.add_argument("--shard", type=shard, default=(0, 1))
        r.set_defaults(fn=f)
    sub.add_parser("a2-embed").set_defaults(fn=cmd_embed)
    sub.add_parser("a2-rows").set_defaults(fn=cmd_rows)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
