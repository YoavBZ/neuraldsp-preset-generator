"""The rebuild gap (`docs/rebuild-gap-plan.md`): where C′ loses local ranking from a perfect stem,
and a training change judged on rendered ranking. Development only; estimates with 90%
band-clustered intervals, no pass/fail bars.

    .venv/bin/python -m learn.rebuild_gap where                       # A1, zero renders
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.rebuild_gap rescore   # A2, zero renders (stored FLACs)
    .venv/bin/python -m learn.rebuild_gap probes                      # build + check the probe DIs
    .venv/bin/python -m learn.rebuild_gap metrics                     # A3/A4 (reads B0 if present)
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.rebuild_gap choose-rot --shard i/3   # 216 renders
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.rebuild_gap render --probe all --shard i/3
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.rebuild_gap score --workers 3
    .venv/bin/python -m learn.rebuild_gap report --stage r1           # R1 + the R2 extension list
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.rebuild_gap render --stage r2 --shard i/3
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.rebuild_gap render --probe arm_rank,arm_ctl --stage tr1 --shard i/3
    .venv/bin/python -m learn.rebuild_gap report --stage tr

The torch side (the proxy amp bank, B0, stage T's fine-tune, the arms' rebuilds) is
`learn/rebuild_gap_train.py`. The pure parts (cells, families, alignment, the probes, scoring
configurations, the rules, the gates) are unit-tested; the commands that render are not, like the
other step modules.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import pathlib
import random
import re
import statistics
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import arm_a_levers as L  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import song_readout as SRD  # noqa: E402

OUT = K.HOME / "learn/rebuild-gap"
SR = 48000
HALVES = LO.HALVES
OBJ_LAG = L.OBJ_LAG                       # −52: the rebuilt objective's lag
CHECK_TOL = LO.CHECK_TOL                  # 0.005 (log)

# --- the probes (stage R) -----------------------------------------------------------------------------
PROBES = ("reb", "rot", "t_rot", "mag", "phase", "low", "mid", "high", "onset", "sustain", "half", "noise",
          "dep_eq", "dep_rot")
# Each probe's paired anchor (amendment 1): the composites against `rot` (the rotation-aligned
# rebuild), `rot` and the deployable probes against `reb`, and `t_rot` (the true DI carrying the
# rebuild's rotation) against the truth itself.
ANCHOR = {"reb": None, "rot": "reb", "t_rot": "truth", "dep_eq": "reb", "dep_rot": "reb",
          **{p: "rot" for p in ("mag", "phase", "low", "mid", "high", "onset", "sustain", "half", "noise")}}
ARMS = ("arm_rank", "arm_ctl")            # stage TR: the fine-tuned networks' rebuilds of the amp track
FAMILY_CONTRASTS = (("mag", "phase"), ("low", "mid"), ("low", "high"), ("mid", "high"), ("onset", "sustain"),
                    ("noise", "rot"), ("half", "rot"), ("rot", "reb"), ("dep_rot", "reb"), ("dep_eq", "reb"),
                    ("t_rot", "truth"))
ROTATIONS = 8                             # dep_rot's choices: k · 45°
ALIGN_WINDOW = 100                        # samples around judge_lag
ALIGN_BAND = (80.0, 2000.0)
MIN_ABS_C, MIN_COH = 0.3, 0.3             # a part below either fails the probe check
MIX_TOL_DB = 3.0
NOISE_BANDS = 16                          # log-spaced, 50 Hz–16 kHz, for noise's calibration
NOISE_TOL_DB = 0.5
MAG_ITERS = 8
N_STFT, HOP = 1024, 256
BAND_EDGES = (500.0, 2000.0)
XOVER_OCT = 1 / 3                         # raised-cosine crossover width (octaves)
ONSET_PRE, ONSET_POST, ONSET_FADE = 0.002, 0.015, 0.002     # amendment 1: attack only
PROBE_LU_TOL = 0.05
MASK_SUM_TOL = 1e-9
ROUNDTRIP_TOL = 1e-6
CELL_SEED = "rebuild-gap|cells"
NOISE_SEED = "rebuild-gap|noise|{slug}"

# --- the machine -------------------------------------------------------------------------------------
CAP = 3
MY_RENDERS = (r"-m learn\.rebuild_gap (render|choose-rot)\b",)
FOREIGN_RENDERS = (*LO.RENDERS, r"-m learn\.arm_a_mega53 search\b")
MEGA = K.HOME / "learn/arm-a-mega53"
MEGA_LOG = MEGA / "logs/run.log"
MEGA_PROCS = (r"-m learn\.arm_a_mega53\b", r"arm_a_mega53_run\.zsh")
# The Mega-53 runner's terminal lines (amendment 1, item 7); "STAGE D: a shard failed", "REPORT D
# FAILED" and "REBUILD X FAILED" are not terminal. Only lines after the latest "start pid" count.
MEGA_ENDED = ("all done", "stage F not started", "STAGE F: a shard failed", "REPORT F FAILED", "DECIDE-X FAILED")
# Stage T trains only on "lane A done:" (the coordinator's gate, 2026-10-17); a lane-A failure or a
# failed decide-x means asking the coordinator first, so those only raise an alert.
LANE_A_DONE = ("lane A done:",)
LANE_A_FAILED = ("LANE A FAILED", "DECIDE-X FAILED")
DISK_GUARD_GB = LO.DISK_GUARD_GB
MB_PER_RENDER = LO.MB_PER_RENDER


def _seed_int(text):
    return int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)


# --- cells ---------------------------------------------------------------------------------------------

def probe_cells(parts, amps=K.AMPS, seed=CELL_SEED):
    """One amp per part, balanced: the parts sorted, the amps repeated to cover them and shuffled by
    `random.Random(seed)`. -> {slug: amp}."""
    parts = sorted(parts)
    pool = [amps[i % len(amps)] for i in range(len(parts))]
    random.Random(seed).shuffle(pool)
    return dict(zip(parts, pool))


def r1_cells(parts=None):
    ps = parts if parts is not None else [s for s in K.parts() if s not in LO.EXCLUDED]
    return sorted(probe_cells(ps).items())


def r2_cells(parts=None):
    """The other 48 cells (both other amps of every part)."""
    ps = parts if parts is not None else [s for s in K.parts() if s not in LO.EXCLUDED]
    one = probe_cells(ps)
    return sorted((s, a) for s in ps for a in K.AMPS if a != one[s])


# --- A1: knob families -----------------------------------------------------------------------------------

GAIN_STAGING = ("pr12Volume", "sw50rVolume", "sw50rLevel", "sw50rInputMode", "ac20Volume", "ac20Power")


def knob_family(name):
    """'input gain', 'amp gain', 'amp tone' or 'cab' for a Dim name ('module/key')."""
    mod, key = name.rsplit("/", 1)
    if key == "inputGain":
        return "input gain"
    if mod == "cabParameters":
        return "cab"
    if key in GAIN_STAGING:
        return "amp gain"
    return "amp tone"


def pair_family(dims, x, y, share=0.5):
    """The family holding more than `share` of the pair's squared unit-scale move (a categorical or
    switch difference counts 1); 'mixed' otherwise; None for identical settings."""
    by = {}
    for d in dims:
        if d.kind in ("cat", "switch"):
            m = 0.0 if x.get(LO._k(d)) == y.get(LO._k(d)) else 1.0
        else:
            m = (L.unit(d, x) - L.unit(d, y)) ** 2
        by[knob_family(d.name)] = by.get(knob_family(d.name), 0.0) + m
    tot = sum(by.values())
    if tot <= 0:
        return None
    fam, v = max(by.items(), key=lambda kv: kv[1])
    return fam if v > share * tot else "mixed"


def swap(obj):
    """{"A": a, "B": b} -> {"A": b, "B": a}: the objective read on the other half (cross-half)."""
    return {"A": obj["B"], "B": obj["A"]}


def concordance(pairs, obj, true):
    """Pairwise concordance on (i, j) pairs, objective on each half against the truth on the other
    (cross-half), true ties and refusals skipped, a tie in the objective half. -> (value, pairs)."""
    accs, n = [], 0
    for h in HALVES:
        o, t = obj[LO.other(h)], true[h]
        m = c = 0.0
        for i, j in pairs:
            if not (LO._pos(t[i]) and LO._pos(t[j]) and LO._finite(o[i]) and LO._finite(o[j])):
                continue
            s = LO._sign(t[i] - t[j])
            if s == 0:
                continue
            m += 1
            c += 1.0 if LO._sign(o[i] - o[j]) == s else 0.5 if o[i] == o[j] else 0.0
        accs.append(c / m if m else None)
        n = max(n, int(m))
    return LO._mean(accs), n


def family_measures(points, dims, obj, true, S):
    """A1 for one configuration on one cell: per knob family, the cross-half 3-way neighbourhood
    agreement (and chance), pairwise concordance by dominant family on all of Σ, and by drive (pairs
    both above or both below S's input gain). -> dict."""
    fam_of = {d.name: knob_family(d.name) for d in dims}
    tw = LO.three_way(points, swap(obj), true)                     # obj on h', truth on h
    three = {}
    for dim, v in tw.items():
        three.setdefault(fam_of.get(dim, "other"), []).extend(v)
    xs = [p["x"] for p in points]
    pairs = {}
    for i, j in itertools.combinations(range(len(xs)), 2):
        f = pair_family(dims, xs[i], xs[j])
        if f:
            pairs.setdefault(f, []).append((i, j))
    ig = next(d for d in dims if LO._k(d) == LO.INPUT_GAIN)
    s_ig = L.unit(ig, S)
    u = [L.unit(ig, x) for x in xs]
    drive = {"above": [(i, j) for i, j in itertools.combinations(range(len(xs)), 2) if u[i] > s_ig and u[j] > s_ig],
             "below": [(i, j) for i, j in itertools.combinations(range(len(xs)), 2) if u[i] < s_ig and u[j] < s_ig]}
    return {"three_way": {f: (statistics.fmean(a for a, _, _ in v), statistics.fmean(c for _, _, c in v), len(v))
                          for f, v in three.items() if v},
            "by_family": {f: concordance(p, obj, true) for f, p in pairs.items()},
            "by_drive": {k: concordance(p, obj, true) for k, p in drive.items()}}


# --- alignment and the probes (zero renders) ---------------------------------------------------------------

def shift(x, k):
    """x delayed by k samples (k < 0: advanced), zero-padded, same length."""
    import numpy as np

    x = np.asarray(x)
    out = np.zeros_like(x)
    if k == 0:
        return x.copy()
    if abs(k) >= len(x):
        return out
    if k > 0:
        out[k:] = x[:-k]
    else:
        out[:k] = x[-k:]
    return out


def analytic(x, band=ALIGN_BAND):
    """The analytic signal of x band-passed to `band` (4th-order Butterworth, zero-phase)."""
    from scipy.signal import butter, hilbert, sosfiltfilt

    sos = butter(4, list(band), btype="band", fs=SR, output="sos")
    return hilbert(sosfiltfilt(sos, x))


def analytic_xcorr(r, t, lags, band=ALIGN_BAND):
    """The normalised complex correlation of r's and t's analytic signals at each lag k (r(n) against
    t(n − k)): its magnitude is invariant to a constant phase rotation, its angle is the rotation."""
    import numpy as np

    ra, ta = analytic(r, band), analytic(t, band)
    n = len(r)
    out = []
    for k in lags:
        a, b = (ra[k:], ta[:n - k]) if k >= 0 else (ra[:n + k], ta[-k:])
        out.append(np.sum(a * np.conj(b)) / math.sqrt(np.sum(np.abs(a) ** 2) * np.sum(np.abs(b) ** 2) + 1e-30))
    return np.array(out)


def rotate(x, phi):
    """x with a constant phase rotation φ at every frequency: Re{(x + iH(x)) e^{iφ}}."""
    import numpy as np
    from scipy.signal import hilbert

    return np.real(hilbert(np.asarray(x, np.float64)) * np.exp(1j * phi))


def align(r, t, judge_lag, window=ALIGN_WINDOW):
    """The rebuild r moved onto t's timeline (amendment 1): the lag within ±`window` of the part's
    judge_lag maximising the analytic correlation's magnitude in 80 Hz–2 kHz, and the constant phase
    rotation φ there (r ≈ rotate(t, φ) after the shift). -> (r on t's timeline, lag, φ, |c|)."""
    import numpy as np

    n = min(len(r), len(t))
    r, t = np.asarray(r[:n], np.float64), np.asarray(t[:n], np.float64)
    lags = np.arange(int(judge_lag) - window, int(judge_lag) + window + 1)
    c = analytic_xcorr(r, t, lags)
    i = int(np.argmax(np.abs(c)))
    return shift(r, -int(lags[i])), int(lags[i]), float(np.angle(c[i])), float(np.abs(c[i]))


def stft(x):
    from scipy.signal import stft as _stft

    return _stft(x, fs=SR, window="hann", nperseg=N_STFT, noverlap=N_STFT - HOP, boundary="zeros", padded=True)


def istft(Z, n):
    from scipy.signal import istft as _istft

    _, x = _istft(Z, fs=SR, window="hann", nperseg=N_STFT, noverlap=N_STFT - HOP, boundary=True)
    out = x[:n]
    if len(out) < n:
        import numpy as np

        out = np.concatenate([out, np.zeros(n - len(out))])
    return out


def band_masks(freqs, edges=BAND_EDGES, width=XOVER_OCT):
    """Complementary low/mid/high weights over `freqs` (sum to 1), raised-cosine crossovers `width`
    octaves wide centred on each edge."""
    import numpy as np

    lf = np.log2(np.maximum(freqs, 1.0))

    def up(edge):                                       # 0 below, 1 above, a cosine ramp between
        z = np.clip((lf - math.log2(edge)) / width + 0.5, 0.0, 1.0)
        return 0.5 - 0.5 * np.cos(math.pi * z)

    a, b = up(edges[0]), up(edges[1])
    return 1 - a, a - b, b


def onset_weights(t, sr=SR, pre=ONSET_PRE, post=ONSET_POST, fade=ONSET_FADE):
    """Weights in [0, 1] over t's samples: 1 inside onset windows [onset − pre, onset + post], cosine
    fades of `fade` outside them. Onsets: peaks of t's half-wave-rectified log spectral flux (hop
    256) above a moving median + 1.5 MAD, at least 50 ms apart, within 40 dB of the loudest frame.
    -> (weights, onset sample positions)."""
    import numpy as np
    from scipy.ndimage import median_filter

    f, tt, Z = stft(t)
    m = np.log1p(np.abs(Z) * 1000)
    flux = np.maximum(np.diff(m, axis=1), 0).sum(0)
    flux = np.concatenate([[0.0], flux])
    e = 10 * np.log10((np.abs(Z) ** 2).sum(0) + 1e-20)
    med = median_filter(flux, size=31, mode="nearest")
    mad = median_filter(np.abs(flux - med), size=31, mode="nearest")
    thr = med + 1.5 * mad + 1e-9
    gap = int(round(0.05 * sr / HOP))
    on = []
    for k in range(1, len(flux) - 1):
        if flux[k] > thr[k] and flux[k] >= flux[k - 1] and flux[k] >= flux[k + 1] and e[k] >= e.max() - 40:
            if not on or k - on[-1] >= gap:
                on.append(k)
    pos = [int(k * HOP) for k in on]
    w = np.zeros(len(t))
    nf = max(1, int(round(fade * sr)))
    ramp = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, nf))
    for p in pos:
        a, b = max(0, p - int(pre * sr)), min(len(t), p + int(post * sr))
        w[a:b] = 1.0
        lo = max(0, a - nf)
        w[lo:a] = np.maximum(w[lo:a], ramp[nf - (a - lo):])
        hi = min(len(t), b + nf)
        w[b:hi] = np.maximum(w[b:hi], ramp[::-1][:hi - b])
    return w, pos


def band_db(Z, f, edges):
    """Per band and frame, 10·log10 of the summed STFT power (bands [edges[i], edges[i+1]))."""
    import numpy as np

    P = np.abs(Z) ** 2
    return np.stack([10 * np.log10(P[(f >= a) & (f < b)].sum(0) + 1e-20) for a, b in zip(edges[:-1], edges[1:])])


def band_error_db(Zx, Zt, f, edges, active):
    """Per band, the mean |ΔdB| of x's band levels against t's over t's active frames."""
    import numpy as np

    return np.abs(band_db(Zx, f, edges) - band_db(Zt, f, edges))[:, active].mean(1)


def noise_edges(lo=50.0, hi=16000.0, n=NOISE_BANDS):
    import numpy as np

    return np.geomspace(lo, hi, n + 1)


def calibrated_noise(T, R, f, rng, iters=30):
    """`noise` (amendment 1, item 4): random-phase noise with |R − T|'s STFT magnitude, scaled per
    band (16 log-spaced, 50 Hz–16 kHz) by bisection so that T + N's band-level error to T equals
    R's (mean |ΔdB| over T's active frames). -> (N's STFT, target errors, reached errors)."""
    import numpy as np

    edges = noise_edges()
    e = 10 * np.log10((np.abs(T) ** 2).sum(0) + 1e-20)
    active = e >= e.max() - 40
    target = band_error_db(R, T, f, edges, active)
    N0 = np.abs(R - T) * np.exp(2j * math.pi * rng.random(T.shape))
    gains = np.ones(len(edges) - 1)
    for b, (a, c) in enumerate(zip(edges[:-1], edges[1:])):
        m = (f >= a) & (f < c)
        if not m.any():
            continue
        lo, hi = 0.0, 8.0
        for _ in range(iters):
            g = 0.5 * (lo + hi)
            Z = T[m] + g * N0[m]
            err = np.abs(10 * np.log10((np.abs(Z) ** 2).sum(0) + 1e-20)
                         - 10 * np.log10((np.abs(T[m]) ** 2).sum(0) + 1e-20))[active].mean()
            lo, hi = (g, hi) if err < target[b] else (lo, g)
        gains[b] = 0.5 * (lo + hi)
    G = np.ones(len(f))
    for b, (a, c) in enumerate(zip(edges[:-1], edges[1:])):
        G[(f >= a) & (f < c)] = gains[b]
    N = G[:, None] * N0
    return N, target, band_error_db(T + N, T, f, edges, active)


def interp(T, R, m):
    """A per-bin blend of two STFTs that cannot cancel (amendment 1, item 3): log-magnitude and
    phase interpolated, |T|^m |R|^(1−m) e^{i(∠R + m·wrap(∠T − ∠R))}; m = 1 gives T, m = 0 gives R."""
    import numpy as np

    m = np.asarray(m, np.float64)
    m = m[:, None] if m.ndim == 1 else m
    mag = np.exp(m * np.log(np.abs(T) + 1e-20) + (1 - m) * np.log(np.abs(R) + 1e-20))
    dphi = np.angle(T * np.conj(R))
    return mag * np.exp(1j * (np.angle(R) + m * dphi))


def consistent_mag(Tmag, phase0, n, iters=MAG_ITERS):
    """A signal with STFT magnitude close to Tmag, starting from phase0 (Griffin–Lim iterations)."""
    import numpy as np

    x = istft(Tmag * np.exp(1j * phase0), n)
    for _ in range(iters):
        _, _, X = stft(x)
        x = istft(Tmag * np.exp(1j * np.angle(X[:, :Tmag.shape[1]])), n)
    return x


def build_probes(r, t, slug, judge_lag, avg=None):
    """Every probe DI (before levelling) from the rebuild r and the measure DI t. Amendment 1: r is
    aligned by `align` (judge_lag-anchored); r̃ = rotate(r on t's timeline, −φ) removes the
    rebuild's constant phase rotation; `t_rot` = rotate(t, φ) gives the truth the rebuild's
    rotation. -> ({probe: array}, info). `dep_rot` is built from the render's choice later."""
    import numpy as np

    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to

    n = min(len(r), len(t))
    t = np.asarray(t[:n], np.float64)
    ra, lag, phi, absc = align(r, t, judge_lag)
    rt = rotate(ra, -phi)                                  # r̃
    f, _, T = stft(t)
    _, _, R = stft(rt)
    lo, mid, hi = band_masks(f)
    out = {"reb": ra, "rot": rt, "t_rot": rotate(t, phi),
           "mag": consistent_mag(np.abs(T), np.angle(R), n),
           "phase": istft(np.abs(R) * np.exp(1j * np.angle(T)), n)}
    for name, m in (("low", lo), ("mid", mid), ("high", hi)):
        out[name] = istft(interp(T, R, m), n)
    w, pos = onset_weights(t)
    out["onset"] = w * t + (1 - w) * rt
    out["sustain"] = (1 - w) * t + w * rt
    H = interp(T, R, np.full(len(f), 0.5))                   # halfway in log-magnitude and phase,
    out["half"] = consistent_mag(np.abs(H), np.angle(H), n)    # made consistent (overlap-add cancels otherwise)
    rng = np.random.default_rng(_seed_int(NOISE_SEED.format(slug=slug)))
    N, target, reached = calibrated_noise(T, R, f, rng)
    out["noise"] = t + istft(N, n)
    if avg is not None:
        own = smoothed_spectrum(ra)
        out["dep_eq"] = eq_to(ra, avg - (own - own.mean()))
    info = {"lag": lag, "lag_minus_judge_lag": lag - int(judge_lag), "phi_deg": math.degrees(phi), "abs_c": absc,
            "coh_80_2k": coherence(rt, t, *ALIGN_BAND), "onsets": len(pos), "onset_coverage": float(w.mean()),
            "noise_target_db": [float(x) for x in target], "noise_reached_db": [float(x) for x in reached],
            "roundtrip_max": float(np.abs(istft(T, n) - t).max()),
            "mask_sum_max": float(np.abs(lo + mid + hi - 1).max())}
    _, _, M = stft(out["mag"])
    info["mag_err_db"] = float(np.mean(np.abs(20 * np.log10(np.abs(M[:, :T.shape[1]]) + 1e-9)
                                              - 20 * np.log10(np.abs(T) + 1e-9))[np.abs(T) > np.abs(T).max() * 1e-3]))
    return out, info


def with_rotation(reb, k, n=ROTATIONS):
    """`dep_rot`: the rebuild on t's timeline rotated by the render's choice k · 360°/n."""
    return reb.copy() if k % n == 0 else rotate(reb, 2 * math.pi * k / n)


MIX_PROBES = ("low", "mid", "high", "onset", "sustain", "half")


def third_octaves(lo=80.0, hi=8000.0):
    import numpy as np

    c = 1000.0 * 2.0 ** (np.arange(-40, 40) / 3)
    return [x for x in c if lo <= x <= hi]


def mix_problems(mix, t, rt, tol=MIX_TOL_DB):
    """Amendment 1, item 3: a mix of t and r̃ must not comb-filter or cancel. In every third-octave
    band from 80 Hz to 8 kHz (the crossover regions included), the mix's long-term level must lie
    within `tol` dB of the range spanned by t's and r̃'s. -> [problem]."""
    import numpy as np

    from learn.di_robustness import N_FFT, smoothed_spectrum

    fr = np.fft.rfftfreq(N_FFT, 1 / SR)
    sm, st, sr_ = (smoothed_spectrum(np.asarray(x, np.float64)) for x in (mix, t, rt))
    out = []
    for fc in third_octaves():
        m = (fr >= fc * 2 ** (-1 / 6)) & (fr < fc * 2 ** (1 / 6))
        if not m.any():
            continue
        a, b, c = (float(np.mean(x[m])) for x in (sm, st, sr_))
        if a < min(b, c) - tol or a > max(b, c) + tol:
            out.append(f"{fc:.0f} Hz: mix {a:.1f} dB outside [{min(b, c):.1f}, {max(b, c):.1f}] ± {tol}")
    return out


def best_snr_db(x, t):
    """Waveform SNR (dB) of x against t at the least-squares gain (sign included)."""
    import numpy as np

    g = float(np.dot(x, t) / (np.dot(x, x) + 1e-20))
    return float(10 * np.log10(np.dot(t, t) / (np.sum((g * x - t) ** 2) + 1e-20)))


def lsd_db(x, t, lo=80.0, hi=8000.0):
    """Long-term log-spectral distance (dB, mean offset removed) over [lo, hi] Hz."""
    import numpy as np

    from learn.di_robustness import smoothed_spectrum

    a, b = smoothed_spectrum(np.asarray(x, np.float64)), smoothed_spectrum(np.asarray(t, np.float64))
    from learn.di_robustness import N_FFT

    fr = np.fft.rfftfreq(N_FFT, 1 / SR)
    m = (fr >= lo) & (fr <= hi)
    d = a[m] - b[m]
    return float(np.sqrt(np.mean((d - d.mean()) ** 2)))


def coherence(x, t, lo, hi):
    """Mean magnitude-squared coherence of x and t over [lo, hi] Hz (Welch, 2,048)."""
    import numpy as np
    from scipy.signal import coherence as _coh

    f, c = _coh(x, t, fs=SR, nperseg=2048)
    m = (f >= lo) & (f < hi)
    return float(np.mean(c[m]))


def crest_db(x, ms):
    """Median over active frames of the peak-to-RMS ratio (dB) in `ms`-long frames."""
    import numpy as np

    n = int(SR * ms / 1000)
    k = len(x) // n
    fr = np.asarray(x[:k * n]).reshape(k, n)
    rms = np.sqrt((fr ** 2).mean(1)) + 1e-12
    act = 20 * np.log10(rms) >= 20 * np.log10(rms.max()) - 40
    return float(np.median(20 * np.log10(np.abs(fr).max(1)[act] / rms[act])))


def quiet_level_db(x, t, n=480):
    """Mean level of x minus t (dB) on t's frames 20–40 dB under t's loudest (both at their own
    loudest-frame reference): positive = gaps filled."""
    import numpy as np

    k = min(len(x), len(t)) // n
    ex = 10 * np.log10((np.asarray(x[:k * n]) ** 2).reshape(k, n).mean(1) + 1e-20)
    et = 10 * np.log10((np.asarray(t[:k * n]) ** 2).reshape(k, n).mean(1) + 1e-20)
    sel = (et <= et.max() - 20) & (et >= et.max() - 40)
    if not sel.any():
        return None
    return float(np.mean((ex[sel] - ex.max()) - (et[sel] - et.max())))


def di_metrics(x, t):
    """A3's metrics of a DI x against the measure DI t (x already on t's timeline)."""
    n = min(len(x), len(t))
    x, t = x[:n], t[:n]
    out = {"snr_db": best_snr_db(x, t), "lsd_db": lsd_db(x, t),
           "coh_80_1k": coherence(x, t, 80, 1000), "coh_1k_3k": coherence(x, t, 1000, 3000),
           "coh_3k_8k": coherence(x, t, 3000, 8000), "quiet_db": quiet_level_db(x, t)}
    for ms in (1, 5, 10):
        out[f"crest{ms}_err_db"] = crest_db(x, ms) - crest_db(t, ms)
    return out


def probe_problems(levels, target_levels, info, tol=PROBE_LU_TOL):
    """The pre-render checks of one part's probes. levels/target_levels: {probe: LUFS} and the part's
    measure-DI LUFS; info: `build_probes`' (alignment gate, noise calibration, masks). -> [problem]."""
    out = []
    if info.get("abs_c", 1.0) < MIN_ABS_C or info.get("coh_80_2k", 1.0) < MIN_COH:
        out.append(f"alignment: |c| {info.get('abs_c')} / 80 Hz–2 kHz coherence {info.get('coh_80_2k')} "
                   f"under {MIN_ABS_C} / {MIN_COH}")
    if abs(info.get("lag_minus_judge_lag", 0)) >= ALIGN_WINDOW:
        out.append(f"alignment: lag at the window's edge ({info.get('lag_minus_judge_lag')} from judge_lag)")
    tg, rc = info.get("noise_target_db") or [], info.get("noise_reached_db") or []
    worst = max((abs(a - b) for a, b in zip(tg, rc)), default=0.0)
    if worst > NOISE_TOL_DB:
        out.append(f"noise calibration off by {worst:.2f} dB in a band")
    for p, l in levels.items():
        if l is None or not math.isfinite(l) or abs(l - target_levels) > tol:
            out.append(f"{p} at {l} LUFS, not within {tol} LU of the measure DI's {target_levels}")
    if info.get("roundtrip_max", 0.0) > ROUNDTRIP_TOL * max(1.0, info.get("t_peak", 1.0)):
        out.append(f"STFT round trip of t off by {info['roundtrip_max']:.2e}")
    if info.get("mask_sum_max", 0.0) > MASK_SUM_TOL:
        out.append(f"band masks off 1 by {info['mask_sum_max']:.2e}")
    return out


# --- scoring ---------------------------------------------------------------------------------------------

def is_arm(name):
    return name in ARMS


def configs(name):
    """Score configurations for renders through a probe or an arm. Probes (on the measure DI's
    timeline): 'decl' — reference.wav, judge_lag, the measure DI as the mask (the truth's own
    configuration with only the DI changed); 'own' — the probe's own mask with the record fallback
    (diagnostic). Arms: 'decl' — 1b's matched configuration (reference.wav, −52, own mask, fallback)."""
    return ("decl",) if is_arm(name) else ("decl", "own")


def score_one(y, name, sig, judge_lag, aligned, only=None):
    """{config: {"A": d, "B": d}} for one render. sig: {"di", "measure", "reference"}. A refusal is
    inf; the own mask falls back to the reference moved into DI time on an activity refusal."""
    from learn.rebuilt_judge import _ACTIVITY

    out = {}
    rec = sig["reference"]
    lag = OBJ_LAG if is_arm(name) else judge_lag
    for c in configs(name):
        if only is not None and c not in only:
            continue
        row = {}
        for h, (a, b) in K.R.HALVES.items():
            if c == "decl" and not is_arm(name):
                d, _ = aligned(rec, y, sig["measure"], lag, a, b)
            else:
                d, why = aligned(rec, y, sig["di"], lag, a, b)
                if d is None and any(w in (why or "") for w in _ACTIVITY):
                    d, _ = aligned(rec, y, LO.in_di_time(rec, lag), lag, a, b)
            row[h] = math.inf if d is None else d
        out[c] = row
    return out


# --- the machine: gates -------------------------------------------------------------------------------

def _matches(cmd, pats):
    from learn import ks_extend as X

    return X._is_python(cmd) and any(re.search(p, cmd) for p in pats)


def render_count(ps, own=()):
    return len([p for p, c in ps if p not in own and (_matches(c, FOREIGN_RENDERS) or _matches(c, MY_RENDERS))])


def mega_running(ps, own=()):
    """Any Mega-53 song-test process (its python modules, or its runner's zsh)."""
    return [p for p, c in ps if p not in own and any(re.search(q, c) for q in MEGA_PROCS)]


def current_run(text):
    """The lines after the latest "start pid" line (the runner's log is appended)."""
    lines = (text or "").splitlines()
    starts = [i for i, l in enumerate(lines) if "start pid" in l]
    return lines[starts[-1]:] if starts else []


def log_has(text, needles):
    return any(any(n in l for n in needles) for l in current_run(text))


def mega_ended(ps, log_text, own=()):
    """Stage R may render: the Mega-53 runner's current run shows a terminal line and none of its
    processes run."""
    return log_has(log_text, MEGA_ENDED) and not mega_running(ps, own)


def lane_a_done(log_text):
    """Stage T may train: lane A (the separations) has finished in the runner's current run."""
    return log_has(log_text, LANE_A_DONE)


def lane_a_failed(log_text):
    """Lane A failed or will never run: stage T waits for the coordinator (an alert, no start)."""
    return log_has(log_text, LANE_A_FAILED)


def mega_vanished(ps, log_text, own=()):
    """The runner is gone without a terminal line: alert, don't start."""
    return bool(current_run(log_text)) and not log_has(log_text, MEGA_ENDED) and not mega_running(ps, own)


def _ps():
    from learn import ks_extend as X

    return X._ps()


def _own():
    return {os.getpid(), os.getppid()}


def _read(p):
    try:
        return pathlib.Path(p).read_text()
    except OSError:
        return ""


def wait_mega(poll=60):
    alerted = False
    while not mega_ended(_ps(), _read(MEGA_LOG), _own()):
        if mega_vanished(_ps(), _read(MEGA_LOG), _own()) and not alerted:
            OUT.mkdir(parents=True, exist_ok=True)
            K._atomic(OUT / "ALERT.json", {"why": "the Mega-53 runner is gone without a terminal line; not starting",
                                           "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            print("ALERT: the Mega-53 runner is gone without a terminal line; waiting", flush=True)
            alerted = True
        time.sleep(poll)


def wait_lane_a(poll=60):
    """Block until lane A is done; on its failure write ALERT.json once and keep waiting (the
    coordinator decides)."""
    alerted = False
    while not lane_a_done(_read(MEGA_LOG)):
        if lane_a_failed(_read(MEGA_LOG)) and not alerted:
            OUT.mkdir(parents=True, exist_ok=True)
            K._atomic(OUT / "ALERT.json", {"why": "Mega-53 lane A failed (or decide-x did): stage T waits for the coordinator",
                                           "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            print("ALERT: lane A failed; stage T waits for the coordinator", flush=True)
            alerted = True
        time.sleep(poll)


def wait_cap(cap=CAP, poll=60):
    while render_count(_ps(), _own()) >= cap:
        time.sleep(poll)


def stop_paths():
    return (OUT / "STOP.json", LO.stop_path())


def check_stop():
    for p in stop_paths():
        if p.exists():
            raise SystemExit(f"stopped: {p}: {p.read_text()}")


def breakage(rec_path, rec, why):
    K._atomic(rec_path, {**rec, "status": "check_failed", "why": why})
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "STOP.json", {"why": why, "slug": rec["slug"], "amp": rec["amp"], "probe": rec["probe"],
                                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    raise SystemExit(f"{why}: every shard stops; investigate, then delete {OUT / 'STOP.json'}")


# --- the rules ------------------------------------------------------------------------------------------

def projected_excludes_zero(contrast, ratio):
    """Amendment 1, item 5: would the interval, narrowed by `ratio` (the all-cells / R1-cells
    half-width ratio of stored contrasts), exclude 0 at the same estimate?"""
    m, lo, hi = contrast.get("band_weighted_mean"), contrast.get("lo90"), contrast.get("hi90")
    if m is None or lo is None or ratio is None:
        return False
    return abs(m) > ratio * (hi - lo) / 2


def extends(contrast, ratio):
    """R1 → R2 (and TR1 → TR2): a positive estimate whose 90% interval contains 0 now and whose
    projected all-cells interval would exclude it."""
    m, lo, hi = contrast.get("band_weighted_mean"), contrast.get("lo90"), contrast.get("hi90")
    return (m is not None and lo is not None and m > 0 and lo <= 0 <= hi
            and projected_excludes_zero(contrast, ratio))


def with_anchors(names):
    need = set()
    for p in names:
        while p and p in ANCHOR:
            need.add(p)
            p = ANCHOR[p]
    return [p for p in PROBES if p in need]


def r2_list(contrasts, families, ratio):
    """contrasts: {probe: probe − anchor}; families: {"a-b": a − b} -> the probes R2 renders on the
    other 48 cells (with their anchors). A family contrast that meets the rule extends both members;
    only positive gains extend (`extends`), so a family contrast is read in its positive direction."""
    names = [p for p, c in contrasts.items() if extends(c, ratio)]
    for k, c in families.items():
        a, b = k.split("-", 1)
        flip = {kk: (-v if kk == "band_weighted_mean" else v) for kk, v in c.items()}
        if c.get("band_weighted_mean") is not None and c.get("lo90") is not None:
            flip["lo90"], flip["hi90"] = -c["hi90"], -c["lo90"]
        if extends(c, ratio) or extends(flip, ratio):
            names += [x for x in (a, b) if x in PROBES]
    return with_anchors(names)


def tr2_due(rank_vs_cprime, ratio):
    return extends(rank_vs_cprime, ratio)


# --- data access -----------------------------------------------------------------------------------------

def probe_path(probe, slug):
    if is_arm(probe):
        return OUT / "arms" / probe / f"{slug}.npy"
    return OUT / "probes" / probe / f"{slug}.npy"


def signals(slug, probe):
    import numpy as np

    from learn import confirm_run as CR

    part = K.parts()[slug]
    return {"di": np.load(probe_path(probe, slug)), "measure": K.measure_di(part),
            "reference": CR.mono(part["crop"] / "reference.wav")}, part


def _render_paths(probe, slug, amp):
    d = OUT / "renders" / probe / slug / amp
    return d, OUT / "renders" / probe / slug / f"{amp}.json"


def _done(probe, slug, amp):
    p = _render_paths(probe, slug, amp)[1]
    return p.exists() and json.loads(p.read_text()).get("status") in ("done", "same_as_reb")


def stored_scores(di, slug, amp):
    return json.loads((LO.OUT / "scores" / di / slug / f"{amp}.json").read_text())["scores"]


def probes_ok():
    p = OUT / "probes" / "check.json"
    return p.exists() and json.loads(p.read_text()).get("ok")


def arms_ok():
    p = OUT / "arms" / "check.json"
    return p.exists() and json.loads(p.read_text()).get("ok")


# --- commands: stage A -------------------------------------------------------------------------------------

def cmd_where():
    """A1: knob families, pair families and drive for the matched cell (1b), today's objective and
    the truth's own cross-half order, on all of Σ from the stored scores. Writes where.json."""
    meta, sig = LO.load_sigma()
    ms, ps = L.menu_S(), K.parts()
    rows = {}
    for (slug, amp), pts in sorted(sig.items()):
        S = ms[amp][ps[slug]["gain_class"]][1]
        dims = K.space(amp, S)
        true = LO._vals(stored_scores("measure", slug, amp), LO.TRUE)
        cfgs = {"matched": LO._vals(stored_scores("cprime_ref", slug, amp), LO.MATCHED),
                "current": LO._vals(stored_scores("cprime", slug, amp), LO.CURRENT),
                "truth": true}
        rows[f"{slug}|{amp}"] = {k: family_measures(pts, dims, v, true, S) for k, v in cfgs.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "where-cells.json", rows)
    K._atomic(OUT / "where.json", summarise_where(rows, ps))
    print(json.dumps(summarise_where(rows, ps)["summary"], indent=1)[:4000])


def _agg_rows(rows, ps, pick):
    """{cell key: value} via pick(cell measures) -> LO.agg rows."""
    out = {}
    for key, m in rows.items():
        slug, amp = key.split("|")
        v = pick(m)
        if v is not None:
            out[(slug, amp)] = (slug, ps[slug]["band"], ps[slug]["gain_class"], v)
    return out


def _brief(a):
    keys = ("band_weighted_mean", "lo90", "hi90", "bands", "bands_positive", "bands_negative", "cells")
    return {k: a.get(k) for k in keys}


def summarise_where(rows, ps):
    fams = ("input gain", "amp gain", "amp tone", "cab")
    out = {"three_way": {}, "by_family": {}, "by_drive": {}}
    for f in fams:
        for name in ("matched", "current", "truth"):
            r = _agg_rows(rows, ps, lambda m: m[name]["three_way"].get(f, (None,))[0])
            out["three_way"].setdefault(f, {})[name] = _brief(LO.agg(r))
        gap = LO.paired(_agg_rows(rows, ps, lambda m: m["truth"]["three_way"].get(f, (None,))[0]),
                        _agg_rows(rows, ps, lambda m: m["matched"]["three_way"].get(f, (None,))[0]))
        out["three_way"][f]["truth_minus_matched"] = _brief(LO.agg(gap))
        out["three_way"][f]["chance"] = _brief(LO.agg(_agg_rows(rows, ps, lambda m: m["truth"]["three_way"].get(f, (None, None))[1])))
    for f in (*fams, "mixed"):
        for name in ("matched", "current", "truth"):
            r = _agg_rows(rows, ps, lambda m: (m[name]["by_family"].get(f) or (None,))[0])
            out["by_family"].setdefault(f, {})[name] = _brief(LO.agg(r))
        gap = LO.paired(_agg_rows(rows, ps, lambda m: (m["truth"]["by_family"].get(f) or (None,))[0]),
                        _agg_rows(rows, ps, lambda m: (m["matched"]["by_family"].get(f) or (None,))[0]))
        out["by_family"][f]["truth_minus_matched"] = _brief(LO.agg(gap))
    for k in ("above", "below"):
        for name in ("matched", "current", "truth"):
            r = _agg_rows(rows, ps, lambda m: m[name]["by_drive"][k][0])
            out["by_drive"].setdefault(k, {})[name] = _brief(LO.agg(r))
    summary = {f"3way {f}": (out["three_way"][f]["matched"]["band_weighted_mean"],
                             out["three_way"][f]["truth"]["band_weighted_mean"]) for f in fams}
    summary.update({f"pairs {f}": (out["by_family"][f]["matched"]["band_weighted_mean"],
                                   out["by_family"][f]["truth"]["band_weighted_mean"]) for f in (*fams, "mixed")})
    out["summary"] = summary
    return out


A2_DIS = ("cprime_mega53", "csep_stem", "csep_mega53")


def _rescore_cell(args):
    di, slug, amp, root = args
    import numpy as np

    from learn import confirm_run as CR

    folder, rec_path = LO._render_paths(di, slug, amp)
    rec = json.loads(rec_path.read_text())
    part = K.parts()[slug]
    sig = {"di": np.load(LO.OUT / LO.REBUILD_DIR[di] / f"{slug}.npy"),
           "reference": CR.mono(part["crop"] / "reference.wav")}
    aligned = LO.judge_fns()
    scores = []
    for i, sc in enumerate(rec["scales"]):
        y = LO.load_flac(folder / f"{i:02d}.flac", sc)
        s = score_one(y, "arm_rank", sig, part["judge_lag"], aligned)  # arms' config = 1b's matched one
        scores.append(s["decl"])
    out = pathlib.Path(root) / "rescore" / di / slug / f"{amp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    K._atomic(out, {"scores": scores, "config": "reference|-52|own+fallback", "sigma": rec["sigma"]})
    return di, slug, amp


def cmd_rescore(workers=1):
    """A2: 1c's and 1d's stored rebuild renders scored against reference.wav at −52, own mask with
    the record fallback (1b's matched configuration). Zero renders."""
    from concurrent.futures import ProcessPoolExecutor

    meta, sig = LO.load_sigma()
    ident = OUT / "rescore" / "identity.json"
    if not ident.exists():                      # the scorer reproduces 1b's stored matched scores
        slug, amp = sorted(sig)[0]
        _rescore_cell(("cprime_ref", slug, amp, str(OUT)))
        mine = json.loads((OUT / "rescore" / "cprime_ref" / slug / f"{amp}.json").read_text())["scores"]
        st = stored_scores("cprime_ref", slug, amp)
        dev = max(LO.deviation(m[h], s_[LO.cname(LO.MATCHED)][h]) for m, s_ in zip(mine, st) for h in HALVES)
        K._atomic(ident, {"cell": [slug, amp], "max_dev": dev, "ok": dev <= 1e-9})
        if dev > 1e-9:
            raise SystemExit(f"rescoring 1b's renders moved {dev} from its stored matched scores")
    todo = [(d, s, a, str(OUT)) for d in A2_DIS for (s, a) in sorted(sig)
            if LO._done(d, s, a) and not (OUT / "rescore" / d / s / f"{a}.json").exists()]
    if workers <= 1:
        for t in todo:
            print("rescored", *_rescore_cell(t)[:3], flush=True)
        return
    with ProcessPoolExecutor(workers) as ex:
        for d, s, a in ex.map(_rescore_cell, todo):
            print("rescored", d, s, a, flush=True)


VARIANT_SOURCES = {"cprime": "stem", "cprime_ref": "reference", "cprime_mega53": "mega53",
                   "csep_stem": "stem", "csep_mega53": "mega53"}


def variant_di(v, slug):
    import numpy as np

    from learn import song_settings as SS

    if v == "cprime":
        return np.load(SS.OUT / "rebuilt" / f"{slug}.npy")
    return np.load(LO.OUT / LO.REBUILD_DIR[v] / f"{slug}.npy")


def variant_fidelity(v, slug, amp):
    """Cross-half fidelity of a rebuild against the amp track on one cell (stored or rescored)."""
    true = LO._vals(stored_scores("measure", slug, amp), LO.TRUE)
    if v == "cprime":
        obj = LO._vals(stored_scores("cprime", slug, amp), ("cprime", "reference", "native", "own"))
    elif v == "cprime_ref":
        obj = LO._vals(stored_scores("cprime_ref", slug, amp), LO.MATCHED)
    else:
        p = OUT / "rescore" / v / slug / f"{amp}.json"
        if not p.exists():
            return None
        sc = json.loads(p.read_text())["scores"]
        obj = {h: [s[h] for s in sc] for h in HALVES}
    return LO.cross_half(obj, true)


def within_part_assoc(table, metric, fid="fidelity", min_n=3):
    """table: [{"slug", "band", "variant", metric, fid}] -> per part, the Spearman of the metric with
    the fidelity across its variants; band-weighted with the interval (`song_readout.bw_stats`)."""
    from scipy.stats import spearmanr

    by = {}
    for r in table:
        if r.get(metric) is not None and r.get(fid) is not None:
            by.setdefault((r["slug"], r["band"]), []).append((r[metric], r[fid]))
    rows = []
    for (slug, band), v in by.items():
        if len(v) >= min_n and len({a for a, _ in v}) > 1 and len({b for _, b in v}) > 1:
            rho = spearmanr(*zip(*v)).correlation
            if rho is not None and math.isfinite(rho):
                rows.append((band, float(rho)))
    return SRD.bw_stats(rows)


def cmd_metrics():
    """A3 and A4: per (rebuild, part) DI metrics against the measure DI (each rebuild on the measure
    DI's timeline, its own rotation), the rendered fidelity against the amp track (part means over
    amps), and their within-part and across-part associations; B0's proxy fidelity if present."""
    import numpy as np

    meta, sig = LO.load_sigma()
    ps = K.parts()
    b0 = json.loads((OUT / "b0.json").read_text()) if (OUT / "b0.json").exists() else {}
    table = []
    for slug in sorted(s for s in ps if s not in LO.EXCLUDED):
        t = K.measure_di(ps[slug])
        for v in VARIANT_SOURCES:
            r = variant_di(v, slug)
            ra, lag, phi, absc = align(r, t, ps[slug]["judge_lag"])
            fids = [variant_fidelity(v, slug, a) for a in K.AMPS]
            fids = [f for f in fids if f is not None]
            rt = rotate(ra, -phi)
            row = {"slug": slug, "band": ps[slug]["band"], "class": ps[slug]["gain_class"], "variant": v,
                   "lag": lag, "phi_deg": math.degrees(phi), "abs_phi_deg": abs(math.degrees(phi)), "abs_c": absc,
                   "snr_rot_db": best_snr_db(rt, t[:len(rt)]),
                   "fidelity": statistics.fmean(fids) if fids else None, **di_metrics(ra, t)}
            row["proxy_fidelity"] = (b0.get(slug) or {}).get(v)
            table.append(row)
        print(slug, "done", flush=True)
    metrics = ("snr_db", "snr_rot_db", "abs_c", "abs_phi_deg", "lsd_db", "coh_80_1k", "coh_1k_3k", "coh_3k_8k", "quiet_db",
               "crest1_err_db", "crest5_err_db", "crest10_err_db", "proxy_fidelity")
    within = {m: _brief(within_part_assoc(table, m)) for m in metrics}
    ceil = {}
    for (slug, amp) in sig:
        true = LO._vals(stored_scores("measure", slug, amp), LO.TRUE)
        ceil.setdefault(slug, []).append(LO.ceiling(true))
    from scipy.stats import spearmanr

    across = {}
    m1b = [r for r in table if r["variant"] == "cprime_ref"]
    for m in metrics:
        pts = [(r[m], statistics.fmean(ceil[r["slug"]]) - r["fidelity"]) for r in m1b
               if r[m] is not None and r["fidelity"] is not None]
        across[m] = float(spearmanr(*zip(*pts)).correlation) if len(pts) > 3 else None
    far = [r for r in m1b if r["abs_phi_deg"] >= 90]
    near = [r for r in m1b if r["abs_phi_deg"] < 90]
    pol_split = {"rotated_90_or_more": {"parts": len(far), "fidelity": _brief(SRD.bw_stats([(r["band"], r["fidelity"]) for r in far]))},
                 "under_90": {"parts": len(near), "fidelity": _brief(SRD.bw_stats([(r["band"], r["fidelity"]) for r in near]))},
                 "by_class": {c: {"rotated_90_or_more": sum(1 for r in far if r["class"] == c),
                                  "under_90": sum(1 for r in near if r["class"] == c)} for c in ("clean", "crunch")}}
    rep = {"table": table, "within_part": within, "across_parts_vs_1b_gap": across, "rotation_split": pol_split}
    K._atomic(OUT / "metrics.json", rep)
    print(json.dumps({"within_part": {m: (v["band_weighted_mean"], v["lo90"], v["hi90"]) for m, v in within.items()},
                      "across": across, "rotation": pol_split}, indent=1, default=str))


# --- commands: the probes ------------------------------------------------------------------------------------

def cmd_probes():
    """Build every probe DI (except dep_rot) for the 24 parts, level them to −22.9 LUFS, log the
    alignment and realised metrics, and run the pre-render checks (probes/check.json)."""
    import numpy as np

    from learn import confirm_run as CR
    from learn.direc_check import to_lufs

    ps = K.parts()
    avg = np.load(CR.AVERAGE)
    log, bad = {}, {}
    for slug in sorted(s for s in ps if s not in LO.EXCLUDED):
        t = K.measure_di(ps[slug])
        r = np.load(LO.OUT / "rebuilt-ref" / f"{slug}.npy")
        raw, info = build_probes(r, t, slug, ps[slug]["judge_lag"], avg)
        info["t_peak"] = float(np.abs(t).max())
        lt = LO.lufs(t)
        levels, mets = {}, {}
        for p, x in raw.items():
            y = to_lufs(x)
            d = OUT / "probes" / p
            d.mkdir(parents=True, exist_ok=True)
            np.save(d / f"{slug}.npy", y)
            levels[p] = LO.lufs(y)
            mets[p] = di_metrics(y, t)
        exact = float(np.abs(raw["reb"] - shift(r[:len(t)], -info["lag"])).max())
        probs = probe_problems(levels, lt, info)
        for m in MIX_PROBES:
            probs += [f"{m}: {q}" for q in mix_problems(raw[m], t, raw["rot"])]
        if exact != 0.0:
            probs.append(f"reb differs from the shifted rebuild by {exact}")
        log[slug] = {**info, "measure_lufs": lt, "levels": levels, "metrics": mets}
        if probs:
            bad[slug] = probs
        print(slug, info["lag"], round(info["phi_deg"]), round(info["abs_c"], 3), info["onsets"],
              round(info["onset_coverage"], 3), probs or "ok", flush=True)
    K._atomic(OUT / "probes" / "log.json", log)
    K._atomic(OUT / "probes" / "check.json", {"ok": not bad, "problems": bad, "parts": len(log)})
    if bad:
        raise SystemExit(f"probe checks failed: {bad}")


def choose_rotation(scores):
    """dep_rot's rule: the rotation index whose S render scores lowest on the search half (A); the
    lowest index on a tie; 0 if every render was refused. scores: [{"A", "B"}] by index."""
    best, k = math.inf, 0
    for i, s_ in enumerate(scores):
        a = s_.get("A")
        if LO._finite(a) and a < best:
            best, k = a, i
    return k


def cmd_choose_rot(shard):
    """dep_rot's choice (216 renders): per R1 cell, a warm-up and S through the unshifted 1b rebuild
    r rotated by k · 45° (k = 0…7), scored on the deployable objective (reference.wav, −52, own mask
    with fallback, half A); the chosen rotation is applied to `reb` to build dep_rot for that part."""
    import numpy as np

    from learn import confirm_run as CR
    from learn.direc_check import to_lufs

    if not probes_ok():
        raise SystemExit("run `probes` first (its checks must pass)")
    wait_mega()
    ms = L.menu_S()
    aligned = LO.judge_fns()
    todo = L._shard(r1_cells(), shard)
    (OUT / "rotation").mkdir(parents=True, exist_ok=True)
    rr = None
    try:
        for slug, amp in todo:
            out = OUT / "rotation" / f"{slug}.json"
            if out.exists():
                continue
            check_stop()
            wait_cap()
            if rr is None:
                rr = K.Renderer()
                menu = rr.menu()
            part = K.parts()[slug]
            sel, S = menu[amp][K.START[part["gain_class"]][amp]]
            if K.key(S) != K.key(ms[amp][part["gain_class"]][1]):
                raise SystemExit(f"{amp}: the live S differs from arm B's stored copy")
            r = np.load(LO.OUT / "rebuilt-ref" / f"{slug}.npy")
            ref = CR.mono(part["crop"] / "reference.wav")
            n0 = rr.count
            rr.render(r.astype(np.float32), sel, S)                          # warm-up
            res = []
            for k in range(ROTATIONS):
                x = to_lufs(with_rotation(r, k))
                y = rr.render(x.astype(np.float32), sel, S)
                res.append(score_one(y, "arm_rank", {"di": x, "reference": ref}, part["judge_lag"], aligned)["decl"])
            k = choose_rotation(res)
            reb = np.load(probe_path("reb", slug))
            d = OUT / "probes" / "dep_rot"
            d.mkdir(parents=True, exist_ok=True)
            np.save(d / f"{slug}.npy", reb if k == 0 else to_lufs(with_rotation(reb, k)))
            log = json.loads((OUT / "probes" / "log.json").read_text())[slug]
            K._atomic(out, {"slug": slug, "amp": amp, "scores": res, "k": k, "deg": 360 * k / ROTATIONS,
                            "oracle_deg": -log["phi_deg"], "renders": rr.count - n0})
            print("rotation", slug, amp, 360 * k / ROTATIONS, "oracle", round(-log["phi_deg"]), flush=True)
    finally:
        if rr is not None:
            rr.close()


def dep_rot_ready():
    return all((OUT / "rotation" / f"{s}.json").exists() for s, _ in r1_cells())


def same_as_reb(probe, slug):
    """dep_rot where the rule chose no rotation is `reb` exactly: its renders and scores are reb's."""
    if probe != "dep_rot":
        return False
    p = OUT / "rotation" / f"{slug}.json"
    return p.exists() and json.loads(p.read_text())["k"] == 0


# --- commands: renders and scores ----------------------------------------------------------------------------

def comparator(rr, sel, slug, amp, points, aligned, arm=False):
    """Per cell, before its first render: the measure DI at S (probes) or 1b's C′ rebuild at S (arms),
    a warm-up then S, against experiment 1's / 1b's stored score at S (|log| per half)."""
    import numpy as np

    from learn import confirm_run as CR

    i = next(j for j, q in enumerate(points) if q.get("source") == "S")
    part = K.parts()[slug]
    ref = CR.mono(part["crop"] / "reference.wav")
    if arm:
        di = np.load(LO.OUT / "rebuilt-ref" / f"{slug}.npy")
        stored = stored_scores("cprime_ref", slug, amp)[i][LO.cname(LO.MATCHED)]
    else:
        di = K.measure_di(part)
        stored = stored_scores("measure", slug, amp)[i][LO.cname(LO.TRUE)]
    x32 = di.astype(np.float32)
    rr.render(x32, sel, points[i]["x"])
    y = rr.render(x32, sel, points[i]["x"])
    if arm:
        s = score_one(y, "arm_rank", {"di": di, "reference": ref}, part["judge_lag"], aligned)["decl"]
    else:
        s = score_one(y, "reb", {"di": di, "measure": di, "reference": ref}, part["judge_lag"], aligned,
                      only={"decl"})["decl"]
    devs = {h: LO.deviation(s[h], stored[h]) for h in HALVES}
    return {"index": i, "renders": 2, "devs": devs, "max_dev": max(devs.values())}


def stage_cells(stage):
    if stage in ("r1", "tr1"):
        return r1_cells()
    if stage in ("r2", "tr2"):
        return r2_cells()
    raise ValueError(stage)


def stage_probes(stage, probe_arg):
    if probe_arg and probe_arg != "all":
        return [p for p in probe_arg.split(",") if p]
    if stage == "r1":
        return list(PROBES)
    if stage == "r2":
        p = OUT / "report-r1.json"
        if not p.exists():
            raise SystemExit("R2 needs report-r1.json (its extension list)")
        return json.loads(p.read_text())["r2_probes"]
    if stage in ("tr1", "tr2"):
        return list(ARMS)
    raise ValueError(stage)


def cmd_render(shard, stage="r1", probe_arg="all", accept_guard_stop=False):
    """Stage R / TR renders: each cell's Σ (48 settings) through each probe or arm, 16-bit FLAC, one
    warm-up per (cell, probe); the comparator once per cell; S against the warm-up and FLAC against
    float. Guards: both stop files, the Mega-53 queue, the cap, the swap and disk guards."""
    import numpy as np

    probes = stage_probes(stage, probe_arg)
    if any(not is_arm(p) for p in probes) and not probes_ok():
        raise SystemExit("probe checks have not passed")
    if "dep_rot" in probes and not dep_rot_ready():
        raise SystemExit("dep_rot needs `choose-rot` first")
    if any(is_arm(p) for p in probes) and not arms_ok():
        raise SystemExit("the arms' rebuilds have not passed their checks")
    meta, sig = LO.load_sigma()
    check_stop()
    cells = stage_cells(stage)
    left = sum(len(sig[c]) + 1 for c in cells for p in probes if not _done(p, *c))
    if not accept_guard_stop and LO.disk_free_gb() - left * MB_PER_RENDER / 1000 < DISK_GUARD_GB:
        raise SystemExit(f"free disk {LO.disk_free_gb():.1f} GB leaves under {DISK_GUARD_GB} GB after {left} renders")
    wait_mega()
    aligned = LO.judge_fns()
    ms, rr, guard = L.menu_S(), None, L.SwapGuard()
    comp_dir = OUT / "comparator"
    try:
        for slug, amp in L._shard(cells, shard):
            for probe in probes:
                folder, rec_path = _render_paths(probe, slug, amp)
                prev = json.loads(rec_path.read_text()) if rec_path.exists() else {}
                if prev.get("status") in ("done", "same_as_reb"):
                    continue
                if same_as_reb(probe, slug):
                    rec_path.parent.mkdir(parents=True, exist_ok=True)
                    K._atomic(rec_path, {"slug": slug, "amp": amp, "probe": probe, "sigma": meta["hash"],
                                         "status": "same_as_reb", "renders": 0, "warm_ups": 0})
                    continue
                if prev.get("status") == "check_failed":
                    raise SystemExit(f"{probe} {slug} {amp} failed a check: investigate before rendering it again")
                check_stop()
                guard.check()
                wait_cap()
                if LO.disk_free_gb() - (len(sig[(slug, amp)]) + 1) * MB_PER_RENDER / 1000 < DISK_GUARD_GB:
                    raise SystemExit("free disk below the 31 GB guard (resumable)")
                if rr is None:
                    rr = K.Renderer()
                    menu = rr.menu()
                sig_s, part = signals(slug, probe)
                sel, S = menu[amp][K.START[part["gain_class"]][amp]]
                if K.key(S) != K.key(ms[amp][part["gain_class"]][1]):
                    raise SystemExit(f"{amp} {part['gain_class']}: the live S differs from arm B's stored copy")
                kind = "arm" if is_arm(probe) else "probe"
                cp = comp_dir / kind / f"{slug}-{amp}.json"
                rec = {"slug": slug, "amp": amp, "probe": probe, "sigma": meta["hash"], "status": "running",
                       "renders": prev.get("renders", 0), "warm_ups": prev.get("warm_ups", 0) + 1}
                if not cp.exists():
                    comp = comparator(rr, sel, slug, amp, sig[(slug, amp)], aligned, arm=is_arm(probe))
                    cp.parent.mkdir(parents=True, exist_ok=True)
                    K._atomic(cp, comp)
                    if comp["max_dev"] > CHECK_TOL:
                        rec_path.parent.mkdir(parents=True, exist_ok=True)
                        breakage(rec_path, {**rec, "comparator": comp},
                                 f"{slug} {amp}: the {kind} comparator at S moved {comp['max_dev']:.4f}")
                di32 = sig_s["di"].astype(np.float32)
                n0 = rr.count
                rec_path.parent.mkdir(parents=True, exist_ok=True)
                warm = rr.render(di32, sel, S)
                scales, checks = [], []
                for i, p in enumerate(sig[(slug, amp)]):
                    y = rr.render(di32, sel, p["x"])
                    rec["renders"] = prev.get("renders", 0) + rr.count - n0
                    scales.append(LO.save_flac(folder / f"{i:02d}.flac", y))
                    if p.get("source") == "S":
                        a = score_one(y, probe, sig_s, part["judge_lag"], aligned)
                        b = score_one(warm, probe, sig_s, part["judge_lag"], aligned, only={"decl"})
                        rec["S_float"] = {"index": i, "scores": a}
                        for h in HALVES:
                            dev = LO.deviation(a["decl"][h], b["decl"][h])
                            checks.append([i, "repeat_S", h, dev])
                            if dev > CHECK_TOL:
                                breakage(rec_path, {**rec, "checks_float": checks},
                                         f"{probe} {slug} {amp}: S moved {dev:.4f} from its warm-up on half {h}")
                    if i % 12 == 0:
                        K._atomic(rec_path, rec)
                rec.update(scales=scales, renders=prev.get("renders", 0) + rr.count - n0, checks_float=checks,
                           status="done")
                K._atomic(rec_path, rec)
                print(stage, probe, slug, amp, len(scales), "renders", rec["renders"], flush=True)
    finally:
        if rr is not None:
            rr.close()


def _score_cell(args):
    probe, slug, amp, root = args
    global OUT
    OUT = pathlib.Path(root)
    folder, rec_path = _render_paths(probe, slug, amp)
    rec = json.loads(rec_path.read_text())
    if rec.get("status") == "same_as_reb":
        src = OUT / "scores" / "reb" / slug / f"{amp}.json"
        if not src.exists():
            return probe, slug, amp                                       # scored after reb
        out = OUT / "scores" / probe / slug / f"{amp}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        K._atomic(out, {**json.loads(src.read_text()), "same_as_reb": True})
        return probe, slug, amp
    sig_s, part = signals(slug, probe)
    aligned = LO.judge_fns()
    scores = [score_one(LO.load_flac(folder / f"{i:02d}.flac", sc), probe, sig_s, part["judge_lag"], aligned)
              for i, sc in enumerate(rec["scales"])]
    sf = rec.get("S_float")
    fvf = None
    if sf:
        fl = scores[sf["index"]]
        fvf = {c: {h: LO.deviation(fl[c][h], v) for h, v in hv.items()} for c, hv in sf["scores"].items()}
    out = OUT / "scores" / probe / slug / f"{amp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    K._atomic(out, {"scores": scores, "sigma": rec["sigma"], "flac_vs_float_S": fvf})
    return probe, slug, amp


def cmd_score(workers=3):
    from concurrent.futures import ProcessPoolExecutor

    meta, sig = LO.load_sigma()
    todo = []
    for probe in (*[p for p in PROBES if p != "dep_rot"], "dep_rot", *ARMS):
        for (s, a) in sorted(sig):
            if _done(probe, s, a) and not (OUT / "scores" / probe / s / f"{a}.json").exists():
                todo.append((probe, s, a, str(OUT)))
    def reuse(t):
        rp = _render_paths(t[0], t[1], t[2])[1]
        return json.loads(rp.read_text()).get("status") == "same_as_reb"

    first, later = [t for t in todo if not reuse(t)], [t for t in todo if reuse(t)]
    with ProcessPoolExecutor(workers) as ex:
        for p, s, a in ex.map(_score_cell, first):
            print("scored", p, s, a, flush=True)
    for t in later:                                    # reb's scores exist now
        print("copied", *_score_cell(t)[:3], flush=True)


# --- report ----------------------------------------------------------------------------------------------------

def probe_vals(probe, slug, amp, config="decl"):
    p = OUT / "scores" / probe / slug / f"{amp}.json"
    if not p.exists():
        return None
    sc = json.loads(p.read_text())["scores"]
    return {h: [s[config][h] for s in sc] for h in HALVES}


def cell_rows(names, cells, config="decl"):
    """{name: {cell: (slug, band, cls, cross-half)}, plus "truth" and "cprime_ref"; and the same for
    reliable-pair accuracy (suffix ':rpa')."""
    ps = K.parts()
    out = {}
    for (slug, amp) in cells:
        true = LO._vals(stored_scores("measure", slug, amp), LO.TRUE)
        key = (slug, amp)
        base = (slug, ps[slug]["band"], ps[slug]["gain_class"])
        out.setdefault("truth", {})[key] = (*base, LO.ceiling(true))
        out.setdefault("truth:rpa", {})[key] = (*base, LO.reliable_accuracy(swap(true), true))
        m = LO._vals(stored_scores("cprime_ref", slug, amp), LO.MATCHED)
        out.setdefault("cprime_ref", {})[key] = (*base, LO.cross_half(m, true))
        out.setdefault("cprime_ref:rpa", {})[key] = (*base, LO.reliable_accuracy(swap(m), true))
        for n in names:
            v = probe_vals(n, slug, amp, config)
            if v is None:
                continue
            out.setdefault(n, {})[key] = (*base, LO.cross_half(v, true))
            out.setdefault(f"{n}:rpa", {})[key] = (*base, LO.reliable_accuracy(swap(v), true))
    return out


def _complete(rows, name, cells):
    return name in rows and all(c in rows[name] for c in cells)


def cmd_report(stage="r1"):
    from learn import local_objective_1c as C

    meta, sig = LO.load_sigma()
    if stage in ("r1", "r2"):
        cells = r1_cells() if stage == "r1" else sorted(set(r1_cells()) | set(r2_cells()))
        names = list(PROBES) if stage == "r1" else json.loads((OUT / "report-r1.json").read_text())["r2_probes"]
        out = {"stage": stage, "cells": len(cells), "probes": {}, "families": {}}
        for config in ("decl", "own"):
            rows = cell_rows(names, cells, config)
            blk = {}
            for p in names:
                cl = cells if stage == "r1" else [c for c in cells if c in rows.get(p, {})]
                if not _complete(rows, p, cl):
                    blk[p] = {"refused": f"{len(rows.get(p, {}))} of {len(cl)} cells scored"}
                    continue
                a = ANCHOR[p]
                e = {"fidelity": _brief(LO.agg(rows[p]))}
                if a:
                    diff = LO.paired(rows[p], rows[a])
                    e.update(vs_anchor=_brief(LO.agg(diff)), anchor=a,
                             vs_anchor_rpa=_brief(LO.agg(LO.paired(rows[f"{p}:rpa"], rows[f"{a}:rpa"]))))
                    if a != "truth":
                        gap = LO.paired({k: rows["truth"][k] for k in rows[p]}, rows[a])
                        e.update(anchor_gap=_brief(LO.agg(gap)), share_of_gap=C.share(diff, gap))
                else:
                    e["vs_stored_1b"] = _brief(LO.agg(LO.paired(rows[p], rows["cprime_ref"])))
                e["truth_same_cells"] = _brief(LO.agg({k: rows["truth"][k] for k in rows[p]}))
                blk[p] = e
            fam = {}
            for a, b in FAMILY_CONTRASTS:
                if a in rows and b in rows:
                    fam[f"{a}-{b}"] = _brief(LO.agg(LO.paired(rows[a], rows[b])))
            out["probes"][config] = blk
            out["families"][config] = fam
        out["where"] = probe_where(names, cells)
        if stage == "r1":
            contr = {p: e["vs_anchor"] for p, e in out["probes"]["decl"].items() if "vs_anchor" in e}
            out["narrowing"] = narrowing_ratio()
            out["r2_probes"] = r2_list(contr, out["families"]["decl"], out["narrowing"]["ratio"])
            rot = [json.loads((OUT / "rotation" / f"{s}.json").read_text()) for s, _ in r1_cells()
                   if (OUT / "rotation" / f"{s}.json").exists()]
            out["dep_rot_choice"] = {"parts": len(rot), "chose_none": sum(r["k"] == 0 for r in rot),
                                     "within_45_of_oracle": sum(abs(((r["deg"] - r["oracle_deg"]) + 180) % 360 - 180) <= 45
                                                                for r in rot)}
        out["renders"] = renders_used()
        K._atomic(OUT / f"report-{stage}.json", out)
        print(json.dumps({p: (e.get("vs_anchor") or e.get("vs_stored_1b") or e) for p, e in out["probes"]["decl"].items()},
                         indent=1, default=str)[:6000])
        if stage == "r1":
            print("R2 extends:", out["r2_probes"])
        return
    cells1 = r1_cells()
    cells = cells1 + (r2_cells() if all(_done(p, *c) for p in ARMS for c in r2_cells()) else [])
    rows = cell_rows(list(ARMS), cells)
    out = {"stage": "tr", "cells": len(cells)}
    for c, name in (("arm_rank", "cprime_ref"), ("arm_rank", "arm_ctl"), ("arm_ctl", "cprime_ref")):
        if c in rows and name in rows:
            out[f"{c}-{name}"] = _brief(LO.agg(LO.paired(rows[c], rows[name])))
            out[f"{c}-{name}:rpa"] = _brief(LO.agg(LO.paired(rows[f"{c}:rpa"], rows[f"{name}:rpa"])))
    out["narrowing"] = narrowing_ratio()
    out["tr2_due"] = tr2_due(out.get("arm_rank-cprime_ref", {}), out["narrowing"]["ratio"])
    out["renders"] = renders_used()
    K._atomic(OUT / "report-tr.json", out)
    print(json.dumps(out, indent=1, default=str))


REFERENCE_CONTRASTS = (("cprime_ref", LO.MATCHED, "cprime", LO.CURRENT),
                       ("measure", LO.TRUE, "cprime_ref", LO.MATCHED),
                       ("cprime", ("cprime", "reference", "native", "own"), "cprime", LO.CURRENT),
                       ("cprime_mega53", ("cprime_mega53", "mega53", "native", "own"), "cprime", LO.CURRENT),
                       ("csep_stem", ("csep_stem", "stem", "native", "own"), "cprime", LO.CURRENT),
                       ("csep_mega53", ("csep_mega53", "mega53", "native", "own"), "cprime_mega53",
                        ("cprime_mega53", "mega53", "native", "own")))


def narrowing_ratio():
    """Amendment 1, item 5: how much a paired contrast's band-clustered half-width shrinks from the 24
    R1 cells to all 72, measured on the stored contrasts of experiments 1–1d (the truth's own
    cross-half order standing in for the measure DI's). -> {"ratio": median, "each": [...]}."""
    meta, sig = LO.load_sigma()
    ps = K.parts()
    each = []
    for da, ca, db, cb in REFERENCE_CONTRASTS:
        rows_a, rows_b = {}, {}
        for (slug, amp) in sig:
            try:
                true = LO._vals(stored_scores("measure", slug, amp), LO.TRUE)
                va = true if da == "measure" else LO._vals(stored_scores(da, slug, amp), ca)
                vb = LO._vals(stored_scores(db, slug, amp), cb)
            except (OSError, KeyError):
                continue
            base = (slug, ps[slug]["band"], ps[slug]["gain_class"])
            rows_a[(slug, amp)] = (*base, LO.ceiling(true) if da == "measure" else LO.cross_half(va, true))
            rows_b[(slug, amp)] = (*base, LO.cross_half(vb, true))
        d = LO.paired(rows_a, rows_b)
        one = set(r1_cells())
        full, sub = LO.agg(d), LO.agg({k: v for k, v in d.items() if k in one})
        if full.get("lo90") is not None and sub.get("lo90") is not None and sub["hi90"] > sub["lo90"]:
            each.append({"contrast": f"{da}:{ca[1]}-{db}:{cb[1]}",
                         "ratio": (full["hi90"] - full["lo90"]) / (sub["hi90"] - sub["lo90"])})
    rs = sorted(e["ratio"] for e in each)
    return {"ratio": statistics.median(rs) if rs else None, "each": each}


def probe_where(names, cells):
    """A1's knob-family 3-way agreement (cross-half) per probe, and each probe − its anchor."""
    meta, sig = LO.load_sigma()
    ms, ps = L.menu_S(), K.parts()
    fams = ("input gain", "amp gain", "amp tone", "cab")
    per = {}
    for (slug, amp) in cells:
        S = ms[amp][ps[slug]["gain_class"]][1]
        dims = K.space(amp, S)
        true = LO._vals(stored_scores("measure", slug, amp), LO.TRUE)
        for n in names:
            v = probe_vals(n, slug, amp)
            if v is not None:
                tw = family_measures(sig[(slug, amp)], dims, v, true, S)["three_way"]
                per.setdefault(n, {})[(slug, amp)] = tw
    out = {}
    for n, cellv in per.items():
        out[n] = {}
        for f in fams:
            rows = {k: (k[0], ps[k[0]]["band"], ps[k[0]]["gain_class"], tw[f][0]) for k, tw in cellv.items() if f in tw}
            out[n][f] = _brief(LO.agg(rows))
            a = ANCHOR.get(n)
            if a in per:
                ra = {k: (k[0], ps[k[0]]["band"], ps[k[0]]["gain_class"], tw[f][0]) for k, tw in per[a].items() if f in tw}
                out[n][f"{f} - anchor"] = _brief(LO.agg(LO.paired(rows, ra)))
    return out


def renders_used():
    tot, by = 0, {}
    for p in (OUT / "renders").glob("*/*/*.json"):
        r = json.loads(p.read_text())
        n = r.get("renders", 0) + r.get("warm_ups", 0)
        by[r["probe"]] = by.get(r["probe"], 0) + n
        tot += n
    comp = 2 * len(list((OUT / "comparator").glob("*/*.json")))
    rot = sum(json.loads(p.read_text()).get("renders", 0) for p in (OUT / "rotation").glob("*.json"))
    return {"by_probe": by, "comparator": comp, "rotation_choice": rot, "total": tot + comp + rot}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("where")
    r = sub.add_parser("rescore")
    r.add_argument("--workers", type=int, default=1)
    sub.add_parser("probes")
    sub.add_parser("metrics")
    c = sub.add_parser("choose-rot")
    c.add_argument("--shard", default="0/1")
    r = sub.add_parser("render")
    r.add_argument("--shard", default="0/1")
    r.add_argument("--stage", default="r1", choices=("r1", "r2", "tr1", "tr2"))
    r.add_argument("--probe", default="all")
    r.add_argument("--accept-guard-stop", action="store_true")
    s = sub.add_parser("score")
    s.add_argument("--workers", type=int, default=3)
    p = sub.add_parser("report")
    p.add_argument("--stage", default="r1", choices=("r1", "r2", "tr"))
    sub.add_parser("wait-mega")
    sub.add_parser("wait-lane-a")
    a = ap.parse_args(argv)

    def shard(x):
        i, n = x.split("/")
        return (int(i), int(n))

    if a.cmd == "where":
        cmd_where()
    elif a.cmd == "rescore":
        cmd_rescore(a.workers)
    elif a.cmd == "probes":
        cmd_probes()
    elif a.cmd == "metrics":
        cmd_metrics()
    elif a.cmd == "choose-rot":
        cmd_choose_rot(shard(a.shard))
    elif a.cmd == "render":
        cmd_render(shard(a.shard), a.stage, a.probe, a.accept_guard_stop)
    elif a.cmd == "score":
        cmd_score(a.workers)
    elif a.cmd == "report":
        cmd_report(a.stage)
    elif a.cmd == "wait-mega":
        wait_mega()
    elif a.cmd == "wait-lane-a":
        wait_lane_a()


if __name__ == "__main__":
    main()
