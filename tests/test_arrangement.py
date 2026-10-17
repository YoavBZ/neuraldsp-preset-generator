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
    (lambda d: d["sections"][0].update(end_s=9.0), "time_basis is unknown"),
    (lambda d: d["sections"][0].update(time_basis="estimated from song structure"),
     "time_basis must be one of"),
    (lambda d: d["changes"][0].update(at_s=-1.0, time_basis="user"), "non-negative"),
    (lambda d: d["sections"][0].update(start_s=float("nan"), end_s=5.0, time_basis="user"),
     "start_s must be a non-negative number"),
    (lambda d: d["guitars"][0].pop("doubled"), "lacks doubled"),
    (lambda d: d.pop("changes"), "lacks changes"),
    (lambda d: d["guitars"][0].update(doubled=1), "doubled must be true, false or null"),
    (lambda d: d["sections"][1]["guitars"].update(g1=5), "must say what it plays"),
    (lambda d: d["sections"][2].update(name="Intro"), "used twice"),
    (lambda d: d["sources"][0].update(url="https://"), "web address"),
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


@pytest.mark.parametrize("edit", [
    lambda d: d.update(changes=None),
    lambda d: d.update(changes=5),
    lambda d: d.update(changes="abc", sections={}, sources="x", guitars=None),
    lambda d: d["changes"][0].update(guitar=["g1"], at_section=["solo"]),
    lambda d: d["guitars"][0].update(sources=[["s1"]], rig=None),
    lambda d: d["sections"].append("chorus 2"),
])
def test_malformed_input_is_reported_not_crashed_on(edit):
    assert _broken(edit)


def test_names_without_latin_letters_never_share_a_file():
    a = A.slug("椎名林檎", "丸の内サディスティック")
    b = A.slug("Мумий Тролль", "Утекай")
    assert a.startswith("song-") and b.startswith("song-") and a != b
    assert A.slug("Sigur Rós", "Hoppípolla") == "sigur-ros-hoppipolla"
    assert A.slug("Beyoncé", "Halo") == A.slug("Beyonce", "Halo")
