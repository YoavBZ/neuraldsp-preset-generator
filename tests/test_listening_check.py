"""The listening check's pure parts (`docs/listening-check-plan.md`)."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import pathlib
import random
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "research"))

import listening_check as L  # noqa: E402


# --- answers ------------------------------------------------------------------------

def test_answers_are_read_per_sitting_with_cant_tell():
    got = L.parse_answers("Sitting 1: 1A 2c 3?\n\nsitting 2: 1D 10B\n")
    assert got == {(1, 1): "A", (1, 2): "C", (1, 3): None, (2, 1): "D", (2, 10): "B"}


@pytest.mark.parametrize("sheet", [
    "1A 2C 3?",                       # the sitting is missing
    "Sitting 1: 1A 2E",               # not a letter A-D
    "Sitting 1: 1A 2C\nnotes",        # a stray line
    "Sitting 1: 1A 1B",               # answered twice
    "Sitting 1: 1A\nSitting 1: 1C",   # answered twice across lines
])
def test_an_answer_sheet_that_cannot_be_read_exactly_is_refused(sheet):
    with pytest.raises(ValueError):
        L.parse_answers(sheet)


def test_the_page_shows_the_exact_answer_format():
    page = L.page(2, [{"number": 1, "cue": "x", "song": "s.wav",
                       "clips": {x: f"{x}.wav" for x in "ABCD"}}])
    assert "Sitting 2: 1A 2C 3?" in page
    L.parse_answers("Sitting 2: 1A 2C 3?")


# --- statistics ---------------------------------------------------------------------

def test_the_randomization_null_is_centred_and_sensitive():
    pytest.importorskip("numpy", reason="needs the analysis extra")
    values = [[-0.3, 0.1, 0.1, 0.1]] * 12
    assert L.randomization_p(values, [0] * 12, draws=20_000) < 0.01      # always the best
    assert L.randomization_p(values, [1] * 12, draws=20_000) > 0.9
    assert L.randomization_p(values, [None] * 12, draws=20_000) == 1.0   # 0 either way


def test_the_randomization_p_is_uniform_under_a_random_pick():
    pytest.importorskip("numpy", reason="needs the analysis extra")
    rng = random.Random(11)
    ps = []
    for _ in range(300):
        values = []
        for _ in range(32):
            logs = [rng.gauss(0, 0.3) for _ in range(4)]
            mean = sum(logs) / 4
            values.append([v - mean for v in logs])
        ps.append(L.randomization_p(values, [rng.randrange(4) for _ in values], draws=4000))
    assert 0.01 <= sum(p < 0.05 for p in ps) / len(ps) <= 0.10
    assert 0.4 <= sum(ps) / len(ps) <= 0.6


def test_the_binomial_tail_is_exact():
    assert L.binomial_p(0, 32) == 1.0
    assert L.binomial_p(32, 32) == pytest.approx(0.25 ** 32)
    assert L.binomial_p(1, 1) == 0.25


def _row(logs, pick, riff="chords", g1=None):
    logs = dict(zip("ABCD", logs))
    return {"logs": logs, "pick": pick, "riff": riff,
            "g1": logs["A"] if g1 is None else g1, "template": 0.0}


def test_readings_aggregate_the_captured_share_and_deliver_g1_on_cant_tell(monkeypatch):
    pytest.importorskip("numpy", reason="needs the analysis extra")
    monkeypatch.setattr(L, "DRAWS", 2000)
    rows = [_row([0.0, 0.4, 0.4, 0.4], "A"), _row([0.0, 0.4, 0.4, 0.4], None)]
    got = L.readings(rows)
    # best - mean is -0.3 on each; the pick gains -0.3 once, "can't tell" 0.
    assert got["captured_share"] == pytest.approx(0.5)
    assert got["best_of_four"] == 1 and got["clear_pairs"] == 3
    assert got["clear_pairs_closer"] == 3
    assert got["median_vs_g1"] == 0.0             # "can't tell" delivers G1
    assert L.readings([]) is None


def test_the_decision_rests_on_the_primary_and_is_gated_by_inconclusive():
    passing = {b: {"all": {"p": 0.01}} for b in L.BAND_SETS}
    failing = dict(passing, union={"all": {"p": 0.2}})
    assert L.decide(passing, cant_tell=0, controls_hit=4)["main_path"]
    assert not L.decide(failing, cant_tell=0, controls_hit=4)["primary_holds"]
    many = L.decide(passing, cant_tell=L.MAX_CANT_TELL + 1, controls_hit=4)
    assert many["inconclusive"] and not many["main_path"]
    missed = L.decide(passing, cant_tell=0, controls_hit=L.MIN_CONTROLS_HIT - 1)
    assert missed["inconclusive"] and not missed["primary_holds"]


def test_a_guessing_listener_rarely_hits_enough_controls():
    chance = sum(math.comb(4, k) * 0.25 ** k * 0.75 ** (4 - k)
                 for k in range(L.MIN_CONTROLS_HIT, 5))
    assert chance < 0.06


# --- the trial plan -----------------------------------------------------------------

def test_the_trial_plan_holds_over_many_shuffles():
    parts = [f"p{i}" for i in range(16)]
    controls = [{"part": f"c{i}"} for i in range(4)]
    for seed in range(2000):
        sittings = L.plan_trials(parts, controls, {"part": "x"}, random.Random(seed))
        kinds = {s: collections.Counter(t["kind"] for t in ts) for s, ts in sittings.items()}
        assert kinds[1] == {"main": 16, "repeat": 1, "control": 2, "practice": 1}
        assert kinds[2] == {"main": 16, "repeat": 2, "control": 2}
        assert sittings[1][0]["kind"] == "practice"
        mains = [(t["part"], t["riff"]) for s in (1, 2) for t in sittings[s]
                 if t["kind"] == "main"]
        assert len(set(mains)) == 32               # every part through both riffs, once
        first = {(t["part"], t["riff"]) for t in sittings[1] if t["kind"] == "main"}
        for s, ts in sittings.items():
            at = [i for i, t in enumerate(ts) if t["kind"] == "control"]
            assert at[0] < len(ts) / 2 + 1 and at[1] > len(ts) / 2 - 1, seed
            assert {ts[i]["riff"] for i in at} == set(L.RIFFS)
            for i, t in enumerate(ts):
                if t["kind"] != "repeat":
                    continue
                assert (t["part"], t["riff"]) in first           # from sitting 1
                if s == 1:
                    orig = next(j for j, u in enumerate(ts) if u["kind"] == "main"
                                and (u["part"], u["riff"]) == (t["part"], t["riff"]))
                    assert i - orig >= 3, seed                   # two trials between
        assert {c["part"] for c in controls} == {
            t["part"] for s in (1, 2) for t in sittings[s] if t["kind"] == "control"}


# --- controls and practice ----------------------------------------------------------

def _reach(parts, near, gains):
    """Synthetic panels: per part, the presets in `near[part]` at their distances and
    every other preset at 4."""
    return {part: {f"{name}|full|{b}": near[part].get(name, 4.0)
                   for name in gains for b in L.BAND_SETS} for part in parts}


def test_controls_clear_the_floor_use_opposite_gain_and_never_share_a_preset():
    clean = [f"{a}:factory:clean{i}" for a in ("ac20", "pr12", "sw50r") for i in range(8)]
    loud = [f"{a}:factory:loud{i}" for a in ("ac20", "pr12", "sw50r") for i in range(8)]
    gains = {c: False for c in clean} | {c: True for c in loud}
    exposure = {"a": -2.0, "b": -5.0, "c": -6.0, "d": -9.0, "e": -9.5, "low": -12.0}
    # b's closest is a's, so it takes its next closest; c's closest is high-gain.
    near = {"a": {clean[0]: 1.0}, "b": {clean[0]: 1.0, clean[8]: 1.2}, "c": {loud[16]: 1.0},
            "d": {clean[17]: 1.0}, "e": {clean[18]: 1.0}, "low": {clean[19]: 1.0}}
    controls, practice = L.choose_controls(list(exposure), exposure.get,
                                           _reach(exposure, near, gains), gains.get)
    assert [c["part"] for c in controls] == ["a", "b", "c", "d"]
    used = [x for c in controls for x in c["candidates"]]
    assert len(used) == len(set(used))                       # no preset serves twice
    for c in controls:
        right, *wrong = c["candidates"]
        assert all(gains[w] != gains[right] for w in wrong)
        for b in L.BAND_SETS:
            assert all(math.log(c["distances"][b][w] / c["distances"][b][right])
                       > L.CONTROL_GAP for w in wrong)
    assert controls[0]["candidates"][0] == clean[0]          # its closest
    assert controls[1]["candidates"][0] == clean[8]          # the closest unused
    assert gains[controls[2]["candidates"][0]]                # high-gain against clean
    assert practice["part"] == "e"                           # the most exposed left
    assert not set(practice["candidates"]) & set(used)
    assert len({x.split(":")[0] for x in practice["candidates"][:3]}) == 3


def test_a_part_under_the_floor_is_never_a_control():
    gains = {f"ac20:factory:c{i}": i % 2 == 1 for i in range(12)}
    exposure = {"a": -2.0, "low": -11.0}
    near = {"a": {"ac20:factory:c0": 1.0}, "low": {"ac20:factory:c2": 1.0}}
    controls, _ = L.choose_controls(list(exposure), exposure.get,
                                    _reach(exposure, near, gains), gains.get)
    assert [c["part"] for c in controls] == ["a"]


# --- the listener's folder ----------------------------------------------------------

def test_the_listeners_folder_may_not_name_an_amp_a_candidate_or_a_preset(tmp_path):
    (tmp_path / "trial-01-A.wav").write_bytes(b"x")
    (tmp_path / "index.html").write_text("<p>Trial 1</p>")
    assert L.leak_check(tmp_path, ["Jazzy Box"]) == []
    (tmp_path / "index.html").write_text("<p>Trial 1: PR12 at the edge</p>")
    assert L.leak_check(tmp_path)
    (tmp_path / "index.html").write_text("<p>Trial 1: the jazzy box one</p>")
    assert L.leak_check(tmp_path, ["Jazzy Box"])
    page = L.page(1, [{"number": 1, "cue": "Bloomlight: the guitar track GTR.",
                       "song": "trial-01-song.wav",
                       "clips": {x: f"trial-01-{x}.wav" for x in "ABCD"}}])
    (tmp_path / "index.html").write_text(page)
    assert L.leak_check(tmp_path, ["Jazzy Box", "G1"]) == []


# --- score, end to end --------------------------------------------------------------

def _scoring_setup(tmp_path, picks_best: bool):
    parts = [f"p{i}" for i in range(16)]
    distances = {p: {b: {"G1": 2.0, "G2": 1.0, "G3": 1.5, "G4": 1.8, "template+R": 2.2}
                     for b in L.BAND_SETS} for p in parts}
    inputs = {"parts": parts, "distances": distances, "g1_rule_chance_pass": 0.99,
              "di_lufs": {p: -30.0 + i for i, p in enumerate(parts)}, "riff_lufs": -23.7}
    inputs_path = tmp_path / "inputs.json"
    inputs_path.write_text(json.dumps(inputs))
    rng = random.Random(5)
    controls = [{"part": f"c{i}"} for i in range(4)]
    sittings = L.plan_trials(parts, controls, {"part": "x"}, rng)
    key = {"inputs_sha256": hashlib.sha256(inputs_path.read_bytes()).hexdigest(),
           "sittings": {}}
    lines = {}
    for s, trials in sittings.items():
        for n, t in enumerate(trials, 1):
            labels = (["G1", "G2", "G3", "G4"] if t["kind"] in ("main", "repeat")
                      else ["C0", "C1", "C2", "C3"])
            rng.shuffle(labels)
            letters = dict(zip("ABCD", labels))
            key["sittings"].setdefault(str(s), []).append({"number": n, **t,
                                                            "letters": letters})
            want = "G2" if picks_best else "G1"
            answer = next((x for x, g in letters.items() if g in (want, "C0")), "A")
            lines.setdefault(s, []).append(f"{n}{answer}")
    private = tmp_path / "run" / "private"
    private.mkdir(parents=True, exist_ok=True)
    (private / "private-key.json").write_text(json.dumps(key))
    answers = tmp_path / "answers.txt"
    answers.write_text("\n".join(f"Sitting {s}: {' '.join(v)}" for s, v in lines.items()))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    return argparse.Namespace(out_dir=tmp_path / "run", inputs=inputs_path,
                              answers=answers, answers_sha=sha(answers),
                              key_sha=sha(private / "private-key.json"),
                              json=tmp_path / "score.json")


def test_score_end_to_end_on_a_listener_who_always_picks_the_best(tmp_path, monkeypatch):
    pytest.importorskip("numpy", reason="needs the analysis extra")
    monkeypatch.setattr(L, "DRAWS", 2000)
    L.score(_scoring_setup(tmp_path, picks_best=True))
    got = json.loads((tmp_path / "score.json").read_text())
    assert got["primary_holds"] and got["main_path"] and not got["inconclusive"]
    assert got["controls_hit"] == {"1": [True, True], "2": [True, True]}
    assert got["repeats_consistent"] == [True, True, True]
    for b in L.BAND_SETS:
        r = got["by_band_set"][b]
        assert r["all"]["trials"] == 32 and r["all"]["best_of_four"] == 32
        assert r["all"]["captured_share"] == pytest.approx(1.0)
        assert r["per_riff"]["chords"]["trials"] == 16
        assert r["di_hotter_than_median_gap"]["trials"] == 16


def test_score_reads_the_worst_pick_as_no_main_path(tmp_path, monkeypatch):
    pytest.importorskip("numpy", reason="needs the analysis extra")
    monkeypatch.setattr(L, "DRAWS", 2000)
    L.score(_scoring_setup(tmp_path, picks_best=False))
    got = json.loads((tmp_path / "score.json").read_text())
    assert not got["primary_holds"] and not got["main_path"]
    assert got["by_band_set"]["recording"]["all"]["median_vs_g1"] == 0.0


def test_score_refuses_a_sheet_missing_a_trial_or_a_changed_key(tmp_path, monkeypatch):
    args = _scoring_setup(tmp_path, picks_best=True)
    first, *rest = args.answers.read_text().splitlines()
    args.answers.write_text("\n".join([first.rsplit(" ", 1)[0], *rest]))   # one fewer
    args.answers_sha = hashlib.sha256(args.answers.read_bytes()).hexdigest()
    with pytest.raises(SystemExit):
        L.score(args)
    args = _scoring_setup(tmp_path, picks_best=True)
    args.key_sha = "0" * 64
    with pytest.raises(SystemExit):
        L.score(args)
