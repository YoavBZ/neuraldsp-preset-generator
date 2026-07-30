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
from typing import Dict, List, Optional, Tuple

from .markers import fix_value_prefix, is_value_prefix
from .parser import Token

def is_value_token(tok: Token) -> bool:
    """True when this token is a VALUE rather than a key or structural marker.

    The byte rule lives in `markers.is_value_prefix` so it is stated once.
    """
    return is_value_prefix(tok.raw_prefix)


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
    preset.tokens[param.value_index] = Token(
        raw_prefix=fix_value_prefix(
            preset.tokens[param.value_index].raw_prefix, new_value
        ),
        value=new_value,
        terminator=preset.tokens[param.value_index].terminator,
    )
    param.value = new_value
