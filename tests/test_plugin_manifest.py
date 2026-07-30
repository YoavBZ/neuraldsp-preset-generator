"""The plugin manifest and skill frontmatter must be loadable by Claude Code.

Malformed skill frontmatter fails *silently*: Claude Code loads the body with
empty metadata, so the skill still runs but has no description to match against
and no pre-approved tools. That happened once already — `argument-hint: [a] [b]`
parses as a YAML flow sequence and threw away every field. These tests are the
guard, and they run without needing the `claude` CLI installed.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

yaml = pytest.importorskip("yaml", reason="pyyaml is needed to check frontmatter")

ROOT = pathlib.Path(__file__).parent.parent
MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))

# description + when_to_use are truncated past this in the skill listing.
LISTING_CAP = 1536
# The docs' guidance for keeping a skill body cheap; it stays in context all session.
BODY_LINE_GUIDANCE = 500


def frontmatter(path: pathlib.Path) -> dict:
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, f"{path} has no YAML frontmatter block"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict), f"{path} frontmatter is not a mapping: {data!r}"
    return data


def test_manifest_is_valid_json():
    data = json.loads(MANIFEST.read_text())
    assert data["name"], "name is the only required field and it namespaces everything"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", data["name"]), (
        f"name must be kebab-case with no spaces, got {data['name']!r}"
    )


def test_manifest_declares_useful_metadata():
    data = json.loads(MANIFEST.read_text())
    for field in ("description", "version", "author", "license", "keywords", "repository"):
        assert field in data, f"plugin.json is missing {field}"
    assert isinstance(data["keywords"], list), "keywords must be an array or the plugin fails to load"


def test_manifest_version_matches_the_package():
    """A stale version means users never receive updates."""
    pyproject = (ROOT / "pyproject.toml").read_text()
    declared = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
    assert json.loads(MANIFEST.read_text())["version"] == declared


def test_component_dirs_are_at_the_plugin_root_not_inside_claude_plugin():
    """The single most common plugin mistake per the docs."""
    for name in ("skills", "commands", "agents", "hooks"):
        assert not (ROOT / ".claude-plugin" / name).exists(), (
            f".claude-plugin/{name}/ must live at the plugin root instead"
        )
    assert (ROOT / "skills").is_dir()


def test_there_are_skills_to_load():
    assert SKILLS, "no skills/*/SKILL.md found"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_frontmatter_parses_as_yaml(skill):
    """The regression guard: malformed frontmatter drops every field silently."""
    frontmatter(skill)


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_frontmatter_fields_have_the_right_types(skill):
    data = frontmatter(skill)
    assert isinstance(data.get("name"), str)
    assert isinstance(data.get("description"), str) and data["description"].strip()
    for field in ("when_to_use", "argument-hint", "allowed-tools"):
        if field in data:
            assert isinstance(data[field], str), (
                f"{skill.parent.name}: {field} parsed as "
                f"{type(data[field]).__name__}, not a string. A value starting "
                f"with '[' becomes a YAML list — quote it."
            )


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_skill_name_matches_its_directory(skill):
    """In a plugin skill, frontmatter `name` sets the command's last segment."""
    assert frontmatter(skill)["name"] == skill.parent.name


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_listing_text_fits_the_budget(skill):
    data = frontmatter(skill)
    combined = len(data["description"]) + len(data.get("when_to_use", ""))
    assert combined <= LISTING_CAP, (
        f"{skill.parent.name}: description + when_to_use is {combined} chars, "
        f"over the {LISTING_CAP} cap — the tail is dropped from the listing"
    )


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_skill_body_stays_cheap(skill):
    """Skill content persists in context for the whole session, so every line is
    a recurring cost. Detail belongs in reference/ files loaded on demand."""
    lines = len(skill.read_text().splitlines())
    assert lines < BODY_LINE_GUIDANCE, (
        f"{skill.parent.name}: {lines} lines; move detail into reference/"
    )


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_linked_reference_files_exist(skill):
    """A skill that points at a missing file sends the agent nowhere."""
    body = skill.read_text()
    missing = []
    for target in re.findall(r"\]\((?!https?://)([^)#]+)\)", body):
        if not (skill.parent / target).resolve().exists():
            missing.append(target)
    assert not missing, f"{skill.parent.name} links to missing files: {missing}"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_scripts_referenced_by_skills_exist(skill):
    """Skill bodies invoke scripts via ${CLAUDE_PLUGIN_ROOT}; the paths must be real."""
    body = skill.read_text()
    missing = [
        rel
        for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w/.\-]+\.py)", body)
        if not (ROOT / rel).exists()
    ]
    assert not missing, f"{skill.parent.name} invokes missing scripts: {missing}"
