import pytest
"""The model path (`learn/product_path.py`): the window choice and the amp pick."""

from learn import product_path as PP


def test_the_pick_is_the_least_mean_cosine_distance():
    stem = [1.0, 0.0]
    feats = {"pr12": [[0.0, 1.0], [0.1, 1.0]], "sw50r": [[1.0, 0.1], [1.0, 0.0]], "ac20": [[1.0, 1.0], [1.0, 1.0]]}
    amp, dist = PP.pick_amp(stem, feats)
    assert amp == "sw50r" and dist["sw50r"] < dist["ac20"] < dist["pr12"]


def test_the_delay_rule_is_d1s():
    assert PP.delay_rule(0.5, (300.0, 305.0), 302.0, 250.0) == (False, None, None)
    on, ms, which = PP.delay_rule(0.8, (300.0, 305.0), 302.0, 250.0)
    assert on and ms == 302.0 and "peak" in which
    on, ms, which = PP.delay_rule(0.8, (300.0, 150.0), 302.0, 250.0)
    assert on and ms == 250.0 and "neighbours" in which


def test_candidates_stay_inside_the_part_and_clear_of_the_ends():
    assert PP.candidate_starts((0.0, 30.0), 30.0) == [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0,
                                                     14.0, 15.0, 16.0, 17.0, 18.0]
    assert PP.candidate_starts((100.0, 112.0), 300.0) == [100.0, 101.0, 102.0]
    assert PP.candidate_starts((0.0, 11.0), 11.0) == []


def test_select_window_takes_the_typical_steady_present_one():
    rows = [{"start": 0.0, "steady": True, "present": True, "profile": [0.0, 0.0]},
            {"start": 1.0, "steady": True, "present": True, "profile": [1.0, 0.0]},
            {"start": 2.0, "steady": True, "present": True, "profile": [2.0, 0.0]},
            {"start": 3.0, "steady": False, "present": True, "profile": [1.0, 0.0]}]
    assert PP.select_window(rows) == (1.0, "steady and present")
    assert PP.select_window([{**r, "present": False} for r in rows])[1] == "steady only"
    assert PP.select_window([{**r, "steady": False} for r in rows])[1] == "none steady"


def test_steady_whole_catches_a_fade_and_a_late_entry():
    np = pytest.importorskip("numpy")
    from learn import pretrain_set as PS

    sr, rng = PS.SR, np.random.default_rng(0)
    x = rng.standard_normal(10 * sr) * 0.1
    assert PP.steady_whole(x, sr)[0]
    fade = x * np.concatenate([np.ones(7 * sr), np.full(3 * sr, 0.01)])           # the song ends at 7 s
    late = x * np.concatenate([np.full(sr, 0.01), np.ones(9 * sr)])               # the guitar enters at 1 s
    assert not PP.steady_whole(fade, sr)[0] and not PP.steady_whole(late, sr)[0]
