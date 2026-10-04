"""Stage 0b's listening validation: how trials are split into sittings, how answers
are read, and how they are scored against each distance."""

from __future__ import annotations

import math
import pathlib
import random
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_listening_validation as B  # noqa: E402
import plan_listening_validation as P  # noqa: E402
import score_listening_validation as S  # noqa: E402


def _plan():
    tests = [{"kind": "test", "id": f"t{i:02d}", "part": f"p{i}", "first": f"c{i}a",
              "second": f"c{i}b", "disagree": i < 10,
              "log_ratio": {d: -0.3 for d in ("judge", "alm", "judge_union", "v3c")}}
             for i in range(24)]
    for t in tests[:10]:
        t["log_ratio"]["v3c"] = 0.3                     # v3c disagrees on the first ten
    hidden = [{"kind": "hidden_reference", "part": f"h{i}", "first": "reference",
               "second": f"x{i}"} for i in range(3)]
    repeats = [{"kind": "repeat", "of": f"t{i:02d}"} for i in (0, 1, 2)]
    return {"trials": tests + hidden + repeats}


def test_repeats_follow_their_originals_and_each_sitting_has_a_hidden_reference():
    plan = _plan()
    for seed in range(20):
        first, second = B.sittings(list(plan["trials"]), random.Random(seed))
        assert len(first) == len(second) == 15
        ids_first = {t.get("id") for t in first}
        assert all(t["of"] in ids_first for t in second if t["kind"] == "repeat")
        assert not any(t["kind"] == "repeat" for t in first)
        for block in (first, second):
            assert any(t["kind"] == "hidden_reference" for t in block)


def test_every_trial_must_be_answered_once():
    assert S.parse_answers("1: A\n2: b\n3 ?\n", 3) == {1: "A", 2: "B", 3: "?"}
    with pytest.raises(ValueError, match="no answer"):
        S.parse_answers("1: A\n3: B\n", 3)
    with pytest.raises(ValueError, match="twice"):
        S.parse_answers("1: A\n1: B\n2: A\n", 2)


def test_validated_rejected_and_inconclusive_are_where_the_plan_puts_them():
    assert S.binomial_p(16, 22) == pytest.approx(0.02624, abs=1e-5)
    outcomes = {k: S.outcome(k, 22) for k in range(23)}
    assert [k for k, v in outcomes.items() if v == "validated"][0] == 16
    assert max(k for k, v in outcomes.items() if v == "rejected") == 11
    assert outcomes[12] == outcomes[15] == "inconclusive"
    assert S.outcome(11, 11) == "inconclusive"               # too few decided pairs
    assert S.upper_bound(11, 22) < 0.7 < S.upper_bound(12, 22)


def _order_and_keys(plan, pick_first, missed_references=0, seed=0):
    """Every trial in order, keys with random A/B, and answers picking `pick_first`'s side."""
    rng = random.Random(seed)
    order, keys = [], {}
    for n, t in enumerate(plan["trials"], start=1):
        pair = (next(x for x in plan["trials"] if x.get("id") == t["of"])
                if t["kind"] == "repeat" else t)
        order.append({"trial": n, "kind": t["kind"], "id": t.get("id"), "of": t.get("of"),
                      "first": pair["first"], "second": pair["second"]})
        swap = rng.random() < 0.5
        keys[n] = {"blind_key": {"A": "second" if swap else "first",
                                 "B": "first" if swap else "second"}}
    answers = {}
    for row in order:
        label_of = {role: label for label, role in keys[row["trial"]]["blind_key"].items()}
        if row["kind"] == "hidden_reference":
            want = "second" if missed_references > 0 else "first"   # first is the reference
            missed_references -= 1
        else:
            want = "first" if pick_first(row) else "second"
        answers[row["trial"]] = label_of[want]
    return order, keys, answers


def test_a_listener_who_agrees_with_the_judge_validates_it():
    plan = _plan()
    order, keys, answers = _order_and_keys(plan, lambda row: True)  # always the first (closer)
    out = S.score(plan, order, keys, answers)
    assert out["valid"] and out["decided"] == 24
    assert out["agreement"]["judge"]["agree"] == 24 and out["judge"] == "validated"
    assert out["agreement"]["v3c"]["agree"] == 14                  # v3c wrong on its ten
    assert out["judge_vs_v3c_where_they_disagree"]["listener_with_judge"] == 10
    assert all(r["same"] for r in out["repeats"])


def test_missed_hidden_references_void_the_test_and_cant_tell_is_not_half():
    plan = _plan()
    order, keys, answers = _order_and_keys(plan, lambda row: True, missed_references=2)
    void = S.score(plan, order, keys, answers)
    assert not void["valid"] and void["judge"] == "void" and "agreement" not in void
    order, keys, answers = _order_and_keys(plan, lambda row: True)
    hidden = next(r for r in order if r["kind"] == "hidden_reference")
    answers[hidden["trial"]] = "?"                              # one "can't tell" is one miss
    assert S.score(plan, order, keys, answers)["hidden_references_missed"] == [hidden["trial"]]
    order, keys, answers = _order_and_keys(plan, lambda row: True)
    for row in order[:8]:
        answers[row["trial"]] = "?"
    out = S.score(plan, order, keys, answers)
    assert out["decided"] == 16 and out["agreement"]["judge"]["of"] == 16
    assert out["cant_tell_rate"] == pytest.approx(8 / 24)
    assert not math.isnan(out["agreement"]["judge"]["p_one_sided"])


def test_a_listener_who_always_picks_the_other_one_rejects_the_judge():
    plan = _plan()
    order, keys, answers = _order_and_keys(plan, lambda row: False, seed=3)
    assert S.score(plan, order, keys, answers)["judge"] == "rejected"


def test_the_seed_makes_the_judges_choice_a_or_b_as_asked():
    import random as r

    rng = r.Random(1)
    for first_is_a in (True, False) * 5:
        seed = B.seed_for(first_is_a, rng)
        assert (not r.Random(seed).getrandbits(1)) == first_is_a


def _pool(parts=12, candidates=30):
    rng = random.Random(5)
    return {f"part{i}": {"window_s": 0.5, "lag": 0, "candidates": {
        f"c{j}": {d: rng.uniform(1, 10) for d in P.DISTANCES} for j in range(candidates)}}
        for i in range(parts)}


def test_the_draw_keeps_its_rules_and_is_fixed_by_its_seed():
    pool = _pool()
    meta = {p: {"band": f"band{i % 9}"} for i, p in enumerate(pool)}
    one, two = P.draw(pool, meta, 7), P.draw(pool, meta, 7)
    assert one == two
    tests = [t for t in one["trials"] if t["kind"] == "test"]
    assert len(tests) == P.TEST_PAIRS and sum(t["disagree"] for t in tests) >= P.MIN_DISAGREE
    assert len({t["band"] for t in tests}) >= P.MIN_BANDS
    from collections import Counter

    assert max(Counter(t["part"] for t in tests).values()) <= P.PER_PART
    assert max(Counter(c for t in tests for c in (t["first"], t["second"])).values()) \
        <= P.PER_CANDIDATE
    assert all(abs(t["log_ratio"]["judge"]) > one["median_abs_log_ratio"] for t in tests)
    assert P.draw(pool, meta, 8) != one



def test_the_build_keeps_keys_private_and_starts_each_render_on_the_window(tmp_path, monkeypatch):
    import json
    import subprocess

    plan = _plan()
    for t in plan["trials"]:
        if t["kind"] != "repeat":
            t.update(window_s=1.0, lag=480)
    trials = tmp_path / "trials.json"
    trials.write_text(json.dumps(plan))
    panel = tmp_path / "panel"
    panel.mkdir()
    rows = [{"part": t["part"], "candidate": c, "file": str(panel / f"{t['part']}-{c}.wav")}
            for t in plan["trials"] if t["kind"] != "repeat"
            for c in (t["first"], t["second"]) if c != "reference"]
    (panel / "index.json").write_text(json.dumps({"rows": rows}))
    calls = []

    def fake_run(cmd, capture_output, text):
        calls.append(cmd)
        out, key = cmd[cmd.index("--out") + 1], cmd[cmd.index("--key") + 1]
        pathlib.Path(out).write_bytes(b"flac")
        pathlib.Path(key).write_text("{}")
        return subprocess.CompletedProcess(cmd, 0, "reproducible blind assignment seed: 1\n", "")

    monkeypatch.setattr(B.subprocess, "run", fake_run)
    listener, private = tmp_path / "listen", tmp_path / "private"
    monkeypatch.setattr(sys, "argv", ["build", "--trials", str(trials), "--panel-dir", str(panel),
                                      "--crops-dir", str(tmp_path / "crops"),
                                      "--out-dir", str(listener), "--private-dir", str(private)])
    B.main()
    assert sorted(p.name for p in listener.iterdir()) == sorted(
        [f"trial-{n:02d}.flac" for n in range(1, 31)] + ["ANSWERS.md"])
    assert (private / "order.json").exists() and (private / "trials.json").exists()
    assert "seed" in (private / "build-01.log").read_text()
    for cmd in calls:                    # a render starts lag/48000 s before the reference
        ref = float(cmd[cmd.index("--reference-start") + 1])
        for side in ("--a", "--b"):
            path = cmd[cmd.index(side) + 1]
            start = float(cmd[cmd.index(side + "-start") + 1])
            expected = ref if path.endswith("reference.wav") else ref - 480 / 48000
            assert start == pytest.approx(expected)
    with pytest.raises(SystemExit):
        B.main()                         # built once: the folders are no longer empty
