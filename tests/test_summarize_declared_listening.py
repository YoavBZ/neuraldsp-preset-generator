"""Declared listening arithmetic with committed synthetic metadata, never held-out audio."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import pathlib
import shutil
import sqlite3
import subprocess
import wave
from copy import deepcopy

import pytest

sf = pytest.importorskip("soundfile")

from scripts.build_validation_crops import _declaration
from scripts._listening_trials import consistency
from scripts import apply_spec
from scripts.summarize_declared_listening import RULES, _slug, summarize


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


def _summarize(declaration, runs, repo):
    return summarize(declaration, runs, repo_root=repo,
                 rule_registry=_registry(declaration))


def _registry(declaration):
    registry = deepcopy(RULES)
    registry[TEST_ID]["declaration_path"] = "docs/synthetic-listening.md"
    registry[TEST_ID]["declaration_sha256"] = _sha(declaration)
    registry[TEST_ID]["renderer_id"] = "synthetic"
    registry[TEST_ID]["plugin_version"] = "synthetic"
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


def _execution(part_dir, binding, *, heard):
    names = ("crops", "di_match", "no_di_match", "di_preset", "no_di_preset",
             "first_render", "second_render") + (("audition",) if heard else ())
    logs = part_dir / "logs"
    logs.mkdir()
    steps = {}
    for name in names:
        path = logs / f"{name}.log"
        path.write_text(f"synthetic {name} completed\n")
        steps[name] = {"exit_code": 0,
                       "log": {"path": str(path.relative_to(part_dir)),
                               "sha256": _sha(path)}}
    (part_dir / "execution.json").write_text(json.dumps({
        "schema": "declared-listening-execution-v1",
        "declaration_sha256": binding["sha256"], "commit": binding["commit"],
        "interpreter_pip_freeze_sha256": "a" * 64, "steps": steps}))


def _matches(part_dir, *, fallback_role=None):
    from analysis import io as audio_io
    from analysis.probes import decaying_noise_bursts
    from match.renderer import _hash_audio
    from match.store import Run, Store, Trial

    template = pathlib.Path(__file__).resolve().parents[1] / "samples" / "SW50R_Atlas_Topology.xml"
    for name, regime in (("with-di", "paired_di"), ("no-di", "isolated_stem")):
        role = "first" if name == "with-di" else "second"
        match_dir = part_dir / name
        match_dir.mkdir()
        spec_path = match_dir / "match-1.json"
        spec_path.write_text(json.dumps({"name": f"synthetic {name}", "parameters": [
            {"module": "", "key": "selectedAmp", "value": 2}]}))
        preset = part_dir / ("with-di.xml" if role == "first" else "no-di.xml")
        if fallback_role == role:
            shutil.copyfile(template, preset)
        else:
            args = argparse.Namespace(template=str(template), spec=str(spec_path),
                                      out=str(preset), recipe=[], bpm=None, name=None,
                                      pack=None, strip_irs=False,
                                      allow_out_of_range=False, force=False, dry_run=False)
            with contextlib.redirect_stdout(io.StringIO()):
                apply_spec.run(args)
        run_id = f"synthetic-{name}"
        probe_note = None if role == "first" else "no --probe-di was given; synthetic noise probe"
        reference_sha = _sha(part_dir / "crops" / "reference.wav")
        renderer = {"quality_mode": "process=fresh", "renderer_id": "synthetic",
                    "plugin_version": "synthetic", "reproducible": True}
        di_sha = (_hash_audio(audio_io.load(part_dir / "crops" / "di.wav").mono())
                  if role == "first" else
                  _hash_audio(decaying_noise_bursts(seconds=6.0, gap=0.9, seed=13)))
        with Store(str(match_dir / "trials.sqlite3")) as store:
            store.start_run(Run(
                run_id=run_id, pack="morgan", regime=regime,
                template=str(template),
                loss_profile="unpaired-v3", budget=300,
                reference_sha=reference_sha, renderer_id="synthetic",
                plugin_version="synthetic", notes=json.dumps({
                    "schema": "tone-match-run-notes-v1", "probe_note": probe_note,
                    "renderer": renderer})))
            trial = store.add_trial(run_id, Trial(
                params={"selectedAmp": 2}, di_sha=di_sha,
                objectives={"total": .5}, fingerprint={}, silent=False))
        (match_dir / "summary.json").write_text(json.dumps({
            "schema": "tone-match-summary-v1", "run_id": run_id, "pack": "morgan",
            "loss_profile": "unpaired-v3", "search": {"budget": 300},
            "renderer": renderer,
            "starting_point": {"template": {"path": str(template),
                                             "sha256": _sha(template)},
                               "settings": {"selectedAmp": 2}},
            "shortlist": [{"rank": 1, "trial_id": trial.trial_id, "score": .5,
                           "objectives": {"total": .5}, "changes": [],
                           "fingerprint": {}, "fingerprint_delta": []}],
            "outputs": {"specs": [str(spec_path)]},
            "caveats": (["nothing beat the preset you started from"]
                        if fallback_role == role else ([probe_note] if probe_note else [])),
            "reference": {"path": str(part_dir / "crops" / "reference.wav"),
                          "regime": regime,
                          "fingerprint": {"source": {"sha256": reference_sha}}}}))


def _render(part_dir, role, di, *, settings=None):
    path = part_dir / f"{role}.wav"
    _wav(path, 4000 if role == "first" else 5000)
    preset = part_dir / ("with-di.xml" if role == "first" else "no-di.xml")
    assert preset.is_file()
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
              primary_last=False, fallback_role=None):
    slug = _slug(part)
    part_dir = runs / slug
    audition = part_dir / "audition"
    audition.mkdir(parents=True)
    binding, crop_path, outputs = _crop(repo, declaration, part_dir, part)
    _matches(part_dir, fallback_role=fallback_role)
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
    _execution(part_dir, binding, heard=True)
    return audition


def _identical_unheard(repo, declaration, runs, part):
    part_dir = runs / _slug(part)
    part_dir.mkdir()
    binding, _, outputs = _crop(repo, declaration, part_dir, part)
    _matches(part_dir)
    for role in ("first", "second"):
        _render(part_dir, role, outputs["di"], settings={"gain": .5})
    _execution(part_dir, binding, heard=False)


def test_support_counts_swapped_trials_and_independent_tones(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    choices = ("first", "first", "first", "second", "first", "first", "first", "tie")
    for index, (part, choice) in enumerate(zip(PARTS, choices)):
        _audition(repo, declaration, runs, part, choice,
                  swap=index % 2 == 1, primary_last=index % 3 == 0)

    result = _summarize(declaration, runs, repo)
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
    assert str(runs) not in json.dumps(result), "the public summary must omit private paths"


def test_all_ties_are_falsified_after_the_minimum_run_gate(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS:
        _audition(repo, declaration, runs, part, "indistinguishable")
    result = _summarize(declaration, runs, repo)
    assert result["total_part_counts"] == {"first": 0, "second": 0}
    assert result["outcome"] == "falsified"
    assert result["applied_rule"] == 3


def test_second_wins_a_completed_test(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS:
        _audition(repo, declaration, runs, part, "second")
    result = _summarize(declaration, runs, repo)
    assert result["total_part_counts"] == {"first": 0, "second": 8}
    assert result["outcome"] == "falsified"
    assert result["applied_rule"] == 3


def test_six_first_parts_in_only_two_tones_do_not_support(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS[2:]:  # Memphis pair plus all four Guitar-TECHS excerpts.
        _audition(repo, declaration, runs, part, "first")
    result = _summarize(declaration, runs, repo)
    assert len(result["parts_run"]) == 6
    assert result["total_part_counts"] == {"first": 6, "second": 0}
    assert sum(row["winner"] == "first" for row in result["tone_counts"].values()) == 2
    assert result["outcome"] == "inconclusive"
    assert result["applied_rule"] == 4


def test_too_few_run_parts_is_inconclusive_even_when_second_wins(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS[:5]:
        _audition(repo, declaration, runs, part, "second")
    result = _summarize(declaration, runs, repo)
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
    result = _summarize(declaration, runs, repo)
    assert result["part_counts"][PARTS[5]]["status"] == "run_identical_settings"
    assert result["part_counts"][PARTS[5]]["counts"] == {"first": 0, "second": 0}
    assert len(result["parts_run"]) == 8
    assert result["total_part_counts"] == {"first": 5, "second": 1}
    assert result["outcome"] == "inconclusive"
    assert result["applied_rule"] == 4


def test_declared_template_fallback_is_bound_to_its_render(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    _audition(repo, declaration, runs, PARTS[0], "first", fallback_role="first")
    result = _summarize(declaration, runs, repo)
    assert result["part_counts"][PARTS[0]]["status"] == "run"
    assert result["part_counts"][PARTS[0]]["counts"]["first"] == 1


@pytest.mark.parametrize("damage", ("di_uses_noise", "no_di_uses_crop",
                                   "no_di_claims_a_di", "wrong_spec", "wrong_template",
                                   "wrong_candidate_score", "wrong_candidate_change",
                                   "wrong_trial_parameters", "wrong_reference_hash",
                                   "wrong_renderer", "wrong_amp", "wrong_run_template"))
def test_match_provenance_mismatch_makes_part_not_run(tmp_path, damage):
    repo, declaration, runs = _repo(tmp_path)
    audition = _audition(repo, declaration, runs, PARTS[0], "first")
    part_dir = audition.parent
    if damage in ("di_uses_noise", "no_di_uses_crop", "no_di_claims_a_di"):
        from analysis import io as audio_io
        from analysis.probes import decaying_noise_bursts
        from match.renderer import _hash_audio

        match_dir = part_dir / ("with-di" if damage == "di_uses_noise" else "no-di")
        store = sqlite3.connect(match_dir / "trials.sqlite3")
        try:
            if damage == "no_di_claims_a_di":
                store.execute("UPDATE runs SET notes = ?", (json.dumps({"probe_note": None}),))
            else:
                wrong = (_hash_audio(decaying_noise_bursts(seconds=6.0, gap=0.9, seed=13))
                         if damage == "di_uses_noise" else
                         _hash_audio(audio_io.load(part_dir / "crops" / "di.wav").mono()))
                store.execute("UPDATE trials SET di_sha = ?", (wrong,))
            store.commit()
        finally:
            store.close()
    elif damage == "wrong_spec":
        path = part_dir / "with-di" / "match-1.json"
        spec = json.loads(path.read_text())
        spec["parameters"][0]["value"] = 1
        path.write_text(json.dumps(spec))
        template = pathlib.Path(__file__).resolve().parents[1] / "samples" / "SW50R_Atlas_Topology.xml"
        args = argparse.Namespace(template=str(template), spec=str(path),
                                  out=str(part_dir / "with-di.xml"), recipe=[], bpm=None,
                                  name=None, pack=None, strip_irs=False,
                                  allow_out_of_range=False, force=True, dry_run=False)
        with contextlib.redirect_stdout(io.StringIO()):
            apply_spec.run(args)
    elif damage == "wrong_trial_parameters":
        store = sqlite3.connect(part_dir / "with-di" / "trials.sqlite3")
        try:
            store.execute("UPDATE trials SET params_json = ?", ('{"selectedAmp":1}',))
            store.commit()
        finally:
            store.close()
    elif damage == "wrong_reference_hash":
        path = part_dir / "with-di" / "summary.json"
        summary = json.loads(path.read_text())
        summary["reference"]["fingerprint"]["source"]["sha256"] = "0" * 64
        path.write_text(json.dumps(summary))
        store = sqlite3.connect(part_dir / "with-di" / "trials.sqlite3")
        try:
            store.execute("UPDATE runs SET reference_sha = ?", ("0" * 64,))
            store.commit()
        finally:
            store.close()
    elif damage == "wrong_run_template":
        store = sqlite3.connect(part_dir / "with-di" / "trials.sqlite3")
        try:
            store.execute("UPDATE runs SET template = ?", ("samples/PR12.xml",))
            store.commit()
        finally:
            store.close()
    else:
        path = part_dir / "with-di" / "summary.json"
        summary = json.loads(path.read_text())
        if damage == "wrong_template":
            summary["starting_point"]["template"]["sha256"] = "0" * 64
        elif damage == "wrong_candidate_score":
            summary["shortlist"][0]["score"] = .1
        elif damage == "wrong_renderer":
            summary["renderer"]["renderer_id"] = "not-swift"
        elif damage == "wrong_amp":
            summary["starting_point"]["settings"]["selectedAmp"] = 1
        else:
            summary["shortlist"][0]["changes"] = [
                {"path": "selectedAmp", "from": 0, "to": 1}]
        path.write_text(json.dumps(summary))
    result = _summarize(declaration, runs, repo)
    assert result["part_counts"][PARTS[0]]["status"] == "not_run"
    assert PARTS[0] not in result["parts_run"]


def test_cached_first_candidate_can_come_from_matching_earlier_run(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    audition = _audition(repo, declaration, runs, PARTS[0], "first")
    store_path = audition.parent / "with-di" / "trials.sqlite3"
    store = sqlite3.connect(store_path)
    try:
        store.execute("INSERT INTO runs SELECT 'earlier-matching-run', created_at, "
                      "pack, template, reference_sha, regime, loss_profile, budget, "
                      "renderer_id, plugin_version, notes FROM runs")
        store.execute("UPDATE trials SET run_id = 'earlier-matching-run'")
        store.commit()
    finally:
        store.close()
    assert _summarize(declaration, runs, repo)["part_counts"][PARTS[0]]["status"] == "run"

    store = sqlite3.connect(store_path)
    try:
        store.execute("UPDATE runs SET reference_sha = ? WHERE run_id = ?",
                      ("0" * 64, "earlier-matching-run"))
        store.commit()
    finally:
        store.close()
    assert _summarize(declaration, runs, repo)["part_counts"][PARTS[0]]["status"] == "not_run"


@pytest.mark.parametrize("damage", ("missing", "failed_step", "missing_step",
                                   "wrong_commit", "changed_log"))
def test_failed_or_unrecorded_declared_step_is_not_run(tmp_path, damage):
    repo, declaration, runs = _repo(tmp_path)
    audition = _audition(repo, declaration, runs, PARTS[0], "first")
    part_dir = audition.parent
    path = part_dir / "execution.json"
    if damage == "missing":
        path.unlink()
    else:
        record = json.loads(path.read_text())
        if damage == "failed_step":
            record["steps"]["no_di_match"]["exit_code"] = 1
        elif damage == "missing_step":
            del record["steps"]["first_render"]
        elif damage == "wrong_commit":
            record["commit"] = "0" * 40
        else:
            log = part_dir / record["steps"]["crops"]["log"]["path"]
            log.write_text("changed after the record\n")
        path.write_text(json.dumps(record))
    result = _summarize(declaration, runs, repo)
    assert result["part_counts"][PARTS[0]]["status"] == "not_run"
    assert PARTS[0] not in result["parts_run"]


def test_a_later_repo_commit_does_not_invalidate_the_frozen_crop(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    _audition(repo, declaration, runs, PARTS[0], "first")
    later = repo / "docs" / "unrelated.md"
    later.write_text("Unrelated later change\n")
    subprocess.run(["git", "-C", str(repo), "add", "docs/unrelated.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Synthetic Test",
                    "-c", "user.email=synthetic@example.invalid", "commit", "-qm",
                    "unrelated change"], check=True)
    assert _summarize(declaration, runs, repo)["part_counts"][PARTS[0]]["status"] == "run"


def test_relative_summary_spec_path_from_other_worktree_is_accepted(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    audition = _audition(repo, declaration, runs, PARTS[0], "first")
    path = audition.parent / "with-di" / "summary.json"
    summary = json.loads(path.read_text())
    summary["outputs"]["specs"][0] = (
        f"runs/heldout-sw50r/{audition.parent.name}/with-di/match-1.json")
    path.write_text(json.dumps(summary))
    assert _summarize(declaration, runs, repo)["part_counts"][PARTS[0]]["status"] == "run"

    summary["outputs"]["specs"][0] = (
        f"runs/heldout-sw50r/{audition.parent.name}/with-di/match-2.json")
    path.write_text(json.dumps(summary))
    assert _summarize(declaration, runs, repo)["part_counts"][PARTS[0]]["status"] == "not_run"


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
        _summarize(declaration, runs, repo)
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
        _summarize(declaration, runs, repo)


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
        _summarize(declaration, runs, repo)
    assert not opened


@pytest.mark.parametrize("missing", ("match-1.json", "summary.json"))
def test_a_built_audition_without_both_match_outputs_is_not_run(tmp_path, missing):
    repo, declaration, runs = _repo(tmp_path)
    audition = _audition(repo, declaration, runs, PARTS[0], "first")
    (audition.parent / "with-di" / missing).unlink()
    result = _summarize(declaration, runs, repo)
    assert result["part_counts"][PARTS[0]]["status"] == "not_run"
    assert PARTS[0] in result["not_run_parts"]
    assert result["total_part_counts"] == {"first": 0, "second": 0}


def test_identical_settings_need_both_match_outputs_to_count_as_run(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    _identical_unheard(repo, declaration, runs, PARTS[0])
    (runs / _slug(PARTS[0]) / "no-di" / "match-1.json").unlink()
    result = _summarize(declaration, runs, repo)
    assert result["part_counts"][PARTS[0]]["status"] == "not_run"


def test_failed_sixth_part_cannot_cross_the_decision_gate(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    for part in PARTS[:5]:
        _audition(repo, declaration, runs, part, "second")
    _identical_unheard(repo, declaration, runs, PARTS[5])
    (runs / _slug(PARTS[5]) / "no-di" / "match-1.json").unlink()
    result = _summarize(declaration, runs, repo)
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
        _summarize(declaration, runs, repo)


def test_rejects_changed_or_wrong_committed_declaration(tmp_path):
    repo, declaration, runs = _repo(tmp_path)
    declaration.write_text(declaration.read_text() + "\nmodified after commit\n")
    with pytest.raises(ValueError, match="differs from its committed HEAD version"):
        _summarize(declaration, runs, repo)

    other = tmp_path / "another"
    other.mkdir()
    repo, declaration, runs = _repo(other, parts=PARTS[:-1])
    with pytest.raises(ValueError, match="do not match its implemented tone rules"):
        _summarize(declaration, runs, repo)


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
        summarize(declaration, runs, repo_root=repo, rule_registry=frozen_rules)


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
    if damage == "first-preset":
        assert _summarize(declaration, runs, repo)["part_counts"][PARTS[0]]["status"] == "not_run"
    else:
        with pytest.raises(ValueError, match="changed|differs|swap|hash"):
            _summarize(declaration, runs, repo)


@pytest.mark.parametrize("damage", ("di-crop", "first-render", "first-preset"))
def test_identical_settings_need_verified_audio_and_preset(tmp_path, damage):
    repo, declaration, runs = _repo(tmp_path)
    _identical_unheard(repo, declaration, runs, PARTS[0])
    part_dir = runs / _slug(PARTS[0])
    path = {"di-crop": part_dir / "crops" / "di.wav",
            "first-render": part_dir / "first.wav",
            "first-preset": part_dir / "with-di.xml"}[damage]
    path.write_bytes(path.read_bytes() + b"tampered")
    if damage == "first-preset":
        assert _summarize(declaration, runs, repo)["part_counts"][PARTS[0]]["status"] == "not_run"
    else:
        with pytest.raises(ValueError, match="hash|differs"):
            _summarize(declaration, runs, repo)


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
        _summarize(declaration, runs, repo)
