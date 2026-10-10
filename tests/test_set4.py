"""Set 4's committed declaration and its leakage guards (learn/set4.py, learn/set3.py)."""

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import set3, set4  # noqa: E402

spec = importlib.util.spec_from_file_location("validation_set4", ROOT / "research" / "validation_set4.py")
vs4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs4)

CATALOG = pathlib.Path("~/ndsp-presets/references/datasets-set4/catalog.json").expanduser()
CROPS = pathlib.Path("~/ndsp-presets/references/validation-crops-set4").expanduser()


def _a_di():
    s = set4.load()["sessions"][0]
    return set4.SET4_ROOT / s["dis"][0]["di"]


# --- the declaration ----------------------------------------------------------------

def test_every_band_is_held_out_and_used_once():
    d = set4.load()
    # Spent by the one declared confirmation (docs/set4-confirmation-plan.md); no other use.
    assert [u["test_id"] for u in d["held_out_uses"]] == ["confirm-rebuilt-di-chooser-2026-10-10"]
    assert d["held_out_uses"][0]["spent"] is True
    assert d["held_out_bands"] == set4.bands()
    assert all(s["split"] == "held_out" and s["fold"] is None for s in d["sessions"])
    assert all(p["split"] == "held_out" and p["fold"] is None for p in d["parts"])
    assert d["counts"]["kept"] == len(d["parts"])
    assert d["counts"]["excluded"] == len(d["excluded"])
    assert d["counts"]["declared_parts"] == 52               # 21 + amendment 1's 31


AMENDMENT_1 = {"Umbriferous", "The Bright Star Alliance", "Sonnet & Alcohol", "The Laminar Flow"}


def test_the_guard_knows_every_declared_session():
    d = set4.load()
    assert {s["key"]: (s["band"], s["path"]) for s in d["sessions"]} == set4.SESSIONS
    assert len(set4.SESSIONS) == 9 and AMENDMENT_1 <= set(set4.bands())
    assert [a["id"] for a in d["amendments"]] == [1]


def test_amendment_1_sessions_come_from_the_wayback_machine():
    for s in set4.load()["sessions"]:
        if s["band"] in AMENDMENT_1:
            assert s["route"] == "wayback" and s["wayback_capture"]
            assert s["url"].startswith("https://web.archive.org/web/") and "id_/https://multitracks.cambridge-mt.com/" in s["url"]
        else:
            assert s["route"] == "direct" and s["url"].startswith("https://mtkdata.cambridgemusictechnology.co.uk/")


def test_the_laminar_flow_keeps_only_crunch_or_high_gain():
    d = set4.load()
    assert d["rules"]["crunch_or_high_gain_only"]["sessions"] == ["cambridge/TheLaminarFlow_Headspace_Full"]
    for p in d["parts"]:
        if p["band"] == "The Laminar Flow":
            assert p["gain_class"] in ("crunch", "high-gain")
    for p in d["excluded"]:
        if any("keeps only crunch or high-gain" in r for r in p["reasons"]):
            assert p["band"] == "The Laminar Flow"


def test_no_band_from_an_earlier_set():
    earlier = {s["band"] for s in set3.load()["sessions"]}
    earlier |= {s["group"] for s in json.loads((ROOT / "docs" / "validation-datasets.json").read_text())["sessions"]
                if s.get("group")}
    assert not set(set4.bands()) & earlier


def test_judge_lag_is_lag_less_52():
    for p in set4.parts():
        assert p["judge_lag_samples"] == p["lag_samples"] - 52


# --- the guard ----------------------------------------------------------------------

def test_set4_names_and_paths_are_held_out():
    d = set4.load()
    for key, (band, directory) in set4.SESSIONS.items():   # known without the declaration
        assert key in set4._names() and band in set4._names()
        assert set4.is_held_out(f"{directory}/01_Kick.wav")
    for s in d["sessions"]:
        assert set4.is_held_out(s["band"]) and set4.is_held_out(s["key"])
        for di in s["dis"]:                                   # kept or not
            assert set4.is_held_out(set4.SET4_ROOT / di["di"])
            assert set4.is_held_out(di["di"])                  # relative to the set-4 root
            assert set4.is_held_out(str(set4.SET4_ROOT / di["di"]).replace(str(pathlib.Path.home()), "~"))
        assert set4.is_held_out(set4.SET4_ROOT / s["path"] / "27_ElecGtr02.wav")   # unlisted file
    for p in [*d["parts"], *d["excluded"]]:
        if p.get("slug"):
            assert set4.is_held_out(p["slug"])
            assert set4.is_held_out(set4.SET4_CROPS / p["slug"] / "reference.wav")
    assert set4.is_held_out(set4.SET4_ROOT / "Some Later Band - Song" / "x.wav")   # whole root
    assert set4.is_held_out(set4.SET4_ROOT / "_tools" / "catalog.json")


@pytest.mark.parametrize("x", ["No Such Band", "/tmp/x.wav", "V.M.GY",
                               str(set3.SET3_ROOT / "cambridge" / "x.wav"), pathlib.Path("relative/unknown.wav")])
def test_set4_guard_raises_on_what_it_does_not_cover(x):
    with pytest.raises(KeyError):
        set4.is_held_out(x)
    set4.refuse(x)                                            # not set 4: no objection


def test_refuse():
    for x in (set4.bands()[0], _a_di(), set4.SET4_CROPS / "anything" / "di.wav"):
        with pytest.raises(ValueError):
            set4.refuse(x)


def test_set3_guards_know_set4():
    for band in set4.bands():
        assert set3.is_held_out(band)
        with pytest.raises(ValueError):
            set3.fold_for_band(band)
    assert set3.is_held_out(_a_di())
    assert set3.is_held_out(set4.SET4_CROPS / set4.parts()[0]["slug"] / "di.wav")


@pytest.mark.parametrize("band", ["Tholas P.", "The Laminar Flow", "Ale Lak"])   # set-4 bands, or a set-2 band's name
def test_training_dis_refuses_a_set4_file(monkeypatch, band):
    from learn import di_pool
    monkeypatch.setattr(di_pool, "tracks", lambda: [(band, _a_di())])
    with pytest.raises(ValueError):
        set3.training_dis(None)


@pytest.mark.skipif(not pathlib.Path("~/ndsp-presets/runs/kill/pr12-clean/index.json").expanduser().exists(),
                    reason="K3 panel index not on this machine")
def test_training_dis_holds_no_set4_file():
    pytest.importorskip("numpy", reason="needs the analysis extra")
    dis = set3.training_dis(None)
    assert dis and not any(set4.covers(f) for f in dis)


# --- the declaration rebuilds --------------------------------------------------------

@pytest.mark.skipif(not (CATALOG.exists() and CROPS.exists()), reason="set-4 catalogue not on this machine")
def test_json_rebuilds_from_the_catalogue():
    rebuilt = json.loads(json.dumps(vs4.build(CATALOG, CROPS), ensure_ascii=False))
    committed = json.loads((ROOT / "docs" / "validation-set4.json").read_text())
    rebuilt.pop("held_out_uses")
    committed.pop("held_out_uses")
    assert rebuilt == committed
