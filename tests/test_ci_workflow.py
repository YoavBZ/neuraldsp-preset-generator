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


def test_every_job_that_runs_the_suite_checks_out_full_history() -> None:
    """`tests/test_plugin_manifest.py` compares against the merge base and, in CI,
    fails rather than skips when it cannot find one. A depth-1 checkout has no
    merge base, so a suite-running job without `fetch-depth: 0` turns that guard
    from a check into a build failure.

    Asserted here rather than left to whoever adds the next job, because relying
    on people to remember a checkout option is the same fragility that let the
    plugin version sit unbumped for twenty-three PRs. This caught the analysis
    job on the very commit that introduced the guard.
    """
    workflow = yaml.load(CI_WORKFLOW.read_text(), Loader=yaml.BaseLoader)

    offenders = []
    for name, job in workflow["jobs"].items():
        steps = job.get("steps") or []
        if not any("pytest" in str(step.get("run", "")) for step in steps):
            continue
        checkouts = [s for s in steps if str(s.get("uses", "")).startswith(
            "actions/checkout")]
        assert checkouts, f"{name} runs the suite without checking anything out"
        for step in checkouts:
            if str((step.get("with") or {}).get("fetch-depth")) != "0":
                offenders.append(name)

    assert not offenders, (
        f"these jobs run pytest without fetch-depth: 0 — the version guard will "
        f"fail there rather than run: {sorted(set(offenders))}"
    )
