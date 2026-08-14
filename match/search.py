"""Spend a render budget on the parameters that turn out to matter.

The inversions in `match/invert.py` have already set what can be calculated. What
is left is genuinely a search: how hard the amp is driven, which cabinet and mic,
how much compression, and the interactions between them — none of which map onto a
closed-form measurement. This module spends renders on that, and the shape of it is
dictated by one fact from §2, D3: **a render is the only expensive thing here.**
Everything else — a fingerprint, a comparison, a decode — is milliseconds. So the
design question is never "how do we compute this faster", it is always "how do we
learn the most per render".

Four stages, in order, each one narrowing what the next has to consider:

1. **Screen.** Render each candidate parameter at its low and high end and see
   whether the objective moves at all. A parameter that does not move it is frozen
   for the run. Two renders each plus one baseline, once — and it pays for itself
   immediately: Morgan declares 125 searchable dimensions of which **87 are
   continuous**, and CMA-ES over 88 dimensions needs thousands of samples to do
   anything at all. (The other 38 are switches and selectors, which stage 2 owns.)
2. **Enumerate.** Amp, cab, mic and effect on/off are discrete, and interpolating
   between mic 3 and mic 4 means nothing. They are an outer loop, never a
   coordinate.
3. **Refine.** CMA-ES over what is left, seeded from the recipe stack with an
   explicit prior term, so a search that finds two equally good answers prefers
   the one closer to what a person would have dialled.
4. **Re-rank.** Re-render the shortlist at ±6 dB of input level. A preset that
   matches at one input level and falls apart at another is not a match — the
   repository's own THD measurements show how strongly breakup depends on it.

Nothing here decides *how many* renders to spend on its own: `budget` is the
caller's, and every stage reports what it used so the arithmetic is checkable.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from match.renderer import canonical_settings
from match.space import Dimension, Space
from match.store import Store, Trial

# How much of the objective's range a parameter has to move before it is worth
# searching over. Not a tolerance on the objective itself: the screen renders at a
# parameter's extremes, which is the largest effect it can have, so anything under
# this is a control that cannot matter however it is set.
#
# A *floor* on the floor. On a backend that does not repeat itself the real limit is
# whatever that backend's own variation is, and `screen` raises this to match — see
# `_backend_floor`.
SENSITIVITY_FLOOR = 0.01
# A non-reproducible backend gets five observations of the same scalar score.
# Their peak-to-peak spread is deliberately conservative; two observations can
# accidentally agree even when the process has meaningful state variation.
NONREPRODUCIBLE_SCREEN_SAMPLES = 5

# The fraction of surviving parameters to freeze anyway, weakest first. The plan
# says "freeze the bottom quantile", and the reason it is a quantile as well as a
# floor is that the floor is absolute while budget is relative: with 60 parameters
# above the floor and 300 renders there is no point pretending to search all 60.
SENSITIVITY_QUANTILE = 0.25

# CMA-ES's initial step, in normalised space. §M4 says 0.15-0.2; the lower end,
# because the seed is the recipe stack rather than a random point and a large first
# step throws that information away.
INITIAL_SIGMA = 0.15

# The prior's weight is NOT here. `prior_deviation` is a dimension of the objective
# vector, so how much it counts is a number in `analysis/loss_profiles.json` — 0.15
# under `unpaired-v1`, 0.1 under `paired-v1`. A `PRIOR_WEIGHT = 0.15` constant used to
# sit here, wired to an `Evaluator.prior_weight` attribute that was assigned and never
# read: a maintainer who changed it would have seen no effect and no error, which is
# the exact trap "no parameter that does nothing" exists to prevent.

# The input-level offsets the shortlist is re-rendered at, in dB.
ROBUSTNESS_OFFSETS_DB = (-6.0, 6.0)

# The minimum objective-space separation between two shortlist entries. Two presets
# differing by 0.005 of an objective are the same preset as far as anyone listening is
# concerned, and a shortlist of five of them wastes four listening comparisons. A
# constant rather than a `pareto()` argument, which nothing outside tests overrode:
# a parameter with one call site pretends to be tunable.
DISTINCT_OBJECTIVE = 0.02


def generation_size(parameters: int) -> int:
    """How many renders one round of CMA-ES costs, for `parameters` of them.

    Hansen's λ. Exposed because it is the *granularity of the whole search* and not
    an internal of `refine`: below one generation the optimiser cannot take a step at
    all, so a caller sizing a budget needs this number, and so does the caveat that
    tells a user what to raise `--budget` to.
    """
    return 4 + int(3 * math.log(max(1, parameters)))


class SearchError(ValueError):
    """A search that cannot be set up, or a budget that cannot be spent."""


@dataclass
class Candidate:
    """One parameter vector and what it scored."""

    values: Dict[str, Any]
    objectives: Dict[str, float] = field(default_factory=dict)
    total: float = float("inf")
    trial_id: Optional[int] = None
    # Populated by `robustness_rerank`: the same vector's score at each input level.
    by_level: Dict[float, float] = field(default_factory=dict)
    # Why this vector scored nothing, when a backend refused it outright. The
    # store has always recorded this; the candidate did not carry it, so the one
    # place that reads a failure — the screen's baseline — could only guess
    # between a silent render and an unmeasurable one, and said both.
    error: Optional[str] = None

    @property
    def worst_level(self) -> Optional[float]:
        """The worst score across the input levels this was re-rendered at.

        The number the shortlist is ordered by after re-ranking, and deliberately
        the worst rather than the mean: a preset that is excellent at one input
        level and unusable at another is not a good match that happens to vary.
        """
        return max(self.by_level.values()) if self.by_level else None

    def dominates(self, other: "Candidate", dimensions: Sequence[str],
                  tolerance: float = 1e-9) -> bool:
        """Pareto domination: no worse anywhere, and better somewhere.

        Compared per dimension rather than on the scalar, because the scalar is one
        weighting of many and the point of an archive is to keep the answers that a
        different weighting would prefer.
        """
        better_somewhere = False
        for name in dimensions:
            mine, theirs = self.objectives.get(name), other.objectives.get(name)
            if mine is None or theirs is None:
                continue      # a dimension neither side measured cannot order them
            if mine > theirs + tolerance:
                return False
            if mine < theirs - tolerance:
                better_somewhere = True
        return better_somewhere


@dataclass
class SearchResult:
    """The shortlist, and enough of the accounting to check the claim."""

    shortlist: List[Candidate] = field(default_factory=list)
    frozen: Dict[str, float] = field(default_factory=dict)
    searched: List[str] = field(default_factory=list)
    # How much each *searched* parameter moved the objective, which the screen
    # measured and then discarded on the way out: `frozen` carried its numbers and
    # `searched` was a bare list, so the report's most useful column was a dash for
    # every row that had been kept, and a reader could not check the freeze decision.
    movement: Dict[str, float] = field(default_factory=dict)
    # The floor the freeze decisions were actually made against, which is the constant
    # raised to the backend's own band noise — and which a report has to have if it is
    # to say *why* a row was frozen rather than guess from a constant.
    floor: float = SENSITIVITY_FLOOR
    floor_observations: int = 1
    # Paths where one end of the range silences the render, and the value that does it.
    # The report called these "too small to matter" while the caveat block, in the same
    # document, said they silence the signal entirely.
    silences: Dict[str, float] = field(default_factory=dict)
    renders: int = 0
    cache_hits: int = 0
    wall_ms: float = 0.0
    caveats: List[str] = field(default_factory=list)
    # The one caveat that invalidates the headline rather than qualifying it: the
    # optimiser never ran, so "0.853, 25% closer" describes the inversion and the
    # screen's own probes. Held separately so a caller can put it first — it arrived
    # ninth of eleven, below the note about palm-muted playing.
    unsearched: Optional[str] = None
    run_id: Optional[str] = None

    @property
    def best(self) -> Optional[Candidate]:
        """The recommended candidate, after the ±6 dB re-rank reordered them."""
        return self.shortlist[0] if self.shortlist else None


class Evaluator:
    """Render, fingerprint, compare, and remember — the unit of budget.

    Every stage below calls this and nothing else, which is what makes the render
    count in `SearchResult` the truth rather than an estimate: there is exactly one
    place a render can happen.
    """

    def __init__(self, renderer, target, probe_di, space: Space,
                 profile: str = "unpaired-v1",
                 store: Optional[Store] = None, run_id: Optional[str] = None,
                 recipe: Optional[Mapping] = None,
                 reference_audio=None) -> None:
        from analysis import require
        from analysis.compare import load_profile

        require("searching for a preset")
        self.renderer = renderer
        self.probe_di = probe_di
        self.space = space
        self.profile = profile
        self.store = store
        self.run_id = run_id
        self.recipe = dict(recipe or {})
        self.renders = 0
        self.cache_hits = 0
        self.wall_ms = 0.0
        self._supported = supported_keys(renderer)
        self.residual_enabled = float(
            load_profile(profile).get("weights", {}).get("residual", 0.0) or 0.0
        ) > 0.0
        self.alignment_attempts = 0
        self.untrusted_alignments = 0
        self.weakest_alignment: Optional[float] = None
        self.set_reference(target, reference_audio)

    def set_reference(self, target, reference_audio=None) -> None:
        """Set both halves of the reference used by a score.

        A fingerprint is sufficient for every statistical objective. A profile
        that weights ``residual`` also needs the waveform the fingerprint
        deliberately discarded. Keeping the two together prevents the benchmark's
        shared evaluator from updating one target and accidentally subtracting the
        previous target's audio.
        """
        self.target = target
        self.reference_audio = reference_audio
        self.reference_audio_sha = (
            None if not self.residual_enabled or reference_audio is None
            else _hash(reference_audio)
        )
        if self.residual_enabled and reference_audio is None:
            raise SearchError(
                f"loss profile {self.profile!r} weights waveform residual, but no "
                "reference samples were supplied. Pass the reamped recording's "
                "samples as reference_audio; a fingerprint alone cannot measure it."
            )

    # --- the one expensive call ---------------------------------------------

    def evaluate(self, values: Mapping, di=None,
                 offset_db: float = 0.0, use_cache: bool = True) -> Candidate:
        """Score one parameter vector. Counts against the budget unless cached.

        `di` and `offset_db` travel together and both are recorded: a trial is
        "these parameters through this signal", so the same vector at a different
        input level is a different trial. Storing the offset is what stops
        `Store.best` from picking a candidate that only looked good because the DI
        was quieter.
        """
        from analysis import io
        from analysis.compare import compare, scalar
        from analysis.fingerprint import fingerprint
        from match.renderer import RenderError, cache_key

        settings = self._settings(values)
        signal = self.probe_di if di is None else di
        metadata = self.renderer.metadata()
        di_sha = _hash(signal)
        key = cache_key(metadata, di_sha, settings)
        # What is being cached is a *score*, and a score is not addressed by the
        # render alone: it also depends on the reference, on how the objective is
        # weighted, and on the seed the prior terms measure from. Keyed on the render
        # address alone, a second run in the same directory was served the first
        # run's objectives against a different recording — no error, no trial row,
        # and a report whose headline scored a match against somebody else's audio.
        scoring_key = _scoring_key(
            key, self.target, self.profile, self.recipe, self.reference_audio_sha)

        # A cached score is valid only when the backend is a function of its inputs.
        # Reused Audio Unit instances explicitly are not: reading an earlier score
        # would mix one plugin instance's endpoint with another instance's baseline.
        if use_cache and metadata.reproducible and self.store is not None:
            hit = self.store.cached(scoring_key)
            if hit is not None:
                self.cache_hits += 1
                return Candidate(values=dict(values),
                                 objectives=dict(hit.objectives or {}),
                                 total=float((hit.objectives or {}).get(
                                     "total", float("inf"))),
                                 trial_id=hit.trial_id)

        started = time.perf_counter()
        error = None
        rendered = None
        try:
            rendered = self.renderer.render(signal, settings, di_sha256=di_sha)
        except (RenderError, ValueError) as e:
            # A backend that cannot render one vector has not invalidated the run.
            # The trial is stored with its error so the failure rate is earned.
            error = f"{type(e).__name__}: {e}"
        elapsed = (time.perf_counter() - started) * 1000.0
        self.renders += 1
        self.wall_ms += elapsed

        objectives: Optional[Dict[str, float]] = None
        printed = None
        if rendered is not None and not rendered.silent:
            printed = fingerprint(io.from_samples(rendered.audio, metadata.sample_rate),
                                  regime="probe", excerpt_s=None)
            waveform_residual = None
            if self.residual_enabled:
                from analysis.align import align, residual_db

                reference, candidate, alignment = align(
                    self.reference_audio, rendered.audio, metadata.sample_rate)
                self.alignment_attempts += 1
                correlation = abs(float(alignment.correlation))
                self.weakest_alignment = (
                    correlation if self.weakest_alignment is None
                    else min(self.weakest_alignment, correlation)
                )
                if not alignment.trustworthy:
                    # ``align`` deliberately returns the unshifted signals here.
                    # The resulting residual is conservative about an unknown
                    # timing relationship instead of inventing one from noise.
                    self.untrusted_alignments += 1
                waveform_residual = residual_db(reference, candidate)
                if waveform_residual is None:
                    error = (
                        "paired waveform residual is not measurable: the aligned "
                        "reference has no usable mono energy"
                    )
            vector = compare(
                self.target, printed, profile=self.profile,
                prior_deviation=self._prior_deviation(values),
                complexity=self._complexity(values),
                residual_db=waveform_residual,
            )
            objectives = {name: float(value) for name, value in vector.values.items()
                          if value is not None}
            total = scalar(vector)
            if error is not None or total is None:
                # A required waveform term failed, or nothing the profile weights
                # was measurable on both sides. Either way there is no ordering to
                # be had; it must not become a zero or a silently renormalised score.
                objectives = None
            else:
                objectives["total"] = float(total)

        trial_id = None
        if self.store is not None and self.run_id is not None:
            trial = self.store.add_trial(self.run_id, Trial(
                params=dict(settings),
                cache_key=key,
                objective_key=scoring_key,
                di_sha=di_sha,
                di_offset_db=float(offset_db),
                render_sha=None if rendered is None else _hash(rendered.audio),
                peak=None if rendered is None else rendered.peak,
                silent=None if rendered is None else rendered.silent,
                wall_ms=round(elapsed, 2),
                objectives=objectives,
                fingerprint=None if printed is None else printed.to_dict(),
                error=error,
            ))
            trial_id = trial.trial_id

        return Candidate(values=dict(values), objectives=objectives or {},
                         total=float((objectives or {}).get("total", float("inf"))),
                         trial_id=trial_id, error=error)

    # --- what the renderer is actually given --------------------------------

    def _settings(self, values: Mapping) -> Dict[str, Any]:
        """The live dimensions this backend models, keyed the way it wants them.

        Filtered twice, and both filters matter. `Space.active()` drops what the
        current switch positions make unreachable, so a render is never charged for
        moving a control inside a bypassed section. `_supported` drops what the
        backend does not model at all: the synthetic chain covers 45 of Morgan's
        132 and *refuses* anything else, which is correct of it and would otherwise
        turn every trial into an error.
        """
        settings: Dict[str, Any] = {}
        for dimension in self.space.active(values):
            value = _get(values, dimension)
            if value is None:
                continue
            if self._supported is not None and dimension.path not in self._supported:
                continue
            settings[dimension.path] = value
        return settings

    # --- the two terms that are not properties of two recordings ------------

    def _prior_deviation(self, values: Mapping) -> Optional[float]:
        """RMS distance from the recipe seed, in normalised units.

        None without a seed, which is the honest answer: with nothing to deviate
        from there is no deviation, and reporting 0.0 would tell the objective that
        every candidate is exactly what a person would have dialled.
        """
        if not self.recipe:
            return None
        from match.space import _to_unit

        squares = []
        for dimension in self.space.dimensions:
            seed = _get(self.recipe, dimension)
            current = _get(values, dimension)
            if seed is None or current is None:
                continue
            squares.append((_to_unit(dimension, current)
                            - _to_unit(dimension, seed)) ** 2)
        if not squares:
            return None
        return math.sqrt(sum(squares) / len(squares))

    def _complexity(self, values: Mapping) -> Optional[float]:
        """How many controls this moved away from the seed, as a fraction.

        So the shortlist can prefer the simpler of two equals. Also None without a
        seed: "moved from nothing" is not a count.
        """
        if not self.recipe:
            return None
        from match.space import _to_unit

        moved = considered = 0
        for dimension in self.space.dimensions:
            seed = _get(self.recipe, dimension)
            current = _get(values, dimension)
            if seed is None or current is None:
                continue
            considered += 1
            if abs(_to_unit(dimension, current) - _to_unit(dimension, seed)) > 1e-6:
                moved += 1
        return (moved / considered) if considered else None


# --- stage 1: the sensitivity screen ----------------------------------------


@dataclass
class Screen:
    """What the sensitivity screen decided, and what it decided it on.

    A tuple of five before, which is why the sixth value — the floor the screen
    *actually used* — had nowhere to go. `screen` raises the floor to the backend's own
    band noise (`_backend_floor`), then threw that number away, so both readers
    classified against the `SENSITIVITY_FLOOR` constant instead. With a backend
    declaring 0.23 dB of band noise the effective floor is 0.0767, and a parameter cut
    by it at 0.0208 was reported as "the weakest 25% that did move it — a larger budget
    would search them". No budget will search it; the floor is not a budget.
    """

    searched: List[str] = field(default_factory=list)
    frozen: Dict[str, float] = field(default_factory=dict)
    probes: List["Candidate"] = field(default_factory=list)
    movement: Dict[str, float] = field(default_factory=dict)
    silences: Dict[str, float] = field(default_factory=dict)
    floor: float = SENSITIVITY_FLOOR
    repeat_failures: int = 0
    repeat_observations: int = 1


def screen(evaluator: Evaluator, seed: Mapping,
           floor: float = SENSITIVITY_FLOOR,
           quantile: float = SENSITIVITY_QUANTILE,
           only: Optional[Sequence[str]] = None) -> Screen:
    """Which parameters move the objective, and by how much.

    Two renders per parameter — its low end and its high end, everything else at the
    seed — so the cost is known before it is spent: 2 × the number of candidates,
    once. Returns a `Screen`: the paths worth searching, the ones frozen with the
    movement that decided each, **every probe it scored**, the movement of every
    parameter — searched or frozen — so a report can show the decision rather than
    assert it, and the floor those decisions were actually made against.

    The probes matter. They are renders that were paid for and compared, and a
    parameter at an extreme is a legitimate parameter vector: measured on a target
    differing in volume, treble and bass, one screen probe scored 0.525 while the
    whole CMA-ES stage found nothing better than 0.694. Discarding them was throwing
    away a fifth of the budget and, on that run, the best answer in it.

    The extremes are the right probe *because* they are extreme. This measures the
    largest effect a control can have on this material; a parameter that cannot
    move the objective from one end of its range to the other cannot matter at any
    setting in between, whatever the interactions.

    Two things it deliberately does not do. It does not screen switches: turning an
    effect off changes what is reachable rather than shifting a value, so the
    topology loop owns them. And it does not screen a parameter the backend cannot
    be driven with, because that render measures the backend's silence rather than
    the control.
    """
    floor = float(floor)
    candidates = [d for d in evaluator.space.active(seed)
                  if not d.switch and d.kind != "enum"
                  and (evaluator._supported is None
                       or d.path in evaluator._supported)]
    if only is not None:
        wanted = set(only)
        candidates = [d for d in candidates if d.path in wanted]
    if not candidates:
        raise SearchError(
            "nothing to screen: no continuous dimension of this space is both live "
            "under the seed values and supported by this backend.\n"
            "  Check that the seed switches the effects on, and that the renderer's "
            "parameter_specs() covers the pack's parameters."
        )

    probes: List[Candidate] = []
    silences: Dict[str, float] = {}
    reproducible = bool(evaluator.renderer.metadata().reproducible)
    # A reused plugin instance is not a function of its inputs. Several actual seed
    # renders measure the scalar objective's own peak-to-peak spread; a cached score
    # from an earlier process cannot answer that question. Reproducible backends keep
    # the old one-render path.
    baseline = evaluator.evaluate(seed, use_cache=reproducible)
    probes.append(baseline)
    if not baseline.objectives:
        why = (f"the backend refused it — {baseline.error}" if baseline.error
               else "a silent render, or no dimension the loss profile weights")
        raise SearchError(
            f"the seed vector produced nothing to compare against: {why}.\n"
            f"  Every movement below is measured against this, so the screen cannot "
            f"proceed without it."
        )
    repeats = [baseline]
    if not reproducible:
        repeats.extend(
            evaluator.evaluate(seed, use_cache=False)
            for _ in range(NONREPRODUCIBLE_SCREEN_SAMPLES - 1)
        )
    repeat_failures = sum(not candidate.objectives for candidate in repeats)
    floor = max(floor, _backend_floor(
        evaluator, repeats, expected=NONREPRODUCIBLE_SCREEN_SAMPLES,
    ))

    movement: Dict[str, float] = {}
    for dimension in candidates:
        low, high = dimension.bounds()
        scores = []
        silenced = []
        for value in (low, high):
            probe = dict(seed)
            probe[(dimension.module, dimension.key)] = dimension.quantise(value)
            scored = evaluator.evaluate(probe)
            probes.append(scored)
            if scored.objectives:
                scores.append(scored.total)
            else:
                silenced.append(value)
        if len(scores) == 1 and silenced:
            # One end silenced the render and the other did not, which is a *measured*
            # fact about the control rather than a failure to measure it: a noise gate
            # at its threshold mutes the signal, by design. Treated as "unknown" this
            # produced the same caveat on every run of the tool, two renders spent on
            # a structural certainty — and the caveat block is where the real warnings
            # are, so padding it teaches people to skip it.
            #
            # The movement is the end that *did* render, measured against the baseline.
            # This line said `= 0.0`, and a report then printed `0.0000` under "distance
            # moved" for a control that had moved it by 0.0413 — four times the floor.
            # Measured on Morgan: `parameters/gateThreshold`'s live end scored 0.8438
            # against a baseline of 0.8025. A fabricated measurement, about the one
            # control the caveat block calls the commonest way a preset sounds broken.
            #
            # It stays frozen, and that is now said in `silences` rather than implied by
            # a zero that no floor could clear. The screen's premise is that the extremes
            # bound the largest effect a control can have; when one extreme cannot be
            # scored at all there is no such bound, so handing the control to an
            # optimiser means handing it a region where half the renders come back
            # silent. Frozen on the honest ground that it could not be screened, with
            # its real movement on the record.
            movement[dimension.path] = abs(scores[0] - baseline.total)
            silences[dimension.path] = float(silenced[0])
            continue
        # A parameter whose extremes both failed to render is *unknown*, not inert.
        # Freezing it is still the right call — nothing was learned about it — but
        # the movement is recorded as NaN so a report does not claim it was measured.
        movement[dimension.path] = (max(scores) - min(scores) if len(scores) == 2
                                    else float("nan"))

    # A path where one extreme silenced the render is out of the search regardless of
    # what its live end measured — see the comment above. Excluded here, explicitly,
    # rather than by recording a movement of zero and relying on the floor to do it.
    measured = {path: value for path, value in movement.items()
                if not _isnan(value) and path not in silences}
    above = {path: value for path, value in measured.items() if value >= floor}
    # Then the quantile, weakest first, over what cleared the floor.
    ordered = sorted(above, key=lambda path: above[path])
    cut = int(len(ordered) * float(quantile))
    searched = ordered[cut:]
    frozen = {path: value for path, value in movement.items()
              if path not in set(searched)}
    # Strongest first, which is the order a caller wants to read and the order
    # CMA-ES benefits from when its budget runs out mid-population.
    searched.sort(key=lambda path: above[path], reverse=True)
    return Screen(searched=searched, frozen=frozen, probes=probes,
                  movement=movement, silences=silences, floor=floor,
                  repeat_failures=repeat_failures,
                  repeat_observations=len(repeats))


# --- stage 2: topology ------------------------------------------------------


def topologies(space: Space, seed: Mapping,
               switches: Optional[Sequence[str]] = None,
               selectors: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    """The discrete choices, as whole vectors to try rather than coordinates.

    Amp, cab, mic and effect on/off are enumerated because interpolating between
    mic 3 and mic 4 means nothing — the numbers are labels, and a gradient over
    labels is a gradient over the order somebody happened to list them in.

    Exhaustive over the *given* switches and selectors, and the caller is expected
    to give few: this is a product, so five two-state switches is 32 topologies and
    each one costs a whole inner search. Passing nothing returns the seed alone,
    which is the honest default — guessing which of Morgan's 32 switches are worth
    enumerating is not something this can know.
    """
    variants: List[Dict[str, Any]] = [dict(seed)]
    for path in switches or ():
        dimension = _dimension(space, path)
        if not dimension.switch:
            raise SearchError(
                f"{path} is kind {dimension.kind!r}, not a switch. Pass it as a "
                f"selector if it has members, or leave it to the continuous search."
            )
        grown = []
        for base in variants:
            for state in (False, True):
                variant = dict(base)
                variant[(dimension.module, dimension.key)] = state
                grown.append(variant)
        variants = grown

    for path in selectors or ():
        dimension = _dimension(space, path)
        members = sorted((dimension.members or {}), key=int)
        if not members:
            raise SearchError(
                f"{path} declares no members, so there is nothing to enumerate. "
                f"The space excludes such selectors for the same reason: a stored "
                f"integer the plugin never displays cannot be chosen on purpose."
            )
        grown = []
        for base in variants:
            for stored in members:
                variant = dict(base)
                variant[(dimension.module, dimension.key)] = int(stored)
                grown.append(variant)
        variants = grown
    return variants


# --- stage 3: CMA-ES --------------------------------------------------------


def refine(evaluator: Evaluator, seed: Mapping, searched: Sequence[str],
           budget: int, sigma: float = INITIAL_SIGMA,
           rng=None) -> Tuple[List[Candidate], List[str]]:
    """CMA-ES over the screened parameters, seeded from the recipe stack.

    Returns every candidate it evaluated, plus caveats. The implementation is the
    standard (μ/μ_w, λ)-CMA-ES with the usual constants — no PyTorch, no `cma`
    dependency (§2, D4), just numpy — because the thing being optimised is 10 to 40
    dimensions of bounded continuous parameters, which is squarely what CMA-ES was
    designed for and does not need a framework.

    Bounds are handled by clipping the evaluated **sample**, and that is sufficient: the
    new mean is `weights @ selected`, the weights are positive and sum to one, and every
    row of `selected` was clipped into [0, 1] — so the mean is a convex combination of
    points in the box and is therefore in the box. It cannot leave, and no separate
    guard on it can do anything.

    This paragraph used to carry a measured table — unclipped 2.5e-03 against clipped
    2.6e-06 on a sphere at unit 0.02, n=8, σ=0.15, 600 evaluations, with a final mean
    range of (−4.2, −0.55) — arguing that clipping the mean mattered a thousandfold. It
    does not, and the table cannot have come from this algorithm: reproduced at four
    seeds, clipped and unclipped agree to every digit printed (3.677e-06, 6.797e-06,
    1.856e-06, 4.268e-06), and the mean's range is (0.019, 0.021) either way. Even with
    the optimum placed *outside* the box at unit −0.30, so that the fitness rewards
    movement past the bound, both variants pin the mean at exactly 0.000 — because of the
    convexity above. It replaced an earlier paragraph that argued the opposite case from
    first principles, and the lesson is the same one twice over: a table with no
    recorded invocation behind it is an argument wearing decimal points.
    """
    import numpy as np

    if not searched:
        return [], ["the screen froze every parameter, so there was nothing to "
                    "refine — the inversion's answer stands"]
    if budget <= 0:
        return [], [f"no budget was left for the optimiser after screening "
                    f"{len(searched)} parameters, so the seed stands"]

    rng = np.random.default_rng(0) if rng is None else rng
    dimensions = [_dimension(evaluator.space, path) for path in searched]
    n = len(dimensions)

    from match.space import _to_unit

    # `or d.bounds()[0]` here read a seed value of exactly **0.0** as absent, because
    # 0.0 is falsy — so a searched parameter sitting at zero started the optimiser at
    # the *bottom* of its range instead. That is not a corner case: the bundled
    # `Example_Clean_PR12.xml` has 35 continuous dimensions at exactly 0.0, including
    # all nine EQ bands (−12..+12 dB, so 0.0 is the middle) and `inputGain`. It also
    # made `None` and `0.0` indistinguishable, which is the very confusion
    # `Space.encode` was rewritten to refuse.
    def start_at(dimension: Dimension) -> float:
        value = _get(seed, dimension)
        if value is None:
            return _to_unit(dimension, dimension.bounds()[0])
        return _to_unit(dimension, value)

    mean = np.array([start_at(d) for d in dimensions], dtype=np.float64)

    # The textbook defaults (Hansen). Written out rather than tuned, so that a
    # future change to them is visible as a change.
    lambda_ = generation_size(n)
    mu = lambda_ // 2
    raw = np.array([math.log(mu + 0.5) - math.log(i + 1) for i in range(mu)])
    weights = raw / raw.sum()
    mu_eff = 1.0 / float(np.sum(weights ** 2))
    c_c = (4 + mu_eff / n) / (n + 4 + 2 * mu_eff / n)
    c_s = (mu_eff + 2) / (n + mu_eff + 5)
    c_1 = 2 / ((n + 1.3) ** 2 + mu_eff)
    c_mu = min(1 - c_1, 2 * (mu_eff - 2 + 1 / mu_eff) / ((n + 2) ** 2 + mu_eff))
    damps = 1 + 2 * max(0.0, math.sqrt((mu_eff - 1) / (n + 1)) - 1) + c_s
    chi_n = math.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n ** 2))

    path_c = np.zeros(n)
    path_s = np.zeros(n)
    covariance = np.eye(n)
    step = float(sigma)

    evaluated: List[Candidate] = []
    caveats: List[str] = []
    generations = 0
    while len(evaluated) + lambda_ <= budget:
        try:
            eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        except np.linalg.LinAlgError:
            caveats.append(
                f"the search lost its bearings after {generations} rounds and "
                f"stopped early — the best of the {len(evaluated)} settings it had "
                f"tried by then is what you have. Running it again with a different "
                f"--seed usually gets further."
            )
            break
        eigenvalues = np.maximum(eigenvalues, 1e-20)
        root = eigenvectors @ np.diag(np.sqrt(eigenvalues))

        offsets = rng.standard_normal((lambda_, n))
        samples = np.clip(mean + step * (offsets @ root.T), 0.0, 1.0)
        scored = []
        for sample in samples:
            candidate = evaluator.evaluate(_decode(evaluator.space, dimensions,
                                                   sample, seed))
            evaluated.append(candidate)
            scored.append((candidate.total, sample))

        scored.sort(key=lambda pair: pair[0])
        if not math.isfinite(scored[0][0]):
            caveats.append(
                f"every candidate in generation {generations + 1} failed to render "
                f"or produced nothing to compare, so the optimiser stopped rather "
                f"than moving its mean towards a failure"
            )
            break

        selected = np.array([pair[1] for pair in scored[:mu]])
        previous = mean.copy()
        # No clip. A convex combination of clipped samples is inside the box already —
        # see the docstring — so `np.clip` here was dead, and dead code that looks like
        # a safety guard is worse than none: it invites the reader to believe a bound is
        # being enforced somewhere it is not needed and to stop looking for where it is.
        mean = weights @ selected

        # The two evolution paths, and the step-size and covariance updates they
        # drive. Standard CMA-ES.
        inverse_root = eigenvectors @ np.diag(1 / np.sqrt(eigenvalues)) @ eigenvectors.T
        displacement = (mean - previous) / step
        path_s = ((1 - c_s) * path_s
                  + math.sqrt(c_s * (2 - c_s) * mu_eff) * (inverse_root @ displacement))
        h_sigma = (np.linalg.norm(path_s)
                   / math.sqrt(1 - (1 - c_s) ** (2 * (generations + 1)))
                   / chi_n) < (1.4 + 2 / (n + 1))
        path_c = ((1 - c_c) * path_c
                  + (math.sqrt(c_c * (2 - c_c) * mu_eff) * displacement if h_sigma
                     else 0.0))
        spread = (selected - previous) / step
        covariance = ((1 - c_1 - c_mu) * covariance
                      + c_1 * (np.outer(path_c, path_c)
                               + (0.0 if h_sigma else c_c * (2 - c_c)) * covariance)
                      + c_mu * (spread.T @ (weights[:, None] * spread)))
        covariance = (covariance + covariance.T) / 2.0
        step *= math.exp((c_s / damps) * (np.linalg.norm(path_s) / chi_n - 1))
        generations += 1

        # Stop when the step is finer than what the plugin can store, rather than
        # flooring it there. A floor was the first attempt and it guaranteed the
        # waste it was meant to prevent: 1e-4 in unit space is 0.0024 dB against an EQ
        # band's 0.25 dB quantum, so once the step reached the floor every remaining
        # render was a duplicate of one already made. A well-posed run hit it and then
        # sampled out the rest of its budget.
        if step < _quantisation_step(dimensions):
            caveats.append(
                f"the optimiser stopped after {generations} generations and "
                f"{len(evaluated)} renders: its step had become finer than the "
                f"smallest change these controls can store, so every further render "
                f"would have repeated one already made"
            )
            break

    # No "it never ran" caveat here. `search` owns that message, because it is the only
    # caller that knows what the fixed costs were and can therefore name the number to
    # raise `--budget` to. The version that lived here said "at least λ more than the
    # fixed costs above" — and nothing above had printed a fixed cost, so the one
    # actionable sentence in the run pointed at nothing. Two messages for one fact, and
    # the one that fired on an 18-parameter Morgan search was the useless one.
    return evaluated, caveats


# --- the Pareto archive ------------------------------------------------------


def pareto(candidates: Sequence[Candidate], dimensions: Sequence[str],
           limit: int = 5) -> List[Candidate]:
    """The non-dominated candidates, thinned to perceptually distinct ones.

    Thinned by `DISTINCT_OBJECTIVE`, which used to be a `distinct=` argument that no
    caller outside the tests ever set.
    """
    distinct = DISTINCT_OBJECTIVE
    usable = [c for c in candidates if c.objectives and math.isfinite(c.total)]
    front = [c for c in usable
             if not any(other.dominates(c, dimensions) for other in usable)]
    front.sort(key=lambda c: c.total)

    kept: List[Candidate] = []
    for candidate in front:
        if all(_separation(candidate, other, dimensions) >= distinct for other in kept):
            kept.append(candidate)
        if len(kept) >= limit:
            break
    return kept


# --- stage 4: robustness -----------------------------------------------------


def robustness_rerank(evaluator: Evaluator, shortlist: Sequence[Candidate],
                      offsets_db: Sequence[float] = ROBUSTNESS_OFFSETS_DB,
                      ) -> Tuple[List[Candidate], List[str]]:
    """Re-render the shortlist at other input levels and order by the worst score.

    A preset that matches at one input level and falls apart at another is not a
    match. This is not a hypothetical: the repository's own THD measurements show
    breakup depending strongly on input level, and every candidate above was scored
    at exactly one.

    Ordered by the *worst* level rather than the mean, and the ranking a caller
    reads is the one that survived this rather than the one that was handed in.
    """
    import numpy as np

    if not shortlist:
        return [], []

    caveats: List[str] = []
    unmeasured: List[float] = []
    # How much of the spread is the `level` term — i.e. the loudness change this stage
    # caused by turning the input up and down — rather than the tone change it exists to
    # detect. Measured per candidate as (change in the weighted level term) / (change in
    # the total), because on the synthetic chain it turned out to be 84% to 100% of it,
    # 97% on average.
    level_share: List[float] = []
    levels = [0.0] + [float(offset) for offset in offsets_db]
    for candidate in shortlist:
        for offset in levels:
            if offset == 0.0:
                candidate.by_level[0.0] = candidate.total
                continue
            scaled = np.asarray(evaluator.probe_di, dtype=np.float64) * (
                10.0 ** (offset / 20.0))
            scored = evaluator.evaluate(candidate.values, di=scaled,
                                        offset_db=offset)
            if scored.objectives:
                candidate.by_level[offset] = scored.total
                share = _level_share(evaluator, candidate, scored)
                if share is not None:
                    level_share.append(share)
            else:
                # A render that failed or came back silent at a shifted level is not
                # a robustness measurement. Recording `inf` made the candidate sink
                # to the bottom of the shortlist *as though it had been measured and
                # found fragile*, which is the standing rule this repository breaks
                # least often: silence is not evidence about a control.
                unmeasured.append(offset)
    if unmeasured:
        levels_text = ", ".join(f"{offset:+.0f} dB" for offset
                                in sorted(set(unmeasured)))
        caveats.append(
            f"one or more candidates could not be re-rendered at {levels_text} of "
            f"input level, so their robustness across playing levels is unknown "
            f"rather than poor — the shortlist below is ordered on the levels that "
            f"did measure"
        )

    reranked, ordering_caveats = _rerank_and_explain(shortlist)
    caveats.extend(ordering_caveats)
    # What the spread is made of, when it is mostly not tone. The docstring above says
    # this stage exists because "breakup depends strongly on input level" — a claim
    # about *timbre* — and measured on the synthetic chain the `level` term accounted
    # for 84% to 100% of the movement — 97% on average — while `timbre` shifted by 0.0001
    # to 0.003. So "0.280
    # at worst, and it holds up" was largely a statement about output loudness, and the
    # loudness was a consequence of the stage turning the input up. Named rather than
    # dropped from the score: a preset whose compression holds its output level steady
    # across playing levels genuinely is more robust, and that belongs in the number.
    if level_share and (sum(level_share) / len(level_share)) > 0.5:
        share = 100.0 * sum(level_share) / len(level_share)
        caveats.append(
            f"about {share:.0f}% of the change in score across ±6 dB is the output "
            f"getting louder or quieter rather than the tone changing — turning the "
            f"input up makes the render louder, and the level term counts that. The "
            f"±6 dB figures are a weaker statement about breakup than they look."
        )
    return reranked, caveats


def _level_share(evaluator: Evaluator, candidate: Candidate,
                 offset_scored: Candidate) -> Optional[float]:
    """The fraction of a candidate's score change at an offset that is the level term.

    `None` when there is nothing to take a fraction of — either dimension missing, or
    a total that did not move — rather than a 0.0 that would drag the mean down and
    read as "the level term is not involved".
    """
    from analysis.compare import load_profile

    weights = load_profile(evaluator.profile).get("weights", {})
    weight = float(weights.get("level", 0.0))
    if not weight:
        return None
    before = (candidate.objectives or {}).get("level")
    after = (offset_scored.objectives or {}).get("level")
    if before is None or after is None:
        return None
    total_change = abs(offset_scored.total - candidate.total)
    if total_change < 1e-9:
        return None
    return min(1.0, weight * abs(after - before) / total_change)


def _rerank_and_explain(shortlist: Sequence[Candidate],
                        ) -> Tuple[List[Candidate], List[str]]:
    """Order by the worst level, and say so when that changed the answer.

    Split from the rendering so it can be tested on constructed `by_level` values.
    The whole worth of the stage is in the first caveat: without it a caller reads
    the reordered list and never learns that the reference-level winner lost.
    """
    reranked = sorted(shortlist, key=lambda c: (c.worst_level if c.worst_level
                                                is not None else float("inf")))
    caveats: List[str] = []
    was, now = shortlist[0], reranked[0] if reranked else None
    # Both levels have to be known before the reorder can be described. A candidate
    # that was never re-rendered has `worst_level` of None, and formatting that with
    # `:.3f` raised a TypeError — on precisely the constructed input this function was
    # split out to make testable.
    if (now is not None and now is not was
            and was.worst_level is not None and now.worst_level is not None):
        caveats.append(
            f"the best match at the reference input level ({was.total:.3f}) is not "
            f"the best across ±6 dB of it ({was.worst_level:.3f} at worst, against "
            f"{now.worst_level:.3f}), so the shortlist is ordered by the worse "
            f"case. A preset that only works at one input level is a preset that "
            f"will not survive being played."
        )
    spreads = [c.worst_level - min(c.by_level.values()) for c in reranked
               if c.by_level and math.isfinite(c.worst_level)]
    if spreads and max(spreads) > 0.25:
        caveats.append(
            f"the shortlist's scores move by up to {max(spreads):.2f} across ±6 dB "
            f"of input level, so how hard you hit the amp matters as much as these "
            f"settings do — check the match at your own playing level"
        )
    return reranked, caveats


# --- the whole pass ----------------------------------------------------------


def search(renderer, target, probe_di, space: Space, seed: Mapping,
           budget: int = 300, profile: str = "unpaired-v1",
           fallbacks: Optional[Sequence[Mapping]] = None,
           shortlist: int = 3, store: Optional[Store] = None,
           run_id: Optional[str] = None,
           switches: Optional[Sequence[str]] = None,
           selectors: Optional[Sequence[str]] = None,
           rng=None, reference_audio=None) -> SearchResult:
    """Screen, enumerate, refine, re-rank — the four stages in order.

    `seed` is the recipe stack plus whatever `invert()` calculated, and it is both
    the starting point and the prior: `prior_deviation` measures distance from it,
    so a candidate that scores the same by moving less wins.

    `fallbacks` are vectors that must be considered even though the search would not
    reach them — in practice the *template as it arrived*, before the inversion
    touched it. Without it a near-perfect template could only get worse: matching the
    bundled PR12 preset against a render of itself scored 0.069 for the template,
    0.593 after the inversion, and 0.408 after the search recovered what it could,
    and the answer handed back was 0.408. The thing you started with has to be on the
    shortlist, or "improvement" is measured from whatever the previous stage did to
    it rather than from where you began.

    The budget is spent in a fixed order, every stage reports what it took, and the
    fixed costs are reserved before the optimiser is offered anything:

    - the screen: **2N + 1** renders for N candidate parameters on a reproducible
      backend, or **2N + 5** when a non-reproducible backend needs five uncached
      observations of the baseline's scalar-objective variation
    - the topology loop: **one render per variant**, for the variant's own seed. This
      was not reserved, so a run overspent by exactly the variant count — one render
      with no switches enumerated, thirty-two with five
    - the re-rank: 2 per shortlisted candidate

    Whatever is left goes to CMA-ES, split across the variants. A run that ends up
    over or materially under budget says so; the accounting is meant to be checkable
    rather than plausible.
    """
    from analysis import require

    require("searching for a preset")

    if budget <= 0:
        raise SearchError(f"budget must be at least 1 render, not {budget}")

    evaluator = Evaluator(renderer, target, probe_di, space, profile=profile,
                          store=store, run_id=run_id, recipe=seed,
                          reference_audio=reference_audio)
    result = SearchResult(run_id=run_id)

    screened = screen(evaluator, seed)
    searched, frozen = screened.searched, screened.frozen
    probes, movement, silences = screened.probes, screened.movement, screened.silences
    result.frozen = frozen
    result.searched = list(searched)
    result.movement = {path: movement[path] for path in searched if path in movement}
    result.floor = screened.floor
    result.floor_observations = screened.repeat_observations
    result.silences = dict(silences)
    if screened.repeat_failures:
        result.caveats.append(
            f"{screened.repeat_failures} of "
            f"{NONREPRODUCIBLE_SCREEN_SAMPLES} identical-state observations could "
            "not be scored, so the sensitivity floor conservatively used the "
            "larger of the observed scalar spread and the renderer's metadata "
            "fallback"
        )
    if frozen:
        # Frozen for three different reasons, and saying "below the floor" about all
        # of them was false: a caveat claimed four parameters "moved the objective by
        # less than 0.01" when their measured movements were 0.062, 0.062, 0.109 and
        # 0.070 — every one of them well clear of the floor and cut by the quantile
        # instead. The report's table showed 0.109 next to the claim.
        #
        # `screened.floor`, not `SENSITIVITY_FLOOR`: the screen raises its floor to the
        # backend's own band noise, and classifying against the constant put a
        # parameter cut by the *floor* into the "weakest 25%, a larger budget would
        # search them" sentence. No budget will search it.
        floor = screened.floor
        inert = [p for p, v in frozen.items() if not _isnan(v) and v < floor]
        weakest = [p for p, v in frozen.items() if not _isnan(v) and v >= floor]
        unknown = [p for p, v in frozen.items() if _isnan(v)]
        total = len(frozen) + len(searched)
        # A control that mutes the signal at one end gets its own sentence wherever it
        # ends up, because "one end of this silences the signal" is the fact a person
        # acts on and neither of the other two sentences carries it.
        muting = [p for p in silences if p in frozen]
        inert = [p for p in inert if p not in silences]
        weakest = [p for p in weakest if p not in silences]
        if inert:
            # "moved the objective" was the one piece of jargon that reached the
            # terminal. `report._screen` had already found the plain wording for the
            # same number and this had not borrowed it.
            result.caveats.append(
                f"{len(inert)} of {total} parameters changed the distance to the "
                f"reference by less than {floor:g} across their whole range "
                f"on this material, so they were left at the seed. On different "
                f"material they might matter."
            )
        if muting:
            named = ", ".join(f"{p} at {silences[p]:g}" for p in sorted(muting))
            result.caveats.append(
                f"one end of {named} silences the signal entirely, so it was left at "
                f"the seed. That is what the control is for rather than a problem — "
                f"but it means the search never tried the loud end either, and a "
                f"noise gate set too high is the commonest way a preset sounds broken."
            )
        if weakest:
            result.caveats.append(
                f"{len(weakest)} of {total} parameters did change the distance to the "
                f"reference but were the weakest "
                f"{int(100 * SENSITIVITY_QUANTILE)}% that did, so "
                f"they were left at the seed to spend the budget on the rest — the "
                f"most any of them moved it was "
                f"{max(frozen[p] for p in weakest):.3f}. A larger budget would "
                f"search them."
            )
        unknown = [p for p in unknown if p not in silences]
        if unknown:
            plural = "s" if len(unknown) > 1 else ""
            result.caveats.append(
                f"{len(unknown)} parameter{plural} could not be screened at all — "
                f"the render failed or came back silent at one or both extremes — so "
                f"{'they were' if plural else 'it was'} left at the seed without "
                f"being measured: {', '.join(sorted(unknown)[:4])}"
            )

    variants = topologies(space, seed, switches=switches, selectors=selectors)
    if len(variants) == 1:
        # No caller reaches the enumeration. `switches` and `selectors` are `search`'s
        # own parameters, nothing in the repository outside tests passes them, and the
        # report's diff column shows switch changes anyway — from the *inversion* — so
        # it reads as though discrete choices were searched. §12c names this as a stage
        # that exists rather than a stage that runs; the run has to say so too.
        result.caveats.append(
            "no switches or selectors were enumerated, so every on/off, the cabinet, "
            "the microphone and the amp are whatever the starting point had — only "
            "continuous controls were searched. Trying a different cab or mic means "
            "editing the template and running this again."
        )
    spent = evaluator.renders
    # Every fixed cost, reserved: the screen has already been paid, the topology loop
    # will render each variant's own seed, the re-rank will render each shortlisted
    # candidate at two more input levels, and each fallback is one render.
    reserved = len(variants) + 2 * shortlist + len(fallbacks or ())
    remaining = budget - spent - reserved
    # One whole generation is the granularity of the search, not one render: CMA-ES
    # samples λ points before it learns anything. A budget leaving 6 renders against a
    # λ of 12 bought exactly as much search as a budget leaving none, and took the
    # branch that told the user so only in the second case.
    generation = generation_size(len(searched)) if searched else 1
    if remaining < generation:
        needed = spent + reserved + generation
        result.unsearched = (
            f"the optimiser never ran, so nothing below was searched — the seed and "
            f"the inversion stand. Of the {budget}-render budget, {spent + reserved} "
            f"goes to costs that cannot be part-paid: {spent} to screen "
            f"{len(searched) + len(frozen)} parameters, {len(variants)} for the "
            f"starting point of each topology, {2 * shortlist} for the ±6 dB re-rank"
            + (f" and {len(fallbacks or ())} for the template as it arrived"
               if fallbacks else "")
            + f". That leaves {max(0, remaining)} against the {generation} that one "
            f"round of search costs with {len(searched)} parameters to move. "
            f"Raise --budget to at least {needed}."
        )
        result.caveats.append(result.unsearched)
        candidates = list(probes) + [evaluator.evaluate(variant)
                                     for variant in variants]
        candidates.extend(evaluator.evaluate(dict(v)) for v in fallbacks or ())
    else:
        per_variant = max(1, remaining // len(variants))
        if len(variants) > 1:
            result.caveats.append(
                f"{len(variants)} topologies share the budget, so each got about "
                f"{per_variant} render{'' if per_variant == 1 else 's'}. Enumerating "
                f"fewer switches gives each remaining one a deeper search."
            )
        # The screen's own probes are candidates: each one is a real parameter
        # vector that was rendered and scored, and one of them may be the answer.
        candidates = list(probes)
        # And so is whatever the caller started from, before anything was done to it.
        candidates.extend(evaluator.evaluate(dict(v)) for v in fallbacks or ())
        for variant in variants:
            # The variant itself first: it is what the prior is measured from, and
            # a topology whose seed already beats every sample is worth keeping.
            candidates.append(evaluator.evaluate(variant))
            evaluated, caveats = refine(evaluator, variant, searched, per_variant,
                                        rng=rng)
            candidates.extend(evaluated)
            # Once each, not once per variant. Every variant runs the same optimiser
            # over the same parameters with the same budget, so they hit the same
            # termination and produce the same sentence: three enumerated switches gave
            # eight identical copies of it, Morgan's five would give thirty-two. This is
            # the module whose whole argument is that the caveat block stays worth
            # reading, and padding it teaches people to skip it.
            result.caveats.extend(c for c in caveats if c not in result.caveats)

    from analysis.compare import DIMENSIONS

    front = pareto(candidates, DIMENSIONS, limit=shortlist)
    if not front:
        result.caveats.append(
            "no candidate produced a comparable render, so there is no shortlist. "
            "Check the renderer: every trial either failed or came back silent."
        )
    reranked, rerank_caveats = robustness_rerank(evaluator, front)
    result.shortlist = reranked
    result.caveats.extend(rerank_caveats)
    result.renders = evaluator.renders
    result.cache_hits = evaluator.cache_hits
    result.wall_ms = round(evaluator.wall_ms, 1)
    if evaluator.residual_enabled:
        result.caveats.append(
            "the paired waveform residual was measured from the reference samples "
            "after aligning every candidate render; unlike the fingerprint terms, "
            "it is a sample-for-sample comparison. It is meaningful only when the "
            "reference really is a reamp of the exact probe-DI performance; the "
            "samples themselves cannot prove that provenance"
        )
        if evaluator.untrusted_alignments:
            result.caveats.append(
                f"{evaluator.untrusted_alignments} of "
                f"{evaluator.alignment_attempts} paired comparisons had absolute "
                "correlation below 0.30, so their waveforms were compared unshifted "
                "rather than applying an offset inferred from noise"
            )
    if result.renders > budget:
        screen_fixed = "2 per parameter plus one baseline"
        if not evaluator.renderer.metadata().reproducible:
            screen_fixed += (
                f" plus {NONREPRODUCIBLE_SCREEN_SAMPLES - 1} repeats used to "
                "measure backend variation"
            )
        result.caveats.append(
            f"the search made {result.renders} renders against a budget of "
            f"{budget}. The screen costs {screen_fixed} and "
            f"cannot be part-paid, so a budget below {spent + reserved} is exceeded "
            f"rather than trimmed"
        )
    elif budget - result.renders > max(10, budget // 5):
        # The other direction, which nothing reported: CMA-ES only spends whole
        # generations, so a budget that does not divide by λ leaves a remainder, and
        # a run that quietly used 70% of what it was given should say so rather than
        # let a caller conclude the budget was the constraint.
        result.caveats.append(
            f"only {result.renders} of the {budget}-render budget was spent: the "
            f"optimiser samples a whole generation at a time, so the remainder is "
            f"not enough for another one. A budget nearer a multiple of its "
            f"generation size would use more of it."
        )
    return result


# --- helpers ----------------------------------------------------------------


def _dimension(space: Space, path: str) -> Dimension:
    module, _, key = path.rpartition("/")
    return space.by_path(module, key)


def _get(values: Mapping, dimension: Dimension):
    from match.space import _get as read

    return read(values, (dimension.module, dimension.key))


def _backend_floor(evaluator: Evaluator,
                   repeated: Optional[Sequence[Candidate]] = None,
                   expected: int = NONREPRODUCIBLE_SCREEN_SAMPLES) -> float:
    """The screen's measured scalar-objective repeat spread.

    ``screen`` supplies five uncached evaluations for a non-reproducible backend.
    Their peak-to-peak scalar spread is already in the same units as the movement
    being screened, unlike a third-octave dB maximum divided by one loss scale.

    The metadata derivation remains only as a fallback when either repeat render
    could not be scored. It is conservative and keeps a broken repeat from silently
    lowering the floor to zero.
    """
    candidates = list(repeated or ())
    totals = [float(candidate.total) for candidate in candidates
              if candidate.objectives]
    observed = max(totals) - min(totals) if len(totals) >= 2 else 0.0
    metadata = evaluator.renderer.metadata()
    noise = float(getattr(metadata, "band_noise_db", 0.0) or 0.0)
    if len(candidates) >= expected and len(totals) == len(candidates):
        return observed
    if noise <= 0.0:
        return observed
    from analysis.compare import load_profile

    scale = float(load_profile(evaluator.profile)["scales"].get("band_db") or 3.0)
    fallback = noise / scale if scale > 0 else 0.0
    return max(observed, fallback)


def _quantisation_step(dimensions: Sequence[Dimension]) -> float:
    """The finest step worth taking, in normalised units.

    A quantum is declared in the control's own unit — 0.25 dB on an EQ band, 1 Hz on a
    corner — so the smallest *normalised* step that still changes a stored value is
    the quantum over the range. The narrowest one across the searched dimensions is
    the limit for the search as a whole, halved, so the optimiser stops one step
    after it stops being able to move anything rather than one step before.
    """
    steps = []
    for dimension in dimensions:
        low, high = dimension.bounds()
        if dimension.quantum and high > low:
            steps.append(float(dimension.quantum) / (high - low))
    return (min(steps) / 2.0) if steps else 1e-6


def _decode(space: Space, dimensions: Sequence[Dimension], vector,
            seed: Mapping) -> Dict[Any, Any]:
    """One CMA-ES sample as human values, over the seed.

    Only the searched dimensions are replaced. Everything else keeps its seed value,
    which is what makes the frozen parameters frozen rather than merely unmentioned.
    """
    from match.space import _from_unit

    values = dict(seed)
    for dimension, unit in zip(dimensions, vector):
        values[(dimension.module, dimension.key)] = _from_unit(dimension, float(unit))
    return values


def _separation(one: Candidate, other: Candidate,
                dimensions: Sequence[str]) -> float:
    """Largest per-dimension gap between two candidates' objectives.

    The largest rather than the Euclidean distance, because two presets that differ
    audibly in *one* respect are two presets, and averaging that difference across
    nine dimensions is how it disappears.
    """
    gaps = [abs(one.objectives[name] - other.objectives[name])
            for name in dimensions
            if name in one.objectives and name in other.objectives]
    return max(gaps) if gaps else 0.0


def supported_keys(renderer) -> Optional[set]:
    """The paths this backend can be driven with, or None if it accepts anything.

    Spelled the way `Dimension.path` and `ParamSpec.path` both spell it, which for
    a top-level parameter means no leading slash. A backend keys its specs
    `(module, key)`, and joining `("", "selectedAmp")` gives `/selectedAmp` while
    the dimension it has to match is `selectedAmp` — so the key was compared
    against a spelling it could never equal.

    That is not cosmetic. `_settings` drops a dimension the backend does not
    claim to support, so `selectedAmp` was dropped from every render on any
    backend that declares it: the search would move an amp's tone stack while the
    plugin stayed on whatever amp it booted with, and writing a control on an
    unselected amp is a silent no-op. Nothing would have failed, and every number
    would have been about the wrong amp. The synthetic chain models one amp and
    never declared `selectedAmp`, which is why this survived M3 and M4.
    """
    try:
        specs = renderer.parameter_specs()
    except NotImplementedError:
        return None
    keys = set()
    for key in specs:
        path = key if isinstance(key, str) else "/".join(str(part) for part in key)
        keys.add(path[1:] if path.startswith("/") else path)
    return keys


# Compatibility for callers and tests written before CLI preflight needed this
# normalisation too. There remains one implementation, especially for top-level
# keys where a leading slash changes whether the parameter is ever rendered.
_supported_keys = supported_keys


def _scoring_key(render_key: str, target, profile: str, recipe: Mapping,
                 reference_audio_sha: Optional[str] = None) -> str:
    """The content address for a *score*, which is finer than the render's.

    Two renders of the same parameters through the same DI are the same audio, so
    §6.3's key addresses them together — correctly. But the number the search caches
    is not the audio, it is the distance to a reference under a weighting, and that
    also depends on which reference, which loss profile, and which seed the prior
    terms measure from. A residual-weighted score additionally depends on the
    reference samples, not only the fingerprint. Keying the cache on the render
    alone was enough to serve one run's objectives to a later run against a
    different recording.

    The whole target fingerprint is digested. The file hash alone is insufficient:
    two excerpts of one file are different targets, and naming one optional field
    here already failed when the provenance schema used different field names.
    """
    import hashlib

    import json

    target_document = (target.to_dict() if callable(getattr(target, "to_dict", None))
                       else target)
    target_digest = hashlib.sha256(json.dumps(
        target_document, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    material = "␟".join([
        str(render_key),
        target_digest,
        str(profile),
        canonical_settings(recipe),
        str(reference_audio_sha),
    ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _hash(audio) -> str:
    import hashlib

    import numpy as np

    array = np.ascontiguousarray(np.asarray(audio, dtype=np.float32))
    return hashlib.sha256(array.tobytes()).hexdigest()


def _isnan(value: float) -> bool:
    return isinstance(value, float) and math.isnan(value)
