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


# Standard-tuning open strings, low E to high E, in Hz.
_OPEN_STRINGS = (82.41, 110.0, 146.83, 196.0, 246.94, 329.63)
# Five open-position chord shapes as frets per string, low to high; None is muted.
_CHORDS = ((0, 2, 2, 1, 0, 0), (None, 0, 2, 2, 1, 0), (None, 3, 2, 0, 1, 0),
           (3, 2, 0, 0, 0, 3), (None, None, 0, 2, 3, 2))


def synthetic_guitar(
    seconds: float = 6.0,
    seed: int = 13,
    target_lufs: float = -17.0,
    sample_rate: int = SAMPLE_RATE,
):
    """A strummed, picked guitar DI, synthesised — tried as the no-DI probe, not adopted.

    Karplus-Strong strings — strummed open chords and short single-note runs
    across the neck — through a rough single-coil response (a bump near 2 kHz,
    rolled off above 3.5 kHz), scaled to a played DI's loudness. Chosen against
    the two played DIs measured so far on loudness, spectral tilt and crest
    factor (it is brighter than both by spectral centroid), then left alone and
    measured as a search signal. Scored through one played passage it ended 31%
    closer than `decaying_noise_bursts`; scored through the other it was no
    better (docs/tone-matching-plan.md, "Matching without a DI"). So matches keep
    the noise probe, and this stays as `benchmark_search_signal.py --signal
    guitar`, reproducible, for the next attempt at a better one.
    """
    require("synthetic probe generation")
    import numpy as np

    from . import io

    rng = np.random.default_rng(seed)
    out = np.zeros(int(seconds * sample_rate))
    t, phrase = 0.0, 0
    while t < seconds - 0.4:
        if phrase % 3 != 2:
            shape = _CHORDS[rng.integers(len(_CHORDS))]
            spread = rng.uniform(0.008, 0.02)     # seconds between strings
            downstroke = rng.random() < 0.7
            order = range(6) if downstroke else range(5, -1, -1)
            played = 0
            for string in order:
                fret = shape[string]
                if fret is None:
                    continue
                frequency = _OPEN_STRINGS[string] * 2 ** (fret / 12)
                note = _plucked_string(frequency, min(2.5, seconds - t), rng,
                                       rng.uniform(0.4, 0.8), rng.uniform(2.0, 4.0),
                                       sample_rate)
                start = int((t + played * spread) * sample_rate)
                end = min(len(out), start + len(note))
                out[start:end] += note[:end - start] * rng.uniform(0.7, 1.0)
                played += 1
            t += rng.choice([0.45, 0.6, 0.9])
        else:
            for _ in range(rng.integers(3, 6)):
                string = rng.integers(2, 6)
                fret = rng.integers(0, 13)
                frequency = _OPEN_STRINGS[string] * 2 ** (fret / 12)
                note = _plucked_string(frequency, min(1.2, seconds - t), rng,
                                       rng.uniform(0.5, 0.9), rng.uniform(1.0, 2.5),
                                       sample_rate)
                start = int(t * sample_rate)
                end = min(len(out), start + len(note))
                out[start:end] += note[:end - start]
                t += rng.choice([0.15, 0.2, 0.3])
                if t >= seconds - 0.4:
                    break
        phrase += 1
    out = _single_coil(out, sample_rate)
    level = io.loudness_lufs(io.from_samples(out.astype(np.float32), sample_rate))
    return (out * 10 ** ((target_lufs - level) / 20)).astype(np.float32)


def _plucked_string(frequency, seconds, rng, brightness, decay_s, sample_rate):
    """One string: a recursive comb with a two-tap averaging loss (Karplus-Strong).

    The pluck is noise smoothed more for a softer pick; the loss per period is set
    so the note falls 60 dB in `decay_s`, which makes high notes die sooner.
    """
    import numpy as np
    from scipy import signal

    delay = max(2, int(round(sample_rate / frequency)))
    excitation = rng.uniform(-1, 1, delay)
    for _ in range(int(8 * (1 - brightness)) + 1):
        excitation = 0.5 * (excitation + np.roll(excitation, 1))
    impulse = np.zeros(int(seconds * sample_rate))
    impulse[:delay] = excitation
    loss = 10 ** (-3.0 / (decay_s * frequency))
    feedback = np.zeros(delay + 2)
    feedback[0] = 1.0
    feedback[delay] = feedback[delay + 1] = -0.5 * loss
    return signal.lfilter([1.0], feedback, impulse)


def _single_coil(samples, sample_rate):
    """A magnetic pickup, roughly: a resonance near 2 kHz and a roll-off above it."""
    from scipy import signal

    b, a = signal.iirpeak(2000 / (sample_rate / 2), Q=1.5)
    peaked = samples + 0.4 * signal.lfilter(b, a, samples)
    b, a = signal.butter(2, 3500 / (sample_rate / 2))
    return signal.lfilter(b, a, peaked)
