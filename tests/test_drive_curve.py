"""Plugin-free checks for the drive-curve measurement command."""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

from packs.loader import load_pack
from scripts import measure_drive_curve as drive


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_morgan_exposes_one_volume_control_per_amp():
    controls = drive._volume_controls(load_pack("morgan"), None)
    assert list(controls) == ["ac20", "pr12", "sw50r"]
    assert [spec.path for spec in controls.values()] == [
        "ac20Amp/ac20Volume",
        "pr12Amp/pr12Volume",
        "sw50rAmp/sw50rVolume",
    ]


def test_the_default_grid_is_the_planned_forty_points_per_amp():
    assert drive._levels(drive.DEFAULT_LEVELS) == [0.015, 0.05, 0.15, 0.3]
    assert drive._positions(drive.DEFAULT_POSITIONS) == [
        10.0, 20.0, 30.0, 40.0, 50.0,
        60.0, 70.0, 80.0, 90.0, 100.0,
    ]


def test_the_frequency_must_be_an_exact_analysis_bin():
    assert drive._frequency(222.65625) == 222.65625
    with pytest.raises(SystemExit):
        drive._frequency(220.0)


def test_the_one_shot_command_puts_every_render_fact_in_argv(tmp_path):
    command = drive._command(
        tmp_path / "au_render",
        {"type": "aumf", "subtype": "NMAS", "manufacturer": "NDSP"},
        "pr12Amp/pr12Volume",
        "0.6",
        tmp_path / "out.wav",
        0.05,
        222.65625,
        200.0,
        -6.0,
    )
    assert command == [
        str(tmp_path / "au_render"), "aumf", "NMAS", "NDSP",
        "pr12Amp/pr12Volume", "0.6", str(tmp_path / "out.wav"),
        "0.05", "sine:222.65625", "--settle", "200", "--output-gain", "-6",
    ]


def test_dry_run_needs_no_plugin_and_names_the_fresh_process_policy():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "measure_drive_curve.py"),
         "--pack", "morgan", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "120 grid renders + 3 exact-repeat checks" in result.stdout
    assert "one fresh plugin process per render" in result.stdout
    assert "drive_curve.json" in result.stdout
