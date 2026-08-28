#!/usr/bin/env python3
"""Record a blind A/B match audition without revealing the key first."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import add_data_dir_arg, die, guarded


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _answer(key, label: str) -> str:
    if label == "indistinguishable":
        return label
    source_role = (key.get("blind_key") or {}).get(label)
    result = ((key.get("match") or {}).get("roles") or {}).get(source_role)
    if result not in ("candidate", "template"):
        die(f"the blind key cannot resolve label {label!r} to candidate/template")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", required=True, type=pathlib.Path)
    parser.add_argument("--choice", required=True,
                        choices=("A", "B", "indistinguishable"),
                        help="which alternative sounded closer to Reference")
    parser.add_argument("--prefer", choices=("A", "B", "indistinguishable"),
                        help="optional separate preference; closeness remains the verdict")
    parser.add_argument("--listener", required=True)
    parser.add_argument("--comment")
    add_data_dir_arg(parser)
    args = parser.parse_args()

    try:
        key = json.loads(args.key.expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        die(f"cannot read audition key {args.key}: {error}")
    if key.get("schema") != "rab-audition-v1":
        die(f"unsupported audition key schema {key.get('schema')!r}")
    match = key.get("match") or {}
    if match.get("schema") != "match-audition-1":
        die("the key is not attached to a completed match run")
    output = key.get("output") or {}
    montage = pathlib.Path(str(output.get("path", "")))
    if not montage.is_file() or _sha256(montage) != output.get("sha256"):
        die("the audition audio is missing or no longer matches the key; refusing "
            "to attach a verdict to different audio")

    choice = _answer(key, args.choice)
    preference = None if args.prefer is None else _answer(key, args.prefer)
    details = []
    if preference is not None:
        details.append(f"preference={preference}")
    if args.comment and args.comment.strip():
        details.append(args.comment.strip())

    from match.verdict import record_verdict
    from packs.paths import data_root_warning, set_data_root

    set_data_root(args.data_dir)
    warning = data_root_warning()
    if warning:
        print(f"warning: {warning}", file=sys.stderr)
    recorded = record_verdict(
        match["run_dir"],
        candidate_rank=int(match["candidate_rank"]),
        choice=choice,
        listener=args.listener,
        comment="; ".join(details) or None,
    )
    print(f"blind label {args.choice!r} resolved after listening to {choice!r}")
    if preference is not None:
        print(f"separate preference: {preference!r}")
    print(f"recorded trial {recorded.trial_id} in run {recorded.run_id}")
    print(f"learned notes: {recorded.notes_path}")


if __name__ == "__main__":
    guarded(main)
