"""Synthetic-only pilot contracts: no dataset/audio/array/model/result files."""

import builtins
from dataclasses import replace
import importlib.util
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.signal import butter, sosfiltfilt

from learn import di_domain_pilot as pilot


def test_import_has_no_optional_imports_or_data_access(monkeypatch):
    original = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"numpy", "scipy", "soundfile", "torch"}:
            raise AssertionError(f"eager optional import: {name}")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    spec = importlib.util.spec_from_file_location("pilot_lazy_test", pilot.__file__)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    assert module.SR == 48000


@pytest.fixture
def catalog():
    pairs, crops = [], []
    for content, count in (("chords", 8), ("scales", 6)):
        for i in range(count):
            take = f"{content}-{i:02}"
            pairs.append({"content": content, "take": take,
                          "di": f"P2_{content}/audio/directinput/directinput_{take}.wav",
                          "micamp": f"P2_{content}/audio/micamp/micamp_{take}.wav"})
            crops.append({"slug": f"crop-{take}", "content": content, "take": take,
                          "start_frame": 48000, "lag_samples": 37})
    # Input order deliberately differs from the declared ordering.
    return {"pairs": pairs[::-1], "crops": crops[::-1]}


def selected(catalog):
    return pilot.select_p2_crops(catalog, "/synthetic/P2-downloads")


def test_selection_frozen_order_and_explicit_content_take_join(catalog):
    rows = selected(catalog)
    assert len(rows) == len({r["take"] for r in rows}) == 12
    assert [r["take"] for r in rows] == [f"{g}-{i:02}" for g in ("chords", "scales") for i in range(6)]
    for row in rows:
        assert Path(row["di"]).name == "directinput_" + row["take"] + ".wav"
        assert row["lag_samples"] == 37
    assert selected({"pairs": catalog["pairs"][::-1], "crops": catalog["crops"][::-1]}) == rows


def test_selection_sorts_by_start_frame_then_rejects_repeated_take(catalog):
    crop = next(r for r in catalog["crops"] if r["take"] == "chords-00")
    catalog["crops"].append({**crop, "slug": "earlier", "start_frame": 24000})
    with pytest.raises(ValueError, match="12 distinct takes"):
        selected(catalog)  # No replacing the second window with a later take.


@pytest.mark.parametrize("field,path", [
    ("di", "P1_chords/audio/directinput/directinput_chords-00.wav"),
    ("micamp", "P3_scales/audio/micamp/micamp_scales-00.wav"),
    ("di", "../P2_chords/audio/directinput/directinput_chords-00.wav"),
    ("di", "/P2_chords/audio/directinput/directinput_chords-00.wav"),
    ("di", "P2_chords\\audio\\directinput\\directinput_chords-00.wav"),
    ("di", "P2_chords/audio/micamp/micamp_chords-00.wav"),
    ("di", "P2_scales/audio/directinput/directinput_chords-00.wav"),
])
def test_selection_rejects_unsafe_or_mismatched_paths(catalog, field, path):
    pair = next(r for r in catalog["pairs"] if r["take"] == "chords-00")
    pair[field] = path
    with pytest.raises(ValueError):
        selected(catalog)


def test_selection_rejects_symlink_escape(catalog, tmp_path):
    root = tmp_path / "P2-downloads"
    root.mkdir()
    (root / "P2_chords").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        pilot.select_p2_crops(catalog, root)


@pytest.mark.parametrize("damage", ["pair", "crop", "source", "missing", "scale", "guard", "lag", "root"])
def test_selection_rejects_missing_duplicates_and_invalid_declarations(catalog, damage):
    if damage == "pair":
        catalog["pairs"].append(dict(catalog["pairs"][0]))
    elif damage == "crop":
        catalog["crops"].append(dict(catalog["crops"][0]))
    elif damage == "source":
        catalog["pairs"][1]["di"] = catalog["pairs"][0]["di"]
    elif damage == "missing":
        catalog["pairs"] = [r for r in catalog["pairs"] if r["take"] != "chords-00"]
    elif damage == "scale":
        catalog["crops"] = [r for r in catalog["crops"] if r["take"] != "scales-00"]
    elif damage == "guard":
        catalog["crops"][0]["start_frame"] = 511
    elif damage == "lag":
        catalog["crops"][0]["lag_samples"] = 513
    if damage == "root":
        with pytest.raises(ValueError, match="root"):
            pilot.select_p2_crops(catalog, "/synthetic/P1-downloads")
    else:
        with pytest.raises(ValueError):
            selected(catalog)


def test_pair_join_does_not_fall_back_to_take_only(catalog):
    pair = next(r for r in catalog["pairs"] if r["take"] == "chords-00")
    pair["content"] = "other"
    with pytest.raises(ValueError, match="missing pair"):
        selected(catalog)


@pytest.fixture
def fake_soundfile(monkeypatch):
    import soundfile

    count, start = pilot.TOTAL + 2 * pilot.GUARD, 48000
    source = SimpleNamespace(samplerate=48000, frames=start + pilot.TOTAL + pilot.GUARD,
                             data=np.tile([0.1, 0.3], (count, 1)), calls=[])

    class File:
        def __init__(self, path):
            source.calls.append(("open", path))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        @property
        def samplerate(self):
            return source.samplerate

        @property
        def frames(self):
            return source.frames

        def seek(self, frame):
            source.calls.append(("seek", frame))

        def read(self, frames, *, dtype, always_2d):
            source.calls.append(("read", frames, dtype, always_2d))
            return source.data

    monkeypatch.setattr(soundfile, "SoundFile", File)
    return source


def test_bounded_read_header_guard_dtype_channels(fake_soundfile):
    result = pilot.read_bounded("synthetic-only.wav", 48000)
    assert result.shape == (pilot.TOTAL + 1024,)
    assert result.dtype == np.float64
    assert np.allclose(result, 0.2)
    assert fake_soundfile.calls == [("open", "synthetic-only.wav"), ("seek", 48000 - 512),
                                   ("read", pilot.TOTAL + 1024, "float64", True)]


@pytest.mark.parametrize("damage", ["rate", "leading", "trailing", "short", "nonfinite"])
def test_bounded_read_refuses_padding_or_bad_source(fake_soundfile, damage):
    start = 48000
    if damage == "rate":
        fake_soundfile.samplerate = 44100
    elif damage == "leading":
        start = 511
    elif damage == "trailing":
        fake_soundfile.frames -= 1
    elif damage == "short":
        fake_soundfile.data = fake_soundfile.data[:-1]
    else:
        fake_soundfile.data[0, 0] = np.nan
    with pytest.raises(ValueError):
        pilot.read_bounded("synthetic-only.wav", start)
    if damage in ("rate", "leading", "trailing"):
        assert not any(c[0] == "read" for c in fake_soundfile.calls)


@pytest.fixture(scope="module")
def noise():
    return np.random.default_rng(19).normal(0, 0.02, pilot.TOTAL + 2 * pilot.GUARD)


@pytest.mark.parametrize("lag,polarity", [(-512, 1), (-37, -1), (0, 1), (37, 1), (512, -1)])
def test_calibration_lag_sign_guards_and_fixed_polarity(noise, lag, polarity):
    wet = polarity * pilot.delay_samples(noise, lag)
    calibration = pilot.calibrate(noise, wet, lag)
    assert calibration.lag == lag
    assert calibration.polarity == polarity
    assert calibration.half_lags == (lag, lag)
    assert calibration.sharpness > 10 and calibration.peak_separation > 1.2
    di, aligned = pilot.align_pair(noise, wet, calibration)
    np.testing.assert_allclose(aligned, di, atol=1e-15)


def test_calibration_is_independent_of_score_and_uses_no_catalog_fallback(noise):
    wet = pilot.delay_samples(noise, 37)
    before = pilot.calibrate(noise, wet, 37)
    changed_di, changed_wet = noise.copy(), wet.copy()
    changed_di[pilot.GUARD + pilot.CALIBRATION:] = np.nan
    changed_wet[pilot.GUARD + pilot.CALIBRATION:] = 0.8
    assert pilot.calibrate(changed_di, changed_wet, 37) == before
    with pytest.raises(ValueError, match="mismatch"):
        pilot.calibrate(noise, wet, 20)  # Difference 17 fails, even though the signal is unambiguous.
    assert pilot.calibrate(noise, wet, 21).lag == 37  # Difference 16 passes.


def test_calibration_rejects_silence(noise):
    with pytest.raises(ValueError, match="sharpness"):
        pilot.calibrate(np.zeros_like(noise), np.zeros_like(noise), 0)


def test_periodic_ambiguity_is_not_rescued_by_catalog():
    # Multiple equally plausible cycle offsets within +/-512.
    t = np.arange(pilot.TOTAL + 1024)
    period = np.random.default_rng(4).normal(0, 0.02, 96)
    di = period[t % len(period)]
    wet = period[(t - 37) % len(period)]
    with pytest.raises(ValueError, match="ambiguous|sharpness"):
        pilot.calibrate(di, wet, 37)


def test_calibration_rejects_half_lag_drift(noise):
    wet = pilot.delay_samples(noise, 20)
    boundary = pilot.GUARD + pilot.CALIBRATION // 2
    other = pilot.delay_samples(noise, 40)
    wet[boundary:] = other[boundary:]
    with pytest.raises(ValueError, match="disagreement|ambiguous"):
        pilot.calibrate(noise, wet, 20)


def test_calibration_rejects_low_filtered_correlation(noise):
    independent = np.random.default_rng(88).normal(0, 0.08, len(noise))
    with pytest.raises(ValueError, match="correlation"):
        pilot.calibrate(noise, pilot.delay_samples(noise, 37) + independent, 37)


@pytest.mark.parametrize("shift,expected", [
    (2, [0, 0, 1, 2, 3]), (-2, [3, 4, 5, 0, 0]), (0, [1, 2, 3, 4, 5]),
    (5, [0] * 5), (-8, [0] * 5),
])
def test_fixed_delay_both_signs_and_no_wrapping(shift, expected):
    np.testing.assert_array_equal(pilot.delay_samples(np.arange(1, 6), shift), expected)


def test_native_and_morgan_inference_timing(noise):
    native = pilot.delay_samples(noise, 37)
    di, aligned = pilot.align_pair(noise, native, pilot.calibrate(noise, native, 37))
    native_network_input = pilot.delay_samples(aligned)  # +52 after native alignment.
    morgan_network_input = pilot.delay_samples(di, 52)  # Synthetic raw renderer latency.
    np.testing.assert_array_equal(native_network_input, morgan_network_input)
    morgan_baseline = pilot.delay_samples(morgan_network_input, -52)
    np.testing.assert_array_equal(morgan_baseline[:-52], di[:-52])
    np.testing.assert_array_equal(morgan_baseline[-52:], 0)


def test_qc_separate_intervals_and_separate_signal_levels():
    x = np.full(pilot.TOTAL, 0.1)
    x[pilot.CALIBRATION:] = 2e-5  # Must not use calibration max to gate score activity.
    assert pilot.waveform_qc(x)["valid"]
    assert pilot.pair_qc(x, x * 2)["valid"]
    x[pilot.CALIBRATION:] = 0
    report = pilot.waveform_qc(x)
    assert not report["valid"]
    assert report["metrics"]["calibration"]["active_fraction"] == 1
    assert report["metrics"]["score"]["active_fraction"] == 0


@pytest.mark.parametrize("interval", [slice(0, pilot.CALIBRATION), slice(pilot.CALIBRATION, pilot.TOTAL)])
def test_qc_clipping_activity_and_rms_exact_boundaries(interval):
    x = np.full(pilot.TOTAL, 0.02)
    part = x[interval]
    n = len(part)
    part[:math.floor(n * 1e-4)] = -0.999
    assert pilot.waveform_qc(x)["valid"]
    part[math.floor(n * 1e-4)] = 0.999
    assert not pilot.waveform_qc(x)["valid"]
    part[:] = 1e-5
    assert pilot.waveform_qc(x)["valid"]
    part[:] = 0.999e-5
    assert not pilot.waveform_qc(x)["valid"]
    frames = part.reshape(-1, 480)
    frames[:] = 0.02
    frames[:len(frames) // 5] = 0
    assert pilot.waveform_qc(x)["valid"]  # Exactly 80% active.
    frames[len(frames) // 5] = 0
    assert not pilot.waveform_qc(x)["valid"]


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_qc_nonfinite_and_both_signals_required(value):
    good = np.full(pilot.TOTAL, 0.02)
    bad = good.copy()
    bad[0] = value
    assert not pilot.pair_qc(good, bad)["valid"]
    assert not pilot.pair_qc(bad, good)["valid"]


def test_eq_clipping_interpolation_and_frozen_average_not_reestimated(monkeypatch):
    from learn import di_robustness

    own = np.linspace(-30, 30, 2049)
    monkeypatch.setattr(di_robustness, "smoothed_spectrum", lambda di: own.copy())
    avg = np.linspace(30, -30, 2049)
    frozen = avg.copy()
    di = np.random.default_rng(2).normal(0, 0.01, pilot.SCORE)
    gain = pilot.scoring_eq_gain(di, avg)
    np.testing.assert_array_equal(gain, np.clip(avg - (own - own.mean()), -15, 15))
    assert gain.min() == -15 and gain.max() == 15
    target = pilot.canonical_target(di, avg)
    curve = np.interp(np.fft.rfftfreq(pilot.SCORE, 1 / 48000),
                      np.fft.rfftfreq(4096, 1 / 48000), gain)
    expected = np.fft.irfft(np.fft.rfft(di) * 10 ** (curve / 20), pilot.SCORE)
    np.testing.assert_allclose(target, expected, rtol=1e-14, atol=1e-14)
    np.testing.assert_array_equal(avg, frozen)
    np.testing.assert_allclose(pilot.apply_fft_eq(di, np.full(2049, 100)), di * 10 ** (15 / 20))
    np.testing.assert_allclose(pilot.apply_fft_eq(di, np.full(2049, -100)), di * 10 ** (-15 / 20))


def test_eq_uses_real_smoothed_spectrum_on_six_seconds():
    from learn.di_robustness import smoothed_spectrum

    x = np.random.default_rng(7).normal(0, 0.02, pilot.SCORE)
    own = smoothed_spectrum(x)
    average = own - own.mean()
    np.testing.assert_allclose(pilot.canonical_target(x, average), x, atol=1e-15)
    with pytest.raises(ValueError, match="length"):
        pilot.canonical_target(x[:-1], average)


def test_standardization_is_std_not_rms_or_mean_subtraction():
    x = np.array([1.0, 2.0, 3.0])
    result = pilot.standardize(x)
    np.testing.assert_allclose(result, x / (x.std() + 1e-9) * 0.1)
    assert result.mean() != 0
    assert result.std() == pytest.approx(0.1)


@pytest.fixture(scope="module")
def fir_case():
    rng = np.random.default_rng(520)
    wet = rng.normal(0.3, 0.1, pilot.TOTAL + 1024)
    # Exact centered inverse with past, present and future taps, plus an intercept.
    taps = np.zeros(256)
    taps[[0, 93, 128, 255]] = [0.07, -0.15, 0.8, 0.12]
    raw_di = 0.04 + np.convolve(wet, taps[::-1], mode="full")[127:127 + len(wet)]
    cal = slice(pilot.GUARD, pilot.GUARD + pilot.CALIBRATION)
    model = pilot.fit_calibration_fir(wet[cal], raw_di[cal])
    return wet, raw_di, taps, model


def test_fir_known_centered_filter_out_of_sample_and_calibration_intercept(fir_case):
    wet, raw_di, taps, model = fir_case
    assert pilot.FIR_OFFSETS == tuple(range(-128, 128))
    np.testing.assert_allclose(model.taps, taps, atol=1e-3)
    assert model.intercept == pytest.approx(0.04, abs=1e-3)
    start = pilot.GUARD + pilot.CALIBRATION
    score = slice(start, start + pilot.SCORE)
    prediction = pilot.predict_fir_score(wet[score], model)
    # Reflected score boundaries differ deliberately from true outside context.
    interior = slice(128, -128)
    error = np.sqrt(np.mean((prediction[interior] - raw_di[score][interior]) ** 2))
    baseline = np.sqrt(np.mean((wet[score][interior] - raw_di[score][interior]) ** 2))
    assert error < baseline * 0.02
    trimmed = wet[pilot.GUARD * 2:pilot.GUARD + pilot.CALIBRATION - pilot.GUARD]
    assert model.input_mean == pytest.approx(trimmed.mean())
    assert model.intercept == pytest.approx(model.target_mean - model.input_mean * model.taps.sum())


def test_fir_fit_excludes_both_512_sample_margins_and_all_evaluation_targets(fir_case):
    wet, raw_di, _, before = fir_case
    cal = slice(pilot.GUARD, pilot.GUARD + pilot.CALIBRATION)
    changed_wet, changed_di = wet[cal].copy(), raw_di[cal].copy()
    # At positive alignment lag, the calibration tail could contain raw post-4s audio.
    for x in (changed_wet, changed_di):
        x[:512] = np.linspace(-10, 20, 512)
        x[-512:] = np.linspace(50, -100, 512)
    after = pilot.fit_calibration_fir(changed_wet, changed_di)
    np.testing.assert_array_equal(after.taps, before.taps)
    assert (after.intercept, after.input_mean, after.target_mean) == (before.intercept, before.input_mean, before.target_mean)
    # No evaluation target parameter exists; whole-ten-second fitting is refused.
    with pytest.raises(ValueError, match="length"):
        pilot.fit_calibration_fir(wet[pilot.GUARD:-pilot.GUARD], raw_di[pilot.GUARD:-pilot.GUARD])


def test_fir_raw_target_scoring_cannot_refit_or_modify_model(fir_case, monkeypatch):
    wet, _, _, model = fir_case
    start = pilot.GUARD + pilot.CALIBRATION
    score = wet[start:start + pilot.SCORE]
    before = model.taps.copy()
    prediction = pilot.predict_fir_score(score, model)
    # Stub only the expensive spectral reductions; the FIR must stay fixed regardless of target.
    monkeypatch.setattr(pilot, "mrstft_numpy", lambda a, b: float(np.mean(np.abs(a - b))))
    pilot.score_prediction(prediction, score * 0.1, score * 20)
    np.testing.assert_array_equal(model.taps, before)
    np.testing.assert_array_equal(pilot.predict_fir_score(score, model), prediction)


def test_fir_prediction_reflects_only_the_six_second_score(fir_case):
    wet, _, _, model = fir_case
    start = pilot.GUARD + pilot.CALIBRATION
    score = wet[start:start + pilot.SCORE]
    expected = pilot.predict_fir(np.pad(score, (512, 512), mode="reflect"), model)
    np.testing.assert_array_equal(pilot.predict_fir_score(score, model), expected)
    with pytest.raises(ValueError, match="length"):
        pilot.predict_fir(wet, model)  # Ten-second/true boundary context forbidden.


@pytest.mark.parametrize("damage", ["taps", "intercept"])
def test_fir_refuses_nonfinite_coefficients(fir_case, damage):
    _, _, _, model = fir_case
    invalid = replace(model, taps=np.full(256, np.nan)) if damage == "taps" else replace(model, intercept=np.inf)
    with pytest.raises(ValueError, match="nonfinite"):
        pilot.predict_fir_score(np.ones(pilot.SCORE), invalid)


def test_fir_refuses_constant_calibration():
    with pytest.raises(ValueError, match="degenerate"):
        pilot.fit_calibration_fir(np.zeros(pilot.CALIBRATION), np.ones(pilot.CALIBRATION))


def test_lowband_freezes_sos_padding_filter_then_center_then_standardize(monkeypatch):
    rng = np.random.default_rng(66)
    a = rng.normal(0, 0.1, pilot.SCORE)
    b = rng.normal(0, 0.1, pilot.SCORE)
    sos = butter(4, (80, 4000), btype="bandpass", fs=48000, output="sos")
    center = slice(72000, 216000)
    filtered = [sosfiltfilt(sos, x, padtype="odd", padlen=27) for x in (a, b)]
    np.testing.assert_array_equal(pilot.bandpass(a), filtered[0])
    seen = []

    def capture(x, y):
        seen.extend((x, y))
        return 1.25

    monkeypatch.setattr(pilot, "mrstft_numpy", capture)
    assert pilot.lowband_mrstft(a, b) == 1.25
    for actual, f in zip(seen, filtered):
        expected = f[center] / (f[center].std() + 1e-9) * 0.1
        np.testing.assert_array_equal(actual, expected)
    with pytest.raises(ValueError, match="length"):
        pilot.lowband_mrstft(np.ones(pilot.TOTAL), np.ones(pilot.TOTAL))


def test_lowband_removes_out_of_band_energy_from_both_signals():
    t = np.arange(pilot.SCORE) / 48000
    di = 0.1 * np.sin(2 * np.pi * 1000 * t)
    a = di + 0.4 * np.sin(2 * np.pi * 10000 * t)
    b = di + 0.3 * np.sin(2 * np.pi * 20 * t)
    full = pilot.mrstft_numpy(pilot.standardize(a[72000:216000]), pilot.standardize(b[72000:216000]))
    center = slice(72000, 216000)
    for x, frequency in ((a, 10000), (b, 20)):
        sinusoid = np.sin(2 * np.pi * frequency * t[center])
        before = abs(x[center] @ sinusoid)
        after = abs(pilot.bandpass(x)[center] @ sinusoid)
        assert after < before * 1e-3
    # Log-magnitude loss still registers small residuals after a finite-order filter.
    assert pilot.lowband_mrstft(a, b) < full * 0.1


def test_score_prediction_only_requested_metrics_and_center_context(monkeypatch):
    a = np.random.default_rng(3).normal(0, 0.1, pilot.SCORE)
    b = a.copy()
    b[:72000] = 100  # Outside primary/L1 center.
    seen = []

    def capture(x, y):
        seen.append((len(x), len(y)))
        return float(np.mean(np.abs(x - y)))

    monkeypatch.setattr(pilot, "mrstft_numpy", capture)
    result = pilot.score_prediction(a, b, a)
    assert result == {"primary": 0.0, "canonical_waveform_l1": 0.0, "raw_lowband": 0.0}
    assert seen == [(144000, 144000), (144000, 144000)]


def test_mrstft_analytic_periodic_hann_dc_fixture_and_added_epsilon():
    # n=8 periodic Hann: nonzero DC/bin1 magnitudes 4 and 2, all other bins zero.
    # Center reflect on constant signals gives 9 frames, all exactly identical.
    b = np.array([4, 2, 0, 0, 0], dtype=float) + 1e-6
    a = np.array([8, 4, 0, 0, 0], dtype=float) + 1e-6
    expected = np.linalg.norm(a - b) * 3 / (np.linalg.norm(b) * 3 + 1e-6) + np.mean(np.abs(np.log(a) - np.log(b)))
    assert pilot.mrstft_numpy(np.full(16, 2.0), np.ones(16), ffts=(8,)) == pytest.approx(expected, abs=1e-9)
    # Add epsilon to each magnitude, do not clamp/floor it. This resolves that distinction near epsilon.
    tiny_a = (a - 1e-6) * 1e-7 + 1e-6
    tiny_b = (b - 1e-6) * 1e-7 + 1e-6
    tiny_expected = np.linalg.norm(tiny_a - tiny_b) * 3 / (np.linalg.norm(tiny_b) * 3 + 1e-6)
    tiny_expected += np.mean(np.abs(np.log(tiny_a) - np.log(tiny_b)))
    assert pilot.mrstft_numpy(np.full(16, 2e-7), np.full(16, 1e-7), ffts=(8,)) == pytest.approx(tiny_expected, abs=1e-12)


def test_mrstft_all_five_ffts_analytic_dc_fixture():
    expected = []
    for n in pilot.FFTS:
        b = np.zeros(n // 2 + 1) + 1e-6
        b[:2] += [n / 2, n / 4]
        a = (b - 1e-6) * 2 + 1e-6
        frames = 1 + 8192 // (n // 4)
        expected.append(np.linalg.norm(a - b) * math.sqrt(frames)
                        / (np.linalg.norm(b) * math.sqrt(frames) + 1e-6)
                        + np.mean(np.abs(np.log(a) - np.log(b))))
    assert pilot.mrstft_numpy(np.full(8192, 2.0), np.ones(8192)) == pytest.approx(np.mean(expected), abs=1e-8)
    assert pilot.mrstft_numpy(np.zeros(8192), np.zeros(8192)) == 0


def test_mrstft_analytic_reflected_edge_impulse_fixture():
    # n=4 periodic Hann is [0, .5, 1, .5]. An impulse at sample 1, with
    # centered reflect padding, gives three nonzero frames: magnitudes
    # [1,0,1], [1,1,1], [.5,.5,.5]. Six remaining frames are all zero.
    x = np.zeros(8)
    x[1] = 1
    expected = math.sqrt(5.75) / (math.sqrt(27) * 1e-6 + 1e-6)
    expected += (5 * math.log((1 + 1e-6) / 1e-6) + 3 * math.log((0.5 + 1e-6) / 1e-6)) / 27
    assert pilot.mrstft_numpy(x, np.zeros(8), ffts=(4,)) == pytest.approx(expected, rel=1e-13, abs=1e-8)


@pytest.mark.parametrize("batch", [False, True])
def test_mrstft_torch_parity_if_available(batch):
    torch = pytest.importorskip("torch")
    from learn.direc import mrstft

    rng = np.random.default_rng(101)
    shape = (2, 8193) if batch else (8193,)
    a, b = rng.normal(0, 0.1, shape), rng.normal(0, 0.1, shape)
    for dtype, tolerance in ((torch.float64, 1e-9), (torch.float32, 2e-5)):
        reference = float(mrstft(torch.tensor(a, dtype=dtype), torch.tensor(b, dtype=dtype)))
        assert pilot.mrstft_numpy(a, b) == pytest.approx(reference, abs=tolerance, rel=tolerance)


@pytest.fixture
def report_case(catalog):
    expected = selected(catalog)
    rows = [{"slug": r["slug"], "take": r["take"], "content": r["content"], "qc_valid": True,
             "native_net": 0.75, "native_input": 2.0, "flatref": 1.0,
             "morgan_net": 0.75, "morgan_input": 1.0, "oracle": 0.0,
             "fir_native_raw_lowband": 0.75, "native_input_raw_lowband": 1.0,
             "flatref_raw_lowband": 1.1} for r in expected]
    return rows, expected


def test_gate_pass_per_take_better_baseline_groups_controls_and_reporting(report_case):
    rows, expected = report_case
    report = pilot.compare_report(rows[::-1], expected)
    assert report["passed"] and report["controls_valid"] and report["native_screen_pass"]
    assert report["disposition"] == "PASS"
    assert report["metrics"]["primary_median_relative_improvement"] == 0.25
    assert report["metrics"]["primary_wins"] == 12
    assert report["metrics"]["group_medians"] == {"chords": 0.25, "scales": 0.25}
    assert all(r["flatref_raw_lowband"] == 1.1 for r in report["metrics"]["per_take"])


@pytest.mark.parametrize("damage", ["missing", "extra", "duplicate", "take", "slug", "group", "qc", "nan", "loss", "flatraw", "zero"])
def test_gate_strict_coverage_and_invalid_controls_inconclusive(report_case, damage):
    rows, expected = report_case
    if damage == "missing":
        rows.pop()
    elif damage == "extra":
        rows.append(dict(rows[0]))
    elif damage == "duplicate":
        rows[-1] = dict(rows[0])
    elif damage == "take":
        rows[0]["take"] = "wrong-take"
    elif damage == "slug":
        rows[0]["slug"] = "wrong-slug"
    elif damage == "group":
        rows[0]["content"] = "scales"
    elif damage == "qc":
        rows[0]["qc_valid"] = False
    elif damage == "nan":
        rows[0]["native_net"] = np.nan
    elif damage == "loss":
        del rows[0]["oracle"]
    elif damage == "flatraw":
        del rows[0]["flatref_raw_lowband"]
    elif damage == "zero":
        rows[0]["flatref"] = 0
    report = pilot.compare_report(rows, expected)
    assert not report["passed"] and not report["controls_valid"]
    assert report["disposition"] == "INCONCLUSIVE" and report["reasons"]


def test_gate_uses_median_of_per_take_relative_improvements(report_case):
    rows, expected = report_case
    # Ratio of aggregate medians would be dominated by the 100x scale change.
    for i, row in enumerate(rows):
        base = 1 if i < 6 else 100
        row.update(flatref=base, native_input=base * 2, native_net=base * (0.9 if i < 6 else 0.7))
    report = pilot.compare_report(rows, expected)
    assert report["metrics"]["primary_median_relative_improvement"] == pytest.approx(0.2)


def test_gate_ties_are_not_wins_and_no_positive_group_can_hide_other_group(report_case):
    rows, expected = report_case
    for row in rows[:4]:
        row["native_net"] = 1.0  # Eight strict wins with positive median is still a MISS.
    report = pilot.compare_report(rows, expected)
    assert report["metrics"]["primary_wins"] == 8
    assert report["controls_valid"] and not report["native_screen_pass"]
    assert report["disposition"] == "MISS"
    for i, row in enumerate(rows):
        row["native_net"] = 0.5 if i < 9 else 1.5
    report = pilot.compare_report(rows, expected)
    assert report["metrics"]["primary_median_relative_improvement"] > 0.1
    assert report["metrics"]["primary_wins"] == 9  # Isolate the content-group gate.
    assert report["metrics"]["group_medians"]["scales"] == 0
    assert any("group" in reason for reason in report["reasons"])


@pytest.mark.parametrize("control", ["morgan_net", "fir_native_raw_lowband", "oracle"])
def test_gate_failed_positive_control_makes_native_pass_inconclusive(report_case, control):
    rows, expected = report_case
    for row in rows:
        row[control] = 1e-6 if control == "oracle" else 0.95
    report = pilot.compare_report(rows, expected)
    assert report["native_screen_pass"] and not report["controls_valid"]
    assert report["disposition"] == "INCONCLUSIVE" and not report["passed"]
    if control == "fir_native_raw_lowband":
        assert "inconclusive" in report["metrics"]["fir_control_interpretation"]


def test_gate_thresholds_inclusive_except_oracle_and_group_wins(report_case):
    rows, expected = report_case
    for row in rows:
        row.update(native_input=20.0, flatref=10.0, native_net=9.0,
                   morgan_input=10.0, morgan_net=9.0,
                   native_input_raw_lowband=10.0, fir_native_raw_lowband=9.0,
                   oracle=0.999e-6)
    assert pilot.compare_report(rows, expected)["passed"]
    # Exactly nine wins with positive content medians passes.
    for i in (0, 6, 7):
        rows[i]["native_net"] = 10.0
    assert pilot.compare_report(rows, expected)["passed"]


def test_gate_inclusive_tenth_handles_only_machine_roundoff(report_case):
    rows, expected = report_case
    for row in rows:
        row.update(native_net=0.9, morgan_net=0.9, fir_native_raw_lowband=0.9)
    assert pilot.compare_report(rows, expected)["passed"]
    for row in rows:
        row["native_net"] = 0.90000000000001
    assert not pilot.compare_report(rows, expected)["native_screen_pass"]


def test_gate_declaration_itself_must_have_12_distinct_takes_and_six_each(report_case):
    rows, expected = report_case
    expected[0]["take"] = expected[1]["take"]
    assert pilot.compare_report(rows, expected)["disposition"] == "INCONCLUSIVE"
    expected[0]["take"] = "chords-00"
    expected[0]["content"] = "scales"
    assert pilot.compare_report(rows, expected)["disposition"] == "INCONCLUSIVE"
