"""Cleaning the direct model's data (`docs/data-cleaning-options.md`, declared 2026-10-22; the user's rule
of 2026-10-22: use only what we can trust, no dirty tracks). Development data only; no held-out data.
Step 0 (zero renders, CPU) declares the trusted sets; step 1 (zero renders) rebuilds every untrusted
R_in example without its offending backing tracks and reads step 3's D_stem (F) on the original against
the rebuilt stems of the same examples.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    MSST=~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN     -m learn.data_cleaning inject                   # 0a: INJECTION OK | INJECTION FAIL (gates 0b)
    $MAIN     -m learn.data_cleaning scan --shard k/3         # 0b: per section and kept track: take level, same part
    $MAIN     -m learn.data_cleaning lists                    # 0c: trusted lists, counts, route (drop | rebuild)
    $MSST     -m learn.data_cleaning rin-rebuild --device mps # 1a: untrusted R_in re-mixed without them, X-LANCE
    $TORCH_PY -m learn.data_cleaning rin-read                 # 1b: F on original vs rebuilt stems (paired)

**The take level** of a kept backing track in a section is the energy of the target's original take in
it, in dB of the original take's own close-mic (amp) track, per judge half (A 1.0-5.5 s, B 5.5-10 s),
the larger of the two. It does not depend on the example's level draw (the review: removal is per
section, never per example, so no level filter comes back).
- **A confirmed same-part track** (another take of the target's part): its whole power counts.
  Candidates: Cambridge "DT" naming, onset correlation with the DI >= 0.6 in the section, or onsets
  that follow the DI at least as well as the own amp track does. **Confirmed by pitch:** chroma
  similarity with the own amp track (the DI when there is none) >= 0.70 in the section, the weakest
  own pair of the label table (0.696).
- **Any other track:** a session-level reading (a room path does not change between sections): the
  held-out energy a per-bin complex ridge regression on the own amp track (lags -1..6 STFT frames,
  24 kHz, 2048/1024, 250 Hz-8 kHz, ridge 0.3) explains over the whole session in 10 contiguous folds,
  on frames where the amp plays, less the mean of four nulls (the source rolled +-2 and +-3 s), in dB
  of the amp's energy, never above the track's own. The amp source is the upper bound (a live amp
  track's own drum bleed can pose as take); the DI-source reading is reported beside as the lower
  bound. Takes under -40 dB count as none. Parts without an amp track have no original take: only
  confirmed same-part tracks count there.
- **The rule (one threshold, as the amp-track targets' "low" bleed flag):** remove the fewest tracks,
  largest take first, until the section's summed take is <= -30 dB. An example is untrusted iff its
  own backing variant (with or without vocals) loses a track.
- **The estimator is validated first** (`inject`): a room-filtered copy of the own amp track injected
  at -20, -25 and -30 dB into the loudest kept drum or room track of 12 clean Cambridge sessions (not
  the 4 it was developed on) must read back within 3 dB (at -20 and -25) and at >= -33 dB (at -30) in
  >= 10 of 12; the uninjected track must read under -35 dB in >= 11 of 12; and at most 5% of the other
  non-guitar tracks of those studio sessions may read at or above -30 dB. `scan` refuses without
  INJECTION OK.

**Step 1 (no target renders):** the gate's 1,407 stored truth renders (FLAC, hash-checked) are each
example's rendered guitar. The original mix is rebuilt from it with the stored draw and must match
the stored mix mels (99% of cells within one 0.5-dB step, half LUFS within 0.01) or the example is
refused. The rebuilt mix drops the section's removed tracks from the example's backing, keeps the
ratio, vocals, loudness and mastering draws (the backing is rescaled to the same ratio), and is
separated by X-LANCE gtr_mss on MPS. `rin-read` scores F (step 3's D_stem, 3 seeds; the 2-seed pair
beside) with step 3's stored constant and pull (amendment 5's A1+A2+A3, masked E).

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
INJECT_SEED = 20261097
INJECT_N = 12
INJECT_DB = (-20.0, -25.0, -30.0)
INJECT_TOL_DB = 3.0
INJECT_DETECT_DB = -33.0                   # at -30 dB the reading must reach at least this
INJECT_BASE_DB = -35.0                     # the uninjected track must read under this
INJECT_NEED = 10 / 12                      # shares of sections (12: >= 10)
INJECT_BASE_NEED = 11 / 12
INJECT_FP_MAX = 0.05                       # other non-guitar tracks of the clean sessions at or above TAKE_DB
CLEAN_EXCESS = 0.002                       # injection sessions: Cambridge, every kept track's coherence <= this
# The estimator's settings (250 Hz floor, per-bin weights, ridge 0.3, session-level folds, nulls at +-2/3 s, the clip
# at the track's power) were chosen in smoke runs on these 4 clean sessions' DIs; the check draws its 12 of the other 13.
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


def injection_verdict(rows, levels=INJECT_DB, tol=INJECT_TOL_DB, need=INJECT_NEED, base_need=INJECT_BASE_NEED,
                      detect=INJECT_DETECT_DB, base_max=INJECT_BASE_DB, fp_max=INJECT_FP_MAX, thr=TAKE_DB):
    """INJECTION OK iff every declared level reads back (within tol at the louder levels, >= detect at the
    threshold level) in >= need of the sessions, the uninjected target stays under base_max in >= base_need,
    and at most fp_max of the other non-guitar tracks of these clean studio sessions read at or above thr.
    rows: [{"base": dB|None, "inj": {level: dB|None}, "others": {track: dB|None}}].
    -> (verdict, {level: share}, base share, false-positive share)."""
    n = len(rows)
    if not n:
        return "FAIL", {}, 0.0, 1.0
    shares = {}
    for L in levels:
        if L == min(levels):
            ok = [r["inj"].get(L) is not None and r["inj"][L] >= detect for r in rows]
        else:
            ok = [r["inj"].get(L) is not None and abs(r["inj"][L] - L) <= tol for r in rows]
        shares[L] = sum(ok) / n
    base = sum(r["base"] is None or r["base"] < base_max for r in rows) / n
    others = [v for r in rows for v in (r.get("others") or {}).values()]
    fp = sum(v is not None and v >= thr for v in others) / len(others) if others else 0.0
    good = all(s >= need - 1e-9 for s in shares.values()) and base >= base_need - 1e-9 and fp <= fp_max + 1e-9
    return ("OK" if good else "FAIL"), shares, base, fp


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
    if getattr(args, "limit", 0) or getattr(args, "only", None):
        raise SystemExit("--limit and --only are for smoke tests (with --smoke and --out) only")
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


def clean_injection_dis(meta, secs, n=INJECT_N, seed=INJECT_SEED, max_excess=CLEAN_EXCESS, exclude=DEV_DIS):
    """INJECT_N training DIs (Cambridge, with an own amp track) whose kept tracks all read coherence excess
    <= max_excess in part C's leakage check, drawn by the seed, leaving out the DIs the estimator was developed
    on (`DEV_DIS`)."""
    dis = set()
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
            dis.add(di)
    dis = sorted(dis - set(exclude))
    random.Random(seed).shuffle(dis)
    return dis[:n]


def injection_target(tracks):
    """The injection's target: the loudest kept drum or room track (else the loudest non-vocal, non-guitar
    track). tracks: {name: session power dB}."""
    for ok in (lambda t: track_class(t) == "drums", lambda t: track_class(t) not in ("vocal", "guitar")):
        c = {t: p for t, p in tracks.items() if ok(t) and p is not None}
        if c:
            return max(c, key=c.get)
    return None


def inject_di(meta, di, seed=INJECT_SEED, levels=INJECT_DB):
    """The injection check on one clean session: a room-filtered copy of the own amp track added to the target
    track at each level (dB of the own amp over its counted frames), read back with the session estimator;
    every other kept track read uninjected (false positives)."""
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
    audio, Ys = {}, {}
    for t in withv:
        y = load_window(sess / t, 0.0, dur)
        Ys[t] = stft(y)[idx]
        audio[t] = y
    power = {t: reader.power(Y) for t, Y in Ys.items()}
    target = injection_target(power)
    rng = np.random.default_rng(int(hashlib.sha256(f"{seed}|{di}".encode()).hexdigest()[:8], 16))
    c = fftconvolve(amp, room_ir(rng))[:len(amp)].astype(np.float32)
    C = stft(c)[idx]
    unit = float(np.sum(np.abs(C[:, reader.counted]) ** 2)) / reader.ref
    for L in levels:
        g = math.sqrt(10 ** (L / 10) / unit)
        Ys[f"inject {L:+.0f}"] = stft(audio[target] + g * c)[idx]
    del audio
    takes = reader.takes(Ys)
    others = {t: takes[t] for t in withv if t != target and track_class(t) != "guitar"}
    return {"di": di, "source": src_name, "track": target, "base": takes[target],
            "inj": {L: takes[f"inject {L:+.0f}"] for L in levels}, "others": others}


# --- commands: step 0 -------------------------------------------------------------------------------------

def cmd_inject(args):
    require_real(args)
    root = out_root(args)
    meta, secs = Meta(), build_sections()
    chosen = (list(DEV_DIS)[:args.limit or None] if args.dev else clean_injection_dis(meta, secs, args.limit or INJECT_N))
    print(f"injection check: {len(chosen)} clean Cambridge sessions (seed {INJECT_SEED})", flush=True)
    rows = []
    for k, di in enumerate(chosen):
        t = time.time()
        r = inject_di(meta, di)
        rows.append(r)
        fp = [f"{o[:20]} {v:.1f}" for o, v in r["others"].items() if v is not None and v >= TAKE_DB]
        print(f"  {k + 1}/{len(chosen)} {di[-50:]} -> {r['track']}: base {r['base']}, "
              + ", ".join(f"{L:+.0f}: {v if v is None else round(v, 1)}" for L, v in r["inj"].items())
              + f"; others at or above {TAKE_DB:.0f} dB: {fp} ({time.time() - t:.0f} s)", flush=True)
    verdict, shares, base, fp = injection_verdict(rows)
    rec = {"plan": PLAN, "step": "0a", "smoke": bool(args.smoke), "verdict": verdict,
           "shares": {str(k): v for k, v in shares.items()}, "base_share": base, "false_positive_share": fp,
           "rule": {"levels": INJECT_DB, "tol_db": INJECT_TOL_DB, "detect_db": INJECT_DETECT_DB,
                    "base_db": INJECT_BASE_DB, "need": INJECT_NEED, "base_need": INJECT_BASE_NEED,
                    "fp_max": INJECT_FP_MAX, "take_db": TAKE_DB},
           "rows": [{**r, "inj": {str(k): v for k, v in r["inj"].items()}} for r in rows],
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "injection.json", rec)
    print(f"INJECTION {verdict}: read-back shares {shares}; uninjected under {INJECT_BASE_DB:.0f} dB {base:.2f}; "
          f"false positives (other non-guitar tracks at or above {TAKE_DB:.0f} dB) {fp:.3f}", flush=True)


def scan_rows_path(root, k, n):
    return root / "scan" / f"rows-{k}of{n}.jsonl"


def scan_rows(root):
    out = {}
    for f in sorted((root / "scan").glob("rows-*.jsonl")):
        for r in read_jsonl(f):
            out[r["section"]] = r
    return out


def cmd_scan(args):
    require_real(args)
    root = out_root(args)
    inj = _load(root / "injection.json")
    if not inj or inj.get("verdict") != "OK" or (inj.get("smoke") and not args.smoke):
        if not args.smoke:
            raise SystemExit("scan needs a real INJECTION OK (run inject first)")
        print("smoke: scanning without a real INJECTION OK", flush=True)
    meta, secs = Meta(), build_sections()
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
    with open(rp, "a") as fh:
        for m, di in enumerate(todo):
            if PS_free_gb() < DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: below {DISK_GUARD_GB:.0f} GB")
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


def PS_free_gb():
    from learn import pretrain_set as PS

    return PS.free_gb()


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


def rin_rows(ctx, trusted):
    """R_in's untrusted examples (part C rows), in section order."""
    bad = set(trusted["untrusted"])
    return sorted((r for r in ctx.parts["vsep"] if not ctx.tag[r["i"]] and r["i"] in bad),
                  key=lambda r: (r["section"], r["i"]))


def cmd_rin_rebuild(args):
    import gc

    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_aug as SA

    require_real(args)
    root = out_root(args)
    trusted = _load(root / "trusted.json")
    if not trusted or (trusted.get("smoke") and not args.smoke):
        raise SystemExit("rin-rebuild needs step 0's trusted.json (run lists first)")
    free = PS.free_gb()
    if free < DISK_GUARD_GB:
        raise SystemExit(f"free disk {free:.1f} GB, below the {DISK_GUARD_GB:.0f} GB guard")
    ctx = DS.Ctx(quiet=True)
    todo_all = rin_rows(ctx, trusted)
    ctx.rows = None                                       # part C's rows (about 1.4 GB): not needed past here
    gc.collect()
    rr = rin_root(root)
    rp = rr / "rows.jsonl"
    done = {r["i"] for r in read_jsonl(rp)}
    todo = [r for r in todo_all if r["i"] not in done][:args.limit or None]
    gd = DS.ROOT / "gate"
    truth = G.gate_rows(gd, "truth")
    print(f"rin-rebuild: {len(todo_all)} untrusted R_in examples, {len(todo)} to do; X-LANCE on {args.device}", flush=True)
    if not todo:
        print("RIN-REBUILD DONE", flush=True)
        return
    sep = DS.stem_separator(STEP_SEP, args.device)
    swap0 = DS.swap_mb()
    rp.parent.mkdir(parents=True, exist_ok=True)
    refused = 0
    t_start = time.time()
    with open(rp, "a") as fh:
        for m, r in enumerate(todo):
            g = DS._guards("rin", DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            i, sid = r["i"], r["section"]
            row = {"i": i, "section": sid, "band": r["band"]}
            tr = truth.get(i)
            if tr is None or tr.get("refused"):
                row["refused"] = "no stored truth render"
            else:
                y = G.read_flac(G.truth_path(gd, i), tr["scale"], tr["sha256"])
                meta = json.loads(PS.backing_path(sid).with_suffix(".json").read_text())
                ratio, v, leak, target = PS.mix_params(i, ctx.ratios, meta["has_vocals"], ctx.eval_mix, 0)
                kind = "v" if v else "n"
                b, meta = ctx.backing(sid, kind)
                gb, gl, ga = PS.mix_gains_db(r["lufs"], meta[f"lufs_{kind}"], ratio, leak, target)
                if max(abs(p - q) for p, q in zip((gb, gl, ga), r["mix"]["gains_db"])) > 1e-6:
                    raise SystemExit(f"{i}: the V_sep mix draw differs from part C's val mix")
                stored = np.load(DS.ex_path(DS.ROOT, i, "mix"))
                mastered, mrng = DS.master_draw(i)
                orig = assemble(y, b, gb, ga)
                orig = SA.compress(orig, mrng) if mastered else orig
                mels, lu, _ = DS.half_features(orig)
                ok, share, dl = parity(mels, lu, stored)
                row.update(orig_share=share, orig_lufs_diff=dl)
                sec_rm = trusted["sections"][sid]["removed"]
                gone = [t for t in sec_rm if t in (meta["tracks"][kind])]
                row["removed"] = gone
                if not ok:
                    row["refused"] = "the original re-mix differs from the stored mix"
                elif not gone:
                    row["refused"] = "no removed track in this example's backing"
                else:
                    sec = ctx.sections[sid]
                    sess = pathlib.Path(ctx.inv[sec["di"]]["session_dir"])
                    nb = np.asarray(b, np.float64).copy()
                    for t in gone:
                        nb -= PS.section_audio(sess / t, sec["start_s"])[int(PS.TRIM_S * PS.SR):]
                    lb_new = SA.lufs(nb)
                    gb_new = rebuilt_gain_db(gb, meta[f"lufs_{kind}"], lb_new, r["lufs"])
                    _, mrng2 = DS.master_draw(i)
                    mix = assemble(y, nb, gb_new, ga)
                    mix = SA.compress(mix, mrng2) if mastered else mix
                    t0 = time.time()
                    s = np.asarray(sep(mix), np.float64)
                    if len(s) != len(mix) or not np.isfinite(s).all():
                        raise SystemExit(f"{i}: bad stem")
                    mm, ml, _ = DS.half_features(mix)
                    sm, sl, floor = DS.half_features(s)
                    DS._save_npz(DS.ex_path(rr, i, "mix"), mA=mm["A"], mB=mm["B"], lufs=[ml["A"], ml["B"]],
                                 gain_db=ga, mastered=mastered)
                    DS._save_npz(DS.ex_path(rr, i, STEP_SEP), sA=sm["A"], sB=sm["B"], lufs=[sl["A"], sl["B"]])
                    row.update(kind=kind, lufs_backing_old=meta[f"lufs_{kind}"], lufs_backing_new=lb_new,
                               gain_backing_db=[gb, gb_new], mastered=mastered, lufs_mA=ml["A"], lufs_mB=ml["B"],
                               lufs_sA=sl["A"], lufs_sB=sl["B"], floor_share=floor, sep=STEP_SEP,
                               device=args.device, sep_seconds=round(time.time() - t0, 2))
            refused += bool(row.get("refused"))
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if m % 25 == 0:
                print(f"rin {m + 1}/{len(todo)} i={i} refused {refused}; "
                      f"{(time.time() - t_start) / (m + 1):.1f} s each", flush=True)
    print(f"RIN-REBUILD DONE ({len(todo)} this run, refused {refused})", flush=True)


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
    rr = rin_root(root)
    trusted = _load(root / "trusted.json")
    if not trusted or (trusted.get("smoke") and not args.smoke):
        raise SystemExit("rin-read needs step 0's trusted.json")
    tried = {r["i"]: r for r in read_jsonl(rr / "rows.jsonl")}
    rebuilt = {i: r for i, r in tried.items() if not r.get("refused")}
    refused = sorted(i for i, r in tried.items() if r.get("refused"))
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
    r_in = [r for r in ctx.parts["vsep"] if not ctx.tag[r["i"]]]
    bad = set(trusted["untrusted"])
    if not args.smoke:
        missing = sorted(i for i in bad if i in {r["i"] for r in r_in} and i not in tried)
        if missing:
            raise SystemExit(f"{len(missing)} untrusted R_in examples are not rebuilt yet (run rin-rebuild)")
    if refused:
        print(f"note: {len(refused)} untrusted R_in examples were refused by the rebuild and leave the trusted set",
              flush=True)
    band_of = {r["i"]: r["band"] for r in r_in}
    section_of = {r["i"]: r["section"] for r in r_in}
    cell_of = {r["i"]: (r["amp"], r["base"]) for r in r_in}
    const = DS.const_errors(r_in, med, DS.encode_audible)
    reb_rows = [r for r in r_in if r["i"] in rebuilt]
    res = {}
    for tag, k in (("3 seeds", len(nets)), ("2 seeds (20261042, 20261043)", 2)):
        per = {}
        for name, rows, broot in (("original", r_in, DS.ROOT), ("rebuilt", reb_rows, rr)):
            if not rows:
                per[name] = {}
                continue
            outs, who, Y = DS.run_rows(nets[:k], rows, lambda x, b=broot: DS.readout_tensors(b, x, STEP_SEP, D))
            sc = DS.score_all(outs, who, DS.silent_masks(Y), cell_of, med, table)[0]
            per[name] = DS.readout_per(sc)["A1+A2+A3"]
        orig, reb = per["original"], per["rebuilt"]
        untouched = {i for i in orig if i not in bad}
        trusted_set = {**{i: e for i, e in orig.items() if i in untouched}, **reb}
        res[tag] = {
            "rebuilt - original (paired, rebuilt examples)": DS.paired(reb, orig, band_of, set(reb)),
            "rebuilt - original, section-clustered (descriptive)": section_interval(reb, orig, section_of, set(reb)),
            "F - constant, untouched trusted R_in (co-primary)": DS.paired(orig, const, band_of, untouched),
            "F - constant, trusted R_in (untouched + rebuilt)": DS.paired(trusted_set, const, band_of, set(trusted_set)),
            "F - constant, rebuilt examples (rebuilt stems)": DS.paired(reb, const, band_of, set(reb)),
            "F - constant, rebuilt examples (original stems)": DS.paired(orig, const, band_of, set(reb)),
            "F - constant, untrusted examples as stored": DS.paired(orig, const, band_of, bad & set(orig)),
            "F - constant, R_in as stored (step 3)": DS.paired(orig, const, band_of, set(orig)),
            "per band, rebuilt - original": {b: float(np.mean([reb[i] - orig[i] for i in reb if band_of[i] == b]))
                                             for b in sorted({band_of[i] for i in reb})},
            "examples": {"r_in": len(orig), "untouched": len(untouched), "rebuilt": len(reb),
                         "untrusted": len(bad & set(orig)), "refused": len(refused)}}
    out = {"plan": PLAN, "step": "1b", "smoke": bool(args.smoke), "decides": "nothing (descriptive)",
           "readout": "amendment 5: A1+A2+A3, masked E; step 3's stored constant and D pull",
           "models": ro["models"]["D"], "results": res, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "rin-read.json", out)

    def f(v):
        return "n/a" if v is None else f"{v[0]:+.4f} [{v[1]:+.4f}, {v[2]:+.4f}] ({v[3]} clusters)"

    for tag, rs in res.items():
        print(f"[{tag}] {rs['examples']}")
        for k2, v in rs.items():
            if k2 not in ("examples", "per band, rebuilt - original"):
                print(f"  {k2:55s} {f(v)}")
        print(f"  per band, rebuilt - original: { {b: round(v, 4) for b, v in rs['per band, rebuilt - original'].items()} }")


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
    p = sub.add_parser("rin-rebuild", help="1a: untrusted R_in examples re-mixed without their tracks, X-LANCE")
    common(p)
    p.add_argument("--device", choices=("mps", "cpu"), default="mps")
    p.set_defaults(fn=cmd_rin_rebuild)
    p = sub.add_parser("rin-read", help="1b: F on the original against the rebuilt stems (paired, zero renders)")
    common(p)
    p.set_defaults(fn=cmd_rin_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
