#!/usr/bin/env python3
"""Summarize a committed held-out listening declaration after every audition has a verdict.

    python scripts/summarize_declared_listening.py \
      --declaration docs/heldout-listening-sw50r.md \
      --runs PRIVATE_RUN_DIRECTORY

Print JSON to stdout. This hashes audio and provenance files, reconstructing
expected presets in a temporary directory; it never modifies the supplied runs.
It checks *all* published ``PART/audition/`` directories for verdicts before
opening a single private key, including auditions outside the declaration.
Only the named declaration's frozen decision rules are implemented so far.

A part also needs ``PART/execution.json``: an operator's record of the commit,
interpreter environment, zero exit status, and hashed log for each declared
step. Without it the part is not run. The record makes those facts checkable,
though it cannot independently prove that the operator recorded them honestly.
Capture it when the commands run, not by guessing from the presence of outputs.
The record has schema ``declared-listening-execution-v1``, the declaration's
``declaration_sha256`` and ``commit``, a SHA-256 string in
``interpreter_pip_freeze_sha256``, and a ``steps`` object. Each step has
``{"exit_code": 0, "log": {"path": "logs/STEP.log", "sha256": "..."}}``.
The required step names are crops, di_match, no_di_match, di_preset,
no_di_preset, first_render, second_render, and audition when an audition was
built. Log paths may be absolute or relative to PART, but must stay inside PART.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import pathlib
import re
import sqlite3
import sys
import tempfile
from urllib.parse import quote

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._cli import guarded
from scripts._listening_trials import CHOICES, _validate_trials, consistency, primary_answer
from scripts.build_validation_crops import _declaration


# One declared test, represented as data rather than thresholds hidden in the
# summary loop. Add another entry only after its own rules are committed first.
RULES = {
    "heldout-sw50r-di-vs-no-di": {
        "declaration_path": "docs/heldout-listening-sw50r.md",
        "declaration_sha256": "3baf20532235d47f96bafef6dab4e8f51de28282a244bf6a87c1239ae3b5c2d7",
        "template_sha256": "25a3efbf0fd243a976da119fb7b65ff39b48f353f51dcb62a45bbeaa08333acf",
        "renderer_id": "swift",
        "plugin_version": "1.1.1",
        "amp_index": 2,
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


def _declared_rules(path: pathlib.Path, repo: pathlib.Path,
                    registry: dict) -> tuple[dict, list[str], dict]:
    # _declaration checks docs/*.md, regular file, HEAD tracking, unchanged bytes,
    # one valid fenced authorization block, and the exact named part.
    anchor = next(iter(next(iter(registry.values()))["tone_parts"].values()))[0]
    binding = _declaration(path, anchor, repo)
    rules = registry.get(binding["test_id"])
    if rules is None:
        raise ValueError(f"no summary rules implemented for {binding['test_id']!r}")
    if (binding["path"] != rules["declaration_path"]
            or binding["sha256"] != rules["declaration_sha256"]):
        raise ValueError("committed declaration is not the frozen source of these summary rules")
    committed_path = repo / binding["path"]
    content = committed_path.read_bytes()
    if hashlib.sha256(content).hexdigest() != binding["sha256"]:
        raise ValueError("declaration changed during summary setup")
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
    # A zero-byte or placeholder verdict is not a completed listener answer.
    # Inspect *every* verdict before opening the first private key.
    for slug, audition in found.items():
        path = audition / "verdict.json"
        try:
            verdict = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(f"{slug}: incomplete verdict; no private keys were opened") from error
        answers = verdict.get("listener_trials") if isinstance(verdict, dict) else None
        key_binding = (verdict.get("audition_key") or {}) if isinstance(verdict, dict) else {}
        logged = (verdict.get("listener_consistency") or {}) if isinstance(verdict, dict) else {}
        repeat = (logged.get("repeat") or {}) if isinstance(logged, dict) else {}
        catch = (logged.get("catch") or {}) if isinstance(logged, dict) else {}
        key_binding = key_binding if isinstance(key_binding, dict) else {}
        repeat = repeat if isinstance(repeat, dict) else {}
        catch = catch if isinstance(catch, dict) else {}
        if (not isinstance(verdict, dict)
                or verdict.get("schema") != "prospective-backed-verdict-v1"
                or not isinstance(answers, list) or len(answers) != 2
                or any(answer not in CHOICES for answer in answers)
                or (verdict.get("verdict") or {}).get("closer") not in CHOICES
                or key_binding.get("path") != str(audition / "private-key.json")
                or not _is_sha256(key_binding.get("sha256"))
                or not _is_sha256(verdict.get("heard_audio_sha256"))
                or repeat.get("trials_not_independent_n") != 1
                or repeat.get("consistent") not in (0, 1)
                or catch.get("trials_not_independent_n") != 0
                or not isinstance(verdict.get("frozen_scored_record"), dict)):
            raise ValueError(f"{slug}: incomplete verdict; no private keys were opened")
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
    if crop_binding.get("declaration", {}).get("head_commit") != binding["commit"]:
        raise ValueError(f"{part_id}: crop was not made at the declaration commit")
    crop_path = pathlib.Path(crop_binding.get("path", ""))
    if (crop_path.resolve() != audition.parent / "crops" / "record.json"
            or not crop_path.is_file()
            or _digest(crop_path) != crop_binding.get("sha256")):
        raise ValueError(f"{part_id}: validation crop binding changed")
    crop = json.loads(crop_path.read_text(encoding="utf-8"))
    if (crop.get("schema") != "validation-crops-1"
            or crop.get("split") != "held_out"
            or crop_binding.get("split") != "held_out"
            or "/".join(str(crop.get(field, "")) for field in ("source", "song", "part"))
            != part_id
            or crop.get("declaration") != crop_binding["declaration"]):
        raise ValueError(f"{part_id}: crop identifies another part or declaration")
    outputs = crop.get("outputs") or {}
    for role in ("di", "reference", "mix", "backing"):
        _checked_file(outputs.get(role), audition.parent / "crops" / f"{role}.wav",
                      f"{part_id}: {role} crop")
    manifest_binding = key.get("manifest") or {}
    manifest_path = pathlib.Path(manifest_binding.get("path", ""))
    if (manifest_path.resolve() != audition.parent / "audition.json"
            or not manifest_path.is_file()
            or _digest(manifest_path) != manifest_binding.get("sha256")):
        raise ValueError(f"{part_id}: audition manifest binding changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    alternatives = manifest.get("alternatives") or {}
    expected_mix = {"guitar_target_lufs": crop.get("reference_lufs"),
                    "master_target_lufs": -20, "peak_ceiling_dbtp": -1,
                    "max_ab_lufs_delta": .5, "gap_s": .5, "cycles": 1}
    if (manifest.get("schema") != "prospective-backed-listening-v1"
            or manifest.get("id") != _slug(part_id)
            or manifest.get("target_id") != "unassigned"
            or manifest.get("purpose") != "prospective"
            or manifest.get("validation_mode") != "declared"
            or manifest.get("declared_test_id") != binding["test_id"]
            or not isinstance(manifest.get("mix"), dict)
            or any(manifest["mix"].get(field) != value
                   for field, value in expected_mix.items())
            or manifest.get("reliability") != {"hidden_repeats": 1, "catch_trial": False}
            or pathlib.Path(manifest.get("validation_crop_record", "")).resolve() != crop_path
            or any(pathlib.Path((alternatives.get(role) or {}).get("path", "")).resolve()
                   != audition.parent / f"{role}.wav" for role in ("first", "second"))):
        raise ValueError(f"{part_id}: audition manifest assigns the wrong alternatives")
    for role, crop_role in (("reference", "mix"), ("backing", "backing")):
        spec = manifest.get(role)
        expected = outputs[crop_role]
        _checked_file(spec, pathlib.Path(expected["path"]),
                      f"{part_id}: manifest {role}")
        if spec["sha256"] != expected["sha256"]:
            raise ValueError(f"{part_id}: manifest {role} is not its crop")
    if (manifest["reference"].get("regime") != "mix"
            or manifest["reference"].get("start_s") != 0
            or manifest["reference"].get("duration_s") != crop.get("excerpt_duration_s")
            or crop.get("excerpt_duration_s") != 10
            or manifest["backing"].get("start_s") != 0
            or manifest["backing"].get("gain_db") != 0
            or manifest["backing"].get("guitar_removed") is not True):
        raise ValueError(f"{part_id}: manifest changed the listening conditions")
    for role in ("first", "second"):
        spec = alternatives[role]
        _checked_file(spec, audition.parent / f"{role}.wav",
                      f"{part_id}: manifest {role}")
        if (pathlib.Path(spec.get("render_record", "")).resolve() !=
                audition.parent / f"{role}.wav.render.json"
                or spec.get("start_s") != 0
                or spec.get("pack") != "morgan"
                or spec.get("amp_model") != "SW50R"):
            raise ValueError(f"{part_id}: manifest {role} lacks its fresh render")
    if (key.get("objective_record", {}).get("id") != _slug(part_id)
            or verdict.get("audition_key", {}).get("path") != str(key_path)
            or verdict.get("audition_key", {}).get("sha256") != _digest(key_path)
            or verdict.get("heard_audio_sha256") != key.get("output", {}).get("sha256")):
        raise ValueError(f"{part_id}: verdict does not bind this audition")
    _checked_file(key.get("output"), audition / "audition.flac",
                  f"{part_id}: heard audition")
    sources = key.get("source_paths") or {}
    hashes = key.get("source_sha256") or {}
    for role, expected in (("reference", outputs["mix"]),
                           ("backing", outputs["backing"])):
        if (pathlib.Path(sources.get(role, "")).resolve() !=
                pathlib.Path(expected["path"]).resolve()
                or hashes.get(role) != expected["sha256"]):
            raise ValueError(f"{part_id}: {role} does not bind the declared crop")
    evidence = {}
    for role in ("first", "second"):
        audio = audition.parent / f"{role}.wav"
        _checked_file({"path": sources.get(role), "sha256": hashes.get(role)},
                      audio, f"{part_id}: {role} source audio")
        proof = _checked_render(audition.parent, role, outputs["di"])
        if proof["audio"]["sha256"] != hashes[role]:
            raise ValueError(f"{part_id}: {role} source is not its fresh render")
        evidence[role] = proof["preset"]["sha256"]
    provenance = key.get("objective_record", {}).get("render_provenance") or {}
    for label, role in key["blind_key"].items():
        proof_file = audition.parent / f"{role}.wav.render.json"
        source = provenance.get(label) or {}
        if (source.get("pack") != "morgan" or source.get("amp_model") != "SW50R"
                or source.get("process_policy") != "fresh"):
            raise ValueError(f"{part_id}: {label} render provenance changed")
        _checked_file(source.get("render_record"), proof_file,
                      f"{part_id}: {label} render provenance")
    trials = key.get("trials")
    answers = verdict.get("listener_trials")
    _validate_trials(trials, answers, key.get("blind_key"))
    if tuple(sorted(trial["kind"] for trial in trials)) != tuple(sorted(trial_kinds)):
        raise ValueError(f"{part_id}: expected exactly the declared two trials")
    primary = next(trial for trial in trials if trial["kind"] == "primary")
    repeat = next(trial for trial in trials if trial["kind"] == "repeat")
    if repeat["blind_key"] != {"A": primary["blind_key"]["B"],
                               "B": primary["blind_key"]["A"]}:
        raise ValueError(f"{part_id}: hidden repeat did not swap its labels")
    if verdict.get("verdict", {}).get("closer") != primary_answer(
            trials, answers, key["blind_key"]):
        raise ValueError(f"{part_id}: primary verdict disagrees with trial answers")
    if verdict.get("listener_consistency") != consistency(trials, answers,
                                                           key["blind_key"]):
        raise ValueError(f"{part_id}: logged repeat consistency disagrees with answers")
    mapped = [trial["blind_key"][answer] if answer in ("A", "B") else None
              for trial, answer in zip(trials, answers)]
    winner = mapped[0] if mapped[0] == mapped[1] else None
    counts = {role: int(winner == role) for role in ("first", "second")}
    return {"status": "run", "counts": counts, "winner": winner,
            "evidence": {"crop_record_sha256": crop_binding["sha256"],
                         "preset_sha256": evidence}}


def _checked_file(spec: dict | None, expected: pathlib.Path, context: str) -> None:
    """Verify the file behind a recorded path and digest, not just the claim."""
    if (not isinstance(spec, dict) or not isinstance(spec.get("path"), str)
            or not isinstance(spec.get("sha256"), str)
            or len(spec["sha256"]) != 64
            or pathlib.Path(spec.get("path", "")).resolve() != expected
            or expected.is_symlink() or not expected.is_file()
            or _digest(expected) != spec["sha256"]):
        raise ValueError(f"{context} is missing or differs from its recorded hash")


_COMMON_STEPS = ("crops", "di_match", "no_di_match", "di_preset", "no_di_preset",
                 "first_render", "second_render")


def _execution_record(part_dir: pathlib.Path, binding: dict, heard: bool) -> dict:
    """Refuse to count a part whose declared steps were not recorded as successful."""
    path = part_dir / "execution.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{part_dir.name}: missing execution record")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"{part_dir.name}: invalid execution record") from error
    required = set(_COMMON_STEPS) | ({"audition"} if heard else set())
    steps = record.get("steps") if isinstance(record, dict) else None
    if (not isinstance(record, dict)
            or record.get("schema") != "declared-listening-execution-v1"
            or record.get("declaration_sha256") != binding["sha256"]
            or record.get("commit") != binding["commit"]
            or not _is_sha256(record.get("interpreter_pip_freeze_sha256"))
            or not isinstance(steps, dict) or set(steps) != required):
        raise ValueError(f"{part_dir.name}: execution record does not match the declared steps")
    for name, step in steps.items():
        log = step.get("log") if isinstance(step, dict) else None
        if (not isinstance(step, dict) or type(step.get("exit_code")) is not int
                or step["exit_code"] != 0 or not isinstance(log, dict)
                or not isinstance(log.get("path"), str)
                or not _is_sha256(log.get("sha256"))):
            raise ValueError(f"{part_dir.name}: {name} did not record a successful step")
        log_path = pathlib.Path(log["path"])
        if not log_path.is_absolute():
            log_path = part_dir / log_path
        if (log_path.is_symlink() or not log_path.is_file()
                or not log_path.resolve().is_relative_to(part_dir)
                or _digest(log_path) != log["sha256"]):
            raise ValueError(f"{part_dir.name}: {name} log is missing or changed")
    return {"sha256": _digest(path), "commit": record["commit"],
            "interpreter_pip_freeze_sha256": record["interpreter_pip_freeze_sha256"]}


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _match_outputs(part_dir: pathlib.Path, role: str, rules: dict) -> dict:
    """Require both completed match outputs for a part to count as run."""
    name = "with-di" if role == "first" else "no-di"
    output_dir = part_dir / name
    spec_path = output_dir / "match-1.json"
    summary_path = output_dir / "summary.json"
    if any(path.is_symlink() or not path.is_file() for path in (spec_path, summary_path)):
        raise ValueError(f"{part_dir.name}: {name} match did not produce both outputs")
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"{part_dir.name}: invalid {name} match output") from error
    search = summary.get("search") if isinstance(summary, dict) else None
    renderer = summary.get("renderer") if isinstance(summary, dict) else None
    reference = summary.get("reference") if isinstance(summary, dict) else None
    if (not isinstance(spec, dict) or not isinstance(spec.get("parameters"), list)
            or not isinstance(summary, dict)
            or summary.get("schema") != "tone-match-summary-v1"
            or summary.get("pack") != "morgan"
            or summary.get("loss_profile") != "unpaired-v3"
            or not isinstance(search, dict) or search.get("budget") != 300
            or not isinstance(renderer, dict)
            or renderer.get("renderer_id") != rules["renderer_id"]
            or renderer.get("plugin_version") != rules["plugin_version"]
            or "process=fresh" not in renderer.get("quality_mode", "")
            or not isinstance(reference, dict)
            or not isinstance(reference.get("path"), str)
            or pathlib.Path(reference["path"]).resolve()
            != part_dir / "crops" / "reference.wav"
            or reference.get("regime") != (
                "paired_di" if role == "first" else "isolated_stem")):
        raise ValueError(f"{part_dir.name}: {name} match is not the declared run")
    crop_reference = part_dir / "crops" / "reference.wav"
    fingerprint = reference.get("fingerprint")
    source = fingerprint.get("source") if isinstance(fingerprint, dict) else None
    if (crop_reference.is_symlink() or not crop_reference.is_file()
            or not isinstance(source, dict)
            or source.get("sha256") != _digest(crop_reference)):
        raise ValueError(f"{part_dir.name}: {name} matched a different reference crop")
    template = ROOT / "samples" / "SW50R_Atlas_Topology.xml"
    starting_point = summary.get("starting_point")
    template_source = (starting_point.get("template")
                       if isinstance(starting_point, dict) else None)
    settings = (starting_point.get("settings")
                if isinstance(starting_point, dict) else None)
    from match.space import _get

    if (_digest(template) != rules["template_sha256"] or
            not isinstance(template_source, dict) or
            template_source.get("sha256") != rules["template_sha256"]
            or not isinstance(settings, dict)
            or _get(settings, ("", "selectedAmp")) != rules["amp_index"]):
        raise ValueError(f"{part_dir.name}: {name} used another template")
    shortlist = summary.get("shortlist")
    candidate = shortlist[0] if isinstance(shortlist, list) and shortlist else None
    outputs = summary.get("outputs")
    specs = outputs.get("specs") if isinstance(outputs, dict) else None
    if (not isinstance(candidate, dict) or candidate.get("rank") != 1
            or not isinstance(specs, list) or not specs
            or not isinstance(specs[0], str)
            # --out-dir in the declaration is relative to its clean worktree.
            # This script can run from another checkout, so a cwd-based resolve
            # would reject an otherwise valid match. The trial binding below
            # checks the content; here only the declared output slot matters.
            or pathlib.Path(specs[0]).parts[-3:] != spec_path.parts[-3:]):
        raise ValueError(f"{part_dir.name}: {name} has no bound first candidate")
    from match.verdict import VerdictError, _spec_parameters, _validate_changes

    try:
        parameters = _spec_parameters(spec)
        _validate_changes(candidate, parameters)
    except VerdictError as error:
        raise ValueError(f"{part_dir.name}: {name} spec differs from its candidate") from error
    _check_probe_store(output_dir / "trials.sqlite3", summary, role,
                       part_dir / "crops" / "di.wav", candidate, parameters, rules)
    preset = part_dir / ("with-di.xml" if role == "first" else "no-di.xml")
    if preset.is_symlink() or not preset.is_file():
        raise ValueError(f"{part_dir.name}: missing {name} applied preset")
    caveats = summary.get("caveats")
    if not isinstance(caveats, list) or any(not isinstance(item, str) for item in caveats):
        raise ValueError(f"{part_dir.name}: invalid {name} match caveats")
    fallback = any(item.startswith("nothing beat the preset you started from")
                   for item in caveats)
    if fallback:
        expected_sha = _digest(template)
    else:
        from scripts import apply_spec

        with tempfile.TemporaryDirectory(prefix="declared-summary-") as temporary:
            expected = pathlib.Path(temporary) / "expected.xml"
            args = argparse.Namespace(
                template=str(template), spec=str(spec_path), out=str(expected),
                recipe=[], bpm=None, name=None, pack=None, strip_irs=False,
                allow_out_of_range=False, force=False, dry_run=False)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                    io.StringIO()):
                try:
                    apply_spec.run(args)
                except SystemExit as error:
                    raise ValueError(f"{part_dir.name}: {name} spec cannot be applied") from error
            expected_sha = _digest(expected)
    if _digest(preset) != expected_sha:
        raise ValueError(f"{part_dir.name}: {name} preset is not its declared spec or fallback")
    return {"spec_sha256": _digest(spec_path), "summary_sha256": _digest(summary_path),
            "trial_store_sha256": _digest(output_dir / "trials.sqlite3")}


def _check_probe_store(path: pathlib.Path, summary: dict, role: str,
                       crop_di: pathlib.Path, candidate: dict,
                       parameters: dict, rules: dict) -> None:
    """The scored trial DI must be the crop for first, the noise probe for second."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{path.parent.name}: missing trial store for probe verification")
    from analysis import io as audio_io
    from match.renderer import _hash_audio
    from analysis.probes import decaying_noise_bursts
    from match.store import Run, Trial
    from match.verdict import _contexts_match, _trial_matches

    if role == "first":
        expected = _hash_audio(audio_io.load(crop_di).mono())
    else:
        expected = _hash_audio(decaying_noise_bursts(seconds=6.0, gap=0.9, seed=13))
    trial_id = candidate.get("trial_id")
    if isinstance(trial_id, bool) or not isinstance(trial_id, int) or trial_id < 1:
        raise ValueError(f"{path.parent.name}: first candidate has no trial id")
    try:
        uri = f"file:{quote(str(path))}?mode=ro&immutable=1"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as db:
            db.row_factory = sqlite3.Row
            run_row = db.execute("SELECT * FROM runs WHERE run_id = ?",
                                 (summary.get("run_id"),)).fetchone()
            trial_row = db.execute("SELECT * FROM trials WHERE trial_id = ?",
                                   (trial_id,)).fetchone()
            probes = [row[0] for row in db.execute(
                "SELECT di_sha FROM trials WHERE run_id = ? "
                "AND ABS(di_offset_db) < 0.000000001", (summary.get("run_id"),))]
            source_row = (db.execute("SELECT * FROM runs WHERE run_id = ?",
                                     (trial_row["run_id"],)).fetchone()
                          if trial_row is not None else None)
    except (sqlite3.DatabaseError, OSError) as error:
        raise ValueError(f"{path.parent.name}: invalid trial store") from error
    if (run_row is None or trial_row is None or source_row is None
            or any(value != expected for value in probes)
            or trial_row["di_sha"] != expected):
        raise ValueError(f"{path.parent.name}: scored trials used the wrong probe")
    try:
        run = Run(**dict(run_row))
        source_run = Run(**dict(source_row))
        stored = dict(trial_row)
        params = json.loads(stored["params_json"])
        objectives = json.loads(stored["objectives_json"])
        fingerprint = json.loads(stored["fingerprint_json"])
        if (not isinstance(params, dict) or not isinstance(objectives, dict)
                or not isinstance(fingerprint, dict)):
            raise ValueError("candidate trial has malformed JSON fields")
        trial = Trial(
            trial_id=stored["trial_id"], run_id=stored["run_id"],
            params=params, di_sha=stored["di_sha"],
            di_offset_db=stored["di_offset_db"], silent=stored["silent"],
            error=stored["error"], objectives=objectives,
            fingerprint=fingerprint,
        )
        notes = json.loads(run.notes)
        source_notes = json.loads(source_run.notes)
    except (TypeError, ValueError, KeyError) as error:
        raise ValueError(f"{path.parent.name}: invalid trial or match-run notes") from error
    regime = "paired_di" if role == "first" else "isolated_stem"
    expected_template = ("samples", "SW50R_Atlas_Topology.xml")
    if (run.pack != "morgan" or run.regime != regime
            or run.loss_profile != "unpaired-v3" or run.budget != 300
            or pathlib.Path(run.template or "").parts[-2:] != expected_template
            or pathlib.Path(source_run.template or "").parts[-2:] != expected_template
            or run.renderer_id != rules["renderer_id"]
            or run.plugin_version != rules["plugin_version"]
            or not isinstance(notes, dict)
            or (notes.get("probe_note") is None) != (role == "first")
            or (role == "second" and not str(notes["probe_note"]).startswith(
                "no --probe-di was given"))
            or not isinstance(source_notes, dict)
            or (source_notes.get("probe_note") is None) != (role == "first")
            or (role == "second" and not str(source_notes["probe_note"]).startswith(
                "no --probe-di was given"))
            or not _contexts_match(source_run, run, summary)
            or not isinstance(trial.di_offset_db, (int, float))
            or not _trial_matches(trial, summary, candidate, parameters)):
        raise ValueError(f"{path.parent.name}: run did not use the declared probe")


def _checked_render(part_dir: pathlib.Path, role: str, di: dict) -> dict:
    path = part_dir / f"{role}.wav.render.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{part_dir.name}: missing {role} fresh-render record")
    proof = json.loads(path.read_text(encoding="utf-8"))
    if (proof.get("schema") != "listening-fresh-render-v1"
            or proof.get("pack") != "morgan" or proof.get("amp_model") != "SW50R"
            or proof.get("process_policy") != "fresh"
            or "process=fresh" not in proof.get("renderer", {}).get("quality_mode", "")
            or not isinstance(proof.get("applied_settings"), dict)):
        raise ValueError(f"{part_dir.name}: invalid {role} fresh-render record")
    _checked_file(proof.get("audio"), part_dir / f"{role}.wav",
                  f"{part_dir.name}: {role} rendered audio")
    _checked_file(proof.get("di"), part_dir / "crops" / "di.wav",
                  f"{part_dir.name}: {role} render DI")
    if proof["di"]["sha256"] != di["sha256"]:
        raise ValueError(f"{part_dir.name}: {role} used a different DI crop")
    _checked_file(proof.get("preset"), part_dir / ("with-di.xml" if role == "first" else
                                                      "no-di.xml"),
                  f"{part_dir.name}: {role} preset")
    return proof


def _identical_unheard(part_dir: pathlib.Path, part_id: str, binding: dict) -> dict | None:
    records = [part_dir / f"{role}.wav.render.json" for role in ("first", "second")]
    if not all(path.is_file() and not path.is_symlink() for path in records):
        return None
    crop_path = part_dir / "crops" / "record.json"
    if crop_path.is_symlink() or not crop_path.is_file():
        raise ValueError(f"{part_dir.name}: missing validation crop record")
    crop = json.loads(crop_path.read_text(encoding="utf-8"))
    if (crop.get("schema") != "validation-crops-1"
            or crop.get("split") != "held_out"
            or "/".join(str(crop.get(field, "")) for field in ("source", "song", "part"))
            != part_id or not isinstance(crop.get("declaration"), dict)
            or any(crop["declaration"].get(field) != binding[field]
                   for field in ("path", "commit", "sha256", "test_id"))
            or crop["declaration"].get("head_commit") != binding["commit"]):
        raise ValueError(f"{part_dir.name}: identical-settings crop is misbound")
    outputs = crop.get("outputs") or {}
    for role in ("di", "reference", "mix", "backing"):
        _checked_file(outputs.get(role), part_dir / "crops" / f"{role}.wav",
                      f"{part_dir.name}: {role} crop")
    di = outputs["di"]
    first, second = (_checked_render(part_dir, role, di) for role in ("first", "second"))
    if first["applied_settings"] != second["applied_settings"]:
        return None
    return {"crop_record_sha256": _digest(crop_path),
            "preset_sha256": {"first": first["preset"]["sha256"],
                              "second": second["preset"]["sha256"]}}


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


def summarize(declaration_path: pathlib.Path, run_dir: pathlib.Path,
          *, repo_root: pathlib.Path = ROOT, rule_registry: dict | None = None) -> dict:
    repo = repo_root.resolve()
    binding, parts, rules = _declared_rules(declaration_path, repo,
                                           RULES if rule_registry is None else rule_registry)
    run_dir = run_dir.expanduser().resolve()
    auditions = _published_auditions(run_dir, {_slug(part) for part in parts})
    part_counts = {}
    for part_id in parts:
        slug = _slug(part_id)
        part_dir = run_dir / slug
        try:
            execution = _execution_record(part_dir, binding, slug in auditions)
            matches = {role: _match_outputs(part_dir, role, rules)
                       for role in ("first", "second")}
        except ValueError as error:
            part_counts[part_id] = {
                "status": "not_run", "reason": str(error),
                "counts": {"first": 0, "second": 0}, "winner": None}
            continue
        if slug in auditions:
            part_counts[part_id] = _read_audition(
                part_id, auditions[slug], binding, rules["trials"])
        else:
            identical = _identical_unheard(part_dir, part_id, binding)
            part_counts[part_id] = ({
                "status": "run_identical_settings", "counts": {"first": 0, "second": 0},
                "winner": None, "evidence": identical} if identical else {
                "status": "not_run", "counts": {"first": 0, "second": 0},
                "winner": None})
        if part_counts[part_id]["status"] != "not_run":
            part_counts[part_id]["evidence"]["match_outputs"] = matches
            part_counts[part_id]["evidence"]["execution_record"] = execution
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
    return {"schema": "declared-listening-summary-v1", "test_id": binding["test_id"],
            "declaration": binding, "alternatives": rules["alternatives"],
            "not_verified_by_summary": [
                "authenticity of operator-recorded step exit codes, commit, and interpreter environment"
            ],
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
    print(json.dumps(summarize(args.declaration, args.runs), indent=2, allow_nan=False))


if __name__ == "__main__":
    guarded(main)
