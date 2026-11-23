"""The from-scratch search, Direction 1's test after R-alone (`docs/scratch-search-plan.md`; ledger `preset-ladder`
`phase_fs`, `phase_fs_draw`, `phase_fs_answers_<row>`, `phase_fs_outcome`).

On 47 of the note-matched replay's held-out ladder parts, C2's label search runs from Cen, driven only by a degraded
input on the search half: row `fs-stem` (b) the true DI against X-LANCE's stem of the mix with no other guitar
(`xlnoG@-3`); then, by the coded cells only, `fs-both` (c) the blurred DI against that stem, `fs-blur` (a) the blurred
DI against the clean record, or `fs-control` the true DI against the clean record. The search process is handed each
reference with everything outside its search half set to zeros, and its guards read the search half only. Each answer
(with step 1's incumbents at 50, 100 and 200 evaluations and the answer shrunk halfway to Cen) is hashed into the
ledger before `score` renders it through the true DI and judges it on the held half against the clean record. Two
numbers a row: G (the answer less Cen) and I (the answer less the borrowed answer: the mean, on this part, of 3 other
parts' answers from the same row). `OUTCOME_TABLE` holds every reachable cell once.

    $MAIN -m learn.scratch_search draw                           # the subset and its partners (zero renders)
    # draw.json's sha256 into the ledger (phase_fs_draw) on main before anything below
    $MAIN -m learn.scratch_search search --row fs-stem --shard 0/3 [--first 2]   # renders; at most 3 shards
    $MAIN -m learn.scratch_search answers --row fs-stem          # zero renders; its sha256 -> phase_fs_answers_stem
    $MAIN -m learn.scratch_search score --row fs-stem --shard 0/3   # the only step that reads a held half
    $MAIN -m learn.scratch_search read --row fs-stem             # zero renders: the reading, then the cell or next row

$MAIN is the main checkout's .venv python (in a worktree add `--data-dir ~/ndsp-presets` through the environment the
replay used). The pure parts (the subset, the partners, the blank, the guards, the shrink and the centre, the
readings, `OUTCOME_TABLE`, the refusal stop, the non-finite rule) are tested in tests/test_scratch_search.py on the
light CI runner (no numpy); the loop's equivalence with C2 and the blank's independence run where numpy and the stored
data exist.

The per-part bodies of `search`, `answers`, `score` and `read` are shared functions (`search_row_part`, `answer_parts`,
`score_row_part`, `read_row_parts`, `report_body`), so one code path scores every row: the note rebuild's `fs-notes`
row (`learn/scratch_notes.py`, plan section 10) runs through them. This module's own commands, `ROWS` and
`OUTCOME_TABLE` are unchanged and still refuse any row but their four.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import time

LEDGER_ID = "preset-ladder"
PLAN = "docs/scratch-search-plan.md"
PHASE = "phase_fs"                       # the declaration: before the draw
PHASE_DRAW = "phase_fs_draw"             # draw.json's sha256: before any render
PHASE_OUTCOME = "phase_fs_outcome"       # the results, after the audit
OUT = "fs"                               # PF/fs/
SEED = 20261301                          # the subset
PARTNER_SEED = 20261302                  # each part's partner order
SETS = ("bks", "goat", "panel")
AMPS = ("ac20", "pr12", "sw50r")
BKS_PER_DI = 2                           # BKS: parts a DI file
GOAT_PER_CELL = 3                        # GOAT: parts a fold and class
PANEL_LEFT_OUT = ("Drowning",)           # the replay's bleed check (never recorded); Silent Waves was never drawn
COUNTS = {"bks": 16, "goat": 24, "panel": 7}
PARTNERS = 3                             # the borrowed answer: the mean of this many partners' answers
REFUSAL_CONF = 0.90                      # the refused share's Clopper-Pearson interval (S1: a report, never a stop)
START_TOL = 0.005                        # the start check: |ln(first evaluation / the replay's position 0)|
SCORE_TOL = 0.005                        # the scoring control: |ln(Cen's held-half render / its stored value)|
BUDGET = 200                             # step 1 (C2's)
CHECKPOINTS = (50, 100, 200)             # step 1's incumbents scored beside the answer
SHRINK = 0.5                             # the answer's continuous controls halfway back to Cen's
SMALL, BIG = 0.05, 0.10                  # the user's rule; "passes" (as the replay's)
ROWS = {                                 # row: (dry guitar, reference on the search half); its letter in the plan
    "fs-stem": ("true", "xlnoG"),        # (b)
    "fs-both": ("avg+mild", "xlnoG"),    # (c)
    "fs-blur": ("avg+mild", "clean"),    # (a)
    "fs-control": ("true", "clean")}     # the conditional Control
LETTER = {"fs-stem": "b", "fs-both": "c", "fs-blur": "a", "fs-control": "Control"}
REF_NAME = {"xlnoG": "xlnoG@-3", "clean": "the clean record"}
MAX_ROWS = 3                             # N1: the longest path
READINGS = ("passes", "constant", "fails", "undecided")
B_READINGS = READINGS + ("undecided-b2",)   # row (b)'s, with B2's lever


def phase_answers(row):
    """The ledger key of a row's answers' sha256 (`phase_fs_answers_stem`, ..._both, ..._blur, ..._control)."""
    if row not in ROWS:
        raise SystemExit(f"unknown row {row!r}")
    return "phase_fs_answers_" + row.split("-", 1)[1]


# --- the subset and the partners (pure) ------------------------------------------------------------------------------------

def subset(parts, seed=SEED, amps=AMPS):
    """(Pure.) The 47 parts from the replay's drawn parts. parts: [{pkey, set, amp, cluster, fold, cls, title}].
    Panel: every part but PANEL_LEFT_OUT's titles. BKS: per DI file (sorted) BKS_PER_DI parts; the wanted amps rotate
    over the DI files from a seeded offset (file j wants amps[(off + 2j) % 3] and amps[(off + 2j + 1) % 3]); for each
    wanted amp the first of the file's parts in seeded order on it, else the first left. GOAT: per fold and class
    GOAT_PER_CELL parts, in seeded order the first on an amp not yet taken in the cell (then any), at most one a GOAT
    item. -> sorted pkeys."""
    rng = random.Random(seed)
    out = [p["pkey"] for p in parts if p["set"] == "panel" and p.get("title") not in PANEL_LEFT_OUT]
    bks = {}
    for p in parts:
        if p["set"] == "bks":
            bks.setdefault(p["cluster"], []).append(p)
    off = rng.randrange(len(amps))
    for j, di in enumerate(sorted(bks)):
        ps = sorted(bks[di], key=lambda p: p["pkey"])
        rng.shuffle(ps)
        want = [amps[(off + BKS_PER_DI * j + i) % len(amps)] for i in range(BKS_PER_DI)]
        got = []
        for a in want:
            q = next((p for p in ps if p["amp"] == a and p not in got), None) or \
                next((p for p in ps if p not in got), None)
            if q is not None:
                got.append(q)
        out += [p["pkey"] for p in got]
    used = set()
    for f in sorted({p["fold"] for p in parts if p["set"] == "goat"}):
        for cls in ("clean", "crunch"):
            ps = sorted((p for p in parts if p["set"] == "goat" and p["fold"] == f and p["cls"] == cls),
                        key=lambda p: p["pkey"])
            rng.shuffle(ps)
            got = []
            for pass_ in ("new amp", "any"):
                for p in ps:
                    if len(got) >= GOAT_PER_CELL:
                        break
                    if p in got or p["cluster"] in used:
                        continue
                    if pass_ == "new amp" and p["amp"] in {q["amp"] for q in got}:
                        continue
                    got.append(p)
                    used.add(p["cluster"])
            out += [p["pkey"] for p in got]
    return sorted(out)


def subset_shortfall(keys, parts):
    """(Pure.) Why the subset is not the declared 47, or []: COUNTS per set, BKS on 8 DI files, the panel on 3."""
    by = {p["pkey"]: p for p in parts}
    out = []
    for s, n in COUNTS.items():
        got = sum(by[k]["set"] == s for k in keys)
        if got != n:
            out.append(f"{s}: {got} parts, not {n}")
    for s, n in (("bks", 8), ("panel", 3)):
        got = len({by[k]["cluster"] for k in keys if by[k]["set"] == s})
        if got != n:
            out.append(f"{s}: {got} DI files, not {n}")
    return out


def eligible(p, q):
    """(Pure.) q may lend its answer to p (N2): another part, the same amp and class, another cluster, no shared
    identity (C3r's ids: the DI file and a capture's creator) and another rig."""
    return (q["pkey"] != p["pkey"] and q["amp"] == p["amp"] and q["cls"] == p["cls"] and q["cluster"] != p["cluster"]
            and not (set(map(tuple, q["ids"])) & set(map(tuple, p["ids"]))) and q["rig"] != p["rig"])


def partner_pool(p, parts, seed=PARTNER_SEED, k=PARTNERS):
    """(Pure.) p's partners in order (N2): the eligible parts of p's own set, seeded, then the eligible parts of the
    other sets, seeded. The borrowed answer takes the first `k` that answered, so it comes from p's own set when at
    least `k` there answered and reaches across sets otherwise (reported); the row's centre takes all that answered.
    scope: "same set" when p's own set holds at least `k` eligible, else "across sets". -> (ordered pkeys, scope)."""
    same = sorted(q["pkey"] for q in parts if q["set"] == p["set"] and eligible(p, q))
    other = sorted(q["pkey"] for q in parts if q["set"] != p["set"] and eligible(p, q))
    random.Random(f"{seed}|{p['pkey']}|same").shuffle(same)
    random.Random(f"{seed}|{p['pkey']}|other").shuffle(other)
    return same + other, "same set" if len(same) >= k else "across sets"


def with_partners(parts, k=PARTNERS):
    """(Pure.) Every part's partners; a part with fewer than `k` eligible is refused at the draw (N2) and dropped, and
    the pools redrawn until none falls short. -> (parts with "partners" and "partner_scope", refused [(pkey, n)])."""
    keep, refused = list(parts), []
    while True:
        pools = {p["pkey"]: partner_pool(p, keep, k=k) for p in keep}
        short = [(q, len(v[0])) for q, v in pools.items() if len(v[0]) < k]
        if not short:
            break
        refused += short
        keep = [p for p in keep if p["pkey"] not in {q for q, _ in short}]
    return [dict(p, partners=pools[p["pkey"]][0], partner_scope=pools[p["pkey"]][1]) for p in keep], refused


def borrowed(p, answered, k=PARTNERS):
    """(Pure.) The first `k` of p's partners (in `partner_pool`'s order) whose search in this row gave an answer
    (answered: a set of pkeys), or None when fewer than `k` did (the part then refuses, counted toward the stop)."""
    got = [q for q in p["partners"] if q in answered][:k]
    return got if len(got) == k else None


# --- the blank and the guards (pure) ---------------------------------------------------------------------------------------

def search_window(half, halves, sr):
    """(Pure.) The samples `aligned_distance` can read on the search half: [int(a * sr), int(b * sr)). Its slice of the
    reference is recording[max(int(start_s * sr), lag if lag > 0):min(len, int(end_s * sr), ...)], inside this."""
    a, b = halves[half]
    return int(a * sr), int(b * sr)


def blank_plan(n, half, halves, sr):
    """(Pure.) The reference's samples to set to zero, as [(lo, hi)]: everything outside the search half's window, the
    held half among them. Zeros, not NaN: `aligned_distance` refuses a non-finite sample anywhere in the array, while
    a zero held half reads "no measurable loudness" (inf) and leaves the search half's read unchanged."""
    lo, hi = search_window(half, halves, sr)
    return [(0, min(lo, n)), (min(hi, n), n)]


def finite_pos(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v > 0


def usable(value, peak, bound, tol=0.05):
    """(Pure.) Why an evaluation can't stand as an answer, or None. It reads the search half only (B3): the value must
    be finite and positive; with a `bound` (`full_controls_c2.peak_bound`), its render's peak must be known and at least
    the bound less `tol` dB (C2's PEAK_TOL). The held half is never read: it is not in the search process."""
    if not finite_pos(value):
        return "non-finite on the search half"
    if bound is None:
        return None
    try:
        pk = float(peak)
    except (TypeError, ValueError):
        pk = math.nan
    if not math.isfinite(pk) or pk < bound - tol:
        return f"peak {peak} dBFS below the bound {bound:.2f} dBFS"
    return None


def best_index(evals, bound, n=None):
    """(Pure.) The lowest search-half value among the first n evaluations that pass `usable`; earliest on ties; None
    when none passes. evals: [{"value", "peak_dbfs"}]."""
    best = None
    for i, e in enumerate(evals[:n]):
        if usable(e["value"], e.get("peak_dbfs"), bound):
            continue
        if best is None or e["value"] < evals[best]["value"]:
            best = i
    return best


def start_check(value, stored, tol=START_TOL):
    """(Pure.) The search's first evaluation (Cen through the row's inputs) against the replay's stored position-0
    distance for the same dry guitar and reference: both finite and within `tol` in ln."""
    return finite_pos(value) and finite_pos(stored) and abs(math.log(value / stored)) <= tol


# --- the shrink and the centre (pure) --------------------------------------------------------------------------------------

def dim_of(spec):
    from learn.knob_ceiling import Dim

    return Dim(spec["module"], spec["key"], spec["kind"], spec.get("lo", 0.0), spec.get("hi", 1.0),
               values=tuple(spec.get("values") or ()))


def dim_spec(d):
    return {"module": d.module, "key": d.key, "kind": d.kind, "lo": d.lo, "hi": d.hi, "values": list(d.values)}


def _unit(d, v):
    return d.to_unit(v if v is not None else d.lo)


def shrunk(answer, cen, specs, lam=SHRINK):
    """(Pure.) The answer with every searched continuous control moved `lam` of the way back to Cen's value in the
    control's unit space (October's device, `arm_a_levers.shrink`'s rule); switches, mic types and every other key as
    the answer's. answer, cen: {"module/key": value}; specs: the answer's searched dims (`dim_spec`)."""
    from learn import knob_ceiling as K

    out = dict(answer)
    for s in specs:
        d = dim_of(s)
        if d.kind not in ("cont", "log"):
            continue
        a, c = _unit(d, answer.get(d.name)), _unit(d, cen.get(d.name))
        u = a + lam * (c - a)
        out[d.name] = answer[d.name] if math.isclose(u, a, abs_tol=1e-12) and d.name in answer else K.fmt(d.from_unit(u))
    return out


def centre(answers, cen):
    """(Pure.) The row's own centre for a part (a side reading): from its pool's answers [(settings, specs)], every
    searched continuous control at the mean of their unit values, every searched switch and mic type at its most
    common value (a tie to Cen's value when it is among the tied, else the lowest), every other key Cen's (the part's
    own). -> {"module/key": value}."""
    from learn import knob_ceiling as K

    out = dict(cen)
    dims = {}
    for _, specs in answers:
        for s in specs:
            dims.setdefault(s["module"] + "/" + s["key"], dim_of(s))
    for name, d in sorted(dims.items()):
        vals = [a.get(name, cen.get(name)) for a, _ in answers]
        if d.kind in ("cont", "log"):
            out[name] = K.fmt(d.from_unit(sum(_unit(d, v) for v in vals) / len(vals)))
        else:
            n = {}
            for v in vals:
                n[v] = n.get(v, 0) + 1
            top = max(n.values())
            tied = sorted(str(v) for v, c in n.items() if c == top)
            out[name] = cen.get(name) if str(cen.get(name)) in tied else tied[0]
    return out


# --- the score's numbers (pure) --------------------------------------------------------------------------------------------

def nonfinite_rule(held):
    """(Pure.) B3, declared: a setting whose held-half score is non-finite takes the part's worst finite held-half score
    among the settings scored on that part in the row, and never better than Cen's. held: {name: value or None} with
    "cen" finite. -> ({name: value}, [names replaced])."""
    fin = [v for v in held.values() if finite_pos(v)]
    worst = max(max(fin), held["cen"])
    out, rep = {}, []
    for k, v in held.items():
        if finite_pos(v):
            out[k] = float(v)
        else:
            out[k] = worst
            rep.append(k)
    return out, sorted(rep)


def part_numbers(held, partners):
    """(Pure.) One part's numbers for a row. held: the scored held-half values {"cen", "answer", "cp50", "cp100",
    "cp200", "shrunk", "centre", <partner pkey>...} after `nonfinite_rule`; partners: the borrowed answer's pkeys. G =
    ln(answer / Cen); the borrowed answer = the mean of the partners' ln(held / Cen); I = G - that; beside: the
    checkpoints', the shrunk answer's and the centre's G and I, and the answer less the centre."""
    c = held["cen"]

    def g(k):
        return math.log(held[k] / c) if k in held else None
    blind = sum(g(q) for q in partners) / len(partners)
    out = {"G": g("answer"), "blind": blind, "I": g("answer") - blind}
    for k in ("cp50", "cp100", "cp200", "shrunk", "centre"):
        v = g(k)
        out[f"G_{k}"] = v
        out[f"I_{k}"] = None if v is None else v - blind
    out["answer_less_centre"] = None if g("centre") is None else g("answer") - g("centre")
    return out


DRIVE_KEYS = ("drive1/drive1Active", "drive2/drive2Active", "compressor/compressorActive")


def moves(answer, cen):
    """(Pure.) What an answer moved that the replay's full-mix row was drawn to (a side reading, compared with the
    Control's answers when it runs): input gain against Cen's (dB) and each pedal's switch, against Cen's."""
    def on(x, k):
        return str(x.get(k, "false")).lower() in ("true", "1")
    try:
        gain = float(answer["parameters/inputGain"]) - float(cen["parameters/inputGain"])
    except (KeyError, TypeError, ValueError):
        gain = None
    return {"input_gain_db": gain, **{k.split("/")[0]: {"answer": on(answer, k), "cen": on(cen, k)} for k in DRIVE_KEYS}}


# --- the readings and the outcome table (pure) -----------------------------------------------------------------------------

def number_reading(row, small=SMALL, big=BIG):
    """(Pure.) "passes" (the 90% interval wholly below zero, the mean at -big or beyond), "fails" (the interval's lower
    end at -small or above), "undecided"; None without an interval. As the replay's."""
    if not row or row.get("lo90") is None or row.get("hi90") is None or row.get("mean") is None:
        return None
    if row["hi90"] < 0 and row["mean"] <= -big:
        return "passes"
    if row["lo90"] >= -small:
        return "fails"
    return "undecided"


def row_reading(g, i):
    """(Pure.) A row from its two numbers: "passes" when G and I both pass; "constant" when G passes and I does not
    (B1: a better constant, the gain not shown to be this recording's); "fails" when either fails (and not constant);
    else "undecided" (not failed). None without an interval."""
    rg, ri = number_reading(g), number_reading(i)
    if rg is None or ri is None:
        return None
    if rg == ri == "passes":
        r = "passes"
    elif rg == "passes":
        r = "constant"
    elif "fails" in (rg, ri):
        r = "fails"
    else:
        r = "undecided"
    return {"reading": r, "G": rg, "I": ri, "G_rules_out_gains_beyond": g.get("lo90"),
            "I_rules_out_gains_beyond": i.get("lo90"),
            "G_not_readable": g["lo90"] >= -SMALL and g["hi90"] <= SMALL,
            "I_not_readable": i["lo90"] >= -SMALL and i["hi90"] <= SMALL}


def b2_lever(pool, bks_goat, panel_g_mean, panel_i_mean):
    """(Pure.) B2, the user's declared next step: row (b) undecided on the deciding pool, passing on BKS+GOAT alone
    (G and I each decided better with the mean at -0.10 or beyond), and the panel's means of G and of I each <= 0."""
    return (pool == "undecided" and bks_goat == "passes" and panel_g_mean is not None and panel_i_mean is not None
            and panel_g_mean <= 0 and panel_i_mean <= 0)


CODES = {
    "F-both": ("a search from Cen works through the stem and a blurred dry guitar together, where the target is alone",
               "build the song-time search for alone windows behind a flag, for testing only, if the window count (Plan "
               "2's W0) is not W-rare (N3). Next: a real note-matched dry guitar on the same rows (waits for the user), "
               "then a blind sitting. No claim on released mixes"),
    "F-compound": ("each fault alone is survivable; together not shown",
                   "to the user. The dry guitar's quality decides; the rebuild's bar is to beat this blur"),
    "F-dry": ("the stem works as a reference; a dry guitar this blurred does not drive a search",
              "the route waits on a better dry guitar. Not a verdict on one"),
    "F-stem": ("the stem misleads a search even with no other guitar",
               "Direction 1 stops at the stem as a search reference. Separator work gets this row as its yardstick"),
    "F-undecided": ("not decided",
                    "to the user, with the intervals, what each rules out, BKS+GOAT beside, and the share of the "
                    "Control's G and I kept. The full 119 cannot tighten the pool (the panel's 3 DI files set its width)"),
    "F-start": ("a 262-render search from Cen is not shown to beat Cen recording by recording even with the true DI",
                "says nothing about the degraded inputs. To the user: a longer budget or a two-stage start, as a "
                "reviewed amendment"),
    "F-constant": ("the row lands on settings better than Cen, but the gain is not shown to be this recording's (G "
                   "passes, I does not): a better constant",
                   "to the user. No song-time search rests on it; the row's own centre (a side reading) is a lead for a "
                   "better constant, which needs no song-time search")}

P_, K_, F_, U_, U2_ = ("passes",), ("constant",), ("fails",), ("undecided",), ("undecided-b2",)
NOT_P = ("constant", "fails", "undecided")
B_NOT_P = ("constant", "fails", "undecided", "undecided-b2")
NONE = (None,)
OUTCOME_TABLE = (               # (b, Control, c, a, code, the row a constant cell rests on); None: not run
    (P_, NONE, P_, NONE, "F-both", None),
    (P_, NONE, NOT_P, P_, "F-compound", None),
    (P_, NONE, NOT_P, ("fails", "undecided"), "F-dry", None),
    (P_, NONE, NOT_P, K_, "F-constant", "fs-blur"),
    (F_, P_, NONE, NONE, "F-stem", None),
    (U_, P_, NONE, NONE, "F-undecided", None),
    (U2_, P_, P_, NONE, "F-both", None),                     # B2's lever: (c) after (b) undecided on the pool only
    (U2_, P_, ("fails", "undecided"), NONE, "F-undecided", None),
    (U2_, P_, K_, NONE, "F-constant", "fs-both"),
    (K_, P_, NONE, NONE, "F-constant", "fs-stem"),
    (B_NOT_P, ("fails", "undecided"), NONE, NONE, "F-start", None),
    (B_NOT_P, K_, NONE, NONE, "F-constant", "fs-control"))
ORDER = ("fs-stem", "fs-control", "fs-both", "fs-blur")      # the table's columns


def next_row(readings):
    """(Pure.) The row to run next from the rows read so far ({row: reading}, row (b)'s from `B_READINGS`), or None
    once a cell is reached. (b) first; (b) passing -> (c), then (a) unless (c) passes; (b) not passing -> the Control,
    then (c) only on B2's lever with the Control passing."""
    if "fs-stem" not in readings:
        return "fs-stem"
    b = readings["fs-stem"]
    if b == "passes":
        if "fs-both" not in readings:
            return "fs-both"
        if readings["fs-both"] != "passes" and "fs-blur" not in readings:
            return "fs-blur"
        return None
    if "fs-control" not in readings:
        return "fs-control"
    if b == "undecided-b2" and readings["fs-control"] == "passes" and "fs-both" not in readings:
        return "fs-both"
    return None


def paths(readings=None):
    """Every reachable set of read rows, as {row: reading}: from `next_row`, each row taking every reading."""
    readings = dict(readings or {})
    nxt = next_row(readings)
    if nxt is None:
        return [readings]
    out = []
    for r in (B_READINGS if nxt == "fs-stem" else READINGS):
        out += paths({**readings, nxt: r})
    return out


def table_hits(readings):
    cols = [readings.get(r) for r in ORDER]
    return [t for t in OUTCOME_TABLE if all(c in t[j] for j, c in enumerate(cols))]


def table_guard():
    """Refuse unless every reachable path ends in exactly one OUTCOME_TABLE cell, every cell is reachable, every code is
    declared, no path reads more than MAX_ROWS rows (N1), and 0 < SMALL < BIG."""
    used = set()
    for p in paths():
        hits = table_hits(p)
        if len(hits) != 1:
            raise SystemExit(f"OUTCOME_TABLE holds {p} {len(hits)} times")
        used.add(OUTCOME_TABLE.index(hits[0]))
        if len(p) > MAX_ROWS:
            raise SystemExit(f"a path reads {len(p)} rows: {p}")
    if used != set(range(len(OUTCOME_TABLE))):
        raise SystemExit(f"cells never reached: {sorted(set(range(len(OUTCOME_TABLE))) - used)}")
    if {t[4] for t in OUTCOME_TABLE} != set(CODES):
        raise SystemExit("OUTCOME_TABLE's codes are not the declared ones")
    for t in OUTCOME_TABLE:
        if (t[4] == "F-constant") != (t[5] is not None):
            raise SystemExit("a constant cell names no row, or another cell names one")
        if t[5] is not None:
            if t[ORDER.index(t[5])] != K_:
                raise SystemExit(f"{t}: its row does not read constant")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")


def outcome(readings):
    """(Pure.) The read so far. readings: {row: reading} (row (b)'s refined by B2's lever). No row stops on a count of
    refusals (S1): a refused part reads at Cen. Only the user's pool rule can still leave a row unread ("stopped": the
    pool lost the panel), which the Cen fallback no longer causes. -> {"code"/"next_row", "reading", "next"}."""
    table_guard()
    if "stopped" in readings.values():
        bad = sorted(r for r, v in readings.items() if v == "stopped")
        return {"code": "stopped", "reading": f"{', '.join(bad)} not read: the pool lost the panel (the report's "
                                              "stop_reason; the user's pool rule)",
                "next": "to the user: no row is read on from an unread row; any way on is an amendment"}
    nxt = next_row(readings)
    if nxt is not None:
        return {"code": None, "next_row": nxt, "reading": "no cell yet",
                "next": f"row {LETTER[nxt]} ({nxt}), by the coded cells, after the parent's audit of this read"}
    hit = table_hits(readings)
    if len(hit) != 1:
        raise SystemExit(f"OUTCOME_TABLE has {len(hit)} cells for {readings}")
    code, row = hit[0][4], hit[0][5]
    reading, nxt_txt = CODES[code]
    if row is not None:
        reading = f"row {LETTER[row]} ({row}): {reading}"
    if readings.get("fs-stem") == "undecided-b2":
        reading += " (row b undecided on the pool, passing on BKS+GOAT alone, the panel's means <= 0: B2's lever)"
    notes = [f"row {LETTER[r]} ({r}) reads constant: the gain is not shown to be this recording's"
             for r, v in readings.items() if v == "constant" and r != row]
    return {"code": code, "reading": reading, "next": nxt_txt, "notes": notes}


def b_refined(row, report_rows):
    """(Pure.) Row (b)'s table reading from its report: undecided on the pool becomes "undecided-b2" on B2's lever."""
    r = (report_rows.get("reading") or {}).get("reading")
    if row != "fs-stem" or r != "undecided":
        return r
    bg = (report_rows.get("reading_bks_goat") or {}).get("reading")
    pg = (report_rows["G"].get("panel") or {}).get("mean")
    pi = (report_rows["I"].get("panel") or {}).get("mean")
    return "undecided-b2" if b2_lever(r, bg, pg, pi) else r


DECIDING = ["bks", "goat", "panel"]      # the user's pool (2026-11-21): never read on fewer sets


def pool_refusal(rows):
    """(Pure.) Why the row's deciding pool is not the user's, or None: `preset_ladder.summarise` falls back to BKS+GOAT
    when fewer than 3 of the panel's DI files are read (`full_controls_c3r.deciding_sets`), which a single refused panel
    part can cause (the panel's DI files hold 1, 3 and 3 parts). Read on G and on I."""
    bad = [q for q in ("G", "I") if (rows.get(q) or {}).get("deciding_sets") != DECIDING]
    if bad:
        return (f"the deciding pool of {', '.join(bad)} is "
                f"{[(rows.get(q) or {}).get('deciding_sets') for q in bad]}, not {DECIDING}: the panel lost a DI file")
    return None


def stopped(refused):
    """(Pure.) S1 (phase_scratch_refusal_reports): no row stops on a count of refusals, so this is always False. The
    count and share are reported (`refusal_report`), a technical refusal is rerun once in a fresh process and then
    reads at Cen (`itt_per`), and a content check never refuses. Kept so every record keeps its "stopped" field."""
    return False


# --- refusals as reports (S1, the delegated decision agent's call under the user's no-made-up-bars rule) -------------

TECHNICAL_REFUSALS = ("search", "borrowed", "scoring_control", "start", "nonfinite", "dry")
CONTENT_REFUSALS = ("content",)          # a check against the true DI: a label on the part, never a refusal
G_FIELDS = ("G", "G_cp50", "G_cp100", "G_cp200", "G_shrunk")   # the part's own answers, ln(x / Cen): 0 at Cen
#   (G_centre is not: the row's centre is no part's fallback, so a refused part's G_centre stays None)
REFUSAL_SENSITIVE = "refusal-sensitive"


def refusal_reasons(why):
    """(Pure.) A refusal's own reasons, unwrapped from the row's "search" wrapper (`answer_parts` stores a search
    record's refusal as {"search": {reason: ...}}). -> {reason: ...}."""
    if isinstance(why, dict) and set(why) == {"search"} and isinstance(why["search"], dict):
        return why["search"]
    return why if isinstance(why, dict) else {"search": why}


def refusal_kind(why):
    """(Pure.) "content" when every reason is a content check, else "technical". why: a refusal's {reason: ...}."""
    kinds = set(refusal_reasons(why))
    return "content" if kinds and kinds <= set(CONTENT_REFUSALS) else "technical"


def _binom_cdf(k, n, q):
    return sum(math.comb(n, i) * q ** i * (1 - q) ** (n - i) for i in range(0, k + 1))


def clopper_pearson(k, n, conf=REFUSAL_CONF):
    """(Pure.) The exact (Clopper-Pearson) two-sided interval of k successes in n, by bisection. -> (lo, hi), or
    (None, None) when n is 0."""
    if n <= 0:
        return None, None
    a = (1 - conf) / 2

    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if f(mid):
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    low = 0.0 if k == 0 else solve(lambda q: 1 - _binom_cdf(k - 1, n, q) < a)
    high = 1.0 if k == n else solve(lambda q: _binom_cdf(k, n, q) > a)
    return low, high


def refusal_report(refused, sets_of, deciding=None, conf=REFUSAL_CONF):
    """(Pure.) The refusals as a report, never a stop: per set and pooled (over `deciding`, or every set), the count,
    the parts, the share and its Clopper-Pearson interval; each refusal's kind. sets_of: {pkey: set} of every part."""
    def cell(keys):
        r = sorted(k for k in keys if k in refused)
        lo, hi = clopper_pearson(len(r), len(keys), conf)
        return {"refused": len(r), "parts": len(keys), "share": len(r) / len(keys) if keys else None,
                f"lo{round(conf * 100)}": lo, f"hi{round(conf * 100)}": hi, "keys": r}
    sets = sorted(set(sets_of.values()))
    pool = [k for k, v in sets_of.items() if deciding is None or v in deciding]
    return {"per_set": {st: cell([k for k, v in sets_of.items() if v == st]) for st in sets},
            "pooled": cell(pool), "deciding": list(deciding) if deciding is not None else sets,
            "kinds": {k: {"kind": refusal_kind(v), "reasons": sorted(refusal_reasons(v))}
                      for k, v in sorted(refused.items())}, "stops": False}


def itt_per(per, refused, fields=G_FIELDS):
    """(Pure.) The intent-to-treat per-part numbers: a refused part with no numbers reads at Cen, its answer's
    fallback (every ln(x / Cen) field 0.0, the rest None: I and the borrowed answer need the partners scored on it),
    marked `cen_fallback`. A part with numbers keeps them; with nothing refused this is `per` unchanged."""
    out = dict(per)
    for k in refused:
        if out.get(k) is None:
            out[k] = dict({f: 0.0 for f in fields}, cen_fallback=True)
    return out


def itt_values(values, refused, cen=0.0):
    """(Pure.) As `itt_per` for one number a part ({pkey: value or None}): a refused part without a value reads `cen`
    (0.0: Cen less Cen)."""
    out = dict(values)
    for k in refused:
        if out.get(k) is None:
            out[k] = cen
    return out


def passing_only(per, refused):
    """(Pure.) The passing-only numbers beside the deciding read: every refused part dropped."""
    return {k: (None if k in refused else v) for k, v in per.items()}


NO_PASSING_INTERVAL = "no passing-only interval"


def refusal_label(code_itt, code_passing):
    """(Pure.) "refusal-sensitive" when the intent-to-treat and the passing-only reads give different codes (the row
    then goes to the user with both), else None; with no passing-only interval (`passing_code`'s None) the two reads
    cannot be compared, and the report says so instead."""
    if code_passing is None:
        return None
    return REFUSAL_SENSITIVE if code_itt != code_passing else None


def passing_code(code_fn, ok):
    """(Pure.) The passing-only read's code, or {"code": None, "reading": "no passing-only interval"} when it has no
    interval (ok False), never a silent fallback to the deciding read. code_fn() -> the code record."""
    return code_fn() if ok else {"code": None, "reading": NO_PASSING_INTERVAL}


def mean_diff(a, b, z=1.6448536269514722):
    """(Pure.) mean(a) - mean(b) with a normal 90% interval (Welch's standard error); None under 2 values a side."""
    if len(a) < 2 or len(b) < 2:
        return {"diff": None, "lo90": None, "hi90": None, "n": [len(a), len(b)]}
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return {"diff": ma - mb, "lo90": ma - mb - z * se, "hi90": ma - mb + z * se, "n": [len(a), len(b)]}


def refused_audit(parts, refused, band=None, start=None, values=None):
    """(Pure.) How the refused parts differ from the rest, on what is known before the held half (set, amp, class,
    lender band, Cen's search-half start value) and, after scoring, their value at the Cen fallback against the
    passing parts' (a difference of means with its interval). parts: the draw's; band: {unit: band}; start: {pkey:
    value}; values: {pkey: the intent-to-treat value}."""
    ref = [p for p in parts if p["pkey"] in refused]
    rest = [p for p in parts if p["pkey"] not in refused]

    def counts(group, f):
        out = {}
        for p in group:
            v = f(p)
            out[str(v)] = out.get(str(v), 0) + 1
        return dict(sorted(out.items()))
    fields = {"set": lambda p: p.get("set"), "amp": lambda p: p.get("amp"), "cls": lambda p: p.get("cls"),
              "band": lambda p: (band or {}).get(p.get("unit"))}
    out = {"refused": sorted(p["pkey"] for p in ref),
           "before_held": {f: {"refused": counts(ref, g), "rest": counts(rest, g)} for f, g in fields.items()}}
    if start:
        out["before_held"]["cen_start"] = mean_diff([start[p["pkey"]] for p in ref if p["pkey"] in start],
                                                    [start[p["pkey"]] for p in rest if p["pkey"] in start])
    if values:
        out["after_scoring"] = mean_diff([values[p["pkey"]] for p in ref if values.get(p["pkey"]) is not None],
                                         [values[p["pkey"]] for p in rest if values.get(p["pkey"]) is not None])
    return out


def rerun_path(path):
    """A record's rerun: the same file name in `<dir>-rerun/` beside its directory."""
    path = pathlib.Path(path)
    return path.parent.parent / f"{path.parent.name}-rerun" / path.name


def refused_record(rec, kind="search"):
    """(Pure.) Whether a stored record refused: a search record holds "refused"; a score record a failed control."""
    if kind == "search":
        return "refused" in rec
    return not rec.get("scoring_control_ok", True)


def with_reruns(keys, path_of, kind="search"):
    """Every record by key, a refused one replaced by its rerun's (`rerun_path`) when that passed. -> ({key: record},
    {key: path used}, {key: "rerun passed" | "rerun refused" | "rerun pending"}). A technical refusal is rerun once in a
    fresh process (the command's `--rerun`) before it reads at Cen; "rerun pending" means it has not been rerun yet."""
    recs, used, status = {}, {}, {}
    for k in keys:
        path = pathlib.Path(path_of(k))
        rec = json.loads(path.read_text())
        recs[k], used[k] = rec, path
        if not refused_record(rec, kind) or (kind == "search" and refusal_kind(rec.get("refused")) == "content"):
            continue
        rp = rerun_path(path)
        if not rp.exists():
            status[k] = "rerun pending"
            continue
        again = json.loads(rp.read_text())
        if refused_record(again, kind):
            status[k] = "rerun refused"
        else:
            recs[k], used[k], status[k] = again, rp, "rerun passed"
    return recs, used, status


def rerun_refusal(status):
    """(Pure.) Why a read or answers step must wait: a technical refusal not yet rerun once, or None."""
    pending = sorted(k for k, v in status.items() if v == "rerun pending")
    if pending:
        return (f"{len(pending)} technical refusal(s) not yet rerun once in a fresh process: run the command again "
                f"with --rerun first ({pending})")
    return None


# --- paths, the ledger, refusals ------------------------------------------------------------------------------------------

def fs_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT


def draw_path():
    return fs_dir() / "draw.json"


def search_path(row, pk):
    return fs_dir() / "search" / row / f"{pk}.json"


def answers_path(row):
    return fs_dir() / f"answers-{row}.json"


def score_path(row, pk):
    return fs_dir() / "score" / row / f"{pk}.json"


def report_path(row):
    return fs_dir() / f"report-{row}.json"


def rows_path(row):
    return fs_dir() / f"rows-{row}.json"


def file_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def fs_keys(entry):
    """(Pure.) The `phase_fs*` keys of a `preset-ladder` entry."""
    return {k: v for k, v in (entry or {}).items() if k.startswith("phase_fs")}


def on_main():
    """main's `preset-ladder` entry (origin/main after a fetch), and whether this checkout runs main's search: its
    learn/scratch_search.py and its `phase_fs*` keys equal main's. -> (main's entry or None, refusal or None)."""
    import subprocess

    from learn import note_replay as NR
    from learn import pipeline_fix as P

    def git(*a):
        return subprocess.run(["git", "-C", str(P.REPO), *a], capture_output=True, text=True)
    git("fetch", "-q", "origin", "main")
    led = git("show", "origin/main:docs/dev-test-ledger.json")
    if led.returncode:
        return None, f"main's ledger is not readable: {led.stderr.strip()}"
    m = NR.main_entry(led.stdout)
    if git("diff", "--quiet", "origin/main", "--", "learn/scratch_search.py").returncode:
        return m, "this checkout's learn/scratch_search.py differs from main's: run from merged code"
    a, b = fs_keys(NR.ledger_entry()), fs_keys(m)
    if a != b:
        diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        return m, f"this checkout's {', '.join(diff)} differ from main's: pull main (run from merged code)"
    return m, None


def require_on_main(*phases):
    m, why = on_main()
    if why:
        raise SystemExit(why)
    for k in phases:
        if not m or k not in m:
            raise SystemExit(f"main's {LEDGER_ID} entry has no {k}: merge it before running")
    return m


def require_hash(phase, path):
    """Refuse unless the file's sha256 is `phase`'s on main (and this checkout runs main's code and keys)."""
    from learn import note_replay as NR

    m = require_on_main(PHASE, phase)
    why = NR.hash_refusal(m, phase, file_sha(path))
    if why:
        raise SystemExit(f"{why} (the hash must be on main before this step)")
    return json.loads(pathlib.Path(path).read_text())


def require_draw():
    table_guard()
    if not draw_path().exists():
        raise SystemExit("no draw (run `draw` first)")
    return require_hash(PHASE_DRAW, draw_path())


def never_overwrite(path):
    if pathlib.Path(path).exists():
        raise SystemExit(f"{path} exists: never overwritten")


def read_so_far(main=None):
    """{row: table reading} from the reports written so far (row (b)'s refined by B2's lever). With `main` (main's
    `preset-ladder` entry), each report's answers sha256 must be main's `phase_fs_answers_<row>`, or this refuses."""
    from learn import note_replay as NR

    out = {}
    for row in ROWS:
        p = report_path(row)
        if p.exists():
            rep = json.loads(p.read_text())
            if main is not None:
                why = NR.hash_refusal(main, phase_answers(row), rep.get("answers_sha256"))
                if why:
                    raise SystemExit(f"{p}: {why}")
            out[row] = "stopped" if rep.get("stopped") else b_refined(row, rep["rows"])
    return out


def require_turn(row):
    """Refuse unless `row` is the coded next row from the reports so far, each read from answers hashed on main."""
    got = read_so_far(require_on_main(PHASE))
    if "stopped" in got.values():
        raise SystemExit(f"a row stopped ({got}): nothing runs on")
    nxt = next_row(got)
    if nxt != row:
        raise SystemExit(f"the coded next row is {nxt} (rows read so far {got}), not {row}")


# --- draw (zero renders, no held-half value) -------------------------------------------------------------------------------

REPLAY_NONFINITE = ("bks__set5__BKS_Bulldozer_Full__19_ElecGtr1aDI.wav@30.0#21_ElecGtr1cReamp.wav|pr12",
                    "bks__set5__BKS_Bulldozer_Full__36_ElecGtr7aDI.wav@225.0#38_ElecGtr7cReamp1.wav|pr12",
                    "goat__goat__item_105@20.0#amp_4|sw50r")   # B5: the replay's parts with non-finite blurred renders


def cmd_draw(_args):
    """The subset and its partners from the replay's hashed draw (zero renders; no held-half value read): `subset`,
    each part's identities, rig, lag, halves, Cen, the replay's position-0 search-half distances for the start check
    (`start_ref`), `with_partners`; B5's check of the replay's three parts with non-finite blurred renders. -> draw.json,
    its sha256 printed for the ledger."""
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    require_on_main(PHASE)
    table_guard()
    never_overwrite(draw_path())
    rd = NR.require_draw()
    sd = NR.Stored()
    if sd.st["sha256"] != rd["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the replay's draw")
    ent = {e["unit"]: e for e in sd.st["entries"]}
    keys = subset(rd["parts"])
    short = subset_shortfall(keys, rd["parts"])
    if short:
        raise SystemExit("the subset falls short: " + "; ".join(short))
    by = {p["pkey"]: p for p in rd["parts"]}
    parts = []
    for k in keys:
        p = by[k]
        ru = sd.units[(p["set"], p["unit"], p["amp"])]
        start_ref = {}
        for dry in sorted({d for d, _ in ROWS.values()}):
            rec = NR.load_dist(dry, p)
            if rec is None:
                raise SystemExit(f"{k}: the replay has no {dry} renders")
            start_ref[dry] = {r: rec["distances"][r][0] for r in sorted({r for _, r in ROWS.values()})}
        cen = p["menu"][0]
        if cen["kind"] != "cen":
            raise SystemExit(f"{k}: the replay's menu position 0 is not Cen")
        parts.append({"pkey": k, "ukey": p["ukey"], "set": p["set"], "unit": p["unit"], "amp": p["amp"],
                      "cluster": f"{p['set']}|{p['cluster']}", "fold": p["fold"], "cls": p["cls"], "title": p["title"],
                      "ids": sorted(map(list, ent[p["unit"]]["ids"])), "rig": ru["prt"]["rig"],
                      "section": p["section"], "lag": p["lag"], "search": p["search"], "held": p["held"],
                      "cen": {"select": cen["select"], "settings": cen["settings"]}, "start_ref": start_ref,
                      "replay_record": p["record"]})
    parts, refused = with_partners(parts)
    bad = [(p["pkey"], d, r) for p in parts for d, rs in p["start_ref"].items() for r, v in rs.items()
           if not finite_pos(v)]
    b5 = {k: {"drawn": k in {p["pkey"] for p in parts},
              "position_0_finite": all(finite_pos(v) for p in parts if p["pkey"] == k
                                       for rs in p["start_ref"].values() for v in rs.values())}
          for k in REPLAY_NONFINITE}
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "seed": SEED, "partner_seed": PARTNER_SEED,
           "replay_draw_sha256": NR.file_sha(NR.draw_path()), "c3r_sha256": sd.st["sha256"],
           "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "counts": {s: {"parts": sum(p["set"] == s for p in parts),
                          "clusters": len({p["cluster"] for p in parts if p["set"] == s}),
                          "amps": {a: sum(p["set"] == s and p["amp"] == a for p in parts) for a in AMPS}}
                      for s in SETS},
           "refused_for_partners": refused, "nonfinite_position_0": bad, "b5_replay_nonfinite_parts": b5,
           "partners_across_sets": sorted(p["pkey"] for p in parts if p["partner_scope"] == "across sets"),
           "parts": parts}
    if bad:
        raise SystemExit(f"a drawn part has no finite position-0 distance: {bad[:3]}")
    P.save(draw_path(), out)
    print(f"FS DRAW: {len(parts)} parts {json.dumps(out['counts'])}; refused for partners {refused}; across sets "
          f"{len(out['partners_across_sets'])}; B5 {json.dumps(b5)}; sha256 {file_sha(draw_path())} (into the ledger "
          f"as {PHASE_DRAW} before any render)")


# --- the search (renders; the held half is never in the process) ----------------------------------------------------------

class StartRefused(Exception):
    """The search's first evaluation is not the replay's position 0 within START_TOL, or not usable: the part refuses."""


def step1_search(amp, start, evaluate, start_ref, budget=BUDGET):
    """Step 1, C2's: `knob_ceiling.coord_search` over `full_controls.c1a_space(amp, start)` at `budget`, seed
    `full_controls.SEED`, cats "levels", canon `full_controls.make_canon(amp)`. evaluate(x) -> (search-half value, peak
    dBFS, render sha256). The first evaluation must pass `start_check` against `start_ref` (else StartRefused).
    -> (evaluations [{value, peak_dbfs, render_sha256, x, t}], names)."""
    from learn import full_controls as F
    from learn import knob_ceiling as K

    dims = F.c1a_space(amp, start)
    names = [d.name for d in dims]
    evals = []

    def f(x):
        v, pk, sha = evaluate(x)
        if not evals:
            if not start_check(v, start_ref):
                raise StartRefused({"value": v, "ref_value": start_ref, "sha": sha})
            if usable(v, pk, None):
                raise StartRefused({"value": v, "why": usable(v, pk, None)})
        evals.append({"value": v, "peak_dbfs": pk, "render_sha256": sha, "x": dict(x),
                      "t": {nm: x.get(tuple(nm.rsplit("/", 1))) for nm in names}})
        return v
    K.coord_search(dims, start, f, budget, F.SEED, cats="levels", canon=F.make_canon(amp))
    return evals, names, dims


def step1_choice(evals, budget=BUDGET):
    """(Pure on evaluations.) The bound from the start's peak (`full_controls_c2.peak_bound`), step 1's best and the
    checkpoints' incumbents under it (`best_index`, the search half only). -> (bound, best index, {checkpoint: index})."""
    from learn import full_controls_c2 as C2

    bound = C2.peak_bound(evals[0]["peak_dbfs"])
    i1 = best_index(evals, bound, budget)
    if i1 is None:
        i1 = 0
    return bound, i1, {c: best_index(evals, bound, c) for c in CHECKPOINTS}


def run_part(p, dry, ref_name, x32, ref_blank, new_renderer, lists, log=print, budget=BUDGET, start_ref=None,
             dry_sha256=None, step1_only=False):
    """One part's search for one row: step 1 (C2's), step 2 (C1b's stages A and B in a fresh process primed with step
    1's best, its first evaluation within START_TOL of step 1's best value, canonical then raw on a miss), the final
    rendered fresh, C2's fallbacks (F70's peak guard) on the search half only. Every distance is J0 on the search half
    against `ref_blank` (zeros outside the search half). -> the part's record (no held-half value exists in it).

    Added for the `fs-notes` row (`learn/scratch_notes.py`), each a no-op at its default, so rows (b) and (c) run
    exactly as they did: `start_ref`, the start check's reference when it is not the draw's `p["start_ref"][dry]
    [ref_name]`; `dry_sha256`, the dry guitar's sha256, recorded in the record; `step1_only`, the search check's stop
    after step 1 (its record has no answer)."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import full_controls as F
    from learn import full_controls_c1b as C
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import note_replay as NR
    from learn import pretrain_set as PS

    amp, search, lag = p["amp"], p["search"], p["lag"]
    sel = p["cen"]["select"]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    dj = np.asarray(x32, np.float64)[trim[0]:trim[1]]
    renders = [0]

    def judge(y):
        y = np.asarray(y, np.float64)[trim[0]:trim[1]]
        if not np.isfinite(y).all():                  # declared: a non-finite render is the worst
            return math.inf, None, AM.audio_sha(np.nan_to_num(y))
        return NR.half_distance(ref_blank, y, dj, lag, search), A.peak_dbfs(y, trim_s=0.0), AM.audio_sha(y)

    def sx1(x):
        return LO.tdict(LO.sdict(x))

    def sorted_x(x):
        return LO.tdict(LO.sdict(C.plugin(x, amp)))

    cen = p["cen"]["settings"]
    start = F.c1a_start(cen, amp)
    bad = F.audible_change(start, cen, amp, declared=())
    if bad:
        return {"refused": {"start_changes_what_sounds": bad}, "renders": 0}
    base = {"plan": PLAN, "part": p["pkey"], "dry": dry, "ref": ref_name, "amp": amp, "select": sel, "search": search,
            "lag": lag, "budget": BUDGET, "start_settings": LO.sdict(start)}
    if dry_sha256 is not None:
        base["dry_sha256"] = dry_sha256
    t0 = time.time()
    # --- step 1 ---
    rr = new_renderer()
    try:
        rr.render(x32, sel, sx1(start))
        renders[0] += 1

        def ev1(x):
            renders[0] += 1
            return judge(rr.render(x32, sel, sx1(x)))
        try:
            evals, names, dims1 = step1_search(amp, start, ev1, p["start_ref"][dry][ref_name] if start_ref is None
                                               else start_ref, budget=budget)
        except StartRefused as e:
            return {**base, "refused": {"start": e.args[0]}, "renders": renders[0], "seconds": time.time() - t0}
    finally:
        rr.close()
    bound, i1, cps = step1_choice(evals, budget)
    best1 = evals[i1]
    bx = best1["x"]
    s1 = {"evaluations": len(evals), "curve": [e["value"] for e in evals], "searched_keys": names,
          "trials": [{"t": e["t"], "value": e["value"], "peak_dbfs": e["peak_dbfs"]} for e in evals],
          "start": {"value": evals[0]["value"], "ref_value": p["start_ref"][dry][ref_name] if start_ref is None
                    else start_ref,
                    "peak_dbfs": evals[0]["peak_dbfs"], "render_sha256": evals[0]["render_sha256"]},
          "bound": bound, "best_index": i1, "best_value": best1["value"],
          "checkpoints": {str(c): {"index": i, "value": evals[i]["value"], "settings": LO.sdict(sx1(evals[i]["x"]))}
                          for c, i in cps.items() if i is not None}}
    if step1_only:
        return {**base, "step1": s1, "step1_only": True, "renders": renders[0], "seconds": time.time() - t0}
    # --- step 2: C1b's stages A and B ---
    label1 = LO.sdict(bx)
    wet = C.dry_start_problems(LO.tdict(label1), amp)
    if wet:
        raise SystemExit(f"{p['pkey']}: step 2's start must be dry: {wet} on")

    def dry_stages(x0, canon, ref2):
        seen, xs, stage_of, trace, stage = {}, {}, {}, [], ["A"]
        rr2 = new_renderer()
        try:
            rr2.render(x32, sel, sorted_x(x0))
            renders[0] += 1

            def f(x):
                k = K.key(x)
                if k in seen:
                    return seen[k]["value"]
                renders[0] += 1
                v, pk, sha = judge(rr2.render(x32, sel, sorted_x(x)))
                if not trace and not F.within(v, ref2):
                    raise F.StartMiss(v, sha)
                seen[k], xs[k], stage_of[k] = {"value": v, "peak_dbfs": pk}, dict(x), stage[0]
                trace.append({"stage": stage[0], "value": v, "peak_dbfs": pk})
                return v

            cn = canon or (lambda x: x)

            def best_of(ks, fallback):
                i = best_index([seen[q] for q in ks], bound)
                return cn(xs[ks[i]]) if i is not None else fallback
            K.coord_search(C.rooms_dims(x0), x0, f, C.BUDGET_ROOMS, C.SEED, cats="levels", canon=canon)
            xa = best_of([q for q in seen if stage_of[q] == "A"], cn(x0))
            stage[0] = "B"
            dims_b = C.mics_eq_dims(xa, amp, lists)
            K.knob_search(dims_b, xa, f, C.BUDGET_MICS_EQ, C.SEED + 1, shares=C.STAGE_B_SHARES, canon=canon)
            xb = best_of([K.key(xa)] + [q for q in seen if stage_of[q] == "B"], xa)
        finally:
            rr2.close()
        return xa, xb, {"trace": trace, "start": seen[K.key(x0)], "b": seen[K.key(xb)],
                        "dims": [dim_spec(d) for d in C.rooms_dims(x0)] + [dim_spec(d) for d in dims_b]}

    kind, miss2, s2rec, final, form = "canonical", None, None, None, None
    for kind, x0, canon in (("canonical", C.c1b_start(label1, amp), C.make_canon(amp)),
                            ("raw_after_miss", C.raw_start(label1, amp), None)):
        if kind == "canonical" and C.audible_change(x0, label1, amp):    # C2's check (the raw start is the label)
            raise SystemExit(f"{p['pkey']}: step 2's start changes what sounds")
        try:
            xa, xb, s2rec = dry_stages(x0, canon, best1["value"])
            final, form = xb, "plugin"
            break
        except F.StartMiss as m:
            miss2 = dict(miss2 or {}, **{kind: m.value})
    else:
        kind = "refused"
        final, form = bx, "step1"
    # --- the final, fresh; C2's fallbacks on the search half ---
    xs_final = sorted_x(final) if form == "plugin" else sx1(final)
    renders[0] += 2
    vf, pkf, shaf = judge(AM.fresh_render(new_renderer, x32, sel, xs_final, xs_final))
    why = usable(vf, pkf, bound)
    fallback = None
    answer = LO.sdict(xs_final)
    specs = [dim_spec(d) for d in dims1] + ((s2rec or {}).get("dims") or [] if form == "plugin" else [])
    if why:
        st = (s2rec or {}).get("start")
        why1 = usable(st["value"], st["peak_dbfs"], bound) if st else why
        if why1 is None:
            fallback, answer, specs = "step1", LO.sdict(sx1(bx)), [dim_spec(d) for d in dims1]
        else:
            fallback, answer, specs = "start", LO.sdict(sx1(start)), []
    log(f"{p['pkey'][-60:]}: step 1 {len(evals)} + step 2 {len((s2rec or {}).get('trace') or [])} ({kind}"
        f"{', fallback ' + fallback if fallback else ''}); {renders[0]} renders, {time.time() - t0:.0f} s")
    return {**base, "step1": s1, "step2": {"start_kind": kind, "first_start_miss": miss2,
                                            "trace": (s2rec or {}).get("trace"),
                                            "best_value": ((s2rec or {}).get("b") or {}).get("value")},
            "final_fresh": {"value": vf, "peak_dbfs": pkf, "render_sha256": shaf, "unusable": why},
            "fallback": fallback, "answer": {"select": sel, "settings": answer}, "searched_dims": specs,
            "renders": renders[0], "seconds": time.time() - t0, "time": time.strftime("%Y-%m-%d %H:%M:%S")}


def load_ref_blank(sd, p, ref_name):
    """The row's reference for a part with every sample outside its search half set to zeros (`blank_plan`); the
    unblanked array is dropped before the search sees anything."""
    import numpy as np

    from analysis.aligned import SAMPLE_RATE

    from learn import knob_ceiling as K
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
    if ref_name == "clean":
        ref = np.array(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)
    else:
        ref = np.array(NR.load_stem(ref_name, p), np.float64)
    for lo, hi in blank_plan(len(ref), p["search"], K.R.HALVES, SAMPLE_RATE):
        ref[lo:hi] = 0.0
    return ref


def npy_sha(x):
    """sha256 of `x` as float32 in `.npy` form: the same bytes a dry guitar's file holds when `np.save`d."""
    import io

    import numpy as np

    buf = io.BytesIO()
    np.save(buf, np.asarray(x, np.float32))
    return hashlib.sha256(buf.getvalue()).hexdigest()


def search_row_part(p, dry, ref_name, x32, ref_blank, new_renderer, lists, out, ledger, start_ref=None,
                    dry_sha256=None, log=print):
    """One part's search for any row, written once to `out` (the per-part body of `cmd_search`, shared with the
    `fs-notes` row): `run_part`, its record tagged with `ledger`. With `dry_sha256` (the dry guitar the row declared),
    the audio handed to `run_part` is hashed itself (`npy_sha`) and refused before any render unless it is that one;
    the measured sha256 goes into the record. Rows (b) and (c) pass none and run as before. -> the record."""
    from learn import pipeline_fix as P

    if dry_sha256 is not None:
        got = npy_sha(x32)
        if got != dry_sha256:
            raise SystemExit(f"{p['pkey']}: the dry guitar handed to the search is not the declared one "
                             f"({got[:12]}, not {dry_sha256[:12]}): nothing rendered")
        dry_sha256 = got
    rec = run_part(p, dry, ref_name, x32, ref_blank, new_renderer, lists, log=log, start_ref=start_ref,
                   dry_sha256=dry_sha256)
    rec["ledger"] = ledger
    P.save(out, rec)
    return rec


def cmd_search(args):
    """One shard of a row's searches (renders): the coded next row only; each part's record written once."""
    from learn import note_replay as NR

    row = args.row
    draw = require_draw()
    require_turn(row)
    NR.no_separation_beside()
    dry, ref_name = ROWS[row]
    blur_rec = None
    if dry != "true":
        blur_rec = json.loads((NR.replay_dir() / "blur.json").read_text())
        if blur_rec["draw_sha256"] != draw["replay_draw_sha256"]:
            raise SystemExit("blur.json was made from another replay draw")
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    sd = NR.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    rby = {p["pkey"]: p for p in NR.require_draw()["parts"]}
    k, n = args.shard
    mine = [p for j, p in enumerate(sorted(draw["parts"], key=lambda p: p["pkey"])) if j % n == k]
    if args.first:
        mine = mine[:args.first]
    lists = C.mic_lists()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in mine:
        out = search_path(row, p["pkey"])
        if out.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        di32 = NR.di_section(prt)
        x32 = di32 if dry == "true" else NR.load_dry(dry, rby[p["pkey"]], di32, blur_rec)
        ref_blank = load_ref_blank(sd, p, ref_name)
        rec = search_row_part(p, dry, ref_name, x32, ref_blank, CB.new_renderer, lists, out, f"{LEDGER_ID} {PHASE}")
        total += rec.get("renders", 0)
        if "refused" in rec:
            print(f"{p['pkey'][-60:]}: REFUSED {rec['refused']}", flush=True)
        print(f"shard {k}/{n}: {total} renders in {time.time() - t0:.0f} s ({total / max(1, time.time() - t0) * 3600:.0f}"
              " an hour)", flush=True)
    print(f"FS-SEARCH DONE {row} {k}/{n}: {total} renders in {time.time() - t0:.0f} s")


# --- the answers (zero renders): hashed before the score -------------------------------------------------------------------

def answer_parts(draw, recs, search_sha):
    """(Pure but for `search_sha`.) The answers of any row from its search records (the per-part body of `cmd_answers`,
    shared with the `fs-notes` row): per part the answer, step 1's incumbents at 50, 100 and 200, the shrunk answer,
    the borrowed answer's partners and the row's centre; each refusal with why. recs: {pkey: search record};
    search_sha(pkey) -> the record file's sha256. -> (parts, refused)."""
    answered = {k for k, r in recs.items() if "refused" not in r}
    parts, refused = {}, {}
    for p in draw["parts"]:
        k = p["pkey"]
        r = recs[k]
        if "refused" in r:
            refused[k] = {"search": r["refused"]}
            continue
        bq = borrowed(p, answered)
        if bq is None:
            refused[k] = {"borrowed": f"fewer than {PARTNERS} partners answered"}
            continue
        ans = r["answer"]["settings"]
        cps = {f"cp{c}": (r["step1"]["checkpoints"].get(str(c)) or {}).get("settings") for c in CHECKPOINTS}
        pool = [q for q in p["partners"] if q in answered]
        parts[k] = {"select": r["answer"]["select"], "answer": ans, **cps,
                    "shrunk": shrunk(ans, p["cen"]["settings"], r["searched_dims"]),
                    "centre": centre([(recs[q]["answer"]["settings"], recs[q]["searched_dims"]) for q in pool],
                                     p["cen"]["settings"]),
                    "borrowed": bq, "centre_pool": pool, "fallback": r.get("fallback"),
                    "search_sha256": search_sha(k)}
    return parts, refused


def cmd_answers(args):
    """The row's answers from its search records (zero renders): per part the answer, step 1's incumbents at 50, 100
    and 200, the shrunk answer, the borrowed answer's partners (`borrowed`) and the row's centre (`centre`), every
    refusal with why, reported (S1: never a stop). -> answers-<row>.json; its sha256 into the ledger as
    phase_fs_answers_<row> before `score`."""
    from learn import pipeline_fix as P

    row = args.row
    draw = require_draw()
    require_turn(row)
    never_overwrite(answers_path(row))
    recs = {}
    for p in draw["parts"]:
        sp = search_path(row, p["pkey"])
        if not sp.exists():
            raise SystemExit(f"{p['pkey']}: not searched")
        recs[p["pkey"]] = json.loads(sp.read_text())
    parts, refused = answer_parts(draw, recs, lambda k: file_sha(search_path(row, k)))
    out = {"plan": PLAN, "row": row, "dry": ROWS[row][0], "ref": REF_NAME[ROWS[row][1]],
           "draw_sha256": file_sha(draw_path()), "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "renders": sum(r.get("renders", 0) for r in recs.values()),
           "refused": refused, "stopped": stopped(refused), "parts": parts}
    P.save(answers_path(row), out)
    print(f"FS ANSWERS {row}: {len(parts)} parts, {len(refused)} refused (each reads at Cen); "
          f"{out['renders']} search renders; sha256 {file_sha(answers_path(row))} (into the ledger as "
          f"{phase_answers(row)} before `score`)")


# --- the score (the only step that reads a held half) ----------------------------------------------------------------------

def to_score(a):
    """(Pure.) A part's distinct settings to render for the score: {name: settings}; the partners' answers come from
    the answers file. Names: cen, answer, cp50, cp100, cp200, shrunk, centre, then each borrowed partner's pkey."""
    return {k: a[k] for k in ("answer", "cp50", "cp100", "cp200", "shrunk", "centre") if a.get(k) is not None}


def score_row_part(p, a, ans_parts, row, answers_sha, sd, new_renderer):
    """One part's score for any row (the per-part body of `cmd_score`, shared with the `fs-notes` row and its score
    check): Cen, `to_score`'s settings and the borrowed partners' answers (from `ans_parts`) through the part's true
    DI, each primed alone, judged on the held half against the clean record; the scoring control against Cen's stored
    held-half value. -> (the record, renders)."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import note_replay as NR
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
    di32 = NR.di_section(prt)
    di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
    clean = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
    sets = {"cen": p["cen"]["settings"], **to_score(a), **{q: ans_parts[q]["answer"] for q in a["borrowed"]}}
    done, held, shas, renders = {}, {}, {}, 0
    for name, s in sets.items():
        x = LO.tdict(s)
        kk = K.key(x)
        if kk not in done:
            y = np.asarray(AM.fresh_render(new_renderer, di32, a["select"], x, x), np.float64)[trim[0]:trim[1]]
            renders += 2
            done[kk] = (NR.half_distance(clean, y, di, p["lag"], p["held"]) if np.isfinite(y).all()
                        else math.inf, AM.audio_sha(np.nan_to_num(y)))
        held[name], shas[name] = done[kk]
    stored = sd.cen_judge((p["set"], p["unit"], p["amp"]))[p["held"]]
    ctl = finite_pos(held["cen"]) and finite_pos(stored) and abs(math.log(held["cen"] / stored)) <= SCORE_TOL
    return ({"plan": PLAN, "row": row, "part": p["pkey"], "held": held, "render_sha256": shas, "cen_stored": stored,
             "scoring_control_ok": ctl, "borrowed": a["borrowed"], "answers_sha256": answers_sha,
             "distinct_renders": len(done)}, renders)


def cmd_score(args):
    """One shard of a row's score (renders): every setting of the hashed answers through the part's true DI, each primed
    alone (`audibility_measure.fresh_render`, as the ladder rendered Cen's stored value), judged on the held half
    against the clean record; Cen re-rendered beside (the scoring control: within SCORE_TOL of its stored held-half
    value). -> score/<row>/<part>.json."""
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as NR
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    row = args.row
    draw = require_draw()
    require_turn(row)
    ans = require_hash(phase_answers(row), answers_path(row))
    if ans.get("stopped"):                               # no answers file is written stopped since S1
        raise SystemExit(f"{row}'s answers were written stopped: nothing is scored")
    NR.no_separation_beside()
    sd = NR.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    k, n = args.shard
    mine = [p for j, p in enumerate(sorted(draw["parts"], key=lambda p: p["pkey"])) if j % n == k]
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in mine:
        out = score_path(row, p["pkey"])
        a = ans["parts"].get(p["pkey"])
        if a is None or out.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        rec, used = score_row_part(p, a, ans["parts"], row, file_sha(answers_path(row)), sd, CB.new_renderer)
        total += used
        P.save(out, rec)
        held, stored, ctl = rec["held"], rec["cen_stored"], rec["scoring_control_ok"]
        print(f"{p['pkey'][-60:]}: scored {rec['distinct_renders']} settings; Cen {held['cen']:.5g} vs stored "
              f"{stored:.5g} ({'ok' if ctl else 'MISS'}); {total} renders, {time.time() - t0:.0f} s", flush=True)
    print(f"FS-SCORE DONE {row} {k}/{n}: {total} renders in {time.time() - t0:.0f} s")


def summarise_row(sd, draw, per):
    """The row's numbers by `note_replay.summary` (the deciding pool BKS+GOAT+panel, `full_controls_c3r.pooled`), with
    BKS+GOAT pooled alone beside. per: {pkey: part_numbers or None}."""
    from learn import full_controls_c3r as R
    from learn import note_replay as NR

    band = NR.lender_band()
    parts = [dict(p, cluster=p["cluster"].split("|", 1)[1]) for p in draw["parts"] if per.get(p["pkey"]) is not None]
    out = {}
    fields = ["G", "I"] + [f"{q}_{k}" for k in ("cp50", "cp100", "cp200", "shrunk", "centre") for q in ("G", "I")] + \
        ["answer_less_centre", "blind", "label_less_cen"]
    for q in fields:
        vals = {p["pkey"]: per[p["pkey"]].get(q) for p in parts}
        if not any(v is not None for v in vals.values()):
            continue
        row = NR.summary(sd.units, parts, vals, band)
        bg = {s: row[s] for s in ("bks", "goat")}
        row["bks_goat"] = R.pooled(bg) if all(v.get("mean") is not None for v in bg.values()) else None
        out[q] = row
    return out


def read_row_parts(draw, ans, answers_sha, score_file, sd, rby):
    """The per-part numbers of any row from its scored files (the per-part body of `cmd_read`, shared with the
    `fs-notes` row): `nonfinite_rule`, `part_numbers`, the scoring-control misses as refusals, the stored label less
    Cen and the moves beside. score_file(pkey) -> the score file's path. -> (per, refused, replaced, misses)."""
    from learn import note_replay as NR

    refused = dict(ans["refused"])
    per, replaced, ctl_miss = {}, {}, []
    for p in draw["parts"]:
        k = p["pkey"]
        if ans.get("stopped") or k not in ans["parts"]:    # a refused part (or a pre-S1 stopped row) was not scored
            per[k] = None
            continue
        sp = score_file(k)
        if not sp.exists():
            raise SystemExit(f"{k}: not scored")
        sc = json.loads(sp.read_text())
        if not sc["scoring_control_ok"]:                 # S1: a miss is rerun once in a fresh process first
            if not rerun_path(sp).exists():
                raise SystemExit(f"{k}: a scoring-control miss not yet rerun once in a fresh process: run `score "
                                 "--rerun` first")
            again = json.loads(rerun_path(sp).read_text())
            if again["scoring_control_ok"]:
                sc = again
        if sc["answers_sha256"] != answers_sha:
            raise SystemExit(f"{k}: scored from other answers")
        if not sc["scoring_control_ok"]:
            refused[k] = {"scoring_control": {"cen": sc["held"]["cen"], "stored": sc["cen_stored"]}}
            ctl_miss.append(k)
            per[k] = None
            continue
        held, rep = nonfinite_rule(sc["held"])
        if rep:
            replaced[k] = rep
        per[k] = part_numbers(held, sc["borrowed"])
        rp = rby[k]                            # beside, zero renders: the stored label less Cen (the replay's menu)
        per[k]["label_less_cen"] = NR.h_of(sd.held((rp["set"], rp["unit"], rp["amp"]), rp["menu"]))[NR.LABEL_INDEX]
        per[k]["moves"] = moves(ans["parts"][k]["answer"], p["cen"]["settings"])
    return per, refused, replaced, ctl_miss


def report_body(row, letter, answers_sha, per, refused, replaced, ctl_miss):
    """(Pure.) A row's report before its rows: as `cmd_read` writes it. No row stops on its refusals (S1)."""
    return {"plan": PLAN, "row": row, "letter": letter, "answers_sha256": answers_sha,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"), "refused": refused, "stopped": stopped(refused),
            "stop_reason": None, "nonfinite_replaced": replaced, "scoring_control_misses": ctl_miss, "parts": per}


def cmd_read(args):
    """The row's reading (zero renders), once: the per-part numbers from the scored files (`nonfinite_rule`,
    `part_numbers`), the refusals (search, borrowed answer, scoring control) reported and each read at Cen (S1: the
    deciding read on every part; the passing-only read beside, with `refusal_label`), the rows saved before the
    reading; then the outcome so far (`outcome`: the cell, or the coded next row). -> report-<row>.json."""
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    row = args.row
    draw = require_draw()
    ans = require_hash(phase_answers(row), answers_path(row))
    require_turn(row)
    never_overwrite(report_path(row))
    sd = NR.Stored()
    rby = {p["pkey"]: p for p in NR.require_draw()["parts"]}
    per, refused, replaced, ctl_miss = read_row_parts(draw, ans, file_sha(answers_path(row)),
                                                      lambda k: score_path(row, k), sd, rby)
    out = report_body(row, LETTER[row], file_sha(answers_path(row)), per, refused, replaced, ctl_miss)
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    out["refusal_report"] = refusal_report(refused, sets_of, DECIDING)
    rows = summarise_row(sd, draw, itt_per(per, refused))           # the deciding read: every part (S1)
    dry, ref = ROWS[row]
    start = {p["pkey"]: ((p.get("start_ref") or {}).get(dry) or {}).get(ref) for p in draw["parts"]}
    rows_pass = summarise_row(sd, draw, passing_only(per, refused)) if refused else rows
    never_overwrite(rows_path(row))
    P.save(rows_path(row), dict(out, rows=rows, rows_passing_only=rows_pass))   # saved before the reading
    why = pool_refusal(rows)
    if why:                                              # the user's pool or nothing: to the user
        out.update(stopped=True, stop_reason=why)
    else:
        rows["reading"] = row_reading(rows["G"]["deciding_pool"], rows["I"]["deciding_pool"])
        rows["reading_bks_goat"] = row_reading(rows["G"]["bks_goat"], rows["I"]["bks_goat"])
        passing = row_reading((rows_pass.get("G") or {}).get("deciding_pool"),
                              (rows_pass.get("I") or {}).get("deciding_pool")) if refused else rows["reading"]
        out["reading_passing_only"] = passing
        out["label"] = refusal_label((rows["reading"] or {}).get("reading"), (passing or {}).get("reading"))
        if refused:
            g_itt = {k: (v or {}).get("G") for k, v in itt_per(per, refused).items()}
            out["refused_audit"] = refused_audit(draw["parts"], refused, NR.lender_band(),
                                                 start={k: v for k, v in start.items() if v is not None}, values=g_itt)
    out["rows"] = rows
    P.save(report_path(row), out)                        # one write: the report holds its reading or its stop
    m = require_on_main(PHASE)
    o = outcome(read_so_far(m))
    if out["stopped"]:
        print(f"{row}: STOPPED ({out['stop_reason']})")
    else:
        rows = out["rows"]
        g, i = rows["G"]["deciding_pool"] or {}, rows["I"]["deciding_pool"] or {}
        print(f"{row}: G {g.get('mean')} [{g.get('lo90')}, {g.get('hi90')}], I {i.get('mean')} [{i.get('lo90')}, "
              f"{i.get('hi90')}] -> {(rows['reading'] or {}).get('reading')}; BKS+GOAT "
              f"{(rows['reading_bks_goat'] or {}).get('reading')}")
    P.save(fs_dir() / "outcome.json", dict(o, readings=read_so_far(m), time=time.strftime("%Y-%m-%d %H:%M:%S")))
    print(f"OUTCOME {o.get('code')}: {o['reading']}. Next: {o['next']}")


# --- main -----------------------------------------------------------------------------------------------------------------

def _shard(s):
    k, n = (int(x) for x in s.split("/"))
    if not 0 <= k < n or n > 3:
        raise argparse.ArgumentTypeError("k/n with 0 <= k < n <= 3 (at most 3 render processes)")
    return k, n


COMMANDS = {"draw": cmd_draw, "search": cmd_search, "answers": cmd_answers, "score": cmd_score, "read": cmd_read}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--row", choices=sorted(ROWS))
    ap.add_argument("--shard", type=_shard, default=(0, 1))
    ap.add_argument("--first", type=int, default=0, help="search only this shard's first n parts (the re-timing)")
    args = ap.parse_args(argv)
    if args.cmd != "draw" and not args.row:
        ap.error(f"{args.cmd} needs --row")
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
