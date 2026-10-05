"""Bind a closeness answer to an immutable backed audition.

    python research/log_backed_verdict.py --key runs/.../private-key.json \
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
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from _cli import guarded
from build_rab_audition import _write_text
from _listening_trials import CHOICES, consistency, primary_answer
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
    from analysis.listening import (attach_verdict, sha256, valid_frozen_match_v2,
                                    valid_frozen_match_v3)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", required=True, type=pathlib.Path)
    parser.add_argument("--closer", choices=CHOICES,
                        help="single-trial closeness answer")
    parser.add_argument("--trial-closer", action="append", choices=CHOICES,
                        help="multi-trial answer in listening order; repeat per numbered block")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    key_path = args.key.expanduser().resolve()
    _require_private_out_dir(key_path.parent)
    key = json.loads(key_path.read_text())
    if key.get("schema") != "prospective-backed-audition-v1":
        raise ValueError("this is not a prospective backed-audition key")
    if key.get("purpose") != "prospective":
        raise ValueError("workflow rehearsals cannot become listener evidence")
    trials = key.get("trials")
    if trials is None:
        if args.closer is None or args.trial_closer:
            raise ValueError("this audition needs exactly one --closer, not --trial-closer")
        primary_label = args.closer
        trial_answers = None
        reliability = None
    else:
        if args.closer is not None or args.trial_closer is None:
            raise ValueError("answer each numbered block with --trial-closer, not --closer")
        trial_answers = args.trial_closer
        primary_label = primary_answer(trials, trial_answers, key.get("blind_key"))
        reliability = consistency(trials, trial_answers, key["blind_key"])
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
    verdict = {"closer": primary_label, "preferred": None}
    objective = key["objective_record"]
    key_profiles = key.get("objective_profiles_frozen")
    record_profiles = objective.get("objective_profiles_frozen")
    old_v1_only = (key_profiles is None and record_profiles is None and
                   "match_v2" not in (objective.get("objective_scoring") or {}) and
                   "match_v3" not in (objective.get("objective_scoring") or {}))
    v2_profiles = ["unpaired-v1", "unpaired-v2"]
    v3_profiles = [*v2_profiles, "unpaired-v3"]
    valid_v2 = (key_profiles == record_profiles == v2_profiles and
                valid_frozen_match_v2(objective) is not None)
    valid_v3 = (key_profiles == record_profiles == v3_profiles and
                valid_frozen_match_v2(objective) is not None and
                valid_frozen_match_v3(objective) is not None)
    if old_v1_only or valid_v2 or valid_v3:
        scored = attach_verdict(objective, verdict)
    else:
        # A damaged objective cannot invalidate what the listener heard. Keep
        # the verdict, but do not publish a misleading prediction or agreement.
        scored = {key: value for key, value in objective.items()
                  if key not in ("objective_scoring", "agreement", "agreement_with_level",
                                 "agreement_match_v2", "agreement_match_v3")}
        scored["verdict"] = verdict
        scored["scoring_error"] = "frozen match prediction or profile marker is invalid"
    record = {"schema": "prospective-backed-verdict-v1",
              "audition_key": {"path": str(key_path), "sha256": sha256(key_path)},
              "heard_audio_sha256": key["output"]["sha256"],
              "verdict": verdict, "listener_notes": args.notes,
              "frozen_scored_record": scored}
    if trial_answers is not None:
        record["listener_trials"] = trial_answers
        record["listener_consistency"] = reliability
    _publish_verdict(output_path, json.dumps(record, indent=2, allow_nan=False) + "\n")
    print(f"recorded primary closer={primary_label} in {output_path}")
    if reliability is not None:
        print("listener consistency (not objective agreement): "
              f"repeats {reliability['repeat']['consistent']}/"
              f"{reliability['repeat']['trials_not_independent_n']}, "
              f"catch ties {reliability['catch']['indistinguishable']}/"
              f"{reliability['catch']['trials_not_independent_n']}")
    print("objective agreement is in the private verdict; no audio was rescored")


if __name__ == "__main__":
    guarded(main)
