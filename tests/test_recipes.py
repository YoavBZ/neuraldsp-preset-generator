"""Recipe structure and compatibility with the current pack contract.

These tests cannot judge whether a recipe sounds good. They prove every recipe
uses existing keys, writable kinds, valid selectors, and values that survive
translation within the declared ranges.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from packs.loader import PackError, load_pack
from packs.recipes import (
    amp_prefix_for,
    expand_amp,
    get_recipe,
    load_recipes,
    resolve_value,
    stack,
)
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


def all_expanded(recipes, pack):
    """Every entry, with {amp} resolved — once for each amp when templated.

    Yields (layer, rid, index, entry, module, key) so a test never has to
    remember the expansion step itself.
    """
    for layer, rid, i, entry in all_entries(recipes):
        prefixes = AMP_PREFIXES if "{amp}" in entry["module"] else (None,)
        for prefix in prefixes:
            expanded = expand_amp(entry, prefix)
            yield layer, rid, i, expanded, expanded["module"], expanded["key"]


# --- structure -------------------------------------------------------------


def test_every_recipe_has_current_metadata(recipes):
    for layer, group in recipes["layers"].items():
        for rid, recipe in group.items():
            assert recipe["title"], f"{layer}/{rid} has no title"
            assert recipe["use_when"], f"{layer}/{rid} does not say when to use it"
            assert recipe["parameters"], f"{layer}/{rid} sets nothing"


def test_entries_have_the_spec_shape(recipes):
    for layer, rid, i, entry in all_entries(recipes):
        assert set(entry) == {"module", "key", "value"}, (
            f"{layer}/{rid}[{i}] has unexpected fields: {sorted(entry)}"
        )


# --- the translation itself -----------------------------------------------


def test_every_key_exists_in_the_manifest(recipes, pack):
    """Catches a rename that went wrong: od1 -> drive1, hpfHz -> delayLowCut, …"""
    for layer, rid, i, entry, module, key in all_expanded(recipes, pack):
        assert pack.get(module, key) is not None, (
            f"{layer}/{rid}[{i}] targets {module}/{key}, which is not a "
            f"parameter of {pack.display_name}"
        )


def test_every_value_survives_translation(recipes, pack):
    """Reject values expressed on the wrong scale or in the wrong unit."""
    for layer, rid, i, entry, module, key in all_expanded(recipes, pack):
        spec = pack.require(module, key)
        value = resolve_value(entry["value"], spec, PROBE_BPM)
        try:
            pack.to_stored(spec, value, warnings=[])
        except PackError as e:
            pytest.fail(f"{layer}/{rid}[{i}] {module}/{key}={value!r}: {e}")


def test_no_recipe_touches_an_unmapped_selector(recipes, pack):
    """Recipes must not set a selector whose members we don't know — the value
    would be a guess dressed up as a recipe."""
    for layer, rid, i, entry, module, key in all_expanded(recipes, pack):
        spec = pack.require(module, key)
        if spec.kind == "enum" and spec.members is None:
            pytest.fail(
                f"{layer}/{rid}[{i}] sets {module}/{key}, a selector with no "
                f"known members. Leave it at the template's value instead."
            )


def test_no_recipe_writes_a_read_only_parameter(recipes, pack):
    for layer, rid, i, entry, module, key in all_expanded(recipes, pack):
        assert pack.require(module, key).writable, (
            f"{layer}/{rid}[{i}] writes read-only {module}/{key}"
        )


# --- knob-scale specifics -------------------------------------------------


def test_knob_values_use_percent_scale(recipes, pack):
    """Rotation recipes use the pack's 0-100 percent convention.

    Small nonzero values are legal but suspicious here because the curated
    recipes use coarse musical starting points rather than near-zero trims.
    """
    suspicious = []
    for layer, rid, i, entry, module, key in all_expanded(recipes, pack):
        spec = pack.require(module, key)
        value = entry["value"]
        if spec.kind != "rotation" or isinstance(value, (dict, bool)):
            continue
        if 0 < value < 10:
            suspicious.append(f"{layer}/{rid} {module}/{key}={value}")
    assert not suspicious, (
        "rotation values below 10% are suspicious for curated recipe starting "
        f"points: {suspicious}"
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


# --- the recipe machinery -------------------------------------------------


def test_recipes_load_as_objects(pack):
    loaded = load_recipes("morgan")
    assert set(loaded) >= {"amp", "eq", "delay", "reverb", "cab", "output"}
    recipe = get_recipe("amp/sw50r-singing-lead")
    assert recipe.ref == "amp/sw50r-singing-lead"
    assert recipe.title and recipe.use_when and recipe.parameters


def test_bad_recipe_reference_lists_the_alternatives():
    with pytest.raises(PackError, match="natural-flat"):
        get_recipe("eq/does-not-exist")
    with pytest.raises(PackError, match="Layers:"):
        get_recipe("nosuchlayer/x")
    with pytest.raises(PackError, match="layer/id"):
        get_recipe("missing-slash")


def test_amp_prefix_resolves_by_name_and_by_index(pack):
    assert amp_prefix_for(pack, "SW50R") == "sw50r"
    assert amp_prefix_for(pack, "sw50r") == "sw50r"
    assert amp_prefix_for(pack, "2") == "sw50r"
    assert amp_prefix_for(pack, 1) == "pr12"
    assert amp_prefix_for(pack, "Marshall") is None


def test_expand_amp_is_a_no_op_for_untemplated_entries():
    entry = {"module": "delay", "key": "delayMix", "value": 30}
    assert expand_amp(entry, "sw50r") == entry


def test_expand_amp_without_an_amp_is_an_error_not_a_silent_pass():
    """Leaving '{amp}EQ' in place would target a module that does not exist,
    and the write would fail far from the cause."""
    entry = {"module": "{amp}EQ", "key": "{amp}EQBand5", "value": 1.5}
    with pytest.raises(PackError, match="templated on the live amp"):
        expand_amp(entry, None)


def test_stack_resolves_the_amp_it_selects(pack):
    """An eq/… recipe stacked after an amp/… recipe must land on that amp."""
    entries = stack(["amp/sw50r-singing-lead", "eq/lead-focus"], pack)
    eq_modules = {e["module"] for e in entries if e["module"].endswith("EQ")}
    assert eq_modules == {"sw50rEQ"}

    entries = stack(["amp/pr12-clean", "eq/warm-clean-rhythm"], pack)
    assert {e["module"] for e in entries if e["module"].endswith("EQ")} == {"pr12EQ"}


def test_stack_order_is_preserved(pack):
    entries = stack(["compressor/off", "compressor/lead-smoothing"], pack)
    actives = [e["value"] for e in entries if e["key"] == "compressorActive"]
    assert actives == [False, True], "later recipes must win, so order must survive"


def test_resolve_value_needs_a_tempo_and_says_so(pack):
    spec = pack.require("delay", "delayTime")
    assert resolve_value({"note": "1/4"}, spec, 96) == 625.0
    assert resolve_value({"note": "1/4", "bpm": 120}, spec, 96) == 500.0, (
        "a bpm on the value itself must beat the fallback"
    )
    with pytest.raises(PackError, match="needs a tempo"):
        resolve_value({"note": "1/4"}, spec, None)
    with pytest.raises(PackError, match="unexpected field"):
        resolve_value({"note": "1/4", "bpm": 96, "typo": 1}, spec, None)
    with pytest.raises(PackError, match="only makes sense"):
        resolve_value({"note": "1/4"}, pack.require("delay", "delayMix"), 96)
