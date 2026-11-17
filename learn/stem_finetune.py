"""Step 6, fine-tune on what the product feeds (`docs/stem-finetune-plan.md`; ledger `pipeline-fix`: `phase_s6`,
`phase_s6_noise`; ledger `preset-ladder`: `phase_l6_noise`). Only stages 0 and N are built (plan section 5.1):

    # stage 0 (zero renders, CPU): the controls and the seed-to-seed gauge
    $TORCH_PY -m learn.stem_finetune stage0
    # stage N: R-rep's 16 runs, then the same-seed replay's 2, one MPS job at a time (`pipeline_fix train-ft`)
    $TORCH_PY -m learn.pipeline_fix train-ft --masked --ft-cap 300 --c3r all --c3r-rep rep --seed 20261181 \\
        --real-fold 0 --inner                         # ... every fold, both seeds, inner runs first, then FT_k
    $TORCH_PY -m learn.pipeline_fix train-ft --masked --ft-cap 300 --c3r all --c3r-rep replay --seed 20261043 \\
        --real-fold 3 --inner                         # then the same without --inner
    $TORCH_PY -m learn.stem_finetune answers          # rep-xl@-3, ens4-xl@-3, sic-rep-xl@-3, rc-rep-xl@-3, the gauges
    .venv/bin/python -m learn.preset_ladder render --rows rep-xl@-3,rc-rep-xl@-3,ens4-xl@-3 --shard 0/3
    .venv/bin/python -m learn.stem_finetune report-n  # N_TABLE's cell, read only after the rows are saved

R-rep is R-all's recipe (`train-ft --masked --ft-cap 300 --c3r all`) on C3r's folds, rows, drops, masks and two-source
mix, with two new fine-tune seeds (`REP_SEEDS`), each starting from one of W's two NS-best states. A run's seed sets
torch's seed and the epoch order; D_fix's variant draws and C3r's source orders are seeded by the row, the epoch and the
fold, not by the run's seed, so R-rep measures the fine-tune's seed noise only. R-rep's runs and the replay's are
written under their own bases (`REP_BASES`): `rep_write_refusal` stops a run whose name is not its base's, or whose files
exist, before any work.

The tables `S0_TABLE`, `N_TABLE`, `P_TABLE` and `S6_TABLE` (with the noise rule and S6-level's sub-rule) are declared
here before any run and tested in `tests/test_stem_finetune.py`; `table_guard` refuses a command if they are broken.
`P_TABLE` and `S6_TABLE` are coded now so stage N's result can't shape them; nothing else of the pilot is built.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time

PLAN = "docs/stem-finetune-plan.md"
PHASE_S6, PHASE_NOISE = "phase_s6", "phase_s6_noise"     # ledger pipeline-fix
PHASE_L6_NOISE = "phase_l6_noise"                        # ledger preset-ladder (`preset_ladder.L6_PHASE`)
OUT = "step6"
FOLDS = 4
R_ALL_SEEDS = (20261042, 20261043)                       # `pipeline_fix.SEEDS`: R-all's seeds, and W's
REP_SEEDS = {20261181: 20261042, 20261182: 20261043}    # R-rep's fine-tune seed -> the W state (W's seed) it starts from
REP_BASES = {"rep": "C3r-rep", "replay": "C3r-replay"}
REPLAY = (3, 20261043)                                   # the same-seed replay: fold 3's inner run and FT_3, this seed
R_ALL_BASE = "C3r-all"
REP_RATE = (1e-4, 300)                                   # R-all's (lr, cap): `pipeline_fix.FT_LR` and `--ft-cap 300`
PROTECTED_BASES = ("C3r-all", "C3r-ctl", "C3r-allK", "C3r-ctlK")   # `full_controls_c3r.BASE`: never written here
KEEP_ENS4 = True                                         # the optional row, kept (plan section 4; the review's note):
                                                         # a beside row with no table; any action needs its own declaration
READINGS = ("better", "undecided", "worse")
DECIDING = ("bks", "goat", "panel")

S0_TABLE = (                          # (code, when, next): the first that holds (plan section 5.1)
    ("S0-fail", "a control fails or a stored hash differs", "stop; reported"),
    ("S0-ok", "none of those", "stage N; the seed-to-seed distances are reported, with no reading attached"))

N_ROWS = {"N": "rep-xl@-3 - xl@-3"}
N_BESIDE = ("rc-rep-xl@-3 - rc-xl@-3", "rc-rep-xl@-3 - cen") + (("ens4-xl@-3 - xl@-3",) if KEEP_ENS4 else ())
N_TABLE = (                           # (N readings, code, next): each reading once (plan section 5.1)
    (("undecided",), "N-quiet",
     "stop and hand back; nothing starts by itself. The half-width and what the interval rules out are reported as "
     "the noise's size. The pilot starts only on the user's answer to open question 1"),
    (("better", "worse"), "N-loud",
     "stop: two trainings of one recipe differ by the score. To the user, with N, the replay and the seed-to-seed "
     "gauge: a second repeat to size the noise (114.4 run-minutes, 27 min of renders a row), or end Step 6. The "
     "write-up names the earlier model-against-model reads that carry the same doubt; none is changed"))

P_ROWS = {"P": "s2-xl@-3 - xl@-3", "P2": "s2-xl@-3 - rep-xl@-3", "Q": "rc-s2-xl@-3 - rc-xl@-3"}
P_TABLE = (                           # (P, P2, Q readings, code, next): each of the 27 triples once (plan section 5.1)
    (("better",), ("better",), ("better", "undecided"), "P-go",
     "the full build and run. The write-up gives what Q's interval rules out; if its lower end is above -0.035, the "
     "ceiling's mean is ruled out at this dose, and that is said"),
    (("better",), ("better",), ("worse",), "P-aim",
     "stop: the stems moved the model's aim, which re-centring gives free, and the re-centred answer got worse. To "
     "the user"),
    (("undecided",), READINGS, READINGS, "P-flat",
     "stop. To the user with the intervals: at 2 stem variants a unit the answer on the product's input is not shown "
     "to move. Underpowered if P's lower end is beyond -0.05, and said so. Not failed"),
    (("worse",), ("worse",), READINGS, "P-worse", "stop; R-all stays; reported"),
    (("better",), ("undecided", "worse"), READINGS, "P-noise",
     "stop: not separable from training noise. To the user with N, P, P2 and Q"),
    (("worse",), ("better", "undecided"), READINGS, "P-noise",
     "stop: not separable from training noise. To the user with N, P, P2 and Q"))

S6_ROWS = {"G": "rc-s-xl@-3 - cen", "O": "rc-s-xl@-3 - rc-xl@-3", "O2": "rc-s-xl@-3 - rc-rep-xl@-3",
           "W": "s-xl@-3 - xl@-3", "W2": "s-xl@-3 - rep-xl@-3"}
S6_TABLE = (                          # (G readings, O readings, code, next): each of the nine pairs once (plan section 7)
    (("better",), ("better",), "S6-adopt",
     "if the noise rule holds: R-stem replaces R-all as the adopted model (ML's reviewed change), and the re-centred "
     "R-stem path is the default candidate. That goes to the user with the ladder read, Step 1's descriptive read and "
     "the ear"),
    (("better",), ("undecided",), "S6-user",
     "it beats Cen but is not shown better than R-all. To the user, with both intervals"),
    (("undecided", "worse"), ("better",), "S6-build",
     "if the noise rule holds: a gain over R-all on the product's input, not shown over Cen. By the adopt rule's "
     "second level: R-stem replaces R-all behind the flag and is the base for later work. Not the default; Cen stays "
     "Step 3's start"),
    (("undecided", "worse"), ("undecided",), "S6-level",
     "the likely cell, even if Step 6 works. No change of model. Not failed: the write-up gives what each interval "
     "rules out. Then by W (S6_LEVEL_SUB)"),
    (("undecided", "worse"), ("worse",), "S6-worse",
     "not adopted; R-all stays. 'Worse' is said only if O2 reads worse too"),
    (("better",), ("worse",), "S6-impossible",
     "the means add: O worse puts G's mean above +0.008. The report refuses and stops"))
S6_LEVEL_SUB = {                      # S6-level's sub-rule on W and W2
    "W and W2 better": "the stems fix the model's aim on the product's input without a table; that, with T, goes to the "
                       "product session as a choice for the flagged path",
    "otherwise": "nothing changes"}
S6_NOISE_CODES = ("S6-adopt", "S6-build", "S6-worse")   # the cells whose action needs O2 to read as O does
NOISE_HELD = "not separable from training noise: the write-up says so, and the choice goes to the user"


# --- the tables (pure) -----------------------------------------------------------------------------------------------------

def table_guard():
    """Refuse unless every declared table is whole: each reading (N), triple (P) or pair (S6) exactly once, the codes
    as declared; S0_TABLE's two codes in order. Every command calls it first."""
    if tuple(c for c, _, _ in S0_TABLE) != ("S0-fail", "S0-ok"):
        raise SystemExit("S0_TABLE's codes are not the two declared, in order")
    for n in READINGS:
        if sum(n in ns for ns, _, _ in N_TABLE) != 1:
            raise SystemExit(f"N_TABLE holds {n} not once")
    if {c for _, c, _ in N_TABLE} != {"N-quiet", "N-loud"}:
        raise SystemExit("N_TABLE's codes are not the two declared")
    for p in READINGS:
        for p2 in READINGS:
            for q in READINGS:
                if sum(p in ps and p2 in p2s and q in qs for ps, p2s, qs, _, _ in P_TABLE) != 1:
                    raise SystemExit(f"P_TABLE holds ({p}, {p2}, {q}) not once")
    if {c for *_, c, _ in P_TABLE} != {"P-go", "P-aim", "P-flat", "P-worse", "P-noise"}:
        raise SystemExit("P_TABLE's codes are not the five declared")
    for g in READINGS:
        for o in READINGS:
            if sum(g in gs and o in os_ for gs, os_, _, _ in S6_TABLE) != 1:
                raise SystemExit(f"S6_TABLE holds ({g}, {o}) not once")
    codes = [c for *_, c, _ in S6_TABLE]
    if len(set(codes)) != len(codes) or not set(S6_NOISE_CODES) <= set(codes):
        raise SystemExit("S6_TABLE's codes are not distinct or miss a noise cell")


def decided(row):
    """'better' (90% interval wholly below 0), 'worse' (wholly above), 'undecided'; None without an interval."""
    if not row or row.get("lo90") is None or row.get("hi90") is None:
        return None
    return "better" if row["hi90"] < 0 else "worse" if row["lo90"] > 0 else "undecided"


def s0_cell(controls):
    """(Pure.) S0_TABLE's code from the controls {name: passed}. An empty set of controls fails."""
    ok = bool(controls) and all(v is True for v in controls.values())
    code = "S0-ok" if ok else "S0-fail"
    return code, next(t for c, _, t in S0_TABLE if c == code)


def n_cell(n):
    """(Pure.) N_TABLE's row for N's reading. -> (code, next)."""
    table_guard()
    hit = [(c, t) for ns, c, t in N_TABLE if n in ns]
    if len(hit) != 1:
        raise SystemExit(f"N_TABLE has {len(hit)} rows for N {n}")
    return hit[0]


def p_cell(p, p2, q):
    """(Pure.) P_TABLE's row for the three readings. -> (code, next)."""
    table_guard()
    hit = [(c, t) for ps, p2s, qs, c, t in P_TABLE if p in ps and p2 in p2s and q in qs]
    if len(hit) != 1:
        raise SystemExit(f"P_TABLE has {len(hit)} rows for P {p}, P2 {p2}, Q {q}")
    return hit[0]


def s6_cell(g, o):
    """(Pure.) S6_TABLE's row for the two action readings. -> (code, next)."""
    table_guard()
    hit = [(c, t) for gs, os_, c, t in S6_TABLE if g in gs and o in os_]
    if len(hit) != 1:
        raise SystemExit(f"S6_TABLE has {len(hit)} rows for G {g}, O {o}")
    return hit[0]


def noise_rule(reading, rep_reading):
    """(Pure.) The noise rule (plan section 4): a reading of a row against R-all counts only if the same row against
    R-rep reads the same way. A missing R-rep reading holds the action."""
    return rep_reading is not None and reading == rep_reading


def n_outcome(rows):
    """(Pure.) Stage N's cell from the report's rows ({name: {"deciding_pool": row}}): N on the deciding pool by
    N_TABLE; a missing N refuses."""
    n = decided((rows.get(N_ROWS["N"]) or {}).get("deciding_pool"))
    if n is None:
        raise SystemExit(f"{N_ROWS['N']}: no reading (the report is incomplete)")
    code, nxt = n_cell(n)
    return {"N": n, "code": code, "next": nxt}


def s6_outcome(rows):
    """(Pure.) Step 6's reading (coded now, read only after the full run): G and O by S6_TABLE; the impossible cell
    refuses; the noise rule on S6-adopt, S6-build and S6-worse (their action fires only when O2 reads as O does);
    S6-level's sub-rule by W and W2. A missing G or O refuses."""
    def get(k, need=True):
        got = decided((rows.get(S6_ROWS[k]) or {}).get("deciding_pool"))
        if got is None and need:
            raise SystemExit(f"{S6_ROWS[k]}: no reading (the report is incomplete)")
        return got
    g, o = get("G"), get("O")
    code, nxt = s6_cell(g, o)
    if code == "S6-impossible":
        raise SystemExit(f"S6-impossible: G {g} with O {o} cannot occur while the means add; the report stops")
    out = {"G": g, "O": o, "code": code, "next": nxt, "fires": True}
    if code in S6_NOISE_CODES:
        o2 = get("O2", need=False)
        holds = noise_rule(o, o2)
        out["noise"] = {"O2": o2, "holds": holds}
        if not holds:
            out["fires"], out["next"] = False, NOISE_HELD
    if code == "S6-level":
        w, w2 = get("W", need=False), get("W2", need=False)
        out["sub"] = S6_LEVEL_SUB["W and W2 better" if (w, w2) == ("better", "better") else "otherwise"]
        out["W"], out["W2"] = w, w2
    return out


# --- R-rep's runs (pure) ---------------------------------------------------------------------------------------------------

def rep_w_seed(kind, seed):
    """The W state's seed a run starts from: R-rep's seed's mapped one, the replay's own."""
    return REP_SEEDS[seed] if kind == "rep" else seed


def rep_inner_keys(kind):
    """The (fold, seed) inner runs whose E a kind's FT_k reads: R-rep's eight, or the replay's one."""
    return [(q, sd) for q in range(FOLDS) for sd in REP_SEEDS] if kind == "rep" else [REPLAY]


def rep_refusal(kind, c3r, k, inner, seed, base):
    """(Pure.) Why `train-ft --c3r-rep` may not run, or None: R-all's recipe only (C3r's arm `all` on C3's recipe), a
    fold run (no all-labels pair at stage N: the pair is the full run's), R-rep's seeds only, and the replay's one
    (fold, seed) only."""
    if kind not in REP_BASES:
        return f"--c3r-rep in {tuple(REP_BASES)}"
    if c3r != "all" or base != R_ALL_BASE:
        return "--c3r-rep repeats R-all's recipe only: --c3r all on C3's recipe"
    if k is None:
        return "--c3r-rep trains fold runs only: R-rep's all-labels pair is the full run's"
    if kind == "rep" and seed not in REP_SEEDS:
        return f"--c3r-rep rep: --seed in {tuple(REP_SEEDS)} (R-all's seeds are R-all's)"
    if kind == "replay" and (k, seed) != REPLAY:
        return f"--c3r-rep replay: fold {REPLAY[0]} and --seed {REPLAY[1]} only"
    return None


def rep_names(kind):
    """Every run file (json and checkpoint) a kind writes, by `pipeline_fix.ft_name`'s rule at cap 300."""
    keys = rep_inner_keys(kind)
    out = []
    for q, sd in keys:
        out.append(f"{REP_BASES[kind]}-k{q}-inner-cap300-{sd}.json")
        out += [f"{REP_BASES[kind]}-k{q}-{sd}.json", f"{REP_BASES[kind]}-k{q}-{sd}-final.pt"]
    return out


def rep_write_refusal(kind, name, seed, inner, exists):
    """(Pure on `exists`.) Why a stage-N run may not start, or None: its name must be its kind's base and no protected
    base's, its seed not R-all's unless the replay, and none of the files it would write may exist (`exists(file
    name)`; the record's json was checked first, so this guards the checkpoint). Checked before any work."""
    base = REP_BASES.get(kind)
    if base is None or not (name == base or name.startswith(base + "-")):
        return f"{name}: not a {kind} run's name (base {base})"
    if any(name == b or name.startswith(b + "-") for b in PROTECTED_BASES):
        return f"{name}: a protected base's name"
    if kind == "rep" and seed in R_ALL_SEEDS:
        return f"{name}: R-all's seed {seed}"
    files = [f"{name}-{seed}.json"] + ([] if inner else [f"{name}-{seed}-final.pt"])
    there = [f for f in files if exists(f)]
    if there:
        return f"{name}: {there} already exist; move them aside first (never overwritten)"
    return None


# --- the knob gauges (pure on knob values) ---------------------------------------------------------------------------------

def moves(va, vb, group_of=None, group=None):
    """(Pure.) How far answers move between two sets of answers against how far they differ between parts, as
    `preset_ladder.knob_read`'s moves: va, vb {(part, head): (cell, unit value)}, on the keys both hold (and in
    `group` when given, by `group_of(head)`). -> {values, rms_move, rms_between_units}."""
    from learn import preset_ladder as L

    ks = sorted(k for k in set(va) & set(vb) if group is None or group_of(k[1]) == group)
    if not ks:
        return {"values": 0, "rms_move": None, "rms_between_units": None}
    mv = math.sqrt(sum((va[k][1] - vb[k][1]) ** 2 for k in ks) / len(ks))
    dev = L.within_cell([(va[k][0], k, va[k][1]) for k in ks])
    between = math.sqrt(sum(v ** 2 for v in dev.values()) / len(dev)) if dev else None
    return {"values": len(ks), "rms_move": mv, "rms_between_units": between}


def sha_json(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


# --- the commands ------------------------------------------------------------------------------------------------------

def step6_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT


def require_all():
    """The three phases, and the tables whole."""
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    table_guard()
    P.require(PHASE_S6)
    P.require(PHASE_NOISE)
    L.require_phase(PHASE_L6_NOISE)


def knob_vals(st, units, ans):
    """{(part and half, head): ((set, fold, amp, class, head), unit value)}: the knob values of one row's answers on
    heads the part's label holds, as `preset_ladder.knob_read` keys its moves."""
    from learn import local_objective as LO
    from learn import preset_ladder as L

    src, out = st["sources"], {}
    for ru in units:
        a = ans.get(ru["set"], {}).get(f"{ru['unit']}|{ru['amp']}")
        s = src.get((ru["unit"], ru["amp"]))
        if a is None or s is None:
            continue
        lab = L.knob_values(LO.sdict(LO.tdict(s["label"])), ru["amp"])
        for h, x in a.items():
            for n, v in L.knob_values(x["settings"], ru["amp"]).items():
                if n in lab:
                    out[((ru["unit"], ru["amp"], h), n)] = ((ru["set"], ru["fold"], ru["amp"], ru["prt"]["cls"], n), v)
    return out


def gauge(st, units, a, b):
    """Two rows' answers -> moves overall and per knob group (`moves`)."""
    from learn import preset_ladder as L

    va, vb = knob_vals(st, units, a), knob_vals(st, units, b)
    return dict({"all": moves(va, vb)}, **{g: moves(va, vb, L.group_of, g) for g in L.GROUP_NAMES})


def answer_row(st, units, models, feats_row, pick=None):
    """A row's answers, exactly as `preset_ladder.cmd_predict` makes them, from `feats_row`'s stored features by each
    part's fold's nets (`models` {fold: nets}; `pick` keeps some of them). -> (answers, missing)."""
    from learn import full_controls_c3r as R
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    ms, hold = P.A_menu_S(), R.answer_hold(st)
    out, missing = {}, []
    for ru in units:
        feats = L.load_feats(feats_row, ru)
        if feats is None:
            missing.append(f"{ru['unit']}|{ru['amp']}")
            continue
        nets = models[ru["fold"]] if pick is None else [models[ru["fold"]][j] for j in pick]
        sel, S = ms[ru["amp"]][ru["prt"]["cls"]]
        for h in ("A", "B"):
            s8, ls = feats[h]
            x, c = P.vreal_model_input(s8, ls, h, ru["amp"], ru["prt"]["cls"])
            out.setdefault(ru["set"], {}).setdefault(f"{ru['unit']}|{ru['amp']}", {})[h] = {
                "select": sel, "settings": LO.sdict(L.answer_of(nets, x, c, ru["amp"], S, hold))}
    return out, missing


def runs_manifest():
    """sha256 of every protected-base run file on disk (R-all's 18 records and 18 checkpoints among them)."""
    from learn import pipeline_fix as P

    od = P.out_dir() / "runs"
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(od.iterdir())
            if any(p.name.startswith(b + "-") for b in PROTECTED_BASES)}


def feats_manifest(units, row):
    """sha256 over a stored input row's feature files, one a unit, in order (missing files named)."""
    from learn import preset_ladder as L

    h, missing = hashlib.sha256(), []
    for ru in L.units_once(units):
        p = L.feat_path(row, ru)
        if not p.exists():
            missing.append(ru["unit"])
            continue
        h.update(p.name.encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return {"sha256": h.hexdigest(), "missing": missing}


STORED_ROWS = ("xl@-3", "mix@-3", "cen", "sic-xl@-3", "rc-xl@-3", "rc-mix@-3")   # the read's stored rows
COMPARATORS = ("xl@-3", "rc-xl@-3", "cen")              # the rows stage N's rows are read against
RC_CHECKED = (("rc-xl@-3", "cen"), ("rc-xl@-3", "xl@-3"))                       # report-rc rows re-derived


def row_mismatches(got, stored, tol=1e-9):
    """(Pure.) Every stored field of a `summarise` row (per set: `preset_ladder.ROW_FIELDS` and directions; the
    deciding pool's `POOL_FIELDS`) against a recomputed one. -> [problem]."""
    from learn import preset_ladder as L

    bad = []
    for s_ in L.SETS:
        for f in L.ROW_FIELDS + ("directions",):
            a, b = (got.get(s_) or {}).get(f), (stored.get(s_) or {}).get(f)
            if (a is None) != (b is None) or (a is not None and abs(a - b) > tol):
                bad.append(f"{s_} {f}: {a} against the stored {b}")
    for f in L.POOL_FIELDS:
        a, b = (got.get("deciding_pool") or {}).get(f), (stored.get("deciding_pool") or {}).get(f)
        if (a is None) != (b is None) or (a is not None and abs(a - b) > tol):
            bad.append(f"deciding pool {f}: {a} against the stored {b}")
    return bad


def read_row(st, units, a, b, band, seen):
    """One declared row, exactly as `preset_ladder.cmd_report_rc` summarises it. -> (summary, directions)."""
    from learn import preset_ladder as L

    got = L.rows_for_pair(st, units, L.value_fn(st, a), L.value_fn(st, b))
    row = L.summarise(got, units, band, seen_player=seen)
    row["directions_read"] = sum(len(v) for v in got.values())
    return row, got


def cmd_stage0(_args):
    """Stage 0 (zero renders, CPU; `phase_s6_noise`): the controls, then the seed-to-seed gauge. Controls: C3r's state
    equals the one every stored read row was made on; the ladder's controls passed; R-all's pairs reproduce the stored
    `xl@-3` and `mix@-3` answers from the stored features (equal sha256, the models those files name); the re-centred
    rows' sources equal today's files; every stored row's judge files were made from today's answers; report-rc's two
    rows re-derived field by field; the fold bans re-derived; free disk over the guard. The manifests of R-all's run
    files and of the stored features are saved for stage N to check against. Gauge: each fold pair's two seeds answered
    apart on the stored inputs, the moves between them per knob group, beside the moves between the inputs and between
    parts. -> PF/step6/stage0.json (never overwritten)."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import preset_ladder as L
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    require_all()
    out_p = step6_dir() / "stage0.json"
    if out_p.exists():
        raise SystemExit(f"{out_p} exists: stage 0 ran; any re-run is an amendment that moves it aside first")
    t0 = time.time()
    st = R.state()
    units = R.read_units(st)
    controls, notes = {}, {}
    stored = {r: json.loads(L.answers_path(r).read_text()) for r in STORED_ROWS}
    controls["state_same"] = all(d.get("c3r_sha256") == st["sha256"] for d in stored.values())
    try:
        L.controls_ok(2, st)
        controls["ladder_controls"] = True
    except SystemExit as e:
        controls["ladder_controls"], notes["ladder_controls"] = False, str(e)
    models = L.fold_models(st)
    shas = {str(k): v[1] for k, v in models.items()}
    nets = {k: v[0] for k, v in models.items()}
    rep_ans = {}
    for row in ("xl@-3", "mix@-3"):
        ans, missing = answer_row(st, units, nets, row)
        rep_ans[row] = ans
        same = (P.answers_sha(ans) == P.answers_sha(stored[row]["answers"]) and stored[row].get("models") == shas
                and sorted(missing) == sorted(stored[row].get("missing", [])))
        controls[f"answers_reproduce {row}"] = same
        notes[f"answers {row}"] = {"sha256": P.answers_sha(ans), "missing": len(missing)}
    for r in ("rc-xl@-3", "rc-mix@-3"):
        try:
            L.rc_sources_check(r)
            controls[f"rc_sources {r}"] = True
        except SystemExit as e:
            controls[f"rc_sources {r}"], notes[f"rc_sources {r}"] = False, str(e)
    for r in STORED_ROWS:
        if r == "sic-xl@-3":
            continue                                   # rendered in stage 2, read by no stage-N row
        try:
            notes[f"judge {r}"] = L.rc_complete(units, r)
            controls[f"judge_files {r}"] = True
        except SystemExit as e:
            controls[f"judge_files {r}"], notes[f"judge {r}"] = False, str(e)
    band = {u: v["band"] for u, v in L.lends()["units"].items()}
    seen = R.player_seen(st, units)
    rc_rep = json.loads((L.ladder_dir() / "report-rc.json").read_text())["rows"]
    for a, b in RC_CHECKED:
        got, _ = read_row(st, units, a, b, band, seen)
        bad = row_mismatches(got, rc_rep[f"{a} - {b}"])
        controls[f"stored_row {a} - {b}"] = not bad
        notes[f"stored_row {a} - {b}"] = {"mismatches": bad, "deciding_pool": got.get("deciding_pool")}
    bans = L.fold_bans(st, units, models)
    controls["fold_bans"] = not bans["problems"]
    notes["fold_bans"] = bans["problems"]
    free = PS.free_gb()
    controls["disk"] = free >= T.DISK_GUARD_GB
    notes["disk_free_gb"] = round(free, 1)
    manifest = {"runs": runs_manifest(), "feats": {r: feats_manifest(units, r) for r in ("xl@-3", "mix@-3")},
                "answers": {r: L.file_sha(L.answers_path(r)) for r in STORED_ROWS}}
    controls["r_all_runs_present"] = all(f"{R_ALL_BASE}-k{k}-{sd}.json" in manifest["runs"] and
                                         f"{R_ALL_BASE}-k{k}-{sd}-final.pt" in manifest["runs"]
                                         for k in range(FOLDS) for sd in R_ALL_SEEDS)
    controls["feats_complete"] = all(not v["missing"] for v in manifest["feats"].values())
    code, nxt = s0_cell(controls)
    seeds = {}
    if code == "S0-ok":                                # the gauge: each seed alone, on both stored inputs
        gdir = step6_dir() / "gauge"
        for j, sd in enumerate(R_ALL_SEEDS):
            for row in ("xl@-3", "mix@-3"):
                ans, _ = answer_row(st, units, nets, row, pick=[j])
                seeds[(sd, row)] = ans
                P.save(gdir / f"r-all-{sd}-{row}.json", {"plan": PLAN, "seed": sd, "row": row, "models": shas,
                                                         "c3r_sha256": st["sha256"], "answers": ans})
        g = {}
        for row in ("xl@-3", "mix@-3"):
            g[f"seed to seed on {row}"] = gauge(st, units, seeds[(R_ALL_SEEDS[0], row)], seeds[(R_ALL_SEEDS[1], row)])
            for sd in R_ALL_SEEDS:
                g[f"pair vs seed {sd} on {row}"] = gauge(st, units, stored[row]["answers"], seeds[(sd, row)])
        g["between inputs (pair, xl@-3 vs mix@-3)"] = gauge(st, units, stored["xl@-3"]["answers"],
                                                            stored["mix@-3"]["answers"])
    else:
        g = None
    out = {"plan": PLAN, "ledger": f"pipeline-fix {PHASE_NOISE}", "c3r_sha256": st["sha256"], "controls": controls,
           "notes": notes, "manifest": manifest, "models": shas, "cell": {"code": code, "next": nxt},
           "seed_gauge": g, "minutes": round((time.time() - t0) / 60, 2), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    out["cell"]["sha256"] = sha_json(out["cell"])
    P.save(out_p, out)
    for k_, v in controls.items():
        print(f"{'ok  ' if v else 'FAIL'} {k_}")
    if g:
        for name, d in g.items():
            print(f"{name}: " + "; ".join(f"{q} {d[q]['rms_move']:.4f}/{d[q]['rms_between_units']:.4f}"
                                          for q in d if d[q]["rms_move"] is not None))
    print(f"STAGE0 {code}")
    if code != "S0-ok":
        raise SystemExit("a stage 0 control failed: stage 0 stops")


def stage0_ok():
    """Refuse unless stage 0 ran and read S0-ok (stage N's training and reads all call it). -> stage 0's record."""
    p = step6_dir() / "stage0.json"
    if not p.exists():
        raise SystemExit("stage 0 has not run: stage N needs S0-ok (`stem_finetune stage0` first)")
    d = json.loads(p.read_text())
    if (d.get("cell") or {}).get("code") != "S0-ok":
        raise SystemExit("stage 0 did not read S0-ok: stage N stops")
    return d


def rep_models(st, kind="rep"):
    """{fold: (nets, model sha256s, run records)}: R-rep's FT_k pair per fold (its two seeds in REP_SEEDS's order), or
    the replay's FT_3 (fold 3 only); each run checked as `preset_ladder.fold_models` checks R-all's, and its `rep`
    record: kind, base and W seed as declared."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    out = {}
    keys = [(k, list(REP_SEEDS)) for k in range(FOLDS)] if kind == "rep" else [(REPLAY[0], [REPLAY[1]])]
    for k, sds in keys:
        nm = P.ft_name(k, base=REP_BASES[kind])
        nets, recs = zip(*(P.load_run(nm, sd, "best") for sd in sds))
        for r_ in recs:
            R.run_info_check(r_, st)
            rp = r_.get("rep") or {}
            if (rp.get("kind"), rp.get("base"), rp.get("w_seed")) != (kind, REP_BASES[kind],
                                                                       rep_w_seed(kind, r_["seed"])):
                raise SystemExit(f"{nm}-{r_['seed']}: not a declared {kind} run")
            if r_.get("inner") or r_["models"]["best"] != r_["models"]["final"] or r_.get("E") != r_.get("epochs_run"):
                raise SystemExit(f"{nm}-{r_['seed']}: not a read checkpoint at its E")
        out[k] = (list(nets), [r_["model_sha256"]["best"] for r_ in recs], list(recs))
    return out


def same_rows(rep, ref):
    """(Pure.) Problems where a stage-N fold run's rows or recipe differ from R-all's same fold's (C3r's info, the
    real-row inputs, the trained and held ids, the rate, cap, mask and real-row share). -> [problem]."""
    bad = []
    for f in ("train_units", "held_units", "train_records", "showings"):
        if (rep.get("c3r") or {}).get(f) != (ref.get("c3r") or {}).get(f):
            bad.append(f"c3r {f}")
    for f in ("inputs_sha256",):
        if (rep.get("c3r") or {}).get(f) != (ref.get("c3r") or {}).get(f):
            bad.append(f"c3r {f}")
    for f in ("ft_train_ids", "real_held_ids", "held_ids", "lr", "cap", "masked", "real_frac", "shuffle_real"):
        if rep.get(f) != ref.get(f):
            bad.append(f)
    return bad


def cmd_answers(_args):
    """Stage N's answers (zero renders, CPU; `phase_l6_noise`), after R-rep's 16 runs and the replay's 2: R-all's run
    files and the stored features unchanged since stage 0; every R-rep and replay run on R-all's rows (`same_rows`) and
    the fold bans re-derived; `rep-xl@-3` (R-rep's pair) and `ens4-xl@-3` (R-all's and R-rep's four seeds) on the stored
    `xl@-3` features; `sic-rep-xl@-3` and `rc-rep-xl@-3` by the ladder's own code (`cmd_sic`, `cmd_rc`); the gauges
    (R-rep seed to seed, R-rep against R-all, the replay against its stored run). -> ladder/answers/<row>.json,
    PF/step6/gauge-n.json."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    require_all()
    s0 = stage0_ok()
    st = R.state()
    if st["sha256"] != s0["c3r_sha256"]:
        raise SystemExit("C3r's state changed since stage 0")
    units = R.read_units(st)
    if runs_manifest() != s0["manifest"]["runs"]:
        raise SystemExit("a protected run file changed, appeared or went since stage 0")
    for r in ("xl@-3", "mix@-3"):
        if feats_manifest(units, r) != s0["manifest"]["feats"][r]:
            raise SystemExit(f"{r}'s stored features changed since stage 0")
    for r in STORED_ROWS:
        if L.file_sha(L.answers_path(r)) != s0["manifest"]["answers"][r]:
            raise SystemExit(f"{r}'s stored answers changed since stage 0")
    allm = L.fold_models(st)
    repm = rep_models(st, "rep")
    replay = rep_models(st, "replay")
    probs = []
    for k in range(FOLDS):
        for j in range(2):
            probs += [f"rep fold {k} seed {repm[k][2][j]['seed']}: {b}" for b in same_rows(repm[k][2][j], allm[k][2][j])]
    j43 = R_ALL_SEEDS.index(REPLAY[1])
    probs += [f"replay: {b}" for b in same_rows(replay[REPLAY[0]][2][0], allm[REPLAY[0]][2][j43])]
    bans = L.fold_bans(st, units, repm)
    probs += bans["problems"]
    if probs:
        raise SystemExit(f"stage N's runs differ from R-all's rows: {probs[:5]} ({len(probs)} problems)")
    rows = {"rep-xl@-3": {k: v[0] for k, v in repm.items()}}
    if KEEP_ENS4:
        rows["ens4-xl@-3"] = {k: allm[k][0] + repm[k][0] for k in range(FOLDS)}
    shas = {"rep-xl@-3": {str(k): v[1] for k, v in repm.items()},
            "ens4-xl@-3": {str(k): allm[k][1] + repm[k][1] for k in range(FOLDS)}}
    made = {}
    there = [L.answers_path(r) for r in list(rows) + ["sic-rep-xl@-3", "rc-rep-xl@-3"] if L.answers_path(r).exists()]
    if there:                                          # all four checked before any is written
        raise SystemExit(f"{[str(p) for p in there]} exist: never overwritten (move them aside first)")
    for row, nets in rows.items():
        ans, missing = answer_row(st, units, nets, "xl@-3")
        made[row] = ans
        L.save_answers(row, ans, {"c3r_sha256": st["sha256"], "models": shas[row], "missing": missing,
                                  "feats": "xl@-3", "stage0_sha256": L.file_sha(step6_dir() / "stage0.json")})
        print(f"ANSWERS {row}: {sum(len(v) for v in ans.values())} parts, {len(missing)} missing")
    L.cmd_sic(argparse.Namespace(rows="sic-rep-xl@-3"))
    L.cmd_rc(argparse.Namespace(rows="rc-rep-xl@-3"))
    stored = {r: json.loads(L.answers_path(r).read_text())["answers"] for r in ("xl@-3", "mix@-3")}
    single = {}
    for j, sd in enumerate(REP_SEEDS):
        single[sd] = answer_row(st, units, {k: v[0] for k, v in repm.items()}, "xl@-3", pick=[j])[0]
    r_all_single = {sd: json.loads((step6_dir() / "gauge" / f"r-all-{sd}-xl@-3.json").read_text())["answers"]
                    for sd in R_ALL_SEEDS}
    g = {"rep seed to seed on xl@-3": gauge(st, units, single[list(REP_SEEDS)[0]], single[list(REP_SEEDS)[1]]),
         "rep pair vs R-all pair on xl@-3": gauge(st, units, made["rep-xl@-3"], stored["xl@-3"])}
    for sd, wsd in REP_SEEDS.items():
        g[f"rep seed {sd} vs R-all seed {wsd} (same W state) on xl@-3"] = gauge(st, units, single[sd], r_all_single[wsd])
    if KEEP_ENS4:
        g["ens4 vs R-all pair on xl@-3"] = gauge(st, units, made["ens4-xl@-3"], stored["xl@-3"])
    u3 = [ru for ru in units if ru["fold"] == REPLAY[0]]
    rnets = {REPLAY[0]: replay[REPLAY[0]][0]}
    rp = {}
    for row in ("xl@-3", "mix@-3"):
        a = answer_row(st, u3, rnets, row)[0]
        b = json.loads((step6_dir() / "gauge" / f"r-all-{REPLAY[1]}-{row}.json").read_text())["answers"]
        b3 = {}
        for ru in u3:
            x = b.get(ru["set"], {}).get(f"{ru['unit']}|{ru['amp']}")
            if x is not None:
                b3.setdefault(ru["set"], {})[f"{ru['unit']}|{ru['amp']}"] = x
        rp[f"replay vs stored FT_3 seed {REPLAY[1]} on {row}"] = gauge(st, u3, a, b3)
        rp[f"answers identical on {row}"] = P.answers_sha(a) == P.answers_sha(b3)
    rrec, orec = replay[REPLAY[0]][2][0], allm[REPLAY[0]][2][j43]
    od = P.out_dir() / "runs"
    rin = json.loads((od / f"{REP_BASES['replay']}-k{REPLAY[0]}-inner-cap300-{REPLAY[1]}.json").read_text())
    oin = json.loads((od / f"{R_ALL_BASE}-k{REPLAY[0]}-inner-cap300-{REPLAY[1]}.json").read_text())
    rp["E"] = {"replay inner": rin["E"], "stored inner": oin["E"], "replay FT_3": rrec["E"], "stored FT_3": orec["E"]}
    rp["model identical"] = rrec["model_sha256"]["best"] == orec["model_sha256"]["best"]
    rp["minutes"] = {"replay inner": rin["minutes"], "replay FT_3": rrec["minutes"]}
    runs = {}
    for q in range(FOLDS):
        for sd in REP_SEEDS:
            ri = json.loads((od / f"{REP_BASES['rep']}-k{q}-inner-cap300-{sd}.json").read_text())
            rf = json.loads((od / f"{REP_BASES['rep']}-k{q}-{sd}.json").read_text())
            oi = json.loads((od / f"{R_ALL_BASE}-k{q}-inner-cap300-{REP_SEEDS[sd]}.json").read_text())
            runs[f"k{q} seed {sd}"] = {"E": ri["E"], "R-all E (same W state)": oi["E"], "inner epochs": ri["epochs_run"],
                                       "minutes": {"inner": ri["minutes"], "fold": rf["minutes"]},
                                       "at_cap": ri.get("at_cap")}
    out = {"plan": PLAN, "ledger": f"preset-ladder {PHASE_L6_NOISE}", "c3r_sha256": st["sha256"], "gauge": g,
           "replay": rp, "runs": runs, "run_minutes": round(sum(v["minutes"]["inner"] + v["minutes"]["fold"]
                                                                for v in runs.values()), 1),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(step6_dir() / "gauge-n.json", out)
    print(f"GAUGE-N saved; replay model identical {rp['model identical']}; E {rp['E']}")


def answers_check(row):
    """Refuse when a stage-N model row's answers were made from other run files than today's (`preset_ladder
    .cmd_render` calls it for every such row)."""
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    d = json.loads(L.answers_path(row).read_text())
    _, model = L.L6_MODEL_ROWS[row]
    od = P.out_dir() / "runs"
    for k, shas in d["models"].items():
        names = ([f"{REP_BASES['rep']}-k{k}-{sd}-final.pt" for sd in REP_SEEDS] if model == "rep" else
                 [f"{R_ALL_BASE}-k{k}-{sd}-final.pt" for sd in R_ALL_SEEDS]
                 + [f"{REP_BASES['rep']}-k{k}-{sd}-final.pt" for sd in REP_SEEDS])
        got = [hashlib.sha256((od / n).read_bytes()).hexdigest() for n in names]
        if got != shas:
            raise SystemExit(f"{row}: fold {k}'s models changed since its answers were made")


def cmd_report_n(_args):
    """Stage N's report (zero renders; `phase_l6_noise`): every stage-N row complete and made from today's answers;
    N and the beside rows per set and pooled (`preset_ladder.summarise`, as report-rc), N's adversarial read
    (`negatives`, leave-one-cluster-out); the rows are saved before N_TABLE's cell is read; the gauges beside.
    -> PF/step6/report-n.json."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    require_all()
    stage0_ok()
    st = R.state()
    units = R.read_units(st)
    names = ["rep-xl@-3", "rc-rep-xl@-3"] + (["ens4-xl@-3"] if KEEP_ENS4 else [])
    complete = {}
    for r in names:
        if L.row_info(r)["kind"] == "rc":
            L.rc_sources_check(r)
        else:
            answers_check(r)
        complete[r] = L.rc_complete(units, r)
    s0 = json.loads((step6_dir() / "stage0.json").read_text())
    for r in COMPARATORS:                              # the comparators: today's answers, as stage 0 hashed them
        if L.file_sha(L.answers_path(r)) != s0["manifest"]["answers"][r]:
            raise SystemExit(f"{r}'s stored answers changed since stage 0")
        complete[r] = L.rc_complete(units, r)
    band = {u: v["band"] for u, v in L.lends()["units"].items()}
    seen = R.player_seen(st, units)
    out = {"plan": PLAN, "ledger": f"preset-ladder {PHASE_L6_NOISE}", "c3r_sha256": st["sha256"], "complete": complete,
           "rows": {}, "negatives": {}}
    for name in (N_ROWS["N"],) + N_BESIDE:
        a, b = name.split(" - ")
        row, got = read_row(st, units, a, b, band, seen)
        out["rows"][name] = row
        if name == N_ROWS["N"]:
            out["negatives"][name] = dict(L.negatives(row, row["deciding_sets"]),
                                          leave_one_cluster_out={s: L.loo_range(got, units, s)
                                                                 for s in row["deciding_sets"]})
    out["gauge_n"] = json.loads((step6_dir() / "gauge-n.json").read_text())
    out["seed_gauge_stage0"] = json.loads((step6_dir() / "stage0.json").read_text())["seed_gauge"]
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(step6_dir() / "report-n.json", out)         # the rows are saved before the cell is read
    out["outcome"] = n_outcome(out["rows"])
    out["outcome"]["sha256"] = sha_json(out["outcome"])
    P.save(step6_dir() / "report-n.json", out)
    for name, row in out["rows"].items():
        dp = row.get("deciding_pool") or {}
        print(f"{name}: pool {dp.get('mean')} [{dp.get('lo90')}, {dp.get('hi90')}]; "
              + "; ".join(f"{s} {(row[s] or {}).get('mean')}" for s in L.SETS))
    print("N OUTCOME", json.dumps(out["outcome"]))


COMMANDS = {"stage0": cmd_stage0, "answers": cmd_answers, "report-n": cmd_report_n}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    args = ap.parse_args(argv)
    return COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
