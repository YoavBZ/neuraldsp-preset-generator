"""How close a render is to a recording of the same performance, as heard.

The project's judge of closeness (`docs/measuring-closeness.md`). A preset is
rendered through the DI of the very take a recording captured, so render and
recording play the same notes at the same instants and can be compared frame by
frame — which an unpaired statistic cannot. On a blind 16-trial test the corrected
`unpaired-v3` agreed with the listener 7 times (it rewarded hiss, reverb and tremolo
the listener heard as wrong) and an aligned log-mel distance frozen before the
answers were read 12 times. This distance was built after those answers
were read and agrees 14 times, so that 14 is a sanity check, not validation.

`aligned_distance` compares log-mel spectra (64 bands, 50 Hz–16 kHz, three frame
sizes) of the loudness-normalised render and recording, after:

- **alignment**: the recording's lag behind the render is given, or estimated by
  `estimate_lag` (best once per recording from several renders, around a
  catalogued hint), and the DI's own timeline follows from it and the plugin's
  latency;
- **frames**: those where the DI plays, plus `tail_s` after each, so reverb and
  delay tails count;
- **bins**: those within `floor_db` of either side's long-term peak (union, so a
  boost the reference lacks is still seen);
- **bleed**: bands where the recording, in frames at least `bleed_gap_s` after the
  DI last played, sits less than `bleed_min_db` under its level while the DI plays
  are dropped — a live-room amp track's top octave can be cymbals. The gap keeps
  the guitar's own sustain out: counted from the DI's last frame instead, a plain
  render standing in for the recording had bands flagged in 17 of 162 comparisons
  and every band in 3; from 0.6 s on, none, with the cymbal bleed of two live-room
  parts still found. Without such frames bleed is not measured (`bleed_checked`);
- **level**: the mean difference over the scored cells is removed, so only tone is
  left (output level is a separate control).

It reports the distance (mean absolute dB difference over the scored cells) and its
two parts: `tonal`, the long-term per-band difference, and `temporal`, what is left
frame by frame (attack, sustain, drive texture, tails).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import require

SAMPLE_RATE = 48000
FRAME_SIZES = (1024, 2048, 4096)
MEL_BANDS = 64
FMIN, FMAX = 50.0, 16000.0


@dataclass
class AlignedDistance:
    distance: Optional[float]           # mean |ΔdB| over the scored cells, offset removed
    tonal: Optional[float]              # mean |long-term per-band ΔdB|
    temporal: Optional[float]           # mean |frame ΔdB − its band's long-term ΔdB|
    offset_db: Optional[float]          # the removed level offset (render − recording)
    lag_samples: int                    # recording[t] corresponds to render[t − lag]
    frames: int                         # scored frames at the middle frame size
    bands: int                          # scored mel bands at the middle frame size
    bleed_bands: List[float] = field(default_factory=list)   # dropped band centres, Hz
    bleed_checked: bool = False         # whether the DI was silent long enough to look
    reason: Optional[str] = None        # why nothing was scored, when distance is None

    def as_dict(self) -> Dict:
        return dict(self.__dict__)


def _mel_matrix(n_fft: int, sample_rate: int):
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
    return matrix, edges[1:-1]


_MELS: Dict = {}


def _frames(x, n_fft: int):
    import numpy as np

    hop = n_fft // 4
    count = max(1, 1 + (len(x) - n_fft) // hop)
    index = np.arange(n_fft)[None, :] + hop * np.arange(count)[:, None]
    return x[np.minimum(index, len(x) - 1)]


def _logmel(x, n_fft: int, sample_rate: int):
    import numpy as np

    key = (n_fft, sample_rate)
    if key not in _MELS:
        _MELS[key] = _mel_matrix(n_fft, sample_rate)
    matrix, centres = _MELS[key]
    spectrum = np.abs(np.fft.rfft(_frames(x, n_fft) * np.hanning(n_fft), axis=1)) ** 2
    return 10.0 * np.log10(spectrum @ matrix.T + 1e-12), centres


def _frame_db(x, n_fft: int):
    import numpy as np

    return 10.0 * np.log10(np.mean(_frames(x, n_fft) ** 2, axis=1) + 1e-20)


def _extend(mask, frames: int):
    """`mask` with each True frame carried `frames` frames forward."""
    out = mask.copy()
    for i in mask.nonzero()[0]:
        out[i: i + frames + 1] = True
    return out


def _mono(x):
    import numpy as np

    x = np.asarray(x, dtype=np.float64)
    return x.mean(axis=1) if x.ndim == 2 else x


def _normalise(x, sample_rate: int):
    from . import io

    lufs = io.loudness_lufs(io.from_samples(x, sample_rate))
    return None if lufs is None else x * 10 ** ((-23.0 - lufs) / 20.0)


def estimate_lag(recording, renders, sample_rate: int = SAMPLE_RATE,
                 max_lag_s: float = 0.05, hint: Optional[int] = None) -> int:
    """Samples the recording lags the renders by (recording[t] ~ render[t - lag]).

    `renders` is one render of the recording's DI or, better, several unlike ones
    (the template and a handful of presets): the lag is the peak, within
    ±`max_lag_s` of `hint` (0 when none), of the summed magnitudes of each render's
    normalised cross-correlation with the recording, band-limited to 80 Hz–2 kHz.
    A real rig and a plugin share the performance's low-frequency waveform closely
    enough, and the magnitude ignores polarity (inverted on 20 of the 43 development
    parts). One render alone can lock onto another pitch period: 6 ms off on one of
    27 parts, where nine pooled renders agreed with an independent estimate to
    0.3 ms on 25. Not GCC-PHAT, whose whitening found spurious zero-lag peaks on
    distorted renders.

    The plugin's latency is the same for every preset, so the lag belongs to the
    recording: estimate it once, with a hint such as its catalogued DI-to-recording
    lag less the latency and a window of ±15 ms, and pass it to `aligned_distance`
    for every candidate."""
    import numpy as np

    if isinstance(renders, np.ndarray) and renders.ndim == 1:
        renders = [renders]
    a = _mono(recording)
    centre = 0 if hint is None else int(hint)
    span = int(max_lag_s * sample_rate)
    lags = np.arange(centre - span, centre + span + 1)
    total = np.zeros(len(lags))
    for render in renders:
        b = _mono(render)
        n = min(len(a), len(b))
        x, y = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
        size = 1 << int(np.ceil(np.log2(2 * n)))
        freqs = np.fft.rfftfreq(size, 1.0 / sample_rate)
        keep = (freqs >= 80.0) & (freqs <= 2000.0)
        corr = np.abs(np.fft.irfft(np.fft.rfft(x, size) * keep
                                   * np.conj(np.fft.rfft(y, size) * keep), size))
        total += corr[lags % size] / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-20)
    return int(lags[np.argmax(total)])


def aligned_distance(recording, render, di, *, sample_rate: int = SAMPLE_RATE,
                     render_latency: int = 52, lag: Optional[int] = None,
                     lag_hint: Optional[int] = None,
                     start_s: float = 1.0, end_s: Optional[float] = None,
                     tail_s: float = 1.5, floor_db: float = 30.0,
                     di_floor_db: float = 40.0, bleed_min_db: float = 15.0,
                     bleed_gap_s: float = 1.0, min_frames: int = 8) -> AlignedDistance:
    """Distance between `render` (the preset through `di`) and `recording` (the same
    performance through the real rig), over [start_s, end_s) of the recording.

    `render_latency`: samples the render lags the DI (the plugin's latency; 52 for
    Morgan, 51 for Tone King). `lag`: samples the recording lags the render; estimated
    when not given, around `lag_hint` if one is known (e.g. a catalogued DI-to-recording
    lag less the latency).
    """
    require("measuring aligned distance")
    import numpy as np

    recording, render, di = _mono(recording), _mono(render), _mono(di)
    shift = (estimate_lag(recording, render, sample_rate, hint=lag_hint)
             if lag is None else int(lag))
    # The window, trimmed to where the render covers the recording once aligned.
    end = min(len(recording), len(render) + shift)
    if end_s is not None:
        end = min(end, int(end_s * sample_rate))
    start = max(int(start_s * sample_rate), shift if shift > 0 else 0)
    if end - start < sample_rate:
        return AlignedDistance(None, None, None, None, shift, 0, 0,
                               reason="under a second to compare once aligned")
    ref = recording[start:end]
    ren = render[start - shift: end - shift]
    di_start = start - shift - render_latency
    dseg = di[max(di_start, 0): max(di_start, 0) + len(ref)]
    dseg = np.pad(dseg, (0, len(ref) - len(dseg)))
    ref_n, ren_n = _normalise(ref, sample_rate), _normalise(ren, sample_rate)
    if ref_n is None or ren_n is None:
        return AlignedDistance(None, None, None, None, shift, 0, 0,
                               reason="no measurable loudness on one side")
    di_peak = _frame_db(_mono(di), 2048).max()

    totals, tonals, temporals, offsets, kept = [], [], [], [], {}
    bleed_hz: List[float] = []
    for n_fft in FRAME_SIZES:
        R, centres = _logmel(ref_n, n_fft, sample_rate)
        X, _ = _logmel(ren_n, n_fft, sample_rate)
        k = min(len(R), len(X))
        # Both sides share one floor, 70 dB under the recording's loudest cell, so a
        # silent tail against a noisy one counts as 70 dB at most, not 120.
        floor = R[:k].max() - 70.0
        R, X = np.maximum(R[:k], floor), np.maximum(X[:k], floor)
        playing = _frame_db(dseg, n_fft)[:k] >= di_peak - di_floor_db
        hop_s = (n_fft // 4) / sample_rate
        scored = _extend(playing, int(round(tail_s / hop_s)))
        # Bleed is what the recording holds once the guitar has stopped sounding.
        silent = ~_extend(playing, int(round(bleed_gap_s / hop_s)))
        if playing.sum() < min_frames:
            return AlignedDistance(None, None, None, None, shift, int(playing.sum()), 0,
                                   reason="the DI plays in too few frames")
        ltas_r = 10 * np.log10(np.mean(10 ** (R[scored] / 10), axis=0))
        ltas_x = 10 * np.log10(np.mean(10 ** (X[scored] / 10), axis=0))
        bins = (ltas_r >= ltas_r.max() - floor_db) | (ltas_x >= ltas_x.max() - floor_db)
        checked = bool(silent.sum() >= min_frames)
        if checked:
            bleed = 10 * np.log10(np.mean(10 ** (R[silent] / 10), axis=0))
            playing_level = 10 * np.log10(np.mean(10 ** (R[playing] / 10), axis=0))
            noisy = playing_level - bleed < bleed_min_db
            if n_fft == 2048:
                audible = ltas_r >= ltas_r.max() - 40.0
                bleed_hz = [round(float(c), 1) for c in centres[noisy & audible]]
            bins &= ~noisy
        if bins.sum() == 0:
            return AlignedDistance(None, None, None, None, shift, int(scored.sum()), 0,
                                   reason="no band is both audible and free of bleed")
        D = X[scored][:, bins] - R[scored][:, bins]
        offset = float(D.mean())
        D = D - offset
        per_band = D.mean(axis=0)
        totals.append(float(np.mean(np.abs(D))))
        tonals.append(float(np.mean(np.abs(per_band))))
        temporals.append(float(np.mean(np.abs(D - per_band))))
        offsets.append(offset)
        if n_fft == 2048:
            kept = {"frames": int(scored.sum()), "bands": int(bins.sum())}
    return AlignedDistance(
        distance=float(np.mean(totals)), tonal=float(np.mean(tonals)),
        temporal=float(np.mean(temporals)), offset_db=float(np.mean(offsets)),
        lag_samples=shift, frames=kept.get("frames", 0), bands=kept.get("bands", 0),
        bleed_bands=bleed_hz, bleed_checked=checked)
