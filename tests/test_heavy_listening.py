"""Listening check H (`docs/heavy-listening-plan.md`): the trial rules and the scorer."""

from __future__ import annotations

import pathlib
import sys

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learn import build_heavy_listening as H  # noqa: E402


def q(distance, tonal, temporal, part="p1", band="b1", amp="sw50r", first="x", second="y"):
    return {"part": part, "band": band, "amp": amp, "first": first, "second": second,
            "exposure": 1.0, "source": "menu",
            "log_ratio": {"distance": distance, "tonal": tonal, "temporal": temporal}}


def test_block_rules():
    assert H.conflict(q(0.0, -0.2, 0.15))
    assert not H.conflict(q(0.0, -0.2, 0.05))           # one part under 0.10
    assert not H.conflict(q(0.0, -0.2, -0.3))           # same sign
    assert H.clear(q(0.2, 0.3, 0.1)) and not H.clear(q(0.2, 0.3, -0.2))
    assert H.small(q(-0.05, -0.04, -0.06)) and not H.small(q(0.1, 0.1, 0.1))


def test_select_keeps_the_caps():
    cands = [q(0.2, 0.2, 0.2, part=f"p{i % 2}", amp=a, first=f"x{i}")
             for i in range(6) for a in ("sw50r", "ac20")]
    state = ({}, {}, set())
    got = H.select(cands, {"sw50r": 3, "ac20": 3}, state, lambda x: x["first"])
    per_part = {}
    for x in got:
        per_part[x["part"]] = per_part.get(x["part"], 0) + 1
    assert all(n <= H.PER_PART for n in per_part.values())
    assert len(got) == 2 * H.PER_PART                    # two parts, two trials each


def test_phone_template_asks_about_tone():
    page = H.phone_template()
    assert "Listening check H" in page and "in tone" in page and '"heavy-' in page


def row(trial, block, sitting=1, **kw):
    r = {"trial": trial, "block": block, "sitting": sitting, "amp": "sw50r", "source": "menu",
         "id": kw.pop("id", f"{block[0]}{trial:02d}"), "A": f"a{trial}", "B": f"b{trial}"}
    r.update(kw)
    return r


def test_score_rows_outcomes():
    rows = [row(n, "texture", tonal_pick="A", judge_pick="B", id=f"t{n:02d}")
            for n in range(1, 17)]
    rows += [row(16 + n, "clear", judge_pick="A") for n in range(1, 11)]
    rows += [row(26 + n, "small", judge_pick="A") for n in range(1, 5)]
    rows += [row(30 + n, "hidden", copy="A") for n in range(1, 4)]
    rows += [row(33 + n, "repeat", sitting=2, of=f"t{n:02d}", A=f"b{n}", B=f"a{n}")
             for n in range(1, 4)]
    answers = {r["trial"]: "A" for r in rows}
    answers.update({34: "B", 35: "B", 36: "B"})          # repeats: the same preset again
    out = H.score_rows(rows, answers)
    assert out["outcome"] == {"void": False, "texture": "tonal", "clear": "judge extends"}
    assert out["reliability"]["repeats_consistent"] == 3
    answers.update({31: "B", 32: "B"})                   # two hidden references missed
    assert H.score_rows(rows, answers)["outcome"] == {"void": True}
