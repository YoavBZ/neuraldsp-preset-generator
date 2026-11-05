"""Tone King Imperial MKII X's own pack: its layout, conversions and recipes."""

from __future__ import annotations

import pathlib

import pytest

from format.parser import parse
from format.structured import build, set_parameter
from format.writer import write
from packs.loader import PackError, detect_pack, load_pack
from packs.recipes import load_recipes
from scripts.apply_spec import strip_custom_irs
from tests.test_valuetree import _write

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _text(value: str) -> bytes:
    raw = value.encode() + b"\x00"
    return bytes([1, len(raw) + 1, 5]) + raw


def _preset() -> bytes:
    """A small file in X's layout, built here: no factory preset ships with the repo."""
    def section(name, *props, children=()):
        return name, [(k, _text(v)) for k, v in props], list(children)

    def nested(*children):
        return "subModels", [], list(children)

    amp = section("ampParameters", ("ampChannel", "false"), ("rhythmVolume", "0.38"))
    cab = section(
        "cabParameters", ("leftChosenIRFilePath", "/x/l.wav"), ("leftMicType", "16"),
        ("leftIsCustomIR", "true"), ("rightChosenIRFilePath", ""), ("rightMicType", "6"),
        ("rightIsCustomIR", "false"), ("leftCabPan", "0"))
    delay = section("delay", ("delaySync", "2"), ("delayFeedback", "0.28"))
    app = section("appModel", children=[nested(
        section("parameters", ("outputGain", "6")), amp, cab, delay)])
    return b"toneking" + _write(("", [("version", _text("0.3.2")), ("name", _text("Test"))],
                                 [app]))


def test_the_header_picks_the_pack_and_sections_read_from_the_tree():
    preset = build(parse(_preset()))
    assert detect_pack(preset.file_header).pack_id == "toneking_x"
    assert preset.by_path[("ampParameters", "rhythmVolume")].value == "0.38"
    assert preset.by_path[("delay", "delayFeedback")].value == "0.28"
    assert ("cabParameters", "leftCabPan") in preset.by_path


def test_every_declared_control_is_in_the_shape_the_writer_expects():
    pack = load_pack("toneking_x")
    assert pack.audio_unit["subtype"] == "NTKX"
    assert sum(1 for spec in pack.parameters.values() if spec.ui and spec.kind != "path") == 97
    for spec in pack.parameters.values():
        if spec.kind == "metered":
            assert spec.min is not None and spec.max is not None, spec.path


@pytest.mark.parametrize("path, human, stored", [
    ("ampParameters/ampChannel", "Lead", "true"),
    ("ampParameters/ampChannel", "Rhythm", "false"),
    ("compressor/compressorSpeed", "Slow", "false"),
    ("delay/delaySync", "DAW", "1"),
    ("ampParameters/ampAttenuation", "-15 dB", "2"),
    ("cabParameters/rightMicType", "Ribbon 121 E33", "6"),
    ("ampParameters/rhythmVolume", 57, "0.57"),
    ("delay/delayFeedback", 32, "0.32"),
    ("cabParameters/leftCabPan", -10, "-10"),
])
def test_values_translate_to_what_the_plugin_stores(path, human, stored):
    pack = load_pack("toneking_x")
    written = pack.to_stored(pack.parameters[path], human, warnings=[])
    assert float(written) == float(stored) if written[0] in "-0123456789" else written == stored


def test_a_two_state_selector_shows_its_label():
    spec = load_pack("toneking_x").parameters["ampParameters/ampChannel"]
    assert spec.member_name("true") == "Lead"
    assert spec.member_name("false") == "Rhythm"


def test_every_recipe_translates_in_range_and_matches_the_original_ids():
    pack = load_pack("toneking_x")
    ours, theirs = load_recipes("toneking_x"), load_recipes("toneking")
    assert {k: set(v) for k, v in ours.items()} == {k: set(v) for k, v in theirs.items()}
    for group in ours.values():
        for recipe in group.values():
            for entry in recipe.parameters:
                spec = pack.require(entry["module"], entry["key"])
                notes = []
                pack.to_stored(spec, entry["value"], warnings=notes)
                assert not notes, (recipe.id, spec.path, notes)


def test_recipe_conversions():
    def values(ref):
        layer, rid = ref.split("/")
        return {e["key"]: e["value"] for e in load_recipes("toneking_x")[layer][rid].parameters}

    slap = values("delay/short-slap")
    assert slap["delaySync"] == "Free" and slap["delayFeedback"] == 10.0   # 0.05 stored there
    assert values("delay/mono-quarter")["delaySync"] == "DAW"
    assert values("reverb/compact-room")["reverbDecay"] == 12.0            # 1.4 s there
    cab = values("cab/balanced-57-ribbon")
    assert cab["leftCabPan"] == -10.0 and cab["leftCabMicLevel"] == 0.0    # −0.2 and −12 there
    assert values("dry/toneking")["gateThreshold"] == -96


def test_chorus_recipes_follow_the_plugin_s_labels():
    """Factory presets hold depth and rate crossed between editions, but each key moves
    its own named control in both, so the recipes keep the original's values by label."""
    def values(rid):
        return {e["key"]: e["value"] for e in load_recipes("toneking_x")["chorus"][rid].parameters}

    assert values("subtle-width")["chorusDepth"] == 20.0 and values("subtle-width")["chorusRate"] == 50.0
    assert values("deep-vintage")["chorusDepth"] == 70.0 and values("deep-vintage")["chorusRate"] == 42.0


def test_a_wrong_label_lists_the_right_ones():
    pack = load_pack("toneking_x")
    spec = pack.parameters["ampParameters/ampChannel"]
    with pytest.raises(PackError, match="Rhythm"):
        pack.to_stored(spec, "Clean", warnings=[])
    delay = pack.parameters["delay/delaySync"]
    with pytest.raises(PackError, match="Tap"):
        pack.to_stored(delay, "Sometimes", warnings=[])


def test_the_fall_back_mics_are_what_a_fresh_plugin_holds():
    slots = load_pack("toneking_x").custom_ir
    assert [(s["custom"], s["default"]) for s in slots] == [("16", "0"), ("16", "6")]


def test_match_refuses_a_pack_it_cannot_render(tmp_path):
    import subprocess
    import sys

    pytest.importorskip("numpy")                  # without the analysis extra, match
    pytest.importorskip("pyloudnorm")             # stops before it reaches the pack
    template = tmp_path / "x.xml"
    template.write_bytes(_preset())
    riff = ROOT / "samples" / "riffs" / "line.flac"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "match_preset.py"), "--template", str(template),
         "--reference", str(riff), "--reference-mode", "paired_di", "--probe-di", str(riff),
         "--renderer", "synthetic", "--out-dir", str(tmp_path / "out")],
        capture_output=True, text=True)
    assert result.returncode != 0
    assert "original plugin" in result.stderr and "Traceback" not in result.stderr


def test_strip_irs_clears_all_three_fields_and_only_the_side_that_used_a_file():
    preset = build(parse(_preset()))
    changed = {key: (before, after) for _, key, before, after in strip_custom_irs(preset)}
    assert changed == {
        "leftChosenIRFilePath": ("/x/l.wav", ""),
        "leftMicType": ("16", "0"),
        "leftIsCustomIR": ("true", "false"),
    }
    after = build(parse(write(preset.tokens)))
    assert after.by_path[("cabParameters", "rightMicType")].value == "6"


def test_an_edit_survives_a_round_trip_and_keeps_the_layout():
    buf = _preset()
    tokens = parse(buf)
    assert write(tokens) == buf
    preset = build(tokens)
    set_parameter(preset, "delay", "delayFeedback", "0.5")
    after = write(preset.tokens)
    assert after.startswith(b"toneking\x00")
    assert build(parse(after)).by_path[("delay", "delayFeedback")].value == "0.5"


ORIGINAL = pathlib.Path("/Library/Audio/Presets/Neural DSP/Tone King Imperial MKII")
X_EDITION = pathlib.Path("/Library/Audio/Presets/Neural DSP/Tone King Imperial MKII X")
SAME = {
    ("ampParameters", "rhythmVolume"): "rhythmAmpVolume",
    ("ampParameters", "leadVolume"): "leadAmpVolume",
    ("parameters", "inputGain"): "inputGain",
    ("drive1", "drive1Drive"): "drive1Overdrive",
    ("toneKingEQ", "toneKingEQBand5"): "eqBand5",
    ("cabParameters", "rightMicType"): "cab2MicIR",
    ("chorus", "chorusRate"): "chorusDepth",       # crossed: see the pack's tone notes
    ("chorus", "chorusDepth"): "chorusRate",
}


@pytest.mark.skipif(not (ORIGINAL.is_dir() and X_EDITION.is_dir()),
                    reason="needs both Tone King Imperial MKII and its X edition installed")
def test_installed_x_presets_hold_the_originals_values():
    pairs = [(f, ORIGINAL / f.relative_to(X_EDITION)) for f in sorted(X_EDITION.rglob("*.xml"))
             if f.read_bytes().startswith(b"toneking\x00")]
    pairs = [(x, o) for x, o in pairs if o.exists()]
    assert pairs
    for x, o in pairs:
        ours, theirs = build(parse(x.read_bytes())).by_path, build(parse(o.read_bytes())).by_path
        for key, old in SAME.items():
            assert float(ours[key].value) == pytest.approx(float(theirs[("", old)].value), abs=1e-3), \
                (x.name, key)
