"""Bind a closeness answer to an immutable backed audition.

    python scripts/log_backed_verdict.py --key runs/.../private-key.json \
      --closer A

Run only after the listener answers. No audio is rescored and the blind key is
not revealed on stdout. The separate private sidecar preserves the original
audition and the prediction frozen before listening. The audit can still read
historical preference answers, but this logger accepts only closeness.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(pathlib.Path(__file__).resolve().parent)]

from _cli import guarded
from build_rab_audition import _write_text
from score_listening import _require_private_out_dir


def _publish_verdict(path: pathlib.Path, content: str) -> None:
    """Publish once, atomically: a concurrent answer must never replace another."""
    with tempfile.TemporaryDirectory(prefix=".verdict-", dir=path.parent) as temporary:
        staged = pathlib.Path(temporary) / "verdict.json"
        _write_text(staged, content)
        try:
            os.link(staged, path)
        except FileExistsError as error:
            raise ValueError("verdict already exists; never overwrite a listener answer") from error


def main() -> None:
    from analysis.listening import attach_verdict, sha256

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", required=True, type=pathlib.Path)
    parser.add_argument("--closer", required=True,
                        choices=("A", "B", "indistinguishable"))
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    key_path = args.key.expanduser().resolve()
    _require_private_out_dir(key_path.parent)
    key = json.loads(key_path.read_text())
    if key.get("schema") != "prospective-backed-audition-v1":
        raise ValueError("this is not a prospective backed-audition key")
    if key.get("purpose") != "prospective":
        raise ValueError("workflow rehearsals cannot become listener evidence")
    for binding in (key["output"], key["manifest"]):
        path = pathlib.Path(binding["path"]).expanduser().resolve()
        if not path.is_file() or sha256(path) != binding["sha256"]:
            raise ValueError(f"audition input changed or disappeared: {path}")
    for role, source in key["source_paths"].items():
        path = pathlib.Path(source).expanduser().resolve()
        if not path.is_file() or sha256(path) != key["source_sha256"][role]:
            raise ValueError(f"{role} source changed or disappeared: {path}")
    output_path = key_path.parent / "verdict.json"
    if output_path.exists() or output_path.is_symlink():
        raise ValueError("verdict already exists; never overwrite a listener answer")
    verdict = {"closer": args.closer, "preferred": None}
    scored = attach_verdict(key["objective_record"], verdict)
    record = {"schema": "prospective-backed-verdict-v1",
              "audition_key": {"path": str(key_path), "sha256": sha256(key_path)},
              "heard_audio_sha256": key["output"]["sha256"],
              "verdict": verdict, "listener_notes": args.notes,
              "frozen_scored_record": scored}
    _publish_verdict(output_path, json.dumps(record, indent=2, allow_nan=False) + "\n")
    print(f"recorded closer={args.closer} in {output_path}")
    print("objective agreement is in the private verdict; no audio was rescored")


if __name__ == "__main__":
    guarded(main)
