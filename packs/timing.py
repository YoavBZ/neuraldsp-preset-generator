"""Tempo-relative times, so musical delay works without a sync selector.

The plugin can lock delay to note divisions via a `*SyncNote` selector, but the
integer-to-note mapping is not visible anywhere in the UI, so it cannot be read
off the screen (see `scripts/probe.py` for how to discover it).

It also doesn't matter for most requests. A "dotted eighth delay at 120 BPM" is
375 ms, and `delayTime` takes milliseconds directly. Computing the value is
exact, needs no selector, and leaves the delay free-running — so it sounds right
regardless of what the host tempo is doing.

    >>> note_ms(120, "1/8 dotted")
    375.0
    >>> note_ms(96, "quarter")
    625.0

Use the selector only when the user explicitly wants the delay to *follow* host
tempo changes. Otherwise prefer this.
"""

from __future__ import annotations

import re
from typing import Dict

# Multiplier relative to a quarter note.
BASE: Dict[str, float] = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "sixteenth": 0.25,
    "thirtysecond": 0.125,
    "sixtyfourth": 0.0625,
}

# Spellings people actually use, mapped onto the canonical names above.
ALIASES: Dict[str, str] = {
    "1/1": "whole", "1": "whole", "w": "whole",
    "1/2": "half", "2nd": "half", "h": "half",
    "1/4": "quarter", "4th": "quarter", "q": "quarter", "crotchet": "quarter",
    "1/8": "eighth", "8th": "eighth", "e": "eighth", "quaver": "eighth",
    "1/16": "sixteenth", "16th": "sixteenth", "s": "sixteenth",
    "1/32": "thirtysecond", "32nd": "thirtysecond",
    "thirty-second": "thirtysecond", "thirty second": "thirtysecond",
    # The plugin's own sync-note tables go down to 1/64, so this path has to
    # reach as far as the selector does or it stops being a full alternative.
    "1/64": "sixtyfourth", "64th": "sixtyfourth",
    "sixty-fourth": "sixtyfourth", "sixty fourth": "sixtyfourth",
}

DOTTED = 1.5          # a dot adds half the note's value
TRIPLET = 2.0 / 3.0   # three in the space of two


class TimingError(ValueError):
    """An unparseable note division."""


def quarter_ms(bpm: float) -> float:
    """Milliseconds per quarter note at the given tempo."""
    try:
        tempo = float(bpm)
    except (TypeError, ValueError):
        raise TimingError(f"tempo must be a number, got {bpm!r}") from None
    if tempo <= 0:
        raise TimingError(f"tempo must be positive, got {bpm}")
    return 60000.0 / tempo


def note_multiplier(division: str) -> float:
    """Multiplier of a quarter note for a division like '1/8 dotted'."""
    text = " ".join(str(division).strip().lower().split())
    if not text:
        raise TimingError("no note division given")

    dotted = False
    triplet = False

    # Trailing shorthand: "1/8D", "1/8T", "8thd", "1/4t".
    shorthand = re.fullmatch(r"(.*?)([dt])", text)
    if shorthand and shorthand.group(1).strip():
        candidate = shorthand.group(1).strip()
        if _lookup(candidate) is not None:
            text = candidate
            dotted = shorthand.group(2) == "d"
            triplet = shorthand.group(2) == "t"

    # Word forms, in any order: "dotted eighth", "1/8 dotted", "eighth triplet".
    words = []
    for word in text.split():
        if word in ("dotted", "dot", "dotted."):
            dotted = True
        elif word in ("triplet", "triplets", "trip"):
            triplet = True
        elif word == "note":
            continue
        else:
            words.append(word)

    base = _lookup(" ".join(words))
    if base is None:
        raise TimingError(
            f"unrecognised note division {division!r}. Try one of "
            f"{', '.join(sorted(BASE))}, optionally with 'dotted' or 'triplet' "
            f"(e.g. '1/8 dotted', 'quarter triplet')."
        )

    if dotted and triplet:
        raise TimingError(f"{division!r} is both dotted and triplet; pick one")

    value = base
    if dotted:
        value *= DOTTED
    if triplet:
        value *= TRIPLET
    return value


def _lookup(text: str) -> float | None:
    text = text.strip()
    if text in BASE:
        return BASE[text]
    if text in ALIASES:
        return BASE[ALIASES[text]]
    # "eighths" / "quarters"
    if text.endswith("s") and text[:-1] in BASE:
        return BASE[text[:-1]]
    return None


def note_ms(bpm: float, division: str) -> float:
    """Delay time in milliseconds for a note division at a tempo.

    Round-trip friendly: the result is what you write to a `metered` ms
    parameter such as `delay/delayTime`.
    """
    return quarter_ms(bpm) * note_multiplier(division)


def note_hz(bpm: float, division: str) -> float:
    """Rate in Hz for a note division at a tempo — one cycle per note.

    Lets a tempo-locked tremolo be written as a free-running rate, the same
    trick `note_ms` plays for delay. An eighth-note tremolo at 120 BPM is 4 Hz.
    """
    return 1000.0 / note_ms(bpm, division)

