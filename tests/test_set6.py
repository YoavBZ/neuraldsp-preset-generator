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
RESULT = pathlib.Path("~/ndsp-presets/listening/di-labelling/validation-result.json").expanduser()

# Amendment 2: one part per counted labelled group (song, DI, reference, gain class, kept).
LABELLED = {
    "PurlingHiss_Lolita": [("RAW_03_06", "RAW_03_05", "high-gain", True)],
    "BigTroubles_Phantom": [("RAW_05_01", "RAW_05_02", "high-gain", True),
                            ("RAW_03_08", "RAW_03_09", "high-gain", False)],   # two lag clusters
    "PortStWillow_StayEven": [("RAW_06_01", "RAW_06_02", "crunch", True),
                              ("RAW_05_01", "RAW_05_02", "crunch", True)],
    "LittleTybee_TheAlchemist": [("RAW_08_02", "RAW_08_03", "crunch", True)],
}


def _a_di():
    s = next(s for s in set6.load()["sessions"] if s["dis"])
    return set6.SET6_ROOT / s["dis"][0]["di"]


# --- the declaration ----------------------------------------------------------------

def test_schema():
    d = set6.load()
    assert d["schema"] == "validation-set6-3"
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


def test_amendment_1_first_rule_parts_all_excluded():
    """Amendment 1: no DI-role rule met its development bar, so no part of the first
    declaration is kept; their crops stay on disk, superseded."""
    d = set6.load()
    a = {x["number"]: x for x in d["amendments"]}[1]
    assert a["committed_before_application"] is True
    assert (ROOT / a["calibration"]).exists() and (ROOT / a["script"]).exists()
    assert "orientation" in d["rules"]["di_role"]["first_declared"]      # the rule that failed, kept
    first = [p for p in d["excluded"] if not p["slug"] or not p["slug"].endswith("-labelled")]
    assert len(first) == 7
    for p in first:
        assert vs6.NO_DI_ROLE in p["reasons"], p["part"]
        assert p["crop_status"] == vs6.SUPERSEDED
    assert not {p["slug"] for p in first} & {p["slug"] for p in d["parts"]}
    clark = next(p for p in first if p["song"] == "StevenClark_Bounty")
    assert vs6.NOT_GUITAR in clark["reasons"] and clark["di_label"] == "electric bass"
    assert {p["slug"]: p.get("superseded_by") for p in first if p.get("superseded_by")} == {
        "medleydb-bigtroubles-phantom-raw-05-01": "medleydb-bigtroubles-phantom-raw-05-01-labelled",
        "medleydb-bigtroubles-phantom-raw-03-08": "medleydb-bigtroubles-phantom-raw-03-08-labelled",
        "medleydb-purlinghiss-lolita-raw-03-06": "medleydb-purlinghiss-lolita-raw-03-06-labelled"}


def test_amendment_2_labelled_parts():
    """Amendment 2: each counted labelled group is one part, DI = the labelled track."""
    d = set6.load()
    a = {x["number"]: x for x in d["amendments"]}[2]
    lab = a["labelling"]
    assert (ROOT / lab["plan"]).exists() and (ROOT / lab["builder"]).exists()
    for rnd in ("first_round", "validation_round"):
        committed = (ROOT / lab[rnd]["hashes_committed_in"]).read_text()
        assert lab[rnd]["key_sha256"] in committed and lab[rnd]["page_sha256"] in committed
    assert len(lab["counted_groups"]) == 6 and len({g["song"] for g in lab["counted_groups"]}) == 4
    want = {(song, di, ref, cls, ok) for song, rows in LABELLED.items() for di, ref, cls, ok in rows}
    got = set()
    for p in d["parts"]:
        assert p["di_inferred"] is False and p["di_role"]["source"].startswith("labelled")
        assert p["slug"] == vs6.slugify("medleydb", p["song"], p["part"], "labelled")
        got.add((p["song"], p["part"], "RAW_" + p["reference"].split("_RAW_")[-1][:-4], p["gain_class"], True))
    for p in d["excluded"]:
        if p["slug"] and p["slug"].endswith("-labelled"):
            got.add((p["song"], p["part"], "RAW_" + p["reference"].split("_RAW_")[-1][:-4], p["gain_class"], False))
    assert got == want
    assert d["counts"]["kept"] == 5 and d["counts"]["labelled_parts"] == 6
    bt = next(p for p in d["excluded"] if p["slug"] == "medleydb-bigtroubles-phantom-raw-03-08-labelled")
    assert bt["reasons"] == ["two lag clusters"] and bt["crop_record_sha256"]
    assert d["in_scope_bands_by_class"] == {"crunch": ["Little Tybee", "Port St Willow"]}
    assert "AlexanderRoss" in lab["not_counted"]
    assert d["held_out_uses"] == []


def test_amendment_2_musdb_marks_per_part():
    by_song = {p["song"]: p for p in set6.parts()}
    assert by_song["PortStWillow_StayEven"]["separator_trained_on"] is True
    assert by_song["BigTroubles_Phantom"]["separator_trained_on"] is True
    assert by_song["LittleTybee_TheAlchemist"]["separator_trained_on"] is False
    assert by_song["PurlingHiss_Lolita"]["separator_trained_on"] is False
    for p in set6.parts():
        assert (p["stem_test"] == "usable") == (not p["separator_trained_on"])
    assert {p["song"] for p in set6.parts(stem_test=True)} == {"LittleTybee_TheAlchemist", "PurlingHiss_Lolita"}
    assert [p["song"] for p in set6.parts(scope="in_scope", stem_test=True)] == ["LittleTybee_TheAlchemist"]


@pytest.mark.skipif(not RESULT.exists(), reason="DI-labelling result not on this machine")
def test_amendment_2_matches_the_labelling_result():
    import hashlib

    res = json.loads(RESULT.read_text())
    a = {x["number"]: x for x in set6.load()["amendments"]}[2]["labelling"]
    assert a["validation_result"]["sha256"] == hashlib.sha256(RESULT.read_bytes()).hexdigest()
    v = res["validation"]
    assert v["passes"] and v["right"] == v["confident"] == 10 and v["decoy_letters"] == 0
    assert res["validation_key_sha256"] == a["validation_round"]["key_sha256"]
    assert res["first_round"]["key_sha256"] == a["first_round"]["key_sha256"]
    counted = {(e["song"], e["gain"]["di_file"], e["gain"]["reference"], e["gain"]["gain_class"])
               for e in res["first_round"]["labels"] if e["counts"]}
    assert counted == {(g["song"], g["di"], g["reference"], g["gain_class"]) for g in a["counted_groups"]}
    for p in set6.parts():
        e = next(e for e in res["first_round"]["labels"] if e["counts"] and e["gain"]["di_file"] == p["di"])
        assert p["lag_samples_native"] == e["gain"]["lag_samples"]


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
        assert r["di_role_source"] == "labelled" and r["pairing"]["di_inferred"] is False
        assert r["sample_rate"] == 48000 and r["channels"] == 1
        assert r["lag"]["judge_lag_samples"] == r["lag"]["lag_samples"] - 52
        for role in ("di", "reference", "mix"):
            f = d / f"{role}.wav"
            assert hashlib.sha256(f.read_bytes()).hexdigest() == p["crop"][f"{role}_sha256"], (p["slug"], role)
            assert r["outputs"][role]["frames"] == 480000


@pytest.mark.skipif(not (INVENTORY.exists() and CROPS.exists() and RESULT.exists()),
                    reason="set-6 inventory, crops or labelling result not on this machine")
def test_json_rebuilds_from_the_inventory():
    rebuilt = json.loads(json.dumps(vs6.build(INVENTORY, CROPS), ensure_ascii=False))
    committed = json.loads((ROOT / "docs" / "validation-set6.json").read_text())
    for k in ("held_out_uses", "amendments"):
        rebuilt.pop(k)
        committed.pop(k)
    assert rebuilt == committed
