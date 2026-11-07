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
    cell = {("pr12", "clean"): ["goat/item_1@5#amp_1", "goat/item_1@5#amp_2", "goat/item_2@9#amp_1", "goat/item_3@7#amp_2"]}
    got = W.rotated(cell)
    assert all(u.split("@")[0] != v.split("@")[0] for u, v in got.items())
