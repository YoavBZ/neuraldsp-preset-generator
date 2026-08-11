"""Controlled signals used by matching when no played DI is available.

These are production inputs, not test fixtures. A match may score hundreds of
plugin renders against this signal, so its exact construction and seed are part
of the measurement protocol.
"""

from __future__ import annotations

from . import SAMPLE_RATE, require


def decaying_noise_bursts(
    seconds: float = 8.0,
    gap: float = 0.9,
    decay: float = 18.0,
    length: float = 0.25,
    seed: int = 7,
    sample_rate: int = SAMPLE_RATE,
):
    """Return transient, aperiodic white-noise bursts at regular intervals.

    This used to be called a synthetic "pluck", which suggested pitched guitar
    excitation it does not contain. Noise is intentional: it exposes attack and
    decay without adding a pitch comb, but it cannot represent sustained or
    palm-muted playing.
    """
    require("synthetic probe generation")
    import numpy as np

    rng = np.random.default_rng(seed)
    out = np.zeros(int(seconds * sample_rate))
    for onset in np.arange(0.1, seconds - 0.4, gap):
        start = int(onset * sample_rate)
        span = min(int(length * sample_rate), len(out) - start)
        if span <= 0:
            break
        envelope = np.exp(-np.arange(span) / sample_rate * decay)
        out[start : start + span] += rng.standard_normal(span) * envelope
    return out
