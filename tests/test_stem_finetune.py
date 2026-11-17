"""Step 6's declared tables, the noise rule, R-rep's names and refusals, the knob gauge and the ladder's new rows
(`learn/stem_finetune.py`, `docs/stem-finetune-plan.md`). Pure: runs on the light CI runner (no numpy)."""
import pytest

from learn import preset_ladder as L
from learn import stem_finetune as S

R = S.READINGS


def _iv(r):
    return ({"lo90": -0.2, "hi90": -0.01} if r == "better" else
            {"lo90": 0.01, "hi90": 0.2} if r == "worse" else {"lo90": -0.1, "hi90": 0.1})


def _rows(table, **kw):
    return {table[k]: {"deciding_pool": _iv(v)} for k, v in kw.items()}


# --- the tables --------------------------------------------------------------------------------------------------------

def test_every_table_is_whole_as_declared():
    S.table_guard()
    assert [c for c, _, _ in S.S0_TABLE] == ["S0-fail", "S0-ok"]
    assert {n: S.n_cell(n)[0] for n in R} == {"better": "N-loud", "undecided": "N-quiet", "worse": "N-loud"}
    want = {("better", "better"): "S6-adopt", ("better", "undecided"): "S6-user", ("better", "worse"): "S6-impossible",
            ("undecided", "better"): "S6-build", ("worse", "better"): "S6-build",
            ("undecided", "undecided"): "S6-level", ("worse", "undecided"): "S6-level",
            ("undecided", "worse"): "S6-worse", ("worse", "worse"): "S6-worse"}
    for g in R:
        for o in R:
            assert S.s6_cell(g, o)[0] == want[(g, o)]


def test_p_table_holds_each_of_the_27_triples_once():
    got = {(p, p2, q): S.p_cell(p, p2, q)[0] for p in R for p2 in R for q in R}
    assert len(got) == 27
    assert got[("better", "better", "better")] == got[("better", "better", "undecided")] == "P-go"
    assert got[("better", "better", "worse")] == "P-aim"
    assert all(got[("undecided", p2, q)] == "P-flat" for p2 in R for q in R)
    assert all(got[("worse", "worse", q)] == "P-worse" for q in R)
    assert all(got[("better", p2, q)] == "P-noise" for p2 in ("undecided", "worse") for q in R)
    assert all(got[("worse", p2, q)] == "P-noise" for p2 in ("better", "undecided") for q in R)


@pytest.mark.parametrize("name,cut", [("N_TABLE", slice(0, 1)), ("P_TABLE", slice(1, None)),
                                      ("S6_TABLE", slice(0, -1)), ("S0_TABLE", slice(1, None))])
def test_the_guard_refuses_a_broken_table(monkeypatch, name, cut):
    monkeypatch.setattr(S, name, getattr(S, name)[cut])
    with pytest.raises(SystemExit):
        S.table_guard()


def test_a_doubled_cell_refuses(monkeypatch):
    monkeypatch.setattr(S, "N_TABLE", S.N_TABLE + ((("worse",), "N-loud", "x"),))
    with pytest.raises(SystemExit):
        S.table_guard()


def test_s0_fails_on_any_failed_or_missing_control():
    assert S.s0_cell({"a": True, "b": True})[0] == "S0-ok"
    assert S.s0_cell({"a": True, "b": False})[0] == "S0-fail"
    assert S.s0_cell({})[0] == "S0-fail"
    assert S.s0_cell({"a": None})[0] == "S0-fail"


def test_n_outcome_reads_n_on_the_deciding_pool_and_refuses_without_it():
    assert S.n_outcome(_rows(S.N_ROWS, N="undecided"))["code"] == "N-quiet"
    assert S.n_outcome(_rows(S.N_ROWS, N="worse"))["code"] == "N-loud"
    with pytest.raises(SystemExit):
        S.n_outcome({})


def test_the_noise_rule_and_s6_outcome():
    assert S.noise_rule("better", "better") and not S.noise_rule("better", "undecided")
    assert not S.noise_rule("worse", None)
    got = S.s6_outcome(_rows(S.S6_ROWS, G="better", O="better", O2="better"))
    assert got["code"] == "S6-adopt" and got["fires"]
    got = S.s6_outcome(_rows(S.S6_ROWS, G="undecided", O="better", O2="undecided"))
    assert got["code"] == "S6-build" and not got["fires"] and got["next"] == S.NOISE_HELD
    got = S.s6_outcome(_rows(S.S6_ROWS, G="worse", O="better"))                # O2 missing: the action is held
    assert not got["fires"] and got["noise"]["O2"] is None
    got = S.s6_outcome(_rows(S.S6_ROWS, G="undecided", O="undecided", W="better", W2="better"))
    assert got["code"] == "S6-level" and got["sub"] == S.S6_LEVEL_SUB["W and W2 better"]
    got = S.s6_outcome(_rows(S.S6_ROWS, G="undecided", O="undecided", W="better", W2="undecided"))
    assert got["sub"] == S.S6_LEVEL_SUB["otherwise"]
    assert S.s6_outcome(_rows(S.S6_ROWS, G="better", O="undecided"))["code"] == "S6-user"
    with pytest.raises(SystemExit):
        S.s6_outcome(_rows(S.S6_ROWS, G="better", O="worse"))                  # the impossible cell stops
    with pytest.raises(SystemExit):
        S.s6_outcome(_rows(S.S6_ROWS, G="better"))                             # a missing action row refuses


def test_stage_n_reads_the_declared_rows_only():
    assert S.N_ROWS == {"N": "rep-xl@-3 - xl@-3"}
    assert S.N_BESIDE == ("rc-rep-xl@-3 - rc-xl@-3", "rc-rep-xl@-3 - cen", "ens4-xl@-3 - xl@-3")
    rows = {n for r in (S.N_ROWS["N"],) + S.N_BESIDE for n in r.split(" - ")}
    assert not any(r.startswith("rep-mix") for r in rows)                      # rep-mix@-3 dropped (the review)


# --- R-rep's names: no R-all file can be written ---------------------------------------------------------------------

def _r_all_names():
    out = []
    for k in range(4):
        for sd in S.R_ALL_SEEDS:
            out += [f"C3r-all-k{k}-inner-cap300-{sd}.json", f"C3r-all-k{k}-{sd}.json", f"C3r-all-k{k}-{sd}-final.pt"]
    return out + [f"C3r-all-{sd}.json" for sd in S.R_ALL_SEEDS] + [f"C3r-all-{sd}-final.pt" for sd in S.R_ALL_SEEDS]


def test_no_stage_n_run_can_carry_an_r_all_name():
    rep, replay = S.rep_names("rep"), S.rep_names("replay")
    assert len(rep) == 24 and len(set(rep)) == 24 and len(replay) == 3
    assert not (set(rep) | set(replay)) & set(_r_all_names())
    for n in rep + replay:
        assert not any(n.startswith(b + "-") for b in S.PROTECTED_BASES)
    assert set(S.REP_SEEDS) & set(S.R_ALL_SEEDS) == set()
    assert sorted(S.REP_SEEDS.values()) == sorted(S.R_ALL_SEEDS)              # each W state once
    assert S.REPLAY[1] in S.R_ALL_SEEDS


def test_the_write_refusal_stops_a_wrong_name_or_any_existing_file():
    never = lambda f: False  # noqa: E731
    assert S.rep_write_refusal("rep", "C3r-rep-k0", 20261181, False, never) is None
    assert S.rep_write_refusal("rep", "C3r-rep-k0-inner-cap300", 20261182, True, never) is None
    assert "not a rep run's name" in S.rep_write_refusal("rep", "C3r-all-k0", 20261181, False, never)
    assert "not a replay run's name" in S.rep_write_refusal("replay", "C3r-all-k3", 20261043, False, never)
    assert "R-all's seed" in S.rep_write_refusal("rep", "C3r-rep-k0", 20261042, False, never)
    pt = lambda f: f.endswith("-final.pt")  # noqa: E731
    assert "already exist" in S.rep_write_refusal("rep", "C3r-rep-k1", 20261181, False, pt)
    assert S.rep_write_refusal("rep", "C3r-rep-k1-inner-cap300", 20261181, True, pt) is None
    assert "already exist" in S.rep_write_refusal("replay", "C3r-replay-k3", 20261043, False, lambda f: True)


def test_the_run_refusal():
    ok = dict(c3r="all", k=0, inner=True, base="C3r-all")
    assert S.rep_refusal("rep", seed=20261181, **ok) is None
    assert "R-all's seeds are R-all's" in S.rep_refusal("rep", seed=20261042, **ok)
    assert "--c3r all" in S.rep_refusal("rep", seed=20261181, **dict(ok, c3r="ctl"))
    assert "--c3r all" in S.rep_refusal("rep", seed=20261181, **dict(ok, base="C3r-allK"))   # FTm's fallback recipe
    assert "fold runs only" in S.rep_refusal("rep", seed=20261181, **dict(ok, k=None))
    assert S.rep_refusal("replay", seed=20261043, **dict(ok, k=3)) is None
    assert "fold 3" in S.rep_refusal("replay", seed=20261043, **ok)
    assert "fold 3" in S.rep_refusal("replay", seed=20261042, **dict(ok, k=3))
    assert S.rep_refusal("other", seed=20261181, **ok)
    assert S.rep_w_seed("rep", 20261181) == 20261042 and S.rep_w_seed("rep", 20261182) == 20261043
    assert S.rep_w_seed("replay", 20261043) == 20261043
    assert S.rep_inner_keys("replay") == [(3, 20261043)] and len(S.rep_inner_keys("rep")) == 8


# --- the knob gauge ----------------------------------------------------------------------------------------------------

def test_moves_is_the_knob_reads_rms_move_and_spread_between_parts():
    va = {(("u1", "A"), "drive"): ("c", 0.5), (("u2", "A"), "drive"): ("c", 0.7), (("u1", "A"), "tone"): ("d", 0.1)}
    vb = {(("u1", "A"), "drive"): ("c", 0.6), (("u2", "A"), "drive"): ("c", 0.7), (("u3", "A"), "drive"): ("c", 0.0)}
    got = S.moves(va, vb)
    assert got["values"] == 2
    assert got["rms_move"] == pytest.approx((0.1 ** 2 / 2) ** 0.5)
    assert got["rms_between_units"] == pytest.approx(0.1)
    g = S.moves(va, vb, group_of=lambda n: n, group="tone")
    assert g["values"] == 0 and g["rms_move"] is None


# --- the ladder's new rows ---------------------------------------------------------------------------------------------

def test_the_ladders_new_rows_carry_their_own_phase_and_leave_the_old_ones_alone():
    assert L.row_info("rep-xl@-3") == {"stage": 2, "kind": "model", "style": "product", "feats": "xl@-3",
                                       "model": "rep", "phase": S.PHASE_L6_NOISE}
    assert L.row_info("ens4-xl@-3")["model"] == "ens4"
    assert L.row_info("sic-rep-xl@-3") == {"stage": 2, "kind": "constant", "style": None, "base": "rep-xl@-3",
                                           "phase": S.PHASE_L6_NOISE}
    assert L.row_info("rc-rep-xl@-3")["phase"] == S.PHASE_L6_NOISE
    assert L.rc_sources("rc-rep-xl@-3") == ["rep-xl@-3", "sic-rep-xl@-3", "cen"]
    assert L.L6_PHASE == S.PHASE_L6_NOISE
    assert "phase" not in L.row_info("sic-xl@-3") and L.row_info("rc-xl@-3")["phase"] == L.RC_PHASE
    assert L.rc_sources("rc-xl@-3") == ["xl@-3", "sic-xl@-3", "cen"]
    assert set(L.RC_ROWS) == {"rc-mix@-3", "rc-xl@-3", "rca-mix@-3", "rcs-mix@-3", "rcs-xl@-3"}   # report-rc unchanged
    with pytest.raises(SystemExit):
        L.row_info("sic-ens5-xl@-3")
    with pytest.raises(SystemExit):
        L.row_info("rep-mix@-3")
