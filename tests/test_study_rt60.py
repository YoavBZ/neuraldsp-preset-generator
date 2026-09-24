"""The RT60 study asks both of its questions and writes what it saw."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

from tests import fixtures_audio as fx

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _cli(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "study_rt60.py"), *map(str, args)],
        cwd=ROOT, capture_output=True, text=True)


def test_the_study_records_where_the_term_fires_and_what_each_reverb_reads(tmp_path):
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    fx.write_wav(a, fx.plucks(seconds=1.5, gap=0.6, seed=3) * 0.3)
    fx.write_wav(b, fx.plucks(seconds=1.5, gap=0.4, seed=9) * 0.3)
    out = tmp_path / "rt60.json"
    done = _cli("--amp", "sw50r", "--template",
                ROOT / "samples" / "SW50R_Atlas_Topology.xml",
                "--di", f"a={a}", "--di", f"b={b}", "--targets", "1", "--json", out)
    assert done.returncode == 0, done.stderr

    written = json.loads(out.read_text())
    assert written["schema"] == "rt60-study-1"
    assert len(written["fires"]) == 1
    assert len(written["fires"][0]["term_target_vs_neutral"]) == 2
    assert "term_target_vs_itself" in written["fires"][0]
    assert set(written["dis"]) == {"a", "b"} and written["dis"]["a"]["sha256"]
    assert written["tracks_backend"] and written["elapsed_s"] >= 0
    rack = next(row for row in written["tracks"] if row["case"].startswith("rack"))
    assert rack["settings"]["reverb/reverbActive"] is True
    cases = [row["case"] for row in written["tracks"]]
    assert cases[0] == "dry" and any(case.startswith("rack decay") for case in cases)
    assert all({"a", "b"} <= set(row) for row in written["tracks"])


def test_the_study_refuses_a_signal_path_without_reverb_steps(tmp_path):
    a = tmp_path / "a.wav"
    fx.write_wav(a, fx.plucks(seconds=1.0, gap=0.6, seed=3) * 0.3)
    done = _cli("--amp", "pr12", "--di", f"a={a}", "--targets", "1")
    assert done.returncode != 0
    assert "reverb steps are defined for" in done.stderr


def test_the_study_refuses_a_passage_named_twice(tmp_path):
    a = tmp_path / "a.wav"
    fx.write_wav(a, fx.plucks(seconds=1.0, gap=0.6, seed=3) * 0.3)
    done = _cli("--amp", "sw50r", "--di", f"a={a}", "--di", f"a={a}", "--targets", "1")
    assert done.returncode != 0
    assert "given twice" in done.stderr
