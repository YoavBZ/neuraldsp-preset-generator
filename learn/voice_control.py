"""The unclaimed-groups control of the sound-gap test (`docs/scratch-voice-plan.md`, "The unclaimed-groups control";
ledger `preset-ladder` `phase_scratch_voice_control`, then the hash PR `phase_scratch_voice_control_dry` with
build.json's sha256, then `phase_scratch_voice_control_outcome`). The sound-gap read was XV-both: S = ln(d_tr-di /
d_vc-own) +0.501 [+0.399, +0.603] on the 40, by the score. This control measures how much of S our unclaimed onset
groups hold (the groups with no true-DI rise of 3 dB within +-20 ms, `scratch_voice.unclaimed_groups`), so the sound
routes are priced against the right figure; its outcome opens the spend gate (`scratch_voice.spend_refusal`).

**The drop rule, one for both guitars** (the orchestrator's call: "drops" literally). The flags are build.json's
`unclaimed.flags` (hashed in `phase_scratch_voice_dry`), recomputed and required equal. A dropped note is any note of
a flagged onset group; dropped notes are not played in either guitar. Every other note keeps its placement, source,
variety, bend, tilt, end and gain (the shared trace is `tr-di`'s), so kept notes a dropped pluck re-plucks stay cut.

| Guitar | Rule |
|---|---|
| `tr-uc` | `scratch_rederive.compose`'s chain (`_synth`, `denoise_above`, then `voice_build.chain`: the finish, cut to n, -22.9 LUFS) on the same notes, bank, ring, loudness option, finish and T, with the dropped groups' levels at -inf dB (10^(-inf/20) = 0: the dropped notes add exactly zero). No new synthesis code |
| `vc-uc` | `voice_build`'s gate path on the same padded raw section, with the dropped notes' trace records marked not played: they open no window. The same padded chain, end fade (`real_end`), `p.finish` and -22.9 LUFS |

T (tuning, mutes, tilt and the kept groups' levels) is not re-fitted. The counterfactual is declared with its whole
signal steps (the control's review, amendment 1): on `tr-uc` the hiss removal (`denoise_above`), the finish's EQ re-fit
and the -22.9 LUFS step run again on the guitar without the dropped notes; on `vc-uc` the finish and the LUFS step do.
So "every other note stays byte for byte" holds only before the hiss removal (`outside_dropped_same`), and the
finished audio's change outside the dropped spans and the level step against the parent are recorded beside, per part,
for both guitars (`outside_change`, `level_step_db`). `level_step_db` is only `at_lufs`' residual step; the real level
change of the kept audio is `outside_change`'s `rms_ratio_db`.

**The terms** (renamed for the no-reused-terms rule, amendment 8), on the floors of row (b)'s answer (the held half, the
true DI as the judge's DI), paired per part through `scratch_notes.set_rows`; the 40 decide, all 47 beside:

| Term | Definition | Meaning |
|---|---|---|
| S | ln(d_tr-di / d_vc-own) | stored: the sound-gap read's S (reproduced from the stored files) |
| Sx | ln(d_tr-uc / d_vc-uc) | S without the unclaimed groups |
| Ux | S - Sx | what the unclaimed groups hold of S |
| Ubx | ln(d_tr-di / d_tr-uc) | the bank guitar's move |
| Urx | ln(d_vc-own / d_vc-uc) | the real-sound guitar's move; below zero means the drop removed real playing |

Ux = Ubx - Urx exactly per part (held to 1e-12). One passing set over the four guitars (`tr-di`, `vc-own`, `tr-uc`,
`vc-uc`; amendment 6): a refusal reruns once (S1); a part refused in any of the four drops from every term.

    $MAIN -m learn.voice_control build --shard k/3     # k = 0, 1, 2 (zero renders): that slice's guitars and records
    $MAIN -m learn.voice_control build --combine       # build.json, once every part is there; then the hash PR
    $MAIN -m learn.voice_control floor --shard k/3     # the floors (voice_floors' body on the control's own world)
    $MAIN -m learn.voice_control floor --shard k/3 --rerun
    $MAIN -m learn.voice_control read                  # zero renders, once: XC_TABLE's code

**The proofs** (`PROOFS`), on every part; a failure stops the build before that part writes anything:
`flags_are_builds` (the recomputed flags equal build.json's), `rule_off_is_stored` (with no group dropped the builder
gives `tr-di` and `vc-own` byte for byte, their stored sha256s), `trace_holds` (the trace equals build 2's stored report
and build.json's, and `tr-uc`'s own synthesis report has the same counts), `outside_dropped_same` (`tr-uc`'s
synthesis before the hiss removal equals `tr-di`'s byte for byte outside the dropped notes' spans; amendment 1 scopes
it there), `gate_outside_same` (`vc-uc`'s gate equals `vc-own`'s byte for byte outside the dropped notes' window spans
and is at most `vc-own`'s everywhere; amendment 2), `synth_inside_gate` (`voice_build`'s check, on the control's pair:
`tr-uc`'s synthesis before the hiss removal sounds only inside `vc-uc`'s windows), `drop_is_additive` (non-binding note
5: `tr-di`'s synthesis equals `tr-uc`'s plus the dropped-only synthesis within DROP_ADD_TOL of its peak).

**`coverage-sensitive`** (amendment 4). The coverage-clean parts are the parts whose held-half `uncovered_weight`
(`scratch_voice.cover_figures`) is exactly unchanged by the drop; carried parts are included and counted separately.
Membership is in the hashed build.json, before any floor. The code is also read on the coverage-clean deciding parts;
when it differs from the 40's, the read is marked coverage-sensitive, and under XC-part and XC-notes it goes to the
user with both subsets, not to the code's figure (and the gate opens only through the waiver).

The floors run `voice_floors`' body (`run_floor`) on this control's own world (`ControlWorld`, amendment 7): its own
guitars (`tr-uc`, `vc-uc`), stored carry sources and repeat guitars (`tr-di`, `vc-own`), and paths under
`PF/fs/voice/control/`, so the main test's `repeat/` records are never read as this run's. A byte-identical guitar
carries its parent's stored floor and names it. Every command refuses unless `scratch_voice.require_voice` holds (main's
code, including this module, and keys), main holds the sound-gap read under XV-sound or XV-both and this declaration;
nothing here imports numpy at module level. It imports `voice_build`'s gate and chain functions and redefines none.
The pure parts are tested in tests/test_voice_control.py on the light CI runner; the builder on a synthetic bank
behind `importorskip`.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import time

from learn import note_rebuild as NR
from learn import rederive_fit as RF
from learn import scratch_exact as SE
from learn import scratch_notes as SN
from learn import scratch_search as S
from learn import scratch_voice as SV
from learn import voice_build as VB
from learn import voice_floors as VF

PLAN = SV.PLAN
MODULE = "learn/voice_control.py"
LEDGER_ID = SV.LEDGER_ID
PHASE = SV.PHASE_CONTROL                 # this declaration
PHASE_DRY = f"{PHASE}_dry"               # the hash PR: build.json's sha256 (zero renders); defined here, not in KEYS_TO_COME
PHASE_OUTCOME = SV.PHASE_CONTROL_OUTCOME
PHASE_WAIVER = SV.PHASE_WAIVER
SR = NR.SR

# --- the guitars, the terms -----------------------------------------------------------------------------------------------

BANK, OWN = SV.BANK, SV.OWN              # tr-di (stored floor), vc-own (the sound-gap floors)
TR_UC, VC_UC = "tr-uc", "vc-uc"
BUILT = (TR_UC, VC_UC)                   # built here, rendered by the floors, in this order
PARENT = {TR_UC: BANK, VC_UC: OWN}
STORED = (BANK, OWN)                     # stored floors, carry sources and the repeat check's guitars (amendment 7)
FOUR = (BANK, OWN, TR_UC, VC_UC)         # the one passing set (amendment 6)
TERMS = (("S", BANK, OWN), ("Sx", TR_UC, VC_UC), ("Ubx", BANK, TR_UC), ("Urx", OWN, VC_UC))   # ln(num / den)
TERM_NAMES = ("S", "Sx", "Ux", "Ubx", "Urx")   # Ux = S - Sx
READ_TERMS = ("Sx", "Ux", "Ubx", "Urx")  # their readings must all be usable
ID_TOL = SV.SUM_TOL                      # |Ux - (Ubx - Urx)| per part, 1e-12
SEEN_S = (0.501, 0.399, 0.603)           # S on the 40 (the sound-gap read; the read must reproduce it to 3 places)
DROP_ADD_TOL = 1e-9                      # drop_is_additive: max |tr-di - (tr-uc + dropped-only)| / max |tr-di|
TIMING_S = NR.REFINE_S                   # the declared limit (non-binding note 7): a true rise within +-50 ms
DROPPED_WHY = "dropped: an unclaimed onset group (the control)"
DECIDING = SV.DECIDING
SMALL, BIG = SV.SMALL, SV.BIG            # 0.05, 0.10: they label only (`paired_reading`)
PARTS = SV.PARTS
CHECK_PARTS = SV.CHECK_PARTS
RENDERS_EACH = VF.RENDERS_EACH
RENDERS = {                              # non-binding note 3: how 148 relates to the pinned CONTROL_RENDERS (188)
    "ceiling_no_carry": len(BUILT) * PARTS * RENDERS_EACH,                     # 188 = scratch_voice.CONTROL_RENDERS
    "repeat": len(STORED) * CHECK_PARTS * RENDERS_EACH,                        # 8
    "ceiling_with_repeat": len(BUILT) * PARTS * RENDERS_EACH + len(STORED) * CHECK_PARTS * RENDERS_EACH,   # 196
    "carried_parts_seen": 12,            # the probe's: 12 of 47 parts have no unclaimed group, so both guitars carry
    "expected": len(BUILT) * (PARTS - 12) * RENDERS_EACH + len(STORED) * CHECK_PARTS * RENDERS_EACH,       # 148
}
COVERAGE_SENSITIVE = SV.COVERAGE_SENSITIVE
COVERAGE_FORCED = SV.COVERAGE_FORCED     # XC-part, XC-notes

DROP_RULE = {
    "flags": "build.json's unclaimed.flags (hashed in phase_scratch_voice_dry), recomputed (unclaimed_groups of the "
             "onset groups' first onsets on the true DI's rise_curve) and required equal",
    "dropped": "every note of a flagged onset group (note_rebuild.onset_groups); the group indices are stored, never "
               "the -inf levels (write_once refuses inf)",
    "tr-uc": "scratch_rederive._synth with T and the dropped groups' levels at -inf dB (last=True, the loudness option "
             "as tr-di's), then note_rebuild.denoise_above, then voice_build.chain (p.finish, cut to n, -22.9 LUFS): "
             "compose's tail exactly (tests/test_voice_build.py's test_the_padded_chain_is_composes); the rule off is "
             "tr-di byte for byte (rule_off_is_stored)",
    "vc-uc": "voice_build.own_gain on the trace with the dropped notes marked not played, on the padded raw section "
             "(voice_build.padded_raw), its end edge fade at real_end, then voice_build.through_gate (p.finish, cut "
             "to n, -22.9 LUFS); the rule off is vc-own byte for byte (rule_off_is_stored)",
    "kept": "placement, sources, variety, bends, tilt and every kept note's end and gain are tr-di's (the shared trace "
            "is tr-di's; the gains never move them): kept notes ending at a dropped note's pluck stay cut in both",
    "not_refitted": "T is not re-fitted: tuning, mutes, tilt and the kept groups' levels stay tr-di's",
    "whole_signal": "amendment 1: the hiss removal, the finish's EQ re-fit and -22.9 LUFS re-run on tr-uc; the finish "
                    "and -22.9 LUFS re-run on vc-uc; both are part of the counterfactual",
}
CHOICES = {
    "bank_chain": "tr-uc is made by compose's own steps with voice_build.chain as its tail, so its level step to -22.9 "
                  "LUFS is known (amendment 1's beside figure) without a second finish; chain is compose's tail byte "
                  "for byte (the existing test), and rule_off_is_stored rebuilds the stored tr-di through this same "
                  "path on every part",
    "spans": "a dropped note's span is voice_build.own_windows' [round((on - PRE_ATTACK_S) * SR), round(trace end * "
             "SR)) of the played dropped notes, on the padded length: the synthesis' own sample span and vc-own's "
             "window span alike",
    "skipped_dropped": "a dropped note the synthesis skips is counted as dropped and changes nothing",
    "coverage_after": "cover_figures with the marked trace's windows and the original trace's skipped spans (a dropped "
                      "note is not a skipped one); only uncovered_weight and its share are read after the drop",
    "cut_by_dropped": "a kept played note whose next played note on its string (in onset order) is a dropped note and "
                      "whose trace end kind is repluck",
    "timing": "per part, the dropped (flagged) groups with a true-DI rise of 3 dB or more within +-50 ms (REFINE_S) of "
              "the group's first onset (unclaimed_groups at a 50-ms window): a timing error, not an extra (note 7)",
    "outside_change": "per guitar against its parent, on the held half's samples ([a + TRIM_S, b + TRIM_S) s, round()) "
                      "outside the dropped spans: max |child - parent| over max |parent|, the difference's RMS against "
                      "the parent's in dB, and the RMS ratio in dB; level_step_db: the child's step to -22.9 LUFS less "
                      "the parent's, only at_lufs' residual step (both guitars end at -22.9 LUFS); the real level "
                      "change of the kept audio is outside_change's rms_ratio_db (#658's review)",
    "readerr_identity": "scratch_readerr.py's blob sha and played_trace's source sha256 are recorded beside the sound-"
                        "gap build's; a change does not stop the build (trace_holds re-checks the behaviour)",
    "carried": "a part is carried when both its guitars are byte-identical to their parents (audio sha256): every part "
               "with no dropped played note; the floors carry the parents' stored floors and name them",
}

# --- the outcome table (pure) -------------------------------------------------------------------------------------------

UPPER = "S stays an upper bound (wrong pitches, bends and articulation stay inside S; the control addresses only the " \
        "extra attacks)"
XC_TABLE = (    # (code, when, meaning, next); on the 40, `paired_reading` of Ux and Sx, the first that holds
    ("XC-anomaly", "a proof, the repeat check or an identity fails; S does not reproduce from the stored files; Ux is "
     "not 0 on a carried part; any of Sx, Ux, Ubx, Urx has no usable interval; or Urx reads worse (amendment 5)",
     "the construction is off", "stop; to the user; the spend gate stays shut"),
    ("XC-stands", "Ux reads matches or better",
     "a heard-size part of S from the unclaimed groups is ruled out, by the score",
     "price the sound routes against S; " + UPPER),
    ("XC-part", "Ux reads worse and Sx reads worse",
     "the unclaimed groups hold a heard-size part of S, and one remains without them",
     "price the sound routes against Sx as the lower figure and S as the upper (dilution pulls Sx down; amendment "
     "4); Ux goes to the note track as a named target, with Ubx and Urx"),
    ("XC-notes", "Ux reads worse, Sx does not read worse",
     "without the unclaimed groups, real audio in our windows is not shown to close a heard-size part",
     "to the user before any sound-route spend (the gate opens only through " + PHASE_WAIVER + "); the unclaimed "
     "groups are the first target"),
    ("XC-undecided", "anything else", "not decided; undecided is not failed",
     "price against S as the upper figure, with Sx beside; " + UPPER),
)
XC_CODES = tuple(c for c, *_ in XC_TABLE)
XC_DECLARED = ("XC-anomaly", "XC-stands", "XC-part", "XC-notes", "XC-undecided")
CHECKS = ("proofs", "repeat", "s_reproduces", "identity_holds", "zero_where_carried")
PROOFS = ("flags_are_builds", "rule_off_is_stored", "trace_holds", "outside_dropped_same", "gate_outside_same",
          "synth_inside_gate", "drop_is_additive")
BUILD_CHECKS = ("raw_is_true_di", "pad_is_builds", "cover_is_builds")   # beside the proofs; each stops the build too
FORCED_NEXT = ("coverage-sensitive: to the user with both coverage subsets (Ux, Ubx, Urx and Sx on each), not to the "
               "code's figure; the gate opens only through " + PHASE_WAIVER)


def iv_ok(iv):
    return SV.iv_ok(iv)


def reading(iv):
    return SV.reading(iv)


def _r(iv):
    return (reading(iv) or {}).get("reading")


def table_guard():
    """Refuse unless XC_TABLE holds its declared codes in order, its last row is literally "anything else", the core's
    gate reads the same codes (`scratch_voice.CONTROL_CODES`, its shut, waiver-only and coverage-forced codes as
    declared), 0 < SMALL < BIG, and the hash key sits under the core's prefix outside every guarded one."""
    if XC_CODES != XC_DECLARED:
        raise SystemExit("XC_TABLE's codes are not the five declared, in order")
    if XC_TABLE[-1][1] != "anything else":
        raise SystemExit("XC_TABLE's last row is not 'anything else'")
    if (SV.CONTROL_CODES != XC_CODES or SV.CONTROL_SHUT != ("XC-anomaly",) or SV.CONTROL_WAIVER_ONLY != ("XC-notes",)
            or SV.COVERAGE_FORCED != ("XC-part", "XC-notes")):
        raise SystemExit("scratch_voice's spend gate does not read XC_TABLE's codes as declared")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")
    if not PHASE_DRY.startswith(SV.KEY_PREFIX) or PHASE_DRY.startswith(SV.GUARDED_PREFIXES):
        raise SystemExit(f"{PHASE_DRY} sits outside the core's prefix or under a guarded one")


def anomaly_why(ivs, checks):
    """(Pure.) Why XC-anomaly holds, or None. ivs: {Sx, Ux, Ubx, Urx: interval}; checks: {CHECKS: bool}."""
    for c in CHECKS:
        if (checks or {}).get(c) is not True:
            return f"the check {c} does not hold"
    for t in READ_TERMS:
        if reading((ivs or {}).get(t)) is None:
            return f"{t} has no usable interval or reading"
    if _r(ivs["Urx"]) == "worse":
        return "Urx reads worse: the real-sound guitar is better by a heard size with real playing removed (amendment 5)"
    return None


def xc_code(ivs, checks):
    """(Pure.) XC_TABLE's one code, the first that holds: `paired_reading` of Ux and Sx (on the set the intervals are
    read on). ivs: {Sx, Ux, Ubx, Urx: interval}; checks: {CHECKS: bool}. -> dict."""
    ivs = dict(ivs or {})
    why = anomaly_why(ivs, checks)
    ru, rs = _r(ivs.get("Ux")), _r(ivs.get("Sx"))
    if why:
        code = "XC-anomaly"
    elif ru in ("matches", "better"):
        code = "XC-stands"
    elif ru == "worse" and rs == "worse":
        code = "XC-part"
    elif ru == "worse":
        code = "XC-notes"
    else:
        code = "XC-undecided"                              # anything else
    row = next(r for r in XC_TABLE if r[0] == code)
    return {"code": code, "when": row[1], "meaning": row[2], "next": row[3], "anomaly": why,
            "readings": {t: reading(ivs.get(t)) for t in READ_TERMS}}


def xc_read(ivs, checks, clean_ivs):
    """(Pure.) The deciding code on the 40, and beside it the code on the coverage-clean deciding parts (amendment 4):
    `coverage-sensitive` when the two differ (a clean subset whose intervals cannot be formed reads XC-anomaly there,
    so the label is set). Under XC-part and XC-notes a coverage-sensitive code goes to the user with both subsets
    (FORCED_NEXT), not to the code's figure. -> dict with `coverage_label` and `with_clean_subset`."""
    code = xc_code(ivs, checks)
    alt = xc_code(clean_ivs, checks)
    label = COVERAGE_SENSITIVE if alt["code"] != code["code"] else None
    out = dict(code, with_clean_subset=alt["code"], coverage_label=label, forced=False)
    if label and code["code"] in COVERAGE_FORCED:
        out.update(next=FORCED_NEXT + "; by the table: " + code["next"], forced=True)
    out["gate"] = gate_state(out["code"], label)
    return out


def gate_state(code, label=None):
    """(Pure.) How the spend gate reads a control outcome (`scratch_voice.spend_refusal`): "shut", "waiver" (the user's
    waiver only) or "open"."""
    if code not in SV.CONTROL_CODES or code in SV.CONTROL_SHUT:
        return "shut"
    if code in SV.CONTROL_WAIVER_ONLY or (code in COVERAGE_FORCED and label == COVERAGE_SENSITIVE):
        return "waiver"
    return "open"


# --- the term arithmetic (pure) -----------------------------------------------------------------------------------------

def finite_pos(v):
    return SV.finite_pos(v)


def part_terms(d):
    """(Pure.) One part's terms from its floors d ({guitar: held}): S, Sx, Ubx, Urx as ln(num / den) (None where a
    floor is missing, zero or non-finite) and Ux = S - Sx."""
    out = {}
    for t, a, b in TERMS:
        x, y = (d or {}).get(a), (d or {}).get(b)
        out[t] = math.log(x / y) if finite_pos(x) and finite_pos(y) else None
    out["Ux"] = out["S"] - out["Sx"] if out["S"] is not None and out["Sx"] is not None else None
    return {t: out[t] for t in TERM_NAMES}


def identity_gap(t):
    """(Pure.) |Ux - (Ubx - Urx)| of one part's terms, or None."""
    if any(t.get(n) is None for n in ("Ux", "Ubx", "Urx")):
        return None
    return abs(t["Ux"] - (t["Ubx"] - t["Urx"]))


def passing(d):
    """(Pure.) Whether a part passes: every floor of the four guitars finite and positive (amendment 6)."""
    return all(finite_pos((d or {}).get(g)) for g in FOUR)


def term_values(floors):
    """(Pure.) floors: {pkey: {guitar: held}}. -> (passing values {term: {pkey: value}}, refused {pkey: reason},
    per-part identity gaps on the passing set). One passing set for every term (amendment 6)."""
    vals = {t: {} for t in TERM_NAMES}
    refused, gaps = {}, {}
    for k in sorted(floors):
        d = floors[k]
        if not passing(d):
            bad = [g for g in FOUR if not finite_pos((d or {}).get(g))]
            refused[k] = f"no finite positive floor for {', '.join(bad)}"
            continue
        t = part_terms(d)
        for n, v in t.items():
            vals[n][k] = v
        gaps[k] = identity_gap(t)
    return vals, refused, gaps


def identity_holds(gaps, tol=ID_TOL):
    return bool(gaps) and all(g is not None and g <= tol for g in gaps.values())


def zero_where_carried(vals, carried):
    """(Pure.) Ux, Ubx and Urx are exactly 0.0 on every passing carried part (both guitars byte-identical to their
    parents, every part with no dropped group among them)."""
    return all(vals[t].get(k) in (None, 0.0) for k in carried for t in ("Ux", "Ubx", "Urx"))


def s_reproduces(s_now, s_rows, iv40, rows_iv):
    """(Pure.) S from the stored files: per part ln(d_tr-di / d_vc-own) equal to the sound-gap rows.json's per-part S
    (by tag), the 40's interval equal to rows.json's and to SEEN_S to 3 places. s_now: {tag: value}; s_rows: {tag:
    value}. -> {per_part, stored, seen, holds, iv}."""
    per = bool(s_rows) and sorted(s_now) == sorted(s_rows) and all(s_now[k] == s_rows[k] for k in s_rows)
    exact = iv_ok(iv40) and iv_ok(rows_iv) and all(iv40[q] == rows_iv[q] for q in ("mean", "lo90", "hi90"))
    seen = SV.close3(iv40, SEEN_S)
    return {"per_part": per, "stored": exact, "seen": seen, "holds": per and exact and seen, "iv": iv40}


# --- the drop (pure) --------------------------------------------------------------------------------------------------------

def dropped_groups(flags):
    """(Pure.) The flagged groups' indices (stored, never the -inf levels)."""
    return [gi for gi, f in enumerate(flags) if f]


def dropped_notes(groups, gidx):
    """(Pure.) Every note of the dropped groups, sorted. groups: `note_rebuild.onset_groups`."""
    g = set(gidx)
    return sorted(k for gi, ks in enumerate(groups) if gi in g for k in ks)


def drop_levels(levels, gidx):
    """(Pure.) T's per-group levels with the dropped groups at -inf dB (in memory only; 10^(-inf/20) = 0)."""
    g = set(gidx)
    if any(not 0 <= i < len(levels) for i in g):
        raise ValueError("a dropped group outside the levels")
    return [-math.inf if i in g else float(v) for i, v in enumerate(levels)]


def only_levels(levels, gidx):
    """(Pure.) drop_is_additive's dropped-only levels: the kept groups at -inf dB, the dropped ones T's."""
    g = set(gidx)
    return [float(v) if i in g else -math.inf for i, v in enumerate(levels)]


def marked_trace(trace, nidx):
    """(Pure.) The trace with the dropped notes' played records marked not played (they open no window); every other
    record as it is."""
    d = set(nidx)
    return [dict(t, played=False, why=DROPPED_WHY, dropped=True) if k in d and t.get("played") else t
            for k, t in enumerate(trace)]


def only_trace(trace, nidx):
    """(Pure.) The trace with only the dropped notes played: their window spans (`voice_build.own_windows`)."""
    d = set(nidx)
    return [t if k in d else dict(t, played=False) for k, t in enumerate(trace)]


def played_count(trace):
    return sum(1 for t in trace if t.get("played"))


def cut_by_dropped(notes, trace, nidx):
    """(Pure.) Kept played notes cut by a dropped pluck (CHOICES["cut_by_dropped"])."""
    d = set(nidx)
    by = {}
    for k in sorted((k for k, t in enumerate(trace) if t.get("played")), key=lambda q: (notes[q]["on"], q)):
        by.setdefault(trace[k]["string"], []).append(k)
    return sum(1 for ks in by.values() for a, b in zip(ks, ks[1:])
               if a not in d and b in d and trace[a].get("end_kind") == "repluck")


def coverage_clean(before, after):
    """(Pure.) Amendment 4's membership: the held-half uncovered weight exactly unchanged by the drop."""
    a, b = (before or {}).get("uncovered_weight"), (after or {}).get("uncovered_weight")
    return a is not None and a == b


def cover_summary(c):
    return {k: (c or {}).get(k) for k in ("frames", "uncovered_weight", "uncovered_share", "whole_frame_share")}


def proof_failures(proofs, names=PROOFS):
    """(Pure.) The failing proofs' names, in order (a missing proof fails; only True holds)."""
    return [k for k in names if proofs.get(k) is not True]


# --- the builder (numpy, lazily) ---------------------------------------------------------------------------------------

def bank_guitar(p, levels, rate=SR):
    """tr-di's chain with given levels (DROP_RULE["tr-uc"]): `scratch_rederive._synth` with T's other values,
    `denoise_above`, `voice_build.chain`. -> (float32 guitar, level step dB, synthesis before the hiss removal, its
    report)."""
    import numpy as np

    from learn import scratch_rederive as RD

    v = p.T
    synth, rep = RD._synth(p.notes, p.n, p.bank, p.ring, v["tuning"], v["mutes"], v["tilt"], levels, p.loud, rate,
                           last=True)
    y, step = VB.chain(NR.denoise_above(synth, rate), p.finish, p.n, rate)
    return np.asarray(y, np.float32), step, synth, rep


def held_mask(n, held, rate=SR):
    import numpy as np

    a, b = SV.HALVES[held]
    m = np.zeros(n, bool)
    m[max(0, int(round((a + SV.TRIM_S) * rate))):min(n, int(round((b + SV.TRIM_S) * rate)))] = True
    return m


def outside_change(child, parent, drop_mask, held, rate=SR):
    """Amendment 1's beside figure: the finished child against its finished parent on the held half outside the
    dropped spans (CHOICES["outside_change"]). -> dict."""
    import numpy as np

    c, p = np.asarray(child, np.float64), np.asarray(parent, np.float64)
    sel = held_mask(len(p), held, rate) & ~np.asarray(drop_mask[:len(p)], bool)
    c, p = c[sel], p[sel]
    if not len(p):
        return {"samples": 0, "identical": True, "max_abs_rel": None, "diff_rms_db_re_parent": None,
                "rms_ratio_db": None}
    d = c - p
    top = float(np.max(np.abs(p)))
    rp, rc, rd = (float(np.sqrt(np.mean(x ** 2))) for x in (p, c, d))
    return {"samples": int(len(p)), "identical": bool(np.array_equal(c, p)),
            "max_abs_rel": float(np.max(np.abs(d))) / top if top > 0 else None,
            "diff_rms_db_re_parent": 20 * math.log10(rd / rp) if rd > 0 and rp > 0 else None,
            "rms_ratio_db": 20 * math.log10(rc / rp) if rc > 0 and rp > 0 else None}


def additive_ratio(full, kept, only):
    """drop_is_additive's figure: max |full - (kept + only)| / max |full| (0 when full is silent and the sum exact)."""
    import numpy as np

    full = np.asarray(full, np.float64)
    gap = float(np.max(np.abs(full - (np.asarray(kept, np.float64) + np.asarray(only, np.float64))))) if len(full) \
        else 0.0
    top = float(np.max(np.abs(full))) if len(full) else 0.0
    return gap / top if top > 0 else (0.0 if gap == 0 else math.inf)


def same_outside(a, b, mask):
    """(numpy) a and b byte for byte where `mask` is False."""
    import numpy as np

    a, b, m = np.asarray(a), np.asarray(b), ~np.asarray(mask, bool)
    return a.shape == b.shape and a[m].tobytes() == b[m].tobytes()


def build_pair(p, raw_l, pad, trace, gidx, nidx, rate=SR):
    """The control's two guitars of one part, their parents rebuilt by the same builder with no group dropped, the
    proofs on the synthesis and the gates, and the beside figures. -> dict (nothing written)."""
    import numpy as np

    from learn import scratch_rederive as RD

    length = p.n + VB.pad_samples(rate)
    end = VB.real_end(p.n, pad)
    levels = list(p.T["levels"])
    tr_di, step_di, synth_di, rep_di = bank_guitar(p, levels, rate)          # the rule off
    gate_own = VB.own_gain(p.notes, trace, length, rate, end)
    vc_own, step_own = VB.through_gate(raw_l, gate_own, p.finish, p.n, rate)
    vc_own = np.asarray(vc_own, np.float32)
    marked = marked_trace(trace, nidx)
    drop_win = VB.own_windows(p.notes, only_trace(trace, nidx), rate)
    mask = VB.span_mask(drop_win, length)
    if played_count(marked) != played_count(trace):                           # a played note is dropped
        tr_uc, step_uc, synth_uc, rep_uc = bank_guitar(p, drop_levels(levels, gidx), rate)
        v = p.T
        synth_only, _ = RD._synth(p.notes, p.n, p.bank, p.ring, v["tuning"], v["mutes"], v["tilt"],
                                  only_levels(levels, gidx), p.loud, rate, last=True)
        gate_uc = VB.own_gain(p.notes, marked, length, rate, end)
        vc_uc, step_vuc = VB.through_gate(raw_l, gate_uc, p.finish, p.n, rate)
        vc_uc = np.asarray(vc_uc, np.float32)
    else:                                                                     # nothing played is dropped: the parents
        tr_uc, step_uc, synth_uc, rep_uc = tr_di, step_di, synth_di, rep_di
        synth_only, gate_uc, vc_uc, step_vuc = np.zeros(length), gate_own, vc_own, step_own
    ratio = additive_ratio(synth_di, synth_uc, synth_only)
    support = VB.support_check(synth_uc, VB.own_windows(p.notes, marked, rate), gate_uc)
    proofs = {"outside_dropped_same": same_outside(synth_uc, synth_di, mask),
              "gate_outside_same": same_outside(gate_uc, gate_own, mask) and bool(np.all(gate_uc <= gate_own)),
              "synth_inside_gate": bool(support["inside"]),
              "drop_is_additive": bool(ratio <= DROP_ADD_TOL)}
    return {"guitars": {TR_UC: tr_uc, VC_UC: vc_uc}, "parents": {BANK: tr_di, OWN: vc_own},
            "steps": {TR_UC: step_uc, VC_UC: step_vuc, BANK: step_di, OWN: step_own}, "reports": {BANK: rep_di,
                                                                                                TR_UC: rep_uc},
            "marked": marked, "mask": mask, "proofs": proofs, "additive_ratio": ratio, "support": support,
            "drop_windows": len(drop_win)}


PART_FIELDS = ("plan", "part", "tag", "set", "held", "renders", "code", "checks", "proofs", "guitars", "parents",
               "carried", "dropped", "cover_before", "cover_after", "coverage_clean", "cut_by_dropped", "timing",
               "outside_change", "level_step_db", "lufs_gain_db", "additive_ratio", "support", "trace_report",
               "uc_trace_played", "pad")


def part_record(p, dp, raw_l, pad, vb, stored_rep, ident, rate=SR):
    """One part: the checks and the seven proofs (any failure stops before anything is written), the two guitars
    (each written once), the figures. p: a `bench_parts` Part; dp: its draw part; raw_l, pad: `padded_raw`'s; vb: the
    sound-gap build.json's part record; stored_rep: build 2's tr-di report. -> the record (saved once)."""
    import numpy as np

    from learn import scratch_readerr as RX
    from learn import scratch_rederive as RD
    from learn import song_bank as SB

    tag = SV.tag(p.key)
    length = p.n + VB.pad_samples(rate)
    raw_l = np.asarray(raw_l, np.float64)
    if len(raw_l) != length:
        raise SystemExit(f"part {tag}: the padded raw section is not n + END_PAD_S samples")
    checks = {"raw_is_true_di": VB.same_bytes(np.asarray(np.asarray(SB.measure(raw_l[:p.n]), np.float32), np.float64),
                                              p.di),
              "pad_is_builds": dict(pad) == dict(vb.get("pad") or {})}
    v = p.T
    trace, rep = RX.played_trace(p.notes, length, p.bank, v["tuning"], p.ring, v["mutes"], rate)
    groups = NR.onset_groups(p.notes)
    rise, hop = NR.rise_curve(p.di, rate)
    onsets = VB.group_onsets(p.notes)
    unc = SV.unclaimed_groups(onsets, rise.tolist(), hop, rate)
    gidx = dropped_groups(unc["flags"])
    nidx = dropped_notes(groups, gidx)
    levels_db = NR.frame_levels_db(p.di, SV.COVER["frame"], SV.COVER["hop"]).tolist()
    w0, s0 = SV.played_windows(p.notes, trace, p.n, rate)
    c0 = SV.cover_figures(levels_db, w0, s0, dp["held"], rate=rate)
    checks["cover_is_builds"] = c0 == vb.get("cover")
    bad = [c for c in BUILD_CHECKS if checks.get(c) is not True]
    if bad:
        raise SystemExit(f"part {tag}: check(s) {bad} failed: the build stops; to the user")
    b = build_pair(p, raw_l, pad, trace, gidx, nidx, rate)
    vb_flags = (vb.get("unclaimed") or {}).get("flags")
    proofs = {"flags_are_builds": isinstance(vb_flags, list) and unc["flags"] == vb_flags
              and len(unc["flags"]) == len(groups),
              "rule_off_is_stored": (VB.same_bytes(b["parents"][BANK], p.X) and S.npy_sha(b["parents"][BANK]) == p.x_sha
                                     and S.npy_sha(b["parents"][OWN]) == vb["guitars"][OWN]["audio_sha256"]),
              "trace_holds": (RX.trace_equals_report(rep, stored_rep) and rep == vb.get("trace_report")
                              and RX.trace_equals_report(b["reports"][TR_UC], stored_rep)),
              **b["proofs"]}
    fail = proof_failures(proofs)
    if fail:
        raise SystemExit(f"part {tag}: proof(s) {fail} failed (drop_is_additive ratio {b['additive_ratio']:.3g}): the "
                         "build stops before anything is written; to the user, never loosened")
    w1, _ = SV.played_windows(p.notes, b["marked"], p.n, rate)
    c1 = SV.cover_figures(levels_db, w1, s0, dp["held"], rate=rate)
    t50 = SV.unclaimed_groups([onsets[gi] for gi in gidx], rise.tolist(), hop, rate, window=TIMING_S)
    mask_n = b["mask"][:p.n]
    if part_path(p.key).exists():
        raise SystemExit(f"part {tag}: its record exists: never overwritten")
    guitars = {}
    for g in BUILT:
        try:
            fs = RD._write_once(dry_path(g, p.key), b["guitars"][g])
        except SystemExit:
            raise SystemExit(f"part {tag}: its {g} guitar exists with other samples: never overwritten") from None
        guitars[g] = {"file_sha256": fs, "audio_sha256": S.npy_sha(b["guitars"][g])}
    parents = {BANK: p.x_sha, OWN: vb["guitars"][OWN]["audio_sha256"]}
    carried = all(guitars[g]["audio_sha256"] == parents[PARENT[g]] for g in BUILT)
    st = b["steps"]
    rec = {"plan": PLAN, "part": p.key, "tag": tag, "set": p.set, "held": dp["held"], "renders": 0, "code": ident,
           "checks": checks, "proofs": proofs, "guitars": guitars, "parents": parents, "carried": carried,
           "dropped": {"groups": gidx, "notes": nidx, "groups_n": len(gidx), "notes_n": len(nidx),
                       "played_notes_n": played_count(trace) - played_count(b["marked"]), "groups_all": len(groups),
                       "notes_all": len(p.notes), "drop_windows": b["drop_windows"]},
           "cover_before": cover_summary(c0), "cover_after": cover_summary(c1), "coverage_clean": coverage_clean(c0, c1),
           "cut_by_dropped": cut_by_dropped(p.notes, trace, nidx),
           "timing": {"dropped_groups": len(gidx), "rise_within_50ms": len(gidx) - t50["unclaimed"]},
           "outside_change": {TR_UC: outside_change(b["guitars"][TR_UC], b["parents"][BANK], mask_n, dp["held"], rate),
                              VC_UC: outside_change(b["guitars"][VC_UC], b["parents"][OWN], mask_n, dp["held"], rate)},
           "level_step_db": {g: (st[g] - st[PARENT[g]] if st[g] is not None and st[PARENT[g]] is not None else None)
                             for g in BUILT},
           "lufs_gain_db": st, "additive_ratio": b["additive_ratio"], "support": b["support"], "trace_report": rep,
           "uc_trace_played": played_count(b["marked"]), "pad": dict(pad)}
    VB._save_once(part_path(p.key), rec)
    return rec


# --- the records (pure) ---------------------------------------------------------------------------------------------------

def coverage_sets(per, keys):
    """(Pure.) Amendment 4's membership over the draw's `keys`: the coverage-clean parts (all of them and the deciding
    ones), with the carried and the with-drop counts. -> dict (part keys: PF only)."""
    clean = sorted(k for k in keys if per[k]["coverage_clean"] is True)
    dec = [k for k in keys if per[k]["set"] in DECIDING]
    cd = [k for k in clean if k in dec]
    return {"clean": clean, "clean_n": len(clean), "deciding_n": len(dec), "clean_deciding_n": len(cd),
            "clean_deciding_carried_n": sum(per[k]["carried"] for k in cd),
            "clean_deciding_with_drops_n": sum(per[k]["dropped"]["groups_n"] > 0 for k in cd),
            "moved_deciding_n": len(dec) - len(cd)}


def combine_body(per, keys, voice_build_sha):
    """(Pure.) build.json from the per-part records over the draw's `keys`: the proofs and checks held of all,
    `proofs_hold` (every proof and check on every part of the 47), the coverage membership (before the floors), the
    drop's totals, the rules. No time, so a rerun is byte-identical."""
    keys = sorted(keys)
    if sorted(per) != keys:
        raise SystemExit("the part records are not the draw's parts")
    ids = {json.dumps(per[k]["code"], sort_keys=True) for k in keys}
    if len(ids) != 1:
        raise SystemExit("the parts were built from different scratch_readerr code: rebuild from one checkout")
    proofs = {p: {"held": sum(per[k]["proofs"].get(p) is True for k in keys), "of": len(keys)} for p in PROOFS}
    checks = {c: {"held": sum(per[k]["checks"].get(c) is True for k in keys), "of": len(keys)} for c in BUILD_CHECKS}
    hold = (len(keys) == PARTS and all(v["held"] == v["of"] for v in proofs.values())
            and all(v["held"] == v["of"] for v in checks.values()))
    dec = [k for k in keys if per[k]["set"] in DECIDING]

    def tot(ks, f):
        return sum(per[k]["dropped"][f] for k in ks)
    dropped = {s: {"parts": len(ks), "groups": tot(ks, "groups_n"), "groups_all": tot(ks, "groups_all"),
                   "notes": tot(ks, "notes_n"), "played_notes": tot(ks, "played_notes_n"),
                   "parts_with_drops": sum(per[k]["dropped"]["groups_n"] > 0 for k in ks),
                   "carried": sum(per[k]["carried"] for k in ks),
                   "cut_by_dropped": sum(per[k]["cut_by_dropped"] for k in ks),
                   "rise_within_50ms": sum(per[k]["timing"]["rise_within_50ms"] for k in ks)}
               for s, ks in (("all_47", keys), ("the_40", dec))}
    return {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": 0, "voice_build_sha256": voice_build_sha,
            **json.loads(next(iter(ids))), "rules": {"drop": DROP_RULE, "choices": CHOICES,
                                                     "drop_add_tol": DROP_ADD_TOL, "timing_s": TIMING_S},
            "parts_n": len(keys), "proofs": proofs, "checks": checks, "proofs_hold": hold,
            "coverage": coverage_sets(per, keys), "dropped": dropped,
            "parts": {k: {f: per[k][f] for f in PART_FIELDS if f not in ("plan", "part", "renders", "code")}
                      for k in keys}}


def dry_body(build, sha):
    """(Pure.) The hash PR's ledger body (`phase_scratch_voice_control_dry`): counts and sha256s only, no part keys."""
    cov = {k: v for k, v in build["coverage"].items() if k != "clean"}
    return {"sha256": sha, "plan": PLAN, "renders": 0, "parts": build["parts_n"],
            "proofs": {p: f"{v['held']} of {v['of']}" for p, v in build["proofs"].items()},
            "checks": {c: f"{v['held']} of {v['of']}" for c, v in build["checks"].items()},
            "proofs_hold": build["proofs_hold"], "coverage": cov, "dropped": build["dropped"],
            "voice_build_sha256": build["voice_build_sha256"],
            "scratch_readerr_blob_sha": build["scratch_readerr_blob_sha"],
            "played_trace_sha256": build["played_trace_sha256"]}


# --- paths, the guards ----------------------------------------------------------------------------------------------------

def control_dir():
    return SV.voice_dir() / "control"


def build_path():
    return control_dir() / "build.json"


def part_path(pk):
    return control_dir() / "build-parts" / f"{SE._f(pk)}.json"


def dry_path(guitar, pk):
    if guitar not in BUILT:
        raise ValueError(guitar)
    return control_dir() / "dry" / guitar / f"{SE._f(pk)}.npy"


def floor_path(pk):
    return control_dir() / "floors" / f"{SE._f(pk)}.json"


def first_path(pk):
    return control_dir() / "floors-first" / f"{SE._f(pk)}.json"


def repeat_path(pk):
    return control_dir() / "repeat" / f"{SE._f(pk)}.json"


def rows_path():
    return control_dir() / "rows.json"


def report_path():
    return control_dir() / "report.json"


def outcome_refusal(m):
    """(Pure.) Why the control may not run on main's entry, or None: the sound-gap read must be on main under XV-sound
    or XV-both (the codes whose spend it gates)."""
    out = (m or {}).get(SV.PHASE_OUTCOME)
    code = out.get("code") if isinstance(out, dict) else None
    if code not in SV.SPEND_CODES:
        return f"main's {SV.PHASE_OUTCOME} code is {code!r}: the control runs only under {list(SV.SPEND_CODES)}"
    return None


def require_control(*phases):
    """Refuse unless both tables hold, this checkout runs main's code and keys (`scratch_voice.require_voice`, this
    module among the core's UNIT_FILES), and main holds the sound-gap build's hash, its read under XV-sound or
    XV-both, this declaration and `phases`. -> main's `preset-ladder` entry."""
    table_guard()
    m = SV.require_voice(SV.PHASE_DRY, SV.PHASE_OUTCOME, PHASE, *phases)
    why = outcome_refusal(m)
    if why:
        raise SystemExit(why)
    return m


def _control_build(m):
    from learn import note_transcribe as NT

    if not build_path().exists():
        raise SystemExit("no control build.json (`build` first)")
    b = NT.require_file_hash(m, PHASE_DRY, build_path())
    if b.get("proofs_hold") is not True:
        raise SystemExit("the control build's proofs did not hold")
    return b


def _voice_rows(m):
    """The sound-gap read's rows.json, refused unless its sha256 is main's phase_scratch_voice_outcome rows_sha256."""
    p = SV.rows_path()
    if not p.exists():
        raise SystemExit("no sound-gap rows.json")
    why = SE.field_refusal(m, SV.PHASE_OUTCOME, "rows_sha256", S.file_sha(p))
    if why:
        raise SystemExit(why)
    return json.loads(p.read_text())


def own_floors(rows, recs):
    """(Pure.) vc-own's stored floor per part from the sound-gap floor records ({pkey: (record, file sha256)}), each
    file's sha256 rows.json's `floors_sha256` (by tag), its vc-own floor finite, positive and not refused.
    -> {pkey: {held, audio_sha256}}."""
    out = {}
    shas = rows.get("floors_sha256") or {}
    for k, (rec, sha) in recs.items():
        if shas.get(SV.tag(k)) != sha:
            raise SystemExit(f"part {SV.tag(k)}: its sound-gap floor record is not the one rows.json hashed")
        g = ((rec or {}).get("guitars") or {}).get(OWN) or {}
        if g.get("refused") or not finite_pos(g.get("held")) or not g.get("audio_sha256"):
            raise SystemExit(f"part {SV.tag(k)}: vc-own's stored floor is refused or not finite and positive")
        out[k] = {"held": g["held"], "audio_sha256": g["audio_sha256"]}
    return out


def require_build():
    """Refuse unless the control's guard holds and bench_parts' code is main's (`voice_build.code_refusal`)."""
    m = require_control()
    why = VB.code_refusal()
    if why:
        raise SystemExit(why)
    return m


# --- build (zero renders) --------------------------------------------------------------------------------------------------

def _draw_parts():
    draw, _ = SE.context()
    return {p["pkey"]: p for p in draw["parts"]}


def _build_parts(m, need, by):
    """Build the parts `need` (keys) from bench_parts, each saved once."""
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
    _, sd = SE.context()
    vbuild = SV._build(m)
    if vbuild.get("proofs_hold") is not True:
        raise SystemExit("the sound-gap build's proofs did not hold")
    b2 = SE.bank_build(m)
    ident = VB.code_identity()
    t0 = time.time()
    for j, p in enumerate(RF.bench_parts(m, set(need))):
        dp = by[p.key]
        prt = sd.units[(dp["set"], dp["unit"], dp["amp"])]["prt"]
        raw_l, pad = VB.padded_raw(prt["di_path"], prt["start_s"])
        rec = part_record(p, dp, raw_l, pad, vbuild["parts"][p.key],
                          b2["parts"][p.key]["arms"][SE.BANK_ARM]["report"], ident)
        d = rec["dropped"]
        print(f"part {rec['tag']} ({j + 1} of {len(need)}): proofs hold; dropped {d['groups_n']} of {d['groups_all']} "
              f"groups, {d['played_notes_n']} played notes; carried {rec['carried']}; coverage-clean "
              f"{rec['coverage_clean']} ({time.time() - t0:.0f} s in all)", flush=True)


def cmd_build(args):
    """build (zero renders): `--shard k/n` that slice's guitars and part records (parts already there are kept);
    `--combine` build.json once every part is there; neither: every part, then the combine."""
    m = require_build()
    from learn import note_transcribe as NT

    mode = RF.run_mode(args)
    if mode != "shard":
        NT.never_overwrite(build_path())
    by = _draw_parts()
    keys = sorted(by)
    if mode in ("one", "shard"):
        shard = getattr(args, "shard", None)
        mine = RF.shard_keys(keys, shard)
        need = [k for k in mine if not part_path(k).exists()]
        if need:
            _build_parts(m, need, by)
        if mode == "shard":
            print(f"VC BUILD SHARD {shard[0]}/{shard[1]}: {len(mine)} parts ({len(need)} new); `build --combine` once "
                  "every shard is done")
            return
    missing = [k for k in keys if not part_path(k).exists()]
    if missing:
        raise SystemExit(f"{len(missing)} of {len(keys)} parts have no record yet: run every shard first")
    per = {}
    for k in keys:
        r = json.loads(part_path(k).read_text())
        if r.get("part") != k or tuple(r) != PART_FIELDS:
            raise SystemExit(f"part {SV.tag(k)}: a malformed part record")
        for g in BUILT:
            if S.file_sha(dry_path(g, k)) != r["guitars"][g]["file_sha256"]:
                raise SystemExit(f"part {SV.tag(k)}: its {g} guitar changed since its record")
        per[k] = r
    out = combine_body(per, keys, S.file_sha(SV.build_path()))
    sha = VB._save_once(build_path(), out)
    print(f"VC BUILD: {out['parts_n']} parts, proofs " + ", ".join(f"{p} {v['held']}/{v['of']}" for p, v in
                                                                    out["proofs"].items())
          + f" -> {'hold' if out['proofs_hold'] else 'DO NOT HOLD: to the user'}; build.json sha256 {sha}")
    print(json.dumps({PHASE_DRY: dry_body(out, sha)}, indent=1))


# --- floor (voice_floors' body on the control's own world, amendment 7) -----------------------------------------------

class ControlRuns:
    """The control's guitars and paths as `voice_floors.run_floor` reads them off a world."""

    order = BUILT
    stored_guitars = STORED
    repeat_guitars = STORED
    plan = PLAN
    sha_fields = ("build", "answers", "floors", "voice_rows")
    label = "VOICE CONTROL FLOORS"

    @staticmethod
    def floor_path(pk):
        return floor_path(pk)

    @staticmethod
    def first_path(pk):
        return first_path(pk)

    @staticmethod
    def repeat_path(pk):
        return repeat_path(pk)


def require_floors():
    """Every guard, before any render or numpy: the control's guard and its build's hash (`phase_scratch_voice_control_
    dry`, proofs held), the sound-gap build's hash, the stored real floors, the sound-gap rows.json (its sha256 the
    outcome's) and each vc-own floor record it hashed, row (b)'s answers, all covering the draw's parts. -> the
    guarded context."""
    m = require_control(PHASE_DRY)
    build = _control_build(m)
    vbuild = SV._build(m)
    stored, _iv = SV._stored_floors(m)
    rows = _voice_rows(m)
    ans = S.require_hash(S.phase_answers(SV.STEM_ROW), S.answers_path(SV.STEM_ROW))
    b2 = SE.bank_build(m)
    draw, sd = SE.context()
    keys = sorted(p["pkey"] for p in draw["parts"])
    if (len(keys) != PARTS or sorted(stored) != keys or sorted(build.get("parts") or {}) != keys
            or sorted(vbuild.get("parts") or {}) != keys):
        raise SystemExit("the draw, the stored floors and the two builds do not cover the same parts")
    recs = {}
    for k in keys:
        if not SV.floor_path(k).exists():
            raise SystemExit(f"{SV.tag(k)}: no sound-gap floor record")
        recs[k] = (json.loads(SV.floor_path(k).read_text()), S.file_sha(SV.floor_path(k)))
        gs = build["parts"][k].get("guitars") or {}
        if any(not (gs.get(g) or {}).get("audio_sha256") or not (gs.get(g) or {}).get("file_sha256") for g in BUILT):
            raise SystemExit(f"{SV.tag(k)}: the control build does not declare both guitars' sha256")
        if not finite_pos((stored[k].get(BANK) or {}).get("held")):
            raise SystemExit(f"{SV.tag(k)}: the stored tr-di floor is not finite and positive")
        if k not in (ans.get("parts") or {}):
            raise SystemExit(f"{SV.tag(k)}: row (b) has no answer")
    own = own_floors(rows, recs)
    st = {k: {BANK: {"held": stored[k][BANK]["held"], "audio_sha256": stored[k][BANK].get("audio_sha256")},
              OWN: own[k]} for k in keys}
    shas = {"build": S.file_sha(build_path()), "floors": S.file_sha(SE.floors_path()),
            "answers": S.file_sha(S.answers_path(SV.STEM_ROW)), "voice_rows": S.file_sha(SV.rows_path())}
    return {"m": m, "build": build, "voice_build": vbuild, "stored": st, "answers": ans, "b2": b2, "draw": draw,
            "sd": sd, "shas": shas}


class ControlWorld(ControlRuns, VF.RealWorld):
    """The control's renders and files: `voice_floors.RealWorld`'s render and judge, the control's guitars and paths;
    `tr-di` and `vc-own` the stored guitars (`vc-own` loaded by the sound-gap build's sha256s)."""

    def _context(self, pk):
        c = super()._context(pk)
        if OWN not in c["stored32"]:
            import numpy as np

            ent = self.ctx["voice_build"]["parts"][pk]["guitars"][OWN]
            path = SV.dry_path(OWN, pk)
            if not path.exists() or S.file_sha(path) != ent["file_sha256"]:
                raise SystemExit(f"{SV.tag(pk)}: vc-own's file is not the sound-gap build's")
            x32 = np.load(path).astype(np.float32)
            if S.npy_sha(x32) != ent["audio_sha256"]:
                raise SystemExit(f"{SV.tag(pk)}: vc-own's samples are not the sound-gap build's")
            c["stored32"][OWN] = x32
        return c

    def dry_shas(self, pk):
        """{guitar: dry sha256}: tr-uc's and vc-uc's as the control build declares them, tr-di's and vc-own's from
        their audio."""
        c = self._context(pk)
        out = {g: self.ctx["build"]["parts"][pk]["guitars"][g]["audio_sha256"] for g in BUILT}
        out.update({g: S.npy_sha(c["stored32"][g]) for g in STORED})
        return out

    def load(self, pk, g):
        c = self._context(pk)
        if g in STORED:
            return c["stored32"][g]
        import numpy as np

        ent = self.ctx["build"]["parts"][pk]["guitars"][g]
        path = dry_path(g, pk)
        if not path.exists() or S.file_sha(path) != ent["file_sha256"]:
            raise SystemExit(f"{SV.tag(pk)}: {g}'s file is not the control build's")
        x32 = np.load(path).astype(np.float32)
        if S.npy_sha(x32) != ent["audio_sha256"]:
            raise SystemExit(f"{SV.tag(pk)}: {g}'s samples are not the control build's")
        if x32.ndim != 1 or len(x32) != len(c["di32"]):
            raise SystemExit(f"{SV.tag(pk)}: {g} is not the section's length")
        return x32


def open_world():
    return ControlWorld(require_floors())


def cmd_floor(args):
    """The control's floors of one shard (`voice_floors.run_floor` on `ControlWorld`): the shard checked, every guard
    before any render; shard 0 runs the control's own repeat check (tr-di and vc-own on the two check parts, 8
    renders, `control/repeat/`)."""
    why = VF.shard_refusal(getattr(args, "shard", None))
    if why:
        raise SystemExit(why)
    return VF.run_floor(args, open_world())


# --- read (zero renders, once) ---------------------------------------------------------------------------------------------

def floors_of(stored, recs, build):
    """Per part {guitar: held} over the four guitars: the stored tr-di and vc-own floors and the control's records.
    Refuses (SystemExit) a record that sets a guitar outside BUILT, whose guitar was not rendered from the control
    build's (dry_sha256), or whose floor is missing, non-finite or not positive without `refused`. -> ({pkey: {guitar:
    held or None}}, {pkey: {guitar: reason}})."""
    out, why = {}, {}
    for k, st in stored.items():
        d = {}
        for g in STORED:
            h = (st.get(g) or {}).get("held")
            d[g] = h if finite_pos(h) else None
            if d[g] is None:
                why.setdefault(k, {})[g] = f"the stored {g} floor is not finite and positive ({h!r})"
        gs = (recs.get(k) or {}).get("guitars") or {}
        if sorted(gs) != sorted(BUILT):
            raise SystemExit(f"part {SV.tag(k)}: a control floor record sets {sorted(gs)}, not {sorted(BUILT)}")
        for g, r in gs.items():
            if r.get("dry_sha256") != build["parts"][k]["guitars"][g]["audio_sha256"]:
                raise SystemExit(f"part {SV.tag(k)}: {g}'s floor was not rendered from the control build's guitar")
            if r.get("refused"):
                d[g] = None
                why.setdefault(k, {})[g] = r["refused"]
            elif finite_pos(r.get("held")):
                d[g] = r["held"]
            else:
                raise SystemExit(f"part {SV.tag(k)}: {g}'s floor {r.get('held')!r} is not finite and positive and is "
                                 "not marked refused: a malformed floor record, to the user")
        out[k] = d
    return out, why


def read_body(vals, refused, gaps, iv_fn, deciding, clusters, clean, checks, share_fn=None):
    """(Pure but for `iv_fn` and `share_fn`.) The read on one passing set: each term's interval on the 40 (`iv_fn(values,
    keys)`, BKS+GOAT's pool; keys None: all), XC_TABLE's code with the coverage-clean subset beside
    (`coverage-sensitive`), the intent-to-treat code beside (`refusal-sensitive`), both coverage subsets' terms, each
    cluster of the 40 left out, the three largest parts, Fieller's Ux/S. clean: the coverage-clean keys (build.json).
    -> dict."""
    dec = sorted(k for k in deciding if k not in refused)
    ivs = {t: iv_fn(vals[t], None) for t in TERM_NAMES}
    cd = [k for k in dec if k in set(clean)]
    md = [k for k in dec if k not in set(clean)]
    sub = {name: ({t: iv_fn(vals[t], set(ks)) for t in TERM_NAMES} if ks else {t: None for t in TERM_NAMES})
           for name, ks in (("clean", cd), ("moved", md))}
    code = xc_read({t: ivs[t] for t in READ_TERMS}, checks, {t: sub["clean"][t] for t in READ_TERMS})
    itt = {t: S.itt_values(v, refused) for t, v in vals.items()}
    itt_ivs = {t: iv_fn(v, None) for t, v in itt.items()}
    itt_code = xc_read({t: itt_ivs[t] for t in READ_TERMS}, checks, {t: sub["clean"][t] for t in READ_TERMS})
    code, itt_rec, s1 = SV.with_itt(code, itt_code, refused)
    left = {t: [iv_fn(vals[t], set(dec) - set(c)) for c in clusters] for t in TERM_NAMES}
    rng = {t: ([min(x["mean"] for x in v if iv_ok(x)), max(x["mean"] for x in v if iv_ok(x))]
               if any(iv_ok(x) for x in v) else None) for t, v in left.items()}
    big = {}
    for t in READ_TERMS:
        top = SV.largest(vals[t], dec)
        big[t] = {"tags": [SV.tag(k) for k in top], "values": [vals[t][k] for k in top],
                  "without": iv_fn(vals[t], set(dec) - set(top))}
    return {"passing_parts_on_the_40": len(dec), "refused": sorted(SV.tag(k) for k in refused), "terms": ivs,
            "readings": {t: reading(ivs.get(t)) for t in TERM_NAMES}, "code": code["code"], "xc": code,
            "coverage_label": code.get("coverage_label"), "gate": code.get("gate"),
            "coverage_subsets": {"clean": {"parts": len(cd), "terms": sub["clean"]},
                                 "moved": {"parts": len(md), "terms": sub["moved"]}},
            "itt": {"terms": {t: itt_ivs.get(t) for t in READ_TERMS}, "xc": itt_rec} if itt_rec else None,
            "label": s1, "identity_max_gap": max((g for g in gaps.values() if g is not None), default=None),
            "cluster_left_out": left, "cluster_left_out_range": rng, "largest_three": big,
            "share_Ux_of_S": share_fn(vals["Ux"], vals["S"]) if share_fn else None}


def cmd_read(_args):
    """The read (zero renders), once: the control's build.json (main's phase_scratch_voice_control_dry), every part's
    control floor record (no pending rerun) and the control's repeat check; S reproduced from the stored files against
    the sound-gap rows.json; the terms on one passing set; XC_TABLE's code with coverage-sensitive and S1 beside; the
    figures beside. The rows are saved before the code. -> control/rows.json, control/report.json."""
    m = require_control(PHASE_DRY)
    from learn import note_transcribe as NT
    from learn import pipeline_fix as P

    for p_ in (rows_path(), report_path()):
        NT.never_overwrite(p_)
    ctx = require_floors()
    build, st = ctx["build"], ctx["stored"]
    draw, sd = ctx["draw"], ctx["sd"]
    keys = sorted(p["pkey"] for p in draw["parts"])
    recs = {}
    for k in keys:
        if not floor_path(k).exists():
            raise SystemExit(f"part {SV.tag(k)}: no control floor record (`floor` first)")
        recs[k] = json.loads(floor_path(k).read_text())
    pend = SV.pending_reruns(recs)
    if pend:
        raise SystemExit(f"{len(pend)} refused render(s) not rerun once: `floor --rerun` first")
    reps = {k: VF._read(repeat_path(k)) for k in SV.check_parts(draw["parts"])}

    def iv_fn(vals, ks=None):
        r = SN.set_rows(sd, draw, {k: v for k, v in vals.items() if v is not None and math.isfinite(v)}, ks)
        return ((r or {}).get("bks_goat") or {}).get("all")

    def share_fn(num, den):
        return SE.share(sd, draw, num, den)

    rows_v = _voice_rows(m)
    s_now = {k: SV.part_terms_pair({BANK: st[k][BANK]["held"], OWN: st[k][OWN]["held"]}, BANK, OWN) for k in keys}
    sr = s_reproduces({SV.tag(k): v for k, v in s_now.items()}, (rows_v.get("rows") or {}).get("per_part", {}).get("S"),
                      iv_fn(s_now), ((rows_v.get("rows") or {}).get("terms") or {}).get("S"))
    floors, refused_why = floors_of(st, recs, build)
    vals, refused, gaps = term_values(floors)
    carried = [k for k in keys if build["parts"][k]["carried"] is True]
    checks = {"proofs": build.get("proofs_hold") is True,
              "repeat": len(reps) == CHECK_PARTS and all(r and r.get("holds") is True for r in reps.values()),
              "s_reproduces": sr["holds"], "identity_holds": identity_holds(gaps),
              "zero_where_carried": zero_where_carried(vals, carried)}
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    deciding = [k for k in keys if sets_of[k] in DECIDING]
    clusters = {}
    for p in draw["parts"]:
        if p["set"] in DECIDING:
            clusters.setdefault(p["cluster"], []).append(p["pkey"])
    body = read_body(vals, refused, gaps, iv_fn, deciding, [sorted(v) for _, v in sorted(clusters.items())],
                     build["coverage"]["clean"], checks, share_fn)
    per = build["parts"]
    beside = {"all_47": {t: ((SN.set_rows(sd, draw, v) or {}).get("deciding_pool")) for t, v in vals.items()},
              "clean": {t: (((SN.set_rows(sd, draw, v) or {}).get("bks_goat") or {}).get("clean")) for t, v in
                        vals.items()},
              "crunch": {t: (((SN.set_rows(sd, draw, v) or {}).get("bks_goat") or {}).get("crunch")) for t, v in
                         vals.items()},
              "coverage": {k: v for k, v in build["coverage"].items() if k != "clean"},
              "dropped": build["dropped"],
              "outside_change_max_abs_rel_40": {g: _span([per[k]["outside_change"][g]["max_abs_rel"]
                                                          for k in deciding]) for g in BUILT},
              "level_step_db_40": {g: _span([per[k]["level_step_db"][g] for k in deciding]) for g in BUILT}}
    common = {"plan": PLAN, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0, "checks": checks,
              "s_reproduced": sr, "build_sha256": S.file_sha(build_path()), "voice_rows_sha256": ctx["shas"]["voice_rows"],
              "refused_why": {SV.tag(k): v for k, v in refused_why.items()},
              "refusal_report": S.refusal_report({SV.tag(k): refused_why.get(k) or {"floor": refused[k]}
                                                  for k in refused}, {SV.tag(k): v for k, v in sets_of.items()},
                                                 DECIDING),
              "floors_sha256": {SV.tag(k): S.file_sha(floor_path(k)) for k in keys}}
    rows = dict(common, rows={"terms": body["terms"], "coverage_subsets": body["coverage_subsets"], "beside": beside,
                              "per_part": {t: {SV.tag(k): v for k, v in vs.items()} for t, vs in vals.items()}})
    P.save(rows_path(), rows)                            # the rows are saved before the code is read
    report = dict(common, read=body, beside=beside)
    P.save(report_path(), report)
    for t in TERM_NAMES:
        print(f"{t} on the 40: {body['terms'].get(t)} -> {(body['readings'].get(t) or {}).get('reading')}")
    lab = ", ".join(x for x in (body["label"], body["coverage_label"]) if x)
    print(f"XC READ: {body['code']}{' (' + lab + ')' if lab else ''}; gate {body['gate']}; next: {body['xc']['next']}; "
          f"sha256 {S.file_sha(report_path())}")


def _span(xs):
    xs = [x for x in xs if isinstance(x, (int, float)) and math.isfinite(x)]
    return [min(xs), max(xs)] if xs else None


COMMANDS = {"build": cmd_build, "floor": cmd_floor, "read": cmd_read}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="zero renders: --shard k/n, then --combine")
    b.add_argument("--shard", type=RF.shard_arg, default=None, help=f"k/n (n <= {RF.SHARD_MAX}): this slice")
    b.add_argument("--combine", action="store_true", help="refused until every part is there; build.json")
    f = sub.add_parser("floor", help="the control's floors, one render process a shard")
    f.add_argument("--shard", type=S._shard, required=True, help=f"k/{VF.SHARDS}: one render process a shard")
    f.add_argument("--rerun", action="store_true", help="S1: only the refused guitars, once more")
    sub.add_parser("read", help="zero renders, once")
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
