"""H4's opt-in paths in `pipeline_fix` (docs/heavy-cleanup-plan.md): the pinned exclusions, the W and FTm filters, the
chain, the inputs guard and the read's registrations, all without training or rendering."""
import argparse
import json

import pytest

from learn import pipeline_fix as P
from tests.test_pipeline_fix import _ft_records, _ft_world


def _lists(real_out=("u1", "u2"), pf=(1, 2), pg=(1,), nf=(9,), ng=()):
    d = {"real_out": {"ids": sorted(real_out)}, "plugin_out_full": {"ids": sorted(pf)},
         "plugin_out_gentle": {"ids": sorted(pg)}, "ns_out_full": {"ids": sorted(nf)}, "ns_out_gentle": {"ids": sorted(ng)}}
    for v in d.values():
        v["n"] = len(v["ids"])
    d["lists_sha256"] = P.h4_lists_sha(d)
    return d


def _pin(tmp_path, monkeypatch, doc=None, sha=None, have=(P.H4, P.H4_EXCL)):
    """A synthetic exclusions file under tmp_path, pinned in a synthetic ledger entry holding the keys `have`."""
    from learn import direct_stems as DS

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    p = tmp_path / "heavy" / "h4-exclusions.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_lists() if doc is None else doc))
    entry = {k: {} for k in have}
    if P.H4_EXCL in have:
        entry[P.H4_EXCL] = {"path": "heavy/h4-exclusions.json", "sha256": sha or DS.hashlib_file(p)}
    seen = []

    def require(key):
        seen.append(key)
        if key not in entry:
            raise SystemExit(f"the ledger has no {key}")
        return entry
    monkeypatch.setattr(P, "require", require)
    return p, seen


def test_the_exclusions_load_only_through_both_keys_and_the_pinned_hash(tmp_path, monkeypatch):
    p, seen = _pin(tmp_path, monkeypatch)
    ex = P.h4_exclusions()
    assert set(seen) == {P.H4, P.H4_EXCL}
    assert ex["real_out"] == {"u1", "u2"} and ex["plugin_out"] == {"full": {1, 2}, "gentle": {1}}
    assert ex["ns_out"] == {"full": {9}, "gentle": frozenset()} and ex["path"] == str(p)
    for have, why in (((P.H4,), P.H4_EXCL), ((P.H4_EXCL,), P.H4)):
        _pin(tmp_path, monkeypatch, have=have)
        with pytest.raises(SystemExit, match=why):
            P.h4_exclusions()
    _pin(tmp_path, monkeypatch, sha="0" * 64)
    with pytest.raises(SystemExit, match="pins"):
        P.h4_exclusions()
    bad = _lists()
    bad["plugin_out_full"]["ids"].append(3)                     # an edited list: its own lists_sha256 no longer fits
    bad["plugin_out_full"]["n"] = 3
    _pin(tmp_path, monkeypatch, doc=bad)
    with pytest.raises(SystemExit, match="lists_sha256"):
        P.h4_exclusions()
    bad = _lists()
    bad["ns_out_full"]["n"] = 5
    _pin(tmp_path, monkeypatch, doc=bad)
    with pytest.raises(SystemExit, match="count"):
        P.h4_exclusions()
    bad = _lists()
    del bad["ns_out_gentle"]
    _pin(tmp_path, monkeypatch, doc=bad)
    with pytest.raises(SystemExit, match="no list"):
        P.h4_exclusions()


def test_the_filter_takes_the_lists_out_and_keeps_plugin_rows_layout():
    tr, held = [1, 2, 3, 4], [7, 8, 9]
    rows = [{"i": i} for i in tr] + [{"i": i, "held": True} for i in held]
    tr2, held2, rows2 = P.h4_filter(tr, held, rows, {2, 4}, {8})
    assert tr2 == [1, 3] and held2 == [7, 9]
    assert rows2 == [{"i": 1}, {"i": 3}, {"i": 7, "held": True}, {"i": 9, "held": True}]
    assert P.h4_filter(tr, held, rows, set(), set()) == (tr, held, rows)
    with pytest.raises(SystemExit, match="training rows"):
        P.h4_filter(tr, held, rows, {7}, set())                    # an NS id in the training list
    with pytest.raises(SystemExit, match="NS rows"):
        P.h4_filter(tr, held, rows, set(), {5})
    with pytest.raises(SystemExit, match="layout"):
        P.h4_filter(tr, held, rows[::-1], set(), set())


def test_train_h4_takes_only_ws_recipe_and_a_plugin_arm():
    a = lambda **kw: argparse.Namespace(**{"h4": "full", "wide": True, "rung": "b", **kw})   # noqa: E731
    assert P.h4_train_refusal(a(), "P2b-wide24") is None and P.h4_train_refusal(a(h4="gentle"), "P2b-wide24") is None
    assert "real arm" in P.h4_train_refusal(a(h4="real"), "P2b-wide24")
    assert P.h4_train_refusal(a(wide=False), "P2b-wide24")
    assert P.h4_train_refusal(a(), "P2b-wide24-dd")              # any other flag changes W's base name
    assert P.h4_train_refusal(a(rung="a"), "P2b-wide24")
    assert set(P.H4_W.values()) == {"P2b-wide24-hf", "P2b-wide24-hg"}


def test_train_ft_h4_takes_only_ftms_recipe():
    a = argparse.Namespace(h4="real")
    ok = (True, False, P.FT_LR, P.FT_FALLBACK_CAP)
    assert P.h4_ft_refusal(a, *ok) is None
    for bad in ((False, False, P.FT_LR, 300), (True, True, P.FT_LR, 300), (True, False, P.FT_FALLBACK_LR, 300),
                (True, False, P.FT_LR, P.FT_CAP)):
        assert P.h4_ft_refusal(a, *bad)
    assert P.h4_ft_refusal(argparse.Namespace(h4="other"), *ok)


def test_h4_names_chain_within_the_arm_and_take_no_other_runs_name():
    for arm, base in (("full", "P2b-ftmf"), ("gentle", "P2b-ftmg"), ("real", "P2b-ftmc")):
        assert P.H4_FT[arm] == base
        assert P.ft_name(1, True, P.FT_LR, 300, base) == f"{base}-k1-inner-cap300"
        assert P.ft_name(1, False, P.FT_LR, 300, base) == f"{base}-k1" and P.ft_name(None, base=base) == base
    assert P.H4_PRETRAIN == {"full": "P2b-wide24-hf", "gentle": "P2b-wide24-hg", "real": "P2b-wide24"}
    old = {P.ft_name(k, i, P.FT_LR, c, b) for b in (P.FT_BASE, P.FTM_BASE) for k in (None, 0, 1, 2, 3)
           for i in (False, True) if not (i and k is None) for c in (P.FT_CAP, 300)}
    old |= {f"{P.FTM_BASE}{t}-k{k}" for t in ("s", "f25", "f50") for k in range(4)}      # N3's curve names
    new = {P.ft_name(k, i, P.FT_LR, 300, b) for b in P.H4_FT_TAGS for k in (None, 0, 1, 2, 3)
           for i in (False, True) if not (i and k is None)}
    assert not old & new


def _chain(arm, sha="x", drop=None, wrong=None):
    """A synthetic arm's records: W both seeds, its 8 inner and 8 FT_k runs; `drop` one missing, `wrong` one off-arm."""
    recs = {}
    h = {"arm": arm, "exclusions_sha256": sha}
    for sd in P.SEEDS:
        recs[(P.H4_PRETRAIN[arm], sd)] = {} if arm == "real" else {"h4": dict(h)}
        for k in range(P.REAL_FOLDS):
            for inner in (True, False):
                recs[(P.ft_name(k, inner, P.FT_LR, 300, P.H4_FT[arm]), sd)] = {"h4": dict(h)}
    if drop:
        del recs[drop]
    if wrong:
        recs[wrong] = {"h4": {"arm": "gentle" if arm != "gentle" else "full", "exclusions_sha256": sha}}
    return lambda nm, sd: recs.get((nm, sd))


def test_each_h4_run_refuses_until_its_arms_prerequisites_are_done():
    sd = P.SEEDS[0]
    for arm in P.H4_FT:
        get = _chain(arm)
        for k, inner in ((0, True), (2, False), (None, False)):
            assert P.h4_chain_refusal(arm, k, inner, "x", get) is None
        assert "not the" in P.h4_chain_refusal(arm, None, False, "other-sha", get)
    w = ("P2b-wide24-hf", P.SEEDS[1])
    assert "missing" in P.h4_chain_refusal("full", 0, True, "x", _chain("full", drop=w))      # inner: both Ws
    inner = (P.ft_name(3, True, P.FT_LR, 300, "P2b-ftmf"), sd)
    assert P.h4_chain_refusal("full", 0, True, "x", _chain("full", drop=inner)) is None       # inner needs no inner
    assert "missing" in P.h4_chain_refusal("full", 0, False, "x", _chain("full", drop=inner))
    ftk = (P.ft_name(2, False, P.FT_LR, 300, "P2b-ftmf"), sd)
    assert P.h4_chain_refusal("full", 1, False, "x", _chain("full", drop=ftk)) is None        # FT_k needs no FT_k
    assert "missing" in P.h4_chain_refusal("full", None, False, "x", _chain("full", drop=ftk))
    assert "not the full arm" in P.h4_chain_refusal("full", 1, False, "x", _chain("full", wrong=inner))
    assert "not the full arm" in P.h4_chain_refusal("full", 0, True, "x", _chain("full", wrong=w))
    real_w = ("P2b-wide24", sd)                                 # the real arm: today's W, no H4 field needed
    assert "missing" in P.h4_chain_refusal("real", 0, True, "x", _chain("real", drop=real_w))


def test_the_inputs_guard_checks_the_full_hash_and_the_units_less_real_out():
    ref = {"inputs_sha256": "full", "target_lufs": {"a": 1, "b": 1, "c": 1}}
    assert P.h4_inputs_refusal("full", {"a": 0, "c": 0}, ref, {"b"}, "P2b-dfix0") is None
    assert "unfiltered" in P.h4_inputs_refusal("other", {"a", "c"}, ref, {"b"}, "P2b-dfix0")
    assert "1 extra" in P.h4_inputs_refusal("full", {"a", "b", "c"}, ref, {"b"}, "P2b-dfix0")
    assert "1 missing" in P.h4_inputs_refusal("full", {"a"}, ref, {"b"}, "P2b-dfix0")
    assert P.h4_real_out_refusal({"a"}, ref["target_lufs"]) is None
    assert "never had" in P.h4_real_out_refusal({"a", "z"}, ref["target_lufs"])


def test_the_inputs_hash_is_dfixdatas_over_the_units(tmp_path, monkeypatch):
    import hashlib

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "DFIX_K", 3)
    for u in ("goat/x@1.0#amp_1", "s/A_Full/d.wav@0.0#t.wav"):
        for v in range(3):
            p = P.dfix_input_path(u, v)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(f"{u}{v}".encode())
    h = hashlib.sha256()                                        # DfixData's loop: units sorted, variants in order
    for u in sorted({"s/A_Full/d.wav@0.0#t.wav", "goat/x@1.0#amp_1"}):
        for v in range(3):
            p = P.dfix_input_path(u, v)
            h.update(f"{p.name} {hashlib.sha256(p.read_bytes()).hexdigest()}\n".encode())
    assert P.dfix_inputs_sha256(["s/A_Full/d.wav@0.0#t.wav", "goat/x@1.0#amp_1", "goat/x@1.0#amp_1"]) == h.hexdigest()


def test_real_out_leaves_every_real_row_and_every_held_set(monkeypatch):
    brecs, by_unit, folds, grecs, gunits = _ft_records()
    monkeypatch.setattr(P, "real_labels", lambda stage: (brecs, by_unit, folds))
    monkeypatch.setattr(P, "goat_labels", lambda: (grecs, gunits, None))
    monkeypatch.setattr(P, "record_rows", lambda recs, by, row0, label_of=None: [
        {"i": row0 + j, "real": r["unit"]} for j, r in enumerate(recs)])
    drop = frozenset({"b3", "b6", sorted(gunits)[0]})
    for k, inner in ((0, True), (1, True), (2, False), (None, False)):
        assert P.ft_real_rows(k, inner) == P.ft_rows_of(brecs, by_unit, folds, grecs, gunits, k, inner)
        tr, held, n = P.ft_real_rows(k, inner, drop)
        full_tr, full_held, _ = P.ft_real_rows(k, inner)
        assert not {r["real"] for r in tr + held} & drop
        assert {r["real"] for r in tr + held} == {r["real"] for r in full_tr + full_held} - drop
        assert n["real_rows"] == len([r for r in tr if r["i"] < P.GOAT_ROW0])
        if inner:                                               # the validation fold j that chooses E is cleaned too
            assert held and all(r["real"] not in drop for r in held)


def test_the_all_labels_pairs_guard_takes_the_h4_form():
    recs, sets_get, _, w_of, _ = _ft_world()
    r0 = P.REAL_ROW0
    d = {sd: {"train_ids": [1, 2, r0, r0 + 1], "held_ids": [9],
              "dfix": {"inputs_sha256": "full", "target_lufs": {"a": 0, "b": 0, "c": 0}}} for sd in P.SEEDS}
    inner = sets_get((P.FT_LR, P.FT_CAP))
    get = lambda lr, cap: inner if (lr, cap) == (P.FT_LR, P.FT_FALLBACK_CAP) else None   # noqa: E731
    h4 = [dict(r_, cap=P.FT_FALLBACK_CAP, real_held_ids=[],
               dfix={"inputs_sha256": "filtered", "target_lufs": {"a": 0, "c": 0}},
               h4={"full_inputs_sha256": "full", "inputs_sha256": "filtered", "train_units": ["a", "c"]}) for r_ in recs]
    kw = dict(base="P2b-ftmc", pretrain="P2b-wide24", real_out={"b"})
    assert P.ft_vreal_provenance(h4, get, w_of, d.get, **kw) == h4
    for change, why in (({"h4": dict(h4[0]["h4"], full_inputs_sha256="x")}, "unfiltered"),
                        ({"dfix": {"inputs_sha256": "filtered", "target_lufs": {"a": 0, "b": 0, "c": 0}}}, "extra"),
                        ({"h4": dict(h4[0]["h4"], train_units=["a"])}, "training units"),
                        ({"h4": dict(h4[0]["h4"], inputs_sha256="y")}, "filtered inputs hash"),
                        ({"real_held_ids": [r0 + P.DFIX_HELD0]}, "holds real rows"),
                        ({"E": 99}, "inner median"), ({"cap": P.FT_CAP}, "FTm's rate and cap")):
        with pytest.raises(SystemExit, match=why):
            P.ft_vreal_provenance([dict(h4[0], **change), h4[1]], get, w_of, d.get, **kw)
    with pytest.raises(SystemExit, match="P2b-ftmc: the 8 inner runs"):
        P.ft_vreal_provenance(h4, lambda lr, cap: None, w_of, d.get, **kw)


def test_an_h4_read_takes_only_its_arms_runs_on_the_pinned_exclusions():
    ok = {"test": "P2b-ftmg-k2", "seed": 1, "h4": {"arm": "gentle", "exclusions_sha256": "x"}}
    P.h4_read_check(ok, "x")
    P.h4_read_check(dict(ok, test="P2b-ftmg"), "x")
    for bad in (dict(ok, h4={"arm": "full", "exclusions_sha256": "x"}),
                dict(ok, h4={"arm": "gentle", "exclusions_sha256": "y"}),
                dict(ok, h4=None), dict(ok, test="P2b-ftm-k2"), dict(ok, test="P2b-ftmg50-k2")):
        with pytest.raises(SystemExit, match="not an H4 run"):
            P.h4_read_check(bad, "x")


def test_the_h4_tags_read_under_phase_h4_as_ftm_does():
    for t in P.H4_FT_TAGS:
        assert P.read_phase(t) == P.H4
        assert P.report_phase({t, P.FTM_BASE, "S"}) == P.H4
    assert P.read_phase(P.FTM_BASE) == "phase_night2" and P.report_phase({P.FTM_BASE, "S"}) == "phase_night2"
    assert P.report_phase({"P2b-ftmf50", "S"}) == "phase_5b1"            # an N3 tag is not an H4 one
    assert P.H4 in P.ARM_FOLD_PHASES


def test_goat_predict_takes_the_h4_tags(monkeypatch):
    seen = []
    monkeypatch.setattr(P, "goat_predict", lambda name: seen.append(name))
    for t in sorted(P.H4_FT_TAGS):
        P.cmd_goat_predict(argparse.Namespace(names=t))
    assert seen == sorted(P.H4_FT_TAGS)
    with pytest.raises(SystemExit):
        P.cmd_goat_predict(argparse.Namespace(names="P2b-ftmx"))


def test_the_h4_tags_reach_the_predict_paths_and_refuse_without_the_pin(monkeypatch):
    keys = []

    def require(k):
        keys.append(k)
        if k == P.H4_EXCL:
            raise SystemExit(f"no {k}")
        return {}
    monkeypatch.setattr(P, "require", require)
    for fn in (P.goat_predict, P.real_predict_5b2):
        keys.clear()
        with pytest.raises(SystemExit, match=P.H4_EXCL):
            fn("P2b-ftmc")
        assert keys == [P.H4, P.H4, P.H4_EXCL]                 # read_phase's key, then the exclusions' two
    seen = []
    monkeypatch.setattr(P, "real_predict_5b2", lambda name: seen.append(name))
    for t in sorted(P.H4_FT_TAGS):
        P.cmd_real_predict(argparse.Namespace(names=t))
    assert seen == sorted(P.H4_FT_TAGS)


def test_h4_apart_reports_real_out_units_apart_and_leaves_the_default_unchanged(tmp_path, monkeypatch):
    pytest.importorskip("scipy")
    _pin(tmp_path, monkeypatch, doc=_lists(real_out=("g/u2",)), have=(P.H4, P.H4_EXCL, "phase_5c"))
    units = [{"unit": f"g/u{j}", "amp": "pr12", "item": f"it{j}", "fold": j % 4} for j in range(6)]
    monkeypatch.setattr(P, "goat_read_units", lambda tol=None: units)
    for t, scale in (("P2b-ftmf", 1.0), ("P2b-ftm", 2.0)):
        d = tmp_path / P.GOAT_DIR / "judge" / t
        d.mkdir(parents=True)
        for j, u in enumerate(units):
            v = scale * (1 + j)
            (d / f"{j}.json").write_text(json.dumps({"unit": u["unit"], "amp": "pr12",
                                                     "judge": {"A": {"B": v}, "B": {"A": v * 1.1}}}))
    a = argparse.Namespace(pairs="P2b-ftmf:P2b-ftm", label="t", lag_tol=None, h4_apart=False)
    P.cmd_goat_report(a)
    base = json.loads((tmp_path / P.GOAT_DIR / "report-t.json").read_text())
    assert list(base["rows"]) == ["P2b-ftmf - P2b-ftm"] and "h4_apart" not in base
    assert base["rows"]["P2b-ftmf - P2b-ftm"]["parts"] == 6
    P.cmd_goat_report(argparse.Namespace(**{**vars(a), "h4_apart": True}))
    rep = json.loads((tmp_path / P.GOAT_DIR / "report-t.json").read_text())
    assert list(rep["rows"]) == ["P2b-ftmf - P2b-ftm", "P2b-ftmf - P2b-ftm (real_out, apart)"]
    assert rep["rows"]["P2b-ftmf - P2b-ftm"]["parts"] == 5
    assert rep["rows"]["P2b-ftmf - P2b-ftm (real_out, apart)"]["parts"] == 1
    assert rep["h4_apart"]["real_out"] == ["g/u2"] and rep["ledger"].endswith(P.H4)
    assert P.h4_apart_groups([("a", 1), ("b", 2)], None) == [("", [("a", 1), ("b", 2)])]


def test_real_report_h4_apart_splits_the_rows_by_real_out(tmp_path, monkeypatch):
    pytest.importorskip("scipy")
    from learn import cc_build as CB

    _pin(tmp_path, monkeypatch, doc=_lists(real_out=("s/A/d1@0#t1",)), have=(P.H4, P.H4_EXCL, "phase_5b1", "phase_5b2"))
    parts = [{"unit": f"s/A/d{j}@0#t{j}", "di": f"d{j % 3}", "rig": f"r{j}"} for j in range(6)]
    d = tmp_path / P.REAL_DIR / "answers"
    d.mkdir(parents=True)
    (d / "S.json").write_text(json.dumps({"parts": parts}))
    for t, scale in (("S", 3.0), ("P2b-ftmg", 1.0), ("P2b-ftm", 2.0)):
        jd = tmp_path / P.REAL_DIR / "judge" / t
        jd.mkdir(parents=True)
        for j, p_ in enumerate(parts):
            for amp in P.AMPS3:
                v = scale * (1 + j)
                (jd / f"{j}-{amp}.json").write_text(json.dumps({"unit": p_["unit"], "amp": amp,
                                                                "judge": {"A": {"B": v}, "B": {"A": v}}}))
    monkeypatch.setattr(P, "recipe_inputs", lambda pin=None: (None, {}, None, {}, None))
    monkeypatch.setattr(CB, "cc_inventory", lambda: {})
    monkeypatch.setattr(P, "stage_units", lambda kept, sp, inv, st: parts)
    monkeypatch.setattr(P, "real_folds", lambda a, b: {f"d{j}": j for j in range(3)})
    a = argparse.Namespace(pairs="P2b-ftmg:P2b-ftm", label="t", within="", h4_apart=False)
    P.cmd_real_report(a)
    base = json.loads((tmp_path / P.REAL_DIR / "report-t.json").read_text())
    assert list(base["rows"]) == ["P2b-ftmg - P2b-ftm"] and base["ledger"].endswith(P.H4)
    assert base["rows"]["P2b-ftmg - P2b-ftm"]["parts"] == 6 and "h4_apart" not in base
    P.cmd_real_report(argparse.Namespace(**{**vars(a), "h4_apart": True}))
    rep = json.loads((tmp_path / P.REAL_DIR / "report-t.json").read_text())
    assert rep["rows"]["P2b-ftmg - P2b-ftm"]["parts"] == 5
    assert rep["rows"]["P2b-ftmg - P2b-ftm (real_out, apart)"]["parts"] == 1
    assert rep["rows"]["P2b-ftmg - P2b-ftm"]["directions"] == 5 * len(P.AMPS3) * 2


# --- the two training commands' H4 wiring, end to end with fakes in place of torch, the data and `fit` ------------------

class _Stop(Exception):
    pass


def _fake_torch(monkeypatch):
    import sys
    import types

    t = types.ModuleType("torch")
    t.set_num_threads = lambda n: None
    t.save = lambda st, p: open(p, "wb").write(b"state")
    monkeypatch.setitem(sys.modules, "torch", t)


def _world(tmp_path, monkeypatch, doc):
    """Ledger, exclusions pin, D_CC's split (training 1-6, NS 7-9) and W's stored record, all synthetic."""
    have = (P.H4, P.H4_EXCL, "phase_3", "phase_5a", "phase_ft", "phase_night2", "phase_ft_fallback", "phase_n4",
            "phase_ft_carry")
    _pin(tmp_path, monkeypatch, doc=doc, have=have)
    entry = P.require(P.H4)
    entry["phase_3_length"] = {"epochs": 10, "every": 5}
    kept = {i: {"section": f"s{i}", "band": "b"} for i in range(1, 10)}
    sp = {"train": [1, 2, 3, 4, 5, 6], "fs": [], "ns": [7, 8, 9], "dropped": {}}
    monkeypatch.setattr(P, "recipe_inputs", lambda pin=None: (None, kept, None, sp, {"doubles": "kept"}))
    monkeypatch.setattr(P, "rung_rows", lambda kept_, rend, ids: [{"i": i, "amp": "pr12", "cls": "clean"} for i in ids])
    monkeypatch.setattr(P, "rung_path", lambda *a: None)
    od = tmp_path / "runs"
    od.mkdir()
    for sd in P.SEEDS:
        (od / f"P2b-wide24-{sd}.json").write_text(json.dumps({"train_ids": sp["train"], "held_ids": sp["ns"],
                                                              "model_sha256": {"best": f"w{sd}"}}))
    _fake_torch(monkeypatch)
    return od


def _w_args(**kw):
    a = dict(rung="b", aug=False, backings=False, dd=False, pc=False, pcsz=False, wide=True, goat=False,
             goat_shuffle=False, fold=None, frac=1.0, sections=1.0, stage=0, real_fold=None, dfix=False,
             dfix_share=None, seed=P.SEEDS[0], h4="full")
    a.update(kw)
    return argparse.Namespace(**a)


def test_train_h4_filters_ws_rows_and_records_the_arm(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    od = _world(tmp_path, monkeypatch, _lists(pf=(2, 4), nf=(8,)))
    seen = {}

    class Wide:
        def __init__(self, rows, path_of, train_ids):
            seen.update(rows=[r["i"] for r in rows], train=set(train_ids))
            self.Y, self.applied, self.counts = [np.zeros(len(rows))], {}, {}
    monkeypatch.setattr(P, "WideData", Wide)

    class Base:
        def __init__(self, *a):
            pass

        def losses(self, *a):
            return {}
    monkeypatch.setattr(P, "Baseline", Base)
    monkeypatch.setattr(P, "device", lambda: "cpu")

    def fit(data, ti, watch, track, seed, dev, log, epochs, every=1, **kw):
        seen.update(ti=list(ti), held=list(watch[track]), track=track)
        log += [{"epoch": e, "steps": e} for e in range(epochs)]
        return type("N", (), {"load_state_dict": lambda self, st: None})(), {}, {}, 8, 1.0
    monkeypatch.setattr(P, "fit", fit)
    monkeypatch.setattr(P, "head_losses", lambda *a: {})
    monkeypatch.setattr(P, "head_table", lambda a, b: {"families": {"model": 0, "baseline": 0}, "knobs": [],
                                                       "knobs_below_baseline": 0, "switches": [],
                                                       "switches_below_baseline": 0})
    monkeypatch.setattr(P, "family_means", lambda v: {})
    P.cmd_train(_w_args())
    assert seen["rows"] == [1, 3, 5, 6, 7, 9] and seen["train"] == {1, 3, 5, 6}
    assert seen["ti"] == [0, 1, 2, 3] and seen["held"] == [4, 5] and seen["track"] == "ns"
    rec = json.loads((od / f"P2b-wide24-hf-{P.SEEDS[0]}.json").read_text())
    assert rec["train_ids"] == [1, 3, 5, 6] and rec["held_ids"] == [7, 9] and rec["flags"]["h4"] == "full"
    assert rec["ledger"] == f"{P.LEDGER_ID} {P.H4}" and rec["h4"]["arm"] == "full"
    assert rec["h4"]["plugin_out"] == 2 and rec["h4"]["ns_out"] == 1 and rec["h4"]["possibly_undertrained"]
    assert rec["h4"]["exclusions_sha256"] == P.h4_exclusions()["sha256"]
    (od / f"P2b-wide24-{P.SEEDS[1]}.json").unlink()
    P.cmd_train(_w_args(seed=P.SEEDS[1], h4=None))           # without --h4: W's rows as they are, W's name
    assert seen["rows"] == list(range(1, 10))
    rec = json.loads((od / f"P2b-wide24-{P.SEEDS[1]}.json").read_text())
    assert "h4" not in rec and "h4" not in rec["flags"] and rec["ledger"] == f"{P.LEDGER_ID} phase_3"
    (od / f"P2b-wide24-{P.SEEDS[1]}.json").write_text(json.dumps({"train_ids": [1, 2], "held_ids": [7, 8, 9]}))
    with pytest.raises(SystemExit, match="unfiltered rows"):
        P.cmd_train(_w_args(seed=P.SEEDS[1]))
    with pytest.raises(SystemExit, match="real arm"):
        P.cmd_train(_w_args(h4="real"))


def _ft_args(**kw):
    a = dict(real_fold=1, inner=False, seed=P.SEEDS[0], masked=True, real_frac=1.0, shuffle_real=False, ft_lr=None,
             ft_cap=300, h4="full")
    a.update(kw)
    return argparse.Namespace(**a)


def _ft_runs(od, sha, units=("a", "b", "c", "d")):
    """The full arm's W (both seeds) and 8 inner runs; D_fix's records over `units`; FTm's inner runs."""
    from tests.test_pipeline_fix import _inner_log

    h = {"arm": "full", "exclusions_sha256": sha}
    for sd in P.SEEDS:
        (od / f"P2b-wide24-hf-{sd}.json").write_text(json.dumps({"train_ids": [1, 3, 5, 6], "held_ids": [7, 9],
                                                                 "model_sha256": {"best": f"hf{sd}"}, "h4": h}))
        for k in range(P.REAL_FOLDS):
            (od / f"P2b-ftmf-k{k}-inner-cap300-{sd}.json").write_text(json.dumps({
                "real_fold": k, "seed": sd, "lr": P.FT_LR, "cap": 300, "init": {"sha256": f"hf{sd}"}, "h4": h,
                "log": _inner_log([1.0] * 6 + [0.5])}))
            (od / f"P2b-ftm-k{k}-inner-cap300-{sd}.json").write_text(json.dumps({
                "dfix": {"inputs_sha256": "full-inner", "target_lufs": {u: 0 for u in units if u != "d"}}}))
        for nm in ("P2b-dfix", "P2b-dfix0", "P2b-dfix1", "P2b-dfix2", "P2b-dfix3"):
            (od / f"{nm}-{sd}.json").write_text(json.dumps({"dfix": {"inputs_sha256": "full",
                                                                     "target_lufs": {u: 0 for u in units}}}))


def _ft_fakes(monkeypatch, seen):
    import numpy as np

    def real_rows(k, inner, drop=frozenset()):
        tr = [{"i": P.REAL_ROW0 + j, "real": u, "amp": "pr12", "cls": "clean"} for j, u in enumerate("abc")]
        held = [] if inner else [{"i": P.REAL_ROW0 + P.DFIX_HELD0, "real": "d", "amp": "pr12", "cls": "clean"}]
        tr, held = [r for r in tr if r["real"] not in drop], [r for r in held if r["real"] not in drop]
        return tr, held, {"real_rows": len(tr)}
    monkeypatch.setattr(P, "ft_real_rows", real_rows)
    monkeypatch.setattr(P, "real_labels", lambda stage: ([], {u: {"di": "d0"} for u in "abcd"}, {"d0": 0}))
    monkeypatch.setattr(P, "goat_labels", lambda: ([], {}, None))        # the inner guard's folds: every unit fold 0

    def start(seed, pre=P.FT_PRETRAIN):
        seen["pre"] = pre
        return {}, json.loads((P.out_dir() / "runs" / f"{pre}-{seed}.json").read_text())
    monkeypatch.setattr(P, "ft_start_state", start)

    class Dfix:
        def __init__(self, rows, path_of, plugin_ids, real_train_ids, share):
            seen["rows"] = [r["i"] for r in rows]
            self.target_lufs = {r["real"]: 0.0 for r in rows if "real" in r}
            self.inputs_sha256, self.Y, self.counts = "filtered", None, {}
    monkeypatch.setattr(P, "DfixData", Dfix)
    monkeypatch.setattr(P, "A_menu_S", lambda: None)
    monkeypatch.setattr(P, "mask_searched", lambda Y, rows, ms: None)
    monkeypatch.setattr(P, "dfix_inputs_sha256", lambda units: {frozenset("abcd"): "full",
                                                                frozenset("abc"): "full-inner"}.get(frozenset(units), "?"))
    monkeypatch.setattr(P, "device", lambda: "cpu")

    def fit(data, ti, watch, track, seed, dev, log, epochs, **kw):
        seen.update(ti=list(ti), epochs=epochs, watch=sorted(watch))
        log += [{"epoch": e, "steps": e, "train_real": {"total": 1.0}, "real_val_smoothed": 1.0} for e in range(epochs)]
        return None, {}, {}, epochs - 1, 1.0
    monkeypatch.setattr(P, "fit", fit)
    return np


def test_train_ft_h4_chains_filters_and_guards_its_inputs(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    od = _world(tmp_path, monkeypatch, _lists(real_out=("b",), pf=(2, 4), nf=(8,)))
    sha = P.h4_exclusions()["sha256"]
    _ft_runs(od, sha)
    seen = {}
    _ft_fakes(monkeypatch, seen)
    P.cmd_train_ft(_ft_args())
    rec = json.loads((od / f"P2b-ftmf-k1-{P.SEEDS[0]}.json").read_text())
    assert seen["pre"] == "P2b-wide24-hf" and rec["init"]["run"] == f"P2b-wide24-hf-{P.SEEDS[0]}"
    assert seen["rows"] == [1, 3, 5, 6, P.REAL_ROW0, P.REAL_ROW0 + 2, 7, 9, P.REAL_ROW0 + P.DFIX_HELD0]
    assert rec["held_ids"] == [7, 9] and rec["ledger"] == f"{P.LEDGER_ID} {P.H4}" and seen["epochs"] == 7
    h = rec["h4"]
    assert h["full_inputs_sha256"] == "full" and h["inputs_sha256"] == "filtered" == rec["dfix"]["inputs_sha256"]
    assert h["real_out_dropped"] == ["b"] and h["train_units"] == ["a", "c"] and h["exclusions_sha256"] == sha
    assert h["inputs_ref"] == f"P2b-dfix1-{P.SEEDS[0]}"
    (od / f"P2b-ftmf-k2-inner-cap300-{P.SEEDS[1]}.json").unlink()
    from learn import full_space as F

    net = type("N", (), {"load_state_dict": lambda self, st: None, "to": lambda self, dev: self})()
    monkeypatch.setattr(F, "build_net", lambda: net)
    monkeypatch.setattr(P, "head_losses", lambda *a: {"total": 1.0})
    P.cmd_train_ft(_ft_args(inner=True, real_fold=2, seed=P.SEEDS[1]))        # an inner run: FTm's inner run is the ref
    rec = json.loads((od / f"P2b-ftmf-k2-inner-cap300-{P.SEEDS[1]}.json").read_text())
    assert rec["h4"]["inputs_ref"] == f"P2b-ftm-k2-inner-cap300-{P.SEEDS[1]}" and seen["watch"] == ["real_val", "train_real"]
    with pytest.raises(SystemExit, match="P2b-ftmf-k0-.*missing"):            # the all-labels pair: the arm's FT_k first
        P.cmd_train_ft(_ft_args(real_fold=None))


@pytest.mark.parametrize("break_it, why", [
    (lambda od, sd: (od / f"P2b-dfix1-{sd}.json").write_text(json.dumps({"dfix": {"inputs_sha256": "old",
                                                                         "target_lufs": {u: 0 for u in "abcd"}}})),
     "unfiltered"),
    (lambda od, sd: (od / f"P2b-dfix1-{sd}.json").write_text(json.dumps({"dfix": {"inputs_sha256": "full",
                                                                         "target_lufs": {u: 0 for u in "abcde"}}})),
     "less real_out"),
    (lambda od, sd: (od / f"P2b-dfix-{sd}.json").write_text(json.dumps({"dfix": {"target_lufs": {"a": 0}}})),
     "never had"),
    (lambda od, sd: (od / f"P2b-ftmf-k3-inner-cap300-{sd}.json").unlink(), "not all done|missing"),
    (lambda od, sd: (od / f"P2b-wide24-hf-{sd}.json").write_text(json.dumps({"train_ids": [1, 3, 5, 6],
                                                                             "held_ids": [7, 9], "h4": {"arm": "gentle"}})),
     "not the full arm"),
    (lambda od, sd: (od / f"P2b-wide24-hf-{sd}.json").write_text(json.dumps({
        "train_ids": [1, 2, 3, 5, 6], "held_ids": [7, 9], "model_sha256": {"best": f"hf{sd}"},
        "h4": json.loads((od / f"P2b-ftmf-k0-inner-cap300-{sd}.json").read_text())["h4"]})),
     "other plugin rows"),
])
def test_train_ft_h4_refuses_on_each_guard(tmp_path, monkeypatch, break_it, why):
    pytest.importorskip("numpy")
    od = _world(tmp_path, monkeypatch, _lists(real_out=("b",), pf=(2, 4), nf=(8,)))
    _ft_runs(od, P.h4_exclusions()["sha256"])
    _ft_fakes(monkeypatch, {})
    break_it(od, P.SEEDS[0])
    with pytest.raises(SystemExit, match=why):
        P.cmd_train_ft(_ft_args())
    assert not (od / f"P2b-ftmf-k1-{P.SEEDS[0]}.json").exists()


def test_train_ft_h4_refuses_another_recipe(tmp_path, monkeypatch):
    _world(tmp_path, monkeypatch, _lists())
    for kw in ({"masked": False}, {"ft_cap": None}, {"real_frac": 0.5}, {"h4": "other"}):
        with pytest.raises(SystemExit):
            P.cmd_train_ft(_ft_args(**kw))
