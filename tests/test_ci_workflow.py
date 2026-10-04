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
    """`--shard I/N` runs one slice and trusts the matrix for the rest. A matrix of
    `[1, 2, 3]` beside a `/4`, or an `exclude:` that drops one version's shard,
    would leave part of the suite unrun on every build, and nothing would fail:
    each shard that did run would pass."""
    import re

    workflow = yaml.load(CI_WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["analysis"]
    matrix = job["strategy"]["matrix"]
    assert set(matrix) == {"python-version", "shard"}, (
        "an include or exclude changes which (version, shard) pairs run; if one "
        "is needed, extend this test to check every version still runs every slice")
    shards = [int(shard) for shard in matrix["shard"]]
    commands = [step["run"] for step in job["steps"] if "--shard" in step.get("run", "")]
    assert len(commands) == 1, commands
    split = re.search(r"--shard \$\{\{ matrix\.shard \}\}/(\d+)", commands[0])
    assert split, commands[0]
    count = int(split.group(1))
    assert shards == list(range(1, count + 1))
    assert f"{{{{ matrix.shard }}}}/{count})" in job["name"]


def test_the_slices_cover_every_test_exactly_once() -> None:
    """Including tests the recorded times have never seen, which is every test
    written since they were last recorded."""
    from tests import conftest

    recorded = conftest._recorded()
    assert recorded, "tests/durations.json is missing or empty"
    known = sorted(recorded)
    nodeids = known + ["tests/test_new.py::test_unrecorded",
                       f"{conftest._module(known[0])}::test_unrecorded_in_a_known_module"]
    for count in range(1, 7):
        parts = conftest.slices(nodeids, count, recorded)
        assert len(parts) == count
        assert sum(len(part) for part in parts) == len(nodeids), count
        assert set().union(*parts) == set(nodeids), count


def test_the_slices_are_the_same_on_every_python(monkeypatch) -> None:
    """3.12 made `sum()` of floats compensated, and summing recorded times as
    floats cut the suite differently on 3.10 and 3.13: each still ran every test,
    but a failing `--shard 1/4` named different tests on another interpreter.

    The costs are integers, which every interpreter adds alike. Shadowing `sum`
    with the old left-to-right addition checks the same thing from the other end,
    though only where the built-in differs from it — 3.12 and later."""
    import functools
    import operator

    from tests import conftest

    recorded = conftest._recorded()
    costs = conftest._costs([*recorded, "tests/test_new.py::test_unrecorded"], recorded)
    assert all(type(cost) is int for cost in costs.values())

    compensated = conftest.slices(recorded, 4, recorded)
    monkeypatch.setattr(conftest, "sum", lambda values, start=0: functools.reduce(
        operator.add, values, start), raising=False)
    assert conftest.slices(recorded, 4, recorded) == compensated


def test_a_slice_is_cut_before_the_run_is_narrowed() -> None:
    """Through pytest itself, not only `slices()`: the slices of a collection add up
    to it, and narrowing with `-k` or a path keeps each test in the slice the full
    run put it in — so a failing slice can be rerun as `--shard I/N -k name`."""
    import subprocess
    import sys

    def collect(*args) -> set:
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-n0",
             "-p", "no:cacheprovider", *args],
            cwd=ROOT, capture_output=True, text=True)
        assert done.returncode in (0, 5), done.stdout + done.stderr  # 5: none here
        return {line for line in done.stdout.splitlines() if "::" in line}

    from tests import conftest

    files = ["tests/test_ci_workflow.py", "tests/test_paths.py"]
    whole = collect(*files)
    assert whole
    recorded = conftest._recorded()
    cut = conftest.slices(set(recorded) | whole, 2, recorded)
    parts = [collect("--shard", f"{index}/2", *files) for index in (1, 2)]
    assert parts == [whole & cut[0], whole & cut[1]]

    name = "test_the_slices_cover_every_test_exactly_once"
    for index, part in zip((1, 2), parts):
        expected = {nodeid for nodeid in part if nodeid.endswith(f"::{name}")}
        assert collect("--shard", f"{index}/2", "-k", name, *files) == expected
        expected = {nodeid for nodeid in part if nodeid.startswith(files[1])}
        assert collect("--shard", f"{index}/2", files[1]) == expected
