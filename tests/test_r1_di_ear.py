import pytest

from learn import r1_di_ear as E


def test_lead_pick_is_single_note_near_the_register_on_a_new_source():
    segs = [{"di": "a", "start": 1.0, "voiced": 0.95, "median": 64.0, "onset_rate": 4.0},
            {"di": "b", "start": 1.0, "voiced": 0.95, "median": 72.0, "onset_rate": 4.0},
            {"di": "c", "start": 1.0, "voiced": 0.40, "median": 72.0, "onset_rate": 4.0}]     # chords: never a lead
    assert E.lead_pick(2.0, segs, 72.0, used=set())["di"] == "b"
    assert E.lead_pick(2.0, segs, 72.0, used={"b"})["di"] == "a"
    assert E.lead_pick(2.0, segs, 72.0, used={"a", "b"}) is None


def test_picks_of():
    key = {"songs": [{"id": "x", "song": "s1", "cands": [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]},
                     {"id": "y", "song": "s2", "cands": [{"id": "d1"}]}]}
    got = E.picks_of({"x": {"fits": ["c3", "c1"]}, "y": {"none": True}}, key)
    assert [c["id"] for c in got["s1"]] == ["c1", "c3"] and got["s2"] == []
    with pytest.raises(SystemExit):
        E.picks_of({"x": {"fits": ["c1", "c2", "c3"]}}, key)
