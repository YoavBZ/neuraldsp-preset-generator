"""The amp-reach measurement's oracles and decision (`docs/amp-reach-plan.md`)."""

from __future__ import annotations

import math
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import amp_reach as R  # noqa: E402


def _d(values):
    """{candidate: (half A, half B)} -> the distance table, same under both band sets."""
    return {f"{c}|{h}|{b}": v[i] for c, v in values.items() for i, h in enumerate("AB")
            for b in R.BAND_SETS}


def test_the_oracle_chooses_on_half_a_and_scores_on_half_b():
    d = _d({"x:factory:a": (1.0, 3.0), "x:factory:b": (2.0, 1.0)})
    assert R.oracle(d, ["x:factory:a", "x:factory:b"], "recording") == ("x:factory:a", 3.0)


def _parts(reach):
    """Parts whose recordings `reach` names the amp that gets close (others don't)."""
    meta, dist = {}, {}
    menus = {a: [f"{a}:factory:{i}" for i in range(6)] for a in R.AMPS}
    for n, amp in enumerate(reach):
        values = {}
        for a in R.AMPS:
            for i, c in enumerate(menus[a]):
                values[c] = (1.0, 1.0) if (a == amp and i == 0) else (2.0 + i * .01, 2.0)
            values[f"{a}:template+R"] = (2.5, 2.5)
        p = f"p{n}"
        meta[p] = {"band": f"b{n % 4}"}
        dist[p] = _d(values)
    return list(meta), meta, dist, menus


def test_another_amp_on_a_minority_of_recordings_is_counted():
    parts, meta, dist, menus = _parts(["sw50r"] * 6 + ["ac20", "pr12"] * 2)
    seeds = {p: p for p in parts}
    by = {b: R.comparison(parts, meta, dist, menus, "sw50r", b, seeds) for b in R.BAND_SETS}
    r = by["recording"]
    assert r["other_amp_clearly_closer_parts"] == 4 and r["other_amp_clearly_closer_bands"] == 4
    reasons = R.verdict({("sw50r", "all"): by})[("sw50r", "all")]
    assert "another amp is clearly closer on a third of the parts" in reasons


def test_one_amp_reaching_everything_adds_nothing():
    parts, meta, dist, menus = _parts(["sw50r"] * 10)
    seeds = {p: p for p in parts}
    by = {b: R.comparison(parts, meta, dist, menus, "sw50r", b, seeds) for b in R.BAND_SETS}
    assert by["recording"]["full_joint_vs_tested"] == 0.0
    assert by["recording"]["other_amp_clearly_closer_parts"] == 0
    assert R.verdict({("sw50r", "all"): by})[("sw50r", "all")] == []


def test_the_minority_rule_is_held_against_a_label_permutation_null():
    import amp_reach_null as N

    # Another amp reaches four of ten recordings that SW50R can't.
    parts, meta, dist, menus = _parts(["sw50r"] * 6 + ["ac20", "pr12"] * 2)
    bands_of = {p: meta[p]["band"] for p in parts}
    labels = {c: a for a in R.AMPS for c in menus[a]}
    observed = N.minority(dist, parts, bands_of, labels, "sw50r", "recording")
    assert observed == (4, 4)
    q95, counts = N.null_quantile(dist, parts, bands_of, labels, "sw50r", "recording", "s")
    # With labels shuffled the one close preset per part is SW50R's a third of the time,
    # so the null often counts other amps' wins too; the observed count is not beyond it.
    assert len(counts) == N.PERMUTATIONS and q95 >= 4
