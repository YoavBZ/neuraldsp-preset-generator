"""L1a's rules (`learn/capture_units.py`, `learn/capture_labels.py`, `learn/nam_load.py`): pure parts."""
import json

import pytest

from learn import capture_labels as L
from learn import capture_units as U
from learn import nam_load as N
from learn import pipeline_fix as P


@pytest.fixture(autouse=True)
def no_t0(request, monkeypatch):
    """T0's file is the user's data: the gate tests take no unit away, and its own tests below hold the rule."""
    if not request.function.__name__.startswith("test_t0_"):
        monkeypatch.setattr(L, "t0_dropped", lambda units, verified=None: set())


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
    crunchy = set()

    def cls(c, it):
        if c == "all-heavy":
            return "high-gain"
        if c == "all-clean":
            return "clean"
        return "crunch" if it in crunchy else "clean"
    _, tried = U.walk(["all-heavy", "all-clean", "mixed"], players(), lambda c, it: "clean", 3)
    crunchy.update(tried["mixed"][-2:])                                 # two late candidates: the walk must reach them
    taken, _ = U.walk(["all-heavy", "all-clean", "mixed"], players(), cls, 3)
    assert taken["all-heavy"] == {}
    assert len(taken["all-clean"]) == 3
    assert crunchy <= set(taken["mixed"].values()) and len(taken["mixed"]) == 3


def test_walk_seeds_capture_order_amp_order_and_first_player():
    caps = [f"cap{j}" for j in range(40)]
    a, ta = U.walk(caps, players(), lambda c, it: "clean", 11)
    b, _ = U.walk(caps, players(), lambda c, it: "clean", 12)
    assert a != b
    firsts = {it[0] for v in ta.values() for it in v[:1]}
    assert len(firsts) >= 2                                             # the first player is not one player
    orders = {tuple(amps) for amps in a.values()}
    assert len(orders) >= 2                                             # amp order changes by capture
    assert list(a) != sorted(a)                                         # captures run in a seeded order


def test_walk_tells_after_each_capture():
    seen = []
    U.walk(["c1", "c2"], players(), lambda c, it: "clean", 3, after=lambda c, amps: seen.append((c, len(amps))))
    assert sorted(seen) == [("c1", 3), ("c2", 3)]


def test_worker_refuses_a_file_that_is_not_the_manifests(tmp_path):
    f = tmp_path / "x.nam"
    f.write_text("{}")
    assert U.checked({"path": str(f), "sha256": U.sha256_file(f)}) == str(f)
    with pytest.raises(SystemExit):
        U.checked({"path": str(f), "sha256": "00"})


def test_folds_keep_a_creator_together_and_balance():
    units = [{"creator": f"c{j % 7}"} for j in range(70)]
    fold = L.folds_by_creator(units)
    assert set(fold) == {f"c{j}" for j in range(7)} and set(fold.values()) <= set(range(L.FOLDS))
    assert L.folds_by_creator(units) == fold
    size = [sum(f == k for f in fold.values()) for k in range(L.FOLDS)]
    assert max(size) - min(size) <= 1


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
    made = [by[it["unit"]]["creator"] for it in items]
    assert max(made.count(c) for c in made) <= 2
    few = [dict(u, creator=f"k{j % 6}") for j, u in enumerate(us)]        # creators must repeat, and placebos must avoid them
    who = {u["unit"]: u["creator"] for u in few}
    for seed in range(30):
        got = L.pick_items(few, active, seed=seed, fallbacks=0)
        assert all(who[p] != who[it["unit"]] for it in got for p in it["placebos"])
        made = [who[it["unit"]] for it in got]
        assert max(made.count(c) for c in made) <= 2
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
    assert len(L.stage_set(list(range(121)), 2, "third")) == 41         # a third, rounded up
    assert len(L.stage_set(order, 60, "third")) == 60                   # never fewer than the items and placebos
    with pytest.raises(SystemExit):
        L.stage_set(order, 2, "rest")


def test_no_bks_or_goat_reader_sees_a_capture_record(tmp_path, monkeypatch):
    from learn import cc_build as CB

    assert L.CAPTURE_DIR not in (P.GOAT_DIR, P.REAL_DIR, P.PANEL_DIR, P.VREAL_DIR)
    monkeypatch.setattr(P, "out_dir", lambda *a: tmp_path)
    d = tmp_path / L.CAPTURE_DIR / P.SEARCH_DIR
    d.mkdir(parents=True)
    (d / "cap.json").write_text(json.dumps({"unit": "cap/x#a", "label": {"a": 1}, "stage": 1}))
    monkeypatch.setattr(P, "goat_units", lambda: [])
    monkeypatch.setattr(P, "goat_ear_passed", lambda u: set())
    monkeypatch.setattr(P, "goat_lags_refused", lambda u, h, tol=None: ({}, set()))
    assert P.goat_labels()[0] == []
    monkeypatch.setattr(P, "require", lambda k: {})
    monkeypatch.setattr(P, "recipe_inputs", lambda pin=None: (0, 0, 0, 0, 0))
    monkeypatch.setattr(CB, "cc_inventory", lambda: None)
    monkeypatch.setattr(P, "stage_units", lambda *a: [])
    monkeypatch.setattr(P, "real_folds", lambda *a: {})
    monkeypatch.setattr(P, "lag_refused", lambda r: set())
    assert P.real_labels(2)[0] == []


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


def layout(tmp_path, monkeypatch, verdicts=True):
    """Two units on disk, as `units`, with both gates' files if `verdicts`."""
    us = [{"unit": "cap/x#a", "capture": "x", "split": "uncertain", "capture_sha256": "aa", "item_lag": 0, "search": "A", "amp": "a"},
          {"unit": "cap/y#a", "capture": "y", "split": "driven", "capture_sha256": "bb", "item_lag": 0, "search": "B", "amp": "a"}]
    (tmp_path / "units.json").write_text(json.dumps({"units": us}))
    (tmp_path / "heavy-key.json").write_text(json.dumps({"build": "b", "items": [{"unit": "cap/y#a"}]}))
    if verdicts:
        (tmp_path / "ear-key.json").write_text(json.dumps({"build": "e"}))
        (tmp_path / "ear.json").write_text(json.dumps({"build": "e", "verdicts": {"x": {"verdict": "amp"}, "y": {"verdict": "amp"}}}))
        (tmp_path / "heavy.json").write_text(json.dumps({"build": "b", "verdicts": {"cap/y#a": {"verdict": "heavy"}}}))
    monkeypatch.setattr(L, "root", lambda: tmp_path)
    return us


def test_search_and_items_refuse_before_both_gates_by_default(tmp_path, monkeypatch):
    import argparse

    layout(tmp_path, monkeypatch, verdicts=False)
    monkeypatch.setattr(P, "require", lambda k: {})
    args = argparse.Namespace(before_ear=False, lags_only=True, shard=(0, 1), stage="third")
    with pytest.raises(SystemExit, match="not the current"):
        L.cmd_search(args)
    with pytest.raises(SystemExit, match="not the current"):
        L.cmd_items(args)


def test_the_pre_ear_path_covers_this_batch_only(tmp_path, monkeypatch):
    us = layout(tmp_path, monkeypatch)
    monkeypatch.setattr(P, "require", lambda k: {"phase_l1a_night_batch": L.batch_digest(us)})
    assert L.night_guard(us)
    with pytest.raises(SystemExit):
        L.night_guard(us + [dict(us[0], capture_sha256="cc")])


def test_items_are_drawn_once(tmp_path, monkeypatch):
    layout(tmp_path, monkeypatch)
    monkeypatch.setattr(P, "require", lambda k: {})
    (tmp_path / "items.json").write_text("{}")
    with pytest.raises(SystemExit, match="drawn once"):
        L.cmd_items(None)


def test_every_reader_of_the_records_passes_the_gates(tmp_path, monkeypatch):
    layout(tmp_path, monkeypatch)
    (tmp_path / "lags").mkdir()
    (tmp_path / P.SEARCH_DIR).mkdir()
    for u in ("cap/x#a", "cap/y#a"):
        (tmp_path / "lags" / f"{u.replace('/', '__')}.json").write_text(json.dumps({"lag": 0}))
        (tmp_path / P.SEARCH_DIR / f"{u.replace('/', '__')}.json").write_text(json.dumps({"unit": u, "label": {"a": 1}}))
    assert set(L.search_records()) == {"cap/x#a"}                 # y's unit is out on the heavy page


def test_night_check_says_go_or_stop_and_stores_no_figure(tmp_path, monkeypatch, capsys):
    us = layout(tmp_path, monkeypatch)
    monkeypatch.setattr(P, "require", lambda k: {"phase_l1a_night_batch": L.batch_digest(us)})
    (tmp_path / P.SEARCH_DIR).mkdir()
    for u in ("cap__x#a|a.json", "cap__y#a|a.json"):
        (tmp_path / P.SEARCH_DIR / u).write_text("{}")
    monkeypatch.setattr(P, "stage_read", lambda r, ph: {"stop": False, "labelled": 2, "held_best_minus_S": {"mean": -0.5}})
    L.cmd_night_check(None)
    assert capsys.readouterr().out.strip() == "GO"
    stored = json.loads((tmp_path / "night-check.json").read_text())
    assert set(stored) == {"stop", "time"}
    monkeypatch.setattr(P, "stage_read", lambda r, ph: {"stop": True, "labelled": 2, "held_best_minus_S": {"mean": 0.5}})
    with pytest.raises(SystemExit):
        L.cmd_night_check(None)
    assert capsys.readouterr().out.strip() == "STOP"


def test_commands_refuse_without_the_ledgers_phase(tmp_path, monkeypatch):
    import argparse

    layout(tmp_path, monkeypatch)

    def no(k):
        raise SystemExit(f"no {k}")
    monkeypatch.setattr(P, "require", no)
    a = argparse.Namespace(before_ear=False, lags_only=True, shard=(0, 1), stage="third", exports=[])
    for cmd in (L.cmd_search, L.cmd_items, L.cmd_answers, L.cmd_heavy_answers, L.cmd_stage_check, L.cmd_page, L.cmd_heavy,
                L.cmd_scope, L.cmd_scope_answers):
        with pytest.raises(SystemExit, match="no phase_l1a"):
            cmd(a)


def test_a_short_batch_stops_at_the_data_stage(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "root", lambda: tmp_path)
    (tmp_path / "units.json").write_text(json.dumps({"units": [], "short": {"(pr12, clean)": 3}}))
    with pytest.raises(SystemExit, match="data stage"):
        L.units_of()


def test_items_stop_when_the_trusted_cells_are_short(tmp_path, monkeypatch):
    layout(tmp_path, monkeypatch)
    monkeypatch.setattr(P, "require", lambda k: {})
    monkeypatch.setattr(L, "trusted_units", lambda: ([{"amp": "pr12", "cls": "clean"}], {}))
    with pytest.raises(SystemExit, match="under 10"):
        L.cmd_items(None)


def test_trusted_refuses_until_both_pages_are_current(tmp_path, monkeypatch):
    us = layout(tmp_path, monkeypatch, verdicts=False)
    with pytest.raises(SystemExit):                                # nothing heard
        L.trusted(us)
    (tmp_path / "ear-key.json").write_text(json.dumps({"build": "e"}))
    (tmp_path / "ear.json").write_text(json.dumps({"build": "other", "verdicts": {"x": {"verdict": "amp"}, "y": {"verdict": "amp"}}}))
    with pytest.raises(SystemExit, match="ear page's build"):
        L.trusted(us)
    (tmp_path / "ear.json").write_text(json.dumps({"build": "e", "verdicts": {"x": {"verdict": "amp"}, "y": {"verdict": "amp"}}}))
    with pytest.raises(SystemExit, match="still unheard"):          # the heavy card
        L.trusted(us)
    (tmp_path / "heavy.json").write_text(json.dumps({"build": "other", "verdicts": {}}))
    with pytest.raises(SystemExit, match="heavy page's build"):
        L.trusted(us)
    (tmp_path / "heavy.json").write_text(json.dumps({"build": "b", "verdicts": {"cap/y#a": {"verdict": "keep"}}}))
    assert L.trusted(us) == {"cap/x#a", "cap/y#a"}
    (tmp_path / "ear.json").write_text(json.dumps({"build": "e", "verdicts": {"x": {"verdict": "amp"}, "y": {"verdict": "odd"}}}))
    with pytest.raises(SystemExit, match="not the current"):        # y's unit is on the page but its capture failed
        L.trusted(us)


def test_heavy_candidates_are_the_driven_units_of_passed_captures():
    us = [{"unit": "a", "capture": "x", "split": "driven"}, {"unit": "b", "capture": "y", "split": "driven"},
          {"unit": "c", "capture": "x", "split": "uncertain"}]
    assert L.heavy_candidates(us, {"x": {"verdict": "amp"}, "y": {"verdict": "odd"}}) == ["a"]


def test_scope_cards_are_undriven_crunch_at_the_line_and_not_yet_heard():
    us = [{"unit": "a", "cls": "crunch", "split": "uncertain", "nonlinear_db": -1.0},
          {"unit": "b", "cls": "crunch", "split": "uncertain", "nonlinear_db": L.SCOPE_DB},
          {"unit": "c", "cls": "crunch", "split": "uncertain", "nonlinear_db": L.SCOPE_DB - 0.01},    # under the line
          {"unit": "d", "cls": "crunch", "split": "driven", "nonlinear_db": 2.0},                     # had the heavy page
          {"unit": "e", "cls": "clean", "split": "uncertain", "nonlinear_db": -1.0},
          {"unit": "f", "cls": "crunch", "split": "uncertain", "nonlinear_db": -2.0}]                 # on the label page
    assert L.scope_cards(us, {"f"}) == ["a", "b"]


def test_the_scope_page_builds_its_cards_and_refuses_the_second_batch(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "require", lambda k: {})
    monkeypatch.setattr(L, "root", lambda: tmp_path)
    us = [{"unit": "u", "cls": "crunch", "split": "uncertain", "nonlinear_db": -1.0, "render_sha256": "r"}]
    monkeypatch.setattr(L, "trusted_units", lambda: (us, {}))
    (tmp_path / "ear-check").mkdir()
    (tmp_path / "ear-check" / "key.json").write_text(json.dumps({"items": []}))
    got = {}
    monkeypatch.setattr(L, "build_page", lambda items, spec, key, by: got.update(items=items, spec=spec, key=key))
    L.cmd_scope(None)
    assert [it["unit"] for it in got["items"]] == ["u"] and got["spec"] is L.SCOPE_SPEC and got["key"] == "scope-key.json"
    monkeypatch.setattr(L, "BATCH", L.BATCH2)
    with pytest.raises(SystemExit, match="first batch"):
        L.cmd_scope(None)


def test_scope_out_drops_the_label_pages_two_and_what_the_scope_page_did_not_keep(tmp_path, monkeypatch):
    us = layout(tmp_path, monkeypatch, verdicts=False)
    (tmp_path / "ear-key.json").write_text(json.dumps({"build": "e"}))
    (tmp_path / "ear.json").write_text(json.dumps({"build": "e", "verdicts": {"x": {"verdict": "amp"}, "y": {"verdict": "amp"}}}))
    (tmp_path / "heavy.json").write_text(json.dumps({"build": "b", "verdicts": {"cap/y#a": {"verdict": "keep"}}}))
    assert L.scope_out() == set(L.LABEL_PAGE_OUT)                  # no scope page yet: the label page's two alone
    assert L.trusted(us) == {"cap/x#a", "cap/y#a"}
    monkeypatch.setattr(L, "LABEL_PAGE_OUT", ("cap/x#a",))
    assert L.trusted(us) == {"cap/y#a"}
    monkeypatch.setattr(L, "LABEL_PAGE_OUT", ())
    (tmp_path / "scope-key.json").write_text(json.dumps({"build": "s", "items": [{"unit": "cap/x#a"}, {"unit": "cap/y#a"}]}))
    with pytest.raises(SystemExit, match="2 scope cards still unheard"):      # the page built, nothing answered
        L.trusted(us)
    (tmp_path / "scope.json").write_text(json.dumps({"build": "s", "verdicts": {"cap/x#a": {"verdict": "keep"}}}))
    with pytest.raises(SystemExit, match="1 scope cards still unheard"):
        L.trusted(us)
    (tmp_path / "scope.json").write_text(json.dumps({"build": "other", "verdicts": {}}))
    with pytest.raises(SystemExit, match="scope page's build"):
        L.trusted(us)
    (tmp_path / "scope.json").write_text(json.dumps({"build": "s", "verdicts": {"cap/x#a": {"verdict": "keep"},
                                                                                "cap/y#a": {"verdict": "heavy"}}}))
    assert L.scope_out() == {"cap/y#a"}                            # only "keep" stays, and it drops that unit alone
    assert L.trusted(us) == {"cap/x#a"}


def test_the_rest_needs_the_page_and_a_clean_stage_check(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "root", lambda: tmp_path)
    with pytest.raises(SystemExit):
        L.rest_may_run()
    (tmp_path / "stage-check.json").write_text(json.dumps({"stop": False}))
    (tmp_path / "ear-check.json").write_text(json.dumps({}))        # no branch fails closed
    with pytest.raises(SystemExit):
        L.rest_may_run()
    (tmp_path / "ear-check.json").write_text(json.dumps({"branch": "clear below"}))
    with pytest.raises(SystemExit):
        L.rest_may_run()
    (tmp_path / "ear-check.json").write_text(json.dumps({"branch": "reaching one half"}))
    with pytest.raises(SystemExit, match="scope page"):
        L.rest_may_run()
    (tmp_path / "scope.json").write_text(json.dumps({"build": "s", "verdicts": {}}))
    L.rest_may_run()
    (tmp_path / "scope-key.json").write_text(json.dumps({"build": "s", "items": [{"unit": "u"}]}))
    with pytest.raises(SystemExit, match="1 scope cards still unheard"):
        L.rest_may_run()
    (tmp_path / "scope.json").write_text(json.dumps({"build": "s", "verdicts": {"u": {"verdict": "keep"}}}))
    L.rest_may_run()
    (tmp_path / "ear-check.json").write_text(json.dumps({"branch": None, "build": "04cf993bee72"}))    # F57's held-out part
    L.rest_may_run()
    (tmp_path / "ear-check.json").write_text(json.dumps({"branch": None, "build": "other"}))           # a truly partial file
    with pytest.raises(SystemExit, match="label page"):
        L.rest_may_run()
    (tmp_path / "ear-check.json").write_text(json.dumps({"branch": "reaching one half"}))
    (tmp_path / "stage-check.json").write_text(json.dumps({"stop": True}))
    with pytest.raises(SystemExit):
        L.rest_may_run()


def test_the_default_search_skips_an_item_outside_the_trusted_units(tmp_path, monkeypatch):
    import argparse

    layout(tmp_path, monkeypatch)                                  # cap/y#a went out on the heavy page
    monkeypatch.setattr(P, "require", lambda k: {})
    monkeypatch.setattr(L, "lags_of", lambda tr: ({u["unit"]: 0 for u in tr}, set()))
    (tmp_path / "items.json").write_text(json.dumps({"items": [{"unit": "cap/y#a", "placebos": ["cap/x#a", "p2", "p3"]}]}))
    calls = []
    monkeypatch.setattr(P, "search_units", lambda mine, *a, **k: calls.append([u["unit"] for u in mine]) or 0)
    L.cmd_search(argparse.Namespace(before_ear=False, lags_only=False, shard=(0, 1), stage="third", recipe="goat"))
    assert calls == [["cap/x#a"]]


def test_a_fallback_comes_due_only_when_the_placebo_gave_no_label():
    items = [{"unit": "i", "placebos": ["p1", "p2", "p3"]}]
    assert L.fallbacks_due(items, {}) == ["p1"]
    assert L.fallbacks_due(items, {"p1": {"a": 1}}) == []
    assert L.fallbacks_due(items, {"p1": None}) == ["p2"]
    assert L.fallbacks_due(items, {"p1": None, "p2": None, "p3": None}) == []


def test_pick_items_gives_every_part_a_placebo_before_any_fallback():
    us = units(n=4)                                                 # 2 items and 2 others a cell: no room for fallbacks
    for u in us:
        u["creator"] = u["pack"]                                    # all different
    got = L.pick_items(us, {u["unit"]: {"A": 1.0, "B": 1.0} for u in us})
    assert len(got) == 12 and all(it["placebos"] for it in got)


def test_stage_beside_reads_gain_against_input_gain(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "out_dir", lambda *a: tmp_path)
    recs = [{"unit": f"u{j}", "held": "A", "label": {"parameters/inputGain": str(j)}, "s_judge": {"A": 5.0},
             "best": {"judge": {"A": 4.0}}} for j in range(6)]
    us = {f"u{j}": {"creator": f"k{j % 3}", "gain_db": float(j)} for j in range(6)}
    out = L.stage_beside(recs, us)
    assert out["input_gain_vs_capture_gain"]["spearman"] == 1.0
    assert out["captures"]["n"] == 6 and out["captures"]["search_gain"] > 0 and out["goat"] is None


def night_setup(tmp_path, monkeypatch):
    import argparse

    us = layout(tmp_path, monkeypatch, verdicts=False)
    monkeypatch.setattr(P, "require", lambda k: {"phase_l1a_night_batch": L.batch_digest(us)})
    calls = []
    monkeypatch.setattr(P, "search_units", lambda mine, root, ph, halves, refused, lags, quiet=False, searcher=None:
                        calls.append(([u["unit"] for u in mine], refused, lags, quiet)) or 0)
    return us, calls, lambda **k: argparse.Namespace(**{"before_ear": True, "lags_only": False, "shard": (0, 1), "stage": "third", "recipe": "goat", **k})


def test_the_night_path_searches_every_unit_quietly_in_the_seeded_order(tmp_path, monkeypatch):
    us, calls, args = night_setup(tmp_path, monkeypatch)
    L.cmd_search(args(lags_only=True))
    L.cmd_search(args(stage="third"))
    assert calls[0][1:] == (set(), True, True) and sorted(calls[0][0]) == sorted(u["unit"] for u in us)
    assert calls[1][1:] == (set(), False, True) and calls[1][0] == L.stage_set(L.night_order(us), 0, "third")
    s = [f"u{j:03d}" for j in range(30)]
    assert L.night_order([{"unit": u} for u in s]) == L.search_order(s, []) != s


def test_the_night_path_refuses_a_later_batch_before_any_search(tmp_path, monkeypatch):
    us, calls, args = night_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(P, "require", lambda k: {"phase_l1a_night_batch": "other"})
    with pytest.raises(SystemExit, match="first batch"):
        L.cmd_search(args())
    with pytest.raises(SystemExit, match="first batch"):
        L.cmd_night_check(None)
    assert calls == []


def test_the_rest_of_the_night_waits_for_a_clean_fault_check(tmp_path, monkeypatch):
    us, calls, args = night_setup(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="fault check"):
        L.cmd_search(args(stage="all"))
    (tmp_path / "night-check.json").write_text(json.dumps({"stop": True}))
    with pytest.raises(SystemExit, match="fault check"):
        L.cmd_search(args(stage="all"))
    assert calls == []
    (tmp_path / "night-check.json").write_text(json.dumps({"stop": False}))
    L.cmd_search(args(stage="all"))
    assert len(calls[0][0]) == len(us)


def test_night_check_waits_for_the_third_and_stops_on_no_label(tmp_path, monkeypatch, capsys):
    us, _, _ = night_setup(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="no record yet"):
        L.cmd_night_check(None)
    d = tmp_path / P.SEARCH_DIR
    d.mkdir()
    for u in L.stage_set(L.night_order(us), 0, "third"):
        (d / f"{u.replace('/', '__')}|a.json").write_text("{}")
    monkeypatch.setattr(P, "stage_read", lambda r, ph: {"stop": False, "labelled": 0})
    with pytest.raises(SystemExit):
        L.cmd_night_check(None)
    assert capsys.readouterr().out.strip() == "STOP"


def test_stage_check_reads_the_trusted_units_at_a_third(tmp_path, monkeypatch):
    us = layout(tmp_path, monkeypatch)
    monkeypatch.setattr(P, "require", lambda k: {})
    d = tmp_path / P.SEARCH_DIR
    d.mkdir()
    tr = [dict(us[0], gain_db=0.0, creator="k")] + [{"unit": f"cap/t{j}#a"} for j in range(3)]
    monkeypatch.setattr(L, "trusted_units", lambda: (tr, {}))
    monkeypatch.setattr(L, "search_records", lambda: {})
    with pytest.raises(SystemExit, match="at a third"):
        L.cmd_stage_check(None)
    (d / "x.json").write_text(json.dumps({"unit": "cap/x#a"}))
    (d / "y.json").write_text(json.dumps({"unit": "cap/y#a"}))           # not trusted: does not count
    with pytest.raises(SystemExit, match="at a third"):
        L.cmd_stage_check(None)
    (d / "t.json").write_text(json.dumps({"unit": "cap/t0#a"}))
    seen = {}

    def fake(r, ph, keep):
        seen["keep"] = keep
        return {"stop": False}
    monkeypatch.setattr(P, "stage_check", fake)
    monkeypatch.setattr(L, "stage_beside", lambda r, u: {})
    monkeypatch.setattr(P, "save", lambda *a: None)
    L.cmd_stage_check(None)
    assert seen["keep"] == {u["unit"] for u in tr}


def test_the_worker_loads_only_a_checked_file():
    import inspect

    assert "load(checked(" in inspect.getsource(U.worker)


def test_the_quiet_search_prints_no_judge_figure():
    import inspect

    src = inspect.getsource(P.search_units)
    assert 'print(f"{key[-70:]}: renders so far {renders}" if quiet else f"{key[-70:]}: {search}->{held} S' in src


def test_the_library_dis_leave_out_every_held_band():
    def row(band, j=0, **k):
        return {"di": f"{band}/{j}.wav", "start_s": float(j), "band": band, "training_ok": True, "clean": True, "disjoint": True, **k}

    rows = [row("Eggy", j) for j in range(60)] + [row("Zeno"), row("BKS"), row("Adam Buckley"), row("Blue Manic"),
                                                  row("Ale Lak", training_ok=False), row("Dom McLennon", clean=False)]
    got = L.library_dis(rows)
    assert set(got) == {"Eggy"} and len(got["Eggy"]) == L.BAND_SECTIONS
    assert got == L.library_dis(rows)


def test_each_second_batch_capture_plays_one_balanced_amp():
    caps = [f"c{j}" for j in range(30)]
    amp = U.amps_balanced(caps, "s")
    assert amp == U.amps_balanced(caps, "s") and sorted(amp) == sorted(caps)
    n = [list(amp.values()).count(a) for a in U.AMPS]
    assert max(n) - min(n) <= 1
    taken, _ = U.walk(caps, players(), lambda c, it: "clean", 5, amp_of=amp)
    assert all(list(v) == [amp[c]] for c, v in taken.items())


def test_the_second_batch_has_its_own_folder_phase_and_pages():
    assert L.BATCH2["dir"] != L.CAPTURE_DIR and L.BATCH2["phase"] != L.PHASE and L.BATCH2["page"]
    assert L.BATCH2["night"] != L.NIGHT


def test_the_second_batch_guard_reads_its_own_digest(tmp_path, monkeypatch):
    us = layout(tmp_path, monkeypatch)
    monkeypatch.setattr(L, "BATCH", L.BATCH2)
    d = L.batch_digest(us)
    monkeypatch.setattr(P, "require", lambda k: {"phase_l1b_night_batch": d})
    assert L.night_guard(us)
    monkeypatch.setattr(P, "require", lambda k: {"phase_l1a_night_batch": d})
    with pytest.raises(SystemExit, match="second batch"):
        L.night_guard(us)
    assert L.BATCH2["night"] + "_batch" in P.ledger_entry()


def test_a_held_half_the_judge_refuses_leaves_the_search_row():
    good = {"held": "A", "label": {"x": 1}, "s_judge": {"A": 2.0}, "best": {"judge": {"A": 1.0}}}
    bad = {"held": "A", "label": {"x": 1}, "s_judge": {"A": float("inf")}, "best": {"judge": {"A": float("inf")}}}
    row = L.search_row([good, bad])
    assert row["n"] == 1 and row["s_held"] == 2.0



T0 = {"dis": {"cambridge/a.wav": {"verdict": "verified"}, "cambridge/b.wav": {"verdict": "excluded"}},
      "intake_dis": {"cambridge-new/c.wav": {"verdict": "verified"}},
      "measure_dis": {"telefunken-Blind_Spots-GTR": {"verdict": "excluded"}, "telefunken-Measurements-GTR": {"verdict": "pending ear"},
                      "cambridge-Quicksand-ElecGtr1": {"verdict": "verified"}}}


def test_t0_drops_every_di_it_did_not_verify_and_keeps_goats():
    units = [{"unit": u, "di": d} for u, d in (("g", "goat/item_1"), ("a", "cambridge/a.wav"), ("b", "cambridge/b.wav"),
                                               ("c", "cambridge-new/c.wav"),
                                               ("d", "telefunken/Doom Flamingo - Blind Spots LFTL/GTR DI_TDP-1.wav"),
                                               ("e", "telefunken/Doom Flamingo - Measurements LFTL/GTR DI_TDP-1.wav"),
                                               ("f", "cambridge/TheTravellingBand_Quicksand_Full/16_ElecGtr1DI.wav"))]
    assert L.t0_dropped(units, T0) == {"b", "d", "e"}            # "pending ear" is not trusted


def test_t0_refuses_a_di_it_has_no_verdict_on():
    with pytest.raises(SystemExit, match="no verdict"):
        L.t0_dropped([{"unit": "x", "di": "cambridge/nowhere.wav"}], T0)
