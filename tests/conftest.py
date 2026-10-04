"""Splitting the suite across CI machines: `--shard I/N` and `--record-durations`.

The suite renders audio and runs the real optimiser, so it is CPU-bound: on a
four-core CI runner it was fourteen minutes even with xdist using every core.
xdist spreads the work over one machine's cores; this spreads it over machines.
`--shard 2/4` runs the second of four slices; the four together run each test
once.

Which slice a test belongs to is decided by its node id and `durations.json`
alone — never by what else was collected. Every machine therefore agrees on
every test it collects, and narrowing a run cannot move one: `--shard 3/4 -k
name`, `--shard 3/4 tests/test_search.py` or `--shard 3/4 --lf` runs exactly
the matching part of CI's slice 3. An earlier version cut the collected tests
instead, and one unrecorded test — even a docs change adding a parametrization —
moved a third of the suite to other slices.

Recorded tests are balanced on their times, not their count: a few dozen tests
in `test_match_cli.py` and `test_search.py` are most of the cost, and a
count-based split would hand one machine all of them. Slices are filled
longest-first, each unit going to whichever slice is lightest so far.

A module is a single unit unless it is too large to be one. Keeping a module
together means its module- and session-scoped fixtures are paid once per worker
on one machine rather than on every machine: `test_match_audition.py` builds its
match once per worker, and scattered over four machines that saving would be
gone. Modules too big to balance as one piece are split into their tests.

A test with no recorded time joins its module's slice if the module was kept
whole, and otherwise goes by a hash of its name; a new module goes by a hash of
the module's, so it stays together. The record only decides balance, never
whether a test runs. To refresh it from the CI runners themselves, start the CI
workflow by hand with `record_durations` ticked, download one Python version's
four `durations-*` artifacts, and take their union:

    python - durations-3.13-*/durations.json > tests/durations.json <<'EOF'
    import json, sys
    union = {}
    for path in sys.argv[1:]:
        union.update(json.load(open(path)))
    print(json.dumps(union, indent=0, sort_keys=True))
    EOF

`python -m pytest --record-durations tests/durations.json` does the same from
one whole local run, if the machine is otherwise idle.
"""

from __future__ import annotations

import json
import pathlib
import zlib

import pytest

DURATIONS = pathlib.Path(__file__).with_name("durations.json")

# A module costing more than 1/WHOLE_MODULE_PARTS of one slice is split into
# its tests.
WHOLE_MODULE_PARTS = 4


def pytest_addoption(parser):
    group = parser.getgroup("shard", "split the suite across machines")
    group.addoption(
        "--shard", metavar="I/N", default=None,
        help="run only slice I of N, balanced on tests/durations.json")
    group.addoption(
        "--record-durations", metavar="PATH.json", default=None,
        help="write this run's per-test times to PATH.json")


def pytest_configure(config):
    spec = config.getoption("shard")
    if spec:
        _parse(spec)            # a usage error now, not after collection
    path = config.getoption("record_durations")
    if path and not path.endswith(".json"):
        # It takes a value, so `--record-durations tests/test_x.py` would
        # otherwise run the whole suite and then overwrite that test file.
        raise pytest.UsageError(
            f"--record-durations takes the .json file to write, not {path!r}")
    # Under xdist every report reaches the controller, so only it records.
    if path and not hasattr(config, "workerinput"):
        config.pluginmanager.register(_Recorder(pathlib.Path(path)), "record-durations")


def _parse(spec: str) -> tuple[int, int]:
    try:
        index, count = (int(part) for part in spec.split("/"))
    except ValueError:
        raise pytest.UsageError(f"--shard takes I/N, such as 2/4, not {spec!r}")
    if not 1 <= index <= count:
        raise pytest.UsageError(f"--shard {spec}: I must be between 1 and N")
    return index, count


def _recorded(path: pathlib.Path = DURATIONS) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}


def _module(nodeid: str) -> str:
    return nodeid.split("::", 1)[0]


def _costs(recorded: dict) -> dict:
    """Each recorded time in whole centiseconds.

    Integers, not the floats they came from: Python 3.12 made `sum()` of floats
    compensated, so 3.10 and 3.13 added the same times to different last bits,
    broke near-ties between slices differently, and cut the suite differently.
    """
    return {nodeid: round(seconds * 100) for nodeid, seconds in recorded.items()}


class Cut:
    """Which of `count` slices each test belongs to: `cut(nodeid)`, counted from 0.

    Built from `recorded` alone, so it is the same wherever the same
    `durations.json` is checked out, whatever was collected there."""

    def __init__(self, count: int, recorded: dict):
        self.count = count
        costs = _costs(recorded)
        modules: dict = {}
        for nodeid in sorted(costs):
            modules.setdefault(_module(nodeid), []).append(nodeid)
        whole = sum(costs.values())

        units = []
        self.split: set = set()
        for name, members in modules.items():
            total = sum(costs[member] for member in members)
            if total * WHOLE_MODULE_PARTS * count <= whole:
                units.append((total, name, members, name))
            else:
                self.split.add(name)
                units.extend((costs[member], member, [member], None) for member in members)

        self.loads = [0] * count
        self.tests: dict = {}
        self.modules: dict = {}
        # Names are unique, so this order — and the cut — does not depend on
        # how the units were gathered.
        units.sort(key=lambda unit: (-unit[0], unit[1]))
        for weight, _, members, module in units:
            lightest = min(range(count), key=lambda index: (self.loads[index], index))
            self.loads[lightest] += weight
            self.tests.update(dict.fromkeys(members, lightest))
            if module is not None:
                self.modules[module] = lightest

    def __call__(self, nodeid: str) -> int:
        if nodeid in self.tests:
            return self.tests[nodeid]
        module = _module(nodeid)
        if module in self.modules:
            return self.modules[module]
        key = nodeid if module in self.split else module
        return zlib.crc32(key.encode()) % self.count


def pytest_collection_modifyitems(config, items):
    spec = config.getoption("shard")
    if not spec:
        return
    index, count = _parse(spec)
    cut = Cut(count, _recorded())
    mine = {item.nodeid: cut(item.nodeid) == index - 1 for item in items}
    config.hook.pytest_deselected(
        items=[item for item in items if not mine[item.nodeid]])
    items[:] = [item for item in items if mine[item.nodeid]]


class _Recorder:
    def __init__(self, path: pathlib.Path):
        self.path = path
        self.seconds: dict = {}

    def pytest_runtest_logreport(self, report):
        seconds = self.seconds.get(report.nodeid, 0.0)
        self.seconds[report.nodeid] = seconds + report.duration

    def pytest_sessionfinish(self, session, exitstatus):
        # A run stopped partway records only what it reached; keep the old file.
        if exitstatus == pytest.ExitCode.INTERRUPTED or not self.seconds:
            return
        recorded = {nodeid: round(self.seconds[nodeid], 2) for nodeid in self.seconds}
        self.path.write_text(json.dumps(recorded, indent=0, sort_keys=True) + "\n")
