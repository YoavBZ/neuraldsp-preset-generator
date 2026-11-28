"""The spectral-envelope steps' builder (`learn/envelope_build.py`): the declared transform on synthetic signals (the
STFT and its inverse, the unity proof, the swap proof, the gain, floor and clamp rules, the edge bins, the swap's
zero-magnitude rule), the realised error, the four proofs on a synthetic part, and `part_record` behind fakes: it
writes the five guitars and one record only under PF/fs/envelope/, a failing proof or a length mismatch stops before
anything is written. Made-up keys only; numpy behind `importorskip`."""
import json
import math

import pytest

np = pytest.importorskip("numpy")

from learn import envelope_build as EB          # noqa: E402
from learn import note_rebuild as NR            # noqa: E402
from learn import scratch_envelope as E         # noqa: E402
from learn import scratch_search as S           # noqa: E402
from learn import voice_build as VB             # noqa: E402

SR = NR.SR
N = SR // 2                                     # a half-second section: n samples, n + pad padded
L = N + VB.pad_samples()


def _noise(seed=1, length=L):
    rng = np.random.default_rng(seed)
    return rng.standard_normal(length) * 0.1


def _tone(f, length=L, a=0.2):
    return a * np.sin(2 * np.pi * f * np.arange(length) / SR)


# --- the transform -------------------------------------------------------------------------------------------------------

def test_the_window_is_periodic_hann():
    w = EB.window()
    assert len(w) == 2048 and w[0] == 0.0 and w[1024] == pytest.approx(1.0) and w[1] == pytest.approx(w[2047])


@pytest.mark.parametrize("length", [1, 239, 2048, 5001, L])
def test_the_stft_frames_and_the_inverse_return_the_signal(length):
    x = _noise(3, length)
    X = EB.stft(x)
    assert X.shape == (E.frame_count(length), E.BINS)
    y = EB.istft(X, length)
    assert EB.ratio(y, x) <= E.PROOF_TOL


def test_frame_i_is_centred_on_sample_240_i():
    x = np.zeros(4801)
    x[2400] = 1.0                                         # an impulse at frame 10's centre
    P = np.abs(EB.stft(x)) ** 2
    e = P.sum(axis=1)
    assert int(np.argmax(e)) == 10 and e[10] == pytest.approx(E.BINS)     # w[1024] = 1: a flat unit spectrum


def test_proof_3_unity_gains_return_the_source_on_every_eq_step():
    x = _noise(4)
    X = EB.stft(x)
    nb = len(E.band_table())
    for step, onsets in (("part", ()), ("group", (0.05, 0.21, 0.33)), ("win", ())):
        u = E.unit_ids(step, X.shape[0], onsets)
        y = EB.istft(EB.apply_gains(X, u, np.zeros((max(u) + 1, nb))), L)
        assert EB.ratio(y, x) <= E.PROOF_TOL


def test_proof_4_the_targets_own_magnitude_and_phase_return_the_target():
    t = _noise(5) * np.linspace(0, 1, L)
    T = EB.stft(t)
    assert EB.ratio(EB.istft(EB.swap(T, T), L), t) <= E.PROOF_TOL


def test_a_broken_swap_would_fail_proof_4():
    t = _noise(6)
    T = EB.stft(t)
    shifted = np.roll(T, 1, axis=0)                       # a mis-aligned phase donor
    assert EB.ratio(EB.istft(EB.swap(T, shifted), L), t) > 1e-3


def test_the_swap_keeps_the_other_signals_bin_where_the_phase_donor_is_silent():
    M = np.array([[3 + 4j, 1 - 1j, 2j]])
    P = np.array([[0j, 2 + 0j, -1j]])
    out = EB.swap(M, P)
    assert out[0, 0] == 3 + 4j                            # |P| = 0: M's own bin (its phase)
    assert out[0, 1] == pytest.approx(math.sqrt(2))        # |M| with P's phase (0)
    assert out[0, 2] == pytest.approx(-2j)


def test_the_gain_floor_and_clamp_rules():
    es = np.array([[1.0, 0.0, 1.0, 1e-5, 1.0], [1.0, 0.0, 1.0, 1.0, 2e-4]])
    et = np.array([[4.0, 1.0, 0.0, 1.0, 1e3], [1e-3, 0.0, 1.0, 1.0, 1.0]])
    g, fl, cl = EB.eq_gains(es, et)
    assert g[0, 0] == pytest.approx(10 * math.log10(4.0))  # sqrt(E_t / E_s) in amplitude dB
    assert fl[0, 1] and fl[1, 1] and g[0, 1] == 0.0 == g[1, 1]   # E_source = 0: 0 dB
    assert g[0, 2] == -20.0 and cl[0, 2]                  # E_target = 0, E_source > 0: -20 dB (clamped)
    assert fl[0, 3] and g[0, 3] == 0.0                    # under the band's largest cell less 40 dB: 0 dB
    assert not fl[1, 3]
    assert g[0, 4] == 20.0 and cl[0, 4]                   # +30 dB clamped to +20
    assert not fl[1, 4] and g[1, 4] == 20.0 and cl[1, 4]  # 2e-4 is over 1e-4 of the band's largest: +37 dB clamped
    assert g[1, 0] == -20.0 and cl[1, 0]                  # -30 dB clamped to -20
    assert np.all(np.abs(g) <= 20.0)


def test_the_floor_is_relative_to_the_bands_largest_cell_at_that_step():
    es = np.array([[1.0], [0.99e-4], [1.01e-4]])
    _g, fl, _c = EB.eq_gains(es, es)
    assert list(fl[:, 0]) == [False, True, False]


def test_edge_bins_keep_0_db():
    X = np.ones((3, E.BINS), complex)
    g = np.full((1, len(E.band_table())), 6.0)
    Y = EB.apply_gains(X, [0, 0, 0], g)
    edges = E.edge_bins()
    assert np.all(Y[:, edges] == 1.0)
    inside = [j for j in range(E.BINS) if j not in set(edges)]
    assert np.allclose(Y[:, inside], 10 ** (6 / 20))


def test_one_gain_per_band_and_unit():
    X = np.ones((4, E.BINS), complex)
    nb = len(E.band_table())
    g = np.zeros((2, nb))
    g[1, 5] = -6.0
    Y = EB.apply_gains(X, [0, 0, 1, 1], g)
    b = E.band_table()[5]
    cols = list(range(b["bin_lo"], b["bin_hi"] + 1))
    assert np.allclose(Y[2:, cols], 10 ** (-6 / 20)) and np.all(Y[:2, cols] == 1.0)
    assert np.all(np.delete(Y, cols, axis=1) == 1.0)


def test_unit_energy_sums_frames_and_band_bins():
    X = np.zeros((3, E.BINS), complex)
    X[0, 3], X[1, 4], X[2, 7], X[2, 0] = 1.0, 2.0, 3.0, 5.0     # bins 3-7 are band 0; bin 0 an edge bin
    e = EB.unit_energy(X, [0, 0, 1])
    assert e.shape == (2, 20) and e[0, 0] == 5.0 and e[1, 0] == 9.0 and e.sum() == 14.0


def test_a_flat_target_ratio_is_realised_on_vt_part():
    x = _noise(7)
    t = 2.0 * x
    Xs, Xt = EB.stft(x), EB.stft(t)
    u = E.unit_ids("part", Xs.shape[0])
    es, et = EB.unit_energy(Xs, u), EB.unit_energy(Xt, u)
    g, fl, _ = EB.eq_gains(es, et)
    assert np.allclose(g, 20 * math.log10(2.0))
    y = EB.istft(EB.apply_gains(Xs, u, g), L)
    err = EB.cell_error(EB.unit_energy(EB.stft(y), u), es, ~fl, g)
    assert err["cells"] == 20 and err["median_abs_db"] < 0.05


def test_the_cell_error_leaves_out_masked_and_silent_cells():
    got, ref = np.array([[2.0, 0.0, 1.0]]), np.array([[1.0, 1.0, 1.0]])
    r = EB.cell_error(got, ref, np.array([[True, True, False]]))
    assert r["cells"] == 1 and r["median_abs_db"] == pytest.approx(10 * math.log10(2))
    assert EB.cell_error(got, ref, np.zeros((1, 3), bool))["cells"] == 0


def test_spectral_convergence():
    M = np.ones((2, 3))
    assert EB.spectral_convergence(M, M) == 0.0 and EB.spectral_convergence(2 * M, M) == pytest.approx(1.0)
    assert EB.spectral_convergence(M, 0 * M) is None


# --- one part's guitars and the proofs -------------------------------------------------------------------------------------

def _finish(y):
    return 0.5 * np.asarray(y)


def test_build_guitars_on_a_synthetic_part():
    pytest.importorskip("pyloudnorm")
    x = _noise(8) + _tone(220)
    t = _noise(9) * 0.8 + _tone(220, a=0.15)
    b = EB.build_guitars(x, t, _finish, N, [0.05, 0.2, 0.31])
    assert sorted(b["guitars"]) == sorted(E.BUILT)
    assert all(g.dtype == np.float32 and len(g) == N for g in b["guitars"].values())
    assert b["unity_ratio"] <= E.PROOF_TOL and b["swap_ratio"] <= E.PROOF_TOL
    assert b["units"]["part"] == 1 and b["units"]["group"] == 4 and b["units"]["win"] == b["frames"] == E.frame_count(L)
    src, _ = VB.chain(x, _finish, N)
    assert VB.same_bytes(b["source_out"], src)
    x32 = np.asarray(src, np.float32)
    proofs = EB.proofs_of(b, S.npy_sha(x32), x32, S.npy_sha(b["target_out"]))
    assert all(proofs[p] is True for p in E.PROOFS)
    for g in E.BUILT:
        e = b["error"][g]
        assert set(e) >= {"intent", "target", "level_change_db", "units"}
        assert e["intent"]["cells"] > 0 and 0 <= e["intent"]["floored_share"] <= 1
        assert e["target"]["cells"] > 0
    assert "spectral_convergence" in b["error"]["vt-mag"] and "spectral_convergence" not in b["error"]["vt-win"]
    assert b["error"]["vt-part"]["units"] == 1
    assert b["error"]["vt-mag"]["intent"]["clamped_share"] == 0.0
    assert b["error"]["vt-part"]["intent"]["median_abs_db"] < 1.0


def test_level_align():
    assert EB.level_align(np.array([[4.0, 4.0]]), np.array([[1.0, 1.0]])) == 4.0
    assert EB.level_align(np.zeros((1, 2)), np.ones((1, 2))) == 1.0 == EB.level_align(np.ones((1, 2)), np.zeros((1, 2)))


def test_the_target_is_level_aligned_before_the_clamp():
    """A target 40 dB under the source with the same shape: no cell clamps, vt-part corrects nothing (the call)."""
    pytest.importorskip("pyloudnorm")
    x = _noise(14) + _tone(440)
    b = EB.build_guitars(x, 1e-2 * x, _finish, N, [0.1, 0.3])
    assert b["target_align_db"] == pytest.approx(40.0)
    for g in ("vt-part", "vt-group", "vt-win"):
        assert b["error"][g]["intent"]["clamped_share"] == 0.0
        assert abs(b["error"][g]["level_change_db"]) < 1e-6
    assert b["swap_ratio"] <= E.PROOF_TOL                    # proof 4 runs on the unscaled target


def test_the_swap_survives_subnormal_magnitudes():
    M = np.array([[1.0 + 0j, 2.0 + 0j]])
    P = np.array([[5e-324 + 5e-324j, -5e-324 + 0j]])
    out = EB.swap(M, P)
    assert np.all(np.isfinite(out)) and out[0, 0] == pytest.approx(np.exp(1j * np.pi / 4)) and out[0, 1] == pytest.approx(-2.0)


def test_the_proofs_fail_on_other_bytes():
    pytest.importorskip("pyloudnorm")
    x, t = _noise(10), _noise(11)
    b = EB.build_guitars(x, t, _finish, N, [])
    x32 = np.asarray(VB.chain(x, _finish, N)[0], np.float32)
    other = x32.copy()
    other[5] += 1e-3
    p = EB.proofs_of(b, S.npy_sha(other), other, S.npy_sha(b["target_out"]))
    assert p["source_is_tr_di"] is False and p["target_is_vc_own"] is True
    p = EB.proofs_of(b, S.npy_sha(x32), x32, None)
    assert p["target_is_vc_own"] is False
    p = EB.proofs_of(dict(b, unity_ratio=2e-9, swap_ratio=math.inf), S.npy_sha(x32), x32, S.npy_sha(b["target_out"]))
    assert p["unity_is_source"] is False and p["swap_is_target"] is False


def test_a_length_mismatch_stops():
    with pytest.raises(SystemExit, match="not n \\+ END_PAD_S"):
        EB.build_guitars(_noise(1, L - 1), _noise(2), _finish, N, [])
    with pytest.raises(SystemExit, match="not n \\+ END_PAD_S"):
        EB.build_guitars(_noise(1), _noise(2, L + 1), _finish, N, [])


# --- part_record behind fakes ----------------------------------------------------------------------------------------------

class _Part:
    def __init__(self, x):
        self.key, self.set, self.n = "bks/fake1", "bks", N
        self.notes = [{"on": 0.05, "off": 0.2}, {"on": 0.25, "off": 0.4}]
        self.T = {"tuning": 0.0, "mutes": [], "tilt": 0.0, "levels": [0.0, 0.0]}
        self.bank, self.ring, self.loud, self.finish = None, "ring-soft", None, _finish
        self.X = np.asarray(VB.chain(x, _finish, N)[0], np.float32)
        self.x_sha = S.npy_sha(self.X)


@pytest.fixture
def faked(monkeypatch, tmp_path):
    pytest.importorskip("pyloudnorm")
    from learn import scratch_readerr as RX
    from learn import scratch_rederive as RD

    x, raw = _noise(12) + _tone(330), _noise(13)
    gate = np.linspace(0.2, 1.0, L)
    monkeypatch.setattr(S, "fs_dir", lambda: tmp_path / "fs")
    monkeypatch.setattr(RX, "played_trace", lambda *a, **k: ([], {}))
    monkeypatch.setattr(RD, "_synth", lambda *a, **k: (x, {}))
    monkeypatch.setattr(NR, "denoise_above", lambda y, rate=SR: np.asarray(y))
    monkeypatch.setattr(VB, "own_gain", lambda notes, trace, length, rate=SR, end=None: gate)
    p = _Part(x)
    own = np.asarray(VB.chain(raw * gate, _finish, N)[0], np.float32)
    vb = {"guitars": {"vc-own": {"audio_sha256": S.npy_sha(own)}}}
    return p, raw, vb, tmp_path


def test_part_record_writes_five_guitars_and_one_record_under_envelope(faked):
    p, raw, vb, tmp = faked
    rec = EB.part_record(p, {"held": "A"}, raw, {"real": 4800, "zeros": 0, "first_n_equal": True}, vb, {"c": 1})
    assert tuple(rec) == EB.PART_FIELDS and all(rec["proofs"][q] is True for q in E.PROOFS)
    files = sorted(q.relative_to(tmp) for q in tmp.rglob("*") if q.is_file())
    assert all(q.parts[:2] == ("fs", "envelope") for q in files) and len(files) == 6
    for g in E.BUILT:
        y = np.load(E.dry_path(g, p.key))
        assert y.dtype == np.float32 and S.npy_sha(y) == rec["guitars"][g]["audio_sha256"]
    saved = json.loads(E.part_path(p.key).read_text())
    assert saved["tag"] == E.tag(p.key) and saved["groups"] == 2 and saved["units"]["group"] == 3
    assert saved["parents"] == {"tr-di": p.x_sha, "vc-own": vb["guitars"]["vc-own"]["audio_sha256"]}
    with pytest.raises(SystemExit, match="never overwritten"):
        EB.part_record(p, {"held": "A"}, raw, {"real": 4800, "zeros": 0, "first_n_equal": True}, vb, {"c": 1})


@pytest.mark.parametrize("broken", ["source", "target"])
def test_a_failing_proof_stops_before_anything_is_written(faked, broken):
    p, raw, vb, tmp = faked
    if broken == "source":
        p.x_sha = "0" * 64
    else:
        vb = {"guitars": {"vc-own": {"audio_sha256": "0" * 64}}}
    with pytest.raises(SystemExit, match="the shard stops before anything is written"):
        EB.part_record(p, {"held": "A"}, raw, {"real": 4800, "zeros": 0, "first_n_equal": True}, vb, {"c": 1})
    assert not any(q.is_file() for q in tmp.rglob("*"))


def test_a_padded_raw_of_the_wrong_length_stops(faked):
    p, raw, vb, tmp = faked
    with pytest.raises(SystemExit, match="not n \\+ END_PAD_S"):
        EB.part_record(p, {"held": "A"}, raw[:-1], {"real": 4800, "zeros": 0}, vb, {"c": 1})
    assert not any(q.is_file() for q in tmp.rglob("*"))


def test_combine_and_dry_bodies():
    rec = {"code": {"scratch_readerr_blob_sha": "b" * 40, "played_trace_sha256": "p" * 64},
           "proofs": {q: True for q in E.PROOFS}, "proof_ratios": {"unity": 1e-16, "swap": 2e-16},
           "error": {g: {"intent": {"median_abs_db": 0.4, "p90_abs_db": 1.1, "clamped_share": 0.0,
                                    "floored_share": 0.1}, "target": {"median_abs_db": 0.9, "p90_abs_db": 2.0}}
                     for g in E.BUILT}}
    per = {f"bks__fake{i}": dict(rec, **{f: None for f in EB.BUILD_PART_FIELDS if f not in rec}) for i in range(3)}
    keys = sorted(per)
    out = EB.combine_body(per, keys)
    assert out["proofs"]["unity_is_source"] == {"held": 3, "of": 3} and out["proofs_hold"] is False   # not the 47
    assert out["rules"]["bands"] == E.band_rows() and out["proof_ratio_max"]["swap"] == 2e-16
    d = EB.dry_body(out, "s" * 64)
    assert d["proofs"]["swap_is_target"] == "3 of 3" and d["sha256"] == "s" * 64
    assert d["realised_error_medians_47"]["vt-win"]["intent_median_abs_db"] == 0.4
    assert all(k not in json.dumps(d) for k in keys)
    bad = dict(per)
    bad["bks__fake0"] = dict(rec, code={"other": 1})
    with pytest.raises(SystemExit, match="different scratch_readerr"):
        EB.combine_body(bad, keys)
    with pytest.raises(SystemExit, match="not the draw's parts"):
        EB.combine_body(per, keys + ["goat__fake9"])
