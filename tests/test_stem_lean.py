"""N8's pure parts (`learn/stem_lean.py`)."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import stem_lean as L  # noqa: E402


def _o(level, gain, dt=False, di="d"):
    return {"render_lufs": level, "gain_db": gain, "dt": dt, "di": di, "amp": "ac20", "settings": {"a/b": "1"}}


def test_the_dominant_other_is_the_loudest_and_never_a_double():
    a, b = _o(-20, -2), _o(-18, -8)
    assert L.dominant([a, b]) is a
    assert L.dominant([a, _o(-10, 0, dt=True)]) is None
    assert L.dominant([]) is None


def test_other_rows_carry_the_others_label_and_keep_the_section():
    rows = [{"i": 1, "amp": "pr12", "base": "clean", "section": "s", "label": {"amp": "pr12"}},
            {"i": 2, "amp": "pr12", "base": "clean", "section": "t", "label": {}}]
    render = {1: {"others": [_o(-20, 0, di="x")]}, 2: {"others": [_o(-20, 0, dt=True, di="y")]}}
    plan = {1: [{"di": "x", "draw": {"base": "crunch"}}], 2: [{"di": "y", "draw": "target"}]}
    pairs = L.other_rows(rows, render, plan)
    assert len(pairs) == 1
    t, o = pairs[0]
    assert t is rows[0] and (o["amp"], o["base"], o["section"]) == ("ac20", "crunch", "s")
    assert o["label"]["amp"] == "ac20" and o["label"]["settings"] == {"a/b": "1"}


def test_hits_read_the_top_answer():
    p = [[0.1, 0.7, 0.2], [0.5, 0.2, 0.3]]
    assert L.hits(p, ["b", "b"], ["a", "b", "c"]).tolist() == [1.0, 0.0]


def test_demeaning_and_the_two_correlations():
    assert L.demean([1.0, 3.0, 5.0, 9.0], ["x", "x", "y", "y"]).tolist() == [-1.0, 1.0, -2.0, 2.0]
    a = np.array([1.0, -1.0, 2.0, -2.0])
    assert L.group_rows(a, a, -a) == pytest.approx((1.0, -1.0))


def test_an_answer_that_only_knows_its_cell_reads_nothing():
    rng = np.random.default_rng(1)
    n = 3000
    cell = rng.integers(0, 6, n)
    sec = rng.integers(0, 12, n)
    level = rng.normal(0, 1, 6)
    answer = level[cell]                                     # no audio: the constant of T's own cell
    y_t = level[cell] + rng.normal(0, 1, n)
    y_o = rng.normal(0, 1, n)
    tc, sc = [str(c) for c in cell], [str(s) for s in sec]
    biased = L.group_rows(*(L.demean(v, sc) for v in (answer, y_t, y_o)))
    fair = L.group_rows(*(L.clean_of_cells(v, tc, sc) for v in (answer, y_t, y_o)))
    assert biased[0] - biased[1] > 0.4
    assert abs(fair[0] - fair[1]) < 0.1 or np.isnan(fair[0])


def test_the_jackknife_widens_with_the_sections_spread():
    s = np.repeat(np.arange(6), 3)
    r = L.jackknife(lambda k: 0.25, s, lambda df: 2.0)
    assert r["point"] == 0.25 and r["lo"] == r["hi"] == 0.25 and r["sections"] == 6
    v = np.repeat(np.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0]), 3)
    w = L.jackknife(lambda k: float(v[k].mean()), s, lambda df: 2.0)
    assert w["point"] == 0.5 and w["lo"] < 0.2 and w["hi"] > 0.8


def test_the_reading():
    up = {"lo": 0.01, "hi": 0.2}
    span = {"lo": -0.1, "hi": 0.1}
    down = {"lo": -0.2, "hi": -0.01}
    none = {"lo": None, "hi": None}
    assert L.reading(up, span, span, True) == "the lead holds"
    assert L.reading(up, span, up, True) == "already in the mix"
    assert L.reading(up, span, span, False) == "void"
    assert L.reading(span, up, span, True) == "not shown"
    assert L.reading(down, up, span, True) == "the lead does not hold"
    assert L.reading(down, span, span, True) == "not shown"
    assert L.reading(none, up, none, True) == "not shown"
