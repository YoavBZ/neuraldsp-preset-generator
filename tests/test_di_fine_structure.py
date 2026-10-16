"""Experiment 4's rules, leak check, output folders and lag argument
(`learn/di_fine_structure.py`, `docs/di-fine-structure-plan.md`). No renders, no torch."""

import hashlib
import json
import math

import pytest

from learn import di_fine_structure as F


def _stored(rows):
    """rows: key -> (d_S, d_target, measure found, C′ found), half B."""
    return {k: {"S": {"A": 1.0, "B": s}, "target": {"A": 1.0, "B": t}, "measure_run": {"A": 1.0, "B": m},
                "rebuilt_run": {"A": 1.0, "B": c}} for k, (s, t, m, c) in rows.items()}


# Fold 3 as recorded: measure-DI mean shortfall ≈ −0.043, C′ 2 of 4 closed, mean ≈ +0.201.
F3 = {"p|pr12": (2.0, 1.0, 0.996, 1.083), "p|sw50r": (1.5, 1.0, 1.019, 1.306),
      "j|pr12": (1.8, 1.0, 0.986, 1.49), "j|sw50r": (2.0, 1.0, 0.842, 1.061)}


def test_fold3_figures_match_the_plan():
    st = _stored(F3)
    r = F.subset_rule(st, list(F3), {k: st[k]["rebuilt_run"]["B"] for k in F3})
    assert r["need_closed"] == 3
    assert r["go_shortfall"] == pytest.approx(-0.0129, abs=5e-4)
    assert r["stop_shortfall"] == pytest.approx(0.1709, abs=5e-4)
    assert r["cprime"]["closed"] == 2 and r["reading"] == "stop"


@pytest.mark.parametrize("found, reading", [
    ({"p|pr12": 1.0, "p|sw50r": 1.0, "j|pr12": 1.0, "j|sw50r": 2.0}, "go"),          # 3 of 4 closed
    ({"p|pr12": 0.6, "p|sw50r": 0.6, "j|pr12": 1.51, "j|sw50r": 1.51}, "go"),       # 2 closed; mean −0.049
    ({"p|pr12": 1.6, "p|sw50r": 1.6, "j|pr12": 1.6, "j|sw50r": 1.0}, "stop"),        # 1 closed; mean +0.35
    ({"p|pr12": 1.52, "p|sw50r": 1.52, "j|pr12": 0.8, "j|sw50r": 0.8}, "undecided"), # 2 closed; mean +0.098
    ({"p|pr12": math.inf, "p|sw50r": 1.0, "j|pr12": 1.0, "j|sw50r": 1.0}, "undecided (a refused or missing cell)"),
])
def test_fold3_rule_rows(found, reading):
    st = _stored(F3)
    assert F.subset_rule(st, list(F3), found)["reading"] == reading


def test_fold1_branch_needs_five_of_seven():
    rows = {f"c{i}|pr12": (2.0, 1.0, 1.0, 1.5) for i in range(7)}
    st = _stored(rows)
    r = F.subset_rule(st, list(rows), {k: (1.0 if i < 5 else 2.0) for i, k in enumerate(rows)})
    assert r["need_closed"] == 5 and r["reading"] == "go"
    r = F.subset_rule(st, list(rows), {k: (1.0 if i < 4 else 1.9) for i, k in enumerate(rows)})
    assert r["reading"] in ("stop", "undecided") and r["arm"]["closed"] == 4


def _reading(reading, closed, mean):
    return {"reading": reading, "arm": {"closed": closed, "mean_shortfall": mean}}


def test_choose_any_go_wins_by_cells_then_shortfall_then_cost():
    r = {"1a": _reading("go", 3, 0.0), "1b": _reading("go", 3, -0.01), "1c": _reading("stop", 1, 0.3)}
    assert F.choose(r)["winner"] == "1b"
    r = {"1c": _reading("go", 3, 0.0), "1a": _reading("go", 3, 0.0)}
    assert F.choose(r)["winner"] == "1a"


def test_choose_against_1z():
    z = _reading("go", 3, 0.0)
    r = {"1a": _reading("go", 3, -0.02), "1b": _reading("go", 4, 0.1)}
    out = F.choose(r, z)
    assert out["winner"] == "1b" and "fine-tuning" in out["note"]
    r = {"1a": _reading("go", 3, -0.02)}
    assert F.choose(r, z)["winner"] == "1z"
    r = {"1a": _reading("go", 3, -0.03)}
    assert F.choose(r, z)["winner"] == "1a"


def test_choose_branch_and_stop():
    out = F.choose({"1a": _reading("undecided", 2, 0.1), "1b": _reading("stop", 1, 0.3)})
    assert out["outcome"] == "fold-1 branch" and out["undecided"] == ["1a"]
    assert F.choose({"1a": _reading("stop", 1, 0.3)})["outcome"] == "stop"


def test_step4_uses_the_controls_own_rows():
    rows = {f"c{i}|pr12": (2.0, 1.0, 1.0, 1.9) for i in range(9)}
    rows.update({f"u{i}|pr12": (1.0, 1.05, 1.0, 1.0) for i in range(3)})
    st = _stored(rows)
    res = {k: {"rebuilt_run": {"A": 1.0, "B": (1.0 if i < 6 else 1.9)}} for i, k in enumerate(st)}
    out = F.step4(st, res)
    assert out["informative"] == 9 and out["rebuilt_closed"] == 6 and out["outcome"] == "passes"
    res = {k: {"rebuilt_run": {"A": 1.0, "B": (1.0 if i < 5 else 1.9)}} for i, k in enumerate(st)}
    assert F.step4(st, res)["outcome"] == "fails"
    with pytest.raises(SystemExit):
        F.step4(st, {})


def test_share_rule_keeps_or_moves_to_midpoint():
    means = {"L_C": 6.0, "mrstft": 1.0, "short": 1.5, "peak": 4.0, "gap": 50.0, "phase": 0.5}
    out = F.share_rule(means, {"short": 1.0, "peak": 0.1, "gap": 0.02})
    assert out["kept"] == {"short": True, "peak": True, "gap": False}
    assert out["weights"]["gap"] == pytest.approx(float(f"{0.065 * 6.0 / 50.0:.1g}"))
    ph = F.share_rule(means, {"phase": 1.0}, fixed={"short": 1.0})
    assert ph["shares"]["phase"] == pytest.approx(0.5 / 2.5) and ph["kept"]["phase"]


def test_capacity_needs_the_out_of_loss_checks():
    good = {"crest_1ms_err": 0.5, "crest_2.5ms_err": -0.4, "gap_db": 2.0, "crest_0.5ms_err": 0.8, "snr_db": 9.0}
    ref = {"snr_db": 5.0}
    assert F.capacity_verdict(good, ref)["pass"]
    assert not F.capacity_verdict({**good, "crest_0.5ms_err": 1.5}, ref)["pass"]
    assert not F.capacity_verdict({**good, "snr_db": 7.9}, ref)["pass"]
    q = F.capacity_verdict({**good, "gap_db": None, "quiet_db": 1.0}, ref)
    assert q["pass"] and q["gap_source"] == "quiet"


def _eval(ratio, hf=0.0, crest1=-3.0):
    return {"ratio": ratio, "fine": {"hf_3_8k_db": hf, "crest_1ms_err": crest1, "gap_db": 10.0}}


def test_screen_stops_on_breakage_only():
    c = _eval(0.519)
    assert F.screen_verdict(_eval(0.539, hf=2.0, crest1=-5.0), c, 0.13)["passes"]
    assert F.screen_verdict(_eval(0.5391), c, 0.13)["stops"]["val_ratio"]
    assert F.screen_verdict(_eval(0.5), c, 0.1125)["stops"]["check2"]
    assert F.screen_verdict(_eval(0.5, hf=2.01), c, 0.13)["stops"]["hf_3_8k"]
    dark = _eval(0.519, hf=-7.4)                         # amendment 1: closer to the true DI passes
    assert not F.screen_verdict(_eval(0.5, hf=-4.7), dark, 0.13)["stops"]["hf_3_8k"]
    assert F.screen_verdict(_eval(0.5, hf=2.01), dark, 0.13)["stops"]["hf_3_8k"]   # too bright vs the record
    assert not F.screen_verdict(_eval(0.5, hf=-9.5), dark, 0.13)["stops"]["hf_3_8k"]  # no darker-side stop


def test_parent_of_1c_and_render_cap():
    assert F.parent_of_1c(_eval(0.5, crest1=-3.0), _eval(0.5, crest1=-2.85)) == "1a"
    assert F.parent_of_1c(_eval(0.5, crest1=-3.0), _eval(0.5, crest1=-2.7)) == "1b"
    v = {a: {"passes": True} for a in ("1a", "1b", "1c", "1e")}
    ev = {"1c": _eval(0.5, crest1=-2.0), "1e": _eval(0.5, crest1=-1.0)}
    assert F.render_set(v, ev) == (["1a", "1b", "1e"], ["1c"])
    v["1a"]["passes"] = False
    assert F.render_set(v, ev)[0] == ["1b", "1e"]


def test_e1_and_swap_readings():
    keys = ["a", "b", "c", "d"]
    true = {k: 0.188 for k in keys}
    assert F.e1_opens({k: 0.15 for k in keys}, true, {k: 0.5 for k in keys}, keys)["opens"]
    assert not F.e1_opens({k: 0.13 for k in keys}, true, {k: 0.5 for k in keys}, keys)["opens"]
    assert not F.e1_opens({**{k: 0.2 for k in keys}, "a": -0.01}, true, {k: 0.5 for k in keys}, keys)["opens"]
    assert not F.e1_opens({**{k: 0.2 for k in keys}, "a": None}, true, {k: 0.5 for k in keys}, keys)["opens"]
    k9 = [str(i) for i in range(9)]
    assert F.swap_reorders({k: -0.1 for k in k9}, {k: 0.1 for k in k9[:6]}, k9)["1b_first"]
    assert not F.swap_reorders({k: 0.1 for k in k9[:4]}, {k: 0.1 for k in k9}, k9)["1b_first"]


# --- the leak check ----------------------------------------------------------------------------

def test_train_pool_and_leak(tmp_path):
    c = tmp_path / "cache"
    c.mkdir()
    (c / "meta.json").write_text(json.dumps([{"band": "A"}, {"band": "B"}, {"band": "P1"}]))
    crops = tmp_path / "crops"
    (crops / "part-c").mkdir(parents=True)
    (crops / "part-c" / "backing_instrumental.wav").write_bytes(b"")
    k3 = ({"A": 0, "B": 3, "C": 1, "D": 2}, {"part-c": "C", "part-d": "D"})
    pool = F.train_pool_bands(3, [c], k3=k3, crops=crops)
    assert pool == {"A", "P1", "C"}                        # B is fold 3's own; D has no backing
    F.assert_no_leak("B", 3, 3, pool)
    with pytest.raises(AssertionError):
        F.assert_no_leak("A", 3, 3, pool)
    with pytest.raises(AssertionError):
        F.assert_no_leak("B", 2, 3, pool)


# --- output folders, DONE, lag --------------------------------------------------------------------

def test_arm_folders_never_touch_the_stored_control(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "HOME", tmp_path)
    for a in F.ARMS:
        d = F.arm_dir(a)
        assert F.control_dir() not in d.parents and d != F.control_dir()
    with pytest.raises(ValueError):
        F.arm_dir("cprime")


def test_net_ready_needs_done_for_new_networks(tmp_path, monkeypatch):
    from learn import song_settings as SS

    monkeypatch.setattr(SS, "MODELS", tmp_path)
    legacy = tmp_path / "models-cprime/fold2.pt"
    fs = tmp_path / "models-fs-1a-f3/fold3.pt"
    for p in (legacy, fs):
        p.parent.mkdir(parents=True)
        p.write_bytes(b"x")
    assert SS.net_ready(legacy)
    assert not SS.net_ready(fs)
    (fs.parent / "DONE").write_text("")
    assert SS.net_ready(fs)
    assert SS.cprime_ready(2)


def test_rebuilt_distance_lag(monkeypatch):
    from analysis import aligned
    from learn import rebuilt_judge as RJ

    seen = []

    class D:
        distance, reason = 1.0, None

    monkeypatch.setattr(aligned, "aligned_distance", lambda *a, **k: (seen.append(k), D())[1])
    RJ.rebuilt_distance(None, None, None, start_s=1, end_s=5)
    RJ.rebuilt_distance(None, None, None, start_s=1, end_s=5, lag=0)
    assert [k["lag"] for k in seen] == [-52, 0]
    assert all(k["render_latency"] == 52 for k in seen)


def test_tally_counts_renders(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "HOME", tmp_path)
    r = F.root()
    (r / "step0/d0").mkdir(parents=True)
    (r / "step0/d0/x.json").write_text(json.dumps({"renders": 5}))
    (r / "control/1a").mkdir(parents=True)
    (r / "control/1a/c-pr12-result.json").write_text(json.dumps({"renders": 153}))
    (r / "control/1a/rebuild-log.json").write_text(json.dumps({"c|pr12": {}}))
    t = F.tally()
    assert t["d0"] == 5 and t["control"] == 153 and t["total"] == 158


def test_control_search_writes_only_to_the_arm_folder(tmp_path, monkeypatch):
    """A full pass of the runner with the renderer and judge faked: the stored control's files
    are byte-identical afterwards, and the result lands in the arm's folder."""
    import numpy as np

    from learn import knob_ceiling as K
    from learn import rank_margin as RM
    from learn import rebuilt_judge as RJ
    from learn import song_settings as SS

    monkeypatch.setattr(F, "HOME", tmp_path)
    ctrl = F.control_dir()
    ctrl.mkdir(parents=True)
    tag, key = "s-pr12", "s|pr12"
    np.save(ctrl / f"{tag}-fake.npy", np.zeros(480000))
    (ctrl / f"{tag}-target.json").write_text(json.dumps({"m/k": "1"}))
    (ctrl / f"{tag}-result.json").write_text(json.dumps(_stored({key: (2.0, 1.0, 1.0, 1.5)})[key]))
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ctrl.iterdir()}
    d = F.arm_dir("1a")
    d.mkdir(parents=True)
    np.save(d / f"{tag}-rebuilt.npy", np.zeros(480000))
    (d / "rebuild-log.json").write_text(json.dumps({key: {"lag_ok": True, "network": "n.pt"}}))

    class R:
        count = 0

        def menu(self):
            return {"pr12": {"start": ("sel", {("m", "k"): "0"})}}

        def render(self, di, sel, x):
            R.count += 1
            return np.zeros(len(di))

        def close(self):
            pass

    monkeypatch.setattr(F, "cells", lambda: [("s", "pr12")])
    monkeypatch.setattr(K, "Renderer", lambda: R())
    monkeypatch.setattr(K, "parts", lambda: {"s": {"band": "B", "gain_class": "clean"}})
    monkeypatch.setattr(K, "START", {"clean": {"pr12": "start"}})
    monkeypatch.setattr(K, "measure_di", lambda part: np.zeros(480000))
    monkeypatch.setattr(K, "space", lambda amp, S: [])
    monkeypatch.setattr(K, "judge", lambda ref, y, di, lag: {"A": 1.0, "B": 1.2})
    monkeypatch.setattr(SS, "folds", lambda: {"B": 3})

    def search(dims, x0, f, budget, seed):
        for _ in range(3):
            f(x0)
        return x0, 1.0, None, None

    monkeypatch.setattr(K, "knob_search", search)

    class Dist:
        distance = 1.0

    monkeypatch.setattr(RJ, "rebuilt_distance", lambda *a, **k: (Dist(), False))
    monkeypatch.setattr(RM, "distance", lambda fake, y, mask, lag, w: (1.0, False, None))
    F.control_search("1a", {3})
    res = json.loads((d / f"{tag}-result.json").read_text())
    assert res["rebuilt_run"]["gap_closed_B"] == pytest.approx(0.8) and res["lag"] == 0
    assert res["renders"] == 6 and res["measure_run"]["B"] == 1.0
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ctrl.iterdir()}
    assert before == after


def test_frame_split_accepts_stereo_renders():
    import numpy as np

    from learn import di_fine_structure as F

    rng = np.random.default_rng(0)
    fake = rng.standard_normal(48000) * 0.1
    y = np.stack([fake] * 2, axis=1)                    # renders and the fake share timing
    mono = F.frame_split(fake, y.mean(axis=1), fake)
    assert F.frame_split(fake, y, fake) == mono
