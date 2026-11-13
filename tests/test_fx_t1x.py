"""T1x (`learn/fx_t1x.py`): the ratio override and the hit rule."""

from learn import fx_t1x as X


def test_the_ratio_override_keeps_every_other_draw():
    x = {"i": 1, "draw": {"ratio_db": -9.3, "leak_db": -20.0, "target_lufs": -14.0, "mastered": True}, "section": "s"}
    y = X.with_ratio(x, 0.0)
    assert y["draw"]["ratio_db"] == 0.0 and x["draw"]["ratio_db"] == -9.3
    assert {k: v for k, v in y["draw"].items() if k != "ratio_db"} == {k: v for k, v in x["draw"].items() if k != "ratio_db"}


def test_a_hit_is_within_ten_percent():
    assert X.hit(109.0, 100.0) and not X.hit(111.0, 100.0) and X.hit(91.0, 100.0)
