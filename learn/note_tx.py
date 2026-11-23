"""Research track 1, a better note transcriber: does a second transcriber (MuScriptor medium) give the note rebuild a
note list with clearly fewer extra notes, no loss of real notes our checks can see, and a note F that is not worse?
(`docs/note-transcriber-plan.md`; ledger `note-transcriber` `phase_tx`, then `phase_tx_go`, `phase_tx_install`,
`phase_tx_lists`, `phase_tx_go_read`, `phase_tx_notes`, `phase_tx_read`, `phase_tx_bridge`.) Zero plugin renders, no
training. "Transcriber" and the prefix `tx`, because "reader" already means the knob reader in this repo.

    $MAIN -m learn.note_tx install      # phase 2: the hashed venv, the user's weights checked (a declared download)
    $MAIN -m learn.note_tx gate         # phase 2: repeat and speed on MPS and the CPU; the device, the size; then the
                                        #          ten lists transcribed with that model (`--size small` after a switch)
    $MAIN -m learn.note_tx lists        # phase 3a, once: the list screen (TXR-none or lists-go)
    $MAIN -m learn.note_tx transcribe   # phase 3b: MuScriptor on the consistent truth windows and the 27 windows
    $MAIN -m learn.note_tx read         # phase 3b, once: the read and its code (TXR-vote, TXR-ms, TXR-ends,
                                        #          TXR-undecided)
    $MAIN -m learn.note_tx bridge       # phase 4, once: the winner against "Measure first"'s stored distances

$MAIN is the main checkout's .venv python (in a worktree add `--data-dir ~/ndsp-presets` through the environment the
replay used). Every command refuses unless this checkout runs main's code (`tx_on_main`: the redo's `CODE_FILES` and
this track's two files equal main's, and the `note-transcriber` entry's `phase_tx*` keys equal main's) and main's
ledger holds the phases the step needs. Every output is written once (`never_overwrite`), under PF/note-rebuild/tx/.
MuScriptor and torch are imported only inside `learn/tx_run.py`, run by its venv's own interpreter in a subprocess with
HF_HUB_OFFLINE=1; nothing here imports them. Basic Pitch is never run again on a DI: its note files come from the
gate's stored list events and "Measure first"'s truth report, loaded by their recorded sha256.

The input guard (MuScriptor's terms forbid transcribing music without the rights to it): `declared_input` is the only
way an input manifest row is made, and it refuses anything outside the declared material: a known list, a P1 or P2
truth window from the hashed listing, or one of the 27 GOAT development windows. `tx_run` refuses any input not in
that manifest.

The pure parts (the guard, the pairing, the vote, the veto, the borrowed loudness, the figures, the readings, the
screen, the code, the recommendation, the bridge table, the lock, the install record, the device and size rules, the
guards) are tested in tests/test_note_tx.py on the light CI runner (no numpy); the commands' numpy parts in
tests/test_note_tx_np.py.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import statistics
import time

from learn import note_rebuild as NR
from learn import note_transcribe as T
from learn import note_truth as NTR
from learn import note_versions as NV
from learn import tx_run as TR

LEDGER_ID = "note-transcriber"
PLAN = "docs/note-transcriber-plan.md"
PHASE = "phase_tx"                       # this declaration
PHASE_GO = "phase_tx_go"                 # the user's go on the difference, the terms and the download (phase 0)
PHASE_INSTALL = "phase_tx_install"       # the lock, the weights, the gate file, the device, the list notes' listing
PHASE_LISTS = "phase_tx_lists"           # the list screen's result
PHASE_GO_READ = "phase_tx_go_read"       # the user's go on stage b, after Basic Pitch's real-DI precision is known
PHASE_NOTES = "phase_tx_notes"           # stage b's note files' listing, hashed before any scoring
PHASE_READ = "phase_tx_read"             # the read's code
PHASE_BRIDGE = "phase_tx_bridge"         # the bridge's deciding difference
RESERVED_PHASES = ("phase_tx_stems", "phase_tx_stem_read")   # the stems declaration's, not this one's
RESERVED_SEEDS = (20261411, 20261412)
RESERVED_CODE_PREFIX = "TXS-"
NR_ID = NR.LEDGER_ID                     # note-rebuild: "Measure first"'s keys are read, never written

OUT = NR.OUT / "tx"                      # PF/note-rebuild/tx/

# --- the install (plan B0), checked against PyPI and Hugging Face on 2026-11-22 ------------------------------------------
TOOLS = NR.HOME / "tools" / "muscriptor-venv"
WEIGHTS_DIR = NR.HOME / "tools" / "muscriptor-weights"   # the user's browser download: <size>/model.safetensors, config.json
MS_PYTHON = TOOLS / "bin" / "python"
LOCK = TOOLS / "requirements.lock"
RESOLVE = TOOLS / "resolve.json"
MANIFEST = TOOLS / "manifest.json"
INTERPRETER = str(pathlib.Path.home() / ".pyenv" / "versions" / "3.14.6" / "bin" / "python")
FALLBACK_INTERPRETER = "/opt/homebrew/opt/python@3.13/bin/python3.13"   # only on the user's yes (a named download)
PYTHONS = ("3.14", "3.13")               # the declared interpreter's minor version and the fallback's; nothing else
PACKAGE = ("muscriptor", "0.4.0", "a7e941b6e1d85a25f9fc4e00c2a46b43d4d516de0e751d54b42fda438ac2abb9", 1850618)
WEIGHTS = {
    "medium": {"repo": "MuScriptor/muscriptor-medium", "revision": "f32236969308476e01fd3aae67357de5feb05a2d",
               "sha256": TR.WEIGHTS["medium"][0], "bytes": TR.WEIGHTS["medium"][1], "config_bytes": 126},
    "small": {"repo": "MuScriptor/muscriptor-small", "revision": "8c127f603b807520fa465c838e9bfee8a91ada4e",
              "sha256": TR.WEIGHTS["small"][0], "bytes": TR.WEIGHTS["small"][1], "config_bytes": 124},
}
REQUIREMENTS = ("torch>=2.3", "numpy>=2", "einops>=0.4", "mido>=1.3", "packaging>=20.0", "safetensors>=0.4",
                "huggingface_hub>=0.13", "soundfile>=0.14.0")   # what `transcribe()` needs; no server, no beat tracker
NOT_NEEDED = ("beat-this", "fastapi", "typer", "uvicorn")   # the server and beat-tracking parts: never in the lock
INSTALL_MIN_GB = 36.0                    # the install refuses under this (the disk guard is 31 GB)
LICENCES = {"muscriptor code": "MIT", "muscriptor weights": "CC BY-NC 4.0 (gated; Kyutai and Mirelo)",
            "the rest": "from each wheel's metadata (resolve.json)"}
APPROVAL = {"date": "2026-11-23", "ledger": f"{LEDGER_ID} {PHASE_GO}"}   # a date and a ledger key only: no account
                                                                         # name, email or token, ever
PRIVATE_WORDS = ("account", "email", "e-mail", "token", "username", "login")

# --- the call (plan B0) -------------------------------------------------------------------------------------------------
MS_SR = 16000                            # 48 kHz to 16 kHz by resample_poly(x, 1, 3)
MS_UP, MS_DOWN = 1, 3
MS_PEAK_DBFS = -1.0
MS_SETTINGS = TR.MASKED                  # tx-ms: greedy, guidance 1.0, the guitar groups only
MS_FREE_SETTINGS = TR.FREE               # tx-ms-free: no instrument mask, drums dropped
NOTE_KINDS = {"list": MS_SETTINGS, "list-free": MS_FREE_SETTINGS, "truth": MS_SETTINGS, "goat": MS_SETTINGS,
              "goat-free": MS_FREE_SETTINGS}
DEVICE_DTYPE = {"mps": "float16", "cpu": "float32"}
REPEAT_WINDOWS = T.REPEAT_WINDOWS        # the gate's four development windows, three runs each per device
STAGE_B_WINDOWS = 265                    # at most 238 truth windows and the 27 development windows
SIZE_SWITCH_S = 2 * 3600.0               # over this projected for stage b: every MuScriptor arm moves to small

# --- the comparison (plan sections 4 and B0) ----------------------------------------------------------------------------
PAIR_ONSET_S = 0.050                     # same MIDI pitch, onsets within 50 ms, one to one, closest first
END_SHARE, END_MIN_S = 0.20, 0.050       # a note end within max(20% of the true note, 50 ms)
VETO_INTERVALS = (12, 19, 24)            # the ghost shape: an octave, a twelfth, two octaves above a paired note
SOUNDING_LEAD_S = 0.050                  # an extra sorted against the truth notes sounding at its onset (50 ms lead)
RECALL_GUARD = 0.05                      # recall and chord-note recall at most this under tx-bp's (PR #547's size)
CHECK_SLACK = 1                          # each check on the 27 windows passes on at most one window fewer
UNPAIRED_LOOKUP = 0.05                   # TXR-ms with more of its notes unpaired: a loudness and bend lookup first
GUARDED_CHECKS = ("playing-covered", "judge-accepts", "ring-kept", "chords-kept")   # onsets-found is a report
DECIDING_RING, BESIDE_RING = NV.DECIDING_RING, NV.BESIDE_RING
ARMS = ("tx-bp", "tx-ms", "tx-vote")
BESIDE_ARMS = ("tx-veto", "tx-ms-free")
ALL_ARMS = ARMS + BESIDE_ARMS
BUILT_ARMS = ("tx-bp", "tx-ms", "tx-vote", "tx-veto")   # the dry guitars built on the 27 windows (tx-ms-free: notes only)
BRIDGE_VERSIONS = ("bv-asis", "bv-loud", "bv-ends")
FIELDS = ("precision", "recall", "f", "end_f", "chord_recall")
SETS = ("lists", "real")                 # the deciding sets; P1, P2 and each kind are reported apart
SCREEN = ("TXR-none", "lists-go")
CODES = ("TXR-vote", "TXR-ms", "TXR-ends", "TXR-undecided")
FLAG_VETO = "veto-holds"
RECOMMENDATION = {
    "TXR-none": "stop: stage b does not run and the route stays on Basic Pitch with whatever 'Measure first' "
                "decides; Basic Pitch's P1 and P2 precision is copied into the results once truth-report.json "
                "exists, so the user can reopen the track",
    "lists-go": "to the user with Basic Pitch's real-DI precision (P1 and P2, chords and scales apart, from "
                "truth-report.json); stage b runs only on the user's go (phase_tx_go_read)",
    "TXR-vote": "the bridge (phase 4), then the questions in section 7 (MuScriptor cannot ship: a win is a "
                "development oracle)",
    "TXR-ms": "the bridge (phase 4), then the questions in section 7; Basic Pitch stays beside MuScriptor for "
              "loudness and bends",
    "TXR-ends": "note ends only: Basic Pitch's notes with MuScriptor's note-off where paired (bv-ends), tested in "
                "the bridge; never straight to a change",
    "TXR-undecided": "reported with effect sizes; no change to the route",
}
VETO_CANDIDATE = "veto-holds: the veto is put to the user as the candidate (an open rule in its shape, section 7)"
LOOKUP_FIRST = ("more than 5% of tx-ms's notes have no Basic Pitch partner: any amendment first adds a loudness and "
                "bend lookup from Basic Pitch's own frame output for those notes")


# --- the input guard (pure) ---------------------------------------------------------------------------------------------

def declared_input(source, listing, dev_items):
    """(Pure.) The only way an input manifest row is made: `list:<name>` (a key of `note_transcribe.KNOWN_NOTES`),
    `truth:<window key>` (a P1 or P2 window of the hashed listing whose file passes `note_truth.refuse_path`) or
    `goat-dev:<item>` (one of the 27 development windows, clear of the exclusion list). Refuses anything else: a row
    part, a replay part, a stem, a song, a P3 path, a GOAT item outside the 27, any path. -> {source, kind, key}."""
    why = TR.source_refusal(source)
    if why:
        raise SystemExit(f"not declared material: {why}")
    kind, key = source.split(":", 1)
    if kind == "list":
        if key not in T.KNOWN_NOTES:
            raise SystemExit(f"{source}: not one of the ten known lists")
    elif kind == "truth":
        win = next((w for w in (listing or {}).get("windows") or [] if w.get("key") == key), None)
        if win is None:
            raise SystemExit(f"{source}: not a window of the hashed truth listing")
        if win.get("player") not in ("P1", "P2"):
            raise SystemExit(f"{source}: only P1 and P2 are declared (P3 is never read)")
        fk = f"{win['player']}|{win['kind']}|{win['name']}"
        f = next((x for x in listing.get("files") or [] if f"{x['player']}|{x['kind']}|{x['name']}" == fk), None)
        if f is None:
            raise SystemExit(f"{source}: its file is not in the listing")
        for p in (f["di"], f.get("midi") or f["di"]):
            r = NTR.refuse_path(p)
            if r:
                raise SystemExit(f"{source}: {r}")
    elif kind == "goat-dev":
        items = list(dev_items or [])
        if len(items) != T.DEV_COUNT:
            raise SystemExit(f"{len(items)} development items given, not the declared {T.DEV_COUNT}")
        if key not in items:
            raise SystemExit(f"{source}: not one of the 27 development windows")
    return {"source": source, "kind": kind, "key": key}


def manifest_doc(rows):
    """(Pure.) The input manifest tx_run reads: [(source, sha256)] -> {"inputs": [{sha256, source}]}."""
    return {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "inputs": [{"sha256": s, "source": src}
                                                                       for src, s in rows]}


# --- the note lists (pure) ----------------------------------------------------------------------------------------------

def ms_events(rec):
    """(Pure.) A MuScriptor note file -> the events `note_transcribe.timed_notes` reads (no loudness, no bend) and
    its pre_s: {"events", "pre_s"}."""
    return {"events": [{"on": n["on"], "off": n["off"], "pitch": n["pitch"], "amp": 0.0, "bends": []}
                       for n in rec["notes"]], "pre_s": rec["pre_s"]}


def end_match(ref, est, share=END_SHARE, floor=END_MIN_S):
    """(Pure.) `est`'s note-off within max(share of `ref`'s length, floor) of `ref`'s."""
    return abs(est["off"] - ref["off"]) <= max(share * (ref["off"] - ref["on"]), floor)


def pair_notes(a, b, onset_s=PAIR_ONSET_S, ends=False):
    """(Pure.) One-to-one pairs of two note lists by `match_notes`'s rule: same MIDI pitch, onsets within `onset_s`,
    the closest first. With `ends`, a pair also needs b's note-off within `end_match` of a's. -> [(i in a, j in b)]."""
    cand = sorted((abs(r["on"] - e["on"]), i, j) for i, r in enumerate(a) for j, e in enumerate(b)
                  if r["pitch"] == e["pitch"] and abs(r["on"] - e["on"]) <= onset_s and (not ends or end_match(r, e)))
    ui, uj, out = set(), set(), []
    for _, i, j in cand:
        if i not in ui and j not in uj:
            ui.add(i)
            uj.add(j)
            out.append((i, j))
    return sorted(out)


def vote_notes(bp, ms):
    """(Pure.) `tx-vote`: a Basic Pitch note is kept only if MuScriptor has the same pitch within 50 ms (one to one,
    closest first); each kept note as Basic Pitch gave it, MuScriptor's note-off carried beside (`ms_off`)."""
    pairs = dict(pair_notes(bp, ms))
    return [dict(n, ms_off=ms[pairs[i]]["off"]) for i, n in enumerate(bp) if i in pairs]


def veto_notes(bp, ms, intervals=VETO_INTERVALS):
    """(Pure.) `tx-veto`: every paired Basic Pitch note, and every unpaired one unless a paired note in its own onset
    group (`note_transcribe.groups_of`'s groups) sits exactly 12, 19 or 24 semitones below it. No free number."""
    paired = {i for i, _ in pair_notes(bp, ms)}
    out = []
    for g in NR.onset_groups(bp):
        below = {bp[k]["pitch"] for k in g if k in paired}
        for k in g:
            if k in paired or not any(bp[k]["pitch"] - p in intervals for p in below):
                out.append(k)
    return [dict(bp[k]) for k in sorted(out)]


def window_median_amp(bp):
    """(Pure.) The window's median Basic Pitch loudness, or None with no note."""
    amps = [float(n.get("amp", 0.0) or 0.0) for n in bp]
    return statistics.median(amps) if amps else None


def ms_with_bp(ms, bp):
    """(Pure.) `tx-ms`: MuScriptor's notes, each paired one borrowing its Basic Pitch partner's loudness and bend
    track; an unpaired note gets the window's median loudness (none when Basic Pitch has no note: it then counts as 1)
    and no bend. -> (notes, {notes, unpaired, unpaired_share})."""
    pairs = {j: i for i, j in pair_notes(bp, ms)}
    med = window_median_amp(bp)
    out = []
    for j, n in enumerate(ms):
        m = {k: n[k] for k in ("on", "off", "pitch")}
        if j in pairs:
            src = bp[pairs[j]]
            m.update(amp=src.get("amp", 1.0), bends=list(src.get("bends") or []))
        else:
            m.update(bends=[])
            if med is not None:
                m["amp"] = med
        out.append(m)
    un = len(ms) - len(pairs)
    return out, {"notes": len(ms), "unpaired": un, "unpaired_share": un / len(ms) if ms else None}


def ends_notes(bp, ms):
    """(Pure.) `bv-ends`'s notes: every Basic Pitch note, with MuScriptor's note-off where paired."""
    pairs = dict(pair_notes(bp, ms))
    return [dict(n, off=max(n["on"], ms[pairs[i]]["off"])) if i in pairs else dict(n) for i, n in enumerate(bp)]


def arm_notes(bp, ms, ms_free=None):
    """(Pure.) Every arm's notes from the two transcribers' timed notes. -> ({arm: notes}, {arm: borrow report})."""
    out = {"tx-bp": [dict(n) for n in bp], "tx-vote": vote_notes(bp, ms), "tx-veto": veto_notes(bp, ms)}
    out["tx-ms"], rep = ms_with_bp(ms, bp)
    reps = {"tx-ms": rep}
    if ms_free is not None:
        out["tx-ms-free"], reps["tx-ms-free"] = ms_with_bp(ms_free, bp)
    return out, reps


# --- the figures (pure) -------------------------------------------------------------------------------------------------

def restruck_indices(truth):
    """(Pure.) The true notes whose pitch is struck again while an earlier true note of that pitch still rings."""
    return [k for k, n in enumerate(truth)
            if any(m is not n and m["pitch"] == n["pitch"] and m["on"] < n["on"] < m["off"] for m in truth)]


def extras_sorted(truth, est, paired, lead=SOUNDING_LEAD_S, intervals=VETO_INTERVALS):
    """(Pure.) The unpaired found notes sorted as the review sorted them, against the true notes sounding at each one's
    onset (from `lead` before their onset to their note-off): "harmonic" (12, 19 or 24 semitones above one), else
    "re-find" (its pitch), else "other". paired: the found notes' indices that pair. -> counts."""
    out = {"harmonic": 0, "re-find": 0, "other": 0}
    for j, e in enumerate(est):
        if j in paired:
            continue
        snd = [t for t in truth if t["on"] - lead <= e["on"] < t["off"]]
        if any(e["pitch"] - t["pitch"] in intervals for t in snd):
            out["harmonic"] += 1
        elif any(e["pitch"] == t["pitch"] for t in snd):
            out["re-find"] += 1
        else:
            out["other"] += 1
    return out


def bend_frames(note, others):
    """(Pure.) The frames of a note's bend track that `note_rebuild.bend_curve` keeps (non-zero)."""
    return sum(1 for v in NR.bend_curve(note, others) if v)


def bend_figures(truth, notes, bp):
    """(Pure.) The bend report: the bent notes (the truth's where it has bends, the bend list; else Basic Pitch's own
    bent notes, by `bend_curve`), how many of them the arm keeps (pairs), and the mean share of each one's span that
    still carries a bend track in the kept note (0 where not kept). -> {ref, bent, kept, span_share}."""
    if truth and any(any(n.get("bends") or []) for n in truth):
        ref, kind = [n for n in truth if any(n.get("bends") or [])], "truth"
    else:
        ref, kind = [n for n in bp if bend_frames(n, bp)], "tx-bp"
    if not ref:
        return {"ref": kind, "bent": 0, "kept": 0, "span_share": None}
    pairs = dict(pair_notes(ref, notes))
    shares = []
    for i, r in enumerate(ref):
        if i not in pairs:
            shares.append(0.0)
            continue
        span = max(r["off"] - r["on"], 1e-9)
        shares.append(min(1.0, bend_frames(notes[pairs[i]], notes) * NR.BEND_FRAME_S / span))
    return {"ref": kind, "bent": len(ref), "kept": len(pairs), "span_share": sum(shares) / len(shares)}


def window_figures(truth, est):
    """(Pure.) One window's figures for one arm against the truth: matched, ref, est, precision, recall, F; note-end
    F (a pair also needs its end, `end_match`); chord-note recall (`note_versions.chord_indices`); the recall of a
    pitch struck again while it rings (underpowered on the lists: a report); the extras sorted."""
    pairs = pair_notes(truth, est)
    m, me = len(pairs), len(pair_notes(truth, est, ends=True))
    nr, ne = len(truth), len(est)
    found = {i for i, _ in pairs}
    ch, rs = NV.chord_indices(truth), restruck_indices(truth)
    return {"matched": m, "ref": nr, "est": ne, "precision": m / ne if ne else None, "recall": m / nr if nr else None,
            "f": 2 * m / (nr + ne) if nr + ne else None, "end_matched": me,
            "end_f": 2 * me / (nr + ne) if nr + ne else None,
            "chord_notes": len(ch), "chord_found": sum(i in found for i in ch),
            "chord_recall": NV.recall_of(found, ch), "restruck_notes": len(rs), "restruck_found": sum(i in found for i in rs),
            "extras": extras_sorted(truth, est, {j for _, j in pairs})}


def window_row(st, cluster, key, group, kind, truth, notes, reps=None, timing=None):
    """(Pure.) A window's stored row: its set, cluster (the list, or the Guitar-TECHS file), key, group ("lists", "P1",
    "P2", "goat"), kind, and per arm the figures against the truth (none on GOAT: no usable truth) and the note
    counts. notes: {arm: notes}."""
    row = {"set": st, "cluster": cluster, "key": key, "group": group, "kind": kind,
           "notes": {a: len(n) for a, n in notes.items()}, "borrow": reps or {}, "timing": timing or {}}
    if truth is not None:
        row["figures"] = {a: window_figures(truth, n) for a, n in notes.items()}
        row["bends"] = {a: bend_figures(truth, n, notes["tx-bp"]) for a, n in notes.items()}
    else:
        row["bends"] = {a: bend_figures(None, n, notes["tx-bp"]) for a, n in notes.items()}
    return row


def pooled(figs):
    """(Pure.) Figures pooled over windows: precision, recall, F, note-end F, chord-note recall, the re-struck
    recall, the extras."""
    s = {k: sum(f[k] for f in figs) for k in ("matched", "ref", "est", "end_matched", "chord_notes", "chord_found",
                                              "restruck_notes", "restruck_found")}
    d = s["ref"] + s["est"]
    ex = {k: sum(f["extras"][k] for f in figs) for k in ("harmonic", "re-find", "other")}
    return {**s, "windows": len(figs), "precision": s["matched"] / s["est"] if s["est"] else None,
            "recall": s["matched"] / s["ref"] if s["ref"] else None, "f": 2 * s["matched"] / d if d else None,
            "end_f": 2 * s["end_matched"] / d if d else None,
            "chord_recall": s["chord_found"] / s["chord_notes"] if s["chord_notes"] else None,
            "restruck_recall": s["restruck_found"] / s["restruck_notes"] if s["restruck_notes"] else None,
            "extras": ex}


def paired_differences(row, arm, fields=FIELDS):
    """(Pure.) One window's differences against tx-bp, per field (None where either side is None)."""
    a, b = row["figures"].get(arm), row["figures"].get("tx-bp")
    if a is None or b is None:
        return {f: None for f in fields}
    return {f: (a[f] - b[f]) if a[f] is not None and b[f] is not None else None for f in fields}


def in_group(row, group):
    """(Pure.) A row's membership of a reported group: a set ("lists", "real"), a player ("P1"), or "P1|chords"."""
    if group in ("lists", "real", "goat"):
        return row["set"] == group
    if "|" in group:
        pl, kind = group.split("|", 1)
        return row["group"] == pl and row["kind"] == kind
    return row["group"] == group


def report_groups(rows):
    """(Pure.) The sets and every player and player|kind group the rows hold, in a fixed order."""
    out = [s for s in ("lists", "real") if any(r["set"] == s for r in rows)]
    pk = sorted({(r["group"], r["kind"]) for r in rows if r["set"] == "real"})
    out += sorted({p for p, _ in pk}) + [f"{p}|{k}" for p, k in pk]
    return out


def set_summary(rows, group, arms=ALL_ARMS):
    """(Pure.) A group's numbers: per arm its pooled figures and, against tx-bp, the paired per-window differences as
    the mean over clusters of each cluster's mean with a 90% t interval (`note_versions.set_numbers`)."""
    rs = [r for r in rows if "figures" in r and in_group(r, group)]
    out = {"windows": len(rs), "clusters": len({r["cluster"] for r in rs}), "pooled": {}, "diff": {}}
    for a in arms:
        figs = [r["figures"][a] for r in rs if a in r["figures"]]
        if not figs:
            continue
        out["pooled"][a] = pooled(figs)
        if a != "tx-bp":
            d = [(r["cluster"], paired_differences(r, a)) for r in rs if a in r["figures"]]
            out["diff"][a] = {f: NV.set_numbers(d, f) for f in FIELDS}
    return out


# --- the readings (pure; plan section 4) --------------------------------------------------------------------------------

def clear_above(iv):
    return bool(iv) and iv.get("lo90") is not None and iv["lo90"] > 0


def clear_below(iv):
    return bool(iv) and iv.get("hi90") is not None and iv["hi90"] < 0


def decided_worse(iv):
    """(Pure.) A difference against tx-bp (higher is better) clear of zero below."""
    return clear_below(iv)


def precision_raised(iv):
    """(Pure.) The paired precision difference against tx-bp is clear of zero above."""
    return clear_above(iv)


def precision_not_better(iv):
    """(Pure.) The screen's decided negative: the precision difference's mean, or its interval's upper end, at or
    below zero."""
    if not iv or iv.get("mean") is None:
        return False
    return iv["mean"] <= 0 or (iv.get("hi90") is not None and iv["hi90"] <= 0)


def f_not_worse(iv):
    """(Pure.) The paired note-F difference against tx-bp is not clear of zero below (a direction, not a bar)."""
    return not decided_worse(iv)


def recall_held(arm, bp, guard=RECALL_GUARD, checks=None, checks_bp=None, slack=CHECK_SLACK):
    """(Pure.) "No loss the checks can see": pooled recall and chord-note recall each at most `guard` under tx-bp's
    (no chord notes: holds); with the 27 windows' check counts ({check: windows passing}), each guarded check passes on
    at most `slack` windows fewer than tx-bp."""
    for k in ("recall", "chord_recall"):
        a, b = (arm or {}).get(k), (bp or {}).get(k)
        if b is None:
            continue
        if a is None or a < b - guard:
            return False
    if checks is not None:
        for c in GUARDED_CHECKS:
            if (checks.get(c) or 0) < (checks_bp or {}).get(c, 0) - slack:
                return False
    return True


def ends_better(lists_iv, real_iv=None):
    """(Pure.) Note-end F clear of zero above tx-bp on the lists and, where the real DIs are read, not decided worse
    there."""
    return clear_above(lists_iv) and not decided_worse(real_iv)


def arm_reading(summaries, arm, checks=None):
    """(Pure.) One arm's reading on the deciding sets. summaries: {set: set_summary}; checks: {arm: {check: windows
    passing}} on the 27 windows (stage b) or None. -> {set: {precision, f, end_f, recall_held, ...}, ends_better}."""
    out = {}
    for st, s in summaries.items():
        d = (s.get("diff") or {}).get(arm) or {}
        ck = (checks or {}).get(arm) if st == "real" and checks is not None else None
        held = recall_held((s.get("pooled") or {}).get(arm), (s.get("pooled") or {}).get("tx-bp"),
                           checks=ck, checks_bp=(checks or {}).get("tx-bp") if ck is not None else None)
        out[st] = {"precision": d.get("precision"), "f": d.get("f"), "end_f": d.get("end_f"),
                   "recall": d.get("recall"), "chord_recall": d.get("chord_recall"),
                   "precision_raised": precision_raised(d.get("precision")),
                   "precision_not_better": precision_not_better(d.get("precision")),
                   "f_not_worse": f_not_worse(d.get("f")), "recall_held": held}
    out["ends_better"] = ends_better((out.get("lists") or {}).get("end_f"), (out.get("real") or {}).get("end_f"))
    return out


def arm_wins(reading, sets=SETS):
    """(Pure.) Precision raised, recall held and F not decided worse, on every deciding set."""
    return all(s in reading and reading[s]["precision_raised"] and reading[s]["recall_held"]
               and reading[s]["f_not_worse"] for s in sets)


def veto_holds(reading, sets=SETS):
    """(Pure.) `veto-holds`: the veto raises precision, holds recall and its F is not decided worse, on both sets. A
    flag: it never sets the code."""
    return arm_wins(reading, sets)


def lists_screen(readings):
    """(Pure.) Stage a's result: `TXR-none` only when, on the lists, both tx-vote and tx-ms read their precision
    difference decided not better (mean or upper end at or below zero) and neither's ends are better (note-end F clear
    of zero above); anything else, an undecided screen included, is `lists-go`. readings: {arm: arm_reading}."""
    ok = all(readings[a]["lists"]["precision_not_better"] and not clear_above(readings[a]["lists"]["end_f"])
             for a in ("tx-vote", "tx-ms"))
    return "TXR-none" if ok else "lists-go"


def txr_code(readings):
    """(Pure.) Stage b's code, the first that holds (every condition on the lists and on the real DIs):
    TXR-vote (tx-vote raises precision, holds recall, F not decided worse); TXR-ms (tx-ms does and the vote does not);
    TXR-ends (neither, but tx-ms's ends are better); TXR-undecided (the rest). -> {code, flags}."""
    if arm_wins(readings["tx-vote"]):
        code = "TXR-vote"
    elif arm_wins(readings["tx-ms"]):
        code = "TXR-ms"
    elif readings["tx-ms"]["ends_better"]:
        code = "TXR-ends"
    else:
        code = "TXR-undecided"
    flags = {FLAG_VETO: veto_holds(readings["tx-veto"]) if "tx-veto" in readings else False}
    if code in ("TXR-vote", "TXR-ms"):
        flags["ends_better"] = readings["tx-vote" if code == "TXR-vote" else "tx-ms"]["ends_better"]
    return {"code": code, "flags": flags}


def recommendation(code, flags=None, unpaired_share=None):
    """(Pure.) The declared recommendation for a screen result or a code. -> {text, veto_candidate, lookup_first}."""
    flags = flags or {}
    text = RECOMMENDATION[code]
    veto = code == "TXR-undecided" and bool(flags.get(FLAG_VETO))
    lookup = code == "TXR-ms" and unpaired_share is not None and unpaired_share > UNPAIRED_LOOKUP
    if veto:
        text += "; " + VETO_CANDIDATE
    if lookup:
        text += "; " + LOOKUP_FIRST
    return {"text": text, "veto_candidate": veto, "lookup_first": lookup}


def summarise_screen(rows):
    """(Pure.) Stage a from the ten lists' rows, once: per arm the lists' numbers, the readings, the screen's result
    and its recommendation."""
    s = {"lists": set_summary(rows, "lists")}
    readings = {a: arm_reading(s, a) for a in ALL_ARMS if a != "tx-bp" and a in s["lists"]["diff"]}
    screen = lists_screen(readings)
    return {"numbers": s, "readings": readings, "screen": screen, "recommendation": recommendation(screen)}


def check_counts(goat_rows, ring=DECIDING_RING):
    """(Pure.) Per arm, how many of the 27 windows pass each check (note checks and, on the deciding ring, the audio
    checks). goat_rows: [{"checks": {arm: {ring or "notes": {check: pass}}}}]."""
    out = {}
    for r in goat_rows:
        for a, by in (r.get("checks") or {}).items():
            c = out.setdefault(a, {})
            for src in ("notes", ring):
                for k, v in (by.get(src) or {}).items():
                    c[k] = c.get(k, 0) + (v is True)
    return out


def summarise_read(list_rows, real_rows, goat_rows):
    """(Pure.) Stage b's read, once: the lists' rows (from the screen), the real DIs' rows and the 27 windows' check
    rows -> every group's numbers, the readings (recall held includes the checks' counts on the real set), the code,
    its flags and recommendation."""
    rows = list(list_rows) + list(real_rows)
    numbers = {g: set_summary(rows, g) for g in report_groups(rows)}
    checks = check_counts(goat_rows)
    readings = {a: arm_reading({s: numbers[s] for s in SETS if s in numbers}, a, checks)
                for a in ("tx-ms", "tx-vote", "tx-veto", "tx-ms-free") if a in numbers.get("lists", {}).get("diff", {})}
    code = txr_code(readings)
    un = unpaired_share(rows, "tx-ms")
    return {"numbers": numbers, "checks": checks, "readings": readings, **code,
            "unpaired_share": un, "recommendation": recommendation(code["code"], code["flags"], un)}


def unpaired_share(rows, arm="tx-ms"):
    """(Pure.) The share of an arm's notes with no Basic Pitch partner, pooled over rows."""
    a = sum((r.get("borrow") or {}).get(arm, {}).get("unpaired", 0) for r in rows)
    n = sum((r.get("borrow") or {}).get(arm, {}).get("notes", 0) for r in rows)
    return a / n if n else None


# --- the bridge (pure; plan section 6) ----------------------------------------------------------------------------------

BRIDGE_TABLE = (    # ("Measure first" codes, loudness adopted, this track's codes, (built, stored), reading)
    (("NV-loud", "NV-undecided"), True, ("TXR-vote", "TXR-ms"), ("bv-loud", "nv-loud"),
     "the winner adds something only if this is clear of zero below; otherwise loudness alone stays"),
    (("NV-short",), None, ("TXR-vote", "TXR-ms"), ("bv-asis", "nv-hand"),
     "read as 'Measure first' reads G against its stored C: near makes the winner the candidate clean-up"),
    (("NV-none", "NV-undecided"), False, ("TXR-vote", "TXR-ms"), ("bv-asis", "nv-asis"),
     "reported only: extras cost nothing shown, so this is never a reason to change the route"),
    (None, None, ("TXR-ends",), ("bv-ends", "nv-asis"), "better ends count only if this is clear of zero below"),
)
BRIDGE_CODES = ("TXR-vote", "TXR-ms", "TXR-ends")   # a code with a bridge


def bridge_difference(nv_code, loud_adopted, txr):
    """(Pure.) Section 6's table: the one deciding difference for "Measure first"'s code (`nv_code`, with whether a
    loudness was adopted) and this track's code. -> {built, stored, reading} or None (no bridge)."""
    if txr not in BRIDGE_CODES:
        return None
    if nv_code == "NV-loud" and not loud_adopted:
        raise ValueError("NV-loud always adopts a loudness")
    for nvs, loud, txrs, (b, s), reading in BRIDGE_TABLE:
        if txr not in txrs:
            continue
        if nvs is not None and nv_code not in nvs:
            continue
        if loud is not None and nv_code == "NV-undecided" and bool(loud_adopted) != loud:
            continue
        return {"built": b, "stored": s, "reading": reading}
    raise ValueError(f"no bridge row for {nv_code} and {txr}")


def bridge_versions(txr, loud_adopted):
    """(Pure.) The versions the bridge builds: only the winner's (bv-asis, and bv-loud when a loudness was adopted),
    or bv-ends for TXR-ends."""
    if txr == "TXR-ends":
        return ("bv-ends",)
    if txr in ("TXR-vote", "TXR-ms"):
        return ("bv-asis", "bv-loud") if loud_adopted else ("bv-asis",)
    return ()


def bridge_reading(diff, iv, stored_c=None):
    """(Pure.) The deciding difference read by its row: bv-loud - nv-loud and bv-ends - nv-asis count only when clear
    of zero below; bv-asis - nv-hand by `note_versions.set_reading` against the stored C (nv-asis - nv-hand); bv-asis -
    nv-asis is reported only."""
    b, s = diff["built"], diff["stored"]
    if (b, s) == ("bv-loud", "nv-loud"):
        return "the winner adds" if clear_below(iv) else "loudness alone stays"
    if (b, s) == ("bv-ends", "nv-asis"):
        return "better ends count" if clear_below(iv) else "better ends do not count"
    if (b, s) == ("bv-asis", "nv-hand"):
        r = NV.set_reading(stored_c, iv)
        return "the winner is the candidate clean-up" if r == "near" else r
    return "reported only"


def bridge_body(vwindows, built, nv_code, loud_adopted, txr):
    """(Pure.) The bridge's read from versions.json's stored windows ([{set, cluster, key, d: {ring: {version: dB}}}])
    and the built versions' distances ({key: {ring: {bv: dB}}}): per ring and set every built version less every
    stored version there is, with 90% cluster intervals, and on the deciding ring the declared difference and its
    reading per set (GOAT: no nv-hand)."""
    diff = bridge_difference(nv_code, loud_adopted, txr)
    out = {"difference": diff, "numbers": {}, "readings": {}}
    for ring in (DECIDING_RING, BESIDE_RING):
        out["numbers"][ring] = {}
        for st in ("lists", "real", "goat"):
            rows = []
            for w in vwindows:
                if w["set"] != st or w["key"] not in built or ring not in w["d"]:
                    continue
                d, b = w["d"][ring], built[w["key"]].get(ring) or {}
                rows.append((w["cluster"], {f"{bv}-{nv}": b[bv] - d[nv] for bv in b for nv in ("nv-hand", "nv-asis",
                                                                                                 "nv-loud") if nv in d},
                             {"C": d["nv-asis"] - d["nv-hand"] if "nv-hand" in d and "nv-asis" in d else None}))
            fields = sorted({k for _, r, _ in rows for k in r})
            nums = {f: NV.set_numbers([(c, r) for c, r, _ in rows], f) for f in fields}
            nums["C"] = NV.set_numbers([(c, x) for c, _, x in rows], "C")
            out["numbers"][ring][st] = nums
    if diff:
        for st in ("lists", "real", "goat"):
            nums = out["numbers"][DECIDING_RING][st]
            iv = nums.get(f"{diff['built']}-{diff['stored']}")
            out["readings"][st] = None if iv is None else bridge_reading(diff, iv, nums.get("C"))
    return out


# --- the install, the gate's rules and the records (pure) ---------------------------------------------------------------

def lock_refusal(text):
    """(Pure.) Why a lock does not hold the declared pins, or None: muscriptor at its declared version and sha256,
    every requirement named, nothing from the server or beat tracker, every line hashed, no package twice."""
    pins = {}
    for ln in text.splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        if "--hash=sha256:" not in ln:
            return f"an unhashed line: {ln[:60]}"
        spec, h = ln.split("--hash=sha256:", 1)
        n, v = spec.strip().split("==")
        n = n.lower().replace("_", "-")
        if n in pins:
            return f"{n} is in the lock twice"
        pins[n] = (v, h.split()[0])
    if pins.get(PACKAGE[0]) != (PACKAGE[1], PACKAGE[2]):
        return f"{PACKAGE[0]} is not {PACKAGE[1]} at its declared sha256"
    for r in REQUIREMENTS:
        name = r.split(">=")[0].split("==")[0].lower().replace("_", "-")
        if name not in pins:
            return f"{name} is not in the lock"
    for n in NOT_NEEDED:
        if n in pins:
            return f"{n} is in the lock (not needed: the server and beat-tracking parts)"
    return None


def weights_refusal(size, model_bytes, model_sha, config_bytes):
    """(Pure.) Why the user's weights folder is not the declared checkpoint, or None."""
    w = WEIGHTS.get(size)
    if w is None:
        return f"{size}: not a declared size"
    if model_bytes != w["bytes"]:
        return f"model.safetensors is {model_bytes} bytes, not {w['bytes']}"
    if model_sha != w["sha256"]:
        return "model.safetensors is not the declared sha256"
    if config_bytes != w["config_bytes"]:
        return f"config.json is {config_bytes} bytes, not {w['config_bytes']}"
    return None


def private_keys(obj, path=""):
    """(Pure.) Every key, anywhere in a record, that names an account, an email or a token. -> [paths]."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            if any(w in str(k).lower() for w in PRIVATE_WORDS):
                out.append(p)
            out += private_keys(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += private_keys(v, f"{path}[{i}]")
    return out


def install_manifest(interp, python, lock_sha, resolve_sha, weights, files, free_gb, made):
    """(Pure.) The install's record: every file's name, size and sha256; the lock's and resolve.json's sha256; the
    weights (size, repo, revision, sha256, bytes, config.json's sha256 and bytes); the package; the licences; the
    approval as a date and a ledger key only; Python; the free disk. No account name, email or token field exists."""
    man = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "made": made, "interpreter": interp, "python": python,
           "package": {"name": PACKAGE[0], "version": PACKAGE[1], "sha256": PACKAGE[2], "bytes": PACKAGE[3]},
           "requirements": list(REQUIREMENTS), "lock_sha256": lock_sha, "resolve_sha256": resolve_sha,
           "weights": weights, "files": files, "installed_bytes": sum(f["size"] for f in files),
           "licences": dict(LICENCES), "approval": dict(APPROVAL), "free_gb_after": free_gb}
    bad = private_keys(man)
    if bad:
        raise SystemExit(f"the install record names {bad}: no account name, email or token, ever")
    return man


def install_record_refusal(rec, man, gate_sha, listing_sha):
    """(Pure.) Why main's `phase_tx_install` does not hold this install's facts, or None: the lock's and weights'
    sha256, the gate file's sha256 and the list notes' listing sha256."""
    if not isinstance(rec, dict):
        return f"main's {PHASE_INSTALL} names no install"
    if rec.get("lock_sha256") != man["lock_sha256"] or rec.get("weights_sha256") != man["weights"]["sha256"]:
        return f"main's {PHASE_INSTALL} names another lock or weights"
    if rec.get("gate_sha256") != gate_sha:
        return f"the gate file is not main's {PHASE_INSTALL} gate_sha256"
    if rec.get("list_notes_listing_sha256") != listing_sha:
        return f"the list note files are not main's {PHASE_INSTALL} listing"
    return None


def device_choice(repeat):
    """(Pure.) The device rule: MPS (float16) if its three runs repeat on every window; else the CPU (float32) if it
    does; else None (stop). repeat: {device: {window: bool}}."""
    for d in ("mps", "cpu"):
        r = repeat.get(d) or {}
        if r and all(r.values()):
            return d
    return None


def projection_s(seconds, repeat, windows=STAGE_B_WINDOWS):
    """(Pure.) Stage b's projected seconds on the faster repeatable device (seconds per window times 265), or None."""
    ok = [seconds[d] for d in seconds if (repeat.get(d) or {}) and all(repeat[d].values())]
    return min(ok) * windows if ok else None


def size_choice(projected, limit=SIZE_SWITCH_S):
    """(Pure.) The size rule: over two hours projected switches every MuScriptor arm (tx-ms-free included) to small,
    decided before any list is transcribed."""
    return "small" if projected is not None and projected > limit else "medium"


def gate_list_refusal(stored, recomputed):
    """(Pure.) The screen's input check: Basic Pitch's list figures recomputed from the gate's stored events (the
    clean-up, then `match_notes`, no offset, no snap) must equal install-gate.json's matched, ref and est per list."""
    if sorted(stored) != sorted(recomputed):
        return f"the lists differ: {sorted(set(stored) ^ set(recomputed))}"
    for nm in sorted(stored):
        a, b = stored[nm], recomputed[nm]
        if (a["matched"], a["ref"], a["est"]) != (b["matched"], b["ref"], b["est"]):
            return f"{nm}: tx-bp {b['matched']}/{b['ref']}/{b['est']} is not the gate's {a['matched']}/{a['ref']}/{a['est']}"
    return None


def truth_report_refusal(rows, figures):
    """(Pure.) `read`'s check: tx-bp's per-window matched, ref and est equal the truth report's. rows: the report's
    windows; figures: {key: tx-bp's window_figures}."""
    for r in rows:
        f = figures.get(r["key"])
        if f is None:
            return f"{r['key']}: not read"
        if (f["matched"], f["ref"], f["est"]) != (r["matched"], r["ref"], r["est"]):
            return f"{r['key']}: tx-bp {f['matched']}/{f['ref']}/{f['est']} is not the truth report's"
    if len(figures) != len(rows):
        return "the read holds windows the truth report does not"
    return None


def lists_go_refusal(rec):
    """(Pure.) Why stage b may not run on main's `phase_tx_lists`, or None: the screen read lists-go."""
    if not isinstance(rec, dict) or "screen" not in rec:
        return f"main's {PHASE_LISTS} holds no screen result"
    if rec["screen"] != "lists-go":
        return f"the list screen read {rec['screen']}: the track stopped, stage b does not run"
    return None


def read_bridge_refusal(rec):
    """(Pure.) Why the bridge may not run on main's `phase_tx_read`, or None: a code with a bridge."""
    if not isinstance(rec, dict) or "code" not in rec:
        return f"main's {PHASE_READ} holds no code"
    if rec["code"] not in BRIDGE_CODES:
        return f"the read is {rec['code']}: no bridge"
    return None


def note_refusal(rec, kind, install):
    """(Pure.) Why a MuScriptor note file may not be used, or None: the install's weights and lock, its kind's
    declared settings, the gate's device, a declared source."""
    if rec.get("weights_sha256") != install["weights_sha256"] or rec.get("lock_sha256") != install["lock_sha256"]:
        return "the note file comes from another install (weights or lock)"
    if rec.get("settings") != NOTE_KINDS[kind]:
        return f"the note file ran with other settings than {kind}'s"
    if rec.get("device") != install["device"]:
        return "the note file ran on another device than the gate's"
    return TR.source_refusal(rec.get("source"))


# --- the guards ---------------------------------------------------------------------------------------------------------

CODE_FILES = T.CODE_FILES + ("learn/note_tx.py", "learn/tx_run.py")
KEY_PREFIX = "phase_tx"


def tx_entries(text):
    """(Pure.) {ledger id: entry} for this track's entry and the note rebuild's, from a ledger file's text."""
    d = json.loads(text)
    return {t["test_id"]: t for t in d.get("tests", []) if t.get("test_id") in (LEDGER_ID, NR_ID)}


def tx_keys_refusal(local, main):
    """(Pure.) Why this checkout's `note-transcriber` `phase_tx*` keys are not main's, or None."""
    a = T.guarded_keys(local.get(LEDGER_ID), (KEY_PREFIX,))
    b = T.guarded_keys(main.get(LEDGER_ID), (KEY_PREFIX,))
    if a != b:
        diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        return f"this checkout's {LEDGER_ID} {', '.join(diff)} differ from main's: pull main (run from merged code)"
    return None


def tx_on_main():
    """main's two entries (origin/main after a fetch) and whether this checkout runs main's code: CODE_FILES equal
    main's and the `phase_tx*` keys equal main's. -> ({ledger id: main's entry}, refusal or None)."""
    import subprocess

    def git(*a):
        return subprocess.run(["git", "-C", str(NR.REPO), *a], capture_output=True, text=True)
    git("fetch", "-q", "origin", "main")
    led = git("show", "origin/main:docs/dev-test-ledger.json")
    if led.returncode:
        return {}, f"main's ledger is not readable: {led.stderr.strip()}"
    m = tx_entries(led.stdout)
    for f in CODE_FILES:
        if git("diff", "--quiet", "origin/main", "--", f).returncode:
            return m, f"this checkout's {f} differs from main's: run from merged code"
    return m, tx_keys_refusal(tx_entries((NR.REPO / "docs" / "dev-test-ledger.json").read_text()), m)


def require_tx(*phases, nr=()):
    """Refuse unless this checkout runs main's code and main's `note-transcriber` entry holds `phase_tx` and `phases`
    (and its `note-rebuild` entry `nr`). -> {ledger id: main's entry}."""
    m, why = tx_on_main()
    if why:
        raise SystemExit(why)
    for k in (PHASE,) + tuple(phases):
        if k not in (m.get(LEDGER_ID) or {}):
            raise SystemExit(f"main's {LEDGER_ID} entry has no {k}: merge it before running")
    for k in nr:
        if k not in (m.get(NR_ID) or {}):
            raise SystemExit(f"main's {NR_ID} entry has no {k}: merge it before running")
    return m


never_overwrite = T.never_overwrite


# --- paths --------------------------------------------------------------------------------------------------------------

def note_path(kind, key):
    if kind not in NOTE_KINDS:
        raise ValueError(kind)
    return OUT / "notes" / kind / f"{key.replace('/', '__')}.json"


def gate_path(size="medium"):
    return OUT / f"gate-{size}.json"


def gate_work(size="medium"):
    return OUT / "work" / f"gate-{size}"


def lists_path():
    return OUT / "lists.json"


def transcribe_path():
    return OUT / "transcribe.json"


def read_path():
    return OUT / "read.json"


def bridge_path():
    return OUT / "bridge.json"


def notes_listing(kinds):
    """The note files of `kinds` as [(relative path, sha256)] and their listing sha256 (`note_transcribe.listing_sha`)."""
    rows = []
    for k in kinds:
        d = OUT / "notes" / k
        rows += [(str(p.relative_to(OUT / "notes")), NR.file_sha(p)) for p in sorted(d.glob("*.json"))]
    return rows, T.listing_sha(rows)


# --- audio in and the runner (numpy) ------------------------------------------------------------------------------------

def ms_input(x48):
    """MuScriptor's input from 48 kHz audio: mono, `resample_poly(x, 1, 3)` to 16 kHz, peak at -1 dBFS, float32."""
    import numpy as np
    from scipy.signal import resample_poly

    x = np.asarray(x48, np.float64)
    if x.ndim == 2:
        x = x.mean(axis=1)
    y = resample_poly(x, MS_UP, MS_DOWN)
    pk = float(np.abs(y).max()) if len(y) else 0.0
    if pk > 0:
        y = y * (10 ** (MS_PEAK_DBFS / 20) / pk)
    return y.astype(np.float32)


def load_manifest():
    if not MANIFEST.exists():
        raise SystemExit(f"{MANIFEST}: no install (run `install` first)")
    return json.loads(MANIFEST.read_text())


def weights_file(size, man=None):
    """The user's weights of `size`, refused unless they are the declared checkpoint (medium: the install's)."""
    d = WEIGHTS_DIR / size
    p, c = d / "model.safetensors", d / "config.json"
    if not p.exists() or not c.exists():
        raise SystemExit(f"{d}: model.safetensors and config.json missing (the user's browser download)")
    if man is not None and size == "medium" and man["weights"]["sha256"] != WEIGHTS["medium"]["sha256"]:
        raise SystemExit("the install names other weights")
    why = weights_refusal(size, p.stat().st_size, NR.file_sha(p), c.stat().st_size)
    if why:
        raise SystemExit(f"{d}: {why}")
    return p


def run_ms(jobs, workdir, weights, device, settings, listing=None, dev_items=None):
    """MuScriptor on [(48 kHz audio, source)] in one tx_run process (the venv's interpreter, `-I`, HF_HUB_OFFLINE=1,
    the weights passed by path). Every source passes `declared_input` before anything is written; the input manifest
    lists each written input's sha256 with its source. -> [tx_run's output record] in order."""
    for _, src in jobs:                                   # the guard first: nothing is written for a refused input
        declared_input(src, listing, dev_items)
    import subprocess

    import soundfile as sf

    workdir = pathlib.Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    args, rows = [], []
    for i, (x, src) in enumerate(jobs):
        tag = src.split(":", 1)[0]
        w, o = workdir / f"{i:03d}-{tag}.wav", workdir / f"{i:03d}-{tag}.json"
        sf.write(str(w), ms_input(x), MS_SR, subtype="FLOAT")
        rows.append((src, NR.file_sha(w)))
        args += [str(w), str(o)]
    man = workdir / f"inputs-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}.json"
    never_overwrite(man)
    man.write_text(json.dumps(manifest_doc(rows), indent=1))
    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    r = subprocess.run([str(MS_PYTHON), "-I", str(NR.REPO / "learn" / "tx_run.py"), "--weights", str(weights),
                        "--device", device, "--settings", json.dumps(settings), "--inputs", str(man), *args],
                       capture_output=True, text=True, env=env)
    if r.returncode:
        raise SystemExit(f"tx_run failed: {r.stderr.strip()[-400:]}")
    out = []
    for (src, sha), o in zip(rows, args[1::2]):
        rec = json.loads(pathlib.Path(o).read_text())
        if rec["settings"] != settings or rec["device"] != device or rec["input_sha256"] != sha or rec["source"] != src:
            raise SystemExit("tx_run ran other settings, another device or another input")
        out.append(rec)
    return out


def ms_note_record(rec, pre_s, man, kind):
    """One MuScriptor note file's body: the install's lock and weights, the settings, the device and dtype, the input's
    sha256 and source, pre_s, the versions, the notes and counts."""
    return {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "kind": kind, "lock_sha256": man["lock_sha256"],
            "weights_sha256": rec["weights_sha256"], "weights_size": rec["weights_size"], "settings": rec["settings"],
            "device": rec["device"], "dtype": rec["dtype"], "input_sha256": rec["input_sha256"],
            "source": rec["source"], "pre_s": pre_s,
            "versions": {k: rec.get(k) for k in ("muscriptor", "torch", "python", "threads")},
            "counts": rec["counts"], "notes": rec["notes"]}


def load_ms(kind, key, install):
    """A MuScriptor note file, refused unless it names the install's weights and lock, its kind's settings and the
    gate's device."""
    p = note_path(kind, key)
    if not p.exists():
        raise SystemExit(f"{p}: not transcribed")
    rec = json.loads(p.read_text())
    why = note_refusal(rec, kind, install)
    if why:
        raise SystemExit(f"{p.name}: {why}")
    return rec


def require_install(m):
    """The install's manifest and the gate's record, refused unless main's `phase_tx_install` names them (the lock,
    the weights, the gate file and the list notes' listing). -> {lock_sha256, weights_sha256, device, size, gate}."""
    man = load_manifest()
    rec = (m.get(LEDGER_ID) or {}).get(PHASE_INSTALL)
    size = (rec or {}).get("size", "medium")
    gp = gate_path(size)
    if not gp.exists():
        raise SystemExit(f"{gp.name} missing: run `gate` first")
    _, listing = notes_listing(("list", "list-free"))
    why = install_record_refusal(rec, man, NR.file_sha(gp), listing)
    if why:
        raise SystemExit(why)
    gate = json.loads(gp.read_text())["body"]
    if not gate.get("lists_written") or gate.get("device") != rec.get("device"):
        raise SystemExit("the gate wrote no list notes, or on another device than main's record")
    return {"lock_sha256": man["lock_sha256"], "weights_sha256": gate["weights_sha256"], "device": gate["device"],
            "size": gate["size"], "gate": gate, "manifest": man}


def busy_refusal():
    """Why the gate may not run now, or None: another MPS user or a render is running."""
    from learn import ks_extend as X
    from learn import local_objective as LO
    from learn import real_mix_test as M

    ps = X._ps()
    own = {os.getpid(), os.getppid()}
    mps, rend = M.mps_users(ps, own), LO.others_rendering(ps, own)
    if mps or rend:
        return f"another MPS user {mps} or a render {rend} is running: one MPS job at a time"
    return None


# --- the commands -------------------------------------------------------------------------------------------------------

def cmd_install(args):
    """Phase 2 (a declared download): the venv from pyenv's 3.14.6 (or `--interpreter`, Homebrew's 3.13, the declared
    fallback on the user's yes; no other version), the lock made by `pip install --dry-run --ignore-installed
    --only-binary :all: --report` over REQUIREMENTS with the muscriptor wheel added, then `pip install
    --require-hashes --only-binary :all: --no-deps -r requirements.lock`; the user's medium weights and config.json
    checked; an import test; the manifest. Refuses without `phase_tx` and `phase_tx_go` on main, and under
    INSTALL_MIN_GB free."""
    import shutil
    import subprocess

    require_tx(PHASE_GO)
    never_overwrite(TOOLS)
    from learn import pretrain_set as PS

    if PS.free_gb() < INSTALL_MIN_GB:
        raise SystemExit(f"DISK GUARD: under {INSTALL_MIN_GB:.0f} GB free; the install refuses")
    wp = weights_file("medium")
    cp = wp.parent / "config.json"

    def run(*a):
        r = subprocess.run([str(x) for x in a], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"{' '.join(map(str, a))[:120]}: {r.stderr.strip()[-600:]}")
        return r.stdout
    interp = getattr(args, "interpreter", None) or INTERPRETER
    minor = run(interp, "-c", "import sys; print('%d.%d' % sys.version_info[:2])").strip()
    if minor not in PYTHONS:
        raise SystemExit(f"{interp} is Python {minor}: only {PYTHONS[0]} (declared) or {PYTHONS[1]} (the fallback)")
    run(interp, "-m", "venv", TOOLS)
    pip = TOOLS / "bin" / "pip"
    run(pip, "install", "--dry-run", "--ignore-installed", "--only-binary", ":all:", "--report", RESOLVE,
        *REQUIREMENTS)
    text = T.lock_lines(json.loads(RESOLVE.read_text()), [PACKAGE[:3]])
    why = lock_refusal(text)
    if why:
        raise SystemExit(f"the lock: {why}")
    LOCK.write_text(text)
    run(pip, "install", "--require-hashes", "--only-binary", ":all:", "--no-deps", "-r", LOCK)
    run(MS_PYTHON, "-I", "-c", "from muscriptor import TranscriptionModel")
    files = [{"path": str(p.relative_to(TOOLS)), "size": p.stat().st_size, "sha256": NR.file_sha(p)}
             for p in sorted(TOOLS.rglob("*")) if p.is_file() and not p.is_symlink() and "__pycache__" not in p.parts]
    weights = {"size": "medium", "repo": WEIGHTS["medium"]["repo"], "revision": WEIGHTS["medium"]["revision"],
               "path": str(wp), "sha256": NR.file_sha(wp), "bytes": wp.stat().st_size,
               "config_sha256": NR.file_sha(cp), "config_bytes": cp.stat().st_size}
    man = install_manifest(interp, run(MS_PYTHON, "-c", "import sys; print(sys.version)").strip(), NR.file_sha(LOCK),
                           NR.file_sha(RESOLVE), weights, files, PS.free_gb(), time.strftime("%Y-%m-%d %H:%M:%S"))
    man["disk_total_gb"] = shutil.disk_usage(str(TOOLS)).total / 1e9
    NR.write_once(MANIFEST, man)
    print(f"INSTALL DONE: lock {man['lock_sha256']}, weights {weights['sha256']}, config.json "
          f"{weights['config_sha256']}, {man['installed_bytes'] / 1e6:.0f} MB, {man['free_gb_after']:.1f} GB free")


def repeat_table(one, fresh, n):
    """(Pure.) Per window, whether its three runs (two in one process, one fresh) gave identical notes.
    one: 2n records (each window twice, in order); fresh: n records."""
    return [T.repeat_identical([one[2 * i]["notes"], one[2 * i + 1]["notes"], fresh[i]["notes"]]) for i in range(n)]


def cmd_gate(args):
    """Phase 2 (zero renders): per device, REPEAT_WINDOWS development windows, three runs each (two in one process, one
    fresh), identical notes; seconds per window; the device by `device_choice`; stage b's projection on the faster
    repeatable device; the size by `size_choice`. If the size stays (medium, or small after a switch), the ten lists
    are transcribed with it (the guitar groups, and no mask for tx-ms-free), each note file written once, their
    listing sha256 printed. If the rule calls for small, it stops with no list notes written; after the user installs
    the small weights, `gate --size small` runs the repeat and speed tests again on small, then the lists. Refuses
    while another MPS user or a render runs. -> tx/gate-<size>.json (its sha256 goes into phase_tx_install)."""
    size = getattr(args, "size", None) or "medium"
    require_tx(PHASE_GO)
    man = load_manifest()
    if size == "small":
        prior = gate_path("medium")
        if not prior.exists() or json.loads(prior.read_text())["body"].get("size_rule") != "small":
            raise SystemExit("the small model runs only after the medium gate's size rule called for it")
    never_overwrite(gate_path(size))
    never_overwrite(gate_work(size))
    why = busy_refusal()
    if why:
        raise SystemExit(why)
    weights = weights_file(size, man)
    wsha = NR.file_sha(weights)
    excl, tn, z, _ = T._dev_context()
    dev = T.dev_windows(z, excl, tn["items"])
    items = [w["item"] for w in dev]
    wins = dev[:REPEAT_WINDOWS]
    ins = []
    for w in wins:
        _, inp, _ = T.window_audio(T.goat_audio(z, w["item"]), w["start_s"])
        ins.append((inp, f"goat-dev:{w['item']}"))
    work = gate_work(size)
    repeat, secs, dtypes = {}, {}, {}
    for d in TR.DEVICES:
        t0 = time.perf_counter()
        a = run_ms([j for j in ins for _ in (0, 1)], work / d / "one-process", weights, d, MS_SETTINGS,
                   dev_items=items)
        secs[d] = (time.perf_counter() - t0) / (2 * len(ins))
        b = run_ms(ins, work / d / "fresh", weights, d, MS_SETTINGS, dev_items=items)
        repeat[d] = dict(zip([w["item"] for w in wins], repeat_table(a, b, len(wins))))
        dtypes[d] = a[0]["dtype"]
    device = device_choice(repeat)
    proj = projection_s(secs, repeat)
    rule = size_choice(proj) if size == "medium" else "small"
    body = {"size": size, "weights_sha256": wsha, "repeat": repeat, "seconds_per_window": secs, "dtype": dtypes,
            "device": device, "projection_s": proj, "size_rule": rule, "lists_written": False,
            "manifest_sha256": NR.file_sha(MANIFEST), "lock_sha256": man["lock_sha256"]}
    if device is not None and rule == size:
        bank = NR.Bank(NR.load_notes_doc(), excl=excl)
        names = sorted(T.KNOWN_NOTES)
        audio = [(T.known_audio(nm, bank), f"list:{nm}") for nm in names]
        for kind, st in (("list", MS_SETTINGS), ("list-free", MS_FREE_SETTINGS)):
            for nm in names:
                never_overwrite(note_path(kind, nm))
            recs = run_ms(audio, work / kind, weights, device, st, dev_items=items)
            for nm, r in zip(names, recs):
                NR.write_once(note_path(kind, nm), ms_note_record(r, 0.0, man, kind))
        rows, body["list_notes_listing_sha256"] = notes_listing(("list", "list-free"))
        body["list_note_files"] = len(rows)
        body["lists_written"] = True
    NR.write_once(gate_path(size), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}",
                                    "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    if device is None:
        msg = "STOP: the notes repeat on neither MPS nor the CPU (stop rule 2)"
    elif rule != size:
        msg = (f"STOP: projected {proj / 3600:.2f} h for stage b on the faster repeatable device; the size rule calls "
               f"for small (no list notes written): the user accepts and downloads muscriptor-small, then "
               f"`gate --size small`")
    else:
        msg = (f"PASS on {device} ({size}); projected {proj / 3600:.2f} h; list notes listing sha256 "
               f"{body['list_notes_listing_sha256']}")
    print(f"GATE {msg}; repeat {repeat}; {json.dumps({d: round(s, 2) for d, s in secs.items()})} s a window; "
          f"sha256 {NR.file_sha(gate_path(size))}")


def gate_known():
    """Basic Pitch's list events from the gate's stored files (redo/work/install-gate/known/), refused unless they
    come from the redo's install and settings. -> {list: events}."""
    pair = T.install_pair(T.load_manifest())
    out = {}
    for pp in sorted((T.gate_work_dir() / "known").glob("*.json")):
        ev = json.loads(pp.read_text())
        if ev.get("model_sha256") != pair[1] or ev.get("settings") != T.BP_SETTINGS:
            raise SystemExit(f"{pp.name}: the stored events come from another model or other settings")
        out[pp.stem.split("-", 1)[1]] = ev["events"]
    if sorted(out) != sorted(T.KNOWN_NOTES):
        raise SystemExit("the gate's stored list events are not the ten lists")
    return out


def gate_figures(known):
    """(Pure.) The gate's own list figures from its stored events: the clean-up, then `match_notes` (no offset, no
    snap). -> {list: {matched, ref, est, ...}}."""
    return {nm: T.match_notes([dict(n) for n in T.KNOWN_NOTES[nm]],
                              T.clean_transcribed(T.notes_from_events(ev))[0], T.KNOWN_ONSET_S)
            for nm, ev in known.items()}


def list_rows(known, ms, ms_free, dis, truths=None):
    """The lists' rows (numpy: the onset steps): Basic Pitch's stored events and MuScriptor's note files through
    `timed_notes` (pre_s 0, the list's own audio through `song_bank.measure`), every arm against the list's truth
    (`truths`, default `note_transcribe.KNOWN_NOTES`). known: {list: events}; ms, ms_free: {list: note file}; dis:
    {list: DI}, one per list read."""
    truths = T.KNOWN_NOTES if truths is None else truths
    rows = []
    for nm in sorted(dis):
        di = dis[nm]
        bp, rb = T.timed_notes({"events": known[nm], "pre_s": 0.0}, di)
        m, rm = T.timed_notes(ms_events(ms[nm]), di)
        f, rf = T.timed_notes(ms_events(ms_free[nm]), di)
        notes, reps = arm_notes(bp, m, f)
        rows.append(window_row("lists", nm, nm, "lists", None, [dict(n) for n in truths[nm]], notes, reps,
                               timing={"tx-bp": rb, "tx-ms": rm, "tx-ms-free": rf}))
    return rows


def cmd_lists(_args):
    """Phase 3a (zero renders), once: refuses without `phase_tx_install` on main. Loads Basic Pitch's list events from
    the gate's stored files; first recomputes the gate's own figures (the clean-up, then `match_notes`, no offset, no
    snap) and requires each list's matched, ref and est to equal install-gate.json's; then the deciding figures
    through `timed_notes`; the screen (`summarise_screen`). -> tx/lists.json (its sha256 and the screen go into
    phase_tx_lists)."""
    m = require_tx(PHASE_GO, PHASE_INSTALL)
    inst = require_install(m)
    never_overwrite(lists_path())
    known = gate_known()
    stored = json.loads(T.gate_path().read_text())["body"]["known"]
    why = gate_list_refusal(stored, gate_figures(known))
    if why:
        raise SystemExit(f"the input check: {why}")
    from learn import song_bank as SB

    bank = NR.Bank(NR.load_notes_doc(), excl=NR.load_exclusion())
    names = sorted(T.KNOWN_NOTES)
    dis = {nm: SB.measure(T.known_audio(nm, bank)) for nm in names}
    ms = {nm: load_ms("list", nm, inst) for nm in names}
    free = {nm: load_ms("list-free", nm, inst) for nm in names}
    rows = list_rows(known, ms, free, dis)
    body = {"rows": rows, **summarise_screen(rows), "input_check": "tx-bp equals install-gate.json on every list",
            "gate_sha256": NR.file_sha(gate_path(inst["size"])), "install_gate_sha256": NR.file_sha(T.gate_path()),
            "device": inst["device"], "size": inst["size"]}
    NR.write_once(lists_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}",
                                 "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    d = body["numbers"]["lists"]["diff"]
    print(f"LISTS {body['screen']}: precision tx-vote {d['tx-vote']['precision']}, tx-ms {d['tx-ms']['precision']}; "
          f"recommendation: {body['recommendation']['text']}; sha256 {NR.file_sha(lists_path())}")


def bp_note(kind, key, want_sha, pair):
    """A Basic Pitch note file of "Measure first"'s, loaded by its recorded sha256 (never re-run)."""
    p = T.note_path(kind, key)
    if not p.exists() or NR.file_sha(p) != want_sha:
        raise SystemExit(f"{p.name}: not the note file the truth report recorded")
    return T.load_note(kind, key, pair)


def stage_b_context(m):
    """The truth listing (main's `phase_nr_1_redo_truth`), the truth report, the 27 windows and their items."""
    listing = T.require_truth(m)
    report = T.require_truth_report()
    excl, tn, z, _ = T._dev_context()
    dev = T.dev_windows(z, excl, tn["items"])
    return listing, report, z, dev, [w["item"] for w in dev]


def cmd_transcribe(_args):
    """Phase 3b (zero renders): refuses without `phase_tx_lists` reading lists-go, `phase_tx_go_read` and
    `phase_nr_1_redo_truth` on main, and without "Measure first"'s truth-report.json. MuScriptor on the consistent
    truth windows and the 27 development windows (and with no mask on the 27); each note file written once. Basic
    Pitch's note files are not touched here (`read` loads them by their recorded sha256). -> tx/notes/{truth, goat,
    goat-free}/, tx/transcribe.json; the listing sha256 goes into phase_tx_notes before any scoring."""
    m = require_tx(PHASE_GO, PHASE_INSTALL, PHASE_LISTS, PHASE_GO_READ, nr=(T.PHASE_TRUTH,))
    why = lists_go_refusal((m.get(LEDGER_ID) or {}).get(PHASE_LISTS))
    if why:
        raise SystemExit(why)
    inst = require_install(m)
    T.require_file_hash(m.get(LEDGER_ID), PHASE_LISTS, lists_path())
    never_overwrite(transcribe_path())
    listing, report, z, dev, items = stage_b_context(m)
    weights = weights_file(inst["size"], inst["manifest"])
    ta = T.TruthAudio(listing)
    jobs, meta = [], []
    for w in T.usable_windows(listing):
        never_overwrite(note_path("truth", w["key"]))
        _, inp, pre, _ = ta.window(w)
        jobs.append((inp, f"truth:{w['key']}"))
        meta.append(("truth", w["key"], pre))
    goat = []
    for w in dev:
        for k in ("goat", "goat-free"):
            never_overwrite(note_path(k, w["item"]))
        _, inp, pre = T.window_audio(T.goat_audio(z, w["item"]), w["start_s"])
        goat.append((inp, f"goat-dev:{w['item']}"))
        meta.append(("goat", w["item"], pre))
    work = OUT / "work" / "transcribe"
    recs = run_ms(jobs + goat, work / "masked", weights, inst["device"], MS_SETTINGS, listing, items)
    free = run_ms(goat, work / "free", weights, inst["device"], MS_FREE_SETTINGS, listing, items)
    for (kind, key, pre), r in zip(meta, recs):
        NR.write_once(note_path(kind, key), ms_note_record(r, pre, inst["manifest"], kind))
    for (kind, key, pre), r in zip(meta[len(jobs):], free):
        NR.write_once(note_path("goat-free", key), ms_note_record(r, pre, inst["manifest"], "goat-free"))
    rows, sha = notes_listing(("truth", "goat", "goat-free"))
    NR.write_once(transcribe_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}",
                                      "made": time.strftime("%Y-%m-%d %H:%M:%S"),
                                      "body": {"truth_windows": len(jobs), "goat_windows": len(goat),
                                               "note_files": len(rows), "listing_sha256": sha,
                                               "device": inst["device"], "size": inst["size"],
                                               "truth_report_sha256": NR.file_sha(T.truth_report_path())}})
    print(f"TRANSCRIBE: {len(jobs)} truth windows, {len(goat)} development windows (+ {len(goat)} with no mask); "
          f"note files listing sha256 {sha} (into the ledger as {PHASE_NOTES} before any scoring)")


def goat_checks(notes, di, bank, attacks, offset, round_trip, finish, rings=(DECIDING_RING, BESIDE_RING)):
    """One development window's checks per arm (numpy): the note checks (`playing-covered`; `onsets-found`, a report)
    on every arm's notes; on the built arms, `tr-di` built by `note_rebuild.rebuild_redo` (levels as today; ring-soft
    deciding, ring-on beside) and the audio checks (`ring-kept`, `judge-accepts` without a stem: clauses (ii) and
    (iii); `chords-kept` by Basic Pitch's round trip on the deciding ring). round_trip: [(audio, tag)] -> [notes];
    finish: `song_bank.measure`, as `calibrate` finishes its development windows.
    -> {arm: {"notes": {check: pass}, ring: {check: pass}, "figures": ...}}."""
    import numpy as np

    out, jobs, built = {}, [], []
    for a, ns in notes.items():
        figs = {"playing-covered": T.playing_covered(ns, di),
                "onsets-found": T.attacks_found(attacks, ns, di, offset)}
        out[a] = {"notes": T.check_verdict(figs, T.NOTE_CHECKS)["passes"], "figures": {"notes": figs}}
        if a not in BUILT_ARMS:
            continue
        for ring in rings:
            y, _ = NR.rebuild_redo("tr-di", ns, len(di), bank, di, ring, finish=finish)
            y = np.asarray(y, np.float64)
            f = {"ring-kept": T.ring_kept(y, di, [n["on"] for n in ns]), "judge-accepts": T.judge_accepts(y, di, 0, "A")}
            out[a]["figures"][ring] = f
            if ring == rings[0]:
                jobs.append((y, a))
                built.append(a)
            else:
                out[a][ring] = T.check_verdict(f, ("judge-accepts", "ring-kept"))["passes"]
    for a, got in zip(built, round_trip(jobs) if jobs else []):
        f = dict(out[a]["figures"][rings[0]], **{"chords-kept": T.chords_kept(got, notes[a])})
        out[a]["figures"][rings[0]] = f
        out[a][rings[0]] = T.check_verdict(f, T.AUDIO_CHECKS)["passes"]
    return out


def cmd_read(_args):
    """Phase 3b (zero renders), once: refuses without `phase_tx_notes` on main (the note files' listing equal to its
    sha256). The lists' rows from tx/lists.json (main's phase_tx_lists); on every consistent P1 and P2 window Basic
    Pitch's note file (by the truth report's sha256) and MuScriptor's through `timed_notes`, every arm against the
    truth; on the 27 windows the checks per arm (`goat_checks`; the detector's attacks with `attacks-report`'s
    offset). Asserts tx-bp reproduces truth-report.json's matched, ref and est per window. -> tx/read.json (raw
    hand-back, audit, then phase_tx_read)."""
    m = require_tx(PHASE_GO, PHASE_INSTALL, PHASE_LISTS, PHASE_GO_READ, PHASE_NOTES, nr=(T.PHASE_TRUTH,))
    inst = require_install(m)
    rec = (m.get(LEDGER_ID) or {}).get(PHASE_NOTES) or {}
    _, sha = notes_listing(("truth", "goat", "goat-free"))
    if rec.get("listing_sha256") != sha:
        raise SystemExit(f"the note files are not main's {PHASE_NOTES} listing")
    never_overwrite(read_path())
    lists = T.require_file_hash(m.get(LEDGER_ID), PHASE_LISTS, lists_path())["body"]
    listing, report, z, dev, items = stage_b_context(m)
    pair = T.install_pair(T.load_manifest())
    from learn import note_attacks as NA
    from learn import song_bank as SB

    ta = T.TruthAudio(listing)
    real, bp_figs = [], {}
    sha_of = {r["key"]: r["note_file_sha256"] for r in report["windows"]}
    for w in T.usable_windows(listing):
        di, _, _, truth = ta.window(w)
        bp, rb = T.timed_notes(bp_note("truth", w["key"], sha_of.get(w["key"]), pair), di)
        ms, rm = T.timed_notes(ms_events(load_ms("truth", w["key"], inst)), di)
        notes, reps = arm_notes(bp, ms)
        row = window_row("real", f"{w['player']}|{w['kind']}|{w['name']}", w["key"], w["player"], w["kind"], truth,
                         notes, reps, timing={"tx-bp": rb, "tx-ms": rm})
        real.append(row)
        bp_figs[w["key"]] = row["figures"]["tx-bp"]
    why = truth_report_refusal(report["windows"], bp_figs)
    if why:
        raise SystemExit(f"tx-bp does not reproduce the truth report: {why}")
    bank = NR.Bank(NR.load_notes_doc(), excl=NR.load_exclusion())
    offset = T.require_attacks()["offset_s"]
    work = OUT / "work" / "read"
    ins = []
    for w in dev:
        sec, inp, pre = T.window_audio(T.goat_audio(z, w["item"]), w["start_s"])
        ins.append((w, SB.measure(sec), (inp, "goat", pre)))
    att = NA.run_attacks([x for _, _, x in ins], work / "attacks")

    calls = []

    def round_trip(jobs):
        calls.append(len(jobs))
        return [T.clean_transcribed(T.notes_from_events(r["events"]))[0]
                for r in T.run_bp(jobs, work / f"round-trip-{len(calls):02d}")]
    goat = []
    for (w, di, _), a in zip(ins, att):
        it = w["item"]
        bp, rb = T.timed_notes(bp_note("goat", it, report["goat"][it]["note_file_sha256"], pair), di)
        ms, rm = T.timed_notes(ms_events(load_ms("goat", it, inst)), di)
        fr, rf = T.timed_notes(ms_events(load_ms("goat-free", it, inst)), di)
        notes, reps = arm_notes(bp, ms, fr)
        row = window_row("goat", it, it, "goat", None, None, notes, reps,
                         timing={"tx-bp": rb, "tx-ms": rm, "tx-ms-free": rf})
        row["checks"] = goat_checks(notes, di, bank, a, offset, round_trip, SB.measure)
        goat.append(row)
    body = {"lists_rows": len(lists["rows"]), "real": real, "goat": goat,
            **summarise_read(lists["rows"], real, goat), "detector_offset_s": offset,
            "lists_sha256": NR.file_sha(lists_path()), "truth_report_sha256": NR.file_sha(T.truth_report_path()),
            "notes_listing_sha256": sha, "device": inst["device"], "size": inst["size"]}
    NR.write_once(read_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}",
                                "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    print(f"READ {body['code']} {body['flags']}: recommendation: {body['recommendation']['text']}; "
          f"sha256 {NR.file_sha(read_path())}")


def winner_notes(txr, bp, ms):
    """(Pure.) The bridge's notes: the vote's (TXR-vote), tx-ms's with borrowed loudness and bends (TXR-ms), or
    Basic Pitch's with MuScriptor's note-off where paired (TXR-ends)."""
    if txr == "TXR-vote":
        return [{k: v for k, v in n.items() if k != "ms_off"} for n in vote_notes(bp, ms)]
    if txr == "TXR-ms":
        return ms_with_bp(ms, bp)[0]
    if txr == "TXR-ends":
        return ends_notes(bp, ms)
    raise ValueError(txr)


def bridge_builds(txr, loud, windows, bank, finish, rings=(DECIDING_RING, BESIDE_RING)):
    """The built versions' distances (numpy): per window [(key, di, bp, ms)] the winner's notes built as `tr-di`
    (`note_rebuild.rebuild_redo`, `finish`), bv-loud at the adopted loudness, each ring; `floored_logmel` to the DI.
    Never `build_versions`. -> {key: {ring: {bv: dB}}}."""
    out = {}
    for key, di, bp, ms in windows:
        notes = winner_notes(txr, bp, ms)
        out[key] = {}
        for ring in rings:
            out[key][ring] = {}
            for bv in bridge_versions(txr, loud):
                y, _ = NR.rebuild_redo("tr-di", notes, len(di), bank, di, ring, finish=finish,
                                       loud=loud if bv == "bv-loud" else None)
                out[key][ring][bv] = NV.floored_logmel(di, y)
    return out


def reproduce_refusal(stored, rebuilt, tol=1e-9):
    """(Pure.) The bridge's first step: one stored nv-asis distance rebuilt through the bridge's own path must equal
    the stored one to `tol`."""
    if stored is None or rebuilt is None or not math.isfinite(rebuilt) or abs(stored - rebuilt) > tol:
        return f"nv-asis rebuilt {rebuilt} is not the stored {stored}: nothing is read"
    return None


def cmd_bridge(_args):
    """Phase 4 (zero renders), once: refuses without `phase_tx_read` (a code with a bridge) and
    `phase_nr_1_redo_versions` on main. First rebuilds nv-asis for one stored window (the first list by name,
    ring-soft) by `note_rebuild.rebuild_redo` and `note_versions.floored_logmel`, and requires the stored distance to
    1e-9. Then builds only the winner's versions (`bridge_versions`) on the windows versions.json holds, both rings,
    and reads them against the stored nv-hand, nv-asis and nv-loud per window with the stored clusters
    (`bridge_body`). -> tx/bridge.json."""
    m = require_tx(PHASE_GO, PHASE_INSTALL, PHASE_LISTS, PHASE_GO_READ, PHASE_NOTES, PHASE_READ,
                   nr=(T.PHASE_TRUTH, T.PHASE_VERSIONS))
    rd = (m.get(LEDGER_ID) or {}).get(PHASE_READ)
    why = read_bridge_refusal(rd)
    if why:
        raise SystemExit(why)
    txr = rd["code"]
    vrec = (m.get(NR_ID) or {}).get(T.PHASE_VERSIONS)
    if not isinstance(vrec, dict) or "sha256" not in vrec:
        raise SystemExit(f"main's {T.PHASE_VERSIONS} names no versions.json sha256")
    versions = T.require_file_hash(m.get(NR_ID), T.PHASE_VERSIONS, T.versions_path())["body"]
    loud, why = T.versions_loud(m.get(NR_ID))
    if why:
        raise SystemExit(why)
    inst = require_install(m)
    T.require_file_hash(m.get(LEDGER_ID), PHASE_READ, read_path())
    never_overwrite(bridge_path())
    from learn import song_bank as SB

    listing, report, z, dev, _ = stage_b_context(m)
    pair = T.install_pair(T.load_manifest())
    bank = NR.Bank(NR.load_notes_doc(), excl=NR.load_exclusion())
    known = gate_known()
    first = sorted(T.KNOWN_NOTES)[0]
    di0 = SB.measure(T.known_audio(first, bank))
    est0, _ = T.timed_notes({"events": known[first], "pre_s": 0.0}, di0)
    y0, _ = NR.rebuild_redo("tr-di", est0, len(di0), bank, di0, DECIDING_RING, finish=SB.measure)
    stored0 = next((w["d"][DECIDING_RING].get("nv-asis") for w in versions["windows"]
                    if w["set"] == "lists" and w["key"] == first), None)
    why = reproduce_refusal(stored0, NV.floored_logmel(di0, y0))
    if why:
        raise SystemExit(why)
    ta = T.TruthAudio(listing)
    byk = {w["key"]: w for w in T.usable_windows(listing)}
    sha_of = {r["key"]: r["note_file_sha256"] for r in report["windows"]}
    starts = {w["item"]: w["start_s"] for w in dev}
    todo = []
    for vw in versions["windows"]:
        k = vw["key"]
        if vw["set"] == "lists":
            di = SB.measure(T.known_audio(k, bank))
            bp, _ = T.timed_notes({"events": known[k], "pre_s": 0.0}, di)
            ms, _ = T.timed_notes(ms_events(load_ms("list", k, inst)), di)
        elif vw["set"] == "real":
            di, _, _, _ = ta.window(byk[k])
            bp, _ = T.timed_notes(bp_note("truth", k, sha_of.get(k), pair), di)
            ms, _ = T.timed_notes(ms_events(load_ms("truth", k, inst)), di)
        else:
            di = SB.measure(T.window_audio(T.goat_audio(z, k), starts[k])[0])
            bp, _ = T.timed_notes(bp_note("goat", k, report["goat"][k]["note_file_sha256"], pair), di)
            ms, _ = T.timed_notes(ms_events(load_ms("goat", k, inst)), di)
        todo.append((k, di, bp, ms))
    built = bridge_builds(txr, loud, todo, bank, SB.measure)
    nv = vrec.get("code")
    body = {"txr": txr, "nv_code": nv, "loud_gamma": loud, "reproduced": {"window": first, "stored": stored0},
            "built": built, **bridge_body(versions["windows"], built, nv, loud, txr),
            "versions_sha256": NR.file_sha(T.versions_path()), "read_sha256": NR.file_sha(read_path())}
    NR.write_once(bridge_path(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}",
                                  "made": time.strftime("%Y-%m-%d %H:%M:%S"), "body": body})
    print(f"BRIDGE {txr} against {nv}: {body['difference']}; readings {body['readings']}; "
          f"sha256 {NR.file_sha(bridge_path())}")


COMMANDS = {"install": cmd_install, "gate": cmd_gate, "lists": cmd_lists, "transcribe": cmd_transcribe,
            "read": cmd_read, "bridge": cmd_bridge}


def main(argv=None):
    import sys

    for p_ in (str(NR.REPO), str(NR.REPO / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--interpreter", default=None, help="install only: Homebrew's 3.13, the fallback on the user's yes")
    ap.add_argument("--size", choices=sorted(WEIGHTS), default=None, help="gate only: small after the size rule's switch")
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
