"""Recipes are a translation, so the suite has to check the translation.

The source doc uses a 0-10 knob scale, its own parameter names, and a cab model
that doesn't match the binary. Transcribing that by hand is exactly where wrong
numbers creep in. These tests can't judge whether a recipe sounds good, but they
prove every recipe is *legal and in the right dialect*: keys that exist, values
that survive translation, ranges that hold.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from packs.loader import PackError, load_pack
from packs.timing import note_hz, note_ms

RECIPES_PATH = pathlib.Path(__file__).parent.parent / "packs" / "morgan" / "recipes.json"
AMP_PREFIXES = ("pr12", "sw50r", "ac20")
PROBE_BPM = 120  # a tempo every note-division recipe must work at


@pytest.fixture(scope="module")
def recipes():
    return json.loads(RECIPES_PATH.read_text())


@pytest.fixture(scope="module")
def pack():
    return load_pack("morgan")


def all_entries(recipes):
    """(layer, recipe_id, index, entry) for every parameter in every recipe."""
    for layer, group in recipes["layers"].items():
        for rid, recipe in group.items():
            for i, entry in enumerate(recipe["parameters"]):
                yield layer, rid, i, entry


def expand(entry, amp_prefix):
    """Resolve the {amp} template in an EQ recipe entry."""
    return (
        entry["module"].replace("{amp}", amp_prefix),
        entry["key"].replace("{amp}", amp_prefix),
    )


def resolve(value, spec):
    """Resolve a note-division value the way apply_spec does."""
    if not isinstance(value, dict):
        return value
    convert = note_ms if spec.unit == "ms" else note_hz
    return round(convert(PROBE_BPM, value["note"]), 4)


# --- structure -------------------------------------------------------------


def test_every_recipe_is_documented(recipes):
    for layer, group in recipes["layers"].items():
        for rid, recipe in group.items():
            assert recipe["title"], f"{layer}/{rid} has no title"
            assert recipe["use_when"], f"{layer}/{rid} does not say when to use it"
            assert recipe["source"].startswith("docs/"), (
                f"{layer}/{rid} does not cite where it came from"
            )
            assert recipe["parameters"], f"{layer}/{rid} sets nothing"


def test_entries_have_the_spec_shape(recipes):
    for layer, rid, i, entry in all_entries(recipes):
        assert set(entry) == {"module", "key", "value"}, (
            f"{layer}/{rid}[{i}] has unexpected fields: {sorted(entry)}"
        )


# --- the translation itself -----------------------------------------------


def test_every_key_exists_in_the_manifest(recipes, pack):
    """Catches a rename that went wrong: od1 -> drive1, hpfHz -> delayLowCut, …"""
    for layer, rid, i, entry in all_entries(recipes):
        prefixes = AMP_PREFIXES if "{amp}" in entry["module"] else ("",)
        for prefix in prefixes:
            module, key = expand(entry, prefix)
            assert pack.get(module, key) is not None, (
                f"{layer}/{rid}[{i}] targets {module}/{key}, which is not a "
                f"parameter of {pack.display_name}"
            )


def test_every_value_survives_translation(recipes, pack):
    """The load-bearing test. A knob left on the doc's 0-10 scale lands far
    outside 0-100 and fails here; so does a dB value written where Hz belongs,
    or an out-of-range time."""
    for layer, rid, i, entry in all_entries(recipes):
        prefixes = AMP_PREFIXES if "{amp}" in entry["module"] else ("",)
        for prefix in prefixes:
            module, key = expand(entry, prefix)
            spec = pack.require(module, key)
            value = resolve(entry["value"], spec)
            try:
                pack.to_stored(spec, value, warnings=[])
            except PackError as e:
                pytest.fail(f"{layer}/{rid}[{i}] {module}/{key}={value!r}: {e}")


def test_no_recipe_touches_an_unmapped_selector(recipes, pack):
    """Recipes must not set a selector whose members we don't know — the value
    would be a guess dressed up as a recipe."""
    for layer, rid, i, entry in all_entries(recipes):
        prefixes = AMP_PREFIXES if "{amp}" in entry["module"] else ("",)
        for prefix in prefixes:
            module, key = expand(entry, prefix)
            spec = pack.require(module, key)
            if spec.kind == "enum" and spec.members is None:
                pytest.fail(
                    f"{layer}/{rid}[{i}] sets {module}/{key}, a selector with no "
                    f"known members. Leave it at the template's value instead."
                )


def test_no_recipe_writes_a_read_only_parameter(recipes, pack):
    for layer, rid, i, entry in all_entries(recipes):
        prefixes = AMP_PREFIXES if "{amp}" in entry["module"] else ("",)
        for prefix in prefixes:
            module, key = expand(entry, prefix)
            assert pack.require(module, key).writable, (
                f"{layer}/{rid}[{i}] writes read-only {module}/{key}"
            )


# --- knob-scale specifics -------------------------------------------------


def test_knob_values_look_like_percent_not_doc_scale(recipes, pack):
    """A value the translator forgot to multiply by 10 is legal (0-100 admits
    3.6) but wrong. Every rotation value in the source doc is a one-decimal
    number on a 0-10 scale, so a correctly converted value is a multiple of 5
    at minimum and never below 10 unless it is deliberately zero."""
    suspicious = []
    for layer, rid, i, entry in all_entries(recipes):
        prefixes = AMP_PREFIXES if "{amp}" in entry["module"] else ("",)
        for prefix in prefixes:
            module, key = expand(entry, prefix)
            spec = pack.require(module, key)
            value = entry["value"]
            if spec.kind != "rotation" or isinstance(value, (dict, bool)):
                continue
            if 0 < value < 10:
                suspicious.append(f"{layer}/{rid} {module}/{key}={value}")
    assert not suspicious, (
        "rotation values below 10% are suspicious — they look like a doc 0-10 "
        f"knob value that was never scaled: {suspicious}"
    )


def test_eq_recipes_are_amp_templated(recipes):
    """The graphic EQ is per-amp, so an EQ recipe that hard-codes one amp would
    silently do nothing when a different amp is live."""
    for rid, recipe in recipes["layers"]["eq"].items():
        for entry in recipe["parameters"]:
            assert "{amp}" in entry["module"] and "{amp}" in entry["key"], (
                f"eq/{rid} hard-codes an amp: {entry['module']}/{entry['key']}"
            )
        assert "{amp}" in recipe["note"], f"eq/{rid} does not explain substitution"


def test_eq_band_order_matches_manifest_centres(pack):
    """Band1..Band9 must ascend in frequency, or 'push 2 kHz' lands on the
    wrong band."""
    for amp in AMP_PREFIXES:
        centres = [
            pack.require(f"{amp}EQ", f"{amp}EQBand{i}").__dict__.get("kind")
            for i in range(1, 10)
        ]
        assert all(c == "metered" for c in centres)
    manifest = json.loads(
        (RECIPES_PATH.parent / "manifest.json").read_text()
    )["parameters"]
    for amp in AMP_PREFIXES:
        got = [manifest[f"{amp}EQ/{amp}EQBand{i}"]["centre_hz"] for i in range(1, 10)]
        assert got == sorted(got), f"{amp} EQ band centres are not ascending: {got}"
        assert got == [65, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]


# --- note divisions -------------------------------------------------------


def test_note_division_recipes_resolve_at_ordinary_tempos(recipes, pack):
    """A recipe carrying a note division must be usable across the tempo range
    people actually play at."""
    for layer, rid, i, entry in all_entries(recipes):
        if not isinstance(entry["value"], dict):
            continue
        spec = pack.require(entry["module"], entry["key"])
        for bpm in (70, 90, 110, 130, 150):
            value = round(
                (note_ms if spec.unit == "ms" else note_hz)(bpm, entry["value"]["note"]),
                4,
            )
            try:
                pack.to_stored(spec, value, warnings=[])
            except PackError as e:
                pytest.fail(
                    f"{layer}/{rid} {entry['key']} at {bpm} BPM: {e}\n"
                    f"  The recipe's note should say which tempos it fits."
                )


def test_recipes_declaring_tempo_limits_say_so(recipes):
    """Where a division can't span all tempos, the recipe has to warn."""
    for layer, group in recipes["layers"].items():
        for rid, recipe in group.items():
            has_note = any(
                isinstance(e["value"], dict) for e in recipe["parameters"]
            )
            if has_note:
                assert recipe.get("note"), (
                    f"{layer}/{rid} uses a note division but has no note "
                    f"explaining that bpm must be supplied"
                )


# --- integrity of the record ---------------------------------------------


def test_untranslated_fields_are_recorded(recipes):
    """Anything dropped in translation must be written down, or the next reader
    will assume the doc was fully absorbed."""
    dropped = recipes["not_translated"]
    assert len(dropped) >= 8
    for reason in dropped.values():
        assert len(reason) > 20, "a dropped field needs a real reason"


def test_conversion_rules_are_stated(recipes):
    conversion = recipes["conversion"]
    for field in ("knob_scale", "renames", "metered", "verification"):
        assert field in conversion, f"conversion is missing {field}"


def test_tone_md_only_cites_recipes_that_exist(recipes):
    """tone.md's intent table names recipe ids. A typo there sends the agent
    looking for a recipe that isn't in the file."""
    import re

    tone = (RECIPES_PATH.parent / "tone.md").read_text()
    known = {rid for group in recipes["layers"].values() for rid in group}
    known_qualified = {
        f"{layer}/{rid}"
        for layer, group in recipes["layers"].items()
        for rid in group
    }

    cited = set(re.findall(r"`([a-z0-9]+(?:/[a-z0-9-]+)?[a-z0-9-]*)`", tone))
    # Only judge things that look like recipe ids: hyphenated, or layer//id.
    candidates = {c for c in cited if "-" in c or "/" in c}
    unknown = {
        c
        for c in candidates
        if c not in known and c not in known_qualified and not c.startswith("docs/")
    }
    # Filenames and paths cited in prose are not recipe ids.
    unknown = {c for c in unknown if not c.endswith((".md", ".json", ".py"))}
    assert not unknown, (
        f"tone.md cites recipe ids that do not exist in recipes.json: "
        f"{sorted(unknown)}"
    )


def test_every_intent_row_is_reachable(recipes):
    """Each layer that the intent table draws on must actually have recipes."""
    tone = (RECIPES_PATH.parent / "tone.md").read_text()
    assert "Intent → which recipes to stack" in tone
    for layer in ("amp", "compressor", "eq", "delay", "reverb", "output", "cab"):
        assert recipes["layers"].get(layer), f"no recipes for layer {layer}"
