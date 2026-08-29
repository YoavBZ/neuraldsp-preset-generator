"""A completed match becomes a blind audition and a measured verdict."""

from __future__ import annotations

import json
import pathlib
import sqlite3
import subprocess
import sys

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("soundfile", reason="needs the analysis extra")

from match.store import Store

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "samples" / "Example_Clean_PR12.xml"


def run(script: str, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
        cwd=ROOT, capture_output=True, text=True,
    )


@pytest.fixture()
def completed_run(tmp_path):
    from analysis import refchain
    from tests import fixtures_audio as fx

    probe = fx.plucks(seconds=2.0, gap=0.9, seed=73)
    probe_path = tmp_path / "probe.wav"
    reference_path = tmp_path / "reference.wav"
    fx.write_wav(str(probe_path), probe)
    fx.write_wav(str(reference_path), refchain.render(probe, {
        "sw50rAmp/sw50rVolume": 76.0,
        "sw50rAmp/sw50rTreble": 24.0,
    }))
    run_dir = tmp_path / "run"
    matched = run(
        "match_preset.py",
        "--template", TEMPLATE,
        "--reference", reference_path,
        "--reference-mode", "paired_di",
        "--probe-di", probe_path,
        "--amp", "sw50r",
        "--budget", "60",
        "--shortlist", "1",
        "--renderer", "synthetic",
        "--out-dir", run_dir,
    )
    assert matched.returncode == 0, matched.stdout + matched.stderr
    return run_dir, probe_path


def test_export_and_record_one_blind_match_verdict(completed_run, tmp_path):
    run_dir, probe_path = completed_run
    audition_dir = tmp_path / "audition"
    exported = run(
        "export_match_audition.py",
        "--run-dir", run_dir,
        "--candidate", "1",
        "--probe-di", probe_path,
        "--renderer", "synthetic",
        "--seed", "123",
        "--out-dir", audition_dir,
    )
    assert exported.returncode == 0, exported.stdout + exported.stderr

    montage = audition_dir / "audition.flac"
    key_path = audition_dir / "audition.flac.key.json"
    key = json.loads(key_path.read_text())
    assert montage.is_file()
    assert (audition_dir / "raw" / "template.wav").is_file()
    assert (audition_dir / "raw" / "candidate-1.wav").is_file()
    assert key["schema"] == "rab-audition-v1"
    assert key["match"]["schema"] == "match-audition-1"
    assert key["match"]["candidate_rank"] == 1
    assert isinstance(key["match"]["source_trial_id"], int)
    assert isinstance(key["match"]["audition_trial_id"], int)
    assert key["match"]["audition_trial_id"] != key["match"]["source_trial_id"]
    assert set(key["match"]["binding"]) == {
        "candidate_context_sha256", "summary_sha256", "spec_sha256",
        "template_settings_sha256",
    }
    assert key["match"]["roles"] == {"first": "template", "second": "candidate"}
    assert key["match"]["reference_regime"] == "paired_di"
    assert key["sequence"] == "Reference-A-B-Reference-A-B"
    excerpt = json.loads((run_dir / "summary.json").read_text())["reference"][
        "excerpt"]
    assert [source["used_start_s"] for source in key["sources"]] == \
        pytest.approx([excerpt["start_s"]] * 3)
    assert key["segment_duration_s"] == pytest.approx(excerpt["duration_s"])

    # The source XML selects PR12, but the completed run scored --amp sw50r.
    # The audition must reconstruct that effective in-memory starting state.
    import numpy as np
    from analysis import io
    from match import invert
    from match import space as space_module
    from match.renderer_synth import SyntheticRenderer
    from scripts._cli import renderer_paths
    from scripts.export_match_audition import _settings
    from scripts.match_preset import _seed_from_template

    space = space_module.build("morgan", amp="sw50r")
    seed, _ = _seed_from_template(TEMPLATE, space, "morgan")
    effective = invert.apply_to(
        seed, invert.signal_path_selection("morgan", "sw50r"), space,
    )
    renderer = SyntheticRenderer()
    settings = _settings(space, effective, renderer_paths(renderer))
    probe = io.load(str(probe_path), target_rate=renderer.metadata().sample_rate)
    expected = renderer.render(probe.samples, settings).audio
    heard = io.load(str(audition_dir / "raw" / "template.wav")).samples
    assert np.allclose(heard, expected, atol=2e-7)

    candidate_label = next(
        label for label, source_role in key["blind_key"].items()
        if key["match"]["roles"][source_role] == "candidate"
    )
    template_label = "B" if candidate_label == "A" else "A"
    data_dir = tmp_path / "data"
    recorded = run(
        "log_blind_verdict.py",
        "--key", key_path,
        "--choice", candidate_label,
        "--prefer", template_label,
        "--listener", "blind-test",
        "--comment", "candidate is closer but template feels softer",
        "--data-dir", data_dir,
    )
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    assert "resolved after listening to 'candidate'" in recorded.stdout
    assert "separate preference: 'template'" in recorded.stdout

    with Store(str(run_dir / "trials.sqlite3")) as store:
        verdict, = store.verdicts(json.loads((run_dir / "summary.json").read_text())[
            "run_id"])
        heard_trial = store.trial(key["match"]["audition_trial_id"])
    assert verdict["choice"] == "candidate"
    assert verdict["trial_id"] == heard_trial.trial_id
    assert heard_trial.render_sha == key["match"]["audition_render_sha256"]
    assert verdict["listener"] == "blind-test"
    assert verdict["comment"].startswith("preference=template;")

    notes = data_dir / "packs" / "morgan" / "learned-tones.md"
    assert "preference=template" in notes.read_text()

    montage.write_bytes(montage.read_bytes() + b"tampered")
    refused = run(
        "log_blind_verdict.py",
        "--key", key_path,
        "--choice", candidate_label,
        "--listener", "second-listener",
        "--data-dir", data_dir,
    )
    assert refused.returncode != 0
    assert "missing or no longer matches the key" in refused.stderr


def test_an_unpaired_run_is_refused_without_an_explicit_override(
        completed_run, tmp_path):
    run_dir, probe_path = completed_run
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["reference"]["regime"] = "mix"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    refused = run(
        "export_match_audition.py",
        "--run-dir", run_dir,
        "--candidate", "1",
        "--probe-di", probe_path,
        "--renderer", "synthetic",
        "--out-dir", tmp_path / "audition",
    )
    assert refused.returncode != 0
    assert "not the exact probe performance" in refused.stderr
    assert "--allow-unpaired" in refused.stderr


def test_a_different_probe_performance_is_refused(completed_run, tmp_path):
    from analysis import io
    from match.renderer import _hash_audio
    from match.store import Trial
    from tests import fixtures_audio as fx

    run_dir, _ = completed_run
    wrong_probe = tmp_path / "wrong-probe.wav"
    fx.write_wav(str(wrong_probe), fx.plucks(seconds=2.0, gap=0.9, seed=999))
    wrong_sha = _hash_audio(io.load(str(wrong_probe)).samples)
    # An unrelated row must not authorize this DI for the selected candidate.
    summary = json.loads((run_dir / "summary.json").read_text())
    with Store(str(run_dir / "trials.sqlite3")) as store:
        store.add_trial(summary["run_id"], Trial(
            params={"sw50rAmp/sw50rVolume": 1.0}, di_sha=wrong_sha,
            error="an unrelated failed probe",
        ))

    refused = run(
        "export_match_audition.py",
        "--run-dir", run_dir,
        "--candidate", "1",
        "--probe-di", wrong_probe,
        "--renderer", "synthetic",
        "--out-dir", tmp_path / "audition",
    )
    assert refused.returncode != 0
    assert "does not match the DI of the selected candidate trial" in refused.stderr


def test_probe_regime_requires_an_explicit_unpaired_override(
        completed_run, tmp_path):
    run_dir, probe_path = completed_run
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["reference"]["regime"] = "probe"
    summary_path.write_text(json.dumps(summary))
    with sqlite3.connect(run_dir / "trials.sqlite3") as database:
        database.execute("UPDATE runs SET regime = 'probe' WHERE run_id = ?",
                         (summary["run_id"],))

    refused = run(
        "export_match_audition.py", "--run-dir", run_dir, "--candidate", "1",
        "--probe-di", probe_path, "--renderer", "synthetic",
        "--out-dir", tmp_path / "audition",
    )
    assert refused.returncode != 0
    assert "regime 'probe' is not the exact probe performance" in refused.stderr
    assert "--allow-unpaired" in refused.stderr


def test_export_refuses_a_candidate_spec_that_no_longer_matches_its_trial(
        completed_run, tmp_path):
    run_dir, probe_path = completed_run
    spec_path = run_dir / "match-1.json"
    spec = json.loads(spec_path.read_text())
    rendered = next(
        item for item in spec["parameters"]
        if item["module"] == "sw50rAmp" and item["key"] == "sw50rVolume"
    )
    rendered["value"] = 0.123456
    spec_path.write_text(json.dumps(spec))

    refused = run(
        "export_match_audition.py", "--run-dir", run_dir, "--candidate", "1",
        "--probe-di", probe_path, "--renderer", "synthetic",
        "--out-dir", tmp_path / "audition",
    )
    assert refused.returncode != 0
    assert "does not match" in refused.stderr


def test_logging_refuses_a_run_changed_after_the_audition_was_exported(
        completed_run, tmp_path):
    run_dir, probe_path = completed_run
    audition_dir = tmp_path / "audition"
    exported = run(
        "export_match_audition.py", "--run-dir", run_dir, "--candidate", "1",
        "--probe-di", probe_path, "--renderer", "synthetic", "--seed", "12",
        "--out-dir", audition_dir,
    )
    assert exported.returncode == 0, exported.stdout + exported.stderr
    key_path = audition_dir / "audition.flac.key.json"
    key = json.loads(key_path.read_text())
    candidate_label = next(
        label for label, role in key["blind_key"].items()
        if key["match"]["roles"][role] == "candidate"
    )
    wrong_trial = dict(key)
    wrong_trial["match"] = dict(key["match"])
    wrong_trial["match"]["source_trial_id"] += 1
    key_path.write_text(json.dumps(wrong_trial))
    refused_trial = run(
        "log_blind_verdict.py", "--key", key_path, "--choice", candidate_label,
        "--listener", "wrong-trial", "--data-dir", tmp_path / "data",
    )
    assert refused_trial.returncode != 0
    assert "different source candidate trial" in refused_trial.stderr
    key_path.write_text(json.dumps(key))

    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["caveats"].append("changed after listening material was made")
    summary_path.write_text(json.dumps(summary))

    refused = run(
        "log_blind_verdict.py", "--key", key_path, "--choice", candidate_label,
        "--listener", "stale-test", "--data-dir", tmp_path / "data",
    )
    assert refused.returncode != 0
    assert "changed after the audition was exported" in refused.stderr


def test_force_never_overwrites_an_aliased_reference(completed_run, tmp_path):
    run_dir, probe_path = completed_run
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text())
    original = pathlib.Path(summary["reference"]["path"])
    collision_dir = tmp_path / "collision"
    collision_dir.mkdir()
    collision = collision_dir / "audition.flac"
    collision.write_bytes(original.read_bytes())
    summary["reference"]["path"] = str(collision)
    summary_path.write_text(json.dumps(summary))
    before = collision.read_bytes()

    refused = run(
        "export_match_audition.py", "--run-dir", run_dir, "--candidate", "1",
        "--probe-di", probe_path, "--renderer", "synthetic",
        "--out-dir", collision_dir, "--force",
    )
    assert refused.returncode != 0
    assert "aliases the reference input" in refused.stderr
    assert collision.read_bytes() == before

    # A pre-existing output symlink is the same collision even though its spelling
    # differs. --force may replace the link, but must never reach its source.
    summary["reference"]["path"] = str(original)
    summary_path.write_text(json.dumps(summary))
    symlink_dir = tmp_path / "symlink-collision"
    symlink_dir.mkdir()
    (symlink_dir / "audition.flac").symlink_to(original)
    original_before = original.read_bytes()
    refused_symlink = run(
        "export_match_audition.py", "--run-dir", run_dir, "--candidate", "1",
        "--probe-di", probe_path, "--renderer", "synthetic",
        "--out-dir", symlink_dir, "--force",
    )
    assert refused_symlink.returncode != 0
    assert "aliases the reference input" in refused_symlink.stderr
    assert original.read_bytes() == original_before

    dangling_dir = tmp_path / "dangling-output"
    dangling_dir.mkdir()
    dangling = dangling_dir / "audition.flac"
    dangling.symlink_to(tmp_path / "missing.flac")
    refused_dangling = run(
        "export_match_audition.py", "--run-dir", run_dir, "--candidate", "1",
        "--probe-di", probe_path, "--renderer", "synthetic",
        "--out-dir", dangling_dir,
    )
    assert refused_dangling.returncode != 0
    assert "already exists" in refused_dangling.stderr
    assert dangling.is_symlink()


def test_a_run_without_an_exact_excerpt_is_refused(completed_run, tmp_path):
    run_dir, probe_path = completed_run
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["reference"].pop("excerpt")
    summary_path.write_text(json.dumps(summary))

    refused = run(
        "export_match_audition.py", "--run-dir", run_dir, "--candidate", "1",
        "--probe-di", probe_path, "--renderer", "synthetic",
        "--out-dir", tmp_path / "audition",
    )
    assert refused.returncode != 0
    assert "does not record its exact reference excerpt" in refused.stderr


def test_nonfinite_screen_evidence_has_a_stable_audition_binding(
        completed_run, tmp_path):
    run_dir, probe_path = completed_run
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["search"]["movement"]["a/control/whose/extremes/failed"] = float("nan")
    summary_path.write_text(json.dumps(summary))

    exported = run(
        "export_match_audition.py", "--run-dir", run_dir, "--candidate", "1",
        "--probe-di", probe_path, "--renderer", "synthetic", "--seed", "55",
        "--out-dir", tmp_path / "audition",
    )
    assert exported.returncode == 0, exported.stdout + exported.stderr
    assert (tmp_path / "audition" / "audition.flac.key.json").is_file()
