"""Line two recordings up before comparing them sample by sample.

Needed more often than it looks. M0 measured a **57-sample offset between two
hosts rendering the same plugin with the same input** — the waveforms correlate
at 0.991, but subtract them unaligned and the difference is larger than either
signal. Any comparison that works in the time domain has to align first, and
that includes comparing two renders, not just a render against a reference.

Spectral and cepstral features do not need this: they are shift-invariant by
construction, which is a large part of why the fingerprint is built out of them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from . import require


@dataclass(frozen=True)
class Alignment:
    """How far apart two signals are, and how sure that is.

    `offset_samples` is what to shift the candidate by to land on the reference:
    positive means the candidate is late. `correlation` is the normalised peak,
    so 1.0 is the same signal and something near 0 means these two have no
    common timing at all — in which case aligning them is meaningless and the
    caller should say so rather than shift by the argmax of noise.
    """

    offset_samples: int
    fractional_offset: float
    correlation: float
    polarity: int
    sample_rate: int

    @property
    def offset_ms(self) -> float:
        return (self.offset_samples + self.fractional_offset) / self.sample_rate * 1000.0

    @property
    def trustworthy(self) -> bool:
        return abs(self.correlation) >= 0.3


def find_alignment(reference, candidate, sample_rate: int,
                   max_lag_s: float = 1.0) -> Alignment:
    """Integer cross-correlation, then sub-sample refinement, then polarity."""
    require("alignment")
    import numpy as np

    a = _mono(reference)
    b = _mono(candidate)
    if len(a) == 0 or len(b) == 0:
        return Alignment(0, 0.0, 0.0, 1, sample_rate)

    a = a - a.mean()
    b = b - b.mean()
    norm = math.sqrt(float((a**2).sum()) * float((b**2).sum()))
    if norm <= 0:
        return Alignment(0, 0.0, 0.0, 1, sample_rate)

    size = 1 << int(math.ceil(math.log2(len(a) + len(b))))
    correlation = np.fft.irfft(np.fft.rfft(a, size) * np.conj(np.fft.rfft(b, size)), size)
    correlation /= norm

    # Lags in [-max, +max], laid out contiguously so the peak search is one call.
    span = min(int(max_lag_s * sample_rate), size // 2 - 2)
    window = np.concatenate([correlation[-span:], correlation[: span + 1]])
    lags = np.arange(-span, span + 1)

    peak = int(np.argmax(np.abs(window)))
    value = float(window[peak])
    # The correlation peaks at minus the delay: if the candidate is d samples
    # late, a[t]·b[t-k] is largest at k = -d. Negate here so that the offset
    # this returns reads the way its name does.
    offset = -int(lags[peak])

    # Sub-sample refinement by fitting a parabola to the peak and its neighbours.
    fractional = 0.0
    if 0 < peak < len(window) - 1:
        before, at, after = np.abs(window[peak - 1 : peak + 2])
        curvature = before - 2.0 * at + after
        if curvature != 0:
            fractional = -float(np.clip(0.5 * (before - after) / curvature, -0.5, 0.5))

    # A negative peak means one of them is wired backwards. That is a real thing
    # that happens to a re-amped DI, and it makes every waveform difference
    # meaningless while changing no spectrum at all.
    return Alignment(
        offset_samples=offset,
        fractional_offset=fractional,
        correlation=value,
        polarity=-1 if value < 0 else 1,
        sample_rate=sample_rate,
    )


def apply_alignment(reference, candidate, alignment: Alignment):
    """Shift and trim so index *i* means the same instant in both.

    Returns the overlapping region of each, with the candidate's polarity
    corrected and its sub-sample offset removed.
    """
    require("alignment")
    import numpy as np

    a = np.asarray(reference, dtype=np.float64)
    b = np.asarray(candidate, dtype=np.float64) * alignment.polarity

    if alignment.fractional_offset:
        b = _fractional_shift(b, -alignment.fractional_offset)

    offset = alignment.offset_samples
    if offset > 0:      # candidate is late: drop its head
        b = b[offset:]
    elif offset < 0:    # candidate is early: drop the reference's head
        a = a[-offset:]

    length = min(len(a), len(b))
    return a[:length], b[:length]


def _fractional_shift(signal, samples: float):
    """Delay by a fraction of a sample, as a phase rotation in the frequency
    domain. Exact for a band-limited signal, which a render is."""
    import numpy as np

    size = 1 << int(math.ceil(math.log2(len(signal) + 2)))
    spectrum = np.fft.rfft(signal, size)
    frequencies = np.fft.rfftfreq(size, 1.0)
    shifted = spectrum * np.exp(-2j * np.pi * frequencies * samples)
    return np.fft.irfft(shifted, size)[: len(signal)]


def align(reference, candidate, sample_rate: int, max_lag_s: float = 1.0):
    """Find and apply in one call. Returns (reference, candidate, Alignment).

    When the correlation is too low to trust, nothing is shifted: a bad
    alignment is worse than none, because it silently invents a timing
    relationship that the audio does not have.
    """
    alignment = find_alignment(reference, candidate, sample_rate, max_lag_s)
    if not alignment.trustworthy:
        import numpy as np

        a, b = _mono(reference), _mono(candidate)
        length = min(len(a), len(b))
        return np.asarray(a[:length]), np.asarray(b[:length]), alignment
    a, b = apply_alignment(_mono(reference), _mono(candidate), alignment)
    return a, b, alignment


def _mono(samples):
    import numpy as np

    array = np.asarray(samples, dtype=np.float64)
    return array.mean(axis=1) if array.ndim > 1 else array


def residual_db(reference, candidate) -> Optional[float]:
    """How much of the reference is left after subtracting the candidate, in dB.

    The number M0 used to compare two hosts and two renders: 0 dB means the
    difference is as loud as the signal, -60 dB means they are the same
    recording. Align first, or this measures the offset instead of the audio.
    """
    require("residual measurement")
    import numpy as np

    a, b = _mono(reference), _mono(candidate)
    length = min(len(a), len(b))
    if length == 0:
        return None
    a, b = a[:length], b[:length]
    energy = float((a**2).mean())
    if energy <= 0:
        return None
    difference = float(((a - b) ** 2).mean())
    return float(10.0 * np.log10(difference / energy + 1e-30))
