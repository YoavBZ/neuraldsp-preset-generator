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
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
BOOTSTRAP = REPO_ROOT / "scripts" / "bootstrap_pack.py"
EXAMPLE = REPO_ROOT / "samples" / "Example_Clean_PR12.xml"

from format.parser import parse_file
from format.structured import Token, build
from format.writer import write_file
from packs import loader


def run(root, *args):
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "bootstrap_pack.py"), *args],
        capture_output=True,
        text=True,
        cwd=str(root),
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
def plugin_root(tmp_path, monkeypatch):
    """A throwaway copy of the plugin to draft into.

    `packs/loader.py` derives `PACKS_DIR` from its own `__file__`, so a copy of
    the tree is a working installation — the same trick `tests/test_skills.py`
    uses for `drafted_plugin_root`. Drafting into it rather than into the
    repository is not tidiness. Ten tests in this file draft the *same* pack id
    into the *same* directory, which was invisible while pytest ran them one at
    a time and became four to seven failures a run the moment pytest-xdist
    started distributing per test: one worker's teardown deleted the pack
    another was still reading, and a third found it already drafted.

    The in-process loader is pointed at the copy too, because several tests
    below check that what the script wrote is loadable.
    """
    skip = shutil.ignore_patterns("templates", "__pycache__", "*.xml",
                                  "observed.json", "response_atlas_*.json")
    for name in ("scripts", "packs", "format"):
        shutil.copytree(REPO_ROOT / name, tmp_path / name, ignore=skip)
    monkeypatch.setattr(loader, "PACKS_DIR", tmp_path / "packs")
    return tmp_path


def test_refuses_a_plugin_that_is_already_supported(plugin_root):
    result = run(plugin_root, "--preset", str(EXAMPLE))
    assert result.returncode == 2
    assert "already supported" in result.stderr
    assert "morgan" in result.stderr


def test_drafts_a_loadable_pack(unknown_preset, plugin_root):
    result = run(plugin_root, "--preset", str(unknown_preset), "--display-name", "Test Plugin")
    assert result.returncode == 0, result.stderr

    from packs.loader import detect_pack, list_packs, load_pack

    assert "testplugin" in list_packs()
    pack = load_pack("testplugin")
    assert pack.display_name == "Test Plugin"
    assert pack.file_header == "testplugin"
    assert len(pack.parameters) == len(build(parse_file(str(unknown_preset))).parameters)
    assert detect_pack("testplugin").pack_id == "testplugin"


def test_draft_covers_every_parameter_in_the_preset(unknown_preset, plugin_root):
    assert run(plugin_root, "--preset", str(unknown_preset)).returncode == 0

    from packs.loader import load_pack

    pack = load_pack("testplugin")
    preset = build(parse_file(str(unknown_preset)))
    missing = [
        f"{p.module_path}/{p.key}"
        for p in preset.parameters
        if pack.get(p.module_path, p.key) is None
    ]
    assert not missing, f"draft misses parameters present in the preset: {missing}"


def test_draft_declares_no_ranges_and_no_selector_members(unknown_preset, plugin_root):
    """Neither can be inferred from a preset. Inventing them would put guesses
    into the file that is supposed to be the contract."""
    assert run(plugin_root, "--preset", str(unknown_preset)).returncode == 0

    manifest = json.loads((plugin_root / "packs" / "testplugin" / "manifest.json").read_text())
    for path, entry in manifest["parameters"].items():
        assert "min" not in entry and "max" not in entry, (
            f"{path} declares a range, which cannot be known from one preset"
        )
        if entry["kind"] == "enum":
            assert entry.get("members") is None
            assert entry.get("needs_confirmation") is True


def test_guessed_kinds_survive_into_the_write_path(unknown_preset, plugin_root):
    """`needs_review` is only worth writing if it reaches the person writing a
    value. It was written to the manifest and then dropped by the loader, so
    every guessed kind was applied in silence — the whole round trip is the test.
    """
    assert run(plugin_root, "--preset", str(unknown_preset)).returncode == 0

    manifest = json.loads((plugin_root / "packs" / "testplugin" / "manifest.json").read_text())
    guessed = {p for p, e in manifest["parameters"].items() if e.get("needs_review")}
    assert guessed, "a draft of a real preset should be guessing at some kinds"

    from packs.loader import load_pack

    pack = load_pack("testplugin")
    assert {p for p, s in pack.parameters.items() if s.needs_review} == guessed

    spec = next(s for s in pack.parameters.values() if s.needs_review and s.kind == "rotation")
    warnings: list[str] = []
    assert pack.to_stored(spec, 50, warnings=warnings) == "0.5"
    assert any("needs_review" in w for w in warnings), (
        "a value written through a guessed kind must say so"
    )


def test_draft_is_marked_as_a_draft(unknown_preset, plugin_root):
    assert run(plugin_root, "--preset", str(unknown_preset)).returncode == 0
    manifest = json.loads((plugin_root / "packs" / "testplugin" / "manifest.json").read_text())
    assert manifest["draft"] is True
    assert manifest["drafted_from"] == unknown_preset.name
    assert "guess" in manifest["description"].lower()


def test_output_says_what_it_cannot_know(unknown_preset, plugin_root):
    """The report is the product here: a draft without its caveats is a trap."""
    result = run(plugin_root, "--preset", str(unknown_preset))
    assert result.returncode == 0
    assert "RANGES" in result.stdout
    assert "SELECTORS" in result.stdout
    assert "probe.py" in result.stdout
    assert "GUESSED KINDS" in result.stdout


def test_will_not_clobber_an_existing_draft(unknown_preset, plugin_root):
    assert run(plugin_root, "--preset", str(unknown_preset)).returncode == 0
    second = run(plugin_root, "--preset", str(unknown_preset))
    assert second.returncode == 2
    assert "--force" in second.stderr
    assert run(plugin_root, "--preset", str(unknown_preset), "--force").returncode == 0


def test_missing_preset_is_reported_cleanly(plugin_root, tmp_path):
    result = run(plugin_root, "--preset", str(tmp_path / "nope.xml"))
    assert result.returncode == 2
    assert "not found" in result.stderr
    assert "Traceback" not in result.stderr


# --- formats this tool cannot draft ---------------------------------------
# Tone King's shape — 8-byte doubles inside `PARAM {id, value}` records — is now
# understood, so it drafts rather than being refused. What is still refused is
# the shape we would get wrong *silently*: a binary width we cannot decode, and
# a record layout that is not the one format/structured.py knows.
#
# The fixtures below are synthetic. Real presets are Neural DSP's factory
# content and are not committed — see NOTICE.md.


@pytest.fixture
def binary_valued_preset(tmp_path):
    """A preset whose numbers are binary at a width nobody has decoded."""
    body = b"otherplugin\x00"
    for i, key in enumerate(["ampType", "gain", "bass"]):
        body += key.encode() + b"\x00"
        # 0x05 -> a 4-byte payload: plausibly a float32, but unverified.
        body += b"\x01\x05\x04" + bytes([i, 0, 0, 0])
    path = tmp_path / "BinaryValues.xml"
    path.write_bytes(body)
    return path


@pytest.fixture
def record_shaped_preset(tmp_path):
    """A record layout that is NOT the `PARAM {id, value}` shape we understand,
    so the same few key names repeat instead of one key per parameter."""
    body = b"recordplugin\x00"
    for i in range(40):
        body += b"ENTRY\x00"
        body += b"tag\x00" + b"\x01\x09\x05" + f"param{i}".encode() + b"\x00"
        body += b"data\x00" + b"\x01\x05\x05" + b"0.5" + b"\x00"
    path = tmp_path / "Records.xml"
    path.write_bytes(body)
    return path


def test_undecodable_binary_width_is_refused_not_drafted(binary_valued_preset, plugin_root):
    """The failure mode this guards against is a draft that looks fine.

    An 8-byte double is understood; anything else would be drafted as hex, and
    writing it would be a guess dressed as a value."""
    result = run(plugin_root, "--preset", str(binary_valued_preset))
    assert result.returncode == 2
    assert "4 bytes wide" in result.stderr
    assert "Traceback" not in result.stderr
    # It must say the file itself is intact, or the reader will assume the
    # preset is damaged and go looking for a problem that isn't there.
    assert "8-byte doubles" in result.stderr and "nothing is corrupt" in result.stderr
    assert not (plugin_root / "packs" / "otherplugin").exists()


def test_record_shaped_format_is_refused_not_drafted(record_shaped_preset, plugin_root):
    result = run(plugin_root, "--preset", str(record_shaped_preset))
    assert result.returncode == 2
    assert "distinct key names" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (plugin_root / "packs" / "recordplugin").exists()


def test_a_normal_preset_is_still_drafted(unknown_preset, plugin_root):
    """The guards must not fire on the shape the tool does support."""
    assert run(plugin_root, "--preset", str(unknown_preset)).returncode == 0
