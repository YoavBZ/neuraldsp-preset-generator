#!/usr/bin/env python3
"""Tally a committed held-out listening declaration after every audition has a verdict.

    python scripts/tally_declared_listening.py \
      --declaration docs/heldout-listening-sw50r.md \
      --runs PRIVATE_RUN_DIRECTORY

Print JSON to stdout. This reads no audio and writes no result or private file.
It checks *all* published ``PART/audition/`` directories for verdicts before
opening a single private key, including auditions outside the declaration.
Only the named declaration's frozen decision rules are implemented so far.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._cli import guarded
from scripts._listening_trials import _validate_trials, primary_answer
from scripts.build_validation_crops import _declaration


# One declared test, represented as data rather than thresholds hidden in the
# tally loop. Add another entry only after its own rules are committed first.
RULES = {
    "heldout-sw50r-di-vs-no-di": {
        "alternatives": {"first": "DI match", "second": "no-DI match"},
        "tone_parts": {
            "57 Chevy GTR 1": ("telefunken/57 Chevy/GTR 1",),
            "57 Chevy GTR 2": ("telefunken/57 Chevy/GTR 2",),
            "Memphis ElecGtr3": (
                "cambridge/That's How I Got To Memphis/ElecGtr3",
                "cambridge/That's How I Got To Memphis/ElecGtr3DT",
            ),
            "Guitar-TECHS P3": (
                "guitar-techs/P3_music excerpt 02/02",
                "guitar-techs/P3_music excerpt 06/06",
                "guitar-techs/P3_music excerpt 10/10",
                "guitar-techs/P3_music excerpt 11/11",
            ),
        },
        "trials": ("primary", "repeat"),
        "ordered_rules": (
            {"when": "run_parts_below", "count": 6, "result": "inconclusive"},
            {"when": "first_parts_and_tones", "first_at_least": 6,
             "second_at_most": 1, "first_tones_at_least": 3,
             "result": "supported"},
            {"when": "second_at_least_first", "result": "falsified"},
            {"when": "always", "result": "inconclusive"},
        ),
    },
}


def _digest(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slug(part_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", part_id.replace("/", "-"))


def _declared_rules(path: pathlib.Path, repo: pathlib.Path) -> tuple[dict, list[str], dict]:
    # _declaration checks docs/*.md, regular file, HEAD tracking, unchanged bytes,
    # one valid fenced authorization block, and the exact named part.
    anchor = next(iter(next(iter(RULES.values()))["tone_parts"].values()))[0]
    binding = _declaration(path, anchor, repo)
    rules = RULES.get(binding["test_id"])
    if rules is None:
        raise ValueError(f"no tally rules implemented for {binding['test_id']!r}")
    committed_path = repo / binding["path"]
    content = committed_path.read_bytes()
    if hashlib.sha256(content).hexdigest() != binding["sha256"]:
        raise ValueError("declaration changed during tally setup")
    blocks = re.findall(r"^```json[ \t]*\r?\n(.*?)^```[ \t]*$",
                        content.decode("utf-8"), flags=re.MULTILINE | re.DOTALL)
    declaration = next(json.loads(block) for block in blocks
                       if "held-out-listening-test-v1" in block)
    parts = declaration["parts"]
    expected = [part for group in rules["tone_parts"].values() for part in group]
    if len(parts) != len(expected) or set(parts) != set(expected):
        raise ValueError("declaration's parts do not match its implemented tone rules")
    slugs = [_slug(part) for part in parts]
    if len(slugs) != len(set(slugs)):
        raise ValueError("declared part IDs have colliding run-directory slugs")
    return binding, parts, rules


def _published_auditions(run_dir: pathlib.Path, slugs: set[str]) -> dict[str, pathlib.Path]:
    """Presence-only preflight: no private key is read on an incomplete batch."""
    if not run_dir.is_dir():
        raise ValueError("--runs must be an existing directory of declared parts")
    found = {}
    for part_dir in run_dir.iterdir():
        if part_dir.is_symlink():
            raise ValueError(f"linked part directory is not a declared run: {part_dir.name}")
        if not part_dir.is_dir():
            continue
        audition = part_dir / "audition"
        if not audition.exists() and not audition.is_symlink():
            continue
        if audition.is_symlink() or not audition.is_dir():
            raise ValueError(f"invalid published audition directory: {part_dir.name}")
        found[part_dir.name] = audition
    incomplete = sorted(slug for slug, audition in found.items()
                        if not (audition / "verdict.json").is_file())
    if incomplete:
        raise ValueError("verdict.json is missing for built audition(s): "
                         + ", ".join(incomplete) + "; no private keys were opened")
    unexpected = sorted(set(found) - slugs)
    if unexpected:
        raise ValueError("audition directory is not a declared part: "
                         + ", ".join(unexpected))
    for slug, audition in found.items():
        if (audition / "private-key.json").is_symlink() or not (
                audition / "private-key.json").is_file():
            raise ValueError(f"built audition has no regular private key: {slug}")
        if (audition / "verdict.json").is_symlink():
            raise ValueError(f"built audition has a linked verdict: {slug}")
    return found


def _read_audition(part_id: str, audition: pathlib.Path, binding: dict,
                   trial_kinds: tuple[str, ...]) -> dict:
    key_path = audition / "private-key.json"
    key = json.loads(key_path.read_text(encoding="utf-8"))
    verdict = json.loads((audition / "verdict.json").read_text(encoding="utf-8"))
    if (key.get("schema") != "prospective-backed-audition-v1"
            or key.get("purpose") != "prospective"
            or key.get("validation_mode") != "declared"
            or verdict.get("schema") != "prospective-backed-verdict-v1"):
        raise ValueError(f"{part_id}: invalid declared audition or verdict schema")
    crop_binding = key.get("validation_crop_record") or {}
    if any(crop_binding.get("declaration", {}).get(field) != binding[field]
           for field in ("path", "commit", "sha256", "test_id")):
        raise ValueError(f"{part_id}: audition belongs to another declaration")
    crop_path = pathlib.Path(crop_binding.get("path", ""))
    if (crop_path.resolve() != audition.parent / "crops" / "record.json"
            or not crop_path.is_file()
            or _digest(crop_path) != crop_binding.get("sha256")):
        raise ValueError(f"{part_id}: validation crop binding changed")
    crop = json.loads(crop_path.read_text(encoding="utf-8"))
    if (crop.get("schema") != "validation-crops-1"
            or "/".join(str(crop.get(field, "")) for field in ("source", "song", "part"))
            != part_id
            or crop.get("declaration") != crop_binding["declaration"]):
        raise ValueError(f"{part_id}: crop identifies another part or declaration")
    manifest_binding = key.get("manifest") or {}
    manifest_path = pathlib.Path(manifest_binding.get("path", ""))
    if (manifest_path.resolve() != audition.parent / "audition.json"
            or not manifest_path.is_file()
            or _digest(manifest_path) != manifest_binding.get("sha256")):
        raise ValueError(f"{part_id}: audition manifest binding changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    alternatives = manifest.get("alternatives") or {}
    if (manifest.get("schema") != "prospective-backed-listening-v1"
            or manifest.get("id") != _slug(part_id)
            or manifest.get("validation_mode") != "declared"
            or manifest.get("declared_test_id") != binding["test_id"]
            or pathlib.Path(manifest.get("validation_crop_record", "")).resolve() != crop_path
            or any(pathlib.Path((alternatives.get(role) or {}).get("path", "")).resolve()
                   != audition.parent / f"{role}.wav" for role in ("first", "second"))):
        raise ValueError(f"{part_id}: audition manifest assigns the wrong alternatives")
    if (key.get("objective_record", {}).get("id") != _slug(part_id)
            or verdict.get("audition_key", {}).get("path") != str(key_path)
            or verdict.get("audition_key", {}).get("sha256") != _digest(key_path)
            or verdict.get("heard_audio_sha256") != key.get("output", {}).get("sha256")):
        raise ValueError(f"{part_id}: verdict does not bind this audition")
    trials = key.get("trials")
    answers = verdict.get("listener_trials")
    _validate_trials(trials, answers, key.get("blind_key"))
    if tuple(sorted(trial["kind"] for trial in trials)) != tuple(sorted(trial_kinds)):
        raise ValueError(f"{part_id}: expected exactly the declared two trials")
    if verdict.get("verdict", {}).get("closer") != primary_answer(
            trials, answers, key["blind_key"]):
        raise ValueError(f"{part_id}: primary verdict disagrees with trial answers")
    mapped = [trial["blind_key"][answer] if answer in ("A", "B") else None
              for trial, answer in zip(trials, answers)]
    winner = mapped[0] if mapped[0] == mapped[1] else None
    counts = {role: int(winner == role) for role in ("first", "second")}
    return {"status": "run", "counts": counts, "winner": winner}


def _identical_unheard(part_dir: pathlib.Path) -> bool:
    records = [part_dir / f"{role}.wav.render.json" for role in ("first", "second")]
    if not all(path.is_file() and not path.is_symlink() for path in records):
        return False
    first, second = (json.loads(path.read_text(encoding="utf-8")) for path in records)
    for role, record in zip(("first", "second"), (first, second)):
        if (record.get("schema") != "listening-fresh-render-v1"
                or record.get("process_policy") != "fresh"
                or not isinstance(record.get("applied_settings"), dict)
                or pathlib.Path(record.get("audio", {}).get("path", "")).resolve()
                != part_dir / f"{role}.wav"
                or not record.get("audio", {}).get("sha256")
                or not (part_dir / f"{role}.wav").is_file()):
            raise ValueError(f"{part_dir.name}: invalid {role} render record")
    if (not first.get("di", {}).get("sha256")
            or first["di"]["sha256"] != second.get("di", {}).get("sha256")
            or first.get("pack") != second.get("pack")
            or first.get("amp_model") != second.get("amp_model")):
        raise ValueError(f"{part_dir.name}: alternatives were rendered through different DIs")
    return first["applied_settings"] == second["applied_settings"]


def _outcome(ordered_rules: tuple[dict, ...], *, run_count: int,
             counts: dict[str, int], first_tones: int) -> tuple[str, int]:
    for ordinal, rule in enumerate(ordered_rules, 1):
        kind = rule["when"]
        if kind == "run_parts_below":
            matched = run_count < rule["count"]
        elif kind == "first_parts_and_tones":
            matched = (counts["first"] >= rule["first_at_least"]
                       and counts["second"] <= rule["second_at_most"]
                       and first_tones >= rule["first_tones_at_least"])
        elif kind == "second_at_least_first":
            matched = counts["second"] >= counts["first"]
        elif kind == "always":
            matched = True
        else:
            raise ValueError(f"unknown declared decision rule: {kind}")
        if matched:
            return rule["result"], ordinal
    raise ValueError("declared decision rules have no final case")


def tally(declaration_path: pathlib.Path, run_dir: pathlib.Path,
          *, repo_root: pathlib.Path = ROOT) -> dict:
    repo = repo_root.resolve()
    binding, parts, rules = _declared_rules(declaration_path, repo)
    run_dir = run_dir.expanduser().resolve()
    auditions = _published_auditions(run_dir, {_slug(part) for part in parts})
    part_counts = {}
    for part_id in parts:
        slug = _slug(part_id)
        if slug in auditions:
            part_counts[part_id] = _read_audition(
                part_id, auditions[slug], binding, rules["trials"])
        elif _identical_unheard(run_dir / slug):
            part_counts[part_id] = {
                "status": "run_identical_settings", "counts": {"first": 0, "second": 0},
                "winner": None}
        else:
            part_counts[part_id] = {
                "status": "not_run", "counts": {"first": 0, "second": 0},
                "winner": None}
    tone_counts = {}
    for tone, members in rules["tone_parts"].items():
        counts = {role: sum(part_counts[part]["counts"][role] for part in members)
                  for role in ("first", "second")}
        winner = ("first" if counts["first"] > counts["second"] else
                  "second" if counts["second"] > counts["first"] else None)
        tone_counts[tone] = {"parts": list(members), "counts": counts, "winner": winner}
    run_parts = [part for part in parts if part_counts[part]["status"] != "not_run"]
    totals = {role: sum(row["counts"][role] for row in part_counts.values())
              for role in ("first", "second")}
    result, rule_number = _outcome(
        rules["ordered_rules"], run_count=len(run_parts), counts=totals,
        first_tones=sum(row["winner"] == "first" for row in tone_counts.values()))
    return {"schema": "declared-listening-tally-v1", "test_id": binding["test_id"],
            "declaration": binding, "alternatives": rules["alternatives"],
            "parts_run": run_parts,
            "not_run_parts": [part for part in parts if part not in run_parts],
            "part_counts": part_counts, "tone_counts": tone_counts,
            "total_part_counts": totals, "outcome": result,
            "ordered_rules": list(rules["ordered_rules"]), "applied_rule": rule_number}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--declaration", required=True, type=pathlib.Path)
    parser.add_argument("--runs", required=True, type=pathlib.Path)
    args = parser.parse_args()
    print(json.dumps(tally(args.declaration, args.runs), indent=2, allow_nan=False))


if __name__ == "__main__":
    guarded(main)
