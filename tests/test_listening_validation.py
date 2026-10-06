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
sys.path.insert(0, str(ROOT / "research"))

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
    return {"clear_pairs": 1000, "clear_pairs_disagreeing": 170,
            "trials": tests + hidden + repeats}


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
    with pytest.raises(ValueError, match="no trial 3"):
        S.parse_answers("1: A\n2: B\n3: A\n", 2)


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
    assert out["same_prediction_as_judge"] == {"judge_union": 24, "alm": 24, "v3c": 14}
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
    out = S.score(plan, order, keys, answers)
    assert out["judge"] == "rejected"
    # The same count from a listener whose repeats disagree is not a rejection.
    flips = iter([True, False, True, False, True, False])
    order, keys, answers = _order_and_keys(
        plan, lambda row: next(flips) if row["kind"] == "repeat" or row["id"] in
        ("t00", "t01", "t02") else False, seed=3)
    out = S.score(plan, order, keys, answers)
    assert sum(1 for r in out["repeats"] if r["same"]) < 2 and out["judge"] == "inconclusive"


def test_the_scorer_records_the_answers_before_any_key_and_refuses_a_changed_list(
        tmp_path, monkeypatch):
    import hashlib
    import json

    plan = _plan()
    order, keys, answers = _order_and_keys(plan, lambda row: True)
    private = tmp_path / "private"
    private.mkdir()
    trials_text = json.dumps(plan)
    (private / "trials.json").write_text(trials_text)
    sha = hashlib.sha256(trials_text.encode()).hexdigest()
    (private / "order.json").write_text(json.dumps({"trials_sha256": sha, "order": order}))
    sheet = tmp_path / "ANSWERS.md"
    sheet.write_text("\n".join(f"{n:02d}: {a}" for n, a in answers.items()))
    monkeypatch.setattr(S, "declared_trials_sha256", lambda: sha)
    monkeypatch.setattr(sys, "argv", ["score", "--private-dir", str(private),
                                      "--answers", str(sheet)])
    with pytest.raises(FileNotFoundError):                      # no keys exist yet...
        S.main()
    assert (private / "answers.sha256").read_text().strip() == hashlib.sha256(
        sheet.read_bytes()).hexdigest()                         # ...but the hash is written
    sheet.write_text(sheet.read_text().replace("01: ", "01: ?  #", 1).replace("#A", "")
                     .replace("#B", ""))
    with pytest.raises(SystemExit):
        S.main()                                                # a changed sheet is refused
    (private / "answers.sha256").unlink()
    monkeypatch.setattr(S, "declared_trials_sha256", lambda: "0" * 64)
    with pytest.raises(SystemExit):
        S.main()                                                # an undeclared trial list


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



def test_the_build_keeps_keys_private_and_starts_each_render_on_the_window(tmp_path, monkeypatch,
                                                                           capsys):
    import json
    import subprocess

    plan = _plan()
    for t in plan["trials"]:
        if t["kind"] != "repeat":
            t.update(window_s=1.0, lag=480)
            for side in ("first", "second"):            # candidates from two panels
                if t[side] != "reference":
                    t[side] = f"{'pr12' if t[side].endswith('a') else 'sw50r'}:{t[side]}"
    panels = {amp: tmp_path / amp for amp in ("pr12", "sw50r")}
    parts = sorted({t["part"] for t in plan["trials"] if t["kind"] != "repeat"})
    for amp, panel in panels.items():
        panel.mkdir()
        names = {c.split(":", 1)[1] for t in plan["trials"] if t["kind"] != "repeat"
                 for c in (t["first"], t["second"]) if c.startswith(f"{amp}:")}
        rows = [{"part": part, "candidate": c, "file": str(panel / f"{part}-{c}.wav")}
                for part in parts for c in sorted(names)]
        for row in rows:
            pathlib.Path(row["file"]).write_bytes(row["file"].encode())
        (panel / "index.json").write_text(json.dumps({"amp": amp, "rows": rows}))
    files, plan["panels"] = P.panel_files(list(panels.values()))
    crops = tmp_path / "crops"
    for t in plan["trials"]:
        if t["kind"] != "repeat":
            t["files"] = {c: {"path": str(files[t["part"]][c]),
                              "sha256": P.file_sha256(files[t["part"]][c])}
                          for c in (t["first"], t["second"]) if c != "reference"}
            (crops / t["part"]).mkdir(parents=True, exist_ok=True)
            for n in ("reference", "di"):
                (crops / t["part"] / f"{n}.wav").write_bytes(f"{t['part']}{n}".encode())
            t["crops"] = {n: P.file_sha256(crops / t["part"] / f"{n}.wav")
                          for n in ("reference", "di")}
    trials = tmp_path / "trials.json"
    trials.write_text(json.dumps(plan))
    calls = []

    def fake_run(cmd, capture_output, text):
        calls.append(cmd)
        out, key = cmd[cmd.index("--out") + 1], cmd[cmd.index("--key") + 1]
        pathlib.Path(out).write_bytes(b"flac")
        pathlib.Path(key).write_text("{}")
        return subprocess.CompletedProcess(cmd, 0, "reproducible blind assignment seed: 1\n", "")

    import hashlib

    import analysis

    monkeypatch.setattr(B.subprocess, "run", fake_run)
    monkeypatch.setattr(analysis, "require", lambda *_: None)       # no audio is touched
    monkeypatch.setattr(B, "declared_trials_sha256",
                        lambda: hashlib.sha256(trials.read_text().encode()).hexdigest())
    listener, private = tmp_path / "listen", tmp_path / "private"
    monkeypatch.setattr(sys, "argv", ["build", "--trials", str(trials),
                                      "--panel-dir", str(panels["pr12"]),
                                      "--panel-dir", str(panels["sw50r"]),
                                      "--crops-dir", str(crops),
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
            model = cmd[cmd.index(side + "-amp-model") + 1]  # each render's own amp
            assert model == ("non-Morgan" if path.endswith("reference.wav")
                             else pathlib.Path(path).parent.name.upper())
    import random as r

    judge_a = 0                          # the judge's closer option is A on exactly half
    order = json.loads((private / "order.json").read_text())["order"]
    for cmd, row in zip(calls, order):
        if row["kind"] == "test":
            first_is_a = not r.Random(int(cmd[cmd.index("--seed") + 1])).getrandbits(1)
            judge_a += first_is_a        # every fixture pair has the first closer
    assert judge_a == 12
    with pytest.raises(SystemExit):
        B.main()                         # built once: the folders are no longer empty
    option = pathlib.Path(files["p0"]["pr12:c0a"])
    kept = option.read_bytes()
    for changed in (option, crops / "p0" / "reference.wav"):
        original = changed.read_bytes()
        changed.write_bytes(b"re-rendered")
        monkeypatch.setattr(sys, "argv", ["build", "--trials", str(trials),
                                          "--panel-dir", str(panels["pr12"]),
                                          "--panel-dir", str(panels["sw50r"]),
                                          "--crops-dir", str(crops),
                                          "--out-dir", str(tmp_path / "w"),
                                          "--private-dir", str(tmp_path / "v")])
        with pytest.raises(SystemExit):
            B.main()                     # audio that is not what the trial list recorded
        assert not (tmp_path / "w").exists(), "refused before anything was written"
        changed.write_bytes(original)
    assert option.read_bytes() == kept
    monkeypatch.setattr(sys, "argv", ["build", "--trials", str(trials),
                                      "--panel-dir", str(panels["pr12"]),
                                      "--out-dir", str(tmp_path / "u"),
                                      "--private-dir", str(tmp_path / "t")])
    with pytest.raises(SystemExit):
        B.main()                         # not the panels the trials were drawn from
    assert "not the ones the trials were drawn from" in capsys.readouterr().err
    assert not (tmp_path / "u").exists()
    unbound = json.loads(trials.read_text())
    del next(t for t in unbound["trials"] if t["kind"] == "test")["files"]
    trials.write_text(json.dumps(unbound))
    monkeypatch.setattr(B, "declared_trials_sha256",
                        lambda: hashlib.sha256(trials.read_text().encode()).hexdigest())
    monkeypatch.setattr(sys, "argv", ["build", "--trials", str(trials),
                                      "--panel-dir", str(panels["pr12"]),
                                      "--panel-dir", str(panels["sw50r"]),
                                      "--crops-dir", str(crops),
                                      "--out-dir", str(tmp_path / "s"),
                                      "--private-dir", str(tmp_path / "r")])
    with pytest.raises(SystemExit):
        B.main()                         # a trial whose options are not bound to audio
    assert not (tmp_path / "s").exists()
    monkeypatch.setattr(sys, "argv", ["build", "--trials", str(trials),
                                      "--panel-dir", str(panels["pr12"]),
                                      "--panel-dir", str(panels["sw50r"]),
                                      "--crops-dir", str(crops),
                                      "--out-dir", str(tmp_path / "x"),
                                      "--private-dir", str(tmp_path / "x" / "private")])
    with pytest.raises(SystemExit):
        B.main()                         # the private folder inside the listener's
    monkeypatch.setattr(B, "declared_trials_sha256", lambda: "0" * 64)
    monkeypatch.setattr(sys, "argv", ["build", "--trials", str(trials),
                                      "--panel-dir", str(panels["pr12"]),
                                      "--panel-dir", str(panels["sw50r"]),
                                      "--crops-dir", str(crops),
                                      "--out-dir", str(tmp_path / "y"),
                                      "--private-dir", str(tmp_path / "z")])
    with pytest.raises(SystemExit):
        B.main()                         # a trial list the plan does not declare


def test_the_draw_refuses_to_overwrite_a_trial_list(tmp_path, monkeypatch):
    out = tmp_path / "trials.json"
    out.write_text("{}")
    cache = tmp_path / "pool.json"
    import json

    panel = tmp_path / "panel"
    panel.mkdir()
    (panel / "index.json").write_text(json.dumps({"amp": "pr12", "rows": []}))
    import benchmark_recordings

    cache.write_text(json.dumps({"panels": P.panel_files([panel])[1],
                                 "lags_sha256": P.file_sha256(benchmark_recordings.LAGS),
                                 "pool": {}}))
    import analysis

    monkeypatch.setattr(analysis, "require", lambda *_: None)
    monkeypatch.setattr(sys, "argv", ["plan", "--panel-dir", str(panel), "--cache", str(cache),
                                      "--out", str(out)])
    with pytest.raises(SystemExit):
        P.main()
    assert out.read_text() == "{}"



def test_the_plan_declares_exactly_one_trial_list_hash():
    sha = B.declared_trials_sha256()
    assert len(sha) == 64 and S.declared_trials_sha256() == sha


def _panel(tmp_path, amp, parts, names):
    import json

    panel = tmp_path / amp
    panel.mkdir()
    rows = [{"part": p, "candidate": c, "file": str(panel / f"{p}-{c}.wav")}
            for p in parts for c in names]
    (panel / "index.json").write_text(json.dumps({"amp": amp, "rows": rows}))
    return panel


def test_panels_merge_by_amp_and_must_hold_the_same_parts(tmp_path):
    a = _panel(tmp_path, "pr12", ["p1", "p2"], ["template", "x"])
    b = _panel(tmp_path, "sw50r", ["p1", "p2"], ["x"])
    files, hashes = P.panel_files([a, b])
    assert sorted(files["p1"]) == ["pr12:template", "pr12:x", "sw50r:x"]
    assert set(hashes) == {str(a), str(b)}
    with pytest.raises(SystemExit):
        P.panel_files([a, a])                                  # one amp twice
    c = _panel(tmp_path, "ac20", ["p1"], ["x"])
    with pytest.raises(SystemExit):
        P.panel_files([a, c])                                  # different parts


def test_parts_without_a_clear_recorded_lag_are_left_out_and_the_lag_is_passed(tmp_path):
    files = {"p1": {"pr12:x": "f1"}, "p2": {"pr12:x": "f2"}}
    meta = {"p1": {"lag": 480}, "p2": {"lag": 0}}
    jobs, no_lag = P.pool_jobs(files, meta, tmp_path, lag_of={"p1": 1000, "p2": None}.get)
    assert no_lag == ["p2"]
    assert jobs == [("p1", {"pr12:x": "f1"}, 480, 1000, tmp_path)]


def test_the_draw_refuses_a_cache_scored_from_other_panels(tmp_path, monkeypatch):
    import json

    panel = tmp_path / "panel"
    panel.mkdir()
    (panel / "index.json").write_text(json.dumps({"amp": "pr12", "rows": []}))
    cache = tmp_path / "pool.json"
    cache.write_text(json.dumps({"panels": {str(panel): "0" * 64}, "lags_sha256": "0" * 64,
                                 "pool": {}}))
    import analysis

    monkeypatch.setattr(analysis, "require", lambda *_: None)
    monkeypatch.setattr(sys, "argv", ["plan", "--panel-dir", str(panel), "--cache", str(cache),
                                      "--out", str(tmp_path / "trials.json")])
    with pytest.raises(SystemExit):
        P.main()
    assert not (tmp_path / "trials.json").exists()


def test_eligible_options_are_neither_the_shipped_template_nor_high_gain():
    loud = {"pr12:factory:Metal"}.__contains__
    assert P.eligible("pr12:factory:Clean", gain_of=loud)
    assert not P.eligible("pr12:factory:Metal", gain_of=loud)
    assert not P.eligible("pr12:template", gain_of=loud)
    pool = _pool()
    banned = {"c0", "c1", "c2"}
    for seed in range(3):
        drawn = P.draw(pool, {k: {"band": f"b{i % 9}"} for i, k in enumerate(pool)}, seed,
                       allowed=lambda c: c not in banned)["trials"]
        assert not any(t.get(s) in banned for t in drawn for s in ("first", "second"))


@pytest.mark.skipif(not P.preset_path("pr12:factory:Neural DSP/x").parent.parent.exists(),
                    reason="needs the plugin's factory presets")
def test_high_gain_is_read_from_the_presets_settings():
    assert P.high_gain("pr12:factory:Neural DSP/Vintage Metal")         # drive 1 on, volume 0.88
    assert P.high_gain("pr12:factory:Artists/Joseph Anidjar/Mean Little Crunchy Guy")   # volume 0.87
    assert not P.high_gain("pr12:factory:Artists/Richard Henshall/Crystal Clean")
    assert not P.high_gain("pr12:template+R")                          # volume 0.62


def test_the_shipped_template_is_never_in_a_test_pair():
    pool = _pool()
    for p in pool.values():
        p["candidates"]["pr12:template"] = {d: 0.01 for d in P.DISTANCES}   # always "clear"
    for seed in range(5):
        tests = [t for t in P.draw(pool, {k: {"band": f"b{i % 9}"} for i, k in
                                          enumerate(pool)}, seed)["trials"]
                 if t["kind"] == "test"]
        assert not any(P.shipped_template(t[s]) for t in tests for s in ("first", "second"))
