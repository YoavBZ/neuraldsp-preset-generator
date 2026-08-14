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
    assert [path.volume_control for path in controls.values()] == [
        "ac20Amp/ac20Volume",
        "pr12Amp/pr12Volume",
        "sw50rAmp/sw50rVolume",
    ]


def test_legacy_output_gain_must_declare_db_units():
    import dataclasses

    from packs.calibration import CalibrationError, signal_paths

    pack = load_pack("morgan")
    parameters = dict(pack.parameters)
    parameters["parameters/outputGain"] = dataclasses.replace(
        parameters["parameters/outputGain"], unit=None,
    )
    clone = dataclasses.replace(pack, parameters=parameters)

    with pytest.raises(CalibrationError, match="unit 'db'"):
        signal_paths(clone)


def test_tone_king_exposes_both_flat_namespace_channels():
    controls = drive._volume_controls(load_pack("toneking"), None)
    assert list(controls) == ["rhythm", "lead"]
    assert [path.volume_control for path in controls.values()] == [
        "/rhythmAmpVolume",
        "/leadAmpVolume",
    ]
    assert controls["rhythm"].settings["/ampType"] == "Rhythm Channel"
    assert controls["lead"].settings["/ampType"] == "Lead Channel"
    assert controls["rhythm"].selection_settings == {
        "/ampType": "Rhythm Channel"
    }
    assert controls["lead"].selection_settings == {
        "/ampType": "Lead Channel"
    }
    for path in controls.values():
        assert path.settings["/delayActive"] == "Inactive"
        assert path.settings["/reverbActive"] == "Inactive"
        assert path.settings["/ampReverb"] == 0.0
        assert path.settings["/ampTremoloDepth"] == 0.0
        assert path.settings["/inputGain"] == 0.0
        assert load_pack("toneking").parameters[
            path.output_gain_control
        ].unit == "db"


def test_signal_path_selection_accepts_stored_and_display_values():
    from packs.calibration import selected_signal_path

    pack = load_pack("toneking")
    assert selected_signal_path(pack, {"ampType": "Lead Channel"}) == "lead"
    assert selected_signal_path(pack, {("", "ampType"): "1"}) == "lead"
    assert selected_signal_path(pack, {"/ampType": 0}) == "rhythm"
    assert selected_signal_path(pack, {}) is None


def test_path_local_calibration_setup_is_not_treated_as_a_selector():
    import copy
    import dataclasses

    from packs.calibration import signal_paths

    pack = load_pack("toneking")
    calibration = copy.deepcopy(pack.calibration)
    calibration["signal_paths"]["lead"]["settings"] = {
        "/leadAmpTone": 0.5,
    }
    clone = dataclasses.replace(pack, calibration=calibration)

    lead = signal_paths(clone)["lead"]
    assert lead.settings["/leadAmpTone"] == 0.5
    assert lead.selection_settings == {"/ampType": "Lead Channel"}


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


def test_percent_positions_follow_each_controls_human_scale():
    morgan = load_pack("morgan").parameters["pr12Amp/pr12Volume"]
    toneking = load_pack("toneking").parameters["/rhythmAmpVolume"]
    assert drive._position_value(morgan, 60.0) == 60.0
    assert drive._position_value(toneking, 60.0) == pytest.approx(0.6)


def test_an_exact_repeat_has_a_json_safe_zero_error(tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    path = tmp_path / "same.wav"
    sf.write(path, np.linspace(-0.1, 0.1, 4096, dtype=np.float32), 48000,
             subtype="FLOAT")

    difference = drive._difference(path, path)

    assert difference["relative_error_db"] is None
    assert difference["max_abs_difference"] == 0.0
    assert difference["max_band_difference_db"] == 0.0


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


def test_tone_king_dry_run_names_both_channels_without_a_plugin():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "measure_drive_curve.py"),
         "--pack", "toneking", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "80 grid renders + 2 exact-repeat checks" in result.stdout
    assert "rhythm: /rhythmAmpVolume" in result.stdout
    assert "lead: /leadAmpVolume" in result.stdout
