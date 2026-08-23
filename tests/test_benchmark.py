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
from match import search as S
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


def test_paired_compares_only_the_targets_both_arms_scored():
    """The one thing that makes the comparison mean anything, and it had no direct test:
    replacing the intersection with "every success in each arm" passed every test in this
    file and in the CLI's.

    Demonstrated with failure rates *inside* the 10% gate, so nothing else catches it:
    ten targets, the recipe arm fails one of them, and the full arm scores 3.0 on exactly
    that one. Unpaired, the verdict flips — and its own sentence then misstates its
    denominator.
    """
    outcomes = [outcome("recipe", i, 0.6) for i in range(9)]
    outcomes += [B.Outcome(arm="recipe", target_index=9, failed=True, error="died")]
    outcomes += [outcome("full", i, 0.5) for i in range(9)]
    outcomes += [outcome("full", 9, 3.0)]
    outcomes += [outcome("inversion", i, 0.9) for i in range(10)]
    result = B.BenchmarkResult(outcomes=outcomes)

    ours, theirs = result.paired("full", "recipe")
    assert len(ours) == len(theirs) == 9, (
        f"the recipe arm scored 9 targets and the full arm 10; pairing them gives 9, "
        f"not {len(ours)} and {len(theirs)}"
    )
    assert [o.target_index for o in ours] == [o.target_index for o in theirs]
    assert 9 not in [o.target_index for o in ours], (
        "target 9 has no recipe score, so the full arm's 3.0 on it is not comparable"
    )

    ships, reasons = result.verdict()
    assert ships, reasons
    beat = [r for r in reasons if "recipe" in r][0]
    assert "0.500 against 0.600" in beat, beat
    assert "9 targets" in beat, "and the sentence names the denominator it used"


def test_a_recovered_vector_that_scores_nothing_is_a_failure(space, seed):
    """`outcome.failed = True` in the "produced nothing comparable" branch, flipped to
    `False`, survived every test: `_mean` skips `None`, so the arm's mean is unchanged,
    the failure rate under-reports, and the >10% gate never fires on it.

    Run through `compare_baselines` rather than by constructing an `Outcome`, because the
    line is in `compare_baselines` — a hand-built row asserts the dataclass and not the
    branch that fills it. The renderer here returns silence for exactly the vector the
    `recipe` arm hands back, which is the seed, and renders the target normally.
    """
    probe = fx.plucks(seconds=1.0, gap=0.9, seed=3)
    scorer = S.Evaluator(SyntheticRenderer(), None, probe, space)
    seed_settings = scorer._settings(seed)

    class SilentOnTheSeed(SyntheticRenderer):
        def render(self, di_samples, settings, **kwargs):
            rendered = super().render(di_samples, settings, **kwargs)
            if settings == seed_settings:
                import dataclasses

                # `silent` and `peak` are derived from the audio, so zeroing it is the
                # whole of it — there is nothing to set separately.
                return dataclasses.replace(
                    rendered, audio=np.zeros_like(np.asarray(rendered.audio)))
            return rendered

    result = B.compare_baselines(SilentOnTheSeed(), space, probe, seed, targets=1,
                                 budget=20, arms=("recipe",), amp=AMP)
    summary = result.summarise("recipe")

    assert summary["targets"] == 1
    assert summary["failures"] == 1, (
        "the recovered vector rendered silent, so there is no objective and no success"
    )
    assert summary["failure_rate"] == pytest.approx(1.0)
    row, = result.outcomes
    assert row.objective is None and "nothing comparable" in (row.error or "")


def test_a_verdict_resting_on_few_shared_targets_says_so():
    """A verdict from 2 shared targets out of 10 reads exactly like one from 10 unless
    the coverage guard fires, and the guard's threshold can be zeroed with nothing
    failing."""
    outcomes = [outcome("recipe", i, 2.0) for i in range(10)]
    outcomes += [outcome("inversion", i, 2.0) for i in range(10)]
    # The full arm only reached two of them.
    outcomes += [outcome("full", i, 0.1) for i in range(2)]
    outcomes += [B.Outcome(arm="full", target_index=i, failed=True, error="died")
                 for i in range(2, 10)]

    ships, reasons = B.BenchmarkResult(outcomes=outcomes).verdict()
    assert not ships
    assert any("rests on less than it looks like" in r for r in reasons), reasons
    assert any("only 2 of 10 targets" in r for r in reasons), reasons


def test_the_failure_column_is_a_percentage():
    """It is headed `fail%`. Printing the fraction there shows `0` for an arm failing a
    quarter of its targets, while a reason line below the table says 25%."""
    outcomes = [outcome("full", i, 0.5) for i in range(3)]
    outcomes += [B.Outcome(arm="full", target_index=3, failed=True, error="died")]
    table = B.format_table(B.BenchmarkResult(outcomes=outcomes), arms=("full",))

    row = [line for line in table.splitlines() if line.strip().startswith("full")][0]
    assert "25" in row, f"a quarter failed and the fail% column says: {row}"


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
    assert recipe["renders"] == 2, "one final scoring render per target"
    assert inversion["renders"] == 4, (
        "one inversion probe and one final scoring render per target"
    )
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


def test_tone_king_structural_bypasses_stay_on_in_seed_and_targets():
    toneking = SP.build("toneking", amp="lead")
    seed = B.centre_seed(toneking)
    structural = {
        ("", "ampsActive"), ("", "cabSectionActive"),
        ("", "eqSectionActive"), ("", "pedalSectionActive"),
        ("", "timeSectionActive"),
    }

    assert all(seed[key] is True for key in structural)
    assert seed[("", "eqActive")] is True
    for index in range(20):
        sampled = B.random_vector(
            toneking, np.random.default_rng(index), base=seed,
        )
        assert all(sampled[key] is True for key in structural)


def test_tone_king_target_sampler_omits_the_unselected_channel():
    toneking = SP.build("toneking", amp="lead")
    seed = B.centre_seed(toneking)
    seed[("", "ampType")] = "Lead Channel"

    sampled = B.random_vector(
        toneking, np.random.default_rng(3), base=seed,
    )

    assert ("", "leadAmpVolume") in sampled
    assert ("", "rhythmAmpVolume") not in sampled


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
    found, renders, arm_caveats = B._run_arm(
        "full", renderer, target, probe, space, seed, 30, "unpaired-v1", invert,
        search, np.random.default_rng(0), "morgan", AMP)
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


def test_paired_benchmark_threads_each_targets_waveform_to_every_arm(space, seed):
    """A paired benchmark is only paired if both recovery and final scoring see
    the rendered target samples, not merely their fingerprint."""
    result = B.compare_baselines(
        SyntheticRenderer(), space, fx.plucks(seconds=1.2, gap=0.7, seed=21),
        seed, targets=1, budget=30, profile="paired-v1",
        arms=("recipe", "inversion", "full"), amp=AMP,
        rng=np.random.default_rng(4),
    )
    assert len(result.outcomes) == 3
    assert all(not item.failed for item in result.outcomes)
    assert all(item.objective is not None for item in result.outcomes)


def test_an_unknown_amp_is_refused_before_the_first_target(space, seed):
    """`space.build` accepts any prefix and simply finds nothing, so `--amp nope` used
    to fail inside every arm once per target, with the cause visible only in --json."""
    with pytest.raises(B.BenchmarkError) as raised:
        B.compare_baselines(SyntheticRenderer(), space, fx.plucks(seconds=0.5),
                            seed, targets=1, budget=10, amp="nope")
    assert "not a signal path" in str(raised.value)
    assert "sw50r" in str(raised.value), "and it names the ones that are"


def test_selector_based_signal_path_is_accepted_by_the_benchmark():
    """Validation must not use Morgan's amp_modules as the universal topology."""
    from packs.loader import load_pack

    class ToneKingContractRenderer(SyntheticRenderer):
        def parameter_specs(self):
            return load_pack("toneking").parameters

    toneking = SP.build("toneking", amp="lead")
    seed = B.centre_seed(toneking)

    result = B.compare_baselines(
        ToneKingContractRenderer(), toneking, fx.plucks(seconds=0.5), seed,
        targets=0, budget=10, arms=("recipe",), pack_id="toneking", amp="lead",
    )

    assert result.outcomes == []


def test_selector_based_seed_resolves_path_when_amp_is_omitted(monkeypatch):
    from packs.loader import load_pack

    class ToneKingContractRenderer(SyntheticRenderer):
        def parameter_specs(self):
            return load_pack("toneking").parameters

    toneking = SP.build("toneking")
    seed = B.centre_seed(toneking)
    seed[("", "ampType")] = "Lead Channel"
    seen = []
    from match import invert
    actual = invert.selected_signal_path

    def watching(pack_id, values):
        selected = actual(pack_id, values)
        seen.append(selected)
        return selected

    monkeypatch.setattr(invert, "selected_signal_path", watching)
    B.compare_baselines(
        ToneKingContractRenderer(), toneking, fx.plucks(seconds=0.5), seed,
        targets=0, budget=10, arms=("recipe",), pack_id="toneking",
    )

    assert seen == ["lead"]


def test_inferred_signal_path_is_pinned_when_sampling_targets(monkeypatch):
    from packs.loader import load_pack

    class ToneKingPassthrough(SyntheticRenderer):
        def __init__(self):
            super().__init__()
            self.seen = []

        def parameter_specs(self):
            return load_pack("toneking").parameters

        def _render(self, di, settings):
            self.seen.append(dict(settings or {}))
            return di

    toneking = SP.build("toneking")
    seed = B.centre_seed(toneking)
    seed[("", "ampType")] = "Lead Channel"
    monkeypatch.setattr(
        B, "random_vector",
        lambda *args, **kwargs: {("", "ampType"): "Rhythm Channel"},
    )
    renderer = ToneKingPassthrough()

    B.compare_baselines(
        renderer, toneking, fx.plucks(seconds=0.5), seed,
        targets=1, budget=10, arms=("recipe",), pack_id="toneking",
    )

    assert renderer.seen
    assert all(settings.get("ampType") == "Lead Channel"
               for settings in renderer.seen)


def test_a_renderer_with_no_pack_dimensions_is_refused_before_sampling():
    toneking = SP.build("toneking", amp="lead")
    seed = B.centre_seed(toneking)

    with pytest.raises(B.BenchmarkError, match="no searchable controls"):
        B.compare_baselines(
            SyntheticRenderer(), toneking, fx.plucks(seconds=0.5), seed,
            targets=0, budget=10, arms=("recipe",), pack_id="toneking",
            amp="lead",
        )


def test_a_target_depends_on_its_index_and_not_on_the_ones_before_it(space, seed):
    """§12i had to record that `--seed 0` does not pin individual targets, because
    the search drew a variable number of times from the generator that sampled
    them. Target *i* now depends on the seed and on *i* alone — which is also what
    lets targets run concurrently, since a shared generator makes execution order
    part of the answer."""
    import numpy as np

    def truths(targets, greedy):
        """Sample `targets` vectors, optionally burning draws in between."""
        streams = B._spawn_streams(np.random.default_rng(5), targets, np)
        out = []
        for index, stream in enumerate(streams):
            out.append(B.random_vector(space, stream, base=dict(seed)))
            if greedy:
                # Stands in for a search consuming an unpredictable number of
                # draws after this target was sampled. It must not move the next
                # target, whose stream is a different SeedSequence child.
                stream.random(index * 7 + 1)
        return out

    steady, disturbed = truths(4, greedy=False), truths(4, greedy=True)

    assert steady == disturbed, "a target must not move because of what preceded it"
    assert steady[0] != steady[1], "and the targets must still differ from each other"


def test_targets_run_concurrently_and_give_the_same_answer(space, seed):
    """The one parallel use §12j says is sound: targets are independent
    experiments, so each takes an instance for its whole run and every comparison
    it makes stays inside that instance. The answer must not depend on how many
    ran at once."""
    probe = fx.plucks(seconds=2.0, gap=0.9, seed=13)

    serial = B.compare_baselines(
        SyntheticRenderer(), space, probe, seed, targets=4, budget=12,
        arms=("recipe", "inversion"), rng=np.random.default_rng(3))
    parallel = B.compare_baselines(
        SyntheticRenderer(), space, probe, seed, targets=4, budget=12,
        arms=("recipe", "inversion"), rng=np.random.default_rng(3),
        workers=3, renderer_factory=SyntheticRenderer)

    def rows(result):
        return [(o.arm, o.target_index, o.objective, o.parameter_mae)
                for o in result.outcomes]

    assert serial.outcomes, (
        "a probe short enough to silence every target makes this test compare two "
        "empty lists — which is how three concurrency tests here passed against a "
        "bug that cost a 25% failure rate on the plugin"
    )
    assert rows(parallel) == rows(serial), (
        "same targets, same arms, same scores — and in index order, not the order "
        "they happened to finish in"
    )
    assert [o.target_index for o in parallel.outcomes] == sorted(
        o.target_index for o in parallel.outcomes)


def test_a_concurrent_run_reports_progress_once_per_target(space, seed):
    seen = []
    B.compare_baselines(
        SyntheticRenderer(), space, fx.plucks(seconds=2.0, gap=0.9, seed=13), seed,
        targets=4, budget=12, arms=("recipe",), rng=np.random.default_rng(3),
        workers=2,
        renderer_factory=SyntheticRenderer,
        progress=lambda done, total: seen.append((done, total)))

    assert [done for done, _ in seen] == [1, 2, 3, 4]
    assert {total for _, total in seen} == {4}


def test_every_render_a_target_makes_goes_to_its_own_instance(space, seed):
    """The invariant §12j requires, and the one the synthetic chain cannot check by
    comparing answers: a stateless reproducible renderer gives the same numbers
    whether or not the arms accidentally share one instance, which is how a shared
    renderer survived a passing test and only showed up as a state-file race on the
    real plugin."""
    import threading

    seen = {}

    class Tagged(SyntheticRenderer):
        def render(self, di_samples, settings=None, **kwargs):
            seen.setdefault(threading.current_thread().name, set()).add(id(self))
            return super().render(di_samples, settings, **kwargs)

    B.compare_baselines(
        Tagged(), space, fx.plucks(seconds=2.0, gap=0.9, seed=13), seed,
        targets=4, budget=12,
        arms=("recipe", "inversion"), rng=np.random.default_rng(3),
        workers=4, renderer_factory=Tagged)

    worker_threads = [name for name in seen if name != "MainThread"]
    assert worker_threads, "the targets must actually have run on worker threads"
    assert sum(len(ids) for ids in seen.values()) >= len(worker_threads), (
        "and they must have rendered something — see the empty-list trap above"
    )
    for name in worker_threads:
        assert len(seen[name]) == 1, (
            f"{name} rendered through {len(seen[name])} instances; a target's "
            f"comparisons must all happen on the one it borrowed"
        )


def test_a_target_that_dies_outside_its_arms_is_reported_not_dropped(space, seed):
    """A worker exception used to kill its thread and leave the target absent from
    a table that still claimed to have run it. At the documented 50 targets on 4
    workers that would have silently discarded most of the run."""
    class DiesOnTheTruthRender(SyntheticRenderer):
        calls = 0

        def render(self, di_samples, settings=None, **kwargs):
            type(self).calls += 1
            if type(self).calls == 2:
                raise OSError("deliberate, outside any arm")
            return super().render(di_samples, settings, **kwargs)

    DiesOnTheTruthRender.calls = 0
    result = B.compare_baselines(
        DiesOnTheTruthRender(), space, fx.plucks(seconds=2.0, gap=0.9, seed=13),
        seed, targets=3, budget=12, arms=("recipe",),
        rng=np.random.default_rng(3), workers=2,
        renderer_factory=DiesOnTheTruthRender)

    indices = {o.target_index for o in result.outcomes}
    assert indices == {0, 1, 2}, f"every target must appear, got {sorted(indices)}"
    failed = [o for o in result.outcomes if o.failed]
    assert len(failed) == 1 and "deliberate" in failed[0].error
    assert any("outside its arms" in c for c in result.caveats)


def test_a_control_exception_in_a_worker_reaches_the_caller(space, seed):
    """Raising it inside the child thread is not enough: threading sends it to
    `excepthook` and the caller otherwise sees only a generic missing-target error."""
    class Interrupted(SyntheticRenderer):
        def render(self, di_samples, settings=None, **kwargs):
            raise KeyboardInterrupt("user pressed ctrl-c")

    with pytest.raises(KeyboardInterrupt, match="ctrl-c"):
        B.compare_baselines(
            Interrupted(), space,
            fx.plucks(seconds=2.0, gap=0.9, seed=13), seed, targets=2,
            budget=12, arms=("recipe",), rng=np.random.default_rng(3),
            workers=2, renderer_factory=Interrupted)


def test_a_progress_callback_exception_reaches_the_caller(space, seed):
    def stop_after_one(done, total):
        raise RuntimeError(f"progress failed at {done}/{total}")

    with pytest.raises(RuntimeError, match="progress failed"):
        B.compare_baselines(
            SyntheticRenderer(), space,
            fx.plucks(seconds=2.0, gap=0.9, seed=13), seed, targets=2,
            budget=12, arms=("recipe",), rng=np.random.default_rng(3),
            workers=2, renderer_factory=SyntheticRenderer,
            progress=stop_after_one)


def test_the_pool_width_is_capped_by_the_target_count(space, seed):
    made = []

    def factory():
        made.append(1)
        return SyntheticRenderer()

    B.compare_baselines(
        SyntheticRenderer(), space,
        fx.plucks(seconds=2.0, gap=0.9, seed=13), seed, targets=1,
        budget=12, arms=("recipe",), rng=np.random.default_rng(3),
        workers=8, renderer_factory=factory)

    assert len(made) == 0, (
        "the caller's renderer is the one effective member; seven idle plugin "
        "instances would be pure startup cost"
    )


def test_workers_without_a_factory_are_refused_not_silently_serial(space, seed):
    with pytest.raises(B.BenchmarkError, match="renderer_factory"):
        B.compare_baselines(
            SyntheticRenderer(), space,
            fx.plucks(seconds=2.0, gap=0.9, seed=13), seed, targets=2,
            budget=12, arms=("recipe",), rng=np.random.default_rng(3),
            workers=2)


def test_per_target_streams_do_not_need_generator_spawn():
    """`Generator.spawn` requires NumPy 1.25; the project supports 1.24."""
    streams = B._spawn_streams(np.random.default_rng(7), 3, np)
    again = B._spawn_streams(np.random.default_rng(7), 3, np)

    assert [s.random() for s in streams] == [s.random() for s in again]
    assert len({s.random() for s in B._spawn_streams(
        np.random.default_rng(7), 3, np)}) == 3
