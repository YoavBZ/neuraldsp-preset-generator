"""M4's exit criterion: does the whole pipeline beat what it replaces?

Sample N random legal parameter vectors, render each one, throw the vector away,
and try to recover it from the audio alone. Then report four things **separately**,
because merging them is how a pipeline gets shipped on the strength of the one
number that looks best:

- **parameter MAE**, normalised, and selector accuracy — did it find the settings?
- **objective distance** to the ground-truth render — did it find the *sound*?
- **render count and wall time** — what did it cost?
- **failure rate** — how often did nothing come back?

The two questions in the first two bullets are genuinely different and the answers
diverge. A different volume with a compensating EQ curve can sound almost
identical, so the objective closes while the parameter MAE does not. That is not a
flaw in the measurement, it is the actual situation: the plugin's controls are not
identifiable from its output, and a pipeline that matches the sound while getting
the numbers wrong is still doing its job. Reporting only the MAE would condemn it;
reporting only the objective would let a real failure through.

**Ship only if the full pipeline beats both baselines** — the recipe-only generator
this repository already has, and inversion alone with no search. `compare_baselines`
runs all three on the same targets with the same probe DI, and the comparison is
only worth anything because it is the same targets.

This is a *local* check, not CI. Fifty targets at a 300-render budget is 15,000
renders, which is about eighty minutes on the synthetic chain and days on the real
plugin. `--targets` and `--budget` exist so a smaller version can run in a test.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from match.space import Space

# The three pipelines being compared. `recipe` is the baseline this repository
# already ships: pick a preset from the recipe stack and stop. `inversion` adds the
# calculated step and no search. `full` is everything.
ARMS = ("recipe", "inversion", "full")


class BenchmarkError(ValueError):
    """A benchmark that cannot be set up."""


@dataclass
class Outcome:
    """One arm's attempt at one target. Every field is reported, none merged."""

    arm: str
    target_index: int
    parameter_mae: Optional[float] = None
    selector_accuracy: Optional[float] = None
    objective: Optional[float] = None
    renders: int = 0
    wall_ms: float = 0.0
    failed: bool = False
    error: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Every outcome, plus the arithmetic the exit criterion asks for."""

    outcomes: List[Outcome] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)

    def by_arm(self, arm: str) -> List[Outcome]:
        return [o for o in self.outcomes if o.arm == arm]

    def summarise(self, arm: str) -> Dict[str, Any]:
        """One arm's numbers, with the failures counted rather than dropped.

        The averages are over the outcomes that *succeeded*, and the failure rate is
        reported next to them, because an arm that fails half its targets and does
        well on the rest is not better than one that succeeds everywhere and does
        slightly worse. Averaging over successes alone without saying so is the
        specific dishonesty this shape is designed to prevent.
        """
        outcomes = self.by_arm(arm)
        if not outcomes:
            return {"arm": arm, "targets": 0}
        good = [o for o in outcomes if not o.failed]
        return {
            "arm": arm,
            "targets": len(outcomes),
            "failures": len(outcomes) - len(good),
            "failure_rate": (len(outcomes) - len(good)) / len(outcomes),
            "parameter_mae": _mean(o.parameter_mae for o in good),
            "selector_accuracy": _mean(o.selector_accuracy for o in good),
            "objective": _mean(o.objective for o in good),
            "objective_median": _median([o.objective for o in good
                                         if o.objective is not None]),
            "renders": sum(o.renders for o in outcomes),
            "wall_s": round(sum(o.wall_ms for o in outcomes) / 1000.0, 1),
        }

    def verdict(self) -> Tuple[bool, List[str]]:
        """Whether M4 ships, and the reasoning either way.

        Both baselines have to be beaten on the objective — that is the plan's
        wording and it is the right test, because the objective is what the pipeline
        optimises and the parameters are not identifiable. The parameter MAE is
        reported and *not* part of the gate, and the reasoning is stated in the
        result so nobody has to guess whether it was forgotten.
        """
        full = self.summarise("full")
        reasons = []
        ships = True
        for baseline in ("recipe", "inversion"):
            other = self.summarise(baseline)
            if other.get("targets", 0) == 0:
                reasons.append(f"the {baseline} baseline was not run, so there is "
                               f"nothing to beat")
                ships = False
                continue
            mine, theirs = full.get("objective"), other.get("objective")
            if mine is None or theirs is None:
                reasons.append(f"the {baseline} baseline produced no comparable "
                               f"objective")
                ships = False
                continue
            if mine < theirs:
                reasons.append(f"beats {baseline}: {mine:.3f} against {theirs:.3f} "
                               f"mean objective distance")
            else:
                reasons.append(f"does NOT beat {baseline}: {mine:.3f} against "
                               f"{theirs:.3f} — the extra renders bought nothing")
                ships = False
        if full.get("failure_rate", 0.0) > 0.1:
            reasons.append(f"and fails {100 * full['failure_rate']:.0f}% of targets, "
                           f"which is too many to call the mean representative")
            ships = False
        reasons.append(
            f"parameter MAE is {_show(full.get('parameter_mae'))} and selector "
            f"accuracy {_show(full.get('selector_accuracy'))}; neither is part of "
            f"this gate, because the plugin's controls are not identifiable from its "
            f"output and a match that sounds right with different numbers is still a "
            f"match"
        )
        return ships, reasons


# --- sampling ----------------------------------------------------------------


def random_vector(space: Space, rng, supported: Optional[Sequence[str]] = None,
                  switch_probability: float = 0.35) -> Dict[Any, Any]:
    """One legal parameter vector, uniform over each dimension's declared range.

    Uniform rather than plausible, and that is the point: a benchmark over presets a
    person would dial is a benchmark over the easy cases. A random legal vector may
    sound terrible, and recovering it is still exactly the task.

    Switches are on with probability `switch_probability` rather than half, because
    at half the average target has four effects running and the objective is then
    dominated by whether the search found the delay. Section switches are forced on:
    a target with the cab section bypassed is a target with no cabinet, which is not
    a tone anyone is asking to match.
    """
    keys = None if supported is None else {
        key if isinstance(key, str) else "/".join(str(p) for p in key)
        for key in supported
    }
    values: Dict[Any, Any] = {}
    for dimension in space.dimensions:
        if keys is not None and dimension.path not in keys:
            continue
        if dimension.key == "selectedAmp":
            continue
        if dimension.switch:
            forced = dimension.key.endswith("sectionActive")
            values[(dimension.module, dimension.key)] = (
                True if forced else bool(rng.random() < switch_probability))
        elif dimension.kind == "enum":
            members = sorted((dimension.members or {}), key=int)
            if members:
                values[(dimension.module, dimension.key)] = int(
                    members[int(rng.integers(len(members)))])
        else:
            low, high = dimension.bounds()
            values[(dimension.module, dimension.key)] = dimension.quantise(
                float(low + rng.random() * (high - low)))
    return values


def parameter_error(space: Space, truth: Mapping, found: Mapping,
                    only: Optional[Sequence[str]] = None
                    ) -> Tuple[Optional[float], Optional[float]]:
    """Normalised MAE over the continuous dimensions, and selector accuracy.

    Normalised so a 10 Hz miss on a 1500 ms delay does not swamp a 40% miss on a
    knob: every dimension is measured as a fraction of its own declared range, which
    is the only way to average across units at all.

    Continuous and discrete are kept apart because they are different mistakes. A
    knob 8% out is nearly right; the wrong microphone is wrong. Averaging them
    produces a number that means neither.
    """
    from match.space import _get, _to_unit

    wanted = None if only is None else set(only)
    errors = []
    hits = misses = 0
    for dimension in space.dimensions:
        if wanted is not None and dimension.path not in wanted:
            continue
        mine, theirs = _get(truth, (dimension.module, dimension.key)), _get(
            found, (dimension.module, dimension.key))
        if mine is None or theirs is None:
            continue
        if dimension.switch or dimension.kind == "enum":
            if _to_unit(dimension, mine) == _to_unit(dimension, theirs):
                hits += 1
            else:
                misses += 1
        else:
            errors.append(abs(_to_unit(dimension, mine) - _to_unit(dimension, theirs)))
    mae = (sum(errors) / len(errors)) if errors else None
    accuracy = (hits / (hits + misses)) if (hits + misses) else None
    return mae, accuracy


# --- the three arms ----------------------------------------------------------


def compare_baselines(renderer, space: Space, probe_di, seed: Mapping,
                      targets: int = 50, budget: int = 300,
                      profile: str = "unpaired-v1", rng=None,
                      arms: Sequence[str] = ARMS,
                      pack_id: str = "morgan",
                      amp: Optional[str] = None,
                      progress=None) -> BenchmarkResult:
    """Run each arm against the same targets, and report them side by side.

    `seed` is the recipe-stack starting point, which is also the `recipe` arm's whole
    answer: that baseline is "use the preset you would have used", and its score is
    what the other two have to beat. Same targets, same probe DI, same objective for
    all three — the comparison is worth nothing otherwise.
    """
    from analysis import io, require

    require("running the match benchmark")
    import numpy as np

    from analysis.fingerprint import fingerprint
    from match import invert, search

    rng = np.random.default_rng(11) if rng is None else rng
    unknown = [arm for arm in arms if arm not in ARMS]
    if unknown:
        raise BenchmarkError(f"unknown arm(s) {', '.join(unknown)}; "
                             f"available: {', '.join(ARMS)}")

    supported = list(renderer.parameter_specs())
    scorer = search.Evaluator(renderer, fingerprint(
        io.from_samples(probe_di, renderer.metadata().sample_rate),
        regime="probe", excerpt_s=None), probe_di, space, profile=profile)
    result = BenchmarkResult()
    amp = amp or space.amp_prefix(seed)

    for index in range(int(targets)):
        truth = dict(seed)
        truth.update(random_vector(space, rng, supported=supported))
        truth[("", "selectedAmp")] = _get_or(seed, ("", "selectedAmp"), 2)
        rendered = renderer.render(probe_di, scorer._settings(truth))
        if rendered.silent:
            result.caveats.append(
                f"target {index} rendered silent from a legal parameter vector — "
                f"a gate threshold above the signal, most likely — so it was skipped "
                f"rather than counted as a failure of any arm"
            )
            continue
        target = fingerprint(io.from_samples(
            rendered.audio, rendered.metadata.sample_rate),
            regime="probe", excerpt_s=None)

        for arm in arms:
            started = time.perf_counter()
            outcome = Outcome(arm=arm, target_index=index)
            try:
                found, renders = _run_arm(arm, renderer, target, probe_di, space,
                                          seed, budget, profile, invert, search,
                                          rng, pack_id, amp)
            except (ValueError, RuntimeError) as e:
                outcome.failed = True
                outcome.error = f"{type(e).__name__}: {e}"
                outcome.wall_ms = (time.perf_counter() - started) * 1000.0
                result.outcomes.append(outcome)
                continue
            outcome.renders = renders
            outcome.wall_ms = (time.perf_counter() - started) * 1000.0
            scored = scorer_score(scorer, target, found)
            if scored is None:
                outcome.failed = True
                outcome.error = "the recovered vector produced nothing comparable"
            else:
                outcome.objective = scored
                mae, accuracy = parameter_error(
                    space, truth, found,
                    only=[d.path for d in space.dimensions
                          if d.path in {k if isinstance(k, str)
                                        else "/".join(str(p) for p in k)
                                        for k in supported}])
                outcome.parameter_mae = mae
                outcome.selector_accuracy = accuracy
            result.outcomes.append(outcome)
        if progress is not None:
            progress(index + 1, int(targets))
    return result


def scorer_score(scorer, target, values: Mapping) -> Optional[float]:
    """One vector's weighted distance to a target, through the shared evaluator."""
    scorer.target = target
    scored = scorer.evaluate(values)
    return scored.total if scored.objectives else None


def _run_arm(arm: str, renderer, target, probe_di, space, seed, budget, profile,
             invert, search, rng, pack_id: str, amp: Optional[str]):
    """One arm's answer for one target, and how many renders it took.

    The three arms are **nested**, which is what makes the comparison mean anything:
    `inversion` is `recipe` plus the calculated step, and `full` is `inversion` plus
    the search. The first version of this searched from the recipe seed instead of
    the inverted one, so the `full` arm was search-*only* — and it scored 1.401
    against inversion's 1.021, reporting DOES NOT SHIP for a mistake in the harness
    rather than in the pipeline. A benchmark whose arms are not nested does not
    measure what each stage adds.

    The render counts are not comparable by design, and the table says so: `recipe`
    spends none, `inversion` spends one (the seed render its delta is measured
    against), and `full` spends that plus its budget. The question is what the extra
    renders buy, so the cost has to travel with the answer.
    """
    if arm == "recipe":
        return dict(seed), 0

    inverted, spent = _invert_from(renderer, target, probe_di, space, seed, profile,
                                   invert, search, pack_id, amp)
    if arm == "inversion":
        return inverted, spent

    outcome = search.search(renderer, target, probe_di, space, inverted,
                            budget=budget, profile=profile, shortlist=1, rng=rng)
    if not outcome.shortlist:
        raise BenchmarkError("the search returned no candidate")
    return outcome.shortlist[0].values, outcome.renders + spent


def _invert_from(renderer, target, probe_di, space, seed, profile, invert, search,
                 pack_id: str, amp: Optional[str]):
    """The seed with everything calculable calculated, and the one render it cost."""
    from analysis import io
    from analysis.fingerprint import fingerprint

    if amp is None:
        raise BenchmarkError(
            "the inversion step needs to know which amp is selected; pass amp= or a "
            "seed with a selectedAmp value"
        )
    evaluator = search.Evaluator(renderer, target, probe_di, space, profile=profile,
                                 recipe=seed)
    rendered = renderer.render(probe_di, evaluator._settings(seed))
    printed = fingerprint(io.from_samples(rendered.audio,
                                          rendered.metadata.sample_rate),
                          regime="probe", excerpt_s=None)
    calculated = invert.invert(target, printed, amp=amp, pack_id=pack_id)
    merged = dict(seed)
    known = {d.path: (d.module, d.key) for d in space.dimensions}
    known["selectedAmp"] = ("", "selectedAmp")
    for path, value in calculated.as_settings().items():
        key = known.get(path) or known.get(path.lstrip("/"))
        if key is not None:
            merged[key] = value
    return merged, 1


# --- helpers ----------------------------------------------------------------


def _get_or(values: Mapping, key, default):
    from match.space import _get

    found = _get(values, key)
    return default if found is None else found


def _mean(values) -> Optional[float]:
    present = [float(v) for v in values if v is not None]
    return round(sum(present) / len(present), 4) if present else None


def _median(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(float(v) for v in values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[middle], 4)
    return round((ordered[middle - 1] + ordered[middle]) / 2.0, 4)


def _show(value: Optional[float]) -> str:
    return "not measured" if value is None else f"{value:.4f}"


def format_table(result: BenchmarkResult, arms: Sequence[str] = ARMS) -> str:
    """The four numbers per arm, in a table, never collapsed into a score."""
    columns = [("arm", 10), ("targets", 8), ("fail%", 7), ("param MAE", 10),
               ("selector", 9), ("objective", 10), ("median", 8), ("renders", 8),
               ("wall s", 8)]
    lines = ["  ".join(name.ljust(width) for name, width in columns),
             "  ".join("-" * width for _, width in columns)]
    for arm in arms:
        summary = result.summarise(arm)
        if not summary.get("targets"):
            continue
        cells = [
            arm,
            str(summary["targets"]),
            f"{100 * summary['failure_rate']:.0f}",
            _show(summary["parameter_mae"]),
            _show(summary["selector_accuracy"]),
            _show(summary["objective"]),
            _show(summary["objective_median"]),
            str(summary["renders"]),
            f"{summary['wall_s']:.0f}",
        ]
        lines.append("  ".join(cell.ljust(width)
                               for cell, (_, width) in zip(cells, columns)))
    ships, reasons = result.verdict()
    lines.append("")
    lines.append("SHIPS" if ships else "DOES NOT SHIP")
    lines.extend(f"  - {reason}" for reason in reasons)
    if result.caveats:
        lines.append("")
        lines.extend(f"  ! {caveat}" for caveat in result.caveats)
    return "\n".join(lines)
