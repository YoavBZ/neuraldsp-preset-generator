"""The amp-reach measurement's oracles and statistics (`docs/amp-reach-plan.md`)."""

from __future__ import annotations

import math
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import amp_reach as R  # noqa: E402


def _distances(close_amp):
    """Each amp has two presets; `close_amp`'s second preset is closest on both halves."""
    d = {}
    for a in R.AMPS:
        for i in range(2):
            c = f"{a}:factory:X/{a}{i}"
            near = a == close_amp and i == 1
            for half in ("A", "B"):
                for bands in R.BAND_SETS:
                    d[f"{c}|{half}|{bands}"] = 1.0 if near else 2.0 + i * 0.1
        for half in ("A", "B"):
            for bands in R.BAND_SETS:
                d[f"{a}:template+R|{half}|{bands}"] = 2.5
    menus = {a: [f"{a}:factory:X/{a}{i}" for i in range(2)] for a in R.AMPS}
    return d, menus


def test_the_oracle_chooses_on_half_a_and_scores_on_half_b():
    d, menus = _distances("pr12")
    d["pr12:factory:X/pr121|B|recording"] = 1.7          # chosen on A, worse on B
    pick, score = R.oracle(d, menus["pr12"], "recording")
    assert pick == "pr12:factory:X/pr121" and score == 1.7


def test_the_joint_menu_is_credited_only_where_another_amp_reaches_further():
    rows = []
    for i, amp in enumerate(["pr12", "pr12", "ac20", "sw50r"]):
        d, menus = _distances(amp)
        rows.append({"part": f"p{i}", "band": f"b{i}",
                     "row": R.part_row(d, menus, "recording", random.Random(0))})
    out = R.summarise(rows)
    assert out["joint_pick_amp_share"] == {"ac20": 0.25, "pr12": 0.5, "sw50r": 0.25}
    # Against PR12 the joint menu gains on the two parts PR12 cannot reach.
    assert out["best_single_amp"] == "pr12"
    assert out["joint_vs_best_amp"] == 0.5 * (0.0 + math.log(1.0 / 2.0))
    assert out["amp_vs_own_template"]["pr12"] == 0.5 * (math.log(1 / 2.5) + math.log(2 / 2.5))
