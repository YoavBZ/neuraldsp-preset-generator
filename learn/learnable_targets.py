"""Step 5, targets the model can learn, and Step 3's R1 versions check (`docs/learnable-targets-plan.md`; ledger
`pipeline-fix`: `phase_s5`, `phase_s5_targets`, `phase_r1_versions`).

    .venv/bin/python -m learn.learnable_targets stage0       # Step 5's stage 0: the nine target sets, the controls, the
                                                             # head rows, the dose, the stored held-half cost, the
                                                             # learnability readout and its cell (zero renders, CPU)
    $TORCH_PY -m learn.learnable_targets versions            # Step 3: the adopted pair's answers on R1's stored versions
                                                             # (zero renders, zero separations, CPU; descriptive)

**The target rule** (plan section 4.3): per labelled record, among its stored, rendered and judged full settings (the
label, stage B's best, stage A's best and step 1's 200 trials, identical settings once) whose judge is finite on both
halves, those within `MARGIN` of the best in ln judge on the search half qualify; the target is the one nearest the
run's own Cen, by the sum of squares in `full_space` unit space over the heads the adopted answer writes that sound in
both the candidate and Cen (a switch or a mic counts 0 when equal, 1 when not). A tie goes to the better search-half
score, then the lower index (the label first). Each run uses the Cen of its own training records (`RUNS`, nine sets).
Rows follow `HEAD_RULE`. The tables `S0_TABLE` and `S5_TABLE` (with `S5_LEVEL_SUB` and the noise rule) are declared
here before any run and tested in `tests/test_learnable_targets.py`; `table_guard` refuses a run if they are broken.

Only stage 0 is built. The confirm, the fine-tune, the noise repeat and the ladder read are declared in the plan and
built only after stage 0 reads S0-rise, or on the user's word.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time

PLAN = "docs/learnable-targets-plan.md"
PHASE_S5, PHASE_S0, PHASE_VERSIONS = "phase_s5", "phase_s5_targets", "phase_r1_versions"
OUT = "step5"
MARGIN = 0.05                         # the heard-size floor (F65, `preset_ladder.SMALL`), borrowed per record
DOSE_MARGINS = (0.01, 0.02, 0.03, 0.05, 0.10)   # the dose table's margins (descriptive; only MARGIN builds targets)
BOOT_N, BOOT_SEED = 2000, 20261171    # the readout's cluster bootstrap
MIN_CELL = 5                          # a readout cell (amp, class, head) needs this many values (the planner's preview)
RAIL = 1e-6                           # an EQ band within this of 0 or 1 in unit space sits on its limit
FOLDS = 4
RUNS = tuple([f"fold{k}" for k in range(FOLDS)] + [f"inner{k}" for k in range(FOLDS)] + ["all"])
DECIDING = ("bks", "goat", "panel")
CAND_KINDS = ("label", "stage_b", "stage_a", "step1")

HEAD_RULE = (                         # (part, rule): how a target's training row is built from the label's (plan 4.4)
    ("written", "A head the adopted answer writes (C3-cabS's written keys, the forced EQ and gate switches out), the "
                "mic types included, takes the candidate's own value and keeps the label's training mask: it trains "
                "wherever, and only where, the label trains it."),
    ("unwritten", "A trained head the answer does not write (the left cab, the room mics, the right cab's phase) keeps "
                  "the label's row, its value and its mask, whatever the candidate."),
    ("count", "Stage 0 counts every head's training rows (showings) under the labels and under the targets, run by "
              "run, and refuses on any difference."))

S0_TABLE = (                          # (code, when, next): the first that holds (plan 4.6)
    ("S0-fail", "a control fails, or any head's training rows differ between the labels and the targets",
     "stop; reported"),
    ("S0-overfit", "the stored held-half cost of the all-labels targets against the labels has its whole 90% interval "
                   "beyond +MARGIN on the deciding pool",
     "stop: the search half's near-ties are not near-ties on the held half; a smaller margin is an amendment, reviewed "
     "first"),
    ("S0-flat", "the learnability readout's r(answer, target) - r(answer, label) over all written knob heads has a "
                "90% cluster-bootstrap interval that holds zero or lies below it",
     "stop before any render or training; to the user with the dose table and the readout: the line to the centre, or "
     "their word to run the step as approved. Not failed: the stored trials' dose is not shown to reach what the model "
     "reads"),
    ("S0-rise", "that interval lies wholly above zero",
     "on to the confirm (its own build and review); the size is reported beside the answers' r today, no bar on it"))

S5_TABLE = (                          # (G readings, O readings, code, next): each of the nine pairs once (plan 4.10)
    (("better",), ("better",), "S5-adopt",
     "if the noise rule holds: R-near replaces R-all as the adopted model (ML's reviewed change); the re-centred R-near "
     "path is the default candidate and goes to the user with the ladder read; Step 6 trains on R-near's targets"),
    (("better",), ("undecided",), "S5-user",
     "it beats Cen but is not shown better than R-all, so the adoption rule is not met: to the user, with both "
     "intervals"),
    (("better",), ("worse",), "S5-impossible",
     "cannot occur while R-near's rows read R-all's directions (G = O + rc-xl@-3 - cen): the report refuses and stops"),
    (("undecided", "worse"), ("better",), "S5-build",
     "if the noise rule holds: a gain over R-all, not shown over Cen; not the default, Cen stays Step 3's start; R-near "
     "replaces R-all behind the flag (a reviewed change) and is Step 6's base; the size is reported and built on"),
    (("undecided", "worse"), ("undecided",), "S5-level",
     "no change of model; not failed: the write-up gives what each interval rules out; then by R (S5_LEVEL_SUB)"),
    (("undecided", "worse"), ("worse",), "S5-worse",
     "the targets hurt on the product's input: not adopted, the raw labels stay and Step 6 trains on them; 'worse' is "
     "said only if O2 reads worse too (the noise rule)"))
S5_LEVEL_SUB = {                      # row S5-level's sub-rule on R = rc-n-mix@-3 - rc-mix@-3
    "better": "the reader gained on the ideal input and the stem hides it: Step 6 trains on R-near's targets",
    "not better": "the stored trials' dose did not show: Step 6 trains on the raw labels, and the stronger doses go "
                  "to the user with this read"}
NOISE_CODES = ("S5-adopt", "S5-build", "S5-worse")   # the cells whose action needs O2 to read as O does
NOISE_HELD = "not separable from training noise: the write-up gives N, O and O2, and the choice goes to the user"
S5_ROWS = {"G": "rc-n-xl@-3 - cen", "O": "rc-n-xl@-3 - rc-xl@-3", "R": "rc-n-mix@-3 - rc-mix@-3",
           "O2": "rc-n-xl@-3 - rcN-xl@-3", "N": "rcN-xl@-3 - rc-xl@-3"}
READINGS = ("better", "undecided", "worse")


# --- the tables (pure) -----------------------------------------------------------------------------------------------------

def table_guard():
    """Refuse unless the declared tables are whole: S5_TABLE holds each (G, O) pair once, its codes are distinct and
    cover the noise cells; S0_TABLE's codes are the four declared in order. Every command calls it first."""
    for g in READINGS:
        for o in READINGS:
            n = sum(g in gs and o in os_ for gs, os_, _, _ in S5_TABLE)
            if n != 1:
                raise SystemExit(f"S5_TABLE holds ({g}, {o}) {n} times, not once")
    codes = [c for *_, c, _ in S5_TABLE]
    if len(set(codes)) != len(codes) or not set(NOISE_CODES) <= set(codes):
        raise SystemExit("S5_TABLE's codes are not distinct or miss a noise cell")
    if tuple(c for c, _, _ in S0_TABLE) != ("S0-fail", "S0-overfit", "S0-flat", "S0-rise"):
        raise SystemExit("S0_TABLE's codes are not the four declared, in order")
    if tuple(p for p, _ in HEAD_RULE) != ("written", "unwritten", "count"):
        raise SystemExit("HEAD_RULE is not the three declared parts")


def decided(row):
    """'better' (90% interval wholly below 0), 'worse' (wholly above), 'undecided'; None without an interval."""
    if not row or row.get("lo90") is None or row.get("hi90") is None:
        return None
    return "better" if row["hi90"] < 0 else "worse" if row["lo90"] > 0 else "undecided"


def s5_cell(g, o):
    """(Pure.) S5_TABLE's row for the two action readings. -> (code, next)."""
    hit = [(c, t) for gs, os_, c, t in S5_TABLE if g in gs and o in os_]
    if len(hit) != 1:
        raise SystemExit(f"S5_TABLE has {len(hit)} rows for G {g}, O {o}")
    return hit[0]


def s5_outcome(rows):
    """(Pure.) Step 5's reading from the read's rows ({name: {"deciding_pool": row}}): G and O by S5_TABLE; the
    impossible cell refuses; S5-level's sub-rule by R; the noise rule on S5-adopt, S5-build and S5-worse (their action
    fires only when O2 reads as O does; without O2 it is held). A missing action row refuses."""
    table_guard()

    def get(k, need=True):
        got = decided((rows.get(S5_ROWS[k]) or {}).get("deciding_pool"))
        if got is None and need:
            raise SystemExit(f"{S5_ROWS[k]}: no reading (the report is incomplete)")
        return got
    g, o, r = get("G"), get("O"), get("R")
    code, nxt = s5_cell(g, o)
    if code == "S5-impossible":
        raise SystemExit(f"G {g} with O {o}: the cell that cannot occur; the report stops")
    out = {"G": g, "O": o, "R": r, "code": code, "next": nxt, "fires": True, "noise": None}
    if code == "S5-level":
        out["sub"] = S5_LEVEL_SUB["better" if r == "better" else "not better"]
    if code in NOISE_CODES:
        o2 = get("O2", need=False)
        out["noise"] = {"O2": o2, "N": get("N", need=False), "holds": o2 == o}
        if o2 != o:
            out["fires"], out["next"] = False, NOISE_HELD
    return out


def s0_cell(controls_ok, rows_equal, overfit, readout):
    """(Pure.) S0_TABLE's cell, the first that holds. overfit: the all-labels targets' held-half cost on the deciding
    pool ({lo90, hi90}); readout: the "all" difference row ({lo90, hi90}). A missing interval refuses."""
    table_guard()
    if not controls_ok or not rows_equal:
        return "S0-fail"
    if not overfit or overfit.get("lo90") is None or not readout or readout.get("lo90") is None:
        raise SystemExit("stage 0's cell needs the overfit and readout intervals")
    if overfit["lo90"] > MARGIN:
        return "S0-overfit"
    return "S0-rise" if readout["lo90"] > 0 else "S0-flat"


# --- the target rule (pure) ------------------------------------------------------------------------------------------------

def finite_pos(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v > 0


def candidates(out):
    """A labelled search output's candidates in `CAND_KINDS` order, each a stored full setting with its stored judge:
    the label (its fresh render's judge), stage B's best, stage A's best, step 1's trials (each on step 1's start
    settings). Identical settings once, the first kept (stage B's best is the label on every record). -> [(kind, index,
    settings {"module/key": stored}, judge {"A", "B"})]."""
    s1, s2 = out["step1"], out.get("step2") or {}
    raw = [("label", 0, out["label"], ((out.get("fresh") or {}).get("label") or {}).get("judge"))]
    for kind, sk, jk in (("stage_b", "stage_b_settings", "stage_b"), ("stage_a", "stage_a_settings", "stage_a")):
        if s2.get(sk) and s2.get(jk):
            raw.append((kind, 0, s2[sk], s2[jk]["judge"]))
    for i, t in enumerate(s1["trials"]):
        x = dict(s1["start_settings"])
        x.update(t["x"])
        raw.append(("step1", i, x, t["judge"]))
    seen, got = set(), []
    for c in raw:
        key = json.dumps(c[2], sort_keys=True)
        if key not in seen:
            seen.add(key)
            got.append(c)
    return got


def usable(judge, search, held):
    return bool(judge) and finite_pos(judge.get(search)) and finite_pos(judge.get(held))


def pick(ln_s, ok, dist, margin=MARGIN):
    """(Pure.) The target's index: among the usable candidates within `margin` of the best ln search-half judge, the
    nearest the centre; a tie to the better search-half score, then the lower index."""
    idx = [i for i in range(len(ln_s)) if ok[i]]
    if not idx:
        raise SystemExit("a record with no usable candidate")
    best = min(ln_s[i] for i in idx)
    q = [i for i in idx if ln_s[i] <= best + margin]
    return min(q, key=lambda i: (dist[i], ln_s[i], i))


def distances(enc, cen, written):
    """(numpy.) Each candidate's sum of squares to the centre over written heads sounding in both. enc: the candidates'
    encodes stacked (C, CM, S, SM, K, KM), each [n, heads]; cen: the centre's encode (c, cm, s, sm, k, km); written:
    (wc, ws, wk) 0/1 masks. -> [n]."""
    import numpy as np

    C, CM, S, SM, K, KM = enc
    c, cm, s, sm, k, km = cen
    wc, ws, wk = written
    mc = (CM > 0) & (cm > 0)[None, :] & (wc > 0)[None, :]
    ms = (SM > 0) & (sm > 0)[None, :] & (ws > 0)[None, :]
    mk = (KM > 0) & (km > 0)[None, :] & (wk > 0)[None, :]
    d = np.where(mc, (C - c[None, :]) ** 2, 0.0).sum(1)
    d = d + np.where(ms, (S != s[None, :]).astype(np.float64), 0.0).sum(1)
    return d + np.where(mk, (K != k[None, :]).astype(np.float64), 0.0).sum(1)


def target_row(lab, cand, written):
    """(numpy.) HEAD_RULE (1) and (2): the target's training row from the label's. lab: the label's row (c, cm, s, sm,
    k, km) with C3's training masks (keys x sounding); cand: the candidate's encode; written: (wc, ws, wk). Written
    heads take the candidate's value, every other head the label's; every mask is the label's. -> (row, counts) where
    counts holds, per head kind, the trained written heads silent in the candidate and the written heads sounding in the
    candidate but untrained by the label."""
    import numpy as np

    row, counts = [], {}
    for i, name in ((0, "cont"), (2, "sw"), (4, "mic")):
        w = written[i // 2] > 0
        row += [np.where(w, cand[i], lab[i]).astype(lab[i].dtype), lab[i + 1].copy()]
        counts[name] = {"trained_silent_in_target": int(((lab[i + 1] > 0) & w & ~(cand[i + 1] > 0)).sum()),
                        "sounding_untrained": int((~(lab[i + 1] > 0) & w & (cand[i + 1] > 0)).sum())}
    return tuple(row), counts


def head_counts(rows_w):
    """(numpy.) Per head, the training rows (showings) whose mask is on. rows_w: [(row, weight)]. -> (cont, sw, mic)."""
    import numpy as np

    out = []
    for i in (1, 3, 5):
        out.append(sum((np.asarray(r[i]) > 0).astype(np.int64) * w for r, w in rows_w) if rows_w else None)
    return tuple(out)


def rails(c, cm, eq_idx):
    """EQ bands sounding on a limit, of the bands sounding."""
    v = [c[j] for j in eq_idx if cm[j] > 0]
    return sum(x <= RAIL or x >= 1 - RAIL for x in v), len(v)


def centred(values, min_n=MIN_CELL):
    """values: [(cell, *xs)] -> [(index, xs less their cell's means)] for cells of at least min_n values."""
    by = {}
    for i, v in enumerate(values):
        by.setdefault(v[0], []).append(i)
    out = []
    for idx in by.values():
        if len(idx) < min_n:
            continue
        k = len(values[idx[0]]) - 1
        means = [sum(values[i][1 + j] for i in idx) / len(idx) for j in range(k)]
        out += [(i, tuple(values[i][1 + j] - means[j] for j in range(k))) for i in idx]
    return out


def cos_r(pairs):
    """r on already-centred pairs [(x, y)]: sum xy / sqrt(sum x^2 sum y^2) (the preview's)."""
    sxy = sum(x * y for x, y in pairs)
    sxx, syy = sum(x * x for x, _ in pairs), sum(y * y for _, y in pairs)
    return None if not sxx or not syy else sxy / math.sqrt(sxx * syy)


def readout(values, n_boot=BOOT_N, seed=BOOT_SEED):
    """The learnability readout. values: [(cell, cluster, answer, label, target)], cells (amp, class, head). Each of
    answer, label and target centred within its cell (cells of MIN_CELL values or more); r(answer, label), r(answer,
    target), their difference, and the difference's 90% cluster-bootstrap interval (clusters resampled with
    replacement; percentile). -> {values, clusters, r_label, r_target, diff, lo90, hi90, sd_*}."""
    import random

    cen = centred([(v[0], v[2], v[3], v[4]) for v in values])
    if not cen:
        return {"values": 0}
    by = {}
    for i, xs in cen:
        by.setdefault(values[i][1], []).append(xs)
    cl = sorted(by, key=str)

    def stat(groups):
        xs = [x for g in groups for x in by[g]]
        a = cos_r([(x[0], x[1]) for x in xs])
        b = cos_r([(x[0], x[2]) for x in xs])
        return a, b, (None if a is None or b is None else b - a)
    rl, rt, d = stat(cl)
    rng = random.Random(seed)
    boots = sorted(x for x in (stat(rng.choices(cl, k=len(cl)))[2] for _ in range(n_boot)) if x is not None)
    lo, hi = (boots[int(0.05 * len(boots))], boots[int(0.95 * len(boots)) - 1]) if boots else (None, None)
    sd = lambda j: math.sqrt(sum(x[j] ** 2 for _, x in cen) / len(cen))   # noqa: E731
    return {"values": len(cen), "clusters": len(cl), "r_label": rl, "r_target": rt, "diff": d, "lo90": lo,
            "hi90": hi, "boot": len(boots), "sd_answer": sd(0), "sd_label": sd(1), "sd_target": sd(2)}


# --- the runs and their centres (zero renders) -----------------------------------------------------------------------------

def run_split(name):
    """A run name -> (fold k or None, inner)."""
    if name == "all":
        return None, False
    return int(name[-1]), name.startswith("inner")


def run_records(st, name):
    """A run's training records, each as often as one epoch shows it (`preset_ladder.training_records`, with the inner
    runs' own split and mix seeds), and its validation records (an inner run's held fold, once each). -> (train,
    held)."""
    from learn import full_controls_c3r as R

    k, inner = run_split(name)
    tr, held, _ = R.split(st["entries"], k, inner, "all")

    def by(es):
        out = {}
        for e in es:
            out.setdefault(e["set"], []).append(e["unit"])
        return out
    recs = R.records_of(st, by(tr))
    train = []
    for src_name, v in recs.items():
        train += R.cycled_to(R.mixed(v, R.mix_seed("all", k, inner, src_name)))
    hrecs = R.records_of(st, by(held))
    return train, [r for v in hrecs.values() for r in v]


def sha_json(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def step5_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT


# --- stage 0 -------------------------------------------------------------------------------------------------------------

class Ctx:
    """Stage 0's shared state: C3r's state, S per amp and class, the hold, the written masks, the label rows."""

    def __init__(self):
        from learn import full_controls_c3 as C3
        from learn import full_controls_c3r as R
        from learn import full_space as F
        from learn import pipeline_fix as P
        from learn import preset_ladder as L

        self.st = R.state()
        self.src = self.st["sources"]
        self.outs = {**self.st["c2"]["outputs"], **self.st["c2r"]["outputs"]}
        self.ms, self.hold = P.A_menu_S(), R.answer_hold(self.st)
        self.keys_of = C3.keys_fn(self.src)
        self.cls_of = L.classes(self.st)
        self.ent = {e["unit"]: e for e in self.st["entries"]}
        self.D = F.by_name()
        self.eq_idx = [j for j, n in enumerate(F.CONT) if self.D[n].module.endswith("EQ") and "EQBand" in self.D[n].key]
        self._w = {}

    def enc(self, settings, amp):
        from learn import full_space as F
        from learn import local_objective as LO

        return F.encode(LO.tdict(settings), amp)[:6]

    def written(self, amp, cls):
        """The (cont, switch, mic) 0/1 masks of the heads the adopted answer writes (C3-cabS; forced keys out)."""
        import numpy as np

        from learn import full_space as F

        if (amp, cls) not in self._w:
            S = self.ms[amp][cls][1]
            keys, forced = self.hold(amp, S)
            w = set(keys) - set(forced)
            self._w[(amp, cls)] = tuple(np.array([(self.D[n].module, self.D[n].key) in w for n in names], np.float32)
                                        for names in (F.CONT, F.SW, F.CAT))
        return self._w[(amp, cls)]


def build_records(cx):
    """Every labelled record: its label's training row (C3's masks), its candidates, their encodes and ln judges; the
    source controls. -> (recs, kinds, problems)."""
    import numpy as np

    from learn import full_controls_c3 as C3
    from learn import full_space as F
    from learn import local_objective as LO

    recs, kinds, problems = {}, {}, []
    label_of = C3.label_fn(cx.src)
    for (u, a), s in sorted(cx.src.items()):
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
        o = cx.outs.get(s.get("key"))
        cls = cx.cls_of[u]
        lab = label_of({"unit": u, "amp": a})
        c, cm, sw, sm, k, km, _ = F.encode(LO.tdict(lab["settings"]), a)
        hc, hs, hk = C3.head_masks(cx.keys_of(u, a, cx.ms[a][cls][1]))
        lrow = (c, cm * hc, sw, sm * hs, k, km * hk)
        if s["kind"] != "c2" or o is None:
            recs[(u, a)] = {"set": s["set"], "cls": cls, "lab": lrow, "cands": None, "fold": cx.ent[u]["fold"]}
            continue
        if o.get("label") != s["label"]:
            problems.append(f"{u}|{a}: the training source is not the search's label")
        if len(o["step1"].get("trials") or []) != 200:
            problems.append(f"{u}|{a}: {len(o['step1'].get('trials') or [])} step 1 trials, not 200")
        se, he = o.get("search"), o.get("held")
        if {se, he} != {"A", "B"}:
            problems.append(f"{u}|{a}: halves {se}, {he}")
        if o.get("cls") != cls:
            problems.append(f"{u}|{a}: class {o.get('cls')} against the unit's {cls}")
        b = o["step1"].get("best") or {}
        x = dict(o["step1"]["start_settings"])
        x.update(o["step1"]["trials"][b["index"]]["x"])
        if x != b.get("settings") or o["step1"]["trials"][b["index"]]["judge"] != b.get("judge"):
            problems.append(f"{u}|{a}: step 1's stored best is not its trial {b.get('index')}")
        cands = candidates(o)
        E = [cx.enc(x_, a) for _, _, x_, _ in cands]
        encs = tuple(np.stack([e[i] for e in E]) for i in range(6))
        ok = [usable(j, se, he) for *_, j in cands]
        ln_s = [math.log(j[se]) if ok_ else math.inf for (*_, j), ok_ in zip(cands, ok)]
        ln_h = [math.log(j[he]) if ok_ else math.inf for (*_, j), ok_ in zip(cands, ok)]
        if not ok[0]:
            problems.append(f"{u}|{a}: the label's fresh judge is not finite on both halves")
        recs[(u, a)] = {"set": s["set"], "cls": cls, "lab": lrow, "cands": cands, "enc": encs, "ok": ok,
                        "ln_s": ln_s, "ln_h": ln_h, "cluster": o.get("cluster"), "fold": cx.ent[u]["fold"]}
    return recs, kinds, problems


def build_cens(cx, recs):
    """Each run's training and validation records and its Cen per amp and class (the ladder's `centre_of` over its
    training labels, each as often as an epoch shows it; written as `cmd_centres` writes it). -> (runs, cens)."""
    import numpy as np

    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    runs, cens = {}, {}
    for name in RUNS:
        train, held = run_records(cx.st, name)
        runs[name] = {"train": train, "held": held}
        for amp in P.AMPS3:
            for cls in ("clean", "crunch"):
                sel, S = cx.ms[amp][cls]
                s_enc = F.encode(dict(S), amp)
                s_mics = [int(v) if m else None for v, m in zip(s_enc[4], s_enc[5])]
                rows = [recs[(r["unit"], r["amp"])]["lab"] for r in train
                        if r["amp"] == amp and cx.cls_of[r["unit"]] == cls]
                cont, swp, mics = L.centre_of(rows, len(F.CONT), len(F.SW), len(F.CAT), s_mics)
                stg = F.answer_settings(amp, S, np.array(cont, np.float64), swp, mics)
                stg = (P.hold_outside_space(stg, S, amp, cx.hold) if cx.hold is not None
                       else P.hold_outside_space(stg, S, amp))
                sd = LO.sdict(stg)
                cens[(name, amp, cls)] = {"select": sel, "settings": sd, "enc": cx.enc(sd, amp), "showings": len(rows)}
    return runs, cens


def cen_control(cx, cens):
    """The fold models' Cen against the ladder's stored `cen` answers, the all-labels Cen against `centres.json`.
    -> (record, problem or None)."""
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    lad = json.loads((L.ladder_dir() / "answers" / "cen.json").read_text())
    mism, seen = 0, 0
    for d in lad["answers"].values():
        for ku, v in d.items():
            u, a = ku.rsplit("|", 1)
            seen += 1
            mism += v[P.ANY_HALF]["settings"] != cens[(f"fold{cx.ent[u]['fold']}", a, cx.cls_of[u])]["settings"]
    cj = json.loads((L.ladder_dir() / "centres.json").read_text())["centres"]["cen"]
    mism_all = sum(cj[a][c]["settings"] != cens[("all", a, c)]["settings"] for a in P.AMPS3 for c in ("clean", "crunch"))
    rec = {"parts": seen, "mismatches": mism, "all_labels_mismatches": mism_all}
    bad = mism or mism_all or not seen
    return rec, (f"Cen does not reproduce the ladder's: {mism} of {seen} parts, {mism_all} all-labels cells" if bad
                 else None)


def cmd_stage0(_args):
    """Stage 0 (plan section 4.6): zero renders. Writes step5/targets-{run}.json (nine) and step5/stage0.json."""
    import numpy as np

    from learn import full_controls_c3r as R
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    table_guard()
    P.require(PHASE_S5)
    P.require(PHASE_S0)
    t0 = time.time()
    cx = Ctx()
    st, D, eq_idx, written = cx.st, cx.D, cx.eq_idx, cx.written
    recs, kinds, problems = build_records(cx)
    controls = {"sources": {"kinds": kinds, "records": len(recs),
                            "with_trials": sum(r["cands"] is not None for r in recs.values())}}
    print(f"stage 0: {len(recs)} records encoded ({time.time() - t0:.0f} s)", flush=True)
    runs, cens = build_cens(cx, recs)
    controls["cen_reproduces_ladder"], why = cen_control(cx, cens)
    if why:
        problems.append(why)

    # the targets: every record under every run's Cen, at MARGIN and (all-labels) at each dose margin
    def target_of(key, name, margin=MARGIN):
        r = recs[key]
        if r["cands"] is None:
            return None
        cen = cens[(name, key[1], r["cls"])]["enc"]
        d = distances(r["enc"], cen, written(key[1], r["cls"]))
        return pick(r["ln_s"], r["ok"], list(d), margin), d

    picks = {}
    for name in RUNS:
        for key in recs:
            got = target_of(key, name)
            picks[(name, key)] = None if got is None else (got[0], float(got[1][got[0]]), float(got[1][0]))
    print(f"stage 0: nine target sets picked ({time.time() - t0:.0f} s)", flush=True)

    # HEAD_RULE's rows and the per-head counts, run by run
    row_counts, silent = {}, {"cont": [0, 0], "sw": [0, 0], "mic": [0, 0]}
    rows_equal = True
    tgt_rows = {}
    for key, r in recs.items():
        for name in RUNS:
            pk = picks[(name, key)]
            if pk is None or pk[0] == 0:
                tgt_rows[(name, key)] = (r["lab"], None)
                continue
            cand = tuple(r["enc"][i][pk[0]] for i in range(6))
            tgt_rows[(name, key)] = target_row(r["lab"], cand, written(key[1], r["cls"]))
    for name in RUNS:
        w = {}
        for rr in runs[name]["train"]:
            key = (rr["unit"], rr["amp"])
            w[key] = w.get(key, 0) + 1
        missing = [k for k in w if k not in recs]
        if missing:
            problems.append(f"{name}: {len(missing)} training records without a label row")
        lab_c = head_counts([(recs[k]["lab"], n) for k, n in w.items()])
        tg_c = head_counts([(tgt_rows[(name, k)][0], n) for k, n in w.items()])
        diff = {nm: int(np.sum(np.asarray(a_) != np.asarray(b_))) for nm, a_, b_ in zip(("cont", "sw", "mic"), lab_c, tg_c)}
        rows_equal &= not any(diff.values())
        for k, n in w.items():
            cnt = tgt_rows[(name, k)][1]
            if cnt:
                for hk_, v in cnt.items():
                    silent[hk_][0] += v["trained_silent_in_target"] * n
                    silent[hk_][1] += v["sounding_untrained"] * n
        row_counts[name] = {"records": len(w), "showings": sum(w.values()), "heads_differing": diff,
                            "rows_per_head": {nm: {n_: int(x) for n_, x in zip(names, arr)} for nm, names, arr in
                                              zip(("cont", "sw", "mic"), (F.CONT, F.SW, F.CAT), lab_c)}}
    controls["head_rule"] = {"rows_equal": rows_equal,
                             "written_head_rows_trained_but_silent_in_target": {k: v[0] for k, v in silent.items()},
                             "written_head_rows_sounding_in_target_untrained": {k: v[1] for k, v in silent.items()}}

    # per run: what the targets are, how far they moved, what to confirm
    def summary(name, keys):
        moved, kind_n, d_lab, d_tgt, rails_l, rails_t, disc = 0, {}, [], [], [], [], {}
        for key in keys:
            r, pk = recs[key], picks[(name, key)]
            if pk is None:
                kind_n["no trials"] = kind_n.get("no trials", 0) + 1
                continue
            kd = r["cands"][pk[0]][0]
            kind_n[kd] = kind_n.get(kd, 0) + 1
            moved += pk[0] != 0
            d_lab.append(pk[2])
            d_tgt.append(pk[1])
            rails_l.append(rails(r["enc"][0][0], r["enc"][1][0], eq_idx)[0])
            rails_t.append(rails(r["enc"][0][pk[0]], r["enc"][1][pk[0]], eq_idx)[0])
            ws_, wk_ = written(key[1], r["cls"])[1:]
            for i, names, wm in ((2, F.SW, ws_), (4, F.CAT, wk_)):
                for j, n_ in enumerate(names):
                    if wm[j] and r["lab"][i + 1][j] > 0 and r["enc"][i][0][j] != r["enc"][i][pk[0]][j]:
                        disc[n_] = disc.get(n_, 0) + 1
        med = lambda v: float(np.median(v)) if v else None   # noqa: E731
        return {"records": len(keys), "differ_from_label": moved, "kinds": kind_n,
                "median_sumsq_to_cen": {"label": med(d_lab), "target": med(d_tgt)},
                "median_rms_to_cen_ratio": med([math.sqrt(t / l_) for t, l_ in zip(d_tgt, d_lab) if l_ > 0]),
                "eq_bands_on_limit_per_record": {"label": float(np.mean(rails_l)) if rails_l else None,
                                                 "target": float(np.mean(rails_t)) if rails_t else None},
                "discrete_heads_moved": dict(sorted(disc.items()))}

    per_run = {}
    distinct = set()
    for name in RUNS:
        keys = sorted({(rr["unit"], rr["amp"]) for rr in runs[name]["train"]})
        per_run[name] = {"train": summary(name, keys)}
        if name.startswith("inner"):
            hk = sorted({(rr["unit"], rr["amp"]) for rr in runs[name]["held"]})
            per_run[name]["validation"] = summary(name, hk)
        for key in keys:
            pk = picks[(name, key)]
            if pk is not None and pk[0] != 0:
                distinct.add((key, pk[0]))
    controls["confirm"] = {"distinct_non_label_training_targets": len(distinct),
                           "records_with_one": len({k for k, _ in distinct}),
                           "renders_if_primed": 2 * len(distinct)}

    # the held-half cost (stored judges) of each run's training targets against the labels, by set and pooled
    def cost_rows(name, keys):
        by = {}
        for key in keys:
            r, pk = recs[key], picks[(name, key)]
            if pk is None:
                continue
            by.setdefault(r["set"], []).append((r["cluster"], f"{key[0]}|{key[1]}", r["ln_h"][pk[0]] - r["ln_h"][0]))
        rows = {s: P.clustered(v) for s, v in by.items()}
        pool = R.pooled({s: rows[s] for s in DECIDING}) if all(rows.get(s) for s in DECIDING) else None
        return {"deciding_pool": pool, "sets": {s: {k: v.get(k) for k in ("mean", "lo90", "hi90", "clusters", "parts")}
                                                for s, v in rows.items()}}
    costs = {name: cost_rows(name, sorted({(rr["unit"], rr["amp"]) for rr in runs[name]["train"]})) for name in RUNS}

    # the dose table: the all-labels set at each margin (descriptive)
    dose = {}
    all_keys = sorted({(rr["unit"], rr["amp"]) for rr in runs["all"]["train"]})
    for m in DOSE_MARGINS:
        best_other, moved, dl, dt, rl_, rt_, cost = 0, 0, [], [], [], [], {}
        for key in all_keys:
            r = recs[key]
            if r["cands"] is None:
                continue
            i, d = target_of(key, "all", m)
            ib = min((j for j in range(len(r["ok"])) if r["ok"][j]), key=lambda j: (r["ln_s"][j], j))
            best_other += i != ib
            moved += i != 0
            dl.append(math.sqrt(d[0]))
            dt.append(math.sqrt(d[i]))
            rl_.append(rails(r["enc"][0][0], r["enc"][1][0], eq_idx)[0])
            rt_.append(rails(r["enc"][0][i], r["enc"][1][i], eq_idx)[0])
            cost.setdefault(r["set"], []).append((r["cluster"], f"{key[0]}|{key[1]}", r["ln_h"][i] - r["ln_h"][0]))
        rows = {s: P.clustered(v) for s, v in cost.items()}
        pool = R.pooled({s: rows[s] for s in DECIDING}) if all(rows.get(s) for s in DECIDING) else None
        dose[f"{m:.2f}"] = {"records": len(dl), "not_the_best_scoring": best_other, "differ_from_label": moved,
                            "median_dist_to_cen": {"label": float(np.median(dl)), "target": float(np.median(dt))},
                            "eq_bands_on_limit_per_record": {"label": float(np.mean(rl_)), "target": float(np.mean(rt_))},
                            "held_cost_deciding_pool": pool}

    # the knobs' within-cell spread (all-labels set): targets against labels
    spread = {}
    vals = []
    for key in all_keys:
        r, pk = recs[key], picks[("all", key)]
        if pk is None:
            continue
        wc = written(key[1], r["cls"])[0]
        for j, n_ in enumerate(F.CONT):
            g = L.knob_group(D[n_].module, D[n_].key)
            if g and wc[j] and r["lab"][1][j] > 0:
                vals.append(((key[1], r["cls"], n_), g, float(r["lab"][0][j]), float(tgt_rows[("all", key)][0][0][j])))
    for g in L.GROUP_NAMES + ("all",):
        xs = [v for v in vals if g == "all" or v[1] == g]
        cen_ = centred([(v[0], v[2], v[3]) for v in xs], 2)
        if cen_:
            spread[g] = {"values": len(cen_), "sd_label": math.sqrt(sum(x[0] ** 2 for _, x in cen_) / len(cen_)),
                         "sd_target": math.sqrt(sum(x[1] ** 2 for _, x in cen_) / len(cen_))}

    # the learnability readout: R-all's out-of-fold answers against each read record's label and its fold's target
    ans = json.loads((P.out_dir() / R.OUT / "answers" / "all.json").read_text())
    if ans.get("c3r_sha256") != st["sha256"]:
        problems.append("c3r/answers/all.json was answered on another C3r state")
    controls["answers"] = {"file_sha256": L.file_sha(P.out_dir() / R.OUT / "answers" / "all.json"),
                           "c3r_sha256_matches": ans.get("c3r_sha256") == st["sha256"]}
    rvals, n_rec = [], 0
    for s_, d in ans["answers"].items():
        for ku, halves in d.items():
            u, a = ku.rsplit("|", 1)
            key = (u, a)
            if key not in recs or recs[key]["cands"] is None:
                continue
            r = recs[key]
            name = f"fold{r['fold']}"
            pk = picks[(name, key)]
            trow = tgt_rows[(name, key)][0]
            wc = written(a, r["cls"])[0]
            n_rec += 1
            for h, x in halves.items():
                c_, cm_, *_ = F.encode(LO.tdict(x["settings"]), a)
                for j, n_ in enumerate(F.CONT):
                    g = L.knob_group(D[n_].module, D[n_].key)
                    if not g or not wc[j] or cm_[j] <= 0 or r["lab"][1][j] <= 0:
                        continue
                    if pk is not None and pk[0] != 0 and r["enc"][1][pk[0]][j] <= 0:
                        continue                         # the head must sound in the target too
                    rvals.append(((a, r["cls"], n_), (r["set"], r["cluster"]), g, float(c_[j]), float(r["lab"][0][j]),
                                  float(trow[0][j])))
    learn = {"records": n_rec}
    for g in L.GROUP_NAMES + ("all",):
        xs = [(v[0], v[1], v[3], v[4], v[5]) for v in rvals if g == "all" or v[2] == g]
        learn[g] = readout(xs)
    print(f"stage 0: readout done ({time.time() - t0:.0f} s)", flush=True)

    controls["problems"] = problems
    cell = s0_cell(not problems, rows_equal, (costs["all"] or {}).get("deciding_pool"), learn["all"])
    out_d = step5_dir()
    shas = {}
    for name in RUNS:
        body = {"plan": PLAN, "ledger": f"pipeline-fix {PHASE_S0}", "run": name, "margin": MARGIN,
                "c3r_sha256": st["sha256"], "cen": {f"{a}|{c}": {"select": cens[(name, a, c)]["select"],
                                                                 "settings": cens[(name, a, c)]["settings"],
                                                                 "showings": cens[(name, a, c)]["showings"]}
                                                    for a in P.AMPS3 for c in ("clean", "crunch")},
                "targets": {}}
        keys = sorted({(rr["unit"], rr["amp"]) for rr in runs[name]["train"]} |
                      {(rr["unit"], rr["amp"]) for rr in runs[name]["held"]})
        for key in keys:
            r, pk = recs[key], picks[(name, key)]
            if pk is None:
                body["targets"][f"{key[0]}|{key[1]}"] = {"kind": "label (no stored trials)"}
                continue
            kd, ix, stg, j = r["cands"][pk[0]]
            body["targets"][f"{key[0]}|{key[1]}"] = {"kind": kd, "index": ix, "settings": stg, "judge": j,
                                                     "sumsq_to_cen": pk[1], "label_sumsq_to_cen": pk[2]}
        body["sha256"] = sha_json(body["targets"])
        shas[name] = body["sha256"]
        P.save(out_d / f"targets-{name}.json", body)
    rep = {"plan": PLAN, "ledger": f"pipeline-fix {PHASE_S0}", "cell": cell,
           "cell_next": next(t for c, _, t in S0_TABLE if c == cell), "margin": MARGIN, "c3r_sha256": st["sha256"],
           "target_sets_sha256": shas, "controls": controls, "rows": row_counts, "per_run": per_run,
           "held_half_cost": costs, "dose": dose, "spread": spread, "learnability": learn,
           "replay_of_stages_a_b": "not built (lean path): stage A's and B's other trials stay out (plan 4.3)",
           "seconds": round(time.time() - t0, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(out_d / "stage0.json", rep)
    la = learn["all"]
    print(json.dumps({"cell": cell, "problems": problems[:5], "rows_equal": rows_equal,
                      "overfit_pool": (costs["all"] or {}).get("deciding_pool"),
                      "readout_all": {k: la.get(k) for k in ("values", "clusters", "r_label", "r_target", "diff",
                                                              "lo90", "hi90")},
                      "confirm": controls["confirm"]}, indent=1, default=str))
    print(f"STAGE 0 DONE: {cell} ({time.time() - t0:.0f} s) -> {out_d / 'stage0.json'}")


# --- Step 3: the R1 versions check ---------------------------------------------------------------------------------------

def rms(a, b):
    """RMS difference over the heads both hold. a, b: {head: value}."""
    ks = sorted(set(a) & set(b))
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in ks) / len(ks)) if ks else None


def version_spread(ans, group=None):
    """(Pure.) ans: {(song, cls, version, amp): {head: value}}; group: a head predicate or None. The RMS distances
    between a song's versions (same amp; every pair) and between songs of one class (same version and amp; every
    pair). -> {"within_song": [d], "between_songs": [d]}."""
    sel = (lambda a: a) if group is None else (lambda a: {k: v for k, v in a.items() if group(k)})   # noqa: E731
    keys = sorted(ans)
    w, b = [], []
    for i, p in enumerate(keys):
        for q in keys[i + 1:]:
            if p[3] != q[3]:
                continue
            if p[0] == q[0] and p[2] != q[2]:
                d = rms(sel(ans[p]), sel(ans[q]))
                if d is not None:
                    w.append(d)
            elif p[0] != q[0] and p[1] == q[1] and p[2] == q[2]:
                d = rms(sel(ans[p]), sel(ans[q]))
                if d is not None:
                    b.append(d)
    return {"within_song": w, "between_songs": b}


def cmd_versions(_args):
    """Step 3's R1 versions check (plan section 2.2): the adopted pair's answer on each amp from each stored version of
    each R1 song's window (`r1/versions/`), at the product's level (the window's mix to MIX_LEVEL, the version by the
    same gain, its stored loudness gain undone), read as the product path's `answers` stage reads a stem. Descriptive:
    the written knob heads' RMS distance between a song's versions against between songs of a class. A control: the
    same code on the product's stored window (`r1/<song>/model/window.npz`) reproduces `model/answers.json`.
    -> step5/r1-versions.json."""
    import numpy as np
    import soundfile as sf

    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import preset_ladder as L
    from learn import product_path as PP

    table_guard()
    P.require(PHASE_VERSIONS)
    t0 = time.time()
    r1 = P.out_dir() / "r1"
    vroot = r1 / "versions"
    nets, hold, _ = PP._adopted()
    ms = P.A_menu_S()
    D = F.by_name()
    vals, controls, n_ans, info = {}, {}, 0, {}

    def answer(stem, mix, g, cls):
        s8, _, ls, _ = DS.step4_half(stem, mix, PP.HALF, g)
        got = {}
        for a in PP.AMPS:
            sel, S = ms[a][cls]
            x, c = P.vreal_model_input(s8, ls, PP.HALF, a, cls)
            r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
            stg = F.answer_settings(a, S, r["a2"], r["sw_p"], r["mics"])
            stg = P.hold_outside_space(stg, S, a) if hold is None else P.hold_outside_space(stg, S, a, hold)
            got[a] = (LO.sdict(stg), S)
        return got

    for slug in sorted(p.name for p in vroot.iterdir() if p.is_dir()):
        meta = json.loads((vroot / slug / "meta.json").read_text())
        w = np.load(r1 / slug / "model" / "window.npz")
        mix = np.asarray(w["mix"], np.float64)
        stored = json.loads((r1 / slug / "model" / "answers.json").read_text())
        cls = stored["cls"]
        g = DE.inference_gain_db(mix, PP.MIX_LEVEL)
        own = answer(np.asarray(w["stem"], np.float64), mix, g, cls)
        controls[slug] = {"reproduces_model_answers": all(own[a][0] == stored["answers"][a]["settings"]
                                                          for a in PP.AMPS),
                          "gain_db_matches": abs(g - stored["gain_db"]) < 1e-9}
        info[slug] = {"cls": cls, "versions": []}
        for v in sorted(meta["versions"]):
            y, sr = sf.read(vroot / slug / f"{v}.wav", dtype="float64", always_2d=True)
            y = y.mean(1)
            i0 = int(round(meta["window_offset_s"] * sr))
            n = int(PP.WINDOW_S * sr)
            seg = y[i0:i0 + n] / 10 ** (meta["versions"][v]["gain_db"] / 20)
            if len(seg) != len(mix):
                raise SystemExit(f"{slug} {v}: a window of {len(seg)} samples, not the mix's {len(mix)}")
            got = answer(seg, mix, g, cls)
            info[slug]["versions"].append(v)
            for a, (stg, S) in got.items():
                written = set(hold(a, S)[0]) - set(hold(a, S)[1])
                c_, cm_, *_ = F.encode(LO.tdict(stg), a)
                vals[(slug, cls, v, a)] = {n_: float(c_[j]) for j, n_ in enumerate(F.CONT)
                                           if cm_[j] > 0 and (D[n_].module, D[n_].key) in written
                                           and L.knob_group(D[n_].module, D[n_].key)}
                n_ans += 1
        print(f"versions: {slug} ({len(info[slug]['versions'])} versions, {time.time() - t0:.0f} s)", flush=True)
    out = {"plan": PLAN, "ledger": f"pipeline-fix {PHASE_VERSIONS}", "answers": n_ans, "songs": info,
           "controls": controls, "groups": {}}
    med = lambda v: float(np.median(v)) if v else None   # noqa: E731
    for gname in L.GROUP_NAMES + ("all",):
        pred = None if gname == "all" else (lambda k, gg=gname: L.group_of(k) == gg)
        for amp in PP.AMPS + ("pooled",):
            sub = {k: v for k, v in vals.items() if amp == "pooled" or k[3] == amp}
            sp = version_spread(sub, pred)
            out["groups"].setdefault(gname, {})[amp] = {
                "within_song_pairs": len(sp["within_song"]), "within_song_median": med(sp["within_song"]),
                "between_song_pairs": len(sp["between_songs"]), "between_song_median": med(sp["between_songs"])}
    allp = out["groups"]["all"]["pooled"]
    out["reading"] = (None if allp["within_song_median"] is None or allp["between_song_median"] is None else
                      "answers move more between versions than between songs" if allp["within_song_median"] >
                      allp["between_song_median"] else "answers move less between versions than between songs")
    out["answers_by_key"] = {"|".join(k): v for k, v in sorted(vals.items())}
    out["seconds"] = round(time.time() - t0, 1)
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(step5_dir() / "r1-versions.json", out)
    print(json.dumps({k: out[k] for k in ("answers", "controls", "reading")}, indent=1))
    print(json.dumps(out["groups"]["all"], indent=1))
    print(f"VERSIONS DONE ({out['seconds']} s) -> {step5_dir() / 'r1-versions.json'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stage0").set_defaults(fn=cmd_stage0)
    sub.add_parser("versions").set_defaults(fn=cmd_versions)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
