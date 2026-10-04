"""Regression tests for the GitHub Actions trigger contract."""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

from tests import conftest


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
    in through `PYTEST_ADDOPTS` would each leave part of the suite unrun or
    unheeded on every build — and nothing would fail, because every shard that
    did run would pass."""
    workflow = yaml.load(CI_WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["analysis"]
    [test] = [step for step in job["steps"] if step.get("name") == "Test"]
    for scope in (workflow, job, test):
        env = scope.get("env") or {}
        assert isinstance(env, dict), f"an `env:` this test cannot read: {env!r}"
        assert "PYTEST_ADDOPTS" not in env, "PYTEST_ADDOPTS can narrow every shard"
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
    assert [int(shard) for shard in matrix["shard"]] == list(range(1, count + 1))
    assert f"{{{{ matrix.shard }}}}/{count})" in job["name"]


def test_a_test_nobody_has_timed_still_has_exactly_one_slice() -> None:
    """The cut is made from the record alone, so a test added since it was taken
    is placed by rule: with its module if the module is kept whole, by its own name
    if the module is split, and a new module all together, for its fixtures."""
    recorded = conftest._recorded()
    assert recorded, "tests/durations.json is missing or empty"
    for count in range(1, 7):
        cut = conftest.Cut(count, recorded)
        assert set(cut.tests) == set(recorded)
        for module, index in cut.modules.items():
            assert cut(f"{module}::test_added_since") == index
        new = {cut(f"tests/test_new.py::test_{n}") for n in range(20)}
        assert len(new) == 1 and 0 <= new.pop() < count
        for module in cut.split:
            spread = {cut(f"{module}::test_added_{n}") for n in range(40)}
            assert spread <= set(range(count)) and (count == 1 or len(spread) > 1)


def test_the_slices_are_balanced_on_the_recorded_times() -> None:
    """Greedy filling guarantees no two slices differ by more than the largest
    unit placed; anything worse is a bug in the filling, not in the data."""
    recorded = conftest._recorded()
    costs = conftest._costs(recorded)
    for count in range(1, 7):
        cut = conftest.Cut(count, recorded)
        modules: dict = {}
        for nodeid, cost in costs.items():
            modules.setdefault(conftest._module(nodeid), []).append(cost)
        units = [cost for module in cut.split for cost in modules[module]]
        units += [sum(modules[module]) for module in cut.modules]
        assert set(cut.modules) | cut.split == set(modules)
        assert sum(cut.loads) == sum(costs.values())
        assert max(cut.loads) - min(cut.loads) <= max(units), (count, cut.loads)


def test_the_slices_are_the_same_on_every_python() -> None:
    """3.12 made `sum()` of floats compensated, and summing recorded times as
    floats cut the suite differently on 3.10 and 3.13: each still ran every test,
    but a failing `--shard 1/4` named different tests on another interpreter.
    Integers add alike everywhere. And the cut must not follow string hashing,
    which every process — every machine — seeds differently."""
    recorded = conftest._recorded()
    assert all(type(cost) is int for cost in conftest._costs(recorded).values())

    script = ("import hashlib, json; from tests import conftest; "
              "cut = conftest.Cut(4, conftest._recorded()); "
              "extra = [cut(f'{m}::test_x') for m in sorted(cut.split)]; "
              "print(hashlib.sha256(json.dumps([sorted(cut.tests.items()), extra])"
              ".encode()).hexdigest())")
    digests = {subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "PYTHONHASHSEED": seed}, check=True).stdout
        for seed in ("1", "2")}
    assert len(digests) == 1, digests


def test_narrowing_a_run_keeps_each_test_in_its_slice() -> None:
    """Through pytest itself, not only `Cut`: `--shard I/N` runs the collected tests
    the cut gives slice I, and `-k` or a path narrows within it — so a failing slice
    can be rerun as `--shard I/N -k name`. And every slice names the same whole
    collection, which is what lets the shards of one run be compared."""
    # Neither may leak in from the run around this one: one would narrow these
    # runs, the other would put their lines on a CI run's summary page.
    env = {key: value for key, value in os.environ.items()
           if key not in ("PYTEST_ADDOPTS", "GITHUB_STEP_SUMMARY")}

    def pytest(*args) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args],
            cwd=ROOT, capture_output=True, text=True, env=env)

    def collect(*args) -> tuple:
        done = pytest("--collect-only", "-n0", *args)
        assert done.returncode in (0, 5), done.stdout + done.stderr  # 5: none here
        return {line for line in done.stdout.splitlines() if "::" in line}, done.stdout

    files = ["tests/test_ci_workflow.py", "tests/test_paths.py"]
    name = "test_the_analysis_shards_are_every_slice_of_the_split_they_run"
    everything, _ = collect(*files)
    digest = hashlib.sha256("\n".join(sorted(everything)).encode()).hexdigest()[:16]
    whole = f"of the {len(everything)} tests collected (collection sha256 {digest})"
    cut = conftest.Cut(4, conftest._recorded())
    assert any(nodeid.endswith(f"::{name}") for nodeid in everything)
    for index in range(1, 5):
        mine = {nodeid for nodeid in everything if cut(nodeid) == index - 1}
        named = {nodeid for nodeid in mine if nodeid.endswith(f"::{name}")}
        for narrowing, expected in (((), mine), (("-k", name), named)):
            ran, output = collect("--shard", f"{index}/4", *narrowing, *files)
            assert ran == expected
            assert f"--shard {index}/4: running {len(expected)} {whole}" in output

    # Once through xdist as CI runs it, where the line comes back from a worker.
    index = cut(next(nodeid for nodeid in everything if nodeid.endswith(f"::{name}"))) + 1
    done = pytest("-n", "2", "--shard", f"{index}/4", "-k", name, *files)
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"--shard {index}/4: running 1 {whole}" in done.stdout, done.stdout
