"""Bounded P2 pilot utilities; importing this module performs no data access.

Callers supply catalog metadata, waveforms, the frozen average and score rows.
There is deliberately no CLI, model loading, rendering or result-file access.
Lag convention: ``wet[n + lag]`` aligns with ``di[n]``. Calibration is seconds
0..4; scoring is seconds 4..10. A failed take must remain in the report.

Historical catalog crop selection and lags used all ten seconds: this is not
a pristine calibration/test split. The catalog lag is an inherited prior used
only for consistency QC; operative alignment is always recalibrated on 0..4.
Primary MR-STFT alone differs from training's combined waveform/MR-STFT loss.
Six-second inference also differs from training/validation's three-second context.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path, PurePosixPath
import statistics

SR = 48_000
GUARD = 512
CALIBRATION = 4 * SR
SCORE = 6 * SR
TOTAL = CALIBRATION + SCORE
SPEC_N = 4096
FFTS = (256, 512, 1024, 2048, 4096)
FIR_TAPS = 256
FIR_OFFSETS = tuple(range(-128, 128))
TRAINING_DELAY = 52


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _key(row):
    content, take = row["content"], row["take"]
    if not isinstance(content, str) or not isinstance(take, str) or not take:
        raise ValueError("content and take must be nonempty strings")
    if any(c in take for c in ("/", "\\")) or take in (".", ".."):
        raise ValueError("unsafe take")
    return content, take


def _p2_path(root, relative, role):
    if not isinstance(relative, str) or "\\" in relative:
        raise ValueError("source must be an explicit P2 relative path")
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or len(path.parts) != 4:
        raise ValueError("unsafe P2 source path")
    if (not path.parts[0].startswith("P2_") or path.parts[1:3] != ("audio", role)
            or not path.name.startswith(role + "_") or path.suffix != ".wav"):
        raise ValueError("source must be an explicit P2 audio path with the correct role")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("P2 source escapes downloads root")
    # Also reject a symlink within P2 that points to P1/P3 material.
    if any(p.upper().startswith(("P1_", "P3_")) or p.upper() in ("P1", "P3")
           for p in resolved.relative_to(root).parts):
        raise ValueError("P1/P3 sources are forbidden")
    return resolved


def select_p2_crops(catalog, downloads_root):
    """Join metadata only: first six sorted chords and all six sorted scales.

    Reads no catalog file or audio. Paths may be absent at declaration time;
    traversal, role/content mismatches, symlink escapes and duplicate sources
    are rejected. Returned absolute paths are for later bounded reads.
    """
    root = Path(downloads_root).expanduser().resolve()
    if root.name != "P2-downloads":
        raise ValueError("downloads root must be explicitly named P2-downloads")
    pairs, sources = {}, set()
    for pair in catalog["pairs"]:
        key = _key(pair)
        if key in pairs:
            raise ValueError(f"duplicate pair: {key}")
        paths = {}
        for field, role in (("di", "directinput"), ("micamp", "micamp")):
            path = _p2_path(root, pair[field], role)
            if path in sources:
                raise ValueError("duplicate source path")
            sources.add(path)
            paths[field] = str(path)
        pairs[key] = pair, paths

    groups = {"chords": [], "scales": []}
    seen_crops, slugs = set(), set()
    for crop in catalog["crops"]:
        key = _key(crop)
        start = _integer(crop["start_frame"], "start_frame")
        if start < GUARD:
            raise ValueError("crop lacks leading 512-sample guard")
        identity = (*key, start)
        slug = crop["slug"]
        if not isinstance(slug, str) or not slug or slug in slugs or identity in seen_crops:
            raise ValueError("duplicate or invalid crop identity")
        slugs.add(slug)
        seen_crops.add(identity)
        if key[0] in groups:
            groups[key[0]].append(crop)
    for rows in groups.values():
        rows.sort(key=lambda r: (r["take"], r["start_frame"]))
    if len(groups["chords"]) < 6 or len(groups["scales"]) != 6:
        raise ValueError("need at least six chord crops and exactly six scale crops")
    selected = []
    for crop in groups["chords"][:6] + groups["scales"]:
        key = _key(crop)
        if key not in pairs:
            raise ValueError(f"missing pair: {key}")
        pair, paths = pairs[key]
        for field, role in (("di", "directinput"), ("micamp", "micamp")):
            expected = f"P2_{key[0]}/audio/{role}/{role}_{key[1]}.wav"
            if pair[field] != expected:
                raise ValueError("pair content/take does not match source path")
        lag = _integer(crop["lag_samples"], "lag_samples")
        if abs(lag) > GUARD:
            raise ValueError("catalog lag outside guard")
        selected.append({"slug": crop["slug"], "content": key[0], "take": key[1],
                         "start_frame": crop["start_frame"], "lag_samples": lag, **paths})
    if len({r["take"] for r in selected}) != 12:
        raise ValueError("selected crops must contain 12 distinct takes; no replacements")
    return selected


def read_bounded(path, start_frame):
    """Read exactly ten seconds plus 512 samples on each side, as mono float64.

    Header and length checks precede the bounded read. No resampling, padding,
    whole-file reads or clipping normalization. ``start_frame`` is the DI-time
    origin; read both sources at that origin before applying the fixed lag.
    """
    import numpy as np
    import soundfile as sf

    start = _integer(start_frame, "start_frame")
    if start < GUARD:
        raise ValueError("missing leading guard")
    count = TOTAL + 2 * GUARD
    with sf.SoundFile(str(path)) as source:
        if source.samplerate != SR:
            raise ValueError("sample rate must be 48000")
        if source.frames < start + TOTAL + GUARD:
            raise ValueError("missing ten seconds or trailing guard")
        source.seek(start - GUARD)
        data = source.read(count, dtype="float64", always_2d=True)
    if data.shape[0] != count or data.shape[1] == 0 or not np.isfinite(data).all():
        raise ValueError("short or nonfinite source read")
    return data.mean(axis=1)


def _mono(x, length=None):
    import numpy as np

    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1 or not x.size or (length is not None and len(x) != length):
        raise ValueError("expected mono waveform of the declared length")
    if not np.isfinite(x).all():
        raise ValueError("nonfinite waveform")
    return x


def bandpass(x):
    """One fixed zero-phase fourth-order Butterworth 80..4000 Hz transform."""
    from scipy.signal import butter, sosfiltfilt

    x = _mono(x)
    sos = butter(4, (80, 4000), btype="bandpass", fs=SR, output="sos")
    return sosfiltfilt(sos, x, padtype="odd", padlen=27)


def _gcc_phat(di, wet):
    import numpy as np
    from scipy.fft import next_fast_len

    n = next_fast_len(2 * len(di) - 1)
    # Taper finite-interval edges. Near-zero leakage bins must not receive the
    # same PHAT weight as periodic signal energy and invent a unique delay.
    window = np.hanning(len(di))
    cross = (np.fft.rfft((wet - wet.mean()) * window, n)
             * np.fft.rfft((di - di.mean()) * window, n).conj())
    magnitude = np.abs(cross)
    frequencies = np.fft.rfftfreq(n, 1 / SR)
    in_band = (frequencies >= 80) & (frequencies <= 4000)
    floor = float(magnitude[in_band].max()) * 1e-8
    valid = in_band & (magnitude > floor)
    phat = np.zeros_like(cross)
    np.divide(cross, magnitude, out=phat, where=valid)
    corr = np.fft.irfft(phat, n)
    lags = np.arange(-GUARD, GUARD + 1)
    peaks = np.abs(corr[lags % n])
    best = int(np.argmax(peaks))
    sharpness = float(peaks[best] / max(float(np.median(peaks)), np.finfo(float).tiny))
    outside = np.abs(lags - lags[best]) > 8
    second = float(peaks[outside].max())
    separation = float(peaks[best] / max(second, np.finfo(float).tiny))
    return int(lags[best]), sharpness, separation


@dataclass(frozen=True)
class Calibration:
    lag: int
    polarity: int
    correlation: float
    sharpness: float
    half_lags: tuple[int, int]
    half_sharpness: tuple[float, float]
    peak_separation: float
    half_peak_separation: tuple[float, float]


def calibrate(di_guarded, wet_guarded, catalog_lag):
    """Use only first-four-second samples, including for filter boundaries.

    Require sharpness >10 in the full interval and both two-second halves,
    <=16 samples from the catalog, and a <=8 sample range across all three
    estimates. Each winner must also exceed the strongest absolute peak outside
    its +/-8 sample neighborhood by >1.2x; the inherited catalog prior cannot
    rescue an ambiguous peak. GCC uses mean removal, a symmetric Hann taper
    and only cross-spectrum magnitudes >1e-8 of the in-band maximum before PHAT.
    Pearson correlation of bandpassed calibration
    samples fixes polarity once; its absolute value must be >=0.5.
    """
    import numpy as np

    catalog_lag = _integer(catalog_lag, "catalog_lag")
    if abs(catalog_lag) > GUARD:
        raise ValueError("catalog lag outside +/-512")
    # Do not inspect or filter evaluation samples, even at calibration edges.
    if len(di_guarded) != TOTAL + 2 * GUARD or len(wet_guarded) != TOTAL + 2 * GUARD:
        raise ValueError("expected ten seconds plus both guards")
    di = _mono(di_guarded[GUARD:GUARD + CALIBRATION], CALIBRATION)
    wet = _mono(wet_guarded[GUARD:GUARD + CALIBRATION], CALIBRATION)
    estimates = [_gcc_phat(di, wet)]
    half = CALIBRATION // 2
    estimates += [_gcc_phat(di[s:s + half], wet[s:s + half]) for s in (0, half)]
    lags, sharpness, separation = zip(*estimates)
    lag = lags[0]
    if any(s <= 10 for s in sharpness):
        raise ValueError("calibration GCC-PHAT peak sharpness must exceed 10")
    if any(s <= 1.2 for s in separation):
        raise ValueError("ambiguous GCC-PHAT peak: separation must exceed 1.2")
    if abs(lag - catalog_lag) > 16:
        raise ValueError("calibration/catalog lag mismatch")
    if max(lags) - min(lags) > 8:
        raise ValueError("calibration half-lag disagreement")
    a, b = bandpass(di), bandpass(wet)
    if lag > 0:
        a, b = a[:-lag], b[lag:]
    elif lag < 0:
        a, b = a[-lag:], b[:lag]
    a, b = a - a.mean(), b - b.mean()
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    correlation = float(a @ b / denominator) if denominator else 0.0
    if not math.isfinite(correlation) or abs(correlation) < 0.5:
        raise ValueError("calibration filtered correlation below 0.5")
    return Calibration(lag, 1 if correlation >= 0 else -1, correlation, sharpness[0],
                       tuple(lags[1:]), tuple(sharpness[1:]), separation[0], tuple(separation[1:]))


def align_pair(di_guarded, wet_guarded, calibration):
    """Apply a calibration unchanged to all ten seconds; never fit score lags."""
    di = _mono(di_guarded, TOTAL + 2 * GUARD)
    wet = _mono(wet_guarded, TOTAL + 2 * GUARD)
    lag = _integer(calibration.lag, "lag")
    if abs(lag) > GUARD or calibration.polarity not in (-1, 1):
        raise ValueError("invalid fixed alignment")
    return (di[GUARD:GUARD + TOTAL].copy(),
            calibration.polarity * wet[GUARD + lag:GUARD + lag + TOTAL])


def delay_samples(x, samples=TRAINING_DELAY):
    """Fixed shift, zero-pad/truncate, preserving length; positive means delay.

    Native inference: align to DI, then delay +52 to emulate training wet.
    Morgan inference: retain raw render's 52-sample latency. Morgan baseline
    alone: shift -52 to DI time. Never estimate a prediction-specific delay.
    """
    import numpy as np

    x = _mono(x)
    shift = _integer(samples, "samples")
    out = np.zeros_like(x)
    if shift == 0:
        return x.copy()
    if abs(shift) >= len(x):
        return out
    if shift > 0:
        out[shift:] = x[:-shift]
    else:
        out[:shift] = x[-shift:]
    return out


def waveform_qc(x):
    """QC each unnormalized calibration/score interval separately."""
    import numpy as np

    x = np.asarray(x, dtype=np.float64)
    reasons, metrics = [], {}
    if x.ndim != 1 or len(x) != TOTAL:
        return {"valid": False, "reasons": ["expected ten seconds mono"], "metrics": metrics}
    if not np.isfinite(x).all():
        return {"valid": False, "reasons": ["nonfinite"], "metrics": metrics}
    for name, part in (("calibration", x[:CALIBRATION]), ("score", x[CALIBRATION:])):
        rms = float(np.sqrt(np.mean(part ** 2)))
        clipped = float(np.mean(np.abs(part) >= 0.999))
        frame_rms = np.sqrt(np.mean(part.reshape(-1, SR // 100) ** 2, axis=1))
        active = float(np.mean(frame_rms > frame_rms.max() * 0.01))
        metrics[name] = {"rms": rms, "clipped_fraction": clipped, "active_fraction": active}
        if clipped > 1e-4:
            reasons.append(f"{name}: clipping")
        if rms < 1e-5:
            reasons.append(f"{name}: RMS below 1e-5")
        if active < 0.8:
            reasons.append(f"{name}: active fraction below 0.8")
    return {"valid": not reasons, "reasons": reasons, "metrics": metrics}


def pair_qc(di, wet):
    """Both aligned signals must pass; callers retain failures, without replacement."""
    reports = {"di": waveform_qc(di), "wet": waveform_qc(wet)}
    return {"valid": all(r["valid"] for r in reports.values()), **reports}


def standardize(x):
    """Match direc.py's independent x / (x.std() + 1e-9) * 0.1 (no mean subtraction)."""
    x = _mono(x)
    return x / (x.std() + 1e-9) * 0.1


def scoring_eq_gain(di_score, frozen_average):
    """Six-second DI spectrum, mean removed, subtracted from the frozen average."""
    import numpy as np
    from learn.di_robustness import smoothed_spectrum

    di = _mono(di_score, SCORE)
    average = _mono(frozen_average, SPEC_N // 2 + 1)
    own = smoothed_spectrum(di)
    return np.clip(average - (own - own.mean()), -15, 15)


def apply_fft_eq(x, gain_bins):
    """direc.py's FFT interpolation and +/-15 dB clamp, without FIR substitution."""
    import numpy as np

    x = _mono(x, SCORE)
    gains = np.clip(_mono(gain_bins, SPEC_N // 2 + 1), -15, 15)
    curve = np.interp(np.fft.rfftfreq(len(x), 1 / SR),
                      np.fft.rfftfreq(SPEC_N, 1 / SR), gains)
    return np.fft.irfft(np.fft.rfft(x) * 10 ** (curve / 20), len(x))


def canonical_target(di_score, frozen_average):
    """Return the six-second canonical target before independent standardization."""
    return apply_fft_eq(di_score, scoring_eq_gain(di_score, frozen_average))


@dataclass(frozen=True)
class FIRModel:
    taps: object
    intercept: float
    input_mean: float
    target_mean: float


def fit_calibration_fir(wet_calibration, raw_di_calibration):
    """Centered 256-tap wet->raw DI ridge, only valid rows of seconds 0..4.

    Row for center n uses wet[n-128:n+128], in chronological order. Every
    eighth valid row is fitted. Evaluation targets are not accepted by this API.
    Trim 512 samples from BOTH ends before means or rows, keeping source samples
    strictly within raw seconds 0..4 for every allowed fixed alignment lag.
    Remove trimmed calibration input/target means; restore the intercept.
    Failure of this bounded linear control is INCONCLUSIVE, not evidence of
    irrecoverability by a different inverse or a richer model.
    """
    import numpy as np

    wet = _mono(wet_calibration, CALIBRATION)[GUARD:-GUARD]
    di = _mono(raw_di_calibration, CALIBRATION)[GUARD:-GUARD]
    input_mean, target_mean = float(wet.mean()), float(di.mean())
    rows = np.lib.stride_tricks.sliding_window_view(wet - input_mean, FIR_TAPS)[::8]
    centers = FIR_TAPS // 2 + np.arange(len(rows)) * 8
    rows = np.ascontiguousarray(rows)
    gram = rows.T @ rows
    ridge = 0.001 * float(np.diag(gram).mean())
    if ridge <= 0 or not math.isfinite(ridge):
        raise ValueError("degenerate FIR calibration")
    taps = np.linalg.solve(gram + ridge * np.eye(FIR_TAPS), rows.T @ (di[centers] - target_mean))
    intercept = target_mean - input_mean * float(taps.sum())
    if not np.isfinite(taps).all() or not math.isfinite(intercept):
        raise ValueError("nonfinite FIR coefficients or intercept")
    taps.setflags(write=False)
    return FIRModel(taps, intercept, input_mean, target_mean)


def predict_fir(wet_guarded, model, *, start_frame=GUARD, frames=SCORE):
    """Predict the held six seconds by default; no evaluation target is accepted.

    Supply ONLY the six-second aligned score, reflect-padded by 512 samples
    on each end (predict_fir_score constructs this). No true pre-4/post-10 context.
    """
    import numpy as np

    wet, taps = _mono(wet_guarded, SCORE + 2 * GUARD), _mono(model.taps, FIR_TAPS)
    if not math.isfinite(model.intercept):
        raise ValueError("nonfinite FIR intercept")
    start = _integer(start_frame, "start_frame")
    frames = _integer(frames, "frames")
    left = start - FIR_TAPS // 2
    stop = start + frames + FIR_TAPS // 2 - 1
    if frames <= 0 or start < GUARD or start + frames > GUARD + SCORE or left < 0 or stop > len(wet):
        raise ValueError("missing centered FIR context")
    windows = np.lib.stride_tricks.sliding_window_view(wet[left:stop], FIR_TAPS)
    # Chunking bounds the temporary matrix regardless of requested duration.
    out = np.empty(frames, dtype=np.float64)
    for s in range(0, frames, 4096):
        out[s:s + 4096] = windows[s:s + 4096] @ taps + model.intercept
    return out


def predict_fir_score(wet_score, model):
    """Predict using only the six-second score, with reflected score-only context."""
    import numpy as np

    wet = _mono(wet_score, SCORE)
    return predict_fir(np.pad(wet, (GUARD, GUARD), mode="reflect"), model)


def mrstft_numpy(a, b, ffts=FFTS):
    """NumPy replica of direc.mrstft, including its two epsilon placements.

    Mono or (batch, time); unnormalized one-sided FFT, default centered reflect
    padding, periodic Hann, hop=n//4. Norms cover the full batch, as in torch.
    """
    import numpy as np

    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    if a.shape != b.shape or a.ndim not in (1, 2) or not a.size or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("MR-STFT requires matching finite mono or batch arrays")
    if not ffts or any(not isinstance(n, int) or n < 4 or n % 4 for n in ffts):
        raise ValueError("FFT sizes must be positive multiples of four")
    if a.shape[-1] <= max(ffts) // 2:
        raise ValueError("signal too short for torch reflect padding")
    loss = 0.0
    for n in ffts:
        window = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)
        pad = [(0, 0)] * (a.ndim - 1) + [(n // 2, n // 2)]

        def magnitude(x):
            frames = np.lib.stride_tricks.sliding_window_view(np.pad(x, pad, mode="reflect"), n, axis=-1)
            return np.abs(np.fft.rfft(frames[..., ::n // 4, :] * window, axis=-1)) + 1e-6

        A, B = magnitude(a), magnitude(b)
        loss += (np.linalg.norm(A - B) / (np.linalg.norm(B) + 1e-6)
                 + np.mean(np.abs(np.log(A) - np.log(B))))
    return float(loss / len(ffts))


def lowband_mrstft(a, raw_di):
    """Filter BOTH signals with bandpass(), THEN independently standardize.

    Filter each entire six-second scoring signal separately, then take its
    center three seconds and standardize. Never filter a ten-second concatenation
    across calibration/score. This targets raw DI, separately from canonical EQ.
    """
    a, raw_di = _mono(a, SCORE), _mono(raw_di, SCORE)
    start = (SCORE - 3 * SR) // 2
    center = slice(start, start + 3 * SR)
    return mrstft_numpy(standardize(bandpass(a)[center]), standardize(bandpass(raw_di)[center]))


def score_prediction(prediction, canonical_di, raw_di):
    """Score six-second predictions; primary uses their center three seconds.

    Canonical EQ must be constructed on the whole six-second DI first. Primary
    standardization uses the center three seconds, matching validation context.
    Waveform L1 uses the same standardized center. The raw-DI low-band diagnostic
    filters each six-second score before selecting its center. Nothing
    here estimates delay, polarity or EQ from a prediction's evaluation target.
    """
    import numpy as np

    prediction = _mono(prediction, SCORE)
    canonical_di, raw_di = _mono(canonical_di, SCORE), _mono(raw_di, SCORE)
    start = (SCORE - 3 * SR) // 2
    center = slice(start, start + 3 * SR)
    p, y = standardize(prediction[center]), standardize(canonical_di[center])
    return {"primary": mrstft_numpy(p, y),
            "canonical_waveform_l1": float(np.mean(np.abs(p - y))),
            "raw_lowband": lowband_mrstft(prediction, raw_di)}


GATE_LOSSES = ("native_net", "native_input", "flatref", "morgan_net", "morgan_input",
               "oracle", "fir_native_raw_lowband", "native_input_raw_lowband", "flatref_raw_lowband")


def compare_report(rows, expected):
    """Engineering screen over exactly the declared 12 takes, without dropping.

    ``expected`` is select_p2_crops()'s output (or equivalent frozen metadata).
    Each row repeats slug/content/take, has qc_valid=True and the nine finite,
    nonnegative GATE_LOSSES. Net/input/flatref/Morgan/oracle values are PRIMARY
    canonical MR-STFT; FIR/input low-band values must target RAW DI.
    Flatref's raw-DI low-band loss is reported alongside the FIR control.
    Improvements are computed per take before taking medians; wins are strict.
    A failed FIR control makes interpretation inconclusive, not irrecoverable.
    """
    expected, rows = list(expected), list(rows)
    metrics = {}

    def reject(reason):
        return {"passed": False, "controls_valid": False, "native_screen_pass": False,
                "disposition": "INCONCLUSIVE", "reasons": [reason], "metrics": metrics}

    if len(expected) != 12 or len(rows) != 12:
        return reject("require all 12 declared rows; no missing or dropped takes")
    try:
        declared = {r["slug"]: _key(r) for r in expected}
        if len(declared) != 12 or len({k[1] for k in declared.values()}) != 12:
            return reject("declaration must have 12 distinct slugs and takes")
        if any(sum(k[0] == group for k in declared.values()) != 6 for group in ("chords", "scales")):
            return reject("require six chords and six scales")
        actual = {r["slug"]: r for r in rows}
        if len(actual) != 12 or set(actual) != set(declared):
            return reject("score coverage differs from frozen declaration")
        ordered = [actual[r["slug"]] for r in expected]
        for row in ordered:
            if _key(row) != declared[row["slug"]]:
                return reject("score content/take differs from declaration")
            if row["qc_valid"] is not True:
                return reject("all 12 takes must be QC valid")
            for name in GATE_LOSSES:
                value = row[name]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    return reject(f"invalid or nonfinite loss: {name}")
            if min(row["native_input"], row["flatref"], row["morgan_input"], row["native_input_raw_lowband"]) <= 0:
                return reject("relative improvement requires positive baseline losses")
    except (KeyError, TypeError, ValueError):
        return reject("missing or invalid declaration/score fields")

    primary = [(min(r["native_input"], r["flatref"]) - r["native_net"])
               / min(r["native_input"], r["flatref"]) for r in ordered]
    morgan = [(r["morgan_input"] - r["morgan_net"]) / r["morgan_input"] for r in ordered]
    fir = [(r["native_input_raw_lowband"] - r["fir_native_raw_lowband"])
           / r["native_input_raw_lowband"] for r in ordered]
    groups = {g: statistics.median(v for r, v in zip(ordered, primary) if r["content"] == g)
              for g in ("chords", "scales")}
    metrics = {"primary_median_relative_improvement": statistics.median(primary),
               "primary_wins": sum(v > 0 for v in primary), "group_medians": groups,
               "morgan_median_relative_improvement": statistics.median(morgan),
               "fir_raw_lowband_median_relative_improvement": statistics.median(fir),
               "oracle_max": max(r["oracle"] for r in ordered),
               "fir_control_interpretation": "bounded linear diagnostic; failure is inconclusive",
               "per_take": [{"slug": r["slug"], "primary_relative_improvement": p,
                             "morgan_relative_improvement": m, "fir_raw_lowband_relative_improvement": f,
                             "flatref_raw_lowband": r["flatref_raw_lowband"]}
                            for r, p, m, f in zip(ordered, primary, morgan, fir)]}
    def below_ten_percent(value):
        # Only absorb floating subtraction/division roundoff at the inclusive
        # boundary (e.g. (1 - .9) / 1); wins and group positivity remain strict.
        return value < 0.1 and not math.isclose(value, 0.1, rel_tol=0, abs_tol=8 * math.ulp(0.1))

    native_reasons = []
    if below_ten_percent(metrics["primary_median_relative_improvement"]):
        native_reasons.append("primary median relative improvement below 10%")
    if metrics["primary_wins"] < 9:
        native_reasons.append("fewer than 9 strict primary wins")
    if any(v <= 0 for v in groups.values()):
        native_reasons.append("both content-group medians must improve strictly")
    control_reasons = []
    if below_ten_percent(metrics["morgan_median_relative_improvement"]):
        control_reasons.append("Morgan positive control median improvement below 10%")
    if below_ten_percent(metrics["fir_raw_lowband_median_relative_improvement"]):
        control_reasons.append("FIR raw-DI low-band control median improvement below 10% (inconclusive)")
    if metrics["oracle_max"] >= 1e-6:
        control_reasons.append("every oracle loss must be below 1e-6")
    controls_valid, native_pass = not control_reasons, not native_reasons
    return {"passed": controls_valid and native_pass, "controls_valid": controls_valid,
            "native_screen_pass": native_pass,
            "disposition": "INCONCLUSIVE" if not controls_valid else ("PASS" if native_pass else "MISS"),
            "reasons": native_reasons + control_reasons, "metrics": metrics}
