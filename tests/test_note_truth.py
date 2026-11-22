"""The redo's truth on real DIs (`learn/note_truth.py`, note-rebuild-plan 12m): the P3 refusal, the clean-up, the
windows, the clusters, the consistency test, the hum share and the report's pooling. Pure: runs on the light CI runner
(no numpy). One data test needs the dataset (skipped elsewhere)."""
import pytest

from learn import note_truth as TR


def _n(on, pitch, off=None):
    return {"on": on, "off": on + 0.4 if off is None else off, "pitch": pitch}


def test_the_declared_constants():
    assert (TR.TRUTH_MIN_S, TR.TRUTH_MERGE_S) == (0.058, 0.030)
    assert TR.WINDOW_STARTS == (10.0, 70.0, 130.0) and TR.WINDOW_S == 10.25
    assert (TR.MIN_NOTES, TR.CLUSTER_S, TR.RISE_WINDOW_S, TR.CONSISTENT_WITHIN_S, TR.CONSISTENT_SHARE) == \
        (8, 0.150, 0.150, 0.030, 0.80)
    assert TR.HUM_STOP == 0.05 and list(TR.HUM_HARMONICS) == [1, 2, 3, 4, 5, 6] and TR.HUM_CENTS == 50.0
    assert set(TR.PLAYERS) == {"P1", "P2"}


def test_p3_is_refused():
    assert TR.refuse_path("/x/guitar-techs/P1-downloads/P1_chords/audio/directinput/a.wav") is None
    assert TR.refuse_path("/x/guitar-techs/P2-downloads/P2_scales/midi/midi_A.mid") is None
    assert "held out" in TR.refuse_path("/x/guitar-techs/P3_music/audio/directinput/a.wav")
    assert "outside" in TR.refuse_path("/x/guitar-techs/other/a.wav")


def test_clean_truth_drops_blips_and_merges_twins():
    notes = [_n(0.0, 60, off=0.040), _n(1.0, 62), _n(1.02, 62, off=1.8), _n(1.05, 62), _n(2.0, 64, off=2.06)]
    kept, cnt = TR.clean_truth(notes)
    assert cnt == {"short": 1, "merged": 1}
    assert [(n["on"], n["pitch"], round(n["off"], 3)) for n in kept] == [(1.0, 62, 1.8), (1.05, 62, 1.45),
                                                                         (2.0, 64, 2.06)]


def test_windows_and_in_window():
    assert TR.window_starts(80.25) == [10.0, 70.0] and TR.window_starts(20.25) == [10.0]
    assert TR.window_starts(140.25) == [10.0, 70.0, 130.0] and TR.window_starts(15.0) == []
    w = TR.in_window([_n(9.9, 60), _n(10.0, 62, off=25.0), _n(20.3, 64)], 10.0)
    assert [(n["pitch"], n["on"], n["off"]) for n in w] == [(62, 0.0, 10.25)]
    assert w[0]["amp"] == 1.0 and w[0]["bends"] == []


def test_a_strum_is_one_cluster():
    strum = [1.0, 1.04, 1.09, 1.13, 1.18]                          # each within 150 ms of the previous
    assert TR.clusters(strum + [2.0, 2.4]) == [strum, [2.0], [2.4]]


def test_consistency():
    shifts = [0.020, 0.025, 0.030, 0.018, None]                    # 4 of 5 clusters within 30 ms of the offset
    assert TR.consistent(shifts, 0.025, 8)["consistent"]
    assert not TR.consistent(shifts, 0.025, 7)["consistent"]       # under 8 notes
    assert not TR.consistent(shifts + [0.2], 0.025, 12)["consistent"]   # 4 of 6
    assert TR.consistent([], 0.0, 20) == {"consistent": False, "clusters": 0, "share": None}


def test_hum_share():
    assert TR.on_mains(35) and TR.on_mains(47) and not TR.on_mains(64)   # 60 Hz is MIDI 35; 120 Hz is MIDI 47
    assert TR.hum_share([_n(0, 47), _n(1, 64), _n(2, 69), _n(3, 71)]) == 0.25 and TR.hum_share([]) == 0.0


def test_truth_precision_pools_by_player_and_kind():
    rows = [{"player": "P1", "kind": "chords", "matched": 8, "ref": 10, "est": 16},
            {"player": "P1", "kind": "scales", "matched": 15, "ref": 15, "est": 20},
            {"player": "P2", "kind": "chords", "matched": 3, "ref": 6, "est": 4}]
    got = TR.truth_precision(rows)
    assert got["P1|chords"]["recall"] == 0.8 and got["P1|chords"]["precision"] == 0.5
    assert got["P1"]["recall"] == pytest.approx(23 / 25) and got["P1"]["windows"] == 2
    assert got["P2|chords"]["recall"] == 0.5 and "P2|scales" not in got


def test_listing_body_counts():
    body = TR.listing_body([{"name": "a"}], [{"player": "P1", "kind": "chords", "consistent": True},
                                             {"player": "P1", "kind": "chords", "consistent": False}],
                           {"short": 3, "merged": 1})
    assert body["by_player_kind"] == {"P1|chords": {"windows": 2, "consistent": 1}}
    assert body["rule"]["share"] == 0.80 and body["cleanup"]["short"] == 3
    assert TR.window_key({"player": "P2", "kind": "scales", "name": "A"}, 70.0) == "P2|scales|A@70"


def test_the_listing_is_written_once(tmp_path):
    from learn import note_rebuild as NR

    p = tmp_path / "truth.json"
    NR.write_once(p, {"body": {}})
    with pytest.raises(SystemExit, match="never overwritten"):
        NR.write_once(p, {"body": {}})


def test_the_dataset_files_are_40_and_45():
    if not TR.ROOT.exists():
        pytest.skip("no Guitar-TECHS on disk")
    files = TR.truth_files()
    assert sum(f["player"] == "P1" for f in files) == 40 and sum(f["player"] == "P2" for f in files) == 45
    assert not any("P3" in f["di"] or "P3" in f["midi"] for f in files)
