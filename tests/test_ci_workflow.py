"""Regression tests for the GitHub Actions trigger contract."""

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_pull_request_commits_do_not_start_duplicate_ci_runs() -> None:
    workflow = yaml.load(CI_WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    triggers = workflow["on"]

    assert "pull_request" in triggers
    assert triggers["push"]["branches"] == ["main"]


# Jobs that deliberately run on a shallow checkout, each with the reason it is
# safe. A job is listed here only because it does not run the suite; if one ever
# does, it needs full history instead of an entry.
SHALLOW_BY_DESIGN = {
    "fresh-clone": "installs and exercises the CLI, never invokes pytest",
    "plugin-validate": "runs `claude plugin validate`, never invokes pytest",
}


def test_every_job_checks_out_full_history_unless_it_says_why_not() -> None:
    """`tests/test_plugin_manifest.py` compares against the merge base and, on
    GitHub Actions, fails rather than skips when it cannot find one. A depth-1
    checkout has no merge base, so a suite-running job without `fetch-depth: 0`
    turns that guard from a check into a build failure.

    Written to fail **closed**. An earlier version asked "does any step's `run:`
    contain pytest", which is not how Actions resolves a workflow: a job running
    `make test`, a composite action, or a job-level `uses:` reusable workflow all
    run the suite while matching nothing, so the check passed and the build would
    still have broken. Requiring every checkout to be full-history unless its job
    is named here means adding a job forces a decision instead of inheriting a
    silent default — which is the failure this whole area keeps repeating.
    """
    offenders, unreviewable = [], []
    for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        for name, job in (workflow.get("jobs") or {}).items():
            if name in SHALLOW_BY_DESIGN:
                continue
            if job.get("uses"):
                # A reusable workflow has no steps here; its checkout is in
                # another file this assertion cannot see.
                unreviewable.append(f"{path.name}:{name}")
                continue
            for step in job.get("steps") or []:
                if not str(step.get("uses", "")).startswith("actions/checkout"):
                    continue
                if str((step.get("with") or {}).get("fetch-depth")) != "0":
                    offenders.append(f"{path.name}:{name}")

    assert not offenders, (
        f"these jobs check out shallow history — the version guard fails rather "
        f"than runs there. Add `fetch-depth: 0`, or add the job to "
        f"SHALLOW_BY_DESIGN with the reason it never runs the suite: "
        f"{sorted(set(offenders))}"
    )
    assert not unreviewable, (
        f"these jobs call a reusable workflow, whose checkout this cannot see. "
        f"Confirm it uses full history and add the job to SHALLOW_BY_DESIGN, or "
        f"inline it: {sorted(set(unreviewable))}"
    )


def test_the_analysis_shards_are_every_slice_of_the_split_they_run() -> None:
    """`--shard I/N` runs one slice and trusts the job for the rest. A matrix of
    `[1, 2, 3]` beside a `/4`, an `exclude:` dropping one version's shard, an `if:`
    or `continue-on-error` on the step, or a `-k` added to the command or slipped
    in through `PYTEST_ADDOPTS` — set in an `env:`, written to `$GITHUB_ENV` by an
    earlier step, or exported by a `defaults:` shell — would each leave part of the
    suite unrun or unheeded on every build, and nothing would fail, because every
    shard that did run would pass. The sharding itself is tests/test_shard.py's."""
    workflow = yaml.load(CI_WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["analysis"]
    [test] = [step for step in job["steps"] if step.get("name") == "Test"]
    for scope in (workflow, job, test):
        env = scope.get("env") or {}
        assert isinstance(env, dict), f"an `env:` this test cannot read: {env!r}"
        assert "PYTEST_ADDOPTS" not in env, "PYTEST_ADDOPTS can narrow every shard"
        assert "defaults" not in scope, "a `defaults:` shell can wrap the Test step"
    for step in job["steps"]:
        for name in ("PYTEST_ADDOPTS", "GITHUB_ENV"):
            assert name not in step.get("run", ""), f"{step.get('name')!r} touches {name}"
    matrix = job["strategy"]["matrix"]
    assert set(matrix) == {"python-version", "shard"}, (
        "an include or exclude changes which (version, shard) pairs run; if one "
        "is needed, extend this test to check every version still runs every slice")
    assert "if" not in job and "continue-on-error" not in job
    assert "if" not in test and "continue-on-error" not in test
    split = re.fullmatch(
        r"python -m pytest -q --shard \$\{\{ matrix\.shard \}\}/(\d+)"
        r"( \$\{\{ inputs\.record_durations && '--record-durations=\S+' \|\| '' \}\})?",
        test["run"].strip())
    assert split, test["run"]
    count = int(split.group(1))
    shards = [int(shard) for shard in matrix["shard"]]
    assert shards == list(range(1, count + 1))
    assert f"{{{{ matrix.shard }}}}/{count})" in job["name"]

    # The smoke steps run on one shard; a condition naming no shard runs them never.
    for step in job["steps"]:
        condition = step.get("if", "")
        if "matrix.shard" in condition:
            only = re.fullmatch(r"matrix\.shard == (\d+)", condition.strip())
            assert only and int(only.group(1)) in shards, (step.get("name"), condition)
