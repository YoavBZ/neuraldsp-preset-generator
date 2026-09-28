"""The declared multitrack crop rules, without touching held-out or licensed audio."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

np = pytest.importorskip("numpy", reason="needs the analysis extra")
sf = pytest.importorskip("soundfile", reason="needs the analysis extra")
pytest.importorskip("pyloudnorm", reason="needs the analysis extra")

from analysis import io
from scripts.build_backed_audition import build as build_backed
from scripts.build_validation_crops import build

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_validation_crops.py"
RATE = io.SAMPLE_RATE


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path, *, split="development"):
    data_root = tmp_path / "datasets"
    session_dir = data_root / "test" / "song"
    session_dir.mkdir(parents=True)
    seconds = 12
    frames = seconds * RATE
    t = np.arange(frames) / RATE
    reference = np.sin(2 * np.pi * 220 * t).astype(np.float32)
    reference *= np.where(t < 2, .05, np.where(t < 10, .1, .8)).astype(np.float32)
    stems = {
        "reference.wav": reference,
        "other-mic.wav": np.full(frames, .05, np.float32),
        "own-di.wav": np.full(frames, .9, np.float32),
        "other-di.wav": np.full(frames, .8, np.float32),
        "other-amp.wav": np.full(frames, .2, np.float32),
        "bass-di.wav": np.full(frames, .01, np.float32),
        "short-stereo.wav": np.column_stack((np.full(5 * 44100, .2, np.float32),
                                                np.full(5 * 44100, .4, np.float32))),
        "long.wav": np.full(13 * RATE, .03, np.float32),
    }
    for name, samples in stems.items():
        sf.write(session_dir / name, samples,
                 44100 if name == "short-stereo.wav" else RATE, subtype="FLOAT")
    catalog = {
        "schema": "validation-datasets-2", "root": str(data_root),
        "sessions": [{"source": "test", "song": "song", "path": "test/song",
                      "split": split,
                      "files": {name: _digest(session_dir / name) for name in stems},
                      "parts": [
                          {"part": "one", "reference": "reference.wav",
                           "alternate": ["other-mic.wav"], "di": "own-di.wav",
                           "usable": True},
                          {"part": "two", "reference": "other-amp.wav",
                           "alternate": [], "di": "other-di.wav", "usable": True},
                      ]}]}
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog))
    return catalog_path, data_root, session_dir


def _run(catalog, data_root, out_dir):
    return build(catalog, data_root, "test", "song", "one", out_dir)


def _declaration_repo(tmp_path, *, parts=("test/song/one",)):
    repo = tmp_path / "declaration-repo"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    path = docs / "prospective-test.md"
    path.write_text("# Synthetic declared test\n\n```json\n" + json.dumps({
        "schema": "held-out-listening-test-v1", "test_id": "synthetic-01",
        "parts": list(parts)}) + "\n```\n")
    subprocess.run(["git", "-C", str(repo), "add", "docs/prospective-test.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Synthetic Test",
                    "-c", "user.email=synthetic@example.invalid", "commit", "-qm",
                    "declare synthetic test"], check=True)
    return repo, path


def test_builds_exact_unity_mix_and_backing_with_one_shared_excerpt(tmp_path):
    catalog, data_root, session_dir = _fixture(tmp_path)
    out = tmp_path / "private-crops"
    _run(catalog, data_root, out)
    record = json.loads((out / "record.json").read_text())
    assert record["schema"] == "validation-crops-1"
    assert record["excerpt_start_s"] == 2.0
    assert record["excerpt_duration_s"] == 10.0
    assert record["session_frames"] == 12 * RATE
    assert record["excluded_guitar_dis"] == ["other-di.wav", "own-di.wav"]
    assert record["removed_own_amp_tracks"] == ["other-mic.wav", "reference.wav"]
    assert set(record["included_mix_tracks"]) == {
        "reference.wav", "other-mic.wav", "other-amp.wav", "bass-di.wav",
        "short-stereo.wav", "long.wav"}
    assert record["verified_source_sha256"]["reference.wav"] == _digest(
        session_dir / "reference.wav")
    assert set(record["outputs"]) == {"di", "reference", "mix", "backing"}
    for role, entry in record["outputs"].items():
        path = pathlib.Path(entry["path"])
        assert path == out / f"{role}.wav"
        assert _digest(path) == entry["sha256"]
        assert io.load(path).frames == 10 * RATE

    reference = io.load(out / "reference.wav").mono()
    mix = io.load(out / "mix.wav").mono()
    backing = io.load(out / "backing.wav").mono()
    di = io.load(out / "di.wav").mono()
    assert np.allclose(di, .9)
    # The reference and its second microphone are the only tracks removed;
    # the other guitar, bass DI, and short stereo stem remain.
    assert np.allclose(mix - backing, reference + .05, atol=2e-6)
    # Polyphase resampling has a small periodic ripple even on a constant
    # source; compare to the repository loader, not an idealized constant.
    stereo_at_three = io.load(session_dir / "short-stereo.wav").mono()[3 * RATE]
    assert backing[RATE] == pytest.approx(.2 + .01 + stereo_at_three + .03, abs=2e-6)
    assert backing[4 * RATE] == pytest.approx(.2 + .01 + .03, abs=2e-6)
    assert np.max(np.abs(backing)) < 1
    # A second publication may not silently replace the private record.
    with pytest.raises(ValueError, match="new private output directory"):
        _run(catalog, data_root, out)


def test_refuses_held_out_before_opening_any_audio(tmp_path):
    catalog, data_root, session_dir = _fixture(tmp_path, split="held_out")
    for path in session_dir.glob("*.wav"):
        path.unlink()
    out = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="held-out material"):
        _run(catalog, data_root, out)
    assert not out.exists()


def test_held_out_requires_unchanged_committed_declaration_for_exact_part(tmp_path):
    catalog, data_root, _ = _fixture(tmp_path, split="held_out")
    repo, declaration = _declaration_repo(tmp_path)
    out = tmp_path / "private-crops"
    record = build(catalog, data_root, "test", "song", "one", out,
                   declaration, declaration_repo=repo)
    proof = record["declaration"]
    assert proof["path"] == "docs/prospective-test.md"
    assert proof["test_id"] == "synthetic-01"
    assert proof["commit"] == proof["head_commit"]
    assert proof["sha256"] == _digest(declaration)
    assert json.loads((out / "record.json").read_text())["declaration"] == proof


def test_synthetic_held_out_crops_feed_backed_audition_with_fresh_di_proofs(tmp_path):
    catalog, data_root, _ = _fixture(tmp_path, split="held_out")
    repo, declaration = _declaration_repo(tmp_path)
    crop_dir = tmp_path / "crops"
    crops = build(catalog, data_root, "test", "song", "one", crop_dir,
                  declaration, declaration_repo=repo)
    frames = crops["outputs"]["di"]["frames"]
    t = np.arange(frames) / RATE
    alternatives = {}
    for role, hz, amp in (("first", 440, "PR12"), ("second", 660, "SW50R")):
        audio_path = tmp_path / f"{role}.wav"
        sf.write(audio_path, .02 * np.sin(2 * np.pi * hz * t), RATE, subtype="FLOAT")
        proof_path = tmp_path / f"{role}.render.json"
        proof_path.write_text(json.dumps({
            "schema": "listening-fresh-render-v1", "pack": "morgan",
            "amp_model": amp, "process_policy": "fresh",
            "renderer": {"quality_mode": "process=fresh"},
            "di": crops["outputs"]["di"],
            "audio": {"path": str(audio_path), "sha256": _digest(audio_path)},
        }))
        alternatives[role] = {"path": str(audio_path), "sha256": _digest(audio_path),
                              "start_s": 0, "pack": "morgan", "amp_model": amp,
                              "render_record": str(proof_path)}
    manifest = {
        "schema": "prospective-backed-listening-v1", "id": "synthetic-01-one",
        "target_id": "test/song", "declared_test_id": "synthetic-01",
        "validation_crop_record": str(crop_dir / "record.json"),
        "reference": {**crops["outputs"]["mix"], "start_s": 0,
                      "duration_s": 10, "regime": "mix"},
        "backing": {**crops["outputs"]["backing"], "start_s": 0,
                    "gain_db": 0, "guitar_removed": True},
        "alternatives": alternatives,
        "mix": {"guitar_target_lufs": -29, "master_target_lufs": -20,
                "peak_ceiling_dbtp": -1, "max_ab_lufs_delta": 3,
                "gap_s": .1, "cycles": 1},
    }
    montage, evidence = build_backed(manifest, seed=17)
    assert len(montage) > 30 * RATE
    assert evidence["objective_profiles_frozen"] == ["unpaired-v1", "unpaired-v2"]
    assert evidence["validation_crop_record"]["declaration"]["test_id"] == "synthetic-01"
    assert evidence["objective_record"]["reference"]["regime"] == "mix"
    assert evidence["source_paths"]["reference"] == crops["outputs"]["mix"]["path"]
    assert evidence["source_paths"]["backing"] == crops["outputs"]["backing"]["path"]
    for label, role in evidence["blind_key"].items():
        assert evidence["objective_record"]["render_provenance"][label]["process_policy"] == "fresh"
        assert role in alternatives

    no_proof = {**manifest, "alternatives": {**alternatives,
                "second": {key: value for key, value in alternatives["second"].items()
                           if key != "render_record"}}}
    with pytest.raises(ValueError, match="fresh-process render record from the crop DI"):
        build_backed(no_proof, seed=17)
    wrong_mix = {**manifest, "reference": {**manifest["reference"],
                 "path": crops["outputs"]["reference"]["path"],
                 "sha256": crops["outputs"]["reference"]["sha256"]}}
    with pytest.raises(ValueError, match="whole mix and unchanged backing"):
        build_backed(wrong_mix, seed=17)

    proof_path = pathlib.Path(alternatives["first"]["render_record"])
    original_proof = proof_path.read_text()
    wrong_di = json.loads(original_proof)
    wrong_di["di"]["sha256"] = "wrong"
    proof_path.write_text(json.dumps(wrong_di))
    with pytest.raises(ValueError, match="not freshly rendered from this crop DI"):
        build_backed(manifest, seed=17)
    proof_path.write_text(original_proof)
    manifest["declared_test_id"] = "a different test"
    with pytest.raises(ValueError, match="crop's declared_test_id"):
        build_backed(manifest, seed=17)


@pytest.mark.parametrize("change, message", [
    ("wrong-part", "does not name exact part"),
    ("unstaged", "differs from its committed HEAD"),
    ("staged", "differs from its committed HEAD"),
    ("untracked", "committed regular file"),
    ("outside-docs", "regular docs/\\*.md"),
    ("symlink", "regular docs/\\*.md"),
])
def test_held_out_rejects_unapproved_declarations_before_audio(tmp_path, change, message):
    catalog, data_root, session_dir = _fixture(tmp_path, split="held_out")
    repo, declaration = _declaration_repo(
        tmp_path, parts=("test/song/two",) if change == "wrong-part" else ("test/song/one",))
    if change in ("unstaged", "staged"):
        declaration.write_text(declaration.read_text() + "\nchanged after commit\n")
        if change == "staged":
            subprocess.run(["git", "-C", str(repo), "add", "docs/prospective-test.md"],
                           check=True)
    elif change == "untracked":
        declaration = repo / "docs" / "new-test.md"
        declaration.write_text("```json\n" + json.dumps({
            "schema": "held-out-listening-test-v1", "test_id": "untracked",
            "parts": ["test/song/one"]}) + "\n```\n")
    elif change == "outside-docs":
        declaration = repo / "other.md"
        declaration.write_text("not a docs declaration")
    elif change == "symlink":
        link = repo / "docs" / "linked.md"
        link.symlink_to(declaration)
        declaration = link
    for path in session_dir.glob("*.wav"):
        path.unlink()
    out = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match=message):
        build(catalog, data_root, "test", "song", "one", out,
              declaration, declaration_repo=repo)
    assert not out.exists()


@pytest.mark.parametrize("invalid", ("duplicate", "malformed"))
def test_held_out_refuses_ambiguous_or_malformed_committed_block(tmp_path, invalid):
    catalog, data_root, session_dir = _fixture(tmp_path, split="held_out")
    repo, declaration = _declaration_repo(tmp_path)
    original = declaration.read_text()
    block = original.split("```json\n", 1)[1].split("\n```", 1)[0]
    if invalid == "duplicate":
        declaration.write_text(original + "\n```json\n" + block + "\n```\n")
        expected = "exactly one"
    else:
        declaration.write_text(original.replace(block, block[:-1]))
        expected = "JSON is invalid"
    subprocess.run(["git", "-C", str(repo), "add", "docs/prospective-test.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Synthetic Test",
                    "-c", "user.email=synthetic@example.invalid", "commit", "-qm",
                    "alter synthetic declaration"], check=True)
    for path in session_dir.glob("*.wav"):
        path.unlink()
    out = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match=expected):
        build(catalog, data_root, "test", "song", "one", out,
              declaration, declaration_repo=repo)
    assert not out.exists()


def test_refuses_changed_source_hash_and_keeps_output_absent(tmp_path):
    catalog, data_root, session_dir = _fixture(tmp_path)
    with (session_dir / "reference.wav").open("ab") as stream:
        stream.write(b"changed")
    out = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="source hash differs"):
        _run(catalog, data_root, out)
    assert not out.exists()


def test_refuses_catalog_path_escape(tmp_path):
    catalog_path, data_root, _ = _fixture(tmp_path)
    catalog = json.loads(catalog_path.read_text())
    catalog["sessions"][0]["path"] = "../../outside"
    catalog_path.write_text(json.dumps(catalog))
    out = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="paths must be relative"):
        _run(catalog_path, data_root, out)
    assert not out.exists()


def test_cli_is_pinned_to_committed_catalog_and_refuses_held_out(tmp_path):
    command = [sys.executable, str(SCRIPT), "--source", "telefunken",
               "--song", "57 Chevy", "--part", "GTR 1", "--out-dir",
               str(tmp_path / "must-not-exist")]
    done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert done.returncode != 0
    assert "held-out material" in done.stderr
    assert not (tmp_path / "must-not-exist").exists()

    with_override = subprocess.run([*command, "--catalog", str(tmp_path / "fake.json")],
                                   cwd=ROOT, capture_output=True, text=True)
    assert with_override.returncode != 0
    assert "unrecognized arguments: --catalog" in with_override.stderr
