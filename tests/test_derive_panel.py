"""The clean panel keeps only the presets stage 0b validated the judge on, and its
lag table gives the judge each part's recorded lag, or none where it is ambiguous."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "research"))

import derive_panel as D  # noqa: E402


def test_high_gain_presets_are_dropped_and_the_templates_kept():
    index = {"amp": "pr12", "rows": [
        {"part": p, "candidate": c, "file": f"{p}-{c}.wav"}
        for p in ("p1", "p2") for c in ("factory:A/Clean", "factory:A/Metal",
                                        "template", "template+R")]}
    index["rows"].append({"canary": "p1", "candidate": "factory:A/Clean", "rms_drift_db": 0.0})
    rows, presets = D.kept_rows(index, {"pr12:factory:A/Metal"}.__contains__)
    assert presets == ["factory:A/Clean"]
    assert sorted({r["candidate"] for r in rows}) == ["factory:A/Clean", "template",
                                                       "template+R"]
    assert len(rows) == 7                                   # the canary row is kept
    assert {r["part"] for r in rows if "part" in r} == {"p1", "p2"}


def test_the_judge_gets_recorded_lags_less_the_latency_and_none_when_ambiguous():
    doc = {"parts": {"p1": {"lag_samples": 1000, "ambiguous": False},
                     "p2": {"lag_samples": 50, "ambiguous": True}}}
    table = D.judge_lags(doc, {"p1", "p2", "p3"})
    assert table["p1"]["lag"] == 1000 - 52
    assert table["p2"]["lag"] is None and "ambiguous" in table["p2"]["reason"]
    assert table["p3"]["lag"] is None

