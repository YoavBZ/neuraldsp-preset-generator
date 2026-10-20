"""Step 0 of docs/separation-finetune-plan.md (`learn/separation_ceiling.py`): the track classes,
the Wiener refinement, the ensemble, X, the band bootstrap and Holm. Fakes only."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import separation_ceiling as S  # noqa: E402


def test_classify_stage_f_tracks():
    ref = "13_ElecGtr1Amp.wav"
    assert S.classify_f(ref, ref, []) == "target"
    assert S.classify_f("14_ElecGtr1Mic2.wav", ref, ["14_ElecGtr1Mic2.wav"]) == "target_other_mic"
    assert S.classify_f("15_ElecGtr1DTAmp.wav", ref, []) == "double_track_of_target"
    assert S.classify_f("19_ElecGtr2DTAmp.wav", ref, []) == "double_track_of_other"
    assert S.classify_f("17_ElecGtr2Amp.wav", ref, []) == "other_electric_guitar"
    assert S.classify_f("GTR 2 Amp M80-Norm_03-01.wav", "GTR 1 Amp M80.wav", []) == "other_electric_guitar"
    for rest in ("30_AcousticGtr.wav", "Acoustic GTR TDP-1.wav", "23_ElecGtr1DI.wav", "GTR KEYS AMP_TF51.wav",
                 "VOX GTR.04_02.wav", "32_IntroClose1.wav", "14_BassDI.wav", "40_LeadVox.wav"):
        assert S.classify_f(rest, ref, []) == "rest", rest


def test_classify_training_tracks():
    assert S.classify_train("GTR DI_TDP-1.wav", True) == "di"
    assert S.classify_train("Pre Record Tracks.wav", False) == "dropped"
    assert S.classify_train("GTR Pre Rec.L.wav", False) == "dropped"
    assert S.classify_train("BAND CLICK.wav", False) == "dropped"
    assert S.classify_train("GTR 1 Amp_M81.wav", False) == "electric_guitar"
    assert S.classify_train("12_ElecGtr1a_Amp1.wav", False) == "electric_guitar"
    assert S.classify_train("GTR KEYS AMP_M80.wav", False) == "rest"


def test_wiener_is_near_identity_for_an_oracle_stem_and_ensemble_weights():
    rng = np.random.default_rng(0)
    s, n = rng.standard_normal(48000), 0.01 * rng.standard_normal(48000)
    t = S.wiener(s + n, s, 1)
    assert np.sum((t - s) ** 2) < 0.01 * np.sum(s ** 2)
    e = S.ensemble(2 * s, 0.5 * s, s)
    assert np.allclose(e, s)


def test_exposed_share_counts_active_sections_only():
    sec = S.SECTION_S * S.SR
    tgt = np.concatenate([np.full(sec, 0.1), np.full(sec, 0.1), np.zeros(sec)])
    oth = np.concatenate([np.full(sec, 0.001), np.full(sec, 0.1), np.full(sec, 0.1)])
    share, n = S.exposed_share(tgt, oth)
    assert n == 2 and share == 0.5


def test_boot_holm_and_median_lobo():
    pairs = [("a", 1.0), ("a", 3.0), ("b", 1.0), ("c", -1.0)]
    b = S.boot(pairs)
    assert b["band_mean"] == pytest.approx(2 / 3) and b["band_median"] == pytest.approx(1.0)
    assert 0 < b["p_le_0"] < 1 and b["lo"] <= b["band_mean"] <= b["hi"]
    m = S.median_lobo(pairs)
    assert (m["lobo_min"], m["lobo_max"]) == (0.0, 1.5)
    assert S.holm({"T1": 0.01, "T2": 0.04, "T3": 0.2}) == {"T1": True, "T2": True, "T3": False}
    assert S.holm({"T1": 0.06, "T2": 0.04}) == {"T2": True, "T1": True}
    assert S.holm({"T1": 0.2, "T2": 0.01}) == {"T2": True, "T1": False}
