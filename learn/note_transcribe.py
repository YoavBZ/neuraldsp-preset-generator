"""The note rebuild's redo: notes transcribed from the DI by Basic Pitch, the content checks against the DI, and the
redo's dry guitars `tr-di` and `tr-plain` (`docs/note-rebuild-plan.md` section 12; ledger `note-rebuild`
`phase_nr_1_redo`, then `phase_nr_1_ear_old`, `phase_nr_1_redo_install`, `phase_nr_1_redo_notes`,
`phase_nr_1_redo_ear`; the row itself is `learn/scratch_notes.py`).

    $MAIN -m learn.note_transcribe set-aside      # step 2: stage 1's renders hashed and moved aside unread (0 renders)
    $MAIN -m learn.note_transcribe install        # step 3: the Basic Pitch venv from a hashed lock (a declared download)
    $MAIN -m learn.note_transcribe install-gate   # step 3: repeatable, the known notes, the timing
    $MAIN -m learn.note_transcribe calibrate      # step 3: the note checks on the 27 development windows, the checks'
                                                  #         test, the ring variant (0 renders)
    $MAIN -m learn.note_transcribe transcribe     # step 5: the 47 parts and the 8 ear items; the note checks
    $MAIN -m learn.note_transcribe build          # step 6: tr-di and tr-plain; the audio checks (0 renders)
    $MAIN -m learn.note_transcribe stem-preview   # step 6: Basic Pitch on each part's stem, search half (0 renders)
    $MAIN -m learn.note_transcribe clips          # step 8: the ear page's clips (52 renders)

The second amendment (note-rebuild-plan 12m, "measure first"; ledger `phase_nr_1_redo_calib_amend`), run in this
order before `calibrate`, each written once under redo/ and refused without `phase_nr_1_redo_calib_amend` (and, after
`truth`, `phase_nr_1_redo_truth`) on main:

    $MAIN -m learn.note_transcribe truth          # the Guitar-TECHS P1/P2 truth listing (its sha256 -> ledger first)
    $MAIN -m learn.note_transcribe attacks-report # the flux detector's report: P1 offset, recall overall and ringing
    $MAIN -m learn.note_transcribe ghost-ladder   # the distance's instrument check (a failing list stops)
    $MAIN -m learn.note_transcribe truth-report   # Basic Pitch on the truth and GOAT windows; precision, recall
    $MAIN -m learn.note_transcribe versions       # the note-versions read, once -> phase_nr_1_redo_versions

$MAIN is the main checkout's .venv python (in a worktree add `--data-dir ~/ndsp-presets` through the environment the
replay used). Every command refuses unless this checkout runs main's code (`redo_on_main`: `CODE_FILES`, the redo's
eleven modules from learn/scratch_search.py to learn/note_versions.py, equal main's, and the `phase_fs*`, `phase_scratch_notes*` and `phase_nr*` keys equal main's) and main's ledger holds the
phases the step needs. Every output is written once (`never_overwrite`). Basic Pitch is imported only inside
`learn/bp_run.py`, run by its venv's own interpreter in a subprocess; nothing here imports it.

The pure parts (the clean-up, the note matching, the kinds and windows of the ear items, every check's pass rule, the
calibration's rule (12m), the gate's pass, the rejected clips' cases, the triggers, the ring variant's rule, the
refusal count, the expected-failure table, the lock, the overlap song by song) are tested in
tests/test_note_transcribe.py on the light CI runner (no numpy).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import statistics
import time

from learn import note_rebuild as NR

LEDGER_ID = NR.LEDGER_ID                 # note-rebuild
PLAN = NR.PLAN
PHASE = "phase_nr_1_redo"                # this declaration
PHASE_EAR_OLD = "phase_nr_1_ear_old"     # the old page's verdict, the user's words, and which check must fail which
                                         # rejected clip (step 2; never written to phase_nr_1_ear)
PHASE_INSTALL = "phase_nr_1_redo_install"   # the lock, the model, resolve.json, the gate's and calibration's facts
PHASE_NOTES = "phase_nr_1_redo_notes"    # the note files' sha256
PHASE_EAR = "phase_nr_1_redo_ear"        # the new page's verdict (`note_rebuild_ear.redo_verdict`)
LADDER_ID = "preset-ladder"
PHASE_DRY = "phase_scratch_notes_dry"    # the redo build's sha256 (the dry guitar of every fs-notes search record)
# the second amendment (note-rebuild-plan 12m): measure first
PHASE_CALIB = "phase_nr_1_redo_calib_amend"   # the declaration: detector, truth report, gate bar reported, the read
PHASE_TRUTH = "phase_nr_1_redo_truth"    # the truth listing's sha256, before any run reads a truth window
PHASE_VERSIONS = "phase_nr_1_redo_versions"   # the note-versions read: per-set numbers, the code, gamma if adopted
PHASE_GO_CHORDS = "phase_nr_1_redo_go_chords"   # the user's go when P2's chord recall reads under 0.85
PHASE_GO_FLAGS = "phase_nr_1_redo_go_flags"     # ... when onsets-found flags 3 or more of the 40 deciding parts
PHASE_GO_CLIPS = "phase_nr_1_redo_go_clips"     # ... when a rejected clip is caught by no check
PHASE_GO_VERSIONS = "phase_nr_1_redo_go_versions"   # ... the user's decision after a code other than NV-loud
PHASE_GO_LADDER = "phase_nr_1_redo_go_ladder"     # ... the user's go after the instrument check failed a list
                                                #     (2026-11-23; bound to that ghost-ladder.json by its sha256)
PHASE_CALIB_FIX = "phase_nr_1_redo_calib_fix"     # the calibration's fix (2026-11-23): chords-kept on one timeline,
                                                #     annotated-found a report, the positive control's rule, the rerun
PHASE_GO_CALIB = "phase_nr_1_redo_go_calib"       # the user's go after the first calibration stopped (2026-11-23;
                                                #     playing-covered reported for this run; bound to its sha256)
PHASE_GO_GUARD = "phase_nr_1_redo_go_guard"       # the user's go that the checks the positive control fails become
                                                #     reports, the listening page the guard (2026-11-23; names them)
PHASE_EAR_KINDS = "phase_nr_1_ear_kinds"          # the ear items' kinds, amended 2026-11-23 (the delegated decision)
PHASE_ITEM5_OUT = "phase_nr_1_redo_item5_out"     # 12p's exclusion of the DI the user ruled out (the code on main)
PHASE_NO_CAPS = "phase_nr_1_redo_no_caps"         # the user retires 12h's fix cap and its stop (2026-11-24)
FIRST_DRY_SHA = "46e485a22c5f925457ebb89905aa2fc16c853e58c694791cbde77c14831fbf5b"   # the first build (phase_scratch_notes_dry)
PHASE_GO_HUM = "phase_nr_1_redo_go_hum"           # ... the user's go after the hum guard stopped the truth report
                                                #     (2026-11-23; bound to that truth-report.json by its sha256)

REDO = NR.OUT / "redo"                   # PF/note-rebuild/redo/
CALIB_ASIDE = REDO / "calibration.failed-20261123"   # the first calibration.json and its work folder, set aside unread
STAGE1 = NR.OUT / "stage1"
SET_ASIDE = NR.OUT / "stage1.set-aside-20261122"
SET_ASIDE_NOTE = "unread: no pick, no score"
# the stage-1 render hand-back's "sha256 of the sorted per-file sha256 list" (2dccf3e6...71de), in full: `shasum -a 256`
# lines ("<sha256>  ./<arm>/<file>") over dist/'s files sorted by path, hashed (`listing_sha`)
DIST_LIST_SHA = "2dccf3e667e3b1941600bde5e9829e1c8bdff4d0788683d9ef22b70bae1471de"

# --- the install (plan section 12b), checked against PyPI on 2026-11-22 -----------------------------------------------
TOOLS = NR.HOME / "tools" / "basic-pitch-venv"
INTERPRETER = "/usr/bin/python3"         # 3.9.6 arm64; the fallback (3.11) is a declared download, never a second install
BP_PYTHON = TOOLS / "bin" / "python"
LOCK = TOOLS / "requirements.lock"
RESOLVE = TOOLS / "resolve.json"
MANIFEST = TOOLS / "manifest.json"
PIP_PIN = ("pip", "26.0.1", "bdb1b08f4274833d62c1aa29e20907365a2ceb950410df15fc9521bad440122b")
BASIC_PITCH = ("basic-pitch", "0.4.0", "738adb503aae7fdfc7d1e1511aa0ce35052315f260a19531ef4c356708425db0", 758279)
ONNXRUNTIME = ("onnxruntime", "1.19.2", "006c8d326835c017a9e9f74c9c77ebb570a71174a1e89fe078b29a557d9c3848", 16776457)
ONNXRUNTIME_CP311 = ("onnxruntime", "1.19.2", "d863e8acdc7232d705d49e41087e10b274c42f09e259016a46f32c34e06dc4fd",
                     16779187)          # the declared fallback (Python 3.11): the same version's cp311 universal2 wheel
ONNX_PIN = {"3.9": ONNXRUNTIME, "3.11": ONNXRUNTIME_CP311}   # the interpreter's minor version -> its onnxruntime pin
KNOWN_WHEELS = {"pretty-midi": ("0.2.11.post0", "a3e2321736245a9c92259716d85a4762f16b7bde2f591fb0dba95bdb6e793d8a"),
                "mir-eval": ("0.8.2", "114cda33d8e17408c170598e0b36ed0d71ff4a2fee8eaf9e165b58ecf1c87170")}
REQUIREMENTS = ("librosa>=0.8.0", "mir-eval==0.8.2", "numpy>=1.18", "pretty-midi==0.2.11.post0",
                "resampy<0.4.3,>=0.2.2", "scikit-learn", "scipy>=1.4.1", "typing-extensions",
                "onnxruntime==1.19.2")   # basic-pitch's own list on this platform, without coremltools
MODEL_IN_WHEEL = "basic_pitch/saved_models/icassp_2022/nmp.onnx"
MEDLEYDB_INDEX = NR.HOME / "references" / "mirdata" / "medleydb_pitch_index.json"   # mirdata's medleydb_pitch index
                                         # (103 ids): placed by a declared download before `install`, which records its
                                         # sha256 in the manifest
INSTALL_MIN_GB = 32.0                    # the install refuses under this (the disk guard is 31 GB)

# --- the transcriber's settings, frozen (plan section 12c) ----------------------------------------------------------------
BP_SETTINGS = {"onset_threshold": 0.5, "frame_threshold": 0.3, "minimum_note_length": 58.0,
               "minimum_frequency": 60.0, "maximum_frequency": 1400.0, "melodia_trick": True,
               "multiple_pitch_bends": True}
BP_SR = 22050                            # 48 kHz to 22.05 kHz by resample_poly(x, 147, 320)
BP_UP, BP_DOWN = 147, 320
BP_PEAK_DBFS = -1.0
MARGIN_S = 1.0                           # up to 1.0 s of the file either side of the section
KEEP_MIDI = (36, 88)                     # the clean-up: MIDI 36 to 88 kept
MERGE_S = 0.030                          # a pitch struck twice within 30 ms: merged
MAX_AT_ONCE = 6
OCTAVE_UP_BELOW = 38                     # notes below MIDI 38 are played an octave up (counted)

# --- the content checks (plan section 12e, amended in note-rebuild-plan 12m), thresholds frozen; `CONTENT` names each,
# what it gates, and whether it blocks a row part. `onsets-found` is a report since 12m: librosa's flux detector
# (`note_attacks`), a flag under 0.90; `annotated-found` admits its windows by `note_truth.consistent`.
CONTENT = {
    "annotated-found": {"gates": "a report (12m fix, 2026-11-23: no fair admission test admits GOAT's windows)",
                        "blocking": False,
                        "onset_s": 0.050, "median": 0.85, "floor": 0.75, "admission": "consistent", "tertile": "top"},
    "onsets-found": {"gates": "a report (flag under 0.90)", "blocking": False, "within_s": 0.050, "share": 0.90,
                     "detector": "librosa onset_detect, hop 256, delta 0.07, after the P1 offset"},
    "playing-covered": {"gates": "a report (12q R1)", "blocking": False, "playing": 0.95, "silent": 0.10},
    "judge-accepts": {"gates": "a report (12q R1)", "blocking": False, "pause_over_true": 0.05, "gap_s": 0.250,
                      "gap_db": 40.0},
    "ring-kept": {"gates": "a report (12q R1)", "blocking": False, "after_s": 0.600, "attack_s": 0.050, "median_db": 3.0,
                  "min_frames": 20, "env_corr": 0.80},
    "chords-kept": {"gates": "a report (12q R1)", "blocking": False, "onset_s": 0.050, "note_f": 0.85, "chord_recall": 0.85,
                    "chord_size": 3, "min_chord_notes": 5},
}
NOTE_CHECKS = ("onsets-found", "playing-covered")
AUDIO_CHECKS = ("judge-accepts", "ring-kept", "chords-kept")
CHECK_FRAME_S, CHECK_HOP_S = 0.020, 0.005   # the level frames of judge-accepts (iii) and ring-kept (i)
PLAY_FLOOR_DB = 40.0                     # "where the DI plays": within 40 dB of its loudest frame (J0's floor)
PLAY_FRAME = 2048                        # playing-covered's frames: J0's middle frame size, hop a quarter
CALIBRATION_PASS = 25                    # of the 27 development windows, playing-covered (90%; 12m: onsets-found is
                                         # a report and not in the rate)
P2_CHORD_TRIGGER = 0.85                  # P2's chord recall in the truth report under this: to the user before step 5
FLAG_TRIGGER = 3                         # onsets-found flags on this many of the 40 deciding parts: to the user
DECIDING = ("bks", "goat")               # the user's exception for this row only (2026-11-22, answer 3)

# --- the install gate (plan section 12b) -----------------------------------------------------------------------------------
REPEAT_WINDOWS = 4                       # development windows, three runs each (two in one process, one fresh)
KNOWN_F = 0.90                           # note F on the ten known lists, pooled (onset 50 ms, pitch 50 cents)
KNOWN_ONSET_S = 0.050
RING_TIE = 0.02                          # ring-soft unless ring-on's median envelope_corr is more than this higher

# --- the development windows and the ear page's items (plan sections 12c, 12d) ------------------------------------------
DEV_COUNT = 27                           # every GOAT item clear of the exclusion list with fine-aligned MIDI and a full
                                         # window at the probe's start (30 s into items over 45 s, else 1 s)
RULED_OUT = ("item_5",)                  # the user's "Bad DI, don't use it" (2026-11-23; 12p, phase_nr_1_redo_item5_out):
                                         # out of fs-notes and every later read; the records made keep it
DEV_READ_COUNT = DEV_COUNT - len(RULED_OUT)   # the development windows a later read uses (26); made records keep 27
CALIBRATION_FAIL_ALLOWED = DEV_COUNT - CALIBRATION_PASS   # 2: a later read keeps the count of windows allowed to fail
EAR_SEED = 20261401                      # the 4 new ear items' order
CONTROL_SEED = 20261402                  # the hidden control card's item and the cards' order
DEV_BLUR_SEED = 20261403                 # avg+mild on the development windows (the checks' positive control)
KINDS = ("chord-led", "single-note", "bends", "let-ring")
KIND_BARS = {"chord-led": 0.5, "single-note": 0.8, "bends": 3, "let-ring": 0.5}   # each kind's own figure's bar
ANNOTATED_KINDS = ("single-note",)       # read from GOAT's annotated notes (the ear kinds' amendment, 2026-11-23)
GRID_S = 5.0                             # an ear item's window: the 10 s with the most notes on a 5-s grid
EAR_AMP = "ac20"
EAR_LUFS = -23.0
OLD_EAR_ITEMS = 4


# --- the clean-up and the note lists (pure) -------------------------------------------------------------------------------

def notes_from_events(events):
    """(Pure.) bp_run's stored events -> notes {on, off, pitch, amp, bends}."""
    return [{"on": float(e["on"]), "off": float(e["off"]), "pitch": int(e["pitch"]), "amp": float(e.get("amp", 0.0)),
             "bends": list(e.get("bends") or [])} for e in events]


def clean_transcribed(notes):
    """(Pure.) The declared clean-up: MIDI KEEP_MIDI kept (the rest counted out); notes below OCTAVE_UP_BELOW played an
    octave up (counted); a pitch struck twice within MERGE_S merged into the first (its end the later of the two); at
    most MAX_AT_ONCE notes at once (the newest dropped). -> (notes in onset order, counts)."""
    cnt = {"out_of_range": 0, "octave_up": 0, "merged": 0, "over_six": 0}
    up = []
    for n in notes:
        if not KEEP_MIDI[0] <= n["pitch"] <= KEEP_MIDI[1]:
            cnt["out_of_range"] += 1
            continue
        if n["pitch"] < OCTAVE_UP_BELOW:
            n = dict(n, pitch=n["pitch"] + 12)
            cnt["octave_up"] += 1
        up.append(dict(n))
    kept = []
    for n in sorted(up, key=lambda n: (n["on"], n["pitch"], n["off"])):
        twin = next((m for m in kept if m["pitch"] == n["pitch"] and abs(m["on"] - n["on"]) < MERGE_S), None)
        if twin is not None:
            twin["off"] = max(twin["off"], n["off"])
            cnt["merged"] += 1
            continue
        if sum(m["on"] <= n["on"] < m["off"] for m in kept) >= MAX_AT_ONCE:
            cnt["over_six"] += 1
            continue
        kept.append(n)
    return kept, cnt


def in_window(notes, length_s):
    """(Pure.) The notes sounding inside [0, length_s)."""
    return [n for n in notes if n["off"] > 0 and n["on"] < length_s]


def match_notes(ref, est, onset_s=KNOWN_ONSET_S):
    """(Pure.) One-to-one matching of two note lists: same MIDI pitch (50 cents on integer pitches), onsets within
    `onset_s`, the closest pairs first. -> {matched, ref, est, precision, recall, f}."""
    pairs = sorted((abs(r["on"] - e["on"]), i, j) for i, r in enumerate(ref) for j, e in enumerate(est)
                   if r["pitch"] == e["pitch"] and abs(r["on"] - e["on"]) <= onset_s)
    ui, uj, m = set(), set(), 0
    for _, i, j in pairs:
        if i not in ui and j not in uj:
            ui.add(i)
            uj.add(j)
            m += 1
    p = m / len(est) if est else None
    r = m / len(ref) if ref else None
    f = 2 * m / (len(ref) + len(est)) if (ref or est) else None
    return {"matched": m, "ref": len(ref), "est": len(est), "precision": p, "recall": r, "f": f,
            "ref_matched": sorted(ui)}


def pooled_f(results):
    """(Pure.) Note F pooled over several `match_notes` results."""
    m = sum(r["matched"] for r in results)
    d = sum(r["ref"] + r["est"] for r in results)
    return 2 * m / d if d else None


def repeat_identical(runs):
    """(Pure.) The install gate's repeat test: every run's events (a list of event lists for one window) identical."""
    return all(r == runs[0] for r in runs[1:]) if runs else False


def groups_of(notes, gap=NR.CHORD_S):
    """(Pure.) `note_rebuild.onset_groups` on these notes, as lists of notes."""
    return [[notes[k] for k in g] for g in NR.onset_groups(notes)]


def kind_flags(notes):
    """(Pure.) The ear page's four kinds a window's transcribed notes show (plan section 12g): chord-led (half or more
    of the onset groups hold 3 or more notes); single-note (80% or more hold one note, and no bent note); bends (3 or
    more bent notes, by `note_rebuild.bend_curve`); let-ring (half or more of the groups are single notes still sounding
    100 ms into the next onset). -> set of kinds."""
    gs = groups_of(notes)
    if not gs:
        return set()
    bent = sum(any(NR.bend_curve(n, notes)) for n in notes)
    out = set()
    if sum(len(g) >= 3 for g in gs) >= 0.5 * len(gs):
        out.add("chord-led")
    if sum(len(g) == 1 for g in gs) >= 0.8 * len(gs) and bent == 0:
        out.add("single-note")
    if bent >= 3:
        out.add("bends")
    ring = sum(1 for a, b in zip(gs, gs[1:]) if len(a) == 1 and a[0]["off"] >= b[0]["on"] + 0.100)
    if ring >= 0.5 * len(gs):
        out.add("let-ring")
    return out


def grid_window(notes, duration_s, length_s=10.0, grid_s=GRID_S, lead_s=0.25):
    """(Pure.) An ear item's window: the start on a `grid_s` grid whose window (`lead_s` + `length_s`) fits the item
    and holds the most note onsets in its scored `length_s`; the earliest on a tie. -> start s or None."""
    best, j = None, 0
    while j * grid_s + lead_s + length_s <= duration_s + 1e-9:
        w = j * grid_s
        c = sum(w + lead_s <= n["on"] < w + lead_s + length_s for n in notes)
        if best is None or c > best[1]:
            best = (w, c)
        j += 1
    return None if best is None else best[0]


def kind_figures(notes):
    """(Pure.) Each kind's own figure on a window's notes (as `kind_flags` reads them): chord-led, the share of onset
    groups holding 3 or more notes; single-note, the share holding one (None with a bent note: it cannot qualify);
    bends, the count of bent notes; let-ring, the share of groups that are single notes still sounding 100 ms into the
    next onset. -> {kind: figure} ({} with no groups)."""
    gs = groups_of(notes)
    if not gs:
        return {}
    bent = sum(any(NR.bend_curve(n, notes)) for n in notes)
    ring = sum(1 for a, b in zip(gs, gs[1:]) if len(a) == 1 and a[0]["off"] >= b[0]["on"] + 0.100)
    return {"chord-led": sum(len(g) >= 3 for g in gs) / len(gs),
            "single-note": None if bent else sum(len(g) == 1 for g in gs) / len(gs),
            "bends": bent, "let-ring": ring / len(gs)}


def ear_kinds_of(kinds_tr, kinds_ann):
    """(Pure.) The ear kinds' amendment (2026-11-23): `single-note` from GOAT's annotated notes (bend-free), the other
    kinds from the transcription as declared. kinds_*: {item: set of kinds}. -> {item: set of kinds}."""
    out = {}
    for it in set(kinds_tr) | set(kinds_ann):
        tr = {k for k in kinds_tr.get(it, set()) if k not in ANNOTATED_KINDS}
        out[it] = tr | {k for k in kinds_ann.get(it, set()) if k in ANNOTATED_KINDS}
    return out


def nearest_fill(order, picked, figures, kind, bar=None):
    """(Pure.) The ear kinds' fallback (2026-11-23): an unfilled kind takes the not-yet-picked item with the highest
    figure of that kind's own (ties by `order`, the seeded order), recorded as not filled. figures: {item: {kind:
    figure}}. -> {kind, item, filled: False, nearest: True, figure, bar, label} or None (no item has the figure)."""
    used = set(picked.values())
    best = None
    for it in order:
        f = (figures.get(it) or {}).get(kind)
        if it in used or f is None:
            continue
        if best is None or f > best[1]:
            best = (it, f)
    if best is None:
        return None
    bar = KIND_BARS[kind] if bar is None else bar
    return {"kind": kind, "item": best[0], "filled": False, "nearest": True, "figure": best[1], "bar": bar,
            "label": f"{kind} (nearest; none met {bar:.2f})"}


def choose_ear_kinds(order, kinds_tr, kinds_ann, figs_tr, figs_ann):
    """(Pure.) The 4 new ear items as amended (2026-11-23): the declared pass (`pick_ear_items`) on the kinds of
    `ear_kinds_of`; then each kind still unfilled takes its nearest item by its own figure (`nearest_fill`, from the
    kind's own source). A kind the declared pass fills never uses the fallback. -> ({kind: item}, {kind: record})."""
    new = pick_ear_items(order, ear_kinds_of(kinds_tr, kinds_ann))
    chosen = {}
    for k in KINDS:
        src, fg = ("annotation", figs_ann) if k in ANNOTATED_KINDS else ("transcription", figs_tr)
        if k in new:
            chosen[k] = {"kind": k, "item": new[k], "filled": True, "nearest": False,
                         "figure": (fg.get(new[k]) or {}).get(k), "bar": KIND_BARS[k], "label": k, "source": src}
            continue
        near = nearest_fill(order, new, fg, k)
        if near is None:
            raise SystemExit(f"no item has a {k} figure among the development items")
        new[k] = near["item"]
        chosen[k] = {**near, "source": src}
    return new, chosen


def pick_ear_items(order, kinds_of):
    """(Pure.) The 4 new ear items: in `order` (seeded), each item fills the first kind (in KINDS order) it shows that
    is not filled yet; an item fills at most one kind. kinds_of: {item: set of kinds}. -> {kind: item} (a kind left
    unfilled is missing)."""
    out = {}
    for it in order:
        k = next((k for k in KINDS if k not in out and k in kinds_of.get(it, set())), None)
        if k is not None:
            out[k] = it
        if len(out) == len(KINDS):
            break
    return out


def ear_cards(old_items, new_by_kind, seed=CONTROL_SEED):
    """(Pure.) The page's 13 cards: each of the 8 items through the clean start; the 4 new items (one of each kind)
    again through the crunch start; one hidden control (the true DI as Rebuilt) on a seeded item's clean window; the
    cards in a seeded order. -> [{id, n, item, cls, control}]."""
    items = sorted(old_items) + [new_by_kind[k] for k in KINDS]
    cards = [{"item": it, "cls": "clean", "control": False} for it in items]
    cards += [{"item": new_by_kind[k], "cls": "crunch", "control": False} for k in KINDS]
    rng = random.Random(f"{seed}|cards")
    cards.append({"item": rng.choice(items), "cls": "clean", "control": True})
    rng.shuffle(cards)
    return [dict(c, id=f"c{j}", n=j) for j, c in enumerate(cards, 1)]


# --- the checks' pass rules (pure) -----------------------------------------------------------------------------------------

def onsets_found_pass(fig, c=CONTENT["onsets-found"]):
    """(Pure.) At least `share` of the DI's attacks have a note onset within `within_s`; with no attack it is not
    measured (None: reported, never blocking)."""
    if not fig or not fig.get("attacks"):
        return None
    return fig["found"] / fig["attacks"] >= c["share"]


def playing_covered_pass(fig, c=CONTENT["playing-covered"]):
    """(Pure.) A note sounds in at least `playing` of the DI's playing frames and in at most `silent` of the rest."""
    if not fig or fig.get("playing_share") is None:
        return None
    return fig["playing_share"] >= c["playing"] and (fig.get("silent_share") or 0.0) <= c["silent"]


def judge_accepts_pass(fig, c=CONTENT["judge-accepts"]):
    """(Pure.) (i) J0 does not refuse on the search half (None where no stem exists: the development and ear items);
    (ii) on each half and frame size the dry guitar's pause share at most the true DI's + `pause_over_true`; (iii) no
    stretch over `gap_s` where the DI plays and the dry guitar is `gap_db` under its loudest."""
    if not fig:
        return None
    if fig.get("judge_finite") is False:
        return False
    for h in (fig.get("pauses") or {}).values():
        for v in h.values():
            if v["dry"] > v["true"] + c["pause_over_true"]:
                return False
    return (fig.get("longest_gap_s") or 0.0) <= c["gap_s"]


def ring_kept_pass(fig, c=CONTENT["ring-kept"]):
    """(Pure.) (i) the median late-level difference within +-`median_db` (not measured under `min_frames` frames: (ii)
    gates alone); (ii) `envelope_corr` at least `env_corr`."""
    if not fig or fig.get("env_corr") is None or not math.isfinite(fig["env_corr"]):
        return False if fig else None
    if fig["env_corr"] < c["env_corr"]:
        return False
    if fig.get("late_frames", 0) >= c["min_frames"] and fig.get("late_median_db") is not None:
        return abs(fig["late_median_db"]) <= c["median_db"]
    return True


def chords_kept_pass(fig, c=CONTENT["chords-kept"]):
    """(Pure.) The round trip's note F at least `note_f`; the recall of notes in groups of `chord_size` or more at least
    `chord_recall` (measured on parts with `min_chord_notes` such notes). The pitch-class cosine is reported only."""
    if not fig or fig.get("f") is None:
        return None
    if fig["f"] < c["note_f"]:
        return False
    if fig.get("chord_notes", 0) >= c["min_chord_notes"]:
        return fig["chord_recall"] >= c["chord_recall"]
    return True


PASS_RULES = {"onsets-found": onsets_found_pass, "playing-covered": playing_covered_pass,
              "judge-accepts": judge_accepts_pass, "ring-kept": ring_kept_pass, "chords-kept": chords_kept_pass}


def declared_blocking():
    """(Pure.) The checks `CONTENT` declares blocking."""
    return {k for k, c in CONTENT.items() if c["blocking"]}


def check_verdict(figs, which=NOTE_CHECKS + AUDIO_CHECKS, blocking=None):
    """(Pure.) {check: True | False | None} for `which`, and the blocking failures (a None, not measured, never
    blocks). figs: {check: figure}; `blocking`: the checks that block (default: as `CONTENT` declares; after the
    calibration's fix, `effective_blocking`)."""
    block = declared_blocking() if blocking is None else set(blocking)
    res = {k: PASS_RULES[k](figs.get(k)) for k in which}
    return {"passes": res, "failed": sorted(k for k, v in res.items() if v is False and k in block)}


def positive_failing(checks, controls=("avg+mild", "true")):
    """(Pure.) The declared blocking checks the positive control (avg+mild or the true DI) fails on any window.
    checks: {control: {window: {passes: {check: bool | None}}}}. -> sorted checks."""
    return sorted({k for d in controls for r in (checks.get(d) or {}).values()
                   for k, v in (r.get("passes") or {}).items() if v is False and k in declared_blocking()})


def positive_report_only(failing, nr_main, first_sha):
    """(Pure.) The calibration fix's rule (12m, 2026-11-23): a check the positive control fails becomes report-only
    for the row only when main holds the user's go on that effect (`PHASE_GO_GUARD`, its `go` true, its
    `calibration_sha256` the first record's, `first_sha`, and naming the check in `report_only_checks`); otherwise it
    stays blocking (and its failure stops the calibration). -> (report-only checks, checks the positive control fails
    that stay blocking)."""
    go = (nr_main or {}).get(PHASE_GO_GUARD)
    valid = (isinstance(go, dict) and go.get("go") is True and bool(first_sha)
             and go.get("calibration_sha256") == first_sha)
    named = set(go.get("report_only_checks") or []) if valid else set()
    return sorted(k for k in failing if k in named), sorted(k for k in failing if k not in named)


def effective_blocking(cal_body, nr_main):
    """(Pure.) The checks that block a row part after the calibration's fix: the declared blocking checks less
    `playing-covered` under the user's go (`PHASE_GO_CALIB`, its `go` true: reported for this run) and less every check
    the calibration made report-only (`report_only_checks`)."""
    block = declared_blocking()
    go = (nr_main or {}).get(PHASE_GO_CALIB)
    if isinstance(go, dict) and go.get("go") is True:
        block.discard("playing-covered")
    return block - set((cal_body or {}).get("report_only_checks") or [])


def annotated_found_pass(rows, c=CONTENT["annotated-found"]):
    """(Pure.) `annotated-found` on the development windows: on the windows in the top alignment-F tertile whose own
    annotation is consistent with the DI (`note_truth.consistent`, 12m: at least 8 notes and 80% of its onset clusters
    with their steepest rise within 30 ms of the window's one offset; the old "lands" test passed at random times), the
    median recall at least `median` and no window under `floor`. rows: [{alignment_f, consistent, recall}].
    -> {windows, median, minimum, passes}."""
    from learn import note_rebuild_s1 as S1

    edges = S1.tertile_edges([r["alignment_f"] for r in rows])
    top = [r for r in rows if r.get("alignment_f") is not None and S1.group_of(r["alignment_f"], edges) == len(edges)
           and r.get("consistent") is True and r.get("recall") is not None]
    if not top:
        return {"windows": 0, "median": None, "minimum": None, "passes": None, "edges": edges}
    rec = [r["recall"] for r in top]
    med = statistics.median(rec)
    return {"windows": len(top), "median": med, "minimum": min(rec), "edges": edges,
            "passes": med >= c["median"] and min(rec) >= c["floor"]}


def gate_passes(body):
    """(Pure.) The install gate passes when the transcriber repeats exactly (12m, the user's decision): its known-notes
    F is a reported figure, not a bar; the timing is measured and recorded."""
    return (body or {}).get("repeat_ok") is True


def clip_case(expected, results, blocking=None):
    """(Pure.) Each rejected clip's case (12m): "caught by a blocking check" (a blocking check its line names fails),
    "caught by a report only" (only a report-only check it names fails: recorded, the page's "missing notes" button is
    the guard, the user is told, the work goes on) or "caught by no check" (to the user, recommended: go on with the
    listening page as the guard). `blocking`: the checks that block (default: as `CONTENT` declares). -> {clip: case}."""
    block = declared_blocking() if blocking is None else set(blocking)
    out = {}
    for e in expected:
        got = results.get(e["clip"]) or {}
        failed = [k for k in (e.get("must_fail_any") or list(NOTE_CHECKS)) if got.get(k) is False]
        if any(k in block for k in failed):
            out[e["clip"]] = "caught by a blocking check"
        elif failed:
            out[e["clip"]] = "caught by a report only"
        else:
            out[e["clip"]] = "caught by no check"
    return out


def calibration_ok(covered_windows, cases, clips_go=False, need=CALIBRATION_PASS, covered_reported=False,
                   positive_blocking=()):
    """(Pure.) The calibration passes (12m, as fixed 2026-11-23, `PHASE_CALIB_FIX`): `playing-covered` holds on at
    least `need` of the 27 windows, unless the user's go makes it a report for this run (`covered_reported`); every
    rejected clip is caught by a check (a clip caught by no check needs the user's go, `PHASE_GO_CLIPS`).
    `annotated-found` is a report (no fair admission test admits GOAT's windows); a check the positive control
    fails becomes report-only under the user's go (`positive_report_only`), and one it fails that stays blocking
    (`positive_blocking`) stops the calibration, as declared before the fix."""
    return ((covered_reported or covered_windows >= need) and not positive_blocking
            and (clips_go or "caught by no check" not in cases.values()))


def calib_rerun_refusal(nr_main, aside_sha, aside_work):
    """(Pure.) Why `calibrate` may not run, or None. The first run stopped (2026-11-23); the only way to run it again:
    main holds the fix (`PHASE_CALIB_FIX`) and the user's go (`PHASE_GO_CALIB`, its `go` true, naming the first
    record's sha256), and that record and its work folder are set aside in `CALIB_ASIDE` (`aside_sha`: the set-aside
    calibration.json's sha256 or None; `aside_work`: whether its work folder is there)."""
    if PHASE_CALIB_FIX not in (nr_main or {}):
        return f"main's {LEDGER_ID} entry has no {PHASE_CALIB_FIX}: the calibration's fix first"
    go = (nr_main or {}).get(PHASE_GO_CALIB)
    if not isinstance(go, dict) or go.get("go") is not True or not go.get("calibration_sha256"):
        return f"main holds no go of the user's for the calibration's rerun ({PHASE_GO_CALIB})"
    if aside_sha is None or not aside_work:
        return f"the first calibration.json and its work folder are not set aside in {CALIB_ASIDE.name}/"
    if aside_sha != go["calibration_sha256"]:
        return f"the set-aside calibration.json's sha256 {aside_sha[:12]} is not the one the user's go names"
    return None


def round_trip_notes(events, audio, rate=NR.SR):
    """A round trip's notes on the DI notes' timeline (12m fix, 2026-11-23): the same steps `timed_notes` gives the
    DI's notes (the clean-up, the notes inside the audio, `coarse_offset`, the +-SNAP_S snap), against the audio that
    was transcribed."""
    return timed_notes({"events": events, "pre_s": 0.0}, audio, rate)[0]


def chords_go_refusal(p2_chord_recall, nr_main, trigger=P2_CHORD_TRIGGER):
    """(Pure.) Why the 47 parts may not be transcribed on the truth report, or None: P2's chord recall under the
    trigger goes to the user first (their go on main, `PHASE_GO_CHORDS`)."""
    if p2_chord_recall is None:
        return "the truth report has no P2 chord recall"
    return None                                  # 12q R1: the chord recall is reported, never a trigger


def flags_note(flagged_deciding, nr_main, trigger=FLAG_TRIGGER):
    """(Pure.) `transcribe`'s word on the flagged-parts count: to the user before any build while the trigger holds
    and main holds no go of the user's (`flags_go_refusal`); reported under the go; nothing under the trigger."""
    if len(flagged_deciding) < trigger:
        return ""
    return " (reported: 12q R1, never a trigger)"


def flags_go_refusal(flagged_deciding, nr_main, trigger=FLAG_TRIGGER):
    """(Pure.) Why nothing may be built after transcription, or None: `onsets-found` flags on `trigger` or more of the
    40 deciding parts go to the user first (their go on main, `PHASE_GO_FLAGS`)."""
    return None                                  # 12q R1: the flag count is reported, never a trigger


def versions_loud(nr_main):
    """(Pure.) The loudness `build` uses, from main's note-versions read: its gamma when it reads NV-loud; otherwise
    the user's decision recorded under `PHASE_GO_VERSIONS` ({"go": true, "versions_sha256": the read's sha256, "loud":
    None, 1.0 or 2.0}), refused unless all three hold. -> (gamma or None, refusal)."""
    rec = (nr_main or {}).get(PHASE_VERSIONS)
    if not isinstance(rec, dict) or "code" not in rec:
        return None, f"main's {PHASE_VERSIONS} holds no code: the read first"
    if rec["code"] == "NV-loud":
        return rec.get("gamma"), None
    go = (nr_main or {}).get(PHASE_GO_VERSIONS)
    if (not isinstance(go, dict) or go.get("go") is not True or not rec.get("sha256")
            or go.get("versions_sha256") != rec["sha256"]
            or "loud" not in go or isinstance(go["loud"], bool)
            or go["loud"] not in (None,) + tuple(NR.LOUD_GAMMA)):
        return None, f"the read is {rec['code']}: to the user first ({PHASE_GO_VERSIONS})"
    return go["loud"], None


def ladder_refusal(ladder, nr_main, ladder_sha):
    """(Pure.) Whether `versions` may read with the instrument check's distance, and whether the real set is reported
    only. The check's own outcome when it let the work go; when a list failed, only the user's go on main
    (`PHASE_GO_LADDER`, naming this ghost-ladder.json's sha256), and then the real set is reported only (their
    recorded reason, 2026-11-23). The ladder rule itself is unchanged. -> (refusal or None, real_reported_only)."""
    if ladder["go"]:
        return None, ladder["real_reported_only"]
    go = (nr_main or {}).get(PHASE_GO_LADDER)
    if not isinstance(go, dict) or go.get("go") is not True or go.get("ladder_sha256") != ladder_sha:
        return ("the instrument check failed on a list: nothing is read with that distance (to the user, "
                f"{PHASE_GO_LADDER})"), None
    return None, True


def content_shares(notes):
    """(Pure.) A part's two figures read beside the bottleneck: the share of bent notes (`note_rebuild.bend_curve`)
    and the share of onset groups holding 3 or more notes (chords). None without notes."""
    if not notes:
        return {"bent_share": None, "chord_share": None}
    gs = groups_of(notes)
    return {"bent_share": sum(any(NR.bend_curve(n, notes)) for n in notes) / len(notes),
            "chord_share": sum(len(g) >= 3 for g in gs) / len(gs)}


def install_record_refusal(rec, gate_sha, calibration_sha, pair):
    """(Pure.) Why main's `phase_nr_1_redo_install` does not hold this install's facts, or None: the lock and model
    sha256 (`pair`), the install gate's and the calibration's file sha256."""
    if not isinstance(rec, dict):
        return f"main's {PHASE_INSTALL} names no install"
    if (rec.get("lock_sha256"), rec.get("model_sha256")) != tuple(pair):
        return f"main's {PHASE_INSTALL} names another lock or model"
    if rec.get("gate_sha256") != gate_sha:
        return f"install-gate.json is not main's {PHASE_INSTALL} gate_sha256"
    if rec.get("calibration_sha256") != calibration_sha:
        return f"calibration.json is not main's {PHASE_INSTALL} calibration_sha256"
    return None


def ring_choice(corr_on, corr_soft, tie=RING_TIE):
    """(Pure.) The ring variant: the higher median `envelope_corr` over the development windows; `ring-soft` within
    `tie` (it cannot leave a released chord note sounding). corr_*: [per window]."""
    a, b = statistics.median(corr_on), statistics.median(corr_soft)
    return "ring-on" if a > b + tie else "ring-soft"


def refusal_count(build_parts, sets_of, deciding=DECIDING):
    """(Pure.) The row's content-check failures: {pkey: failed checks} of the deciding parts and of the panel
    (beside). A count of them stops nothing (S1, phase_scratch_refusal_reports): a check against the true DI is a label
    on its part, so "stops" is always False and `cmd_build` builds on. -> (deciding failed, panel failed, stops)."""
    dec, pan = {}, {}
    for k, r in sorted(build_parts.items()):
        failed = r.get("failed") or []
        if failed:
            (dec if sets_of[k] in deciding else pan)[k] = failed
    return dec, pan, False


def flagged_parts(parts, sets_of, deciding=DECIDING):
    """(Pure.) The parts `onsets-found` flags (a report), deciding and panel apart. parts: {pkey: {figures}}."""
    fl = sorted(k for k, r in parts.items() if ((r.get("figures") or {}).get("onsets-found") or {}).get("flag"))
    return [k for k in fl if sets_of.get(k) in deciding], [k for k in fl if sets_of.get(k) not in deciding]


def p2_chord_recall(report):
    """(Pure.) The truth report's P2 chord recall, or None."""
    return (((report or {}).get("report") or {}).get("P2|chords") or {}).get("recall")


def expected_failure_refusal(expected, results):
    """(Pure.) The checks' negative control: every rejected clip must fail at least one of the checks the ledger names
    for it (`phase_nr_1_ear_old`'s table, written before the checks run; the default where the user's words name none:
    `onsets-found` or `playing-covered`). expected: [{clip, must_fail_any: [checks]}]; results: {clip: {check: pass}}.
    -> [blind spots: (clip, the checks that should have failed)]."""
    out = []
    for e in expected:
        want = e.get("must_fail_any") or list(NOTE_CHECKS)
        got = results.get(e["clip"]) or {}
        if not any(got.get(k) is False for k in want):
            out.append((e["clip"], want))
    return out


def medleydb_song(name):
    """(Pure.) A MedleyDB file or index id's song ("Artist_Title"), or None for a name in no MedleyDB form."""
    base = pathlib.PurePath(name).name
    for tag in ("_RAW_", "_STEM_", "_MIX"):
        if tag in base:
            return base.split(tag, 1)[0]
    return None


def medleydb_index_ids(doc):
    """(Pure.) The track ids of a mirdata index document ({"tracks": {id: ...}})."""
    return sorted((doc or {}).get("tracks") or {})


def panel_group(p):
    """(Pure.) A panel part's group for the beside readings: "medleydb" (a file in MedleyDB's naming) or
    "laminar_flow" (the Cambridge session); None off the panel."""
    if p["set"] != "panel":
        return None
    rec = p["unit"].split("#", 1)[1] if "#" in p["unit"] else p["unit"]
    return "medleydb" if medleydb_song(rec) else "laminar_flow"


def transcriber_overlap_songs(parts, index_ids):
    """(Pure.) Song by song (the re-review's R13 on `note_rebuild.transcriber_overlap`, which marks the whole panel at
    set level): a panel part's MedleyDB song (from its record file's name) against mirdata's `medleydb_pitch` index
    ids, the stems Basic Pitch trained on. -> {pkey: song or None}; None: not a song it trained on (The Laminar
    Flow, a Cambridge session)."""
    trained = {medleydb_song(i) for i in index_ids} - {None}
    out = {}
    for p in parts:
        if p["set"] != "panel":
            continue
        rec = p["unit"].split("#", 1)[1] if "#" in p["unit"] else p["unit"]
        s = medleydb_song(rec)
        out[p["pkey"]] = s if s in trained else None
    return out


def lock_lines(report, extra=()):
    """(Pure.) requirements.lock from pip's `--dry-run --report` (every entry: name, version, file, sha256) with the
    extra pinned wheels (name, version, sha256) added. Refuses an entry with no sha256 or not a wheel. -> text."""
    rows = []
    for e in report.get("install") or []:
        md, dl = e.get("metadata") or {}, e.get("download_info") or {}
        ai = dl.get("archive_info") or {}
        sha = (ai.get("hashes") or {}).get("sha256") or (ai.get("hash") or "").split("sha256=")[-1] or None
        url = dl.get("url") or ""
        if not sha or not url.endswith(".whl"):
            raise SystemExit(f"{md.get('name')}: no wheel with a sha256 in the report ({url[-60:]})")
        rows.append((md["name"].lower().replace("_", "-"), md["version"], sha, url.rsplit("/", 1)[-1]))
    rows += [(n, v, s, "") for n, v, s in extra]
    names = [r[0] for r in rows]
    if len(names) != len(set(names)):
        raise SystemExit("the lock names a package twice")
    return "".join(f"{n}=={v} --hash=sha256:{s}" + (f"  # {f}" if f else "") + "\n" for n, v, s, f in sorted(rows))


def lock_refusal(text, onnx=ONNXRUNTIME):
    """(Pure.) Why a lock does not hold the declared pins, or None: basic-pitch and onnxruntime (`onnx`: the cp39
    pin, or ONNXRUNTIME_CP311 on the 3.11 fallback) at their declared versions and sha256, pretty-midi and mir-eval at
    their known wheels, no coremltools, every line hashed."""
    pins = {}
    for ln in text.splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        if "--hash=sha256:" not in ln:
            return f"an unhashed line: {ln[:60]}"
        spec, h = ln.split("--hash=sha256:", 1)
        n, v = spec.strip().split("==")
        pins[n] = (v, h.split()[0])
    for n, v, s, *_ in (BASIC_PITCH, onnx):
        if pins.get(n) != (v, s):
            return f"{n} is not {v} at its declared sha256"
    for n, (v, s) in KNOWN_WHEELS.items():
        if pins.get(n) != (v, s):
            return f"{n} is not the known wheel {v}"
    if "coremltools" in pins:
        return "coremltools is in the lock"
    return None


def install_pair(manifest):
    """(Pure.) The install's (lock sha256, model sha256) from its manifest."""
    return manifest["lock_sha256"], manifest["model_sha256"]


def install_refusal(note_rec, pair):
    """(Pure.) Why a note file may not be used, or None: it must name the install's lock and model sha256 (each note
    file comes from one install, never two) and the frozen settings."""
    if (note_rec.get("lock_sha256"), note_rec.get("model_sha256")) != tuple(pair):
        return "the note file comes from another install (lock or model sha256)"
    if note_rec.get("settings") != BP_SETTINGS:
        return "the note file ran with other settings"
    return None


def ledger_pair_refusal(nr_main, pair):
    """(Pure.) Why main's `phase_nr_1_redo_install` does not hold this install's pair, or None (absent: None; the
    steps before the hash PR read the install's own manifest, the steps after it refuse without the key)."""
    rec = (nr_main or {}).get(PHASE_INSTALL)
    if rec is None:
        return None
    if not isinstance(rec, dict) or (rec.get("lock_sha256"), rec.get("model_sha256")) != tuple(pair):
        return f"main's {PHASE_INSTALL} names another lock or model"
    return None


# --- the guards ------------------------------------------------------------------------------------------------------------

CODE_FILES = ("learn/scratch_search.py", "learn/scratch_notes.py", "learn/note_rebuild.py",
              "learn/note_rebuild_s1.py", "learn/note_rebuild_ear.py", "learn/note_transcribe.py", "learn/bp_run.py",
              "learn/note_truth.py", "learn/note_attacks.py", "learn/attack_run.py", "learn/note_versions.py",
              "learn/note_fixes.py")
KEY_PREFIXES = {LADDER_ID: ("phase_fs", "phase_scratch_notes"), LEDGER_ID: ("phase_nr",)}


def guarded_keys(entry, prefixes):
    """(Pure.) An entry's keys under the guarded prefixes."""
    return {k: v for k, v in (entry or {}).items() if k.startswith(tuple(prefixes))}


def keys_refusal(local, main):
    """(Pure.) Why this checkout's guarded keys are not main's, or None. local, main: {ledger id: entry}."""
    for lid, pre in KEY_PREFIXES.items():
        a, b = guarded_keys(local.get(lid), pre), guarded_keys(main.get(lid), pre)
        if a != b:
            diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            return f"this checkout's {lid} {', '.join(diff)} differ from main's: pull main (run from merged code)"
    return None


def entries(text):
    """(Pure.) {ledger id: entry} for the two ledgers this redo reads, from a ledger file's text."""
    d = json.loads(text)
    return {t["test_id"]: t for t in d.get("tests", []) if t.get("test_id") in (LADDER_ID, LEDGER_ID)}


def redo_on_main():
    """main's two entries (origin/main after a fetch) and whether this checkout runs main's redo: CODE_FILES equal
    main's and the guarded keys equal main's. -> ({ledger id: main's entry}, refusal or None)."""
    import subprocess

    def git(*a):
        return subprocess.run(["git", "-C", str(NR.REPO), *a], capture_output=True, text=True)
    git("fetch", "-q", "origin", "main")
    led = git("show", "origin/main:docs/dev-test-ledger.json")
    if led.returncode:
        return {}, f"main's ledger is not readable: {led.stderr.strip()}"
    m = entries(led.stdout)
    for f in CODE_FILES:
        if git("diff", "--quiet", "origin/main", "--", f).returncode:
            return m, f"this checkout's {f} differs from main's: run from merged code"
    return m, keys_refusal(entries((NR.REPO / "docs" / "dev-test-ledger.json").read_text()), m)


def require_redo(*phases, ladder=()):
    """Refuse unless this checkout runs main's redo and main's `note-rebuild` entry holds `phases` (and its
    `preset-ladder` entry `ladder`). -> {ledger id: main's entry}."""
    m, why = redo_on_main()
    if why:
        raise SystemExit(why)
    for k in (PHASE,) + tuple(phases):
        if k not in (m.get(LEDGER_ID) or {}):
            raise SystemExit(f"main's {LEDGER_ID} entry has no {k}: merge it before running")
    for k in ladder:
        if k not in (m.get(LADDER_ID) or {}):
            raise SystemExit(f"main's {LADDER_ID} entry has no {k}: merge it before running")
    return m


def never_overwrite(path):
    if pathlib.Path(path).exists():
        raise SystemExit(f"{path} exists: never overwritten")


def require_file_hash(entry, phase, path):
    """Refuse unless the file's sha256 is `phase`'s in `entry`. -> the file's JSON."""
    rec = (entry or {}).get(phase)
    sha = NR.file_sha(path)
    if not isinstance(rec, dict) or rec.get("sha256") != sha:
        raise SystemExit(f"{pathlib.Path(path).name}'s sha256 {sha[:12]} is not main's {phase}")
    return json.loads(pathlib.Path(path).read_text())


def ear_old_table(nr_main):
    """main's `phase_nr_1_ear_old` expected-failure table ([{clip, must_fail_any}]), refused when absent."""
    rec = (nr_main or {}).get(PHASE_EAR_OLD)
    if not isinstance(rec, dict) or not isinstance(rec.get("expected_failures"), list):
        raise SystemExit(f"main's {PHASE_EAR_OLD} has no expected_failures table: write it before the checks run")
    return rec["expected_failures"]


# --- paths -------------------------------------------------------------------------------------------------------------------

def note_path(kind, key):
    return REDO / "notes" / kind / f"{key.replace('/', '__')}.json"


def dry_path(arm, key, root=None):
    """A dry guitar's file: under the build's own `dry_root` (a fixed build), else the first build's `redo/dry/`."""
    return (pathlib.Path(root) if root else REDO / "dry") / arm / f"{key.replace('/', '__')}.npy"


def listening_suffix(build_sha):
    """(Pure.) The listening folders' suffix for a build (2026-11-24, no attempt cap): none for the first build (its
    page as built), the build's sha256 prefix for every later one, so each fixed build gets its own clips, page and
    verdict and none overwrites another."""
    return "" if build_sha == FIRST_DRY_SHA else f"-{build_sha[:12]}"


def ear_key(build_sha):
    """(Pure.) A build's ear verdict key: `phase_nr_1_redo_ear` for the first build, `phase_nr_1_redo_ear_<sha12>`
    for each later one."""
    return PHASE_EAR if build_sha == FIRST_DRY_SHA else f"{PHASE_EAR}_{build_sha[:12]}"


def gate_path():
    return REDO / "install-gate.json"


def gate_work_dir():
    """The install gate's raw events and inputs (one-process/, fresh/, known/): moved aside with install-gate.json."""
    return REDO / "work" / "install-gate"


def calibration_path():
    return REDO / "calibration.json"


def truth_path():
    return REDO / "truth.json"


def attacks_path():
    return REDO / "attacks.json"


def ladder_path():
    return REDO / "ghost-ladder.json"


def truth_report_path():
    return REDO / "truth-report.json"


def versions_path():
    return REDO / "versions.json"


def require_truth(m):
    """The truth listing, refused unless its sha256 is main's `phase_nr_1_redo_truth`."""
    if not truth_path().exists():
        raise SystemExit("no truth listing (run `truth` first)")
    return require_file_hash(m.get(LEDGER_ID), PHASE_TRUTH, truth_path())["body"]


def require_attacks():
    """The detector's report (`attacks-report`): its P1 offset is read by every `onsets-found` figure."""
    if not attacks_path().exists():
        raise SystemExit("no detector report (run `attacks-report` first)")
    return json.loads(attacks_path().read_text())["body"]


def truth_report_refusal(body, nr_main, report_sha):
    """(Pure.) Why the truth report may not be used, or None: refused when its hum guard stopped it, unless main holds
    the user's go (`PHASE_GO_HUM`, its `go` true, naming this truth-report.json's sha256; 2026-11-23: the stopping
    notes were chords ringing in from before each window, not hum). The guard's rule itself is unchanged."""
    if not body.get("stopped"):
        return None
    go = (nr_main or {}).get(PHASE_GO_HUM)
    if not isinstance(go, dict) or go.get("go") is not True or go.get("truth_report_sha256") != report_sha:
        return f"the truth report stopped on its hum guard ({body['stopped']}): to the user ({PHASE_GO_HUM})"
    return None


def require_truth_report(nr_main=None):
    """The truth report (`truth-report`), refused when its hum guard stopped it without the user's go on main
    (`truth_report_refusal`)."""
    if not truth_report_path().exists():
        raise SystemExit("no truth report (run `truth-report` first)")
    body = json.loads(truth_report_path().read_text())["body"]
    why = truth_report_refusal(body, nr_main, NR.file_sha(truth_report_path()))
    if why:
        raise SystemExit(why)
    return body


def transcribe_path():
    return REDO / "transcribe.json"


def build_path(name=None):
    """The first build's record, or a later build's own (`build-<name>.json`; no attempt cap)."""
    return REDO / ("build.json" if not name else f"build-{name}.json")


def dry_root(name=None):
    """The first build's dry guitars (`redo/dry/`), or a later build's own (`redo/dry-<name>/`)."""
    return REDO / ("dry" if not name else f"dry-{name}")


def ear_items_file(name=None):
    """The first build's ear items, or a later page's own when they were made (`ear-items-<name>.json`)."""
    p = REDO / f"ear-items-{name}.json"
    return p if name and p.exists() else ear_items_path()


def stem_preview_path():
    return REDO / "stem-preview.json"


def ear_items_path():
    return REDO / "ear-items.json"


def clips_dir(build_sha=FIRST_DRY_SHA):
    return NR.HOME / "listening" / f"note-rebuild-ear-2{listening_suffix(build_sha)}"


# --- audio in and out (numpy) ---------------------------------------------------------------------------------------------

def transcriber_input(x48):
    """The transcriber's input from 48 kHz audio: mono, `resample_poly(x, 147, 320)` to 22.05 kHz, peak at -1 dBFS,
    float32 (the package neither resamples nor normalises a 22.05 kHz file)."""
    import numpy as np
    from scipy.signal import resample_poly

    x = np.asarray(x48, np.float64)
    if x.ndim == 2:
        x = x.mean(axis=1)
    y = resample_poly(x, BP_UP, BP_DOWN)
    pk = float(np.abs(y).max())
    if pk > 0:
        y = y * (10 ** (BP_PEAK_DBFS / 20) / pk)
    return y.astype(np.float32)


def padded_section(prt, sr=NR.SR):
    """A part's raw DI section (`pretrain_set.section_audio`'s window) with up to MARGIN_S of the file either side.
    -> (audio at 48 kHz, pre_s: the section's start less the audio's)."""
    import soundfile as sf

    from learn import pretrain_set as PS

    dur = sf.info(str(prt["di_path"])).duration
    t0 = prt["start_s"] - PS.TRIM_S
    a = max(0.0, t0 - MARGIN_S)
    b = min(dur, t0 + PS.SEC_S + PS.TRIM_S + MARGIN_S)
    return PS.load_mono(prt["di_path"], sr, a, b - a), t0 - a


def run_bp(jobs, workdir):
    """Basic Pitch on [(48 kHz audio, tag)] in one bp_run process (the venv's interpreter, `-I`), the `.onnx` path
    passed explicitly. -> [bp_run's output record] in order."""
    import subprocess

    import soundfile as sf

    man = load_manifest()
    workdir = pathlib.Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    args = []
    for i, (x, tag) in enumerate(jobs):
        w, o = workdir / f"{i:03d}-{tag}.wav", workdir / f"{i:03d}-{tag}.json"
        sf.write(str(w), transcriber_input(x), BP_SR, subtype="FLOAT")
        args += [str(w), str(o)]
    r = subprocess.run([str(BP_PYTHON), "-I", str(NR.REPO / "learn" / "bp_run.py"), "--model", man["model_path"],
                        "--settings", json.dumps(BP_SETTINGS), *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"bp_run failed: {r.stderr.strip()[-400:]}")
    out = []
    for o in args[1::2]:
        rec = json.loads(pathlib.Path(o).read_text())
        if rec["model_sha256"] != man["model_sha256"] or rec["settings"] != BP_SETTINGS:
            raise SystemExit("bp_run ran another model or other settings")
        out.append(rec)
    return out


def note_record(bp, pre_s, source):
    """One note file's body: the install's pair, the settings, the input's sha256, the raw events, `pre_s`."""
    man = load_manifest()
    lock_sha, model_sha = install_pair(man)
    return {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "lock_sha256": lock_sha, "model_sha256": model_sha,
            "settings": BP_SETTINGS, "input_sha256": bp["input_sha256"], "pre_s": pre_s, "source": source,
            "versions": {k: bp.get(k) for k in ("basic_pitch", "onnxruntime", "python", "providers", "threads")},
            "events": bp["events"]}


def load_note(kind, key, pair=None):
    """A note file, refused unless it names `pair` (the install's lock and model sha256) and the frozen settings."""
    p = note_path(kind, key)
    if not p.exists():
        raise SystemExit(f"{p}: not transcribed")
    rec = json.loads(p.read_text())
    why = install_refusal(rec, pair or install_pair(load_manifest()))
    if why:
        raise SystemExit(f"{p.name}: {why}")
    return rec


def timed_notes(rec, di, rate=NR.SR):
    """A note file's notes on the section's timeline: the clean-up, moved by `pre_s`, the notes inside the window, then
    `coarse_offset` and the onset snap at +-SNAP_S against the DI as rendered. -> (notes, report)."""
    notes, cnt = clean_transcribed(notes_from_events(rec["events"]))
    notes = in_window(NR.shifted_notes(notes, -rec["pre_s"]), len(di) / rate)
    off = NR.coarse_offset(notes, di, rate)
    notes, shifts = NR.snap_onsets(NR.shifted_notes(notes, off), di, NR.SNAP_S, rate)
    return notes, {**cnt, "notes": len(notes), "window_offset_ms": 1000 * off,
                   "snapped": sum(s != 0 for s in shifts), "groups": len(shifts)}


def load_manifest():
    if not MANIFEST.exists():
        raise SystemExit(f"{MANIFEST}: no install (run `install` first)")
    return json.loads(MANIFEST.read_text())


# --- the checks' measures (numpy) -------------------------------------------------------------------------------------------

def attacks_found(attacks, notes, di, offset):
    """`onsets-found`'s figure (12m, a report): the detector's attacks (`note_attacks.run_attacks`) where the DI plays,
    after the detector's P1 offset, with a note onset within 50 ms; flagged under 0.90."""
    from learn import note_attacks as NA

    return NA.onsets_found(NA.plays_filter(attacks, di), [n["on"] for n in notes], offset)


def playing_covered(notes, di, c=CONTENT["playing-covered"]):
    """`playing-covered`'s figure: on J0's middle frames (PLAY_FRAME, hop a quarter), the share of the DI's playing
    frames (within PLAY_FLOOR_DB of its loudest) where a note sounds (the transcriber's own on and off times), and the
    share of the other frames where one does."""
    import numpy as np

    from analysis import aligned as A

    L = A._frame_db(np.asarray(di, np.float64), PLAY_FRAME)
    play = L >= L.max() - PLAY_FLOOR_DB
    hop = PLAY_FRAME // 4
    t = (np.arange(len(L)) * hop + PLAY_FRAME / 2) / NR.SR
    sound = np.zeros(len(L), bool)
    for n in notes:
        sound |= (t >= n["on"]) & (t < n["off"])
    return {"playing_frames": int(play.sum()), "playing_share": float(sound[play].mean()) if play.any() else None,
            "silent_frames": int((~play).sum()), "silent_share": float(sound[~play].mean()) if (~play).any() else 0.0}


def annotation_consistent(raw, di, rate=NR.SR):
    """A development window's GOAT annotation admitted by the consistency test (12m; `note_truth.consistent`): the
    annotation as it is (before the onset steps) against the window's one offset (`coarse_offset`)."""
    from learn import note_truth as NT_

    return NT_.consistent(NT_.cluster_shifts(raw, di, rate), NR.coarse_offset(raw, di, rate), len(raw))


def judge_pause_share(di_trim, lag, half, n_fft):
    """J0's pause share on one half for one frame size, as `aligned_distance` counts it from the DI alone (the frames
    within 40 dB of the DI's loudest, against the scored frames carried 1.5 s on)."""
    import numpy as np

    from analysis import aligned as A

    from learn import knob_ceiling as K

    a, b = K.R.HALVES[half]
    sr, shift = A.SAMPLE_RATE, int(lag)
    start = max(int(a * sr), shift if shift > 0 else 0)
    end = int(b * sr)
    hop = n_fft // 4
    k = max(1, 1 + (end - start - n_fft) // hop)
    tail = int(round(1.5 * sr / hop))
    pre = int(math.ceil(1.5 * sr / hop))
    di = np.asarray(di_trim, np.float64)
    dseg = A._segment(di, start - shift - K.P.LATENCY - pre * hop, end - start + pre * hop)
    playing = A._frame_db(dseg, n_fft) >= A._frame_db(di, n_fft).max() - 40.0
    scored = A._extend(playing, tail)
    playing, scored = playing[pre:pre + k], scored[pre:pre + k]
    return 1.0 - playing.sum() / scored.sum() if scored.sum() else 1.0


def longest_gap_s(dry, di, rate=NR.SR, c=CONTENT["judge-accepts"]):
    """judge-accepts (iii): the longest stretch where the DI plays (within PLAY_FLOOR_DB of its loudest 20-ms frame) and
    the dry guitar is `gap_db` or more under its own loudest."""
    n, h = int(CHECK_FRAME_S * rate), int(CHECK_HOP_S * rate)
    Ld, Lr = NR.frame_levels_db(di, n, h), NR.frame_levels_db(dry, n, h)
    k = min(len(Ld), len(Lr))
    if not k:
        return 0.0
    bad = (Ld[:k] >= Ld[:k].max() - PLAY_FLOOR_DB) & (Lr[:k] <= Lr[:k].max() - c["gap_db"])
    best = run = 0
    for v in bad:
        run = run + 1 if v else 0
        best = max(best, run)
    return 0.0 if not best else ((best - 1) * h + n) / rate


def judge_accepts(dry32, di32, lag, search, ref_blank=None, trim=None):
    """judge-accepts' figure on the trimmed timeline: (i) J0 on the search half with the dry guitar as DI and render
    against `ref_blank` (the stem zeroed outside the search half; None for items with no stem); (ii) the pause shares
    on each half and frame size, the dry guitar's and the true DI's; (iii) the longest gap."""
    import numpy as np

    from analysis import aligned as A

    from learn import knob_ceiling as K
    from learn import note_replay as R
    from learn import pretrain_set as PS

    trim = trim or (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    d = np.asarray(dry32, np.float64)[trim[0]:trim[1]]
    t = np.asarray(di32, np.float64)[trim[0]:trim[1]]
    fig = {"judge_finite": None}
    if ref_blank is not None:
        fig["judge_finite"] = bool(math.isfinite(R.half_distance(ref_blank, d, d, lag, search)))
    fig["pauses"] = {h: {str(n): {"dry": float(judge_pause_share(d, lag, h, n)),
                                  "true": float(judge_pause_share(t, lag, h, n))} for n in A.FRAME_SIZES}
                     for h in K.R.HALVES}
    fig["longest_gap_s"] = longest_gap_s(d, t)
    return fig


def ring_kept(dry, di, onsets, rate=NR.SR, c=CONTENT["ring-kept"]):
    """ring-kept's figure: (i) over 20-ms frames where the DI plays `after_s` or more after the last onset, the median
    of the dry guitar's level less the DI's, each against its own level in the `attack_s` after that onset; (ii)
    `note_rebuild.envelope_corr`."""
    import numpy as np

    n, h = int(CHECK_FRAME_S * rate), int(CHECK_HOP_S * rate)
    Ld, Lr = NR.frame_levels_db(di, n, h), NR.frame_levels_db(dry, n, h)
    k = min(len(Ld), len(Lr))
    ons = sorted(o for o in onsets if o >= 0)
    diffs = []
    if k:
        top = Ld[:k].max()
        for j in range(k):
            t = (j * h + n / 2) / rate
            prev = [o for o in ons if o <= t - c["after_s"]]
            if not prev or Ld[j] < top - PLAY_FLOOR_DB:
                continue
            if any(t - c["after_s"] < o <= t for o in ons):
                continue
            o = prev[-1]
            a, b = int(round(o * rate)), int(round((o + c["attack_s"]) * rate))
            ed = 20 * math.log10(NR.span_rms(di, a, b) + 1e-12)
            er = 20 * math.log10(NR.span_rms(dry, a, b) + 1e-12)
            diffs.append((Lr[j] - er) - (Ld[j] - ed))
    return {"late_frames": len(diffs), "late_median_db": float(np.median(diffs)) if diffs else None,
            "env_corr": NR.envelope_corr(np.asarray(di, np.float64), np.asarray(dry, np.float64))}


def pitch_class_cosine(a, b):
    """(Pure.) The cosine of two note lists' pitch-class counts (reported only)."""
    va, vb = [0.0] * 12, [0.0] * 12
    for n in a:
        va[n["pitch"] % 12] += 1
    for n in b:
        vb[n["pitch"] % 12] += 1
    na, nb = math.sqrt(sum(x * x for x in va)), math.sqrt(sum(x * x for x in vb))
    return sum(x * y for x, y in zip(va, vb)) / (na * nb) if na and nb else None


def chords_kept(round_trip, di_notes, c=CONTENT["chords-kept"]):
    """(Pure.) chords-kept's figure: Basic Pitch's notes on the dry guitar against the DI's: note F (onset `onset_s`),
    the recall of the DI's notes in onset groups of `chord_size` or more, and the pitch-class cosine (reported)."""
    m = match_notes(di_notes, round_trip, c["onset_s"])
    chord = set()
    for g in NR.onset_groups(di_notes):
        if len(g) >= c["chord_size"]:
            chord |= set(g)
    hit = len(chord & set(m["ref_matched"]))
    return {"f": m["f"], "precision": m["precision"], "recall": m["recall"], "chord_notes": len(chord),
            "chord_recall": hit / len(chord) if chord else None,
            "pitch_class_cosine": pitch_class_cosine(di_notes, round_trip)}


# --- the development windows and GOAT audio ------------------------------------------------------------------------------

def goat_audio(z, item):
    """A GOAT item's DI from the zip, mono at 48 kHz."""
    import io

    import soundfile as sf

    from learn import clean_di as CD

    x, sr = sf.read(io.BytesIO(z.read(f"GOAT/data/{item}/{item}.wav")), dtype="float64", always_2d=True)
    return CD.resample(x.mean(1), sr, NR.SR)


def goat_duration(z, item):
    """A GOAT item's DI length in seconds, from its WAV header."""
    import io

    import soundfile as sf

    return sf.info(io.BytesIO(z.read(f"GOAT/data/{item}/{item}.wav"))).duration


def probe_start(duration_s):
    """(Pure.) The probe's and the old clips' window start: 30 s into an item over 45 s long, else 1 s."""
    return 30.0 if duration_s > 45 else 1.0


def full_window(duration_s, start_s, sr=NR.SR):
    """(Pure.) The item holds the whole 10.25-s window from `start_s` (the probe's `len(raw) >= sec` at 48 kHz)."""
    from learn import pretrain_set as PS

    n = int(round((PS.SEC_S + PS.TRIM_S) * sr))
    return int(round(duration_s * sr)) >= int(round(start_s * sr)) + n


def dev_windows(z, excl, tn_items):
    """The 27 development windows (the stage-1 declaration's, by its rule): every GOAT item clear of the exclusion list
    with fine-aligned MIDI (true notes in stage P's record) and a full window at `probe_start`, in item order.
    -> [{item, start_s}] (refused unless DEV_COUNT)."""
    out = []
    for it in sorted(tn_items, key=lambda s: int(s.split("_")[1])):
        if NR.clear_of({"goat_item": it}, excl) or "notes_sha256" not in tn_items[it]:
            continue
        dur = goat_duration(z, it)
        st = probe_start(dur)
        if full_window(dur, st):
            out.append({"item": it, "start_s": st})
    if len(out) != DEV_COUNT:
        raise SystemExit(f"{len(out)} development windows, not the declared {DEV_COUNT}")
    NR.assert_clear([{"goat_item": w["item"]} for w in out], excl)
    return out


def window_audio(x, start_s, rate=NR.SR):
    """(The window's 10.25 s from `start_s`, the transcriber's input with up to MARGIN_S either side, pre_s)."""
    from learn import pretrain_set as PS

    n = int(round((PS.SEC_S + PS.TRIM_S) * rate))
    a = max(0.0, start_s - MARGIN_S)
    b = min(len(x) / rate, start_s + n / rate + MARGIN_S)
    return x[int(round(start_s * rate)):int(round(start_s * rate)) + n], x[int(round(a * rate)):int(round(b * rate))], \
        start_s - a


def dev_annotation(item, start_s, di):
    """A development window's GOAT annotation (stage P's fine-aligned true notes) as it is, on the window's timeline."""
    p = NR.OUT / "true-notes" / f"{item}.json"
    rec = json.loads(p.read_text())
    return [dict(n, bends=[]) for n in NR.window_notes(rec["notes"], start_s, len(di) / NR.SR)]


def annotated_notes(item):
    """A GOAT item's annotated notes (stage P's fine-aligned true notes) on the item's timeline, bend-free (the
    annotation carries none), or [] without an annotation (the ear kinds' amendment)."""
    p = NR.OUT / "true-notes" / f"{item}.json"
    if not p.exists():
        return []
    return [dict(n, bends=[]) for n in json.loads(p.read_text())["notes"]]


def dev_true_notes(item, start_s, di):
    """A development window's GOAT annotation (stage P's fine-aligned true notes) after the same onset steps."""
    w = dev_annotation(item, start_s, di)
    off = NR.coarse_offset(w, di)
    return NR.snap_onsets(NR.shifted_notes(w, off), di, NR.SNAP_S)[0]


# --- the known notes (the install gate's only truth with chords) ---------------------------------------------------------

def _seq(pitches, t0, step, dur):
    return [{"on": t0 + j * step, "off": t0 + j * step + dur, "pitch": p, "bends": []} for j, p in enumerate(pitches)]


def _chords(chords, t0, step, dur):
    return [{"on": t0 + j * step, "off": t0 + j * step + dur, "pitch": p, "bends": []}
            for j, ch in enumerate(chords) for p in ch]


KNOWN_NOTES = {         # ten made-up note lists, each inside 10 s: scales, chords of 3 to 6 notes, a let-ring arpeggio,
    # and a bend; played from the bank by `synthesise_redo`, each note cut at its note-off (`known_audio`)
    "scale-c-major": _seq([48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72], 0.5, 0.5, 0.45),
    "scale-e-minor-fast": _seq([52, 55, 57, 59, 62, 64, 67, 69, 71, 74, 76, 74, 71, 69, 67, 64, 62, 59, 57, 55, 52] * 2,
                               0.5, 0.18, 0.16),
    "chromatic-down": _seq(list(range(76, 52, -1)), 0.5, 0.3, 0.28),
    "chords-six": _chords([[40, 47, 52, 56, 59, 64], [45, 52, 57, 61, 64, 69], [40, 47, 52, 56, 59, 64]] * 2, 0.5, 1.5,
                          1.4),
    "chords-five": _chords([[45, 52, 57, 60, 64], [48, 52, 55, 60, 64], [43, 50, 55, 59, 62]] * 2, 0.5, 1.5, 1.4),
    "chords-four": _chords([[50, 57, 62, 66], [52, 55, 59, 64], [48, 55, 60, 64], [47, 54, 59, 62]] * 2, 0.5, 1.1,
                           1.0),
    "power-chords": _chords([[40, 47, 52], [43, 50, 55], [45, 52, 57], [47, 54, 59]] * 3, 0.5, 0.75, 0.6),
    "let-ring-arpeggio": [{"on": 0.5 + 0.4 * j, "off": 0.5 + 0.4 * j + 2.0, "pitch": p, "bends": []}
                          for j, p in enumerate([45, 52, 57, 60, 64, 60, 57, 52, 43, 50, 55, 59, 62, 59, 55, 50,
                                                 40, 47, 52, 55])],
    "triads-and-singles": _chords([[55, 59, 62], [57, 60, 64], [59, 62, 67]], 0.5, 2.0, 0.9)
    + _seq([67, 69, 71, 72, 74, 72, 71, 69], 1.6, 1.0, 0.35),
    "bend": [{"on": 0.5 + 2.0 * j, "off": 0.5 + 2.0 * j + 1.5, "pitch": p,
              "bends": [0] * 20 + [min(6, k // 3) for k in range(18)] + [6] * 60} for j, p in enumerate([64, 67, 69])]
    + _seq([60, 62, 64, 65], 6.5, 0.7, 0.5),
}


def known_audio(name, bank, rate=NR.SR):
    """A known list played from the bank, each note cut at its declared note-off (`cut`: no note sounds past its
    declared end; amended 2026-11-22, `phase_nr_1_redo_known_amend`, after the first gate's lists rang on past their
    note-offs under ring-on), no mutes or tilt, at -22.9 LUFS, 10.25 s. Two known gaps (plan section 12l): the first A
    chord of `chords-six` leaves no string for its 69, and the bend list's bends end about 0.36 s before its
    note-offs."""
    from learn import pretrain_set as PS

    n = int(round((PS.SEC_S + PS.TRIM_S) * rate))
    y, _ = NR.synthesise_redo(KNOWN_NOTES[name], n, bank, 0.0, "ring-on", (), 0.0, None, rate, cut=True)
    return NR.at_lufs(y, NR.ASSUMED_LUFS, rate)


# --- the commands ------------------------------------------------------------------------------------------------------------

def listing_text(rows):
    """(Pure.) `shasum -a 256` lines for [(relative path, sha256)], sorted by "./<path>"."""
    return "".join(f"{s}  ./{r}\n" for r, s in sorted(rows, key=lambda q: "./" + q[0]))


def listing_sha(rows):
    """(Pure.) The sha256 of a folder's `listing_text` (the stage-1 hand-back's dist list sha256)."""
    return NR.bytes_sha(listing_text(rows).encode())


def cmd_set_aside(_args):
    """Step 2 (zero renders): stage 1's di/ hashed first (`listing_sha` of its files), the dist/ list checked against
    the hand-back's (DIST_LIST_SHA), then dist/, di/ and build.json moved (never deleted, never read) to
    stage1.set-aside-20261122/ with a note: "unread: no pick, no score". subset.json stays. -> the hashes printed."""
    require_redo()
    never_overwrite(SET_ASIDE)

    def listing(d):
        return [(str(p.relative_to(d)), NR.file_sha(p)) for p in sorted(d.rglob("*")) if p.is_file()]
    di, dist = listing(STAGE1 / "di"), listing(STAGE1 / "dist")
    di_sha, dist_sha = listing_sha(di), listing_sha(dist)
    if dist_sha != DIST_LIST_SHA:
        raise SystemExit("stage1/dist is not the list the render hand-back hashed")
    build_sha = NR.file_sha(STAGE1 / "build.json")
    SET_ASIDE.mkdir(parents=True)
    for name in ("dist", "di", "build.json"):
        os.rename(STAGE1 / name, SET_ASIDE / name)
    NR.write_once(SET_ASIDE / "README.json", {"note": SET_ASIDE_NOTE, "plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}",
                                              "di_files": len(di), "di_list_sha256": di_sha,
                                              "dist_files": len(dist), "dist_list_sha256": dist_sha,
                                              "build_sha256": build_sha, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"SET ASIDE: di {len(di)} files, list sha256 {di_sha}; dist {len(dist)} files, list sha256 {dist_sha}; "
          f"build.json {build_sha} -> {SET_ASIDE}")


def cmd_install(args):
    """Step 3 (a declared download): the venv from /usr/bin/python3 (or `--interpreter`, the declared 3.11 fallback,
    whose onnxruntime pin is ONNXRUNTIME_CP311; no other version is accepted), pip upgraded by its hashed pin, the lock made by
    `pip install --dry-run --ignore-installed --only-binary :all: --report` over REQUIREMENTS (basic-pitch's own list
    without coremltools) with the basic-pitch wheel added, then `pip install --require-hashes --only-binary :all:
    --no-deps -r requirements.lock`; the manifest (every file, the lock's and the model's sha256, resolve.json, the
    Python version, the installed size, the date). Refuses under INSTALL_MIN_GB free. A package with no wheel stops
    here: the declared sdist build (`--no-build-isolation`, setuptools and wheel hashed in the lock) is its own step."""
    import shutil
    import subprocess
    import sys

    require_redo()
    never_overwrite(TOOLS)
    from learn import pretrain_set as PS

    if PS.free_gb() < INSTALL_MIN_GB:
        raise SystemExit(f"DISK GUARD: under {INSTALL_MIN_GB:.0f} GB free; the install refuses")

    def run(*a):
        r = subprocess.run([str(x) for x in a], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"{' '.join(map(str, a))[:120]}: {r.stderr.strip()[-600:]}")
        return r.stdout
    interp = getattr(args, "interpreter", None) or INTERPRETER
    minor = run(interp, "-c", "import sys; print('%d.%d' % sys.version_info[:2])").strip()
    if minor not in ONNX_PIN:
        raise SystemExit(f"{interp} is Python {minor}: only 3.9 (declared) or 3.11 (the declared fallback)")
    onnx = ONNX_PIN[minor]
    run(interp, "-m", "venv", TOOLS)
    pip = TOOLS / "bin" / "pip"
    pin = TOOLS / "pip-pin.txt"
    pin.write_text(f"{PIP_PIN[0]}=={PIP_PIN[1]} --hash=sha256:{PIP_PIN[2]}\n")
    run(BP_PYTHON, "-m", "pip", "install", "--require-hashes", "--only-binary", ":all:", "-r", pin)
    run(pip, "install", "--dry-run", "--ignore-installed", "--only-binary", ":all:", "--report", RESOLVE,
        *REQUIREMENTS)
    text = lock_lines(json.loads(RESOLVE.read_text()), [BASIC_PITCH[:3]])
    why = lock_refusal(text, onnx)
    if why:
        raise SystemExit(f"the lock: {why}")
    LOCK.write_text(text)
    run(pip, "install", "--require-hashes", "--only-binary", ":all:", "--no-deps", "-r", LOCK)
    site = pathlib.Path(run(BP_PYTHON, "-I", "-c", "import basic_pitch, os; print(os.path.dirname("
                            "os.path.dirname(basic_pitch.__file__)))").strip())
    model = site / MODEL_IN_WHEEL
    run(BP_PYTHON, "-I", "-c", "import pretty_midi, mir_eval, onnxruntime, basic_pitch")
    files = [{"path": str(p.relative_to(TOOLS)), "size": p.stat().st_size, "sha256": NR.file_sha(p)}
             for p in sorted(TOOLS.rglob("*")) if p.is_file() and not p.is_symlink() and "__pycache__" not in p.parts]
    man = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "made": time.strftime("%Y-%m-%d %H:%M:%S"),
           "interpreter": interp, "python": run(BP_PYTHON, "-c", "import sys; print(sys.version)").strip(),
           "lock_sha256": NR.file_sha(LOCK), "resolve_sha256": NR.file_sha(RESOLVE), "model_path": str(model),
           "model_sha256": NR.file_sha(model), "pip_pin": list(PIP_PIN), "requirements": list(REQUIREMENTS),
           "installed_bytes": sum(f["size"] for f in files), "files": files,
           "medleydb_index_sha256": NR.file_sha(MEDLEYDB_INDEX) if MEDLEYDB_INDEX.exists() else None,
           "approval": "the user's three answers, 2026-11-22 (AskUserQuestion), recorded in phase_nr_1_redo",
           "licences": "basic-pitch Apache-2.0; onnxruntime MIT; the rest from each wheel's metadata (resolve.json)",
           "host_python": sys.version.split()[0], "free_gb_after": PS.free_gb(),
           "disk_total_gb": shutil.disk_usage(str(TOOLS)).total / 1e9}
    NR.write_once(MANIFEST, man)
    print(f"INSTALL DONE: lock {man['lock_sha256']}, model {man['model_sha256']}, {man['installed_bytes'] / 1e6:.0f} MB"
          f", {man['free_gb_after']:.1f} GB free")


def _dev_context():
    import csv
    import io
    import zipfile

    excl = NR.load_exclusion()
    tn = NR.load_doc("true-notes.json")
    z = zipfile.ZipFile(NR.GOAT_ZIP)
    meta = {r["item"]: r for r in csv.DictReader(io.StringIO(z.read("GOAT/metadata.csv").decode()))}
    return excl, tn, z, meta


def cmd_install_gate(_args):
    """Step 3, the install gate (zero renders): repeatable (REPEAT_WINDOWS development windows, three runs each: two
    in one process, one in a fresh one, identical events), the known notes (the ten KNOWN_NOTES lists played from the
    bank and transcribed: pooled note F at least KNOWN_F, each list reported), the seconds per 10-s window. Refuses
    when install-gate.json or its raw-event folder (`gate_work_dir`) exists: a rerun never overwrites a run's evidence
    (both are moved aside first, never deleted; amendment `phase_nr_1_redo_known_amend`).
    -> redo/install-gate.json (its facts go into phase_nr_1_redo_install), redo/work/install-gate/."""
    require_redo()
    never_overwrite(gate_path())
    never_overwrite(gate_work_dir())
    excl, tn, z, _ = _dev_context()
    wins = read_dev_windows(dev_windows(z, excl, tn["items"]))[:REPEAT_WINDOWS]   # 12p: item_5 out
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    work = gate_work_dir()
    ins = []
    for w in wins:
        x = goat_audio(z, w["item"])
        _, inp, _ = window_audio(x, w["start_s"])
        ins.append((inp, w["item"]))
    t0 = time.perf_counter()
    a = run_bp([j for j in ins for _ in (0, 1)], work / "one-process")
    secs = (time.perf_counter() - t0) / (2 * len(ins))
    b = run_bp(ins, work / "fresh")
    repeat = {w["item"]: repeat_identical([a[2 * i]["events"], a[2 * i + 1]["events"], b[i]["events"]])
              for i, w in enumerate(wins)}
    res = {}
    names = sorted(KNOWN_NOTES)
    bp = run_bp([(known_audio(nm, bank), nm) for nm in names], work / "known")
    for nm, r in zip(names, bp):
        est, _ = clean_transcribed(notes_from_events(r["events"]))
        truth = [dict(n) for n in KNOWN_NOTES[nm]]
        res[nm] = match_notes(truth, est, KNOWN_ONSET_S)
    f = pooled_f(list(res.values()))
    body = {"repeat": repeat, "repeat_ok": all(repeat.values()), "known": res, "known_f": f,
            "known_ok": f is not None and f >= KNOWN_F, "seconds_per_window": secs,
            "manifest_sha256": NR.file_sha(MANIFEST), "pair": list(install_pair(load_manifest()))}
    body["ok"] = gate_passes(body)        # 12m: the gate passes on repeatability; known F is a reported figure
    NR.write_once(gate_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}",
                                "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    print(f"INSTALL GATE {'PASS' if body['ok'] else 'FAIL'}: repeat {body['repeat']}; known F {f}; "
          f"{secs:.2f} s a window; sha256 {NR.file_sha(gate_path())}")


def _avg_mild(di, key, others):
    import random as _r

    from learn import di_robustness as DR

    return DR.degrade("mild", key, DR.average_balance(di, others), others, _r.Random(f"{DEV_BLUR_SEED}|mild|{key}"))


def dev_others_maker():
    """The positive control's other guitars for a development window, as a function of its key: `note_replay.
    others_for` over the replay's drawn parts from every source but GOAT's (a development item's player is not
    checked against GOAT's), seeded by the window (DEV_BLUR_SEED); each DI section read once."""
    import numpy as np

    from learn import note_replay as R

    draw = R.require_draw()
    sd = R.Stored()
    by_sec = {p["section"]: sd.units[(p["set"], p["unit"], p["amp"])]["prt"] for p in draw["parts"]}
    pool = [p for p in draw["parts"] if not p["source"].startswith("GOAT")]
    cache = {}

    def sec(s):
        if s not in cache:
            cache[s] = np.asarray(R.di_section(by_sec[s]), np.float64)
        return cache[s]

    def others(key):
        oth = R.others_for({"pkey": key, "source": "GOAT development"}, pool, seed=DEV_BLUR_SEED)
        return {s: [sec(x) for x in xs] for s, xs in oth.items()}
    return others


def cmd_calibrate(_args):
    """Step 7 of note-rebuild-plan 12m (zero renders), once, after the install gate passed (on repeatability), the
    detector's report and the note-versions read, with the adopted synthesis (`versions_loud`): on the 27 development
    windows, the DI's transcription; `playing-covered` (the declared pass rate, 25 of 27) and `onsets-found` (a report:
    the flux detector after the P1 offset, flagged under 0.90); `annotated-found` on the top-tertile windows its
    consistency test admits; the ring variant (`ring_choice` on tr-di's `envelope_corr`); and the checks' test: avg+mild
    and the true DI must pass every audio check, and each clip the user rejected is placed by `clip_case` (caught by a
    blocking check; caught by a report only: recorded, the user told, the work goes on; caught by no check: the user's
    go first, `PHASE_GO_CLIPS`). As fixed (`PHASE_CALIB_FIX`, 2026-11-23): the round trips on the DI notes' timeline
    (`round_trip_notes`), `annotated-found` a report, a check the positive control fails made report-only
    (`positive_report_only`, only under the user's go `PHASE_GO_GUARD`), `playing-covered` reported under the
    user's go; runs only as the one rerun
    (`calib_rerun_refusal`). -> redo/calibration.json (its facts go into phase_nr_1_redo_install)."""
    m = require_redo(PHASE_EAR_OLD, PHASE_CALIB, PHASE_TRUTH, PHASE_CALIB_FIX, PHASE_GO_CALIB, PHASE_GO_GUARD)
    aside = CALIB_ASIDE / "calibration.json"
    why = calib_rerun_refusal(m.get(LEDGER_ID), NR.file_sha(aside) if aside.exists() else None,
                              (CALIB_ASIDE / "work-calibrate").is_dir())
    if why:
        raise SystemExit(why)
    never_overwrite(calibration_path())
    never_overwrite(REDO / "work" / "calibrate")
    gate = json.loads(gate_path().read_text())["body"] if gate_path().exists() else None
    if not gate_passes(gate):
        raise SystemExit("the install gate has not passed (repeatability)")
    loud, why = versions_loud(m.get(LEDGER_ID))
    if why:
        raise SystemExit(why)
    offset = require_attacks()["offset_s"]
    expected = ear_old_table(m.get(LEDGER_ID))
    import numpy as np

    from learn import note_attacks as NA
    from learn import song_bank as SB

    excl, tn, z, meta = _dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    wins = read_dev_windows(dev_windows(z, excl, tn["items"]))   # 12p: item_5 out, 26 windows
    work = REDO / "work" / "calibrate"
    dis, ins = {}, []
    for w in wins:
        x = goat_audio(z, w["item"])
        sec, inp, pre = window_audio(x, w["start_s"])
        dis[w["item"]] = SB.measure(sec)
        ins.append((inp, w["item"], pre))
    bp = run_bp([(i, t) for i, t, _ in ins], work / "di")
    att = NA.run_attacks(ins, work / "attacks")
    rows, notes_of = {}, {}
    for (_, it, pre), r, a in zip(ins, bp, att):
        di = dis[it]
        notes, rep = timed_notes({"events": r["events"], "pre_s": pre}, di)
        notes_of[it] = notes
        st = next(w["start_s"] for w in wins if w["item"] == it)
        raw = dev_annotation(it, st, di)
        ann = dev_true_notes(it, st, di)
        rows[it] = {"timing": rep, "alignment_f": tn["items"][it].get("alignment_f"),
                    "consistent": annotation_consistent(raw, di)["consistent"],
                    "admission": annotation_consistent(raw, di),
                    "recall": match_notes(ann, notes, CONTENT["annotated-found"]["onset_s"])["recall"],
                    "onsets_found": attacks_found(a, notes, di, offset), "playing_covered": playing_covered(notes, di)}
    covered = sum(bool(playing_covered_pass(r["playing_covered"])) for r in rows.values())
    flagged = sorted(it for it, r in rows.items() if r["onsets_found"]["flag"])
    af = annotated_found_pass([dict(r, item=it) for it, r in rows.items()])
    corr, audio = {v: [] for v in NR.RING_VARIANTS}, {}
    rt_jobs = []
    dev_others = dev_others_maker()
    for w in wins:
        it, di = w["item"], dis[w["item"]]
        key = f"dev|{it}"
        drys = {}
        for v in NR.RING_VARIANTS:
            drys[v], _ = NR.rebuild_redo("tr-di", notes_of[it], len(di), bank, di, v, finish=SB.measure, loud=loud)
            corr[v].append(NR.envelope_corr(np.asarray(di, np.float64), drys[v]))
        drys["avg+mild"] = np.asarray(_avg_mild(di, key, dev_others(key)), np.float64)
        drys["true"] = np.asarray(di, np.float64)
        audio[it] = drys
        rt_jobs += [(y, f"{it}-{d}") for d, y in drys.items()]
    ring = ring_choice(corr["ring-on"], corr["ring-soft"])
    rt = run_bp(rt_jobs, work / "round-trip")
    checks, j = {}, 0
    for w in wins:
        it, di = w["item"], dis[w["item"]]
        for d, y in audio[it].items():
            got = round_trip_notes(rt[j]["events"], y)
            j += 1
            figs = {"judge-accepts": judge_accepts(y, di, 0, "A"), "ring-kept": ring_kept(y, di, [n["on"] for n in
                                                                                             notes_of[it]]),
                    "chords-kept": chords_kept(got, notes_of[it])}
            checks.setdefault(d, {})[it] = {"figures": figs, **check_verdict(figs, AUDIO_CHECKS)}
    positive = {d: sorted(it for it, r in checks[d].items() if r["failed"]) for d in ("avg+mild", "true")}
    report_only, still_blocking = positive_report_only(positive_failing(checks), m.get(LEDGER_ID), NR.file_sha(aside))
    blocking = effective_blocking({"report_only_checks": report_only}, m.get(LEDGER_ID))
    neg = negative_control(expected, bank, z, meta, excl, offset, work)
    results = {c: r["passes"] for c, r in neg.items()}
    cases = clip_case(expected, results, blocking)
    body = {"windows": [w["item"] for w in wins], "rows": rows, "playing_covered_windows": covered,
            "onsets_found_flagged": flagged, "detector_offset_s": offset, "annotated_found": af,
            "ring_corr": corr, "ring_variant": ring, "loud_gamma": loud, "checks": checks, "positive_failures": positive,
            "negative": neg, "clip_cases": cases, "blind_spots": expected_failure_refusal(expected, results),
            "report_only_checks": report_only, "positive_still_blocking": still_blocking,
            "blocking_checks": sorted(blocking),
            "playing_covered_reported": "playing-covered" not in blocking,
            "first_run_sha256": NR.file_sha(aside),
            "gate_sha256": NR.file_sha(gate_path()), "attacks_sha256": NR.file_sha(attacks_path())}
    body["ok"] = calibration_ok(covered, cases, PHASE_GO_CLIPS in (m.get(LEDGER_ID) or {}),
                                need=DEV_READ_COUNT - CALIBRATION_FAIL_ALLOWED,       # 24 of 26 (12p)
                                covered_reported=body["playing_covered_reported"], positive_blocking=still_blocking)
    NR.write_once(calibration_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_CALIB}",
                                       "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    print(f"CALIBRATE {'PASS' if body['ok'] else 'STOP'}: blocking {sorted(blocking)}, report-only {report_only}; "
          f"playing-covered {covered} of {len(wins)}; onsets-found "
          f"flags {flagged}; annotated-found {af}; ring {ring}; positive failures {positive}; clips {cases}; "
          f"sha256 {NR.file_sha(calibration_path())}")


def negative_control(expected, bank, z, meta, excl, offset, work):
    """The checks on the clips the user rejected: each old clip's dry guitar rebuilt in memory as `note_rebuild_s1
    clips` built it (GOAT's true notes, the two-stage oracle onset step, `rebuild_dry` with `song_bank.measure`), its
    notes (the old ones) through the note checks (`onsets-found` by the flux detector, a report), its audio through the
    audio checks. clip keys: "<item>|<arm>". -> {clip: {passes, failed, figures}}."""
    import numpy as np

    from learn import note_attacks as NA
    from learn import song_bank as SB

    out, jobs, built, ajobs = {}, [], {}, []
    for e in expected:
        it, arm = e["clip"].split("|")[:2]
        x = goat_audio(z, it)
        st = probe_start(len(x) / NR.SR)
        sec, inp, pre = window_audio(x, st)
        di = SB.measure(sec)
        rec = NR.true_notes_for(it, z, meta)
        wn = NR.window_notes(rec["notes"], st, len(di) / NR.SR)
        notes, _ = NR.refine_onsets(NR.shifted_notes(wn, NR.coarse_offset(wn, di)), di)
        y, _ = NR.rebuild_dry(arm, notes, len(di), bank, di, finish=SB.measure)
        built[e["clip"]] = (di, notes, np.asarray(y, np.float64))
        jobs.append((y, e["clip"].replace("|", "-")))
        ajobs.append((inp, e["clip"].replace("|", "-"), pre))
    rt = run_bp(jobs, work / "rejected") if jobs else []
    att = NA.run_attacks(ajobs, work / "rejected-attacks") if ajobs else []
    for (clip, (di, notes, y)), r, a in zip(built.items(), rt, att):
        got = round_trip_notes(r["events"], y)
        figs = {"onsets-found": attacks_found(a, notes, di, offset), "playing-covered": playing_covered(notes, di),
                "judge-accepts": judge_accepts(y, di, 0, "A"), "ring-kept": ring_kept(y, di, [n["on"] for n in notes]),
                "chords-kept": chords_kept(got, [dict(n, bends=[]) for n in notes])}
        out[clip] = {"figures": figs, **check_verdict(figs)}
    return out


def require_install_facts():
    """The install gate's and the calibration's records, both passed (steps 5 and after read them; their sha256 go into
    phase_nr_1_redo_install with the hash PR). -> (gate body, calibration body)."""
    for p in (gate_path(), calibration_path()):
        if not p.exists():
            raise SystemExit(f"{p.name} missing: run step 3 first")
    g, c = (json.loads(p.read_text())["body"] for p in (gate_path(), calibration_path()))
    if not gate_passes(g):                       # 12q R1: the calibration is a report; repeatability stays
        raise SystemExit("the install gate did not pass (repeatability)")
    if c["gate_sha256"] != NR.file_sha(gate_path()):
        raise SystemExit("calibration.json was made from another install gate")
    return g, c


def ruled_out_items(units):
    """(Pure.) The ruled-out GOAT items among unit ids or items ("goat/item_5@10.0#amp_3", "item_5"). -> sorted."""
    out = set()
    for u in units:
        it = str(u).split("/", 1)[1] if str(u).startswith("goat/") else str(u)
        it = it.split("@", 1)[0].split("#", 1)[0]
        if it in RULED_OUT:
            out.add(it)
    return sorted(out)


def ruled_out_refusal(units, what):
    """(Pure.) Why `what` may not be read, or None: it holds a DI the user ruled out (`RULED_OUT`)."""
    bad = ruled_out_items(units)
    return f"{what} holds {bad}, which the user ruled out (\"Bad DI, don't use it\"; 12p)" if bad else None


def read_dev_windows(windows, count=DEV_READ_COUNT):
    """(Pure.) The development windows a later read uses (12p): `dev_windows`' 27 less the ruled-out items, refused
    unless `count` remain. Made records (the gates, both calibrations, the truth report, the versions read, stage b's
    note files) keep their 27."""
    out = [w for w in windows if w["item"] not in RULED_OUT]
    if len(out) != count:
        raise SystemExit(f"{len(out)} development windows to read, not the declared {count}")
    return out


def read_version_windows(vwindows):
    """(Pure.) versions.json's stored windows a later read uses (12p): GOAT's windows less the ruled-out items, on
    both sides of every comparison (the stored and the newly built distances alike); the lists and the real set as
    stored."""
    return [w for w in vwindows if not (w.get("set") == "goat" and w.get("key") in RULED_OUT)]


def row_parts():
    """The row's 47 parts from the from-scratch search's hashed draw, with each part's replay record and stored C3r
    unit. -> (draw, replay parts by key, Stored)."""
    from learn import note_replay as R
    from learn import scratch_search as S

    draw = S.require_draw()
    why = ruled_out_refusal([p["unit"] for p in draw["parts"]], "the row's draw")
    if why:
        raise SystemExit(why)
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    return draw, {p["pkey"]: p for p in R.require_draw()["parts"]}, sd


def cmd_transcribe(_args):
    """Step 5 (zero renders): Basic Pitch on each of the 47 parts' raw DI sections (with up to MARGIN_S either side)
    and on the 8 ear items' windows (the 4 the user heard, at their old windows; 4 new by `pick_ear_items` from a
    whole-item scan, at `grid_window`); each note file written once with the install's pair; the note checks
    (`playing-covered`, blocking; `onsets-found`, a report since 12m: the flux detector after the P1 offset) and, on
    GOAT parts, `annotated-found`'s recall, reported. Refuses while the truth report's P2 chord recall is under 0.85
    without the user's go (`chords_go_refusal`). The flagged-parts trigger is counted straight after: flags on 3 or
    more of the 40 deciding parts go to the user before any build (`flags_go_refusal`, read by `build`).
    -> redo/notes/<kind>/<key>.json, redo/ear-items.json, redo/transcribe.json."""
    m = require_redo(PHASE_CALIB, PHASE_TRUTH)
    _, cal = require_install_facts()
    pair = install_pair(load_manifest())
    report = require_truth_report(m.get(LEDGER_ID))
    why = ledger_pair_refusal(m.get(LEDGER_ID), pair) or chords_go_refusal(p2_chord_recall(report), m.get(LEDGER_ID))
    if why:
        raise SystemExit(why)
    never_overwrite(transcribe_path())
    import numpy as np

    from learn import note_attacks as NA
    from learn import note_replay as R
    from learn import song_bank as SB

    draw, rby, sd = row_parts()
    work = REDO / "work" / "transcribe"
    offset = require_attacks()["offset_s"]
    jobs, meta_of = [], []
    for p in sorted(draw["parts"], key=lambda p: p["pkey"]):
        never_overwrite(note_path("part", p["pkey"]))
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        x, pre = padded_section(prt)
        jobs.append((x, "part"))
        meta_of.append(("part", p["pkey"], pre, {"set": p["set"], "section": p["section"]}))
    excl, tn, z, meta = _dev_context()
    old = sorted({c["item"] for c in json.loads((NR.HOME / "listening/note-rebuild-ear/index.json")
                                                .read_text())["clips"]})
    if len(old) != OLD_EAR_ITEMS:
        raise SystemExit(f"the old page has {len(old)} items, not {OLD_EAR_ITEMS}")
    pool = sorted((it for it in meta if not NR.clear_of({"goat_item": it}, excl) and it not in old
                   and it not in RULED_OUT),                       # 12p: a ruled-out DI is never an ear candidate
                  key=lambda s: int(s.split("_")[1]))
    NR.assert_clear([{"goat_item": it} for it in pool + old], excl)
    order = list(pool)
    random.Random(f"{EAR_SEED}|ear-items").shuffle(order)
    scans = run_bp([(goat_audio(z, it), "scan") for it in order], work / "scan")
    kinds, starts, kind_figs, kinds_ann, starts_ann, figs_ann = {}, {}, {}, {}, {}, {}
    for it, r in zip(order, scans):
        dur = goat_duration(z, it)
        notes, _ = clean_transcribed(notes_from_events(r["events"]))
        st = grid_window(notes, dur)
        if st is not None:
            starts[it] = st
            w = [dict(n, on=n["on"] - st - 0.25, off=n["off"] - st - 0.25) for n in notes
                 if st + 0.25 <= n["on"] < st + 10.25]
            kinds[it], kind_figs[it] = kind_flags(w), kind_figures(w)
        ann = annotated_notes(it)                     # the ear kinds' amendment: single-note from the annotation
        sa = grid_window(ann, dur) if ann else None
        if sa is not None:
            starts_ann[it] = sa
            wa = [dict(n, on=n["on"] - sa - 0.25, off=n["off"] - sa - 0.25) for n in ann
                  if sa + 0.25 <= n["on"] < sa + 10.25]
            kinds_ann[it], figs_ann[it] = kind_flags(wa), kind_figures(wa)
    new, chosen = choose_ear_kinds(order, kinds, kinds_ann, kind_figs, figs_ann)
    start_of = {k: (starts_ann if chosen[k]["source"] == "annotation" else starts)[new[k]] for k in KINDS}
    ear = [{"item": it, "start_s": probe_start(goat_duration(z, it)), "kind": None, "old": True}
           for it in old] + [{"item": new[k], "start_s": start_of[k], "kind": k, "kind_label": chosen[k]["label"],
                              "kind_filled": chosen[k]["filled"], "old": False} for k in KINDS]
    for e in ear:
        never_overwrite(note_path("ear", e["item"]))
        x = goat_audio(z, e["item"])
        _, inp, pre = window_audio(x, e["start_s"])
        jobs.append((inp, "ear"))
        meta_of.append(("ear", e["item"], pre, {"start_s": e["start_s"]}))
    bp = run_bp(jobs, work / "notes")
    att = NA.run_attacks([(x, tag, mo[2]) for (x, tag), mo in zip(jobs, meta_of)], work / "attacks")
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "pair": list(pair), "detector_offset_s": offset,
           "parts": {}, "ear": {}, "calibration_sha256": NR.file_sha(calibration_path()),
           "attacks_sha256": NR.file_sha(attacks_path()), "truth_report_sha256": NR.file_sha(truth_report_path())}
    for (kind, key, pre, info), r, a in zip(meta_of, bp, att):
        rec = note_record(r, pre, info)
        NR.write_once(note_path(kind, key), rec)
        if kind == "part":
            p = next(q for q in draw["parts"] if q["pkey"] == key)
            di = np.asarray(R.di_section(sd.units[(p["set"], p["unit"], p["amp"])]["prt"]), np.float64)
        else:
            e = next(q for q in ear if q["item"] == key)
            di = SB.measure(window_audio(goat_audio(z, key), e["start_s"])[0])
        notes, rep = timed_notes(rec, di)
        figs = {"onsets-found": attacks_found(a, notes, di, offset), "playing-covered": playing_covered(notes, di)}
        row = {"note_file_sha256": NR.file_sha(note_path(kind, key)), "timing": rep, "figures": figs,
               **check_verdict(figs, NOTE_CHECKS, effective_blocking(cal, m.get(LEDGER_ID)))}
        if kind == "part" and info["set"] == "goat":
            it = p["unit"].split("/", 1)[1].split("@", 1)[0]
            tp = NR.OUT / "true-notes" / f"{it}.json"
            if tp.exists():
                w0 = float(p["section"].rsplit("@", 1)[1]) - 0.25
                raw = NR.window_notes(json.loads(tp.read_text())["notes"], w0, len(di) / NR.SR)
                ann = NR.snap_onsets(NR.shifted_notes(raw, NR.coarse_offset(raw, di)), di)[0]
                row["annotated_found"] = {"recall": match_notes(ann, notes, CONTENT["annotated-found"]["onset_s"])[
                    "recall"], "consistent": annotation_consistent(raw, di)["consistent"]}
        (out["parts"] if kind == "part" else out["ear"])[key] = row
    out["ear_items"] = ear
    NR.write_once(ear_items_path(), {"plan": PLAN, "items": ear, "kinds_scanned": {k: sorted(v) for k, v in
                                                                                     kinds.items()},
                                     "kinds_annotated": {k: sorted(v) for k, v in kinds_ann.items()},
                                     "figures": kind_figs, "figures_annotated": figs_ann, "chosen": chosen,
                                     "ledger": f"{LEDGER_ID} {PHASE_EAR_KINDS}", "order_seed": EAR_SEED})
    out["ear_kinds"] = chosen
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    dec, pan, stop = refusal_count(out["parts"], sets_of)
    fl = flagged_parts(out["parts"], sets_of)
    out.update(note_refused_deciding=dec, note_refused_panel=pan, stopped=stop,
               ear_failing=sorted(k for k, r in out["ear"].items() if r["failed"]),
               onsets_flagged_deciding=fl[0], onsets_flagged_panel=fl[1],
               flags_trigger=len(fl[0]) >= FLAG_TRIGGER)
    NR.write_once(transcribe_path(), out)
    print(f"TRANSCRIBE: {len(out['parts'])} parts, {len(out['ear'])} ear items; note-check refusals deciding "
          f"{len(dec)} {sorted(dec)}{' (STOPPED: no render)' if stop else ''}, panel {sorted(pan)}; ear failing "
          f"{out['ear_failing']}; onsets-found flags deciding {len(fl[0])}"
          f"{flags_note(fl[0], m.get(LEDGER_ID))}, panel {len(fl[1])}; "
          f"sha256 {NR.file_sha(transcribe_path())}")


def build_loudness(loud, fixes):
    """(Pure.) The loudness a build plays: the versions read's (`versions_loud`) unless a later build's `fixes` name
    its own (`"loud"`: None for none, or a gamma above zero; 12s). -> (gamma or None, refusal or None)."""
    if "loud" not in (fixes or {}):
        return loud, None
    g = fixes["loud"]
    if g is None:
        return None, None
    if isinstance(g, bool) or not isinstance(g, (int, float)) or not g > 0:
        return None, f"the build's loudness {g!r} is not None or a gamma above zero"
    return float(g), None


def build_todo(pair=None, ear_file=None):
    """The build's items in its order (also the fixes' identity check, `note_fixes`): the 47 parts (each with its
    finish: `song_bank.measure`, then `average_balance` with `note_replay.others_for`'s others, as row (c)'s avg+mild)
    and the ear items (finish: `song_bank.measure`). -> [(kind, key, info, note record, DI, finish)]."""
    import numpy as np

    from learn import di_robustness as DR
    from learn import note_replay as R
    from learn import song_bank as SB

    pair = pair or install_pair(load_manifest())
    draw, rby, sd = row_parts()
    _, _, z, _ = _dev_context()
    rparts = list(rby.values())                   # the replay's drawn parts (the others' pool, as row (c)'s blur)
    by_sec = {}
    for p in rparts:
        by_sec.setdefault(p["section"], sd.units[(p["set"], p["unit"], p["amp"])]["prt"])
    cache = {}

    def sec(s):
        if s not in cache:
            cache[s] = np.asarray(R.di_section(by_sec[s]), np.float64)
        return cache[s]
    todo = []
    for p in sorted(draw["parts"], key=lambda p: p["pkey"]):
        rec = load_note("part", p["pkey"], pair)
        di = sec(p["section"])
        others = {s: [sec(x) for x in xs] for s, xs in R.others_for(rby[p["pkey"]], rparts).items()}

        def finish(y, others=others):
            return DR.average_balance(SB.measure(y), others)
        todo.append(("part", p["pkey"], p, rec, di, finish))
    for e in json.loads((ear_file or ear_items_path()).read_text())["items"]:
        rec = load_note("ear", e["item"], pair)
        di = SB.measure(window_audio(goat_audio(z, e["item"]), e["start_s"])[0])
        todo.append(("ear", e["item"], e, rec, di, SB.measure))
    return todo


def merge_kind_figures(figs_tr, figs_ann):
    """(Pure.) Each kind's figure from its own source (12n): the annotated kinds (`ANNOTATED_KINDS`) from the
    annotation's figures, every other kind from the transcription's. Only items with a scan window (keys of
    `figs_tr`) are covered; an item without one has no figure. -> {item: {kind: figure}}."""
    return {it: {**{k: v for k, v in (figs_ann.get(it) or {}).items() if k in ANNOTATED_KINDS},
                 **{k: v for k, v in f.items() if k not in ANNOTATED_KINDS}} for it, f in figs_tr.items()}


def replace_ruled_out_kinds(order, ear, figs, kinds_of, exclude=()):
    """(Pure.) A later page's ear items (12q; #581's nit): the first page's items kept, each new item that is a
    ruled-out DI replaced for its kind by the first item in the seeded `order` (ruled-out items dropped) that shows
    the kind and is not already on the page, else its nearest by the kind's own figure (`nearest_fill`).
    ear: the first page's items; figs/kinds_of: the kind figures and kinds by item (from the kind's own source).
    `exclude`: items never drawn (12q: D's 19 development windows, so the new page never hears an item the fixes
    were picked on). -> (items, replacements)."""
    keep = [e for e in ear if e["old"] or e["item"] not in RULED_OUT]
    order = [it for it in order if it not in RULED_OUT and it not in set(exclude)]
    out, repl = [dict(e) for e in keep], {}
    for e in ear:
        if e["old"] or e["item"] not in RULED_OUT:
            continue
        k = e["kind"]
        used = {x["item"] for x in out}
        it = next((i for i in order if i not in used and k in (kinds_of.get(i) or set())), None)
        if it is not None:
            rec = {"kind": k, "item": it, "filled": True, "nearest": False, "figure": (figs.get(it) or {}).get(k),
                   "bar": KIND_BARS[k], "label": k}
        else:
            rec = nearest_fill(order, {i: x["item"] for i, x in enumerate(out)}, figs, k)
            if rec is None:
                raise SystemExit(f"no item has a {k} figure among the development items")
        repl[k] = {"from": e["item"], **rec}
        out.append({"item": rec["item"], "start_s": None, "kind": k, "kind_label": rec["label"],
                    "kind_filled": rec["filled"], "old": False})
    return out, repl


def cmd_ear_items(_args):
    """A later page's ear items (zero renders; 12q, #581's nit; 12p's "new ear items come first"): the first page's
    eight items with each ruled-out DI replaced for its kind (`replace_ruled_out_kinds`, from the first transcribe's
    stored scans and seeded order); a replacement's window by the declared rule (`grid_window`, its kind's source);
    its notes transcribed once (Basic Pitch, the install's pair). -> redo/ear-items-<name>.json, its note files."""
    require_redo(PHASE_CALIB, PHASE_TRUTH, PHASE_ITEM5_OUT)
    name = getattr(_args, "build_name", None)
    if not name:
        raise SystemExit("ear-items needs --build-name: the first page's items are never rewritten")
    out_path = REDO / f"ear-items-{name}.json"
    never_overwrite(out_path)
    pair = install_pair(load_manifest())
    first = json.loads(ear_items_path().read_text())
    excl, tn, z, meta = _dev_context()
    old = [e["item"] for e in first["items"] if e["old"]]
    pool = sorted((it for it in meta if not NR.clear_of({"goat_item": it}, excl) and it not in old),
                  key=lambda s: int(s.split("_")[1]))                 # the first transcribe's pool, item_5 in
    order = list(pool)
    random.Random(f"{EAR_SEED}|ear-items").shuffle(order)
    scan = REDO / "work" / "transcribe" / "scan"
    kinds_tr, figs_tr, starts = {}, {}, {}
    for i, it in enumerate(order):
        f = scan / f"{i:03d}-scan.json"
        if not f.exists():
            raise SystemExit(f"{f.name}: the first transcribe's scan is not stored")
        notes, _ = clean_transcribed(notes_from_events(json.loads(f.read_text())["events"]))
        st = grid_window(notes, goat_duration(z, it))
        if st is not None:
            starts[it] = st
            w = [dict(n, on=n["on"] - st - 0.25, off=n["off"] - st - 0.25) for n in notes
                 if st + 0.25 <= n["on"] < st + 10.25]
            kinds_tr[it], figs_tr[it] = kind_flags(w), kind_figures(w)
    kinds = ear_kinds_of(kinds_tr, {k: set(v) for k, v in (first.get("kinds_annotated") or {}).items()})
    figs = merge_kind_figures(figs_tr, first.get("figures_annotated") or {})
    d_items = {w["item"] for w in read_dev_windows(dev_windows(z, excl, tn["items"]))} - \
        {e["item"] for e in first["items"]}                 # D: the fixes' development windows
    items, repl = replace_ruled_out_kinds(order, first["items"], figs, kinds, exclude=d_items)
    jobs, meta_of = [], []
    for e in items:
        if e["start_s"] is None:
            e["start_s"] = starts[e["item"]]
        if note_path("ear", e["item"]).exists():
            rec = json.loads(note_path("ear", e["item"]).read_text())
            if abs(rec["source"]["start_s"] - e["start_s"]) > 1e-9:
                raise SystemExit(f"{e['item']}: a note file at another window exists")
            continue
        _, inp, pre = window_audio(goat_audio(z, e["item"]), e["start_s"])
        jobs.append((inp, "ear"))
        meta_of.append((e["item"], pre, {"start_s": e["start_s"]}))
    for (it, pre, info), r in zip(meta_of, run_bp(jobs, REDO / "work" / f"ear-items-{name}") if jobs else []):
        NR.write_once(note_path("ear", it), note_record(r, pre, info))
    why = ruled_out_refusal([e["item"] for e in items], "the new ear items")
    if why:
        raise SystemExit(why)
    NR.write_once(out_path, {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_ITEM5_OUT}", "name": name,
                             "items": items, "replaced": repl, "first_sha256": NR.file_sha(ear_items_path()),
                             "pair": list(pair)})
    print(f"EAR ITEMS {name}: {[(e['item'], e['kind']) for e in items]}; replaced {repl}; sha256 "
          f"{NR.file_sha(out_path)}")


def cmd_build(_args):
    """Step 6 (zero renders): `tr-di` and `tr-plain` (`note_rebuild.rebuild_redo`, the ring variant from the
    calibration) for the 47 parts (finish: `song_bank.measure`, then `average_balance` with `note_replay.others_for`'s
    others, as row (c)'s avg+mild and stage 1's arms) and the 8 ear items (finish: `song_bank.measure`, as the old
    clips); the audio checks on every dry guitar (`judge-accepts` against the part's `xlnoG@-3` stem on its search
    half; the ear items have no stem: clauses (ii) and (iii)); Basic Pitch's round trip for `chords-kept`; a part
    failing a blocking check is refused (3 or more of the 40 deciding stop the row before any render; a panel refusal
    is listed). Every note file must name the install's pair (and main's phase_nr_1_redo_install's, once merged).
    12m: loudness is used only as main's note-versions read gives it (`versions_loud`: its gamma on NV-loud, else the
    user's recorded decision); refuses while `onsets-found` flags 3 or more of the 40 deciding parts without the user's
    go (`flags_go_refusal`).
    -> redo/dry/<arm>/<key>.npy, redo/build.json; its sha256 goes into the ledger as phase_scratch_notes_dry."""
    m = require_redo(PHASE_CALIB, PHASE_TRUTH)
    _, cal = require_install_facts()
    pair = install_pair(load_manifest())
    loud, why = versions_loud(m.get(LEDGER_ID))
    why = why or ledger_pair_refusal(m.get(LEDGER_ID), pair)
    if why:
        raise SystemExit(why)
    name = getattr(_args, "build_name", None)             # a later build (12q): its own record and dry root
    fixes = json.loads(getattr(_args, "fixes", None) or "{}")
    if fixes and not name:
        raise SystemExit("a build with fixes needs --build-name: the first build is never rewritten")
    loud, why = build_loudness(loud, fixes)               # a later build's own loudness (12s: build 2 is loud null)
    if why:
        raise SystemExit(why)
    if name:
        why = ruled_out_refusal([e["item"] for e in json.loads(ear_items_file(name).read_text())["items"]],
                                f"the ear items for {name}")
        if why:
            raise SystemExit(why)
    never_overwrite(build_path(name))
    tr = json.loads(transcribe_path().read_text())     # its "stopped" is always False since S1 (refusal_count)
    why = flags_go_refusal(tr.get("onsets_flagged_deciding") or [], m.get(LEDGER_ID))
    if why:
        raise SystemExit(why)
    import numpy as np

    from learn import scratch_search as S

    excl, _, z, _ = _dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    ring = cal["ring_variant"]
    draw, _, sd = row_parts()
    work = REDO / "work" / "build"
    todo = build_todo(pair, ear_items_file(name))
    if name:
        from learn import note_fixes as NF
    built, jobs = [], []
    for kind, key, info, rec, di, finish in todo:
        notes, rep = timed_notes(rec, di)
        if fixes:
            notes, frep = NF.apply_fixes(notes, fixes, di)
            rep = {**rep, "fixes": frep}
        for arm in NR.REDO_ARMS:
            y, yrep = NR.rebuild_redo(arm, notes, len(di), bank, di, ring, finish=finish, loud=loud)
            y32 = np.asarray(y, np.float32)
            if len(y32) != len(di) or not np.isfinite(y32).all():
                raise SystemExit(f"{key}: a bad {arm} dry guitar")
            path = dry_path(arm, f"{kind}|{key}", dry_root(name) if name else None)
            never_overwrite(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, y32)
            built.append((kind, key, info, arm, notes, rep, yrep, di, y32, NR.file_sha(path)))
            jobs.append((y32, f"{arm}"))
    rt = run_bp(jobs, work / "round-trip")
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "pair": list(pair), "ring_variant": ring,
           "loud_gamma": loud, "name": name, "fixes": fixes,
           "dry_root": str(dry_root(name)) if name else None, "ear_items_file": ear_items_file(name).name,
           "transcribe_sha256": NR.file_sha(transcribe_path()), "parts": {}, "ear": {}}
    for (kind, key, info, arm, notes, rep, yrep, di, y32, sha), r in zip(built, rt):
        got = round_trip_notes(r["events"], np.asarray(y32, np.float64))
        if kind == "part":
            ref_blank = S.load_ref_blank(sd, info, "xlnoG")
            ja = judge_accepts(y32, di, info["lag"], info["search"], ref_blank)
        else:
            ja = judge_accepts(y32, di, 0, "A")
        figs = {**(tr["parts"] if kind == "part" else tr["ear"])[key]["figures"], "judge-accepts": ja,
                "ring-kept": ring_kept(np.asarray(y32, np.float64), di, [n["on"] for n in notes]),
                "chords-kept": chords_kept(got, notes)}
        side = {"crest_diff_db": NR.crest_db(np.asarray(y32, np.float64)) - NR.crest_db(di),
                "logmel": NR.logmel_distance(di, np.asarray(y32, np.float64)),
                "above2k_dry": NR.share_above(np.asarray(y32, np.float64)), "above2k_true": NR.share_above(di),
                "mask": NR.mask_agreement(di, np.asarray(y32, np.float64))}
        row = (out["parts"] if kind == "part" else out["ear"]).setdefault(key, {"timing": rep, "arms": {},
                                                                               **content_shares(notes)})
        row["arms"][arm] = {"sha256": sha, "report": yrep, "figures": figs, "beside": side,
                            **check_verdict(figs, blocking=effective_blocking(cal, m.get(LEDGER_ID)))}
    for rows in (out["parts"], out["ear"]):
        for key, row in rows.items():
            row["failed"] = row["arms"]["tr-di"]["failed"]
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    dec, pan, stop = refusal_count(out["parts"], sets_of)
    out.update(refused_deciding=dec, refused_panel=pan, stopped=stop,
               ear_failing=sorted(k for k, r in out["ear"].items() if r["failed"]))
    NR.write_once(build_path(name), out)
    print(f"BUILD: {len(out['parts'])} parts and {len(out['ear'])} ear items x {len(NR.REDO_ARMS)} arms; refused "
          f"deciding {len(dec)} {sorted(dec)}{' (STOPPED: no render)' if stop else ''}, panel {sorted(pan)}; ear "
          f"failing {out['ear_failing']}; sha256 {NR.file_sha(build_path(name))} (into the ledger as "
          f"{PHASE_DRY if not name else PHASE_DRY + '_' + name})")


def load_dry(arm, key, build, kind="part"):
    """A redo dry guitar, refused unless its sha256 is the one `build` recorded."""
    import numpy as np

    path = dry_path(arm, f"{kind}|{key}", build.get("dry_root"))
    rows = build["parts"] if kind == "part" else build["ear"]
    if NR.file_sha(path) != rows[key]["arms"][arm]["sha256"]:
        raise SystemExit(f"{path.name}: not the dry guitar `build` wrote")
    return np.load(path).astype(np.float32)


def cmd_stem_preview(_args):
    """Step 6, beside (zero renders): Basic Pitch on each part's `xlnoG@-3` stem, its search half only (the stem on the
    section's timeline, `note_rebuild_s1.ref_on_section`), against the DI's notes in that half: note F by set and
    class. It gates nothing; it sizes the stem-notes row. -> redo/stem-preview.json."""
    require_redo()
    never_overwrite(stem_preview_path())
    pair = install_pair(load_manifest())
    import numpy as np

    from learn import knob_ceiling as K
    from learn import note_rebuild_s1 as S1
    from learn import note_replay as R
    from learn import pretrain_set as PS

    draw, rby, sd = row_parts()
    jobs, info = [], []
    for p in sorted(draw["parts"], key=lambda p: p["pkey"]):
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        di = np.asarray(R.di_section(prt), np.float64)
        stem = S1.ref_on_section(R.load_stem("xlnoG", rby[p["pkey"]]), len(di), int(PS.TRIM_S * PS.SR),
                                 K.P.LATENCY + p["lag"])
        a, b = (PS.TRIM_S + h for h in K.R.HALVES[p["search"]])
        jobs.append((stem[int(a * PS.SR):int(b * PS.SR)], "stem"))
        notes, _ = timed_notes(load_note("part", p["pkey"], pair), di)
        info.append((p, a, b, [n for n in notes if a <= n["on"] < b]))
    bp = run_bp(jobs, REDO / "work" / "stem-preview")
    per = {}
    for (p, a, b, truth), r in zip(info, bp):
        got = [dict(n, on=n["on"] + a, off=n["off"] + a) for n in clean_transcribed(notes_from_events(r["events"]))[0]]
        per[p["pkey"]] = {"set": p["set"], "cls": p["cls"], **match_notes(truth, got, KNOWN_ONSET_S)}
    by = {}
    for v in per.values():
        for g in (v["set"], f"{v['set']}|{v['cls']}"):
            by.setdefault(g, []).append(v)
    NR.write_once(stem_preview_path(), {"plan": PLAN, "parts": per,
                                        "note_f": {g: pooled_f(vs) for g, vs in sorted(by.items())}})
    print(f"STEM PREVIEW: note F {json.dumps({g: round(pooled_f(vs) or 0, 3) for g, vs in sorted(by.items())})}")


def cmd_clips(_args):
    """Step 8 (52 renders): the ear page's 13 cards (`ear_cards`), each version (the recorded DI and Rebuilt: tr-di, or
    the true DI on the hidden control) through the AC20's clean or crunch class start, each render primed alone,
    trimmed, at EAR_LUFS; only when every ear item passes every content check. -> listening/note-rebuild-ear-2/
    <card>-ref.wav, <card>-reb.wav, index.json (the key: never on the page)."""
    require_redo()
    bpath = pathlib.Path(getattr(_args, "build", None) or build_path())     # any build: no attempt cap (2026-11-24)
    build_sha = NR.file_sha(bpath)
    dest = clips_dir(build_sha)
    never_overwrite(dest)
    build = json.loads(bpath.read_text())
    # 12q R1: the page is built whatever the checks read (their figures go into the key, never on the page)
    from learn import note_replay as R

    R.no_separation_beside()
    import numpy as np
    import soundfile as sf

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as SB

    _, _, z, _ = _dev_context()
    ear = json.loads((REDO / build.get("ear_items_file", ear_items_path().name)).read_text())["items"]
    why = None if build_sha == FIRST_DRY_SHA else ruled_out_refusal([e["item"] for e in ear], "the ear items")
    if why:                                                  # 12p: a later page never plays a ruled-out DI
        raise SystemExit(why)
    cards = ear_cards([e["item"] for e in ear if e["old"]], {e["kind"]: e["item"] for e in ear if not e["old"]})
    ms = P.A_menu_S()[EAR_AMP]
    trim = (int(PS.TRIM_S * PS.SR), int(round((PS.SEC_S + PS.TRIM_S) * PS.SR)))
    LO._wait_cap()
    dest.mkdir(parents=True)
    index = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "amp": EAR_AMP, "lufs": EAR_LUFS,
             "build_sha256": build_sha, "cards": []}
    for c in cards:
        e = next(q for q in ear if q["item"] == c["item"])
        di = SB.measure(window_audio(goat_audio(z, c["item"]), e["start_s"])[0])
        reb = di if c["control"] else load_dry("tr-di", c["item"], build, kind="ear")
        sel, S_ = ms[c["cls"]]
        s_ = LO.tdict(LO.sdict(dict(S_)))
        files = {}
        for ver, y in (("ref", di), ("reb", reb)):
            out = np.asarray(AM.fresh_render(CB.new_renderer, np.asarray(y, np.float32), sel, s_, s_),
                             np.float64)[trim[0]:trim[1]]
            if not np.isfinite(out).all():
                raise SystemExit(f"{c['id']} {ver}: a non-finite render")
            f = dest / f"{c['id']}-{ver}.wav"
            sf.write(f, NR.at_lufs(out, EAR_LUFS).astype(np.float32), PS.SR)
            files[ver] = {"file": f.name, "sha256": NR.file_sha(f)}
        index["cards"].append({**c, "kind": e["kind"], "kind_label": e.get("kind_label"), "clips": files})
    NR.write_once(dest / "index.json", index)
    print(f"CLIPS DONE: {len(cards)} cards, {2 * len(cards)} clips, {4 * len(cards)} renders -> {dest}")


# --- the second amendment's commands (note-rebuild-plan 12m; zero renders) -------------------------------------------------

class TruthAudio:
    """The truth windows' audio and notes, each file read once and checked against the listing's sha256."""

    def __init__(self, listing):
        self.files = {f"{f['player']}|{f['kind']}|{f['name']}": f for f in listing["files"]}
        self.cache = {}

    def window(self, w):
        """-> (DI as rendered, the transcriber's input, pre_s, the truth notes)."""
        from learn import note_truth as TR
        from learn import song_bank as SB

        k = f"{w['player']}|{w['kind']}|{w['name']}"
        if k not in self.cache:
            f = self.files[k]
            for path, want in ((f["di"], f["di_sha256"]), (f["midi"], f["midi_sha256"])):
                if NR.file_sha(path) != want:
                    raise SystemExit(f"{pathlib.Path(path).name}: not the file the truth listing hashed")
            self.cache = {k: (TR.di_audio(f["di"]), TR.clean_truth(TR.midi_truth(f["midi"]))[0])}
        x, clean = self.cache[k]
        sec, inp, pre = window_audio(x, w["start"])
        di = SB.measure(sec)
        notes, off = TR.truth_notes(clean, w["start"], di)
        if len(notes) != w["notes"] or abs(1000 * off - w["offset_ms"]) > 1e-6:
            raise SystemExit(f"{w['key']}: the truth no longer matches its listing (notes or offset)")
        return di, inp, pre, notes


def usable_windows(listing, players=("P1", "P2")):
    """(Pure.) The listing's windows that pass the consistency test, for `players`."""
    return [w for w in listing["windows"] if w["consistent"] and w["player"] in players]


def ladder_windows(listing):
    """(Pure.) The instrument check's six real windows: for P1 and for P2, the first usable window of the first two
    chord files and of the first scale file that have one, by name."""
    out = []
    for pl in ("P1", "P2"):
        for kind, k in (("chords", 2), ("scales", 1)):
            names = sorted({w["name"] for w in usable_windows(listing, (pl,)) if w["kind"] == kind})[:k]
            for nm in names:
                out.append(min((w for w in usable_windows(listing, (pl,)) if w["kind"] == kind and w["name"] == nm),
                               key=lambda w: w["start"]))
    return out


def cmd_truth(_args):
    """The truth listing (zero Basic Pitch runs; note-rebuild-plan 12m phase 2): every P1 and P2 file's DI and MIDI
    sha256, the clean-up's counts, every declared window with its consistency test. Written once; its sha256 goes into
    the ledger as phase_nr_1_redo_truth before any run reads a truth window. -> redo/truth.json."""
    require_redo(PHASE_CALIB)
    never_overwrite(truth_path())
    from learn import note_truth as TR

    body = TR.build_listing()
    NR.write_once(truth_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_CALIB}",
                                 "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    print(f"TRUTH: {len(body['files'])} files, {len(body['windows'])} windows {json.dumps(body['by_player_kind'])}; "
          f"clean-up {body['cleanup']}; sha256 {NR.file_sha(truth_path())} (into the ledger as {PHASE_TRUTH})")


def cmd_attacks_report(_args):
    """The detector's report (zero renders; phase 3): librosa's flux detector on the usable P1 and P2 windows and the
    ten known lists, timed on 3 windows first; its steady offset from P1 only; its recall of true onset groups, overall
    and on ringing onsets, per set (should it ever gate again, 0.90 on both); "truth passes" per window. Written once.
    -> redo/attacks.json."""
    m = require_redo(PHASE_CALIB, PHASE_TRUTH)
    never_overwrite(attacks_path())
    listing = require_truth(m)
    from learn import note_attacks as NA
    from learn import song_bank as SB

    ta = TruthAudio(listing)
    bank = NR.Bank(NR.load_notes_doc(), excl=NR.load_exclusion())
    items = []
    for w in usable_windows(listing):
        di, inp, pre, truth = ta.window(w)
        items.append((w["player"], w["key"], di, truth, (inp, w["player"], pre)))
    for nm in sorted(KNOWN_NOTES):
        y = known_audio(nm, bank)
        items.append(("lists", nm, SB.measure(y), KNOWN_NOTES[nm], (y, "list", 0.0)))
    work = REDO / "work" / "attacks"
    t0 = time.perf_counter()
    NA.run_attacks([it[4] for it in items[:3]], work / "timing")
    secs = (time.perf_counter() - t0) / max(1, min(3, len(items)))
    att = NA.run_attacks([it[4] for it in items], work / "all")
    offset = NA.detector_offset([(a, [n["on"] for n in it[3]]) for it, a in zip(items, att) if it[0] == "P1"])
    rec, passes = {}, {}
    kind_of = {w["key"]: w["kind"] for w in usable_windows(listing)}
    for st in ("P1", "P2", "lists"):
        figs = [NA.detector_recall(a, it[3], offset) for it, a in zip(items, att) if it[0] == st]
        rec[st] = NA.pooled_recall(figs)
        for kind in ("chords", "scales", "techniques"):
            sub = [(it, a) for it, a in zip(items, att) if it[0] == st and kind_of.get(it[1]) == kind]
            if sub:
                rec[f"{st}|{kind}"] = NA.pooled_recall([NA.detector_recall(a, it[3], offset) for it, a in sub])
                if kind == "chords":
                    rec[f"{st}|chords|strum"] = NA.pooled_recall(
                        [NA.detector_recall(a, it[3], offset, gap=NA.STRUM_GROUP_S) for it, a in sub])
    for it, a in zip(items, att):
        passes[it[1]] = attacks_found(a, it[3], it[2], offset)
    body = {"detector": CONTENT["onsets-found"]["detector"], "hop": NA.ATTACK_HOP, "delta": NA.ATTACK_DELTA,
            "offset_s": offset, "offset_from": "P1", "seconds_per_window": secs, "recall": rec,
            "truth_passes": passes, "windows": len(items), "truth_sha256": NR.file_sha(truth_path())}
    NR.write_once(attacks_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_CALIB}",
                                   "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    print(f"ATTACKS: offset {1000 * offset:.1f} ms (P1); recall {json.dumps({k: [v['recall'], v['ringing_recall']] for k, v in rec.items()})}; "
          f"{secs:.2f} s a window; sha256 {NR.file_sha(attacks_path())}")


def cmd_ghost_ladder(_args):
    """The instrument check (zero Basic Pitch runs; phase 3b): made-up octave ghosts added to the true-notes rebuild at
    0, -6, -12 and -20 dB must lower `floored_logmel` at every step, the -20 dB version not below the plain rebuild, on
    each of the ten lists and on six real windows (`ladder_windows`). Any list failing stops the work (to the user);
    a real window failing alone makes the real set reported only. Written once. -> redo/ghost-ladder.json."""
    m = require_redo(PHASE_CALIB, PHASE_TRUTH)
    never_overwrite(ladder_path())
    listing = require_truth(m)
    from learn import note_versions as NV
    from learn import song_bank as SB

    ta = TruthAudio(listing)
    bank = NR.Bank(NR.load_notes_doc(), excl=NR.load_exclusion())
    lists, real = {}, {}
    for nm in sorted(KNOWN_NOTES):
        di = SB.measure(known_audio(nm, bank))
        lists[nm] = NV.ghost_ladder(di, KNOWN_NOTES[nm], bank, SB.measure)
    for w in ladder_windows(listing):
        di, _, _, truth = ta.window(w)
        real[w["key"]] = NV.ghost_ladder(di, truth, bank, SB.measure)
    go, real_only = NV.ladder_outcome({k: v["passes"] for k, v in lists.items()},
                                      {k: v["passes"] for k, v in real.items()})
    body = {"lists": lists, "real": real, "go": go, "real_reported_only": real_only, "steps_db": NV.GHOST_STEPS_DB,
            "truth_sha256": NR.file_sha(truth_path())}
    NR.write_once(ladder_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_CALIB}",
                                  "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    print(f"GHOST-LADDER {'GO' if go else 'STOP (to the user)'}: lists {sum(v['passes'] for v in lists.values())} of "
          f"{len(lists)}, real {sum(v['passes'] for v in real.values())} of {len(real)}"
          f"{' (the real set is reported only)' if real_only else ''}; sha256 {NR.file_sha(ladder_path())}")


def rest_level_db(di, notes, rate=NR.SR):
    """The DI's median 20-ms level where no truth note sounds, less its loudest frame's (P2's rest level, reported)."""
    import numpy as np

    n, h = int(CHECK_FRAME_S * rate), int(CHECK_HOP_S * rate)
    L = NR.frame_levels_db(di, n, h)
    if not len(L):
        return None
    t = (np.arange(len(L)) * h + n / 2) / rate
    rest = np.ones(len(L), bool)
    for q in notes:
        rest &= ~((t >= q["on"]) & (t < q["off"]))
    return float(np.median(L[rest]) - L.max()) if rest.any() else None


def cmd_truth_report(_args):
    """The truth report (zero renders; phase 4), once: Basic Pitch on every usable P1 and P2 window and on GOAT's 27
    development windows (note files written once, reused by `versions`); precision and recall against the cleaned
    truth, chords and scales apart, P1 and P2 apart (`note_truth.truth_precision`), reported, never a gate; the hum
    guard (12m, relative: over 5% of a window's found notes on a mains harmonic, with no truth note and none sounding, stops the report); P2's rest level; P2's chord recall
    read against the 0.85 trigger (under it: to the user before step 5). -> redo/truth-report.json."""
    m = require_redo(PHASE_CALIB, PHASE_TRUTH)
    never_overwrite(truth_report_path())
    listing = require_truth(m)
    pair = install_pair(load_manifest())
    from learn import note_truth as TR
    from learn import song_bank as SB

    ta = TruthAudio(listing)
    excl, tn, z, _ = _dev_context()
    jobs, meta = [], []
    for w in usable_windows(listing):
        never_overwrite(note_path("truth", w["key"]))
        di, inp, pre, truth = ta.window(w)
        jobs.append((inp, w["player"]))
        meta.append(("truth", w["key"], pre, w, di, truth))
    for w in read_dev_windows(dev_windows(z, excl, tn["items"])):   # 12p: item_5 out
        never_overwrite(note_path("goat", w["item"]))
        sec, inp, pre = window_audio(goat_audio(z, w["item"]), w["start_s"])
        jobs.append((inp, "goat"))
        meta.append(("goat", w["item"], pre, w, SB.measure(sec), None))
    bp = run_bp(jobs, REDO / "work" / "truth-report")
    rows, hum, rest, goat = [], [], [], {}
    for (kind, key, pre, w, di, truth), r in zip(meta, bp):
        rec = note_record(r, pre, {"truth_window": key} if kind == "truth" else {"start_s": w["start_s"]})
        NR.write_once(note_path(kind, key), rec)
        est, _ = timed_notes(rec, di)
        if kind == "goat":
            goat[key] = {"notes": len(est), "note_file_sha256": NR.file_sha(note_path(kind, key))}
            continue
        mt = match_notes(truth, est)
        hs = TR.hum_share(est, truth)
        if hs > TR.HUM_STOP:
            hum.append((key, hs))
        if w["player"] == "P2":
            rest.append(rest_level_db(di, truth))
        rows.append({"key": key, "player": w["player"], "kind": w["kind"], "matched": mt["matched"], "ref": mt["ref"],
                     "est": mt["est"], "hum_share": hs, "note_file_sha256": NR.file_sha(note_path(kind, key))})
    report = TR.truth_precision(rows)
    rl = [x for x in rest if x is not None]
    body = {"report": report, "windows": rows, "goat": goat, "pair": list(pair),
            "p2_chord_recall": (report.get("P2|chords") or {}).get("recall"),
            "p2_scale_recall": (report.get("P2|scales") or {}).get("recall"),
            "p2_rest_level_db": statistics.median(rl) if rl else None, "hum_windows": hum,
            "stopped": hum or None, "truth_sha256": NR.file_sha(truth_path())}
    body["p2_chord_trigger"] = body["p2_chord_recall"] is not None and body["p2_chord_recall"] < P2_CHORD_TRIGGER
    NR.write_once(truth_report_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_CALIB}",
                                        "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    print(f"TRUTH REPORT: {json.dumps({k: [v['precision'], v['recall']] for k, v in report.items()})}; P2 chord recall "
          f"{body['p2_chord_recall']}{' (UNDER 0.85: to the user before step 5)' if body['p2_chord_trigger'] else ''};"
          f" hum {hum or 'none'}; sha256 {NR.file_sha(truth_report_path())}")


def cmd_versions(_args):
    """The note-versions read (zero renders; phase 5), once: refused unless the instrument check let it go. Per window
    (the ten lists, with the rerun's stored events; the usable P1 and P2 windows; GOAT's 27, nv-asis and the loud
    versions only) every version built as `tr-di` (`note_versions.build_versions`, `song_bank.measure` finish,
    `ring-soft` deciding, `ring-on` beside), its `floored_logmel` to the DI, the beside figures; the build rate timed on
    3 real windows first; Basic Pitch on nv-asis, nv-loud and nv-loud2 for the chord and soft-note guard; then
    `note_versions.summarise_read` (C, G, E per set with 90% intervals, the readings, the guard, one code, the
    `other-gap` flag, the declared recommendation) and the turned-down shares on P1, P2 and GOAT. Per-window distances
    and the rate written once. -> redo/versions.json."""
    m = require_redo(PHASE_CALIB, PHASE_TRUTH)
    never_overwrite(versions_path())
    listing = require_truth(m)
    if not ladder_path().exists():
        raise SystemExit("the instrument check has not run (`ghost-ladder` first)")
    ladder = json.loads(ladder_path().read_text())["body"]
    why, real_only = ladder_refusal(ladder, m.get(LEDGER_ID), NR.file_sha(ladder_path()))
    if why:
        raise SystemExit(why)
    report = require_truth_report(m.get(LEDGER_ID))
    pair = install_pair(load_manifest())
    from learn import note_versions as NV
    from learn import song_bank as SB

    ta = TruthAudio(listing)
    excl, tn, z, _ = _dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    known = {pp.stem.split("-", 1)[1]: pp for pp in (gate_work_dir() / "known").glob("*.json")}
    for nm, pp in known.items():                      # the lists' stored events come from this install
        ev = json.loads(pp.read_text())
        if ev.get("model_sha256") != pair[1] or ev.get("settings") != BP_SETTINGS:
            raise SystemExit(f"{pp.name}: the stored events come from another model or other settings")
    todo = []
    for w in usable_windows(listing):
        di, _, _, truth = ta.window(w)
        est, _ = timed_notes(load_note("truth", w["key"], pair), di)
        todo.append(("real", f"{w['player']}|{w['kind']}|{w['name']}", w["key"], di, truth, est, w["player"]))
    for nm in sorted(KNOWN_NOTES):
        di = SB.measure(known_audio(nm, bank))
        est, _ = timed_notes({"events": json.loads(known[nm].read_text())["events"], "pre_s": 0.0}, di)
        todo.append(("lists", nm, nm, di, KNOWN_NOTES[nm], est, "lists"))
    for w in read_dev_windows(dev_windows(z, excl, tn["items"])):   # 12p: item_5 out
        di = SB.measure(window_audio(goat_audio(z, w["item"]), w["start_s"])[0])
        est, _ = timed_notes(load_note("goat", w["item"], pair), di)
        todo.append(("goat", w["item"], w["item"], di, dev_true_notes(w["item"], w["start_s"], di), est, "goat"))
    t0, timed = time.perf_counter(), 0
    windows, rt_jobs, rt_of = [], [], []
    for st, cluster, key, di, truth, est, group in todo:
        deciding_truth = None if st == "goat" else truth
        d, side, audio = NV.build_versions(di, deciding_truth, est, bank, SB.measure)
        if st == "real" and timed < 3:
            timed += 1
            if timed == 3:
                rate_s = (time.perf_counter() - t0) / (3 * sum(len(v) for v in d.values()))
        rec = {"set": st, "cluster": cluster, "key": key, "group": group, "d": d, "beside": side,
               "turned_down": {str(g): NV.turned_down_counts(est, truth, g) for g in NR.LOUD_GAMMA}}
        windows.append(rec)
        for v in NV.ROUND_TRIP:
            if v in audio:
                rt_jobs.append((audio[v], v))
                rt_of.append((len(windows) - 1, v))
    rt = run_bp(rt_jobs, REDO / "work" / "versions-round-trip")
    trips = {}
    for (i, v), r in zip(rt_of, rt):
        trips.setdefault(i, {})[v] = clean_transcribed(notes_from_events(r["events"]))[0]
    for i, w in enumerate(windows):
        st, _, _, _, truth, est, _ = todo[i]
        if st == "goat":
            w["round_trip_notes"] = {v: len(n) for v, n in trips.get(i, {}).items()}
            continue
        ch = NV.chord_indices(truth)
        asis = NV.found_true(trips[i]["nv-asis"], truth)
        w["guard"] = {}
        for g, v in zip(NR.LOUD_GAMMA, ("nv-loud", "nv-loud2")):
            loud = NV.found_true(trips[i][v], truth)
            soft = NV.soft_indices(est, truth, g)
            w["guard"][g] = {"chord": (len(asis & set(ch)), len(loud & set(ch)), len(ch)),
                             "soft": (len(asis & set(soft)), len(loud & set(soft)), len(soft))}
        w["round_trip_precision"] = {v: match_notes(truth, n)["precision"] for v, n in trips[i].items()}
        w["pitch_class_cosine"] = pitch_class_cosine(truth, est)
    read = NV.summarise_read(windows, real_only)
    shares = {}
    for grp in ("P1", "P2", "goat"):
        for g in NR.LOUD_GAMMA:
            v = [w["turned_down"][str(g)] for w in windows if w["group"] == grp]
            shares.setdefault(grp, {})[str(g)] = NV.pooled_share(v)      # pooled over the set's paired notes
    body = {"windows": windows, "read": read, "turned_down_shares": shares, "build_seconds": rate_s if timed >= 3
            else None, "real_reported_only": real_only, "ladder_by_user_go": not ladder["go"],
            "truth_report_by_user_go": bool(report.get("stopped")),
            "ladder_sha256": NR.file_sha(ladder_path()), "truth_sha256": NR.file_sha(truth_path()),
            "truth_report_sha256": NR.file_sha(truth_report_path()), "gate_sha256": NR.file_sha(gate_path())}
    NR.write_once(versions_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_CALIB}",
                                    "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    c = read["code"]
    print(f"VERSIONS {c['code']}{' gamma ' + str(c['gamma']) if c['gamma'] else ''}: readings "
          f"{json.dumps({str(k): v for k, v in read['readings'].items()})}; other-gap {read['other_gap']}; "
          f"recommendation: {read['recommendation']['text']}; sha256 {NR.file_sha(versions_path())}")


COMMANDS = {"set-aside": cmd_set_aside, "install": cmd_install, "install-gate": cmd_install_gate,
            "calibrate": cmd_calibrate, "transcribe": cmd_transcribe, "build": cmd_build,
            "stem-preview": cmd_stem_preview, "clips": cmd_clips, "truth": cmd_truth, "ear-items": cmd_ear_items,
            "attacks-report": cmd_attacks_report, "ghost-ladder": cmd_ghost_ladder, "truth-report": cmd_truth_report,
            "versions": cmd_versions}


def main(argv=None):
    import sys

    for p_ in (str(NR.REPO), str(NR.REPO / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--interpreter", default=None, help="install only: the declared 3.11 fallback's interpreter")
    ap.add_argument("--build", default=None, help="clips only: a later build's record (default: the first build)")
    ap.add_argument("--build-name", dest="build_name", default=None,
                    help="build and ear-items: a later build's name (its own record, dry root and ear items)")
    ap.add_argument("--fixes", default=None, help='build only: the fixes as JSON, e.g. {"F1": "global", "F3": true}')
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
