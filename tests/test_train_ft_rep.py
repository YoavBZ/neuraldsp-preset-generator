"""Step 6's stage N through `pipeline_fix train-ft --c3r all --c3r-rep` (`learn/stem_finetune.py`): R-rep's and the
replay's names, W states, E sources and write refusals, up to the first step (`--dry-run`), on C3r's stub data. Needs
torch (the demucs venv); the light CI runner skips it."""
import json

import pytest

pytest.importorskip("numpy")
pytest.importorskip("torch")

from learn import pipeline_fix as P  # noqa: E402
from learn import stem_finetune as S  # noqa: E402
from tests.test_train_ft_c3r import _state, _wire, base, ns  # noqa: E402,F401

REP1, REP2 = list(S.REP_SEEDS)


def _inners(base, b, seeds, kind, folds=range(4), sha="stub-state"):
    for q in folds:
        for sd in seeds:
            (base / "runs" / f"{P.ft_name(q, True, P.FT_LR, 300, b)}-{sd}.json").write_text(json.dumps(
                {"lr": P.FT_LR, "cap": 300, "real_fold": q, "seed": sd, "init": {"sha256": "w"},
                 "c3r": {"c3r_sha256": sha}, **({"rep": {"kind": kind}} if kind else {}),
                 "log": [{"epoch": e, "real_val_smoothed": [3.0, 2.0, 1.0, 1.5, 2.0][e]} for e in range(5)]}))


@pytest.fixture
def wired(base, monkeypatch):
    st, S_ = _state()
    _wire(base, monkeypatch, st, S_)
    starts = []
    monkeypatch.setattr(S, "stage0_ok", lambda: {"cell": {"code": "S0-ok"}})
    monkeypatch.setattr(P, "ft_start_state", lambda seed, pre=None: (starts.append(seed) or {}, {
        "train_ids": [0, 1, 2], "model_sha256": {"best": "w"}}))
    return base, starts


def test_an_r_rep_inner_run_has_its_own_name_and_its_seeds_w_state(wired):
    base, starts = wired
    d = P.cmd_train_ft(ns(real_fold=0, inner=True, c3r_rep="rep", seed=REP1))
    assert d["name"] == "C3r-rep-k0-inner-cap300" and d["seed"] == REP1 and d["epochs"] == 300
    assert d["w_seed"] == S.REP_SEEDS[REP1] and starts == [S.REP_SEEDS[REP1]]
    assert d["init_run"] == f"{P.FT_PRETRAIN}-{S.REP_SEEDS[REP1]}" and d["rep"] == "rep"
    a = P.cmd_train_ft(ns(real_fold=0, inner=True, seed=P.SEEDS[0]))                # R-all's own: the same rows
    assert (d["train_units"], d["held_units"], d["train_real"], d["held_real"]) == \
        (a["train_units"], a["held_units"], a["train_real"], a["held_real"])


def test_r_rep_ft_k_reads_its_own_inner_runs_only(wired):
    base, _ = wired
    _inners(base, "C3r-all", P.SEEDS, None)                                        # R-all's: never R-rep's E
    with pytest.raises(SystemExit, match="the 8 inner runs are not all done"):
        P.cmd_train_ft(ns(real_fold=1, c3r_rep="rep", seed=REP2))
    _inners(base, "C3r-rep", list(S.REP_SEEDS), "rep")
    d = P.cmd_train_ft(ns(real_fold=1, c3r_rep="rep", seed=REP2))
    assert d["name"] == "C3r-rep-k1" and d["epochs"] == 3 and d["w_seed"] == S.REP_SEEDS[REP2]


def test_an_inner_run_of_another_kind_is_refused(wired):
    base, _ = wired
    _inners(base, "C3r-rep", list(S.REP_SEEDS), None)                              # no `rep` record: refused
    with pytest.raises(SystemExit, match="another kind"):
        P.cmd_train_ft(ns(real_fold=1, c3r_rep="rep", seed=REP2))


def test_the_replay_reads_its_one_inner_run(wired):
    base, starts = wired
    with pytest.raises(SystemExit, match="the 1 inner runs are not all done"):
        P.cmd_train_ft(ns(real_fold=3, c3r_rep="replay", seed=S.REPLAY[1]))
    d = P.cmd_train_ft(ns(real_fold=3, inner=True, c3r_rep="replay", seed=S.REPLAY[1]))
    assert d["name"] == "C3r-replay-k3-inner-cap300" and d["w_seed"] == S.REPLAY[1]
    _inners(base, "C3r-replay", [S.REPLAY[1]], "replay", folds=[3])
    d = P.cmd_train_ft(ns(real_fold=3, c3r_rep="replay", seed=S.REPLAY[1]))
    assert d["name"] == "C3r-replay-k3" and d["epochs"] == 3


@pytest.mark.parametrize("kw,msg", [({"seed": P.SEEDS[0]}, "R-all's seeds are R-all's"),
                                    ({"real_fold": None}, "fold runs only"),
                                    ({"c3r": "ctl"}, "--c3r all"),
                                    ({"c3r_rep": "replay", "seed": P.SEEDS[0], "real_fold": 3}, "fold 3")])
def test_stage_n_refusals(wired, kw, msg):
    a = dict(real_fold=0, inner=True, c3r_rep="rep", seed=REP1)
    a.update(kw)
    with pytest.raises(SystemExit, match=msg):
        P.cmd_train_ft(ns(**a))


def test_no_r_all_file_can_be_written(wired):
    base, _ = wired
    od = base / "runs"
    (od / f"C3r-rep-k2-{REP1}-final.pt").write_bytes(b"x")                          # a stray checkpoint stops the run
    _inners(base, "C3r-rep", list(S.REP_SEEDS), "rep")
    with pytest.raises(SystemExit, match="already exist"):
        P.cmd_train_ft(ns(real_fold=2, c3r_rep="rep", seed=REP1))
    before = {p.name: p.read_bytes() for p in od.iterdir()}
    for k in range(4):                                                              # every rep and replay run, dry
        for sd in S.REP_SEEDS:
            for inner in (True, False):
                if (k, sd, inner) == (2, REP1, False):
                    continue
                d = P.cmd_train_ft(ns(real_fold=k, inner=inner, c3r_rep="rep", seed=sd))
                if inner:                                                           # its record exists: nothing to do
                    assert d is None
                else:
                    assert d["name"].startswith("C3r-rep-") and not d["name"].startswith("C3r-all")
    after = {p.name: p.read_bytes() for p in od.iterdir()}
    assert before == after                                                          # nothing written or changed


def test_stage_n_refuses_without_stage_0s_s0_ok(wired, monkeypatch, tmp_path):
    monkeypatch.undo()                                                              # the real stage0_ok, on stub data
    st, S_ = _state()
    _wire(tmp_path, monkeypatch, st, S_)
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda k: {})
    with pytest.raises(SystemExit, match="stage 0 has not run"):
        P.cmd_train_ft(ns(real_fold=0, inner=True, c3r_rep="rep", seed=REP1))
    (tmp_path / "step6").mkdir()
    (tmp_path / "step6" / "stage0.json").write_text(json.dumps({"cell": {"code": "S0-fail"}}))
    with pytest.raises(SystemExit, match="did not read S0-ok"):
        P.cmd_train_ft(ns(real_fold=0, inner=True, c3r_rep="rep", seed=REP1))
    (tmp_path / "step6" / "stage0.json").write_text(json.dumps({"cell": {"code": "S0-ok"}}))
    assert P.cmd_train_ft(ns(real_fold=0, inner=True, c3r_rep="rep", seed=REP1))["name"] == "C3r-rep-k0-inner-cap300"


@pytest.mark.parametrize("kw", [{"ft_cap": None}, {"ft_cap": 100}, {"ft_lr": P.FT_FALLBACK_LR}])
def test_stage_n_pins_r_alls_rate_and_cap(wired, kw):
    with pytest.raises(SystemExit, match="rate and cap"):
        P.cmd_train_ft(ns(real_fold=0, inner=True, c3r_rep="rep", seed=REP1, **kw))


def test_stage_n_refuses_without_its_ledger_phase(wired, monkeypatch):
    import copy

    real = P.ledger_entry()
    assert S.PHASE_NOISE in real                                                    # declared in this PR
    entry = copy.deepcopy(real)
    del entry[S.PHASE_NOISE]
    monkeypatch.setattr(P, "require", REQUIRE)                                      # the real `require`
    monkeypatch.setattr(P, "ledger_entry", lambda: entry)
    with pytest.raises(SystemExit, match="no phase_s6_noise: declare it before running"):
        P.cmd_train_ft(ns(real_fold=0, inner=True, c3r_rep="rep", seed=REP1))


REQUIRE = P.require
