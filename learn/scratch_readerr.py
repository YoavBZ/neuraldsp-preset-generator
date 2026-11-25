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
    $MAIN -m learn.scratch_readerr score           # Phase 2a: unit C, not built here (refuses)
    $MAIN -m learn.scratch_readerr read            # the RX read: after the xr- row (refuses)

The Phase 2 amendment's `xr-` row (`phase_scratch_readerr_p2`; plan section 9):

    $MAIN -m learn.scratch_readerr xr-build [--set first]   # zero renders: xr-matched, hand-plain; four proofs
    # the hash PR: phase_scratch_readerr_xr_dry, before any search
    $MAIN -m learn.scratch_readerr xr-check                 # about 50 renders: xn-reread's search and score again
    $MAIN -m learn.scratch_readerr xr-search --row xr-matched --shard 0/3 [--rerun]
    $MAIN -m learn.scratch_readerr xr-answers --row xr-matched   # -> phase_scratch_readerr_xr_answers_matched
    $MAIN -m learn.scratch_readerr xr-score --row xr-matched --shard 0/3 [--rerun]
    $MAIN -m learn.scratch_readerr xr-read                  # zero renders, once: E, M, XH_TABLE's code

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
from learn import note_versions as NV
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


LAZY_IMPORTS = ("learn/note_replay.py", "learn/pipeline_fix.py", "learn/song_bank.py",   # imported inside
                "learn/cc_build.py", "learn/full_controls_c1b.py", "learn/local_objective.py",   # commands
                "learn/knob_ceiling.py", "analysis/aligned.py")
CODE_FILES = _dedupe(OWN_FILES + SX.CODE_FILES + NT.CODE_FILES + TX.CODE_FILES + LAZY_IMPORTS)
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
MISS_CLASSES = ("clean-up", "substitution", "timing", "merged", "chord-member", "rest")   # after never-sounded
NEVER_SOUNDED = "never-sounded"          # an exact note the trace says never sounds: on the nominal list, apart
MISS_ORDER = (NEVER_SOUNDED,) + MISS_CLASSES   # the primary order: never-sounded, then clean-up, then the rest
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
    ("reread_pause_error", "error"),   # the mask disagreement (1 - agree), else |excess|
    ("list_env_corr", "similarity"),
    ("list_logmel", "error"),
    ("list_pause_error", "error"),
)
FIGURES = tuple(f for f, _ in FAMILY)
DRY_FIGURES = tuple(f for f in FIGURES if f.startswith(("reread_", "list_")))   # no real-DI version
NOTE_FIGURES = tuple(f for f in FIGURES if f not in DRY_FIGURES)
CONTROL_FIGURES = tuple(f for f in FIGURES if f.startswith("list_"))   # xn-list's guitar: controls, never frozen
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
              "minimum_note_length": (1000.0 * FRAME_S, 1000.0 * NTR.WINDOW_S, "closed")}   # one Basic Pitch frame
                                         # at least; at most the window (a longer minimum keeps no note)
STORED_POINT = {a: NT.BP_SETTINGS[a] for a in GRID_AXES}   # the frozen defaults: 0.5, 0.3, 58 ms, Melodia on
REAL_DI_FALLBACK = "note_error"         # a dry-domain frozen figure has no real-DI version: note F (1 - F) instead
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
    "rest". missed: the truth notes no re-read note pairs. An extra's "octave-sub" can only be an octave below: an
    octave above a missed truth note with onsets within 50 ms always sounds against it, so it reads "harmonic" first.
    (A miss's "substitution" counts both directions.)"""
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


def miss_holds(t, k, est, unpaired_est, lost, group_of, paired_truth, skipped=()):
    """(Pure.) Every miss class that holds for one missed truth note, in MISS_ORDER: "never-sounded" (the trace's
    skipped notes, the nominal list only); "clean-up" (a note the clean-up dropped, of its pitch, onsets within 50 ms:
    six at once or out of range); "substitution" (an unpaired re-read note 1 or 12 semitones away, either direction,
    onsets within 50 ms); "timing" (an unpaired re-read note of its pitch, onsets 50 to 150 ms apart); "merged" (a
    re-read note of its pitch began more than 50 ms before it and still sounds at its onset: held through it);
    "chord-member" (its onset group holds 2 or more notes and another of them pairs). -> [classes] ("rest" when
    none holds)."""
    out = []
    if k in skipped:
        out.append(NEVER_SOUNDED)
    if any(x["pitch"] == t["pitch"] and abs(x["on"] - t["on"]) <= ONSET_S for x in lost):
        out.append("clean-up")
    if any(abs(e["on"] - t["on"]) <= ONSET_S and abs(e["pitch"] - t["pitch"]) in (1, 12) for e in unpaired_est):
        out.append("substitution")
    if any(e["pitch"] == t["pitch"] and ONSET_S < abs(e["on"] - t["on"]) <= TIMING_S for e in unpaired_est):
        out.append("timing")
    if any(e["pitch"] == t["pitch"] and e["on"] < t["on"] - ONSET_S and e["off"] > t["on"] for e in est):
        out.append("merged")
    g = group_of[k]
    if len(g) >= 2 and any(q != k and q in paired_truth for q in g):
        out.append("chord-member")
    return out or ["rest"]


def miss_class(t, k, est, unpaired_est, lost, group_of, paired_truth, skipped=()):
    """(Pure.) One missed truth note's primary class: the first of `miss_holds` in MISS_ORDER (never-sounded, then
    clean-up, then the rest)."""
    return miss_holds(t, k, est, unpaired_est, lost, group_of, paired_truth, skipped)[0]


def miss_overlap(holds):
    """(Pure.) Beside the primary class: per class, the misses where it holds at all, and per pair of classes, the
    misses where both hold. holds: [[classes]] for the missed notes."""
    per = {c: sum(c in h for h in holds) for c in MISS_ORDER}
    pairs = {}
    for h in holds:
        for i, a in enumerate(h):
            for b in h[i + 1:]:
                pairs[f"{a}+{b}"] = pairs.get(f"{a}+{b}", 0) + 1
    return {"holds": per, "pairs": dict(sorted(pairs.items())), "more_than_one": sum(len(h) > 1 for h in holds)}


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
    tru_all = [None if i in pt else miss_holds(truth[i], i, est, unpaired_est, lost, group_of, pt, skipped)
               for i in range(len(truth))]
    tru_cls = [None if h is None else h[0] for h in tru_all]
    sorted3 = TX.extras_sorted(truth, est, pe)
    ex = {c: est_cls.count(c) for c in EXTRA_CLASSES}
    mi = {c: tru_cls.count(c) for c in MISS_ORDER}
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
            "est_classes": est_cls, "truth_classes": tru_cls, "truth_classes_all": tru_all,
            "miss_overlap": miss_overlap([h for h in tru_all if h is not None]),
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


def pause_error(fig):
    """(Pure.) The pause figure (an error): the playing-frame mask's disagreement with the bank guitar's, 1 - agree,
    the mean over J0's frame sizes, where `mask_agreement` stored it; else |pause excess|. The signed excess goes
    beside."""
    mask = (fig or {}).get("mask") or {}
    d = [1 - v["agree"] for v in mask.values() if v.get("agree") is not None]
    if d:
        return sum(d) / len(d)
    e = pause_excess(fig)
    return None if e is None else abs(e)


def dry_figures(guitars):
    """(Pure.) The stored dry-domain figures of both guitars against the bank guitar, from build.json's part record."""
    out = {}
    for g, name in (("xn-reread", "reread"), ("xn-list", "list")):
        fig = ((guitars or {}).get(g) or {}).get("figures") or {}
        out[f"{name}_env_corr"] = fig.get("env_corr")
        out[f"{name}_logmel"] = fig.get("logmel")
        out[f"{name}_pause_error"] = pause_error(fig)
    return out


def dry_beside(guitars):
    """(Pure.) Beside the family, never in it: each guitar's signed pause excess."""
    return {f"{name}_pause_excess_signed": pause_excess((((guitars or {}).get(g) or {}).get("figures")))
            for g, name in (("xn-reread", "reread"), ("xn-list", "list"))}


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
    the `list_*` figures (xn-list's guitar) are controls, read and reported but never frozen; none tracks: note error,
    labelled "fidelity only". -> {figure, orientation, how, code}."""
    cand = [f for f in FIGURES if (reads.get(f) or {}).get("tracks") and f not in CONTROL_FIGURES]
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


def edge_rounds(axes, minimum_of):
    """(Pure but for `minimum_of`.) The edge rule repeated: `minimum_of(axes)` (the grid's minimum once every point
    on `axes` is read) is extended by `edge_extensions`, the new values joined to their axes, and read again, until
    the minimum leaves the edge or the parameter's range blocks every extension it asks for. No round cap: the ranges
    bound it. -> {axes, minimum, rounds: [{minimum, extend, blocked}]}."""
    axes = {a: tuple(v) for a, v in axes.items()}
    rounds = []
    while True:
        mn = minimum_of(axes)
        e = edge_extensions(mn, axes)
        rounds.append({"minimum": mn, **e})
        if not e["extend"]:
            return {"axes": axes, "minimum": mn, "rounds": rounds}
        for x in e["extend"]:
            axes[x["axis"]] = tuple(sorted(set(axes[x["axis"]]) | {x["value"]}))


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


def real_di_figure(figure):
    """(Pure.) The figure the real-DI arm reads: the frozen figure itself (`note_figures` per window), or note error
    (1 - note F) for the six dry-domain figures, which have no real-DI version."""
    return figure if figure in NOTE_FIGURES else REAL_DI_FALLBACK


def real_di_interval(rows, cand, figure, group):
    """(Pure.) The real-DI arm's interval (amendment 5; the named exception to `set_rows`): per window of `group`
    ("P1", "P2", "lists"), the candidate's frozen figure less Basic Pitch's (`rows`: real-compare's windows, each with
    its `note_figures` and its file `cluster`; cand: {window key: the candidate's `note_figures`}), then
    `note_versions.set_numbers`, `note_tx.set_summary`'s file-clustered mean and 90% t interval."""
    fig = real_di_figure(figure)
    d = []
    for r in rows:
        c = (cand.get(r["key"]) or {}).get(fig)
        b = (r.get("figures") or {}).get(fig)
        if r["group"] == group and c is not None and b is not None:
            d.append((r["cluster"], {"d": c - b}))
    return NV.set_numbers(d, "d")


def real_di_label(iv, figure):
    """(Pure.) The real-DI arm's labeller: `paired_reading(0, 0)` on `real_di_interval`'s interval, the candidate
    less tx-bp on the frozen figure (or note error for a dry-domain one), turned by that figure's orientation so
    "better" is the candidate's. Never `clear_above` or `decided_worse`. -> {figure, label, words, note}."""
    fig = real_di_figure(figure)
    r = sign_label(iv, ORIENTATION[fig])
    return {"figure": fig, "label": (r or {}).get("reading"), "words": SIGN_ONLY,
            "note": None if fig == figure else f"{figure} has no real-DI version: note F (as note error) read instead"}


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


# Basic Pitch's own time map (basic_pitch.note_creation.model_frames_to_time and its constants), in pure Python
BP_SR, BP_HOP = 22050, 256               # AUDIO_SAMPLE_RATE, FFT_HOP
BP_ANNOT_N_FRAMES = (BP_SR // BP_HOP) * 2   # ANNOTATIONS_FPS x AUDIO_WINDOW_LENGTH: 172
BP_AUDIO_N_SAMPLES = BP_SR * 2 - BP_HOP  # AUDIO_N_SAMPLES: 43,844
BP_WINDOW_OFFSET = (BP_HOP / BP_SR) * (BP_ANNOT_N_FRAMES - BP_AUDIO_N_SAMPLES / BP_HOP) + 0.0018   # its magic number


def bp_frame_time(i):
    """(Pure.) `model_frames_to_time` for frame i: i x hop / sr, less the window offset once per 172-frame window."""
    return i * BP_HOP / BP_SR - BP_WINDOW_OFFSET * (i // BP_ANNOT_N_FRAMES)


def bp_frame_at(t):
    """(Pure.) The frame whose time is nearest `t` seconds (Basic Pitch's note times are frame times; the records
    round them to 0.1 ms)."""
    i0 = max(0, int(t * BP_SR / BP_HOP) - 2)
    i = i0
    while bp_frame_time(i + 1) <= t:
        i += 1
    return i if abs(bp_frame_time(i) - t) <= abs(bp_frame_time(i + 1) - t) else i + 1


def clipped_trim(n, shift_s):
    """(Pure.) How many leading bend frames of one re-based event lie before the input's own 0. Only a note the runner
    actually clipped (a padded read, `shift_s` > 0, and its onset at exactly 0) is touched. Its bend track is
    contours[start:end] on the padded read (one value a frame); the end frame is found from its note-off through Basic
    Pitch's own time map, the start frame is the end less the track's length, and the frames whose time falls before
    the pad are dropped."""
    b = n.get("bends") or []
    if shift_s <= 0 or n["on"] != 0.0 or not b:
        return 0
    end = bp_frame_at(n["off"] + shift_s)
    start = end - len(b)
    return sum(1 for i in range(start, end) if bp_frame_time(i) < shift_s)


def runner_notes(events, shift_s):
    """(Pure.) A Basic Pitch runner record's events as notes (`note_transcribe.notes_from_events`) with a clipped
    note's bends trimmed to its onset (#617: the runner clips an onset below 0 to 0 and keeps the bend track as read).
    shift_s: the pad the runner re-based by, in seconds asked (`lead_in_s`, plus the shift's `offset_s`; the whole-
    sample pad is within half a sample of it). An unpadded read is returned unchanged."""
    out = []
    for n in NT.notes_from_events(events):
        k = clipped_trim(n, shift_s)
        out.append(dict(n, bends=n["bends"][k:]) if k else n)
    return out


def record_notes(rec):
    """(Pure.) Every read of a Basic Pitch runner record as notes, each re-based read trimmed by its own pad:
    {"events": ..., "grid": [...]} for bp-grid (the lead-in), {"events": ..., "shifts": [...]} for bp-shift (the
    lead-in plus each offset)."""
    lead = float(rec["spec"].get("lead_in_s") or 0.0)
    if rec["mode"] == "bp-grid":
        return {"events": runner_notes(rec["events"], lead),
                "grid": [{"settings": g["settings"], "notes": runner_notes(g["events"], lead)} for g in rec["grid"]]}
    if rec["mode"] == "bp-shift":
        shifts = [{"offset_s": s["offset_s"], "notes": runner_notes(s["events"], lead + s["offset_s"])}
                  for s in rec["shifts"]]
        zero = next((s["notes"] for s in shifts if s["offset_s"] == 0), [])
        return {"events": zero, "shifts": shifts}
    raise SystemExit(f"{rec['mode']}: not a Basic Pitch record (no bend tracks to trim)")


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
    beside = dict(dry_beside(guitars), note_error_nominal=None if nom["f"] is None else 1 - nom["f"])
    return {"nominal": nom, "played": pla, "figures": figs, "beside": beside,
            "partition_holds": partition_holds(nom) and partition_holds(pla)}


def pooled_counts(ans):
    """(Pure.) Class counts summed over windows."""
    out = {"truth": 0, "est": 0, "matched": 0, "extras": {c: 0 for c in EXTRA_CLASSES},
           "extras_sorted": {c: 0 for c in EXTRAS_SORTED}, "misses": {c: 0 for c in MISS_ORDER}}
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
    `real_di_source`: P3 never) and the ten lists (the install gate's stored events against the known notes). The
    truth report's stored counts (matched, ref, est) must reproduce on every window (79 of 79), else nothing is
    written; track 1's stored `tx-bp` extras are compared per window as a named report (`track1_tx_bp_extras`), never
    a refusal. Each window carries its file as its cluster (the real-DI arm's interval). -> real-compare.json."""
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
        rows.append({"group": w["player"], "kind": w["kind"], "key": w["key"],
                     "cluster": f"{win['player']}|{win['kind']}|{win['name']}", "anatomy": an,
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
        rows.append({"group": "lists", "kind": None, "key": nm, "cluster": nm, "anatomy": an,
                     "figures": note_figures(an, truth, est, L), "partition_holds": partition_holds(an)})
    if repro != len(report["windows"]):
        raise SystemExit(f"the truth report's counts reproduce on {repro} of {len(report['windows'])} windows: "
                         "nothing written; to the orchestrator")
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
           "track1_tx_bp_extras": {"report": "track 1's stored tx-bp extras against this anatomy's three, per "
                                             "window; a report, never a refusal", "equal": tx_same,
                                   "windows": len(report["windows"])}, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
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


# --- Phase 2 (`phase_scratch_readerr_p2`): the shift vote (pure) ----------------------------------------------------------

PHASE_P2 = "phase_scratch_readerr_p2"    # the Phase 2 amendment (units A and B) with its review's six amendments
PHASE_XR_DRY = "phase_scratch_readerr_xr_dry"          # xr-build's build file: before any xr- search
PHASE_XR_OUTCOME = "phase_scratch_readerr_xr_outcome"  # the XH code, after an audit
SHIFT_FRAMES = (0, 35, 71, 106)          # 0, 1/4, 1/2, 3/4 of Basic Pitch's 36,164-sample window hop, in frames
SHIFT_OFFSETS_S = tuple(f * BP_HOP / BP_SR for f in SHIFT_FRAMES)   # 0, 0.4063, 0.8243, 1.2306 s
SHIFT_KS = (2, 3, 4)


def shift_vote(anchor, shifted, k):
    """(Pure.) The shift vote (amendment section 2): an anchor note's votes are 1 plus the shifted reads holding a
    note paired with it (`pair_by`: same pitch, onsets within 50 ms, one to one, closest first); kept with votes at or
    above k, exactly as the anchor read it. It only removes notes. anchor: the zero-offset read (the stored re-read);
    shifted: the other reads, each re-based (`record_notes`). -> (kept notes, votes per anchor note)."""
    votes = [1] * len(anchor)
    for read in shifted:
        for i, _ in pair_by(anchor, read):
            votes[i] += 1
    return [dict(n) for n, v in zip(anchor, votes) if v >= k], votes


def shift_unanchored(anchor, shifted):
    """(Pure.) Beside, never a candidate: the notes every shifted read finds that pair with no anchor note (the first
    shifted read's, chained through each other shifted read's unpaired notes by `pair_by`)."""
    if not shifted:
        return []
    free = []
    for read in shifted:
        taken = {j for _, j in pair_by(anchor, read)}
        free.append([n for j, n in enumerate(read) if j not in taken])
    out = list(free[0])
    for other in free[1:]:
        out = [out[i] for i, _ in pair_by(out, other)]
    return out


# --- Phase 2: the hybrid note lists (pure) -----------------------------------------------------------------------------

XR_ROWS = ("xr-matched", "xr-found", "xr-filled")
XR_SHORT = {"xr-matched": "matched", "xr-found": "found", "xr-filled": "filled"}
XR_BESIDE = ("hand-plain",)             # built and reported, never searched
XR_SETS = {"first": ("xr-matched", "hand-plain"), "found": ("xr-found",), "filled": ("xr-filled",)}
XR_SET_ASKED = {"found": "XH-rest", "filled": "XH-undecided"}   # each later list only when the code asks for it
JOIN_REPORT_EXTRAS = ("timing", "octave-sub", "semitone-sub")
JOIN_REPORT_MISSES = ("timing", "substitution")


def chain_root(j, target, kept):
    """(Pure.) A re-find's chain root: follow `refind_pairs`' targets from j while the note is an unpaired re-find,
    stopping at a kept note or where the chain ends. -> the root index."""
    seen = set()
    while j in target and j not in kept and j not in seen:
        seen.add(j)
        j = target[j]
    return j


def xr_matched(reread, exact):
    """(Pure.) `xr-matched` (review amendment 4): the re-read notes that pair with an exact note
    (`note_versions.hand_pairs`), each unpaired re-find whose chain root is a kept note first handing its end to that
    note (`note_fixes.refind_pairs`, `join_refinds`, which follows roots); every other unpaired note leaves. A note is
    joined when it is unpaired and its chain root is kept. -> (notes, {kept, joined, removed, joins, extended})."""
    pairs = NV.hand_pairs(reread, exact)
    kept = {j for _, j in pairs}
    rp = NF.refind_pairs(reread)
    target = {j: i for i, j in rp}
    joins = {j for j in target if j not in kept and chain_root(j, target, kept) in kept}
    tagged = [dict(n, _k=k) for k, n in enumerate(reread)]
    joined = NF.join_refinds(tagged, rp, joins)
    out = [n for n in joined if n["_k"] in kept]
    extended = [n["_k"] for n in out if n["off"] != reread[n["_k"]]["off"]]
    ends = {n["_k"]: n["off"] for n in out}              # each kept note's end after the joins, by its re-read index
    for n in out:
        del n["_k"]
    return out, {"kept": len(kept), "joined": len(joins), "removed": len(reread) - len(kept) - len(joins),
                 "joins": sorted(joins), "extended": sorted(extended), "ends": ends, "pairs": pairs}


def xr_found(reread, exact):
    """(Pure.) `xr-found`: the exact notes the re-read found, as exact."""
    found = {i for i, _ in NV.hand_pairs(reread, exact)}
    return [dict(t) for i, t in enumerate(exact) if i in found]


def xr_filled(reread, exact):
    """(Pure.) `xr-filled`: the whole exact list plus the re-read's unpaired notes, not joined, in onset order."""
    paired = {j for _, j in NV.hand_pairs(reread, exact)}
    extra = [dict(e) for j, e in enumerate(reread) if j not in paired]
    return sorted([dict(t) for t in exact] + extra, key=lambda n: (n["on"], n["pitch"]))


def xr_lists(reread, exact):
    """(Pure.) Every hybrid's notes and the join report. hand-plain is `note_versions.hand_notes` (the plain drop)."""
    m, rep = xr_matched(reread, exact)
    return {"xr-matched": m, "xr-found": xr_found(reread, exact), "xr-filled": xr_filled(reread, exact),
            "hand-plain": NV.hand_notes(reread, exact)}, rep


def join_report(rep, reread, exact, est_classes, truth_classes):
    """(Pure.) Beside the build (review amendment 4): the joins; how many of them the nominal anatomy calls re-finds;
    the joined ends that run past the exact partner's end; and the true notes dropped with timing or substitution
    extras (the extras of those classes left out, the misses of those classes). Each joined end is read from
    `xr_matched`'s report by the kept note's own re-read index (`_k`), never by list order."""
    partner = {j: i for i, j in rep["pairs"]}
    past = sum(1 for j in rep["extended"] if rep["ends"][j] > exact[partner[j]]["off"])
    return {"joins": rep["joined"], "joins_anatomy_refind": sum(est_classes[j] == "re-find" for j in rep["joins"]),
            "joined_ends_past_partner": past,
            "extras_left_out": {c: sum(1 for j, x in enumerate(est_classes) if x == c and j not in rep["joins"])
                                for c in JOIN_REPORT_EXTRAS},
            "misses": {c: truth_classes.count(c) for c in JOIN_REPORT_MISSES}}


# --- Phase 2: the read's labels, XH_TABLE, the next figure (pure) ---------------------------------------------------------

XH_TABLE = (    # (code, when (the first that holds), meaning, next)
    ("XH-stop", "a build proof or xr-check fails, a zero distance on a deciding setting, or a label is missing",
     "nothing is read", "to the orchestrator"),
    ("XH-anomaly", "E reads 'worse', or M reads 'better'",
     "the preset lands decidedly further without the extras, or an oracle list beats the exact list",
     "audited before anything is said; Phase 2b waits"),
    ("XH-both", "E passes and M reads 'worse'", "the extras and the rest both cost; the share sits beside",
     "Phase 2 scores by note error; Phase 2b runs; to the user"),
    ("XH-extras", "E passes, M not 'worse'", "{extras_words}",
     "Phase 2 scores by extra_rate with miss_rate not decided worse (sign only, the cross-set rule); Phase 2b runs; "
     "to the user with the best no-download candidate from 2a's table by that rule as the next xr- row"),
    ("XH-rest", "M reads 'worse', E does not pass", "the shown cost sits in misses and matched notes; E {e_words}",
     "no figure frozen now; Phase 2b runs; to the user with xr-found as the next row, which separates the misses "
     "(xr-found - xn-list) from matched-note error (xr-matched - xr-found); the figure is chosen after it"),
    ("XH-undecided", "anything else", "the split is not decided; undecided is not failed",
     "Phase 2a stays descriptive; Phase 2b does not run on this; to the user with xr-filled or parking the track "
     "behind the rebuild bench"),
)
XH_CODES = tuple(c for c, *_ in XH_TABLE)
XH_NEXT_FIGURE = {
    "XH-both": {"figure": "note_error", "rule": "note error decides Phase 2's candidates"},
    "XH-extras": {"figure": "extra_rate", "guard": "miss_rate",
                  "rule": "the best no-download candidate by extra_rate, with miss_rate not decided worse (sign only), "
                          "under the cross-set rule (picked on BKS read on GOAT, and the reverse)"},
    "XH-rest": {"figure": None, "rule": "none frozen now (miss_rate's Phase 1 halves were degenerate, and M bundles "
                                        "misses with matched-note error): chosen after xr-found"},
}
XH_FIDELITY = {"figure": "note_error", "rule": FIDELITY_ONLY}


def xh_table_guard():
    """Refuse unless XH_TABLE holds the six declared codes in order, and the next figures name declared figures."""
    if XH_CODES != ("XH-stop", "XH-anomaly", "XH-both", "XH-extras", "XH-rest", "XH-undecided"):
        raise SystemExit("XH_TABLE's codes are not the six declared, in order")
    for v in XH_NEXT_FIGURE.values():
        if v["figure"] is not None and v["figure"] not in FIGURES:
            raise SystemExit(f"{v['figure']}: not a declared figure")


def xh_labels(e_iv, m_iv):
    """(Pure.) The read's labels, all at their defaults (on J0's scale): E by `number_reading` (a gain) and
    `paired_reading`; M by `paired_reading`."""
    return {"E_number": S.number_reading(e_iv), "E": (SN.paired_reading(e_iv) or {}).get("reading"),
            "M": (SN.paired_reading(m_iv) or {}).get("reading")}


def xh_code(labels, stop=False):
    """(Pure.) XH_TABLE's code, the first that holds. labels: `xh_labels`'s. -> {code, when, meaning, next, figure}."""
    en, e, mm = labels.get("E_number"), labels.get("E"), labels.get("M")
    if stop or en is None or e is None or mm is None:
        code = "XH-stop"
    elif e == "worse" or mm == "better":
        code = "XH-anomaly"
    elif en == "passes" and mm == "worse":
        code = "XH-both"
    elif en == "passes":
        code = "XH-extras"
    elif mm == "worse":
        code = "XH-rest"
    else:
        code = "XH-undecided"
    row = next(r for r in XH_TABLE if r[0] == code)
    words = row[2].format(
        extras_words=("the extras carry reading proper" if mm == "matches" else
                      "the extras cost; the rest not decided"),
        e_words="fails" if en == "fails" else "undecided")
    return {"code": code, "when": row[1], "meaning": words, "next": row[3],
            "figure": XH_NEXT_FIGURE.get(code, XH_FIDELITY)}


def xh_read(itt, passing):
    """(Pure.) S1 for E and M alike (review amendment 1): intent-to-treat decides, passing-only beside, and
    "refusal-sensitive" when the codes differ. itt, passing: {"E": interval, "M": interval}; passing may be None."""
    code = xh_code(xh_labels(itt.get("E"), itt.get("M")))
    pc = None
    if passing is not None:
        ok = passing.get("E") is not None and passing.get("M") is not None
        pc = S.passing_code(lambda: xh_code(xh_labels(passing["E"], passing["M"])), ok)
    return {"itt": code, "passing_only": pc, "label": S.refusal_label(code["code"], (pc or {}).get("code"))}


def leave_one_cluster_out(values, cluster_of, interval_of):
    """(Pure but for `interval_of`.) Beside: the pooled interval with each cluster left out in turn.
    -> {cluster: interval}."""
    out = {}
    for c in sorted({cluster_of[k] for k in values if k in cluster_of}):
        out[c] = interval_of({k: v for k, v in values.items() if cluster_of.get(k) != c})
    return out


def forward_test(e, dry, sets_of, deciding=DECIDING):
    """(Pure.) The forward test, beside: per part the change in a dry figure (the xr-matched guitar less xn-reread's,
    each against the bank guitar) against E; Spearman and sign agreement pooled on the 40 (BKS+GOAT), as every other
    read, with each set's Spearman and all 47 beside. No median split. dry: {pkey: change}."""
    ks = [k for k in e if dry.get(k) is not None and e[k] is not None]

    def read(sub):
        return {"parts": len(sub), "spearman": SN.spearman([(dry[k], e[k]) for k in sub]),
                "sign_agreement": sign_agreement({k: e[k] for k in sub}, {k: dry[k] for k in sub})}
    out = dict(read([k for k in ks if sets_of[k] in deciding]), all_47=read(ks))
    for s in sorted({sets_of[k] for k in ks}):
        out[s] = SN.spearman([(dry[k], e[k]) for k in ks if sets_of[k] == s])
    return out


# --- Phase 2: paths, the widened write rule, the search's forbidden list ----------------------------------------------------

XR_SEARCH_FORBIDDEN = ("targets.json", "trace.json", "anatomy.json")
XR_SEARCH_FORBIDDEN_DIRS = ("target", "score", "score-rerun")


def xr_dir():
    return readerr_dir() / "xr"


def xr_path(kind, row=None, pk=None):
    """Every xr- path: under PF/fs/readerr/xr/, by kind. -> path (refused outside readerr)."""
    if kind == "build":
        p = xr_dir() / f"build-{row}.json"
    elif kind == "check":
        p = xr_dir() / "check" / "result.json"
    elif kind in ("dry", "search", "start-ref", "score", "check-search", "check-score", "check-start-ref"):
        if pk is None:
            raise ValueError("a part's path needs its key")
        ext = ".npy" if kind == "dry" else ".json"
        p = xr_dir() / kind / (row or "check") / f"{pk.replace('/', '__')}{ext}"
    elif kind == "answers":
        if row not in XR_ROWS:
            raise ValueError(row)
        p = xr_dir() / f"answers-{row}.json"
    elif kind in ("rows", "report"):
        p = xr_dir() / f"{kind}.json"
    else:
        raise ValueError(kind)
    root = pathlib.Path(readerr_dir()).resolve()
    if root not in pathlib.Path(p).resolve().parents:
        raise SystemExit(f"{p}: outside {root}")
    return p


def fresh_xr_path(kind, row=None, pk=None):
    """An xr- path that must not exist yet: the only kind handed to a writer outside this module
    (`scratch_search.search_row_part` writes through `P.save`)."""
    p = xr_path(kind, row, pk)
    if pathlib.Path(p).exists():
        raise SystemExit(f"{p} exists: never overwritten")
    return p


def write_once_npy(path, x32):
    """The guitars' write: under PF/fs/readerr/, never over a file. -> its file's sha256."""
    import numpy as np

    path = pathlib.Path(path)
    root = pathlib.Path(readerr_dir()).resolve()
    if root not in path.resolve().parents:
        raise SystemExit(f"{path}: outside {root}: this track writes only there")
    if path.exists():
        raise SystemExit(f"{path} exists: never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, x32)
    return file_sha(path)


def xr_is_forbidden(path):
    """(Pure.) Whether the xr- search may not open `path`: targets.json, a target or score file, any answers file,
    trace.json or anatomy.json."""
    path = pathlib.PurePath(path)
    return (path.name in XR_SEARCH_FORBIDDEN or path.name.startswith("answers")
            or any(part in XR_SEARCH_FORBIDDEN_DIRS for part in path.parent.parts[-2:]))


def xr_search_open(path):
    if xr_is_forbidden(path):
        raise SystemExit(f"{pathlib.PurePath(path).name}: the xr- search never opens it")
    return pathlib.Path(path)


def xr_answers_key(row):
    if row not in XR_ROWS:
        raise SystemExit(f"unknown row {row!r}: one of {list(XR_ROWS)}")
    return f"{KEY_PREFIX}_xr_answers_{XR_SHORT[row]}"


def xr_dry_key(set_name):
    if set_name not in XR_SETS:
        raise SystemExit(f"unknown build set {set_name!r}")
    return PHASE_XR_DRY if set_name == "first" else f"{PHASE_XR_DRY}_{set_name}"


def set_of_row(row):
    return next(s for s, rows in XR_SETS.items() if row in rows)


def require_xr_build(m, set_name, hashed=True):
    """xr-build's file for a set: its proofs held; with `hashed`, its sha256 main's xr_dry key's."""
    p = xr_search_open(xr_path("build", set_name))
    if not p.exists():
        raise SystemExit(f"no {p.name} (run `xr-build` first)")
    if hashed:
        why = SX.field_refusal(m, xr_dry_key(set_name), "sha256", file_sha(p))
        if why:
            raise SystemExit(why)
    b = json.loads(p.read_text())
    if not b.get("proofs_hold"):
        raise SystemExit(f"{p.name}'s proofs did not hold: XH-stop")
    return b


def require_xr_check():
    p = xr_search_open(xr_path("check"))
    if not p.exists():
        raise SystemExit("xr-check has not run")
    r = json.loads(p.read_text())
    if not r.get("passed"):
        raise SystemExit(f"xr-check did not pass: XH-stop ({r.get('mismatches')})")
    return r


def load_xr_guitar(row, pk, build):
    """A row's dry guitar for a part, float32, refused unless its sha256 is xr-build's. -> (x32, sha256)."""
    import numpy as np

    x32 = np.load(xr_search_open(xr_path("dry", row, pk))).astype(np.float32)
    sha = build["parts"][pk]["guitars"][row]["sha256"]
    if S.npy_sha(x32) != build["parts"][pk]["guitars"][row]["audio_sha256"]:
        raise SystemExit(f"{pk}: {row}'s dry guitar is not the declared one")
    return x32, sha


def read_xr_parts(draw, ans, answers_sha, row):
    """A row's per-part numbers from its xr- score files, step for step `scratch_exact.read_xn_parts` (which only
    knows the four xn- rows): a scoring-control miss read from its rerun (one not yet rerun waits), then a refusal;
    `deciding_bug` stops the read; `nonfinite_rule`; `xn_numbers`. -> (per, refused, replaced, misses)."""
    refused = dict(ans["refused"])
    per, replaced, ctl = {}, {}, []
    for p in draw["parts"]:
        k = p["pkey"]
        if k not in ans["parts"]:
            per[k] = None
            continue
        sp = xr_path("score", row, k)
        if not sp.exists():
            raise SystemExit(f"{row} {k}: not scored")
        sc = json.loads(sp.read_text())
        if not sc["scoring_control_ok"]:
            if not S.rerun_path(sp).exists():
                raise SystemExit(f"{row} {k}: a scoring-control miss not yet rerun: `xr-score --rerun` first")
            again = json.loads(S.rerun_path(sp).read_text())
            if again["scoring_control_ok"]:
                sc = again
        if sc["answers_sha256"] != answers_sha:
            raise SystemExit(f"{row} {k}: scored from other answers")
        if not sc["scoring_control_ok"]:
            refused[k] = {"scoring_control": {"cen": sc["held"]["cen"], "stored": sc["cen_stored"]}}
            ctl.append(k)
            per[k] = None
            continue
        bug = SX.deciding_bug(sc["held"])
        if bug:
            raise SystemExit(f"{row} {k}: {bug} — a zero or non-finite distance on a deciding setting is a bug: "
                             "XH-stop, the read stops, to the orchestrator")
        held, rep = S.nonfinite_rule(sc["held"])
        if rep:
            replaced[k] = rep
        per[k] = SX.xn_numbers(held)
    return per, refused, replaced, ctl


def xr_row_numbers(m, draw, row):
    ans = NT.require_file_hash(m, xr_answers_key(row), xr_path("answers", row))
    sha = file_sha(xr_path("answers", row))
    per, refused, replaced, ctl = read_xr_parts(draw, ans, sha, row)
    return {"per": per, "itt": S.itt_per(per, refused, SX.FIELDS), "refused": refused, "replaced": replaced,
            "control_misses": ctl, "coverage": ans.get("coverage"), "answers_sha256": sha}


# --- Phase 2: xr-build (zero renders) -----------------------------------------------------------------------------------------

def pause_error_of(bank64, y):
    """The rebuilt guitar's pause error against the bank guitar: 1 - agree of the playing-frame masks
    (`note_rebuild.mask_agreement`), the mean over J0's frame sizes, as Phase 1's stored figure."""
    mask = NR.mask_agreement(bank64, y)
    return sum(1 - v["agree"] for v in mask.values()) / len(mask)


def cmd_xr_build(args):
    """xr-build (zero renders), once a set: per part, from trace.json's re-read (after timing and F1) and nominal exact
    list, the set's hybrids (`xr_lists`), each rebuilt as `cmd_trace` rebuilds (`rebuild_redo("tr-di", ...)`, the
    part's finish, loud None). Four proofs before anything is written: (1) the full re-read reproduces
    dry/xn-reread's sha256 and (2) the exact list dry/xn-list's on 47 of 47, (3) the pairing's counts equal
    anatomy.json's nominal `matched` per part, (4) CODE_FILES equal main's. The first set is xr-matched and
    hand-plain (four rebuilds a part); xr-found and xr-filled only when main's XH code asks. -> xr/dry/<row>/,
    xr/build-<set>.json; its sha256 into the ledger as phase_scratch_readerr_xr_dry(_<set>) before any search."""
    set_name = getattr(args, "set", None) or "first"
    if set_name not in XR_SETS:
        raise SystemExit(f"unknown build set {set_name!r}")
    m = require_readerr(PHASE_FROZEN, PHASE_P2)
    if set_name != "first":
        got = ((m.get(PHASE_XR_OUTCOME) or {}).get("code"))
        if got != XR_SET_ASKED[set_name]:
            raise SystemExit(f"{set_name} is built only when main's {PHASE_XR_OUTCOME} reads {XR_SET_ASKED[set_name]}")
    tr = require_trace(m)
    an = require_out("anatomy", m)
    out_p = xr_path("build", set_name)
    NT.never_overwrite(out_p)
    import numpy as np

    from analysis import aligned as A

    from learn import knob_ceiling as K

    xb = SX.require_xbuild(m)
    b2 = SX.bank_build(m)
    draw, _sd = SX.context()
    by = {p["pkey"]: p for p in draw["parts"]}
    t0 = time.time()
    pinned = pinned_identity()
    pair = NT.install_pair(NT.load_manifest())
    excl, _, _, _ = NT._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    finish_of = {key: fin for kind, key, _i, _r, _d, fin in NT.build_todo(pair, NT.ear_items_file(BUILD2))
                 if kind == "part"}
    ring = tr["ring_variant"]
    lo, hi = SX._trim()
    rows = XR_SETS[set_name]
    built, bad = {}, {1: [], 2: [], 3: []}
    for j, (key, r) in enumerate(sorted(tr["parts"].items())):
        bank64 = np.asarray(NT.load_dry(BANK_ARM, key, b2), np.float64)

        def rebuild(notes):
            y, rep = NR.rebuild_redo(BANK_ARM, notes, len(bank64), bank, bank64, ring, finish=finish_of[key],
                                     loud=None)
            return np.asarray(y, np.float32), rep
        g = xb["parts"][key]["guitars"]
        if npy_bytes_sha(rebuild(r["reread"])[0]) != g["xn-reread"]["sha256"]:
            bad[1].append(key)
        if npy_bytes_sha(rebuild(r["nominal"])[0]) != g["xn-list"]["sha256"]:
            bad[2].append(key)
        lists, jrep = xr_lists(r["reread"], r["nominal"])
        if len(jrep["pairs"]) != an["parts"][key]["nominal"]["matched"]:
            bad[3].append(key)
        nom = an["parts"][key]["nominal"]
        part = {"guitars": {}, "counts": {k: jrep[k] for k in ("kept", "joined", "removed")},
                "join_report": join_report(jrep, r["reread"], r["nominal"], nom["est_classes"], nom["truth_classes"]),
                "notes": {row: len(lists[row]) for row in rows}}
        for row in rows:
            y32, rep = rebuild(lists[row])
            if len(y32) != len(bank64) or not np.isfinite(y32).all():
                raise SystemExit(f"part {j + 1}: a bad {row} dry guitar: nothing written")
            y = np.asarray(y32, np.float64)
            pauses = {h: {str(n): float(NT.judge_pause_share(y[lo:hi], 0, h, n)) for n in A.FRAME_SIZES}
                      for h in K.R.HALVES}
            figs = NR.figures(bank64, y)
            part["guitars"][row] = {
                "y32": y32, "sha256": npy_bytes_sha(y32), "audio_sha256": S.npy_sha(y32), "report": rep,
                "figures": figs, "pause_error": pause_error_of(bank64, y), "pauses": pauses,
                "bank_pauses": {h: {str(n): float(NT.judge_pause_share(bank64[lo:hi], 0, h, n))
                                    for n in A.FRAME_SIZES} for h in K.R.HALVES},
                "identical_to": next((xn for xn in ("xn-reread", "xn-list") if g[xn]["sha256"] == npy_bytes_sha(y32)),
                                     None)}
        built[key] = part
        print(f"part {j + 1} of {len(tr['parts'])}: proofs {'=' if key not in bad[1] else 'DIFFERS'} "
              f"{'=' if key not in bad[2] else 'DIFFERS'} {'=' if key not in bad[3] else 'DIFFERS'}", flush=True)
    n = len(tr["parts"])
    proofs = {"reread_equal": n - len(bad[1]), "list_equal": n - len(bad[2]), "pairs_equal": n - len(bad[3]),
              "pinned": pinned, "parts": n}
    hold = not any(bad.values()) and all(pinned.values())
    if not hold:
        raise SystemExit(f"XH-stop: a build proof fails ({ {k: len(v) for k, v in bad.items()} }, pinned "
                         f"{sum(pinned.values())} of {len(pinned)}): nothing written; to the orchestrator")
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2}", "renders": 0, "set": set_name, "rows": list(rows),
           "trace_sha256": file_sha(out_path("trace")), "anatomy_sha256": file_sha(out_path("anatomy")),
           "proofs": proofs, "proofs_hold": True, "parts": {}}
    refuse_risk = []
    for key, part in built.items():
        for row in rows:
            gg = part["guitars"][row]
            path = xr_path("dry", row, key)
            gg["file_sha256"] = write_once_npy(path, gg.pop("y32"))
            if gg["file_sha256"] != gg["sha256"]:
                raise SystemExit(f"{row}: the written guitar is not the one built")
            if max(gg["pauses"][by[key]["search"]].values()) > 0.5:
                refuse_risk.append((row, key))
        out["parts"][key] = part
    out["refusal_risk"] = {"report": "parts whose search-half pause share would make J0 refuse; a report, not a stop",
                           "parts": [{"row": r_, "part": k_} for r_, k_ in refuse_risk]}
    out["pooled"] = {"counts": {c: sum(p["counts"][c] for p in built.values()) for c in ("kept", "joined", "removed")},
                     "join_report": {c: sum(p["join_report"][c] for p in built.values())
                                     for c in ("joins", "joins_anatomy_refind", "joined_ends_past_partner")}}
    out["seconds"] = round(time.time() - t0, 1)
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    sha = write_once(out_p, out)
    print(f"XH BUILD {set_name}: proofs (1) {proofs['reread_equal']}, (2) {proofs['list_equal']}, (3) "
          f"{proofs['pairs_equal']} of {n}, (4) pinned {sum(pinned.values())} of {len(pinned)}; pooled "
          f"{out['pooled']}; J0 refusal risk on {len(refuse_risk)}; {out['seconds']} s; sha256 {sha} (into the "
          f"ledger as {xr_dry_key(set_name)} before any search)")


# --- Phase 2: xr-check (renders, once) ---------------------------------------------------------------------------------------

def cmd_xr_check(_args):
    """xr-check (about 50 renders), once: on `scratch_notes.check_parts`' two parts with xn-reread's stored guitar,
    this module's start reference and `run_part(budget=10, step1_only=True)` must equal xn-reread's stored first 10
    evaluations (`search_check_verdict`), and this module's score of xn-reread's hashed answers must equal its stored
    score files (`score_check_verdict`). A mismatch is XH-stop. -> xr/check/."""
    m = require_readerr(PHASE_FROZEN, PHASE_P2, PHASE_XR_DRY, SX.answers_key("xn-reread"))
    res_p = xr_path("check")
    NT.never_overwrite(res_p)
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as R

    R.no_separation_beside()
    xb = SX.require_xbuild(m)
    records = SX.require_records(m)
    tg = SX.require_targets(m)
    ans = SX.require_answers(m, "xn-reread")
    b2 = SX.bank_build(m)
    draw, sd = SX.context()
    by = {p["pkey"]: p for p in draw["parts"]}
    lists = C.mic_lists()
    LO._wait_cap()
    new_s, old_s, new_c, old_c, total = {}, {}, {}, {}, 0
    for k in SN.check_parts(draw["parts"]):
        SX.disk_guard()
        p = by[k]
        x32, sha = SX.load_guitar("xn-reread", p, xb, b2, sd)
        ref_blank = SX.load_record_blank(p, records)
        px = SX.synthetic_part(p)
        sref, used = SX.start_reference("xn-reread", px, x32, ref_blank, CB.new_renderer,
                                        fresh_xr_path("check-start-ref", None, k), sha)
        rec = S.run_part(px, "xn-reread", SX.REF, x32, ref_blank, CB.new_renderer, lists, budget=SN.CHECK_BUDGET,
                         start_ref=sref, dry_sha256=sha, step1_only=True)
        total += rec.get("renders", 0) + used
        write_once(fresh_xr_path("check-search", None, k), rec)
        new_s[k], old_s[k] = rec, json.loads(SX.search_path("xn-reread", k).read_text())
        bank32 = NT.load_dry(BANK_ARM, k, b2)
        sc, used = SX.score_exact_part(px, ans["parts"][k], bank32, SX.load_record(k, records), 0,
                                       tg["parts"][k]["cen_held"], CB.new_renderer)
        total += used
        write_once(fresh_xr_path("check-score", None, k), sc)
        new_c[k], old_c[k] = sc, json.loads(SX.score_path("xn-reread", k).read_text())
    vs, vc = SN.search_check_verdict(new_s, old_s), SX.score_check_verdict(new_c, old_c)
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2}", "renders": total, "budget": SN.CHECK_BUDGET,
           "search": vs, "score": vc, "passed": vs["passed"] and vc["passed"],
           "mismatches": {"search": vs["mismatches"], "score": vc["mismatches"]},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    write_once(res_p, res)
    print(f"XH CHECK {'PASS' if res['passed'] else 'FAIL (XH-stop)'}: {total} renders; {res['mismatches']}")


# --- Phase 2: the row (renders but answers) ------------------------------------------------------------------------------------

def cmd_xr_search(args):
    """One shard of an xr- row's searches (renders), after the build's hash and a passing xr-check: per part the
    row's guitar (its sha256 xr-build's), the record blanked outside the search half, the start reference at lag 0,
    then `scratch_search.search_row_part` on the exact world's part, every path from `xr_path`. A guitar
    byte-identical to a stored xn- row's takes that row's search record byte for byte. The search opens none of
    XR_SEARCH_FORBIDDEN (no target, score or answers file, no trace.json or anatomy.json). The disk guard before
    every part."""
    row = args.row
    if row not in XR_ROWS:
        raise SystemExit(f"{row!r}: the searched rows are {list(XR_ROWS)}")
    set_name = set_of_row(row)
    m = require_readerr(PHASE_FROZEN, PHASE_P2, xr_dry_key(set_name))
    build = require_xr_build(m, set_name)
    require_xr_check()
    records = SX.require_records(m)
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as R

    R.no_separation_beside()
    draw, _sd = SX.context()
    todo = SX.mine(draw, args.shard)
    if getattr(args, "first", 0):
        todo = todo[:args.first]
    lists = C.mic_lists()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in todo:
        pk = p["pkey"]
        out = xr_path("search", row, pk)
        rerun = getattr(args, "rerun", False)
        if rerun:                                          # S1: a technical refusal, once more in a fresh process
            if not out.exists() or not S.refused_record(json.loads(out.read_text())):
                continue
            out = S.rerun_path(out)
        if out.exists():
            continue
        SX.disk_guard()
        same = build["parts"][pk]["guitars"][row].get("identical_to")
        if same:
            src = SX.search_path(same, pk)
            if rerun:
                src = S.rerun_path(src)
            if not src.exists():
                raise SystemExit(f"{pk}: {row}'s guitar is {same}'s, and {same}'s record is not there")
            write_bytes_once(out, src.read_bytes())
            print(f"{row}: a guitar identical to {same}: its record taken byte for byte", flush=True)
            continue
        x32, _sha = load_xr_guitar(row, pk, build)
        ref_blank = SX.load_record_blank(p, records)
        px = SX.synthetic_part(p)
        spath = xr_path("start-ref", row, pk)
        if rerun:
            spath = S.rerun_path(spath)
        dry_sha = build["parts"][pk]["guitars"][row]["audio_sha256"]
        sref, used = SX.start_reference(row, px, x32, ref_blank, CB.new_renderer, spath, dry_sha)
        rec = S.search_row_part(px, row, SX.REF, x32, ref_blank, CB.new_renderer, lists, fresh_xr_path_of(out),
                                f"{LEDGER_ID} {PHASE_P2}", start_ref=sref, dry_sha256=dry_sha)
        total += rec.get("renders", 0) + used
        if "refused" in rec:
            print(f"REFUSED {rec['refused']}", flush=True)
        print(f"{row} shard {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s "
              f"({total / max(1, time.time() - t0) * 3600:.0f} an hour)", flush=True)
    print(f"XH SEARCH DONE {row} {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


def fresh_xr_path_of(path):
    """A path already made by `xr_path` (or its rerun twin), checked again: under readerr, not there yet."""
    path = pathlib.Path(path)
    root = pathlib.Path(readerr_dir()).resolve()
    if root not in path.resolve().parents:
        raise SystemExit(f"{path}: outside {root}")
    if path.exists():
        raise SystemExit(f"{path} exists: never overwritten")
    return path


def write_bytes_once(path, data):
    """A stored record copied byte for byte: under PF/fs/readerr/, never over a file."""
    path = fresh_xr_path_of(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return file_sha(path)


def cmd_xr_answers(args):
    """An xr- row's answers (zero renders): every search record or its rerun (`with_reruns`), each dry guitar checked
    against xr-build (`dry_refusal`), `xn_answer_parts`, the refusals (S1) and T1's coverage. -> xr/answers-<row>.json;
    its sha256 into the ledger as phase_scratch_readerr_xr_answers_<row> before `xr-score`."""
    row = args.row
    if row not in XR_ROWS:
        raise SystemExit(f"{row!r}: one of {list(XR_ROWS)}")
    set_name = set_of_row(row)
    m = require_readerr(PHASE_FROZEN, PHASE_P2, xr_dry_key(set_name))
    build = require_xr_build(m, set_name)
    tg = SX.require_targets(m)
    path = xr_path("answers", row)
    NT.never_overwrite(path)
    draw, _sd = SX.context()
    for p in draw["parts"]:
        if not xr_path("search", row, p["pkey"]).exists():
            raise SystemExit(f"a part is not searched on {row}")
    recs, used, reruns = S.with_reruns([p["pkey"] for p in draw["parts"]], lambda k: xr_path("search", row, k))
    why = S.rerun_refusal(reruns)
    if why:
        raise SystemExit(why)
    want = {k: build["parts"][k]["guitars"][row]["audio_sha256"] for k in build["parts"]}
    why = SX.dry_refusal(recs, want)
    if why:
        raise SystemExit(why)
    parts, refused = SX.xn_answer_parts(draw, recs, lambda k: file_sha(used[k]))
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    cov = {k: SX.coverage([s["module"] + "/" + s["key"] for s in (recs[k].get("searched_dims") or [])],
                          tg["parts"][k]["changed"]) for k in parts}
    out = {"plan": PLAN, "row": row, "ref": SX.REF, "draw_sha256": S.file_sha(S.draw_path()),
           "build_sha256": file_sha(xr_path("build", set_name)), "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "renders": sum(r.get("renders", 0) for r in recs.values()), "refused": refused, "reruns": reruns,
           "refusal_report": S.refusal_report(refused, sets_of, DECIDING), "stopped": False,
           "coverage": {"covered": sum(c["covered"] for c in cov.values()), "parts": cov}, "parts": parts}
    sha = write_once(path, out)
    print(f"XH ANSWERS {row}: {len(parts)} parts, {len(refused)} refused (each reads at Cen); reruns {reruns}; "
          f"coverage {out['coverage']['covered']} of {len(cov)}; sha256 {sha} (into the ledger as "
          f"{xr_answers_key(row)} before `xr-score`)")


def cmd_xr_score(args):
    """One shard of an xr- row's score (renders): Cen and the five settings of the hashed answers through the bank
    guitar, each primed alone, judged on the held half against the record at lag 0 (`score_exact_part`); the scoring
    control against Cen's value from `targets`. -> xr/score/<row>/<part>.json."""
    row = args.row
    if row not in XR_ROWS:
        raise SystemExit(f"{row!r}: one of {list(XR_ROWS)}")
    m = require_readerr(PHASE_FROZEN, PHASE_P2, xr_answers_key(row))
    records = SX.require_records(m)
    tg = SX.require_targets(m)
    ans = NT.require_file_hash(m, xr_answers_key(row), xr_path("answers", row))
    asha = file_sha(xr_path("answers", row))
    b2 = SX.bank_build(m)
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as R

    R.no_separation_beside()
    draw, _sd = SX.context()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in SX.mine(draw, args.shard):
        pk = p["pkey"]
        out = xr_path("score", row, pk)
        a = ans["parts"].get(pk)
        if getattr(args, "rerun", False):                  # S1: a scoring-control miss, once more in a fresh process
            if a is None or not out.exists() or json.loads(out.read_text())["scoring_control_ok"]:
                continue
            out = S.rerun_path(out)
        if a is None or out.exists():
            continue
        SX.disk_guard()
        bank32 = NT.load_dry(BANK_ARM, pk, b2)
        rec, used = SX.score_exact_part(SX.synthetic_part(p), a, bank32, SX.load_record(pk, records), 0,
                                        tg["parts"][pk]["cen_held"], CB.new_renderer)
        rec.update(row=row, answers_sha256=asha)
        total += used
        write_once(fresh_xr_path_of(out), rec)
        print(f"{row}: scored {rec['distinct_renders']} settings; control "
              f"{'ok' if rec['scoring_control_ok'] else 'MISS'}; {total} renders, {time.time() - t0:.0f} s", flush=True)
    print(f"XH SCORE DONE {row} {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


# --- Phase 2: xr-read (zero renders, once) -------------------------------------------------------------------------------------

def _rows(sd, draw, vals, keys=None):
    r = SN.set_rows(sd, draw, {k: v for k, v in vals.items() if v is not None and math.isfinite(v)}, keys)
    bg = (r or {}).get("bks_goat") or {}
    return {"bks_goat": bg.get("all"), "clean": bg.get("clean"), "crunch": bg.get("crunch"),
            "bks": {q: ((r or {}).get("bks") or {}).get(q) for q in ("mean", "lo90", "hi90")},
            "goat": {q: ((r or {}).get("goat") or {}).get(q) for q in ("mean", "lo90", "hi90")},
            "pool_47": (r or {}).get("deciding_pool")}


def cmd_xr_read(_args):
    """xr-read (zero renders), once: per part on the answer arm (shrunk beside) E = G(xr-matched) - G(xn-reread) and
    M = G(xr-matched) - G(xn-list); reading proper M - E. S1 for both (review amendment 1): intent-to-treat decides,
    passing-only beside, refusal-sensitive when the codes differ. set_rows on BKS+GOAT decides; BKS alone, GOAT alone,
    clean, crunch, all 47, checkpoints 50, 100, 200 and leave-one-cluster-out beside. Beside, never deciding: the
    share -E / reading proper (`fieller_share`) and the forward test (the change in logmel and env_corr against E).
    The rows are saved before the code. -> xr/rows.json, xr/report.json."""
    row = "xr-matched"
    m = require_readerr(PHASE_FROZEN, PHASE_P2, PHASE_XR_DRY, xr_answers_key(row))
    xh_table_guard()
    for p_ in (xr_path("rows"), xr_path("report")):
        NT.never_overwrite(p_)
    check = require_xr_check()
    build = require_xr_build(m, "first")
    xb = SX.require_xbuild(m)
    draw, sd = SX.context()
    rn = {r: SX.row_numbers(m, draw, r) for r in ("xn-reread", "xn-list")}
    rn[row] = xr_row_numbers(m, draw, row)
    cluster_of = {p["pkey"]: p["cluster"] for p in draw["parts"] if p["set"] in DECIDING}
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    arms, beside = {}, {}
    for arm, f in SX.ARMS.items():
        d = {}
        for treat in ("itt", "per"):
            d[treat] = {"E": SX.paired(rn[row][treat], rn["xn-reread"][treat], f),
                        "M": SX.paired(rn[row][treat], rn["xn-list"][treat], f)}
        rows_ = {t: {n: _rows(sd, draw, v) for n, v in d[t].items()} for t in d}
        arms[arm] = {"rows": rows_, "read": xh_read({n: rows_["itt"][n]["bks_goat"] for n in ("E", "M")},
                                                    {n: rows_["per"][n]["bks_goat"] for n in ("E", "M")})}
        if arm == "answer":
            e, mm = d["itt"]["E"], d["itt"]["M"]
            rp = {k: mm[k] - e[k] for k in e if k in mm}
            beside["share_minus_E_of_reading_proper"] = SX.share(sd, draw, {k: -v for k, v in e.items()}, rp)
            beside["checkpoints"] = {cp: {n: _rows(sd, draw, SX.paired(rn[row]["itt"], rn[o]["itt"], cp))["bks_goat"]
                                          for n, o in (("E", "xn-reread"), ("M", "xn-list"))}
                                     for cp in ("G_cp50", "G_cp100", "G_cp200")}
            beside["leave_one_cluster_out"] = {
                n: leave_one_cluster_out({k: v for k, v in vals.items() if k in cluster_of}, cluster_of,
                                         lambda vs: _rows(sd, draw, vs)["bks_goat"])
                for n, vals in (("E", e), ("M", mm))}
            fwd = {}
            for fig in ("logmel", "env_corr"):
                ch = {k: build["parts"][k]["guitars"][row]["figures"][fig] - xb["parts"][k]["guitars"]["xn-reread"][
                    "figures"][fig] for k in build["parts"]}
                fwd[fig] = forward_test(e, ch, sets_of)
            beside["forward_test"] = dict(fwd, note="a dry figure becomes Phase 2's scoring figure only by a further "
                                                    "amendment")
    out = {"plan": PLAN, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0, "row": row,
           "answers_sha256": {r: rn[r]["answers_sha256"] for r in rn}, "check_renders": check.get("renders"),
           "refusals": {r: {"refused": len(rn[r]["refused"]), "control_misses": len(rn[r]["control_misses"])}
                        for r in rn}}
    write_once(xr_path("rows"), dict(out, arms=arms, beside=beside))     # the rows before the code
    main_read = arms["answer"]["read"]
    code = main_read["itt"]
    write_once(xr_path("report"), dict(out, arms=arms, beside=beside, xh=main_read, code=code["code"],
                                       shrunk=arms["shrunk"]["read"]["itt"]["code"],
                                       next=("to the user with both reads" if main_read["label"] else code["next"])))
    r_ = arms["answer"]["rows"]["itt"]
    print(f"E on the 40 {r_['E']['bks_goat']}; M {r_['M']['bks_goat']}")
    print(f"XH {code['code']}: {code['meaning']}. Next: {code['next']}; label {main_read['label']}")


# --- Phase 2a's commands (unit C; not built here) ---------------------------------------------------------------------------

PHASE2_STUB = ("Phase 2a's `notes` and `score` come with unit C (the same two files), after this declaration merges; "
               "the RX read waits for the xr- row's code")


def cmd_score(_args):
    require_readerr(PHASE_FROZEN)
    raise SystemExit(PHASE2_STUB)


def cmd_read(_args):
    require_readerr(PHASE_FROZEN)
    raise SystemExit(PHASE2_STUB)


COMMANDS = {"trace": cmd_trace, "anatomy": cmd_anatomy, "real-compare": cmd_real_compare,
            "screen-check": cmd_screen_check, "freeze": cmd_freeze, "score": cmd_score, "read": cmd_read,
            "xr-build": cmd_xr_build, "xr-check": cmd_xr_check, "xr-search": cmd_xr_search,
            "xr-answers": cmd_xr_answers, "xr-score": cmd_xr_score, "xr-read": cmd_xr_read}
NEEDS_ROW = ("xr-search", "xr-answers", "xr-score")


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--row", choices=XR_ROWS)
    ap.add_argument("--set", choices=sorted(XR_SETS), default="first", help="xr-build's set")
    ap.add_argument("--shard", type=S._shard, default=(0, 1))
    ap.add_argument("--first", type=int, default=0, help="search only this shard's first n parts")
    ap.add_argument("--rerun", action="store_true",
                    help="search or score again, once, only the parts whose record refused (S1: then Cen)")
    args = ap.parse_args(argv)
    if args.cmd in NEEDS_ROW and not args.row:
        ap.error(f"{args.cmd} needs --row")
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
