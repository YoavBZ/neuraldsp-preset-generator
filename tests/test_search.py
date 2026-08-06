"""The four search stages, against targets built with the answer known.

Every test renders through the synthetic chain, so a "budget" here is small and
real: the point is not that CMA-ES converges — that is Hansen's problem, not this
repository's — but that each stage does the accounting it claims, spends what it
says it spends, and abstains where abstaining is right.
"""

from __future__ import annotations

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
    and it turns 126 dimensions into something CMA-ES can work in."""
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)
    searched, frozen, probes, movement, _ = S.screen(evaluator, seed)

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


def test_the_screens_probes_are_candidates_not_waste(space, seed, target):
    """Forty renders that were paid for and scored. A parameter at an extreme is a
    legitimate parameter vector, and on one measured run a probe scored 0.525 while
    the whole CMA-ES stage found nothing better than 0.694."""
    evaluator = S.Evaluator(SyntheticRenderer(), target, di(), space, recipe=seed)
    _, _, probes, _, _ = S.screen(evaluator, seed)

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
    searched, frozen, _, _, _ = S.screen(evaluator, seed)

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
    searched, frozen, _, _, silences = S.screen(
        evaluator, with_gate,
        only=["parameters/gateThreshold", f"{AMP}Amp/{AMP}Volume"])

    assert "parameters/gateThreshold" in frozen
    assert "parameters/gateThreshold" in silences, (
        "one extreme silenced the render, and that is a measured fact about the "
        "control rather than a failure to measure it"
    )
    assert f"{AMP}Amp/{AMP}Volume" in searched, "the control that does work survives"


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
    wastes four listening comparisons."""
    crowd = [make(0.50 + 0.001 * i, timbre=0.5 + 0.001 * i) for i in range(6)]
    apart = make(0.60, timbre=0.2, ambience=0.9)
    front = S.pareto(crowd + [apart], ["timbre", "ambience"], limit=5, distinct=0.02)

    assert len(front) <= 5
    totals = [c.total for c in front]
    assert totals == sorted(totals), "kept in score order"
    assert len(front) < len(crowd), "the near-duplicates must collapse"


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
    first = printed(refchain.render(probe, scorer._settings(
        {**seed, (f"{AMP}Amp", f"{AMP}Volume"): 80.0})))
    second = printed(refchain.render(probe, scorer._settings(
        {**seed, (f"{AMP}Amp", f"{AMP}Treble"): 15.0})))

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
                            run_id="two", recipe=seed, profile="paired-v1")
        paired.evaluate(seed)
        assert paired.cache_hits == 0

        # While a genuine repeat of the same question is still free.
        a.evaluate(seed)
        assert a.cache_hits == 1 and a.renders == 1


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


def test_a_candidate_never_re_rendered_does_not_crash_the_reorder():
    """`worst_level` is None for it, and formatting that with `:.3f` raised — on
    exactly the constructed input this function was split out to make testable."""
    unmeasured = S.Candidate(values={}, objectives={"total": 0.2}, total=0.2)
    steady = S.Candidate(values={}, objectives={"total": 0.5}, total=0.5)
    steady.by_level = {0.0: 0.5, -6.0: 0.5, 6.0: 0.5}

    reranked, caveats = S._rerank_and_explain([unmeasured, steady])
    assert reranked[0] is steady, "a measured candidate outranks an unmeasured one"
    assert isinstance(caveats, list)
