"""Does the signal a search renders through change where it ends?

`match_preset.py` renders every candidate through a DI: the user's own when they
have one, and the synthetic noise-burst probe when they do not. The benchmark in
`match.benchmark` renders its targets and its candidates through one signal, so it
cannot ask what that choice costs. Here every target is rendered from one played
passage — standing in for the reference recording — and the same pipeline
(neutral settings → inversion → search) runs once per search signal, with the same
budget and the same random numbers. Every answer is then scored by rendering it
from the target's own passage, which is what the user hears when they play the
part through the preset.

The topology is fixed: a template's switches and selectors, put back after the
inversion in every arm, so the arms differ only in the continuous values their
searches found. The targets are fingerprinted as `isolated_stem`, as a recording
would be, so no inversion rule treats them as sharing a DI with any search.

Each target also records, in the same instance, what the pipeline gives without
its search: the neutral start, and each signal's inversion alone — the vector
that signal's search starts from. Those are the baselines a search has to beat,
and scoring them beside it means no comparison has to pair two processes' renders
of the same settings.
"""

from __future__ import annotations

import copy
import queue
import statistics
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from match.space import Space


class SignalBenchmarkError(ValueError):
    """A search-signal benchmark that cannot be set up."""


@dataclass
class SignalOutcome:
    """One search signal's attempt at one target."""

    signal: str
    target_index: int
    position: int
    # The answer rendered from the target's own signal: what the user hears.
    objective: Optional[float] = None
    objective_spread: Optional[float] = None
    # The search's own best score, measured through the signal it searched with.
    # Beside `objective` it shows how far that signal misled it.
    search_belief: Optional[float] = None
    parameter_mae: Optional[float] = None
    # Without the search, heard the same way as `objective`: this signal's
    # inversion alone, and the neutral start — one score per target, repeated on
    # each of its outcomes so every row can be paired on its own.
    inversion_objective: Optional[float] = None
    neutral_objective: Optional[float] = None
    inversion_spread: Optional[float] = None
    neutral_spread: Optional[float] = None
    # Each of those three scores by dimension (timbre, dynamics, ambience, ...),
    # each dimension averaged over the observations that measured it: which part
    # of the loss a distance came from.
    objective_dimensions: Optional[Dict[str, float]] = None
    inversion_dimensions: Optional[Dict[str, float]] = None
    neutral_dimensions: Optional[Dict[str, float]] = None
    # With `level_trim`: the output-gain change applied to the answer after its
    # search (None when none was), and the answer as it was before, heard the same
    # way as `objective` — so the trim is paired with its own untrimmed answer.
    level_trim_db: Optional[float] = None
    # What `level_trim` recorded for this answer, applied or not, without the vector.
    level_trim_record: Optional[Dict[str, Any]] = None
    untrimmed_objective: Optional[float] = None
    untrimmed_dimensions: Optional[Dict[str, float]] = None
    # This arm's own renders: its inversion, scoring that inversion, its search
    # and scoring its answer. The neutral start's are shared by every arm of a
    # target and counted in none.
    renders: int = 0
    failed: bool = False
    error: Optional[str] = None


def fixed_topology(space: Space, amp: str, template_values: Optional[Mapping],
                   supported) -> Dict[str, Any]:
    """The template's topology as `(dimensions, seed, discrete)` pieces.

    Returns a dict with the sampled continuous `dimensions`, the neutral `seed`
    (every sampled control centred, in the benchmark's key spelling) and the
    `discrete` positions — switches and selectors — held after every inversion.
    """
    from match import atlas, benchmark, invert

    if template_values is None:
        template_values = atlas.fixed_topology_seed(space, amp)
    fixed = atlas.tone_topology(template_values, space, amp)
    paths = {atlas._path(key): value for key, value in fixed.items()}
    dimensions = atlas.sampling_dimensions(space, fixed, supported)
    if not dimensions:
        raise SignalBenchmarkError(
            f"the {amp} topology has no continuous control this renderer can drive")
    base = invert.apply_to(benchmark.centre_seed(space),
                           invert.signal_path_selection(space.pack_id, amp), space)
    seed = invert.apply_to(base, atlas.neutral_settings(paths, dimensions), space)
    discrete = {dimension.path for dimension in space.dimensions
                if not dimension.continuous}
    return {
        "dimensions": dimensions,
        "seed": seed,
        "discrete": {path: value for path, value in paths.items() if path in discrete},
    }


def compare_search_signals(renderer, space: Space, target_di, signals: Mapping,
                           topology: Mapping, targets: int = 12, budget: int = 300,
                           profile: str = "unpaired-v1", rng=None,
                           pack_id: str = "morgan", amp: Optional[str] = None,
                           progress=None, workers: int = 1,
                           renderer_factory=None,
                           run_search: bool = True,
                           level_trim: bool = False) -> List[SignalOutcome]:
    """Run the pipeline once per search signal on every target.

    `signals` maps a name to the samples a search renders its candidates through.
    `topology` is `fixed_topology(...)`. Each target is scored in the instance
    that rendered it, and every arm's final score renders its answer from
    `target_di` — never from the signal it searched with. With `run_search`
    false only the baselines are scored: minutes, where the searches take hours.
    """
    from analysis import io, require

    require("running the search-signal benchmark")
    import numpy as np

    from analysis.fingerprint import fingerprint
    from match import benchmark, invert, search

    if not signals:
        raise SignalBenchmarkError("at least one search signal is required")
    if amp is None:
        raise SignalBenchmarkError("the inversion needs to know which amp is selected")
    workers = int(workers)
    if workers < 1:
        raise SignalBenchmarkError(f"workers must be at least 1, not {workers}")
    if workers > 1 and renderer_factory is None:
        raise SignalBenchmarkError(
            f"workers={workers} needs renderer_factory, one instance per worker")
    rng = np.random.default_rng(11) if rng is None else rng
    streams = benchmark._spawn_streams(rng, int(targets), np)
    names = list(signals)
    dimensions = topology["dimensions"]
    seed = topology["seed"]
    discrete = topology["discrete"]
    sampled = [dimension.path for dimension in dimensions]
    output_control = invert.output_gain_control(pack_id, amp) if level_trim else None

    def one_target(index: int, own) -> List[SignalOutcome]:
        stream = streams[index]
        truth = dict(seed)
        truth.update(benchmark.atlas_vector(dimensions, stream))
        # Every search draws from a copy of this one state, so the arms get the
        # same random numbers and differ only in the signal they render through.
        search_state = copy.deepcopy(stream)
        scorer = search.Evaluator(own, None, target_di, space, profile=profile)
        rendered = own.render(target_di, scorer._settings(truth))
        if rendered.silent:
            return [SignalOutcome(signal=name, target_index=index, position=-1,
                                  failed=True, error="the target rendered silent")
                    for name in names]
        target = fingerprint(io.from_samples(rendered.audio,
                                             rendered.metadata.sample_rate),
                             regime="isolated_stem", excerpt_s=None)
        observations = search.shortlist_replicates(own.metadata())

        def heard(values):
            """Mean total, mean per dimension and spread, or Nones."""
            scored = benchmark.scorer_candidates(scorer, target, values,
                                                 observations=observations)
            if not scored:
                return None, None, None
            totals = [candidate.total for candidate in scored]
            measured = {term for candidate in scored for term in candidate.objectives
                        if term != "total"}
            per_dimension = {term: statistics.fmean(
                candidate.objectives[term] for candidate in scored
                if term in candidate.objectives) for term in sorted(measured)}
            spread = max(totals) - min(totals) if len(totals) > 1 else None
            return statistics.fmean(totals), per_dimension, spread

        # Shared by every arm, so its renders are counted in none of them.
        neutral, neutral_dimensions, neutral_spread = heard(seed)
        rotation = index % len(names)
        order = names[rotation:] + names[:rotation]
        outcomes = []
        for position, name in enumerate(order):
            outcome = SignalOutcome(signal=name, target_index=index,
                                    position=position, neutral_objective=neutral,
                                    neutral_spread=neutral_spread,
                                    neutral_dimensions=neutral_dimensions)
            try:
                inverted, spent = benchmark._invert_from(
                    own, target, signals[name], space, seed, profile, invert,
                    search, pack_id, amp)
                inverted = invert.apply_to(inverted, discrete, space)
                before = scorer.renders
                (outcome.inversion_objective, outcome.inversion_dimensions,
                 outcome.inversion_spread) = heard(inverted)
                spent += scorer.renders - before
                if not run_search:
                    outcome.renders = spent
                    if outcome.inversion_objective is None or neutral is None:
                        outcome.failed = True
                        outcome.error = "a baseline produced no comparable objective"
                    outcomes.append(outcome)
                    continue
                found = search.search(own, target, signals[name], space, inverted,
                                      budget=budget, profile=profile, shortlist=1,
                                      rng=copy.deepcopy(search_state),
                                      output_control=output_control)
                if not found.shortlist:
                    raise SignalBenchmarkError(
                        f"the search returned no candidate after {found.renders} "
                        f"renders")
                best = found.shortlist[0]
                before = scorer.renders
                # One shortlisted candidate, so at most one trim, and it is this one.
                if found.level_trims:
                    outcome.level_trim_record = {
                        key: value for key, value in found.level_trims[0].items()
                        if key != "values_before"}
                trim = next((record for record in found.level_trims
                             if record.get("applied")), None)
                if trim is not None:
                    outcome.level_trim_db = trim["after"] - trim["before"]
                    (outcome.untrimmed_objective, outcome.untrimmed_dimensions,
                     _) = heard(trim["values_before"])
                (outcome.objective, outcome.objective_dimensions,
                 outcome.objective_spread) = heard(best.values)
                outcome.renders = spent + found.renders + (scorer.renders - before)
                outcome.search_belief = best.total
                if outcome.objective is None:
                    outcome.failed = True
                    outcome.error = "the answer produced no comparable objective"
                outcome.parameter_mae, _ = benchmark.parameter_error(
                    space, truth, best.values, only=sampled)
            except (ValueError, RuntimeError) as error:
                outcome.failed = True
                outcome.error = f"{type(error).__name__}: {error}"
            outcomes.append(outcome)
        return outcomes

    results: Dict[int, List[SignalOutcome]] = {}
    if workers == 1:
        for index in range(int(targets)):
            results[index] = one_target(index, renderer)
            if progress is not None:
                progress(index + 1, int(targets))
    else:
        pending: "queue.Queue[int]" = queue.Queue()
        for index in range(int(targets)):
            pending.put(index)
        lock = threading.Lock()
        failures: List[BaseException] = []
        stop = threading.Event()
        members = [renderer]
        try:
            for _ in range(workers - 1):
                members.append(renderer_factory())
        except BaseException:
            _close(members[1:])
            raise

        def work(member):
            try:
                while not stop.is_set():
                    try:
                        index = pending.get_nowait()
                    except queue.Empty:
                        return
                    done = one_target(index, member)
                    with lock:
                        results[index] = done
                        if progress is not None:
                            progress(len(results), int(targets))
            except BaseException as error:   # noqa: BLE001 — re-raised below
                # One failed target ends the run; the others stop taking new ones
                # rather than rendering for an hour into a result that is dropped.
                stop.set()
                with lock:
                    failures.append(error)

        threads = [threading.Thread(target=work, args=(member,), daemon=True)
                   for member in members]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        _close(members[1:])
        if failures:
            raise failures[0]
    return [outcome for index in sorted(results) for outcome in results[index]]


def summarise(outcomes: Sequence[SignalOutcome], reference: str) -> Dict[str, Any]:
    """Per-signal means, and each signal's answers paired by target.

    Every signal but `reference` is paired against it (the flat
    `closer_than_reference` keys). Every signal's answers are also paired against
    the same target's neutral start and against that signal's own inversion alone
    (`against_neutral`, `against_inversion`): did the search beat what the
    pipeline gives without it? Those pairs are within one instance's renders.
    """
    by = {}
    for outcome in outcomes:
        by.setdefault(outcome.signal, {})[outcome.target_index] = outcome
    summary: Dict[str, Any] = {}
    for name, rows in by.items():
        good = [row for row in rows.values() if not row.failed]
        entry = {
            "targets": len(rows),
            "failures": len(rows) - len(good),
            "objective_mean": _mean(row.objective for row in good),
            "objective_median": _median(row.objective for row in good),
            "search_belief_mean": _mean(row.search_belief for row in good),
            "parameter_mae": _mean(row.parameter_mae for row in good),
            # A baseline is measured before the search, so a row whose search
            # failed still has one; a row whose baseline failed still has an
            # answer, and is counted here rather than failed.
            "inversion_objective_mean": _mean(
                row.inversion_objective for row in rows.values()),
            "inversion_objective_median": _median(
                row.inversion_objective for row in rows.values()),
            "neutral_objective_mean": _mean(
                row.neutral_objective for row in rows.values()),
            "neutral_objective_median": _median(
                row.neutral_objective for row in rows.values()),
            "baseline_failures": sum(
                row.inversion_objective is None or row.neutral_objective is None
                for row in rows.values()),
            "renders": sum(row.renders for row in rows.values()),
        }
        trimmed = [row for row in good if row.level_trim_db is not None]
        if trimmed:
            entry["level_trims"] = len(trimmed)
        for key, field in (("against_neutral", "neutral_objective"),
                           ("against_inversion", "inversion_objective"),
                           ("against_untrimmed", "untrimmed_objective")):
            paired = _paired([(row.objective, getattr(row, field)) for row in good])
            if paired:
                entry[key] = paired
        if name != reference and reference in by:
            theirs = by[reference]
            paired = _paired([(rows[i].objective, theirs[i].objective) for i in rows
                              if i in theirs and not rows[i].failed
                              and not theirs[i].failed])
            if paired:
                entry["paired_against"] = reference
                entry["paired_targets"] = paired["targets"]
                entry["closer_than_reference"] = paired["closer"]
                entry["mean_change_fraction"] = paired["mean_change_fraction"]
                entry["wilcoxon_p"] = paired["wilcoxon_p"]
        summary[name] = entry
    return summary


def _paired(pairs) -> Optional[Dict[str, Any]]:
    """How often, by how much and how surely the first of each pair was closer."""
    from scipy import stats

    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if not pairs:
        return None
    mine = [a for a, _ in pairs]
    theirs = [b for _, b in pairs]
    return {
        "targets": len(pairs),
        "closer": sum(a < b for a, b in pairs),
        "mean_change_fraction": ((statistics.fmean(mine) - statistics.fmean(theirs))
                                 / statistics.fmean(theirs)),
        "wilcoxon_p": (float(stats.wilcoxon(mine, theirs).pvalue)
                       if len(pairs) > 1 and any(a != b for a, b in pairs) else None),
    }


def _close(renderers) -> None:
    for member in renderers:
        close = getattr(member, "close", None)
        if close is not None:
            close()


def _mean(values) -> Optional[float]:
    present = [float(v) for v in values if v is not None]
    return round(statistics.fmean(present), 4) if present else None


def _median(values) -> Optional[float]:
    present = [float(v) for v in values if v is not None]
    return round(statistics.median(present), 4) if present else None
