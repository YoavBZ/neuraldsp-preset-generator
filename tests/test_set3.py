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
