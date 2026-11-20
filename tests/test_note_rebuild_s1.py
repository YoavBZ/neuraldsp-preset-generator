"""Stage 1 of the note rebuild (`learn/note_rebuild_s1.py`): the carrying subset, the gate read from the replay's own
report and main's ledger, the ear check's refusal, the record's timeline, the tertiles, stage 3's blind setting and card
rule, and every command's refusals. Pure: runs on the light CI runner (no numpy) except where marked."""
import pytest

from learn import note_rebuild_s1 as S


def _report(code="R-dry-only", picks="abc", both=()):
    return {"picks_sha256": picks, "outcome": {"code": code, "both_notes": list(both)}}


REPLAY_MAIN = {"phase_replay_picks": {"sha256": "abc"}, "phase_replay_outcome": "audited"}


def test_gate_goes_only_on_a_continue_code():
    assert S.gate_refusal(_report(), REPLAY_MAIN, {}) is None
    assert S.gate_refusal(_report("R-alone"), REPLAY_MAIN, {}) is None
    for code in ("R-dry", "R-stem", "R-undecided", "singles-triggered", "incomplete"):
        assert "stage 1 does not run" in S.gate_refusal(_report(code), REPLAY_MAIN, {})


def test_gate_refusals():
    assert "not been read" in S.gate_refusal(None, REPLAY_MAIN, {})
    assert "hashed on main" in S.gate_refusal(_report(picks="zzz"), REPLAY_MAIN, {})
    assert "hashed on main" in S.gate_refusal(_report(), {}, {})
    assert "audited" in S.gate_refusal(_report(), {"phase_replay_picks": {"sha256": "abc"}}, {})
    both = _report(both=["both-full reads fails"])
    assert "Both-row" in S.gate_refusal(both, REPLAY_MAIN, {})
    assert S.gate_refusal(both, REPLAY_MAIN, {S.PHASE_BOTH_GO: "the user's go"}) is None


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


@pytest.mark.parametrize("cmd", ["cmd_subset", "cmd_build", "cmd_clips", "cmd_render", "cmd_pick", "cmd_score"])
def test_every_command_refuses_without_the_phase(monkeypatch, cmd):
    from learn import note_rebuild as NR

    monkeypatch.setattr(NR, "ledger_entry", lambda: {"test_id": NR.LEDGER_ID, NR.PHASE_P: "declared"})
    with pytest.raises(SystemExit, match="phase_nr_1"):
        getattr(S, cmd)(type("A", (), {"shard": (0, 1)})())
