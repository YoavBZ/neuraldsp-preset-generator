"""The amp check's guessing, family and offering rules (`docs/amp-identifiability-plan.md`)."""

from __future__ import annotations

import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "research"))

import amp_identifiability as A  # noqa: E402


def _matrix(distance, per_amp=5):
    names = [f"{a}:factory:Artists/{a}{i}/x" for a in ("ac20", "pr12", "sw50r")
             for i in range(per_amp)]
    return {t: {c: [distance(t, c), 0.0, distance(t, c)] for c in names if c != t}
            for t in names}


def test_an_amp_whose_presets_sit_together_is_always_guessed():
    out = A.guesses(_matrix(lambda t, c: 1.0 if t[:4] == c[:4] else 2.0), seed="p")
    assert {g[0] for g in out.values()} == {1.0}
    assert {g[2] for g in out.values()} == {4}          # the own amp's pool sets k


def test_amps_the_judge_cannot_separate_are_guessed_at_chance():
    rng = random.Random(0)
    out = A.guesses(_matrix(lambda t, c: rng.random(), per_amp=8), seed="p")
    assert abs(sum(g[0] for g in out.values()) / len(out) - 1 / 3) < 0.08


def test_the_targets_family_is_left_out_so_a_twin_cannot_win():
    m = _matrix(lambda t, c: 2.0)
    twin_a, twin_b = "sw50r:factory:Artists/Zaza/Open", "sw50r:factory:Artists/Zaza/Open Trem"
    for name in (twin_a, twin_b):
        m[name] = {c: [2.0, 0, 2.0] for c in m if c != name}
    for t in list(m):
        for name in (twin_a, twin_b):
            if t != name:
                m[t][name] = [2.0, 0, 2.0]
    m[twin_a][twin_b] = m[twin_b][twin_a] = [0.0, 0, 0.0]          # identical renders
    for t_, row in m.items():                      # everyone else: other amps are closer
        for c in row:
            if row[c] is not None and row[c][0] != 0.0:
                same = c.split(":")[0] == t_.split(":")[0]
                row[c] = [3.0 if same else 1.0, 0, 3.0 if same else 1.0]
    out = A.guesses(m, seed="p")
    assert out[twin_a][0] == 0.0, "without its twin, the target's own amp never wins"


def test_families():
    assert A.family("pr12:template+R") == A.family("sw50r:template+R") == "templates"
    assert A.family("ac20:factory:Default", {"ac20:factory:Default"}) == "templates"
    assert A.family("sw50r:factory:Artists/Neil Zaza/Bell") == "artist:Neil Zaza"
    assert A.family("pr12:factory:Neural DSP/Lush") == "pr12:factory:Neural DSP/Lush"


def test_a_target_with_too_few_candidates_left_is_not_scored():
    m = _matrix(lambda t, c: 1.0, per_amp=5)
    t = "ac20:factory:Artists/ac200/x"
    for c in list(m[t]):
        if c.startswith("pr12:"):
            m[t][c] = None
    assert A.guesses(m, seed="p")[t] is None


def test_only_clean_presets_with_their_cab_and_the_dry_templates_are_offered():
    loud = {"sw50r:factory:X/Metal"}.__contains__
    assert A.offered("sw50r:factory:X/Clean", loud)
    assert not A.offered("sw50r:factory:X/Metal", loud)
    assert not A.offered("sw50r:factory:X/Clean", loud, sections_on=lambda c: False)
    assert A.offered("pr12:template+R", loud)
    assert not A.offered("pr12:template", loud)


def test_the_sign_flip_p():
    assert A.sign_flip_p([0.3, 0.2, 0.1]) == 1 / 8
    assert A.sign_flip_p([0.3, -0.3]) == 3 / 4
