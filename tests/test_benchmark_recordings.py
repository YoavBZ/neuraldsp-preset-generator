"""The recordings benchmark picks development parts only and pairs 'other' across songs."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import benchmark_recordings as R  # noqa: E402

CATALOG = {"sessions": [
    {"source": "a", "song": "one", "split": "development",
     "parts": [{"part": "g1", "usable": True}, {"part": "g2", "usable": True},
               {"part": "g3", "usable": False}]},
    {"source": "a", "song": "two", "split": "held_out",
     "parts": [{"part": "g1", "usable": True}]},
    {"source": "b", "song": "three", "split": "development",
     "parts": [{"part": "x", "usable": True}]},
]}


def test_only_usable_development_parts_are_targets():
    assert R.development_parts(CATALOG) == [("a", "one", "g1"), ("a", "one", "g2"),
                                            ("b", "three", "x")]


def test_another_songs_di_comes_from_a_different_session():
    parts = R.development_parts(CATALOG)
    assert [R.other_di_index(parts, i) for i in range(3)] == [2, 2, 0]
    assert R.other_di_index([("a", "one", "g1"), ("a", "one", "g2")], 0) is None
