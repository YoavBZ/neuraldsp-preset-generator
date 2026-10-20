"""learn/stereo_side_screen.py: the pure parts (docs/stereo-side-plan.md)."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import stereo_mix_check as S  # noqa: E402
from learn import stereo_side_screen as T  # noqa: E402


def test_instrument_key_groups_mics_of_one_take_and_keeps_doubles_apart():
    assert T.instrument_key("x/15_ElecGtr1Mic1.wav") == T.instrument_key("x/16_ElecGtr1Mic2.wav") == "elecgtr1"
    assert T.instrument_key("23_ElecGtr01Amp1.wav") == "elecgtr01"
    assert T.instrument_key("14_ElecGtr1Close.wav") == "elecgtr1"
    assert T.instrument_key("23_AcousticGtr01Mic.wav") == T.instrument_key("24_AcousticGtr01DI.wav")
    assert T.instrument_key("15_ElecGtr1DTAmp.wav") != T.instrument_key("13_ElecGtr1Amp.wav")


def test_electric_excludes_acoustic():
    assert T.is_electric("a/12_ElecGtr1.wav") and T.is_electric("GTR 1 Amp M80.wav")
    assert not T.is_electric("Acoustic GTR TDP-1.wav") and not T.is_electric("01_Kick.wav")


def test_lc_alternates_by_instrument_and_hp_sp_put_all_others_on_one_side():
    tracks = ["01_Kick.wav", "12_ElecGtr1Mic1.wav", "13_ElecGtr1Mic2.wav", "14_ElecGtr2.wav",
              "16_ElecGtr3.wav", "18_ElecGtr4Stereo.wav", "20_Vox.wav"]
    lc = T.scenario_plan(tracks, "14_ElecGtr2.wav", "LC")
    assert lc["14_ElecGtr2.wav"] == 0.0
    assert lc["12_ElecGtr1Mic1.wav"] == lc["13_ElecGtr1Mic2.wav"] == 1.0      # one take, one side
    assert lc["16_ElecGtr3.wav"] == -1.0 and lc["18_ElecGtr4Stereo.wav"] == 1.0
    assert lc["01_Kick.wav"] is None and lc["20_Vox.wav"] is None
    hp = T.scenario_plan(tracks, "14_ElecGtr2.wav", "HP")
    assert hp["14_ElecGtr2.wav"] == -1.0
    assert {hp[t] for t in tracks if T.is_guitar(t) and t != "14_ElecGtr2.wav"} == {1.0}
    sp = T.scenario_plan(tracks, "14_ElecGtr2.wav", "SP")
    assert {sp[t] for t in tracks if T.is_guitar(t)} == {-0.6}


def test_place_folds_a_stereo_track_when_it_is_panned():
    st = np.array([[1.0, 3.0], [2.0, 5.0]])
    assert np.allclose(S.place(st, 1.0), [0 * st.mean(1), np.sqrt(2) * st.mean(1)])     # +1 = hard right


def test_pick_and_side():
    x2 = np.array([[1.0, 2.0], [3.0, 4.0]])
    assert np.array_equal(T.pick(x2, -0.6), x2[0]) and np.array_equal(T.pick(x2, 1), x2[1])
    assert np.allclose(T.pick(x2, 0), [2.0, 3.0])
    assert T.blind_side(0.2) == 0.0 and T.blind_side(-0.5) == -0.5


def _two_sources(n=48000 * 2, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / T.SR
    a = 0.3 * np.sin(2 * np.pi * 440 * t)                      # target, a tone
    b = 0.3 * rng.standard_normal(n)                            # the other, broadband
    return a, b


def test_pan_index_inverts_the_pan_law_per_bin():
    a, _ = _two_sources()
    for p in (-1, -0.6, 0, 0.6):
        gl, gr = S.pan_gains(p)
        ph, e = T.pan_index(T.stft(gl * a), T.stft(gr * a))
        k = e >= 1e-3 * e.max()
        assert np.allclose(ph[k], p, atol=1e-6)


def test_ild_mask_removes_an_opposite_source_and_keeps_the_target():
    a, b = _two_sources()
    gl, gr = S.pan_gains(-0.6)
    hl, hr = S.pan_gains(0.6)
    x2 = np.stack([gl * a + hl * b, gr * a + hr * b])
    picked = T.pick(x2, -0.6)
    masked = T.ild_mask(x2, -0.6)
    assert S.snr_db(masked, a) > S.snr_db(picked, a) + 3
    alone = np.stack([gl * a, gr * a])
    assert S.snr_db(T.ild_mask(alone, -0.6), a) > 40          # a lone target passes untouched


def test_wiener_with_a_perfect_estimate_returns_it_and_irm_is_an_oracle():
    a, b = _two_sources()
    x = a + b
    assert S.snr_db(T.wiener(a, x), a) > 20
    assert S.snr_db(T.irm(x, a), a) > S.snr_db(x, a) + 3


def test_blind_peak_finds_the_louder_source():
    a, b = _two_sources()
    gl, gr = S.pan_gains(0.6)
    x2 = np.stack([gl * b, gr * b])
    assert T.blind_peak(x2) == pytest.approx(0.6, abs=0.06)


def test_si_sdr_matches_the_project_snr_identity():
    a, b = _two_sources()
    est = 0.7 * a + 0.2 * b
    lin = 10 ** (T.si_sdr_db(est, a) / 10)
    assert S.snr_db(est, a) == pytest.approx(10 * np.log10(1 + lin), abs=1e-6)


def test_boot_draws_agree_with_band_boot_and_lobo():
    pairs = [("a", 1.0), ("a", 3.0), ("b", 0.0), ("c", 4.0)]
    bb, draws = T.boot_draws(pairs, n=400)
    assert bb == S.band_boot(pairs, n=400)
    assert draws[int(0.05 * 400)] == pytest.approx(bb["lo"], abs=1e-3)
    assert T.lobo(pairs) == (1.0, 3.0)


def test_holm():
    assert T.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert T.holm([0.5]) == [0.5]


def test_coherence_mask_keeps_a_panned_point_source_and_cuts_uncorrelated_sides():
    a, b = _two_sources()
    rng = np.random.default_rng(3)
    c = rng.standard_normal(len(a)) * np.std(b)
    for p in (0, -0.6):
        gl, gr = S.pan_gains(p)
        alone = np.stack([gl * a, gr * a])
        assert S.snr_db(T.coherence_mask(alone, p), T.pick(alone, p)) > 40   # coherent: untouched
    x2 = np.stack([a + b, a + c])                 # centred target, different takes hard L and R
    assert S.snr_db(T.coherence_mask(x2, 0), a) > S.snr_db(T.pick(x2, 0), a) + 2
    assert S.snr_db(T.coherence_mask(x2, 0, ild=True), a) > S.snr_db(T.pick(x2, 0), a) + 2
