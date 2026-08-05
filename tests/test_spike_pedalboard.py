"""The state handling in the pedalboard spike, without a plugin or macOS.

The spike itself needs a licensed Audio Unit, so it is never run in CI. Its
*decisions* do not: which encoding a state document is, whether a preset can
legally be handed to a plugin as state, and whether the plugin kept what was
written. Those are the parts that were wrong or missing, so those are the parts
tested here.

The gap this closes: `--state` was never exercised with a generated preset, and
an encoding mismatch between a preset file and a plugin's live state is silent —
the host accepts the bytes and the plugin ignores them, so a render of the
default preset gets reported as a render of the generated one.
"""

from __future__ import annotations

import pathlib

from format.parser import parse
from format.structured import build, set_parameter
from format.writer import write
from scripts.spike_pedalboard import state_encoding, state_round_trip_diff

ROOT = pathlib.Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "Example_Clean_PR12.xml"

JUCE_XML = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<MorganAmpsSuite sw50rVolume="0.5" pr12Volume="0.4"/>\n'
)


def preset_bytes() -> bytes:
    return SAMPLE.read_bytes()


# --- which encoding is this? -------------------------------------------------


def test_a_preset_file_is_the_record_encoding():
    assert state_encoding(preset_bytes()) == "record"


def test_a_juce_state_document_is_xml():
    assert state_encoding(JUCE_XML) == "xml"
    # Leading whitespace is still XML: this is what a host hands back.
    assert state_encoding(b"\n  " + JUCE_XML) == "xml"


def test_empty_and_garbage_are_unknown_rather_than_record():
    """The parser reads any printable run as a header, so it accepts nonsense.

    Detection must not inherit that leniency: an unknown blob passed through as
    'record' is exactly the silent-acceptance failure this guards.
    """
    assert state_encoding(b"") == "unknown"
    assert state_encoding(b"\x00\x01\x02\x03") == "unknown"
    assert state_encoding(b"not a preset at all") == "unknown"


def test_a_printable_header_with_no_parameters_is_not_a_record():
    """`build(parse(...))` succeeds on this and yields nothing. It is not state."""
    assert state_encoding(b"morgan") == "unknown"


def test_an_unknown_plugin_header_is_not_a_record():
    """Parsing is not enough — a pack has to claim the header.

    A record document from some other vendor's plugin is not state for either of
    ours, and treating it as one would apply it and report success.
    """
    preset = build(parse(preset_bytes()))
    renamed = write(preset.tokens).replace(b"morgan\x00", b"someoth\x00", 1)
    assert state_encoding(renamed) == "unknown"


# --- did the plugin keep it? -------------------------------------------------


def test_round_trip_reports_no_differences_when_state_survives():
    blob = preset_bytes()
    checked, differences = state_round_trip_diff(blob, blob)
    assert checked > 100, "the sample preset has 132 parameters"
    assert differences == []


def test_round_trip_names_the_parameter_the_plugin_changed():
    """The case that matters: the write is accepted and quietly not kept."""
    before = preset_bytes()
    preset = build(parse(before))
    set_parameter(preset, "sw50rAmp", "sw50rVolume", "0.9")
    after = write(preset.tokens)

    checked, differences = state_round_trip_diff(before, after)
    assert checked > 100
    changed = {(module, key): (wrote, got) for module, key, wrote, got in differences}
    assert ("sw50rAmp", "sw50rVolume") in changed
    wrote, got = changed[("sw50rAmp", "sw50rVolume")]
    assert got == "0.9" and wrote != "0.9"
    assert len(differences) == 1, f"only one parameter moved, got {differences}"


def test_a_parameter_the_plugin_never_returned_counts_as_a_difference():
    """A missing parameter is a difference, not an absence.

    Same rule the audit had to learn: "absent, not failing" is how three wrong
    ranges survived a full run of it. Here the plugin hands back a document that
    parses but carries none of what was written — nothing was kept, and the
    report has to say so rather than finding zero disagreements.
    """
    before = preset_bytes()
    expected = len(build(parse(before)).by_path)

    checked, differences = state_round_trip_diff(before, JUCE_XML)

    assert checked == 0, "nothing was read back, so nothing was verified"
    assert len(differences) == expected, "every parameter is unaccounted for"
    assert all(got is None for _, _, _, got in differences)
