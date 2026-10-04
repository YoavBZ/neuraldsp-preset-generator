"""The amp check's guessing and offering rules (`docs/amp-identifiability-plan.md`)."""

from __future__ import annotations

import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import amp_identifiability as A  # noqa: E402


def _matrix(distance):
    names = [f"{a}:factory:{a}{i}" for a in ("ac20", "pr12", "sw50r") for i in range(5)]
    return {t: {c: distance(t, c) for c in names if c != t} for t in names}


def test_an_amp_whose_presets_sit_together_is_always_guessed():
    acc, k = A.guesses(_matrix(lambda t, c: 1.0 if t[:4] == c[:4] else 2.0), seed="p")
    assert k == 4 and set(acc.values()) == {1.0}


def test_amps_the_judge_cannot_separate_are_guessed_at_chance():
    rng = random.Random(0)
    acc, _ = A.guesses(_matrix(lambda t, c: rng.random()), seed="p")
    assert abs(sum(acc.values()) / len(acc) - 1 / 3) < 0.12


def test_a_target_with_too_many_refusals_is_not_scored():
    m = _matrix(lambda t, c: 1.0)
    t = "ac20:factory:ac200"
    for c in list(m[t]):
        if c.startswith("pr12:"):
            m[t][c] = None
    acc, _ = A.guesses(m, seed="p")
    assert acc[t] is None and acc["ac20:factory:ac201"] is not None


def test_only_clean_presets_and_the_dry_templates_are_offered():
    loud = {"sw50r:factory:X/Metal"}.__contains__
    assert A.offered("sw50r:factory:X/Clean", loud)
    assert not A.offered("sw50r:factory:X/Metal", loud)
    assert A.offered("pr12:template+R", loud)
    assert not A.offered("pr12:template", loud)


def test_the_sign_flip_p():
    assert A.sign_flip_p([0.3, 0.2, 0.1]) == 1 / 8
    assert A.sign_flip_p([0.3, -0.3]) == 3 / 4
