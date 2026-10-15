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
- **chords-mid**, **chords-high**, **line-mid**, **line-high** (2026-10-15,
  `docs/riff-library-plan.md`): the same styles higher on the neck. Chords use the
  `Set2` and `Set1` voicings at the strums the plan names; lines a 10-s window of a
  scale's middle or top positions. Each riff's register is the median MIDI pitch of
  every note in its cut (low below C4, mid C4-A4, high above A4); `--plan-only` prints
  the strums, notes and medians, and the build refuses a riff outside its register.
  The first two riffs are never re-encoded: a riff whose file still matches
  `riffs.json` is kept as it is.

All are set to -23.7 LUFS, the median loudness of the development sets' DIs, so they
drive an amp as a typical recorded DI does (the P1 recordings sit 5-10 dB lower).
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
PROGRESSION = (("maj", 7, "G"), ("maj", 2, "D"), ("min", 4, "Em"), ("maj", 0, "C"))
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


def find_chord(groups, quality: str, root: int, near: float | None = None) -> float:
    """The onset of the first strum that is exactly the triad, or else the first that
    holds it among stray transcribed notes. With `near`, the matching strum closest to
    that time instead of the first (a voicing further up the neck)."""
    triad = {root % 12, (root + (4 if quality == "maj" else 3)) % 12, (root + 7) % 12}
    for exact in (True, False):
        found = [onset for onset, classes in groups
                 if (classes == triad if exact else triad <= classes)]
        if found:
            return found[0] if near is None else min(found, key=lambda t: abs(t - near))
    raise ValueError(f"no {quality} triad on pitch class {root} in the transcription")


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
# Register by the median MIDI pitch of every note in a cut (riff-library-plan.md):
# low below C4 (60), mid C4 to A4 (60-69), high above A4.
REGISTER_EDGES = (60, 69)


def note_name(pitch: int) -> str:
    return f"{NOTE_NAMES[pitch % 12]}{pitch // 12 - 1}"


def register_of(pitches) -> tuple:
    """(register, median pitch) of a cut's notes."""
    import statistics

    median = statistics.median(pitches)
    low, high = REGISTER_EDGES
    return ("low" if median < low else "mid" if median <= high else "high"), median


def notes_between(notes, start_s: float, end_s: float) -> list:
    """The pitches of notes starting inside [start_s, end_s)."""
    return [pitch for onset, _, pitch in notes if start_s <= onset < end_s]


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


# The riffs (riff-library-plan.md). `chords` and `line` are the two first shipped ones:
# kept as they are, never re-encoded.
CHORD_RIFFS = {
    "chords": dict(voicing="Set4", register="low", near={}, default=True,
                   what="a G-D-Em-C chord progression, low on the neck"),
    "chords-mid": dict(voicing="Set2", register="mid", default=False,
                       near={"G": 148.1, "D": 55.9, "Em": 44.0, "C": 120.0},
                       what="a G-D-Em-C chord progression, mid-neck voicings"),
    "chords-high": dict(voicing="Set1", register="high", default=False,
                        near={"G": 36.0, "D": 140.0, "Em": 148.1, "C": 96.0},
                        what="a G-D-Em-C chord progression on the top three strings, "
                             "frets 10-13"),
}
LINE_RIFFS = {
    "line": dict(key="A", start=0.0, register="low", default=True,
                 what="a single-note scale line in A, low on the neck"),
    "line-mid": dict(key="A", start=65.0, register="mid", default=False,
                     what="a single-note scale line in A, a mid-neck position"),
    "line-high": dict(key="E", start=143.5, register="high", default=False,
                      what="a single-note scale line in E, the top positions"),
}
LINE_SECONDS = 10.0


def _quietest(audio, rate: int, start_s: float, end_s: float) -> int:
    """The sample at the quietest 5 ms between start_s and end_s, so a cut is not
    mid-note."""
    import numpy as np

    hop = round(0.005 * rate)
    lo = max(0, round(start_s * rate))
    window = np.abs(audio[lo:round(end_s * rate)])
    if len(window) <= hop:
        return lo
    envelope = [window[i:i + hop].max() for i in range(0, len(window) - hop, hop)]
    return lo + int(np.argmin(envelope)) * hop + hop


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=pathlib.Path, required=True,
                    help="the folder holding the unpacked P1_chords and P1_scales")
    ap.add_argument("--out-dir", type=pathlib.Path, default=PLUGIN_ROOT / "samples" / "riffs")
    ap.add_argument("--plan-only", action="store_true",
                    help="print each riff's chosen strums or window, notes and register "
                         "median, and stop before cutting any audio")
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
    index = out / "riffs.json"
    old = json.loads(index.read_text()) if index.exists() else {}
    record = {"schema": "riffs-2", "attribution": ATTRIBUTION, "loudness_lufs": TARGET_LUFS,
              "register_edges": {"low_below": note_name(REGISTER_EDGES[0]),
                                 "high_above": note_name(REGISTER_EDGES[1])},
              "riffs": {}, "cuts": [],
              "sources": dict(old.get("sources", {}))}

    def keep(name) -> bool:
        """An already shipped riff whose file still matches its record is left alone."""
        entry = old.get("riffs", {}).get(name)
        path = out / entry["file"] if entry else None
        return bool(entry and path.exists() and _sha(path) == entry["sha256"])

    built, problems, measured = {}, [], {}
    for name, spec in CHORD_RIFFS.items():
        pieces, cuts, pitches = [], [], []
        for quality, root, chord in PROGRESSION:
            stem = f"{spec['voicing']}_{quality}"
            audio_path = source / "P1_chords" / "audio" / "directinput" / f"directinput_{stem}.wav"
            midi_path = source / "P1_chords" / "midi" / f"midi_{stem}.mid"
            notes = midi_notes(midi_path.read_bytes())
            onset = find_chord(strums(notes), quality, root, spec["near"].get(chord))
            strum = notes_between(notes, onset - 0.05, onset + CHORD_S)
            pitches += strum
            print(f"{name} {chord}: {midi_path.name} at {onset:.2f} s, "
                  f"{' '.join(note_name(p) for p in sorted(set(strum)))}")
            if args.plan_only or keep(name):
                continue
            audio, rate = sf.read(str(audio_path))
            if rate != RATE or audio.ndim != 1:
                die(f"{audio_path} is not 48 kHz mono")
            first = attack(audio, RATE, onset) - round(LEAD_IN_S * RATE)
            if first < 0:
                die(f"{chord}'s strum starts too close to the start of {audio_path.name}")
            pieces.append(faded(audio[first:first + round(CHORD_S * RATE)], RATE))
            record["sources"][audio_path.name] = _sha(audio_path)
            record["sources"][midi_path.name] = _sha(midi_path)
            cuts.append({"riff": name, "chord": chord, "file": audio_path.name,
                         "start_s": round(first / RATE, 4), "seconds": CHORD_S})
        register, median = register_of(pitches)
        measured[name] = (median, min(pitches), max(pitches))
        print(f"  {name}: median {note_name(round(median))} ({median}), {register}"
              f" (declared {spec['register']})")
        if register != spec["register"]:
            problems.append(f"{name} measures {register}, declared {spec['register']}")
        if pieces:
            built[name] = (np.concatenate(pieces), cuts)
    for name, spec in LINE_RIFFS.items():
        stem = f"directinput_{spec['key']}"
        line_path = source / "P1_scales" / "audio" / "directinput" / f"{stem}.wav"
        midi_path = source / "P1_scales" / "midi" / f"midi_{spec['key']}.mid"
        notes = midi_notes(midi_path.read_bytes())
        pitches = notes_between(notes, spec["start"], spec["start"] + LINE_SECONDS)
        register, median = register_of(pitches)
        measured[name] = (median, min(pitches), max(pitches))
        print(f"{name}: {line_path.name} {spec['start']}-{spec['start'] + LINE_SECONDS} s, "
              f"{note_name(min(pitches))}-{note_name(max(pitches))}, median "
              f"{note_name(round(median))} ({median}), {register} (declared {spec['register']})")
        if register != spec["register"]:
            problems.append(f"{name} measures {register}, declared {spec['register']}")
        if args.plan_only or keep(name):
            continue
        line, rate = sf.read(str(line_path))
        if rate != RATE or line.ndim != 1:
            die(f"{line_path} is not 48 kHz mono")
        begin = (round(spec["start"] * RATE) if spec["start"] == 0
                 else _quietest(line, RATE, spec["start"] - 0.3, spec["start"]))
        end_at = _quietest(line, RATE, begin / RATE + LINE_SECONDS - 0.2, begin / RATE + LINE_SECONDS)
        piece = faded(line[begin:end_at], RATE)
        record["sources"][line_path.name] = _sha(line_path)
        record["sources"][midi_path.name] = _sha(midi_path)
        built[name] = (piece, [{"riff": name, "line": spec["key"], "file": line_path.name,
                                "start_s": round(begin / RATE, 4),
                                "seconds": round(len(piece) / RATE, 4)}])
    if problems:
        die("; ".join(problems))
    if args.plan_only:
        return

    for name, spec in {**CHORD_RIFFS, **LINE_RIFFS}.items():
        style = "chords" if name in CHORD_RIFFS else "line"
        median, lowest, highest = measured[name]
        meta = {"style": style, "register": spec["register"], "default": spec["default"],
                "median_pitch": median, "notes": f"{note_name(lowest)}-{note_name(highest)}"}
        if keep(name):
            record["riffs"][name] = {**old["riffs"][name], **meta}
            # The first records' cuts carry no riff name: chord pieces are `chords`'.
            record["cuts"] += [{"riff": c.get("riff") or ("chords" if "chord" in c else "line"),
                                **{k: v for k, v in c.items() if k != "riff"}}
                               for c in old.get("cuts", [])
                               if (c.get("riff") or ("chords" if "chord" in c else "line")) == name]
            continue
        audio, cuts = built[name]
        gain = TARGET_LUFS - meter.integrated_loudness(audio)
        audio = audio * 10 ** (gain / 20)
        if np.abs(audio).max() >= 10 ** (-1 / 20):
            die(f"{name} would peak above -1 dBFS at {TARGET_LUFS} LUFS")
        path = out / f"{name}.flac"
        sf.write(str(path), audio.astype(np.float32), RATE, subtype="PCM_24")
        record["cuts"] += cuts
        record["riffs"][name] = {"file": path.name, "sha256": _sha(path), "what": spec["what"],
                                 "seconds": round(len(audio) / RATE, 3),
                                 "gain_db": round(float(gain), 2), **meta}
    index.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record["riffs"], indent=1))


if __name__ == "__main__":
    guarded(main)
