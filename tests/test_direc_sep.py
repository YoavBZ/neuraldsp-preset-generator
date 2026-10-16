"""Separator-robust C′ (`docs/cprime-sep-plan.md`): the residual library, its fold split, the
augmentation and the `fit` options. C′'s own defaults stay bit-identical; that is checked by
`tests/test_direc_fine.py` (run it with this file). Torch runs on the CPU."""

import json

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from learn import direc as D  # noqa: E402
from learn import direc_sep as S  # noqa: E402
from tests import direc_tiny as T  # noqa: E402


def _entry(n, band, part, fold, rsr_db=0.0, seed=0, gdb=None):
    rng = np.random.default_rng(seed)
    r = rng.standard_normal(n).astype(np.float32) * 0.1
    freqs = np.fft.rfftfreq(S.NFFT, 1 / S.SR)
    return {"id": f"{part}|m|i", "part": part, "band": band, "fold": fold, "r": r, "freqs": freqs,
            "gdb": np.zeros(len(freqs), np.float32) if gdb is None else gdb, "rsr_db": rsr_db,
            "rsr": 10 ** (rsr_db / 20), "r_rms": float(np.sqrt((r.astype(np.float64) ** 2).mean()))}


def test_sep_apply_flat_and_level():
    n = 48000
    x = np.sin(np.arange(n) * 0.05).astype(np.float32)
    cf = np.fft.rfftfreq(n, 1 / S.SR)
    e = _entry(n, "A", "a", 0, rsr_db=-6.0)
    e0 = dict(e, r=np.zeros(n, np.float32), r_rms=1.0)
    np.testing.assert_allclose(D.sep_apply(x, e0, 0, 0.0, cf), x, atol=1e-5)
    y = D.sep_apply(x, e, 0, 0.0, cf)
    added = y - x
    assert 20 * np.log10(added.std() / x.std()) == pytest.approx(-6.0, abs=0.05)
    y3 = D.sep_apply(x, e, 0, 3.0, cf)
    assert 20 * np.log10((y3 - x).std() / added.std()) == pytest.approx(3.0, abs=0.01)


def test_sep_apply_colouration():
    n = 48000
    rng = np.random.default_rng(1)
    x = rng.standard_normal(n).astype(np.float32)
    cf = np.fft.rfftfreq(n, 1 / S.SR)
    freqs = np.fft.rfftfreq(S.NFFT, 1 / S.SR)
    e = _entry(n, "A", "a", 0, gdb=np.where(freqs > 4000, -20.0, 0.0).astype(np.float32))
    e = dict(e, r=np.zeros(n, np.float32), r_rms=1.0)
    y = D.sep_apply(x, e, 0, 0.0, cf)
    X, Y = np.abs(np.fft.rfft(x)), np.abs(np.fft.rfft(y))
    hi, lo = cf > 6000, (cf > 200) & (cf < 3000)
    assert 20 * np.log10(Y[hi].mean() / X[hi].mean()) == pytest.approx(-20, abs=0.5)
    assert 20 * np.log10(Y[lo].mean() / X[lo].mean()) == pytest.approx(0, abs=0.2)


def test_separator_channel_recovers_gain_and_residual():
    n = 4 * S.SR
    rng = np.random.default_rng(2)
    ref = rng.standard_normal(n)
    noise = 0.1 * rng.standard_normal(n)
    G, h, r, den = S.separator_channel(ref, 0.5 * ref + noise)
    freqs = np.fft.rfftfreq(S.NFFT, 1 / S.SR)
    band = (freqs > 100) & (freqs < 10000)
    assert np.median(np.abs(G[band])) == pytest.approx(0.5, abs=0.02)
    mid = slice(S.NFFT, n - S.NFFT)
    assert np.corrcoef(r[mid], noise[mid])[0, 1] > 0.97
    g = S.smoothed_gain_db(G, den, freqs)
    assert np.abs(g[band]).max() < 0.5                    # flat after the mean is removed


def test_split_bands_is_seeded_disjoint_and_large_enough():
    bands = {"A": {"a1", "a2"}, "B": {"b1"}, "C": {"c1", "c2", "c3"}, "D": {"d1"}, "E": {"e1"}}
    for fold in range(4):
        tr, va = S.split_bands(bands, fold)
        assert not set(tr) & set(va) and set(tr) | set(va) == set(bands)
        assert sum(len(bands[b]) for b in va) >= S.VAL_MIN_PARTS
        assert (tr, va) == S.split_bands(bands, fold)


def test_load_lib_never_uses_the_left_out_fold(tmp_path):
    n = 1000
    rows, rs, gs = [], [], []
    for k, (band, fold) in enumerate([("A", 0), ("B", 1), ("C", 2), ("D", 3), ("E", 1), ("F", 2)]):
        for j in range(2):
            e = _entry(n, band, f"{band}{j}", fold, seed=k)
            rows.append({x: e[x] for x in ("id", "part", "band", "fold", "rsr_db", "r_rms")})
            rs.append(e["r"])
            gs.append(e["gdb"])
    np.savez(tmp_path / "lib.npz", r=np.stack(rs), gdb=np.stack(gs), freqs=np.fft.rfftfreq(S.NFFT, 1 / S.SR))
    (tmp_path / "lib.json").write_text(json.dumps({"rows": rows}))
    for fold in range(4):
        tr, va = S.load_lib(tmp_path / "lib.npz", fold)
        assert all(e["fold"] != fold for e in tr + va)
        assert not {e["band"] for e in tr} & {e["band"] for e in va}
        assert len({e["part"] for e in va}) >= S.VAL_MIN_PARTS


def _tiny_sep(p):
    tr = [_entry(T.CLIP * 2, b, f"{b}x", 1, rsr_db=-3.0, seed=i) for i, b in enumerate(("Band B", "Band C"))]
    va = [_entry(T.CLIP * 2, "Band D", "Dx", 3, rsr_db=-3.0, seed=9)]
    return {"train": tr, "val": va, "p": p, "jitter_db": 3.0}


def test_fit_with_sep_runs_and_saves_best(tmp_path, monkeypatch):
    h, lines = T.tiny_fit(tmp_path, monkeypatch, out_name="s", steps=6, log_every=2, warmup=1,
                          sep=_tiny_sep(0.75))
    out = tmp_path / "s"
    assert (out / "fold0-best.pt").exists() and (out / "fold0-last.pt").exists()
    cfg = json.loads((out / "config.json").read_text())
    assert cfg["sep"]["p"] == 0.75 and cfg["sep"]["val"] == ["Dx|m|i"]
    best = torch.load(out / "fold0-best.pt")
    final = torch.load(out / "fold0.pt")
    assert all(torch.equal(best[k], final[k]) for k in best)
    # deterministic for a seed
    h2, _ = T.tiny_fit(tmp_path, monkeypatch, out_name="s2", steps=6, log_every=2, warmup=1, sep=_tiny_sep(0.75))
    assert h == h2


def test_sep_changes_training_but_control_runs(tmp_path, monkeypatch):
    base, _ = T.tiny_fit(tmp_path, monkeypatch, out_name="b", steps=3)
    sep, _ = T.tiny_fit(tmp_path, monkeypatch, out_name="p1", steps=3, sep=_tiny_sep(1.0))
    ctl, _ = T.tiny_fit(tmp_path, monkeypatch, out_name="p0", steps=3, sep=_tiny_sep(0.0))
    assert sep != base and ctl is not None


def test_patience_stops_early(tmp_path, monkeypatch, capsys):
    import contextlib
    import io

    monkeypatch.setattr(D, "CLIP", T.CLIP)
    monkeypatch.setattr(D, "CROP", T.CROP)
    monkeypatch.setattr(D, "CROPS", tmp_path / "no-crops")
    from learn import train as TR

    monkeypatch.setattr(TR, "k3_folds", lambda: ({b: i for i, b in enumerate(T.BANDS)}, {}))
    monkeypatch.setenv("DIREC_DEVICE", "cpu")
    T.make_cache(tmp_path / "cache")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        D.fit(tmp_path / "cache", 0, tmp_path / "pat", 1, 0, batch=2, log_every=1, steps=40, lr=0.0,
              lr_end=None, sep=_tiny_sep(0.5), patience=2, min_steps=2)
    text = buf.getvalue()
    assert "stopped at step 2: no 0.2% gain since step 0" in text    # lr 0: never beats step 0


def test_sep_validation_uses_held_out_bands_only(tmp_path, monkeypatch):
    """Review change 1: the separator validation scores rows of the library's validation bands
    (here Band D), which leave training; fold 0's own rows (Band A) are never selected on."""
    import contextlib
    import io

    from learn import train as TR

    monkeypatch.setattr(D, "CLIP", T.CLIP)
    monkeypatch.setattr(D, "CROP", T.CROP)
    monkeypatch.setattr(D, "CROPS", tmp_path / "no-crops")
    monkeypatch.setattr(TR, "k3_folds", lambda: ({b: i for i, b in enumerate(T.BANDS)}, {}))
    monkeypatch.setenv("DIREC_DEVICE", "cpu")
    T.make_cache(tmp_path / "cache")
    seen = []
    real = D.sep_apply

    def spy(x, e, off, jit, cf):
        seen.append(e["band"])
        return real(x, e, off, jit, cf)

    monkeypatch.setattr(D, "sep_apply", spy)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        D.fit(tmp_path / "cache", 0, tmp_path / "v", 1, 0, batch=2, log_every=2, steps=2, lr=1e-4,
              lr_end=None, sep=_tiny_sep(0.0))
    text = buf.getvalue()
    # 16 rows, 4 per band: fold 0 (Band A) is validation; Band D (4 rows) leaves training
    assert "separator validation on 4 crops of ['Band D'] (4 rows, out of training); train now 8" in text
    assert "step 0 sepval" in text
    assert seen and set(seen) == {"Band D"}              # p = 0: only validation applies residuals


def test_lsd_db():
    rng = np.random.default_rng(3)
    x = rng.standard_normal(4 * S.SR)
    assert S.lsd_db(2.0 * x, x) == pytest.approx(0.0, abs=0.3)   # a level offset is removed
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / S.SR)
    y = np.fft.irfft(X * np.where(f > 1000, 0.25, 1.0), len(x))  # −12 dB above 1 kHz
    assert S.lsd_db(y, x) > 4.0


def test_report_contrasts(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "OUT", tmp_path)
    monkeypatch.setattr(S, "_bleed_high", lambda: {"p3"})
    base, sep = {}, {}
    for k, band in enumerate(("A", "A", "B", "C")):
        row = {"band": band, "fold": k % 2, "device": "mps", "stem": [0.2, 0.2, 0.02], "ref": [0.5, 0.5, 0.03],
               "lsd": {"stem": 6.0, "ref": 3.0}}
        base[f"p{k}"] = row
        sep[f"p{k}"] = dict(row, stem=[0.3, 0.3, 0.02], ref=[0.5, 0.5, 0.03], lsd={"stem": 5.0, "ref": 3.0})
    (tmp_path / "eval-cprime.json").write_text(json.dumps(base))
    (tmp_path / "eval-sep.json").write_text(json.dumps(sep))
    out = S.report()
    assert out["sep"]["stem_1_3k"]["band_weighted_mean"] == pytest.approx(0.1)
    assert out["sep"]["stem_lsd"]["band_weighted_mean"] == pytest.approx(-1.0)
    assert out["sep"]["stem_minus_ref_1_3k"]["band_weighted_mean"] == pytest.approx(0.1)
    assert out["sep"]["share_of_ref_gap_1_3k"] == pytest.approx(0.1 / 0.3, abs=1e-3)
    assert out["sep"]["share_of_ref_gap_lsd"] == pytest.approx(1 / 3, abs=1e-3)
    assert out["sep"]["stem_1_3k_no_high_bleed"]["parts"] == 3
    assert out["sep"]["stem_bs_1_3k"]["parts"] == 0
