"""The crunch starting presets set to the labels' centre (`start/crunch-<amp>`, learn/cen_crunch_start.py)."""

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECIPES = ROOT / "packs/morgan/recipes.json"
AMPS = {"pr12": "PR12", "sw50r": "SW50R", "ac20": "AC20"}
EFFECT_MODULES = {"delay", "reverb", "tremolo", "fxParameters"}
EFFECT_KEYS = {"doublerActive", "doublerSpread", "transpose", "pr12Reverb", "pr12Dwell", "sw50rReverb", "selectedAmp"}


def start_layer():
    return json.loads(RECIPES.read_text())["layers"]["start"]


def test_one_crunch_start_per_amp_tagged_with_its_amp():
    layer = start_layer()
    assert set(layer) == {f"crunch-{a}" for a in AMPS}
    for a, name in AMPS.items():
        assert layer[f"crunch-{a}"]["for_amp"] == name


@pytest.mark.parametrize("amp", sorted(AMPS))
def test_a_crunch_start_leaves_the_effects_and_the_amp_alone(amp):
    for p in start_layer()[f"crunch-{amp}"]["parameters"]:
        assert p["module"] not in EFFECT_MODULES, p
        assert p["key"] not in EFFECT_KEYS, p


@pytest.mark.parametrize("amp", sorted(AMPS))
def test_a_crunch_start_sets_the_output_once_within_range(amp):
    out = [p for p in start_layer()[f"crunch-{amp}"]["parameters"] if p["key"] == "outputGain"]
    assert len(out) == 1 and -24.0 <= out[0]["value"] <= 24.0


@pytest.mark.parametrize("amp", sorted(AMPS))
def test_a_crunch_start_touches_only_its_own_amp(amp):
    others = {f"{a}Amp" for a in AMPS if a != amp} | {f"{a}EQ" for a in AMPS if a != amp}
    for p in start_layer()[f"crunch-{amp}"]["parameters"]:
        assert p["module"] not in others, p


def test_a_crunch_start_is_refused_on_another_amp(tmp_path):
    template = ROOT / "samples/Example_Clean_PR12.xml"
    r = subprocess.run([sys.executable, str(ROOT / "scripts/apply_spec.py"), "--template", str(template),
                        "--recipe", "start/crunch-sw50r", "--out", str(tmp_path / "x.xml"), "--dry-run"],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "SW50R" in (r.stdout + r.stderr)


def test_the_factory_baselines_made_dry_and_centred_equal_the_centre():
    """On the dev machine: factory baseline + dry/<amp> + start/crunch-<amp> equals the ladder's Cen cell on every
    setting but the output gain."""
    from learn import cen_crunch_start as C

    if not C.CENTRES.exists():
        pytest.skip("the ladder's centres.json is not on this machine")
    if not all((C.FACTORY / rel).exists() for rel in C.BASELINE.values()):
        pytest.skip("the Morgan factory presets are not installed")
    C.cmd_check(None)
