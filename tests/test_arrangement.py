"""The arrangement prior: its format reference's example is valid, and the checker
catches the mistakes that would mislead the side that reads it."""

from __future__ import annotations

import copy
import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import arrangement as A  # noqa: E402


def _example() -> dict:
    text = (ROOT / "reference" / "arrangement.md").read_text()
    return json.loads(re.search(r"```json\n(.*?)```", text, re.S).group(1))


def test_the_documented_example_is_valid():
    assert A.problems(_example()) == []


def _broken(edit) -> list:
    doc = copy.deepcopy(_example())
    edit(doc)
    return A.problems(doc)


@pytest.mark.parametrize("edit,expected", [
    (lambda d: d["guitars"][0].update(confidence="documented", sources=[]),
     "documented but cites no source"),
    (lambda d: d["guitars"][1].update(sources=["s1"]),
     "corroborated but cites fewer than two"),
    (lambda d: d["sections"][0].update(sources=["s9"]), "'s9', which is not in sources"),
    (lambda d: d["sections"][1]["guitars"].update(g7="chords"), "'g7', which is not in guitars"),
    (lambda d: d["sections"][2].update(name="intro"), "used twice"),
    (lambda d: d["sections"][2].update(order=1), "share an order"),
    (lambda d: d["sections"][0].update(start_s=10.0, end_s=5.0, time_basis="user"),
     "ends before it starts"),
    (lambda d: d["sections"][0].update(start_s=3.0, end_s=9.0), "time_basis is unknown"),
    (lambda d: d["changes"][0].update(at_section="bridge"), "'bridge' is not a section name"),
    (lambda d: d["changes"][0].update(at_section=None), "neither which section nor when"),
    (lambda d: d["guitars"][0].update(doubled="yes"), "doubled must be true, false or null"),
    (lambda d: d["guitars"][0].update(capo=30), "capo must be a fret number"),
    (lambda d: d["song"].pop("recording"), "song.recording"),
    (lambda d: d["sources"][0].update(kind="blog"), "kind must be one of"),
    (lambda d: d.update(schema="arrangement-0"), "schema is"),
])
def test_each_mistake_is_named(edit, expected):
    found = _broken(edit)
    assert any(expected in f for f in found), found


def test_the_slug_and_location_live_under_the_data_root(tmp_path):
    from packs import paths

    assert A.slug("Eagles", "Hotel California") == "eagles-hotel-california"
    assert A.slug("AC/DC", "T.N.T.") == "ac-dc-t-n-t"
    paths.set_data_root(str(tmp_path))
    try:
        assert A.location("Eagles", "Hotel California") == (
            tmp_path / "research" / "eagles-hotel-california" / "arrangement.json")
    finally:
        paths.set_data_root(None)


def test_check_fails_with_every_problem_listed(tmp_path):
    doc = _example()
    doc["guitars"][0]["sources"] = []
    doc["sections"][2]["order"] = 1
    path = tmp_path / "a.json"
    path.write_text(json.dumps(doc))
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "arrangement.py"),
                             "check", str(path)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "cites no source" in result.stderr and "share an order" in result.stderr
    assert "Traceback" not in result.stderr
