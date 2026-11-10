"""C3r (`docs/full-controls-plan.md`, "C2r and C3r in detail"; ledger `pipeline-fix` `phase_c3r`): C3's recipe on every
trusted real row, trained and read by rotation. Two arms: R-all (GOAT's and BKS's rows on C2's labels, plus cap1, n12 and
the panel on C2r's) and R-ctl (the same folds, drops and validation rows without the new rows). Four folds: GOAT's and
BKS's FTm folds, cap1's stored creator folds, n12's stored creator folds (a creator shared with batch 1 takes batch 1's
fold), the panel's by band. Model k leaves out every row sharing a DI file or a capture creator with a fold-k unit; inner
run k leaves out folds k and j = (k + 1) mod 4 and every row sharing either.

The training is `pipeline_fix train-ft --masked --ft-cap 300 --c3r ARM` (C3's recipe; this module gives the rows, the
labels, the masks and the checks). The read and the rule are this module's:

    .venv/bin/python -m learn.full_controls_c3r c3r-folds                 # folds and drops, counted (zero renders)
    .venv/bin/python -m learn.full_controls_c3r c3r-check                 # C2, C2r, C3's decision, inputs (zero renders)
    $TORCH_PY -m learn.full_controls_c3r c3r-predict --arm all            # the answers (zero renders, CPU)
    .venv/bin/python -m learn.full_controls_c3r c3r-render --shard 0/3    # the answers' renders (renders)
    .venv/bin/python -m learn.full_controls_c3r c3r-report                # the rows and the adoption (zero renders)

The pure parts (the folds, the drops, the sources, the rows, the pooled interval and the rule) are unit-tested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time

PHASE = "phase_c3r"
ARMS = ("all", "ctl")
SETS = ("bks", "goat", "cap1", "n12", "panel")
NEW_SETS = ("cap1", "n12", "panel")
CAPTURE_SETS = ("goat", "cap1", "n12")                 # the captures source; BKS and the panel are real amps
DECIDING = ("bks", "goat", "panel")                    # with the pooled row, the sets whose "shown worse" decides
BASE = {("all", "c3"): "C3r-all", ("ctl", "c3"): "C3r-ctl", ("all", "ftm"): "C3r-allK", ("ctl", "ftm"): "C3r-ctlK"}
FOLDS = 4
PER_EPOCH = 300                                        # each source cycled to at least this, as FT's REAL/GOAT_PER_EPOCH
MIX_SEED = 20261152                                    # each source's order before cycling: one seed per run and source
OUT = "c3r"


def c3r_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT


# --- the folds (pure) -----------------------------------------------------------------------------------------------------

def band_folds(counts, k=FOLDS):
    """The panel's folds by band: bands largest first (then by name), each to the fold with the fewest panel units so
    far, ties to the lowest fold. counts: {band: units}. -> {band: fold}."""
    n = [0] * k
    out = {}
    for b in sorted(counts, key=lambda b_: (-counts[b_], b_)):
        f = min(range(k), key=lambda q: (n[q], q))
        out[b] = f
        n[f] += counts[b]
    return out


def creator_folds(units2, fold1):
    """n12's folds: each unit its stored creator fold, unless its creator is in batch 1, whose fold it then takes.
    units2: [unit dict with creator, fold]; fold1: {creator: fold} (batch 1's, one fold a creator). -> {unit: fold}."""
    return {u["unit"]: fold1.get(u["creator"], u["fold"]) for u in units2}


def batch1_creator_folds(units1):
    """{creator: fold} over batch 1's units; refuses a creator on two folds (creator folds hold a creator whole)."""
    out = {}
    for u in units1:
        if out.setdefault(u["creator"], u["fold"]) != u["fold"]:
            raise SystemExit(f"{u['creator']}: a batch 1 creator on two folds")
    return out


def entry(set_, unit, fold, di, creator=None, band=None, row=True):
    """One rotation unit: its set, fold and identities (its DI file, and a capture's creator). `row` False: a read unit
    with no training row (it still holds its identities out of its fold's models)."""
    ids = {("di", di)} | ({("creator", creator)} if creator else set())
    return {"set": set_, "unit": unit, "fold": fold, "di": di, "creator": creator, "band": band, "ids": ids, "row": row}


def split(ents, k, inner, arm):
    """Which units a model trains on and holds. FT_k (inner False): held fold k; training the other folds' units with a
    row, less every one sharing an identity with a fold-k unit. Inner run k: held (its validation) fold j = (k + 1) mod 4;
    training the folds other than k and j, less every unit sharing an identity with a unit of fold k or j. k None: the
    all-labels model, every unit with a row, nothing held. Arm "ctl" trains on BKS and GOAT only; the held units are
    the same in both arms. -> (training entries, held entries, dropped entries)."""
    if k is None:
        if inner:
            raise SystemExit("an inner run needs a fold")
        tr = [e for e in ents if e["row"] and (arm == "all" or e["set"] not in NEW_SETS)]
        return tr, [], []
    out_f = {k, (k + 1) % FOLDS} if inner else {k}
    hf = (k + 1) % FOLDS if inner else k
    banned = set().union(*[e["ids"] for e in ents if e["fold"] in out_f]) if ents else set()
    held = [e for e in ents if e["fold"] == hf and e["row"]]
    cand = [e for e in ents if e["fold"] not in out_f and e["row"] and (arm == "all" or e["set"] not in NEW_SETS)]
    tr = [e for e in cand if not (e["ids"] & banned)]
    return tr, held, [e for e in cand if e["ids"] & banned]


def drop_counts(ents, arm):
    """Per FT_k and inner run: the records (rows before cycling; an entry's `n`, else 1) trained, held and dropped, by
    set, and the units. -> {name: {"train", "held", "dropped": {set: rows, "all": rows}, "units": {...}}}."""
    out = {}
    for inner in (False, True):
        for k in range(FOLDS):
            tr, held, dr = split(ents, k, inner, arm)
            cnt = {"units": {}}
            for tag, xs in (("train", tr), ("held", held), ("dropped", dr)):
                cnt[tag] = {s: sum(e.get("n", 1) for e in xs if e["set"] == s) for s in SETS}
                cnt[tag]["all"] = sum(e.get("n", 1) for e in xs)
                cnt["units"][tag] = len(xs)
            out[f"{'inner' if inner else 'FT'}_k{k}"] = cnt
    return out


# --- the sources and labels (pure on loaded records) ----------------------------------------------------------------------

def new_source(set_, out, stored, c1b=None, c1a=None, step0_label=None):
    """A new row's training label: C2r's own if it has one; else cap1 its stored label, n12 its C1b record when usable
    (else its stored v2 label), the panel step 0's best (None when step 0 gave none: the record leaves the rows).
    -> source dict (C3's kinds: "c2", "c1b", "stored") or None."""
    from learn import full_controls_c3 as C3

    if out is None:
        raise SystemExit("a C2r record with no output: C2r is not complete")
    if out.get("label") is not None:
        return {"kind": "c2", "label": out["label"], "searched": list(out.get("searched_keys") or [])}
    if set_ == "n12":
        return C3.choose_source(out, "c1a", c1b, c1a, stored)
    if set_ == "cap1":
        if not stored or stored.get("label") is None:
            raise SystemExit("a cap1 record with neither a C2r label nor a stored one")
        return {"kind": "stored", "label": stored["label"]}
    if set_ == "panel":
        return None if step0_label is None else {"kind": "stored", "label": step0_label}
    raise ValueError(set_)


def stored_source(label):
    """FTm's recipe (the fallback when C3 is shown worse than FTm): the record's `K.space` label, `K.space`'s mask."""
    return None if label is None else {"kind": "stored", "label": label}


def mixed(recs, seed):
    """A source's records in the order its cycling shows them: each set's records shuffled with `seed`, then the sets
    interleaved in proportion (the j-th of a set's n at position (j + 0.5) / n, ties in set order), so every prefix
    holds each set within one record of its share. Cycled to 300 (`cycled_to`), each record is shown k or k + 1 times
    an epoch and each set's showings are within one row of its share of the records, whatever the sets' order in the
    list. (FTm's and C3's sources hold one set each; their own paths are unchanged.)"""
    import random

    by, order = {}, []
    for r in recs:
        if r["set"] not in by:
            order.append(r["set"])
        by.setdefault(r["set"], []).append(r)
    keyed = []
    for si, s_ in enumerate(order):
        xs = list(by[s_])
        random.Random(f"{seed}|{s_}").shuffle(xs)
        keyed += [((j + 0.5) / len(xs), si, j, x) for j, x in enumerate(xs)]
    return [x for *_, x in sorted(keyed, key=lambda t: t[:3])]


def mix_seed(arm, k, inner, source):
    """The fixed seed of one run's source order: from MIX_SEED, per (arm, fold, inner, source)."""
    return f"{MIX_SEED}|{arm}|{k}|{bool(inner)}|{source}"


def showings(recs, n=PER_EPOCH):
    """How often each set is shown an epoch when `recs` (in order) are cycled to at least n. -> {set: showings}."""
    out = {}
    for r in cycled_to(recs, n):
        out[r["set"]] = out.get(r["set"], 0) + 1
    return out


def cycled_to(recs, n=PER_EPOCH):
    """A source's training records cycled to at least n (a longer list kept whole), as FT's `dfix_records`."""
    from learn import pipeline_fix as P

    return P.cycled(recs, max(n, len(recs)))


# --- the pooled interval and the rule (pure) ------------------------------------------------------------------------------

def pooled(rows):
    """The sets weighted equally: the mean of the set means, its standard error from the sets' cluster standard errors
    (`full_controls_c3.se_of`), Welch-Satterthwaite's df, a 90% t interval. rows: {set: row}. -> dict or None."""
    from learn import full_controls_c3 as C3
    from learn import pipeline_fix as P

    ses = {s: C3.se_of(r) for s, r in rows.items()}
    if not rows or any(v is None for v in ses.values()) or any(r.get("mean") is None for r in rows.values()):
        return None
    n = len(rows)
    m = sum(r["mean"] for r in rows.values()) / n
    v = sum(se ** 2 for se, _ in ses.values()) / n ** 2
    if v == 0:
        return {"mean": m, "lo90": m, "hi90": m, "df": None, "sets": n}
    df = sum(se ** 2 for se, _ in ses.values()) ** 2 / sum(se ** 4 / d for se, d in ses.values())
    h = P.t95(max(1, int(math.floor(df)))) * math.sqrt(v)
    return {"mean": m, "lo90": m - h, "hi90": m + h, "df": df, "sets": n}


def adoption(rows):
    """R-all replaces C3's adopted model unless R-all - R-ctl is shown worse (its 90% interval wholly above 0) on the
    deciding pool (BKS, GOAT and the panel, weighted equally: their DI files are disjoint) or on BKS, GOAT or the panel
    alone. The five-set pool is reported beside, not deciding (cap1 and n12 lean towards R-all by design, and cap1
    shares GOAT's DI files, so independent set variances would make its interval too narrow). rows: {set: row}."""
    from learn import full_controls_c3 as C3

    dp = pooled({s: rows[s] for s in DECIDING}) if all(rows.get(s) for s in DECIDING) else None
    five = pooled({s: rows[s] for s in SETS}) if all(rows.get(s) for s in SETS) else None
    worse = {s: C3.shown_worse(rows.get(s)) for s in DECIDING}
    worse["deciding_pool"] = C3.shown_worse(dp)
    missing = [s for s in DECIDING if C3.se_of(rows.get(s)) is None]
    if dp is None or dp.get("lo90") is None or dp.get("hi90") is None:
        missing.append("deciding_pool")
    why = None if not missing else (f"no interval on {', '.join(missing)}: the read is incomplete, so the rule does "
                                    "not decide")
    return {"deciding_pool": dp, "five_set_pool": five, "shown_worse": worse,
            "replaces_c3": None if missing else not any(worse.values()), "complete": not missing, "why": why}


# --- the state (zero renders) ---------------------------------------------------------------------------------------------

def c2r_state(partial=False):
    """C2r's records and outputs, one sha256 over records.json and every output in order; refuses unless all are
    written (`partial` lets a check read what exists)."""
    from learn import full_controls_c2r as R

    rp = R.c2r_dir() / "records.json"
    if not rp.exists():
        if not partial:
            raise SystemExit(f"{rp}: C2r is not drawn")
        recs = R.load_records()[0]                     # a zero-render check before C2r's draw: its records as drawn
        return {"sha256": None, "written": 0, "records": recs, "outputs": {}, "drawn": False}
    recs = json.loads(rp.read_text())["records"]
    missing = [r["key"] for r in recs if not R.out_path(r).exists()]
    if missing and not partial:
        raise SystemExit(f"C2r is not complete: {len(recs) - len(missing)} of {len(recs)} written (first missing "
                         f"{missing[0]})")
    h = hashlib.sha256(rp.read_bytes())
    outs = {}
    for r in recs:
        p = R.out_path(r)
        if p.exists():
            b = p.read_bytes()
            h.update(r["key"].encode() + b"\0" + b)
            outs[r["key"]] = json.loads(b)
    return {"sha256": h.hexdigest(), "written": len(outs), "records": recs, "outputs": outs, "drawn": True}


def decision():
    """C3's final decision (`full_controls_c3 c3-adopt --final`): -> (recipe "c3" or "ftm", the answer's tag, record)."""
    from learn import full_controls_c3 as C3

    p = C3.c3_dir() / "decision.json"
    if not p.exists():
        raise SystemExit(f"{p}: C3's adoption decision is not made (c3-adopt --final)")
    d = json.loads(p.read_text())
    return ("c3" if d.get("replaces_ftm") else "ftm"), d["tag"], d


_CACHE = {}


def state(partial=False):
    """Everything C3r's rows and reads need, at zero renders (cached per process): the rotation entries, every record
    with its training source, the unit dicts, the recipe and the hashes."""
    key = ("state", partial)
    if key in _CACHE:
        return _CACHE[key]
    from learn import capture_labels as CL
    from learn import full_controls_c3 as C3
    from learn import pipeline_fix as P
    from learn import score_ear as SE

    c2 = C3.c2_state(partial)
    c2r = c2r_state(partial)
    try:
        recipe, tag, dec = decision()
    except SystemExit:
        if not partial:
            raise
        recipe, tag, dec = "c3", None, None
    brecs, by_unit, bfolds = P.real_labels(2)
    grecs, gunits, _ = P.goat_labels()
    cu1 = {u["unit"]: u for u in CL.units_of()}
    wide, _, _ = SE.wide_units()
    cu2 = {u["unit"]: u for u in wide}
    panel_units = {u["unit"]: u for u in P.panel_lagged_units()[0]}
    units = {"bks": by_unit, "goat": gunits, "cap1": cu1, "n12": cu2, "panel": panel_units}
    # the training sources, keyed (unit, amp)
    src, rec_set = {}, {}
    c3src = C3.sources(c2)
    for r in c2["records"]:
        s = r["set"]
        if (r["unit"], r["amp"]) not in c3src:
            continue
        if recipe == "c3":
            src[(r["unit"], r["amp"])] = dict(c3src[(r["unit"], r["amp"])], set=s)
        else:
            src[(r["unit"], r["amp"])] = dict(stored_source(json.loads(open(r["source"]).read())["label"]),
                                              block=r["block"], key=r["key"], set=s)
        rec_set[(r["unit"], r["amp"])] = s
    lifted = []
    for r in c2r["records"]:
        if r["set"] == "n12":                          # F69's "measurement only", lifted here by phase_c3r
            lifted.append(lift_measurement_only(json.loads(open(r["c1a_output"]).read()), r["key"]))
        o = c2r["outputs"].get(r["key"])
        if o is None:
            continue
        s = r["set"]
        stored = json.loads(open(r["source"]).read()) if (o.get("label") is None or recipe == "ftm") \
            and pathlib_exists(r["source"]) else None
        if recipe == "ftm":
            got = stored_source((stored or {}).get("label"))
        else:
            c1b = c1a = None
            if s == "n12" and o.get("label") is None:
                c1b = json.loads(open(r["c1b_record"]).read()) if pathlib_exists(r["c1b_record"]) else None
                c1a = json.loads(open(r["c1a_output"]).read())
            got = new_source(s, o, stored, c1b, c1a, (stored or {}).get("label") if s == "panel" else None)
        if got is not None:
            src[(r["unit"], r["amp"])] = dict(got, block=r["block"], key=r["key"], set=s)
            rec_set[(r["unit"], r["amp"])] = s
    # the folds and the rotation entries: every drawn record's unit (a row when it has a training source)
    drawn = [(r["unit"], r["set"]) for r in c2["records"]] + [(r["unit"], r["set"]) for r in c2r["records"]]
    n_rec = {}
    for u, _ in drawn:
        n_rec[u] = n_rec.get(u, 0) + 1
    # a row: a unit with a training source; before C2 and C2r are written (`partial`), every drawn unit, since C3's
    # fallbacks give every C2 record a label and C2r's leave out only a panel record whose step 0 gives none
    has_row = set(n_rec) if partial else {u for (u, _) in src}
    fold1 = batch1_creator_folds([cu1[u] for u, s in drawn if s == "cap1"])
    f2 = creator_folds([cu2[u] for u, s in drawn if s == "n12"], fold1)
    bands = {}
    for u in sorted({u for u, s in drawn if s == "panel"}):
        bands[panel_units[u]["band"]] = bands.get(panel_units[u]["band"], 0) + 1
    fb = band_folds(bands)
    ents, seen = [], set()
    for u, s in sorted(set(drawn)):
        if u in seen:
            continue
        seen.add(u)
        prt = units[s][u]
        row = u in has_row
        n_r = n_rec[u] if partial else sum(1 for (q, _) in src if q == u)
        if s == "bks":
            ents.append(entry(s, u, bfolds[prt["di"]], prt["di"], row=row))
        elif s == "goat":
            ents.append(entry(s, u, prt["fold"], prt["di"], row=row))
        elif s == "cap1":
            ents.append(entry(s, u, prt["fold"], prt["di"], creator=prt["creator"], row=row))
        elif s == "n12":
            ents.append(entry(s, u, f2[u], prt["di"], creator=prt["creator"], row=row))
        else:
            ents.append(entry(s, u, fb[prt["band"]], prt["di"], band=prt["band"], row=row))
        ents[-1]["n"] = n_r
        ents[-1]["player"] = player_of(s, prt)
    for prt in P.goat_read_units():                    # read-only GOAT units: their identities stay in their fold
        if prt["unit"] not in seen:
            seen.add(prt["unit"])
            ents.append(entry("goat", prt["unit"], prt["fold"], prt["di"], row=False))
            ents[-1]["n"], ents[-1]["player"] = 0, player_of("goat", prt)
    out = {"c2": c2, "c2r": c2r, "recipe": recipe, "answer_tag": tag, "decision": dec, "sources": src,
           "rec_set": rec_set, "units": units, "entries": ents, "band_folds": fb, "n12_folds": f2,
           "measurement_only_lifted": {"phase": PHASE, "records": sorted(lifted)},
           "records": {"bks": brecs, "goat": grecs}, "sha256": None if partial else hashlib.sha256(
               (c2["sha256"] + c2r["sha256"] + json.dumps(dec, sort_keys=True)).encode()).hexdigest()}
    _CACHE[key] = out
    return out


def lift_measurement_only(c1a_out, key):
    """N12's records were measurement only (F69: never training rows). C3r lifts that, explicitly and only for them: the
    check stays, and a record that is not marked so (or any other set's record marked so) refuses. -> key."""
    if c1a_out.get("set") != "n12" or c1a_out.get("measurement_only") is not True:
        raise SystemExit(f"{key}: an n12 record not marked measurement only, or another set's: the lift is n12's alone")
    return key


def player_of(set_, prt):
    """The band or GOAT player a unit's DI belongs to (a capture's DI: its `player`; GOAT's: its band less "GOAT "). For
    the read's split of cap1 and n12 by whether their DI's band trains in the held unit's model."""
    if set_ in ("cap1", "n12"):
        p = prt.get("player")
        return f"GOAT {p}" if set_ == "cap1" and p and not str(p).startswith("GOAT ") else p
    return prt.get("band")


def pathlib_exists(p):
    import pathlib

    return p is not None and pathlib.Path(p).exists()


def records_of(st, units_by_set):
    """The (unit, amp) records of the given units, per source in FT's order: real amps BKS (`real_labels` order) then
    the panel; captures GOAT (`goat_labels` order), cap1, n12 (by key). -> {"real_amps": [rec], "captures": [rec]}."""
    want = {s: set(us) for s, us in units_by_set.items()}
    src = st["sources"]
    out = {"real_amps": [], "captures": []}
    for s, base in (("bks", st["records"]["bks"]), ("goat", st["records"]["goat"])):
        for r in base:
            if r["unit"] in want.get(s, ()) and (r["unit"], r["amp"]) in src:
                out["real_amps" if s == "bks" else "captures"].append({"unit": r["unit"], "amp": r["amp"], "set": s})
    for s in ("panel", "cap1", "n12"):
        for (u, a), q in sorted(st["rec_set"].items()):
            if q == s and u in want.get(s, ()):
                out["real_amps" if s == "panel" else "captures"].append({"unit": u, "amp": a, "set": s})
    return out


def rows_for(arm, k, inner, st=None):
    """C3r's real rows for one run, in `pipeline_fix`'s row layout: training rows cycled per source (real amps from
    REAL_ROW0, captures from GOAT_ROW0), the held units' records once each (ids + DFIX_HELD0). -> (training rows, held
    rows, info)."""
    from learn import full_controls_c3 as C3
    from learn import pipeline_fix as P

    st = st or state()
    tr, held, dropped = split(st["entries"], k, inner, arm)

    def by_set(es):
        out = {}
        for e in es:
            out.setdefault(e["set"], []).append(e["unit"])
        return out
    trr, hdr = records_of(st, by_set(tr)), records_of(st, by_set(held))
    merged = {}
    for s in SETS:
        merged.update(st["units"][s])
    label_of = C3.label_fn(st["sources"])
    rows, held_rows = [], []
    trr = {name: mixed(v, mix_seed(arm, k, inner, name)) for name, v in trr.items()}   # no set favoured by its place
    for name, row0 in (("real_amps", P.REAL_ROW0), ("captures", P.GOAT_ROW0)):
        rows += P.record_rows(cycled_to(trr[name]), merged, row0, label_of)
        held_rows += P.record_rows(hdr[name], merged, row0 + P.DFIX_HELD0, label_of)
    if max([len(cycled_to(trr[n])) for n in trr] + [len(hdr[n]) for n in hdr]) >= P.DFIX_HELD0:
        raise SystemExit("C3r's real row ids would collide")
    info = {"arm": arm, "fold": k, "inner": inner, "recipe": st["recipe"], "c3r_sha256": st["sha256"],
            "c2_sha256": st["c2"]["sha256"], "c2r_sha256": st["c2r"]["sha256"],
            "train_units": {s: len(v) for s, v in by_set(tr).items()},
            "held_units": {s: len(v) for s, v in by_set(held).items()},
            "dropped_units": {s: len(v) for s, v in by_set(dropped).items()},
            "train_records": {n: len(v) for n, v in trr.items()},
            "train_rows": {n: len(cycled_to(v)) for n, v in trr.items()},
            "showings": {n: showings(v) for n, v in trr.items()},
            "held_records": {n: len(v) for n, v in hdr.items()}}
    return rows, held_rows, info


def keys_fn(st=None):
    """C3's per-record mask over C3r's sources (`full_controls_c3.keys_fn`)."""
    from learn import full_controls_c3 as C3

    return C3.keys_fn((st or state())["sources"])


def check_rows(arm, k, inner, rows, held_rows, st=None):
    """The run's rows against the rule: no held unit and no unit sharing an identity with a fold out of the run among
    the training rows; every held unit in its held fold; arm ctl trains on BKS and GOAT only. -> [problem]."""
    st = st or state()
    ent = {e["unit"]: e for e in st["entries"]}
    out = []
    tr_units = {r["real"] for r in rows}
    held_units = {r["real"] for r in held_rows}
    if tr_units & held_units:
        out.append("a held unit among the training rows")
    if k is None:
        return out
    out_f = {k, (k + 1) % FOLDS} if inner else {k}
    hf = (k + 1) % FOLDS if inner else k
    banned = set().union(*[e["ids"] for e in st["entries"] if e["fold"] in out_f])
    for u in tr_units:
        e = ent[u]
        if e["fold"] in out_f:
            out.append(f"{u}: a training unit in a fold out of the run")
        if e["ids"] & banned:
            out.append(f"{u}: a training unit sharing a DI or creator with a fold out of the run")
        if arm == "ctl" and e["set"] in NEW_SETS:
            out.append(f"{u}: a new row in R-ctl")
    for u in held_units:
        if ent[u]["fold"] != hf:
            out.append(f"{u}: a held unit outside fold {hf}")
    return out


def run_info_check(rec, st=None):
    """A C3r run read or built on: trained on today's C2, C2r and C3 decision state."""
    got = (rec.get("c3r") or {}).get("c3r_sha256")
    if got != (st or state())["sha256"]:
        raise SystemExit(f"{rec['test']}-{rec['seed']}: trained on another C2/C2r/C3 state ({str(got)[:8]})")


def base_of(arm, st=None):
    st = st or state()
    return BASE[(arm, st["recipe"])]


def answer_hold(st=None):
    """The answer's hold: C3's adopted configuration (the decision's tag) on C3's recipe; `K.space` (None) on FTm's."""
    from learn import full_controls_c3 as C3

    st = st or state()
    return C3.hold_for(st["answer_tag"]) if st["recipe"] == "c3" else None


# --- the read --------------------------------------------------------------------------------------------------------------

def read_units(st=None):
    """Every read direction's unit, per set: BKS 5B.1's 40 units on each amp (`real_parts`), GOAT read 2's units
    (`goat_read_units`), cap1, n12 and the panel's C2r records on their own amp; each with its fold, lag, cluster and the
    record's stored S judges. -> [{set, unit, amp, fold, lag, cluster, band, prt}]."""
    from learn import cc_build as CB
    from learn import pipeline_fix as P

    st = st or state()
    ent = {e["unit"]: e for e in st["entries"]}
    out = []
    e = P.require("phase_5b1")
    _, kept, _, sp, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    inv = CB.cc_inventory()
    parts = P.real_parts(kept, sp, inv)
    folds = P.real_folds(parts, P.stage_units(kept, sp, inv, 1) + P.stage_units(kept, sp, inv, 2))
    for prt in parts:
        lp = P.out_dir() / P.REAL_DIR / "lags" / f"{prt['unit'].replace('/', '__')}.json"
        lag = json.loads(lp.read_text())["lag"] if lp.exists() else None
        for a in P.AMPS3:
            out.append({"set": "bks", "unit": prt["unit"], "amp": a, "fold": folds[prt["di"]], "lag": lag,
                        "cluster": prt["di"], "prt": prt})
    for prt in P.goat_read_units():
        out.append({"set": "goat", "unit": prt["unit"], "amp": prt["amp"], "fold": ent[prt["unit"]]["fold"],
                    "lag": prt["lag"], "cluster": prt["item"], "prt": prt})
    for r in sorted(st["c2r"]["records"], key=lambda x: (NEW_SETS.index(x["set"]), x["key"])):
        s, u, a = r["set"], r["unit"], r["amp"]
        prt = st["units"][s][u]
        lag = prt["lag"] if s == "panel" else json.loads(open(r["source"]).read())["lag"]
        out.append({"set": s, "unit": u, "amp": a, "fold": ent[u]["fold"], "lag": lag,
                    "cluster": prt["di"] if s == "panel" else prt["creator"], "band": prt.get("band"), "prt": prt})
    return out


def fname(key):
    return key.replace("/", "__").replace(" ", "_")


def answers_path(arm):
    return c3r_dir() / "answers" / f"{arm}.json"


def judge_path(arm, ru):
    return c3r_dir() / "judge" / arm / ru["set"] / f"{fname(ru['unit'] + '|' + ru['amp'])}.json"


def cmd_predict(args):
    """The answers (zero renders, CPU): each read unit by its fold's FT_k of the arm, both seeds pooled, on its D_fix
    input's variant 0 (`dfix_backed`), per search half, told the class and the amp, held by C3's adopted
    configuration (`answer_hold`). -> c3r/answers/<arm>.json."""
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    P.require(PHASE)
    st = state()
    base = base_of(args.arm, st)
    models = {}
    for k in range(FOLDS):
        nm = P.ft_name(k, base=base)
        nets, recs = zip(*(P.load_run(nm, sd, "best") for sd in P.SEEDS))
        for r_ in recs:
            run_info_check(r_, st)
            if r_.get("inner") or r_["models"]["best"] != r_["models"]["final"] or r_.get("E") != r_.get("epochs_run"):
                raise SystemExit(f"{nm}-{r_['seed']}: not an FT_k read at its E")
        models[k] = (list(nets), [r_["model_sha256"]["best"] for r_ in recs])
    ms = P.A_menu_S()
    hold = answer_hold(st)
    out = {}
    units = read_units(st)
    for ru in units:
        nets, _ = models[ru["fold"]]
        amp, prt = ru["amp"], ru["prt"]
        sel, S = ms[amp][prt["cls"]]
        backed = P.dfix_backed(ru["unit"])
        for search in ("A", "B"):
            s8, ls = backed[search]
            x, c = DS.model_input(s8, s8, ls, ls, search, amp, prt["cls"], "Dstem")
            r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
            stg = F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"])
            stg = P.hold_outside_space(stg, S, amp) if hold is None else P.hold_outside_space(stg, S, amp, hold)
            out.setdefault(ru["set"], {}).setdefault(f"{ru['unit']}|{amp}", {})[search] = {
                "select": sel, "settings": LO.sdict(stg)}
    P.save(answers_path(args.arm), {"plan": "docs/full-controls-plan.md", "ledger": f"{P.LEDGER_ID} {PHASE}",
                                    "arm": args.arm, "base": base, "recipe": st["recipe"],
                                    "answer_tag": st["answer_tag"], "c3r_sha256": st["sha256"],
                                    "models": {k: m[1] for k, m in models.items()}, "answers": out,
                                    "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"C3R PREDICT DONE {args.arm}: {sum(len(v) for v in out.values())} keys over {len(units)} read units")


def cmd_render(args):
    """The answers' renders (one shard): each answer through its unit's DI in its own primed process (`fresh_render`),
    trimmed, judged on both halves at the unit's lag. -> c3r/judge/<arm>/<set>/<unit>|<amp>.json."""
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
    arms = [a for a in args.arms.split(",") if a]
    ans = {a: json.loads(answers_path(a).read_text()) for a in arms}
    st = state()
    for a in arms:
        if ans[a]["c3r_sha256"] != st["sha256"]:
            raise SystemExit(f"{a}: its answers were made on another state")
    k, n = args.shard
    units = [ru for j, ru in enumerate(read_units(st)) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for ru in units:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        if ru["lag"] is None:
            continue
        prt, key = ru["prt"], f"{ru['unit']}|{ru['amp']}"
        todo = [a for a in arms if key in ans[a]["answers"].get(ru["set"], {})]
        di32 = ref = di = None
        for a in todo:
            gp = judge_path(a, ru)
            asha = P.answers_sha({key: ans[a]["answers"][ru["set"]][key]})
            if gp.exists():
                if json.loads(gp.read_text()).get("answers_sha256") != asha:
                    raise SystemExit(f"{gp}: rendered from other answers")
                continue
            if di32 is None:
                di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
                di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
                ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            rec = {"set": ru["set"], "unit": ru["unit"], "amp": ru["amp"], "arm": a, "lag": ru["lag"],
                   "answers_sha256": asha, "judge": {}, "render_sha256": {}}
            for search, x in sorted(ans[a]["answers"][ru["set"]][key].items()):
                s_ = LO.tdict(x["settings"])
                y = np.asarray(AM.fresh_render(CB.new_renderer, di32, x["select"], s_, s_), np.float64)[trim[0]:trim[1]]
                renders += 2
                rec["judge"][search] = K.judge(ref, y, di, ru["lag"])
                rec["render_sha256"][search] = AM.audio_sha(y)
            P.save(gp, rec)
        print(f"{ru['set']} {ru['unit'][-56:]}|{ru['amp']}: renders so far {renders}", flush=True)
    print(f"C3R-RENDER DONE {k}/{n}: {renders} renders")


def half_value(judge, search, held):
    """One direction's held-half distance from a judge record's {search or "*": {A, B}}: a finite positive value or None."""
    from learn import pipeline_fix as P

    v = (judge or {}).get(search) or (judge or {}).get(P.ANY_HALF)
    x = (v or {}).get(held)
    return x if isinstance(x, (int, float)) and math.isfinite(x) and x > 0 else None


def s_judges(st, ru):
    """S's judge on a read unit's amp ({A, B}), from what was stored: BKS's S renders, GOAT's and the captures' search
    records, the panel's 5D lag record."""
    from learn import pipeline_fix as P

    u, a = ru["unit"], ru["amp"]
    if ru["set"] == "bks":
        p = P.out_dir() / P.REAL_DIR / "judge" / "S" / f"{(u + '|' + a).replace('/', '__')}.json"
        return (json.loads(p.read_text())["judge"].get(P.ANY_HALF) if p.exists() else None)
    if ru["set"] == "goat":
        p = P.out_dir() / P.GOAT_DIR / P.SEARCH_DIR / f"{(u + '|' + a).replace('/', '__')}.json"
        return json.loads(p.read_text()).get("s_judge") if p.exists() else None
    if ru["set"] in ("cap1", "n12"):
        r = next(x for x in st["c2r"]["records"] if x["unit"] == u and x["amp"] == a)
        return json.loads(open(r["source"]).read()).get("s_judge")
    lp = P.out_dir() / P.PANEL_DIR / "lags" / f"{P.panel_fname(u)}.json"
    return json.loads(lp.read_text())["s"][a]["judge"]


def c3_judge(ru, tag):
    """C3's stored score on a read unit (BKS and GOAT: their judge records, both directions; n12: N12's side read, the
    held half of its one direction). -> {search: {A, B}} or None."""
    from learn import pipeline_fix as P
    from learn import score_ear as SE

    k = (ru["unit"] + "|" + ru["amp"]).replace("/", "__")
    if ru["set"] == "bks":
        p = P.out_dir() / P.REAL_DIR / "judge" / tag / f"{k}.json"
    elif ru["set"] == "goat":
        p = P.out_dir() / P.GOAT_DIR / "judge" / tag / f"{k}.json"
    elif ru["set"] == "n12":                           # N12's side read: one direction, its held half
        slug = SE.slug_of(ru["unit"])
        if tag == P.FTM_BASE:                          # FTm's own N12 renders (ear-wide/renders/<slug>/rec.json)
            q = SE.wide_dir() / "renders" / slug / "rec.json"
            if not q.exists():
                return None
            r = json.loads(q.read_text())
            v = (r.get("judge") or {}).get("FTm")
            return None if v is None else {("B" if r["held"] == "A" else "A"): {r["held"]: v}}
        j = SE.h4_judged(tag, slug)
        if not j:
            return None
        return {j["search"]: {j["held"]: j["judge"]}}
    else:
        return None
    return json.loads(p.read_text())["judge"] if p.exists() else None


def c3_n12_refusal(tag):
    """Why C3's N12 scores can't be read for `tag`, or None: a C3 tag's side read writes ear-wide/h4/<tag>/ (C3's read
    launcher, before its decision); FTm's are N12's own renders."""
    from learn import pipeline_fix as P
    from learn import score_ear as SE

    d = SE.wide_dir() / ("renders" if tag == P.FTM_BASE else SE.H4_DIR) / ("" if tag == P.FTM_BASE else tag)
    return None if d.is_dir() and any(d.iterdir()) else f"{d}: no N12 scores for {tag} (C3's side read has not run)"


def pair_rows(st, units, val_a, val_b, set_):
    """ln(d_a / d_b) on the held half for every direction of one set's read units both judge finite.
    -> ([(cluster, unit, value)], missing)."""
    rows, missing = [], 0
    for ru in units:
        if ru["set"] != set_:
            continue
        for sh, h in (("A", "B"), ("B", "A")):
            a, b = val_a(ru, sh, h), val_b(ru, sh, h)
            if a is None or b is None:
                missing += 1
                continue
            rows.append((ru["cluster"], ru["unit"] + "|" + ru["amp"], math.log(a / b)))
    return rows, missing


def cmd_report(_args):
    """The rows (zero renders): per set and pooled, R-all - R-ctl (primary), R-all - S, R-ctl - S, and R-all - C3 where
    C3's scores are stored; cluster t intervals (GOAT by item, BKS by DI, cap1 and n12 by creator, the panel by DI with
    the band-weighted reading beside); the new sets' units whose DI file is among W's plugin rows apart; H4's real_out
    units in the rows, with a reading without them beside; the adoption rule. -> c3r/report.json."""
    from learn import pipeline_fix as P
    from learn import score_ear as SE

    P.require(PHASE)
    st = state()
    units = read_units(st)
    judge = {a: {} for a in ARMS}
    for a in ARMS:
        for ru in units:
            p = judge_path(a, ru)
            if p.exists():
                judge[a][(ru["unit"], ru["amp"])] = json.loads(p.read_text())["judge"]
    wd = set(SE.w_dis())
    real_out = set(P.h4_exclusions()["real_out"])
    c3tag = st["answer_tag"] if st["recipe"] == "c3" else P.FTM_BASE
    why = c3_n12_refusal(c3tag)
    if why:
        raise SystemExit(why)

    def val(arm):
        return lambda ru, sh, h: half_value(judge[arm].get((ru["unit"], ru["amp"])), sh, h)

    def s_val(ru, sh, h):
        return half_value({P.ANY_HALF: s_judges(st, ru)}, sh, h)

    def c3_val(ru, sh, h):
        return half_value(c3_judge(ru, c3tag), sh, h)

    seen_player = player_seen(st, units)
    pairs = {"R-all - R-ctl": (val("all"), val("ctl")), "R-all - S": (val("all"), s_val),
             "R-ctl - S": (val("ctl"), s_val), f"R-all - {c3tag}": (val("all"), c3_val)}
    keep = ("mean", "lo90", "hi90", "clusters", "clusters_negative", "part_weighted", "parts", "parts_negative")
    out = {"plan": "docs/full-controls-plan.md", "ledger": f"{P.LEDGER_ID} {PHASE}", "recipe": st["recipe"],
           "answer_tag": st["answer_tag"], "c3r_sha256": st["sha256"], "rows": {}, "apart": {}}
    for name, (fa, fb) in pairs.items():
        out["rows"][name] = {}
        for s in SETS:
            rows, missing = pair_rows(st, units, fa, fb, s)
            main = [r for r in rows if not _apart(r, units, wd)]
            c = P.clustered(main)
            row = {q: c.get(q) for q in keep}
            row["missing"] = missing
            row["directions"] = len(main)
            ro = [r for r in main if r[1].rsplit("|", 1)[0] not in real_out]   # H4's real_out read beside, as C3
            row["without_real_out"] = dict({q: P.clustered(ro).get(q) for q in keep}, directions=len(ro)) if ro else None
            if s == "panel":
                bands = {ru["unit"] + "|" + ru["amp"]: ru.get("band") for ru in units if ru["set"] == "panel"}
                row["band_weighted"] = {q: P.clustered([(bands[p_], p_, v) for _, p_, v in main]).get(q) for q in keep}
            if s in ("cap1", "n12"):                   # split by whether the DI's band or GOAT player trains in FT_k
                for tag_, keep_it in (("player_trains", True), ("player_unseen", False)):
                    sub = [r for r in main if (r[1] in seen_player) == keep_it]
                    row[tag_] = {q: P.clustered(sub).get(q) for q in keep} if sub else None
            out["rows"][name][s] = row
            ap = [r for r in rows if _apart(r, units, wd)]
            if ap:
                out["apart"].setdefault(name, {})[s] = {q: P.clustered(ap).get(q) for q in keep}
                out["apart"][name][s]["units"] = sorted({r[1] for r in ap})
        rs = out["rows"][name]
        rs["deciding_pool"] = pooled({s: rs[s] for s in DECIDING}) if all(rs[s].get("mean") is not None
                                                                        for s in DECIDING) else None
        rs["five_set_pool"] = pooled({s: rs[s] for s in SETS}) if all(rs[s].get("mean") is not None
                                                                     for s in SETS) else None
    out["adoption"] = adoption({s: out["rows"]["R-all - R-ctl"][s] for s in SETS})
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(c3r_dir() / "report.json", out)
    for name in pairs:
        rs = out["rows"][name]
        print(name, {s: (rs[s].get("mean"), rs[s].get("lo90"), rs[s].get("hi90")) for s in SETS},
              "deciding pool", rs.get("deciding_pool"), "five-set pool", rs.get("five_set_pool"))
    print("ADOPTION", json.dumps({k: out["adoption"][k] for k in ("shown_worse", "replaces_c3", "complete", "why")}))


def player_seen(st, units):
    """The cap1 and n12 read directions whose DI's band or GOAT player (`player_of`) is among R-all's FT_k training
    units' for the unit's own fold. -> {"unit|amp"}."""
    ents = st["entries"]
    by_fold = {k: {e["player"] for e in split(ents, k, False, "all")[0]} for k in range(FOLDS)}
    ent = {e["unit"]: e for e in ents}
    return {ru["unit"] + "|" + ru["amp"] for ru in units
            if ru["set"] in ("cap1", "n12") and ent[ru["unit"]]["player"] in by_fold[ru["fold"]]}


def _apart(row, units, wd):
    """A direction read apart: a new set's unit whose DI file is among W's plugin rows (`score_ear.w_dis`; BKS's and
    GOAT's reads keep H4a's and C3's convention, and BKS's 40 units all sit on W's DIs). H4's real_out units stay in the
    main rows, as C3 trains and reads every row (C5 holds the exclusions); a reading without them is reported beside."""
    u = row[1].rsplit("|", 1)[0]
    ru = next((x for x in units if x["unit"] == u), {})
    prt = ru.get("prt") or {}
    return ru.get("set") in NEW_SETS and (prt.get("di_path") in wd or prt.get("di") in wd)


def cmd_folds(_args):
    """The folds and drops on today's records (zero renders), both arms. -> c3r/folds.json."""
    from learn import pipeline_fix as P

    st = state(partial=True)
    ents = st["entries"]
    out = {"recipe": st["recipe"], "band_folds": st["band_folds"],
           "folds": {s: {f: sum(1 for e in ents if e["set"] == s and e["fold"] == f and e["row"]) for f in range(FOLDS)}
                     for s in SETS},
           "read_only_goat": sum(1 for e in ents if not e["row"]),
           "arms": {a: drop_counts(ents, a) for a in ARMS},
           "records": {s: sum(1 for q in st["rec_set"].values() if q == s) for s in SETS},
           "complete": {"c2": st["c2"]["written"], "c2r": st["c2r"]["written"], "decision": st["decision"] is not None}}
    P.save(c3r_dir() / "folds.json", out)
    print(json.dumps({k: out[k] for k in ("band_folds", "folds", "records", "complete", "read_only_goat")}, indent=1))
    for a in ARMS:
        for name, c in out["arms"][a].items():
            print(a, name, "train", c["train"], "dropped", c["dropped"])


def cmd_check(_args):
    """Zero renders: C2 and C2r complete, C3's decision, every row's and read unit's D_fix inputs built."""
    from learn import pipeline_fix as P

    st = state()
    missing = sorted({u for (u, _) in st["sources"]} | {ru["unit"] for ru in read_units(st)})
    missing = [u for u in missing if not all(P.dfix_input_path(u, v).exists() for v in range(P.DFIX_K))]
    print(json.dumps({"recipe": st["recipe"], "answer_tag": st["answer_tag"], "c2": st["c2"]["written"],
                      "c2r": st["c2r"]["written"], "records": len(st["sources"]),
                      "units_missing_inputs": len(missing), "first_missing": missing[:3]}, indent=1))
    if missing:
        raise SystemExit("D_fix inputs missing (build-dfix-real --panel)")


def main(argv=None):
    from learn import full_controls as F

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("c3r-folds").set_defaults(fn=cmd_folds)
    sub.add_parser("c3r-check").set_defaults(fn=cmd_check)
    p = sub.add_parser("c3r-predict")
    p.add_argument("--arm", choices=ARMS, required=True)
    p.set_defaults(fn=cmd_predict)
    r = sub.add_parser("c3r-render")
    r.add_argument("--arms", default="all,ctl")
    r.add_argument("--shard", type=F.shard, default=(0, 1))
    r.set_defaults(fn=cmd_render)
    sub.add_parser("c3r-report").set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
