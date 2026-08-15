"""The four search stages, against targets built with the answer known.

Every test renders through the synthetic chain, so a "budget" here is small and
real: the point is not that CMA-ES converges — that is Hansen's problem, not this
repository's — but that each stage does the accounting it claims, spends what it
says it spends, and abstains where abstaining is right.
"""

from __future__ import annotations

import math
from unittest import mock

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

import numpy as np

from analysis import io, refchain
from analysis.fingerprint import fingerprint
from match import search as S
from match import space as SP
from match.renderer_synth import SyntheticRenderer
from match.store import Run, Store
from tests import fixtures_audio as fx

SR = fx.SAMPLE_RATE
AMP = "sw50r"


def di():
    return fx.plucks(seconds=2.5, gap=0.9, seed=13)


def printed(audio):
    return fingerprint(io.from_samples(audio, SR), regime="probe", excerpt_s=None)


@pytest.fixture(scope="module")
def space():
    return SP.build("morgan", amp=AMP)


@pytest.fixture(scope="module")
def seed(space):
    """Every control mid-range, effects off, the EQ and the cab section on.

    `selectedAmp` is set *after* the loop on purpose: it is itself an enum dimension,
    so a loop that assigns every enum its first member overwrites it with AC20 — and
    then `amp_prefix` returns `ac20`, every `sw50r` dimension is dormant, and the
    screen finds three parameters instead of eighteen. That cost half an hour once.
    """
    values = {}
    for dimension in space.dimensions:
        if dimension.key == "selectedAmp":
            continue
        if dimension.switch:
            values[(dimension.module, dimension.key)] = (
                dimension.key.endswith("EQActive")
                or dimension.key.endswith("sectionActive"))
        elif dimension.kind == "enum":
            values[(dimension.module, dimension.key)] = int(
                sorted(dimension.members, key=int)[0])
        else:
            low, high = dimension.bounds()
            values[(dimension.module, dimension.key)] = dimension.quantise(
                (low + high) / 2.0)
    values[("", "selectedAmp")] = 2
    return values


@pytest.fixture(scope="module")
def target(space, seed):
    """A render differing from the seed in volume, treble and bass."""
    probe = di()
    scorer = S.Evaluator(SyntheticRenderer(), printed(probe), probe, space)
    truth = dict(seed)
    truth[(f"{AMP}Amp", f"{AMP}Volume")] = 80.0
    truth[(f"{AMP}Amp", f"{AMP}Treble")] = 22.0
    truth[(f"{AMP}Amp", f"{AMP}Bass")] = 72.0
    return printed(refchain.render(probe, scorer._settings(truth)))


# --- the evaluator ----------------------------------------------------------


def test_the_seed_is_live_and_the_amp_resolves(space, seed):
    """The fixture's own precondition, asserted rather than assumed, because getting
    it wrong makes every test below pass while measuring almost nothing."""
    assert space.amp_prefix(seed) == AMP
    live = space.active(seed)
    assert len(live) > 30, f"only {len(live)} dimensions live under the seed"
    assert any(d.module == f"{AMP}Amp" for d in live)


def test_a_render_is_only_paid_for_once(space, seed, target):
    """The cache is the reason the store exists: the optimiser revisits vectors, the
    re-rank re-renders the shortlist, and a render is the only expensive thing."""
    probe = di()
    with Store() as store:
        store.start_run(Run(run_id="r"))
        evaluator = S.Evaluator(SyntheticRenderer(), target, probe, space,
                                store=store, run_id="r")
        first = evaluator.evaluate(seed)
        assert evaluator.renders == 1 and evaluator.cache_hits == 0

        again = evaluator.evaluate(seed)
        assert evaluator.renders == 1, "the second call must not render"
        assert evaluator.cache_hits == 1
        assert again.total == pytest.approx(first.total)

        evaluator.evaluate(seed, use_cache=False)
        assert evaluator.renders == 2, "an explicit repeat must bypass the cache"
        assert evaluator.cache_hits == 1


def test_nonreproducible_screen_measures_objective_repeatability(space, seed, target):
    """A 25 Hz dB outlier is not a scalar-objective floor."""
    from dataclasses import replace

    class DeterministicButDeclaredVariable(SyntheticRenderer):
        def metadata(self):
            return replace(
                super().metadata(), reproducible=False, band_noise_db=5.228794,
            )

    evaluator = S.Evaluator(
        DeterministicButDeclaredVariable(), target, di(), space,
    )
    screened = S.screen(
        evaluator, seed, only=[f"{AMP}Amp/{AMP}Volume"],
    )

    assert screened.floor == S.SENSITIVITY_FLOOR
    assert evaluator.renders == 7, "five repeats plus two range endpoints"


def test_nonreproducible_screen_uses_the_range_of_several_varying_renders(
    space, seed, target,
):
    from dataclasses import replace

    class AlternatingRenderer(SyntheticRenderer):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def metadata(self):
            return replace(super().metadata(), reproducible=False)

        def render(self, di, settings=None, **kwargs):
            result = super().render(di, settings, **kwargs)
            self.calls += 1
            # A real non-reproducible backend changes samples under identical
            # inputs. Alternate a plainly audible level so the scalar score—not
            # metadata—has an observed range the screen must retain.
            gain = 0.5 if self.calls == S.NONREPRODUCIBLE_SCREEN_SAMPLES else 1.0
            return replace(result, audio=result.audio * gain)

    evaluator = S.Evaluator(AlternatingRenderer(), target, di(), space)
    screened = S.screen(
        evaluator, seed, only=[f"{AMP}Amp/{AMP}Volume"],
    )

    assert evaluator.renders == 7
    assert screened.floor > S.SENSITIVITY_FLOOR


def test_incomplete_nonreproducible_floor_uses_metadata_and_is_reported(
    space, seed, target,
):
    from dataclasses import replace
    from match.renderer import RenderError

    class OneFailedRepeat(SyntheticRenderer):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def metadata(self):
            return replace(
                super().metadata(), reproducible=False, band_noise_db=0.6,
            )

        def render(self, di, settings=None, **kwargs):
            self.calls += 1
            if self.calls == 3:
                raise RenderError("deliberate repeat failure")
            return super().render(di, settings, **kwargs)

    evaluator = S.Evaluator(OneFailedRepeat(), target, di(), space)
    screened = S.screen(
        evaluator, seed, only=[f"{AMP}Amp/{AMP}Volume"],
    )

    assert screened.repeat_failures == 1
    assert screened.floor == pytest.approx(0.2)  # 0.6 dB / the 3 dB band scale


def test_nonreproducible_renderer_never_reads_a_cached_score(space, seed, target):
    from dataclasses import replace

    class VariableContract(SyntheticRenderer):
        def metadata(self):
            return replace(super().metadata(), reproducible=False,
                           band_noise_db=0.2)

    with Store() as store:
        store.start_run(Run(run_id="variable"))
        evaluator = S.Evaluator(
            VariableContract(), target, di(), space,
            store=store, run_id="variable",
        )
        evaluator.evaluate(seed)
        evaluator.evaluate(seed)

        assert evaluator.renders == 2
        assert evaluator.cache_hits == 0


def test_paired_profile_requires_and_scores_the_reference_waveform(space, seed):
    """The profile's 0.9 residual weight must reach a real production score.

    A fingerprint cannot supply this term. With the samples supplied, the exact
    deterministic render reaches the residual floor while a wrong tone does not.
    """
    probe = di()
    renderer = SyntheticRenderer()
    settings = dict(seed)
    settings[(f"{AMP}Amp", f"{AMP}Volume")] = 80.0
    helper = S.Evaluator(renderer, printed(probe), probe, space)
    reference = renderer.render(probe, helper._settings(settings)).audio
    target = printed(reference)

    with pytest.raises(S.SearchError, match="reference samples"):
        S.Evaluator(renderer, target, probe, space, profile="paired-v1")

    evaluator = S.Evaluator(renderer, target, probe, space,
                            profile="paired-v1", reference_audio=reference)
    exact = evaluator.evaluate(settings)
    wrong = evaluator.evaluate(seed)

    assert exact.objectives["residual"] == pytest.approx(0.0)
    assert wrong.objectives["residual"] > exact.objectives["residual"]
    assert exact.total < wrong.total


def test_the_same_vector_at_another_input_level_is_a_different_trial(space, seed,
                                                                    target):
    """Not a cache hit: a quieter DI drives the amp less hard, so it is a different
    render of the same parameters and it scores differently for a reason that has
    nothing to do with the parameters."""
    probe = di()
    with Store() as store:
        store.start_run(Run(run_id="r"))
        evaluator = S.Evaluator(SyntheticRenderer(), target, probe, space,
                                store=store, run_id="r")
        evaluator.evaluate(seed)
        evaluator.evaluate(seed, di=np.asarray(probe) * 0.5, offset_db=-6.0)

        assert evaluator.renders == 2 and evaluator.cache_hits == 0
        offsets = sorted(t.di_offset_db for t in store.trials("r"))
        assert offsets == [-6.0, 0.0]


def test_a_backend_a_parameter_is_unknown_to_is_not_sent_it(space, seed, target):
    """The synthetic chain models 45 of Morgan's 132 and refuses the rest outright,
    which is correct of it and would otherwise turn every trial into an error."""
    renderer = SyntheticRenderer()
    supported = {"/".join(key) if isinstance(key, tuple) else key
                 for key in renderer.parameter_specs()}
    evaluator = S.Evaluator(renderer, target, di(), space)
    sent = evaluator._settings(seed)

    assert sent, "something has to be sent"
    assert set(sent) <= supported
    unmodelled = [d.path for d in space.dimensions if d.path not in supported]
    assert unmodelled, "the fixture is pointless if the backend models everything"
    assert not (set(sent) & set(unmodelled))


def test_the_prior_terms_abstain_without_a_seed_to_deviate_from(space, seed, target):
    """`0.0` would tell the objective that every candidate is exactly what a person
    would have dialled. With nothing to deviate from there is no deviation."""
    without = S.Evaluator(SyntheticRenderer(), target, di(), space)
    assert without._prior_deviation(seed) is None
    assert without._complexity(seed) is None

    with_seed = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)
    assert with_seed._prior_deviation(seed) == pytest.approx(0.0)
    assert with_seed._complexity(seed) == pytest.approx(0.0)

    moved = dict(seed)
    moved[(f"{AMP}Amp", f"{AMP}Volume")] = 100.0
    assert with_seed._prior_deviation(moved) > 0.0
    assert 0.0 < with_seed._complexity(moved) < 1.0


# --- the screen -------------------------------------------------------------


def test_the_screen_costs_two_renders_per_parameter_and_says_which(space, seed,
                                                                  target):
    """The whole reason it is worth doing: the cost is knowable before it is spent,
    and it turns 125 dimensions into something CMA-ES can work in."""
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)
    s = S.screen(evaluator, seed)
    searched, frozen, probes, movement = s.searched, s.frozen, s.probes, s.movement

    candidates = len(searched) + len(frozen)
    assert candidates > 10, f"only {candidates} parameters were screened"
    assert evaluator.renders == 1 + 2 * candidates, (
        f"{evaluator.renders} renders for {candidates} parameters plus a baseline"
    )
    assert len(probes) == evaluator.renders
    assert searched, "some parameter has to move the objective"
    assert set(searched) & set(frozen) == set()
    # The movement of every parameter, not only the frozen ones: the report's most
    # useful column was a dash for every row the screen had kept, because `searched`
    # was a bare list and the number measured for it was discarded.
    assert set(movement) == set(searched) | set(frozen)
    assert all(path in movement for path in searched)

    # Strongest first: the order a caller reads, and the order CMA-ES benefits from
    # when its budget runs out mid-generation. Weakest-first spends the last renders
    # on the controls that matter least.
    moved = [movement[path] for path in searched]
    assert moved == sorted(moved, reverse=True), dict(zip(searched, moved))
    assert moved[0] > moved[-1], "the fixture needs a spread to order at all"


def test_the_screens_probes_are_candidates_not_waste(space, seed, target):
    """Forty renders that were paid for and scored. A parameter at an extreme is a
    legitimate parameter vector, and on one measured run a probe scored 0.525 while
    the whole CMA-ES stage found nothing better than 0.694."""
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)
    probes = S.screen(evaluator, seed).probes

    scored = [p for p in probes if p.objectives]
    assert len(scored) > 10
    assert all(p.values for p in scored), "a probe has to carry the vector it scored"
    # And they differ from each other, so they are genuinely different vectors.
    assert len({p.total for p in scored}) > 5


def test_the_screen_does_not_screen_switches_or_selectors(space, seed, target):
    """Turning an effect off changes what is *reachable* rather than shifting a
    value, so the topology loop owns them — and a gradient over a mic-type index is
    a gradient over the order somebody listed them in."""
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)
    s = S.screen(evaluator, seed)
    searched, frozen = s.searched, s.frozen

    seen = set(searched) | set(frozen)
    for dimension in space.dimensions:
        if dimension.switch or dimension.kind == "enum":
            assert dimension.path not in seen, dimension.path


def test_a_parameter_that_cannot_be_screened_is_frozen_but_not_called_inert(
        space, seed, target):
    """A render that failed at an extreme taught nothing about that parameter.
    Freezing it is still right; recording zero movement would be a claim it moved
    nothing, which is a measurement nobody made.

    Constructed rather than hoped for: the gate has to be *on* for its threshold to
    reach the sound at all, and at 0 dB it silences everything. An earlier version of
    this asserted the same thing with the gate off, where `gateThreshold` is dormant
    and never screened — so it was asserting about a parameter that was not there.
    """
    with_gate = dict(seed)
    with_gate[("parameters", "gateActive")] = True
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space,
                            recipe=with_gate)
    s = S.screen(evaluator, with_gate,
                 only=["parameters/gateThreshold", f"{AMP}Amp/{AMP}Volume"])
    searched, frozen, silences = s.searched, s.frozen, s.silences

    assert "parameters/gateThreshold" in frozen
    assert "parameters/gateThreshold" in silences, (
        "one extreme silenced the render, and that is a measured fact about the "
        "control rather than a failure to measure it"
    )
    assert f"{AMP}Amp/{AMP}Volume" in searched, "the control that does work survives"

    # And the movement recorded for it is the end that *did* render, measured against
    # the baseline. This was hardcoded to `0.0`, so the report printed `0.0000` under
    # "distance moved" for a control that had moved the score — on Morgan's own
    # `gateThreshold`, by four times the floor. A fabricated measurement is worse than
    # an absent one: a reader checking the freeze decision against it concludes the
    # screen was right.
    #
    # Recomputed here rather than compared against a literal, because a literal is the
    # same mistake one level up — the first version of this assertion asserted the 0.04
    # from another fixture's run and failed at 0.0021, which is a real measurement of
    # *this* target.
    dimension = next(d for d in space.dimensions
                     if d.path == "parameters/gateThreshold")
    low, high = dimension.bounds()
    live = high if silences["parameters/gateThreshold"] == low else low
    at_live = dict(with_gate)
    at_live[("parameters", "gateThreshold")] = dimension.quantise(live)
    expected = abs(evaluator.evaluate(at_live).total
                   - evaluator.evaluate(with_gate).total)

    moved = s.movement["parameters/gateThreshold"]
    assert moved == pytest.approx(expected), (
        f"recorded {moved:.4f} for a control whose live end moved the score by "
        f"{expected:.4f}"
    )
    assert moved > 0.0, "and it is not the zero the code used to invent"
    # It is frozen anyway, and for the stated reason rather than by the arithmetic
    # happening to fall out that way: with one extreme unscoreable the screen has no
    # bound on the control's effect, so it has nothing to hand an optimiser.
    assert "parameters/gateThreshold" not in searched


def test_the_screen_refuses_a_seed_it_cannot_measure_against(space, seed, target):
    """Every movement is measured against the baseline, so a baseline that produced
    nothing comparable means the screen has no scale at all.

    The seed itself has to be the silent one — a silent *target* still compares, its
    spectrum is simply the spectrum of silence.
    """
    silent = dict(seed)
    silent[("parameters", "gateActive")] = True
    silent[("parameters", "gateThreshold")] = 0.0
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=silent)
    assert evaluator.evaluate(silent).objectives == {}, "the seed must render silent"

    with pytest.raises(S.SearchError) as raised:
        S.screen(evaluator, silent)
    assert "nothing to compare against" in str(raised.value)


# --- topology ---------------------------------------------------------------


def test_topologies_are_a_product_and_default_to_the_seed_alone(space, seed):
    """Passing nothing returns the seed, which is the honest default: guessing which
    of Morgan's 32 switches are worth enumerating is not something this can know."""
    assert len(S.topologies(space, seed)) == 1

    two = S.topologies(space, seed, switches=["delay/delayActive"])
    assert len(two) == 2
    assert {v[("delay", "delayActive")] for v in two} == {False, True}

    four = S.topologies(space, seed, switches=["delay/delayActive",
                                              "reverb/reverbActive"])
    assert len(four) == 4

    selectors = S.topologies(space, seed, selectors=["cabParameters/leftMicType"])
    members = space.by_path("cabParameters", "leftMicType").members
    assert len(selectors) == len(members)


def test_a_continuous_parameter_is_refused_as_a_switch(space, seed):
    with pytest.raises(S.SearchError) as raised:
        S.topologies(space, seed, switches=[f"{AMP}Amp/{AMP}Volume"])
    assert "not a switch" in str(raised.value)


# --- the Pareto archive -----------------------------------------------------


def make(total: float, **dimensions) -> S.Candidate:
    objectives = {"total": total, **dimensions}
    return S.Candidate(values={"x": total}, objectives=objectives, total=total)


def test_domination_is_per_dimension_not_on_the_scalar():
    """The scalar is one weighting of many, and the point of an archive is to keep
    the answers a different weighting would prefer."""
    names = ["timbre", "ambience"]
    even = make(0.5, timbre=0.5, ambience=0.5)
    better = make(0.4, timbre=0.4, ambience=0.4)
    traded = make(0.5, timbre=0.1, ambience=0.9)

    assert better.dominates(even, names)
    assert not even.dominates(better, names)
    # A trade is not domination, however the scalars compare.
    assert not better.dominates(traded, names)
    assert not traded.dominates(better, names)


def test_a_dimension_only_one_side_measured_cannot_order_them():
    """Scoring an unmeasured dimension as zero would make every candidate that could
    not measure it look better than one that could."""
    names = ["timbre", "ambience"]
    both = make(0.5, timbre=0.5, ambience=0.5)
    partial = make(0.4, timbre=0.4)

    assert partial.dominates(both, names), "on timbre alone it is better"
    assert not both.dominates(partial, names)


def test_the_archive_thins_to_perceptually_distinct_entries():
    """A shortlist of five presets differing by 0.005 is a shortlist of one that
    wastes four listening comparisons.

    The crowd has to be mutually **non-dominated** for the thinning to be what
    collapses it. An earlier version gave every crowd member the same two dimensions,
    so they dominated each other and the front was one candidate before any thinning
    happened — the test passed with `distinct` removed entirely.
    """
    # Each trades a little timbre for a little ambience, so none dominates another,
    # and all five sit within 0.008 of each other in both.
    crowd = [make(0.50 + 0.001 * i,
                  timbre=0.50 + 0.002 * i, ambience=0.50 - 0.002 * i)
             for i in range(5)]
    apart = make(0.90, timbre=0.90, ambience=0.90)

    front = S.pareto(crowd, ["timbre", "ambience"], limit=5)
    for one in crowd:
        for other in crowd:
            if one is not other:
                assert not one.dominates(other, ["timbre", "ambience"]), (
                    "the crowd must be non-dominated or this tests domination"
                )
    assert len(front) == 1, f"five near-identical candidates are one: {front}"

    # And with the threshold below their separation, all five are kept — so the
    # thinning is doing the work rather than the domination check. Patched rather than
    # passed: `distinct` was an argument nothing but this line ever set, which made it
    # look tunable by callers who had no reason to tune it.
    with mock.patch.object(S, "DISTINCT_OBJECTIVE", 0.0):
        assert len(S.pareto(crowd, ["timbre", "ambience"], limit=5)) == 5

    # A genuinely different candidate survives the thinning.
    with_apart = S.pareto(crowd + [apart], ["timbre", "ambience"], limit=5)
    assert len(with_apart) == 1, "apart is dominated, so it is not on the front"
    totals = [c.total for c in with_apart]
    assert totals == sorted(totals), "kept in score order"


def test_the_shortlists_first_entry_is_the_recommendation():
    """`best` is what every caller prints and what the CLI writes as `match-1.json`,
    so returning the last of the shortlist instead of the first would recommend the
    worst candidate it found."""
    result = S.SearchResult(shortlist=[make(0.2, timbre=0.2), make(0.9, timbre=0.9)])
    assert result.best.total == pytest.approx(0.2)
    assert S.SearchResult().best is None


def test_separation_is_the_largest_gap_not_the_smallest():
    """Two presets that differ audibly in *one* respect are two presets. Taking the
    smallest gap instead collapses them: a pair 0.8 apart in timbre and identical in
    ambience separates by 0.005, so the archive keeps one of them."""
    # Non-dominated, or the archive drops one before the thinning is consulted: each
    # is better than the other somewhere.
    one = make(0.5, timbre=0.10, ambience=0.900)
    other = make(0.5, timbre=0.90, ambience=0.895)

    assert S._separation(one, other, ["timbre", "ambience"]) == pytest.approx(0.8)
    kept = S.pareto([one, other], ["timbre", "ambience"], limit=5)
    assert len(kept) == 2, "a big difference in one dimension is a real difference"


def test_the_archive_ignores_candidates_that_never_scored():
    front = S.pareto([S.Candidate(values={}), make(0.4, timbre=0.4)], ["timbre"])
    assert len(front) == 1 and front[0].total == pytest.approx(0.4)


# --- robustness -------------------------------------------------------------


def test_the_rerank_orders_by_the_worst_input_level(space, seed, target):
    """A preset that matches at one input level and falls apart at another is not a
    match. Ordered by the worst rather than the mean, on purpose."""
    probe = di()
    evaluator = S.Evaluator(SyntheticRenderer(), target, probe, space, recipe=seed)
    louder = dict(seed)
    louder[(f"{AMP}Amp", f"{AMP}Volume")] = 95.0
    shortlist = [evaluator.evaluate(seed), evaluator.evaluate(louder)]
    before = evaluator.renders

    reranked, caveats = S.robustness_rerank(evaluator, shortlist)

    assert evaluator.renders == before + 2 * len(shortlist), (
        "two extra renders per candidate, one per offset"
    )
    for candidate in reranked:
        assert set(candidate.by_level) == {-6.0, 0.0, 6.0}
        assert candidate.worst_level == max(candidate.by_level.values())
    worsts = [c.worst_level for c in reranked]
    assert worsts == sorted(worsts)
    assert isinstance(caveats, list)


def test_the_rerank_really_shifts_the_input_by_six_decibels(space, seed, target):
    """The `by_level` keys are labels. `10 ** (offset / 20)` mutated to `/ 10` makes the
    gain 3.98× instead of 2.0× — so every "±6 dB of input level" in the report, the CLI
    and the caveats becomes a statement about ±12 dB, and breakup depends strongly on
    level. The keys were checked and the signal was not.
    """
    probe = np.asarray(di(), dtype=np.float64)
    reference = float(np.sqrt(np.mean(probe ** 2)))
    seen = []

    class Watching(SyntheticRenderer):
        def render(self, di_samples, settings, **kwargs):
            array = np.asarray(di_samples, dtype=np.float64)
            seen.append(float(np.sqrt(np.mean(array ** 2))) / reference)
            return super().render(di_samples, settings, **kwargs)

    evaluator = S.Evaluator(Watching(), target, probe, space, recipe=seed)
    candidate = evaluator.evaluate(seed)
    seen.clear()
    S.robustness_rerank(evaluator, [candidate])

    ratios = sorted(round(value, 4) for value in seen)
    expected = sorted(round(10.0 ** (offset / 20.0), 4)
                      for offset in S.ROBUSTNESS_OFFSETS_DB)
    assert ratios == expected, (
        f"the DI was scaled by {ratios}, which is "
        f"{[round(20 * math.log10(r), 1) for r in ratios]} dB, not "
        f"{list(S.ROBUSTNESS_OFFSETS_DB)}"
    )


def test_a_stateful_backend_scores_each_shortlist_level_more_than_once(
    space, seed, target,
):
    """One render is a sample when the backend is not a function of its inputs, and
    a shortlist ordered on samples publishes an ordering it cannot support."""
    from dataclasses import replace

    class Stateful(SyntheticRenderer):
        def metadata(self):
            return replace(super().metadata(), reproducible=False,
                           band_noise_db=0.2)

    evaluator = S.Evaluator(Stateful(), target, di(), space, recipe=seed)
    louder = dict(seed)
    louder[(f"{AMP}Amp", f"{AMP}Volume")] = 95.0
    shortlist = [evaluator.evaluate(seed), evaluator.evaluate(louder)]
    before = evaluator.renders

    reranked, _ = S.robustness_rerank(evaluator, shortlist)

    # Three observations of each of three levels, less the one the search already
    # paid for at the reference level.
    per_candidate = 2 * S.SHORTLIST_REPLICATES + (S.SHORTLIST_REPLICATES - 1)
    assert evaluator.renders == before + per_candidate * len(shortlist)
    for candidate in reranked:
        assert candidate.replicates == S.SHORTLIST_REPLICATES
        assert set(candidate.by_level) == {-6.0, 0.0, 6.0}
        assert set(candidate.by_level_spread) == {-6.0, 0.0, 6.0}


def test_a_reproducible_backend_is_not_made_to_render_the_same_thing_twice(
    space, seed, target,
):
    """A second render of a deterministic backend is a copy of the first."""
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)
    candidate = evaluator.evaluate(seed)
    before = evaluator.renders

    S.robustness_rerank(evaluator, [candidate])

    assert evaluator.renders == before + len(S.ROBUSTNESS_OFFSETS_DB)
    assert candidate.replicates == 1
    assert candidate.by_level_spread == {}


def test_replicates_are_averaged_while_levels_are_still_taken_at_their_worst():
    """The two words are the design: variation between renders of the same settings
    is the backend's and gets averaged, variation across input level is the preset's
    and gets the worst case. Taking the worst of both would rank presets by which
    one drew the unluckiest render."""
    import itertools

    from match.renderer import RenderMetadata

    scores = itertools.chain([0.40, 0.60], itertools.repeat(0.50))

    class Drifting(SyntheticRenderer):
        def metadata(self):
            return RenderMetadata(renderer_id="synthetic", sample_rate=48000,
                                  block_size=512, reproducible=False,
                                  band_noise_db=0.2)

    evaluator = S.Evaluator(Drifting(), None, di(), S.Space([], {}), recipe={})
    evaluator.evaluate = lambda *args, **kwargs: S.Candidate(  # type: ignore
        values={}, objectives={"total": 1.0}, total=next(scores))
    candidate = S.Candidate(values={}, objectives={"total": 0.5}, total=0.50)

    S.robustness_rerank(evaluator, [candidate], offsets_db=(6.0,))

    assert candidate.by_level[0.0] == pytest.approx(0.50), (
        "0.50 handed in, 0.40 and 0.60 rendered: the mean, not the worst"
    )
    assert candidate.by_level_spread[0.0] == pytest.approx(0.20)
    # +6 dB drew 0.50 three times, so it is the quieter level — and the candidate's
    # worst is still the max across levels rather than the max across renders.
    assert candidate.by_level[6.0] == pytest.approx(0.50)
    assert candidate.worst_level == pytest.approx(0.50), (
        "0.60 was observed, but at a level whose mean is 0.50: worst across "
        "levels, mean across replicates"
    )


def _ranked(worst: float, spread: float, observations: int = 3) -> "S.Candidate":
    """A candidate whose worst level is `worst`, measured with `spread` there."""
    candidate = S.Candidate(values={}, objectives={}, total=worst)
    candidate.by_level = {0.0: worst - 0.05, 6.0: worst}
    candidate.by_level_spread = {6.0: spread}
    candidate.by_level_observations = {0.0: observations, 6.0: observations}
    candidate.replicates = observations
    return candidate


def test_two_candidates_inside_the_backends_own_variation_are_not_ranked():
    """Something has to come first, but a reader choosing what to audition is
    entitled to know the gap is smaller than the evidence can resolve."""
    best, second = _ranked(0.500, 0.09), _ranked(0.530, 0.08)

    inside = S._indistinguishable([best, second], S.SHORTLIST_REPLICATES)
    outside = S._indistinguishable([best, second], 1)

    assert any("not evidence" in caveat for caveat in inside)
    assert any("0.030 apart" in caveat for caveat in inside)
    assert outside == [], "a backend that repeats itself has no such doubt"


def test_a_wobble_at_a_level_that_decides_nothing_does_not_blur_the_ranking():
    """Pooling every level's spread let a −6 dB wobble call two candidates a coin
    toss when both worst levels were measured with no spread at all."""
    best, second = _ranked(1.0, 0.0), _ranked(3.0, 0.0)
    for candidate in (best, second):
        candidate.by_level[-6.0] = 0.2
        candidate.by_level_spread[-6.0] = 0.5

    assert S._indistinguishable([best, second], S.SHORTLIST_REPLICATES) == []


def test_the_threshold_is_the_error_of_the_means_not_the_spread_of_renders():
    """Averaging three observations is most of the point of replicating them. A
    rule that compared the gap against a raw single-render spread called a
    three-sigma separation indistinguishable two times in five."""
    spread = 0.30                       # peak-to-peak of three renders
    sigma = spread / S._RANGE_TO_SIGMA[3]
    resolution = math.sqrt(2) * sigma / math.sqrt(3)

    inside = S._indistinguishable(
        [_ranked(0.50, spread), _ranked(0.50 + resolution * 0.8, spread)],
        S.SHORTLIST_REPLICATES,
    )
    outside = S._indistinguishable(
        [_ranked(0.50, spread), _ranked(0.50 + resolution * 1.5, spread)],
        S.SHORTLIST_REPLICATES,
    )

    assert inside and not outside
    assert resolution < spread, (
        "the point of the fix: the means resolve better than one render does"
    )


def test_a_level_that_loses_a_render_says_so_and_counts_what_it_got(
    space, seed, target,
):
    """Three asked for, two obtained, and the report has to say two — the field
    exists because a mean of three and a single render differ, so a field that
    says three and means one is worse than not having it."""
    from dataclasses import replace

    from match.renderer import RenderError

    class OneBadRender(SyntheticRenderer):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def metadata(self):
            return replace(super().metadata(), reproducible=False,
                           band_noise_db=0.2)

        def render(self, di_samples, settings=None, **kwargs):
            self.calls += 1
            if self.calls == 2:
                raise RenderError("deliberate failure")
            return super().render(di_samples, settings, **kwargs)

    evaluator = S.Evaluator(OneBadRender(), target, di(), space, recipe=seed)
    candidate = evaluator.evaluate(seed)

    _, caveats = S.robustness_rerank(evaluator, [candidate])

    assert candidate.by_level_observations[0.0] < S.SHORTLIST_REPLICATES
    assert set(candidate.by_level) == {-6.0, 0.0, 6.0}, (
        "a level that lost one render of three is measured, not unknown"
    )
    assert any("thinner evidence" in caveat for caveat in caveats)


def test_the_budget_reserves_what_a_stateful_rerank_actually_spends(space, seed,
                                                                    target):
    """The reserve is a promise about the fixed costs, and replication made the
    re-rank four times what the promise said."""
    from dataclasses import replace

    class Stateful(SyntheticRenderer):
        def metadata(self):
            return replace(super().metadata(), reproducible=False,
                           band_noise_db=0.2)

    with Store() as store:
        store.start_run(Run(run_id="reserve"))
        result = S.search(Stateful(), target, di(), space, seed, budget=120,
                          shortlist=2, store=store, run_id="reserve",
                          rng=np.random.default_rng(0))

    assert result.renders <= 120, result.caveats
    assert all(candidate.by_level_observations.get(0.0) == S.SHORTLIST_REPLICATES
               for candidate in result.shortlist)


def test_the_rerank_says_when_it_changed_the_order(seed):
    """The whole value of the stage is in this caveat: without it a caller reads the
    reordered list and never learns that the reference-level winner lost.

    Constructed rather than rendered, which is why `_rerank_and_explain` is split out:
    getting a real search to produce a fragile winner on demand is not something a
    test can arrange.
    """
    fragile = S.Candidate(values=dict(seed), objectives={"total": 0.1}, total=0.1)
    fragile.by_level = {0.0: 0.1, -6.0: 9.0, 6.0: 0.2}
    steady = S.Candidate(values=dict(seed), objectives={"total": 0.5}, total=0.5)
    steady.by_level = {0.0: 0.5, -6.0: 0.5, 6.0: 0.5}
    reranked, caveats = S._rerank_and_explain([fragile, steady])

    assert reranked[0] is steady
    assert any("only works at one input level" in c for c in caveats), caveats


# --- the whole pass ---------------------------------------------------------


def test_a_search_improves_the_objective_and_accounts_for_its_budget(space, seed,
                                                                     target):
    """The end-to-end claim, with the arithmetic checked rather than trusted."""
    probe = di()
    with Store() as store:
        store.start_run(Run(run_id="r", budget=90))
        before = S.Evaluator(SyntheticRenderer(), target, probe, space,
                             recipe=seed).evaluate(seed).total
        result = S.search(SyntheticRenderer(), target, probe, space, seed,
                          budget=90, shortlist=2, store=store, run_id="r",
                          rng=np.random.default_rng(0))

        assert result.shortlist, result.caveats
        assert result.best.total < before, f"{before:.3f} -> {result.best.total:.3f}"
        assert result.searched and result.frozen is not None
        # The renders the search reports are the trials the store holds.
        assert store.summary("r")["trials"] == result.renders
        assert all(c.by_level for c in result.shortlist), "everything is re-ranked"


def test_a_budget_too_small_for_the_optimiser_says_so_rather_than_pretending(
        space, seed, target):
    """Screening has a fixed cost and the re-rank has another, and both are paid
    before CMA-ES gets what is left. A run that could not search has to say it."""
    result = S.search(SyntheticRenderer(), target, di(), space, seed,
                      budget=1, shortlist=1, rng=np.random.default_rng(0))

    assert any("optimiser never ran" in c for c in result.caveats), result.caveats
    assert any("Raise --budget" in c for c in result.caveats)
    assert result.shortlist, "the seed and the screen still give an answer"


def test_going_over_budget_is_reported_rather_than_hidden(space, seed, target):
    """The screen's cost is 2 per parameter and cannot be part-paid, so a budget
    below it is exceeded. Silently exceeding it would make every render count in
    every report a guess."""
    result = S.search(SyntheticRenderer(), target, di(), space, seed,
                      budget=4, shortlist=1, rng=np.random.default_rng(0))

    assert result.renders > 4
    assert any("against a budget of 4" in c for c in result.caveats), result.caveats


def test_a_zero_budget_is_refused_at_the_door(space, seed, target):
    with pytest.raises(S.SearchError):
        S.search(SyntheticRenderer(), target, di(), space, seed, budget=0)


def test_frozen_parameters_keep_their_seed_value_through_the_search(space, seed,
                                                                   target):
    """"Frozen" has to mean *held*, not merely unmentioned: a decode that filled the
    unsearched dimensions from a vector would move them all to whatever CMA-ES last
    sampled."""
    result = S.search(SyntheticRenderer(), target, di(), space, seed,
                      budget=80, shortlist=1, rng=np.random.default_rng(0))
    assert result.frozen, "some parameter should be frozen on this material"

    winner = result.best.values
    for path in result.frozen:
        module, _, key = path.rpartition("/")
        assert winner[(module, key)] == seed[(module, key)], path


def test_a_second_reference_is_not_served_the_first_ones_score(space, seed):
    """One store, one directory, two runs — which is the designed workflow, since
    `open_store` gives every `--out-dir` one `trials.sqlite3`. Keyed on the render
    address the second run got the first run's objectives against different audio,
    wrote zero trial rows, and reported a headline scored against the wrong
    recording."""
    probe = di()
    scorer = S.Evaluator(SyntheticRenderer(), printed(probe), probe, space)
    first_audio = refchain.render(probe, scorer._settings(
        {**seed, (f"{AMP}Amp", f"{AMP}Volume"): 80.0}))
    second_audio = refchain.render(probe, scorer._settings(
        {**seed, (f"{AMP}Amp", f"{AMP}Treble"): 15.0}))
    first = printed(first_audio)
    second = printed(second_audio)

    with Store() as store:
        store.start_run(Run(run_id="one"))
        store.start_run(Run(run_id="two"))
        a = S.Evaluator(SyntheticRenderer(), first, probe, space, store=store,
                        run_id="one", recipe=seed)
        b = S.Evaluator(SyntheticRenderer(), second, probe, space, store=store,
                        run_id="two", recipe=seed)
        truth = S.Evaluator(SyntheticRenderer(), second, probe, space, recipe=seed)

        a.evaluate(seed)
        scored = b.evaluate(seed)

        assert b.cache_hits == 0 and b.renders == 1
        assert scored.total == pytest.approx(truth.evaluate(seed).total)
        assert store.summary("two")["trials"] == 1, "a real trial, not a phantom hit"

        # And the same profile change is also a different score.
        paired = S.Evaluator(SyntheticRenderer(), second, probe, space, store=store,
                            run_id="two", recipe=seed, profile="paired-v1",
                            reference_audio=second_audio)
        paired.evaluate(seed)
        assert paired.cache_hits == 0

        # The waveform is part of a paired score even when the fingerprint object
        # is unchanged. Otherwise a caller correcting a mismatched DI/reamp pair in
        # the same out-dir would receive the old residual from cache.
        other_waveform = S.Evaluator(
            SyntheticRenderer(), second, probe, space, store=store,
            run_id="two", recipe=seed, profile="paired-v1",
            reference_audio=first_audio)
        other_waveform.evaluate(seed)
        assert other_waveform.cache_hits == 0

        # And so is a different *seed*, which is the third component of the key and the
        # one nothing checked. `prior_deviation` and `complexity` are distances from the
        # recipe, so the same parameters against the same reference under two seeds are
        # two different scores — which is exactly what happens when a second run in the
        # same --out-dir uses another template, or adds --no-invert.
        moved_seed = {**seed, (f"{AMP}Amp", f"{AMP}Bass"): 90.0}
        other_recipe = S.Evaluator(SyntheticRenderer(), first, probe, space,
                                   store=store, run_id="one", recipe=moved_seed)
        rescored = other_recipe.evaluate(seed)
        assert other_recipe.cache_hits == 0, (
            "the seed is part of what a score means, so it has to be part of the key"
        )
        assert rescored.total != pytest.approx(a.evaluate(seed).total), (
            "and the two scores differ, or there would be nothing to get wrong"
        )

        # While a genuine repeat of the same question is still free.
        before = a.renders
        a.evaluate(seed)
        assert a.renders == before


def test_two_excerpts_of_one_file_have_different_score_keys(seed):
    """The file hash is the same; the measured samples are not."""
    import numpy as np

    source = io.from_samples(np.concatenate([
        fx.band_limited(seconds=2.0, high=1200, seed=3),
        fx.band_limited(seconds=2.0, low=2500, high=8000, seed=4),
    ]), SR)
    short = fingerprint(source, regime="probe", excerpt_s=1.0)
    long = fingerprint(source, regime="probe", excerpt_s=3.0)
    assert short.source["sha256"] == long.source["sha256"]
    assert S._scoring_key("render", short, "unpaired-v1", seed) != \
        S._scoring_key("render", long, "unpaired-v1", seed)


def test_a_seed_value_of_exactly_zero_is_not_read_as_absent(space, seed, target):
    """`_get(seed, d) or d.bounds()[0]` treated 0.0 as missing, because 0.0 is falsy,
    so a parameter sitting at zero started the optimiser at the *bottom* of its range.
    The bundled `Example_Clean_PR12.xml` has 35 continuous dimensions at exactly 0.0,
    including all nine EQ bands whose range is −12..+12 — so zero is the middle."""
    band = space.by_path(f"{AMP}EQ", f"{AMP}EQBand1")
    assert band.bounds() == (-12.0, 12.0), "zero has to be mid-range for this to bite"

    at_zero = dict(seed)
    at_zero[(f"{AMP}EQ", f"{AMP}EQBand1")] = 0.0
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=at_zero)
    evaluated, _ = S.refine(evaluator, at_zero, [band.path], 12,
                            rng=np.random.default_rng(0))

    assert evaluated, "one generation has to run"
    gains = [c.values[(f"{AMP}EQ", f"{AMP}EQBand1")] for c in evaluated]
    # Sampling starts at the mean, so the samples straddle zero rather than piling up
    # against −12. With the bug every one of them sat in the bottom of the range.
    assert min(gains) < 0.0 < max(gains), gains
    assert sum(gains) / len(gains) == pytest.approx(0.0, abs=4.0), gains


def test_the_budget_reserves_every_fixed_cost(space, seed, target):
    """The per-variant seed render was not reserved, so a run overspent by exactly the
    variant count — one with no switches enumerated, thirty-two with five."""
    for budget in (98, 60):
        result = S.search(SyntheticRenderer(), target, di(), space, seed,
                          budget=budget, shortlist=3,
                          rng=np.random.default_rng(0))
        assert result.renders <= budget, (
            f"budget {budget}: spent {result.renders}"
        )


def test_the_vector_the_caller_started_from_is_on_the_shortlist(space, seed):
    """`fallbacks=` is what stops a near-perfect template only getting worse: matching
    the bundled PR12 preset against a render of *itself* scored 0.069 for the template,
    0.593 after the inversion, and 0.408 after the search recovered what it could — and
    0.408 was the answer handed back. Nothing in the suite passed `fallbacks=` at all,
    so deleting the line that evaluates them survived every test including the CLI's.

    Constructed the same way the regression was: the target is a render of `seed`, so
    `seed` is the exact answer and the search cannot beat it. It only appears in the
    shortlist if it was put there.
    """
    probe = di()
    scorer = S.Evaluator(SyntheticRenderer(), printed(probe), probe, space)
    perfect = printed(refchain.render(probe, scorer._settings(seed)))

    result = S.search(SyntheticRenderer(), perfect, probe, space,
                      {**seed, (f"{AMP}Amp", f"{AMP}Volume"): 20.0},
                      budget=90, shortlist=1, fallbacks=[seed],
                      rng=np.random.default_rng(0))

    assert result.best is not None
    assert result.best.total < 0.05, (
        f"the exact answer was handed in as a fallback and the best was "
        f"{result.best.total:.4f}; it was not considered"
    )


def test_the_screens_probes_are_used_and_not_only_returned(space, seed, target):
    """A probe is a real parameter vector that was rendered and scored, and on the run
    §12c records one of them (0.525) beat everything CMA-ES found (0.694). `screen`
    returning them was tested; `search` putting them in the candidate pool was not, so
    `candidates = list(probes)` → `[]` re-binned a third of the budget undetectably.

    Made observable by putting the answer *at an extreme*: the target is a render of the
    seed with one control at the top of its range, so the screen's probe for that control
    is nearly the exact answer and CMA-ES starting from mid-range will not beat it. The
    budget is large enough to reach the optimiser, which is where the mutation lives —
    an earlier version of this test used a budget so small that the run took the
    "optimiser never ran" branch, which has its own copy of the line and passed.
    """
    probe = di()
    scorer = S.Evaluator(SyntheticRenderer(), printed(probe), probe, space)
    extreme = dict(seed)
    volume = space.by_path(f"{AMP}Amp", f"{AMP}Volume")
    extreme[(f"{AMP}Amp", f"{AMP}Volume")] = volume.bounds()[1]
    at_extreme = printed(refchain.render(probe, scorer._settings(extreme)))

    evaluator = S.Evaluator(SyntheticRenderer(), at_extreme, probe, space, recipe=seed)
    screened = S.screen(evaluator, seed)
    probe_totals = {round(c.total, 9) for c in screened.probes if c.objectives}
    assert len(probe_totals) > 5, "the screen has to have scored several vectors"

    result = S.search(SyntheticRenderer(), at_extreme, probe, space, seed,
                      budget=evaluator.renders + 40, shortlist=3,
                      rng=np.random.default_rng(0))

    assert result.unsearched is None, "this has to reach the optimiser to be a test"
    assert result.shortlist, "something has to come back"
    assert round(result.best.total, 9) in probe_totals, (
        f"the answer sits at a control's extreme, which the screen rendered and scored, "
        f"and the best returned was {result.best.total:.4f} — not one of the "
        f"{len(probe_totals)} probes already paid for"
    )


def test_every_vector_the_optimiser_asks_for_is_inside_the_declared_range():
    """The property the bounds handling actually has, asserted on the samples rather than
    on an internal.

    `refine` used to carry a measured table claiming that clipping the distribution's
    *mean* as well as the sample mattered a thousandfold, and removing the clip survived
    every test — because the clip was dead. The new mean is `weights @ selected` with
    positive weights summing to one over rows that were already clipped, so it is a
    convex combination of points in the box and cannot leave it. Reproducing the table
    gives identical digits either way, and with the optimum placed outside the box both
    variants pin the mean at exactly 0.000.

    Which leaves the real invariant: no vector handed to a renderer is out of range. That
    is what a plugin would reject, and it is checked here on the arithmetic itself so it
    holds for any weights a future change might use.
    """
    for mu in (1, 3, 8):
        raw = np.array([math.log(mu + 0.5) - math.log(i + 1) for i in range(mu)])
        weights = raw / raw.sum()
        assert (weights > 0).all(), "a negative weight would break the convexity"
        assert weights.sum() == pytest.approx(1.0)

        # Selected rows are always clipped samples, so the extremes are the corners.
        rng = np.random.default_rng(0)
        for _ in range(50):
            selected = np.clip(rng.standard_normal((mu, 6)) * 3.0, 0.0, 1.0)
            mean = weights @ selected
            assert mean.min() >= 0.0 and mean.max() <= 1.0, mean


def test_a_frozen_parameter_that_did_move_is_not_called_inert(space, seed, target):
    """The caveat said four parameters "moved the objective by less than 0.01" when
    their measured movements were 0.062, 0.062, 0.109 and 0.070 — every one well clear
    of the floor and cut by the quantile instead. The report repeated the claim in
    prose next to a table showing 0.109."""
    result = S.search(SyntheticRenderer(), target, di(), space, seed, budget=80,
                      shortlist=1, rng=np.random.default_rng(0))

    below = [p for p, v in result.frozen.items()
             if not np.isnan(v) and v < S.SENSITIVITY_FLOOR]
    weakest = [p for p, v in result.frozen.items()
               if not np.isnan(v) and v >= S.SENSITIVITY_FLOOR]

    for caveat in result.caveats:
        if "moved the objective by less than" in caveat:
            assert below, f"nothing was below the floor, but: {caveat}"
            assert caveat.startswith(f"{len(below)} of"), caveat
    if weakest:
        assert any("weakest" in c for c in result.caveats), (
            f"{len(weakest)} parameters were cut by the quantile with no caveat: "
            f"{result.caveats}"
        )


def test_the_optimiser_stops_when_its_step_is_finer_than_the_controls(space, seed,
                                                                     target):
    """A step floor was the first attempt and it guaranteed the waste it was meant to
    prevent: 1e-4 in unit space is 0.0024 dB against an EQ band's 0.25 dB quantum, so
    once the step reached the floor every render repeated one already made."""
    paths = [f"{AMP}EQ/{AMP}EQBand{i}" for i in range(1, 5)]
    dimensions = [S._dimension(space, path) for path in paths]
    step = S._quantisation_step(dimensions)
    assert 0.0 < step < 0.01, step

    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)
    evaluated, caveats = S.refine(evaluator, seed, paths, 400,
                                  rng=np.random.default_rng(0))
    if len(evaluated) < 400:
        assert any("finer than the smallest change" in c for c in caveats), caveats

    # And it does not stop *immediately*, which is what the assertion above allows on
    # its own: inverting the comparison to `step > quantisation_step` satisfies every
    # line of it — the caveat is there, the budget is under-spent — while ending the
    # search after one generation. Measured on this fixture: 53 renders of 120 and a
    # score three times worse. So the count of generations is the thing to pin.
    lambda_ = S.generation_size(len(paths))
    assert len(evaluated) > 2 * lambda_, (
        f"the optimiser ran {len(evaluated) // lambda_} generation(s) of "
        f"{lambda_} against a 400-render budget; a well-posed run does not stop there"
    )


def test_the_optimiser_gets_better_within_a_single_refine(space, seed, target):
    """Recombining the *worst* μ samples instead of the best passed every test in this
    file: the end-to-end winner is often one of the screen's probes, so nothing checked
    that CMA-ES itself improves. Measured, that mutation cost 0.144 → 0.463.

    Compared first generation against last rather than best-so-far, because best-so-far
    is monotone by construction and would pass with the selection reversed.
    """
    paths = [f"{AMP}Amp/{AMP}Volume", f"{AMP}Amp/{AMP}Treble", f"{AMP}Amp/{AMP}Bass"]
    lambda_ = S.generation_size(len(paths))
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)
    evaluated, _ = S.refine(evaluator, seed, paths, 8 * lambda_,
                            rng=np.random.default_rng(0))
    assert len(evaluated) >= 4 * lambda_, "not enough generations to compare"

    totals = [c.total for c in evaluated]
    first = min(totals[:lambda_])
    last = min(totals[-lambda_:])
    assert last < first, (
        f"the last generation's best was {last:.4f} against the first's {first:.4f} — "
        f"the distribution is not moving towards better samples"
    )


def test_the_screen_freezes_the_weakest_movers_and_not_the_strongest(space, seed,
                                                                    target):
    """`ordered[cut:]` reversed to `ordered[:len(ordered) - cut]` froze the two
    strongest movers, and every test passed — the caveat still said "the weakest 25%"
    and the report still printed the numbers under that heading. The invariant is an
    ordering between the two sets, and nothing asserted it."""
    s = S.screen(evaluator_for(space, target, seed), seed)
    frozen_measured = [v for p, v in s.frozen.items()
                       if not S._isnan(v) and p not in s.silences]
    searched_measured = [s.movement[p] for p in s.searched if p in s.movement]
    assert frozen_measured and searched_measured, "both sets have to be non-empty"

    assert min(searched_measured) >= max(frozen_measured) - 1e-12, (
        f"a frozen parameter moved the score by {max(frozen_measured):.4f} while a "
        f"searched one moved it by only {min(searched_measured):.4f}"
    )


def test_the_quantile_cut_is_the_documented_fraction():
    """The constant can be changed to 0.75 and only the caveat's wording follows, so
    the arithmetic is pinned here instead: the cut is a fraction of what cleared the
    floor, taken weakest-first."""
    above = {f"p{i}": 0.1 * (i + 1) for i in range(8)}
    ordered = sorted(above, key=lambda p: above[p])
    cut = int(len(ordered) * S.SENSITIVITY_QUANTILE)

    assert cut == 2, f"25% of 8 is 2, not {cut}"
    kept = ordered[cut:]
    assert kept == ["p2", "p3", "p4", "p5", "p6", "p7"]
    assert min(above[p] for p in kept) > max(above[p] for p in ordered[:cut])


def evaluator_for(space, target, seed):
    return S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)


def test_a_candidate_never_re_rendered_does_not_crash_the_reorder():
    """`worst_level` is None for it, and formatting that with `:.3f` raised — on
    exactly the constructed input this function was split out to make testable."""
    unmeasured = S.Candidate(values={}, objectives={"total": 0.2}, total=0.2)
    steady = S.Candidate(values={}, objectives={"total": 0.5}, total=0.5)
    steady.by_level = {0.0: 0.5, -6.0: 0.5, 6.0: 0.5}

    reranked, caveats = S._rerank_and_explain([unmeasured, steady])
    assert reranked[0] is steady, "a measured candidate outranks an unmeasured one"
    assert isinstance(caveats, list)


def test_a_bypassed_section_is_never_sent_to_the_backend(space, seed, target):
    """`_settings` filters through `active()`, and without it a render is charged for
    moving controls inside a bypassed section: 26 settings became 45, twelve of them
    delay parameters sent while `delayActive` was False."""
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space)
    off = dict(seed)
    off[("delay", "delayActive")] = False
    off[("delay", "delayTime")] = 400.0
    off[("delay", "delayMix")] = 70.0

    sent = evaluator._settings(off)
    assert "delay/delayActive" in sent, "the switch itself is still stated"
    assert "delay/delayTime" not in sent, sent
    assert "delay/delayMix" not in sent, sent

    on = dict(off)
    on[("delay", "delayActive")] = True
    with_delay = evaluator._settings(on)
    assert "delay/delayTime" in with_delay
    assert len(with_delay) > len(sent), "switching it on reaches more controls"


def test_a_control_the_backend_cannot_be_driven_with_is_not_screened(space, seed,
                                                                    target):
    """Screening it renders the backend's indifference rather than the control, and
    reports 0.0000 movement — a measurement of something that was never driven, which
    the screen's own docstring says it must not do."""
    renderer = SyntheticRenderer()
    supported = {"/".join(k) if isinstance(k, tuple) else k
                 for k in renderer.parameter_specs()}
    unmodelled = [d.path for d in space.active(seed)
                  if not d.switch and d.kind != "enum" and d.path not in supported]
    assert unmodelled, "the fixture is pointless if the backend models everything"

    evaluator = S.Evaluator(renderer, target, di(), space, recipe=seed)
    s = S.screen(evaluator, seed)
    searched, frozen, movement = s.searched, s.frozen, s.movement

    for path in unmodelled:
        assert path not in searched, path
        assert path not in frozen, f"{path} was reported as measured at 0.0"
        assert path not in movement, path


def test_decoding_a_sample_holds_every_parameter_it_did_not_search(space, seed):
    """"Frozen" has to mean *held*. Decoding from an empty dict instead left the
    unsearched dimensions absent, so a CMA-ES winner would have carried two values
    where the seed had ninety-two — and the end-to-end test could not see it, because
    the winner is usually a screen probe rather than a decoded vector."""
    paths = [f"{AMP}Amp/{AMP}Volume", f"{AMP}Amp/{AMP}Treble"]
    dimensions = [S._dimension(space, path) for path in paths]

    decoded = S._decode(space, dimensions, [1.0, 0.0], seed)

    assert len(decoded) == len(seed), "every key the seed had"
    assert decoded[(f"{AMP}Amp", f"{AMP}Volume")] == pytest.approx(100.0)
    assert decoded[(f"{AMP}Amp", f"{AMP}Treble")] == pytest.approx(0.0)
    # And everything else is exactly what it was.
    for key, value in seed.items():
        if key in {(d.module, d.key) for d in dimensions}:
            continue
        assert decoded[key] == value, key


def test_the_optimisers_first_step_is_the_documented_one(space, seed, target):
    """`INITIAL_SIGMA` is the width of the first generation, and both directions are
    wrong in a way no assertion caught: at 0.001 every sample lands on the seed and
    the search does nothing, at 5.0 they saturate against the bounds."""
    assert S.INITIAL_SIGMA == 0.15
    paths = [f"{AMP}Amp/{AMP}Volume"]
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)

    def volumes(sigma):
        evaluated, _ = S.refine(evaluator, seed, paths, 12, sigma=sigma,
                                rng=np.random.default_rng(0))
        return [c.values[(f"{AMP}Amp", f"{AMP}Volume")] for c in evaluated]

    default = volumes(S.INITIAL_SIGMA)
    spread = max(default) - min(default)
    assert 5.0 < spread < 80.0, (
        f"the first generation has to explore without saturating: {sorted(default)}"
    )
    seeded = seed[(f"{AMP}Amp", f"{AMP}Volume")]
    assert min(default) < seeded < max(default), "and it straddles the seed"

    tiny = volumes(0.001)
    assert max(tiny) - min(tiny) < 1.0, f"0.001 explores nothing: {sorted(tiny)}"
    huge = volumes(5.0)
    assert sum(1 for v in huge if v in (0.0, 100.0)) > len(huge) // 2, (
        f"5.0 saturates against the bounds: {sorted(huge)}"
    )


def test_a_generation_that_all_failed_stops_rather_than_chasing_it(space, seed,
                                                                  target):
    """Moving the mean towards a failure is moving it towards nothing. Without the
    early stop a backend that fails every render spent 56 of a 60-render budget and
    emitted no caveat at all."""
    class Broken(SyntheticRenderer):
        def _render(self, di, settings):
            from match.renderer import RenderError

            raise RenderError("this backend is broken")

    evaluator = S.Evaluator(Broken(), target, di(), space, recipe=seed)
    evaluated, caveats = S.refine(evaluator, seed, [f"{AMP}Amp/{AMP}Volume"], 60,
                                  rng=np.random.default_rng(0))

    assert evaluator.renders < 20, (
        f"{evaluator.renders} renders spent on a backend that failed every one"
    )
    assert any("failed to render" in c for c in caveats), caveats
