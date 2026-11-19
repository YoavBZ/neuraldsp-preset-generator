"""The learning-curve diagnostic's declared table, the user's heard-size rule, the noise check, the halves and their
guard, the runs' refusals and the ladder's new rows (`learn/half_data.py`, `docs/half-data-plan.md`). Pure: runs on the
light CI runner (no numpy)."""
import pytest

from learn import half_data as H
from learn import preset_ladder as L


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


# --- the table and the user's rule ------------------------------------------------------------------------------------

def test_d_table_is_whole_as_declared():
    H.table_guard()
    want = {("cost", "holds"): "D-data", ("cost", "fails"): "D-noise", ("gain", "holds"): "D-odd",
            ("gain", "fails"): "D-noise", ("unreadable", "holds"): "D-unreadable",
            ("unreadable", "fails"): "D-unreadable", ("short", "holds"): "D-short", ("short", "fails"): "D-short"}
    assert {(h, n): H.d_cell(h, n)[0] for h in H.HEARD for n in H.NOISE} == want


@pytest.mark.parametrize("cut", [slice(0, -1), slice(1, None)])
def test_the_guard_refuses_a_broken_table(monkeypatch, cut):
    monkeypatch.setattr(H, "D_TABLE", H.D_TABLE[cut])
    with pytest.raises(SystemExit):
        H.table_guard()


def test_a_doubled_cell_refuses(monkeypatch):
    monkeypatch.setattr(H, "D_TABLE", H.D_TABLE + ((("short",), ("holds",), "D-short", "x"),))
    with pytest.raises(SystemExit):
        H.table_guard()


@pytest.mark.parametrize("row,want", [
    (_iv(0.02, -0.01, 0.04), "unreadable"),       # the interval inside +-0.05: not readable by the score
    (_iv(0.03, 0.01, 0.05), "unreadable"),        # decided, but inside +-0.05: still not readable
    (_iv(-0.03, -0.05, -0.01), "unreadable"),
    (_iv(0.08, 0.051, 0.11), "cost"),             # decided, its lower end over 0.05
    (_iv(0.10, 0.02, 0.18), "cost"),              # decided, a gap of 0.1 or more
    (_iv(0.07, 0.03, 0.11), "short"),             # decided, but neither: under the user's rule
    (_iv(0.03, -0.03, 0.09), "short"),            # undecided, reaching past 0.05: underpowered
    (_iv(-0.08, -0.11, -0.051), "gain"),
    (_iv(-0.10, -0.18, -0.02), "gain"),
    (_iv(-0.07, -0.11, -0.03), "short"),
    (_iv(0.0, -0.06, 0.06), "short"),
])
def test_heard_reading_follows_the_users_rule(row, want):
    assert H.heard_reading(row) == want


def test_heard_reading_needs_an_interval():
    assert H.heard_reading(None) is None and H.heard_reading({"mean": 0.1}) is None
    assert (H.SMALL, H.BIG) == (0.05, 0.10) and H.SMALL == L.SMALL


def test_the_noise_check():
    w, b, u = _iv(0.1, 0.02, 0.2), _iv(-0.1, -0.2, -0.02), _iv(0.0, -0.1, 0.1)
    assert H.noise_check("cost", w, w) == "holds"
    assert H.noise_check("cost", w, u) == "fails" and H.noise_check("cost", w, None) == "fails"
    assert H.noise_check("gain", b, b) == "holds" and H.noise_check("gain", b, w) == "fails"
    assert H.noise_check("unreadable", None, None) == H.noise_check("short", u, u) == "holds"


def _rows(h, h_a=None, h_b=None, cen=None):
    out = {"H": {"deciding_pool": h}}
    if h_a is not None:
        out["H_a"] = {"deciding_pool": h_a}
    if h_b is not None:
        out["H_b"] = {"deciding_pool": h_b}
    if cen is not None:
        out["full vs cen"] = {"deciding_pool": cen}
    return out


def test_d_outcome_cells():
    w = _iv(0.09, 0.06, 0.12)
    got = H.d_outcome(_rows(w, w, w, _iv(0.003, -0.05, 0.06)))
    assert got["code"] == "D-data" and got["heard"] == "cost" and got["noise"] == "holds"
    d = got["doublings_to_goal"]
    assert d["at_mean"] == pytest.approx((0.003 + 0.06) / 0.09) and d["at_hi90"] == pytest.approx(0.063 / 0.12)
    assert d["at_lo90"] == pytest.approx(0.063 / 0.06)
    assert H.d_outcome(_rows(w, w, _iv(0.02, -0.02, 0.06)))["code"] == "D-noise"
    assert H.d_outcome(_rows(_iv(0.01, -0.01, 0.03)))["code"] == "D-unreadable"
    assert H.d_outcome(_rows(_iv(0.03, -0.02, 0.08)))["code"] == "D-short"
    g = _iv(-0.12, -0.16, -0.08)
    assert H.d_outcome(_rows(g, g, g))["code"] == "D-odd"
    with pytest.raises(SystemExit):
        H.d_outcome({})


def test_doublings():
    assert H.doublings(0.0, 0.03) == pytest.approx(2.0)
    assert H.doublings(-0.07, 0.03) == 0.0
    assert H.doublings(0.0, 0.0) is None and H.doublings(0.0, -0.01) is None and H.doublings(None, 0.1) is None


def test_the_rows_are_declared():
    assert H.D_ROWS["H"] == ("rc-half-a-xl@-3+rc-half-b-xl@-3", "rc-xl@-3+rc-rep-xl@-3")
    assert H.D_ROWS["H_a"] == ("rc-half-a-xl@-3", "rc-xl@-3") and H.D_ROWS["H_b"] == ("rc-half-b-xl@-3", "rc-rep-xl@-3")
    assert H.D_BESIDE["H raw"] == ("half-a-xl@-3+half-b-xl@-3", "xl@-3+rep-xl@-3")
    assert H.D_BESIDE["full spread"] == ("rc-rep-xl@-3", "rc-xl@-3")


def test_geo_is_the_mean_of_the_log_ratios():
    import math

    fa = H.geo([lambda *a: 2.0, lambda *a: 8.0])
    fb = H.geo([lambda *a: 1.0, lambda *a: 2.0])
    assert math.log(fa(0, 0, 0) / fb(0, 0, 0)) == pytest.approx((math.log(2 / 1) + math.log(8 / 2)) / 2)
    assert H.geo([lambda *a: 2.0, lambda *a: None])(0, 0, 0) is None


# --- the halves -------------------------------------------------------------------------------------------------------

def _ents(spec):
    """spec: [(set, unit, fold, rig, cls, di)] -> (entries, prt_of)."""
    ents, prt = [], {}
    for s, u, f, rig, c, di in spec:
        ents.append({"set": s, "unit": u, "fold": f, "row": True, "ids": {("di", di)}, "di": di})
        prt[u] = {"rig": rig, "cls": c}
    return ents, (lambda e: prt[e["unit"]])


def test_chains_group_units_and_take_the_common_class():
    ents, prt_of = _ents([("bks", "u1", 0, "r1", "clean", "d1"), ("bks", "u2", 0, "r1", "clean", "d1"),
                          ("cap1", "c1#a", 1, "cap/c1", "crunch", "d2"), ("cap1", "c1#b", 1, "cap/c1", "clean", "d2"),
                          ("cap1", "c1#c", 1, "cap/c1", "crunch", "d2")])
    ch = H.chains_of(ents, prt_of)
    assert ch[("bks", "r1")]["units"] == ["u1", "u2"] and ch[("bks", "r1")]["fold"] == 0
    assert ch[("cap1", "cap/c1")]["cls"] == "crunch"
    ents2, prt2 = _ents([("bks", "u1", 0, "r1", "clean", "d1"), ("bks", "u2", 1, "r1", "clean", "d1")])
    with pytest.raises(SystemExit, match="several folds"):
        H.chains_of(ents2, prt2)


def _goat(n_per=4):
    spec = [("goat", f"g{f}{c}{i}", f, f"g{f}{c}{i}", c, f"d{f}{c}{i}") for f in range(4) for c in ("clean", "crunch")
            for i in range(n_per)]
    return _ents(spec)


def test_a_draw_halves_each_stratum_and_is_seeded():
    ents, prt_of = _goat(5)
    ch = H.chains_of(ents, prt_of)
    a = H.draw(ch, 0)
    assert a == H.draw(ch, 0) and a != H.draw(ch, 1)
    for f in range(4):
        for c in ("clean", "crunch"):
            n = sum(1 for k in a if ch[k]["fold"] == f and ch[k]["cls"] == c)
            assert n in (2, 3)                                   # five chains: two or three kept, the rest in B


def test_the_guard_needs_every_set_with_two_chains_in_both_halves():
    ents, prt_of = _goat(2)
    ch = H.chains_of(ents, prt_of)
    records = {e["unit"]: ["pr12"] for e in ents}
    cls_of = {e["unit"]: prt_of(e)["cls"] for e in ents}
    keep_all = sorted(ch)                                        # half B empty: refused everywhere
    bad = H.guard(ch, keep_all, ents, records, cls_of)
    assert any("half B: no goat record" in b for b in bad) and any("outside" in b for b in bad)
    j, kept, _ = H.choose(ch, ents, records, cls_of)
    assert H.guard(ch, kept, ents, records, cls_of) == []


def test_one_chain_of_a_set_in_a_run_is_not_required_in_both_halves():
    spec = [("goat", f"g{f}{c}{i}", f, f"g{f}{c}{i}", c, f"d{f}{c}{i}") for f in range(4) for c in ("clean", "crunch")
            for i in range(2)]
    spec += [("panel", "p0", 0, "p0", "clean", "pd0")]           # one panel chain: in one half only
    ents, prt_of = _ents(spec)
    ch = H.chains_of(ents, prt_of)
    records = {e["unit"]: ["pr12"] for e in ents}
    cls_of = {e["unit"]: prt_of(e)["cls"] for e in ents}
    j, kept, _ = H.choose(ch, ents, records, cls_of)
    assert H.guard(ch, kept, ents, records, cls_of) == []


def test_an_amp_class_cell_lost_by_a_half_is_refused():
    ents, prt_of = _goat(2)
    ch = H.chains_of(ents, prt_of)
    cls_of = {e["unit"]: prt_of(e)["cls"] for e in ents}
    only = sorted(ch)[0]
    records = {e["unit"]: (["ac20"] if (e["set"], prt_of(e)["rig"]) == only else ["pr12"]) for e in ents}
    bad = H.guard(ch, [k for k in sorted(ch) if k != only], ents, records, cls_of)
    assert any("half A: no (ac20, " in b for b in bad) and not any("half B: no (ac20" in b for b in bad)


def test_keep_filter_drops_training_units_outside_the_half_only():
    tr = [{"unit": "a"}, {"unit": "b"}, {"unit": "c"}]
    assert H.keep_filter(tr, frozenset({"a", "c"})) == [{"unit": "a"}, {"unit": "c"}]


def test_selection_sha_covers_the_halves():
    sel = {"halves": {"A": {"chains": [["goat", "x"]], "units": ["x"]}, "B": {"chains": [["goat", "y"]], "units": ["y"]}}}
    a = H.selection_sha(sel)
    sel["halves"]["B"]["units"] = ["z"]
    assert H.selection_sha(sel) != a


# --- the runs ---------------------------------------------------------------------------------------------------------

def test_the_arms_match_r_all_and_r_rep():
    from learn import stem_finetune as S

    assert H.ARMS["a"]["seeds"] == {sd: sd for sd in S.R_ALL_SEEDS}
    assert H.ARMS["b"]["seeds"] == S.REP_SEEDS
    assert {H.ARMS[a]["half"] for a in H.ARMS} == {"A", "B"}
    assert H.HALF_RATE == S.REP_RATE
    for b in ("C3r-all", "C3r-rep", "C3r-replay") + S.PROTECTED_BASES:
        assert b in H.PROTECTED_BASES
    for a in H.ARMS:
        assert not any(H.ARMS[a]["base"].startswith(b + "-") for b in H.PROTECTED_BASES)
        assert len(H.half_inner_keys(a)) == 8


def test_the_run_refusal():
    ok = dict(c3r="all", k=0, inner=True, base="C3r-all")
    assert H.half_refusal("a", seed=20261042, **ok) is None
    assert H.half_refusal("b", seed=20261181, **ok) is None
    assert "--seed in" in H.half_refusal("a", seed=20261181, **ok)
    assert "--seed in" in H.half_refusal("b", seed=20261042, **ok)
    assert "--c3r all" in H.half_refusal("a", seed=20261042, **dict(ok, c3r="ctl"))
    assert "--c3r all" in H.half_refusal("a", seed=20261042, **dict(ok, base="C3r-allK"))
    assert "fold runs only" in H.half_refusal("a", seed=20261042, **dict(ok, k=None))
    assert "separate" in H.half_refusal("a", seed=20261042, rep="rep", **ok)
    assert H.half_refusal("c", seed=20261042, **ok)
    assert H.half_w_seed("b", 20261181) == 20261042 and H.half_w_seed("a", 20261043) == 20261043


def test_the_write_refusal():
    never = lambda f: False  # noqa: E731
    assert H.half_write_refusal("a", "C3r-half-a-k0", 20261042, False, never) is None
    assert "not arm a's name" in H.half_write_refusal("a", "C3r-all-k0", 20261042, False, never)
    assert "not arm b's name" in H.half_write_refusal("b", "C3r-half-a-k0", 20261181, False, never)
    pt = lambda f: f.endswith("-final.pt")  # noqa: E731
    assert "already exist" in H.half_write_refusal("a", "C3r-half-a-k1", 20261042, False, pt)
    assert H.half_write_refusal("a", "C3r-half-a-k1-inner-cap300", 20261042, True, pt) is None


def test_same_recipe():
    ref = {"lr": 1e-4, "cap": 300, "masked": True, "real_held_ids": [1], "init": {"sha256": "w"},
           "train_ids": [0, 1, 5], "ft_train_ids": [5]}
    assert H.same_recipe(dict(ref, train_ids=[0, 1, 6], ft_train_ids=[6]), ref) == []
    assert H.same_recipe(dict(ref, init={"sha256": "x"}), ref) == ["init"]
    assert H.same_recipe(dict(ref, train_ids=[0, 6], ft_train_ids=[6]), ref) == ["plugin train_ids"]
    assert H.same_recipe(dict(ref, real_held_ids=[2]), ref) == ["real_held_ids"]


# --- the ladder's new rows --------------------------------------------------------------------------------------------

def test_the_ladders_half_rows_carry_their_own_phase():
    assert L.row_info("half-a-xl@-3") == {"stage": 2, "kind": "model", "style": "product", "feats": "xl@-3",
                                          "model": "half-a", "phase": H.PHASE_L6_HALF}
    assert L.row_info("sic-half-b-xl@-3")["phase"] == H.PHASE_L6_HALF
    assert L.row_info("rc-half-a-xl@-3")["phase"] == H.PHASE_L6_HALF
    assert L.rc_sources("rc-half-b-xl@-3") == ["half-b-xl@-3", "sic-half-b-xl@-3", "cen"]
    assert L.row_info("rep-xl@-3")["phase"] == "phase_l6_noise"                  # stage N's rows unchanged
    assert L.row_info("rc-rep-xl@-3")["phase"] == "phase_l6_noise"
    assert set(H.HALF_ROWS) == set(L.L6H_MODEL_ROWS) and set(H.RC_HALF_ROWS) == set(L.L6H_RC_ROWS)
    with pytest.raises(SystemExit):
        L.row_info("half-c-xl@-3")


@pytest.mark.parametrize("missing,cmd", [("phase_s6_half", "cmd_select"), ("phase_s6_half", "cmd_answers"),
                                         ("phase_l6_half", "cmd_report")])
def test_every_command_refuses_without_its_ledger_phases(monkeypatch, missing, cmd):
    import copy

    from learn import pipeline_fix as P

    pf, pl = copy.deepcopy(P.ledger_entry()), copy.deepcopy(L.ledger_entry())
    assert H.PHASE_HALF in pf and H.PHASE_L6_HALF in pl                           # declared in this PR
    (pl if missing == H.PHASE_L6_HALF else pf).pop(missing)
    monkeypatch.setattr(P, "ledger_entry", lambda: pf)
    monkeypatch.setattr(L, "ledger_entry", lambda: pl)
    with pytest.raises(SystemExit, match=f"no {missing}: declare it before running"):
        getattr(H, cmd)(None)


def test_the_read_leaves_out_silent_waves_only():
    def ru(s, di):
        return {"set": s, "prt": {"di": di}}
    us = [ru("panel", "panel/x/Silent Waves"), ru("panel", "panel/x/Drowning"), ru("goat", "goat/Silent Waves"),
          ru("panel", "panel/y/RAW_01")]
    assert [u["prt"]["di"] for u in H.read_parts(us)] == ["panel/x/Drowning", "goat/Silent Waves", "panel/y/RAW_01"]
    assert len(H.read_parts(us, H.BAND_BESIDE)) == 2
