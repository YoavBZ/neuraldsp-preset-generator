#!/usr/bin/env python3
"""Build the guitar riffs the audition page plays presets through (`samples/riffs/`).

    python research/build_riffs.py --source ~/ndsp-presets/references/datasets/guitar-techs/P1-downloads

The riffs are cut from the direct-input recordings of Guitar-TECHS, part P1 (Zenodo
record 14963133, CC BY 4.0): one player's dry guitar, so any preset can play them.
Part P3 is validation material and is never used here.

- **chords** (10 s): a G–D–Em–C progression, 2.5 s of each chord, in the `Set4`
  voicings, low on the neck, so the riff has body (fundamentals near 100 Hz). Each chord is found by its triad in
  the recordings' own MIDI transcription (an exact match preferred), then its pick
  attack is found in the audio, since the transcription lags it, and the piece is cut
  20 ms before the attack, with a 3 ms fade in and a 40 ms fade out.
- **line** (about 10 s): the A scale run (`P1_scales`, `A`) from its start to the
  quietest moment between 9.8 and 10 s, with the same fades: a single-note line.

Both are set to -23.7 LUFS, the median loudness of the development sets' DIs, so they
drive an amp as a typical recorded DI does (the P1 recordings sit 7-9 dB lower).
Written as 24-bit FLAC with `riffs.json`, which records every source file's SHA-256,
where each piece was cut, the gain, and the attribution the licence requires.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.append(str(PLUGIN_ROOT / "scripts"))

from _cli import die, guarded

RATE = 48000
TARGET_LUFS = -23.7
CHORD_S, LEAD_IN_S, FADE_S = 2.5, 0.02, 0.04
VOICING = "Set4"
PROGRESSION = (("maj", 7, "G"), ("maj", 2, "D"), ("min", 4, "Em"), ("maj", 0, "C"))
LINE = ("P1_scales", "A", 0.0, 9.8, 10.0)
FADE_IN_S, ATTACK_SEARCH_S = 0.003, 0.08
ATTRIBUTION = ("Guitar-TECHS: An Electric Guitar Dataset Covering Techniques, Musical "
               "Excerpts, Chords and Scales Using a Diverse Array of Hardware, by Hegel "
               "Emmanuel Pedroza Villalobos, Termeh Taheri, Wallace Abreu, Ryan Corey and "
               "Iran R. Roman (Zenodo record 14963133, https://zenodo.org/records/14963133; "
               "ICASSP 2025, doi:10.1109/ICASSP49660.2025.10887996). Licensed CC BY 4.0, "
               "https://creativecommons.org/licenses/by/4.0/. Changes: excerpts of the "
               "part-P1 direct-input recordings cut, joined, faded and level-adjusted.")


def _varlen(data: bytes, i: int):
    value = 0
    while True:
        b = data[i]
        i += 1
        value = (value << 7) | (b & 0x7F)
        if not b & 0x80:
            return value, i


def midi_notes(data: bytes):
    """[(start_s, end_s, pitch)] from a standard MIDI file, tempo changes honoured."""
    if data[:4] != b"MThd":
        raise ValueError("not a MIDI file")
    _, ntracks, division = struct.unpack(">HHH", data[8:14])
    i, events = 14, []
    for _ in range(ntracks):
        if data[i:i + 4] != b"MTrk":
            raise ValueError("malformed MIDI track")
        length = struct.unpack(">I", data[i + 4:i + 8])[0]
        j, end, tick, status = i + 8, i + 8 + length, 0, None
        while j < end:
            delta, j = _varlen(data, j)
            tick += delta
            b = data[j]
            if b == 0xFF:                                   # meta: keep only tempo
                kind = data[j + 1]
                n, j = _varlen(data, j + 2)
                if kind == 0x51:
                    events.append((tick, 0, int.from_bytes(data[j:j + 3], "big")))
                j += n
                continue
            if b in (0xF0, 0xF7):                           # sysex
                n, j = _varlen(data, j + 1)
                j += n
                continue
            if b & 0x80:
                status, j = b, j + 1
            hi = status & 0xF0
            if hi in (0xC0, 0xD0):
                j += 1
                continue
            pitch, velocity = data[j], data[j + 1]
            j += 2
            if hi == 0x90 and velocity:
                events.append((tick, 1, pitch))
            elif hi == 0x80 or hi == 0x90:
                events.append((tick, 2, pitch))
        i = end
    events.sort()
    tempo, last, seconds, held, out = 500000, 0, 0.0, {}, []
    for tick, kind, payload in events:
        seconds += (tick - last) * tempo / 1e6 / division
        last = tick
        if kind == 0:
            tempo = payload
        elif kind == 1:
            held.setdefault(payload, []).append(seconds)
        elif held.get(payload):
            out.append((held[payload].pop(0), seconds, payload))
    return sorted(out)


def strums(notes, gap_s: float = 0.25):
    """[(onset_s, pitch classes)]: notes starting within `gap_s` of a strum's first."""
    out = []
    for start, _, pitch in notes:
        if out and start - out[-1][0] < gap_s:
            out[-1][1].add(pitch % 12)
        else:
            out.append((start, {pitch % 12}))
    return out


def find_chord(groups, quality: str, root: int) -> float:
    """The onset of the first strum that is exactly the triad, or else the first that
    holds it among stray transcribed notes."""
    triad = {root % 12, (root + (4 if quality == "maj" else 3)) % 12, (root + 7) % 12}
    for exact in (True, False):
        for onset, classes in groups:
            if classes == triad if exact else triad <= classes:
                return onset
    raise ValueError(f"no {quality} triad on pitch class {root} in the transcription")


def attack(audio, rate: int, near_s: float) -> int:
    """The first sample, within ATTACK_SEARCH_S of `near_s`, where the signal rises past
    a tenth of that window's peak: the pick attack the transcription lags."""
    import numpy as np

    lo = max(0, round((near_s - ATTACK_SEARCH_S) * rate))
    window = np.abs(audio[lo:round((near_s + ATTACK_SEARCH_S) * rate)])
    return lo + int(np.argmax(window > 0.1 * window.max()))


def faded(piece, rate: int):
    import numpy as np

    piece = piece.copy()
    fade_in, fade_out = round(FADE_IN_S * rate), round(FADE_S * rate)
    piece[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
    piece[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)
    return piece


def _sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=pathlib.Path, required=True,
                    help="the folder holding the unpacked P1_chords and P1_scales")
    ap.add_argument("--out-dir", type=pathlib.Path, default=PLUGIN_ROOT / "samples" / "riffs")
    args = ap.parse_args()
    from analysis import require

    require("building the riffs")
    import numpy as np
    import pyloudnorm
    import soundfile as sf

    source = args.source.expanduser()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    meter = pyloudnorm.Meter(RATE)
    record = {"schema": "riffs-1", "attribution": ATTRIBUTION, "loudness_lufs": TARGET_LUFS,
              "riffs": {}}

    pieces, sources = [], {}
    for quality, root, name in PROGRESSION:
        audio_path = source / "P1_chords" / "audio" / "directinput" / f"directinput_{VOICING}_{quality}.wav"
        midi_path = source / "P1_chords" / "midi" / f"midi_{VOICING}_{quality}.mid"
        onset = find_chord(strums(midi_notes(midi_path.read_bytes())), quality, root)
        audio, rate = sf.read(str(audio_path))
        if rate != RATE or audio.ndim != 1:
            die(f"{audio_path} is not 48 kHz mono")
        first = attack(audio, RATE, onset) - round(LEAD_IN_S * RATE)
        if first < 0:
            die(f"{name}'s strum starts too close to the start of {audio_path.name}")
        pieces.append(faded(audio[first:first + round(CHORD_S * RATE)], RATE))
        sources[audio_path.name] = _sha(audio_path)
        sources[midi_path.name] = _sha(midi_path)
        record.setdefault("cuts", []).append({"chord": name, "file": audio_path.name,
                                              "start_s": round(first / RATE, 4),
                                              "seconds": CHORD_S})
    folder, key, start, quiet_from, quiet_to = LINE
    line_path = source / folder / "audio" / "directinput" / f"directinput_{key}.wav"
    line, rate = sf.read(str(line_path))
    if rate != RATE or line.ndim != 1:
        die(f"{line_path} is not 48 kHz mono")
    # End where the run is quietest near ten seconds, so the cut is not mid-note.
    hop = round(0.005 * RATE)
    tail = np.abs(line[round(quiet_from * RATE):round(quiet_to * RATE)])
    envelope = [tail[i:i + hop].max() for i in range(0, len(tail) - hop, hop)]
    end_at = round(quiet_from * RATE) + int(np.argmin(envelope)) * hop + hop
    line = faded(line[round(start * RATE):end_at], RATE)
    sources[line_path.name] = _sha(line_path)
    record["cuts"].append({"line": key, "file": line_path.name, "start_s": start,
                           "seconds": round(len(line) / RATE, 4)})

    for name, audio, describe in (
            ("chords", np.concatenate(pieces), "a G-D-Em-C chord progression"),
            ("line", line, "a single-note scale line in A")):
        gain = TARGET_LUFS - meter.integrated_loudness(audio)
        audio = audio * 10 ** (gain / 20)
        if np.abs(audio).max() >= 10 ** (-1 / 20):
            die(f"{name} would peak above -1 dBFS at {TARGET_LUFS} LUFS")
        path = out / f"{name}.flac"
        sf.write(str(path), audio.astype(np.float32), RATE, subtype="PCM_24")
        record["riffs"][name] = {"file": path.name, "sha256": _sha(path), "what": describe,
                                 "seconds": round(len(audio) / RATE, 3),
                                 "gain_db": round(float(gain), 2)}
    record["sources"] = sources
    (out / "riffs.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record["riffs"], indent=1))


if __name__ == "__main__":
    guarded(main)
