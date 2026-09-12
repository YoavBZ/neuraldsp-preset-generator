"""A known preset render becomes durable paired-DI validation evidence."""

from __future__ import annotations

import hashlib
import json
import pathlib
import shlex
import subprocess
import sys

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("soundfile", reason="needs the analysis extra")

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "samples" / "Example_Clean_PR12.xml"


def run(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "render_paired_reference.py"),
         *map(str, args)],
        cwd=ROOT, capture_output=True, text=True,
    )


def test_a_paired_reference_records_the_exact_inputs_and_render(tmp_path):
    import numpy as np
    from analysis import io
    from match import invert
    from match import space as space_module
    from match.renderer import _hash_audio
    from match.renderer_synth import SyntheticRenderer
    from scripts._cli import renderer_paths
    from scripts.match_preset import _seed_from_template
    from scripts.render_paired_reference import _settings
    from tests import fixtures_audio as fx

    di = fx.plucks(seconds=2.0, gap=0.9, seed=91)
    stereo_di = np.column_stack([di, di * 0.5])
    probe = tmp_path / "dry guitar.wav"
    output = tmp_path / "paired reference.wav"
    fx.write_wav(str(probe), stereo_di)
    completed = run(
        "--preset", TEMPLATE, "--probe-di", probe, "--out", output,
        "--pack", "morgan", "--amp", "sw50r", "--renderer", "synthetic",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    sidecar = pathlib.Path(str(output) + ".paired.json")
    document = json.loads(sidecar.read_text())
    assert document["schema"] == "paired-di-reference-1"
    assert document["preset"]["path"] == str(TEMPLATE.resolve())
    assert document["preset"]["sha256"] == hashlib.sha256(
        TEMPLATE.read_bytes()).hexdigest()
    assert document["probe_di"]["path"] == str(probe.resolve())
    assert document["reference"]["path"] == str(output.resolve())
    assert document["reference"]["sha256"] == hashlib.sha256(
        output.read_bytes()).hexdigest()
    assert document["renderer"]["renderer_id"] == "synthetic"

    renderer = SyntheticRenderer()
    space = space_module.build("morgan", amp="sw50r")
    values, _ = _seed_from_template(TEMPLATE, space, "morgan")
    values = invert.apply_to(
        values, invert.signal_path_selection("morgan", "sw50r"), space,
    )
    loaded_probe = io.load(str(probe), target_rate=renderer.metadata().sample_rate)
    expected = renderer.render(
        loaded_probe.mono(),
        _settings(space, values, renderer_paths(renderer)),
    ).audio
    actual = io.load(str(output)).samples
    assert np.allclose(actual, expected, atol=2e-7)
    assert document["probe_di"]["audio_sha256"] == _hash_audio(
        loaded_probe.mono())
    assert document["probe_di"]["source_channels"] == 2
    assert document["probe_di"]["canonical_channels"] == 1
    assert document["reference"]["audio_sha256"] == _hash_audio(expected)

    matched = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "match_preset.py"),
        "--template", str(TEMPLATE), "--reference", str(output),
        "--reference-mode", "paired_di", "--probe-di", str(probe),
        "--paired-provenance", str(sidecar), "--pack", "morgan",
        "--amp", "sw50r", "--renderer", "synthetic", "--budget", "60",
        "--shortlist", "1",
        "--out-dir", str(tmp_path / "run"),
    ], cwd=ROOT, capture_output=True, text=True)
    assert matched.returncode == 0, matched.stdout + matched.stderr
    # Follow the printed arguments literally, including spaces in paths.
    printed = completed.stdout.split("use these exact files with match_preset.py:\n", 1)[1]
    handoff = shlex.split(printed.replace("\\\n", " "))
    assert handoff[handoff.index("--paired-provenance") + 1] == str(sidecar)
    exported = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "export_match_audition.py"),
        "--run-dir", str(tmp_path / "run"), "--candidate", "1",
        "--probe-di", str(probe), "--renderer", "synthetic",
    ], cwd=ROOT, capture_output=True, text=True)
    assert exported.returncode == 0, exported.stdout + exported.stderr


def test_force_never_replaces_a_source_or_directory(tmp_path):
    from tests import fixtures_audio as fx

    probe = tmp_path / "probe.wav"
    fx.write_wav(str(probe), fx.plucks(seconds=2.0, gap=0.9, seed=92))
    before = probe.read_bytes()
    alias = run(
        "--preset", TEMPLATE, "--probe-di", probe, "--out", probe,
        "--pack", "morgan", "--renderer", "synthetic", "--force",
    )
    assert alias.returncode != 0
    assert "aliases the probe DI input" in alias.stderr
    assert probe.read_bytes() == before

    output = tmp_path / "reference.wav"
    provenance = tmp_path / "provenance"
    provenance.mkdir()
    occupied = run(
        "--preset", TEMPLATE, "--probe-di", probe, "--out", output,
        "--provenance", provenance, "--pack", "morgan",
        "--renderer", "synthetic", "--force",
    )
    assert occupied.returncode != 0
    assert "is a directory" in occupied.stderr
    assert not output.exists()
