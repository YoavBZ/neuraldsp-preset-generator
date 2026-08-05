"""The search space: what may be moved, when it matters, and what comes out.

Built from the manifest, so most of what is checked here is that the space agrees
with the pack rather than with a list someone typed.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

import numpy as np

from match import space as S
from packs.loader import PackError, load_pack

ALL_OFF = {
    ("delay", "delayActive"): False, ("reverb", "reverbActive"): False,
    ("compressor", "compressorActive"): False, ("drive1", "drive1Active"): False,
    ("drive2", "drive2Active"): False, ("tremolo", "tremoloActive"): False,
    ("parameters", "gateActive"): False, ("parameters", "doublerActive"): False,
    ("cabParameters", "leftCabActive"): False, ("cabParameters", "rightCabActive"): False,
    ("cabParameters", "leftRoomActive"): False, ("cabParameters", "rightRoomActive"): False,
    ("cabParameters", "sectionActive"): False,
    ("sw50rEQ", "sw50rEQActive"): False, ("pr12EQ", "pr12EQActive"): False,
    ("ac20EQ", "ac20EQActive"): False,
}


@pytest.fixture(scope="module")
def space():
    return S.build("morgan")


def complete(space, overrides=None):
    """A legal value for every dimension, so `to_spec` has something to emit."""
    values = {}
    for dimension in space.dimensions:
        if dimension.switch:
            values[(dimension.module, dimension.key)] = False
        elif dimension.kind == "enum":
            values[(dimension.module, dimension.key)] = int(
                sorted(dimension.members, key=int)[0])
        else:
            low, high = dimension.bounds()
            values[(dimension.module, dimension.key)] = round((low + high) / 2, 3)
    values[("", "selectedAmp")] = 2
    values.update(ALL_OFF)
    values.update(overrides or {})
    return values


# --- what is in it ----------------------------------------------------------


def test_the_space_excludes_what_cannot_be_searched(space):
    """Each exclusion is a category, not a name: strings, paths, read-only
    parameters, and selectors whose member names the manifest does not know."""
    pack = load_pack("morgan")
    for path, reason in space.excluded.items():
        spec = pack.parameters[path]
        assert (
            spec.kind in S.UNSEARCHABLE_KINDS
            or not spec.writable
            or (spec.kind in ("enum", "switch") and not spec.members)
            or spec.needs_confirmation
            or spec.needs_review
        ), f"{path} was excluded for {reason!r} but looks searchable"

    assert space.excluded, "morgan has read-only and unknown-selector parameters"
    assert len(space) + len(space.excluded) == len(pack.parameters)


def test_a_guessed_kind_is_left_out_unless_asked_for():
    """A wrong `kind` picks the human-to-stored mapping, so it writes a plausible
    number instead of failing — the one error nothing downstream notices."""
    strict = S.build("morgan")
    permissive = S.build("morgan", include_needs_review=True)
    assert len(permissive) >= len(strict)
    for reason in strict.excluded.values():
        if "bootstrap guess" in reason:
            assert len(permissive) > len(strict)
            break


def test_every_continuous_dimension_has_a_range_to_search(space):
    for dimension in space.dimensions:
        if dimension.continuous:
            low, high = dimension.bounds()
            assert high > low, dimension.path


def test_enums_carry_their_members_and_switches_need_not(space):
    """An enum's stored integer means nothing without the table, and the plugin
    never displays it — so one without members cannot be chosen on purpose.

    A switch is the opposite case and the distinction matters: its states are true
    and false whatever the plugin labels them, so requiring members took every
    effect on/off control out of the space and nothing could turn an effect on.
    """
    for dimension in space.dimensions:
        if dimension.kind == "enum":
            assert dimension.members, dimension.path

    switches = [d for d in space.dimensions if d.switch]
    assert switches, "the effect gates have to be in the space"
    assert any(not d.members for d in switches), (
        "morgan declares members for only some switches; the rest must still be here"
    )
    assert {"delay/delayActive", "reverb/reverbActive"} <= {d.path for d in switches}


# --- conditioning -----------------------------------------------------------


def test_only_the_selected_amp_is_live(space):
    """Morgan carries all three amps in every preset and writing the inactive
    one's controls is a silent no-op, so a search over them would spend its budget
    learning that tone stacks do nothing."""
    for stored, prefix in (("2", "sw50r"), ("0", "ac20"), ("1", "pr12")):
        values = complete(space, {("", "selectedAmp"): int(stored)})
        live = {d.module for d in space.active(values)}
        assert any(m.startswith(prefix) for m in live), f"{prefix} should be live"
        for other in ("sw50r", "ac20", "pr12"):
            if other != prefix:
                assert not any(m.startswith(other) for m in live), (
                    f"{other} is live while {prefix} is selected"
                )


def test_an_effect_behind_its_switch_is_dormant_until_the_switch_is_on(space):
    off = complete(space)
    on = complete(space, {("delay", "delayActive"): True})

    dormant = {d.path for d in space.dormant(off)}
    assert "delay/delayTime" in dormant
    assert "delay/delayTime" not in {d.path for d in space.dormant(on)}


def test_a_switch_is_never_gated_by_itself(space):
    """Otherwise it would be unreachable the moment it went off, and a search
    could not turn an effect back on."""
    for dimension in space.dimensions:
        assert dimension.gate != (dimension.module, dimension.key), dimension.path


def test_the_gate_of_each_parameter_is_the_most_specific_switch_that_covers_it(space):
    """`leftCabPan` belongs to `leftCabActive`, not to the whole cab section."""
    gates = {d.path: d.gate for d in space.dimensions}
    assert gates["cabParameters/leftCabPan"] == ("cabParameters", "leftCabActive")
    assert gates["cabParameters/leftRoomMicLevel"] == ("cabParameters", "leftRoomActive")
    assert gates["parameters/gateThreshold"] == ("parameters", "gateActive")
    assert gates["sw50rEQ/sw50rEQBand1"] == ("sw50rEQ", "sw50rEQActive")
    # And a parameter with no switch of its own is not invented one.
    assert gates["parameters/inputGain"] is None


def test_restricting_the_space_to_one_amp_drops_the_others():
    only = S.build("morgan", amp="sw50r")
    paths = {d.path for d in only.dimensions}
    assert any(p.startswith("sw50r") for p in paths)
    assert not any(p.startswith(("ac20", "pr12")) for p in paths)


# --- vectors ----------------------------------------------------------------


def test_a_vector_round_trips_to_within_the_quantisation(space):
    values = complete(space)
    recovered = space.decode(space.encode(values))

    for dimension in space.dimensions:
        key = (dimension.module, dimension.key)
        before, after = values[key], recovered[key]
        if dimension.switch:
            assert bool(before) == bool(after), dimension.path
        elif dimension.kind == "enum":
            assert int(before) == int(after), dimension.path
        else:
            step = dimension.quantum or 0.001
            assert abs(float(before) - float(after)) <= step, dimension.path


def test_the_vector_length_does_not_change_when_a_switch_flips(space):
    """An optimiser needs a stable shape across trials: dropping a dimension
    mid-run would change what every earlier sample meant."""
    off = space.encode(complete(space))
    on = space.encode(complete(space, {("delay", "delayActive"): True}))
    assert len(off) == len(on) == len(space.dimensions)


def test_the_vector_stays_inside_the_unit_cube(space):
    vector = space.encode(complete(space))
    assert vector.min() >= 0.0 and vector.max() <= 1.0


def test_decoding_the_extremes_gives_the_declared_endpoints(space):
    low = space.decode(np.zeros(len(space.dimensions)))
    high = space.decode(np.ones(len(space.dimensions)))
    for dimension in space.dimensions:
        if not dimension.continuous:
            continue
        bottom, top = dimension.bounds()
        key = (dimension.module, dimension.key)
        assert low[key] == pytest.approx(bottom, abs=dimension.quantum or 0.001)
        assert high[key] == pytest.approx(top, abs=dimension.quantum or 0.001)


def test_a_wrong_length_vector_is_refused(space):
    with pytest.raises(S.SpaceError, match="dimensions"):
        space.decode(np.zeros(len(space.dimensions) - 1))


# --- output -----------------------------------------------------------------


def test_every_value_in_an_emitted_spec_is_one_the_pack_accepts(space):
    """The point of emitting a spec rather than preset bytes: the winner of a
    search goes through exactly the validation a hand-authored preset does."""
    pack = load_pack("morgan")
    values = complete(space, {
        ("", "selectedAmp"): 2,
        ("reverb", "reverbActive"): True,
        ("sw50rEQ", "sw50rEQActive"): True,
        ("cabParameters", "sectionActive"): True,
        ("cabParameters", "leftCabActive"): True,
    })
    spec = space.to_spec(values, name="Matched")

    assert spec["name"] == "Matched"
    assert spec["parameters"]
    for entry in spec["parameters"]:
        path = f"{entry['module']}/{entry['key']}" if entry["module"] else f"/{entry['key']}"
        pack.to_stored(pack.parameters[path], entry["value"], warnings=[])


def test_an_emitted_spec_does_not_set_the_inactive_amp(space):
    """A preset that sets the unselected amp's treble to whatever the optimiser
    last sampled is noise in a file someone may read."""
    values = complete(space, {("", "selectedAmp"): 2})
    spec = space.to_spec(values)

    touched = {f"{p['module']}/{p['key']}" for p in spec["parameters"]}
    assert not any(p.startswith("ac20Amp") or p.startswith("pr12Amp") for p in touched)
    assert any(p.startswith("sw50r") for p in touched)


def test_the_switches_are_always_written_so_what_is_off_is_explicit(space):
    values = complete(space)
    spec = space.to_spec(values)
    written = {f"{p['module']}/{p['key']}" for p in spec["parameters"]}
    assert "delay/delayActive" in written
    assert "reverb/reverbActive" in written
    # ... while what they gate is not, because it is dormant.
    assert "delay/delayTime" not in written


def test_the_dormant_dimensions_can_be_included_when_asked(space):
    values = complete(space)
    lean = space.to_spec(values)
    everything = space.to_spec(values, include_dormant=True)
    assert len(everything["parameters"]) > len(lean["parameters"])
