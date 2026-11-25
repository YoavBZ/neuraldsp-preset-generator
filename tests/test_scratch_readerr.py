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


def _args(**kw):
    base = {"shard": (0, 1), "first": 0, "rerun": False, "row": "xr-matched", "set": "first", "combine": False}
    base.update(kw)
    return type("A", (), base)()


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
    assert {"learn/note_replay.py", "learn/pipeline_fix.py", "learn/song_bank.py", "learn/cc_build.py",
            "learn/full_controls_c1b.py", "learn/local_objective.py", "learn/knob_ceiling.py",
            "analysis/aligned.py"} <= set(X.CODE_FILES)
    assert len(X.CODE_FILES) == len(set(X.CODE_FILES)) == 25
    for f in X.CODE_FILES:
        assert (REPO / f).exists(), f


def test_real_compare_refuses_before_writing_unless_every_window_reproduces():
    tree = ast.parse(SRC)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "cmd_real_compare")
    seg = ast.get_source_segment(SRC, fn)
    assert 'if repro != len(report["windows"]):' in seg
    assert seg.index('if repro != len(report["windows"]):') < seg.index("write_once(")
    assert "track1_tx_bp_extras" in seg


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
    assert all(h == [c] for h, c in zip(an["truth_classes_all"], an["truth_classes"]) if c is not None)
    assert an["miss_overlap"]["more_than_one"] == 0


def test_clean_up_comes_straight_after_never_sounded_and_every_holding_class_is_kept():
    assert X.MISS_ORDER[:2] == (X.NEVER_SOUNDED, "clean-up")
    truth = [_n(1.0, 60), _n(1.0, 64), _n(3.0, 67)]
    est = [_n(1.0, 61), _n(1.0, 64)]                    # an unpaired 61: a substitution for the 60 ...
    lost = [dict(_n(1.0, 60), why="over_six"), dict(_n(3.01, 67), why="over_six")]   # ... and the clean-up lost it
    an = X.anatomy(truth, est, lost=lost, skipped={2})
    assert an["truth_classes"] == ["clean-up", None, X.NEVER_SOUNDED]
    assert an["truth_classes_all"][0] == ["clean-up", "substitution", "chord-member"]
    assert an["truth_classes_all"][2] == [X.NEVER_SOUNDED, "clean-up"]
    ov = an["miss_overlap"]
    assert ov["holds"]["clean-up"] == 2 and ov["holds"]["substitution"] == 1 and ov["more_than_one"] == 2
    assert ov["pairs"] == {"clean-up+chord-member": 1, "clean-up+substitution": 1, "never-sounded+clean-up": 1,
                           "substitution+chord-member": 1}
    assert X.partition_holds(an)


def test_an_extras_octave_sub_is_only_below_a_misss_substitution_both_ways():
    truth = [_n(1.0, 60)]
    assert X.anatomy(truth, [_n(1.02, 72)])["est_classes"] == ["harmonic"]     # an octave above: harmonic first
    assert X.anatomy(truth, [_n(0.98, 72)])["est_classes"] == ["harmonic"]
    assert X.anatomy(truth, [_n(1.02, 48)])["est_classes"] == ["octave-sub"]   # an octave below
    for p in (48, 72, 59, 61):
        assert X.anatomy(truth, [_n(1.0, p)])["truth_classes"] == ["substitution"], p


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
    assert dry["reread_pause_error"] == pytest.approx(0.1) and dry["list_env_corr"] is None   # no agree: |excess|
    neg = {"1024": {"pauses_dry": 0.1, "pauses_true": 0.3}}
    assert X.pause_error({"mask": neg}) == pytest.approx(0.2) and X.pause_excess({"mask": neg}) == pytest.approx(-0.2)
    agree = {"1024": dict(mask["1024"], agree=0.9), "2048": dict(mask["2048"], agree=0.7)}
    assert X.pause_error({"mask": agree}) == pytest.approx(0.2)        # the disagreement, when stored
    assert set(dry) == set(X.DRY_FIGURES) == {f for f in X.FIGURES if f.startswith(("reread_", "list_"))}
    beside = X.dry_beside({"xn-reread": {"figures": {"mask": neg}}})
    assert beside == {"reread_pause_excess_signed": pytest.approx(-0.2), "list_pause_excess_signed": None}
    assert not set(beside) & set(X.FIGURES)


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
    assert sorted(r["worse_half"]) == sorted(ks[5:]) and r["label"]["reading"] == "worse"
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


def test_the_list_figures_are_controls_never_frozen():
    assert X.CONTROL_FIGURES == ("list_env_corr", "list_logmel", "list_pause_error")
    reads = {"list_logmel": {"tracks": True, "spearman": 0.9}, "miss_rate": {"tracks": True, "spearman": 0.3}}
    assert X.freeze_rule(reads)["figure"] == "miss_rate"
    assert X.freeze_rule({"list_env_corr": {"tracks": True, "spearman": -0.9}})["code"] == "RX-untracked"


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
    top = X.edge_extensions(dict(X.STORED_POINT, minimum_note_length=10000.0),
                            dict(X.GRID_AXES, minimum_note_length=(9000.0, 10000.0)))
    assert top["blocked"][0]["axis"] == "minimum_note_length"          # the window bounds the length from above


def test_the_edge_extension_repeats_until_the_minimum_leaves_the_edge_or_the_range_blocks_it():
    seen = []

    def lowest_length(axes):                           # the figure falls with the length all the way down
        seen.append(tuple(axes["minimum_note_length"]))
        return dict(X.STORED_POINT, minimum_note_length=min(axes["minimum_note_length"]))
    got = X.edge_rounds(X.GRID_AXES, lowest_length)
    assert seen == [(58.0, 90.0, 127.7), (26.0, 58.0, 90.0, 127.7)]   # 26 then -6: blocked by one frame
    assert got["minimum"]["minimum_note_length"] == 26.0 and len(got["rounds"]) == 2
    assert got["rounds"][-1]["blocked"][0]["value"] == -6.0

    def left_at(target):
        def f(axes):
            vals = sorted(axes["onset_threshold"])
            return dict(X.STORED_POINT, onset_threshold=max(v for v in vals if v <= target),
                        minimum_note_length=90.0)
        return f
    up = X.edge_rounds(X.GRID_AXES, left_at(0.95))          # 0.8 -> 0.9 -> 0.9 is the edge -> 1.0 blocked
    assert up["axes"]["onset_threshold"][-1] == 0.9 and up["rounds"][-1]["blocked"][0]["axis"] == "onset_threshold"
    inside = X.edge_rounds(X.GRID_AXES, left_at(0.55))      # the minimum is not on an edge: one round
    assert len(inside["rounds"]) == 1 and inside["axes"] == {a: tuple(v) for a, v in X.GRID_AXES.items()}


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


def test_the_real_di_arm_reads_the_frozen_figure_per_window():
    rows = [{"group": "P1", "key": f"w{i}", "cluster": f"file{i // 2}", "figures": {"frame_error": 0.5, "note_error": 0.4}}
            for i in range(6)] + [{"group": "lists", "key": "l0", "cluster": "l0", "figures": {"frame_error": 0.1}}]
    cand = {f"w{i}": {"frame_error": 0.5 - 0.1 - 0.01 * i, "note_error": 0.5} for i in range(6)}
    iv = X.real_di_interval(rows, cand, "frame_error", "P1")
    assert iv["clusters"] == 3 and iv["mean"] == pytest.approx(-0.125) and iv["hi90"] < 0   # file means, t interval
    r = X.real_di_label(iv, "frame_error")
    assert r == {"figure": "frame_error", "label": "better", "words": X.SIGN_ONLY, "note": None}
    dry = X.real_di_interval(rows, cand, "reread_logmel", "P1")              # no real-DI version: note error
    assert dry["mean"] == pytest.approx(0.1)
    rd = X.real_di_label(dry, "reread_logmel")
    assert rd["figure"] == "note_error" and rd["note"] and rd["label"] in ("worse", "undecided")
    assert X.real_di_interval(rows, cand, "frame_error", "lists")["clusters"] == 0   # the list has no candidate value
    assert X.real_di_label(_iv(0.02, 0.01, 0.03), "list_env_corr")["figure"] == "note_error"
    assert {X.real_di_figure(f) for f in X.DRY_FIGURES} == {"note_error"}
    assert all(X.real_di_figure(f) == f for f in X.NOTE_FIGURES)
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


def _bp_time(i):
    """Basic Pitch's model_frames_to_time, written out apart from the module: 22,050 Hz, hop 256, 172-frame
    windows, each shifting the clock back by (256 / 22050) x (172 - 43844 / 256) + 0.0018 s."""
    return i * 256 / 22050 - ((256 / 22050) * (172 - 43844 / 256) + 0.0018) * (i // 172)


def _padded_event(start, end, pitch, shift):
    """An event Basic Pitch read on a padded input (frames start to end), re-based and clipped as #617 does."""
    on, off = _bp_time(start) - shift, _bp_time(end) - shift
    return {"on": round(max(on, 0.0), 4), "off": round(off, 4), "pitch": pitch, "amp": 0.5,
            "bends": list(range(end - start))}


def test_a_clipped_notes_bends_are_trimmed_to_its_onset_on_basic_pitchs_clock():
    assert [X.bp_frame_time(i) for i in (0, 171, 172, 400)] == [_bp_time(i) for i in (0, 171, 172, 400)]
    # a 1-s lead-in; a note read from frame 50 (0.58 s) to frame 250 (2.89 s): longer than 1 s after the pad,
    # crossing Basic Pitch's 172-frame window
    ev = _padded_event(50, 250, 60, 1.0)
    keep = [i for i in range(50, 250) if _bp_time(i) >= 1.0]
    assert ev["on"] == 0.0 and ev["off"] - ev["on"] > 1.0
    got = X.runner_notes([ev], 1.0)[0]
    assert got["bends"] == list(range(keep[0] - 50, 200)) and len(got["bends"]) == len(keep)
    assert keep[0] == 87 and got["bends"][0] == 37 and ev["bends"] == list(range(200))   # the record untouched
    inside = _padded_event(120, 300, 62, 1.0)                              # starts after the pad: untouched
    assert inside["on"] > 0 and X.runner_notes([inside], 1.0)[0]["bends"] == list(range(180))
    at_zero = dict(_padded_event(0, 60, 64, 0.0))                          # no pad: never trimmed, even at 0
    assert X.runner_notes([at_zero], 0.0)[0]["bends"] == list(range(60))


def test_every_read_of_a_record_is_trimmed_by_its_own_pad():
    base = dict(T.BP_SETTINGS)
    sh = X.make_spec("bp-shift", "/m.onnx", SHA, settings=base, offsets_s=[0.0, 0.5], lead_in_s=1.0)
    rec = _rec("bp-shift", sh, events=[_padded_event(50, 250, 60, 1.0)],
               shifts=[{"offset_s": 0.0, "pad_samples": 48000, "events": [_padded_event(50, 250, 60, 1.0)]},
                       {"offset_s": 0.5, "pad_samples": 72000, "events": [_padded_event(50, 250, 60, 1.5)]}])
    got = X.record_notes(rec)
    k0 = sum(1 for i in range(50, 250) if _bp_time(i) < 1.0)
    k1 = sum(1 for i in range(50, 250) if _bp_time(i) < 1.5)
    assert [len(s["notes"][0]["bends"]) for s in got["shifts"]] == [200 - k0, 200 - k1] and k1 > k0
    assert got["events"] == got["shifts"][0]["notes"]
    g = X.make_spec("bp-grid", "/m.onnx", SHA, settings=base, grid={"onset_threshold": [0.5]})
    grec = _rec("bp-grid", g, events=[_padded_event(0, 60, 64, 0.0)],
                grid=[{"settings": base, "events": [_padded_event(0, 60, 64, 0.0)]}])
    assert X.record_notes(grec)["grid"][0]["notes"][0]["bends"] == list(range(60))   # no lead-in: no trim
    with pytest.raises(SystemExit, match="not a Basic Pitch record"):
        X.record_notes(_rec("mt3", X.make_spec("mt3", "/m.pth", SHA)))


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
                    allowed = (fn.name in ("write_once", "write_once_npy", "write_bytes_once")
                               or (fn.name == "npy_bytes_sha" and name == "save"))
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
        X.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(X.COMMANDS))
def test_every_command_refuses_without_the_declaration(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (_main(), None))
    with pytest.raises(SystemExit, match="phase_scratch_readerr"):
        X.COMMANDS[cmd](_args())
    m = _main(X.PHASE)
    del m[SX.PHASE_OUTCOME]
    monkeypatch.setattr(S, "on_main", lambda: (m, None))
    with pytest.raises(SystemExit, match="phase_scratch_exact_outcome"):
        X.COMMANDS[cmd](_args())


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
        X.cmd_score_p2a(_args())                                 # Phase 2 waits for the frozen key ...
    _on_main_with(monkeypatch, _main(X.PHASE, X.PHASE_FROZEN), {f: True for f in X.CODE_FILES})
    with pytest.raises(SystemExit, match="waits for the xr- row"):
        X.cmd_read(_args())                                      # ... and then refuses: not built
    monkeypatch.setattr(X, "readerr_dir", lambda: tmp_path)
    for cmd in ("anatomy", "real-compare", "screen-check", "freeze"):
        with pytest.raises(SystemExit, match="trace"):
            X.COMMANDS[cmd](_args())                          # every later command waits for the trace
    X.write_once(X.out_path("trace"), {"proofs_hold": False})
    with pytest.raises(SystemExit, match="RX-stop"):
        X.cmd_anatomy(_args())


def test_the_cli():
    with pytest.raises(SystemExit):
        X.main(["candidates"])
    assert set(X.COMMANDS) == {"trace", "anatomy", "real-compare", "screen-check", "freeze", "notes", "score", "read",
                               "xr-build", "xr-check", "xr-search", "xr-answers", "xr-score", "xr-read"}
    with pytest.raises(SystemExit):
        X.main(["xr-search"])                                    # needs --row
    with pytest.raises(SystemExit):
        X.main(["xr-score", "--row", "hand-plain"])               # never searched, never scored
    with pytest.raises(SystemExit):
        X.main(["xr-search", "--row", "xr-matched", "--shard", "0/4"])


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


# --- Phase 2 (phase_scratch_readerr_p2): the shift vote -------------------------------------------------------------------

def test_the_shift_offsets_are_quarters_of_basic_pitchs_window_hop():
    assert X.SHIFT_FRAMES == (0, 35, 71, 106)
    assert [f * 256 for f in X.SHIFT_FRAMES] == [0, 8960, 18176, 27136]
    assert [round(o, 4) for o in X.SHIFT_OFFSETS_S] == [0.0, 0.4063, 0.8243, 1.2307]
    hop = 36164 / 256                                          # frames in Basic Pitch's window hop
    assert [round(q * hop) for q in (0, 0.25, 0.5, 0.75)] == list(X.SHIFT_FRAMES)


def test_the_shift_vote_only_removes_anchor_notes_as_the_anchor_read_them():
    anchor = [_n(1.0, 60, amp=0.7, bends=[1, 2]), _n(2.0, 62), _n(3.0, 64), _n(4.0, 65)]
    r1 = [_n(1.02, 60), _n(2.01, 62), _n(3.0, 64)]
    r2 = [_n(0.99, 60), _n(2.04, 62), _n(5.0, 70)]
    r3 = [_n(1.01, 60), _n(5.01, 70)]
    kept1, votes = X.shift_vote(anchor, [r1, r2, r3], 1)
    assert kept1 == anchor and votes == [4, 3, 2, 1]           # k = 1 reproduces the anchor (a proof)
    assert X.shift_vote(anchor, [r1, r2, r3], 2)[0] == anchor[:3]
    assert X.shift_vote(anchor, [r1, r2, r3], 3)[0] == anchor[:2]
    k4 = X.shift_vote(anchor, [r1, r2, r3], 4)[0]
    assert k4 == [anchor[0]] and k4[0]["amp"] == 0.7 and k4[0]["bends"] == [1, 2]
    one_to_one = X.shift_vote([_n(1.0, 60), _n(1.02, 60)], [[_n(1.01, 60)]], 2)[1]
    assert one_to_one == [2, 1] or one_to_one == [1, 2]       # one shifted note votes for one anchor note
    assert [n["pitch"] for n in X.shift_unanchored(anchor, [r1, r2, r3])] == []
    assert [n["pitch"] for n in X.shift_unanchored(anchor, [[_n(5.0, 70)], r2, r3])] == [70]


# --- Phase 2: the hybrids ------------------------------------------------------------------------------------------------

def _hybrid_case():
    exact = [_n(1.0, 60, off=1.6), _n(5.0, 67, off=5.5), _n(6.0, 69)]
    reread = [_n(1.0, 60, off=1.5),                     # 0: paired, kept
              _n(1.4, 60, off=1.9),                     # 1: unpaired re-find of 0 (root kept): joined
              _n(1.7, 60, off=2.5),                     # 2: unpaired re-find of 1, chain root 0: joined
              _n(3.0, 62, off=3.6),                     # 3: unpaired, not a re-find: leaves
              _n(3.2, 62, off=3.9),                     # 4: re-find of 3, root unpaired: leaves
              _n(5.01, 67, off=5.4),                    # 5: paired, kept
              _n(5.0, 79)]                              # 6: unpaired harmonic: leaves
    return reread, exact


def test_xr_matched_joins_re_finds_whose_chain_root_is_kept():
    reread, exact = _hybrid_case()
    target = {j: i for i, j in __import__("learn.note_fixes", fromlist=["x"]).refind_pairs(reread)}
    assert target[2] == 1 and target[1] == 0 and target[4] == 3
    assert X.chain_root(2, target, {0, 5}) == 0 and X.chain_root(4, target, {0, 5}) == 3
    notes, rep = X.xr_matched(reread, exact)
    assert [(n["on"], n["pitch"]) for n in notes] == [(1.0, 60), (5.01, 67)]
    assert notes[0]["off"] == 2.5 and notes[1]["off"] == 5.4    # the joined note takes the chain's last end
    assert rep["kept"] == 2 and rep["joined"] == 2 and rep["removed"] == 3 and rep["joins"] == [1, 2]
    assert rep["extended"] == [0] and reread[0]["off"] == 1.5      # the input untouched
    lists, _ = X.xr_lists(reread, exact)
    assert [n["pitch"] for n in lists["hand-plain"]] == [60, 67] and lists["hand-plain"][0]["off"] == 1.5
    assert lists["xr-found"] == [exact[0], exact[1]]
    assert [(n["on"], n["pitch"]) for n in lists["xr-filled"]] == [
        (1.0, 60), (1.4, 60), (1.7, 60), (3.0, 62), (3.2, 62), (5.0, 67), (5.0, 79), (6.0, 69)]


def test_the_join_report():
    reread, exact = _hybrid_case()
    _, rep = X.xr_matched(reread, exact)
    est_cls = [None, "re-find", "re-find", "timing", "re-find", None, "harmonic"]
    tru_cls = [None, None, "substitution"]
    jr = X.join_report(rep, reread, exact, est_cls, tru_cls)
    assert jr == {"joins": 2, "joins_anatomy_refind": 2, "joined_ends_past_partner": 1,
                  "extras_left_out": {"timing": 1, "octave-sub": 0, "semitone-sub": 0},
                  "misses": {"timing": 0, "substitution": 1}}
    assert rep["ends"] == {0: 2.5, 5: 5.4}


def test_the_join_report_keys_each_end_on_the_notes_own_index():
    reread = [_n(5.01, 67, off=5.4), _n(1.0, 60, off=1.5), _n(1.4, 60, off=1.9)]   # kept notes out of onset order
    exact = [_n(1.0, 60, off=1.6), _n(5.0, 67, off=5.5)]
    _, rep = X.xr_matched(reread, exact)
    assert rep["ends"] == {0: 5.4, 1: 1.9} and rep["joins"] == [2] and rep["extended"] == [1]
    jr = X.join_report(rep, reread, exact, [None, None, "re-find"], [None, None])
    assert jr["joined_ends_past_partner"] == 1 and jr["joins_anatomy_refind"] == 1


def test_the_hybrids_on_random_lists():
    rng = random.Random(5)
    for _ in range(40):
        exact = [_n(rng.uniform(0, 8), rng.randint(50, 70)) for _ in range(rng.randint(1, 20))]
        reread = [dict(t, on=t["on"] + rng.uniform(-0.03, 0.03)) for t in exact if rng.random() < 0.8]
        reread += [_n(rng.uniform(0, 8), rng.randint(50, 70), off=None) for _ in range(rng.randint(0, 15))]
        notes, rep = X.xr_matched(reread, exact)
        assert len(notes) == rep["kept"] == T.match_notes(exact, reread)["matched"]
        assert rep["kept"] + rep["joined"] + rep["removed"] == len(reread)
        assert all(n["off"] >= reread_n["off"] for n, reread_n in
                   zip(notes, [reread[j] for j in sorted(j for _, j in rep["pairs"])]))
        assert X.xr_found(reread, exact) == [t for i, t in enumerate(exact) if i in {i for i, _ in rep["pairs"]}]
        assert len(X.xr_filled(reread, exact)) == len(exact) + len(reread) - rep["kept"]


# --- Phase 2: XH_TABLE ----------------------------------------------------------------------------------------------------

E_NUMBERS = ("passes", "fails", "undecided", None)
PAIRED = ("better", "matches", "worse", "undecided", None)


def _xh_reference(en, e, m, stop):
    """XH_TABLE as written, apart from `xh_code`'s order of evaluation."""
    if stop or None in (en, e, m):
        return "XH-stop"
    if e == "worse" or m == "better":
        return "XH-anomaly"
    if en == "passes":
        return "XH-both" if m == "worse" else "XH-extras"
    if m == "worse":
        return "XH-rest"
    return "XH-undecided"


def test_every_pair_of_labels_ends_in_exactly_one_xh_code():
    seen = set()
    for en, e, m, stop in itertools.product(E_NUMBERS, PAIRED, PAIRED, (False, True)):
        got = X.xh_code({"E_number": en, "E": e, "M": m}, stop)
        assert got["code"] == _xh_reference(en, e, m, stop), (en, e, m, stop)
        assert got["code"] in X.XH_CODES and got["next"] and got["meaning"] and "{" not in got["meaning"]
        seen.add(got["code"])
    assert seen == set(X.XH_CODES)
    X.xh_table_guard()


def test_the_xh_words_and_the_next_figure():
    assert X.xh_code({"E_number": "passes", "E": "better", "M": "better"})["code"] == "XH-anomaly"   # an oracle beats
    assert X.xh_code({"E_number": "passes", "E": "better", "M": None})["code"] == "XH-stop"         # no interval
    und = X.xh_code({"E_number": "passes", "E": "better", "M": "undecided"})
    assert und["code"] == "XH-extras" and und["meaning"] == "the extras cost; the rest not decided"
    mat = X.xh_code({"E_number": "passes", "E": "better", "M": "matches"})
    assert mat["meaning"] == "the extras carry reading proper" and mat["figure"]["figure"] == "extra_rate"
    assert mat["figure"]["guard"] == "miss_rate" and "cross-set" in mat["figure"]["rule"]
    rest = X.xh_code({"E_number": "fails", "E": "matches", "M": "worse"})
    assert rest["code"] == "XH-rest" and rest["meaning"].endswith("E fails") and rest["figure"]["figure"] is None
    assert "xr-found" in rest["next"]
    assert X.xh_code({"E_number": "undecided", "E": "undecided", "M": "worse"})["meaning"].endswith("E undecided")
    assert X.xh_code({"E_number": "passes", "E": "better", "M": "worse"})["figure"]["figure"] == "note_error"
    assert X.xh_code({"E_number": "undecided", "E": "undecided", "M": "undecided"})["figure"] == X.XH_FIDELITY


def test_the_xh_table_guard_refuses_a_changed_table(monkeypatch):
    monkeypatch.setattr(X, "XH_CODES", tuple(reversed(X.XH_CODES)))
    with pytest.raises(SystemExit, match="six declared"):
        X.xh_table_guard()
    monkeypatch.undo()
    monkeypatch.setattr(X, "XH_NEXT_FIGURE", {"XH-both": {"figure": "set0/part01"}})
    with pytest.raises(SystemExit, match="not a declared figure"):
        X.xh_table_guard()


def test_e_and_m_follow_s1_intent_to_treat_decides():
    passes, worse, und = _iv(-0.2, -0.3, -0.12), _iv(0.2, 0.1, 0.3), _iv(0.02, -0.05, 0.09)
    assert X.xh_labels(passes, worse) == {"E_number": "passes", "E": "better", "M": "worse"}
    r = X.xh_read({"E": passes, "M": worse}, {"E": passes, "M": und})
    assert r["itt"]["code"] == "XH-both" and r["passing_only"]["code"] == "XH-extras"
    assert r["label"] == S.REFUSAL_SENSITIVE
    same = X.xh_read({"E": passes, "M": worse}, {"E": passes, "M": worse})
    assert same["label"] is None
    none = X.xh_read({"E": passes, "M": worse}, {"E": None, "M": worse})
    assert none["passing_only"]["reading"] == S.NO_PASSING_INTERVAL and none["label"] is None


def test_leave_one_cluster_out_and_the_forward_test():
    vals = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}
    clus = {"a": "c1", "b": "c1", "c": "c2", "d": "c3"}
    got = X.leave_one_cluster_out(vals, clus, lambda v: sum(v.values()))
    assert got == {"c1": 7.0, "c2": 7.0, "c3": 6.0}
    e = {"bks/p1": -0.3, "bks/p2": -0.1, "goat/p3": 0.1, "goat/p4": 0.2, "goat/p5": 0.3,
         "panel/p6": 0.5, "panel/p7": -0.5}
    dry = {"bks/p1": -1.0, "bks/p2": -0.5, "goat/p3": 0.2, "goat/p4": 0.4, "goat/p5": 0.5,
           "panel/p6": -2.0, "panel/p7": 2.0}
    sets = {k: k.split("/")[0] for k in e}
    f = X.forward_test(e, dry, sets)
    assert f["parts"] == 5 and f["spearman"] == pytest.approx(1.0) and f["sign_agreement"] == 1.0   # the 40 pool
    assert f["all_47"]["parts"] == 7 and f["all_47"]["spearman"] < 1.0 and f["all_47"]["sign_agreement"] == \
        pytest.approx(5 / 7)                                     # the panel only beside
    assert f["goat"] == pytest.approx(1.0) and f["bks"] is None   # under 3 parts: no rho
    assert "panel" in f


# --- Phase 2: paths, writes, the search's forbidden list, read_xr_parts --------------------------------------------------

def test_xr_paths_and_keys(monkeypatch, tmp_path):
    monkeypatch.setattr(X, "readerr_dir", lambda: tmp_path / "readerr")
    assert X.xr_path("dry", "xr-matched", "set0/part01").name == "set0__part01.npy"
    assert X.xr_path("build", "first").name == "build-first.json"
    assert X.xr_path("answers", "xr-matched").name == "answers-xr-matched.json"
    with pytest.raises(ValueError):
        X.xr_path("answers", "hand-plain")
    with pytest.raises(ValueError):
        X.xr_path("search", "xr-matched")
    p = X.xr_path("search", "xr-matched", "set0/part01")
    assert X.fresh_xr_path("search", "xr-matched", "set0/part01") == p
    p.parent.mkdir(parents=True)
    p.write_text("{}")
    with pytest.raises(SystemExit, match="never overwritten"):
        X.fresh_xr_path("search", "xr-matched", "set0/part01")
    with pytest.raises(SystemExit, match="never overwritten"):
        X.fresh_xr_path_of(p)
    with pytest.raises(SystemExit, match="outside"):
        X.fresh_xr_path_of(tmp_path / "x.json")
    X.write_bytes_once(S.rerun_path(p), b"{}")
    with pytest.raises(SystemExit, match="never overwritten"):
        X.write_bytes_once(S.rerun_path(p), b"{}")
    assert [X.xr_answers_key(r) for r in X.XR_ROWS] == ["phase_scratch_readerr_xr_answers_matched",
                                                        "phase_scratch_readerr_xr_answers_found",
                                                        "phase_scratch_readerr_xr_answers_filled"]
    assert X.xr_dry_key("first") == X.PHASE_XR_DRY and X.xr_dry_key("found") == "phase_scratch_readerr_xr_dry_found"
    for k in (X.PHASE_P2, X.PHASE_XR_DRY, X.PHASE_XR_OUTCOME, X.xr_answers_key("xr-matched")):
        assert k.startswith(X.KEY_PREFIX) and not k.startswith(X.GUARDED_PREFIXES)
    assert X.set_of_row("xr-found") == "found" and X.XR_SET_ASKED == {"found": "XH-rest", "filled": "XH-undecided"}


def test_write_once_npy_writes_only_under_readerr_and_never_over_a_file(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    monkeypatch.setattr(X, "readerr_dir", lambda: tmp_path / "readerr")
    p = X.xr_path("dry", "xr-matched", "set0/part01")
    sha = X.write_once_npy(p, np.zeros(4, np.float32))
    assert sha == X.file_sha(p) and np.load(p).tolist() == [0.0] * 4
    with pytest.raises(SystemExit, match="never overwritten"):
        X.write_once_npy(p, np.zeros(4, np.float32))
    with pytest.raises(SystemExit, match="outside"):
        X.write_once_npy(tmp_path / "x.npy", np.zeros(4, np.float32))


def test_the_xr_search_opens_none_of_the_forbidden_files():
    base = pathlib.Path("/x/fs/readerr/xr")
    for bad in (base.parent.parent / "exact" / "targets.json", base.parent / "trace.json", base.parent / "anatomy.json",
                base / "answers-xr-matched.json", base.parent.parent / "answers-fs-stem.json",
                base / "score" / "xr-matched" / "k.json", base.parent.parent / "exact" / "target" / "k.json",
                base.parent.parent / "exact" / "score" / "xn-reread" / "k.json"):
        assert X.xr_is_forbidden(bad), bad
        with pytest.raises(SystemExit, match="never opens"):
            X.xr_search_open(bad)
    for ok in (base / "build-first.json", base / "dry" / "xr-matched" / "k.npy", base / "check" / "result.json",
               base / "search" / "xr-matched" / "k.json"):
        assert not X.xr_is_forbidden(ok)


def _reached(root):
    tree = ast.parse(SRC)
    defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    seen, todo = set(), [root]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        todo += [n.id for n in ast.walk(defs[name]) if isinstance(n, ast.Name) and n.id in defs]
    return {k: defs[k] for k in seen}


def test_the_xr_search_never_names_a_target_score_answers_trace_or_anatomy_file():
    """Every function `cmd_xr_search` reaches in this module, found by walking the code: no call opens the targets,
    a score or an answers file, trace.json or anatomy.json; the build, the check and the guitar go through
    `xr_search_open`."""
    reached = _reached("cmd_xr_search")
    assert {"require_xr_build", "require_xr_check", "load_xr_guitar", "xr_path", "fresh_xr_path_of",
            "write_bytes_once", "xr_search_open"} <= set(reached)
    banned_calls = {"require_targets", "require_answers", "require_out", "require_trace", "out_path", "targets_path",
                    "target_path", "score_path", "answers_path", "xr_row_numbers", "read_xr_parts"}
    for name, fn in reached.items():
        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                f = node.func
                called = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
                assert called not in banned_calls, (name, called)
                if called in ("xr_path", "fresh_xr_path") and node.args and isinstance(node.args[0], ast.Constant):
                    assert node.args[0].value not in ("score", "answers", "rows", "report"), (name, node.args[0].value)
    for name in ("require_xr_build", "require_xr_check", "load_xr_guitar"):
        assert any(isinstance(n, ast.Call) and getattr(n.func, "id", None) == "xr_search_open"
                   for n in ast.walk(reached[name])), name


def _score_file(held, ok=True, sha="ans"):
    return {"held": held, "scoring_control_ok": ok, "cen_stored": 1.0, "answers_sha256": sha}


def test_read_xr_parts_equals_read_xn_parts_on_made_up_files(monkeypatch, tmp_path):
    good = {"cen": 2.0, "answer": 1.0, "cp50": 1.5, "cp100": 1.2, "cp200": 1.0, "shrunk": 1.6}
    files = {"set0/p1": (_score_file(good), None),
             "set0/p2": (_score_file(good, ok=False), _score_file(dict(good, answer=0.9))),
             "set1/p3": (_score_file(good, ok=False), _score_file(good, ok=False)),
             "set1/p4": (_score_file(dict(good, cp100=float("inf"))), None)}
    for k, (body, again) in files.items():
        p = tmp_path / f"{k.replace('/', '__')}.json"
        p.write_text(json.dumps(body))
        if again is not None:
            S.rerun_path(p).parent.mkdir(exist_ok=True)
            S.rerun_path(p).write_text(json.dumps(again))
    path_of = (lambda k: tmp_path / f"{k.replace('/', '__')}.json")   # noqa: E731
    monkeypatch.setattr(SX, "score_path", lambda row, k: path_of(k))
    monkeypatch.setattr(X, "xr_path", lambda kind, row=None, pk=None: path_of(pk))
    draw = {"parts": [{"pkey": k} for k in list(files) + ["set1/p5"]]}
    ans = {"refused": {"set1/p5": {"search": {"start": {}}}}, "parts": {k: {} for k in files}}
    want = SX.read_xn_parts(draw, ans, "ans", "xn-reread")
    got = X.read_xr_parts(draw, ans, "ans", "xr-matched")
    assert got == want
    per, refused, replaced, ctl = got
    assert per["set1/p3"] is None and ctl == ["set1/p3"] and "set1/p4" in replaced and per["set1/p5"] is None
    files_bug = tmp_path / "set0__p1.json"
    files_bug.write_text(json.dumps(_score_file(dict(good, answer=0.0))))
    with pytest.raises(SystemExit, match="XH-stop"):
        X.read_xr_parts(draw, ans, "ans", "xr-matched")
    with pytest.raises(SystemExit, match="other answers"):
        X.read_xr_parts(draw, ans, "other", "xr-matched")


@pytest.mark.parametrize("cmd", ["xr-build", "xr-check", "xr-search", "xr-answers", "xr-score", "xr-read"])
def test_every_xr_command_waits_for_the_frozen_key_and_the_p2_declaration(monkeypatch, cmd):
    _on_main_with(monkeypatch, _main(X.PHASE), {f: True for f in X.CODE_FILES})
    with pytest.raises(SystemExit, match="phase_scratch_readerr_frozen"):
        X.COMMANDS[cmd](_args())
    _on_main_with(monkeypatch, _main(X.PHASE, X.PHASE_FROZEN), {f: True for f in X.CODE_FILES})
    with pytest.raises(SystemExit, match="phase_scratch_readerr_p2"):
        X.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd,key", [("xr-search", "phase_scratch_readerr_xr_dry"),
                                     ("xr-answers", "phase_scratch_readerr_xr_dry"),
                                     ("xr-check", "phase_scratch_readerr_xr_dry"),
                                     ("xr-score", "phase_scratch_readerr_xr_answers_matched"),
                                     ("xr-read", "phase_scratch_readerr_xr_dry")])
def test_the_row_waits_for_its_hashes(monkeypatch, cmd, key):
    _on_main_with(monkeypatch, _main(X.PHASE, X.PHASE_FROZEN, X.PHASE_P2), {f: True for f in X.CODE_FILES})
    with pytest.raises(SystemExit, match=key):
        X.COMMANDS[cmd](_args())


def test_the_later_lists_are_built_only_when_the_code_asks(monkeypatch):
    m = _main(X.PHASE, X.PHASE_FROZEN, X.PHASE_P2)
    _on_main_with(monkeypatch, m, {f: True for f in X.CODE_FILES})
    with pytest.raises(SystemExit, match="XH-rest"):
        X.cmd_xr_build(_args(set="found"))
    m[X.PHASE_XR_OUTCOME] = {"code": "XH-both"}
    with pytest.raises(SystemExit, match="XH-undecided"):
        X.cmd_xr_build(_args(set="filled"))
    with pytest.raises(SystemExit, match="unknown build set"):
        X.cmd_xr_build(_args(set="hand-plain"))
    with pytest.raises(SystemExit, match="searched rows"):
        X.cmd_xr_search(_args(row="hand-plain"))


# --- Phase 2a (unit C): notes and score ------------------------------------------------------------------------------------

def test_the_149_candidates():
    ids = X.candidate_ids()
    assert len(ids) == len(set(ids)) == 149
    assert X.STORED_ID in ids and X.STORED_ID == "grid-o0.5-f0.3-l58.0-m1"
    assert ids[144:] == ["lead-in", "shift-k2", "shift-k3", "shift-k4", "f6"]
    assert [X.grid_id(p) for p in X.grid_points()] == ids[:144]
    assert X.BASE not in ids


def test_input_ids_name_no_file_and_shards_partition_them():
    ids = X.input_ids(47, 79, ["chords-six", "bend"])
    assert len(ids) == 128 and ids[0] == "bench-000" and ids[47] == "truth-000" and ids[-2:] == ["list-bend",
                                                                                                 "list-chords-six"]
    assert {X.kind_of(i) for i in ids} == {"bench", "truth", "list"}
    shards = [X.select(ids, (k, 5)) for k in range(5)]
    assert sorted(sum(shards, [])) == sorted(ids) and not set(shards[0]) & set(shards[1])
    assert X.select(ids, (1, 5), first=3) == shards[1][:3]


def test_the_three_reads_per_input():
    s = X.notes_specs("/m.onnx", SHA)
    assert len(X.expected_grid(s["grid"])) == 144 and s["grid"]["settings"] == dict(T.BP_SETTINGS)
    assert X.expected_grid(s["lead"]) == [dict(T.BP_SETTINGS)] and s["lead"]["lead_in_s"] == 1.0
    assert s["shift"]["offsets_s"] == list(X.SHIFT_OFFSETS_S) and "lead_in_s" not in s["shift"]
    assert all(v["threads"] == 1 and v["model_sha256"] == SHA for v in s.values())


def _rec_grid(spec, events_at, top):
    return _rec("bp-grid", spec, events=top, grid=[{"settings": p, "events": events_at(p)} for p in X.expected_grid(spec)])


def _records(stored, lead_extra=None):
    s = X.notes_specs("/m.onnx", SHA)

    def at(p):
        return stored if X.point_key(p) == X.point_key(X.STORED_POINT) else stored[:1]
    g = _rec_grid(s["grid"], at, stored)
    lead_ev = [dict(e) for e in stored] + ([lead_extra] if lead_extra else [])
    lead = _rec_grid(s["lead"], lambda p: lead_ev, lead_ev)
    shifts = [{"offset_s": o, "pad_samples": round(o * 22050), "events": stored if i < 2 else stored[:2]}
              for i, o in enumerate(X.SHIFT_OFFSETS_S)]
    sh = _rec("bp-shift", s["shift"], events=stored, shifts=shifts)
    return s, g, lead, sh


def test_candidates_from_runner_records():
    stored = [_ev(0.5, 0.9), dict(_ev(1.5, 1.9), pitch=62), dict(_ev(2.5, 2.9), pitch=64)]
    clipped = {"on": 0.0, "off": round(_bp_time(250) - 1.0, 4), "pitch": 70, "amp": 0.5, "bends": list(range(200))}
    s, g, lead, sh = _records(stored, lead_extra=clipped)
    for name, rec, mode in (("grid", g, "bp-grid"), ("lead", lead, "bp-grid"), ("shift", sh, "bp-shift")):
        assert X.runner_refusal(rec, mode, s[name], "b" * 64) is None, name
    cands, checks, beside = X.candidates_from_records(g, lead, sh)
    assert sorted(cands) == sorted(X.candidate_ids()[:-1])           # 148: all but F6
    assert cands[X.STORED_ID] == stored and cands["grid-o0.3-f0.2-l58.0-m1"] == stored[:1]
    trimmed = next(e for e in cands["lead-in"] if e["pitch"] == 70)
    assert len(trimmed["bends"]) == sum(1 for i in range(50, 250) if _bp_time(i) >= 1.0)   # the lead-in's clip trimmed
    assert cands["shift-k2"] == stored and cands["shift-k3"] == stored[:2] and cands["shift-k4"] == stored[:2]
    assert checks["votes"] == [4, 4, 2] and checks["k1"] == checks["anchor"] == stored
    assert beside["unanchored_count"] == 0
    proofs = X.notes_proofs(g, sh, checks, stored)
    assert proofs == {"grid_top_equal": True, "grid_stored_point_equal": True, "anchor_equal": True, "k1_equal": True}
    bad = X.notes_proofs(g, sh, checks, stored[:2])
    assert not bad["grid_top_equal"] and not bad["anchor_equal"]


def test_the_combines_refusals():
    assert X.coverage_refusal(["a", "b"], ["a", "b"]) is None
    assert "not done yet" in X.coverage_refusal(["a", "b"], ["a"])
    assert "unexpected" in X.coverage_refusal(["a"], ["a", "c"])
    ok = {f"bench-{j:03d}": {"proofs": {"grid_top_equal": True}} for j in range(47)}
    assert X.bench_proof_refusal(dict(ok, **{"truth-000": {"proofs": {"grid_top_equal": False}}})) is None
    bad = dict(ok, **{"bench-003": {"proofs": {"grid_top_equal": False}}})
    assert "RX-stop" in X.bench_proof_refusal(bad) and "46 of 47" in X.bench_proof_refusal(bad)
    assert "RX-stop" in X.bench_proof_refusal({k: v for k, v in ok.items() if k != "bench-000"})


def _figs(**kw):
    base = {f: 0.5 for f in X.p2a_figures()}
    base.update(kw)
    return {"figures": base, "counts": {"truth": 10, "est": 12, "matched": 8, "extras": {"harmonic": 4},
                                        "misses": {"rest": 2}}}


def test_the_frontier_table():
    per = {"p1": {X.BASE: _figs(), "lead-in": _figs()}, "p2": {X.BASE: _figs()}}
    f = X.frontier(per, ["lead-in", "f6"])
    assert f[X.BASE]["inputs"] == 2 and f[X.BASE]["precision"] == pytest.approx(16 / 24)
    assert f[X.BASE]["recall"] == pytest.approx(0.8) and f[X.BASE]["extras"]["harmonic"] == 8
    assert f["lead-in"]["inputs"] == 1 and "f6" not in f


def test_paired_reads_are_descriptive_sign_only_and_oriented():
    per = {f"set0/p{i}": {X.BASE: _figs(), "lead-in": _figs(note_error=0.4, env_corr=0.6)} for i in range(4)}
    got = X.paired_reads(per, "lead-in", lambda d: {"bks_goat": _iv(sum(d.values()) / len(d), min(d.values()) - 0.01,
                                                                    max(d.values()) - 0.005)})
    assert set(got) == set(X.p2a_figures())
    assert got["note_error"]["label"]["reading"] == "better" and got["note_error"]["words"] == X.P2A_LABEL
    assert got["env_corr"]["label"]["reading"] == "better"          # a similarity that rose: better
    up = X.paired_reads(per, "lead-in", lambda d: {"bks_goat": _iv(0.1, 0.05, 0.15)})
    assert up["env_corr"]["label"]["reading"] == "better" and up["note_error"]["label"]["reading"] == "worse"
    assert got["note_error"]["label"]["words"] == X.SIGN_ONLY and got["logmel"]["parts"] == 4


def test_the_real_di_arm_by_group_and_file():
    rows = [{"group": "P1", "kind": "chords", "cluster": f"P1|chords|n{i // 2}", "iid": f"truth-{i:03d}",
             "figures": {X.BASE: {"note_error": 0.5}, "lead-in": {"note_error": 0.4 - 0.01 * i}}} for i in range(6)]
    rows += [{"group": "lists", "kind": None, "cluster": "l1", "iid": "list-l1",
              "figures": {X.BASE: {"note_error": 0.2}, "lead-in": {"note_error": 0.2}}}]
    got = X.real_reads(rows, "lead-in")
    assert set(got) == {"P1", "P1|chords", "lists"}
    iv = got["P1"]["note_error"]["interval"]
    assert iv["clusters"] == 3 and iv["hi90"] < 0 and got["P1"]["note_error"]["label"]["reading"] == "better"
    assert got["lists"]["note_error"]["label"] is None               # one list: no interval
    assert got["P1|chords"]["note_error"]["interval"] == iv


def test_grid_pick_three_ways_would_pick_not_acted_on():
    per = {}
    for k in ("bks/p1", "goat/p2"):
        per[k] = {}
        for p in X.grid_points():
            ne = abs(p["onset_threshold"] - 0.3) + (0 if p["melodia_trick"] else 0.01)
            per[k][X.grid_id(p)] = {"figures": {"note_error": ne, "logmel": 1.0 + ne, "env_corr": 0.9 - ne}}

    def mean_rows_of(vals):
        m = sum(vals.values()) / len(vals)
        return _iv(m, m - 0.001, m + 0.001)
    got = X.would_picks(per, mean_rows_of)
    assert set(got) == set(X.PICK_BY)
    for f in X.PICK_BY:
        assert got[f]["words"] == X.WOULD_PICK and got[f]["selected_from"] == 144
        assert got[f]["minimum"].startswith("grid-o0.3-") and got[f]["edge_reported_not_extended"]["extend"]
        assert got[f]["pick"] == got[f]["minimum"]                  # nothing else level with it here


def test_the_stored_point_check():
    want = {"logmel": 7.1, "env_corr": 0.97, "mask": {"1024": {"agree": 0.9}}}
    xb = {"p1": {"guitars": {"xn-reread": {"figures": want}}}}
    ok = {"p1": {X.BASE: {"stored_check": {"logmel": 7.1, "env_corr": 0.97, "mask": {"1024": {"agree": 0.9}}}}}}
    assert X.stored_point_refusal(ok, xb) is None
    off = {"p1": {X.BASE: {"stored_check": {"logmel": 7.1000001, "env_corr": 0.97, "mask": {"1024": {"agree": 0.9}}}}}}
    assert "RX-stop" in X.stored_point_refusal(off, xb)
    assert "RX-stop" in X.stored_point_refusal({}, xb)


def test_phase_2a_paths_sit_under_readerr(monkeypatch, tmp_path):
    monkeypatch.setattr(X, "readerr_dir", lambda: tmp_path / "readerr")
    root = (tmp_path / "readerr").resolve()
    for kind, c, i in (("cand", "lead-in", "bench-000"), ("raw", "grid", "truth-001"), ("notes-input", None, "list-x"),
                       ("listing", None, None), ("score-input", None, "bench-001"), ("candidates", None, None)):
        assert root in X.p2a_path(kind, c, i).resolve().parents
    with pytest.raises(ValueError):
        X.p2a_path("elsewhere")
    assert X.p2a_path("listing").name == "notes.json" and X.p2a_path("candidates").name == "candidates.json"


@pytest.mark.parametrize("cmd", ["notes", "score"])
def test_phase_2a_commands_wait_for_their_keys(monkeypatch, cmd):
    _on_main_with(monkeypatch, _main(X.PHASE), {f: True for f in X.CODE_FILES})
    with pytest.raises(SystemExit, match="phase_scratch_readerr_frozen"):
        X.COMMANDS[cmd](_args())
    _on_main_with(monkeypatch, _main(X.PHASE, X.PHASE_FROZEN), {f: True for f in X.CODE_FILES})
    with pytest.raises(SystemExit, match="phase_scratch_readerr_p2"):
        X.COMMANDS[cmd](_args())


def test_score_waits_for_the_notes_listings_hash(monkeypatch):
    _on_main_with(monkeypatch, _main(X.PHASE, X.PHASE_FROZEN, X.PHASE_P2), {f: True for f in X.CODE_FILES})
    with pytest.raises(SystemExit, match="phase_scratch_readerr_notes"):
        X.cmd_score_p2a(_args())


def test_the_cli_shards_spread_cpu_work_but_never_renders():
    assert X.parse_shard("5/8") == (5, 8)
    for bad in ("3/3", "1", "a/b", "-1/2"):
        with pytest.raises(Exception):
            X.parse_shard(bad)
    with pytest.raises(SystemExit):
        X.main(["xr-score", "--row", "xr-matched", "--shard", "0/4"])
