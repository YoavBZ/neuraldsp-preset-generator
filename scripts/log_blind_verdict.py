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
    montage = pathlib.Path(str(output.get("path", ""))).expanduser().resolve()
    if not montage.is_file() or _sha256(montage) != output.get("sha256"):
        die("the audition audio is missing or no longer matches the key; refusing "
            "to attach a verdict to different audio")

    from match.verdict import (candidate_binding_sha256, validate_audition_trial,
                               validate_candidate)

    try:
        candidate_rank = int(match["candidate_rank"])
        validated = validate_candidate(match["run_dir"], candidate_rank)
    except (KeyError, TypeError, ValueError) as error:
        die(f"the completed match no longer validates against the audition key: {error}")
    binding = match.get("binding") or {}
    expected = {
        "candidate_context_sha256": candidate_binding_sha256(validated),
        "summary_sha256": _sha256(validated.directory / "summary.json"),
        "spec_sha256": _sha256(validated.directory / f"match-{candidate_rank}.json"),
        "template_settings_sha256": hashlib.sha256(json.dumps(
            (validated.summary.get("starting_point") or {}).get("settings") or {},
            sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest(),
    }
    if match.get("run_id") != validated.run.run_id:
        die("the audition key names a different run than the completed match")
    if match.get("source_trial_id") != validated.trial.trial_id:
        die("the audition key names a different source candidate trial")
    for name, digest in expected.items():
        if binding.get(name) != digest:
            die(f"the completed match's {name.removesuffix('_sha256').replace('_', ' ')} "
                "changed after the audition was exported; refusing a stale verdict")
    recorded_renderer = validated.summary.get("renderer") or {}
    if match.get("renderer") != recorded_renderer:
        die("the audition key's renderer provenance differs from the completed run")
    recorded_excerpt = (validated.summary.get("reference") or {}).get("excerpt")
    if match.get("excerpt") != recorded_excerpt:
        die("the audition key's reference excerpt differs from the completed run")
    probe = match.get("probe_di") or {}
    try:
        audition_trial = validate_audition_trial(
            validated, int(match["audition_trial_id"]),
            di_sha=str(probe["audio_sha256"]),
            render_sha=str(match["audition_render_sha256"]),
            trial_sha=str(match["audition_trial_sha256"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        die(f"the heard audition trial no longer validates: {error}")

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
        candidate_rank=candidate_rank,
        choice=choice,
        listener=args.listener,
        comment="; ".join(details) or None,
        audition_trial_id=audition_trial.trial_id,
        audition_di_sha=audition_trial.di_sha,
        audition_render_sha=audition_trial.render_sha,
        audition_trial_sha=match["audition_trial_sha256"],
    )
    print(f"blind label {args.choice!r} resolved after listening to {choice!r}")
    if preference is not None:
        print(f"separate preference: {preference!r}")
    print(f"recorded trial {recorded.trial_id} in run {recorded.run_id}")
    print(f"learned notes: {recorded.notes_path}")


if __name__ == "__main__":
    guarded(main)
