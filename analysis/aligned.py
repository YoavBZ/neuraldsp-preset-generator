"""How close a render is to a recording of the same performance, as heard.

The project's judge of closeness (`docs/measuring-closeness.md`). A preset is
rendered through the DI of the very take a recording captured, so render and
recording play the same notes at the same instants and can be compared frame by
frame. On a blind 16-trial test the corrected `unpaired-v3` agreed with the
listener 7 times; an aligned log-mel distance frozen before the answers were read
agreed 12 times, as did an unpaired long-term loudness distance. This distance was
built after those answers were read, its family chosen with them in view; it agrees
on 12 of the 14 it scores (it refuses the two where over half the scored frames
are pauses), so that is a sanity check, not validation.

`aligned_distance` compares log-mel spectra (64 bands, 50 Hz–16 kHz, three frame
sizes) of the loudness-normalised render and recording, after:

- **alignment**: the recording's lag behind the render, which belongs to the
  recording, is given (`estimate_lag` estimates it once per recording from several
  renders), and the DI's timeline follows from it and the plugin's latency;
- **frames**: those where the DI plays, plus `tail_s` after each (notes played just
  before the window included), so reverb and delay tails count where a part leaves
  room for them;
- **bands**: those within `floor_db` of the recording's long-term peak, the same
  for every candidate (`bands="recording"`); or, with `bands="union"`, also those
  within `floor_db` of the candidate's, which sees treble the recording lacks at
  the cost of tracking EQ moves less well (`docs/measuring-closeness.md`);
- **level**: the render's level difference is taken out first (the median over the
  cells where the DI plays and the recording is above its floor), then what is left
  of the mean after flooring, so only tone is left (output level is a separate
  control);
- **floor**: in each frame, both sides are clamped at `mask_db` under the
  recording's loudest band in that frame, a rough stand-in for masking (40 dB is a
  judgement call between measured alternatives, `docs/measuring-closeness.md`).

Judge v3 (`JUDGE_V3`, `docs/judge-v3-plan.md`) is an option beside it, held to
`docs/judge-spec.md`: the same bands for every part, and a floor taken from both sides on
levels per Bark (masking spread over frequency, the threshold in quiet, the louder
background).

Windows where more than `max_pauses` of the scored frames are pauses (tails where
the DI is silent) are refused: there the ranking of candidates depends on hiss and
on bleed from other instruments, which this distance does not handle. A silent
lead-in is not scored, so it does not count against a window.

It reports the distance (mean absolute dB difference over the scored cells) and its
two parts: `tonal`, the long-term per-band difference, and `temporal`, what is left
frame by frame (attack, sustain, drive texture, tails).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from . import require

SAMPLE_RATE = 48000
FRAME_SIZES = (1024, 2048, 4096)
MEL_BANDS = 64
FMIN, FMAX = 50.0, 16000.0
FIXED_LOW_HZ = 80.0
# Judge v3's floor (`floor="symmetric"`), on levels per Bark. Masking spreads over
# frequency, further up than down (dB per Bark: the slopes of Schroeder et al. 1979, as
# in the MPEG psychoacoustic models)...
SPREAD_UP_DB, SPREAD_DOWN_DB = 10.0, 25.0
# ...nothing is heard under the threshold in quiet (Terhardt 1979), placed as if the
# loudest cell played at 90 dB SPL...
LOUDEST_SPL = 90.0
# ...nor under the louder side's steady background (hiss, hum, bleed): its level in each
# band where the DI rests, at this percentile.
BACKGROUND_PERCENTILE = 10.0
# Judge v3 (docs/judge-v3-plan.md): fixed bands and that floor, from both sides. Not the
# default until the listening calibration agrees.
JUDGE_V3 = {"bands": "fixed", "floor": "symmetric"}


@dataclass
class AlignedDistance:
    distance: Optional[float]           # mean |ΔdB| over the scored cells, offset removed
    tonal: Optional[float]              # mean |long-term per-band ΔdB|
    temporal: Optional[float]           # mean |frame ΔdB − its band's long-term ΔdB|
    offset_db: Optional[float]          # the removed level offset (render − recording)
    lag_samples: int                    # recording[t] corresponds to render[t − lag]
    frames: int                         # scored frames at the middle frame size
    bands: int                          # scored mel bands at the middle frame size
    reason: Optional[str] = None        # why nothing was scored, when distance is None

    def as_dict(self) -> Dict:
        return dict(self.__dict__)


def _mel_matrix(n_fft: int, sample_rate: int, bark: bool = False):
    import numpy as np

    def hz_to_mel(f):
        return 2595.0 * np.log10(1.0 + np.asarray(f) / 700.0)

    def mel_to_hz(m):
        return 700.0 * (10 ** (np.asarray(m) / 2595.0) - 1.0)

    freqs = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
    edges = mel_to_hz(np.linspace(hz_to_mel(FMIN), hz_to_mel(FMAX), MEL_BANDS + 2))
    matrix = np.zeros((MEL_BANDS, len(freqs)))
    for b in range(MEL_BANDS):
        lo, centre, hi = edges[b], edges[b + 1], edges[b + 2]
        rise = (freqs - lo) / max(centre - lo, 1e-9)
        fall = (hi - freqs) / max(hi - centre, 1e-9)
        matrix[b] = np.clip(np.minimum(rise, fall), 0.0, None)
    if bark:
        # Each band as power per Bark: the mean power of the bins it covers (a density),
        # times the critical bandwidth at its centre. Otherwise a band's level depends on
        # its filter's width: a wide treble band reads up to 13 dB louder than a narrow
        # low one of the same density, a width hearing does not share.
        gain = (1960.0 + edges[1:-1]) ** 2 / (26.81 * 1960.0)               # Hz per Bark
        gain = gain / np.maximum(matrix.sum(axis=1), 1e-12)
        matrix *= gain[:, None]
        _BARK_DB[(n_fft, sample_rate)] = 10.0 * np.log10(gain)
    return matrix, edges[1:-1]


_MELS: Dict = {}
_BARK_DB: Dict = {}            # per band, dB added by reading it per Bark


def _frames(x, n_fft: int):
    import numpy as np

    hop = n_fft // 4
    count = max(1, 1 + (len(x) - n_fft) // hop)
    index = np.arange(n_fft)[None, :] + hop * np.arange(count)[:, None]
    return x[np.minimum(index, len(x) - 1)]


def _logmel(x, n_fft: int, sample_rate: int, bark: bool = False):
    import numpy as np

    key = (n_fft, sample_rate, FMIN, FMAX, MEL_BANDS) + (("bark",) if bark else ())
    if key not in _MELS:
        _MELS[key] = _mel_matrix(n_fft, sample_rate, bark)
    matrix, centres = _MELS[key]
    spectrum = np.abs(np.fft.rfft(_frames(x, n_fft) * np.hanning(n_fft), axis=1)) ** 2
    return 10.0 * np.log10(spectrum @ matrix.T + 1e-12), centres


def _hearing_db(n_fft: int, sample_rate: int):
    """Per-band dB added before choosing bands and floors under `weighting="hearing"`:
    A-weighting at each band's centre, less the band's filter area (wide treble bands
    otherwise gain up to 13 dB from bandwidth alone). Differences are unaffected."""
    import numpy as np

    key = (n_fft, sample_rate, FMIN, FMAX, MEL_BANDS)
    if key not in _MELS:
        _MELS[key] = _mel_matrix(n_fft, sample_rate)
    matrix, centres = _MELS[key]
    f2 = np.asarray(centres) ** 2
    ra = (12194.0 ** 2 * f2 ** 2) / ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2))
                                     * (f2 + 12194.0 ** 2))
    a = 20 * np.log10(ra) + 2.0
    area = 10 * np.log10(matrix.sum(axis=1) + 1e-12)
    return a - (area - area.mean()), np.asarray(centres)


def _masked_floor(S, centres, mask_db: float):
    """Per cell (`S`: frames × bands, power per Bark in dB), the level under which it is
    not heard: `mask_db` under the strongest masker in its frame once spread over
    frequency, or the threshold in quiet, whichever is higher."""
    import numpy as np

    f = np.asarray(centres, dtype=np.float64)
    z = 26.81 * f / (1960.0 + f) - 0.53                    # Bark (Traunmüller 1990)
    floor = np.full(S.shape, -np.inf)
    for b in range(S.shape[1]):                            # band b as the masker
        dz = z - z[b]
        spread = np.where(dz >= 0, SPREAD_UP_DB * dz, -SPREAD_DOWN_DB * dz)
        np.maximum(floor, S[:, b: b + 1] - spread[None, :], out=floor)
    k = f / 1000.0
    quiet = 3.64 * k ** -0.8 - 6.5 * np.exp(-0.6 * (k - 3.3) ** 2) + 1e-3 * k ** 4
    return np.maximum(floor - mask_db, S.max() - LOUDEST_SPL + quiet[None, :])


def _symmetric_difference(R, X, n_fft, sample_rate, playing, scored, bins, mask_db,
                          min_frames):
    """Judge v3's cell differences (frames × bands, render − recording, before the mean
    offset) and the level taken out, or (None, None) when the recording is inaudible
    where the DI plays. `R` and `X` are levels per Bark."""
    import numpy as np

    centres = _MELS[(n_fft, sample_rate, FMIN, FMAX, MEL_BANDS, "bark")][1]
    # Refused as the default judge refuses: on band powers, `mask_db` under the
    # recording's loudest band in the frame, 70 dB under its loudest cell at most.
    rp = R - _BARK_DB[(n_fft, sample_rate)]
    audible = rp >= np.maximum(rp.max() - 70.0, rp.max(axis=1, keepdims=True) - mask_db)
    if audible[playing][:, bins].sum() < min_frames * bins.sum():
        return None, None

    def background(S):
        return _background(S, playing, min_frames)

    def heard(S):
        return S >= np.maximum(_masked_floor(S, centres, mask_db), background(S))

    # The level from the cells both sides hold above their own floors (either, where
    # those are too few), so swapping the two only flips its sign.
    cells = (heard(R) & heard(X))[playing][:, bins]
    if cells.sum() < min_frames * bins.sum():
        cells = (heard(R) | heard(X))[playing][:, bins]
    level = float(np.median((X[playing][:, bins] - R[playing][:, bins])[cells]))
    X = X - level
    # One floor for both: what the louder side masks, the threshold in quiet, and the
    # louder of the two backgrounds, so hiss under the recording's own is not compared.
    shared = np.maximum(_masked_floor(np.maximum(R, X), centres, mask_db),
                        np.maximum(background(R), background(X)))
    R, X = np.maximum(R, shared), np.maximum(X, shared)
    return X[scored][:, bins] - R[scored][:, bins], level


def _background(S, playing, min_frames):
    """The steady floor in each band (hiss, hum, bleed): its level where the DI is not
    playing, at the `BACKGROUND_PERCENTILE`-th percentile, under which tails have
    faded. No floor where the DI rests in fewer than `min_frames` frames."""
    import numpy as np

    rest = ~playing
    if rest.sum() < min_frames:
        return np.full((1, S.shape[1]), -np.inf)
    return np.percentile(S[rest], BACKGROUND_PERCENTILE, axis=0)[None, :]


def _frame_db(x, n_fft: int):
    import numpy as np

    return 10.0 * np.log10(np.mean(_frames(x, n_fft) ** 2, axis=1) + 1e-20)


def _extend(mask, frames: int):
    """`mask` with each True frame carried `frames` frames forward."""
    out = mask.copy()
    for i in mask.nonzero()[0]:
        out[i: i + frames + 1] = True
    return out


def _signal(x, name: str):
    """`x` as mono float64 (a (samples, channels) array is folded), or a refusal."""
    import numpy as np

    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 2:
        if x.shape[1] > 8 or x.shape[1] > x.shape[0]:
            raise ValueError(f"the {name} looks channels-first {x.shape}: pass "
                             f"(samples, channels)")
        x = x.mean(axis=1)
    if x.ndim != 1 or len(x) == 0:
        raise ValueError(f"the {name} is not a non-empty mono or (samples, channels) signal")
    if not np.all(np.isfinite(x)):
        raise ValueError(f"the {name} holds values that are not finite")
    return x


def _segment(x, start: int, length: int):
    """`x[start:start + length]`, zero-padded where that runs off either end."""
    import numpy as np

    out = np.zeros(length)
    lo, hi = max(start, 0), min(start + length, len(x))
    if hi > lo:
        out[lo - start: hi - start] = x[lo:hi]
    return out


def _normalise(x, sample_rate: int):
    from . import io

    lufs = io.loudness_lufs(io.from_samples(x, sample_rate))
    return None if lufs is None else x * 10 ** ((-23.0 - lufs) / 20.0)


def estimate_lag(recording, renders, sample_rate: int = SAMPLE_RATE,
                 max_lag_s: float = 0.05, hint: Optional[int] = None) -> int:
    """Samples the recording lags the renders by (recording[t] ~ render[t - lag]).

    `renders` is one render of the recording's DI (an array, mono or (samples,
    channels)) or, better, a list of several unlike ones (the template and a
    handful of presets): the lag is the peak, within ±`max_lag_s` of `hint` (0 when
    none), of the summed magnitudes of each render's normalised cross-correlation
    with the recording, band-limited to 80 Hz–2 kHz. A real rig and a plugin share
    the performance's low-frequency waveform closely enough, and the magnitude
    ignores polarity (inverted on 19 of the 43 development parts). One render alone can lock onto
    another pitch period: 6 ms off on one of 27 parts, where nine pooled renders
    agreed with another estimate to 0.3 ms on 25. A higher peak just outside the
    window (within twice its width) is refused: the hint is probably wrong.

    The plugin's latency is the same for every preset, so the lag belongs to the
    recording: estimate it once, with a hint such as its catalogued DI-to-recording
    lag less the latency and a window of ±15 ms, and pass it to `aligned_distance`
    for every candidate. (`analysis.align.find_alignment` measures one pair,
    full-band, with the opposite sign.)"""
    require("estimating a lag")
    import numpy as np

    if isinstance(renders, np.ndarray):
        renders = [renders]                        # one render, mono or (samples, channels)
    a = _signal(recording, "recording")
    centre = 0 if hint is None else int(hint)
    span = int(max_lag_s * sample_rate)
    lags = np.arange(centre - 2 * span, centre + 2 * span + 1)   # twice the window
    total, used = np.zeros(len(lags)), 0
    for render in renders:
        b = _signal(render, "render")
        n = min(len(a), len(b))
        x, y = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
        norm = np.linalg.norm(x) * np.linalg.norm(y)
        if norm == 0:
            continue
        size = 1 << int(np.ceil(np.log2(2 * n)))
        freqs = np.fft.rfftfreq(size, 1.0 / sample_rate)
        keep = (freqs >= 80.0) & (freqs <= 2000.0)
        corr = np.abs(np.fft.irfft(np.fft.rfft(x, size) * keep
                                   * np.conj(np.fft.rfft(y, size) * keep), size))
        total += corr[lags % size] / norm
        used += 1
    if not used:
        raise ValueError("the recording or every render is silent; no lag to find")
    inside = np.abs(lags - centre) <= span
    if total[~inside].max() > total[inside].max():
        raise ValueError(f"the correlation peaks outside the search window "
                         f"({centre - span}..{centre + span} samples): the hint is "
                         f"probably wrong")
    return int(lags[inside][np.argmax(total[inside])])


def aligned_distance(recording, render, di, *, lag: int, render_latency: int = 52,
                     sample_rate: int = SAMPLE_RATE, start_s: float = 1.0,
                     end_s: Optional[float] = None, tail_s: float = 1.5,
                     floor_db: float = 30.0, mask_db: float = 40.0,
                     di_floor_db: float = 40.0, min_frames: int = 8,
                     max_pauses: float = 0.5, bands: str = "recording",
                     weighting: str = "flat", min_bands: int = 16,
                     max_band_hz: float = 10000.0,
                     floor: str = "recording") -> AlignedDistance:
    """Distance between `render` (the preset through `di`) and `recording` (the same
    performance through the real rig), over [start_s, end_s) of the recording.

    `lag`: samples the recording lags the render (`estimate_lag`, once per
    recording). `render_latency`: samples the render lags the DI (the plugin's
    latency; 52 for Morgan, 51 for Tone King). Non-finite input is refused with a
    ValueError; a window that cannot be scored gives `distance=None` and a reason.

    `bands="fixed"` (judge v2 as decided, `docs/judge-v2-plan.md`) scores the same mel bands
    for every part and candidate, 80 Hz to `max_band_hz`.

    `weighting="hearing"` (an earlier v2 attempt, `docs/closeness-review-2026-10-10.md`) chooses bands
    and floors on hearing-weighted levels (A-weighting, area-normalised bands), scores
    bands up to `max_band_hz` only, and refuses a window scored on fewer than `min_bands`
    bands at the middle frame size. The default, `"flat"`, is the judge as validated.

    `floor="symmetric"` (judge v3, `docs/judge-v3-plan.md`) floors each cell from both
    sides, on levels per Bark: `mask_db` under the louder of recording and level-matched
    render once spread over frequency like masking, or the threshold in quiet. A loud low
    end then does not floor the treble, missing and excess content are judged alike, and
    no level depends on a mel filter's width. The level is the median difference over
    the cells both sides hold above their own floors. `JUDGE_V3` is judge v3's options.
    """
    require("measuring aligned distance")
    import math

    import numpy as np

    if bands not in ("recording", "union", "fixed"):
        raise ValueError(f"bands must be 'recording', 'union' or 'fixed', not {bands!r}")
    if weighting not in ("flat", "hearing"):
        raise ValueError(f"weighting must be 'flat' or 'hearing', not {weighting!r}")
    if floor not in ("recording", "symmetric"):
        raise ValueError(f"floor must be 'recording' or 'symmetric', not {floor!r}")
    if floor == "symmetric" and (bands != "fixed" or weighting != "flat"):
        raise ValueError("floor='symmetric' goes with bands='fixed' and weighting='flat'")
    bark = floor == "symmetric"
    recording = _signal(recording, "recording")
    render = _signal(render, "render")
    di = _signal(di, "DI")
    shift = int(lag)

    def refuse(reason, frames=0):
        return AlignedDistance(None, None, None, None, shift, frames, 0, reason=reason)

    if not np.any(di):
        return refuse("the DI is silent")
    # The window, trimmed to where the render covers the recording once aligned.
    end = min(len(recording), len(render) + shift)
    if end_s is not None:
        end = min(end, int(end_s * sample_rate))
    start = max(int(start_s * sample_rate), shift if shift > 0 else 0)
    if end - start < sample_rate:
        return refuse("under a second to compare once aligned")
    ref = recording[start:end]
    ren = render[start - shift: end - shift]
    di_start = start - shift - render_latency      # recording[t] <-> di[t - shift - latency]
    ref_n, ren_n = _normalise(ref, sample_rate), _normalise(ren, sample_rate)
    if ref_n is None or ren_n is None:
        return refuse("no measurable loudness on one side")

    totals, tonals, temporals, offsets, kept = [], [], [], [], {}

    def _add(D, level, scored, bins, n_fft):
        offset = float(D.mean())
        D = D - offset
        offset += level
        per_band = D.mean(axis=0)
        totals.append(float(np.mean(np.abs(D))))
        tonals.append(float(np.mean(np.abs(per_band))))
        temporals.append(float(np.mean(np.abs(D - per_band))))
        offsets.append(offset)
        if n_fft == 2048:
            kept.update(frames=int(scored.sum()), bands=int(bins.sum()))

    for n_fft in FRAME_SIZES:
        hop = n_fft // 4
        R, centres = _logmel(ref_n, n_fft, sample_rate, bark)
        X, _ = _logmel(ren_n, n_fft, sample_rate, bark)
        k = min(len(R), len(X))
        R, X = R[:k], X[:k]
        if weighting == "hearing":
            # The same per-band offset on both sides: differences are unchanged, only the
            # band choice and the floors see hearing-weighted levels.
            w, centres = _hearing_db(n_fft, sample_rate)
            R, X = R + w, X + w
        # The DI's frames on the same grid, starting early enough that a note played
        # just before the window still has its tail scored.
        tail = int(round(tail_s * sample_rate / hop))
        pre = int(math.ceil(tail_s * sample_rate / hop))
        dseg = _segment(di, di_start - pre * hop, len(ref) + pre * hop)
        playing = _frame_db(dseg, n_fft) >= _frame_db(di, n_fft).max() - di_floor_db
        scored = _extend(playing, tail)
        playing, scored = playing[pre: pre + k], scored[pre: pre + k]
        if playing.sum() < min_frames:
            return refuse("the DI plays in too few frames", int(playing.sum()))
        pauses = 1.0 - playing.sum() / scored.sum()
        if pauses > max_pauses:
            return refuse(f"{pauses:.0%} of the scored frames are pauses, over "
                          f"{max_pauses:.0%}", int(playing.sum()))
        if floor == "symmetric":
            bins = (centres >= FIXED_LOW_HZ) & (centres <= max_band_hz)
            D, level = _symmetric_difference(R, X, n_fft, sample_rate, playing, scored, bins,
                                             mask_db, min_frames)
            if D is None:
                return refuse("the recording is inaudible where the DI plays",
                              int(playing.sum()))
            _add(D, level, scored, bins, n_fft)
            continue
        # One floor for both sides, from the recording alone: `mask_db` under its
        # loudest band in each frame (70 dB under its loudest cell at most).
        floor_r = np.maximum(R.max() - 70.0, R.max(axis=1, keepdims=True) - mask_db)
        audible = R >= floor_r
        ltas_r = 10 * np.log10(np.mean(10 ** (np.maximum(R, floor_r)[scored] / 10), axis=0))
        bins = ltas_r >= ltas_r.max() - floor_db
        if bands == "fixed":
            # Judge v2 as decided (docs/closeness-review-2026-10-10.md): the same bands for
            # every part and candidate, 80 Hz to `max_band_hz`, whatever the recording's
            # balance, so a dominant low end can't drop the treble from scoring.
            bins = (centres >= FIXED_LOW_HZ) & (centres <= max_band_hz)
        if weighting == "hearing":
            bins &= centres <= max_band_hz
        if bands == "union":
            ltas_x = 10 * np.log10(np.mean(10 ** (np.maximum(X, R.max() - 70.0)[scored] / 10),
                                           axis=0))
            bins |= ltas_x >= ltas_x.max() - floor_db
            if weighting == "hearing":
                bins &= centres <= max_band_hz
        if weighting == "hearing" and n_fft == 2048 and bins.sum() < min_bands:
            return refuse(f"only {int(bins.sum())} bands are scored, under {min_bands}",
                          int(playing.sum()))
        # Level before the floor, so a render that sits a few dB low is not clipped
        # unevenly by it: the median difference where the DI plays and the recording
        # is above its floor, which a silent stretch on one side cannot drag.
        cells = audible[playing][:, bins]
        if cells.sum() < min_frames * bins.sum():
            return refuse("the recording is inaudible where the DI plays", int(playing.sum()))
        level = float(np.median((X[playing][:, bins] - R[playing][:, bins])[cells]))
        R, X = np.maximum(R, floor_r), np.maximum(X - level, floor_r)
        D = X[scored][:, bins] - R[scored][:, bins]
        _add(D, level, scored, bins, n_fft)
    return AlignedDistance(
        distance=float(np.mean(totals)), tonal=float(np.mean(tonals)),
        temporal=float(np.mean(temporals)), offset_db=float(np.mean(offsets)),
        lag_samples=shift, frames=kept.get("frames", 0), bands=kept.get("bands", 0))
