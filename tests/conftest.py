"""Splitting the suite across CI machines: `--shard I/N` and `--record-durations`.

The suite renders audio and runs the real optimiser, so it is CPU-bound: on a
four-core CI runner it was fourteen minutes even with xdist using every core.
xdist spreads the work over one machine's cores; this spreads it over machines.
`--shard 2/4` runs the second of four slices, and every slice is chosen from
the same `durations.json`, so the four together run each collected test once.

A slice is balanced on recorded time, not on test count: a few dozen tests in
`test_match_cli.py` and `test_search.py` are most of the cost, and a count-based
split would hand one machine all of them. Slices are filled longest-first, each
unit going to whichever slice is lightest so far.

A module is a single unit unless it is too large to be one. Keeping a module
together means its module- and session-scoped fixtures are paid once per worker
on one machine rather than on every machine: `test_match_audition.py` builds its
match once per worker, and scattered over four machines that saving would be
gone. Modules too big to balance as one piece are split into their tests.

The cut is made over every recorded test as well as every collected one, and
before `-k`, `-m`, `--deselect` or `--lf` narrow the run. So `--shard 3/4 -k
name`, or `--shard 3/4 tests/test_search.py`, runs the part of CI's slice 3 that
matches — which is what rerunning a failing slice needs. Only tests with no
recorded time can move between slices when the collection changes.

A test with no recorded time is costed at its module's mean, or the suite's,
so a new test is placed sensibly before anyone records it. A stale record costs
balance, never correctness. To refresh it from the CI runners themselves, run
the CI workflow by hand with `record_durations` ticked, download one Python
version's four `durations-*` artifacts, and take their union:

    jq -s add durations-3.13-*/durations.json > tests/durations.json

`python -m pytest --record-durations tests/durations.json` does the same from
one local run, if the machine is otherwise idle.
"""

from __future__ import annotations

import json
import pathlib

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


def _costs(nodeids, recorded: dict) -> dict:
    """Each test's recorded time in whole centiseconds.

    Integers, not the floats they came from: Python 3.12 made `sum()` of floats
    compensated, so 3.10 and 3.13 added the same times to different last bits,
    broke near-ties between slices differently, and cut the suite differently.
    Each version still ran every test, but `--shard 1/4` named different tests
    on each, so a failing slice could not be rerun on another interpreter.
    """
    centis = {nodeid: round(seconds * 100) for nodeid, seconds in recorded.items()}
    by_module: dict = {}
    for nodeid, cost in centis.items():
        by_module.setdefault(_module(nodeid), []).append(cost)
    overall = sum(centis.values()) // len(centis) if centis else 100
    costs = {}
    for nodeid in nodeids:
        if nodeid in centis:
            costs[nodeid] = centis[nodeid]
        else:
            peers = by_module.get(_module(nodeid))
            costs[nodeid] = sum(peers) // len(peers) if peers else overall
    return costs


def slices(nodeids, count: int, recorded: dict) -> list:
    """Partition `nodeids` into `count` sets of roughly equal recorded time."""
    costs = _costs(set(nodeids), recorded)
    modules: dict = {}
    for nodeid in costs:
        modules.setdefault(_module(nodeid), []).append(nodeid)
    whole = sum(costs.values())

    units = []
    for name, members in modules.items():
        total = sum(costs[member] for member in members)
        if total * WHOLE_MODULE_PARTS * count <= whole:
            units.append((total, name, members))
        else:
            units.extend((costs[member], member, [member]) for member in members)

    loads = [0] * count
    chosen: list = [set() for _ in range(count)]
    # Names are unique, so this order — and with it the partition — is the same
    # on every xdist worker, every machine and every interpreter.
    for weight, _, members in sorted(units, key=lambda unit: (-unit[0], unit[1])):
        lightest = min(range(count), key=lambda index: (loads[index], index))
        loads[lightest] += weight
        chosen[lightest].update(members)
    return chosen


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    spec = config.getoption("shard")
    if not spec:
        return
    index, count = _parse(spec)
    recorded = _recorded()
    universe = set(recorded) | {item.nodeid for item in items}
    keep = slices(universe, count, recorded)[index - 1]
    config.hook.pytest_deselected(
        items=[item for item in items if item.nodeid not in keep])
    items[:] = [item for item in items if item.nodeid in keep]


class _Recorder:
    def __init__(self, path: pathlib.Path):
        self.path = path
        self.seconds: dict = {}

    def pytest_runtest_logreport(self, report):
        seconds = self.seconds.get(report.nodeid, 0.0)
        self.seconds[report.nodeid] = seconds + report.duration

    def pytest_sessionfinish(self, session):
        if self.seconds:
            recorded = {nodeid: round(seconds, 2) for nodeid, seconds in self.seconds.items()}
            self.path.write_text(json.dumps(recorded, indent=0, sort_keys=True) + "\n")
