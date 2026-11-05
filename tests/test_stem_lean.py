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
    assert L.group_rows(a, a, -a, None) == pytest.approx((1.0, -1.0))


def test_the_jackknife_is_zero_for_a_constant_and_keeps_its_point():
    s = np.repeat(np.arange(6), 3)
    r = L.jackknife(lambda k: 0.25, s, lambda df: 2.0)
    assert r["point"] == 0.25 and r["lo"] == r["hi"] == 0.25 and r["sections"] == 6


def test_the_reading():
    up = {"lo": 0.01, "hi": 0.2}
    span = {"lo": -0.1, "hi": 0.1}
    down = {"lo": -0.2, "hi": -0.01}
    assert L.reading(up, span) == "the lead holds"
    assert L.reading(span, up) == "not shown"
    assert L.reading(down, up) == "the lead does not hold"
    assert L.reading(down, span) == "not shown"
    assert L.reading({"lo": None, "hi": None}, up) == "not shown"
