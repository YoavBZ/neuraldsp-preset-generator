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
