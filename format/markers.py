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
