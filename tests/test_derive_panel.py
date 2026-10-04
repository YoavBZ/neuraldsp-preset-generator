"""The clean panel keeps only the presets stage 0b validated the judge on, and its
lag table gives the judge each part's recorded lag, or none where it is ambiguous."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

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


def test_the_verdict_counts_as_declared():
    import kill_tests_pr12_verdict as V

    def row(band, model, vs_shuffled, vs_constant, pick):
        return {"band": band, "model": model, "model_vs_shuffled": vs_shuffled,
                "model_vs_constant": vs_constant, "pick": pick}

    rows = [row("b1", -0.3, -0.1, -0.1, "x"), row("b2", -0.2, 0.0, 0.0, "y"),
            row("b3", -0.4, -0.2, 0.1, "z"), row("b4", -0.2, -0.1, -0.2, "w")]
    r = V.k3_reading(rows)
    assert r["better_than_shuffled_ties_half"] == 3.5          # a shuffled tie is half
    assert r["closer_than_constant"] == 2 and r["constant_ties"] == 1
    assert not r["pass"], "2 of 4 against the constant is not a majority"
    rows[2] = row("b3", -0.4, -0.2, -0.1, "z")
    assert V.k3_reading(rows)["pass"]
    rows = [dict(r, model=-0.12) for r in rows]                # above the clear cut
    assert not V.k3_reading(rows)["pass"]
