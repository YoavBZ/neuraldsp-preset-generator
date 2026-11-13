import pytest

from learn import r1_di as D


def test_distance_and_pick_on_distinct_files():
    song = {"median": 60.0, "p10": 55.0, "p90": 65.0, "voiced": 0.8, "onset_rate": 4.0}
    near = {**song, "file": "a", "start": 1.0}
    off = {**song, "median": 72.0, "file": "a", "start": 3.0}
    chords = {**song, "voiced": 0.2, "file": "b", "start": 1.0}
    other = {**song, "median": 61.0, "file": "c", "start": 2.0}
    assert D.distance(song, near) == 0.0
    assert abs(D.distance(song, chords) - 8 * 0.6) < 1e-9
    assert [s["file"] for s in D.pick(song, [off, chords, near, other])] == ["a", "c"]


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
