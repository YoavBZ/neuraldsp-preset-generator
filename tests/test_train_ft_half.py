"""The learning-curve diagnostic through `pipeline_fix train-ft --c3r all --c3r-half` (`learn/half_data.py`): each arm's
names, W states, half of the rows, E source and write refusals, up to the first step (`--dry-run`), on C3r's stub data.
Needs torch (the demucs venv); the light CI runner skips it."""
import json

import pytest

pytest.importorskip("numpy")
pytest.importorskip("torch")

from learn import half_data as H  # noqa: E402
from learn import pipeline_fix as P  # noqa: E402
from learn import stem_finetune as S  # noqa: E402
from tests.test_train_ft_c3r import _state, _wire, base, ns  # noqa: E402,F401

A1, A2 = list(H.ARMS["a"]["seeds"])
B1, B2 = list(H.ARMS["b"]["seeds"])
SEL = {"sha256": "stub-selection",
       "halves": {"A": {"units": [f"{s}/u{f}" for s in ("bks", "goat", "cap1", "n12", "panel") for f in (0, 2)]},
                  "B": {"units": [f"{s}/u{f}" for s in ("bks", "goat", "cap1", "n12", "panel") for f in (1, 3)]}}}


def _inners(base, b, seeds, arm, folds=range(4), sel="stub-selection"):
    for q in folds:
        for sd in seeds:
            (base / "runs" / f"{P.ft_name(q, True, P.FT_LR, 300, b)}-{sd}.json").write_text(json.dumps(
                {"lr": P.FT_LR, "cap": 300, "real_fold": q, "seed": sd, "init": {"sha256": "w"},
                 "c3r": {"c3r_sha256": "stub-state"},
                 **({"half": {"arm": arm, "selection_sha256": sel}} if arm else {}),
                 "log": [{"epoch": e, "real_val_smoothed": [3.0, 2.0, 1.0, 1.5, 2.0][e]} for e in range(5)]}))


@pytest.fixture
def wired(base, monkeypatch):
    st, S_ = _state()
    _wire(base, monkeypatch, st, S_)
    starts = []
    monkeypatch.setattr(S, "stage0_ok", lambda: {"cell": {"code": "S0-ok"}})
    monkeypatch.setattr(H, "load_selection", lambda st=None: SEL)
    monkeypatch.setattr(P, "ft_start_state", lambda seed, pre=None: (starts.append(seed) or {}, {
        "train_ids": [0, 1, 2], "model_sha256": {"best": "w"}}))
    return base, starts


def test_an_arm_a_inner_run_trains_its_half_from_r_alls_w_state_and_seed(wired):
    base, starts = wired
    d = P.cmd_train_ft(ns(real_fold=0, inner=True, c3r_half="a", seed=A1))
    full = P.cmd_train_ft(ns(real_fold=0, inner=True, seed=A1))                     # R-all's own
    assert d["name"] == "C3r-half-a-k0-inner-cap300" and d["seed"] == A1 and d["w_seed"] == A1
    assert d["half"] == "a" and d["init_run"] == f"{P.FT_PRETRAIN}-{A1}"
    assert set(d["train_units"]) == set(full["train_units"]) & set(SEL["halves"]["A"]["units"])
    assert set(d["train_units"]) < set(full["train_units"])
    assert d["held_units"] == full["held_units"]                                    # validation unchanged
    assert d["train_real"] == full["train_real"]                                    # cycled to as many rows


def test_arm_b_trains_the_complement_from_r_reps_w_states(wired):
    base, starts = wired
    d = P.cmd_train_ft(ns(real_fold=1, inner=True, c3r_half="b", seed=B2))
    full = P.cmd_train_ft(ns(real_fold=1, inner=True, seed=P.SEEDS[1]))
    assert d["name"] == "C3r-half-b-k1-inner-cap300" and d["w_seed"] == H.ARMS["b"]["seeds"][B2]
    assert set(d["train_units"]) == set(full["train_units"]) & set(SEL["halves"]["B"]["units"])
    a = P.cmd_train_ft(ns(real_fold=1, inner=True, c3r_half="a", seed=A2))
    assert not set(a["train_units"]) & set(d["train_units"])


def test_an_arms_ft_k_reads_its_own_inner_runs_only(wired):
    base, _ = wired
    _inners(base, "C3r-all", P.SEEDS, None)
    with pytest.raises(SystemExit, match="the 8 inner runs are not all done"):
        P.cmd_train_ft(ns(real_fold=1, c3r_half="a", seed=A2))
    _inners(base, "C3r-half-a", list(H.ARMS["a"]["seeds"]), "a")
    d = P.cmd_train_ft(ns(real_fold=1, c3r_half="a", seed=A2))
    assert d["name"] == "C3r-half-a-k1" and d["epochs"] == 3


def test_an_inner_run_of_another_arm_or_selection_is_refused(wired):
    base, _ = wired
    _inners(base, "C3r-half-a", list(H.ARMS["a"]["seeds"]), "b")
    with pytest.raises(SystemExit, match="another half arm"):
        P.cmd_train_ft(ns(real_fold=1, c3r_half="a", seed=A2))
    _inners(base, "C3r-half-a", list(H.ARMS["a"]["seeds"]), "a", sel="other")
    with pytest.raises(SystemExit, match="another selection"):
        P.cmd_train_ft(ns(real_fold=1, c3r_half="a", seed=A2))


@pytest.mark.parametrize("kw,msg", [({"seed": B1}, "--seed in"), ({"real_fold": None}, "fold runs only"),
                                    ({"c3r": "ctl"}, "--c3r all"), ({"c3r_rep": "rep"}, "separate"),
                                    ({"ft_cap": 100}, "rate and cap")])
def test_half_refusals(wired, kw, msg):
    a = dict(real_fold=0, inner=True, c3r_half="a", seed=A1)
    a.update(kw)
    with pytest.raises(SystemExit, match=msg):
        P.cmd_train_ft(ns(**a))


def test_no_protected_file_can_be_written(wired):
    base, _ = wired
    od = base / "runs"
    (od / f"C3r-half-a-k2-{A1}-final.pt").write_bytes(b"x")
    _inners(base, "C3r-half-a", list(H.ARMS["a"]["seeds"]), "a")
    with pytest.raises(SystemExit, match="already exist"):
        P.cmd_train_ft(ns(real_fold=2, c3r_half="a", seed=A1))
    before = {p.name: p.read_bytes() for p in od.iterdir()}
    for arm in H.ARMS:
        for k in range(4):
            for sd in H.ARMS[arm]["seeds"]:
                if (arm, k, sd) == ("a", 2, A1):
                    continue
                d = P.cmd_train_ft(ns(real_fold=k, inner=True, c3r_half=arm, seed=sd))
                if d is not None:
                    assert d["name"].startswith(H.ARMS[arm]["base"] + "-")
    assert before == {p.name: p.read_bytes() for p in od.iterdir()}


def test_a_half_run_refuses_without_its_ledger_phase(wired, monkeypatch):
    import copy

    real = P.ledger_entry()
    assert H.PHASE_HALF in real                                                     # declared in this PR
    entry = copy.deepcopy(real)
    del entry[H.PHASE_HALF]
    monkeypatch.setattr(P, "require", REQUIRE)
    monkeypatch.setattr(P, "ledger_entry", lambda: entry)
    with pytest.raises(SystemExit, match="no phase_s6_half: declare it before running"):
        P.cmd_train_ft(ns(real_fold=0, inner=True, c3r_half="a", seed=A1))


REQUIRE = P.require
