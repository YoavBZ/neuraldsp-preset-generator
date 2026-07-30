"""The pack manifest is the contract: completeness, agreement, and validation."""

from __future__ import annotations

import pathlib

import pytest

from format.parser import parse_file
from format.structured import build
from packs.loader import PackError, detect_pack, list_packs, load_pack
from packs.paths import all_presets

# Every preset this installation can see: the bundled example plus anything the
# user has added to their own template directories.
SAMPLE_FILES = all_presets(list_packs())

TRANSLATABLE_KINDS = {
    "rotation", "fraction", "metered", "switch", "enum", "path", "string",
}


@pytest.fixture(scope="module")
def pack():
    return load_pack("morgan")


def test_pack_is_discoverable(pack):
    assert "morgan" in list_packs()
    assert detect_pack("morgan").pack_id == "morgan"
    assert detect_pack("definitely-not-a-plugin") is None


def test_every_kind_is_translatable(pack):
    """A kind the translator doesn't understand would fail at write time."""
    for spec in pack.parameters.values():
        assert spec.kind in TRANSLATABLE_KINDS, f"{spec.path} has kind {spec.kind!r}"


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_manifest_covers_every_parameter_in_sample(sample, pack):
    """Any parameter present in a real preset must be described by the manifest,
    or the agent can neither read it nor write it."""
    preset = build(parse_file(str(sample)))
    missing = [
        f"{p.module_path}/{p.key}"
        for p in preset.parameters
        if pack.get(p.module_path, p.key) is None
    ]
    assert not missing, f"{sample.name} has parameters absent from the manifest: {missing}"


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_declared_ranges_admit_real_values(sample, pack):
    """A declared range that excludes a value from a real preset is a bug in the
    manifest, not in the preset. This is the guard against transcribing a wrong
    range from the config reference."""
    preset = build(parse_file(str(sample)))
    for p in preset.parameters:
        spec = pack.get(p.module_path, p.key)
        if spec is None or (spec.min is None and spec.max is None):
            continue
        try:
            value = float(p.value)
        except ValueError:
            continue
        lo = spec.min if spec.min is not None else float("-inf")
        hi = spec.max if spec.max is not None else float("inf")
        assert lo <= value <= hi, (
            f"{sample.name}: {spec.path}={value} is outside the manifest's "
            f"declared range [{spec.min}, {spec.max}] (source: {spec.range_source})"
        )


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_declared_enum_values_are_members(sample, pack):
    """Every selector value in a real preset must be a declared member."""
    preset = build(parse_file(str(sample)))
    for p in preset.parameters:
        spec = pack.get(p.module_path, p.key)
        if spec is None or spec.kind != "enum" or not spec.members:
            continue
        assert str(int(float(p.value))) in spec.members, (
            f"{sample.name}: {spec.path}={p.value} is not a declared member "
            f"({sorted(spec.members)})"
        )


# --- validation ------------------------------------------------------------


def test_enum_out_of_range_is_rejected(pack):
    spec = pack.require("", "selectedAmp")
    with pytest.raises(PackError, match="not a valid selector"):
        pack.to_stored(spec, 7)


def test_enum_accepts_member_name(pack):
    assert pack.to_stored(pack.require("", "selectedAmp"), "PR12") == "1"
    assert pack.to_stored(pack.require("", "selectedAmp"), "sw50r") == "2"
    assert pack.to_stored(pack.require("cabParameters", "rightMicType"), "Ribbon 121") == "8"


def test_enum_rejects_unknown_member_name(pack):
    with pytest.raises(PackError, match="unknown value"):
        pack.to_stored(pack.require("", "selectedAmp"), "Marshall JCM800")


def test_unknown_mic_index_is_rejected(pack):
    with pytest.raises(PackError, match="not a valid selector"):
        pack.to_stored(pack.require("cabParameters", "leftMicType"), 99)


def test_unconfirmed_selector_warns_but_writes(pack):
    warnings: list[str] = []
    spec = pack.require("delay", "delaySyncNote")
    assert pack.to_stored(spec, 13, warnings=warnings) == "13"
    assert len(warnings) == 1
    # The warning has to be actionable: the user cannot read the integer off the
    # plugin UI, so pointing them at the UI would be a dead end.
    assert "probe.py" in warnings[0]
    assert "not known" in warnings[0]


def test_selectors_lacking_members_explain_the_alternative(pack):
    """An unknown selector is only acceptable if its note says what to do
    instead. Otherwise the agent has no path forward."""
    for spec in pack.parameters.values():
        if spec.kind != "enum" or spec.members is not None:
            continue
        assert spec.note, f"{spec.path} has no members and no guidance"
        assert "probe.py" in spec.note, (
            f"{spec.path} does not point at the discovery workflow"
        )


def test_note_timed_delay_does_not_need_a_selector(pack):
    """The functional consequence of the unknown sync-note table: a musical
    delay must still be reachable through delayTime in ms."""
    from packs.timing import note_ms

    spec = pack.require("delay", "delayTime")
    assert pack.to_stored(spec, note_ms(120, "1/8 dotted")) == "375"


def test_read_only_parameter_is_refused(pack):
    with pytest.raises(PackError, match="read-only"):
        pack.to_stored(pack.require("", "version"), "2.0.0")


def test_declared_range_is_enforced(pack):
    spec = pack.require("delay", "delayTime")
    with pytest.raises(PackError, match="outside the declared range"):
        pack.to_stored(spec, 9000)


def test_out_of_range_can_be_overridden(pack):
    warnings: list[str] = []
    spec = pack.require("delay", "delayTime")
    assert pack.to_stored(spec, 9000, allow_out_of_range=True, warnings=warnings) == "9000"
    assert any("outside the declared range" in w for w in warnings)


def test_rotation_percent_is_converted(pack):
    assert pack.to_stored(pack.require("pr12Amp", "pr12Volume"), 62) == "0.62"
    with pytest.raises(PackError, match="0–100"):
        pack.to_stored(pack.require("pr12Amp", "pr12Volume"), 620)


def test_unknown_parameter_names_the_manifest(pack):
    with pytest.raises(PackError, match="manifest.json"):
        pack.require("chorus", "chorusMix")


def test_morgan_has_no_modulation_section(pack):
    """tone-references.md used to promise chorus/flanger. It does not exist."""
    modules = {spec.module for spec in pack.parameters.values()}
    assert not modules & {"chorus", "flanger", "phaser", "pitch"}
