"""T1's arm P (`learn/fx_t1p.py`): the seeded draw and the launcher."""

import pathlib

from learn import fx_t1p as P


def test_the_draw_is_seeded_and_keeps_t1s_order():
    items = [{"i": 800000 + j} for j in range(134)]
    a = P.draw(items)
    assert len(a) == P.N_ITEMS and a == P.draw(items)
    assert [x["i"] for x in a] == sorted(x["i"] for x in a)


def test_the_launcher_waits_for_t1s_read_then_renders_and_separates():
    s = (pathlib.Path(__file__).parents[1] / "logs" / "launch-t1p.zsh").read_text()
    assert "setopt no_bg_nice" in s and "acquire_render_slot" in s and "t1-read" not in s.split("t1p-draw")[1]
    assert s.index("t1.log") < s.index("t1p-draw") < s.index("t1p-render") < s.index("t1p-read")
    assert "t1p-separate --device mps" in s
