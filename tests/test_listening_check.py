"""The listening check's pure parts (`docs/listening-check-plan.md`)."""

from __future__ import annotations

import collections
import pathlib
import random
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "research"))

import listening_check as L  # noqa: E402


def test_answers_are_read_per_sitting_with_cant_tell():
    got = L.parse_answers("sitting 1: 1A 2c 3?\nnotes\nSitting 2: 1D 10B")
    assert got == {(1, 1): "A", (1, 2): "C", (1, 3): None, (2, 1): "D", (2, 10): "B"}


def test_the_randomization_null_is_centred_and_sensitive():
    pytest.importorskip("numpy", reason="needs the analysis extra")
    rows = [{"c": v[0], "choices": v, "pick": "A"} for v in [[-0.3, 0.1, 0.1, 0.1]] * 12]
    assert L.randomization_p(rows, draws=20_000) < 0.01          # always the best
    worst = [{"c": 0.1, "choices": [-0.3, 0.1, 0.1, 0.1], "pick": "B"}] * 12
    assert L.randomization_p(worst, draws=20_000) > 0.9
    cant = [{"c": 0.0, "choices": [-0.3, 0.1, 0.1, 0.1], "pick": None}] * 12
    assert L.randomization_p(cant, draws=20_000) == 1.0           # 0 either way


def test_the_trial_plan_splits_riffs_across_sittings():
    parts = [f"p{i}" for i in range(16)]
    controls = [{"part": "c1"}, {"part": "c2"}]
    sittings = L.plan_trials(parts, controls, {"part": "x"}, random.Random(3))
    kinds = {s: collections.Counter(t["kind"] for t in ts) for s, ts in sittings.items()}
    assert kinds[1] == {"main": 16, "repeat": 1, "control": 1, "practice": 1}
    assert kinds[2] == {"main": 16, "repeat": 2, "control": 1}
    assert sittings[1][0]["kind"] == "practice"
    mains = [(t["part"], t["riff"]) for s in (1, 2) for t in sittings[s] if t["kind"] == "main"]
    assert len(set(mains)) == 32                  # every part through both riffs, once
    for s, ts in sittings.items():
        for i, t in enumerate(ts):
            if t["kind"] == "repeat" and s == 1:
                first = [j for j, u in enumerate(ts) if u["kind"] == "main"
                         and (u["part"], u["riff"]) == (t["part"], t["riff"])]
                assert first and first[0] < i


def test_the_listeners_folder_may_not_name_an_amp_or_a_candidate(tmp_path):
    (tmp_path / "trial-01-A.wav").write_bytes(b"x")
    (tmp_path / "index.html").write_text("<p>Trial 1</p>")
    assert L.leak_check(tmp_path) == []
    (tmp_path / "index.html").write_text("<p>Trial 1: PR12 at the edge</p>")
    assert L.leak_check(tmp_path)
    page = L.page(1, [{"number": 1, "cue": "Bloomlight: the guitar track GTR.",
                       "song": "trial-01-song.wav",
                       "clips": {x: f"trial-01-{x}.wav" for x in "ABCD"}}])
    (tmp_path / "index.html").write_text(page)
    assert L.leak_check(tmp_path) == []
