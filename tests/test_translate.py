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
            back = to_binary(spec.kind, human, spec.unit)
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

