"""C3r's `pipeline_fix train-ft --c3r` path (docs/full-controls-plan.md, "C2r and C3r in detail"): its refusals, its run
names and its row and fold wiring up to the first step (`--dry-run`), on stub data. Needs torch (the demucs venv); the
light CI runner skips it."""
import argparse
import json

import pytest

pytest.importorskip("numpy")
pytest.importorskip("torch")

from learn import full_controls_c2 as C2  # noqa: E402
from learn import full_controls_c2r as R  # noqa: E402
from learn import full_controls_c3 as C3  # noqa: E402
from learn import full_controls_c3r as R3  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import pipeline_fix as P  # noqa: E402
from tests import test_full_controls_c2 as T2  # noqa: E402

SEED = P.SEEDS[0]


def ns(**kw):
    a = dict(real_fold=None, inner=False, seed=SEED, masked=True, c3=False, c3r="all", real_frac=1.0,
             shuffle_real=False, h4=None, ft_lr=None, ft_cap=300, dry_run=True)
    a.update(kw)
    return argparse.Namespace(**a)


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda k: {})
    return tmp_path


# --- the refusals ------------------------------------------------------------------------------------------------------

def test_r_ctl_has_no_all_labels_pair(base):
    with pytest.raises(SystemExit, match="R-ctl has no all-labels pair"):
        P.cmd_train_ft(ns(c3r="ctl", real_fold=None))


@pytest.mark.parametrize("kw", [{"masked": False}, {"c3": True}, {"h4": "full"}, {"real_frac": 0.5}])
def test_c3r_trains_c3s_recipe_only(base, kw):
    with pytest.raises(SystemExit, match="--c3r trains C3's recipe only"):
        P.cmd_train_ft(ns(real_fold=0, inner=True, **kw))


def _c2(tmp_path, monkeypatch, written=True):
    monkeypatch.setattr(C3, "N_C2", 2)
    recs = [{"set": "goat", "block": "goat", "key": f"goat/u{i}|pr12", "unit": f"goat/u{i}", "amp": "pr12"}
            for i in range(2)]
    (tmp_path / "c2").mkdir(exist_ok=True)
    (tmp_path / "c2" / "records.json").write_text(json.dumps({"records": recs}))
    if written:
        for r in recs:
            p = C2.out_path(r)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"label": {"a/b": "1"}, "searched_keys": []}))
    return recs


def _c2r(tmp_path, written=True):
    recs = [{"set": "cap1", "block": "cap1", "key": "cap/a#pr12|pr12", "unit": "cap/a#pr12", "amp": "pr12"}]
    (tmp_path / "c2r").mkdir(exist_ok=True)
    (tmp_path / "c2r" / "records.json").write_text(json.dumps({"records": recs}))
    if written:
        p = R.out_path(recs[0])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"label": {"a/b": "1"}}))


def test_train_ft_refuses_until_c2_is_complete(base, monkeypatch):
    _c2(base, monkeypatch, written=False)
    with pytest.raises(SystemExit, match="C2 is not complete"):
        P.cmd_train_ft(ns(real_fold=0, inner=True))


def test_train_ft_refuses_until_c2r_is_drawn_and_complete(base, monkeypatch):
    _c2(base, monkeypatch)
    with pytest.raises(SystemExit, match="C2r is not drawn"):
        P.cmd_train_ft(ns(real_fold=0, inner=True))
    _c2r(base, written=False)
    R3._CACHE.clear()
    with pytest.raises(SystemExit, match="C2r is not complete"):
        P.cmd_train_ft(ns(real_fold=0, inner=True))


def test_train_ft_refuses_until_c3s_decision_exists(base, monkeypatch):
    _c2(base, monkeypatch)
    _c2r(base)
    R3._CACHE.clear()
    with pytest.raises(SystemExit, match="C3's adoption decision is not made"):
        P.cmd_train_ft(ns(real_fold=0, inner=True))


# --- the names ---------------------------------------------------------------------------------------------------------

def test_the_run_names_on_c3s_recipe_and_on_ftms_fallback():
    cap = 300
    for (arm, recipe), b in R3.BASE.items():
        assert P.ft_name(0, True, P.FT_LR, cap, b) == f"{b}-k0-inner-cap300"
        assert P.ft_name(3, False, P.FT_LR, cap, b) == f"{b}-k3"
        assert P.ft_name(None, False, P.FT_LR, cap, b) == b
    assert R3.base_of("all", {"recipe": "c3"}) == "C3r-all" and R3.base_of("ctl", {"recipe": "c3"}) == "C3r-ctl"
    assert R3.base_of("all", {"recipe": "ftm"}) == "C3r-allK" and R3.base_of("ctl", {"recipe": "ftm"}) == "C3r-ctlK"
    assert len(set(R3.BASE.values()) | {C3.C3_BASE, P.FTM_BASE}) == 6       # never C3's or FTm's own names


# --- the wiring, up to the first step (--dry-run) -------------------------------------------------------------------------

def _state(recipe="c3"):
    """A stub rotation: four folds, one unit of each set in each fold (the captures with creators), one record each."""
    S = T2.full_start("pr12")
    label = LO.sdict(S)
    ents, src, rec_set, units = [], {}, {}, {s: {} for s in R3.SETS}
    recs = {"bks": [], "goat": []}
    for s in R3.SETS:
        for f in range(4):
            u = f"{s}/u{f}"
            ents.append(dict(R3.entry(s, u, f, f"{s}-di{f}", creator=f"cr{f}" if s in ("cap1", "n12") else None,
                                      band=f"band{f}" if s == "panel" else None), n=1, player=None))
            src[(u, "pr12")] = {"kind": "c2", "label": label, "searched": [], "set": s, "block": s, "key": f"{u}|pr12"}
            rec_set[(u, "pr12")] = s
            units[s][u] = {"unit": u, "section": f"{u}@0", "band": f"band{f}", "cls": "clean"}
            if s in recs:
                recs[s].append({"unit": u, "amp": "pr12"})
    return {"entries": ents, "sources": src, "rec_set": rec_set, "units": units, "records": recs, "recipe": recipe,
            "sha256": "stub-state", "c2": {"sha256": "c2"}, "c2r": {"sha256": "c2r"}, "answer_tag": "C3-ftm"}, S


def _wire(base, monkeypatch, st, S):
    np = pytest.importorskip("numpy")
    from learn import full_space as FS

    R3._CACHE.clear()
    monkeypatch.setattr(R3, "state", lambda partial=False: st)
    monkeypatch.setattr(P, "recipe_inputs", lambda root=None, pin=None: ("croot", {}, {}, {}, {"doubles": "none"}))
    monkeypatch.setattr(P, "ft_start_state", lambda seed, pre=None: ({}, {"train_ids": [0, 1, 2],
                                                                          "model_sha256": {"best": "w"}}))
    monkeypatch.setattr(P, "plugin_rows", lambda kept, sp, pa, rows_of: (
        [0, 1, 2], [9], "ns", [{"i": 0}, {"i": 1}, {"i": 2}, {"i": 9}]))
    monkeypatch.setattr(P, "rung_path", lambda croot, rung, doubled=frozenset(), root=None: (lambda i: None))
    monkeypatch.setattr(P, "A_menu_S", lambda: {"pr12": {"clean": (0, S)}})

    class Data:
        def __init__(self, rows, path_of, plugin_ids, real_train_ids, share=1.0):
            n = len(rows)
            self.Y = [None, np.ones((n, len(FS.CONT)), np.float32), None, np.ones((n, len(FS.SW)), np.float32), None,
                      np.ones((n, len(FS.CAT)), np.float32), np.zeros(n)]
            self.inputs_sha256, self.target_lufs = "stub-inputs", {}
            Data.last = self
    monkeypatch.setattr(P, "DfixData", Data)
    od = base / "runs"
    od.mkdir(exist_ok=True)
    for sd in P.SEEDS:
        (od / f"{P.FT_PRETRAIN}-{sd}.json").write_text(json.dumps({"model_sha256": {"best": "w"}}))
    return Data


def _inner_runs(base, b, sha="stub-state"):
    for q in range(4):
        for sd in P.SEEDS:
            (base / "runs" / f"{P.ft_name(q, True, P.FT_LR, 300, b)}-{sd}.json").write_text(json.dumps(
                {"lr": P.FT_LR, "cap": 300, "real_fold": q, "seed": sd, "init": {"sha256": "w"},
                 "c3r": {"c3r_sha256": sha},
                 "log": [{"epoch": e, "real_val_smoothed": [3.0, 2.0, 1.0, 1.5][e]} for e in range(4)]}))


def test_an_inner_run_holds_fold_j_and_trains_on_the_other_two_folds(base, monkeypatch):
    st, S = _state()
    data = _wire(base, monkeypatch, st, S)
    d = P.cmd_train_ft(ns(real_fold=0, inner=True))
    assert d["name"] == "C3r-all-k0-inner-cap300" and d["epochs"] == 300 and d["phase"] == "phase_c3r"
    assert d["held_units"] == sorted(f"{s}/u1" for s in R3.SETS)
    assert sorted(d["train_units"]) == sorted(f"{s}/u{f}" for s in R3.SETS for f in (2, 3))
    assert d["info"]["train_rows"] == {"real_amps": 300, "captures": 300}           # each source cycled to 300
    assert d["train_real"] == 600 and d["held_real"] == 5
    amp = data.last.Y[6]            # layout: plugin training 3, real training 600, plugin held 1, real held 5
    assert (amp[:3] == 0).all() and (amp[3:603] == -100).all() and amp[603] == 0 and (amp[604:] == -100).all()
    assert not (base / "runs" / "C3r-all-k0-inner-cap300-20261042.json").exists()  # a dry run writes nothing


def test_r_ctl_trains_on_bks_and_goat_only_and_holds_r_alls_units(base, monkeypatch):
    st, S = _state()
    _wire(base, monkeypatch, st, S)
    a = P.cmd_train_ft(ns(real_fold=2, inner=True, c3r="all"))
    c = P.cmd_train_ft(ns(real_fold=2, inner=True, c3r="ctl"))
    assert c["name"] == "C3r-ctl-k2-inner-cap300" and c["held_units"] == a["held_units"]
    assert {u.split("/")[0] for u in c["train_units"]} == {"bks", "goat"}
    assert set(c["train_units"]) < set(a["train_units"])


def test_ft_k_takes_its_own_inner_runs_e_and_holds_fold_k(base, monkeypatch):
    st, S = _state()
    _wire(base, monkeypatch, st, S)
    with pytest.raises(SystemExit, match="the 8 inner runs are not all done"):
        P.cmd_train_ft(ns(real_fold=1))
    _inner_runs(base, "C3r-all")
    d = P.cmd_train_ft(ns(real_fold=1))
    assert d["name"] == "C3r-all-k1" and d["epochs"] == 3                          # argmin at epoch 2, + 1
    assert d["held_units"] == sorted(f"{s}/u1" for s in R3.SETS)
    assert sorted(d["train_units"]) == sorted(f"{s}/u{f}" for s in R3.SETS for f in (0, 2, 3))


def test_ft_k_refuses_inner_runs_made_on_another_state(base, monkeypatch):
    st, S = _state()
    _wire(base, monkeypatch, st, S)
    _inner_runs(base, "C3r-all", sha="another")
    with pytest.raises(SystemExit, match="another C2, C2r or C3 state"):
        P.cmd_train_ft(ns(real_fold=0))


def test_the_all_labels_pair_trains_every_row_and_ftms_fallback_has_its_own_names(base, monkeypatch):
    st, S = _state(recipe="ftm")
    _wire(base, monkeypatch, st, S)
    _inner_runs(base, "C3r-allK")
    d = P.cmd_train_ft(ns(real_fold=None))
    assert d["name"] == "C3r-allK" and d["held_real"] == 0
    assert len(d["train_units"]) == 20 and d["info"]["train_records"] == {"real_amps": 8, "captures": 12}


def test_a_leaking_row_stops_the_run(base, monkeypatch):
    st, S = _state()
    st["entries"][1]["ids"] = set(st["entries"][1]["ids"]) | {("di", "goat-di0")}  # bks/u1 shares goat/u0's DI
    _wire(base, monkeypatch, st, S)
    d = P.cmd_train_ft(ns(real_fold=3, inner=True))                                  # folds 3 and 0 out
    assert "bks/u1" not in d["train_units"]                                           # dropped by the rule
    real_split = R3.split
    monkeypatch.setattr(R3, "split", lambda ents, k, inner, arm: (real_split(ents, None, False, arm)[0],
                                                                  *real_split(ents, k, inner, arm)[1:]))
    with pytest.raises(SystemExit, match="problems"):
        P.cmd_train_ft(ns(real_fold=3, inner=True))
