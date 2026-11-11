"""A1 (`learn/amp_di_compare.py`): the stock-DI draw, the shape and distance, the pick, the rows and the reading."""

import math
import pathlib

import pytest

from learn import amp_di_compare as A


def test_the_stock_draw_takes_distinct_di_files_per_class_seeded():
    cands = [{"unit": f"u{i}", "di": f"d{i % 3}", "cls": "clean" if i < 6 else "crunch", "di_path": "p", "start_s": 0.25}
             for i in range(10)]
    got = A.draw_stock(cands)
    assert set(got) == {"clean", "crunch"} and all(len(v) == 2 and len({c["di"] for c in v}) == 2 for v in got.values())
    assert A.draw_stock(cands) == got
    with pytest.raises(SystemExit):
        A.draw_stock(cands, per_class=4)


def test_the_shape_removes_level_and_the_pick_takes_the_closest_amp():
    s = A.shape([[10, 10], [20, 20], [30, 30]])
    assert s == pytest.approx([-10.0, 0.0, 10.0]) and A.shape([[110, 110], [120, 120], [130, 130]]) == pytest.approx(s)
    renders = {"pr12": [[-9, 0, 9], [-11, 0, 11]], "sw50r": [[5, 0, -5]] * 2, "ac20": [[0, 0, 0]] * 2}
    assert A.pick(s, renders) == "pr12" and A.distance([0, 3], [4, 0]) == 5.0


def test_the_rows_read_each_pick_against_the_constant_and_w_on_the_models_renders():
    judge = {"pr12": {"A": {"A": 1.0, "B": 2.0}, "B": {"A": 2.0, "B": 1.0}},
             "sw50r": {"A": {"A": 2.0, "B": 1.0}, "B": {"A": 1.0, "B": 2.0}},
             "ac20": {"A": {"A": 3.0, "B": 4.0}, "B": {"A": 4.0, "B": 3.0}}}
    picks = {"stem": {"A": "pr12", "B": "ac20"}, "clean amp track": {"A": "sw50r", "B": "sw50r"}}
    rows, dropped = A.unit_rows("u", "c", "clean", judge, picks, {"A": "ac20", "B": "pr12"})
    v = lambda n: [x for *_, x in rows[n]]   # noqa: E731
    assert dropped == 0 and v("DI-compare - always sw50r") == pytest.approx([math.log(2.0), math.log(4.0)])
    assert v("DI-compare - W") == pytest.approx([math.log(2.0 / 4.0), math.log(4.0 / 2.0)])
    assert v("DI-compare on the clean amp track - always sw50r") == pytest.approx([0.0, 0.0])
    assert v("search-half argmin - always sw50r")[0] == pytest.approx(math.log(2.0))
    assert v("DI-compare - always sw50r (clean)") == v("DI-compare - always sw50r")


def test_the_reading_learns_only_when_better_somewhere_and_worse_nowhere():
    row = lambda lo, hi: {"mean": (lo + hi) / 2, "lo90": lo, "hi90": hi, "clusters": 8}   # noqa: E731
    assert A.reading({"bks": row(-0.05, -0.01), "goat": None, "pooled": None}) == "learns"
    assert A.reading({"bks": row(-0.02, 0.01), "goat": None, "pooled": None}) == "undecided"
    assert A.reading({"bks": row(0.01, 0.05), "goat": row(-0.05, -0.01), "pooled": None}) == "split"


def test_the_launcher_draws_renders_then_reads_on_slot_locks():
    t = (pathlib.Path(__file__).resolve().parents[1] / "logs" / "launch-a1.zsh").read_text()
    order = [t.index(x) for x in ("run draw", "three render")]
    assert order == sorted(order) and "acquire_render_slot" in t and "train-ft" not in t and "run rows" not in t


def test_the_band_mask_keeps_60_hz_to_8_khz():
    pytest.importorskip("numpy")
    m = A.band_mask()
    assert len(m) == 96 and 0 < sum(m) < 96 and not m[0] and not m[-1]
