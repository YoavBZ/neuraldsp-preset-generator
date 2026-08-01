"""
Structured (key→value) layer over the byte-level token stream.

The byte-level layer is enough for round-trip but inconvenient for the LLM,
which thinks in terms of "set pr12Volume to 0.5". This module pairs up tokens
into Parameters that can be looked up and mutated by (module_path, key).

Discrimination rule:
- A token whose ``raw_prefix`` ends with ``0x05`` is a VALUE. Every other token
  is a KEY (or a structural marker like a sub-module name).
- A key is paired with the immediately-following value token if that token is
  a value; otherwise the key has no string value (bare-encoded bool / null /
  section marker — left untouched).
- The token ``subModels`` is followed (after a structural separator) by a
  sub-module NAME token. That name updates the current module path.

This is heuristic, derived from observation of Morgan presets. It's good
enough for parameter mutation but is not a full grammar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .markers import (
    fix_value_prefix,
    is_opaque_value_prefix,
    is_typed_value_prefix,
    is_value_prefix,
)
from .parser import Token, encode_payload

def is_value_token(tok: Token) -> bool:
    """True when this token is a VALUE rather than a key or structural marker.

    The byte rule lives in `markers` so it is stated once. Both encodings count:
    a printable string behind 0x05, and a binary number behind 0x04.
    """
    return is_value_prefix(tok.raw_prefix) or is_typed_value_prefix(tok.raw_prefix)


# Some plugins do not name a parameter with its own key. Tone King Imperial
# MKII writes a flat list of records instead:
#
#     PARAM  id -> "ampType"  value -> <binary double>
#
# so 259 parameters share seven key names and the key says nothing about which
# control it is. The parameter's real identity is the `id` field *inside* the
# record. Reading these as plain key/value pairs collapses every one of them
# onto ("", "id") and ("", "value"), which is how an early Tone King draft
# produced six parameters instead of two hundred.
RECORD_MARKER = "PARAM"
RECORD_NAME_KEY = "id"
RECORD_VALUE_KEY = "value"


def is_record_marker(value: str) -> bool:
    """True for the token that opens a parameter record.

    The list of records is introduced by `0x01 <count+1>`, and when that count
    byte lands in printable ASCII the tokenizer reads it as text and glues it to
    the front of the first marker: 101 records makes `0x66`, so the token comes
    out as `fPARAM`. Only the first record in a file is affected, and only when
    the count happens to be printable — which is why every preset parsed
    perfectly except its very first parameter.

    Tolerating one stray leading byte here is deliberate: the byte layer is
    already lossless and rewrites the file exactly, so this is purely a question
    of reading, and teaching the tokenizer to recognise every structural marker
    a plugin might invent is a much bigger promise than this needs.
    """
    return value == RECORD_MARKER or (
        value.endswith(RECORD_MARKER) and len(value) == len(RECORD_MARKER) + 1
    )


def read_record(tokens: List[Token], i: int):
    """Parse `PARAM {id: <name>[, value: <v>]}` at `i`.

    Returns (name, value_index_or_None, end_index), or None when the tokens
    after the marker are not a record at all — in which case the caller falls
    back to treating them as ordinary keys, so an unfamiliar shape cannot
    silently vanish.

    The value field is genuinely optional. A record's `id` key carries a field
    count in its marker (`0x01 0x02` with a value, `0x01 0x01` without), and
    presets do contain one-field records: `Rawds.xml` names `drive1Treble` and
    stores nothing for it. Requiring the value made those records fail to parse,
    and the leftover `id` and `value` keys then registered as parameters in
    their own right.
    """
    if i + 2 >= len(tokens):
        return None
    name_key, name_val = tokens[i + 1], tokens[i + 2]
    if name_key.value != RECORD_NAME_KEY or not is_value_token(name_val):
        return None
    if i + 4 < len(tokens):
        value_key, value_val = tokens[i + 3], tokens[i + 4]
        if value_key.value == RECORD_VALUE_KEY and is_value_token(value_val):
            return name_val.value, i + 4, i + 5
    return name_val.value, None, i + 3


@dataclass
class Parameter:
    """A (module_path, key, value) tuple with index back into the token list."""

    # The file flattens its module tree: each `subModels` marker replaces the
    # current module rather than nesting under it, so a path is a single name
    # ("pr12Amp", "cabParameters"), never dotted. Top-level keys use "".
    module_path: str          # e.g. "pr12Amp"
    key: str                  # e.g. "pr12Volume"
    value: str                # current value as stored (string form)
    key_index: int            # index of key token in the token list
    value_index: int          # index of value token in the token list


@dataclass
class Preset:
    """Structured view of a parsed preset."""

    tokens: List[Token]
    parameters: List[Parameter]
    preset_name: str = ""     # value of the top-level "name" key
    file_header: str = ""     # token[0].value, e.g. "morgan"

    # Convenience: index by (module_path, key) → Parameter.
    by_path: Dict[Tuple[str, str], Parameter] = field(default_factory=dict)

    # Paths seen more than once. The file flattens its module tree, so two
    # sibling sub-modules sharing a name would collapse onto one path and a
    # write would silently hit only the last. No Morgan preset does this, but
    # nothing in the format prevents it, so callers can check rather than
    # assume.
    duplicates: List[Tuple[str, str]] = field(default_factory=list)

    # Records that name a parameter but store no value for it. They are not
    # parameters you can read or write, and they are not errors either, so they
    # are listed rather than dropped or faked.
    valueless: List[Tuple[str, str]] = field(default_factory=list)


def build(tokens: List[Token]) -> Preset:
    """Pair tokens into Parameters and identify sub-module structure."""
    parameters: List[Parameter] = []
    module_stack: List[str] = []
    expect_submodule_name = False

    preset = Preset(tokens=tokens, parameters=parameters)
    preset.file_header = tokens[0].value if tokens else ""

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if is_value_token(tok):
            # Stray value token (no preceding key) — skip. Could be the
            # second half of a subModels declaration consumed below.
            i += 1
            continue

        if is_record_marker(tok.value):
            record = read_record(tokens, i)
            if record is not None:
                name, value_index, end = record
                module_path = ".".join(module_stack)
                if value_index is None:
                    # Named but valueless. There is nothing to read and nothing
                    # to write -- the writer clones a template and mutates
                    # existing values, it cannot add a field -- so record the
                    # name and move on rather than inventing an empty value.
                    preset.valueless.append((module_path, name))
                    i = end
                    continue
                param = Parameter(
                    module_path=module_path,
                    key=name,
                    value=tokens[value_index].value,
                    key_index=i + 2,      # the `id` value token names it
                    value_index=value_index,
                )
                parameters.append(param)
                if (module_path, name) in preset.by_path:
                    preset.duplicates.append((module_path, name))
                preset.by_path[(module_path, name)] = param
                i = end
                continue

        if tok.value == "subModels":
            # The next non-value token is the new sub-module name. Pop the
            # current one and push the new name.
            expect_submodule_name = True
            i += 1
            continue

        if expect_submodule_name:
            # tok is the name of the sub-module entering scope.
            # Pop the previous sub-module at this depth (heuristic: replace
            # the deepest entry rather than nest, since the file flattens
            # everything alongside subModels markers).
            if module_stack:
                module_stack[-1] = tok.value
            else:
                module_stack.append(tok.value)
            expect_submodule_name = False
            i += 1
            continue

        # tok is a candidate KEY. Look ahead one token for its value.
        if i + 1 < len(tokens) and is_value_token(tokens[i + 1]):
            value_tok = tokens[i + 1]
            module_path = ".".join(module_stack)
            param = Parameter(
                module_path=module_path,
                key=tok.value,
                value=value_tok.value,
                key_index=i,
                value_index=i + 1,
            )
            parameters.append(param)
            if (module_path, tok.value) in preset.by_path:
                preset.duplicates.append((module_path, tok.value))
            preset.by_path[(module_path, tok.value)] = param
            if param.module_path == "" and param.key == "name":
                preset.preset_name = param.value
            i += 2
            continue

        # Bare-encoded key (e.g., isFavorite, appModel) — no string value.
        i += 1

    return preset


def set_parameter(preset: Preset, module_path: str, key: str, new_value: str) -> None:
    """Update a parameter's string value in both the token list and the index."""
    param = preset.by_path.get((module_path, key))
    if param is None:
        raise KeyError(f"No parameter {module_path!r}.{key!r} in preset")
    current = preset.tokens[param.value_index]
    if current.is_binary:
        # A binary value keeps its marker (the width is fixed) and is
        # re-encoded rather than length-patched.
        preset.tokens[param.value_index] = Token(
            raw_prefix=current.raw_prefix,
            value=new_value,
            terminator=current.terminator,
            payload=encode_payload(
                new_value,
                len(current.payload),
                opaque=is_opaque_value_prefix(current.raw_prefix),
            ),
        )
    else:
        preset.tokens[param.value_index] = Token(
            raw_prefix=fix_value_prefix(current.raw_prefix, new_value),
            value=new_value,
            terminator=current.terminator,
        )
    param.value = new_value
