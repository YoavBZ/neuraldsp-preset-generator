"""Tempo-relative note times — the way to get musical delay without a selector."""

from __future__ import annotations

import pytest

from packs.timing import TimingError, note_ms, note_multiplier, quarter_ms


def test_quarter_note_from_tempo():
    assert quarter_ms(120) == 500.0
    assert quarter_ms(60) == 1000.0
    assert quarter_ms(96) == 625.0


@pytest.mark.parametrize(
    "division,expected",
    [
        ("whole", 4.0),
        ("half", 2.0),
        ("quarter", 1.0),
        ("eighth", 0.5),
        ("sixteenth", 0.25),
        ("thirtysecond", 0.125),
    ],
)
def test_plain_divisions(division, expected):
    assert note_multiplier(division) == expected


@pytest.mark.parametrize(
    "spelling",
    ["1/8 dotted", "dotted eighth", "dotted 1/8", "1/8D", "8th dotted", "1/8 DOTTED"],
)
def test_dotted_eighth_spellings_agree(spelling):
    """A dotted eighth at 120 BPM is 375 ms — the classic U2 delay."""
    assert note_ms(120, spelling) == pytest.approx(375.0)


@pytest.mark.parametrize("spelling", ["1/4", "quarter", "4th", "q", "crotchet"])
def test_quarter_spellings_agree(spelling):
    assert note_ms(120, spelling) == pytest.approx(500.0)


def test_triplets():
    assert note_ms(120, "quarter triplet") == pytest.approx(1000.0 / 3)
    assert note_ms(120, "1/8T") == pytest.approx(500.0 / 3)


def test_dotted_is_one_and_a_half_times_plain():
    for name in ("half", "quarter", "eighth", "sixteenth"):
        assert note_multiplier(f"{name} dotted") == pytest.approx(
            note_multiplier(name) * 1.5
        )


def test_case_and_whitespace_insensitive():
    assert note_ms(120, "  Dotted   EIGHTH  ") == pytest.approx(375.0)


def test_plural_and_note_suffix():
    assert note_multiplier("eighths") == 0.5
    assert note_multiplier("quarter note") == 1.0


def test_bad_input_is_rejected():
    with pytest.raises(TimingError):
        note_ms(120, "banana")
    with pytest.raises(TimingError):
        note_ms(120, "")
    with pytest.raises(TimingError, match="both dotted and triplet"):
        note_ms(120, "1/8 dotted triplet")
    with pytest.raises(TimingError, match="positive"):
        note_ms(0, "quarter")



def test_computed_times_fit_the_declared_delay_range():
    """The values we'd actually write must be writable — a spot check that the
    manifest's delayTime range admits ordinary musical delays."""
    from packs.loader import load_pack

    spec = load_pack("morgan").require("delay", "delayTime")
    for bpm in (80, 100, 120, 140, 175):
        for division in ("1/4", "1/8 dotted", "1/8", "1/16", "1/2"):
            ms = note_ms(bpm, division)
            assert spec.min <= ms <= spec.max, (
                f"{division} at {bpm} BPM is {ms} ms, outside "
                f"[{spec.min}, {spec.max}]"
            )
