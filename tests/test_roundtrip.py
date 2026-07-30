"""parse → write must produce byte-identical output for every sample."""

from __future__ import annotations

import pathlib

import pytest

from format.parser import parse
from format.writer import write
from packs.loader import list_packs
from packs.paths import all_presets

# Every preset this installation can see: the bundled example plus anything the
# user has added to their own template directories.
SAMPLE_FILES = all_presets(list_packs())


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_roundtrip_bytes_exact(sample: pathlib.Path) -> None:
    original = sample.read_bytes()
    tokens = parse(original)
    rewritten = write(tokens)
    assert rewritten == original, (
        f"Round-trip mismatch for {sample.name}: "
        f"{len(original)} bytes in, {len(rewritten)} bytes out"
    )


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_tokens_have_consistent_structure(sample: pathlib.Path) -> None:
    """Sanity: at least one token, the first token is the preset file header."""
    tokens = parse(sample.read_bytes())
    assert len(tokens) > 0
    assert tokens[0].raw_prefix == b""  # file starts with a printable string
    assert tokens[0].value != ""


def test_sample_files_present() -> None:
    """Fail loudly if there are no presets, so the suite isn't silently green.

    Most of this file is parametrised over the preset library; with an empty
    library those tests would collect zero cases and pass vacuously.
    """
    assert SAMPLE_FILES, (
        "No presets found. The bundled samples/Example_Clean_PR12.xml should "
        "always be present; add your own under <data root>/packs/<id>/templates/."
    )


@pytest.mark.parametrize(
    "name",
    [
        "Émile Lead",            # non-ASCII FIRST byte — the failure case
        "É" + "x" * 200,         # non-ASCII first byte, long
        "日本語プリセット",         # entirely non-ASCII
        "Café Clean",            # non-ASCII interior (always worked)
        "Ω",                     # 2 bytes total
    ],
    ids=["leading-accent", "leading-accent-long", "all-cjk", "interior", "tiny"],
)
def test_non_ascii_values_stay_addressable(name: str) -> None:
    """A value whose first byte is non-ASCII must not vanish from the structured
    view.

    The prefix scan skips non-printable bytes, and a UTF-8 lead byte is
    non-printable — so scanning past the value marker used to swallow the
    value's own first byte, leaving a token that no longer looked like a value.
    The key was then paired with nothing and the parameter disappeared: the file
    still round-tripped byte-exact, but our own tools could no longer read or
    re-edit it.
    """
    from format.structured import build, set_parameter

    original = SAMPLE_FILES[0].read_bytes()
    before = build(parse(original))

    preset = build(parse(original))
    set_parameter(preset, "", "name", name)
    rewritten = write(preset.tokens)

    after = build(parse(rewritten))
    assert after.preset_name == name
    assert ("", "name") in after.by_path
    assert len(after.parameters) == len(before.parameters), (
        "mutating a value must not change how many parameters are visible"
    )
