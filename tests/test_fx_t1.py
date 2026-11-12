"""T1 (`learn/fx_t1.py`): the items, the stock DI choice, the grid, the pick, the rule and the launcher."""

import math
import pathlib

import pytest

np = pytest.importorskip("numpy")
from learn import fx_t1 as T  # noqa: E402


def test_the_grid_spans_66_to_733_ms_in_13_cells_of_about_ten_percent():
    g = T.GRID
    assert len(g) == 13 and math.isclose(g[0], 66.0) and math.isclose(g[-1], 733.0)
    r = g[1] / g[0]
    assert all(math.isclose(b / a, r) for a, b in zip(g, g[1:])) and 1.20 < r < 1.24


def test_the_strong_third_is_the_kept_wide_delay_ons_top_mix_third():
    meta = [{"mode": "wide"}] * 6 + [{"mode": "factory"}]
    L = np.zeros((7, 8))
    L[:, 1] = [1, 1, 1, 1, 0, 1, 1]
    L[:, 4] = [0.1, 0.5, 0.9, 0.95, 0.99, 0.2, 0.99]
    strong, ons = T.strong_third(meta, L, [True, True, True, False, True, True, True])
    assert ons == [0, 1, 2, 5] and set(strong) <= set(ons) and 2 in strong and 6 not in strong and 3 not in strong


def test_a_candidate_never_plays_the_items_own_song():
    stock = {"clean": [{"di": "cambridge/TheTravellingBand_Quicksand_Full/16.wav"}, {"di": "cambridge/AleLak_X/24.wav"}]}
    assert T.stock_for("TheTravellingBand_Quicksand_Full", "clean", stock)["di"].endswith("24.wav")
    assert T.stock_for("Forkupines_SugarFaith_Full", "clean", stock)["di"].endswith("16.wav")


def test_the_pick_is_the_best_correlated_candidate():
    rng = np.random.default_rng(0)
    song = rng.standard_normal(200)
    cands = [rng.standard_normal(200) for _ in range(5)]
    cands[3] = song + 0.1 * rng.standard_normal(200)
    assert T.pick(song, cands) == 3


def test_with_delay_time_copies_the_settings():
    s = {"delay/delayTime": "500", "delay/delayMix": "0.4"}
    t = T.with_delay_time(s, 123.456)
    assert t["delay/delayTime"] == "123.456" and s["delay/delayTime"] == "500" and t["delay/delayMix"] == "0.4"


def test_the_pass_bar_needs_both_halves():
    assert T.rule([0.02, 0.2], [-0.4, -0.1])
    assert not T.rule([-0.01, 0.2], [-0.4, -0.1]) and not T.rule([0.02, 0.2], [-0.4, 0.01])


def test_the_launcher_renders_on_cpu_and_separates_on_mps_after_the_draw():
    s = (pathlib.Path(__file__).parents[1] / "logs" / "launch-t1.zsh").read_text()
    assert "setopt no_bg_nice" in s and "acquire_render_slot" in s
    assert s.index("t1-draw") < s.index("t1-render") < s.index("t1-read") and "t1-separate --device mps" in s
    assert "--shard ${k}/3" in s
