"""The spectral-envelope steps (`docs/scratch-envelope-plan.md`; ledger `preset-ladder` `phase_scratch_envelope`, then
the hash PR `phase_scratch_envelope_dry` with build.json's sha256, then `phase_scratch_envelope_outcome`): the core,
the outcome table and the read.

The sound-gap read gave S = ln(d_tr-di / d_vc-own) +0.501 [+0.399, +0.603] on the 40, by the score; the `vc-own` search
row read XW-part (about 70% of build 2's search cost recovered by real audio inside our note windows). These steps ask
how finely the bank guitar's spectral envelope must be corrected to close S: per part, per onset group, or per 43-ms
window. Each guitar is `tr-di` before its finish, corrected toward `vc-own` before its finish, then `p.finish`, cut to
n, -22.9 LUFS (`voice_build.chain`):

| Guitar | Correction | Read as |
|---|---|---|
| `vt-part` | one EQ per part | a check: about 0 by construction (the finish refits each guitar's long-term tone) |
| `vt-group` | one EQ per onset group | an oracle per-note EQ; not a bound on a bank |
| `vt-win` | one EQ per 43-ms window (one STFT frame), 5-ms hop | tone moving inside the note |
| `vt-mag` (beside) | `vc-own`'s magnitude, `tr-di`'s phase | magnitude alone |
| `vt-phase` (beside) | `tr-di`'s magnitude, `vc-own`'s phase | phase alone |

**The transform** (`TRANSFORM`, the review's amendment 1; `learn/envelope_build.py` codes it). The source is
`note_rebuild.denoise_above` of `scratch_rederive._synth(..., last=True)` (`tr-di` before its finish), the target the
padded raw section (`voice_build.padded_raw`) times `voice_build.own_gain(..., end=real_end(n, pad))` (`vc-own` before
its finish); both exactly n + `pad_samples()` long, or the part stops. STFT: periodic Hann 2048, hop 240, the signal
zero-extended by 1024 at both ends, frame i centred on sample 240 i, frames 0 to (L - 1) // 240 (`frame_count`).
Bands (`band_table`): third-octave centres 1000 2^(k/3), k = -12 to 12, edges at +-1/6 octave; bin b (frequency
b 48000 / 2048) lies in a band when its frequency is in [lo, hi) on the exact centres; a band with fewer than 4 bins
merges upward: 20 bands, bins 3 to 766. Bins 0-2 and 767-1024 keep 0 dB in the three EQ steps (`edge_bins`); `vt-mag`
and `vt-phase` swap all 1,025 bins. Units (`unit_ids`): `vt-part` one; `vt-group` the frames whose centre lies in
[onset_k - 2 ms, onset_k+1 - 2 ms) (`voice_build.group_onsets`; unit 0 everything before the first, the last to the
padded end); `vt-win` one frame each. E is the STFT power summed over a unit's frames and a band's bins; the target
is first level-aligned to the source by one factor per part (`TRANSFORM["level_align"]`); the gain is
sqrt(E_target / E_source), the same for every bin of the band, its amplitude dB clamped to +-20 dB; a cell keeps 0 dB
when E_source < (that band's largest source cell over the part's units at that step) x 10^-4, or E_source = 0;
E_target = 0 with E_source > 0 gives -20 dB. The inverse is windowed overlap-add normalised by the sum of w^2. In the
swaps, where the phase donor's magnitude is 0, the other signal's phase is kept.

**The proofs** (`PROOFS`, on 47 of 47; a failure stops the shard before that part writes anything): 1 the source
through `chain` is `tr-di` byte for byte (build 2's sha256); 2 the target through `chain` is the stored `vc-own` byte
for byte (the sound-gap build.json's `audio_sha256`), its inputs `played_trace(p.notes, n + pad, p.bank, T's tuning,
p.ring, T's mutes)` and `padded_raw(prt.di_path, prt.start_s)` as `voice_build.part_record`; 3 unity gains through the
transform return the source (max |y - x| / max |x| <= 1e-9, float64, before the finish); 4 the target's STFT through
the swap with its own magnitude and phase returns the target to the same tolerance (amendment 6).

**The realised error** (amendment 2), recorded per part for all five, on the cells that are not floored: before the
finish against the clamped intent (the transform's fidelity), and the finished `vt-k` against the finished `vc-own`
(what the adaptive finish leaves); median and 90th percentile of |error| in dB, each step's clamped and floored
shares, spectral convergence for `vt-mag` and `vt-phase`, the level change.

**The terms** (floors at row (b)'s answer, the held half, the true DI as the judge's DI; `tr-di`'s and `vc-own`'s
floors are stored): C_k = ln(d_tr-di / d_vt-k), what step k closes; R_k = ln(d_vt-k / d_vc-own), what is left; C_k +
R_k = S per part to 1e-12, on each step's passing set. `XE_TABLE` reads `paired_reading` of C_k and R_k (k in part,
group, win) on the 40, the first that holds; `vt-mag` and `vt-phase` sit beside and never change the code.

    $MAIN -m learn.envelope_build build --shard k/3     # zero renders; then --combine; the hash PR _dry
    $MAIN -m learn.envelope_floors floor --shard k/3    # 478 renders in all; then --rerun
    $MAIN -m learn.scratch_envelope read                # zero renders, once: XE_TABLE's code

Every command refuses unless this checkout runs main's code (this module, its two units and `PINNED`) and keys (the
`phase_scratch_envelope*`, `phase_scratch_own*` and `phase_scratch_voice*` keys), main holds the keys it reads, and the
`vc-own` search row's audited code is XW-closed or XW-part (`outcome_refusal`). The pure parts (the bands, the units,
`XE_TABLE`, `xe_code`, the terms, the guards, the paths) are tested in tests/test_scratch_envelope.py on the light CI
runner (no numpy at import), on made-up keys.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
import pathlib
import statistics
import time

from learn import note_rebuild as NR
from learn import scratch_exact as SE
from learn import scratch_notes as SN
from learn import scratch_own as SO
from learn import scratch_search as S
from learn import scratch_voice as SV

LEDGER_ID = S.LEDGER_ID                  # preset-ladder
PLAN = "docs/scratch-envelope-plan.md"
KEY_PREFIX = "phase_scratch_envelope"
PHASE = KEY_PREFIX                       # this declaration
PHASE_DRY = f"{KEY_PREFIX}_dry"          # the build's hash PR: build.json's sha256 (zero renders), before any floor
PHASE_OUTCOME = f"{KEY_PREFIX}_outcome"  # the audited read
KEYS_TO_COME = (PHASE_DRY, PHASE_OUTCOME)
GUARDED_PREFIXES = SO.GUARDED_PREFIXES + (SO.KEY_PREFIX,)

MODULE = "learn/scratch_envelope.py"
UNIT_FILES = ("learn/envelope_build.py", "learn/envelope_floors.py")
OWN_FILES = (MODULE,) + UNIT_FILES
PINNED = tuple(dict.fromkeys(SV.CODE_FILES + SO.CODE_FILES + ("learn/scratch_readerr.py",)))   # edited by none here
CODE_FILES = OWN_FILES + PINNED
OWN_OPEN = ("XW-closed", "XW-part")      # the vc-own row's codes under which these steps run (its "deferred" call)

# --- the guitars, the steps, the terms ---------------------------------------------------------------------------------

SR = NR.SR
BANK, OWN = SV.BANK, SV.OWN              # tr-di, vc-own: the stored floors, the carry sources, the repeat's guitars
STEPS = ("part", "group", "win", "mag", "phase")
EQ_STEPS = ("part", "group", "win")      # the three EQ steps: they decide
SWAP_STEPS = ("mag", "phase")            # beside, never changing the code
GUITAR = {k: f"vt-{k}" for k in STEPS}
BUILT = tuple(GUITAR[k] for k in STEPS)  # built here, rendered by the floors in this order
STORED = (BANK, OWN)
DECIDING_SET = (BANK, OWN) + tuple(GUITAR[k] for k in EQ_STEPS)   # one passing set for the code
TERMS = (("S", BANK, OWN),) + tuple((f"C_{k}", BANK, GUITAR[k]) for k in STEPS) + tuple(
    (f"R_{k}", GUITAR[k], OWN) for k in STEPS)                     # ln(num / den)
TERM_NAMES = tuple(t for t, _, _ in TERMS)
READ_TERMS = tuple(f"{c}_{k}" for k in EQ_STEPS for c in ("C", "R"))   # their readings must all be usable
BESIDE_TERMS = tuple(f"{c}_{k}" for k in SWAP_STEPS for c in ("C", "R"))
ID_TOL = SV.SUM_TOL                      # |C_k + R_k - S| per part, 1e-12
SEEN_S = (0.501, 0.399, 0.603)           # S on the 40 (the sound-gap read; the read must reproduce it to 3 places)
DECIDING = SV.DECIDING                   # BKS+GOAT, the 40; all 47 beside
SMALL, BIG = SV.SMALL, SV.BIG            # 0.05, 0.10: they label only (`paired_reading`)
PARTS = SV.PARTS                         # 47
CHECK_PARTS = SV.CHECK_PARTS             # 2
RENDERS_EACH = 2                         # a priming render and the kept one (voice_floors.RENDERS_EACH)
RENDERS = {"floors": len(BUILT) * PARTS * RENDERS_EACH, "repeat": len(STORED) * CHECK_PARTS * RENDERS_EACH}  # 470 + 8
NOT_COMPUTABLE = SV.NOT_COMPUTABLE

# --- the transform (amendment 1; envelope_build codes it, these constants only) ---------------------------------------

N_FFT = 2048
HOP = 240                                # 5 ms
HALF = N_FFT // 2                        # the zero extension at both ends: frame i is centred on sample HOP * i
BINS = N_FFT // 2 + 1                    # 1,025
BAND_REF_HZ = 1000.0
BAND_K = tuple(range(-12, 13))           # third-octave centres 1000 * 2^(k/3)
BAND_EDGE_OCT = 1 / 6
MIN_BINS = 4                             # a band with fewer bins merges upward
CLAMP_DB = NR.ORACLE_CLAMP_DB            # 20 dB, on the amplitude gain
FLOOR_DB = NR.MUTE_FLOOR_DB              # 40 dB: a cell keeps 0 dB under its band's largest source cell less this
FLOOR_POWER = 10 ** (-FLOOR_DB / 10)     # 1e-4, in power
LEAD_S = SV.WINDOWS["lead_s"]            # 2 ms: a group unit opens this far before its first onset
PROOF_TOL = 1e-9                         # proofs 3 and 4: max |y - x| / max |x|, float64
BANDS_N = 20
TRANSFORM = {
    "source": "note_rebuild.denoise_above(scratch_rederive._synth(notes, n, bank, ring, T's tuning, mutes, tilt, "
              "levels, loudness option, last=True)): tr-di before its finish, n + END_PAD_S samples, float64",
    "target": "voice_build.padded_raw(prt.di_path, prt.start_s) times voice_build.own_gain(notes, played_trace(notes, "
              "n + pad, bank, T's tuning, ring, T's mutes), n + pad, end=real_end(n, pad)): vc-own before its finish",
    "lengths": "both exactly n + voice_build.pad_samples() samples, or the part stops before writing",
    "stft": f"periodic Hann {N_FFT} (0.5 - 0.5 cos(2 pi j / {N_FFT})), hop {HOP}, numpy.fft.rfft ({BINS} bins), the "
            f"signal zero-extended by {HALF} at both ends; frame i centred on sample {HOP} i; frames 0 to (L - 1) // "
            f"{HOP} (frame_count), so every sample 0..L-1 lies within {HOP} of a frame centre",
    "istft": "numpy.fft.irfft of each frame times the same window, overlap-added at the hop, divided by the "
             "overlap-added w^2 (never 0 on 0..L-1), cut back to 0..L-1",
    "bands": "third-octave centres 1000 * 2^(k/3), k = -12..12, edges centre * 2^(+-1/6) on the exact centres; bin b "
             f"(frequency b * {SR} / {N_FFT}) lies in a band when its frequency is in [lo, hi); a band with fewer "
             f"than {MIN_BINS} bins merges with the next one up: {BANDS_N} bands, bins 3..766 (band_table)",
    "edge_bins": "bins 0-2 (below 55.7 Hz) and 767-1024 (above 17.96 kHz) keep 0 dB in the three EQ steps; vt-mag "
                 "and vt-phase swap all 1,025 bins",
    "units": "vt-part one unit; vt-group: frame i is in unit bisect_right(bounds, 240 i), bounds the onset groups' "
             "first onsets (voice_build.group_onsets) less 2 ms, round(... * SR): unit 0 everything before the first, "
             "the last to the padded end; vt-win: one frame each",
    "energy": "E[unit, band] = the STFT power |X|^2 summed over the unit's frames and the band's bins",
    "level_align": "the implementer's call: before the gains the target's STFT is scaled by one factor per part, sqrt("
                   "the source's in-band power / the target's), summed over all 20 bands and every frame of the padded "
                   "part, so the clamp bounds the envelope's shape, not the two signals' arbitrary levels; the finish "
                   "and -22.9 LUFS re-level every guitar, so the factor reaches a finished guitar only through the "
                   "clamp; recorded per part (target_align_db); proof 4 runs on the unscaled target",
    "gain": "sqrt(E_target / E_source), the same for every bin of the band and every frame of the unit; its amplitude "
            f"dB (10 log10 of the power ratio) clamped to +-{CLAMP_DB:g} dB",
    "floor": "a cell keeps 0 dB when E_source < max over the part's units at that step of E_source for that band, "
             f"times 10^-{FLOOR_DB / 10:g} (power dB), or when E_source = 0; E_target = 0 with E_source > 0 gives "
             f"-{CLAMP_DB:g} dB (clamped)",
    "swaps": "vt-mag |X_target| with X_source's phase, vt-phase |X_source| with X_target's phase, every bin; where the "
             "phase donor's magnitude is 0 the other signal's own bin is kept (its phase)",
    "after": "voice_build.chain: p.finish on all n + pad samples, cut to n, -22.9 LUFS by at_lufs; float32",
}
PROOFS = ("source_is_tr_di", "target_is_vc_own", "unity_is_source", "swap_is_target")
ERROR_RULE = {
    "intent": "before the finish: per cell (unit, band) 10 log10(E_y / E_source) less the clamped intended gain (the "
              "EQ steps); vt-mag against the target's band power, vt-phase against the source's, on vt-win's cells; "
              "cells floored at that step (vt-win's floor for the swaps) or with zero power left out",
    "target": "the finished vt-k against the finished vc-own (chain's n samples, the same STFT, frames 0..(n - 1) // "
              "240): per cell 10 log10(E_vt-k / E_vc-own), the step's cells and floor (vt-win's for the swaps)",
    "figures": "per part and step: the median and 90th percentile of |error| in dB, the signed median, the cell count, "
               "the clamped and floored shares of the step's cells; spectral convergence (|| |Y| - |M| ||_F / || |M| "
               "||_F, M the magnitude donor) for vt-mag and vt-phase; the level change before the finish (20 log10 of "
               "the RMS over the source's) and the step to -22.9 LUFS",
}


def band_table(rate=SR, n_fft=N_FFT):
    """(Pure.) The declared bands: third-octave centres 1000 2^(k/3), edges at +-1/6 octave on the exact centres, bin b
    in a band when b * rate / n_fft lies in [lo, hi); a band with fewer than MIN_BINS bins merges with the next one up
    (a remainder at the top would merge down; none here). -> tuple of {ks, centres_hz, lo_hz, hi_hz, bin_lo, bin_hi,
    bins} (bin_hi inclusive)."""
    raw = []
    for k in BAND_K:
        c = BAND_REF_HZ * 2 ** (k / 3)
        lo, hi = c * 2 ** -BAND_EDGE_OCT, c * 2 ** BAND_EDGE_OCT
        raw.append((k, c, lo, hi, [b for b in range(n_fft // 2 + 1) if lo <= b * rate / n_fft < hi]))
    out, acc = [], None
    for k, c, lo, hi, bins in raw:
        if acc is None:
            acc = {"ks": [k], "centres_hz": [c], "lo_hz": lo, "hi_hz": hi, "bins_list": list(bins)}
        else:
            acc["ks"].append(k)
            acc["centres_hz"].append(c)
            acc["hi_hz"] = hi
            acc["bins_list"] += bins
        if len(acc["bins_list"]) >= MIN_BINS:
            out.append(acc)
            acc = None
    if acc is not None:                      # a short top band merges down
        if not out:
            raise ValueError("no band has enough bins")
        last = out[-1]
        last["ks"] += acc["ks"]
        last["centres_hz"] += acc["centres_hz"]
        last["hi_hz"] = acc["hi_hz"]
        last["bins_list"] += acc["bins_list"]
    return tuple({"ks": b["ks"], "centres_hz": b["centres_hz"], "lo_hz": b["lo_hz"], "hi_hz": b["hi_hz"],
                  "bin_lo": b["bins_list"][0], "bin_hi": b["bins_list"][-1], "bins": len(b["bins_list"])}
                 for b in out)


def band_of_bins(rate=SR, n_fft=N_FFT):
    """(Pure.) Each bin's band index, or -1 for an edge bin (outside every band). -> list of n_fft // 2 + 1."""
    out = [-1] * (n_fft // 2 + 1)
    for i, b in enumerate(band_table(rate, n_fft)):
        for j in range(b["bin_lo"], b["bin_hi"] + 1):
            out[j] = i
    return out


def edge_bins(rate=SR, n_fft=N_FFT):
    """(Pure.) The bins that keep 0 dB in the EQ steps: outside every band."""
    return [j for j, b in enumerate(band_of_bins(rate, n_fft)) if b < 0]


def band_rows(rate=SR, n_fft=N_FFT):
    """(Pure.) The band table as the ledger and the plan doc write it: centres (Hz, rounded), edges, bin ranges."""
    return [{"band": i, "centres_hz": [round(c, 1) for c in b["centres_hz"]], "lo_hz": round(b["lo_hz"], 1),
             "hi_hz": round(b["hi_hz"], 1), "bins": f"{b['bin_lo']}-{b['bin_hi']}", "n_bins": b["bins"]}
            for i, b in enumerate(band_table(rate, n_fft))]


def frame_count(length, hop=HOP):
    """(Pure.) The declared frame count on `length` samples: frames 0..(length - 1) // hop, centred on hop * i."""
    if length <= 0:
        raise ValueError("an empty signal has no frames")
    return (length - 1) // hop + 1


def group_bounds(onsets, rate=SR):
    """(Pure.) The group units' bounds in samples: each onset group's first onset less 2 ms, round(), sorted."""
    return sorted(int(round((t - LEAD_S) * rate)) for t in onsets)


def unit_ids(step, frames, onsets=(), rate=SR, hop=HOP):
    """(Pure.) Each frame's unit at an EQ step (or vt-win's, the swaps' error cells): `part` one unit (0); `group`
    bisect_right(bounds, hop * i), so unit 0 holds the frames before the first bound and the last runs to the padded
    end, the units then numbered in order with the empty ones dropped; `win` the frame itself. -> list of `frames`."""
    if step == "part":
        return [0] * frames
    if step in ("win",) + SWAP_STEPS:
        return list(range(frames))
    if step != "group":
        raise ValueError(step)
    bounds = group_bounds(onsets, rate)
    raw = [bisect.bisect_right(bounds, hop * i) for i in range(frames)]
    ren = {u: j for j, u in enumerate(sorted(set(raw)))}
    return [ren[u] for u in raw]


# --- the outcome table (pure; amendments 3, 4 and 5, the orchestrator's calls) ------------------------------------------

ORACLE = ("an oracle: every correction comes from the true DI, read by the floor; a song-only way to get this envelope "
          "(for example from the stem, through the amp) is not priced here; the next search row (about 13,400 "
          "renders) needs its own go; a floor remainder over 0.10 may cost little by search (the floor-to-search "
          "mapping is concave)")
XE_TABLE = (    # (code, when, said, decides); on the 40, `paired_reading` of C_k and R_k (k in part, group, win)
    ("XE-anomaly", "a proof, the repeat check, S's reproduction or the identity fails; a C or R of the EQ steps (part, "
     "group, win) has no usable interval or reading; or any of them reads better",
     "unexpected; audit. If the audit finds no fault, the figures go to the user as read{then}",
     "stop; audit; nothing said before the audit"),
    ("XE-static", "C_part reads worse (closes)",
     "unexpected by construction (the finish refits each guitar's long-term tone); audit the finish. If it stands, "
     "that part of S is static tone{then}",
     "the finish, not a sound route; " + ORACLE),
    ("XE-group", "R_group reads matches",
     "a per-note correction is enough: a heard-size remainder after one EQ per onset group is ruled out, by the score",
     "route 1's kind (a better-matched bank, pickup, or per-note EQ), an indication and not a bound on a bank (a bank "
     "also changes attacks and articulation); " + ORACLE),
    ("XE-window", "R_win reads matches and R_group reads worse",
     "the tone must move inside the note: one EQ per onset group leaves a heard-size remainder, one EQ per 43-ms "
     "window does not, by the score",
     "route 2, or samples that change over the note; " + ORACLE),
    ("XE-split", "C_win reads worse (closes) and R_win reads worse",
     "envelope correction buys about C_win, an estimate within the realised error (the transform's error makes it "
     "understate rather than bound); the rest is not envelope at this resolution; C_group reads {c_group}: that says "
     "whether per-note covers the envelope part",
     "the envelope part to routes 1 and 2 as C_group and C_win say, the rest to note content or detail; " + ORACLE),
    ("XE-detail", "R_win reads worse and C_win reads matches",
     "no heard-size part of S is envelope at this resolution: note content or detail, by the score, with the realised "
     "error beside",
     "route 3 or the stem; route 2 only as whole-waveform generation; " + ORACLE),
    ("XE-undecided", "anything else", "not decided; undecided is not failed{note}",
     "to the user with the intervals (R_win {rw_lo} to {rw_hi}, R_group {rg_lo} to {rg_hi}, C_win {cw_lo} to "
     "{cw_hi})"),
)
XE_CODES = tuple(c for c, *_ in XE_TABLE)
XE_DECLARED = ("XE-anomaly", "XE-static", "XE-group", "XE-window", "XE-split", "XE-detail", "XE-undecided")
SURPRISE_CODES = ("XE-anomaly", "XE-static")   # amendment 3: a `then` field holds what the rest of the table gives
REST_CODES = ("XE-group", "XE-window", "XE-split", "XE-detail", "XE-undecided")
WINDOW_GROUP_UNDECIDED = "window suffices; group undecided"   # the orchestrator's call: XE-undecided, no new code
WINDOW_ARTEFACT = "window-step artefact"       # beside (non-binding note): R_group matches while R_win reads worse
CHECKS = ("proofs", "repeat", "s_reproduces", "identity_holds")


def iv_ok(iv):
    return SV.iv_ok(iv)


def reading(iv):
    """(Pure.) `scratch_notes.paired_reading` of a usable interval, else None."""
    return SV.reading(iv)


def _r(iv):
    return (reading(iv) or {}).get("reading")


def table_guard():
    """Refuse unless XE_TABLE holds its declared codes in order, its last row is literally "anything else", the
    surprise and rest codes split the table, 0 < SMALL < BIG, the key prefix sits outside every guarded prefix, the
    bands are the declared 20 and the renders the sound-gap test's 478."""
    if XE_CODES != XE_DECLARED:
        raise SystemExit("XE_TABLE's codes are not the seven declared, in order")
    if XE_TABLE[-1][1] != "anything else":
        raise SystemExit("XE_TABLE's last row is not 'anything else'")
    if SURPRISE_CODES + REST_CODES != XE_DECLARED:
        raise SystemExit("XE_TABLE's surprise and rest codes do not split it")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")
    if not KEY_PREFIX.startswith("phase_scratch_") or KEY_PREFIX.startswith(GUARDED_PREFIXES):
        raise SystemExit(f"{KEY_PREFIX} sits under a guarded prefix")
    if len(band_table()) != BANDS_N:
        raise SystemExit(f"the band rule does not give the declared {BANDS_N} bands")
    if sum(RENDERS.values()) != sum(SV.RENDERS.values()):
        raise SystemExit("the floors' renders are not the sound-gap test's 478")


def fault_why(ivs, checks):
    """(Pure.) A fault behind XE-anomaly, or None: a check fails, or a C or R of the EQ steps has no usable interval or
    reading (amendment 1 of the earlier tables: a malformed interval is an anomaly)."""
    for c in CHECKS:
        if (checks or {}).get(c) is not True:
            return f"the check {c} does not hold"
    for t in READ_TERMS:
        if reading((ivs or {}).get(t)) is None:
            return f"{t} has no usable interval or reading"
    return None


def surprises_of(rd):
    """(Pure.) Amendment 3's surprises (real outcomes, not faults), in table order: a C or R of the EQ steps reading
    better, and C_part closing. rd: {term: reading}."""
    out = [f"{t} reads better" for t in READ_TERMS if rd.get(t) == "better"]
    if rd.get("C_part") == "worse":
        out.append("C_part reads worse (closes)")
    return out


def rest_code(rd):
    """(Pure.) What the rest of the table gives (XE-group onward), the first that holds. rd: {term: reading}."""
    if rd.get("R_group") == "matches":
        return "XE-group"
    if rd.get("R_win") == "matches" and rd.get("R_group") == "worse":
        return "XE-window"
    if rd.get("C_win") == "worse" and rd.get("R_win") == "worse":
        return "XE-split"
    if rd.get("R_win") == "worse" and rd.get("C_win") == "matches":
        return "XE-detail"
    return "XE-undecided"


def _fmt(x):
    return f"{x:+.3f}" if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else "n/a"


def xe_code(ivs, checks):
    """(Pure.) XE_TABLE's one code, the first that holds, on the 40: `paired_reading` of C_k and R_k (k in part, group,
    win). With XE-anomaly from a surprise (no fault) or XE-static, `then` holds the code the rest of the table gives
    (amendment 3); `flags` the beside labels, never changing the code. ivs: {C_part, R_part, C_group, R_group, C_win,
    R_win: interval}; checks: {CHECKS: bool}. -> dict."""
    ivs = dict(ivs or {})
    fault = fault_why(ivs, checks)
    rd = {t: _r(ivs.get(t)) for t in READ_TERMS}
    surp = surprises_of(rd)
    better = [s for s in surp if s.endswith("better")]
    rest = rest_code(rd)
    if fault or better:
        code = "XE-anomaly"
    elif rd["C_part"] == "worse":
        code = "XE-static"
    else:
        code = rest
    then = rest if code in SURPRISE_CODES and not fault else None
    row = next(r for r in XE_TABLE if r[0] == code)
    note = ("; " + WINDOW_GROUP_UNDECIDED if code == "XE-undecided" and rd["R_win"] == "matches"
            and rd["R_group"] == "undecided" else "")
    tt = f"; the rest of the table gives {then}" if then else ""

    def ends(t):
        iv = ivs.get(t) if iv_ok(ivs.get(t)) else {}
        return _fmt(iv.get("lo90")), _fmt(iv.get("hi90"))
    (rw_lo, rw_hi), (rg_lo, rg_hi), (cw_lo, cw_hi) = ends("R_win"), ends("R_group"), ends("C_win")
    flags = [WINDOW_ARTEFACT] if rd["R_group"] == "matches" and rd["R_win"] == "worse" else []
    if note:
        flags.append(WINDOW_GROUP_UNDECIDED)
    return {"code": code, "when": row[1], "said": row[2].format(then=tt, c_group=rd["C_group"], note=note),
            "decides": row[3].format(rw_lo=rw_lo, rw_hi=rw_hi, rg_lo=rg_lo, rg_hi=rg_hi, cw_lo=cw_lo, cw_hi=cw_hi),
            "anomaly": fault or ("; ".join(better) if better else None), "fault": fault, "surprises": surp,
            "then": then, "flags": flags, "readings": {t: reading(ivs.get(t)) for t in READ_TERMS}}


# --- the term arithmetic (pure) ---------------------------------------------------------------------------------------

def finite_pos(v):
    return SV.finite_pos(v)


def part_terms(d):
    """(Pure.) One part's terms from its floors d ({guitar: held}): S, C_k, R_k as ln(num / den), None where a floor
    is missing, zero or non-finite."""
    out = {}
    for t, a, b in TERMS:
        x, y = (d or {}).get(a), (d or {}).get(b)
        out[t] = math.log(x / y) if finite_pos(x) and finite_pos(y) else None
    return out


def identity_gap(t, step):
    """(Pure.) |C_k + R_k - S| of one part's terms at a step, or None."""
    xs = [t.get(n) for n in (f"C_{step}", f"R_{step}", "S")]
    return None if any(x is None for x in xs) else abs(xs[0] + xs[1] - xs[2])


def step_set(step):
    return (BANK, OWN, GUITAR[step])


def term_values(floors):
    """(Pure.) floors: {pkey: {guitar: held}}. One passing set for the code: tr-di, vc-own and the three EQ guitars
    (DECIDING_SET); the beside steps each on their own (tr-di, vc-own and that guitar), so a beside refusal never moves
    the code. -> (values {term: {pkey: value}}, refused {pkey: reason} (the code's set), refused beside {step: {pkey:
    reason}}, identity gaps {step: {pkey: gap}} on each step's set)."""
    vals = {t: {} for t in TERM_NAMES}
    refused, beside = {}, {k: {} for k in SWAP_STEPS}
    gaps = {k: {} for k in STEPS}
    for k in sorted(floors):
        d = floors[k] or {}
        t = part_terms(d)
        bad = [g for g in DECIDING_SET if not finite_pos(d.get(g))]
        if bad:
            refused[k] = f"no finite positive floor for {', '.join(bad)}"
        else:
            vals["S"][k] = t["S"]
            for s in EQ_STEPS:
                vals[f"C_{s}"][k], vals[f"R_{s}"][k] = t[f"C_{s}"], t[f"R_{s}"]
                gaps[s][k] = identity_gap(t, s)
        for s in SWAP_STEPS:
            bs = [g for g in step_set(s) if not finite_pos(d.get(g))]
            if bs:
                beside[s][k] = f"no finite positive floor for {', '.join(bs)}"
                continue
            vals[f"C_{s}"][k], vals[f"R_{s}"][k] = t[f"C_{s}"], t[f"R_{s}"]
            gaps[s][k] = identity_gap(t, s)
    return vals, refused, beside, gaps


def identity_holds(gaps, tol=ID_TOL):
    """(Pure.) C_k + R_k = S per part on every step's passing set (each EQ step's set non-empty)."""
    return (all(gaps.get(s) for s in EQ_STEPS)
            and all(g is not None and g <= tol for s in STEPS for g in (gaps.get(s) or {}).values()))


def s_reproduces(s_now, s_rows, iv40, rows_iv):
    """(Pure.) S from the stored files: per part ln(d_tr-di / d_vc-own) equal to the sound-gap rows.json's per-part S
    (by tag), the 40's interval equal to rows.json's and to SEEN_S to 3 places. s_now, s_rows: {tag: value}."""
    per = bool(s_rows) and sorted(s_now) == sorted(s_rows) and all(s_now[k] == s_rows[k] for k in s_rows)
    exact = iv_ok(iv40) and iv_ok(rows_iv) and all(iv40[q] == rows_iv[q] for q in ("mean", "lo90", "hi90"))
    seen = SV.close3(iv40, SEEN_S)
    return {"per_part": per, "stored": exact, "seen": seen, "holds": per and exact and seen, "iv": iv40}


def proof_failures(proofs, names=PROOFS):
    """(Pure.) The failing proofs' names, in order (a missing proof fails; only True holds)."""
    return [k for k in names if (proofs or {}).get(k) is not True]


# --- the guards ----------------------------------------------------------------------------------------------------------

def tag(pk):
    return SV.tag(pk)


def own_keys(entry):
    """(Pure.) These steps' own keys of a `preset-ladder` entry."""
    return {k: v for k, v in (entry or {}).items() if k.startswith(KEY_PREFIX)}


def keys_refusal(local, main):
    """(Pure.) Why this checkout's `phase_scratch_envelope*` keys are not main's, or None."""
    a, b = own_keys(local), own_keys(main)
    if a != b:
        return f"this checkout's {sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))} differ from main's"
    return None


def outcome_refusal(m):
    """(Pure.) Why the steps may not run on main's entry, or None: the vc-own search row's audited code must be
    XW-closed or XW-part (its declaration's "deferred" call; XW-undecided would need the user's word first)."""
    out = (m or {}).get(SO.PHASE_OUTCOME)
    code = out.get("code") if isinstance(out, dict) else None
    if code not in OWN_OPEN:
        return f"main's {SO.PHASE_OUTCOME} code is {code!r}: the envelope steps run only under {list(OWN_OPEN)}"
    return None


BASE = (S.PHASE, S.PHASE_DRAW, S.phase_answers(SV.STEM_ROW), SE.PHASE_TARGETS, SV.PHASE_DRY, SV.PHASE_OUTCOME,
        SO.PHASE_OUTCOME, PHASE)
PHASES = {"build": (), "floor": (PHASE_DRY,), "read": (PHASE_DRY,)}


def pinned_identity():
    """Each of CODE_FILES equal to origin/main's (git diff --quiet). -> {file: same}."""
    return {f: SV._git("diff", "--quiet", "origin/main", "--", f).returncode == 0 for f in CODE_FILES}


def require_envelope(*phases):
    """Refuse unless the table holds, this checkout runs main's search (`scratch_search.require_on_main`), this module,
    its units and the pinned files are main's, the `phase_scratch_envelope*`, `phase_scratch_own*` and
    `phase_scratch_voice*` keys are main's, main holds the draw, row (b)'s answers, the stored floors, the voice build's
    hash, the sound-gap read, the vc-own row's read under XW-closed or XW-part, this declaration and `phases`.
    -> main's `preset-ladder` entry."""
    from learn import note_replay as NRP

    table_guard()
    m = S.require_on_main(*BASE, *phases)
    bad = [f for f, ok in pinned_identity().items() if not ok]
    if bad:
        raise SystemExit(f"this checkout's {bad} differ from main's: run from merged code")
    local = NRP.ledger_entry()
    why = keys_refusal(local, m) or SO.keys_refusal(local, m) or SV.keys_refusal(local, m) or outcome_refusal(m)
    if why:
        raise SystemExit(why)
    return m


# --- paths ------------------------------------------------------------------------------------------------------------------

def envelope_dir():
    """PF/fs/envelope/ (scratch_own's search never opens it)."""
    return S.fs_dir() / "envelope"


def build_path():
    return envelope_dir() / "build.json"


def part_path(pk):
    return envelope_dir() / "build-parts" / f"{SE._f(pk)}.json"


def dry_path(guitar, pk):
    if guitar not in BUILT:
        raise ValueError(guitar)
    return envelope_dir() / "dry" / guitar / f"{SE._f(pk)}.npy"


def floor_path(pk):
    return envelope_dir() / "floors" / f"{SE._f(pk)}.json"


def first_path(pk):
    return envelope_dir() / "floors-first" / f"{SE._f(pk)}.json"


def repeat_path(pk):
    return envelope_dir() / "repeat" / f"{SE._f(pk)}.json"


def rows_path():
    return envelope_dir() / "rows.json"


def report_path():
    return envelope_dir() / "report.json"


# --- the stored floors (tr-di's and vc-own's) --------------------------------------------------------------------------------

def stored_floors(m, keys):
    """tr-di's stored floor (the exact-notes floors.json, main's phase_scratch_exact_targets) and vc-own's (the
    sound-gap floor records, each file's sha256 the sound-gap rows.json's, its sha256 main's phase_scratch_voice_outcome)
    per part. -> ({pkey: {tr-di: {held, audio_sha256}, vc-own: {held, audio_sha256}}}, the sound-gap rows.json)."""
    from learn import voice_control as VC

    stored, _iv = SV._stored_floors(m)
    rows = VC._voice_rows(m)
    if sorted(stored) != sorted(keys):
        raise SystemExit("the stored floors do not cover the draw's parts")
    recs = {}
    for k in keys:
        if not SV.floor_path(k).exists():
            raise SystemExit(f"{tag(k)}: no sound-gap floor record")
        recs[k] = (json.loads(SV.floor_path(k).read_text()), S.file_sha(SV.floor_path(k)))
        if not finite_pos((stored[k].get(BANK) or {}).get("held")):
            raise SystemExit(f"{tag(k)}: the stored tr-di floor is not finite and positive")
    own = VC.own_floors(rows, recs)
    return ({k: {BANK: {"held": stored[k][BANK]["held"], "audio_sha256": stored[k][BANK].get("audio_sha256")},
                 OWN: own[k]} for k in keys}, rows)


def envelope_build(m):
    """build.json, refused unless its sha256 is main's phase_scratch_envelope_dry and its proofs held."""
    from learn import note_transcribe as NT

    if not build_path().exists():
        raise SystemExit("no envelope build.json (`envelope_build build` first)")
    b = NT.require_file_hash(m, PHASE_DRY, build_path())
    if b.get("proofs_hold") is not True:
        raise SystemExit("the envelope build's proofs did not hold")
    return b


# --- the read (zero renders) -----------------------------------------------------------------------------------------------

def floors_of(stored, recs, build):
    """Per part {guitar: held} over the seven guitars: the stored tr-di and vc-own floors and the envelope records.
    Refuses (SystemExit) a record that sets a guitar outside BUILT, whose guitar was not rendered from the build's
    (dry_sha256), or whose floor is missing, non-finite or not positive without `refused`. -> ({pkey: {guitar: held or
    None}}, {pkey: {guitar: reason}})."""
    out, why = {}, {}
    for k, st in stored.items():
        d = {}
        for g in STORED:
            h = (st.get(g) or {}).get("held")
            d[g] = h if finite_pos(h) else None
            if d[g] is None:
                why.setdefault(k, {})[g] = f"the stored {g} floor is not finite and positive ({h!r})"
        gs = (recs.get(k) or {}).get("guitars") or {}
        if sorted(gs) != sorted(BUILT):
            raise SystemExit(f"part {tag(k)}: an envelope floor record sets {sorted(gs)}, not {sorted(BUILT)}")
        for g, r in gs.items():
            if r.get("dry_sha256") != build["parts"][k]["guitars"][g]["audio_sha256"]:
                raise SystemExit(f"part {tag(k)}: {g}'s floor was not rendered from the envelope build's guitar")
            if r.get("refused"):
                d[g] = None
                why.setdefault(k, {})[g] = r["refused"]
            elif finite_pos(r.get("held")):
                d[g] = r["held"]
            else:
                raise SystemExit(f"part {tag(k)}: {g}'s floor {r.get('held')!r} is not finite and positive and is "
                                 "not marked refused: a malformed floor record, to the user")
        out[k] = d
    return out, why


def _span(xs):
    xs = [x for x in xs if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)]
    return [min(xs), max(xs)] if xs else None


def _median(xs):
    xs = [x for x in xs if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)]
    return statistics.median(xs) if xs else None


def error_summary(parts, keys):
    """(Pure.) The realised error beside, over `keys`: per step and side (intent, target) the median and the range of
    the parts' median and 90th-percentile |error|, the clamped and floored shares' medians, spectral convergence's
    (the swaps) and the level change's. parts: build.json's per-part records."""
    out = {}
    for s in STEPS:
        g = GUITAR[s]
        e = [((parts.get(k) or {}).get("error") or {}).get(g) or {} for k in keys]
        row = {}
        for side in ("intent", "target"):
            for f in ("median_abs_db", "p90_abs_db"):
                xs = [(x.get(side) or {}).get(f) for x in e]
                row[f"{side}_{f}"] = {"median": _median(xs), "range": _span(xs)}
        for f in ("clamped_share", "floored_share"):
            row[f] = _median([(x.get("intent") or {}).get(f) for x in e])
        row["level_change_db"] = _span([x.get("level_change_db") for x in e])
        if s in SWAP_STEPS:
            row["spectral_convergence"] = {"median": _median([x.get("spectral_convergence") for x in e]),
                                           "range": _span([x.get("spectral_convergence") for x in e])}
        out[g] = row
    return out


def read_body(vals, refused, beside_refused, gaps, iv_fn, deciding, clusters, checks, share_fn=None, neg_d=None):
    """(Pure but for `iv_fn` and `share_fn`.) The read: each term's interval on the 40 (`iv_fn(values, keys)`, BKS+GOAT's
    pool; keys None: all), XE_TABLE's code on the code's passing set with S1 beside (the intent-to-treat code, a refused
    part at 0.0: `refusal-sensitive` when they differ), each cluster of the 40 left out, the three largest parts,
    Fieller's C_k / S, Spearman of C_group and C_win with -D_own (neg_d by tag). -> dict."""
    dec = sorted(k for k in deciding if k not in refused)
    ivs = {t: iv_fn(vals[t], None) for t in TERM_NAMES}
    code = xe_code({t: ivs[t] for t in READ_TERMS}, checks)
    itt_ivs = {t: iv_fn(S.itt_values(vals[t], refused), None) for t in READ_TERMS}
    itt_code = xe_code(itt_ivs, checks)
    code, itt_rec, s1 = SV.with_itt(code, itt_code, refused)
    left = {t: [iv_fn(vals[t], set(dec) - set(c)) for c in clusters] for t in TERM_NAMES}
    rng = {t: ([min(x["mean"] for x in v if iv_ok(x)), max(x["mean"] for x in v if iv_ok(x))]
               if any(iv_ok(x) for x in v) else None) for t, v in left.items()}
    big = {}
    for t in READ_TERMS + ("S",):
        top = SV.largest(vals[t], dec)
        big[t] = {"tags": [tag(k) for k in top], "values": [vals[t][k] for k in top],
                  "without": iv_fn(vals[t], set(dec) - set(top))}
    share = {t: (share_fn(vals[t], vals["S"]) if share_fn else None) for t in ("C_part", "C_group", "C_win")
             + ("C_mag", "C_phase")}
    ranks = {}
    for t in ("C_group", "C_win"):
        ks = [k for k in dec if vals[t].get(k) is not None and isinstance((neg_d or {}).get(tag(k)), (int, float))]
        rho = SV.spearman([vals[t][k] for k in ks], [neg_d[tag(k)] for k in ks]) if neg_d else None
        ranks[t] = {"rho": NOT_COMPUTABLE if rho is None else rho, "parts": len(ks)}
    return {"passing_parts_on_the_40": len(dec), "refused": sorted(tag(k) for k in refused),
            "refused_beside": {s: sorted(tag(k) for k in v) for s, v in beside_refused.items()},
            "terms": ivs, "readings": {t: reading(ivs.get(t)) for t in TERM_NAMES}, "code": code["code"], "xe": code,
            "then": code.get("then"), "flags": code.get("flags"),
            "itt": {"terms": itt_ivs, "xe": itt_rec} if itt_rec else None, "label": s1,
            "identity_max_gap": {s: max((g for g in (gaps.get(s) or {}).values() if g is not None), default=None)
                                 for s in STEPS},
            "cluster_left_out": left, "cluster_left_out_range": rng, "largest_three": big,
            "share_of_S": share, "share_label": "Fieller's C_k / S on the 40, beside",
            "ranks_with_minus_D_own": ranks, "ranks_label": "Spearman on the 40 against fs-own's -D_own; beside"}


def cmd_read(_args):
    """The read (zero renders), once: build.json (main's phase_scratch_envelope_dry), every part's floor record (no
    pending rerun) and the repeat check; S reproduced from the stored files against the sound-gap rows.json; the
    terms; XE_TABLE's code (with `then` and the flags) and S1; beside: vt-mag and vt-phase with their realised error,
    Fieller's C_k / S, vc-env's stored E1, clean and crunch, each cluster left out, the three largest parts, all 47,
    Spearman of C_group and C_win with -D_own. The rows are saved before the code. Part keys appear only as 12-hex
    tags. -> rows.json, report.json."""
    m = require_envelope(*PHASES["read"])
    from learn import note_transcribe as NT
    from learn import pipeline_fix as P
    from learn import voice_floors as VF

    for p_ in (rows_path(), report_path()):
        NT.never_overwrite(p_)
    build = envelope_build(m)
    draw, sd = SE.context()
    keys = sorted(p["pkey"] for p in draw["parts"])
    if len(keys) != PARTS or sorted(build.get("parts") or {}) != keys:
        raise SystemExit("the draw and the envelope build do not cover the same parts")
    st, rows_v = stored_floors(m, keys)
    recs = {}
    for k in keys:
        if not floor_path(k).exists():
            raise SystemExit(f"part {tag(k)}: no envelope floor record (`envelope_floors floor` first)")
        recs[k] = json.loads(floor_path(k).read_text())
    pend = SV.pending_reruns(recs)
    if pend:
        raise SystemExit(f"{len(pend)} refused render(s) not rerun once: `envelope_floors floor --rerun` first")
    reps = {k: VF._read(repeat_path(k)) for k in SV.check_parts(draw["parts"])}

    def iv_fn(vals, ks=None):
        r = SN.set_rows(sd, draw, {k: v for k, v in vals.items() if v is not None and math.isfinite(v)}, ks)
        return ((r or {}).get("bks_goat") or {}).get("all")

    def share_fn(num, den):
        return SE.share(sd, draw, num, den)

    s_now = {k: SV.part_terms_pair({BANK: st[k][BANK]["held"], OWN: st[k][OWN]["held"]}, BANK, OWN) for k in keys}
    vr = rows_v.get("rows") or {}
    sr = s_reproduces({tag(k): v for k, v in s_now.items()}, (vr.get("per_part") or {}).get("S"), iv_fn(s_now),
                      (vr.get("terms") or {}).get("S"))
    floors, refused_why = floors_of(st, recs, build)
    vals, refused, beside_refused, gaps = term_values(floors)
    checks = {"proofs": build.get("proofs_hold") is True,
              "repeat": len(reps) == CHECK_PARTS and all(r and r.get("holds") is True for r in reps.values()),
              "s_reproduces": sr["holds"], "identity_holds": identity_holds(gaps)}
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    deciding = [k for k in keys if sets_of[k] in DECIDING]
    clusters = {}
    for p in draw["parts"]:
        if p["set"] in DECIDING:
            clusters.setdefault(p["cluster"], []).append(p["pkey"])
    own_rows, own_why = SO._hashed_rows(m, SO.rows_path(), SO.PHASE_OUTCOME, "rows_sha256")
    neg_d = {t: -v for t, v in ((own_rows or {}).get("D_own") or {}).items() if isinstance(v, (int, float))}
    body = read_body(vals, refused, beside_refused, gaps, iv_fn, deciding,
                     [sorted(v) for _, v in sorted(clusters.items())], checks, share_fn, neg_d or None)
    body["ranks_with_minus_D_own"]["source"] = own_why or "fs-own's rows.json"

    def rows_on(field):
        return {t: (((SN.set_rows(sd, draw, v) or {}).get("bks_goat") or {}).get(field)) for t, v in vals.items()}
    beside = {"all_47": {t: ((SN.set_rows(sd, draw, v) or {}).get("deciding_pool")) for t, v in vals.items()},
              "clean": rows_on("clean"), "crunch": rows_on("crunch"),
              "swaps": {GUITAR[s]: {"C": body["terms"].get(f"C_{s}"), "R": body["terms"].get(f"R_{s}"),
                                    "label": "beside, never changing the code; not read as note content or string "
                                             "detail"} for s in SWAP_STEPS},
              "vc_env_E1": {"iv": (vr.get("terms") or {}).get("E1"),
                            "label": "vc-env's stored E1 (the sound-gap read): the level-only, one-band relative, "
                                     "built on the finished guitar with 20-ms frames; not a step"},
              "realised_error_40": error_summary(build["parts"], deciding),
              "realised_error_47": error_summary(build["parts"], keys)}
    common = {"plan": PLAN, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0, "checks": checks,
              "s_reproduced": sr, "build_sha256": S.file_sha(build_path()),
              "refused_why": {tag(k): v for k, v in refused_why.items()},
              "refusal_report": S.refusal_report({tag(k): refused_why.get(k) or {"floor": refused[k]} for k in refused},
                                                 {tag(k): v for k, v in sets_of.items()}, DECIDING),
              "floors_sha256": {tag(k): S.file_sha(floor_path(k)) for k in keys}}
    rows = dict(common, rows={"terms": body["terms"], "beside": beside,
                              "per_part": {t: {tag(k): v for k, v in vs.items()} for t, vs in vals.items()}})
    P.save(rows_path(), rows)                            # the rows are saved before the code is read
    report = dict(common, read=body, beside=beside)
    P.save(report_path(), report)
    for t in TERM_NAMES:
        print(f"{t} on the 40: {body['terms'].get(t)} -> {(body['readings'].get(t) or {}).get('reading')}")
    lab = ", ".join(x for x in [body["label"]] + list(body["flags"] or []) if x)
    then = f"; then {body['then']}" if body["then"] else ""
    print(f"XE READ: {body['code']}{' (' + lab + ')' if lab else ''}{then}: {body['xe']['said']}. Decides: "
          f"{body['xe']['decides']}; sha256 {S.file_sha(report_path())}")


COMMANDS = {"read": cmd_read}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
