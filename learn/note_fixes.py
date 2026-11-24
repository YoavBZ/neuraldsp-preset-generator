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

def apply_fixes(notes, fixes, di=None, rate=NR.SR):
    """Fixes in order F1, F2, F3 on a window's timed notes. fixes: {"F1": mode, "F2": theta, "F3": True}; an absent
    or falsy fix is off. F2 needs the DI. -> (notes, report)."""
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
    s = sub.add_parser("clamps")
    s.add_argument("out")
    s.set_defaults(fn=lambda a: clamps(a.out))
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
