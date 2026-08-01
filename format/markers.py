"""
Marker byte constants observed in Neural DSP preset files.

Sources:
- toneparse docs/neural_dsp.md for the Archetype-Gojira format (facts about the
  byte layout only; that project carries no license and none of its code is used)
- Direct inspection of Morgan Amps Suite preset samples

Morgan presets use additional value-type markers not documented in toneparse;
these were inferred empirically and are documented here as observations only.
For lossless round-trip we preserve marker bytes as-is rather than rely on
their semantic meaning.
"""

NUL = b"\x00"

# Documented in toneparse:
NULL_VALUE_POSIX = b"\x01\x02\x05"
NULL_VALUE_DOS = b"\x01\x09\x06"
EDITOR_VALUE = b"\x01\x05\x01"
LIST_ELEMENTS_END = b"\x00\x01\x01"
LEGACY_STRING_VALUE = b"\x01\x06\x05"

# Observed in Morgan samples (3-byte value-type prefixes, last byte 0x05):
# Each precedes a string-encoded value. The middle byte appears to denote
# the value's "type" but we don't rely on it semantically.
VALUE_TYPE_PREFIXES_SEEN = {
    b"\x01\x03\x05",  # short int-as-string ("0", "1", "6")
    b"\x01\x04\x05",  # also int-as-string ("13" — delaySyncNote)
    b"\x01\x05\x05",  # short numeric ("0.5", "120", "500")
    b"\x01\x06\x05",  # bool true / legacy string
    b"\x01\x07\x05",  # generic string ("Clean", "false", "1.1.0")
    b"\x01\x09\x05",  # signed/long decimal ("-71.153", "5027.64")
    b"\x01\x0a\x05",  # unsigned decimal ("0.780312")
    b"\x01\x0c\x05",  # display string ("Soft Touch", 10 chars)
    b"\x01\x0d\x05",  # display string ("Ultra Clean", 11 chars)
}

# Bytes considered "printable string content" (a string token's body).
PRINTABLE_START = 0x20
PRINTABLE_END = 0x7E


def is_printable(b: int) -> bool:
    return PRINTABLE_START <= b <= PRINTABLE_END


# A value's marker prefix ends with the 3 bytes  0x01 <LEN> 0x05  where
# <LEN> == byte-length of the value string + 2. Verified to hold for every
# value in every sample preset (including ~150-char IR paths). When a value
# is mutated to a different length, <LEN> MUST be recomputed or the plugin
# reads the wrong number of bytes and silently rejects the preset.
VALUE_PREFIX_HEAD = 0x01
VALUE_PREFIX_TAIL = 0x05
VALUE_LEN_OFFSET = 2


def is_value_prefix(prefix: bytes) -> bool:
    return (
        len(prefix) >= 3
        and prefix[-3] == VALUE_PREFIX_HEAD
        and prefix[-1] == VALUE_PREFIX_TAIL
    )


def fix_value_prefix(prefix: bytes, value: str) -> bytes:
    """Return prefix with its length byte set to match `value`.

    No-op for non-value prefixes (keys, structural markers).
    """
    if not is_value_prefix(prefix):
        return prefix
    encoded = len(value.encode("utf-8"))
    n = encoded + VALUE_LEN_OFFSET
    if n > 0xFF:
        raise ValueError(
            f"value too long to length-encode in one byte ({encoded} bytes, "
            f"max {0xFF - VALUE_LEN_OFFSET}); multi-byte length encoding is "
            f"unknown. Note the limit is on BYTES, so non-ASCII characters "
            f"count more than once."
        )
    return prefix[:-2] + bytes([n]) + prefix[-1:]


# --- typed binary values ---------------------------------------------------
# Not every Neural DSP plugin stores its numbers as text. Tone King Imperial
# MKII writes them as raw IEEE-754 doubles behind a marker that mirrors the
# string one but ends 0x04 instead of 0x05:
#
#     0x01 <LEN> 0x04  <LEN-1 payload bytes>  0x00
#
# Only LEN == 0x09 (an 8-byte double) occurs in the 135 Tone King presets on
# hand, but the length is read from the marker rather than assumed, so a
# different width decodes as opaque bytes instead of corrupting the file.
#
# This encoding is why a text-only parser cannot be pointed at these files: a
# payload byte that happens to land in printable ASCII gets read as text. The
# exponent bytes of 120.0 are 0x5e 0x40 — "^@" — which is how an early Tone
# King draft acquired a parameter named `^@presetNameProp`.
TYPED_VALUE_TAIL = 0x04     # a number: 8 bytes, little-endian IEEE-754 double
OPAQUE_VALUE_TAIL = 0x06    # an identifier: 8 bytes with no numeric meaning
TYPED_LEN_OFFSET = 1
DOUBLE_WIDTH = 8

# Both tails are exclusive to Tone King across the 681 factory presets on hand;
# Morgan, Nolly X and Plini X use none, so widening the parser to accept them
# cannot change how those three are read.
BINARY_VALUE_TAILS = (TYPED_VALUE_TAIL, OPAQUE_VALUE_TAIL)


def is_typed_value_prefix(prefix: bytes) -> bool:
    """True for a 0x01 <LEN> <tail> marker introducing a fixed-width binary body.

    The 0x06 form matters even though nothing reads its value: `presetUIDProp`
    uses it, and a parser that scans it as text runs off the end of the payload
    and glues a stray byte onto the *next* key. That is how the first parameter
    record in every Tone King preset came out named `fPARAM`.
    """
    return (
        len(prefix) >= 3
        and prefix[-3] == VALUE_PREFIX_HEAD
        and prefix[-1] in BINARY_VALUE_TAILS
    )


def is_opaque_value_prefix(prefix: bytes) -> bool:
    """True when the binary body has no interpretation, only bytes to preserve."""
    return (
        len(prefix) >= 3
        and prefix[-3] == VALUE_PREFIX_HEAD
        and prefix[-1] == OPAQUE_VALUE_TAIL
    )


def typed_payload_length(prefix: bytes) -> int:
    """How many binary bytes follow this marker."""
    return prefix[-2] - TYPED_LEN_OFFSET
