#!/usr/bin/env python3
"""Audit private blind-verdict sidecars without rescoring audio.

    python scripts/audit_frozen_listening.py --record PRIVATE_VERDICT.json \
      [--record ANOTHER_VERDICT.json ...] --out-dir PRIVATE_NEW_DIRECTORY

Only logger-produced match and backed verdicts with their original private keys
are accepted. The audit checks the sidecar-to-key binding and counts each target
group once. It cannot prove the key was created before listening or that two
target groups are independent; those remain matters of experiment provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(pathlib.Path(__file__).resolve().parent)]

from _cli import guarded
from build_rab_audition import _write_text
from _listening_trials import consistency, primary_answer
from score_listening import _require_private_out_dir


_BLIND_SIDECAR = re.compile(r"(.+)\.([0-9a-f]{64})\.objective-verdict\.json\Z")
_STATIC_FIELDS = ("reference", "alternatives", "target_id", "render_provenance",
                  "objective_profiles_frozen")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _digest(value: object) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def _audio_binding(key: dict) -> dict:
    output = key.get("output")
    if (not isinstance(output, dict) or
            not isinstance(output.get("path"), str) or not output["path"] or
            not _digest(output.get("sha256"))):
        raise ValueError("audition key has no complete heard-audio binding")
    return output


def _read_object(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _objective_record(key: dict) -> dict:
    value = key.get("objective_record")
    if not isinstance(value, dict):
        raise ValueError("audition key has no objective record object")
    return value


def _same_frozen_record(key_record: dict, verdict_record: dict, *, blind: bool) -> None:
    if not isinstance(key_record, dict) or not isinstance(verdict_record, dict):
        raise ValueError("audition key and verdict must contain objective records")
    for field in _STATIC_FIELDS:
        if key_record.get(field) != verdict_record.get(field):
            raise ValueError(f"audition key and verdict disagree on {field}")
    if blind:
        listener = verdict_record.get("listener")
        if not isinstance(listener, str) or not listener:
            raise ValueError("blind objective verdict has no listener binding")
        suffix = hashlib.sha256(listener.encode()).hexdigest()[:12]
        expected_id = f"{key_record.get('id')}-{suffix}"
    else:
        expected_id = key_record.get("id")
    if verdict_record.get("id") != expected_id:
        raise ValueError("audition key and verdict disagree on comparison id")
    if "scoring_error" in verdict_record:
        if any(field in verdict_record for field in
               ("objective_scoring", "agreement", "agreement_with_level",
                "agreement_match_v2", "agreement_match_v3")):
            raise ValueError("an unscored verdict still contains objective evidence")
    elif key_record.get("objective_scoring") != verdict_record.get("objective_scoring"):
        raise ValueError("audition key and verdict disagree on frozen objectives")


def _bound_consistency(key: dict, verdict: dict, closer: str) -> dict | None:
    """Recompute reliability from the hashed key and ordered listener answers."""
    trials = key.get("trials")
    if trials is None:
        if "listener_trials" in verdict or "listener_consistency" in verdict:
            raise ValueError("a single-trial key cannot carry hidden-trial answers")
        return None
    answers = verdict.get("listener_trials")
    try:
        primary = primary_answer(trials, answers, key.get("blind_key"))
        measured = consistency(trials, answers, key["blind_key"])
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid hidden-trial evidence: {error}") from error
    if primary != closer or verdict.get("listener_consistency") != measured:
        raise ValueError("hidden-trial answers or consistency disagree with the primary verdict")
    return measured


def _closer(record: dict) -> str:
    verdict = record.get("verdict")
    if not isinstance(verdict, dict) or verdict.get("closer") not in (
            "A", "B", "indistinguishable"):
        raise ValueError("each verdict needs a closeness answer")
    return verdict["closer"]


def load_bound_verdict(path: pathlib.Path) -> tuple[dict, str, dict | None]:
    """Read a logger sidecar and its key, refusing a broken frozen-score binding."""
    from analysis.listening import sha256

    path = path.expanduser().resolve()
    verdict = _read_object(path)
    if verdict.get("schema") == "prospective-backed-verdict-v1":
        binding = verdict.get("audition_key")
        if (not isinstance(binding, dict) or
                not isinstance(binding.get("path"), str) or not binding["path"] or
                not _digest(binding.get("sha256"))):
            raise ValueError("backed verdict has no complete private-key binding")
        key_path = pathlib.Path(binding["path"]).expanduser().resolve()
        if not key_path.is_file() or sha256(key_path) != binding["sha256"]:
            raise ValueError("backed verdict no longer matches its private audition key")
        key = _read_object(key_path)
        if key.get("schema") != "prospective-backed-audition-v1" or key.get("purpose") != "prospective":
            raise ValueError("backed verdict does not name a prospective audition")
        output = _audio_binding(key)
        key_record = _objective_record(key)
        if key.get("objective_profiles_frozen") != key_record.get("objective_profiles_frozen"):
            raise ValueError("backed key disagrees on frozen profiles")
        record = verdict.get("frozen_scored_record")
        _same_frozen_record(key_record, record, blind=False)
        if (verdict.get("verdict") != record.get("verdict") or
                not _digest(verdict.get("heard_audio_sha256")) or
                verdict["heard_audio_sha256"] != output["sha256"]):
            raise ValueError("backed verdict disagrees with its listener answer or heard audio")
        return record, "backed", _bound_consistency(key, verdict, _closer(record))

    match = _BLIND_SIDECAR.fullmatch(path.name)
    if not match:
        raise ValueError("expected a logger-produced blind or backed objective verdict")
    key_path = path.with_name(match.group(1))
    key = _read_object(key_path)
    if key.get("schema") != "rab-audition-v1":
        raise ValueError("blind objective verdict has no matching audition key")
    output = _audio_binding(key)
    key_record = _objective_record(key)
    if key.get("objective_profiles_frozen") != key_record.get("objective_profiles_frozen"):
        raise ValueError("blind key disagrees on frozen profiles")
    record = verdict
    _same_frozen_record(key_record, record, blind=True)
    listener_hash = hashlib.sha256(record["listener"].encode()).hexdigest()
    if listener_hash != match.group(2):
        raise ValueError("blind verdict filename disagrees with its listener binding")
    heard = record.get("heard_audio")
    if (not isinstance(heard, dict) or not _digest(heard.get("sha256")) or
            not isinstance(heard.get("path"), str) or not heard["path"] or
            heard["sha256"] != output["sha256"] or heard["path"] != output["path"]):
        raise ValueError("blind verdict disagrees with the audition audio binding")
    binding = record.get("audition_key")
    if binding is None:
        # Old v1-only sidecars predate a digest over the whole blind key. They
        # remain readable, but cannot be prospective v2/v3 evidence.
        if record.get("objective_profiles_frozen") is not None or (
                isinstance(record.get("objective_scoring"), dict) and
                any(field in record["objective_scoring"]
                    for field in ("match_v2", "match_v3"))):
            raise ValueError("v2/v3 blind verdict lacks a whole-key hash")
        return record, "blind-legacy-v1-only", _bound_consistency(key, record, _closer(record))
    if (not isinstance(binding, dict) or
            not isinstance(binding.get("path"), str) or not binding["path"] or
            not _digest(binding.get("sha256")) or
            pathlib.Path(binding["path"]).expanduser().resolve() != key_path or
            sha256(key_path) != binding["sha256"]):
        raise ValueError("blind verdict no longer matches its private audition key")
    return record, "blind", _bound_consistency(key, record, _closer(record))


def main() -> None:
    from analysis.listening import (match_v2_agreement_report,
                                    match_v3_agreement_report, sha256)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, action="append", type=pathlib.Path,
                        help="private logger-produced verdict sidecar; repeat for each verdict")
    parser.add_argument("--out-dir", required=True, type=pathlib.Path,
                        help="new Git-ignored directory for the private report")
    args = parser.parse_args()
    out_dir = _require_private_out_dir(args.out_dir)
    if out_dir.exists() or out_dir.is_symlink():
        raise ValueError("use a new output directory; prior audits are immutable")
    paths = [path.expanduser().resolve() for path in args.record]
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate verdict path")
    records, sources, reliability_rows = [], [], []
    for path in paths:
        record, kind, reliability = load_bound_verdict(path)
        if not isinstance(record.get("id"), str) or not isinstance(record.get("target_id"), str):
            raise ValueError("each verdict needs an id and target_id")
        verdict = record.get("verdict")
        if not isinstance(verdict, dict) or verdict.get("closer") not in (
                "A", "B", "indistinguishable"):
            raise ValueError("each verdict needs a closeness answer")
        records.append(record)
        sources.append({"kind": kind, "sha256": sha256(path)})
        if reliability is not None:
            reliability_rows.append(reliability)
    v2 = match_v2_agreement_report(records)
    v3 = match_v3_agreement_report(records)
    # New auditions ask only for closeness. Historical preference fields remain
    # readable in source records, but are not a question in this audit.
    v2["summary"] = {"closer": v2["summary"]["closer"]}
    for group in v2["target_groups"].values():
        group.pop("preferred", None)
    v3["summary"] = {"closer": v3["summary"]["closer"]}
    for group in v3["target_groups"].values():
        group.pop("preferred", None)
    repeat_total = sum(row["repeat"]["trials_not_independent_n"] for row in reliability_rows)
    repeat_same = sum(row["repeat"]["consistent"] for row in reliability_rows)
    catch_total = sum(row["catch"]["trials_not_independent_n"] for row in reliability_rows)
    catch_ties = sum(row["catch"]["indistinguishable"] for row in reliability_rows)
    listener_consistency = {
        "auditions_with_probes_not_independent_n": len(reliability_rows),
        "repeat": {"trials_not_independent_n": repeat_total,
                   "consistent": repeat_same,
                   "fraction": repeat_same / repeat_total if repeat_total else None},
        "catch": {"trials_not_independent_n": catch_total,
                  "indistinguishable": catch_ties,
                  "fraction": catch_ties / catch_total if catch_total else None},
        "interpretation": "Descriptive within-listener checks, not independent targets, "
                          "objective agreement, or a validated perceptual threshold.",
    }
    report = {
        "schema": "frozen-listening-audit-v1",
        "comparison_count_not_independent_n": len(records),
        "inputs": sources,
        "scoring_error_count": sum("scoring_error" in row for row in records),
        "v2": v2,
        "v3": v3,
        "listener_consistency": listener_consistency,
        "limitations": [
            "The key binding and frozen-score structure are checked; file timestamps do not prove pre-listening creation.",
            "Old v1-only blind sidecars without whole-key hashes remain unscored for v2.",
            "Old v1/v2 sidecars remain unscored for v3; no post-listening v3 score is inferred.",
            "Distinct target IDs and repeated verdicts do not establish independent songs or listeners.",
            "The listener heard an audition, sometimes with backing; the objective scored bare guitar. No audio was rescored here.",
        ],
    }
    out_dir.mkdir(parents=True)
    _write_text(out_dir / "report.json", json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"closer": report["v2"]["summary"]["closer"],
                      "closer_v3": report["v3"]["summary"]["closer"],
                      "listener_consistency": listener_consistency}, indent=2))


if __name__ == "__main__":
    guarded(main)
