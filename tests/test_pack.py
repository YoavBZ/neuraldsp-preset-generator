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
    manifest, not in the preset."""
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


# --- Tone King verified and internal state --------------------------------


@pytest.fixture(scope="module")
def toneking():
    return load_pack("toneking")


def test_tone_king_has_no_guessed_writable_kinds(toneking):
    guessed = [s.path for s in toneking.parameters.values() if s.needs_review]
    assert not guessed


def test_tone_king_internal_state_is_read_only(toneking):
    internal = [s for s in toneking.parameters.values() if s.kind == "internal"]
    assert len(internal) == 159
    assert all(not spec.writable for spec in internal)
    with pytest.raises(PackError, match="lossless state round-trip"):
        toneking.to_stored(toneking.require("", "ampOutput"), 0.5, warnings=[])


def test_tone_king_published_control_surface_is_verified(toneking):
    published = [s for s in toneking.parameters.values() if s.ui]
    assert len(published) == 94
    assert all(spec.kind != "internal" and spec.writable for spec in published)


def test_tone_king_verified_switches_use_the_record_encoding(toneking):
    spec = toneking.require("", "ampsActive")
    assert spec.kind == "switch"
    assert spec.switch_encoding == "numeric"
    assert toneking.to_stored(spec, True, warnings=[]) == "1"
    assert toneking.to_stored(spec, False, warnings=[]) == "0"


def test_tone_king_switches_carry_the_plugin_s_own_two_labels(toneking):
    """All 21 switches used to declare nothing, so `audit_manifest.py` tested
    nothing about them — 21 of the 53 parameters it reported as untested. The
    plugin publishes both labels for every one of them; declaring them is what
    gives the audit something to re-derive."""
    switches = [s for s in toneking.parameters.values() if s.kind == "switch"]
    assert len(switches) == 21
    for spec in switches:
        assert list(spec.members.values()) in (["Inactive", "Active"], ["Off", "On"]), (
            f"{spec.path} must carry the labels the plugin publishes, not a "
            f"paraphrase — the audit compares them literally"
        )
    assert toneking.require("", "ampsActive").members == {"0": "Inactive", "1": "Active"}
    assert toneking.require("", "cab1Phase").members == {"0": "Off", "1": "On"}


def test_a_tone_king_switch_accepts_the_label_it_displays(toneking):
    """Declaring members makes `member_name` fire, and that is what show.py and
    apply_spec.py print — so "Active" is what a reader hands back. It has to be
    writable, or the display and the write path disagree."""
    spec = toneking.require("", "ampsActive")
    assert spec.member_name("1") == "Active"
    assert toneking.to_stored(spec, "Active", warnings=[]) == "1"
    assert toneking.to_stored(spec, "Inactive", warnings=[]) == "0"
    assert toneking.to_stored(spec, True, warnings=[]) == "1"    # still a switch
    with pytest.raises(PackError):
        toneking.to_stored(spec, "Enabled", warnings=[])


def test_tone_king_fractions_declare_the_range_the_plugin_publishes(toneking):
    """31 of the 32 fractions now carry the 0..1 the mapped control publishes,
    with a source saying which evidence it came from."""
    fractions = [s for s in toneking.parameters.values() if s.kind == "fraction"]
    assert len(fractions) == 32
    undeclared = sorted(s.path for s in fractions if s.min is None and s.max is None)
    # `reverbPreDelay` is the one the plugin will not answer for: it already
    # sits at its own minimum, so writing below that moves nothing and the state
    # keeps the out-of-range number verbatim. Half a range is not a range, and
    # the missing half is precisely the blind spot that hid three wrong ranges.
    assert undeclared == ["reverbPreDelay"]
    for spec in fractions:
        if spec.path in undeclared:
            assert "undeclared" in (spec.note or "").lower(), (
                f"{spec.path} declares nothing and must say why"
            )
            continue
        assert (spec.min, spec.max) == (0.0, 1.0), spec.path
        assert spec.range_source, f"{spec.path} declares a range with no source"


def test_tone_king_unlabelled_continuous_controls_are_not_enums(toneking):
    for key in ("delayHPF", "delayLPF", "reverbPreDelay"):
        spec = toneking.require("", key)
        assert spec.kind == "fraction"
        assert spec.members is None
        assert not spec.needs_confirmation


def test_tone_king_mapped_selector_tables_are_confirmed(toneking):
    assert toneking.require("", "ampAttenuation").members["5"] == "0 dB"
    assert toneking.require("", "cab1MicIR").members["16"] == "Custom IR"
    assert toneking.require("", "delaySyncNoteL").members["13"] == "1/4"
    assert toneking.require("", "wahMode").members == {
        "0": "Auto-Wah OFF", "1": "Auto-Wah ON"
    }
    still_unknown = {
        spec.path for spec in toneking.parameters.values() if spec.needs_confirmation
    }
    assert not still_unknown


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


def test_pan_scales_differ_between_packs(pack):
    """The two plugins display a pan identically and store it differently.

    Morgan stores -50..50; Tone King stores -1..1. Both show `50 L` / `L 50` at
    the same end, so the display establishes nothing — reading the range off it
    gave Tone King a range 50x too large, and the cab recipes built on that
    hard-panned both cabs while asking for a gentle spread.

    Pinned because the mistake is invisible: every value still writes, still
    round-trips, and still looks reasonable in the file.
    """
    toneking = load_pack("toneking")
    assert (pack.require("cabParameters", "leftCabPan").min,
            pack.require("cabParameters", "leftCabPan").max) == (-50, 50)
    assert (toneking.require("", "cab1Pan").min,
            toneking.require("", "cab1Pan").max) == (-1.0, 1.0)

    # A value that is legal on one is far out of range on the other.
    assert pack.to_stored(pack.require("cabParameters", "leftCabPan"), -25) == "-25"
    with pytest.raises(PackError, match="outside the declared range"):
        toneking.to_stored(toneking.require("", "cab1Pan"), -25)


def test_toneking_recipes_pan_within_the_real_scale():
    """The recipes were written against the wrong scale once already."""
    import json as _json
    from packs.paths import PLUGIN_ROOT

    toneking = load_pack("toneking")
    recipes = _json.loads((PLUGIN_ROOT / "packs" / "toneking" / "recipes.json").read_text())
    for layer, group in recipes["layers"].items():
        for name, recipe in group.items():
            for entry in recipe["parameters"]:
                if not entry["key"].endswith("Pan"):
                    continue
                spec = toneking.require(entry["module"], entry["key"])
                # Must survive the manifest's own validation, not just look small.
                toneking.to_stored(spec, entry["value"], warnings=[])


def test_a_bad_switch_value_names_the_labels_it_would_accept():
    """Declaring `members` on a switch means show.py displays "Active" — so a
    reader hands "Active" back, and the error for a wrong guess has to name what
    is actually accepted rather than only true/false."""
    toneking = load_pack("toneking")
    spec = toneking.require("", "ampsActive")
    with pytest.raises(PackError) as exc:
        toneking.to_stored(spec, "Enabled", warnings=[])
    message = str(exc.value)
    assert "Inactive" in message and "Active" in message, message

    # Morgan's switches declare no labels, so its message must stay unchanged.
    morgan = load_pack("morgan")
    with pytest.raises(PackError) as plain:
        morgan.to_stored(morgan.require("parameters", "gateActive"), "Enabled", warnings=[])
    assert "accepts its displayed labels" not in str(plain.value)
