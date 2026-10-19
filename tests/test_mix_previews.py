"""learn/mix_previews.py: the pure parts (docs/mix-previews-results.md)."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import mix_previews as M  # noqa: E402


def test_ncc_lag_finds_envelope_position():
    rng = np.random.default_rng(0)
    ref = rng.standard_normal(2000)
    k, r = M.ncc_lag(ref[700:900] * 3 + 1, ref)
    assert k == 700 and r > 0.999


def test_gcc_phat_integer_lag():
    rng = np.random.default_rng(1)
    b = rng.standard_normal(5000)
    a = b[123:123 + 3000]
    assert M.gcc_phat(a, b, 300) == 123


def _b(p0, off, r=0.9):
    return {"p0": p0, "p1": p0 + 4 * M.SR, "offset": off, "r": r, "judged": True}


def test_clusters_need_support_and_spans_split_on_edit():
    S = M.SR
    blocks = [_b(0, 100), _b(2 * S, 102), _b(4 * S, 9_000_000), _b(6 * S, 101),
              _b(8 * S, 5000), _b(10 * S, 5001), _b(12 * S, 5002)]
    M.clusters(blocks)
    assert [b["matched"] for b in blocks] == [True, True, False, True, True, True, True]
    sp = M.spans(blocks)
    assert len(sp) == 2 and sp[0]["preview_end_s"] == 10.0 and sp[0]["n_blocks"] == 3
    assert sp[0]["judged_blocks"] == 4 and abs(sp[1]["offset_samples"] - 5000) <= 1
    assert M.same_take(sp[:1], 16, 16) == "partial"          # main span covers 10 of 16 s
    assert M.same_take(M.spans(M.clusters(blocks[:4])), 10, 10) == "yes"
    assert M.same_take([], 6, 6) == "no"


def test_covered_maps_session_window():
    sp = M.spans(M.clusters([_b(0, M.SR), _b(1 * M.SR, M.SR), _b(2 * M.SR, M.SR)]), only=M.SR)   # preview 0–6 s = session 1–7 s
    frac, whole = M.covered(2 * M.SR, 4 * M.SR, sp)
    assert frac == 1.0 and whole is not None
    frac, whole = M.covered(6 * M.SR, 8 * M.SR, sp)
    assert frac == 0.5 and whole is None


def test_crop_check_finds_true_offset():
    rng = np.random.default_rng(2)
    mix = rng.standard_normal(20 * M.SR)
    y = mix[M.SR:] * 0.5 + 0.1 * rng.standard_normal(19 * M.SR)       # preview starts 1 s in
    chk = M.crop_check(mix, y, 5 * M.SR, 9 * M.SR, M.SR, search=M.SR)
    assert chk["deviation_samples"] == 0 and chk["peak_sd"] > 50 and chk["r_at_offset"] > 0.9
    assert M.crop_check(mix, y, 0, 4 * M.SR, M.SR) is None


def test_same_take_rival_offset():
    sp = M.spans(M.clusters([_b(0, 10), _b(2 * M.SR, 10), _b(4 * M.SR, 10)]))
    assert M.same_take(sp, 8, 8, 0.3, 0.1, 0.1) == "yes"
    assert M.same_take(sp, 8, 8, 0.3, 0.4, 0.1) == "partial"


def test_best_lag_and_shift_undo_a_flipped_delay():
    rng = np.random.default_rng(3)
    ref = rng.standard_normal(20000)
    x = -M.shift(ref, -37)                      # x leads ref by 37 samples, polarity flipped
    lag, c = M.best_lag(x, ref, 100)
    assert lag == 37 and c < -0.99
    assert np.allclose(-M.shift(x, lag)[100:-100], ref[100:-100])
