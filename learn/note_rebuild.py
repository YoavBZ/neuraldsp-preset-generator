"""A dry guitar rebuilt from a song's notes (`docs/note-rebuild-plan.md`; ledger `note-rebuild`).

Direction 1 of the strategic review searches the plugin's settings at song time through a dry guitar that plays the
song's notes. The note-matched replay (`preset-ladder` `phase_replay`) tests that search with a blurred copy of the
true DI. This module builds the dry guitar from notes alone: read the notes, play each one back from EGFxSet's single
recorded DI notes (a Stratocaster, CC BY 4.0), and level and balance the result as the measure does. It trains
nothing.

Stage P (this file's commands; zero renders, separations, downloads and training; `phase_nr_p`):

    .venv/bin/python -m learn.note_rebuild exclusion     # P1: every DI file, capture, creator and lent session
    .venv/bin/python -m learn.note_rebuild notes         # P2: EGFxSet's 690 clean notes checked
    .venv/bin/python -m learn.note_rebuild true-notes    # P3: GOAT's tab + fine-aligned MIDI per ladder unit
    .venv/bin/python -m learn.note_rebuild probe         # P7: seconds per 10-s window, on the CPU
    .venv/bin/python -m learn.note_rebuild ready         # NP_TABLE's code from P1-P4's records

P4 (the re-synthesis) is the pure functions below, tested in `tests/test_note_rebuild.py` on made-up note lists.

The coded tables for stages 1-3 (`N1_TABLE`, `N2_TABLE`, `N3_TABLE`) and the two-number reading (`row_reading`) are
declared here before any stage runs; stages 1 and 2 are run only under their own reviewed declarations (P8), and only
after the replay's gate reads "pass".

Every output is written once and never overwritten (`write_once`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
HOME = pathlib.Path(os.path.expanduser("~/ndsp-presets"))
PF = HOME / "learn/trusted-data/pipeline-fix"
OUT = PF / "note-rebuild"
PLAN = "docs/note-rebuild-plan.md"
LEDGER_ID = "note-rebuild"
PHASE_P = "phase_nr_p"

SR = 48000
EGFX = HOME / "references/datasets/egfxset/Clean"
GOAT_ZIP = HOME / "references/datasets-goat/_zips/GOAT.zip"
LENDS = PF / "ladder/lends.json"

# --- the note set (P2) -------------------------------------------------------------------------------------------------

PICKUPS = ("Bridge", "Bridge-Middle", "Middle", "Middle-Neck", "Neck")
PICKUP = "Middle"                       # the riff library's position: EGFxSet's quietest (least hiss)
OPEN_STRINGS = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}   # string 1 the high E (build_riffs.OPEN_STRINGS)
FRETS = range(0, 23)                    # EGFxSet: frets 0-22 on every string
NOTE_RULES = {                          # P2's pass rules for one note, fixed before any note is read
    "max_abs_cents": 50.0,              # further than this from its nominal pitch: the wrong note
    "max_clipped": 0,                   # samples at or above 0.999 of full scale
    "attack_by_s": 1.0,                 # the attack must be found inside the first second
    "max_hum_db": -40.0,                # the mains series (50 or 60 Hz, harmonics 1-4) under the note's attack level
    "rate": SR,
    "seconds": 5.0,
}
ATTACK_FRAC = 0.1                       # an attack: the first sample past a tenth of the first second's peak

# --- the re-synthesis (P4), every rule frozen here ---------------------------------------------------------------------

DENOISE_ABOVE_HZ = 3000.0               # the riff library's lesson: noisereduce, non-stationary, above 3 kHz only
NOTE_FADE_IN_S = 0.002
PRE_ATTACK_S = 0.002                    # each sample starts this far before its measured attack
CHORD_S = 0.050                         # onsets this close form one chord: the onset groups, the tab matching and the
                                        # clean-up's merge share it (GOAT's fine alignment spreads a chord up to ~50 ms)
END_FADE_S = 0.020                      # a note ends at its MIDI note-off with this fade (the mute)
REPLUCK_FADE_S = 0.010                  # ... or when its string is plucked again
EDGE_FADE_S = 0.010                     # the dry guitar fades in and out over its window's first and last 10 ms
END_PAD_S = 0.100                       # rebuild_dry synthesises and finishes this much past the window, then trims it
                                        # back: the end fade and the finishing filters' edge (4,096 taps) fall in the pad
TAIL_FADE_S = 0.150                     # a note held past its sample's end fades over the sample's last 150 ms
DEAD_S, DEAD_DB = 0.040, -6.0           # a dead note: a 40 ms pluck, 6 dB down
PALM_S = 0.150                          # a palm-muted note: held at most 150 ms
LEGATO_DB = -6.0                        # hammer-on, pull-off or slide-into: no pick attack, 6 dB down
GHOST_DB = -10.0
EARLY_S = 0.300                         # a sample's own pitch is read over its first 300 ms from the attack
MAX_SHIFT_SEMITONES = 2                 # a note may be resampled this far from its sample's pitch, no further
LEVEL_SPAN_S = 0.050                    # `nr-level` and `nr-oracle` read the 50 ms after each onset group
LEVEL_CLAMP_DB = 9.0                    # `nr-level`'s gain about the window's median, held within +-9 dB
ORACLE_CLAMP_DB = 20.0
REFINE_S = 0.050                        # the oracle onset step: each onset snapped within +-50 ms of the true DI's rise
REFINE_MIN_RISE_DB = 3.0                # ... only where the rise is at least this; else the MIDI onset is kept
REFINE_FRAME = 96                       # 2 ms frames, 1 ms hop (48 samples)
REFINE_HP_HZ = 1000.0
ASSUMED_LUFS = -22.9                    # the measure's DI level (`di_robustness.ASSUMED_LUFS`)
TUNING_BAND_HZ = (80.0, 1400.0)
MIDI_RANGE = (40, 88)                   # a guitar in standard tuning

ARMS = ("nr-plain", "nr-level", "nr-oracle")    # stage 1's three dry guitars (`nr-oracle` a diagnostic only)
ARTICULATIONS = ("bend", "slide", "hammer", "vibrato", "harmonic", "dead", "ghost_note", "palm_mute", "grace",
                 "tremoloPicking")      # a tab note with any of these (or a tremolo-bar beat) is "articulated"

# --- the readings (the replay's two-number bar, the user's rule of 2026-11-20) -----------------------------------------

PASS_MEAN = -0.10
FAIL_EDGE = -0.05


def row_reading(g, i):
    """(Pure.) A row's reading under the replay's declared `row_reading` (its plan, section C.8): G is the pick less
    Cen, I the pick less the blind pick, each {mean, lo90, hi90}. "passes": each decided better (the whole 90%
    interval below 0) with its mean at -0.10 or beyond; "fails": G's or I's interval rules out a gain beyond -0.05
    (its lower end at -0.05 or above); else "undecided". When the replay's `learn/note_replay.py` is merged, stage 1's
    code imports its `row_reading` and `tests/test_note_rebuild.py` asserts the two agree on a grid."""
    for r in (g, i):
        if not r or r.get("lo90") is None or r.get("hi90") is None or r.get("mean") is None:
            raise ValueError("a row needs mean, lo90 and hi90 for both G and I")
    if all(r["hi90"] < 0 and r["mean"] <= PASS_MEAN for r in (g, i)):
        return "passes"
    if any(r["lo90"] >= FAIL_EDGE for r in (g, i)):
        return "fails"
    return "undecided"


def unreadable(r):
    """(Pure.) An interval inside +-0.05: worded "not readable by the score"."""
    return r["lo90"] >= -0.05 and r["hi90"] <= 0.05


READINGS = ("passes", "fails", "undecided")

NP_TABLE = (    # stage P: (code, when, next)
    ("NP-ready", "P1 to P4 pass and at least 30 of the replay's GOAT units carry true notes",
     "wait for the replay's gate"),
    ("NP-few", "P1 to P4 pass and fewer than 30 of the replay's GOAT units carry true notes",
     "stage 1's declaration adds revision-pool units (cap1 on GOAT items not among the replay's) by a seeded rule, "
     "fixed before any render; to the orchestrator"),
    ("NP-gap", "the note set has failed notes at the middle pickup (P2)", "the placing rule avoids them; the gaps are "
     "listed in stage 1's declaration; NP-ready or NP-few follows it by the count (`np_code` returns both)"),
    ("NP-broken", "P1, P3 or P4 fails its own checks", "stop; fix and re-declare"),
)

# Stage 1: rows by arm; the deciding arms are nr-plain and nr-level (two arms share the units: false pass at most
# 10%); nr-oracle is read beside and never decides.
N1_TABLE = (    # (code, when, next)
    ("N1-pass", "nr-plain or nr-level passes",
     "stage 2 with the simpler passing arm (nr-plain if both); nr-oracle and the breakdowns reported beside"),
    ("N1-fail", "nr-plain and nr-level both fail",
     "the re-synthesis with true notes, oracle onsets and the tab's strings does not pick a heard size better; with "
     "nr-oracle's row and the breakdowns (alignment-F tertile, brand, articulated share, mask agreement) to the user: "
     "the guided or the network route, or stop. The reading is audited adversarially before it is written up"),
    ("N1-between", "any other combination",
     "undecided, not failed; to the user with each arm's share of the GOAT-alone Blurred row's I; one revision allowed, "
     "declared first, read on fresh units only (the revision pool)"),
)

N2_ROWS = ("B-clean", "B-alone", "B-full")      # stage 2's rows, run in order, each only after a pass of the one before
N2_TABLE = (    # (code, when, next): read on the rows that ran (each ran only after a pass of the one before)
    ("N2-full", "B-full passes", "stage 3"),
    ("N2-exposed", "B-alone passes, B-full fails",
     "to the user and stop: it would work only on windows where the target is the only or dominant guitar, and no "
     "automatic finder of such windows exists (picking them by ear is a human step, ruled out); a finder needs its own "
     "declaration first"),
    ("N2-stem", "B-clean passes, B-alone fails",
     "the separator's output breaks the notes: stop, to the user; separator and transcription work get a preset-level "
     "yardstick"),
    ("N2-notes", "B-clean fails, after N1-pass",
     "the transcriber's accuracy is the gap: the dose read (stage 1's true notes with notes dropped, added and shifted "
     "at three declared levels), then to the user"),
    ("N2-between", "any row that ran reads undecided",
     "undecided, not failed: to the user with shares and intervals; one revision allowed, on fresh units"),
)

N3_TABLE = (    # (code, when, next): a one-sided sign test at 5% on the untied cards, for each comparison
    ("N3-heard", "the rebuilt-DI pick is ranked above Cen and above the blind menu setting",
     "a search through the rebuilt DI (from Cen, against the stem) with fresh held-half renders through the true DI, "
     "under its own declaration; not product wiring"),
    ("N3-blind", "above Cen but not above the blind menu setting",
     "heard over Cen without the comparison working: stop, to the user"),
    ("N3-not-heard", "Cen ranked above the pick", "the score's gain is not heard: stop, to the user"),
    ("N3-between", "anything else", "undecided, to the user"),
)


def n1_code(plain, level):
    """(Pure.) N1_TABLE's code from the two deciding arms' readings."""
    for r in (plain, level):
        if r not in READINGS:
            raise ValueError(f"not a reading: {r}")
    if "passes" in (plain, level):
        return "N1-pass"
    if plain == "fails" and level == "fails":
        return "N1-fail"
    return "N1-between"


def n1_arm(plain, level):
    """(Pure.) The arm stage 2 carries on N1-pass: nr-plain if it passes, else nr-level."""
    if n1_code(plain, level) != "N1-pass":
        return None
    return "nr-plain" if plain == "passes" else "nr-level"


def n2_next_row(done):
    """(Pure.) The next stage-2 row to run given the readings so far ({row: reading}), or None: each row runs only
    after a pass of the one before."""
    for k, row in enumerate(N2_ROWS):
        if row not in done:
            return row if all(done.get(r) == "passes" for r in N2_ROWS[:k]) else None
    return None


def n2_code(done):
    """(Pure.) N2_TABLE's code from the rows read (in order); None while a row is due."""
    if n2_next_row(done) is not None:
        return None
    ran = [done[r] for r in N2_ROWS if r in done]
    if not ran:
        return None
    for r in ran:
        if r not in READINGS:
            raise ValueError(f"not a reading: {r}")
    if "undecided" in ran:
        return "N2-between"
    c, a, f = (done.get(r) for r in N2_ROWS)
    if c == "fails":
        return "N2-notes"
    if a == "fails":
        return "N2-stem"
    return "N2-full" if f == "passes" else "N2-exposed"


def sign_test_p(wins, losses):
    """(Pure.) One-sided sign test: P(X >= wins) for X ~ Bin(wins + losses, 1/2)."""
    n = wins + losses
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n


def n3_code(vs_cen, vs_blind, alpha=0.05):
    """(Pure.) N3_TABLE's code. `vs_cen`, `vs_blind`: (cards the pick is ranked above, cards below), ties left out."""
    up_cen = sign_test_p(*vs_cen) < alpha
    down_cen = sign_test_p(vs_cen[1], vs_cen[0]) < alpha
    up_blind = sign_test_p(*vs_blind) < alpha
    if down_cen:
        return "N3-not-heard"
    if up_cen and up_blind:
        return "N3-heard"
    if up_cen:
        return "N3-blind"
    return "N3-between"


def table_guard():
    """Refuse unless every table's codes are as declared and every reading pair or row state maps to exactly one."""
    if [c for c, *_ in NP_TABLE] != ["NP-ready", "NP-few", "NP-gap", "NP-broken"]:
        raise SystemExit("NP_TABLE's codes are not the four declared")
    if {c for c, *_ in N1_TABLE} != {"N1-pass", "N1-fail", "N1-between"}:
        raise SystemExit("N1_TABLE's codes are not the three declared")
    for p in READINGS:
        for lv in READINGS:
            if n1_code(p, lv) not in {c for c, *_ in N1_TABLE}:
                raise SystemExit("n1_code leaves a pair unmapped")
    if {c for c, *_ in N2_TABLE} != {"N2-full", "N2-exposed", "N2-stem", "N2-notes", "N2-between"}:
        raise SystemExit("N2_TABLE's codes are not the five declared")
    if {c for c, *_ in N3_TABLE} != {"N3-heard", "N3-blind", "N3-not-heard", "N3-between"}:
        raise SystemExit("N3_TABLE's codes are not the four declared")
    if not PASS_MEAN < FAIL_EDGE < 0:
        raise SystemExit("the bar is not PASS_MEAN < FAIL_EDGE < 0")


# --- plumbing -----------------------------------------------------------------------------------------------------------

def ledger_entry():
    d = json.loads((REPO / "docs" / "dev-test-ledger.json").read_text())
    return next((t for t in d["tests"] if t["test_id"] == LEDGER_ID), None)


def require(phase):
    e = ledger_entry()
    if not e or phase not in e:
        raise SystemExit(f"the ledger's {LEDGER_ID} entry has no {phase}: declare it before running")
    return e


def refuse_existing(path):
    path = pathlib.Path(path)
    if path.exists():
        raise SystemExit(f"{path} exists: never overwritten (move it aside to rebuild)")


def write_once(path, obj):
    """Write JSON once; refuse to overwrite."""
    path = pathlib.Path(path)
    refuse_existing(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=str) + "\n")
    tmp.replace(path)
    return content_sha(obj)


def content_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def file_sha(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def bytes_sha(b):
    return hashlib.sha256(b).hexdigest()


# --- P1: the exclusion list ---------------------------------------------------------------------------------------------

GUITAR_WORDS = ("gtr", "guitar")
TRANSCRIBER_TRAINED_ON = ("medleydb", "guitarset")      # Basic Pitch's guitar training sources


def is_guitar_track(name):
    n = name.lower()
    return n.endswith((".wav", ".flac", ".aif", ".aiff")) and any(w in n for w in GUITAR_WORDS)


def exclusion_keys(units, lends):
    """(Pure.) The identity keys every built, tuned or trained input must avoid, from C3r's read units
    (`full_controls_c3r.read_units`, as dicts with set, unit, prt) and the ladder's lends ({unit: {section, band}}).
    -> {kind: sorted list}."""
    keys = {"di": set(), "goat_item": set(), "capture": set(), "creator": set(), "session": set(), "band": set(),
            "pack": set()}
    for r in units:
        p = r["prt"]
        keys["di"].add(p["di"])
        di = p["di"]
        if di.startswith("goat/"):
            keys["goat_item"].add(di.split("/", 1)[1])
        if p.get("di_item", "").startswith("item_"):
            keys["goat_item"].add(p["di_item"])
        if p.get("item", "").startswith("item_"):
            keys["goat_item"].add(p["item"])
        if p.get("capture"):
            keys["capture"].add(p["capture"])
        if p.get("creator"):
            keys["creator"].add(p["creator"])
        if p.get("pack"):
            keys["pack"].add(p["pack"])
        if p.get("band"):
            keys["band"].add(p["band"])
        if "/" in di and not di.startswith(("goat/", "panel/")):
            keys["session"].add(di.rsplit("/", 1)[0])
    for v in lends.values():
        keys["session"].add(v["section"].split("@", 1)[0].rsplit("/", 1)[0])
        keys["band"].add(v["band"])
    return {k: sorted(v) for k, v in keys.items()}


def transcriber_overlap(units):
    """(Pure.) The read units whose material a released transcriber was trained on (MedleyDB, GuitarSet): {unit:
    source}. The panel is MedleyDB (set 6)."""
    out = {}
    for r in units:
        src = (r["prt"].get("source") or "").lower()
        hit = [s for s in TRANSCRIBER_TRAINED_ON if s in src]
        if hit or r["set"] == "panel":
            out[f"{r['unit']}|{r['amp']}"] = hit[0] if hit else "medleydb (the panel, set 6)"
    return out


def clear_of(candidate, excl):
    """(Pure.) The exclusion entries a candidate input hits, [] when clear. `candidate`: any of di, goat_item, capture,
    creator, session, band, pack (strings) and sha256 (a file hash)."""
    hits = []
    for k in ("di", "goat_item", "capture", "creator", "session", "band", "pack"):
        v = candidate.get(k)
        if v and v in set(excl["keys"].get(k, ())):
            hits.append(f"{k}={v}")
    sha = candidate.get("sha256")
    if sha and sha in set(excl["sha256"]):
        hits.append(f"sha256={sha[:12]}")
    return hits


def assert_clear(candidates, excl=None):
    """Refuse unless every candidate is clear of the exclusion list (P1); used by every build, tune or train step."""
    excl = excl or load_exclusion()
    bad = {i: h for i, c in enumerate(candidates) if (h := clear_of(c, excl))}
    if bad:
        raise SystemExit(f"{len(bad)} inputs hit the ladder's exclusion list, e.g. {next(iter(bad.values()))}")
    return True


def load_doc(name):
    """A stage-P record, refused unless its body matches its stored hash."""
    p = OUT / name
    if not p.exists():
        raise SystemExit(f"{p} missing: run its command first")
    d = json.loads(p.read_text())
    if content_sha(d["body"]) != d["body_sha256"]:
        raise SystemExit(f"{name}'s body does not match its hash")
    return d["body"]


def load_exclusion():
    return load_doc("exclusion.json")


def find_session_dirs(sessions, roots):
    """{session key: directory} by the key's last path part, searched under `roots` (depth 5)."""
    want = {s.rsplit("/", 1)[-1]: s for s in sessions}
    found = {}
    for root in roots:
        root = pathlib.Path(root)
        if not root.exists():
            continue
        for dirpath, dirnames, _ in os.walk(root):
            if dirpath[len(str(root)):].count(os.sep) > 5:
                dirnames[:] = []
                continue
            base = os.path.basename(dirpath)
            if base in want and want[base] not in found:
                found[want[base]] = dirpath
    return found


def cmd_exclusion(_args):
    """P1. Every DI file, GOAT item, capture, creator, pack, band and session under the ladder's 480 parts, and the six
    lent sessions with their guitar tracks; sha256 of every DI section, DI source, capture render and guitar track on
    disk. Any unit's section missing on disk, or a session not found, is recorded and makes `p1_ok` false (NP-broken).
    -> note-rebuild/exclusion.json."""
    require(PHASE_P)
    refuse_existing(OUT / "exclusion.json")
    import zipfile                                  # after the refusals

    from learn import full_controls_c3r as C

    units = C.read_units()
    lends = json.loads(LENDS.read_text())["units"]
    keys = exclusion_keys(units, lends)
    sha, files, missing = set(), {}, []

    def add(path, why):
        path = str(path)
        if path in files:
            return
        if not os.path.exists(path):
            missing.append({"path": path, "why": why})
            return
        h = file_sha(path)
        files[path] = {"sha256": h, "why": why}
        sha.add(h)

    for r in units:
        p = r["prt"]
        add(p["di_path"], f"{r['set']} DI section")
        if p.get("sd") and p.get("track"):
            add(os.path.join(p["sd"], p["track"]), f"{r['set']} amp section")
    zips = {}
    with zipfile.ZipFile(GOAT_ZIP) as z:
        for it in keys["goat_item"]:
            for suffix in (".wav", "_amp_1.wav", "_amp_2.wav", "_amp_3.wav", "_amp_4.wav", "_amp_5.wav"):
                n = f"GOAT/data/{it}/{it}{suffix}"
                try:
                    zi = z.getinfo(n)
                except KeyError:
                    continue
                zips[n] = {"crc32": f"{zi.CRC:08x}", "size": zi.file_size}
    roots = [HOME / "references" / d for d in os.listdir(HOME / "references") if d.startswith("datasets")]
    sdirs = find_session_dirs(keys["session"], roots)
    tracks = {}
    for s, d in sorted(sdirs.items()):
        for dirpath, _, fnames in os.walk(d):
            for f in sorted(fnames):
                if is_guitar_track(f):
                    fp = os.path.join(dirpath, f)
                    add(fp, f"session {s} guitar track")
                    tracks.setdefault(s, []).append(fp)
    body = {"keys": keys, "sha256": sorted(sha), "files": files, "goat_zip_members": zips,
            "sessions_found": sdirs, "sessions_missing": sorted(set(keys["session"]) - set(sdirs)),
            "session_guitar_tracks": tracks, "transcriber_overlap": transcriber_overlap(units),
            "units": len(units), "lent_units": len(lends), "missing": missing}
    body["p1_ok"] = p1_ok(body)
    doc = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P}", "made": time.strftime("%Y-%m-%d %H:%M:%S"),
           "body": body, "body_sha256": content_sha(body)}
    h = write_once(OUT / "exclusion.json", doc)
    print(f"EXCLUSION DONE: {', '.join(f'{k} {len(v)}' for k, v in keys.items())}; {len(sha)} file hashes; "
          f"{len(zips)} GOAT zip members; sessions found {len(sdirs)} of {len(keys['session'])}; "
          f"transcriber overlap {len(body['transcriber_overlap'])} parts; missing {len(missing)}; "
          f"p1_ok {body['p1_ok']}; doc sha256 {h}")


def p1_ok(body):
    """(Pure.) P1 passes its own checks: 480 units read, every key kind but pack non-empty, no unit's file missing on
    disk, every session found and holding at least one guitar track."""
    k = body["keys"]
    return (body["units"] == EXPECTED_UNITS and all(k[x] for x in ("di", "goat_item", "capture", "creator", "session"))
            and not body["missing"] and not body["sessions_missing"]
            and all(body["session_guitar_tracks"].get(s) for s in k["session"]))


EXPECTED_UNITS = 480                    # C3r's read parts (BKS 120, GOAT 215, cap1 121, n12 12, the panel 12)


# --- P2: the note set ---------------------------------------------------------------------------------------------------

def nominal_midi(string, fret):
    return OPEN_STRINGS[string] + fret


def note_path(string, fret, pickup=PICKUP, root=EGFX):
    return pathlib.Path(root) / pickup / f"{string}-{fret}.wav"


def detune_cents(audio, rate, midi):
    """How far a single note sits from equal temperament, in cents (`research/build_riffs.detune_cents`, unchanged)."""
    import sys

    sys.path.insert(0, str(REPO / "research"))
    import build_riffs as BR

    return float(BR.detune_cents(audio, rate, midi))


PITCH_RIVALS = (-12, -2, -1, 1, 2, 12)  # semitone offsets the nominal note must beat on harmonic energy


def pitch_rival(x, rate, midi):
    """(Pure.) The nominal note against its rivals: the energy of harmonics 1-4 (+-30 cents) 0.3-2.3 s in, for the
    nominal pitch and each PITCH_RIVALS offset. -> the winning offset (0 when the nominal note wins)."""
    import numpy as np

    piece = x[int(0.3 * rate):int(0.3 * rate) + 2 * rate]
    spec = np.abs(np.fft.rfft(piece * np.hanning(len(piece)), 1 << 20)) ** 2
    freqs = np.fft.rfftfreq(1 << 20, 1 / rate)

    def energy(m):
        f0 = 440 * 2 ** ((m - 69) / 12)
        return sum(spec[(freqs > h * f0 * 2 ** (-30 / 1200)) & (freqs < h * f0 * 2 ** (30 / 1200))].sum()
                   for h in range(1, 5))

    scores = {d: energy(midi + d) for d in (0,) + PITCH_RIVALS}
    return max(scores, key=lambda d: (scores[d], d == 0))


def attack_index(x, rate, frac=ATTACK_FRAC):
    """(Pure.) The first sample past `frac` of the first second's peak; None if the first second is silent."""
    import numpy as np

    head = np.abs(x[:rate])
    peak = head.max() if len(head) else 0.0
    if peak <= 0:
        return None
    return int(np.argmax(head > frac * peak))


def hum_db(x, rate, attack):
    """(Pure.) The mains series (50 or 60 Hz, whichever is louder; harmonics 1-4, +-2 Hz) in the last second, in dB
    under the note's attack level (the 50 ms RMS from the attack)."""
    import numpy as np

    tail = x[-rate:]
    spec = np.abs(np.fft.rfft(tail * np.hanning(len(tail)))) ** 2
    freqs = np.fft.rfftfreq(len(tail), 1 / rate)
    best = 0.0
    for mains in (50.0, 60.0):
        e = sum(spec[(freqs > k * mains - 2) & (freqs < k * mains + 2)].sum() for k in range(1, 5))
        best = max(best, e)
    tail_p = best / (np.sum(np.hanning(len(tail)) ** 2) * len(tail) / 2 + 1e-20)
    a = x[attack:attack + int(0.05 * rate)]
    att = float(np.mean(a ** 2)) + 1e-20
    return 10 * math.log10(tail_p / att + 1e-20)


def check_note(x, rate, string, fret, rules=NOTE_RULES):
    """(Pure but for the tuning helper.) One note's checks. -> {cents, clipped, attack_s, hum_db, peak, ok, why}."""
    import numpy as np

    why = []
    if rate != rules["rate"]:
        why.append(f"rate {rate}")
    if abs(len(x) / rate - rules["seconds"]) > 0.01:
        why.append(f"length {len(x) / rate:.2f} s")
    clipped = int(np.sum(np.abs(x) >= 0.999))
    if clipped > rules["max_clipped"]:
        why.append(f"{clipped} clipped samples")
    a = attack_index(x, rate)
    if a is None or a / rate > rules["attack_by_s"]:
        why.append("no attack in the first second")
        a = a or 0
    cents = detune_cents(x, rate, nominal_midi(string, fret))
    if abs(cents) > rules["max_abs_cents"]:
        why.append(f"{cents:+.0f} cents from its nominal pitch")
    rival = pitch_rival(x, rate, nominal_midi(string, fret))
    if rival:
        why.append(f"sounds {rival:+d} semitones from its nominal note")
    h = hum_db(x, rate, a)
    if h > rules["max_hum_db"]:
        why.append(f"hum {h:.1f} dB")
    return {"cents": round(cents, 2), "rival": rival, "clipped": clipped, "attack_s": round(a / rate, 5), "hum_db": round(h, 2),
            "peak": round(float(np.abs(x).max()), 5), "ok": not why, "why": why}


NOTE_SOURCE = {"dataset": "EGFxSet, the Clean set", "record": "Zenodo 7044411 (doi 10.5281/zenodo.7044411)",
               "licence": "CC BY 4.0", "trust": "trusted: raw single-note DI recordings of one Stratocaster, five pickup "
               "positions, never amped; no ladder unit, capture or session uses it (assert_clear on every hash); "
               "the riff library's chords built from it were checked by ear on 2026-10-17"}


def cmd_notes(_args):
    """P2. All 690 clean notes (5 pickups x 6 strings x 23 frets): sha256, pitch against the nominal note, clipping,
    attack position and hum, under NOTE_RULES; every hash checked clear of the exclusion list; source, licence and
    trust recorded. -> note-rebuild/notes.json."""
    require(PHASE_P)
    refuse_existing(OUT / "notes.json")
    excl = load_exclusion()
    import soundfile as sf                          # after the refusals

    rows, gaps = {}, []
    for pu in PICKUPS:
        for s in OPEN_STRINGS:
            for f in FRETS:
                p = note_path(s, f, pu)
                key = f"{pu}/{s}-{f}"
                if not p.exists():
                    rows[key] = {"ok": False, "why": ["missing"]}
                    gaps.append(key)
                    continue
                x, rate = sf.read(str(p), dtype="float64", always_2d=True)
                r = check_note(x.mean(1), rate, s, f)
                r["sha256"] = file_sha(p)
                rows[key] = r
                if not r["ok"]:
                    gaps.append(key)
    assert_clear([{"sha256": r["sha256"]} for r in rows.values() if "sha256" in r], excl)
    used = [k for k in rows if k.startswith(PICKUP + "/")]
    why = {}
    for k in gaps:
        for w in rows[k]["why"]:
            kind = w.split(" ", 1)[1] if w[:1] in "+-0123456789" else w.split(" ")[0]
            why[kind] = why.get(kind, 0) + 1
    body = {"source": NOTE_SOURCE, "rules": NOTE_RULES, "pickup": PICKUP, "notes": rows, "failed": gaps,
            "failed_by_reason": why, "exclusion_sha256": content_sha(excl),
            "failed_in_pickup": [k for k in gaps if k.startswith(PICKUP + "/")], "count": len(rows),
            "pickup_count": len(used)}
    doc = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P}", "made": time.strftime("%Y-%m-%d %H:%M:%S"),
           "body": body, "body_sha256": content_sha(body)}
    h = write_once(OUT / "notes.json", doc)
    print(f"NOTES DONE: {len(rows)} notes, {len(gaps)} failed ({len(body['failed_in_pickup'])} at {PICKUP}); "
          f"doc sha256 {h}")


def load_notes_doc():
    return load_doc("notes.json")


# --- P3: the true notes --------------------------------------------------------------------------------------------------

def dadagp_notes(text):
    """(Pure.) The sounding notes of a DadaGP token file, in playing order: [{string, fret, beat, arts, tie}], repeats
    unrolled ('measure:repeat_open' ... 'measure:repeat_close:N' plays N times), tied notes kept with tie=True (they
    do not re-sound). `beat` counts beats (each 'wait' closes one); `downtune` is returned beside."""
    toks = text.split()
    down = 0
    for t in toks[:5]:
        if t.startswith("downtune:"):
            down = int(t.split(":")[1])
    # unroll repeats at token level, measure by measure
    out_toks, i, open_at = [], 0, None
    while i < len(toks):
        t = toks[i]
        if t == "measure:repeat_open":
            open_at = len(out_toks)
        elif t.startswith("measure:repeat_close"):
            n = int(t.split(":")[2]) if t.count(":") >= 2 else 2
            body = out_toks[open_at if open_at is not None else 0:]
            for _ in range(n - 1):
                out_toks.extend(body)
            open_at = None
        else:
            out_toks.append(t)
        i += 1
    notes, beat, beat_fx, tick = [], 0, set(), 0
    for t in out_toks:
        p = t.split(":")
        if len(p) >= 4 and p[1] == "note":
            notes.append({"string": int(p[2][1:]), "fret": int(p[3][1:]), "beat": beat, "tick": tick, "arts": set(),
                          "tie": False})
            notes[-1]["arts"] |= beat_fx
        elif p[0] == "nfx" and notes and notes[-1]["beat"] == beat:
            if p[1] == "tie":
                notes[-1]["tie"] = True
            else:
                notes[-1]["arts"].add(p[1])
        elif p[0] == "bfx" and len(p) > 1 and p[1] == "tremolo_bar":
            beat_fx = {"tremolo_bar"}
            for n in notes:
                if n["beat"] == beat:
                    n["arts"].add("tremolo_bar")
        elif p[0] == "wait":
            beat += 1
            tick += int(p[1])
            beat_fx = set()
    for n in notes:
        n["arts"] = sorted(n["arts"])
    return notes, down


def tab_pitch(note, offset):
    return OPEN_STRINGS[note["string"]] + note["fret"] + offset


def match_tab(tab, midi, offset):
    """(Pure.) Each MIDI note's tab note, by aligning the two pitch sequences (sorted by onset or beat, then pitch;
    `difflib.SequenceMatcher`, autojunk off; MIDI notes within CHORD_S are one chord): a MIDI note gets the tab note it pairs with, else None. Tied tab notes do
    not sound and are left out. -> [index into tab or None] per MIDI note."""
    import difflib

    tab_i = [k for k, n in enumerate(tab) if not n["tie"]]
    tab_i.sort(key=lambda k: (tab[k]["beat"], tab_pitch(tab[k], offset)))
    a = [tab_pitch(tab[k], offset) for k in tab_i]
    order = sorted(range(len(midi)), key=lambda k: midi[k][0])
    group, g, first = {}, -1, None
    for k in order:                                    # the fine alignment spreads a chord's notes a little
        if first is None or midi[k][0] - first >= CHORD_S:
            g, first = g + 1, midi[k][0]
        group[k] = g
    mid_i = sorted(range(len(midi)), key=lambda k: (group[k], midi[k][2]))
    b = [midi[k][2] for k in mid_i]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    out = [None] * len(midi)
    for blk in sm.get_matching_blocks():
        for d in range(blk.size):
            out[mid_i[blk.b + d]] = tab_i[blk.a + d]
    return out


def best_offset(tab, midi, down):
    """(Pure.) The semitone offset between the tab's strings and the MIDI's pitches that pairs the most notes, from
    the DadaGP downtune (-12 is standard tuning in GOAT's files), +-3 about it and an octave either way (some items'
    fine-aligned MIDI sits an octave from the tab; the MIDI's pitch is kept, `source_for` moves the fret). ->
    (offset, matched)."""
    base = down + 12
    best = None
    for off in [o + octave for octave in (0, 12, -12) for o in range(base - 3, base + 4)]:
        m = sum(x is not None for x in match_tab(tab, midi, off))
        if best is None or m > best[1] or (m == best[1] and abs(off - base) < abs(best[0] - base)):
            best = (off, m)
    return best


READER_WINDOW = 16                      # the MIDI reader's cross-check: linear fits over 16 matched notes, hop 8
READER_MAX_RESID_S = 0.005              # an item passes with a median residual within 5 ms ...
READER_MIN_SHARE = 0.9                  # ... and at least 90% of the MIDI's notes matched to the tab
READER_MIN_ITEMS = 0.5                  # the reader passes when at least half the items checked pass


def _fit_resid(xs, ys):
    """(Pure.) Median absolute residual of a least-squares line through (xs, ys)."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    r = sorted(abs(y - (my + b * (x - mx))) for x, y in zip(xs, ys))
    return r[n // 2] if n % 2 else (r[n // 2 - 1] + r[n // 2]) / 2


def reader_check(tab, unaligned, offset):
    """(Pure.) The MIDI reader's cross-check, needing no download: GOAT's unaligned MIDI is exported from the same tab,
    so the reader's onsets must follow the tab's own ticks (parsed from the DadaGP text, independently of the MIDI
    bytes). Notes paired as `match_tab` pairs them; over each run of READER_WINDOW pairs in tab order, a straight line
    from ticks to seconds; the item's residual is the median of the runs' median residuals (tempo changes and repeats
    break only the runs that span them). -> {share, resid_s, ok}."""
    idx = match_tab(tab, unaligned, offset)
    pairs = sorted((tab[k]["tick"], unaligned[i][0]) for i, k in enumerate(idx) if k is not None)
    share = len(pairs) / len(unaligned) if unaligned else 0.0
    res = []
    for a in range(0, max(0, len(pairs) - READER_WINDOW + 1), READER_WINDOW // 2):
        w = pairs[a:a + READER_WINDOW]
        r = _fit_resid([x for x, _ in w], [y for _, y in w])
        if r is not None:
            res.append(r)
    if not res:
        return {"share": round(share, 4), "resid_s": None, "ok": None}
    res.sort()
    med = res[len(res) // 2]
    return {"share": round(share, 4), "resid_s": med, "ok": share >= READER_MIN_SHARE and med <= READER_MAX_RESID_S}


def placed(pitch, taken, notes_ok=None):
    """(Pure.) The fallback placing rule for a note with no tab match: the lowest fret on a free string that plays it
    (fret 0-22), skipping failed notes. -> (string, fret) or None."""
    best = None
    for s, o in OPEN_STRINGS.items():
        f = pitch - o
        if s in taken or f not in FRETS:
            continue
        if notes_ok is not None and not notes_ok(s, f):
            continue
        if best is None or f < best[1]:
            best = (s, f)
    return best


def true_notes_for(item, z, meta):
    """One GOAT item's true notes: the fine-aligned MIDI (timing, pitch) with each note's string, fret and
    articulations from the DadaGP tab. -> {notes: [{on, off, pitch, string, fret, arts, from}], ...} or {out: why}."""
    import sys

    sys.path.insert(0, str(REPO / "research"))
    import build_riffs as BR

    m = meta[item]
    fine = f"GOAT/data/{item}/{item}_fine_aligned.mid"
    txt = f"GOAT/data/{item}/{item}.txt"
    names = set(z.namelist())
    if fine not in names:
        return {"out": "no fine-aligned MIDI"}
    midi = BR.midi_notes(z.read(fine))
    rec = {"alignment_f": float(m["alignment_f_measure_fine"]) if m["alignment_f_measure_fine"] else None,
           "tuning": m["tuning_class"], "guitar": m["guitar_brand"], "player": m["player"],
           "midi_notes": len(midi), "midi_sha256": bytes_sha(z.read(fine))}
    tab, down = ([], 0)
    if txt in names:
        tab, down = dadagp_notes(z.read(txt).decode())
        rec["tab_sha256"] = bytes_sha(z.read(txt))
    rec["tab_notes"], rec["downtune"] = len(tab), down
    offset, matched = best_offset(tab, midi, down) if tab else (0, 0)
    rec["offset"], rec["matched"] = offset, matched
    una = f"GOAT/data/{item}/{item}.mid"
    if tab and una in names:
        rec["reader_check"] = reader_check(tab, BR.midi_notes(z.read(una)), offset)
    idx = match_tab(tab, midi, offset) if tab else [None] * len(midi)
    notes = []
    for (on, off, pitch), k in zip(midi, idx):
        if k is not None:
            t = tab[k]
            notes.append({"on": on, "off": off, "pitch": pitch, "string": t["string"], "fret": t["fret"],
                          "arts": t["arts"], "from": "tab"})
        else:
            notes.append({"on": on, "off": off, "pitch": pitch, "string": None, "fret": None, "arts": [],
                          "from": "none"})
    rec["notes"] = notes
    return rec


def articulated_share(notes):
    """(Pure.) The share of notes carrying an articulation (ARTICULATIONS or a tremolo-bar beat), of those matched to
    the tab; None with none matched."""
    tabbed = [n for n in notes if n["from"] == "tab"]
    if not tabbed:
        return None
    return sum(bool(set(n["arts"]) & (set(ARTICULATIONS) | {"tremolo_bar"})) for n in tabbed) / len(tabbed)


def window_notes(notes, start, length):
    """(Pure.) Notes sounding in [start, start + length) of the item, re-timed to the window ([on - start, off -
    start]); a note begun before the window is kept only if it is still sounding."""
    out = []
    for n in notes:
        if n["off"] <= start or n["on"] >= start + length:
            continue
        out.append({**n, "on": n["on"] - start, "off": n["off"] - start})
    return out


def cmd_true_notes(_args):
    """P3. Every GOAT item's true notes (fine-aligned MIDI with the tab's strings and frets), and per GOAT and cap1
    read unit: the notes in its DI section's window, the share matched to the tab, the alignment F, tuning, brand and
    articulated share; the MIDI reader's cross-check against the tab (`reader_check`) on every item with both. The
    per-item note files are written to a temporary folder and moved into place only when every item is built, then
    the record. -> note-rebuild/true-notes.json (+ true-notes/<item>.json)."""
    require(PHASE_P)
    final, tmp = OUT / "true-notes", OUT / "true-notes.partial"
    for p in (OUT / "true-notes.json", final, tmp):
        refuse_existing(p)
    import csv                                      # after the refusals
    import io
    import zipfile

    from learn import full_controls_c3r as C
    from learn import pretrain_set as PS

    units = [r for r in C.read_units() if r["set"] in ("goat", "cap1")]
    sec_len = PS.SEC_S + PS.TRIM_S
    per_item, per_unit = {}, {}
    with zipfile.ZipFile(GOAT_ZIP) as z:
        meta = {r["item"]: r for r in csv.DictReader(io.StringIO(z.read("GOAT/metadata.csv").decode()))}
        items = sorted(meta, key=lambda s: int(s.split("_")[1]))
        for it in items:
            rec = true_notes_for(it, z, meta)
            if "notes" in rec:
                write_once(tmp / f"{it}.json", rec)
                rec = {k: v for k, v in rec.items() if k != "notes"} | {"notes_sha256": content_sha(rec["notes"]),
                                                                        "_notes": rec["notes"]}
            per_item[it] = rec
    goat_units = json.loads((PF / "goat/units.json").read_text())
    window_of = {it: v["start_s"] for it, v in goat_units["items"].items() if v.get("start_s") is not None}
    for r in units:
        p = r["prt"]
        it = p["item"] if r["set"] == "goat" else p["di_item"]
        key = f"{r['unit']}|{r['amp']}"
        rec = per_item.get(it, {"out": "not a GOAT item"})
        if "_notes" not in rec:
            per_unit[key] = {"set": r["set"], "item": it, "carries": False, "why": rec.get("out", "no notes")}
            continue
        start = window_of.get(it)
        if start is None:
            per_unit[key] = {"set": r["set"], "item": it, "carries": False, "why": "no window"}
            continue
        w = window_notes(rec["_notes"], start - PS.TRIM_S, sec_len)
        tabbed = sum(n["from"] == "tab" for n in w)
        per_unit[key] = {"set": r["set"], "item": it, "fold": r["fold"], "cls": p["cls"], "window_s": start,
                         "notes": len(w), "tabbed": tabbed, "tab_share": round(tabbed / len(w), 4) if w else None,
                         "alignment_f": rec["alignment_f"], "tuning": rec["tuning"], "guitar": rec["guitar"],
                         "player": rec["player"], "articulated": articulated_share(w),
                         "below_range": sum(n["pitch"] < MIDI_RANGE[0] for n in w),
                         "carries": len(w) >= CARRY_MIN_NOTES}
        if not per_unit[key]["carries"]:
            per_unit[key]["why"] = f"fewer than {CARRY_MIN_NOTES} notes in the window"
    for rec in per_item.values():
        rec.pop("_notes", None)
    goat_carry = sum(v["carries"] for v in per_unit.values() if v["set"] == "goat")
    checks = [v["reader_check"] for v in per_item.values() if v.get("reader_check", {}).get("ok") is not None]
    reader = {"items_checked": len(checks), "items_passing": sum(c["ok"] for c in checks),
              "rule": {"window": READER_WINDOW, "max_resid_s": READER_MAX_RESID_S, "min_share": READER_MIN_SHARE,
                       "min_items": READER_MIN_ITEMS}}
    reader["ok"] = bool(checks) and reader["items_passing"] >= READER_MIN_ITEMS * len(checks)
    body = {"items": per_item, "units": per_unit, "carry_rule": {"min_notes": CARRY_MIN_NOTES,
                                                                 "tab_share_split": CARRY_TAB_SHARE},
            "goat_units_carrying": goat_carry, "reader": reader, "units_read": len(units),
            "cap1_units_carrying": sum(v["carries"] for v in per_unit.values() if v["set"] == "cap1")}
    body["p3_ok"] = p3_ok(body)
    tmp.rename(final)
    doc = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P}", "made": time.strftime("%Y-%m-%d %H:%M:%S"),
           "body": body, "body_sha256": content_sha(body)}
    h = write_once(OUT / "true-notes.json", doc)
    print(f"TRUE-NOTES DONE: {sum('notes_sha256' in v for v in per_item.values())} of {len(per_item)} items with "
          f"notes; GOAT units carrying {goat_carry} of {sum(v['set'] == 'goat' for v in per_unit.values())}; "
          f"cap1 {body['cap1_units_carrying']}; reader {reader['items_passing']} of {reader['items_checked']} items "
          f"(ok {reader['ok']}); p3_ok {body['p3_ok']}; doc sha256 {h}")


EXPECTED_NOTE_UNITS = 336               # C3r's GOAT (215) and cap1 (121) read parts


def p3_ok(body):
    """(Pure.) P3 passes its own checks: every GOAT and cap1 read part recorded, every item with fine-aligned MIDI
    built with notes, the MIDI reader's cross-check passing, and some GOAT part carrying."""
    built = all("notes_sha256" in v for v in body["items"].values() if v.get("out") != "no fine-aligned MIDI")
    return (body["units_read"] == EXPECTED_NOTE_UNITS and len(body["units"]) == EXPECTED_NOTE_UNITS and built
            and body["reader"]["ok"] and body["goat_units_carrying"] > 0)


CARRY_MIN_NOTES = 8                     # a unit carries stage 1 with fine-aligned MIDI and at least 8 notes in its window
CARRY_TAB_SHARE = 0.8                   # stage 1 reads beside: units with at least 80% of notes matched to the tab


# --- P4: the re-synthesis ------------------------------------------------------------------------------------------------

def denoise_above(x, rate=SR):
    """The declared hiss removal: noisereduce (non-stationary, prop 0.9, time constant 2 s) on the content above
    DENOISE_ABOVE_HZ only, the rest untouched (the riff library's lesson)."""
    import noisereduce
    import scipy.signal as ss

    low = ss.sosfiltfilt(ss.butter(4, DENOISE_ABOVE_HZ, "lp", fs=rate, output="sos"), x)
    return low + noisereduce.reduce_noise(y=x - low, sr=rate, stationary=False, prop_decrease=0.9, time_constant_s=2.0)


def prepare_sample(x, rate, cents_off):
    """One EGFxSet note made ready (the riff library's lessons, `build_riffs.prepared_note`, with the retune applied
    later): denoised above 3 kHz (noisereduce, non-stationary), trimmed to start PRE_ATTACK_S before its attack with a
    2 ms fade in, set to a common level by its first 0.3 s from the attack. -> (audio, own cents from equal
    temperament)."""
    import numpy as np

    y = denoise_above(x, rate)
    a = attack_index(y, rate) or 0
    y = y[max(0, a - int(PRE_ATTACK_S * rate)):].copy()
    fade = int(NOTE_FADE_IN_S * rate)
    y[:fade] *= np.linspace(0.0, 1.0, fade)
    head = y[:int(0.3 * rate)]
    return y / (np.sqrt(np.mean(head ** 2)) + 1e-12), cents_off


def shifted(y, cents):
    """(Pure.) `y` resampled so its pitch moves by `cents` (shorter when up)."""
    import scipy.signal as ss

    if abs(cents) < 1e-6:
        return y.copy()
    return ss.resample(y, max(1, round(len(y) * 2 ** (-cents / 1200))))


class Bank:
    """The prepared note set at one pickup: lazily loads, prepares and caches each (string, fret), and each shift.
    From disk it needs P2's record: every note's hash is checked clear of the exclusion list when the bank opens, and
    each file's hash is checked against the record when it loads. Only a test's `loader` may stand in for the files
    (then with no record)."""

    def __init__(self, notes_doc=None, pickup=PICKUP, root=EGFX, loader=None, excl=None):
        if notes_doc is None and loader is None:
            raise SystemExit("a bank on disk needs P2's notes.json")
        if notes_doc is not None:
            if notes_doc.get("source", {}).get("licence") != "CC BY 4.0":
                raise SystemExit("notes.json records no CC BY 4.0 source")
            assert_clear([{"sha256": r["sha256"]} for k, r in notes_doc["notes"].items()
                          if k.startswith(pickup + "/") and "sha256" in r], excl)
        self.pickup, self.root = pickup, root
        self.doc = notes_doc
        self.loader = loader
        self._prep, self._shift, self._early = {}, {}, {}

    def ok(self, s, f):
        if self.doc is None:
            return f in FRETS and s in OPEN_STRINGS
        r = self.doc["notes"].get(f"{self.pickup}/{s}-{f}")
        return bool(r and r["ok"])

    def own_cents(self, s, f):
        """The sample's own pitch against equal temperament where it is played: its first EARLY_S from the attack
        (`global_tuning_cents`). P2's figure (0.3-2.3 s in) reads about 4.5 cents flatter, the pick attack's glide
        (measured on 10 notes at stage 1's declaration), and most notes in a part sound only their first few hundred
        ms; P2's cents still gate wrong notes."""
        if (s, f) not in self._early:
            y = self.prepared(s, f)
            self._early[(s, f)] = global_tuning_cents(y[:int(EARLY_S * SR)])
        return self._early[(s, f)]

    def prepared(self, s, f):
        if (s, f) not in self._prep:
            if self.loader is not None:
                x, rate = self.loader(s, f)
            else:
                import io

                import soundfile as sf

                raw = note_path(s, f, self.pickup, self.root).read_bytes()
                want = self.doc["notes"][f"{self.pickup}/{s}-{f}"].get("sha256")
                if bytes_sha(raw) != want:
                    raise SystemExit(f"{self.pickup}/{s}-{f}: the file's hash does not match notes.json")
                x, rate = sf.read(io.BytesIO(raw), dtype="float64", always_2d=True)
                x = x.mean(1)
            self._prep[(s, f)] = prepare_sample(x, rate, 0.0)[0]
        return self._prep[(s, f)]

    def note(self, s, f, cents):
        key = (s, f, round(cents, 1))
        if key not in self._shift:
            self._shift[key] = shifted(self.prepared(s, f), key[2])
        return self._shift[key]


def source_for(n, tuning_cents, bank):
    """(Pure but for `bank.ok`.) The sample a note plays and its shift: the tab's string and fret when known, else the
    placing rule; the shift in cents takes the sample from its own measured pitch to the note's pitch plus the
    reference's global tuning. -> (string, fret, cents) or None (unplayable)."""
    p = n["pitch"]
    if n.get("string") and n.get("fret") is not None:
        s, f = n["string"], n["fret"]
        semis = p - nominal_midi(s, f)
        if abs(semis) > MAX_SHIFT_SEMITONES or f not in FRETS or not bank.ok(s, f):
            f2 = p - OPEN_STRINGS[s]
            if f2 in FRETS and bank.ok(s, f2):
                s, f = s, f2
            else:
                sp = placed(p, n.get("_taken", set()) - {n["string"]}, bank.ok)
                if sp is None:
                    return None
                s, f = sp
    else:
        sp = placed(p, n.get("_taken", set()), bank.ok)
        if sp is None:
            return None
        s, f = sp
    semis = p - nominal_midi(s, f)
    if abs(semis) > MAX_SHIFT_SEMITONES:
        return None
    return s, f, 100.0 * semis + tuning_cents - bank.own_cents(s, f)


def onset_groups(notes, gap=CHORD_S):
    """(Pure.) Indices of notes grouped by onset: a note within `gap` of its group's first onset joins it."""
    order = sorted(range(len(notes)), key=lambda k: notes[k]["on"])
    groups = []
    for k in order:
        if groups and notes[k]["on"] - notes[groups[-1][0]]["on"] < gap:
            groups[-1].append(k)
        else:
            groups.append([k])
    return groups


def note_gain_db(n):
    """(Pure.) A note's fixed articulation gain."""
    arts = set(n.get("arts") or ())
    g = 0.0
    if "dead" in arts:
        g += DEAD_DB
    if "ghost_note" in arts:
        g += GHOST_DB
    if arts & {"hammer", "slide"}:
        g += LEGATO_DB
    return g


def note_length_s(n, next_same_string):
    """(Pure.) How long a note sounds: to its note-off, cut at its string's next pluck, a dead note DEAD_S and a
    palm-muted one at most PALM_S."""
    end = n["off"]
    if next_same_string is not None:
        end = min(end, next_same_string)
    arts = set(n.get("arts") or ())
    if "dead" in arts:
        end = min(end, n["on"] + DEAD_S)
    if "palm_mute" in arts:
        end = min(end, n["on"] + PALM_S)
    return max(0.0, end - n["on"])


def synthesise(notes, length, bank, tuning_cents=0.0, group_gain_db=None, rate=SR):
    """The dry guitar for a note list on a window of `length` samples: each note's sample placed with its attack at
    its onset, held to `note_length_s` with END_FADE_S (or REPLUCK_FADE_S when its string is plucked again, or
    TAIL_FADE_S when it outlasts its sample), its articulation gain, and a group of k notes struck together at
    1/sqrt(k) so every onset group is equally loud (`nr-plain`); `group_gain_db` (one per onset group) adds the
    `nr-level` or `nr-oracle` gain. Deterministic. -> (audio, report)."""
    import numpy as np

    out = np.zeros(length)
    groups = onset_groups(notes)
    gain_of = {}
    for gi, g in enumerate(groups):
        extra = 0.0 if group_gain_db is None else group_gain_db[gi]
        for k in g:
            gain_of[k] = 10 ** ((note_gain_db(notes[k]) + extra) / 20) / math.sqrt(len(g))
    # strings: tab strings, or the placing rule inside each group
    src = {}
    for g in groups:
        taken = {notes[k]["string"] for k in g if notes[k].get("string")}
        for k in g:
            n = dict(notes[k])
            n["_taken"] = taken
            r = source_for(n, tuning_cents, bank)
            if r is not None:
                src[k] = r
                taken.add(r[0])
    by_string = {}
    for k in sorted(src, key=lambda k: notes[k]["on"]):
        by_string.setdefault(src[k][0], []).append(k)
    nxt = {}
    for ks in by_string.values():
        for a, b in zip(ks, ks[1:]):
            nxt[a] = notes[b]["on"]
    skipped = []
    for k, n in enumerate(notes):
        if k not in src:
            skipped.append(k)
            continue
        s, f, cents = src[k]
        y = bank.note(s, f, cents)
        start = int(round((n["on"] - PRE_ATTACK_S) * rate))       # the sample's attack lands on the onset
        dur = int(round((note_length_s(n, nxt.get(k)) + PRE_ATTACK_S) * rate))
        if dur <= 0:
            skipped.append(k)
            continue
        held_past = dur > len(y)
        dur = min(dur, len(y))
        seg = y[:dur].copy()
        if held_past:
            fade = min(dur, int(TAIL_FADE_S * rate))
        elif k in nxt and nxt[k] <= n["off"]:
            fade = min(dur, int(REPLUCK_FADE_S * rate))
        else:
            fade = min(dur, int(END_FADE_S * rate))
        seg[dur - fade:] *= np.linspace(1.0, 0.0, fade)
        if start < 0:
            seg, start = seg[-start:], 0
        end = min(length, start + len(seg))
        if end > start:
            out[start:end] += gain_of[k] * seg[:end - start]
    edge = min(length // 2, int(EDGE_FADE_S * rate))       # notes cut by the window's edges: no step at either end
    if edge:
        out[:edge] *= np.linspace(0.0, 1.0, edge)
        out[length - edge:] *= np.linspace(1.0, 0.0, edge)
    return out, {"notes": len(notes), "played": len(notes) - len(skipped), "skipped": len(skipped),
                 "groups": len(groups), "from_tab": sum(1 for k in src if notes[k].get("string") and k not in skipped)}


def span_rms(x, a, b):
    import numpy as np

    seg = x[max(0, a):max(0, b)]
    return float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0


def group_spans(notes, groups, length, rate=SR):
    """(Pure.) Each onset group's level span: LEVEL_SPAN_S from its first onset, cut at the next group's."""
    starts = [int(round(notes[g[0]]["on"] * rate)) for g in groups]
    spans = []
    for gi, a in enumerate(starts):
        b = a + int(LEVEL_SPAN_S * rate)
        if gi + 1 < len(starts):
            b = min(b, starts[gi + 1])
        spans.append((max(0, a), min(length, max(b, a + 1))))
    return spans


MIN_SPAN_S = 0.010                      # a group whose level span inside the window is shorter (it began before the
                                        # window) keeps 0 dB and stays out of the median


def _span_gains(db, ok, clamp):
    """(Pure.) Gains about the median of the usable spans' dB, held within +-clamp; 0 dB where not usable."""
    import numpy as np

    use = [d for d, k in zip(db, ok) if k]
    if not use:
        return [0.0] * len(db)
    med = float(np.median(use))
    return [float(np.clip(d - med, -clamp, clamp)) if k else 0.0 for d, k in zip(db, ok)]


def level_gains(notes, reference, rate=SR, clamp=LEVEL_CLAMP_DB):
    """(Pure.) `nr-level`: each onset group's gain from the reference's RMS over its span, in dB about the median of
    all usable spans, held within +-clamp (a group begun before the window: 0 dB)."""
    groups = onset_groups(notes)
    spans = group_spans(notes, groups, len(reference), rate)
    ok = [notes[g[0]]["on"] >= 0 and b - a >= MIN_SPAN_S * rate for g, (a, b) in zip(groups, spans)]
    db = [20 * math.log10(span_rms(reference, a, b) + 1e-12) for a, b in spans]
    return _span_gains(db, ok, clamp)


def oracle_gains(notes, plain, di, rate=SR, clamp=ORACLE_CLAMP_DB):
    """(Pure.) `nr-oracle`: each onset group's gain so the plain re-synthesis' RMS over its span equals the true DI's
    there, about the median ratio (the overall level is set afterwards), held within +-clamp. Diagnostic only."""
    groups = onset_groups(notes)
    spans = group_spans(notes, groups, min(len(di), len(plain)), rate)
    ok = [notes[g[0]]["on"] >= 0 and b - a >= MIN_SPAN_S * rate for g, (a, b) in zip(groups, spans)]
    r = [20 * math.log10((span_rms(di, a, b) + 1e-12) / (span_rms(plain, a, b) + 1e-12)) for a, b in spans]
    return _span_gains(r, ok, clamp)


def rise_curve(x, rate=SR):
    """(Pure.) The DI's onset function: the rise in dB of high-passed (REFINE_HP_HZ) energy in 2 ms frames at a 1 ms
    hop, frame against the one before. -> (rise_db per hop, hop)."""
    import numpy as np
    import scipy.signal as ss

    hop = REFINE_FRAME // 2
    h = ss.sosfilt(ss.butter(2, REFINE_HP_HZ, "hp", fs=rate, output="sos"), x)
    n = max(0, (len(h) - REFINE_FRAME) // hop + 1)
    if n == 0:
        return np.zeros(0), hop
    idx = np.arange(REFINE_FRAME)[None, :] + hop * np.arange(n)[:, None]
    e = 10 * np.log10(np.mean(h[idx] ** 2, axis=1) + 1e-12)
    return np.concatenate([[0.0], np.diff(e)]), hop


COARSE_S = 0.150                        # the onset step's first stage: one offset per window, from rises within +-150 ms


def coarse_offset(notes, di, rate=SR, window=COARSE_S):
    """(Pure.) The window's constant offset between the notes and the true DI (stage 1's oracle onset step, first
    stage): for each onset group the steepest rise of the DI within +-window of its onset (kept when at least
    REFINE_MIN_RISE_DB), and the median of those shifts. GOAT's fine-aligned MIDI runs about 30 ms late against the DI's
    attacks on most items (measured at P8's build), beyond what the +-50 ms snap alone can bring back. -> seconds (0.0
    with no rise)."""
    import numpy as np

    rise, hop = rise_curve(di, rate)
    shifts = []
    for g in onset_groups(notes):
        t = notes[g[0]]["on"]
        lo = max(0, int((t - window) * rate) // hop)
        hi = min(len(rise), int((t + window) * rate) // hop + 1)
        if hi <= lo:
            continue
        j = lo + int(np.argmax(rise[lo:hi]))
        if rise[j] >= REFINE_MIN_RISE_DB:
            shifts.append((j * hop + REFINE_FRAME / 2) / rate - t)
    return float(np.median(shifts)) if shifts else 0.0


def shifted_notes(notes, offset):
    """(Pure.) Every note moved by `offset` seconds."""
    return [{**n, "on": n["on"] + offset, "off": n["off"] + offset} for n in notes]


def refine_onsets(notes, di, rate=SR):
    """The oracle onset step: each onset group's onset moved to the true DI's steepest rise within +-REFINE_S of it,
    when that rise is at least REFINE_MIN_RISE_DB; else kept. Every note in a group moves together; offsets move with
    their onsets. -> (notes, shifts in seconds per group)."""
    import numpy as np

    rise, hop = rise_curve(di, rate)
    out = [dict(n) for n in notes]
    shifts = []
    for g in onset_groups(notes):
        t = notes[g[0]]["on"]
        lo = max(0, int((t - REFINE_S) * rate) // hop)
        hi = min(len(rise), int((t + REFINE_S) * rate) // hop + 1)
        if hi <= lo:
            shifts.append(0.0)
            continue
        j = lo + int(np.argmax(rise[lo:hi]))
        if rise[j] < REFINE_MIN_RISE_DB:
            shifts.append(0.0)
            continue
        new = (j * hop + REFINE_FRAME / 2) / rate
        d = new - t
        shifts.append(d)
        for k in g:
            out[k]["on"] = notes[k]["on"] + d
            out[k]["off"] = max(out[k]["on"], notes[k]["off"] + d)
    return out, shifts


def global_tuning_cents(x, rate=SR, band=TUNING_BAND_HZ):
    """(Pure.) The reference's global tuning against A440 equal temperament, in cents (-50 to +50): the
    magnitude-weighted circular mean of spectral peaks' deviations in `band`, over 8,192-sample frames."""
    import numpy as np
    import scipy.signal as ss

    n = 8192
    if len(x) < n:
        return 0.0
    f, _, Z = ss.stft(x, fs=rate, nperseg=n, noverlap=n // 2, window="hann")
    mag = np.abs(Z)
    keep = (f >= band[0]) & (f <= band[1])
    f, mag = f[keep], mag[keep]
    acc = 0j
    for col in mag.T:
        if col.max() <= 0:
            continue
        pk, _ = ss.find_peaks(col, height=col.max() * 0.1)
        for p in pk:
            if 0 < p < len(col) - 1:                           # parabolic refinement
                a, b, c = col[p - 1], col[p], col[p + 1]
                d = 0.5 * (a - c) / (a - 2 * b + c + 1e-20)
                fp = f[p] + d * (f[1] - f[0])
            else:
                fp = f[p]
            if fp <= 0:
                continue
            dev = 1200 * math.log2(fp / 440.0)
            acc += col[p] * np.exp(2j * math.pi * dev / 100.0)
    if abs(acc) == 0:
        return 0.0
    return float(np.angle(acc) / (2 * math.pi) * 100.0)


def clean_notes(notes):
    """(Pure.) The note list's declared clean-up: MIDI 40 to 88 kept (counted out otherwise); one pitch struck twice
    within CHORD_S merged; at most six notes at once (the newest dropped)."""
    kept, out = [], {"out_of_range": 0, "merged": 0, "over_six": 0}
    for n in sorted(notes, key=lambda n: (n["on"], n["pitch"])):
        if not MIDI_RANGE[0] <= n["pitch"] <= MIDI_RANGE[1]:
            out["out_of_range"] += 1
            continue
        if any(m["pitch"] == n["pitch"] and abs(m["on"] - n["on"]) < CHORD_S for m in kept[-6:]):
            out["merged"] += 1
            continue
        if sum(m["on"] <= n["on"] < m["off"] for m in kept) >= 6:
            out["over_six"] += 1
            continue
        kept.append(n)
    return kept, out


def loudness(y, rate=SR):
    import pyloudnorm

    return pyloudnorm.Meter(rate).integrated_loudness(y)


def at_lufs(y, lufs, rate=SR, tol=0.01, passes=4):
    """`y` at `lufs` integrated loudness. The gating's absolute -70 LUFS gate makes one gain step inexact when parts of
    the signal sit near it, so the step repeats until within `tol` LU (at most `passes` times)."""
    for _ in range(passes):
        d = lufs - loudness(y, rate)
        if abs(d) <= tol:
            break
        y = y * 10 ** (d / 20)
    return y


def rebuild_dry(arm, notes, length, bank, reference, di=None, finish=None, rate=SR):
    """One stage-1 dry guitar. `notes`: the window's notes (true notes, already onset-refined by `refine_onsets` for
    every arm); `reference`: the window's reference audio (its global tuning; `nr-level`'s levels); `di`: the true DI
    **as the replay renders it** (`song_bank.measure` of its section: the average guitar's balance at -22.9 LUFS),
    `nr-oracle` only (its levels); `finish`: the replay's own chain for a dry guitar, bound by stage 1's declaration
    (the blurred row's: `song_bank.measure`, then the `avg` step with the part's `others`), or None (then the level
    alone). Every arm ends at ASSUMED_LUFS, so `nr-oracle` differs from `nr-plain` only by its per-group levels.
    -> (audio, report)."""
    if arm not in ARMS:
        raise ValueError(arm)
    if arm == "nr-oracle" and di is None:
        raise ValueError("nr-oracle needs the true DI as rendered")
    notes, cleaned = clean_notes(notes)
    tune = global_tuning_cents(reference, rate)
    padded = length + int(round(END_PAD_S * rate))   # the window's end is never faded: half B ends there
    plain, rep = synthesise(notes, padded, bank, tune, None, rate)
    if arm == "nr-plain":
        y = plain
    elif arm == "nr-level":
        y, _ = synthesise(notes, padded, bank, tune, level_gains(notes, reference, rate), rate)
    else:
        y, _ = synthesise(notes, padded, bank, tune, oracle_gains(notes, plain[:length], di, rate), rate)
    if arm != "nr-plain":
        y = denoise_above(y, rate)          # the level gain lifts each note's residual hiss: removed again after it
    if finish is not None:
        y = finish(y)
    y = at_lufs(y[:length], ASSUMED_LUFS, rate)
    return y, {**rep, **cleaned, "tuning_cents": round(tune, 2), "lufs": ASSUMED_LUFS}


# --- the redo's dry guitars, `tr-di` and `tr-plain` (plan section 12; every rule frozen here) ----------------------------
# Added for the redo. Nothing above this block changed: the stage-1 arms (`ARMS`, `synthesise`, `rebuild_dry` and every
# helper they call) are byte-for-byte as they were, and the functions below never call `synthesise` or `rebuild_dry`.

REDO_ARMS = ("tr-di", "tr-plain")       # tr-di decides (levels from the DI); tr-plain is the zero-render side figure
RING_VARIANTS = ("ring-on", "ring-soft")   # the transcriber's note-off: never cuts / starts a 150-ms release
RING_SOFT_S = 0.150
MUTE_FRAME_S = 0.020                    # a mute in the DI: its 20-ms level ...
MUTE_HOP_S = 0.005
MUTE_DROP_DB = 12.0                     # ... falls 12 dB or more ...
MUTE_WITHIN_S = 0.060                   # ... inside 60 ms, from a frame where the DI plays (within MUTE_FLOOR_DB of
MUTE_FLOOR_DB = 40.0                    # its loudest 20-ms frame, J0's playing floor)
MUTE_FADE_S = 0.030                     # every note sounding then ends with a 30-ms fade
TILT_ISOLATED_S = 0.600                 # the sustain tilt: onset groups with no other onset for 600 ms after them ...
TILT_EARLY = (0.000, 0.050)             # ... the level at 300-500 ms against 0-50 ms from the onset ...
TILT_LATE = (0.300, 0.500)              # ... DI less the plain rebuild; the median, as dB per second
TILT_MAX_DB_S = 12.0                    # within +-12 dB/s ...
TILT_MAX_GAIN_DB = 12.0                 # ... and at most +12 dB in all on any note
TILT_MIN_GROUPS = 3                     # under 3 isolated groups: no tilt (reported)
BEND_FRAME_S = 256 / 22050              # Basic Pitch's frames (11.6 ms); a bend step is a third of a semitone
BEND_STEPS_PER_SEMITONE = 3
BEND_MEDIAN = 3                         # 3-frame median
BEND_MIN_FRAMES = 5                     # applied where a bend of one step or more lasts five frames
BEND_MAX_SEMITONES = 3.0
BEND_CLEAR_SEMITONES = 2                # not while another note sounds within 2 semitones
VARIETY_S = 2.0                         # a pitch struck again within 2 s takes the next source
SNAP_S = 0.020                          # the redo's onset snap: +-20 ms (rise of REFINE_MIN_RISE_DB)


def snap_onsets(notes, di, window=SNAP_S, rate=SR):
    """`refine_onsets` with the snap window as a parameter (the redo's +-20 ms; `refine_onsets` itself, stage 1's
    +-50 ms, is unchanged). Each onset group moves to the DI's steepest rise within +-window when that rise is at least
    REFINE_MIN_RISE_DB, else stays; offsets move with their onsets. -> (notes, shifts per group)."""
    import numpy as np

    rise, hop = rise_curve(di, rate)
    out = [dict(n) for n in notes]
    shifts = []
    for g in onset_groups(notes):
        t = notes[g[0]]["on"]
        lo = max(0, int((t - window) * rate) // hop)
        hi = min(len(rise), int((t + window) * rate) // hop + 1)
        if hi <= lo:
            shifts.append(0.0)
            continue
        j = lo + int(np.argmax(rise[lo:hi]))
        if rise[j] < REFINE_MIN_RISE_DB:
            shifts.append(0.0)
            continue
        d = (j * hop + REFINE_FRAME / 2) / rate - t
        shifts.append(d)
        for k in g:
            out[k]["on"] = notes[k]["on"] + d
            out[k]["off"] = max(out[k]["on"], notes[k]["off"] + d)
    return out, shifts


def frame_levels_db(x, frame, hop):
    """(Pure.) RMS levels in dB of `frame`-sample frames at `hop`. -> numpy array (empty for a short signal)."""
    import numpy as np

    x = np.asarray(x, np.float64)
    k = max(0, (len(x) - frame) // hop + 1)
    if k == 0:
        return np.zeros(0)
    idx = np.arange(frame)[None, :] + hop * np.arange(k)[:, None]
    return 10 * np.log10(np.mean(x[idx] ** 2, axis=1) + 1e-20)


def mute_times(di, rate=SR):
    """(Pure.) The DI's mutes, in seconds: from a 20-ms frame where the DI plays (within MUTE_FLOOR_DB of its loudest),
    the first later frame within MUTE_WITHIN_S whose level is MUTE_DROP_DB or more under it; the mute is that frame's
    end. The search goes on after it."""
    n, hop = int(round(MUTE_FRAME_S * rate)), int(round(MUTE_HOP_S * rate))
    L = frame_levels_db(di, n, hop)
    if not len(L):
        return []
    top = float(L.max())
    w = int(round(MUTE_WITHIN_S / MUTE_HOP_S))
    out, i = [], 0
    while i < len(L):
        if L[i] >= top - MUTE_FLOOR_DB:
            j = next((j for j in range(i + 1, min(len(L), i + w + 1)) if L[j] <= L[i] - MUTE_DROP_DB), None)
            if j is not None:
                out.append((j * hop + n) / rate)
                i = j + 1
                continue
        i += 1
    return out


def note_end(on, off, ring, mutes, sample_s, repluck=None, cut=False):
    """(Pure.) When a redo note stops sounding and how: the first of its string's next pluck ("repluck", a 10-ms fade),
    a mute in the DI after its onset ("mute", 30 ms), the transcriber's note-off under `ring-soft` ("release": the
    note-off starts a 150-ms release; under `ring-on` the note-off never cuts), or its sample's end ("sample", the
    sample's last 150 ms). With `cut` (the install gate's known lists only, amendment `phase_nr_1_redo_known_amend`)
    the note also ends at its own note-off ("cut", the 10-ms fade ending there), so no note sounds past its declared
    end. Every fade ends at the returned time. -> (end, kind, fade seconds)."""
    if ring not in RING_VARIANTS:
        raise ValueError(ring)
    cands = [(on + sample_s, 1, "sample", TAIL_FADE_S)]
    if cut:
        cands.append((max(on, off), 0, "cut", REPLUCK_FADE_S))
    if repluck is not None and repluck > on:
        cands.append((repluck, 0, "repluck", REPLUCK_FADE_S))
    m = next((t for t in sorted(mutes) if t > on), None)
    if m is not None:
        cands.append((m, 0, "mute", MUTE_FADE_S))
    if ring == "ring-soft":
        cands.append((max(on, off) + RING_SOFT_S, 0, "release", RING_SOFT_S))
    end, _, kind, fade = min(cands)
    return end, kind, fade


def placed_free(pitch, taken, ringing, notes_ok=None):
    """(Pure.) The redo's placing rule (no tab): a free string (not `taken` in this onset group) that plays the pitch
    and is not still ringing, lowest fret first; when every free string that plays it is still ringing, the lowest
    fret among them. -> (string, fret) or None."""
    def best(strings):
        out = None
        for s in strings:
            f = pitch - OPEN_STRINGS[s]
            if s in taken or f not in FRETS or (notes_ok is not None and not notes_ok(s, f)):
                continue
            if out is None or f < out[1]:
                out = (s, f)
        return out
    return best([s for s in OPEN_STRINGS if s not in ringing]) or best(list(OPEN_STRINGS))


def variety_sources(pitch, placed_sf, taken, notes_ok=None):
    """(Pure.) The fixed order of sources for a re-struck pitch: the placed string and fret; the same pitch on another
    free string (lowest fret first); the placed string's neighbours one semitone either side (fret - 1, then fret + 1),
    retuned to the pitch. No randomness. -> [(string, fret)]."""
    s0, f0 = placed_sf
    out = [(s0, f0)]
    others = sorted(((s, pitch - o) for s, o in OPEN_STRINGS.items() if s != s0 and s not in taken
                     and pitch - o in FRETS), key=lambda sf: (sf[1], sf[0]))
    out += [sf for sf in others if notes_ok is None or notes_ok(*sf)]
    for f in (f0 - 1, f0 + 1):
        if f in FRETS and (notes_ok is None or notes_ok(s0, f)):
            out.append((s0, f))
    return out


def next_source(sources, last):
    """(Pure.) The source after `last` in the fixed order (cycling); the first when `last` is not among them. A re-struck
    pitch so never reuses its last sample while another source exists."""
    if last in sources:
        return sources[(sources.index(last) + 1) % len(sources)]
    return sources[0]


def bend_curve(note, others=()):
    """(Pure.) A redo note's bend in steps (thirds of a semitone) per Basic Pitch frame: its bend track, a 3-frame
    median, zero on frames where another note within BEND_CLEAR_SEMITONES sounds (transcriber's times), held within
    +-BEND_MAX_SEMITONES, and kept only on runs of BEND_MIN_FRAMES or more frames at one step or more. A note marked
    `keep_bend` (F6b's stitched notes, the bend lists' true bent notes; note-rebuild-plan 12t) skips the clear rule;
    without the mark the curve is as it always was. -> [steps]."""
    b = [float(v) for v in (note.get("bends") or [])]
    if not b:
        return []
    h = BEND_MEDIAN // 2
    med = []
    for j in range(len(b)):
        w = sorted(b[max(0, j - h):j + h + 1])
        med.append(w[len(w) // 2] if len(w) % 2 else (w[len(w) // 2 - 1] + w[len(w) // 2]) / 2)
    clear = [] if note.get("keep_bend") else range(len(med))
    for j in clear:
        t = note["on"] + j * BEND_FRAME_S
        if any(m is not note and abs(m["pitch"] - note["pitch"]) <= BEND_CLEAR_SEMITONES and m["on"] <= t < m["off"]
               for m in others):
            med[j] = 0.0
    lim = BEND_MAX_SEMITONES * BEND_STEPS_PER_SEMITONE
    med = [max(-lim, min(lim, v)) for v in med]
    out, j = [0.0] * len(med), 0
    while j < len(med):
        if abs(med[j]) >= 1:
            k = j
            while k < len(med) and abs(med[k]) >= 1:
                k += 1
            if k - j >= BEND_MIN_FRAMES:
                out[j:k] = med[j:k]
            j = k
        else:
            j += 1
    return out


def apply_bend(y, steps, lead_s, rate=SR):
    """`y` (a sample whose attack sits `lead_s` in) re-read at a variable rate so its pitch follows `steps` (thirds of
    a semitone per BEND_FRAME_S frame from the attack, linear between frame centres, 0 outside). -> audio, no longer
    than `y`."""
    import numpy as np

    if not any(steps):
        return y
    n = len(y)
    t = (np.arange(n) / rate) - lead_s
    centres = (np.arange(len(steps)) + 0.5) * BEND_FRAME_S
    cents = np.interp(t, centres, 100.0 / BEND_STEPS_PER_SEMITONE * np.asarray(steps, np.float64), left=0.0, right=0.0)
    pos = np.concatenate([[0.0], np.cumsum(2 ** (cents[:-1] / 1200))])
    keep = pos <= n - 1
    return np.interp(pos[keep], np.arange(n), y)


def synthesise_redo(notes, length, bank, tuning_cents=0.0, ring="ring-soft", mutes=(), tilt_db_s=0.0,
                    group_gain_db=None, rate=SR, cut=False, note_weights=None, group_trim=None):
    """The redo's dry guitar for a transcribed note list (`on`, `off`, `pitch`, `bends`) on `length` samples. Strings
    by `placed_free` in onset order (each group's notes low to high); a pitch struck again within VARIETY_S whose
    placed source is the sample it last played takes `next_source` in `variety_sources`' order (a re-struck pitch never
    reuses its last sample); each note ends by `note_end` (repluck, a mute in the DI, the `ring` variant's note-off, the
    sample's end); its bend by `bend_curve`; the sustain tilt `tilt_db_s` on every note (capped at +TILT_MAX_GAIN_DB);
    a group of k notes struck together at 1/sqrt(k); `group_gain_db` (one per onset group) adds the levels. The
    edge fade as stage 1's. Deterministic. The loudness option (note-rebuild-plan 12m, `phase_nr_1_redo_calib_amend`):
    `note_weights` (one gain per note, replacing 1/sqrt(k); `note_weights()`) and `group_trim` (one factor per onset
    group, never above 1; `group_trims()`); with both left out the gain line is today's, so `tr-di` and `tr-plain` stay
    byte for byte. -> (audio, report)."""
    import numpy as np

    if ring not in RING_VARIANTS:
        raise ValueError(ring)
    out = np.zeros(length)
    groups = onset_groups(notes)
    gain_of = {}
    for gi, g in enumerate(groups):
        extra = 0.0 if group_gain_db is None else group_gain_db[gi]
        for k in g:
            if note_weights is None and group_trim is None:
                gain_of[k] = 10 ** (extra / 20) / math.sqrt(len(g))
            else:
                w = note_weights[k] if note_weights is not None else 1 / math.sqrt(len(g))
                gain_of[k] = 10 ** (extra / 20) * w * (group_trim[gi] if group_trim is not None else 1.0)
    src, busy, last = {}, {}, {}
    swaps = 0
    for g in groups:
        taken = set()
        for k in sorted(g, key=lambda q: (notes[q]["pitch"], q)):
            n = notes[k]
            p = n["pitch"]
            ringing = {s for s, e in busy.items() if e > n["on"]}
            sp = placed_free(p, taken, ringing, bank.ok)
            if sp is None:
                continue
            prev = last.get(p)
            if prev is not None and n["on"] - prev[0] <= VARIETY_S and sp == prev[1]:
                sp = next_source(variety_sources(p, sp, taken, bank.ok), prev[1])
                swaps += sp != prev[1]
            s, f = sp
            semis = p - nominal_midi(s, f)
            if abs(semis) > MAX_SHIFT_SEMITONES:
                continue
            y = bank.note(s, f, 100.0 * semis + tuning_cents - bank.own_cents(s, f))
            src[k] = (s, f, y)
            end, _, _ = note_end(n["on"], n["off"], ring, mutes, len(y) / rate - PRE_ATTACK_S, cut=cut)
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
    skipped, ends, bent = [], {}, 0
    for k, n in enumerate(notes):
        if k not in src:
            skipped.append(k)
            continue
        y = src[k][2]
        steps = bend_curve(n, notes)
        if any(steps):
            bent += 1
            y = apply_bend(y, steps, PRE_ATTACK_S, rate)
        end, kind, fade_s = note_end(n["on"], n["off"], ring, mutes, len(y) / rate - PRE_ATTACK_S, nxt.get(k), cut=cut)
        start = int(round((n["on"] - PRE_ATTACK_S) * rate))
        dur = min(len(y), int(round((end - n["on"] + PRE_ATTACK_S) * rate)))
        if dur <= 0:
            skipped.append(k)
            continue
        ends[kind] = ends.get(kind, 0) + 1
        seg = y[:dur].copy()
        if tilt_db_s:
            tau = np.clip(np.arange(dur) / rate - PRE_ATTACK_S, 0.0, None)
            seg *= 10 ** (np.minimum(tilt_db_s * tau, TILT_MAX_GAIN_DB) / 20)
        fade = min(dur, int(round(fade_s * rate)))
        if fade:
            seg[dur - fade:] *= np.linspace(1.0, 0.0, fade)
        if start < 0:
            seg, start = seg[-start:], 0
        e = min(length, start + len(seg))
        if e > start:
            out[start:e] += gain_of[k] * seg[:e - start]
    edge = min(length // 2, int(EDGE_FADE_S * rate))
    if edge:
        out[:edge] *= np.linspace(0.0, 1.0, edge)
        out[length - edge:] *= np.linspace(1.0, 0.0, edge)
    return out, {"notes": len(notes), "played": len(notes) - len(skipped), "skipped": len(skipped),
                 "groups": len(groups), "bent": bent, "variety_swaps": swaps, "ends": ends}


def sustain_tilt(notes, plain, di, rate=SR):
    """(Pure.) The window's one sustain tilt, in dB per second: over onset groups with no other onset for
    TILT_ISOLATED_S after them (onset inside the window, its late span too), the level at TILT_LATE against TILT_EARLY
    from the onset, the DI's less the plain rebuild's (`plain`: `synthesise_redo` with no tilt and no levels), over
    the spans' centres' distance; the median, held within +-TILT_MAX_DB_S. Under TILT_MIN_GROUPS such groups: 0
    (reported). -> (tilt, report)."""
    import statistics

    groups = onset_groups(notes)
    starts = [notes[g[0]]["on"] for g in groups]
    n = min(len(plain), len(di))
    span = (sum(TILT_LATE) - sum(TILT_EARLY)) / 2

    def lvl(x, t, ab):
        return 20 * math.log10(span_rms(x, int(round((t + ab[0]) * rate)), int(round((t + ab[1]) * rate))) + 1e-12)
    slopes = []
    for gi, t in enumerate(starts):
        nxt = starts[gi + 1] if gi + 1 < len(starts) else math.inf
        if t < 0 or nxt - t < TILT_ISOLATED_S or (t + TILT_LATE[1]) * rate > n:
            continue
        d = (lvl(di, t, TILT_LATE) - lvl(di, t, TILT_EARLY)) - (lvl(plain, t, TILT_LATE) - lvl(plain, t, TILT_EARLY))
        slopes.append(d / span)
    if len(slopes) < TILT_MIN_GROUPS:
        return 0.0, {"isolated_groups": len(slopes), "tilt_db_s": None, "applied": False}
    raw = statistics.median(slopes)
    tilt = max(-TILT_MAX_DB_S, min(TILT_MAX_DB_S, raw))
    return tilt, {"isolated_groups": len(slopes), "tilt_db_s": tilt, "raw_db_s": raw, "applied": True,
                  "clamped": tilt != raw}


LOUD_GAMMA = (1.0, 2.0)                  # the loudness option's settings: 1 first, 2 only if 1 is not enough
SOFT_DB = -3.0                          # a note turned down by more than 3 dB (weight and trim together) is "soft"


def note_weights(notes, gamma):
    """(Pure.) Each note's gain inside its onset group at its detected loudness: its amplitude over the group's
    largest, to the power `gamma`, the group rescaled so its power is today's (k notes at 1/sqrt(k) have power 1).
    Equal amplitudes give exactly today's 1/sqrt(k). A note without an amplitude counts as 1. -> [gain per note]."""
    out = [0.0] * len(notes)
    for g in onset_groups(notes):
        amps = [float(notes[k].get("amp", 1.0) or 0.0) for k in g]
        top = max(amps)
        if top <= 0:
            w = [1.0] * len(g)
        else:
            w = [(a / top) ** gamma for a in amps]
        norm = math.sqrt(sum(x * x for x in w))
        for k, x in zip(g, w):
            out[k] = x / norm if norm > 0 else 1 / math.sqrt(len(g))
    return out


def group_trims(notes, gamma):
    """(Pure.) Each onset group's turndown: a group that starts while louder notes still sound (another group's
    note with on < onset < off, the transcriber's times) is turned down by its largest amplitude over the largest still
    sounding, to the power `gamma`; never turned up. -> [factor per group]."""
    groups = onset_groups(notes)
    out = []
    for g in groups:
        t = notes[g[0]]["on"]
        top = max(float(notes[k].get("amp", 1.0) or 0.0) for k in g)
        inside = set(g)
        sounding = [float(m.get("amp", 1.0) or 0.0) for j, m in enumerate(notes)
                    if j not in inside and m["on"] < t < m["off"]]
        loud = max(sounding) if sounding else 0.0
        out.append(min(1.0, top / loud) ** gamma if loud > 0 else 1.0)
    return out


def note_turndown_db(notes, gamma):
    """(Pure.) Each note's turndown in dB at `gamma`, weight and trim together, against today's 1/sqrt(k)."""
    w, t = note_weights(notes, gamma), group_trims(notes, gamma)
    out = [0.0] * len(notes)
    for gi, g in enumerate(onset_groups(notes)):
        for k in g:
            f = w[k] * math.sqrt(len(g)) * t[gi]
            out[k] = 20 * math.log10(f) if f > 0 else -math.inf
    return out


def rebuild_redo(arm, notes, length, bank, di, ring, finish=None, rate=SR, loud=None):
    """One redo dry guitar. `notes`: the window's transcribed notes after the clean-up and the onset steps
    (`note_transcribe.timed_notes`); `di`: the true DI as the row renders it (its tuning, mutes, sustain tilt and, for
    `tr-di`, levels by `oracle_gains`); `ring`: the variant chosen at `note_transcribe calibrate`; `finish`: the row's chain
    (`song_bank.measure`, then `average_balance` with the part's others) or None. `tr-plain` is `tr-di` without the
    per-group levels. Both end at ASSUMED_LUFS; the hiss removal runs again after `tr-di`'s level gain, as stage 1's
    level arms. `loud` (a LOUD_GAMMA value, or None: off) plays each note at its detected loudness: `note_weights` in
    every pass, `group_trims` in the last only, after the group's level, so the level step cannot undo it.
    -> (audio, report)."""
    if arm not in REDO_ARMS:
        raise ValueError(arm)
    tune = global_tuning_cents(di, rate)
    mutes = mute_times(di, rate)
    padded = length + int(round(END_PAD_S * rate))
    if loud is None:
        plain0, _ = synthesise_redo(notes, padded, bank, tune, ring, mutes, 0.0, None, rate)
        tilt, trep = sustain_tilt(notes, plain0[:length], di, rate)
        plain, rep = synthesise_redo(notes, padded, bank, tune, ring, mutes, tilt, None, rate)
        if arm == "tr-plain":
            y = plain
        else:
            y, rep = synthesise_redo(notes, padded, bank, tune, ring, mutes, tilt,
                                     oracle_gains(notes, plain[:length], di, rate), rate)
            y = denoise_above(y, rate)
    else:
        w, trims = note_weights(notes, loud), group_trims(notes, loud)
        plain0, _ = synthesise_redo(notes, padded, bank, tune, ring, mutes, 0.0, None, rate, note_weights=w)
        tilt, trep = sustain_tilt(notes, plain0[:length], di, rate)
        plain, rep = synthesise_redo(notes, padded, bank, tune, ring, mutes, tilt, None, rate, note_weights=w)
        if arm == "tr-plain":
            y, rep = synthesise_redo(notes, padded, bank, tune, ring, mutes, tilt, None, rate, note_weights=w,
                                     group_trim=trims)
        else:
            y, rep = synthesise_redo(notes, padded, bank, tune, ring, mutes, tilt,
                                     oracle_gains(notes, plain[:length], di, rate), rate, note_weights=w,
                                     group_trim=trims)
            y = denoise_above(y, rate)
        rep = {**rep, "loud_gamma": loud}
    if finish is not None:
        y = finish(y)
    y = at_lufs(y[:length], ASSUMED_LUFS, rate)
    return y, {**rep, "tuning_cents": round(tune, 2), "mutes": len(mutes), "tilt": trep, "ring": ring,
               "lufs": ASSUMED_LUFS}


# --- the stage-1 figures (reports only; zero render cost) ---------------------------------------------------------------

def crest_db(x):
    import numpy as np

    rms = np.sqrt(np.mean(x ** 2))
    return float(20 * np.log10(np.abs(x).max() / (rms + 1e-20) + 1e-20)) if rms > 0 else float("nan")


def envelope_corr(a, b, frame=1024):
    """(Pure.) The correlation of two signals' frame-RMS envelopes in dB (1,024-sample frames, half hop)."""
    import numpy as np

    def env(x):
        n = max(0, (len(x) - frame) // (frame // 2) + 1)
        idx = np.arange(frame)[None, :] + (frame // 2) * np.arange(n)[:, None]
        return 10 * np.log10(np.mean(x[idx] ** 2, axis=1) + 1e-12)

    k = min(len(a), len(b))
    ea, eb = env(a[:k]), env(b[:k])
    if len(ea) < 3 or ea.std() == 0 or eb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ea, eb)[0, 1])


def logmel_distance(a, b, rate=SR, floor_db=40.0):
    """(Pure.) The mean absolute frame-by-frame log-mel difference (J0's 2,048-sample mel grid,
    `analysis.aligned._logmel`) over the frames where `a` (the true DI) plays (J0's rule: within floor_db of its
    loudest frame), both sides loudness-free (each side's mean over those frames removed)."""
    import numpy as np

    from analysis import aligned as A

    k = min(len(a), len(b))
    A1, _ = A._logmel(a[:k], 2048, rate)
    B1, _ = A._logmel(b[:k], 2048, rate)
    fa = A._frame_db(a[:k], 2048)
    m = min(len(A1), len(B1), len(fa))
    play = fa[:m] >= fa[:m].max() - floor_db
    if play.sum() < 1:
        return float("nan")
    A1, B1 = A1[:m][play], B1[:m][play]
    return float(np.mean(np.abs((A1 - A1.mean()) - (B1 - B1.mean()))))


def share_above(x, hz=2000.0, rate=SR):
    import numpy as np

    s = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / rate)
    return float(s[f >= hz].sum() / (s.sum() + 1e-20))


def mask_agreement(true_di, dry, floor_db=40.0):
    """(Pure.) J0's playing-frame mask (`aligned_distance`: frames within di_floor_db of the DI's loudest) from the
    rebuilt dry guitar against the true DI's, at each of J0's frame sizes: the share of frames on which they agree and
    the rebuilt mask's pause share. -> {n_fft: {agree, pauses_true, pauses_dry}}."""
    import numpy as np

    from analysis import aligned as A

    out = {}
    for n_fft in A.FRAME_SIZES:
        k = min(len(true_di), len(dry))
        t = A._frame_db(true_di[:k], n_fft)
        d = A._frame_db(dry[:k], n_fft)
        pt, pd = t >= t.max() - floor_db, d >= d.max() - floor_db
        out[n_fft] = {"agree": float(np.mean(pt == pd)), "pauses_true": float(1 - pt.mean()),
                      "pauses_dry": float(1 - pd.mean())}
    return out


def figures(true_di, dry, rate=SR):
    """The stage-1 component figures for one window (reports, never gates)."""
    return {"crest_diff_db": crest_db(dry) - crest_db(true_di), "env_corr": envelope_corr(true_di, dry),
            "logmel": logmel_distance(true_di, dry, rate), "above2k_dry": share_above(dry, rate=rate),
            "above2k_true": share_above(true_di, rate=rate), "mask": mask_agreement(true_di, dry)}


# --- P7: the timing probe ------------------------------------------------------------------------------------------------

def cmd_probe(args):
    """P7. Seconds per 10-s window on the CPU: the oracle onset step, each arm's re-synthesis (with
    `song_bank.measure` as the finishing chain, the true DI through `song_bank.measure` as `nr-oracle` reads it) and the
    figures' computation, on GOAT development items clear of the exclusion list (`assert_clear` before any is read).
    Timing only: no figure, level or audio is stored (development items, not evidence). -> note-rebuild/probe.json."""
    require(PHASE_P)
    refuse_existing(OUT / "probe.json")
    excl = load_exclusion()
    notes_doc = load_notes_doc()
    import csv                                      # after the refusals
    import io
    import zipfile

    import soundfile as sf

    from learn import clean_di as CD
    from learn import pretrain_set as PS
    from learn import song_bank as SB

    bank = Bank(notes_doc, excl=excl)
    sec = int(round((PS.SEC_S + PS.TRIM_S) * SR))
    rows = []
    with zipfile.ZipFile(GOAT_ZIP) as z:
        names = set(z.namelist())
        meta = {r["item"]: r for r in csv.DictReader(io.StringIO(z.read("GOAT/metadata.csv").decode()))}
        dev = [it for it in sorted(meta, key=lambda s: int(s.split("_")[1]))
               if not clear_of({"goat_item": it}, excl) and f"GOAT/data/{it}/{it}_fine_aligned.mid" in names]
        assert_clear([{"goat_item": it} for it in dev], excl)
        for it in dev[:args.items]:
            rec = true_notes_for(it, z, meta)
            if "notes" not in rec:
                continue
            x, sr = sf.read(io.BytesIO(z.read(f"GOAT/data/{it}/{it}.wav")), dtype="float64", always_2d=True)
            x = CD.resample(x.mean(1), sr, SR)
            start = 30.0 if len(x) / SR > 45 else 1.0
            raw = x[int(start * SR):int(start * SR) + sec]
            if len(raw) < sec:
                continue
            t0 = time.perf_counter()
            di = SB.measure(raw)
            times = {"measure_di": time.perf_counter() - t0}
            notes = window_notes(rec["notes"], start, sec / SR)
            t0 = time.perf_counter()
            ref_notes, _ = refine_onsets(notes, di)
            times["refine"] = time.perf_counter() - t0
            for arm in ARMS:
                t0 = time.perf_counter()
                y, _ = rebuild_dry(arm, ref_notes, sec, bank, di, di=di, finish=SB.measure)
                times[arm] = time.perf_counter() - t0
                t0 = time.perf_counter()
                figures(di, y)
                times[f"figures:{arm}"] = time.perf_counter() - t0
            rows.append({"item": it, "notes": len(notes), "times_s": {k: round(v, 3) for k, v in times.items()},
                         "prepared_notes": len(bank._prep)})
            print(f"{it}: {len(notes)} notes; " + ", ".join(f"{k} {v:.2f}s" for k, v in times.items()), flush=True)
    body = {"rows": rows, "machine": os.uname().machine, "cpu_only": True, "evidence": False,
            "note": "timing only, on development items; the first windows include the bank's one-time note "
                    "preparation; later windows reuse it"}
    doc = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE_P}", "made": time.strftime("%Y-%m-%d %H:%M:%S"),
           "body": body, "body_sha256": content_sha(body)}
    h = write_once(OUT / "probe.json", doc)
    print(f"PROBE DONE: {len(rows)} windows; doc sha256 {h}")


# --- stage P's code -----------------------------------------------------------------------------------------------------

def np_code(p1, p2_failed, p3, p4, replay_goat_carrying):
    """(Pure.) NP_TABLE's codes, in order: NP-broken alone; or NP-gap followed by the count's code; or the count's
    code. `replay_goat_carrying`: the replay's drawn GOAT parts that carry true notes, None before the replay's draw
    (then the count's code waits). -> list of codes."""
    if not (p1 and p3 and p4):
        return ["NP-broken"]
    out = ["NP-gap"] if p2_failed else []
    if replay_goat_carrying is not None:
        out.append("NP-ready" if replay_goat_carrying >= NP_MIN_CARRYING else "NP-few")
    return out


NP_MIN_CARRYING = 30


def cmd_ready(args):
    """Stage P's codes from P1-P4's records (P4: the test suite's result, passed in by --p4-ok after it runs; the
    replay's drawn GOAT parts from its draw, when it exists)."""
    require(PHASE_P)
    table_guard()
    ex, nd, tn = load_exclusion(), load_notes_doc(), load_doc("true-notes.json")
    drawn = None
    draw = PF / "replay/draw.json"
    if draw.exists():
        d = json.loads(draw.read_text())
        keys = {f"{p['unit']}|{p['amp']}" for p in d.get("parts", []) if p.get("set") == "goat"}
        drawn = sum(tn["units"].get(k, {}).get("carries", False) for k in keys)
    codes = np_code(ex["p1_ok"], nd["failed_in_pickup"], tn["p3_ok"], args.p4_ok, drawn)
    print(json.dumps({"codes": codes, "replay_goat_carrying": drawn, "failed_in_pickup": nd["failed_in_pickup"],
                      "goat_units_carrying_all": tn["goat_units_carrying"]}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="learn.note_rebuild")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("exclusion").set_defaults(fn=cmd_exclusion)
    sub.add_parser("notes").set_defaults(fn=cmd_notes)
    sub.add_parser("true-notes").set_defaults(fn=cmd_true_notes)
    p = sub.add_parser("probe")
    p.add_argument("--items", type=int, default=6)
    p.set_defaults(fn=cmd_probe)
    p = sub.add_parser("ready")
    p.add_argument("--p4-ok", action="store_true")
    p.set_defaults(fn=cmd_ready)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
