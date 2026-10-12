"""Set 5's committed declaration and its leakage guards (learn/set5.py, learn/set3.py)."""

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import set3, set4, set5  # noqa: E402

spec = importlib.util.spec_from_file_location("validation_set5", ROOT / "research" / "validation_set5.py")
vs5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs5)

INVENTORY = pathlib.Path("~/ndsp-presets/references/datasets-set5/inventory.json").expanduser()
CROPS = pathlib.Path("~/ndsp-presets/references/validation-crops-set5").expanduser()


def _a_di():
    s = set5.load()["sessions"][0]
    return set5.SET5_ROOT / s["dis"][0]["di"]


# --- the declaration ----------------------------------------------------------------

def test_schema():
    d = set5.load()
    assert d["schema"] == "validation-set5-1"
    for k in ("declared", "inventory", "root", "crops_root", "rules", "held_out_bands", "band_strata",
              "licences", "unpaired", "counts", "sessions", "parts", "excluded", "held_out_uses"):
        assert k in d, k
    assert set(d["licences"]) == {"cambridge", "hf-rawstems"}
    for s in d["sessions"]:
        assert s["source"] in d["licences"]
        if s["source"] == "cambridge":
            assert s["publisher_original"] is True and len(s["archive_sha256"]) == 64
            assert s["route"] in ("direct", "wayback")
            assert (s["route"] == "wayback") == bool(s["wayback_capture"])
        else:
            assert s["publisher_original"] is False and s["route"] == "huggingface-rehost"
            assert s["hf_repo"] == "kwatcharasupat/mixing-secrets-rawstems"
            assert s["revision"] == "b482eb2e31aa15ff10489b3b23871a1e7a109198"
            assert all(len(f["sha256"]) == 64 for f in s["files_fetched"])
            assert s["mix_on_disk"] is False


def test_every_part_is_held_out_and_unused():
    d = set5.load()
    assert [u["test_id"] for u in d["held_out_uses"]] == ["set5-cprime-test-2026-10-12"]   # one declared use
    assert d["held_out_bands"] == set5.bands()
    assert all(s["split"] == "held_out" and s["fold"] is None for s in d["sessions"])
    assert all(p["split"] == "held_out" and p["fold"] is None for p in d["parts"])
    assert d["counts"]["kept"] == len(d["parts"])
    assert d["counts"]["excluded"] == len(d["excluded"])
    assert d["counts"]["declared_parts"] == len(d["parts"]) + len(d["excluded"])


def test_scope_clean_and_crunch_in_high_gain_report_only():
    d = set5.load()
    assert d["rules"]["scope"]["in_scope"] == ["clean", "crunch"]
    for p in d["parts"]:
        assert p["scope"] == ("in_scope" if p["gain_class"] in ("clean", "crunch") else "report_only")
    assert {p["band"] for p in set5.parts(scope="report_only")} >= {"Nova-One Studio"}
    assert all(p["scope"] == "report_only" for p in d["parts"] if p["band"] == "Nova-One Studio")
    assert len(set5.parts(scope="in_scope")) + len(set5.parts(scope="report_only")) == len(d["parts"])
    with pytest.raises(ValueError):
        set5.parts(scope="high-gain")


def test_kept_parts_meet_the_set4_rules():
    for p in set5.parts():
        assert p["waveform"]["passing_windows"] >= 3
        assert p["waveform"]["median_peak_to_sidelobe"] >= 2.0
        assert "di_touches_full_scale" in p["marks"] or not any("full scale" in f for f in p["inventory_flags"])
        assert p["polarity"] in (1, -1)
        assert p["crop"]["di_sha256"] and p["crop"]["reference_sha256"]
        assert p["evidence"]["pairs"].startswith("_tools/pairs/")


def test_the_guard_knows_every_declared_session():
    d = set5.load()
    assert {s["key"]: (s["band"], s["path"]) for s in d["sessions"]} == set5.SESSIONS
    assert [a.get("band_merge") for a in d["amendments"]] == [{"Fytakyte": "BKS"}]   # the 2026-10-12 amendment


def test_no_band_from_an_earlier_set():
    earlier = {s["band"] for s in set3.load()["sessions"]} | set(set4.bands())
    earlier |= {s["group"] for s in json.loads((ROOT / "docs" / "validation-datasets.json").read_text())["sessions"]
                if s.get("group")}
    assert not set(set5.bands()) & earlier


def test_judge_lag_is_lag_less_52():
    for p in set5.parts():
        assert p["judge_lag_samples"] == p["lag_samples"] - 52


# --- the guard ----------------------------------------------------------------------

def test_set5_names_and_paths_are_held_out():
    d = set5.load()
    for key, (band, directory) in set5.SESSIONS.items():   # known without the declaration
        assert key in set5._names() and band in set5._names()
        assert set5.is_held_out(f"{directory}/01_Kick.wav")
    for s in d["sessions"]:
        assert set5.is_held_out(s["band"]) and set5.is_held_out(s["key"])
        for di in s["dis"]:                                   # kept or not
            assert set5.is_held_out(set5.SET5_ROOT / di["di"])
            assert set5.is_held_out(di["di"])                  # relative to the set-5 root
            assert set5.is_held_out(str(set5.SET5_ROOT / di["di"]).replace(str(pathlib.Path.home()), "~"))
    for p in [*d["parts"], *d["excluded"]]:
        if p.get("slug"):
            assert set5.is_held_out(p["slug"])
            assert set5.is_held_out(set5.SET5_CROPS / p["slug"] / "reference.wav")
    assert set5.is_held_out(set5.SET5_ROOT / "Some Later Band - Song" / "x.wav")   # whole root
    assert set5.is_held_out(set5.SET5_ROOT / "_tools" / "pairs" / "x.json")


@pytest.mark.parametrize("x", ["No Such Band", "/tmp/x.wav", "V.M.GY", "Tholas P.",
                               str(set4.SET4_ROOT / "x.wav"), pathlib.Path("relative/unknown.wav")])
def test_set5_guard_raises_on_what_it_does_not_cover(x):
    with pytest.raises(KeyError):
        set5.is_held_out(x)
    set5.refuse(x)                                            # not set 5: no objection


def test_refuse():
    for x in (set5.bands()[0], _a_di(), set5.SET5_CROPS / "anything" / "di.wav"):
        with pytest.raises(ValueError):
            set5.refuse(x)


def test_set3_guards_know_set5():
    for band in set5.bands():
        assert set3.is_held_out(band)
        with pytest.raises(ValueError):
            set3.fold_for_band(band)
    assert set3.is_held_out(_a_di())
    assert set3.is_held_out(set5.SET5_CROPS / set5.parts()[0]["slug"] / "di.wav")


@pytest.mark.parametrize("band", ["Ronnie Jones", "BKS", "Ale Lak"])   # set-5 bands, or a set-2 band's name
def test_training_dis_refuses_a_set5_file(monkeypatch, band):
    from learn import di_pool
    monkeypatch.setattr(di_pool, "tracks", lambda: [(band, _a_di())])
    with pytest.raises(ValueError):
        set3.training_dis(None)


@pytest.mark.skipif(not pathlib.Path("~/ndsp-presets/runs/kill/pr12-clean/index.json").expanduser().exists(),
                    reason="K3 panel index not on this machine")
def test_training_dis_holds_no_set5_file():
    pytest.importorskip("numpy", reason="needs the analysis extra")
    dis = set3.training_dis(None)
    assert dis and not any(set5.covers(f) for f in dis)


# --- the crops and the rebuild (need the data) ---------------------------------------

@pytest.mark.skipif(not CROPS.exists(), reason="set-5 crops not on this machine")
def test_crops_exist_and_match_the_declaration():
    import hashlib

    for p in set5.parts():
        d = CROPS / p["slug"]
        rec = d / "record.json"
        assert hashlib.sha256(rec.read_bytes()).hexdigest() == p["crop"]["record_sha256"], p["slug"]
        r = json.loads(rec.read_text())
        assert r["split"] == "held_out" and r["set"] == 5 and r["excerpt_rule"] == "di-activity"
        assert r["sample_rate"] == 48000 and r["channels"] == 1
        assert r["lag"]["judge_lag_samples"] == r["lag"]["lag_samples"] - 52
        assert (r["mix_absent"] is True) == ("mix" not in r["outputs"])
        for role in ("di", "reference"):
            f = d / f"{role}.wav"
            assert hashlib.sha256(f.read_bytes()).hexdigest() == p["crop"][f"{role}_sha256"], (p["slug"], role)
            assert r["outputs"][role]["frames"] == 480000


@pytest.mark.skipif(not (INVENTORY.exists() and CROPS.exists()), reason="set-5 inventory not on this machine")
def test_json_rebuilds_from_the_inventory():
    rebuilt = json.loads(json.dumps(vs5.build(INVENTORY, CROPS), ensure_ascii=False))
    committed = json.loads((ROOT / "docs" / "validation-set5.json").read_text())
    rebuilt.pop("held_out_uses")
    committed.pop("held_out_uses")
    rebuilt.pop("amendments")                # hand-recorded after declaration, like the ledger
    committed.pop("amendments")
    assert rebuilt == committed
