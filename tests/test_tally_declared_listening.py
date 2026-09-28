"""Declared listening arithmetic with committed synthetic metadata, never held-out audio."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

import pytest

from scripts.build_validation_crops import _declaration
from scripts.tally_declared_listening import _slug, tally


PARTS = (
    "telefunken/57 Chevy/GTR 1",
    "telefunken/57 Chevy/GTR 2",
    "cambridge/That's How I Got To Memphis/ElecGtr3",
    "cambridge/That's How I Got To Memphis/ElecGtr3DT",
    "guitar-techs/P3_music excerpt 02/02",
    "guitar-techs/P3_music excerpt 06/06",
    "guitar-techs/P3_music excerpt 10/10",
    "guitar-techs/P3_music excerpt 11/11",
)
TEST_ID = "heldout-sw50r-di-vs-no-di"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo(tmp_path, parts=PARTS):
    repo = tmp_path / "synthetic-repo"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    declaration = docs / "synthetic-listening.md"
    declaration.write_text("# Synthetic declaration\n\n```json\n" + json.dumps({
        "schema": "held-out-listening-test-v1", "test_id": TEST_ID,
        "parts": list(parts)}) + "\n```\n")
    subprocess.run(["git", "-C", str(repo), "add", "docs/synthetic-listening.md"],
                   check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Synthetic Test",
                    "-c", "user.email=synthetic@example.invalid", "commit", "-qm",
                    "declare synthetic listening test"], check=True)
    runs = tmp_path / "synthetic-runs"
    runs.mkdir()
    return repo, declaration, runs


def _audition(repo, declaration, runs, part, choice, *, swap=False,
              primary_last=False):
    slug = _slug(part)
    part_dir = runs / slug
    audition = part_dir / "audition"
    audition.mkdir(parents=True)
    binding = _declaration(declaration, part, repo)
    crop_path = part_dir / "crops" / "record.json"
    crop_path.parent.mkdir()
    source, song, part_name = part.split("/", 2)
    crop_path.write_text(json.dumps({"schema": "validation-crops-1",
                                     "source": source, "song": song, "part": part_name,
                                     "declaration": binding}))
    manifest_path = part_dir / "audition.json"
    manifest_path.write_text(json.dumps({
        "schema": "prospective-backed-listening-v1", "id": slug,
        "validation_mode": "declared", "declared_test_id": TEST_ID,
        "validation_crop_record": str(crop_path),
        "alternatives": {role: {"path": str(part_dir / f"{role}.wav")}
                         for role in ("first", "second")}}))
    primary = {"A": "second", "B": "first"} if swap else {"A": "first", "B": "second"}
    repeat = {"A": primary["B"], "B": primary["A"]}
    order = (("repeat", repeat), ("primary", primary)) if primary_last else (
        ("primary", primary), ("repeat", repeat))
    trials = [{"ordinal": index + 1, "kind": kind, "blind_key": mapping}
              for index, (kind, mapping) in enumerate(order)]
    if choice in ("first", "second"):
        answers = [next(label for label, role in mapping.items() if role == choice)
                   for _, mapping in order]
    elif choice == "tie":
        answers = ["A", "A"]  # Opposite roles because the repeat swaps labels.
    elif choice == "indistinguishable":
        answers = [choice, choice]
    else:
        raise AssertionError(choice)
    key = {"schema": "prospective-backed-audition-v1", "purpose": "prospective",
           "validation_mode": "declared",
           "validation_crop_record": {"path": str(crop_path), "sha256": _sha(crop_path),
                                      "declaration": binding},
           "manifest": {"path": str(manifest_path), "sha256": _sha(manifest_path)},
           "objective_record": {"id": slug}, "blind_key": primary,
           "trials": trials, "output": {"sha256": "synthetic-audio-hash"}}
    key_path = audition / "private-key.json"
    key_path.write_text(json.dumps(key))
    verdict = {"schema": "prospective-backed-verdict-v1",
               "audition_key": {"path": str(key_path), "sha256": _sha(key_path)},
               "heard_audio_sha256": "synthetic-audio-hash",
               "verdict": {"closer": next(answer for trial, answer in zip(trials, answers)
                                     if trial["kind"] == "primary"), "preferred": None},
               "listener_trials": answers}
    (audition / "verdict.json").write_text(json.dumps(verdict))
    return audition


def _identical_unheard(runs, part):
    part_dir = runs / _slug(part)
    part_dir.mkdir()
    for role in ("first", "second"):
        (part_dir / f"{role}.wav").write_bytes(b"synthetic render, not audio")
        (part_dir / f"{role}.wav.render.json").write_text(json.dumps({
            "schema": "listening-fresh-render-v1", "process_policy": "fresh",
            "pack": "morgan", "amp_model": "SW50R",
            "audio": {"path": str(part_dir / f"{role}.wav"), "sha256": "synthetic"},
            "applied_settings": {"gain": .5},
            "di": {"sha256": "synthetic-di-hash"}}))


def test_support_counts_swapped_trials_and_independent_tones(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    choices = ("first", "first", "first", "second", "first", "first", "first", "tie")
    for index, (part, choice) in enumerate(zip(PARTS, choices)):
        _audition(repo, declaration, runs, part, choice,
                  swap=index % 2 == 1, primary_last=index % 3 == 0)

    result = tally(declaration, runs, repo_root=repo)
    assert result["outcome"] == "supported"
    assert result["applied_rule"] == 2
    assert result["parts_run"] == list(PARTS)
    assert result["total_part_counts"] == {"first": 6, "second": 1}
    assert result["part_counts"][PARTS[3]]["counts"] == {"first": 0, "second": 1}
    assert result["part_counts"][PARTS[7]]["counts"] == {"first": 0, "second": 0}
    assert result["tone_counts"]["Memphis ElecGtr3"]["winner"] is None
    assert result["tone_counts"]["Guitar-TECHS P3"]["counts"] == {
        "first": 3, "second": 0}
    assert sum(row["winner"] == "first" for row in result["tone_counts"].values()) == 3
    assert str(runs) not in json.dumps(result), "the public tally must omit private paths"


def test_all_ties_are_falsified_after_the_minimum_run_gate(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS:
        _audition(repo, declaration, runs, part, "indistinguishable")
    result = tally(declaration, runs, repo_root=repo)
    assert result["total_part_counts"] == {"first": 0, "second": 0}
    assert result["outcome"] == "falsified"
    assert result["applied_rule"] == 3


def test_second_wins_a_completed_test(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS:
        _audition(repo, declaration, runs, part, "second")
    result = tally(declaration, runs, repo_root=repo)
    assert result["total_part_counts"] == {"first": 0, "second": 8}
    assert result["outcome"] == "falsified"
    assert result["applied_rule"] == 3


def test_six_first_parts_in_only_two_tones_do_not_support(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS[2:]:  # Memphis pair plus all four Guitar-TECHS excerpts.
        _audition(repo, declaration, runs, part, "first")
    result = tally(declaration, runs, repo_root=repo)
    assert len(result["parts_run"]) == 6
    assert result["total_part_counts"] == {"first": 6, "second": 0}
    assert sum(row["winner"] == "first" for row in result["tone_counts"].values()) == 2
    assert result["outcome"] == "inconclusive"
    assert result["applied_rule"] == 4


def test_too_few_run_parts_is_inconclusive_even_when_second_wins(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS[:5]:
        _audition(repo, declaration, runs, part, "second")
    result = tally(declaration, runs, repo_root=repo)
    assert result["parts_run"] == list(PARTS[:5])
    assert result["not_run_parts"] == list(PARTS[5:])
    assert result["outcome"] == "inconclusive"
    assert result["applied_rule"] == 1


def test_remaining_case_is_inconclusive_and_identical_settings_count_as_run(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS[:5]:
        _audition(repo, declaration, runs, part, "first")
    _identical_unheard(runs, PARTS[5])
    _audition(repo, declaration, runs, PARTS[6], "second")
    _audition(repo, declaration, runs, PARTS[7], "tie")
    result = tally(declaration, runs, repo_root=repo)
    assert result["part_counts"][PARTS[5]] == {
        "status": "run_identical_settings", "counts": {"first": 0, "second": 0},
        "winner": None}
    assert len(result["parts_run"]) == 8
    assert result["total_part_counts"] == {"first": 5, "second": 1}
    assert result["outcome"] == "inconclusive"
    assert result["applied_rule"] == 4


def test_no_private_key_opened_until_every_published_audition_has_verdict(
        tmp_path, monkeypatch):
    repo, declaration, runs = _repo(tmp_path)
    _audition(repo, declaration, runs, PARTS[0], "first")
    incomplete = _audition(repo, declaration, runs, PARTS[1], "second")
    (incomplete / "verdict.json").unlink()
    original = pathlib.Path.read_text
    opened = []

    def spy(path, *args, **kwargs):
        if path.name == "private-key.json":
            opened.append(path)
            raise AssertionError("a private key was opened before all verdicts existed")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", spy)
    with pytest.raises(ValueError, match="verdict.json is missing"):
        tally(declaration, runs, repo_root=repo)
    assert not opened


def test_preflight_includes_undeclared_built_auditions(tmp_path, monkeypatch):
    repo, declaration, runs = _repo(tmp_path)
    _audition(repo, declaration, runs, PARTS[0], "first")
    unexpected = runs / "undeclared" / "audition"
    unexpected.mkdir(parents=True)
    (unexpected / "private-key.json").write_text("invalid and must not be read")
    original = pathlib.Path.read_text

    def refuse_key(path, *args, **kwargs):
        if path.name == "private-key.json":
            raise AssertionError("private key opened before undeclared audition's verdict")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", refuse_key)
    with pytest.raises(ValueError, match="undeclared"):
        tally(declaration, runs, repo_root=repo)


def test_rejects_changed_or_wrong_committed_declaration(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    declaration.write_text(declaration.read_text() + "\nmodified after commit\n")
    with pytest.raises(ValueError, match="differs from its committed HEAD version"):
        tally(declaration, runs, repo_root=repo)

    other = tmp_path / "another"
    other.mkdir()
    repo, declaration, runs = _repo(other, parts=PARTS[:-1])
    with pytest.raises(ValueError, match="do not match its implemented tone rules"):
        tally(declaration, runs, repo_root=repo)


@pytest.mark.parametrize("damage", ("key-hash", "primary-answer", "crop-part",
                                   "one-trial", "reversed-manifest"))
def test_rejects_misbound_or_incomplete_trial_evidence(tmp_path, damage):
    repo, declaration, runs = _repo(tmp_path)
    audition = _audition(repo, declaration, runs, PARTS[0], "first")
    verdict_path = audition / "verdict.json"
    verdict = json.loads(verdict_path.read_text())
    if damage == "key-hash":
        verdict["audition_key"]["sha256"] = "incorrect"
        verdict_path.write_text(json.dumps(verdict))
    elif damage == "primary-answer":
        verdict["verdict"]["closer"] = "indistinguishable"
        verdict_path.write_text(json.dumps(verdict))
    elif damage == "crop-part":
        crop_path = audition.parent / "crops" / "record.json"
        crop = json.loads(crop_path.read_text())
        crop["part"] = "some other guitar"
        crop_path.write_text(json.dumps(crop))
        key_path = audition / "private-key.json"
        key = json.loads(key_path.read_text())
        key["validation_crop_record"]["sha256"] = _sha(crop_path)
        key_path.write_text(json.dumps(key))
        verdict["audition_key"]["sha256"] = _sha(key_path)
        verdict_path.write_text(json.dumps(verdict))
    elif damage == "reversed-manifest":
        manifest_path = audition.parent / "audition.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["alternatives"]["first"]["path"] = str(audition.parent / "second.wav")
        manifest_path.write_text(json.dumps(manifest))
        key_path = audition / "private-key.json"
        key = json.loads(key_path.read_text())
        key["manifest"]["sha256"] = _sha(manifest_path)
        key_path.write_text(json.dumps(key))
        verdict["audition_key"]["sha256"] = _sha(key_path)
        verdict_path.write_text(json.dumps(verdict))
    else:
        key_path = audition / "private-key.json"
        key = json.loads(key_path.read_text())
        key["trials"] = key["trials"][:1]
        key_path.write_text(json.dumps(key))
        verdict["audition_key"]["sha256"] = _sha(key_path)
        verdict_path.write_text(json.dumps(verdict))
    with pytest.raises(ValueError):
        tally(declaration, runs, repo_root=repo)
