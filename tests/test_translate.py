"""Human <-> binary value translation, per parameter kind."""

from __future__ import annotations

import pathlib

import pytest

from format.translate import describe, from_binary, to_binary
from schema.loader import SCHEMA_PATH, index_by_key, load_schema

# The real schema is generated from whatever presets you supply, so it is
# git-ignored. Fall back to a minimal committed fixture covering every
# translatable kind, so this file passes on a fresh clone.
FIXTURE_SCHEMA = pathlib.Path(__file__).parent / "fixtures" / "schema_min.json"


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


def test_every_factory_value_roundtrips_through_human():
    """For each real value in the schema, binary -> human -> binary should be
    stable for the kinds where that is well-defined (rotation/fraction/switch/
    enum/metered with integer-ish values)."""
    schema = load_schema() if SCHEMA_PATH.exists() else load_schema(FIXTURE_SCHEMA)
    idx = index_by_key(schema)
    for (mod, key), meta in idx.items():
        kind = meta["kind"]
        if kind in ("path", "string", "unknown"):
            continue
        for stored in meta["observed_values"]:
            human = from_binary(kind, stored, meta.get("unit"))
            back = to_binary(kind, human, meta.get("unit"))
            # Compare numerically where applicable to avoid format noise.
            if kind in ("rotation", "fraction", "metered"):
                assert abs(float(back) - float(stored)) < 1e-6, (
                    f"{mod}/{key} {kind}: {stored} -> {human} -> {back}"
                )
            else:
                assert back == stored, f"{mod}/{key} {kind}: {stored} -> {back}"
