#!/usr/bin/env python3
"""Build private backed-audition metadata from one declared crop and two fresh renders.

The declaration's machine-readable manifest step supplies this command's argv.
This reads records and hashes their named files, not the audio samples. It does
not open an audition key or reveal a blind mapping. With --instrumental the
reference and the backing are the crop's vocal-free mix and backing, which a
second-set crop has when its session lists vocal tracks; the two are always
taken together, so the singing cannot tell the reference from A and B.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._cli import guarded
from scripts.score_listening import _require_private_out_dir


def _sha(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified(spec: dict, context: str) -> dict:
    if not isinstance(spec, dict) or not isinstance(spec.get("path"), str):
        raise ValueError(f"{context} lacks a recorded path")
    path = pathlib.Path(spec["path"])
    if (path.is_symlink() or not path.is_file() or _sha(path) != spec.get("sha256")):
        raise ValueError(f"{context} differs from its recorded hash")
    return {"path": str(path.resolve()), "sha256": spec["sha256"]}


def build(crop_record: pathlib.Path, first_render: pathlib.Path,
          second_render: pathlib.Path, out: pathlib.Path, *,
          master_lufs: float = -20, peak_ceiling_dbtp: float = -1,
          max_ab_lufs_delta: float = .5, gap_s: float = .5,
          hidden_repeats: int = 1, instrumental: bool = False) -> dict:
    crop_record = crop_record.expanduser().absolute()
    first_render = first_render.expanduser().absolute()
    second_render = second_render.expanduser().absolute()
    out = out.expanduser().absolute()
    _require_private_out_dir(out.parent)
    if out.exists() or out.is_symlink():
        raise ValueError("choose a new private manifest path")
    if crop_record.is_symlink() or not crop_record.is_file():
        raise ValueError("manifest needs a regular crop record")
    crop = json.loads(crop_record.read_text(encoding="utf-8"))
    if not isinstance(crop, dict):
        raise ValueError("manifest needs a declared held-out crop record")
    declaration = crop.get("declaration")
    outputs = crop.get("outputs")
    if (crop.get("schema") != "validation-crops-1" or crop.get("split") != "held_out"
            or not isinstance(declaration, dict) or not declaration.get("test_id")
            or not isinstance(outputs, dict)
            or not isinstance(crop.get("reference_lufs"), (int, float))
            or crop.get("excerpt_duration_s") != 10):
        raise ValueError("manifest needs a declared held-out crop record")
    mix_role, backing_role = (("mix_instrumental", "backing_instrumental")
                              if instrumental else ("mix", "backing"))
    if instrumental and not all(role in outputs for role in (mix_role, backing_role)):
        raise ValueError("--instrumental needs a crop cut without its vocal tracks")
    mix = _verified(outputs.get(mix_role), f"{mix_role} crop")
    backing = _verified(outputs.get(backing_role), f"{backing_role} crop")
    di = _verified(outputs.get("di"), "DI crop")
    alternatives = {}
    for role, record_path in (("first", first_render), ("second", second_render)):
        if record_path.is_symlink() or not record_path.is_file():
            raise ValueError(f"{role} needs a regular fresh-render record")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if (record.get("schema") != "listening-fresh-render-v1"
                or record.get("process_policy") != "fresh"
                or not isinstance(record.get("pack"), str)
                or not isinstance(record.get("amp_model"), str)):
            raise ValueError(f"{role} is not a fresh plugin render")
        audio = _verified(record.get("audio"), f"{role} audio")
        used_di = _verified(record.get("di"), f"{role} DI")
        if used_di != di:
            raise ValueError(f"{role} used another DI crop")
        alternatives[role] = {**audio, "start_s": 0, "pack": record["pack"],
                              "amp_model": record["amp_model"],
                              "render_record": str(record_path)}
    part_id = "/".join(str(crop.get(field, "")) for field in ("source", "song", "part"))
    slug = re.sub(r"[^A-Za-z0-9_-]", "_", part_id.replace("/", "-"))
    manifest = {
        "schema": "prospective-backed-listening-v1", "id": slug,
        "target_id": "unassigned", "purpose": "prospective",
        "validation_mode": "declared", "declared_test_id": declaration["test_id"],
        "validation_crop_record": str(crop_record),
        "reference": {**mix, "start_s": 0, "duration_s": 10, "regime": "mix"},
        "backing": {**backing, "start_s": 0, "gain_db": 0,
                    "guitar_removed": True},
        "alternatives": alternatives,
        "mix": {"guitar_target_lufs": crop["reference_lufs"],
                "master_target_lufs": master_lufs,
                "peak_ceiling_dbtp": peak_ceiling_dbtp,
                "max_ab_lufs_delta": max_ab_lufs_delta,
                "gap_s": gap_s, "cycles": 1},
        "reliability": {"hidden_repeats": hidden_repeats,
                        "catch_trial": False},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".manifest-",
                                     dir=out.parent, delete=False) as staged:
        staged_path = pathlib.Path(staged.name)
        json.dump(manifest, staged, indent=2, allow_nan=False)
        staged.write("\n")
    try:
        os.link(staged_path, out)  # Never overwrite another published manifest.
    finally:
        staged_path.unlink(missing_ok=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crop-record", required=True, type=pathlib.Path)
    parser.add_argument("--first-render", required=True, type=pathlib.Path)
    parser.add_argument("--second-render", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--master-lufs", type=float, default=-20)
    parser.add_argument("--peak-ceiling-dbtp", type=float, default=-1)
    parser.add_argument("--max-ab-lufs-delta", type=float, default=.5)
    parser.add_argument("--gap-s", type=float, default=.5)
    parser.add_argument("--hidden-repeats", type=int, default=1)
    parser.add_argument("--instrumental", action="store_true",
                        help="play the crop's vocal-free mix and backing")
    args = parser.parse_args()
    build(args.crop_record, args.first_render, args.second_render, args.out,
          master_lufs=args.master_lufs, peak_ceiling_dbtp=args.peak_ceiling_dbtp,
          max_ab_lufs_delta=args.max_ab_lufs_delta, gap_s=args.gap_s,
          hidden_repeats=args.hidden_repeats, instrumental=args.instrumental)


if __name__ == "__main__":
    guarded(main)
