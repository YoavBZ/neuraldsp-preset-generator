"""L1a's rules (`learn/capture_units.py`, `learn/capture_labels.py`, `learn/nam_load.py`): pure parts."""
import json

import pytest

from learn import capture_labels as L
from learn import capture_units as U
from learn import nam_load as N
from learn import pipeline_fix as P


def players():
    return {"player1": [f"a{j}" for j in range(40)], "player2": [f"b{j}" for j in range(30)],
            "player4": [f"c{j}" for j in range(4)]}


def test_level_rule_reference_none_and_the_hold():
    assert U.level_gain_db(12.0, 0.1) == (-3.0, False)
    assert U.level_gain_db(None, 0.5) == (0.0, False)
    gain, held = U.level_gain_db(-9.0, 0.5)
    assert held and gain == pytest.approx(6.0206, abs=1e-3)     # 18 dB wanted, 6 dB to the top of the trained range


def test_walk_is_seeded_keeps_the_di_cap_and_never_repeats_a_di():
    caps = [f"cap{j}" for j in range(50)]
    cls = lambda c, it: "crunch" if (int(c[3:]) + len(it) + ord(it[-1])) % 3 == 0 else "clean"
    taken, tried = U.walk(caps, players(), cls, 7)
    assert (taken, tried) == U.walk(caps, players(), cls, 7)
    use = {}
    for c, amps in taken.items():
        assert len(set(amps.values())) == len(amps)
        for it in amps.values():
            use[it] = use.get(it, 0) + 1
    assert max(use.values()) <= U.DI_CAP
    assert sum(v for k, v in use.items() if k.startswith("c")) <= 12     # player4's 4 items
    assert all(len(set(v)) == len(v) <= U.TRIES for v in tried.values())


def test_walk_prefers_crunch_then_clean_and_plays_nothing_else():
    def cls(c, it):
        return {"all-heavy": "high-gain", "all-clean": "clean"}.get(c) or ("crunch" if it in ("a1", "b1") else "clean")
    taken, _ = U.walk(["all-heavy", "all-clean", "mixed"], players(), cls, 3)
    assert taken["all-heavy"] == {}
    assert len(taken["all-clean"]) == 3
    assert {"crunch" if v in ("a1", "b1") else "clean" for v in taken["mixed"].values()} >= {"clean"}


def test_walk_seeds_amp_order_and_first_player_per_capture():
    caps = [f"cap{j}" for j in range(40)]
    taken, _ = U.walk(caps, players(), lambda c, it: "clean", 11)
    firsts = {}
    for amps in taken.values():
        for amp, it in amps.items():
            firsts.setdefault(amp, set()).add(it[0])
    assert all(len(v) >= 2 for v in firsts.values())              # no amp stuck on one player


def test_folds_keep_a_creator_together_and_balance():
    units = [{"creator": f"c{j % 7}"} for j in range(70)]
    fold = L.folds_by_creator(units)
    assert set(fold) == {f"c{j}" for j in range(7)} and set(fold.values()) <= set(range(L.FOLDS))
    assert L.folds_by_creator(units) == fold


def units(n=8):
    out = []
    for a in P.AMPS3:
        for c in ("clean", "crunch"):
            for j in range(n):
                out.append({"unit": f"cap/{a}{c}{j}#{a}", "amp": a, "cls": c, "held_half": "AB"[j % 2], "pack": f"p{a}{c}{j}",
                            "creator": f"k{len(out) % 9}", "capture": f"{a}{c}{j}", "nonlinear_db": float(j)})
    return out


def test_card_units_takes_each_captures_most_driven_unit():
    us = [{"unit": "cap/x#a", "capture": "x", "nonlinear_db": -3.0}, {"unit": "cap/x#b", "capture": "x", "nonlinear_db": 1.0},
          {"unit": "cap/y#a", "capture": "y", "nonlinear_db": -9.0}]
    assert [u["unit"] for u in L.card_units(us)] == ["cap/x#b", "cap/y#a"]


def test_passed_needs_every_verdict_and_drops_capture_or_unit():
    us = [{"unit": "cap/x#a", "capture": "x"}, {"unit": "cap/x#b", "capture": "x"}, {"unit": "cap/y#a", "capture": "y"}]
    ok, miss = L.passed(us, {"x": {"verdict": "amp"}, "y": {"verdict": "odd"}}, ["cap/x#b"], {"cap/x#b": {"verdict": "heavy"}})
    assert ok == {"cap/x#a"} and miss == []
    ok, miss = L.passed(us, {"x": {"verdict": "amp"}}, ["cap/x#b"], {})
    assert set(miss) == {"y", "cap/x#b"}
    ok, _ = L.passed(us, {"x": {"verdict": "unsure"}, "y": {"verdict": "amp"}}, [], {})
    assert ok == {"cap/y#a"}


def test_pick_items_crosses_amp_and_class_and_draws_placebos_blind():
    import inspect
    us = units()
    by = {u["unit"]: u for u in us}
    active = {u["unit"]: {"A": 1.0, "B": 1.0} for u in us}
    items = L.pick_items(us, active)
    assert items == L.pick_items(us, active) and len(items) == 12
    cells = {}
    for it in items:
        u = by[it["unit"]]
        cells.setdefault((u["amp"], u["cls"]), []).append(u["held_half"])
        for p in it["placebos"]:
            v = by[p]
            assert (v["amp"], v["cls"]) == (u["amp"], u["cls"]) and v["creator"] != u["creator"]
    assert all(sorted(v) == ["A", "B"] for v in cells.values()) and len(cells) == 6
    packs = [by[it["unit"]]["pack"] for it in items]
    assert len(set(packs)) == 12
    held = [it["unit"] for it in items] + [p for it in items for p in it["placebos"]]
    assert len(set(held)) == len(held)                            # a placebo is no item and serves one part
    assert list(inspect.signature(L.pick_items).parameters)[:2] == ["units", "active"]   # no search record comes in


def test_pick_items_refuses_when_every_held_half_is_quiet():
    us = units()
    active = {u["unit"]: {"A": 0.5, "B": 0.5} for u in us}
    with pytest.raises(SystemExit):
        L.pick_items(us, active, seed=1)


def test_search_order_puts_the_items_first_and_stages_cut_it():
    us = [f"u{j:03d}" for j in range(120)]
    first = ["u050", "u010"]
    order = L.search_order(us, first)
    assert order[:2] == sorted(first) and sorted(order) == us and order == L.search_order(us, first)
    assert order[2:] != sorted(order[2:])
    assert L.stage_set(order, 2, "first") == order[:2]
    assert len(L.stage_set(order, 2, "third")) == 40 and L.stage_set(order, 2, "all") == order
    with pytest.raises(SystemExit):
        L.stage_set(order, 2, "rest")


def test_records_stay_apart_from_bks_and_goat():
    assert L.CAPTURE_DIR not in (P.GOAT_DIR, P.REAL_DIR, P.PANEL_DIR, P.VREAL_DIR)
    assert all(not u.startswith(("goat/", "real/")) for u in ("cap/x#pr12",))


def test_a1_translator_and_container():
    a1 = {"architecture": "WaveNet", "config": {"layers": [{"head_size": 8, "head_bias": False, "gated": False,
                                                            "activation": "Tanh", "dilations": [1, 2]}]}}
    d = N.modern(a1)["config"]["layers"][0]
    assert d["head"] == {"out_channels": 8, "kernel_size": 1, "bias": False} and d["activation"] == ["Tanh", "Tanh"]
    assert "head_size" in a1["config"]["layers"][0]                    # the input is not touched
    with pytest.raises(ValueError):
        N.modern({"architecture": "WaveNet", "config": {"layers": [{"head_size": 8, "head_bias": True, "gated": True,
                                                                    "activation": "Tanh", "dilations": [1]}]}})
    box = {"architecture": "SlimmableContainer", "config": {"submodels": [
        {"max_value": 0.5, "model": {"architecture": "LSTM", "n": 1}}, {"max_value": 1, "model": {"architecture": "LSTM", "n": 2}}]}}
    assert N.inner(box)["n"] == 2


def test_check_files_refuses_a_file_that_is_not_the_manifests(tmp_path, monkeypatch):
    (tmp_path / "x.nam").write_text("{}")
    rows = "file_name,sha256,creator,class_guess\n" + "x.nam,deadbeef,k,clean\n"
    (tmp_path / "manifest.csv").write_text(rows)
    (tmp_path / "capture-read.json").write_text(json.dumps([{"file": "x.nam", "capture": "x", "input_level_dbu": 1, "pack": "p"}]))
    monkeypatch.setattr(L, "tone3000", lambda: tmp_path)
    monkeypatch.setattr(L, "CAPTURES", 1)
    with pytest.raises(SystemExit):
        L.check_files()
