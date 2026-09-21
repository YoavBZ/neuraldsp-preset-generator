"""The plugin manifest and skill frontmatter must be loadable by Claude Code.

Malformed skill frontmatter fails *silently*: Claude Code loads the body with
empty metadata, so the skill still runs but has no description to match against
and no pre-approved tools. That happened once already — `argument-hint: [a] [b]`
parses as a YAML flow sequence and threw away every field. These tests are the
guard, and they run without needing the `claude` CLI installed.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess

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


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_plugin_internal_paths_are_root_relative(skill):
    """An installed plugin runs with the user's project as cwd, so a bare
    `packs/…` path in skill text resolves to the wrong place — or nowhere."""
    body = skill.read_text()
    bare = re.findall(
        r"(?<!\$\{CLAUDE_PLUGIN_ROOT\}/)`((?:packs|scripts|samples|format)/[\w<>/.\-]+)`",
        body,
    )
    assert not bare, (
        f"{skill.parent.name} refers to plugin files without "
        f"${{CLAUDE_PLUGIN_ROOT}}/: {sorted(set(bare))}"
    )


# What actually reaches a user's installed plugin. Deliberately not `tests/`,
# `docs/`, `.github/` or the top-level prose files: those change without changing
# what the plugin does.
SHIPPED = (
    ".claude-plugin/", "analysis/", "format/", "match/", "packs/", "pyproject.toml",
    "reference/", "samples/", "scripts/", "skills/",
)


def _git(*args):
    """Run a git command, or return None if it cannot answer."""
    try:
        done = subprocess.run(("git", "-C", str(ROOT)) + args,
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _unavailable(why: str):
    """Skip locally; fail in CI.

    A guard that silently skips is indistinguishable from a guard that passes,
    and that is the failure being fixed here — `test_manifest_version_matches_
    the_package` ran green for twenty-three PRs while checking nothing that
    mattered. Outside CI a developer may legitimately have no remote, a shallow
    clone, or no git at all. Inside CI, not being able to answer *is* the bug:
    it means the checkout no longer fetches enough history and the guard has
    stopped running where it is the only thing watching.
    """
    if os.environ.get("GITHUB_ACTIONS"):
        pytest.fail(
            f"the version guard could not run: {why}.\n"
            f"  This check is the only thing that catches a shipped change with "
            f"no version bump, so a skip here is a silent hole.\n"
            f"  Every job that runs the suite needs `fetch-depth: 0` on "
            f"actions/checkout."
        )
    # Deliberately GITHUB_ACTIONS and not CI. The remedy above names a GitHub
    # Actions input, and `CI=true` is set by GitLab, CircleCI, Travis and most
    # Jenkins jobs — all of which default to a shallow single-branch clone with
    # no `origin/main`. Keying on CI hard-failed those builds and told them to
    # edit a file they do not have.
    pytest.skip(f"{why} — not GitHub Actions, so the remedy would not apply")


def test_a_shipped_change_bumps_the_version():
    """A behaviour change with no version bump never reaches anybody.

    `test_manifest_version_matches_the_package` only checks the two declarations
    agree with *each other*, which they did throughout: the version sat at 0.4.0
    from PR #16 to PR #42 while twenty-three PRs merged — the Tone King
    calibration and benchmarks, the M7 response atlas and warm-start experiment,
    blind auditions, paired provenance. All of it was unreachable from an
    installed plugin, and nothing went red.

    The rule is deliberately blunt: any shipped path changing requires the
    declared version to differ from the merge base's. A docstring fix will
    therefore ask for a bump too. That is the cheap side of the trade — a version
    number costs nothing, and the expensive side is what happened above.
    """
    base = _git("merge-base", "HEAD", "origin/main")
    if base is None:
        _unavailable("no merge base with origin/main (shallow clone, or no remote)")

    changed = _git("diff", "--name-only", f"{base}...HEAD")
    if changed is None:
        _unavailable("could not diff against the merge base")
    touched = sorted(p for p in changed.splitlines() if p.startswith(SHIPPED))
    if not touched:
        return  # nothing a user would receive; no bump owed

    previous = _git("show", f"{base}:.claude-plugin/plugin.json")
    if previous is None:
        _unavailable("merge base has no plugin manifest to compare against")

    was = json.loads(previous)["version"]
    now = json.loads(MANIFEST.read_text())["version"]
    assert now != was, (
        f"{len(touched)} shipped path(s) changed but the version is still {now}:\n"
        + "\n".join(f"  {path}" for path in touched[:10])
        + (f"\n  … and {len(touched) - 10} more" if len(touched) > 10 else "")
        + f"\nBump it in .claude-plugin/plugin.json and pyproject.toml — they "
          f"must match, which test_manifest_version_matches_the_package checks."
    )


@pytest.mark.parametrize("env,outcome", [
    ({}, "skip"),
    # `CI=true` with no GitHub Actions is GitLab, CircleCI, Travis, most Jenkins
    # jobs — all of which default to a shallow single-branch clone with no
    # `origin/main`. Keying the hard failure on CI hard-failed those builds and
    # told them to set a GitHub Actions input they do not have.
    ({"CI": "true"}, "skip"),
    ({"GITHUB_ACTIONS": "true"}, "fail"),
    ({"CI": "true", "GITHUB_ACTIONS": "true"}, "fail"),
])
def test_the_version_guard_refuses_to_skip_quietly_on_github(monkeypatch, env, outcome):
    """A guard that skips looks exactly like a guard that passes.

    That is not hypothetical here: the version sat at 0.4.0 for twenty-three PRs
    with a green suite the whole way. So where this repo's CI runs — GitHub
    Actions, where the remedy applies and where the checkout is ours to fix — a
    guard that cannot answer has to go red. Everywhere else it skips, because a
    shallow clone on someone else's CI is not this repository's bug and the
    advice would not help them.
    """
    for name in ("CI", "GITHUB_ACTIONS"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(BaseException) as raised:
        _unavailable("no merge base with origin/main")

    kind = type(raised.value).__name__
    if outcome == "fail":
        assert kind == "Failed", f"GitHub Actions must not skip this guard, got {kind}"
        assert "fetch-depth" in str(raised.value), "say how to fix it"
    else:
        assert kind == "Skipped", (
            f"a shallow clone outside GitHub Actions is not this repo's bug, got {kind}"
        )
