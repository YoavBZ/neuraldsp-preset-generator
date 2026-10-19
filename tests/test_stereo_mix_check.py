"""learn/stereo_mix_check.py: the pure parts (docs/stereo-and-mix-check-plan.md)."""

import math

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import stereo_mix_check as S  # noqa: E402


def test_pan_law_centre_is_unity_and_pan_of_inverts_it():
    assert S.pan_gains(0) == pytest.approx((1, 1))
    gl, gr = S.pan_gains(-0.6)
    assert gl > 1.3 and gr < 0.45 and gl ** 2 + gr ** 2 == pytest.approx(2)
    for p in (-1, -0.6, 0, 0.3, 1):
        assert S.pan_of(*S.pan_gains(p)) == pytest.approx(p, abs=1e-9)
    assert S.pan_of(0, 0) is None


def test_pan_plan_pans_target_left_and_other_mono_guitars_alternately():
    tracks = ["a/01_Kick.wav", "a/12_ElecGtr1.wav", "a/14_ElecGtr2.wav", "a/16_ElecGtr3.wav",
              "a/18_AcousticGtr.wav", "a/20_GuitarStereo.wav", "a/30_Vox.wav"]
    plan = S.pan_plan(tracks, "a/14_ElecGtr2.wav", stereo={"a/20_GuitarStereo.wav"})
    assert plan["a/14_ElecGtr2.wav"] == S.TARGET_PAN
    assert [plan[t] for t in ("a/12_ElecGtr1.wav", "a/16_ElecGtr3.wav", "a/18_AcousticGtr.wav")] == [0.6, -0.6, 0.6]
    assert plan["a/01_Kick.wav"] is None and plan["a/30_Vox.wav"] is None and plan["a/20_GuitarStereo.wav"] is None


def test_place_keeps_stereo_native_and_centres_or_pans_mono():
    st = np.array([[1.0, 2.0], [3.0, 4.0]])
    assert np.array_equal(S.place(st, None), st.T)
    m = np.array([1.0, -1.0])
    assert np.allclose(S.place(m, None), [m, m])
    gl, gr = S.pan_gains(0.6)
    assert np.allclose(S.place(m, 0.6), [gl * m, gr * m])


def test_modes_mid_is_mono_fold_and_oracle_uses_known_gains():
    rng = np.random.default_rng(0)
    L, R = rng.normal(size=1000), rng.normal(size=1000)
    out = S.modes(np.stack([L, R]), L, (2.0, 1.0))
    assert np.allclose(out["mid"], (L + R) / 2) and np.allclose(out["side"], (L - R) / 2)
    assert np.allclose(out["oracle_pan"], 2 * L + R)
    wl, wr = S.blind_weights(np.stack([L, R]))
    assert np.allclose(out["blind_pan"], wl * L + wr * R)
    assert np.array_equal(S.modes(np.stack([L, 3 * R]), L, (1, 1))["blind_pick"], 3 * R)


def test_snr_is_gain_invariant():
    rng = np.random.default_rng(1)
    r = rng.normal(size=5000)
    n = rng.normal(size=5000)
    assert S.snr_db(3 * (r + 0.1 * n), r) == pytest.approx(S.snr_db(r + 0.1 * n, r))
    assert S.snr_db(r, r) > 100


def test_heldout_fir_recovers_a_filtered_signal_without_fitting_the_scored_half():
    rng = np.random.default_rng(2)
    x = rng.normal(size=40000)
    y = np.convolve(x, [0.5, 0.3, -0.2])[:40000] + 0.01 * rng.normal(size=40000)
    z = S.ls_fir_heldout(x, y, taps=64)
    assert S.snr_db(z, y) > 30


def test_lsd_crest_and_brightness_are_zero_against_itself_and_see_a_lowpass():
    from scipy.signal import butter, sosfilt

    rng = np.random.default_rng(3)
    x = rng.normal(size=96000)
    mask = S.active_frames(x)
    assert S.lsd_db(2 * x, x) == pytest.approx(0, abs=1e-9)
    assert S.crest_db(x, mask) == pytest.approx(S.crest_db(5 * x, mask))
    lp = sosfilt(butter(4, 2000, fs=48000, output="sos"), x)
    assert S.lsd_db(lp, x) > 3 and S.hf_ratio_db(lp) < S.hf_ratio_db(x) - 10


def test_band_boot_weights_bands_not_parts():
    b = S.band_boot([("a", 0.0), ("a", 0.0), ("a", 0.0), ("b", 3.0)], n=200)
    assert b["band_mean"] == 1.5 and b["part_mean"] == 0.75 and b["bands"] == 2
    assert b["lo"] <= 1.5 <= b["hi"]
    assert math.isclose(S.band_boot([("a", 1.0)], n=10)["lo"], 1.0)
