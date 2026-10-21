import pytest

np = pytest.importorskip("numpy")

from learn import xlance_screen as X  # noqa: E402


def test_single_chunk_is_exact():
    a = np.random.default_rng(0).standard_normal((2, X.CHUNK44))
    out = X.run_chunked(lambda c: 2 * c, a)
    assert np.allclose(out, 2 * a)


def test_crossfade_sums_to_one_and_identity_holds():
    n = 1_323_000                                     # a 30-s context at 44.1 kHz
    starts = X.chunk_starts(n)
    assert starts[0] == 0 and starts[-1] + X.CHUNK44 >= n
    cover = np.zeros(starts[-1] + X.CHUNK44)
    for s, w in zip(starts, X.crossfade_windows(starts)):
        cover[s:s + X.CHUNK44] += w
    assert np.allclose(cover[:n], 1.0)
    a = np.random.default_rng(1).standard_normal((2, n))
    assert np.allclose(X.run_chunked(lambda c: c, a), a)


def test_short_input_pads():
    a = np.ones((2, 1000))
    out = X.run_chunked(lambda c: c * 3, a)
    assert out.shape == (2, 1000) and np.allclose(out, 3)


def test_repro_db():
    s = np.random.default_rng(2).standard_normal(48000)
    assert X.repro_db(s, s) > 200
    assert abs(X.repro_db(s, s + 0.1 * s) - 20.0) < 1e-6


def test_band_centres_match_third_octave():
    from learn import stereo_mix_check as SMC

    x = np.random.default_rng(3).standard_normal(480_000)
    assert len(X.band_centres()) == len(SMC.third_octave_db(x, lo=X.MEL_LO, hi=X.MEL_HI))


def test_mel_lsd_gain_invariant_and_detects_darkening():
    from scipy.signal import butter, sosfilt

    x = np.random.default_rng(4).standard_normal(480_000)
    assert X.mel_lsd_db(3 * x, x) < 1e-6
    dark = sosfilt(butter(2, 4000, "low", fs=48000, output="sos"), x)
    assert X.mel_lsd_db(dark, x) > 1.0
    e = X.spectral_error(dark, x)
    assert abs(e.mean()) < 1e-9 and e[-1] < e[0]


def test_decide():
    snr_ok = {"mean": 0.1, "hi90": 0.4}
    lsd_ok = {"hi90": -0.2}
    assert X.decide(snr_ok, lsd_ok, 1.2) == "SWITCH TO X-LANCE"
    assert X.decide(snr_ok, lsd_ok, 1.6) == "PASS, OVER BUDGET"
    assert X.decide({"mean": -0.01, "hi90": 0.3}, lsd_ok, 1.0) == "KEEP MEGA-53"
    assert X.decide(snr_ok, {"hi90": 0.01}, 1.0) == "KEEP MEGA-53"
    assert X.decide({"mean": 0.0, "hi90": 0.2}, {"hi90": -0.01}, 1.5) == "SWITCH TO X-LANCE"


def test_spread_consistent_vs_inconsistent():
    c = X.band_centres()
    base = np.where(np.asarray(c) > 3000, -6.0, 0.0)
    consistent = [base + 0.01 * k for k in range(5)]
    rng = np.random.default_rng(5)
    inconsistent = [base * rng.uniform(0, 2) for _ in range(5)]
    a, b = X.spread(consistent, c), X.spread(inconsistent, c)
    assert a["hf_mean_db_sd"] < b["hf_mean_db_sd"]
    assert a["hf_mean_db_median"] < 0


def test_lobo():
    pairs = [("a", 1, 1.0), ("b", 2, 2.0), ("c", 3, 3.0)]
    assert X.lobo_min(pairs) == {"min": 1.5, "max": 2.5}
    assert X.lobo_min(pairs[:2]) is None


def test_failures_both_ways():
    m = lambda s, l: {"snr_db": s, "mel_lsd_db": l}                     # noqa: E731
    per = {"a": {"M_f": m(5, 8), "X": m(0.4, 15)},                       # X fails both ways
           "b": {"M_f": m(1, 9), "X": m(4.5, 3)},                        # M_f fails both ways
           "c": {"M_f": m(2, 8), "X": m(1, 10)}}                         # within the margins
    f = X.failures(per, "X")
    assert f["row_snr_worse"] == ["a"] and f["row_lsd_worse"] == ["a"]
    assert f["base_snr_worse"] == ["b"] and f["base_lsd_worse"] == ["b"]
    assert f["n_row_snr_worse"] == 1


def test_decide_a1():
    assert X.decide_a1(True, True, True, False, -0.5).startswith("X_g PASSES")
    assert "PENDING MPS TIMING" in X.decide_a1(True, True, True, False, None)
    assert X.decide_a1(True, True, True, True, 0.2).startswith("X PASSES")      # X clearly better on tone
    assert X.decide_a1(True, True, True, True, -0.1).startswith("X_g PASSES")
    assert X.decide_a1(True, False, True, False, None) == "X_g: PASS, OVER BUDGET; KEEP MEGA-53"
    assert X.decide_a1(False, True, True, False, None) == "KEEP MEGA-53"


def test_quality_ok():
    assert X.quality_ok({"mean": 0.0, "hi90": 0.3}, {"hi90": -0.1})
    assert not X.quality_ok({"mean": -0.1, "hi90": 0.3}, {"hi90": -0.1})
    assert not X.quality_ok({"mean": 0.2, "hi90": 0.5}, {"hi90": 0.0})
