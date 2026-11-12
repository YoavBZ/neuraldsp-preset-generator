"""LS by ear (`learn/ls_ear.py`): the draw and letters, the unblinding, the sign test, the read, the peak gain and the
page's leaks."""

import math

from learn import ls_ear as E


def _keys(n=29):
    return [f"c4|cap/u{i}#sw50r|sw50r" for i in range(n)]


def test_the_draw_is_seeded_with_one_s_and_one_matched_per_item():
    a = E.draw(_keys())
    assert len(a) == E.N_ITEMS and a == E.draw(_keys())
    assert all(sorted(it["letters"].values()) == ["S", "matched"] for it in a)


def test_unblinding_turns_b_against_a_into_matched_against_s():
    it = {"letters": {"A": "S", "B": "matched"}}
    jt = {"letters": {"A": "matched", "B": "S"}}
    assert E.unblind(it, {"choice": "louder"}) == 1 and E.unblind(jt, {"choice": "louder"}) == -1
    assert E.unblind(it, {"choice": "same"}) == 0 and E.unblind(it, {}) is None


def test_the_sign_test_and_the_rule():
    assert math.isclose(E.sign_test(6, 0), 2 / 64) and E.sign_test(3, 3) == 1.0 and E.sign_test(0, 0) == 1.0
    items = [{"id": f"i{j}", "letters": {"A": "S", "B": "matched"}} for j in range(12)]
    loud = E.ear_read(items, {f"i{j}": {"choice": "louder"} for j in range(8)})
    assert loud["matched louder"] == 8 and loud["shown_bias"] == "louder" and loud["outcome"] == "user"
    same = E.ear_read(items, {f"i{j}": {"choice": "same" if j % 3 else "louder"} for j in range(12)})
    assert same["outcome"] == "stands" and same["about the same"] == 8


def test_the_peak_gain_keeps_the_relative_level_and_never_raises():
    import pytest

    np = pytest.importorskip("numpy")
    g = E.peak_gain({"A": np.array([0.5, -2.0]), "B": np.array([0.1])})
    assert math.isclose(2.0 * g, 10 ** (-1 / 20))
    assert E.peak_gain({"A": np.array([0.1])}) == 1.0


def test_the_page_names_no_amp_or_unit():
    items = E.draw(_keys())
    body = E.page_html(items, {}, "b0")
    assert E.leaks(body, items) == [] and E.leaks("plays sw50r", items) == ["sw50r"]
    assert 'data-c="louder"' in body and 'data-k="B"' in body
