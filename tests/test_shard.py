"""The `--shard I/N` split in tests/conftest.py: one slice per test, chosen the same
way everywhere, balanced, and narrowed — never moved — by `-k` or a path.

The workflow's side of the contract, that every slice is actually run, is
tests/test_ci_workflow.py's.
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

from tests import conftest

ROOT = Path(__file__).resolve().parents[1]


def test_a_test_nobody_has_timed_still_has_exactly_one_slice() -> None:
    """The cut is made from the record alone, so a test added since it was taken
    is placed by rule: with its module if the module is kept whole, by its own name
    if the module is split, and a new module all together, for its fixtures."""
    recorded = conftest._recorded()
    assert recorded, "tests/durations.json is missing or empty"
    for count in range(1, 7):
        cut = conftest.Cut(count, recorded)
        assert set(cut.tests) == set(recorded)
        assert all(cut(nodeid) == index for nodeid, index in cut.tests.items())
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


def test_the_cut_follows_neither_float_sums_nor_string_hashes() -> None:
    """3.12 made `sum()` of floats compensated, and summing recorded times as
    floats cut the suite differently on 3.10 and 3.13: each still ran every test,
    but a failing `--shard 1/4` named different tests on another interpreter.
    Integers add alike everywhere. Nor may the cut follow string hashing, which
    every process — so every machine — seeds differently: two seeds, every kind
    of placement, one answer."""
    recorded = conftest._recorded()
    assert all(type(cost) is int for cost in conftest._costs(recorded).values())

    script = ("import hashlib, json; from tests import conftest; "
              "cut = conftest.Cut(4, conftest._recorded()); "
              "extra = [cut(f'{m}::test_x') for m in sorted(cut.split)]; "
              "extra += [cut(f'tests/test_new_{n}.py::test_x') for n in range(20)]; "
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

    files = ["tests/test_paths.py", "tests/test_roundtrip.py"]
    name = "test_code_root_is_derived_from_file_not_environment"
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
