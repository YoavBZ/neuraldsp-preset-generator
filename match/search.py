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
   immediately: Morgan declares 126 searchable dimensions of which **88 are
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
    renders: int = 0
    cache_hits: int = 0
    wall_ms: float = 0.0
    caveats: List[str] = field(default_factory=list)
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
                 recipe: Optional[Mapping] = None) -> None:
        from analysis import require

        require("searching for a preset")
        self.renderer = renderer
        self.target = target
        self.probe_di = probe_di
        self.space = space
        self.profile = profile
        self.store = store
        self.run_id = run_id
        self.recipe = dict(recipe or {})
        self.renders = 0
        self.cache_hits = 0
        self.wall_ms = 0.0
        self._supported = _supported_keys(renderer)

    # --- the one expensive call ---------------------------------------------

    def evaluate(self, values: Mapping, di=None,
                 offset_db: float = 0.0) -> Candidate:
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
        scoring_key = _scoring_key(key, self.target, self.profile, self.recipe)

        if self.store is not None:
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
            vector = compare(
                self.target, printed, profile=self.profile,
                prior_deviation=self._prior_deviation(values),
                complexity=self._complexity(values),
            )
            objectives = {name: float(value) for name, value in vector.values.items()
                          if value is not None}
            total = scalar(vector)
            if total is None:
                # Nothing the profile weights was measurable on either side, so
                # there is no ordering to be had. Not an error, and not a zero.
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
                         trial_id=trial_id)

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


def screen(evaluator: Evaluator, seed: Mapping,
           floor: float = SENSITIVITY_FLOOR,
           quantile: float = SENSITIVITY_QUANTILE,
           only: Optional[Sequence[str]] = None
           ) -> Tuple[List[str], Dict[str, float], List[Candidate],
                      Dict[str, float], Dict[str, float]]:
    """Which parameters move the objective, and by how much.

    Two renders per parameter — its low end and its high end, everything else at the
    seed — so the cost is known before it is spent: 2 × the number of candidates,
    once. Returns the paths worth searching, the ones frozen with the movement that
    decided each, **every probe it scored**, and the movement of every parameter —
    searched or frozen — so a report can show the decision rather than assert it.

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
    floor = max(float(floor), _backend_floor(evaluator))
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
    baseline = evaluator.evaluate(seed)
    probes.append(baseline)
    if not baseline.objectives:
        raise SearchError(
            "the seed vector produced nothing to compare against — a silent render, "
            "or no dimension the loss profile weights.\n"
            "  Every movement below is measured against this, so the screen cannot "
            "proceed without it."
        )

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
            # are, so padding it teaches people to skip it. The movement is recorded
            # against the end that did render, so the control can still be frozen or
            # searched on evidence.
            movement[dimension.path] = 0.0
            silences[dimension.path] = float(silenced[0])
            continue
        # A parameter whose extremes both failed to render is *unknown*, not inert.
        # Freezing it is still the right call — nothing was learned about it — but
        # the movement is recorded as NaN so a report does not claim it was measured.
        movement[dimension.path] = (max(scores) - min(scores) if len(scores) == 2
                                    else float("nan"))

    measured = {path: value for path, value in movement.items() if not _isnan(value)}
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
    return searched, frozen, probes, movement, silences


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

    Bounds are handled by clipping the evaluated sample **and** the distribution's
    mean. An earlier version clipped only the sample, on the reasoning that clipping
    the mean lets a parameter stick on a bound it was only passing through — which
    sounds right and is measurably wrong. Clipping the sample makes the fitness a
    *plateau* outside the box, so selection carries no gradient information back and a
    mean that wanders out never returns. Measured on a sphere objective, n=8, σ=0.15,
    600 evaluations, optimum at unit 0.02 — the near-clean end of a gain control,
    exactly the case the old comment cited:

    | mean | best found | final mean range |
    |---|---|---|
    | unclipped | 2.5e-03 | (−4.2, −0.55) |
    | clipped   | **2.6e-06** | (0.019, 0.021) |

    A thousand times worse, and it also wasted renders: with the optimum near a bound,
    76% of 600 samples quantised to a vector already tried, and only 10 of the last
    240 were distinct. Nobody had measured the claim; it was an argument.
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
    lambda_ = 4 + int(3 * math.log(n))
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
        mean = np.clip(weights @ selected, 0.0, 1.0)

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

    if generations == 0 and not caveats:
        caveats.append(
            f"the budget of {budget} renders is smaller than one round of "
            f"{lambda_}, which is the smallest step the search can take with "
            f"{n} parameters to move, so it never ran. Raise --budget to at least "
            f"{lambda_} more than the fixed costs above."
        )
    return evaluated, caveats


# --- the Pareto archive ------------------------------------------------------


def pareto(candidates: Sequence[Candidate], dimensions: Sequence[str],
           limit: int = 5, distinct: float = 0.02) -> List[Candidate]:
    """The non-dominated candidates, thinned to perceptually distinct ones.

    `distinct` is the minimum objective-space separation between two entries. Two
    presets differing by 0.005 of an objective are the same preset as far as anyone
    listening is concerned, and a shortlist of five of them is a shortlist of one
    that wastes four listening comparisons.
    """
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
    return reranked, caveats + ordering_caveats


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
           rng=None) -> SearchResult:
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

    - the screen: **2N + 1** renders for N candidate parameters — the baseline the
      movements are measured against is a render too, and calling it "2 per
      parameter" was off by exactly that one
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
                          store=store, run_id=run_id, recipe=seed)
    result = SearchResult(run_id=run_id)

    searched, frozen, probes, movement, silences = screen(evaluator, seed)
    result.frozen = frozen
    result.searched = list(searched)
    result.movement = {path: movement[path] for path in searched if path in movement}
    if frozen:
        # Frozen for three different reasons, and saying "below the floor" about all
        # of them was false: a caveat claimed four parameters "moved the objective by
        # less than 0.01" when their measured movements were 0.062, 0.062, 0.109 and
        # 0.070 — every one of them well clear of the floor and cut by the quantile
        # instead. The report's table showed 0.109 next to the claim.
        inert = [p for p, v in frozen.items()
                 if not _isnan(v) and v < SENSITIVITY_FLOOR]
        weakest = [p for p, v in frozen.items()
                   if not _isnan(v) and v >= SENSITIVITY_FLOOR]
        unknown = [p for p, v in frozen.items() if _isnan(v)]
        total = len(frozen) + len(searched)
        # A control that mutes the signal at one end is not inert, however small its
        # measured movement: it is the one control that matters most and cannot be
        # scored. Named separately, and only when a caller would act on it.
        muting = [p for p in inert if p in silences]
        inert = [p for p in inert if p not in silences]
        if inert:
            result.caveats.append(
                f"{len(inert)} of {total} parameters moved the objective by less "
                f"than {SENSITIVITY_FLOOR} across their whole range on this "
                f"material, so they were left at the seed. On different material "
                f"they might matter."
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
                f"{len(weakest)} of {total} parameters did move the objective but "
                f"were the weakest {int(100 * SENSITIVITY_QUANTILE)}% that did, so "
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
    spent = evaluator.renders
    # Every fixed cost, reserved: the screen has already been paid, the topology loop
    # will render each variant's own seed, and the re-rank will render each
    # shortlisted candidate at two more input levels.
    reserved = len(variants) + 2 * shortlist + len(fallbacks or ())
    remaining = budget - spent - reserved
    if remaining <= 0:
        result.caveats.append(
            f"the fixed costs used {spent + reserved} of the {budget}-render "
            f"budget — {spent} to screen {len(searched) + len(frozen)} parameters, "
            f"{len(variants)} for the starting point of each topology and "
            f"{2 * shortlist} for the ±6 dB re-rank — so the optimiser never ran. "
            f"The seed and the inversion stand. Raise --budget above "
            f"{spent + reserved + 20} for a search worth the name."
        )
        candidates = list(probes) + [evaluator.evaluate(variant)
                                     for variant in variants]
        candidates.extend(evaluator.evaluate(dict(v)) for v in fallbacks or ())
    else:
        per_variant = max(1, remaining // len(variants))
        if len(variants) > 1:
            result.caveats.append(
                f"{len(variants)} topologies share the budget, so each got about "
                f"{per_variant} renders. Enumerating fewer switches gives each "
                f"remaining one a deeper search."
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
            result.caveats.extend(caveats)

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
    if result.renders > budget:
        result.caveats.append(
            f"the search made {result.renders} renders against a budget of "
            f"{budget}. The screen costs 2 per parameter plus one baseline and "
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


def _backend_floor(evaluator: Evaluator) -> float:
    """The screen's floor, raised to what this backend can resolve.

    `RenderMetadata.band_noise_db` is the per-band spread between two renders of
    identical parameters — measured, not chosen, and 0.23 dB on a reused Audio Unit
    instance. The screen's floor is in *objective* units, so the two have to be
    related, and the loss profile already states the conversion: its `band_db` scale
    is what the timbre term divides a band difference by. So a noise of 0.23 dB
    against a 3.0 dB scale is 0.077 of a normalised band unit.

    Being explicit about what this is: a **derivation**, not a measurement of the
    objective's own repeatability. It is one term of nine, so it overstates — a real
    measurement would render the seed twice on the backend and take the spread of the
    scalar directly, which costs one render and is the right thing to do in M5 when
    there is a backend that varies. Until then this is a defensible bound rather than
    a number nobody checked, and `renderer.py`'s claim that the screen reads
    `band_noise_db` is now true, which it was not.
    """
    metadata = evaluator.renderer.metadata()
    noise = float(getattr(metadata, "band_noise_db", 0.0) or 0.0)
    if noise <= 0.0:
        return 0.0
    from analysis.compare import load_profile

    scale = float(load_profile(evaluator.profile)["scales"].get("band_db") or 3.0)
    return noise / scale if scale > 0 else 0.0


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


def _supported_keys(renderer) -> Optional[set]:
    """The paths this backend can be driven with, or None if it accepts anything."""
    try:
        specs = renderer.parameter_specs()
    except NotImplementedError:
        return None
    keys = set()
    for key in specs:
        keys.add(key if isinstance(key, str) else "/".join(str(part) for part in key))
    return keys


def _scoring_key(render_key: str, target, profile: str, recipe: Mapping) -> str:
    """The content address for a *score*, which is finer than the render's.

    Two renders of the same parameters through the same DI are the same audio, so
    §6.3's key addresses them together — correctly. But the number the search caches
    is not the audio, it is the distance to a reference under a weighting, and that
    also depends on which reference, which loss profile, and which seed the prior
    terms measure from. Keying the cache on the render alone was enough to serve one
    run's objectives to a later run against a different recording.

    The target contributes its `sha256` rather than its whole document: two
    fingerprints of the same file with different excerpt lengths would otherwise
    collide, so the excerpt is folded in too.
    """
    import hashlib

    source = getattr(target, "source", {}) or {}
    material = "␟".join([
        str(render_key),
        str(source.get("sha256")),
        str(source.get("excerpt_s")),
        str(getattr(target, "regime", None)),
        str(profile),
        canonical_settings(recipe),
    ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _hash(audio) -> str:
    import hashlib

    import numpy as np

    array = np.ascontiguousarray(np.asarray(audio, dtype=np.float32))
    return hashlib.sha256(array.tobytes()).hexdigest()


def _isnan(value: float) -> bool:
    return isinstance(value, float) and math.isnan(value)
