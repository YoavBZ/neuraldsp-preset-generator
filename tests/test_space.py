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
            or not spec.searchable
            or (spec.kind in ("enum", "switch") and not spec.members)
            or spec.needs_confirmation
            or spec.needs_review
        ), f"{path} was excluded for {reason!r} but looks searchable"

    assert space.excluded, "morgan has read-only and unknown-selector parameters"
    assert len(space) + len(space.excluded) == len(pack.parameters)


def test_a_guessed_kind_is_left_out_unless_asked_for():
    """A wrong `kind` picks the human-to-stored mapping, so it writes a plausible
    number instead of failing — the one error nothing downstream notices.

    Asserted against the rule directly, because neither shipped pack has a
    `needs_review` parameter: `build("morgan")` and
    `build("morgan", include_needs_review=True)` are both 126 dimensions, so
    comparing their lengths was `126 >= 126` and could not fail. Deleting the
    exclusion entirely passed.
    """
    from packs.loader import ParamSpec

    guessed = ParamSpec(module="fx", key="fxDepth", kind="rotation", needs_review=True)

    assert S._exclusion_reason(guessed, include_needs_review=False) is not None
    assert "guess" in S._exclusion_reason(guessed, include_needs_review=False)
    assert S._exclusion_reason(guessed, include_needs_review=True) is None

    # And a parameter with nothing wrong with it is not excluded either way.
    sound = ParamSpec(module="fx", key="fxDepth", kind="rotation")
    assert S._exclusion_reason(sound, include_needs_review=False) is None


def test_every_exclusion_rule_actually_excludes():
    """The other direction, which nothing checked.

    The suite asserted that everything *excluded* looked excludable, which holds
    however the split falls — dropping the read-only guard, the
    `needs_confirmation` guard or the enum-members guard each passed. Three of the
    four categories are also masked on Morgan (its only read-only parameter is also
    a string), so they need constructing to be testable at all.
    """
    from packs.loader import ParamSpec

    cases = [
        ("read-only", ParamSpec(module="", key="v", kind="rotation", writable=False)),
        ("utility", ParamSpec(module="", key="v", kind="metered",
                              searchable=False)),
        ("string", ParamSpec(module="", key="v", kind="string")),
        ("path", ParamSpec(module="", key="v", kind="path")),
        ("internal", ParamSpec(module="", key="v", kind="internal")),
        ("enum with no members", ParamSpec(module="", key="v", kind="enum")),
        ("unconfirmed", ParamSpec(module="", key="v", kind="rotation",
                                  needs_confirmation=True)),
    ]
    for label, spec in cases:
        assert S._exclusion_reason(spec, include_needs_review=False) is not None, label

    # A switch without members is deliberately *not* excluded: see
    # test_enums_carry_their_members_and_switches_need_not.
    switch = ParamSpec(module="", key="v", kind="switch")
    assert S._exclusion_reason(switch, include_needs_review=False) is None


def test_pitch_transpose_is_writable_but_not_tone_searchable(space):
    """A different melody must not make the matcher transpose the guitarist.

    The control remains in the pack contract so specs can deliberately write it;
    only the generated tone-search space excludes it.
    """
    pack = load_pack("morgan")
    transpose = pack.parameters["parameters/transpose"]
    assert transpose.writable and not transpose.searchable
    assert "parameters/transpose" in space.excluded
    with pytest.raises(S.SpaceError):
        space.by_path("parameters", "transpose")


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


def test_tone_king_channel_controls_follow_amp_type():
    toneking = S.build("toneking")
    rhythm = {d.path for d in toneking.active({"ampType": "Rhythm Channel"})}
    lead = {d.path for d in toneking.active({"/ampType": 1})}

    assert "rhythmAmpVolume" in rhythm
    assert "leadAmpVolume" not in rhythm
    assert "leadAmpTone" in lead
    assert "rhythmAmpTreble" not in lead


def test_an_absent_tone_king_channel_selector_does_not_guess():
    toneking = S.build("toneking")
    live = {d.path for d in toneking.active({})}
    assert "rhythmAmpVolume" in live
    assert "leadAmpVolume" in live


def test_a_switch_is_never_gated_by_a_prefix_sibling(space):
    """Tone King keeps every parameter in one flat module, where `/eqActive` (stem
    `eq`) matches `/eqSectionActive` as though the page bypass were a child of the
    band bypass. That inverted the nesting exactly backwards: it reported the
    section bypass dormant, and reported `eqBand1` *active* while the EQ page was
    bypassed.
    """
    for pack_id in ("morgan", "toneking"):
        built = S.build(pack_id)
        stems = {(d.module, d.key[: -len("Active")])
                 for d in built.dimensions
                 if d.switch and d.key.endswith("Active")}
        for dimension in built.dimensions:
            if not (dimension.switch and dimension.key.endswith("Active")):
                continue
            if dimension.gate is None:
                continue
            gate_module, gate_key = dimension.gate
            stem = gate_key[: -len("Active")]
            assert stem == "section", (
                f"{pack_id}: {dimension.path} is gated by {gate_key}, which is a "
                f"prefix sibling rather than a parent"
            )
            assert (gate_module, stem) in stems or stem == "section"

    toneking = S.build("toneking")
    section = toneking.by_path("", "eqSectionActive")
    band_bypass = toneking.by_path("", "eqActive")
    assert section.gate is None and band_bypass.gate is None
    assert toneking.by_path("", "eqBand1").gate == ("", "eqActive")


def test_a_section_switch_does_gate_the_switches_under_it(space):
    """The narrower rule, which the first fix overshot.

    Ruling out every switch-on-switch gate cost four correct gates on Morgan — the
    cab section really does bypass `leftCabActive` — for nothing on Tone King, whose
    defect was the prefix match alone. Asserted by name so widening the rule back
    out fails here.
    """
    morgan = S.build("morgan")
    for key in ("leftCabActive", "rightCabActive", "leftRoomActive", "rightRoomActive"):
        assert morgan.by_path("cabParameters", key).gate == (
            "cabParameters", "sectionActive"), key
    assert morgan.by_path("cabParameters", "sectionActive").gate is None


def test_bypassing_a_section_silences_everything_under_it(space):
    """Gates compose, and checking only the immediate gate did not.

    `cabParameters/sectionActive` gates `leftCabActive`, which gates `leftCabPan`.
    With only the immediate gate checked, 15 of Morgan's 21 cab dimensions were
    reported live behind a switch that silences all 21.
    """
    morgan = S.build("morgan")
    values = {"selectedAmp": 2}
    for dimension in morgan.dimensions:
        if dimension.switch:
            values[(dimension.module, dimension.key)] = True

    cab = [d for d in morgan.dimensions if d.module == "cabParameters"]
    assert len(cab) == 21
    live = [d for d in morgan.active(values) if d.module == "cabParameters"]
    assert len(live) == 21, "with everything on, every cab control is live"

    values[("cabParameters", "sectionActive")] = False
    live = [d for d in morgan.active(values) if d.module == "cabParameters"]
    # Only the section switch itself, which has to stay reachable to be turned back
    # on. Every one of the other 20 is behind it, directly or one level down.
    assert [d.key for d in live] == ["sectionActive"]


def test_the_section_switches_that_gate_nothing_are_named(space):
    """Reported rather than papered over.

    Four of Morgan's five section switches live in modules containing nothing but
    themselves, while the controls they bypass live in `sw50rAmp`, `drive1`, `delay`
    and so on — so module-scoped gating gates nothing for them, and a search will
    move controls inside a bypassed section. Guessing which modules a section covers
    is exactly the unmeasured claim this project refuses, so the limit is named
    instead.
    """
    from packs.loader import load_pack

    morgan = S.unmodelled_sections(load_pack("morgan"))
    assert set(morgan) == {
        "ampParameters/sectionActive", "eqParameters/sectionActive",
        "fxParameters/sectionActive", "pedalParameters/sectionActive",
    }
    # The one that does work, because the cab controls share its module.
    assert "cabParameters/sectionActive" not in morgan

    # And Tone King's, which are spelled differently and were being missed entirely.
    toneking = S.unmodelled_sections(load_pack("toneking"))
    assert toneking, "checking for the literal 'sectionActive' found none of these"
    assert all("ection" in path for path in toneking)


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


def test_a_rotation_searches_its_whole_travel(space):
    """`bounds()` was only ever compared against itself.

    Every expected endpoint in this file came from `bounds()`, the function under
    test, and the fixture derived its values from it too — so changing the rotation
    range from 0..100 to 0..1 kept the round trip self-consistent and passed, while
    leaving all 31 knobs searching the bottom 1% of their travel. `pack.to_stored`
    does not range-check a rotation either, so nothing downstream objects.
    """
    rotation = next(d for d in space.dimensions if d.kind == "rotation")
    assert rotation.bounds() == (0.0, 100.0), (
        f"{rotation.path} is a percent, so a search over it must span 0..100"
    )

    fraction = next(d for d in space.dimensions if d.kind == "fraction")
    assert fraction.bounds() == (0.0, 1.0)

    # And a full-scale vector really does reach the top of a knob.
    top = space.decode(np.ones(len(space.dimensions)))
    assert top[(rotation.module, rotation.key)] == pytest.approx(100.0)


def test_a_switch_can_be_turned_on_through_the_vector(space):
    """Nothing could. The fixture set every switch `False`, so the round-trip
    assertion was only ever `False == False`, and hardcoding `_to_unit` to 0.0 or
    `_from_unit` to `False` both passed — the vector-space form of the very
    regression this module's docstring memorialises.
    """
    values = complete(space, {("delay", "delayActive"): True,
                              ("reverb", "reverbActive"): True})
    recovered = space.decode(space.encode(values))

    assert recovered[("delay", "delayActive")] is True
    assert recovered[("reverb", "reverbActive")] is True
    assert recovered[("compressor", "compressorActive")] is False

    # And the coordinate itself distinguishes them.
    index = next(i for i, d in enumerate(space.dimensions)
                 if d.path == "delay/delayActive")
    assert space.encode(values)[index] == 1.0
    assert space.encode(complete(space))[index] == 0.0


def test_decoded_values_land_on_a_quantised_step(space):
    """Quantisation was named in a test title and asserted nowhere: emptying
    `QUANTA`, or making `quantise` a no-op, made the round trip *more* exact and so
    greener. It is only ever used as a tolerance elsewhere.
    """
    import numpy as np

    rng = np.random.default_rng(4)
    decoded = space.decode(rng.random(len(space.dimensions)))

    checked = 0
    for dimension in space.dimensions:
        if not dimension.continuous or not dimension.quantum:
            continue
        value = decoded[(dimension.module, dimension.key)]
        steps = value / dimension.quantum
        assert steps == pytest.approx(round(steps), abs=1e-6), (
            f"{dimension.path} decoded to {value}, not a multiple of "
            f"{dimension.quantum}"
        )
        checked += 1
    assert checked > 50, "most of morgan's continuous dimensions carry a quantum"


def test_a_value_outside_its_range_is_clamped(space):
    """`clamp` was never exercised out of range — the fixture only used mid-range
    values, so removing the clamp from `Dimension`, from `_to_unit` and from
    `_from_unit` all passed."""
    gain = next(d for d in space.dimensions if d.path == "parameters/inputGain")
    low, high = gain.bounds()

    assert gain.clamp(high + 500.0) == high
    assert gain.clamp(low - 500.0) == low

    # And through the vector: an out-of-range human value encodes at the edge.
    values = complete(space, {("parameters", "inputGain"): high + 500.0})
    index = next(i for i, d in enumerate(space.dimensions)
                 if d.path == "parameters/inputGain")
    assert space.encode(values)[index] == 1.0


def test_encoding_refuses_a_value_it_was_not_given(space):
    """Zero is a real coordinate — the bottom of every range — so treating a missing
    key as zero silently invented a hard-left pan, a mic 40 dB down and a 16 ms
    delay, and `to_spec` would have written them."""
    with pytest.raises(S.SpaceError, match="no value"):
        space.encode({("", "selectedAmp"): 2})

    # Opt in, if the floor is genuinely what you mean.
    vector = space.encode({("", "selectedAmp"): 2}, missing="floor")
    assert len(vector) == len(space.dimensions)


def test_an_enum_value_the_pack_does_not_have_is_refused(space):
    """It used to become member index 0, so `"SW50R"` — the spelling `amp_prefix`
    promises to accept — round-tripped to a *different amp*, and so did `99`."""
    values = complete(space)

    values[("", "selectedAmp")] = "SW50R"
    assert space.decode(space.encode(values))[("", "selectedAmp")] == 2

    values[("", "selectedAmp")] = 99
    with pytest.raises(S.SpaceError, match="not one of its members"):
        space.encode(values)


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
    """Including a switch that is itself dormant, which is the only case the rule
    exists for.

    The two switches checked before — `delayActive` and `reverbActive` — have no
    gate of their own, so they were already in `active()` and the clause that keeps
    dormant switches did nothing for them. Deleting it passed.
    """
    values = complete(space)
    spec = space.to_spec(values)
    written = {f"{p['module']}/{p['key']}" for p in spec["parameters"]}

    assert "delay/delayActive" in written
    assert "reverb/reverbActive" in written
    # ... while what they gate is not, because it is dormant.
    assert "delay/delayTime" not in written

    # `delayPingPong` is a switch that is *itself* gated — by `delayActive`, which
    # is off here. It is dormant, and must still be written, or a reader could not
    # tell ping-pong is off. (Switches named `*Active` are never gated, so they
    # could not exercise this clause; one that is not is needed.)
    ping_pong = space.by_path("delay", "delayPingPong")
    assert ping_pong.gate == ("delay", "delayActive")
    assert ping_pong.path in {d.path for d in space.dormant(values)}
    assert ping_pong.path in written


def test_the_spec_names_the_selected_amp(space):
    """Deleting the `selectedAmp` block passed: sw50r's own controls were still
    present, so nothing noticed that the preset never said which amp to use."""
    spec = space.to_spec(complete(space, {("", "selectedAmp"): 2}))
    entries = {(p["module"], p["key"]): p["value"] for p in spec["parameters"]}
    assert ("", "selectedAmp") in entries
    assert entries[("", "selectedAmp")] == 2


def test_the_spec_carries_the_name_it_was_given(space):
    """`name="Matched"` is also the default, so hardcoding the default passed."""
    spec = space.to_spec(complete(space), name="Hotel California clean")
    assert spec["name"] == "Hotel California clean"


def test_the_dormant_dimensions_can_be_included_when_asked(space):
    values = complete(space)
    lean = space.to_spec(values)
    everything = space.to_spec(values, include_dormant=True)
    assert len(everything["parameters"]) > len(lean["parameters"])


# --- value helpers ----------------------------------------------------------


def test_a_gate_nobody_mentioned_does_not_drop_what_is_behind_it():
    """`_truthy(None)` is False, so an absent `*Active` switch marked its whole
    subtree dormant and `to_spec` silently dropped it — the same class of silent
    drop the missing-`selectedAmp` refusal exists to prevent, one line lower:

        to_spec({"selectedAmp": 2, "sw50rEQ/sw50rEQBand1": 6.0})
          -> [{"module": "", "key": "selectedAmp", "value": 2}]

    Absence is not a measurement of off. The template's own switch decides.
    """
    built = S.build("morgan")
    for supplied in ({("sw50rEQ", "sw50rEQBand1"): 6.0},
                     {("delay", "delayTime"): 400.0},
                     {("cabParameters", "leftCabPan"): 30.0}):
        values = {("", "selectedAmp"): 2, **supplied}
        written = {(p["module"], p["key"]): p["value"]
                   for p in built.to_spec(values)["parameters"]}
        (key, value), = supplied.items()
        assert written.get(key) == value, f"{key} was dropped: {sorted(written)}"

    # And a gate the caller *did* turn off still drops its subtree, so this is not
    # "gates no longer work".
    off = {("", "selectedAmp"): 2, ("delay", "delayActive"): False,
           ("delay", "delayTime"): 400.0}
    written = {(p["module"], p["key"]) for p in built.to_spec(off)["parameters"]}
    assert ("delay", "delayActive") in written, "the switch is always written"
    assert ("delay", "delayTime") not in written, "and what it gates is not"


def test_a_switch_reads_a_number_as_a_number():
    """`from_binary("switch", x)` matches the literal `"true"` and `"1"` — the two
    spellings a preset file uses — so delegating the numeric test to it read every
    other number as *off*. `_truthy(1.0)` was False while
    `to_binary("switch", 1.0)` writes `"true"`: `active()` reported a delay's time
    and mix dormant, `to_spec` dropped both, and the preset came out with the delay
    switched on and the template's own settings.
    """
    from format.translate import to_binary

    for value in (1, 1.0, 2, 2.0, -1, np.float64(1.0), True, "1", "true", "on",
                  "yes", "Active", "  ENABLED  "):
        assert S._truthy(value) is True, repr(value)
    for value in (0, 0.0, False, None, "0", "false", "off", "Inactive", "",
                  "maybe", "Bypassed", np.float64(0.0)):
        assert S._truthy(value) is False, repr(value)

    # And the two ends of the round trip agree about every numeric spelling, which
    # is the property that was broken.
    for value in (0, 1, 1.0, 0.0, np.float64(1.0)):
        written = to_binary("switch", value)
        assert (written == "true") is S._truthy(value), (value, written)


def test_a_selector_refuses_a_value_between_two_members(space):
    """`_member_index` floored a non-integral value and `pack.to_stored` rounds it,
    so `1.7` resolved to PR12 at one end of the round trip and SW50R at the other.
    The docstring says it refuses anything that is not a member."""
    from packs.loader import load_pack

    selector = space.by_path("", "selectedAmp")
    members = sorted(selector.members, key=int)

    # Every spelling that does name a member.
    for value in (2, "2", 2.0, "2.0", "SW50R", "sw50r", "  SW50R  "):
        assert S._member_index(selector, members, value) == members.index("2"), value

    # And the ones that do not, including the between-two-members case and the
    # overflow `int(float("inf"))` raises, which `except (ValueError, TypeError)`
    # did not catch.
    for value in (1.7, 0.5, 99, "99", -1, "", "Marshall", float("inf"), float("nan")):
        with pytest.raises(S.SpaceError):
            S._member_index(selector, members, value)

    # The writer's own opinion of 1.7, which is where the disagreement showed.
    pack = load_pack("morgan")
    assert pack.to_stored(pack.parameters["/selectedAmp"], 1.7) == "2"


def test_encode_and_decode_ask_for_the_extra_before_using_it():
    """A bare clone gets one actionable line, not an ImportError from six frames
    down. Pinned by *call*, not by import: `match.space` imports fine without numpy,
    so the existing import test could not see these three."""
    from tests.test_no_dependencies import run_without_analysis

    result = run_without_analysis(
        """
        from analysis import AnalysisUnavailable
        from match import invert, space

        built = space.build("morgan")
        calls = {
            "encode": lambda: built.encode({}, missing="floor"),
            "decode": lambda: built.decode([0.0] * len(built)),
            "bell_basis": lambda: invert.bell_basis([100.0], [100.0]),
        }
        for name, call in calls.items():
            try:
                call()
            except AnalysisUnavailable as e:
                assert "pip install" in str(e), (name, str(e))
            else:
                raise SystemExit(name + " did not ask for the extra")
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
