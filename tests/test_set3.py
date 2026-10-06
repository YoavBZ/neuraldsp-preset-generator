"""Set 3's committed declaration and its loader (learn/set3.py)."""

import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import set3  # noqa: E402

spec = importlib.util.spec_from_file_location("validation_set3", ROOT / "research" / "validation_set3.py")
vs3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs3)


def test_split_is_by_band_and_folds_cover_development():
    d = set3.load()
    held = set(d["held_out_bands"])
    assert held == set(set3.bands("held_out"))
    assert not held & set(set3.bands("development"))
    assert "Eat The Feeder" not in held
    for p in set3.parts("held_out"):
        assert p["fold"] is None and p["band"] in held
    folded = [p for f in range(4) for p in set3.parts("development", f)]
    assert len(folded) == len(set3.parts("development"))


def test_draw_reproduces_from_strata():
    d = set3.load()
    held, fold_of = vs3.draw(d["band_strata"])
    assert held == d["held_out_draw"]
    assert {str(f): sorted(b for b, x in fold_of.items() if x == f) for f in range(4)} == d["folds"]
    assert fold_of["Eat The Feeder"] == 2


def test_training_sessions_exclude_held_out_and_test_fold():
    for f in range(4):
        sessions = set3.training_sessions(f)
        assert all(s["split"] == "development" and s["fold"] != f for s in sessions)
        test_bands = {p["band"] for p in set3.parts("development", f)}
        assert not test_bands & {s["band"] for s in sessions}
    assert not any(set3.is_held_out(s["key"]) for s in set3.training_sessions(None))


def test_judge_lag_is_lag_less_52():
    for p in set3.parts():
        assert p["judge_lag_samples"] == p["lag_samples"] - 52
        assert set3.lag(p["slug"]) == p["judge_lag_samples"]


def test_bad_filters_rejected():
    with pytest.raises(ValueError):
        set3.parts("held_out", 0)
    with pytest.raises(ValueError):
        set3.parts(fold=4)


def test_eat_the_feeder_keeps_its_k3_fold():
    panel = pathlib.Path("~/ndsp-presets/runs/kill/pr12-clean/index.json").expanduser()
    if not panel.exists():
        pytest.skip("K3 panel index not on this machine")
    from learn.train import k3_folds
    fold_of, _ = k3_folds()
    for band, fold in set3.load()["rules"]["pinned_folds"].items():
        assert fold_of[band] == fold


# --- leakage guards ----------------------------------------------------------------

K3_PANEL = pathlib.Path("~/ndsp-presets/runs/kill/pr12-clean/index.json").expanduser()
needs_k3 = pytest.mark.skipif(not K3_PANEL.exists(), reason="K3 panel index not on this machine")
CATALOG = pathlib.Path("~/ndsp-presets/references/datasets-set3/catalog.json").expanduser()
CROPS = pathlib.Path("~/ndsp-presets/references/validation-crops-set3").expanduser()


def _sessions(split):
    return [s for s in set3.load()["sessions"] if s["split"] == split]


@needs_k3
def test_fold_for_band_merges_k3_and_set3():
    from learn.train import k3_folds
    assert set3.fold_for_band("Eat The Feeder") == 2
    assert set3.fold_for_band("Guitar-TECHS P1") == -1
    for band, fold in k3_folds()[0].items():
        assert set3.fold_for_band(band) == fold
    for s in _sessions("development"):
        assert set3.fold_for_band(s["band"]) == (-1 if s["fold"] is None else s["fold"])
    assert set3.fold_for_band("Cnoc An Tursa") == -1          # no kept part: unfolded


def test_fold_for_band_fails_closed():
    for band in set3.load()["held_out_bands"] + ["Catbite"]:   # set 3, and set 2's held out
        with pytest.raises(ValueError):
            set3.fold_for_band(band)
    if K3_PANEL.exists():
        with pytest.raises(KeyError):
            set3.fold_for_band("No Such Band")


def test_is_held_out_names_and_paths():
    root = set3.SET3_ROOT
    for s in _sessions("held_out"):
        assert set3.is_held_out(s["band"]) and set3.is_held_out(s["key"])
        for di in s["dis"]:
            assert set3.is_held_out(root / di["di"])                 # absolute path
            assert set3.is_held_out(di["di"])                        # relative to the root
            assert set3.is_held_out(str(root / di["di"]).replace(str(pathlib.Path.home()), "~"))
        assert set3.is_held_out(root / s["path"] / "any" / "other.wav")
    for s in _sessions("development"):
        assert not set3.is_held_out(s["band"]) and not set3.is_held_out(s["key"])
        for di in s["dis"]:
            assert not set3.is_held_out(root / di["di"])
    for p in set3.parts("held_out"):
        assert set3.is_held_out(p["slug"]) and set3.is_held_out(set3.SET3_CROPS / p["slug"] / "di.wav")
    for e in set3.load()["excluded"]:                        # excluded parts follow their band
        if e["slug"]:
            assert set3.is_held_out(e["slug"]) == (e["band"] in set3.load()["held_out_bands"])
    assert set3.is_held_out(set3.SET3_CROPS / "cambridge-japan-song-gtr5" / "reference.wav")
    assert not set3.is_held_out("Guitar-TECHS P1")
    assert not set3.is_held_out(set3.GUITAR_TECHS_DIR / "P1_chords" / "audio" / "directinput" / "x.wav")


def test_is_held_out_knows_sets_1_and_2():
    gt = set3.SETS_1_2_ROOT / "guitar-techs" / "P3_music" / "audio" / "directinput"
    assert set3.is_held_out(gt / "directinput_02.wav")       # set 1 shares this directory
    assert not set3.is_held_out(gt / "directinput_01.wav")
    assert set3.is_held_out(set3.SETS_1_2_ROOT / "cambridge" / "TimTaler_Stalker_Full" / "x.wav")
    assert set3.is_held_out("Catbite") and not set3.is_held_out("Ale Lak")


@pytest.mark.parametrize("x", [
    "No Such Band", "/tmp/x.wav", "cambridge/VMGY_Omen_Fullx/a.wav",
    str(set3.SET3_ROOT / "_tools" / "gcc.py"),
    str(set3.SETS_1_2_ROOT / "guitar-techs" / "P3_music" / "audio" / "directinput" / "directinput_99.wav"),
    pathlib.Path("relative/unknown.wav")])
def test_is_held_out_raises_on_unknown(x):
    with pytest.raises(KeyError):
        set3.is_held_out(x)


@needs_k3
@pytest.mark.parametrize("fold", [None, 0, 1, 2, 3])
def test_training_dis(fold):
    d = set3.load()
    dis = set3.training_dis(fold)
    got = {str(f) for f in dis}
    for s in d["sessions"]:
        for di in s["dis"]:
            path = str(set3.SET3_ROOT / di["di"])
            want = (s["split"] == "development" and not di["clipped"]
                    and (fold is None or s["fold"] != fold))
            assert (path in got) == want, path
    assert not any(set3.is_held_out(f) for f in dis)
    if fold is not None:
        assert not any(set3.fold_for_band(b) == fold for b in _bands_of(dis))
    wickerman = set3.SET3_ROOT / "cambridge/EatTheFeeder_Wickerman_Full/EatTheFeeder_Wickerman_Full"
    assert str(wickerman / "32_ElecGtr5DI.wav") not in got
    assert str(wickerman / "34_ElecGtr6DI.wav") not in got
    assert (str(wickerman / "21_ElecGtr1DI.wav") in got) == (fold != 2)
    if set3.GUITAR_TECHS_DIR.exists():
        assert any(str(set3.GUITAR_TECHS_DIR) in f for f in got)    # every fold trains on it


def _bands_of(dis):
    from learn import di_pool
    band_of = {str(f): b for b, f in di_pool.tracks()}
    for s in set3.load()["sessions"]:
        for di in s["dis"]:
            band_of[str(set3.SET3_ROOT / di["di"])] = s["band"]
    return {band_of[str(f)] for f in dis}


def test_clipped_dis_match_the_catalogue_line():
    clipped = sorted((s["band"], di["part"]) for s in set3.load()["sessions"]
                     for di in s["dis"] if di["clipped"])
    assert clipped == [("Dunning Kruger", "Gtr5"), ("Eat The Feeder", "ElecGtr5"),
                       ("Eat The Feeder", "ElecGtr6"), ("V.M.GY", "ElecGtr2")]
    assert all(di["clipped"] == (di["di_clip_runs"] >= 10)
               for s in set3.load()["sessions"] for di in s["dis"])


# --- the declaration rebuilds --------------------------------------------------------

@pytest.mark.skipif(not (CATALOG.exists() and CROPS.exists()), reason="set-3 catalogue not on this machine")
def test_json_rebuilds_from_the_catalogue():
    import json
    rebuilt = json.loads(json.dumps(vs3.build(CATALOG, CROPS), ensure_ascii=False))
    committed = json.loads((ROOT / "docs" / "validation-set3.json").read_text())
    rebuilt.pop("held_out_uses")
    committed.pop("held_out_uses")         # appended to as held-out uses are declared
    assert rebuilt == committed


# --- polarity: the judge reads magnitudes ----------------------------------------------

def test_judge_ignores_polarity():
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    from analysis.aligned import aligned_distance, estimate_lag

    rng = np.random.default_rng(0)
    sr, n = 48000, 4 * 48000
    t = np.arange(n) / sr
    env = (np.sin(2 * np.pi * 1.5 * t) > -0.3).astype(float)
    di = env * (np.sin(2 * np.pi * 110 * t) + 0.3 * np.sin(2 * np.pi * 330 * t)
                + 0.02 * rng.standard_normal(n))
    render = np.tanh(3 * np.roll(di, 52)) + 0.2 * np.tanh(3 * np.roll(di, 52)) ** 2
    recording = np.roll(np.tanh(2 * di) + 0.01 * rng.standard_normal(n), 52 + 30)
    base = aligned_distance(recording, render, di, lag=30, start_s=0.5)
    assert base.distance is not None
    for rec, ren, d in ((-recording, render, di), (recording, -render, di), (recording, render, -di)):
        flipped = aligned_distance(rec, ren, d, lag=30, start_s=0.5)
        assert flipped.distance == pytest.approx(base.distance, abs=1e-9)
    assert estimate_lag(-recording, [render], hint=30) == estimate_lag(recording, [render], hint=30)
