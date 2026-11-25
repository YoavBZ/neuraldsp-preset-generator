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
    $MAIN -m learn.scratch_readerr notes --shard k/n [--first 3]   # Phase 2a: Basic Pitch's three reads an input
    $MAIN -m learn.scratch_readerr notes --combine  # once: the bench proof on 47 of 47, notes.json
    # the hash PR: phase_scratch_readerr_notes, before `score`
    $MAIN -m learn.scratch_readerr score --shard k/n [--first 3]   # Phase 2a: the 149 candidates' figures
    $MAIN -m learn.scratch_readerr score --combine  # once: the stored point on 47 of 47, candidates.json
    $MAIN -m learn.scratch_readerr read            # the RX read: after the xr- row (refuses)

The Phase 2 amendment's `xr-` row (`phase_scratch_readerr_p2`; plan section 9):

    $MAIN -m learn.scratch_readerr xr-build [--set first]   # zero renders: xr-matched, hand-plain; four proofs
    # the hash PR: phase_scratch_readerr_xr_dry, before any search
    $MAIN -m learn.scratch_readerr xr-check                 # about 50 renders: xn-reread's search and score again
    $MAIN -m learn.scratch_readerr xr-search --row xr-matched --shard 0/3 [--rerun]
    $MAIN -m learn.scratch_readerr xr-answers --row xr-matched   # -> phase_scratch_readerr_xr_answers_matched
    $MAIN -m learn.scratch_readerr xr-score --row xr-matched --shard 0/3 [--rerun]
    $MAIN -m learn.scratch_readerr xr-read                  # zero renders, once: E, M, XH_TABLE's code

The Phase 2b amendment (`phase_scratch_readerr_p2b`; unit E here, unit F's `learn/readerr_tools.py` installs and
fetches, unit D's `learn/readerr_run.py` runs the torch modes):

    $MAIN -m learn.scratch_readerr tx-gate                  # once: checkpoints, repeat, timing -> tools-gate.json
    # the hash PR: phase_scratch_readerr_tools
    $MAIN -m learn.scratch_readerr tx-notes --shard k/n [--first 3]; tx-notes --combine   # -> notes-tx.json
    # the hash PR: phase_scratch_readerr_notes_tx
    $MAIN -m learn.scratch_readerr tx-score --shard k/n [--first 3]; tx-score --combine   # -> candidates-tx.json
    # the hash PR: phase_scratch_readerr_candidates_tx
    $MAIN -m learn.scratch_readerr select                   # once: the rule, the RX code -> select.json; an audit
    # only on RX-transcriber or RX-setting and the user's word:
    $MAIN -m learn.scratch_readerr xr-build --set cand; xr-check --row xr-cand; xr-search --row xr-cand ...
    $MAIN -m learn.scratch_readerr xr-read --row xr-cand    # P, L, XP_TABLE's code

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
                "learn/knob_ceiling.py", "analysis/aligned.py",
                "learn/readerr_tools.py")    # unit F (Phase 2b): the installs, the manifest reader, the licences
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
SPEC_MODE = {"bp-grid": ("settings", "grid"), "bp-shift": ("settings", "offsets_s"),
             "mt3": ("options", "grid", "allow_globals"), "kong": ("options", "grid", "allow_globals")}
TORCH_MODES = ("mt3", "kong")
TORCH_AXES = {"mt3": ("programs",), "kong": ("onset_threshold", "frame_threshold")}   # Phase 2b's D-E contract
SPEC_REQUIRED = {"bp-grid": ("model", "model_sha256", "settings", "grid"),
                 "bp-shift": ("model", "model_sha256", "settings", "offsets_s"),
                 "mt3": ("model", "model_sha256", "options", "allow_globals"),
                 "kong": ("model", "model_sha256", "options", "allow_globals")}   # #641: the checkpoint's pickle globals
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
    axes = TORCH_AXES[mode] if mode in TORCH_MODES else tuple(GRID_AXES)
    if "grid" in spec and (not isinstance(spec["grid"], dict) or not spec["grid"] or set(spec["grid"]) - set(axes)
                           or any(not isinstance(v, list) or not v for v in spec["grid"].values())):
        raise SystemExit(f"grid must be a non-empty {{axis: [values]}} over {list(axes)}, each axis non-empty "
                         "(the runner refuses an empty grid)")
    if mode in TORCH_MODES and "options" in spec and (not isinstance(spec["options"], dict)
                                                      or set(spec["options"]) - set(axes)):
        raise SystemExit(f"{mode}: options must be an object over {list(axes)}")
    if "allow_globals" in spec:
        a = spec["allow_globals"]
        if not isinstance(a, list) or not a or not all(isinstance(n, str) and "." in n.strip(".") for n in a):
            raise SystemExit("allow_globals must be a non-empty list of 'module.name' strings")
        if len(set(a)) != len(a):
            raise SystemExit("allow_globals repeats a name")
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
    if mode in TORCH_MODES and "grid" in spec:
        got = rec.get("grid")
        if not isinstance(got, list):
            return f"{mode}'s record has no grid"
        want = sorted(json.dumps(o, sort_keys=True) for o in torch_points(spec))
        try:
            have = sorted(json.dumps(g["options"], sort_keys=True) for g in got)
        except (KeyError, TypeError):
            return f"{mode}: a grid entry lacks its options"
        if have != want:
            return f"{mode}'s grid is not the spec's"
        for g in got:
            why = events_refusal(g.get("events"))
            if why:
                return f"grid options {g['options']}: {why}"
        base = next((g for g in got if g["options"] == torch_base(spec)), None)
        if base is not None and base["events"] != rec["events"]:
            return f"{mode}'s top-level events are not the read at its options"
    return None


def torch_base(spec):
    """(Pure.) A torch spec's base options: its `options`, each axis left out at the grid's first value."""
    out = {a: v[0] for a, v in (spec.get("grid") or {}).items()}
    out.update(spec.get("options") or {})
    return out


def torch_points(spec):
    """(Pure.) A torch spec's grid as options dicts: the product over the grid's axes (an axis left out of the grid
    holds its `options` value)."""
    base = torch_base(spec)
    out = [dict(base)]
    for a, vals in (spec.get("grid") or {}).items():
        out = [dict(q, **{a: v}) for q in out for v in vals]
    return out


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

XR_ROWS = ("xr-matched", "xr-found", "xr-filled", "xr-cand")
XR_SHORT = {"xr-matched": "matched", "xr-found": "found", "xr-filled": "filled", "xr-cand": "cand"}
XR_BESIDE = ("hand-plain",)             # built and reported, never searched
XR_SETS = {"first": ("xr-matched", "hand-plain"), "found": ("xr-found",), "filled": ("xr-filled",),
           "cand": ("xr-cand",)}             # Phase 2b's priced row: built only when main's RX code names it
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
    elif kind == "check":                # the first check; xr-cand's own rerun (Phase 2b amendment 2)
        p = xr_dir() / ("check" if row in (None, "xr-matched") else f"check-{XR_SHORT[row]}") / "result.json"
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
        p = xr_dir() / (f"{kind}.json" if row in (None, "xr-matched") else f"{kind}-{XR_SHORT[row]}.json")
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


def require_xr_check(row=None):
    p = xr_search_open(xr_path("check", row))
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
    if set_name == "cand":
        return cmd_xr_build_cand(args)
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
    if getattr(_args, "row", None) == "xr-cand":
        return cmd_xr_check_row(_args, "xr-cand")
    return cmd_xr_check_row(_args, None)


def cmd_xr_check_row(_args, row):
    """xr-check (about 50 renders), once: on `scratch_notes.check_parts`' two parts with xn-reread's stored guitar,
    this module's start reference and `run_part(budget=10, step1_only=True)` must equal xn-reread's stored first 10
    evaluations (`search_check_verdict`), and this module's score of xn-reread's hashed answers must equal its stored
    score files (`score_check_verdict`). A mismatch is XH-stop. -> xr/check/. `--row xr-cand` is Phase 2b
    amendment 2's rerun before any xr-cand search, into its own xr/check-cand/ (the first check is never rewritten),
    after xr-cand's guitar is hashed (phase_scratch_readerr_xr_dry_cand)."""
    needs = (PHASE_XR_DRY,) if row is None else (PHASE_P2B, xr_dry_key(set_of_row(row)))
    m = require_readerr(PHASE_FROZEN, PHASE_P2, *needs, SX.answers_key("xn-reread"))
    res_p = xr_path("check", row)
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
                                        fresh_xr_path("check-start-ref", row, k), sha)
        rec = S.run_part(px, "xn-reread", SX.REF, x32, ref_blank, CB.new_renderer, lists, budget=SN.CHECK_BUDGET,
                         start_ref=sref, dry_sha256=sha, step1_only=True)
        total += rec.get("renders", 0) + used
        write_once(fresh_xr_path("check-search", row, k), rec)
        new_s[k], old_s[k] = rec, json.loads(SX.search_path("xn-reread", k).read_text())
        bank32 = NT.load_dry(BANK_ARM, k, b2)
        sc, used = SX.score_exact_part(px, ans["parts"][k], bank32, SX.load_record(k, records), 0,
                                       tg["parts"][k]["cen_held"], CB.new_renderer)
        total += used
        write_once(fresh_xr_path("check-score", row, k), sc)
        new_c[k], old_c[k] = sc, json.loads(SX.score_path("xn-reread", k).read_text())
    vs, vc = SN.search_check_verdict(new_s, old_s), SX.score_check_verdict(new_c, old_c)
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2 if row is None else PHASE_P2B}", "row": row or "first",
           "renders": total, "budget": SN.CHECK_BUDGET,
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
    require_xr_check(CHECK_ROW.get(row))
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
    The rows are saved before the code. -> xr/rows.json, xr/report.json. `--row xr-cand` reads the priced row
    instead (`cmd_xr_read_cand`, XP_TABLE)."""
    if getattr(_args, "row", None) == "xr-cand":
        return cmd_xr_read_cand(_args)
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


# --- Phase 2a (unit C): the candidates (pure) -------------------------------------------------------------------------------

PHASE_NOTES_KEY = PHASE_NOTES            # phase_scratch_readerr_notes: notes.json's sha256, before `score`
P2A_LABEL = "descriptive: no figure decided (RX-untracked); sign only, not on J0's scale, no size ruled out"
WOULD_PICK = "would-pick, not acted on"
LEAD_IN_S = 1.0
BASE = "base"                            # the stored re-read: every candidate is paired against it
LEAD_ID = "lead-in"
F6_ID = "f6"
DRY_P2A = ("logmel", "env_corr", "pause_error")      # the rebuilt guitar against the bank guitar
DRY_ORIENTATION = {"logmel": "error", "env_corr": "similarity", "pause_error": "error"}
PICK_BY = ("note_error", "logmel", "env_corr")       # grid_pick printed three times, never acted on
SHIFT_ID = {k: f"shift-k{k}" for k in SHIFT_KS}
REAL_GROUPS = ("P1", "P2", "P1|chords", "P1|scales", "P2|chords", "P2|scales", "P2|techniques", "lists")


def grid_id(pt):
    """(Pure.) A grid point's candidate id, e.g. grid-o0.5-f0.3-l58.0-m1."""
    return (f"grid-o{pt['onset_threshold']}-f{pt['frame_threshold']}-l{float(pt['minimum_note_length'])}"
            f"-m{int(bool(pt['melodia_trick']))}")


STORED_ID = grid_id(STORED_POINT)


def candidate_ids():
    """(Pure.) The 149 candidates: the 144 grid points, the lead-in, the shift vote at k = 2, 3, 4, F6 on the stored
    re-read."""
    return [grid_id(p) for p in grid_points()] + [LEAD_ID] + [SHIFT_ID[k] for k in SHIFT_KS] + [F6_ID]


def input_ids(n_bench, n_truth, list_names):
    """(Pure.) Every input's id, never a file or song name: bench-NNN (the part's index in key order), truth-NNN (the
    truth report's window order), list-<name> (the ten known lists)."""
    return ([f"bench-{j:03d}" for j in range(n_bench)] + [f"truth-{i:03d}" for i in range(n_truth)]
            + [f"list-{n}" for n in sorted(list_names)])


def kind_of(iid):
    return iid.split("-", 1)[0]


def select(ids, shard=(0, 1), first=0):
    """(Pure.) A shard's inputs: every n-th of the sorted ids from k; with `first`, only its first n (timing)."""
    k, n = shard
    out = [x for j, x in enumerate(sorted(ids)) if j % n == k]
    return out[:first] if first else out


def notes_specs(model, model_sha256):
    """(Pure.) The three reads per input: the 144-point grid, the stored point with a 1-s lead-in (a one-point grid:
    the runner refuses an empty one), the four shifts."""
    base = dict(NT.BP_SETTINGS)
    return {"grid": make_spec("bp-grid", model, model_sha256, settings=base, grid=declared_grid_spec()),
            "lead": make_spec("bp-grid", model, model_sha256, settings=base,
                              grid={"onset_threshold": [base["onset_threshold"]]}, lead_in_s=LEAD_IN_S),
            "shift": make_spec("bp-shift", model, model_sha256, settings=base, offsets_s=list(SHIFT_OFFSETS_S))}


def events_of(notes):
    """(Pure.) Notes back to the runner's event records (on, off, pitch, amp, bends)."""
    return [{"on": n["on"], "off": n["off"], "pitch": n["pitch"], "amp": n.get("amp", 0.0),
             "bends": list(n.get("bends") or [])} for n in notes]


def candidates_from_records(grid_rec, lead_rec, shift_rec):
    """(Pure.) One input's 148 runner candidates as event lists, each re-based read's clipped bends trimmed
    (`record_notes`): every grid point, the lead-in's read, and the shift vote at k = 2, 3, 4 on the anchor (the
    zero-offset read) against the three shifted reads. -> (candidates, checks: the anchor and k = 1, beside: the
    unanchored notes)."""
    g = record_notes(grid_rec)
    out = {grid_id(x["settings"]): events_of(x["notes"]) for x in g["grid"]}
    lead = record_notes(lead_rec)
    out[LEAD_ID] = events_of(lead["events"])
    sh = record_notes(shift_rec)
    by = {s["offset_s"]: s["notes"] for s in sh["shifts"]}
    anchor = by[0.0]
    others = [by[o] for o in SHIFT_OFFSETS_S[1:]]
    for k in SHIFT_KS:
        out[SHIFT_ID[k]] = events_of(shift_vote(anchor, others, k)[0])
    k1, votes = shift_vote(anchor, others, 1)
    un = shift_unanchored(anchor, others)
    return out, {"anchor": events_of(anchor), "k1": events_of(k1), "votes": votes}, {
        "unanchored": events_of(un), "unanchored_count": len(un)}


def notes_proofs(grid_rec, shift_rec, checks, stored_events):
    """(Pure.) One input's proofs: bp-grid's top-level events equal the stored read's (the declared proof); the
    shift vote's anchor (the zero-offset read) and its k = 1 vote each reproduce the stored events, each compared with
    them directly."""
    stored = events_of(NT.notes_from_events(stored_events))
    return {"grid_top_equal": grid_rec["events"] == stored_events,
            "grid_stored_point_equal": next(x["events"] for x in grid_rec["grid"]
                                            if point_key(x["settings"]) == point_key(STORED_POINT)) == stored_events,
            "anchor_equal": checks["anchor"] == stored, "k1_equal": checks["k1"] == stored}


def coverage_refusal(expected, done):
    """(Pure.) Why a combine may not run, or None: every expected input has its per-input file."""
    miss = sorted(set(expected) - set(done))
    extra = sorted(set(done) - set(expected))
    if miss:
        return f"{len(miss)} input(s) not done yet: run every shard first"
    if extra:
        return f"{len(extra)} unexpected input file(s)"
    return None


def bench_proof_refusal(summaries, n_bench=47):
    """(Pure.) RX-stop unless bp-grid's top-level events equal the stored re-read on every bench input (47 of 47)."""
    bench = {k: v for k, v in summaries.items() if kind_of(k) == "bench"}
    ok = sum(1 for v in bench.values() if v["proofs"]["grid_top_equal"])
    if len(bench) != n_bench or ok != n_bench:
        return f"RX-stop: bp-grid's top-level events equal the stored re-read on {ok} of {n_bench}"
    return None


def counts_of(an):
    """(Pure.) A window's counts for the frontier table."""
    return {"truth": an["truth"], "est": an["est"], "matched": an["matched"], "extras": dict(an["extras"]),
            "misses": dict(an["misses"])}


def frontier(per_input, cands):
    """(Pure.) The frontier table: per candidate (and the base) pooled precision, recall, extras by class and misses by
    class over the inputs given. per_input: {iid: {cand: {"counts": ...}}}."""
    out = {}
    for c in [BASE] + list(cands):
        cs = [r[c]["counts"] for r in per_input.values() if c in r]
        if not cs:
            continue
        t, e, m = (sum(x[q] for x in cs) for q in ("truth", "est", "matched"))
        out[c] = {"inputs": len(cs), "precision": m / e if e else None, "recall": m / t if t else None,
                  "extras": {k: sum(x["extras"].get(k, 0) for x in cs) for k in EXTRA_CLASSES},
                  "misses": {k: sum(x["misses"].get(k, 0) for x in cs) for k in MISS_ORDER}}
    return out


def p2a_figures():
    """(Pure.) The figures every bench candidate carries: the 23 note figures and the rebuilt guitar's three."""
    return NOTE_FIGURES + DRY_P2A


def p2a_orientation(f):
    return DRY_ORIENTATION[f] if f in DRY_ORIENTATION else ORIENTATION[f]


def paired_reads(per_part, cand, rows_of):
    """(Pure but for `rows_of`.) A candidate's paired differences against the base, per figure: per part cand less
    base, then `rows_of(values)` (set_rows: the 40 pooled, BKS, GOAT, all 47), labelled sign only by the figure's
    orientation. per_part: {pkey: {cand: {"figures": {...}}}}."""
    out = {}
    for f in p2a_figures():
        d = {}
        for k, r in per_part.items():
            a, b = (r.get(cand) or {}).get("figures", {}).get(f), (r.get(BASE) or {}).get("figures", {}).get(f)
            if a is not None and b is not None:
                d[k] = a - b
        rows = rows_of(d) if d else None
        out[f] = {"parts": len(d), "rows": rows, "label": sign_label((rows or {}).get("bks_goat"), p2a_orientation(f)),
                  "words": P2A_LABEL}
    return out


def real_reads(rows, cand):
    """(Pure.) The real-DI arm, note figures only: per group (P1, P2, each player and kind, the lists) the candidate
    less the base per window, then `note_versions.set_numbers` (file-clustered), labelled sign only. rows: [{group,
    kind, cluster, iid, figures: {cand: {...}}}]."""
    out = {}
    for g in REAL_GROUPS:
        inside = [r for r in rows if (r["group"] == g if "|" not in g else f"{r['group']}|{r['kind']}" == g)]
        if not inside:
            continue
        out[g] = {}
        for f in NOTE_FIGURES:
            d = []
            for r in inside:
                a, b = (r["figures"].get(cand) or {}).get(f), (r["figures"].get(BASE) or {}).get(f)
                if a is not None and b is not None:
                    d.append((r["cluster"], {"d": a - b}))
            iv = NV.set_numbers(d, "d")
            out[g][f] = {"interval": iv, "label": sign_label(iv if iv and iv.get("lo90") is not None else None,
                                                             ORIENTATION[f])}
    return out


def would_picks(per_part, mean_rows_of):
    """(Pure but for `mean_rows_of`.) `grid_pick` three times (note error, logmel, env_corr), each marked "would-pick,
    not acted on"; an edge minimum is reported, never extended. mean_rows_of(values) -> the 40's pooled interval."""
    pts = grid_points()
    out = {}
    for f in PICK_BY:
        vals = {grid_id(p): {k: (r.get(grid_id(p)) or {}).get("figures", {}).get(f) for k, r in per_part.items()}
                for p in pts}
        means = {}
        for p in pts:
            iv = mean_rows_of({k: v for k, v in vals[grid_id(p)].items() if v is not None})
            means[grid_id(p)] = (iv or {}).get("mean")

        def diff_of(p, mn, vals=vals):
            a, b = vals[grid_id(p)], vals[grid_id(mn)]
            return mean_rows_of({k: a[k] - b[k] for k in a if a[k] is not None and b.get(k) is not None})
        got = grid_pick(pts, lambda p: means[grid_id(p)], diff_of, p2a_orientation(f))
        out[f] = {"words": WOULD_PICK, "minimum": grid_id(got["minimum"]) if got else None,
                  "pick": grid_id(got["pick"]) if got else None, "near": [grid_id(x) for x in got["near"]] if got else [],
                  "distance": got["distance"] if got else None,
                  "edge_reported_not_extended": got["edge"] if got else None, "selected_from": len(pts)}
    return out


def stored_point_refusal(per_part, xb_parts):
    """(Pure.) RX-stop unless, at the stored point, the base's rebuilt guitar's logmel, env_corr and mask equal
    build.json's stored xn-reread figures on every part (47 of 47)."""
    bad = 0
    for k, r in per_part.items():
        got = (r.get(BASE) or {}).get("stored_check") or {}
        want = xb_parts[k]["guitars"]["xn-reread"]["figures"]
        if not (got.get("logmel") == want.get("logmel") and got.get("env_corr") == want.get("env_corr")
                and got.get("mask") == {str(n): v for n, v in (want.get("mask") or {}).items()}):
            bad += 1
    if bad or len(per_part) != len(xb_parts):
        return (f"RX-stop: at the stored point the rebuilt guitar's figures equal build.json's on "
                f"{len(per_part) - bad} of {len(xb_parts)}")
    return None


# --- Phase 2a: paths ----------------------------------------------------------------------------------------------------

def p2a_path(kind, cand=None, iid=None, root=None):
    """Phase 2a's files, under PF/fs/readerr/. Each input's notes sit in one folder, notes/inputs/<input>/ (the
    candidates <candidate>.json, the raw reads raw-<read>.json, summary.json), made whole in a partial folder and moved
    into place at once (`move_into_place`); `root` names that partial folder while it is built. Then notes.json;
    score/inputs/<input>.json, candidates.json; the timing sidecars under notes/timing/ and score/timing/, never in
    a hash chain."""
    r = readerr_dir()
    folder = pathlib.Path(root) if root is not None else r / "notes" / "inputs" / str(iid)
    if kind == "input-dir":
        return folder
    if kind == "cand":
        return folder / f"{cand}.json"
    if kind == "raw":
        return folder / f"raw-{cand}.json"
    if kind == "notes-input":
        return folder / "summary.json"
    if kind == "partial":
        return r / "notes" / "partial"
    if kind == "timing":
        return r / cand / "timing"
    if kind == "listing":
        return r / "notes.json"
    if kind == "score-input":
        return r / "score" / "inputs" / f"{iid}.json"
    if kind == "candidates":
        return r / "candidates.json"
    raise ValueError(kind)


# --- Phase 2a: the inputs ------------------------------------------------------------------------------------------------

def bench_inputs(tr):
    """{bench id: (part key, wav, stored record)} for the 47 bench inputs (exact/work/reread/NNN-tr-di.*), each wav's
    sha256 its stored record's `input_sha256`; parts in key order, as `scratch_exact.cmd_build` ran them."""
    out = {}
    for j, key in enumerate(sorted(tr["parts"])):
        w = SX.work_dir() / "reread" / f"{j:03d}-{BANK_ARM}.wav"
        rec = json.loads(w.with_suffix(".json").read_text())
        if file_sha(w) != rec["input_sha256"]:
            raise SystemExit(f"bench input {j}: the wav is not the stored record's input")
        out[f"bench-{j:03d}"] = (key, w, rec)
    return out


def _by_input_sha(folder, wanted):
    """{sha256: wav} for exactly the inputs `wanted` (the note files' `input_sha256`) among a work folder's stored
    records; refused when one is missing. Nothing else in the folder is kept."""
    want, out = set(wanted), {}
    for p in sorted(pathlib.Path(folder).glob("*.json")):
        sha = json.loads(p.read_text()).get("input_sha256")
        w = p.with_suffix(".wav")
        if sha in want and w.exists():
            out[sha] = w
    miss = want - set(out)
    if miss:
        raise SystemExit(f"{len(miss)} note file input(s) are not in {pathlib.Path(folder).name}")
    return out


def real_inputs(mr, pair):
    """{truth or list id: (source, wav, stored events, meta)} for the real-DI arm, every one through `real_di_source`
    (P3 never): the truth report's 79 windows (their stored Basic Pitch input, found by the note file's
    `input_sha256`) and the ten lists (the install gate's stored inputs)."""
    listing = NT.require_truth(mr)
    report = NT.require_truth_report(mr.get(NR.LEDGER_ID))
    by_key = {w["key"]: w for w in listing["windows"]}
    recs = []
    for w in report["windows"]:
        real_di_source(f"truth:{w['key']}", listing)
        recs.append(TX.bp_note("truth", w["key"], w["note_file_sha256"], pair))
    work = _by_input_sha(NT.REDO / "work" / "truth-report", [r["input_sha256"] for r in recs])
    out = {}
    for i, (w, rec) in enumerate(zip(report["windows"], recs)):
        wav = work[rec["input_sha256"]]
        if file_sha(wav) != rec["input_sha256"]:
            raise SystemExit(f"truth window {i}: the wav is not the note file's input")
        win = by_key[w["key"]]
        out[f"truth-{i:03d}"] = (f"truth:{w['key']}", wav, rec["events"],
                                 {"group": w["player"], "kind": w["kind"], "pre_s": rec["pre_s"], "window": win,
                                  "cluster": f"{win['player']}|{win['kind']}|{win['name']}"})
    known = TX.gate_known()
    for p in sorted((NT.gate_work_dir() / "known").glob("*.json")):
        nm = p.stem.split("-", 1)[1]
        rec = json.loads(p.read_text())
        real_di_source(f"list:{nm}")
        w = p.with_suffix(".wav")
        if file_sha(w) != rec["input_sha256"] or rec["events"] != known[nm]:
            raise SystemExit(f"list {nm}: the stored input is not the gate's")
        out[f"list-{nm}"] = (f"list:{nm}", w, rec["events"], {"group": "lists", "kind": None, "pre_s": 0.0,
                                                               "cluster": nm})
    return out, listing


def run_runner(spec_name, spec, mode, jobs, work):
    """Basic Pitch's runner (`learn/readerr_run.py`, the venv's interpreter, -I, one thread) on [(iid, wav)] in one
    process, outputs into `work` (a temporary folder). -> {iid: record}, each checked by `runner_refusal`."""
    import os

    pairs = [(wav, pathlib.Path(work) / f"{spec_name}-{iid}.json") for iid, wav in jobs]
    env = runner_env(os.environ, False)
    env.update({k: "1" for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")})
    r = subprocess.run(runner_argv(NT.BP_PYTHON, mode, spec, pairs), capture_output=True, text=True, env=env)
    if r.returncode:
        raise SystemExit(f"readerr_run {mode} failed: {r.stderr.strip()[-400:]}")
    out = {}
    for (iid, wav), (_, o) in zip(jobs, pairs):
        rec = json.loads(pathlib.Path(o).read_text())
        why = runner_refusal(rec, mode, spec, file_sha(wav))
        if why:
            raise SystemExit(f"{iid} ({spec_name}): {why}")
        out[iid] = rec
    return out


# --- Phase 2a: notes (zero renders, Basic Pitch only) -------------------------------------------------------------------------

def cmd_notes(args):
    """Phase 2a's `notes` (zero renders), a shard at a time (`--shard k/n`, `--first` for timing): per input, three
    runner reads in the Basic Pitch venv (one thread; the model loaded once a read): the 144-point grid, the stored
    point with a 1-s lead-in, the four shifts. Proof before anything of an input is written: bp-grid's top-level
    events equal the stored read's (and the shift vote's anchor and k = 1 reproduce it). Then every runner candidate
    (`candidates_from_records`) to notes/<candidate>/<input>.json, the raw reads to notes/raw/, and the input's summary.
    An input already done is skipped. `--combine`, once every shard is done: RX-stop unless the bench proof holds on
    47 of 47; else notes.json, the listing (every file's sha256), whose sha256 goes to main as
    phase_scratch_readerr_notes before `score`."""
    m = require_readerr(PHASE_FROZEN, PHASE_P2)
    tr = require_trace(m)
    mr, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    pair = NT.install_pair(NT.load_manifest())
    man = NT.load_manifest()
    if man["model_sha256"] != pair[1]:
        raise SystemExit("the manifest's model is not the install's")
    bench = bench_inputs(tr)
    real, _listing = real_inputs(mr, pair)
    ids = sorted(bench) + sorted(real)
    if getattr(args, "combine", False):
        return notes_combine(ids, bench)
    specs = notes_specs(man["model_path"], man["model_sha256"])
    done = done_inputs("notes")
    todo = [i for i in select(ids, args.shard, getattr(args, "first", 0)) if i not in done]
    if not todo:
        print("RX NOTES: nothing to do in this shard")
        return
    import tempfile

    partial = p2a_path("partial")
    left = sorted(x.name for x in partial.iterdir()) if partial.exists() else []
    if left:
        print(f"RX NOTES: {len(left)} partial folder(s) from an interrupted run under {partial.name}/ (never read; "
              "safe to remove)", flush=True)

    wav_of = {i: (bench[i][1] if i in bench else real[i][1]) for i in todo}
    stored_of = {i: (bench[i][2]["events"] if i in bench else real[i][2]) for i in todo}
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="readerr-notes-") as work:
        recs = {name: run_runner(name, specs[name], "bp-shift" if name == "shift" else "bp-grid",
                                 [(i, wav_of[i]) for i in todo], work) for name in ("grid", "lead", "shift")}
        secs = round(time.time() - t0, 1)
        stops = []
        for i in todo:
            cands, checks, beside = candidates_from_records(recs["grid"][i], recs["lead"][i], recs["shift"][i])
            proofs = notes_proofs(recs["grid"][i], recs["shift"][i], checks, stored_of[i])
            if kind_of(i) == "bench" and not all(proofs.values()):
                stops.append(i)
                continue
            staging = new_staging(i)
            shas = {c: write_once(p2a_path("cand", c, i, root=staging), {"input": i, "candidate": c, "events": ev})
                    for c, ev in sorted(cands.items())}
            raw = {n: write_once(p2a_path("raw", n, i, root=staging), recs[n][i]) for n in ("grid", "lead", "shift")}
            write_once(p2a_path("notes-input", iid=i, root=staging), {
                "plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2}", "input": i, "input_sha256": file_sha(wav_of[i]),
                "proofs": proofs, "candidates": shas, "raw": raw, "beside": beside, "votes": checks["votes"]})
            move_into_place(staging, p2a_path("input-dir", iid=i))
    write_timing("notes", args.shard, {"inputs": todo, "written": len(todo) - len(stops), "reads_seconds": secs,
                                        "seconds": round(time.time() - t0, 1)})
    print(f"RX NOTES shard {args.shard[0]}/{args.shard[1]}: {len(todo) - len(stops)} of {len(todo)} inputs written "
          f"in {time.time() - t0:.0f} s ({secs} s of reads)")
    if stops:
        raise SystemExit(f"RX-stop: bp-grid's top-level events differ from the stored re-read on {len(stops)} bench "
                         "input(s): nothing of them written; to the orchestrator")


def new_staging(iid):
    """A fresh partial folder for one input, under notes/partial/ (a unique name: a crashed run's leftover never
    blocks a rerun, and is never read)."""
    import tempfile

    partial = p2a_path("partial")
    partial.mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(prefix=f"{iid}-", dir=partial))


def move_into_place(staging, final):
    """An input's notes folder, complete, moved into place in one rename (the same file system): never over a folder,
    never outside PF/fs/readerr/."""
    staging, final = pathlib.Path(staging), pathlib.Path(final)
    root = pathlib.Path(readerr_dir()).resolve()
    if root not in final.resolve().parents or root not in staging.resolve().parents:
        raise SystemExit(f"{final}: outside {root}")
    if final.exists():
        raise SystemExit(f"{final} exists: never overwritten")
    final.parent.mkdir(parents=True, exist_ok=True)
    staging.rename(final)
    return final


def done_inputs(kind):
    """The inputs whose files are complete: a notes folder with its summary, or a score file."""
    if kind == "notes":
        d = readerr_dir() / "notes" / "inputs"
        return {x.name for x in d.iterdir() if (x / "summary.json").exists()} if d.exists() else set()
    d = readerr_dir() / "score" / "inputs"
    return {x.stem for x in d.glob("*.json")} if d.exists() else set()


def write_timing(command, shard, body):
    """The timing sidecar (seconds, shard), outside every hash chain, so a listing's sha256 is the same however the
    run is sharded."""
    tag = f"shard-{shard[0]}-of-{shard[1]}-{time.strftime('%Y%m%d-%H%M%S')}"
    return write_once(p2a_path("timing", command) / f"{tag}.json", dict(body, command=command, shard=list(shard)))


def notes_combine(ids, bench):
    path = p2a_path("listing")
    NT.never_overwrite(path)
    done = done_inputs("notes")
    why = coverage_refusal(ids, done)
    if why:
        raise SystemExit(why)
    summ = {i: json.loads(p2a_path("notes-input", iid=i).read_text()) for i in ids}
    why = bench_proof_refusal(summ, len(bench))
    if why:
        raise SystemExit(why)
    cands = candidate_ids()[:-1]
    for i, s in summ.items():
        if sorted(s["candidates"]) != sorted(cands):
            raise SystemExit(f"{i}: not the 148 runner candidates")
        for c, sha in s["candidates"].items():
            if file_sha(p2a_path("cand", c, i)) != sha:
                raise SystemExit(f"{i} {c}: the file changed since `notes`")
    body = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2}", "renders": 0, "candidates": candidate_ids(),
            "runner_candidates": len(cands), "inputs": {i: {"summary_sha256": file_sha(p2a_path("notes-input", iid=i)),
                                                           "input_sha256": s["input_sha256"]} for i, s in summ.items()},
            "proofs": {k: sum(1 for i, s in summ.items() if kind_of(i) == "bench" and s["proofs"][k])
                       for k in ("grid_top_equal", "grid_stored_point_equal", "anchor_equal", "k1_equal")},
            "real_checks": {k: sum(1 for i, s in summ.items() if kind_of(i) != "bench" and s["proofs"][k])
                            for k in ("grid_top_equal", "anchor_equal")},
            "unanchored": {"bench": sum(s["beside"]["unanchored_count"] for i, s in summ.items() if kind_of(i) == "bench"),
                           "real": sum(s["beside"]["unanchored_count"] for i, s in summ.items() if kind_of(i) != "bench")},
            "counts": {"bench": len(bench), "real": len(ids) - len(bench)}, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    sha = write_once(path, body)
    print(f"RX NOTES COMBINE: {len(ids)} inputs; bench proofs {body['proofs']}; real checks {body['real_checks']}; "
          f"sha256 {sha} (into the ledger as {PHASE_NOTES_KEY} before `score`)")


# --- Phase 2a: score (zero renders) -------------------------------------------------------------------------------------------

def load_candidate(listing, iid, cand):
    """A runner candidate's events, refused unless its input summary is the listing's and the file the summary's."""
    sp = p2a_path("notes-input", iid=iid)
    if file_sha(sp) != listing["inputs"][iid]["summary_sha256"]:
        raise SystemExit(f"{iid}: the input summary is not the hashed listing's")
    s = json.loads(sp.read_text())
    p = p2a_path("cand", cand, iid)
    if file_sha(p) != s["candidates"][cand]:
        raise SystemExit(f"{iid} {cand}: not the listed file")
    return json.loads(p.read_text())["events"]


def scored_list(events, di, fixes, length_s, pre_s=0.0):
    """A candidate's events as the stored re-read was treated: `timed_notes` against the DI it was read from, then
    the fixes; with the notes before the snap and the clean-up's losses for the anatomy. -> (notes, presnap, lost)."""
    notes, trep = NT.timed_notes({"events": events, "pre_s": pre_s}, di)
    fixed, _ = NF.apply_fixes(notes, fixes, di)
    off_s = trep["window_offset_ms"] / 1000.0
    return (fixed, presnap_notes(events, pre_s, off_s, length_s), lost_on_timeline(events, pre_s, off_s, length_s))


def cmd_score_p2a(args):
    """Phase 2a's `score` (zero renders), a shard at a time (`--shard k/n`, `--first` for timing): per bench part, the
    base (the stored re-read) and the 149 candidates (F6: build 3's frozen rule on the stored re-read), each timed and
    fixed as the re-read was; the note figures on the as-played list (`anatomy`, `note_figures`) and the rebuilt
    guitar's logmel, env_corr and pause error against the bank guitar (`rebuild_redo` as proof 4; one rebuild per
    distinct list). Per real-DI input, the note figures only. An input already done is skipped. `--combine`, once
    every shard is done: RX-stop unless the base's rebuilt figures equal build.json's on 47 of 47; then per candidate
    the paired differences (set_rows: the 40, BKS, GOAT, all 47), the frontier table, the real-DI arm and grid_pick
    three ways, every line descriptive. -> score/inputs/<input>.json, candidates.json. No RX code."""
    m = require_readerr(PHASE_FROZEN, PHASE_P2, PHASE_NOTES_KEY)
    listing = NT.require_file_hash(m, PHASE_NOTES_KEY, p2a_path("listing"))
    tr = require_trace(m)
    xb = SX.require_xbuild(m)
    mr, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    ids = sorted(listing["inputs"])
    if getattr(args, "combine", False):
        return score_combine(m, ids, xb)
    import numpy as np

    from learn import song_bank as SB

    b2 = SX.bank_build(m)
    pair = NT.install_pair(NT.load_manifest())
    rule = ((mr.get(NR.LEDGER_ID) or {}).get(NF.PHASE_F6_FROZEN) or {}).get("rule")
    if not rule or not rule.get("F6"):
        raise SystemExit(f"no {NF.PHASE_F6_FROZEN} rule on main")
    fixes = tr["fixes"]
    f6_fixes = dict(fixes, F6=rule["F6"])
    excl, _, _, _ = NT._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    finish_of = {key: fin for kind, key, _i, _r, _d, fin in NT.build_todo(pair, NT.ear_items_file(BUILD2))
                 if kind == "part"}
    bench = bench_inputs(tr)
    real, truth_listing = real_inputs(mr, pair)
    ta = None
    cands = candidate_ids()
    done = done_inputs("score")
    todo = [i for i in select(ids, args.shard, getattr(args, "first", 0)) if i not in done]
    t0, seconds = time.time(), {}
    for i in todo:
        t1 = time.time()
        if kind_of(i) == "bench":
            key, _w, rec = bench[i]
            row = tr["parts"][key]
            bank64 = np.asarray(NT.load_dry(BANK_ARM, key, b2), np.float64)
            L = len(bank64) / NR.SR
            truth = row["played"]
            lists = {BASE: scored_list(rec["events"], bank64, fixes, L)}
            if lists[BASE][0] != row["reread"]:
                raise SystemExit(f"{i}: the base is not trace.json's re-read")
            lists[F6_ID] = scored_list(rec["events"], bank64, f6_fixes, L)
            for c in cands:
                if c != F6_ID:
                    lists[c] = scored_list(load_candidate(listing, i, c), bank64, fixes, L)
            cache, res = {}, {}
            for c, (notes, pre, lost) in lists.items():
                an = anatomy(truth, notes, pre, lost)
                figs = note_figures(an, truth, notes, L)
                ck = json.dumps(notes, sort_keys=True)
                if ck not in cache:
                    y, _ = NR.rebuild_redo(BANK_ARM, notes, len(bank64), bank, bank64, tr["ring_variant"],
                                           finish=finish_of[key], loud=None)
                    d = np.asarray(np.asarray(y, np.float32), np.float64)
                    fig = NR.figures(bank64, d)
                    cache[ck] = {"logmel": fig["logmel"], "env_corr": fig["env_corr"],
                                 "pause_error": pause_error(fig), "mask": fig["mask"]}
                dry = cache[ck]
                res[c] = {"figures": dict(figs, logmel=dry["logmel"], env_corr=dry["env_corr"],
                                          pause_error=dry["pause_error"]), "counts": counts_of(an)}
                if c == BASE:
                    res[c]["stored_check"] = {"logmel": dry["logmel"], "env_corr": dry["env_corr"],
                                              "mask": {str(n): v for n, v in dry["mask"].items()}}
            body = {"input": i, "part": key, "kind": "bench", "candidates": res, "rebuilds": len(cache)}
        else:
            source, _w, events, meta = real[i]
            if kind_of(i) == "truth":
                ta = ta or NT.TruthAudio(truth_listing)
                di, _, _, truth = ta.window(meta["window"])
            else:
                nm = i.split("-", 1)[1]
                di = SB.measure(NT.known_audio(nm, bank))
                truth = [dict(n) for n in NT.KNOWN_NOTES[nm]]
            L = len(di) / NR.SR
            lists = {BASE: scored_list(events, di, fixes, L, meta["pre_s"]),
                     F6_ID: scored_list(events, di, f6_fixes, L, meta["pre_s"])}
            for c in cands:
                if c != F6_ID:
                    lists[c] = scored_list(load_candidate(listing, i, c), di, fixes, L, meta["pre_s"])
            res = {}
            for c, (notes, pre, lost) in lists.items():
                an = anatomy(truth, notes, pre, lost)
                res[c] = {"figures": note_figures(an, truth, notes, L), "counts": counts_of(an)}
            body = {"input": i, "kind": kind_of(i), "group": meta["group"], "kind_of_window": meta["kind"],
                    "cluster": meta["cluster"], "candidates": res}
        body.update(plan=PLAN, listing_sha256=file_sha(p2a_path("listing")))
        write_once(p2a_path("score-input", iid=i), body)
        seconds[i] = round(time.time() - t1, 1)
        print(f"{i}: {len(body['candidates'])} lists scored in {seconds[i]} s", flush=True)
    write_timing("score", args.shard, {"inputs": todo, "seconds_per_input": seconds,
                                        "seconds": round(time.time() - t0, 1)})
    print(f"RX SCORE shard {args.shard[0]}/{args.shard[1]}: {len(todo)} inputs in {time.time() - t0:.0f} s")


def score_combine(m, ids, xb):
    path = p2a_path("candidates")
    NT.never_overwrite(path)
    done = done_inputs("score")
    why = coverage_refusal(ids, done)
    if why:
        raise SystemExit(why)
    lsha = file_sha(p2a_path("listing"))
    rows = {i: json.loads(p2a_path("score-input", iid=i).read_text()) for i in ids}
    if any(r["listing_sha256"] != lsha for r in rows.values()):
        raise SystemExit("a score file was made from another listing")
    per_part = {r["part"]: r["candidates"] for r in rows.values() if r["kind"] == "bench"}
    why = stored_point_refusal(per_part, xb["parts"])
    if why:
        raise SystemExit(why)
    draw, sd = SX.context()
    cands = candidate_ids()
    real_rows = [{"group": r["group"], "kind": r["kind_of_window"], "cluster": r["cluster"], "iid": i,
                  "figures": {c: v["figures"] for c, v in r["candidates"].items()}}
                 for i, r in rows.items() if r["kind"] != "bench"]

    def rows_of(vals):
        return _rows(sd, draw, vals)

    def mean_rows_of(vals):
        return _rows(sd, draw, vals)["bks_goat"]
    body = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2}", "renders": 0, "words": P2A_LABEL, "rx_code": None,
            "listing_sha256": lsha, "base": "the stored re-read (xn-reread's notes)", "stored_point": STORED_ID,
            "paired": {c: paired_reads(per_part, c, rows_of) for c in cands},
            "frontier": {"bench": frontier({k: v for k, v in per_part.items()}, cands),
                         **{g: frontier({r["iid"]: rows[r["iid"]]["candidates"] for r in real_rows
                                         if (r["group"] == g if "|" not in g else f"{r['group']}|{r['kind']}" == g)},
                                        cands) for g in REAL_GROUPS}},
            "real": {c: real_reads(real_rows, c) for c in cands},
            "would_pick": would_picks(per_part, mean_rows_of),
            "rebuilds": sum(r.get("rebuilds", 0) for r in rows.values() if r["kind"] == "bench"),
            "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    sha = write_once(path, body)
    for f, w in body["would_pick"].items():
        print(f"{f}: {w['words']}: minimum {w['minimum']}, pick {w['pick']}, edge {w['edge_reported_not_extended']}")
    print(f"RX SCORE COMBINE: {len(per_part)} parts, {len(real_rows)} real-DI inputs; {P2A_LABEL}; sha256 {sha}")


# --- Phase 2b (`phase_scratch_readerr_p2b`, unit E): the transcribers' candidates (pure) -------------------------------

PHASE_P2B = "phase_scratch_readerr_p2b"
PHASE_TOOLS = "phase_scratch_readerr_tools"              # tools-gate.json: the checkpoints, the repeat, the timing
PHASE_NOTES_TX = "phase_scratch_readerr_notes_tx"        # notes-tx.json, before tx-score
PHASE_CANDIDATES = "phase_scratch_readerr_candidates"    # Phase 2a's candidates.json (on main)
PHASE_CANDIDATES_TX = "phase_scratch_readerr_candidates_tx"   # candidates-tx.json, before select
PHASE_XP_OUTCOME = "phase_scratch_readerr_xp_outcome"    # the XP code, after an audit
CHECK_ROW = {"xr-cand": "xr-cand"}       # amendment 2: xr-check reruns before any xr-cand search, into its own file
BP_SUFFIX = "+bp"                        # loudness and bends borrowed from the paired Basic Pitch note
TX_THREADS = 1                           # every torch read at one thread; the gate times 1 and 2
TX_FAMILIES = {   # amendment 5: the declared grids and the shipped settings (the distance's zero)
    "ymt3": {"lock": "A", "mode": "mt3", "axes": {"programs": ("pitched", "guitar")},
             "shipped": {"programs": "pitched"}},
    "kong-fl": {"lock": "B", "mode": "kong",
                "axes": {"onset_threshold": (0.2, 0.3, 0.4, 0.5), "frame_threshold": (0.1, 0.2, 0.3)},
                "shipped": {"onset_threshold": 0.3, "frame_threshold": 0.1}},
    "kong-gaps": {"lock": "B", "mode": "kong",
                  "axes": {"onset_threshold": (0.2, 0.3, 0.4, 0.5), "frame_threshold": (0.1, 0.2, 0.3)},
                  "shipped": {"onset_threshold": 0.3, "frame_threshold": 0.1}},
}
BP_LICENCE = {"code": "Apache-2.0", "weights_data": "in the wheel", "product_status": "usable"}
PRODUCT_USABLE = "usable"
GATE_REPEAT_PARTS = 4                    # amendment item 5: three runs on 4 bench parts
GATE_TIMING_PARTS = 3                    # item 6: timed on 3 parts, at 1 and at 2 threads
ONSET_ERROR = "onset_error"              # amendment 3: the matched notes' median |onset error| (ms), as played


def tx_points(fam):
    """(Pure.) A family's declared options: the product over its axes in order, the first outermost."""
    out = [{}]
    for a, vals in TX_FAMILIES[fam]["axes"].items():
        out = [dict(q, **{a: v}) for q in out for v in vals]
    return out


def tx_id(fam, opts):
    """(Pure.) A transcriber candidate's id: ymt3-pitched, kong-fl-o0.3-f0.1."""
    if TX_FAMILIES[fam]["mode"] == "mt3":
        return f"{fam}-{opts['programs']}"
    return f"{fam}-o{opts['onset_threshold']}-f{opts['frame_threshold']}"


def tx_candidates():
    """(Pure.) Every transcriber candidate: {plain id: (family, options)}; 26 at the declaration."""
    return {tx_id(f, o): (f, o) for f in TX_FAMILIES for o in tx_points(f)}


def tx_distance(fam, opts):
    """(Pure.) Amendment 5's distance to the shipped settings: YourMT3+'s programmes one step apart (every pitched
    programme shipped); the Riley models' L1 in grid steps on (onset, frame)."""
    sh = TX_FAMILIES[fam]["shipped"]
    d = 0
    for a, vals in TX_FAMILIES[fam]["axes"].items():
        vals = list(vals)
        d += abs(vals.index(opts[a]) - vals.index(sh[a]))
    return d


def tx_spec(fam, model, model_sha256, allow_globals, threads=TX_THREADS):
    """(Pure.) A family's one read: its shipped options, the declared grid from one inference, and the checkpoint's
    pickle globals (#641: the runner's guarded load allows exactly these)."""
    f = TX_FAMILIES[fam]
    return make_spec(f["mode"], model, model_sha256, threads=threads, options=dict(f["shipped"]),
                     grid={a: list(v) for a, v in f["axes"].items()}, allow_globals=list(allow_globals))


TX_MANIFEST_ITEM = {"ymt3": "yourmt3-moe-nops", "kong-fl": "guitar-fl", "kong-gaps": "guitar-gaps"}
ALLOW_FIELD = "pickle_globals"           # the manifest item's list of "module.name" globals (see tx_allow_globals)


def tx_allow_globals(man, fam):
    """(Pure.) A checkpoint's pickle globals from the manifest (`readerr_tools.load_manifest()`): its item's
    `pickle_globals`, a list of "module.name". Refused when the manifest lists none: the allowlist is never guessed."""
    items = [i for i in (man or {}).get("items") or [] if i.get("id") == TX_MANIFEST_ITEM[fam]]
    if len(items) != 1:
        raise SystemExit(f"the manifest holds {len(items)} items for {fam}")
    g = items[0].get(ALLOW_FIELD)
    if not isinstance(g, list) or not g:
        raise SystemExit(f"the manifest lists no {ALLOW_FIELD} for {fam}: the guarded load's allowlist has no source")
    return list(g)


def family_of(cid):
    """(Pure.) A selection candidate's family, kind and distance to its shipped settings: the Basic Pitch grid (by
    `grid_distance` from the stored point), the shift vote (k - 2: k = 2 keeps the most), the lead-in and F6 alone
    (shipped), or a transcriber's family (its `+bp` list). -> {family, kind, distance, shipped}."""
    base = cid[:-len(BP_SUFFIX)] if cid.endswith(BP_SUFFIX) else cid
    txc = tx_candidates()
    if base in txc:
        fam, opts = txc[base]
        d = tx_distance(fam, opts)
        return {"family": fam, "kind": "transcriber", "distance": d, "shipped": d == 0}
    if cid.startswith("grid-"):
        pt = next(p for p in grid_points() if grid_id(p) == cid)
        d = grid_distance(pt, STORED_POINT, GRID_AXES)
        return {"family": "bp-grid", "kind": "setting", "distance": d, "shipped": d == 0}
    if cid in SHIFT_ID.values():
        k = int(cid.rsplit("k", 1)[1])
        return {"family": "shift", "kind": "setting", "distance": k - min(SHIFT_KS), "shipped": False}
    if cid in (LEAD_ID, F6_ID):
        return {"family": cid, "kind": "setting", "distance": 0, "shipped": True}
    raise ValueError(cid)


def select_ids():
    """(Pure.) The candidates `select` reads: Phase 2a's 149 and every transcriber's `+bp` list (every item is read on
    the list that would be priced)."""
    return candidate_ids() + [c + BP_SUFFIX for c in tx_candidates()]


# --- Phase 2b: select's rule (pure) ------------------------------------------------------------------------------------

SELECT_ITEMS = ("extra_rate", "miss_rate", "end_error", ONSET_ERROR)   # items 1, 2 and amendment 3's two, sign only
SELECT_SETS = ("deciding", "bks", "goat")


def select_constants(rows, treat="itt"):
    """(Pure.) The rule's constants read from the hashed xr/rows.json (answer arm, the 40): E's mean and its interval's
    half-width h, and M's mean. treat "itt" decides; "per" is the passing-only recompute (amendment 4)."""
    r = rows["arms"]["answer"]["rows"][treat]
    e, m = r["E"]["bks_goat"], r["M"]["bks_goat"]
    return {"E": e["mean"], "M": m["mean"], "h": (e["hi90"] - e["lo90"]) / 2, "treat": treat}


def predicted_g(counts, base, consts):
    """(Pure.) g = E x + M y: x the share of extras removed, y the share of misses added, on one set's counts."""
    if not base["extras"] or not base["misses"]:
        return None
    x = 1 - counts["extras"] / base["extras"]
    y = counts["misses"] / base["misses"] - 1
    return consts["E"] * x + consts["M"] * y


def items_on(c, base, consts, s):
    """(Pure.) One candidate's items on one set s: extra_rate "better"; miss_rate, end error and onset error not
    "worse" (sign only); g <= -h. c: {counts: {set: {extras, misses}}, labels: {set: {figure: reading}}}."""
    lab = (c.get("labels") or {}).get(s) or {}
    g = predicted_g(c["counts"][s], base[s], consts)
    return {"extra_rate": lab.get("extra_rate") == "better",
            "miss_rate": lab.get("miss_rate") not in ("worse", None),
            "end_error": lab.get("end_error") not in ("worse", None),
            ONSET_ERROR: lab.get(ONSET_ERROR) not in ("worse", None),
            "g": g, "g_ok": g is not None and g <= -consts["h"]}


def _form2(it):
    return it["extra_rate"] and it["miss_rate"] and it["end_error"] and it[ONSET_ERROR]


def family_pick(members, base, consts):
    """(Pure.) Item 4, the cross-set rule, for a family whose settings the data chose: on BKS, the member with the
    lowest g among those meeting items 1 and 2 (and amendment 3's two) there must meet items 1 to 3 on GOAT, and the
    reverse; if the two picks differ, the one nearer the shipped settings is taken and must pass both ways.
    members: {cid: candidate}. -> {pick, passes, bks_pick, goat_pick}."""
    def best(s):
        ok = [(cid, items_on(c, base, consts, s)) for cid, c in members.items()]
        ok = [(cid, it) for cid, it in ok if _form2(it) and it["g"] is not None]
        if not ok:
            return None
        return min(ok, key=lambda t: (t[1]["g"], members[t[0]]["distance"], t[0]))[0]

    def passes_on(cid, s):
        it = items_on(members[cid], base, consts, s)
        return _form2(it) and it["g_ok"]
    pb, pg = best("bks"), best("goat")
    if pb is None or pg is None:
        return {"pick": None, "passes": False, "bks_pick": pb, "goat_pick": pg}
    if pb == pg:
        return {"pick": pb, "passes": passes_on(pb, "goat") and passes_on(pb, "bks"), "bks_pick": pb, "goat_pick": pg}
    nearer = min((pb, pg), key=lambda cid: (members[cid]["distance"], cid))
    return {"pick": nearer, "passes": passes_on(nearer, "bks") and passes_on(nearer, "goat"), "bks_pick": pb,
            "goat_pick": pg}


def select_rule(cands, base, consts):
    """(Pure.) The selection rule (amendment section 3 with review amendments 1, 3 and 5): per candidate the items on
    the 40, item 4 (shipped, or its family's cross-set pick that passes), item 5 (no real-DI harm), item 6 (it
    repeats); the qualifiers; the pick (lowest g; ties no download first, then a usable licence, then by id).
    cands: {cid: {kind, family, distance, shipped, counts, labels, real_worse, repeats, licence}}. -> dict."""
    fams = {}
    for cid, c in cands.items():
        if not c["shipped"]:
            fams.setdefault(c["family"], {})[cid] = c
    picks = {f: family_pick(ms, base, consts) for f, ms in fams.items()}
    rows = {}
    for cid, c in cands.items():
        it = items_on(c, base, consts, "deciding")
        if c["shipped"]:
            i4 = True
        else:
            fp = picks[c["family"]]
            i4 = fp["pick"] == cid and fp["passes"]
        i123 = _form2(it) and it["g_ok"]
        rows[cid] = dict(it, item4=i4, item5=not c["real_worse"], item6=bool(c["repeats"]),
                         decided_better=i123 and i4 and bool(c["repeats"]),
                         qualifies=i123 and i4 and not c["real_worse"] and bool(c["repeats"]),
                         harm=i123 and i4 and c["real_worse"],
                         better_by_mean=it["g"] is not None and it["g"] < 0 and it["extra_rate"])
    qual = sorted(cid for cid, r in rows.items() if r["qualifies"])

    def tie(cid):
        c = cands[cid]
        return (rows[cid]["g"], c["kind"] != "setting",
                (c.get("licence") or {}).get("product_status") != PRODUCT_USABLE, cid)
    pick = min(qual, key=tie) if qual else None
    return {"rows": rows, "families": picks, "qualifiers": qual, "pick": pick,
            "pick_kind": cands[pick]["kind"] if pick else None}


RX_P2B_NEXT = {   # the codes unchanged; their inputs and next steps under this rule (amendment 1's order)
    "RX-transcriber": "to the user with the licence table and the xr-cand row",
    "RX-setting": "to the user with the xr-cand row",
    "RX-harm": "reported; not priced",
    "RX-undecided": "no priced row; to the user with each candidate's g",
    "RX-none": "Basic Pitch as frozen stays; to the user",
}


def rx_p2b(sel):
    """(Pure.) The RX code by the pick's kind (review amendment 1): transcriber, setting, harm, undecided, none.
    RX-undecided is "some candidate better by the mean (g < 0 with item 1), none qualifies"."""
    rows = sel["rows"]
    if sel["pick"] is not None:
        code = "RX-transcriber" if sel["pick_kind"] == "transcriber" else "RX-setting"
    elif any(r["harm"] for r in rows.values()):
        code = "RX-harm"
    elif any(r["better_by_mean"] for r in rows.values()):
        code = "RX-undecided"
    else:
        code = "RX-none"
    return {"code": code, "next": RX_P2B_NEXT[code], "pick": sel["pick"]}


def refusal_sensitive_p2b(sel_itt, sel_pass):
    """(Pure.) Amendment 4: with passing-only E, M and h recomputed together, "refusal-sensitive" when the set of
    qualifiers (or the pick) changes."""
    changed = sel_itt["qualifiers"] != sel_pass["qualifiers"] or sel_itt["pick"] != sel_pass["pick"]
    return {"label": S.REFUSAL_SENSITIVE if changed else None, "qualifiers_itt": sel_itt["qualifiers"],
            "qualifiers_passing": sel_pass["qualifiers"], "pick_itt": sel_itt["pick"], "pick_passing": sel_pass["pick"]}


# --- Phase 2b: the priced row's table (pure) ------------------------------------------------------------------------------

XP_TABLE = (    # (code, when (the first that holds), meaning, next)
    ("XP-stop", "a build proof fails, a zero distance on a deciding setting, or a label is missing",
     "nothing is read", "to the orchestrator"),
    ("XP-anomaly", "L reads 'better'", "a transcriber's list beats the exact list", "audited before anything is said"),
    ("XP-closes", "P passes and L matches", "the candidate removes the shown reading cost",
     "to the user with the licence question and the stem-notes step"),
    ("XP-gain", "P passes, L not matching", "{gain_words}", "to the user with the licence question"),
    ("XP-worse", "P reads 'worse' (paired_reading at its defaults)",
     "it lands further than Basic Pitch's re-read; the prediction failed",
     "not adopted; reported with g; no second row without an amendment"),
    ("XP-undecided", "anything else", "not decided; undecided is not failed", "to the user with P's interval beside g"),
)
XP_CODES = tuple(c for c, *_ in XP_TABLE)


def xp_table_guard():
    if XP_CODES != ("XP-stop", "XP-anomaly", "XP-closes", "XP-gain", "XP-worse", "XP-undecided"):
        raise SystemExit("XP_TABLE's codes are not the six declared, in order")


def xp_labels(p_iv, l_iv):
    """(Pure.) P by `number_reading` (a gain) and `paired_reading` (its "worse", amendment 6); L by `paired_reading`;
    all at their defaults."""
    return {"P_number": S.number_reading(p_iv), "P": (SN.paired_reading(p_iv) or {}).get("reading"),
            "L": (SN.paired_reading(l_iv) or {}).get("reading")}


def xp_code(labels, stop=False):
    """(Pure.) XP_TABLE's code, the first that holds (amendment 6: XP-closes only when L matches; with L undecided
    the gain is shown and the remaining cost not decided)."""
    pn, pp, ll = labels.get("P_number"), labels.get("P"), labels.get("L")
    if stop or pn is None or pp is None or ll is None:
        code = "XP-stop"
    elif ll == "better":
        code = "XP-anomaly"
    elif pn == "passes" and ll == "matches":
        code = "XP-closes"
    elif pn == "passes":
        code = "XP-gain"
    elif pp == "worse":
        code = "XP-worse"
    else:
        code = "XP-undecided"
    row = next(r for r in XP_TABLE if r[0] == code)
    words = row[2].format(gain_words=("a shown gain; reading still costs L" if ll == "worse" else
                                      "gain shown; the remaining cost not decided"))
    return {"code": code, "when": row[1], "meaning": words, "next": row[3]}


def xp_read(itt, passing):
    """(Pure.) S1, as for xr-matched: intent-to-treat decides, passing-only beside, "refusal-sensitive" when the codes
    differ."""
    code = xp_code(xp_labels(itt.get("P"), itt.get("L")))
    pc = None
    if passing is not None:
        ok = passing.get("P") is not None and passing.get("L") is not None
        pc = S.passing_code(lambda: xp_code(xp_labels(passing["P"], passing["L"])), ok)
    return {"itt": code, "passing_only": pc, "label": S.refusal_label(code["code"], (pc or {}).get("code"))}


# --- Phase 2b: paths -------------------------------------------------------------------------------------------------------

def tx_path(kind, cand=None, iid=None, root=None):
    """Phase 2b's files, under PF/fs/readerr/: notes-tx/inputs/<input>/ (built whole in notes-tx/partial/ and moved),
    notes-tx.json; score-tx/inputs/<input>.json, candidates-tx.json; select.json; tools-gate.json; the timing
    sidecars under tx-notes/timing/ and tx-score/timing/."""
    r = readerr_dir()
    folder = pathlib.Path(root) if root is not None else r / "notes-tx" / "inputs" / str(iid)
    if kind == "input-dir":
        return folder
    if kind == "cand":
        return folder / f"{cand}.json"
    if kind == "raw":
        return folder / f"raw-{cand}.json"
    if kind == "notes-input":
        return folder / "summary.json"
    if kind == "partial":
        return r / "notes-tx" / "partial"
    if kind == "listing":
        return r / "notes-tx.json"
    if kind == "score-input":
        return r / "score-tx" / "inputs" / f"{iid}.json"
    if kind == "candidates":
        return r / "candidates-tx.json"
    if kind == "select":
        return r / "select.json"
    if kind == "gate":
        return r / "tools-gate.json"
    raise ValueError(kind)


def tx_staging(iid):
    """A fresh partial folder for one input's transcriber notes (never read; never blocks a rerun)."""
    import tempfile

    partial = tx_path("partial")
    partial.mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(prefix=f"{iid}-", dir=partial))


def tx_done(kind):
    if kind == "notes":
        d = readerr_dir() / "notes-tx" / "inputs"
        return {x.name for x in d.iterdir() if (x / "summary.json").exists()} if d.exists() else set()
    d = readerr_dir() / "score-tx" / "inputs"
    return {x.stem for x in d.glob("*.json")} if d.exists() else set()


def require_hashed(m, key, path):
    """A file whose sha256 must be main's `key` (a {sha256, counts} body). -> its JSON."""
    return NT.require_file_hash(m, key, path)


# --- Phase 2b: the tools gate (the transcriber runs; zero renders) ---------------------------------------------------------

def run_tx(fam, spec, jobs, work, threads=TX_THREADS):
    """One transcriber family's runner call in its own venv (unit F's `venv_python`), offline (`runner_env`), at most
    2 threads, on [(tag, wav)] in one process (the model loaded once). -> {tag: record}, each `runner_refusal`-checked."""
    import os

    from learn import readerr_tools as RT

    pairs = [(wav, pathlib.Path(work) / f"{fam}-{tag}.json") for tag, wav in jobs]
    env = runner_env(os.environ, True)
    env.update({k: str(threads) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")})
    mode = TX_FAMILIES[fam]["mode"]
    r = subprocess.run(runner_argv(RT.venv_python(TX_FAMILIES[fam]["lock"]), mode, spec, pairs), capture_output=True,
                       text=True, env=env)
    if r.returncode:
        raise SystemExit(f"readerr_run {mode} ({fam}) failed: {r.stderr.strip()[-400:]}")
    out = {}
    for (tag, wav), (_, o) in zip(jobs, pairs):
        rec = json.loads(pathlib.Path(o).read_text())
        why = runner_refusal(rec, mode, spec, file_sha(wav))
        if why:
            raise SystemExit(f"{fam} {tag}: {why}")
        out[tag] = rec
    return out


def record_events(rec):
    """(Pure.) A torch record's every read: {options as JSON: events}, the top-level read under "top"."""
    out = {"top": rec["events"]}
    for g in rec.get("grid") or []:
        key = json.dumps(g["options"], sort_keys=True)
        out[key] = g["events"]
    return out


def repeat_holds(runs):
    """(Pure.) Gate item 5: every run's reads, input by input, identical. runs: [{tag: record}]."""
    if not runs:
        return False
    first = {t: record_events(r) for t, r in runs[0].items()}
    return all({t: record_events(r) for t, r in run.items()} == first for run in runs[1:])


def runner_report(rec):
    """(Pure.) What the runner reports beyond the contract: #641's `scan`, `load_report` and `guards`, and anything
    else it adds (never refused as unknown)."""
    return {k: v for k, v in rec.items() if k not in RECORD_KEYS + ("grid",)}


def cmd_tx_gate(args):
    """The tools gate (zero renders), once, before any transcriber candidate is read: per family, the pinned
    checkpoint (unit F's `checkpoint_path`) hashed; the runner (unit D's mode, through `run_tx`) run on 4 bench inputs
    three times (two in one process, one fresh): identical reads, or the candidate cannot be priced; timed on 3 bench
    inputs at 1 and at 2 threads, with the projection for every input; D's scan, load and key report as the runner
    gives it; the licence record (unit F's `licence_record`). -> tools-gate.json, hashed as phase_scratch_readerr_tools
    before `tx-notes`."""
    m = require_readerr(PHASE_FROZEN, PHASE_P2, PHASE_P2B, PHASE_XR_OUTCOME)
    path = tx_path("gate")
    NT.never_overwrite(path)
    import tempfile

    from learn import readerr_tools as RT

    man = RT.load_manifest()
    tr = require_trace(m)
    bench = bench_inputs(tr)
    mr, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    real, _ = real_inputs(mr, NT.install_pair(NT.load_manifest()))
    n_inputs = len(bench) + len(real)
    ids = sorted(bench)
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2B}", "renders": 0, "families": {},
           "manifest_keys": sorted(man) if isinstance(man, dict) else None}
    for fam in TX_FAMILIES:
        ck = pathlib.Path(RT.checkpoint_path(fam))
        if not ck.exists():
            raise SystemExit(f"{fam}: no checkpoint at its pinned path (tx-fetch first)")
        sha = file_sha(ck)
        allow = tx_allow_globals(man, fam)
        spec = tx_spec(fam, ck, sha, allow)
        rep_jobs = [(i, bench[i][1]) for i in ids[:GATE_REPEAT_PARTS]]
        with tempfile.TemporaryDirectory(prefix=f"readerr-gate-{fam}-") as work:
            one = run_tx(fam, spec, [(f"{t}-a", w) for t, w in rep_jobs] + [(f"{t}-b", w) for t, w in rep_jobs], work)
            fresh = run_tx(fam, spec, [(f"{t}-f", w) for t, w in rep_jobs], work)
            runs = [{t: one[f"{t}-a"] for t, _ in rep_jobs}, {t: one[f"{t}-b"] for t, _ in rep_jobs},
                    {t: fresh[f"{t}-f"] for t, _ in rep_jobs}]
            timing = {}
            for th in (1, 2):
                t0 = time.time()
                recs = run_tx(fam, tx_spec(fam, ck, sha, allow, threads=th), [(f"{i}-t{th}", bench[i][1]) for i in
                                                                        ids[:GATE_TIMING_PARTS]], work, threads=th)
                wall = time.time() - t0
                timing[str(th)] = {"wall_s": round(wall, 1), "per_input_s": round(wall / GATE_TIMING_PARTS, 2),
                                   "runner_seconds": [r["seconds"] for r in recs.values()],
                                   "projection_s": round(wall / GATE_TIMING_PARTS * n_inputs, 0)}
        first = fresh[f"{ids[0]}-f"]
        out["families"][fam] = {"checkpoint_sha256": sha, "allow_globals": allow,
                                "scan": first.get("scan"), "load_report": first.get("load_report"),
                                "guards": first.get("guards"), "lock": TX_FAMILIES[fam]["lock"], "spec_options":
                                spec["options"], "grid": spec["grid"], "repeats": repeat_holds(runs),
                                "timing": timing, "inputs": n_inputs,
                                "runner_report": runner_report(fresh[f"{ids[0]}-f"]),
                                "versions": fresh[f"{ids[0]}-f"]["versions"], "licence": RT.licence_record(fam)}
        print(f"{fam}: repeats {out['families'][fam]['repeats']}; per input {timing['1']['per_input_s']} s at 1 thread, "
              f"{timing['2']['per_input_s']} s at 2; projection {timing['1']['projection_s']:.0f} s for {n_inputs} "
              "inputs", flush=True)
    sha = write_once(path, out)
    print(f"RX TX-GATE: {len(out['families'])} families; sha256 {sha} (into the ledger as {PHASE_TOOLS})")


def require_gate(m):
    g = require_hashed(m, PHASE_TOOLS, tx_path("gate"))
    for fam in TX_FAMILIES:
        if fam not in g["families"]:
            raise SystemExit(f"tools-gate.json has no {fam}")
    return g


def checkpoint_for(fam, gate):
    """The family's checkpoint at its pinned path, refused unless its sha256 is the gate's (hashed on main)."""
    from learn import readerr_tools as RT

    ck = pathlib.Path(RT.checkpoint_path(fam))
    if file_sha(ck) != gate["families"][fam]["checkpoint_sha256"]:
        raise SystemExit(f"{fam}: the checkpoint is not the gate's")
    return ck


# --- Phase 2b: tx-notes (zero renders) --------------------------------------------------------------------------------------

def tx_candidates_from(fam, rec):
    """(Pure.) One family's candidate events from its record: {tx id: events}, one per declared option set."""
    out = {}
    for g in rec["grid"]:
        out[tx_id(fam, g["options"])] = [dict(e) for e in g["events"]]
    return out


def cmd_tx_notes(args):
    """Phase 2b's `tx-notes` (zero renders), a shard at a time (`--shard k/n`, `--first n`): per family one runner
    call on the shard's inputs (the same 136 stored inputs as Phase 2a; the real-DI inputs through `real_di_source`),
    the checkpoint the gate's; per input, every candidate's events, the raw reads and a summary, built whole in a
    partial folder and moved into notes-tx/inputs/<input>/. `--combine`: every input done, then notes-tx.json, hashed
    as phase_scratch_readerr_notes_tx before `tx-score`."""
    m = require_readerr(PHASE_FROZEN, PHASE_P2, PHASE_P2B, PHASE_TOOLS)
    gate = require_gate(m)
    tr = require_trace(m)
    mr, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    bench = bench_inputs(tr)
    real, _ = real_inputs(mr, NT.install_pair(NT.load_manifest()))
    ids = sorted(bench) + sorted(real)
    if getattr(args, "combine", False):
        return tx_notes_combine(ids, gate)
    done = tx_done("notes")
    todo = [i for i in select(ids, args.shard, getattr(args, "first", 0)) if i not in done]
    if not todo:
        print("RX TX-NOTES: nothing to do in this shard")
        return
    import tempfile

    wav_of = {i: (bench[i][1] if i in bench else real[i][1]) for i in todo}
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="readerr-tx-notes-") as work:
        recs = {}
        for fam in TX_FAMILIES:
            ck = checkpoint_for(fam, gate)
            recs[fam] = run_tx(fam, tx_spec(fam, ck, gate["families"][fam]["checkpoint_sha256"],
                                            gate["families"][fam]["allow_globals"]),
                               [(i, wav_of[i]) for i in todo], work)
        for i in todo:
            staging = tx_staging(i)
            shas = {}
            for fam in TX_FAMILIES:
                for c, ev in sorted(tx_candidates_from(fam, recs[fam][i]).items()):
                    shas[c] = write_once(tx_path("cand", c, i, root=staging), {"input": i, "candidate": c, "events": ev})
            raw = {fam: write_once(tx_path("raw", fam, i, root=staging), recs[fam][i]) for fam in TX_FAMILIES}
            write_once(tx_path("notes-input", iid=i, root=staging), {
                "plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2B}", "input": i, "input_sha256": file_sha(wav_of[i]),
                "candidates": shas, "raw": raw})
            move_into_place(staging, tx_path("input-dir", iid=i))
    write_timing("tx-notes", args.shard, {"inputs": todo, "seconds": round(time.time() - t0, 1)})
    print(f"RX TX-NOTES shard {args.shard[0]}/{args.shard[1]}: {len(todo)} inputs in {time.time() - t0:.0f} s")


def tx_notes_combine(ids, gate):
    path = tx_path("listing")
    NT.never_overwrite(path)
    why = coverage_refusal(ids, tx_done("notes"))
    if why:
        raise SystemExit(why)
    cands = sorted(tx_candidates())
    inputs = {}
    for i in ids:
        sp = tx_path("notes-input", iid=i)
        s = json.loads(sp.read_text())
        if sorted(s["candidates"]) != cands:
            raise SystemExit(f"{i}: not the {len(cands)} transcriber candidates")
        for c, sha in s["candidates"].items():
            if file_sha(tx_path("cand", c, i)) != sha:
                raise SystemExit(f"{i} {c}: the file changed since `tx-notes`")
        inputs[i] = {"summary_sha256": file_sha(sp), "input_sha256": s["input_sha256"]}
    body = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2B}", "renders": 0, "candidates": cands,
            "gate_checkpoints": {f: v["checkpoint_sha256"] for f, v in gate["families"].items()}, "inputs": inputs,
            "counts": {"inputs": len(ids), "candidates": len(cands)}}
    sha = write_once(path, body)
    print(f"RX TX-NOTES COMBINE: {len(ids)} inputs, {len(cands)} candidates; sha256 {sha} (into the ledger as "
          f"{PHASE_NOTES_TX} before `tx-score`)")


def load_tx_candidate(listing, iid, cand):
    sp = tx_path("notes-input", iid=iid)
    if file_sha(sp) != listing["inputs"][iid]["summary_sha256"]:
        raise SystemExit(f"{iid}: the transcriber summary is not the hashed listing's")
    s = json.loads(sp.read_text())
    p = tx_path("cand", cand, iid)
    if file_sha(p) != s["candidates"][cand]:
        raise SystemExit(f"{iid} {cand}: not the listed file")
    return json.loads(p.read_text())["events"]


# --- Phase 2b: tx-score (zero renders) ---------------------------------------------------------------------------------------

def with_bp(notes, base_notes):
    """(Pure.) The `+bp` list: the candidate's own notes after its timing, each borrowing loudness and bends from its
    paired Basic Pitch note of the stored re-read after F1 (`note_tx.ms_with_bp`); F1 is not applied again."""
    out, _ = TX.ms_with_bp(notes, base_notes)
    return out


def figures_p2b(an, truth, notes, length_s):
    """(Pure.) The note figures and amendment 3's onset error (the matched notes' median |onset error|, ms, as
    played)."""
    return dict(note_figures(an, truth, notes, length_s), onset_error=an["onset_ms_after_snap"]["median_abs"])


def tx_lists(listing, iid, events_base, di, fixes, L, pre_s, base_fixed):
    """Every transcriber candidate's two lists for one input: as read (`scored_list`) and its `+bp` variant
    (`with_bp` on the same timing). -> {id: (notes, presnap, lost)}."""
    out = {}
    for c in tx_candidates():
        notes, pre, lost = scored_list(load_tx_candidate(listing, iid, c), di, fixes, L, pre_s)
        out[c] = (notes, pre, lost)
        out[c + BP_SUFFIX] = (with_bp(notes, base_fixed), pre, lost)
    return out


def cmd_tx_score(args):
    """Phase 2b's `tx-score` (zero renders), a shard at a time: per bench part the base (the stored re-read), the 26
    transcriber candidates as read and as `+bp`, each with the 23 note figures, the onset error and the rebuilt
    guitar's logmel, env_corr and pause error (one rebuild per distinct list); and, for select, every Phase 2a
    candidate's as-played counts and onset error recomputed from its hashed notes (no rebuild). Per real-DI input,
    the note figures only. `--combine`: RX-stop unless the base's rebuilt figures equal build.json's on 47 of 47 and
    the recomputed Phase 2a counts give candidates.json's frontier exactly; then candidates-tx.json: the paired reads
    (the 40, BKS, GOAT, all 47), the frontier, the real-DI arm, the counts by set, the licence fields. Descriptive;
    no RX code."""
    m = require_readerr(PHASE_FROZEN, PHASE_P2, PHASE_P2B, PHASE_TOOLS, PHASE_NOTES_TX, PHASE_NOTES_KEY,
                        PHASE_CANDIDATES)
    listing = require_hashed(m, PHASE_NOTES_TX, tx_path("listing"))
    listing2a = NT.require_file_hash(m, PHASE_NOTES_KEY, p2a_path("listing"))
    tr = require_trace(m)
    xb = SX.require_xbuild(m)
    mr, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    ids = sorted(listing["inputs"])
    if getattr(args, "combine", False):
        return tx_score_combine(m, ids, xb, listing2a)
    import numpy as np

    from learn import song_bank as SB

    b2 = SX.bank_build(m)
    pair = NT.install_pair(NT.load_manifest())
    rule = ((mr.get(NR.LEDGER_ID) or {}).get(NF.PHASE_F6_FROZEN) or {}).get("rule")
    if not rule or not rule.get("F6"):
        raise SystemExit(f"no {NF.PHASE_F6_FROZEN} rule on main")
    fixes = tr["fixes"]
    f6_fixes = dict(fixes, F6=rule["F6"])
    excl, _, _, _ = NT._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    finish_of = {key: fin for kind, key, _i, _r, _d, fin in NT.build_todo(pair, NT.ear_items_file(BUILD2))
                 if kind == "part"}
    bench = bench_inputs(tr)
    real, truth_listing = real_inputs(mr, pair)
    ta = None
    done = tx_done("score")
    todo = [i for i in select(ids, args.shard, getattr(args, "first", 0)) if i not in done]
    t0, seconds = time.time(), {}
    for i in todo:
        t1 = time.time()
        if kind_of(i) == "bench":
            key, _w, rec = bench[i]
            row = tr["parts"][key]
            bank64 = np.asarray(NT.load_dry(BANK_ARM, key, b2), np.float64)
            L = len(bank64) / NR.SR
            truth = row["played"]
            base = scored_list(rec["events"], bank64, fixes, L)
            if base[0] != row["reread"]:
                raise SystemExit(f"{i}: the base is not trace.json's re-read")
            lists = dict({BASE: base}, **tx_lists(listing, i, rec["events"], bank64, fixes, L, 0.0, base[0]))
            cache, res = {}, {}
            for c, (notes, pre, lost) in lists.items():
                an = anatomy(truth, notes, pre, lost)
                ck = json.dumps(notes, sort_keys=True)
                if ck not in cache:
                    y, _ = NR.rebuild_redo(BANK_ARM, notes, len(bank64), bank, bank64, tr["ring_variant"],
                                           finish=finish_of[key], loud=None)
                    fig = NR.figures(bank64, np.asarray(np.asarray(y, np.float32), np.float64))
                    cache[ck] = {"logmel": fig["logmel"], "env_corr": fig["env_corr"],
                                 "pause_error": pause_error(fig), "mask": fig["mask"]}
                dry = cache[ck]
                res[c] = {"figures": dict(figures_p2b(an, truth, notes, L), logmel=dry["logmel"],
                                          env_corr=dry["env_corr"], pause_error=dry["pause_error"]),
                          "counts": counts_of(an)}
                if c == BASE:
                    res[c]["stored_check"] = {"logmel": dry["logmel"], "env_corr": dry["env_corr"],
                                              "mask": {str(n): v for n, v in dry["mask"].items()}}
            p2a = {}
            for c in candidate_ids():
                ev = rec["events"] if c == F6_ID else load_candidate(listing2a, i, c)
                notes, pre, lost = scored_list(ev, bank64, f6_fixes if c == F6_ID else fixes, L)
                an = anatomy(truth, notes, pre, lost)
                p2a[c] = {"counts": counts_of(an), "onset_error": an["onset_ms_after_snap"]["median_abs"]}
            body = {"input": i, "part": key, "kind": "bench", "candidates": res, "phase2a": p2a,
                    "rebuilds": len(cache)}
        else:
            _source, _w, events, meta = real[i]
            if kind_of(i) == "truth":
                ta = ta or NT.TruthAudio(truth_listing)
                di, _, _, truth = ta.window(meta["window"])
            else:
                nm = i.split("-", 1)[1]
                di = SB.measure(NT.known_audio(nm, bank))
                truth = [dict(n) for n in NT.KNOWN_NOTES[nm]]
            L = len(di) / NR.SR
            base = scored_list(events, di, fixes, L, meta["pre_s"])
            lists = dict({BASE: base}, **tx_lists(listing, i, events, di, fixes, L, meta["pre_s"], base[0]))
            res = {}
            for c, (notes, pre, lost) in lists.items():
                an = anatomy(truth, notes, pre, lost)
                res[c] = {"figures": figures_p2b(an, truth, notes, L), "counts": counts_of(an)}
            body = {"input": i, "kind": kind_of(i), "group": meta["group"], "kind_of_window": meta["kind"],
                    "cluster": meta["cluster"], "candidates": res}
        body.update(plan=PLAN, listing_sha256=file_sha(tx_path("listing")))
        write_once(tx_path("score-input", iid=i), body)
        seconds[i] = round(time.time() - t1, 1)
        print(f"{i}: {len(body['candidates'])} lists scored in {seconds[i]} s", flush=True)
    write_timing("tx-score", args.shard, {"inputs": todo, "seconds_per_input": seconds,
                                           "seconds": round(time.time() - t0, 1)})
    print(f"RX TX-SCORE shard {args.shard[0]}/{args.shard[1]}: {len(todo)} inputs in {time.time() - t0:.0f} s")


def counts_by_set(per_part, sets_of, cands):
    """(Pure.) Per candidate the as-played extras and misses pooled on the 40 ("deciding"), BKS and GOAT.
    per_part: {pkey: {cand: counts}}."""
    out = {}
    for c in cands:
        out[c] = {}
        for s in SELECT_SETS:
            ks = [k for k in per_part if (sets_of[k] in DECIDING if s == "deciding" else sets_of[k] == s)]
            cs = [per_part[k][c] for k in ks if c in per_part[k]]
            out[c][s] = {"extras": sum(sum(x["extras"].values()) for x in cs),
                         "misses": sum(sum(x["misses"].values()) for x in cs), "parts": len(cs)}
    return out


def frontier_equal_refusal(recomputed, stored):
    """(Pure.) RX-stop unless the Phase 2a counts recomputed here give candidates.json's bench frontier exactly."""
    bad = sorted(c for c in stored if c in recomputed and recomputed[c] != stored[c])
    miss = sorted(set(stored) - set(recomputed))
    if bad or miss:
        return f"RX-stop: the recomputed Phase 2a counts differ from candidates.json's frontier on {len(bad) + len(miss)}"
    return None


def tx_score_combine(m, ids, xb, listing2a):
    from learn import readerr_tools as RT

    path = tx_path("candidates")
    NT.never_overwrite(path)
    why = coverage_refusal(ids, tx_done("score"))
    if why:
        raise SystemExit(why)
    lsha = file_sha(tx_path("listing"))
    rows = {i: json.loads(tx_path("score-input", iid=i).read_text()) for i in ids}
    if any(r["listing_sha256"] != lsha for r in rows.values()):
        raise SystemExit("a score file was made from another listing")
    per_part = {r["part"]: r["candidates"] for r in rows.values() if r["kind"] == "bench"}
    why = stored_point_refusal(per_part, xb["parts"])
    if why:
        raise SystemExit(why)
    c2a = require_hashed(m, PHASE_CANDIDATES, p2a_path("candidates"))
    p2a_counts = {r["part"]: {c: v["counts"] for c, v in r["phase2a"].items()} for r in rows.values()
                  if r["kind"] == "bench"}
    re_front = frontier({k: {c: {"counts": v} for c, v in cs.items()} for k, cs in p2a_counts.items()},
                        candidate_ids())
    why = frontier_equal_refusal({c: v for c, v in re_front.items() if c != BASE},
                                 {c: v for c, v in c2a["frontier"]["bench"].items() if c != BASE})
    if why:
        raise SystemExit(why)
    draw, sd = SX.context()
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    txc = sorted(c for c in rows[ids[0]]["candidates"] if c != BASE)

    def rows_of(vals):
        return _rows(sd, draw, vals)
    real_rows = [{"group": r["group"], "kind": r["kind_of_window"], "cluster": r["cluster"], "iid": i,
                  "figures": {c: v["figures"] for c, v in r["candidates"].items()}}
                 for i, r in rows.items() if r["kind"] != "bench"]
    onset_2a = {}
    for c in candidate_ids():
        d = {k: r["phase2a"][c]["onset_error"] - r["candidates"][BASE]["figures"]["onset_error"]
             for k, r in ((rr["part"], rr) for rr in rows.values() if rr["kind"] == "bench")
             if r["phase2a"][c]["onset_error"] is not None and r["candidates"][BASE]["figures"]["onset_error"] is not None}
        rr_ = rows_of(d) if d else None
        onset_2a[c] = {"parts": len(d), "rows": rr_, "label": sign_label((rr_ or {}).get("bks_goat"), "error"),
                       "words": P2A_LABEL}
    paired = {}
    for c in txc:
        pr = paired_reads(per_part, c, rows_of)
        d = {}
        for k, r in per_part.items():
            a, b = r[c]["figures"].get(ONSET_ERROR), r[BASE]["figures"].get(ONSET_ERROR)
            if a is not None and b is not None:
                d[k] = a - b
        rr_ = rows_of(d) if d else None
        pr[ONSET_ERROR] = {"parts": len(d), "rows": rr_, "label": sign_label((rr_ or {}).get("bks_goat"), "error"),
                           "words": P2A_LABEL}
        paired[c] = pr
    base_counts = counts_by_set({k: {BASE: v[BASE]["counts"]} for k, v in per_part.items()}, sets_of, [BASE])[BASE]
    body = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2B}", "renders": 0, "words": P2A_LABEL, "rx_code": None,
            "listing_sha256": lsha, "candidates_2a_sha256": file_sha(p2a_path("candidates")), "candidates": txc,
            "paired": paired, "onset_error_2a": onset_2a,
            "frontier": {"bench": frontier(per_part, txc)},
            "real": {c: real_reads(real_rows, c) for c in txc},
            "counts_by_set": dict(counts_by_set({k: {c: v[c]["counts"] for c in [BASE] + txc}
                                                 for k, v in per_part.items()}, sets_of, [BASE] + txc),
                                  **counts_by_set(p2a_counts, sets_of, candidate_ids())),
            "base_counts": base_counts,
            "licence": {f: RT.licence_record(f) for f in TX_FAMILIES},
            "rebuilds": sum(r.get("rebuilds", 0) for r in rows.values() if r["kind"] == "bench"),
            "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    sha = write_once(path, body)
    print(f"RX TX-SCORE COMBINE: {len(per_part)} parts, {len(real_rows)} real-DI inputs, {len(txc)} lists; base "
          f"on the 40 {base_counts['deciding']}; {P2A_LABEL}; sha256 {sha} (into the ledger as {PHASE_CANDIDATES_TX})")


# --- Phase 2b: select (zero renders) ---------------------------------------------------------------------------------------

def labels_from(paired, onset):
    """(Pure.) A candidate's item labels by set from its paired reads: {set: {figure: reading}}."""
    out = {}
    for s, key in (("deciding", "bks_goat"), ("bks", "bks"), ("goat", "goat")):
        out[s] = {}
        for f in SELECT_ITEMS:
            src = onset if f == ONSET_ERROR else (paired or {}).get(f)
            rows = (src or {}).get("rows") or {}
            iv = rows.get(key)
            if s != "deciding" and iv and iv.get("mean") is None:
                iv = None
            out[s][f] = (sign_label(iv, ORIENTATION.get(f, "error")) or {}).get("reading")
    return out


def real_worse_of(real):
    """(Pure.) Item 5: on P1, P2 or the lists, extra_rate or miss_rate reads "worse" against Basic Pitch."""
    for g in ("P1", "P2", "lists"):
        for f in ("extra_rate", "miss_rate"):
            lab = ((((real or {}).get(g) or {}).get(f) or {}).get("label")) or {}
            if lab.get("reading") == "worse":
                return True
    return False


def select_inputs(c2a, ctx, gate):
    """(Pure.) Every selection candidate's record from the two hashed candidate files and the gate."""
    out = {}
    for cid in select_ids():
        fam = family_of(cid)
        if fam["kind"] == "setting":
            paired, onset, real, lic, rep = (c2a["paired"].get(cid), ctx["onset_error_2a"].get(cid),
                                             c2a["real"].get(cid), BP_LICENCE, True)
        else:
            paired, real = ctx["paired"].get(cid), ctx["real"].get(cid)
            onset = (paired or {}).get(ONSET_ERROR)
            lic, rep = ctx["licence"][fam["family"]], gate["families"][fam["family"]]["repeats"]
        out[cid] = dict(fam, counts=ctx["counts_by_set"][cid], labels=labels_from(paired, onset),
                        real_worse=real_worse_of(real), repeats=rep, licence=lic)
    return out


def cmd_select(_args):
    """`select` (zero renders), once: refused unless candidates.json and candidates-tx.json are hashed on main; the
    rule's constants from the hashed xr/rows.json; the rule (`select_rule`) on Phase 2a's candidates and every
    transcriber's `+bp` list; the RX code by the pick's kind (`rx_p2b`); beside, the full passing-only recompute
    (amendment 4) and its label, each candidate's g, end error, attack rates and dry figures, the shrunk arm's caveat
    and the licence fields. -> select.json; after an audit its code into phase_scratch_readerr_outcome."""
    m = require_readerr(PHASE_FROZEN, PHASE_P2, PHASE_P2B, PHASE_TOOLS, PHASE_CANDIDATES, PHASE_CANDIDATES_TX,
                        PHASE_XR_OUTCOME)
    path = tx_path("select")
    NT.never_overwrite(path)
    c2a = require_hashed(m, PHASE_CANDIDATES, p2a_path("candidates"))
    ctx = require_hashed(m, PHASE_CANDIDATES_TX, tx_path("candidates"))
    if ctx["candidates_2a_sha256"] != file_sha(p2a_path("candidates")):
        raise SystemExit("candidates-tx.json was made from another candidates.json")
    gate = require_gate(m)
    why = SX.field_refusal(m, PHASE_XR_OUTCOME, "rows_sha256", file_sha(xr_path("rows")))
    if why:
        raise SystemExit(why)
    rows = json.loads(xr_path("rows").read_text())
    consts, consts_p = select_constants(rows, "itt"), select_constants(rows, "per")
    cands = select_inputs(c2a, ctx, gate)
    base = ctx["base_counts"]
    sel, sel_p = select_rule(cands, base, consts), select_rule(cands, base, consts_p)
    code = rx_p2b(sel)
    sens = refusal_sensitive_p2b(sel, sel_p)
    beside = {cid: {"g_passing": sel_p["rows"][cid]["g"],
                    "end_error": (c2a["paired"].get(cid) or ctx["paired"].get(cid) or {}).get("end_error", {}).get(
                        "label"),
                    "attacks": {f: (c2a["paired"].get(cid) or ctx["paired"].get(cid) or {}).get(f, {}).get("label")
                                for f in ("attack_miss_rate", "extra_attack_rate")},
                    "dry": {f: (c2a["paired"].get(cid) or ctx["paired"].get(cid) or {}).get(f, {}).get("label")
                            for f in DRY_P2A}} for cid in cands}
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2B}", "renders": 0,
           "rows_sha256": file_sha(xr_path("rows")), "candidates_sha256": file_sha(p2a_path("candidates")),
           "candidates_tx_sha256": file_sha(tx_path("candidates")), "constants": consts,
           "constants_passing": consts_p, "base_counts": base, "rule": sel, "code": code, "refusal": sens,
           "beside": beside, "licences": {cid: c["licence"] for cid, c in cands.items()},
           "shrunk_caveat": "E is not shown on the shrunk answer (passing-only -0.007 [-0.122, +0.109]): the predicted "
                            "gain is for the full answer only",
           "words": "g is a straight-line prediction from two measured slopes, never a reading; only a row decides",
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    sha = write_once(path, out)
    print(f"RX SELECT: {code['code']} (pick {code['pick']}); qualifiers {sel['qualifiers']}; passing-only "
          f"{sens['qualifiers_passing']} -> {sens['label']}; h {consts['h']:.4f}; sha256 {sha}")


# --- Phase 2b: the priced row xr-cand (renders only after the user's word) --------------------------------------------------

def require_cand_outcome(m):
    """main's RX outcome naming the priced candidate: RX-transcriber or RX-setting with its `candidate`."""
    rec = m.get(PHASE_OUTCOME) or {}
    if rec.get("code") not in ("RX-transcriber", "RX-setting") or rec.get("candidate") not in select_ids():
        raise SystemExit(f"main's {PHASE_OUTCOME} names no priced candidate (RX-transcriber or RX-setting with its "
                         "candidate)")
    return rec["candidate"]


def cand_list(cid, i, events, di, fixes, f6_fixes, L, pre_s, base_fixed, listing2a, listing_tx):
    """The priced candidate's list for one input, as tx-score or score made it."""
    fam = family_of(cid)
    if fam["kind"] == "setting":
        ev = events if cid == F6_ID else load_candidate(listing2a, i, cid)
        return scored_list(ev, di, f6_fixes if cid == F6_ID else fixes, L, pre_s)[0]
    plain = cid[:-len(BP_SUFFIX)]
    notes, _pre, _lost = scored_list(load_tx_candidate(listing_tx, i, plain), di, fixes, L, pre_s)
    return with_bp(notes, base_fixed)


def cmd_xr_build_cand(args):
    """xr-build --set cand (zero renders): refused unless main's phase_scratch_readerr_outcome names the candidate;
    per part the candidate's hashed list rebuilt as every xr- guitar. Four proofs before anything is written: (1) the
    stored re-read reproduces dry/xn-reread's sha256 on 47 of 47; (2) the candidate's note files equal the listing's
    (each load checks it); (3) the guitar's dry figures equal tx-score's (or score's) stored ones on 47 of 47; (4)
    CODE_FILES equal main's. -> xr/dry/xr-cand/, xr/build-cand.json, hashed as phase_scratch_readerr_xr_dry_cand."""
    m = require_readerr(PHASE_FROZEN, PHASE_P2, PHASE_P2B, PHASE_OUTCOME)
    cid = require_cand_outcome(m)
    out_p = xr_path("build", "cand")
    NT.never_overwrite(out_p)
    import numpy as np

    from analysis import aligned as A

    from learn import knob_ceiling as K

    tr = require_trace(m)
    xb = SX.require_xbuild(m)
    b2 = SX.bank_build(m)
    mr, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    rule = ((mr.get(NR.LEDGER_ID) or {}).get(NF.PHASE_F6_FROZEN) or {}).get("rule") or {}
    fixes = tr["fixes"]
    f6_fixes = dict(fixes, F6=rule.get("F6"))
    listing2a = NT.require_file_hash(m, PHASE_NOTES_KEY, p2a_path("listing"))
    kind = family_of(cid)["kind"]
    listing_tx = require_hashed(m, PHASE_NOTES_TX, tx_path("listing")) if kind == "transcriber" else None
    draw, _sd = SX.context()
    by = {p["pkey"]: p for p in draw["parts"]}
    pinned = pinned_identity()
    pair = NT.install_pair(NT.load_manifest())
    excl, _, _, _ = NT._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    finish_of = {key: fin for k_, key, _i, _r, _d, fin in NT.build_todo(pair, NT.ear_items_file(BUILD2)) if k_ == "part"}
    bench = bench_inputs(tr)
    lo, hi = SX._trim()
    t0 = time.time()
    built, bad = {}, {1: [], 3: []}
    for i, (key, _w, rec) in sorted(bench.items()):
        bank64 = np.asarray(NT.load_dry(BANK_ARM, key, b2), np.float64)
        L = len(bank64) / NR.SR
        base = scored_list(rec["events"], bank64, fixes, L)[0]

        def rebuild(notes):
            y, rep = NR.rebuild_redo(BANK_ARM, notes, len(bank64), bank, bank64, tr["ring_variant"],
                                     finish=finish_of[key], loud=None)
            return np.asarray(y, np.float32), rep
        if npy_bytes_sha(rebuild(base)[0]) != xb["parts"][key]["guitars"]["xn-reread"]["sha256"]:
            bad[1].append(key)
        notes = cand_list(cid, i, rec["events"], bank64, fixes, f6_fixes, L, 0.0, base, listing2a, listing_tx)
        y32, rep = rebuild(notes)
        y = np.asarray(y32, np.float64)
        figs = NR.figures(bank64, y)
        stored_p = (tx_path("score-input", iid=i) if kind == "transcriber" else p2a_path("score-input", iid=i))
        stored = json.loads(stored_p.read_text())["candidates"][cid]["figures"]
        if not (stored.get("logmel") == figs["logmel"] and stored.get("env_corr") == figs["env_corr"]
                and stored.get("pause_error") == pause_error(figs)):
            bad[3].append(key)
        pauses = {h: {str(n): float(NT.judge_pause_share(y[lo:hi], 0, h, n)) for n in A.FRAME_SIZES}
                  for h in K.R.HALVES}
        built[key] = {"y32": y32, "notes": len(notes), "report": rep, "figures": figs,
                      "pause_error": pause_error(figs), "pauses": pauses,
                      "identical_to": next((xn for xn in ("xn-reread", "xn-list")
                                            if xb["parts"][key]["guitars"][xn]["sha256"] == npy_bytes_sha(y32)), None)}
        print(f"{i}: proofs {'=' if key not in bad[1] else 'DIFFERS'} {'=' if key not in bad[3] else 'DIFFERS'}",
              flush=True)
    n = len(bench)
    proofs = {"reread_equal": n - len(bad[1]), "notes_listed": n, "figures_equal": n - len(bad[3]),
              "pinned": pinned, "parts": n}
    if any(bad.values()) or not all(pinned.values()):
        raise SystemExit(f"XP-stop: a build proof fails ({ {k: len(v) for k, v in bad.items()} }, pinned "
                         f"{sum(pinned.values())} of {len(pinned)}): nothing written; to the orchestrator")
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P2B}", "renders": 0, "set": "cand", "rows": ["xr-cand"],
           "candidate": cid, "proofs": proofs, "proofs_hold": True, "parts": {}}
    risk = []
    for key, g in built.items():
        y32 = g.pop("y32")
        g["sha256"], g["audio_sha256"] = npy_bytes_sha(y32), S.npy_sha(y32)
        g["file_sha256"] = write_once_npy(xr_path("dry", "xr-cand", key), y32)
        if g["file_sha256"] != g["sha256"]:
            raise SystemExit("xr-cand: the written guitar is not the one built")
        if max(g["pauses"][by[key]["search"]].values()) > 0.5:
            risk.append(key)
        out["parts"][key] = {"guitars": {"xr-cand": g}}
    out["refusal_risk"] = {"report": "parts whose search-half pause share would make J0 refuse; a report, not a stop",
                           "parts": [{"row": "xr-cand", "part": k} for k in risk]}
    out["seconds"] = round(time.time() - t0, 1)
    sha = write_once(out_p, out)
    print(f"XP BUILD cand ({cid}): proofs {proofs['reread_equal']}, {proofs['figures_equal']} of {n}, pinned "
          f"{sum(pinned.values())} of {len(pinned)}; J0 refusal risk on {len(risk)}; sha256 {sha} (into the ledger as "
          f"{xr_dry_key('cand')})")


def cmd_xr_read_cand(_args):
    """xr-read --row xr-cand (zero renders), once: per part on the answer arm (shrunk beside) P = G(xr-cand) -
    G(xn-reread) and L = G(xr-cand) - G(xn-list); S1 (intent-to-treat decides, passing-only beside); XP_TABLE's code;
    beside, P less its prediction g (select.json), G(xr-cand) - G(xr-matched), each set, the checkpoints. The rows
    before the code. -> xr/rows-cand.json, xr/report-cand.json."""
    row = "xr-cand"
    m = require_readerr(PHASE_FROZEN, PHASE_P2, PHASE_P2B, PHASE_OUTCOME, xr_dry_key("cand"), xr_answers_key(row),
                        xr_answers_key("xr-matched"))
    xp_table_guard()
    for p_ in (xr_path("rows", row), xr_path("report", row)):
        NT.never_overwrite(p_)
    require_xr_check(row)
    cid = require_cand_outcome(m)
    sel = json.loads(tx_path("select").read_text())
    draw, sd = SX.context()
    rn = {r: SX.row_numbers(m, draw, r) for r in ("xn-reread", "xn-list")}
    rn[row] = xr_row_numbers(m, draw, row)
    rn["xr-matched"] = xr_row_numbers(m, draw, "xr-matched")
    arms = {}
    for arm, f in SX.ARMS.items():
        d = {t: {"P": SX.paired(rn[row][t], rn["xn-reread"][t], f), "L": SX.paired(rn[row][t], rn["xn-list"][t], f),
                 "vs_matched": SX.paired(rn[row][t], rn["xr-matched"][t], f)} for t in ("itt", "per")}
        rows_ = {t: {n: _rows(sd, draw, v) for n, v in d[t].items()} for t in d}
        arms[arm] = {"rows": rows_, "read": xp_read({n: rows_["itt"][n]["bks_goat"] for n in ("P", "L")},
                                                    {n: rows_["per"][n]["bks_goat"] for n in ("P", "L")})}
    g = (sel["rule"]["rows"].get(cid) or {}).get("g")
    p_mean = ((arms["answer"]["rows"]["itt"]["P"]["bks_goat"]) or {}).get("mean")
    beside = {"candidate": cid, "g": g, "P_less_g": None if g is None or p_mean is None else p_mean - g,
              "checkpoints": {cp: {n: _rows(sd, draw, SX.paired(rn[row]["itt"], rn[o]["itt"], cp))["bks_goat"]
                                   for n, o in (("P", "xn-reread"), ("L", "xn-list"))}
                              for cp in ("G_cp50", "G_cp100", "G_cp200")}}
    out = {"plan": PLAN, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0, "row": row,
           "answers_sha256": {r: rn[r]["answers_sha256"] for r in rn}}
    write_once(xr_path("rows", row), dict(out, arms=arms, beside=beside))
    main_read = arms["answer"]["read"]
    code = main_read["itt"]
    write_once(xr_path("report", row), dict(out, arms=arms, beside=beside, xp=main_read, code=code["code"],
                                            shrunk=arms["shrunk"]["read"]["itt"]["code"],
                                            next=("to the user with both reads" if main_read["label"] else
                                                  code["next"])))
    r_ = arms["answer"]["rows"]["itt"]
    print(f"P on the 40 {r_['P']['bks_goat']}; L {r_['L']['bks_goat']}; g {g}")
    print(f"XP {code['code']}: {code['meaning']}. Next: {code['next']}; label {main_read['label']}")


# --- the RX read (after the xr- row; not built here) --------------------------------------------------------------------------

PHASE2_STUB = "the RX read waits for the xr- row's XH code and its own amendment"


def cmd_read(_args):
    require_readerr(PHASE_FROZEN)
    raise SystemExit(PHASE2_STUB)


COMMANDS = {"trace": cmd_trace, "anatomy": cmd_anatomy, "real-compare": cmd_real_compare,
            "screen-check": cmd_screen_check, "freeze": cmd_freeze, "notes": cmd_notes, "score": cmd_score_p2a,
            "read": cmd_read, "xr-build": cmd_xr_build, "xr-check": cmd_xr_check, "xr-search": cmd_xr_search,
            "xr-answers": cmd_xr_answers, "xr-score": cmd_xr_score, "xr-read": cmd_xr_read, "tx-gate": cmd_tx_gate,
            "tx-notes": cmd_tx_notes, "tx-score": cmd_tx_score, "select": cmd_select}
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
    ap.add_argument("--shard", type=parse_shard, default=(0, 1))
    ap.add_argument("--first", type=int, default=0, help="only this shard's first n parts or inputs (timing)")
    ap.add_argument("--combine", action="store_true", help="notes or score: gather every shard's files, once")
    ap.add_argument("--rerun", action="store_true",
                    help="search or score again, once, only the parts whose record refused (S1: then Cen)")
    args = ap.parse_args(argv)
    if args.cmd in NEEDS_ROW and not args.row:
        ap.error(f"{args.cmd} needs --row")
    if args.cmd in RENDER_COMMANDS and args.shard[1] > RENDER_SHARDS:
        ap.error(f"{args.cmd} renders: at most {RENDER_SHARDS} shards (render processes)")
    COMMANDS[args.cmd](args)


RENDER_COMMANDS = ("xr-check", "xr-search", "xr-score")
RENDER_SHARDS = 3                        # at most 3 render processes on the machine


def parse_shard(text):
    """`k/n` with 0 <= k < n. The render commands keep scratch_search's cap of 3 shards; notes and score take any n."""
    try:
        k, n = (int(x) for x in text.split("/"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r}: k/n")
    if not 0 <= k < n:
        raise argparse.ArgumentTypeError(f"{text!r}: 0 <= k < n")
    return k, n


if __name__ == "__main__":
    main()
