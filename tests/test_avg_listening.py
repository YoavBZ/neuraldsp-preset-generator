"""Listening check L's answer sheets (`docs/avg-measure-listening-plan.md`): the phone
pages' answer lines and the terminal's `ANSWERS.md` read alike."""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learn import build_avg_listening as B  # noqa: E402

LINES = ("Sitting 1: " + " ".join(f"{n}{'AB'[n % 2]}" for n in range(1, 19)) + "\n"
         "sitting 2: " + " ".join(f"{n}{'ab'[n % 3 == 0]}" for n in range(19, 37)) + "\n")


def test_phone_lines_and_answers_md_read_alike(tmp_path):
    phone = tmp_path / "phone.txt"
    phone.write_text(LINES)
    got = B.read_sheet(phone)
    assert sorted(got) == list(range(1, 37)) and set(got.values()) == {"A", "B"}
    md = tmp_path / "ANSWERS.md"
    md.write_text("# Answers\n\n## Sitting 1\n"
                  + "".join(f"{n:02d}: {got[n]}\n" for n in range(1, 19))
                  + "\n## Sitting 2\n" + "".join(f"{n:02d}: {got[n]}\n" for n in range(19, 37)))
    assert B.read_sheet(md) == got


@pytest.mark.parametrize("text, why", [
    ("Sitting 1: 1A 2B   (16 left)\n", "not an answer"),
    ("Sitting 1: 1A 19B\n", "not in sitting 1"),
    ("Sitting 2: 18A\n", "not in sitting 2"),
    ("Sitting 1: 1A 1B\n", "answered twice"),
    ("Sitting 1: 1A\nSitting 1: 1A\n", "answered twice"),
    ("Sitting 1: 1?\n", "not an answer"),
    ("Sitting 1: 1A\nthanks!\n", "not a sitting line"),
])
def test_phone_lines_are_read_strictly(text, why):
    with pytest.raises(ValueError, match=why):
        B.read_phone_lines(text)


def test_public_trials_come_from_file_names_alone(tmp_path):
    for n in (1, 18, 19, 36):
        for suffix in ("", "-R", "-A", "-B"):
            (tmp_path / f"trial-{n:02d}{suffix}.flac").write_bytes(b"")
    assert B.public_trials(tmp_path) == {1: 1, 18: 1, 19: 2, 36: 2}
