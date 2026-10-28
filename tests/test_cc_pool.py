"""The clean/crunch pool's step 2 guards (`learn/cc_pool.py`): the released sessions, the V-real band bar, the
never-test-again rule, and the released DI rows. No audio is read."""

import json
import pathlib

import pytest

from learn import arm_a_mega53 as A
from learn import cc_pool as CC
from learn import clean_di as CD
from learn import verify_tracks as V

ROOT = pathlib.Path(__file__).resolve().parents[1]
REFS = pathlib.Path("/data/refs")


def released_path(key, name="10_ElecGtr1DI.wav", refs=CC.REFS):
    return str(pathlib.Path(refs) / CC.RELEASED[key][3] / name)


# --- the declaration ---------------------------------------------------------------------------------------------

def test_released_is_the_plans_list():
    assert len(CC.RELEASED) == 19
    by = {}
    for key, (src, band, _, _) in CC.RELEASED.items():
        by.setdefault(src, set()).add(band)
    assert by["sets-1-2"] == {"Boogie Snakes", "Forkupines", "Lights Off Clarity", "The Maybe Next Years", "Tim Taler"}
    assert by["set3"] == {"Dunning Kruger", "Silona"}
    assert by["set5"] == {"Hazael", "Peter White", "BKS", "Ronnie Jones", "Saturn Syndicate", "Chris Durban",
                          "Hannes Keseberg"}
    assert not CC.released_bands() & CC.VREAL_BANDS


def test_released_sessions_match_the_catalogues():
    v = json.loads(CD.SETS_1_2.read_text())
    s12 = {pathlib.PurePosixPath(s["path"]).name: s for s in v["sessions"]}
    s3 = json.loads((ROOT / "docs/validation-set3.json").read_text())
    s5 = {s["key"]: s for s in json.loads((ROOT / "docs/validation-set5.json").read_text())["sessions"]}
    for key, (src, band, sdir, tracks) in CC.RELEASED.items():
        assert tracks.startswith(sdir)
        if src == "sets-1-2":
            assert s12[key]["split"] == "held_out" and CD.band_of(s12[key]) == band
            assert sdir == "datasets/" + s12[key]["path"]
        elif src == "set3":
            assert band in s3["held_out_bands"]
            if key != "DunningKruger_Sascha_Full":           # downloaded with set 3, never declared
                assert any(s["key"] == f"cambridge/{key}" and s["split"] == "held_out" for s in s3["sessions"])
        else:
            s = s5[f"cambridge/{key}"]
            assert s["band"] == band and tracks == "datasets-set5/" + s["path"]


def test_declarations_record_the_release():
    for f, src in (("validation-datasets.json", "sets-1-2"), ("validation-set3.json", "set3"),
                   ("validation-set5.json", "set5")):
        d = json.loads((ROOT / "docs" / f).read_text())
        rel = [u for u in d["held_out_uses"] if u.get("test_id") == CC.RELEASE_ID]
        assert len(rel) == 1, f
        want = {f"cambridge/{k}" for k, v in CC.RELEASED.items() if v[0] == src}
        assert set(rel[0]["sessions"]) == want, f
    led = json.loads((ROOT / "docs/dev-test-ledger.json").read_text())
    assert [t for t in led["tests"] if t.get("test_id") == CC.LEDGER_ID]
    assert CC.ledger_ok()


def test_sascha_is_released_not_refused():
    assert "cambridge/DunningKruger_Sascha_Full" not in CD.REFUSED_SESSIONS
    assert "cambridge/UmphreysMcGee_CrucialTaunt_Full" in CD.REFUSED_SESSIONS   # a line-out, not a DI: still out
    assert "DunningKruger_Sascha_Full" in CC.RELEASED


# --- released_entry ----------------------------------------------------------------------------------------------

def test_released_entry_matches_paths_under_released_sessions_only():
    e = CC.released_entry(released_path("BKS_TooMuch_Full", refs=REFS), refs=REFS)
    assert e["key"] == "BKS_TooMuch_Full" and e["band"] == "BKS" and e["source"] == "set5"
    assert CC.released_entry(str(REFS / "datasets-set5/BKS - Too Much"), refs=REFS)["key"] == "BKS_TooMuch_Full"
    # a sibling whose name only starts like a released session, a relative path, a crop, an unreleased set-5 session
    assert CC.released_entry(str(REFS / "datasets/cambridge/TimTaler_Stalker_Full2/x.wav"), refs=REFS) is None
    assert CC.released_entry("datasets/cambridge/TimTaler_Stalker_Full/x.wav", refs=REFS) is None
    assert CC.released_entry(str(REFS / "validation-crops-set5/cambridge-BKS-ElecGtr1/di.wav"), refs=REFS) is None
    assert CC.released_entry(str(REFS / "datasets-set5/Nova-One Studio - Four Graham/x.wav"), refs=REFS) is None
    assert CC.released_entry(str(REFS / "datasets-set5/Fytakyte - Too Much/Gtr_EG/x.wav"), refs=REFS) is None


# --- the pool's band guards (fail closed) -------------------------------------------------------------------------

def test_vreal_bands_derive_from_the_frozen_membership():
    led = json.loads((ROOT / "docs/dev-test-ledger.json").read_text())
    t3 = next(t for t in led["tests"] if t.get("test_id") == "trusted-data-t3")
    assert CC.vreal_bands(t3["parts"]["v_real_12"], A.F_POOL) == CC.VREAL_BANDS
    assert len(CC.VREAL_BANDS) == 7 and CC.VREAL_BANDS <= set(A.F_POOL)
    with pytest.raises(ValueError, match="no stage-F band"):
        CC.vreal_bands(["cambridge-unknown-elecgtr1"], A.F_POOL)


@pytest.mark.parametrize("band", sorted(CC.VREAL_BANDS))
def test_every_vreal_band_is_barred(band):
    with pytest.raises(ValueError, match="V-real band"):
        CC.refuse_pool_band(band)


@pytest.mark.parametrize("band,why", [(None, "no band"), ("", "no band"), ("The Apprehended", "known-answer"),
                                      ("Blue Manic", "reserved"), ("Fytakyte", "never trains")])
def test_pool_band_guard_fails_closed(band, why):
    with pytest.raises(ValueError, match=why):
        CC.refuse_pool_band(band)


def test_other_bands_pass_the_pool_band_guard():
    for band in ("Boogie Snakes", "BKS", "The Travelling Band", "Turbosauro", "Doom Flamingo", "Adam Buckley"):
        CC.refuse_pool_band(band)                                # stage F's non-V-real bands may enter (tier 1)


def test_check_pool_rows_refuses_vreal_missing_path_and_held_out():
    ok = {"id": "a", "path": released_path("TimTaler_Stalker_Full"), "band": "Tim Taler", "set": "x"}
    CC.check_pool_rows([ok])
    with pytest.raises(ValueError, match="V-real"):
        CC.check_pool_rows([{**ok, "band": "Zeno"}], refuse=lambda r: None)
    with pytest.raises(ValueError, match="no path"):
        CC.check_pool_rows([{**ok, "path": ""}])
    held = {"id": "b", "path": str(CC.REFS / "datasets-set5/Nova-One Studio - Four Graham/x/10_GtrDI.wav"),
            "band": "Nova-One Studio", "set": "x"}
    with pytest.raises(ValueError):
        CC.check_pool_rows([held])


# --- refuse_held_out: released sessions pass, nothing else changes ------------------------------------------------

def test_refuse_held_out_passes_released_sessions_with_their_band():
    for key, (src, band, _, _) in CC.RELEASED.items():
        CD.refuse_held_out({"path": released_path(key), "band": band, "set": src})


def test_refuse_held_out_refuses_a_released_path_with_another_band():
    with pytest.raises(ValueError, match="declared"):
        CD.refuse_held_out({"path": released_path("Silona_LearningHowToFly_Full"), "band": "Zeno", "set": "set3"})


@pytest.mark.parametrize("path,band,st", [
    ("datasets-set5/Nova-One Studio - Four Graham/NovaOneStudio_FourGraham_Full/10_GtrDI.wav", "Nova-One Studio", 5),
    ("datasets-set5/Fytakyte - Too Much/Gtr_EG/Gtr_EG.wav", "Fytakyte", 5),
    ("validation-crops-set5/cambridge-BKS-ElecGtr1/di.wav", "BKS", 5),
    ("datasets-set3/cambridge/VMGY_Omen_Full/VMGY_Omen_Full/10_ElecGtr1DI.wav", "V.M.GY", 3),
    ("datasets/cambridge/ChrisColtraine_ThatsHowIGotToMemphis_Full/10_GtrDI.wav", "Chris Coltraine", 1),
    ("datasets/telefunken/Catbite - Bad Influence LIVE FROM THE LAB/GTR DI.wav", "Catbite", 1),
])
def test_refuse_held_out_still_refuses_unreleased_held_out_material(path, band, st):
    with pytest.raises((ValueError, KeyError)):
        CD.refuse_held_out({"path": str(CC.REFS / path), "band": band, "set": st})


def test_refuse_held_out_still_refuses_an_undeclared_session_of_a_held_out_band():
    rec = {"path": str(CC.REFS / "datasets-cambridge-new/X_Y_Full/1_GtrDI.wav"), "band": "Catbite", "set": "undeclared"}
    with pytest.raises(ValueError, match="held-out band"):
        CD.refuse_held_out(rec)


# --- never a test again ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("x", ["BKS", "Dunning Kruger", "Forkupines_SugarFaith_Full", "Fytakyte",
                               "cambridge/DunningKruger_Sascha_Full", "hf-rawstems/Fytakyte - Too_Much",
                               "cambridge-Stalker-ElecGtr01", "cambridge/Stalker", "cambridge-endance-gtr4",
                               "cambridge-bulldozer-elecgtr1a", released_path("Hazael_AMiLado_Full")])
def test_released_material_is_never_a_test_again(x):
    with pytest.raises(ValueError, match="never a test again|spent"):
        CC.refuse_test(x)


@pytest.mark.parametrize("x", ["Nova-One Studio", "MOPP", "hf-rawstems/Jeff_Hirata - Sunshine", "Catbite"])
def test_unreleased_held_out_material_may_still_be_tested(x):
    CC.refuse_test(x)


def test_refuse_test_covers_the_band_in_a_slug():
    with pytest.raises(ValueError):
        CC.refuse_test("cambridge-Bad_Influence-GTR (Tim Taler)")


# --- the released DI rows ----------------------------------------------------------------------------------------

def test_session_rows_follow_the_inventory_rule_and_stay_pending():
    files = ["01_Kick.wav", "09_ElecGtr1Amp.wav", "10_ElecGtr1DI.wav", "11_ElecGtr2.wav", "12_ElecGtr2DI.wav",
             "13_AcousticGtrDI.wav", "14_SynthGtrDI.wav", "20_LeadVox.wav"]
    rows = CC.session_rows("K_Full", "/d/K_Full", files, "Band", "set5", "rock",
                           [("ElecGtr1", "10_ElecGtr1DI.wav", ["09_ElecGtr1Amp.wav", "missing.wav"])],
                           mix=["01_Kick.wav", "20_LeadVox.wav"], vocals=["20_LeadVox.wav"])
    assert [pathlib.Path(r["path"]).name for r in rows] == ["10_ElecGtr1DI.wav", "12_ElecGtr2DI.wav"]
    a, b = rows
    assert a["own"] == ["09_ElecGtr1Amp.wav"] and b["own"] == ["11_ElecGtr2.wav"] and b["part"] == "ElecGtr2"
    assert a["id"] == "set5/K_Full/10_ElecGtr1DI.wav" and a["session_dir"] == "/d/K_Full"
    assert all(CD.INTAKE_PENDING in r["notes"] and r["training_ok"] is False for r in rows)
    assert a["mix"] == ["01_Kick.wav", "20_LeadVox.wav"] and a["vocals"] == ["20_LeadVox.wav"]
    with pytest.raises(ValueError, match="not on disk"):
        CC.session_rows("K_Full", "/d", files, "Band", "set5", None, [("ElecGtr9", "99_ElecGtr9DI.wav", None)])


def test_cross_check_reports_differences_with_the_intake():
    r = {"id": "set5/BKS_TooMuch_Full/a.wav", "song": "BKS_TooMuch_Full", "path": "p", "part": "x", "own": [],
         "band": "BKS"}
    assert CC.cross_check([r], [dict(r)]) == []
    assert CC.cross_check([r], [{**r, "own": ["y"]}]) == [f"{r['id']}: own [] vs intake ['y']"]
    assert CC.cross_check([], [r]) == [f"only in the intake: {r['id']}"]
    assert CC.cross_check([r], [{**r, "song": "TheTravellingBand_Quicksand_Full"}]) == [f"only here: {r['id']}"]


# --- the stem scan: its own shards, the per-example rule ----------------------------------------------------------

def test_cc_shards_never_mix_with_t0s_stem_shards(tmp_path):
    (tmp_path / "t0").mkdir()
    for prefix, sd in (("stems", "/a"), (CC.STEM_PREFIX, "/b")):
        (tmp_path / "t0" / f"{prefix}-0of1.json").write_text(json.dumps(
            {"shard": [0, 1], "complete": True, "floor_db": -35.0, "sessions": {sd: {}}}))
    t0, _ = V.load_shards(tmp_path, "stems", "sessions", lambda d: True)
    cc, _ = V.load_shards(tmp_path, CC.STEM_PREFIX, "sessions", lambda d: True)
    assert set(t0) == {"/a"} and set(cc) == {"/b"}


def test_stems_report_reads_both_rules():
    row = {"sources": ["09_ElecGtr1Amp.wav", "11_ElecGtr2.wav"],
           "stems": {"01_Kick.wav": {"pass": False, "takes_db": {"09_ElecGtr1Amp.wav": -20.0, "11_ElecGtr2.wav": -60.0}},
                     "05_BassDI.wav": {"pass": False, "takes_db": {"09_ElecGtr1Amp.wav": -10.0}},
                     "06_Keys.wav": {"pass": True, "takes_db": {"09_ElecGtr1Amp.wav": -50.0}}}}
    kept, dropped, by_part = CC.stems_report(row, -35.0)
    assert kept == ["06_Keys.wav"] and dropped == ["01_Kick.wav", "05_BassDI.wav"]
    k1, k2 = (V.guitar_part_key(s) for s in row["sources"])
    assert by_part[k1] == ["05_BassDI.wav", "06_Keys.wav"]            # its own leak drops the kick; BassDI exempt
    assert by_part[k2] == ["01_Kick.wav", "05_BassDI.wav", "06_Keys.wav"]
