"""A2 (`learn/amp_di_compare_r.py`): the units, the deciding pool and the reading; the launcher."""

import pathlib

import pytest

from learn import amp_di_compare_r as A


def _ru(s, u, a="sw50r", cls="clean"):
    return {"set": s, "unit": u, "amp": a, "fold": 1, "lag": 3, "cluster": f"c-{u}", "prt": {"cls": cls}}


def test_the_units_are_one_per_unit_outside_n12():
    got = A.units_of([_ru("bks", "b", "pr12"), _ru("bks", "b", "sw50r"), _ru("n12", "n"), _ru("cap1", "c"),
                      _ru("panel", "p"), _ru("goat", "g")])
    assert [(u["set"], u["unit"]) for u in got] == [("bks", "b"), ("cap1", "c"), ("panel", "p"), ("goat", "g")]


def test_the_reading_decides_on_the_fresh_sets_and_refuses_worse_anywhere():
    pytest.importorskip("numpy")
    row = lambda lo, hi: {"mean": (lo + hi) / 2, "lo90": lo, "hi90": hi, "clusters": 8}   # noqa: E731
    und, better, worse = row(-0.02, 0.01), row(-0.05, -0.01), row(0.01, 0.05)
    assert A.reading({"cap1": better, "panel": und, "goat": und, "bks": und}, und) == "learns"
    assert A.reading({"cap1": und, "panel": und, "goat": better, "bks": und}, und) == "undecided"   # GOAT doesn't decide
    assert A.reading({"cap1": better, "panel": und, "goat": und, "bks": worse}, und) == "split"
    assert A.reading({"cap1": und, "panel": und, "goat": und, "bks": und}, worse) == "worse"


def test_the_launcher_predicts_judges_renders_then_reads():
    t = (pathlib.Path(__file__).resolve().parents[1] / "logs" / "launch-a2.zsh").read_text()
    order = [t.index(x) for x in ("a2-predict", "a2-judge", "a2-render", "a2-embed", "a2-rows")]
    assert order == sorted(order) and "acquire_render_slot" in t and "train-ft" not in t


def test_the_stock_overlap_finds_a_unit_on_a_stock_file_or_its_multitrack():
    stock = {"clean": [{"di": "cambridge/Song/16_DI.wav"}]}
    units = [{"unit": "a", "prt": {"di": "cambridge/Song/16_DI.wav"}}, {"unit": "b", "prt": {"di": "cambridge/Song/09_DI.wav"}},
             {"unit": "c", "prt": {"di": "goat/item_1"}}]
    got = A.stock_overlap(units, stock)
    assert got == {"file": ["a"], "session": ["a", "b"]}
