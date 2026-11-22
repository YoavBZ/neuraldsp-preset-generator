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

$MAIN is the main checkout's .venv python (in a worktree add `--data-dir ~/ndsp-presets` through the environment the
replay used). Every command refuses unless this checkout runs main's code (`redo_on_main`: learn/scratch_search.py,
scratch_notes.py, note_rebuild.py, note_rebuild_s1.py, note_rebuild_ear.py, note_transcribe.py and bp_run.py equal
main's, and the `phase_fs*`, `phase_scratch_notes*` and `phase_nr*` keys equal main's) and main's ledger holds the
phases the step needs. Every output is written once (`never_overwrite`). Basic Pitch is imported only inside
`learn/bp_run.py`, run by its venv's own interpreter in a subprocess; nothing here imports it.

The pure parts (the clean-up, the note matching, the kinds and windows of the ear items, every check's pass rule, the
calibration's pick, the ring variant's rule, the refusal count, the expected-failure table, the lock, the overlap
song by song) are tested in tests/test_note_transcribe.py on the light CI runner (no numpy).
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

REDO = NR.OUT / "redo"                   # PF/note-rebuild/redo/
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

# --- the content checks (plan section 12e), thresholds frozen; `CONTENT` names each, what it gates, and whether it
# blocks a row part. `onsets-found`'s rise level is the lowest of RISE_LEVELS that holds the calibration's bars.
CONTENT = {
    "annotated-found": {"gates": "the transcriber's settings", "blocking": False,
                        "onset_s": 0.050, "median": 0.85, "floor": 0.75, "lands_share": 0.90, "tertile": "top"},
    "onsets-found": {"gates": "the notes", "blocking": True, "merge_s": 0.050, "within_s": 0.030, "share": 0.90},
    "playing-covered": {"gates": "the notes", "blocking": True, "playing": 0.95, "silent": 0.10},
    "judge-accepts": {"gates": "the audio", "blocking": True, "pause_over_true": 0.05, "gap_s": 0.250,
                      "gap_db": 40.0},
    "ring-kept": {"gates": "the audio", "blocking": True, "after_s": 0.600, "attack_s": 0.050, "median_db": 3.0,
                  "min_frames": 20, "env_corr": 0.80},
    "chords-kept": {"gates": "the audio", "blocking": True, "onset_s": 0.050, "note_f": 0.85, "chord_recall": 0.85,
                    "chord_size": 3, "min_chord_notes": 5},
}
NOTE_CHECKS = ("onsets-found", "playing-covered")
AUDIO_CHECKS = ("judge-accepts", "ring-kept", "chords-kept")
RISE_LEVELS = (6.0, 9.0, 12.0)           # calibrated in step 3 on the 27 development windows
CHECK_FRAME_S, CHECK_HOP_S = 0.020, 0.005   # the level frames of judge-accepts (iii) and ring-kept (i)
PLAY_FLOOR_DB = 40.0                     # "where the DI plays": within 40 dB of its loudest frame (J0's floor)
PLAY_FRAME = 2048                        # playing-covered's frames: J0's middle frame size, hop a quarter
CALIBRATION_PASS = 25                    # of the 27 development windows, each note check (90%)
RISE_PRECISION = 0.95                    # rise peaks that are true onsets, on the known-notes lists
REFUSAL_STOP = 3                         # of the 40 deciding parts (BKS+GOAT)
DECIDING = ("bks", "goat")               # the user's exception for this row only (2026-11-22, answer 3)

# --- the install gate (plan section 12b) -----------------------------------------------------------------------------------
REPEAT_WINDOWS = 4                       # development windows, three runs each (two in one process, one fresh)
KNOWN_F = 0.90                           # note F on the ten known lists, pooled (onset 50 ms, pitch 50 cents)
KNOWN_ONSET_S = 0.050
RING_TIE = 0.02                          # ring-soft unless ring-on's median envelope_corr is more than this higher

# --- the development windows and the ear page's items (plan sections 12c, 12d) ------------------------------------------
DEV_COUNT = 27                           # every GOAT item clear of the exclusion list with fine-aligned MIDI and a full
                                         # window at the probe's start (30 s into items over 45 s, else 1 s)
EAR_SEED = 20261401                      # the 4 new ear items' order
CONTROL_SEED = 20261402                  # the hidden control card's item and the cards' order
DEV_BLUR_SEED = 20261403                 # avg+mild on the development windows (the checks' positive control)
KINDS = ("chord-led", "single-note", "bends", "let-ring")
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


def check_verdict(figs, which=NOTE_CHECKS + AUDIO_CHECKS):
    """(Pure.) {check: True | False | None} for `which`, and the blocking failures (a None, not measured, never
    blocks). figs: {check: figure}."""
    res = {k: PASS_RULES[k](figs.get(k)) for k in which}
    return {"passes": res, "failed": sorted(k for k, v in res.items() if v is False and CONTENT[k]["blocking"])}


def annotated_found_pass(rows, c=CONTENT["annotated-found"]):
    """(Pure.) `annotated-found` on the development windows: on the windows in the top alignment-F tertile whose own
    annotation lands on a DI rise for at least `lands_share` of its notes, the median recall at least `median` and no
    window under `floor`. rows: [{alignment_f, lands_share, recall}]. -> {windows, median, minimum, passes}."""
    from learn import note_rebuild_s1 as S1

    edges = S1.tertile_edges([r["alignment_f"] for r in rows])
    top = [r for r in rows if r.get("alignment_f") is not None and S1.group_of(r["alignment_f"], edges) == len(edges)
           and (r.get("lands_share") or 0.0) >= c["lands_share"] and r.get("recall") is not None]
    if not top:
        return {"windows": 0, "median": None, "minimum": None, "passes": None, "edges": edges}
    rec = [r["recall"] for r in top]
    med = statistics.median(rec)
    return {"windows": len(top), "median": med, "minimum": min(rec), "edges": edges,
            "passes": med >= c["median"] and min(rec) >= c["floor"]}


def calibration_pick(rates, n=DEV_COUNT, need=CALIBRATION_PASS, precision=None):
    """(Pure.) The rise level for `onsets-found`: the lowest of RISE_LEVELS at which at least `need` of the `n`
    windows pass `onsets-found` and `playing-covered` and (when given) the rise detector's precision on the known lists
    is at least RISE_PRECISION. rates: {level: {"onsets-found": passing windows, "playing-covered": passing windows}};
    precision: {level: share}. -> level or None (a bar missed: amended by declaration before step 5)."""
    for lv in RISE_LEVELS:
        r = rates.get(lv) or rates.get(str(lv)) or {}
        ok = all((r.get(k) or 0) >= need for k in NOTE_CHECKS)
        if precision is not None:
            p = precision.get(lv, precision.get(str(lv)))
            ok = ok and p is not None and p >= RISE_PRECISION
        if ok:
            return lv
    return None


def ring_choice(corr_on, corr_soft, tie=RING_TIE):
    """(Pure.) The ring variant: the higher median `envelope_corr` over the development windows; `ring-soft` within
    `tie` (it cannot leave a released chord note sounding). corr_*: [per window]."""
    a, b = statistics.median(corr_on), statistics.median(corr_soft)
    return "ring-on" if a > b + tie else "ring-soft"


def refusal_count(build_parts, sets_of, deciding=DECIDING):
    """(Pure.) The row's content refusals: {pkey: failed checks} of the deciding parts and of the panel (beside).
    -> (deciding refused, panel refused, stops)."""
    dec, pan = {}, {}
    for k, r in sorted(build_parts.items()):
        failed = r.get("failed") or []
        if failed:
            (dec if sets_of[k] in deciding else pan)[k] = failed
    return dec, pan, len(dec) >= REFUSAL_STOP


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


def lock_refusal(text):
    """(Pure.) Why a lock does not hold the declared pins, or None: basic-pitch and onnxruntime at their declared
    versions and sha256, pretty-midi and mir-eval at their known wheels, no coremltools, every line hashed."""
    pins = {}
    for ln in text.splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        if "--hash=sha256:" not in ln:
            return f"an unhashed line: {ln[:60]}"
        spec, h = ln.split("--hash=sha256:", 1)
        n, v = spec.strip().split("==")
        pins[n] = (v, h.split()[0])
    for n, v, s, *_ in (BASIC_PITCH, ONNXRUNTIME):
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
              "learn/note_rebuild_s1.py", "learn/note_rebuild_ear.py", "learn/note_transcribe.py", "learn/bp_run.py")
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


def dry_path(arm, key):
    return REDO / "dry" / arm / f"{key.replace('/', '__')}.npy"


def gate_path():
    return REDO / "install-gate.json"


def calibration_path():
    return REDO / "calibration.json"


def transcribe_path():
    return REDO / "transcribe.json"


def build_path():
    return REDO / "build.json"


def stem_preview_path():
    return REDO / "stem-preview.json"


def ear_items_path():
    return REDO / "ear-items.json"


def clips_dir():
    return NR.HOME / "listening" / "note-rebuild-ear-2"


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

def attack_times(di, rise_db, rate=NR.SR, c=CONTENT["onsets-found"]):
    """The DI's attacks: `note_rebuild.rise_curve` peaks of `rise_db` or more, merged within `merge_s` (the first
    kept), where the DI plays (its 20-ms level within PLAY_FLOOR_DB of its loudest). -> [seconds]."""
    from scipy.signal import find_peaks

    rise, hop = NR.rise_curve(di, rate)
    if not len(rise):
        return []
    pk, _ = find_peaks(rise, height=rise_db)
    n, h = int(CHECK_FRAME_S * rate), int(CHECK_HOP_S * rate)
    L = NR.frame_levels_db(di, n, h)
    top = float(L.max()) if len(L) else 0.0
    out = []
    for j in pk:
        t = (j * hop + NR.REFINE_FRAME / 2) / rate
        f = min(len(L) - 1, max(0, int((t * rate - n / 2) // h))) if len(L) else 0
        if len(L) and L[f] < top - PLAY_FLOOR_DB:
            continue
        if out and t - out[-1] < c["merge_s"]:
            continue
        out.append(float(t))
    return out


def onsets_found(notes, di, rise_db, rate=NR.SR, c=CONTENT["onsets-found"]):
    """`onsets-found`'s figure: the DI's attacks with a note onset within `within_s`."""
    att = attack_times(di, rise_db, rate)
    ons = sorted(n["on"] for n in notes)
    found = sum(any(abs(a - o) <= c["within_s"] for o in ons) for a in att)
    return {"attacks": len(att), "found": found, "share": found / len(att) if att else None, "rise_db": rise_db}


def rise_precision(audio, true_onsets, rise_db, rate=NR.SR, c=CONTENT["onsets-found"]):
    """The rise detector's precision on a known list: the share of its attacks within `within_s` of a true onset."""
    att = attack_times(audio, rise_db, rate)
    hit = sum(any(abs(a - o) <= c["within_s"] for o in true_onsets) for a in att)
    return {"attacks": len(att), "true": hit, "precision": hit / len(att) if att else None}


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


def annotation_lands(ann, di, rate=NR.SR):
    """The share of annotated notes (after the onset steps) whose onset has a DI rise of REFINE_MIN_RISE_DB or more
    within +-SNAP_S (the snap's own rule)."""
    import numpy as np

    rise, hop = NR.rise_curve(di, rate)
    hits = 0
    for n in ann:
        lo = max(0, int((n["on"] - NR.SNAP_S) * rate) // hop)
        hi = min(len(rise), int((n["on"] + NR.SNAP_S) * rate) // hop + 1)
        hits += hi > lo and float(np.max(rise[lo:hi])) >= NR.REFINE_MIN_RISE_DB
    return hits / len(ann) if ann else None


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


def dev_true_notes(item, start_s, di):
    """A development window's GOAT annotation (stage P's fine-aligned true notes) after the same onset steps."""
    p = NR.OUT / "true-notes" / f"{item}.json"
    rec = json.loads(p.read_text())
    w = NR.window_notes(rec["notes"], start_s, len(di) / NR.SR)
    w = [dict(n, bends=[]) for n in w]
    off = NR.coarse_offset(w, di)
    return NR.snap_onsets(NR.shifted_notes(w, off), di, NR.SNAP_S)[0]


# --- the known notes (the install gate's only truth with chords) ---------------------------------------------------------

def _seq(pitches, t0, step, dur):
    return [{"on": t0 + j * step, "off": t0 + j * step + dur, "pitch": p, "bends": []} for j, p in enumerate(pitches)]


def _chords(chords, t0, step, dur):
    return [{"on": t0 + j * step, "off": t0 + j * step + dur, "pitch": p, "bends": []}
            for j, ch in enumerate(chords) for p in ch]


KNOWN_NOTES = {         # ten made-up note lists, each inside 10 s: scales, chords of 3 to 6 notes, a let-ring arpeggio,
    # and a bend; played from the bank by `synthesise_redo` (ring-on, no mutes, no tilt)
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
    """A known list played from the bank (ring-on, no mutes or tilt), at -22.9 LUFS, 10.25 s."""
    from learn import pretrain_set as PS

    n = int(round((PS.SEC_S + PS.TRIM_S) * rate))
    y, _ = NR.synthesise_redo(KNOWN_NOTES[name], n, bank, 0.0, "ring-on", (), 0.0, None, rate)
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


def cmd_install(_args):
    """Step 3 (a declared download): the venv from /usr/bin/python3, pip upgraded by its hashed pin, the lock made by
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
    run(INTERPRETER, "-m", "venv", TOOLS)
    pip = TOOLS / "bin" / "pip"
    pin = TOOLS / "pip-pin.txt"
    pin.write_text(f"{PIP_PIN[0]}=={PIP_PIN[1]} --hash=sha256:{PIP_PIN[2]}\n")
    run(BP_PYTHON, "-m", "pip", "install", "--require-hashes", "--only-binary", ":all:", "-r", pin)
    run(pip, "install", "--dry-run", "--ignore-installed", "--only-binary", ":all:", "--report", RESOLVE,
        *REQUIREMENTS)
    text = lock_lines(json.loads(RESOLVE.read_text()), [BASIC_PITCH[:3]])
    why = lock_refusal(text)
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
           "interpreter": INTERPRETER, "python": run(BP_PYTHON, "-c", "import sys; print(sys.version)").strip(),
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
    bank and transcribed: pooled note F at least KNOWN_F, each list reported), the seconds per 10-s window.
    -> redo/install-gate.json (its facts go into phase_nr_1_redo_install)."""
    require_redo()
    never_overwrite(gate_path())
    excl, tn, z, _ = _dev_context()
    wins = dev_windows(z, excl, tn["items"])[:REPEAT_WINDOWS]
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    work = REDO / "work" / "install-gate"
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
    body["ok"] = body["repeat_ok"] and body["known_ok"]
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
    """Step 3 (zero renders), once, after the install gate passed: on the 27 development windows, the DI's
    transcription, the note checks at each RISE_LEVELS level (pass rates; `calibration_pick`), the rise detector's
    precision on the known lists (and against the annotated onsets of the top-tertile windows, reported),
    `annotated-found` (the annotation's own ceiling, `annotation_lands`, first), the ring variant (`ring_choice` on
    tr-di's `envelope_corr`), and the checks' test: avg+mild must pass every audio check, the true DI through the same
    finish must pass, and each clip the user rejected must fail a check main's `phase_nr_1_ear_old` names for it
    (`expected_failure_refusal`). -> redo/calibration.json (its facts go into phase_nr_1_redo_install)."""
    m = require_redo(PHASE_EAR_OLD)
    never_overwrite(calibration_path())
    gate = json.loads(gate_path().read_text())["body"] if gate_path().exists() else None
    if not gate or not gate["ok"]:
        raise SystemExit("the install gate has not passed")
    expected = ear_old_table(m.get(LEDGER_ID))
    import numpy as np

    from learn import note_rebuild_s1 as S1
    from learn import song_bank as SB

    excl, tn, z, meta = _dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    wins = dev_windows(z, excl, tn["items"])
    work = REDO / "work" / "calibrate"
    dis, ins = {}, []
    for w in wins:
        x = goat_audio(z, w["item"])
        sec, inp, pre = window_audio(x, w["start_s"])
        dis[w["item"]] = SB.measure(sec)
        ins.append((inp, w["item"], pre))
    bp = run_bp([(i, t) for i, t, _ in ins], work / "di")
    rows, notes_of = {}, {}
    for (_, it, pre), r in zip(ins, bp):
        rec = {"events": r["events"], "pre_s": pre}
        di = dis[it]
        notes, rep = timed_notes(rec, di)
        notes_of[it] = notes
        ann = dev_true_notes(it, next(w["start_s"] for w in wins if w["item"] == it), di)
        rows[it] = {"timing": rep, "alignment_f": tn["items"][it].get("alignment_f"),
                    "lands_share": annotation_lands(ann, di),
                    "recall": match_notes(ann, notes, CONTENT["annotated-found"]["onset_s"])["recall"],
                    "onsets_found": {str(lv): onsets_found(notes, di, lv) for lv in RISE_LEVELS},
                    "playing_covered": playing_covered(notes, di)}
    rates = {str(lv): {"onsets-found": sum(bool(onsets_found_pass(r["onsets_found"][str(lv)])) for r in rows.values()),
                       "playing-covered": sum(bool(playing_covered_pass(r["playing_covered"])) for r in rows.values())}
             for lv in RISE_LEVELS}
    prec = {}
    for lv in RISE_LEVELS:
        hits = [rise_precision(known_audio(nm, bank), sorted({n["on"] for n in KNOWN_NOTES[nm]}), lv)
                for nm in sorted(KNOWN_NOTES)]
        a = sum(h["attacks"] for h in hits)
        prec[str(lv)] = sum(h["true"] for h in hits) / a if a else None
    level = calibration_pick(rates, precision=prec)
    ann_rows = [dict(r, item=it) for it, r in rows.items()]
    af = annotated_found_pass(ann_rows)
    top = [r["item"] for r in ann_rows if r["alignment_f"] is not None and af["edges"]
           and S1.group_of(r["alignment_f"], af["edges"]) == len(af["edges"])]
    prec_ann = {}
    for lv in RISE_LEVELS:
        a = t = 0
        for it in top:
            att = attack_times(dis[it], lv)
            w_ = next(w["start_s"] for w in wins if w["item"] == it)
            ons = [n["on"] for n in dev_true_notes(it, w_, dis[it])]
            a += len(att)
            t += sum(any(abs(x - o) <= CONTENT["onsets-found"]["within_s"] for o in ons) for x in att)
        prec_ann[str(lv)] = t / a if a else None
    # the ring variant, then the checks' test on the audio checks (at the calibrated level where it exists)
    corr, audio = {v: [] for v in NR.RING_VARIANTS}, {}
    rt_jobs = []
    dev_others = dev_others_maker()
    for w in wins:
        it, di = w["item"], dis[w["item"]]
        key = f"dev|{it}"
        drys = {}
        for v in NR.RING_VARIANTS:
            drys[v], _ = NR.rebuild_redo("tr-di", notes_of[it], len(di), bank, di, v, finish=SB.measure)
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
            got = clean_transcribed(notes_from_events(rt[j]["events"]))[0]
            j += 1
            figs = {"judge-accepts": judge_accepts(y, di, 0, "A"), "ring-kept": ring_kept(y, di, [n["on"] for n in
                                                                                             notes_of[it]]),
                    "chords-kept": chords_kept(got, notes_of[it])}
            checks.setdefault(d, {})[it] = {"figures": figs, **check_verdict(figs, AUDIO_CHECKS)}
    positive = {d: sorted(it for it, r in checks[d].items() if r["failed"]) for d in ("avg+mild", "true")}
    neg = negative_control(expected, bank, z, meta, excl, level or RISE_LEVELS[0], work)
    blind = expected_failure_refusal(expected, {c: r["passes"] for c, r in neg.items()})
    body = {"windows": [w["item"] for w in wins], "rows": rows, "rates": rates, "rise_precision_known": prec,
            "rise_precision_annotated_top": prec_ann, "rise_level": level, "annotated_found": af,
            "ring_corr": corr, "ring_variant": ring, "checks": checks, "positive_failures": positive,
            "negative": neg, "blind_spots": blind, "gate_sha256": NR.file_sha(gate_path())}
    body["ok"] = (level is not None and not positive["avg+mild"] and not positive["true"] and not blind)
    NR.write_once(calibration_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}",
                                       "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    print(f"CALIBRATE {'PASS' if body['ok'] else 'STOP'}: rise level {level} (rates {rates}, precision {prec}); "
          f"annotated-found {af}; ring {ring}; positive failures {positive}; blind spots {blind}; "
          f"sha256 {NR.file_sha(calibration_path())}")


def negative_control(expected, bank, z, meta, excl, rise_db, work):
    """The checks on the clips the user rejected: each old clip's dry guitar rebuilt in memory as `note_rebuild_s1
    clips` built it (GOAT's true notes, the two-stage oracle onset step, `rebuild_dry` with `song_bank.measure`), its
    notes (the old ones) through the note checks, its audio through the audio checks. clip keys: "<item>|<arm>".
    -> {clip: {passes, failed, figures}}."""
    import numpy as np

    from learn import song_bank as SB

    out, jobs, built = {}, [], {}
    for e in expected:
        it, arm = e["clip"].split("|")[:2]
        x = goat_audio(z, it)
        st = probe_start(len(x) / NR.SR)
        sec, _, _ = window_audio(x, st)
        di = SB.measure(sec)
        rec = NR.true_notes_for(it, z, meta)
        wn = NR.window_notes(rec["notes"], st, len(di) / NR.SR)
        notes, _ = NR.refine_onsets(NR.shifted_notes(wn, NR.coarse_offset(wn, di)), di)
        y, _ = NR.rebuild_dry(arm, notes, len(di), bank, di, finish=SB.measure)
        built[e["clip"]] = (di, notes, np.asarray(y, np.float64))
        jobs.append((y, e["clip"].replace("|", "-")))
    rt = run_bp(jobs, work / "rejected") if jobs else []
    for (clip, (di, notes, y)), r in zip(built.items(), rt):
        got = clean_transcribed(notes_from_events(r["events"]))[0]
        figs = {"onsets-found": onsets_found(notes, di, rise_db), "playing-covered": playing_covered(notes, di),
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
    if not g["ok"] or not c["ok"]:
        raise SystemExit("the install gate or the calibration did not pass: a declared amendment first")
    if c["gate_sha256"] != NR.file_sha(gate_path()):
        raise SystemExit("calibration.json was made from another install gate")
    return g, c


def row_parts():
    """The row's 47 parts from the from-scratch search's hashed draw, with each part's replay record and stored C3r
    unit. -> (draw, replay parts by key, Stored)."""
    from learn import note_replay as R
    from learn import scratch_search as S

    draw = S.require_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    return draw, {p["pkey"]: p for p in R.require_draw()["parts"]}, sd


def cmd_transcribe(_args):
    """Step 5 (zero renders): Basic Pitch on each of the 47 parts' raw DI sections (with up to MARGIN_S either side)
    and on the 8 ear items' windows (the 4 the user heard, at their old windows; 4 new by `pick_ear_items` from a
    whole-item scan, at `grid_window`); each note file written once with the install's pair; the note checks
    (`onsets-found` at the calibrated level, `playing-covered`) and, on GOAT parts, `annotated-found`'s recall,
    reported. -> redo/notes/<kind>/<key>.json, redo/ear-items.json, redo/transcribe.json."""
    m = require_redo()
    _, cal = require_install_facts()
    pair = install_pair(load_manifest())
    why = ledger_pair_refusal(m.get(LEDGER_ID), pair)
    if why:
        raise SystemExit(why)
    never_overwrite(transcribe_path())
    import numpy as np

    from learn import note_replay as R
    from learn import song_bank as SB

    draw, rby, sd = row_parts()
    work = REDO / "work" / "transcribe"
    level = cal["rise_level"]
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
    pool = sorted((it for it in meta if not NR.clear_of({"goat_item": it}, excl) and it not in old),
                  key=lambda s: int(s.split("_")[1]))
    NR.assert_clear([{"goat_item": it} for it in pool + old], excl)
    order = list(pool)
    random.Random(f"{EAR_SEED}|ear-items").shuffle(order)
    scans = run_bp([(goat_audio(z, it), "scan") for it in order], work / "scan")
    kinds, starts = {}, {}
    for it, r in zip(order, scans):
        dur = goat_duration(z, it)
        notes, _ = clean_transcribed(notes_from_events(r["events"]))
        st = grid_window(notes, dur)
        if st is None:
            continue
        starts[it] = st
        w = [dict(n, on=n["on"] - st - 0.25, off=n["off"] - st - 0.25) for n in notes
             if st + 0.25 <= n["on"] < st + 10.25]
        kinds[it] = kind_flags(w)
    new = pick_ear_items(order, kinds)
    if set(new) != set(KINDS):
        raise SystemExit(f"no item of kind {sorted(set(KINDS) - set(new))} among the development items")
    ear = [{"item": it, "start_s": probe_start(goat_duration(z, it)), "kind": None, "old": True}
           for it in old] + [{"item": new[k], "start_s": starts[new[k]], "kind": k, "old": False} for k in KINDS]
    for e in ear:
        never_overwrite(note_path("ear", e["item"]))
        x = goat_audio(z, e["item"])
        _, inp, pre = window_audio(x, e["start_s"])
        jobs.append((inp, "ear"))
        meta_of.append(("ear", e["item"], pre, {"start_s": e["start_s"]}))
    bp = run_bp(jobs, work / "notes")
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "pair": list(pair), "rise_level": level, "parts": {},
           "ear": {}, "calibration_sha256": NR.file_sha(calibration_path())}
    for (kind, key, pre, info), r in zip(meta_of, bp):
        rec = note_record(r, pre, info)
        NR.write_once(note_path(kind, key), rec)
        if kind == "part":
            p = next(q for q in draw["parts"] if q["pkey"] == key)
            di = np.asarray(R.di_section(sd.units[(p["set"], p["unit"], p["amp"])]["prt"]), np.float64)
        else:
            e = next(q for q in ear if q["item"] == key)
            di = SB.measure(window_audio(goat_audio(z, key), e["start_s"])[0])
        notes, rep = timed_notes(rec, di)
        figs = {"onsets-found": onsets_found(notes, di, level), "playing-covered": playing_covered(notes, di)}
        row = {"note_file_sha256": NR.file_sha(note_path(kind, key)), "timing": rep, "figures": figs,
               **check_verdict(figs, NOTE_CHECKS)}
        if kind == "part" and info["set"] == "goat":
            it = p["unit"].split("/", 1)[1].split("@", 1)[0]
            tp = NR.OUT / "true-notes" / f"{it}.json"
            if tp.exists():
                w0 = float(p["section"].rsplit("@", 1)[1]) - 0.25
                ann = NR.window_notes(json.loads(tp.read_text())["notes"], w0, len(di) / NR.SR)
                ann = NR.snap_onsets(NR.shifted_notes(ann, NR.coarse_offset(ann, di)), di)[0]
                row["annotated_found"] = {"recall": match_notes(ann, notes, CONTENT["annotated-found"]["onset_s"])[
                    "recall"], "lands_share": annotation_lands(ann, di)}
        (out["parts"] if kind == "part" else out["ear"])[key] = row
    out["ear_items"] = ear
    NR.write_once(ear_items_path(), {"plan": PLAN, "items": ear, "kinds_scanned": {k: sorted(v) for k, v in
                                                                                     kinds.items()},
                                     "order_seed": EAR_SEED})
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    dec, pan, stop = refusal_count(out["parts"], sets_of)
    out.update(note_refused_deciding=dec, note_refused_panel=pan, stopped=stop,
               ear_failing=sorted(k for k, r in out["ear"].items() if r["failed"]))
    NR.write_once(transcribe_path(), out)
    print(f"TRANSCRIBE: {len(out['parts'])} parts, {len(out['ear'])} ear items; note-check refusals deciding "
          f"{len(dec)} {sorted(dec)}{' (STOPPED: no render)' if stop else ''}, panel {sorted(pan)}; ear failing "
          f"{out['ear_failing']}; sha256 {NR.file_sha(transcribe_path())}")


def cmd_build(_args):
    """Step 6 (zero renders): `tr-di` and `tr-plain` (`note_rebuild.rebuild_redo`, the ring variant from the
    calibration) for the 47 parts (finish: `song_bank.measure`, then `average_balance` with `note_replay.others_for`'s
    others, as row (c)'s avg+mild and stage 1's arms) and the 8 ear items (finish: `song_bank.measure`, as the old
    clips); the audio checks on every dry guitar (`judge-accepts` against the part's `xlnoG@-3` stem on its search
    half; the ear items have no stem: clauses (ii) and (iii)); Basic Pitch's round trip for `chords-kept`; a part
    failing a blocking check is refused (3 or more of the 40 deciding stop the row before any render; a panel refusal
    is listed). Every note file must name the install's pair (and main's phase_nr_1_redo_install's, once merged).
    -> redo/dry/<arm>/<key>.npy, redo/build.json; its sha256 goes into the ledger as phase_scratch_notes_dry."""
    m = require_redo()
    _, cal = require_install_facts()
    pair = install_pair(load_manifest())
    why = ledger_pair_refusal(m.get(LEDGER_ID), pair)
    if why:
        raise SystemExit(why)
    never_overwrite(build_path())
    tr = json.loads(transcribe_path().read_text())
    if tr["stopped"]:
        raise SystemExit("the note checks refused 3 or more deciding parts: nothing is built (one declared fix)")
    import numpy as np

    from learn import di_robustness as DR
    from learn import note_replay as R
    from learn import scratch_search as S
    from learn import song_bank as SB

    draw, rby, sd = row_parts()
    excl, _, z, _ = _dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    ring = cal["ring_variant"]
    rparts = list(rby.values())                   # the replay's drawn parts (the others' pool, as row (c)'s blur)
    by_sec = {}
    for p in rparts:
        by_sec.setdefault(p["section"], sd.units[(p["set"], p["unit"], p["amp"])]["prt"])
    cache = {}

    def sec(s):
        if s not in cache:
            cache[s] = np.asarray(R.di_section(by_sec[s]), np.float64)
        return cache[s]
    work = REDO / "work" / "build"
    todo = []
    for p in sorted(draw["parts"], key=lambda p: p["pkey"]):
        rec = load_note("part", p["pkey"], pair)
        di = sec(p["section"])
        others = {s: [sec(x) for x in xs] for s, xs in R.others_for(rby[p["pkey"]], rparts).items()}

        def finish(y, others=others):
            return DR.average_balance(SB.measure(y), others)
        todo.append(("part", p["pkey"], p, rec, di, finish))
    for e in json.loads(ear_items_path().read_text())["items"]:
        rec = load_note("ear", e["item"], pair)
        di = SB.measure(window_audio(goat_audio(z, e["item"]), e["start_s"])[0])
        todo.append(("ear", e["item"], e, rec, di, SB.measure))
    built, jobs = [], []
    for kind, key, info, rec, di, finish in todo:
        notes, rep = timed_notes(rec, di)
        for arm in NR.REDO_ARMS:
            y, yrep = NR.rebuild_redo(arm, notes, len(di), bank, di, ring, finish=finish)
            y32 = np.asarray(y, np.float32)
            if len(y32) != len(di) or not np.isfinite(y32).all():
                raise SystemExit(f"{key}: a bad {arm} dry guitar")
            path = dry_path(arm, f"{kind}|{key}")
            never_overwrite(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, y32)
            built.append((kind, key, info, arm, notes, rep, yrep, di, y32, NR.file_sha(path)))
            jobs.append((y32, f"{arm}"))
    rt = run_bp(jobs, work / "round-trip")
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "pair": list(pair), "ring_variant": ring,
           "transcribe_sha256": NR.file_sha(transcribe_path()), "parts": {}, "ear": {}}
    for (kind, key, info, arm, notes, rep, yrep, di, y32, sha), r in zip(built, rt):
        got = clean_transcribed(notes_from_events(r["events"]))[0]
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
        row = (out["parts"] if kind == "part" else out["ear"]).setdefault(key, {"timing": rep, "arms": {}})
        row["arms"][arm] = {"sha256": sha, "report": yrep, "figures": figs, "beside": side, **check_verdict(figs)}
    for rows in (out["parts"], out["ear"]):
        for key, row in rows.items():
            row["failed"] = row["arms"]["tr-di"]["failed"]
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    dec, pan, stop = refusal_count(out["parts"], sets_of)
    out.update(refused_deciding=dec, refused_panel=pan, stopped=stop,
               ear_failing=sorted(k for k, r in out["ear"].items() if r["failed"]))
    NR.write_once(build_path(), out)
    print(f"BUILD: {len(out['parts'])} parts and {len(out['ear'])} ear items x {len(NR.REDO_ARMS)} arms; refused "
          f"deciding {len(dec)} {sorted(dec)}{' (STOPPED: no render)' if stop else ''}, panel {sorted(pan)}; ear "
          f"failing {out['ear_failing']}; sha256 {NR.file_sha(build_path())} (into the ledger as {PHASE_DRY})")


def load_dry(arm, key, build, kind="part"):
    """A redo dry guitar, refused unless its sha256 is the one `build` recorded."""
    import numpy as np

    path = dry_path(arm, f"{kind}|{key}")
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
    dest = clips_dir()
    never_overwrite(dest)
    build = json.loads(build_path().read_text())
    if build["ear_failing"]:
        raise SystemExit(f"ear items fail a content check ({build['ear_failing']}): no page until fixed")
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
    ear = json.loads(ear_items_path().read_text())["items"]
    cards = ear_cards([e["item"] for e in ear if e["old"]], {e["kind"]: e["item"] for e in ear if not e["old"]})
    ms = P.A_menu_S()[EAR_AMP]
    trim = (int(PS.TRIM_S * PS.SR), int(round((PS.SEC_S + PS.TRIM_S) * PS.SR)))
    LO._wait_cap()
    dest.mkdir(parents=True)
    index = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "amp": EAR_AMP, "lufs": EAR_LUFS,
             "build_sha256": NR.file_sha(build_path()), "cards": []}
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
        index["cards"].append({**c, "kind": e["kind"], "clips": files})
    NR.write_once(dest / "index.json", index)
    print(f"CLIPS DONE: {len(cards)} cards, {2 * len(cards)} clips, {4 * len(cards)} renders -> {dest}")


COMMANDS = {"set-aside": cmd_set_aside, "install": cmd_install, "install-gate": cmd_install_gate,
            "calibrate": cmd_calibrate, "transcribe": cmd_transcribe, "build": cmd_build,
            "stem-preview": cmd_stem_preview, "clips": cmd_clips}


def main(argv=None):
    import sys

    for p_ in (str(NR.REPO), str(NR.REPO / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
