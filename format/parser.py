"""
Lossless tokenizer for Neural DSP preset binary files.

A preset is a sequence of UTF-8 null-terminated printable strings separated by
short non-printable "marker" bytes. We tokenize into (raw_prefix, value,
terminator) triples that preserve every byte of the original file. The writer
concatenates them back; mutating a `value` produces a valid edited preset as
long as the marker bytes around it are unchanged.

Credit: what the marker bytes mean was learned from the format notes in
https://github.com/vian21/toneparse (lib/NeuralDSPParser.ts, BaseParser.ts,
docs/neural_dsp.md). That project decodes the structured key/value semantics;
here we focus on the byte-level layer needed for lossless write-back. The
implementation below is original — no code is taken from that project, which
carries no license.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .markers import (
    NUL,
    VALUE_LEN_OFFSET,
    VALUE_PREFIX_TAIL,
    is_printable,
    is_value_prefix,
)


@dataclass
class Token:
    """One printable string in the preset, with the bytes that preceded it."""

    raw_prefix: bytes  # non-printable bytes between previous string and this one
    value: str         # printable UTF-8 body (no NUL)
    terminator: bytes  # b"\x00" normally; b"" only at EOF if file lacks final NUL

    def to_bytes(self) -> bytes:
        return self.raw_prefix + self.value.encode("utf-8") + self.terminator


def parse(buf: bytes) -> List[Token]:
    """Tokenize a preset buffer.

    Invariant: ``b"".join(tok.to_bytes() for tok in parse(buf)) == buf``.
    """

    tokens: List[Token] = []
    i = 0
    n = len(buf)

    while i < n:
        # Collect non-printable prefix bytes up to the next printable byte —
        # but stop the moment a complete value marker (0x01 <LEN> 0x05) has been
        # consumed. A value's own first byte need not be printable: any value
        # starting with a non-ASCII character begins with a UTF-8 lead byte
        # (>= 0xC2), and scanning past the marker would swallow it, leaving a
        # prefix that no longer looks like a value. The key would then be paired
        # with nothing and the parameter would vanish from the structured view.
        prefix_start = i
        while i < n and not is_printable(buf[i]):
            i += 1
            if is_value_prefix(buf[prefix_start:i]):
                break
        prefix = buf[prefix_start:i]

        # --- Length-aware value handling ----------------------------------
        # A value is introduced by the 3-byte marker 0x01 <LEN> 0x05, where
        # LEN == len(value_bytes) + 2. We must read EXACTLY LEN-2 bytes, not
        # scan to the next NUL: when the value is 30..124 bytes long, LEN
        # lands in printable ASCII (0x20..0x7E) and would otherwise be
        # mis-split (silently corrupting e.g. long preset names).
        #
        # Case A: LEN byte is printable, so the prefix run above stopped on
        # it. The run ended with 0x01 and buf[i+1] == 0x05 -> pull LEN and
        # 0x05 into the prefix to complete the 3-byte marker.
        if (
            prefix.endswith(b"\x01")
            and i + 1 < n
            and buf[i + 1] == VALUE_PREFIX_TAIL
        ):
            len_byte = buf[i]
            prefix = prefix + bytes([len_byte, VALUE_PREFIX_TAIL])
            i += 2
            vend = i + (len_byte - VALUE_LEN_OFFSET)
            value = buf[i:vend].decode("utf-8")
            i = vend
            terminator = NUL if (i < n and buf[i] == 0x00) else b""
            if terminator:
                i += 1
            tokens.append(Token(raw_prefix=prefix, value=value, terminator=terminator))
            continue

        if i >= n:
            # File ended in a run of non-printable bytes (e.g. trailing
            # 0x00 0x01 0x01). Emit a trailing token so round-trip is exact.
            if prefix:
                tokens.append(Token(raw_prefix=prefix, value="", terminator=b""))
            break

        # Case B: LEN byte was non-printable, so the prefix already contains
        # the full 0x01 <LEN> 0x05 marker. Read exactly LEN-2 value bytes.
        if is_value_prefix(prefix):
            vlen = prefix[-2] - VALUE_LEN_OFFSET
            vend = i + vlen
            if vlen >= 0 and vend <= n:
                value = buf[i:vend].decode("utf-8")
                i = vend
                terminator = NUL if (i < n and buf[i] == 0x00) else b""
                if terminator:
                    i += 1
                tokens.append(
                    Token(raw_prefix=prefix, value=value, terminator=terminator)
                )
                continue

        # --- Fallback: plain string (key / sub-model name) ----------------
        str_start = i
        while i < n and buf[i] != 0x00:
            if not is_printable(buf[i]):
                break
            i += 1
        value = buf[str_start:i].decode("utf-8", errors="strict")
        terminator = NUL if (i < n and buf[i] == 0x00) else b""
        if terminator:
            i += 1
        tokens.append(Token(raw_prefix=prefix, value=value, terminator=terminator))

    return tokens


def parse_file(path: str) -> List[Token]:
    with open(path, "rb") as f:
        return parse(f.read())
