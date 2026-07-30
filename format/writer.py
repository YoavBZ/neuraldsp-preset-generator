"""
Byte-level writer for Neural DSP preset files.

The token list produced by ``format.parser.parse`` is enough to reconstruct the
original file byte-for-byte. To mutate a preset, change a token's ``value``
field (only the string body) and call ``write()``. Marker bytes are preserved
verbatim, which keeps the wrapper structure exactly as the plugin expects.

The writer never recomputes marker bytes from scratch. The value-type markers
in the Morgan format are undocumented; recomputing them risks corrupting the
file. The template-based approach sidesteps this entirely.
"""

from __future__ import annotations

from typing import Iterable

from .parser import Token


def write(tokens: Iterable[Token]) -> bytes:
    """Serialize a token sequence back to the preset binary format."""
    return b"".join(tok.to_bytes() for tok in tokens)


def write_file(path: str, tokens: Iterable[Token]) -> None:
    with open(path, "wb") as f:
        f.write(write(tokens))

