"""Pure, private trial planning and listener-consistency accounting.

An audition's primary pair is the only objective-agreement observation. Hidden
repeat and catch blocks ask whether the same listener gives stable answers;
they are not additional target or objective observations.
"""

from __future__ import annotations

import random

CHOICES = ("A", "B", "indistinguishable")
ROLES = ("first", "second")
MAX_REPEATS = 3


def plan_trials(seed: int, blind_key: dict[str, str], *, repeats: int = 0,
                catch: bool = False) -> list[dict] | None:
    """Return a shuffled secret plan, or None for the legacy one-trial file.

    The first repeat always reverses the primary labels. Later repeats receive
    new independent mappings. Trial order is shuffled separately from the
    primary A/B assignment; the listener sees only numbered blocks.
    """
    if type(repeats) is not int or not 0 <= repeats <= MAX_REPEATS:
        raise ValueError(f"hidden repeats must be between 0 and {MAX_REPEATS}")
    if type(catch) is not bool:
        raise ValueError("catch must be a boolean")
    if set(blind_key) != {"A", "B"} or set(blind_key.values()) != set(ROLES):
        raise ValueError("primary blind key must map A/B to first/second")
    if repeats == 0 and not catch:
        return None
    rng = random.Random(seed ^ 0xA81D17C4)
    trials = [{"kind": "primary", "blind_key": dict(blind_key)}]
    for index in range(repeats):
        flip = True if index == 0 else bool(rng.getrandbits(1))
        mapping = ({"A": blind_key["B"], "B": blind_key["A"]}
                   if flip else dict(blind_key))
        trials.append({"kind": "repeat", "blind_key": mapping})
    if catch:
        role = ROLES[rng.randrange(2)]
        trials.append({"kind": "catch", "blind_key": {"A": role, "B": role}})
    rng.shuffle(trials)
    return [{**trial, "ordinal": index + 1} for index, trial in enumerate(trials)]


def primary_answer(trials: list[dict] | None, answers: list[str],
                   blind_key: dict[str, str]) -> str:
    """Select the primary answer without leaking trial types to the listener."""
    if trials is None:
        if len(answers) != 1 or answers[0] not in CHOICES:
            raise ValueError("one closeness answer is required")
        return answers[0]
    _validate_trials(trials, answers, blind_key)
    return answers[next(i for i, trial in enumerate(trials)
                        if trial["kind"] == "primary")]


def _validate_trials(trials: list[dict], answers: list[str],
                     blind_key: dict[str, str]) -> None:
    if not isinstance(trials, list) or not 2 <= len(trials) <= MAX_REPEATS + 2:
        raise ValueError("invalid hidden-trial plan")
    if not isinstance(answers, list) or len(answers) != len(trials) or any(
            answer not in CHOICES for answer in answers):
        raise ValueError(f"exactly {len(trials)} ordered closeness answers are required")
    if set(blind_key) != {"A", "B"} or set(blind_key.values()) != set(ROLES):
        raise ValueError("invalid primary blind key")
    kinds = []
    for index, trial in enumerate(trials):
        if not isinstance(trial, dict) or trial.get("ordinal") != index + 1:
            raise ValueError("hidden-trial order is invalid")
        kind, mapping = trial.get("kind"), trial.get("blind_key")
        if kind not in ("primary", "repeat", "catch") or not isinstance(mapping, dict):
            raise ValueError("hidden-trial kind or mapping is invalid")
        if set(mapping) != {"A", "B"} or not set(mapping.values()) <= set(ROLES):
            raise ValueError("hidden-trial A/B mapping is invalid")
        if kind in ("primary", "repeat") and set(mapping.values()) != set(ROLES):
            raise ValueError("a non-catch trial must compare both alternatives")
        if kind == "catch" and mapping["A"] != mapping["B"]:
            raise ValueError("a catch trial must play one alternative twice")
        if kind == "primary" and mapping != blind_key:
            raise ValueError("primary trial disagrees with the frozen objective mapping")
        kinds.append(kind)
    if kinds.count("primary") != 1 or kinds.count("catch") > 1 or kinds.count("repeat") > MAX_REPEATS:
        raise ValueError("hidden-trial kinds are invalid")


def consistency(trials: list[dict], answers: list[str],
                blind_key: dict[str, str]) -> dict:
    """Score repeat-role stability and catch ties, never objective agreement."""
    _validate_trials(trials, answers, blind_key)
    primary_index = next(i for i, row in enumerate(trials) if row["kind"] == "primary")
    primary = answers[primary_index]
    primary_role = (primary if primary == "indistinguishable"
                    else trials[primary_index]["blind_key"][primary])
    repeats, catches = [], []
    for trial, answer in zip(trials, answers):
        if trial["kind"] == "repeat":
            role = answer if answer == "indistinguishable" else trial["blind_key"][answer]
            repeats.append(role == primary_role)
        elif trial["kind"] == "catch":
            catches.append(answer == "indistinguishable")
    return {
        "schema": "listener-consistency-v1",
        "repeat": {"trials_not_independent_n": len(repeats),
                   "consistent": sum(repeats),
                   "fraction": sum(repeats) / len(repeats) if repeats else None},
        "catch": {"trials_not_independent_n": len(catches),
                  "indistinguishable": sum(catches),
                  "fraction": sum(catches) / len(catches) if catches else None},
    }
