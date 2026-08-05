"""Signals with known answers, synthesised at test time.

Nothing here is committed as audio. Every fixture is generated from a seed, so
the tests carry no files, redistribute nothing, and a failure can be reproduced
exactly by anyone who has the repository.

Each generator exists to make one measurement checkable: a filter whose response
is known, an echo whose time and feedback are known, a decay whose RT60 is
known. If a feature cannot be checked against a signal like these, that is a
sign the feature is not yet defined precisely enough to be useful.
"""

from __future__ import annotations

SAMPLE_RATE = 48000


def noise(seconds: float = 4.0, seed: int = 7, sample_rate: int = SAMPLE_RATE):
    """Seeded white noise: flat excitation, identical between runs."""
    import numpy as np

    rng = np.random.default_rng(seed)
    return rng.standard_normal(int(seconds * sample_rate))


def band_limited(seconds: float = 4.0, low: float = 90.0, high: float = 5000.0,
                 seed: int = 7, order: int = 4, sample_rate: int = SAMPLE_RATE):
    """Noise through a known bandpass — the LTAS should recover its shape."""
    from scipy import signal

    sos = signal.butter(order, [low, high], btype="band", fs=sample_rate, output="sos")
    return signal.sosfilt(sos, noise(seconds, seed, sample_rate))


def plucks(seconds: float = 8.0, gap: float = 0.9, decay: float = 18.0,
           length: float = 0.25, seed: int = 7, sample_rate: int = SAMPLE_RATE):
    """A train of decaying noise bursts: transient, aperiodic, one per `gap`.

    Aperiodic on purpose. A pitched signal correlates with itself at every
    multiple of its period, which is a separate problem with its own test.
    `length` is how long each burst rings for, which decides whether anything
    modulating the note has room to be heard.
    """
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


def harmonic_note(seconds: float = 2.0, f0: float = 196.0,
                  partials=(1.0, 0.5, 0.3, 0.2, 0.12, 0.08),
                  sample_rate: int = SAMPLE_RATE):
    """A sustained note with a known fundamental and a known harmonic series."""
    import numpy as np

    t = np.arange(int(seconds * sample_rate)) / sample_rate
    return sum(a * np.sin(2 * np.pi * f0 * (k + 1) * t) for k, a in enumerate(partials))


def with_echo(signal_1d, delay_s: float, feedback: float, repeats: int = 8,
              sample_rate: int = SAMPLE_RATE):
    """Add a feedback echo of known time and known decay per repeat."""
    import numpy as np

    out = np.array(signal_1d, dtype=np.float64, copy=True)
    delay = int(delay_s * sample_rate)
    for repeat in range(1, repeats + 1):
        offset = repeat * delay
        if offset >= len(signal_1d):
            break
        shifted = np.zeros_like(out)
        shifted[offset:] = signal_1d[: len(signal_1d) - offset]
        out += shifted * (feedback**repeat)
    return out


def decaying_bursts(rt60_s: float = 1.2, seconds: float = 10.0, gap: float = 1.8,
                    seed: int = 7, sample_rate: int = SAMPLE_RATE):
    """Noise bursts that decay at a known rate — a room, with the answer known.

    RT60 is the time to fall 60 dB, so the envelope is 10^(-3t/rt60).
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    out = np.zeros(int(seconds * sample_rate))
    for onset in np.arange(0.2, seconds - 1.0, gap):
        start = int(onset * sample_rate)
        length = min(int(1.6 * sample_rate), len(out) - start)
        if length <= 0:
            break
        t = np.arange(length) / sample_rate
        out[start : start + length] += rng.standard_normal(length) * 10 ** (-3 * t / rt60_s)
    return out


def dense(seconds: float = 8.0, pulse: float = 0.25, decay: float = 8.0,
          length: float = 0.6, tonal: bool = False, seed: int = 5,
          sample_rate: int = SAMPLE_RATE):
    """Notes on a strong regular pulse that ring on into each other.

    The material the delay detector is worst at, and the reason: each note lasts
    `length` while the next arrives after `pulse`, so the amplitude envelope
    never falls back down. Anything that needs the envelope to dip between notes
    has nothing to work with.

    `tonal=True` cycles four pitches, which makes it worse in a second way — the
    part repeats *literally* every four notes, in the waveform as well as the
    envelope, which is what an echo does.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    out = np.zeros(int(seconds * sample_rate))
    for index, onset in enumerate(np.arange(0.1, seconds - 0.8, pulse)):
        start = int(onset * sample_rate)
        span = min(int(length * sample_rate), len(out) - start)
        if span <= 0:
            break
        shape = np.exp(-np.arange(span) / sample_rate * decay)
        if tonal:
            f0 = [196.0, 220.0, 246.9, 261.6][index % 4]
            t = np.arange(span) / sample_rate
            note = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in (1, 2, 3))
        else:
            note = rng.standard_normal(span)
        out[start : start + span] += note * shape
    return out


def bursts_with_predelay(predelay_ms: float = 80.0, rt60_s: float = 1.2,
                         seconds: float = 10.0, gap: float = 1.8, tail_level: float = 0.5,
                         seed: int = 7, sample_rate: int = SAMPLE_RATE):
    """A short direct sound, then a gap, then a decaying tail.

    A reverb with a pre-delay, built so the answer is known: the direct burst
    stops, the envelope falls into the gap, and the tail arrives `predelay_ms`
    after the attack and pushes it back up. That shoulder is the only thing
    `_detect_predelay` looks for.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    out = np.zeros(int(seconds * sample_rate))
    direct_len = int(0.012 * sample_rate)
    offset = int(predelay_ms / 1000.0 * sample_rate)
    for onset in np.arange(0.2, seconds - 2.0, gap):
        start = int(onset * sample_rate)
        # The direct sound: brief, and gone well before the tail arrives.
        length = min(direct_len, len(out) - start)
        if length <= 0:
            break
        t = np.arange(length) / sample_rate
        out[start : start + length] += rng.standard_normal(length) * np.exp(-t * 400.0)

        tail_start = start + offset
        tail_len = min(int(1.6 * sample_rate), len(out) - tail_start)
        if tail_len <= 0:
            continue
        t = np.arange(tail_len) / sample_rate
        out[tail_start : tail_start + tail_len] += (
            rng.standard_normal(tail_len) * tail_level * 10 ** (-3 * t / rt60_s)
        )
    return out


def tremolo(signal_1d, rate_hz: float = 5.0, depth: float = 0.6,
            sample_rate: int = SAMPLE_RATE):
    """Amplitude modulation at a known rate and depth."""
    import numpy as np

    t = np.arange(len(signal_1d)) / sample_rate
    return np.asarray(signal_1d) * (1.0 + depth * np.sin(2 * np.pi * rate_hz * t))


def stereo(signal_1d, width: float = 0.0):
    """Two channels from one, with a known amount of decorrelation."""
    import numpy as np

    mono = np.asarray(signal_1d, dtype=np.float64)
    if width <= 0:
        return np.stack([mono, mono], axis=1)
    side = np.roll(mono, 137) * width
    return np.stack([mono + side, mono - side], axis=1)


def write_wav(path, samples, sample_rate: int = SAMPLE_RATE):
    """Write a fixture to a temporary path, for the CLI tests."""
    import numpy as np
    import soundfile as sf

    data = np.asarray(samples, dtype=np.float32)
    if data.ndim == 1:
        data = data[:, None]
    peak = float(np.abs(data).max())
    if peak > 0:
        data = data / peak * 0.7
    sf.write(str(path), data, sample_rate)
    return path
