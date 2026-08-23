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

import queue
import threading
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

    def paired(self, arm: str, other: str) -> Tuple[List[Outcome], List[Outcome]]:
        """The two arms' outcomes on the targets where *both* succeeded.

        `summarise` averages each arm over its own successes, which is the right
        number to report and the wrong one to compare. An arm that failed 49 of 50
        targets and happened to score 2.0 on the easy one would set a bar the other
        arm clears by construction — measured, that produced SHIPS from a comparison
        of 50 targets against 1. The mirror image blocks a working pipeline.

        `compare_baselines` promises "the comparison is only worth anything because it
        is the same targets", and this is what makes that true after a failure.
        """
        mine = {o.target_index: o for o in self.by_arm(arm) if not o.failed}
        theirs = {o.target_index: o for o in self.by_arm(other) if not o.failed}
        shared = sorted(set(mine) & set(theirs))
        return [mine[i] for i in shared], [theirs[i] for i in shared]

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
        # Bound once. `summarise` is a full pass over every outcome and this method used
        # to call it four times for the same three arms, twice for `full` inside a single
        # conditional expression.
        summaries = {arm: self.summarise(arm) for arm in ARMS}
        full = summaries["full"]
        reasons = []
        ships = True
        for baseline in ("recipe", "inversion"):
            other = summaries[baseline]
            if other.get("targets", 0) == 0:
                reasons.append(f"the {baseline} baseline was not run, so there is "
                               f"nothing to beat")
                ships = False
                continue
            ours, theirs = self.paired("full", baseline)
            if not ours:
                # Which arm failed matters, and the message used to name the baseline
                # whatever the cause: with `full` failing every target it reported
                # "the recipe baseline produced no comparable objective" about a
                # baseline that had scored 1.0 on all fifty.
                #
                # A flat chain. This was a three-way conditional expression whose result
                # was then overwritten by an `if` on the next line, so its first branch
                # was reachable only when the full arm's mean objective was exactly 0.0.
                if full.get("objective") is None and other.get("objective") is None:
                    blamed = "neither arm succeeded on any target"
                elif full.get("objective") is None:
                    blamed = "the full pipeline scored nothing on any target"
                elif other.get("objective") is None:
                    blamed = f"the {baseline} baseline scored nothing"
                else:
                    blamed = "no target was scored by both arms"
                reasons.append(f"cannot compare against {baseline}: {blamed}")
                ships = False
                continue
            mine = sum(o.objective for o in ours) / len(ours)
            against = sum(o.objective for o in theirs) / len(theirs)
            shared = len(ours)
            if mine < against:
                reasons.append(f"beats {baseline}: {mine:.3f} against {against:.3f} "
                               f"mean objective distance over the {shared} targets "
                               f"both arms scored")
            else:
                reasons.append(f"does NOT beat {baseline}: {mine:.3f} against "
                               f"{against:.3f} over the {shared} targets both arms "
                               f"scored — the extra renders bought nothing")
                ships = False
            if shared < 0.7 * other["targets"]:
                reasons.append(f"and only {shared} of {other['targets']} targets "
                               f"were scored by both arms, so that comparison rests "
                               f"on less than it looks like")
                ships = False
        for arm in ("recipe", "inversion", "full"):
            summary = self.summarise(arm)
            if summary.get("targets") and summary["failure_rate"] > 0.1:
                reasons.append(
                    f"{arm} fails {100 * summary['failure_rate']:.0f}% of targets, "
                    f"which is too many to call its mean representative"
                )
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
                  switch_probability: float = 0.35,
                  base: Optional[Mapping] = None) -> Dict[Any, Any]:
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
    dimensions = space.dimensions
    if base is not None:
        # Keep every potentially gated control available to the sampler while
        # respecting selector routing such as Tone King's Lead/Rhythm channel.
        # Calling ``space.active(base)`` directly would also hide the knobs behind
        # effects that the sampler is about to switch on.
        routing = dict(base)
        for dimension in space.dimensions:
            if dimension.switch:
                routing[(dimension.module, dimension.key)] = True
        dimensions = space.active(routing)
    for dimension in dimensions:
        if keys is not None and dimension.path not in keys:
            continue
        if dimension.key == "selectedAmp":
            continue
        if dimension.switch:
            forced = _structural_enable(dimension)
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


def centre_seed(space: Space) -> Dict[Any, Any]:
    """Every control at the middle of its range, effects off, EQ and sections on.

    Not the recipe stack, and the difference matters for reading the `recipe` arm's
    score: this is a *neutral* starting point rather than a good one, so the number to
    beat is "the middle of every range", which is easier to beat than a preset someone
    chose. A recipe-stack seed would make the `recipe` baseline stronger and the
    comparison more honest — `packs/recipes.py` needs a genre or a reference to pick one,
    which a random target does not have, so the neutral seed is what a caller with no
    other information actually starts from.

    Here rather than in `scripts/benchmark_match.py`, next to `random_vector`, which is
    the same loop over the same three dimension kinds. It is a decision about the
    benchmark's *design* — the plan documents it by name as one — and it was living in
    the argument parser.
    """
    values: Dict[Any, Any] = {}
    for dimension in space.dimensions:
        if dimension.key == "selectedAmp":
            continue
        if dimension.switch:
            values[(dimension.module, dimension.key)] = (
                dimension.key.casefold().endswith("eqactive")
                or _structural_enable(dimension))
        elif dimension.kind == "enum":
            members = sorted((dimension.members or {}), key=int)
            if members:
                values[(dimension.module, dimension.key)] = int(members[0])
        else:
            low, high = dimension.bounds()
            values[(dimension.module, dimension.key)] = dimension.quantise(
                (low + high) / 2.0)
    if any(dimension.key == "selectedAmp" for dimension in space.dimensions):
        values[("", "selectedAmp")] = 2
    return values


def _structural_enable(dimension) -> bool:
    """A page/section bypass that must stay on in benchmark targets.

    Effect switches remain random. Structural bypasses do not describe a tone;
    switching one off makes a whole page unreachable and turns the benchmark into
    a topology lottery. Pack spellings differ in case and Tone King calls its amp
    page simply ``ampsActive``, so matching is case-insensitive.
    """
    key = dimension.key.casefold()
    return key.endswith("sectionactive") or key == "ampsactive"


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
                      switches: Optional[Sequence[str]] = None,
                      selectors: Optional[Sequence[str]] = None,
                      progress=None, workers: int = 1,
                      renderer_factory=None) -> BenchmarkResult:
    """Run each arm against the same targets, and report them side by side.

    `seed` is the recipe-stack starting point, which is also the `recipe` arm's whole
    answer: that baseline is "use the preset you would have used", and its score is
    what the other two have to beat. Same targets, same probe DI, same objective for
    all three — the comparison is worth nothing otherwise.

    `switches` and `selectors` go to the `full` arm's search only, which is the
    point of them: `recipe` and `inversion` have no way to choose a cabinet, so
    with nothing enumerated all three arms report the *same* selector accuracy in
    every run and that column measures nothing. It is the one column that can show
    the topology stage doing something.

    `workers > 1` requires `renderer_factory`: the renderer passed in is the
    serial instance and cannot be cloned safely by guessing its constructor.
    Each worker keeps one factory-created instance for its life.
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
    workers = int(workers)
    if workers < 1:
        raise BenchmarkError(f"workers must be at least 1, not {workers}")
    if workers > 1 and renderer_factory is None:
        raise BenchmarkError(
            f"workers={workers} needs renderer_factory so each worker can own "
            f"one backend instance; without it the run would silently be serial"
        )

    selection = {}
    if amp is not None:
        try:
            amp = invert.resolve_signal_path(pack_id, amp)
        except invert.InversionError as error:
            raise BenchmarkError(str(error)) from error
    else:
        amp = (space.amp_prefix(seed)
               or invert.selected_signal_path(pack_id, seed))
    if amp is not None:
        selection = invert.signal_path_selection(pack_id, amp)
        # The benchmark's requested path is part of both baselines and truth. It
        # must be selected before target generation, not merely named for inversion.
        seed = invert.apply_to(seed, selection, space)
    supported = search.supported_keys(renderer)
    if supported is not None and not any(
        dimension.path in supported for dimension in space.dimensions
    ):
        path_name = amp or "the selected signal path"
        raise BenchmarkError(
            f"the renderer supports no searchable controls for {pack_id}/{path_name}; "
            "a benchmark would sample no target settings"
        )
    scorer = search.Evaluator(renderer, fingerprint(
        io.from_samples(probe_di, renderer.metadata().sample_rate),
        regime="probe", excerpt_s=None), probe_di, space, profile=profile,
        reference_audio=probe_di)
    result = BenchmarkResult()

    # One independent stream per target, rather than one generator threaded through
    # every target and every search in turn. Two reasons, and the second is why this
    # is a fix rather than a refactor.
    #
    # It makes a target reproducible. §12i had to record that `--seed 0` does not
    # pin individual targets, because the search draws a variable number of times —
    # CMA-ES can stop early, and how many controls the screen freezes differs per
    # target — so on a backend that does not repeat itself, target *i*'s consumption
    # moved target *i+1*'s vector. Target *i* now depends on the seed and on `i`,
    # and on nothing that happened before it.
    #
    # And it is the precondition for running targets concurrently: a shared
    # generator makes the order they execute in part of the answer. Each target is
    # an independent experiment — its own truth, its own search, its own score — so
    # nothing but the generator was keeping them in a line.
    #
    # This does change which vectors get sampled, so figures from before it are not
    # comparable target-for-target. The distribution they are drawn from is
    # unchanged.
    streams = _spawn_streams(rng, int(targets), np)

    def one_target(index, own_renderer, own_scorer):
        """Everything one target needs, on one renderer.

        Every comparison a target makes — its truth against each arm's answer —
        stays inside `own_renderer`, which is what §12j requires: the offset
        between two plugin instances lands in any comparison spread across them.
        Targets themselves compare with nothing, so they are free to run at once.

        Returns `(outcomes, caveats)` rather than appending, so a concurrent caller
        can put them in index order instead of completion order.
        """
        outcomes, caveats = [], []
        stream = streams[index]
        truth = dict(seed)
        truth.update(random_vector(space, stream, supported=supported, base=truth))
        if selection:
            truth = invert.apply_to(truth, selection, space)
        elif any(dimension.key == "selectedAmp" for dimension in space.dimensions):
            truth[("", "selectedAmp")] = _get_or(seed, ("", "selectedAmp"), 2)
        rendered = own_renderer.render(probe_di, own_scorer._settings(truth))
        if rendered.silent:
            caveats.append(
                f"target {index} rendered silent from a legal parameter vector — "
                f"a gate threshold above the signal, most likely — so it was skipped "
                f"rather than counted as a failure of any arm"
            )
            return outcomes, caveats
        target = fingerprint(io.from_samples(
            rendered.audio, rendered.metadata.sample_rate),
            regime="probe", excerpt_s=None)

        for arm in arms:
            started = time.perf_counter()
            outcome = Outcome(arm=arm, target_index=index)
            try:
                found, renders, arm_caveats = _run_arm(
                    arm, own_renderer, target, probe_di, space, seed, budget,
                    profile, invert, search, stream, pack_id, amp, switches,
                    selectors, reference_audio=rendered.audio)
            except (ValueError, RuntimeError) as e:
                outcome.failed = True
                outcome.error = f"{type(e).__name__}: {e}"
                outcome.wall_ms = (time.perf_counter() - started) * 1000.0
                # An arm that raised may already have spent its whole budget, and
                # reporting 0 renders for it understates what the failure cost. The
                # error carries the count when the raiser knows it.
                outcome.renders = getattr(e, "renders_spent", 0)
                outcomes.append(outcome)
                continue
            # Deduped: fifty targets produce fifty copies of the same sentence about
            # the budget, and a caveat block nobody can read is a caveat block nobody
            # reads. Prefixed with the arm, because "the optimiser never ran" is a fact
            # about `full` and would otherwise look like a fact about the benchmark.
            for text in arm_caveats:
                caveats.append(f"{arm}: {text}")
            scoring_renders = own_scorer.renders
            scored = scorer_score(own_scorer, target, found,
                                  reference_audio=rendered.audio)
            outcome.renders = renders + (own_scorer.renders - scoring_renders)
            outcome.wall_ms = (time.perf_counter() - started) * 1000.0
            if scored is None:
                outcome.failed = True
                outcome.error = "the recovered vector produced nothing comparable"
            else:
                outcome.objective = scored
                active = {dimension.path for dimension in space.active(truth)}
                mae, accuracy = parameter_error(
                    space, truth, found,
                    only=[
                        d.path for d in space.dimensions
                        if d.path in active
                        and (supported is None or d.path in supported)
                    ])
                outcome.parameter_mae = mae
                outcome.selector_accuracy = accuracy
            outcomes.append(outcome)
        return outcomes, caveats

    def collect(index, outcomes, caveats):
        """Fold one target's results in, deduping caveats as the loop used to.

        Fifty targets produce fifty copies of the same sentence about the budget,
        and a caveat block nobody can read is a caveat block nobody reads.
        """
        result.outcomes.extend(outcomes)
        for text in caveats:
            if text not in result.caveats:
                result.caveats.append(text)

    if workers > 1 and renderer_factory is not None:
        # One instance per worker thread, held for that thread's whole life. The
        # property §12j requires is that every comparison a target makes stays
        # inside one instance, and it does: a target's truth render, its arms and
        # its scoring all go through the member its thread holds. Several targets
        # sharing an instance is not a comparison spread across instances — and it
        # is what the serial path has always done with its single renderer.
        from match.pool import RendererPool

        done = {}
        lock = threading.Lock()
        finished = [0]
        completed: "queue.Queue[Optional[int]]" = queue.Queue()
        cancelled = threading.Event()
        fatal: List[BaseException] = []
        # `workers` threads pulling from a queue, not one thread per target. A
        # thread per target starts every target at once and leaves all but
        # `workers` of them blocked inside `borrow()`, which is bounded by the
        # pool's wedged-member deadline — so a long run would have had its later
        # targets time out, their threads die, and their results simply be absent
        # from a report that still said it ran `targets` of them. At the
        # documented `--targets 50 --budget 300` roughly three quarters of the run
        # would have vanished that way.
        pending: "queue.Queue[int]" = queue.Queue()
        for index in range(int(targets)):
            pending.put(index)

        def work_body():
            # One member for the thread's whole life. Different targets on one
            # instance is fine — targets compare with nothing outside themselves —
            # and it matches what the serial path does with its single renderer.
            with pool.borrow() as member:
                own_scorer = search.Evaluator(
                    member, fingerprint(
                        io.from_samples(probe_di, member.metadata().sample_rate),
                        regime="probe", excerpt_s=None),
                    probe_di, space, profile=profile, reference_audio=probe_di)
                while not cancelled.is_set():
                    try:
                        index = pending.get_nowait()
                    except queue.Empty:
                        return
                    try:
                        outcomes, caveats = one_target(index, member, own_scorer)
                    except Exception as unexpected:   # noqa: BLE001
                        # A target that dies outside the arm loop — its truth
                        # render, or building its evaluator — used to take its
                        # thread with it and leave no trace but a shorter table.
                        # It is a failed target now, and it says so.
                        outcomes = [Outcome(arm=arm, target_index=index, failed=True,
                                            error=f"{type(unexpected).__name__}: "
                                                  f"{unexpected}")
                                    for arm in arms]
                        caveats = [
                            f"target {index} failed outside its arms: "
                            f"{type(unexpected).__name__}: {unexpected}"
                        ]
                    with lock:
                        done[index] = (outcomes, caveats)
                        finished[0] += 1
                    completed.put(index)

        def work():
            try:
                work_body()
            except BaseException as unexpected:      # noqa: BLE001 — re-raised below
                # Includes control exceptions, borrowing a member, and building
                # the per-worker evaluator. A child thread cannot propagate any
                # of those to its joining thread by raising alone.
                with lock:
                    fatal.append(unexpected)
                cancelled.set()
                completed.put(None)

        pool_width = min(int(workers), int(targets))
        if pool_width == 0:
            return result
        with RendererPool(renderer_factory, workers=pool_width) as pool:
            threads = [threading.Thread(target=work, daemon=True)
                       for _ in range(pool_width)]
            for thread in threads:
                thread.start()
            progress_error = None
            reported = 0
            while any(thread.is_alive() for thread in threads) or not completed.empty():
                try:
                    item = completed.get(timeout=0.1)
                except queue.Empty:
                    continue
                if item is None:
                    continue
                reported += 1
                if progress is not None and progress_error is None:
                    try:
                        # User code belongs on the calling thread. Running this
                        # in a worker swallowed its exception while the benchmark
                        # returned a clean result.
                        progress(reported, int(targets))
                    except BaseException as error:  # noqa: BLE001 — re-raised below
                        progress_error = error
                        cancelled.set()
            for thread in threads:
                thread.join()
        if progress_error is not None:
            raise progress_error
        if fatal:
            raise fatal[0]
        missing = [index for index in range(int(targets)) if index not in done]
        if missing:
            # Never silently. A benchmark that reports on a subset it did not
            # choose is worse than one that fails.
            raise BenchmarkError(
                f"{len(missing)} of {targets} targets produced no result at all "
                f"(indices {missing[:5]}{'…' if len(missing) > 5 else ''}). This is "
                f"a bug in the concurrent path, not a property of the run."
            )
        # Index order, not completion order: a benchmark whose rows depended on
        # which target finished first would not be the same experiment twice.
        for index in sorted(done):
            collect(index, *done[index])
        return result

    for index in range(int(targets)):
        collect(index, *one_target(index, renderer, scorer))
        if progress is not None:
            progress(index + 1, int(targets))
    return result


def _spawn_streams(rng, count: int, np):
    """Independent target streams supported by NumPy 1.24.

    ``Generator.spawn`` arrived in NumPy 1.25 while this project permits 1.24.
    ``SeedSequence.spawn`` predates that minimum. One seed sequence is drawn from
    the caller's generator, then target-indexed children are derived from it.
    """
    words = rng.integers(0, 2 ** 32, size=4, dtype=np.uint32)
    return [np.random.default_rng(child)
            for child in np.random.SeedSequence(words).spawn(int(count))]


def scorer_score(scorer, target, values: Mapping,
                 reference_audio=None) -> Optional[float]:
    """One vector's weighted distance to a target, through the shared evaluator.

    Updating the reference is the sharp edge here and the reason this is a named
    function rather than three inline lines: the evaluator is shared across every arm
    and every target, so a caller that forgets either the fingerprint or, for a paired
    profile, its waveform scores against the previous one. `set_reference` updates the
    pair together. That is the same class of hidden state as the "a quieter DI looked
    like a better match" bug §12c records, and the reason it has not bitten is that
    there is exactly one caller.
    """
    scorer.set_reference(target, reference_audio)
    scored = scorer.evaluate(values)
    return scored.total if scored.objectives else None


def _run_arm(arm: str, renderer, target, probe_di, space, seed, budget, profile,
             invert, search, rng, pack_id: str, amp: Optional[str],
             switches: Optional[Sequence[str]] = None,
             selectors: Optional[Sequence[str]] = None,
             reference_audio=None):
    """One arm's answer for one target, and how many renders it took.

    The three arms are **nested**, which is what makes the comparison mean anything:
    `inversion` is `recipe` plus the calculated step, and `full` is `inversion` plus
    the search. The first version of this searched from the recipe seed instead of
    the inverted one, so the `full` arm was search-*only* — and it scored 1.401
    against inversion's 1.021, reporting DOES NOT SHIP for a mistake in the harness
    rather than in the pipeline. A benchmark whose arms are not nested does not
    measure what each stage adds.

    The render counts are not comparable by design, and the table says so: this
    helper returns zero for `recipe`, one for inversion's delta, and the search
    budget for `full`; `compare_baselines` then adds the final render that scores
    each answer. The question is what the extra renders buy, so every cost has to
    travel with the answer.
    """
    if arm == "recipe":
        return dict(seed), 0, []

    inverted, spent = _invert_from(renderer, target, probe_di, space, seed, profile,
                                   invert, search, pack_id, amp,
                                   reference_audio=reference_audio)
    if arm == "inversion":
        return inverted, spent, []

    outcome = search.search(renderer, target, probe_di, space, inverted,
                            budget=budget, profile=profile, shortlist=1,
                            switches=switches, selectors=selectors, rng=rng,
                            reference_audio=reference_audio)
    if not outcome.shortlist:
        failure = BenchmarkError(
            f"the search returned no candidate after {outcome.renders} renders: "
            f"every trial failed or came back silent"
        )
        # So the reported cost is what the failure actually cost.
        failure.renders_spent = outcome.renders + spent
        raise failure
    # The search's caveats travel with the answer. Dropped, `--budget 60` ran zero
    # optimiser generations across every target and the table still printed
    # "SHIPS / beats inversion: 0.997 against 1.203" with nothing said — and `--budget`
    # is the one knob a maintainer turns to make this fast. `BenchmarkResult.caveats`
    # already existed and `format_table` already prints it.
    return outcome.shortlist[0].values, outcome.renders + spent, outcome.caveats


def _invert_from(renderer, target, probe_di, space, seed, profile, invert, search,
                 pack_id: str, amp: Optional[str], reference_audio=None):
    """The seed with everything calculable calculated, and the one render it cost."""
    from analysis import io
    from analysis.fingerprint import fingerprint

    if amp is None:
        raise BenchmarkError(
            "the inversion step needs to know which amp is selected; pass amp= or a "
            "seed with a selectedAmp value"
        )
    evaluator = search.Evaluator(renderer, target, probe_di, space, profile=profile,
                                 recipe=seed, reference_audio=reference_audio)
    rendered = renderer.render(probe_di, evaluator._settings(seed))
    printed = fingerprint(io.from_samples(rendered.audio,
                                          rendered.metadata.sample_rate),
                          regime="probe", excerpt_s=None)
    calculated = invert.invert(target, printed, amp=amp, pack_id=pack_id,
                               renderer=renderer, current_settings=seed)
    return invert.apply_to(seed, calculated.as_settings(), space), 1


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
    columns = [("arm", 10), ("targets", 8), ("fail%", 7), ("param MAE", 13),
               ("selector", 13), ("objective", 13), ("median", 13), ("renders", 8),
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
    lines.append("")
    lines.append("param MAE is the mean absolute error over the continuous controls, "
                 "as a fraction of")
    lines.append("each one's own range; selector is the share of switches and "
                 "selectors got right.")

    # The errors, which were recorded and never printed: `--amp nope` produced three
    # arms of "not measured" and a verdict blaming the wrong one, while the actual
    # cause — "'nope' is not an amp in pack 'morgan'" — sat in the store, reachable
    # only through --json.
    failures = {}
    for outcome in result.outcomes:
        if outcome.error:
            failures.setdefault(outcome.error, []).append(outcome.arm)
    if failures:
        lines.append("")
        lines.append("failures:")
        for error, arms in sorted(failures.items()):
            where = ", ".join(sorted(set(arms)))
            lines.append(f"  {where}: {error}")

    ships, reasons = result.verdict()
    lines.append("")
    lines.append("SHIPS" if ships else "DOES NOT SHIP")
    lines.extend(f"  - {reason}" for reason in reasons)
    if result.caveats:
        lines.append("")
        lines.extend(f"  ! {caveat}" for caveat in result.caveats)
    return "\n".join(lines)
