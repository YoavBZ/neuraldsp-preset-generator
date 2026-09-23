"""A backed listening file must retain blind, bare-guitar evidence."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("soundfile")
pytest.importorskip("scipy")
pytest.importorskip("pyloudnorm")

from analysis import io
from analysis.listening import sha256
from tests import fixtures_audio as fx

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_backed_audition.py"
VERDICT_SCRIPT = ROOT / "scripts" / "log_backed_verdict.py"


def _fixture(tmp_path):
    rate = fx.SAMPLE_RATE
    t = np.arange(rate * 2) / rate
    bed = .025 * np.sin(2 * np.pi * 110 * t)
    first = .04 * np.sin(2 * np.pi * 440 * t)
    second = .04 * np.sin(2 * np.pi * 880 * t)
    reference = bed + first
    paths = {}
    for name, samples in (("reference", reference), ("backing", bed),
                          ("first", first), ("second", second)):
        path = fx.write_wav(tmp_path / f"{name}.wav", samples)
        paths[name] = {"path": str(path), "sha256": sha256(path), "start_s": 0.0}
    manifest = {
        "schema": "prospective-backed-listening-v1", "id": "new-song-01",
        "target_id": "new-song", "reference": {**paths["reference"],
                                            "duration_s": 1.0, "regime": "mix"},
        "backing": {**paths["backing"], "gain_db": 0.0,
                    "guitar_removed": True},
        "alternatives": {
            "first": {**paths["first"], "amp_model": "PR12"},
            "second": {**paths["second"], "amp_model": "SW50R"},
        },
        "mix": {"guitar_target_lufs": -29.0, "master_target_lufs": -20.0,
                "peak_ceiling_dbtp": -1.0, "max_ab_lufs_delta": 3.0,
                "cycles": 1, "gap_s": .1},
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path, manifest


def _run(manifest, out):
    return subprocess.run([sys.executable, str(SCRIPT), "--manifest", str(manifest),
                           "--out-dir", str(out), "--seed", "17"],
                          cwd=ROOT, capture_output=True, text=True)


def test_backed_audio_uses_one_bed_and_scores_only_guitar(tmp_path):
    manifest_path, manifest = _fixture(tmp_path)
    out = tmp_path / "audition"
    done = _run(manifest_path, out)
    assert done.returncode == 0, done.stderr
    key = json.loads((out / "private-key.json").read_text())
    assert key["schema"] == "prospective-backed-audition-v1"
    assert set(key["blind_key"].values()) == {"first", "second"}
    assert key["manifest"]["sha256"] == sha256(manifest_path)
    assert key["output"]["sha256"] == sha256(out / "audition.flac")
    scored = key["objective_record"]
    assert scored["agreement"]["closer"]["status"] == "no_verdict"
    assert scored["agreement"]["preferred"]["status"] == "no_verdict"
    assert scored["objective_scoring"]["primary_excluded_audio_terms"] == ["level"]
    for label, role in key["blind_key"].items():
        assert scored["alternatives"][label]["path"] == manifest["alternatives"][role]["path"]

    audio = io.load(out / "audition.flac")
    assert audio.frames == round((3.0 + .2) * fx.SAMPLE_RATE)
    segments = {row["label"]: audio.samples[round(row["start_s"] * fx.SAMPLE_RATE):
                                              round(row["end_s"] * fx.SAMPLE_RATE), 0]
                for row in key["timeline"]}
    master = 10 ** (key["common_master_gain_db"] / 20)
    bed = io.load(manifest["backing"]["path"]).mono()[:fx.SAMPLE_RATE] * master
    for label, role in key["blind_key"].items():
        guitar = io.load(manifest["alternatives"][role]["path"]).mono()[:fx.SAMPLE_RATE]
        guitar *= 10 ** ((key["guitar_static_gain_db"][role] +
                          key["common_master_gain_db"]) / 20)
        assert segments[label] - guitar == pytest.approx(bed, abs=3e-6)
    assert key["output"]["true_peak_dbtp"] <= -0.98


def test_refuses_unproven_ac20_and_changed_audio(tmp_path):
    manifest_path, manifest = _fixture(tmp_path)
    manifest["alternatives"]["first"]["amp_model"] = "AC20"
    manifest_path.write_text(json.dumps(manifest))
    out = tmp_path / "audition"
    done = _run(manifest_path, out)
    assert done.returncode != 0 and "fresh-process record" in done.stderr
    assert not out.exists()
    manifest["alternatives"]["first"]["amp_model"] = "PR12"
    manifest["alternatives"]["first"]["sha256"] = "incorrect"
    manifest_path.write_text(json.dumps(manifest))
    done = _run(manifest_path, out)
    assert done.returncode != 0 and "SHA-256 changed" in done.stderr
    assert not out.exists()


def test_toneking_requires_exact_fresh_process_proof(tmp_path):
    from packs.loader import load_pack
    from tests.test_records import preset, record as binary_record

    pack = load_pack("toneking")

    def synthetic_state(channel):
        return preset(*(binary_record(
            spec.key, None if spec.key == "drive1Treble"
            else channel if spec.key == "ampType" else 0)
            for spec in pack.parameters.values()))

    manifest_path, manifest = _fixture(tmp_path)
    first = manifest["alternatives"]["first"]
    first.update({"pack": "toneking", "amp_model": "Lead Channel"})
    manifest_path.write_text(json.dumps(manifest))
    out = tmp_path / "audition"
    refused = _run(manifest_path, out)
    assert refused.returncode != 0 and "fresh-process record" in refused.stderr
    assert not out.exists()

    preset_path = tmp_path / "synthetic-toneking.xml"
    preset_path.write_bytes(synthetic_state(1))
    preset_sha = sha256(preset_path)
    proof = {"schema": "listening-fresh-render-v1", "pack": "toneking",
             "amp_model": "Lead Channel", "process_policy": "fresh",
             "state_source": "exact_preset_blob",
             "preset": {"path": str(preset_path), "sha256": preset_sha},
             "di": {"path": first["path"], "sha256": first["sha256"]},
             "state_preflight": {"schema": "toneking-state-preflight-v1",
                                 "source_sha256": preset_sha,
                                 "retained_sha256": preset_sha,
                                 "compared_valued_controls": len(pack.parameters) - 1,
                                 "compared_valueless_controls": 1},
             "renderer": {"renderer_build": "audio-unit-preset-renderer-test",
                          "quality_mode": f"process=fresh;state_template_sha256={preset_sha}"},
             "audio": {"path": first["path"], "sha256": first["sha256"]}}
    proof_path = tmp_path / "fresh-render.json"
    proof_path.write_text(json.dumps(proof))
    first["render_record"] = str(proof_path)
    manifest_path.write_text(json.dumps(manifest))
    built = _run(manifest_path, out)
    assert built.returncode == 0, built.stderr
    key = json.loads((out / "private-key.json").read_text())
    label = next(label for label, role in key["blind_key"].items() if role == "first")
    assert key["objective_record"]["render_provenance"][label]["pack"] == "toneking"
    assert key["objective_record"]["render_provenance"][label]["amp_model"] == "Lead Channel"

    proof["state_preflight"]["compared_valued_controls"] = 1
    proof_path.write_text(json.dumps(proof))
    rejected = _run(manifest_path, tmp_path / "wrong-count")
    assert rejected.returncode != 0 and "preflight does not match" in rejected.stderr
    proof["state_preflight"]["compared_valued_controls"] = len(pack.parameters) - 1

    proof["di"]["sha256"] = "incorrect"
    proof_path.write_text(json.dumps(proof))
    rejected = _run(manifest_path, tmp_path / "wrong-di")
    assert rejected.returncode != 0 and "exact preset state" in rejected.stderr
    proof["di"]["sha256"] = first["sha256"]

    preset_path.write_bytes(synthetic_state(0))
    wrong_channel_sha = sha256(preset_path)
    proof["preset"]["sha256"] = wrong_channel_sha
    proof["state_preflight"]["source_sha256"] = wrong_channel_sha
    proof["renderer"]["quality_mode"] = (
        f"process=fresh;state_template_sha256={wrong_channel_sha}")
    proof_path.write_text(json.dumps(proof))
    rejected = _run(manifest_path, tmp_path / "wrong-channel")
    assert rejected.returncode != 0 and "channel differs" in rejected.stderr

    preset_path.write_bytes(b"synthetic private preset fixture")
    invalid_sha = sha256(preset_path)
    proof["preset"]["sha256"] = invalid_sha
    proof["state_preflight"]["source_sha256"] = invalid_sha
    proof["renderer"]["quality_mode"] = f"process=fresh;state_template_sha256={invalid_sha}"
    proof_path.write_text(json.dumps(proof))
    rejected = _run(manifest_path, tmp_path / "invalid-preset")
    assert rejected.returncode != 0 and "valid preset" in rejected.stderr
    preset_path.write_bytes(synthetic_state(1))
    proof["preset"]["sha256"] = preset_sha
    proof["state_preflight"]["source_sha256"] = preset_sha
    proof["renderer"]["quality_mode"] = f"process=fresh;state_template_sha256={preset_sha}"

    proof["pack"] = "morgan"
    proof_path.write_text(json.dumps(proof))
    rejected = _run(manifest_path, tmp_path / "wrong-pack")
    assert rejected.returncode != 0 and "does not prove exact audio" in rejected.stderr
    proof["pack"] = "toneking"
    preset_path.write_bytes(b"changed")
    proof_path.write_text(json.dumps(proof))
    rejected = _run(manifest_path, tmp_path / "changed-preset")
    assert rejected.returncode != 0 and "exact preset state" in rejected.stderr


def test_rejects_loudness_confounded_pair_and_never_overwrites(tmp_path):
    manifest_path, manifest = _fixture(tmp_path)
    manifest["mix"]["max_ab_lufs_delta"] = 0.0
    manifest_path.write_text(json.dumps(manifest))
    out = tmp_path / "audition"
    done = _run(manifest_path, out)
    assert done.returncode != 0 and "loudness-confounded" in done.stderr
    assert not out.exists()
    manifest["mix"]["max_ab_lufs_delta"] = 3.0
    manifest_path.write_text(json.dumps(manifest))
    assert _run(manifest_path, out).returncode == 0
    original = (out / "audition.flac").read_bytes()
    refused = _run(manifest_path, out)
    assert refused.returncode != 0 and "immutable" in refused.stderr
    assert (out / "audition.flac").read_bytes() == original


def test_bad_crop_is_refused_before_any_output(tmp_path):
    manifest_path, manifest = _fixture(tmp_path)
    manifest["alternatives"]["second"]["start_s"] = 1.5
    manifest_path.write_text(json.dumps(manifest))
    out = tmp_path / "audition"
    done = _run(manifest_path, out)
    assert done.returncode != 0 and "less than" in done.stderr
    assert not out.exists()


def test_failed_key_write_does_not_claim_the_immutable_destination(tmp_path, monkeypatch):
    from scripts import build_backed_audition

    manifest_path, _ = _fixture(tmp_path)
    out = tmp_path / "audition"
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--manifest", str(manifest_path),
                                        "--out-dir", str(out), "--seed", "17"])

    def fail_key(*_args, **_kwargs):
        raise OSError("simulated key write failure")

    monkeypatch.setattr(build_backed_audition, "_write_text", fail_key)
    with pytest.raises(OSError, match="simulated key write failure"):
        build_backed_audition.main()
    assert not out.exists()
    assert not list(tmp_path.glob(".audition-*"))
    assert _run(manifest_path, out).returncode == 0


def test_listener_answers_bind_to_frozen_scores_without_rescoring(tmp_path):
    manifest_path, _ = _fixture(tmp_path)
    out = tmp_path / "audition"
    assert _run(manifest_path, out).returncode == 0
    key_path = out / "private-key.json"
    key = json.loads(key_path.read_text())
    submitted = subprocess.run(
        [sys.executable, str(VERDICT_SCRIPT), "--key", str(key_path),
         "--closer", "A", "--preferred", "B", "--notes", "separate questions"],
        cwd=ROOT, capture_output=True, text=True)
    assert submitted.returncode == 0, submitted.stderr
    record = json.loads((out / "verdict.json").read_text())
    assert record["audition_key"]["sha256"] == sha256(key_path)
    assert record["verdict"] == {"closer": "A", "preferred": "B"}
    assert record["frozen_scored_record"]["objective_scoring"] == key["objective_record"]["objective_scoring"]
    assert record["frozen_scored_record"]["agreement"]["closer"]["status"] in (
        "agree", "disagree", "unequal_coverage", "objective_tie")
    assert record["frozen_scored_record"]["agreement"]["preferred"]["status"] in (
        "agree", "disagree", "unequal_coverage", "objective_tie")
    again = subprocess.run(
        [sys.executable, str(VERDICT_SCRIPT), "--key", str(key_path),
         "--closer", "B", "--preferred", "A"],
        cwd=ROOT, capture_output=True, text=True)
    assert again.returncode != 0 and "never overwrite" in again.stderr
    assert json.loads((out / "verdict.json").read_text())["verdict"]["closer"] == "A"


def test_simultaneous_verdict_publication_cannot_replace_the_first(tmp_path, monkeypatch):
    from scripts import log_backed_verdict

    destination = tmp_path / "verdict.json"
    original_write = log_backed_verdict._write_text
    both_staged = threading.Barrier(2)

    def staged_write(path, content):
        original_write(path, content)
        both_staged.wait(timeout=5)

    monkeypatch.setattr(log_backed_verdict, "_write_text", staged_write)

    def publish(answer):
        try:
            log_backed_verdict._publish_verdict(destination, answer)
            return answer
        except ValueError as error:
            assert "never overwrite" in str(error)
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(publish, ("A", "B")))
    assert sorted(outcomes, key=lambda value: value or "") in ([None, "A"], [None, "B"])
    assert destination.read_text() in ("A", "B")
    assert destination.read_text() in outcomes


def test_full_original_cannot_masquerade_as_guitar_removed_backing(tmp_path):
    manifest_path, manifest = _fixture(tmp_path)
    manifest["backing"].pop("guitar_removed")
    manifest_path.write_text(json.dumps(manifest))
    out = tmp_path / "audition"
    refused = _run(manifest_path, out)
    assert refused.returncode != 0 and "guitar_removed=true" in refused.stderr
    manifest["backing"]["guitar_removed"] = True
    manifest["backing"]["path"] = manifest["reference"]["path"]
    manifest["backing"]["sha256"] = manifest["reference"]["sha256"]
    manifest_path.write_text(json.dumps(manifest))
    refused = _run(manifest_path, out)
    assert refused.returncode != 0 and "same file" in refused.stderr
    assert not out.exists()


def test_output_must_be_private_and_verdict_checks_the_heard_audio(tmp_path):
    manifest_path, _ = _fixture(tmp_path)
    repository = tmp_path / "public-repo"
    repository.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    refused = _run(manifest_path, repository / "audition")
    assert refused.returncode != 0 and "not Git-ignored" in refused.stderr
    assert not (repository / "audition").exists()

    out = tmp_path / "private-audition"
    assert _run(manifest_path, out).returncode == 0
    (out / "audition.flac").write_bytes(b"changed")
    verdict = subprocess.run(
        [sys.executable, str(VERDICT_SCRIPT), "--key", str(out / "private-key.json"),
         "--closer", "A", "--preferred", "none"],
        cwd=ROOT, capture_output=True, text=True)
    assert verdict.returncode != 0 and "changed" in verdict.stderr
    assert not (out / "verdict.json").exists()
