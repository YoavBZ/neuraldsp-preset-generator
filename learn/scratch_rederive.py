"""The rebuild's re-derivation on the exact bench (`docs/rederive-plan.md`; ledger `preset-ladder`
`phase_scratch_rederive`, then `phase_scratch_rederive_ladder`, `_frozen`, `_answers_<row>`, `_bench_outcome`,
`_outcome`): the core, the ladder and the two outcome tables.

`rebuild_redo` re-derives four values from the DI it is handed, in this order: the global tuning, the mute times, the
one sustain tilt and the per-onset-group levels (`ELEMENTS`). On the exact bench the four values taken from the true DI
(T) rebuild the bank guitar X (build 2's `tr-di`) byte for byte. This module splits `rebuild_redo` in two without
changing it: `derive` (the four values, `rebuild_redo`'s own estimators in its own order) and `compose`
(`rebuild_redo`'s tail: the synthesis with given values, the hiss removal, the finish, -22.9 LUFS). Both call only
`note_rebuild`'s existing functions. `input_form` builds the three forms of X the rule may be handed:

| Input | What it is |
|---|---|
| `in-F` | X finished, as the bench handed it (`compose` of T, as float32): what `xn-list` was rebuilt from |
| `in-M` | `song_bank.measure(denoise_above(synthesise_redo(T))[:n])`: the form real songs hand over (decides) |
| `in-U` | `denoise_above(synthesise_redo(T))[:n]` at the true DI's RMS, unfinished (beside) |

    $MAIN -m learn.scratch_rederive ladder      # zero renders, once: T, R and every cell per part and input

`ladder` (zero renders) per part: T from the true DI; per input form, today's rule's values R, the 16 value cells (each
element T or R, `VALUE_CELLS`) and the 4 chain cells (one element true, the later ones re-derived after it,
`CHAIN_CELLS`); three proofs: (1) `in-F` is X byte for byte, (2) today's rule handed `in-F` is `xn-list` byte for byte,
(3) today's rule handed `in-M` (`xf-now`) is `rebuild_redo`'s own output byte for byte. It writes only the `in-M`
guitars the rows render: `xf-now` and the four chain cells (the rung rows' guitars), each file written once, under
`PF/fs/rederive/`. The fit (`learn/rederive_fit.py`), the diagnosis (`learn/rederive_diag.py`) and the rows
(`learn/rederive_rows.py`) are later units.

Every command refuses unless this checkout runs main's code (this module, `scratch_exact.py` and its six pinned files,
`note_transcribe.CODE_FILES`, `song_bank.py`) and keys (the `phase_scratch_rederive*` and `phase_scratch_exact*` keys;
`scratch_search.on_main`; `note_transcribe.redo_on_main`), and main holds the draw, build 2's hash, the exact-notes
build's hash and this declaration.

The pure parts (`VALUE_CELLS`, `cell_values`, `chain_fixed`, `values_key`, `mute_errors`, `value_errors`, `XF_TABLE`,
`xf_stage1`, `xf_stage2`, `xf_read`, `RF_TABLE`, `rf_code`, the guards) are tested in tests/test_scratch_rederive.py on
the light CI runner (no numpy), on synthetic keys; `derive`, `compose` and `input_form` against `rebuild_redo` with a
made-up bank (numpy, skipped elsewhere).
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import pathlib
import statistics
import time

from learn import note_rebuild as NR
from learn import note_transcribe as NT
from learn import scratch_exact as SE
from learn import scratch_search as S

LEDGER_ID = S.LEDGER_ID                  # preset-ladder
PLAN = "docs/rederive-plan.md"
KEY_PREFIX = "phase_scratch_rederive"
PHASE = KEY_PREFIX                       # the declaration
PHASE_LADDER = f"{KEY_PREFIX}_ladder"    # Phase 1's hash PR: the ladder's, the diagnosis' and xf-now's sha256
PHASE_FROZEN = f"{KEY_PREFIX}_frozen"    # Phase 2's: the frozen rule, the safety stop, both builds' sha256
PHASE_BENCH_OUTCOME = f"{KEY_PREFIX}_bench_outcome"
PHASE_OUTCOME = f"{KEY_PREFIX}_outcome"
BANK_BUILD = SE.BUILD2                   # "b2": X is build 2's tr-di
BANK_ARM = SE.BANK_ARM                   # "tr-di"
ELEMENTS = ("tuning", "mutes", "tilt", "levels")   # rebuild_redo's order
INPUTS = ("in-F", "in-M", "in-U")
DECIDING_INPUT = "in-M"                  # what build_todo hands the rule on real songs (the re-review, section 2)
TODAY = "R" * len(ELEMENTS)              # the value cell of today's rule (every element re-derived)
TRUE = "T" * len(ELEMENTS)               # every element true: X itself
VALUE_CELLS = tuple("".join(c) for c in itertools.product("RT", repeat=len(ELEMENTS)))   # position i: ELEMENTS[i]
CHAIN_CELLS = ELEMENTS                   # chain cell e: e true, the others re-derived (the later ones after it)
RUNG_ROWS = tuple(f"xf-{e}" for e in ELEMENTS)     # a rung row searches its chain cell's in-M guitar
NOW_ROW, FIX_ROW, NULL_ROW = "xf-now", "xf-fix", "xf-null"
BENCH_ROWS = (NOW_ROW, FIX_ROW, NULL_ROW) + RUNG_ROWS
REAL_ROW = "fs-refit"                    # the bridge: build 2's notes, the frozen rule, the true DI
REAL_BUILD = "rf2"
ROWS = BENCH_ROWS + (REAL_ROW,)
SHORT = {NOW_ROW: "now", FIX_ROW: "fix", NULL_ROW: "null", **{f"xf-{e}": e for e in ELEMENTS}, REAL_ROW: "refit"}
LADDER_WRITES = (NOW_ROW,) + RUNG_ROWS   # the in-M guitars the ladder stores (only the guitars to be rendered)
STAGE_1, STAGE_2 = (NOW_ROW,), (FIX_ROW,)   # the bench table's two stages (the re-review's amendment 1)
DECIDING = SE.DECIDING                   # BKS+GOAT, the 40; all 47 beside
SMALL, BIG = S.SMALL, S.BIG              # 0.05, 0.10: they label only
MUTE_MATCH_S = NR.MUTE_FADE_S            # beside only: a mute counts as found when the other list has one within 30 ms
PINNED = tuple(dict.fromkeys(SE.CODE_FILES + NT.CODE_FILES + ("learn/song_bank.py", "learn/di_robustness.py")))
CODE_FILES = ("learn/scratch_rederive.py",) + PINNED
GUARDED_PREFIXES = ("phase_fs", "phase_scratch_notes", "phase_scratch_exact", "phase_scratch_readerr", "phase_nr")

# The fit's rules (plan v2 "The fit's rules", with the re-review's amendment 5), declared here before Unit 3 codes them
FIT = {
    "domains": ("unfinished", "measured", "finished"),   # the comparison domain, in the "simpler" order
    "passes": ("one", "iterated"),
    "mutes": ("as-now", "veto"),
    "candidates": 12,                    # 3 domains x 2 passes x 2 mute rules, plus today's rule
    "mute_veto_s": NR.MUTE_FADE_S,       # a drop is kept only if the rebuild has no mute of its own within 30 ms
    "repeat_tuning_cents": 0.05,         # half of Bank.note's 0.1-cent rounding
    "repeat_level_db": 0.01,             # at_lufs' own tolerance
    "repeat_tilt_db_s": 0.027,           # 0.01 dB over the estimator's 0.375-s span
    "max_passes": 64,                    # converge's bound (the measurement's own); the stop is set from it
    "cycle_match": "within the repeat tolerances",
    "update": "each pass adds the measured difference; tuning and tilt take a secant step from the second pass on",
    "cycle": "a pass that matches (within the repeat tolerances) any earlier pass but its predecessor stops the fit; "
             "the pass used is the cycle's member with the lowest residual, a tie the earliest",
    "safety_stop": "converge runs every iterated candidate on the 47 bench parts in in-M up to max_passes; the stop "
                   "is the largest pass count among fits that repeated; every fit reaching it is listed, its pass used "
                   "the lowest-residual pass at or before the stop; the stop also applies to build-real, whose fits "
                   "that reach it are listed too; the number and both lists go into the ledger with freeze",
    "deciding_measure": "note_rebuild.logmel_distance from the candidate's finished guitar to X, in in-M, on the 40",
    "tie": "per-part paired differences from the lowest-mean candidate through scratch_notes.set_rows' BKS+GOAT pool; "
           "an interval that spans zero is a tie",
    "simpler": "today's rule first; then fewer passes; then the domain (unfinished, measured, finished); then mutes as "
               "now before the veto",
}


def answers_key(row):
    """(Pure.) A row's answers hash key: `phase_scratch_rederive_answers_<now|fix|null|tuning|...|refit>`."""
    if row not in ROWS:
        raise SystemExit(f"unknown row {row!r}: one of {list(ROWS)}")
    return f"{KEY_PREFIX}_answers_{SHORT[row]}"


KEYS_TO_COME = (PHASE_LADDER, PHASE_FROZEN) + tuple(answers_key(r) for r in ROWS) + (PHASE_BENCH_OUTCOME, PHASE_OUTCOME)


# --- the cells (pure) ------------------------------------------------------------------------------------------------------

def cell_true(cell):
    """(Pure.) The elements a value cell takes true. cell: a string of T and R, position i for ELEMENTS[i]."""
    if cell not in VALUE_CELLS:
        raise ValueError(cell)
    return tuple(e for e, c in zip(ELEMENTS, cell) if c == "T")


def cell_values(T, R, cell):
    """(Pure.) A value cell's four values: each element T's where the cell says T, R's where it says R."""
    on = set(cell_true(cell))
    return {e: (T[e] if e in on else R[e]) for e in ELEMENTS}


def chain_fixed(T, element):
    """(Pure.) A chain cell's given values: `element` true; `derive` re-derives the rest, the later ones after it."""
    if element not in CHAIN_CELLS:
        raise ValueError(element)
    return {element: T[element]}


def values_key(v):
    """(Pure.) A hashable key of four values (equal keys compose the same guitar)."""
    return (float(v["tuning"]), tuple(float(t) for t in v["mutes"]), float(v["tilt"]),
            tuple(float(g) for g in v["levels"]))


def values_json(v):
    return {"tuning": float(v["tuning"]), "mutes": [float(t) for t in v["mutes"]], "tilt": float(v["tilt"]),
            "levels": [float(g) for g in v["levels"]]}


def mute_errors(true, got, tol=MUTE_MATCH_S):
    """(Pure.) Beside only: `got`'s mutes with no true mute within `tol` (extra), the true mutes with none of `got`'s
    within `tol` (missed)."""
    def near(t, xs):
        return any(abs(t - x) <= tol + 1e-12 for x in xs)
    return {"true": len(true), "got": len(got), "extra": sum(not near(t, true) for t in got),
            "missed": sum(not near(t, got) for t in true), "identical": list(true) == list(got)}


def value_errors(T, R):
    """(Pure.) R's errors against T: tuning and tilt (absolute), each group's level (absolute dB), the mutes."""
    if len(T["levels"]) != len(R["levels"]):
        raise ValueError("the two value sets have different onset groups: the notes differ")
    lv = [abs(a - b) for a, b in zip(T["levels"], R["levels"])]
    return {"tuning_cents": abs(T["tuning"] - R["tuning"]), "tilt_db_s": abs(T["tilt"] - R["tilt"]),
            "tilt_part": T["tilt"] != 0 or R["tilt"] != 0, "levels_db": lv,
            "levels_median_db": statistics.median(lv) if lv else None, "mutes": mute_errors(T["mutes"], R["mutes"]),
            "identical": values_key(T) == values_key(R)}


# --- the intervals (pure) ------------------------------------------------------------------------------------------------------

def iv_ok(iv):
    """(Pure.) A usable 90% interval: a dict with finite mean, lo90 and hi90, lo90 <= hi90."""
    if not isinstance(iv, dict):
        return False
    try:
        m, lo, hi = (float(iv[k]) for k in ("mean", "lo90", "hi90"))
    except (KeyError, TypeError, ValueError):
        return False
    return all(math.isfinite(x) for x in (m, lo, hi)) and lo <= hi


def _end(iv, k):
    return iv.get(k) if isinstance(iv, dict) else None


def wholly_above(iv):
    return iv_ok(iv) and iv["lo90"] > 0


def wholly_below(iv):
    return iv_ok(iv) and iv["hi90"] < 0


def spans_zero(iv):
    return iv_ok(iv) and iv["lo90"] <= 0 <= iv["hi90"]


# --- the bench table, read in two stages (pure) --------------------------------------------------------------------------

XF_TABLE = (    # (code, stage, when, said, next); within a stage, the first that holds (on the 40, the answer arm)
    ("XF-anomaly", (1, 2), "D_now (stage 1) or D_fix (stage 2) wholly below zero",
     "a re-derived guitar beats X itself", "audit before anything is said"),
    ("XF-input", (1,), "D_now spans zero",
     "in the real-song input form today's rule's cost is not shown; the read rules out a cost above D_now's "
     "hi90 = {now_hi}; undecided is not failed",
     "xf-fix does not run; to the user; the bridge is the user's call"),
    ("XF-worse", (2,), "the gain (D_fix - D_now) wholly above zero", "the rule costs more than today's",
     "not kept; audit; rung rows, tilt and mutes first"),
    ("XF-closed", (2,), "the gain wholly below zero, D_fix spans zero",
     "the cost is no longer shown; a cost above D_fix's hi90 = {fix_hi} is ruled out", "the bridge runs"),
    ("XF-part", (2,), "the gain wholly below zero, D_fix wholly above zero", "it helps; a residual is shown",
     "the bridge runs; the residual is priced by the rungs the fit recovered worst, and by the null row if the "
     "guitars are near X"),
    ("XF-undecided", (2,), "the gain spans zero", "not decided; undecided is not failed",
     "rung rows, cheapest first; the bridge is the user's call"),
    ("XF-other", (1, 2), "anything else", "no reading", "to the user with the numbers; nothing runs on"),
)
XF_CODES = tuple(c for c, *_ in XF_TABLE)
XF_DECLARED = ("XF-anomaly", "XF-input", "XF-worse", "XF-closed", "XF-part", "XF-undecided", "XF-other")
GO_ON = "stage 1 goes on: xf-fix runs (stage 2)"

RF_TABLE = (    # (code, when, said, next); the first that holds (on the 40, the answer arm)
    ("RF-anomaly", "G(fs-refit) - G(row (b)) wholly below zero", "the rebuilt guitar beats the true DI",
     "audit before anything is said"),
    ("RF-closer", "D_real wholly below zero", "the rule moves real songs, with the DI still supplying every input",
     "to the user: adoption, an ear page, then the later step in Scope; not a licence for the song-only path"),
    ("RF-worse", "D_real wholly above zero", "the bench does not carry", "not adopted; audit"),
    ("RF-undecided", "D_real spans zero", "not decided; undecided is not failed{level}",
     "to the user with what the interval rules out (hi90 = {real_hi}, lo90 = {real_lo})"),
    ("RF-other", "anything else", "no reading", "to the user"),
)
RF_CODES = tuple(c for c, *_ in RF_TABLE)
RF_DECLARED = ("RF-anomaly", "RF-closer", "RF-worse", "RF-undecided", "RF-other")


def tables_guard():
    """Refuse unless both tables hold their declared codes in order, the stages are as declared, 0 < SMALL < BIG and the
    key prefix sits outside every guarded prefix."""
    if XF_CODES != XF_DECLARED:
        raise SystemExit("XF_TABLE's codes are not the seven declared, in order")
    if RF_CODES != RF_DECLARED:
        raise SystemExit("RF_TABLE's codes are not the five declared, in order")
    stages = {c: s for c, s, *_ in XF_TABLE}
    if stages != {"XF-anomaly": (1, 2), "XF-input": (1,), "XF-worse": (2,), "XF-closed": (2,), "XF-part": (2,),
                  "XF-undecided": (2,), "XF-other": (1, 2)}:
        raise SystemExit("XF_TABLE's stages are not the declared two")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")
    if not KEY_PREFIX.startswith("phase_scratch_") or KEY_PREFIX.startswith(GUARDED_PREFIXES):
        raise SystemExit(f"{KEY_PREFIX} sits under a guarded prefix")


def _xf(code, stage, d_now=None, d_fix=None, gain=None):
    row = next(r for r in XF_TABLE if r[0] == code)
    said = row[3].format(now_hi=_end(d_now, "hi90"), fix_hi=_end(d_fix, "hi90"))
    return {"code": code, "stage": stage, "when": row[2], "reading": said, "next": row[4], "go_on": False,
            "d_now": d_now, "d_fix": d_fix, "gain": gain}


def xf_stage1(d_now):
    """(Pure.) Stage 1, after `xf-now` only: XF-anomaly on D_now, then XF-input; D_now wholly above zero goes on to
    stage 2 (no code yet); anything else XF-other. d_now: G(xf-now) - G(xn-bank) on the 40. -> dict."""
    if not iv_ok(d_now):
        return _xf("XF-other", 1, d_now)
    if wholly_below(d_now):
        return _xf("XF-anomaly", 1, d_now)
    if spans_zero(d_now):
        return _xf("XF-input", 1, d_now)
    if wholly_above(d_now):
        return {"code": None, "stage": 1, "go_on": True, "reading": "today's rule's cost is shown in the real-song "
                "input form", "next": GO_ON, "d_now": d_now}
    return _xf("XF-other", 1, d_now)                    # unreachable with a usable interval


def xf_stage2(d_now, d_fix, gain):
    """(Pure.) Stage 2, after `xf-fix`: only when stage 1 went on (refused otherwise). XF-anomaly on D_fix, XF-worse,
    XF-closed, XF-part, XF-undecided, else XF-other. d_fix: G(xf-fix) - G(xn-bank); gain: G(xf-fix) - G(xf-now),
    paired per part; all on the 40. -> dict."""
    if not xf_stage1(d_now)["go_on"]:
        raise SystemExit("stage 2 reads only after stage 1 went on (D_now wholly above zero): xf-fix does not run")
    if not iv_ok(d_fix) or not iv_ok(gain):
        return _xf("XF-other", 2, d_now, d_fix, gain)
    if wholly_below(d_fix):
        return _xf("XF-anomaly", 2, d_now, d_fix, gain)
    if wholly_above(gain):
        return _xf("XF-worse", 2, d_now, d_fix, gain)
    if wholly_below(gain) and spans_zero(d_fix):
        return _xf("XF-closed", 2, d_now, d_fix, gain)
    if wholly_below(gain) and wholly_above(d_fix):
        return _xf("XF-part", 2, d_now, d_fix, gain)
    if spans_zero(gain):
        return _xf("XF-undecided", 2, d_now, d_fix, gain)
    return _xf("XF-other", 2, d_now, d_fix, gain)       # unreachable with usable intervals


def xf_read(d_now, d_fix=None, gain=None):
    """(Pure.) The bench table's one code: stage 1's when it ends there, else stage 2's. -> dict."""
    s1 = xf_stage1(d_now)
    return s1 if not s1["go_on"] else xf_stage2(d_now, d_fix, gain)


def rf_code(d_vs_b, d_real):
    """(Pure.) RF_TABLE's code, the first that holds. d_vs_b: G(fs-refit) - G(row (b)); d_real: G(fs-refit) -
    G(build 2), paired per part; both on the 40. RF-undecided is labelled "level, not readable by the score" when D_real
    lies inside +-SMALL. -> dict."""
    if not iv_ok(d_vs_b) or not iv_ok(d_real):
        code = "RF-other"
    elif wholly_below(d_vs_b):
        code = "RF-anomaly"
    elif wholly_below(d_real):
        code = "RF-closer"
    elif wholly_above(d_real):
        code = "RF-worse"
    elif spans_zero(d_real):
        code = "RF-undecided"
    else:
        code = "RF-other"                                # unreachable with usable intervals
    row = next(r for r in RF_TABLE if r[0] == code)
    level = iv_ok(d_real) and d_real["lo90"] >= -SMALL and d_real["hi90"] <= SMALL
    said = row[2].format(level="; level, not readable by the score" if level else "")
    nxt = row[3].format(real_hi=_end(d_real, "hi90"), real_lo=_end(d_real, "lo90"))
    return {"code": code, "when": row[1], "reading": said, "next": nxt, "level_not_readable": bool(level),
            "d_vs_b": d_vs_b, "d_real": d_real}


# --- the guards ---------------------------------------------------------------------------------------------------------------

def keys_refusal(local, main):
    """(Pure.) Why this checkout's `phase_scratch_rederive*` or `phase_scratch_exact*` keys are not main's, or None."""
    for pre in (KEY_PREFIX, SE.KEY_PREFIX):
        a = {k: v for k, v in (local or {}).items() if k.startswith(pre)}
        b = {k: v for k, v in (main or {}).items() if k.startswith(pre)}
        if a != b:
            return f"this checkout's {sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))} differ from main's"
    return None


def pinned_identity():
    """Each of CODE_FILES equal to origin/main's (git diff --quiet). -> {file: identical}."""
    return {f: SE._git("diff", "--quiet", "origin/main", "--", f).returncode == 0 for f in CODE_FILES}


def require_rederive(*phases):
    """Refuse unless this checkout runs main's code and keys, and main holds the draw, build 2's hash, the exact-notes
    declaration and Phase A's hashes (the bench's build.json), this declaration and `phases`. -> main's `preset-ladder`
    entry."""
    from learn import note_replay as NRP

    tables_guard()
    m = S.require_on_main(S.PHASE, S.PHASE_DRAW, SE.PHASE_BANK, SE.PHASE, SE.PHASE_TARGETS, PHASE, *phases)
    bad = [f for f, ok in pinned_identity().items() if not ok]
    if bad:
        raise SystemExit(f"this checkout's {bad} differ from main's: run from merged code")
    why = keys_refusal(NRP.ledger_entry(), m)
    if why:
        raise SystemExit(why)
    return m


# --- paths --------------------------------------------------------------------------------------------------------------------

def rederive_dir():
    return S.fs_dir() / "rederive"


def dry_path(row, pk):
    if row not in LADDER_WRITES:
        raise ValueError(row)
    return rederive_dir() / "dry" / row / f"{SE._f(pk)}.npy"


def part_path(pk):
    return rederive_dir() / "ladder" / f"{SE._f(pk)}.json"


def ladder_path():
    return rederive_dir() / "ladder.json"


# --- the core: derive, compose, input_form (numpy) -------------------------------------------------------------------------

def _padded(n, rate):
    return n + int(round(NR.END_PAD_S * rate))


def _synth(notes, n, bank, ring, tuning, mutes, tilt, levels, loud, rate, last):
    """`synthesise_redo` on the padded length as `rebuild_redo` calls it: with `loud`, the note weights in every pass
    and the group trims in the last only."""
    if loud is None:
        return NR.synthesise_redo(notes, _padded(n, rate), bank, tuning, ring, mutes, tilt, levels, rate)
    w = NR.note_weights(notes, loud)
    trims = NR.group_trims(notes, loud) if last else None
    return NR.synthesise_redo(notes, _padded(n, rate), bank, tuning, ring, mutes, tilt, levels, rate, note_weights=w,
                              group_trim=trims)


def derive(notes, n, bank, di, ring, loud=None, fixed=None, rate=NR.SR):
    """`rebuild_redo`'s four values (`tr-di`) from `di`, in its order: the global tuning, the mutes, the sustain tilt
    (against the plain synthesis with no tilt and no levels), the levels (`oracle_gains` against the plain synthesis
    with the tilt). `fixed` ({element: value}) takes those as given; every other element is re-derived, a later one
    after the given ones (a chain cell). -> (values, report)."""
    fixed = dict(fixed or {})
    bad = set(fixed) - set(ELEMENTS)
    if bad:
        raise ValueError(f"unknown elements {sorted(bad)}")
    tune = fixed["tuning"] if "tuning" in fixed else NR.global_tuning_cents(di, rate)
    mutes = list(fixed["mutes"]) if "mutes" in fixed else NR.mute_times(di, rate)
    trep = None
    if "tilt" in fixed:
        tilt = fixed["tilt"]
    else:
        plain0, _ = _synth(notes, n, bank, ring, tune, mutes, 0.0, None, loud, rate, last=False)
        tilt, trep = NR.sustain_tilt(notes, plain0[:n], di, rate)
    if "levels" in fixed:
        levels = list(fixed["levels"])
    else:
        plain, _ = _synth(notes, n, bank, ring, tune, mutes, tilt, None, loud, rate, last=False)
        levels = NR.oracle_gains(notes, plain[:n], di, rate)
    return ({"tuning": tune, "mutes": mutes, "tilt": tilt, "levels": levels},
            {"tilt": trep, "given": sorted(fixed)})


def unfinished(notes, n, bank, ring, values, loud=None, rate=NR.SR):
    """The synthesis with `values`, the hiss removal run again after the level gain, trimmed to `n`: the rebuild before
    its finish (`denoise_above(synthesise_redo(values))[:n]`)."""
    y, _ = _synth(notes, n, bank, ring, values["tuning"], values["mutes"], values["tilt"], values["levels"], loud, rate,
                  last=True)
    return NR.denoise_above(y, rate)[:n]


def compose(notes, n, bank, ring, finish, values, loud=None, rate=NR.SR):
    """`rebuild_redo`'s tail (`tr-di`) with given values: the synthesis, the hiss removal, the finish (or none), then
    ASSUMED_LUFS on `n` samples. -> (audio float64, report)."""
    y, rep = _synth(notes, n, bank, ring, values["tuning"], values["mutes"], values["tilt"], values["levels"], loud,
                    rate, last=True)
    y = NR.denoise_above(y, rate)
    if finish is not None:
        y = finish(y)
    y = NR.at_lufs(y[:n], NR.ASSUMED_LUFS, rate)
    return y, {**rep, "tuning_cents": round(values["tuning"], 2), "mutes": len(values["mutes"]),
               "tilt_db_s": values["tilt"], "ring": ring, "lufs": NR.ASSUMED_LUFS,
               **({"loud_gamma": loud} if loud is not None else {})}


def input_form(kind, notes, n, bank, ring, T, di, finish=None, loud=None, measure=None, raw=None, rate=NR.SR):
    """The form of X the rule is handed, built from the true values T (float64):
    `in-F` X finished: `compose` of T with the part's finish, rounded to float32 as the bench's bank guitar was;
    `in-M` `song_bank.measure(denoise_above(synthesise_redo(T))[:n])` (`measure` stands in only in tests);
    `in-U` `denoise_above(synthesise_redo(T))[:n]` scaled to the true DI's RMS.
    `raw`: `unfinished(..., T)` when already made (in-M and in-U share it)."""
    import numpy as np

    if kind not in INPUTS:
        raise ValueError(kind)
    if kind == "in-F":
        y, _ = compose(notes, n, bank, ring, finish, T, loud, rate)
        return np.asarray(np.asarray(y, np.float32), np.float64)
    if raw is None:
        raw = unfinished(notes, n, bank, ring, T, loud, rate)
    if kind == "in-M":
        if measure is None:
            from learn import song_bank as SB

            measure = SB.measure
        return np.asarray(measure(raw), np.float64)
    d = np.asarray(di, np.float64)
    return raw * (np.sqrt(np.mean(d ** 2)) / (np.sqrt(np.mean(raw ** 2)) + 1e-12))


def cells(notes, n, bank, ring, finish, T, u, loud=None, rate=NR.SR):
    """One input form's ladder: today's rule's values R from `u`, the 16 value cells and the 4 chain cells, each
    guitar composed once per distinct value set. -> {"R", "report", "value": {cell: (y32, values)},
    "chain": {element: (y32, values)}}."""
    import numpy as np

    R, rep = derive(notes, n, bank, u, ring, loud, None, rate)
    made = {}

    def guitar(v):
        k = values_key(v)
        if k not in made:
            y, _ = compose(notes, n, bank, ring, finish, v, loud, rate)
            made[k] = np.asarray(y, np.float32)
        return made[k]
    value = {c: (guitar(cell_values(T, R, c)), cell_values(T, R, c)) for c in VALUE_CELLS}
    chain = {}
    for e in CHAIN_CELLS:
        v, _ = derive(notes, n, bank, u, ring, loud, chain_fixed(T, e), rate)
        chain[e] = (guitar(v), v)
    return {"R": R, "report": rep, "value": value, "chain": chain, "distinct": len(made)}


# --- the ladder (zero renders) ------------------------------------------------------------------------------------------------

def _write_once(path, y32):
    """Save a guitar once: an existing file must hold exactly these samples (a rerun after a stop), else refuse."""
    import numpy as np

    if path.exists():
        if S.file_sha(path) != S.npy_sha(y32):
            raise SystemExit(f"{path.name} exists with other samples: never overwritten")
        return S.file_sha(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, np.asarray(y32, np.float32))
    return S.file_sha(path)


def _cell_figures(X64, y32, x_sha, now_sha):
    import numpy as np

    y = np.asarray(y32, np.float64)
    sha = S.npy_sha(y32)
    return {"sha256": sha, "identical_to_x": sha == x_sha, "identical_to_now": sha == now_sha,
            "logmel_to_x": float(NR.logmel_distance(X64, y)), "env_corr_to_x": float(NR.envelope_corr(X64, y))}


def _mean(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return statistics.mean(xs) if xs else None


def _median(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return statistics.median(xs) if xs else None


def ladder_summary(parts, keys):
    """(Pure.) The ladder's descriptive figures over `keys` (beside; never a price): per input form, today's rule's
    distance to X and its value errors against T; per value and chain cell, the mean distance to X and the parts
    byte-identical to X; per chain cell, the parts whose in-M guitar differs from xf-now's (the rung rows' searches)."""
    out = {}
    for u in INPUTS:
        rows = [parts[k]["inputs"][u] for k in keys]
        err = [r["errors"] for r in rows]
        tilt = [e["tilt_db_s"] for e in err if e["tilt_part"]]
        out[u] = {
            "today_logmel_to_x_mean": _mean([r["value"][TODAY]["logmel_to_x"] for r in rows]),
            "today_identical_to_x": sum(r["value"][TODAY]["identical_to_x"] for r in rows),
            "tilt_parts": len(tilt), "tilt_error_mean_db_s": _mean(tilt),
            "level_error_median_db": _median([x for e in err for x in e["levels_db"]]),
            "mutes_true": sum(e["mutes"]["true"] for e in err), "mutes_got": sum(e["mutes"]["got"] for e in err),
            "mutes_extra": sum(e["mutes"]["extra"] for e in err),
            "mutes_missed": sum(e["mutes"]["missed"] for e in err),
            "tuning_error_median_cents": _median([e["tuning_cents"] for e in err]),
            "values_identical": sum(e["identical"] for e in err),
            "value_cells": {c: {"logmel_to_x_mean": _mean([r["value"][c]["logmel_to_x"] for r in rows]),
                                "identical_to_x": sum(r["value"][c]["identical_to_x"] for r in rows)}
                            for c in VALUE_CELLS},
            "chain_cells": {e: {"logmel_to_x_mean": _mean([r["chain"][e]["logmel_to_x"] for r in rows]),
                                "identical_to_x": sum(r["chain"][e]["identical_to_x"] for r in rows),
                                "changed_from_today": sum(not r["chain"][e]["identical_to_now"] for r in rows)}
                            for e in CHAIN_CELLS}}
    return out


def cmd_ladder(_args):
    """Phase 1 (zero renders), once: per part (build 2's notes after its fixes, as `scratch_exact build` made them), T
    from the true DI; the three input forms; per form R, the 16 value cells and the 4 chain cells (`cells`); the
    proofs: (1) `in-F` is X byte for byte, (2) today's rule on `in-F` is `xn-list` byte for byte, (3) `xf-now` (today's
    rule on `in-M`) is `rebuild_redo`'s own output byte for byte; this module and the pinned files equal main's. A part
    whose proofs fail writes nothing. Per part the in-M guitars of `xf-now` and the four rung rows (each file written
    once) and its record; then, only when every part's proofs hold, ladder.json (never overwritten)."""
    m = require_rederive()
    NT.never_overwrite(ladder_path())
    import numpy as np

    from learn import note_fixes as NF
    from learn import pipeline_fix as P

    _, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    b2 = SE.bank_build(m)
    xb = SE.require_xbuild(m)
    pinned = pinned_identity()
    if not all(pinned.values()):
        raise SystemExit(f"{[f for f, ok in pinned.items() if not ok]} differ from main's")
    fixes, ring, loud = b2["fixes"], b2["ring_variant"], b2.get("loud_gamma")
    if (xb["fixes"], xb["ring_variant"], xb.get("loud_gamma")) != (fixes, ring, loud):
        raise SystemExit("the exact-notes build was not made with build 2's rule")
    excl, _, _, _ = NT._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    todo = NT.build_todo(NT.install_pair(NT.load_manifest()), NT.ear_items_file(BANK_BUILD))
    parts = [t for t in todo if t[0] == "part"]
    if sorted(k for _, k, *_ in parts) != sorted(xb["parts"]):
        raise SystemExit("the parts are not the exact-notes build's")
    t0 = time.time()
    recs, failed = {}, {}
    for kind, key, info, rec, di, finish in parts:
        pp = part_path(key)
        if pp.exists():
            r = json.loads(pp.read_text())
            for row, f in r["files"].items():
                if S.file_sha(dry_path(row, key)) != f["file_sha256"]:
                    raise SystemExit(f"{key}: {row}'s guitar changed since its record")
            recs[key] = r
            continue
        tp = time.time()
        x_sha = b2["parts"][key]["arms"][BANK_ARM]["sha256"]
        list_sha = xb["parts"][key]["guitars"]["xn-list"]["sha256"]
        X64 = np.asarray(NT.load_dry(BANK_ARM, key, b2), np.float64)
        di = np.asarray(di, np.float64)
        if S.npy_sha(di) != xb["parts"][key]["guitars"]["xn-swap"]["sha256"]:
            raise SystemExit(f"{key}: the DI is not the exact-notes build's true DI")
        notes, _ = NT.timed_notes(rec, di)
        exact, _ = NF.apply_fixes(notes, fixes, di)
        if len(exact) != xb["parts"][key]["notes"] or len(X64) != len(di):
            raise SystemExit(f"{key}: the exact note list or the length is not the exact-notes build's")
        n = len(X64)
        T, trep = derive(exact, n, bank, di, ring, loud)
        raw = unfinished(exact, n, bank, ring, T, loud)
        forms = {u: input_form(u, exact, n, bank, ring, T, di, finish, loud, raw=raw) for u in INPUTS}
        lad = {u: cells(exact, n, bank, ring, finish, T, forms[u], loud) for u in INPUTS}
        now32 = lad[DECIDING_INPUT]["value"][TODAY][0]
        y_rr, _ = NR.rebuild_redo(BANK_ARM, exact, n, bank, forms[DECIDING_INPUT], ring, finish=finish, loud=loud)
        proofs = {"in_f_is_x": S.npy_sha(forms["in-F"]) == x_sha,
                  "today_on_in_f_is_xn_list": S.npy_sha(lad["in-F"]["value"][TODAY][0]) == list_sha,
                  "xf_now_is_rebuild_redo": S.npy_sha(y_rr) == S.npy_sha(now32)}
        if not all(proofs.values()):
            failed[key] = proofs
            print(f"{key[-40:]}: PROOF FAILED {proofs}: nothing written for this part", flush=True)
            continue
        now_sha = S.npy_sha(now32)
        row = {"plan": PLAN, "part": key, "set": info["set"], "n": n, "notes": len(exact), "T": values_json(T),
               "T_tilt_report": trep["tilt"], "proofs": proofs, "inputs": {}, "files": {}}
        for u in INPUTS:
            L = lad[u]
            row["inputs"][u] = {
                "input_sha256": S.npy_sha(forms[u]), "R": values_json(L["R"]), "R_tilt_report": L["report"]["tilt"],
                "errors": value_errors(T, L["R"]), "distinct_guitars": L["distinct"],
                "value": {c: _cell_figures(X64, y, x_sha, now_sha) for c, (y, _v) in L["value"].items()},
                "chain": {e: dict(_cell_figures(X64, y, x_sha, now_sha), values=values_json(v),
                                  errors=value_errors(T, v)) for e, (y, v) in L["chain"].items()}}
        guitars = {NOW_ROW: now32, **{f"xf-{e}": lad[DECIDING_INPUT]["chain"][e][0] for e in CHAIN_CELLS}}
        for g, y32 in guitars.items():
            row["files"][g] = {"file_sha256": _write_once(dry_path(g, key), y32), "audio_sha256": S.npy_sha(y32)}
        row.update(seconds=round(time.time() - tp, 1), time=time.strftime("%Y-%m-%d %H:%M:%S"))
        NT.never_overwrite(pp)
        P.save(pp, row)
        recs[key] = row
        d_now = row["inputs"][DECIDING_INPUT]["value"][TODAY]["logmel_to_x"]
        print(f"{key[-40:]}: proofs hold; today's rule on in-M {d_now:.3f} from X; {row['seconds']} s "
              f"({time.time() - t0:.0f} s in all)", flush=True)
    n_all = len(parts)
    held = {p: sum(r["proofs"][p] for r in recs.values()) for p in ("in_f_is_x", "today_on_in_f_is_xn_list",
                                                                     "xf_now_is_rebuild_redo")}
    print(f"RD LADDER proofs: in-F is X {held['in_f_is_x']} of {n_all}; today's rule on in-F is xn-list "
          f"{held['today_on_in_f_is_xn_list']} of {n_all}; xf-now is rebuild_redo's "
          f"{held['xf_now_is_rebuild_redo']} of {n_all}; failed {len(failed)}; pinned {sum(pinned.values())} of "
          f"{len(pinned)}")
    if failed or len(recs) != n_all:
        raise SystemExit(f"the proofs do not hold on every part ({len(failed)} failed): ladder.json not written; "
                         "a bug, to the user")
    keys = sorted(recs)
    deciding = [k for k in keys if recs[k]["set"] in DECIDING]
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": 0, "bank_build": BANK_BUILD,
           "bank_build_sha256": S.file_sha(NT.build_path(BANK_BUILD)),
           "exact_build_sha256": S.file_sha(SE.build_path()),
           "fixes": fixes, "ring_variant": ring, "loud_gamma": loud, "inputs": list(INPUTS),
           "deciding_input": DECIDING_INPUT, "elements": list(ELEMENTS), "value_cells": list(VALUE_CELLS),
           "chain_cells": list(CHAIN_CELLS), "written": list(LADDER_WRITES), "mute_match_s": MUTE_MATCH_S,
           "pinned": pinned, "proofs": {p: {"held": v, "of": n_all} for p, v in held.items()},
           "proofs_hold": True, "deciding_parts": len(deciding),
           "summary": {"the_40": ladder_summary(recs, deciding), "all_47": ladder_summary(recs, keys)},
           "parts": {k: {"record_sha256": S.file_sha(part_path(k)), "files": recs[k]["files"]} for k in keys},
           "seconds": round(time.time() - t0, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    NT.never_overwrite(ladder_path())
    P.save(ladder_path(), out)
    for u in INPUTS:
        s = out["summary"]["the_40"][u]
        print(f"  {u} on the 40: today's rule {s['today_logmel_to_x_mean']:.3f} from X (logmel), tilt error "
              f"{s['tilt_error_mean_db_s']} dB/s on {s['tilt_parts']} parts, level error median "
              f"{s['level_error_median_db']} dB, mutes extra {s['mutes_extra']} missed {s['mutes_missed']}, tuning "
              f"error median {s['tuning_error_median_cents']} c; rung rows' changed parts (all 47) "
              f"{ {e: out['summary']['all_47'][u]['chain_cells'][e]['changed_from_today'] for e in CHAIN_CELLS} }")
    print(f"RD LADDER: {len(keys)} parts, {out['seconds']} s; sha256 {S.file_sha(ladder_path())} (into the ledger as "
          f"{PHASE_LADDER} with the diagnosis')")


COMMANDS = {"ladder": cmd_ladder}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
