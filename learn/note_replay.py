"""The note-matched replay, Direction 1's deciding test (`docs/note-replay-plan.md`; ledger `preset-ladder`
`phase_replay`, `phase_replay_draw`, `phase_replay_picks`, `phase_replay_picks_singles`, `phase_replay_outcome`).

On held-out ladder parts, a menu of 23 stored settings a part (Cen, S, the label and 20 step-1 trials by level) is
rendered through a dry guitar and compared, on the search half only, with a reference. The pick is the closest menu
setting; its score is its stored held-half judge through the true DI against the clean record. Two numbers a row: G
(the pick less Cen) and I (the pick less the blind pick, the menu's mean). Six rows: the Control (clean record, true
DI), the blurred DI (`di_robustness`'s `avg+mild`), the stem alone (`xlnoG@-3`), the stem of the full mix (`xl@-3`),
and both on each stem. Two single-blur rows (`avg`, `mild`) run only when the blurred DI fails or reads undecided.

    $MAIN -m learn.note_replay draw                         # units, menus, the stored control (zero renders)
    # the draw file's sha256 goes into the ledger (phase_replay_draw) before anything below
    $MAIN -m learn.note_replay blur                         # the blurred DIs (CPU)
    $MSST -m learn.note_replay sep --device mps             # 244 stems, never beside a render
    $MAIN -m learn.note_replay position-check               # 288 renders: picks the render mode, times the rate
    $MAIN -m learn.note_replay render --shard 0/3           # ... 1/3, 2/3: 122 parts x 2 dry guitars x 23 settings
    $MAIN -m learn.note_replay control                      # a failed Control stops the replay (zero renders)
    $MAIN -m learn.note_replay bleed --verdict clean|bleed  # optional: the user's ear check of Drowning, before pick
    $MAIN -m learn.note_replay pick                         # distances only; its sha256 into the ledger
    $MAIN -m learn.note_replay score                        # the rows, then R_TABLE or the singles trigger
    # only when score says the singles are triggered (phase_replay_picks_singles after their pick):
    $MAIN -m learn.note_replay render --dry avg,mild --shard 0/3
    $MAIN -m learn.note_replay pick --singles
    $MAIN -m learn.note_replay score --singles

$MAIN is the main checkout's .venv python, $MSST `~/ndsp-presets/tools/msst-venv/bin/python`. The pure parts (the
menu rule, the draw, the picks, the readings, `R_TABLE`, the dry-guitar reading, the Control's check, the halves'
separation) are tested in tests/test_note_replay.py on the light CI runner (no numpy).
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
PLAN = "docs/note-replay-plan.md"
PHASE = "phase_replay"                       # the declaration: before the draw
PHASE_DRAW = "phase_replay_draw"             # the draw file's sha256: before any blur, separation or render
PHASE_PICKS = "phase_replay_picks"           # picks.json's sha256: before `score` loads a held-half value
PHASE_PICKS2 = "phase_replay_picks_singles"  # picks-singles.json's sha256: before `score --singles`
OUT = "replay"                               # PF/replay/
SEED = 20261201                              # the draw
BLUR_SEED = 20261202                         # the blurs: the others drawn per source, the mild artefacts' draws
POSITION_SEED = 20261203                     # the position check's 12 parts
POWER_SEED = 20261204                        # the stored control's simulated picks
SETS = ("bks", "goat", "panel")              # drawn, and the deciding pool
AMPS = ("ac20", "pr12", "sw50r")             # BKS's rotation order inside a DI file
GOAT_PER_CELL = 9                            # GOAT units per fold and class
BKS_MIN_DIS, PANEL_MIN_DIS = 8, 3            # the draw refuses below these (the panel counted without BLEED_CHECK)
EXCLUDED = ("Silent Waves",)                 # panel DI titles never drawn (vocal bleed)
BLEED_CHECK = ("Drowning",)                  # drawn and rendered; read only on a recorded ear check before `pick`
MENU_TRIALS = 20                             # step-1 trials a menu, by level
MIN_TRIALS = 20                              # a part needs this many usable step-1 trials
FIXED = ("cen", "S", "label")                # menu positions 0, 1, 2
LABEL_INDEX = 2
MENU_N = len(FIXED) + MENU_TRIALS            # 23
POSITION_PER_SET = 4
OTHERS_PER_SOURCE = 8                        # a blur's other guitars: at most this many seeded sections a source
EXPOSURE = "-3"
STEM_ROWS = {"xlnoG": "xlnoG@-3", "xl": "xl@-3"}   # reference -> the ladder's stem row (its stored SI-SDR)
REFS = ("clean", "xlnoG", "xl")
MAIN_DRY = ("true", "avg+mild")
SINGLE_DRY = ("avg", "mild")
DRY = MAIN_DRY + SINGLE_DRY
ROWS = {                                     # row: (dry guitar, reference), in reading order
    "control": ("true", "clean"),
    "blurred": ("avg+mild", "clean"),
    "stem-alone": ("true", "xlnoG"),
    "stem-full": ("true", "xl"),
    "both-alone": ("avg+mild", "xlnoG"),
    "both-full": ("avg+mild", "xl")}
SINGLE_ROWS = {                              # read only after the trigger; the last four beside
    "avg-only": ("avg", "clean"),
    "mild-only": ("mild", "clean"),
    "avg-both-alone": ("avg", "xlnoG"),
    "avg-both-full": ("avg", "xl"),
    "mild-both-alone": ("mild", "xlnoG"),
    "mild-both-full": ("mild", "xl")}
REPEAT_TOL = 0.005                           # `knob_ceiling.REPEAT_TOL`: |ln(rendered / stored)| for a repeat
CONTROL_MAX = 0.02                           # no Control value beyond this
CONTROL_SHARE = 0.99                         # at least this share within REPEAT_TOL
ORDER_GAP = 0.01                             # the Control's pick must equal the stored one where the best two differ more
SI_SDR_TOL = 0.5                             # dB: a new stem against the ladder's stored SI-SDR (half A)
SMALL = 0.05                                 # the user's rule: no action rests on a gap under this
BIG = 0.10                                   # "passes": decided better with the mean at -0.10 or beyond
READINGS = ("passes", "fails", "undecided")
TRIGGER = ("fails", "undecided")             # the blurred DI's readings that trigger the single-blur rows
POWER_NOISE = (0.2, 0.4)                     # the stored control's simulated picks: noise SD on the search half
POWER_REPEATS = 40


# --- the menu (pure) -------------------------------------------------------------------------------------------------------

def finite_pos(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v > 0


def level_menu(ln_s, k=MENU_TRIALS):
    """(Pure.) MENU_RULE's trials: `k` levels evenly from the best (lowest) to the worst ln search-half judge; for each
    level from the best, the nearest trial not yet taken, a tie to the lower position. ln_s: the usable trials' ln
    search-half judges in trial order. -> positions into ln_s."""
    n = len(ln_s)
    if n < k:
        raise SystemExit(f"{n} usable trials, fewer than the menu's {k}")
    lo, hi = min(ln_s), max(ln_s)
    used = []
    for j in range(k):
        lv = lo + (hi - lo) * j / (k - 1)
        used.append(min((x for x in range(n) if x not in used), key=lambda x: (abs(ln_s[x] - lv), x)))
    return used


def part_refusal(n_usable, fixed_finite, min_trials=MIN_TRIALS):
    """(Pure.) Why a part can't be drawn, or None: fewer than `min_trials` usable step-1 trials, or Cen, S or the label
    without a finite stored judge on both halves (`fixed_finite`: {name: bool})."""
    if n_usable < min_trials:
        return f"{n_usable} usable step-1 trials (fewer than {min_trials})"
    bad = [k for k in FIXED if not fixed_finite.get(k)]
    return f"no finite stored judge on both halves for {', '.join(bad)}" if bad else None


def menu_of(fixed, trials, search, held):
    """(Pure.) A part's 23 settings in menu order: Cen, S, the label (`fixed`: {name: (select, settings, judge)}), then
    MENU_RULE's 20 step-1 trials. trials: [(trial index, settings, judge)] in trial order, already distinct; a trial is
    usable when its judge is finite on both halves. Reads search-half values and held-half finiteness only.
    -> [{kind, index, select, settings, stored_search}]."""
    ok = [t for t in trials if finite_pos((t[2] or {}).get(search)) and finite_pos((t[2] or {}).get(held))]
    why = part_refusal(len(ok), {k: finite_pos((v[2] or {}).get(search)) and finite_pos((v[2] or {}).get(held))
                                 for k, v in fixed.items()})
    if why:
        return None, why
    out = [{"kind": k, "index": 0, "select": fixed[k][0], "settings": fixed[k][1],
            "stored_search": float(fixed[k][2][search])} for k in FIXED]
    for p in level_menu([math.log(t[2][search]) for t in ok]):
        i, x, j = ok[p]
        out.append({"kind": "step1", "index": i, "select": fixed["label"][0], "settings": x,
                    "stored_search": float(j[search])})
    return out, None


# --- the draw (pure) -------------------------------------------------------------------------------------------------------

def draw_parts(cands, seed=SEED, goat_n=GOAT_PER_CELL, amps=AMPS):
    """(Pure.) The draw. cands: [{set, unit, amp, cluster, fold, cls, title, ok}] (ok: no `part_refusal`). BKS: every
    unit on one amp, inside each DI file (cluster) the units shuffled by the seed and the amps rotating from a seeded
    offset; a refused part is dropped and counted. Panel: every part but EXCLUDED's titles; a refused part dropped.
    GOAT: per fold and class `goat_n` parts, at most one a GOAT item (cluster) a fold, in seeded order; a refused part is
    passed over for the next. -> {"drawn": [(set, unit, amp)], "dropped": [...], "passed_over": n, "excluded": n}."""
    rng = random.Random(seed)
    by = {(c["set"], c["unit"], c["amp"]): c for c in cands}
    drawn, dropped, passed, excluded = [], [], 0, 0
    bydi = {}
    for c in cands:
        if c["set"] == "bks":
            bydi.setdefault(c["cluster"], set()).add(c["unit"])
    for di in sorted(bydi):
        us = sorted(bydi[di])
        rng.shuffle(us)
        off = rng.randrange(len(amps))
        for j, u in enumerate(us):
            k = ("bks", u, amps[(j + off) % len(amps)])
            c = by.get(k)
            if c is None or not c["ok"]:
                dropped.append({"part": list(k), "why": "no record" if c is None else "refused"})
            else:
                drawn.append(k)
    for c in sorted((c for c in cands if c["set"] == "panel"), key=lambda c: (c["unit"], c["amp"])):
        if c.get("title") in EXCLUDED:
            excluded += 1
        elif not c["ok"]:
            dropped.append({"part": ["panel", c["unit"], c["amp"]], "why": "refused"})
        else:
            drawn.append(("panel", c["unit"], c["amp"]))
    for f in sorted({c["fold"] for c in cands if c["set"] == "goat"}):
        g = sorted((c for c in cands if c["set"] == "goat" and c["fold"] == f), key=lambda c: (c["unit"], c["amp"]))
        rng.shuffle(g)
        used, got = set(), {"clean": 0, "crunch": 0}
        for c in g:
            if got.get(c["cls"], goat_n) < goat_n and c["cluster"] not in used:
                if not c["ok"]:
                    passed += 1
                    continue
                drawn.append(("goat", c["unit"], c["amp"]))
                used.add(c["cluster"])
                got[c["cls"]] += 1
    return {"drawn": drawn, "dropped": dropped, "passed_over": passed, "excluded": excluded}


def draw_shortfall(drawn, cands, goat_n=GOAT_PER_CELL):
    """(Pure.) Why the draw falls short, or []: a GOAT fold and class under `goat_n`, BKS under BKS_MIN_DIS DI files,
    the panel under PANEL_MIN_DIS DI files without BLEED_CHECK's titles."""
    by = {(c["set"], c["unit"], c["amp"]): c for c in cands}
    ps = [by[k] for k in drawn]
    out = []
    for f in sorted({c["fold"] for c in cands if c["set"] == "goat"}):
        for cls in ("clean", "crunch"):
            n = sum(p["set"] == "goat" and p["fold"] == f and p["cls"] == cls for p in ps)
            if n < goat_n:
                out.append(f"GOAT fold {f} {cls}: {n} of {goat_n}")
    nb = len({p["cluster"] for p in ps if p["set"] == "bks"})
    if nb < BKS_MIN_DIS:
        out.append(f"BKS: {nb} DI files of {BKS_MIN_DIS}")
    npn = len({p["cluster"] for p in ps if p["set"] == "panel" and p.get("title") not in BLEED_CHECK})
    if npn < PANEL_MIN_DIS:
        out.append(f"panel: {npn} DI files without {', '.join(BLEED_CHECK)}, of {PANEL_MIN_DIS}")
    return out


def position_parts(keys, seed=POSITION_SEED, per_set=POSITION_PER_SET):
    """(Pure.) The position check's parts: `per_set` a set, a seeded sample of the drawn parts (BLEED_CHECK's left to
    the main pass). keys: [(set, unit, amp, title)]. -> [(set, unit, amp)]."""
    rng = random.Random(seed)
    out = []
    for s in SETS:
        pool = sorted((k[0], k[1], k[2]) for k in keys if k[0] == s and k[3] not in BLEED_CHECK)
        out += sorted(rng.sample(pool, min(per_set, len(pool))))
    return out


# --- the picks and the part's numbers (pure) -------------------------------------------------------------------------------

def pick_index(d, skip=()):
    """(Pure.) The menu position with the smallest distance; a non-finite distance passed over, a tie to the lower
    position; positions in `skip` left out. None when no distance is finite."""
    best = None
    for j, x in enumerate(d):
        if j in skip or x is None or not math.isfinite(x):
            continue
        if best is None or x < d[best]:
            best = j
    return best


def part_numbers(d, h, label=LABEL_INDEX):
    """(Pure.) One part's numbers for one row. d: the row's search-half distances in menu order; h: the menu's stored
    held-half scores as ln(held / Cen's held) (h[0] = 0). G = h[pick]; the blind pick = the menu's mean; I = G - blind;
    `_nl` the same with the label out of both the pick and the blind mean. None without a pick."""
    p = pick_index(d)
    if p is None:
        return None
    q = pick_index(d, skip=(label,))
    rest = [v for j, v in enumerate(h) if j != label]
    blind, blind_nl = sum(h) / len(h), sum(rest) / len(rest)
    return {"pick": p, "G": h[p], "blind": blind, "I": h[p] - blind, "label_pick": p == label,
            "pick_nl": q, "G_nl": None if q is None else h[q], "blind_nl": blind_nl,
            "I_nl": None if q is None else h[q] - blind_nl, "best": min(h)}


def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    """(Pure.) Spearman's rank correlation on the pairs both finite (ties averaged); None under 3 pairs or no spread."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None and math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 3:
        return None
    ra, rb = _ranks([p[0] for p in pairs]), _ranks([p[1] for p in pairs])
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    va = sum((x - ma) ** 2 for x in ra)
    vb = sum((y - mb) ** 2 for y in rb)
    if va == 0 or vb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(va * vb)


# --- the readings and the table (pure) -------------------------------------------------------------------------------------

def number_reading(row, small=SMALL, big=BIG):
    """(Pure.) One number's reading: "passes" (the whole 90% interval below zero and the mean at -`big` or beyond),
    "fails" (the interval rules out a gain beyond -`small`: its lower end at -`small` or above), "undecided"; None
    without an interval."""
    if not row or row.get("lo90") is None or row.get("hi90") is None or row.get("mean") is None:
        return None
    if row["hi90"] < 0 and row["mean"] <= -big:
        return "passes"
    if row["lo90"] >= -small:
        return "fails"
    return "undecided"


def unreadable(row, small=SMALL):
    """(Pure.) The interval sits inside +-small: "not readable by the score"."""
    return bool(row) and row.get("lo90") is not None and row["lo90"] >= -small and row["hi90"] <= small


def row_reading(g, i):
    """(Pure.) A row from its two numbers (deciding-pool rows of G and I): "fails" when either fails, "passes" when both
    pass, else "undecided" (undecided is not failed). None when either has no interval."""
    rg, ri = number_reading(g), number_reading(i)
    if rg is None or ri is None:
        return None
    reading = "fails" if "fails" in (rg, ri) else "passes" if rg == ri == "passes" else "undecided"
    return {"reading": reading, "G": rg, "I": ri, "G_not_readable": unreadable(g), "I_not_readable": unreadable(i),
            "G_rules_out_gains_beyond": g.get("lo90"), "I_rules_out_gains_beyond": i.get("lo90")}


SECOND_STAGE = ("A pass is necessary, not sufficient: it says the degraded comparison ranks a true-DI search's "
                "candidates well, not that a search through it works. Before any product claim, a from-scratch search "
                "through the degraded inputs (the stem and the blurred dry guitar), scored on the held half against Cen")
R_CODES = {
    "R-dry": ("a dry guitar this degraded does not work: with the right notes and a perfect reference, the comparison "
              "through it does not pick a heard size better than Cen and a blind pick",
              "stop the route at this degradation; to the user. Not a verdict on a better dry guitar"),
    "R-stem": ("the stem is not a usable reference even alone",
               "stop. Separator work gets a preset-level yardstick with a known prize (the Control's I)"),
    "R-alone": ("it works where the target is the only or the dominant guitar",
                "continue, scoped to such windows; count how many songs offer them. " + SECOND_STAGE),
    "R-dry-only": ("only the dry guitar is missing",
                   "to the user. " + SECOND_STAGE + "; only then the second stage (a real note-matched dry guitar), "
                   "the exam's parts and a blind sitting"),
    "R-undecided": ("not decided",
                    "to the user, with each row's intervals, what each rules out and the share of the Control's I it "
                    "kept")}
R_TABLE = (                     # (dry guitar, stem alone, stem full mix): code; each of the 27 triples exactly once
    (("fails",), READINGS, READINGS, "R-dry"),
    (("passes",), ("fails",), READINGS, "R-stem"),
    (("passes",), ("passes",), ("fails",), "R-alone"),
    (("passes",), ("passes",), ("passes",), "R-dry-only"),
    (("undecided",), READINGS, READINGS, "R-undecided"),
    (("passes",), ("undecided",), READINGS, "R-undecided"),
    (("passes",), ("passes",), ("undecided",), "R-undecided"))


def table_guard():
    """Refuse unless R_TABLE holds every (dry guitar, stem alone, stem full mix) triple exactly once, with its five
    codes, and the thresholds are 0 < SMALL < BIG."""
    for d in READINGS:
        for a in READINGS:
            for f in READINGS:
                if sum(d in ds and a in as_ and f in fs for ds, as_, fs, _ in R_TABLE) != 1:
                    raise SystemExit(f"R_TABLE holds ({d}, {a}, {f}) not once")
    if {c for *_, c in R_TABLE} != set(R_CODES):
        raise SystemExit("R_TABLE's codes are not the five declared")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")
    if set(TRIGGER) != {"fails", "undecided"}:
        raise SystemExit("the singles' trigger is not the declared one")


def r_cell(dry, stem_alone, stem_full):
    """(Pure.) R_TABLE's row. -> (code, reading, next)."""
    table_guard()
    hit = [c for ds, as_, fs, c in R_TABLE if dry in ds and stem_alone in as_ and stem_full in fs]
    if len(hit) != 1:
        raise SystemExit(f"R_TABLE has {len(hit)} rows for ({dry}, {stem_alone}, {stem_full})")
    return (hit[0],) + R_CODES[hit[0]]


def dry_reading(blurred, avg=None, mild=None):
    """(Pure.) The dry-guitar column of R_TABLE. The blurred DI passing -> ("passes", "avg+mild"). Otherwise the
    single-blur rows decide once read: either passing -> ("passes", the one(s)); both failing -> ("fails", None); else
    ("undecided", None). Before they are read -> (None, "singles pending"). "avg+mild" names the combined blur only;
    passing singles are named "avg", "mild" or "avg, mild"."""
    if blurred == "passes":
        return "passes", "avg+mild"
    if avg is None or mild is None:
        return None, "singles pending"
    passing = [n for n, r in (("avg", avg), ("mild", mild)) if r == "passes"]
    if passing:
        return "passes", ", ".join(passing)
    if avg == mild == "fails":
        return "fails", None
    return "undecided", None


BOTH_OF = {"R-alone": ("both-alone",), "R-dry-only": ("both-alone", "both-full")}


def both_notes(code, readings, via="avg+mild"):
    """(Pure.) The Both rows' notes: for a cell that says continue, each matching Both row (through the dry guitar the
    cell rests on) that fails or reads undecided is said, and goes to the user before any second stage. readings:
    {row: reading}. -> [note]."""
    out = []
    names = [r for r in BOTH_OF.get(code, ())] if via == "avg+mild" else \
        [f"{v}-{r}" for v in via.split(", ") for r in BOTH_OF.get(code, ())]
    for name in names:
        got = readings.get(name)
        if got in ("fails", "undecided"):
            out.append(f"{name} reads {got}: the stem and the blurred dry guitar together "
                       f"{'do not keep a heard-size pick' if got == 'fails' else 'are not shown to keep one'} (the two "
                       "faults may compound). To the user before any second stage")
    return out


def outcome(readings, singles=None):
    """(Pure.) The read. readings: the main rows' {row: reading}; singles: the single-blur rows' {row: reading} or None.
    A Control that does not pass is reported (it is the stored order's reproduction, `control_check`, that gates the
    read). The blurred DI in TRIGGER and no singles -> the singles are triggered and no cell is read."""
    out = {"readings": dict(readings), "singles": dict(singles) if singles else None}
    missing = [n for n in ROWS if readings.get(n) not in READINGS] + \
        ([n for n in ("avg-only", "mild-only") if singles.get(n) not in READINGS] if singles is not None else [])
    if missing:
        out.update(code="incomplete", reading=f"no reading for {', '.join(missing)}", next="nothing is read")
        return out
    d, via = dry_reading(readings["blurred"], *((singles or {}).get(r) for r in ("avg-only", "mild-only")))
    out.update(dry_guitar=d, via=via)
    if d is None:
        out.update(code="singles-triggered", reading="the blurred DI reads " + readings["blurred"],
                   next="render the avg and mild dry guitars (two more dry guitars, 1 h 26 min to 2 h 46 min at the "
                        "ladder's rate), pick (phase_replay_picks_singles), then score --singles")
        return out
    code, reading, nxt = r_cell(d, readings["stem-alone"], readings["stem-full"])
    if via not in (None, "avg+mild"):
        reading += f" (the dry guitar through {via} alone; the combined blur did not pass)"
    out.update(code=code, reading=reading, next=nxt,
               both_notes=both_notes(code, {**readings, **(singles or {})}, via or "avg+mild"))
    return out


# --- the Control and the position check (pure) -----------------------------------------------------------------------------

def control_check(parts):
    """(Pure.) The rendered Control against the stored values. parts: {pkey: (rendered search-half distances, stored
    ones)} in menu order. Values: at least CONTROL_SHARE within REPEAT_TOL in ln, none beyond CONTROL_MAX (a
    non-finite render counts beyond). Order: the rendered pick equals the stored pick on every part whose stored best two
    differ by more than ORDER_GAP in ln. -> record with "ok"."""
    devs, beyond, mism, gated = [], [], [], 0
    for k, (r, s) in sorted(parts.items()):
        for j, (x, y) in enumerate(zip(r, s)):
            dv = abs(math.log(x / y)) if finite_pos(x) and finite_pos(y) else math.inf
            devs.append(dv)
            if dv > CONTROL_MAX:
                beyond.append({"part": k, "position": j, "ln_dev": None if math.isinf(dv) else dv})
        ss = sorted(math.log(y) for y in s)
        if len(ss) > 1 and ss[1] - ss[0] > ORDER_GAP:
            gated += 1
            if pick_index(r) != pick_index(s):
                mism.append({"part": k, "rendered": pick_index(r), "stored": pick_index(s)})
    n = len(devs)
    within = sum(d <= REPEAT_TOL for d in devs)
    ok = bool(n) and within >= CONTROL_SHARE * n and not beyond and not mism
    finite = [d for d in devs if math.isfinite(d)]
    return {"ok": ok, "values": n, "within_tol": within, "share_within": within / n if n else None,
            "beyond_max": beyond, "max_ln_dev": max(finite) if finite else None,
            "order_parts_gated": gated, "order_mismatches": mism}


def position_mode(devs, tol=REPEAT_TOL):
    """(Pure.) The main pass's render mode: "process" (one primed process a part and dry guitar, as the stored trials
    were made) when every position-check value is within `tol`, else "fresh" (each kept render primed alone)."""
    return "process" if devs and all(d is not None and d <= tol for d in devs) else "fresh"


def hash_refusal(entry, phase, sha):
    """(Pure.) Why a file may not be used, or None: the ledger entry's `phase` must hold its sha256."""
    rec = (entry or {}).get(phase)
    if not isinstance(rec, dict) or not rec.get("sha256"):
        return f"the ledger's {LEDGER_ID} entry has no {phase} sha256: record the file's hash first"
    if rec["sha256"] != sha:
        return f"the file's sha256 {sha[:12]} is not the ledger's {phase} {rec['sha256'][:12]}"
    return None


def bleed_included(bleed):
    """(Pure.) BLEED_CHECK's parts enter the rows only on a recorded ear check that heard no bleed."""
    return bool(bleed) and bleed.get("verdict") == "clean"


# --- paths, refusals ------------------------------------------------------------------------------------------------------

def fname(key):
    return key.replace("/", "__").replace(" ", "_")


def pkey(s, unit, amp):
    return f"{s}__{fname(unit + '|' + amp)}"


def ukey(s, unit):
    return f"{s}__{fname(unit)}"


def replay_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT


def draw_path():
    return replay_dir() / "draw.json"


def picks_path(singles=False):
    return replay_dir() / ("picks-singles.json" if singles else "picks.json")


def report_path(singles=False):
    return replay_dir() / ("report-singles.json" if singles else "report.json")


def dist_path(dry, k):
    return replay_dir() / "dist" / dry / f"{k}.json"


def blur_path(dry, k):
    return replay_dir() / "di" / dry / f"{k}.npy"


def stem_path(ref, uk):
    return replay_dir() / "stems" / ref / f"{uk}.npy"


def control_path(name):
    return replay_dir() / "controls" / f"{name}.json"


def file_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def ledger_entry():
    from learn import preset_ladder as L

    return L.ledger_entry()


def require(*keys):
    e = ledger_entry()
    for k in keys:
        if not e or k not in e:
            raise SystemExit(f"the ledger's {LEDGER_ID} entry has no {k}: declare it before running")
    return e


def require_hash(phase, path):
    e = require(PHASE, phase)
    why = hash_refusal(e, phase, file_sha(path))
    if why:
        raise SystemExit(why)
    return json.loads(pathlib.Path(path).read_text())


def require_draw():
    table_guard()
    if not draw_path().exists():
        raise SystemExit("no draw (run `draw` first)")
    return require_hash(PHASE_DRAW, draw_path())


def never_overwrite(path):
    if pathlib.Path(path).exists():
        raise SystemExit(f"{path} exists: never overwritten")


def separation_running(ps, own):
    """(Pure on its input.) Separation processes other than `own`: [pid]. ps: [(pid, command)]."""
    return [p for p, c in ps if p not in own and ("note_replay sep" in c or "preset_ladder sep" in c)]


def no_separation_beside():
    import os

    from learn import ks_extend as X

    got = separation_running(X._ps(), {os.getpid(), os.getppid()})
    if got:
        raise SystemExit(f"a separation is running ({got}): renders never run beside one")


# --- the stored data (reads files) ----------------------------------------------------------------------------------------

class Stored:
    """C3r's state, the search records, Cen's answers and judges, S, and the read units, keyed by (set, unit, amp)."""

    def __init__(self):
        from learn import full_controls_c3r as R
        from learn import pipeline_fix as P
        from learn import preset_ladder as L

        self.st = R.state()
        self.units = {(ru["set"], ru["unit"], ru["amp"]): ru for ru in R.read_units(self.st) if ru["set"] in SETS}
        self.outs = {**self.st["c2"]["outputs"], **self.st["c2r"]["outputs"]}
        self.recs = {(r["unit"], r["amp"]): r for d in (self.st["c2"], self.st["c2r"]) for r in d["records"]}
        self.cen_ans = json.loads(L.answers_path("cen").read_text())
        self.cen_v = L.val_row("cen")
        self.ms = P.A_menu_S()
        self._s = {}

    def output(self, k):
        r = self.recs.get((k[1], k[2]))
        return None if r is None else self.outs.get(r["key"])

    def s_judge(self, k):
        from learn import full_controls_c3r as R

        if k not in self._s:
            self._s[k] = R.s_judges(self.st, self.units[k])
        return self._s[k]

    def cen_judge(self, k):
        ru = self.units[k]
        return {h: self.cen_v(ru, h, h) for h in ("A", "B")}

    def fixed(self, k):
        """{name: (select, settings "module/key", judge {A, B})} for Cen, S and the label."""
        from learn import local_objective as LO
        from learn import pipeline_fix as P

        ru, o = self.units[k], self.output(k)
        c = self.cen_ans["answers"][k[0]][f"{k[1]}|{k[2]}"][P.ANY_HALF]
        sel, S = self.ms[k[2]][ru["prt"]["cls"]]
        lab = ((o.get("fresh") or {}).get("label") or {}).get("judge")
        return {"cen": (c["select"], c["settings"], self.cen_judge(k)),
                "S": (sel, LO.sdict(dict(S)), self.s_judge(k)),
                "label": (sel, o["label"], lab)}

    def trials(self, k):
        """[(trial index, settings, judge)]: the record's distinct step-1 trials (`learnable_targets.candidates`)."""
        from learn import learnable_targets as LT

        return [(i, x, j) for kind, i, x, j in LT.candidates(self.output(k)) if kind == "step1"]

    def held(self, k, menu):
        """The menu's stored held-half judges, in menu order (only `score` and the stored control call this)."""
        o = self.output(k)
        he = o["held"]
        fx = self.fixed(k)
        out = []
        for m in menu:
            if m["kind"] == "step1":
                out.append(o["step1"]["trials"][m["index"]]["judge"][he])
            else:
                out.append(fx[m["kind"]][2][he])
        return out


def h_of(held):
    """ln(held / Cen's held) in menu order (Cen first)."""
    return [math.log(v / held[0]) for v in held]


def lender_band():
    from learn import preset_ladder as L

    return {u: v["band"] for u, v in L.lends()["units"].items()}


def rows_by_set(parts, values):
    """{set: [(cluster, unit|amp, value, search half)]} for `summarise`. values: {pkey: value or None}."""
    from learn import preset_ladder as L

    out = {s: [] for s in L.SETS}
    for p in parts:
        v = values.get(p["pkey"])
        if v is not None:
            out[p["set"]].append((p["cluster"], f"{p['unit']}|{p['amp']}", v, p["search"]))
    return out


def summary(st_units, parts, values, band):
    """`preset_ladder.summarise` on the parts, with each deciding set's leave-one-cluster-out range."""
    from learn import preset_ladder as L

    units = [st_units[(p["set"], p["unit"], p["amp"])] for p in parts]
    got = rows_by_set(parts, values)
    row = L.summarise(got, units, band)
    row["leave_one_cluster_out"] = {s: L.loo_range(got, units, s) for s in row["deciding_sets"]}
    row["parts_read"] = sum(len(v) for v in got.values())
    return row


# --- draw ------------------------------------------------------------------------------------------------------------------

def cmd_draw(_args):
    """The draw (zero renders, no held-half value read): every candidate part's menu and refusal, `draw_parts`, the
    position check's parts; saved, its sha256 printed for the ledger; then the stored control. -> PF/replay/draw.json,
    stored-control.json."""
    from learn import half_data as HD
    from learn import pipeline_fix as P

    require(PHASE)
    table_guard()
    never_overwrite(draw_path())
    sd = Stored()
    cands, menus = [], {}
    for k, ru in sorted(sd.units.items()):
        o = sd.output(k)
        title = HD.title_of(ru)
        if o is None or not (o.get("step1") or {}).get("trials") or o.get("search") not in ("A", "B"):
            cands.append({"set": k[0], "unit": k[1], "amp": k[2], "cluster": ru["cluster"], "fold": ru["fold"],
                          "cls": ru["prt"]["cls"], "title": title, "ok": False, "why": "no search record"})
            continue
        menu, why = menu_of(sd.fixed(k), sd.trials(k), o["search"], o["held"])
        cands.append({"set": k[0], "unit": k[1], "amp": k[2], "cluster": ru["cluster"], "fold": ru["fold"],
                      "cls": ru["prt"]["cls"], "title": title, "ok": why is None, "why": why})
        menus[k] = menu
    res = draw_parts(cands)
    short = draw_shortfall(res["drawn"], cands)
    if short:
        raise SystemExit("the draw falls short: " + "; ".join(short))
    by = {(c["set"], c["unit"], c["amp"]): c for c in cands}
    parts = []
    for k in res["drawn"]:
        ru, o, c = sd.units[k], sd.output(k), by[k]
        parts.append({"pkey": pkey(*k), "ukey": ukey(k[0], k[1]), "set": k[0], "unit": k[1], "amp": k[2],
                      "cluster": ru["cluster"], "fold": ru["fold"], "cls": c["cls"], "title": c["title"],
                      "source": ru["prt"]["band"], "section": ru["prt"]["section"], "lag": ru["lag"],
                      "record_lag": o.get("lag"), "search": o["search"], "held": o["held"],
                      "record": sd.recs[(k[1], k[2])]["key"], "menu": menus[k]})
    pos = position_parts([(p["set"], p["unit"], p["amp"], p["title"]) for p in parts])
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "seed": SEED, "c3r_sha256": sd.st["sha256"],
           "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "counts": {s: {"parts": sum(p["set"] == s for p in parts),
                          "clusters": len({p["cluster"] for p in parts if p["set"] == s})} for s in SETS},
           "dropped": res["dropped"], "passed_over": res["passed_over"], "excluded": res["excluded"],
           "refused": sorted(f"{c['set']}|{c['unit']}|{c['amp']}: {c['why']}" for c in cands if not c["ok"]),
           "bleed_check": [p["pkey"] for p in parts if p["title"] in BLEED_CHECK],
           "position_parts": [pkey(*k) for k in pos], "parts": parts}
    P.save(draw_path(), out)
    print(f"DRAW: {len(parts)} parts {out['counts']}; dropped {len(res['dropped'])}, passed over {res['passed_over']}; "
          f"sha256 {file_sha(draw_path())} (into the ledger as {PHASE_DRAW} before anything else)")
    stored_control(sd, out)


def _power(sd_parts, noise, seed=POWER_SEED, repeats=POWER_REPEATS):
    """Simulated picks on the stored scores: the stored search-half values plus Gaussian noise of SD `noise` in ln
    (None: a blind pick, a seeded random menu position). -> [(pooled G, pooled I)] per repeat."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    out = []
    for rep in range(repeats):
        rng = random.Random(f"{seed}|{noise}|{rep}")
        rows = {"G": {s: [] for s in SETS}, "I": {s: [] for s in SETS}}
        for p, s, h in sd_parts:
            if noise is None:                          # a blind pick: a seeded menu position
                g = h[rng.randrange(len(h))]
            else:
                d = [math.log(x) + rng.gauss(0.0, noise) for x in s]
                g = h[pick_index(d)]
            rows["G"][p["set"]].append((p["cluster"], p["pkey"], g))
            rows["I"][p["set"]].append((p["cluster"], p["pkey"], g - sum(h) / len(h)))
        got = []
        for q in ("G", "I"):
            got.append(R.pooled({s: P.clustered(rows[q][s]) for s in SETS}))
        out.append(tuple(got))
    return out


def stored_control(sd, draw):
    """The Control from stored scores alone (what the rendered Control must reproduce): per part the stored pick, G, I,
    the blind pick, the best menu setting and the label-free numbers; the rows with and without BLEED_CHECK's parts; the
    simulated picks' power. -> PF/replay/stored-control.json."""
    from learn import pipeline_fix as P

    p_ = control_path("stored")
    never_overwrite(p_)
    band = lender_band()
    per, sim = {}, []
    for p in draw["parts"]:
        k = (p["set"], p["unit"], p["amp"])
        h = h_of(sd.held(k, p["menu"]))
        s = [m["stored_search"] for m in p["menu"]]
        per[p["pkey"]] = part_numbers(s, h)
        if p["title"] not in BLEED_CHECK:
            sim.append((p, s, h))
    out = {"plan": PLAN, "draw_sha256": file_sha(draw_path()), "parts": per, "rows": {}}
    for name, keep in (("without_bleed_check", lambda p: p["title"] not in BLEED_CHECK), ("every_part", lambda p: True)):
        ps = [p for p in draw["parts"] if keep(p)]
        out["rows"][name] = {q: summary(sd.units, ps, {k: (v or {}).get(q) for k, v in per.items()}, band)
                             for q in ("G", "I", "G_nl", "I_nl", "blind", "best")}
        out["rows"][name]["label_share"] = sum(per[p["pkey"]]["label_pick"] for p in ps) / len(ps)
    out["power"] = {}
    for noise in POWER_NOISE + (None,):
        reps = _power(sd_parts=sim, noise=noise)
        out["power"]["blind" if noise is None else f"noise {noise}"] = {
            q: {"mean": sum(r[j]["mean"] for r in reps) / len(reps),
                "half_width": sum((r[j]["hi90"] - r[j]["lo90"]) / 2 for r in reps) / len(reps)}
            for j, q in enumerate(("G", "I"))}
    P.save(p_, out)
    r = out["rows"]["without_bleed_check"]
    for q in ("G", "I", "G_nl", "I_nl"):
        dp = r[q]["deciding_pool"] or {}
        print(f"stored control {q}: {dp.get('mean')} [{dp.get('lo90')}, {dp.get('hi90')}]")
    print(f"stored control: label picked on {r['label_share']:.2f} of parts; power {json.dumps(out['power'])}")


# --- the blurred DIs (CPU) -------------------------------------------------------------------------------------------------

def others_for(part, parts, seed=BLUR_SEED, per=OTHERS_PER_SOURCE):
    """(Pure.) A part's other guitars: from every source but its own, at most `per` of the drawn parts' distinct DI
    sections, a seeded sample of each source's sorted sections. parts: the draw's. -> {source: [section]}."""
    secs = {}
    for p in parts:
        if p["source"] != part["source"]:
            secs.setdefault(p["source"], set()).add(p["section"])
    out = {}
    for s in sorted(secs):
        pool = sorted(secs[s])
        rng = random.Random(f"{seed}|others|{part['pkey']}|{s}")
        out[s] = sorted(rng.sample(pool, min(per, len(pool))))
    return out


def di_section(prt):
    import numpy as np

    from learn import pretrain_set as PS
    from learn import song_bank as B

    return B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)


def cmd_blur(_args):
    """The dry guitars (CPU, zero renders): per drawn part `di_robustness`'s average_balance and degrade("mild"), code
    unchanged, on the true DI section as rendered: avg+mild (the blurred DI), avg and mild alone (the conditional
    rows), the mild draws seeded per part and shared by mild and avg+mild. -> PF/replay/di/<dry>/, blur.json."""
    import numpy as np

    from learn import di_robustness as DR
    from learn import pipeline_fix as P

    draw = require_draw()
    rec_p = replay_dir() / "blur.json"
    never_overwrite(rec_p)
    sd = Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    by_sec = {}
    for p in draw["parts"]:
        by_sec.setdefault(p["section"], sd.units[(p["set"], p["unit"], p["amp"])]["prt"])
    cache = {}

    def sec(s):
        if s not in cache:
            cache[s] = np.asarray(di_section(by_sec[s]), np.float64)
        return cache[s]
    spec, orig = {}, DR.smoothed_spectrum

    def cached(x):                                 # the same function, its value memoised by the audio's bytes
        key = hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
        if key not in spec:
            spec[key] = orig(x)
        return spec[key]
    DR.smoothed_spectrum = cached
    out, t0 = {"plan": PLAN, "draw_sha256": file_sha(draw_path()), "parts": {}}, time.time()
    try:
        for n, p in enumerate(draw["parts"]):
            di = sec(p["section"])
            oth_s = others_for(p, draw["parts"])
            others = {s: [sec(x) for x in xs] for s, xs in oth_s.items()}
            ys = {"avg": DR.average_balance(di, others)}
            ys["avg+mild"] = DR.degrade("mild", p["pkey"], ys["avg"], others, random.Random(f"{BLUR_SEED}|mild|"
                                                                                            f"{p['pkey']}"))
            ys["mild"] = DR.degrade("mild", p["pkey"], di, others, random.Random(f"{BLUR_SEED}|mild|{p['pkey']}"))
            rec = {"others": oth_s, "sha256": {}}
            for dry, y in ys.items():
                y32 = np.asarray(y, np.float32)
                if len(y32) != len(di) or not np.isfinite(y32).all():
                    raise SystemExit(f"{p['pkey']}: a bad {dry} dry guitar")
                path = blur_path(dry, p["pkey"])
                path.parent.mkdir(parents=True, exist_ok=True)
                np.save(path, y32)
                rec["sha256"][dry] = file_sha(path)
            out["parts"][p["pkey"]] = rec
            if n % 20 == 0:
                print(f"blur {n + 1}/{len(draw['parts'])}: {(time.time() - t0) / (n + 1):.1f} s each", flush=True)
    finally:
        DR.smoothed_spectrum = orig
    P.save(rec_p, out)
    print(f"BLUR DONE: {len(out['parts'])} parts x 3 dry guitars, {time.time() - t0:.0f} s")


def load_dry(dry, p, di32, blur_rec):
    import numpy as np

    if dry == "true":
        return di32
    path = blur_path(dry, p["pkey"])
    if file_sha(path) != blur_rec["parts"][p["pkey"]]["sha256"][dry]:
        raise SystemExit(f"{path}: not the blurred DI `blur` wrote")
    return np.load(path).astype(np.float32)


# --- the stems (msst-venv) ------------------------------------------------------------------------------------------------

def cmd_sep(args):
    """The stems (msst-venv, never beside a render): each drawn unit's lender mixes at -3 rebuilt (`lender_mix`), their
    features required equal to the ladder's stored `mix@-3` and `full@-3` builds (`rebuild_refusal`), X-LANCE on noG's
    mid (xlnoG) and full's mid (xl); each stem's SI-SDR on half A within SI_SDR_TOL of the ladder's stored value, or the
    stage stops. -> PF/replay/stems/<ref>/<unit>.npy and .json."""
    import argparse as AP
    import os

    import numpy as np

    from learn import cc_build as CB
    from learn import direct_stems as DS
    from learn import ks_extend as X
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import preset_ladder as L
    from learn import pretrain_set as PS
    from learn import real_mix_test as RMT
    from learn import sep_s0 as S0
    from learn import trusted_data as T

    draw = require_draw()
    why = L.sep_blockers(X._ps(), {os.getpid(), os.getppid()}, LO.others_rendering,
                         RMT.mps_users if args.device == "mps" else None)
    if why:
        raise SystemExit("not now: " + "; ".join(why))
    sd = Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    sep = DS.stem_separator(T.SEP, args.device)
    e = P.require("phase_dfix")
    croot, kept, rend, _, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    ctx = CB.ctx_for(AP.Namespace(out=None, smoke=False))
    ld = L.lends()["units"]
    seen, todo = set(), []
    for p in draw["parts"]:
        if p["ukey"] not in seen:
            seen.add(p["ukey"])
            todo.append(p)
    todo.sort(key=lambda p: (ld[p["unit"]]["section"], p["unit"]))
    h = PS.half_slices()["A"]
    cache, t0, done = {}, time.time(), 0
    for p in todo:
        if all(stem_path(r, p["ukey"]).exists() for r in STEM_ROWS):
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        ru = sd.units[(p["set"], p["unit"], p["amp"])]
        prt = ru["prt"]
        ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        mixes, _ = L.lender_mix(ctx, croot, kept, rend, cache, ref, dict(ld[p["unit"]], unit=p["unit"]), EXPOSURE,
                                PS.SR)
        bad = L.rebuild_refusal(mixes, {k_: L.load_feats(f"{w}@{EXPOSURE}", ru) for k_, w in (("full", "full"),
                                                                                             ("noG", "mix"))})
        if bad:
            raise SystemExit(f"{p['unit']}: {bad}: the separations stop")
        for r, row in STEM_ROWS.items():
            path = stem_path(r, p["ukey"])
            if path.exists():
                continue
            m = mixes["noG" if r == "xlnoG" else "full"]
            md = (m["L"] + m["R"]) / 2
            stem = np.asarray(sep(md), np.float64)
            if len(stem) != len(md) or not np.isfinite(stem).all():
                raise SystemExit(f"{p['unit']}: a bad stem ({r})")
            si = S0.si_sdr(stem[h], m["target"][h])
            stored = json.loads((L.ladder_dir() / "seps" / row / f"{p['set']}__{L.fname(p['unit'])}.json")
                                .read_text())["si_sdr_A"]
            if abs(si - stored) > SI_SDR_TOL:
                raise SystemExit(f"{p['unit']} ({r}): SI-SDR {si:.2f} dB against the ladder's {stored:.2f}: the "
                                 "separations stop")
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, stem.astype(np.float32))
            P.save(path.with_suffix(".json"), {"unit": p["unit"], "ref": r, "row": row, "rebuilt_features_equal": True,
                                               "si_sdr_A": si, "stored_si_sdr_A": stored, "n": len(stem),
                                               "sha256": file_sha(path)})
            done += 1
        print(f"sep: {done} stems, {(time.time() - t0) / max(1, done):.1f} s each", flush=True)
    print(f"REPLAY-SEP DONE: {done} stems in {time.time() - t0:.0f} s")


def load_stem(ref, p):
    import numpy as np

    path = stem_path(ref, p["ukey"])
    rec = json.loads(path.with_suffix(".json").read_text())
    if rec["sha256"] != file_sha(path):
        raise SystemExit(f"{path}: not the stem `sep` wrote")
    return np.load(path).astype(np.float64)


# --- the renders ----------------------------------------------------------------------------------------------------------

def half_distance(ref, y, di, lag, half):
    """J0 on one half only (`knob_ceiling.judge`'s call for that half; a refusal is the worst)."""
    from analysis.aligned import aligned_distance

    from learn import knob_ceiling as K

    a, b = K.R.HALVES[half]
    x = aligned_distance(ref, y, di, lag=lag, render_latency=K.P.LATENCY, start_s=a, end_s=b).distance
    return math.inf if x is None else x


def render_menu(di32, menu, mode):
    """The menu's 23 renders, trimmed, in menu order: one primed process (`process`: Cen's priming render discarded)
    or each primed alone (`fresh_render`). -> ([y], renders used)."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    form = [(m["select"], LO.tdict(LO.sdict(LO.tdict(m["settings"])))) for m in menu]
    ys = []
    if mode == "process":
        rr = CB.new_renderer()
        try:
            rr.render(di32, form[0][0], form[0][1])
            for sel, s_ in form:
                ys.append(np.asarray(rr.render(di32, sel, s_), np.float64)[trim[0]:trim[1]])
        finally:
            rr.close()
        return ys, 1 + len(form)
    for sel, s_ in form:
        ys.append(np.asarray(AM.fresh_render(CB.new_renderer, di32, sel, s_, s_), np.float64)[trim[0]:trim[1]])
    return ys, 2 * len(form)


def part_audio(sd, p):
    """(di32, the clean record, the trimmed true DI) for a drawn part."""
    import numpy as np

    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
    di32 = di_section(prt)
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    return di32, P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), trim


def cmd_position(_args):
    """The position check (renders): POSITION_PER_SET seeded parts a set, the true DI, each part's 23 settings in one
    primed process, each search-half distance against its stored value; every one within REPEAT_TOL -> the main pass
    renders a part and dry guitar in one primed process, else each kept render primed alone. The render rate is timed
    here. -> PF/replay/controls/position.json."""
    import numpy as np

    from learn import local_objective as LO
    from learn import pipeline_fix as P

    draw = require_draw()
    p_ = control_path("position")
    never_overwrite(p_)
    no_separation_beside()
    sd = Stored()
    LO._wait_cap()
    by = {p["pkey"]: p for p in draw["parts"]}
    devs, rows, renders, t0 = [], [], 0, time.time()
    for k in draw["position_parts"]:
        p = by[k]
        di32, ref, trim = part_audio(sd, p)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ys, used = render_menu(di32, p["menu"], "process")
        renders += used
        d = [half_distance(ref, y, di, p["lag"], p["search"]) for y in ys]
        dv = [abs(math.log(x / m["stored_search"])) if finite_pos(x) else None for x, m in zip(d, p["menu"])]
        devs += dv
        rows.append({"part": k, "distances": d, "ln_dev": dv})
        print(f"position {len(rows)}/{len(draw['position_parts'])}: max dev "
              f"{max((v for v in dv if v is not None), default=None)}", flush=True)
    secs = time.time() - t0
    mode = position_mode(devs)
    P.save(p_, {"plan": PLAN, "draw_sha256": file_sha(draw_path()), "mode": mode, "renders": renders, "seconds": secs,
                "renders_per_hour_one_process": renders / secs * 3600, "values": len(devs),
                "within_tol": sum(d is not None and d <= REPEAT_TOL for d in devs),
                "max_ln_dev": max((d for d in devs if d is not None), default=None), "parts": rows})
    print(f"POSITION: mode {mode}; {renders} renders in {secs:.0f} s ({renders / secs * 3600:.0f} an hour, one process)")


def cmd_render(args):
    """One shard's renders: each part and dry guitar's 23 settings (the position check's mode), each kept render's
    search-half distance against the clean record and both stems (no held-half distance, no audio kept); on the
    position check's parts, the true DI's stem lag re-estimated beside. The single-blur dry guitars only after `score`
    triggered them. -> PF/replay/dist/<dry>/<part>.json."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    draw = require_draw()
    drys = [d.strip() for d in args.dry.split(",")]
    if any(d not in DRY for d in drys):
        raise SystemExit(f"--dry takes {', '.join(DRY)}")
    if any(d in SINGLE_DRY for d in drys):
        rp = report_path()
        if not rp.exists() or (json.loads(rp.read_text()).get("outcome") or {}).get("code") != "singles-triggered":
            raise SystemExit("the single-blur dry guitars render only after `score` triggered them")
    pos = control_path("position")
    if not pos.exists():
        raise SystemExit("run the position check first")
    mode = json.loads(pos.read_text())["mode"]
    blur_rec = json.loads((replay_dir() / "blur.json").read_text())
    if blur_rec["draw_sha256"] != file_sha(draw_path()):
        raise SystemExit("blur.json was made from another draw")
    no_separation_beside()
    sd = Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    k, n = args.shard
    mine = [p for j, p in enumerate(sorted(draw["parts"], key=lambda p: p["pkey"])) if j % n == k]
    relag = set(draw["position_parts"])
    LO._wait_cap()
    renders, t0 = 0, time.time()
    for p in mine:
        todo = [d for d in drys if not dist_path(d, p["pkey"]).exists()]
        if not todo:
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        di32, clean, trim = part_audio(sd, p)
        refs = {"clean": clean, **{r: load_stem(r, p) for r in STEM_ROWS}}
        for dry in todo:
            t1 = time.time()
            x32 = load_dry(dry, p, di32, blur_rec)
            dj = np.asarray(x32, np.float64)[trim[0]:trim[1]]
            ys, used = render_menu(x32, p["menu"], mode)
            renders += used
            rec = {"plan": PLAN, "part": p["pkey"], "dry": dry, "mode": mode, "lag": p["lag"], "search": p["search"],
                   "menu_sha256": hashlib.sha256(json.dumps(p["menu"], sort_keys=True).encode()).hexdigest(),
                   "distances": {r: [half_distance(refs[r], y, dj, p["lag"], p["search"]) for y in ys] for r in REFS},
                   "render_sha256": [AM.audio_sha(y) for y in ys], "renders": used}
            if dry == "true" and p["pkey"] in relag:      # beside: the stem's own lag, from Cen, S and the label
                from analysis.aligned import estimate_lag

                rec["relag"] = {}
                for r in STEM_ROWS:
                    try:
                        lg = int(estimate_lag(refs[r], ys[:3], hint=p["lag"]))
                        rec["relag"][r] = {"lag": lg, "distances": [half_distance(refs[r], y, dj, lg, p["search"])
                                                                    for y in ys]}
                    except ValueError as err:
                        rec["relag"][r] = {"lag": None, "why": str(err)}
            rec["seconds"] = time.time() - t1
            P.save(dist_path(dry, p["pkey"]), rec)
        print(f"{p['pkey'][-60:]}: renders so far {renders}, {time.time() - t0:.0f} s", flush=True)
    print(f"REPLAY-RENDER DONE {k}/{n}: {renders} renders in {time.time() - t0:.0f} s")


def load_dist(dry, p):
    path = dist_path(dry, p["pkey"])
    if not path.exists():
        return None
    rec = json.loads(path.read_text())
    if rec["menu_sha256"] != hashlib.sha256(json.dumps(p["menu"], sort_keys=True).encode()).hexdigest():
        raise SystemExit(f"{path}: rendered from another menu")
    return rec


# --- the Control (zero renders) -------------------------------------------------------------------------------------------

def cmd_control(_args):
    """The Control's check (zero renders) on every part's true-DI renders against the clean record (`control_check`). A
    failure stops the replay: no row is read, and any way on is an amendment. -> PF/replay/controls/control.json."""
    from learn import pipeline_fix as P

    draw = require_draw()
    p_ = control_path("control")
    never_overwrite(p_)
    parts = {}
    for p in draw["parts"]:
        rec = load_dist("true", p)
        if rec is None:
            raise SystemExit(f"{p['pkey']}: not rendered")
        parts[p["pkey"]] = (rec["distances"]["clean"], [m["stored_search"] for m in p["menu"]])
    got = control_check(parts)
    got.update(plan=PLAN, draw_sha256=file_sha(draw_path()), time=time.strftime("%Y-%m-%d %H:%M:%S"))
    P.save(p_, got)
    print(f"CONTROL {'OK' if got['ok'] else 'FAILED'}: {got['within_tol']} of {got['values']} within {REPEAT_TOL}, "
          f"{len(got['beyond_max'])} beyond {CONTROL_MAX}, {len(got['order_mismatches'])} order mismatches")
    if not got["ok"]:
        raise SystemExit("the Control failed: the replay stops (no row is read; any way on is an amendment)")


def require_control():
    p_ = control_path("control")
    if not p_.exists() or not json.loads(p_.read_text()).get("ok"):
        raise SystemExit("the Control has not passed: nothing is picked or read")


# --- the bleed check, the picks (distances only) --------------------------------------------------------------------------

def cmd_bleed(args):
    """Records the user's ear check of BLEED_CHECK's amp-track sections (clean: no vocal bleed heard; bleed), before
    `pick`; refused once the picks exist. -> PF/replay/bleed.json."""
    from learn import pipeline_fix as P

    require_draw()
    if picks_path().exists():
        raise SystemExit("the picks exist: the bleed check comes before `pick`")
    p_ = replay_dir() / "bleed.json"
    never_overwrite(p_)
    P.save(p_, {"verdict": args.verdict, "by": args.by, "titles": list(BLEED_CHECK),
                "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"BLEED CHECK recorded: {args.verdict}")


def cmd_pick(args):
    """The picks (zero renders; distances only, no held-half value): per row and part the menu position with the
    smallest search-half distance, with and without the label; BLEED_CHECK's parts in only on a recorded clean ear
    check. -> PF/replay/picks.json (or picks-singles.json); its sha256 goes into the ledger before `score`."""
    from learn import pipeline_fix as P

    draw = require_draw()
    require_control()
    singles = bool(args.singles)
    p_ = picks_path(singles)
    never_overwrite(p_)
    if singles:
        main = require_hash(PHASE_PICKS, picks_path())
        rp = report_path()
        if not rp.exists() or json.loads(rp.read_text())["outcome"]["code"] != "singles-triggered":
            raise SystemExit("the singles were not triggered")
        included = main["included"]
        rows = SINGLE_ROWS
    else:
        bp = replay_dir() / "bleed.json"
        bleed = json.loads(bp.read_text()) if bp.exists() else None
        included = [p["pkey"] for p in draw["parts"] if p["title"] not in BLEED_CHECK or bleed_included(bleed)]
        rows = ROWS
    by = {p["pkey"]: p for p in draw["parts"]}
    out = {"plan": PLAN, "draw_sha256": file_sha(draw_path()), "included": included,
           "left_out": sorted(set(by) - set(included)), "rows": {}, "dist_sha256": {},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not singles:
        out["bleed_check"] = json.loads((replay_dir() / "bleed.json").read_text()) \
            if (replay_dir() / "bleed.json").exists() else None
    for k in included:
        for dry in sorted({d for d, _ in rows.values()}):
            rec = load_dist(dry, by[k])
            if rec is None:
                raise SystemExit(f"{k}: no {dry} renders")
            out["dist_sha256"][f"{dry}/{k}"] = file_sha(dist_path(dry, k))
    for name, (dry, ref) in rows.items():
        out["rows"][name] = {}
        for k in included:
            d = load_dist(dry, by[k])["distances"][ref]
            out["rows"][name][k] = {"pick": pick_index(d), "pick_nl": pick_index(d, skip=(LABEL_INDEX,))}
    P.save(p_, out)
    print(f"PICKS ({'singles' if singles else 'main'}): {len(included)} parts, left out {out['left_out']}; sha256 "
          f"{file_sha(p_)} (into the ledger as {PHASE_PICKS2 if singles else PHASE_PICKS} before `score`)")


# --- the score (the only step that loads held-half values) ----------------------------------------------------------------

def read_rows(sd, draw, picks, rows):
    """Per row: the parts' numbers from the hashed picks and the stored held-half scores, the rows (`summary`) of G, I
    and their label-free forms, the label's share, the share of picks equal to the Control's, the within-part rank
    correlation of the row's search-half distances with the true ones, and each set's mean of it."""
    by = {p["pkey"]: p for p in draw["parts"]}
    parts = [by[k] for k in picks["included"]]
    band = lender_band()
    hs = {p["pkey"]: h_of(sd.held((p["set"], p["unit"], p["amp"]), p["menu"])) for p in parts}
    true_d = {p["pkey"]: load_dist("true", p)["distances"]["clean"] for p in parts}
    ctl = {}
    if "control" not in rows:
        main = json.loads(picks_path().read_text())
        ctl = {k: v["pick"] for k, v in main["rows"]["control"].items()}
    out = {}
    for name, (dry, ref) in rows.items():
        per = {}
        for p in parts:
            k = p["pkey"]
            d = load_dist(dry, p)["distances"][ref]
            num = part_numbers(d, hs[k])
            if num is not None and (num["pick"] != picks["rows"][name][k]["pick"]
                                    or num["pick_nl"] != picks["rows"][name][k]["pick_nl"]):
                raise SystemExit(f"{name} {k}: the distances' pick is not the hashed pick")
            if num is not None:
                truth = [m["stored_search"] for m in p["menu"]] if name == "control" else true_d[k]
                num["spearman_vs_true"] = spearman(d, truth)
            per[k] = num
        ctl_pick = {k: v["pick"] for k, v in picks["rows"]["control"].items()} if "control" in picks["rows"] else ctl
        got = {"parts": per}
        for q in ("G", "I", "G_nl", "I_nl"):
            got[q] = summary(sd.units, parts, {k: (v or {}).get(q) for k, v in per.items()}, band)
        ok = [v for v in per.values() if v is not None]
        got["label_share"] = sum(v["label_pick"] for v in ok) / len(ok) if ok else None
        got["picks_equal_control"] = sum(per[k] is not None and per[k]["pick"] == ctl_pick.get(k)
                                         for k in per) / len(per)
        rh = [v["spearman_vs_true"] for v in ok if v.get("spearman_vs_true") is not None]
        got["spearman_vs_true"] = {"mean": sum(rh) / len(rh) if rh else None,
                                   **{s: (lambda xs: sum(xs) / len(xs) if xs else None)(
                                       [per[p["pkey"]]["spearman_vs_true"] for p in parts if p["set"] == s
                                        and per[p["pkey"]] and per[p["pkey"]].get("spearman_vs_true") is not None])
                                      for s in SETS}}
        got["no_pick"] = sorted(k for k, v in per.items() if v is None)
        out[name] = got
    return out


def relag_read(draw, picks):
    """Beside: on the position check's parts, the stem rows' picks at the stored lag and at the stem's own lag."""
    by = {p["pkey"]: p for p in draw["parts"]}
    out = {}
    for k in draw["position_parts"]:
        if k not in picks["included"]:
            continue
        rec = load_dist("true", by[k])
        for r, x in (rec.get("relag") or {}).items():
            if x.get("lag") is None:
                out.setdefault(r, []).append({"part": k, "lag": None})
                continue
            out.setdefault(r, []).append({"part": k, "stored_lag": by[k]["lag"], "lag": x["lag"],
                                          "same_pick": pick_index(x["distances"]) == pick_index(rec["distances"][r])})
    return out


def cmd_score(args):
    """The read (zero renders), once: refused unless the picks' sha256 is the ledger's. The rows are saved before the
    outcome is read; the outcome is `outcome` (the main rows: R_TABLE, or the singles triggered; --singles: the dry
    guitar's reading from the single-blur rows, then R_TABLE). -> PF/replay/report.json or report-singles.json."""
    from learn import pipeline_fix as P

    draw = require_draw()
    require_control()
    singles = bool(args.singles)
    picks = require_hash(PHASE_PICKS2 if singles else PHASE_PICKS, picks_path(singles))
    p_ = report_path(singles)
    never_overwrite(p_)
    sd = Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    rows = SINGLE_ROWS if singles else ROWS
    got = read_rows(sd, draw, picks, rows)
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "draw_sha256": file_sha(draw_path()),
           "picks_sha256": file_sha(picks_path(singles)), "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "included": picks["included"], "left_out": picks["left_out"], "rows": got}
    if not singles:
        out["relag"] = relag_read(draw, picks)
    P.save(p_, out)                                   # the rows are saved before the outcome is read
    readings = {n: row_reading(r["G"]["deciding_pool"], r["I"]["deciding_pool"]) for n, r in got.items()}
    ctl_i = None
    if singles:
        main = json.loads(report_path().read_text())
        base = {n: (v or {}).get("reading") for n, v in main["readings"].items()}
        ctl_i = (main["rows"]["control"]["I"]["deciding_pool"] or {}).get("mean")
        out["outcome"] = outcome(base, {n: (v or {}).get("reading") for n, v in readings.items()})
    else:
        ctl_i = (got["control"]["I"]["deciding_pool"] or {}).get("mean")
        out["outcome"] = outcome({n: (v or {}).get("reading") for n, v in readings.items()})
    out["readings"] = readings
    out["share_of_control_I"] = {n: (r["I"]["deciding_pool"] or {}).get("mean") / ctl_i
                                 if ctl_i and (r["I"]["deciding_pool"] or {}).get("mean") is not None else None
                                 for n, r in got.items()}
    P.save(p_, out)
    for n, r in got.items():
        g, i = r["G"]["deciding_pool"] or {}, r["I"]["deciding_pool"] or {}
        print(f"{n}: G {g.get('mean')} [{g.get('lo90')}, {g.get('hi90')}], I {i.get('mean')} [{i.get('lo90')}, "
              f"{i.get('hi90')}] -> {(readings[n] or {}).get('reading')}")
    print(f"OUTCOME {out['outcome']['code']}: {out['outcome']['reading']}. Next: {out['outcome']['next']}")


# --- main -----------------------------------------------------------------------------------------------------------------

def _shard(s):
    k, n = (int(x) for x in s.split("/"))
    if not 0 <= k < n:
        raise argparse.ArgumentTypeError("k/n with 0 <= k < n")
    return k, n


COMMANDS = {"draw": cmd_draw, "blur": cmd_blur, "sep": cmd_sep, "position-check": cmd_position, "render": cmd_render,
            "control": cmd_control, "bleed": cmd_bleed, "pick": cmd_pick, "score": cmd_score}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=_shard, default=(0, 1))
    ap.add_argument("--dry", default=",".join(MAIN_DRY))
    ap.add_argument("--device", default="mps", choices=("mps", "cpu"))
    ap.add_argument("--singles", action="store_true")
    ap.add_argument("--verdict", choices=("clean", "bleed"))
    ap.add_argument("--by", default="the user, by ear")
    args = ap.parse_args(argv)
    if args.cmd == "bleed" and not args.verdict:
        ap.error("bleed needs --verdict")
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
