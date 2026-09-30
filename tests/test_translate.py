"""Human <-> binary value translation, per parameter kind."""

from __future__ import annotations

import pytest

from format.parser import parse_file
from format.structured import build
from format.translate import describe, from_binary, to_binary
from packs.loader import detect_pack, list_packs
from packs.paths import all_presets


def test_rotation_percent_to_fraction():
    assert to_binary("rotation", 50) == "0.5"
    assert to_binary("rotation", 62) == "0.62"
    assert to_binary("rotation", 0) == "0"
    assert to_binary("rotation", 100) == "1"


def test_rotation_out_of_range_rejected():
    with pytest.raises(ValueError):
        to_binary("rotation", 120)
    with pytest.raises(ValueError):
        to_binary("rotation", -5)


def test_rotation_roundtrip():
    assert from_binary("rotation", "0.62") == 62.0
    assert describe("rotation", "0.5") == "50%"


def test_metered_passthrough():
    assert to_binary("metered", -70, "db") == "-70"
    assert to_binary("metered", 5027.64, "hz") == "5027.64"
    assert to_binary("metered", 120, "bpm") == "120"
    assert describe("metered", "-70.0205", "db") == "-70.0205 db"


def test_fraction_passthrough_and_bounds():
    assert to_binary("fraction", 0.3) == "0.3"
    with pytest.raises(ValueError):
        to_binary("fraction", 1.5)


def test_switch_forms():
    assert to_binary("switch", True) == "true"
    assert to_binary("switch", False) == "false"
    assert to_binary("switch", "on") == "true"
    assert to_binary("switch", "off") == "false"
    assert from_binary("switch", "true") is True
    assert from_binary("switch", "1") is True
    assert from_binary("switch", "0") is False
    assert describe("switch", "1") == "on"
    assert describe("switch", "0") == "off"


def test_enum_int():
    assert to_binary("enum", 2) == "2"
    assert to_binary("enum", 1.0) == "1"


def test_every_real_value_roundtrips_through_human():
    """Every value in every preset we can see must survive
    binary -> human -> binary unchanged.

    This runs against real stored values and the committed manifest, so it
    covers whatever presets the user has added as well as the bundled example.
    A lossy conversion here would silently alter a preset on any edit.
    """
    checked = 0
    for preset_path in all_presets(list_packs()):
        preset = build(parse_file(str(preset_path)))
        pack = detect_pack(preset.file_header)
        if pack is None:
            continue
        for param in preset.parameters:
            spec = pack.get(param.module_path, param.key)
            if spec is None or spec.kind in ("path", "string"):
                continue
            human = from_binary(spec.kind, param.value, spec.unit)
            # Use the pack contract, not the format-only default: record-format
            # packs can store a switch as numeric 1/0 instead of text true/false.
            back = pack.to_stored(spec, human, warnings=[])
            if spec.kind in ("rotation", "fraction", "metered"):
                assert abs(float(back) - float(param.value)) < 1e-6, (
                    f"{preset_path.name} {spec.path} {spec.kind}: "
                    f"{param.value} -> {human} -> {back}"
                )
            else:
                assert back == param.value, (
                    f"{preset_path.name} {spec.path} {spec.kind}: "
                    f"{param.value} -> {back}"
                )
            checked += 1
    assert checked > 100, f"only checked {checked} values — is samples/ empty?"


def test_non_finite_values_display_but_are_never_written():
    """A binary plugin can store inf, and the parser keeps it on purpose. Showing
    it must not fail; writing one from a spec must be refused in words."""
    assert describe("metered", "inf", "dB") == "inf dB"
    assert describe("rotation", "nan") == "nan%"
    for value in ("inf", "-inf", "nan", float("inf")):
        with pytest.raises(ValueError, match="finite"):
            to_binary("metered", value)


def test_show_lists_a_preset_with_one_unreadable_value(tmp_path):
    """One value that does not read as its kind used to stop show.py outright,
    naming neither the value nor the parameter — and every skill runs it first."""
    import json
    import pathlib
    import subprocess
    import sys

    from format.structured import set_parameter
    from format.writer import write_file

    root = pathlib.Path(__file__).resolve().parents[1]
    preset = build(parse_file(str(root / "samples" / "Example_Clean_PR12.xml")))
    set_parameter(preset, "delay", "delayTime", "")
    odd = tmp_path / "odd.xml"
    write_file(str(odd), preset.tokens)

    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "show.py"), str(odd),
         "--data-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    rows = {(p["module"], p["key"]): p for p in json.loads(result.stdout)["parameters"]}
    odd_row = rows[("delay", "delayTime")]
    assert odd_row["display"] == "" and "does not read as metered" in odd_row["unreadable"]
    assert rows[("delay", "delayFeedback")]["display"].endswith("%"), (
        "every other parameter must still be read normally"
    )
