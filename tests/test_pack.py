"""The pack manifest is the contract: completeness, agreement, and validation."""

from __future__ import annotations

import pytest

from format.parser import parse_file
from format.structured import build
from packs.loader import PackError, detect_pack, list_packs, load_pack
from packs.paths import all_presets

# Every preset this installation can see: the bundled example plus anything the
# user has added to their own template directories.
SAMPLE_FILES = all_presets(list_packs())

TRANSLATABLE_KINDS = {
    "rotation", "fraction", "metered", "switch", "enum", "path", "string",
}


@pytest.fixture(scope="module")
def pack():
    return load_pack("morgan")


def test_pack_is_discoverable(pack):
    assert "morgan" in list_packs()
    assert detect_pack("morgan").pack_id == "morgan"
    assert detect_pack("definitely-not-a-plugin") is None


def test_every_kind_is_translatable(pack):
    """A kind the translator doesn't understand would fail at write time."""
    for spec in pack.parameters.values():
        assert spec.kind in TRANSLATABLE_KINDS, f"{spec.path} has kind {spec.kind!r}"


def pack_for(preset):
    """The pack that actually describes this preset.

    These run over every preset the installation can see, which now spans more
    than one plugin. Checking a Tone King preset against Morgan's manifest
    reports 259 missing parameters and says nothing true.
    """
    found = detect_pack(preset.file_header)
    if found is None:
        pytest.skip(f"no pack for file header {preset.file_header!r}")
    return found


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_manifest_covers_every_parameter_in_sample(sample, pack):
    """Any parameter present in a real preset must be described by the manifest,
    or the agent can neither read it nor write it."""
    preset = build(parse_file(str(sample)))
    pack = pack_for(preset)
    missing = [
        f"{p.module_path}/{p.key}"
        for p in preset.parameters
        if pack.get(p.module_path, p.key) is None
    ]
    assert not missing, f"{sample.name} has parameters absent from the manifest: {missing}"


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_declared_ranges_admit_real_values(sample, pack):
    """A declared range that excludes a value from a real preset is a bug in the
    manifest, not in the preset. This is the guard against transcribing a wrong
    range from the config reference."""
    preset = build(parse_file(str(sample)))
    pack = pack_for(preset)
    for p in preset.parameters:
        spec = pack.get(p.module_path, p.key)
        if spec is None or (spec.min is None and spec.max is None):
            continue
        try:
            value = float(p.value)
        except ValueError:
            continue
        lo = spec.min if spec.min is not None else float("-inf")
        hi = spec.max if spec.max is not None else float("inf")
        assert lo <= value <= hi, (
            f"{sample.name}: {spec.path}={value} is outside the manifest's "
            f"declared range [{spec.min}, {spec.max}] (source: {spec.range_source})"
        )


@pytest.mark.parametrize("sample", SAMPLE_FILES, ids=lambda p: p.name)
def test_declared_enum_values_are_members(sample, pack):
    """Every selector value in a real preset must be a declared member."""
    preset = build(parse_file(str(sample)))
    pack = pack_for(preset)
    for p in preset.parameters:
        spec = pack.get(p.module_path, p.key)
        if spec is None or spec.kind != "enum" or not spec.members:
            continue
        assert str(int(float(p.value))) in spec.members, (
            f"{sample.name}: {spec.path}={p.value} is not a declared member "
            f"({sorted(spec.members)})"
        )


# --- validation ------------------------------------------------------------


def test_enum_out_of_range_is_rejected(pack):
    spec = pack.require("", "selectedAmp")
    with pytest.raises(PackError, match="not a valid selector"):
        pack.to_stored(spec, 7)


def test_enum_accepts_member_name(pack):
    assert pack.to_stored(pack.require("", "selectedAmp"), "PR12") == "1"
    assert pack.to_stored(pack.require("", "selectedAmp"), "sw50r") == "2"
    assert pack.to_stored(pack.require("cabParameters", "rightMicType"), "Ribbon 121") == "8"


def test_enum_rejects_unknown_member_name(pack):
    with pytest.raises(PackError, match="unknown value"):
        pack.to_stored(pack.require("", "selectedAmp"), "Marshall JCM800")


def test_unknown_mic_index_is_rejected(pack):
    with pytest.raises(PackError, match="not a valid selector"):
        pack.to_stored(pack.require("cabParameters", "leftMicType"), 99)


def test_unconfirmed_selector_warns_but_writes(pack):
    warnings: list[str] = []
    # The room mic catalog is the last selector whose member names nobody has
    # read: the plugin publishes no strings for it.
    spec = pack.require("cabParameters", "leftRoomMicType")
    assert pack.to_stored(spec, 1, warnings=warnings) == "1"
    assert len(warnings) == 1
    # The warning has to be actionable: the user cannot read the integer off the
    # plugin UI, so pointing them at the UI would be a dead end.
    assert "probe.py" in warnings[0]
    assert "not known" in warnings[0]


# --- guessed kinds ---------------------------------------------------------
# `needs_review` marks a kind that bootstrap_pack.py guessed from the key name.
# The manifest carried that doubt for 242 of Tone King's 259 parameters while the
# loader dropped it on the floor, so every one of those values was written in
# silence. A wrong kind is not a wrong-looking value: `metered` guessed as
# `rotation` divides by 100 and writes a number the plugin will happily accept.


@pytest.fixture(scope="module")
def draft():
    """A pack whose kinds are still guesses. Morgan's have all been measured."""
    return load_pack("toneking")


def test_guessed_kind_warns_but_writes(draft):
    """Picks a still-guessed parameter rather than naming one.

    Naming one couples this test to how far the pack has been verified: a
    parameter measured against the plugin loses `needs_review`, and hardcoding
    `ampReverb` broke here the moment it was. The property under test is about
    the flag, not about any particular parameter carrying it.
    """
    spec = next(s for s in draft.parameters.values()
                if s.needs_review and s.kind == "rotation" and s.writable)

    warnings: list[str] = []
    assert draft.to_stored(spec, 50, warnings=warnings) == "0.5", (
        "the warning must not block the write — a draft pack is meant to be "
        "usable while it is being corrected"
    )
    assert len(warnings) == 1
    # Actionable in the same sense as the unconfirmed-selector warning: it has to
    # say which kind is in doubt, how to check it, and which file to fix.
    assert "rotation" in warnings[0]
    assert "needs_review" in warnings[0]
    assert "packs/toneking/manifest.json" in warnings[0]


def test_guessed_kind_warns_for_every_guessed_parameter(draft):
    """Not just the one above: the flag is per-parameter, so the warning is too."""
    guessed = [s for s in draft.parameters.values() if s.needs_review]
    # Most of the pack is still guesses; the verified ones are those a probe
    # reached, and that number goes up as more are measured.
    assert len(guessed) > 100, "the Tone King draft is mostly guesses"
    for spec in guessed[:20]:
        warnings: list[str] = []
        draft.to_stored(spec, _plausible(spec), warnings=warnings)
        assert any("guessed kind" in w for w in warnings), spec.path


def test_tone_king_verified_switches_use_the_record_encoding(draft):
    spec = draft.require("", "ampsActive")
    assert spec.kind == "switch"
    assert spec.switch_encoding == "numeric"
    assert draft.to_stored(spec, True, warnings=[]) == "1"
    assert draft.to_stored(spec, False, warnings=[]) == "0"


def test_tone_king_unlabelled_continuous_controls_are_not_enums(draft):
    for key in ("delayHPF", "delayLPF", "reverbPreDelay"):
        spec = draft.require("", key)
        assert spec.kind == "fraction"
        assert spec.members is None
        assert not spec.needs_confirmation


def test_tone_king_mapped_selector_tables_are_confirmed(draft):
    assert draft.require("", "ampAttenuation").members["5"] == "0 dB"
    assert draft.require("", "cab1MicIR").members["16"] == "Custom IR"
    assert draft.require("", "delaySyncNoteL").members["13"] == "1/4"
    assert draft.require("", "wahMode").members == {
        "0": "Auto-Wah OFF", "1": "Auto-Wah ON"
    }
    still_unknown = {
        spec.path for spec in draft.parameters.values() if spec.needs_confirmation
    }
    assert still_unknown == {
        "flangerVHMode", "midiMode", "phaserMode", "reverbMode"
    }


def test_reviewed_parameters_stay_silent(pack):
    """Morgan has been measured against the running plugin. If the new warning
    fires here it is noise, and noise is how a real warning gets ignored."""
    flagged = [spec.path for spec in pack.parameters.values() if spec.needs_review]
    assert not flagged, f"Morgan should carry no guessed kinds: {flagged}"


def test_no_morgan_write_emits_a_review_warning(pack):
    """Stronger than reading the flag: drive the write path for every writable
    parameter, because that is where the warning is actually decided."""
    for spec in pack.parameters.values():
        if not spec.writable:
            continue
        warnings: list[str] = []
        pack.to_stored(spec, _plausible(spec), warnings=warnings)
        assert not any("guessed kind" in w for w in warnings), spec.path


def _plausible(spec) -> object:
    """A value this parameter will accept, whatever its kind.

    Only used to exercise the write path — the point is which warnings come
    back, not what lands in the file.
    """
    if spec.kind == "enum":
        return min(int(k) for k in spec.members) if spec.members else 0
    if spec.kind == "switch":
        return True
    if spec.kind in ("path", "string"):
        return ""
    if spec.kind == "fraction":
        return 0.5
    if spec.kind == "rotation":
        return 50
    # metered: the midpoint of the declared range clears both the range check and
    # the dimensional floor. Undeclared means unchecked, so anything positive does.
    if spec.min is None and spec.max is None:
        return 1
    lo = spec.min if spec.min is not None else spec.max
    hi = spec.max if spec.max is not None else spec.min
    return (lo + hi) / 2


# --- what was measured against the running plugin --------------------------
# These pin facts that cost a measurement to obtain, so that a later edit
# "tidying up" a note cannot quietly undo one. See
# docs/measuring-against-the-plugin.md.


def test_sync_note_tables_are_the_measured_ones(pack):
    delay = pack.require("delay", "delaySyncNote")
    tremolo = pack.require("tremolo", "tremoloSyncNote")
    assert delay.members["13"] == "1/4"
    assert tremolo.members["11"] == "1/4"
    assert len(delay.members) == 21
    assert len(tremolo.members) == 19
    # The two tables are the same list of divisions, but tremolo's starts two
    # entries later. Sharing one table would silently shift every tremolo value.
    assert [delay.members[str(i + 2)] for i in range(19)] == [
        tremolo.members[str(i)] for i in range(19)
    ]


def test_sync_note_is_ordered_by_duration(pack):
    """The tables are not grouped straight/dotted/triplet — they ascend by note
    length, which is why the indices look shuffled."""
    from packs.timing import note_ms

    spec = pack.require("delay", "delaySyncNote")
    durations = []
    for i in range(len(spec.members)):
        name = spec.members[str(i)]
        base = name.rstrip("TD")
        suffix = name[len(base):]
        ms = note_ms(120, base)
        durations.append(ms * {"": 1.0, "T": 2 / 3, "D": 1.5}[suffix])
    assert durations == sorted(durations)


def test_pan_is_a_signed_number_not_a_selector(pack):
    for key in ("leftCabPan", "rightCabPan"):
        spec = pack.require("cabParameters", key)
        assert spec.kind == "metered"
        assert (spec.min, spec.max) == (-50, 50)
        assert pack.to_stored(spec, -25) == "-25"
        with pytest.raises(PackError, match="outside the declared range"):
            pack.to_stored(spec, 60)


def test_ac20_power_is_a_knob_not_a_selector(pack):
    spec = pack.require("ac20Amp", "ac20Power")
    assert spec.kind == "rotation"
    assert pack.to_stored(spec, 100) == "1"
    assert pack.to_stored(spec, 50) == "0.5"


def test_treble_boost_documents_the_measured_direction(pack):
    """Two names disagree about this switch and both are unreliable: the key says
    treble boost, the plugin's own control says Bass Emphasis, and rendering
    audio through it shows ON *removes* low end. The note must carry the
    measured direction, because either name alone sends the reader the wrong
    way — reading the plugin's name is exactly how this got documented
    backwards once already."""
    spec = pack.require("sw50rAmp", "sw50rTrebleBoost")
    assert "Bass emphasis" == spec.ui  # the plugin's own label for the control
    note = spec.note.lower()
    assert "bass emphasis" in note, "must say which control it moves"
    assert "brighter and tighter" in note, "must say which way the sound goes"
    assert "60 hz" in note, "must carry the measurement, not just an adjective"


def test_room_mics_do_not_share_the_close_mic_catalog(pack):
    """The room selector takes 0-2; the close-mic catalog has eleven entries.
    Pointing one at the other would let 'Ribbon 121' be written to a control
    that silently rewrites it to 0."""
    close = pack.require("cabParameters", "leftMicType")
    room = pack.require("cabParameters", "leftRoomMicType")
    assert len(close.members) == 11  # ten mics plus Custom IR
    assert room.members is None


def test_selectors_lacking_members_explain_the_alternative(pack):
    """An unknown selector is only acceptable if its note says what to do
    instead. Otherwise the agent has no path forward — and "run the discovery
    workflow" is only a path forward when the workflow can actually succeed."""
    for spec in pack.parameters.values():
        if spec.kind != "enum" or spec.members is not None:
            continue
        assert spec.note, f"{spec.path} has no members and no guidance"
        discoverable = "probe.py" in spec.note
        undiscoverable = "NO CONTROL FOR THIS EXISTS" in spec.note
        assert discoverable or undiscoverable, (
            f"{spec.path} neither points at the discovery workflow nor says why "
            f"discovery is impossible"
        )


def test_note_timed_delay_does_not_need_a_selector(pack):
    """The functional consequence of the unknown sync-note table: a musical
    delay must still be reachable through delayTime in ms."""
    from packs.timing import note_ms

    spec = pack.require("delay", "delayTime")
    assert pack.to_stored(spec, note_ms(120, "1/8 dotted")) == "375"


def test_read_only_parameter_is_refused(pack):
    with pytest.raises(PackError, match="read-only"):
        pack.to_stored(pack.require("", "version"), "2.0.0")


def test_declared_range_is_enforced(pack):
    spec = pack.require("delay", "delayTime")
    with pytest.raises(PackError, match="outside the declared range"):
        pack.to_stored(spec, 9000)


def test_out_of_range_can_be_overridden(pack):
    warnings: list[str] = []
    spec = pack.require("delay", "delayTime")
    assert pack.to_stored(spec, 9000, allow_out_of_range=True, warnings=warnings) == "9000"
    assert any("outside the declared range" in w for w in warnings)


def test_rotation_percent_is_converted(pack):
    assert pack.to_stored(pack.require("pr12Amp", "pr12Volume"), 62) == "0.62"
    with pytest.raises(PackError, match="0–100"):
        pack.to_stored(pack.require("pr12Amp", "pr12Volume"), 620)


def test_unknown_parameter_names_the_manifest(pack):
    with pytest.raises(PackError, match="manifest.json"):
        pack.require("chorus", "chorusMix")


def test_morgan_has_no_modulation_section(pack):
    """tone-references.md used to promise chorus/flanger. It does not exist."""
    modules = {spec.module for spec in pack.parameters.values()}
    assert not modules & {"chorus", "flanger", "phaser", "pitch"}


# --- the gap where declared ranges are missing ----------------------------

# Metered parameters whose real limits nobody has measured against the plugin.
# The set is empty: every metered parameter now carries a range read off the
# running plugin. It stays here as a guard rather than being deleted, because
# the failure it catches is a new parameter arriving with no range at all —
# which would be written unchecked apart from the dimensional floor in
# UNIT_FLOOR. Growing this set silently is the thing to prevent.
UNDECLARED_RANGES: set[str] = set()


def test_the_set_of_undeclared_ranges_is_exactly_what_we_think(pack):
    actual = {
        spec.path
        for spec in pack.parameters.values()
        if spec.kind == "metered" and spec.min is None and spec.max is None
    }
    assert actual == UNDECLARED_RANGES, (
        "the set of range-less parameters changed.\n"
        f"  newly missing a range: {sorted(actual - UNDECLARED_RANGES)}\n"
        f"  newly given a range:   {sorted(UNDECLARED_RANGES - actual)}\n"
        "  If a range was added, delete it from UNDECLARED_RANGES. If a new "
        "parameter arrived without one, decide whether that is acceptable."
    )


def test_every_other_metered_parameter_has_a_sourced_range(pack):
    """A declared range without a source is a guess wearing a uniform."""
    for spec in pack.parameters.values():
        if spec.kind != "metered" or spec.path in UNDECLARED_RANGES:
            continue
        assert spec.range_source, f"{spec.path} declares a range with no source"


def test_dimensional_floors_reject_impossible_values(pack):
    """Not the plugin's limits — just what cannot mean anything in the unit."""
    for path, value in [
        ("delay/delayTempo", -400),      # negative tempo
        ("delay/delayTempo", 0),         # zero tempo
        ("pr12EQ/pr12EQHpf", -20),       # negative frequency
        ("reverb/reverbPreDelay", -5),   # negative duration
    ]:
        module, _, key = path.rpartition("/")
        with pytest.raises(PackError, match="not a possible value"):
            pack.to_stored(pack.require(module, key), value, warnings=[])


def test_dimensional_floors_do_not_touch_signed_units(pack):
    """dB is signed; a negative output gain is entirely ordinary."""
    assert pack.to_stored(pack.require("parameters", "outputGain"), -6, warnings=[]) == "-6"
    assert pack.to_stored(
        pack.require("cabParameters", "leftCabMicLevel"), -12, warnings=[]
    ) == "-12"


def test_dimensional_floors_are_not_overridable(pack):
    """--allow-out-of-range covers values the plugin might accept but we have
    not declared. A negative tempo is not in that category."""
    with pytest.raises(PackError, match="not a possible value"):
        pack.to_stored(
            pack.require("delay", "delayTempo"), -120,
            allow_out_of_range=True, warnings=[],
        )
