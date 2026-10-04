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
the declaration does not say how to treat partial or non-stem media files. A
second-set session declares its mix (`mix_tracks`) and is mixed from exactly
those; when it lists `vocal_tracks`, the mix and the backing are also cut
without them (`mix_instrumental`, `backing_instrumental`).

The excerpt is a 10-second window on a 0.5-second grid; every output uses that same
span. Rule `di-activity` (crop rule 2, docs/validation-datasets.md) takes the window
where the part's DI plays in the most frames (2048-sample frames, hop 1024, within
40 dB of the DI's loudest), breaking ties within 0.02 by the reference's ungated
mean square, then by the earliest. Rule `loudness` (the first rule) takes the earliest
maximum-integrated-loudness window of the mono reference; integrated loudness is
gated, so it often picked a window the part barely plays in.
No normalization, limiter, or gain change is applied. Float32 WAV preserves
out-of-range raw mix samples without integer clipping. The output is private.
Held-out parts require --declaration pointing to an unchanged, committed
docs/*.md file containing one unambiguous fenced JSON authorization block:

    ```json
    {"schema":"held-out-listening-test-v1","test_id":"example-id",
     "parts":["source/song/part"]}
    ```

The declaration must also describe the command, measurement, and interpretation
of outcomes required by docs/validation-datasets.md. This tool checks the
machine-readable authorization, not the quality of that prose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
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
    if catalog.get("schema") not in ("validation-datasets-2", "validation-datasets-3"):
        raise ValueError("unsupported validation dataset schema")
    sessions = [item for item in catalog["sessions"]
                if item.get("source") == source and item.get("song") == song]
    if len(sessions) != 1:
        raise ValueError("select exactly one declared source/song session")
    session = sessions[0]
    if session.get("split") not in ("development", "held_out"):
        raise ValueError("unknown validation dataset split")
    parts = [item for item in session["parts"] if item.get("part") == part_name]
    if len(parts) != 1 or not parts[0].get("usable"):
        raise ValueError("select one usable declared part")
    return session, parts[0]


def _git(repo: pathlib.Path, *args: str) -> bytes:
    done = subprocess.run(("git", "-C", str(repo), *args), capture_output=True)
    if done.returncode:
        raise ValueError("held-out declaration must be committed and tracked at HEAD")
    return done.stdout


def _declaration(path: pathlib.Path, part_id: str, repo: pathlib.Path) -> dict:
    """Bind an exact part to the unchanged HEAD version of a docs declaration."""
    repo = repo.resolve()
    path = path.expanduser()
    if not path.is_absolute():
        path = repo / path
    absolute = path.absolute()
    relative = absolute.relative_to(repo) if absolute.is_relative_to(repo) else None
    if (relative is None or len(relative.parts) != 2 or relative.parts[0] != "docs"
            or relative.suffix != ".md" or path.is_symlink() or not path.is_file()
            or path.resolve() != repo / relative):
        raise ValueError("held-out declaration must be a regular docs/*.md file in this repo")
    name = relative.as_posix()
    tree_entry = _git(repo, "ls-tree", "HEAD", "--", name)
    if not tree_entry.startswith((b"100644 blob ", b"100755 blob ")):
        raise ValueError("held-out declaration must be a committed regular file")
    committed = _git(repo, "show", f"HEAD:{name}")
    current = path.read_bytes()
    changed = subprocess.run(("git", "-C", str(repo), "diff", "--quiet", "HEAD",
                              "--", name), capture_output=True)
    if current != committed or changed.returncode != 0:
        raise ValueError("held-out declaration differs from its committed HEAD version")
    blocks = re.findall(r"^```json[ \t]*\r?\n(.*?)^```[ \t]*$",
                        current.decode("utf-8"), flags=re.MULTILINE | re.DOTALL)
    marked = [block for block in blocks if "held-out-listening-test-v1" in block]
    if len(marked) != 1:
        raise ValueError("declaration needs exactly one held-out-listening-test-v1 JSON block")
    try:
        payload = json.loads(marked[0])
    except json.JSONDecodeError as error:
        raise ValueError("held-out declaration JSON is invalid") from error
    if (not isinstance(payload, dict)
            or set(payload) != {"schema", "test_id", "parts"}
            or payload["schema"] != "held-out-listening-test-v1"
            or not isinstance(payload["test_id"], str) or not payload["test_id"].strip()
            or not isinstance(payload["parts"], list) or not payload["parts"]
            or any(not isinstance(part, str) or not part for part in payload["parts"])
            or len(payload["parts"]) != len(set(payload["parts"]))):
        raise ValueError("held-out declaration must name one test_id and unique part IDs")
    if part_id not in payload["parts"]:
        raise ValueError(f"held-out declaration does not name exact part {part_id!r}")
    return {"path": name,
            "commit": _git(repo, "log", "-1", "--format=%H", "HEAD", "--", name).decode().strip(),
            "head_commit": _git(repo, "rev-parse", "HEAD").decode().strip(),
            "sha256": hashlib.sha256(current).hexdigest(), "test_id": payload["test_id"]}


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


DI_ACTIVITY_TIE = 0.02


def _window_by_di(di, reference, rate: int) -> tuple[int, int, float, float]:
    """(start, end, reference LUFS, DI activity) of crop rule 2's window."""
    import numpy as np

    from analysis import io

    frames, step = 10 * rate, rate // 2
    if len(di) < frames:
        raise ValueError("the part's DI is shorter than the required 10-second excerpt")
    db = io.frame_rms_db(di, 2048, 1024)
    playing = db >= db.max() - 40.0
    starts = list(range(0, len(di) - frames + 1, step))
    share = {s: float(np.mean(playing[s // 1024:(s + frames - 2048) // 1024 + 1]))
             for s in starts}
    top = max(share.values())
    if top == 0:
        raise ValueError("the part's DI never plays")
    tied = [s for s in starts if share[s] >= top - DI_ACTIVITY_TIE]
    start = max(tied, key=lambda s: (float(np.mean(np.square(reference[s:s + frames],
                                                             dtype=np.float64))), -s))
    lufs = io.loudness_lufs(io.from_samples(reference[start:start + frames], rate))
    if lufs is None:
        raise ValueError("reference has no measurable 10-second excerpt")
    return start, start + frames, lufs, share[start]


def build(catalog_path: pathlib.Path, data_root: pathlib.Path, source: str,
          song: str, part_name: str, out_dir: pathlib.Path,
          declaration_path: pathlib.Path | None = None,
          *, repo_root: pathlib.Path = ROOT, rule: str = "loudness") -> dict:
    """Verify a trusted catalog and atomically publish private WAV crops and hashes.

    The CLI accepts only the unchanged committed catalog. A different catalog
    argument here permits synthetic unit fixtures, not held-out authorization.
    """
    import numpy as np
    import soundfile as sf
    from analysis import io

    catalog_path = catalog_path.expanduser().resolve()
    repo_root = repo_root.resolve()
    catalog_name = "docs/validation-datasets.json"
    catalog_bytes = catalog_path.read_bytes()
    if catalog_path == (repo_root / catalog_name).resolve():
        committed = _git(repo_root, "show", f"HEAD:{catalog_name}")
        changed = subprocess.run(("git", "-C", str(repo_root), "diff", "--quiet",
                                  "HEAD", "--", catalog_name), capture_output=True)
        if catalog_bytes != committed or changed.returncode != 0:
            raise ValueError("validation catalog differs from its committed HEAD version")
    catalog = json.loads(catalog_bytes.decode("utf-8"))
    session, part = _entry(catalog, source, song, part_name)
    declaration = None
    if session["split"] == "held_out":
        if declaration_path is None:
            raise ValueError("held-out material needs --declaration in a separately committed test")
        declaration = _declaration(declaration_path, f"{source}/{song}/{part_name}",
                                   repo_root)
    elif declaration_path is not None:
        raise ValueError("--declaration applies only to held-out material")
    data_root = data_root.expanduser().resolve()
    out_dir = _require_private_out_dir(out_dir)
    if out_dir.exists() or out_dir.is_symlink():
        raise ValueError("choose a new private output directory; crops are immutable")

    files = session["files"]
    guitar_dis = {item["di"] for item in session["parts"] if item.get("di")}
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
    if rule == "di-activity":
        start, end, lufs, activity = _window_by_di(di, reference, io.SAMPLE_RATE)
    elif rule == "loudness":
        start, end, lufs = _window(reference, io.SAMPLE_RATE)
        activity = None
    else:
        raise ValueError(f"unknown excerpt rule {rule!r}")
    # A session that declares its mix tracks (the second set) is mixed from exactly
    # those, one amp track per guitar; the first set's sessions sum every stem but
    # the guitar DIs, as validation-datasets.md declared for them.
    declared_mix = session.get("mix_tracks")
    if declared_mix is not None:
        if not set(declared_mix) <= set(stem_names) or set(declared_mix) & guitar_dis:
            raise ValueError("the declared mix names an undeclared WAV or a guitar DI")
        if part["reference"] not in declared_mix:
            raise ValueError("the declared mix leaves out the selected part's reference")
    vocals = set(session.get("vocal_tracks") or ())
    mix = np.zeros(end - start, dtype=np.float64)
    own_amps = np.zeros_like(mix)
    singing = np.zeros_like(mix)
    included = []
    for name in (declared_mix if declared_mix is not None else stem_names):
        if name in guitar_dis:
            continue
        samples = reference if name == part["reference"] else _fit(load(name), length)
        crop = samples[start:end].astype(np.float64)
        mix += crop
        if name in amp_tracks:
            own_amps += crop
        if name in vocals:
            singing += crop
        included.append(name)
    backing = mix - own_amps
    outputs = {"di": di[start:end], "reference": reference[start:end],
               "mix": mix.astype(np.float32), "backing": backing.astype(np.float32)}
    if vocals:
        # The mix and backing with the singing left out, for a listener who has to
        # hear the guitar through them; an audition plays the two together.
        outputs["mix_instrumental"] = (mix - singing).astype(np.float32)
        outputs["backing_instrumental"] = (backing - singing).astype(np.float32)

    record = {
        "schema": "validation-crops-2" if rule == "di-activity" else "validation-crops-1",
        "excerpt_rule": rule, "di_activity": activity,
        "catalog": {"path": str(catalog_path), "sha256": _sha256(catalog_path)},
        "source": source, "song": song, "part": part_name, "split": session["split"],
        "sample_rate": io.SAMPLE_RATE, "channels": 1,
        "session_frames": length, "excerpt_start_frame": start,
        "excerpt_end_frame": end, "excerpt_start_s": start / io.SAMPLE_RATE,
        "excerpt_duration_s": 10.0, "reference_lufs": lufs,
        "policy": "mono channel mean; first-sample alignment; session length from DI; "
                  "short stems zero-padded and long stems cut; unity WAV-stem sum; "
                  "no normalization or limiting; float32 WAV",
        "mix_rule": ("declared mix_tracks" if declared_mix is not None
                     else "every session WAV except the guitar DIs"),
        "included_mix_tracks": included,
        "vocal_tracks": sorted(vocals & set(included)),
        "excluded_guitar_dis": sorted(guitar_dis),
        "removed_own_amp_tracks": sorted(amp_tracks),
        "verified_source_sha256": checked,
        "outputs": {},
    }
    if declaration is not None:
        record["declaration"] = declaration
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
    parser.add_argument("--declaration", type=pathlib.Path,
                        help="unchanged committed docs/*.md declaring this held-out test and part")
    parser.add_argument("--out-dir", required=True, type=pathlib.Path)
    parser.add_argument("--rule", choices=("di-activity", "loudness"), default="di-activity",
                        help="crop rule 2 (where the DI plays most; the default) or the "
                             "first rule (loudest by gated loudness)")
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    data_root = args.data_root or pathlib.Path(catalog["root"]).expanduser()
    record = build(CATALOG, data_root, args.source, args.song, args.part, args.out_dir,
                   args.declaration, rule=args.rule)
    print(f"wrote private 10-second WAV crops and hashes to {args.out_dir}")
    print(f"reference excerpt: {record['excerpt_start_s']:.1f} s, "
          f"{record['reference_lufs']:.2f} LUFS; no gain or time shift applied")


if __name__ == "__main__":
    guarded(main)
