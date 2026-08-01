"""Bootstrapping a pack for a plugin the tool doesn't know yet.

The point of this path is to turn "add a plugin" from a code change into a
draft-then-correct conversation. What matters is that the draft is (a)
immediately loadable, so the rest of the tooling works against it, and (b)
honest about what it cannot know — a draft that looked authoritative would be
worse than none, because ranges and selector members genuinely cannot be
inferred from a preset.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
BOOTSTRAP = REPO_ROOT / "scripts" / "bootstrap_pack.py"
EXAMPLE = REPO_ROOT / "samples" / "Example_Clean_PR12.xml"

from format.parser import parse_file
from format.structured import Token, build
from format.writer import write_file
from packs.loader import PACKS_DIR


def run(*args):
    return subprocess.run(
        [sys.executable, str(BOOTSTRAP), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


@pytest.fixture
def unknown_preset(tmp_path):
    """A preset that claims to come from a plugin we have no pack for."""
    preset = build(parse_file(str(EXAMPLE)))
    preset.tokens[0] = Token(raw_prefix=b"", value="testplugin", terminator=b"\x00")
    path = tmp_path / "Unknown.xml"
    write_file(str(path), preset.tokens)
    return path


@pytest.fixture
def cleanup_pack():
    """Remove any pack the test drafts, so the repo is left as it was."""
    created = []
    yield created
    for pack_id in created:
        directory = PACKS_DIR / pack_id
        if directory.exists():
            for child in directory.iterdir():
                child.unlink()
            directory.rmdir()


def test_refuses_a_plugin_that_is_already_supported():
    result = run("--preset", str(EXAMPLE))
    assert result.returncode == 2
    assert "already supported" in result.stderr
    assert "morgan" in result.stderr


def test_drafts_a_loadable_pack(unknown_preset, cleanup_pack):
    cleanup_pack.append("testplugin")
    result = run("--preset", str(unknown_preset), "--display-name", "Test Plugin")
    assert result.returncode == 0, result.stderr

    from packs.loader import detect_pack, list_packs, load_pack

    assert "testplugin" in list_packs()
    pack = load_pack("testplugin")
    assert pack.display_name == "Test Plugin"
    assert pack.file_header == "testplugin"
    assert len(pack.parameters) == len(build(parse_file(str(unknown_preset))).parameters)
    assert detect_pack("testplugin").pack_id == "testplugin"


def test_draft_covers_every_parameter_in_the_preset(unknown_preset, cleanup_pack):
    cleanup_pack.append("testplugin")
    assert run("--preset", str(unknown_preset)).returncode == 0

    from packs.loader import load_pack

    pack = load_pack("testplugin")
    preset = build(parse_file(str(unknown_preset)))
    missing = [
        f"{p.module_path}/{p.key}"
        for p in preset.parameters
        if pack.get(p.module_path, p.key) is None
    ]
    assert not missing, f"draft misses parameters present in the preset: {missing}"


def test_draft_declares_no_ranges_and_no_selector_members(unknown_preset, cleanup_pack):
    """Neither can be inferred from a preset. Inventing them would put guesses
    into the file that is supposed to be the contract."""
    cleanup_pack.append("testplugin")
    assert run("--preset", str(unknown_preset)).returncode == 0

    manifest = json.loads((PACKS_DIR / "testplugin" / "manifest.json").read_text())
    for path, entry in manifest["parameters"].items():
        assert "min" not in entry and "max" not in entry, (
            f"{path} declares a range, which cannot be known from one preset"
        )
        if entry["kind"] == "enum":
            assert entry.get("members") is None
            assert entry.get("needs_confirmation") is True


def test_draft_is_marked_as_a_draft(unknown_preset, cleanup_pack):
    cleanup_pack.append("testplugin")
    assert run("--preset", str(unknown_preset)).returncode == 0
    manifest = json.loads((PACKS_DIR / "testplugin" / "manifest.json").read_text())
    assert manifest["draft"] is True
    assert manifest["drafted_from"] == unknown_preset.name
    assert "guess" in manifest["description"].lower()


def test_output_says_what_it_cannot_know(unknown_preset, cleanup_pack):
    """The report is the product here: a draft without its caveats is a trap."""
    cleanup_pack.append("testplugin")
    result = run("--preset", str(unknown_preset))
    assert result.returncode == 0
    assert "RANGES" in result.stdout
    assert "SELECTORS" in result.stdout
    assert "probe.py" in result.stdout
    assert "GUESSED KINDS" in result.stdout


def test_will_not_clobber_an_existing_draft(unknown_preset, cleanup_pack):
    cleanup_pack.append("testplugin")
    assert run("--preset", str(unknown_preset)).returncode == 0
    second = run("--preset", str(unknown_preset))
    assert second.returncode == 2
    assert "--force" in second.stderr
    assert run("--preset", str(unknown_preset), "--force").returncode == 0


def test_missing_preset_is_reported_cleanly(tmp_path):
    result = run("--preset", str(tmp_path / "nope.xml"))
    assert result.returncode == 2
    assert "not found" in result.stderr
    assert "Traceback" not in result.stderr


# --- formats this tool cannot draft ---------------------------------------
# Neural DSP presets are not all shaped like Morgan's. Tone King Imperial MKII
# stores numbers as raw IEEE-754 doubles inside repeated PARAM records, and the
# structured layer — which assumes one named key per printable value — mis-pairs
# the tokens and yields a handful of parameters that do not exist. It drafted a
# plausible-looking six-parameter manifest, one of whose names was two bytes of
# a float glued to the next key. Refusing is the only honest outcome until
# format/ can decode those values.
#
# The fixtures below are synthetic. Real presets are Neural DSP's factory
# content and are not committed — see NOTICE.md.


@pytest.fixture
def binary_valued_preset(tmp_path):
    """A preset whose numbers are raw doubles rather than printable strings."""
    import struct

    body = b"otherplugin\x00"
    for i, key in enumerate(["ampType", "gain", "bass"]):
        body += key.encode() + b"\x00"
        body += b"\x01\x09\x04" + struct.pack("<d", float(i))
    path = tmp_path / "BinaryValues.xml"
    path.write_bytes(body)
    return path


@pytest.fixture
def record_shaped_preset(tmp_path):
    """A preset that names parameters inside repeated records, so the same few
    key names repeat instead of one key per parameter."""
    body = b"recordplugin\x00"
    for i in range(40):
        body += b"PARAM\x00"
        body += b"id\x00" + b"\x01\x09\x05" + f"param{i}".encode() + b"\x00"
        body += b"value\x00" + b"\x01\x05\x05" + b"0.5" + b"\x00"
    path = tmp_path / "Records.xml"
    path.write_bytes(body)
    return path


def test_binary_valued_format_is_refused_not_drafted(binary_valued_preset):
    """The failure mode this guards against is a draft that looks fine."""
    result = run("--preset", str(binary_valued_preset))
    assert result.returncode == 2
    assert "binary doubles" in result.stderr
    assert "Traceback" not in result.stderr
    # It must say the file itself is intact, or the reader will assume the
    # preset is damaged and go looking for a problem that isn't there.
    assert "losslessly" in result.stderr
    assert not (PACKS_DIR / "otherplugin").exists()


def test_record_shaped_format_is_refused_not_drafted(record_shaped_preset):
    result = run("--preset", str(record_shaped_preset))
    assert result.returncode == 2
    assert "distinct key names" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (PACKS_DIR / "recordplugin").exists()


def test_a_normal_preset_is_still_drafted(unknown_preset, cleanup_pack):
    """The guards must not fire on the shape the tool does support."""
    cleanup_pack.append("testplugin")
    assert run("--preset", str(unknown_preset)).returncode == 0
