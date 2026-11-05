"""The model comparison's inputs (`docs/model-comparison-plan.md`, Phase 3): summaries of one half's stored log-mel.

Each takes x, a [bands, frames] normalised log-mel as the network sees it ((dB + 60) / 30, `song_model.norm_feat`), without
any frames half A masks, and the bands' centres in Hz. Each returns a flat vector; the caller adds the half's LUFS.
"""
from __future__ import annotations

import numpy as np

FRAMES_PER_S = 100
ATTACK_FRAMES = 6                       # 60 ms after an onset
MIN_ONSET_GAP = 5                       # 50 ms between onsets
LTAS_HZ = (80.0, 5000.0)
LTAS_FLOOR_DB = -45.0
CEPS_LOW = (1, 21)
CEPS_HIGH = (21, 61)
COARSE = 8
MEDIAN_SIZE = 17
EPS = 1e-10


def to_db(x):
    return np.asarray(x, np.float64) * 30.0 - 60.0


def dct(a):
    """Orthonormal DCT-II along axis 0."""
    n = a.shape[0]
    k = np.arange(n)[:, None]
    basis = np.cos(np.pi * k * (2 * np.arange(n)[None] + 1) / (2 * n)) * np.sqrt(2.0 / n)
    basis[0] /= np.sqrt(2.0)
    return basis @ a


def mel(x, _centres=None):
    """Band means then stds."""
    return np.concatenate([x.mean(-1), x.std(-1)])


def ltas(x, centres):
    """Band means inside LTAS_HZ, each frame's cells raised to the floor first."""
    keep = (np.asarray(centres) >= LTAS_HZ[0]) & (np.asarray(centres) <= LTAS_HZ[1])
    return ((np.maximum(to_db(x[keep]), LTAS_FLOOR_DB) + 60.0) / 30.0).mean(-1)


def ceps_lo(x, _centres=None):
    """Low quefrency of the long-term spectrum: orders 1-20 of the band means' DCT."""
    return dct(x.mean(-1))[CEPS_LOW[0]:CEPS_LOW[1]]


def ceps_hi(x, _centres=None):
    """High quefrency per frame: the means and stds over time of orders 21-60."""
    c = dct(x)[CEPS_HIGH[0]:CEPS_HIGH[1]]
    return np.concatenate([c.mean(-1), c.std(-1)])


def onsets(x):
    """Frames of peaks in positive spectral flux, above its mean plus one sd, at least MIN_ONSET_GAP apart."""
    d = np.diff(to_db(x), axis=-1, prepend=to_db(x)[..., :1])
    flux = np.maximum(d, 0).sum(0)
    bar = flux.mean() + flux.std()
    picked = []
    for t in np.argsort(-flux):
        if flux[t] <= bar:
            break
        if all(abs(t - p) >= MIN_ONSET_GAP for p in picked):
            picked.append(int(t))
    return sorted(picked)


def attack_mask(x):
    """True on the ATTACK_FRAMES from each onset."""
    m = np.zeros(x.shape[-1], bool)
    for t in onsets(x):
        m[t:t + ATTACK_FRAMES] = True
    return m


def onset(x, _centres=None):
    """Band means and stds on attacks and sustains apart; with too few of either, both take all frames."""
    m = attack_mask(x)
    if m.sum() < 2 or (~m).sum() < 2:
        return np.concatenate([mel(x), mel(x)])
    return np.concatenate([mel(x[:, m]), mel(x[:, ~m])])


def flat(x, _centres=None):
    """Spectral flatness (log geometric over log arithmetic mean power, in nats) over all bands and COARSE groups: each one's
    mean and std over frames."""
    p = 10.0 ** (to_db(x) / 10.0)
    groups = [np.arange(x.shape[0]), *np.array_split(np.arange(x.shape[0]), COARSE)]
    out = []
    for g in groups:
        f = np.log(p[g] + EPS).mean(0) - np.log(p[g].mean(0) + EPS)
        out += [f.mean(), f.std()]
    return np.array(out)


def hpss(x, _centres=None):
    """Band means and stds, in network units, of the percussive part: median filters in time and in frequency, soft mask."""
    from scipy.ndimage import median_filter

    p = 10.0 ** (to_db(x) / 10.0)
    h = median_filter(p, size=(1, MEDIAN_SIZE), mode="nearest")
    q = median_filter(p, size=(MEDIAN_SIZE, 1), mode="nearest")
    r = p * q ** 2 / (h ** 2 + q ** 2 + EPS)
    return mel((10.0 * np.log10(r + EPS) + 60.0) / 30.0)


INPUTS = {"mel": mel, "ltas": ltas, "ceps-lo": ceps_lo, "ceps-hi": ceps_hi, "onset": onset, "flat": flat, "hpss": hpss}
