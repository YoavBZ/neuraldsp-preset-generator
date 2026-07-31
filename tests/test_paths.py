"""Where data goes. Getting this wrong loses the user's preset library.

When installed as a Claude Code plugin, the install directory is ephemeral — it
changes on every update and the old one is deleted. Anything generated or
user-supplied has to live outside it, under ${CLAUDE_PLUGIN_DATA}. These tests
pin the resolution order so a future refactor can't quietly reintroduce writing
state into the install directory.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

from packs import paths


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Each test starts with no data-root override and no relevant env vars."""
    paths.set_data_root(None)
    monkeypatch.delenv("NDSP_PRESET_DATA", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)
    yield
    paths.set_data_root(None)


def test_code_root_is_derived_from_file_not_environment(monkeypatch):
    """The plugin's own modules are inside the install directory, so __file__ is
    always correct. An env var could be stale or wrong; we must not depend on it."""
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/nonsense/elsewhere")
    assert paths.PLUGIN_ROOT == pathlib.Path(paths.__file__).resolve().parents[1]
    assert (paths.PLUGIN_ROOT / "packs" / "paths.py").exists()


def test_defaults_to_repo_root_in_a_clone():
    assert paths.data_root() == paths.PLUGIN_ROOT
    assert paths.is_ephemeral_data_root()


def test_claude_plugin_data_wins_over_the_install_dir(monkeypatch, tmp_path):
    """The whole point: an installed plugin must not write into its own dir."""
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    assert paths.data_root() == tmp_path.resolve()
    assert not paths.is_ephemeral_data_root()
    assert paths.observed_path("morgan") == (
        tmp_path.resolve() / "packs" / "morgan" / "observed.json"
    )


def test_ndsp_preset_data_beats_claude_plugin_data(monkeypatch, tmp_path):
    mine, theirs = tmp_path / "mine", tmp_path / "theirs"
    monkeypatch.setenv("NDSP_PRESET_DATA", str(mine))
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(theirs))
    assert paths.data_root() == mine.resolve()


def test_explicit_override_beats_every_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("NDSP_PRESET_DATA", str(tmp_path / "env1"))
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "env2"))
    paths.set_data_root(tmp_path / "flag")
    assert paths.data_root() == (tmp_path / "flag").resolve()


def test_override_can_be_cleared(monkeypatch, tmp_path):
    paths.set_data_root(tmp_path)
    assert paths.data_root() == tmp_path.resolve()
    paths.set_data_root(None)
    assert paths.data_root() == paths.PLUGIN_ROOT


def test_user_paths_expand_a_tilde(monkeypatch):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", "~/some-plugin-data")
    assert "~" not in str(paths.data_root())
    assert paths.data_root().is_absolute()


def test_generated_and_user_data_are_per_pack(monkeypatch, tmp_path):
    """A preset from one plugin must not land in another plugin's catalog."""
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    assert paths.observed_path("morgan") != paths.observed_path("gojira")
    assert paths.templates_dir("morgan") != paths.templates_dir("gojira")


def test_bundled_example_is_always_visible():
    """It ships with the code, so it is reachable with no data directory set."""
    names = [p.name for p in paths.bundled_presets()]
    assert "Example_Clean_PR12.xml" in names


def test_user_presets_are_found_and_merged(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    templates = paths.templates_dir("morgan")
    templates.mkdir(parents=True)
    source = paths.bundled_presets()[0]
    (templates / "Mine.xml").write_bytes(source.read_bytes())

    assert [p.name for p in paths.user_presets("morgan")] == ["Mine.xml"]
    everything = [p.name for p in paths.all_presets(["morgan"])]
    assert "Mine.xml" in everything
    assert "Example_Clean_PR12.xml" in everything


def test_missing_directories_are_not_an_error(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "does-not-exist"))
    assert paths.user_presets("morgan") == []
    assert paths.all_presets(["morgan"])  # the bundled example still shows up


def test_all_presets_deduplicates(monkeypatch, tmp_path):
    """The same file reachable by two routes must be listed once.

    Constructed with a symlink, because that is the only way the bundled and
    user locations actually coincide — an earlier version of this test set the
    data root to the repo and asserted uniqueness, but the templates directory
    did not exist, so no duplicate was ever created and the assertion held even
    with de-duplication removed entirely.
    """
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    templates = paths.templates_dir("morgan")
    templates.mkdir(parents=True)
    bundled = paths.bundled_presets()[0]
    try:
        (templates / bundled.name).symlink_to(bundled)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")

    both_routes = paths.bundled_presets() + paths.user_presets("morgan")
    assert len(both_routes) == 2, "the file is reachable two ways"
    assert len({p.resolve() for p in both_routes}) == 1, "but it is one file"

    assert len(paths.all_presets(["morgan"])) == 1, (
        "all_presets must collapse the duplicate, or the preset would be parsed "
        "twice and counted twice in the observed catalog"
    )


def test_describe_roots_flags_the_ephemeral_case(monkeypatch, tmp_path):
    assert "same as the plugin directory" in paths.describe_roots()
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    assert "same as the plugin directory" not in paths.describe_roots()


def test_empty_data_dir_is_rejected_not_ignored():
    """An empty --data-dir used to clear the override silently, falling back to
    the plugin directory — the one place data must not be written."""
    with pytest.raises(ValueError, match="cannot be empty"):
        paths.set_data_root("")
    with pytest.raises(ValueError, match="cannot be empty"):
        paths.set_data_root("   ")
    paths.set_data_root(None)  # None still means "no override"
    assert paths.data_root() == paths.PLUGIN_ROOT


def test_empty_data_dir_fails_at_the_command_line_too():
    """`--data-dir "$SOME_UNSET_VAR"` is the realistic way to produce it, so the
    rejection has to reach the user as a usage error, not a traceback."""
    result = subprocess.run(
        [
            sys.executable,
            str(paths.PLUGIN_ROOT / "scripts" / "show.py"),
            str(paths.bundled_presets()[0]),
            "--data-dir",
            "",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "cannot be empty" in result.stderr
    assert "Traceback" not in result.stderr
