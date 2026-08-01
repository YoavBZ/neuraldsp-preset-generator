"""End-to-end tests for the writer, driven through its command line.

These exist because a unit test of `packs.recipes.stack()` passed while the CLI
that calls it resolved the amp from the wrong source — the EQ silently landed on
the template's amp instead of the one the recipe stack selected. Testing the
library function proved nothing about the wiring, and the failure was invisible
because a misdirected EQ writes a real parameter on an inactive module.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
APPLY = REPO_ROOT / "scripts" / "apply_spec.py"
EXAMPLE = REPO_ROOT / "samples" / "Example_Clean_PR12.xml"


def run(*args):
    return subprocess.run(
        [sys.executable, str(APPLY), "--template", str(EXAMPLE), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def changed_modules(stdout: str, suffix: str) -> set:
    """Module names appearing in the change list that end with `suffix`."""
    found = set()
    for line in stdout.splitlines():
        parts = line.strip().split()
        if parts and "/" in parts[0]:
            module = parts[0].split("/")[0]
            if module.endswith(suffix):
                found.add(module)
    return found


@pytest.fixture
def out(tmp_path):
    return tmp_path / "out.xml"


# --- the regression this file was created for -----------------------------


def test_eq_recipe_follows_the_amp_the_stack_selects(out):
    result = run(
        "--recipe", "amp/sw50r-singing-lead", "--recipe", "eq/lead-focus",
        "--out", str(out), "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    assert changed_modules(result.stdout, "EQ") == {"sw50rEQ"}, (
        "the EQ must land on the amp the stack selects, not the template's"
    )


def test_spec_amp_overrides_the_recipe_amp(tmp_path, out):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(
        {"parameters": [{"module": "", "key": "selectedAmp", "value": "AC20"}]}
    ))
    result = run(
        "--recipe", "amp/sw50r-singing-lead", "--recipe", "eq/lead-focus",
        "--spec", str(spec), "--out", str(out), "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    assert changed_modules(result.stdout, "EQ") == {"ac20EQ"}, (
        "--spec is applied last, so its amp is the one that ends up live"
    )


def test_eq_recipe_alone_uses_the_template_amp(out):
    """No amp recipe and no spec: fall back to whatever the template already is."""
    result = run("--recipe", "eq/lead-focus", "--out", str(out), "--dry-run")
    assert result.returncode == 0, result.stderr
    assert changed_modules(result.stdout, "EQ") == {"pr12EQ"}


# --- recipes end to end ---------------------------------------------------


def test_a_full_stack_writes_a_valid_preset(out):
    result = run(
        "--recipe", "amp/sw50r-singing-lead", "--recipe", "compressor/lead-smoothing",
        "--recipe", "drive1/singing-lead-push", "--recipe", "eq/lead-focus",
        "--recipe", "delay/classic-lead", "--recipe", "reverb/large-lead",
        "--recipe", "output/lead", "--bpm", "96",
        "--name", "Stacked Lead", "--strip-irs", "--out", str(out),
    )
    assert result.returncode == 0, result.stderr

    from format.parser import parse, parse_file
    from format.structured import build
    from format.writer import write

    raw = out.read_bytes()
    assert write(parse(raw)) == raw, "output must round-trip byte-exact"
    preset = build(parse_file(str(out)))
    assert preset.preset_name == "Stacked Lead"
    assert preset.by_path[("", "selectedAmp")].value == "2"          # SW50R
    assert preset.by_path[("delay", "delayTime")].value == "625"     # 1/4 at 96 BPM
    assert preset.by_path[("sw50rEQ", "sw50rEQBand5")].value == "1.5"


def test_note_division_without_a_tempo_is_refused(out):
    result = run("--recipe", "delay/classic-lead", "--out", str(out), "--dry-run")
    assert result.returncode == 2
    assert "needs a tempo" in result.stderr


def test_unknown_recipe_lists_the_layer(out):
    result = run("--recipe", "eq/nope", "--out", str(out), "--dry-run")
    assert result.returncode == 2
    assert "natural-flat" in result.stderr


def test_nothing_to_apply_is_an_error(out):
    result = run("--out", str(out), "--dry-run")
    assert result.returncode == 2
    assert "Nothing to apply" in result.stderr


# --- guards ---------------------------------------------------------------


def test_dry_run_honours_the_overwrite_guard(out):
    """A preview that reports success where the real run would refuse is a lie."""
    out.write_bytes(EXAMPLE.read_bytes())
    result = run("--recipe", "compressor/off", "--out", str(out), "--dry-run")
    assert result.returncode == 2
    assert "already exists" in result.stderr


def test_refuses_to_overwrite_its_own_template():
    result = run("--recipe", "compressor/off", "--out", str(EXAMPLE), "--force")
    assert result.returncode == 2
    assert "same file as --template" in result.stderr
    assert EXAMPLE.read_bytes(), "the template must be untouched"


def test_failed_run_writes_nothing(tmp_path, out):
    """Validation happens before any write, so a bad value leaves no partial file."""
    spec = tmp_path / "bad.json"
    spec.write_text(json.dumps(
        {"parameters": [{"module": "", "key": "selectedAmp", "value": 99}]}
    ))
    result = run("--spec", str(spec), "--out", str(out))
    assert result.returncode == 2
    assert not out.exists(), "nothing should be written when a value is rejected"


def test_raw_cannot_write_a_read_only_parameter(tmp_path, out):
    """`raw` bypasses translation and range checks. It must not bypass the
    read-only guard — corrupting the format-version field is not what the
    escape hatch is for."""
    spec = tmp_path / "raw.json"
    spec.write_text(json.dumps({"parameters": [
        {"module": "", "key": "version", "value": "9.9.9", "raw": True}
    ]}))
    result = run("--spec", str(spec), "--out", str(out))
    assert result.returncode == 2
    assert "read-only" in result.stderr
    assert not out.exists()


def test_raw_still_works_for_an_ir_path(tmp_path, out):
    """The escape hatch must keep doing its actual job."""
    spec = tmp_path / "raw.json"
    spec.write_text(json.dumps({"parameters": [
        {"module": "cabParameters", "key": "leftChosenIRFilePath",
         "value": "/Users/me/IRs/cab.wav", "raw": True}
    ]}))
    result = run("--spec", str(spec), "--out", str(out))
    assert result.returncode == 0, result.stderr
    from format.parser import parse_file
    from format.structured import build
    preset = build(parse_file(str(out)))
    assert preset.by_path[("cabParameters", "leftChosenIRFilePath")].value == (
        "/Users/me/IRs/cab.wav"
    )


def test_out_expands_a_tilde(tmp_path, monkeypatch):
    """A quoted `~/…` path used to create a literal directory named '~' in the
    working directory, and report success."""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = subprocess.run(
        [sys.executable, str(APPLY), "--template", str(EXAMPLE),
         "--recipe", "compressor/off", "--out", "~/preset.xml"],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "preset.xml").exists(), "the tilde should resolve to $HOME"
    assert not (tmp_path / "~").exists(), "a literal '~' directory is the bug"


def test_missing_value_field_reports_cleanly(tmp_path, out):
    """This used to raise KeyError from the amp-resolution pass, before the
    entry validator ever ran."""
    spec = tmp_path / "bad.json"
    spec.write_text(json.dumps(
        {"parameters": [{"module": "", "key": "selectedAmp"}]}
    ))
    result = run("--spec", str(spec), "--recipe", "eq/lead-focus",
                 "--out", str(out), "--dry-run")
    assert result.returncode == 2
    assert "missing" in result.stderr and "value" in result.stderr
    assert "Traceback" not in result.stderr


def test_list_recipes_needs_no_other_arguments():
    result = subprocess.run(
        [sys.executable, str(APPLY), "--list-recipes"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert "sw50r-singing-lead" in result.stdout
    assert "classic-lead" in result.stdout


def test_strip_irs_reports_the_mic_change_in_human_terms(tmp_path):
    """The change list is the thing the user approves, so it has to be true.

    --strip-irs clears the IR path *and* moves the mic selector off "Custom IR".
    Both were once reported as "(cleared)", which was wrong for the selector: it
    is set, not emptied, and 10 means something. The bundled example is IR-free,
    so a template that actually uses an IR has to be synthesised here — which is
    why this went unnoticed: every existing --strip-irs test was a no-op.
    """
    from format.parser import parse_file
    from format.structured import build, set_parameter
    from format.writer import write_file

    template = tmp_path / "WithIR.xml"
    preset = build(parse_file(str(EXAMPLE)))
    for side in ("left", "right"):
        set_parameter(preset, "cabParameters", f"{side}ChosenIRFilePath",
                      f"/Users/someone/IRs/{side}.wav")
        set_parameter(preset, "cabParameters", f"{side}MicType", "10")
    write_file(str(template), preset.tokens)

    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"parameters": []}))
    result = subprocess.run(
        [sys.executable, str(APPLY), "--template", str(template),
         "--spec", str(spec), "--strip-irs", "--out", str(tmp_path / "o.xml")],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr

    assert "leftMicType" in result.stdout
    # Named at both ends, like every other row — not a bare index, not "(cleared)".
    assert "Custom IR  ->  Dynamic 57" in result.stdout
    assert "Custom IR  ->  Condenser 184" in result.stdout
    assert "MicType" not in [
        line.split()[0].split("/")[-1]
        for line in result.stdout.splitlines()
        if "(cleared)" in line
    ], "a mic selector is set, not cleared"

    written = build(parse_file(str(tmp_path / "o.xml")))
    assert written.by_path[("cabParameters", "leftMicType")].value == "0"
    assert written.by_path[("cabParameters", "rightMicType")].value == "4"
