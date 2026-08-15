"""The synthetic chain, and M2's exit criterion.

Two things are checked here. That the chain agrees with the manifest about what
its parameters are — which is what lets `match/space.py` build a search space over
it with no special-casing — and that **each parameter moves the fingerprint field
it should**.

That second table is the exit criterion, and it is also the most honest
documentation in the project of what M1's features actually detect: a feature that
cannot see a control move here, on a signal with no other variables, will not see
it in a recording.
"""

from __future__ import annotations

import time

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

import numpy as np

from analysis import io, refchain
from analysis.fingerprint import fingerprint
from match.renderer_synth import SyntheticRenderer
from tests import fixtures_audio as fx

SR = fx.SAMPLE_RATE


def di(seconds: float = 4.0, gap: float = 0.9):
    """A dry, transient, aperiodic DI: plucks, so onsets and decays exist."""
    return fx.plucks(seconds=seconds, gap=gap, seed=13)


def measure(settings=None, signal=None, excerpt_s=None):
    audio = refchain.render(signal if signal is not None else di(), settings)
    return fingerprint(io.from_samples(audio, SR), regime="probe", excerpt_s=excerpt_s)


# --- the contract with the manifest -----------------------------------------


def test_every_parameter_is_declared_by_the_pack():
    """The chain names keys; the manifest owns their kinds, units and ranges.

    A chain that invented a parameter, or kept one the manifest dropped, would
    give `match/space.py` a space the real plugin does not have.
    """
    specs = refchain.parameter_specs()
    assert len(specs) == len(refchain.PARAMETERS)
    for (module, key), spec in specs.items():
        assert spec.module == module and spec.key == key
        assert spec.writable, f"{module}/{key} is read-only in the manifest"


def test_the_eq_centres_come_from_the_manifest():
    """The nine fixed ISO centres `match/invert.py` fits onto."""
    assert refchain.band_centres() == [65.0, 125.0, 250.0, 500.0, 1000.0,
                                       2000.0, 4000.0, 8000.0, 16000.0]


def test_defaults_are_legal_values_for_their_own_parameters():
    """Every default survives the pack's own validation, so a bare render is a
    render of a preset the plugin would accept.

    Passed explicitly, one at a time. `resolve(None)` returns the defaults without
    entering its validation loop at all, so asserting `resolve() == defaults()` was
    `dict(X) == dict(X)` — it passed with `inputGain` defaulted to 9999 dB against a
    declared range of -24..24.
    """
    for (module, key), value in refchain.defaults().items():
        resolved = refchain.resolve({f"{module}/{key}": value})
        assert resolved[(module, key)] == value, f"{module}/{key}"


@pytest.mark.parametrize("key, value, message", [
    ("sw50rEQ/sw50rEQBand1", 40.0, "outside"),        # declared -12..12 dB
    ("delay/delayTime", 9000.0, "outside"),           # declared 16..1500 ms
    ("compressor/compressorCompression", 150.0, "0"),  # a rotation is a percent
])
def test_illegal_values_are_refused_the_same_way_apply_spec_refuses_them(key, value, message):
    """The synthetic chain must not accept settings the real plugin would reject.

    Otherwise M4 could converge on a parameter vector that cannot be written, and
    the failure would surface at the very end, in `apply_spec.py`.
    """
    with pytest.raises(refchain.ChainError, match=message):
        refchain.render(di(seconds=1.0), {key: value})


def test_an_unmodelled_parameter_is_refused_rather_than_ignored():
    """Silently dropping it would let a search move a control with no effect and
    conclude the control does nothing."""
    with pytest.raises(refchain.ChainError, match="not implemented"):
        refchain.render(di(seconds=1.0), {"reverb/reverbHighCut2": 1000.0})


def test_settings_round_trip_into_a_spec():
    """§11's requirement: the render and the preset come from one source.

    Morgan's live state and its preset files are different encodings and nothing
    converts between them, so the only thing keeping them from drifting is that
    both are generated from the same spec.
    """
    spec = refchain.to_spec({"delay/delayActive": True, "delay/delayTime": 250.0})
    entries = {(p["module"], p["key"]): p["value"] for p in spec["parameters"]}
    assert entries[("delay", "delayActive")] is True
    assert entries[("delay", "delayTime")] == 250.0
    assert entries[("parameters", "outputGain")] == 0.0     # untouched default
    assert spec["name"] == "Synthetic"


# --- M2's exit criterion: speed ---------------------------------------------


EVERYTHING_ON = {
    "parameters/gateActive": True, "compressor/compressorActive": True,
    "drive1/drive1Active": True, "delay/delayActive": True,
    "reverb/reverbActive": True, "reverb/reverbDecay": 60.0,
}


def best_of(settings, signal, runs: int = 5) -> float:
    """CPU time for one render, best of `runs`.

    `process_time`, not `perf_counter`, and the difference is the whole reason
    these three tests are not flaky. They all compare two measurements, and a
    ratio of two wall-clock minima is not protected by taking minima: with
    pytest-xdist running eight workers, the longer of the two operations has more
    chances for every one of its samples to lose its core, so the ratio inflates
    even though neither render got slower. Measured here: the everything-on render
    came back at 35 ms against a 3.5 ms dry render — 9.9x, through a bound of 8 —
    on run 14 of 15, having passed the other 14. CPU time counts only this
    process's work, which is exactly what "has a stage become pathologically
    expensive" is asking about, and it does not move when a neighbour is busy.

    Measured side by side under eight competing processes, six samples each: the
    wall-clock ratio ranged 3.5 to 6.6 while the CPU-time ratio ranged 3.3 to 3.5.
    The real ratio is about 3.4 and the bound is 8, so this was never a marginal
    threshold — it was a measurement that stopped describing the code.
    """
    refchain.render(signal, settings)        # warm the scipy and IR caches
    times = []
    for _ in range(runs):
        started = time.process_time()
        refchain.render(signal, settings)
        times.append(time.process_time() - started)
    return min(times)


def test_a_di_renders_fast_enough_to_search_with():
    """Measured on this machine for a 2-second DI: 21 ms for the default chain,
    23 ms with all 45 parameters supplied — which is what a search does — 51 ms
    with every effect engaged at a maximal reverb, and 90 ms for the pathological
    16 ms delay at 95% feedback.

    The absolute bound is deliberately loose: this runs on shared CI runners, and
    a tight assertion there is a flake, not a check. The *ratio* below is the part
    that means something, because it holds on any machine. Both are CPU time — see
    `best_of` for why that matters once the suite runs in parallel.
    """
    signal = di(seconds=2.0)
    assert best_of(None, signal) < 1.0, "a render should not take a second"


def test_supplying_every_parameter_costs_little_more_than_supplying_none():
    """The check that keeps manifest parsing out of the render path.

    `load_pack()` re-reads and re-parses `manifest.json` on every call, and this
    used to run once per render *plus once per supplied setting*: a render with all
    45 parameters spent about 25 of its 47 ms parsing the same file 47 times. A
    search supplies every parameter on every trial, so that was the real cost of a
    render, and the documented 11-16 ms was measured on the one case that avoids it.

    A ratio, so it means the same thing on a slow runner as on a fast one.
    """
    signal = di(seconds=2.0)
    bare = best_of(None, signal)
    full = best_of({"/".join(key): value for key, value in refchain.defaults().items()},
                   signal)
    assert full < bare * 2.0, (
        f"supplying 45 parameters cost {full / bare:.1f}x a bare render "
        f"({full * 1000:.0f} ms against {bare * 1000:.0f} ms)"
    )


def test_engaging_every_effect_stays_within_a_few_times_the_dry_render():
    """Catches a change that makes one stage pathologically expensive, without
    asserting a millisecond count on a runner we do not control."""
    signal = di(seconds=2.0)
    assert best_of(EVERYTHING_ON, signal) < best_of(None, signal) * 8.0


def test_the_synthetic_chain_is_exactly_reproducible():
    """Unlike either real backend. This is the property that makes it a ground
    truth, and `RenderMetadata.reproducible` is where it is advertised."""
    signal = di(seconds=1.0)
    settings = {"reverb/reverbActive": True, "delay/delayActive": True}
    assert np.array_equal(refchain.render(signal, settings),
                          refchain.render(signal, settings))
    assert SyntheticRenderer().metadata().reproducible is True


# --- M2's exit criterion: each control moves the field it should -------------


def test_output_gain_moves_the_level_and_leaves_the_tone_alone():
    quiet = measure({"parameters/outputGain": -12.0})
    loud = measure({"parameters/outputGain": 6.0})

    assert loud.source["lufs_i"] - quiet.source["lufs_i"] == pytest.approx(18.0, abs=1.5)
    # And the spectrum is loudness-normalised, so the *shape* must not move.
    quiet_bands = np.array(quiet.spectrum["band_db"])
    loud_bands = np.array(loud.spectrum["band_db"])
    assert np.abs(quiet_bands - loud_bands).max() < 1.0


def nearest_band(centre_hz: float) -> float:
    """The third-octave band a plugin EQ centre falls in.

    They are not the same list. Morgan's lowest graphic-EQ band is labelled 65 Hz
    and the ISO third-octave centre beside it is 63 Hz; the other eight coincide.
    So `Fingerprint.band_db(65.0)` finds nothing and returns None, and M3's fit has
    to map between the two sets rather than index one with the other.
    """
    from analysis.features import THIRD_OCTAVE_CENTRES

    return float(min(THIRD_OCTAVE_CENTRES, key=lambda c: abs(c - centre_hz)))


def test_the_eq_centres_do_not_all_coincide_with_analysis_bands():
    """Named so the 65-versus-63 trap is discovered here and not in M3."""
    assert nearest_band(65.0) == 63.0
    for centre in refchain.band_centres()[1:]:
        assert nearest_band(centre) == centre


@pytest.mark.parametrize("band, centre", [
    ("sw50rEQ/sw50rEQBand1", 65.0),
    ("sw50rEQ/sw50rEQBand3", 250.0),
    ("sw50rEQ/sw50rEQBand5", 1000.0),
    ("sw50rEQ/sw50rEQBand7", 4000.0),
    ("sw50rEQ/sw50rEQBand9", 16000.0),
])
def test_each_eq_band_moves_its_own_third_octave_band(band, centre):
    """The measurement M3's least-squares fit inverts.

    Boosting one band must lift the spectrum at that frequency and leave the far
    end of the spectrum where it was — otherwise the fit has no basis to solve on.
    """
    at = nearest_band(centre)
    flat = measure({band: 0.0})
    boosted = measure({band: 12.0})

    at_centre = boosted.band_db(at) - flat.band_db(at)
    assert at_centre > 2.0, f"{band} did not lift {at} Hz ({at_centre:+.2f} dB)"

    # Two octaves away in the direction with room, the change must be much smaller.
    far = nearest_band(250.0 if centre >= 4000.0 else 8000.0)
    at_far = boosted.band_db(far) - flat.band_db(far)
    assert at_far < at_centre - 1.5, (
        f"{band} moved {far} Hz by {at_far:+.2f} dB against {at_centre:+.2f} dB at centre"
    )


def test_the_high_pass_moves_the_bottom_of_the_spectrum():
    open_low = measure({"sw50rEQ/sw50rEQHpf": 20.0})
    filtered = measure({"sw50rEQ/sw50rEQHpf": 500.0})
    assert filtered.band_db(100.0) < open_low.band_db(100.0) - 5.0


def test_the_low_pass_moves_the_top_of_the_spectrum():
    open_high = measure({"sw50rEQ/sw50rEQLpf": 20000.0})
    filtered = measure({"sw50rEQ/sw50rEQLpf": 1000.0})
    assert filtered.band_db(6300.0) < open_high.band_db(6300.0) - 8.0


def test_the_tone_stack_moves_the_tilt():
    dark = measure({"sw50rAmp/sw50rBass": 90.0, "sw50rAmp/sw50rTreble": 10.0})
    bright = measure({"sw50rAmp/sw50rBass": 10.0, "sw50rAmp/sw50rTreble": 90.0})
    assert bright.spectrum["tilt_db_per_decade"] > dark.spectrum["tilt_db_per_decade"] + 2.0


def test_the_bright_switch_lifts_the_top_relative_to_the_bottom():
    """Relative, because the spectrum is loudness-normalised.

    Adding 6 dB at 5 kHz raises the whole measurement's loudness, so normalising
    pulls every other band *down* — 125 Hz drops about 3 dB here without any
    filter touching it. A test that asked for the bottom to stay put would be
    asking the normalisation not to work. Only the difference between bands
    carries meaning, which is also why `compare._timbre` removes the mean before
    scoring band shape.
    """
    off = measure({"sw50rAmp/sw50rBright": False})
    on = measure({"sw50rAmp/sw50rBright": True})

    top = on.band_db(5000.0) - off.band_db(5000.0)
    bottom = on.band_db(125.0) - off.band_db(125.0)
    assert top - bottom > 3.0, f"top moved {top:+.2f} dB, bottom {bottom:+.2f} dB"


def test_the_cab_position_trades_top_end_for_low_mids():
    """The direction M0 measured on the real `*CabPosition`: +1.4 dB in the low
    mids and -1.1 dB at 6.3 kHz.

    Magnitudes, not just signs. Asserting the sign alone passed with the control
    made fifty times weaker, moving the bands by 0.1 dB — below the 0.23 dB
    per-band noise the real plugin shows between two identical renders, so an
    inversion built against it would be fitting noise.
    """
    centre = measure({"cabParameters/leftCabPosition": 0.0})
    edge = measure({"cabParameters/leftCabPosition": 1.0})

    top = centre.band_db(6300.0) - edge.band_db(6300.0)
    lows = edge.band_db(500.0) - centre.band_db(500.0)
    assert top > 1.0, f"6.3 kHz moved only {top:+.2f} dB"
    assert lows > 1.0, f"500 Hz moved only {lows:+.2f} dB"


def test_the_delay_moves_the_measured_delay_time():
    """The whole reason `time_fx` exists: this is set, not searched for."""
    for wanted in (180.0, 420.0):
        result = measure({"delay/delayActive": True, "delay/delayTime": wanted,
                          "delay/delayMix": 60.0, "delay/delayFeedback": 40.0},
                         signal=di(seconds=8.0))
        assert result.time_fx["delay_ms"] == pytest.approx(wanted, abs=20.0), (
            f"asked for {wanted} ms, measured {result.time_fx['delay_ms']}"
        )


def test_no_delay_in_the_chain_means_none_measured():
    result = measure({"delay/delayActive": False}, signal=di(seconds=8.0))
    assert result.time_fx["delay_ms"] is None


def test_the_delay_feedback_moves_the_measured_feedback():
    """Against the knob's own value, not merely in the right order.

    Ordering alone passed with the control made nearly inert — 0.263 against 0.270
    for a knob moved from 20% to 60% — which would let M3 invert feedback onto a
    parameter that barely does anything.

    Not asserted equal to the knob, because it is not: filtering each repeat
    inside the loop costs energy the raw coefficient does not account for, so a
    60% knob measures about 0.42. That is the *effective* decay, which is what the
    reference audio actually contains and therefore what M3 should invert onto.
    What is asserted is that each step of the knob moves it substantially.
    """
    measured = [
        measure({"delay/delayActive": True, "delay/delayMix": 60.0,
                 "delay/delayFeedback": knob}, signal=di(seconds=8.0))
        .time_fx["delay_feedback_est"]
        for knob in (20.0, 40.0, 60.0)
    ]
    for lower, higher in zip(measured, measured[1:]):
        assert higher - lower > 0.08, f"the knob barely moved it: {measured}"


def test_the_delay_repeats_get_darker_the_way_a_feedback_line_does():
    """`delayLowCut`/`delayHighCut` act once per trip round the loop.

    The first version summed the taps and filtered the sum once, so every repeat
    came back with an identical spectrum and these two controls had no cumulative
    effect at all — the only effect they exist for. Measured here on successive
    repeats of a single burst.
    """
    from analysis.features import spectral_statistics

    # One short burst then silence, so each 300 ms window holds exactly one
    # repeat. `plucks(seconds=0.3)` cannot be used: its onset range is empty at
    # that length and it returns digital silence.
    rng = np.random.default_rng(21)
    burst = np.zeros(int(3.3 * SR))
    burst[: int(0.05 * SR)] = rng.standard_normal(int(0.05 * SR)) * 0.5
    audio = refchain.render(burst, {
        "delay/delayActive": True, "delay/delayTime": 300.0,
        "delay/delayFeedback": 60.0, "delay/delayMix": 100.0,
        "delay/delayLowCut": 60.0, "delay/delayHighCut": 5000.0,
    })[:, 0]

    def centroid(repeat: int) -> float:
        window = int(0.3 * SR)
        return spectral_statistics(audio[window * repeat: window * (repeat + 1)],
                                   SR)["centroid_hz"]["p50"]

    first, last = centroid(1), centroid(6)
    assert last < first - 300.0, (
        f"repeat 6 centroid {last:.0f} Hz against repeat 1's {first:.0f} Hz"
    )


def test_the_reverb_decay_moves_the_measured_rt60():
    """`reverbDecay` is wired so that it *is* the RT60, which is what makes the
    synthetic chain a ground truth for the estimator rather than a second guess."""
    for wanted in (1.2, 2.4):
        result = measure({"reverb/reverbActive": True, "reverb/reverbDecay": wanted,
                          "reverb/reverbMix": 70.0}, signal=di(seconds=10.0, gap=1.8))
        assert result.time_fx["rt60_s"] == pytest.approx(wanted, rel=0.4), (
            f"asked for {wanted} s, measured {result.time_fx['rt60_s']}"
        )


def spread_db(result) -> float:
    """How far the loud frames sit above the quiet ones — compression behaviour.

    The term `compare._dynamics` actually scores, and a better observable than the
    crest factor: crest is a single sample against an average, so one surviving
    transient dominates it, and heavy compression can raise it while plainly
    reducing the range.
    """
    percentiles = result.dynamics["rms_percentiles_db"]
    return percentiles["p90"] - percentiles["p10"]


def test_the_compressor_narrows_the_level_distribution():
    """Dynamics, which is the dimension a spectrum cannot see."""
    dry = measure({"compressor/compressorActive": False})
    light = measure({"compressor/compressorActive": True,
                     "compressor/compressorCompression": 20.0,
                     "compressor/compressorMix": 100.0})
    heavy = measure({"compressor/compressorActive": True,
                     "compressor/compressorCompression": 95.0,
                     "compressor/compressorMix": 100.0})

    assert spread_db(heavy) < spread_db(light) < spread_db(dry)
    assert spread_db(dry) - spread_db(heavy) > 4.0


def test_the_drive_adds_harmonic_content():
    """Measured on a sustained note, because that is the only thing the harmonic
    features will speak about — which is itself the point of the confidence field."""
    note = fx.harmonic_note(seconds=3.0, f0=196.0)
    clean = measure({"drive1/drive1Active": False}, signal=note)
    dirty = measure({"drive1/drive1Active": True, "drive1/drive1Drive": 95.0},
                    signal=note)

    if clean.harmonic.get("confidence", 0) < 0.4 or dirty.harmonic.get("confidence", 0) < 0.4:
        pytest.skip("no sustained monophonic segment was found in either render")
    assert dirty.harmonic["hnr_db"] < clean.harmonic["hnr_db"]


def test_the_gate_removes_the_quiet_frames_from_the_distribution():
    """A gate *raises* the measured p10, which is the opposite of the obvious guess.

    It does not make the quiet parts quieter — it removes them. What is left is the
    louder material, so the tenth percentile of the surviving distribution climbs,
    from -48 dB wide open to -33 dB with the gate shut. Everything in `features` is
    measured on gated frames for the same reason, and silence that has been gated
    to nothing is below the analysis floor and never counted at all.
    """
    open_gate = measure({"parameters/gateActive": True,
                         "parameters/gateThreshold": -96.0})
    shut = measure({"parameters/gateActive": True,
                    "parameters/gateThreshold": -12.0})

    quiet_open = open_gate.dynamics["rms_percentiles_db"]["p10"]
    quiet_shut = shut.dynamics["rms_percentiles_db"]["p10"]
    assert quiet_shut > quiet_open + 5.0, (
        f"the gate did not remove the quiet frames: {quiet_shut:.1f} vs {quiet_open:.1f}"
    )


def test_a_gate_at_its_minimum_threshold_is_a_bypass():
    """Compared against the gate being *off*, which is the only version of this
    claim that says anything.

    The earlier test re-rendered the identical settings and compared them, on a
    chain proven bit-deterministic two tests up — so it restated determinism, and
    a mutation that made a wide-open gate duck hard by 10 dB passed it.

    Bit-exactness rather than approximate equality, because the causal mask
    smoothing this guards against does not merely shift the level: it ramped the
    first 5 ms of every attack after a silent gap, and digital silence is always
    below the -96 dB minimum, so nothing was ever transparent.
    """
    signal = di(seconds=2.0)
    off = refchain.render(signal, {"parameters/gateActive": False})
    wide_open = refchain.render(signal, {"parameters/gateActive": True,
                                         "parameters/gateThreshold": -96.0})
    assert np.array_equal(off, wide_open)

    # And a threshold that does bite is not a bypass, so the test can fail.
    shut = refchain.render(signal, {"parameters/gateActive": True,
                                    "parameters/gateThreshold": -12.0})
    assert not np.array_equal(off, shut)


# --- the renderer wrapper ----------------------------------------------------


def test_the_renderer_reports_what_produced_the_audio():
    renderer = SyntheticRenderer()
    result = renderer.render(di(seconds=1.0), {"delay/delayActive": True})

    assert result.audio.shape[1] == 2
    assert not result.silent and result.peak > 0
    assert result.metadata.renderer_id == "synthetic"
    assert result.metadata.sample_rate == SR
    assert result.cache_key and len(result.cache_key) == 64
    assert renderer.parameter_specs() == refchain.parameter_specs()
