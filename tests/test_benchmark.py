"""M4's exit criterion, checked as a measurement rather than as a claim.

The benchmark is the thing that decides whether M4 ships, so it is the thing most
worth distrusting: a harness that measures the wrong pipeline reports the wrong
verdict with complete confidence. That happened once — the `full` arm searched from
the recipe seed instead of the inverted one, so it was search-*only*, and it reported
DOES NOT SHIP against a pipeline that in fact works. `test_the_arms_are_nested` is
that bug.

The end-to-end run here is small on purpose: three targets at a 30-render budget.
The real numbers come from `scripts/benchmark_match.py --targets 50 --budget 300`,
which is about an hour and is not a CI job.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

import numpy as np

from match import benchmark as B
from match import space as SP
from match.renderer_synth import SyntheticRenderer
from tests import fixtures_audio as fx

AMP = "sw50r"


@pytest.fixture(scope="module")
def space():
    return SP.build("morgan", amp=AMP)


@pytest.fixture(scope="module")
def seed(space):
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


# --- sampling ----------------------------------------------------------------


def test_a_sampled_vector_is_legal_and_covers_the_ranges(space):
    """Uniform over each declared range, not over plausible presets: a benchmark over
    tones a person would dial is a benchmark over the easy cases."""
    rng = np.random.default_rng(1)
    vectors = [B.random_vector(space, rng) for _ in range(40)]

    for values in vectors:
        for (module, key), value in values.items():
            dimension = space.by_path(module, key)
            if dimension.switch:
                assert isinstance(value, bool)
            elif dimension.kind == "enum":
                assert str(value) in dimension.members
            else:
                low, high = dimension.bounds()
                assert low <= value <= high, (dimension.path, value)

    # And it really does move: a sampler that returned one point would make the
    # whole benchmark a benchmark of one target.
    volumes = {v[(f"{AMP}Amp", f"{AMP}Volume")] for v in vectors}
    assert len(volumes) > 20, f"only {len(volumes)} distinct volumes in 40 samples"


def test_a_section_switch_is_never_sampled_off(space):
    """A target with the cab section bypassed is a target with no cabinet, which is
    not a tone anyone is asking to match."""
    rng = np.random.default_rng(2)
    for _ in range(30):
        values = B.random_vector(space, rng)
        assert values[("cabParameters", "sectionActive")] is True


def test_sampling_respects_what_the_backend_models(space):
    """A target rendered with a parameter the backend refuses is not a target."""
    supported = list(SyntheticRenderer().parameter_specs())
    keys = {"/".join(k) if isinstance(k, tuple) else k for k in supported}
    values = B.random_vector(space, np.random.default_rng(3), supported=supported)

    assert values
    for module, key in values:
        assert f"{module}/{key}" in keys


# --- the error measures ------------------------------------------------------


def test_continuous_and_discrete_errors_are_kept_apart(space, seed):
    """A knob 8% out is nearly right; the wrong microphone is wrong. Averaging them
    produces a number that means neither."""
    truth = dict(seed)
    truth[(f"{AMP}Amp", f"{AMP}Volume")] = 100.0
    truth[("cabParameters", "leftMicType")] = 1

    found = dict(seed)
    found[(f"{AMP}Amp", f"{AMP}Volume")] = 100.0
    found[("cabParameters", "leftMicType")] = 0

    mae, accuracy = B.parameter_error(space, truth, found)
    assert mae == pytest.approx(0.0, abs=1e-6), "every continuous value matches"
    assert accuracy is not None and accuracy < 1.0, "the mic type does not"


def test_the_mae_is_normalised_so_units_can_be_averaged(space, seed):
    """10 Hz out of a 1500 ms delay and 40% out on a knob are not comparable in their
    own units, and a mean over raw values is dominated by whichever has the widest
    range."""
    half_a_knob = dict(seed)
    volume = space.by_path(f"{AMP}Amp", f"{AMP}Volume")
    low, high = volume.bounds()
    half_a_knob[(f"{AMP}Amp", f"{AMP}Volume")] = (low + high) / 2.0

    full_travel = dict(seed)
    full_travel[(f"{AMP}Amp", f"{AMP}Volume")] = high

    one = B.parameter_error(space, half_a_knob, full_travel,
                            only=[volume.path])[0]
    assert one == pytest.approx(0.5, abs=0.01), (
        "half the declared range is 0.5 whatever the unit is"
    )


def test_a_parameter_only_one_side_has_is_not_counted_as_an_error(space, seed):
    partial = {(f"{AMP}Amp", f"{AMP}Volume"): 70.0}
    mae, accuracy = B.parameter_error(space, seed, partial)
    assert mae is not None
    # Only the one shared continuous dimension contributed.
    assert mae == pytest.approx(
        abs(70.0 - seed[(f"{AMP}Amp", f"{AMP}Volume")]) / 100.0, abs=1e-6)


# --- the verdict -------------------------------------------------------------


def outcome(arm: str, index: int, objective: float, **fields) -> B.Outcome:
    return B.Outcome(arm=arm, target_index=index, objective=objective,
                     parameter_mae=0.2, selector_accuracy=0.6, **fields)


def test_the_verdict_needs_both_baselines_beaten():
    """The plan's wording, and the right test: the objective is what the pipeline
    optimises, so it is what has to improve."""
    result = B.BenchmarkResult(outcomes=[
        outcome("recipe", 0, 2.0), outcome("inversion", 0, 1.0),
        outcome("full", 0, 0.5),
    ])
    ships, reasons = result.verdict()
    assert ships
    assert any("beats recipe" in r for r in reasons)
    assert any("beats inversion" in r for r in reasons)

    # Beating one is not enough.
    worse = B.BenchmarkResult(outcomes=[
        outcome("recipe", 0, 2.0), outcome("inversion", 0, 0.4),
        outcome("full", 0, 0.5),
    ])
    ships, reasons = worse.verdict()
    assert not ships
    assert any("does NOT beat inversion" in r for r in reasons)


def test_a_missing_baseline_is_not_a_pass():
    """An arm that was not run has not been beaten, and defaulting to "ships" would
    let `--arms full` alone declare victory."""
    result = B.BenchmarkResult(outcomes=[outcome("full", 0, 0.5)])
    ships, reasons = result.verdict()
    assert not ships
    assert any("was not run" in r for r in reasons)


def test_too_many_failures_sinks_it_however_good_the_mean():
    """An arm that fails a third of its targets and does beautifully on the rest is
    not better than one that succeeds everywhere."""
    outcomes = [outcome("recipe", i, 2.0) for i in range(10)]
    outcomes += [outcome("inversion", i, 1.0) for i in range(10)]
    outcomes += [outcome("full", i, 0.1) for i in range(7)]
    outcomes += [B.Outcome(arm="full", target_index=i, failed=True, error="died")
                 for i in range(7, 10)]

    result = B.BenchmarkResult(outcomes=outcomes)
    ships, reasons = result.verdict()
    assert not ships
    assert any("30% of targets" in r for r in reasons)


def test_the_verdict_says_the_mae_is_not_part_of_it():
    """Reported and deliberately not gated, because the plugin's controls are not
    identifiable from its output — and nobody should have to guess whether that was a
    decision or an omission."""
    result = B.BenchmarkResult(outcomes=[
        outcome("recipe", 0, 2.0), outcome("inversion", 0, 1.0),
        outcome("full", 0, 0.5),
    ])
    _, reasons = result.verdict()
    assert any("part of this gate" in r for r in reasons)
    assert any("parameter MAE" in r for r in reasons)


def test_the_summary_averages_over_successes_and_says_how_many_there_were():
    outcomes = [outcome("full", 0, 0.2), outcome("full", 1, 0.4),
                B.Outcome(arm="full", target_index=2, failed=True, error="died")]
    summary = B.BenchmarkResult(outcomes=outcomes).summarise("full")

    assert summary["targets"] == 3
    assert summary["failures"] == 1
    assert summary["failure_rate"] == pytest.approx(1 / 3)
    assert summary["objective"] == pytest.approx(0.3), "the mean of the two that ran"
    assert summary["objective_median"] == pytest.approx(0.3)


def test_the_table_shows_every_number_and_never_a_single_score():
    result = B.BenchmarkResult(outcomes=[
        outcome("recipe", 0, 2.0), outcome("inversion", 0, 1.0),
        outcome("full", 0, 0.5, renders=300),
    ])
    table = B.format_table(result)

    for header in ("param MAE", "selector", "objective", "renders", "fail%"):
        assert header in table
    assert "SHIPS" in table
    assert "300" in table


def test_an_unknown_arm_is_refused_by_name():
    with pytest.raises(B.BenchmarkError) as raised:
        B.compare_baselines(SyntheticRenderer(), SP.build("morgan"),
                            fx.plucks(seconds=0.5), {}, arms=("magic",))
    assert "magic" in str(raised.value)


# --- end to end -------------------------------------------------------------


def test_the_arms_are_nested_so_each_stage_shows_what_it_adds(space, seed):
    """The bug this exists for: the `full` arm searched from the recipe seed instead
    of the inverted one, so it measured search-*only* and scored worse than inversion
    alone — reporting DOES NOT SHIP for a mistake in the harness.

    Asserted structurally as well as by score, because a run where the search happens
    to be very good would hide it.
    """
    probe = fx.plucks(seconds=2.0, gap=0.9, seed=13)
    renderer = SyntheticRenderer()
    result = B.compare_baselines(renderer, space, probe, seed, targets=2, budget=30,
                                 rng=np.random.default_rng(5), amp=AMP)

    recipe = result.summarise("recipe")
    inversion = result.summarise("inversion")
    full = result.summarise("full")

    assert recipe["targets"] == inversion["targets"] == full["targets"] == 2
    assert inversion["renders"] == 2, "one render per target, the seed's"
    assert full["renders"] > inversion["renders"], (
        "the full arm pays for the inversion too, so it cannot cost less"
    )
    assert inversion["objective"] < recipe["objective"], (
        f"the calculated step has to help: {recipe['objective']} -> "
        f"{inversion['objective']}"
    )
    assert full["objective"] <= inversion["objective"], (
        f"the search starts from the inversion, so it cannot be worse: "
        f"{inversion['objective']} -> {full['objective']}"
    )


def test_a_silent_target_is_skipped_rather_than_blamed_on_an_arm(space, seed):
    """A legal parameter vector can produce silence — a gate threshold above the
    signal — and counting that as a failure of every arm would report a failure rate
    that belongs to the sampler."""
    probe = fx.plucks(seconds=1.5, gap=0.9, seed=7)
    result = B.compare_baselines(SyntheticRenderer(), space, probe, seed,
                                 targets=3, budget=20, arms=("recipe",),
                                 rng=np.random.default_rng(4), amp=AMP)

    counted = len(result.by_arm("recipe"))
    assert counted + len(result.caveats) == 3, (
        "every target is either scored or explained"
    )
    for caveat in result.caveats:
        assert "silent" in caveat


def test_a_sampled_value_lands_on_the_step_grid(space):
    """"Legal" for `apply_spec` means inside the range *and* on the step. Without the
    quantise call 2240 of 40 targets' continuous values were off-grid — targets that
    are not presets the plugin can be given."""
    rng = np.random.default_rng(1)
    off_grid = []
    for _ in range(40):
        for (module, key), value in B.random_vector(space, rng).items():
            dimension = space.by_path(module, key)
            if dimension.switch or dimension.kind == "enum" or not dimension.quantum:
                continue
            low, high = dimension.bounds()
            if value in (low, high):
                continue      # an endpoint is legal whether or not it is on the grid
            steps = value / dimension.quantum
            if abs(steps - round(steps)) > 1e-6:
                off_grid.append((dimension.path, value))
    assert not off_grid, f"{len(off_grid)} off-grid values, e.g. {off_grid[:3]}"


def test_the_sampler_switches_effects_on_sometimes_and_not_always(space):
    """At half, the average target has four effects running and the objective is
    dominated by whether the search found the delay; at zero, every target is
    effect-free and the switches are never exercised at all."""
    rng = np.random.default_rng(2)
    states = []
    for _ in range(30):
        for (module, key), value in B.random_vector(space, rng).items():
            if space.by_path(module, key).switch and not key.endswith("sectionActive"):
                states.append(bool(value))

    on = sum(states) / len(states)
    assert 0.2 < on < 0.55, f"{on:.3f} of switches were on"


def test_a_failed_outcome_is_not_averaged_into_the_mean():
    """An arm's mean is over what it measured. A failure carrying a number would drag
    it — and the failure rate is reported beside the mean precisely so the mean can
    stay clean."""
    good = [outcome("full", 0, 0.2), outcome("full", 1, 0.4)]
    broken = B.Outcome(arm="full", target_index=2, failed=True, error="died",
                       objective=9.0, parameter_mae=0.9)

    summary = B.BenchmarkResult(outcomes=good + [broken]).summarise("full")
    assert summary["objective"] == pytest.approx(0.3), (
        "the mean of the two that ran, not of all three"
    )
    assert summary["parameter_mae"] == pytest.approx(0.2)
    assert summary["failures"] == 1


def test_a_tie_is_not_beating():
    """`<=` would ship a pipeline that spends 300 renders to arrive exactly where the
    baseline already was."""
    tied = B.BenchmarkResult(outcomes=[
        outcome("recipe", 0, 0.5), outcome("inversion", 0, 0.5),
        outcome("full", 0, 0.5),
    ])
    ships, reasons = tied.verdict()
    assert not ships, reasons
    assert any("does NOT beat" in r for r in reasons)


def test_the_arms_are_nested_structurally_not_only_by_score(space, seed):
    """The score assertion tolerates the harness bug: with `full` searching from the
    recipe seed it still came out at 1.649 against inversion's 2.042, so `full <=
    inversion` held while the arm being measured was search-only. What pins it is that
    the full arm's answer starts from the inversion's."""
    probe = fx.plucks(seconds=1.5, gap=0.9, seed=13)
    renderer = SyntheticRenderer()
    from match import invert, search

    target_values = dict(seed)
    target_values[("sw50rAmp", "sw50rVolume")] = 85.0
    scorer = search.Evaluator(renderer, None, probe, space)
    rendered = renderer.render(probe, scorer._settings(target_values))
    from analysis import io
    from analysis.fingerprint import fingerprint

    target = fingerprint(io.from_samples(rendered.audio, 48000), regime="probe",
                         excerpt_s=None)

    inverted, spent = B._invert_from(renderer, target, probe, space, seed,
                                     "unpaired-v1", invert, search, "morgan", AMP)
    assert spent == 1, "one render, the seed's, so the delta can be measured"
    assert inverted != dict(seed), "the inversion has to change something"

    # And `full` is that, plus a search. Asserted through the arm itself.
    found, renders = B._run_arm("full", renderer, target, probe, space, seed, 30,
                                "unpaired-v1", invert, search,
                                np.random.default_rng(0), "morgan", AMP)
    assert renders > spent, "the full arm pays for the inversion as well"
    # Every value the inversion set and the screen froze is still the inversion's,
    # which is only true if the search started from it.
    from match.space import _get

    carried = [path for path in ("parameters/outputGain",)
               if _get(inverted, tuple(path.split("/")))
               == _get(found, tuple(path.split("/")))]
    assert carried, (
        "the search started from the recipe seed, not from the inversion: "
        f"outputGain is {_get(found, ('parameters', 'outputGain'))} against the "
        f"inversion's {_get(inverted, ('parameters', 'outputGain'))}"
    )


def test_an_unknown_amp_is_refused_before_the_first_target(space, seed):
    """`space.build` accepts any prefix and simply finds nothing, so `--amp nope` used
    to fail inside every arm once per target, with the cause visible only in --json."""
    with pytest.raises(B.BenchmarkError) as raised:
        B.compare_baselines(SyntheticRenderer(), space, fx.plucks(seconds=0.5),
                            seed, targets=1, budget=10, amp="nope")
    assert "not an amp in this space" in str(raised.value)
    assert "sw50r" in str(raised.value), "and it names the ones that are"
