"""A cleaned raw-guitar (DI) library (`docs/clean-di-library-plan.md`, part A). Zero renders.

    .venv/bin/python -m learn.clean_di inventory        # every development DI we may use, with exclusions
    .venv/bin/python -m learn.clean_di screen           # per DI and per 10-s section: the declared screens
    .venv/bin/python -m learn.clean_di manifest         # the clean sections, tagged
    .venv/bin/python -m learn.clean_di hum-fix          # the hum notch's effect on the guitar (measured)
    .venv/bin/python -m learn.clean_di hum-amend        # amendment 3: re-measure the rest-refuted DIs' hum
    .venv/bin/python -m learn.clean_di listen-hum build # second blind page: the amended hum rule
    .venv/bin/python -m learn.clean_di listen build     # blind listening page (flagged vs passed sections)
    .venv/bin/python -m learn.clean_di listen score --answers "1ok 2hum 3noise+hum ..."

Outputs go to ~/ndsp-presets/learn/clean-di/ and ~/ndsp-presets/listening/di-clean-1/ (key under
private/). Run the screen with `nice -n 19` and OMP/BLAS at 2 threads beside other jobs.

The library is the DI tracks of development sessions only. Held-out material is refused by
`learn.set3.is_held_out` (sets 1-3, Guitar-TECHS P1) and `learn.set4/5/6.covers`; a path neither
knows is refused unless it is one of the declared undeclared-downloads below, whose band is checked
against every held-out list. Part B's known-answer DIs (`KNOWN_ANSWER`) are in the inventory with
split "known_answer" and are refused by `assert_training_ok`.

Sections reuse the multi-section grid and activity rule (`learn/multi_section.py`, step 1): 10-s
windows every 5 s at 48 kHz, a frame plays when within 40 dB of the DI's loudest frame, a section
counts when 80% of its frames and 60% of each judge half's play. Those pure functions are copied
here (multi_section is not on main yet); `tests/test_clean_di.py` checks they agree when it is.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import re
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
REFS = HOME / "references"
OUT = HOME / "learn/clean-di"
LISTEN = HOME / "listening/di-clean-1"
SR = 48000

# --- sections (copied from learn/multi_section.py step 1; parity-tested) -------------------------
SEC_S = 10.0
HOP_S = 5.0
FRAME, FHOP = 2048, 1024
PLAY_DB = 40.0
MIN_ACTIVE = 0.80
MIN_ACTIVE_HALF = 0.60
HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}

# --- the screens' declared thresholds (docs/clean-di-library-plan.md, "Screens") ----------------
MAINS = (50.0, 60.0)
CLIP_RUN = 3                     # >= 3 consecutive samples at >= 0.999 of the file's peak (set 3's rule) ...
FLAT_TOL = 1e-6                  # ... and flat: consecutive samples equal within 1e-6 (review item 9)
NEAR_FS = 0.989                  # a file peak within ~0.1 dB of full scale
SUBFS_CLIP_RUNS = 3              # below full scale, flat tops count only from 3 runs in a section
DC_TAG_DB = -30.0                # |mean| re the section's RMS: tag (fixable: removed by a 5-Hz high-pass)
DROP_MIN_S = 0.001               # a dropout: >= 1 ms of exact digital zero ...
DROP_CTX_S = 0.010               # ... with both 10-ms neighbours within 30 dB of the playing level
DROP_CTX_DB = 30.0
DROP_MAX_S = 0.2                 # longer zero runs are edits: their loud ends are tagged "hard_cut"
BLEED_SR = 16000                 # bleed: coherence on the DI's rest frames, 16 kHz, nfft 1024
BLEED_NFFT = 1024
BLEED_BAND = (100.0, 6000.0)
BLEED_MSC = 0.05                 # mean coherence above the 1/N bias: the track is a bleed source
BLEED_FLAG_DB = -40.0            # predicted bleed re the DI in the section: flag
MIN_REST_FRAMES = 50             # bleed is read on frames where the DI rests and the other track plays
OTHER_ACTIVE_DB = 30.0           # ... (within 30 dB of its loudest frame); fewer than 50 such frames: unmeasured
ONSET_SPARSE, ONSET_DENSE = 2.0, 5.0   # onsets per second: sparse below, dense above


# --- pure functions: sections ---------------------------------------------------------------------

def frame_db(x, frame=FRAME, hop=FHOP):
    import numpy as np

    x = np.asarray(x, np.float64)
    if len(x) < frame:
        x = np.pad(x, (0, frame - len(x)))
    n = 1 + (len(x) - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(n)[:, None]
    return 10 * np.log10(np.mean(x[idx] ** 2, axis=1) + 1e-30)


def playing(di_db, play_db=PLAY_DB):
    import numpy as np

    if di_db.max() < -200.0:
        return np.zeros(len(di_db), bool)
    return di_db >= di_db.max() - play_db


def frames_in(start, end, n_frames, frame=FRAME, hop=FHOP):
    lo = -(-start // hop)
    hi = (end - frame) // hop + 1
    return range(max(0, lo), min(n_frames, hi))


def grid(n_samples, sec_s=SEC_S, hop_s=HOP_S, sr=SR):
    L, h = int(sec_s * sr), int(hop_s * sr)
    return list(range(0, n_samples - L + 1, h))


def section_activity(play, start, sr=SR, sec_s=SEC_S):
    import numpy as np

    L = int(sec_s * sr)
    whole = frames_in(start, start + L, len(play))
    out = {}
    for h, (a, b) in HALVES.items():
        r = frames_in(start + int(a * sr), start + int(b * sr), len(play))
        out[h] = float(np.mean(play[r.start:r.stop])) if len(r) else 0.0
    return (float(np.mean(play[whole.start:whole.stop])) if len(whole) else 0.0), out


def passes(share, halves, min_active=MIN_ACTIVE, min_half=MIN_ACTIVE_HALF):
    return share >= min_active and all(v >= min_half for v in halves.values())


def disjoint(starts, sec_s=SEC_S, sr=SR):
    out, end = [], -1
    for s in sorted(starts):
        if s >= end:
            out.append(s)
            end = s + int(sec_s * sr)
    return out


# --- pure functions: screens ----------------------------------------------------------------------

def db(p):
    return 10 * math.log10(max(float(p), 1e-30))


def play_level_db(fdb, play):
    """The playing level: the median dB of the frames that play (mean-square per frame)."""
    import numpy as np

    return float(np.median(fdb[play])) if play.any() else -300.0


def power_spectrum(x, nfft, hop=None):
    """(freqs, frames x bins) power per bin of Hann frames, scaled so a frame's bins sum to its
    windowed mean square (Parseval with the window's power)."""
    import numpy as np

    x = np.asarray(x, np.float64)
    hop = hop or nfft // 2
    if len(x) < nfft:
        x = np.pad(x, (0, nfft - len(x)))
    n = 1 + (len(x) - nfft) // hop
    w = np.hanning(nfft)
    idx = np.arange(nfft)[None, :] + hop * np.arange(n)[:, None]
    X = np.fft.rfft(x[idx] * w, axis=1)
    P = np.abs(X) ** 2
    P[:, 1:-1] *= 2
    P /= nfft * np.sum(w ** 2)
    return np.fft.rfftfreq(nfft, 1 / SR), P


def line_at(f, spec, fk, ctx=20.0, peak_bw=6.0):
    """(power, prominence dB) of a stationary line at `fk` in a (percentile) spectrum: the bins
    within one bin width of fk (the two bins a line between bins falls into) less the local median
    (bins within `ctx` Hz, outside three bin widths), clipped at 0. When the strongest bin within
    `peak_bw` Hz is more than one bin from fk (the skirt of a nearby note, not a line), (0, 0)."""
    import numpy as np

    w = float(f[1] - f[0])
    on = np.abs(f - fk) <= w
    near = (np.abs(f - fk) <= ctx) & ~(np.abs(f - fk) <= 3 * w)
    wide = np.flatnonzero(np.abs(f - fk) <= max(peak_bw, 2 * w))
    if not on.any() or not near.any() or abs(f[wide[np.argmax(spec[wide])]] - fk) > w:
        return 0.0, 0.0
    med = float(np.median(spec[near]))
    return float(np.sum(np.maximum(spec[on] - med, 0.0))), round(db(spec[on].max()) - db(med), 2)


def lines(f, spec, f0, harmonics=8):
    """(total line power, [prominence dB per harmonic k = 1..harmonics]) at k*f0."""
    out = [line_at(f, spec, k * f0) for k in range(1, harmonics + 1)]
    return sum(p for p, _ in out), [q for _, q in out]

def clip_runs(x, peak=None, run=CLIP_RUN, flat=FLAT_TOL):
    """Start indices of flat tops: runs of >= `run` consecutive samples with |x| >= 0.999 * peak
    (the file's peak unless given; set 3's catalogue rule) that are also flat: each step between
    them within `flat` (a smooth unclipped peak stays near its top for several samples but moves)."""
    import numpy as np

    x = np.asarray(x, np.float64)
    peak = float(np.max(np.abs(x))) if peak is None else peak
    if peak <= 0 or len(x) < 2:
        return np.zeros(0, int)
    at = np.abs(x) >= 0.999 * peak
    pair = at[:-1] & at[1:] & (np.abs(np.diff(x)) <= flat)
    d = np.diff(np.concatenate([[0], pair.astype(np.int8), [0]]))
    s, e = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return s[(e - s) >= run - 1]


def zero_runs(x, sr, min_s=DROP_MIN_S):
    """(start, end) of runs of exact digital zero at least `min_s` long."""
    import numpy as np

    z = np.asarray(x) == 0
    d = np.diff(np.concatenate([[0], z.astype(np.int8), [0]]))
    s, e = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    keep = (e - s) >= int(min_s * sr)
    return list(zip(s[keep].tolist(), e[keep].tolist()))


def dropouts(x, sr, play_db, ctx_s=DROP_CTX_S, ctx_db=DROP_CTX_DB, max_s=DROP_MAX_S):
    """(dropouts, hard cuts): zero runs with loud signal on both sides (both 10-ms neighbours within
    `ctx_db` of the playing level). Up to `max_s` long: a dropout inside playing; longer: an edit
    whose ends are hard cuts (tagged, not flagged). Each as (start, end) native samples."""
    import numpy as np

    x = np.asarray(x, np.float64)
    c = int(ctx_s * sr)
    drops, cuts = [], []
    for s, e in zero_runs(x, sr):
        a = db(np.mean(x[s - c:s] ** 2)) if s - c >= 0 else -300.0
        b = db(np.mean(x[e:e + c] ** 2)) if e + c <= len(x) else -300.0
        loud_a, loud_b = a >= play_db - ctx_db, b >= play_db - ctx_db
        if loud_a and loud_b and (e - s) <= max_s * sr:
            drops.append((s, e))
        elif loud_a or loud_b:
            cuts.append((s, e))
    return drops, cuts


def onset_rate(x, sr=SR, nfft=2048, hop=512):
    """Onsets per second: peaks of half-wave-rectified log-spectral flux above its median by 1.5x
    the median absolute deviation, at least 50 ms apart."""
    import numpy as np

    f, P = power_spectrum(x, nfft, hop)
    L = np.log10(P + 1e-12)
    flux = np.maximum(np.diff(L, axis=0), 0).sum(1)
    if len(flux) < 3:
        return 0.0
    med = np.median(flux)
    mad = np.median(np.abs(flux - med)) + 1e-12
    thr = med + 1.5 * 1.4826 * mad * 3
    gap = max(1, int(0.05 * sr / hop))
    peaks, last = 0, -gap
    for i in range(1, len(flux) - 1):
        if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1] and i - last >= gap:
            peaks += 1
            last = i
    return peaks / (len(x) / sr)


def centroid_hz(x, play_mask=None, nfft=2048, hop=1024):
    import numpy as np

    f, P = power_spectrum(x, nfft, hop)
    if play_mask is not None:
        P = P[np.asarray(play_mask[:len(P)], bool)]
    if not len(P):
        return None
    c = (P * f).sum(1) / (P.sum(1) + 1e-30)
    return float(np.median(c))


def style(onsets_per_s):
    if onsets_per_s < ONSET_SPARSE:
        return "sparse"
    return "dense" if onsets_per_s > ONSET_DENSE else "medium"


def section_flags(row, track):
    """The declared screens applied to one measured section row (and its track): (flags, tags).
    Flags exclude the section; tags describe it."""
    flags, tags = [], []
    h = row.get("hum_rel_db")
    if h is not None:
        if h >= HUM_FLAG_DB:
            flags.append("hum")
        elif h >= HUM_TAG_DB:
            tags.append("slight_hum")
    n = row.get("hiss_rel_db")
    if n is not None:
        if n >= HISS_FLAG_DB:
            flags.append("hiss")
        elif n >= HISS_TAG_DB:
            tags.append("slight_hiss")
    if row.get("clip_runs", 0) >= (1 if track.get("near_fs") else SUBFS_CLIP_RUNS):
        flags.append("clipping")
    if row.get("dropouts", 0) >= 1:
        flags.append("dropout")
    if row.get("hard_cuts", 0) >= 1:
        tags.append("hard_cut")
    if row.get("dc_rel_db") is not None and row["dc_rel_db"] >= DC_TAG_DB:
        tags.append("dc")                          # fixable: removed by the 5-Hz high-pass
    if row.get("bleed_rel_db") is not None and row["bleed_rel_db"] >= BLEED_FLAG_DB:
        flags.append("bleed")
    if row.get("bleed_status") in ("unmeasured", "no_rest_frames", "partial"):
        tags.append("bleed_unread" if row["bleed_status"] != "partial" else "bleed_partly_read")
    if "hum" in flags and track.get("hum_rest_check") == "unconfirmed":
        tags.append("hum_unconfirmed_on_rests")
    if "hum" in flags and track.get("hum_rest_check") == "kept_fundamental":
        tags.append("hum_kept_by_fundamental")  # the rest check refuted it; amendment 3 keeps it
    r = track.get("rest_hiss_2_6k_rel_db")
    if r is not None and r >= REST_HISS_TAG_DB:
        tags.append("rest_hiss")
    return flags, tags

# --- the hum screen and fix (stationary lines) --------------------------------------------------

HUM_NFFT, HUM_HOP = 16384, 4096
HUM_QUANTILE = 10                # a line must persist: the 10th percentile of each bin over frames
LINE_PROM_DB = 10.0              # a track's hum harmonic: >= 10 dB above its neighbours (track-wide)
HUM_MAX_K = 40                   # lines up to about 2-2.4 kHz: the buzz heard after an amp and cab
LOW_K = 4                        # a hum must show one of its first 4 harmonics on the DI's rest frames
MIN_REST_SPEC = 8                # ... read when it has at least 8 rest frames (16384-point); else "unconfirmed"
REST_HISS_BAND = (2000.0, 6000.0)   # track-level hiss on rest frames, inside a guitar cab's band
REST_HISS_TAG_DB = -60.0
MIN_LINES = 2                    # hum needs at least two harmonic lines
HISS_BAND = (6000.0, 16000.0)    # the floor is read where a DI's guitar is weak
HUM_FLAG_DB = -55.0              # the track's hum lines in the section's floor, re playing level: flag
HUM_TAG_DB = -70.0               # ... tag "slight hum"
HISS_FLAG_DB = -65.0             # hiss (6-16 kHz floor) re playing level: flag
HISS_TAG_DB = -75.0
NOTCH_BW_HZ = 1.0
FIX_SEED = 20261019
FIX_MAX_BAND_DB = 0.1            # the fix "does not alter the guitar": on hum-free DIs no third-octave band
FIX_BAND_LO = 80.0               # from 80 Hz moves more than it moves on pink noise, plus this (amendment 2)
F0_NFFT = 2 ** 16                # amendment 3: the mains fundamental's frequency, read on a 0.73-Hz floor spectrum
F0_SEARCH_HZ = 3.0               # ... its peak within 3 Hz of the mains (the neighbours: 3-20 Hz away)
F0_TOL_HZ = 0.3                  # ... at the mains when within 0.3 Hz (grid held within +-0.2 Hz, plus the estimate)
HUM_AMENDMENT = 3                # screen files measured under amendment 3's hum rule carry this


def floor_spectrum(x, nfft=HUM_NFFT, hop=HUM_HOP, q=HUM_QUANTILE):
    """(freqs, per-bin q-th percentile of power over the non-silent frames), or (freqs, None)."""
    import numpy as np

    f, P = power_spectrum(x, nfft, hop)
    ok = P.sum(1) > 1e-14
    if ok.sum() < 3:
        return f, None
    return f, np.percentile(P[ok], q, axis=0)


def hum_lines(f, spec, mains, prom_db=LINE_PROM_DB, kmax=HUM_MAX_K, min_lines=MIN_LINES):
    """The DI's hum harmonics at the session's `mains`: [k whose line stands >= prom_db above its
    neighbours], or [] when fewer than `min_lines` do (one persistent line can be a held note)."""
    _, prom = lines(f, spec, mains, harmonics=kmax)
    ks = [k for k, p in enumerate(prom, 1) if p >= prom_db]
    return ks if len(ks) >= min_lines else []


def line_count(f, spec, mains, prom_db=LINE_PROM_DB, kmax=HUM_MAX_K):
    """(lines at >= prom_db, their total power) at `mains`: the session's vote for its mains."""
    tot, prom = lines(f, spec, mains, harmonics=kmax)
    return sum(p >= prom_db for p in prom), tot


def session_mains(votes):
    """The session's mains from its DIs' votes {mains: [(count, power)]}: more lines, then more power."""
    return max(MAINS, key=lambda m: (sum(c for c, _ in votes.get(m, [])), sum(p for _, p in votes.get(m, []))))


def rest_spectrum(x, nfft=HUM_NFFT, hop=HUM_HOP, below=PLAY_DB):
    """(freqs, mean power spectrum of the frames more than `below` dB under the loudest and above
    digital silence, number of such frames)."""
    import numpy as np

    f, P = power_spectrum(x, nfft, hop)
    e = 10 * np.log10(P.sum(1) + 1e-30)
    rest = (e < e.max() - below) & (e > e.max() - 120)
    return f, (P[rest].mean(0) if rest.any() else None), int(rest.sum())


def rest_confirms(f, rest_spec, mains, n_rest, prom_db=LINE_PROM_DB, low_k=LOW_K, min_rest=MIN_REST_SPEC):
    """'yes' when one of the first `low_k` harmonics stands out on the rest frames, 'no' when none
    does, 'unconfirmed' when there are too few rest frames to tell."""
    if rest_spec is None or n_rest < min_rest:
        return "unconfirmed"
    return "yes" if any(line_at(f, rest_spec, k * mains)[1] >= prom_db for k in range(1, low_k + 1)) else "no"


def mains_line_hz(x, mains, nfft=F0_NFFT, search=F0_SEARCH_HZ, q=HUM_QUANTILE):
    """(frequency, prominence dB) of the persistent line nearest the mains fundamental: the peak
    within `search` Hz of `mains` in the q-th percentile spectrum of `nfft`-point frames (hop
    nfft/4), parabolically interpolated, against the median of the bins `search`-20 Hz away; or
    (None, None). Guitar notes come and go, so the percentile keeps the steady line (amendment 3)."""
    import numpy as np

    f, P = power_spectrum(x, nfft, nfft // 4)
    ok = P.sum(1) > 1e-14
    if ok.sum() < 3:
        return None, None
    s = np.percentile(P[ok], q, axis=0)
    w = float(f[1] - f[0])
    idx = np.flatnonzero(np.abs(f - mains) <= search)
    i = int(idx[np.argmax(s[idx])])
    a, b, c = (np.log(s[j] + 1e-30) for j in (i - 1, i, i + 1))
    den = a - 2 * b + c
    d = 0.5 * (a - c) / den if den != 0 else 0.0
    near = (np.abs(f - mains) <= 20.0) & (np.abs(f - mains) > search)
    return round(float(f[i] + d * w), 3), round(db(s[i]) - db(float(np.median(s[near]))), 2)


def fundamental_overrides(ks, line_hz, mains, tol=F0_TOL_HZ):
    """Amendment 3: the rest check may not refute a DI's lines when the mains fundamental itself is
    one of them (k = 1 passes the track's own line test) and that line sits at the mains frequency
    (within `tol` Hz). In any tuning near A = 440 Hz no equal-tempered note lies within 2% of 50 or
    60 Hz, so a steady line there is mains hum, whatever the rest frames show."""
    return 1 in ks and line_hz is not None and abs(line_hz - mains) <= tol


def line_power(f, spec, mains, ks):
    """Power of the lines k*mains (k in ks), as `line_at`."""
    return sum(line_at(f, spec, k * mains)[0] for k in ks)

def band_power_sum(f, spec, lo, hi):
    from scipy.ndimage import median_filter

    sm = median_filter(spec, size=25, mode="nearest")
    m = (f >= lo) & (f <= hi)
    return float(sm[m].sum())


def mains_f0(x, mains, ks, nfft=2 ** 18):
    """The mains frequency to 0.01 Hz: per harmonic the peak of the long-window mean spectrum within
    1 Hz of k*mains (parabolic interpolation), f0 = the power-weighted mean of peak/k."""
    import numpy as np

    f, P = power_spectrum(x, nfft, nfft // 2)
    s = P.mean(0)
    est, w = [], []
    for k in ks:
        m = np.flatnonzero(np.abs(f - k * mains) <= 1.0)
        if len(m) < 3:
            continue
        i = m[np.argmax(s[m])]
        if 0 < i < len(s) - 1:
            a, b, c = np.log(s[i - 1] + 1e-30), np.log(s[i] + 1e-30), np.log(s[i + 1] + 1e-30)
            den = a - 2 * b + c
            d = 0.5 * (a - c) / den if den != 0 else 0.0
            est.append((f[i] + d * (f[1] - f[0])) / k)
            w.append(s[i])
    return float(np.average(est, weights=w)) if est else mains


def notch(x, f0, ks, bw=NOTCH_BW_HZ, sr=SR):
    """Zero-phase notches (1-Hz wide) at k*f0, k in ks."""
    import numpy as np
    from scipy import signal

    y = np.asarray(x, np.float64)
    for k in ks:
        b, a = signal.iirnotch(k * f0, k * f0 / bw, fs=sr)
        y = signal.filtfilt(b, a, y, padlen=min(len(y) - 1, 3 * sr))
    return y


def third_octave_db(x, mask=None, lo=40.0, hi=8000.0):
    """Per third-octave band (40 Hz - 8 kHz) mean power in dB over the frames in `mask`."""
    import numpy as np

    f, P = power_spectrum(x, 4096, 2048)
    if mask is not None:
        P = P[np.asarray(mask[:len(P)], bool)]
    s = P.mean(0)
    k = np.arange(math.floor(3 * math.log2(lo / 1000)), math.ceil(3 * math.log2(hi / 1000)) + 1)
    out = []
    for fc in 1000.0 * 2.0 ** (k / 3):
        m = (f >= fc * 2 ** (-1 / 6)) & (f < fc * 2 ** (1 / 6))
        out.append(db(s[m].sum()))
    return np.asarray(out)


def band_changes(x, f0, ks, mask=None):
    """Per third-octave band from 80 Hz, the |change| in dB the notch set makes to `x` (on `mask`)."""
    import numpy as np

    y = notch(x, f0, ks)
    return np.abs(third_octave_db(y, mask, lo=FIX_BAND_LO) - third_octave_db(x, mask, lo=FIX_BAND_LO))


def noise_reference(f0, ks, seconds=20.0, seed=FIX_SEED):
    """The same per-band change on seeded pink noise: what a notch set does to any broadband signal
    (1-Hz notches take a fixed share of the narrow low third-octave bands; amendment 2)."""
    import numpy as np

    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    w = np.fft.rfft(rng.standard_normal(n))
    fr = np.fft.rfftfreq(n, 1 / SR)
    w[1:] /= np.sqrt(fr[1:])
    w[0] = 0
    pink = np.fft.irfft(w, n)
    return band_changes(pink / np.std(pink) * 0.1, f0, ks)


def excess_collateral(control_bands, reference_bands):
    """The largest amount by which a control DI's band change exceeds the noise reference's, dB."""
    import numpy as np

    return float(np.max(np.asarray(control_bands) - np.asarray(reference_bands)))


def fix_effect(x, f0, ks, play_mask_4096=None):
    """What the notch does to `x`: (max |third-octave change| dB from 80 Hz on the frames in the
    mask (the playing frames), removed power re x's power dB (reported only: any notch removes
    its slivers of a broadband guitar spectrum, about -26 to -29 dB for 4-8 notches; amendment 1))."""
    import numpy as np

    y = notch(x, f0, ks)
    a, b = third_octave_db(x, play_mask_4096, lo=FIX_BAND_LO), third_octave_db(y, play_mask_4096, lo=FIX_BAND_LO)
    removed = db(np.mean((x - y) ** 2)) - db(np.mean(np.asarray(x) ** 2))
    return float(np.max(np.abs(b - a))), float(removed), y


# --- bleed into the DI ---------------------------------------------------------------------------

def stft16(x, nfft=BLEED_NFFT):
    import numpy as np

    hop = nfft // 2
    x = np.asarray(x, np.float64)
    if len(x) < nfft:
        x = np.pad(x, (0, nfft - len(x)))
    n = 1 + (len(x) - nfft) // hop
    idx = np.arange(nfft)[None, :] + hop * np.arange(n)[:, None]
    return np.fft.rfft(x[idx] * np.hanning(nfft), axis=1)


def bleed_bins(mains=None, nfft=BLEED_NFFT, sr=BLEED_SR, band=BLEED_BAND):
    """The bins coherence is averaged over: the band, less bins within 3 Hz of any 50/60-Hz harmonic
    (hum is common to many tracks without being bleed)."""
    import numpy as np

    f = np.fft.rfftfreq(nfft, 1 / sr)
    m = (f >= band[0]) & (f <= band[1])
    for base in MAINS:
        m &= np.abs(((f + base / 2) % base) - base / 2) > 3.0 + (f[1] - f[0]) / 2
    return m


def coherence(X, Y, rows, bins):  # noqa: D401
    """Mean magnitude-squared coherence over `bins` from the frames in `rows`, and the 1/N bias."""
    import numpy as np

    Xr, Yr = X[rows][:, bins], Y[rows][:, bins]
    sxy = np.sum(Xr * np.conj(Yr), 0)
    sxx = np.sum(np.abs(Xr) ** 2, 0)
    syy = np.sum(np.abs(Yr) ** 2, 0)
    msc = np.abs(sxy) ** 2 / (sxx * syy + 1e-30)
    return float(np.mean(msc)), 1.0 / max(int(np.sum(rows)), 1)


def bleed_rel(X, Y, rest, sections, bins):
    """Per section (frame-index slices), the bleed predicted from Y (transfer fitted on the DI's
    rest frames) re the DI's power there, dB."""
    import numpy as np

    Xr, Yr = X[rest][:, bins], Y[rest][:, bins]
    H = np.sum(Xr * np.conj(Yr), 0) / (np.sum(np.abs(Yr) ** 2, 0) + 1e-30)
    out = []
    for sl in sections:
        pb = float(np.sum(np.abs(H) ** 2 * np.abs(Y[sl][:, bins]) ** 2))
        px = float(np.sum(np.abs(X[sl][:, bins]) ** 2))
        out.append(db(pb) - db(px) if px > 0 else None)
    return out


# --- the inventory ------------------------------------------------------------------------------

SETS_1_2 = PLUGIN_ROOT / "docs/validation-datasets.json"
SET3_DECL = PLUGIN_ROOT / "docs/validation-set3.json"
SET3_ROOT = REFS / "datasets-set3"
SET3_CATALOG = SET3_ROOT / "catalog.json"
SETS_1_2_ROOT = REFS / "datasets"
LABEL_PARTS = PLUGIN_ROOT / "docs/label-table-parts.json"
GT_ROOT = SETS_1_2_ROOT / "guitar-techs"
GT_DIRS = {"Guitar-TECHS P1": GT_ROOT / "P1-downloads", "Guitar-TECHS P2": GT_ROOT / "P2-downloads"}
# Downloaded with set 3 but never declared in any set: (session dir, band, split, why).
UNDECLARED = {
    "cambridge/DarkRide_DeadEnemies_Full": ("Dark Ride", "library", "8 DIs with no amp track; never used"),
    "cambridge/TheApprehended_StillFlyin_Full": ("The Apprehended", "known_answer",
                                                 "3 DIs with no amp track; never used; part B's first song"),
}
CAMBRIDGE_NEW = REFS / "datasets-cambridge-new"
# Downloaded on 2026-10-25 as TRAINING bands (the user, 2026-10-25; ledger `cambridge-new-training-bands-2026-10-25`):
# {session dir: (band, split, why)}. Training permission only: a DI still trains once T0's checks and the ear pass it.
# Blue Manic, in the same folder, is a reserved test band and is not here.
TRAINING_DOWNLOADS = {
    "EmberRev_DivesAndLazarus_Full": ("Ember Rev", "library", "2026-10-25 training band (art rock)"),
    "EmptySignifier_Change_Full": ("Empty Signifier", "library",
                                   "2026-10-25 training band ('various styles': scope by ear)"),
    "GoranLevi_QueSeYo_Full": ("Goran Levi", "library", "2026-10-25 training band (Afro-Cuban jazz)"),
    "Mopia_IfYouThenI_Full": ("Mopia", "library", "2026-10-25 training band (jazz-metal big band: scope by ear)"),
    "Soren_ALittleLate_Full": ("Soren", "library", "2026-10-25 training band (disco-pop; DI only)"),
    # Metal and hard rock, downloaded on 2026-10-26 as TRAINING sessions (the user, 2026-10-26: high gain may train,
    # parts heard as too heavy are left out; ledger `cambridge-new-training-bands-2026-10-26`). Not V.M.GY (held out).
    "ArcadianAlone_TheDeathlessOne_Full": ("Arcadian Alone", "library", "2026-10-26 training band (symphonic metal)"),
    "DaimonB_BrokenAgain_Full": ("Daimon B", "library", "2026-10-26 training band (nu metal)"),
    "DaimonB_CryingRivers_Full": ("Daimon B", "library", "2026-10-26 training band (nu metal; no electric DI)"),
    "DarkIllusion_DarkIllusion_Full": ("Dark Illusion", "library", "2026-10-26 training band (metal)"),
    "DarkIllusion_EvilBones_Full": ("Dark Illusion", "library", "2026-10-26 training band (metal)"),
    "InhumanityVortex_Cybermod_Full": ("Inhumanity Vortex", "library", "2026-10-26 training band (death metal)"),
    "Peppermark_LuaNegra_Full": ("Peppermark", "library", "2026-10-26 training band (melodic metal)"),
    "Peppermark_AnotherFeeling_Full": ("Peppermark", "library", "2026-10-26 training band (melodic metal)"),
    "Peppermark_Interlude_Full": ("Peppermark", "library", "2026-10-26 training band (melodic metal)"),
    "Serapis_TheDarkAbyss_Full": ("Serapis", "library", "2026-10-26 training band (progressive death metal)"),
    "Serapis_MorbusAnimi_Full": ("Serapis", "library", "2026-10-26 training band (progressive death metal)"),
    "DGX_RedemptivePain_Full": ("DGX", "library", "2026-10-26 training band (hard rock/metal; DI only)"),
    "DGX_RestInHell_Full": ("DGX", "library", "2026-10-26 training band (hard rock/metal; DI only)"),
    # Part B2's parked known-answer songs, which the user allowed for training on 2026-10-23 (spending that pool);
    # downloaded on 2026-10-26 as T3's clean/crunch source for F20 (ledger `cambridge-new-training-bands-2026-10-26b`).
    # DI-only sessions: no DI has its own amp track (Timeless Part 2's ElecGtr2 and ElecGtr3 have no DI).
    "Strobe_Maya_Full": ("Strobe", "library", "2026-10-23 B2-pool training band (pop/electronica; DI only)"),
    "Mekaphil_AliveYetFree_Full": ("MekaPhil", "library", "2026-10-23 B2-pool training band (anime alt rock; DI only)"),
    "Mekaphil_Core_Full": ("MekaPhil", "library", "2026-10-23 B2-pool training band (anime alt rock; DI only)"),
    "MekaPhil_TimelessPart1_Full": ("MekaPhil", "library", "2026-10-23 B2-pool training band (anime alt rock; DI only)"),
    "Mekaphil_TimelessPart2_Full": ("MekaPhil", "library",
                                    "2026-10-23 B2-pool training band (anime alt rock; its DIs have no amp track)"),
    # Two more Strobe songs, downloaded by mistake beside 'Maya' and kept for training by the user on 2026-10-26
    # (ledger `cambridge-new-training-bands-2026-10-26c`). Taken in, no usable DI: no file in either is named as a DI,
    # and their electric guitar tracks are excluded as unconfirmed DIs (INTAKE_UNNAMED_DI).
    "Strobe_Gone_Full": ("Strobe", "library", "2026-10-26c training band (pop/electronica; no usable DI)"),
    "Strobe_Nostalgic_Full": ("Strobe", "library", "2026-10-26c training band (pop/electronica; no usable DI)"),
}
# Not an electric guitar DI although the name reads as one: acoustic-guitar DIs and MIDI renders (2026-10-26)
INTAKE_NOT_DI = re.compile(r"(?i)acoustic|midi")
# Electric guitar tracks not named as DIs (2026-10-26c): Strobe 'Gone' and 'Nostalgic' name no file as a DI. Not a
# confirmed DI, so excluded: no DI row (one ear click cannot establish an unnamed track as a DI; review of PR #303).
INTAKE_UNNAMED_DI = {
    "Strobe_Gone_Full": ("21_ElecGtr1.wav", "22_ElecGtr1DT.wav", "23_ElecGtr2.wav", "24_ElecGtr2DT.wav",
                         "25_ElecGtr3.wav", "26_ElecGtr4.wav"),
    "Strobe_Nostalgic_Full": ("07_ElecGtr.wav",),
}
INTAKE_UNNAMED_WHY = "not a confirmed DI (unnamed); excluded"
RESERVED_NEW = {"BlueManic_Acomatay_Full": "reserved test band (ledger cambridge-new-test-band-bluemanic)"}
RESERVED_BANDS = {"Blue Manic"}          # refused even if its session is ever added to TRAINING_DOWNLOADS
# Every TRAINING_DOWNLOADS row carries this note, which `training_ok` rejects: a DI trains only once a verified list
# (T0's checks and the ear) admits it.
INTAKE_PENDING = "catalogue: pending T0 intake (trains only once a verified list admits it)"
# The verified list that admits them: T0's `verified.json` (`verify_tracks lists`), its `intake_admitted` (T0's intake
# checks and the user's ear, part 6). An admitted row carries INTAKE_ADMITTED in place of INTAKE_PENDING.
TRUSTED_VERIFIED = HOME / "learn/trusted-data/t0/verified.json"
INTAKE_ADMITTED = "admitted by T0's verified list (verified.json intake_admitted: T0's checks and the ear)"
# Dunning Kruger "Sascha" (refused here as a set-3 held-out band's song until 2026-10-28) is released into training
# with its band by the clean/crunch pool plan's decision B (`learn.cc_pool.RELEASED`).
REFUSED_SESSIONS = {
    "cambridge/UmphreysMcGee_CrucialTaunt_Full": "its 'DI' is a Palmer PDI-09 speaker-simulated line-out after the "
                                                 "amp, not a raw DI (fresh-di-amp-multitracks-2026-10.md)",
}
# Part B's bands (its pilot B1's songs): never in any training set, nor in a later fresh draw.
KNOWN_ANSWER = {"The Apprehended", "Rebecca Haviland", "Chris Coltraine"}
STAGE_F = ("cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3", "cambridge-Passing_Ships-ElecGtr2",
           "cambridge-Passing_Ships-ElecGtr4", "cambridge-Quicksand-ElecGtr2", "cambridge-Signs-ElecGtr3",
           "cambridge-Today's_The_Day-ElecGtr07", "cambridge-colour-me-red-elecgtr02",
           "cambridge-colour-me-red-elecgtr03", "cambridge-femme-elecgtr5", "cambridge-get-out-of-bed-elecgtr2",
           "cambridge-let-s-dance-elecgtr3", "cambridge-let-s-dance-elecgtr4", "cambridge-magilla-elecgtr1",
           "cambridge-wickerman-elecgtr1", "cambridge-wickerman-elecgtr2", "cambridge-wickerman-elecgtr3",
           "cambridge-wickerman-elecgtr7", "telefunken-Gym_Hours-GTR_2", "telefunken-Russian_Cream-GTR_1",
           "telefunken-She's_Gone-GTR", "telefunken-Strangest_Places-GTR")
LICENCE = {
    "cambridge": "Cambridge-MT 'Mixing Secrets' library: educational use only, no commercial use (session Readme.txt)",
    "telefunken": "TELEFUNKEN Live From The Lab: home-studio and educational use only, no commercial use; "
                  "attribution: 'All audio files have been engineered and recorded by TELEFUNKEN Elektroakustik "
                  "and are presented for educational and demonstrational purposes only.'",
    "guitar-techs": "Guitar-TECHS (Zenodo 14963133), CC BY 4.0; cite Pedroza et al., ICASSP 2025",
}
DI_NAME = re.compile(r"(?i)(gtr|guitar).*\bdi|(gtr|guitar)\w*di\b|gtr\d*(dt)?di")
NOT_GUITAR = re.compile(r"(?i)bass|vox|vocal|drum|key\s*\d|keys\s*\d|direct\.wav$")


def is_guitar_di(name):
    """A file name that reads as an electric guitar's DI (not a bass DI, a drum or a keyboard)."""
    stem = pathlib.PurePosixPath(name).stem
    return bool(DI_NAME.search(stem)) and not NOT_GUITAR.search(stem)


def own_tracks(part, files, di):
    """The DI's own amp and microphone tracks: names carrying the part token (not followed by a
    digit), other than DIs."""
    pat = re.compile(re.escape(part) + r"(?!\d)", re.I)
    return sorted(f for f in files if f != di and pat.search(pathlib.PurePosixPath(f).name) and not is_guitar_di(f))


def band_of(s):
    """A set-1/2 session's band: its group or artist, else the artist in its directory name
    (Telefunken "Artist - Song", Cambridge "ArtistName_SongName_Full")."""
    if s.get("group") or s.get("artist"):
        return s.get("group") or s.get("artist")
    name = pathlib.PurePosixPath(s["path"]).name
    if " - " in name:
        band = name.split(" - ")[0].strip()
        return {"Rebecaa Haviland": "Rebecca Haviland"}.get(band, band)     # the directory's typo
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name.split("_")[0])


def slug12(source, song, part):
    return f"{source}-{song.replace(' ', '_')}-{part.replace(' ', '_')}"


def _held_out_names():
    from learn import set3

    d = set3.load()
    names = set(d["held_out_bands"])
    v = json.loads(SETS_1_2.read_text())
    names |= {band_of(s) for s in v["sessions"] if s["split"] == "held_out" and s["source"] != "guitar-techs"}
    return {n for n in names if n}


def refuse_held_out(rec):
    """Raise if a record is held out anywhere. Declared sets: set3.is_held_out (sets 1-3 and
    Guitar-TECHS P1; fails closed) and set4/5/6.covers. Guitar-TECHS P2 (development, docs/
    di-domain-pilot-plan.md) and the undeclared downloads: their band in no held-out list and their
    path under no set-4/5/6 root. A session the clean/crunch pool plan released into training
    (`learn.cc_pool.released_entry`, 2026-10-28) passes, its band as declared and never a V-real band;
    its crops and its band's unreleased material stay held out."""
    from learn import cc_pool as CC
    from learn import set3, set4, set5, set6

    p = rec["path"]
    if "P3_music" in p:
        raise ValueError(f"Guitar-TECHS P3 is never used: {p}")
    rel = CC.released_entry(p)
    if rel is not None:
        if rec.get("band") != rel["band"]:
            raise ValueError(f"released session {rel['key']}: band {rec.get('band')!r}, declared {rel['band']!r}")
        CC.refuse_pool_band(rec.get("band"))
        return
    if set4.covers(p) or set5.covers(p) or set6.covers(p):
        raise ValueError(f"set 4-6 material: {p}")
    if "P3_music" in p:
        raise ValueError(f"Guitar-TECHS P3 is never used: {p}")
    if any(k in p for k in RESERVED_NEW) or rec.get("band") in RESERVED_BANDS:
        raise ValueError(f"reserved test band: {p}")
    if rec["set"] in ("undeclared", "guitar-techs-P2", "cambridge-new"):
        band = rec["band"]
        if band in _held_out_names() or set4.covers(band) or set5.covers(band) or set6.covers(band):
            raise ValueError(f"held-out band: {band}")
        return
    if set3.is_held_out(pathlib.Path(p)):
        raise ValueError(f"held out: {p}")


def intake_admitted(path=None):
    """The TRAINING_DOWNLOADS DI ids that T0's verified list admits (a real `lists` run, not a smoke one); none when
    there is no such list."""
    p = pathlib.Path(path or TRUSTED_VERIFIED)
    if not p.exists():
        return set()
    rec = json.loads(p.read_text())
    return set() if rec.get("smoke") else set(rec.get("intake_admitted") or ())


def assert_training_ok(paths, manifest=None):
    """Refuse any DI that may not train a model: part B's known-answer DIs, set-1 DIs of a band
    with a held-out song, and anything held out. `paths`: DI paths."""
    man = manifest or json.loads((OUT / "inventory.json").read_text())
    by = {r["path"]: r for r in man["dis"]}
    for p in paths:
        r = by.get(str(p))
        if r is None:
            raise KeyError(f"not in the DI inventory: {p}")
        if r["split"] != "library" or not r["training_ok"]:
            raise ValueError(f"not for training ({r['split']}, {r['notes']}): {p}")


def inventory():
    """(dis, excluded): every development guitar DI on disk we may use, and what was left out."""
    from learn import set3

    labels = json.loads(LABEL_PARTS.read_text())
    classes = labels["classes_all"]
    dis, excluded = [], []

    def add(**r):
        r.setdefault("notes", [])
        r["licence"] = LICENCE[r["source"]]
        if r["band"] in KNOWN_ANSWER:
            r["split"] = "known_answer"
            r["notes"].append("part B known-answer song")
        r["training_ok"] = (r["split"] == "library" and "band has a held-out song" not in r["notes"]
                            and not any(n.startswith("catalogue:") for n in r["notes"]))
        if r.get("slug") in STAGE_F:
            r["notes"].append("stage F part (used once)")
        dis.append(r)

    # sets 1-2
    v = json.loads(SETS_1_2.read_text())
    split_bands = {}
    for s in v["sessions"]:
        if s["source"] != "guitar-techs":
            split_bands.setdefault(band_of(s), set()).add(s["split"])
    for s in v["sessions"]:
        if s["source"] == "guitar-techs":
            excluded.append({"what": f"guitar-techs/{s['song']}", "why": "Guitar-TECHS P3 is never used "
                             "(its excerpts share one recording with held-out excerpts)"})
            continue
        band = band_of(s)
        if s["split"] != "development":
            excluded.append({"what": s["path"], "why": f"set {s.get('set', 1)} held out"})
            continue
        sdir = SETS_1_2_ROOT / s["path"]
        files = sorted(s["files"])
        parts = {p["di"]: p for p in s["parts"] if p.get("di")}
        for f in files:
            if f not in parts and is_guitar_di(f):
                m = re.search(r"(?i)(elecgtr\d+(dt)?|gtr\s*\d*)", f)
                parts[f] = {"part": m.group(1) if m else pathlib.Path(f).stem, "unpaired": True}
        for di, p in sorted(parts.items()):
            if "keys" in di.lower():
                excluded.append({"what": f"{s['path']}/{di}", "why": "'Keys GTR' DI: the catalogue names it for "
                                 "the keyboard player; the instrument is unverified (review item 4)"})
                continue
            notes = []
            if p.get("unpaired"):
                notes.append("no amp track in the catalogue")
            elif not p.get("usable"):
                notes.append("not a same-take pair (DI kept as a DI)")
            if "held_out" in split_bands.get(band, ()):
                notes.append("band has a held-out song")
            slug = slug12(s["source"], s["song"], p["part"])
            add(id=f"{s['path']}/{di}", path=str(sdir / di), source=s["source"], set=s.get("set", 1),
                band=band, song=s["song"], part=p["part"], slug=slug if slug in classes else None,
                gain_class=classes.get(slug), genre=None, split="library", session_dir=str(sdir),
                own=[f for f in ([p.get("reference")] + list(p.get("alternate", []))) if f]
                or own_tracks(p["part"], files, di),
                mix=s.get("mix_tracks"), vocals=s.get("vocal_tracks"), notes=notes)
    # set 3
    decl = set3.load()
    cat = json.loads(SET3_CATALOG.read_text())
    cat_s = {s["key"]: s for s in cat["sessions"]}
    kept = {(p["session_key"], p["part"]): p for p in decl["parts"]}
    for s in decl["sessions"]:
        if s["split"] != "development":
            excluded.append({"what": s["key"], "why": "set 3 held out (spent; excluded from training)"})
            continue
        c = cat_s[s["key"]]
        cdir = SET3_ROOT / c["path"]
        files = sorted(c["files"])
        rows = [(p["part"], p["di"], [p["reference"]] + list(p.get("alternate", [])), False) for p in c["parts"] if p.get("di")]
        rows += [(u["part"], f"{pathlib.PurePosixPath(c['path']).name}/{u['di']}", None, True)
                 for u in cat["unpaired"] if u.get("session") == s["key"] and u.get("di")]
        for part, di, own, unpaired in rows:
            k = kept.get((s["key"], part))
            notes = ["no amp track in the catalogue"] if unpaired else ([] if k else ["part not kept (DI kept as a DI)"])
            clip = next((d["di_clip_runs"] for d in s["dis"] if d["part"] == part), None)
            if clip is not None and clip >= set3.CLIP_RUNS:
                notes.append(f"catalogue: {clip} flat-topped runs (set 3's clipped-DI rule)")
            add(id=f"{c['path']}/{di}", path=str(cdir / di), source=s["source"], set=3, band=s["band"],
                song=s["song"], part=part, slug=k["slug"] if k else None,
                gain_class=(k or {}).get("gain_class") or classes.get((k or {}).get("slug")),
                genre=c.get("genre"), split="library", session_dir=str(cdir / pathlib.PurePosixPath(di).parent),
                own=[pathlib.PurePosixPath(o).name for o in own] if own else
                own_tracks(part, [pathlib.PurePosixPath(f).name for f in files], pathlib.PurePosixPath(di).name),
                mix=[pathlib.PurePosixPath(m).name for m in c.get("mix_tracks", [])],
                vocals=[pathlib.PurePosixPath(m).name for m in c.get("vocal_tracks", [])], notes=notes)
    # downloaded, never declared
    for key, why in REFUSED_SESSIONS.items():
        excluded.append({"what": key, "why": why})
    for what in ("set 4 (references/datasets-set4)", "set 5 (references/datasets-set5)",
                 "set 6 (MedleyDB, references/datasets-medleydb)"):
        excluded.append({"what": what, "why": "held out for the ML plan's step 7; never read"})
    excluded.append({"what": "EGFxSet clean (references/datasets/egfxset)",
                     "why": "single notes, too short for 10-s sections (CC BY 4.0; used for riffs)"})
    excluded.append({"what": "ToneTwist AFx DRY (references/datasets-set3/tonetwist)",
                     "why": "CC BY-NC 4.0, calibration only by the set-3 declaration"})
    for key, (band, split, why) in UNDECLARED.items():
        inner = SET3_ROOT / key / pathlib.PurePosixPath(key).name
        files = sorted(p.name for p in inner.glob("*.wav"))
        for di in [f for f in files if is_guitar_di(f)]:
            part = re.search(r"(?i)elecgtr\d+", di).group(0)
            add(id=f"{key}/{di}", path=str(inner / di), source="cambridge", set="undeclared", band=band,
                song=pathlib.PurePosixPath(key).name, part=part, slug=None, gain_class=None, genre=None,
                split=split, session_dir=str(inner), own=own_tracks(part, files, di), mix=None, vocals=None,
                notes=[why])
    # downloaded 2026-10-25 for training (datasets-cambridge-new); the reserved test band stays out
    for key, why in RESERVED_NEW.items():
        excluded.append({"what": f"datasets-cambridge-new/{key}", "why": why})
    admitted = intake_admitted()
    for key, (band, split, why) in TRAINING_DOWNLOADS.items():
        inner = CAMBRIDGE_NEW / key
        files = sorted(p.name for p in inner.glob("*.wav"))
        for f in INTAKE_UNNAMED_DI.get(key, ()):
            if f in files:
                excluded.append({"what": f"datasets-cambridge-new/{key}/{f}", "why": INTAKE_UNNAMED_WHY})
        for di in [f for f in files if is_guitar_di(f) and not INTAKE_NOT_DI.search(f)]:
            part = re.search(r"(?i)elecgtr\d*", di).group(0)
            rid = f"cambridge-new/{key}/{di}"
            add(id=rid, path=str(inner / di), source="cambridge", set="cambridge-new",
                band=band, song=key, part=part, slug=None, gain_class=None, genre=None, split=split,
                session_dir=str(inner), own=own_tracks(part, files, di), mix=None, vocals=None,
                notes=[why, INTAKE_ADMITTED if rid in admitted else INTAKE_PENDING])
    # Guitar-TECHS P1 and P2 (development; P3 never)
    for band, root in GT_DIRS.items():
        for f in sorted(root.glob("*/audio/directinput/*.wav")):
            add(id=str(f.relative_to(SETS_1_2_ROOT)), path=str(f), source="guitar-techs",
                set="guitar-techs-" + band[-2:], band=band, song=f.parts[-4], part=f.stem, slug=None,
                gain_class=None, genre=None, split="library", session_dir=None, own=[], mix=None, vocals=None,
                notes=["solo exercise recording (no band)"])
    seen = set()
    for r in dis:
        assert r["path"] not in seen, r["path"]
        seen.add(r["path"])
        assert pathlib.Path(r["path"]).is_file(), r["path"]
        refuse_held_out(r)
        if r["band"] in KNOWN_ANSWER:
            assert r["split"] == "known_answer", r["id"]
    return dis, excluded


def cmd_inventory(_):
    import collections

    dis, excluded = inventory()
    OUT.mkdir(parents=True, exist_ok=True)
    out = {"schema": "clean-di-inventory-1", "plan": "docs/clean-di-library-plan.md", "dis": dis,
           "excluded": excluded,
           "counts": {"dis": len(dis),
                      "by_set": dict(collections.Counter(str(r["set"]) for r in dis)),
                      "by_split": dict(collections.Counter(r["split"] for r in dis)),
                      "training_ok": sum(r["training_ok"] for r in dis),
                      "bands": len({r["band"] for r in dis}),
                      "by_gain_class": dict(collections.Counter(str(r["gain_class"]) for r in dis))}}
    _atomic(OUT / "inventory.json", out)
    print(json.dumps(out["counts"], indent=1))
    for e in excluded:
        print("excluded:", e["what"], "-", e["why"])


def _atomic(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    os.replace(tmp, path)


# --- the screen (zero renders; CPU) ---------------------------------------------------------------

def load_native(path):
    import numpy as np
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    return x.mean(axis=1), sr


def resample(x, sr, to):
    import numpy as np
    from scipy.signal import resample_poly

    if sr == to:
        return np.asarray(x, np.float64)
    g = math.gcd(int(sr), int(to))
    return resample_poly(x, to // g, sr // g)


def _key(rec):
    import hashlib

    return hashlib.sha1(rec["id"].encode()).hexdigest()[:16]


SCREEN_SCHEMA = "clean-di-screen-2"     # outputs of another schema are recomputed (review item 6)


def measure_di(x, sr, mains):
    """Track-level measures and per-section rows of one DI (native samples `x` at `sr`), with the
    session's `mains`; bleed is added later by the session pass. Returns (track, rows)."""
    import numpy as np

    y = resample(x, sr, SR)
    fdb = frame_db(y)
    play = playing(fdb)
    pl = play_level_db(fdb, play)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    near_fs = peak >= NEAR_FS
    f, fs = floor_spectrum(y)
    fr, rs, n_rest = rest_spectrum(y)
    ks = hum_lines(f, fs, mains) if fs is not None else []
    confirm = rest_confirms(fr, rs, mains, n_rest) if ks else None
    line_hz = line_prom = None
    refuted = []
    if confirm == "no":                       # persistent lines but no hum where the guitar rests ...
        line_hz, line_prom = mains_line_hz(y, mains)
        if fundamental_overrides(ks, line_hz, mains):
            confirm = "kept_fundamental"      # ... unless the mains fundamental is a line (amendment 3)
        else:
            refuted, ks = ks, []
    track = {"seconds": round(len(x) / sr, 2), "native_sr": sr, "peak_dbfs": round(20 * math.log10(max(peak, 1e-12)), 2),
             "near_fs": near_fs, "play_db": round(pl, 2), "mains": mains, "hum_harmonics": ks,
             "hum_rest_check": confirm, "rest_frames_16384": n_rest,
             "mains_line_hz": line_hz, "mains_line_prom_db": line_prom, "hum_harmonics_refuted": refuted,
             "hum_amendment": HUM_AMENDMENT,
             "hum_f0": round(mains_f0(y, mains, [k for k in ks if k <= 10] or ks), 3) if ks else None,
             "hum_rel_db": round(db(line_power(f, fs, mains, ks)) - pl, 2) if ks else None,
             "hiss_rel_db": round(db(band_power_sum(f, fs, *HISS_BAND)) - pl, 2) if fs is not None else None,
             "rest_hiss_2_6k_rel_db": (round(db(band_power_sum(fr, rs, *REST_HISS_BAND)) - pl, 2)
                                       if rs is not None and n_rest >= MIN_REST_SPEC else None)}
    clips = clip_runs(x)
    clip48 = (np.asarray(clips) * SR / sr).astype(int)
    drops, cuts = dropouts(x, sr, pl)
    drop48 = [int(s * SR / sr) for s, _ in drops]
    cut48 = [int(v * SR / sr) for s, e in cuts for v in (s, e)]
    track.update({"clip_runs": int(len(clips)), "dropouts": len(drops), "hard_cuts": len(cuts)})
    L = int(SEC_S * SR)
    rows = []
    for s in grid(len(y)):
        share, halves = section_activity(play, s)
        row = {"start_s": s / SR, "active": round(share, 4), "passes_activity": passes(share, halves)}
        if row["passes_activity"]:
            seg = y[s:s + L]
            r_ = frames_in(s, s + L, len(fdb))
            sdb = fdb[r_.start:r_.stop]
            spl = play_level_db(sdb, sdb >= fdb.max() - PLAY_DB)
            f2, fs2 = floor_spectrum(seg)
            rms = math.sqrt(float(np.mean(seg ** 2)))
            c = centroid_hz(seg)
            row.update({
                "play_db": round(spl, 2),
                "hum_rel_db": round(db(line_power(f2, fs2, mains, ks)) - spl, 2) if ks and fs2 is not None else None,
                # the refuted lines' level, as if the rest check had not refuted them (amendment 3; not a screen)
                "hum_rel_db_refuted": (round(db(line_power(f2, fs2, mains, refuted)) - spl, 2)
                                       if refuted and fs2 is not None else None),
                "hiss_rel_db": round(db(band_power_sum(f2, fs2, *HISS_BAND)) - spl, 2) if fs2 is not None else None,
                "clip_runs": int(np.sum((clip48 >= s) & (clip48 < s + L))),
                "dropouts": int(sum(s <= d < s + L for d in drop48)),
                "hard_cuts": int(sum(s <= d < s + L for d in cut48)),
                "dc_rel_db": round(20 * math.log10(abs(float(np.mean(seg))) / rms + 1e-12), 2) if rms > 0 else None,
                "onset_rate": round(onset_rate(seg), 3),
                "centroid_hz": round(c, 1) if c is not None else None,
            })
        rows.append(row)
    return track, rows


def vote(path):
    """A DI's mains vote {mains: (line count, power)} from its percentile spectrum."""
    x, sr = load_native(path)
    f, fs = floor_spectrum(resample(x, sr, SR))
    return {m: line_count(f, fs, m) for m in MAINS} if fs is not None else {}


def screen_session(recs, done, out_dir=None):
    """Screen the DIs of one session directory (or one Guitar-TECHS file): measures, then bleed
    from every other track of the session into each DI's rest frames. out_dir: where the screen
    files go (default OUT/screen; the clean/crunch pool's own screen, `learn.cc_pool`)."""
    import numpy as np

    todo = [r for r in recs if _key(r) not in done]
    if not todo:
        return
    votes = {}
    for r in recs:                                         # the session's mains: all its DIs vote
        for m, v in vote(r["path"]).items():
            votes.setdefault(m, []).append(v)
    mains = session_mains(votes)
    states = []
    for r in todo:
        x, sr = load_native(r["path"])
        track, rows = measure_di(x, sr, mains)
        track["session_mains_votes"] = {str(m): [list(v) for v in vs] for m, vs in votes.items()}
        y16 = resample(resample(x, sr, SR), SR, BLEED_SR)
        X = stft16(y16)
        xdb = 10 * np.log10(np.mean(np.abs(X) ** 2, 1) + 1e-30)
        rest = (xdb < xdb.max() - PLAY_DB) & (xdb > xdb.max() - 120)
        states.append({"rec": r, "track": track, "rows": rows, "X": X, "rest": rest, "n16": len(y16),
                       "sources": [], "bleed": [None] * len(rows)})
    sdir = recs[0].get("session_dir")
    others = sorted(p for p in pathlib.Path(sdir).glob("*.wav")) if sdir else []
    bins = bleed_bins()
    L16 = int(SEC_S * BLEED_SR)
    for p in others:
        users = [st for st in states if p.name != pathlib.Path(st["rec"]["path"]).name
                 and p.name not in {pathlib.PurePosixPath(o).name for o in st["rec"]["own"]}
                 and st["rest"].sum() >= MIN_REST_FRAMES]
        if not users:
            continue
        z, zsr = load_native(p)
        z16 = resample(z, zsr, BLEED_SR)
        for st in users:
            zz = np.zeros(st["n16"])
            k = min(len(zz), len(z16))
            zz[:k] = z16[:k]
            Y = stft16(zz)
            ydb = 10 * np.log10(np.mean(np.abs(Y) ** 2, 1) + 1e-30)
            rows_ = st["rest"] & (ydb >= ydb.max() - OTHER_ACTIVE_DB)
            if rows_.sum() < MIN_REST_FRAMES:
                st["sources"].append({"track": p.name, "msc": None, "frames": int(rows_.sum())})
                continue
            msc, bias = coherence(st["X"], Y, rows_, bins)
            st["sources"].append({"track": p.name, "msc": round(msc, 4), "bias": round(bias, 4),
                                  "frames": int(rows_.sum())})
            if msc - bias > BLEED_MSC:
                sls = []
                for row in st["rows"]:
                    a = int(row["start_s"] * BLEED_SR)
                    r_ = frames_in(a, a + L16, len(Y), BLEED_NFFT, BLEED_NFFT // 2)
                    sls.append(slice(r_.start, r_.stop))
                for i, v in enumerate(bleed_rel(st["X"], Y, rows_, sls, bins)):
                    if v is not None and st["rows"][i]["passes_activity"] and (st["bleed"][i] is None or v > st["bleed"][i][0]):
                        st["bleed"][i] = (v, p.name)
    for st in states:
        r = st["rec"]
        measured = [d for d in st["sources"] if d["msc"] is not None]
        status = bleed_status(int(st["rest"].sum()), len(measured), len(st["sources"]), bool(sdir))
        for row, b in zip(st["rows"], st["bleed"]):
            if row["passes_activity"]:
                row["bleed_rel_db"] = round(b[0], 2) if b else None
                row["bleed_from"] = b[1] if b else None
                row["bleed_status"] = status
        st["track"]["bleed_status"] = status
        st["track"]["rest_frames_16k"] = int(st["rest"].sum())
        st["track"]["bleed_sources"] = sorted([d for d in st["sources"] if d["msc"] is not None],
                                              key=lambda d: -d["msc"])[:5]
        st["track"]["bleed_unmeasured"] = sum(d["msc"] is None for d in st["sources"])
        st["track"]["bleed_tracks_checked"] = len(st["sources"])
        out = {"schema": SCREEN_SCHEMA, "id": r["id"], "path": r["path"], "track": st["track"], "rows": st["rows"]}
        _atomic(pathlib.Path(out_dir or OUT / "screen") / f"{_key(r)}.json", out)
        n = sum(x["passes_activity"] for x in st["rows"])
        print(f"{r['id'][:70]:70s} sections {n:3d} hum {st['track']['hum_rel_db']} hiss {st['track']['hiss_rel_db']} "
              f"clips {st['track']['clip_runs']} drops {st['track']['dropouts']} "
              f"bleed {[s['track'][:20] for s in st['sources'] if s['msc'] is not None and s['msc'] - s['bias'] > BLEED_MSC][:3]}", flush=True)


def bleed_status(rest_frames, measured, checked, has_session):
    """How far bleed was read for a DI: 'no_session' (a solo recording), 'no_rest_frames' (the DI
    never rests long enough), 'unmeasured' (no other track plays in its rests), 'partial' (some
    tracks could not be read), 'measured' (every other track was read). 'clean' never implies
    bleed-free unless 'measured' (review item 7)."""
    if not has_session:
        return "no_session"
    if rest_frames < MIN_REST_FRAMES:
        return "no_rest_frames"
    if measured == 0:
        return "unmeasured"
    return "measured" if measured == checked else "partial"


def cmd_screen(args):
    inv = json.loads((OUT / "inventory.json").read_text())
    (OUT / "screen").mkdir(parents=True, exist_ok=True)
    done = set()
    for p in (OUT / "screen").glob("*.json"):
        if json.loads(p.read_text()).get("schema") == SCREEN_SCHEMA:
            done.add(p.stem)
    groups = {}
    for r in inv["dis"]:
        if args.only and not any(o in r["id"] for o in args.only):
            continue
        # a session votes its mains together; Guitar-TECHS files vote per player
        groups.setdefault(r.get("session_dir") or r["band"], []).append(r)
    t0 = time.time()
    for i, (k, recs) in enumerate(sorted(groups.items())):
        screen_session(recs, done)
        print(f"[{i + 1}/{len(groups)}] {time.time() - t0:.0f}s", flush=True)


# --- the manifest -------------------------------------------------------------------------------

DI_TAGS = ("source", "set", "band", "song", "part", "slug", "gain_class", "genre", "licence", "split",
           "training_ok")


def _screens():
    out = {}
    for p in sorted((OUT / "screen").glob("*.json")):
        d = json.loads(p.read_text())
        out[d["path"]] = d
    return out


def manifest_rows(inv, screens, hum_fix_dis=()):
    """One row per section that passes the activity rule, with its flags, tags, DI tags, style
    and fixes; `clean` when unflagged (hum-flagged sections count as clean only once the fix is
    adopted, marked fix 'hum_notch'); `disjoint` marks the greedy non-overlapping clean ones."""
    rows = []
    for r in inv["dis"]:
        d = screens.get(r["path"])
        if d is None:
            continue
        clean_starts = []
        mine = []
        for x in d["rows"]:
            if not x["passes_activity"]:
                continue
            flags, tags = section_flags(x, d["track"])
            fix = ["dc_highpass"] if "dc" in tags else []
            if r["id"] in hum_fix_dis and flags == ["hum"]:
                flags, fix = [], fix + ["hum_notch"]
            row = {"di": r["id"], "path": r["path"], "start_s": x["start_s"], "end_s": x["start_s"] + SEC_S,
                   **{k: r.get(k) for k in DI_TAGS}, "flags": flags, "tags": tags, "fix": fix,
                   "clean": not flags, "style": style(x["onset_rate"]), "onset_rate": x["onset_rate"],
                   "centroid_hz": x["centroid_hz"], "bleed_status": x.get("bleed_status"),
                   "measures": {k: x.get(k) for k in ("play_db", "hum_rel_db", "hum_rel_db_refuted", "hiss_rel_db", "clip_runs",
                                                      "dropouts", "hard_cuts", "dc_rel_db", "bleed_rel_db",
                                                      "bleed_from")}}
            mine.append(row)
            if row["clean"]:
                clean_starts.append(int(round(x["start_s"] * SR)))
        keep = set(disjoint(clean_starts))
        for row in mine:
            row["disjoint"] = row["clean"] and int(round(row["start_s"] * SR)) in keep
        rows += mine
    return rows


def summarise(rows, inv):
    import collections

    def count(sel):
        sel = list(sel)
        return {"sections": len(sel), "clean": sum(r["clean"] for r in sel),
                "clean_disjoint": sum(r["disjoint"] for r in sel),
                "clean_minutes_disjoint": round(sum(r["disjoint"] for r in sel) * SEC_S / 60, 1)}

    flags = collections.Counter(f for r in rows for f in r["flags"])
    tags = collections.Counter(t for r in rows for t in r["tags"])
    by_source = {k: count(r for r in rows if str(r["set"]) == k) for k in sorted({str(r["set"]) for r in rows})}
    by_class = {k: count(r for r in rows if str(r["gain_class"]) == k)
                for k in sorted({str(r["gain_class"]) for r in rows})}
    dis_with_clean = len({r["di"] for r in rows if r["clean"]})
    return {"all": count(rows), "library_training_ok": count(r for r in rows if r["training_ok"]),
            "known_answer": count(r for r in rows if r["split"] == "known_answer"),
            "flags": dict(flags), "tags": dict(tags), "by_set": by_source, "by_gain_class": by_class,
            "by_style": dict(collections.Counter(r["style"] for r in rows if r["clean"])),
            "dis_screened": len({r["di"] for r in rows}), "dis_in_inventory": len(inv["dis"]),
            "dis_with_a_clean_section": dis_with_clean,
            "clean_by_bleed_status": dict(collections.Counter(str(r["bleed_status"]) for r in rows if r["clean"]))}


MANIFEST_VERSION = 2             # 1: amendments 1-2 (2026-10-18); 2: amendment 3's hum rule


def _archive_manifest():
    """Keep the manifest of an older version as manifest-v<n>.json before it is replaced."""
    cur = OUT / "manifest.json"
    if not cur.exists():
        return None
    v = json.loads(cur.read_text()).get("version", 1)
    if v >= MANIFEST_VERSION:
        return None
    dst = OUT / f"manifest-v{v}.json"
    if not dst.exists():
        dst.write_bytes(cur.read_bytes())
    return dst


def cmd_manifest(args):
    import hashlib

    if any(json.loads(p.read_text())["track"].get("hum_amendment") != HUM_AMENDMENT
           for p in (OUT / "screen").glob("*.json")):
        raise SystemExit("screen files predate amendment 3: run `hum-amend` first")
    archived = _archive_manifest()
    inv = json.loads((OUT / "inventory.json").read_text())
    screens = _screens()
    missing = [r["id"] for r in inv["dis"] if r["path"] not in screens]
    adopted = []
    fx = OUT / "hum-fix.json"
    if fx.exists():
        h = json.loads(fx.read_text())
        adopted = h.get("adopted_dis", []) if h.get("adopted") else []     # set only after the listening check
    rows = manifest_rows(inv, screens, set(adopted))
    summ = summarise(rows, inv)
    summ["unscreened"] = missing
    summ["hum_fix_adopted_dis"] = adopted
    out = {"schema": "clean-di-manifest-1", "version": MANIFEST_VERSION, "amendments": [1, 2, 3],
           "plan": "docs/clean-di-library-plan.md",
           "inventory_sha256": hashlib.sha256((OUT / "inventory.json").read_bytes()).hexdigest(),
           "previous": None, "summary": summ, "sections": rows}
    prev = archived or (OUT / f"manifest-v{MANIFEST_VERSION - 1}.json")
    if prev.exists():
        out["previous"] = {"file": prev.name, "sha256": hashlib.sha256(prev.read_bytes()).hexdigest()}
    _atomic(OUT / "manifest.json", out)
    print(json.dumps(summ, indent=1))
    print("manifest sha256", hashlib.sha256((OUT / "manifest.json").read_bytes()).hexdigest())


HUM_FIELDS = ("hum_harmonics", "hum_rest_check", "mains_line_hz", "mains_line_prom_db", "hum_harmonics_refuted",
              "hum_f0", "hum_rel_db")


def cmd_hum_amend(args):
    """Amendment 3 on the stored screen: re-measure the DIs whose hum lines the rest check refuted
    (only their hum can change), assert every other measure reproduces, and rewrite their hum fields;
    the screen as it stood is kept in screen-v1/. Every screen file is stamped hum_amendment = 3.
    Re-running it reads screen-v1/ again, so it is idempotent; after a fresh `screen` run (already
    under amendment 3), delete screen-v1/ rather than re-running this, or v1 rows come back."""
    import shutil

    sdir, keep = OUT / "screen", OUT / "screen-v1"
    if not keep.exists():
        if any(json.loads(p.read_text())["track"].get("hum_amendment") == HUM_AMENDMENT for p in sdir.glob("*.json")):
            raise SystemExit("the screen already carries amendment 3 and screen-v1/ is absent: nothing to amend")
        shutil.copytree(sdir, keep)
    changed = []
    for p in sorted(sdir.glob("*.json")):
        d = json.loads(p.read_text())
        old = json.loads((keep / p.name).read_text())
        t = d["track"]
        if old["track"]["hum_rest_check"] in ("no", "kept_fundamental"):
            x, sr = load_native(d["path"])
            track, rows = measure_di(x, sr, t["mains"])
            assert track["hum_rest_check"] in ("no", "kept_fundamental"), (d["id"], track["hum_rest_check"])
            for k in ("seconds", "play_db", "hiss_rel_db", "rest_frames_16384", "clip_runs", "dropouts"):
                assert track[k] == old["track"][k], (d["id"], k, track[k], old["track"][k])
            assert len(rows) == len(old["rows"])
            for a, b in zip(rows, old["rows"]):
                for k in ("start_s", "passes_activity", "play_db", "hiss_rel_db", "clip_runs", "onset_rate"):
                    assert a.get(k) == b.get(k), (d["id"], a["start_s"], k)
                if b["passes_activity"]:
                    b["hum_rel_db"], b["hum_rel_db_refuted"] = a["hum_rel_db"], a["hum_rel_db_refuted"]
            d["rows"] = old["rows"]
            t.update({k: track[k] for k in HUM_FIELDS})
            changed.append((d["id"], t["hum_rest_check"], t["mains_line_hz"], t["mains_line_prom_db"]))
            print(*changed[-1], flush=True)
        else:
            t.update({"mains_line_hz": None, "mains_line_prom_db": None, "hum_harmonics_refuted": []})
        t["hum_amendment"] = HUM_AMENDMENT
        _atomic(p, d)
    kept = [c for c in changed if c[1] == "kept_fundamental"]
    print(len(changed), "refuted DIs re-measured;", len(kept), "kept by the mains fundamental (amendment 3)")


# --- the hum fix's measured effect ------------------------------------------------------------------

FIX_CONTROLS = 20
FIX_CONTROL_S = 20.0             # each control DI: 20 s from its first passing section


def fix_adopted(collateral_band_db, residual_rel, listener_damage=None):
    """The adoption rule (amendments 1-2), per DI: `collateral_band_db` holds, per hum-free control
    DI, the largest excess of its band change over pink noise's under the same notch set
    (`excess_collateral`), each at most FIX_MAX_BAND_DB; its fixed sections' hum, read over every harmonic
    up to k = 40 (not only the notched ones), is under the flag level; and, once heard, the listener
    reports no guitar change on any notched trial. None while measured fine but not heard."""
    ok = (all(b <= FIX_MAX_BAND_DB for b in collateral_band_db)
          and all(h is None or h < HUM_FLAG_DB for h in residual_rel))
    if not ok:
        return False
    if listener_damage is None:
        return None
    return all(a == "no" for a in listener_damage)


def cmd_hum_fix(args):
    import random

    import numpy as np

    inv = json.loads((OUT / "inventory.json").read_text())
    screens = _screens()
    by_path = {r["path"]: r for r in inv["dis"]}
    flagged, clean = [], []
    for p, d in screens.items():
        t = d["track"]
        rows = [x for x in d["rows"] if x["passes_activity"]]
        if any("hum" in section_flags(x, t)[0] for x in rows):
            flagged.append(p)
        elif not t["hum_harmonics"] and not t.get("hum_harmonics_refuted") and rows:   # no line at all (amendment 3)
            clean.append(p)
    rng = random.Random(FIX_SEED)
    controls = rng.sample(sorted(clean), min(FIX_CONTROLS, len(clean)))
    ctrl = {}
    for p in controls:                          # 20 s from each control's first passing section
        x, sr = load_native(p)
        y = resample(x, sr, SR)
        s0 = int(next(r["start_s"] for r in screens[p]["rows"] if r["passes_activity"]) * SR)
        y = y[s0:s0 + int(FIX_CONTROL_S * SR)]
        ctrl[p] = (y, playing(frame_db(y, 4096, 2048)))
    cache = {}
    allk = list(range(1, HUM_MAX_K + 1))
    res = {"seed": FIX_SEED, "controls": [by_path[p]["id"] for p in controls], "dis": []}
    for p in sorted(flagged):
        t = screens[p]["track"]
        f0, ks = t["hum_f0"], t["hum_harmonics"]
        ck = (round(f0, 2), tuple(ks))           # DIs sharing a notch set share its collateral
        if ck not in cache:
            ref = noise_reference(f0, ks)
            col = []
            for y, play in ctrl.values():
                z = notch(y, f0, ks)
                ch = np.abs(third_octave_db(z, play, lo=FIX_BAND_LO) - third_octave_db(y, play, lo=FIX_BAND_LO))
                col.append((excess_collateral(ch, ref), db(np.mean((y - z) ** 2)) - db(np.mean(y ** 2))))
            cache[ck] = (ref, col)
        ref, col = cache[ck]
        x, sr = load_native(p)
        y = resample(x, sr, SR)
        fixed = notch(y, f0, ks)
        before, after = [], []
        for row in screens[p]["rows"]:
            if not row["passes_activity"] or "hum" not in section_flags(row, t)[0]:
                continue
            s = int(row["start_s"] * SR)
            for src, acc in ((y, before), (fixed, after)):
                f2, fs2 = floor_spectrum(src[s:s + int(SEC_S * SR)])
                acc.append(round(db(line_power(f2, fs2, t["mains"], allk)) - row["play_db"], 2))
        bands = [round(b, 4) for b, _ in col]
        verdict = fix_adopted(bands, after, None)
        res["dis"].append({"id": by_path[p]["id"], "f0": f0, "harmonics": ks,
                           "collateral_max_excess_over_noise_db": max(bands) if bands else None,
                           "noise_reference_max_band_db": round(float(ref.max()), 4),
                           "collateral_removed_db_reported": [round(r, 2) for _, r in col],
                           "hum_allk_before": before, "hum_allk_after": after, "measured_ok": verdict is not False})
        print(by_path[p]["id"][:70], "f0", f0, len(ks), "lines; collateral max band", max(bands) if bands else None,
              "hum before/after (max)", max(before) if before else None, max(after) if after else None, flush=True)
    res["measured_ok_dis"] = [d["id"] for d in res["dis"] if d["measured_ok"]]
    res["adopted"] = False if not res["measured_ok_dis"] else None
    res["hum_amendment"] = HUM_AMENDMENT
    res["adoption_note"] = ("adoption waits on the listening check for the DIs whose measures pass; the rest stay out"
                            if res["measured_ok_dis"] else "no flagged DI passes the measured conditions: "
                            "hum-flagged sections stay out")
    old = OUT / "hum-fix.json"
    if old.exists() and json.loads(old.read_text()).get("hum_amendment") != HUM_AMENDMENT \
            and not (OUT / "hum-fix-v1.json").exists():
        (OUT / "hum-fix-v1.json").write_bytes(old.read_bytes())   # the run before amendment 3, kept
    _atomic(OUT / "hum-fix.json", res)
    print(len(res["measured_ok_dis"]), "of", len(res["dis"]), "flagged DIs pass the measured conditions")


# --- the blind listening check ----------------------------------------------------------------------

LISTEN_SEED = 20261017
CONTINUOUS = {"hum": ("hum_rel_db", HUM_TAG_DB, HUM_FLAG_DB), "hiss": ("hiss_rel_db", HISS_TAG_DB, HISS_FLAG_DB)}
STRATA = ("below_tag", "tag_to_flag", "just_over", "well_over")
DISCRETE = ("clipping", "dropout", "bleed")
PER_STRATUM, PER_DISCRETE, N_HARD_CUT, N_CLEAN = 2, 2, 2, 4
N_HUM_AB = 6
PROBLEMS = ("ok", "hum", "hiss", "click", "dist", "bleed", "other")
FLAG_TO_PROBLEM = {"hum": "hum", "hiss": "hiss", "clipping": "dist", "dropout": "click", "bleed": "bleed",
                   "hard_cut": "click"}
BENIGN_TAGS = {"dc", "bleed_unread", "bleed_partly_read"}
REPEAT = "repeat"
STEP_DB = 5.0                    # amend(): how far a threshold moves when no clip bounds it


def _group(row):
    return "guitar-techs" if row["source"] == "guitar-techs" else row["source"]


def stratum(v, tag, flag):
    """Where a measured value sits around a screen's tag and flag levels."""
    if v is None:
        return None
    if v < tag:
        return "below_tag"
    if v < flag:
        return "tag_to_flag"
    return "just_over" if v < flag + 10 else "well_over"


def draw(rows, seed=LISTEN_SEED, n_hum=N_HUM_AB):
    """The page's trials from manifest rows (sections that pass the activity rule). Part 1, at most
    one clip per DI: for hum and hiss, PER_STRATUM sections in each stratum of the measured value
    around the tag and flag levels (no other flag); PER_DISCRETE sections per discrete flag; N_HARD_CUT
    sections tagged hard_cut (no flag); N_CLEAN clean sections with no tag beyond the benign ones,
    round-robin over sources; then one repeat of a screened clip and one of a clean clip, shuffled
    until no repeat is first or next to its source. Part 2: up to `n_hum` hum-flagged sections (one
    per DI), the notched letter balanced, plus one null trial (A = B = original)."""
    import random

    rng = random.Random(seed)
    used = set()

    def take(pool, n, **info):
        pool = sorted(pool, key=lambda r: (r["di"], r["start_s"]))
        rng.shuffle(pool)
        out = []
        for r in pool:
            if len(out) >= n:
                break
            if r["di"] in used:
                continue
            used.add(r["di"])
            out.append({**_ref(r), **info})
        return out

    part1 = []
    for scr, (key, tag, flag) in CONTINUOUS.items():
        for st in STRATA:
            pool = [r for r in rows if stratum(r["measures"].get(key), tag, flag) == st
                    and not (set(r["flags"]) - {scr})]
            for t in take(pool, PER_STRATUM, kind="screen", screen=scr, stratum=st):
                t["value"] = next(r["measures"][key] for r in rows if _same(r, t))
                part1.append(t)
    for fl in DISCRETE:
        part1 += take([r for r in rows if fl in r["flags"]], PER_DISCRETE, kind="screen", screen=fl,
                      stratum="flagged", value=None)
    part1 += take([r for r in rows if "hard_cut" in r["tags"] and not r["flags"]], N_HARD_CUT, kind="screen",
                  screen="hard_cut", stratum="tagged", value=None)
    clean = [r for r in rows if r["clean"] and not (set(r["tags"]) - BENIGN_TAGS)]
    groups = sorted({_group(r) for r in clean})
    picks, i = [], 0
    while len(picks) < N_CLEAN and any(r["di"] not in used for r in clean) and i < 100:
        g = groups[i % len(groups)]
        picks += take([r for r in clean if _group(r) == g], 1, kind="clean", screen=None, stratum=None, value=None)
        i += 1
    part1 += picks
    screened = [t for t in part1 if t["kind"] == "screen" and t["stratum"] not in ("below_tag",)]
    if screened:
        part1.append({**rng.choice(screened), "kind": REPEAT})
    if picks:
        part1.append({**rng.choice(picks), "kind": REPEAT})
    for _ in range(10000):
        rng.shuffle(part1)
        bad = False
        for i, t in enumerate(part1):
            if t["kind"] != REPEAT:
                continue
            j = next(j for j, u in enumerate(part1) if u["kind"] != REPEAT and _same(u, t))
            if i == 0 or abs(i - j) <= 1:
                bad = True
        if not bad:
            break
    hum = sorted({r["di"]: r for r in sorted(rows, key=lambda r: (r["di"], r["start_s"]))
                  if "hum" in r["flags"]}.values(), key=lambda r: r["di"])
    rng.shuffle(hum)
    hum = hum[:n_hum]
    n = len(hum)
    on_a = [True] * (n // 2) + [False] * (n - n // 2)
    rng.shuffle(on_a)
    part2 = [{**_ref(r), "kind": "hum_ab", "letters": {"A": "notched", "B": "original"} if a
              else {"A": "original", "B": "notched"}} for r, a in zip(hum, on_a)]
    if part2:
        part2.append({**{k: part2[0][k] for k in ("di", "path", "start_s")}, "kind": "null",
                      "letters": {"A": "original", "B": "original"}})
        for _ in range(10000):
            rng.shuffle(part2)
            i = next(i for i, t in enumerate(part2) if t["kind"] == "null")
            j = next(j for j, t in enumerate(part2) if t["kind"] != "null" and _same(t, part2[i]))
            if i > 0 and abs(i - j) > 1:
                break
    return part1, part2


def amend(clips, flag, step=STEP_DB):
    """The declared amendment rule for a continuous screen. `clips`: [(measured value, heard with
    the screen's problem: bool)], unanswered clips left out. At least two clips under the flag heard
    with the problem lower it to midway between the lowest of them and the highest clip under that
    heard clean (or `step` under it); at least two clips at or over the flag heard clean raise it to
    midway between the highest of them and the lowest clip over that heard with the problem (or
    `step` over it). Both at once: unchanged, 'conflict'. Returns (new flag, reason)."""
    heard_below = [v for v, h in clips if h and v < flag]
    clean_over = [v for v, h in clips if not h and v >= flag]
    lower, raise_ = len(heard_below) >= 2, len(clean_over) >= 2
    if lower and raise_:
        return flag, "conflict"
    if lower:
        lo = min(heard_below)
        below = [v for v, h in clips if not h and v < lo]
        return round((lo + max(below)) / 2 if below else lo - step, 2), "lowered"
    if raise_:
        hi = max(clean_over)
        above = [v for v, h in clips if h and v > hi]
        return round((hi + min(above)) / 2 if above else hi + step, 2), "raised"
    return flag, "stays"


def _ref(r):
    return {"di": r["di"], "path": r["path"], "start_s": r["start_s"], "flags": list(r["flags"])}


def _same(a, b):
    return a["di"] == b["di"] and a["start_s"] == b["start_s"]


ANSWER1 = re.compile(r"(\d+)((?:ok|hum|hiss|click|dist|bleed|other|\?)(?:\+(?:ok|hum|hiss|click|dist|bleed|other))*)",
                     re.I)
ANSWER2 = re.compile(r"H(\d+)(a|b|same|\?)-(no|little|lot|\?)", re.I)


def parse_answers(text):
    """'1ok 2hum+hiss 3? H1A-no H2same-little' -> ({'1': {'ok'}, '2': {'hum', 'hiss'}, '3': None},
    {'1': ('A', 'no'), '2': ('same', 'little')})."""
    p1, p2 = {}, {}
    for tok in text.split():
        m2 = ANSWER2.fullmatch(tok)
        if m2:
            w = m2.group(2).lower()
            g = m2.group(3).lower()
            p2[m2.group(1)] = ({"a": "A", "b": "B", "same": "same", "?": None}[w], None if g == "?" else g)
            continue
        m1 = ANSWER1.fullmatch(tok)
        if not m1:
            raise SystemExit(f"cannot read answer {tok!r} (expected like 1ok, 2hum+hiss, H1A-no)")
        s = {x.lower() for x in m1.group(2).split("+")}
        p1[m1.group(1)] = None if s == {"?"} else s
    return p1, p2


def score_key(key, answers):
    """Descriptive counts and the declared amendments: per screen and stratum, clips named with the
    screen's problem; for hum and hiss the amend() proposal; for a discrete flag or hard_cut, both
    clips heard clean proposes it becomes a tag; clean clips named with any problem (two naming the
    same unscreened problem asks for a new screen); repeats beside their sources; hum A/B picks."""
    import collections

    p1, p2 = answers
    rows = []
    for n, t in sorted(key["part1"].items(), key=lambda x: int(x[0])):
        heard = p1.get(n)
        rows.append({"trial": int(n), **t, "heard": sorted(heard) if heard else None})
    per_screen = {}
    for r in rows:
        if r["kind"] != "screen" or r["heard"] is None:
            continue
        d = per_screen.setdefault(r["screen"], {}).setdefault(r["stratum"], {"clips": 0, "named": 0, "heard_ok": 0})
        d["clips"] += 1
        d["named"] += FLAG_TO_PROBLEM[r["screen"]] in r["heard"]
        d["heard_ok"] += r["heard"] == ["ok"]
    proposals = {}
    for scr, (_, _, flag) in CONTINUOUS.items():
        clips = [(r["value"], FLAG_TO_PROBLEM[scr] in r["heard"]) for r in rows
                 if r["kind"] == "screen" and r["screen"] == scr and r["heard"] is not None and r["value"] is not None]
        new, why = amend(clips, flag)
        tag = CONTINUOUS[scr][1]
        proposals[scr] = {"flag": new, "reason": why, "tag": round(tag + (new - flag), 2)}
    for scr in (*DISCRETE, "hard_cut"):
        sel = [r for r in rows if r["kind"] == "screen" and r["screen"] == scr and r["heard"] is not None]
        if sel:
            clean_heard = sum(FLAG_TO_PROBLEM[scr] not in r["heard"] for r in sel)
            proposals[scr] = {"reason": "becomes a tag" if clean_heard >= 2 and clean_heard == len(sel) else "stays"}
    clean = [r for r in rows if r["kind"] == "clean"]
    named = collections.Counter(p for r in clean if r["heard"] for p in r["heard"] if p != "ok")
    passing = {"clips": len(clean), "any_problem": sum(bool(r["heard"]) and r["heard"] != ["ok"] for r in clean),
               "unanswered": sum(r["heard"] is None for r in clean), "named": dict(named),
               "new_screen_needed_for": sorted(p for p, c in named.items() if c >= 2)}
    reps = []
    for r in rows:
        if r["kind"] == REPEAT:
            src = next(u for u in rows if u["kind"] != REPEAT and _same(u, r))
            reps.append({"repeat": r["trial"], "source": src["trial"], "repeat_heard": r["heard"],
                         "source_heard": src["heard"]})
    hum = []
    for n, t in sorted(key.get("part2", {}).items(), key=lambda x: int(x[0])):
        w, g = p2.get(n, (None, None))
        names = None if w is None else ("same" if w == "same" else t["letters"][w])
        hum.append({"trial": int(n), "kind": t["kind"], "di": t["di"], "less_hum": w, "names": names, "guitar": g})
    ab = [h for h in hum if h["kind"] == "hum_ab"]
    hum_summary = {"trials": len(ab), "notched_less_hum": sum(h["names"] == "notched" for h in ab),
                   "original_less_hum": sum(h["names"] == "original" for h in ab),
                   "same": sum(h["names"] == "same" for h in ab),
                   "guitar": dict(collections.Counter(h["guitar"] or "unanswered" for h in ab)),
                   "guitar_by_di": {h["di"]: h["guitar"] for h in ab},
                   "null": next(({"less_hum": h["less_hum"], "guitar": h["guitar"]} for h in hum if h["kind"] == "null"), None)}
    return {"part1": rows, "per_screen": per_screen, "proposals": proposals, "passing": passing,
            "repeats": reps, "hum_ab": hum, "hum_summary": hum_summary}


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guitar track check</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#fff; --acc:#2d5bd7; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#161614; --fg:#ecebe6; --muted:#a3a29c;
  --line:#33322e; --card:#1f1f1c; --acc:#7da0ff; }} }}
body {{ background:var(--bg); color:var(--fg); font:16px/1.45 -apple-system,system-ui,sans-serif;
  margin:0 auto; max-width:720px; padding:16px; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px;
  margin:14px 0; }}
.row {{ display:flex; align-items:center; gap:10px; margin:6px 0; }}
.row b {{ width:2em; }} audio {{ width:100%; }}
.q {{ margin:10px 0 2px; }}
.pick button {{ font-size:16px; padding:8px 12px; margin:4px 6px 0 0; border-radius:8px;
  border:1px solid var(--line); background:var(--bg); color:var(--fg); }}
.pick button.on {{ background:var(--acc); color:#fff; border-color:var(--acc); }}
#line {{ font:15px ui-monospace,monospace; padding:10px; border:1px dashed var(--line); border-radius:8px;
  word-break:break-all; }} .muted {{ color:var(--muted); }}
</style></head><body>
<h1>Do these guitar tracks have problems?</h1>
<p class="muted">These are raw guitar recordings, straight from the guitar with no amp, so they
sound thin and plain. That is expected. The question is whether the recording itself has a fault.
Each clip is 10 seconds, all at the same loudness. Some may sound fine. Headphones help; guess if unsure.</p>
<h2>Part 1: what do you hear?</h2>
<p class="muted">For each clip, tap every problem you hear, or OK if none: hum or buzz; hiss or
noise; clicks, dropouts or crackle; distortion or clipping; other instruments leaking in; or
something else. Some clips may appear twice.</p>
{part1}
{part2_block}
<h2>Your answers</h2>
<p class="muted">Copy this line and send it back. Part 1 items read like <code>1ok</code> or
<code>2hum+hiss</code>; part 2 items like <code>H1A-no</code> (A has less hum, the guitar sounds
no different). A ? marks a question not yet answered.</p>
<div id="line">-</div>
<script>
const key = "di-clean-{build}";
let a = {{}}; try {{ a = JSON.parse(localStorage.getItem(key) || "{{}}"); }} catch (e) {{}}
function show() {{
  document.querySelectorAll(".multi").forEach(p => p.querySelectorAll("button").forEach(b =>
    b.classList.toggle("on", ((a["p" + p.dataset.trial] || {{}}).set || []).includes(b.dataset.value))));
  document.querySelectorAll(".one").forEach(p => p.querySelectorAll("button").forEach(b =>
    b.classList.toggle("on", (a["h" + p.dataset.trial] || {{}})[p.dataset.q] === b.dataset.value)));
  const one = [...new Set([...document.querySelectorAll(".multi")].map(p => p.dataset.trial))];
  const two = [...new Set([...document.querySelectorAll(".one")].map(p => p.dataset.trial))];
  document.getElementById("line").textContent =
    one.map(t => {{ const s = (a["p" + t] || {{}}).set || []; return t + (s.length ? s.join("+") : "?"); }})
    .concat(two.map(t => "H" + t + ((a["h" + t] || {{}}).w || "?") + "-" + ((a["h" + t] || {{}}).g || "?")))
    .join(" ");
}}
function save() {{ try {{ localStorage.setItem(key, JSON.stringify(a)); }} catch (e) {{}} show(); }}
document.querySelectorAll(".multi button").forEach(b => b.onclick = () => {{
  const t = "p" + b.parentElement.dataset.trial, v = b.dataset.value;
  let s = (a[t] || {{}}).set || [];
  if (v === "ok") s = s.includes("ok") ? [] : ["ok"];
  else {{ s = s.filter(x => x !== "ok"); s = s.includes(v) ? s.filter(x => x !== v) : s.concat([v]); }}
  a[t] = {{set: s}}; save(); }});
document.querySelectorAll(".one button").forEach(b => b.onclick = () => {{
  const p = b.parentElement, t = "h" + p.dataset.trial;
  a[t] = Object.assign(a[t] || {{}}, {{[p.dataset.q]: b.dataset.value}}); save(); }});
document.querySelectorAll("audio").forEach(x => x.addEventListener("play", () =>
  document.querySelectorAll("audio").forEach(y => {{ if (y !== x) y.pause(); }})));
show();
</script></body></html>
"""

PART2 = """<h2>Part 2: hum taken out?</h2>
<p class="muted">Each trial plays the same 10 seconds twice, as A and B. One may have had its hum
taken out; some trials may have two identical clips. Answer which has less hum (A, B or the same)
and whether the guitar itself sounds different apart from the hum (no, a little, a lot).</p>
{trials}"""


def section1(n, src):
    btn = "".join(f'<button type="button" data-value="{v}">{lab}</button>' for v, lab in
                  (("ok", "OK"), ("hum", "Hum/buzz"), ("hiss", "Hiss/noise"), ("click", "Clicks/dropouts"),
                   ("dist", "Distortion"), ("bleed", "Other instruments"), ("other", "Something else")))
    return (f'<section><h2>Clip {n}</h2><div class="row"><audio controls preload="none" src="{src}"></audio></div>'
            f'<div class="pick multi" data-trial="{n}">{btn}</div></section>')


def section2(n, clips):
    rows = "".join(f'<div class="row"><b>{L}</b><audio controls preload="none" src="{s}"></audio></div>' for L, s in clips)
    w = "".join(f'<button type="button" data-value="{v}">{lab}</button>' for v, lab in (("A", "A"), ("B", "B"), ("same", "Same")))
    g = "".join(f'<button type="button" data-value="{v}">{lab}</button>' for v, lab in
                (("no", "No"), ("little", "A little"), ("lot", "A lot")))
    return (f'<section><h2>Trial H{n}</h2>{rows}<div class="q">Less hum?</div>'
            f'<div class="pick one" data-trial="{n}" data-q="w">{w}</div>'
            f'<div class="q">Guitar sounds different?</div><div class="pick one" data-trial="{n}" data-q="g">{g}</div></section>')


def _clip(path, start_s):
    x, sr = load_native(path)
    y = resample(x, sr, SR)
    s = int(start_s * SR)
    return y[s:s + int(SEC_S * SR)]


def cmd_listen(args):
    import hashlib
    import tempfile

    import numpy as np

    from learn import build_bleed_damage as BD
    from learn import build_knob_listening as BK

    if args.step == "score":
        key = json.loads((LISTEN / "private" / "key.json").read_text())
        rep = score_key(key, parse_answers(args.answers))
        for r in rep["part1"]:
            print(f"{r['trial']:2d} {r['kind']:7s} {str(r['screen']):8s} {str(r['stratum']):11s} {r['value']} "
                  f"{r['di'][:55]} @{r['start_s']:.0f}s -> {r['heard']}")
        for k in ("per_screen", "proposals", "passing", "repeats", "hum_summary"):
            print(k, json.dumps(rep[k]))
        rep["answers"] = args.answers
        (LISTEN / "private" / "score.json").write_text(json.dumps(rep, indent=1))
        return
    if (LISTEN / "private" / "key.json").exists() and not args.force:
        raise SystemExit(f"{LISTEN / 'private' / 'key.json'} exists; pass --force to rebuild")
    man = json.loads((OUT / "manifest.json").read_text())
    screens = _screens()
    fx = OUT / "hum-fix.json"
    # part 2 only asks the ear about a fix whose measured conditions hold (amendment 1, item 8)
    n_hum = 0 if fx.exists() and json.loads(fx.read_text()).get("adopted") is False else N_HUM_AB
    part1, part2 = draw(man["sections"], n_hum=n_hum)
    key = {"plan": "docs/clean-di-library-plan.md", "seed": LISTEN_SEED,
           "note": "part 2's null trial reuses one hum trial's section (played four times in all)",
           "manifest_sha256": hashlib.sha256((OUT / "manifest.json").read_bytes()).hexdigest(),
           "part1": {}, "part2": {}}
    s1, s2 = [], []
    with tempfile.TemporaryDirectory() as tmp:
        enc = lambda x: BD.pad(BK.aac(BK.fade(x), tmp))  # noqa: E731
        for n, t in enumerate(part1, 1):
            x = _clip(t["path"], t["start_s"])
            s1.append(section1(n, enc(BK.level(np.asarray(x, np.float64)))))
            key["part1"][str(n)] = t
            print(n, t["kind"], t["screen"], t["stratum"], t["value"], t["di"], t["start_s"], flush=True)
        for n, t in enumerate(part2, 1):
            x = np.asarray(_clip(t["path"], t["start_s"]), np.float64)
            tr = screens[t["path"]]["track"]
            whole, sr = load_native(t["path"])
            fixed = notch(resample(whole, sr, SR), tr["hum_f0"], tr["hum_harmonics"])
            s = int(t["start_s"] * SR)
            fx = fixed[s:s + int(SEC_S * SR)]
            lev = BK.level(x)
            g = float(np.sum(lev * x) / np.sum(x * x))            # one gain for both clips
            clips = {"original": lev, "notched": fx * g}
            peak = max(np.abs(clips["original"]).max(), np.abs(clips["notched"]).max())
            if peak > 0.95:
                clips = {k: v * (0.95 / peak) for k, v in clips.items()}
            s2.append(section2(n, [(L, enc(clips[name])) for L, name in t["letters"].items()]))
            key["part2"][str(n)] = t
            print("H", n, t["kind"], t["letters"], t["di"], t["start_s"], flush=True)
    build = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]
    page = PAGE.format(part1="\n".join(s1), part2_block=PART2.format(trials="\n".join(s2)) if s2 else "",
                       build=build)
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", page).lower()
    words = {"telefunken", "cambridge", "elecgtr", "gtr ", "techs", "directinput", "repeat", "flagged",
             "notched", "original\"", "null"}
    words |= {t["di"].lower() for t in part1 + part2}
    words |= {pathlib.Path(t["path"]).stem.lower() for t in part1 + part2}
    for w in words:
        assert w not in text, w
    uris = re.findall(r'src="(data:[^"]+)"', page)
    # Distinct only because of BD.pad's random `free` box: a repeat's AAC stream is byte-identical
    # to its source's before the padding, and encoded sizes still follow the content (a hissy clip
    # encodes larger, an edit to silence smaller). It blinds the ear, not a byte inspection.
    assert len(uris) == len(set(uris)), "duplicate clip bytes"
    (LISTEN / "private").mkdir(parents=True, exist_ok=True)
    (LISTEN / "private" / "key.json").write_text(json.dumps(key, indent=1))
    out = LISTEN / "di-clean.html"
    out.write_text(page)
    print(out, f"{out.stat().st_size / 1e6:.2f} MB", "clips", len(uris))


# --- the second blind page: amendment 3's hum rule -------------------------------------------------

LISTEN2 = HOME / "listening/di-clean-2"
LISTEN2_SEED = 20261018
N_REFUTED, N_ANCHOR = 8, 2
N_PER_UNIT = 2                   # clips from a multi-DI unit (Guitar-TECHS P1's chord files: one recording setup)
PAGE2_TAGS_OK = BENIGN_TAGS | {"slight_hiss", "rest_hiss"}   # rest_hiss describes the track's rests, not the section
KEPT_TAGS_OK = PAGE2_TAGS_OK | {"hum_kept_by_fundamental"}


def hum_unit(di):
    """The unit a kept DI votes as: Guitar-TECHS P1's near-identical chord files are one unit."""
    return "guitar-techs-P1" if di.startswith("guitar-techs/P1-") else di


def draw_hum(rows_v1, rows, page1_dis=(), seed=LISTEN2_SEED):
    """Amendment 3's page. 'kept': for every unit (`hum_unit`) whose lines amendment 3 keeps, one
    section it moves (clean before, flagged for hum alone now); N_PER_UNIT sections, from different
    DIs, for a multi-DI unit. 'refuted': N_REFUTED DIs whose lines the rest check
    still refutes, one clean section each among those the refuted lines would flag (where the rest
    check alone decides). Anchors: N_ANCHOR hum-only sections of rest-confirmed DIs at least 10 dB
    over the flag, and N_ANCHOR clean sections of DIs with no hum line. Then one repeat each of a
    kept and a refuted clip, never first or next to its source. One clip per DI; DIs on page 1 are
    left out of the refuted and anchor draws. Rows are manifest sections (v1 and amended)."""
    import random

    rng = random.Random(seed)
    was_clean = {(r["di"], r["start_s"]) for r in rows_v1 if r["clean"]}
    used = set(page1_dis)

    def take(pool, n, kind, fixed=False):
        pool = sorted(pool, key=lambda r: (r["di"], r["start_s"]))
        rng.shuffle(pool)
        out, seen = [], set()
        for r in pool:
            if len(out) >= n:
                break
            if r["di"] in seen or (not fixed and r["di"] in used):
                continue
            seen.add(r["di"])
            used.add(r["di"])
            out.append({**_ref(r), "kind": kind, "value": r["measures"].get("hum_rel_db"),
                        "value_refuted": r["measures"].get("hum_rel_db_refuted")})
        return out

    kept = [r for r in rows if r["flags"] == ["hum"] and "hum_kept_by_fundamental" in r["tags"]
            and (r["di"], r["start_s"]) in was_clean and not (set(r["tags"]) - KEPT_TAGS_OK)]
    clips = []
    for u in sorted({hum_unit(r["di"]) for r in kept}):
        n = N_PER_UNIT if sum(1 for d in {r["di"] for r in kept} if hum_unit(d) == u) > 1 else 1
        clips += [{**t, "unit": u} for t in take([r for r in kept if hum_unit(r["di"]) == u], n, "kept", fixed=True)]
    refuted = [r for r in rows if r["clean"] and r["measures"].get("hum_rel_db_refuted") is not None
               and r["measures"]["hum_rel_db_refuted"] >= HUM_FLAG_DB and not (set(r["tags"]) - PAGE2_TAGS_OK)]
    clips += take(refuted, N_REFUTED, "refuted")
    hummy = [r for r in rows if r["flags"] == ["hum"] and r["measures"]["hum_rel_db"] >= HUM_FLAG_DB + 10
             and not ({"hum_unconfirmed_on_rests", "hum_kept_by_fundamental"} & set(r["tags"]))]
    clips += take(hummy, N_ANCHOR, "anchor_hum")
    quiet = [r for r in rows if r["clean"] and r["measures"].get("hum_rel_db") is None
             and r["measures"].get("hum_rel_db_refuted") is None and not (set(r["tags"]) - BENIGN_TAGS)]
    clips += take(quiet, N_ANCHOR, "anchor_clean")
    for kind in ("kept", "refuted"):
        src = [t for t in clips if t["kind"] == kind]
        if src:
            clips.append({**rng.choice(src), "kind": REPEAT, "repeat_of": kind})
    for _ in range(10000):
        rng.shuffle(clips)
        ok = True
        for i, t in enumerate(clips):
            if t["kind"] == REPEAT:
                j = next(j for j, u in enumerate(clips) if u["kind"] != REPEAT and _same(u, t))
                ok &= i > 0 and abs(i - j) > 1
        if ok:
            return clips
    raise RuntimeError("no order keeps every repeat apart from its source")


def score_hum(key, answers):
    """Amendment 3's declared rule on the second page's answers (trusted; unanswered left out).
    - kept, per unit (`hum_unit`): a unit more than half of whose answered clips are heard without
      hum reverts (its lines refuted again, as before amendment 3). When at least 2 units, and more
      than half of the answered units, revert, the amendment is withdrawn for every DI.
    - refuted, per DI: a DI whose clip is heard with hum has its lines restored (kept and screened
      by level). When at least half of the answered refuted clips, and a larger share than of the
      answered clean anchors, are heard with hum, the rest check's refutation is suspended for every
      DI until a further amendment designs a better test.
    - withdrawal and suspension at once: neither applies, and the conflict is reported (the per-unit
      and per-DI changes still apply).
    - this page does not move the hum flag level (page 1's strata test it); anchors and repeats are
      reported as a calibration caveat and move nothing."""
    p1, _ = answers
    rows = []
    for n, t in sorted(key["clips"].items(), key=lambda x: int(x[0])):
        heard = p1.get(n)
        rows.append({"trial": int(n), **t, "heard": sorted(heard) if heard else None,
                     "hum": None if not heard else "hum" in heard})

    def sel(kind):
        return [r for r in rows if r["kind"] == kind and r["hum"] is not None]

    units = {}
    for r in sel("kept"):
        units.setdefault(r.get("unit", r["di"]), []).append(r["hum"])
    reverted = sorted(u for u, h in units.items() if sum(not x for x in h) > len(h) / 2)
    withdraw = len(reverted) >= 2 and len(reverted) > len(units) / 2
    ref = sel("refuted")
    restored = sorted(r["di"] for r in ref if r["hum"])
    share = len(restored) / len(ref) if ref else 0.0
    anc = sel("anchor_clean")
    anc_share = sum(r["hum"] for r in anc) / len(anc) if anc else 0.0
    suspend = bool(ref) and share >= 0.5 and share > anc_share
    if withdraw and suspend:
        decision, withdraw, suspend = "conflict: neither withdrawal nor suspension applies", False, False
    else:
        decision = ("amendment 3 withdrawn" if withdraw else "amendment 3 stands") + (
            "; rest refutation suspended" if suspend else "")
    reps = []
    for r in rows:
        if r["kind"] == REPEAT:
            src = next(u for u in rows if u["kind"] != REPEAT and _same(u, r))
            reps.append({"repeat": r["trial"], "source": src["trial"], "repeat_heard": r["heard"],
                         "source_heard": src["heard"]})
    return {"clips": rows, "decision": decision, "withdraw": withdraw, "suspend": suspend,
            "kept": {"units_answered": len(units), "units_reverted": reverted},
            "refuted": {"answered": len(ref), "heard_hum": len(restored), "restored_dis": restored,
                        "clean_anchor_hum_share": anc_share},
            "anchors": {k: [r["heard"] for r in rows if r["kind"] == k] for k in ("anchor_hum", "anchor_clean")},
            "repeats": reps}


def cmd_listen_hum(args):
    import hashlib
    import tempfile

    import numpy as np

    from learn import build_bleed_damage as BD
    from learn import build_knob_listening as BK

    kfile = LISTEN2 / "private" / "key.json"
    if args.step == "score":
        key = json.loads(kfile.read_text())
        rep = score_hum(key, parse_answers(args.answers))
        for r in rep["clips"]:
            print(f"{r['trial']:2d} {r['kind']:12s} {r.get('unit', '')[:16]:16s} {r['value']} {r['value_refuted']} {r['di'][:55]} "
                  f"@{r['start_s']:.0f}s -> {r['heard']}")
        for k in ("decision", "kept", "refuted", "anchors", "repeats"):
            print(k, json.dumps(rep[k]))
        rep["answers"] = args.answers
        (LISTEN2 / "private" / "score.json").write_text(json.dumps(rep, indent=1))
        return
    if kfile.exists() and not args.force:
        raise SystemExit(f"{kfile} exists; pass --force to rebuild")
    man = json.loads((OUT / "manifest.json").read_text())
    if man.get("version", 1) < MANIFEST_VERSION:
        raise SystemExit("the manifest predates amendment 3: run `hum-amend` and `manifest` first")
    if not man.get("previous"):
        raise SystemExit("no version 1 manifest to compare with (manifest-v1.json)")
    v1 = json.loads((OUT / man["previous"]["file"]).read_text())
    page1 = json.loads((LISTEN / "private" / "key.json").read_text())
    p1_dis = {t["di"] for part in ("part1", "part2") for t in page1.get(part, {}).values()}
    clips = draw_hum(v1["sections"], man["sections"], p1_dis)
    was = {(r["di"], r["start_s"]) for r in v1["sections"] if r["clean"]}
    moved = {hum_unit(r["di"]) for r in man["sections"] if r["flags"] == ["hum"]
             and "hum_kept_by_fundamental" in r["tags"] and (r["di"], r["start_s"]) in was}
    drawn = {t["unit"] for t in clips if t["kind"] == "kept"}
    print("kept units drawn", len(drawn), "of", len(moved), sorted(moved - drawn))
    assert drawn == moved, "a kept unit has no eligible section"
    key = {"plan": "docs/clean-di-library-plan.md (amendment 3)", "seed": LISTEN2_SEED,
           "manifest_sha256": hashlib.sha256((OUT / "manifest.json").read_bytes()).hexdigest(), "clips": {}}
    s1 = []
    with tempfile.TemporaryDirectory() as tmp:
        for n, t in enumerate(clips, 1):
            x = np.asarray(_clip(t["path"], t["start_s"]), np.float64)
            s1.append(section1(n, BD.pad(BK.aac(BK.fade(BK.level(x)), tmp))))
            key["clips"][str(n)] = t
            print(n, t["kind"], t["value"], t["value_refuted"], t["di"], t["start_s"], flush=True)
    build = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]
    page = PAGE.format(part1="\n".join(s1), part2_block="", build=build)
    page = page.replace("Part 1: what do you hear?", "What do you hear?").replace(
        "Part 1 items read like", "Items read like").replace(
        "; part 2 items like <code>H1A-no</code> (A has less hum, the guitar sounds\nno different)", "")
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", page).lower()
    words = {"telefunken", "cambridge", "elecgtr", "gtr ", "techs", "directinput", "repeat", "flagged",
             "refuted", "anchor", "kept", "fundamental"}
    words |= {t["di"].lower() for t in clips} | {pathlib.Path(t["path"]).stem.lower() for t in clips}
    for w in words:
        assert w not in text, w
    uris = re.findall(r'src="(data:[^"]+)"', page)
    assert len(uris) == len(set(uris)) == len(clips), "duplicate or missing clip bytes"
    (LISTEN2 / "private").mkdir(parents=True, exist_ok=True)
    kfile.write_text(json.dumps(key, indent=1))
    out = LISTEN2 / "di-hum.html"
    out.write_text(page)
    print(out, f"{out.stat().st_size / 1e6:.2f} MB", "clips", len(uris))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inventory")
    s = sub.add_parser("screen")
    s.add_argument("--only", nargs="*", default=None, help="substrings of DI ids")
    sub.add_parser("manifest")
    sub.add_parser("hum-fix")
    sub.add_parser("hum-amend")
    li = sub.add_parser("listen")
    li.add_argument("step", choices=("build", "score"))
    li.add_argument("--answers", default="")
    li.add_argument("--force", action="store_true")
    lh = sub.add_parser("listen-hum")
    lh.add_argument("step", choices=("build", "score"))
    lh.add_argument("--answers", default="")
    lh.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    {"inventory": cmd_inventory, "screen": cmd_screen, "manifest": cmd_manifest, "hum-fix": cmd_hum_fix,
     "hum-amend": cmd_hum_amend, "listen": cmd_listen, "listen-hum": cmd_listen_hum}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
