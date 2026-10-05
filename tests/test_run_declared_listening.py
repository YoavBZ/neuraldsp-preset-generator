"""Execution protocol tests use a synthetic repository and fake plugin, never held-out audio."""

from __future__ import annotations

import json
import hashlib
import pathlib
import subprocess
import sys

import pytest

from research.build_validation_crops import _declaration
from research.build_declared_listening_manifest import build as build_manifest
from research.copy_declared_template import copy as copy_template
from research.run_declared_listening import run
from research.summarize_declared_listening import _execution_record


PARTS = ("source/song/part-1", "source/song/part-2")
FAKE = r'''
import argparse
import json
import pathlib
import shutil
import sys

p = argparse.ArgumentParser()
p.add_argument("--step", required=True)
p.add_argument("--run", required=True, type=pathlib.Path)
p.add_argument("--case", required=True)
p.add_argument("--template", type=pathlib.Path)
a = p.parse_args()
run = a.run
print("SECRET_OBJECTIVE_SCORE=0.123")
print("PRIVATE_DIAGNOSTIC", file=sys.stderr)
if a.step == "di_match" and a.case == "fail_no_output":
    sys.exit(3)
if a.step == "di_match" and a.case == "retry":
    marker = run / "retry-marker"
    if not marker.exists():
        marker.write_text("first attempt did not produce the declared output")
        sys.exit(3)
if a.step == "crops":
    dest = run / "crops" / "record.json"
    dest.parent.mkdir()
    (dest.parent / "di.wav").write_bytes(b"synthetic DI")
    if a.case == "partial_crop":
        sys.exit(3)
    dest.write_text('{"synthetic":true}')
elif a.step in ("di_match", "no_di_match"):
    arm = "with-di" if a.step == "di_match" else "no-di"
    dest = run / arm
    dest.mkdir(exist_ok=True)
    (dest / "match-1.json").write_text('{"synthetic":true}')
    caveats = (["nothing beat the preset you started from: synthetic"]
               if arm == "no-di" and a.case in ("fallback", "bad_copy") else [])
    (dest / "summary.json").write_text(json.dumps({"caveats": caveats}))
    if a.step == "di_match" and a.case == "fail_with_output":
        sys.exit(3)
elif a.step in ("di_preset", "no_di_preset"):
    dest = run / ("with-di.xml" if a.step == "di_preset" else "no-di.xml")
    dest.write_text("FAKE PRESET")
elif a.step in ("di_copy", "no_di_copy"):
    dest = run / ("with-di.xml" if a.step == "di_copy" else "no-di.xml")
    if a.case == "bad_copy":
        dest.write_bytes(b"not the template")
    else:
        shutil.copyfile(a.template, dest)
elif a.step in ("first_render", "second_render"):
    role = "first" if a.step == "first_render" else "second"
    (run / f"{role}.wav").write_bytes(b"synthetic audio")
    gain = 1 if role == "first" or a.case == "identical" else 2
    record = run / f"{role}.wav.render.json"
    if role == "second" and a.case == "bad_render_record":
        record.write_text("not JSON")
    else:
        record.write_text(json.dumps({
            "schema": "listening-fresh-render-v1", "applied_settings": {"gain": gain}}))
elif a.step == "manifest":
    (run / "audition.json").write_text('{"synthetic":true}')
elif a.step == "audition":
    dest = run / "audition"
    dest.mkdir()
    (dest / "audition.flac").write_bytes(b"synthetic audition")
else:
    sys.exit(4)
'''


def _step(name: str, case: str) -> dict:
    argv = ["{python}", "scripts/fake_plugin.py", "--step", name,
            "--run", "{run}", "--case", case]
    outputs = {
        "crops": ["{run}/crops/record.json", "{run}/crops/di.wav"],
        "di_match": ["{run}/with-di/match-1.json", "{run}/with-di/summary.json"],
        "no_di_match": ["{run}/no-di/match-1.json", "{run}/no-di/summary.json"],
        "di_preset": ["{run}/with-di.xml"],
        "no_di_preset": ["{run}/no-di.xml"],
        "first_render": ["{run}/first.wav", "{run}/first.wav.render.json"],
        "second_render": ["{run}/second.wav", "{run}/second.wav.render.json"],
        "manifest": ["{run}/audition.json"],
        "audition": ["{run}/audition/audition.flac"],
    }[name]
    spec = {"argv": argv, "outputs": outputs, "primary_output": outputs[0]}
    if name in ("di_preset", "no_di_preset"):
        arm = "with-di" if name == "di_preset" else "no-di"
        spec["summary"] = "{run}/" + arm + "/summary.json"
        spec["fallback_argv"] = ["{python}", "scripts/fake_plugin.py", "--step",
                                 "di_copy" if name == "di_preset" else "no_di_copy",
                                 "--run", "{run}", "--case", case,
                                 "--template", "{repo}/samples/template.xml"]
    if name in ("first_render", "second_render"):
        role = "first" if name == "first_render" else "second"
        spec["applied_settings_record"] = "{run}/" + role + ".wav.render.json"
    return spec


def _repo(tmp_path: pathlib.Path, case: str = "normal"):
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "samples").mkdir()
    (repo / "scripts" / "fake_plugin.py").write_text(FAKE)
    (repo / "samples" / "template.xml").write_bytes(b"EXACT TEMPLATE")
    (repo / ".gitignore").write_text("/runs/\n")
    declaration = repo / "docs" / "test.md"
    test = {"schema": "held-out-listening-test-v1",
            "test_id": "synthetic-test", "parts": list(PARTS)}
    names = ("crops", "di_match", "no_di_match", "di_preset", "no_di_preset",
             "first_render", "second_render", "manifest", "audition")
    commands = {"schema": "declared-listening-commands-v1",
                "test_id": "synthetic-test", "template": "samples/template.xml",
                "steps": {name: _step(name, case) for name in names}}
    declaration.write_text("# Synthetic declared test\n\n```json\n" + json.dumps(test)
                           + "\n```\n\n```json\n" + json.dumps(commands) + "\n```\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "docs", "scripts", "samples",
                    ".gitignore"],
                   check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Synthetic Test",
                    "-c", "user.email=synthetic@example.invalid", "commit", "-qm",
                    "declare synthetic protocol"], check=True)
    return repo, declaration


def _record(runs: pathlib.Path, part: str) -> dict:
    slug = part.replace("/", "-")
    return json.loads((runs / slug / "execution.json").read_text())


def test_parallel_parts_record_commands_logs_outputs_and_freeze(tmp_path, capsys):
    repo, declaration = _repo(tmp_path)
    runs = repo / "runs" / "private-runs"
    result = run(declaration, runs, repo_root=repo, python=pathlib.Path(sys.executable),
                 parallel=2)
    assert [item["status"] for item in result] == ["awaiting_verdict"] * 2
    freeze = (runs / "pip-freeze.txt").read_text()
    assert freeze
    freeze_sha = hashlib.sha256(freeze.encode()).hexdigest()
    for part in PARTS:
        record = _record(runs, part)
        assert record["status"] == "awaiting_verdict"
        assert record["interpreter_pip_freeze"] == str(runs / "pip-freeze.txt")
        assert record["interpreter_pip_freeze_sha256"] == freeze_sha
        assert set(record["steps"]) == {"crops", "di_match", "no_di_match",
                                         "di_preset", "no_di_preset", "first_render",
                                         "second_render", "manifest", "audition"}
        part_dir = runs / part.replace("/", "-")
        binding = _declaration(declaration, part, repo)
        assert _execution_record(part_dir, binding, heard=True)["commit"] == binding["commit"]
        for name, step in record["steps"].items():
            assert step["exit_code"] == 0
            assert step["command"][:2] == [sys.executable, "scripts/fake_plugin.py"]
            assert step["started_at"] <= step["ended_at"]
            assert step["outputs"]
            assert "SECRET_OBJECTIVE_SCORE" in (
                runs / part.replace("/", "-") / step["log"]["path"]).read_text()
    printed = capsys.readouterr().out
    assert "SECRET_OBJECTIVE_SCORE" not in printed
    assert "PRIVATE_DIAGNOSTIC" not in printed
    assert "part-1/audition 0" in printed


def test_fallback_is_exact_template_copy_and_identical_settings_skip_listening(tmp_path):
    repo, declaration = _repo(tmp_path, "fallback")
    runs = repo / "runs" / "fallback-runs"
    run(declaration, runs, repo_root=repo, python=pathlib.Path(sys.executable))
    for part in PARTS:
        record = _record(runs, part)
        assert record["steps"]["no_di_preset"]["variant"] == "template-copy"
        assert (runs / part.replace("/", "-") / "no-di.xml").read_bytes() == b"EXACT TEMPLATE"

    second = tmp_path / "identical"
    identical_repo, identical_decl = _repo(second, "identical")
    identical_runs = identical_repo / "runs" / "identical-runs"
    run(identical_decl, identical_runs, repo_root=identical_repo,
        python=pathlib.Path(sys.executable))
    for part in PARTS:
        record = _record(identical_runs, part)
        assert record["status"] == "run_identical_settings"
        assert "manifest" not in record["steps"]
        assert "audition" not in record["steps"]


def test_fallback_that_is_not_a_byte_copy_stops_the_part(tmp_path):
    repo, declaration = _repo(tmp_path, "bad_copy")
    runs = repo / "runs" / "bad-copy"
    result = run(declaration, runs, repo_root=repo, python=pathlib.Path(sys.executable))
    assert all(item["status"] == "not_run" for item in result)
    for part in PARTS:
        record = _record(runs, part)
        assert record["steps"]["no_di_preset"]["failed"] is True
        assert "first_render" not in record["steps"]


@pytest.mark.parametrize("case,attempts", (("fail_no_output", 2), ("fail_with_output", 1)))
def test_failed_match_stops_part_and_retries_only_without_its_output(tmp_path, case, attempts):
    repo, declaration = _repo(tmp_path, case)
    runs = repo / "runs" / "failed-match"
    run(declaration, runs, repo_root=repo, python=pathlib.Path(sys.executable))
    for part in PARTS:
        record = _record(runs, part)
        assert record["status"] == "not_run"
        assert len(record["steps"]["di_match"]["attempts"]) == attempts
        assert "no_di_match" not in record["steps"]
        assert record["steps"]["di_match"]["attempts"][0]["command"] == (
            record["steps"]["di_match"]["attempts"][-1]["command"])


def test_same_command_succeeds_on_the_one_allowed_rerun(tmp_path):
    repo, declaration = _repo(tmp_path, "retry")
    runs = repo / "runs" / "retry"
    result = run(declaration, runs, repo_root=repo, python=pathlib.Path(sys.executable))
    assert all(item["status"] == "awaiting_verdict" for item in result)
    for part in PARTS:
        attempts = _record(runs, part)["steps"]["di_match"]["attempts"]
        assert [item["exit_code"] for item in attempts] == [3, 0]
        assert attempts[0]["command"] == attempts[1]["command"]


def test_partial_non_match_output_never_gets_retried(tmp_path):
    repo, declaration = _repo(tmp_path, "partial_crop")
    runs = repo / "runs" / "partial-crop"
    run(declaration, runs, repo_root=repo, python=pathlib.Path(sys.executable))
    for part in PARTS:
        record = _record(runs, part)
        assert record["status"] == "not_run"
        assert len(record["steps"]["crops"]["attempts"]) == 1
        assert "di_match" not in record["steps"]


def test_invalid_render_record_finalizes_the_part_as_not_run(tmp_path):
    repo, declaration = _repo(tmp_path, "bad_render_record")
    runs = repo / "runs" / "bad-render"
    result = run(declaration, runs, repo_root=repo, python=pathlib.Path(sys.executable))
    assert all(item["status"] == "not_run" for item in result)
    for part in PARTS:
        record = _record(runs, part)
        assert record["ended_at"] >= record["started_at"]
        assert "JSONDecodeError" in record["error"]
        assert "manifest" not in record["steps"]


def test_refuses_external_run_directory_before_any_execution(tmp_path):
    repo, declaration = _repo(tmp_path)
    external = tmp_path / "external-runs"
    with pytest.raises(ValueError, match="under this worktree's runs"):
        run(declaration, external, repo_root=repo, python=pathlib.Path(sys.executable))
    assert not external.exists()


def test_refuses_dirty_or_edited_committed_declaration(tmp_path):
    repo, declaration = _repo(tmp_path)
    declaration.write_text(declaration.read_text() + "\nchanged after commit\n")
    with pytest.raises(ValueError, match="clean worktree"):
        run(declaration, repo / "runs" / "dirty", repo_root=repo)
    assert not (repo / "runs" / "dirty").exists()


def test_refuses_declaration_without_machine_readable_commands(tmp_path):
    repo, declaration = _repo(tmp_path)
    data = declaration.read_text()
    declaration.write_text(data[:data.rfind("\n```json\n")])
    subprocess.run(["git", "-C", str(repo), "add", "docs/test.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Synthetic Test",
                    "-c", "user.email=synthetic@example.invalid", "commit", "-qm",
                    "remove command block"], check=True)
    with pytest.raises(ValueError, match="one test block and one commands block"):
        run(declaration, repo / "runs" / "missing-block", repo_root=repo)


def _manifest_inputs(tmp_path, roles=("di", "reference", "mix", "backing")):
    crops = tmp_path / "crops"
    crops.mkdir()
    outputs = {}
    for role in roles:
        path = crops / f"{role}.wav"
        path.write_bytes(f"synthetic {role}".encode())
        outputs[role] = {"path": str(path),
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    crop_record = crops / "record.json"
    crop_record.write_text(json.dumps({
        "schema": "validation-crops-1", "split": "held_out", "source": "source",
        "song": "song", "part": "part-1", "reference_lufs": -19.5,
        "excerpt_duration_s": 10, "declaration": {"test_id": "synthetic-test"},
        "outputs": outputs}))
    renders = []
    for role in ("first", "second"):
        audio = tmp_path / f"{role}.wav"
        audio.write_bytes(f"synthetic {role}".encode())
        proof = tmp_path / f"{role}.wav.render.json"
        proof.write_text(json.dumps({
            "schema": "listening-fresh-render-v1", "process_policy": "fresh",
            "pack": "fake", "amp_model": "FakeAmp", "di": outputs["di"],
            "audio": {"path": str(audio),
                      "sha256": hashlib.sha256(audio.read_bytes()).hexdigest()}}))
        renders.append(proof)
    return crop_record, renders, outputs


def test_manifest_builder_uses_the_declared_crops_and_fresh_render_records(tmp_path):
    crop_record, renders, outputs = _manifest_inputs(tmp_path)
    out = tmp_path / "audition.json"
    manifest = build_manifest(crop_record, *renders, out)
    assert json.loads(out.read_text()) == manifest
    assert manifest["reference"]["path"] == outputs["mix"]["path"]
    assert manifest["backing"]["path"] == outputs["backing"]["path"]
    assert manifest["mix"]["guitar_target_lufs"] == -19.5
    assert manifest["reliability"] == {"hidden_repeats": 1, "catch_trial": False}
    with pytest.raises(ValueError, match="cut without its vocal tracks"):
        build_manifest(crop_record, *renders, tmp_path / "instrumental.json",
                       instrumental=True)
    assert not (tmp_path / "instrumental.json").exists()
    half = json.loads(crop_record.read_text())
    half["outputs"]["mix_instrumental"] = outputs["mix"]
    crop_record.write_text(json.dumps(half))
    with pytest.raises(ValueError, match="cut without its vocal tracks"):
        build_manifest(crop_record, *renders, tmp_path / "half.json", instrumental=True)
    assert not (tmp_path / "half.json").exists()


def test_manifest_builder_takes_the_vocal_free_mix_and_backing_together(tmp_path):
    crop_record, renders, outputs = _manifest_inputs(
        tmp_path, ("di", "reference", "mix", "backing", "mix_instrumental",
                   "backing_instrumental"))
    manifest = build_manifest(crop_record, *renders, tmp_path / "audition.json",
                              instrumental=True)
    assert manifest["reference"]["path"] == outputs["mix_instrumental"]["path"]
    assert manifest["backing"]["path"] == outputs["backing_instrumental"]["path"]


def test_template_copy_is_byte_identical_and_never_overwrites(tmp_path):
    source = tmp_path / "template.xml"
    source.write_bytes(b"\x00synthetic preset\xff")
    out = tmp_path / "private" / "answer.xml"
    copy_template(source, out)
    assert out.read_bytes() == source.read_bytes()
    with pytest.raises(ValueError, match="new private path"):
        copy_template(source, out)
    assert out.read_bytes() == source.read_bytes()


def test_the_documented_example_runs_only_tools_the_runner_accepts():
    """The example block in docs/declared-listening-runner.md is what a new declaration
    copies; every command and fallback in it must pass the runner's own check against
    this repository (tools in scripts/ or research/, tracked at HEAD)."""
    import re

    from research.run_declared_listening import _argv

    root = pathlib.Path(__file__).resolve().parents[1]
    doc = (root / "docs" / "declared-listening-runner.md").read_text()
    block = json.loads(re.search(r"```json\n(\{.*?\})\n```", doc, re.S).group(1))
    fields = {"python": "python", "repo": str(root), "declaration": "d.md", "run": "/r",
              "source": "s", "song": "g", "part": "p", "slug": "x", "test_id": "t"}
    checked = 0
    for step in block["steps"].values():
        for key in ("argv", "fallback_argv"):
            if key in step:
                assert _argv(step[key], fields, root)[1] == step[key][1]
                checked += 1
    assert checked == 11
