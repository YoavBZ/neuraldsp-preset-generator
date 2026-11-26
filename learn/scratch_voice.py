"""Pricing the sound gap at the real floor (`docs/scratch-voice-plan.md`; ledger `preset-ladder` `phase_scratch_voice`,
then `phase_scratch_voice_dry`, `phase_scratch_voice_outcome`): the core, the outcome table and the read.

T = ln(d_tr-di / d_true) is row (b)'s answer rendered through build 2's bank guitar `tr-di` against through the true DI,
judged on the held half against the clean record with the true DI as the judge's DI (the exact-notes test's stored real
floors). This test splits T into four terms along a declared chain of guitars (`CHAIN`, amendment 6):

    tr-di  ->  vc-own  ->  vc-cut  ->  vc-fin  ->  true

| Guitar | What it is (`vc-own`, `vc-cut` and `vc-fin` are built from the raw section, `pretrain_set.section_audio`, through the part's own finish `p.finish`, then -22.9 LUFS: the orchestrator's call on amendment 1; on the padded length with the edge fade, as `tr-di`'s compose (review B1, `WINDOWS["chain"]`); `vc-env` comes from `tr-di`) |
|---|---|
| `vc-own` | the raw section gated by our played notes (`WINDOWS`), then the finish |
| `vc-cut` | the raw section with the worst-case notch at every one of our onset groups (`NOTCH`), then the finish |
| `vc-fin` | the raw section through the finish: `tr-di`'s own finish chain at real sound |
| `vc-env` | beside: `tr-di` times a gain that makes its 20-ms level follow the true DI's (`ENV`) |
| `avg+mild` | beside, stored: row (c)'s dry guitar |

| Term | Definition | Meaning |
|---|---|---|
| S | ln(d_tr-di / d_vc-own) | real audio inside our note windows closes at most S (an upper bound; not a sound gap, amendment 2) |
| N | ln(d_vc-own / d_vc-cut) | our note activity (a lower bound for notes and timing) |
| K | ln(d_vc-cut / d_vc-fin) | the cuts themselves (over-stated: `vc-cut` notches every group, amendment 5) |
| F | ln(d_vc-fin / d_true) | the finish (`average_balance` alone, amendment 1) |

T = S + N + K + F exactly, per part, on one passing part set (amendment 3). Beside: N+K = ln(d_vc-own / d_vc-fin)
(the code is marked `cut-sensitive` when it changes with N+K in N's place), E1 = ln(d_tr-di / d_vc-env), E2 =
ln(d_vc-env / d_vc-own), the `avg+mild` floor, Fieller's share S/T, the per-part unclaimed-attack share with S above
and below its median and its Spearman (amendment 2), and N's uncovered frames by cause (amendment 7), with the
cause order swapped beside (`cause-order-sensitive` when the larger route group changes).

A limit: `song_bank.measure` re-fits its EQ to each guitar's own audio, so the gated and notched guitars get their
own re-fit, and N and K also carry the finish's re-fit, not only the gate and the cuts.

    $MAIN -m learn.scratch_voice read      # zero renders, once: the terms, XV_TABLE's code, the figures beside

`XV_TABLE` reads `paired_reading` of S and N on the 40 (BKS+GOAT, all 47 beside), the first that holds; F's reading is
attached to every code. Under XV-sound or XV-both no synthesis, DI-restoration or search-row spend runs before the
unclaimed-groups control (about 188 renders, `phase_scratch_voice_control_outcome`) or the user's waiver
(`phase_scratch_voice_waiver`): `spend_refusal`, `require_spend`.

The builders (`learn/voice_build.py`, Unit B: `build.json` and the four `vc-*` guitars, the proofs, and per part the
figures `unclaimed_groups` and `cover_figures` compute) and the floors (`learn/voice_floors.py`, Unit C: one record a
part, the repeat check on the two check parts) are later units; they write the files and the record shapes declared
here (`build_path`, `dry_path`, `floor_path`, `repeat_path`; the shapes in the plan doc's "Files").

Every command refuses unless this checkout runs main's code (this module, the later units' files, the pinned imports
`PINNED`) and keys (the `phase_scratch_voice*` keys only), and main holds the keys it reads.

The pure parts (`XV_TABLE`, `xv_code`, `xv_read`, the term arithmetic, the passing set, the windows' union, the
coverage and its causes, the unclaimed groups, Spearman, the spend gate, the guards) are tested in
tests/test_scratch_voice.py on the light CI runner (no numpy), on synthetic keys.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import pathlib
import statistics
import subprocess
import time

from learn import note_rebuild as NR
from learn import pretrain_set as PS
from learn import scratch_exact as SE
from learn import scratch_notes as SN
from learn import scratch_search as S

LEDGER_ID = S.LEDGER_ID                  # preset-ladder
PLAN = "docs/scratch-voice-plan.md"
KEY_PREFIX = "phase_scratch_voice"
PHASE = KEY_PREFIX                       # this declaration
PHASE_DRY = f"{KEY_PREFIX}_dry"          # Unit D1's hash PR: build.json's sha256 (zero renders)
PHASE_OUTCOME = f"{KEY_PREFIX}_outcome"  # the audited read
PHASE_CONTROL = f"{KEY_PREFIX}_control"  # the unclaimed-groups control's own declaration (only under XV-sound, XV-both)
PHASE_CONTROL_OUTCOME = f"{KEY_PREFIX}_control_outcome"
PHASE_WAIVER = f"{KEY_PREFIX}_waiver"    # the user's waiver of the control, in the user's words
KEYS_TO_COME = (PHASE_DRY, PHASE_OUTCOME, PHASE_CONTROL, PHASE_CONTROL_OUTCOME, PHASE_WAIVER)
GUARDED_PREFIXES = ("phase_fs", "phase_scratch_notes", "phase_scratch_exact", "phase_scratch_readerr",
                    "phase_scratch_rederive", "phase_scratch_tone", "phase_nr")

MODULE = "learn/scratch_voice.py"
UNIT_FILES = ("learn/voice_build.py", "learn/voice_floors.py")   # Units B and C (absent on both sides until merged)
OWN_FILES = (MODULE,) + UNIT_FILES
PINNED = ("learn/scratch_search.py", "learn/scratch_notes.py", "learn/scratch_exact.py", "learn/note_rebuild.py",
          "learn/note_transcribe.py", "learn/note_replay.py", "learn/pretrain_set.py")   # this module's imports
CODE_FILES = OWN_FILES + PINNED

# --- the guitars, the chain, the terms ------------------------------------------------------------------------------------

TRUE, BANK = "true", SE.BANK_ARM         # the stored real floors (the exact-notes test's floors.json)
OWN, CUT, FIN, ENV_G = "vc-own", "vc-cut", "vc-fin", "vc-env"
AVG_MILD = "avg+mild"                    # beside, stored: row (c)'s dry guitar, rendered at row (b)'s answer
BUILT = (FIN, CUT, OWN, ENV_G)           # Unit B builds these
RENDERED = BUILT + (AVG_MILD,)           # Unit C renders row (b)'s answer through these, 2 renders each
STORED = (TRUE, BANK)
CHAIN = (BANK, OWN, CUT, FIN, TRUE)      # the declared order (amendment 6): S, N, K priced with the finish on
TERMS = (("S", BANK, OWN), ("N", OWN, CUT), ("K", CUT, FIN), ("F", FIN, TRUE))   # (term, numerator, denominator)
TERM_NAMES = tuple(t for t, _, _ in TERMS)
TOTAL = ("T", BANK, TRUE)
BESIDE = (("N+K", OWN, FIN), ("E1", BANK, ENV_G), ("E2", ENV_G, OWN))
ALL_TERMS = TERMS + (TOTAL,) + BESIDE
READ_TERMS = TERM_NAMES + ("T",)         # their readings must all be usable (amendment 4)
PASSING_SET = (TRUE, BANK, FIN, CUT, OWN, ENV_G)   # amendment 3: a part refused in any of the six drops from all
SUM_TOL = 1e-12                          # S + N + K + F = T per part
DECIDING = SE.DECIDING                   # BKS+GOAT, the 40; all 47 beside
SMALL, BIG = S.SMALL, S.BIG              # 0.05, 0.10: they label only (`paired_reading`)
STEM_ROW = SE.STEM_ROW                   # row (b): its stored, hashed answer is rendered through every guitar
SEEN_T = (0.822, 0.714, 0.930)           # T on the 40 (seen; the read must reproduce it to 3 places)
PARTS = sum(S.COUNTS.values())           # 47
CHECK_PARTS = 2                          # the repeat check: the first BKS and the first GOAT part by key
RENDERS = {"floors": len(RENDERED) * PARTS * 2, "repeat": len(STORED) * CHECK_PARTS * 2}   # 470 + 8 = 478
CONTROL_RENDERS = 2 * PARTS * 2          # the unclaimed-groups control: tr-di and vc-own without them, 188

# --- the builders' declared constants (Unit B codes them; every constant an existing one in note_rebuild) --------------

WINDOWS = {                              # vc-own
    "source": "the raw section (pretrain_set.section_audio), float64",
    "lead_s": NR.PRE_ATTACK_S,           # each played note's window opens 2 ms before its onset ...
    "start_fade_s": NR.NOTE_FADE_IN_S,   # ... with a linear fade-in over [on - 2 ms, on] (amendment 6)
    "end": "the note's end in scratch_readerr.played_trace (synthesise_redo's own end), the fade ending there",
    "end_fades_s": {"repluck": NR.REPLUCK_FADE_S, "mute": NR.MUTE_FADE_S, "release": NR.RING_SOFT_S,
                    "sample": NR.TAIL_FADE_S, "cut": NR.REPLUCK_FADE_S},
    "fade_shape": "linear",
    "combine": "maximum, never sum (simultaneous notes are the same audio)",
    "skipped": "notes the synthesis skips open no window",
    "edge_fade_s": NR.EDGE_FADE_S,       # the dry guitar's window edges, as synthesise_redo
    "level": "no per-note gain, tilt, tuning or denoise; one overall gain to -22.9 LUFS, recorded",
    "finish": "the part's own finish p.finish (song_bank.measure, then average_balance), then -22.9 LUFS",
    "chain": "as tr-di's compose (review B1): the raw section on the padded length n + END_PAD_S (the file's real "
             "continuation past n, else zeros, recorded per part), the gate on the padded timeline, the edge fade "
             "(EDGE_FADE_S) at both padded ends, p.finish, cut to n, then -22.9 LUFS; vc-own, vc-cut and vc-fin alike",
    "end_fade": "where any of the pad is zero-filled, the end edge fade ends at the last real sample, zeros after "
                "(the fix to #653's review: the zero pad's hard cut at n re-shaped the finish's EQ); proof 3 and "
                "the length term are read on that gate",
}
NOTCH = {                                # vc-cut
    "source": WINDOWS["source"],
    "where": "every one of our onset groups (note_rebuild.onset_groups), at the group's first onset",
    "fade_out_s": NR.REPLUCK_FADE_S,     # a 10-ms linear fade-out ending at the onset ...
    "fade_in_s": NR.NOTE_FADE_IN_S,      # ... and a 2-ms linear fade-in over [on - 2 ms, on]
    "combine": "maximum of the two (amendment 6): a notch of about -15.6 dB at 1.67 ms before the onset, about 3 ms",
    "finish": WINDOWS["finish"],
    "chain": WINDOWS["chain"],
}
FIN_RULE = {"source": WINDOWS["source"], "finish": WINDOWS["finish"], "chain": WINDOWS["chain"],
            "proof": "the same builder with the pad off and no edge fade (the raw section's n samples, p.finish, "
                     "-22.9 LUFS) equals the stored average-balance DI (note_replay's avg) brought to -22.9 LUFS by "
                     "at_lufs: max |difference| / max |vc-fin| <= FIN_PROOF_TOL (amendment 1, re-declared by review "
                     "B1); the padded vc-fin equals the padded gate path at all-pass byte for byte, both with the end "
                     "fade at the real end (all_pass_is_vc_fin; WINDOWS['end_fade'])",
            "length_term": "beside, per part: the held-half RMS ratio and note_rebuild.logmel_distance (pad-off "
                           "vc-fin the reference side) between the padded and the pad-off vc-fin, the size of the "
                           "length term now inside F"}
FIN_PROOF_TOL = 1e-5
ENV = {                                  # vc-env (beside)
    "from": "tr-di (build 2's, finished, at -22.9 LUFS)",
    "against": "the true DI (note_replay.di_section)",
    "frame_s": NR.MUTE_FRAME_S, "hop_s": NR.MUTE_HOP_S,   # 20-ms RMS levels at a 5-ms hop
    "gain": "per frame the true DI's level less tr-di's, in dB, clipped to +-ORACLE_CLAMP_DB",
    "clamp_db": NR.ORACLE_CLAMP_DB,
    "floor_db": NR.MUTE_FLOOR_DB,        # 0 dB where tr-di's frame is under its own loudest less 40 dB
    "interpolation": "the dB gain linear between frame centres, held before the first and after the last",
    "after": "-22.9 LUFS",
}
PROOFS = ("rule_off_is_tr_di", "trace_is_tr_di_report", "all_pass_is_vc_fin", "vc_fin_is_avg")

# --- the figures beside: coverage, causes, unclaimed groups (amendments 2, 7, 8) -------------------------------------------

SR = NR.SR
TRIM_S = PS.TRIM_S                       # the judge's timeline starts 0.25 s into the section
HALVES = PS.HALVES                       # A 1.0-5.5 s, B 5.5-10.0 s on the trimmed timeline
COVER = {
    "frame": int(round(NR.MUTE_FRAME_S * SR)),   # 960 samples, 20 ms
    "hop": int(round(NR.MUTE_HOP_S * SR)),       # 240 samples, 5 ms
    "playing_floor_db": NR.MUTE_FLOOR_DB,        # a frame plays within 40 dB of the true DI's loudest frame (whole section)
    "levels": "note_rebuild.frame_levels_db of the true DI (note_replay.di_section), the whole section",
    "half": "the part's held half: frame centres in [a + TRIM_S, b + TRIM_S) s of the section (HALVES)",
    "windows": "[on - PRE_ATTACK_S, end] of every played note (played_trace), in samples by round(), clipped",
    "weight": "each playing held-half frame's uncovered sample share (the headline); whole-frame uncovered beside",
}
NEAR_S = NR.TILT_ISOLATED_S              # "nearby": within 600 ms after a window's end (the rebuild's isolation span)
LATE_S = NR.REFINE_S                     # a late onset: one of our windows opens within 50 ms after the frame
CAUSES = ("skipped", "late-onset", "after-release", "after-repluck", "after-mute", "after-sample", "after-cut",
          "no-note")
END_KINDS = ("release", "repluck", "mute", "sample", "cut")   # note_rebuild.note_end's kinds
SYNTH_CAUSES = ("skipped", "after-release", "after-repluck", "after-mute", "after-sample", "after-cut")
READ_CAUSES = ("late-onset", "no-note")
ROUTE = {"synthesis rules": SYNTH_CAUSES, "note reading": READ_CAUSES}
CAUSE_RULE = ("each uncovered piece of a playing held-half frame, at its midpoint, takes the first that holds: "
              "'skipped' (inside a skipped note's [on - 2 ms, max(on, off)]); 'late-onset' (one of our windows opens "
              "within 50 ms after it); 'after-<kind>' (the last window before it ended within 600 ms, by that "
              "window's end kind); 'no-note' (anything else); beside, the same with 'after-<kind>' at any distance, "
              "and the same with the order swapped ('after-<kind>' within 600 ms before 'late-onset'); when the "
              "swapped order names a different larger route group, the route is marked cause-order-sensitive")
CAUSE_ORDER_SENSITIVE = "cause-order-sensitive"
NOT_COMPUTABLE = "not computable"        # a figure beside whose interval or rank correlation cannot be formed
UNCLAIMED = {"groups": "note_rebuild.onset_groups of build 2's notes after its fixes (the whole section)",
             "at": "each group's first onset", "rise": "note_rebuild.rise_curve of the true DI (2-ms frames, 1-ms hop)",
             "window_s": NR.SNAP_S, "min_rise_db": NR.REFINE_MIN_RISE_DB,
             "rule": "unclaimed when no rise of 3 dB or more lies within +-20 ms of the onset "
                     "(hops max(0, int((t - 0.02) * SR) // hop) to int((t + 0.02) * SR) // hop + 1)"}

# --- the outcome table (pure) ------------------------------------------------------------------------------------------------

GATE_NOTE = ("before any synthesis, DI-restoration or search-row spend: the unclaimed-groups control (about "
             f"{CONTROL_RENDERS} renders, its own declaration {PHASE_CONTROL}) or the user's waiver ({PHASE_WAIVER})")
XV_TABLE = (    # (code, when, meaning, next); on the 40, `paired_reading` of S and N, the first that holds
    ("XV-anomaly", "a build proof or the repeat check fails, T does not reproduce from the stored files, the sum "
     "fails on a part, any of S, N, K, F, T has no usable interval or reading, K reads worse or better, or S or N "
     "reads better", "the construction is off", "stop; to the user"),
    ("XV-both", "S reads worse and N reads worse",
     "real audio inside our note windows closes a heard-size part (at most S), and our note activity costs one too "
     "(at least N)",
     "both tracks: N's uncovered frames by cause go to their tracks as named targets ({route}); E1 and E2 say, "
     "loosely, which kind of sound; " + GATE_NOTE),
    ("XV-sound", "S reads worse, N does not read worse",
     "real audio inside our note windows closes at most S; not a sound gap: S also holds every note error the gate "
     "cannot see (extra attacks in true sustain, wrong pitches, bends and articulation, level shaping){dominates}",
     "E1 against E2 (loosely, sustain against spectrum); " + GATE_NOTE + "; then the search row through vc-own "
     "only on its own declaration and the user's go"),
    ("XV-notes", "N reads worse, S does not read worse",
     "our note activity alone costs a heard size under real sound (a lower bound)",
     "by N's cause split ({route}): each cause group to its own track as a named target; candidates may be screened "
     "here at 94 renders each, a screen only (adoption needs the note track's own search row); no synthesis spend"),
    ("XV-undecided", "anything else", "not split at the floor; undecided is not failed",
     "{finish}"),
)
XV_CODES = tuple(c for c, *_ in XV_TABLE)
XV_DECLARED = ("XV-anomaly", "XV-both", "XV-sound", "XV-notes", "XV-undecided")
CHECKS = ("proofs", "repeat", "t_reproduces", "sum_holds")
SPEND_CODES = ("XV-sound", "XV-both")    # the codes under which the control (or the waiver) gates any spend
SPEND_KINDS = ("synthesis", "di-restoration", "search-row")
CUT_SENSITIVE = "cut-sensitive"


def iv_ok(iv):
    """(Pure.) A usable 90% interval: finite mean, lo90 and hi90, lo90 <= hi90."""
    if not isinstance(iv, dict):
        return False
    try:
        m, lo, hi = (float(iv[k]) for k in ("mean", "lo90", "hi90"))
    except (KeyError, TypeError, ValueError):
        return False
    return all(math.isfinite(x) for x in (m, lo, hi)) and lo <= hi


def reading(iv):
    """(Pure.) `scratch_notes.paired_reading` of a usable interval, else None."""
    return SN.paired_reading(iv) if iv_ok(iv) else None


def _r(iv):
    return (reading(iv) or {}).get("reading")


def table_guard():
    """Refuse unless XV_TABLE holds its declared codes in order, its last row is literally "anything else", 0 < SMALL
    < BIG and the key prefix sits outside every guarded prefix."""
    if XV_CODES != XV_DECLARED:
        raise SystemExit("XV_TABLE's codes are not the five declared, in order")
    if XV_TABLE[-1][1] != "anything else":
        raise SystemExit("XV_TABLE's last row is not 'anything else'")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")
    if not KEY_PREFIX.startswith("phase_scratch_") or KEY_PREFIX.startswith(GUARDED_PREFIXES):
        raise SystemExit(f"{KEY_PREFIX} sits under a guarded prefix")


def anomaly_why(ivs, checks):
    """(Pure.) Why XV-anomaly holds, or None. ivs: {S, N, K, F, T: interval}; checks: {CHECKS: bool}."""
    for c in CHECKS:
        if (checks or {}).get(c) is not True:
            return f"the check {c} does not hold"
    for t in READ_TERMS:
        if reading((ivs or {}).get(t)) is None:
            return f"{t} has no usable interval or reading"
    if _r(ivs["K"]) in ("worse", "better"):
        return f"K reads {_r(ivs['K'])}"
    for t in ("S", "N"):
        if _r(ivs[t]) == "better":
            return f"{t} reads better"
    return None


def route_text(route):
    """(Pure.) N's cause split as words: each group's pooled share of N's uncovered frames, the larger first."""
    if not isinstance(route, dict) or not route.get("shares"):
        return "N's cause split not available"
    sh = route["shares"]
    parts = [f"{g} {sh[g]:.0%} ({', '.join(ROUTE[g])})" for g in sorted(sh, key=lambda g: (-sh[g], g))]
    text = "; ".join(parts)
    sw = route.get("swapped_shares")
    if route.get("order_label") and sw:
        text += (f" ({CAUSE_ORDER_SENSITIVE}: with the order swapped, "
                 + "; ".join(f"{g} {sw[g]:.0%}" for g in sorted(sw, key=lambda g: (-sw[g], g))) + ")")
    return text


def xv_code(ivs, checks, route=None):
    """(Pure.) XV_TABLE's one code, the first that holds, on the 40: `paired_reading` of S and N; F's reading attached.
    ivs: {S, N, K, F, T: interval}; checks: {proofs, repeat, t_reproduces, sum_holds: bool}; route: N's cause split
    (`route_split`), worded into Next. -> dict."""
    ivs = dict(ivs or {})
    why = anomaly_why(ivs, checks)
    rs, rn = _r(ivs.get("S")), _r(ivs.get("N"))
    if why:
        code = "XV-anomaly"
    elif rs == "worse" and rn == "worse":
        code = "XV-both"
    elif rs == "worse":
        code = "XV-sound"
    elif rn == "worse":
        code = "XV-notes"
    else:
        code = "XV-undecided"                              # anything else
    row = next(r for r in XV_TABLE if r[0] == code)
    rf = _r(ivs.get("F"))
    dominates = code == "XV-sound" and rn == "matches"
    meaning = row[2].format(dominates="; it dominates (N reads matches)" if dominates else
                            ("; 'dominates' only if N reads matches" if code == "XV-sound" else ""))
    fin = ("F reads worse: the finish holds it, and the held fs-tone question returns to the user" if rf == "worse"
           else "to the user with the numbers")
    nxt = row[3].format(route=route_text(route), finish=fin)
    return {"code": code, "when": row[1], "meaning": meaning, "next": nxt, "anomaly": why,
            "readings": {t: reading(ivs.get(t)) for t in READ_TERMS},
            "F": {"iv": ivs.get("F"), "reading": rf}, "dominates": dominates,
            "spend_gated": code in SPEND_CODES}


def xv_read(ivs, checks, nk_iv, route=None):
    """(Pure.) The deciding code, and beside it the code with N+K in N's place (amendment 5): `cut-sensitive` when the
    two differ. -> dict."""
    code = xv_code(ivs, checks, route)
    alt = xv_code(dict(ivs or {}, N=nk_iv), checks, route)
    return dict(code, with_n_plus_k=alt["code"], label=CUT_SENSITIVE if alt["code"] != code["code"] else None)


def with_itt(read_passing, read_itt, refused):
    """(Pure.) S1 here: the deciding read is passing-only (one part set, amendment 3); with refusals, the
    intent-to-treat read (`itt_values`, a refused part at 0.0) sits beside and the code is `refusal-sensitive` when the
    two codes differ. -> (deciding record, itt record or None, label or None)."""
    if not refused:
        return read_passing, None, None
    lab = S.REFUSAL_SENSITIVE if (read_itt or {}).get("code") != read_passing["code"] else None
    return read_passing, read_itt, lab


# --- the term arithmetic (pure) --------------------------------------------------------------------------------------------

def finite_pos(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def part_terms(d):
    """(Pure.) One part's terms from its floors d ({guitar: held distance}): every ln(num / den) of ALL_TERMS, None
    where either floor is missing, zero or non-finite."""
    out = {}
    for t, a, b in ALL_TERMS:
        x, y = (d or {}).get(a), (d or {}).get(b)
        out[t] = math.log(x / y) if finite_pos(x) and finite_pos(y) else None
    return out


def passing(d):
    """(Pure.) Whether a part passes: every floor of PASSING_SET finite and positive."""
    return all(finite_pos((d or {}).get(g)) for g in PASSING_SET)


def sum_gap(t):
    """(Pure.) |S + N + K + F - T| of one part's terms, or None."""
    xs = [t.get(n) for n in TERM_NAMES + ("T",)]
    if any(x is None for x in xs):
        return None
    return abs(sum(xs[:-1]) - xs[-1])


def term_values(floors):
    """(Pure.) floors: {pkey: {guitar: held}}. -> (passing values {term: {pkey: value}}, refused {pkey: reason},
    per-part sum gaps on the passing set). One passing set for every term (amendment 3)."""
    vals = {t: {} for t, _, _ in ALL_TERMS}
    refused, gaps = {}, {}
    for k in sorted(floors):
        d = floors[k]
        if not passing(d):
            bad = [g for g in PASSING_SET if not finite_pos((d or {}).get(g))]
            refused[k] = f"no finite positive floor for {', '.join(bad)}"
            continue
        t = part_terms(d)
        for n, v in t.items():
            vals[n][k] = v
        gaps[k] = sum_gap(t)
    return vals, refused, gaps


def itt_terms(vals, refused):
    """(Pure.) The intent-to-treat values beside: each term's passing values with every refused part at 0.0
    (`scratch_search.itt_values`)."""
    return {t: S.itt_values(v, refused) for t, v in vals.items()}


def sum_holds(gaps, tol=SUM_TOL):
    return bool(gaps) and all(g is not None and g <= tol for g in gaps.values())


# --- coverage and its causes (pure; Unit B hands in the levels, the trace and the rise curve) ------------------------------

def played_windows(notes, trace, n, rate=SR):
    """(Pure.) Our played windows in samples: [round((on - PRE_ATTACK_S) * rate), round(end * rate)) clipped to [0, n),
    with the note's end kind; and the skipped notes' spans [on - PRE_ATTACK_S, max(on, off)]. notes, trace: the note
    list and `played_trace`'s per-note records, in order. -> (windows [(a, b, kind)], skipped [(a, b)])."""
    win, skip = [], []
    for nt, tr in zip(notes, trace):
        a = max(0, int(round((nt["on"] - NR.PRE_ATTACK_S) * rate)))
        if tr.get("played"):
            b = min(n, int(round(tr["end"] * rate)))
            if b > a:
                win.append((a, b, tr.get("end_kind")))
        else:
            b = min(n, int(round(max(nt["on"], nt["off"]) * rate)))
            if b > a:
                skip.append((a, b))
    return win, skip


def union(windows):
    """(Pure.) The union of windows [(a, b, kind)] as sorted, disjoint [a, b, kind] pieces; a piece's kind is that of
    the window reaching its end (the first such in start order)."""
    out = []
    for a, b, kind in sorted(windows, key=lambda w: (w[0], w[1])):
        if out and a <= out[-1][1]:
            if b > out[-1][1]:
                out[-1][1], out[-1][2] = b, kind
        else:
            out.append([a, b, kind])
    return out


def uncovered_pieces(lo, hi, merged, starts):
    """(Pure.) [lo, hi) less the union: [(a, b, left piece index or None, right piece index or None)]."""
    out, x = [], lo
    i = max(0, bisect.bisect_right(starts, lo) - 1)
    while x < hi:
        while i < len(merged) and merged[i][1] <= x:
            i += 1
        if i < len(merged) and merged[i][0] <= x:
            x = merged[i][1]
            continue
        nxt = merged[i][0] if i < len(merged) else hi
        b = min(hi, nxt)
        out.append((x, b, i - 1 if i > 0 else None, i if i < len(merged) else None))
        x = b
    return out


def cause_of(mid, left, right, skipped, near=True, rate=SR, swapped=False):
    """(Pure.) The cause of an uncovered piece at sample `mid` (CAUSE_RULE). left, right: the union pieces before and
    after ([a, b, kind] or None). The declared order decides: skipped, late onset, after an end, no note nearby;
    `swapped` (beside, the review's fix 1) checks after an end before late onset."""
    if any(a <= mid <= b for a, b in skipped):
        return "skipped"
    late = right is not None and right[0] - mid <= LATE_S * rate
    after = left is not None and (not near or mid - left[1] <= NEAR_S * rate)
    if after and left[2] not in END_KINDS:
        raise ValueError(f"unknown end kind {left[2]!r}")
    for step in (("after", "late") if swapped else ("late", "after")):
        if step == "late" and late:
            return "late-onset"
        if step == "after" and after:
            return f"after-{left[2]}"
    return "no-note"


def held_frames(levels_db, held, frame=COVER["frame"], hop=COVER["hop"], rate=SR, floor_db=COVER["playing_floor_db"]):
    """(Pure.) The playing frames of the held half: indices whose level is within floor_db of the loudest (the whole
    section) and whose centre lies in [a + TRIM_S, b + TRIM_S) s."""
    if not len(levels_db):
        return []
    top = max(levels_db)
    a, b = HALVES[held]
    lo, hi = (a + TRIM_S) * rate, (b + TRIM_S) * rate
    return [i for i, v in enumerate(levels_db) if v >= top - floor_db and lo <= i * hop + frame / 2 < hi]


def cover_figures(levels_db, windows, skipped, held, frame=COVER["frame"], hop=COVER["hop"], rate=SR):
    """(Pure.) The uncovered figure (amendment 8's definition, COVER) and N's causes (amendment 7, CAUSE_RULE) on one
    part. levels_db: the true DI's 20-ms levels at the 5-ms hop; windows, skipped: `played_windows`. -> dict."""
    frames = held_frames(levels_db, held, frame, hop, rate)
    merged = union(windows)
    starts = [m[0] for m in merged]
    by, by_any, by_sw = ({c: 0.0 for c in CAUSES} for _ in range(3))
    w_sum, whole = 0.0, 0
    for i in frames:
        lo, hi = i * hop, i * hop + frame
        pcs = uncovered_pieces(lo, hi, merged, starts)
        unc = sum(b - a for a, b, _, _ in pcs)
        w_sum += unc / frame
        whole += unc == frame
        for a, b, li, ri in pcs:
            mid = (a + b) / 2
            left = merged[li] if li is not None else None
            right = merged[ri] if ri is not None else None
            by[cause_of(mid, left, right, skipped, True, rate)] += (b - a) / frame
            by_any[cause_of(mid, left, right, skipped, False, rate)] += (b - a) / frame
            by_sw[cause_of(mid, left, right, skipped, True, rate, swapped=True)] += (b - a) / frame
    n = len(frames)
    return {"frames": n, "uncovered_weight": w_sum, "uncovered_share": w_sum / n if n else None,
            "whole_frame_share": whole / n if n else None, "by_cause": by, "by_cause_any_distance": by_any,
            "by_cause_swapped": by_sw}


def unclaimed_groups(onsets, rise, hop, rate=SR, window=NR.SNAP_S, min_rise=NR.REFINE_MIN_RISE_DB):
    """(Pure.) Amendment 2's figure on one part: the onset groups (their first onsets, seconds) with no true-DI rise
    of `min_rise` dB or more within +-`window` (UNCLAIMED's hops). rise: `rise_curve`'s values. -> dict."""
    flags = []
    for t in onsets:
        lo = max(0, int((t - window) * rate) // hop)
        hi = min(len(rise), int((t + window) * rate) // hop + 1)
        flags.append(hi <= lo or float(max(rise[lo:hi])) < min_rise)
    n = len(flags)
    return {"groups": n, "unclaimed": sum(flags), "share": sum(flags) / n if n else None, "flags": flags}


def leading(shares):
    """(Pure.) The route group with the larger share (ties by name), or None."""
    return min(shares, key=lambda g: (-shares[g], g)) if shares else None


def route_order(route, swapped):
    """(Pure.) The deciding route with the swapped order's split beside (the review's fix 1): `cause-order-sensitive`
    when the two name a different larger group, no threshold; both orders' shares kept. -> route dict."""
    out = dict(route or {}, swapped_shares=(swapped or {}).get("shares"), order_label=None)
    a, b = leading((route or {}).get("shares")), leading((swapped or {}).get("shares"))
    if a is not None and b is not None and a != b:
        out["order_label"] = CAUSE_ORDER_SENSITIVE
    return out


def route_split(cover_by_part, keys, field="by_cause"):
    """(Pure.) N's uncovered frames pooled over `keys` by cause and by route group (ROUTE). -> dict."""
    tot = {c: 0.0 for c in CAUSES}
    for k in keys:
        for c, w in ((cover_by_part.get(k) or {}).get(field) or {}).items():
            tot[c] = tot.get(c, 0.0) + w
    s = sum(tot.values())
    if s <= 0:
        return {"by_cause": tot, "shares": None, "total_weight": s}
    return {"by_cause": tot, "cause_shares": {c: w / s for c, w in tot.items()}, "total_weight": s,
            "shares": {g: sum(tot[c] for c in cs) / s for g, cs in ROUTE.items()}}


def ranks(xs):
    """(Pure.) Average ranks (1-based), ties sharing their mean rank."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for q in range(i, j + 1):
            r[order[q]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    """(Pure.) Spearman's rho of two paired lists (Pearson on average ranks), or None under 3 pairs or with no spread."""
    if len(a) != len(b) or len(a) < 3:
        return None
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    va = sum((x - ma) ** 2 for x in ra)
    vb = sum((y - mb) ** 2 for y in rb)
    if va == 0 or vb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(va * vb)


def median_split(share, keys):
    """(Pure.) Amendment 2's split: the keys whose unclaimed share lies above its median over `keys`, and the rest (at
    or below; a part with no share is left out). -> (above, at_or_below, median)."""
    ks = [k for k in keys if share.get(k) is not None]
    if not ks:
        return [], [], None
    med = statistics.median([share[k] for k in ks])
    return sorted(k for k in ks if share[k] > med), sorted(k for k in ks if share[k] <= med), med


def tag(pk):
    """(Pure.) A part's public 12-hex tag (git gets no part keys)."""
    return hashlib.sha256(pk.encode()).hexdigest()[:12]


def largest(vals, keys, n=3):
    """(Pure.) The n keys with the largest |value| among `keys`, largest first (ties by key)."""
    ks = [k for k in keys if vals.get(k) is not None]
    return sorted(ks, key=lambda k: (-abs(vals[k]), k))[:n]


def check_parts(parts):
    """(Pure.) The repeat check's two parts: the first BKS and the first GOAT part by key. parts: [{pkey, set}]."""
    out = []
    for st in SN.CHECK_SETS:
        ks = sorted(p["pkey"] for p in parts if p["set"] == st)
        if ks:
            out.append(ks[0])
    return out


# --- the spend gate (amendment 2) --------------------------------------------------------------------------------------------

def spend_refusal(entry, kind):
    """(Pure.) Why a synthesis, DI-restoration or search-row spend may not run on this test's account, or None. entry:
    main's `preset-ladder` entry. Under XV-sound or XV-both it needs the control's audited outcome or the user's
    waiver (with the user's words and the date); under XV-notes no synthesis or DI-restoration spend at all; without
    the audited outcome, nothing. Holding is necessary, not sufficient: the search row needs its own declaration and
    the user's go."""
    if kind not in SPEND_KINDS:
        raise ValueError(kind)
    out = (entry or {}).get(PHASE_OUTCOME)
    code = out.get("code") if isinstance(out, dict) else None
    if code is None:
        return f"main has no {PHASE_OUTCOME} code: the read and its audit first"
    if code == "XV-notes" and kind != "search-row":
        return "XV-notes: no synthesis spend"
    if code not in SPEND_CODES:
        return f"{code}: no spend on this test's account; to the user"
    ctl = (entry or {}).get(PHASE_CONTROL_OUTCOME)
    if isinstance(ctl, dict) and ctl.get("code"):          # the control's audited outcome carries its code
        return None
    w = (entry or {}).get(PHASE_WAIVER)
    if isinstance(w, dict) and w.get("user_words") and w.get("date"):
        return None
    return f"{code}: " + GATE_NOTE + " must be on main first"


def require_spend(kind):
    """Refuse a spend unless main's entry opens it (`spend_refusal`). -> main's entry."""
    m, why = on_main()
    if why:
        raise SystemExit(why)
    why = spend_refusal(m, kind)
    if why:
        raise SystemExit(why)
    return m


# --- the guards -------------------------------------------------------------------------------------------------------------

def voice_keys(entry):
    """(Pure.) This test's own keys of a `preset-ladder` entry."""
    return {k: v for k, v in (entry or {}).items() if k.startswith(KEY_PREFIX)}


def keys_refusal(local, main):
    """(Pure.) Why this checkout's `phase_scratch_voice*` keys are not main's, or None (its own keys only)."""
    a, b = voice_keys(local), voice_keys(main)
    if a != b:
        return f"this checkout's {sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))} differ from main's"
    return None


def _git(*a):
    from learn import pipeline_fix as P

    return subprocess.run(["git", "-C", str(P.REPO), *a], capture_output=True, text=True)


def pinned_identity():
    """Each of CODE_FILES equal to origin/main's (git diff --quiet; a later unit's file absent on both sides is
    equal). -> {file: same}."""
    return {f: _git("diff", "--quiet", "origin/main", "--", f).returncode == 0 for f in CODE_FILES}


def main_entry():
    """main's `preset-ladder` entry (origin/main after a fetch), or (None, refusal)."""
    from learn import note_replay as NRP

    _git("fetch", "-q", "origin", "main")
    led = _git("show", "origin/main:docs/dev-test-ledger.json")
    if led.returncode:
        return None, f"main's ledger is not readable: {led.stderr.strip()}"
    return NRP.main_entry(led.stdout), None


def on_main():
    """main's entry and whether this checkout runs main's code (CODE_FILES) and its own keys. -> (entry, refusal)."""
    from learn import note_replay as NRP

    m, why = main_entry()
    if why:
        return None, why
    bad = [f for f, ok in pinned_identity().items() if not ok]
    if bad:
        return m, f"this checkout's {bad} differ from main's: run from merged code"
    why = keys_refusal(NRP.ledger_entry(), m)
    return m, why


def require_voice(*phases):
    """Refuse unless the table holds, this checkout runs main's code and keys, and main holds the draw, row (b)'s
    answers, the exact-notes test's floors, this declaration and `phases`. -> main's `preset-ladder` entry."""
    table_guard()
    m, why = on_main()
    if why:
        raise SystemExit(why)
    for k in (S.PHASE_DRAW, S.phase_answers(STEM_ROW), SE.PHASE_TARGETS, PHASE) + tuple(phases):
        if not m or k not in m:
            raise SystemExit(f"main's {LEDGER_ID} entry has no {k}: merge it before running")
    return m


# --- paths --------------------------------------------------------------------------------------------------------------------

def voice_dir():
    return S.fs_dir() / "voice"


def build_path():
    """Unit B's record (build.json): the proofs and, per part, every built guitar's sha256 and the figures beside."""
    return voice_dir() / "build.json"


def dry_path(guitar, pk):
    if guitar not in BUILT:
        raise ValueError(guitar)
    return voice_dir() / "dry" / guitar / f"{SE._f(pk)}.npy"


def floor_path(pk):
    """Unit C's floor record of a part (every rendered guitar's held distance)."""
    return voice_dir() / "floors" / f"{SE._f(pk)}.json"


def repeat_path(pk):
    """Unit C's repeat check on a check part (tr-di and the true DI against their stored floors)."""
    return voice_dir() / "repeat" / f"{SE._f(pk)}.json"


def rows_path():
    return voice_dir() / "rows.json"


def report_path():
    return voice_dir() / "report.json"


# --- the read -----------------------------------------------------------------------------------------------------------------

def close3(iv, seen):
    return iv_ok(iv) and all(round(iv[q], 3) == v for q, v in zip(("mean", "lo90", "hi90"), seen))


def floors_of(stored, floor_recs):
    """Per part {guitar: held} from the stored real floors (true, tr-di) and Unit C's records. A refused render's
    floor is None with its reason; a stored floor that is not finite and positive is None with an explicit reason.
    Refuses (SystemExit) a Unit C record that sets any guitar but the rendered ones (never the stored true or tr-di),
    or whose floor is missing, non-finite or not positive without a `refused` flag: a malformed record is never read
    as a refusal. -> ({pkey: {guitar: held or None}}, {pkey: {guitar: reason}})."""
    out, why = {}, {}
    for k, st in stored.items():
        d = {}
        for g in STORED:
            h = (st.get(g) or {}).get("held")
            d[g] = h if finite_pos(h) else None
            if d[g] is None:
                why.setdefault(k, {})[g] = f"the stored {g} floor is not finite and positive ({h!r})"
        for g, r in ((floor_recs.get(k) or {}).get("guitars") or {}).items():
            if g not in RENDERED:
                raise SystemExit(f"part {tag(k)}: a floor record sets {g!r}, not one of the rendered guitars")
            if r.get("refused"):
                d[g] = None
                why.setdefault(k, {})[g] = r["refused"]
            elif finite_pos(r.get("held")):
                d[g] = r["held"]
            else:
                raise SystemExit(f"part {tag(k)}: {g}'s floor {r.get('held')!r} is not finite and positive and is "
                                 "not marked refused: a malformed floor record, to the user")
        out[k] = d
    return out, why


def pending_reruns(floor_recs):
    """(Pure.) Refused renders not yet rerun once (S1): [(pkey, guitar)]."""
    return sorted((k, g) for k, r in floor_recs.items() for g, x in ((r or {}).get("guitars") or {}).items()
                  if x.get("refused") and not x.get("reran"))


def t_reproduces(stored, iv40, stored_iv):
    """(Pure.) T from the stored files: per part ln(tr-di / true) equal to the stored `tr_di_less_true`, the 40's
    interval equal to the stored read's and to SEEN_T to 3 places. -> {per_part, stored, seen, holds}."""
    per = all(st.get("tr_di_less_true") == part_terms({TRUE: (st.get(TRUE) or {}).get("held"),
                                                       BANK: (st.get(BANK) or {}).get("held")})["T"]
              for st in stored.values())
    exact = iv_ok(iv40) and iv_ok(stored_iv) and all(iv40[q] == stored_iv[q] for q in ("mean", "lo90", "hi90"))
    seen = close3(iv40, SEEN_T)
    return {"per_part": per, "stored": exact, "seen": seen, "holds": per and exact and seen, "iv": iv40}


def read_body(vals, refused, gaps, iv_fn, deciding, clusters, share, cover, checks, share_fn=None):
    """(Pure but for `iv_fn` and `share_fn`.) The read on one passing set: each term's interval on the 40
    (`iv_fn(values, keys)`, BKS+GOAT's pool), XV_TABLE's code with N+K beside (`cut-sensitive`), the intent-to-treat
    code beside (`refusal-sensitive`), each cluster of the 40 left out, the three largest parts' contributions, S above
    and below the unclaimed share's median and its Spearman, N's cause split, Fieller's S/T. vals: {term: {pkey:
    value}} on the passing parts; deciding: the 40's keys; clusters: [[pkey]] of the 40; share: {pkey: unclaimed
    share}; cover: {pkey: cover_figures}. -> dict."""
    dec = sorted(k for k in deciding if k not in refused)
    ivs = {t: iv_fn(v, None) for t, v in vals.items()}
    route = route_order(route_split(cover, dec), route_split(cover, dec, "by_cause_swapped"))
    code = xv_read({t: ivs.get(t) for t in READ_TERMS}, checks, ivs.get("N+K"), route)
    itt = itt_terms(vals, refused)
    itt_ivs = {t: iv_fn(v, None) for t, v in itt.items()}
    itt_code = xv_read({t: itt_ivs.get(t) for t in READ_TERMS}, checks, itt_ivs.get("N+K"), route)
    code, itt_rec, s1 = with_itt(code, itt_code, refused)
    left = {t: [iv_fn(vals[t], set(dec) - set(c)) for c in clusters] for t in READ_TERMS}
    rng = {t: ([min(x["mean"] for x in v if iv_ok(x)), max(x["mean"] for x in v if iv_ok(x))]
               if any(iv_ok(x) for x in v) else None) for t, v in left.items()}
    big = {}
    for t in READ_TERMS:
        top = largest(vals[t], dec)
        big[t] = {"tags": [tag(k) for k in top], "values": [vals[t][k] for k in top],
                  "contribution": iv_fn({k: (v if k in top else 0.0) for k, v in vals[t].items()}, None),
                  "without": iv_fn(vals[t], set(dec) - set(top))}
    above, below, med = median_split(share, dec)
    ks = [k for k in dec if share.get(k) is not None and vals["S"].get(k) is not None]
    def sub(keys_):
        iv = iv_fn(vals["S"], set(keys_)) if keys_ else None
        return iv if iv_ok(iv) else NOT_COMPUTABLE
    rho = spearman([share[k] for k in ks], [vals["S"][k] for k in ks])
    unclaimed = {"median_share": med, "above": len(above), "at_or_below": len(below),
                 "S_above": sub(above), "S_at_or_below": sub(below),
                 "spearman_with_S": NOT_COMPUTABLE if rho is None else rho, "spearman_parts": len(ks),
                 "label": "beside, not decided (amendment 2)"}
    return {"passing_parts_on_the_40": len(dec), "refused": sorted(tag(k) for k in refused), "terms": ivs,
            "readings": {t: reading(ivs.get(t)) for t in ivs}, "code": code["code"], "xv": code,
            "mean_sum_gap": (abs(sum(ivs[t]["mean"] for t in TERM_NAMES) - ivs["T"]["mean"])
                             if all(iv_ok(ivs.get(t)) for t in READ_TERMS) else None),
            "itt": {"terms": {t: itt_ivs.get(t) for t in READ_TERMS}, "xv": itt_rec} if itt_rec else None,
            "label": s1, "cut_label": code.get("label"), "sum_max_gap": max((g for g in gaps.values()
                                                                             if g is not None), default=None),
            "cluster_left_out": left, "cluster_left_out_range": rng, "largest_three": big, "unclaimed": unclaimed,
            "route": route, "route_any_distance": route_split(cover, dec, "by_cause_any_distance"),
            "route_swapped": route_split(cover, dec, "by_cause_swapped"), "route_label": route.get("order_label"),
            "share_S_of_T": share_fn(vals["S"], vals["T"]) if share_fn else None}


def _stored_floors(m):
    """The exact-notes test's floors.json, refused unless its sha256 is main's phase_scratch_exact_targets
    floors_sha256. -> (per-part real floors, the stored read of T on the 40)."""
    p = SE.floors_path()
    if not p.exists():
        raise SystemExit("no exact-notes floors.json")
    why = SE.field_refusal(m, SE.PHASE_TARGETS, "floors_sha256", S.file_sha(p))
    if why:
        raise SystemExit(why)
    fl = json.loads(p.read_text())
    return fl["floors_real"], ((fl["read"]["real"]["tr_di_less_true"] or {}).get("bks_goat") or {}).get("all")


def _build(m):
    from learn import note_transcribe as NT

    if not build_path().exists():
        raise SystemExit("no build.json (Unit B's build first)")
    return NT.require_file_hash(m, PHASE_DRY, build_path())


def cmd_read(_args):
    """The read (zero renders), once: build.json (main's phase_scratch_voice_dry), the stored real floors
    (phase_scratch_exact_targets), every part's floor record (each guitar's dry sha256 the build's) and the repeat
    check; T reproduced from the stored files; the terms on one passing set; XV_TABLE's code with N+K, S1 and F's
    reading; the figures beside. The rows are saved before the code. -> rows.json, report.json."""
    m = require_voice(PHASE_DRY)
    from learn import note_transcribe as NT
    from learn import pipeline_fix as P

    for p_ in (rows_path(), report_path()):
        NT.never_overwrite(p_)
    build = _build(m)
    stored, stored_iv = _stored_floors(m)
    draw, sd = SE.context()
    keys = sorted(p["pkey"] for p in draw["parts"])
    if sorted(stored) != keys or sorted(build["parts"]) != keys:
        raise SystemExit("the stored floors or the build do not cover the draw's parts")
    recs = {}
    for k in keys:
        if not floor_path(k).exists():
            raise SystemExit(f"part {tag(k)}: no floor record (Unit C's floors first)")
        recs[k] = json.loads(floor_path(k).read_text())
        for g in RENDERED:
            r = (recs[k].get("guitars") or {}).get(g)
            if not r or r.get("dry_sha256") != build["parts"][k]["guitars"][g]["audio_sha256"]:
                raise SystemExit(f"part {tag(k)}: {g}'s floor was not rendered from the build's guitar")
    pend = pending_reruns(recs)
    if pend:
        raise SystemExit(f"{len(pend)} refused render(s) not rerun once: Unit C's --rerun first")
    reps = {k: json.loads(repeat_path(k).read_text()) if repeat_path(k).exists() else None
            for k in check_parts(draw["parts"])}

    def iv_fn(vals, ks=None):
        r = SN.set_rows(sd, draw, {k: v for k, v in vals.items() if v is not None and math.isfinite(v)}, ks)
        return ((r or {}).get("bks_goat") or {}).get("all")

    def share_fn(num, den):
        return SE.share(sd, draw, num, den)

    tr = t_reproduces(stored, iv_fn({k: st.get("tr_di_less_true") for k, st in stored.items()}), stored_iv)
    floors, refused_why = floors_of(stored, recs)
    vals, refused, gaps = term_values(floors)
    checks = {"proofs": build.get("proofs_hold") is True, "repeat": all(r and r.get("holds") for r in reps.values())
              and len(reps) == CHECK_PARTS, "t_reproduces": tr["holds"], "sum_holds": sum_holds(gaps)}
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    deciding = [k for k in keys if sets_of[k] in DECIDING]
    clusters = {}
    for p in draw["parts"]:
        if p["set"] in DECIDING:
            clusters.setdefault(p["cluster"], []).append(p["pkey"])
    share = {k: (build["parts"][k].get("unclaimed") or {}).get("share") for k in keys}
    cover = {k: build["parts"][k].get("cover") for k in keys}
    body = read_body(vals, refused, gaps, iv_fn, deciding, [sorted(v) for _, v in sorted(clusters.items())], share,
                     cover, checks, share_fn)
    beside = {"all_47": {t: ((SN.set_rows(sd, draw, v) or {}).get("deciding_pool")) for t, v in vals.items()},
              "clean": {t: (((SN.set_rows(sd, draw, v) or {}).get("bks_goat") or {}).get("clean")) for t, v in
                        vals.items()},
              "crunch": {t: (((SN.set_rows(sd, draw, v) or {}).get("bks_goat") or {}).get("crunch")) for t, v in
                         vals.items()},
              "avg_mild_less_true": iv_fn({k: part_terms_pair(floors[k], AVG_MILD, TRUE) for k in keys}),
              "avg_mild_less_tr_di": iv_fn({k: part_terms_pair(floors[k], AVG_MILD, BANK) for k in keys}),
              "sample_ends": sum(((build["parts"][k].get("ends") or {}).get("sample") or 0) for k in keys),
              "uncovered_share_median_40": _median([(cover.get(k) or {}).get("uncovered_share") for k in deciding])}
    common = {"plan": PLAN, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0, "checks": checks,
              "t_reproduced": tr, "build_sha256": S.file_sha(build_path()),
              "refused_why": {tag(k): v for k, v in refused_why.items()},
              "refusal_report": S.refusal_report({tag(k): refused_why.get(k) or {"floor": refused[k]} for k in refused},
                                                 {tag(k): v for k, v in sets_of.items()}, DECIDING),
              "floors_sha256": {tag(k): S.file_sha(floor_path(k)) for k in keys}}
    rows = dict(common, rows={"terms": body["terms"], "beside": beside, "per_part": {
        t: {tag(k): v for k, v in vs.items()} for t, vs in vals.items()}})
    P.save(rows_path(), rows)                            # the rows are saved before the code is read
    report = dict(common, read=body, beside=beside)
    P.save(report_path(), report)
    for t in READ_TERMS:
        print(f"{t} on the 40: {body['terms'].get(t)} -> {(body['readings'].get(t) or {}).get('reading')}")
    lab = ", ".join(x for x in (body["label"], body["cut_label"]) if x)
    print(f"XV READ: {body['code']}{' (' + lab + ')' if lab else ''}; F reads {body['xv']['F']['reading']}; next: "
          f"{body['xv']['next']}; sha256 {S.file_sha(report_path())}")


def part_terms_pair(d, a, b):
    x, y = (d or {}).get(a), (d or {}).get(b)
    return math.log(x / y) if finite_pos(x) and finite_pos(y) else None


def _median(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return statistics.median(xs) if xs else None


COMMANDS = {"read": cmd_read}


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
