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
    `[1, 2, 3]` beside a `/4` would leave a quarter of the suite unrun on every
    build, and nothing would fail: each shard that did run would pass."""
    import re

    workflow = yaml.load(CI_WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["analysis"]
    shards = [int(shard) for shard in job["strategy"]["matrix"]["shard"]]
    commands = [step["run"] for step in job["steps"] if "--shard" in step.get("run", "")]
    assert len(commands) == 1, commands
    split = re.search(r"--shard \$\{\{ matrix\.shard \}\}/(\d+)", commands[0])
    assert split, commands[0]
    count = int(split.group(1))
    assert shards == list(range(1, count + 1))
    assert f"{{{{ matrix.shard }}}}/{count})" in job["name"]


class _Item:
    def __init__(self, nodeid: str) -> None:
        self.nodeid = nodeid


def test_the_slices_cover_every_test_exactly_once() -> None:
    """Including tests the recorded times have never seen, which is every test
    written since they were last recorded."""
    from tests import conftest

    recorded = conftest._recorded()
    assert recorded, "tests/durations.json is missing or empty"
    items = [_Item(nodeid) for nodeid in sorted(recorded)]
    items += [_Item("tests/test_new.py::test_unrecorded"),
              _Item(f"{items[0].nodeid.split('::')[0]}::test_unrecorded_in_a_known_module")]
    for count in range(1, 7):
        parts = conftest.slices(items, count, recorded)
        assert len(parts) == count
        ran = [item.nodeid for part in parts for item in part]
        assert sorted(ran) == sorted(item.nodeid for item in items), count
