"""The shipped audition riffs and the tool that builds them."""

from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "research"))

import audition as A  # noqa: E402
import build_riffs as B  # noqa: E402


def _midi(notes, division=480, tempo=1_000_000):
    """A one-track MIDI file: notes as (start_tick, end_tick, pitch)."""
    events = [(0, b"\xff\x51\x03" + tempo.to_bytes(3, "big"))]
    for start, end, pitch in notes:
        events += [(start, bytes([0x90, pitch, 100])), (end, bytes([0x80, pitch, 0]))]
    events.sort(key=lambda e: e[0])
    body, last = b"", 0
    for tick, data in events:
        delta, buf = tick - last, []
        buf.append(delta & 0x7F)
        delta >>= 7
        while delta:
            buf.append(0x80 | (delta & 0x7F))
            delta >>= 7
        body += bytes(reversed(buf)) + data
        last = tick
    body += b"\x00\xff\x2f\x00"
    return (b"MThd" + struct.pack(">IHHH", 6, 0, 1, division)
            + b"MTrk" + struct.pack(">I", len(body)) + body)


def test_midi_notes_are_read_in_seconds_at_the_files_tempo():
    # 1,000,000 us per quarter at 480 ticks: 480 ticks is one second.
    notes = B.midi_notes(_midi([(0, 480, 67), (960, 1440, 71)]))
    assert notes == [(0.0, 1.0, 67), (2.0, 3.0, 71)]


def test_a_chord_is_found_by_its_triad_despite_a_stray_note():
    data = _midi([(0, 400, 64), (10, 400, 67), (20, 400, 71), (25, 400, 63),   # Em + D#
                  (960, 1300, 67), (970, 1300, 71), (980, 1300, 74)])           # G
    groups = B.strums(B.midi_notes(data))
    assert len(groups) == 2
    assert B.find_chord(groups, "min", 4) == 0.0
    assert B.find_chord(groups, "maj", 7) == 2.0


def test_the_shipped_riffs_match_their_record():
    record = json.loads((ROOT / "samples" / "riffs" / "riffs.json").read_text())
    assert "CC BY 4.0" in record["attribution"]
    for name, entry in record["riffs"].items():
        path = ROOT / "samples" / "riffs" / entry["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], name
    assert sorted(A.shipped_riffs()) == sorted(record["riffs"])
