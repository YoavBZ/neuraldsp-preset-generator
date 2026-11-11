"""C3 (`docs/full-controls-plan.md`, "C3 in detail"; ledger `pipeline-fix` `phase_c3`): FTm's recipe retrained on C2's
full labels with per-record masks, read by the score as H4a read FTm, with one tag per family at S so each family is
adopted on its own. The training is `pipeline_fix train-ft --c3` (FTm's recipe; only the label source, the masks and
the answer's hold change); the read is `real-predict`, `goat-predict`, `real-render`, `goat-render`, `score_ear h4-*`,
`real-report` and `goat-report` on C3's tags. This module holds C3's pure parts and its own commands:

    .venv/bin/python -m learn.full_controls_c3 c3-check            # C2 complete? sources, masks, the hold (zero renders)
    .venv/bin/python -m learn.full_controls_c3 c3-gate OUT.json    # the gate threshold labels' spread (zero renders)
    .venv/bin/python -m learn.full_controls_c3 c3-recheck          # FTm's stored BKS and GOAT renders again (renders)
    .venv/bin/python -m learn.full_controls_c3 c3-n12 OUT.json     # N12: C3 against its C1b labels (zero renders)
    .venv/bin/python -m learn.full_controls_c3 c3-amp OUT.json     # BKS: W's amp head on C3's body (zero renders)
    .venv/bin/python -m learn.full_controls_c3 c3-adopt [--final]  # the per-family adoption, then C3 against FTm

The pure parts (the label sources, the masks, the per-control hold and its tags, the families, the pooled interval,
the adoption and the replacement rule) are unit-tested; the renders are not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time

PHASE = "phase_c3"
C3_BASE = "C3-ftm"                   # C3's own runs: `C3-ftm-k{k}-inner-cap300`, `C3-ftm-k{k}`, `C3-ftm` (never FTm's)
FTM_TAG = "P2b-ftm"
N_C2 = 520                           # C2's records: the training refuses until every one is written
FAMILIES = ("eq", "pedals", "gate", "cab")             # the trained families outside `K.space`
FAMILY_TAG = {"eq": "C3-eqS", "pedals": "C3-pedalsS", "gate": "C3-gateS", "cab": "C3-cabS"}
TAGS = {"C3-ftm": (), "C3-core": FAMILIES, **{t: (f,) for f, t in FAMILY_TAG.items()}}   # tag -> families at S
ADOPT_TAG = "C3-adopt"               # the adopted configuration when it is none of the six
ALL_TAGS = frozenset(TAGS) | {ADOPT_TAG}
C3I_PHASE = "phase_c3i"              # C3i, the isolation of C3's core (docs/full-controls-plan.md, "C3i in detail")
C3I_BASE = "C3i-ftm"                 # its own runs (`train-ft --masked --c3i`): FTm's recipe and mask on C2's labels
C3I_TAG = "C3i"                      # its read tag (`pipeline_fix.C3I_TAG`), answered with FTm's hold (`K.space`)
C3I_PAIRS = ((C3I_TAG, FTM_TAG), ("C3-core", C3I_TAG), (C3I_TAG, "S"))
C3B_PHASE = "phase_c3b"              # C3b, the amp head on real rows (docs/full-controls-plan.md, "C3b in detail")
C3B_BASE = "C3b-ftm"                 # its own runs (`train-ft --masked --c3b`): C3's recipe, plus each unit's amp label
C3B_TAG = "C3b"                      # its read tag (`pipeline_fix.C3B_TAG`), answered with the adopted C3's hold
AMP_USABLE_DBFS = -57.0              # C2b's like-for-like bound: a label counts for the amp choice at or above it
PEDAL_MODULES = ("drive1", "drive2", "compressor")
GATE_SW, GATE_THR = ("parameters", "gateActive"), ("parameters", "gateThreshold")
RECHECK_N = 3                        # FTm's stored judge files rendered again per set (both halves: 12 renders + priming)
OUT = "c3"


def eq_active(amp):
    return (f"{amp}EQ", f"{amp}EQActive")


def parse(names):
    """["module/key"] -> {(module, key)}."""
    return {tuple(n.rsplit("/", 1)) for n in names}


def names_of(keys):
    return sorted(f"{a}/{b}" for a, b in keys)


def family_of(key, amp):
    """A trained key outside `K.space` -> its family; anything else refuses (C3 trains no other family)."""
    m, k = key
    if m == f"{amp}EQ" and k != f"{amp}EQActive":
        return "eq"
    if m in PEDAL_MODULES:
        return "pedals"
    if key in (GATE_SW, GATE_THR):
        return "gate"
    if m == "cabParameters":
        return "cab"
    raise SystemExit(f"{m}/{k}: a trained key in no C3 family")


def kspace_keys(amp, S):
    from learn import knob_ceiling as K

    return {(d.module, d.key) for d in K.space(amp, S)}


# --- the label sources and the masks (zero renders) -------------------------------------------------------------------

def finite_pos(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v > 0


def c1b_usable(c1b):
    """A C1b record C3 may fall back to: a dry label whose fresh final scores on both halves (F70's failed record does
    not: its final is infinite on the held half)."""
    if not c1b or c1b.get("label") is None or c1b.get("effect_kept"):
        return False
    j = (((c1b.get("fresh") or {}).get("final") or {}).get("judge") or {})
    return all(finite_pos(j.get(h)) for h in ("A", "B"))


def mask_keys(kind, amp, kspace, searched=(), c1a=(), stage_a=(), stage_b=()):
    """The keys a record trains: a C2 label `K.space` ∪ C2's `searched_keys`; C1a's block on C1b's record C1a's space ∪
    C1b's stage A and B keys (never C1b's `searched_keys`, which list every effect knob: F70); a stored label `K.space`
    only, as FTm. The gate's switch and `EQActive` are masked everywhere (the switch is the start's convention, F69;
    the EQ is forced on). -> {(module, key)}."""
    if kind == "c2":
        keys = set(kspace) | parse(searched)
    elif kind == "c1b":
        keys = parse(c1a) | parse(stage_a) | parse(stage_b)
    elif kind == "stored":
        keys = set(kspace)
    else:
        raise ValueError(kind)
    return keys - {GATE_SW, eq_active(amp)}


def choose_source(out, block, c1b=None, c1a=None, stored=None):
    """One C2 record's training label: C2's own if it has one, else its source (C1b's record for C1a's block when
    usable, else the stored label). -> {"kind", "label" (sdict), "searched", "c1a", "stage_a", "stage_b"}."""
    if out is None:
        raise SystemExit("a C2 record with no output: C2 is not complete")
    if out.get("label") is not None:
        return {"kind": "c2", "label": out["label"], "searched": list(out.get("searched_keys") or [])}
    if block == "c1a" and c1b_usable(c1b):
        return {"kind": "c1b", "label": c1b["label"], "c1a": list((c1a or {}).get("searched_keys") or []),
                "stage_a": list(c1b.get("rooms_keys") or []), "stage_b": list(c1b.get("mics_eq_keys") or [])}
    if not stored or stored.get("label") is None:
        raise SystemExit("a record with neither a C2 label nor a stored one")
    return {"kind": "stored", "label": stored["label"]}


def head_masks(keys):
    """{(module, key)} -> the (continuous, switch, mic) masks of FT2's heads (`full_space` layout) those keys label."""
    import numpy as np

    from learn import full_space as FS

    D = FS.by_name()
    return tuple(np.array([(D[n].module, D[n].key) in keys for n in names], np.float32)
                 for names in (FS.CONT, FS.SW, FS.CAT))


def mask_rows(Y, rows, ms, keys_of):
    """`pipeline_fix.mask_searched` with per-record keys: every real row (training or held) keeps only its record's
    trained heads, and no amp label (-100). keys_of(unit, amp, S) -> {(module, key)}. Y changed in place."""
    for j, r in enumerate(rows):
        if "real" in r:
            c, s, k = head_masks(keys_of(r["real"], r["amp"], ms[r["amp"]][r["cls"]][1]))
            Y[1][j] *= c
            Y[3][j] *= s
            Y[5][j] *= k
            Y[6][j] = -100


# --- C2's state ---------------------------------------------------------------------------------------------------------

def c2_files():
    """C2's records.json and each record's output path, in C2's order. -> (records path, [(record, output path)])."""
    from learn import full_controls_c2 as C2

    rp = C2.c2_dir() / "records.json"
    if not rp.exists():
        raise SystemExit(f"{rp}: C2 is not drawn")
    recs = json.loads(rp.read_text())["records"]
    return rp, [(r, C2.out_path(r)) for r in recs]


def c2_state(partial=False):
    """C2's records and outputs, with one sha256 over records.json and every output in order. Refuses unless all
    N_C2 are written (`partial` lets a zero-render check read what exists). -> {"sha256", "written", "records",
    "outputs": {key: output}}."""
    rp, pairs = c2_files()
    if len(pairs) != N_C2:
        raise SystemExit(f"C2 drew {len(pairs)} records, not {N_C2}")
    missing = [r["key"] for r, p in pairs if not p.exists()]
    if missing and not partial:
        raise SystemExit(f"C2 is not complete: {N_C2 - len(missing)} of {N_C2} written (first missing {missing[0]})")
    h = hashlib.sha256(rp.read_bytes())
    outs = {}
    for r, p in pairs:
        if p.exists():
            b = p.read_bytes()
            h.update(r["key"].encode() + b"\0" + b)
            outs[r["key"]] = json.loads(b)
    return {"sha256": h.hexdigest(), "written": len(outs), "records": [r for r, _ in pairs], "outputs": outs}


def sources(state):
    """Each C2 record's training label and mask names. -> {(unit, amp): {"kind", "label", ...}} for written ones."""
    out = {}
    for r in state["records"]:
        o = state["outputs"].get(r["key"])
        if o is None:
            continue
        c1b = c1a = None
        if o.get("label") is None and r["block"] == "c1a":
            c1b = json.loads(open(r["c1b_record"]).read())
            c1a = json.loads(open(r["c1a_output"]).read())
        stored = json.loads(open(r["source"]).read()) if o.get("label") is None else None
        out[(r["unit"], r["amp"])] = dict(choose_source(o, r["block"], c1b, c1a, stored), block=r["block"],
                                          key=r["key"])
    return out


def keys_fn(src):
    """keys_of(unit, amp, S) for `mask_rows`, from `sources`."""
    def keys_of(unit, amp, S):
        s = src.get((unit, amp))
        if s is None:
            raise SystemExit(f"{unit}|{amp}: a real training row with no C2 record")
        return mask_keys(s["kind"], amp, kspace_keys(amp, S), s.get("searched", ()), s.get("c1a", ()),
                         s.get("stage_a", ()), s.get("stage_b", ()))
    return keys_of


def label_fn(src):
    """label_of(stored record) for `pipeline_fix.record_rows`: the record's C3 label as a full label."""
    from learn import full_space as FS
    from learn import local_objective as LO

    def label_of(rec):
        s = src.get((rec["unit"], rec["amp"]))
        if s is None:
            raise SystemExit(f"{rec['unit']}|{rec['amp']}: a real training row with no C2 record")
        return FS.label_of(LO.tdict(s["label"]), rec["amp"])
    return label_of


def source_counts(src):
    out = {}
    for s in src.values():
        k = f"{s['block']}:{s['kind']}"
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def trained_union(state):
    """Per amp, the union of C2's `searched_keys` over its records with a C2 label. -> {amp: {(module, key)}}."""
    out = {}
    for r in state["records"]:
        o = state["outputs"].get(r["key"])
        if o and o.get("label") is not None:
            out.setdefault(r["amp"], set()).update(parse(o.get("searched_keys") or ()))
    return out


# --- the answer's per-control hold --------------------------------------------------------------------------------------

def hold_keys(amp, S, union, at_S, kspace=None):
    """C3's answer hold: the keys written from the heads and the values forced. Written: `K.space` ∪ C2's union for the
    amp, less the gate's switch and `EQActive`, less every trained key whose family is in `at_S`. Forced: `EQActive`
    on, and the gate on unless "gate" is at S. Everything else stays at S. -> (written keys, {key: forced value})."""
    ks = kspace_keys(amp, S) if kspace is None else set(kspace)
    bad = [f for f in at_S if f not in FAMILIES]
    if bad:
        raise SystemExit(f"no such family: {bad}")
    trained = (ks | set(union.get(amp, ()))) - {GATE_SW, eq_active(amp)}
    write = {k for k in trained if k in ks or family_of(k, amp) not in at_S}
    forced = {eq_active(amp): "true"}
    if "gate" not in at_S:
        forced[GATE_SW] = "true"
    return write, forced


def hold_spec(union, at_S):
    """A `pipeline_fix.hold_outside_space` hold: (amp, S) -> (written keys, forced values)."""
    def hold(amp, S):
        return hold_keys(amp, S, union, at_S)
    return hold


def at_S_of(tag, adoption=None):
    """The families a tag answers at S; C3-adopt's come from the adoption record."""
    if tag in TAGS:
        return TAGS[tag]
    if tag == ADOPT_TAG:
        if adoption is None:
            raise SystemExit(f"{ADOPT_TAG}: no adoption record (run c3-adopt first)")
        return tuple(adoption["at_S"])
    raise SystemExit(f"{tag}: not a C3 tag ({', '.join(sorted(ALL_TAGS))})")


_STATE = {}


def hold_for(tag):
    """The hold of a C3 tag, on C2's complete state (cached per process)."""
    if "state" not in _STATE:
        _STATE["state"] = c2_state()
    adoption = None
    if tag == ADOPT_TAG:
        adoption = json.loads((c3_dir() / "adoption.json").read_text())
        if adoption["c2_sha256"] != _STATE["state"]["sha256"]:
            raise SystemExit("the adoption record was made on another C2 state")
    return hold_spec(trained_union(_STATE["state"]), at_S_of(tag, adoption))


def c2_sha():
    if "state" not in _STATE:
        _STATE["state"] = c2_state()
    return _STATE["state"]["sha256"]


def read_check(rec):
    """A C3 run read by a C3 tag: it trained on today's C2 state."""
    got = (rec.get("c3") or {}).get("c2_sha256")
    if got != c2_sha():
        raise SystemExit(f"{rec['test']}-{rec['seed']}: trained on another C2 state ({str(got)[:8]})")


def c3_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT


# --- the rows: pooled, shown worse, adoption, replacement -------------------------------------------------------------

def se_of(row):
    """A report row's standard error from its 90% cluster t interval (df = clusters - 1). -> (se, df) or None."""
    from learn import pipeline_fix as P

    if not row or row.get("lo90") is None or row.get("hi90") is None or (row.get("clusters") or 0) < 2:
        return None
    df = row["clusters"] - 1
    return (row["hi90"] - row["lo90"]) / (2 * P.t95(df)), df


def pooled(bks, goat):
    """The two sets weighted equally: the mean of the two set means, its standard error from the two sets' cluster
    standard errors, Welch-Satterthwaite's df, a 90% t interval. -> {"mean", "lo90", "hi90", "df"} or None."""
    from learn import pipeline_fix as P

    a, b = se_of(bks), se_of(goat)
    if a is None or b is None or bks.get("mean") is None or goat.get("mean") is None:
        return None
    (sa, da), (sb, db) = a, b
    m = (bks["mean"] + goat["mean"]) / 2
    v = (sa ** 2 + sb ** 2) / 4
    if v == 0:
        return {"mean": m, "lo90": m, "hi90": m, "df": None}
    df = (sa ** 2 + sb ** 2) ** 2 / (sa ** 4 / da + sb ** 4 / db)
    h = P.t95(max(1, int(math.floor(df)))) * math.sqrt(v)
    return {"mean": m, "lo90": m - h, "hi90": m + h, "df": df}


def shown_worse(row):
    """A row's 90% interval wholly above 0."""
    return bool(row) and row.get("lo90") is not None and row["lo90"] > 0


def judged(bks, goat):
    """One comparison read on both sets: each set's row, the pooled row, and whether any of the three is shown worse."""
    p = pooled(bks, goat)
    return {"bks": bks, "goat": goat, "pooled": p,
            "shown_worse": any(shown_worse(r) for r in (bks, goat, p))}


COMPARISONS = (f"C3-ftm - {FTM_TAG}", "C3-ftm - S", f"C3-core - {FTM_TAG}")   # pooled beside the families


def config_tag(at_S):
    """The tag that answers with exactly the families `at_S` at S: one of the six, else C3-adopt."""
    want = set(at_S)
    for t, fams in TAGS.items():
        if set(fams) == want:
            return t
    return ADOPT_TAG


def row_name(a, b):
    return f"{a} - {b}"


def adoption(bks_rows, goat_rows):
    """Per family: C3 - (C3 with that family at S), kept unless shown worse on BKS, on GOAT or pooled (an undecided
    family is kept). -> {"families": {f: judged}, "adopted", "at_S", "config_tag"}."""
    fam = {}
    for f in FAMILIES:
        n = row_name("C3-ftm", FAMILY_TAG[f])
        if n not in bks_rows or n not in goat_rows:
            raise SystemExit(f"the report has no row {n}")
        fam[f] = judged(bks_rows[n], goat_rows[n])
    at_S = [f for f in FAMILIES if fam[f]["shown_worse"]]
    comp = {n: judged(bks_rows[n], goat_rows[n]) for n in COMPARISONS if n in bks_rows and n in goat_rows}
    missing = [n for n in COMPARISONS if n not in comp]
    if missing:
        raise SystemExit(f"the report has no row {missing[0]}")
    return {"families": fam, "adopted": [f for f in FAMILIES if f not in at_S], "at_S": at_S,
            "config_tag": config_tag(at_S), "comparisons": comp,
            "core_shown_worse": comp[row_name("C3-core", FTM_TAG)]["shown_worse"]}


def replacement(bks_rows, goat_rows, tag):
    """The adopted configuration replaces FTm unless it is shown worse than FTm, by the family test."""
    n = row_name(tag, FTM_TAG)
    if n not in bks_rows or n not in goat_rows:
        raise SystemExit(f"the report has no row {n}")
    j = judged(bks_rows[n], goat_rows[n])
    return dict(j, tag=tag, replaces_ftm=not j["shown_worse"])


def report_pairs():
    """The read's report pairs (`real-report` and `goat-report --pairs`)."""
    pairs = [("C3-ftm", FTM_TAG), ("C3-ftm", "S"), ("C3-core", FTM_TAG)]
    pairs += [("C3-ftm", FAMILY_TAG[f]) for f in FAMILIES]
    pairs += [(FAMILY_TAG[f], FTM_TAG) for f in FAMILIES]   # an adopted single-family-at-S tag against FTm
    return ",".join(f"{a}:{b}" for a, b in pairs)


# --- the gate's spread (zero renders) ----------------------------------------------------------------------------------

def gate_of(label):
    """A label's (gate on, threshold) or None."""
    if not label:
        return None
    on = str(label.get("parameters/gateActive", "false")).lower() in ("true", "1")
    thr = label.get("parameters/gateThreshold")
    return on, (float(thr) if thr is not None else None)


def spread(values):
    v = sorted(values)
    if not v:
        return None

    def q(p):
        return v[min(len(v) - 1, max(0, int(round(p * (len(v) - 1)))))]
    return {"n": len(v), "min": v[0], "q25": q(0.25), "median": q(0.5), "q75": q(0.75), "max": v[-1],
            "at_minus_80": sum(1 for x in v if abs(x + 80.0) < 1e-6),
            "moved_from_minus_80": sum(1 for x in v if abs(x + 80.0) >= 1e-6)}


def gate_rows(labels):
    """labels: {set: [label]} -> per set the gate on and off counts and the spread of the thresholds where it is on."""
    out = {}
    for s, labs in labels.items():
        g = [gate_of(x) for x in labs]
        g = [x for x in g if x is not None]
        out[s] = {"labels": len(g), "gate_on": sum(1 for on, _ in g if on), "gate_off": sum(1 for on, _ in g if not on),
                  "threshold_where_on": spread([t for on, t in g if on and t is not None])}
    return out


def cmd_gate(args):
    from learn import full_controls as C1A
    from learn import full_controls_c1b as C1B
    from learn import pipeline_fix as P

    P.require(PHASE)
    labs = {}
    for name, dirs in (("c1a", C1A.OUT_DIRS), ("c1b", C1B.OUT_DIRS)):
        for s, (root, sub) in dirs.items():
            for p in sorted((P.out_dir() / root / sub).glob("*.json")):
                labs.setdefault(f"{name}:{s}", []).append(json.loads(p.read_text()).get("label"))
    st = c2_state(partial=True)
    for r in st["records"]:
        o = st["outputs"].get(r["key"])
        if o is not None:
            labs.setdefault(f"c2:{r['block']}", []).append(o.get("label"))
    rep = {"phase": PHASE, "c2_written": st["written"], "c2_complete": st["written"] == N_C2, "rows": gate_rows(labs),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(args.out, rep)
    print(json.dumps(rep, indent=1))


# --- the zero-render check -------------------------------------------------------------------------------------------

def hold_equal_core(answers, ms, union, amp_of):
    """C3-core's hold against `hold_outside_space` on stored answers. -> (compared, [keys that differ])."""
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    hold = hold_spec(union, TAGS["C3-core"])
    n, bad = 0, []
    for key, by in answers.items():
        amp = amp_of(key)
        for _, a in by.items():
            st = LO.tdict(a["settings"])
            cls = a["cls"]
            S = ms[amp][cls][1]
            x, y = P.hold_outside_space(st, S, amp), P.hold_outside_space(st, S, amp, hold)
            n += 1
            if x != y:
                bad.append(key)
    return n, bad


def untrained_at_S(answers, ms, union, amp_of):
    """For every C3 tag's hold on stored answers: no key outside the written and forced ones differs from S."""
    from learn import full_space as FS
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    bad = []
    for tag, fams in TAGS.items():
        hold = hold_spec(union, fams)
        for key, by in answers.items():
            amp = amp_of(key)
            for _, a in by.items():
                S = ms[amp][a["cls"]][1]
                y = P.hold_outside_space(LO.tdict(a["settings"]), S, amp, hold)
                w, f = hold(amp, S)
                base = FS.sections_on(dict(S))
                bad += [(tag, key, k) for k in y if k not in w and k not in f and y[k] != base.get(k)]
    return bad


def cmd_check(_args):
    """Zero renders: C2's state (written of 520; refuses nothing), the label sources and mask sizes on what is written,
    whether the training would refuse, and the hold on stored FTm answers: C3-core equal to `hold_outside_space`, and
    no untrained key off S in any tag."""
    from learn import pipeline_fix as P

    P.require(PHASE)
    st = c2_state(partial=True)
    src = sources(st)
    ms = P.A_menu_S()
    kf = keys_fn(src)
    sizes = {}
    for (u, amp), s in src.items():
        cls = next(r["cls"] for r in st["records"] if r["unit"] == u and r["amp"] == amp)
        sizes.setdefault(f"{s['block']}:{s['kind']}", []).append(len(kf(u, amp, ms[amp][cls][1])))
    try:
        c2_state()
        refuses = None
    except SystemExit as e:
        refuses = str(e)
    union = trained_union(st)
    ans, n_all, bad_all, off = {}, 0, [], []
    for d in (P.REAL_DIR, P.GOAT_DIR):
        f = P.out_dir() / d / "answers" / f"{FTM_TAG}.json"
        a = json.loads(f.read_text())
        cls_of = ({p["unit"]: p["cls"] for p in a["parts"]} if "parts" in a
                  else {p["unit"]: p["cls"] for p in P.goat_read_units()})
        some = dict(sorted(a["answers"].items())[::7])
        tagged = {k: {h: dict(v, cls=cls_of[k.rsplit("|", 1)[0]]) for h, v in by.items()} for k, by in some.items()}
        n, bad = hold_equal_core(tagged, ms, union, lambda k: k.rsplit("|", 1)[1])
        n_all += n
        bad_all += bad
        off += untrained_at_S(tagged, ms, union, lambda k: k.rsplit("|", 1)[1])
    rep = {"c2_written": st["written"], "c2_sha256_partial": st["sha256"], "training_refuses": refuses,
           "sources": source_counts(src),
           "mask_sizes": {k: {"min": min(v), "max": max(v), "n": len(v)} for k, v in sorted(sizes.items())},
           "union_sizes": {a: len(v) for a, v in sorted(union.items())},
           "core_hold_equal": {"compared": n_all, "differ": len(bad_all), "first": bad_all[:3]},
           "untrained_off_S": {"n": len(off), "first": [list(map(str, x)) for x in off[:3]]}}
    P.save(c3_dir() / "check.json", dict(rep, time=time.strftime("%Y-%m-%d %H:%M:%S")))
    print(json.dumps(rep, indent=1))


# --- FTm's hash checks (renders) ---------------------------------------------------------------------------------------

def cmd_recheck(_args):
    """A few of FTm's stored BKS and GOAT judge files (RECHECK_N each, seeded) rendered again exactly as `real-render` and
    `goat-render` render them (a fresh primed process per half), the hashes compared, as H4a checked FTm on N12. FTm is
    re-rendered in full only if they don't match. -> c3/recheck.json; refuses (after saving) on any mismatch."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(PHASE)
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    bans = json.loads((P.out_dir() / P.REAL_DIR / "answers" / f"{FTM_TAG}.json").read_text())
    gans = json.loads((P.out_dir() / P.GOAT_DIR / "answers" / f"{FTM_TAG}.json").read_text())["answers"]
    parts = {p_["unit"]: p_ for p_ in bans["parts"]}
    gunits = {p_["unit"]: p_ for p_ in P.goat_read_units()}
    rows, renders = [], 0
    for kind, jd, ans, by in (("bks", P.out_dir() / P.REAL_DIR / "judge" / FTM_TAG, bans["answers"], parts),
                              ("goat", P.out_dir() / P.GOAT_DIR / "judge" / FTM_TAG, gans, gunits)):
        for f in P.ft_recheck_pick([q.name for q in jd.glob("*.json")], RECHECK_N, f"c3|{kind}"):
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            old = json.loads((jd / f).read_text())
            if old["unit"] not in by:
                raise SystemExit(f"{jd / f}: its unit is no longer a read unit")
            prt = by[old["unit"]]
            key = P.real_key(prt, old["amp"])
            if old["answers_sha256"] != P.answers_sha(ans if kind == "bks" else {key: ans[key]}):
                raise SystemExit(f"{jd / f}: rendered from other answers than the stored file holds now")
            di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
            for search, a in sorted(ans[key].items()):
                st = LO.tdict(a["settings"])
                y = np.asarray(AM.fresh_render(CB.new_renderer, di32, a["select"], st, st), np.float64)[trim[0]:trim[1]]
                renders += 2
                new = AM.audio_sha(y)
                rows.append({"kind": kind, "file": f, "half": search, "stored": old["render_sha256"][search],
                             "new": new, "same": new == old["render_sha256"][search]})
    miss = [r_ for r_ in rows if not r_["same"]]
    P.save(c3_dir() / "recheck.json", {"ledger": f"{P.LEDGER_ID} {PHASE}", "rows": rows, "renders": renders,
                                       "mismatched": len(miss), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"C3-RECHECK: {len(rows) - len(miss)} of {len(rows)} FTm renders identical; {renders} renders, priming "
          "included", flush=True)
    if miss:
        raise SystemExit(f"C3-RECHECK: {len(miss)} renders differ from FTm's stored ones: re-render FTm in full")
    print("C3-RECHECK DONE")


# --- N12 against its C1b labels, and the BKS amp read (zero renders) ---------------------------------------------------

def cmd_n12(args):
    """N12's units: C3's held-half judge (`score_ear h4-render`'s C3-ftm records) against the unit's C1b label's fresh
    final, ln(d_C3 / d_C1b), clustered by band; measurement only."""
    from learn import full_controls_c1b as C1B
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import score_ear as SE

    P.require(PHASE)
    units, recs, _ = SE.wide_units()
    root, sub = C1B.OUT_DIRS["n12"]
    v, bad, missing = [], 0, []
    for u in units:
        j = SE.h4_judged("C3-ftm", SE.slug_of(u["unit"]))
        p = P.out_dir() / root / sub / f"{(u['unit'] + '|' + u['amp']).replace('/', '__')}.json"
        if j is None or not p.exists():
            missing.append(u["unit"])
            continue
        c = json.loads(p.read_text())
        if c["held"] != j["held"]:
            raise SystemExit(f"{u['unit']}: C1b's held half differs from the read's")
        d = (((c.get("fresh") or {}).get("final") or {}).get("judge") or {}).get(c["held"])
        if not (finite_pos(j["judge"]) and finite_pos(d)):
            bad += 1
            continue
        v.append((u["player"], math.log(float(j["judge"]) / float(d))))
    rep = {"phase": PHASE, "read": "N12, ln(d_C3 / d_C1b label) on the held half, clustered by band; measurement only",
           "units": len(units), "missing": missing, "non_finite": bad, "row": SE.interval(v, PS.t90),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(args.out, rep)
    print(json.dumps({k: rep[k] for k in ("units", "missing", "non_finite", "row")}, indent=1, default=str))


def amp_value(held, pick):
    """One BKS unit and half: ln(held judge of the picked amp) less the mean ln held judge over the amps (F69's
    blind choice). held: {amp: judge}. -> value or None."""
    logs = {a: math.log(float(v)) for a, v in held.items() if finite_pos(v)}
    if pick not in logs or len(logs) < 2:
        return None
    return logs[pick] - sum(logs.values()) / len(logs)


def amp_rows(parts, amp_p, judge, amps, head_amps):
    """BKS's amp read rows: per unit and search half, the head's pick (its probabilities on the first amp input that has
    them; the head reads the audio only) and `amp_value` on the held half of each amp's render. judge: {(unit, amp):
    a judge file's "judge", {search half: {half: value}}}; amp_p: {key: {search half: [p per head amp]}}.
    -> [(DI, unit, value)]."""
    rows = []
    for prt in parts:
        for sh, h in (("A", "B"), ("B", "A")):
            ps = [(amp_p.get(f"{prt['unit']}|{a}") or {}).get(sh) for a in amps]
            ps = [q for q in ps if q]
            if not ps:
                continue
            pick = head_amps[max(range(len(ps[0])), key=lambda i: ps[0][i])]
            held = {a: ((judge.get((prt["unit"], a)) or {}).get(sh) or {}).get(h) for a in amps}
            val = amp_value(held, pick)
            if val is not None:
                rows.append((prt["di"], prt["unit"], val))
    return rows


def cmd_amp(args):
    """BKS: the amp pick of W's amp head on C3's body (the head is masked on real rows by `loss_fn`'s `keep`) against a
    blind choice, from C3's per-amp renders, clustered by DI. Zero renders."""
    from learn import full_space as FS
    from learn import pipeline_fix as P

    P.require(PHASE)
    ans = json.loads((P.out_dir() / P.REAL_DIR / "answers" / "C3-ftm.json").read_text())
    judge = {}
    for p_ in (P.out_dir() / P.REAL_DIR / "judge" / "C3-ftm").glob("*.json"):
        r = json.loads(p_.read_text())
        judge[(r["unit"], r["amp"])] = r["judge"]
    rows = amp_rows(ans["parts"], ans.get("amp_p") or {}, judge, P.AMPS3, FS.AMPS)
    if not rows:
        raise SystemExit("c3-amp: no row (no amp probabilities or no finite held judges)")
    rep = {"phase": PHASE, "read": "W's amp head on C3's body (masked on real rows): the picked amp's held judge less "
           "the mean over the three amps, ln, clustered by DI", "row": P.clustered(rows),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(args.out, rep)
    print(json.dumps(rep["row"], indent=1, default=str))


# --- adoption ------------------------------------------------------------------------------------------------------------

# --- C3b: the amp head on real rows (phase_c3b) ------------------------------------------------------------------------

def usable_pair(rec):
    """A label's (search judge, held judge), or None: a label, finite halves, the best's peak at or above -57 dBFS."""
    if rec is None or rec.get("label") is None or rec.get("fallback_reason"):
        return None
    b = rec.get("best") or {}
    j, pk = b.get("judge") or {}, b.get("peak_dbfs")
    s, h = j.get(rec.get("search")), j.get(rec.get("held"))
    if pk is None or float(pk) < AMP_USABLE_DBFS or not (finite_pos(s) and finite_pos(h)):
        return None
    return float(s), float(h)


def label_argmin(pairs):
    """{amp: (search, held)} -> the amp with the lowest search judge, ties to the first in sorted order, or None."""
    return min(sorted(pairs), key=lambda a: pairs[a][0]) if pairs else None


def bks_unit_labels():
    """BKS's stored labels per unit: {unit: {amp: record}} (`real_labels(2)`)."""
    from learn import pipeline_fix as P

    recs, _, _ = P.real_labels(2)
    out = {}
    for r in recs:
        out.setdefault(r["unit"], {})[r["amp"]] = r
    return out


def goat_unit_labels():
    """GOAT's three like-for-like labels per unit: the stored forced amp's (`goat_labels`) and C2b's two.
    -> {unit: {amp: record}}."""
    from learn import pipeline_fix as P

    out = {}
    for r in P.goat_labels()[0]:
        out.setdefault(r["unit"], {})[r["amp"]] = r
    for p_ in (P.out_dir() / P.GOAT_DIR / "search-c2b").glob("*.json"):
        r = json.loads(p_.read_text())
        if r["unit"] in out:
            out[r["unit"]][r["amp"]] = r
    return out


def amp_labels():
    """C3b's amp label per unit, on the stored recipe for both sets (the user's choice, 2026-11-11): GOAT's from C2b's
    report (its argmin), BKS's the argmin over its three stored labels, both by `usable_pair`. Refuses an incomplete C2b.
    -> {unit: amp}."""
    from learn import pipeline_fix as P

    rep = json.loads((P.out_dir() / "c2b" / "report.json").read_text())
    if not rep.get("complete"):
        raise SystemExit("C2b's report is not complete: no GOAT amp labels")
    out = {u: v["amp"] for u, v in rep["labels"].items() if v.get("amp")}
    for u, recs in bks_unit_labels().items():
        a = label_argmin({amp: q for amp, q in ((amp, usable_pair(r)) for amp, r in recs.items()) if q})
        if a is not None:
            out[u] = a
    return out


def amp_labels_sha(labels):
    return hashlib.sha256(json.dumps(sorted(labels.items())).encode()).hexdigest()


def amp_label_rows(Y, rows, labels):
    """Every real row (training or held) takes its unit's amp label in the amp head's slot (`Y[6]`, `full_space.AMPS`'
    order) in place of -100. Refuses a real row whose unit has no label. -> the number of rows labelled."""
    from learn import full_space as F

    n, missing = 0, []
    for j, r in enumerate(rows):
        if "real" in r:
            a = labels.get(r["real"])
            if a is None:
                missing.append(r["real"])
                continue
            Y[6][j] = F.AMPS.index(a)
            n += 1
    if missing:
        raise SystemExit(f"{len(missing)} real rows have no amp label (first {missing[0]})")
    return n


def head_pick(amp_p, unit, half, head_amps):
    """The amp head's pick for a unit from its input on `half`: argmax of its probabilities on the first record of the
    unit that has them (the head reads the audio only). amp_p: {"unit|amp": {half: [p per head amp]}}. -> amp or None."""
    for key in sorted(k for k in amp_p if k.split("|")[0] == unit):
        p = (amp_p[key] or {}).get(half)
        if p:
            return head_amps[max(range(len(p)), key=lambda i: p[i])]
    return None


def stage1_rows(unit_labels, picks, cluster_of):
    """Stage 1's rows: per unit, `amp_value` of each pick on its labels' held halves (the pick made from the input on the
    labels' search half). unit_labels: {unit: {amp: record}}; picks: {name: {unit: amp}}. -> {name: [(cluster, unit,
    value)]}, plus "label" (the labels' own argmin: the ceiling) and the pairwise "C3b - W"."""
    out = {n: [] for n in list(picks) + ["label", "C3b - W"]}
    for u, recs in sorted(unit_labels.items()):
        pairs = {a: q for a, q in ((a, usable_pair(r)) for a, r in recs.items()) if q}
        if len(pairs) < 2:
            continue
        held = {a: q[1] for a, q in pairs.items()}
        vals = {n: amp_value(held, p[u]) for n, p in picks.items() if u in p}
        for n, v in vals.items():
            if v is not None:
                out[n].append((cluster_of(u), u, v))
        lv = amp_value(held, label_argmin(pairs))
        if lv is not None:
            out["label"].append((cluster_of(u), u, lv))
        if vals.get("C3b") is not None and vals.get("W") is not None:
            out["C3b - W"].append((cluster_of(u), u, vals["C3b"] - vals["W"]))
    return out


def stage1_reading(row):
    """Stage 1's declared reading of `C3b - blind` judged by C3's test: "learns" (better, never worse), "worse", "split"
    or "undecided"."""
    d = direction(row)
    return "learns" if d == "better" else d


def cmd_c3b(args):
    """C3b's stage 1 at zero renders -> c3/c3b-stage1.json: on BKS's read units (by DI) and GOAT's (by item), the trained
    head's pick (C3b's answers), W's pick on C3's body (C3-cabS's answers) and the labels' argmin, each against a blind
    pick on the labels' held halves, and C3b - W; pooled with C3's equal weights; the declared reading."""
    from learn import full_space as FS
    from learn import pipeline_fix as P

    P.require(C3B_PHASE)
    sets = {}
    for name, d, ul, cl in (("bks", P.REAL_DIR, bks_unit_labels(), lambda u: u.split("@")[0]),
                            ("goat", P.GOAT_DIR, goat_unit_labels(), lambda u: u.split("/")[1].split("@")[0])):
        ans = {t: json.loads((P.out_dir() / d / "answers" / f"{t}.json").read_text()).get("amp_p") or {}
               for t in (C3B_TAG, "C3-cabS")}
        read_units = {k.split("|")[0] for k in ans[C3B_TAG]}
        ul = {u: v for u, v in ul.items() if u in read_units}
        half = {u: next(iter(v.values()))["search"] for u, v in ul.items()}
        picks = {n: {u: a for u in ul if (a := head_pick(ans[t], u, half[u], FS.AMPS))}
                 for n, t in (("C3b", C3B_TAG), ("W", "C3-cabS"))}
        rows = stage1_rows(ul, picks, cl)
        sets[name] = {n: P.clustered(v) if v else None for n, v in rows.items()}
        sets[name]["units"] = len(ul)
        sets[name]["picks_by_amp"] = {n: {a: sum(1 for x in p.values() if x == a) for a in FS.AMPS}
                                      for n, p in picks.items()}
    names = ("C3b", "W", "label", "C3b - W")
    judged_rows = {n: judged(sets["bks"][n] or {}, sets["goat"][n] or {}) for n in names}
    rec = {"phase": C3B_PHASE, "sets": sets, "rows": judged_rows, "reading": stage1_reading(judged_rows["C3b"]),
           "against_W": direction(judged_rows["C3b - W"]), "labels_sha256": amp_labels_sha(amp_labels()),
           "c2_sha256": c2_sha(), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(c3_dir() / "c3b-stage1.json", rec)
    for n in names:
        j = judged_rows[n]
        p_ = j["pooled"] or {}
        print(f"{n} - blind: BKS {(j['bks'] or {}).get('mean')}, GOAT {(j['goat'] or {}).get('mean')}, pooled "
              f"{p_.get('mean')} [{p_.get('lo90')}, {p_.get('hi90')}]")
    print(f"C3B STAGE 1: {rec['reading']}; against W: {rec['against_W']}")


def report_rows(label="c3"):
    from learn import pipeline_fix as P

    b = json.loads((P.out_dir() / P.REAL_DIR / f"report-{label}.json").read_text())["rows"]
    g = json.loads((P.out_dir() / P.GOAT_DIR / f"report-{label}.json").read_text())["rows"]
    return b, g


def c3i_pairs():
    """C3i's report pairs (`real-report` and `goat-report --pairs ... --label c3i`)."""
    return ",".join(f"{a}:{b}" for a, b in C3I_PAIRS)


def direction(j):
    """A judged row by C3's test: "worse" (a 90% interval wholly above 0 on BKS, GOAT or pooled), "better" (wholly below 0
    on one of them), "split" (both), else "undecided"."""
    rs = [r for r in (j.get("bks"), j.get("goat"), j.get("pooled")) if r]
    w = any(r.get("lo90") is not None and r["lo90"] > 0 for r in rs)
    b = any(r.get("hi90") is not None and r["hi90"] < 0 for r in rs)
    return "split" if w and b else "worse" if w else "better" if b else "undecided"


def c3i_reading(iso_ftm, core_iso):
    """C3i's declared reading (docs/full-controls-plan.md, "C3i in detail") from its two judged rows, C3i - FTm and C3 core
    - C3i: "split" (either row split; read per set, no follow-up), "both" (both worse), "labels" (C3i worse, the other
    not), "objective" (C3 core - C3i worse, C3i not), else "neither"."""
    a, b = direction(iso_ftm), direction(core_iso)
    if "split" in (a, b):
        return "split"
    if a == "worse":
        return "both" if b == "worse" else "labels"
    return "objective" if b == "worse" else "neither"


def cmd_c3i(args):
    """C3i's rows from its reports (`--label c3i`) -> c3/c3i.json: each pair judged on BKS, GOAT and pooled, and the
    declared reading. A diagnostic: it adopts and replaces nothing."""
    from learn import pipeline_fix as P

    P.require(C3I_PHASE)
    b, g = report_rows("c3i")
    rows = {}
    for a_, b_ in C3I_PAIRS:
        n = row_name(a_, b_)
        if n not in b or n not in g:
            raise SystemExit(f"{n}: not in both C3i reports")
        rows[n] = judged(b[n], g[n])
    reading = c3i_reading(rows[row_name(C3I_TAG, FTM_TAG)], rows[row_name("C3-core", C3I_TAG)])
    rec = {"phase": C3I_PHASE, "rows": rows, "directions": {n: direction(j) for n, j in rows.items()}, "reading": reading,
           "follow_up": reading in ("objective", "both"), "c2_sha256": c2_sha(),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(c3_dir() / "c3i.json", rec)
    for n, j in rows.items():
        p_ = j["pooled"] or {}
        print(f"{n}: BKS {j['bks'].get('mean')}, GOAT {j['goat'].get('mean')}, pooled {p_.get('mean')} "
              f"[{p_.get('lo90')}, {p_.get('hi90')}]; shown worse {j['shown_worse']}")
    print(f"C3I READING: {reading}")


def cmd_adopt(args):
    """The per-family adoption from the C3 reports (`real-report` and `goat-report --label c3`) -> c3/adoption.json;
    with --final, the adopted configuration against FTm (`--label c3-adopt` when it needed its own tag) ->
    c3/decision.json."""
    from learn import pipeline_fix as P

    P.require(PHASE)
    b, g = report_rows()
    if not args.final:
        a = adoption(b, g)
        rec = dict(a, c2_sha256=c2_sha(), needs_own_tag=a["config_tag"] == ADOPT_TAG,
                   isolation_run_needed=a["core_shown_worse"],   # C3 core worse than FTm: FTm's mask on C2's labels
                   time=time.strftime("%Y-%m-%d %H:%M:%S"))
        P.save(c3_dir() / "adoption.json", rec)
        print(json.dumps({k: rec[k] for k in ("adopted", "at_S", "config_tag", "needs_own_tag", "core_shown_worse")},
                         indent=1))
        for n, j in rec["comparisons"].items():
            p_ = j["pooled"] or {}
            print(f"{n}: BKS {j['bks'].get('mean')}, GOAT {j['goat'].get('mean')}, pooled {p_.get('mean')} "
                  f"[{p_.get('lo90')}, {p_.get('hi90')}]; shown worse {j['shown_worse']}")
        return
    a = json.loads((c3_dir() / "adoption.json").read_text())
    tag = a["config_tag"]
    if tag == ADOPT_TAG:
        b, g = report_rows("c3-adopt")
    d = dict(replacement(b, g, tag), adopted=a["adopted"], at_S=a["at_S"], time=time.strftime("%Y-%m-%d %H:%M:%S"))
    P.save(c3_dir() / "decision.json", d)
    print(json.dumps({k: d[k] for k in ("tag", "adopted", "at_S", "replaces_ftm", "shown_worse")}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("c3-check").set_defaults(fn=cmd_check)
    s = sub.add_parser("c3-gate")
    s.add_argument("out")
    s.set_defaults(fn=cmd_gate)
    sub.add_parser("c3-recheck").set_defaults(fn=cmd_recheck)
    s = sub.add_parser("c3-n12")
    s.add_argument("out")
    s.set_defaults(fn=cmd_n12)
    s = sub.add_parser("c3-amp")
    s.add_argument("out")
    s.set_defaults(fn=cmd_amp)
    sub.add_parser("c3i-rows").set_defaults(fn=cmd_c3i)
    sub.add_parser("c3b-rows").set_defaults(fn=cmd_c3b)
    s = sub.add_parser("c3-adopt")
    s.add_argument("--final", action="store_true")
    s.set_defaults(fn=cmd_adopt)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
