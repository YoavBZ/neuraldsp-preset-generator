"""The second preset encoding: binary values inside PARAM records.

Morgan, Nolly X and Plini X name every parameter with its own key and store
every value as text. Tone King Imperial MKII does neither: numbers are 8-byte
little-endian doubles behind a `0x01 <LEN> 0x04` marker, and parameters live in
a flat list of `PARAM {id, value}` records, so the key says nothing about which
control it is.

Reading it as text produced six parameters instead of 259, one of them named
from two bytes of a float that happened to land in printable ASCII. Every case
below is a specific way that went wrong.

Fixtures are synthetic: real presets are Neural DSP's factory content and are
not committed. See NOTICE.md.
"""

from __future__ import annotations

import struct

import pytest

from format.parser import Token, decode_payload, encode_payload, parse
from format.structured import build, set_parameter
from format.writer import write


def double(x: float) -> bytes:
    """A typed numeric value: marker, 8-byte payload, terminator."""
    return b"\x01\x09\x04" + struct.pack("<d", x) + b"\x00"


def text(s: str) -> bytes:
    """A string value: 0x01 <len+2> 0x05, body, terminator."""
    body = s.encode()
    return bytes([0x01, len(body) + 2, 0x05]) + body + b"\x00"


def record(name: str, value: float | None = None) -> bytes:
    """A record. The `id` marker carries a field count: 0x02 with a value,
    0x01 without, which is what real one-field records use."""
    out = b"PARAM\x00" + bytes([0x01, 0x02 if value is not None else 0x01]) + b"id\x00" + text(name)
    if value is not None:
        out += b"value\x00" + double(value)
    return out


def preset(*records: bytes, count_byte: int | None = None) -> bytes:
    head = b"neural_dsp_toneking\x00"
    if count_byte is not None:
        head += bytes([0x01, count_byte])
    return head + b"".join(records)


# --- the byte layer --------------------------------------------------------


def test_binary_values_round_trip_byte_for_byte():
    raw = preset(record("ampType", 3.0), record("gain", 0.5))
    assert write(parse(raw)) == raw


def test_a_payload_byte_in_ascii_does_not_leak_into_the_next_key():
    """120.0 ends in the bytes 0x5e 0x40 — `^@`. Read as text, those became the
    start of the next token, which is how a parameter called `^@presetNameProp`
    appeared in the first Tone King draft.

    Built without a terminator after the payload, because that is how real
    top-level binary values are stored: `tempo\\0 <marker> <8 bytes>` runs
    straight into the next key with nothing between them.
    """
    import struct as _s
    raw = (b"toneking\x00tempo\x00" + b"\x01\x09\x04" + _s.pack("<d", 120.0)
           + b"presetNameProp\x00" + text("Default"))
    tokens = parse(raw)
    assert write(tokens) == raw
    assert "presetNameProp" in [t.value for t in tokens]
    assert not any(t.value.startswith("^@") for t in tokens)

    raw = preset(record("tempo", 120.0), record("gain", 0.5))
    tokens = parse(raw)
    assert write(tokens) == raw
    names = [t.value for t in tokens]
    assert "gain" in names
    assert not any(n.startswith("^@") for n in names), names


def test_payload_is_decoded_as_a_number_not_kept_as_bytes():
    tokens = parse(preset(record("tempo", 120.0)))
    binaries = [t for t in tokens if t.is_binary]
    assert [t.value for t in binaries] == ["120"]


def test_decode_and_encode_are_inverses():
    for x in (0.0, 1.0, 0.5, 120.0, -6.25, 1e-3):
        assert float(decode_payload(struct.pack("<d", x))) == x
        assert encode_payload(decode_payload(struct.pack("<d", x)), 8) == struct.pack("<d", x)


def test_an_opaque_value_is_not_read_as_a_number():
    """`presetUIDProp` uses a 0x06 marker over 8 bytes that are an identifier,
    not a quantity. Decoding it as a double would print a plausible-looking
    number that means nothing."""
    uid = b"\x01\x09\x06" + bytes([0x4A, 0x04, 0x64, 0xD6, 0x6F, 0x2F, 0x4E, 0x02])
    raw = b"toneking\x00presetUIDProp\x00" + uid + b"nextKey\x00" + text("x")
    tokens = parse(raw)
    assert write(tokens) == raw
    opaque = [t for t in tokens if t.is_binary][0]
    assert opaque.value == uid[3:].hex()
    # And the key after it survives intact — this is what ran off the end before.
    assert "nextKey" in [t.value for t in tokens]


def test_writing_an_opaque_value_is_refused():
    with pytest.raises(ValueError, match="opaque identifier"):
        encode_payload("1.0", 8, opaque=True)


def test_set_parameter_refuses_an_opaque_value_through_the_real_path():
    """Not just the encoder in isolation: `presetUIDProp` is a real Parameter in
    every Tone King preset, so `set_parameter` is reachable with it and must
    refuse there too."""
    uid = b"\x01\x09\x06" + bytes(range(8))
    raw = b"toneking\x00presetUIDProp\x00" + uid + b"tempo\x00" + double(120.0)
    pre = build(parse(raw))
    assert pre.by_path[("", "presetUIDProp")].value == bytes(range(8)).hex()
    with pytest.raises(ValueError, match="opaque identifier"):
        set_parameter(pre, "", "presetUIDProp", "1.0")
    # The neighbouring real value is still writable.
    set_parameter(pre, "", "tempo", "90")
    assert build(parse(write(pre.tokens))).by_path[("", "tempo")].value == "90"


# --- the structured layer --------------------------------------------------


def test_records_are_named_by_their_id_field():
    raw = preset(record("ampType", 3.0), record("cab1Active", 1.0))
    pre = build(parse(raw))
    assert {p.key for p in pre.parameters} == {"ampType", "cab1Active"}
    assert pre.by_path[("", "ampType")].value == "3"
    # The record's own key names are not parameters.
    assert not {"id", "value"} & {p.key for p in pre.parameters}


def test_tone_king_switch_writes_use_numeric_binary_values():
    """Tone King's switches are doubles, not the text true/false used by
    Morgan. Promoting their kinds to switch without carrying that encoding to
    the writer made every real switch write fail at ``float('true')``."""
    from packs.loader import load_pack

    pack = load_pack("toneking")
    spec = pack.require("", "ampsActive")
    assert pack.to_stored(spec, True, warnings=[]) == "1"
    assert pack.to_stored(spec, False, warnings=[]) == "0"

    pre = build(parse(preset(record("ampsActive", 0.0))))
    set_parameter(pre, "", "ampsActive", pack.to_stored(spec, True, warnings=[]))
    reparsed = build(parse(write(pre.tokens)))
    assert reparsed.by_path[("", "ampsActive")].value == "1"


def test_a_printable_record_count_does_not_break_the_first_record():
    """The record list is introduced by `0x01 <count+1>`. When that byte is
    printable it is read as text and glued to the first marker (`fPARAM`), which
    broke exactly one record per preset — the first."""
    raw = preset(record("ampAttenuation", 5.0), record("ampHfc", 0.0), count_byte=0x66)
    pre = build(parse(raw))
    assert {p.key for p in pre.parameters} == {"ampAttenuation", "ampHfc"}


def test_a_record_with_no_value_is_listed_not_invented():
    """One-field records exist. They cannot be read or written, so they must not
    appear as parameters with a made-up value — nor leak their `id` key."""
    raw = preset(record("drive1Bass", 0.5), record("drive1Treble"), record("gain", 1.0))
    pre = build(parse(raw))
    assert {p.key for p in pre.parameters} == {"drive1Bass", "gain"}
    assert pre.valueless == [("", "drive1Treble")]


def test_an_unrecognised_record_shape_falls_back_rather_than_vanishing():
    """A record we do not understand must still surface as *something*."""
    raw = b"toneking\x00" + b"PARAM\x00" + b"tag\x00" + text("weird") + text("0.5")
    pre = build(parse(raw))
    assert any(p.key == "tag" for p in pre.parameters)


# --- writing ---------------------------------------------------------------


def test_setting_a_binary_value_reencodes_and_round_trips():
    raw = preset(record("tempo", 120.0))
    pre = build(parse(raw))
    set_parameter(pre, "", "tempo", "142.5")
    out = write(pre.tokens)
    assert build(parse(out)).by_path[("", "tempo")].value == "142.5"
    assert len(out) == len(raw), "a double is fixed width; the file must not resize"


def test_restoring_a_binary_value_reproduces_the_original_bytes():
    raw = preset(record("tempo", 120.0), record("gain", 0.25))
    pre = build(parse(raw))
    set_parameter(pre, "", "tempo", "142.5")
    changed = write(pre.tokens)
    pre2 = build(parse(changed))
    set_parameter(pre2, "", "tempo", "120")
    assert write(pre2.tokens) == raw


def test_the_text_format_is_untouched_by_all_of_this():
    """Morgan-shaped presets must parse exactly as before: no 0x04 or 0x06
    markers appear in any of the three text-valued plugins."""
    raw = b"morgan\x00name\x00" + text("Example") + b"volume\x00" + text("0.62")
    pre = build(parse(raw))
    assert write(pre.tokens) == raw
    assert pre.by_path[("", "volume")].value == "0.62"
    assert not any(t.is_binary for t in pre.tokens)
