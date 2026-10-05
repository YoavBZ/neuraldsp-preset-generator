#!/usr/bin/env python3
"""Rebuild docs/validation-datasets.json from the recordings themselves.

    python research/validation_datasets.py \\
      --root ~/ndsp-presets/references/datasets --json docs/validation-datasets.json

Hashes every file, measures how well each guitar part's DI and amp track are the
same take kept in step (`pairing`, `windowed_pairing`), and draws the declared
development / held-out splits. The second set's sessions, parts and amp tracks
come from docs/validation-sources-2.json. `docs/validation-datasets.md` states the rules;
this is them, so the committed numbers can be reproduced from the audio.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import re
import sys

FRAME_S = 0.01          # envelope frame: 10 ms of mean absolute amplitude
WHOLE_LAG_S = 0.02      # the whole-length test looks within ±20 ms
WINDOW_S, HOP_S = 20.0, 10.0
WINDOW_LAG_S = 0.2      # each window's own best lag, within ±200 ms
ACTIVE_DB = 30.0        # a window counts when within 30 dB of the loudest
PAIRED_MIN = 0.8        # whole-length correlation a usable part needs
IN_STEP_FRACTION = 0.8  # share of active windows whose best lag is within ±20 ms
WINDOW_MEDIAN_MIN = 0.6

SPLIT_SEED = 20260927
TELEFUNKEN_SONGS = ["57 Chevy", "Bourbon", "Collide With Me"]
CAMBRIDGE_SONGS = ["Heather Jane", "That's How I Got To Memphis"]
GUITAR_TECHS_EXCERPTS = [f"{i:02d}" for i in range(1, 13)]

TELEFUNKEN_DIRS = {"57 Chevy": "Rebecca Haviland - 57 Chevy",
                   "Bourbon": "Rebecca Haviland - Burbon",
                   "Collide With Me": "Rebecaa Haviland - Collide With Me"}
# The second set: sessions found and pair-tested after the first split was used,
# listed in docs/validation-sources-2.json and split by band (validation-datasets.md).
SET2_SOURCES = pathlib.Path(__file__).resolve().parents[1] / "docs" / "validation-sources-2.json"
SET2_SPLIT_SEED = 20261001
SET2_HELD_OUT_GROUPS = {"cambridge": 5, "telefunken": 3}
# The order a part's amp tracks are tried in for its reference (set2_session): the
# M80 for Telefunken, as in the first set; on Cambridge the first microphone, the
# close one, or the one named as the amp.
AMP_PREFERENCE = (r"M ?80(?!\d)", r"Mic ?1(?!\d)", r"Close", r"Amp ?1(?!\d)",
                  r"Amp(?! ?\d)", r"^(?:\d+_)?ElecGtr\d+(?:DT)?$", r"TF ?11(?!\d)",
                  r"TF ?51(?!\d)", r"TF ?39(?!\d)", r"Mic ?2(?!\d)", r"Far",
                  r"Mic ?3(?!\d)", r"Amp ?2(?!\d)")
VOCAL_TRACK = re.compile(r"vox|vocal", re.I)
# Tracks no second-set mix holds, by name: rendered mixes, click tracks and
# electric guitar DIs, a part's or not. An amp simulator or modeller track
# (SIMULATED_AMP; validation-sources-2.json lists them per part) is left out only
# when it is the same take as its part's DI: otherwise it is another guitar.
RENDERED_MIX = re.compile(r"master|mixdown|(?:^|[ _-])mix(?:[ _-]|$)", re.I)
CLICK_TRACK = re.compile(r"click|metronome", re.I)
SIMULATED_AMP = re.compile(r"sim|helix|kemper|axe-?fx|quad ?cortex", re.I)
GUITAR_DI = re.compile(r"^(?!.*acoustic)(?=.*(?:gtr|guitar)).*(?:DI(?![a-z])|TDP|direct)",
                       re.I)
# A part named for the keyboard player ("Keys GTR") may be a keyboard through a
# guitar amp; the names do not say, so it is not used.
KEYBOARD_PART = re.compile(r"\bkeys?\b", re.I)
CAMBRIDGE_DIRS = {"Heather Jane": "ChrisColtraine_HeatherJane_Full",
                  "That's How I Got To Memphis":
                      "ChrisColtraine_ThatsHowIGotToMemphis_Full"}


def draw_split():
    """The held-out draw, exactly as declared: the drawn items are held out."""
    rng = random.Random(SPLIT_SEED)
    return {"telefunken": rng.choice(TELEFUNKEN_SONGS),
            "cambridge": rng.choice(CAMBRIDGE_SONGS),
            "guitar_techs": sorted(rng.sample(GUITAR_TECHS_EXCERPTS, 4))}


def load_mono(path):
    import numpy as np
    import soundfile as sf

    samples, rate = sf.read(str(path), always_2d=True, dtype="float64")
    return samples.mean(axis=1), int(rate)


def envelope(samples, rate):
    import numpy as np

    hop = int(round(FRAME_S * rate))
    usable = len(samples) // hop * hop
    return np.abs(samples[:usable]).reshape(-1, hop).mean(axis=1)


def _zscore(values):
    return (values - values.mean()) / (values.std() + 1e-12)


def _best_lag(reference, di, max_frames):
    """(correlation, lag in frames) at the best lag; positive: reference later."""
    import numpy as np
    from scipy import signal

    a, b = _zscore(reference), _zscore(di)
    full = signal.correlate(a, b, mode="full") / len(b)
    lags = np.arange(-len(b) + 1, len(a))
    window = np.abs(lags) <= max_frames
    index = int(np.argmax(full[window]))
    return float(full[window][index]), int(lags[window][index])


def pairing(reference_path, di_path):
    """Whole-length envelope correlation of the amp track against its DI.

    Mono, 10 ms mean-absolute frames, both truncated to the shorter file and
    z-scored, the peak within ±20 ms. `lag_ms` is positive when the amp track is
    later than the DI. Whole-length agreement is lifted by shared silences and a
    song's loudness arc, which is why `windowed_pairing` is asked as well.
    """
    reference, rate = load_mono(reference_path)
    di, di_rate = load_mono(di_path)
    if rate != di_rate:
        raise ValueError(f"{reference_path} and {di_path} differ in sample rate")
    a, b = envelope(reference, rate), envelope(di, rate)
    size = min(len(a), len(b))
    correlation, lag = _best_lag(a[:size], b[:size],
                                 int(round(WHOLE_LAG_S / FRAME_S)))
    return round(correlation, 3), int(round(lag * FRAME_S * 1000))


def windowed_pairing(reference_path, di_path):
    """Whether the take stays in step: 20 s windows every 10 s.

    Windows whose reference envelope is within 30 dB of the loudest window count.
    Each gets its own best lag within ±200 ms. Returns the share of counted
    windows whose best lag is within ±20 ms, and the median of their
    correlations at that best lag.
    """
    import numpy as np

    reference, rate = load_mono(reference_path)
    di, _ = load_mono(di_path)
    a, b = envelope(reference, rate), envelope(di, rate)
    size = min(len(a), len(b))
    a, b = a[:size], b[:size]
    width = int(round(WINDOW_S / FRAME_S))
    hop = int(round(HOP_S / FRAME_S))
    starts = list(range(0, max(size - width, 0) + 1, hop)) or [0]
    levels = np.array([a[s:s + width].mean() for s in starts])
    loudest = levels.max()
    lags, correlations = [], []
    for start, level in zip(starts, levels):
        if level <= 0 or 20 * np.log10(level / loudest) < -ACTIVE_DB:
            continue
        correlation, lag = _best_lag(a[start:start + width], b[start:start + width],
                                     int(round(WINDOW_LAG_S / FRAME_S)))
        lags.append(lag * FRAME_S * 1000)
        correlations.append(correlation)
    in_step = [abs(lag) <= WHOLE_LAG_S * 1000 for lag in lags]
    return {"windows": len(lags),
            "in_step_fraction": round(sum(in_step) / len(lags), 3) if lags else None,
            "median_correlation": (round(float(np.median(correlations)), 3)
                                   if correlations else None)}


def _usable(part):
    window = part.get("windowed") or {}
    return (part["di"] is not None and part["pairing_corr"] is not None
            and part["pairing_corr"] >= PAIRED_MIN
            and (window.get("in_step_fraction") or 0) >= IN_STEP_FRACTION
            and (window.get("median_correlation") or 0) >= WINDOW_MEDIAN_MIN)


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _part(session_dir, name, reference, di, alternate=()):
    part = {"part": name, "reference": reference, "alternate": list(alternate),
            "di": di, "pairing_corr": None, "lag_ms": None, "windowed": None}
    if di is not None:
        part["pairing_corr"], part["lag_ms"] = pairing(session_dir / reference,
                                                       session_dir / di)
        part["windowed"] = windowed_pairing(session_dir / reference, session_dir / di)
    part["usable"] = _usable(part)
    return part


def draw_set2_split(groups_by_source):
    """The second set's held-out draw: whole bands, per source, as declared."""
    rng = random.Random(SET2_SPLIT_SEED)
    return {source: sorted(rng.sample(sorted(groups_by_source[source]),
                                      SET2_HELD_OUT_GROUPS[source]))
            for source in ("cambridge", "telefunken")}


def amp_rank(name):
    stem = pathlib.Path(name).stem
    for rank, pattern in enumerate(AMP_PREFERENCE):
        if re.search(pattern, stem, re.I):
            return rank
    return len(AMP_PREFERENCE)


def set2_session(root, entry, split):
    """One second-set session: its files, parts, mix tracks and vocal tracks.

    A part's reference is its first amp track by `AMP_PREFERENCE` that passes
    both pairing tests, or its first if none does (the part is then unusable);
    the others are alternates. A part is also unusable when it is named for the
    keyboard player, or when one of its amp tracks is another part's too, since
    that track then carries two performances (`excluded` says which). The mix is
    every WAV except electric guitar DIs, every part's alternates and same-take
    simulator tracks, click tracks and rendered mixes, so each part's guitar is
    heard once, through its reference; `vocal_tracks` lets a backing leave the
    singing out.
    """
    directory = root / entry["path"]
    if "/" in entry["song"] or any("/" in part["part"] for part in entry["parts"]):
        raise ValueError(f"{entry['path']}: a song or part name holds '/', which part "
                         "IDs (source/song/part) cannot")
    wavs = sorted(p.relative_to(directory).as_posix() for p in directory.rglob("*.wav")
                  if not p.name.startswith("._"))
    by_name = {pathlib.PurePosixPath(w).name: w for w in wavs}
    if len(by_name) != len(wavs):
        raise ValueError(f"{entry['path']}: two WAVs share a file name")
    owners = {}
    for declared in entry["parts"]:
        for amp in declared["amps"]:
            owners.setdefault(amp, []).append(declared["part"])
    parts, left_out = [], set()
    for declared in entry["parts"]:
        amps = sorted((by_name[a] for a in declared["amps"]), key=amp_rank)
        di = by_name[declared["di"]]
        tried = []
        for reference in amps:
            tried.append(_part(directory, declared["part"], reference, di,
                               [a for a in amps if a != reference]))
            if tried[-1]["usable"]:
                break
        part = tried[-1] if tried[-1]["usable"] else tried[0]
        shared = sorted({other for amp in declared["amps"] for other in owners[amp]}
                        - {declared["part"]})
        if KEYBOARD_PART.search(declared["part"]):
            part.update(usable=False, excluded="named for the keyboard player")
        elif shared:
            part.update(usable=False,
                        excluded=f"shares an amp track with {', '.join(shared)}")
        part["simulated"] = [by_name[t] for t in declared.get("simulated", [])
                             if (pairing(directory / by_name[t], directory / di)[0]
                                 or 0) >= PAIRED_MIN]
        parts.append(part)
        left_out.update({di, *part["alternate"], *part["simulated"]})
    listed = {by_name[t] for declared in entry["parts"]
              for t in (*declared["amps"], *declared.get("simulated", []))}
    unlisted = [w for w in wavs if w not in listed
                and SIMULATED_AMP.search(pathlib.PurePosixPath(w).stem)]
    if unlisted:
        raise ValueError(f"{entry['path']}: {', '.join(unlisted)} looks like an amp "
                         "simulator; list it under its part's simulated tracks")
    mix = [w for w in wavs if w not in left_out
           and not any(rule.search(pathlib.PurePosixPath(w).stem) for rule in
                       (RENDERED_MIX, CLICK_TRACK, GUITAR_DI))]
    return {"source": entry["source"], "song": entry["song"], "artist": entry["artist"],
            "group": entry["group"], "set": 2, "path": entry["path"],
            "url": entry["url"], "archive_sha256": entry["archive_sha256"],
            "split": "held_out" if entry["group"] in split[entry["source"]] else "development",
            "files": {w: _sha(directory / w) for w in wavs},
            "parts": parts, "mix_tracks": mix,
            "vocal_tracks": [w for w in mix
                             if VOCAL_TRACK.search(pathlib.PurePosixPath(w).stem)]}


def build(root: pathlib.Path):
    split = draw_split()
    sessions = []
    for song, folder in TELEFUNKEN_DIRS.items():
        directory = root / "telefunken" / folder
        files = sorted(p.name for p in directory.glob("*.wav"))
        parts = []
        for guitar in ("GTR 1", "GTR 2"):
            di = next(f for f in files if f.startswith(guitar) and "DI" in f)
            amps = sorted(f for f in files if f.startswith(guitar) and "Amp" in f)
            m80 = next(f for f in amps if "M 80" in f)
            parts.append(_part(directory, guitar, m80, di,
                               [f for f in amps if f != m80]))
        sessions.append({"source": "telefunken", "song": song,
                         "path": f"telefunken/{folder}",
                         "split": "held_out" if song == split["telefunken"]
                         else "development",
                         "files": {f: _sha(directory / f) for f in files},
                         "parts": parts})
    for song, folder in CAMBRIDGE_DIRS.items():
        directory = root / "cambridge" / folder
        files = sorted(p.name for p in directory.glob("*.wav"))
        stems = {pathlib.Path(f).stem.split("_", 1)[1]: f for f in files}
        parts = [_part(directory, name, stems[name], stems.get(name + "DI"))
                 for name in sorted(stems)
                 if name.startswith("ElecGtr") and not name.endswith("DI")]
        sessions.append({"source": "cambridge", "song": song,
                         "path": f"cambridge/{folder}",
                         "split": "held_out" if song == split["cambridge"]
                         else "development",
                         "files": {f: _sha(directory / f) for f in files},
                         "parts": parts})
    directory = root / "guitar-techs" / "P3_music"
    for number in GUITAR_TECHS_EXCERPTS:
        files = [f"audio/directinput/directinput_{number}.wav",
                 f"audio/micamp/micamp_{number}.wav",
                 f"midi/midi_{number}.mid",
                 f"video/ego/ego_{number}.mp3", f"video/exo/exo_{number}.mp3"]
        sessions.append({"source": "guitar-techs", "song": f"P3_music excerpt {number}",
                         "path": "guitar-techs/P3_music",
                         "split": ("held_out" if number in split["guitar_techs"]
                                   else "development"),
                         "files": {f: _sha(directory / f) for f in files},
                         "parts": [_part(directory, number,
                                         f"audio/micamp/micamp_{number}.wav",
                                         f"audio/directinput/directinput_{number}.wav")]})
    manifest = json.loads(SET2_SOURCES.read_text(encoding="utf-8"))
    groups = {}
    for entry in manifest["sessions"]:
        groups.setdefault(entry["source"], set()).add(entry["group"])
    split2 = draw_set2_split(groups)
    sessions += [set2_session(root, entry, split2) for entry in manifest["sessions"]]
    return {
        "schema": "validation-datasets-3",
        "root": "~/ndsp-presets/references/datasets",
        "split_seed": SPLIT_SEED,
        "split_draw": split,
        "set2_split_seed": SET2_SPLIT_SEED,
        "set2_split_draw": split2,
        "rules": {"paired_min": PAIRED_MIN, "in_step_fraction": IN_STEP_FRACTION,
                  "window_median_min": WINDOW_MEDIAN_MIN,
                  "lag_sign": "positive when the amp track is later than the DI"},
        "sessions": sessions,
        # Each use of a held-out session by a declared test: the declaring file,
        # the commit it ran at and its dates. main() keeps what is already there.
        "held_out_uses": [],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=pathlib.Path, required=True)
    ap.add_argument("--json", type=pathlib.Path, required=True)
    args = ap.parse_args()
    document = build(args.root.expanduser())
    # The ledger of held-out uses is a record, not a measurement: a rebuild
    # keeps every entry already written.
    if args.json.exists():
        document["held_out_uses"] = json.loads(
            args.json.read_text(encoding="utf-8")).get("held_out_uses", [])
    args.json.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    for session in document["sessions"]:
        for part in session["parts"]:
            window = part["windowed"] or {}
            print(f"{session['split']:12} {session['song'][:28]:28} {part['part']:10} "
                  f"whole {part['pairing_corr']} lag {part['lag_ms']} | "
                  f"in step {window.get('in_step_fraction')} of "
                  f"{window.get('windows')} windows, median "
                  f"{window.get('median_correlation')} | "
                  f"{'usable' if part['usable'] else 'excluded'}")


if __name__ == "__main__":
    sys.exit(main())
