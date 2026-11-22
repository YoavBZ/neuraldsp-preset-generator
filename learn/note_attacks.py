"""The redo's attack detector, replaced (note-rebuild-plan 12m; ledger `note-rebuild` `phase_nr_1_redo_calib_amend`):
librosa's spectral-flux onset detector (`learn/attack_run.py`, in the Basic Pitch venv) on the transcriber's own
input, and `onsets-found` as a report, no longer a gate.

`onsets-found` per part: the share of the DI's attacks (where the DI plays), after the detector's steady offset
(`detector_offset`, measured on P1), with a note onset within FOUND_S; flagged under FLAG_UNDER. Its own report
carries the detector's recall of true onset groups, overall and on ringing onsets (`detector_recall`); should it ever
gate again it needs 0.90 on both. A ringing onset starts while another note has sounded RINGING_S and goes on RINGING_S
more.

The pure parts are tested in tests/test_note_attacks.py on the light CI runner (no numpy).
"""

from __future__ import annotations

import json
import pathlib
import statistics

from learn import note_rebuild as NR

ATTACK_HOP = 256                         # 11.6 ms at 22.05 kHz (librosa's default is 512)
ATTACK_DELTA = 0.07                      # librosa's default threshold
FOUND_S = 0.050                          # an attack is found with a note onset within 50 ms, after the offset
FLAG_UNDER = 0.90                        # a part is flagged under this share (a report, not a refusal)
RINGING_S = 0.100
RECALL_FLOOR = 0.90                      # the detector's own recall, overall and ringing, should it ever gate again
GROUP_S = NR.CHORD_S                     # true onsets within 50 ms are one onset group
STRUM_GROUP_S = 0.150                    # on chord windows a strum spreads 120 to 200 ms: their recall is also
                                         # reported on 150-ms groups (a report only)


def onset_groups(onsets, gap=GROUP_S):
    """(Pure.) The first onset of each group of onsets within `gap` of the group's first."""
    out = []
    for t in sorted(onsets):
        if not out or t - out[-1] >= gap:
            out.append(t)
    return out


def detector_offset(rows, within=FOUND_S):
    """(Pure.) The detector's steady offset: the median of (true onset less attack) over every attack within `within`
    of a true onset group. rows: [(attacks, true onsets)] (P1's windows). -> seconds (0.0 with none)."""
    d = []
    for att, ons in rows:
        gs = onset_groups(ons)
        for a in att:
            if gs:
                k = min(gs, key=lambda o: abs(o - a))
                if abs(k - a) <= within:
                    d.append(k - a)
    return statistics.median(d) if d else 0.0


def onsets_found(attacks, onsets, offset=0.0, within=FOUND_S, flag=FLAG_UNDER):
    """(Pure.) `onsets-found`'s figure: the share of attacks (already filtered to where the DI plays), moved by
    `offset`, with a note onset within `within`; flagged under `flag`; not measured (None) with no attack."""
    att = [a + offset for a in attacks]
    found = sum(any(abs(a - o) <= within for o in onsets) for a in att)
    share = found / len(att) if att else None
    return {"attacks": len(att), "found": found, "share": share, "flag": share is not None and share < flag,
            "offset_s": offset}


def ringing(t, notes, wait=RINGING_S):
    """(Pure.) An onset at `t` is ringing when another note has sounded `wait` by then and goes on `wait` more."""
    return any(m["on"] <= t - wait and m["off"] >= t + wait for m in notes)


def detector_recall(attacks, notes, offset=0.0, within=FOUND_S, gap=GROUP_S):
    """(Pure.) The detector's recall of the true onset groups (onsets within `gap` of a group's first; STRUM_GROUP_S
    on chord windows, reported beside), overall and on ringing onsets. notes: the true notes [{on, off}].
    -> {groups, found, recall, ringing, ringing_found, ringing_recall}."""
    att = [a + offset for a in attacks]
    gs = onset_groups([n["on"] for n in notes], gap)
    hit = [any(abs(a - g) <= within for a in att) for g in gs]
    rg = [i for i, g in enumerate(gs) if ringing(g, notes)]
    return {"groups": len(gs), "found": sum(hit), "recall": sum(hit) / len(gs) if gs else None,
            "ringing": len(rg), "ringing_found": sum(hit[i] for i in rg),
            "ringing_recall": sum(hit[i] for i in rg) / len(rg) if rg else None}


def pooled_recall(figs):
    """(Pure.) `detector_recall` figures pooled. -> {recall, ringing_recall, holds_floor}."""
    g, f = sum(x["groups"] for x in figs), sum(x["found"] for x in figs)
    rg, rf = sum(x["ringing"] for x in figs), sum(x["ringing_found"] for x in figs)
    r, rr = (f / g if g else None), (rf / rg if rg else None)
    return {"groups": g, "found": f, "recall": r, "ringing": rg, "ringing_found": rf, "ringing_recall": rr,
            "holds_floor": r is not None and rr is not None and r >= RECALL_FLOOR and rr >= RECALL_FLOOR}


def truth_passes(attacks, truth_onsets, offset=0.0):
    """(Pure.) The detector on the truth itself: `onsets-found` against the true onsets, at or over FLAG_UNDER."""
    f = onsets_found(attacks, truth_onsets, offset)
    return f["share"] is not None and f["share"] >= FLAG_UNDER


def plays_filter(times, di, rate=NR.SR):
    """The attacks where the DI plays: its 20-ms level (5-ms hop) within 40 dB of its loudest, as the old detector's
    filter."""
    from learn import note_transcribe as T

    n, h = int(T.CHECK_FRAME_S * rate), int(T.CHECK_HOP_S * rate)
    L = NR.frame_levels_db(di, n, h)
    if not len(L):
        return []
    top = float(L.max())
    keep = []
    for t in times:
        f = min(len(L) - 1, max(0, int((t * rate - n / 2) // h)))
        if L[f] >= top - T.PLAY_FLOOR_DB:
            keep.append(t)
    return keep


def run_attacks(jobs, workdir, hop=ATTACK_HOP, delta=ATTACK_DELTA):
    """The detector on [(48 kHz audio, tag, pre_s)] in one attack_run process (the Basic Pitch venv's interpreter,
    `-I`), each on the transcriber's own input; times moved by `pre_s` onto the section's timeline.
    -> [onset times]."""
    import subprocess

    import soundfile as sf

    from learn import note_transcribe as T

    workdir = pathlib.Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    args = []
    for i, (x, tag, _) in enumerate(jobs):
        w, o = workdir / f"{i:03d}-{tag}.wav", workdir / f"{i:03d}-{tag}.json"
        sf.write(str(w), T.transcriber_input(x), T.BP_SR, subtype="FLOAT")
        args += [str(w), str(o)]
    r = subprocess.run([str(T.BP_PYTHON), "-I", str(NR.REPO / "learn" / "attack_run.py"), "--hop", str(hop),
                        "--delta", str(delta), *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"attack_run failed: {r.stderr.strip()[-400:]}")
    out = []
    for (_, _, pre), o in zip(jobs, args[1::2]):
        rec = json.loads(pathlib.Path(o).read_text())
        if rec["hop_length"] != hop or rec["delta"] != delta:
            raise SystemExit("attack_run ran other settings")
        out.append([t - pre for t in rec["onsets"]])
    return out
