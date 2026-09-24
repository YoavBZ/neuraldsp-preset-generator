"""What the signal a search renders through costs, measured the same way each time.

`match.signal_benchmark` runs one pipeline per search signal on known-truth
targets. It is only a comparison of signals if everything else is the same:
the targets, the budget, the random numbers, the topology — and if every answer
is heard through the target's own signal rather than the one it searched with.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

import numpy as np

from match import benchmark as B
from match import signal_benchmark as SB
from match import space as SP
from match.renderer_synth import SyntheticRenderer
from scripts.match_preset import _seed_from_template
from tests import fixtures_audio as fx

ROOT = pathlib.Path(__file__).resolve().parents[1]
AMP = "sw50r"


@pytest.fixture(scope="module")
def space():
    return SP.build("morgan", amp=AMP)


@pytest.fixture(scope="module")
def topology(space):
    values, _ = _seed_from_template(
        ROOT / "samples" / "SW50R_Atlas_Topology.xml", space, "morgan")
    return SB.fixed_topology(space, AMP, values,
                             SyntheticRenderer().parameter_specs())


@pytest.fixture(scope="module")
def signals():
    target = fx.plucks(seconds=1.2, gap=0.7, seed=3) * 0.3
    return target, {"same": target,
                    "other": fx.plucks(seconds=1.2, gap=0.5, seed=9) * 0.3}


def _run(space, topology, target, signals, **overrides):
    options = dict(targets=2, budget=30, rng=np.random.default_rng(4),
                   pack_id="morgan", amp=AMP)
    options.update(overrides)
    return SB.compare_search_signals(SyntheticRenderer(), space, target, signals,
                                     topology, **options)


def test_the_topology_is_the_templates_switches_with_its_continuous_controls_centred(
        space, topology):
    discrete = {d.path for d in space.dimensions if not d.continuous}
    assert topology["discrete"], "a template fixes switches and selectors"
    assert set(topology["discrete"]) <= discrete
    assert topology["discrete"]["tremolo/tremoloActive"] is False
    for dimension in topology["dimensions"]:
        low, high = dimension.bounds()
        value = topology["seed"][(dimension.module, dimension.key)]
        assert value == dimension.quantise((low + high) / 2.0), dimension.path


def test_every_answer_is_heard_through_the_targets_own_signal(
        space, topology, signals, monkeypatch):
    """The whole point: an answer found through the noise probe is judged by how
    it sounds played through the guitar, not by how it sounds through noise."""
    target, named = signals
    real = B.scorer_candidates
    seen = []

    def checking(scorer, *args, **kwargs):
        seen.append(scorer.probe_di is target)
        return real(scorer, *args, **kwargs)

    monkeypatch.setattr(B, "scorer_candidates", checking)
    outcomes = _run(space, topology, target, named)

    assert len(outcomes) == 4, "two targets by two signals"
    assert seen and all(seen), "every final score renders from the target DI"
    assert all(not o.failed for o in outcomes), [o.error for o in outcomes]
    assert all(o.objective is not None and o.search_belief is not None
               for o in outcomes)


def test_every_signal_searches_with_the_same_random_numbers(
        space, topology, signals, monkeypatch):
    from match import search as search_module

    target, named = signals
    real = search_module.search
    states = []

    def recording(*args, **kwargs):
        states.append(kwargs["rng"].bit_generator.state["state"]["state"])
        return real(*args, **kwargs)

    monkeypatch.setattr(search_module, "search", recording)
    _run(space, topology, target, named)

    assert len(states) == 4
    assert states[0] == states[1] and states[2] == states[3]
    assert states[0] != states[2], "each target has its own stream"


def test_the_inversion_cannot_change_the_topology(
        space, topology, signals, monkeypatch):
    """Every arm's answer keeps the template's switches, so the arms differ only
    in the continuous values their searches found."""
    from match import invert

    target, named = signals
    real_invert, real_scores = invert.invert, B.scorer_candidates
    answers = []

    def switching(*args, **kwargs):
        result = real_invert(*args, **kwargs)
        result.values["tremolo/tremoloActive"] = True
        return result

    def recording(scorer, target_fp, values, *args, **kwargs):
        answers.append(values.get(("tremolo", "tremoloActive")))
        return real_scores(scorer, target_fp, values, *args, **kwargs)

    monkeypatch.setattr(invert, "invert", switching)
    monkeypatch.setattr(B, "scorer_candidates", recording)
    _run(space, topology, target, named, targets=1)

    # The neutral start, then each arm's inversion alone and its answer.
    assert answers == [False] * 5


def test_the_baselines_are_scored_beside_the_search_on_the_same_targets(
        space, topology, signals, monkeypatch):
    """The neutral start and each signal's inversion alone are heard through the
    target's own signal, and the inversion scored is the vector that signal's
    search starts from — so a search is paired with its own start, in-run."""
    from match import search as search_module

    target, named = signals
    real_search, real_scores = search_module.search, B.scorer_candidates
    starts, scored = [], []

    def recording_search(renderer, target_fp, probe, space_, start, **kwargs):
        starts.append(dict(start))
        return real_search(renderer, target_fp, probe, space_, start, **kwargs)

    def recording_scores(scorer, target_fp, values, *args, **kwargs):
        scored.append(dict(values))
        return real_scores(scorer, target_fp, values, *args, **kwargs)

    monkeypatch.setattr(search_module, "search", recording_search)
    monkeypatch.setattr(B, "scorer_candidates", recording_scores)
    outcomes = _run(space, topology, target, named, targets=1)

    assert scored[0] == topology["seed"], "the neutral start is scored first"
    assert starts == [scored[1], scored[3]], "each inversion is its search's start"
    neutral = {o.neutral_objective for o in outcomes}
    assert len(neutral) == 1 and None not in neutral, "one neutral score per target"
    assert all(o.inversion_objective is not None for o in outcomes)
    summary = SB.summarise(outcomes, reference="same")
    assert summary["other"]["neutral_objective_mean"] == round(neutral.pop(), 4)
    # Every score says which dimensions it came from, and they are the loss's own.
    for o in outcomes:
        for dimensions in (o.objective_dimensions, o.inversion_dimensions,
                           o.neutral_dimensions):
            assert "total" not in dimensions and {"timbre", "level"} <= set(dimensions)
    # And each answer is paired with its own baselines, in-run.
    for name in named:
        assert summary[name]["against_neutral"]["targets"] == 1
        assert summary[name]["against_inversion"]["targets"] == 1


def test_without_the_search_only_the_baselines_are_scored(
        space, topology, signals, monkeypatch):
    from match import search as search_module

    target, named = signals

    def refusing(*args, **kwargs):
        raise AssertionError("no search runs with run_search=False")

    monkeypatch.setattr(search_module, "search", refusing)
    outcomes = _run(space, topology, target, named, run_search=False)

    assert len(outcomes) == 4 and not any(o.failed for o in outcomes)
    assert all(o.objective is None and o.search_belief is None for o in outcomes)
    assert all(o.inversion_objective is not None and o.neutral_objective is not None
               for o in outcomes)
    summary = SB.summarise(outcomes, reference="same")
    assert summary["other"]["objective_mean"] is None
    assert "paired_against" not in summary["other"], "nothing to pair without answers"
    assert summary["other"]["inversion_objective_mean"] is not None


def test_a_baseline_that_cannot_be_scored_fails_its_row(
        space, topology, signals, monkeypatch):
    """Without the search, a row whose baseline produced no objective is a
    failure the summary counts, not a row that quietly leaves the mean."""
    target, named = signals
    monkeypatch.setattr(B, "scorer_candidates", lambda *args, **kwargs: [])
    outcomes = _run(space, topology, target, named, targets=1, run_search=False)

    assert all(o.failed and "baseline" in o.error for o in outcomes)
    assert SB.summarise(outcomes, reference="same")["other"]["failures"] == 1


def test_a_baseline_lost_beside_a_search_is_counted_not_failed(
        space, topology, signals, monkeypatch):
    """With the search on, an answer whose baselines could not be scored is still
    an answer; the summary says how many rows lack a baseline."""
    target, named = signals
    real = B.scorer_candidates
    calls = []

    def losing_baselines(scorer, target_fp, values, *args, **kwargs):
        calls.append(values)
        # The first scoring of a target is its neutral start.
        return [] if len(calls) == 1 else real(scorer, target_fp, values,
                                               *args, **kwargs)

    monkeypatch.setattr(B, "scorer_candidates", losing_baselines)
    outcomes = _run(space, topology, target, named, targets=1)

    assert not any(o.failed for o in outcomes)
    assert all(o.neutral_objective is None and o.objective is not None
               for o in outcomes)
    summary = SB.summarise(outcomes, reference="same")
    assert summary["other"]["baseline_failures"] == 1
    assert "against_neutral" not in summary["other"]
    assert summary["other"]["against_inversion"]["targets"] == 1


def test_the_summary_pairs_each_answer_with_its_own_baselines():
    outcomes = []
    for index, (answer, inversion, neutral) in enumerate(
            [(0.3, 0.5, 1.0), (0.6, 0.5, 1.2), (0.2, 0.4, 0.9)]):
        outcomes.append(SB.SignalOutcome(
            "noise", index, 0, objective=answer, inversion_objective=inversion,
            neutral_objective=neutral))
    noise = SB.summarise(outcomes, reference="noise")["noise"]

    assert noise["against_neutral"]["closer"] == 3
    assert noise["against_inversion"]["closer"] == 2
    assert noise["against_inversion"]["mean_change_fraction"] == pytest.approx(
        (1.1 - 1.4) / 1.4)
    assert noise["neutral_objective_median"] == 1.0
    assert "paired_against" not in noise, "the reference is not paired with itself"


def test_arms_take_turns_going_first(space, topology, signals):
    target, named = signals
    outcomes = _run(space, topology, target, named)
    first = {o.target_index: o.signal for o in outcomes if o.position == 0}
    assert first == {0: "same", 1: "other"}


def test_the_summary_pairs_every_signal_with_the_reference_by_target():
    outcomes = []
    for index, (same, noise) in enumerate([(0.3, 0.6), (0.4, 0.5), (0.5, 0.45)]):
        outcomes.append(SB.SignalOutcome("same", index, 0, objective=same,
                                         search_belief=same))
        outcomes.append(SB.SignalOutcome("noise", index, 1, objective=noise,
                                         search_belief=0.2))
    summary = SB.summarise(outcomes, reference="same")

    assert "paired_against" not in summary["same"]
    noise = summary["noise"]
    assert noise["paired_against"] == "same"
    assert noise["closer_than_reference"] == 1
    assert noise["paired_targets"] == 3
    assert noise["mean_change_fraction"] == pytest.approx((1.55 - 1.2) / 1.2)
    assert noise["search_belief_mean"] == 0.2


def test_a_run_needs_a_signal_and_an_amp(space, topology, signals):
    target, _ = signals
    with pytest.raises(SB.SignalBenchmarkError, match="at least one"):
        _run(space, topology, target, {})
    with pytest.raises(SB.SignalBenchmarkError, match="which amp"):
        _run(space, topology, target, {"same": target}, amp=None)


def _cli(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "benchmark_search_signal.py"),
         *map(str, args)], cwd=ROOT, capture_output=True, text=True)


def test_the_cli_writes_every_signal_and_pairs_them_with_the_first(tmp_path):
    target = tmp_path / "target.wav"
    fx.write_wav(target, fx.plucks(seconds=1.2, gap=0.7, seed=3) * 0.3)
    out = tmp_path / "signals.json"
    done = _cli("--amp", AMP, "--template",
                ROOT / "samples" / "SW50R_Atlas_Topology.xml",
                "--target-di", target, "--signal", "same", "--signal", "noise",
                "--signal", "noise-at-di-level", "--targets", "1", "--budget", "30",
                "--json", out)
    assert done.returncode == 0, done.stderr

    written = json.loads(out.read_text())
    assert written["schema"] == "search-signal-benchmark-2"
    assert written["search"] is True and written["budget"] == 30
    assert written["reference"] == "same"
    assert list(written["signals"]) == ["same", "noise", "noise-at-di-level"]
    assert written["summary"]["noise"]["paired_against"] == "same"
    # The quiet probe really is at the target's loudness, and the plain one is not.
    signals = written["signals"]
    assert signals["noise-at-di-level"]["lufs"] == pytest.approx(
        signals["same"]["lufs"], abs=0.1)
    assert signals["noise"]["lufs"] > signals["same"]["lufs"] + 3
    assert len(written["outcomes"]) == 3
    assert all(o["inversion_objective"] is not None and o["neutral_objective"]
               is not None for o in written["outcomes"])
    assert "without the search" in done.stdout and "answer vs it" in done.stdout


def test_the_cli_can_score_only_the_baselines(tmp_path):
    target = tmp_path / "target.wav"
    fx.write_wav(target, fx.plucks(seconds=1.2, gap=0.7, seed=3) * 0.3)
    out = tmp_path / "baselines.json"
    done = _cli("--amp", AMP, "--target-di", target, "--signal", "same",
                "--signal", "noise", "--targets", "1", "--no-search", "--json", out)
    assert done.returncode == 0, done.stderr
    assert "no search" in done.stdout and "neutral start" in done.stdout

    assert "inversion alone" in done.stdout and "—" not in done.stdout
    written = json.loads(out.read_text())
    assert written["search"] is False and written["budget"] is None
    assert all(o["objective"] is None and o["inversion_objective"] is not None
               for o in written["outcomes"])


@pytest.mark.parametrize("spec, message", [
    ("wobble", "is not same, guitar, noise"),
    ("noise=elsewhere.wav", "its own name"),
])
def test_the_cli_refuses_a_signal_it_cannot_name(tmp_path, spec, message):
    target = tmp_path / "target.wav"
    fx.write_wav(target, fx.plucks(seconds=1.0, gap=0.7, seed=3) * 0.3)
    done = _cli("--amp", AMP, "--target-di", target, "--signal", spec,
                "--targets", "1", "--budget", "30")
    assert done.returncode != 0
    assert message in done.stderr


def test_two_workers_give_the_serial_answer_and_need_a_factory(
        space, topology, signals):
    target, named = signals
    serial = _run(space, topology, target, named)
    pooled = _run(space, topology, target, named, workers=2,
                  renderer_factory=SyntheticRenderer)
    key = lambda o: (o.target_index, o.signal)
    scored = lambda o: (key(o), o.objective, o.inversion_objective,
                        o.neutral_objective)
    assert [scored(o) for o in sorted(serial, key=key)] == [
        scored(o) for o in sorted(pooled, key=key)]
    with pytest.raises(SB.SignalBenchmarkError, match="renderer_factory"):
        _run(space, topology, target, named, workers=2)


def test_the_summary_leaves_failed_rows_out_and_tests_the_pairs():
    outcomes = []
    pairs = [(0.3, 0.6), (0.4, 0.7), (0.5, 0.9), (0.2, 0.4), (0.6, 0.8)]
    for index, (same, noise) in enumerate(pairs):
        outcomes.append(SB.SignalOutcome("same", index, 0, objective=same))
        outcomes.append(SB.SignalOutcome("noise", index, 1, objective=noise))
    outcomes.append(SB.SignalOutcome("same", 5, 0, objective=0.1))
    outcomes.append(SB.SignalOutcome("noise", 5, 1, failed=True, error="boom"))
    noise = SB.summarise(outcomes, reference="same")["noise"]

    assert noise["failures"] == 1
    assert noise["paired_targets"] == 5, "a failed row is not a pair"
    assert noise["closer_than_reference"] == 0
    assert noise["wilcoxon_p"] == pytest.approx(0.0625)


def test_the_cli_takes_a_named_recording_and_hashes_its_file(tmp_path):
    target, other = tmp_path / "target.wav", tmp_path / "other.wav"
    fx.write_wav(target, fx.plucks(seconds=1.2, gap=0.7, seed=3) * 0.3)
    fx.write_wav(other, fx.plucks(seconds=1.2, gap=0.5, seed=9) * 0.3)
    out = tmp_path / "signals.json"
    done = _cli("--amp", AMP, "--target-di", target, "--signal", "same",
                "--signal", f"other={other}", "--targets", "1", "--budget", "30",
                "--json", out)
    assert done.returncode == 0, done.stderr
    written = json.loads(out.read_text())["signals"]
    import hashlib

    assert written["other"]["file_sha256"] == hashlib.sha256(
        other.read_bytes()).hexdigest()
    assert "samples_sha256" in written["same"]


def test_the_benchmark_offers_the_synthetic_guitar_as_a_signal():
    from scripts.benchmark_search_signal import _signals

    target = fx.plucks(seconds=1.2, gap=0.7, seed=3) * 0.3
    signals, described = _signals(["same", "guitar"], target, fx.SAMPLE_RATE)
    assert list(signals) == ["same", "guitar"]
    assert described["guitar"]["kind"].startswith("synthetic strummed guitar")
