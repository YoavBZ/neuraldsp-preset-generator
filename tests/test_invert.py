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

    # A non-zero shape whose complete fitted correction remains below the floor.
    tiny = {frequency: (0.2 if index % 2 else -0.2)
            for index, frequency in enumerate(analysis)}
    result = invert.fit_graphic_eq(tiny, centres, module=AMP, pack_id="morgan")
    assert all(value == 0.0 for value in result.values.values()), result.values
    assert any("solved at or below" in caveat for caveat in result.caveats), (
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


def band_rms(one, other) -> float:
    """How far apart two fingerprints are across the third-octave bands, in dB."""
    rows = band_delta(one, other)
    return float(np.sqrt(np.mean([row["delta_db"] ** 2 for row in rows])))


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


def test_a_corner_is_recovered_from_a_real_roll_off():
    """The end-to-end claim, on renders rather than on hand-drawn curves.

    Two earlier rules failed here. The corner was a constant — 100, 200 and 500 Hz
    of deficit all gave `EQHpf = 100.0`. Then it was "where the deficit stops",
    which is not the corner and is not near it: a corner is already down *at* itself
    and tens of dB down an octave away, so a truth low-pass at 4 kHz came back as
    6.3 kHz. Fitting `filter_response_db` recovers a low-pass exactly.
    """
    flat = measure()

    for truth in (2000.0, 4000.0, 8000.0):
        target = measure({f"{AMP}EQ/{AMP}EQLpf": truth,
                          f"{AMP}EQ/{AMP}EQActive": True})
        rows = band_delta(target, flat)
        delta = {float(r["centre_hz"]): float(r["delta_db"]) for r in rows}
        result = invert.fit_filters(delta, module=AMP, pack_id="morgan")
        assert result.values[f"{AMP}EQ/{AMP}EQLpf"] == pytest.approx(truth), truth
        assert result.detail["filter_fit_db"] < invert.FILTER_MAX_FIT_DB


def test_two_corners_are_fitted_together_not_one_at_a_time():
    """Fitting each corner against the whole measurement independently makes the
    *other* corner's roll-off look like unexplained error. A target that really is a
    200 Hz high-pass and a 4 kHz low-pass reported 7.6 dB and 5.5 dB of misfit,
    picked `100 / 5000`, and said "not the shape a corner makes" about a difference
    that was exactly two corners."""
    flat = measure()
    target = measure({f"{AMP}EQ/{AMP}EQHpf": 200.0, f"{AMP}EQ/{AMP}EQLpf": 4000.0,
                      f"{AMP}EQ/{AMP}EQActive": True})
    rows = band_delta(target, flat)
    delta = {float(r["centre_hz"]): float(r["delta_db"]) for r in rows}
    result = invert.fit_filters(delta, module=AMP, pack_id="morgan")

    # The low-pass is still recovered exactly with a high-pass in the way.
    assert result.values[f"{AMP}EQ/{AMP}EQLpf"] == pytest.approx(4000.0)
    assert result.values[f"{AMP}EQ/{AMP}EQHpf"] == pytest.approx(160.0)
    # And one honest residual for the pair, not two inflated ones.
    assert result.detail["filter_fit_db"] < 3.0, result.detail["filter_fit_db"]

    # Scored through the chain: both corners plus the bands close it.
    after = measure(invert.invert(target, flat, amp=AMP)
                    .as_settings(refchain.parameter_specs()))
    assert band_rms(target, flat) > 9.0
    assert band_rms(target, after) < 1.5, band_rms(target, after)


def test_a_high_pass_lands_low_and_the_fit_residual_says_so():
    """The honest half. A cab's own low-end roll-off is in the same measurement, so
    above about 200 Hz what is measured is not the shape of a high-pass — and the
    corner comes out low. The fit residual crosses `FILTER_MAX_FIT_DB` exactly
    where that starts, so the caveat is driven by a number rather than by a hunch.
    """
    flat = measure()

    costs = {}
    corners = {}
    for truth in (100.0, 200.0, 400.0):
        target = measure({f"{AMP}EQ/{AMP}EQHpf": truth,
                          f"{AMP}EQ/{AMP}EQActive": True})
        rows = band_delta(target, flat)
        delta = {float(r["centre_hz"]): float(r["delta_db"]) for r in rows}
        result = invert.fit_filters(delta, module=AMP, pack_id="morgan")
        corners[truth] = result.values[f"{AMP}EQ/{AMP}EQHpf"]
        costs[truth] = result.detail["filter_fit_db"]
        rough = any("shape a corner makes" in c for c in result.caveats)
        assert rough == (costs[truth] > invert.FILTER_MAX_FIT_DB), (truth, costs)

    # Not monotonic — 200 Hz and 400 Hz both come back as 125 on this fixture, which
    # is the point: past 200 Hz the measurement stops being a high-pass at all and
    # the corner saturates. Asserting an ordering here would be asserting a wish.
    assert all(corners[t] < t for t in corners), f"lands low, as documented: {corners}"
    assert costs[100.0] < costs[200.0] < costs[400.0], (
        f"the residual is what makes the undershoot visible: {costs}"
    )
    assert costs[100.0] < invert.FILTER_MAX_FIT_DB, "a real corner fits"
    assert costs[400.0] > invert.FILTER_MAX_FIT_DB, "and this one does not"


def test_the_bands_close_what_the_corner_left():
    """The composition, scored through the chain that made the target.

    This is the assertion the whole `fit_filters`/`fit_graphic_eq` split exists for.
    Deleting the covered bands from the delta instead left the outer bands with
    nothing to fit and sent one to +10.6 dB on a target 23.7 dB *down* there, for a
    band RMS of 2.83; subtracting the modelled response gets 0.38.
    """
    signal = di()
    specs = refchain.parameter_specs()
    flat = measure(signal=signal)
    target = measure({f"{AMP}EQ/{AMP}EQLpf": 4000.0, f"{AMP}EQ/{AMP}EQActive": True},
                     signal=signal)

    result = invert.invert(target, flat, amp=AMP)
    before = band_rms(target, flat)
    after = band_rms(target, measure(result.as_settings(specs), signal=signal))

    assert before > 8.0, before
    assert after < 1.0, f"the corner and the bands together: {after:.2f} dB"

    # No band anywhere near a bound. A small boost above the corner is *correct* —
    # the fitted low-pass slightly over-attenuates and the band takes it back — so
    # the invariant is not "every top band cuts", which was the shape of the defect
    # rather than a truth. It is that no band has been driven to the rail for want of
    # anything to fit against, which is what sent one to +10.6 dB.
    low, high = invert.EQ_BOUNDS_DB
    for index in range(1, len(invert._band_centres("morgan", AMP)) + 1):
        gain = result.values[f"{AMP}EQ/{AMP}EQBand{index}"]
        assert low + 1.0 < gain < high - 1.0, f"band {index} is at the rail: {gain}"


def test_the_bands_do_not_double_correct_what_a_corner_handled():
    """Both used to run on one delta, so a flat -3.5 dB low end set the corner *and*
    -4.6 dB on band 1 on top of it."""
    from analysis.features import THIRD_OCTAVE_CENTRES

    centres = sorted(float(f) for f in THIRD_OCTAVE_CENTRES)
    delta = {f: (-6.0 if f <= 100.0 else 0.0) for f in centres}
    band_centres = invert._band_centres("morgan", AMP)
    response = invert.fit_filters(delta, module=AMP,
                                 pack_id="morgan").detail["filter_response_db"]
    assert response, "a corner has to fire for this to mean anything"

    deducted = invert.fit_graphic_eq(delta, band_centres, module=AMP,
                                     pack_id="morgan", accounted_for=response)
    raw = invert.fit_graphic_eq(delta, band_centres, module=AMP, pack_id="morgan")

    band1 = f"{AMP}EQ/{AMP}EQBand1"
    assert raw.values[band1] < -3.0, "the un-deducted fit doubles the correction"
    assert deducted.values[band1] > raw.values[band1] + 2.0, (
        f"deducting the corner has to pull band 1 back: "
        f"{raw.values[band1]} -> {deducted.values[band1]}"
    )
    # And the two records are kept apart: what was measured, and what is left.
    assert deducted.detail["eq_measured_db"][25.0] == pytest.approx(-6.0)
    assert deducted.detail["eq_requested_db"][25.0] > -6.0


def test_a_clamped_corner_is_still_the_best_the_plugin_can_do():
    """`EQHpf` stops at 500 Hz, so a roll-off that wants more cannot be had. The
    corner has to stay inside the declared range and the bands take the rest."""
    from analysis.features import THIRD_OCTAVE_CENTRES

    centres = sorted(float(f) for f in THIRD_OCTAVE_CENTRES)
    spec = invert.declared("morgan", f"{AMP}EQ/{AMP}EQHpf")
    assert (float(spec.min), float(spec.max)) == (20.0, 500.0)

    steep = {f: (invert.filter_response_db([f], hpf_hz=2000.0)[0]) for f in centres}
    steep = {f: v - sum(steep.values()) / len(steep) for f, v in steep.items()}
    result = invert.fit_filters(steep, module=AMP, pack_id="morgan")

    corner = result.values[f"{AMP}EQ/{AMP}EQHpf"]
    assert 20.0 <= corner <= 500.0, corner
    assert corner == pytest.approx(500.0), "the range's own limit is the best offer"
    assert any("shape a corner makes" in c for c in result.caveats), (
        result.caveats
    )


def test_a_deficit_everywhere_is_a_level_difference_not_two_corners():
    """Two maximal runs inward from opposite edges can only meet if every band is
    short, and taking a corner from each end produced an `HPF 500 / LPF 1000`
    one-octave slot out of evidence that says only "quieter everywhere"."""
    from analysis.features import THIRD_OCTAVE_CENTRES

    everywhere = {float(f): -6.0 for f in THIRD_OCTAVE_CENTRES}
    result = invert.fit_filters(everywhere, module=AMP, pack_id="morgan")

    assert result.values == {}
    assert result.detail["filter_response_db"] == {}
    assert any("whole spectrum" in c for c in result.caveats), result.caveats

    # The three-band version the reviewer found, which came out HPF 160 / LPF 1000.
    three = invert.fit_filters({100.0: -6.0, 125.0: -6.0, 160.0: -6.0},
                               module=AMP, pack_id="morgan")
    assert three.values == {}


def test_a_short_run_at_the_very_bottom_is_not_a_filter():
    """A wrongly-set corner removes range no band gain can put back, so a deficit
    over fewer than `FILTER_MIN_BANDS` bands must be left to the equaliser.

    The run has to start at the *lowest* centre to exercise the length gate at all.
    An earlier version put its single-band dip at 63 Hz — the fifth third-octave
    centre — so `short[0]` was False, the run was 0 bands long before the threshold
    was ever consulted, and `FILTER_MIN_BANDS = 1` passed.
    """
    from analysis.features import THIRD_OCTAVE_CENTRES

    centres = sorted(float(f) for f in THIRD_OCTAVE_CENTRES)
    assert invert.FILTER_MIN_BANDS == 3
    for run in (1, 2):
        edge = set(centres[:run])
        delta = {f: (-8.0 if f in edge else 0.0) for f in centres}
        result = invert.fit_filters(delta, module=AMP, pack_id="morgan")
        assert f"{AMP}EQ/{AMP}EQHpf" not in result.values, run
        assert result.detail["filter_deficit_bands"] == (run, 0)
        assert result.detail["filter_response_db"] == {}

    # And the third band is the one that tips it over.
    edge = set(centres[:3])
    delta = {f: (-8.0 if f in edge else 0.0) for f in centres}
    assert f"{AMP}EQ/{AMP}EQHpf" in invert.fit_filters(
        delta, module=AMP, pack_id="morgan").values


def test_a_deficit_of_less_than_the_threshold_is_not_a_filter():
    """`FILTER_MIN_DEFICIT_DB` is the other half of the gate, and nothing pinned it:
    a shallow tilt is a band-gain job, and a corner would remove range the bands
    cannot put back."""
    from analysis.features import THIRD_OCTAVE_CENTRES

    centres = sorted(float(f) for f in THIRD_OCTAVE_CENTRES)
    assert invert.FILTER_MIN_DEFICIT_DB == 3.0
    shallow = {f: (-2.0 if f <= 200.0 else 0.0) for f in centres}
    assert invert.fit_filters(shallow, module=AMP, pack_id="morgan").values == {}

    steep = {f: (-4.0 if f <= 200.0 else 0.0) for f in centres}
    assert invert.fit_filters(steep, module=AMP, pack_id="morgan").values != {}


@pytest.mark.parametrize("current,target", [(160.0, 500.0), (500.0, 160.0)])
def test_a_filter_move_is_fitted_from_the_current_audible_corner(current, target):
    """The measured delta is a transition, not a response from an open filter."""
    from analysis.features import THIRD_OCTAVE_CENTRES

    frequencies = sorted(float(f) for f in THIRD_OCTAVE_CENTRES)
    delta = {
        frequency: float(
            invert.filter_response_db([frequency], hpf_hz=target)[0]
            - invert.filter_response_db([frequency], hpf_hz=current)[0]
        )
        for frequency in frequencies
    }

    result = invert.fit_filters(
        delta, module=AMP, pack_id="morgan",
        current_filters=(current, None),
    )

    assert result.values == {f"{AMP}EQ/{AMP}EQHpf": target}
    assert f"{AMP}EQ/{AMP}EQLpf" not in result.values
    assert result.detail["filter_fit_db"] == 0.0


def test_a_caller_supplied_basis_still_fits_when_a_corner_fires():
    """`basis` is sized to the full delta, so removing the covered bands made the
    shape check reject the measured basis M5 will supply — the only reason `basis`
    is a parameter of `invert()` at all."""
    from analysis.features import THIRD_OCTAVE_CENTRES

    centres = sorted(float(f) for f in THIRD_OCTAVE_CENTRES)
    delta = {f: (-8.0 if f <= 300.0 else 0.0) for f in centres}
    band_centres = invert._band_centres("morgan", AMP)
    basis = invert.bell_basis(band_centres, centres, q=1.4)
    response = invert.fit_filters(delta, module=AMP,
                                 pack_id="morgan").detail["filter_response_db"]
    assert response, "a corner has to fire for this to mean anything"

    result = invert.fit_graphic_eq(delta, band_centres, basis=basis, module=AMP,
                                   pack_id="morgan", accounted_for=response)
    assert result.values
    # A supplied basis is a measurement, so the textbook-shapes caveat must not fire.
    assert not any("textbook" in c for c in result.caveats), result.caveats


def test_the_modelled_corner_response_is_the_order_refchain_builds():
    """The one assumption this rests on, stated as a number. `filter_response_db` is
    a Butterworth magnitude of `FILTER_ORDER`, and `refchain._filters` builds
    `butter(2, ...)`, so the two agree by construction rather than by luck."""
    assert invert.FILTER_ORDER == 2
    # A second-order corner is 3 dB down at itself and 12 dB per octave beyond.
    assert invert.filter_response_db([1000.0], lpf_hz=1000.0)[0] == pytest.approx(
        -3.0103, abs=1e-3)
    at_octave = invert.filter_response_db([2000.0], lpf_hz=1000.0)[0]
    at_two = invert.filter_response_db([4000.0], lpf_hz=1000.0)[0]
    assert at_two - at_octave == pytest.approx(-12.0, abs=0.3)
    # And a high-pass is the mirror image.
    assert invert.filter_response_db([250.0], hpf_hz=1000.0)[0] == pytest.approx(
        invert.filter_response_db([4000.0], lpf_hz=1000.0)[0], abs=1e-6)


def test_an_empty_difference_leaves_the_corners_alone_without_a_caveat():
    """`invert()` says "no band difference could be measured" once, for both fits.
    Two sentences meaning the same thing is one too many for a report someone reads,
    and the `fit_graphic_eq` copy became *false* when both ends rolled off."""
    result = invert.fit_filters({}, module=AMP, pack_id="morgan")
    assert result.values == {}
    assert result.caveats == []
    assert result.detail["filter_response_db"] == {}


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


def test_the_output_level_adds_the_correction_to_the_template_value():
    target = measure({"parameters/outputGain": 4.0})
    candidate = measure({"parameters/outputGain": 0.0})

    result = invert.output_level(target, candidate, current_value=-6.0)

    assert result.values["parameters/outputGain"] == pytest.approx(-2.0, abs=0.5)
    assert result.detail["output_gain_before_db"] == -6.0
    assert result.detail["lufs_difference_db"] == pytest.approx(4.0, abs=0.5)


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
        # A rotation is a percent, and `0 < x <= 100` accepted the unscaled fraction
        # 0.45 just as happily — 0.45% of feedback where 45% was measured.
        feedback = result.values["delay/delayFeedback"]
        assert feedback == pytest.approx(45.0, abs=25.0), (
            f"the estimate is a fraction and the control is a percent: {feedback}"
        )


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

    # Asserted rather than skipped. A `pytest.skip` here meant the positive half
    # could vanish on any fixture change without anyone noticing, and the fast suite
    # reports zero skips so nothing would have shown it.
    modulated = measure(signal=fx.tremolo(fx.noise(seconds=6.0), rate_hz=5.0, depth=0.6))
    result = invert.tremolo_settings(modulated)
    assert result.values["tremolo/tremoloActive"] is True, result.caveats
    assert result.values["tremolo/tremoloRate"] == pytest.approx(5.0, abs=0.5)
    # A percent, not the fraction the detector reports. 17.9% for a 0.6 modulation is
    # the chain's own compression flattening it — the number worth pinning is the
    # scale, because the unscaled 0.179 would be written just as silently.
    assert result.values["tremolo/tremoloDepth"] > 5.0


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
    # fit at all: the delay settings alone move the objective from 1.15 to 0.61,
    # already inside the 0.8 gate above. So each part has to be attributed, and by
    # more than a hair — a bare inequality passed with the whole spectral fit
    # replaced by zeros.
    delay_only = {path: value for path, value in
                  inverted.as_settings(renderer.parameter_specs()).items()
                  if path.startswith("delay/")}
    with_delay_only = measure(delay_only, signal=probe)
    delay_only_score = scalar(compare(target, with_delay_only))

    assert end < delay_only_score * 0.9, (
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
    # Matched on the sentence, not on the word "level": the delay's own "the delay's
    # wet level is left for the search" also contains it, so deleting this caveat
    # entirely used to pass.
    assert any("the output level was matched before the equaliser" in caveat
               for caveat in inverted.caveats), (
        f"the leftover level has to be reported: {inverted.caveats}"
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
    graphic EQ on or off would be a change with no reason behind it."""
    same = measure()
    inverted = invert.invert(same, same, amp=AMP)
    gains = [value for path, value in inverted.values.items() if "EQBand" in path]
    assert all(gain == 0.0 for gain in gains), gains
    assert f"{AMP}EQ/{AMP}EQActive" not in inverted.values


def test_zero_eq_correction_preserves_a_non_flat_template():
    settings = {
        ("", "selectedAmp"): "2",
        ("parameters", "outputGain"): 0.0,
        (f"{AMP}EQ", f"{AMP}EQActive"): True,
        (f"{AMP}EQ", f"{AMP}EQBand5"): 4.0,
    }
    same = measure({f"{AMP}EQ/{AMP}EQActive": True,
                    f"{AMP}EQ/{AMP}EQBand5": 4.0})

    calculated = invert.invert(
        same, same, amp=AMP, current_settings=settings,
    )

    assert not any(path in calculated.values for path in (
        f"{AMP}EQ/{AMP}EQBand5", f"{AMP}EQ/{AMP}EQActive"
    ))


def test_eq_correction_is_added_to_the_template_gain():
    current = 3.0
    candidate_settings = {
        f"{AMP}EQ/{AMP}EQActive": True,
        f"{AMP}EQ/{AMP}EQBand5": current,
    }
    target_settings = {
        f"{AMP}EQ/{AMP}EQActive": True,
        f"{AMP}EQ/{AMP}EQBand5": 7.0,
    }
    seed = {
        ("", "selectedAmp"): "2",
        ("parameters", "outputGain"): 0.0,
        (f"{AMP}EQ", f"{AMP}EQActive"): True,
        ("eqParameters", "sectionActive"): True,
        (f"{AMP}EQ", f"{AMP}EQBand5"): current,
    }

    calculated = invert.invert(
        measure(target_settings), measure(candidate_settings), amp=AMP,
        current_settings=seed,
    )

    absolute = calculated.values[f"{AMP}EQ/{AMP}EQBand5"]
    assert absolute == pytest.approx(7.0, abs=2.5)
    assert absolute > current


def test_dormant_eq_values_are_not_used_as_the_audible_baseline():
    path = invert._validated_signal_path("morgan", AMP)
    band = f"{AMP}EQ/{AMP}EQBand5"
    current = {
        (f"{AMP}EQ", f"{AMP}EQActive"): False,
        ("eqParameters", "sectionActive"): False,
        (f"{AMP}EQ", f"{AMP}EQBand5"): 8.0,
    }
    correction = invert.Inversion(values={band: 4.0})

    applied = invert._apply_band_corrections(
        correction, path, current, "morgan"
    )

    assert applied.values[band] == 4.0
    assert set(applied.values) == set(path.eq_band_controls)
    assert all(applied.values[control] == 0.0
               for control in path.eq_band_controls if control != band)
    assert any("dormant band values" in caveat for caveat in applied.caveats)


def test_filter_only_correction_neutralises_dormant_bands_before_enabling_eq(
    monkeypatch,
):
    """A corner also enables the section, exposing every stored band with it."""
    path = invert._validated_signal_path("morgan", AMP)
    current = {
        ("", "selectedAmp"): "2",
        ("parameters", "outputGain"): 0.0,
        (f"{AMP}EQ", f"{AMP}EQActive"): False,
        ("eqParameters", "sectionActive"): False,
        (f"{AMP}EQ", f"{AMP}EQLpf"): 8000.0,
        (f"{AMP}EQ", f"{AMP}EQBand5"): 8.0,
    }
    target = measure({
        f"{AMP}EQ/{AMP}EQActive": True,
        f"{AMP}EQ/{AMP}EQLpf": 4000.0,
    })
    candidate = measure({
        f"{AMP}EQ/{AMP}EQActive": False,
        f"{AMP}EQ/{AMP}EQLpf": 8000.0,
        f"{AMP}EQ/{AMP}EQBand5": 8.0,
    })

    def no_band_moves(*args, **kwargs):
        return invert.Inversion(values={
            control: 0.0 for control in kwargs["band_controls"]
        })

    monkeypatch.setattr(invert, "fit_graphic_eq", no_band_moves)
    result = invert.invert(
        target, candidate, amp=AMP, current_settings=current,
    )

    assert f"{AMP}EQ/{AMP}EQLpf" in result.values
    assert result.values[f"{AMP}EQ/{AMP}EQHpf"] == 20.0
    assert all(result.values[control] == 0.0
               for control in path.eq_band_controls)
    assert all(result.values[control] is True
               for control in path.eq_enable_controls)
    assert any("dormant band values" in caveat for caveat in result.caveats)
    assert any("dormant filter values" in caveat for caveat in result.caveats)


def test_band_only_correction_opens_both_dormant_filter_corners():
    path = invert._validated_signal_path("morgan", AMP)
    current = {
        (f"{AMP}EQ", f"{AMP}EQActive"): False,
        ("eqParameters", "sectionActive"): False,
        (f"{AMP}EQ", f"{AMP}EQHpf"): 500.0,
        (f"{AMP}EQ", f"{AMP}EQLpf"): 1000.0,
    }
    result = invert.Inversion(values={f"{AMP}EQ/{AMP}EQBand5": 2.0})

    invert._neutralise_dormant_filters(result, path, current, "morgan")

    assert result.values[f"{AMP}EQ/{AMP}EQHpf"] == 20.0
    assert result.values[f"{AMP}EQ/{AMP}EQLpf"] == 20000.0


def test_a_floored_correction_does_not_claim_the_equaliser_was_untouched():
    """The band fit is floored, but enabling the section still rewrites nine
    controls. Saying the equaliser was left unchanged beside that is a false
    statement about a run, which this repository treats as a defect."""
    from match.renderer import RenderMetadata

    class DeafBackend:
        """Everything is noise, so nothing the fit solves can clear the floor."""

        def metadata(self):
            return RenderMetadata(renderer_id="synthetic", sample_rate=48000,
                                  block_size=512, reproducible=False,
                                  band_noise_db=50.0)

    path = invert._validated_signal_path("morgan", AMP)
    current = {
        ("", "selectedAmp"): "2",
        ("parameters", "outputGain"): 0.0,
        (f"{AMP}EQ", f"{AMP}EQActive"): False,
        ("eqParameters", "sectionActive"): False,
        (f"{AMP}EQ", f"{AMP}EQLpf"): 8000.0,
        (f"{AMP}EQ", f"{AMP}EQBand5"): 8.0,
    }
    target = measure({f"{AMP}EQ/{AMP}EQActive": True,
                      f"{AMP}EQ/{AMP}EQLpf": 4000.0})
    candidate = measure({f"{AMP}EQ/{AMP}EQActive": False,
                         f"{AMP}EQ/{AMP}EQLpf": 8000.0,
                         f"{AMP}EQ/{AMP}EQBand5": 8.0})

    result = invert.invert(target, candidate, amp=AMP,
                           current_settings=current, renderer=DeafBackend())

    assert all(result.values[control] == 0.0
               for control in path.eq_band_controls), (
        "the dormant +8 dB band still has to be neutralised before the section "
        "is switched on"
    )
    assert not any("left unchanged" in caveat for caveat in result.caveats)
    assert any("no band correction was written" in caveat
               for caveat in result.caveats)
    assert any("dormant band values" in caveat for caveat in result.caveats)


def test_a_band_cut_back_to_neutral_still_warns_about_leftover_level(monkeypatch):
    """Under delta arithmetic a written 0.00 dB can be a 6 dB cut, and it changes
    the loudness exactly as much as a 6 dB boost does. Asking whether the final
    value is non-zero asked the wrong question and said nothing about one."""
    band = f"{AMP}EQ/{AMP}EQBand5"
    current = {
        ("", "selectedAmp"): "2",
        ("parameters", "outputGain"): 0.0,
        (f"{AMP}EQ", f"{AMP}EQActive"): True,
        ("eqParameters", "sectionActive"): True,
        (f"{AMP}EQ", f"{AMP}EQBand5"): 6.0,
    }

    def cancel_the_template(*args, **kwargs):
        return invert.Inversion(values={
            control: (-6.0 if control == band else 0.0)
            for control in kwargs["band_controls"]
        })

    monkeypatch.setattr(invert, "fit_graphic_eq", cancel_the_template)
    result = invert.invert(
        measure({f"{AMP}EQ/{AMP}EQActive": True}),
        measure({f"{AMP}EQ/{AMP}EQActive": True,
                 f"{AMP}EQ/{AMP}EQBand5": 6.0}),
        amp=AMP, current_settings=current,
    )

    assert result.values[band] == 0.0, "a 6 dB cut, written as an absolute"
    assert any("level left over" in caveat for caveat in result.caveats)


def test_a_band_the_template_omits_is_not_solved_for():
    """A correction that cannot be written must not be fitted either, or
    `eq_residual_db` describes a solution nobody applied.

    The residual is what this pins, not the width of the interval the solve is
    given: how a band is held at zero is an implementation detail, and that the
    reported misfit belongs to the correction actually written is not.
    """
    path = invert._validated_signal_path("morgan", AMP)
    omitted = f"{AMP}EQ/{AMP}EQBand6"
    target = measure({f"{AMP}EQ/{AMP}EQBand6": 8.0})
    candidate = measure({f"{AMP}EQ/{AMP}EQActive": True})
    stated = {
        ("", "selectedAmp"): "2",
        ("parameters", "outputGain"): 0.0,
        (f"{AMP}EQ", f"{AMP}EQActive"): True,
        ("eqParameters", "sectionActive"): True,
    }
    for index in range(1, 10):
        stated[(f"{AMP}EQ", f"{AMP}EQBand{index}")] = 0.0
    partial = {key: value for key, value in stated.items()
               if key != (f"{AMP}EQ", f"{AMP}EQBand6")}

    whole = invert.invert(target, candidate, amp=AMP, current_settings=stated)
    short = invert.invert(target, candidate, amp=AMP, current_settings=partial)

    index = list(path.eq_band_controls).index(omitted)
    lower, upper = invert._band_correction_bounds(path, partial, "morgan")
    assert upper[index] - lower[index] < 0.01, "the band gets no usable room"
    assert omitted not in short.values
    assert whole.values[omitted] != 0.0, "the band the target needs, when writable"
    # The target's 8 dB boost sits on the band that cannot be written, so the
    # honest residual has to be the worse one. Reporting the nine-band fit's
    # number here was the defect.
    assert short.detail["eq_residual_db"] > whole.detail["eq_residual_db"]
    skipped = [caveat for caveat in short.caveats if omitted in caveat]
    assert len(skipped) == 1 and "no correction was fitted" in skipped[0]
    # Nothing here promises the search will pick the band up: it may be frozen by
    # the sensitivity screen, or behind a section this pass just switched on.
    assert "the search" not in skipped[0]


def test_a_dormant_corner_already_open_is_not_written_again():
    path = invert._validated_signal_path("morgan", AMP)
    current = {
        (f"{AMP}EQ", f"{AMP}EQActive"): False,
        ("eqParameters", "sectionActive"): False,
        (f"{AMP}EQ", f"{AMP}EQHpf"): 20.0,
        (f"{AMP}EQ", f"{AMP}EQLpf"): 1000.0,
    }
    result = invert.Inversion(values={f"{AMP}EQ/{AMP}EQBand5": 2.0})

    invert._neutralise_dormant_filters(result, path, current, "morgan")

    assert f"{AMP}EQ/{AMP}EQHpf" not in result.values
    assert result.values[f"{AMP}EQ/{AMP}EQLpf"] == 20000.0
    assert all(f"{AMP}EQ/{AMP}EQHpf" not in caveat for caveat in result.caveats)


def test_an_unstated_eq_gate_is_unknown_rather_than_off():
    """`Space.active`'s rule, applied where it decides nine controls: a gate the
    template does not state is not a gate that is off. Reading it as off made every
    stored band dormant, which licensed overwriting all nine with neutral zero and
    switching the section on — discarding an audible equaliser and reporting it as
    a tidy-up."""
    path = invert._validated_signal_path("morgan", AMP)
    stated = {
        ("", "selectedAmp"): "2",
        ("parameters", "outputGain"): 0.0,
        (f"{AMP}EQ", f"{AMP}EQActive"): True,
        ("eqParameters", "sectionActive"): True,
        (f"{AMP}EQ", f"{AMP}EQBand5"): 6.0,
    }
    # The same template with one gate missing, which is the only difference.
    silent = {key: value for key, value in stated.items()
              if key != ("eqParameters", "sectionActive")}
    target = measure({f"{AMP}EQ/{AMP}EQActive": True,
                      f"{AMP}EQ/{AMP}EQBand3": 8.0})
    candidate = measure({f"{AMP}EQ/{AMP}EQActive": True,
                         f"{AMP}EQ/{AMP}EQBand5": 6.0})

    known = invert.invert(target, candidate, amp=AMP, current_settings=stated)
    unknown = invert.invert(target, candidate, amp=AMP, current_settings=silent)

    assert any(control in known.values for control in path.eq_band_controls), (
        "the stated template must still be inverted"
    )
    assert not any(control in unknown.values
                   for control in path.eq_band_controls), unknown.values
    assert not any(control in unknown.values
                   for control in path.eq_enable_controls)
    assert f"{AMP}EQ/{AMP}EQHpf" not in unknown.values
    assert any("eqParameters/sectionActive" in caveat and "no way to know" in caveat
               for caveat in unknown.caveats), unknown.caveats
    # The rest of the inversion is unaffected: level is not an EQ decision.
    assert "parameters/outputGain" in unknown.values


def test_an_unreadable_gate_value_is_also_unknown_and_says_which_problem():
    """A value that will not translate is not a reading either — and the caveat has
    to name *that*, not report the control as unstated. Telling someone to set a
    value they have already set is advice they cannot act on."""
    path = invert._validated_signal_path("morgan", AMP)
    current = {
        ("", "selectedAmp"): "2",
        ("parameters", "outputGain"): 0.0,
        (f"{AMP}EQ", f"{AMP}EQActive"): "not a switch position",
        ("eqParameters", "sectionActive"): True,
    }

    result = invert.invert(measure({f"{AMP}EQ/{AMP}EQBand3": 8.0}), measure(),
                           amp=AMP, current_settings=current)

    assert not any(control in result.values
                   for control in path.eq_band_controls), result.values
    gate = next(c for c in result.caveats if "in circuit" in c)
    assert "not a switch position" in gate and "cannot read as a switch" in gate
    assert "does not state" not in gate, "the template does state it"


def test_a_gate_known_to_be_off_settles_it_whatever_the_others_say():
    """One open gate proves the section was out of circuit for that render. Letting
    an unstated sibling override it discarded a correct inversion and replaced it
    with a caveat claiming the state was unknowable — and which of the two won
    depended on the order the manifest happens to declare them in."""
    path = invert._validated_signal_path("morgan", AMP)
    base = {
        ("", "selectedAmp"): "2",
        ("parameters", "outputGain"): 0.0,
        (f"{AMP}EQ", f"{AMP}EQBand5"): 6.0,
    }
    off_first = {**base, (f"{AMP}EQ", f"{AMP}EQActive"): False}
    off_second = {**base, ("eqParameters", "sectionActive"): False}

    assert invert._eq_is_active(path, off_first, "morgan") is False
    assert invert._eq_is_active(path, off_second, "morgan") is False, (
        "declaration order must not decide this"
    )
    target = measure({f"{AMP}EQ/{AMP}EQActive": True,
                      f"{AMP}EQ/{AMP}EQBand3": 8.0})
    result = invert.invert(target, measure(), amp=AMP,
                           current_settings=off_first)

    assert any(control in result.values for control in path.eq_band_controls), (
        "a bypassed section has a known-zero baseline, so it can be inverted"
    )
    assert not any("in circuit" in caveat for caveat in result.caveats)


def test_eq_delta_bounds_reach_the_opposite_control_rail():
    path = invert._validated_signal_path("morgan", AMP)
    band = f"{AMP}EQ/{AMP}EQBand5"
    current = {
        (f"{AMP}EQ", f"{AMP}EQActive"): True,
        ("eqParameters", "sectionActive"): True,
        (f"{AMP}EQ", f"{AMP}EQBand5"): 12.0,
    }

    lower, upper = invert._band_correction_bounds(path, current, "morgan")
    index = list(path.eq_band_controls).index(band)
    applied = invert._apply_band_corrections(
        invert.Inversion(values={band: -24.0}), path, current, "morgan"
    )

    assert lower[index] == -24.0
    assert upper[index] == 0.0
    assert applied.values[band] == -12.0


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


def test_tone_king_inversion_uses_its_selected_path_and_measured_eq():
    """Flat namespace controls must not be reconstructed as Morgan modules."""
    from match import space as space_module
    from match.renderer import RenderMetadata
    from packs.loader import load_pack

    pack = load_pack("toneking")
    measured_noise = pack.calibration["reused_instance_band_noise_db"]

    class ToneKingBasis:
        def metadata(self):
            return RenderMetadata(
                renderer_id="swift", sample_rate=48000, block_size=512,
                plugin_version="1.0.3", reproducible=False,
                band_noise_db=measured_noise,
                renderer_build="audio-unit-renderer-2af9432f77c6",
                quality_mode=("standard;amplitude=1;settle_ms=0;warmup_s=0;"
                              "isolate=auto;process=reuse"),
            )

        def eq_basis(self, signal_path, analysis_centres):
            return invert.measured_basis(
                "toneking", signal_path, analysis_centres,
                expected_plugin_version="1.0.3",
            )

    target = measure({f"{AMP}EQ/{AMP}EQBand4": 6.0,
                      "parameters/outputGain": -3.0})
    calculated = invert.invert(
        target, measure(), amp="Lead Channel", pack_id="toneking",
        renderer=ToneKingBasis(),
    )

    assert calculated.values["/ampType"] == "Lead Channel"
    assert "/outputGain" in calculated.values
    assert all(f"/eqBand{index}" in calculated.values for index in range(1, 10))
    assert calculated.values["/eqSectionActive"] is True
    assert calculated.values["/eqActive"] is True
    assert not any("sw50r" in path or path.startswith("parameters/")
                   for path in calculated.values)
    assert any("measured" in caveat and "does not repeat" in caveat
               for caveat in calculated.caveats)
    assert any("delay, reverb, tremolo" in caveat
               for caveat in calculated.caveats)

    pack = load_pack("toneking")
    for path, value in calculated.values.items():
        spec = pack.parameters.get(path)
        assert spec is not None, f"{path} is not declared by Tone King"
        pack.to_stored(spec, value, warnings=[])

    # The same values must survive the conditional preset writer. This catches a
    # selector that is valid in isolation but fails to activate the Lead controls.
    document = space_module.build("toneking").to_spec(calculated.as_settings())
    written = {f"/{row['key']}" if not row["module"] else
               f"{row['module']}/{row['key']}"
               for row in document["parameters"]}
    assert "/ampType" in written
    assert all(f"/eqBand{index}" in written for index in range(1, 10))
    assert "/eqSectionActive" in written and "/eqActive" in written


def test_tone_king_template_selector_resolves_the_inversion_path():
    assert invert.selected_signal_path(
        "toneking", {("", "ampType"): "1"}
    ) == "lead"
    assert invert.selected_signal_path(
        "toneking", {"/ampType": "Rhythm Channel"}
    ) == "rhythm"


def test_inversion_does_not_report_a_selector_label_as_a_real_change():
    calculated = invert.invert(
        measure(), measure(), amp="lead", pack_id="toneking",
        current_settings={("", "ampType"): "1"},
    )

    assert "/ampType" not in calculated.values


def test_the_renderer_noise_floor_stops_eq_from_chasing_repeat_variation():
    """Tone King's floor is measured output variation, not a Morgan constant."""
    delta = {100.0: 2.0, 1000.0: -2.0}
    basis = np.eye(2)

    unresolved = invert.fit_graphic_eq(
        delta, [100.0, 1000.0], basis=basis,
        band_controls=["/eqBand1", "/eqBand2"], band_noise_db=5.228794,
    )
    resolved = invert.fit_graphic_eq(
        delta, [100.0, 1000.0], basis=basis,
        band_controls=["/eqBand1", "/eqBand2"], band_noise_db=1.0,
    )

    assert set(unresolved.values.values()) == {0.0}
    assert any("5.22879 dB" in caveat for caveat in unresolved.caveats)
    assert any(value != 0.0 for value in resolved.values.values())


def test_an_outlier_below_the_guitar_band_does_not_floor_the_whole_eq():
    delta = {25.0: 0.0, 100.0: 2.0, 1000.0: -2.0}
    basis = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    noise = {25.0: 5.228794, 100.0: 0.000415, 1000.0: 0.000024}

    result = invert.fit_graphic_eq(
        delta, [100.0, 1000.0], basis=basis,
        band_controls=["/eqBand1", "/eqBand2"], band_noise_db=noise,
    )

    assert any(value != 0.0 for value in result.values.values())
    assert result.detail["eq_noise_max_db"] == pytest.approx(0.000415)
    assert result.detail["eq_effect_max_db"] > result.detail["eq_noise_max_db"]


def test_frequency_aligned_noise_is_compared_at_the_same_frequency():
    delta = {50.0: 0.0, 1000.0: 2.0}
    basis = np.array([[0.0, 1.0]])
    noise = {50.0: 3.5, 1000.0: 0.02}

    result = invert.fit_graphic_eq(
        delta, [1000.0], basis=basis,
        band_controls=["/eqBand1"], band_noise_db=noise,
    )

    assert result.values["/eqBand1"] != 0.0
    assert result.detail["eq_noise_margin_db"] > 0.0


def test_a_modern_basis_from_another_renderer_build_is_refused():
    from match.renderer import RenderMetadata

    found = invert.MeasuredBasis(
        np.eye(1), "measured", renderer_build="audio-unit-renderer-old",
        quality_mode="standard", provenance_schema="eq-basis-provenance-1",
    )

    class Current:
        def metadata(self):
            return RenderMetadata(
                renderer_id="swift", sample_rate=48000, block_size=512,
                renderer_build="audio-unit-renderer-current",
                quality_mode="standard",
            )

    with pytest.raises(invert.InversionError, match="renderer build"):
        invert._validate_basis_provenance(found, Current())


def test_a_modern_basis_from_another_sample_rate_is_refused():
    from match.renderer import RenderMetadata

    found = invert.MeasuredBasis(
        np.eye(1), "measured", renderer_build="audio-unit-renderer-current",
        quality_mode="standard", renderer_id="swift", plugin_version="1.0",
        sample_rate=48000, block_size=512,
        provenance_schema="eq-basis-provenance-1",
    )

    class Current:
        def metadata(self):
            return RenderMetadata(
                renderer_id="swift", sample_rate=44100, block_size=512,
                plugin_version="1.0",
                renderer_build="audio-unit-renderer-current",
                quality_mode="standard",
            )

    with pytest.raises(invert.InversionError, match="sample rate"):
        invert._validate_basis_provenance(found, Current())


@pytest.mark.parametrize(
    "field_name,label",
    [
        ("renderer_id", "renderer id"),
        ("plugin_version", "plugin version"),
        ("sample_rate", "sample rate"),
        ("block_size", "block size"),
        ("quality_mode", "quality mode"),
    ],
)
def test_a_modern_basis_missing_renderer_identity_is_refused(field_name, label):
    from dataclasses import replace
    from match.renderer import RenderMetadata

    found = invert.MeasuredBasis(
        np.eye(1), "measured", renderer_build="audio-unit-renderer-current",
        quality_mode="standard", renderer_id="swift", plugin_version="1.0",
        sample_rate=48000, block_size=512,
        provenance_schema="eq-basis-provenance-1",
    )
    found = replace(found, **{field_name: None})

    class Current:
        def metadata(self):
            return RenderMetadata(
                renderer_id="swift", sample_rate=48000, block_size=512,
                plugin_version="1.0",
                renderer_build="audio-unit-renderer-current",
                quality_mode="standard",
            )

    with pytest.raises(invert.InversionError, match=f"missing {label}"):
        invert._validate_basis_provenance(found, Current())


def test_output_level_refuses_a_control_without_db_units(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        invert, "declared",
        lambda pack_id, path: SimpleNamespace(min=-24, max=24, unit=None),
    )
    with pytest.raises(invert.InversionError, match="unit 'db'"):
        invert.output_level(measure(), measure())


def test_overlapping_eq_moves_are_compared_with_the_floor_together():
    # A synthetic floor chosen so neither overlapping row clears it alone while
    # their combined correction does. This is not a Tone King measurement.
    delta = {100.0: 4.0, 1000.0: -4.0}
    basis = np.array([[1.0, -1.0], [1.0, -1.0]])

    result = invert.fit_graphic_eq(
        delta, [100.0, 1000.0], basis=basis,
        band_controls=["/eqBand1", "/eqBand2"], band_noise_db=3.505611,
    )

    assert all(value != 0.0 for value in result.values.values())


def test_tone_king_unknown_signal_path_names_the_valid_choices():
    with pytest.raises(invert.InversionError, match="Accepted: rhythm, lead"):
        invert.invert(measure(), measure(), amp="clean", pack_id="toneking")


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


def test_the_fit_is_weighted_towards_the_range_a_guitar_occupies():
    """A third-octave curve's extremes are the source's own filtering, not the amp's,
    and letting 25 Hz pull on the fit moves 65 Hz to chase it. Replacing the weights
    with ones changed no test, so the comment was the only thing saying this.
    """
    from analysis.features import THIRD_OCTAVE_CENTRES

    centres = sorted(float(f) for f in THIRD_OCTAVE_CENTRES)
    band_centres = invert._band_centres("morgan", AMP)
    assert centres[1] < 50.0 <= centres[3], "the split has to straddle 50 Hz"

    def band1_for(selected):
        """The lowest band's gain for a 20 dB deficit over exactly these centres."""
        delta = {f: (-20.0 if f in selected else 0.0) for f in centres}
        mean = sum(delta.values()) / len(delta)   # mean-free: the fit reads shape
        delta = {f: value - mean for f, value in delta.items()}
        return invert.fit_graphic_eq(delta, band_centres, module=AMP,
                                     pack_id="morgan").values[f"{AMP}EQ/{AMP}EQBand1"]

    below = band1_for(set(centres[:2]))       # 25 and 31.5 Hz
    inside = band1_for(set(centres[3:6]))     # 50, 63 and 80 Hz

    assert inside < -6.0, f"a deficit in the guitar's range moves the band: {inside}"
    # A 20 dB hole at 25 Hz must not pull the 65 Hz band down at all. Unweighted the
    # same input gives -1.09, so the sign is the discriminator, not a tolerance.
    assert below > 0.0, f"25-31.5 Hz pulled the lowest band to {below}"
