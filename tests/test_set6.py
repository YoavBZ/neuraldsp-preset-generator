"""Set 6's committed declaration (MedleyDB) and its leakage guards (learn/set6.py, learn/set3.py)."""

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import set3, set4, set5, set6  # noqa: E402

spec = importlib.util.spec_from_file_location("validation_set6", ROOT / "research" / "validation_set6.py")
vs6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs6)

INVENTORY = pathlib.Path("~/ndsp-presets/references/datasets-medleydb/inventory.json").expanduser()
CROPS = pathlib.Path("~/ndsp-presets/references/validation-crops-set6").expanduser()


def _a_di():
    s = next(s for s in set6.load()["sessions"] if s["dis"])
    return set6.SET6_ROOT / s["dis"][0]["di"]


# --- the declaration ----------------------------------------------------------------

def test_schema():
    d = set6.load()
    assert d["schema"] == "validation-set6-2"
    for k in ("declared", "inventory", "root", "crops_root", "rules", "held_out_bands", "band_strata",
              "licences", "provenance", "unpaired", "role_failures", "counts", "sessions", "parts",
              "excluded", "held_out_uses"):
        assert k in d, k
    assert set(d["licences"]) == {"medleydb"}
    assert "NonCommercial-ShareAlike 4.0" in d["licences"]["medleydb"]
    assert {v["record"] for v in d["provenance"]["archives"].values()} == {"1649325", "1715175"}
    for s in d["sessions"]:
        assert s["source"] == "medleydb" and s["medleydb_version_dir"] in ("V1", "V2")
        assert s["path"] == f"audio/{s['medleydb_version_dir']}/{s['song']}"


def test_every_part_is_held_out_and_unused():
    d = set6.load()
    assert d["held_out_uses"] == []                       # no declared use yet
    assert d["held_out_bands"] == set6.bands()
    assert all(s["split"] == "held_out" and s["fold"] is None for s in d["sessions"])
    assert all(p["split"] == "held_out" and p["fold"] is None for p in d["parts"])
    assert d["counts"]["kept"] == len(d["parts"])
    assert d["counts"]["excluded"] == len(d["excluded"])
    assert d["counts"]["declared_parts"] == len(d["parts"]) + len(d["excluded"])
    assert d["counts"]["songs"] == len(set6.SESSIONS) == 73


def test_scope_clean_and_crunch_in_high_gain_report_only():
    d = set6.load()
    assert d["rules"]["scope"]["in_scope"] == ["clean", "crunch"]
    for p in d["parts"]:
        assert p["scope"] == ("in_scope" if p["gain_class"] in ("clean", "crunch") else "report_only")
    assert len(set6.parts(scope="in_scope")) + len(set6.parts(scope="report_only")) == len(d["parts"])
    with pytest.raises(ValueError):
        set6.parts(scope="high-gain")


def test_amendment_1_no_di_part():
    """Amendment 1: no DI-role rule met its development bar, so set 6 has no DI part."""
    d = set6.load()
    a = {x["number"]: x for x in d["amendments"]}[1]
    assert a["committed_before_application"] is True
    assert (ROOT / a["calibration"]).exists() and (ROOT / a["script"]).exists()
    assert "unusable for DI-based tests" in d["use"]
    assert d["parts"] == [] and set6.parts() == [] and d["counts"]["kept"] == 0
    assert d["in_scope_bands_by_class"] == {}
    assert "orientation" in d["rules"]["di_role"]["first_declared"]      # the rule that failed, kept
    for p in d["excluded"]:
        assert vs6.NO_DI_ROLE in p["reasons"], p["part"]
    clark = next(p for p in d["excluded"] if p["song"] == "StevenClark_Bounty")
    assert vs6.NOT_GUITAR in clark["reasons"] and clark["di_label"] == "electric bass"


def test_the_calibration_fails_its_bar():
    c = json.loads((ROOT / "docs" / "validation-set6-di-calibration.json").read_text())
    bar = c["fa_bar"]
    for name, fam in c["families"].items():
        lbo = fam["leave_band_out"]
        fa, n = lbo["false_accepts"]
        kept, total = lbo["recall_all"]
        assert fa > bar * n or kept <= total / 2, name     # neither family passes
    fa, n = c["declared_rule"]["false_accepts"]
    kept, total = c["declared_rule"]["recall_all"]
    assert kept <= total / 2


def test_musdb18_overlap_marked():
    d = set6.load()
    marked = {s["song"]: s["separator_trained_on"] for s in d["sessions"] if s["separator_trained_on"]}
    assert len(marked) == d["counts"]["separator_trained_on"] == 35
    assert marked["StevenClark_Bounty"]["musdb18_subset"] == "train"
    assert marked["AlexanderRoss_GoodbyeBolero"]["musdb18_validation"] is True
    assert marked["Meaxic_TakeAStep"]["musdb18_validation"] is True
    assert "DahkaBand_SoldierMan" not in marked and "Sweat_Elegy" not in marked
    lists = d["provenance"]["musdb18_lists"]
    assert set(lists) == {"tracklist.csv", "musdb_mus.yaml", "musdb_splits.json"}


def test_licence_texts_identical():
    lt = set6.load()["licence_texts"]
    assert lt["identical"] is True and lt["V1"]["md5"] == lt["V2"]["md5"] == "071086fd72dc543a4a680a747874bd16"


def test_the_guard_knows_every_declared_session():
    d = set6.load()
    assert {s["key"]: (s["band"], s["path"]) for s in d["sessions"]} == set6.SESSIONS


def test_no_band_from_an_earlier_set():
    earlier = {s["band"] for s in set3.load()["sessions"]} | set(set4.bands()) | set(set5.bands())
    earlier |= {s["group"] for s in json.loads((ROOT / "docs" / "validation-datasets.json").read_text())["sessions"]
                if s.get("group")}
    norm = lambda b: "".join(c for c in b.lower() if c.isalnum())   # noqa: E731
    assert not {norm(b) for b in set6.bands()} & {norm(b) for b in earlier}


def test_judge_lag_is_lag_less_52():
    for p in set6.parts():
        assert p["judge_lag_samples"] == p["lag_samples"] - 52


# --- the guard ----------------------------------------------------------------------

def test_set6_names_and_paths_are_held_out():
    d = set6.load()
    for key, (band, directory) in set6.SESSIONS.items():   # known without the declaration
        assert key in set6._names() and band in set6._names()
        assert set6.is_held_out(f"{directory}/x_MIX.wav")
    for s in d["sessions"]:
        assert set6.is_held_out(s["band"]) and set6.is_held_out(s["key"])
        for di in s["dis"]:
            assert set6.is_held_out(set6.SET6_ROOT / di["di"])
            assert set6.is_held_out(di["di"])                  # relative to the set-6 root
            assert set6.is_held_out(str(set6.SET6_ROOT / di["di"]).replace(str(pathlib.Path.home()), "~"))
    for p in [*d["parts"], *d["excluded"]]:
        if p.get("slug"):
            assert set6.is_held_out(p["slug"])
            assert set6.is_held_out(set6.SET6_CROPS / p["slug"] / "mix.wav")
    assert set6.is_held_out(set6.SET6_ROOT / "audio" / "V2" / "Unlisted_Song" / "x.wav")   # whole root
    assert set6.is_held_out(set6.SET6_ROOT / "_tools" / "pairs" / "x.json")


@pytest.mark.parametrize("x", ["No Such Band", "/tmp/x.wav", "V.M.GY", "Ronnie Jones",
                               str(set5.SET5_ROOT / "x.wav"), pathlib.Path("relative/unknown.wav")])
def test_set6_guard_raises_on_what_it_does_not_cover(x):
    with pytest.raises(KeyError):
        set6.is_held_out(x)
    set6.refuse(x)                                            # not set 6: no objection


def test_refuse():
    for x in (set6.bands()[0], _a_di(), set6.SET6_CROPS / "anything" / "di.wav"):
        with pytest.raises(ValueError):
            set6.refuse(x)


def test_set3_guards_know_set6():
    for band in set6.bands():
        assert set3.is_held_out(band)
        with pytest.raises(ValueError):
            set3.fold_for_band(band)
    assert set3.is_held_out(_a_di())
    if set6.parts():
        assert set3.is_held_out(set6.SET6_CROPS / set6.parts()[0]["slug"] / "di.wav")


@pytest.mark.parametrize("band", ["Meaxic", "SWEAT", "Ale Lak"])   # set-6 bands, or a set-2 band's name
def test_training_dis_refuses_a_set6_file(monkeypatch, band):
    from learn import di_pool
    monkeypatch.setattr(di_pool, "tracks", lambda: [(band, _a_di())])
    with pytest.raises(ValueError):
        set3.training_dis(None)


@pytest.mark.skipif(not pathlib.Path("~/ndsp-presets/runs/kill/pr12-clean/index.json").expanduser().exists(),
                    reason="K3 panel index not on this machine")
def test_training_dis_holds_no_set6_file():
    pytest.importorskip("numpy", reason="needs the analysis extra")
    dis = set3.training_dis(None)
    assert dis and not any(set6.covers(f) for f in dis)


# --- the crops and the rebuild (need the data) ---------------------------------------

@pytest.mark.skipif(not CROPS.exists(), reason="set-6 crops not on this machine")
def test_crops_exist_and_match_the_declaration():
    import hashlib

    for p in set6.load()["excluded"]:             # superseded crops: still on disk, unchanged
        if p.get("crop_record_sha256"):
            rec = CROPS / p["slug"] / "record.json"
            assert hashlib.sha256(rec.read_bytes()).hexdigest() == p["crop_record_sha256"], p["slug"]
    for p in set6.parts():
        d = CROPS / p["slug"]
        rec = d / "record.json"
        assert hashlib.sha256(rec.read_bytes()).hexdigest() == p["crop"]["record_sha256"], p["slug"]
        r = json.loads(rec.read_text())
        assert r["split"] == "held_out" and r["set"] == 6 and r["excerpt_rule"] == "di-activity"
        assert r["sample_rate"] == 48000 and r["channels"] == 1
        assert r["lag"]["judge_lag_samples"] == r["lag"]["lag_samples"] - 52
        for role in ("di", "reference", "mix"):
            f = d / f"{role}.wav"
            assert hashlib.sha256(f.read_bytes()).hexdigest() == p["crop"][f"{role}_sha256"], (p["slug"], role)
            assert r["outputs"][role]["frames"] == 480000


@pytest.mark.skipif(not (INVENTORY.exists() and CROPS.exists()), reason="set-6 inventory not on this machine")
def test_json_rebuilds_from_the_inventory():
    rebuilt = json.loads(json.dumps(vs6.build(INVENTORY, CROPS), ensure_ascii=False))
    committed = json.loads((ROOT / "docs" / "validation-set6.json").read_text())
    for k in ("held_out_uses", "amendments"):
        rebuilt.pop(k)
        committed.pop(k)
    assert rebuilt == committed
