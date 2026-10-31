"""
Which section each stored property belongs to, read from the file's tree.

A Neural DSP preset is a serialised JUCE ValueTree: a node is its type name
(NUL-terminated), a compressed count of properties, each property as a name
(NUL-terminated), a compressed byte count and that many bytes of value, then a
compressed count of child nodes and the children themselves. A compressed int
is one byte giving how many little-endian bytes follow (top bit for sign).

`structured.build` first named a section by the token after each `subModels`
marker. That works on files where every node carries a `subModels` child, empty
or not, which is how Morgan Amps Suite saves. Morgan Amps Suite X leaves the
empty ones out, so every amp, EQ and pedal after the first in a group was filed
under its predecessor's name (`pr12Volume` read as `ac20Amp/pr12Volume`). The
tree says which node a property sits in without depending on that marker.

The section name keeps the old convention so every existing caller and manifest
still matches: a property's module is the type of the node holding it when that
node is a child of a `subModels` node, and "" otherwise (the root and `appModel`).
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

SUBMODELS = "subModels"
# A stored value is never empty: its first byte is a JUCE `var` type marker
# (1 int, 2 true, 3 false, 4 double, 5 string, 6 int64, 7 array, 8 binary,
# 9 undefined). Checking it is what stops a damaged file, one property cut out
# without its count being lowered, from re-syncing into a whole but wrong tree.
VAR_MARKERS = 9


class NotATree(ValueError):
    """The bytes do not read as one complete ValueTree."""


def _compressed_int(buf: bytes, i: int) -> Tuple[int, int]:
    if i >= len(buf):
        raise NotATree("ran out of bytes reading a count")
    head = buf[i]
    width = head & 0x7F
    if width > 4 or i + 1 + width > len(buf):
        raise NotATree(f"bad count width {width} at byte {i}")
    value = int.from_bytes(buf[i + 1:i + 1 + width], "little")
    return (-value if head & 0x80 else value), i + 1 + width


def _name(buf: bytes, i: int) -> Tuple[str, int]:
    end = buf.find(b"\x00", i)
    if end < 0:
        raise NotATree(f"unterminated name at byte {i}")
    try:
        return buf[i:end].decode("utf-8"), end + 1
    except UnicodeDecodeError as e:
        raise NotATree(f"name at byte {i} is not UTF-8") from e


def property_modules(buf: bytes) -> Optional[Dict[int, str]]:
    """Map each property name's byte offset to its module, or None.

    None means the buffer is not one complete tree (trailing bytes, a count
    that runs past the end, a negative count), and the caller keeps its own
    reading. Nothing here guesses.
    """
    modules: Dict[int, str] = {}
    try:
        end = _node(buf, 0, "", modules)
    except (NotATree, RecursionError):
        return None
    return modules if end == len(buf) else None


def _node(buf: bytes, i: int, parent: str, modules: Dict[int, str]) -> int:
    kind, i = _name(buf, i)
    module = kind if parent == SUBMODELS else ""
    count, i = _compressed_int(buf, i)
    if count < 0:
        raise NotATree(f"negative property count at byte {i}")
    for _ in range(count):
        modules[i] = module
        _, i = _name(buf, i)
        size, i = _compressed_int(buf, i)
        if size < 1 or i + size > len(buf):
            raise NotATree(f"property value empty or past the end at byte {i}")
        if not 1 <= buf[i] <= VAR_MARKERS:
            raise NotATree(f"unknown value type {buf[i]} at byte {i}")
        i += size
    children, i = _compressed_int(buf, i)
    if children < 0:
        raise NotATree(f"negative child count at byte {i}")
    for _ in range(children):
        i = _node(buf, i, kind, modules)
    return i
