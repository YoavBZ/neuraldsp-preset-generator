"""The redo's truth on real DIs: Guitar-TECHS P1 and P2 direct-input recordings with their MIDI (a six-string pickup
tracker's), cleaned and tested for consistency before any window is read (note-rebuild-plan 12m; ledger `note-rebuild`
`phase_nr_1_redo_calib_amend`, then `phase_nr_1_redo_truth`, the listing's sha256, before any run reads a window).

P1 and P2 are development material (CC BY 4.0, credited in NOTICE.md). P3 is held out: `truth_files` refuses any
path outside `P1-downloads` and `P2-downloads`, and nothing here names it. The listing is written once
(`note_transcribe truth`); the truth report (`truth_precision`: Basic Pitch's notes against the cleaned truth,
precision and recall, chords and scales apart, P1 and P2 apart) is reported, never a gate.

The pure parts (the path refusal, the clean-up, the windows, the clusters, the consistency test, the hum share, the
report's pooling) are tested in tests/test_note_truth.py on the light CI runner (no numpy).
"""

from __future__ import annotations

import math
import pathlib

from learn import note_rebuild as NR

ROOT = NR.HOME / "references" / "datasets" / "guitar-techs"
PLAYERS = {"P1": ("chords", "scales"), "P2": ("chords", "scales", "techniques")}   # P3 is held out: never read
ALLOWED = ("P1-downloads", "P2-downloads")
TRUTH_MIN_S = 0.058                      # the truth's clean-up: notes under 58 ms dropped (Basic Pitch's own minimum)
TRUTH_MERGE_S = 0.030                    # ... same-pitch notes within 30 ms merged (as `clean_transcribed`)
WINDOW_STARTS = (10.0, 70.0, 130.0)      # where a full window fits
WINDOW_S = 10.25                         # PS.SEC_S + PS.TRIM_S, the section's length
MIN_NOTES = 8
CLUSTER_S = 0.150                        # onsets chained within 150 ms are one cluster (a strum is one)
RISE_WINDOW_S = 0.150                    # each cluster's steepest DI rise (3 dB or more) within +-150 ms ...
CONSISTENT_WITHIN_S = 0.030              # ... within 30 ms of the window's one offset ...
CONSISTENT_SHARE = 0.80                  # ... for at least 80% of the clusters
HUM_MAINS = (50.0, 60.0)
HUM_HARMONICS = range(1, 7)
HUM_CENTS = 50.0
HUM_STOP = 0.05                          # over 5% of a window's found notes are mains-pitch notes no truth note
                                         # explains: the report stops (12m, relative; the plan's absolute rule was wrong)
HUM_PAIR_S = 0.050                       # a found note pairs with a truth note: same pitch, onsets within 50 ms


def refuse_path(path):
    """(Pure.) Why a path may not be read, or None: only the P1 and P2 download folders; never P3."""
    parts = pathlib.PurePath(path).parts
    if "P3_music" in parts or any(p.startswith("P3") for p in parts):
        return f"{path}: P3 is held out and never read"
    if not any(a in parts for a in ALLOWED):
        return f"{path}: outside {ALLOWED}"
    return None


def truth_files(root=ROOT):
    """The DI files and their MIDI, P1 chords and scales, P2 chords, scales and techniques (not the single notes).
    -> [{player, kind, name, di, midi}] (refuses a path outside P1 and P2, and a DI without its MIDI)."""
    out = []
    for pl, kinds in PLAYERS.items():
        for kind in kinds:
            d = pathlib.Path(root) / f"{pl}-downloads" / f"{pl}_{kind}"
            for di in sorted((d / "audio" / "directinput").glob("directinput_*.wav")):
                name = di.stem.split("directinput_", 1)[1]
                mids = sorted((d / "midi").glob(f"midi_{name}.mid*"))
                for p in [di] + mids[:1]:
                    why = refuse_path(p)
                    if why:
                        raise SystemExit(why)
                if not mids:
                    raise SystemExit(f"{di.name}: no MIDI")
                out.append({"player": pl, "kind": kind, "name": name, "di": str(di), "midi": str(mids[0])})
    return out


def clean_truth(notes, min_s=TRUTH_MIN_S, merge_s=TRUTH_MERGE_S):
    """(Pure.) The truth's declared clean-up: notes under `min_s` dropped; a pitch struck twice within `merge_s`
    merged into the first (its end the later). notes: [{on, off, pitch}]. -> (notes in onset order, counts)."""
    cnt = {"short": 0, "merged": 0}
    kept = []
    for n in sorted(notes, key=lambda n: (n["on"], n["pitch"], n["off"])):
        if n["off"] - n["on"] < min_s:
            cnt["short"] += 1
            continue
        twin = next((m for m in kept if m["pitch"] == n["pitch"] and abs(m["on"] - n["on"]) < merge_s), None)
        if twin is not None:
            twin["off"] = max(twin["off"], n["off"])
            cnt["merged"] += 1
            continue
        kept.append(dict(n))
    return kept, cnt


def window_starts(duration_s, starts=WINDOW_STARTS, length=WINDOW_S):
    """(Pure.) The declared window starts where a full window fits."""
    return [s for s in starts if s + length <= duration_s + 1e-9]


def in_window(notes, start, length=WINDOW_S):
    """(Pure.) The notes starting inside [start, start + length), on the window's timeline (off held to its end)."""
    return [dict(n, on=n["on"] - start, off=min(n["off"], start + length) - start, bends=list(n.get("bends") or []),
                 amp=n.get("amp", 1.0))
            for n in notes if start <= n["on"] < start + length]


def clusters(onsets, gap=CLUSTER_S):
    """(Pure.) Onsets chained within `gap` (each within `gap` of the previous one) as clusters. -> [[onsets]]."""
    out = []
    for t in sorted(onsets):
        if out and t - out[-1][-1] <= gap:
            out[-1].append(t)
        else:
            out.append([t])
    return out


def consistent(shifts, offset, n_notes, within=CONSISTENT_WITHIN_S, share=CONSISTENT_SHARE, min_notes=MIN_NOTES):
    """(Pure.) The truth window's admission: at least `min_notes` notes, and at least `share` of its onset clusters
    have their steepest DI rise within `within` of the window's one offset. shifts: per cluster the rise's time less
    the cluster's first onset (None where no rise of 3 dB or more). -> {consistent, clusters, share}."""
    if not shifts:
        return {"consistent": False, "clusters": 0, "share": None}
    hit = sum(s is not None and abs(s - offset) <= within for s in shifts)
    sh = hit / len(shifts)
    return {"consistent": n_notes >= min_notes and sh >= share, "clusters": len(shifts), "share": sh}


def cluster_shifts(notes, di, rate=NR.SR, window=RISE_WINDOW_S):
    """Each onset cluster's steepest DI rise (`note_rebuild.rise_curve`) within +-window of its first onset, as a time
    less that onset; None where the rise is under REFINE_MIN_RISE_DB."""
    import numpy as np

    rise, hop = NR.rise_curve(di, rate)
    out = []
    for c in clusters([n["on"] for n in notes]):
        t = c[0]
        lo = max(0, int((t - window) * rate) // hop)
        hi = min(len(rise), int((t + window) * rate) // hop + 1)
        if hi <= lo:
            out.append(None)
            continue
        j = lo + int(np.argmax(rise[lo:hi]))
        out.append((j * hop + NR.REFINE_FRAME / 2) / rate - t if rise[j] >= NR.REFINE_MIN_RISE_DB else None)
    return out


def midi_truth(path):
    """A MIDI file's notes (the project's `research/build_riffs.midi_notes`). -> [{on, off, pitch}]."""
    import sys

    sys.path.insert(0, str(NR.REPO / "research"))
    import build_riffs as BR

    return [{"on": a, "off": b, "pitch": p} for a, b, p in BR.midi_notes(pathlib.Path(path).read_bytes())]


def di_audio(path, rate=NR.SR):
    """A DI file folded to mono at 48 kHz (P2's stereo files have identical channels)."""
    import soundfile as sf

    from learn import clean_di as CD

    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    x = x.mean(axis=1)
    return x if sr == rate else CD.resample(x, sr, rate)


def window_of(x, start, rate=NR.SR):
    """(The window's 10.25 s, the transcriber's input with up to 1 s either side, pre_s), as the development windows'."""
    from learn import note_transcribe as T

    return T.window_audio(x, start, rate)


def truth_notes(notes_clean, start, di, rate=NR.SR):
    """A window's truth on the section's timeline: the cleaned file's notes inside it, `coarse_offset` and the +-20 ms
    snap against the DI as rendered. -> (notes, offset seconds)."""
    w = in_window(notes_clean, start)
    off = NR.coarse_offset(w, di, rate)
    return NR.snap_onsets(NR.shifted_notes(w, off), di, NR.SNAP_S, rate)[0], off


def midi_freq(p):
    return 440.0 * 2 ** ((p - 69) / 12)


def on_mains(pitch, mains=HUM_MAINS, harmonics=HUM_HARMONICS, cents=HUM_CENTS):
    """(Pure.) A MIDI pitch within `cents` of a mains harmonic (50 or 60 Hz times 1 to 6)."""
    f = midi_freq(pitch)
    return any(abs(1200 * math.log2(f / (m * k))) <= cents for m in mains for k in harmonics)


def paired_found(found, truth, onset_s=HUM_PAIR_S):
    """(Pure.) The found notes' indices that pair one to one with a truth note (same pitch, onsets within `onset_s`,
    the closest first, as `match_notes`)."""
    pairs = sorted((abs(r["on"] - e["on"]), i, j) for i, r in enumerate(truth) for j, e in enumerate(found)
                   if r["pitch"] == e["pitch"] and abs(r["on"] - e["on"]) <= onset_s)
    ui, uj = set(), set()
    for _, i, j in pairs:
        if i not in ui and j not in uj:
            ui.add(i)
            uj.add(j)
    return uj


def hum_share(found, truth):
    """(Pure.) The hum guard's figure (12m, relative): the share of a window's found notes that sit on a mains
    harmonic (50 or 60 Hz times 1 to 6, within 50 cents) and pair with no truth note. Over HUM_STOP stops the report.
    The plan's first rule counted every found note on a mains pitch; those pitches include MIDI 43, 47, 50, 54, 55,
    59, 62 and 66 (G, B, D and F-sharp), so ordinary playing in G tripped it (228 of 238 windows, with the truth
    itself as the found notes)."""
    if not found:
        return 0.0
    ok = paired_found(found, truth)
    return sum(on_mains(n["pitch"]) and j not in ok for j, n in enumerate(found)) / len(found)


def truth_precision(rows):
    """(Pure.) The truth report pooled by player and kind: precision and recall of Basic Pitch's notes against the
    cleaned truth (`match_notes`, same pitch, 50 ms). rows: [{player, kind, matched, ref, est}]. -> {group: figures}
    with groups "P1|chords", ..., "P1", "P2"."""
    out = {}
    for r in rows:
        for g in (f"{r['player']}|{r['kind']}", r["player"]):
            a = out.setdefault(g, {"matched": 0, "ref": 0, "est": 0, "windows": 0})
            a["matched"] += r["matched"]
            a["ref"] += r["ref"]
            a["est"] += r["est"]
            a["windows"] += 1
    for a in out.values():
        a["recall"] = a["matched"] / a["ref"] if a["ref"] else None
        a["precision"] = a["matched"] / a["est"] if a["est"] else None
    return out


def listing_body(files, windows, counts):
    """(Pure.) The truth listing's body: every file's sha256 and kind, every window with its consistency, and the
    clean-up's counts. windows: [{key, player, kind, name, start, notes, consistent, ...}]."""
    by = {}
    for w in windows:
        g = f"{w['player']}|{w['kind']}"
        b = by.setdefault(g, {"windows": 0, "consistent": 0})
        b["windows"] += 1
        b["consistent"] += bool(w["consistent"])
    return {"files": files, "windows": windows, "cleanup": counts, "by_player_kind": by,
            "rule": {"min_s": TRUTH_MIN_S, "merge_s": TRUTH_MERGE_S, "starts": list(WINDOW_STARTS), "length": WINDOW_S,
                     "min_notes": MIN_NOTES, "cluster_s": CLUSTER_S, "rise_window_s": RISE_WINDOW_S,
                     "within_s": CONSISTENT_WITHIN_S, "share": CONSISTENT_SHARE}}


def window_key(f, start):
    """(Pure.) A truth window's key: player, kind, name and start."""
    return f"{f['player']}|{f['kind']}|{f['name']}@{start:g}"


def build_listing():
    """The listing (zero Basic Pitch runs): per file its DI and MIDI sha256 and the clean-up's counts; per declared
    window its truth notes, offset and consistency. -> body (written once by `note_transcribe truth`)."""
    from learn import song_bank as SB

    files, windows, counts = [], [], {"short": 0, "merged": 0, "files": 0}
    for f in truth_files():
        x = di_audio(f["di"])
        raw = midi_truth(f["midi"])
        clean, cnt = clean_truth(raw)
        counts["short"] += cnt["short"]
        counts["merged"] += cnt["merged"]
        counts["files"] += 1
        files.append({**f, "di_sha256": NR.file_sha(f["di"]), "midi_sha256": NR.file_sha(f["midi"]),
                      "notes_raw": len(raw), "notes_clean": len(clean), **cnt})
        for st in window_starts(len(x) / NR.SR):
            sec, _, _ = window_of(x, st)
            di = SB.measure(sec)
            notes, off = truth_notes(clean, st, di)
            # the admission reads the MIDI as it is (before the offset and the snap) against the window's one offset
            cons = consistent(cluster_shifts(in_window(clean, st), di), off, len(notes))
            windows.append({"key": window_key(f, st), "player": f["player"], "kind": f["kind"], "name": f["name"],
                            "start": st, "notes": len(notes), "offset_ms": 1000 * off, **cons})
    return listing_body(files, windows, counts)
