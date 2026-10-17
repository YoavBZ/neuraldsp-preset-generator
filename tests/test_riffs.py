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


def test_every_riff_declares_its_style_register_and_default():
    """Six riffs: chords and single lines in three registers (riff-library-plan.md);
    only the first two play by default, so a page never renders six unasked."""
    record = json.loads((ROOT / "samples" / "riffs" / "riffs.json").read_text())
    riffs = record["riffs"]
    assert {(e["style"], e["register"]) for e in riffs.values()} == {
        (s, r) for s in ("chords", "line") for r in ("low", "mid", "high")}
    assert sorted(n for n, e in riffs.items() if e["default"]) == ["chords", "line"]
    assert A.default_riffs() == ["chords", "line"]
    # The low and mid chords are assembled from EGFxSet notes (rebuilt 2026-10-17);
    # the rest are the Guitar-TECHS cuts heard and kept, unchanged.
    assert {n for n, e in riffs.items() if e["source"] == "egfxset"} == {"chords", "chords-mid"}
    assert all(riffs[n]["method"] == B.note_method() for n in ("chords", "chords-mid"))
    assert riffs["chords-high"]["sha256"].startswith("29e03e21")
    assert riffs["line"]["sha256"].startswith("f0102680")
    assert "EGFxSet" in record["attribution"] and "Guitar-TECHS" in record["attribution"]


def test_register_is_the_median_pitch_of_the_cut_with_contiguous_edges():
    assert B.register_of([40, 45, 59])[0] == "low"
    assert B.register_of([60, 62, 64])[0] == "mid"
    assert B.register_of([66, 69, 71])[0] == "mid"          # median A4 is still mid
    assert B.register_of([70, 74, 77])[0] == "high"
    assert B.register_of([70, 74, 40])[0] == "high"          # one stray low note
    assert B.note_name(69) == "A4" and B.note_name(60) == "C4"


def test_a_voicing_up_the_neck_is_found_near_the_named_time():
    data = _midi([(0, 400, 55), (10, 400, 59), (20, 400, 62),            # G low, t=0
                  (4800, 5200, 67), (4810, 5200, 71), (4820, 5200, 74)])  # G high, t=10
    groups = B.strums(B.midi_notes(data))
    assert B.find_chord(groups, "maj", 7) == 0.0
    assert B.find_chord(groups, "maj", 7, near=9.5) == 10.0


def test_each_riffs_recorded_median_sits_in_its_register_and_levels_match():
    record = json.loads((ROOT / "samples" / "riffs" / "riffs.json").read_text())
    for name, entry in record["riffs"].items():
        assert B.register_of([entry["median_pitch"]])[0] == entry["register"], name
    np = pytest.importorskip("numpy")
    pyloudnorm = pytest.importorskip("pyloudnorm")
    sf = pytest.importorskip("soundfile")
    for name, entry in record["riffs"].items():
        audio, rate = sf.read(str(ROOT / "samples" / "riffs" / entry["file"]))
        loud = pyloudnorm.Meter(rate).integrated_loudness(np.asarray(audio))
        assert abs(loud - record["loudness_lufs"]) < 0.1, (name, loud)


def test_every_cut_names_its_riff_once_per_piece():
    record = json.loads((ROOT / "samples" / "riffs" / "riffs.json").read_text())
    counts = {}
    for cut in record["cuts"]:
        counts[cut["riff"]] = counts.get(cut["riff"], 0) + 1
    assert counts == {"chords": 4, "chords-mid": 4, "chords-high": 4,
                      "line": 1, "line-mid": 1, "line-high": 1}


def test_each_note_riff_records_its_notes_and_the_retuning():
    record = json.loads((ROOT / "samples" / "riffs" / "riffs.json").read_text())
    for name, spec in B.NOTE_RIFFS.items():
        cuts = [c for c in record["cuts"] if c["riff"] == name]
        assert [c["chord"] for c in cuts] == list(spec["voicings"])
        for cut in cuts:
            assert cut["notes"] == [f"{s}-{f}" for s, f in spec["voicings"][cut["chord"]]]
            assert len(cut["retuned_cents"]) == len(cut["notes"])
            assert all(abs(c) <= 15 for c in cut["retuned_cents"])
            for note in cut["notes"]:
                assert f"egfxset/Clean/{cut['pickup']}/{note}.wav" in record["sources"]
    pitches = [B.OPEN_STRINGS[s] + f for v in B.NOTE_RIFFS["chords"]["voicings"].values()
               for s, f in v]
    assert B.register_of(pitches) == ("low", 55)


def test_a_detuned_note_is_measured_in_cents():
    np = pytest.importorskip("numpy")
    rate = 48000
    t = np.arange(3 * rate) / rate
    f = 82.41 * 2 ** (10 / 1200)                       # E2, 10 cents sharp
    tone = sum(np.sin(2 * np.pi * h * f * t) / h for h in (1, 2, 3))
    assert abs(B.detune_cents(tone, rate, 40) - 10) < 0.5


def test_a_strum_goes_down_then_up_and_ends_muted():
    np = pytest.importorskip("numpy")
    pyloudnorm = pytest.importorskip("pyloudnorm")
    rate = 48000
    notes = [np.ones(3 * rate) * 0.1 for _ in range(4)]
    chord = B.strummed(notes, rate, pyloudnorm.Meter(rate))
    assert len(chord) == round(B.CHORD_S * rate)
    level = np.abs(chord)
    first = int(np.argmax(level > 0))
    assert first == round(B.LEAD_IN_S * rate)                 # the low string, 20 ms in
    down = [round((B.LEAD_IN_S + k * B.DOWN_GAP_S) * rate) for k in range(4)]
    assert level[down[1] - 1] < level[down[1] + 1]           # the strings enter one by one
    up = round(B.UP_AT_S * rate)                              # the high string is re-plucked first
    assert level[up - 2] < level[up - round(B.REPLUCK_S * rate)]
    assert level[-1] == 0.0 and level[-round(B.RELEASE_S * rate) - 1] > 0.0
    assert round(B.UP_GAP_S * rate) == 863                    # the approved build's spacing


def test_a_prepared_note_is_retuned_and_its_lows_untouched():
    pytest.importorskip("noisereduce")
    np = pytest.importorskip("numpy")
    rate = 48000
    t = np.arange(4 * rate) / rate
    f = 110 * 2 ** (12 / 1200)                         # A2, 12 cents sharp
    tone = np.exp(-t) * sum(np.sin(2 * np.pi * h * f * t) / h for h in (1, 2, 3))
    note, cents = B.prepared_note(tone, rate, 45)
    assert abs(cents - 12) < 0.5
    assert abs(B.detune_cents(note, rate, 45)) < 0.5
    assert note[0] == 0.0
