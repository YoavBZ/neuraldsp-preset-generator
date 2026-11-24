"""The note rebuild's fixes after the ear page's `fault-content` (note-rebuild-plan 12q; ledger `note-rebuild`
`phase_nr_1_redo_fixes`; the delegated decision of 2026-11-24, `rebuild-one-fix.md`, not the user's go).

Each fix is a pure transform of a window's timed notes (`note_transcribe.timed_notes`) before `note_rebuild.rebuild_redo`,
so with every fix off the rebuild is the first build, byte for byte (the identity check):
- F1, the bend baseline: Basic Pitch's bend track reads +1 step on an in-tune note; a note's bend is its track less its
  baseline (`rezero_bends`: the global -1 step, or each note's own median; picked by measurement).
- F2, joining same-pitch re-finds: a note re-found while the same pitch still sounds (`refind_pairs`) extends that note
  instead of re-plucking it, when the discriminator reads no new attack (`join_refinds`; the DI's pitch-band rise,
  `band_change_db`; its operating point read from the measured trade-off, never set in advance).
- F3, joining glides: when a note's re-zeroed bend moves toward the next note's pitch and the next note starts as it
  ends (`handoff_pairs`), the next note continues the same sample along the bend path (`join_glides`).
- F4 (`tx-veto`'s ghosts) and F2's MuScriptor candidate wait for track 1's real-DI read.

No pass/fail bar and no attempt cap (the user, 2026-11-24): every effect is reported with its interval; a fix is kept
when it measurably brings the rebuild closer to the DI. `item_5` is in no set (12p).

    $MAIN -m learn.note_fixes isolate OUT.json   # zero renders: identity, then each fix alone on L and D (preliminary
                                                 # from a branch; the declared run from merged main)

F6, bend chains (12t; ledger `phase_nr_1_redo_fix_bend`): a bend Basic Pitch splits into semitone notes is stitched
back into one bent note when the notes' absolute pitch tracks meet at the junction (`f6_pairs`, `f6_chains`,
`f6_stitch`), F6b's `keep_bend` exempting it from the clear rule. Zero renders throughout:

    $MAIN -m learn.note_fixes bend-lists                     # B's lists played and transcribed (fixes/bend/lists/)
    $MAIN -m learn.note_fixes bend-windows                   # Db's windows transcribed (fixes/bend/windows/)
    $MAIN -m learn.note_fixes isolate-bend OUT.json [--declared]   # identity, the ladder, B's fault, every grid
                                                             # point, the pick and the keep call
    $MAIN -m learn.note_fixes e-read OUT.json --fixes '<frozen>' --base '{"F1": "global"}' [--declared]
    $MAIN -m learn.note_fixes exposure OUT.json --fixes '<frozen>' [--declared]
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time

from learn import note_rebuild as NR

PHASE = "phase_nr_1_redo_fixes"
F1_MODES = ("global", "median")          # the bend baseline's two candidates
BASELINE_STEP = 1                        # Basic Pitch's bend track on an in-tune note (93% of notes, the decision's
                                         # measurement): the global candidate subtracts it
# the pair definitions, candidate definitions and not tuned bars (the decision's probes, `probe4.py`): which notes a
# join may consider; the discriminator then decides each pair
REFIND_LEAD_S, REFIND_TAIL_S = 0.030, 0.060   # a same-pitch note started 30 ms or more before, still sounding or
                                              # ended within 60 ms of this onset
HANDOFF_S = 0.060                        # a glide's next note starts within 60 ms of this note's end
HANDOFF_SEMITONES = (1, NR.BEND_MAX_SEMITONES)   # 1 to the bend cap (the synthesis clamp, unchanged in build 2)
F2_GRID_DB = (-math.inf, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, math.inf)   # the sweep's points (a measurement grid, not
                                         # a bar): join when the pitch band changes less than this
EAR_ITEMS = ("item_102", "item_160", "item_46", "item_57", "item_77", "item_49", "item_39", "item_5")
LEGATO_ARTS = {"hammer", "slide", "bend"}


# --- F1: the bend baseline (pure) --------------------------------------------------------------------------------------

def rezero_bends(notes, mode):
    """(Pure.) Each note's bend track less its baseline: `global`, BASELINE_STEP off every frame; `median`, the note's
    own median off every frame. None or "" leaves the notes as they are. -> new notes."""
    if not mode:
        return [dict(n) for n in notes]
    if mode not in F1_MODES:
        raise ValueError(mode)
    out = []
    for n in notes:
        b = [float(v) for v in (n.get("bends") or [])]
        if b:
            base = BASELINE_STEP if mode == "global" else statistics.median(b)
            b = [v - base for v in b]
        out.append(dict(n, bends=b))
    return out


def bent_share(notes):
    """(Pure.) The share of notes `bend_curve` bends (any frame), or None without notes."""
    if not notes:
        return None
    return sum(any(NR.bend_curve(n, notes)) for n in notes) / len(notes)


# --- F2: joining same-pitch re-finds (pure, then the DI's band) --------------------------------------------------------

def refind_pairs(notes, lead_s=REFIND_LEAD_S, tail_s=REFIND_TAIL_S):
    """(Pure.) The candidate re-finds: (i, j) where note j has a same-pitch note i started `lead_s` or more before it
    and still sounding, or ended within `tail_s` of its onset (the latest such i). -> [(i, j)] in onset order."""
    out = []
    for j, n in enumerate(notes):
        prev = [i for i, m in enumerate(notes) if i != j and m["pitch"] == n["pitch"]
                and m["on"] < n["on"] - lead_s and m["off"] > n["on"] - tail_s]
        if prev:
            out.append((max(prev, key=lambda i: notes[i]["on"]), j))
    return out


def join_refinds(notes, pairs, joins):
    """(Pure.) Joins: each re-find j in `joins` (a subset of `pairs`' j) extends its sounding note i to j's end
    (chains follow: a re-find of a joined note extends the first) and is dropped. -> new notes."""
    target = {j: i for i, j in pairs if j in joins}
    out = [dict(n) for n in notes]
    root = {}
    for j in sorted(target, key=lambda j: notes[j]["on"]):
        i = target[j]
        while i in root:
            i = root[i]
        root[j] = i
        out[i]["off"] = max(out[i]["off"], notes[j]["off"])
    return [n for k, n in enumerate(out) if k not in target]


def band_change_db(di, note, rate=NR.SR):
    """The DI's pitch-band energy change at a note's onset (the decision's probe): the note's first four harmonics
    (within max(12 Hz, 3%)) on 2,048-sample STFT frames hopped 240, the mean of frames 2 to 6 after the onset over
    frames 3 to 8 before it, in dB. A real attack raises its own band; a re-find of a sounding note barely does."""
    import numpy as np
    import scipy.signal as ss

    f, t, s = ss.stft(np.asarray(di, np.float64), fs=rate, nperseg=2048, noverlap=2048 - 240)
    p = np.abs(s) ** 2
    f0 = 440.0 * 2 ** ((note["pitch"] - 69) / 12)
    rows = np.zeros(len(f), bool)
    for h in (1, 2, 3, 4):
        rows |= np.abs(f - h * f0) <= max(12.0, h * f0 * 0.03)
    band = p[rows].sum(0) + 1e-12
    j = int(np.argmin(np.abs(t - note["on"])))
    pre = band[max(0, j - 8):max(1, j - 3)].mean()
    post = band[j + 2:j + 7].mean() if j + 7 <= len(band) else band[j:].mean()
    return float(10 * np.log10(post / pre))


def f2_joins(pairs, changes, theta):
    """(Pure.) At operating point `theta`: the re-finds whose pitch band changes less than `theta` dB. changes:
    {j: dB}. -> set of j."""
    return {j for _, j in pairs if changes.get(j) is not None and changes[j] < theta}


# --- F3: joining glides (pure) -----------------------------------------------------------------------------------------

def handoff_pairs(notes, gap_s=HANDOFF_S, span=HANDOFF_SEMITONES):
    """(Pure.) The candidate glides on re-zeroed notes: (i, j) where note j starts within `gap_s` of note i's end, at
    1 to the bend cap semitones away, and i's bend at its end moves toward j (the mean of its last five frames' track
    on j's side of zero). -> [(i, j)]."""
    out = []
    for i, m in enumerate(notes):
        b = [float(v) for v in (m.get("bends") or [])]
        if not b:
            continue
        tail = b[-NR.BEND_MIN_FRAMES:]
        lean = sum(tail) / len(tail)
        for j, n in enumerate(notes):
            d = n["pitch"] - m["pitch"]
            if j == i or not span[0] <= abs(d) <= span[1] or abs(n["on"] - m["off"]) > gap_s:
                continue
            if lean * d > 0:
                out.append((i, j))
                break
    return out


def join_glides(notes, pairs, rate_frame=NR.BEND_FRAME_S):
    """(Pure.) Each glide (i, j): note i continues to j's end, its bend track running on from j's onset at j's pitch
    (j's own track added), and j is dropped. -> new notes."""
    drop, out = set(), [dict(n) for n in notes]
    for i, j in pairs:
        if i in drop or j in drop:
            continue
        m, n = out[i], notes[j]
        d_steps = (n["pitch"] - m["pitch"]) * NR.BEND_STEPS_PER_SEMITONE
        k = max(0, int(round((n["on"] - m["on"]) / rate_frame)))
        b = [float(v) for v in (m.get("bends") or [])][:k]
        b += [b[-1] if b else 0.0] * (k - len(b))
        b += [d_steps + float(v) for v in (n.get("bends") or [])] or [float(d_steps)]
        n_frames = int(round((n["off"] - m["on"]) / rate_frame))
        b += [b[-1]] * max(0, n_frames - len(b))
        out[i] = dict(m, off=max(m["off"], n["off"]), bends=b)
        drop.add(j)
    return [n for k, n in enumerate(out) if k not in drop]


# --- F6: bend chains (pure; note-rebuild-plan 12t, ledger phase_nr_1_redo_fix_bend) -----------------------------------

PHASE_F6 = "phase_nr_1_redo_fix_bend"               # the declaration (M1)
PHASE_F6_LISTS = "phase_nr_1_redo_bend_lists"       # the bend lists' and windows' note files hashed (M2), before a
                                                    # declared run reads them
PHASE_F6_FROZEN = "phase_nr_1_redo_fix_bend_frozen"  # the picked rule (M3); `e-read` refuses without it
F6_K = (1, 3, 5)                       # the grid: frames in a junction median ...
F6_GAPS = (0, 1, 2)                    # ... the largest gap joined, in bins (thirds of a semitone) ...
F6_FAMILIES = ("sequential", "both")   # ... sequential pairs alone, or with overlapping pairs; every point reported
F6_TRACKS = ("own", "line")            # the stitched track: the members' own tracks, or a line through their pitches
F6_PARAM_KEYS = ("K", "gap", "family", "track", "keep")
F6_SEQ_S = 0.060                       # J1, sequential: on_j - off_i within +-60 ms ...
F6_LEAD_S = 0.030                      # ... both families: on_j more than 30 ms after on_i ...
F6_OVERLAP_S = 0.060                   # ... overlapping: on_j more than 60 ms before off_i (the families are disjoint)
F6_SEMITONES = (1, 3)                  # 1 to 3 semitones apart
F6_PAD_S = NR.RING_SOFT_S              # the release padding: a stitched track holds its last value 150 ms past the off
F6_K_PREFERENCE = (3, 5, 1)            # B2: a preference, not simplicity (on D, K = 3 and K = 5 join the same 2 plucks)


def f6_params(p):
    """(Pure.) F6's parameters checked: {K, gap, family, track, keep}, each on its grid. -> p, or ValueError."""
    if not isinstance(p, dict) or set(p) != set(F6_PARAM_KEYS):
        raise ValueError(f"F6 takes exactly {list(F6_PARAM_KEYS)}, not {p!r}")
    if (isinstance(p["K"], bool) or p["K"] not in F6_K or isinstance(p["gap"], bool) or p["gap"] not in F6_GAPS
            or p["family"] not in F6_FAMILIES or p["track"] not in F6_TRACKS or not isinstance(p["keep"], bool)):
        raise ValueError(f"F6's parameters off the declared grid: {p!r}")
    return p


def note_track(n):
    """(Pure.) A note's bend track per Basic Pitch frame from its onset, in steps (bins), as floats."""
    return [float(v) for v in (n.get("bends") or [])]


def f6_pairs(notes, k, family):
    """(Pure.) F6's candidate pairs on F1-`global` notes (12t, J1). (i, j): j starts more than F6_LEAD_S after i, 1 to
    3 semitones away. Sequential: on_j - off_i within +-F6_SEQ_S; gap = |3(p_i - p_j) + median of i's last k frames -
    median of j's first k frames|. Overlapping (family "both" only): on_j more than F6_OVERLAP_S before off_i; gap =
    |the median, over the frames both sound (j's frames, at least k), of the same difference|. -> [(i, j, gap, kind)]."""
    F = NR.BEND_FRAME_S
    out = []
    for i, a in enumerate(notes):
        ta = note_track(a)
        if not ta:
            continue
        for j, b in enumerate(notes):
            d = a["pitch"] - b["pitch"]
            if j == i or not F6_SEMITONES[0] <= abs(d) <= F6_SEMITONES[1] or not b["on"] - a["on"] > F6_LEAD_S:
                continue
            tb = note_track(b)
            if not tb:
                continue
            if abs(b["on"] - a["off"]) <= F6_SEQ_S:
                gap = abs(3 * d + statistics.median(ta[-k:]) - statistics.median(tb[:k]))
                out.append((i, j, gap, "sequential"))
            elif family == "both" and b["on"] < a["off"] - F6_OVERLAP_S:
                diffs = []
                for q, v in enumerate(tb):
                    t = b["on"] + q * F
                    p = int(round((t - a["on"]) / F))
                    if t >= min(a["off"], b["off"]) or p >= len(ta):
                        break
                    diffs.append(3 * d + ta[p] - v)
                if len(diffs) >= k:
                    out.append((i, j, abs(statistics.median(diffs)), "overlapping"))
    return out


def f6_chains(notes, pairs, max_gap):
    """(Pure.) The chains: pairs with gap <= max_gap linked so each note has at most one predecessor and one successor
    (the smallest gap first; a tie takes the later onset, of j, then of i), followed from each head. -> [[indices]] in
    onset order, each two or more notes."""
    acc = sorted((p for p in pairs if p[2] <= max_gap),
                 key=lambda p: (p[2], -notes[p[1]]["on"], -notes[p[0]]["on"], p[0], p[1]))
    succ, pred = {}, {}
    for i, j, _, _ in acc:
        if i in succ or j in pred:
            continue
        succ[i], pred[j] = j, i
    chains = []
    for h in sorted(succ, key=lambda i: (notes[i]["on"], i)):
        if h in pred:
            continue
        c = [h]
        while c[-1] in succ:
            c.append(succ[c[-1]])
        chains.append(c)
    return chains


def stitched_track(notes, chain, track="own"):
    """(Pure.) A chain's track from its head's onset, in steps from the head's pitch, through the last member's note-off
    plus F6_PAD_S (holding the last value: the release padding). `own`: on each frame, the track of the latest-started
    member sounding then (its frame from its own onset, its last value past its track's end), plus 3 x (member pitch -
    head pitch); a frame with no member sounding holds the last value (so an overlapping pair switches on j's first
    frame). `line`: linear through (each member's onset, 3 x (its pitch - the head's)), held after the last onset."""
    F = NR.BEND_FRAME_S
    h = notes[chain[0]]
    end = max(notes[m]["off"] for m in chain)
    body = max(1, int(math.ceil((end - h["on"]) / F)))
    total = int(math.ceil((end + F6_PAD_S - h["on"]) / F))
    out = []
    if track == "own":
        for q in range(body):
            t = h["on"] + q * F
            snd = [m for m in chain if notes[m]["on"] <= t < notes[m]["off"]]
            if not snd:
                out.append(out[-1] if out else 0.0)
                continue
            m = max(snd, key=lambda m: (notes[m]["on"], m))
            tm = note_track(notes[m])
            p = int(round((t - notes[m]["on"]) / F))
            out.append(3.0 * (notes[m]["pitch"] - h["pitch"]) + (tm[min(p, len(tm) - 1)] if tm else 0.0))
    elif track == "line":
        pts = [(notes[m]["on"], 3.0 * (notes[m]["pitch"] - h["pitch"])) for m in chain]
        for q in range(body):
            t = h["on"] + q * F
            v = pts[-1][1]
            for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
                if t < t1:
                    v = v0 + (v1 - v0) * max(0.0, t - t0) / (t1 - t0)
                    break
            out.append(v)
    else:
        raise ValueError(track)
    return out + [out[-1]] * max(0, total - len(out))


def f6_stitch(notes, chains, track="own", keep=False):
    """(Pure.) F6a (and F6b with `keep`): each chain becomes its head, ending at the members' last note-off, with the
    stitched track (`stitched_track`); the other members are dropped; with `keep` the stitched note carries `keep_bend`
    (the clear rule skips it, `note_rebuild.bend_curve`). Unstitched notes are unchanged. -> new notes."""
    head = {c[0]: c for c in chains}
    drop = {m for c in chains for m in c[1:]}
    out = []
    for k, n in enumerate(notes):
        if k in drop:
            continue
        if k in head:
            c = head[k]
            n2 = dict(n, off=max(notes[m]["off"] for m in c), bends=stitched_track(notes, c, track))
            if keep:
                n2["keep_bend"] = True
            out.append(n2)
        else:
            out.append(dict(n))
    return out


def apply_f6(notes, p):
    """(Pure.) F6 at parameters `p` on F1-`global` notes: the pairs of `p`'s family at K, the chains at its gap, the
    stitch with its track and keep. -> (notes, report {pairs, chains, joins})."""
    f6_params(p)
    pairs = f6_pairs(notes, p["K"], p["family"])
    chains = f6_chains(notes, pairs, p["gap"])
    return f6_stitch(notes, chains, p["track"], p["keep"]), {
        "pairs": len(pairs), "chains": chains, "joins": sum(len(c) - 1 for c in chains)}


def pad_bent(notes, others=None):
    """(Pure.) The beside arm "pad every bent note" (12t; never inside build 3): a note whose curve as played
    (`bend_curve` against the window's notes) ends bent holds its track's last value through its note-off plus
    F6_PAD_S, so it no longer drops back to its pitch in the release. Other notes unchanged. -> new notes."""
    F = NR.BEND_FRAME_S
    others = notes if others is None else others
    out = []
    for n in notes:
        c = NR.bend_curve(n, others)
        if c and c[-1] != 0:
            b = note_track(n)
            total = int(math.ceil((n["off"] + F6_PAD_S - n["on"]) / F))
            out.append(dict(n, bends=b + [b[-1]] * max(0, total - len(b))))
        else:
            out.append(dict(n))
    return out


# --- 12r: the MuScriptor-based fixes (pure; MuScriptor's timed notes beside Basic Pitch's) --------------------------

MS_JOIN_WINDOWS_S = (0.050, 0.100, 0.150)    # F2-MuScriptor's operating points (12r)
CONFIRM_S = 0.050                            # a MuScriptor confirmation: same pitch, onsets within 50 ms (track 1's pair)
F4_BELOW_S = (0.050, 0.150)                  # F4: the paired note below confirmed within 50 ms (as declared), 150 beside
F5_CONTEXT_S, F5_CONTEXT_COUNT = 0.150, 2    # F5: the auditor's candidate definition (12r), not tuned bars
F5_CONTEXT_BESIDE_S = 0.100
GHOST_INTERVALS = (12, 19, 24)               # track 1's veto: an octave, a twelfth, two octaves above a paired note


def ms_confirms(note, ms, w=CONFIRM_S):
    """(Pure.) MuScriptor has an onset of the note's pitch within +-w of its onset."""
    return any(m["pitch"] == note["pitch"] and abs(m["on"] - note["on"]) <= w for m in ms)


def f2_ms_joins(notes, pairs, ms, w):
    """(Pure.) F2-MuScriptor at window `w`: the re-finds MuScriptor does not confirm (they join; nothing is deleted).
    -> set of j."""
    return {j for _, j in pairs if not ms_confirms(notes[j], ms, w)}


def _paired(bp, ms, w):
    """(Pure.) One-to-one pairs of Basic Pitch notes with MuScriptor's (same pitch, onsets within w, closest first).
    -> set of Basic Pitch indices."""
    cand = sorted((abs(a["on"] - b["on"]), i, j) for i, a in enumerate(bp) for j, b in enumerate(ms)
                  if a["pitch"] == b["pitch"] and abs(a["on"] - b["on"]) <= w)
    ui, uj = set(), set()
    for _, i, j in cand:
        if i not in ui and j not in uj:
            ui.add(i)
            uj.add(j)
    return ui


def f4_keep(bp, ms, below_s=F4_BELOW_S[0], intervals=GHOST_INTERVALS):
    """(Pure.) F4, `tx-veto`: every confirmed note kept, and every unconfirmed one unless a note in its onset group,
    confirmed within `below_s`, sits 12, 19 or 24 semitones below it. -> set of kept indices."""
    paired = _paired(bp, ms, CONFIRM_S)
    below_ok = _paired(bp, ms, below_s)
    keep = set()
    for g in NR.onset_groups(bp):
        below = {bp[k]["pitch"] for k in g if k in below_ok}
        for k in g:
            if k in paired or not any(bp[k]["pitch"] - p in intervals for p in below):
                keep.add(k)
    return keep


def f5_keep(bp, ms, ctx_s=F5_CONTEXT_S, count=F5_CONTEXT_COUNT):
    """(Pure.) F5, the context hybrid: a note MuScriptor confirms is kept; an unconfirmed one is dropped (the vote)
    unless MuScriptor has `count` or more onsets within +-`ctx_s` of it, where F4's veto decides. -> kept indices."""
    paired = _paired(bp, ms, CONFIRM_S)
    veto = f4_keep(bp, ms)
    keep = set()
    for k, n in enumerate(bp):
        dense = sum(abs(m["on"] - n["on"]) <= ctx_s for m in ms) >= count
        if k in paired or (dense and k in veto):
            keep.add(k)
    return keep


def kept_notes(bp, keep):
    return [dict(n) for k, n in enumerate(bp) if k in keep]


# --- applying the fixes ------------------------------------------------------------------------------------------------

FIX_KEYS = ("F1", "F2", "F3", "F6", "loud")   # "loud" is the build's loudness (`note_transcribe.build_loudness`),
                                              # read by the build, not a note transform: whitelisted, never applied here


def apply_fixes(notes, fixes, di=None, rate=NR.SR):
    """Fixes in order F1, F2, F3, F6 on a window's timed notes. fixes: {"F1": mode, "F2": theta, "F3": True, "F6":
    {K, gap, family, track, keep}}; an absent or falsy fix (F2, F6: None) is off. F2 needs the DI. F6 refuses to run
    without F1 `global` (12t: junction gaps are not invariant under `median`); a key outside FIX_KEYS is refused, never
    dropped silently. -> (notes, report)."""
    unknown = sorted(set(fixes) - set(FIX_KEYS))
    if unknown:
        raise ValueError(f"unknown fixes {unknown}: only {list(FIX_KEYS)}")
    if fixes.get("F6") is not None:
        f6_params(fixes["F6"])
        if fixes.get("F1") != "global":
            raise ValueError("F6 needs F1 global: junction gaps are not invariant under the median baseline")
    rep = {}
    if fixes.get("F1"):
        notes = rezero_bends(notes, fixes["F1"])
    if fixes.get("F2") is not None:
        pairs = refind_pairs(notes)
        changes = {j: band_change_db(di, notes[j], rate) for _, j in pairs}
        joins = f2_joins(pairs, changes, fixes["F2"])
        rep["F2"] = {"pairs": len(pairs), "joins": sorted(joins)}
        notes = join_refinds(notes, pairs, joins)
    if fixes.get("F3"):
        pairs = handoff_pairs(notes)
        rep["F3"] = {"pairs": pairs}
        notes = join_glides(notes, pairs)
    if fixes.get("F6") is not None:
        notes, rep["F6"] = apply_f6(notes, fixes["F6"])
    return notes, rep


def interval90(values):
    """(Pure.) Mean and two-sided 90% t interval over `values` (each window its own cluster). -> {mean, lo90, hi90,
    n} or None."""
    v = [x for x in values if x is not None and math.isfinite(x)]
    if not v:
        return None
    m = sum(v) / len(v)
    if len(v) < 2:
        return {"mean": m, "lo90": None, "hi90": None, "n": len(v)}
    from scipy import stats

    sd = statistics.stdev(v)
    h = stats.t.ppf(0.95, len(v) - 1) * sd / math.sqrt(len(v))
    return {"mean": m, "lo90": m - h, "hi90": m + h, "n": len(v)}


def wrap_cents(c):
    """(Pure.) Cents wrapped to -50..+50."""
    return (c + 50.0) % 100.0 - 50.0


# --- the isolation check (zero renders) --------------------------------------------------------------------------------

def windows_L_D():
    """L, the ten lists (their stored events, the bank's audio as DI), and D, the 19 development windows outside the ear
    page (`item_5` out, 12p), with Basic Pitch's notes, the DI and, on D, GOAT's annotation. -> (L, D, bank)."""
    from learn import note_transcribe as T
    from learn import song_bank as SB

    excl, tn, z, _ = T._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    pair = T.install_pair(T.load_manifest())
    known = {pp.stem.split("-", 1)[1]: pp for pp in (T.gate_work_dir() / "known").glob("*.json")}
    L = []
    for nm in sorted(T.KNOWN_NOTES):
        di = SB.measure(T.known_audio(nm, bank))
        est, _ = T.timed_notes({"events": json.loads(known[nm].read_text())["events"], "pre_s": 0.0}, di)
        L.append({"key": nm, "di": di, "notes": est, "truth": T.KNOWN_NOTES[nm]})
    D = []
    for w in T.read_dev_windows(T.dev_windows(z, excl, tn["items"])):
        if w["item"] in EAR_ITEMS:
            continue
        di = SB.measure(T.window_audio(T.goat_audio(z, w["item"]), w["start_s"])[0])
        est, _ = T.timed_notes(T.load_note("goat", w["item"], pair), di)
        D.append({"key": w["item"], "di": di, "notes": est,
                  "truth": T.dev_true_notes(w["item"], w["start_s"], di)})
    if len(D) != 19:
        raise SystemExit(f"{len(D)} windows in D, not 19")
    return L, D, bank


def rebuild(notes, di, bank, ring="ring-soft"):
    """`tr-di` as the redo builds a list's or a development window's (`song_bank.measure` finish, no loudness)."""
    import numpy as np

    from learn import song_bank as SB

    y, _ = NR.rebuild_redo("tr-di", notes, len(di), bank, di, ring, finish=SB.measure)
    return np.asarray(y, np.float64)


def matched(note, truth, onset_s=0.050):
    """(Pure.) The truth note of the same pitch with the nearest onset within `onset_s`, or None."""
    c = [t for t in truth if t["pitch"] == note["pitch"] and abs(t["on"] - note["on"]) <= onset_s]
    return min(c, key=lambda t: abs(t["on"] - note["on"])) if c else None


def window_figures(win, notes, bank):
    from learn import note_versions as NV

    y = rebuild(notes, win["di"], bank)
    return {"distance": NV.floored_logmel(win["di"], y),
            "tuning_c": wrap_cents(NR.global_tuning_cents(y) - NR.global_tuning_cents(win["di"]))}


def isolate(out_path):
    """Identity (the first build, byte for byte, with every fix off), then F1 alone (both modes), F3 on top of F1, and
    F2's DI-band candidate on top of F1 across its sweep, on L and D. Every figure with its interval. -> OUT.json."""
    import hashlib
    import io

    import numpy as np

    from learn import note_transcribe as T

    t0 = time.time()
    body = {"plan": "docs/note-rebuild-plan.md 12q", "ledger": f"{T.LEDGER_ID} {PHASE}", "renders": 0}
    # 1. identity: the first build's 47 parts and 7 ear items (item_5 out), both arms
    build = json.loads(T.build_path().read_text())
    ident = {"checked": 0, "mismatches": []}
    bank0 = NR.Bank(NR.load_notes_doc(), excl=NR.load_exclusion())
    for kind, key, info, rec, di, finish in T.build_todo():
        if kind == "ear" and key in T.RULED_OUT:
            continue
        notes, _ = T.timed_notes(rec, di)
        notes2, _ = apply_fixes(notes, {})
        rows = build["parts"] if kind == "part" else build["ear"]
        for arm in NR.REDO_ARMS:
            y, _ = NR.rebuild_redo(arm, notes2, len(di), bank0, di, build["ring_variant"], finish=finish,
                                   loud=build.get("loud_gamma"))
            buf = io.BytesIO()
            np.save(buf, np.asarray(y, np.float32))
            sha = hashlib.sha256(buf.getvalue()).hexdigest()
            ident["checked"] += 1
            if sha != rows[key]["arms"][arm]["sha256"]:
                ident["mismatches"].append(f"{kind}|{key}|{arm}")
    ident["identical"] = not ident["mismatches"]
    body["identity"] = ident
    body["identity_seconds"] = time.time() - t0
    L, D, bank = windows_L_D()
    base = {s: {w["key"]: window_figures(w, w["notes"], bank) for w in ws} for s, ws in (("L", L), ("D", D))}
    body["as_built"] = base

    def compare(fixed):
        out = {}
        for s in ("L", "D"):
            dd = [fixed[s][k]["distance"] - base[s][k]["distance"] for k in base[s]]
            out[s] = {"distance_less_as_built": interval90(dd),
                      "tuning_c_as_built": interval90([base[s][k]["tuning_c"] for k in base[s]]),
                      "tuning_c": interval90([fixed[s][k]["tuning_c"] for k in base[s]])}
        return out
    # 2. F1 alone, both modes
    f1 = {}
    for mode in F1_MODES:
        fig = {s: {w["key"]: window_figures(w, rezero_bends(w["notes"], mode), bank) for w in ws}
               for s, ws in (("L", L), ("D", D))}
        free = [w for w in L if w["key"] != "bend"]
        bend = next(w for w in L if w["key"] == "bend")
        held = []
        for t in bend["truth"]:
            if not any(t.get("bends") or []):
                continue
            nn = rezero_bends([n for n in bend["notes"] if matched(n, [t])], mode)
            curves = [NR.bend_curve(n, nn) for n in nn]
            tail = [v for c in curves for v in c[-20:]]
            held.append({"truth_steps": max(t["bends"]), "rebuilt_steps": statistics.median(tail) if tail else None})
        f1[mode] = {**compare(fig), "bent_share_bend_free_lists": {
            "as_built": bent_share([n for w in free for n in w["notes"]]),
            "fixed": bent_share([n for w in free for n in rezero_bends(w["notes"], mode)])},   # pooled alike
            "bend_list": held, "figures": fig}
    body["F1"] = f1
    # F1's mode: median less global per D window; an interval spanning zero is a tie, and the tie takes the global
    # step, the simpler rule (#584's review); F2 and F3 sit on top of the pick
    md = interval90([f1["median"]["figures"]["D"][k]["distance"] - f1["global"]["figures"]["D"][k]["distance"]
                     for k in base["D"]])
    tie = md is None or md["lo90"] is None or md["lo90"] <= 0 <= md["hi90"]
    pick = "global" if tie else ("median" if md["mean"] < 0 else "global")
    body["F1_pick"] = pick
    body["F1_median_less_global_D"] = {**(md or {}), "tie": tie}
    # 3. F3 on top of F1
    f3fig, f3joins = {}, {}
    for s, ws in (("L", L), ("D", D)):
        f3fig[s] = {}
        for w in ws:
            n1 = rezero_bends(w["notes"], pick)
            pairs = handoff_pairs(n1)
            n3 = join_glides(n1, pairs)
            f3fig[s][w["key"]] = window_figures(w, n3, bank)
            lab = []
            for i, j in pairs:
                tj = matched(n1[j], w["truth"])
                arts = set((tj or {}).get("arts") or [])
                lab.append("unannotated" if tj is None else ("annotated glide" if arts & LEGATO_ARTS else
                                                               "annotated pluck"))
            f3joins.setdefault(s, {})[w["key"]] = lab
    f1fig = f1[pick]["figures"]

    def over_f1(fig):
        return {s: interval90([fig[s][k]["distance"] - f1fig[s][k]["distance"] for k in base[s]]) for s in ("L", "D")}
    body["F3"] = {"distance_less_F1": over_f1(f3fig), "joins": f3joins,
                  "joins_by_label": {s: {lab: sum(v.count(lab) for v in f3joins[s].values())
                                         for lab in ("unannotated", "annotated glide", "annotated pluck")}
                                     for s in f3joins}, "figures": f3fig}
    # 4. F2's DI-band candidate on top of F1, across its sweep
    sweep = []
    prep = {}
    for s, ws in (("L", L), ("D", D)):
        for w in ws:
            n1 = rezero_bends(w["notes"], pick)
            pairs = refind_pairs(n1)
            prep[(s, w["key"])] = (n1, pairs, {j: band_change_db(w["di"], n1[j]) for _, j in pairs})
    for theta in F2_GRID_DB:
        row = {"theta_db": theta if math.isfinite(theta) else ("never" if theta < 0 else "always"), "D": {}, "L": {}}
        fig = {"L": {}, "D": {}}
        for s, ws in (("L", L), ("D", D)):
            counts = {"joined_matched": 0, "joined_unmatched": 0, "pairs": 0}
            for w in ws:
                n1, pairs, ch = prep[(s, w["key"])]
                joins = f2_joins(pairs, ch, theta)
                counts["pairs"] += len(pairs)
                for j in joins:
                    counts["joined_matched" if matched(n1[j], w["truth"]) else "joined_unmatched"] += 1
                fig[s][w["key"]] = window_figures(w, join_refinds(n1, pairs, joins), bank)
            row[s] = counts
        row["distance_less_F1"] = over_f1(fig)
        sweep.append(row)
    body["F2_band"] = {"sweep": sweep, "note": ("joined_matched: a joined re-find that matches a truth note (on D an "
                                                "annotated pick lost, on L a true note lost); joined_unmatched: a "
                                                "spurious re-pluck removed")}
    body["seconds"] = time.time() - t0
    NR.write_once(out_path, body)
    print(f"ISOLATE: identity {ident['identical']} ({ident['checked']} files); F1 pick {pick}; "
          f"{time.time() - t0:.0f} s -> {out_path}")


def chord_truth(truth):
    """(Pure.) The truth notes in onset groups of 3 or more (the chords). -> set of indices."""
    return {k for g in NR.onset_groups(truth) if len(g) >= 3 for k in g}


def matched_truth(notes, truth, onset_s=0.050):
    """(Pure.) The truth notes a note list matches one to one (same pitch, onsets within `onset_s`, closest first).
    -> set of truth indices."""
    cand = sorted((abs(t["on"] - n["on"]), i, j) for i, t in enumerate(truth) for j, n in enumerate(notes)
                  if t["pitch"] == n["pitch"] and abs(t["on"] - n["on"]) <= onset_s)
    ui, uj = set(), set()
    for _, i, j in cand:
        if i not in ui and j not in uj:
            ui.add(i)
            uj.add(j)
    return ui


def removal_counts(before, after, truth):
    """(Pure.) What a fix removed (dropped or joined away), against the truth: `lost`, truth notes matched before and
    no longer matched after (on D annotated picks, on L true notes; never over-counted); `removed`, the other notes
    gone; `chord_lost_proxy`, of the lost, the chord notes (a stand-in for real chord repicks lost)."""
    ch = chord_truth(truth)
    lost = matched_truth(before, truth) - matched_truth(after, truth)
    return {"lost": len(lost), "removed": max(0, (len(before) - len(after)) - len(lost)),
            "chord_lost_proxy": len(lost & ch)}


def chord_recall(notes, truth):
    """(Pure.) The share of the truth's chord notes a note list matches (same pitch, onsets within 50 ms)."""
    ch = chord_truth(truth)
    if not ch:
        return None
    return sum(any(n["pitch"] == truth[k]["pitch"] and abs(n["on"] - truth[k]["on"]) <= 0.050 for n in notes)
               for k in ch) / len(ch)


def muscriptor_notes(L, D):
    """MuScriptor's timed notes beside each L and D window (track 1's stage b and list screen, the picked size;
    `note_tx`'s own refusals: its install, its listing). Adds `ms` to each window."""
    from learn import note_transcribe as T
    from learn import note_tx as X

    m = X.require_tx(X.PHASE_GO, X.PHASE_INSTALL, X.PHASE_LISTS, X.PHASE_GO_READ, X.PHASE_NOTES)
    tx = m.get(X.LEDGER_ID) or {}
    _, sha = X.notes_listing(("truth", "goat", "goat-free"))          # as `note_tx read` checks it
    if (tx.get(X.PHASE_NOTES) or {}).get("listing_sha256") != sha:
        raise SystemExit(f"the note files are not main's {X.PHASE_NOTES} listing")
    size = X.picked_size(T.require_file_hash(tx, X.PHASE_LISTS, X.lists_path())["body"], tx.get(X.PHASE_GO_READ))
    inst = X.require_install(m, size)
    for w in L:
        w["ms"], _ = T.timed_notes(X.ms_events(X.load_ms(X.LIST_KINDS[size][0], w["key"], inst)), w["di"])
    for w in D:
        w["ms"], _ = T.timed_notes(X.ms_events(X.load_ms("goat", w["key"], inst)), w["di"])
    return size


def isolate_ms(out_path, f1_mode):
    """12r (zero renders): F2-MuScriptor at 50, 100 and 150 ms, F4 (the note below confirmed within 50, and 150
    beside) and F5 (the context hybrid, 150 ms and 2 onsets, 100 ms beside), each alone on top of F1 (`f1_mode`, the
    declared isolation's pick), on L and D: the distance less F1 with its 90% interval, the counts against the truth
    or the annotation, chord repicks or notes lost, chord-note recall on L. -> OUT.json."""
    t0 = time.time()
    L, D, bank = windows_L_D()
    size = muscriptor_notes(L, D)
    base = {s: {w["key"]: window_figures(w, rezero_bends(w["notes"], f1_mode), bank) for w in ws}
            for s, ws in (("L", L), ("D", D))}
    variants = [("F2-MuScriptor", f"w={int(w * 1000)}ms", w) for w in MS_JOIN_WINDOWS_S]
    variants += [("F4", f"below={int(b * 1000)}ms", b) for b in F4_BELOW_S]
    variants += [("F5", f"ctx={int(c * 1000)}ms,count={F5_CONTEXT_COUNT}", c) for c in (F5_CONTEXT_S, F5_CONTEXT_BESIDE_S)]
    rows = []
    for fix, label, par in variants:
        row = {"fix": fix, "point": label, "L": {"lost": 0, "removed": 0, "chord_lost_proxy": 0},
               "D": {"lost": 0, "removed": 0, "chord_lost_proxy": 0},
               "counts_label": "seen before the declaration" if fix in ("F2-MuScriptor", "F4") else None}
        fig = {"L": {}, "D": {}}
        chord = {"before": [], "after": []}
        for s, ws in (("L", L), ("D", D)):
            for w in ws:
                n1 = rezero_bends(w["notes"], f1_mode)
                if fix == "F2-MuScriptor":
                    pairs = refind_pairs(n1)
                    after = join_refinds(n1, pairs, f2_ms_joins(n1, pairs, w["ms"], par))
                elif fix == "F4":
                    after = kept_notes(n1, f4_keep(n1, w["ms"], below_s=par))
                else:
                    after = kept_notes(n1, f5_keep(n1, w["ms"], ctx_s=par))
                for k, v in removal_counts(n1, after, w["truth"]).items():
                    row[s][k] += v
                fig[s][w["key"]] = window_figures(w, after, bank)
                if s == "L":
                    chord["before"].append(chord_recall(n1, w["truth"]))
                    chord["after"].append(chord_recall(after, w["truth"]))
        row["distance_less_F1"] = {s: interval90([fig[s][k]["distance"] - base[s][k]["distance"] for k in base[s]])
                                   for s in ("L", "D")}
        pairs_ = [(a, b) for a, b in zip(chord["before"], chord["after"]) if a is not None and b is not None]
        row["chord_recall_L"] = {"F1": interval90([a for a, _ in pairs_]), "fixed": interval90([b for _, b in pairs_]),
                                 "fixed_less_F1": interval90([b - a for a, b in pairs_])}
        row["figures"] = fig
        rows.append(row)
    body = {"plan": "docs/note-rebuild-plan.md 12r", "ledger": "note-rebuild phase_nr_1_redo_fixes_ms", "renders": 0,
            "f1_mode": f1_mode, "muscriptor_size": size, "F1_figures": base, "rows": rows,
            "seconds": time.time() - t0}
    NR.write_once(out_path, body)
    print(f"ISOLATE-MS on F1 {f1_mode}: {len(rows)} variants; {time.time() - t0:.0f} s -> {out_path}")


GAMMA_GRID = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)   # R3's measurement grid for the loudness gamma (off beside); extended
                                              # upward by doubling its top while the minimum sits there, so it brackets
                                              # the minimum; a safety stop at 12 points, recorded as bracketed: false
GAMMA_GRID_MAX = 12
KEPT_KEYS = ("F1", "F2ms", "F4", "F5")


def kept_transform(notes, ms, kept):
    """(Pure.) The kept fixes in order on a window's notes: F1 (`kept["F1"]`, a mode), then F2-MuScriptor
    (`kept["F2ms"]`, a window in s) joins, then F4 (`kept["F4"]`, its below window) or F5 (`kept["F5"]`, its
    context) drops. An absent key is off; any other key (`F2`, the band, or `F3`) is refused, never dropped silently.
    -> notes."""
    unknown = sorted(set(kept) - set(KEPT_KEYS))
    if unknown:
        raise ValueError(f"unknown kept fixes {unknown}: only {list(KEPT_KEYS)}")
    n = rezero_bends(notes, kept.get("F1"))
    if kept.get("F2ms"):
        pairs = refind_pairs(n)
        n = join_refinds(n, pairs, f2_ms_joins(n, pairs, ms, kept["F2ms"]))
    if kept.get("F5"):
        n = kept_notes(n, f5_keep(n, ms, ctx_s=kept["F5"]))
    elif kept.get("F4"):
        n = kept_notes(n, f4_keep(n, ms, below_s=kept["F4"]))
    return n


def combine(out_path, kept):
    """12q step 6 and R3 (zero renders): the kept fixes together on D (L beside), against F1 alone and against as
    built, then on top of them the ring variant (ring-soft against ring-on, `envelope_corr` beside) and the loudness
    gamma (off, then GAMMA_GRID, extended while the minimum sits at its top), each picked on D by the distance;
    an interval spanning zero keeps the as-built choice (ring-soft, no loudness). E is not read here. -> OUT.json."""
    import numpy as np

    from learn import note_versions as NV
    from learn import song_bank as SB

    t0 = time.time()
    kept_transform([], [], kept)                          # refuses an unknown key before any work
    L, D, bank = windows_L_D()
    needs_ms = any(kept.get(k) for k in ("F2ms", "F4", "F5"))
    if needs_ms:
        muscriptor_notes(L, D)

    def fig(w, notes, ring="ring-soft", loud=None):
        y, _ = NR.rebuild_redo("tr-di", notes, len(w["di"]), bank, w["di"], ring, finish=SB.measure, loud=loud)
        y = np.asarray(y, np.float64)
        return {"distance": NV.floored_logmel(w["di"], y), "env": NR.envelope_corr(np.asarray(w["di"]), y)}
    notes = {s: {w["key"]: kept_transform(w["notes"], w.get("ms") or [], kept) for w in ws}
             for s, ws in (("L", L), ("D", D))}
    asb = {s: {w["key"]: fig(w, w["notes"]) for w in ws} for s, ws in (("L", L), ("D", D))}
    f1 = {s: {w["key"]: fig(w, rezero_bends(w["notes"], kept.get("F1"))) for w in ws} for s, ws in (("L", L), ("D", D))}
    comb = {s: {w["key"]: fig(w, notes[s][w["key"]]) for w in ws} for s, ws in (("L", L), ("D", D))}

    def diff(a, b, key="distance"):
        return {s: interval90([a[s][k][key] - b[s][k][key] for k in a[s]]) for s in ("L", "D")}
    body = {"plan": "docs/note-rebuild-plan.md 12q step 6, R3", "renders": 0, "kept": kept,
            "combined_less_as_built": diff(comb, asb), "combined_less_F1": diff(comb, f1)}
    # R3: the ring variant on the combined notes
    on = {s: {w["key"]: fig(w, notes[s][w["key"]], ring="ring-on") for w in ws} for s, ws in (("L", L), ("D", D))}
    rd = diff(on, comb)
    body["ring"] = {"ring_on_less_soft": rd, "env_on_less_soft": diff(on, comb, "env")}
    spans = rd["D"] is None or rd["D"]["lo90"] is None or rd["D"]["lo90"] <= 0 <= rd["D"]["hi90"]
    ring = "ring-soft" if spans or rd["D"]["mean"] > 0 else "ring-on"
    body["ring"]["pick"] = ring
    body["ring"]["label"] = "undecided, the as-built ring-soft kept" if spans else None
    body["ring"]["optimistic"] = ("picked and read on the same D: its interval is optimistic; E is the held-out "
                                  "check")
    base = comb if ring == "ring-soft" else on
    # R3: the loudness gamma on the picked ring
    grid, rows = list(GAMMA_GRID), {}
    while True:
        for g in grid:
            if g in rows:
                continue
            gf = {s: {w["key"]: fig(w, notes[s][w["key"]], ring=ring, loud=g) for w in ws}
                  for s, ws in (("L", L), ("D", D))}
            rows[g] = diff(gf, base)
        best = min(rows, key=lambda g: rows[g]["D"]["mean"])
        if best == max(grid) and len(grid) < GAMMA_GRID_MAX:
            grid.append(max(grid) * 2)
            continue
        break
    bracketed = best != max(grid)
    bd = rows[best]["D"]
    spans_g = bd["lo90"] is None or bd["lo90"] <= 0 <= bd["hi90"] or bd["mean"] > 0
    body["gamma"] = {"grid": grid, "less_off": {str(g): r for g, r in sorted(rows.items())}, "lowest": best,
                     "bracketed": bracketed, "pick": None if spans_g else best,
                     "label": "undecided, no loudness kept (as built)" if spans_g else None,
                     "optimistic": "picked and read on the same D: its interval is optimistic; E is the held-out check",
                     "grid_rule": ("doubling the top while the minimum sits there, a safety stop at "
                                   f"{GAMMA_GRID_MAX} points (bracketed: false when it is hit)")}
    body["seconds"] = time.time() - t0
    NR.write_once(out_path, body)
    print(f"COMBINE {kept}: ring {ring}, gamma {body['gamma']['pick']}; {time.time() - t0:.0f} s -> {out_path}")


def clamp_binding(notes, raw_counts):
    """(Pure.) 12q R4: how often the synthesis clamps act on a window's notes, from the notes alone: the bend cap
    (a note whose re-zeroed track passes +-BEND_MAX_SEMITONES), the 2-semitone clear rule (a note with a frame it
    zeroes), the onset snap (`timed_notes`' snapped groups) and the clean-up's MIDI range, octave-up and six-at-once
    counts. -> {clamp: (acting, of)}. The level, oracle and tilt clamps act inside the synthesis: not counted here."""
    cap = NR.BEND_MAX_SEMITONES * NR.BEND_STEPS_PER_SEMITONE
    capped = sum(any(abs(float(v)) > cap for v in (n.get("bends") or [])) for n in notes)
    cleared = 0
    for n in notes:
        b = n.get("bends") or []
        if any(m is not n and abs(m["pitch"] - n["pitch"]) <= NR.BEND_CLEAR_SEMITONES
               and m["on"] <= n["on"] + j * NR.BEND_FRAME_S < m["off"] for m in notes for j in range(len(b))):
            cleared += 1
    raw = len(notes) + sum(raw_counts.get(k, 0) for k in ("out_of_range", "over_six"))
    return {"bend_cap": (capped, len(notes)), "clear_rule": (cleared, len(notes)),
            "snap": (raw_counts.get("snapped", 0), raw_counts.get("groups", 0)),
            "midi_range": (raw_counts.get("out_of_range", 0), raw), "octave_up": (raw_counts.get("octave_up", 0), raw),
            "six_at_once": (raw_counts.get("over_six", 0), raw)}


def clamps(out_path):
    """12q R4 (zero renders): the clamps' binding on the 47 parts, D and E, the bend cap and clear rule after F1
    (the median mode; the global read beside), pooled per set. -> OUT.json."""
    from learn import note_transcribe as T

    excl, tn, z, _ = T._dev_context()
    body = {"plan": "docs/note-rebuild-plan.md 12q R4", "renders": 0, "sets": {}}
    sets = {"parts": [], "E": []}
    for kind, key, info, rec, di, finish in T.build_todo():
        if kind == "ear" and key in T.RULED_OUT:
            continue
        sets["parts" if kind == "part" else "E"].append((rec, di))
    pair = T.install_pair(T.load_manifest())
    from learn import song_bank as SB
    sets["D"] = []
    for w in T.read_dev_windows(T.dev_windows(z, excl, tn["items"])):
        if w["item"] in EAR_ITEMS:
            continue
        di = SB.measure(T.window_audio(T.goat_audio(z, w["item"]), w["start_s"])[0])
        sets["D"].append((T.load_note("goat", w["item"], pair), di))
    for st, items in sets.items():
        tot = {}
        for mode in (None, "median", "global"):
            acc = {}
            for rec, di in items:
                notes, rep = T.timed_notes(rec, di)
                for k, (a, b) in clamp_binding(rezero_bends(notes, mode), rep).items():
                    x = acc.setdefault(k, [0, 0])
                    x[0] += a
                    x[1] += b
            tot[mode or "as_built"] = {k: {"acting": a, "of": b, "share": a / b if b else None}
                                       for k, (a, b) in acc.items()}
        body["sets"][st] = {"windows": len(items), **tot}
    NR.write_once(out_path, body)
    print(f"CLAMPS -> {out_path}")


# --- F6's instruments (12t): the bend lists B, the bend windows Db, the L `bend` re-truth ------------------------------

FIXES_DIR = NR.OUT / "redo" / "fixes"
BEND_DIR = FIXES_DIR / "bend"             # B's and Db's note files, each written once (`bend-lists`, `bend-windows`)
BEND_STEP_S = 2.4                         # B: one instance every 2.4 s from 0.5 s, four to a list
BEND_NOTE_S = 1.6                         # a bent note's (and a held note's) length
BEND_RISE_AT_S, BEND_RISE_FRAMES = 0.25, 18   # a bend rises 0.25 s after its pluck, over 18 frames (0.21 s)
BEND_RELEASE_AT_S = 0.85                  # the solo bend's release starts 0.85 s after its pluck, over 18 frames
ONSET_S = 0.050                           # `note_transcribe.match_notes`' onset tolerance (KNOWN_ONSET_S)


def bend_track(target, dur_s, rise_at_s=BEND_RISE_AT_S, rise_frames=BEND_RISE_FRAMES, fall_at_s=None,
               fall_frames=BEND_RISE_FRAMES):
    """(Pure.) A true bend track in whole steps per frame, spanning the note and ring-soft's 150-ms release (12t: B's
    tracks cover the full note plus the release): 0, then an integer staircase up to `target` over `rise_frames`, held;
    with `fall_at_s`, back down to 0 over `fall_frames` and held at 0. Monotone integer runs, so `bend_curve` plays it
    unchanged (its median, clamp and five-frame rule leave it as it is; tested)."""
    F = NR.BEND_FRAME_S
    n = int(math.ceil((dur_s + NR.RING_SOFT_S) / F))
    q0 = int(round(rise_at_s / F))
    q1 = None if fall_at_s is None else int(round(fall_at_s / F))
    out = []
    for q in range(n):
        v = 0 if q < q0 else (((q - q0) * target) // rise_frames if q < q0 + rise_frames else target)
        if q1 is not None and q >= q1:
            v = target - ((q - q1) * target) // fall_frames if q < q1 + fall_frames else 0
        out.append(v)
    return out


def _bent(on, pitch, target, **kw):
    return {"on": on, "off": on + BEND_NOTE_S, "pitch": pitch, "bends": bend_track(target, BEND_NOTE_S, **kw),
            "keep_bend": True}


def _held(on, pitch, off=None):
    return {"on": on, "off": on + BEND_NOTE_S if off is None else off, "pitch": pitch, "bends": []}


def _run(t0, pitches, step):
    return [{"on": t0 + k * step, "off": t0 + (k + 1) * step, "pitch": p, "bends": []} for k, p in enumerate(pitches)]


def _instances(make, pitches):
    out = []
    for j, p in enumerate(pitches):
        out += make(0.5 + BEND_STEP_S * j, p)
    return sorted(out, key=lambda n: (n["on"], n["pitch"]))


BEND_POSITIVES = ("bend-fourth-above", "bend-unison", "bend-picked-during", "bend-held-below", "bend-release",
                  "bend-half-step-held", "bend-under-semitone-held")
BEND_CONTROLS = ("steps-over-held", "chromatic-over-held", "let-ring-semitones")
BEND_LISTS = {   # B (12t): made-up lists played from the bank; each true bent note carries `keep_bend`
    # positives
    "bend-fourth-above": _instances(lambda t, p: [_bent(t, p, 6), _held(t, p + 5)], (57, 59, 62, 64)),
    "bend-unison": _instances(lambda t, p: [_bent(t, p - 2, 6), _held(t, p)], (59, 62, 64, 67)),
    "bend-picked-during": _instances(lambda t, p: [_bent(t, p, 6), _held(t + 0.7, p + 5, t + BEND_NOTE_S)],
                                     (57, 59, 62, 64)),
    "bend-held-below": _instances(lambda t, p: [_bent(t, p, 6), _held(t, p - 5)], (59, 62, 64, 67)),
    "bend-release": _instances(lambda t, p: [_bent(t, p, 6, fall_at_s=BEND_RELEASE_AT_S)], (57, 59, 62, 64)),
    "bend-half-step-held": _instances(lambda t, p: [_bent(t, p, 3), _held(t, p + 5)], (57, 59, 62, 64)),
    "bend-under-semitone-held": _instances(lambda t, p: [_bent(t, p, 2), _held(t, p + 2)], (57, 59, 62, 64)),
    # controls: bend-free, so every join is false
    "steps-over-held": _instances(lambda t, p: [_held(t, p - 7, t + 2.0)] + _run(t, [p, p + 1, p + 3, p + 2, p + 4,
                                                                                    p + 2], 0.3), (60, 62, 57, 64)),
    "chromatic-over-held": _instances(lambda t, p: [_held(t, p - 5, t + 1.4)] + _run(t, range(p, p + 7), 0.2),
                                      (57, 60, 62, 55)),
    "let-ring-semitones": _instances(lambda t, p: [_held(t + 0.4 * k, p + k, t + 0.4 * k + 1.2) for k in range(3)],
                                     (57, 60, 62, 64)),
}


def bend_audio(name, bank, rate=NR.SR):
    """A bend list played from the bank as the rebuild plays (`synthesise_redo`, ring-soft, so each true track covers
    the note and its release; no cut, mutes or tilt), at -22.9 LUFS, 10.25 s."""
    from learn import pretrain_set as PS

    n = int(round((PS.SEC_S + PS.TRIM_S) * rate))
    y, _ = NR.synthesise_redo(BEND_LISTS[name], n, bank, 0.0, "ring-soft", (), 0.0, None, rate)
    return NR.at_lufs(y, NR.ASSUMED_LUFS, rate)


def bend_retruth(truth):
    """(Pure.) L's `bend` list re-truthed (12t): each bent true track extended with zeros to its note-off, which is what
    its audio does (the track ends 0.36 s early). Reported beside only: amendment A scores the list up to each true
    track's end and never uses the re-truth for deciding."""
    F = NR.BEND_FRAME_S
    out = []
    for n in truth:
        b = note_track(n)
        if any(b):
            b = b + [0.0] * max(0, int(math.ceil((n["off"] - n["on"]) / F)) - len(b))
        out.append(dict(n, bends=b))
    return out


def l_bend_excluded(truth, onset_s=ONSET_S):
    """(Pure.) Amendment A's unscored spans on L's `bend` list: from each bent true track's end, less the matcher's
    onset tolerance, to its note-off. A rebuilt onset there is the artefact step-back's, never scored."""
    F = NR.BEND_FRAME_S
    return [(n["on"] + len(n["bends"]) * F - onset_s, n["off"]) for n in truth if any(n.get("bends") or [])]


def db_windows(bend_ons, d_start, duration_s, length_s, grid_s=5.0, full=None):
    """(Pure.) Db's windows on one item (12t, filled in at declaration): candidate starts on the 5-s grid (the ear
    items' GRID_S) with the whole window inside the item and not overlapping the item's D window; each holds the
    annotated bends with onsets inside it; picked greedily, the candidate holding the most bends not yet held (a tie:
    the earlier start), never overlapping one picked, until none adds a bend. -> [(start, [bend onsets])]."""
    full = full or (lambda st: st + length_s <= duration_s)
    cands = []
    k = 0
    while k * grid_s + length_s <= duration_s + 1e-9:
        st = k * grid_s
        k += 1
        if not full(st) or (st < d_start + length_s and d_start < st + length_s):
            continue
        cands.append((st, [b for b in bend_ons if st <= b < st + length_s]))
    picked, held = [], set()
    while True:
        best = None
        for st, bs in cands:
            new = len(set(bs) - held)
            if not new or any(st < p + length_s and p < st + length_s for p, _ in picked):
                continue
            if best is None or new > best[0]:
                best = (new, st, bs)
        if best is None:
            return sorted(picked)
        picked.append((best[1], best[2]))
        held |= set(best[2])


# --- F6's measures (12t; pure) --------------------------------------------------------------------------------------

def note_pairs(truth, notes, onset_s=ONSET_S):
    """(Pure.) `match_notes`' one-to-one matching (same pitch, onsets within `onset_s`, the closest first).
    -> {truth index: note index}."""
    cand = sorted((abs(t["on"] - n["on"]), i, j) for i, t in enumerate(truth) for j, n in enumerate(notes)
                  if t["pitch"] == n["pitch"] and abs(t["on"] - n["on"]) <= onset_s)
    ui, uj = {}, set()
    for _, i, j in cand:
        if i not in ui and j not in uj:
            ui[i] = j
            uj.add(j)
    return ui


def scored_notes(notes, excluded=()):
    """(Pure.) The notes whose onset lies in no excluded span (amendment A)."""
    return [n for n in notes if not any(a <= n["on"] < b for a, b in excluded)]


def note_error(truth, notes, excluded=()):
    """(Pure.) 12t's note error: rebuilt notes matching no true note plus true notes matching no rebuilt note, every
    note the same weight. -> {lost, extra, error}."""
    s = scored_notes(notes, excluded)
    m = len(note_pairs(truth, s))
    return {"lost": len(truth) - m, "extra": len(s) - m, "error": len(truth) + len(s) - 2 * m}


def bent_truth(truth):
    return [i for i, t in enumerate(truth) if any(note_track(t))]


def played_steps(n, curve, t):
    """(Pure.) A rebuilt note's absolute pitch in bins at time t as played: 3 x pitch + its curve's frame (0 past the
    curve's end, as `apply_bend`)."""
    q = int(math.floor((t - n["on"]) / NR.BEND_FRAME_S))
    return 3.0 * n["pitch"] + (curve[q] if 0 <= q < len(curve) else 0.0)


def bend_error(truth, notes, excluded=()):
    """(Pure.) 12t's bend error. For each frame of a true bent note (its centre): truth 3 x pitch + true track; rebuilt,
    the absolute pitch as played after `bend_curve` of the rebuilt note sounding then (its onset to its note-off plus
    ring-soft's release) nearest the truth, not matched to another true note. -> {mean_abs_bins, frames, empty_share,
    release: the same over frames past the true note-off}."""
    F = NR.BEND_FRAME_S
    s = scored_notes(notes, excluded)
    owner = {j: i for i, j in note_pairs(truth, s).items()}
    curves = [NR.bend_curve(n, s) for n in s]
    acc = {"all": [0.0, 0, 0], "release": [0.0, 0, 0]}
    for ti in bent_truth(truth):
        t = truth[ti]
        for q, v in enumerate(note_track(t)):
            tc = t["on"] + (q + 0.5) * F
            want = 3.0 * t["pitch"] + v
            errs = [abs(played_steps(s[k], curves[k], tc) - want) for k, n in enumerate(s)
                    if owner.get(k, ti) == ti and n["on"] <= tc < n["off"] + NR.RING_SOFT_S]
            for key in ("all",) + (("release",) if tc >= t["off"] else ()):
                a = acc[key]
                if errs:
                    a[0] += min(errs)
                    a[1] += 1
                else:
                    a[2] += 1

    def fig(a):
        n = a[1] + a[2]
        return {"mean_abs_bins": a[0] / a[1] if a[1] else None, "frames": n, "empty_share": a[2] / n if n else None}
    return {**fig(acc["all"]), "release": fig(acc["release"])}


def extra_attacks(truth, notes, excluded=()):
    """(Pure.) Per true bent note, the rebuilt onsets inside its track's span that match no true note (12t: a
    staircase's "split" half). -> [count per bent true note]."""
    F = NR.BEND_FRAME_S
    s = scored_notes(notes, excluded)
    used = set(note_pairs(truth, s).values())
    return [sum(1 for k, n in enumerate(s) if k not in used
                and truth[ti]["on"] <= n["on"] < truth[ti]["on"] + len(note_track(truth[ti])) * F)
            for ti in bent_truth(truth)]


def second_lost(truth, notes, excluded=()):
    """(Pure.) Amendment E: a positive's other true notes (not bent) that no rebuilt note matches."""
    s = scored_notes(notes, excluded)
    got = note_pairs(truth, s)
    bent = set(bent_truth(truth))
    return sum(1 for i in range(len(truth)) if i not in bent and i not in got)


def bent_but_cleared(notes, skip=()):
    """(Pure.) The notes (outside `skip`, the stitched heads) the clear rule takes a bend from: their curve alone bends
    on a frame that `bend_curve` against the window's notes zeroes. -> [indices]."""
    out = []
    for k, n in enumerate(notes):
        if k in skip:
            continue
        alone = NR.bend_curve(n, ())
        if any(alone):
            played = NR.bend_curve(n, notes)
            if any(a and not b for a, b in zip(alone, played)):
                out.append(k)
    return out


def ends_bent(notes):
    """(Pure.) The notes whose curve as played ends bent (the release then drops back to the note's pitch)."""
    return sum(1 for n in notes if (lambda c: bool(c) and c[-1] != 0)(NR.bend_curve(n, notes)))


def stitched_heads(n_before, chains):
    """(Pure.) The stitched notes' indices in `f6_stitch`'s output, from the input's length and the chains."""
    drop = {m for c in chains for m in c[1:]}
    heads = {c[0] for c in chains}
    out, pos = set(), 0
    for k in range(n_before):
        if k in drop:
            continue
        if k in heads:
            out.add(pos)
        pos += 1
    return out


def annotated_fragments(truth, notes):
    """(Pure.) Db's and E's split read on annotated bends (the annotation carries no track): per annotated bend, the
    rebuilt notes matching no annotated note whose onsets fall inside its span (after its onset, to its note-off) at 1
    to 3 semitones from its pitch. -> {bends, fragmented (bends with one or more), fragments}."""
    used = set(note_pairs(truth, notes).values())
    per = []
    for t in truth:
        if "bend" not in (t.get("arts") or []):
            continue
        per.append(sum(1 for k, n in enumerate(notes) if k not in used and t["on"] < n["on"] < t["off"]
                       and F6_SEMITONES[0] <= abs(n["pitch"] - t["pitch"]) <= F6_SEMITONES[1]))
    return {"bends": len(per), "fragmented": sum(1 for x in per if x), "fragments": sum(per)}


def art_label(note, truth):
    """(Pure.) A note's articulation by the annotated truth note it matches (same pitch, onset within 50 ms):
    `hammer`, `slide`, `bend` (joined by + when several), `pluck` (none of them), or `unannotated` (no match)."""
    t = matched(note, truth)
    if t is None:
        return "unannotated"
    a = sorted(set(t.get("arts") or []) & LEGATO_ARTS)
    return "+".join(a) if a else "pluck"


def join_labels(n1, chains, truth, annotated):
    """(Pure.) Each join (a chain member joined into its predecessor): the interval in semitones, and either the
    articulation of the joined-away note and of the chain head (`annotated`, D and Db) or whether the joined-away
    note is a true note (`true note`, a false join) or not (`fragment`). -> [{interval, joined, head}]."""
    out = []
    for c in chains:
        for a, b in zip(c, c[1:]):
            if annotated:
                lab = {"joined": art_label(n1[b], truth), "head": art_label(n1[c[0]], truth)}
            else:
                lab = {"joined": "true note" if matched(n1[b], truth) else "fragment"}
            out.append({"interval": abs(n1[b]["pitch"] - n1[a]["pitch"]), **lab})
    return out


def fault_kinds(truth, notes):
    """(Pure.) B's fault as built (F1 only), per true bent note: `missed` (no rebuilt note matches it), `split` (an
    extra attack inside its span), else unsplit: `cleared` (the clear rule takes bend from its note), `bent` (it plays
    a bend), `flat` (its note's track shows none). -> {kind: count}."""
    got = note_pairs(truth, notes)
    xa = extra_attacks(truth, notes)
    cleared = set(bent_but_cleared(notes))
    out = {k: 0 for k in ("missed", "split", "cleared", "bent", "flat")}
    for ti, x in zip(bent_truth(truth), xa):
        if ti not in got:
            kind = "split" if x else "missed"
        elif x:
            kind = "split"
        elif got[ti] in cleared:
            kind = "cleared"
        else:
            kind = "bent" if any(NR.bend_curve(notes[got[ti]], notes)) else "flat"
        out[kind] += 1
    return out


def ladder_rungs(truth):
    """(Pure.) The bend ladder (12t, inside `isolate-bend`): the true notes (bent ones kept); bends flattened; bends as
    re-plucked steps (each bent note cut into one note per run of its played semitone, no bends). -> {rung: notes}."""
    F = NR.BEND_FRAME_S
    flat = [{k: v for k, v in dict(n, bends=[]).items() if k != "keep_bend"} for n in truth]
    steps = []
    for n in truth:
        b = note_track(n)
        if not any(b):
            steps.append(dict(n))
            continue
        runs, q = [], 0
        semis = [int(round(v / NR.BEND_STEPS_PER_SEMITONE)) for v in b]
        while q < len(semis):
            r = q
            while r < len(semis) and semis[r] == semis[q]:
                r += 1
            runs.append((q, r, semis[q]))
            q = r
        for a, (q0, q1, s) in enumerate(runs):
            on = n["on"] + q0 * F
            if on >= n["off"]:
                break
            off = n["off"] if a == len(runs) - 1 or n["on"] + q1 * F >= n["off"] else n["on"] + q1 * F
            steps.append({"on": on, "off": off, "pitch": n["pitch"] + s, "amp": n.get("amp", 0.5), "bends": []})
    return {"true": [dict(n) for n in truth], "flattened": flat,
            "steps": sorted(steps, key=lambda n: (n["on"], n["pitch"]))}


def clopper_pearson(k, n, conf=0.90):
    """Clopper-Pearson interval for k of n. -> {k, n, share, lo90, hi90} or None without n."""
    if not n:
        return None
    from scipy import stats

    a = (1 - conf) / 2
    lo = 0.0 if k == 0 else float(stats.beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - a, k + 1, n - k))
    return {"k": k, "n": n, "share": k / n, "lo90": lo, "hi90": hi}


def spans_zero(iv):
    """(Pure.) A tie (12t): no interval, or a 90% interval holding zero."""
    return iv is None or iv.get("lo90") is None or iv["lo90"] <= 0 <= iv["hi90"]


def point_key(pt):
    fam, k, gap = pt
    return f"{fam}|K={k}|gap<={gap}"


def simpler_key(pt, free_joins):
    """(Pure.) 12t's order on tied points, B2's wording: first the declared harm step (fewer joins on bend-free
    material), then sequential pairs only, then the smaller gap, then K by the preference 3, 5, 1."""
    fam, k, gap = pt
    return (free_joins[pt], fam != "sequential", gap, F6_K_PREFERENCE.index(k))


def pick_point(ne, free_joins):
    """(Pure.) 12t's grid pick with amendment B1. ne: {point: {list: note error}} on the deciding lists (B and L's
    `bend`); free_joins: {point: joins on bend-free material}. The minimum summed note error (a tie in the sum by the
    order below); the candidates, every point whose paired difference against it (by list, `interval90`) spans zero;
    the pick, the first candidate by `simpler_key`. -> {minimum, candidates, pick, less_minimum}."""
    tot = {pt: sum(v.values()) for pt, v in ne.items()}
    best = min(ne, key=lambda pt: (tot[pt], simpler_key(pt, free_joins)))
    lists = sorted(ne[best])
    diffs = {pt: interval90([ne[pt][c] - ne[best][c] for c in lists]) for pt in ne}
    cands = [pt for pt in ne if pt == best or spans_zero(diffs[pt])]
    return {"minimum": best, "candidates": cands, "pick": min(cands, key=lambda pt: simpler_key(pt, free_joins)),
            "less_minimum": diffs, "summed": tot}


def pick_track_keep(be):
    """(Pure.) 12t's track and keep: be: {(track, keep): {list: mean bend error}} at the picked point. The lowest mean
    over the lists; the candidates, every combination whose paired difference against it spans zero; a tie takes the
    members' own tracks, then "cleared" (today's synthesis). -> {minimum, candidates, pick, less_minimum}."""
    def pref(tk):
        return (tk[0] != "own", tk[1])

    def mean(tk):
        v = [x for x in be[tk].values() if x is not None]
        return sum(v) / len(v) if v else math.inf
    best = min(be, key=lambda tk: (mean(tk), pref(tk)))
    diffs = {}
    for tk in be:
        lists = [c for c in be[best] if be[best][c] is not None and be[tk].get(c) is not None]
        diffs[tk] = interval90([be[tk][c] - be[best][c] for c in lists])
    cands = [tk for tk in be if tk == best or spans_zero(diffs[tk])]
    return {"minimum": best, "candidates": cands, "pick": min(cands, key=pref), "less_minimum": diffs}


def keep_call(deciding, harm):
    """(Pure.) Amendment B3. deciding: the picked point's note error less F1-only's on B and L's `bend` (an interval);
    harm: {set: the same difference on L's nine bend-free lists, B's controls, Guitar-TECHS}. Kept: the deciding
    interval below zero and no harm interval above zero; not kept: the deciding interval above zero or any harm
    interval above zero; otherwise undecided (the ear page then decides if `tr-di` differs on a faulted card's item)."""
    above = [s for s, iv in harm.items() if iv is not None and iv.get("lo90") is not None and iv["lo90"] > 0]
    if above or (deciding and deciding.get("lo90") is not None and deciding["lo90"] > 0):
        return {"call": "not kept", "harm_above_zero": above}
    if deciding and deciding.get("hi90") is not None and deciding["hi90"] < 0:
        return {"call": "kept", "harm_above_zero": []}
    return {"call": "undecided", "harm_above_zero": []}


# --- F6's commands (zero renders) -------------------------------------------------------------------------------------

def run_label(declared):
    """The run's ledger view and label: the declared run refuses off main (`note_transcribe.redo_on_main`, amendment
    D2); a branch run reads this checkout's ledger and is labelled preliminary. -> (entries, label, head sha)."""
    import subprocess

    from learn import note_transcribe as T

    head = subprocess.run(["git", "-C", str(NR.REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if declared:
        m, why = T.redo_on_main()
        if why:
            raise SystemExit(why)
        return m, "declared (merged main)", head
    return T.entries((NR.REPO / "docs" / "dev-test-ledger.json").read_text()), "preliminary (branch)", head


def cmd_bend_lists(_args):
    """12t phase 2 (zero renders): B's ten lists played from the bank (`bend_audio`) and transcribed in one Basic
    Pitch process; each note file written once under fixes/bend/lists/, its listing (each file's, its audio's and
    its truth's sha256) in fixes/bend/lists.json, hashed into the ledger as phase_nr_1_redo_bend_lists before a
    declared run reads them."""
    from learn import note_transcribe as T
    from learn import pretrain_set as PS

    if PS.free_gb() < 31.0:
        raise SystemExit("DISK GUARD: free disk below 31 GB")
    listing = BEND_DIR / "lists.json"
    T.never_overwrite(listing)
    T.never_overwrite(BEND_DIR / "work" / "lists")
    excl, _, _, _ = T._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    names = sorted(BEND_LISTS)
    audio = {nm: bend_audio(nm, bank) for nm in names}
    bp = T.run_bp([(audio[nm], nm) for nm in names], BEND_DIR / "work" / "lists")
    rows = {}
    for nm, r in zip(names, bp):
        p = BEND_DIR / "lists" / f"{nm}.json"
        NR.write_once(p, T.note_record(r, 0.0, {"bend_list": nm}))
        rows[nm] = {"note_sha256": NR.file_sha(p), "audio_sha256": NR.bytes_sha(audio[nm].astype("float64").tobytes()),
                    "truth_sha256": NR.content_sha(BEND_LISTS[nm]), "events": len(r["events"])}
    NR.write_once(listing, {"plan": "docs/note-rebuild-plan.md 12t", "ledger": f"{NR.LEDGER_ID} {PHASE_F6_LISTS}",
                            "renders": 0, "positives": list(BEND_POSITIVES), "controls": list(BEND_CONTROLS),
                            "lists": rows})
    print(f"BEND-LISTS: {len(rows)} lists; lists.json sha256 {NR.file_sha(listing)} (into the ledger as "
          f"{PHASE_F6_LISTS})")


def d_items_windows():
    """D's 19 windows ({item, start_s}) without reading audio."""
    from learn import note_transcribe as T

    excl, tn, z, _ = T._dev_context()
    return [w for w in T.read_dev_windows(T.dev_windows(z, excl, tn["items"])) if w["item"] not in EAR_ITEMS], z


def cmd_bend_windows(_args):
    """12t phase 2 (zero renders): Db, windows on D's items holding annotated bends outside their D windows
    (`db_windows`), transcribed in one Basic Pitch process; each note file written once under fixes/bend/windows/,
    the listing in fixes/bend/windows.json (hashed with the lists into phase_nr_1_redo_bend_lists)."""
    from learn import note_transcribe as T
    from learn import pretrain_set as PS

    if PS.free_gb() < 31.0:
        raise SystemExit("DISK GUARD: free disk below 31 GB")
    listing = BEND_DIR / "windows.json"
    T.never_overwrite(listing)
    T.never_overwrite(BEND_DIR / "work" / "windows")
    ws, z = d_items_windows()
    length = PS.SEC_S + PS.TRIM_S
    picks, jobs = [], []
    for w in ws:
        bends = sorted(n["on"] for n in T.annotated_notes(w["item"]) if "bend" in (n.get("arts") or []))
        if not bends:
            continue
        dur = T.goat_duration(z, w["item"])
        for st, held in db_windows(bends, w["start_s"], dur, length, full=lambda s, d=dur: T.full_window(d, s)):
            sec, inp, pre = T.window_audio(T.goat_audio(z, w["item"]), st)
            jobs.append((inp, w["item"]))
            picks.append({"item": w["item"], "start_s": st, "pre_s": pre, "annotated_bends": len(held),
                          "d_window_start_s": w["start_s"]})
    bp = T.run_bp(jobs, BEND_DIR / "work" / "windows")
    for pk, r in zip(picks, bp):
        p = BEND_DIR / "windows" / f"{pk['item']}@{pk['start_s']:g}.json"
        NR.write_once(p, T.note_record(r, pk["pre_s"], {"item": pk["item"], "start_s": pk["start_s"]}))
        pk["note_sha256"] = NR.file_sha(p)
    NR.write_once(listing, {"plan": "docs/note-rebuild-plan.md 12t", "ledger": f"{NR.LEDGER_ID} {PHASE_F6_LISTS}",
                            "renders": 0, "rule": db_windows.__doc__.split("(Pure.) ")[1].split(" ->")[0],
                            "windows": picks})
    print(f"BEND-WINDOWS: {len(picks)} windows on {len({p['item'] for p in picks})} items, "
          f"{sum(p['annotated_bends'] for p in picks)} annotated bends; windows.json sha256 {NR.file_sha(listing)}")


def bend_sets(m, declared, bank):
    """B (the ten lists) and Db (the bend windows) as windows {key, set, cluster, di, notes, truth}, each note file
    checked against its listing (and, declared, the listings against main's phase_nr_1_redo_bend_lists)."""
    import numpy as np

    from learn import note_transcribe as T
    from learn import song_bank as SB

    lists, wins = BEND_DIR / "lists.json", BEND_DIR / "windows.json"
    if declared:
        rec = (m.get(NR.LEDGER_ID) or {}).get(PHASE_F6_LISTS) or {}
        for p, k in ((lists, "lists_sha256"), (wins, "windows_sha256")):
            if rec.get(k) != NR.file_sha(p):
                raise SystemExit(f"{p.name}'s sha256 is not main's {PHASE_F6_LISTS} {k}")
    pair = T.install_pair(T.load_manifest())

    def note(p, want):
        if NR.file_sha(p) != want:
            raise SystemExit(f"{p.name}: not the note file its listing hashed")
        r = json.loads(p.read_text())
        why = T.install_refusal(r, pair)
        if why:
            raise SystemExit(f"{p.name}: {why}")
        return r
    B = []
    for nm, row in sorted(json.loads(lists.read_text())["lists"].items()):
        y = bend_audio(nm, bank)
        if NR.bytes_sha(np.asarray(y, np.float64).tobytes()) != row["audio_sha256"]:
            raise SystemExit(f"{nm}: the list no longer plays as transcribed")
        di = SB.measure(y)
        notes, _ = T.timed_notes(note(BEND_DIR / "lists" / f"{nm}.json", row["note_sha256"]), di)
        B.append({"key": nm, "set": "B", "cluster": nm, "di": di, "notes": notes, "truth": BEND_LISTS[nm],
                  "positive": nm in BEND_POSITIVES})
    _, z = d_items_windows()
    Db = []
    for pk in json.loads(wins.read_text())["windows"]:
        sec, _, _ = T.window_audio(T.goat_audio(z, pk["item"]), pk["start_s"])
        di = SB.measure(sec)
        rec = note(BEND_DIR / "windows" / f"{pk['item']}@{pk['start_s']:g}.json", pk["note_sha256"])
        notes, _ = T.timed_notes(rec, di)
        Db.append({"key": f"{pk['item']}@{pk['start_s']:g}", "set": "Db", "cluster": pk["item"], "di": di,
                   "notes": notes, "truth": T.dev_true_notes(pk["item"], pk["start_s"], di)})
    return B, Db, NR.file_sha(lists), NR.file_sha(wins)


def truth_set(m):
    """Guitar-TECHS's 79 usable windows (`note_transcribe` 12m's truth listing, refused unless main's
    phase_nr_1_redo_truth): Basic Pitch's stored notes and the MIDI truth, clustered by file."""
    from learn import note_transcribe as T

    listing = T.require_truth(m)
    ta = T.TruthAudio(listing)
    pair = T.install_pair(T.load_manifest())
    out = []
    for w in T.usable_windows(listing):
        di, _, _, truth = ta.window(w)
        notes, _ = T.timed_notes(T.load_note("truth", w["key"], pair), di)
        out.append({"key": w["key"], "set": "GT", "cluster": f"{w['player']}|{w['kind']}|{w['name']}", "di": di,
                    "notes": notes, "truth": truth})
    return out


def identity_check(name, fixes):
    """A build's files, byte for byte, through `apply_fixes` with `fixes` (build 1: every fix off; build 2: its own
    fixes), the build's ring and loudness. -> {checked, mismatches, identical}."""
    import hashlib
    import io

    import numpy as np

    from learn import note_transcribe as T

    build = json.loads(T.build_path(name).read_text())
    bank = NR.Bank(NR.load_notes_doc(), excl=NR.load_exclusion())
    out = {"build": name or "1", "fixes": fixes, "checked": 0, "mismatches": []}
    for kind, key, info, rec, di, finish in T.build_todo(ear_file=T.ear_items_file(name)):
        if kind == "ear" and key in T.RULED_OUT:
            continue
        notes, _ = T.timed_notes(rec, di)
        notes, _ = apply_fixes(notes, fixes, di)
        rows = build["parts"] if kind == "part" else build["ear"]
        for arm in NR.REDO_ARMS:
            y, _ = NR.rebuild_redo(arm, notes, len(di), bank, di, build["ring_variant"], finish=finish,
                                   loud=build.get("loud_gamma"))
            buf = io.BytesIO()
            np.save(buf, np.asarray(y, np.float32))
            out["checked"] += 1
            if hashlib.sha256(buf.getvalue()).hexdigest() != rows[key]["arms"][arm]["sha256"]:
                out["mismatches"].append(f"{kind}|{key}|{arm}")
    out["identical"] = not out["mismatches"]
    return out


def true_bends(w, s):
    """(Pure.) A window's true bent notes: B's by their tracks, Db's by the annotation's `bend`."""
    if s == "B":
        return [w["truth"][i] for i in bent_truth(w["truth"])]
    return [t for t in w["truth"] if "bend" in (t.get("arts") or [])]


def f6_points():
    """(Pure.) The grid's points (family, K, gap), in `f6_variants`' order."""
    return [(fam, k, gap) for k in F6_K for fam in F6_FAMILIES for gap in F6_GAPS]


def f6_variants(n1):
    """(Pure.) Every grid point's chains and notes on one window's F1 notes. -> {point: {chains, pairs, notes:
    {(track, keep): notes}}}."""
    out = {}
    for k in F6_K:
        both = f6_pairs(n1, k, "both")
        for fam in F6_FAMILIES:
            pairs = both if fam == "both" else [p for p in both if p[3] == "sequential"]
            for gap in F6_GAPS:
                chains = f6_chains(n1, pairs, gap)
                out[(fam, k, gap)] = {"chains": chains, "pairs": len(pairs),
                                      "notes": {(tr, kp): f6_stitch(n1, chains, tr, kp)
                                                for tr in F6_TRACKS for kp in (False, True)}}
    return out


def isolate_bend(out_path, declared=False, skip_identity=False):
    """12t phases 2 and 3 (zero renders): identity (build 1 with F6 off, build 2 with its fixes); the bend ladder; B's
    fault as built, split and unsplit apart; every grid point, track and keep on top of F1 only, on B, L (`bend` per
    amendment A, the nine bend-free lists), Guitar-TECHS, D (distance reported only) and Db (confirms); the beside
    arms' counts (unsplit bends, pad every bent note); the pick by the declared rule and the keep call (B3).
    Branch runs are labelled preliminary; `--declared` refuses off main. -> OUT.json."""
    import numpy as np

    from learn import note_transcribe as T

    t0 = time.time()
    if declared and skip_identity:
        raise SystemExit("the declared run checks identity: --skip-identity is for branch runs only")
    m, label, head = run_label(declared)
    if declared and PHASE_F6 not in (m.get(NR.LEDGER_ID) or {}):
        raise SystemExit(f"main's {NR.LEDGER_ID} entry has no {PHASE_F6}: merge the declaration first")
    NR.refuse_existing(out_path)
    body = {"plan": "docs/note-rebuild-plan.md 12t", "ledger": f"{NR.LEDGER_ID} {PHASE_F6}", "label": label,
            "head": head, "renders": 0}
    if not skip_identity:
        body["identity"] = {"build1_F6_off": identity_check(None, {}),
                            "build2": identity_check("b2", {"F1": "global", "loud": None})}
        body["identity_seconds"] = time.time() - t0
    else:
        body["identity"] = "skipped (--skip-identity): not a declared run"
    L, D, bank = windows_L_D()
    B, Db, lists_sha, wins_sha = bend_sets(m, declared, bank)
    GT = truth_set(m)
    body["listings"] = {"lists_sha256": lists_sha, "windows_sha256": wins_sha}
    for w in L:
        w.update(set="L" if w["key"] != "bend" else "Lbend", cluster=w["key"])
        if w["key"] == "bend":
            w["excluded"] = l_bend_excluded(w["truth"])
    for w in D:
        w.update(set="D", cluster=w["key"])
    wins = L + B + GT + D + Db
    for w in wins:
        w["n1"] = rezero_bends(w["notes"], "global")
        w["var"] = f6_variants(w["n1"])
    deciding = [w for w in wins if w["set"] in ("B", "Lbend")]
    harm = {"L nine bend-free": [w for w in wins if w["set"] == "L"],
            "B controls": [w for w in B if not w["positive"]], "Guitar-TECHS": GT}
    bent_lists = [w for w in deciding if bent_truth(w["truth"])]
    points = f6_points()

    def ne(w, notes):
        return note_error(w["truth"], notes, w.get("excluded", ()))["error"]

    def by_cluster(ws, f):
        acc = {}
        for w in ws:
            acc[w["cluster"]] = acc.get(w["cluster"], 0) + f(w)
        return acc
    # 1. the ladder (the measures' own check, true notes as the rebuilt notes)
    ladder = {}
    for rung in ("true", "flattened", "steps"):
        rows = {}
        for w in bent_lists:
            notes = ladder_rungs(w["truth"])[rung]
            xa = extra_attacks(w["truth"], notes, w.get("excluded", ()))
            rows[w["key"]] = {"bend_error": bend_error(w["truth"], notes, w.get("excluded", ())),
                              "extra_attacks": sum(xa), "bent_notes": len(xa), "note_error": ne(w, notes)}
        ladder[rung] = rows
    body["ladder"] = ladder
    # 2. B's fault as built (F1 only, build 2's rule), split and unsplit apart; L's `bend` beside
    fault = {}
    for w in bent_lists:
        fk = fault_kinds(w["truth"], scored_notes(w["n1"], w.get("excluded", ())))
        fault[w["key"]] = {**fk, "bend_error": bend_error(w["truth"], w["n1"], w.get("excluded", ())),
                           "extra_attacks": sum(extra_attacks(w["truth"], w["n1"], w.get("excluded", ()))),
                           "note_error": ne(w, w["n1"])}
    tot = {k: sum(f[k] for f in fault.values()) for k in ("missed", "split", "cleared", "bent", "flat")}
    nb = sum(tot.values())
    body["fault_as_built"] = {"per_list": fault, "total": tot,
                              "split_share": clopper_pearson(tot["split"], nb),
                              "unsplit_cleared_share": clopper_pearson(tot["cleared"], nb)}
    # 3. every grid point on top of F1 only
    f1_ne = {w["key"]: ne(w, w["n1"]) for w in wins}
    rows, free_joins, dec_ne = {}, {}, {}
    for pt in points:
        r = {"point": point_key(pt)}
        dec_ne[pt] = {w["cluster"]: ne(w, w["var"][pt]["notes"][("own", False)]) for w in deciding}
        r["note_error_deciding"] = {"summed": sum(dec_ne[pt].values()), "F1_summed": sum(f1_ne[w["key"]] for w in deciding),
                                    "less_F1": interval90([dec_ne[pt][w["cluster"]] - f1_ne[w["key"]] for w in deciding])}
        r["harm_less_F1"] = {}
        fj = 0
        for hs, ws in harm.items():
            a = by_cluster(ws, lambda w: ne(w, w["var"][pt]["notes"][("own", False)]))
            b = by_cluster(ws, lambda w: f1_ne[w["key"]])
            joins = sum(len(c) - 1 for w in ws for c in w["var"][pt]["chains"])
            notes_n = sum(len(w["n1"]) for w in ws)
            fj += joins
            r["harm_less_F1"][hs] = {"note_error": interval90([a[c] - b[c] for c in sorted(a)]),
                                     "false_joins": clopper_pearson(joins, notes_n)}
        free_joins[pt] = fj
        r["false_joins_bend_free"] = fj
        r["extra_attacks"] = {w["key"]: sum(extra_attacks(w["truth"], w["var"][pt]["notes"][("own", False)],
                                                          w.get("excluded", ()))) for w in bent_lists}
        r["second_note_lost"] = {w["key"]: second_lost(w["truth"], w["var"][pt]["notes"][("own", False)])
                                 for w in B if w["positive"]}
        r["second_note_lost_F1"] = {w["key"]: second_lost(w["truth"], w["n1"]) for w in B if w["positive"]}
        r["bend_error"] = {}
        for tr in F6_TRACKS:
            for kp in (False, True):
                r["bend_error"][f"{tr}|{'kept' if kp else 'cleared'}"] = {
                    w["key"]: bend_error(w["truth"], w["var"][pt]["notes"][(tr, kp)], w.get("excluded", ()))
                    for w in bent_lists}
        r["joins"] = {}
        for s in ("B", "Lbend", "L", "GT", "D", "Db"):
            ws = [w for w in wins if w["set"] == s]
            labs = [x for w in ws for x in join_labels(w["n1"], w["var"][pt]["chains"], w["truth"], s in ("D", "Db"))]
            cnt = {}
            for x in labs:
                k_ = x["joined"] + (f" into {x['head']}" if "head" in x else "") + f", {x['interval']} st"
                cnt[k_] = cnt.get(k_, 0) + 1
            r["joins"][s] = {"total": len(labs), "of_notes": sum(len(w["n1"]) for w in ws), "labels": cnt}
        r["unsplit_bent_but_cleared"] = {}
        for s, ws in (("B", B), ("Db", Db)):
            tot_c, at_true = 0, 0
            for w in ws:
                v = w["var"][pt]
                notes = v["notes"][("own", False)]
                cl = bent_but_cleared(notes, stitched_heads(len(w["n1"]), v["chains"]))
                tot_c += len(cl)
                at_true += sum(1 for k in cl if matched(notes[k], true_bends(w, s)))
            r["unsplit_bent_but_cleared"][s] = {"notes": tot_c, "at_true_bends": at_true}
        rows[pt] = r
    # F1 alone's figures beside (the as-built read on every set)
    body["F1"] = {"note_error": f1_ne,
                  "bend_error": {w["key"]: bend_error(w["truth"], w["n1"], w.get("excluded", ())) for w in bent_lists},
                  "unsplit_bent_but_cleared": {s: {"notes": sum(len(bent_but_cleared(w["n1"])) for w in ws),
                                                   "at_true_bends": sum(
                                                       1 for w in ws for k in bent_but_cleared(w["n1"])
                                                       if matched(w["n1"][k], true_bends(w, s)))}
                                               for s, ws in (("B", B), ("Db", Db))},
                  "ends_bent": {s: [sum(ends_bent(w["n1"]) for w in ws), sum(len(w["n1"]) for w in ws)]
                                for s, ws in (("B", B), ("L", L), ("GT", GT), ("D", D), ("Db", Db))}}
    # Db, confirms: annotated bends as built and after each point (split = an unmatched onset in its 1-s span)
    # 4. the pick by the declared rule (B1, B2), then track and keep, then the keep call (B3)
    pk = pick_point(dec_ne, free_joins)
    pt = pk["pick"]
    be = {}
    for tr in F6_TRACKS:
        for kp in (False, True):
            be[(tr, kp)] = {w["key"]: rows[pt]["bend_error"][f"{tr}|{'kept' if kp else 'cleared'}"][w["key"]]
                            ["mean_abs_bins"] for w in bent_lists}
    tk = pick_track_keep(be)
    kc = keep_call(rows[pt]["note_error_deciding"]["less_F1"],
                   {hs: rows[pt]["harm_less_F1"][hs]["note_error"] for hs in harm})
    body["pick"] = {"label": label, "minimum": point_key(pk["minimum"]),
                    "candidates": [point_key(p) for p in pk["candidates"]], "point": point_key(pt),
                    "point_params": {"family": pt[0], "K": pt[1], "gap": pt[2]},
                    "less_minimum": {point_key(p): iv for p, iv in pk["less_minimum"].items()},
                    "summed_note_error": {point_key(p): v for p, v in pk["summed"].items()},
                    "bend_free_joins": {point_key(p): v for p, v in free_joins.items()},
                    "track_keep": {"minimum": list(tk["minimum"]), "candidates": [list(c) for c in tk["candidates"]],
                                   "pick": list(tk["pick"]),
                                   "less_minimum": {f"{a}|{'kept' if b else 'cleared'}": iv
                                                    for (a, b), iv in tk["less_minimum"].items()}},
                    "rule": {"F1": "global", "F6": {"K": pt[1], "gap": pt[2], "family": pt[0], "track": tk["pick"][0],
                                                    "keep": tk["pick"][1]}},
                    "keep_call": kc,
                    "k_order_note": "K = 3, 5, 1 is a preference (B2): on D, K = 3 and K = 5 join the same 2 plucks",
                    "harm_label": "Guitar-TECHS in the first step is deciding for harm (B2)"}
    # D, harm, seen: the distance (report only, 12s), for every variant, cached by the notes
    cache = {}

    def dist(w, notes):
        key = (w["key"], NR.content_sha(notes))
        if key not in cache:
            cache[key] = window_figures(w, notes, bank)["distance"]
        return cache[key]
    d_f1 = {w["key"]: dist(w, w["n1"]) for w in D}
    for p in points:
        rows[p]["D_distance_less_F1"] = {}
        for tr in F6_TRACKS:
            for kp in (False, True):
                rows[p]["D_distance_less_F1"][f"{tr}|{'kept' if kp else 'cleared'}"] = interval90(
                    [dist(w, w["var"][p]["notes"][(tr, kp)]) - d_f1[w["key"]] for w in D])
    # the beside arm "pad every bent note" (never inside build 3)
    pad = {w["key"]: bend_error(w["truth"], pad_bent(w["n1"]), w.get("excluded", ())) for w in bent_lists}
    body["pad_every_bent_note"] = {"bend_error": pad,
                                   "D_distance_less_F1": interval90([dist(w, pad_bent(w["n1"])) - d_f1[w["key"]]
                                                                     for w in D])}
    # Db's annotated bends: split as built, and after the picked rule
    dbr = {}
    for w in Db:
        dbr[w["key"]] = {"as_built": annotated_fragments(w["truth"], w["n1"]),
                         "after_pick": annotated_fragments(w["truth"], w["var"][pt]["notes"][tuple(tk["pick"])]),
                         "joins_at_pick": sum(len(c) - 1 for c in w["var"][pt]["chains"])}
    body["Db_at_pick"] = {"windows": dbr, "label": "confirms; designed-on if it ever enters a pick",
                          "total": {k: {f: sum(r[k][f] for r in dbr.values()) for f in ("bends", "fragmented",
                                                                                         "fragments")}
                                    for k in ("as_built", "after_pick")}}
    body["rows"] = {point_key(p): r for p, r in rows.items()}
    body["L_bend_retruth_beside"] = {
        point_key(p): bend_error(bend_retruth(next(w for w in L if w["key"] == "bend")["truth"]),
                                 next(w for w in L if w["key"] == "bend")["var"][p]["notes"][tuple(tk["pick"])])
        for p in points}
    body["seconds"] = time.time() - t0
    NR.write_once(out_path, body)
    ident = body["identity"] if isinstance(body["identity"], dict) else {}
    print(f"ISOLATE-BEND ({label}): identity "
          f"{ {k: (v['identical'], v['checked']) for k, v in ident.items()} }; pick {point_key(pt)} "
          f"{tk['pick']}; keep call {kc['call']}; {time.time() - t0:.0f} s -> {out_path}")


def require_frozen(m, fixes):
    """`e-read` and `exposure`'s refusal (12t): the frozen F6 rule (`phase_nr_1_redo_fix_bend_frozen`) must be in the
    ledger, and `fixes`' F6 must be that rule."""
    rec = (m.get(NR.LEDGER_ID) or {}).get(PHASE_F6_FROZEN)
    if not isinstance(rec, dict):
        raise SystemExit(f"no {PHASE_F6_FROZEN} in the ledger: E is read only after F6 is frozen")
    if (rec.get("rule") or {}).get("F6") != fixes.get("F6"):
        raise SystemExit(f"--fixes' F6 is not {PHASE_F6_FROZEN}'s rule")
    return rec


def e_read(out_path, fixes, base, declared=False):
    """12t phase 5 (zero renders), after the freeze: on E (build 2's ear items, `ear-items-b2.json`), per item the
    chains stitched and joins, the bent-but-cleared unstitched notes, the annotated bends still fragmented, and the
    distance against `base` (build 2's rule; reported). -> OUT.json."""
    from learn import note_transcribe as T
    from learn import song_bank as SB

    t0 = time.time()
    m, label, head = run_label(declared)
    require_frozen(m, fixes)
    apply_fixes([], fixes)
    apply_fixes([], base)
    NR.refuse_existing(out_path)
    excl, _, z, _ = T._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    pair = T.install_pair(T.load_manifest())
    items, dd = {}, []
    for e in json.loads(T.ear_items_file("b2").read_text())["items"]:
        di = SB.measure(T.window_audio(T.goat_audio(z, e["item"]), e["start_s"])[0])
        notes, _ = T.timed_notes(T.load_note("ear", e["item"], pair), di)
        nb, _ = apply_fixes(notes, base, di)
        nf, rep = apply_fixes(notes, fixes, di)
        ann = T.dev_true_notes(e["item"], e["start_s"], di) if (NR.OUT / "true-notes" / f"{e['item']}.json").exists() \
            else []
        f6 = rep.get("F6") or {"chains": [], "joins": 0}
        win = {"di": di}
        fb, ff = window_figures(win, nb, bank), window_figures(win, nf, bank)
        dd.append(ff["distance"] - fb["distance"])
        items[e["item"]] = {"start_s": e["start_s"], "chains": len(f6["chains"]), "joins": f6["joins"],
                            "bent_but_cleared_unstitched": len(bent_but_cleared(
                                nf, stitched_heads(len(nf) + f6["joins"], f6["chains"]))),
                            "annotated_fragments": {"base": annotated_fragments(ann, nb),
                                                    "fixed": annotated_fragments(ann, nf)},
                            "base": fb, "fixed": ff}
    body = {"plan": "docs/note-rebuild-plan.md 12t phase 5 (E)", "label": label, "head": head, "renders": 0,
            "fixes": fixes, "base": base, "items": items, "distance_less_base": interval90(dd),
            "seconds": time.time() - t0}
    NR.write_once(out_path, body)
    print(f"E-READ ({label}): distance less base {body['distance_less_base']}; -> {out_path}")


def exposure(out_path, fixes, declared=False):
    """12t phase 5 (zero renders): per part, the chains `fixes` stitch and whether its `tr-di` is byte-identical to
    build 2's (`build-b2.json`), the build's ring and loudness (`fixes`' own "loud" when named). -> OUT.json."""
    import hashlib
    import io

    import numpy as np

    from learn import note_transcribe as T

    t0 = time.time()
    m, label, head = run_label(declared)
    require_frozen(m, fixes)
    apply_fixes([], fixes)
    NR.refuse_existing(out_path)
    b2 = json.loads(T.build_path("b2").read_text())
    loud, why = T.build_loudness(b2.get("loud_gamma"), fixes)
    if why:
        raise SystemExit(why)
    bank = NR.Bank(NR.load_notes_doc(), excl=NR.load_exclusion())
    parts = {}
    for kind, key, info, rec, di, finish in T.build_todo(ear_file=T.ear_items_file("b2")):
        if kind != "part":
            continue
        notes, _ = T.timed_notes(rec, di)
        nf, rep = apply_fixes(notes, fixes, di)
        y, _ = NR.rebuild_redo("tr-di", nf, len(di), bank, di, b2["ring_variant"], finish=finish, loud=loud)
        buf = io.BytesIO()
        np.save(buf, np.asarray(y, np.float32))
        sha = hashlib.sha256(buf.getvalue()).hexdigest()
        parts[key] = {"chains": len((rep.get("F6") or {}).get("chains", [])),
                      "joins": (rep.get("F6") or {}).get("joins", 0),
                      "tr_di_sha256": sha, "identical_to_b2": sha == b2["parts"][key]["arms"]["tr-di"]["sha256"]}
    body = {"plan": "docs/note-rebuild-plan.md 12t phase 5 (exposure)", "label": label, "head": head, "renders": 0,
            "fixes": fixes, "parts": parts, "changed": sorted(k for k, v in parts.items() if not v["identical_to_b2"]),
            "seconds": time.time() - t0}
    NR.write_once(out_path, body)
    print(f"EXPOSURE ({label}): {len(body['changed'])} of {len(parts)} parts' tr-di differ from build 2's -> {out_path}")


def main(argv=None):
    import sys

    for p_ in (str(NR.REPO), str(NR.REPO / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("isolate")
    s.add_argument("out")
    s.set_defaults(fn=lambda a: isolate(a.out))
    s = sub.add_parser("isolate-ms")
    s.add_argument("out")
    s.add_argument("--f1", required=True, choices=F1_MODES, help="the declared isolation's F1 pick")
    s.set_defaults(fn=lambda a: isolate_ms(a.out, a.f1))
    s = sub.add_parser("combine")
    s.add_argument("out")
    s.add_argument("--kept", required=True, help='the kept fixes as JSON, e.g. {"F1": "global", "F2ms": 0.1}')
    s.set_defaults(fn=lambda a: combine(a.out, json.loads(a.kept)))
    s = sub.add_parser("clamps")
    s.add_argument("out")
    s.set_defaults(fn=lambda a: clamps(a.out))
    s = sub.add_parser("bend-lists")
    s.set_defaults(fn=cmd_bend_lists)
    s = sub.add_parser("bend-windows")
    s.set_defaults(fn=cmd_bend_windows)
    s = sub.add_parser("isolate-bend")
    s.add_argument("out")
    s.add_argument("--declared", action="store_true", help="the declared run: refuses off main (amendment D2)")
    s.add_argument("--skip-identity", action="store_true", help="a branch run without the identity check (never "
                   "with --declared)")
    s.set_defaults(fn=lambda a: isolate_bend(a.out, a.declared, a.skip_identity))
    s = sub.add_parser("e-read")
    s.add_argument("out")
    s.add_argument("--fixes", required=True, help="the frozen rule as JSON, e.g. {\"F1\": \"global\", \"F6\": {...}}")
    s.add_argument("--base", required=True, help='build 2\'s rule, {"F1": "global"}')
    s.add_argument("--declared", action="store_true")
    s.set_defaults(fn=lambda a: e_read(a.out, json.loads(a.fixes), json.loads(a.base), a.declared))
    s = sub.add_parser("exposure")
    s.add_argument("out")
    s.add_argument("--fixes", required=True)
    s.add_argument("--declared", action="store_true")
    s.set_defaults(fn=lambda a: exposure(a.out, json.loads(a.fixes), a.declared))
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
