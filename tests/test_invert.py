"""Direct inversion, against targets built with the answer known.

The synthetic chain is what makes this possible: a target is rendered from a
parameter vector, the vector is thrown away, and the inversion has to get it back
from the audio alone. No search runs in any test here — that is the point of M3.

Every inversion is also checked for the case where it should *decline*. A preset
that switches a reverb on because the notes were short is worse than one that
leaves it alone, and abstention is the behaviour that is easy to lose.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

import numpy as np

from analysis import io, refchain
from analysis.compare import band_delta, compare, load_profile, scalar
from analysis.fingerprint import fingerprint
from match import invert
from match import space as S
from match.renderer_synth import SyntheticRenderer
from tests import fixtures_audio as fx

SR = fx.SAMPLE_RATE
AMP = "sw50r"


def di(seconds: float = 6.0, gap: float = 0.9):
    return fx.plucks(seconds=seconds, gap=gap, seed=13)


def measure(settings=None, signal=None):
    audio = refchain.render(signal if signal is not None else di(), settings)
    return fingerprint(io.from_samples(audio, SR), regime="probe", excerpt_s=None)


# --- the spectral fit -------------------------------------------------------


def test_the_eq_fit_recovers_a_known_curve():
    """Three bands moved in the target; the fit has to find those three.

    Tolerances are loose on purpose and the reason is the caveat the fit itself
    emits: with no measured `eq_basis.json` the solve uses idealised bell curves,
    which do not match the chain's real filters, so some of the answer leaks into
    neighbouring bands. Tightening these numbers is what M5's calibration buys.
    """
    wanted = {2: 8.0, 5: -6.0, 8: 5.0}
    settings = {f"{AMP}EQ/{AMP}EQBand{index}": gain for index, gain in wanted.items()}

    target, candidate = measure(settings), measure()
    delta = {row["centre_hz"]: row["delta_db"] for row in band_delta(target, candidate)}
    result = invert.fit_graphic_eq(delta, refchain.band_centres(), module=AMP)

    for index, gain in wanted.items():
        recovered = result.values[f"{AMP}EQ/{AMP}EQBand{index}"]
        assert recovered == pytest.approx(gain, abs=2.5), (
            f"band {index}: wanted {gain:+.1f} dB, recovered {recovered:+.1f}"
        )
        assert np.sign(recovered) == np.sign(gain), f"band {index} moved the wrong way"

    assert result.detail["eq_residual_db"] < 1.5


def test_the_eq_fit_says_when_it_had_no_measured_basis():
    """This repository does not silently substitute a guess for a measurement.

    Matched on substance rather than an exact phrase, so rewording the caveat does
    not fail the test but removing it does. The wording is checked separately for
    the things a user needs from it: the file that is missing, and that the answer
    is approximate.
    """
    delta = {row["centre_hz"]: row["delta_db"]
             for row in band_delta(measure({f"{AMP}EQ/{AMP}EQBand5": 6.0}), measure())}
    result = invert.fit_graphic_eq(delta, refchain.band_centres(), module=AMP,
                                  pack_id="morgan")

    assert len(result.caveats) == 1
    caveat = result.caveats[0]
    assert "eq_basis.json" in caveat, caveat
    assert "packs/morgan/" in caveat, "the caveat must name a path the user can look for"
    assert "<id>" not in caveat, "the placeholder must be substituted"

    # And with one supplied, it does not claim to be guessing.
    basis = invert.bell_basis(refchain.band_centres(), sorted(delta))
    supplied = invert.fit_graphic_eq(delta, refchain.band_centres(), basis=basis,
                                     module=AMP, pack_id="morgan")
    assert not any("eq_basis" in caveat for caveat in supplied.caveats)


def test_the_eq_fit_leaves_bands_alone_below_the_render_noise():
    """The plugin shows 0.23 dB of per-band variation between two renders of
    identical parameters, so a fit writing tenths is writing noise into a preset.

    Driven by a *small but real* difference, not by two identical fingerprints. The
    identical case gave exactly zero in every band, so `lsq_linear` returned zeros
    whatever the floor was set to — the assertion held with the floor at 0.0, which
    is the one thing it was supposed to catch. `refchain` is deterministic, so no
    amount of re-rendering produces the plugin's variation; the difference has to be
    constructed.
    """
    centres = refchain.band_centres()
    analysis = sorted({invert_nearest(c) for c in centres} | {100.0, 800.0, 5000.0})

    # Above the floor as a difference, but spread so thinly that every individual
    # band solves under it — which is the case where a correction really is thrown
    # away and the report has to say so.
    tiny = {frequency: 0.35 for frequency in analysis}
    result = invert.fit_graphic_eq(tiny, centres, module=AMP, pack_id="morgan")
    assert all(value == 0.0 for value in result.values.values()), result.values
    assert any("solved below" in caveat for caveat in result.caveats), (
        "throwing the whole correction away has to be reported"
    )
    # The residual must describe what was written, not the fit that was discarded.
    assert result.detail["eq_residual_db"] > 0.1

    # And a difference above the floor is still acted on, so the floor is a floor
    # and not a mute.
    real = {frequency: (6.0 if frequency == 1000.0 else 0.0) for frequency in analysis}
    acted = invert.fit_graphic_eq(real, centres, module=AMP, pack_id="morgan")
    assert any(abs(value) > 1.0 for value in acted.values.values()), acted.values


def invert_nearest(centre_hz: float) -> float:
    from analysis.features import THIRD_OCTAVE_CENTRES

    return float(min(THIRD_OCTAVE_CENTRES, key=lambda c: abs(c - centre_hz)))


def synthetic(**sections):
    """A Fingerprint assembled by hand, for the cases audio cannot produce.

    A measurement that is present but *not confident*, or that lands outside the
    plugin's range, cannot be rendered on demand — and both are branches the
    inversions turn on. Every abstention test used to pass through the wrong branch
    for want of this: they declined because a value was `None`, never because a
    confidence was low.
    """
    from analysis.fingerprint import Fingerprint

    return Fingerprint(**sections)


# --- the filters ------------------------------------------------------------


def test_the_high_pass_corner_follows_where_the_deficit_ends():
    """It used to be a constant. The window edges were hardcoded and the code then
    took the boundary of its own window, so a deficit reaching 100 Hz, 200 Hz or
    500 Hz all produced exactly 100.0."""
    from analysis.features import THIRD_OCTAVE_CENTRES

    def deficit_up_to(limit):
        return {float(f): (-6.0 if f <= limit else 0.0) for f in THIRD_OCTAVE_CENTRES}

    corners = {}
    for limit in (100.0, 200.0, 400.0):
        result = invert.fit_filters(deficit_up_to(limit), module=AMP, pack_id="morgan")
        corners[limit] = result.values.get(f"{AMP}EQ/{AMP}EQHpf")

    assert corners[100.0] == pytest.approx(100.0)
    assert corners[200.0] == pytest.approx(200.0)
    assert corners[400.0] == pytest.approx(400.0)
    assert len(set(corners.values())) == 3, f"the corner is not tracking the data: {corners}"


def test_a_dip_at_one_frequency_is_not_a_filter():
    """A wrongly-set corner removes range no band gain can put back, so a single
    band's worth of deficit must be left to the equaliser."""
    from analysis.features import THIRD_OCTAVE_CENTRES

    one_band = {float(f): (-8.0 if f == 63.0 else 0.0) for f in THIRD_OCTAVE_CENTRES}
    result = invert.fit_filters(one_band, module=AMP, pack_id="morgan")

    assert f"{AMP}EQ/{AMP}EQHpf" not in result.values
    assert f"{AMP}EQ/{AMP}EQLpf" not in result.values
    assert result.caveats, "declining has to be reported"


def test_the_filters_say_which_bands_they_accounted_for():
    """So the band fit does not correct the same deficit a second time. Both used to
    run on one delta, and a flat -3.5 dB low end set the corner *and* -4.6 dB on
    band 1 — which through the chain's own filter is -24.6 dB applied at 25 Hz.
    """
    from analysis.features import THIRD_OCTAVE_CENTRES

    delta = {float(f): (-6.0 if f <= 100.0 else 0.0) for f in THIRD_OCTAVE_CENTRES}
    result = invert.fit_filters(delta, module=AMP, pack_id="morgan")

    handled = result.detail["filtered_hz"]
    assert handled, "a corner was set, so the bands it covers must be named"
    assert max(handled) == pytest.approx(100.0)
    assert 125.0 not in handled


def test_an_empty_difference_still_says_the_filters_were_left_alone():
    """It was a completely silent no-op, unlike every sibling."""
    result = invert.fit_filters({}, module=AMP, pack_id="morgan")
    assert result.values == {}
    assert result.caveats


def test_a_basis_of_the_wrong_shape_is_refused():
    delta = {100.0: 1.0, 200.0: 2.0}
    with pytest.raises(invert.InversionError, match="basis is"):
        invert.fit_graphic_eq(delta, [65.0, 125.0], basis=np.zeros((3, 9)), module=AMP)


# --- level ------------------------------------------------------------------


def test_the_output_level_closes_a_known_loudness_difference():
    """The one inversion with no ambiguity in it: both sides report LUFS."""
    for offset in (-8.0, 4.0, 10.0):
        target = measure({"parameters/outputGain": offset})
        candidate = measure({"parameters/outputGain": 0.0})
        result = invert.output_level(target, candidate)
        assert result.values["parameters/outputGain"] == pytest.approx(offset, abs=0.5)


def test_the_output_level_says_when_the_difference_will_not_fit():
    """A clamp that is not reported is a silent failure to match."""
    target = measure({"parameters/outputGain": 0.0})
    loud = type(target)(source=dict(target.source))
    loud.source["lufs_i"] = float(target.source["lufs_i"]) + 40.0

    result = invert.output_level(loud, target)
    assert result.values["parameters/outputGain"] == 24.0     # the declared maximum
    assert any("exceeds" in caveat for caveat in result.caveats)


def test_no_loudness_means_no_level_change():
    silent = measure(signal=np.zeros(SR))
    assert silent.source["lufs_i"] is None
    result = invert.output_level(silent, measure())
    assert "parameters/outputGain" not in result.values
    assert result.caveats


# --- time effects -----------------------------------------------------------


def test_the_delay_is_recovered_from_the_audio_alone():
    for wanted in (180.0, 420.0):
        target = measure({"delay/delayActive": True, "delay/delayTime": wanted,
                          "delay/delayFeedback": 45.0, "delay/delayMix": 70.0},
                         signal=di(seconds=10.0, gap=1.4))
        result = invert.delay_settings(target)

        assert result.values["delay/delayActive"] is True
        assert result.values["delay/delayTime"] == pytest.approx(wanted, abs=20.0)
        assert 0.0 < result.values["delay/delayFeedback"] <= 100.0


def test_a_dry_target_switches_the_delay_off_rather_than_guessing():
    result = invert.delay_settings(measure(), )
    assert result.values["delay/delayActive"] is False
    assert any("no delay was measured" in caveat for caveat in result.caveats)


def test_a_delay_measured_without_confidence_is_declined():
    """The confidence gate, exercised through the gate rather than around it.

    Every abstention test declined because `delay_ms` was `None`, so lowering the
    floor to 0.0 — or deleting the check outright — changed nothing. The detector
    caps its confidence on combed material precisely because a repeated phrase and
    a tempo-synced delay are the same measurement, so this is the case that matters.
    """
    unsure = synthetic(time_fx={"delay_ms": 420.0, "delay_confidence": 0.10,
                                "delay_feedback_est": 0.4})
    result = invert.delay_settings(unsure)
    assert result.values["delay/delayActive"] is False
    assert "delay/delayTime" not in result.values
    assert any("0.10" in caveat for caveat in result.caveats), result.caveats

    # Just over the floor, and it is used.
    sure = synthetic(time_fx={"delay_ms": 420.0, "delay_confidence": 0.20,
                              "delay_feedback_est": 0.4})
    assert invert.delay_settings(sure).values["delay/delayActive"] is True


def test_a_delay_outside_the_plugin_range_is_clamped_and_reported():
    """A clamp nobody is told about is a silent failure to match."""
    far = synthetic(time_fx={"delay_ms": 4000.0, "delay_confidence": 0.6,
                             "delay_feedback_est": 0.3})
    result = invert.delay_settings(far)

    assert result.values["delay/delayTime"] == 1500.0      # the declared maximum
    assert any("clamped" in caveat for caveat in result.caveats), result.caveats


def test_a_reverb_measured_without_confidence_is_declined():
    """Same gap on the reverb: the existing test declined via the short-decay guard
    and its own docstring says the material is *confident*, so the confidence path
    was never taken."""
    unsure = synthetic(time_fx={"rt60_s": 2.0, "rt60_confidence": 0.1})
    result = invert.reverb_settings(unsure)
    assert result.values["reverb/reverbActive"] is False
    assert "reverb/reverbDecay" not in result.values

    sure = synthetic(time_fx={"rt60_s": 2.0, "rt60_confidence": 0.5})
    assert invert.reverb_settings(sure).values["reverb/reverbDecay"] == pytest.approx(2.0)


def test_a_reverb_longer_than_the_plugin_can_make_is_clamped_and_reported():
    long = synthetic(time_fx={"rt60_s": 90.0, "rt60_confidence": 0.6})
    result = invert.reverb_settings(long)
    assert result.values["reverb/reverbDecay"] == 60.0     # the declared maximum
    assert any("clamped" in caveat for caveat in result.caveats)


def test_a_predelay_outside_the_plugin_range_is_clamped_and_reported():
    result = invert.reverb_settings(synthetic(
        time_fx={"rt60_s": 2.0, "rt60_confidence": 0.6, "predelay_ms": 900.0}))
    assert result.values["reverb/reverbPreDelay"] == 200.0
    assert any("pre-delay" in caveat and "clamped" in caveat
               for caveat in result.caveats), result.caveats


def test_the_delays_wet_level_is_not_invented_from_the_detector():
    """`delayMix` used to be the detection confidence times 100, so a confidence of
    0.95 asked for 95% wet. A normalised correlation height is not a mix percentage;
    they are not the same kind of quantity."""
    result = invert.delay_settings(synthetic(
        time_fx={"delay_ms": 420.0, "delay_confidence": 0.95, "delay_feedback_est": 0.3}))
    assert "delay/delayMix" not in result.values
    assert any("wet level" in caveat for caveat in result.caveats)


def test_a_tremolo_is_not_read_off_a_delays_repeats():
    """The worst false positive found in review, and it fired on M3's own
    exit-criterion target: a 420 ms delay modulates the envelope at 2.1 Hz purely
    enough to pass the confidence gate, so a full-depth tremolo was written into a
    target that had none — and this was the one inversion that said nothing when it
    acted.
    """
    with_delay = synthetic(
        modulation={"am_rate_hz": 2.38, "am_depth": 1.0, "am_confidence": 0.85},
        time_fx={"delay_ms": 420.0, "delay_confidence": 0.5},
    )
    result = invert.tremolo_settings(with_delay)
    assert result.values["tremolo/tremoloActive"] is False
    assert any("repeat rate" in caveat for caveat in result.caveats), result.caveats

    # A modulation that does *not* coincide with the repeats is still a tremolo.
    unrelated = synthetic(
        modulation={"am_rate_hz": 6.0, "am_depth": 0.5, "am_confidence": 0.85},
        time_fx={"delay_ms": 420.0, "delay_confidence": 0.5},
    )
    assert invert.tremolo_settings(unrelated).values["tremolo/tremoloActive"] is True


def test_a_tremolo_that_fires_always_says_so():
    """It is set from a measurement no recording can make unambiguous, so acting on
    it without a word was the gap that let the delay case through unnoticed."""
    clean = synthetic(modulation={"am_rate_hz": 5.0, "am_depth": 0.6,
                                  "am_confidence": 0.9})
    result = invert.tremolo_settings(clean)
    assert result.values["tremolo/tremoloActive"] is True
    assert result.caveats, "a tremolo set from audio alone must carry a caveat"
    assert any("by ear" in caveat for caveat in result.caveats)


def test_a_tremolo_rate_outside_the_plugin_range_is_clamped_and_reported():
    fast = synthetic(modulation={"am_rate_hz": 40.0, "am_depth": 0.5,
                                 "am_confidence": 0.9})
    result = invert.tremolo_settings(fast)
    assert result.values["tremolo/tremoloRate"] == 15.0   # the declared maximum
    assert any("clamped" in caveat for caveat in result.caveats)


def test_the_reverb_decay_is_recovered_from_the_audio_alone():
    target = measure({"reverb/reverbActive": True, "reverb/reverbDecay": 2.4,
                      "reverb/reverbMix": 70.0},
                     signal=fx.decaying_bursts(rt60_s=0.05, seconds=12.0, gap=2.4))
    result = invert.reverb_settings(target)

    assert result.values["reverb/reverbActive"] is True
    assert result.values["reverb/reverbDecay"] == pytest.approx(2.4, rel=0.4)


def test_a_decay_shorter_than_the_plugin_can_make_is_the_note_not_a_room():
    """The defect this test exists for: dry plucks measure a *confident* 0.41 s
    decay, and clamping that up into the plugin's 1..60 s range turned "there is no
    reverb here" into "reverb at its minimum". The reverb now stays off.
    """
    result = invert.reverb_settings(measure())
    assert result.values["reverb/reverbActive"] is False
    assert any("shorter than the plugin's shortest reverb" in caveat
               for caveat in result.caveats)


def test_a_tremolo_is_only_set_when_the_modulation_is_a_clean_sine():
    """Strumming in time is not a tremolo, and nothing in the audio distinguishes
    the two except how pure the modulation is."""
    strummed = measure(signal=fx.plucks(seconds=8.0, gap=0.5))
    assert invert.tremolo_settings(strummed).values["tremolo/tremoloActive"] is False

    modulated = measure(signal=fx.tremolo(fx.noise(seconds=6.0), rate_hz=5.0, depth=0.6))
    result = invert.tremolo_settings(modulated)
    if result.values["tremolo/tremoloActive"]:
        assert result.values["tremolo/tremoloRate"] == pytest.approx(5.0, abs=0.5)
    else:
        pytest.skip("the chain's own processing lowered the modulation purity")


# --- M3's exit criterion ----------------------------------------------------


def test_inversion_alone_closes_an_eq_and_time_effects_gap_with_no_search():
    """M3's exit criterion.

    A target that differs from the source only in EQ, level and a delay — exactly
    the things D2 says are calculable — must be brought substantially closer by one
    inversion pass and zero renders of search.

    The assertion is a *relative* improvement plus an absolute ceiling, because the
    absolute number depends on the loss profile's scales, and those are data that
    are meant to be tuned.
    """
    truth = {
        f"{AMP}EQ/{AMP}EQActive": True,
        f"{AMP}EQ/{AMP}EQBand2": 7.0,
        f"{AMP}EQ/{AMP}EQBand6": -5.0,
        "parameters/outputGain": -4.0,
        "delay/delayActive": True,
        "delay/delayTime": 420.0,
        "delay/delayFeedback": 45.0,
        "delay/delayMix": 60.0,
    }
    probe = di(seconds=10.0, gap=1.4)
    target = measure(truth, signal=probe)

    before = measure(signal=probe)
    inverted = invert.invert(target, before, amp=AMP)

    # Filtered to what this backend models: the inversion is computed against the
    # plugin's parameters and the synthetic chain covers 45 of them.
    renderer = SyntheticRenderer()
    after = measure(inverted.as_settings(renderer.parameter_specs()), signal=probe)

    start = scalar(compare(target, before))
    end = scalar(compare(target, after))
    assert end < start, f"inversion made it worse: {start:.3f} -> {end:.3f}"
    assert end < start * 0.8, (
        f"inversion barely helped: {start:.3f} -> {end:.3f}. "
        f"caveats: {inverted.caveats}"
    )

    # The delay is the part that should be recovered outright, not approached.
    assert inverted.values["delay/delayActive"] is True
    assert inverted.values["delay/delayTime"] == pytest.approx(420.0, abs=20.0)

    # And the aggregate is not enough on its own. A mutation run showed this test
    # passing with `invert()` doing no level match, no filter fit and no spectral
    # fit at all: the delay settings alone move the objective from 1.15 to 0.64,
    # already inside the 0.8 gate above. So each part has to be attributed.
    delay_only = {path: value for path, value in
                  inverted.as_settings(renderer.parameter_specs()).items()
                  if path.startswith("delay/")}
    with_delay_only = measure(delay_only, signal=probe)
    delay_only_score = scalar(compare(target, with_delay_only))

    assert end < delay_only_score, (
        f"the spectral and level fits added nothing: delay alone {delay_only_score:.3f}, "
        f"everything {end:.3f}"
    )

    # Not asserted equal to the -4 dB in the truth vector, and that is the point:
    # the target's EQ boosts and its delay change its loudness too, so the gain that
    # matches the two is the *total* difference (about -8 dB here), not the one
    # control's value. What the contract says is that the loudness gap closes.
    #
    # It does not close completely, and that is a property of one-pass inversion
    # rather than a slack tolerance: the level is matched against the candidate as
    # it was, and the band gains then change how loud the result is. About 3 dB is
    # left over here. `invert()` says so in a caveat, and this asserts both halves —
    # that the gap shrinks substantially, and that what remains is small enough for
    # the search to finish off.
    gap_before = abs(target.source["lufs_i"] - before.source["lufs_i"])
    gap_after = abs(target.source["lufs_i"] - after.source["lufs_i"])
    assert gap_after < gap_before / 2, f"{gap_before:.1f} dB -> {gap_after:.1f} dB"
    assert gap_after < 5.0, f"loudness still {gap_after:.1f} dB apart after inversion"
    assert any("level" in caveat for caveat in inverted.caveats), (
        "the leftover level has to be reported, not left for someone to find"
    )
    gains = [value for path, value in inverted.values.items() if "EQBand" in path]
    assert gains, "no band gains were emitted at all"
    assert max(abs(gain) for gain in gains) > 2.0, (
        f"the band fit moved nothing meaningful: {gains}"
    )
    assert inverted.values[f"{AMP}EQ/{AMP}EQActive"] is True


def test_an_inversion_reaches_a_spec_with_its_spectral_fit_intact():
    """The composition both modules advertise, which did not work.

    `invert()` emits `sw50rEQ/...` keys and used to emit no `selectedAmp`, so
    `to_spec` could not tell which amp's controls mattered and dropped every one:
    fourteen values in, four parameters out, no error and no caveat. This asserts the
    band gains survive the trip that `apply_spec.py` is at the end of.
    """
    space = S.build("morgan")
    target = measure({f"{AMP}EQ/{AMP}EQBand4": 6.0, f"{AMP}EQ/{AMP}EQBand7": -5.0})
    inverted = invert.invert(target, measure(), amp=AMP)

    spec = space.to_spec(inverted.as_settings(), name="Matched")
    written = {f"{p['module']}/{p['key']}" if p["module"] else p["key"]: p["value"]
               for p in spec["parameters"]}

    bands = [key for key in written if "EQBand" in key]
    assert len(bands) == 9, f"only {len(bands)} of nine band gains survived: {sorted(written)}"
    assert written[f"{AMP}EQ/{AMP}EQBand4"] > 2.0
    assert written[f"{AMP}EQ/{AMP}EQBand7"] < -2.0
    assert "selectedAmp" in written


def test_a_spec_that_sets_amp_controls_without_naming_the_amp_is_refused():
    """Rather than silently dropping them, which is how the above went unnoticed."""
    space = S.build("morgan")
    with pytest.raises(S.SpaceError, match="which amp is selected"):
        space.to_spec({f"{AMP}EQ/{AMP}EQBand1": 3.0})


@pytest.mark.parametrize("amp", ["SW50R", "sw50r"])
def test_both_spellings_of_the_amp_are_accepted(amp):
    """`SW50R` is not a hypothetical typo: it is what `amp_modules` is keyed by and
    what `Space.amp_prefix` accepts, and it used to produce a caveat blaming the
    manifest for declaring no EQ centres — for a pack that declares them."""
    inverted = invert.invert(measure(), measure(), amp=amp)
    assert not any("declares no graphic-EQ centres" in caveat
                   for caveat in inverted.caveats), inverted.caveats


def test_an_unknown_amp_is_refused_and_the_message_names_the_real_ones():
    with pytest.raises(invert.InversionError) as raised:
        invert.invert(measure(), measure(), amp="nosuchamp")
    message = str(raised.value)
    assert "nosuchamp" in message
    assert "sw50r" in message and "ac20" in message, message


def test_a_pack_that_does_not_declare_the_parameter_is_refused():
    """`pack_id` used to be threaded through and ignored: with `toneking` these
    functions wrote Morgan's paths clamped to Morgan's ranges, so `reverbDecay` came
    out at 30 s against Tone King's declared 0.5-8, for a parameter it does not have.
    """
    confident = synthetic(time_fx={"rt60_s": 30.0, "rt60_confidence": 0.8})
    with pytest.raises(invert.InversionError, match="does not declare"):
        invert.reverb_settings(confident, pack_id="toneking")

    with pytest.raises(invert.InversionError, match="does not declare"):
        invert.output_level(measure({"parameters/outputGain": 3.0}), measure(),
                            pack_id="toneking")


def test_the_equaliser_is_not_switched_on_to_do_nothing():
    """Identical target and candidate: there is nothing to correct, so turning the
    graphic EQ on would be a change with no reason behind it."""
    same = measure()
    inverted = invert.invert(same, same, amp=AMP)
    gains = [value for path, value in inverted.values.items() if "EQBand" in path]
    assert all(gain == 0.0 for gain in gains), gains
    assert inverted.values[f"{AMP}EQ/{AMP}EQActive"] is False


def test_an_inversion_result_is_a_spec_the_pack_accepts():
    """Whatever inversion decides has to be writable by the same validated path a
    hand-authored preset uses. Nothing here writes preset bytes."""
    from packs.loader import load_pack

    target = measure({f"{AMP}EQ/{AMP}EQBand3": 6.0, "parameters/outputGain": -3.0})
    inverted = invert.invert(target, measure(), amp=AMP)

    pack = load_pack("morgan")
    for path, value in inverted.values.items():
        spec = pack.parameters.get(path)
        assert spec is not None, f"{path} is not a parameter this pack declares"
        pack.to_stored(spec, value, warnings=[])


def test_an_inversion_result_renders_through_the_synthetic_chain():
    """The other half of §11's requirement: one dict drives the renderer and the
    preset writer, so they cannot drift."""
    target = measure({f"{AMP}EQ/{AMP}EQBand7": -8.0})
    inverted = invert.invert(target, measure(), amp=AMP)
    renderer = SyntheticRenderer()
    settings = inverted.as_settings(renderer.parameter_specs())
    assert inverted.dropped_for(renderer.parameter_specs()), (
        "the chain models fewer parameters than the plugin, so something is dropped"
    )

    audio = refchain.render(di(seconds=2.0), settings)
    assert np.abs(audio).max() > 0.0


def test_every_inversion_reports_what_it_could_not_do():
    """The caveats are the deliverable as much as the values are: a report that
    does not say "no measured basis" or "no pre-delay was visible" overstates what
    was measured."""
    inverted = invert.invert(measure(), measure(), amp=AMP)
    assert inverted.caveats
    assert all(isinstance(caveat, str) and caveat for caveat in inverted.caveats)


def test_the_inversion_can_be_merged_into_a_search_space():
    """What M4 consumes: inversion sets a starting point, the space says what is
    left to search."""
    space = S.build("morgan", amp=AMP)
    target = measure({f"{AMP}EQ/{AMP}EQBand4": 5.0})
    inverted = invert.invert(target, measure(), amp=AMP)

    values = {("", "selectedAmp"): 2}
    for path, value in inverted.values.items():
        module, _, key = path.rpartition("/")
        values[(module, key)] = value

    live = space.active(values)
    assert live
    assert any(d.path == f"{AMP}EQ/{AMP}EQBand4" for d in live), (
        "the EQ the inversion just set should be live in the space"
    )
