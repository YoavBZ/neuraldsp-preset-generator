"""Probe presets: valid, minimal, and self-labelling.

The probe workflow exists because the plugin never shows a selector's stored
integer. A probe preset must therefore be trustworthy: if it differs from the
template in anything but the name and the probed selector, the label the user
reads back means nothing.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
PROBE = REPO_ROOT / "scripts" / "probe.py"
EXAMPLE = REPO_ROOT / "samples" / "Example_Clean_PR12.xml"

from format.parser import parse, parse_file
from format.structured import build
from format.writer import write


def run_probe(*args, **kwargs):
    return subprocess.run(
        [sys.executable, str(PROBE), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        **kwargs,
    )


@pytest.fixture
def probes(tmp_path):
    result = run_probe(
        "--param", "delay/delaySyncNote", "--values", "0-3",
        "--out-dir", str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    return sorted(tmp_path.glob("*.xml"))


def test_writes_one_preset_per_value(probes):
    assert len(probes) == 4
    assert [p.name for p in probes] == [
        f"probe delaySyncNote {i:02d}.xml" for i in range(4)
    ]


def test_probe_presets_round_trip_byte_exact(probes):
    for path in probes:
        raw = path.read_bytes()
        assert write(parse(raw)) == raw, f"{path.name} does not round-trip"


def test_probe_differs_only_in_name_and_probed_selector(probes):
    """The whole point: any other difference invalidates what the user reads."""
    base = build(parse_file(str(EXAMPLE)))
    for path in probes:
        probe = build(parse_file(str(path)))
        differing = {
            key
            for key, param in probe.by_path.items()
            if key in base.by_path and base.by_path[key].value != param.value
        }
        assert differing <= {("", "name"), ("delay", "delaySyncNote")}, (
            f"{path.name} also changed {differing}"
        )


def test_preset_name_encodes_the_value(probes):
    """The plugin's browser is the label, so the name must carry the number."""
    for i, path in enumerate(probes):
        preset = build(parse_file(str(path)))
        assert preset.preset_name == f"probe delaySyncNote {i:02d}"
        assert preset.by_path[("delay", "delaySyncNote")].value == str(i)


def test_probing_a_non_selector_is_refused(tmp_path):
    result = run_probe(
        "--param", "delay/delayMix", "--values", "0-2", "--out-dir", str(tmp_path)
    )
    assert result.returncode == 2
    assert "not 'enum'" in result.stderr


def test_absurd_sweep_is_refused(tmp_path):
    result = run_probe(
        "--param", "delay/delaySyncNote", "--values", "0-200",
        "--out-dir", str(tmp_path),
    )
    assert result.returncode == 2
    assert "narrow it down" in result.stderr


def test_unknown_parameter_is_refused(tmp_path):
    result = run_probe(
        "--param", "delay/nope", "--values", "0", "--out-dir", str(tmp_path)
    )
    assert result.returncode == 2
    assert "not present" in result.stderr


def test_existing_probe_is_not_clobbered(tmp_path):
    args = ("--param", "delay/delaySyncNote", "--values", "1", "--out-dir", str(tmp_path))
    assert run_probe(*args).returncode == 0
    second = run_probe(*args)
    assert second.returncode == 2
    assert "--force" in second.stderr
    assert run_probe(*args, "--force").returncode == 0


def test_known_selector_shows_predictions(tmp_path):
    """Probing a selector we already know should predict, so a mismatch is
    obvious on the first load."""
    result = run_probe(
        "--param", "/selectedAmp", "--values", "0-2", "--out-dir", str(tmp_path)
    )
    assert result.returncode == 0
    assert "predicted: AC20" in result.stdout
    assert "predicted: SW50R" in result.stdout


def test_a_colliding_sweep_writes_nothing(tmp_path):
    """A half-written sweep is worse than none: probe presets are read by loading
    them in the plugin, so leftovers from an aborted run are misleading."""
    assert run_probe(
        "--param", "delay/delaySyncNote", "--values", "5", "--out-dir", str(tmp_path)
    ).returncode == 0
    before = {p.name for p in tmp_path.glob("*.xml")}

    result = run_probe(
        "--param", "delay/delaySyncNote", "--values", "0-9", "--out-dir", str(tmp_path)
    )
    assert result.returncode == 2
    assert "Nothing was written" in result.stderr
    assert {p.name for p in tmp_path.glob("*.xml")} == before, (
        "the aborted sweep must not leave partial output behind"
    )

    assert run_probe(
        "--param", "delay/delaySyncNote", "--values", "0-9",
        "--out-dir", str(tmp_path), "--force",
    ).returncode == 0
    assert len(list(tmp_path.glob("*.xml"))) == 10
