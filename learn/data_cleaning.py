"""Cleaning the direct model's data (`docs/data-cleaning-options.md`, declared 2026-10-22, amendment 1 from the code
review; the user's rule of 2026-10-22: use only what we can trust, no dirty tracks). Development data only; no
held-out data. Step 0 (zero renders, CPU) declares the trusted sets; a candidate list made from it drives every
rebuild, so a listening verdict changes R_in and the pool alike. Step 1 (zero renders) rebuilds the R_in examples
the list touches and reads step 3's D_stem (F) on rebuilt against re-separated original stems of the same examples.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    MSST=~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN     -m learn.data_cleaning inject                   # 0a: INJECTION OK | FAIL (gates 0b; never overwritten)
    $MAIN     -m learn.data_cleaning scan --shard k/3         # 0b: per section and kept track: take level, same part
    $MAIN     -m learn.data_cleaning lists                    # 0c: trusted lists, counts, route (drop | rebuild)
    $MAIN     -m learn.data_cleaning pool-candidates          # the candidate list (guitar doubles on, the rest pending)
    $MSST     -m learn.data_cleaning rin-rebuild --device mps # 1a: R_in rebuilt + re-made originals, X-LANCE
    $TORCH_PY -m learn.data_cleaning rin-read                 # 1b: F on rebuilt vs re-separated original (paired)
    $MSST     -m learn.data_cleaning pool-rebuild --device mps --order asc   # 2 (data): renders + X-LANCE
    $MSST     -m learn.data_cleaning pool-rebuild --device cpu --order desc  # optional second worker
    $MAIN     -m learn.data_cleaning pool-status              # 2 (data): what the list asks for; the manifest
    $MSST     -m learn.data_cleaning bleed-test --device mps  # decision memo: the bleed-injection test (after pool-rebuild)
    $TORCH_PY -m learn.data_cleaning bleed-read               # its readout: F on injected vs clean stems

**The take level** of a kept backing track in a section is the energy of the target's original take in
it, in dB of the original take's own close-mic (amp) track. It does not depend on the example's level
draw (removal is per section, never per example, so no level filter comes back).
- **A confirmed same-part track** (another take of the target's part): its whole power in the section counts
  (the larger half). Candidates: Cambridge "DT" naming, onset correlation with the DI >= 0.6 in the section,
  or onsets that follow the DI at least as well as the own amp track does. **Confirmed by pitch:** chroma
  similarity with the own amp track (the DI when there is none) >= 0.70 in the section, the weakest own pair
  of the label table (0.696).
- **Any other track:** a session-level reading (a room path does not change between sections): the
  held-out energy a per-bin complex ridge regression on the own amp track (lags -1..6 STFT frames,
  24 kHz, 2048/1024, 250 Hz-8 kHz, ridge 0.3) explains over the whole session in 10 contiguous folds,
  on frames where the amp plays, less the mean of four nulls (the source rolled +-2 and +-3 s), in dB
  of the amp's energy, never above the track's own. The amp source decides (an upper bound: a live amp
  track's own drum bleed can pose as take); the DI-source reading is reported beside. Takes under -40 dB
  count as none. Parts without an amp track have no original take: only confirmed same-part tracks count.
- **The rule (one threshold, as the amp-track targets' "low" bleed flag):** remove the fewest tracks,
  largest take first, until the section's summed take is <= -30 dB. An example is untrusted iff its
  own backing variant (with or without vocals) loses a track.
- **The estimator is validated first** (`inject`, amendment 1): per clean Cambridge session, a room-filtered
  copy of the own amp track is injected at -20, -25 and -30 dB into each kept drum, room and overhead track in
  turn. A session passes if, at every level, >= 80% of its targets (and of its room/overhead ones) read back
  (within 3 dB at -20 and -25, >= -33 dB at -30) and >= 90% read under -35 dB uninjected. INJECTION OK needs
  every deciding session (the 3 the estimator was not developed on) to pass, a room/overhead target among
  them, and <= 5% of their other non-guitar tracks at or above -30 dB. The development sessions are read
  beside. `scan` refuses unless the record is real, OK, made under the current rule, and holds exactly the
  declared deciding sessions; `inject` never overwrites a record.

**The candidate list** (`pool-candidates`): one entry per removed (DI, track, kind). Guitar-class doubles are
on; every other candidate (non-guitar doubles, live-room takes) is off and pending: its examples are
excluded, not read as original, until a verdict keeps the track or switches it on.

**Step 1 (no target renders):** the gate's 1,407 stored truth renders (FLAC, hash-checked) are each
example's rendered guitar. The original mix is re-made from it with the stored draw and must match
the stored mix mels (99% of cells within one 0.5-dB step, half LUFS within 0.01) or the example is
refused. The rebuilt mix drops the list's switched-on tracks from the example's backing, keeps the
ratio, vocals, loudness and mastering draws (the backing is rescaled to the same ratio), and is
separated by X-LANCE gtr_mss on MPS; so is the re-made original (the null: the stored stems were made
partly on the CPU from rendered mixes). Files are keyed by the removed tracks; rows under another key
are never read. `rin-read` scores F (3 seeds; the 2-seed pair beside) with step 3's stored constant and
pull (amendment 5's A1+A2+A3, masked E).

**Step 2's data (no training here).** `pool-rebuild` re-renders each pool example the list wants rebuilt
(isolate=True, primed, at most 3 render processes machine-wide), checks its original mix against the stored
one, rebuilds the mix without the tracks and separates it; files and rows carry the removal key, beside the
D build's untouched originals. `pool-status` shows the difference after a verdict (to build; stale, read as
original again; excluded: refused or pending) and writes the manifest that arm T would read.

The pure parts are unit-tested (`tests/test_data_cleaning.py`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import random
import re
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/data-cleaning"
PLAN = "docs/data-cleaning-options.md"
LEDGER_ID = "data-cleaning"

# --- the take estimator (declared) ------------------------------------------------------------------
AN_SR = 24_000
NFFT, HOP = 2048, 1024
BAND = 1                                   # one complex weight per bin and lag (a delayed path rotates phase across bins)
LAGS = (-1, 0, 1, 2, 3, 4, 5, 6)           # STFT frames (42.7 ms each): about -43..+256 ms
F_LO, F_HI = 250.0, 8000.0                 # above the kick and bass fundamentals, where riffs phase-lock
RIDGE = 0.3                                # relative to the bin's mean diagonal
FOLDS = 10                                 # cross-validation: contiguous blocks of the whole session
ACTIVE_DB = 40.0                           # frames counted: the reference within 40 dB of its loudest
NULL_S = (2.0, 3.0)                        # the nulls roll the source by +-2 and +-3 s (past the lags, and
                                           # close enough to keep the music's structure: the chance level)
HALF_SPANS = {"A": (1.0, 5.5), "B": (5.5, 10.0)}   # seconds into the 10-s section (pretrain_set.HALVES)
SEC_S = 10.0

# --- the rule (declared) ----------------------------------------------------------------------------
TAKE_DB = -30.0                            # one threshold, as the amp-track targets' "low" bleed flag
FLOOR_DB = -40.0                           # a track's take under this counts as none
SENS_DB = (-25.0, -20.0)                   # descriptive only: counts at looser thresholds
CHROMA_MIN = 0.70                          # same part, by pitch: the label table's weakest own pair (0.696)
ONSET_MIN = 0.60                           # a same-part candidate by onsets (the audit's di_match rule)
DROP_MAX_SHARE = 0.05                      # route: drop if at most 5% of the pool is untrusted, else rebuild

# --- the injection check (declared) -----------------------------------------------------------------
# Amendment 1 (code review, 2026-10-22): the check votes per session, the sessions the estimator was not developed
# on decide, and the take is injected into every drum, room and overhead track (room mics are the hard case).
INJECT_SEED = 20261097
INJECT_DB = (-20.0, -25.0, -30.0)
INJECT_TOL_DB = 3.0
INJECT_DETECT_DB = -33.0                   # at -30 dB the reading must reach at least this
INJECT_BASE_DB = -35.0                     # an uninjected drum/room track must read under this
INJECT_TRACK_NEED = 0.8                    # per session and level: share of its targets (and of its room ones) read back
INJECT_BASE_NEED = 0.9                     # per session: share of its targets whose uninjected reading is under -35 dB
INJECT_FP_MAX = 0.05                       # pooled over the deciding sessions: other non-guitar tracks at or above -30
INJECT_DECIDING = ("HollowGround_IllFate_Full", "RebuildTheEvil_BurialOfSilence_Full", "TheLongWait_Drag_Full")
CLEAN_EXCESS = 0.002                       # injection sessions: Cambridge, every kept track's coherence <= this
ROOM_RE = re.compile(r"room|\boh\b|overhead|amb", re.I)
# The estimator's settings (250 Hz floor, per-bin weights, ridge 0.3, session-level folds, nulls at +-2/3 s, the clip
# at the track's power) were chosen in smoke runs on these 4 DIs, from 3 sessions (Ale Lak, Death Of A Romantic, Storm
# Of Particles). Those sessions are read beside the check; only the other clean sessions (INJECT_DECIDING) decide.
DEV_DIS = ("cambridge/AleLak_NossoMundoDeixouDeExistir_Full/20_ElecGtr04DI.wav",
           "cambridge/AleLak_NossoMundoDeixouDeExistir_Full/22_ElecGtr04DTDI.wav",
           "cambridge/DeathOfARomantic_TheWell_Full/DeathOfARomantic_TheWell_Full/14_ElecGtr02DI.wav",
           "cambridge/StormOfParticles_OfIceAndHopelessFate_Full/StormOfParticles_OfIceAndHopelessFate_Full/"
           "17_ElecGtr05DI.wav")

# --- step 1 -------------------------------------------------------------------------------------------
STEP_SEP = "xlance_g"
DISK_GUARD_GB = 31.0
EXPECT_SECTIONS = 332                      # 277 pool + 55 V_sep sections (the D build's rows)

DRUM_RE = re.compile(r"kick|snare|hat|tom|\boh\b|overhead|ride|cymbal|crash|drum|room|perc|spdx|clap|shaker", re.I)
BASS_RE = re.compile(r"bass", re.I)
VOX_RE = re.compile(r"vox|vocal|voc\b|harm", re.I)
GTR_RE = re.compile(r"gtr|guitar", re.I)
KEYS_RE = re.compile(r"key|piano|synth|organ|leslie|rhodes|wurli|pad|string", re.I)


# --- pure: names --------------------------------------------------------------------------------------

def track_class(name):
    """A coarse class from the file name, for reporting only (never for the rule)."""
    s = pathlib.PurePosixPath(name).stem
    if VOX_RE.search(s):
        return "vocal"
    if BASS_RE.search(s):
        return "bass"
    if GTR_RE.search(s):
        return "guitar"
    if KEYS_RE.search(s):
        return "keys"
    if DRUM_RE.search(s):
        return "drums"
    return "other"


def part_base(name):
    """A track's part name: no leading take number, extension, or trailing Amp/Mic/DI suffix."""
    s = pathlib.PurePosixPath(name).stem
    s = re.sub(r"^\d+_", "", s)
    s = re.sub(r"(Amp\d*|Mic\d*|DI)$", "", s)
    return s.strip(" _")


def name_partner(part, track):
    """Cambridge's double-track naming: one name is the other's with "DT" added (ElecGtr01 <-> ElecGtr01DT)."""
    t = part_base(track)
    if not part or not t or t == part:
        return False
    return (t == part + "DT") or (part == t + "DT")


# --- pure: the rule -------------------------------------------------------------------------------------

def db_sum(levels):
    """Power sum of dB levels (-inf for none; +inf stays +inf)."""
    tot = 0.0
    for v in levels:
        if v == math.inf:
            return math.inf
        tot += 10 ** (v / 10)
    return 10 * math.log10(tot) if tot > 0 else -math.inf


def removal(levels, thr=TAKE_DB, floor=FLOOR_DB):
    """The fewest tracks, largest take first, whose removal brings the section's summed take to <= thr.
    levels: {track: dB, +inf or None}; takes under `floor` count as none.
    -> (removed tracks, summed take before, after)."""
    items = sorted(((v, t) for t, v in levels.items() if v is not None and v >= floor),
                   key=lambda vt: (-vt[0], vt[1]))
    before = db_sum(v for v, _ in items)
    removed = []
    while items and db_sum(v for v, _ in items) > thr:
        removed.append(items.pop(0)[1])
    return removed, before, db_sum(v for v, _ in items)


def same_part(chroma, onset, onset_own, partner, cmin=CHROMA_MIN, omin=ONSET_MIN):
    """A same-part track: a candidate (naming, onsets >= omin, or onsets following the DI at least as
    well as the own amp track does) confirmed by pitch (chroma >= cmin)."""
    if chroma is None or chroma < cmin:
        return False
    cand = bool(partner) or (onset is not None and onset >= omin) or (
        onset is not None and onset_own is not None and onset >= onset_own)
    return cand


def track_take(rec, has_amp):
    """A scanned track's take for the rule: a confirmed same-part track's power in the section (the larger
    half; any level when the part has no amp track), else the session-level take read against the own amp
    track (none without an amp track: no original take was recorded through an amp)."""
    if rec.get("same_part"):
        return max_half(rec.get("power_db")) if has_amp else math.inf
    return rec.get("take_amp_db") if has_amp else None


def max_half(d):
    """The larger of a {half: dB or None} reading (None if neither)."""
    if not d:
        return None
    vals = [v for v in d.values() if v is not None]
    return max(vals) if vals else None


def section_decision(row, thr=TAKE_DB, floor=FLOOR_DB):
    """(removed, before, after) of one scanned section."""
    has_amp = row["source"]["kind"] == "amp"
    levels = {t: track_take(rec, has_amp) for t, rec in row["tracks"].items()}
    return removal(levels, thr, floor)


def touched(removed, variant_tracks):
    """An example is untrusted iff its own backing variant loses a track."""
    return bool(set(removed) & set(variant_tracks))


def route(share, max_share=DROP_MAX_SHARE):
    return "drop" if share <= max_share else "rebuild"


def is_room(name):
    return bool(ROOM_RE.search(pathlib.PurePosixPath(name).stem))


def readback_ok(level, reading, levels=INJECT_DB, tol=INJECT_TOL_DB, detect=INJECT_DETECT_DB):
    """An injected take read back: within tol at the louder levels, at least `detect` at the threshold level."""
    if reading is None:
        return False
    return reading >= detect if level == min(levels) else abs(reading - level) <= tol


def session_verdict(row, levels=INJECT_DB, need=INJECT_TRACK_NEED, base_need=INJECT_BASE_NEED,
                    base_max=INJECT_BASE_DB):
    """One session's vote. row["targets"]: {track: {"room": bool, "base": dB|None, "inj": {level: dB|None}}}.
    It passes iff at every level >= need of its targets read back, and >= need of its room/overhead targets
    (when it has any), and >= base_need of its targets read under base_max uninjected.
    -> (pass, {level: (share, room share or None)}, base share)."""
    tg = row.get("targets") or {}
    if not tg:
        return False, {}, 0.0
    shares, good = {}, True
    for L in levels:
        ok = {t: readback_ok(L, r["inj"].get(L), levels) for t, r in tg.items()}
        rooms = [ok[t] for t, r in tg.items() if r.get("room")]
        sh = sum(ok.values()) / len(ok)
        rs = sum(rooms) / len(rooms) if rooms else None
        shares[L] = (sh, rs)
        good &= sh >= need - 1e-9 and (rs is None or rs >= need - 1e-9)
    base = sum(r["base"] is None or r["base"] < base_max for r in tg.values()) / len(tg)
    return good and base >= base_need - 1e-9, shares, base


def injection_verdict(rows, fp_max=INJECT_FP_MAX, thr=TAKE_DB, deciding=INJECT_DECIDING):
    """INJECTION OK iff every deciding session (one row each, all present) passes its vote, the deciding sessions
    hold at least one room/overhead target, and at most fp_max of their other non-guitar tracks read at or above
    thr uninjected. Development sessions are read beside and never decide.
    -> (verdict, {session: pass}, false-positive share)."""
    dec = {r["session"]: r for r in rows if r.get("deciding")}
    votes = {k: session_verdict(r)[0] for k, r in dec.items()}
    others = [v for r in dec.values() for v in (r.get("others") or {}).values()]
    fp = sum(v is not None and v >= thr for v in others) / len(others) if others else 0.0
    rooms = sum(1 for r in dec.values() for t in (r.get("targets") or {}).values() if t.get("room"))
    good = (set(dec) == set(deciding) and all(votes.values()) and rooms > 0 and fp <= fp_max + 1e-9)
    return ("OK" if good else "FAIL"), votes, fp


def injection_rule():
    """The declared rule, stored with the record and checked by `scan`."""
    return {"levels": list(INJECT_DB), "tol_db": INJECT_TOL_DB, "detect_db": INJECT_DETECT_DB,
            "base_db": INJECT_BASE_DB, "track_need": INJECT_TRACK_NEED, "base_need": INJECT_BASE_NEED,
            "fp_max": INJECT_FP_MAX, "take_db": TAKE_DB, "deciding": list(INJECT_DECIDING), "seed": INJECT_SEED,
            "estimator": {"f_lo": F_LO, "f_hi": F_HI, "ridge": RIDGE, "folds": FOLDS, "lags": list(LAGS),
                          "null_s": list(NULL_S)}}


def injection_record_problem(rec, expected_dis):
    """None if an injection record lets `scan` run: real, OK, the current rule, and exactly the expected deciding
    sessions with their expected DIs; else the reason. expected_dis: {session: DI}."""
    if not rec:
        return "no injection record (run inject first)"
    if rec.get("smoke"):
        return "the injection record is a smoke test's"
    if rec.get("rule") != injection_rule():
        return "the injection record was made under another rule or estimator"
    rows = [{**r, "targets": {t: {**x, "inj": {float(L): v for L, v in x["inj"].items()}}
                              for t, x in (r.get("targets") or {}).items()}} for r in rec.get("rows") or []]
    got = {r["session"]: r["di"] for r in rows if r.get("deciding")}
    if got != expected_dis or len(got) != len(INJECT_DECIDING):
        return f"the record's deciding sessions differ from the declared ones: {sorted(got)}"
    if rec.get("verdict") != "OK" or injection_verdict(rows)[0] != "OK":
        return f"the injection check read {rec.get('verdict')}"
    return None


# --- pure: signals ----------------------------------------------------------------------------------------

def stft(x, nfft=NFFT, hop=HOP):
    """[bins, frames] complex64 of a Hann-windowed STFT (frames fully inside x)."""
    import numpy as np

    x = np.asarray(x, np.float32)
    n = max(0, (len(x) - nfft) // hop + 1)
    win = np.hanning(nfft).astype(np.float32)
    out = np.empty((nfft // 2 + 1, n), np.complex64)
    for j in range(0, n, 256):
        k = min(n, j + 256)
        idx = np.arange(j, k)[:, None] * hop + np.arange(nfft)[None, :]
        out[:, j:k] = np.fft.rfft(x[idx] * win, axis=1).T
    return out


def frame_times(n, t0=0.0, sr=AN_SR, nfft=NFFT, hop=HOP):
    """Centre time (s) of each STFT frame, starting at t0."""
    import numpy as np

    return t0 + (np.arange(n) * hop + nfft / 2) / sr


def band_bins(sr=AN_SR, nfft=NFFT, lo=F_LO, hi=F_HI, band=BAND):
    """(selected bin indices, band id per selected bin)."""
    import numpy as np

    f = np.fft.rfftfreq(nfft, 1 / sr)
    idx = np.where((f >= lo) & (f < hi))[0]
    return idx, (idx - idx[0]) // band


def lagged(S, lags=LAGS):
    """[bins, frames, lags]: S delayed by each lag (frames; zero-padded)."""
    import numpy as np

    F, N = S.shape
    X = np.zeros((F, N, len(lags)), np.complex64)
    for k, L in enumerate(lags):
        if L > 0:
            X[:, L:, k] = S[:, :N - L]
        elif L < 0:
            X[:, :N + L, k] = S[:, -L:]
        else:
            X[:, :, k] = S
    return X


class SessionMeter:
    """A source's ridge regression over a whole session, cross-validated in FOLDS contiguous blocks: per band
    and fold, (G_train + lambda I)^-1. `explained(Y)` is the held-out energy of Y the source explains
    (sum |Y|^2 - sum |Y - Yhat|^2), summed over the counted frames of every fold."""

    def __init__(self, S, counted, band, folds=None, lags=LAGS, ridge=RIDGE):
        import numpy as np

        folds = folds or FOLDS
        F, N = S.shape
        X = lagged(S, lags)
        self.XH = np.ascontiguousarray(np.conj(X).transpose(0, 2, 1))                 # [F, K, N]
        del X
        self.band, self.counted = band, counted
        cut = np.linspace(0, N, folds + 1).astype(int)
        self.blocks = [np.arange(cut[k], cut[k + 1]) for k in range(folds) if cut[k + 1] > cut[k]]
        nb, K = int(band.max()) + 1, len(lags)
        Gk = []
        for idx in self.blocks:
            xh = self.XH[:, :, idx]
            g = np.matmul(xh, np.conj(xh).transpose(0, 2, 1)).astype(np.complex128)
            gb = np.zeros((nb, K, K), np.complex128)
            np.add.at(gb, band, g)
            Gk.append(gb)
        tot = sum(Gk)
        self.inv = []
        for gb in Gk:
            g = tot - gb
            lam = ridge * np.real(np.einsum("bkk->b", g)) / K
            lam = np.where(lam > 0, lam, 1e-12)
            self.inv.append(np.linalg.inv(g + lam[:, None, None] * np.eye(K)[None]))

    def explained(self, Y):
        import numpy as np

        nb = self.inv[0].shape[0]
        rk = []
        for idx in self.blocks:
            r = np.matmul(self.XH[:, :, idx], np.ascontiguousarray(Y[:, idx])[:, :, None])[:, :, 0]
            rb = np.zeros((nb, r.shape[1]), np.complex128)
            np.add.at(rb, self.band, r.astype(np.complex128))
            rk.append(rb)
        tot = sum(rk)
        e = 0.0
        for idx, inv, rb in zip(self.blocks, self.inv, rk):
            m = idx[self.counted[idx]]
            if not len(m):
                continue
            W = np.einsum("bkl,bl->bk", inv, tot - rb)[self.band]
            yt = Y[:, m].astype(np.complex128)
            yh = np.einsum("fkn,fk->fn", np.conj(self.XH[:, :, m]).astype(np.complex128), W)
            e += float(np.sum(np.abs(yt) ** 2) - np.sum(np.abs(yt - yh) ** 2))
        return e


def take_db(real, nulls, ref):
    """10 log10((real - mean(nulls)) / ref): the held-out energy the source explains beyond what a rolled
    source explains by chance (the same overfitting bias), None if nothing is left."""
    e = real - (sum(nulls) / len(nulls) if nulls else 0.0)
    if e <= 0 or ref <= 0:
        return None
    return 10 * math.log10(e / ref)


def null_rolls(n_frames, null_s=NULL_S, sr=AN_SR, hop=HOP):
    """The nulls' rolls in frames: +-each of NULL_S (shorter sessions: at most a quarter of the session)."""
    out = []
    for t in null_s:
        k = min(int(round(t * sr / hop)), max(1, n_frames // 4))
        out += [k, -k]
    return out


def counted_frames(S_ref, active_db=ACTIVE_DB):
    """Frames where the reference plays: energy (selected bins) within active_db of its loudest frame."""
    import numpy as np

    e = np.sum(np.abs(S_ref) ** 2, axis=0)
    return e > e.max() * 10 ** (-active_db / 10) if e.size and e.max() > 0 else np.zeros(e.shape, bool)


class TakeReader:
    """Session-level take readings of many tracks against one source (and the reference it is read in)."""

    def __init__(self, S_src, S_ref):
        import numpy as np

        _, self.band = band_bins()
        self.counted = counted_frames(S_ref)
        self.ref = float(np.sum(np.abs(S_ref[:, self.counted]) ** 2))
        self.S, self.rolls = S_src, null_rolls(S_src.shape[1])

    def takes(self, Ys):
        """{name: dB or None} for {name: selected STFT}; one meter alive at a time (memory)."""
        import gc

        import numpy as np

        real, nulls = {}, {k: [] for k in Ys}
        for v, roll in enumerate([0] + self.rolls):
            meter = SessionMeter(np.roll(self.S, roll, axis=1) if roll else self.S, self.counted, self.band)
            for k, Y in Ys.items():
                e = meter.explained(Y)
                (nulls[k].append(e) if v else real.__setitem__(k, e))
            del meter
            gc.collect()
        out = {}
        for k, Y in Ys.items():
            t, pw = take_db(real[k], nulls[k], self.ref), self.power(Y)
            out[k] = None if t is None or pw is None else min(t, pw)        # a take never exceeds the track
        return out

    def power(self, Y):
        """dB of a track's energy against the reference's, over the counted frames."""
        import numpy as np

        e = float(np.sum(np.abs(Y[:, self.counted]) ** 2))
        return 10 * math.log10(e / self.ref) if e > 0 and self.ref > 0 else None


def onset_env(x, sr=AN_SR, nf=1024, hop=240):
    """The audit's onset strength: 24 log-spaced bands 80 Hz-8 kHz, rectified dB rise (floor 50 dB down)."""
    import numpy as np

    x = np.asarray(x, np.float32)
    if len(x) < nf:
        return np.zeros(0)
    fr = np.lib.stride_tricks.sliding_window_view(x, nf)[::hop] * np.hanning(nf)
    P = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(nf, 1 / sr)
    edges = np.geomspace(80, 8000, 25)
    B = np.stack([P[:, (f >= edges[k]) & (f < edges[k + 1])].sum(1) for k in range(24)], 1)
    E = 10 * np.log10(B + 1e-12)
    E = np.maximum(E, E.max() - 50)
    return np.maximum(np.diff(E, axis=0, prepend=E[:1]), 0).sum(1)


def best_corr(a, b, lag=10):
    """The largest Pearson correlation over lags within +-lag frames (None if undefined)."""
    import numpy as np

    best = None
    for L in range(-lag, lag + 1):
        x, y = (a[L:], b[:len(b) - L]) if L >= 0 else (a[:len(a) + L], b[-L:])
        n = min(len(x), len(y))
        if n < 20 or np.std(x[:n]) == 0 or np.std(y[:n]) == 0:
            continue
        c = float(np.corrcoef(x[:n], y[:n])[0, 1])
        best = c if best is None else max(best, c)
    return best


def chroma(x, sr=AN_SR, nf=4096, hop=1200):
    """(12-bin chroma per frame, normalised; frame energy) over 70-1500 Hz, as the audit's chroma check."""
    import numpy as np

    x = np.asarray(x, np.float32)
    if len(x) < nf:
        return np.zeros((0, 12)), np.zeros(0)
    fr = np.lib.stride_tricks.sliding_window_view(x, nf)[::hop] * np.hanning(nf)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(nf, 1 / sr)
    ok = (f > 70) & (f < 1500)
    pc = (np.round(12 * np.log2(f[ok] / 440)) % 12).astype(int)
    C = np.stack([S[:, ok][:, pc == k].sum(1) for k in range(12)], 1)
    return C / (C.sum(1, keepdims=True) + 1e-12), S[:, ok].sum(1)


def chroma_sim(a, b, min_frames=20):
    """Mean centred cosine of two chroma sequences over frames where both play (energy > max x 1e-3)."""
    import numpy as np

    (A, ea), (B, eb) = a, b
    m = min(len(A), len(B))
    if m == 0:
        return None
    A, B, ea, eb = A[:m], B[:m], ea[:m], eb[:m]
    ok = (ea > ea.max() * 1e-3) & (eb > eb.max() * 1e-3)
    if ok.sum() < min_frames:
        return None
    A = A[ok] - A[ok].mean(1, keepdims=True)
    B = B[ok] - B[ok].mean(1, keepdims=True)
    return float(np.mean((A * B).sum(1) / (np.linalg.norm(A, axis=1) * np.linalg.norm(B, axis=1) + 1e-12)))


def room_ir(rng, sr=AN_SR):
    """A synthetic room path: a direct impulse after 5-20 ms, then an exponential noise tail (RT60 0.3-0.8 s),
    unit energy."""
    import numpy as np

    d = int(rng.uniform(0.005, 0.020) * sr)
    rt = rng.uniform(0.3, 0.8)
    n = int(rt * sr)
    t = np.arange(n) / sr
    tail = rng.standard_normal(n) * np.exp(-6.91 * t / rt) * 0.3
    h = np.zeros(d + n)
    h[d] = 1.0
    h[d:] += tail
    return h / np.sqrt(np.sum(h ** 2))


# --- I/O ----------------------------------------------------------------------------------------------------

def out_root(args):
    return pathlib.Path(args.out).expanduser() if getattr(args, "out", None) else OUT


def _save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def _load(path):
    return json.loads(path.read_text()) if path.exists() else None


def read_jsonl(path):
    out = []
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue                                  # a torn last line from a stopped run
    return out


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ledger_ok():
    return f'"{LEDGER_ID}"' in (PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text()


def require_real(args):
    """Non-smoke runs write only to the default root and need the ledger entry."""
    if getattr(args, "smoke", False):
        if not getattr(args, "out", None):
            raise SystemExit("--smoke writes into a scratch --out only")
        return
    if getattr(args, "limit", 0) or getattr(args, "only", None) or getattr(args, "dev", False):
        raise SystemExit("--limit, --only and --dev are for smoke tests (with --smoke and --out) only")
    if not ledger_ok():
        raise SystemExit(f"the ledger has no {LEDGER_ID} entry")


def load_window(path, t0, t1, sr=AN_SR):
    """Mono audio of [t0, t1) s at `sr` (zeros past the file's ends)."""
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    info = sf.info(str(path))
    a, b = max(0, int(round(t0 * info.samplerate))), max(0, int(round(t1 * info.samplerate)))
    x, sr0 = sf.read(str(path), start=a, stop=min(b, info.frames), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr0 != sr:
        g = math.gcd(sr, sr0)
        x = resample_poly(x, sr // g, sr0 // g).astype(np.float32)
    n = int(round((t1 - t0) * sr))
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def file_seconds(path):
    import soundfile as sf

    info = sf.info(str(path))
    return info.frames / info.samplerate


def build_sections():
    """{section id: {"examples": [...], ...}} of the D build (pool and V_sep), from its mix rows."""
    from learn import direct_stems as DS

    secs = {}
    for part in ("pilot", "rest", "vsep"):
        for r in DS.build_rows(DS.ROOT, part, "mix").values():
            secs.setdefault(r["section"], []).append({"i": r["i"], "part": part, "band": r["band"],
                                                      "early_stop": bool(r.get("early_stop")),
                                                      "split": r["split"], "tag": r.get("tag"),
                                                      "vocals": r.get("vocals"), "refused": bool(r.get("refused"))})
    return secs


class Meta:
    """The pool's sections, the inventory and part C's leak drops: what a backing is made of."""

    def __init__(self):
        from learn import pretrain_set as PS

        self.sections = {s["id"]: s for s in PS.pool()["sections"]}
        self.inv = {r["id"]: r for r in json.loads(PS.INVENTORY.read_text())["dis"]}
        self.leak = PS._load(PS.OUT / "leakage.json")

    def backing(self, sid):
        """(session dir, kept tracks with vocals, without vocals) by part C's rule."""
        from learn import pretrain_set as PS

        sec = self.sections[sid]
        rec = self.inv[sec["di"]]
        sess = pathlib.Path(rec["session_dir"])
        files = sorted(f.name for f in sess.glob("*.wav"))
        withv, nov = PS.backing_tracks(rec, files, self.leak[sec["di"]]["dropped"])
        return sess, withv, nov


def own_source(rec, sess, part, dur):
    """The own close-mic track to read takes against: own tracks named with the part token, the loudest over
    the session (any own track if none is so named). -> (name, whole-session audio) or (None, None)."""
    import numpy as np

    own = list(rec.get("own") or [])
    if not own:
        return None, None
    named = [o for o in own if part and part.lower() in o.lower()] or own
    best, best_e, best_y = None, -1.0, None
    for o in named:
        y = load_window(sess / o, 0.0, dur)
        e = float(np.mean(y.astype(np.float64) ** 2))
        if e > best_e:
            best, best_e, best_y = o, e, y
    return best, best_y


def half_masks(n_frames, s0, spans=HALF_SPANS):
    """Whole-session STFT frame masks of a section's judge halves."""
    tc = frame_times(n_frames)
    return {h: (tc >= s0 + a) & (tc < s0 + b) for h, (a, b) in spans.items()}


def half_power_db(Y, S_ref, masks):
    """{half: dB of a track's energy against the reference's} in one section."""
    import numpy as np

    out = {}
    for h, m in masks.items():
        e, r = float(np.sum(np.abs(Y[:, m]) ** 2)), float(np.sum(np.abs(S_ref[:, m]) ** 2))
        out[h] = 10 * math.log10(e / r) if e > 0 and r > 0 else None
    return out


def scan_di(meta, di, sids, log=print):
    """Step 0b for one DI: session-level take readings of every kept track (the with-vocals list, a superset
    of the other), then per section the halves' power, onsets, chroma, the same-part test and the removal.
    -> [section row]."""
    import gc

    import numpy as np

    from learn import pretrain_set as PS

    rec = meta.inv[di]
    sess = pathlib.Path(rec["session_dir"])
    files = sorted(f.name for f in sess.glob("*.wav"))
    withv, nov = PS.backing_tracks(rec, files, meta.leak[di]["dropped"])
    dur = file_seconds(rec["path"])
    part = rec.get("part") or part_base(di)
    di_a = load_window(rec["path"], 0.0, dur)
    src_name, amp = own_source(rec, sess, part, dur)
    has_amp = amp is not None
    idx, _ = band_bins()
    S_di = stft(di_a)[idx]
    S_ref = stft(amp)[idx] if has_amp else S_di
    src_a = amp if has_amp else di_a
    secs = {sid: float(meta.sections[sid]["start_s"]) for sid in sids}
    cut = {sid: (int(round(s0 * AN_SR)), int(round((s0 + SEC_S) * AN_SR))) for sid, s0 in secs.items()}
    masks = {sid: half_masks(S_ref.shape[1], s0) for sid, s0 in secs.items()}
    di_on = {sid: onset_env(di_a[a:b]) for sid, (a, b) in cut.items()}
    src_ch = {sid: chroma(src_a[a:b]) for sid, (a, b) in cut.items()}
    own_on = {sid: (best_corr(di_on[sid], onset_env(amp[a:b])) if has_amp else None) for sid, (a, b) in cut.items()}
    del di_a
    per_sec = {sid: {} for sid in sids}
    Ys = {}
    for t in withv:
        y = load_window(sess / t, 0.0, dur)
        Y = stft(y)[idx]
        for sid, (a, b) in cut.items():
            on = best_corr(di_on[sid], onset_env(y[a:b]))
            ch = chroma_sim(src_ch[sid], chroma(y[a:b]))
            partner = name_partner(part, t)
            per_sec[sid][t] = {"class": track_class(t), "power_db": half_power_db(Y, S_ref, masks[sid]),
                               "onset": on, "chroma": ch, "partner": partner,
                               "same_part": same_part(ch, on, own_on[sid], partner)}
        Ys[t] = Y
        del y
    gc.collect()
    reader = TakeReader(S_ref, S_ref)
    take_amp = reader.takes(Ys) if has_amp else {}
    take_di = TakeReader(S_di, S_ref).takes(Ys) if has_amp else {}
    session_power = {t: reader.power(Y) for t, Y in Ys.items()}
    del Ys
    gc.collect()
    rows = []
    for sid in sids:
        tracks = per_sec[sid]
        for t, r in tracks.items():
            r.update(take_amp_db=take_amp.get(t), take_di_db=take_di.get(t), session_power_db=session_power[t])
        row = {"section": sid, "di": di, "band": meta.sections[sid]["band"], "part": part,
               "source": {"kind": "amp" if has_amp else "di", "track": src_name}, "onset_own": own_on[sid],
               "variants": {"v": list(withv), "n": list(nov)}, "tracks": tracks}
        removed, before, after = section_decision(row)
        row.update(removed=removed, take_before_db=before, take_after_db=after)
        rows.append(row)
    log(f"  {di[-60:]}: {len(withv)} tracks, source {src_name or 'DI'}; session takes >= {FLOOR_DB:.0f} dB: "
        + str({t[:24]: round(v, 1) for t, v in take_amp.items() if v is not None and v >= FLOOR_DB}))
    return rows


def clean_injection_sessions(meta, secs, max_excess=CLEAN_EXCESS):
    """{session name: sorted DIs}: Cambridge training DIs with an own amp track whose kept tracks all read
    coherence excess <= max_excess in part C's leakage check, by session."""
    out = {}
    for sid, exs in secs.items():
        if all(e["split"] != "train" for e in exs):
            continue
        di = meta.sections[sid]["di"]
        rec = meta.inv[di]
        if rec.get("source") != "cambridge" or not rec.get("own"):
            continue
        lk = meta.leak.get(di) or {}
        kept = {t: e for t, e in (lk.get("excess") or {}).items() if t not in (lk.get("dropped") or [])}
        if kept and max(kept.values()) <= max_excess:
            out.setdefault(pathlib.Path(rec["session_dir"]).name, set()).add(di)
    return {k: sorted(v) for k, v in sorted(out.items())}


def injection_sources(sessions, seed=INJECT_SEED):
    """One DI per session (its own amp track is the injected source), drawn by the seed. -> {session: DI}."""
    return {k: random.Random(f"{seed}|{k}").choice(v) for k, v in sorted(sessions.items())}


def inject_session(meta, di, seed=INJECT_SEED, levels=INJECT_DB):
    """The injection check on one clean session: a room-filtered copy of the own amp track added, one at a time,
    to every kept drum, room and overhead track at each level (dB of the own amp over its counted frames), read back
    with the session estimator; every target read uninjected too, and every other non-guitar track (false
    positives)."""
    import numpy as np
    from scipy.signal import fftconvolve

    from learn import pretrain_set as PS

    rec = meta.inv[di]
    sess = pathlib.Path(rec["session_dir"])
    files = sorted(f.name for f in sess.glob("*.wav"))
    withv, _ = PS.backing_tracks(rec, files, meta.leak[di]["dropped"])
    dur = file_seconds(rec["path"])
    part = rec.get("part") or part_base(di)
    src_name, amp = own_source(rec, sess, part, dur)
    idx, _ = band_bins()
    S_ref = stft(amp)[idx]
    reader = TakeReader(S_ref, S_ref)
    targets = [t for t in withv if track_class(t) == "drums"]
    Ys = {}
    for t in withv:
        y = load_window(sess / t, 0.0, dur)
        Ys[t] = stft(y)[idx]
        if t in targets and float(np.mean(y.astype(np.float64) ** 2)) > 0:
            rng = np.random.default_rng(int(hashlib.sha256(f"{seed}|{di}|{t}".encode()).hexdigest()[:8], 16))
            c = fftconvolve(amp, room_ir(rng))[:len(amp)].astype(np.float32)
            C = stft(c)[idx]
            unit = float(np.sum(np.abs(C[:, reader.counted]) ** 2)) / reader.ref
            for L in levels:
                Ys[f"{t} @ {L:+.0f}"] = stft(y + math.sqrt(10 ** (L / 10) / unit) * c)[idx]
        del y
    targets = [t for t in targets if f"{t} @ {levels[0]:+.0f}" in Ys]
    takes = reader.takes(Ys)
    return {"session": sess.name, "di": di, "source": src_name,
            "targets": {t: {"room": is_room(t), "base": takes[t],
                            "inj": {L: takes[f"{t} @ {L:+.0f}"] for L in levels}} for t in targets},
            "others": {t: takes[t] for t in withv if track_class(t) not in ("guitar", "drums")}}


# --- commands: step 0 -------------------------------------------------------------------------------------

def cmd_inject(args):
    require_real(args)
    root = out_root(args)
    path = root / "injection.json"
    if path.exists() and not args.smoke:                # fail closed: a record (a FAIL above all) is never overwritten
        raise SystemExit(f"{path} exists (verdict {(_load(path) or {}).get('verdict')}): a rerun needs review; "
                         "move the record aside by hand first")
    meta, secs = Meta(), build_sections()
    sessions = clean_injection_sessions(meta, secs)
    sources = injection_sources(sessions)
    dev_sessions = {pathlib.Path(meta.inv[d]["session_dir"]).name for d in DEV_DIS}
    if set(INJECT_DECIDING) & dev_sessions or not set(INJECT_DECIDING) <= set(sources):
        raise SystemExit(f"the deciding sessions {INJECT_DECIDING} are not clean, new sessions: {sorted(sources)}")
    order = [k for k in INJECT_DECIDING] + sorted(k for k in sources if k not in INJECT_DECIDING)
    if args.dev:
        order = sorted(dev_sessions)
    order = order[:args.limit or None]
    print(f"injection check: {len(order)} sessions ({len(INJECT_DECIDING)} deciding); seed {INJECT_SEED}", flush=True)
    rows = []
    for k, name in enumerate(order):
        t = time.time()
        r = inject_session(meta, sources[name])
        r["deciding"] = name in INJECT_DECIDING
        rows.append(r)
        ok, shares, base = session_verdict(r)
        fp = [f"{o[:20]} {v:.1f}" for o, v in r["others"].items() if v is not None and v >= TAKE_DB]
        print(f"  {k + 1}/{len(order)} {name} ({'deciding' if r['deciding'] else 'beside'}; source "
              f"{r['source']}): {len(r['targets'])} targets, "
              f"{sum(x['room'] for x in r['targets'].values())} room/overhead; vote {'PASS' if ok else 'FAIL'}; "
              + "; ".join(f"{L:+.0f}: {a:.2f}" + ("" if rs is None else f" (rooms {rs:.2f})")
                          for L, (a, rs) in shares.items())
              + f"; uninjected under {INJECT_BASE_DB:.0f} dB {base:.2f}; others >= {TAKE_DB:.0f} dB {fp} "
              f"({time.time() - t:.0f} s)", flush=True)
        for tname, x in r["targets"].items():
            print(f"      {tname[:28]:28s} {'room' if x['room'] else '    '} base {x['base']}, "
                  + ", ".join(f"{L:+.0f}: {v if v is None else round(v, 1)}" for L, v in x["inj"].items()), flush=True)
    verdict, votes, fp = injection_verdict(rows)
    rec = {"plan": PLAN, "step": "0a (amendment 1)", "smoke": bool(args.smoke), "dev": bool(args.dev),
           "verdict": verdict, "votes": votes, "false_positive_share": fp, "rule": injection_rule(),
           "rows": [{**r, "targets": {t: {**x, "inj": {str(L): v for L, v in x["inj"].items()}}
                                      for t, x in r["targets"].items()}} for r in rows],
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(path, rec)
    print(f"INJECTION {verdict}: votes {votes}; false positives (other non-guitar tracks of the deciding sessions at "
          f"or above {TAKE_DB:.0f} dB) {fp:.3f}", flush=True)


def scan_rows_path(root, k, n):
    return root / "scan" / f"rows-{k}of{n}.jsonl"


def scan_rows(root):
    out = {}
    for f in sorted((root / "scan").glob("rows-*.jsonl")):
        for r in read_jsonl(f):
            out[r["section"]] = r
    return out


def cmd_scan(args):
    from learn import direct_stems as DS

    require_real(args)
    root = out_root(args)
    meta, secs = Meta(), build_sections()
    expected = {k: v for k, v in injection_sources(clean_injection_sessions(meta, secs)).items() if k in INJECT_DECIDING}
    why = injection_record_problem(_load(root / "injection.json"), expected)
    if why:
        if not args.smoke:
            raise SystemExit(f"scan needs a real INJECTION OK under amendment 1: {why}")
        print(f"smoke: scanning anyway ({why})", flush=True)
    if len(secs) != EXPECT_SECTIONS and not args.smoke:
        raise SystemExit(f"the D build has {len(secs)} sections, not {EXPECT_SECTIONS}")
    by_di = {}
    for sid in sorted(secs):
        if not args.only or args.only in sid:
            by_di.setdefault(meta.sections[sid]["di"], []).append(sid)
    k, n = args.shard
    dis = [d for j, d in enumerate(sorted(by_di)) if j % n == k][:args.limit or None]
    done = set(scan_rows(root))
    todo = [d for d in dis if any(s not in done for s in by_di[d])]
    print(f"scan shard {k}/{n}: {len(todo)} DIs to do ({len(dis)} in the shard, "
          f"{sum(len(by_di[d]) for d in todo)} sections)", flush=True)
    rp = scan_rows_path(root, k, n)
    rp.parent.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    swap0 = DS.swap_mb()
    with open(rp, "a") as fh:
        for m, di in enumerate(todo):
            g = DS._guards("scan", DISK_GUARD_GB, swap0)          # disk, then memory and swap
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            t = time.time()
            rows = scan_di(meta, di, [s for s in by_di[di] if s not in done], log=lambda x: print(x, flush=True))
            for row in rows:
                row["seconds"] = round((time.time() - t) / len(rows), 1)
                fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(f"  {m + 1}/{len(todo)} DIs: {len(rows)} sections, removed "
                  f"{sorted({x for r in rows for x in r['removed']})}; {time.time() - t:.0f} s "
                  f"({(time.time() - t_start) / (m + 1):.0f} s per DI)", flush=True)
    print(f"SCAN DONE {k}/{n}", flush=True)


def example_lists(rows, secs, thr=TAKE_DB):
    """Per example: untrusted or not, under a threshold. -> {i: bool} over every unrefused build example."""
    out = {}
    for sid, exs in secs.items():
        row = rows.get(sid)
        if row is None:
            continue
        removed = section_decision(row, thr)[0]
        for e in exs:
            if e["refused"]:
                continue
            out[e["i"]] = touched(removed, row["variants"]["v" if e["vocals"] else "n"])
    return out


def summarise(untrusted, secs):
    """Counts: the pool (train, early stopping), V_sep and R_in (untagged) per band."""
    info = {e["i"]: e for exs in secs.values() for e in exs}
    c = {"pool": [0, 0], "train": [0, 0], "early_stop": [0, 0], "vsep": [0, 0], "r_in": {}}
    for i, bad in untrusted.items():
        e = info[i]
        if e["part"] == "vsep":
            c["vsep"][0] += bad
            c["vsep"][1] += 1
            if not e["tag"]:
                b = c["r_in"].setdefault(e["band"], [0, 0])
                b[0] += bad
                b[1] += 1
        else:
            c["pool"][0] += bad
            c["pool"][1] += 1
            k = "early_stop" if e["early_stop"] else "train"
            c[k][0] += bad
            c[k][1] += 1
    return c


def cmd_lists(args):
    require_real(args)
    root = out_root(args)
    rows, secs = scan_rows(root), build_sections()
    missing = sorted(set(secs) - set(rows))
    if missing and not args.smoke:
        raise SystemExit(f"{len(missing)} sections are not scanned")
    secs = {s: v for s, v in secs.items() if s in rows}
    untrusted = example_lists(rows, secs)
    c = summarise(untrusted, secs)
    share = c["pool"][0] / max(1, c["pool"][1])
    sens = {str(t): summarise(example_lists(rows, secs, t), secs) for t in SENS_DB}
    removed_by_class = {}
    sec_out = {}
    for sid, row in sorted(rows.items()):
        removed, before, after = section_decision(row)
        for t in removed:
            k = row["tracks"][t]["class"]
            removed_by_class[k] = removed_by_class.get(k, 0) + 1
        sec_out[sid] = {"band": row["band"], "source": row["source"], "removed": removed,
                        "same_part": sorted(t for t, r in row["tracks"].items() if r.get("same_part")),
                        "take_before_db": before, "take_after_db": after}
    files = sorted((root / "scan").glob("rows-*.jsonl"))
    rec = {"plan": PLAN, "step": "0c", "smoke": bool(args.smoke), "rule": {"take_db": TAKE_DB, "floor_db": FLOOR_DB,
           "chroma_min": CHROMA_MIN, "onset_min": ONSET_MIN, "drop_max_share": DROP_MAX_SHARE},
           "scan_sha256": {f.name: sha256_file(f) for f in files}, "counts": c, "pool_share": share,
           "route": route(share), "sensitivity": sens, "removed_by_class": removed_by_class,
           "sections": sec_out, "untrusted": sorted(i for i, b in untrusted.items() if b),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "trusted.json", rec)
    print(f"sections scanned {len(rows)}; with a track removed {sum(1 for v in sec_out.values() if v['removed'])}")
    print(f"untrusted: pool {c['pool'][0]:,}/{c['pool'][1]:,} ({share:.1%}); train {c['train']}; "
          f"early stopping {c['early_stop']}; V_sep {c['vsep']}")
    print(f"R_in per band (untrusted/all): {c['r_in']}")
    print(f"removed tracks by class: {removed_by_class}")
    for t, s in sens.items():
        print(f"  descriptive, at {t} dB: pool {s['pool'][0]:,}/{s['pool'][1]:,}; R_in {s['r_in']}")
    print(f"ROUTE {route(share).upper()} (drop if <= {DROP_MAX_SHARE:.0%} of the pool is untrusted)")


# --- step 1: the paired R_in rebuild -------------------------------------------------------------------------

def rin_root(root):
    return root / "rin"


def rebuilt_gain_db(gb, lb_old, lb_new, lg):
    """The backing gain that keeps the drawn guitar-to-backing ratio after tracks leave the backing
    (`pretrain_set.mix_gains_db`: gb = lg - ratio - max(lb, lg - 40)). The overall gain is unchanged: the
    mix's power sum depends only on lg and the ratio."""
    return gb + max(lb_old, lg - 40.0) - max(lb_new, lg - 40.0)


def assemble(y, b, gb, ga):
    """The true mix before mastering: (guitar + backing x gb) x ga (dB gains)."""
    return (y + b * 10 ** (gb / 20)) * 10 ** (ga / 20)


def parity(mels, lufs, stored, mshare=0.99, ltol=0.01):
    """The re-made original mix against the stored mix features: (ok, cells share, max LUFS diff)."""
    from learn import direct_stems as DS

    share = min(DS.match_share(mels[h], stored[f"m{h}"]) for h in "AB")
    dl = max(abs(lufs[h] - float(stored["lufs"][k])) for k, h in enumerate("AB"))
    return share >= mshare and dl <= ltol, share, dl


def rin_ids(secs):
    """R_in: V_sep's unrefused examples outside Bannockburn and every MUSDB18-tagged section."""
    return {e["i"] for exs in secs.values() for e in exs if e["part"] == "vsep" and not e["tag"] and not e["refused"]}


def rin_state(plan, pending, built):
    """R_in under a candidate list. plan/pending: {i: tracks}; built: {(i, key): row}, key "orig" for the re-made
    original's re-separation (the null). -> (to build: {i: [keys]}, current: {i: (row, orig row)}, excluded:
    {i: reason}). An example is current only with both its rebuild (under the wanted key) and its re-separated
    original; a refusal of either, or a pending candidate, excludes it."""
    to_build, current, excluded = {}, {}, {}
    for i, t in pending.items():
        excluded[i] = "pending review: " + ", ".join(sorted(t))
    for i, t in plan.items():
        k = removal_key(t)
        rows = {kk: built.get((i, kk)) for kk in (k, "orig")}
        bad = [r["refused"] for r in rows.values() if r and r.get("refused")]
        if bad:
            excluded.setdefault(i, f"refused: {bad[0]}")
            continue
        need = [kk for kk, r in rows.items() if r is None]
        if need:
            to_build[i] = need
        elif i not in excluded:
            current[i] = (rows[k], rows["orig"])
    return to_build, current, excluded


def rin_rows(proot):
    return keyed_rows(proot / "rows", "rin")


def _truth_mix(ctx, G, gd, truth, r, PS, DS, SA):
    """The example's guitar (the stored truth render) and its original mix re-made with the stored draw, checked
    against the stored mix. -> (y, b, meta, kind, gains, mastered, orig mix, parity record) or a refusal string."""
    import numpy as np

    i, sid = r["i"], r["section"]
    tr = truth.get(i)
    if tr is None or tr.get("refused"):
        return "no stored truth render"
    y = G.read_flac(G.truth_path(gd, i), tr["scale"], tr["sha256"])
    meta = json.loads(PS.backing_path(sid).with_suffix(".json").read_text())
    ratio, v, leak, target = PS.mix_params(i, ctx.ratios, meta["has_vocals"], ctx.eval_mix, 0)
    kind = "v" if v else "n"
    b, meta = ctx.backing(sid, kind)
    gb, gl, ga = PS.mix_gains_db(r["lufs"], meta[f"lufs_{kind}"], ratio, leak, target)
    if max(abs(p - q) for p, q in zip((gb, gl, ga), r["mix"]["gains_db"])) > 1e-6:
        raise SystemExit(f"{i}: the V_sep mix draw differs from part C's val mix")
    mastered, mrng = DS.master_draw(i)
    orig = assemble(y, b, gb, ga)
    orig = SA.compress(orig, mrng) if mastered else orig
    mels, lu, _ = DS.half_features(orig)
    ok, share, dl = parity(mels, lu, np.load(DS.ex_path(DS.ROOT, i, "mix")))
    if not ok:
        return "the original re-mix differs from the stored mix"
    return {"y": y, "b": b, "meta": meta, "kind": kind, "gb": gb, "ga": ga, "mastered": mastered, "orig": orig,
            "orig_share": share, "orig_lufs_diff": dl}


def cmd_rin_rebuild(args):
    import gc

    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_aug as SA

    require_real(args)
    root = out_root(args)
    rec, cpath = load_candidates(root, args.candidates, args.smoke)
    free = PS.free_gb()
    if free < DISK_GUARD_GB:
        raise SystemExit(f"free disk {free:.1f} GB, below the {DISK_GUARD_GB:.0f} GB guard")
    plan, pending = candidate_plans(root, rec, ("vsep",))
    ids = rin_ids(build_sections())
    plan = {i: t for i, t in plan.items() if i in ids}
    pending = {i: t for i, t in pending.items() if i in ids}
    rr = rin_root(root)
    to_build, current, excluded = rin_state(plan, pending, rin_rows(rr))
    print(f"rin-rebuild ({cpath.name}): {len(plan)} R_in examples wanted rebuilt, {len(to_build)} to build, "
          f"{len(current)} current, {len(excluded)} excluded; X-LANCE on {args.device}", flush=True)
    if not to_build:
        print("RIN-REBUILD DONE", flush=True)
        return
    ctx = DS.Ctx(quiet=True)
    by_i = {r["i"]: r for r in ctx.parts["vsep"]}
    todo = sorted((by_i[i] for i in to_build), key=lambda r: (r["section"], r["i"]))[:args.limit or None]
    ctx.rows = None                                       # part C's rows (about 1.4 GB): not needed past here
    gc.collect()
    gd = DS.ROOT / "gate"
    truth = G.gate_rows(gd, "truth")
    sep = DS.stem_separator(STEP_SEP, args.device)
    swap0 = DS.swap_mb()
    worker = f"{args.device}-{os.getpid()}"
    rp = rr / "rows" / f"rin-{worker}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    csha = sha256_file(cpath)
    refused, n_sep = 0, 0
    t_start = time.time()

    def separate(mix):
        s_ = np.asarray(sep(mix), np.float64)
        if len(s_) != len(mix) or not np.isfinite(s_).all():
            raise SystemExit("bad stem")
        return s_

    with open(rp, "a") as fh:
        for m, r in enumerate(todo):
            g = DS._guards("rin", DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            i, sid = r["i"], r["section"]
            gone, need = plan[i], to_build[i]
            key = removal_key(gone)
            base = {"i": i, "section": sid, "band": r["band"], "candidates_sha256": csha}
            made = _truth_mix(ctx, G, gd, truth, r, PS, DS, SA)
            if isinstance(made, str):
                refused += 1
                for kk in need:
                    fh.write(json.dumps({**base, "key": kk, "refused": made}) + "\n")
                fh.flush()
                continue
            par = {"orig_share": made["orig_share"], "orig_lufs_diff": made["orig_lufs_diff"]}
            if "orig" in need:                            # the null: the re-made original, separated by this path
                t0 = time.time()
                sm, sl, floor = DS.half_features(separate(made["orig"]))
                DS._save_npz(DS.ex_path(rr, i, f"{STEP_SEP}-orig"), sA=sm["A"], sB=sm["B"], lufs=[sl["A"], sl["B"]])
                fh.write(json.dumps({**base, **par, "key": "orig", "removed": [], "lufs_sA": sl["A"], "lufs_sB": sl["B"],
                                     "floor_share": floor, "sep": STEP_SEP, "device": args.device,
                                     "sep_seconds": round(time.time() - t0, 2)}) + "\n")
                n_sep += 1
            if key in need:
                meta, kind = made["meta"], made["kind"]
                if not set(gone) <= set(meta["tracks"][kind]):
                    raise SystemExit(f"{i}: {gone} not all in its backing")
                sec = ctx.sections[sid]
                sess = pathlib.Path(ctx.inv[sec["di"]]["session_dir"])
                nb = np.asarray(made["b"], np.float64).copy()
                for t in gone:
                    nb -= PS.section_audio(sess / t, sec["start_s"])[int(PS.TRIM_S * PS.SR):]
                lb_new = SA.lufs(nb)
                gb_new = rebuilt_gain_db(made["gb"], meta[f"lufs_{kind}"], lb_new, r["lufs"])
                _, mrng2 = DS.master_draw(i)
                mix = assemble(made["y"], nb, gb_new, made["ga"])
                mix = SA.compress(mix, mrng2) if made["mastered"] else mix
                t0 = time.time()
                mm, ml, _ = DS.half_features(mix)
                sm, sl, floor = DS.half_features(separate(mix))
                DS._save_npz(DS.ex_path(rr, i, f"mix-{key}"), mA=mm["A"], mB=mm["B"], lufs=[ml["A"], ml["B"]],
                             gain_db=made["ga"], mastered=made["mastered"])
                DS._save_npz(DS.ex_path(rr, i, f"{STEP_SEP}-{key}"), sA=sm["A"], sB=sm["B"], lufs=[sl["A"], sl["B"]])
                fh.write(json.dumps({**base, **par, "key": key, "removed": gone, "kind": kind,
                                     "lufs_backing_old": meta[f"lufs_{kind}"], "lufs_backing_new": lb_new,
                                     "gain_backing_db": [made["gb"], gb_new], "mastered": made["mastered"],
                                     "lufs_mA": ml["A"], "lufs_mB": ml["B"], "lufs_sA": sl["A"], "lufs_sB": sl["B"],
                                     "floor_share": floor, "sep": STEP_SEP, "device": args.device,
                                     "sep_seconds": round(time.time() - t0, 2)}) + "\n")
                n_sep += 1
            fh.flush()
            if m % 25 == 0:
                print(f"rin {m + 1}/{len(todo)} i={i}: {n_sep} separations, refused {refused}; "
                      f"{(time.time() - t_start) / (m + 1):.1f} s per example", flush=True)
    print(f"RIN-REBUILD DONE ({len(todo)} examples this run, {n_sep} separations, refused {refused})", flush=True)


def stem_tensors(rows, mix_of, stem_of, arm):
    """`direct_stems.readout_tensors` with explicit feature files: (X, C, Y, who) over both halves."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import song_model as SM

    X, C, Y, who = [], [], [], []
    for r in rows:
        dm, ds = np.load(mix_of(r["i"])), np.load(stem_of(r["i"]))
        for k, h in enumerate("AB"):
            x, c = DS.model_input(ds[f"s{h}"], dm[f"m{h}"], float(ds["lufs"][k]), float(dm["lufs"][k]), h,
                                  r["amp"], r["base"], arm)
            X.append(x), C.append(c), Y.append(SM.encode(r["label"])), who.append(r["i"])
    if not X:
        return None
    return np.stack(X).astype(np.float32), np.stack(C), [np.stack(z) for z in zip(*Y)], who


def section_interval(per_a, per_b, section_of, keep):
    """Paired a - b, clustered by section (descriptive beside the band-clustered reading)."""
    from learn import pretrain_set as PS

    by = {}
    for i in sorted(set(per_a) & set(per_b) & set(keep)):
        by.setdefault(section_of[i], []).append(per_a[i] - per_b[i])
    return PS.band_t_interval(by) if len(by) >= 2 else None


def cmd_rin_read(args):
    import numpy as np

    from learn import direct_stems as DS

    require_real(args)
    root = out_root(args)
    rec, cpath = load_candidates(root, args.candidates, args.smoke)
    plan, pending = candidate_plans(root, rec, ("vsep",))
    ids = rin_ids(build_sections())
    plan = {i: t for i, t in plan.items() if i in ids}
    pending = {i: t for i, t in pending.items() if i in ids}
    rr = rin_root(root)
    to_build, current, excluded = rin_state(plan, pending, rin_rows(rr))
    if to_build and not args.smoke:                       # fail closed: stale or missing rows are never read
        raise SystemExit(f"{len(to_build)} R_in examples are not rebuilt under {cpath.name} (run rin-rebuild)")
    ro = DS._load(DS.ROOT / "full" / "readout.json")
    if not ro or ro.get("smoke"):
        raise SystemExit("rin-read needs step 3's real full/readout.json")
    report = DS._load(DS.ROOT / "pilot" / "pilot-report.json")
    D = DS.d_arm(report)
    nets, recs = DS.load_full_runs(DS.ROOT, D, stem_sep=STEP_SEP)
    if {str(r["seed"]): r["model_sha256"] for r in recs} != ro["models"]["D"]:
        raise SystemExit("step 3's D_stem runs differ from those readout.json read")
    med = DS.medians_from_json(ro["constant"])
    table = DS.table_from_json(ro["pull"]["D"])
    ctx = DS.Ctx(quiet=True)
    r_in = [r for r in ctx.parts["vsep"] if r["i"] in ids]
    band_of = {r["i"]: r["band"] for r in r_in}
    section_of = {r["i"]: r["section"] for r in r_in}
    cell_of = {r["i"]: (r["amp"], r["base"]) for r in r_in}
    const = DS.const_errors(r_in, med, DS.encode_audible)
    reb_rows = [r for r in r_in if r["i"] in current]
    key_of = {i: row["key"] for i, (row, _) in current.items()}
    stored_mix = lambda i: DS.ex_path(DS.ROOT, i, "mix")               # noqa: E731
    sets = {"stored original": (r_in, stored_mix, lambda i: DS.ex_path(DS.ROOT, i, STEP_SEP)),
            "re-separated original": (reb_rows, stored_mix, lambda i: DS.ex_path(rr, i, f"{STEP_SEP}-orig")),
            "rebuilt": (reb_rows, lambda i: DS.ex_path(rr, i, f"mix-{key_of[i]}"),
                        lambda i: DS.ex_path(rr, i, f"{STEP_SEP}-{key_of[i]}"))}
    res = {}
    for tag, k in (("3 seeds", len(nets)), ("2 seeds (20261042, 20261043)", 2)):
        per = {}
        for name, (rows, mix_of, stem_of) in sets.items():
            if not rows:
                per[name] = {}
                continue
            outs, who, Y = DS.run_rows(nets[:k], rows, lambda x, a=mix_of, b=stem_of: stem_tensors(x, a, b, D))
            per[name] = DS.readout_per(DS.score_all(outs, who, DS.silent_masks(Y), cell_of, med, table)[0])["A1+A2+A3"]
        orig, reorig, reb = per["stored original"], per["re-separated original"], per["rebuilt"]
        untouched = {i for i in orig if i not in plan and i not in excluded}
        trusted_set = {**{i: e for i, e in orig.items() if i in untouched}, **reb}
        res[tag] = {
            "rebuilt - re-separated original (paired, same path; primary)": DS.paired(reb, reorig, band_of, set(reb)),
            "rebuilt - re-separated original, section-clustered": section_interval(reb, reorig, section_of, set(reb)),
            "re-separated original - stored original (the null: the path only)": DS.paired(reorig, orig, band_of,
                                                                                         set(reorig)),
            "rebuilt - stored original (beside)": DS.paired(reb, orig, band_of, set(reb)),
            "F - constant, untouched trusted R_in (co-primary in step 2)": DS.paired(orig, const, band_of, untouched),
            "F - constant, trusted R_in (untouched + rebuilt)": DS.paired(trusted_set, const, band_of, set(trusted_set)),
            "F - constant, rebuilt examples (rebuilt stems)": DS.paired(reb, const, band_of, set(reb)),
            "F - constant, rebuilt examples (stored stems)": DS.paired(orig, const, band_of, set(reb)),
            "F - constant, R_in as stored (step 3)": DS.paired(orig, const, band_of, set(orig)),
            "per band, rebuilt - re-separated original": {
                b: float(np.mean([reb[i] - reorig[i] for i in reb if band_of[i] == b]))
                for b in sorted({band_of[i] for i in reb})},
            "examples": {"r_in": len(orig), "untouched": len(untouched), "rebuilt": len(reb),
                         "excluded": len(excluded), "not built (smoke only)": len(to_build)}}
    out = {"plan": PLAN, "step": "1b", "smoke": bool(args.smoke), "decides": "nothing (descriptive)",
           "candidates": str(cpath), "candidates_sha256": sha256_file(cpath),
           "readout": "amendment 5: A1+A2+A3, masked E; step 3's stored constant and D pull",
           "models": ro["models"]["D"], "excluded": {str(i): w for i, w in sorted(excluded.items())},
           "results": res, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "rin-read.json", out)

    def f(v):
        return "n/a" if v is None else f"{v[0]:+.4f} [{v[1]:+.4f}, {v[2]:+.4f}] ({v[3]} clusters)"

    for tag, rs in res.items():
        print(f"[{tag}] {rs['examples']}")
        for k2, v in rs.items():
            if k2 not in ("examples", "per band, rebuilt - re-separated original"):
                print(f"  {k2:66s} {f(v)}")
        print(f"  per band: { {b: round(v, 4) for b, v in rs['per band, rebuilt - re-separated original'].items()} }")


# --- step 2's data: the candidate-driven pool rebuild ----------------------------------------------------------
#
# The pool's untrusted examples are rebuilt (never dropped) by removing candidate tracks from their section's
# backing. A candidate list drives it, so that a listening verdict can turn a candidate on or off and the next
# run rebuilds (or stops using) exactly the difference. Each rebuilt example's files carry the removal key (the
# removed tracks), so no rebuild overwrites another, and the D build's original files are never touched.
# `pool-status` writes the manifest arm T would read; nothing here trains.

QUEUE = 2                                  # the rebuild's bounded render -> separation queue


def removal_key(tracks):
    """A short, order-free key of a removal set (file names and rows carry it)."""
    return hashlib.sha1("|".join(sorted(tracks)).encode()).hexdigest()[:10]


def pool_root(root):
    return root / "pool"


def candidates_path(root):
    return root / "candidates.json"


def candidates_from(rows, secs):
    """Step 0's scan rows -> candidates, one per (DI, track, kind): pitch-confirmed same-part tracks the rule
    removes ("double") and the other removed tracks ("take": live-room takes). Rebuild is on by default only for
    guitar-class doubles (a riff-following bass or keys track can pass the pitch test); every other candidate is
    off and pending until a verdict, and its examples are excluded meanwhile (`pending_removals`). Each lists its
    sections, the evidence and the examples it touches."""
    out = {}
    for sid in sorted(rows):
        row = rows[sid]
        removed = section_decision(row)[0]
        for t in removed:
            rec = row["tracks"][t]
            kind = "double" if rec.get("same_part") else "take"
            c = out.setdefault((row["di"], t, kind), {
                "id": f"{row['di']}|{t}|{kind}", "di": row["di"], "track": t, "kind": kind, "class": rec.get("class"),
                "band": row["band"], "sections": [], "evidence": [], "pool_examples": 0, "r_in_examples": 0,
                "rebuild": kind == "double" and rec.get("class") == "guitar", "verdict": None, "note": ""})
            c["sections"].append(sid)
            c["evidence"].append({"section": sid, "same_part": bool(rec.get("same_part")), "chroma": rec.get("chroma"),
                                  "onset": rec.get("onset"), "onset_own": row.get("onset_own"),
                                  "partner": rec.get("partner"), "power_db": rec.get("power_db"),
                                  "take_amp_db": rec.get("take_amp_db"), "take_di_db": rec.get("take_di_db")})
            for e in secs.get(sid, []):
                if e["refused"] or t not in row["variants"]["v" if e["vocals"] else "n"]:
                    continue
                if e["part"] == "vsep":
                    c["r_in_examples"] += not e["tag"]
                else:
                    c["pool_examples"] += 1
    return sorted(out.values(), key=lambda c: (c["kind"] != "double", c["band"], c["di"], c["track"]))


def desired_removals(candidates):
    """{section: set of tracks} of the candidates switched on (`rebuild` true)."""
    out = {}
    for c in candidates:
        if c.get("rebuild"):
            for sid in c["sections"]:
                out.setdefault(sid, set()).add(c["track"])
    return out


def pending_removals(candidates):
    """{section: set of tracks} of the candidates still pending: switched off with no verdict. Their examples are
    excluded (fail closed), not read as original, until a verdict keeps the track in or switches it on."""
    out = {}
    for c in candidates:
        if not c.get("rebuild") and c.get("verdict") is None:
            for sid in c["sections"]:
                out.setdefault(sid, set()).add(c["track"])
    return out


def example_plan(desired, secs, variants, parts=("pilot", "rest")):
    """{i: sorted removed tracks} of the unrefused examples of `parts` whose own backing variant loses a track."""
    plan = {}
    for sid, tracks in desired.items():
        for e in secs.get(sid, []):
            if e["refused"] or e["part"] not in parts:
                continue
            gone = sorted(set(tracks) & set(variants[sid]["v" if e["vocals"] else "n"]))
            if gone:
                plan[e["i"]] = gone
    return plan


def keyed_rows(d, prefix):
    """{(i, key): last row} over every worker's rows `<prefix>-*.jsonl` in d."""
    out = {}
    for f in sorted(d.glob(f"{prefix}-*.jsonl")):
        for r in read_jsonl(f):
            if "key" in r:
                out[(r["i"], r["key"])] = r
    return out


def pool_rows(proot):
    return keyed_rows(proot / "rows", "pool")


def pool_state(plan, built, pending=None):
    """What the candidate list asks for against what is built.
    plan: {i: tracks} wanted removed; pending: {i: tracks} touched by a pending candidate.
    -> (to build: {i: tracks}, current: {i: row}, stale: {i: [rows]}, excluded: {i: reason}).
    - current: built under the wanted key (and not excluded);
    - stale: rebuilds under a key no longer wanted (kept on disk, not read);
    - excluded (fail closed: neither original nor rebuilt may be read): a refused rebuild under the wanted key,
      or an example still touched by a pending candidate."""
    pending = pending or {}
    to_build, current, stale, excluded = {}, {}, {}, {}
    keys = {i: removal_key(t) for i, t in plan.items()}
    for (i, k), r in built.items():
        if keys.get(i) == k and r.get("refused"):
            excluded[i] = f"refused: {r['refused']}"
        elif keys.get(i) == k:
            current[i] = r
        elif not r.get("refused"):
            stale.setdefault(i, []).append(r)
    for i, t in pending.items():
        excluded.setdefault(i, "pending review: " + ", ".join(sorted(t)))
    for i, t in plan.items():
        if i not in current and not built.get((i, keys[i]), {}).get("refused"):
            to_build[i] = t
    current = {i: r for i, r in current.items() if i not in excluded}
    return to_build, current, stale, excluded


def cmd_pool_candidates(args):
    require_real(args)
    root = out_root(args)
    trusted = _load(root / "trusted.json")
    if not trusted or (trusted.get("smoke") and not args.smoke):
        raise SystemExit("pool-candidates needs step 0's trusted.json (run lists first)")
    rows, secs = scan_rows(root), build_sections()
    cands = candidates_from(rows, secs)
    rec = {"plan": PLAN, "step": "2 (data)", "smoke": bool(args.smoke),
           "made_from": {"trusted_sha256": sha256_file(root / "trusted.json")},
           "how_to_edit": "after listening, set each candidate's 'verdict' (e.g. 'double' or 'not a double') and "
                          "'rebuild': true rebuilds its sections' examples without the track; false with a verdict keeps "
                          "the track (the examples read their originals); false with no verdict is pending and excludes "
                          "the examples. Then pool-status shows the difference and pool-rebuild / rin-rebuild build it",
           "candidates": cands, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    path = candidates_path(root)
    if path.exists():                                   # never overwrite a list that may carry verdicts
        path = root / "candidates-new.json"
        print(f"candidates.json exists: the fresh list goes to {path.name} for comparison", flush=True)
    _save(path, rec)
    d = [c for c in cands if c["kind"] == "double"]
    on = [c for c in d if c["rebuild"]]
    print(f"candidates: {len(d)} doubles ({len(on)} guitar doubles on; the rest pending), {len(cands) - len(d)} takes "
          f"(pending review); pool examples touched by the doubles switched on {sum(c['pool_examples'] for c in on):,}",
          flush=True)
    for c in d:
        ch = [round(e["chroma"], 2) for e in c["evidence"] if e["chroma"] is not None]
        print(f"  double ({'on' if c['rebuild'] else 'pending'}, {c['class']}) {c['band']}: "
              f"{c['di'].split('/')[-1]} <- {c['track']}: {len(c['sections'])} sections, "
              f"{c['pool_examples']} pool / {c['r_in_examples']} R_in examples, chroma {ch}", flush=True)


def load_candidates(root, path=None, smoke=False):
    """The candidate list, refused if it is a smoke test's (for a real run) or was made from other step-0 lists."""
    p = pathlib.Path(path).expanduser() if path else candidates_path(root)
    rec = _load(p)
    if not rec:
        raise SystemExit(f"no candidate list at {p} (run pool-candidates first)")
    if rec.get("smoke") and not smoke:
        raise SystemExit("the candidate list is a smoke test's")
    tp = root / "trusted.json"
    if not tp.exists() or rec.get("made_from", {}).get("trusted_sha256") != sha256_file(tp):
        raise SystemExit("the candidate list was made from other step-0 lists than trusted.json")
    return rec, p


def candidate_plans(root, rec, parts):
    """(wanted {i: tracks}, pending {i: tracks}) of the examples of `parts` under a candidate list."""
    rows, secs = scan_rows(root), build_sections()
    variants = {sid: r["variants"] for sid, r in rows.items()}
    return (example_plan(desired_removals(rec["candidates"]), secs, variants, parts),
            example_plan(pending_removals(rec["candidates"]), secs, variants, parts))


def cmd_pool_status(args):
    from learn import direct_stems as DS

    require_real(args)
    root = out_root(args)
    rec, cpath = load_candidates(root, args.candidates, args.smoke)
    plan, pending = candidate_plans(root, rec, ("pilot", "rest"))
    proot = pool_root(root)
    to_build, current, stale, excluded = pool_state(plan, pool_rows(proot), pending)
    man = {"plan": PLAN, "step": "2 (data)", "smoke": bool(args.smoke), "candidates": str(cpath),
           "candidates_sha256": sha256_file(cpath), "stem_sep": STEP_SEP, "complete": not to_build,
           "rebuilt": {str(i): {"key": r["key"], "removed": r["removed"],
                                "mix": str(DS.ex_path(proot, i, f"mix-{r['key']}")),
                                "stem": str(DS.ex_path(proot, i, f"{STEP_SEP}-{r['key']}"))} for i, r in current.items()},
           "excluded": {str(i): why for i, why in sorted(excluded.items())},
           "to_build": {str(i): t for i, t in to_build.items()},
           "stale": {str(i): [r["key"] for r in rs] for i, rs in stale.items()},
           "note": "arm T reads 'rebuilt' examples from their listed files, never reads 'excluded' ones (refused "
                   "rebuilds, or examples a pending candidate still touches), and reads every other pool example from "
                   "its original D-build files; 'stale' rebuilds stay on disk unused; arm T needs complete = true",
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(proot / "manifest.json", man)
    print(f"pool: {len(plan):,} examples wanted rebuilt; {len(current):,} built and current, {len(to_build):,} to "
          f"build, {len(excluded):,} excluded (refused or pending review), {len(stale):,} with a stale rebuild "
          f"(read as original unless excluded)", flush=True)


def _rebuilt_mix(ctx, r, ex, gone):
    """The rebuilt true mix of a rendered pool example: its backing variant without `gone`, rescaled to the drawn
    ratio, the same overall gain and mastering draw. -> (mix, record)."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_aug as SA

    i, sid = r["i"], r["section"]
    kind = "v" if ex["draw"]["vocals"] else "n"
    b, meta = ctx.backing(sid, kind)
    sec = ctx.sections[sid]
    sess = pathlib.Path(ctx.inv[sec["di"]]["session_dir"])
    nb = np.asarray(b, np.float64).copy()
    for t in gone:
        if t not in meta["tracks"][kind]:
            raise SystemExit(f"{i}: {t} is not in its backing")
        nb -= PS.section_audio(sess / t, sec["start_s"])[int(PS.TRIM_S * PS.SR):]
    gb, ga = ex["draw"]["gains_db"]
    lb_new = SA.lufs(nb)
    gb_new = rebuilt_gain_db(gb, meta[f"lufs_{kind}"], lb_new, r["lufs"])
    mastered, mrng = DS.master_draw(i)
    mix = assemble(ex["y"], nb, gb_new, ga)
    mix = SA.compress(mix, mrng) if mastered else mix
    return mix, {"kind": kind, "lufs_backing_old": meta[f"lufs_{kind}"], "lufs_backing_new": lb_new,
                 "gain_backing_db": [gb, gb_new], "gain_db": ga, "mastered": mastered}


def cmd_pool_rebuild(args):
    import gc
    import queue
    import threading

    import numpy as np

    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import pretrain_set as PS

    require_real(args)
    root = out_root(args)
    rec, cpath = load_candidates(root, args.candidates, args.smoke)
    free = PS.free_gb()
    if free < DISK_GUARD_GB:
        raise SystemExit(f"free disk {free:.1f} GB, below the {DISK_GUARD_GB:.0f} GB guard")
    plan, pending = candidate_plans(root, rec, ("pilot", "rest"))
    proot = pool_root(root)
    to_build = pool_state(plan, pool_rows(proot), pending)[0]
    print(f"pool-rebuild ({cpath.name}): {len(plan):,} examples wanted, {len(to_build):,} to build; X-LANCE on "
          f"{args.device}, order {args.order}", flush=True)
    if not to_build:
        print("POOL-REBUILD DONE", flush=True)
        return
    ctx = DS.Ctx(quiet=True)
    by_i = {r["i"]: r for r in ctx.pool}
    todo = DS.render_order([by_i[i] for i in to_build], reverse=args.order == "desc")[:args.limit or None]
    ctx.rows = None                                       # part C's rows (about 1.4 GB): the pool rows are kept above
    gc.collect()
    sep = DS.stem_separator(STEP_SEP, args.device)
    swap0 = DS.swap_mb()
    q, stop, err = queue.Queue(maxsize=QUEUE), threading.Event(), []
    worker = f"{args.device}-{args.order}-{os.getpid()}"

    def produce():
        rr = None
        try:
            DS.wait_render_slot()
            rr = K.Renderer()
            primer = DS.Primer(rr)
            menu = rr.menu()
            DS.check_recipe(rr)
            for r in todo:
                if stop.is_set():
                    break
                gone = to_build[r["i"]]
                key = removal_key(gone)
                if (r["i"], key) in pool_rows(proot):                   # another worker's row: done
                    continue
                ex = DS.example_audio(ctx, primer, menu, r)
                item = {"r": r, "gone": gone, "key": key}
                if "refused" in ex:
                    item["refused"] = ex["refused"]
                else:
                    stored = np.load(DS.ex_path(DS.ROOT, r["i"], "mix"))
                    mels, lu, _ = DS.half_features(ex["mix"])
                    ok, share, dl = parity(mels, lu, stored)
                    item.update(orig_share=share, orig_lufs_diff=dl)
                    if not ok:
                        item["refused"] = "the original re-mix differs from the stored mix"
                    else:
                        item["mix"], item["rec"] = _rebuilt_mix(ctx, r, ex, gone)
                while not stop.is_set():
                    try:
                        q.put(item, timeout=1)
                        break
                    except queue.Full:
                        pass
            print(f"renders {primer.renders} (priming {primer.primes})", flush=True)
        except BaseException as e:                     # noqa: BLE001 - handed to the main thread
            err.append(e)
        finally:
            if rr is not None:
                rr.close()
            while True:
                try:
                    q.put(None, timeout=1)
                    break
                except queue.Full:
                    if stop.is_set():
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            pass

    th = threading.Thread(target=produce, daemon=True)
    th.start()
    rp = proot / "rows" / f"pool-{worker}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    n_done, refused, code = 0, 0, 0
    t_start = time.time()
    try:
        with open(rp, "a") as fh:
            while True:
                item = q.get()
                if item is None:
                    break
                g = DS._guards("pool", DISK_GUARD_GB, swap0)
                if g:
                    print(g[1], flush=True)
                    code = g[0]
                    stop.set()
                    break
                r, key = item["r"], item["key"]
                if (r["i"], key) in pool_rows(proot):
                    continue
                row = {"i": r["i"], "section": r["section"], "band": r["band"], "early_stop": bool(r.get("early_stop")),
                       "key": key, "removed": item["gone"], "candidates_sha256": sha256_file(cpath),
                       "orig_share": item.get("orig_share"), "orig_lufs_diff": item.get("orig_lufs_diff")}
                if "refused" in item:
                    refused += 1
                    row["refused"] = item["refused"]
                else:
                    t0 = time.time()
                    mix = item["mix"]
                    s = np.asarray(sep(mix), np.float64)
                    if len(s) != len(mix) or not np.isfinite(s).all():
                        raise SystemExit(f"{r['i']}: bad stem")
                    mm, ml, _ = DS.half_features(mix)
                    sm, sl, floor = DS.half_features(s)
                    DS._save_npz(DS.ex_path(proot, r["i"], f"mix-{key}"), mA=mm["A"], mB=mm["B"],
                                 lufs=[ml["A"], ml["B"]], gain_db=item["rec"]["gain_db"],
                                 mastered=item["rec"]["mastered"])
                    DS._save_npz(DS.ex_path(proot, r["i"], f"{STEP_SEP}-{key}"), sA=sm["A"], sB=sm["B"],
                                 lufs=[sl["A"], sl["B"]])
                    row.update(**item["rec"], lufs_mA=ml["A"], lufs_mB=ml["B"], lufs_sA=sl["A"], lufs_sB=sl["B"],
                               floor_share=floor, sep=STEP_SEP, device=args.device, worker=worker,
                               sep_seconds=round(time.time() - t0, 2))
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                n_done += 1
                if n_done % 25 == 0:
                    print(f"pool {n_done}/{len(todo)} i={r['i']} refused {refused}; "
                          f"{(time.time() - t_start) / n_done:.1f} s each", flush=True)
    finally:
        stop.set()
        while th.is_alive():
            try:
                q.get(timeout=1)
            except queue.Empty:
                pass
        th.join()
    if err:
        raise err[0]
    if code:
        raise SystemExit(code)
    print(f"POOL-REBUILD DONE ({n_done} this run, refused {refused}); run pool-status for the manifest", flush=True)


# --- the bleed-injection test (decision memo, 2026-10-23) ------------------------------------------------------
#
# Does the target take's own bleed, at the levels measured in the live sessions, move F's answers? The example's own
# original amp track, through a synthetic room path, is added to the backing of R_in examples step 0 trusts, at
# -18, -14 and -8 dB under the render; the injected and the clean (re-made original) mixes are separated by the same
# path and F reads both. Zero renders. It shares the MPS with nothing: it refuses while a pool rebuild runs.

BLEED_SEED = 20261098
BLEED_DB = (-18.0, -14.0, -8.0)            # Eggy's and Swatkins' medians (both readings agree); Renesans' amp-source
BLEED_BAND = "Adam Buckley"
BLEED_EXPECT = (188, 6)                    # examples, sections: Adam Buckley's trusted ElecGtr3 R_in examples
BLEED_SPAN = (1.0, 10.0)                   # the judged span (s), where the level is set
POOL_REBUILD_RE = r"-m learn\.data_cleaning pool-rebuild\b"


def bleed_key(level):
    return f"bleed{int(round(abs(level)))}"


def band_energy(x, sr=48_000, lo=F_LO, hi=F_HI, span=BLEED_SPAN):
    """Energy of x in [lo, hi) Hz over the judged span."""
    import numpy as np

    seg = np.asarray(x, np.float64)[int(span[0] * sr):int(span[1] * sr)]
    if not len(seg):
        return 0.0
    X = np.fft.rfft(seg)
    f = np.fft.rfftfreq(len(seg), 1 / sr)
    return float(np.sum(np.abs(X[(f >= lo) & (f < hi)]) ** 2))


def bleed_gain(y, c, level_db, sr=48_000):
    """The gain that puts c at level_db (energy, 250 Hz-8 kHz, judged span) against the render y; None if c is
    silent there."""
    ey, ec = band_energy(y, sr), band_energy(c, sr)
    return math.sqrt(10 ** (level_db / 10) * ey / ec) if ec > 0 and ey > 0 else None


def others_running(ps, pattern, own=()):
    """[pid] of python processes (not shell wrappers) whose command matches `pattern`, other than `own`."""
    out = []
    for pid, cmd in ps:
        first = cmd.split(" ", 1)[0] if cmd else ""
        if pid not in own and "python" in os.path.basename(first).lower() and re.search(pattern, cmd):
            out.append(pid)
    return out


def answer_movement(a, b):
    """Mean over shared examples of the mean |a - b| of their continuous answers (0-1 knob scale)."""
    import numpy as np

    keys = sorted(set(a) & set(b))
    if not keys:
        return None
    return float(np.mean([np.nanmean(np.abs(np.asarray(a[i], float) - np.asarray(b[i], float))) for i in keys]))


def bleed_examples(ctx, trusted):
    """R_in examples step 0 trusts, of the declared band, whose DI has its own amp track; in section order."""
    bad = set(trusted["untrusted"])
    return sorted((r for r in ctx.parts["vsep"] if not ctx.tag[r["i"]] and r["i"] not in bad and r["band"] == BLEED_BAND
                   and ctx.inv[ctx.sections[r["section"]]["di"]].get("own")), key=lambda r: (r["section"], r["i"]))


def bleed_root(root):
    return root / "bleed"


def refuse_beside_pool_rebuild():
    from learn import ks_extend as X

    busy = others_running(X._ps(), POOL_REBUILD_RE, {os.getpid(), os.getppid()})
    if busy:
        raise SystemExit(f"a data_cleaning pool-rebuild is running (pids {busy}): the bleed test waits for the MPS")


def cmd_bleed_test(args):
    import gc

    import numpy as np
    from scipy.signal import fftconvolve

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_aug as SA

    require_real(args)
    refuse_beside_pool_rebuild()
    root = out_root(args)
    trusted = _load(root / "trusted.json")
    if not trusted or (trusted.get("smoke") and not args.smoke):
        raise SystemExit("bleed-test needs step 0's trusted.json")
    free = PS.free_gb()
    if free < DISK_GUARD_GB:
        raise SystemExit(f"free disk {free:.1f} GB, below the {DISK_GUARD_GB:.0f} GB guard")
    ctx = DS.Ctx(quiet=True)
    exs = bleed_examples(ctx, trusted)
    n_sec = len({r["section"] for r in exs})
    if (len(exs), n_sec) != BLEED_EXPECT and not args.smoke:
        raise SystemExit(f"{len(exs)} examples in {n_sec} sections, not the declared {BLEED_EXPECT}")
    ctx.rows = None
    gc.collect()
    br = bleed_root(root)
    keys = ["clean"] + [bleed_key(L) for L in BLEED_DB]
    built = keyed_rows(br / "rows", "bleed")
    todo = [r for r in exs if any((r["i"], k) not in built for k in keys)][:args.limit or None]
    print(f"bleed-test: {len(exs)} examples in {n_sec} sections, {len(todo)} to do; levels {BLEED_DB} dB; "
          f"X-LANCE on {args.device}", flush=True)
    if not todo:
        print("BLEED-TEST DONE", flush=True)
        return
    gd = DS.ROOT / "gate"
    truth = G.gate_rows(gd, "truth")
    sep = DS.stem_separator(STEP_SEP, args.device)
    swap0 = DS.swap_mb()
    rp = br / "rows" / f"bleed-{args.device}-{os.getpid()}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rooms, refused, n_sep, t_start = {}, 0, 0, time.time()

    def separate(mix):
        s_ = np.asarray(sep(mix), np.float64)
        if len(s_) != len(mix) or not np.isfinite(s_).all():
            raise SystemExit("bad stem")
        return DS.half_features(s_)

    with open(rp, "a") as fh:
        for m, r in enumerate(todo):
            g = DS._guards("bleed", DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            i, sid = r["i"], r["section"]
            base = {"i": i, "section": sid, "band": r["band"]}
            need = [k for k in keys if (i, k) not in built]
            made = _truth_mix(ctx, G, gd, truth, r, PS, DS, SA)
            if isinstance(made, str):
                refused += 1
                for k in need:
                    fh.write(json.dumps({**base, "key": k, "refused": made}) + "\n")
                fh.flush()
                continue
            if "clean" in need:
                sm, sl, floor = separate(made["orig"])
                DS._save_npz(DS.ex_path(br, i, f"{STEP_SEP}-clean"), sA=sm["A"], sB=sm["B"], lufs=[sl["A"], sl["B"]])
                fh.write(json.dumps({**base, "key": "clean", "orig_share": made["orig_share"],
                                     "lufs_sA": sl["A"], "lufs_sB": sl["B"], "floor_share": floor}) + "\n")
                n_sep += 1
            if sid not in rooms:                          # one room per section: the own amp track through it
                sec = ctx.sections[sid]
                rec = ctx.inv[sec["di"]]
                part = rec.get("part") or part_base(sec["di"])
                own = [o for o in rec["own"] if part.lower() in o.lower()] or list(rec["own"])
                sess = pathlib.Path(rec["session_dir"])
                amp = sum(PS.section_audio(sess / o, sec["start_s"])[int(PS.TRIM_S * PS.SR):] for o in own)
                rng = np.random.default_rng(int(hashlib.sha256(f"{BLEED_SEED}|{sid}".encode()).hexdigest()[:8], 16))
                rooms[sid] = (fftconvolve(np.asarray(amp, np.float64), room_ir(rng, sr=PS.SR))[:len(amp)], own)
            c, own = rooms[sid]
            for L in BLEED_DB:
                k = bleed_key(L)
                if k not in need:
                    continue
                gain = bleed_gain(made["y"], c, L, PS.SR)
                if gain is None:
                    fh.write(json.dumps({**base, "key": k, "refused": "the own amp track is silent here"}) + "\n")
                    continue
                pre = made["y"] + made["b"] * 10 ** (made["gb"] / 20) + gain * c
                mix = pre * 10 ** (made["ga"] / 20)
                _, mrng = DS.master_draw(i)
                mix = SA.compress(mix, mrng) if made["mastered"] else mix
                mm, ml, _ = DS.half_features(mix)
                sm, sl, floor = separate(mix)
                DS._save_npz(DS.ex_path(br, i, f"mix-{k}"), mA=mm["A"], mB=mm["B"], lufs=[ml["A"], ml["B"]],
                             gain_db=made["ga"], mastered=made["mastered"])
                DS._save_npz(DS.ex_path(br, i, f"{STEP_SEP}-{k}"), sA=sm["A"], sB=sm["B"], lufs=[sl["A"], sl["B"]])
                got = 10 * math.log10(band_energy(gain * c, PS.SR) / band_energy(made["y"], PS.SR))
                fh.write(json.dumps({**base, "key": k, "level_db": L, "level_check_db": round(got, 3), "own": own,
                                     "lufs_mA": ml["A"], "lufs_mB": ml["B"], "lufs_sA": sl["A"], "lufs_sB": sl["B"],
                                     "floor_share": floor}) + "\n")
                n_sep += 1
            fh.flush()
            if m % 10 == 0:
                print(f"bleed {m + 1}/{len(todo)} i={i}: {n_sep} separations, refused {refused}; "
                      f"{(time.time() - t_start) / (m + 1):.1f} s per example", flush=True)
    print(f"BLEED-TEST DONE ({len(todo)} examples, {n_sep} separations, refused {refused})", flush=True)


def cmd_bleed_read(args):
    import numpy as np

    from learn import direct_stems as DS

    require_real(args)
    root = out_root(args)
    trusted = _load(root / "trusted.json")
    if not trusted or (trusted.get("smoke") and not args.smoke):
        raise SystemExit("bleed-read needs step 0's trusted.json")
    br = bleed_root(root)
    keys = ["clean"] + [bleed_key(L) for L in BLEED_DB]
    built = keyed_rows(br / "rows", "bleed")
    ro = DS._load(DS.ROOT / "full" / "readout.json")
    if not ro or ro.get("smoke"):
        raise SystemExit("bleed-read needs step 3's real full/readout.json")
    D = DS.d_arm(DS._load(DS.ROOT / "pilot" / "pilot-report.json"))
    nets, recs = DS.load_full_runs(DS.ROOT, D, stem_sep=STEP_SEP)
    if {str(r["seed"]): r["model_sha256"] for r in recs} != ro["models"]["D"]:
        raise SystemExit("step 3's D_stem runs differ from those readout.json read")
    med, table = DS.medians_from_json(ro["constant"]), DS.table_from_json(ro["pull"]["D"])
    ctx = DS.Ctx(quiet=True)
    exs = bleed_examples(ctx, trusted)
    missing = [r["i"] for r in exs if any((r["i"], k) not in built for k in keys)]
    if missing and not args.smoke:
        raise SystemExit(f"{len(missing)} examples are not built at every level (run bleed-test)")
    refused = sorted({r["i"] for r in exs for k in keys if built.get((r["i"], k), {}).get("refused")})
    rows = [r for r in exs if r["i"] not in refused and r["i"] not in missing]
    if not rows:
        raise SystemExit("no example built at every level")
    section_of = {r["i"]: r["section"] for r in rows}
    cell_of = {r["i"]: (r["amp"], r["base"]) for r in rows}
    const = DS.const_errors(rows, med, DS.encode_audible)
    stored_mix = lambda i: DS.ex_path(DS.ROOT, i, "mix")               # noqa: E731
    per, ans, seed_ref = {}, {}, None
    for k in keys:
        mix_of = stored_mix if k == "clean" else (lambda i, k=k: DS.ex_path(br, i, f"mix-{k}"))
        outs, who, Y = DS.run_rows(nets, rows, lambda x, a=mix_of, k=k: stem_tensors(
            x, a, lambda i: DS.ex_path(br, i, f"{STEP_SEP}-{k}"), D))
        sc, ans[k], _, _ = DS.score_all(outs, who, DS.silent_masks(Y), cell_of, med, table)
        per[k] = DS.readout_per(sc)["A1+A2+A3"]
        if k == "clean":
            seed_ref = answer_movement(DS.median_answers(outs[:2], who)[1], DS.median_answers(outs[2:], who)[1])
    res = {"examples": len(rows), "sections": len(set(section_of.values())), "refused": len(refused),
           "F - constant, clean": section_interval(per["clean"], const, section_of, set(per["clean"])),
           "seed disagreement on clean (42+43 vs 44), mean |answer change|": seed_ref, "levels": {}}
    for L in BLEED_DB:
        k = bleed_key(L)
        res["levels"][str(L)] = {
            "injected - clean (paired, section-clustered; primary)": section_interval(per[k], per["clean"], section_of,
                                                                                     set(per[k])),
            "F - constant, injected": section_interval(per[k], const, section_of, set(per[k])),
            "mean |answer change|, injected vs clean": answer_movement(ans[k], ans["clean"]),
            "per section, injected - clean": {
                sid.split("/")[-1]: float(np.mean([per[k][i] - per["clean"][i] for i in per[k] if section_of[i] == sid]))
                for sid in sorted(set(section_of.values()))}}
    out = {"plan": PLAN, "step": "bleed-injection test (decision memo, 2026-10-23)", "smoke": bool(args.smoke),
           "decides": "nothing by itself (descriptive; the user decides on option (a))",
           "readout": "amendment 5: A1+A2+A3, masked E; step 3's stored constant and D pull; 3 seeds",
           "models": ro["models"]["D"], "levels_db": list(BLEED_DB), "results": res,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "bleed-read.json", out)

    def f(v):
        return "n/a" if v is None else f"{v[0]:+.4f} [{v[1]:+.4f}, {v[2]:+.4f}] ({v[3]} sections)"

    print(f"bleed test: {res['examples']} examples in {res['sections']} sections (refused {res['refused']})")
    print(f"  F - constant, clean: {f(res['F - constant, clean'])}")
    print(f"  seed disagreement on clean: {seed_ref}")
    for L, v in res["levels"].items():
        print(f"  {L} dB: injected - clean {f(v['injected - clean (paired, section-clustered; primary)'])}; "
              f"F - constant {f(v['F - constant, injected'])}; answer change "
              f"{v['mean |answer change|, injected vs clean']}")


# --- CLI -------------------------------------------------------------------------------------------------------

def parse_shard(s):
    k, n = (int(x) for x in s.split("/"))
    if not 0 <= k < n:
        raise argparse.ArgumentTypeError(f"bad shard {s}")
    return k, n


def main(argv=None):
    ap = argparse.ArgumentParser(prog="learn.data_cleaning")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out", help="the output root (default ~/ndsp-presets/learn/data-cleaning); "
                                     "a scratch directory for smoke tests")
        p.add_argument("--smoke", action="store_true")
        p.add_argument("--limit", type=int, default=0, help="smoke only: the first N sections or examples")

    p = sub.add_parser("inject", help="0a: the take estimator's injection check")
    common(p)
    p.add_argument("--dev", action="store_true", help="smoke only: the 4 development sessions instead of the draw")
    p.set_defaults(fn=cmd_inject)
    p = sub.add_parser("scan", help="0b: take levels and same-part tests per section")
    common(p)
    p.add_argument("--shard", type=parse_shard, default=(0, 1))
    p.add_argument("--only", help="smoke only: sections whose id contains this text")
    p.set_defaults(fn=cmd_scan)
    p = sub.add_parser("lists", help="0c: the trusted lists, counts and route")
    common(p)
    p.set_defaults(fn=cmd_lists)
    p = sub.add_parser("rin-rebuild", help="1a: R_in examples the candidate list touches, re-mixed without the "
                                            "tracks; X-LANCE on the rebuilt and the re-made original mixes")
    common(p)
    p.add_argument("--candidates", help="the candidate list (default <out>/candidates.json)")
    p.add_argument("--device", choices=("mps", "cpu"), default="mps")
    p.set_defaults(fn=cmd_rin_rebuild)
    p = sub.add_parser("rin-read", help="1b: F on the rebuilt against the re-separated original stems (paired)")
    common(p)
    p.add_argument("--candidates", help="the candidate list (default <out>/candidates.json)")
    p.set_defaults(fn=cmd_rin_read)
    p = sub.add_parser("bleed-test", help="the bleed-injection test's mixes and stems (zero renders; X-LANCE on MPS, "
                                           "never beside a pool rebuild)")
    common(p)
    p.add_argument("--device", choices=("mps", "cpu"), default="mps")
    p.set_defaults(fn=cmd_bleed_test)
    p = sub.add_parser("bleed-read", help="the bleed-injection test's readout: F on injected vs clean (zero renders)")
    common(p)
    p.set_defaults(fn=cmd_bleed_read)
    p = sub.add_parser("pool-candidates", help="2 (data): the candidate list from step 0 (never overwrites verdicts)")
    common(p)
    p.set_defaults(fn=cmd_pool_candidates)
    p = sub.add_parser("pool-status", help="2 (data): the candidate list against what is built; the manifest")
    common(p)
    p.add_argument("--candidates", help="the candidate list (default <out>/candidates.json)")
    p.set_defaults(fn=cmd_pool_status)
    p = sub.add_parser("pool-rebuild", help="2 (data): rebuild the pool examples the candidate list asks for (renders)")
    common(p)
    p.add_argument("--candidates", help="the candidate list (default <out>/candidates.json)")
    p.add_argument("--device", choices=("mps", "cpu"), default="mps")
    p.add_argument("--order", choices=("asc", "desc"), default="asc", help="two workers meet in the middle")
    p.set_defaults(fn=cmd_pool_rebuild)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
