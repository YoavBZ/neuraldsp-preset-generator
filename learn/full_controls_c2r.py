"""Every control on the new trusted real rows, C2r (`docs/full-controls-plan.md`, "C2r and C3r in detail"; ledger
`pipeline-fix` `phase_c2r`). Labels, not a measurement: C2's per-record recipe exactly as declared and amended (C1a's
search at budget 200, C1b's stages A and B, the fresh final, the near-silent guard with its constrained bests, the
systematic-miss guard, no effect stage) on three blocks of trusted rows that no product model trains on yet:

- `cap1`: TONE3000 batch 1's labelled trusted units (`capture_labels.search_records()` with a label), each from its
  stored label;
- `n12`: batch 2's C1a records (`captures2/search-c1a/`), continued to 200 exactly as C2's C1a block, a record refused
  for an inexact replay keeping its C1b record;
- `panel`: 5D's lagged read units less those whose bleed residual is above BKS's reamps' maximum, each first given
  step 0 (the stored labels' own recipe: arm A's main stage, `K.space`, from the class's S, on its stored halves and
  lag), one forced amp a unit balanced within class.

    .venv/bin/python -m learn.full_controls_c2r c2r-draw                 # the records (zero renders)
    .venv/bin/python -m learn.full_controls_c2r c2r-search --shard 0/3   # the searches (renders; at most 3 shards)
    .venv/bin/python -m learn.full_controls_c2r c2r-report               # the rows (zero renders)
    .venv/bin/python -m learn.full_controls_c2r c2r-ceiling-check        # step 0 against 5D's ceiling (zero renders)

C2's search loop runs the records unchanged (`full_controls_c2.cmd_search` with this module's `Shard`); this module
adds the records, the panel's step 0 and the report. The pure parts are unit-tested; the search on a stub renderer.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time

from learn import full_controls as F
from learn import full_controls_c2 as X

PHASE = "phase_c2r"
BLOCKS = ("cap1", "n12", "panel")    # the order
OUT_DIRS = {"cap1": ("captures", "search-c2r"), "n12": ("captures2", "search-c2r"), "panel": ("panel", "search-c2r")}
PLAN = "docs/full-controls-plan.md"
PANEL_AMP_SEED = 20261151            # the panel's forced amps: a seeded order within class
STEP0_EVALS = 52                     # arm A's main stage: round(150 x 0.35) distinct settings (`arm_a_levers`)
STEP0_RENDERS = 1 + STEP0_EVALS      # its priming render and its evaluations
KNOWN_WHY_CAP = ("off by source: NAM captures carry no time effect, and the sources are mono (no doubler); not "
                 "searched and not a learned label")
KNOWN_WHY_PANEL = ("none recorded: the panel's amp tracks are real recordings and may carry an amp's spring or a "
                   "pedal's delay; C3 masks every effect head on real rows anyway")


def c2r_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "c2r"


def fname(rec):
    """A record's file name: the panel's own convention (`panel_fname`, spaces too), else `full_controls.fname`."""
    from learn import pipeline_fix as P

    return (P.panel_fname if rec["set"] == "panel" else F.fname)(rec["key"])


def out_path(rec, step1=False):
    from learn import pipeline_fix as P

    root, sub = OUT_DIRS[rec["set"]]
    d = P.out_dir() / root / sub
    return (d / "step1" if step1 else d) / f"{fname(rec)}.json"


def step0_path(rec):
    from learn import pipeline_fix as P

    root, sub = OUT_DIRS["panel"]
    return P.out_dir() / root / sub / "step0" / f"{fname(rec)}.json"


# --- records (zero renders) ---------------------------------------------------------------------------------------------

def cap1_records(labelled, units, real_out, source):
    """Batch 1's labelled trusted records -> C2r's, one forced amp a unit as stored, clustered by DI (`di`, GOAT's item
    naming) with the creator beside. labelled: [stored record]; units: {unit: unit dict}; source(key) -> path."""
    out = []
    for r in labelled:
        prt = units[r["unit"]]
        key = f"{r['unit']}|{r['amp']}"
        out.append({"set": "cap1", "block": "cap1", "key": key, "unit": r["unit"], "amp": r["amp"], "cls": r["cls"],
                    "cluster": prt["di"], "creator": prt["creator"], "fold_stored": prt["fold"],
                    "source": str(source(key)), "prt": prt, "real_out": r["unit"] in real_out})
    return out


def cap1_left_out(stored, kept):
    """Batch 1's gated search records C2r leaves out, with why (no label: the stored record's own reason)."""
    out = []
    for r in stored:
        key = f"{r['unit']}|{r['amp']}"
        if key in kept:
            continue
        why = r.get("why") or ("fallback: " + str((r.get("best") or {}).get("fallback")) if r.get("label") is None
                               else "not among the trusted labelled units")
        out.append({"key": key, "block": "cap1", "why": why})
    return out


def n12_block(c1a_recs, outputs, units, c1b_path):
    """Batch 2's C1a records continued to 200, as C2's C1a block (`full_controls_c2.c1a_block`), clustered by DI with the
    creator beside; `c1b_path(key)` is the C1b record C3r takes on a fallback. -> (records, left out)."""
    recs, left = X.c1a_block(c1a_recs, outputs)
    out = []
    for r in recs:
        prt = units[r["unit"]]
        out.append(dict(r, block="n12", cluster=prt["di"], creator=prt["creator"], fold_stored=prt["fold"],
                        c1b_record=str(c1b_path(r["key"]))))
    return out, [dict(x, block="n12") for x in left]


def high_bleed(u, cap):
    """A panel window whose measured bleed residual is above `cap` (BKS's reamps' maximum)."""
    b = u.get("bleed_db")
    return b is not None and float(b) > cap


def bleed_tracks(units, cap):
    """The amp tracks (`amp_file`) with any measured window above `cap`: bleed is the mic's in the room, so a track
    measured above the bound in one window is out in all of them, its unmeasured windows included. units: every panel
    unit that has a bleed measure or not (5D's units.json). -> {amp_file: the worst measured window's residual}."""
    out = {}
    for u in units:
        if high_bleed(u, cap):
            out[u["amp_file"]] = max(out.get(u["amp_file"], -math.inf), float(u["bleed_db"]))
    return out


def panel_amps(units, ceiling, amps, seed=PANEL_AMP_SEED):
    """One forced amp a panel unit, balanced within class: a ceiling unit keeps its ceiling amp; the others, in a seeded
    order within their class, each take the amp with the fewest units of that class so far, ties to the first of
    `amps`. units: [unit dict]; ceiling: {unit: amp}. -> {unit: amp}."""
    out = {}
    for cls in sorted({u["cls"] for u in units}):
        mine = sorted(u["unit"] for u in units if u["cls"] == cls)
        n = {a: 0 for a in amps}
        for u in mine:
            if u in ceiling:
                out[u] = ceiling[u]
                n[ceiling[u]] += 1
        rest = [u for u in mine if u not in ceiling]
        random.Random(f"{seed}|{cls}").shuffle(rest)
        for u in rest:
            a = min(amps, key=lambda a_: (n[a_], amps.index(a_)))
            out[u] = a
            n[a] += 1
    return out


def panel_records(units, halves, ceiling, amps, real_out, cap, every=None):
    """The panel's records: the lagged read units less every unit on an amp track with a measured window above the bound
    (`bleed_tracks` over `every`, 5D's units; default `units`), on their forced amps (`panel_amps`), clustered by DI with
    the band beside; `halves` are 5D's as stored (dealt over every lagged unit, never re-dealt here); their source is
    step 0's record. -> (records, left out with why)."""
    from learn import pipeline_fix as P

    bad = bleed_tracks(units if every is None else every, cap)
    keep = [u for u in units if u["amp_file"] not in bad]
    left = [{"key": u["unit"], "block": "panel",
             "why": (f"its amp track has a window with bleed residual {bad[u['amp_file']]:.2f} dB above BKS's reamps' "
                     f"maximum {cap} dB" + ("" if high_bleed(u, cap) else " (this window unmeasured)")
                     + " (trusted data only)")}
            for u in units if u["amp_file"] in bad]
    forced = panel_amps(keep, ceiling, amps)
    out = []
    for u in keep:
        a = forced[u["unit"]]
        rec = {"set": "panel", "block": "panel", "key": P.real_key(u, a), "unit": u["unit"], "amp": a, "cls": u["cls"],
               "cluster": u["di"], "band": u["band"], "fold_stored": u["fold"], "search": halves[u["unit"]],
               "ceiling_amp": ceiling.get(u["unit"]), "prt": u, "real_out": u["unit"] in real_out}
        rec["source"] = str(step0_path(rec))
        out.append(rec)
    return out, left


def order(records):
    """By block (`BLOCKS`), then by key."""
    return sorted(records, key=lambda r: (BLOCKS.index(r["block"]), r["key"]))


def shard_records(records, k, n):
    """Shard k of n: a round robin over `order`, so every shard takes each block in turn."""
    return [r for j, r in enumerate(order(records)) if j % n == k]


def renders_upper(recs):
    """At most, on the canonical path: C2's per record (`full_controls_c2.renders_upper`, the n12 block as its C1a
    block), plus step 0's priming and evaluations on the panel."""
    n = 0
    for r in recs:
        n += X.renders_upper([dict(r, block="c1a") if r["block"] == "n12" else r])
        if r["block"] == "panel":
            n += STEP0_RENDERS
    return n


def known(rec):
    """-> (the keys recorded off by source, why): the captures as C2's GOAT (dry, mono); the panel none."""
    if rec["set"] == "panel":
        return {}, KNOWN_WHY_PANEL
    return X.known_keys(rec["amp"]), KNOWN_WHY_CAP


def ceiling_check(step0, ceiling_rec):
    """Step 0 on a 5D ceiling unit's own amp and half against the stored ceiling search (same recipe, seed and
    priming): its best's settings and both halves' judge, exact. -> dict (None when there is no ceiling record)."""
    if ceiling_rec is None:
        return None
    a, b = step0["best"], ceiling_rec["best"]
    same_half = step0["search"] == ceiling_rec["search"] and step0["lag"] == ceiling_rec["lag"]
    return {"same_half_and_lag": same_half, "same_settings": a["settings"] == b["settings"],
            "same_judge": a["judge"] == b["judge"], "evaluations": [step0["evaluations"], ceiling_rec["evaluations"]]}


# --- the loop's shard (C2's search loop, C2r's records) -----------------------------------------------------------------

class Shard(X.Shard):
    phase = PHASE
    tag = "C2R"

    def __init__(self):
        self._ms = None

    def mine(self, k, n):
        return shard_records(json.loads((c2r_dir() / "records.json").read_text())["records"], k, n)

    def out_path(self, rec, step1=False):
        return out_path(rec, step1)

    def continued(self, rec):
        return rec["block"] == "n12"

    def known(self, rec):
        return known(rec)

    def extra(self, rec):
        e = {"creator": rec.get("creator"), "band": rec.get("band"), "fold_stored": rec.get("fold_stored")}
        if rec["block"] == "panel":
            e["step0"] = rec["source"]
        return e

    def prepare(self, rec):
        if rec["block"] != "panel":
            return 0, None
        p = step0_path(rec)
        used = 0
        if not p.exists():
            used = step0(rec, self.menu())
        s0 = json.loads(p.read_text())
        if s0.get("label") is not None:
            return used, None
        return used, {"plan": PLAN, "ledger": s0.get("ledger"), "set": rec["set"], "block": rec["block"],
                      "unit": rec["unit"], "amp": rec["amp"], "cls": rec["cls"], "cluster": rec["cluster"],
                      "band": rec.get("band"), "real_out": rec["real_out"], "step0": str(p), "label": None,
                      **({"refused": s0["refused"]} if "refused" in s0 else {}),
                      "fallback_stage": "step0", "fallback_reason": s0.get("why"),
                      "why": f"step 0 gave no label ({s0.get('why')}): the record leaves C3r's rows",
                      "time": time.strftime("%Y-%m-%d %H:%M:%S")}

    def menu(self):
        if self._ms is None:
            from learn import arm_a_levers as L
            self._ms = L.menu_S()
        return self._ms


def step0(rec, ms):
    """The panel's step 0 (renders): `cmd_panel_ceiling`'s search, the stored labels' recipe: one discarded priming
    render with S, then arm A's main stage (`K.space`, 52 evaluations, seed `arm_a_levers.SEED`) from the class's S on
    the unit's DI, judged at its stored lag on its stored search half (`panel_halves`); S's first evaluation bit-
    identical to its stored fresh render (panel/lags, phase_5d), else within `START_TOL` and flagged, else the record is
    refused. The label is the best's in-process render, none on `fallback_reason`. -> renders; writes step 0's record."""
    import numpy as np

    from learn import arm_a_levers as L
    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B

    prt, amp = rec["prt"], rec["amp"]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    lp = P.out_dir() / P.PANEL_DIR / "lags" / f"{P.panel_fname(prt['unit'])}.json"
    lag_rec = json.loads(lp.read_text())
    if lag_rec.get("phase") != "phase_5d" or lag_rec.get("status") != "ok" or lag_rec.get("lag") != prt["lag"]:
        raise SystemExit(f"{rec['key']}: its stored lag is not 5D's usable one")
    search = rec["search"]
    held = "B" if search == "A" else "A"
    sel, S = ms[amp][rec["cls"]]
    s_j, s_sha = lag_rec["s"][amp]["judge"], lag_rec["s"][amp]["render_sha256"]
    di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
    di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
    ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
    dims = K.space(amp, S)
    seen, first, curve = {}, {}, []
    base = {"plan": PLAN, "ledger": f"{P.LEDGER_ID} {PHASE}", "unit": prt["unit"], "rig": prt.get("rig"),
            "di": prt["di"], "item": None, "fold": prt.get("fold"), "band": prt["band"], "cls": rec["cls"], "amp": amp,
            "select": sel, "search": search, "held": held, "lag": prt["lag"], "item_lag": None, "s_judge": s_j,
            "s_render_sha256": s_sha, "recipe": "arm A's main stage, K.space, seed arm_a_levers.SEED, from S"}

    class Miss(Exception):
        pass

    used = 1
    rr = CB.new_renderer()
    try:
        rr.render(di32, sel, LO.tdict(LO.sdict(S)))   # the discarded priming render, as the ceiling's

        def f(x):
            nonlocal used
            y = np.asarray(rr.render(di32, sel, LO.tdict(LO.sdict(x))), np.float64)[trim[0]:trim[1]]
            used += 1
            j = K.judge(ref, y, di, prt["lag"])
            if not curve:
                first.update(sha=AM.audio_sha(y), value=j[search])
                verdict = P.first_eval_check(first["sha"], s_sha, j[search], s_j[search], F.START_TOL)
                first["verdict"] = verdict
                if verdict == "refuse":
                    raise Miss(j[search])
            seen[K.key(x)] = {"judge": j, "peak_dbfs": A.peak_dbfs(y, trim_s=0.0), "render_sha256": AM.audio_sha(y)}
            curve.append(j[search])
            return j[search]

        try:
            best_x, best_v, evals = L.main_stage(dims, S, f, seed=L.SEED)
        except Miss as m:
            P.save(step0_path(rec), {**base, "label": None, "why": "step 0's first evaluation misses S's stored render",
                                     "refused": {"first_sha": first["sha"], "s_sha": s_sha, "first_value": m.args[0],
                                                 "s_value": s_j[search], "tol": F.START_TOL},
                                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            return used
    finally:
        rr.close()
    best = dict(seen[K.key(best_x)], settings=LO.sdict(best_x))
    best["fallback"] = A.fallback_reason(best["peak_dbfs"], best["judge"][search])
    out = {**base, "s_first": first, "curve": curve, "evaluations": evals, "best_search_value": best_v, "best": best,
           "label": None if best["fallback"] else best["settings"],
           "why": None if best["fallback"] is None else f"fallback: {best['fallback']}",
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    if rec.get("ceiling_amp") == amp:
        cp = P.out_dir() / P.PANEL_DIR / "ceiling" / f"{P.panel_fname(P.real_key(prt, amp))}.json"
        out["ceiling_check"] = ceiling_check(out, json.loads(cp.read_text()) if cp.exists() else None)
    P.save(step0_path(rec), out)
    return used


# --- the report -----------------------------------------------------------------------------------------------------------

def grouped(recs, field):
    """The records with their cluster replaced by `field` (creator or band), for the group-weighted reading."""
    return [dict(r, cluster=r.get(field) or r["cluster"]) for r in recs]


GROUP = {"cap1": "creator", "n12": "creator", "panel": "band"}


# --- commands -------------------------------------------------------------------------------------------------------------

def load_records():
    """-> (records, left out, notes), at zero renders: each record's zero-render start check (C2's `start_problems`)
    on cap1 and n12, the n12 replays' exactness (C2's `replay_check`), and the panel's lags, halves and dry S."""
    from learn import arm_a_levers as L
    from learn import capture_labels as CL
    from learn import full_controls_c1b as C
    from learn import pipeline_fix as P
    from learn import score_ear as SE

    real_out = set(P.h4_exclusions()["real_out"])
    # cap1
    cdir = P.out_dir() / "captures" / P.SEARCH_DIR
    cu = {u["unit"]: u for u in CL.units_of()}
    gated = list(CL.search_records().values())
    labelled = [r for r in gated if r["label"] is not None]
    recs = cap1_records(labelled, cu, real_out, lambda key: cdir / f"{F.fname(key)}.json")
    left = cap1_left_out(gated, {r["key"] for r in recs})
    # n12
    c1a = [r for r in json.loads((F.c1a_dir() / "records.json").read_text())["records"] if r["set"] == "n12"]
    outs = {}
    for r in c1a:
        q = P.out_dir() / F.OUT_DIRS["n12"][0] / F.OUT_DIRS["n12"][1] / f"{F.fname(r['key'])}.json"
        if q.exists():
            outs[r["key"]] = dict(json.loads(q.read_text()), _path=str(q))
    wide, _, refused = SE.wide_units()
    units2 = {u["unit"]: u for u in wide}
    nb, nl = n12_block(c1a, outs, units2,
                       lambda key: P.out_dir() / C.OUT_DIRS["n12"][0] / C.OUT_DIRS["n12"][1] / f"{F.fname(key)}.json")
    left += nl + [{"key": u, "block": "n12", "why": "no C1a record: a non-finite held-half judge for S or the label "
                   "(`score_ear.wide_units`), so N12 and C1a left it out"} for u in refused]
    # panel
    units, lags = P.panel_lagged_units()
    halves = P.panel_halves(units)
    ceiling = {prt["unit"]: a for prt, a in P.panel_ceiling_units(units)}
    pb, pl = panel_records(units, halves, ceiling, list(P.AMPS3), real_out, P.PANEL_BLEED_MAX_DB,
                           every=P.panel_units())
    pl += [{"key": u, "block": "panel", "why": f"no usable 5D lag ({r['status']})"} for u, r in sorted(lags.items())
           if r["status"] != "ok"]
    ms = L.menu_S()
    ok = []
    for r in recs + nb:
        bad = X.start_problems(json.loads(open(r["source"]).read()), r["amp"], ms[r["amp"]][r["cls"]][0])
        if r["block"] == "n12":
            probs, _ = X.replay_check(outs[r["key"]], r["amp"])
            bad += [f"replay: {p}" for p in probs]
        if bad:
            left.append({"key": r["key"], "block": r["block"], "why": "; ".join(bad)})
        else:
            ok.append(r)
    for r in pb:
        wet = C.dry_start_problems(ms[r["amp"]][r["cls"]][1], r["amp"])
        if wet:
            left.append({"key": r["key"], "block": "panel", "why": f"the class's S is wet: {wet}"})
        else:
            ok.append(r)
    notes = {"panel_ceiling_units_kept": sorted(u for u in ceiling if any(r["unit"] == u for r in pb)),
             "panel_amps": {cls: {a: sum(1 for r in pb if r["cls"] == cls and r["amp"] == a) for a in P.AMPS3}
                            for cls in ("clean", "crunch")}}
    return order(ok), left + pl, notes


def cmd_draw(args):
    from learn import pipeline_fix as P

    if not args.dry_run:
        P.require(PHASE)
    path = c2r_dir() / "records.json"
    if path.exists() and not args.dry_run:
        raise SystemExit(f"{path} exists: the records are drawn once")
    recs, left, notes = load_records()
    n = {b: sum(1 for r in recs if r["block"] == b) for b in BLOCKS}
    per = {b: renders_upper([r for r in recs if r["block"] == b]) for b in BLOCKS}
    if not args.dry_run:
        from learn import arm_a_levers as L
        from learn import full_controls_c1b as C

        P.save(path, {"phase": PHASE, "budget": X.BUDGET, "seeds": {"step0": L.SEED, "step1": F.SEED, "stage_a": C.SEED,
                                                                     "stage_b": C.SEED + 1, "panel_amps": PANEL_AMP_SEED},
                      "records": recs, "left_out": left, "notes": notes, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("C2R DRAW" + (" (dry run, nothing written)" if args.dry_run else ""), n, "records,", len(left),
          "left out; renders at most", renders_upper(recs), per, flush=True)
    for x in left:
        print("  left out:", x["block"], x["key"][-70:], "-", x["why"][:140], flush=True)
    print("  notes:", json.dumps(notes), flush=True)


def cmd_search(args):
    X.cmd_search(args, shard=Shard())


def cmd_report(_args):
    from scipy import stats

    from learn import pipeline_fix as P

    P.require(PHASE)
    tq = lambda df: float(stats.t.ppf(0.95, df))          # noqa: E731
    plan = json.loads((c2r_dir() / "records.json").read_text())
    out = {"phase": PHASE, "budget": X.BUDGET, "left_out_at_draw": plan["left_out"], "notes": plan.get("notes")}
    every = {}
    for r in plan["records"]:
        p = out_path(r)
        if p.exists():
            every.setdefault(r["block"], []).append(json.loads(p.read_text()))
    for b in BLOCKS:
        recs = every.get(b, [])
        main = [r for r in recs if not r.get("real_out")]
        out[b] = {"written": len(recs), "drawn": sum(1 for r in plan["records"] if r["block"] == b),
                  "rows": X.report_rows(main, tq, P.clustered),
                  "rows_by_" + GROUP[b]: X.report_rows(grouped(main, GROUP[b]), tq, P.clustered),
                  "real_out": X.report_rows([r for r in recs if r.get("real_out")], tq, P.clustered),
                  "step1_starts": {kk: sum(1 for r in recs if (r.get("step1") or {}).get("start_gate") == kk)
                                   for kk in ("on", "off_after_miss", "refused")},
                  "step2_starts": {kk: sum(1 for r in recs if (r.get("step2") or {}).get("start_kind") == kk)
                                   for kk in ("canonical", "raw_after_miss", "refused", "not_run")},
                  "fallbacks": [{"unit": r["unit"], "amp": r["amp"], "stage": r.get("fallback_stage"),
                                 "why": r.get("fallback_reason")} for r in recs if r.get("fallback_stage")],
                  "quiet": [r["unit"] + "|" + r["amp"] for r in recs if r.get("quiet")],
                  "drift": [r["unit"] + "|" + r["amp"] for r in recs if r.get("drift")],
                  "no_finite_final": X.no_finite_final(recs),
                  "refused": [{"unit": r["unit"], "amp": r["amp"], **r["refused"]} for r in recs if "refused" in r]}
    s0 = []
    for r in plan["records"]:
        if r["block"] == "panel" and step0_path(r).exists():
            s = json.loads(step0_path(r).read_text())
            s0.append({"unit": r["unit"], "amp": r["amp"], "label": s.get("label") is not None,
                       "first": (s.get("s_first") or {}).get("verdict"), "ceiling_check": s.get("ceiling_check")})
    out["panel"]["step0"] = s0
    P.save(c2r_dir() / "report.json", out)
    print(json.dumps({b: {"written": out[b]["written"], "drawn": out[b]["drawn"],
                          "primary": (out[b]["rows"]["all"] or {}).get("primary"),
                          "step1_starts": out[b]["step1_starts"], "step2_starts": out[b]["step2_starts"],
                          "counts": (out[b]["rows"]["all"] or {}).get("counts"),
                          "no_finite_final": len(out[b]["no_finite_final"])} for b in BLOCKS},
                     indent=1, default=str))


def cmd_ceiling_check(_args):
    """Zero renders: does 5D's stored ceiling search use step 0's recipe? Its code path (`cmd_panel_ceiling`: priming
    with S, `K.space`, `arm_a_levers.main_stage` at `arm_a_levers.SEED`, the first evaluation bit-identical to S's stored
    render), and its records against the kept panel units, their halves, lags and forced amps."""
    import inspect

    from learn import arm_a_levers as L
    from learn import pipeline_fix as P

    src = inspect.getsource(P.cmd_panel_ceiling)
    code = {"main_stage_at_L_SEED": "L.main_stage(dims, S, f, seed=L.SEED)" in src,
            "space_K_space_from_S": "dims = K.space(amp, S)" in src,
            "primed_with_S": "rr.render(di32, sel, LO.tdict(LO.sdict(S)))" in src,
            "first_eval_bit_identical": "first evaluation is not bit-identical to its fresh render" in src,
            "seed": L.SEED}
    units, _ = P.panel_lagged_units()
    halves = P.panel_halves(units)
    rows = []
    for prt, amp in P.panel_ceiling_units(units):
        cp = P.out_dir() / P.PANEL_DIR / "ceiling" / f"{P.panel_fname(P.real_key(prt, amp))}.json"
        c = json.loads(cp.read_text()) if cp.exists() else None
        rows.append({"unit": prt["unit"], "amp": amp,
                     "kept": prt["amp_file"] not in bleed_tracks(P.panel_units(), P.PANEL_BLEED_MAX_DB),
                     "record": c is not None, "evaluations": (c or {}).get("evaluations"),
                     "same_half": (c or {}).get("search") == halves[prt["unit"]],
                     "same_lag": (c or {}).get("lag") == prt["lag"]})
    print(json.dumps({"code": code, "ceiling": rows}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("c2r-draw")
    d.add_argument("--dry-run", action="store_true", help="count and check only; write nothing")
    d.set_defaults(fn=cmd_draw)
    s = sub.add_parser("c2r-search")
    s.add_argument("--shard", type=F.shard, default=(0, 1))
    s.set_defaults(fn=cmd_search)
    sub.add_parser("c2r-report").set_defaults(fn=cmd_report)
    sub.add_parser("c2r-ceiling-check").set_defaults(fn=cmd_ceiling_check)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
