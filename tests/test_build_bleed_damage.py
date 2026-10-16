import base64

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
    assert D.parse_answers("1X-little-tone 2N 3y-a-lot-bg 4? 5n-no 6X-? 7Y-?-? 8X-lot") == {
        "1": ("X", "little", "tone"), "2": ("N", None, None), "3": ("Y", "lot", "bg"),
        "4": (None, None, None), "5": ("N", None, None), "6": ("X", None, None),
        "7": ("Y", None, None), "8": ("X", "lot", None)}
    with pytest.raises(SystemExit):
        D.parse_answers("1Z-lot")


def test_score_roles_and_damage():
    key = {"trials": {
        "1": {"kind": "high", "slug": "s", "held": "B", "letters": {"X": "cleaned", "Y": "original"}},
        "2": {"kind": "high", "slug": "t", "held": "A", "letters": {"X": "original", "Y": "cleaned"}},
        "3": {"kind": D.NULL, "slug": "s", "held": "B", "letters": {"X": "original", "Y": "original"}},
        "4": {"kind": "low", "slug": "u", "held": "A", "letters": {"X": "original", "Y": "cleaned"}},
        "5": {"kind": "high", "slug": "v", "held": "A", "letters": {"X": "original", "Y": "cleaned"}}}}
    rep = D.score_key(key, D.parse_answers("1X-little-tone 2X-lot-bg 3Y-little-unsure 4N 5Y-lot-bg"))
    assert rep["high"] == {"cleaned-little-tone": 1, "original-lot-bg": 1, "cleaned-lot-bg": 1}
    assert rep[D.NULL] == {"a letter-little-unsure": 1}
    assert rep["low"] == {"neither": 1}
    assert [r["damage"] for r in rep["trials"]] == [True, False, False, False, False]


def test_pad_makes_bytes_differ_and_stays_valid():
    raw = b"\x00\x00\x00\x10ftypM4A \x00\x00\x00\x00"
    src = "data:audio/mp4;base64," + base64.b64encode(raw).decode()
    a, b = D.pad(src), D.pad(src)
    assert a != b
    blob = base64.b64decode(a.split(",", 1)[1])
    assert blob.startswith(raw)
    n = int.from_bytes(blob[len(raw):len(raw) + 4], "big")
    assert blob[len(raw) + 4:len(raw) + 8] == b"free" and len(blob) == len(raw) + n
