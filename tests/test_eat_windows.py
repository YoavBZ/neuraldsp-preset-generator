"""S11's pure parts (`learn/eat_windows.py`)."""
import pytest

np = pytest.importorskip("numpy")

from learn import eat_windows as W


def test_a_read_of_all_takes_every_section_and_k_takes_k():
    rng = np.random.default_rng(0)
    assert list(W.picked(4, W.ALL, rng)) == [0, 1, 2, 3]
    assert list(W.picked(2, 5, rng)) == [0, 1]
    assert len(set(W.picked(6, 2, rng).tolist())) == 2


def test_no_window_overlaps_the_labelled_one():
    order = W.windows_of("u", 30.0, "u", [0.0, 10.0, 25.0, 30.0, 35.0, 40.0, 60.0], 10.0)
    assert set(order) == {0.0, 10.0, 40.0, 60.0}
    assert order == W.windows_of("u", 30.0, "u", [0.0, 10.0, 25.0, 30.0, 35.0, 40.0, 60.0], 10.0)


def test_far_enough_refuses_a_touching_overlap_only():
    assert W.far_enough(20.0, [10.0], 10.0) and not W.far_enough(19.9, [10.0], 10.0)


def test_backings_stay_in_the_session_and_leave_the_own_entry_out():
    pool = [{"id": "a", "session": "s"}, {"id": "b", "session": "s"}, {"id": "c", "session": "s"}, {"id": "d", "session": "t"}]
    got = W.backing_entries(pool, "a", "s")
    assert sorted(got) == [1, 2]


def test_the_placebo_reads_another_take_in_the_same_cell():
    cell = {(0, "pr12", "clean"): ["goat/item_1@5#amp_1", "goat/item_1@5#amp_2", "goat/item_2@9#amp_1", "goat/item_3@7#amp_2"]}
    got = W.rotated(cell)
    assert all(u.split("@")[0] != v.split("@")[0] for u, v in got.items())


def test_a_cell_of_one_take_has_nothing_to_borrow():
    with pytest.raises(SystemExit):
        W.rotated({(0, "pr12", "clean"): ["goat/item_1@5#amp_1", "goat/item_1@5#amp_2"]})


def test_a_rig_draws_the_same_sections_whichever_rows_are_left_out():
    a = W.picked(9, 3, W.rig_rng(1, 2, (0, "pr12", "clean"), "r"))
    b = W.picked(9, 3, W.rig_rng(1, 2, (0, "pr12", "clean"), "r"))
    assert list(a) == list(b)


def test_a_window_slice_keeps_the_trim_and_the_mono_fold():
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    sr = PS.SR
    a = np.ones(sr * 40)
    raw, sec = W.amp_section(a, sr, 20.0)
    assert len(raw) == int(round((PS.SEC_S + PS.TRIM_S) * sr))
    assert len(sec) == len(raw) - int(PS.TRIM_S * sr)
    assert abs(sec[len(sec) // 2] - T.pan_fold(0.0)) < 1e-3


def test_a_direction_never_reads_its_held_half():
    x = np.array([[1.0, 1.0], [100.0, 100.0]])
    other = np.array([[3.0, 3.0], [5.0, 5.0]])
    got = W.blended(x, [other], True)
    assert np.allclose(got[0], (1 + 3 + 5) / 3) and np.allclose(got[1], (100 + 3 + 5) / 3)


def test_the_far_arm_reads_no_labelled_audio():
    x = np.array([[1000.0], [1000.0]])
    got = W.blended(x, [np.array([[2.0], [4.0]]), np.array([[6.0], [8.0]])], False)
    assert np.allclose(got, 5.0) and got.shape == x.shape


def test_the_split_scores_each_direction_and_groups_by_item():
    judge = {t: {f"goat/item_{i}@5#amp_1|pr12": {"A": {"B": {"distance": d}}, "B": {"A": {"distance": d}}} for i in (1, 2)}
             for t, d in (("M-win", 2.0), ("M-pcs", 3.0), ("S", 4.0))}
    keys = sorted(judge["S"])
    got = W.split_rows("M-win", "M-pcs", judge, keys, {k: "main" for k in keys})
    assert got["main"]["clusters"] == 2 and abs(got["main"]["mean"] - np.log(2 / 3)) < 1e-9
