"""The separation script's context window (`learn/separate.py`)."""

from learn.separate import window


def test_window_pads_both_sides_inside_the_session():
    assert window(1000, 400, 500, 100) == (300, 600)


def test_window_shifts_rather_than_shrinks_at_the_edges():
    assert window(1000, 50, 150, 100) == (0, 300)
    assert window(1000, 850, 950, 100) == (700, 1000)


def test_window_is_the_whole_session_when_it_is_short():
    assert window(200, 50, 150, 100) == (0, 200)


# --- the default separator (Mega-53, 2026-10-19) ---------------------------------------------------

import sys  # noqa: E402
import types  # noqa: E402

import pytest  # noqa: E402

from learn import separate as SEP  # noqa: E402


def test_mega53_is_the_default_and_htdemucs_stays_selectable():
    assert SEP.DEFAULT_SEPARATOR == "mega53"
    assert set(SEP.SEPARATORS) == {"mega53", "htdemucs"}
    assert SEP.check_separator("htdemucs") == "htdemucs"
    with pytest.raises(ValueError):
        SEP.check_separator("demucs")


def test_the_factory_builds_mega53_by_default_and_htdemucs_on_request(monkeypatch):
    built = []
    fake_screen = types.ModuleType("learn.separator_screen")
    fake_screen.MsstSeparator = lambda prune=True: built.append(("mega53", prune)) or "M"
    monkeypatch.setitem(sys.modules, "learn.separator_screen", fake_screen)
    import learn

    monkeypatch.setattr(learn, "separator_screen", fake_screen, raising=False)

    class FakeDemucs:
        device = "cpu"

        def __init__(self):
            built.append(("htdemucs", None))

    monkeypatch.setattr(SEP, "GuitarSeparator", FakeDemucs)
    assert SEP.guitar_separator() == "M"
    assert SEP.guitar_separator(prune=False) == "M"
    assert isinstance(SEP.guitar_separator("htdemucs"), FakeDemucs)
    assert built == [("mega53", True), ("mega53", False), ("htdemucs", None)]
    with pytest.raises(ValueError):
        SEP.guitar_separator("x")


def test_the_factory_refuses_htdemucs_off_the_cpu(monkeypatch):
    class OnMps:
        device = "mps"

    monkeypatch.setattr(SEP, "GuitarSeparator", OnMps)
    with pytest.raises(SystemExit):
        SEP.guitar_separator("htdemucs")
