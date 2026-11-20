"""Stage 1 of the note rebuild (`learn/note_rebuild_s1.py`): the carrying subset, the gate read from the replay's own
report and main's ledger, the ear check's refusal, the record's timeline, the tertiles, stage 3's blind setting and card
rule, and every command's refusals. Pure: runs on the light CI runner (no numpy) except where marked."""
import pytest

from learn import note_rebuild_s1 as S


def _report(code="R-dry-only", picks="abc", both=(), via="avg+mild"):
    return {"picks_sha256": picks, "outcome": {"code": code, "both_notes": list(both), "via": via}}


def _main(code="R-dry-only", singles=None):
    m = {"phase_replay_picks": {"sha256": "abc"}, "phase_replay_outcome": f"audited 2026-11-21: {code}"}
    if singles:
        m["phase_replay_picks_singles"] = {"sha256": singles}
    return m


TRIGGERED = {"picks_sha256": "abc", "outcome": {"code": "singles-triggered"}}


def test_gate_goes_only_on_a_continue_code():
    assert S.gate_refusal(_report(), _main(), {}) is None
    assert S.gate_refusal(_report("R-alone"), _main("R-alone"), {}) is None
    for code in ("R-dry", "R-stem", "R-undecided", "incomplete"):
        assert "stage 1 does not run" in S.gate_refusal(_report(code), _main(code), {})


def test_gate_refusals():
    assert "not been read" in S.gate_refusal(None, _main(), {})
    assert "hashed on main" in S.gate_refusal(_report(picks="zzz"), _main(), {})
    assert "hashed on main" in S.gate_refusal(_report(), {}, {})
    assert "audited" in S.gate_refusal(_report(), {"phase_replay_picks": {"sha256": "abc"}}, {})
    both = _report(both=["both-full reads fails"])
    assert "Both-row" in S.gate_refusal(both, _main(), {})
    assert S.gate_refusal(both, _main(), {S.PHASE_BOTH_GO: "the user's go"}) is None


def test_gate_needs_the_audited_code_itself():
    assert "exactly" in S.gate_refusal(_report(), _main("R-undecided"), {})       # an audit correction closes it
    assert "exactly" in S.gate_refusal(_report(), {**_main(), "phase_replay_outcome": "R-alone or R-dry-only"}, {})
    assert S.gate_refusal(_report(), {**_main(), "phase_replay_outcome": {"code": "R-dry-only"}}, {}) is None
    assert S.recorded_codes("R-dry-only, audited") == {"R-dry-only"}
    assert S.recorded_codes("code R-dry") == {"R-dry"}


def test_gate_on_the_single_blur_path():
    singles = {"picks_sha256": "s1", "outcome": {"code": "R-alone", "via": "avg", "both_notes": []}}
    assert "not read yet" in S.gate_refusal(TRIGGERED, _main("R-alone", "s1"), {})
    assert S.gate_refusal(TRIGGERED, _main("R-alone", "s1"), {}, singles) is None                # a passing single
    assert "single-blur report" in S.gate_refusal(TRIGGERED, _main("R-alone", "zz"), {}, singles)
    assert "single-blur report" in S.gate_refusal(TRIGGERED, _main("R-alone"), {}, singles)
    stop = {"picks_sha256": "s1", "outcome": {"code": "R-dry", "via": None}}
    assert "stage 1 does not run" in S.gate_refusal(TRIGGERED, _main("R-dry", "s1"), {}, stop)    # both singles fail
    noted = {"picks_sha256": "s1", "outcome": {"code": "R-dry-only", "via": "mild",
                                               "both_notes": ["mild-both-full reads undecided"]}}
    assert "Both-row" in S.gate_refusal(TRIGGERED, _main("R-dry-only", "s1"), {}, noted)
    assert S.deciding_outcome(TRIGGERED, singles) == (singles["outcome"], "singles")
    assert S.deciding_outcome(_report(), None)[1] == "main"


def test_comparison_dry():
    assert S.comparison_dry({"via": "avg+mild"}) == ("avg+mild", [])
    assert S.comparison_dry({"via": "mild"}) == ("mild", [])
    assert S.comparison_dry({"via": "avg, mild"}) == ("avg", ["mild"])
    assert S.comparison_dry({}) == ("avg+mild", [])
    with pytest.raises(ValueError):
        S.comparison_dry({"via": "true"})


def test_beside_sets_and_safe_readings():
    parts = [{"pkey": "a", "alignment_f": 0.0, "reader_ok": True}, {"pkey": "b", "alignment_f": 0.8, "reader_ok": False},
             {"pkey": "c", "alignment_f": 0.9, "reader_ok": None}]
    b = S.beside_sets(parts)
    assert b[S.BESIDE_F0] == ["b", "c"] and b[S.BESIDE_READER] == ["a", "c"]
    iv = {"mean": -0.2, "lo90": -0.3, "hi90": -0.12}
    assert S.safe_reading(iv, iv) == "passes"
    assert S.safe_reading({"mean": None}, iv) is None
    assert S.n1_outcome({"nr-plain": None, "nr-level": "passes"})["code"] == "N1-incomplete"
    assert S.n1_outcome({"nr-plain": "fails", "nr-level": "passes"})["arm"] == "nr-level"


def _build(fails, n=60):
    """fails: {arm: number of failing parts}."""
    parts = {}
    for j in range(n):
        parts[f"p{j:02d}"] = {"arms": {a: {"precheck": {"ok": j >= fails.get(a, 0)}} for a in S.NR.ARMS}}
    return {"parts": parts}


def test_precheck_refusal():
    ci = {"checks": [{"file": "x", "ok": True}]}
    assert S.precheck_refusal(_build({}), ci) is None
    assert S.precheck_refusal(_build({"nr-plain": 6, "nr-level": 6}), ci) is None              # 10%: renders
    assert "systematic" in S.precheck_refusal(_build({"nr-plain": 7}), ci)                       # over 10%
    assert "systematic" in S.precheck_refusal(_build({"nr-level": 7}), ci)
    assert S.precheck_refusal(_build({"nr-oracle": 60}), ci) is None                             # never blocks
    assert "build" in S.precheck_refusal(None, ci)
    assert "clips" in S.precheck_refusal(_build({}), None)
    assert "clips' pre-checks fail" in S.precheck_refusal(_build({}), {"checks": [{"file": "x", "ok": False}]})
    assert "missing" in S.precheck_refusal(_build({}), {"checks": []})
    assert S.tuning_diff(49.0, -49.0) == pytest.approx(-2.0)


def test_precheck_failures_and_beside_row():
    b = _build({"nr-plain": 2, "nr-oracle": 3})
    f = S.precheck_failures(b)
    assert f["nr-plain"] == ["p00", "p01"] and f["nr-level"] == [] and f["nr-oracle"] == ["p00", "p01", "p02"]
    parts = [{"pkey": k, "alignment_f": 0.8, "reader_ok": True} for k in b["parts"]]
    keep = S.beside_sets(parts, f)[S.BESIDE_PRECHECK]
    assert "p00" not in keep and "p01" not in keep and "p02" in keep and len(keep) == 58       # nr-oracle not counted


def test_ear_refusal():
    assert "not recorded" in S.ear_refusal({})
    assert "not recorded" in S.ear_refusal({S.PHASE_EAR: "ok"})
    assert "fault" in S.ear_refusal({S.PHASE_EAR: {"verdict": "fault", "heard": "clicks"}})
    assert S.ear_refusal({S.PHASE_EAR: {"verdict": "ok"}}) is None


def test_carrying_subset():
    parts = [{"pkey": "goat|b", "set": "goat", "unit": "u2", "amp": "ac20"},
             {"pkey": "goat|a", "set": "goat", "unit": "u1", "amp": "ac20"},
             {"pkey": "bks|x", "set": "bks", "unit": "u3", "amp": "pr12"},
             {"pkey": "goat|c", "set": "goat", "unit": "u4", "amp": "sw50r"}]
    units = {"u1|ac20": {"carries": True, "item": "item_1", "window_s": 30.0},
             "u2|ac20": {"carries": False, "item": "item_2", "why": "no fine-aligned MIDI"}}
    keep, out = S.carrying_subset(parts, units)
    assert [k["pkey"] for k in keep] == ["goat|a"] and keep[0]["item"] == "item_1"
    assert out == [{"pkey": "goat|b", "why": "no fine-aligned MIDI"}, {"pkey": "goat|c", "why": "not in true-notes.json"}]


def test_tertiles():
    e = S.tertile_edges([0.9, 0.1, 0.5, 0.3, 0.7, 0.8, None])
    assert e == [0.5, 0.8]
    assert [S.group_of(x, e) for x in (0.1, 0.5, 0.79, 0.8, None)] == [0, 1, 1, 2, None]
    assert S.tertile_edges([0.1, 0.2]) == []


def test_stage3_blind_setting_and_cards():
    b = S.blind_setting("goat|a", 23)
    assert 1 <= b <= 22 and b == S.blind_setting("goat|a", 23)
    assert not S.n3_card_eligible(0, b)
    assert not S.n3_card_eligible(b, b)
    assert not S.n3_card_eligible(None, b)
    assert S.n3_card_eligible(next(j for j in range(1, 23) if j != b), b)


def test_ref_on_section():
    np = pytest.importorskip("numpy")
    ref = np.arange(1, 11, dtype=float)
    out = S.ref_on_section(ref, 14, trim=4, delay=1)          # section t holds record t - 3
    assert list(out[:3]) == [0, 0, 0] and out[3] == 1 and out[12] == 10 and out[13] == 0


def test_shards_capped_at_three():
    import argparse

    assert S._shard("2/3") == (2, 3)
    for bad in ("3/3", "0/4"):
        with pytest.raises(argparse.ArgumentTypeError):
            S._shard(bad)


def test_hf_checks():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    rng = np.random.default_rng(5)
    sr = S.NR.SR
    tone = np.sin(2 * np.pi * 220 * np.arange(2 * sr) / sr)
    quiet = np.concatenate([tone * 0.5, 1e-4 * rng.standard_normal(sr)])
    hissy = np.concatenate([tone * 0.5, 1e-2 * rng.standard_normal(sr)])
    assert S.gap_floor_diff(quiet, quiet) == pytest.approx(0.0, abs=1e-6)
    assert S.gap_floor_diff(quiet, hissy) is None or S.gap_floor_diff(quiet, hissy) > 6     # hiss over the floor
    clicks = 0.01 * rng.standard_normal(3 * sr)
    for t in (0.5, 1.2, 2.1):
        clicks[int(t * sr):int(t * sr) + 48] += 0.8
    assert S.burst_rate(clicks, []) > 0.9 and S.burst_rate(clicks, [0.5, 1.2, 2.1]) == 0.0


@pytest.mark.parametrize("cmd", ["cmd_subset", "cmd_build", "cmd_clips", "cmd_render", "cmd_pick", "cmd_score"])
def test_every_command_refuses_without_the_phase(monkeypatch, cmd):
    from learn import note_rebuild as NR

    monkeypatch.setattr(NR, "ledger_entry", lambda: {"test_id": NR.LEDGER_ID, NR.PHASE_P: "declared"})
    with pytest.raises(SystemExit, match="phase_nr_1"):
        getattr(S, cmd)(type("A", (), {"shard": (0, 1)})())


def test_declared_subset():
    keys = [f"goat|{j}" for j in range(60)]
    decl = {"draw_sha256": "d", "true_notes_sha256": "t", "parts": 60, "keys_sha256": S.NR.content_sha(sorted(keys))}
    assert "true-notes" in S.subset_refusal("d", keys, decl, true_notes_sha="u")
    assert S.subset_refusal("d", keys, decl, true_notes_sha="t") is None
    assert S.subset_refusal("d", list(reversed(keys)), decl) is None
    assert "draw" in S.subset_refusal("e", keys, decl)
    assert "declared 60" in S.subset_refusal("d", keys[:59], decl)
    assert "declared 60" in S.subset_refusal("d", keys[:59] + ["goat|x"], decl)
    assert S.DECLARED_SUBSET["parts"] == 60 and len(S.DECLARED_SUBSET["keys_sha256"]) == 64


def test_without_f0():
    parts = [{"pkey": "a", "alignment_f": 0.0}, {"pkey": "b", "alignment_f": 0.8}, {"pkey": "c", "alignment_f": None}]
    assert S.without_f0(parts) == ["b", "c"]
