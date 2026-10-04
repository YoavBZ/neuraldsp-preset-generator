"""Splitting the suite across CI machines: `--shard I/N` and `--record-durations`.

The suite renders audio and runs the real optimiser, so it is CPU-bound: on a
four-core CI runner it was fourteen minutes even with xdist using every core.
xdist spreads the work over one machine's cores; this spreads it over machines. `--shard 2/4` runs the second
of four slices, and every slice is chosen from the same `durations.json`, so
the four together run each collected test exactly once.

A slice is balanced on recorded time, not on test count: a few dozen tests in
`test_match_cli.py` and `test_search.py` are most of the cost, and a count-based
split would hand one machine all of them. Slices are filled longest-first, each
unit going to whichever slice is lightest so far.

A module is a single unit unless it is too large to be one. Keeping a module
together means its module- and session-scoped fixtures are paid once per worker
on one machine rather than on every machine: `test_match_audition.py` builds its
match once per worker, and scattered over four machines that saving would be
gone. Modules too big to balance as one piece are split into their tests.

A test with no recorded time is costed at its module's mean, or the suite's,
so a new test is placed sensibly before anyone records it. Refresh the record
after the suite's shape changes — a stale one only costs balance, never
correctness:

    python -m pytest --record-durations
"""

from __future__ import annotations

import json
import pathlib

import pytest

DURATIONS = pathlib.Path(__file__).with_name("durations.json")

# A module larger than this fraction of one slice is split into its tests.
WHOLE_MODULE_LIMIT = 0.25


def pytest_addoption(parser):
    group = parser.getgroup("shard", "split the suite across machines")
    group.addoption(
        "--shard", metavar="I/N", default=None,
        help="run only slice I of N, balanced on tests/durations.json")
    group.addoption(
        "--record-durations", metavar="PATH", nargs="?", const=str(DURATIONS),
        default=None,
        help="merge this run's per-test times into PATH (tests/durations.json)")


def pytest_configure(config):
    spec = config.getoption("shard")
    if spec:
        _parse(spec)            # a usage error now, not after collection
    # Under xdist every report reaches the controller, so only it records.
    path = config.getoption("record_durations")
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


def _costs(items, recorded: dict) -> dict:
    by_module: dict = {}
    for nodeid, seconds in recorded.items():
        by_module.setdefault(_module(nodeid), []).append(seconds)
    overall = sum(recorded.values()) / len(recorded) if recorded else 1.0
    costs = {}
    for item in items:
        if item.nodeid in recorded:
            costs[item.nodeid] = recorded[item.nodeid]
        else:
            peers = by_module.get(_module(item.nodeid))
            costs[item.nodeid] = sum(peers) / len(peers) if peers else overall
    return costs


def slices(items, count: int, recorded: dict) -> list:
    """Partition `items` into `count` lists of roughly equal recorded time."""
    costs = _costs(items, recorded)
    modules: dict = {}
    for item in items:
        modules.setdefault(_module(item.nodeid), []).append(item)
    limit = WHOLE_MODULE_LIMIT * sum(costs.values()) / count

    units = []
    for name, members in modules.items():
        total = sum(costs[member.nodeid] for member in members)
        if total <= limit:
            units.append((total, name, members))
        else:
            units.extend((costs[member.nodeid], member.nodeid, [member])
                         for member in members)

    loads = [0.0] * count
    chosen: list = [set() for _ in range(count)]
    # Sorting on the name as well makes every xdist worker, and every machine,
    # compute the same partition from the same collection.
    for weight, _, members in sorted(units, key=lambda unit: (-unit[0], unit[1])):
        lightest = min(range(count), key=lambda index: (loads[index], index))
        loads[lightest] += weight
        chosen[lightest].update(member.nodeid for member in members)
    return [[item for item in items if item.nodeid in ids] for ids in chosen]


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    spec = config.getoption("shard")
    if not spec:
        return
    index, count = _parse(spec)
    keep = {item.nodeid for item in slices(items, count, _recorded())[index - 1]}
    config.hook.pytest_deselected(
        items=[item for item in items if item.nodeid not in keep])
    items[:] = [item for item in items if item.nodeid in keep]


class _Recorder:
    def __init__(self, path: pathlib.Path):
        self.path = path
        self.seconds: dict = {}

    def pytest_runtest_logreport(self, report):
        self.seconds[report.nodeid] = self.seconds.get(report.nodeid, 0.0) + report.duration

    def pytest_sessionfinish(self, session):
        if not self.seconds:
            return
        merged = _recorded(self.path)
        merged.update({nodeid: round(seconds, 2) for nodeid, seconds in self.seconds.items()})
        self.path.write_text(json.dumps(merged, indent=0, sort_keys=True) + "\n")
