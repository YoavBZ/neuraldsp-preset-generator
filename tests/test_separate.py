"""The separation script's context window (`learn/separate.py`)."""

from learn.separate import window


def test_window_pads_both_sides_inside_the_session():
    assert window(1000, 400, 500, 100) == (300, 600)


def test_window_shifts_rather_than_shrinks_at_the_edges():
    assert window(1000, 50, 150, 100) == (0, 300)
    assert window(1000, 850, 950, 100) == (700, 1000)


def test_window_is_the_whole_session_when_it_is_short():
    assert window(200, 50, 150, 100) == (0, 200)
