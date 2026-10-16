import pytest

from learn import build_bleed_damage as D

LOW = {"cambridge-Drag_Me_Down-ElecGtr4": "A", "telefunken-Farthest_Step-GTR": "B"}


def test_draw_trials_and_balance():
    t = D.draw(low_halves=LOW)
    assert len(t) == 6
    assert sum(x["kind"] == D.NULL for x in t) == 1
    real = [x for x in t if x["kind"] != D.NULL]
    assert sorted(x["letters"]["X"] for x in real).count("cleaned") in (2, 3)
    for x in real:
        assert sorted(x["letters"].values()) == ["cleaned", "original"]
    i = next(i for i, x in enumerate(t) if x["kind"] == D.NULL)
    assert i > 0
    for j in (i - 1, i + 1):
        if 0 <= j < len(t):
            assert t[j]["slug"] != D.NULL_PART[0]
    assert t == D.draw(low_halves=LOW)


def test_parse_answers():
    assert D.parse_answers("1X-little 2N 3y-a-lot 4? 5n-no") == {
        "1": ("X", "little"), "2": ("N", None), "3": ("Y", "lot"), "4": (None, None), "5": ("N", None)}
    with pytest.raises(SystemExit):
        D.parse_answers("1Z-lot")


def test_score_roles():
    key = {"trials": {
        "1": {"kind": "high", "slug": "s", "held": "B", "letters": {"X": "cleaned", "Y": "original"}},
        "2": {"kind": "high", "slug": "t", "held": "A", "letters": {"X": "original", "Y": "cleaned"}},
        "3": {"kind": D.NULL, "slug": "s", "held": "B", "letters": {"X": "original", "Y": "original"}},
        "4": {"kind": "low", "slug": "u", "held": "A", "letters": {"X": "original", "Y": "cleaned"}}}}
    rep = D.score_key(key, D.parse_answers("1X-little 2X-lot 3Y-little 4N"))
    assert rep["high"] == {"cleaned-little": 1, "original-lot": 1}
    assert rep[D.NULL] == {"a letter-little": 1}
    assert rep["low"] == {"neither": 1}
