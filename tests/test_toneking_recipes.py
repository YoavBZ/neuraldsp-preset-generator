"""Tone King recipe structure and compatibility with its production manifest."""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from packs.loader import PackError, load_pack
from packs.recipes import get_recipe, load_recipes, stack


PACK_DIR = pathlib.Path(__file__).parent.parent / "packs" / "toneking"
RECIPES_PATH = PACK_DIR / "recipes.json"


@pytest.fixture(scope="module")
def recipes():
    return json.loads(RECIPES_PATH.read_text())


@pytest.fixture(scope="module")
def pack():
    return load_pack("toneking")


def entries(recipes):
    for layer, group in recipes["layers"].items():
        for recipe_id, recipe in group.items():
            for index, entry in enumerate(recipe["parameters"]):
                yield layer, recipe_id, index, entry


def test_recipe_file_identifies_the_pack_and_has_all_core_layers(recipes):
    assert recipes["pack_id"] == "toneking"
    assert set(recipes["layers"]) >= {
        "amp", "compressor", "eq", "cab", "delay", "reverb", "output"
    }


def test_every_recipe_has_current_metadata_and_parameters(recipes):
    for layer, group in recipes["layers"].items():
        for recipe_id, recipe in group.items():
            assert recipe["title"], f"{layer}/{recipe_id} has no title"
            assert recipe["use_when"], f"{layer}/{recipe_id} has no use_when"
            assert recipe["parameters"], f"{layer}/{recipe_id} sets nothing"


def test_every_entry_targets_a_writable_parameter_with_a_legal_value(recipes, pack):
    for layer, recipe_id, index, entry in entries(recipes):
        assert set(entry) == {"module", "key", "value"}
        spec = pack.require(entry["module"], entry["key"])
        assert spec.writable, f"{layer}/{recipe_id}[{index}] writes {spec.path}"
        try:
            pack.to_stored(spec, entry["value"], warnings=[])
        except PackError as error:
            pytest.fail(
                f"{layer}/{recipe_id}[{index}] {spec.path}="
                f"{entry['value']!r}: {error}"
            )


def test_every_selector_used_by_a_recipe_has_verified_members(recipes, pack):
    for layer, recipe_id, index, entry in entries(recipes):
        spec = pack.require(entry["module"], entry["key"])
        if spec.kind == "enum":
            assert spec.members, (
                f"{layer}/{recipe_id}[{index}] uses selector {spec.path} "
                "without a verified member table"
            )


def test_recipe_loader_and_stack_support_toneking(pack):
    loaded = load_recipes("toneking")
    assert loaded["amp"]["rhythm-clean"].ref == "amp/rhythm-clean"
    assert get_recipe("delay/short-slap", "toneking").title
    result = stack(
        ["amp/rhythm-clean", "cab/balanced-57-ribbon", "output/unity"],
        pack,
        pack_id="toneking",
    )
    assert any(entry["key"] == "ampType" for entry in result)
    assert any(entry["key"] == "cab1MicIR" for entry in result)
    assert any(entry["key"] == "outputGain" for entry in result)


def test_tone_guide_only_cites_existing_recipe_references(recipes):
    known = {
        f"{layer}/{recipe_id}"
        for layer, group in recipes["layers"].items()
        for recipe_id in group
    }
    tone = (PACK_DIR / "tone.md").read_text()
    cited = set(re.findall(r"`([a-z0-9]+/[a-z0-9-]+)`", tone))
    assert cited <= known, f"unknown Tone King recipes: {sorted(cited - known)}"
