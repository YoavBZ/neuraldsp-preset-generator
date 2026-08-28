"""A completed match becomes a blind audition and a measured verdict."""

from __future__ import annotations

import json
import pathlib
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
        "--reference-mode", "probe",
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
    assert key["match"]["roles"] == {"first": "template", "second": "candidate"}
    assert key["match"]["reference_regime"] == "probe"
    assert key["sequence"] == "Reference-A-B-Reference-A-B"
    excerpt = json.loads((run_dir / "summary.json").read_text())["reference"][
        "excerpt"]
    assert [source["used_start_s"] for source in key["sources"]] == \
        pytest.approx([excerpt["start_s"]] * 3)
    assert key["segment_duration_s"] == pytest.approx(excerpt["duration_s"])

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
    assert verdict["choice"] == "candidate"
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
    from tests import fixtures_audio as fx

    run_dir, _ = completed_run
    wrong_probe = tmp_path / "wrong-probe.wav"
    fx.write_wav(str(wrong_probe), fx.plucks(seconds=2.0, gap=0.9, seed=999))

    refused = run(
        "export_match_audition.py",
        "--run-dir", run_dir,
        "--candidate", "1",
        "--probe-di", wrong_probe,
        "--renderer", "synthetic",
        "--out-dir", tmp_path / "audition",
    )
    assert refused.returncode != 0
    assert "does not match any reference-level DI" in refused.stderr
