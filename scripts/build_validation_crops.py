#!/usr/bin/env python3
"""Build private, audition-ready DI/reference/mix/backing crops from one declared part.

This implements docs/validation-datasets.md without shifting tracks: load every
session stem WAV through analysis.io (48 kHz), average stereo channels to mono,
and align first samples. The part's resampled DI length defines the session:
shorter stems are zero-padded and longer stems truncated. "Tracks" means the
catalog's session stem WAVs, not MIDI or video camera audio. Every guitar DI
listed in the session's parts is excluded from the unity-gain mix; a bass DI
remains. Backing is that mix minus the selected part's reference and alternate
amp tracks. These stereo/length/stem-file interpretations are explicit because
the declaration does not say how to treat partial or non-stem media files.

The excerpt is the earliest maximum-integrated-loudness 10-second window of
the mono reference on a 0.5-second grid. All four outputs use that same span.
No normalization, limiter, or gain change is applied. Float32 WAV preserves
out-of-range raw mix samples without integer clipping. The output is private;
this tool deliberately refuses held-out parts until a separately committed
prospective test declares their use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "validation-datasets.json"
sys.path[:0] = [str(ROOT), str(pathlib.Path(__file__).resolve().parent)]

from _cli import guarded
from score_listening import _require_private_out_dir


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(catalog: dict, source: str, song: str, part_name: str) -> tuple[dict, dict]:
    if catalog.get("schema") != "validation-datasets-2":
        raise ValueError("unsupported validation dataset schema")
    sessions = [item for item in catalog["sessions"]
                if item.get("source") == source and item.get("song") == song]
    if len(sessions) != 1:
        raise ValueError("select exactly one declared source/song session")
    session = sessions[0]
    if session.get("split") != "development":
        raise ValueError("held-out material needs a separately committed test declaration; "
                         "this development crop builder will not open it")
    parts = [item for item in session["parts"] if item.get("part") == part_name]
    if len(parts) != 1 or not parts[0].get("usable"):
        raise ValueError("select one usable declared part")
    return session, parts[0]


def _source_path(root: pathlib.Path, session_path: str, name: str) -> pathlib.Path:
    relative = pathlib.Path(session_path) / name
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("dataset paths must be relative and stay under the dataset root")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("dataset symlink escapes its root")
    return path


def _fit(samples, length: int):
    import numpy as np

    result = np.zeros(length, dtype=np.float32)
    count = min(length, len(samples))
    result[:count] = samples[:count]
    return result


def _window(reference, rate: int) -> tuple[int, int, float]:
    from analysis import io

    frames = 10 * rate
    step = rate // 2
    if len(reference) < frames:
        raise ValueError("the part's DI is shorter than the required 10-second excerpt")
    best = None
    for start in range(0, len(reference) - frames + 1, step):
        loudness = io.loudness_lufs(io.from_samples(reference[start:start + frames], rate))
        if loudness is not None and (best is None or loudness > best[2]):
            best = (start, start + frames, loudness)
    if best is None:
        raise ValueError("reference has no measurable 10-second excerpt")
    return best


def build(catalog_path: pathlib.Path, data_root: pathlib.Path, source: str,
          song: str, part_name: str, out_dir: pathlib.Path) -> dict:
    """Verify a trusted catalog and atomically publish four private WAVs and hashes.

    The CLI always passes the committed catalog. A catalog argument here permits
    synthetic unit fixtures; it is not a way to authorize a held-out use.
    """
    import numpy as np
    import soundfile as sf
    from analysis import io

    catalog_path = catalog_path.expanduser().resolve()
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    session, part = _entry(catalog, source, song, part_name)
    data_root = data_root.expanduser().resolve()
    out_dir = _require_private_out_dir(out_dir)
    if out_dir.exists() or out_dir.is_symlink():
        raise ValueError("choose a new private output directory; crops are immutable")

    files = session["files"]
    guitar_dis = {item["di"] for item in session["parts"]}
    amp_tracks = {part["reference"], *part.get("alternate", [])}
    for name in (part["di"], *amp_tracks):
        if name not in files or pathlib.Path(name).suffix.lower() != ".wav":
            raise ValueError(f"the selected part names an undeclared WAV: {name}")
    if part["di"] in amp_tracks:
        raise ValueError("the selected DI cannot also be an amp track")
    stem_names = sorted(name for name in files if pathlib.Path(name).suffix.lower() == ".wav")
    if not amp_tracks <= set(stem_names) or part["reference"] in guitar_dis:
        raise ValueError("the declared guitar track roles overlap")

    checked: dict[str, str] = {}

    def load(name: str):
        path = _source_path(data_root, session["path"], name)
        audio = io.load(path)
        if audio.sha256 != files[name]:
            raise ValueError(f"dataset source hash differs from the committed catalog: {name}")
        checked[name] = audio.sha256
        return audio.mono().astype(np.float32)

    di = load(part["di"])
    length = len(di)
    reference = _fit(load(part["reference"]), length)
    start, end, lufs = _window(reference, io.SAMPLE_RATE)
    mix = np.zeros(end - start, dtype=np.float64)
    own_amps = np.zeros_like(mix)
    included = []
    for name in stem_names:
        if name in guitar_dis:
            continue
        samples = reference if name == part["reference"] else _fit(load(name), length)
        crop = samples[start:end].astype(np.float64)
        mix += crop
        if name in amp_tracks:
            own_amps += crop
        included.append(name)
    backing = mix - own_amps
    outputs = {"di": di[start:end], "reference": reference[start:end],
               "mix": mix.astype(np.float32), "backing": backing.astype(np.float32)}

    record = {
        "schema": "validation-crops-1",
        "catalog": {"path": str(catalog_path), "sha256": _sha256(catalog_path)},
        "source": source, "song": song, "part": part_name, "split": session["split"],
        "sample_rate": io.SAMPLE_RATE, "channels": 1,
        "session_frames": length, "excerpt_start_frame": start,
        "excerpt_end_frame": end, "excerpt_start_s": start / io.SAMPLE_RATE,
        "excerpt_duration_s": 10.0, "reference_lufs": lufs,
        "policy": "mono channel mean; first-sample alignment; session length from DI; "
                  "short stems zero-padded and long stems cut; unity WAV-stem sum; "
                  "no normalization or limiting; float32 WAV",
        "included_mix_tracks": included,
        "excluded_guitar_dis": sorted(guitar_dis),
        "removed_own_amp_tracks": sorted(amp_tracks),
        "verified_source_sha256": checked,
        "outputs": {},
    }
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="validation-crops-", dir=out_dir.parent) as staged:
        stage = pathlib.Path(staged)
        for role, samples in outputs.items():
            path = stage / f"{role}.wav"
            sf.write(path, samples, io.SAMPLE_RATE, subtype="FLOAT")
            record["outputs"][role] = {"path": str(out_dir / path.name),
                                       "sha256": _sha256(path), "frames": len(samples)}
        (stage / "record.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n",
                                           encoding="utf-8")
        os.rename(stage, out_dir)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=pathlib.Path,
                        help="dataset root; default is the catalog's private root")
    parser.add_argument("--source", required=True)
    parser.add_argument("--song", required=True)
    parser.add_argument("--part", required=True)
    parser.add_argument("--out-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    data_root = args.data_root or pathlib.Path(catalog["root"]).expanduser()
    record = build(CATALOG, data_root, args.source, args.song, args.part, args.out_dir)
    print(f"wrote four private 10-second WAV crops and hashes to {args.out_dir}")
    print(f"reference excerpt: {record['excerpt_start_s']:.1f} s, "
          f"{record['reference_lufs']:.2f} LUFS; no gain or time shift applied")


if __name__ == "__main__":
    guarded(main)
