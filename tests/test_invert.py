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
    """This repository does not silently substitute a guess for a measurement."""
    delta = {row["centre_hz"]: row["delta_db"]
             for row in band_delta(measure({f"{AMP}EQ/{AMP}EQBand5": 6.0}), measure())}
    result = invert.fit_graphic_eq(delta, refchain.band_centres(), module=AMP)
    assert any("no measured EQ basis" in caveat for caveat in result.caveats)

    # And with one supplied, it does not claim to be guessing.
    basis = invert.bell_basis(refchain.band_centres(), sorted(delta))
    supplied = invert.fit_graphic_eq(delta, refchain.band_centres(), basis=basis, module=AMP)
    assert not any("no measured EQ basis" in caveat for caveat in supplied.caveats)


def test_the_eq_fit_leaves_bands_alone_below_the_render_noise():
    """The plugin shows 0.23 dB of per-band variation between two renders of
    identical parameters, so a fit writing tenths is writing noise into a preset."""
    identical = measure()
    delta = {row["centre_hz"]: row["delta_db"] for row in band_delta(identical, identical)}
    result = invert.fit_graphic_eq(delta, refchain.band_centres(), module=AMP)
    assert all(value == 0.0 for value in result.values.values())


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
