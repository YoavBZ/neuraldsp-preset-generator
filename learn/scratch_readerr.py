"""The note-reading diagnosis on the exact bench (`docs/scratch-readerr-plan.md`; ledger `preset-ladder`
`phase_scratch_readerr`, then `phase_scratch_readerr_frozen`, `phase_scratch_readerr_notes`,
`phase_scratch_readerr_outcome`).

At zero renders: what in Basic Pitch's re-read of the bank guitar (the exact-notes test's `xn-reread`,
`docs/scratch-search-plan.md` section 15) costs the preset, and which open transcriber, setting or post-fix reads the
bench best. "Transcriber" and "note reading", never "reader": in this repo the reader is the knob reader.

    $MAIN -m learn.scratch_readerr trace           # Phase 1, first: the exact and as-played lists, the four proofs
    $MAIN -m learn.scratch_readerr anatomy         # Phase 1: every exact and re-read note in one class; the figures
    $MAIN -m learn.scratch_readerr real-compare    # Phase 1: the same anatomy on Guitar-TECHS P1, P2 and the lists
    $MAIN -m learn.scratch_readerr screen-check    # Phase 1: checkpoint 50 against the answer on every stored pair
    $MAIN -m learn.scratch_readerr freeze          # Phase 1, last: the tracking read and the frozen figure
    # the hash PR: phase_scratch_readerr_frozen (the five files' sha256), before anything in Phase 2
    $MAIN -m learn.scratch_readerr score           # Phase 2: declared, not built (refuses)
    $MAIN -m learn.scratch_readerr read            # Phase 2: declared, not built (refuses)

Every command refuses unless this checkout runs main's code and keys: `scratch_exact.require_exact` (its seven files,
the `phase_scratch_exact*` keys, `scratch_search.on_main`) with the exact test's targets, four answers keys and
outcome on main, then this module's own guard: CODE_FILES (this module, `learn/readerr_run.py` and every module either
imports from the redo, the exact test and the transcriber track) equal origin/main's and exist, and the
`phase_scratch_readerr*` keys equal main's. Every Phase 1 command after `trace` refuses unless `trace.json` exists
with its four proofs holding. Output goes only to PF/fs/readerr/, each file written once (`write_once`). No render;
no model runs in Phase 1. Basic Pitch and every other transcriber run only inside `learn/readerr_run.py`, by its own
interpreter (`-I`), in Phase 2.

The pure parts (the played trace's rule, the clean-up's losses, the anatomy's classes, the figures, the tracking
read with its orientation and tie rule, the freeze, the grid pick, the edge extension, the cross-set read, the real-DI
labeller, the runner contract's check, the screen's rule, RX_TABLE and its guard, the write and ledger guards) are
tested in tests/test_scratch_readerr.py on the light CI runner (no numpy); the trace against `synthesise_redo` with
numpy (skipped elsewhere).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import subprocess
import time

from learn import note_fixes as NF
from learn import note_rebuild as NR
from learn import note_transcribe as NT
from learn import note_truth as NTR
from learn import note_tx as TX
from learn import scratch_exact as SX
from learn import scratch_notes as SN
from learn import scratch_search as S

LEDGER_ID = S.LEDGER_ID                  # preset-ladder
PLAN = "docs/scratch-readerr-plan.md"
KEY_PREFIX = "phase_scratch_readerr"
PHASE = "phase_scratch_readerr"          # the declaration (the plan with its review's nine amendments, O1 to O4)
PHASE_FROZEN = "phase_scratch_readerr_frozen"     # Phase 1's five files' sha256 and the frozen figure: before Phase 2
PHASE_NOTES = "phase_scratch_readerr_notes"       # Phase 2a's note listing, hashed before `score` (declared, to come)
PHASE_OUTCOME = "phase_scratch_readerr_outcome"   # the one RX code, after an audit (to come)
GUARDED_PREFIXES = ("phase_fs", "phase_scratch_notes", "phase_nr", "phase_scratch_exact", "phase_replay", "phase_wc")
BUILD2, BANK_ARM = SX.BUILD2, SX.BANK_ARM          # the bank guitar: build 2's tr-di
DECIDING = SX.DECIDING                   # BKS+GOAT, the 40; all 47 beside
RUNNER = "learn/readerr_run.py"          # U2: Basic Pitch's grid and shifts, the downloaded transcribers
OWN_FILES = ("learn/scratch_readerr.py", RUNNER)


def _dedupe(xs):
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return tuple(out)


CODE_FILES = _dedupe(OWN_FILES + SX.CODE_FILES + NT.CODE_FILES + TX.CODE_FILES)
OUT_FILES = ("trace", "anatomy", "real-compare", "screen", "freeze")   # Phase 1's files, hashed in PHASE_FROZEN

# --- the anatomy's constants: existing ones only ----------------------------------------------------------------------
ONSET_S = NT.KNOWN_ONSET_S               # 0.050: same pitch, onsets within 50 ms, one to one, closest first
TIMING_S = 0.150                         # "timing": same pitch, onsets 50 to 150 ms apart (plan, Block B)
LEAD_S = TX.SOUNDING_LEAD_S              # 0.050: the truth notes sounding at an extra's onset (`extras_sorted`)
GHOST_INTERVALS = TX.VETO_INTERVALS      # (12, 19, 24): the ghost shape
CHORD_S = NR.CHORD_S                     # 0.050: the onset groups
BEND_SPAN = NR.BEND_MAX_SEMITONES        # 3: a bend fragment sits 1 to 3 semitones from a bent note sounding then
FRAME_S = NR.BEND_FRAME_S                # 11.6 ms: Basic Pitch's frames, the frame figures' grid
EXTRA_CLASSES = ("harmonic", "re-find", "octave-sub", "semitone-sub", "timing", "bend-fragment", "rest")
EXTRAS_SORTED = ("harmonic", "re-find", "other")   # `note_tx.extras_sorted`'s three, first (like for like)
MISS_CLASSES = ("substitution", "timing", "merged", "clean-up", "chord-member", "rest")
NEVER_SOUNDED = "never-sounded"          # an exact note the trace says never sounds: on the nominal list, apart
SIZE_BUCKETS = ("1", "2", "3+")

# --- the declared figure family, in order, with each figure's orientation ---------------------------------------------
# "error": higher is worse (the upper half is the worse half); "similarity": higher is better (the lower half is)
FAMILY = (
    ("note_error", "error"),             # 1 - note F on the as-played list: the default primary
    ("miss_rate", "error"),
    ("extra_rate", "error"),
    ("end_error", "error"),              # of the onset pairs, the share whose end misses (`note_tx.end_match`)
    ("attack_miss_rate", "error"),
    ("extra_attack_rate", "error"),
    ("frame_error", "error"),            # 1 - frame F on 11.6-ms frames, (frame, pitch) cells
    ("octave_folded_error", "error"),    # 1 - note F with pitch classes
    ("uncovered_time", "error"),         # the as-played list's sounding frames with no re-read note sounding
    ("false_time", "error"),             # the re-read's sounding frames with no as-played note sounding
) + tuple((f"extra_{c}", "error") for c in EXTRA_CLASSES) + tuple((f"miss_{c}", "error") for c in MISS_CLASSES) + (
    ("reread_env_corr", "similarity"),   # build.json's stored dry-domain figures against the bank guitar
    ("reread_logmel", "error"),
    ("reread_pause_excess", "error"),
    ("list_env_corr", "similarity"),
    ("list_logmel", "error"),
    ("list_pause_excess", "error"),
)
FIGURES = tuple(f for f, _ in FAMILY)
ORIENTATION = dict(FAMILY)
DEFAULT_FIGURE = "note_error"
FIDELITY_ONLY = "fidelity only"
SIGN_ONLY = "sign only, not on J0's scale, no size ruled out"
KEY_BROKEN = ("the median split breaks ties by part key here (BKS low, GOAT high is a set confound): read by "
              "Spearman only, never frozen")

# --- Phase 2's declared rules (pure; the commands come with their own amendment) ----------------------------------------
GRID_AXES = {"onset_threshold": (0.3, 0.4, 0.5, 0.6, 0.7, 0.8), "frame_threshold": (0.2, 0.3, 0.4, 0.5),
             "minimum_note_length": (58.0, 90.0, 127.7), "melodia_trick": (True, False)}
CONTINUOUS_AXES = ("onset_threshold", "frame_threshold", "minimum_note_length")
AXIS_RANGE = {"onset_threshold": (0.0, 1.0, "open"), "frame_threshold": (0.0, 1.0, "open"),
              "minimum_note_length": (1000.0 * FRAME_S, math.inf, "closed")}   # one Basic Pitch frame at least
STORED_POINT = {a: NT.BP_SETTINGS[a] for a in GRID_AXES}   # the frozen defaults: 0.5, 0.3, 58 ms, Melodia on
REAL_DI_FIELD = {"note_error": "f", "miss_rate": "recall", "extra_rate": "precision", "end_error": "end_accuracy"}
REAL_DI_FALLBACK = "f"                   # a frozen figure set_summary does not carry: note F, said beside
KINDS = ("setting", "transcriber", "reference")   # no download / downloaded and open / MuScriptor (never ships)
TIE_ORDER = ("setting", "transcriber")   # ties between kinds: no download first, then a licence the product can use
DOWNLOAD_RULES = (   # amendment 7 with the orchestrator's calls O4 to O8 on U4's manifest
    "every checkpoint pre-fetched to a pinned path with its sha256 in the manifest; every run offline "
    "(HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1, auto_download off, absolute checkpoint paths; YourMT3's file kept "
    "named last.ckpt)",
    "pickle safety: a standard-library pickletools scan lists every global before any load; torch.load("
    "weights_only=True) with exactly the expected globals allowlisted; any other global refuses; never "
    "weights_only=False",
    "after each load the missing and unexpected keys are reported; a missing key the model needs refuses",
    "two Python 3.12 environments, each from its project's own uv.lock (mt3-infer with torch 2.7.1; the Riley "
    "models with torch 2.8.0, the fork pinned at cfe28ed); code archives installed --no-deps --no-build-isolation, "
    "the commit and tree hashes binding",
    "MR-MT3 dropped (O5): the file mt3-infer loads is the original MT3 checkpoint, excluded on its scores",
    "licences (O8): every remaining item is fine for development; YourMT3+, guitar-fl, guitar-gaps and soxr go to "
    "the user only if one of them wins",
)
OFFLINE_ENV = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1"}

# --- the screen (O1: a beside line, never a pricing path) ---------------------------------------------------------------
SCREEN_PAIRS = (   # (world, new row, old row): new less old per part, on the 40, intent-to-treat (refusals at Cen)
    ("exact", "xn-swap", "xn-bank"), ("exact", "xn-reread", "xn-bank"), ("exact", "xn-list", "xn-bank"),
    ("exact", "xn-reread", "xn-list"), ("exact", "xn-swap", "xn-reread"), ("exact", "xn-swap", "xn-list"),
    ("real", "fs-both", "fs-stem"), ("real", "fs-notes:b1", "fs-stem"), ("real", "fs-notes:b2", "fs-stem"),
    ("real", "fs-notes:b1", "fs-both"), ("real", "fs-notes:b2", "fs-both"), ("real", "fs-notes:b2", "fs-notes:b1"),
)
SCREEN_HOLDS, NO_SCREEN = "holds", "no screen"


# --- the played trace (pure but for the bank's samples) ----------------------------------------------------------------

def played_trace(notes, length, bank, tuning_cents=0.0, ring="ring-soft", mutes=(), rate=NR.SR, cut=False):
    """`note_rebuild.synthesise_redo`'s placing, variety, skip and end rules, step for step, without the audio: per
    note whether it sounds, its string and fret, its end time and kind, whether it bends; its report's counts. The gains
    (levels, tilt, the loudness option) never change these, so one trace serves every pass of `rebuild_redo`. The
    samples' lengths come from `bank.note` and `note_rebuild.apply_bend` as the synthesis gets them. -> (per note,
    report)."""
    if ring not in NR.RING_VARIANTS:
        raise ValueError(ring)
    groups = NR.onset_groups(notes)
    src, busy, last, swaps, why = {}, {}, {}, 0, {}
    for g in groups:
        taken = set()
        for k in sorted(g, key=lambda q: (notes[q]["pitch"], q)):
            n = notes[k]
            p = n["pitch"]
            ringing = {s for s, e in busy.items() if e > n["on"]}
            sp = NR.placed_free(p, taken, ringing, bank.ok)
            if sp is None:
                why[k] = "no free string"
                continue
            prev = last.get(p)
            if prev is not None and n["on"] - prev[0] <= NR.VARIETY_S and sp == prev[1]:
                sp = NR.next_source(NR.variety_sources(p, sp, taken, bank.ok), prev[1])
                swaps += sp != prev[1]
            s, f = sp
            semis = p - NR.nominal_midi(s, f)
            if abs(semis) > NR.MAX_SHIFT_SEMITONES:
                why[k] = "shift over the limit"
                continue
            y = bank.note(s, f, 100.0 * semis + tuning_cents - bank.own_cents(s, f))
            src[k] = (s, f, y)
            end, _, _ = NR.note_end(n["on"], n["off"], ring, mutes, len(y) / rate - NR.PRE_ATTACK_S, cut=cut)
            busy[s] = max(busy.get(s, -math.inf), end)
            taken.add(s)
            last[p] = (n["on"], (s, f))
    by_string = {}
    for k in sorted(src, key=lambda q: (notes[q]["on"], q)):
        by_string.setdefault(src[k][0], []).append(k)
    nxt = {}
    for ks in by_string.values():
        for a, b in zip(ks, ks[1:]):
            nxt[a] = notes[b]["on"]
    per, skipped, ends, bent = [], 0, {}, 0
    for k, n in enumerate(notes):
        if k not in src:
            per.append({"played": False, "why": why[k]})
            skipped += 1
            continue
        s, f, y = src[k]
        steps = NR.bend_curve(n, notes)
        bends = any(steps)
        if bends:
            bent += 1
            y = NR.apply_bend(y, steps, NR.PRE_ATTACK_S, rate)
        end, kind, _ = NR.note_end(n["on"], n["off"], ring, mutes, len(y) / rate - NR.PRE_ATTACK_S, nxt.get(k),
                                   cut=cut)
        dur = min(len(y), int(round((end - n["on"] + NR.PRE_ATTACK_S) * rate)))
        if dur <= 0:
            per.append({"played": False, "why": "zero length", "bent": bends})
            skipped += 1
            continue
        ends[kind] = ends.get(kind, 0) + 1
        start = int(round((n["on"] - NR.PRE_ATTACK_S) * rate))
        per.append({"played": True, "string": s, "fret": f, "end_kind": kind, "bent": bends,
                    "end": (start + dur) / rate})
    rep = {"notes": len(notes), "played": len(notes) - skipped, "skipped": skipped, "groups": len(groups),
           "bent": bent, "variety_swaps": swaps, "ends": ends}
    return per, rep


TRACE_COUNTS = ("notes", "played", "skipped", "groups", "bent", "variety_swaps", "ends")


def trace_equals_report(rep, stored):
    """(Pure.) Proof 2: the trace's counts equal a stored `synthesise_redo` report's (played, skipped, ends by kind,
    bent, swaps, notes, groups)."""
    return all(rep.get(k) == (stored or {}).get(k) for k in TRACE_COUNTS)


def as_played(notes, per, length_s):
    """(Pure.) The as-played list: the notes that sound, each ending where it really ends (the end of its fade, inside
    the window), carrying its index in the nominal list. -> (notes, skipped indices)."""
    out, skipped = [], []
    for k, (n, t) in enumerate(zip(notes, per)):
        if not t["played"]:
            skipped.append(k)
            continue
        out.append(dict(n, off=max(n["on"], min(t["end"], length_s)), nominal=k, end_kind=t["end_kind"]))
    return out, skipped


# --- the re-read's own steps (pure) --------------------------------------------------------------------------------------

def cleanup_losses(notes):
    """(Pure.) `note_transcribe.clean_transcribed` step for step, keeping what it drops: a note out of MIDI range, or
    one that would be the seventh at once. A merged twin is not lost (it extends the first). -> (kept, lost)."""
    lo, hi = NT.KEEP_MIDI
    lost, up = [], []
    for n in notes:
        if not lo <= n["pitch"] <= hi:
            lost.append(dict(n, why="out_of_range"))
            continue
        if n["pitch"] < NT.OCTAVE_UP_BELOW:
            n = dict(n, pitch=n["pitch"] + 12)
        up.append(dict(n))
    kept = []
    for n in sorted(up, key=lambda n: (n["on"], n["pitch"], n["off"])):
        twin = next((m for m in kept if m["pitch"] == n["pitch"] and abs(m["on"] - n["on"]) < NT.MERGE_S), None)
        if twin is not None:
            twin["off"] = max(twin["off"], n["off"])
            continue
        if sum(m["on"] <= n["on"] < m["off"] for m in kept) >= NT.MAX_AT_ONCE:
            lost.append(dict(n, why="over_six"))
            continue
        kept.append(n)
    return kept, lost


def lost_on_timeline(events, pre_s, offset_s, length_s):
    """(Pure.) The clean-up's lost notes moved as `timed_notes` moves the kept ones (pre_s, then the window offset;
    no snap: the 50-ms tolerance holds the +-20-ms snap), inside the window."""
    _, lost = cleanup_losses(NT.notes_from_events(events))
    return NT.in_window(NR.shifted_notes(NR.shifted_notes(lost, -pre_s), offset_s), length_s)


def presnap_notes(events, pre_s, offset_s, length_s):
    """(Pure.) `timed_notes`' notes before the onset snap: the clean-up, pre_s, the window, the window offset (from its
    report). The snap keeps the order, so index j here is index j of the snapped list."""
    notes, _ = NT.clean_transcribed(NT.notes_from_events(events))
    return NR.shifted_notes(NT.in_window(NR.shifted_notes(notes, -pre_s), length_s), offset_s)


# --- the anatomy (pure) --------------------------------------------------------------------------------------------------

def pair_by(ref, est, key=lambda n: n["pitch"], onset_s=ONSET_S):
    """(Pure.) `match_notes`' one-to-one rule on any pitch key: onsets within `onset_s`, the closest first.
    -> [(i, j)]."""
    cand = sorted((abs(r["on"] - e["on"]), i, j) for i, r in enumerate(ref) for j, e in enumerate(est)
                  if key(r) == key(e) and abs(r["on"] - e["on"]) <= onset_s)
    ui, uj, out = set(), set(), []
    for _, i, j in cand:
        if i not in ui and j not in uj:
            ui.add(i)
            uj.add(j)
            out.append((i, j))
    return sorted(out)


def _bent(t, truth):
    return any(NR.bend_curve(t, truth))


def sounding_at(truth, t, lead=LEAD_S):
    return [x for x in truth if x["on"] - lead <= t < x["off"]]


def extra_class(e, truth, missed):
    """(Pure.) One unpaired re-read note's class, the first that holds: `extras_sorted`'s three against the truth
    notes sounding at its onset (from LEAD_S before their onset to their end): "harmonic" (12, 19 or 24 semitones
    above one), "re-find" (its pitch); then "other" split: "octave-sub" (a missed truth note 12 semitones away, onsets
    within 50 ms), "semitone-sub" (1 semitone), "timing" (a missed truth note of its pitch, onsets 50 to 150 ms apart),
    "bend-fragment" (1 to 3 semitones from a bent truth note sounding then, its curve read against the truth list),
    "rest". missed: the truth notes no re-read note pairs."""
    snd = sounding_at(truth, e["on"])
    if any(e["pitch"] - t["pitch"] in GHOST_INTERVALS for t in snd):
        return "harmonic"
    if any(e["pitch"] == t["pitch"] for t in snd):
        return "re-find"
    near = [t for t in missed if abs(t["on"] - e["on"]) <= ONSET_S]
    if any(abs(e["pitch"] - t["pitch"]) == 12 for t in near):
        return "octave-sub"
    if any(abs(e["pitch"] - t["pitch"]) == 1 for t in near):
        return "semitone-sub"
    if any(t["pitch"] == e["pitch"] and ONSET_S < abs(t["on"] - e["on"]) <= TIMING_S for t in missed):
        return "timing"
    if any(1 <= abs(e["pitch"] - t["pitch"]) <= BEND_SPAN and _bent(t, truth) for t in snd):
        return "bend-fragment"
    return "rest"


def miss_class(t, k, est, unpaired_est, lost, group_of, paired_truth, skipped=()):
    """(Pure.) One missed truth note's class, the first that holds: "never-sounded" (the trace's skipped notes, the
    nominal list only); "substitution" (an unpaired re-read note 1 or 12 semitones away, onsets within 50 ms);
    "timing" (an unpaired re-read note of its pitch, onsets 50 to 150 ms apart); "merged" (a re-read note of its pitch
    began more than 50 ms before it and still sounds at its onset: held through it); "clean-up" (a note the clean-up
    dropped, of its pitch, onsets within 50 ms: six at once or out of range); "chord-member" (its onset group holds 2
    or more notes and another of them pairs); "rest"."""
    if k in skipped:
        return NEVER_SOUNDED
    if any(abs(e["on"] - t["on"]) <= ONSET_S and abs(e["pitch"] - t["pitch"]) in (1, 12) for e in unpaired_est):
        return "substitution"
    if any(e["pitch"] == t["pitch"] and ONSET_S < abs(e["on"] - t["on"]) <= TIMING_S for e in unpaired_est):
        return "timing"
    if any(e["pitch"] == t["pitch"] and e["on"] < t["on"] - ONSET_S and e["off"] > t["on"] for e in est):
        return "merged"
    if any(x["pitch"] == t["pitch"] and abs(x["on"] - t["on"]) <= ONSET_S for x in lost):
        return "clean-up"
    g = group_of[k]
    if len(g) >= 2 and any(q != k and q in paired_truth for q in g):
        return "chord-member"
    return "rest"


def _stats(xs):
    xs = sorted(x for x in xs if x is not None and math.isfinite(x))
    if not xs:
        return {"n": 0, "median": None, "mean": None, "median_abs": None}
    a = sorted(abs(x) for x in xs)
    mid = len(xs) // 2
    med = xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2
    mabs = a[mid] if len(a) % 2 else (a[mid - 1] + a[mid]) / 2
    return {"n": len(xs), "median": med, "mean": sum(xs) / len(xs), "median_abs": mabs}


def _bucket(n):
    return "1" if n == 1 else "2" if n == 2 else "3+"


def ghost_shaped(truth):
    """(Pure.) The bench's bias: the truth notes 12, 19 or 24 semitones above another note of their own onset group
    (the veto's shape, Basic Pitch's ghost shape)."""
    out = set()
    for g in NR.onset_groups(truth):
        ps = {truth[k]["pitch"] for k in g}
        for k in g:
            if any(truth[k]["pitch"] - p in GHOST_INTERVALS for p in ps):
                out.add(k)
    return sorted(out)


def attacks(truth, est, onset_s=ONSET_S):
    """(Pure.) The onset groups: a truth group's attack is missed when no re-read onset lies within 50 ms of its first
    onset; a re-read group's attack is extra when no truth onset lies within 50 ms of its first onset."""
    tg, eg = NR.onset_groups(truth), NR.onset_groups(est)
    eon, ton = [e["on"] for e in est], [t["on"] for t in truth]
    missed = sum(1 for g in tg if not any(abs(x - truth[g[0]]["on"]) <= onset_s for x in eon))
    extra = sum(1 for g in eg if not any(abs(x - est[g[0]]["on"]) <= onset_s for x in ton))
    return {"truth_groups": len(tg), "attacks_missed": missed, "est_groups": len(eg), "extra_attacks": extra}


def anatomy(truth, est, presnap=None, lost=(), skipped=()):
    """(Pure.) One window's anatomy: every truth note and every re-read note in exactly one class (paired, or one of
    MISS_CLASSES / EXTRA_CLASSES, the nominal list's never-sounded notes apart), `extras_sorted`'s three counts beside;
    the pairs' onset errors before and after the snap (`presnap`: the re-read before it, same order), offset errors
    and ends (`note_tx.end_match`); bends (`note_fixes.bend_error`, `bent_but_cleared`); attacks; recall and
    precision by group size; the ghost-shaped share and recall on it. -> dict."""
    pairs = pair_by(truth, est)
    pt, pe = {i for i, _ in pairs}, {j for _, j in pairs}
    missed = [truth[i] for i in range(len(truth)) if i not in pt]
    unpaired_est = [est[j] for j in range(len(est)) if j not in pe]
    tgroups = NR.onset_groups(truth)
    group_of = {k: g for g in tgroups for k in g}
    est_cls = [None if j in pe else extra_class(est[j], truth, missed) for j in range(len(est))]
    tru_cls = [None if i in pt else miss_class(truth[i], i, est, unpaired_est, lost, group_of, pt, skipped)
               for i in range(len(truth))]
    sorted3 = TX.extras_sorted(truth, est, pe)
    ex = {c: est_cls.count(c) for c in EXTRA_CLASSES}
    mi = {c: tru_cls.count(c) for c in MISS_CLASSES + (NEVER_SOUNDED,)}
    on_after = [1000 * (est[j]["on"] - truth[i]["on"]) for i, j in pairs]
    on_before = ([1000 * (presnap[j]["on"] - truth[i]["on"]) for i, j in pairs]
                 if presnap is not None and len(presnap) == len(est) else None)
    off = [1000 * (est[j]["off"] - truth[i]["off"]) for i, j in pairs]
    right = sum(TX.end_match(truth[i], est[j]) for i, j in pairs)
    eg = NR.onset_groups(est)
    esize = {k: len(g) for g in eg for k in g}
    by_size = {}
    for b in SIZE_BUCKETS:
        ti = [i for i in range(len(truth)) if _bucket(len(group_of[i])) == b]
        ej = [j for j in range(len(est)) if _bucket(esize[j]) == b]
        by_size[b] = {"truth": len(ti), "recall": sum(i in pt for i in ti) / len(ti) if ti else None,
                      "est": len(ej), "precision": sum(j in pe for j in ej) / len(ej) if ej else None}
    gh = ghost_shaped(truth)
    rest = [i for i in range(len(truth)) if i not in set(gh)]
    m, nt, ne = len(pairs), len(truth), len(est)
    return {"truth": nt, "est": ne, "matched": m, "extras": ex, "extras_sorted": sorted3, "misses": mi,
            "est_classes": est_cls, "truth_classes": tru_cls,
            "precision": m / ne if ne else None, "recall": m / nt if nt else None,
            "f": 2 * m / (nt + ne) if nt + ne else None,
            "onset_ms_after_snap": _stats(on_after), "onset_ms_before_snap": _stats(on_before or []),
            "presnap_aligned": on_before is not None, "offset_ms": _stats(off), "ends_right": right,
            "bend": NF.bend_error(truth, est), "bent_but_cleared": len(NF.bent_but_cleared(est)),
            "attacks": attacks(truth, est), "by_group_size": by_size,
            "ghost_shaped": {"notes": len(gh), "share": len(gh) / nt if nt else None,
                             "recall": sum(i in pt for i in gh) / len(gh) if gh else None,
                             "recall_rest": sum(i in pt for i in rest) / len(rest) if rest else None}}


def partition_holds(an):
    """(Pure.) Every truth note and every re-read note sits in exactly one class, and the totals reconcile (the
    partition test)."""
    t_ok = an["matched"] + sum(an["misses"].values()) == an["truth"] == len(an["truth_classes"])
    e_ok = an["matched"] + sum(an["extras"].values()) == an["est"] == len(an["est_classes"])
    s_ok = (an["extras_sorted"]["harmonic"] == an["extras"]["harmonic"]
            and an["extras_sorted"]["re-find"] == an["extras"]["re-find"]
            and an["extras_sorted"]["other"] == sum(an["extras"][c] for c in EXTRA_CLASSES[2:]))
    return t_ok and e_ok and s_ok


def frame_cells(notes, length_s, key=lambda n: n["pitch"], frame=FRAME_S):
    """(Pure.) The (frame, pitch) cells a list sounds on: frame q's centre (q + 0.5) x frame in [on, off), inside
    the window."""
    nq = int(length_s / frame)
    out = set()
    for n in notes:
        q0 = max(0, int(math.ceil(n["on"] / frame - 0.5)))
        q = q0
        while q < nq and (q + 0.5) * frame < n["off"]:
            if (q + 0.5) * frame >= n["on"]:
                out.add((q, key(n)))
            q += 1
    return out


def frame_figures(truth, est, length_s):
    """(Pure.) Frame error (1 - frame F on (frame, pitch) cells), uncovered time (the truth's sounding frames with no
    re-read note sounding, over the truth's sounding frames) and false time (the re-read's sounding frames with no truth
    note sounding, over the re-read's)."""
    tc, ec = frame_cells(truth, length_s), frame_cells(est, length_s)
    tp = len(tc & ec)
    d = len(tc) + len(ec)
    tf, ef = {q for q, _ in tc}, {q for q, _ in ec}
    return {"frame_error": 1 - 2 * tp / d if d else None,
            "uncovered_time": len(tf - ef) / len(tf) if tf else None,
            "false_time": len(ef - tf) / len(ef) if ef else None}


def pause_excess(fig):
    """(Pure.) A stored dry guitar's pause share less the bank guitar's, the mean over J0's frame sizes
    (`note_rebuild.mask_agreement`'s `pauses_dry` less `pauses_true`)."""
    mask = (fig or {}).get("mask") or {}
    d = [v["pauses_dry"] - v["pauses_true"] for v in mask.values()
         if v.get("pauses_dry") is not None and v.get("pauses_true") is not None]
    return sum(d) / len(d) if d else None


def dry_figures(guitars):
    """(Pure.) The stored dry-domain figures of both guitars against the bank guitar, from build.json's part record."""
    out = {}
    for g, name in (("xn-reread", "reread"), ("xn-list", "list")):
        fig = ((guitars or {}).get(g) or {}).get("figures") or {}
        out[f"{name}_env_corr"] = fig.get("env_corr")
        out[f"{name}_logmel"] = fig.get("logmel")
        out[f"{name}_pause_excess"] = pause_excess(fig)
    return out


def note_figures(an, truth, est, length_s):
    """(Pure.) A window's note figures from its anatomy against one truth: every FAMILY figure but the dry-domain six.
    A rate per exact note divides by the truth's notes."""
    nt, ne, m = an["truth"], an["est"], an["matched"]
    fold = pair_by(truth, est, key=lambda n: n["pitch"] % 12)
    a = an["attacks"]
    out = {"note_error": None if an["f"] is None else 1 - an["f"],
           "miss_rate": (nt - m) / nt if nt else None, "extra_rate": (ne - m) / ne if ne else None,
           "end_error": 1 - an["ends_right"] / m if m else None,
           "attack_miss_rate": a["attacks_missed"] / a["truth_groups"] if a["truth_groups"] else None,
           "extra_attack_rate": a["extra_attacks"] / a["est_groups"] if a["est_groups"] else None,
           "octave_folded_error": 1 - 2 * len(fold) / (nt + ne) if nt + ne else None,
           **frame_figures(truth, est, length_s)}
    for c in EXTRA_CLASSES:
        out[f"extra_{c}"] = an["extras"][c] / nt if nt else None
    for c in MISS_CLASSES:
        out[f"miss_{c}"] = an["misses"][c] / nt if nt else None
    return out


# --- the tracking read and the freeze (pure) -----------------------------------------------------------------------------

def key_broken(values, lower, upper):
    """(Pure.) Whether `median_split`'s split puts equal values on both sides (it breaks ties by part key)."""
    if not lower or not upper:
        return False
    return max(values[k] for k in lower) == min(values[k] for k in upper)


def oriented(iv, orientation):
    """(Pure.) An interval on the "higher is worse" side: a similarity's turned over."""
    if iv is None or orientation == "error":
        return iv
    return {"mean": -iv["mean"], "lo90": -iv["hi90"], "hi90": -iv["lo90"]}


def tracking_read(cost, values, orientation, interval_of):
    """(Pure but for `interval_of`.) A figure against reading proper per part (`cost`): `scratch_notes.by_figure`
    (Spearman, the median split); the worse half is the upper for an error, the lower for a similarity; each half's
    interval (`interval_of(keys)`, `set_rows`' BKS+GOAT pool); `diff_interval(worse, better)` labelled by
    `paired_reading` at its defaults (on J0's scale). It tracks when the label reads "worse", rho's sign agrees with
    the orientation and the split is not key-broken. -> dict."""
    if orientation not in ("error", "similarity"):
        raise ValueError(orientation)
    v = {k: values.get(k) for k in cost}
    fig = SN.by_figure(cost, v)
    lower, upper = fig["lower"], fig["upper"]
    broken = key_broken(v, lower, upper)
    worse, better = (upper, lower) if orientation == "error" else (lower, upper)
    iv_w, iv_b = (interval_of(worse) if worse else None), (interval_of(better) if better else None)
    d = SN.diff_interval(iv_w, iv_b)
    label = SN.paired_reading(d)
    rho = fig["spearman"]
    agrees = rho is not None and (rho > 0 if orientation == "error" else rho < 0)
    reading = (label or {}).get("reading")
    return {"orientation": orientation, "parts": fig["parts"], "spearman": rho, "rho_agrees": agrees,
            "worse_half": worse, "better_half": better, "worse": iv_w, "better": iv_b, "difference": d,
            "label": label, "key_broken": broken, "note": KEY_BROKEN if broken else None,
            "tracks": reading == "worse" and agrees and not broken}


def freeze_rule(reads):
    """(Pure.) The frozen figure: of the figures that track, the one with the largest |rho| (ties: FAMILY's order);
    none tracks: note error, labelled "fidelity only". -> {figure, orientation, how, code}."""
    cand = [f for f in FIGURES if (reads.get(f) or {}).get("tracks")]
    if not cand:
        return {"figure": DEFAULT_FIGURE, "orientation": ORIENTATION[DEFAULT_FIGURE], "how": FIDELITY_ONLY,
                "code": "RX-untracked"}
    best = max(cand, key=lambda f: (abs(reads[f]["spearman"]), -FIGURES.index(f)))
    return {"figure": best, "orientation": ORIENTATION[best], "how": "tracks", "code": "RX-tracks",
            "spearman": reads[best]["spearman"]}


def read_disagreement(primary, beside):
    """(Pure.) The passing-only read (primary, amendment 3) against intent-to-treat (beside): None, or what differs."""
    diff = [k for k in ("figure", "code") if primary.get(k) != beside.get(k)]
    return None if not diff else {k: {"passing_only": primary.get(k), "itt": beside.get(k)} for k in diff}


# --- Phase 2's pick (pure; declared now) ---------------------------------------------------------------------------------

def point_key(pt):
    return tuple(pt[a] for a in GRID_AXES)


def grid_points(axes=None):
    """(Pure.) The grid's points in a fixed order (onset, frame, minimum length, Melodia; 144 at the declaration)."""
    axes = axes or GRID_AXES
    out = [{}]
    for a, vals in axes.items():
        out = [dict(p, **{a: v}) for p in out for v in vals]
    return out


def grid_distance(p, q, axes):
    """(Pure.) L1 in grid steps on the continuous axes (each value's place among that axis's values in play) plus one
    step when Melodia differs."""
    d = 0
    for a in CONTINUOUS_AXES:
        vals = sorted(axes[a])
        d += abs(vals.index(p[a]) - vals.index(q[a]))
    return d + (p["melodia_trick"] != q["melodia_trick"])


def spans_zero(iv):
    return bool(iv) and iv.get("lo90") is not None and iv.get("hi90") is not None and iv["lo90"] <= 0 <= iv["hi90"]


def grid_pick(points, mean_of, diff_of, orientation="error", stored=None, axes=None):
    """(Pure but for the callables.) The grid's pick, no bars (amendment 4). The minimum: the point with the best
    pooled BKS+GOAT mean of the frozen figure (`mean_of(point)`; lowest for an error, highest for a similarity; ties
    nearest the stored point, then by key). Then every point whose paired difference against it (`diff_of(point,
    minimum)`, per part through `set_rows`) spans zero. Of those and the minimum, the point nearest the frozen defaults
    (`grid_distance`), ties to the stored point, then the better mean, then by key. -> {minimum, near, pick,
    distance, edge}."""
    stored = stored or STORED_POINT
    axes = axes or {a: sorted({p[a] for p in points} | {stored[a]}, key=lambda v: (v is True, v))
                    for a in GRID_AXES}
    sign = 1 if orientation == "error" else -1
    scored = [p for p in points if mean_of(p) is not None]
    if not scored:
        return None
    mn = min(scored, key=lambda p: (sign * mean_of(p), grid_distance(p, stored, axes), point_key(p)))
    near = [mn] + [p for p in scored if point_key(p) != point_key(mn) and spans_zero(diff_of(p, mn))]
    pick = min(near, key=lambda p: (grid_distance(p, stored, axes), point_key(p) != point_key(stored),
                                    sign * mean_of(p), point_key(p)))
    return {"minimum": mn, "near": near, "pick": pick, "distance": grid_distance(pick, stored, axes),
            "edge": edge_extensions(mn, axes), "selected_from": len(points)}


def _within(axis, v):
    lo, hi, kind = AXIS_RANGE[axis]
    return (lo < v < hi) if kind == "open" else (lo <= v <= hi)


def edge_extensions(point, axes=None):
    """(Pure.) A minimum on an axis's edge extends that axis by the axis's own step at that edge (the gap to its
    neighbour), bounded only by the parameter's own range. -> {"extend": [{axis, side, value}], "blocked": [...]}"""
    axes = axes or GRID_AXES
    ext, blocked = [], []
    for a in CONTINUOUS_AXES:
        vals = sorted(axes[a])
        if len(vals) < 2:
            continue
        v = point[a]
        for side, edge, nb in (("low", vals[0], vals[1]), ("high", vals[-1], vals[-2])):
            if v != edge:
                continue
            new = round(edge - (nb - edge), 6)
            if _within(a, new):
                ext.append({"axis": a, "side": side, "value": new})
            else:
                blocked.append({"axis": a, "side": side, "value": new, "why": "outside the parameter's own range"})
    return {"extend": ext, "blocked": blocked}


def sign_label(iv, orientation="error"):
    """(Pure.) `paired_reading(small=0, big=0)` on a candidate's paired difference against the stored re-read, turned
    so "better" is the candidate's: sign only. "matches" cannot occur; "level" needs a zero-width interval."""
    r = SN.paired_reading(oriented(iv, orientation), small=0, big=0)
    return None if r is None else dict(r, words=SIGN_ONLY)


def cross_set(iv_goat_from_bks, iv_bks_from_goat, orientation="error"):
    """(Pure.) A selected candidate's read (the grid's pick, the shift vote's k): picked on BKS and read on GOAT, and
    the reverse. Decided better only when both read better, worse only when both read worse; otherwise undecided (a
    sign disagreement is named). -> {label, reads, sign_disagreement}."""
    a, b = sign_label(iv_goat_from_bks, orientation), sign_label(iv_bks_from_goat, orientation)
    ra, rb = (a or {}).get("reading"), (b or {}).get("reading")
    lab = "better" if ra == rb == "better" else "worse" if ra == rb == "worse" else "undecided"
    ma = (oriented(iv_goat_from_bks, orientation) or {}).get("mean")
    mb = (oriented(iv_bks_from_goat, orientation) or {}).get("mean")
    dis = ma is not None and mb is not None and (ma < 0) != (mb < 0)
    return {"label": lab, "reads": {"bks_pick_on_goat": a, "goat_pick_on_bks": b}, "sign_disagreement": dis,
            "words": SIGN_ONLY}


def real_di_label(iv, figure):
    """(Pure.) The real-DI arm's labeller (amendment 5): `paired_reading(0, 0)` on `note_tx.set_summary`'s
    file-clustered interval (the named exception to `set_rows`) of the field the frozen figure maps to, whose
    orientation against tx-bp is higher-is-better; turned so the label is the candidate's. Never `clear_above` or
    `decided_worse`. -> {field, label, words}."""
    field = REAL_DI_FIELD.get(figure, REAL_DI_FALLBACK)
    r = sign_label(iv, "similarity")
    return {"field": field, "label": (r or {}).get("reading"), "words": SIGN_ONLY,
            "note": None if figure in REAL_DI_FIELD else f"{figure} is not a set_summary field: note F read instead"}


def real_di_lead(labels, bench_label):
    """(Pure.) The beside line "real-DI lead" (amendment 5): better on P1, P2 and the lists by the frozen figure, not
    better on the bench. labels: {"P1", "P2", "lists": label}."""
    return all(labels.get(g) == "better" for g in ("P1", "P2", "lists")) and bench_label != "better"


def without_ghosts(truth, est):
    """(Pure.) The read beside each candidate on the exact list with its ghost-shaped notes left out, and the re-read
    notes they pair with: a gain only on Basic Pitch-shaped notes then shows. -> (truth, est)."""
    gh = set(ghost_shaped(truth))
    pairs = dict(pair_by(truth, est))
    drop_e = {pairs[i] for i in gh if i in pairs}
    return ([t for i, t in enumerate(truth) if i not in gh], [e for j, e in enumerate(est) if j not in drop_e])


# --- the outcome table (pure) --------------------------------------------------------------------------------------------

RX_TABLE = (    # (code, phase, when (the first that holds in its phase), next)
    ("RX-stop", 1, "a Phase 1 proof fails", "stop; to the orchestrator; nothing read"),
    ("RX-tracks", 1, "a declared figure's worse half costs more, labelled 'worse', rho agreeing, not key-broken",
     "that figure is frozen; Phase 2 scores by it"),
    ("RX-untracked", 1, "no figure tracks",
     "note error stays, labelled 'fidelity only'; Phase 2 still runs; recommend pricing a matched-notes-only hybrid "
     "as one xr- row before any transcriber (no screen: O1)"),
    ("RX-transcriber", 2, "a downloaded open transcriber is decided better than the best Basic Pitch variant on the "
     "bench, not decided worse on Guitar-TECHS or the lists",
     "to the user with the licence table and one priced xr- row"),
    ("RX-setting", 2, "a no-download setting or post-fix is decided better on the bench, not decided worse on real DIs",
     "to the user with one priced xr- row"),
    ("RX-harm", 2, "better on the bench, decided worse on Guitar-TECHS or the lists", "reported; not proposed for "
     "pricing"),
    ("RX-reference-only", 2, "only a non-product reference is decided better", "headroom shown; no open tool reaches "
     "it; to the user"),
    ("RX-undecided", 2, "a product candidate better by the mean, none decided",
     "to the user; undecided is not failed; option: price the top two as xr- rows (no screen: O1)"),
    ("RX-none", 2, "nothing better than the stored re-read", "Basic Pitch as frozen stays; to the user with the "
     "re-derivation track's result beside"),
)
RX_CODES = tuple(c for c, *_ in RX_TABLE)
PHASE1_CODES = tuple(c for c, ph, *_ in RX_TABLE if ph == 1)
PHASE2_CODES = ("RX-stop",) + tuple(c for c, ph, *_ in RX_TABLE if ph == 2)


def rx_table_guard():
    """Refuse unless RX_TABLE holds the nine declared codes in order, the prefix sits outside every guarded prefix and
    the family's orientations are declared."""
    if RX_CODES != ("RX-stop", "RX-tracks", "RX-untracked", "RX-transcriber", "RX-setting", "RX-harm",
                    "RX-reference-only", "RX-undecided", "RX-none"):
        raise SystemExit("RX_TABLE's codes are not the nine declared, in order")
    if KEY_PREFIX.startswith(GUARDED_PREFIXES) or not KEY_PREFIX.startswith("phase_scratch_"):
        raise SystemExit(f"{KEY_PREFIX} sits under a guarded prefix")
    if set(ORIENTATION.values()) - {"error", "similarity"} or len(FIGURES) != len(set(FIGURES)):
        raise SystemExit("the figure family's orientations are not declared once each")


def _row(code):
    return next(r for r in RX_TABLE if r[0] == code)


def rx_phase1(proofs_hold, frozen):
    """(Pure.) Phase 1's code: RX-stop on a failed proof, else the freeze's (RX-tracks or RX-untracked)."""
    code = "RX-stop" if not proofs_hold else frozen["code"]
    r = _row(code)
    return {"code": code, "when": r[2], "next": r[3]}


def rx_code(proofs_hold, cands):
    """(Pure.) Phase 2's one code, the first that holds. cands: [{name, kind (KINDS), bench ("better", "worse",
    "undecided" or None: the 40's sign read, or the cross-set read for a selected candidate), mean_better (bool),
    real_worse (decided worse on P1, P2 or the lists), beats_best_setting (transcribers: decided better than the best
    decided Basic Pitch setting)}]. A transcriber needs `beats_best_setting` only when some setting is decided better
    without harm (otherwise the best Basic Pitch variant is the stored re-read itself). -> {code, when, next,
    candidates}."""
    if not proofs_hold:
        code, who = "RX-stop", []
    else:
        prod = [c for c in cands if c["kind"] in TIE_ORDER]
        ok = [c for c in prod if c.get("bench") == "better" and not c.get("real_worse")]
        ok_set = [c for c in ok if c["kind"] == "setting"]
        ok_tx = [c for c in ok if c["kind"] == "transcriber" and (not ok_set or c.get("beats_best_setting"))]
        harm = [c for c in prod if c.get("bench") == "better" and c.get("real_worse")]
        ref = [c for c in cands if c["kind"] == "reference" and c.get("bench") == "better"]
        und = [c for c in prod if c.get("mean_better") and c.get("bench") != "better"]
        for code, who in (("RX-transcriber", ok_tx), ("RX-setting", ok_set), ("RX-harm", harm),
                          ("RX-reference-only", ref), ("RX-undecided", und), ("RX-none", [None])):
            if who:
                break
    r = _row(code)
    return {"code": code, "when": r[2], "next": r[3], "candidates": [c["name"] for c in who if c]}


def screen_line(pairs):
    """(Pure.) `screen-check`'s beside line: "holds" when every stored pair keeps its `paired_reading` label at
    checkpoint 50, else "no screen". Never a pricing path (O1). pairs: [{answer: label, cp50: label}]."""
    ok = bool(pairs) and all((p.get("answer") or {}).get("reading") == (p.get("cp50") or {}).get("reading")
                             and (p.get("answer") or {}).get("reading") is not None for p in pairs)
    return SCREEN_HOLDS if ok else NO_SCREEN


def sign_agreement(a, b):
    """(Pure.) The share of parts where two per-part differences have the same sign (sign equality; amendment 9)."""
    ks = [k for k in a if k in b and a[k] is not None and b[k] is not None]
    return sum((a[k] > 0) == (b[k] > 0) for k in ks) / len(ks) if ks else None


# --- the runner contract (pure; `learn/readerr_run.py`, PR #617) ------------------------------------------------------------

RECORD_KEYS = ("mode", "versions", "model_sha256", "threads", "spec", "input_sha256", "seconds", "events")
EVENT_KEYS = ("on", "off", "pitch", "amp", "bends")
RUNNER_MODES = ("bp-grid", "bp-shift", "mt3", "kong")
SPEC_COMMON = ("model", "model_sha256", "threads", "lead_in_s")
SPEC_MODE = {"bp-grid": ("settings", "grid"), "bp-shift": ("settings", "offsets_s"), "mt3": ("options",),
             "kong": ("options",)}
SPEC_REQUIRED = {"bp-grid": ("model", "model_sha256", "settings", "grid"),
                 "bp-shift": ("model", "model_sha256", "settings", "offsets_s"),
                 "mt3": ("model", "model_sha256"), "kong": ("model", "model_sha256")}
MAX_THREADS = 2
BP_SETTING_KEYS = tuple(NT.BP_SETTINGS)  # bp_run.SETTING_KEYS: the runner's `settings` holds exactly these


def make_spec(mode, model, model_sha256, threads=1, lead_in_s=None, **kw):
    """(Pure.) A runner spec, refused here as the runner would refuse it: only the contract's keys (`model` and
    `model_sha256` always, Basic Pitch included; `threads` 1 or 2; `lead_in_s`; `settings` exactly bp_run's keys and
    `grid` {axis: [values]} for bp-grid; `settings` and `offsets_s` (each >= 0, no repeats) for bp-shift; `options`
    for mt3 and kong)."""
    if mode not in RUNNER_MODES:
        raise SystemExit(f"{mode!r}: not a runner mode {list(RUNNER_MODES)}")
    spec = {"model": str(model), "model_sha256": model_sha256, "threads": threads}
    if lead_in_s is not None:
        spec["lead_in_s"] = lead_in_s
    extra = sorted(set(kw) - set(SPEC_MODE[mode]))
    if extra:
        raise SystemExit(f"{mode}: unknown spec keys {extra}")
    spec.update({k: v for k, v in kw.items() if v is not None})
    miss = [k for k in SPEC_REQUIRED[mode] if k not in spec]
    if miss:
        raise SystemExit(f"{mode}: the spec lacks {miss}")
    if not _is_sha(model_sha256):
        raise SystemExit("model_sha256 is not a sha256")
    if not isinstance(threads, int) or not 1 <= threads <= MAX_THREADS:
        raise SystemExit(f"threads must be 1 to {MAX_THREADS}")
    if "settings" in spec and sorted(spec["settings"]) != sorted(BP_SETTING_KEYS):
        raise SystemExit(f"settings must be exactly {sorted(BP_SETTING_KEYS)}")
    if "grid" in spec and (not isinstance(spec["grid"], dict) or set(spec["grid"]) - set(GRID_AXES)):
        raise SystemExit(f"grid must be {{axis: [values]}} over {list(GRID_AXES)}")
    if "offsets_s" in spec:
        offs = spec["offsets_s"]
        if not isinstance(offs, list) or any(o < 0 for o in offs) or len(set(offs)) != len(offs):
            raise SystemExit("offsets_s: each >= 0, no repeats")
    return spec


def declared_grid_spec():
    """(Pure.) The declared grid as the runner's `grid` ({axis: [values]})."""
    return {a: list(v) for a, v in GRID_AXES.items()}


def expected_grid(spec):
    """(Pure.) The runner's grid points for a bp-grid spec, in its order: the product over (onset, frame, minimum
    length, Melodia), the first axis outermost, an axis left out of `grid` holding the base value; full settings."""
    base, grid = spec["settings"], spec["grid"]
    out = [dict(base)]
    for a in GRID_AXES:
        out = [dict(p, **{a: v}) for p in out for v in grid.get(a, [base[a]])]
    return out


def runner_argv(python, mode, spec, pairs):
    """(Pure but for the repo's path.) The call: PY -I learn/readerr_run.py MODE --spec JSON in.wav out.json
    [in.wav out.json ...] (the model is loaded once)."""
    from learn import pipeline_fix as P

    args = [str(python), "-I", str(pathlib.Path(P.REPO) / RUNNER), mode, "--spec", json.dumps(spec, sort_keys=True)]
    for src, dst in pairs:
        args += [str(src), str(dst)]
    return args


def events_refusal(events):
    if not isinstance(events, list):
        return "events is not a list"
    for e in events:
        if not isinstance(e, dict) or any(k not in e for k in EVENT_KEYS):
            return f"an event lacks one of {list(EVENT_KEYS)}"
        if not (isinstance(e["on"], (int, float)) and isinstance(e["off"], (int, float)) and e["off"] >= e["on"]):
            return "an event's times are not on <= off"
        if e["on"] < 0 or e["off"] <= 0:
            return "an event lies before the input's own timeline (the runner drops or clips those)"
        if not isinstance(e["bends"], list):
            return "an event's bends is not a list"
    return None


def runner_refusal(rec, mode, spec, input_sha):
    """(Pure.) Why a runner record may not be used, or None: every contract key; the mode, spec, model sha256 and
    input's sha256 as asked; every event's shape, on the input's own timeline (the runner re-bases shifts and
    lead-ins: events ending at or before 0 dropped, onsets clipped to 0). `bp-grid`: the points exactly
    `expected_grid`'s, in its order, and the top-level events those read at the base settings (equal to the base
    point's when it is on the grid). `bp-shift`: the offsets those asked, in order, each with its whole-sample pad,
    and the top-level events the zero offset's read (empty when 0 is not asked)."""
    if not isinstance(rec, dict):
        return "not a record"
    miss = [k for k in RECORD_KEYS if k not in rec]
    if miss:
        return f"the record lacks {miss}"
    if rec["mode"] != mode:
        return f"the record's mode {rec['mode']!r} is not {mode!r}"
    if rec["spec"] != spec:
        return "the record's spec is not the one asked"
    if rec["model_sha256"] != spec.get("model_sha256"):
        return "the record's model is not the spec's"
    if rec["input_sha256"] != input_sha:
        return "the record's input sha256 is not this input's"
    why = events_refusal(rec["events"])
    if why:
        return why
    if mode == "bp-grid":
        got = rec.get("grid")
        if not isinstance(got, list):
            return "bp-grid's record has no grid"
        if [g.get("settings") for g in got] != expected_grid(spec):
            return "bp-grid's points are not the spec's grid, in the runner's order"
        for g in got:
            why = events_refusal(g.get("events"))
            if why:
                return f"grid point {point_key(g['settings'])}: {why}"
        base = next((g for g in got if g["settings"] == spec["settings"]), None)
        if base is not None and base["events"] != rec["events"]:
            return "bp-grid's top-level events are not the base point's"
    if mode == "bp-shift":
        got = rec.get("shifts")
        if not isinstance(got, list) or [s.get("offset_s") for s in got] != list(spec["offsets_s"]):
            return "bp-shift's offsets are not those asked, in order"
        for s in got:
            if not isinstance(s.get("pad_samples"), int) or s["pad_samples"] < 0:
                return f"shift {s.get('offset_s')}: no whole-sample pad"
            why = events_refusal(s.get("events"))
            if why:
                return f"shift {s.get('offset_s')}: {why}"
        zero = next((s for s in got if s["offset_s"] == 0), None)
        if rec["events"] != (zero["events"] if zero is not None else []):
            return "bp-shift's top-level events are not the zero offset's read"
    return None


def runner_notes(events, frame=FRAME_S):
    """(Pure.) A runner record's events as notes (`note_transcribe.notes_from_events`), with a clipped note's bends
    trimmed to its onset. The runner clips an onset below 0 to 0 and keeps the bend track as read (#617), so that
    track starts before `on`; Basic Pitch's track holds one value a frame over the note, so a note at exactly 0 whose
    track is longer than round((off - on) / frame) frames loses its leading extra frames. Every other note is
    unchanged."""
    out = []
    for n in NT.notes_from_events(events):
        b = n["bends"]
        extra = len(b) - int(round((n["off"] - n["on"]) / frame)) if n["on"] == 0.0 else 0
        out.append(dict(n, bends=b[extra:]) if extra > 0 else n)
    return out


def runner_env(base, downloaded):
    """(Pure.) The runner's environment: a downloaded transcriber runs offline (amendment 7)."""
    return dict(base, **OFFLINE_ENV) if downloaded else dict(base)


def checkpoint_refusal(entry, sha):
    """(Pure.) A checkpoint may be loaded only from the manifest's pinned path with the manifest's sha256."""
    if not isinstance(entry, dict) or not entry.get("path") or not entry.get("sha256"):
        return "the manifest pins no path and sha256 for this checkpoint"
    if entry["sha256"] != sha:
        return f"the checkpoint's sha256 {sha[:12]} is not the manifest's {entry['sha256'][:12]}"
    return None


# --- the real-DI guard (amendment 6) -------------------------------------------------------------------------------------

REAL_KINDS = ("truth", "list")


def real_di_source(source, listing=None):
    """Every real-DI input of this track goes through here: only a consistent P1 or P2 truth window of the hashed
    listing (its files through `note_truth.refuse_path`) or one of the ten lists, by `note_tx.declared_input`. P3, a
    GOAT item, a part, a song or any path refuses. -> the declared row."""
    kind = source.split(":", 1)[0] if isinstance(source, str) else None
    if kind not in REAL_KINDS:
        raise SystemExit(f"{source!r}: this track's real-DI material is P1 and P2 truth windows and the ten lists only")
    return TX.declared_input(source, listing, None)


def real_path_refusal(path):
    """(Pure.) `note_truth.refuse_path`: P3 and anything outside P1's and P2's download folders refuse."""
    return NTR.refuse_path(path)


# --- writes, the ledger and the guard ------------------------------------------------------------------------------------

def readerr_dir():
    return S.fs_dir() / "readerr"


def out_path(name):
    if name not in OUT_FILES:
        raise ValueError(name)
    return readerr_dir() / f"{name}.json"


def write_once(path, obj):
    """The only write: under PF/fs/readerr/, never over an existing file."""
    path = pathlib.Path(path)
    root = pathlib.Path(readerr_dir()).resolve()
    if root not in path.resolve().parents:
        raise SystemExit(f"{path}: outside {root}: this track writes only there")
    if path.exists():
        raise SystemExit(f"{path} exists: never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if tmp.exists():
        raise SystemExit(f"{tmp} exists: a write was interrupted; to the orchestrator")
    tmp.write_text(json.dumps(obj, indent=1, default=str) + "\n")
    tmp.replace(path)
    return file_sha(path)


def file_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _is_sha(v):
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def ledger_body_refusal(body):
    """(Pure.) Why a hash PR's ledger body holds more than hashes and counts, or None: keys ending in `_sha256` hold
    sha256 hex, `counts` holds integers by declared name, `code` an RX code, `figure` a FAMILY name, `screen` the
    screen's line; nothing else."""
    for k, v in body.items():
        if k.endswith("_sha256"):
            if not _is_sha(v):
                return f"{k} is not a sha256"
        elif k == "counts":
            if not isinstance(v, dict) or not all(isinstance(x, int) and not isinstance(x, bool) for x in v.values()):
                return "counts holds a non-integer"
            if not all(isinstance(n, str) and n.replace("_", "").isalnum() for n in v):
                return "a count's name is not a plain name"
        elif k == "code":
            if v not in RX_CODES:
                return f"{v!r} is not an RX code"
        elif k == "figure":
            if v not in FIGURES:
                return f"{v!r} is not a declared figure"
        elif k == "screen":
            if v not in (SCREEN_HOLDS, NO_SCREEN):
                return f"{v!r} is not the screen's line"
        else:
            return f"{k}: a ledger body holds hashes and counts only"
    return None


def frozen_body(shas, counts, code, figure, screen):
    """(Pure.) PHASE_FROZEN's body: Phase 1's five files' sha256, counts, the Phase 1 code, the frozen figure and the
    screen's line; refused if it holds anything else."""
    body = {f"{n.replace('-', '_')}_sha256": shas[n] for n in OUT_FILES}
    body.update(counts=dict(counts), code=code, figure=figure, screen=screen)
    why = ledger_body_refusal(body)
    if why:
        raise SystemExit(why)
    return body


def _git(*a):
    from learn import pipeline_fix as P

    return subprocess.run(["git", "-C", str(P.REPO), *a], capture_output=True, text=True)


def pinned_identity():
    """Proof 3: each of CODE_FILES exists here and on origin/main and equals main's. -> {file: identical}."""
    from learn import pipeline_fix as P

    out = {}
    for f in CODE_FILES:
        here = (pathlib.Path(P.REPO) / f).exists()
        on_main = _git("cat-file", "-e", f"origin/main:{f}").returncode == 0
        out[f] = here and on_main and _git("diff", "--quiet", "origin/main", "--", f).returncode == 0
    return out


def keys_refusal(local, main):
    """(Pure.) Why this checkout's `phase_scratch_readerr*` keys are not main's, or None."""
    a = {k: v for k, v in (local or {}).items() if k.startswith(KEY_PREFIX)}
    b = {k: v for k, v in (main or {}).items() if k.startswith(KEY_PREFIX)}
    if a != b:
        return f"this checkout's {sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))} differ from main's"
    return None


EXACT_NEEDS = (SX.PHASE_TARGETS,) + tuple(SX.answers_key(r) for r in SX.ROWS) + (SX.PHASE_OUTCOME,)


def require_readerr(*phases):
    """Refuse unless this checkout runs main's code and keys (the exact test's guard, then this module's own:
    CODE_FILES and the `phase_scratch_readerr*` keys) and main holds the exact test's targets, answers and outcome,
    this declaration and `phases`. -> main's `preset-ladder` entry."""
    from learn import note_replay as NRp

    rx_table_guard()
    m = SX.require_exact(*EXACT_NEEDS, PHASE, *phases)
    bad = [f for f, ok in pinned_identity().items() if not ok]
    if bad:
        raise SystemExit(f"this checkout's {bad} differ from main's (or are not on main): run from merged code")
    why = keys_refusal(NRp.ledger_entry(), m)
    if why:
        raise SystemExit(why)
    return m


def require_out(name, m=None):
    """A Phase 1 file: it exists; with `m` (Phase 2), its sha256 is main's PHASE_FROZEN's."""
    p = out_path(name)
    if not p.exists():
        raise SystemExit(f"no {p.name} (run `{name if name != 'screen' else 'screen-check'}` first)")
    if m is not None:
        why = SX.field_refusal(m, PHASE_FROZEN, f"{name.replace('-', '_')}_sha256", file_sha(p))
        if why:
            raise SystemExit(why)
    return json.loads(p.read_text())


def require_trace(m=None):
    tr = require_out("trace", m)
    if not tr.get("proofs_hold"):
        raise SystemExit("trace.json's proofs did not hold: RX-stop, nothing read")
    return tr


def deciding_keys(draw):
    return {p["pkey"] for p in draw["parts"] if p["set"] in DECIDING}


def _pooled(sd, draw, vals, keys=None):
    r = SN.set_rows(sd, draw, {k: v for k, v in vals.items() if v is not None and math.isfinite(v)}, keys)
    return ((r or {}).get("bks_goat") or {}).get("all")


# --- Phase 1: trace (zero renders) -----------------------------------------------------------------------------------------

def npy_bytes_sha(x32):
    """The sha256 of `np.save`'s file for an array, without writing it (as build.json's `NR.file_sha` of the .npy)."""
    import io

    import numpy as np

    buf = io.BytesIO()
    np.save(buf, x32)
    return hashlib.sha256(buf.getvalue()).hexdigest()


def cmd_trace(_args):
    """Phase 1, first (zero renders, no model run), once: per part the exact list as `scratch_exact.cmd_build` makes it
    (`timed_notes`, `apply_fixes` with build 2's fixes), its played trace (`played_trace` with the true DI's tuning and
    mutes, as build 2's `tr-di` was made) and as-played list; the stored re-read (`exact/work/reread/`) through
    `timed_notes` and the fixes, its notes before the snap and the clean-up's losses. The four proofs: (1)
    `match_notes(exact, re-read)` equals build.json's `reread_f` on every part; (2) the trace's counts equal build 2's
    stored `tr-di` report on every part; (3) CODE_FILES equal main's; (4) this module's rebuild of the re-read
    reproduces `dry/xn-reread`'s sha256 on every part. Written with the proofs either way; every later command refuses
    unless they hold (RX-stop). -> trace.json."""
    m = require_readerr()
    path = out_path("trace")
    NT.never_overwrite(path)
    import numpy as np

    _, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    b2 = SX.bank_build(m)
    xb = SX.require_xbuild(m)
    _draw, _sd = SX.context()
    t0 = time.time()
    pinned = pinned_identity()
    fixes, ring, loud = b2["fixes"], b2["ring_variant"], b2.get("loud_gamma")
    if (fixes, ring, loud) != (xb["fixes"], xb["ring_variant"], xb["loud_gamma"]):
        raise SystemExit("build.json's rule is not build 2's")
    pair = NT.install_pair(NT.load_manifest())
    excl, _, _, _ = NT._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    todo = NT.build_todo(pair, NT.ear_items_file(BUILD2))
    parts = [t for t in todo if t[0] == "part"]
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": 0, "bank_build_sha256": xb["bank_build_sha256"],
           "build_sha256": file_sha(SX.build_path()), "fixes": fixes, "ring_variant": ring, "loud_gamma": loud,
           "parts": {}}
    bad = {1: [], 2: [], 4: []}
    for j, (_kind, key, _info, rec, di, finish) in enumerate(parts):
        length_s = len(di) / NR.SR
        notes, _ = NT.timed_notes(rec, di)
        exact, _ = NF.apply_fixes(notes, fixes, di)
        per, rep = played_trace(exact, len(di) + int(round(NR.END_PAD_S * NR.SR)), bank, NR.global_tuning_cents(di),
                                ring, NR.mute_times(di))
        played, skipped = as_played(exact, per, length_s)
        stored_rep = b2["parts"][key]["arms"][BANK_ARM]["report"]
        if not trace_equals_report(rep, stored_rep):
            bad[2].append(key)
        rr = json.loads((SX.work_dir() / "reread" / f"{j:03d}-{BANK_ARM}.json").read_text())
        if rr.get("model_sha256") != pair[1] or rr.get("settings") != NT.BP_SETTINGS:
            raise SystemExit(f"{key}: the stored re-read comes from another model or other settings")
        bank64 = np.asarray(NT.load_dry(BANK_ARM, key, b2), np.float64)
        rnotes, trep = NT.timed_notes({"events": rr["events"], "pre_s": 0.0}, bank64)
        rfixed, _ = NF.apply_fixes(rnotes, fixes, bank64)
        f_now = {k: v for k, v in NT.match_notes(exact, rfixed).items() if k != "ref_matched"}
        if f_now != xb["parts"][key]["reread_f"]:
            bad[1].append(key)
        y, _ = NR.rebuild_redo(BANK_ARM, rfixed, len(bank64), bank, bank64, ring, finish=finish, loud=loud)
        if npy_bytes_sha(np.asarray(y, np.float32)) != xb["parts"][key]["guitars"]["xn-reread"]["sha256"]:
            bad[4].append(key)
        off_s = trep["window_offset_ms"] / 1000.0
        out["parts"][key] = {
            "length_s": length_s, "nominal": exact, "played": played, "skipped": skipped, "trace": per,
            "trace_report": rep, "reread": rfixed, "reread_timing": trep,
            "presnap": presnap_notes(rr["events"], 0.0, off_s, len(bank64) / NR.SR),
            "lost": lost_on_timeline(rr["events"], 0.0, off_s, len(bank64) / NR.SR), "reread_f": f_now}
        print(f"part {j + 1} of {len(parts)}: trace {'=' if key not in bad[2] else 'DIFFERS'}, re-read F "
              f"{'=' if key not in bad[1] else 'DIFFERS'}, rebuild {'=' if key not in bad[4] else 'DIFFERS'}",
              flush=True)
    n = len(parts)
    out["proofs"] = {"reread_f_equal": n - len(bad[1]), "trace_equal": n - len(bad[2]),
                     "pinned": pinned, "rebuild_equal": n - len(bad[4]), "parts": n,
                     "differing_parts": {str(k): len(v) for k, v in bad.items()}}
    out["proofs_hold"] = not any(bad.values()) and all(pinned.values())
    out["code"] = None if out["proofs_hold"] else "RX-stop"
    out["seconds"] = round(time.time() - t0, 1)
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    sha = write_once(path, out)
    print(f"RX TRACE: proofs (1) re-read F {n - len(bad[1])} of {n}, (2) trace {n - len(bad[2])} of {n}, (3) pinned "
          f"{sum(pinned.values())} of {len(pinned)}, (4) rebuild {n - len(bad[4])} of {n} -> "
          f"{'hold' if out['proofs_hold'] else 'RX-stop: to the orchestrator'}; {out['seconds']} s; sha256 {sha}")


# --- Phase 1: anatomy (zero renders) ---------------------------------------------------------------------------------------

def part_anatomy(row, guitars):
    """(Pure.) One part's anatomy against both truths (nominal: what `xn-list` consumed; as played: what a perfect
    transcriber could hear), and its figures (as played, with build.json's dry-domain six)."""
    est, L = row["reread"], row["length_s"]
    nom = anatomy(row["nominal"], est, row["presnap"], row["lost"], set(row["skipped"]))
    pla = anatomy(row["played"], est, row["presnap"], row["lost"])
    figs = dict(note_figures(pla, row["played"], est, L), **dry_figures(guitars))
    figs["note_error_nominal"] = None if nom["f"] is None else 1 - nom["f"]      # beside, not in the family
    return {"nominal": nom, "played": pla, "figures": figs,
            "partition_holds": partition_holds(nom) and partition_holds(pla)}


def pooled_counts(ans):
    """(Pure.) Class counts summed over windows."""
    out = {"truth": 0, "est": 0, "matched": 0, "extras": {c: 0 for c in EXTRA_CLASSES},
           "extras_sorted": {c: 0 for c in EXTRAS_SORTED}, "misses": {c: 0 for c in MISS_CLASSES + (NEVER_SOUNDED,)}}
    for a in ans:
        for k in ("truth", "est", "matched"):
            out[k] += a[k]
        for grp in ("extras", "extras_sorted", "misses"):
            for c, v in a[grp].items():
                out[grp][c] += v
    return out


def cmd_anatomy(_args):
    """Phase 1 (zero renders), once, after `trace`: every exact and re-read note in exactly one class on both truths;
    the figures per part. -> anatomy.json."""
    m = require_readerr()
    tr = require_trace()
    path = out_path("anatomy")
    NT.never_overwrite(path)
    xb = SX.require_xbuild(m)
    parts = {k: part_anatomy(r, xb["parts"][k]["guitars"]) for k, r in sorted(tr["parts"].items())}
    bad = sorted(k for k, a in parts.items() if not a["partition_holds"])
    if bad:
        raise SystemExit(f"the partition does not hold on {len(bad)} part(s): a bug, nothing written")
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": 0, "trace_sha256": file_sha(out_path("trace")),
           "family": [list(f) for f in FAMILY], "parts": parts,
           "pooled": {t: pooled_counts([a[t] for a in parts.values()]) for t in ("nominal", "played")},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    sha = write_once(path, out)
    p = out["pooled"]["played"]
    print(f"RX ANATOMY: {len(parts)} parts; as played {p['truth']} notes, re-read {p['est']}, matched {p['matched']}; "
          f"extras {p['extras']}; misses {p['misses']}; sha256 {sha}")


# --- Phase 1: real-compare (zero renders, no model run) ------------------------------------------------------------------

def cmd_real_compare(_args):
    """Phase 1 (zero renders, no model run), once, after `trace`: the same anatomy on the stored Guitar-TECHS windows
    (the truth report's note files, by their recorded sha256, against the hashed truth listing; every window through
    `real_di_source`: P3 never) and the ten lists (the install gate's stored events against the known notes); per
    window the truth report's stored counts and track 1's stored `tx-bp` extras reproduced beside. -> real-compare.json."""
    require_readerr()
    require_trace()
    path = out_path("real-compare")
    NT.never_overwrite(path)
    from learn import song_bank as SB

    mr, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    listing = NT.require_truth(mr)
    report = NT.require_truth_report(mr.get(NR.LEDGER_ID))
    pair = NT.install_pair(NT.load_manifest())
    ta = NT.TruthAudio(listing)
    by_key = {w["key"]: w for w in listing["windows"]}
    tx_read = TX.read_path()
    stored_tx = {}
    if tx_read.exists():
        stored_tx = {r["key"]: ((r.get("figures") or {}).get("tx-bp") or {}).get("extras")
                     for r in json.loads(tx_read.read_text())["body"].get("real") or []}
    rows, repro, tx_same = [], 0, 0
    for w in report["windows"]:
        real_di_source(f"truth:{w['key']}", listing)
        win = by_key[w["key"]]
        di, _, _, truth = ta.window(win)
        rec = TX.bp_note("truth", w["key"], w["note_file_sha256"], pair)
        est, trep = NT.timed_notes(rec, di)
        L, off_s = len(di) / NR.SR, trep["window_offset_ms"] / 1000.0
        an = anatomy(truth, est, presnap_notes(rec["events"], rec["pre_s"], off_s, L),
                     lost_on_timeline(rec["events"], rec["pre_s"], off_s, L))
        mt = NT.match_notes(truth, est)
        same = (mt["matched"], mt["ref"], mt["est"]) == (w["matched"], w["ref"], w["est"])
        repro += same
        tx_same += stored_tx.get(w["key"]) == an["extras_sorted"]
        rows.append({"group": w["player"], "kind": w["kind"], "key": w["key"], "anatomy": an,
                     "figures": note_figures(an, truth, est, L), "reproduces_truth_report": same,
                     "partition_holds": partition_holds(an)})
    excl, _, _, _ = NT._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    known = TX.gate_known()
    for nm in sorted(NT.KNOWN_NOTES):
        real_di_source(f"list:{nm}")
        di = SB.measure(NT.known_audio(nm, bank))
        truth = [dict(n) for n in NT.KNOWN_NOTES[nm]]
        est, trep = NT.timed_notes({"events": known[nm], "pre_s": 0.0}, di)
        L, off_s = len(di) / NR.SR, trep["window_offset_ms"] / 1000.0
        an = anatomy(truth, est, presnap_notes(known[nm], 0.0, off_s, L), lost_on_timeline(known[nm], 0.0, off_s, L))
        rows.append({"group": "lists", "kind": None, "key": nm, "anatomy": an,
                     "figures": note_figures(an, truth, est, L), "partition_holds": partition_holds(an)})
    bad = [r["key"] for r in rows if not r["partition_holds"]]
    if bad:
        raise SystemExit(f"the partition does not hold on {len(bad)} window(s): a bug, nothing written")
    groups = ("P1", "P2", "lists")
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": 0, "model_runs": 0,
           "truth_report_sha256": file_sha(NT.truth_report_path()),
           "tx_read_sha256": file_sha(tx_read) if tx_read.exists() else None, "windows": rows,
           "pooled": {g: pooled_counts([r["anatomy"] for r in rows if r["group"] == g]) for g in groups},
           "pooled_real": pooled_counts([r["anatomy"] for r in rows if r["group"] in ("P1", "P2")]),
           "reproduces_truth_report": repro, "truth_windows": len(report["windows"]),
           "reproduces_tx_extras": tx_same, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    sha = write_once(path, out)
    print(f"RX REAL-COMPARE: {len(report['windows'])} truth windows (counts reproduced on {repro}, track 1's extras on "
          f"{tx_same}), {len(NT.KNOWN_NOTES)} lists; real extras {out['pooled_real']['extras_sorted']}; sha256 {sha}")


# --- Phase 1: screen-check (stored scores, zero renders) -------------------------------------------------------------------

def real_row_numbers(m, draw, sd, rby, row):
    """A stored real row's per-part numbers (passing) and intent-to-treat, from its hashed answers and score files."""
    if row in ("fs-stem", "fs-both"):
        ans = S.require_hash(S.phase_answers(row), S.answers_path(row))
        sha, score = S.file_sha(S.answers_path(row)), (lambda k: S.score_path(row, k))
    else:
        name = None if row == "fs-notes:b1" else row.split(":", 1)[1]
        ans = NT.require_file_hash(m, SN.answers_key(name), SN.answers_path(name))
        sha, score = S.file_sha(SN.answers_path(name)), (lambda k: SN.score_path(k, name))
    per, refused, *_ = S.read_row_parts(draw, ans, sha, score, sd, rby)
    return {"per": per, "itt": S.itt_per(per, refused)}


def screen_pair(sd, draw, new, old, keys):
    """One stored pair's screen read: the answer's and checkpoint 50's paired difference on the 40 (intent-to-treat,
    refusals at Cen) with intervals and `paired_reading` labels; per-part Spearman and sign agreement on the passing
    parts of the 40."""
    out = {}
    for arm, f in (("answer", "G"), ("cp50", "G_cp50")):
        iv = _pooled(sd, draw, SX.paired(new["itt"], old["itt"], f))
        out[arm] = SN.paired_reading(iv)
        out[f"{arm}_interval"] = iv
    a = {k: v for k, v in SX.paired(new["per"], old["per"], "G").items() if k in keys}
    b = {k: v for k, v in SX.paired(new["per"], old["per"], "G_cp50").items() if k in keys}
    ks = sorted(set(a) & set(b))
    out["spearman"] = SN.spearman([(a[k], b[k]) for k in ks])
    out["sign_agreement"] = sign_agreement(a, b)
    out["passing_parts"] = len(ks)
    return out


def cmd_screen_check(_args):
    """Phase 1 (zero renders), once, after `trace`: for every pair in SCREEN_PAIRS, the checkpoint-50 paired
    difference beside the answer's; the line "holds" only when every pair keeps its label, else "no screen". A beside
    line only (O1): never a pricing path. -> screen.json."""
    m = require_readerr()
    require_trace()
    path = out_path("screen")
    NT.never_overwrite(path)
    from learn import note_replay as R

    draw, sd = SX.context()
    rby = {p["pkey"]: p for p in R.require_draw()["parts"]}
    keys = deciding_keys(draw)
    rows = {r: SX.row_numbers(m, draw, r) for r in SX.ROWS}
    for r in sorted({x for _, a, b in SCREEN_PAIRS for x in (a, b) if x not in SX.ROWS}):
        rows[r] = real_row_numbers(m, draw, sd, rby, r)
    pairs = [dict(screen_pair(sd, draw, rows[a], rows[b], keys), world=w, new=a, old=b) for w, a, b in SCREEN_PAIRS]
    line = screen_line(pairs)
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": 0, "pairs": pairs, "line": line,
           "pricing_path": False, "o1": "the screen is a beside line only; it never prices a row",
           "flipped": [f"{p['new']} - {p['old']}" for p in pairs
                       if (p["answer"] or {}).get("reading") != (p["cp50"] or {}).get("reading")],
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    sha = write_once(path, out)
    print(f"RX SCREEN-CHECK: {line}; flipped {out['flipped']}; sha256 {sha}")


# --- Phase 1: freeze (zero renders) ----------------------------------------------------------------------------------------

def tracking_reads(cost, values_of, interval_of):
    """(Pure but for `interval_of`.) Every FAMILY figure's tracking read. values_of: {figure: {pkey: value}}."""
    return {f: tracking_read(cost, values_of.get(f) or {}, o, interval_of) for f, o in FAMILY}


def cmd_freeze(_args):
    """Phase 1, last (zero renders), once, after `trace` and `anatomy`: reading proper per part (G(xn-reread) -
    G(xn-list), `scratch_exact.row_numbers`), passing-only primary (amendment 3), intent-to-treat beside with any
    disagreement stated; every FAMILY figure's tracking read on the 40 (all 47 beside); `freeze_rule`; Phase 1's code.
    Its sha256 and the other four go into the ledger as phase_scratch_readerr_frozen before anything in Phase 2.
    -> freeze.json."""
    m = require_readerr()
    tr = require_trace()
    an = require_out("anatomy")
    for n in OUT_FILES[:-1]:
        require_out(n)
    if an.get("trace_sha256") != file_sha(out_path("trace")):
        raise SystemExit("anatomy.json was made from another trace.json")
    path = out_path("freeze")
    NT.never_overwrite(path)
    draw, sd = SX.context()
    keys = deciding_keys(draw)
    rr, rl = SX.row_numbers(m, draw, "xn-reread"), SX.row_numbers(m, draw, "xn-list")
    costs = {"passing_only": SX.paired(rr["per"], rl["per"]), "itt": SX.paired(rr["itt"], rl["itt"])}
    values_of = {f: {k: a["figures"].get(f) for k, a in an["parts"].items()} for f in FIGURES}

    def interval_of(ks):
        return _pooled(sd, draw, {k: cur[k] for k in ks})
    reads, frozen = {}, {}
    for name, cost in costs.items():
        for scope, sub in (("deciding", keys), ("all_47", None)):
            cur = {k: v for k, v in cost.items() if sub is None or k in sub}
            r = tracking_reads(cur, values_of, interval_of)
            reads[f"{name}|{scope}"] = r
            if scope == "deciding":
                frozen[name] = freeze_rule(r)
    primary = frozen["passing_only"]
    code = rx_phase1(tr["proofs_hold"], primary)
    shas = {n: file_sha(out_path(n)) for n in OUT_FILES[:-1]}
    scr = json.loads(out_path("screen").read_text())["line"]
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": 0, "shas": shas,
           "parts": {"passing_only": len([k for k in costs["passing_only"] if k in keys]),
                     "itt": len([k for k in costs["itt"] if k in keys])},
           "reads": reads, "frozen": primary, "frozen_itt": frozen["itt"],
           "disagreement": read_disagreement(primary, frozen["itt"]), "code": code, "screen": scr,
           "multiplicity": f"{len(FIGURES)} figures on about 40 parts: about {len(FIGURES) // 20} false 'worse' by "
                           "chance; every figure is reported; the forward test is the first priced row",
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    sha = write_once(path, out)
    shas["freeze"] = sha
    body = frozen_body(shas, {"parts": len(an["parts"]), "figures": len(FIGURES), "tracking":
                              sum(1 for r in reads["passing_only|deciding"].values() if r["tracks"])},
                       code["code"], primary["figure"], scr)
    print(f"RX FREEZE: {code['code']}: {primary['figure']} ({primary['how']}); intent-to-treat "
          f"{frozen['itt']['figure']} ({frozen['itt']['code']}); disagreement {out['disagreement']}; screen {scr}")
    print(f"the ledger body for {PHASE_FROZEN}: {json.dumps(body)}")


# --- Phase 2 (declared, not built) -------------------------------------------------------------------------------------------

PHASE2_STUB = ("Phase 2's commands are declared, not built: the candidates' run flow (the grid runner's note listing, "
               "the shift vote's clustering, the downloads' manifest) comes with its own amendment and review first")


def cmd_score(_args):
    require_readerr(PHASE_FROZEN)
    raise SystemExit(PHASE2_STUB)


def cmd_read(_args):
    require_readerr(PHASE_FROZEN)
    raise SystemExit(PHASE2_STUB)


COMMANDS = {"trace": cmd_trace, "anatomy": cmd_anatomy, "real-compare": cmd_real_compare,
            "screen-check": cmd_screen_check, "freeze": cmd_freeze, "score": cmd_score, "read": cmd_read}


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
