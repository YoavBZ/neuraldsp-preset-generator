"""The committed calibration files, checked without a plugin.

`packs/<pack>/eq_basis.json` is measured by `scripts/measure_eq_basis.py` against
the installed Audio Unit, which CI cannot run. What CI *can* do is keep checking
that the committed file still means what `match/invert.py` reads it as — the
shape, the units, the provenance — so a stale or hand-edited file is caught here
rather than by a fit that quietly solves against nonsense.

A file that does not exist is not a failure: a pack whose equaliser nobody has
measured yet falls back to textbook curves and says so. What is a failure is a
file that exists and does not line up.
"""

from __future__ import annotations

import json
import pathlib

import pytest

PACKS = pathlib.Path(__file__).resolve().parents[1] / "packs"
EQ_BASIS = sorted(PACKS.glob("*/eq_basis.json"))
DRIVE_CURVES = sorted(PACKS.glob("*/drive_curve.json"))


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", EQ_BASIS, ids=lambda p: p.parent.name)
def test_the_schema_is_one_this_repository_understands(path):
    """A consumer has to be able to refuse a shape rather than index into it."""
    assert _load(path)["schema"] == "eq-basis-1"


@pytest.mark.parametrize("path", EQ_BASIS, ids=lambda p: p.parent.name)
def test_every_row_is_one_band_against_every_analysis_centre(path):
    document = _load(path)
    centres = document["analysis_centres_hz"]
    assert centres == sorted(centres), "analysis centres must be in frequency order"
    for amp, rows in document["amps"].items():
        matrix = rows["basis_db_per_db"]
        assert len(matrix) == len(rows["band_centres_hz"]), (
            f"{amp}: {len(matrix)} rows for {len(rows['band_centres_hz'])} bands"
        )
        for index, row in enumerate(matrix):
            assert len(row) == len(centres), (
                f"{amp} row {index}: {len(row)} columns for {len(centres)} centres"
            )


@pytest.mark.parametrize("path", EQ_BASIS, ids=lambda p: p.parent.name)
def test_each_band_declares_the_centre_its_pack_declares(path):
    """The basis solves onto the manifest's centres, so it has to agree with them."""
    from packs.loader import load_pack

    document = _load(path)
    pack = load_pack(document["pack"])
    for amp, rows in document["amps"].items():
        controls = rows.get("band_controls") or [
            f"{amp}EQ/{amp}EQBand{index}"
            for index in range(1, len(rows["band_centres_hz"]) + 1)
        ]
        declared = []
        for control in controls:
            spec = pack.parameters.get(control)
            assert spec is not None, f"{control} is not declared"
            declared.append(float(spec.centre_hz))
        assert [float(c) for c in rows["band_centres_hz"]] == declared


@pytest.mark.parametrize("path", EQ_BASIS, ids=lambda p: p.parent.name)
def test_a_band_does_most_of_its_work_near_its_own_centre(path):
    """A row is dB per dB, so its own centre must move by roughly the gain.

    Loose on purpose: the real bands are shelves at the ends and overlap in the
    middle, which is the whole reason this file exists. What it catches is a row
    that is upside down, scaled by a hundred, or measured on the wrong band —
    the failures that would otherwise show up as a plausible-looking bad fit.
    """
    document = _load(path)
    centres = [float(c) for c in document["analysis_centres_hz"]]
    for amp, rows in document["amps"].items():
        for band, row in zip(rows["band_centres_hz"], rows["basis_db_per_db"]):
            nearest = min(range(len(centres)), key=lambda i: abs(centres[i] - band))
            # Within an octave of the band's own centre, something must respond.
            near = [value for centre, value in zip(centres, row)
                    if 0.5 <= centre / band <= 2.0]
            assert max(near) > 0.3, (
                f"{amp} band at {band:g} Hz peaks at {max(near):.3f} dB/dB near "
                f"its own centre — that is not a band being measured"
            )
            assert max(row) < 2.0, (
                f"{amp} band at {band:g} Hz reaches {max(row):.3f} dB/dB, which is "
                f"more than a graphic-EQ band can do per dB"
            )
            assert row[nearest] > 0.0, (
                f"{amp} band at {band:g} Hz is negative at its own centre — the "
                f"row is inverted"
            )


@pytest.mark.parametrize("path", EQ_BASIS, ids=lambda p: p.parent.name)
def test_the_file_says_what_measured_it_and_whether_that_repeats(path):
    """Never a committed number from a `reproducible=False` backend without it
    saying so beside it. Here that means in the file itself."""
    renderer = _load(path)["renderer"]
    assert renderer["renderer_id"]
    assert renderer["plugin_version"] not in ("", "n/a", "unknown"), (
        "a basis whose plugin version is unknown cannot be matched to a plugin"
    )
    assert "reproducible" in renderer
    if not renderer["reproducible"]:
        assert renderer["band_noise_db"] > 0.0, (
            "a backend that does not repeat itself has to say by how much"
        )
        measured = [
            float(rows["repeat_verification"]["max_band_difference_db"])
            for rows in _load(path)["amps"].values()
            if "repeat_verification" in rows
        ]
        if measured:
            assert float(renderer["band_noise_db"]) == max(measured)


@pytest.mark.parametrize("path", EQ_BASIS + DRIVE_CURVES, ids=lambda p: p.parent.name)
def test_current_batched_renderer_still_matches_its_measured_build(path):
    """A host edit changes provenance even if the plugin version stays put."""
    document = _load(path)
    recorded = document["renderer"].get("renderer_build", "")
    if not recorded.startswith("audio-unit-renderer-"):
        pytest.skip("legacy calibration predates AudioUnitRenderer build identities")

    from match.renderer_au import AudioUnitRenderer

    renderer = AudioUnitRenderer(document["pack"])
    try:
        assert renderer._renderer_build() == recorded
    finally:
        renderer.close()


@pytest.mark.parametrize("path", EQ_BASIS, ids=lambda p: p.parent.name)
def test_the_gain_it_was_measured_at_is_inside_the_declared_range(path):
    from packs.loader import load_pack

    document = _load(path)
    pack = load_pack(document["pack"])
    gain = float(document["gain_db"])
    assert gain > 0.0
    for amp, rows in document["amps"].items():
        control = (rows.get("band_controls") or [f"{amp}EQ/{amp}EQBand1"])[0]
        spec = pack.parameters[control]
        assert spec.min is not None and spec.max is not None
        assert spec.min <= -gain and gain <= spec.max, (
            f"{amp} was measured at ±{gain} dB, outside its declared "
            f"{spec.min}..{spec.max} dB"
        )


@pytest.mark.parametrize("path", EQ_BASIS, ids=lambda p: p.parent.name)
def test_invert_can_read_what_the_measurement_wrote(path):
    """The round trip that matters: the file is only worth having if the fit
    loads it. These are the two halves of one contract and they have been in two
    files since the day the format was invented."""
    pytest.importorskip("numpy")
    from match import invert

    document = _load(path)
    centres = [float(c) for c in document["analysis_centres_hz"]]
    for amp in document["amps"]:
        found = invert.measured_basis(document["pack"], amp, centres)
        assert found is not None, f"{amp} did not load"
        basis, note = found
        assert basis.shape == (len(document["amps"][amp]["band_centres_hz"]),
                               len(centres))
        assert "measured" in note


@pytest.mark.parametrize("path", EQ_BASIS, ids=lambda p: p.parent.name)
def test_a_frequency_that_was_never_measured_is_refused_not_guessed(path):
    """A stale file is a different problem from a missing one.

    Missing falls back to textbook curves with a caveat. A file that is present
    and does not cover the fit's frequencies is a measurement that no longer
    matches the analysis, and quietly ignoring it would hide that.
    """
    pytest.importorskip("numpy")
    from match import invert

    document = _load(path)
    amp = next(iter(document["amps"]))
    with pytest.raises(invert.InversionError, match="Re-run"):
        invert.measured_basis(document["pack"], amp, [1.234])


def test_a_basis_belongs_to_a_backend_not_to_a_pack():
    """The synthetic chain must not be fitted with the plugin's overlap.

    Both render Morgan's parameters, and only one of them is Morgan. Loading the
    file by pack alone made the synthetic chain's own EQ fit measurably worse,
    because it was being solved against a different equaliser's shape.
    """
    pytest.importorskip("numpy")
    from match.renderer_synth import SyntheticRenderer

    assert SyntheticRenderer().eq_basis("sw50r", [1000.0]) is None


@pytest.mark.parametrize("path", EQ_BASIS, ids=lambda p: p.parent.name)
def test_the_plugin_backend_offers_the_basis_it_measured(path):
    pytest.importorskip("numpy")
    from match.renderer_au import AudioUnitRenderer

    document = _load(path)
    centres = [float(c) for c in document["analysis_centres_hz"]]
    amp = next(iter(document["amps"]))
    # The backend checks that the installed plugin is the version this file was
    # measured against. Supply that authoritative answer without starting a server.
    renderer = AudioUnitRenderer(document["pack"])
    renderer._plugin_version = document["renderer"]["plugin_version"]
    renderer._ensure_server = lambda: None
    found = renderer.eq_basis(amp, centres)
    assert found is not None
    assert found[0].shape[1] == len(centres)


@pytest.mark.parametrize("path", EQ_BASIS, ids=lambda p: p.parent.name)
def test_a_basis_from_another_plugin_version_is_refused(path):
    pytest.importorskip("numpy")
    from match import invert

    document = _load(path)
    amp = next(iter(document["amps"]))
    centres = [float(c) for c in document["analysis_centres_hz"]]
    with pytest.raises(invert.InversionError, match="different plugin versions"):
        invert.measured_basis(
            document["pack"], amp, centres,
            expected_plugin_version="999.0.0",
        )


def test_committed_calibrations_ship_as_package_data():
    """A non-editable install must not silently lose the measured EQ basis."""
    project = (PACKS.parent / "pyproject.toml").read_text()
    package_data = project.split("[tool.setuptools.package-data]", 1)[1]
    assert '"*/eq_basis.json"' in package_data.split("\n[", 1)[0]
    assert '"*/drive_curve.json"' in package_data.split("\n[", 1)[0]


@pytest.mark.parametrize("path", DRIVE_CURVES, ids=lambda p: p.parent.name)
def test_drive_curve_schema_and_fresh_process_provenance(path):
    document = _load(path)
    assert document["schema"] == "drive-curve-1"
    assert document["process_policy"] == "one fresh plugin process per render"
    assert -24.0 <= float(document["output_gain_db"]) < 0.0
    renderer = document["renderer"]
    assert renderer["renderer_id"] in {"swift-one-shot", "swift"}
    assert renderer["plugin_version"] not in ("", "n/a", "unknown")
    assert isinstance(renderer["reproducible"], bool)
    if not renderer["reproducible"]:
        assert float(renderer["band_noise_db"]) > 0.0


@pytest.mark.parametrize("path", DRIVE_CURVES, ids=lambda p: p.parent.name)
def test_drive_curve_is_a_complete_input_level_surface(path):
    document = _load(path)
    levels = [float(value) for value in document["input_levels"]]
    positions = [float(value) for value in document["positions_percent"]]
    assert 3 <= len(levels) <= 4
    assert levels == sorted(set(levels)) and all(value > 0 for value in levels)
    assert positions == sorted(set(positions))
    assert positions[0] <= 10.0 and positions[-1] == 100.0

    from packs.loader import load_pack

    pack = load_pack(document["pack"])
    for amp, rows in document["amps"].items():
        assert rows["control"] in pack.parameters
        assert [float(curve["input_level"]) for curve in rows["curves"]] == levels
        for curve in rows["curves"]:
            points = curve["points"]
            assert [float(point["position_percent"]) for point in points] == positions
            for point in points:
                assert point["silent"] is False
                assert point["clipped"] is False
                assert float(point["output_peak"]) > 0.0
                assert float(point["thd_percent"]) >= 0.0


@pytest.mark.parametrize("path", DRIVE_CURVES, ids=lambda p: p.parent.name)
def test_each_drive_curve_proved_a_fresh_process_repeats(path):
    document = _load(path)
    exact_backend = document["renderer"]["reproducible"]
    repeats = []
    for amp, rows in document["amps"].items():
        repeat = rows["repeat_verification"]
        repeats.append(repeat)
        if exact_backend:
            assert repeat["byte_exact"] is True, f"{amp} fresh processes differed"
            assert repeat["sha256_first"] == repeat["sha256_repeat"]
        elif not repeat["byte_exact"]:
            assert repeat["sha256_first"] != repeat["sha256_repeat"]
            assert float(repeat["max_band_difference_db"]) > 0.0
    if not exact_backend:
        assert any(not repeat["byte_exact"] for repeat in repeats), (
            "reproducible=False has no differing repeat beside it"
        )


def test_an_absent_basis_is_a_fallback_not_an_error():
    pytest.importorskip("numpy")
    from match import invert

    assert invert.measured_basis("no-such-pack", "sw50r", [1000.0]) is None
