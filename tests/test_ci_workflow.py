"""Regression tests for the GitHub Actions trigger contract."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_pull_request_commits_do_not_start_duplicate_ci_runs() -> None:
    workflow = yaml.load(CI_WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    triggers = workflow["on"]

    assert "pull_request" in triggers
    assert triggers["push"]["branches"] == ["main"]
