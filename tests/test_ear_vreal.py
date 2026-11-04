import pytest

from learn import ear_vreal as E


def _rows():
    s = {"pr12": {"A": 3.0, "B": 2.0}, "sw50r": {"A": 2.0, "B": 3.0}, "ac20": {"A": 2.5, "B": 2.5}}
    return [{"slug": "p1", "key": "p1", "band": "x", "cls": "clean", "act": {"A": 0.9, "B": 0.5}, "s": s},
            {"slug": "p2", "key": "p2+3", "band": "y", "cls": "crunch", "act": {"A": 0.5, "B": 0.6}, "s": s},
            {"slug": "p3", "key": "p2+3", "band": "y", "cls": "crunch", "act": {"A": 0.8, "B": 0.2}, "s": s}]


def test_choose_uses_activity_and_s_on_the_search_half():
    units = {u["key"]: u for u in E.choose(_rows())}
    assert set(units) == {"p1", "p2+3"}
    assert (units["p1"]["held"], units["p1"]["search"], units["p1"]["amp"]) == ("A", "B", "pr12")
    assert units["p2+3"]["slug"] == "p3"                       # the more active held half of the two members


def test_draw_repeats_apart_and_hides_order():
    units = [{"slug": f"p{i}", "band": "b", "cls": "clean"} for i in range(10)]
    items = E.draw(units, 7)
    assert len(items) == 12 and sum(it["repeat_of"] is not None for it in items) == 2
    assert all(a["slug"] != b["slug"] for a, b in zip(items, items[1:]))
    assert all(sorted(it["letters"].values()) == sorted(E.CANDS) for it in items)
    assert len({tuple(it["letters"].values()) for it in items}) == 12
    assert E.draw(units, 7) == items


def test_unblind_needs_every_answer():
    it = {"letters": {"A": "W", "B": "S", "C": "FT", "D": "D_fix"}}
    rank = {"A": 1, "B": 2, "C": 3, "D": 4}
    close = {"A": "very", "B": "close", "C": "some", "D": "far"}
    got = E.unblind(it, {"rank": rank, "close": close})
    assert got["W"] == {"rank": 1, "close": 3} and got["D_fix"] == {"rank": 4, "close": 0}
    assert E.unblind(it, {"rank": {**rank, "D": 3}, "close": close}) is None
    assert E.unblind(it, {"rank": rank, "close": {**close, "D": None}}) is None


def test_report_weights_bands_and_keeps_repeats_out():
    judge = {"S": 3.0, "FT": 2.0, "D_fix": 4.0, "W": 5.0}
    good = {"S": {"rank": 2, "close": 1}, "FT": {"rank": 1, "close": 3}, "D_fix": {"rank": 3, "close": 1},
            "W": {"rank": 4, "close": 0}}
    bad = {"S": {"rank": 1, "close": 3}, "FT": {"rank": 4, "close": 0}, "D_fix": {"rank": 2, "close": 2},
           "W": {"rank": 3, "close": 1}}
    items = [{"id": "i1", "band": "x", "slug": "a", "repeat_of": None, "judge": judge},
             {"id": "i2", "band": "x", "slug": "b", "repeat_of": None, "judge": judge},
             {"id": "i3", "band": "y", "slug": "c", "repeat_of": None, "judge": judge},
             {"id": "i4", "band": "y", "slug": "c", "repeat_of": "i3", "judge": judge}]
    rep = E.report(items, {"i1": good, "i2": good, "i3": bad, "i4": bad})
    assert rep["parts"] == 3
    assert rep["against_S"]["FT"]["rank"]["mean"] == pytest.approx((1 - 3) / 2)      # bands count once each
    assert rep["against_S"]["FT"]["rank"]["parts_above"] == 2
    assert rep["ear_vs_score"]["pairs"] == 9 and rep["ear_vs_score"]["same_side_of_S"] == 2 * 3 + 2
    assert rep["repeats"] == [{"slug": "c", "spearman": pytest.approx(1.0), "same_top": True}]
