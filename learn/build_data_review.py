"""Data review 1: a quality-review listening page whose verdicts define the trusted data set.

The user's rule (2026-10-22): "use only what we can trust, no dirty tracks". He hears leaks, other
guitars, hum and wrong parts better than the detectors do, so he reviews the tracks themselves. This
is a review, not a blind test: tracks are named plainly, and no detector or model result is shown.
Development data only (label-table parts of sets 1-3, part C's pool, V_sep, stage F).

    .venv/bin/python -m learn.build_data_review plan [--audit-dir DIR]   # items, zero renders (CPU)
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.build_data_review render  # the few missing doubles renders
    .venv/bin/python -m learn.build_data_review build                      # clips, then one page per sitting
    .venv/bin/python -m learn.build_data_review ingest EXPORT.json         # check an export, merge verdicts

Three sections, in order of value; every clip is cut from source files and levelled to -23 LUFS:

1. **Amp/mic target tracks used as "the original"** (stage F's 21 parts, knob ceiling 2's 24 and
   the parts on listening pages; heavy-metal-only parts are out of scope): each half of the
   10-s crop's `reference.wav`, 6 s around it, with the crop's DI beside it on request. The parts
   the bleed audit (`docs/audits/bleed-2026-10-16/bleed-table.json`) or the data-quality audit's
   crop checks flag come first, with a few low-flag parts mixed in as calibration.
2. **Suspected doubles in the backings** (part C's training pool and V_sep): every distinct take
   pair the doubles rules flag (Cambridge "DT" naming; onset r > 0.6 in at least a quarter of the
   DI's windows; another guitar track beating the own amp track in at least a quarter of at
   least 10 windows; `di-library-match-summary.json`), plus a few unflagged pairs as calibration.
   The target take's amp render, then the partner track at the same moment. Stored renders are
   used where they exist; the rest are rendered once (`render`: one process, isolate=True, a
   discarded priming render first, the machine-wide render cap).
3. **DI tracks** used by the training pool, V_sep and stage F (and Prodigal ElecGtr5, which the
   user flagged for hum): a busy 6-s spot, the audit's borderline-hum DIs first.

Outputs go to ~/ndsp-presets/listening/data-review-1/: `plan.json`, `items.json`, `audio/` (24-bit
FLAC clips), `renders/`, `sitting-N.html` (self-contained, AAC) and `index.html`. Verdicts live in
the browser (localStorage) and leave it as an exported JSON; `ingest` checks one against the items
and merges it into `verdicts.json`.

The pure parts (names, the doubles rules, the ordering, window picks, sittings, the page and the
export check) are unit-tested (`tests/test_build_data_review.py`); the commands that read audio or
render are not, like the other step modules.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import pathlib
import re
import subprocess
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "listening/data-review-1"
PAGE = "data-review-1"
AUDIT_DIR = PLUGIN_ROOT / "docs/audits/data-quality-2026-10-22"
BLEED_TABLE = PLUGIN_ROOT / "docs/audits/bleed-2026-10-16/bleed-table.json"
LABEL_TABLE = PLUGIN_ROOT / "docs/label-table-parts.json"

SR = 48000
TARGET_LUFS = -23.0
PEAK_CEILING_DBTP = -1.0
FADE_S = 0.010
CLIP_S = 6.0
HALF_CLIPS = {"A": (0.5, 6.5), "B": (4.0, 10.0)}   # each covers its judge half (1.0-5.5, 5.5-10.0)
PAIR_PART_S = 4.0                                   # target render, gap, partner: 8.5 s
PAIR_GAP_S = 0.5
DECIDE_S = 4.0                                      # listening time beyond the clip, per item
SITTING_MAX_S = 15 * 60
AAC_KBPS = 128
N_CALIB_PARTS = 4
FRAME_HOP_S = 0.025
FRAME_WIN_S = 0.050
ACTIVE_DB = 25.0                                    # a frame plays when within this of the track's max
FLOOR_DB = -60.0                                    # ... and above this (dBFS RMS): silence never plays

SECTIONS = {
    "amp": {"title": "Amp/mic tracks used as the original",
            "ask": "Is this track clean, or does something else leak in?",
            "verdicts": [("clean", "Clean"), ("bleed", "Drum or other bleed"),
                         ("other_guitar", "Another guitar audible"), ("other", "Other problem")]},
    "pair": {"title": "Possible doubles in the training backings",
             "ask": "First the target take (rendered), then the other track at the same moment. "
                    "Are they the same part played twice?",
             "verdicts": [("double", "Same part (double)"), ("different", "Different part"),
                          ("unsure", "Not sure")]},
    "di": {"title": "DI tracks",
           "ask": "Is the DI clean?",
           "verdicts": [("clean", "Clean"), ("hum", "Hum or noise"), ("clicks", "Clicks or dropouts"),
                        ("odd", "Wrong or odd"), ("other", "Other")]},
}

# Knob ceiling 2's 24 scored parts (`~/ndsp-presets/learn/knob-ceiling-2/stage1/`).
KC2_PARTS = (
    "cambridge-Drag_Me_Down-ElecGtr4", "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1",
    "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2", "cambridge-Passing_Ships-ElecGtr6",
    "cambridge-Prodigal-ElecGtr5", "cambridge-Quicksand-ElecGtr1", "cambridge-Signs-ElecGtr2",
    "cambridge-Today's_The_Day-ElecGtr10", "cambridge-colour-me-red-elecgtr01", "cambridge-femme-elecgtr3",
    "cambridge-get-out-of-bed-elecgtr1", "cambridge-just-don-t-talk-elecgtr3", "cambridge-magilla-elecgtr1dt",
    "telefunken-Blind_Spots-GTR", "telefunken-Bloomlight-GTR", "telefunken-Farthest_Step-GTR",
    "telefunken-First_Offering-GTR_1", "telefunken-First_Offering-GTR_2", "telefunken-Fragments-GTR",
    "telefunken-Gym_Hours-GTR_1", "telefunken-Long_Way_Home-GTR", "telefunken-Russian_Cream-GTR_2",
    "telefunken-Sculptor's_Request-GTR_1", "telefunken-Sculptor's_Request-GTR_2")

# The label-table parts whose amp track was the reference on a listening page under
# ~/ndsp-presets/listening/ (from each page's stored files). The heavy page's 17 heavy-metal parts
# outside the label table are left out: heavy metal is out of scope (2026-10-10).
PAGE_PARTS = {
    "arm A": ("cambridge-Drag_Me_Down-ElecGtr4", "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2",
              "cambridge-Prodigal-ElecGtr5", "cambridge-Today's_The_Day-ElecGtr10",
              "cambridge-colour-me-red-elecgtr01", "cambridge-femme-elecgtr3", "telefunken-Bloomlight-GTR",
              "telefunken-First_Offering-GTR_1", "telefunken-Long_Way_Home-GTR"),
    "average measure": (
        "cambridge-Drag_Me_Down-ElecGtr4", "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2",
        "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3", "cambridge-Passing_Ships-ElecGtr2",
        "cambridge-Passing_Ships-ElecGtr4", "cambridge-Passing_Ships-ElecGtr6", "cambridge-Prodigal-ElecGtr5",
        "cambridge-Quicksand-ElecGtr1", "cambridge-Quicksand-ElecGtr2", "cambridge-Signs-ElecGtr2",
        "cambridge-Today's_The_Day-ElecGtr07", "cambridge-Today's_The_Day-ElecGtr10", "telefunken-Blind_Spots-GTR",
        "telefunken-Bloomlight-GTR", "telefunken-Farthest_Step-GTR", "telefunken-First_Offering-GTR_1",
        "telefunken-First_Offering-GTR_2", "telefunken-Fragments-GTR", "telefunken-Gym_Hours-GTR_1",
        "telefunken-Gym_Hours-GTR_2", "telefunken-Long_Way_Home-GTR", "telefunken-Russian_Cream-GTR_1",
        "telefunken-Russian_Cream-GTR_2", "telefunken-Sculptor's_Request-GTR_1",
        "telefunken-Sculptor's_Request-GTR_2"),
    "bleed": ("cambridge-Drag_Me_Down-ElecGtr4", "telefunken-Farthest_Step-GTR", "telefunken-First_Offering-GTR_1",
              "telefunken-Gym_Hours-GTR_1", "telefunken-Sculptor's_Request-GTR_1"),
    "clean-start volume": (
        "cambridge-Drag_Me_Down-ElecGtr4", "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1",
        "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2", "cambridge-Passing_Ships-ElecGtr6",
        "cambridge-Quicksand-ElecGtr1", "cambridge-colour-me-red-elecgtr02", "cambridge-magilla-elecgtr1",
        "cambridge-wickerman-elecgtr2", "cambridge-wickerman-elecgtr3", "telefunken-Blind_Spots-GTR",
        "telefunken-Bloomlight-GTR", "telefunken-Farthest_Step-GTR", "telefunken-First_Offering-GTR_1",
        "telefunken-First_Offering-GTR_2", "telefunken-Fragments-GTR", "telefunken-Long_Way_Home-GTR",
        "telefunken-Russian_Cream-GTR_2", "telefunken-Sculptor's_Request-GTR_1"),
    "DAC preview": ("cambridge-Today's_The_Day-ElecGtr10", "cambridge-colour-me-red-elecgtr01",
                    "cambridge-femme-elecgtr5"),
    "heavy": ("cambridge-colour-me-red-elecgtr01", "cambridge-femme-elecgtr3", "cambridge-femme-elecgtr5",
              "cambridge-get-out-of-bed-elecgtr1", "cambridge-get-out-of-bed-elecgtr2", "cambridge-let-s-dance-elecgtr3",
              "cambridge-let-s-dance-elecgtr4", "cambridge-wickerman-elecgtr1", "cambridge-wickerman-elecgtr2",
              "cambridge-wickerman-elecgtr3", "cambridge-wickerman-elecgtr7"),
    "knob ceiling": ("cambridge-colour-me-red-elecgtr01", "cambridge-magilla-elecgtr1dt", "telefunken-Bloomlight-GTR",
                     "telefunken-Fragments-GTR", "telefunken-Long_Way_Home-GTR"),
    "knob ceiling 2 effects": (
        "cambridge-Prodigal-ElecGtr5", "cambridge-Signs-ElecGtr2", "cambridge-just-don-t-talk-elecgtr3",
        "telefunken-Blind_Spots-GTR", "telefunken-Farthest_Step-GTR", "telefunken-Gym_Hours-GTR_1",
        "telefunken-Russian_Cream-GTR_2", "telefunken-Sculptor's_Request-GTR_2"),
    "record match": (
        "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3", "cambridge-Passing_Ships-ElecGtr2",
        "cambridge-Passing_Ships-ElecGtr4", "cambridge-Quicksand-ElecGtr2", "cambridge-Signs-ElecGtr3",
        "cambridge-Today's_The_Day-ElecGtr07", "cambridge-colour-me-red-elecgtr02", "cambridge-colour-me-red-elecgtr03",
        "cambridge-femme-elecgtr5", "cambridge-get-out-of-bed-elecgtr2", "cambridge-let-s-dance-elecgtr3",
        "cambridge-let-s-dance-elecgtr4", "cambridge-magilla-elecgtr1", "cambridge-wickerman-elecgtr1",
        "cambridge-wickerman-elecgtr2", "cambridge-wickerman-elecgtr3", "cambridge-wickerman-elecgtr7",
        "telefunken-Gym_Hours-GTR_2", "telefunken-Russian_Cream-GTR_1", "telefunken-She's_Gone-GTR",
        "telefunken-Strangest_Places-GTR"),
    "starting presets": (
        "cambridge-Drag_Me_Down-ElecGtr4", "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1",
        "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2", "cambridge-Passing_Ships-ElecGtr6",
        "cambridge-Prodigal-ElecGtr5", "cambridge-Quicksand-ElecGtr1", "cambridge-Today's_The_Day-ElecGtr10",
        "cambridge-colour-me-red-elecgtr01", "cambridge-colour-me-red-elecgtr02", "cambridge-femme-elecgtr3",
        "cambridge-femme-elecgtr5", "cambridge-get-out-of-bed-elecgtr1", "cambridge-get-out-of-bed-elecgtr2",
        "cambridge-magilla-elecgtr1", "cambridge-wickerman-elecgtr1", "cambridge-wickerman-elecgtr2",
        "telefunken-Blind_Spots-GTR", "telefunken-Bloomlight-GTR", "telefunken-Farthest_Step-GTR",
        "telefunken-First_Offering-GTR_1", "telefunken-First_Offering-GTR_2", "telefunken-Fragments-GTR",
        "telefunken-Long_Way_Home-GTR", "telefunken-Russian_Cream-GTR_2", "telefunken-Sculptor's_Request-GTR_1"),
}

# The DI the user flagged for hum (arm A check, trial 8): knob ceiling 2's crop, put first in section 3.
USER_HUM_PART = "cambridge-Prodigal-ElecGtr5"
# Calibration pairs for section 2: one DI each from three bands, with a stored render, that no doubles
# rule flags, and an unflagged guitar track in its backing playing at the same time (Dom McLennon's
# other guitar is left out of its backings by the leak check); the partner plays most with it.
CALIB_PAIR_DIS = (                                  # in preference order; the first that qualify
    "cambridge/AdamBuckley_DragMeDown_Full/35_ElecGtr5DI.wav",
    "cambridge/AdamBuckley_DragMeDown_Full/31_ElecGtr3DI.wav",
    "cambridge/DarkRide_DeadEnemies_Full/27_ElecGtr09DI.wav",
    "cambridge/DarkRide_DeadEnemies_Full/28_ElecGtr10DI.wav",
    "cambridge/DarkRide_DeadEnemies_Full/29_ElecGtr11DI.wav",
    "cambridge/DeathOfARomantic_TheWell_Full/DeathOfARomantic_TheWell_Full/12_ElecGtr01DI.wav",
    "cambridge/DeathOfARomantic_TheWell_Full/DeathOfARomantic_TheWell_Full/14_ElecGtr02DI.wav",
    "cambridge/EatTheFeeder_TodaysTheDay_Full/41_ElecGtr09DI.wav",
    "cambridge/EatTheFeeder_TodaysTheDay_Full/25_ElecGtr01DI.wav",
    "cambridge/HollowGround_IllFate_Full/HollowGround_IllFate_Full/17_ElecGtr2c_DI.wav",
    "cambridge/StormOfParticles_OfIceAndHopelessFate_Full/StormOfParticles_OfIceAndHopelessFate_Full/17_ElecGtr05DI.wav",
)
CALIB_PAIRS = 3
CALIB_PAIR_SLOTS = (2, 7, 12)                       # their places among the flagged pairs

GUITAR_WORDS = ("gtr", "guitar")
BETTER_MIN, BETTER_MIN_WINDOWS = 0.25, 10           # the "beats its own amp track" rule


def _save(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else None


# --- names (pure) ---------------------------------------------------------------------------------

def track_stem(name):
    """A session file's name without its number prefix, extension and stereo suffix:
    '14_ElecGtr02DT.wav' -> 'ElecGtr02DT', 'GTR Pre Rec.L.wav' -> 'GTR Pre Rec'."""
    s = pathlib.PurePosixPath(name).name
    s = re.sub(r"\.wav$", "", s, flags=re.I)
    s = re.sub(r"\.(L|R)$", "", s)
    return re.sub(r"^\d+_", "", s)


def stereo_siblings(name, files):
    """The file and its other stereo half, if the session has one ('X.L.wav' <-> 'X.R.wav')."""
    m = re.fullmatch(r"(.*)\.(L|R)(\.wav)", name, flags=re.I)
    if not m:
        return [name]
    other = f"{m.group(1)}.{'R' if m.group(2).upper() == 'L' else 'L'}{m.group(3)}"
    return sorted({name, other} & set(files)) or [name]


def dt_counterpart(part):
    """Cambridge's double-track naming: 'ElecGtr02' <-> 'ElecGtr02DT'."""
    return part[:-2] if part.endswith("DT") else part + "DT"


def is_guitar_track(name):
    n = name.lower()
    return any(w in n for w in GUITAR_WORDS) and not re.search(r"(^|[^a-z])di([^a-z]|$)|di\.wav$|d\.wav$", n)


def plain_song(band, song):
    """'DarkRide_DeadEnemies_Full' -> 'Dead Enemies'; plain names are kept."""
    s = str(song or "")
    if "_" not in s:
        return s
    s = re.sub(r"_Full$", "", s)
    parts = s.split("_")
    if len(parts) > 1 and parts[0].replace(" ", "").lower() == str(band).replace(" ", "").lower():
        parts = parts[1:]
    s = " ".join(parts)
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)


def mmss(t):
    t = max(0, int(round(t)))
    return f"{t // 60}:{t % 60:02d}"


# --- section 1: parts and their order (pure) -------------------------------------------------------

def amp_parts(stage_f, kc2=KC2_PARTS, pages=PAGE_PARTS):
    """{slug: [where it is used]} for every part of section 1."""
    out = {}
    for s in stage_f:
        out.setdefault(s, []).append("stage F")
    for s in kc2:
        out.setdefault(s, []).append("knob ceiling 2")
    for page, slugs in pages.items():
        for s in slugs:
            out.setdefault(s, [])
            if "listening pages" not in out[s]:
                out[s].append("listening pages")
    return dict(sorted(out.items()))


def half_flags(bleed_half, crop_half):
    """The flags of one half: the bleed audit's level flag, and the crop checks of the data-quality
    audit (onsets that differ, a reference playing where the DI is silent, a mostly silent DI)."""
    f = []
    if bleed_half.get("flag") in ("high", "moderate"):
        f.append("bleed_" + bleed_half["flag"])
    if crop_half:
        on = crop_half.get("onset_ref_di")
        if isinstance(on, (int, float)) and 0 <= on < 0.35 and crop_half.get("di_play_share", 1) >= 0.5:
            f.append("onsets_differ")
        if (crop_half.get("ref_active_di_silent") or 0) >= 0.3:
            f.append("reference_without_di")
        if (crop_half.get("di_play_share") if crop_half.get("di_play_share") is not None else 1) < 0.5:
            f.append("di_mostly_silent")
    return f


def part_rank(flags_by_half):
    """0: a high-bleed half; 1: a moderate one; 2: another flag; 3: none."""
    fl = [f for fs in flags_by_half.values() for f in fs]
    if "bleed_high" in fl:
        return 0
    if "bleed_moderate" in fl:
        return 1
    return 2 if fl else 3


def order_amp_parts(parts, n_calib=N_CALIB_PARTS):
    """parts: {slug: {"flags": {half: [..]}, "bleed_db": {half: dB}, "band": str, "onset": {half: r}}}.
    -> (ordered slugs, calibration slugs). Flagged parts first (rank, then louder bleed), with
    `n_calib` of the cleanest unflagged parts (one per band) spread among them; the other unflagged
    parts after, louder bleed first."""
    def loud(s):
        return -max(parts[s]["bleed_db"].values())

    flagged = sorted((s for s in parts if part_rank(parts[s]["flags"]) < 3),
                     key=lambda s: (part_rank(parts[s]["flags"]), loud(s), s))
    low = [s for s in parts if part_rank(parts[s]["flags"]) == 3]

    def cleanness(s):
        on = [v for v in parts[s].get("onset", {}).values() if isinstance(v, (int, float)) and v >= 0]
        return (max(parts[s]["bleed_db"].values()), -(min(on) if on else 0), s)

    calib, bands = [], set()
    for s in sorted(low, key=cleanness):
        if len(calib) >= n_calib:
            break
        if parts[s]["band"] in bands:
            continue
        calib.append(s)
        bands.add(parts[s]["band"])
    rest = sorted((s for s in low if s not in calib), key=lambda s: (loud(s), s))
    after = {}                                     # calibration j after the flagged part at an even spacing
    for j, c in enumerate(calib):
        after.setdefault(max(1, round((j + 1) * len(flagged) / (len(calib) + 1))), []).append(c)
    out = []
    for k, s in enumerate(flagged, 1):
        out.append(s)
        out += after.pop(k, [])
    out += [c for k in sorted(after) for c in after[k]] + rest
    return out, calib


# --- section 2: the doubles rules (pure) -----------------------------------------------------------

def take_of_track(track, session_dis):
    """The take a session track records: the part of the DI whose own amp tracks include it, else
    the track's own stem. session_dis: [inventory records of the session's DIs]."""
    for r in session_dis:
        if track in (r.get("own") or []):
            return r["part"]
    return track_stem(track)


def doubles_candidates(scope, summary, inv, session_files):
    """Every (DI, partner track) the doubles rules flag, for the DIs in scope.
    scope: {di id: dataset}; summary: {di id: di_match summary row or None}; inv: {di id: record};
    session_files: {session dir: [file names]}.
    -> [{"di", "partner", "rule", "takes"}], partner a file name, takes the sorted take pair."""
    by_session = {}
    for r in inv.values():
        if r.get("session_dir"):
            by_session.setdefault(r["session_dir"], []).append(r)
    out = []

    def add(di, partner, rule):
        rec = inv[di]
        a = rec["part"]
        b = take_of_track(partner, by_session.get(rec["session_dir"], []))
        if a == b:
            return
        out.append({"di": di, "partner": partner, "rule": rule, "takes": sorted([a, b])})

    for di in sorted(scope):
        rec = inv[di]
        files = session_files.get(rec.get("session_dir"), [])
        if rec.get("source") == "cambridge":
            q = dt_counterpart(rec["part"])
            mates = [r for r in by_session.get(rec["session_dir"], []) if r["part"] == q]
            tracks = sorted({t for r in mates for t in (r.get("own") or [])})
            if not tracks:
                tracks = sorted(f for f in files if track_stem(f) == q and not f.lower().endswith("di.wav"))
            for t in tracks:
                add(di, t, "dt_naming")
        row = summary.get(di)
        if not row:
            continue
        for t in sorted(row.get("hi_other") or {}):
            add(di, t, "onsets_follow")
        top = row.get("top") or []
        if (row.get("n", 0) >= BETTER_MIN_WINDOWS and (row.get("better") or 0) >= BETTER_MIN and top
                and is_guitar_track(top[0][0])):
            add(di, top[0][0], "beats_own_amp")
    return out


def group_pairs(cands):
    """Candidates grouped by (session, take pair) -> [{"key", "takes", "rules", "cands"}], sorted."""
    groups = {}
    for c in cands:
        key = (c.get("session", ""), tuple(c["takes"]))
        g = groups.setdefault(key, {"key": key, "takes": tuple(c["takes"]), "rules": set(), "cands": []})
        g["rules"].add(c["rule"])
        g["cands"].append(c)
    out = []
    for k in sorted(groups):
        g = groups[k]
        g["rules"] = sorted(g["rules"])
        out.append(g)
    return out


def direction_options(cands, in_backing):
    """The ways to play one pair: each (DI, partner track) whose partner is in that DI's backing,
    with the rules that flag it, most rules first. -> [{"di", "partner", "rules"}] (empty: none)."""
    rules = {}
    for c in cands:
        if in_backing(c):
            rules.setdefault((c["di"], c["partner"]), set()).add(c["rule"])
    return [{"di": d, "partner": p, "rules": sorted(rules[(d, p)])}
            for d, p in sorted(rules, key=lambda dp: (-len(rules[dp]), dp))]


def pick_play(scored, min_both=0.5):
    """The best way to play a pair from scored options [(option, stored?, both share, onset r)]:
    both tracks playing (share >= min_both) first, then a stored render (no new render), then
    more of both playing, then onsets that agree. -> the chosen tuple."""
    return sorted(scored, key=lambda x: (x[2] < min_both, not x[1], -round(x[2], 2), -x[3]))[0]


def interleave(items, extra, slots):
    """`extra` placed at `slots` (indices in the result, clipped to the end), in order."""
    out = list(items)
    for e, s in zip(extra, slots):
        out.insert(min(s, len(out)), e)
    return out


# --- windows (pure) -------------------------------------------------------------------------------

def frames_for(seconds, hop_s=FRAME_HOP_S):
    return max(1, int(round(seconds / hop_s)))


def playing(x, active_db=ACTIVE_DB, floor_db=FLOOR_DB, ref_db=None):
    """Frames that play: within `active_db` of the loudest (or `ref_db`) and above `floor_db`."""
    import numpy as np

    x = np.asarray(x, np.float64)
    ref = x.max() if ref_db is None else ref_db
    return (x >= ref - active_db) & (x >= floor_db)


def busiest_window(levels_db, n_win, active_db=ACTIVE_DB, ref_db=None, floor_db=FLOOR_DB):
    """Start frame of the n_win-frame window with the largest share of playing frames (`playing`),
    louder breaking ties. -> (start, share)."""
    import numpy as np

    x = np.asarray(levels_db, np.float64)
    if len(x) <= n_win:
        return 0, float(np.mean(playing(x, active_db, floor_db, ref_db))) if len(x) else 0.0
    ref = x.max() if ref_db is None else ref_db
    act = playing(x, active_db, floor_db, ref).astype(np.float64)
    c_act = np.concatenate([[0.0], np.cumsum(act)])
    c_lev = np.concatenate([[0.0], np.cumsum(np.maximum(x, ref - 60.0))])
    share = (c_act[n_win:] - c_act[:-n_win]) / n_win
    level = (c_lev[n_win:] - c_lev[:-n_win]) / n_win
    best = int(np.lexsort((-level, -np.round(share, 3)))[0])
    return best, float(share[best])


def pair_window(a_db, b_db, n_win, onset_a=None, onset_b=None, active_db=ACTIVE_DB, floor_db=FLOOR_DB):
    """Start frame where both tracks play most (the smaller of their playing shares), then where
    their onsets agree most. -> (start, both share, onset r)."""
    import numpy as np

    a, b = np.asarray(a_db, np.float64), np.asarray(b_db, np.float64)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if n <= n_win:
        return 0, 0.0, 0.0
    aa = playing(a, active_db, floor_db).astype(np.float64)
    bb = playing(b, active_db, floor_db).astype(np.float64)
    ca, cb = np.concatenate([[0.0], np.cumsum(aa)]), np.concatenate([[0.0], np.cumsum(bb)])
    both = np.minimum(ca[n_win:] - ca[:-n_win], cb[n_win:] - cb[:-n_win]) / n_win
    corr = np.zeros(len(both))
    if onset_a is not None and onset_b is not None:
        oa, ob = np.asarray(onset_a, np.float64)[:n], np.asarray(onset_b, np.float64)[:n]
        for s in range(len(both)):
            x, y = oa[s:s + n_win], ob[s:s + n_win]
            if x.std() > 0 and y.std() > 0:
                corr[s] = float(np.corrcoef(x, y)[0, 1])
    best = int(np.lexsort((-corr, -np.round(both, 2)))[0])
    return best, float(both[best]), float(corr[best])


# --- sittings, ids and the export (pure) -----------------------------------------------------------

def est_seconds(item):
    return float(item["clip_s"]) + DECIDE_S


def split_sittings(durations, max_s=SITTING_MAX_S):
    """Contiguous sittings of about equal length, none longer than about `max_s`. -> [[indices]]."""
    if not durations:
        return []
    total = float(sum(durations))
    k = max(1, math.ceil(total / max_s - 1e-9))
    target = total / k
    out = [[] for _ in range(k)]
    acc = 0.0
    for i, d in enumerate(durations):
        out[min(k - 1, int((acc + d / 2) / target))].append(i)   # by the item's midpoint: contiguous
        acc += d
    return [s for s in out if s]


def item_id(kind, *parts):
    """A stable id: the kind and a short digest of what the item plays."""
    return f"{kind}-" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


def check_export(obj, items):
    """An exported answer file against the items. -> ({id: {"verdict", "note"}}, [problems])."""
    probs = []
    if not isinstance(obj, dict) or obj.get("page") != PAGE:
        return {}, [f"not a {PAGE} export"]
    by_id = {it["id"]: it for it in items}
    out = {}
    for a in obj.get("answers", []):
        i = a.get("id")
        if i not in by_id:
            probs.append(f"unknown item {i!r}")
            continue
        allowed = {v for v, _ in SECTIONS[by_id[i]["section"]]["verdicts"]}
        v = a.get("verdict")
        if v is not None and v not in allowed:
            probs.append(f"{i}: verdict {v!r} is not one of {sorted(allowed)}")
            continue
        note = (a.get("note") or "").strip()
        if v is None and not note:
            continue
        out[i] = {"verdict": v, "note": note}
    return out, probs


def merge_verdicts(existing, new, stamp):
    """Later answers replace earlier ones per item; each keeps when it was merged."""
    out = dict(existing or {})
    for i, a in new.items():
        out[i] = dict(a, merged=stamp)
    return out


# --- the page (pure) ------------------------------------------------------------------------------

FORBIDDEN_ON_PAGE = ("bleed_db", "flag", "contam", "onset r", "hi_other", "beats_own", "dt_naming",
                     "onsets_follow", "calibration", "D_stem", "judge", "log d", "model")


def page_html(sitting, n_sittings, items, audio, build):
    """One self-contained sitting page. items: the sitting's items (public fields only); audio:
    {key: base64 AAC}; build: a digest of the clips."""
    secs = []
    cur = None
    for k, it in enumerate(items):
        if it["section"] != cur:
            cur = it["section"]
            s = SECTIONS[cur]
            secs.append(f'<h2 class="sec">{html.escape(s["title"])}</h2>'
                        f'<p class="ask">{html.escape(s["ask"])}</p>')
        buttons = "".join(f'<button type="button" class="v" data-v="{v}">{html.escape(lab)}</button>'
                          for v, lab in SECTIONS[it["section"]]["verdicts"])
        extra = "".join(f'<button type="button" class="play small" data-clip="{html.escape(c)}">'
                        f'{html.escape(lab)}</button>' for lab, c in it.get("extra", []))
        cue = (f' data-cue="{PAIR_PART_S:.2f},{PAIR_GAP_S:.2f}"' if it["section"] == "pair" else "")
        secs.append(
            f'<article class="item" data-id="{html.escape(it["id"])}" data-n="{k + 1}">'
            f'<div class="num">{k + 1} / {len(items)}</div>'
            f'<h3>{html.escape(it["title"])}</h3><p class="sub">{html.escape(it["subtitle"])}</p>'
            f'<div class="plays"><button type="button" class="play main" data-clip="{html.escape(it["clip"])}"{cue}>'
            f'&#9654; Play</button>{extra}</div><p class="now"></p>'
            f'<div class="vs">{buttons}</div>'
            f'<input class="note" type="text" placeholder="Note (optional)" aria-label="Note"></article>')
    minutes = sum(est_seconds(it) for it in items) / 60
    data = json.dumps({"page": PAGE, "sitting": sitting, "build": build,
                       "items": [{"id": it["id"], "section": it["section"], "title": it["title"],
                                  "subtitle": it["subtitle"]} for it in items]}, ensure_ascii=False)
    clips = json.dumps(audio)
    return (PAGE_TEMPLATE.replace("{{SITTING}}", str(sitting)).replace("{{N_SITTINGS}}", str(n_sittings))
            .replace("{{COUNT}}", str(len(items))).replace("{{MINUTES}}", f"{minutes:.0f}")
            .replace("{{ITEMS}}", "\n".join(secs)).replace("{{DATA}}", data.replace("</", "<\\/"))
            .replace("{{CLIPS}}", clips))


def page_leaks(page):
    """Detector or model words the page must not show (its text, without the embedded clips)."""
    text = re.sub(r'"[A-Za-z0-9+/=]{200,}"', '""', page)
    text = text.split("<script>", 1)[0]
    return sorted({w for w in FORBIDDEN_ON_PAGE if re.search(r"(?<![\w-])" + re.escape(w), text, re.I)})


PAGE_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Data review, sitting {{SITTING}}</title>
<style>
:root { --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#fff; --on:#1d1d1b;
        --on-fg:#fff; --accent:#2f6f4f; --bar:#e9e6de; }
@media (prefers-color-scheme: dark) { :root { --bg:#171716; --fg:#ecebe6; --muted:#a19f97; --line:#34332f;
  --card:#201f1d; --on:#ecebe6; --on-fg:#171716; --accent:#7fc4a0; --bar:#2c2b28; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
       font:17px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
header { position:sticky; top:0; z-index:5; background:var(--card); border-bottom:1px solid var(--line);
         padding:10px 16px calc(10px); }
.prog { height:6px; background:var(--bar); border-radius:3px; overflow:hidden; margin-top:6px; }
.prog > div { height:100%; width:0; background:var(--accent); }
.hrow { display:flex; gap:10px; align-items:center; justify-content:space-between; flex-wrap:wrap; }
.hrow label { font-size:15px; display:flex; gap:6px; align-items:center; }
main { max-width:720px; margin:0 auto; padding:8px 16px 140px; }
h1 { font-size:1.2rem; margin:14px 0 4px; }
h2.sec { font-size:1.1rem; margin:28px 0 2px; }
.ask, .intro { color:var(--muted); margin:2px 0 10px; }
.item { border:1px solid var(--line); border-radius:12px; background:var(--card); padding:12px 14px;
        margin:12px 0; scroll-margin-top:90px; }
.item.done { opacity:.72; }
.item.current { outline:2px solid var(--accent); }
.num { color:var(--muted); font-size:14px; }
h3 { font-size:1.02rem; margin:2px 0; }
.sub { color:var(--muted); margin:0 0 8px; font-size:15px; }
.plays { display:flex; gap:8px; flex-wrap:wrap; }
button { font:inherit; color:var(--fg); }
.play { min-height:52px; border-radius:10px; border:1px solid var(--line); background:var(--bg); padding:0 18px; }
.play.main { flex:1 1 60%; font-weight:600; }
.play.small { flex:1 1 30%; font-size:15px; }
.play.on { background:var(--on); color:var(--on-fg); }
.now { min-height:1.3em; margin:4px 0; color:var(--accent); font-size:15px; }
.vs { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.v { min-height:56px; border-radius:10px; border:1px solid var(--line); background:var(--bg); padding:6px; }
.v[aria-pressed="true"] { background:var(--on); color:var(--on-fg); border-color:var(--on); }
.note { width:100%; margin-top:8px; font:inherit; font-size:16px; padding:10px; border-radius:8px;
        border:1px solid var(--line); background:var(--bg); color:var(--fg); }
footer { position:fixed; left:0; right:0; bottom:0; z-index:5; background:var(--card); border-top:1px solid var(--line);
         padding:10px 16px calc(10px + env(safe-area-inset-bottom)); display:flex; gap:8px; }
footer button { flex:1; min-height:48px; border-radius:10px; border:1px solid var(--line); background:var(--bg); }
footer button.primary { background:var(--on); color:var(--on-fg); }
#exp { display:none; position:fixed; inset:0; z-index:9; background:var(--bg); padding:16px; overflow:auto; }
#exp textarea { width:100%; height:50vh; font:13px ui-monospace, monospace; padding:8px; background:var(--card);
                color:var(--fg); border:1px solid var(--line); border-radius:8px; }
#exp .row { display:flex; gap:8px; margin:10px 0; }
#exp .row button { flex:1; min-height:48px; border-radius:10px; border:1px solid var(--line); background:var(--bg); }
</style></head><body>
<header><div class="hrow"><b>Data review &middot; sitting {{SITTING}} of {{N_SITTINGS}}</b>
<span id="count"></span></div>
<div class="hrow"><label><input type="checkbox" id="auto"> Autoplay next</label>
<span id="left" class="ask"></span></div><div class="prog"><div id="bar"></div></div></header>
<main>
<h1>Which tracks can we trust?</h1>
<p class="intro">{{COUNT}} short clips, about {{MINUTES}} minutes. Each clip is at the same loudness
(&minus;23 LUFS). Tap Play, then the answer that fits; add a note if something is worth saying. Answers
are saved on this phone as you go. With <b>Autoplay next</b> on, an answer moves on and plays the next clip.
When you finish (or stop), tap <b>Export</b> and send the text.</p>
{{ITEMS}}
</main>
<footer><button type="button" id="next">Next unanswered</button>
<button type="button" id="export" class="primary">Export</button></footer>
<div id="exp"><b>Your answers</b><p class="ask">Copy this and send it, or save it as a file.</p>
<textarea id="out" readonly></textarea>
<div class="row"><button type="button" id="copy">Copy</button><button type="button" id="save">Save file</button>
<button type="button" id="close">Close</button></div></div>
<audio id="player" preload="none" playsinline></audio>
<script id="data" type="application/json">{{DATA}}</script>
<script>
const DATA = JSON.parse(document.getElementById("data").textContent);
const CLIPS = {{CLIPS}};
const KEY = DATA.page + "/answers";
const AUTO = DATA.page + "/autoplay";
let store = {};
try { store = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) {} };
const items = [...document.querySelectorAll(".item")];
const player = document.getElementById("player");
const urls = {};
let playing = null;
function url(key) {
  if (!urls[key]) {
    const bin = atob(CLIPS[key]); const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    urls[key] = URL.createObjectURL(new Blob([buf], {type: "audio/mp4"}));
  }
  return urls[key];
}
function stop() {
  player.pause();
  if (playing) { playing.classList.remove("on"); const n = playing.closest(".item").querySelector(".now"); n.textContent = ""; }
  playing = null;
}
function play(btn) {
  if (playing === btn && !player.paused) { stop(); return; }
  stop();
  items.forEach(i => i.classList.remove("current"));
  btn.closest(".item").classList.add("current");
  player.src = url(btn.dataset.clip);
  playing = btn; btn.classList.add("on");
  player.play().catch(() => {});
}
player.addEventListener("ended", stop);
player.addEventListener("timeupdate", () => {
  if (!playing || !playing.dataset.cue) return;
  const [part, gap] = playing.dataset.cue.split(",").map(Number);
  const t = player.currentTime;
  playing.closest(".item").querySelector(".now").textContent =
    t < part ? "Now: the target take (rendered)" : t < part + gap ? "" : "Now: the other track";
});
document.querySelectorAll(".play").forEach(b => b.addEventListener("click", () => play(b)));
function paint() {
  let n = 0;
  items.forEach(it => {
    const a = store[it.dataset.id] || {};
    it.querySelectorAll(".v").forEach(b => b.setAttribute("aria-pressed", String(a.verdict === b.dataset.v)));
    const note = it.querySelector(".note");
    if (document.activeElement !== note) note.value = a.note || "";
    it.classList.toggle("done", !!a.verdict);
    if (a.verdict) n++;
  });
  document.getElementById("count").textContent = n + " / " + items.length + " done";
  document.getElementById("bar").style.width = (100 * n / items.length) + "%";
  const left = items.length - n;
  document.getElementById("left").textContent = left ? "about " + Math.max(1, Math.round(left * 10 / 60)) + " min left" : "all answered";
}
function nextOpen(from) {
  const k = items.indexOf(from);
  for (let j = 1; j <= items.length; j++) {
    const it = items[(k + j) % items.length];
    if (!(store[it.dataset.id] || {}).verdict) return it;
  }
  return null;
}
function go(it, autoplay) {
  if (!it) return;
  it.scrollIntoView({behavior: "smooth", block: "start"});
  if (autoplay) play(it.querySelector(".play.main"));
  else { items.forEach(i => i.classList.remove("current")); it.classList.add("current"); }
}
items.forEach(it => {
  it.querySelectorAll(".v").forEach(b => b.addEventListener("click", () => {
    const id = it.dataset.id; const a = store[id] || {};
    a.verdict = a.verdict === b.dataset.v ? null : b.dataset.v; a.t = new Date().toISOString();
    store[id] = a; save(); paint();
    if (a.verdict && document.getElementById("auto").checked) go(nextOpen(it), true);
  }));
  it.querySelector(".note").addEventListener("input", e => {
    const id = it.dataset.id; const a = store[id] || {};
    a.note = e.target.value; a.t = new Date().toISOString(); store[id] = a; save();
  });
});
const auto = document.getElementById("auto");
try { auto.checked = localStorage.getItem(AUTO) === "1"; } catch (e) {}
auto.addEventListener("change", () => { try { localStorage.setItem(AUTO, auto.checked ? "1" : "0"); } catch (e) {} });
document.getElementById("next").addEventListener("click", () => {
  const cur = document.querySelector(".item.current") || items[items.length - 1];
  go(nextOpen(cur), auto.checked);
});
function exportText() {
  const answers = DATA.items.map(i => ({id: i.id, section: i.section, title: i.title, subtitle: i.subtitle,
    verdict: (store[i.id] || {}).verdict || null, note: (store[i.id] || {}).note || "", t: (store[i.id] || {}).t || null}));
  return JSON.stringify({page: DATA.page, sitting: DATA.sitting, build: DATA.build,
    exported: new Date().toISOString(), answered: answers.filter(a => a.verdict).length,
    total: answers.length, answers: answers}, null, 1);
}
document.getElementById("export").addEventListener("click", () => {
  stop(); document.getElementById("out").value = exportText();
  document.getElementById("exp").style.display = "block";
});
document.getElementById("close").addEventListener("click", () => { document.getElementById("exp").style.display = "none"; });
document.getElementById("copy").addEventListener("click", async () => {
  const t = document.getElementById("out");
  try { await navigator.clipboard.writeText(t.value); } catch (e) { t.select(); document.execCommand("copy"); }
});
document.getElementById("save").addEventListener("click", () => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([exportText()], {type: "application/json"}));
  a.download = DATA.page + "-sitting-" + DATA.sitting + ".json";
  document.body.appendChild(a); a.click(); a.remove();
});
paint();
</script></body></html>
"""

INDEX_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data review</title>
<style>
:root { --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#fff; }
@media (prefers-color-scheme: dark) { :root { --bg:#171716; --fg:#ecebe6; --muted:#a19f97; --line:#34332f; --card:#201f1d; } }
body { margin:0; background:var(--bg); color:var(--fg); font:17px/1.5 -apple-system, BlinkMacSystemFont, sans-serif; }
main { max-width:640px; margin:0 auto; padding:24px 16px; }
a.s { display:block; border:1px solid var(--line); border-radius:12px; background:var(--card); padding:14px 16px;
      margin:10px 0; color:var(--fg); text-decoration:none; }
.m { color:var(--muted); }
</style></head><body><main>
<h1>Data review</h1>
<p class="m">Three kinds of clips: amp tracks used as the original, possible doubles in the training
backings, and DI tracks. Your answers decide which tracks we trust. About 15 minutes or less per sitting.</p>
{{LINKS}}
</main></body></html>
"""


# --- audio (I/O) ----------------------------------------------------------------------------------

def load(path, start_s, dur_s):
    """Mono float64 at SR from a source file, zero-padded to the asked length."""
    import numpy as np

    from learn import pretrain_set as PS

    a = max(0.0, start_s)
    x = PS.load_mono(path, SR, a, dur_s - (a - start_s)).astype(np.float64)
    if start_s < 0:
        x = np.concatenate([np.zeros(int(round(-start_s * SR))), x])
    n = int(round(dur_s * SR))
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def frame_levels(x, sr=SR, hop_s=FRAME_HOP_S, win_s=FRAME_WIN_S):
    import numpy as np

    hop, win = int(round(hop_s * sr)), int(round(win_s * sr))
    if len(x) < win:
        return np.array([-120.0])
    fr = np.lib.stride_tricks.sliding_window_view(np.asarray(x, np.float64), win)[::hop]
    return 10 * np.log10(np.mean(fr ** 2, axis=1) + 1e-12)


def onset_env(levels_db):
    import numpy as np

    x = np.maximum(np.asarray(levels_db, np.float64), np.max(levels_db) - 50)
    return np.maximum(np.diff(x, prepend=x[:1]), 0)


def level_clip(x):
    """One static gain to TARGET_LUFS (iterated over BS.1770's gate), lowered if the true peak
    would pass PEAK_CEILING_DBTP. -> (y, gain dB, LUFS after, peak-limited dB)."""
    import numpy as np

    from analysis import io

    def lufs(y):
        return io.loudness_lufs(io.from_samples(y.reshape(-1, 1), SR))

    l0 = lufs(x)
    if l0 is None:
        return x, 0.0, None, 0.0
    g = TARGET_LUFS - l0
    for _ in range(4):
        l1 = lufs(x * 10 ** (g / 20))
        if l1 is None or abs(l1 - TARGET_LUFS) < 0.05:
            break
        g += TARGET_LUFS - l1
    y = x * 10 ** (g / 20)
    pk = io.true_peak_dbtp(io.from_samples(y.reshape(-1, 1), SR))
    cut = 0.0
    if pk is not None and pk > PEAK_CEILING_DBTP:
        cut = pk - PEAK_CEILING_DBTP
        y = y * 10 ** (-cut / 20)
    return y, g - cut, lufs(y), cut


def fade(x):
    import numpy as np

    n = int(round(FADE_S * SR))
    y = np.array(x, np.float64)
    if len(y) > 2 * n:
        r = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))
        y[:n] *= r
        y[-n:] *= r[::-1]
    return y


def aac_b64(flac, cache):
    """AAC (mono, AAC_KBPS) of a FLAC clip, cached by the clip's hash, as base64."""
    h = hashlib.sha256(pathlib.Path(flac).read_bytes()).hexdigest()[:16]
    out = pathlib.Path(cache) / f"{h}.m4a"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(out.stem + ".tmp.m4a")
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", str(AAC_KBPS * 1000), str(flac), str(tmp)],
                       check=True)
        tmp.replace(out)
    return base64.b64encode(out.read_bytes()).decode()


# --- plan (I/O, zero renders) ---------------------------------------------------------------------

def _crop_part(lt, slug):
    p = dict(lt[slug])
    p["crop"] = pathlib.Path(p["crop"])
    rec = json.loads((p["crop"] / "record.json").read_text())
    p["song"], p["part"] = rec.get("song"), rec.get("part")
    p["start_s"] = float(rec.get("excerpt_start_s", 0.0))
    p["n_amp_tracks"] = len(rec.get("removed_own_amp_tracks") or []) or 1
    return p


def heldout_ok(slugs):
    """Sets 1-3 catalogues (arm_a_mega53's fail-closed check, without its set 4-6 step: every part
    here is a label-table part of sets 1-2 or 3, and set 4-6 material is not opened)."""
    from learn import arm_a_mega53 as A

    lt = json.loads(LABEL_TABLE.read_text())["parts"]
    cat12 = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    cat3 = json.loads((PLUGIN_ROOT / "docs/validation-set3.json").read_text())
    ledger3 = json.loads((PLUGIN_ROOT / "docs/set3-heldout-use-ledger.json").read_text())
    bad = {}
    for s, probs in A.heldout_problems(slugs, lt, cat12, cat3, ledger3, None).items():
        probs = [p for p in probs if p != "no set 4–6 check supplied"]
        if probs:
            bad[s] = probs
    for s in slugs:
        if lt.get(s, {}).get("set") not in (12, 3):
            bad.setdefault(s, []).append("not a set 1-2 or 3 label-table part")
    if bad:
        raise SystemExit(f"held-out check failed (fail closed): {bad}")


def _amp_items(audit_dir):
    from learn import arm_a_mega53 as A

    lt = json.loads(LABEL_TABLE.read_text())["parts"]
    used = amp_parts(A.pool_slugs())
    heldout_ok(sorted(used))
    bleed = json.loads(BLEED_TABLE.read_text())
    crop = {}
    cm = pathlib.Path(audit_dir) / "label-table-crop-match.jsonl"
    if cm.exists():
        for line in cm.read_text().splitlines():
            if line.strip():
                r = json.loads(line.replace("NaN", "null"))
                crop[r["slug"]] = r["halves"]
    else:
        print(f"note: {cm} not found; ordering by the bleed audit alone", flush=True)
    parts = {}
    for s in used:
        halves = bleed[s]["halves"]
        parts[s] = {"band": lt[s]["band"],
                    "flags": {h: half_flags(halves[h], crop.get(s, {}).get(h)) for h in "AB"},
                    "bleed_db": {h: float(halves[h].get("bleed_db", -99)) for h in "AB"},
                    "onset": {h: (crop.get(s, {}).get(h) or {}).get("onset_ref_di") for h in "AB"}}
    order, calib = order_amp_parts(parts)
    items = []
    for s in order:
        p = _crop_part(lt, s)
        for h in "AB":
            if halves_silent(bleed[s]["halves"][h]):
                continue
            a, b = HALF_CLIPS[h]
            mics = "amp track" if p["n_amp_tracks"] == 1 else f"{p['n_amp_tracks']} amp mics summed"
            items.append({
                "id": item_id("amp", s, h), "section": "amp", "slug": s, "half": h,
                "title": f"{p['band']} · {p['song']} · {p['part']}",
                "subtitle": f"{'First' if h == 'A' else 'Second'} half, {mmss(p['start_s'] + a)}–"
                            f"{mmss(p['start_s'] + b)} · {mics} · used in {', '.join(used[s])}",
                "clip_s": b - a,
                "src": {"main": [{"path": str(p["crop"] / "reference.wav"), "start_s": a, "dur_s": b - a}],
                        "di": [{"path": str(p["crop"] / "di.wav"), "start_s": a, "dur_s": b - a}]},
                "private": {"flags": parts[s]["flags"][h], "bleed_db": parts[s]["bleed_db"][h],
                            "calibration": s in calib, "used_in": used[s]}})
    return items


def halves_silent(h):
    return h.get("flag") == "silent"


def _scope():
    """{di id: [datasets]} for part C's training pool and V_sep; and the pool's sections by DI."""
    from learn import arm_a_mega53 as A
    from learn import pretrain_set as PS

    p = PS.pool()
    if not PS.manifest_ok(p["manifest_sha256"]):
        raise SystemExit("part C's pool was built from the pre-amendment manifest")
    F = set(A.F_POOL)
    scope, secs = {}, {}
    for s in p["sections"]:
        if s.get("source") == "guitar-techs" or "P3" in str(s.get("path", "")):
            raise SystemExit(f"{s['id']}: Guitar-TECHS in the pool")
        if s["split"] == "train":
            ds = "training pool"
        elif s["split"] == "val" and s["band"] not in F:
            ds = "V_sep"
        else:
            continue
        if ds not in scope.setdefault(s["di"], []):
            scope[s["di"]].append(ds)
        secs.setdefault(s["di"], []).append(s)
    return scope, secs


def _stored_renders():
    """{section id: [(example i, base, mode, path, scale)]}: the gate's truth renders (R_in) and part
    C's audit renders, both the 10-s section aligned to its start."""
    from learn import pretrain_set as PS

    out = {}
    gd = HOME / "learn/direct-stems/gate"
    for f in sorted((gd / "rows").glob("truth-*.jsonl")):
        for r in PS.read_rows(f):
            if r.get("refused") or "scale" not in r:
                continue
            path = gd / "truth" / f"{int(r['i']) // 1000:04d}" / f"{int(r['i']):07d}.flac"
            if path.exists():
                out.setdefault(r["section"], []).append((r["i"], r["base"], None, str(path), float(r["scale"])))
    for i, r in PS.all_rows().items():
        f = PS.example_path(i).with_suffix(".flac")
        if r.get("audit") and f.exists():
            out.setdefault(r["section"], []).append((i, r["base"], r["mode"], str(f), r["peak"] / 0.99))
    rows = PS.all_rows()
    for r in _load(OUT / "renders" / "renders.json") or []:       # this page's own renders, once made
        path = OUT / "renders" / f"{int(r['i']):07d}.flac"
        if path.exists():
            out.setdefault(r["section"], []).append((r["i"], r["base"], rows[r["i"]]["mode"], str(path),
                                                     float(r["scale"])))
    for v in out.values():
        v.sort()
    return out


def _pick_example(cands):
    """A clean-based example first (its render is the plainest), then the lowest index."""
    return sorted(cands, key=lambda c: (c[1] != "clean", c[2] not in (None, "start", "factory"), c[0]))[0]


def _stored_audio(st):
    import numpy as np
    import soundfile as sf

    i, base, mode, path, scale = _pick_example(st)
    y, _ = sf.read(path, dtype="float64")
    y = y.mean(axis=1) if y.ndim == 2 else y
    return (i, path, scale), np.asarray(y, np.float64) * float(scale)


def _window(target, partner_paths, start_s, n_win):
    """(start frame, both-playing share, onset r) for a 10-s target and the partner at start_s."""
    import numpy as np

    b = sum(load(p, start_s, 10.0) for p in partner_paths)
    la, lb = frame_levels(target), frame_levels(np.asarray(b))
    return pair_window(la, lb, n_win, onset_env(la), onset_env(lb))


def _pair_items():
    """Section 2's items and the renders they still need."""
    from learn import pretrain_set as PS

    inv = {r["id"]: r for r in json.loads(PS.INVENTORY.read_text())["dis"]}
    scope, secs = _scope()
    summary_rows = json.loads((AUDIT_DIR / "di-library-match-summary.json").read_text())
    summary = {k: v for k, v in summary_rows}
    files = {}
    for di in scope:
        sd = inv[di].get("session_dir")
        if sd and sd not in files:
            files[sd] = sorted(f.name for f in pathlib.Path(sd).glob("*.wav"))
    cands = doubles_candidates(scope, summary, inv, files)
    for c in cands:
        c["session"] = inv[c["di"]]["session_dir"]
    leak = _load(PS.OUT / "leakage.json") or {}
    stored = _stored_renders()
    n_win = frames_for(PAIR_PART_S)

    def backing(di):
        rec = inv[di]
        keep, _ = PS.backing_tracks(rec, files[rec["session_dir"]], (leak.get(di) or {}).get("dropped", ()))
        return set(keep)

    def in_backing(c):
        return c["partner"] in backing(c["di"])

    def score(opt):
        """Every section of the option's DI (those with a stored render, if any): the target is the
        stored render where there is one, else the DI. -> [(option+section, stored?, both, r)]."""
        di = opt["di"]
        rec = inv[di]
        sd = pathlib.Path(rec["session_dir"])
        group = stereo_siblings(opt["partner"], files[rec["session_dir"]])
        with_st = [s for s in secs[di] if stored.get(s["id"])]
        out = []
        for s in with_st or secs[di]:
            st = stored.get(s["id"])
            if st:
                ref, target = _stored_audio(st)
            else:
                ref, target = None, load(rec["path"], float(s["start_s"]), 10.0)
            w, both, r = _window(target, [sd / g for g in group], float(s["start_s"]), n_win)
            out.append(({**opt, "section": s, "group": group, "w": w, "ref": ref}, bool(st), both, r))
        return out

    pairs, skipped = [], []
    for g in group_pairs(cands):
        opts = direction_options(g["cands"], in_backing)
        if not opts:
            skipped.append({"takes": list(g["takes"]), "session": g["key"][0], "why": "partner not in the backing"})
            continue
        best = pick_play([x for o in opts for x in score(o)])
        pairs.append((best, {"takes": list(g["takes"]), "all_rules": g["rules"], "calibration": False}))
    rank = {"training pool": 0, "V_sep": 1}
    pairs.sort(key=lambda p: (min(rank.get(d, 2) for d in scope[p[0][0]["di"]]), p[0][0]["section"]["id"],
                              p[1]["takes"]))
    flagged_takes = {(c["session"], t) for c in cands for t in c["takes"]}
    calib, bands = [], set()
    for di in CALIB_PAIR_DIS:
        rec = inv[di]
        if len(calib) >= CALIB_PAIRS or rec["band"] in bands or (rec["session_dir"], rec["part"]) in flagged_takes:
            continue
        mates = [r for r in inv.values() if r.get("session_dir") == rec["session_dir"]]
        others = sorted(t for t in backing(di) if is_guitar_track(t)
                        and (rec["session_dir"], take_of_track(t, mates)) not in flagged_takes)
        scored = [x for t in others for x in score({"di": di, "partner": t, "rules": []})]
        scored = [x for x in scored if x[1] and x[2] >= 0.5]       # stored, and both playing
        if not scored:
            continue
        best = pick_play(scored)
        calib.append((best, {"takes": None, "all_rules": [], "calibration": True}))
        bands.add(rec["band"])
    if len(calib) < CALIB_PAIRS:
        raise SystemExit(f"only {len(calib)} calibration pairs found")
    items, needs = [], []
    rows_by_section = {}
    for (opt, stored_, both, r), meta in interleave(pairs, calib, CALIB_PAIR_SLOTS):
        rec = inv[opt["di"]]
        sd = pathlib.Path(rec["session_dir"])
        s, partner, group = opt["section"], opt["partner"], opt["group"]
        t0 = opt["w"] * FRAME_HOP_S
        if stored_:
            i, path, scale = opt["ref"]
            render = {"i": i, "path": path, "scale": scale, "stored": True}
        else:
            if not rows_by_section:
                for x in PS.all_rows().values():
                    rows_by_section.setdefault(x["section"], []).append(x)
            ex = _pick_example([(x["i"], x["base"], x["mode"], None, None) for x in rows_by_section[s["id"]]])
            render = {"i": ex[0], "path": str(OUT / "renders" / f"{ex[0]:07d}.flac"), "scale": None, "stored": False}
            needs.append({"i": ex[0], "section": s["id"], "path": render["path"]})
        mates = [x for x in inv.values() if x.get("session_dir") == rec["session_dir"]]
        takes = meta["takes"] or [rec["part"], take_of_track(partner, mates)]
        pname = track_stem(partner) + (" (L+R)" if len(group) > 1 else "")
        start = float(s["start_s"]) + t0
        items.append({
            "id": item_id("pair", rec["session_dir"], rec["part"], partner),
            "section": "pair",
            "title": f"{rec['band']} · {plain_song(rec['band'], rec['song'])} · {rec['part']} and {pname}",
            "subtitle": f"{rec['part']} rendered from its DI, then the {pname} track, at {mmss(start)}",
            "clip_s": 2 * PAIR_PART_S + PAIR_GAP_S,
            "src": {"render": {**render, "offset_s": t0, "dur_s": PAIR_PART_S},
                    "partner": [{"path": str(sd / g), "start_s": start, "dur_s": PAIR_PART_S} for g in group]},
            "private": {"di": opt["di"], "partner": partner, "takes": takes, "rules": meta["all_rules"],
                        "direction_rules": opt["rules"], "calibration": meta["calibration"],
                        "datasets": scope.get(opt["di"]), "section": s["id"],
                        "both_playing_share": round(both, 3), "onset_r": round(r, 3)}})
    return items, needs, skipped


def _di_items():
    """Section 3: every DI of the training pool, V_sep and stage F (and the user's hum flag)."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import pretrain_set as PS

    inv = {r["id"]: r for r in json.loads(PS.INVENTORY.read_text())["dis"]}
    man = json.loads(PS.MANIFEST.read_text())
    hum = {}
    for r in man["sections"]:
        h = (r.get("measures") or {}).get("hum_rel_db")
        if "slight_hum" in (r.get("tags") or []) and h is not None:
            key = (r["di"], float(r["start_s"]))
            hum[key] = float(h)
    scope, secs = _scope()
    lt = json.loads(LABEL_TABLE.read_text())["parts"]
    crops = {s: ["stage F"] for s in A.pool_slugs()}
    crops.setdefault(USER_HUM_PART, []).append("knob ceiling 2 and listening pages")
    heldout_ok(sorted(crops))
    entries = []
    for di, ds in scope.items():
        rec = inv[di]
        hums = {float(s["start_s"]): hum[(di, float(s["start_s"]))] for s in secs[di]
                if (di, float(s["start_s"])) in hum}
        regions = ([(rec["path"], max(hums, key=hums.get))] if hums
                   else [(rec["path"], float(s["start_s"])) for s in secs[di]])
        entries.append({"key": di, "band": rec["band"], "song": plain_song(rec["band"], rec["song"]),
                        "part": rec["part"], "file": pathlib.PurePosixPath(di).name, "datasets": ds,
                        "regions": regions, "offset": 0.0, "hum_db": max(hums.values()) if hums else None,
                        "user_flag": False})
    by_key = {e["key"]: e for e in entries}
    for slug, ds in crops.items():
        p = _crop_part(lt, slug)
        src = next((r for r in inv.values() if r.get("slug") == slug), None)
        if src is not None and src["id"] in by_key:          # the same DI track: one item
            by_key[src["id"]]["datasets"] += [d for d in ds if d not in by_key[src["id"]]["datasets"]]
            continue
        h = None
        if src is not None:
            vals = [v for (d, st), v in hum.items() if d == src["id"]]
            h = max(vals) if vals else None
        entries.append({"key": "crop:" + slug, "band": p["band"], "song": p["song"], "part": p["part"],
                        "file": "crop DI", "datasets": ds, "regions": [(str(p["crop"] / "di.wav"), 0.0)],
                        "offset": p["start_s"], "hum_db": h, "user_flag": slug == USER_HUM_PART})
    n_win = frames_for(CLIP_S)
    items = []
    for e in entries:
        best = None
        for path, st in e["regions"]:
            x = load(path, st, 10.0)
            lv = frame_levels(x)
            w, share = busiest_window(lv, n_win)
            key = (-round(share, 2), -float(np.mean(lv[w:w + n_win])))
            if best is None or key < best[0]:
                best = (key, path, st + w * FRAME_HOP_S, share)
        _, path, start, share = best
        e["clip"] = {"path": path, "start_s": start, "dur_s": CLIP_S}
        e["at"] = e["offset"] + start
        e["share"] = share
    first = [e for e in entries if e["user_flag"]]
    humm = sorted((e for e in entries if e["hum_db"] is not None and not e["user_flag"]),
                  key=lambda e: (-e["hum_db"], e["key"]))
    order = {"stage F": 0, "V_sep": 1, "training pool": 2}
    rest = sorted((e for e in entries if e["hum_db"] is None and not e["user_flag"]),
                  key=lambda e: (min(order.get(d, 3) for d in e["datasets"]) if e["datasets"] else 3,
                                 e["band"], e["song"], e["part"], e["key"]))
    for e in first + humm + rest:
        items.append({
            "id": item_id("di", e["key"]), "section": "di",
            "title": f"{e['band']} · {e['song']} · {e['part']} DI",
            "subtitle": f"{e['file']} at {mmss(e['at'])} · used in {', '.join(e['datasets'])}",
            "clip_s": CLIP_S, "src": {"main": [e["clip"]]},
            "private": {"key": e["key"], "hum_db": e["hum_db"], "user_flag": e["user_flag"],
                        "playing_share": round(e["share"], 3), "datasets": e["datasets"]}})
    return items


def cmd_plan(args):
    global AUDIT_DIR
    AUDIT_DIR = pathlib.Path(args.audit_dir).expanduser()
    if not (AUDIT_DIR / "di-library-match-summary.json").exists():
        raise SystemExit(f"{AUDIT_DIR} has no di-library-match-summary.json (the data-quality audit, PR #272)")
    t0 = time.time()
    amp = _amp_items(AUDIT_DIR)
    pairs, needs, skipped = _pair_items()
    dis = _di_items()
    items = amp + pairs + dis
    ids = [it["id"] for it in items]
    if len(set(ids)) != len(ids):
        raise SystemExit("two items share an id")
    plan = {"page": PAGE, "audit_dir": str(AUDIT_DIR), "items": items, "renders_needed": needs,
            "pairs_skipped": skipped,
            "counts": {k: sum(it["section"] == k for it in items) for k in SECTIONS}}
    _save(OUT / "plan.json", plan)
    print(json.dumps(plan["counts"]), f"renders needed {len(needs)}", f"pairs skipped {len(skipped)}",
          f"({time.time() - t0:.0f} s)")
    print("PLAN DONE")


# --- render (the few missing doubles renders) ---------------------------------------------------

def cmd_render(_args):
    """One process, isolate=True, a discarded priming render before each kept one, after waiting for
    the machine-wide render cap (`local_objective._wait_cap`). Each render is part C's example:
    its section's measure DI through its drawn settings, checked against part C's stored mels."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B

    plan = _load(OUT / "plan.json")
    if plan is None:
        raise SystemExit("run `plan` first")
    todo = [n for n in plan["renders_needed"] if not pathlib.Path(n["path"]).exists()]
    print("renders to do", len(todo), flush=True)
    if not todo:
        print("RENDER DONE")
        return
    secs = {s["id"]: s for s in PS.pool()["sections"]}
    rows = PS.all_rows()
    LO._wait_cap()
    rr = K.Renderer()
    if rr.r.isolate is not True:
        raise SystemExit("the renderer is not isolating renders")
    log = []
    try:
        menu = rr.menu()
        for n in todo:
            i = n["i"]
            r = rows[i]
            rng, amp, mode, base = PS.plan_example(i)
            sel, x, label, _ = PS.settings_for(rng, amp, mode, base, menu, K.START, K.space, K.fmt)
            if {f"{a}/{b}": v for (a, b), v in x.items()} != r["settings"]:
                raise SystemExit(f"{i}: settings differ from part C's row")
            s = secs[n["section"]]
            di = B.measure(PS.section_audio(s["path"], s["start_s"])).astype(np.float32)
            y = PS.primed_render(rr, di, sel, x)
            y = (y.mean(axis=1) if y.ndim == 2 else y)[int(PS.TRIM_S * PS.SR):int((PS.TRIM_S + PS.SEC_S) * PS.SR)]
            stored = np.load(PS.example_path(i))
            share = min(DS.match_share(m, stored[f"g{h}"]) for h, m in PS.halves_mel(y).items())
            from learn import direct_sound_gate as G

            scale, sha = G.write_flac(pathlib.Path(n["path"]), y, PS.SR)
            log.append({"i": i, "section": n["section"], "amp": amp, "base": base, "mode": mode,
                        "mel_match_share": round(share, 4), "scale": scale, "sha256": sha})
            print(log[-1], flush=True)
    finally:
        rr.close()
    old = _load(OUT / "renders" / "renders.json") or []
    _save(OUT / "renders" / "renders.json", old + log)
    print(f"RENDER DONE ({rr.count} renders, {len(log)} kept)")


# --- build -----------------------------------------------------------------------------------------

def _render_audio(src):
    import numpy as np
    import soundfile as sf

    if src["stored"]:
        y, sr = sf.read(src["path"], dtype="float64")
        y = y * float(src["scale"])
    else:
        log = {r["i"]: r for r in (_load(OUT / "renders" / "renders.json") or [])}
        if src["i"] not in log:
            raise SystemExit(f"render {src['i']} is missing: run `render`")
        y, sr = sf.read(src["path"], dtype="float64")
        y = y * float(log[src["i"]]["scale"])
    if sr != SR:
        raise SystemExit(f"{src['path']}: {sr} Hz")
    y = y.mean(axis=1) if y.ndim == 2 else y
    a = int(round(src["offset_s"] * SR))
    n = int(round(src["dur_s"] * SR))
    return np.pad(y[a:a + n], (0, max(0, n - len(y[a:a + n]))))


def _mix(srcs):
    return sum(load(s["path"], s["start_s"], s["dur_s"]) for s in srcs)


def cmd_build(_args):
    import numpy as np
    import soundfile as sf

    plan = _load(OUT / "plan.json")
    if plan is None:
        raise SystemExit("run `plan` first")
    audio_dir, cache = OUT / "audio", OUT / "aac"
    audio_dir.mkdir(parents=True, exist_ok=True)
    items = plan["items"]
    levels = {}

    def write(name, x):
        y, g, l, cut = level_clip(np.asarray(x, np.float64))
        y = fade(y)
        p = audio_dir / f"{name}.flac"
        sf.write(str(p), y.astype(np.float32), SR, subtype="PCM_24")
        levels[name] = {"gain_db": round(g, 2), "lufs": None if l is None else round(l, 2),
                        "peak_cut_db": round(cut, 2)}
        return p

    for it in items:
        if it["section"] == "pair":
            r = write(it["id"] + "-render", _render_audio(it["src"]["render"]))
            p = write(it["id"] + "-partner", _mix(it["src"]["partner"]))
            ra, pa = sf.read(str(r))[0], sf.read(str(p))[0]
            gap = np.zeros(int(round(PAIR_GAP_S * SR)))
            m = audio_dir / f"{it['id']}.flac"
            sf.write(str(m), np.concatenate([ra, gap, pa]).astype(np.float32), SR, subtype="PCM_24")
            it["clip"] = it["id"]
            it["extra"] = [["Render only", it["id"] + "-render"], ["Other track only", it["id"] + "-partner"]]
        else:
            write(it["id"], _mix(it["src"]["main"]))
            it["clip"] = it["id"]
            it["extra"] = []
            if "di" in it["src"]:
                write(it["id"] + "-di", _mix(it["src"]["di"]))
                it["extra"] = [["Its DI", it["id"] + "-di"]]
    durations = [est_seconds(it) for it in items]
    sittings = split_sittings(durations)
    public = [{k: it[k] for k in ("id", "section", "title", "subtitle", "clip_s", "clip", "extra")} for it in items]
    pages = []
    for n, idx in enumerate(sittings, 1):
        its = [public[i] for i in idx]
        keys = [it["clip"] for it in its] + [c for it in its for _, c in it["extra"]]
        audio = {k: aac_b64(audio_dir / f"{k}.flac", cache) for k in keys}
        build = hashlib.sha256("".join(audio[k][:4096] for k in keys).encode()).hexdigest()[:12]
        page = page_html(n, len(sittings), its, audio, build)
        leaks = page_leaks(page)
        if leaks:
            raise SystemExit(f"sitting {n}'s page shows {leaks}")
        out = OUT / f"sitting-{n}.html"
        out.write_text(page)
        minutes = sum(durations[i] for i in idx) / 60
        counts = {k: sum(items[i]["section"] == k for i in idx) for k in SECTIONS}
        pages.append({"sitting": n, "file": out.name, "items": len(idx), "minutes": round(minutes, 1),
                      "by_section": counts, "mb": round(out.stat().st_size / 1e6, 1), "build": build})
        print(f"{out} ({pages[-1]['mb']} MB, {len(idx)} items, about {minutes:.0f} min)", flush=True)
    links = "\n".join(
        f'<a class="s" href="{p["file"]}"><b>Sitting {p["sitting"]}</b><br><span class="m">{p["items"]} clips, '
        f'about {p["minutes"]:.0f} min · ' + ", ".join(f"{v} {SECTIONS[k]['title'].lower()}"
                                                       for k, v in p["by_section"].items() if v) + "</span></a>"
        for p in pages)
    (OUT / "index.html").write_text(INDEX_TEMPLATE.replace("{{LINKS}}", links))
    for it in items:
        it["levels"] = {k: v for k, v in levels.items() if k == it["id"] or k.startswith(it["id"] + "-")}
    _save(OUT / "items.json", {"page": PAGE, "target_lufs": TARGET_LUFS, "sittings": pages,
                               "counts": plan["counts"], "minutes": round(sum(durations) / 60, 1),
                               "items": items})
    print(json.dumps({"counts": plan["counts"], "sittings": [(p["items"], p["minutes"]) for p in pages],
                      "minutes": round(sum(durations) / 60, 1)}))
    print("BUILD DONE")


def cmd_ingest(args):
    items = (_load(OUT / "items.json") or {}).get("items")
    if not items:
        raise SystemExit("run `build` first")
    obj = json.loads(pathlib.Path(args.export).expanduser().read_text())
    new, probs = check_export(obj, items)
    if probs:
        raise SystemExit("the export does not fit the items: " + "; ".join(probs[:10]))
    path = OUT / "verdicts.json"
    old = _load(path) or {"page": PAGE, "verdicts": {}}
    old["verdicts"] = merge_verdicts(old["verdicts"], new, time.strftime("%Y-%m-%dT%H:%M:%S"))
    _save(path, old)
    print(f"merged {len(new)} answers; {len(old['verdicts'])} of {len(items)} items answered")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--audit-dir", default=str(AUDIT_DIR))
    sub.add_parser("render")
    sub.add_parser("build")
    p = sub.add_parser("ingest")
    p.add_argument("export")
    args = ap.parse_args(argv)
    {"plan": cmd_plan, "render": cmd_render, "build": cmd_build, "ingest": cmd_ingest}[args.cmd](args)


if __name__ == "__main__":
    main()
