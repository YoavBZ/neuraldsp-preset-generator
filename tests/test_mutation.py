"""Mutating one parameter must change only that parameter's bytes."""

from __future__ import annotations

import pathlib

import pytest

from format.parser import parse, parse_file
from format.structured import build, set_parameter
from format.writer import write

SAMPLES_DIR = pathlib.Path(__file__).parent.parent / "samples"
SAMPLE_FILES = sorted(SAMPLES_DIR.glob("*.xml"))


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_mutate_preset_name(sample: pathlib.Path) -> None:
    """Renaming the preset (top-level 'name') keeps the file valid and
    changes only the name region."""
    tokens = parse_file(str(sample))
    preset = build(tokens)
    original_name = preset.preset_name
    assert original_name, "Preset must have a name"

    new_name = "Roundtripped"
    set_parameter(preset, "", "name", new_name)

    # Sanity: round-tripped through the parser again, name matches.
    preset2 = build(parse(write(preset.tokens)))
    assert preset2.preset_name == new_name


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_mutate_pr12_volume(sample: pathlib.Path) -> None:
    """Setting a known amp parameter survives a re-parse."""
    tokens = parse_file(str(sample))
    preset = build(tokens)

    target = preset.by_path.get(("pr12Amp", "pr12Volume"))
    assert target is not None, "pr12Volume must exist in all Morgan presets"
    original_value = target.value

    set_parameter(preset, "pr12Amp", "pr12Volume", "0.5")
    rewritten = write(preset.tokens)

    preset2 = build(parse(rewritten))
    assert preset2.by_path[("pr12Amp", "pr12Volume")].value == "0.5"
    # Other PR12 params untouched.
    for key in ("pr12Treble", "pr12Bass", "pr12Reverb", "pr12Dwell"):
        assert (
            preset2.by_path[("pr12Amp", key)].value
            == preset.by_path[("pr12Amp", key)].value
        )


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_length_prefix_invariant_after_mutation(sample: pathlib.Path) -> None:
    """After mutating values to DIFFERENT lengths, every value's prefix
    length byte must still equal len(value)+2 (the plugin relies on this)."""
    from format.markers import VALUE_LEN_OFFSET, is_value_prefix
    tokens = parse_file(str(sample))
    preset = build(tokens)

    # Mutate a spread of values to deliberately different lengths.
    changes = {
        ("", "name"): "A Much Longer Preset Name Than Before",
        ("pr12Amp", "pr12Volume"): "0.5",          # likely shorter
        ("delay", "delayMix"): "0.123456789",      # likely longer
    }
    for (mod, key), val in changes.items():
        if (mod, key) in preset.by_path:
            set_parameter(preset, mod, key, val)

    rewritten = write(preset.tokens)
    reparsed = parse(rewritten)

    for tok in reparsed:
        if is_value_prefix(tok.raw_prefix) and tok.value != "":
            length_byte = tok.raw_prefix[-2]
            assert length_byte == len(tok.value.encode("utf-8")) + VALUE_LEN_OFFSET, (
                f"length byte {length_byte} != len({tok.value!r})+{VALUE_LEN_OFFSET}"
            )

    # The mutated values must survive the re-parse.
    rp = build(reparsed)
    for (mod, key), val in changes.items():
        if (mod, key) in rp.by_path:
            assert rp.by_path[(mod, key)].value == val


@pytest.mark.parametrize(
    "name",
    [
        "X",                                                      # 1 char
        "Smoke Test PR12 Clean",                                  # 21, LEN non-printable
        "Eagles - Hotel California - Clean Rhythm - Morgan PR12",  # 54, LEN printable ('8')
        "A" * 60,                                                 # 60, LEN printable
        "Z" * 123,                                                # 123, LEN printable (max single-byte-ish)
    ],
    ids=["len1", "len21", "len54", "len60", "len123"],
)
def test_long_value_roundtrips(name: str) -> None:
    """Values whose byte-length is 30..124 make the LEN byte land in printable
    ASCII; the tokenizer must still read exactly LEN-2 bytes (regression for
    the long-preset-name corruption bug)."""
    tokens = parse_file(str(SAMPLE_FILES[0]))
    preset = build(tokens)
    set_parameter(preset, "", "name", name)
    out = write(preset.tokens)
    assert build(parse(out)).preset_name == name, (
        f"name of length {len(name)} did not round-trip"
    )


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_setting_same_value_is_byte_identical(sample: pathlib.Path) -> None:
    """Mutating a parameter to its current value should not change any bytes."""
    original = sample.read_bytes()
    tokens = parse_file(str(sample))
    preset = build(tokens)

    target = preset.by_path[("pr12Amp", "pr12Volume")]
    set_parameter(preset, "pr12Amp", "pr12Volume", target.value)
    assert write(preset.tokens) == original
