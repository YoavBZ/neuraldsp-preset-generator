"""Every control on the real rows, C1b (`docs/full-controls-plan.md`, "C1b in detail"; ledger `pipeline-fix` `phase_c1b`).
On top of each C1a label: the rest of the cab (the left cab and the room mics), the mic types re-checked jointly with
the amp EQ, then each time effect on its own (reverb, delay, tremolo, the amp's spring), kept only past a declared
margin on fresh renders. C1a's 71 records. Development only, the true DI, no model, no training.

    .venv/bin/python -m learn.full_controls_c1b c1b-draw                 # the records (zero renders)
    .venv/bin/python -m learn.full_controls_c1b c1b-search --shard 0/3   # the searches (renders; at most 3 shards)
    .venv/bin/python -m learn.full_controls_c1b c1b-report               # the rows (zero renders)

The pure parts (the records, the start, the spaces, the canonical form, the keep rule, the choice, the ablations, the
flags and the rows) are unit-tested; the search is tested on a stub renderer.
"""

from __future__ import annotations

import argparse
import json
import math
import time

from learn import full_controls as F

PHASE = "phase_c1b"
SEED = 20261125                      # stage A; stage B SEED + 1; effect i SEED + 2 + i
BUDGET_ROOMS = 16                    # stage A: the left cab and the room mics, about 3 a control
BUDGET_MICS_EQ = 48                  # stage B: the mics and the amp EQ jointly (`knob_search`, its mic stages)
PER_KNOB = 3.5                       # stage C: each effect's budget, by its knobs (knob ceiling 2 used 24 an effect)
KEEP_MARGIN = 0.02                   # an effect is kept only if its fresh render beats the dry one by this (search
                                     # half, log): declared before use, above knob ceiling 2's 0.005 (see the plan)
START_TOL = F.START_TOL
DRIFT_DB = 10.0                      # an output-level drift flag: the final's peak this far below the start's
ROOM_KEYS = (("cabParameters", "leftCabActive"), ("cabParameters", "leftCabMicLevel"),
             ("cabParameters", "leftRoomActive"), ("cabParameters", "leftRoomMicLevel"),
             ("cabParameters", "rightRoomActive"), ("cabParameters", "rightRoomMicLevel"))
MIC_KEYS = (("cabParameters", "leftMicType"), ("cabParameters", "rightMicType"))
SPRING_KEY = ("spring", "springOn")
ABLATIONS = ("rooms_reset", "mics_eq_reset", "effects_reset")
OUT_DIRS = {"n12": ("captures2", "search-c1b"), "bks": ("real", "search-c1b")}
C1A_DIRS = {"n12": ("captures2", "search-c1a"), "bks": ("real", "search-c1a")}


def _on(x, k):
    return str(x.get(k, "false")).lower() in ("true", "1")


# --- records (zero renders) -------------------------------------------------------------------------------------------

def c1b_records(c1a_records, outputs):
    """C1a's records ({key: C1a output}, written ones only) -> C1b's records and the C1a records left out (refused, a
    fallback label, or no output), with why."""
    recs, out = [], []
    for r in c1a_records:
        o = outputs.get(r["key"])
        why = ("no C1a output" if o is None else "refused in C1a" if "refused" in o
               else "C1a label fell back" if o.get("label") is None else None)
        if why:
            out.append({"key": r["key"], "why": why})
            continue
        recs.append({k: r[k] for k in ("set", "key", "unit", "amp", "cls", "cluster", "real_out", "prt")}
                    | {"measurement_only": r["set"] == "n12", "source": o["_path"]})
    return recs, out


# --- the start, the spaces and the canonical form ---------------------------------------------------------------------

def make_canon(amp):
    """C1b's canonical form: the rooms' own controls to neutral when they can't sound
    (`every_control.group_canon("rooms")`), then the time effects' (`knob_ceiling2.make_canon_effects`: an off effect's
    knobs at its declared on values, sync free)."""
    from learn import every_control as E
    from learn import knob_ceiling2 as K2

    rooms, fx = E.group_canon("rooms", amp), K2.make_canon_effects(amp)

    def canon(x):
        return fx(rooms(x))
    return canon


def with_spring(x, amp):
    """The spring's pseudo-switch (`knob_ceiling2.SPRING_SWITCH`) set from the stored level: on if the level is above 0."""
    from learn import knob_ceiling2 as K2

    y = dict(x)
    if amp in K2.SPRING:
        level = next(iter(K2.SPRING[amp][0]))
        y[SPRING_KEY] = "true" if float(y.get(level, 0) or 0) > 0 else "false"
    return y


def plugin(x, amp):
    """What the plugin gets: the spring's pseudo-switch made real (`knob_ceiling2.plugin_settings`)."""
    from learn import knob_ceiling2 as K2

    return K2.plugin_settings(x, amp)


def c1b_start(label, amp):
    """The C1a label ({"module/key": value}) with the spring's pseudo-switch, in C1b's canonical form."""
    from learn import local_objective as LO

    return make_canon(amp)(with_spring(LO.tdict(label), amp))


def raw_start(label, amp):
    """Amendment-1-style second start: the C1a label as stored, with only the spring's pseudo-switch added."""
    from learn import local_objective as LO

    return with_spring(LO.tdict(label), amp)


def audible_change(start, label, amp):
    """What the start changes from the label that can sound, read on the plugin's settings (must be empty)."""
    return F.audible_change(plugin(start, amp), label, amp)


def rooms_dims(x):
    """Stage A: the left cab and the room mics, as `every_control.group_plan("rooms")` lists them but nothing switched
    on: the left cab's switch only while the right cab is on (one cab must stay on), the right room only while the
    right cab is on. Room mic types have no UI control and stay as stored."""
    from learn import every_control as E

    dims = [E._dim(("cabParameters", "leftCabActive")), E._dim(("cabParameters", "leftCabMicLevel")),
            E._dim(("cabParameters", "leftRoomActive")), E._dim(("cabParameters", "leftRoomMicLevel"))]
    if _on(x, ("cabParameters", "rightCabActive")):
        dims += [E._dim(("cabParameters", "rightRoomActive")), E._dim(("cabParameters", "rightRoomMicLevel"))]
    else:
        dims = [d for d in dims if d.key != "leftCabActive"]
    return dims


def mics_eq_dims(x, amp):
    """Stage B: the mic type of each cab that is on, with the amp EQ (its 9 bands and both filters), searched together."""
    from learn import knob_ceiling as K

    mics = [d for d in K.CAB if d.kind == "cat" and _on(x, ("cabParameters", d.key.replace("MicType", "CabActive")))]
    return mics + K.eq_space(amp)


def effect_plan(amp):
    """Stage C, each effect on its own: {name: (switch key, knob dims, budget)}; the budget is PER_KNOB a knob."""
    from learn import knob_ceiling2 as K2

    out = {n: (sw, dims) for n, (sw, _, dims) in K2.EFFECTS.items()}
    if amp in K2.SPRING:
        out["spring"] = (SPRING_KEY, K2.SPRING[amp][1])
    return {n: (sw, dims, round(PER_KNOB * len(dims))) for n, (sw, dims) in out.items()}


def effect_start(dry, sw, amp, raw=False):
    """One effect switched on at its declared on values, on top of the dry best. Canonically, `make_canon` sets them
    (an off effect already holds them); on the raw path (Amendment-1-style fallback) they are set for this effect
    alone, with its sync free, and nothing else is touched."""
    from learn import knob_ceiling2 as K2

    if not raw:
        return make_canon(amp)({**dry, sw: "true"})
    on = dict(K2.SPRING[amp][0]) if sw == SPRING_KEY else dict(next(v[1] for v in K2.EFFECTS.values() if v[0] == sw))
    sync = {k: v for k, v in K2.FREE_SYNC.items() if k[0] == sw[0]}
    return {**dry, **on, **sync, sw: "true"}


# --- the keep rule, the choice, the ablations -------------------------------------------------------------------------

def passes(wet, dry, margin=KEEP_MARGIN):
    """A wet value beats the dry one by the margin (log), both finite and positive."""
    return all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in (wet, dry)) and \
        math.log(wet / dry) <= -margin


def choose(confirmed, dry_fresh):
    """confirmed: {effect: fresh search-half value} for the effects that passed in process. -> the effect kept (the
    lowest of those passing the margin on fresh renders) or None (dry)."""
    ok = {n: v for n, v in confirmed.items() if passes(v, dry_fresh)}
    return min(sorted(ok), key=lambda n: ok[n]) if ok else None


def ablation_settings(final, start, dry, amp, raw=False):
    """{name: setting}: the final with the rooms or the mics and amp EQ back to the start's (the C1a label's), and the
    effects reset (the dry best), in canonical form (as they are, on the raw path)."""
    canon = (lambda x: x) if raw else make_canon(amp)
    eq = [k for k in start if k[0] == f"{amp}EQ"]
    return {"rooms_reset": canon(F.reset(final, start, list(ROOM_KEYS))),
            "mics_eq_reset": canon(F.reset(final, start, list(MIC_KEYS) + eq)), "effects_reset": dict(dry)}


def drifted(start_peak, final_peak, db=DRIFT_DB):
    """The output-level drift flag: the final's peak more than `db` below the start's."""
    try:
        return float(start_peak) - float(final_peak) > db
    except (TypeError, ValueError):
        return False


def nonfinite_ablations(recs):
    """[(unit, ablation)] whose held-half judge is not finite and positive: named, not dropped silently."""
    out = []
    for r in recs:
        for a, v in ((r.get("fresh") or {}).get("ablations") or {}).items():
            if F._pos((v.get("judge") or {}).get(r["held"])) is None:
                out.append((r["unit"], a))
    return out


# --- the rows ---------------------------------------------------------------------------------------------------------

def record_values(r):
    """One record's held-half rows (ln ratios): C1b's final against C1a's fresh best, each ablation against the final;
    or None."""
    h = r["held"]
    fin = F._pos(((r.get("fresh") or {}).get("final") or {}).get("judge", {}).get(h))
    lab = F._pos((r.get("c1a_fresh_best") or {}).get(h))
    if fin is None or lab is None or r.get("label") is None:
        return None
    abl = {}
    for a in ABLATIONS:
        v = F._pos((((r["fresh"].get("ablations") or {}).get(a) or {}).get("judge") or {}).get(h))
        if v is not None:
            abl[a] = math.log(v / fin)
    return {"primary": math.log(fin / lab), "ablations": abl}


def report_rows(recs, tq, clus):
    vals = [(r, record_values(r)) for r in recs]
    vals = [(r, v) for r, v in vals if v is not None]

    def row(sub, get):
        pts = [(r["cluster"], r["unit"], get(v)) for r, v in sub if get(v) is not None]
        if not pts:
            return None
        return dict(F.with_interval(F.jackknife_mean([(c, x) for c, _, x in pts]), tq), band_weighted=clus(pts))

    def rows(sub):
        kept = {}
        for r, _ in sub:
            if r.get("effect_kept"):
                kept[r["effect_kept"]] = kept.get(r["effect_kept"], 0) + 1
        return {"primary": row(sub, lambda v: v["primary"]),
                "ablations": {a: row(sub, lambda v, a=a: v["ablations"].get(a)) for a in ABLATIONS},
                "effects_kept": kept, "mics_changed": sum(1 for r, _ in sub if r.get("mics_changed")),
                "records": len(sub)}

    res = {"all": rows(vals) if vals else None}
    for cl in ("clean", "crunch"):
        sub = [(r, v) for r, v in vals if r["cls"] == cl]
        res[cl] = rows(sub) if sub else None
    res["records"] = len(vals)
    return res


# --- commands -----------------------------------------------------------------------------------------------------------

def c1b_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "c1b"


def cmd_draw(_args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    path = c1b_dir() / "records.json"
    if path.exists():
        raise SystemExit(f"{path} exists: the records are drawn once")
    c1a = json.loads((F.c1a_dir() / "records.json").read_text())["records"]
    outs = {}
    for r in c1a:
        root, sub = C1A_DIRS[r["set"]]
        q = P.out_dir() / root / sub / f"{F.fname(r['key'])}.json"
        if q.exists():
            outs[r["key"]] = dict(json.loads(q.read_text()), _path=str(q))
    recs, left = c1b_records(c1a, outs)
    P.save(path, {"phase": PHASE, "seed": SEED, "records": recs, "left_out": left,
                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    upper = sum(65 + sum(1 + b + 2 for _, _, b in effect_plan(r["amp"]).values()) + 6 for r in recs)
    print("C1B DRAW", len(recs), "records,", len(left), "left out; renders at most", upper, flush=True)


def cmd_search(args):
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(PHASE)
    plan = json.loads((c1b_dir() / "records.json").read_text())
    k, n = args.shard
    mine = [r for j, r in enumerate(sorted(plan["records"], key=lambda r: r["key"])) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    counts = {"canonical": 0, "raw_after_miss": 0, "refused": 0}

    def sorted_x(x, amp):
        return LO.tdict(LO.sdict(plugin(x, amp)))

    for rec in mine:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        root, sub = OUT_DIRS[rec["set"]]
        out = P.out_dir() / root / sub / f"{F.fname(rec['key'])}.json"
        if out.exists():
            continue
        src = json.loads(open(rec["source"]).read())
        amp, prt = rec["amp"], rec["prt"]
        if src.get("label") is None or src["unit"] != rec["unit"] or src["amp"] != amp:
            raise SystemExit(f"{rec['key']}: the C1a record's unit, amp or label does not fit")
        sel, search, held, lag = src["select"], src["search"], src["held"], src["lag"]
        label = src["label"]
        start = c1b_start(label, amp)
        bad = audible_change(start, label, amp)
        if bad:
            raise SystemExit(f"{rec['key']}: the start changes what sounds: {bad}")
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        ref_v = float(src["best"]["judge"][search])

        def fresh(x):
            xs = sorted_x(x, amp)
            y = np.asarray(AM.fresh_render(CB.new_renderer, di32, sel, xs, xs), np.float64)[trim[0]:trim[1]]
            return {"judge": K.judge(ref, y, di, lag), "render_sha256": AM.audio_sha(y), "peak_dbfs": A.peak_dbfs(y, trim_s=0.0)}

        def dry_stages(x0, canon):
            """Stages A and B in one renderer process primed with x0 (dry: no tail carries over); canon None on the
            raw path, so its first evaluation is x0 as stored. Raises F.StartMiss if the first evaluation is not C1a's
            stored best. -> (renders, x_A, x_B, record)."""
            used = [1]
            seen, trace = {}, []
            rr = CB.new_renderer()
            try:
                rr.render(di32, sel, sorted_x(x0, amp))

                def f(x):
                    key = K.key(x)
                    if key in seen:
                        return seen[key]["judge"][search]
                    y = np.asarray(rr.render(di32, sel, sorted_x(x, amp)), np.float64)[trim[0]:trim[1]]
                    used[0] += 1
                    j = K.judge(ref, y, di, lag)
                    if not trace and not F.within(j[search], ref_v):
                        raise F.StartMiss(j[search], AM.audio_sha(y))
                    seen[key] = {"judge": j, "peak_dbfs": A.peak_dbfs(y, trim_s=0.0)}
                    trace.append({"stage": stage[0], "judge": j})
                    return j[search]

                stage = ["A"]
                xa, _, _ = K.coord_search(rooms_dims(x0), x0, f, BUDGET_ROOMS, SEED, cats="levels", canon=canon)
                stage[0] = "B"
                xb, _, _, stages_b = K.knob_search(mics_eq_dims(xa, amp), xa, f, BUDGET_MICS_EQ, SEED + 1, canon=canon)
            except F.StartMiss as miss:
                miss.renders = used[0]
                raise
            finally:
                rr.close()
            return used[0], xa, xb, {"trace": trace, "start": seen[K.key(x0)], "a": seen[K.key(xa)],
                                     "b": seen[K.key(xb)], "stages_b": stages_b}

        start_kind, first_miss, raw = "canonical", None, False
        try:
            used, xa, xb, dry = dry_stages(start, make_canon(amp))
            renders += used
        except F.StartMiss as miss:
            renders += miss.renders
            first_miss = {"value": miss.value, "sha": miss.sha, "ref_value": ref_v}
            start = raw_start(label, amp)
            try:
                used, xa, xb, dry = dry_stages(start, None)
                renders += used
                start_kind, raw = "raw_after_miss", True
            except F.StartMiss as m2:
                renders += m2.renders
                first_miss["raw_value"] = m2.value
                P.save(out, {"plan": "docs/full-controls-plan.md", "ledger": f"{P.LEDGER_ID} {PHASE}",
                             "set": rec["set"], "unit": rec["unit"], "cls": rec["cls"], "amp": amp,
                             "cluster": rec["cluster"], "real_out": rec["real_out"],
                             "measurement_only": rec["measurement_only"], "label": None, "start_kind": "refused",
                             "refused": first_miss, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
                counts["refused"] += 1
                print(f"{rec['key'][-70:]}: refused ({miss.value}, raw {m2.value} against {ref_v}); renders so far "
                      f"{renders}", flush=True)
                continue
        counts[start_kind] += 1
        canon = None if raw else make_canon(amp)
        fr_dry = fresh(xb)
        renders += 2
        per, confirmed = {}, {}
        for i, (name, (sw, dims, budget)) in enumerate(effect_plan(amp).items()):
            x0 = effect_start(xb, sw, amp, raw=raw)
            vals, best = [], [None, math.inf, None]
            rr = CB.new_renderer()                      # its own process: no other effect's tail carries in
            try:
                rr.render(di32, sel, sorted_x(x0, amp))
                renders += 1

                def g(x):
                    y = np.asarray(rr.render(di32, sel, sorted_x(x, amp)), np.float64)[trim[0]:trim[1]]
                    j = K.judge(ref, y, di, lag)
                    vals.append(j[search])
                    if math.isfinite(j[search]) and j[search] < best[1]:
                        best[:] = [dict(x), j[search], j]
                    return j[search]

                K.knob_search(dims, x0, g, budget, SEED + 2 + i, canon=canon)
                renders += len(vals)
            finally:
                rr.close()
            per[name] = {"renders": len(vals), "in_process_best": best[1], "in_process_judge": best[2],
                         "passed_in_process": best[0] is not None and passes(best[1], dry["b"]["judge"][search]),
                         "settings": None if best[0] is None else LO.sdict(plugin(best[0], amp))}
            if per[name]["passed_in_process"]:
                fw = fresh(best[0])
                renders += 2
                per[name]["fresh"] = fw
                confirmed[name] = fw["judge"][search]
                per[name]["_x"] = best[0]
        kept = choose(confirmed, fr_dry["judge"][search])
        final = per[kept].pop("_x") if kept else xb
        for v in per.values():
            v.pop("_x", None)
        fr = {"dry": fr_dry, "final": per[kept]["fresh"] if kept else fr_dry, "ablations": {}}
        for name, x in ablation_settings(final, start, xb, amp, raw=raw).items():
            if K.key(x) == K.key(final):
                fr["ablations"][name] = dict(fr["final"], same_as_final=True)
            elif K.key(x) == K.key(xb):
                fr["ablations"][name] = dict(fr_dry, same_as_dry=True)
            else:
                fr["ablations"][name] = fresh(x)
                renders += 2
        fb = A.fallback_reason(fr["final"]["peak_dbfs"], fr["final"]["judge"][search])
        c1a_fresh = (src.get("fresh") or {}).get("best") or {}
        P.save(out, {"plan": "docs/full-controls-plan.md", "ledger": f"{P.LEDGER_ID} {PHASE}", "set": rec["set"],
                     "unit": rec["unit"], "rig": src.get("rig"), "di": src.get("di"), "cls": rec["cls"], "amp": amp,
                     "select": sel, "search": search, "held": held, "lag": lag, "cluster": rec["cluster"],
                     "real_out": rec["real_out"], "measurement_only": rec["measurement_only"], "seed": SEED,
                     "keep_margin": KEEP_MARGIN, "source": rec["source"], "c1a_best_judge": src["best"]["judge"],
                     "c1a_fresh_best": c1a_fresh.get("judge"), "c1a_fresh_peak": c1a_fresh.get("peak_dbfs"),
                     "start_kind": start_kind, "first_start_miss": first_miss,
                     "start_settings": LO.sdict(plugin(start, amp)), "start": dry["start"],
                     "stage_a": dry["a"], "stage_b": dry["b"], "trace": dry["trace"],
                     "rooms_keys": [d.name for d in rooms_dims(start)],
                     "mics_eq_keys": [d.name for d in mics_eq_dims(xa, amp)],
                     "effects": per, "effect_kept": kept,
                     "mics_changed": any(xb.get(m) != start.get(m) for m in MIC_KEYS),
                     "searched_keys": sorted({d.name for d in rooms_dims(start)} | {d.name for d in mics_eq_dims(xa, amp)}
                                             | {d.name for _, ds, _ in effect_plan(amp).values() for d in ds}
                                             | {"/".join(sw) for sw, _, _ in effect_plan(amp).values() if sw != SPRING_KEY}),
                     "fresh": fr, "drift": drifted(dry["start"]["peak_dbfs"], fr["final"]["peak_dbfs"]),
                     "label": None if fb else LO.sdict(plugin(final, amp)), "fallback": fb,
                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{rec['key'][-70:]}: {kept or 'dry'}; renders so far {renders}", flush=True)
    print(f"C1B-SEARCH DONE {k}/{n}: {renders} renders; starts {counts}", flush=True)


def cmd_report(_args):
    from scipy import stats

    from learn import pipeline_fix as P

    P.require(PHASE)
    tq = lambda df: float(stats.t.ppf(0.95, df))          # noqa: E731
    out = {"phase": PHASE, "keep_margin": KEEP_MARGIN}
    for s in ("n12", "bks"):
        root, sub = OUT_DIRS[s]
        every = [json.loads(p.read_text()) for p in sorted((P.out_dir() / root / sub).glob("*.json"))]
        recs = [r for r in every if "refused" not in r]
        main = [r for r in recs if not r["real_out"]]
        out[s] = {"rows": report_rows(main, tq, P.clustered),
                  "real_out": report_rows([r for r in recs if r["real_out"]], tq, P.clustered),
                  "starts": {k: sum(1 for r in every if r.get("start_kind") == k)
                             for k in ("canonical", "raw_after_miss", "refused")},
                  "refused": [{"unit": r["unit"], **r["refused"]} for r in every if "refused" in r],
                  "fallbacks": sum(1 for r in recs if r["label"] is None),
                  "drift": {"main": sum(1 for r in main if r.get("drift")),
                            "real_out": sum(1 for r in recs if r["real_out"] and r.get("drift"))},
                  "nonfinite_ablations": nonfinite_ablations(recs)}
    P.save(c1b_dir() / "report.json", out)
    print(json.dumps({s: {"primary": (out[s]["rows"]["all"] or {}).get("primary"), "starts": out[s]["starts"],
                          "effects_kept": (out[s]["rows"]["all"] or {}).get("effects_kept"), "drift": out[s]["drift"],
                          "nonfinite_ablations": out[s]["nonfinite_ablations"]} for s in ("n12", "bks")},
                     indent=1, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("c1b-draw").set_defaults(fn=cmd_draw)
    s = sub.add_parser("c1b-search")
    s.add_argument("--shard", type=F.shard, default=(0, 1))
    s.set_defaults(fn=cmd_search)
    sub.add_parser("c1b-report").set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
