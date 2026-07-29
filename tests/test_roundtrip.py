"""parse → write must produce byte-identical output for every sample."""

from __future__ import annotations

import pathlib

import pytest

from format.parser import parse
from format.writer import write

SAMPLES_DIR = pathlib.Path(__file__).parent.parent / "samples"
SAMPLE_FILES = sorted(SAMPLES_DIR.glob("*.xml"))


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
    """Fail loudly if samples/ is empty so the suite isn't silently green."""
    assert SAMPLE_FILES, (
        "No sample preset files found in samples/. "
        "Drop a few Morgan .xml presets there before running the suite."
    )
