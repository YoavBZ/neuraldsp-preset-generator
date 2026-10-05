"""The shipped audition riffs and the tool that builds them."""

from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import sys

import pytest

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


def test_a_cut_starts_before_the_pick_attack_and_fades_at_both_ends():
    np = pytest.importorskip("numpy")

    rate = 48000
    audio = np.zeros(rate)
    audio[int(0.53 * rate):] = 0.5                    # the attack lags the MIDI onset
    at = B.attack(audio, rate, near_s=0.5)
    assert abs(at - int(0.53 * rate)) <= 1
    piece = B.faded(np.ones(rate // 2), rate)
    assert piece[0] == 0.0 and piece[-1] == 0.0 and piece[rate // 4] == 1.0


def test_an_audition_with_no_riff_to_play_stops_before_making_a_folder(tmp_path, monkeypatch):
    pytest.importorskip("numpy", reason="needs the analysis extra")
    monkeypatch.setattr(A, "RIFFS", tmp_path / "none")
    monkeypatch.setattr(sys, "argv", ["audition.py", "--song", str(tmp_path / "s.wav"),
                                      "--start", "0", "--out-dir", str(tmp_path / "page"),
                                      "--preset", str(ROOT / "samples" / "Example_Clean_PR12.xml")])
    with pytest.raises(SystemExit):
        A.main()
    assert not (tmp_path / "page").exists()


def test_a_changed_shipped_riff_is_refused_not_skipped(tmp_path, monkeypatch):
    riffs = tmp_path / "riffs"
    riffs.mkdir()
    (riffs / "chords.flac").write_bytes(b"not the riff")
    (riffs / "riffs.json").write_text(json.dumps(
        {"riffs": {"chords": {"file": "chords.flac", "sha256": "0" * 64}}}))
    monkeypatch.setattr(A, "RIFFS", riffs)
    with pytest.raises(SystemExit):
        A.shipped_riffs()
