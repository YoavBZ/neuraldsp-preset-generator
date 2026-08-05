"""The individual measurements a fingerprint is made of.

Each function here answers one question about a sound and says how sure it is.
They are separate because they fail separately: a two-second render of white
noise has a spectrum but no note onsets, a chord has onsets but no measurable
harmonic series, and a mix has all of it buried under three other instruments.
A feature that cannot be measured from the material returns `None` with a
confidence of zero. It never returns a number it cannot support — a wrong
`rt60_s` would move the optimiser as hard as a right one.

Everything is computed on gated frames, meaning the frames that are loud enough
relative to the loudest one to be the sound rather than the gap between notes.
Averaging the silence in is how a long-term spectrum ends up describing a room.

Spectral and harmonic features expect loudness-normalised input (see
`io.normalise`), which is what makes them comparable between a mastered record
and a raw render.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

from . import require
from .io import SILENCE_FLOOR_DB

# ISO third-octave centres, 25 Hz to 20 kHz. Wide enough to cover what a guitar
# amp does at both ends, without inventing resolution the material cannot carry.
THIRD_OCTAVE_CENTRES: List[float] = [
    25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800,
    1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500,
    16000, 20000,
]

SPECTRUM_FFT = 8192      # 5.9 Hz bins: enough to resolve the lowest bands
SPECTRUM_HOP = 2048
FRAME_FFT = 2048         # 43 ms: enough time resolution for per-frame statistics
FRAME_HOP = 512
# Hz, for everything that works on the amplitude envelope. 1 ms resolution is
# more than the millisecond quantities derived from it need: halving it to 500
# leaves every measurement inside its tested tolerance, so the value has
# headroom rather than being load-bearing.
ENVELOPE_RATE = 1000
MODULATION_FLOOR = 0.03  # below this an "AM rate" is describing the noise floor

# Note divisions a detected delay time is allowed to be named as. Anything not
# in this list is reported in milliseconds and left unnamed.
NOTE_DIVISIONS = [
    "whole", "half", "half dotted", "half triplet",
    "quarter", "quarter dotted", "quarter triplet",
    "eighth", "eighth dotted", "eighth triplet",
    "sixteenth", "sixteenth dotted", "sixteenth triplet",
]


# --- framing ----------------------------------------------------------------


def _frames(mono, n_fft: int, hop: int):
    """Overlapping windows as a strided view — no copy, no loop."""
    import numpy as np

    mono = np.asarray(mono, dtype=np.float64)
    if len(mono) < n_fft:
        mono = np.pad(mono, (0, n_fft - len(mono)))
    count = 1 + (len(mono) - n_fft) // hop
    return np.lib.stride_tricks.as_strided(
        mono, shape=(count, n_fft), strides=(mono.strides[0] * hop, mono.strides[0])
    )


def _power_frames(mono, sample_rate: int, n_fft: int, hop: int, gated: bool = True):
    """Per-frame power spectra, keeping only the frames worth measuring.

    Returns (frequencies, power) where power is (frames, bins). An all-silent
    input keeps every frame rather than none, so callers still get a shape.
    """
    import numpy as np

    windows = _frames(mono, n_fft, hop)
    if gated:
        rms_db = 20.0 * np.log10(np.sqrt((windows**2).mean(axis=1)) + 1e-12)
        if np.isfinite(rms_db).any() and rms_db.max() > -np.inf:
            keep = rms_db > (rms_db.max() + SILENCE_FLOOR_DB)
            if keep.any():
                windows = windows[keep]
    window = np.hanning(n_fft)
    spectra = np.fft.rfft(windows * window, axis=1)
    power = (np.abs(spectra) ** 2) / (window**2).sum()
    return np.fft.rfftfreq(n_fft, 1.0 / sample_rate), power


def envelope(mono, sample_rate: int, rate: int = ENVELOPE_RATE):
    """Amplitude envelope, decimated to `rate` Hz.

    Rectify and low-pass rather than take a Hilbert magnitude: it is the same
    answer for this purpose, costs a fraction as much on a four-minute file, and
    does not depend on the analytic signal being well defined.
    """
    require("envelope extraction")
    import numpy as np
    from scipy import signal

    mono = np.abs(np.asarray(mono, dtype=np.float64))
    step = max(1, int(round(sample_rate / rate)))
    if len(mono) < 64:
        # Too short to filter — sosfiltfilt needs more samples than its padding.
        # Nothing meaningful is being smoothed at this length anyway.
        return mono[::step], sample_rate / step
    cutoff = min(rate / 2.0 * 0.8, 60.0)
    sos = signal.butter(4, cutoff, btype="low", fs=sample_rate, output="sos")
    smoothed = signal.sosfiltfilt(sos, mono)
    return np.maximum(smoothed[::step], 0.0), sample_rate / step


# --- spectrum ---------------------------------------------------------------


def third_octave_bands(mono, sample_rate: int) -> Dict[str, object]:
    """Long-term average spectrum in third-octave bands.

    The single most useful thing to know about a guitar tone, and the one an
    equaliser can act on directly: `match/invert.py` fits the difference between
    two of these onto nine fixed-centre band gains.
    """
    require("spectral analysis")
    import numpy as np

    n_fft = SPECTRUM_FFT
    while n_fft > 256 and n_fft > len(mono):
        n_fft //= 2
    freqs, power = _power_frames(mono, sample_rate, n_fft, max(1, n_fft // 4))
    mean_power = power.mean(axis=0)

    centres, levels = [], []
    nyquist = sample_rate / 2.0
    for centre in THIRD_OCTAVE_CENTRES:
        low, high = centre / 2 ** (1 / 6), centre * 2 ** (1 / 6)
        if low >= nyquist:
            break
        selected = (freqs >= low) & (freqs < min(high, nyquist))
        if not selected.any():
            continue
        centres.append(float(centre))
        levels.append(float(10.0 * np.log10(mean_power[selected].sum() + 1e-30)))
    return {"band_centres_hz": centres, "band_db": levels}


def spectral_tilt(centres: Sequence[float], band_db: Sequence[float]) -> Optional[float]:
    """Slope of the band curve in dB per decade — "dark" or "bright" as a number.

    Fitted only over 50 Hz to 10 kHz and only over bands within 40 dB of the
    loudest: the extremes of the curve are dominated by whatever the source's
    filtering did, not by the amp.
    """
    require("tilt estimation")
    import numpy as np

    centres = np.asarray(centres, dtype=np.float64)
    band_db = np.asarray(band_db, dtype=np.float64)
    if len(centres) < 4:
        return None
    usable = (centres >= 50) & (centres <= 10000) & (band_db > band_db.max() - 40)
    if usable.sum() < 4:
        return None
    slope, _ = np.polyfit(np.log10(centres[usable]), band_db[usable], 1)
    return float(slope)


def corner_frequencies(centres: Sequence[float], band_db: Sequence[float]) -> Dict[str, Optional[float]]:
    """The outer extent of the long-term spectrum, 6 dB below its loudest band.

    A guitar cabinet is a bandpass filter and these two numbers track its
    corners: brighter cab, higher `hf_corner_hz`. But they are a property of the
    *recording*, not a filter measurement, and they carry whatever tilt the
    source has — third-octave bands of white noise rise 3 dB per octave through
    a flat filter, which moves both corners inward by something like 20%.
    Compare them between two fingerprints; do not read one as a cutoff.
    """
    require("corner estimation")
    import numpy as np

    centres = np.asarray(centres, dtype=np.float64)
    band_db = np.asarray(band_db, dtype=np.float64)
    if len(centres) < 6:
        return {"lf_corner_hz": None, "hf_corner_hz": None}

    peak = int(np.argmax(band_db))
    threshold = band_db[peak] - 6.0
    above = np.flatnonzero(band_db >= threshold)
    if len(above) == 0:
        return {"lf_corner_hz": None, "hf_corner_hz": None}

    def interpolate(inside: int, outside: int) -> float:
        """Log-frequency crossing between a band inside the passband and the
        neighbouring one below the threshold."""
        if outside < 0 or outside >= len(centres):
            return float(centres[inside])
        span = band_db[inside] - band_db[outside]
        if span <= 0:
            return float(centres[inside])
        weight = (band_db[inside] - threshold) / span
        logf = np.log10(centres[inside]) + weight * (
            np.log10(centres[outside]) - np.log10(centres[inside])
        )
        return float(10**logf)

    # The outermost bands still inside the passband, not the first dip walking
    # out from the peak. A guitar's spectrum is a comb of harmonics, and the
    # gaps between them are 6 dB down all over the midrange.
    lowest, highest = int(above[0]), int(above[-1])
    return {
        "lf_corner_hz": interpolate(lowest, lowest - 1),
        "hf_corner_hz": interpolate(highest, highest + 1),
    }


def spectral_statistics(mono, sample_rate: int) -> Dict[str, object]:
    """Per-frame centroid, 85% rolloff and flatness, as distributions.

    Percentiles rather than means because a guitar part is not stationary: the
    p10/p90 spread separates a tone that is consistently dark from one that is
    dark on average because half of it is muted.
    """
    require("spectral statistics")
    import numpy as np

    freqs, power = _power_frames(mono, sample_rate, FRAME_FFT, FRAME_HOP)
    total = power.sum(axis=1)
    live = total > 0
    if not live.any():
        empty = {"p10": None, "p50": None, "p90": None}
        return {"centroid_hz": empty, "rolloff85_hz": dict(empty), "flatness": dict(empty)}
    power, total = power[live], total[live]

    centroid = (power * freqs).sum(axis=1) / total
    cumulative = np.cumsum(power, axis=1) / total[:, None]
    rolloff = freqs[np.argmax(cumulative >= 0.85, axis=1)]
    positive = np.maximum(power, 1e-30)
    flatness = np.exp(np.log(positive).mean(axis=1)) / (positive.mean(axis=1))

    def spread(values) -> Dict[str, float]:
        p10, p50, p90 = np.percentile(values, [10, 50, 90])
        return {"p10": float(p10), "p50": float(p50), "p90": float(p90)}

    return {
        "centroid_hz": spread(centroid),
        "rolloff85_hz": spread(rolloff),
        "flatness": spread(flatness),
    }


# --- dynamics ---------------------------------------------------------------


def onsets(mono, sample_rate: int):
    """Note starts, by spectral flux.

    Attack, decay and every reverb estimate below hang off these: an onset is
    where a note begins, and the interesting parts of an envelope are measured
    relative to one.

    The flux is half-wave rectified because an onset is energy *arriving*. Note
    that this matters less than it reads: any fast amplitude change adds sideband
    and edge energy at new frequencies, so a sharp cut registers either way, and
    replacing the rectification with an absolute value does not change what the
    peak picker returns on any signal tried. The rectification is the correct
    definition, not a load-bearing threshold.

    Positions are the **centre** of the analysis window, not its start. `_frames`
    is uncontented — frame *i* covers samples `[i*hop, i*hop + n_fft)` — so a
    transient first raises the flux one whole window before it happens, and
    returning `i*hop` reported every onset about 30 ms early. That bias is larger
    than the attack times measured against it and comparable to the pre-delays,
    so it is corrected here rather than in each caller.
    """
    require("onset detection")
    import numpy as np

    _, power = _power_frames(mono, sample_rate, FRAME_FFT, FRAME_HOP, gated=False)
    magnitude = np.sqrt(power)
    flux = np.maximum(np.diff(magnitude, axis=0), 0).sum(axis=1)
    if len(flux) < 3 or flux.max() <= 0:
        return np.array([], dtype=int)
    flux = flux / flux.max()

    # A local threshold, so a quiet passage still yields its onsets and a loud
    # one does not yield every frame.
    window = max(3, int(0.25 * sample_rate / FRAME_HOP))
    padded = np.pad(flux, window, mode="edge")
    local = np.array([padded[i : i + 2 * window + 1].mean() for i in range(len(flux))])

    # Keep the strongest frame in each neighbourhood rather than the first one
    # over the threshold: a plucked note's attack spreads flux over several
    # frames, and taking the first counts one note twice.
    from scipy import signal as scipy_signal

    picked, _ = scipy_signal.find_peaks(
        flux - local,
        height=0.08,
        distance=max(2, int(0.08 * sample_rate / FRAME_HOP)),
    )
    picked = [index for index in picked if flux[index] > 0.05]
    # `diff` puts frame i's flux between frames i and i+1, so the window it
    # describes is centred half a hop further on than frame i's own centre.
    centre = FRAME_FFT // 2 + FRAME_HOP // 2
    return np.maximum(np.asarray(picked, dtype=int) * FRAME_HOP + centre, 0)


def dynamics(mono, sample_rate: int, samples_2d=None) -> Dict[str, object]:
    """Crest factor, level distribution, loudness range, attack and decay."""
    require("dynamics analysis")
    import numpy as np

    from .io import frame_rms_db

    mono = np.asarray(mono, dtype=np.float64)
    peak = float(np.abs(mono).max()) if mono.size else 0.0
    rms = float(np.sqrt((mono**2).mean())) if mono.size else 0.0
    crest = float(20.0 * np.log10(peak / rms)) if rms > 0 and peak > 0 else None

    levels = frame_rms_db(mono)
    active = levels > (levels.max() + SILENCE_FLOOR_DB) if np.isfinite(levels).any() else None
    kept = levels[active] if active is not None and active.any() else levels
    p10, p50, p90 = np.percentile(kept, [10, 50, 90])

    attack, decay = _attack_and_decay(mono, sample_rate)
    return {
        "crest_db": crest,
        "rms_percentiles_db": {"p10": float(p10), "p50": float(p50), "p90": float(p90)},
        "lra_lu": loudness_range(samples_2d, sample_rate) if samples_2d is not None else None,
        "attack_ms": attack,
        "decay_db_per_s": decay,
    }


def _attack_and_decay(mono, sample_rate: int):
    """Median 10–90% rise time and median post-peak slope, across onsets."""
    import numpy as np

    env, env_rate = envelope(mono, sample_rate)
    starts = onsets(mono, sample_rate)
    if len(starts) == 0 or env.max() <= 0:
        return None, None

    rises, slopes = [], []
    for index, start in enumerate(starts):
        begin = int(start / sample_rate * env_rate)
        stop = int(starts[index + 1] / sample_rate * env_rate) if index + 1 < len(starts) else len(env)
        segment = env[begin:stop]
        if len(segment) < 5 or segment.max() <= 0:
            continue
        top = int(np.argmax(segment))
        # Attack: the crossing of 10% and 90% of this note's own peak.
        if top >= 2:
            low = np.flatnonzero(segment[: top + 1] >= 0.1 * segment[top])
            high = np.flatnonzero(segment[: top + 1] >= 0.9 * segment[top])
            if len(low) and len(high) and high[0] >= low[0]:
                rises.append((high[0] - low[0]) / env_rate * 1000.0)
        # Decay: the slope of the log envelope from the peak down, in dB/s.
        tail = segment[top:]
        tail = tail[tail > segment[top] * 1e-3]
        if len(tail) >= int(0.05 * env_rate):
            db = 20.0 * np.log10(tail + 1e-12)
            time = np.arange(len(db)) / env_rate
            slope, _ = np.polyfit(time, db, 1)
            if slope < 0:
                slopes.append(float(slope))

    return (
        float(np.median(rises)) if rises else None,
        float(np.median(slopes)) if slopes else None,
    )


def loudness_range(samples_2d, sample_rate: int) -> Optional[float]:
    """EBU R128 loudness range, in LU.

    Short-term loudness over 3-second blocks, gated absolutely at -70 LUFS and
    relatively at 20 LU below the gated mean, then the 10th to 95th percentile
    spread. Material shorter than a few blocks has no loudness range to report.
    """
    require("loudness range")
    import numpy as np
    import pyloudnorm

    data = np.asarray(samples_2d, dtype=np.float64)
    if data.ndim == 1:
        data = data[:, None]
    block, hop = int(3.0 * sample_rate), int(1.0 * sample_rate)
    if len(data) < block + hop:
        return None

    meter = pyloudnorm.Meter(sample_rate, block_size=3.0)
    values = []
    for start in range(0, len(data) - block + 1, hop):
        with np.errstate(divide="ignore", invalid="ignore"):
            value = meter.integrated_loudness(data[start : start + block])
        if np.isfinite(value):
            values.append(value)
    values = np.asarray([v for v in values if v > -70.0])
    if len(values) < 3:
        return None
    gated = values[values > values.mean() - 20.0]
    if len(gated) < 3:
        return None
    low, high = np.percentile(gated, [10, 95])
    return float(high - low)


# --- harmonic ---------------------------------------------------------------


def harmonic(mono, sample_rate: int) -> Dict[str, object]:
    """Harmonic-to-noise ratio, odd/even balance and a high-frequency fizz index.

    All three need a monophonic sustained note to mean anything. Measured across
    a chord, "odd/even ratio" is a number about the chord voicing, not about the
    amp's distortion — so when no such segment exists this returns nulls and a
    confidence of zero rather than something that looks like an answer.
    """
    require("harmonic analysis")
    import numpy as np

    empty = {
        "hnr_db": None, "odd_even_ratio": None, "hf_residual_index": None,
        "confidence": 0.0, "f0_hz": None,
    }
    segment = _monophonic_segment(mono, sample_rate)
    if segment is None:
        return empty
    start, stop, f0, periodicity = segment

    piece = np.asarray(mono[start:stop], dtype=np.float64)
    n_fft = 1
    while n_fft * 2 <= len(piece):
        n_fft *= 2
    if n_fft < 2048:
        return empty
    piece = piece[:n_fft]
    spectrum = np.abs(np.fft.rfft(piece * np.hanning(n_fft))) ** 2
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
    resolution = sample_rate / n_fft

    harmonic_power, odd, even = 0.0, 0.0, 0.0
    harmonic_bins = np.zeros(len(spectrum), dtype=bool)
    for number in range(1, 25):
        centre = f0 * number
        if centre >= sample_rate / 2:
            break
        selected = np.abs(freqs - centre) <= max(2.0 * resolution, centre * 0.02)
        if not selected.any():
            continue
        harmonic_bins |= selected
        power = float(spectrum[selected].sum())
        harmonic_power += power
        if number == 1:
            continue
        if number % 2:
            odd += power
        else:
            even += power

    total = float(spectrum.sum())
    residual = max(total - harmonic_power, 0.0)
    hnr = float(10.0 * np.log10(harmonic_power / residual)) if residual > 0 and harmonic_power > 0 else None

    # Fizz: energy above 4 kHz that is not part of the harmonic series. Fuzz and
    # a badly aliasing model both put energy there; a clean amp does not.
    high = freqs >= 4000
    fizz_num = float(spectrum[high & ~harmonic_bins].sum())
    fizz = float(fizz_num / total) if total > 0 else None

    return {
        "hnr_db": hnr,
        "odd_even_ratio": float(odd / even) if even > 0 else None,
        "hf_residual_index": fizz,
        "confidence": float(round(periodicity, 4)),
        "f0_hz": float(f0),
    }


def _monophonic_segment(mono, sample_rate: int):
    """Find the most periodic sustained stretch, or None.

    Autocorrelation per frame gives both a pitch and a periodicity score. A
    segment qualifies when the score stays high and the pitch stays put — that
    is what makes it one note rather than a chord or a transient.
    """
    import numpy as np

    frame = int(0.046 * sample_rate)
    hop = int(0.023 * sample_rate)
    if len(mono) < frame * 3:
        return None
    lowest, highest = 60.0, 1200.0
    min_lag, max_lag = int(sample_rate / highest), int(sample_rate / lowest)

    pitches, scores = [], []
    for start in range(0, len(mono) - frame, hop):
        window = np.asarray(mono[start : start + frame], dtype=np.float64)
        window = window - window.mean()
        energy = float((window**2).sum())
        if energy <= 1e-12:
            pitches.append(0.0), scores.append(0.0)
            continue
        correlation = np.correlate(window, window, mode="full")[frame - 1 :]
        band = correlation[min_lag:max_lag]
        if len(band) == 0 or correlation[0] <= 0:
            pitches.append(0.0), scores.append(0.0)
            continue
        lag = int(np.argmax(band)) + min_lag
        pitches.append(sample_rate / lag)
        scores.append(float(band.max() / correlation[0]))

    pitches, scores = np.asarray(pitches), np.asarray(scores)
    stable = scores > 0.55
    if not stable.any():
        return None

    # Longest run of stable frames whose pitch does not wander.
    best, run_start = None, None
    for index in range(len(stable) + 1):
        if index < len(stable) and stable[index]:
            if run_start is None:
                run_start = index
            elif abs(pitches[index] - pitches[run_start]) > 0.05 * pitches[run_start]:
                if best is None or index - run_start > best[1] - best[0]:
                    best = (run_start, index)
                run_start = index
        elif run_start is not None:
            if best is None or index - run_start > best[1] - best[0]:
                best = (run_start, index)
            run_start = None
    if best is None or (best[1] - best[0]) * hop < 0.1 * sample_rate:
        return None

    first, last = best
    return (
        first * hop,
        min(last * hop + frame, len(mono)),
        float(np.median(pitches[first:last])),
        float(np.median(scores[first:last])),
    )


# --- time effects -----------------------------------------------------------


def time_effects(mono, sample_rate: int) -> Dict[str, object]:
    """Delay time and feedback, reverb decay, and the tempo they relate to.

    None of this needs a render: an echo repeats the envelope at a fixed
    interval and a reverb decays at a fixed rate, and both are visible in the
    target audio alone. That is the point of measuring them — every one of these
    is a preset parameter that can be set without searching for it.
    """
    require("time-effect analysis")
    import numpy as np

    env, env_rate = envelope(mono, sample_rate)
    bpm = tempo(mono, sample_rate)
    result: Dict[str, object] = {
        "delay_ms": None, "delay_confidence": 0.0, "delay_feedback_est": None,
        "delay_note_division": None, "bpm_est": bpm,
        "rt60_s": None, "rt60_confidence": 0.0, "predelay_ms": None,
    }

    delay_ms, confidence, feedback = _detect_delay(mono, sample_rate)
    if delay_ms is not None:
        result.update(
            delay_ms=delay_ms,
            delay_confidence=confidence,
            delay_feedback_est=feedback,
            delay_note_division=_name_division(delay_ms, bpm),
        )

    rt60, rt60_confidence = _detect_rt60(mono, sample_rate, env, env_rate)
    result.update(rt60_s=rt60, rt60_confidence=rt60_confidence)
    result.update(predelay_ms=_detect_predelay(mono, sample_rate, env, env_rate))
    return result


DELAY_RATE = 8000          # the correlation runs here: 0.125 ms is resolution enough
DELAY_MAX_SECONDS = 30.0
DELAY_MIN_PROMINENCE = 0.10   # waveform: below this it is the material, not an effect
DELAY_MIN_ENVELOPE = 0.05     # envelope: below this the repeat is not audible as one

# An echo's second repeat is quieter than its first by the feedback amount. A
# phrase played twice, or a note held through two periods, comes back just as
# loud. Measured: real echoes sit at 0.12-0.71 across feedback 0.15-0.75, a
# repeating four-note pattern at 0.84, and pitch periodicity at 0.98.
#
# The cost of the threshold is stated rather than hidden: because the ratio
# tracks feedback almost exactly, an echo with feedback above about 0.8 is not
# distinguished from a repeating phrase and is reported as no delay. That is a
# near-runaway echo, and a false negative there is much cheaper than setting a
# delay from the tempo.
DELAY_MAX_REPEAT_RATIO = 0.80

# How much of a candidate's correlation has to survive at half (or a third) of its
# lag before the shorter lag is taken as the real one. An echo's own 2T peak is
# weaker than its T peak, so this walks a harmonic back down to its fundamental
# before the decay test runs -- see `fundamental()` for what went wrong without it.
DELAY_SUBMULTIPLE_SHARE = 0.7
DELAY_HARMONICS = 6          # how many descent steps before giving up

# When the envelope is not entitled to veto: the band where it is *saturated* by
# overlapping notes rather than merely quiet. Measured p90/p10 envelope range is
# 53-229 dB for sparse playing, 11-28 dB once notes ring into each other, and
# 0-1 dB for a held note or steady noise.
#
# Both ends must keep the veto, and for opposite reasons. Above the band the
# envelope has real note structure and its opinion is worth having. Below it
# nothing is happening at all — a drone or a steady tone — and there the
# envelope's refusal to endorse anything is exactly right: a waveform repeat in
# a held note is its own pitch period. Suspending the veto down there reported a
# 663 ms delay in a sustained 196 Hz note at confidence 0.83.
DELAY_ENVELOPE_SATURATED_DB = (8.0, 30.0)

# A pitched signal correlates with itself at *every* multiple of its period, so
# the search band fills with a comb of equally tall peaks and prominence stops
# distinguishing anything. An echo adds one peak, and one more per repeat.
# Measured strong-peak counts in the band: 2 for a real echo (T and 2T), 0 for
# dry material, and 121-384 once the notes are pitched. Where the band is combed
# the envelope gets its veto back however saturated it is — otherwise a dense
# pitched part reports a delay at some multiple of its own note period.
DELAY_COMB_PEAKS = 12

# What a detection off combed material is worth: a ceiling, not a discount. On a
# pitched part that repeats a phrase, the phrase period and a tempo-synced delay
# are the same measurement, so no amount of correlation height earns trust here.
# Held just under the 0.15 that `compare._ambience` requires, because scaling
# instead of capping let a strong comb through at 0.27.
DELAY_COMB_CONFIDENCE_CAP = 0.14


def _detect_delay(mono, sample_rate: int):
    """An echo: a lag where both the waveform *and* the envelope repeat.

    Neither one alone works, and the two fail in opposite directions.

    The **envelope** repeats every time a part repeats. A phrase played in
    eighth notes correlates with itself an eighth note later, so envelope
    autocorrelation returns the tempo and calls it a delay — on a synthetic
    420 ms echo over notes 900 ms apart, it returns 900.

    The **waveform** repeats only for a literal copy, which is what an echo is
    and what a re-played note is not. But a sustained pitched note is also a
    literal copy of itself one period later, and at every multiple of a period
    after that, so the search band fills with tall peaks belonging to the note.
    On a held 196 Hz chord the waveform alone returns 51 ms, which is ten
    periods of the fundamental and nothing else.

    An echo is the only thing that shows up in both. So among lags the waveform
    ranks by prominence, the envelope may veto, and both correlations are
    detrended against their own local median first: a smooth envelope correlates
    well with itself at *every* short lag, which would otherwise endorse the
    whole low end of the range.

    That much was not enough, in both directions, and the third test is what
    makes it hold: **an echo gets quieter and a phrase does not.** The
    correlation at 2T over the correlation at T is the feedback amount for an
    echo, and about 1 for anything that merely recurs.

    - Without it, a part whose four-note pattern comes round every 1000 ms
      reported a 1000 ms delay at confidence 0.86 — higher than it ever reports
      a correct answer — because a literal repeat repeats in the waveform and in
      the envelope alike. No amount of agreement between those two separates a
      loop from an echo.
    - The envelope veto was also rejecting *correct* answers on the same
      material: once notes ring into each other the envelope barely dips, so a
      real 420 ms echo scored 0.348 on the waveform and −0.012 on an envelope
      that endorses nothing anywhere. The veto now applies only where the
      envelope has note structure to veto with.

    `delay_confidence` is the waveform correlation height, which doubles as an
    estimate of how loud the repeat is.

    Two limits stand, both reported as *no* delay rather than as a wrong one —
    and the first of those only became true after a review found it was not:

    - Feedback above about 0.85, where the second repeat is nearly as loud as the
      first and the decay test cannot tell it from a recurrence. Abstaining here
      required `fundamental()`: rejecting a lag is useless if its own harmonics
      are then accepted, and they were, at double the true time and high
      confidence.

      This limit is the *price* of the decay test rather than a fault in it, and
      the trade was measured in both directions. Removing the gate recovers every
      runaway echo exactly — 250, 420, 650 ms all correct between 0.85 and 0.95
      feedback — and costs one confident false positive: a phrase repeated
      verbatim comes back as a delay at the loop period with confidence 0.9. No
      other rule catches that, because an unpitched loop leaves no comb in the
      correlation and its envelope repeats as faithfully as its waveform. A missed
      echo is cheaper than an invented one, so the gate stays.
    - Echoes shorter than roughly 150 ms on material whose notes ring longer than
      the echo — a 65 ms slapback under 250 ms notes is not found, and neither is
      a faint 180 ms one. This predates the work above and is unchanged by it: the
      repeat lands inside the note that caused it, so neither the envelope nor the
      prominence separates them.
    """
    import numpy as np
    from scipy import signal
    from scipy.ndimage import median_filter

    data = np.asarray(mono, dtype=np.float64)
    if len(data) > int(DELAY_MAX_SECONDS * sample_rate):
        data = data[: int(DELAY_MAX_SECONDS * sample_rate)]
    step = max(1, int(round(sample_rate / DELAY_RATE)))
    if step > 1:
        data = signal.decimate(data, step, ftype="fir", zero_phase=True)
    rate = sample_rate / step
    if len(data) < int(2.5 * rate):
        return None, 0.0, None

    correlation = _normalised_autocorrelation(data)
    if correlation is None:
        return None, 0.0, None

    low, high = int(0.040 * rate), min(int(2.0 * rate), len(correlation) - 1)
    if high <= low + 8:
        return None, 0.0, None
    band = correlation[low:high]
    prominence_curve = band - median_filter(
        band, size=int(0.025 * rate) * 2 + 1, mode="nearest"
    )
    peaks, properties = signal.find_peaks(prominence_curve, prominence=0.02)
    if len(peaks) == 0:
        return None, 0.0, None

    # The envelope's own opinion, on its own timebase.
    env, env_rate = envelope(mono, sample_rate)
    env_correlation = _normalised_autocorrelation(env)
    if env_correlation is None:
        return None, 0.0, None
    env_prominence = env_correlation - median_filter(
        env_correlation, size=int(0.100 * env_rate) * 2 + 1, mode="nearest"
    )

    # Is the envelope entitled to an opinion? On overlapping material it stays
    # near-constant, so it endorses nothing anywhere and vetoing on it discards
    # correct answers -- see DELAY_ENVELOPE_SATURATED_DB.
    positive = env[env > 0]
    if len(positive) >= 10:
        p10, p90 = np.percentile(positive, [10, 90])
        env_range_db = float(20.0 * np.log10(max(p90, 1e-12) / max(p10, 1e-12)))
    else:
        env_range_db = 0.0
    saturated_low, saturated_high = DELAY_ENVELOPE_SATURATED_DB
    combed = int((prominence_curve[peaks] >= DELAY_MIN_PROMINENCE).sum()) > DELAY_COMB_PEAKS
    envelope_may_veto = combed or not (saturated_low <= env_range_db < saturated_high)

    def repeat_ratio(lag: int, height: float):
        """How much of the repeat survives to 2T: the feedback, and the test.

        The window around 2T scales with the lag. A fixed ±2 samples let a
        repeating phrase through on a peak a few samples off its true period:
        the candidate at 1004 ms looked for its second repeat at 2008 ms and
        missed the one at 2000, so the loop read as decaying.
        """
        second = 2 * lag
        window = max(2, int(0.005 * lag))
        if second + window >= len(correlation) or height <= 0:
            return None
        return float(correlation[second - window : second + window + 1].max() / height)

    strong_peaks = [int(p) for p in peaks if prominence_curve[p] >= DELAY_MIN_PROMINENCE]

    def fundamental(index: int) -> int:
        """Walk a candidate down to the shortest lag of its own family.

        Whatever repeats at T also repeats at 2T and 3T. Testing 2T for decay
        compares it against 4T and finds it quieter, so a harmonic of a recurring
        pattern passes the very test its fundamental fails — and the loop below
        then accepts it. That is not hypothetical: a 250 ms echo at feedback 0.90
        was rejected correctly at 250 ms and accepted at 500 ms, reporting double
        the truth at confidence 0.76, five times the floor `compare._ambience`
        uses. Descending first means a rejected fundamental takes its whole family
        with it, because every member descends to the same place.

        Searching a fixed set of divisors does not work, which two attempts
        established: dividing by 2, 3 and 4 left 1000 ms descending only to 500 ms,
        and extending to 5 left a 250 ms echo reported at 1750 ms — the 7th
        harmonic. There is no bound on which harmonic carries the most prominence.
        So this searches the peaks that are actually present, for any shorter one
        the candidate is a whole-number multiple of, and takes the shortest.
        """
        lag = index + low
        best = index
        for other in strong_peaks:
            if other >= index:
                continue
            shorter = other + low
            multiple = int(round(lag / shorter))
            if multiple < 2:
                continue
            if abs(lag - multiple * shorter) > max(2.0, 0.01 * lag):
                continue
            if float(band[other]) >= DELAY_SUBMULTIPLE_SHARE * float(band[index]):
                best = min(best, other)
        return best

    best, best_ratio = None, None
    for candidate in np.argsort(properties["prominences"])[::-1]:
        index = int(peaks[candidate])
        if prominence_curve[index] < DELAY_MIN_PROMINENCE:
            break  # sorted by prominence: nothing after this passes either

        index = fundamental(index)
        lag = index + low
        ratio = repeat_ratio(lag, float(band[index]))
        if ratio is not None and ratio >= DELAY_MAX_REPEAT_RATIO:
            # It repeats without getting quieter. That is a phrase coming round
            # again, or a held note correlating with its own period -- not an
            # echo. This is the gate that makes dense material safe, and it does
            # not need the envelope to have any dynamics.
            continue

        position = int(lag / rate * env_rate)
        if ratio is None:
            # 2T is past the end of the excerpt, so decay cannot be checked and
            # the envelope is the only remaining witness.
            if position >= len(env_prominence) or env_prominence[position] < DELAY_MIN_ENVELOPE:
                continue
        elif envelope_may_veto:
            if position >= len(env_prominence) or env_prominence[position] < DELAY_MIN_ENVELOPE:
                continue  # the waveform repeats here but nothing audible does
        best, best_ratio = index, ratio
        break
    if best is None:
        return None, 0.0, None

    height = float(band[best])
    delay_ms = float(round((best + low) / rate * 1000.0, 2))

    # Feedback: an echo with feedback g repeats at 2T with about g times the
    # correlation it had at T. Same quantity the decay gate just tested.
    feedback = None
    if best_ratio is not None and 0.0 <= best_ratio < 1.0:
        feedback = round(best_ratio, 4)

    confidence = min(height, 1.0)
    if combed:
        # A pitched part that repeats its phrase literally repeats it in the
        # waveform and the envelope alike, at a lag that is a whole number of
        # beats — and so does a tempo-synced delay. Nothing in the audio alone
        # separates those two, which is the same shape of problem as strumming
        # against tremolo, and it gets the same answer: report the rate, and let
        # the confidence say whether to believe it. Held below the 0.15 that
        # `compare._ambience` requires, so a combed reading cannot move the
        # objective on its own or outrank a clean detection.
        confidence = min(confidence, DELAY_COMB_CONFIDENCE_CAP)
    return delay_ms, round(confidence, 4), feedback


def _normalised_autocorrelation(signal_1d):
    """Autocorrelation scaled so that lag zero is 1, by FFT.

    Shared by the delay detector's two halves so both are on the same footing:
    a value is the fraction of the signal that repeats at that lag.
    """
    import numpy as np

    data = np.asarray(signal_1d, dtype=np.float64)
    data = data - data.mean()
    if len(data) < 4 or not np.any(data):
        return None
    size = 1 << int(math.ceil(math.log2(2 * len(data))))
    correlation = np.fft.irfft(np.abs(np.fft.rfft(data, size)) ** 2, size)[: len(data)]
    if correlation[0] <= 0:
        return None
    return correlation / correlation[0]


def _detect_rt60(mono, sample_rate: int, env, env_rate: float):
    """Fit the decay of every release segment; report the median and the spread.

    Music is not an impulse. A note that is simply short looks exactly like a
    dry room, so the confidence — how much the segments agree — is not
    decoration, and a single segment is never enough to be sure.
    """
    import numpy as np

    starts = onsets(mono, sample_rate)
    if len(starts) < 2 or env.max() <= 0:
        return None, 0.0

    slopes = []
    for index, start in enumerate(starts):
        begin = int(start / sample_rate * env_rate)
        stop = int(starts[index + 1] / sample_rate * env_rate) if index + 1 < len(starts) else len(env)
        segment = env[begin:stop]
        if len(segment) < int(0.2 * env_rate):
            continue
        top = int(np.argmax(segment))
        tail = segment[top:]
        if len(tail) < int(0.15 * env_rate) or tail[0] <= 0:
            continue
        db = 20.0 * np.log10(np.maximum(tail, tail[0] * 1e-4) / tail[0])
        # Fit between -5 and -25 dB, the usual T20 window: above it is the note
        # still sounding, below it is whatever noise floor the source has.
        usable = (db <= -5.0) & (db >= -25.0)
        if usable.sum() < int(0.05 * env_rate):
            continue
        time = np.arange(len(db)) / env_rate
        slope, _ = np.polyfit(time[usable], db[usable], 1)
        if slope < -1.0:
            slopes.append(-60.0 / slope)

    if not slopes:
        return None, 0.0
    slopes = np.asarray(slopes)
    median = float(np.median(slopes))
    if len(slopes) == 1:
        return round(median, 4), 0.2
    # Agreement, as the inverse of the relative spread. Segments that disagree
    # by more than the estimate itself carry no confidence at all.
    spread = float(np.median(np.abs(slopes - median))) / median if median > 0 else 1.0
    return round(median, 4), float(round(max(0.0, 1.0 - spread), 4))


PREDELAY_MAX_MS = 250.0     # past this it is heard as a slapback, not a pre-delay
PREDELAY_MIN_DIP_DB = 2.0   # the direct sound has to fall by this much to see a gap
PREDELAY_MIN_RISE_DB = 1.0  # and the tail has to come back up by this much
PREDELAY_DIP_TOLERANCE_DB = 1.0  # how close to the floor still counts as in the dip
PREDELAY_MIN_SEGMENTS = 2   # one shoulder is a note shape; two is an effect
PREDELAY_PRIMARY_GAP_MS = 400.0  # an onset closer than this belongs to the previous note


def _detect_predelay(mono, sample_rate: int, env, env_rate: float) -> Optional[float]:
    """The gap between the direct sound and the arrival of the reverb tail.

    Visible in the envelope as a *shoulder*: the direct sound decays, and then
    the tail arrives and pushes the envelope back up. The lag from the attack to
    that second rise is the pre-delay.

    It is only visible when the two are actually separated — on sustained or
    overlapping playing the tail arrives underneath a note that is still
    sounding, and there is no dip to find. This returns `None` far more often
    than it returns a number, which is correct: a pre-delay invented from a note
    shape would set a reverb parameter from the way someone was playing.

    `PREDELAY_MIN_SEGMENTS` is the substance of that: a single shoulder is how a
    plucked note decays, and only agreement across onsets makes it an effect.
    """
    import numpy as np

    starts = onsets(mono, sample_rate)
    if len(starts) == 0 or env.max() <= 0:
        return None

    span = int(PREDELAY_MAX_MS / 1000.0 * env_rate)
    if span < 4:
        return None

    # Only note starts, not the reverb arriving. A tail loud enough to have a
    # measurable pre-delay is loud enough for the onset detector to call it an
    # onset of its own, and those land about one pre-delay after the note — so
    # measuring from them returns a fraction of the answer and drags the median
    # down with it. An onset within `PREDELAY_PRIMARY_GAP_MS` of the previous one
    # is treated as belonging to it.
    gap_samples = PREDELAY_PRIMARY_GAP_MS / 1000.0 * sample_rate
    primary = [s for i, s in enumerate(starts)
               if i == 0 or (s - starts[i - 1]) > gap_samples]

    estimates = []
    for start in primary:
        begin = int(start / sample_rate * env_rate)
        # Deliberately *not* clamped at the next onset: the tail's arrival is
        # the thing being measured, and clamping there cuts it off.
        segment = env[begin:begin + span]
        if len(segment) < 4:
            continue
        # Anchor on the *direct* attack, which is at the onset — not on the
        # loudest point in the window. A long reverb tail can carry more envelope
        # than the short sound that caused it, and anchoring on the maximum then
        # starts the search inside the tail and measures its first wobble.
        attack_window = max(2, int(0.030 * env_rate))
        peak = int(np.argmax(segment[:attack_window]))
        tail = segment[peak:]
        if len(tail) < 4 or tail[0] <= 0:
            continue

        db = 20.0 * np.log10(np.maximum(tail, tail[0] * 1e-6) / tail[0])

        # The crossover is the *end* of the dip — the last moment still at the
        # floor before the tail lifts the envelope again.
        #
        # Two earlier versions are recorded because both looked right and both
        # were wrong in ways the tests did not see. Taking the first local minimum
        # finds envelope ripple. Taking `argmin` over the window returns the first
        # of many equal minima across a silent gap, i.e. the moment the direct
        # sound ended, so it reported a constant ~23 ms whatever the pre-delay was.
        #
        # And anchoring the rise on `argmax(db)` — the version a review caught —
        # only ever worked when the tail was *louder* than the direct sound.
        # `db` is relative to the attack, so `db[0] == 0`; whenever the tail is
        # quieter, as it normally is, `argmax` returned 0 and the onset was
        # skipped. It discarded 108 of 175 onset windows, and the fixture passed
        # only because its tail happened to survive smoothing louder than the
        # 12 ms burst that caused it.
        floor = float(db.min())
        if floor > -PREDELAY_MIN_DIP_DB:
            continue  # the direct sound never falls: nothing is separated
        # Every sample still within a hair of the floor, and the last of them.
        in_dip = np.flatnonzero(db <= floor + PREDELAY_DIP_TOLERANCE_DB)
        crossover = int(in_dip[-1])
        if float(db[crossover:].max() - db[crossover]) < PREDELAY_MIN_RISE_DB:
            continue  # it falls and stays down: a decay, not a pre-delay
        estimates.append((peak + crossover) / env_rate * 1000.0)

    if len(estimates) < PREDELAY_MIN_SEGMENTS:
        return None
    return float(round(float(np.median(estimates)), 2))


def tempo(mono, sample_rate: int) -> Optional[float]:
    """Tempo in BPM, from the self-similarity of the onset envelope."""
    require("tempo estimation")
    import numpy as np

    _, power = _power_frames(mono, sample_rate, FRAME_FFT, FRAME_HOP, gated=False)
    flux = np.maximum(np.diff(np.sqrt(power), axis=0), 0).sum(axis=1)
    if len(flux) < 32 or flux.max() <= 0:
        return None
    flux = flux - flux.mean()
    correlation = np.correlate(flux, flux, mode="full")[len(flux) - 1 :]
    if correlation[0] <= 0:
        return None
    correlation /= correlation[0]

    frame_rate = sample_rate / FRAME_HOP
    low = int(60.0 / 200.0 * frame_rate)   # 200 BPM
    high = int(60.0 / 40.0 * frame_rate)   # 40 BPM
    if high >= len(correlation) or high <= low:
        return None
    lag = int(np.argmax(correlation[low:high])) + low
    if correlation[lag] < 0.1:
        return None
    return float(round(60.0 * frame_rate / lag, 2))


def _name_division(delay_ms: float, bpm: Optional[float]) -> Optional[str]:
    """Name a delay time as a note division, when one fits within 5%."""
    if not bpm or bpm <= 0:
        return None

    from packs.timing import TimingError, note_ms

    best, error = None, 0.05
    for division in NOTE_DIVISIONS:
        try:
            expected = note_ms(bpm, division)
        except TimingError:
            continue
        if expected <= 0:
            continue
        relative = abs(expected - delay_ms) / expected
        if relative < error:
            best, error = division, relative
    return best


# --- modulation -------------------------------------------------------------


def modulation(mono, sample_rate: int) -> Dict[str, object]:
    """Amplitude modulation rate and depth — tremolo, measured.

    With one honest caveat that `am_confidence` carries: a part strummed four
    times a second modulates its own envelope at 4 Hz, and no analysis of the
    audio alone can separate that from a 4 Hz tremolo. When the detected rate
    lands on the rate the notes are arriving at, the confidence drops and the
    caveat says so, rather than the fingerprint asserting a tremolo that is
    really the playing.

    The frequency-modulation field stays null: vibrato needs pitch tracking that
    only works on the monophonic material this cannot assume, and a wrong rate
    is worse than a missing one.
    """
    require("modulation analysis")
    import numpy as np

    env, env_rate = envelope(mono, sample_rate)
    empty = {"am_rate_hz": None, "am_depth": None, "fm_rate_hz": None, "am_confidence": 0.0}
    if len(env) < int(1.0 * env_rate) or env.mean() <= 0:
        return empty

    centred = env - env.mean()
    window = np.hanning(len(centred))
    spectrum = np.abs(np.fft.rfft(centred * window))
    freqs = np.fft.rfftfreq(len(centred), 1.0 / env_rate)

    band = (freqs >= 0.5) & (freqs <= 20.0)
    if not band.any() or spectrum[band].max() <= 0:
        return empty

    # Prefer a *pure* modulation over a merely loud one. A tremolo is a sine, so
    # nearly all of its envelope energy sits at one frequency; a plucked note is
    # a sharp attack and a decay, whose envelope is rich in harmonics of the
    # note rate. Purity is the fraction of energy at the rate itself rather than
    # at two, three or four times it, and it is what separates a 2 Hz tremolo
    # from someone playing at 2 Hz.
    from scipy import signal as _signal

    indices = np.flatnonzero(band)
    peaks, _ = _signal.find_peaks(spectrum[band])
    candidates = indices[peaks] if len(peaks) else indices[[int(np.argmax(spectrum[band]))]]
    candidates = sorted(candidates, key=lambda i: -spectrum[i])[:6]

    resolution = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 0.0
    best, best_score, best_purity = None, -1.0, 0.0
    for index in candidates:
        rate = float(freqs[index])
        if rate <= 0:
            continue
        fundamental = _band_energy(spectrum, freqs, rate, rate, resolution)
        harmonics = sum(_band_energy(spectrum, freqs, rate * k, rate, resolution)
                        for k in (2, 3, 4))
        purity = fundamental / (fundamental + harmonics) if (fundamental + harmonics) > 0 else 0.0
        score = float(spectrum[index]) * purity**2
        if score > best_score:
            best, best_score, best_purity = index, score, purity
    if best is None:
        return empty

    # Depth as the peak-to-mean ratio of the modulation itself: 0 is steady, 1
    # is an envelope that reaches silence once per cycle.
    amplitude = 2.0 * spectrum[best] / (window.sum())
    depth = float(min(amplitude / env.mean(), 1.0)) if env.mean() > 0 else 0.0
    if depth < MODULATION_FLOOR:
        # Every envelope has some energy at some rate. Naming one below this is
        # reporting the noise floor as a tremolo setting.
        return {"am_rate_hz": None, "am_depth": float(round(depth, 4)),
                "fm_rate_hz": None, "am_confidence": 0.0}

    return {
        "am_rate_hz": float(round(float(freqs[best]), 3)),
        "am_depth": float(round(depth, 4)),
        "fm_rate_hz": None,
        # Purity is the confidence: a rate this impure is the playing, and no
        # amount of analysis of the audio alone will tell the two apart.
        "am_confidence": float(round(min(max(best_purity, 0.0), 1.0), 4)),
    }


def _band_energy(spectrum, freqs, centre: float, reference: float, resolution: float) -> float:
    """Energy within a narrow window of `centre`, sized relative to the rate."""
    import numpy as np

    width = max(0.15 * reference, 2.0 * resolution)
    selected = np.abs(freqs - centre) <= width
    return float((spectrum[selected] ** 2).sum()) if selected.any() else 0.0


# --- stereo -----------------------------------------------------------------


def spatial(samples_2d, sample_rate: int) -> Dict[str, object]:
    """Stereo width and inter-channel correlation, overall and per band.

    Mono input is not a failure — it reports width 0 and correlation 1, which is
    exactly what mono is.
    """
    require("stereo analysis")
    import numpy as np

    data = np.asarray(samples_2d, dtype=np.float64)
    if data.ndim == 1 or data.shape[1] < 2:
        return {"width": 0.0, "correlation": 1.0, "ms_ratio_by_band": []}

    left, right = data[:, 0], data[:, 1]
    mid, side = (left + right) / 2.0, (left - right) / 2.0
    mid_rms, side_rms = float(np.sqrt((mid**2).mean())), float(np.sqrt((side**2).mean()))
    width = float(side_rms / (mid_rms + side_rms)) if (mid_rms + side_rms) > 0 else 0.0

    if left.std() > 0 and right.std() > 0:
        correlation = float(np.corrcoef(left, right)[0, 1])
    else:
        correlation = 1.0

    ratios = []
    if mid_rms > 0 or side_rms > 0:
        mid_bands = third_octave_bands(mid, sample_rate)["band_db"]
        side_bands = third_octave_bands(side, sample_rate)["band_db"]
        for m, s in zip(mid_bands, side_bands):
            m_power, s_power = 10 ** (m / 10.0), 10 ** (s / 10.0)
            total = m_power + s_power
            ratios.append(float(round(s_power / total, 4)) if total > 0 else 0.0)

    return {
        "width": round(width, 4),
        "correlation": round(correlation, 4),
        "ms_ratio_by_band": ratios,
    }


# --- cepstral ---------------------------------------------------------------


def _mel_filterbank(sample_rate: int, n_fft: int, count: int = 40,
                    low: float = 30.0, high: float = 16000.0):
    import numpy as np

    def to_mel(f):
        return 2595.0 * np.log10(1.0 + f / 700.0)

    def from_mel(m):
        return 700.0 * (10.0 ** (m / 2595.0) - 1.0)

    high = min(high, sample_rate / 2.0)
    points = from_mel(np.linspace(to_mel(low), to_mel(high), count + 2))
    bins = np.floor((n_fft + 1) * points / sample_rate).astype(int)
    bins = np.clip(bins, 0, n_fft // 2)

    filters = np.zeros((count, n_fft // 2 + 1))
    for i in range(count):
        left, centre, right = bins[i], bins[i + 1], bins[i + 2]
        if centre == left or right == centre:
            continue
        filters[i, left:centre] = (np.arange(left, centre) - left) / (centre - left)
        filters[i, centre:right] = (right - np.arange(centre, right)) / (right - centre)
    return filters


def cepstral(mono, sample_rate: int, coefficients: int = 13) -> Dict[str, object]:
    """MFCC mean, spread, and the principal directions of their covariance.

    Timbre in a form that compares well between different notes played on
    different instruments — which is what matching a record to a render needs,
    since neither side is playing the same thing.
    """
    require("cepstral analysis")
    import numpy as np
    from scipy.fft import dct

    n_fft = FRAME_FFT
    _, power = _power_frames(mono, sample_rate, n_fft, FRAME_HOP)
    if power.shape[0] == 0:
        return {"mfcc_mean": [], "mfcc_std": [], "mfcc_cov_lowrank": []}

    energies = power @ _mel_filterbank(sample_rate, n_fft).T
    log_energies = np.log(np.maximum(energies, 1e-12))
    mfcc = dct(log_energies, type=2, axis=1, norm="ortho")[:, :coefficients]

    mean = mfcc.mean(axis=0)
    std = mfcc.std(axis=0)
    lowrank: List[float] = []
    if mfcc.shape[0] > coefficients:
        centred = mfcc - mean
        covariance = np.cov(centred, rowvar=False)
        values, vectors = np.linalg.eigh(covariance)
        order = np.argsort(values)[::-1][:3]
        # Each direction scaled by its own standard deviation, so the stored
        # vectors carry both the shape of the variation and how much there is.
        for index in order:
            lowrank.extend((vectors[:, index] * math.sqrt(max(values[index], 0.0))).tolist())

    return {
        "mfcc_mean": [float(v) for v in mean],
        "mfcc_std": [float(v) for v in std],
        "mfcc_cov_lowrank": [float(v) for v in lowrank],
    }
