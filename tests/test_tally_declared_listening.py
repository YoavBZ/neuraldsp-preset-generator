"""Declared listening arithmetic with committed synthetic metadata, never held-out audio."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import wave
from copy import deepcopy

import pytest

sf = pytest.importorskip("soundfile")

from scripts.build_validation_crops import _declaration
from scripts._listening_trials import consistency
from scripts.tally_declared_listening import RULES, _slug, tally


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


def _wav(path, sample=1000):
    """A tiny, valid synthetic PCM recording; no held-out material is touched."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48000)
        output.writeframes(int(sample).to_bytes(2, "little", signed=True) * 4800)


def _tally(declaration, runs, repo):
    return tally(declaration, runs, repo_root=repo,
                 rule_registry=_registry(declaration))


def _registry(declaration):
    registry = deepcopy(RULES)
    registry[TEST_ID]["declaration_path"] = "docs/synthetic-listening.md"
    registry[TEST_ID]["declaration_sha256"] = _sha(declaration)
    return registry


def _rebind_key(audition):
    key_path = audition / "private-key.json"
    verdict_path = audition / "verdict.json"
    verdict = json.loads(verdict_path.read_text())
    verdict["audition_key"]["sha256"] = _sha(key_path)
    verdict_path.write_text(json.dumps(verdict))


def _crop(repo, declaration, part_dir, part):
    binding = _declaration(declaration, part, repo)
    crop_path = part_dir / "crops" / "record.json"
    crop_path.parent.mkdir()
    source, song, part_name = part.split("/", 2)
    outputs = {}
    for index, role in enumerate(("di", "reference", "mix", "backing")):
        path = crop_path.parent / f"{role}.wav"
        _wav(path, index * 1000 + 1000)
        outputs[role] = {"path": str(path), "sha256": _sha(path)}
    crop_path.write_text(json.dumps({"schema": "validation-crops-1", "split": "held_out",
                                     "source": source, "song": song, "part": part_name,
                                     "reference_lufs": -18.0, "excerpt_duration_s": 10.0,
                                     "declaration": binding, "outputs": outputs}))
    return binding, crop_path, outputs


def _matches(part_dir):
    for name, regime in (("with-di", "paired_di"), ("no-di", "isolated_stem")):
        match_dir = part_dir / name
        match_dir.mkdir()
        (match_dir / "match-1.json").write_text(json.dumps({
            "name": "synthetic match", "parameters": [{"module": "", "key": "selectedAmp",
                                                        "value": 1}]}))
        (match_dir / "summary.json").write_text(json.dumps({
            "schema": "tone-match-summary-v1", "pack": "morgan",
            "loss_profile": "unpaired-v3", "search": {"budget": 300},
            "renderer": {"quality_mode": "process=fresh"},
            "reference": {"path": str(part_dir / "crops" / "reference.wav"),
                          "regime": regime}}))


def _render(part_dir, role, di, *, settings=None):
    path = part_dir / f"{role}.wav"
    _wav(path, 4000 if role == "first" else 5000)
    preset = part_dir / ("with-di.xml" if role == "first" else "no-di.xml")
    preset.write_text("<synthetic-preset role='" + role + "'/>")
    proof_path = part_dir / f"{role}.wav.render.json"
    proof_path.write_text(json.dumps({
        "schema": "listening-fresh-render-v1", "process_policy": "fresh",
        "pack": "morgan", "amp_model": "SW50R",
        "renderer": {"quality_mode": "process=fresh"},
        "audio": {"path": str(path), "sha256": _sha(path)},
        "di": di, "preset": {"path": str(preset), "sha256": _sha(preset)},
        "applied_settings": settings if settings is not None else {"gain": .5 if role == "first" else .6}}))
    return proof_path


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
    binding, crop_path, outputs = _crop(repo, declaration, part_dir, part)
    _matches(part_dir)
    proofs = {role: _render(part_dir, role, outputs["di"])
              for role in ("first", "second")}
    manifest_path = part_dir / "audition.json"
    manifest_path.write_text(json.dumps({
        "schema": "prospective-backed-listening-v1", "id": slug,
        "target_id": "unassigned", "purpose": "prospective",
        "validation_mode": "declared", "declared_test_id": TEST_ID,
        "validation_crop_record": str(crop_path),
        "reference": {**outputs["mix"], "regime": "mix", "start_s": 0,
                      "duration_s": 10},
        "backing": {**outputs["backing"], "start_s": 0, "gain_db": 0,
                    "guitar_removed": True},
        "alternatives": {role: {"path": str(part_dir / f"{role}.wav"),
                                "sha256": _sha(part_dir / f"{role}.wav"),
                                "render_record": str(proofs[role]),
                                "start_s": 0, "pack": "morgan", "amp_model": "SW50R"}
                         for role in ("first", "second")},
        "mix": {"guitar_target_lufs": -18.0, "master_target_lufs": -20,
                "peak_ceiling_dbtp": -1, "max_ab_lufs_delta": .5,
                "gap_s": .5, "cycles": 1},
        "reliability": {"hidden_repeats": 1, "catch_trial": False}}))
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
                                      "split": "held_out", "declaration": binding},
           "manifest": {"path": str(manifest_path), "sha256": _sha(manifest_path)},
           "objective_record": {"id": slug, "render_provenance": {
               label: {"pack": "morgan", "amp_model": "SW50R",
                       "process_policy": "fresh",
                       "render_record": {"path": str(proofs[role]),
                                         "sha256": _sha(proofs[role])}}
               for label, role in primary.items()}},
           "source_paths": {"reference": outputs["mix"]["path"],
                            "backing": outputs["backing"]["path"],
                            **{role: str(part_dir / f"{role}.wav")
                               for role in ("first", "second")}},
           "source_sha256": {"reference": outputs["mix"]["sha256"],
                             "backing": outputs["backing"]["sha256"],
                             **{role: _sha(part_dir / f"{role}.wav")
                                for role in ("first", "second")}},
           "blind_key": primary, "trials": trials}
    heard = audition / "audition.flac"
    sf.write(heard, [0.05] * 4800, 48000, format="FLAC")
    key["output"] = {"path": str(heard), "sha256": _sha(heard)}
    key_path = audition / "private-key.json"
    key_path.write_text(json.dumps(key))
    verdict = {"schema": "prospective-backed-verdict-v1",
               "audition_key": {"path": str(key_path), "sha256": _sha(key_path)},
               "heard_audio_sha256": _sha(heard),
               "verdict": {"closer": next(answer for trial, answer in zip(trials, answers)
                                     if trial["kind"] == "primary"), "preferred": None},
               "listener_trials": answers,
               "listener_consistency": consistency(trials, answers, primary),
               "frozen_scored_record": {"schema": "synthetic-scored-record"}}
    (audition / "verdict.json").write_text(json.dumps(verdict))
    return audition


def _identical_unheard(repo, declaration, runs, part):
    part_dir = runs / _slug(part)
    part_dir.mkdir()
    _, _, outputs = _crop(repo, declaration, part_dir, part)
    _matches(part_dir)
    for role in ("first", "second"):
        _render(part_dir, role, outputs["di"], settings={"gain": .5})


def test_support_counts_swapped_trials_and_independent_tones(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    choices = ("first", "first", "first", "second", "first", "first", "first", "tie")
    for index, (part, choice) in enumerate(zip(PARTS, choices)):
        _audition(repo, declaration, runs, part, choice,
                  swap=index % 2 == 1, primary_last=index % 3 == 0)

    result = _tally(declaration, runs, repo)
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
    result = _tally(declaration, runs, repo)
    assert result["total_part_counts"] == {"first": 0, "second": 0}
    assert result["outcome"] == "falsified"
    assert result["applied_rule"] == 3


def test_second_wins_a_completed_test(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS:
        _audition(repo, declaration, runs, part, "second")
    result = _tally(declaration, runs, repo)
    assert result["total_part_counts"] == {"first": 0, "second": 8}
    assert result["outcome"] == "falsified"
    assert result["applied_rule"] == 3


def test_six_first_parts_in_only_two_tones_do_not_support(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS[2:]:  # Memphis pair plus all four Guitar-TECHS excerpts.
        _audition(repo, declaration, runs, part, "first")
    result = _tally(declaration, runs, repo)
    assert len(result["parts_run"]) == 6
    assert result["total_part_counts"] == {"first": 6, "second": 0}
    assert sum(row["winner"] == "first" for row in result["tone_counts"].values()) == 2
    assert result["outcome"] == "inconclusive"
    assert result["applied_rule"] == 4


def test_too_few_run_parts_is_inconclusive_even_when_second_wins(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS[:5]:
        _audition(repo, declaration, runs, part, "second")
    result = _tally(declaration, runs, repo)
    assert result["parts_run"] == list(PARTS[:5])
    assert result["not_run_parts"] == list(PARTS[5:])
    assert result["outcome"] == "inconclusive"
    assert result["applied_rule"] == 1


def test_remaining_case_is_inconclusive_and_identical_settings_count_as_run(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS[:5]:
        _audition(repo, declaration, runs, part, "first")
    _identical_unheard(repo, declaration, runs, PARTS[5])
    _audition(repo, declaration, runs, PARTS[6], "second")
    _audition(repo, declaration, runs, PARTS[7], "tie")
    result = _tally(declaration, runs, repo)
    assert result["part_counts"][PARTS[5]]["status"] == "run_identical_settings"
    assert result["part_counts"][PARTS[5]]["counts"] == {"first": 0, "second": 0}
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
        _tally(declaration, runs, repo)
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
        _tally(declaration, runs, repo)


def test_placeholder_verdict_cannot_unblind_any_part(tmp_path, monkeypatch):
    repo, declaration, runs = _repo(tmp_path)
    _audition(repo, declaration, runs, PARTS[0], "first")
    other = _audition(repo, declaration, runs, PARTS[1], "second")
    (other / "verdict.json").write_text("{}")
    original = pathlib.Path.read_text
    opened = []

    def spy(path, *args, **kwargs):
        if path.name == "private-key.json":
            opened.append(path)
            raise AssertionError("a private key was opened before the placeholder was rejected")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", spy)
    with pytest.raises(ValueError, match="incomplete verdict"):
        _tally(declaration, runs, repo)
    assert not opened


@pytest.mark.parametrize("missing", ("match-1.json", "summary.json"))
def test_a_built_audition_without_both_match_outputs_is_not_run(tmp_path, missing):
    repo, declaration, runs = _repo(tmp_path)
    audition = _audition(repo, declaration, runs, PARTS[0], "first")
    (audition.parent / "with-di" / missing).unlink()
    result = _tally(declaration, runs, repo)
    assert result["part_counts"][PARTS[0]]["status"] == "not_run"
    assert PARTS[0] in result["not_run_parts"]
    assert result["total_part_counts"] == {"first": 0, "second": 0}


def test_identical_settings_need_both_match_outputs_to_count_as_run(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    _identical_unheard(repo, declaration, runs, PARTS[0])
    (runs / _slug(PARTS[0]) / "no-di" / "match-1.json").unlink()
    result = _tally(declaration, runs, repo)
    assert result["part_counts"][PARTS[0]]["status"] == "not_run"


def test_failed_sixth_part_cannot_cross_the_decision_gate(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS[:5]:
        _audition(repo, declaration, runs, part, "second")
    _identical_unheard(repo, declaration, runs, PARTS[5])
    (runs / _slug(PARTS[5]) / "no-di" / "match-1.json").unlink()
    result = _tally(declaration, runs, repo)
    assert len(result["parts_run"]) == 5
    assert result["outcome"] == "inconclusive"
    assert result["applied_rule"] == 1


@pytest.mark.parametrize("damage", ("target", "loudness", "delta", "cycles",
                                   "reliability", "backing_gain"))
def test_rejects_builder_valid_but_undeclared_listening_settings(tmp_path, damage):
    repo, declaration, runs = _repo(tmp_path)
    audition = _audition(repo, declaration, runs, PARTS[0], "first")
    manifest_path = audition.parent / "audition.json"
    manifest = json.loads(manifest_path.read_text())
    if damage == "target":
        manifest["target_id"] = "some-song"
    elif damage == "loudness":
        manifest["mix"]["master_target_lufs"] = -18
    elif damage == "delta":
        manifest["mix"]["max_ab_lufs_delta"] = .7
    elif damage == "cycles":
        manifest["mix"]["cycles"] = 2
    elif damage == "reliability":
        manifest["reliability"]["hidden_repeats"] = 2
    else:
        manifest["backing"]["gain_db"] = 1
    manifest_path.write_text(json.dumps(manifest))
    key_path = audition / "private-key.json"
    key = json.loads(key_path.read_text())
    key["manifest"]["sha256"] = _sha(manifest_path)
    key_path.write_text(json.dumps(key))
    _rebind_key(audition)
    with pytest.raises(ValueError, match="manifest"):
        _tally(declaration, runs, repo)


def test_rejects_changed_or_wrong_committed_declaration(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    declaration.write_text(declaration.read_text() + "\nmodified after commit\n")
    with pytest.raises(ValueError, match="differs from its committed HEAD version"):
        _tally(declaration, runs, repo)

    other = tmp_path / "another"
    other.mkdir()
    repo, declaration, runs = _repo(other, parts=PARTS[:-1])
    with pytest.raises(ValueError, match="do not match its implemented tone rules"):
        _tally(declaration, runs, repo)


def test_rejects_another_committed_document_with_same_id_and_parts(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    frozen_rules = _registry(declaration)
    declaration.write_text(declaration.read_text() + "\nConflicting result rules.\n")
    subprocess.run(["git", "-C", str(repo), "add", "docs/synthetic-listening.md"],
                   check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Synthetic Test",
                    "-c", "user.email=synthetic@example.invalid", "commit", "-qm",
                    "change the decision rules"], check=True)
    with pytest.raises(ValueError, match="not the frozen source"):
        tally(declaration, runs, repo_root=repo, rule_registry=frozen_rules)


@pytest.mark.parametrize("damage", ("heard-audio", "reference-crop", "di-crop",
                                   "first-render", "first-render-record",
                                   "first-preset", "unswapped-repeat"))
def test_rejects_changed_audio_render_or_repeat(tmp_path, damage):
    repo, declaration, runs = _repo(tmp_path)
    audition = _audition(repo, declaration, runs, PARTS[0], "first")
    part_dir = audition.parent
    if damage == "unswapped-repeat":
        key_path = audition / "private-key.json"
        key = json.loads(key_path.read_text())
        primary = next(row for row in key["trials"] if row["kind"] == "primary")
        repeat = next(row for row in key["trials"] if row["kind"] == "repeat")
        repeat["blind_key"] = primary["blind_key"]
        key_path.write_text(json.dumps(key))
        _rebind_key(audition)
    else:
        path = {
            "heard-audio": audition / "audition.flac",
            "reference-crop": part_dir / "crops" / "mix.wav",
            "di-crop": part_dir / "crops" / "di.wav",
            "first-render": part_dir / "first.wav",
            "first-render-record": part_dir / "first.wav.render.json",
            "first-preset": part_dir / "with-di.xml",
        }[damage]
        path.write_bytes(path.read_bytes() + (
            b"\n" if damage == "first-render-record" else b"changed after the verdict"))
    with pytest.raises(ValueError, match="changed|differs|swap|hash"):
        _tally(declaration, runs, repo)


@pytest.mark.parametrize("damage", ("di-crop", "first-render", "first-preset"))
def test_identical_settings_need_verified_audio_and_preset(tmp_path, damage):
    repo, declaration, runs = _repo(tmp_path)
    _identical_unheard(repo, declaration, runs, PARTS[0])
    part_dir = runs / _slug(PARTS[0])
    path = {"di-crop": part_dir / "crops" / "di.wav",
            "first-render": part_dir / "first.wav",
            "first-preset": part_dir / "with-di.xml"}[damage]
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="hash|differs"):
        _tally(declaration, runs, repo)


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
        _tally(declaration, runs, repo)
