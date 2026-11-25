"""The note-reading diagnosis (`learn/scratch_readerr.py`, `docs/scratch-readerr-plan.md`): the key prefix, RX_TABLE
(every case ends in exactly one code), the anatomy's partition and one constructed case per class, the clean-up's
losses, the figures, the tracking read's orientation and tie rule, the freeze, the grid pick with its tie order and
edge extension, the cross-set read, the real-DI labeller and its P3 guard, the runner contract, the screen's line,
the module's own guard, the write and ledger guards and that the module assigns no attribute on an imported module.
Synthetic part keys only; pure: runs on the light CI runner (no numpy). The played trace against `synthesise_redo`
needs numpy (skipped elsewhere)."""
import ast
import itertools
import json
import pathlib
import random

import pytest

from learn import note_rebuild as NR
from learn import note_transcribe as T
from learn import scratch_exact as SX
from learn import scratch_readerr as X
from learn import scratch_search as S

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = (REPO / "learn" / "scratch_readerr.py").read_text()
SHA = "a" * 64


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


def _n(on, pitch, off=None, bends=None, amp=0.5):
    return {"on": on, "off": on + 0.4 if off is None else off, "pitch": pitch, "amp": amp, "bends": bends or []}


# --- names, keys, the table ---------------------------------------------------------------------------------------------

def test_the_key_prefix_is_outside_every_guarded_prefix():
    pre = [p for ps in T.KEY_PREFIXES.values() for p in ps]
    for k in (X.PHASE, X.PHASE_FROZEN, X.PHASE_NOTES, X.PHASE_OUTCOME):
        assert k.startswith(X.KEY_PREFIX)
        assert not k.startswith(tuple(pre)) and not k.startswith(SX.KEY_PREFIX) and not k.startswith("phase_fs")
        assert not k.startswith(X.GUARDED_PREFIXES)
    assert not S.fs_keys({X.PHASE: 1}) and not T.guarded_keys({X.PHASE: 1}, pre)
    assert not SX.keys_refusal({X.PHASE: 1}, {})          # the exact test's guard never reads these keys
    X.rx_table_guard()


def test_code_files_cover_the_module_the_runner_and_every_guarded_file():
    assert X.CODE_FILES[:2] == ("learn/scratch_readerr.py", "learn/readerr_run.py")
    assert set(SX.CODE_FILES) | set(T.CODE_FILES) | {"learn/note_tx.py", "learn/tx_run.py"} <= set(X.CODE_FILES)
    assert len(X.CODE_FILES) == len(set(X.CODE_FILES))


def test_the_table_guard_refuses_a_changed_table(monkeypatch):
    monkeypatch.setattr(X, "RX_CODES", tuple(reversed(X.RX_CODES)))
    with pytest.raises(SystemExit, match="nine declared"):
        X.rx_table_guard()
    monkeypatch.undo()
    monkeypatch.setattr(X, "KEY_PREFIX", "phase_scratch_exact_readerr")
    with pytest.raises(SystemExit, match="guarded prefix"):
        X.rx_table_guard()


def test_the_family_is_declared_once_each_with_its_orientation():
    assert X.FIGURES[0] == X.DEFAULT_FIGURE == "note_error"
    assert set(X.ORIENTATION.values()) == {"error", "similarity"}
    assert [f for f, o in X.FAMILY if o == "similarity"] == ["reread_env_corr", "list_env_corr"]
    assert len(X.FIGURES) == len(set(X.FIGURES)) == 29


# --- RX_TABLE ------------------------------------------------------------------------------------------------------------

def test_phase_1_codes():
    assert X.rx_phase1(False, {"code": "RX-tracks"})["code"] == "RX-stop"
    assert X.rx_phase1(True, {"code": "RX-tracks"})["code"] == "RX-tracks"
    r = X.rx_phase1(True, X.freeze_rule({}))
    assert r["code"] == "RX-untracked" and "no screen" in r["next"] and "screen" not in r["when"]


def _reference(proofs, cands):
    """RX_TABLE as written in the plan, apart from `rx_code`'s order of evaluation."""
    if not proofs:
        return "RX-stop"
    prod = [c for c in cands if c["kind"] != "reference"]
    setting_ok = any(c["kind"] == "setting" and c["bench"] == "better" and not c["real_worse"] for c in prod)
    if any(c["kind"] == "transcriber" and c["bench"] == "better" and not c["real_worse"]
           and (c["beats_best_setting"] or not setting_ok) for c in prod):
        return "RX-transcriber"
    if setting_ok:
        return "RX-setting"
    if any(c["bench"] == "better" and c["real_worse"] for c in prod):
        return "RX-harm"
    if any(c["kind"] == "reference" and c["bench"] == "better" for c in cands):
        return "RX-reference-only"
    if any(c["mean_better"] and c["bench"] != "better" for c in prod):
        return "RX-undecided"
    return "RX-none"


def test_every_case_ends_in_exactly_one_code():
    facts = list(itertools.product(("better", "undecided", "worse", None), (True, False), (True, False),
                                   (True, False)))
    seen = set()
    for proofs in (True, False):
        for kinds in itertools.product(X.KINDS, repeat=2):
            for f1, f2 in itertools.product(facts, repeat=2):
                cands = [{"name": f"c{i}", "kind": k, "bench": b, "mean_better": mb, "real_worse": rw,
                          "beats_best_setting": bb} for i, (k, (b, mb, rw, bb)) in enumerate(zip(kinds, (f1, f2)))]
                got = X.rx_code(proofs, cands)
                assert got["code"] == _reference(proofs, cands), (proofs, cands)
                assert got["code"] in X.PHASE2_CODES and got["next"]
                seen.add(got["code"])
    assert seen == set(X.PHASE2_CODES)
    assert set(X.PHASE1_CODES) | set(X.PHASE2_CODES) == set(X.RX_CODES)


def test_ties_between_kinds_go_to_no_download_first():
    s = {"name": "grid", "kind": "setting", "bench": "better", "mean_better": True, "real_worse": False}
    t = {"name": "mt3", "kind": "transcriber", "bench": "better", "mean_better": True, "real_worse": False,
         "beats_best_setting": False}
    assert X.rx_code(True, [s, t])["code"] == "RX-setting"
    assert X.rx_code(True, [s, dict(t, beats_best_setting=True)])["code"] == "RX-transcriber"
    assert X.rx_code(True, [t])["code"] == "RX-transcriber"     # no setting decided: the best variant is the re-read
    assert X.TIE_ORDER == ("setting", "transcriber")


def test_the_screen_is_never_a_pricing_path():
    for code, _, when, nxt in X.RX_TABLE:
        assert "screen-price" not in nxt and "or the screen" not in nxt
    assert "screen" not in json.dumps([r for r in X.RX_TABLE if r[0] == "RX-setting"])


# --- the clean-up's losses and the timeline ------------------------------------------------------------------------------

def _random_events(rng, n=40, span=8.0):
    out = []
    for _ in range(n):
        on = rng.uniform(-0.5, span)
        out.append({"on": on, "off": on + rng.uniform(0.02, 1.2), "pitch": rng.randint(30, 92),
                    "amp": rng.random(), "bends": [rng.choice((0, 1, 2)) for _ in range(rng.randint(0, 6))]})
    for _ in range(12):                                     # crowd one spot so six-at-once drops some
        out.append({"on": 2.0 + rng.uniform(0, 0.01), "off": 3.0, "pitch": rng.randint(40, 80), "amp": 0.3,
                    "bends": []})
    return out


def test_cleanup_losses_mirror_clean_transcribed():
    rng = random.Random(7)
    for _ in range(30):
        ev = _random_events(rng)
        kept, lost = X.cleanup_losses(T.notes_from_events(ev))
        want, cnt = T.clean_transcribed(T.notes_from_events(ev))
        assert kept == want
        assert len(lost) == cnt["out_of_range"] + cnt["over_six"]
        assert sum(n["why"] == "over_six" for n in lost) == cnt["over_six"]


def test_presnap_and_lost_follow_timed_notes_steps():
    ev = [{"on": 1.0, "off": 1.5, "pitch": 60, "amp": 0.5, "bends": []},
          {"on": 2.0, "off": 2.5, "pitch": 20, "amp": 0.5, "bends": []}]
    pre = X.presnap_notes(ev, 0.5, 0.01, 10.0)
    assert len(pre) == 1 and pre[0]["on"] == pytest.approx(0.51)
    lost = X.lost_on_timeline(ev, 0.5, 0.01, 10.0)
    assert len(lost) == 1 and lost[0]["why"] == "out_of_range" and lost[0]["on"] == pytest.approx(1.51)


# --- the anatomy -----------------------------------------------------------------------------------------------------------

def test_one_constructed_case_per_extra_class():
    truth = [_n(1.0, 60), _n(3.0, 50), _n(5.0, 55), _n(7.0, 62), _n(9.0, 58, off=9.6, bends=[0, 0] + [4] * 12)]
    est = [_n(1.0, 60), _n(1.01, 72),                     # paired; harmonic (an octave above a sounding note)
           _n(1.2, 60),                                    # re-find (its pitch, still sounding)
           _n(3.01, 38),                                   # octave-sub (the missed 50, an octave below)
           _n(5.02, 56),                                   # semitone-sub (the missed 55)
           _n(6.9, 62),                                    # timing (the missed 62, 100 ms early)
           _n(9.0, 58), _n(9.2, 60),                       # paired; bend fragment (2 semitones above a bent note)
           _n(11.0, 70)]                                   # rest
    an = X.anatomy(truth, est)
    want = [None, "harmonic", "re-find", "octave-sub", "semitone-sub", "timing", None, "bend-fragment", "rest"]
    assert an["est_classes"] == want
    assert an["truth_classes"] == [None, "substitution", "substitution", "timing", None]
    assert X.partition_holds(an)
    assert an["extras_sorted"] == {"harmonic": 1, "re-find": 1, "other": 5}


def test_one_constructed_case_per_miss_class():
    truth = [_n(1.0, 60),                                  # substitution (an unpaired 61 at once)
             _n(2.0, 64),                                  # timing (an unpaired 64, 120 ms late)
             _n(3.5, 67),                                  # merged (a 67 held from 3.0 through it)
             _n(5.0, 69),                                  # clean-up (a dropped 69 at its onset)
             _n(6.0, 52), _n(6.01, 59),                    # the 52 pairs; the 59 is a chord member
             _n(8.0, 71),                                  # rest
             _n(9.0, 74)]                                  # never sounded (the trace skipped it)
    est = [_n(1.0, 61), _n(2.12, 64), _n(3.0, 67, off=4.0), _n(6.0, 52)]
    lost = [dict(_n(5.0, 69), why="over_six")]
    an = X.anatomy(truth, est, lost=lost, skipped={7})
    assert an["truth_classes"] == ["substitution", "timing", "merged", "clean-up", None, "chord-member", "rest",
                                   X.NEVER_SOUNDED]
    assert an["misses"][X.NEVER_SOUNDED] == 1 and X.partition_holds(an)


def test_the_partition_holds_on_random_lists():
    rng = random.Random(11)
    for _ in range(60):
        truth = [_n(rng.uniform(0, 8), rng.randint(40, 80), bends=[rng.choice((0, 3, 4))] * rng.randint(0, 8))
                 for _ in range(rng.randint(0, 25))]
        est = [_n(rng.uniform(0, 8), rng.randint(40, 80)) for _ in range(rng.randint(0, 25))]
        est += [dict(t, on=t["on"] + rng.uniform(-0.04, 0.04)) for t in truth if rng.random() < 0.6]
        lost = [_n(rng.uniform(0, 8), rng.randint(40, 80)) for _ in range(rng.randint(0, 3))]
        an = X.anatomy(truth, est, lost=lost, skipped=set(rng.sample(range(len(truth)), min(2, len(truth)))))
        assert X.partition_holds(an)
        assert sum(c is None for c in an["est_classes"]) == an["matched"] == T.match_notes(truth, est)["matched"]
        figs = X.note_figures(an, truth, est, 10.0)
        assert set(figs) == set(X.FIGURES) - {f for f in X.FIGURES if f.startswith(("reread_", "list_"))}


def test_matched_errors_groups_and_bias():
    truth = [_n(1.0, 48), _n(1.0, 60), _n(3.0, 55)]           # 60 is ghost-shaped (an octave above 48, one group)
    est = [_n(1.01, 48, off=1.2), _n(3.02, 55, off=3.4)]
    pre = [_n(1.03, 48), _n(3.0, 55)]
    an = X.anatomy(truth, est, presnap=pre)
    assert an["onset_ms_after_snap"]["n"] == 2 and an["onset_ms_before_snap"]["median_abs"] == pytest.approx(15.0)
    assert an["ghost_shaped"] == {"notes": 1, "share": pytest.approx(1 / 3), "recall": 0.0, "recall_rest": 1.0}
    assert an["by_group_size"]["2"] == {"truth": 2, "recall": 0.5, "est": 0, "precision": None}
    assert an["attacks"] == {"truth_groups": 2, "attacks_missed": 0, "est_groups": 2, "extra_attacks": 0}
    assert an["ends_right"] == 1                             # 3.4 against 3.4; 1.2 against 1.4 misses
    assert not X.anatomy(truth, est, presnap=pre[:1])["presnap_aligned"]


def test_as_played_keeps_the_sounding_notes_with_their_real_ends():
    notes = [_n(0.5, 60, off=2.0), _n(1.0, 62), _n(9.9, 64, off=10.5)]
    per = [{"played": True, "end": 1.1, "end_kind": "repluck"}, {"played": False, "why": "no free string"},
           {"played": True, "end": 10.6, "end_kind": "release"}]
    got, skipped = X.as_played(notes, per, 10.25)
    assert skipped == [1] and [g["nominal"] for g in got] == [0, 2]
    assert got[0]["off"] == 1.1 and got[1]["off"] == 10.25 and got[0]["end_kind"] == "repluck"


def test_frame_figures_and_the_dry_six():
    f = X.FRAME_S
    truth = [_n(0.0, 60, off=10 * f)]
    est = [_n(5 * f, 60, off=15 * f)]
    got = X.frame_figures(truth, est, 1.0)
    assert got["frame_error"] == pytest.approx(0.5) and got["uncovered_time"] == pytest.approx(0.5)
    assert got["false_time"] == pytest.approx(0.5)
    assert X.frame_figures([], [], 1.0) == {"frame_error": None, "uncovered_time": None, "false_time": None}
    mask = {"1024": {"pauses_dry": 0.3, "pauses_true": 0.1}, "2048": {"pauses_dry": 0.2, "pauses_true": 0.2}}
    dry = X.dry_figures({"xn-reread": {"figures": {"env_corr": 0.9, "logmel": 7.0, "mask": mask}}})
    assert dry["reread_pause_excess"] == pytest.approx(0.1) and dry["list_env_corr"] is None
    assert set(dry) == {f for f in X.FIGURES if f.startswith(("reread_", "list_"))}


def test_without_ghosts_drops_the_ghost_shaped_notes_and_their_pairs():
    truth = [_n(1.0, 48), _n(1.0, 60), _n(3.0, 55)]
    est = [_n(1.0, 48), _n(1.0, 60), _n(3.0, 55), _n(4.0, 70)]
    t, e = X.without_ghosts(truth, est)
    assert [n["pitch"] for n in t] == [48, 55] and [n["pitch"] for n in e] == [48, 55, 70]


# --- the tracking read and the freeze ------------------------------------------------------------------------------------

def _parts(n):
    return [f"set{i % 2}/part{i:02d}" for i in range(n)]


def _mean_interval(cost):
    def iv(ks):
        m = sum(cost[k] for k in ks) / len(ks)
        return _iv(m, m - 0.02, m + 0.02)
    return iv


def test_an_error_figure_reads_its_upper_half_as_the_worse():
    ks = _parts(10)
    cost = {k: 0.1 * i for i, k in enumerate(ks)}           # costs rise with the figure
    vals = {k: float(i) for i, k in enumerate(ks)}
    r = X.tracking_read(cost, vals, "error", _mean_interval(cost))
    assert r["worse_half"] == ks[5:] and r["difference"]["mean"] == pytest.approx(0.5)   # diff_interval(upper, lower)
    assert r["label"]["reading"] == "worse" and r["rho_agrees"] and r["tracks"]


def test_a_similarity_reads_its_lower_half_as_the_worse_and_rho_must_agree():
    ks = _parts(10)
    cost = {k: 0.1 * i for i, k in enumerate(ks)}
    sim = {k: -float(i) for i, k in enumerate(ks)}          # a similarity falling as the cost rises
    r = X.tracking_read(cost, sim, "similarity", _mean_interval(cost))
    assert r["worse_half"] == r["difference"] and False or r["label"]["reading"] == "worse"
    assert r["spearman"] < 0 and r["rho_agrees"] and r["tracks"]
    wrong = X.tracking_read(cost, sim, "error", _mean_interval(cost))     # read as an error: the better half
    assert not wrong["tracks"] and not wrong["rho_agrees"]


def test_a_key_broken_split_is_never_frozen():
    ks = _parts(10)
    cost = {k: (1.0 if i >= 6 else 0.0) for i, k in enumerate(ks)}
    sparse = {k: (1.0 if i >= 6 else 0.0) for i, k in enumerate(ks)}   # six zeros: the split breaks a tie by key
    r = X.tracking_read(cost, sparse, "error", _mean_interval(cost))
    assert r["key_broken"] and not r["tracks"] and r["note"] == X.KEY_BROKEN
    assert not X.key_broken({"a": 0, "b": 1}, ["a"], ["b"])


def test_the_freeze_takes_the_largest_rho_then_the_family_order():
    reads = {"miss_rate": {"tracks": True, "spearman": 0.4}, "end_error": {"tracks": True, "spearman": -0.6},
             "frame_error": {"tracks": False, "spearman": 0.9}}
    assert X.freeze_rule(reads)["figure"] == "end_error"
    tie = {"extra_rate": {"tracks": True, "spearman": 0.5}, "miss_rate": {"tracks": True, "spearman": 0.5}}
    got = X.freeze_rule(tie)
    assert got["figure"] == "miss_rate" and got["code"] == "RX-tracks" and got["how"] == "tracks"
    none = X.freeze_rule({"miss_rate": {"tracks": False, "spearman": 0.9}})
    assert none == {"figure": "note_error", "orientation": "error", "how": X.FIDELITY_ONLY, "code": "RX-untracked"}


def test_the_passing_only_read_and_intent_to_treat_disagreement_is_stated():
    a, b = {"figure": "miss_rate", "code": "RX-tracks"}, {"figure": "note_error", "code": "RX-untracked"}
    assert X.read_disagreement(a, a) is None
    assert X.read_disagreement(a, b) == {"figure": {"passing_only": "miss_rate", "itt": "note_error"},
                                         "code": {"passing_only": "RX-tracks", "itt": "RX-untracked"}}


# --- the grid pick, the edge, the cross-set read ----------------------------------------------------------------------------

def test_the_grid_has_144_points_in_the_runners_order():
    pts = X.grid_points()
    assert len(pts) == 144 and X.STORED_POINT in pts
    assert pts[0] == {"onset_threshold": 0.3, "frame_threshold": 0.2, "minimum_note_length": 58.0,
                      "melodia_trick": True}
    assert pts[1]["melodia_trick"] is False                  # the last axis fastest
    spec = X.make_spec("bp-grid", "/m.onnx", SHA, settings=dict(T.BP_SETTINGS), grid=X.declared_grid_spec())
    assert [{a: p[a] for a in X.GRID_AXES} for p in X.expected_grid(spec)] == pts


def _pick(means, diffs):
    pts = [dict(X.STORED_POINT, onset_threshold=o) for o in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8)]
    return X.grid_pick(pts, lambda p: means[p["onset_threshold"]],
                       lambda p, mn: diffs.get((p["onset_threshold"], mn["onset_threshold"]), _iv(1, 0.5, 1.5)))


def test_the_pick_is_the_point_nearest_the_defaults_among_those_level_with_the_minimum():
    means = {0.3: 0.4, 0.4: 0.30, 0.5: 0.35, 0.6: 0.31, 0.7: 0.5, 0.8: 0.6}
    got = _pick(means, {(0.5, 0.4): _iv(0.05, -0.01, 0.1), (0.6, 0.4): _iv(0.01, -0.02, 0.04)})
    assert got["minimum"]["onset_threshold"] == 0.4 and got["pick"] == X.STORED_POINT and got["distance"] == 0
    far = _pick(means, {(0.6, 0.4): _iv(0.01, -0.02, 0.04)})
    assert far["pick"]["onset_threshold"] == 0.4             # 0.4 and 0.6 one step each: the better mean
    alone = _pick(means, {})
    assert alone["pick"]["onset_threshold"] == 0.4 and alone["selected_from"] == 6


def test_a_similarity_picks_the_highest_mean():
    means = {0.3: 0.4, 0.4: 0.30, 0.5: 0.35, 0.6: 0.31, 0.7: 0.5, 0.8: 0.6}
    pts = [dict(X.STORED_POINT, onset_threshold=o) for o in means]
    got = X.grid_pick(pts, lambda p: means[p["onset_threshold"]], lambda p, mn: _iv(1, 0.5, 1.5), "similarity")
    assert got["minimum"]["onset_threshold"] == 0.8


def test_the_edge_extends_by_the_axis_step_within_the_parameters_range():
    e = X.edge_extensions(X.STORED_POINT)                    # 58 ms is the lower edge at the stored point itself
    assert e["extend"] == [{"axis": "minimum_note_length", "side": "low", "value": 26.0}]
    hi = X.edge_extensions(dict(X.STORED_POINT, onset_threshold=0.8, frame_threshold=0.2, minimum_note_length=127.7))
    assert {(x["axis"], x["side"], x["value"]) for x in hi["extend"]} == {
        ("onset_threshold", "high", 0.9), ("frame_threshold", "low", 0.1), ("minimum_note_length", "high", 165.4)}
    axes = dict(X.GRID_AXES, onset_threshold=(0.8, 0.9), minimum_note_length=(20.0, 58.0))
    blocked = X.edge_extensions(dict(X.STORED_POINT, onset_threshold=0.9, minimum_note_length=20.0), axes)
    assert {(b["axis"], b["side"]) for b in blocked["blocked"]} == {("onset_threshold", "high"),
                                                                     ("minimum_note_length", "low")}
    assert blocked["extend"] == []


def test_sign_labels_cannot_read_matches():
    assert X.sign_label(_iv(-0.01, -0.02, -0.001))["reading"] == "better"
    assert X.sign_label(_iv(0.01, 0.001, 0.02))["reading"] == "worse"
    assert X.sign_label(_iv(0.0, -0.01, 0.01))["reading"] == "undecided"
    assert X.sign_label(_iv(0.0, 0.0, 0.0))["level_not_readable"]
    assert X.sign_label(_iv(0.01, 0.001, 0.02), "similarity")["reading"] == "better"
    assert X.sign_label(_iv(-0.01, -0.02, -0.001))["words"] == X.SIGN_ONLY
    for m, lo, hi in itertools.product((-0.2, -0.01, 0.0, 0.01), (-0.3, -0.01, 0.0), (0.0, 0.01, 0.3)):
        if lo <= m <= hi:
            assert X.sign_label(_iv(m, lo, hi))["reading"] != "matches"


def test_the_cross_set_read_decides_only_when_both_ways_agree():
    b, w, u = _iv(-0.1, -0.2, -0.01), _iv(0.1, 0.01, 0.2), _iv(-0.05, -0.2, 0.1)
    assert X.cross_set(b, b)["label"] == "better" and X.cross_set(w, w)["label"] == "worse"
    d = X.cross_set(b, w)
    assert d["label"] == "undecided" and d["sign_disagreement"]
    assert X.cross_set(b, u)["label"] == "undecided" and not X.cross_set(b, u)["sign_disagreement"]


def test_the_real_di_labeller_turns_higher_is_better():
    r = X.real_di_label(_iv(0.02, 0.01, 0.03), "note_error")
    assert r["field"] == "f" and r["label"] == "better" and r["words"] == X.SIGN_ONLY and r["note"] is None
    assert X.real_di_label(_iv(-0.02, -0.03, -0.01), "extra_rate") == {
        "field": "precision", "label": "worse", "words": X.SIGN_ONLY, "note": None}
    assert X.real_di_label(_iv(0.0, -0.1, 0.1), "frame_error")["note"]
    assert X.real_di_lead({"P1": "better", "P2": "better", "lists": "better"}, "undecided")
    assert not X.real_di_lead({"P1": "better", "P2": "better", "lists": "better"}, "better")
    assert not X.real_di_lead({"P1": "better", "P2": "undecided", "lists": "better"}, "worse")
    used = {n.attr for n in ast.walk(ast.parse(SRC)) if isinstance(n, ast.Attribute)}
    assert not used & {"clear_above", "decided_worse"}           # never note_tx's own readings


# --- the real-DI guard: P3 never --------------------------------------------------------------------------------------------

def _listing(player, di):
    w = {"key": "w1", "player": player, "kind": "chords", "name": "n1", "consistent": True}
    return {"windows": [w], "files": [{"player": player, "kind": "chords", "name": "n1", "di": di, "midi": di}]}


def test_a_p3_window_or_path_refuses():
    ok = "/x/guitar-techs/P1-downloads/P1_chords/audio/directinput/directinput_n1.wav"
    assert X.real_di_source("truth:w1", _listing("P1", ok))["kind"] == "truth"
    with pytest.raises(SystemExit, match="P3"):
        X.real_di_source("truth:w1", _listing("P3", ok.replace("P1", "P3")))
    with pytest.raises(SystemExit, match="P3"):
        X.real_di_source("truth:w1", _listing("P1", "/x/guitar-techs/P3_music/P1-downloads/a.wav"))
    with pytest.raises(SystemExit, match="P1 and P2 truth windows and the ten lists only"):
        X.real_di_source("goat-dev:item_1")
    with pytest.raises(SystemExit):
        X.real_di_source("/some/path.wav")
    assert X.real_di_source(f"list:{sorted(T.KNOWN_NOTES)[0]}")["kind"] == "list"
    assert X.real_path_refusal("/x/P3_music/a.wav") and X.real_path_refusal(ok) is None


# --- the runner contract ------------------------------------------------------------------------------------------------------

def _ev(on=0.1, off=0.5):
    return {"on": on, "off": off, "pitch": 60, "amp": 0.5, "bends": [0, 1]}


def _rec(mode, spec, **kw):
    return dict({"mode": mode, "versions": {}, "model_sha256": SHA, "threads": 1, "spec": spec,
                 "input_sha256": "b" * 64, "seconds": 1.0, "events": [_ev()]}, **kw)


def test_make_spec_refuses_what_the_runner_refuses():
    base = dict(T.BP_SETTINGS)
    s = X.make_spec("bp-shift", "/m.onnx", SHA, settings=base, offsets_s=[0.0, 0.25], lead_in_s=1.0)
    assert s["lead_in_s"] == 1.0 and s["threads"] == 1
    for kw, msg in ((dict(settings=base, offsets_s=[0.1, 0.1]), "no repeats"),
                    (dict(settings=base, offsets_s=[-0.1]), ">= 0"),
                    (dict(settings=base), "lacks"),
                    (dict(settings=dict(base, extra=1), offsets_s=[0.0]), "exactly"),
                    (dict(settings=base, offsets_s=[0.0], grid={}), "unknown spec keys")):
        with pytest.raises(SystemExit, match=msg):
            X.make_spec("bp-shift", "/m.onnx", SHA, **kw)
    with pytest.raises(SystemExit, match="threads"):
        X.make_spec("mt3", "/m.pth", SHA, threads=3)
    with pytest.raises(SystemExit, match="sha256"):
        X.make_spec("kong", "/m.pth", "nope")
    with pytest.raises(SystemExit, match="grid must be"):
        X.make_spec("bp-grid", "/m.onnx", SHA, settings=base, grid={"maximum_frequency": [1]})
    assert X.make_spec("mt3", "/m.pth", SHA, options={"a": 1})["options"] == {"a": 1}


def test_the_runner_record_check():
    base = dict(T.BP_SETTINGS)
    g = X.make_spec("bp-grid", "/m.onnx", SHA, settings=base, grid={"onset_threshold": [0.4, 0.5]})
    pts = X.expected_grid(g)
    assert [p["onset_threshold"] for p in pts] == [0.4, 0.5] and pts[1] == base
    good = _rec("bp-grid", g, grid=[{"settings": p, "events": [_ev()]} for p in pts])
    assert X.runner_refusal(good, "bp-grid", g, "b" * 64) is None
    assert "points" in X.runner_refusal(dict(good, grid=good["grid"][::-1]), "bp-grid", g, "b" * 64)
    assert "base point" in X.runner_refusal(dict(good, events=[]), "bp-grid", g, "b" * 64)
    assert "input sha256" in X.runner_refusal(good, "bp-grid", g, "c" * 64)
    assert "spec" in X.runner_refusal(good, "bp-grid", dict(g, threads=2), "b" * 64)
    assert "lacks" in X.runner_refusal({k: v for k, v in good.items() if k != "seconds"}, "bp-grid", g, "b" * 64)
    assert "timeline" in X.runner_refusal(dict(good, events=[_ev(-0.1, 0.2)]), "bp-grid", g, "b" * 64)
    sh = X.make_spec("bp-shift", "/m.onnx", SHA, settings=base, offsets_s=[0.0, 0.5])
    rec = _rec("bp-shift", sh, shifts=[{"offset_s": 0.0, "pad_samples": 0, "events": [_ev()]},
                                        {"offset_s": 0.5, "pad_samples": 24000, "events": []}])
    assert X.runner_refusal(rec, "bp-shift", sh, "b" * 64) is None
    assert "zero offset" in X.runner_refusal(dict(rec, events=[]), "bp-shift", sh, "b" * 64)
    sh2 = dict(sh, offsets_s=[0.5])
    rec2 = _rec("bp-shift", sh2, events=[], shifts=[{"offset_s": 0.5, "pad_samples": 24000, "events": []}])
    assert X.runner_refusal(rec2, "bp-shift", sh2, "b" * 64) is None
    assert "pad" in X.runner_refusal(dict(rec2, shifts=[{"offset_s": 0.5, "events": []}]), "bp-shift", sh2, "b" * 64)


def test_a_clipped_notes_bends_are_trimmed_to_its_onset():
    f = X.FRAME_S
    clipped = {"on": 0.0, "off": 10 * f, "pitch": 60, "amp": 0.5, "bends": list(range(14))}   # 4 frames before 0
    inside = {"on": 1.0, "off": 1.0 + 10 * f, "pitch": 62, "amp": 0.5, "bends": list(range(14))}
    short = {"on": 0.0, "off": 10 * f, "pitch": 64, "amp": 0.5, "bends": [1, 2]}
    got = X.runner_notes([clipped, inside, short])
    assert got[0]["bends"] == list(range(4, 14)) and got[1]["bends"] == list(range(14)) and got[2]["bends"] == [1, 2]
    assert clipped["bends"] == list(range(14))                # the record itself untouched


def test_the_download_rules_follow_the_orchestrators_calls():
    text = " ".join(X.DOWNLOAD_RULES)
    assert "weights_only=True" in text and "never weights_only=False" in text and "MR-MT3 dropped" in text
    assert "pickletools" in text and "missing" in text


def test_the_call_and_the_offline_rules(monkeypatch):
    from learn import pipeline_fix as P

    monkeypatch.setattr(P, "REPO", pathlib.Path("/repo"))
    argv = X.runner_argv("/py", "mt3", {"b": 1, "a": 2}, [("a.wav", "a.json"), ("b.wav", "b.json")])
    assert argv == ["/py", "-I", "/repo/learn/readerr_run.py", "mt3", "--spec", '{"a": 2, "b": 1}', "a.wav",
                    "a.json", "b.wav", "b.json"]
    assert X.runner_env({"X": "1"}, True)["HF_HUB_OFFLINE"] == "1" and "HF_HUB_OFFLINE" not in X.runner_env({}, False)
    assert X.checkpoint_refusal({"path": "/p", "sha256": SHA}, SHA) is None
    assert "not the manifest's" in X.checkpoint_refusal({"path": "/p", "sha256": SHA}, "b" * 64)
    assert "pins no path" in X.checkpoint_refusal({"sha256": SHA}, SHA)


# --- the screen ---------------------------------------------------------------------------------------------------------------

def test_the_screen_line_needs_every_pair_to_keep_its_label():
    keep = {"answer": {"reading": "worse"}, "cp50": {"reading": "worse"}}
    flip = {"answer": {"reading": "worse"}, "cp50": {"reading": "undecided"}}
    assert X.screen_line([keep, keep]) == X.SCREEN_HOLDS
    assert X.screen_line([keep, flip]) == X.NO_SCREEN and X.screen_line([]) == X.NO_SCREEN
    assert X.screen_line([{"answer": None, "cp50": None}]) == X.NO_SCREEN
    assert X.sign_agreement({"a": 1, "b": -1, "c": 2}, {"a": 2, "b": 1, "c": 1}) == pytest.approx(2 / 3)
    assert {(w, a, b) for w, a, b in X.SCREEN_PAIRS if w == "exact"} >= {("exact", "xn-list", "xn-bank"),
                                                                          ("exact", "xn-reread", "xn-list")}
    assert len(X.SCREEN_PAIRS) == len(set(X.SCREEN_PAIRS)) == 12


# --- the writes, the ledger body, the module's own guard ---------------------------------------------------------------------

def test_writes_only_under_readerr_and_never_over_a_file(monkeypatch, tmp_path):
    monkeypatch.setattr(X, "readerr_dir", lambda: tmp_path / "readerr")
    sha = X.write_once(X.out_path("trace"), {"a": 1})
    assert len(sha) == 64 and json.loads(X.out_path("trace").read_text()) == {"a": 1}
    with pytest.raises(SystemExit, match="never overwritten"):
        X.write_once(X.out_path("trace"), {"a": 2})
    with pytest.raises(SystemExit, match="outside"):
        X.write_once(tmp_path / "elsewhere.json", {})
    with pytest.raises(SystemExit, match="outside"):
        X.write_once(tmp_path / "readerr" / ".." / "x.json", {})
    with pytest.raises(ValueError):
        X.out_path("candidates")


def _module_aliases(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.asname or a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module in ("learn", "analysis"):
            out |= {a.asname or a.name for a in node.names}
    return out


def test_the_module_assigns_no_attribute_on_an_imported_module():
    tree = ast.parse(SRC)
    mods = _module_aliases(tree)
    assert {"NT", "NR", "SX", "SN", "S", "TX", "NF", "NTR"} <= mods
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        for t in targets:
            for sub in ast.walk(t):
                if isinstance(sub, ast.Attribute):
                    base = sub
                    while isinstance(base, ast.Attribute):
                        base = base.value
                    assert not (isinstance(base, ast.Name) and base.id in mods), ast.unparse(t)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("setattr", "delattr"):
            assert not (isinstance(node.args[0], ast.Name) and node.args[0].id in mods)


def test_every_file_write_goes_through_write_once():
    tree = ast.parse(SRC)
    writers = {"write_text", "write_bytes", "save", "unlink", "rename", "mkdir", "write"}
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                f = node.func
                name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
                if name in writers or name == "open":
                    allowed = fn.name == "write_once" or (fn.name == "npy_bytes_sha" and name == "save")
                    assert allowed, (fn.name, name)


def test_ledger_bodies_hold_hashes_and_counts_only():
    shas = {n: SHA for n in X.OUT_FILES}
    body = X.frozen_body(shas, {"parts": 47, "figures": 29}, "RX-tracks", "miss_rate", X.NO_SCREEN)
    assert X.ledger_body_refusal(body) is None and body["real_compare_sha256"] == SHA
    for bad in ({"trace_sha256": "set0/part01"}, {"counts": {"parts": 1.5}}, {"counts": {"set0/part01": 1}},
                {"code": "XN-both"}, {"figure": "set0/part01"}, {"notes": "anything"}, {"counts": {"x": True}},
                {"screen": "maybe"}):
        assert X.ledger_body_refusal(bad), bad
    with pytest.raises(SystemExit):
        X.frozen_body(shas, {"parts": 47}, "RX-maybe", "miss_rate", X.NO_SCREEN)


def test_the_keys_refusal():
    assert X.keys_refusal({X.PHASE: 1, "phase_fs": 2}, {X.PHASE: 1}) is None
    assert X.PHASE_FROZEN in X.keys_refusal({X.PHASE: 1, X.PHASE_FROZEN: {}}, {X.PHASE: 1})


def _main(*extra):
    base = {S.PHASE: 1, S.PHASE_DRAW: {}, S.phase_answers("fs-stem"): {}, SX.PHASE_BANK: {}, SX.PHASE: {}}
    base.update({k: {} for k in X.EXACT_NEEDS})
    base.update({k: {} for k in extra})
    return base


@pytest.mark.parametrize("cmd", sorted(X.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        X.COMMANDS[cmd](None)


@pytest.mark.parametrize("cmd", sorted(X.COMMANDS))
def test_every_command_refuses_without_the_declaration(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (_main(), None))
    with pytest.raises(SystemExit, match="phase_scratch_readerr"):
        X.COMMANDS[cmd](None)
    m = _main(X.PHASE)
    del m[SX.PHASE_OUTCOME]
    monkeypatch.setattr(S, "on_main", lambda: (m, None))
    with pytest.raises(SystemExit, match="phase_scratch_exact_outcome"):
        X.COMMANDS[cmd](None)


def _on_main_with(monkeypatch, m, pinned):
    from learn import note_replay as NRp

    monkeypatch.setattr(S, "on_main", lambda: (m, None))
    monkeypatch.setattr(SX, "pinned_identity", lambda: {f: True for f in SX.CODE_FILES})
    monkeypatch.setattr(NRp, "ledger_entry", lambda: m)
    monkeypatch.setattr(X, "pinned_identity", lambda: pinned)


def test_the_modules_own_guard_refuses_other_code_or_keys(monkeypatch, tmp_path):
    m = _main(X.PHASE)
    _on_main_with(monkeypatch, m, dict({f: True for f in X.CODE_FILES}, **{X.RUNNER: False}))
    with pytest.raises(SystemExit, match="readerr_run.py"):
        X.require_readerr()
    _on_main_with(monkeypatch, m, {f: True for f in X.CODE_FILES})
    assert X.require_readerr() is m
    from learn import note_replay as NRp

    monkeypatch.setattr(NRp, "ledger_entry", lambda: dict(m, **{X.PHASE_FROZEN: {}}))
    with pytest.raises(SystemExit, match="phase_scratch_readerr_frozen"):
        X.require_readerr()
    monkeypatch.setattr(NRp, "ledger_entry", lambda: m)
    with pytest.raises(SystemExit, match="phase_scratch_readerr_frozen"):
        X.cmd_score(None)                                     # Phase 2 waits for the frozen key ...
    _on_main_with(monkeypatch, _main(X.PHASE, X.PHASE_FROZEN), {f: True for f in X.CODE_FILES})
    with pytest.raises(SystemExit, match="declared, not built"):
        X.cmd_read(None)                                      # ... and then refuses: not built
    monkeypatch.setattr(X, "readerr_dir", lambda: tmp_path)
    for cmd in ("anatomy", "real-compare", "screen-check", "freeze"):
        with pytest.raises(SystemExit, match="trace"):
            X.COMMANDS[cmd](None)                             # every later command waits for the trace
    X.write_once(X.out_path("trace"), {"proofs_hold": False})
    with pytest.raises(SystemExit, match="RX-stop"):
        X.cmd_anatomy(None)


def test_the_cli():
    with pytest.raises(SystemExit):
        X.main(["candidates"])
    assert set(X.COMMANDS) == {"trace", "anatomy", "real-compare", "screen-check", "freeze", "score", "read"}


# --- the played trace against synthesise_redo (numpy) ----------------------------------------------------------------------

class _Bank:
    """A stand-in bank: every string and fret but a few, each sample's length set by its place and shift."""

    def ok(self, s, f):
        return (s, f) not in {(1, 3), (2, 5), (6, 0)}

    def own_cents(self, s, f):
        return ((s * 13 + f * 7) % 11) - 5.0

    def note(self, s, f, cents):
        import numpy as np

        n = int(48000 * (0.25 + 0.15 * ((s * 7 + f) % 9)) * 2 ** (-cents / 1200))
        return np.linspace(1.0, 0.0, max(1, n))


def _random_notes(rng, n):
    out = []
    for _ in range(n):
        on = round(rng.uniform(0.0, 7.0), 3)
        bends = [rng.choice((0, 0, 3, 4, 5)) for _ in range(rng.randint(0, 30))]
        out.append({"on": on, "off": on + rng.uniform(0.03, 2.0), "pitch": rng.randint(40, 84), "amp": 0.5,
                    "bends": bends})
    for _ in range(rng.randint(0, 4)):                      # a chord
        out.append({"on": 3.0, "off": 4.0, "pitch": rng.randint(40, 70), "amp": 0.5, "bends": []})
    return out


def test_the_played_trace_equals_synthesise_redos_report_on_random_lists():
    pytest.importorskip("numpy")
    rng = random.Random(20261125)
    bank = _Bank()
    length = int(8.0 * NR.SR)
    for trial in range(12):
        notes = _random_notes(rng, rng.randint(5, 40))
        ring = ("ring-soft", "ring-on")[trial % 2]
        mutes = sorted(rng.uniform(0, 7) for _ in range(rng.randint(0, 6)))
        cut = trial % 3 == 0
        tune = rng.uniform(-10, 10)
        _, rep = NR.synthesise_redo(notes, length, bank, tune, ring, mutes, 0.0, None, NR.SR, cut=cut)
        per, got = X.played_trace(notes, length, bank, tune, ring, mutes, NR.SR, cut=cut)
        assert got == rep, trial
        assert X.trace_equals_report(got, rep)
        played, skipped = X.as_played(notes, per, length / NR.SR)
        assert len(played) == rep["played"] and len(skipped) == rep["skipped"]
        assert all(p["off"] >= p["on"] for p in played)
    assert not X.trace_equals_report(dict(got, bent=got["bent"] + 1), rep)
