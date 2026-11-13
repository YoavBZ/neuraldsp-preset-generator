import pytest

from learn import r1_di as D

SONG = {"median": 60.0, "p10": 55.0, "p90": 65.0, "voiced": 0.8, "onset_rate": 4.0}


def test_pick_is_on_distinct_performances():
    near = {**SONG, "di": "a", "file": "f1", "start": 1.0}
    same_take = {**SONG, "median": 60.5, "di": "a", "file": "f2", "start": 1.0}   # another cut of take a
    other = {**SONG, "median": 61.0, "di": "c", "file": "f3", "start": 2.0}
    assert D.distance(SONG, near) == 0.0
    assert [s["di"] for s in D.pick(SONG, [same_take, other, near])] == ["a", "c"]


def test_calibration_is_robust_and_moves_the_song_into_the_di_domain():
    di = {**SONG, "voiced": 0.95}
    pairs = [(SONG, di)] * 9 + [({**SONG, "median": 72.0}, di)]                       # one octave flip
    cal = D.calibration(pairs)
    assert cal["median"] == (0.0, 0.5) and abs(cal["voiced"][0] + 0.15) < 1e-9
    assert D.cal_distance(SONG, di, cal) == 0.0                                      # the offset explains the gap
    assert D.cal_distance(SONG, {**di, "median": 61.0}, cal) == 2.0                 # 1 st over a 0.5-st spread


def test_check_cards_and_final_pick():
    cands = {"s1": {"dis": [{"source": "a", "distance": 1.0, "di_path": "p", "start_s": 0.0, "set": "goat"},
                            {"source": "lib", "distance": 2.0, "di_path": "q", "start_s": 0.0, "set": "n12"},
                            {"source": "b", "distance": 3.0, "di_path": "r", "start_s": 0.0, "set": "bks"}]},
             "s2": {"dis": [{"source": "a", "distance": 0.5, "di_path": "p2", "start_s": 1.0, "set": "goat"}]}}
    cards = D.check_cards(cands, kept={"lib"})
    assert [c["source"] for c in cards] == ["a", "b"] and cards[0]["di_path"] == "p2"
    out = D.final_pick({"s1": cands["s1"]}, {"a": "heavy", "b": "keep"}, kept={"lib"})
    assert [d["source"] for d in out["s1"]] == ["lib", "b"]
    with pytest.raises(SystemExit):
        D.final_pick({"s1": cands["s1"]}, {"a": "heavy", "b": "unsure"}, kept={"lib"})


def test_seg_features_needs_activity_and_voicing():
    np = pytest.importorskip("numpy")
    hop = 0.01
    midi = np.full(1000, 60.0)
    act = np.ones(1000, bool)
    f = D.seg_features(midi, act, act, [0.5, 1.0, 1.5], 0.0, 4.5, hop)
    assert f["median"] == 60.0 and f["voiced"] == 1.0 and abs(f["onset_rate"] - 3 / 4.5) < 1e-9
    quiet = act.copy()
    quiet[:300] = False
    assert D.seg_features(midi, quiet, quiet, [], 0.0, 4.5, hop) is None
    assert D.seg_features(midi, quiet, quiet, [], 0.0, 4.5, hop, min_active=0.0) is not None
