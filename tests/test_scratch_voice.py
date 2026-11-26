"""Pricing the sound gap at the real floor (`learn/scratch_voice.py`, `docs/scratch-voice-plan.md`): the names and keys
(outside every guarded prefix), XV_TABLE (every interval case ends in exactly one code, S1 and N+K included, first
match in order), the term arithmetic on one passing set, the windows, the coverage and its causes, the unclaimed groups,
Spearman, the spend gate, the guards and the read behind fakes. Synthetic keys; pure: runs on the light CI runner (no
numpy)."""
import ast
import itertools
import json
import math
import pathlib
import subprocess
import sys

import pytest

from learn import note_rebuild as NR
from learn import note_transcribe as NT
from learn import scratch_exact as SE
from learn import scratch_notes as SN
from learn import scratch_search as S
from learn import scratch_voice as V

REPO = pathlib.Path(__file__).resolve().parents[1]


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


BETTER, MATCHES, WORSE, UNDECIDED = _iv(-0.3, -0.5, -0.1), _iv(0.0, -0.05, 0.05), _iv(0.3, 0.1, 0.5), \
    _iv(0.08, -0.05, 0.2)
READ = {"better": BETTER, "matches": MATCHES, "worse": WORSE, "undecided": UNDECIDED}
BAD = (None, {}, _iv(0.1, 0.2, 0.05), _iv(math.nan, -0.1, 0.1), _iv(0.0, -math.inf, 0.1),
       {"mean": 0.1, "lo90": None, "hi90": 0.2}, "x")
OK = {c: True for c in V.CHECKS}


def test_the_reading_fixtures_are_what_they_say():
    for name, iv in READ.items():
        assert V.reading(iv)["reading"] == name
    for b in BAD:
        assert V.reading(b) is None


# --- names, keys, files ----------------------------------------------------------------------------------------------------

def test_names_and_keys():
    assert V.PHASE == V.KEY_PREFIX == "phase_scratch_voice"
    assert V.KEYS_TO_COME == ("phase_scratch_voice_dry", "phase_scratch_voice_outcome", "phase_scratch_voice_control",
                              "phase_scratch_voice_control_outcome", "phase_scratch_voice_waiver")
    assert V.CHAIN == ("tr-di", "vc-own", "vc-cut", "vc-fin", "true")
    assert V.TERMS == (("S", "tr-di", "vc-own"), ("N", "vc-own", "vc-cut"), ("K", "vc-cut", "vc-fin"),
                       ("F", "vc-fin", "true"))
    assert V.TOTAL == ("T", "tr-di", "true")
    assert V.BESIDE == (("N+K", "vc-own", "vc-fin"), ("E1", "tr-di", "vc-env"), ("E2", "vc-env", "vc-own"))
    assert set(V.PASSING_SET) == set(V.CHAIN) | {"vc-env"} and len(V.PASSING_SET) == 6
    assert V.BUILT == ("vc-fin", "vc-cut", "vc-own", "vc-env") and V.RENDERED == V.BUILT + ("avg+mild",)
    assert V.RENDERS == {"floors": 470, "repeat": 8} and sum(V.RENDERS.values()) == 478
    assert V.CONTROL_RENDERS == 188 and V.PARTS == 47 and V.DECIDING == ("bks", "goat")
    assert (V.SMALL, V.BIG) == (0.05, 0.10) and V.SEEN_T == (0.822, 0.714, 0.930)


def test_the_key_prefix_is_outside_every_guarded_prefix():
    pre = [p for ps in NT.KEY_PREFIXES.values() for p in ps]
    for k in (V.PHASE,) + V.KEYS_TO_COME:
        assert not k.startswith(tuple(pre)) and not k.startswith(V.GUARDED_PREFIXES)
        assert not S.fs_keys({k: 1}) and not NT.guarded_keys({k: 1}, pre)
        assert SE.keys_refusal({k: 1}, {}) is None                   # the exact-notes guard never sees these keys
        from learn import scratch_rederive as RD
        assert RD.keys_refusal({k: 1}, {}) is None                   # nor the re-derivation's
    V.table_guard()


def test_the_code_files():
    assert V.CODE_FILES[0] == "learn/scratch_voice.py" and len(set(V.CODE_FILES)) == len(V.CODE_FILES)
    assert V.UNIT_FILES == ("learn/voice_build.py", "learn/voice_floors.py")
    for f in (V.MODULE,) + V.PINNED:
        assert (REPO / f).exists(), f
    assert "learn/scratch_readerr.py" not in V.CODE_FILES     # the note track's file: the build's proofs cover it


def test_the_module_imports_only_the_standard_library_at_module_level():
    tree = ast.parse((REPO / "learn" / "scratch_voice.py").read_text())
    mods = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module.split(".")[0])
    assert mods <= {"__future__", "argparse", "bisect", "hashlib", "json", "math", "pathlib", "statistics",
                    "subprocess", "time", "learn"}


def test_no_numpy_at_import():
    code = "import sys; import learn.scratch_voice; print('numpy' in sys.modules, 'scipy' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["False", "False"]


def test_the_paths_sit_apart():
    assert V.voice_dir().name == "voice" and V.voice_dir().parent == S.fs_dir() and V.voice_dir() != SE.exact_dir()
    p = V.dry_path("vc-own", "bks__k/1")
    assert p.parent.name == "vc-own" and p.parent.parent.parent == V.voice_dir() and p.name == "bks__k__1.npy"
    for g in ("tr-di", "true", "avg+mild", "xn-list"):
        with pytest.raises(ValueError):
            V.dry_path(g, "k")
    assert V.floor_path("a/b").parent.name == "floors" and V.repeat_path("a/b").parent.name == "repeat"
    assert {V.build_path().name, V.rows_path().name, V.report_path().name} == {"build.json", "rows.json",
                                                                                "report.json"}


def test_the_declared_constants_trace_to_note_rebuild():
    assert V.WINDOWS["lead_s"] == NR.PRE_ATTACK_S == 0.002 and V.WINDOWS["start_fade_s"] == NR.NOTE_FADE_IN_S
    assert V.WINDOWS["end_fades_s"] == {"repluck": 0.010, "mute": 0.030, "release": 0.150, "sample": 0.150,
                                        "cut": 0.010}
    assert set(V.WINDOWS["end_fades_s"]) == set(V.END_KINDS)
    assert V.WINDOWS["edge_fade_s"] == NR.EDGE_FADE_S and "maximum" in V.WINDOWS["combine"]
    assert (V.NOTCH["fade_out_s"], V.NOTCH["fade_in_s"]) == (0.010, 0.002)
    assert (V.ENV["frame_s"], V.ENV["hop_s"], V.ENV["clamp_db"], V.ENV["floor_db"]) == (0.020, 0.005, 20.0, 40.0)
    assert (V.COVER["frame"], V.COVER["hop"], V.COVER["playing_floor_db"]) == (960, 240, 40.0)
    assert (V.NEAR_S, V.LATE_S) == (NR.TILT_ISOLATED_S, NR.REFINE_S) == (0.6, 0.05)
    assert (V.UNCLAIMED["window_s"], V.UNCLAIMED["min_rise_db"]) == (NR.SNAP_S, NR.REFINE_MIN_RISE_DB) == (0.02, 3.0)
    assert V.TRIM_S == 0.25 and V.HALVES == {"A": (1.0, 5.5), "B": (5.5, 10.0)}
    assert set(V.SYNTH_CAUSES) | set(V.READ_CAUSES) == set(V.CAUSES)
    assert not set(V.SYNTH_CAUSES) & set(V.READ_CAUSES)


def test_the_notch_combines_by_maximum_to_about_minus_15_db():
    out, inn = V.NOTCH["fade_out_s"] * 1000, V.NOTCH["fade_in_s"] * 1000   # ms before the onset
    xs = [i / 1000 for i in range(0, 10001)]                                # 0 to 10 ms before the onset

    def gain(x):
        return max(x / out, 1 - x / inn if x <= inn else 0.0)
    g = [gain(x) for x in xs]
    lo = min(g)
    assert abs(20 * math.log10(lo) - 20 * math.log10(1 / 6)) < 1e-2 and -15.7 < 20 * math.log10(lo) < -15.5
    assert abs(xs[g.index(lo)] - 5 / 3) < 2e-3


# --- the table ---------------------------------------------------------------------------------------------------------------

def test_the_table_is_the_declared_one():
    assert V.XV_CODES == V.XV_DECLARED == ("XV-anomaly", "XV-both", "XV-sound", "XV-notes", "XV-undecided")
    assert V.XV_TABLE[-1][1] == "anything else"
    assert V.SPEND_CODES == ("XV-sound", "XV-both")


def test_the_table_guard_refuses_a_broken_table(monkeypatch):
    monkeypatch.setattr(V, "XV_CODES", V.XV_CODES[:-1])
    with pytest.raises(SystemExit, match="five declared"):
        V.table_guard()
    monkeypatch.undo()
    monkeypatch.setattr(V, "XV_TABLE", V.XV_TABLE[:-1] + (("XV-undecided", "neither reads worse", "", ""),))
    with pytest.raises(SystemExit, match="anything else"):
        V.table_guard()
    monkeypatch.undo()
    monkeypatch.setattr(V, "KEY_PREFIX", "phase_scratch_exact_voice")
    with pytest.raises(SystemExit, match="guarded prefix"):
        V.table_guard()


def _ivs(s="undecided", n="undecided", k="undecided", f="undecided", t="worse"):
    return {"S": READ[s], "N": READ[n], "K": READ[k], "F": READ[f], "T": READ[t]}


def test_the_truth_table():
    want = {("worse", "worse"): "XV-both", ("worse", "matches"): "XV-sound", ("worse", "undecided"): "XV-sound",
            ("matches", "worse"): "XV-notes", ("undecided", "worse"): "XV-notes",
            ("matches", "matches"): "XV-undecided", ("matches", "undecided"): "XV-undecided",
            ("undecided", "matches"): "XV-undecided", ("undecided", "undecided"): "XV-undecided"}
    for (s, n), code in want.items():
        for k in ("matches", "undecided"):
            for f in READ:
                assert V.xv_code(_ivs(s, n, k, f), OK)["code"] == code, (s, n, k, f)
    for s, n in itertools.product(READ, READ):
        if "better" in (s, n):
            assert V.xv_code(_ivs(s, n), OK)["code"] == "XV-anomaly"
    for k in ("worse", "better"):
        rec = V.xv_code(_ivs("worse", "worse", k), OK)
        assert rec["code"] == "XV-anomaly" and rec["anomaly"] == f"K reads {k}"


def test_f_better_is_not_an_anomaly_and_f_is_attached_to_every_code():
    assert V.xv_code(_ivs("worse", "matches", f="better"), OK)["code"] == "XV-sound"
    for s, n, f in itertools.product(READ, READ, READ):
        rec = V.xv_code(_ivs(s, n, f=f), OK)
        assert rec["F"]["reading"] == f and rec["F"]["iv"] == READ[f]


def test_every_check_and_every_bad_interval_is_an_anomaly():
    for c in V.CHECKS:
        for v in (False, None):
            rec = V.xv_code(_ivs("worse", "worse"), dict(OK, **{c: v}))
            assert rec["code"] == "XV-anomaly" and c in rec["anomaly"]
    assert V.xv_code(_ivs("worse", "worse"), {})["code"] == "XV-anomaly"
    for t in V.READ_TERMS:
        for b in BAD:
            rec = V.xv_code(dict(_ivs("worse", "worse"), **{t: b}), OK)
            assert rec["code"] == "XV-anomaly" and t in rec["anomaly"]
    assert V.xv_code({}, OK)["code"] == "XV-anomaly" and V.xv_code(None, None)["code"] == "XV-anomaly"


def test_every_case_ends_in_exactly_one_code():
    cases = tuple(READ.values()) + BAD
    seen = set()
    for s, n, k in itertools.product(cases, cases, cases):
        for f, t in ((MATCHES, WORSE), (WORSE, WORSE), (None, WORSE), (MATCHES, None)):
            for checks in (OK, dict(OK, repeat=False)):
                rec = V.xv_code({"S": s, "N": n, "K": k, "F": f, "T": t}, checks)
                assert rec["code"] in V.XV_CODES
                assert sum(rec["code"] == c for c in V.XV_CODES) == 1
                seen.add(rec["code"])
    assert seen == set(V.XV_CODES)


def test_the_meanings_and_next():
    snd = V.xv_code(_ivs("worse", "matches"), OK)
    assert snd["dominates"] and "it dominates" in snd["meaning"] and "not a sound gap" in snd["meaning"]
    snd2 = V.xv_code(_ivs("worse", "undecided"), OK)
    assert not snd2["dominates"] and "only if N reads matches" in snd2["meaning"]
    for rec in (snd, snd2, V.xv_code(_ivs("worse", "worse"), OK)):
        assert rec["spend_gated"] and "control" in rec["next"] and str(V.CONTROL_RENDERS) in rec["next"]
        assert "waiver" in rec["next"]
    notes = V.xv_code(_ivs("matches", "worse"), OK)
    assert not notes["spend_gated"] and "no synthesis spend" in notes["next"] and "screen only" in notes["next"]
    und = V.xv_code(_ivs(f="worse"), OK)
    assert und["code"] == "XV-undecided" and "fs-tone" in und["next"]
    assert "fs-tone" not in V.xv_code(_ivs(f="matches"), OK)["next"]
    assert V.xv_code(_ivs("better"), OK)["next"] == "stop; to the user"


def test_the_route_is_worded_into_next():
    route = {"shares": {"synthesis rules": 0.7, "note reading": 0.3}}
    for s, n in (("worse", "worse"), ("matches", "worse")):
        nxt = V.xv_code(_ivs(s, n), OK, route)["next"]
        assert "synthesis rules 70%" in nxt and nxt.index("synthesis rules") < nxt.index("note reading 30%")
    assert "not available" in V.xv_code(_ivs("matches", "worse"), OK)["next"]


def test_n_plus_k_beside_marks_cut_sensitive():
    rec = V.xv_read(_ivs("worse", "worse"), OK, MATCHES)
    assert rec["code"] == "XV-both" and rec["with_n_plus_k"] == "XV-sound" and rec["label"] == V.CUT_SENSITIVE
    rec = V.xv_read(_ivs("worse", "worse"), OK, WORSE)
    assert rec["with_n_plus_k"] == "XV-both" and rec["label"] is None
    rec = V.xv_read(_ivs("matches", "undecided"), OK, BETTER)       # N+K better: the alternative is an anomaly
    assert rec["code"] == "XV-undecided" and rec["with_n_plus_k"] == "XV-anomaly" and rec["label"] == V.CUT_SENSITIVE
    assert V.xv_read(_ivs("worse", "worse"), OK, None)["label"] == V.CUT_SENSITIVE


def test_s1_the_intent_to_treat_read_sits_beside():
    a, b = {"code": "XV-sound"}, {"code": "XV-undecided"}
    assert V.with_itt(a, b, {}) == (a, None, None)
    assert V.with_itt(a, b, {"k": "silent"}) == (a, b, S.REFUSAL_SENSITIVE)
    assert V.with_itt(a, dict(a), {"k": "silent"})[2] is None
    assert V.with_itt(a, None, {"k": "silent"})[2] == S.REFUSAL_SENSITIVE


# --- the term arithmetic -----------------------------------------------------------------------------------------------------

def _floors(t=0.8, s=0.4, n=0.2, k=0.05, env=0.1, avg=0.3):
    """Floors with T = t, S = s, N = n, K = k (F the rest), E1 = env."""
    true = 2.0
    trdi = true * math.exp(t)
    own = trdi * math.exp(-s)
    cut = own * math.exp(-n)
    fin = cut * math.exp(-k)
    return {"true": true, "tr-di": trdi, "vc-own": own, "vc-cut": cut, "vc-fin": fin,
            "vc-env": trdi * math.exp(-env), "avg+mild": true * math.exp(avg)}


def test_the_terms_of_one_part_sum_to_t():
    t = V.part_terms(_floors())
    assert abs(t["S"] - 0.4) < 1e-12 and abs(t["N"] - 0.2) < 1e-12 and abs(t["K"] - 0.05) < 1e-12
    assert abs(t["F"] - (0.8 - 0.65)) < 1e-12 and abs(t["T"] - 0.8) < 1e-12
    assert abs(t["N+K"] - 0.25) < 1e-12 and abs(t["E1"] - 0.1) < 1e-12 and abs(t["E2"] - 0.3) < 1e-12
    assert V.sum_gap(t) <= V.SUM_TOL
    assert abs(t["E1"] + t["E2"] - t["S"]) < 1e-12


def test_a_missing_or_silent_floor_gives_none():
    for bad in (None, 0.0, -1.0, math.inf, math.nan, True):
        d = dict(_floors(), **{"vc-cut": bad})
        t = V.part_terms(d)
        assert t["N"] is None and t["K"] is None and t["S"] is not None and t["N+K"] is not None
        assert V.sum_gap(t) is None and not V.passing(d)
    assert not V.passing(dict(_floors(), **{"vc-env": None}))      # vc-env is one of the six
    assert V.passing(dict(_floors(), **{"avg+mild": None}))        # avg+mild is not
    assert V.part_terms(None)["T"] is None


def test_one_passing_set_for_every_term():
    floors = {"bks__a": _floors(), "goat__b": dict(_floors(), **{"vc-env": math.inf}),
              "goat__c": dict(_floors(), true=None), "panel__d": _floors(0.5)}
    vals, refused, gaps = V.term_values(floors)
    assert sorted(refused) == ["goat__b", "goat__c"]
    assert "vc-env" in refused["goat__b"] and "true" in refused["goat__c"]
    for t, v in vals.items():
        assert sorted(v) == ["bks__a", "panel__d"], t
    assert sorted(gaps) == ["bks__a", "panel__d"] and V.sum_holds(gaps)
    assert not V.sum_holds({}) and not V.sum_holds({"x": 1e-9}) and not V.sum_holds({"x": None})
    itt = V.itt_terms(vals, refused)
    assert itt["S"]["goat__b"] == itt["S"]["goat__c"] == 0.0 and itt["S"]["bks__a"] == vals["S"]["bks__a"]


# --- the windows, the coverage and its causes --------------------------------------------------------------------------------

def test_played_windows_and_skipped_spans():
    notes = [{"on": 1.0, "off": 1.4}, {"on": 1.2, "off": 1.3}, {"on": 0.001, "off": 0.5}, {"on": 2.0, "off": 1.9}]
    trace = [{"played": True, "end": 1.55, "end_kind": "release"}, {"played": False, "why": "no free string"},
             {"played": True, "end": 9.0, "end_kind": "sample"}, {"played": False, "why": "zero length"}]
    win, skip = V.played_windows(notes, trace, n=48000 * 5, rate=48000)
    assert win == [(int(round(0.998 * 48000)), int(round(1.55 * 48000)), "release"), (0, 48000 * 5, "sample")]
    assert skip == [(int(round(1.198 * 48000)), int(round(1.3 * 48000))), (int(round(1.998 * 48000)), 96000)]


def test_the_union_keeps_the_kind_that_reaches_the_end():
    assert V.union([]) == []
    assert V.union([(0, 10, "release"), (5, 8, "mute"), (20, 30, "repluck")]) == [[0, 10, "release"],
                                                                                  [20, 30, "repluck"]]
    assert V.union([(0, 10, "release"), (5, 15, "mute")]) == [[0, 15, "mute"]]
    assert V.union([(0, 10, "release"), (10, 12, "sample")]) == [[0, 12, "sample"]]      # touching windows join
    assert V.union([(0, 10, "release"), (3, 10, "mute")]) == [[0, 10, "release"]]       # a tie keeps the first


def test_uncovered_pieces():
    m = [[10, 20, "a"], [30, 40, "b"]]
    st = [x[0] for x in m]
    assert V.uncovered_pieces(0, 50, m, st) == [(0, 10, None, 0), (20, 30, 0, 1), (40, 50, 1, None)]
    assert V.uncovered_pieces(12, 18, m, st) == []
    assert V.uncovered_pieces(15, 35, m, st) == [(20, 30, 0, 1)]
    assert V.uncovered_pieces(0, 5, [], []) == [(0, 5, None, None)]


def test_each_cause():
    r = 1000                                        # 1 sample a millisecond
    left, right = [0, 100, "release"], [2000, 2100, "repluck"]
    assert V.cause_of(500, left, right, [(400, 600)], rate=r) == "skipped"
    assert V.cause_of(1960, left, right, [], rate=r) == "late-onset"          # 40 ms before our window opens
    assert V.cause_of(1940, left, right, [], rate=r) == "no-note"             # 60 ms before, 1.84 s after the end
    assert V.cause_of(650, left, right, [], rate=r) == "after-release"        # 550 ms after the end
    assert V.cause_of(750, left, right, [], rate=r) == "no-note"              # 650 ms after
    assert V.cause_of(750, left, right, [], near=False, rate=r) == "after-release"
    for kind in V.END_KINDS:
        assert V.cause_of(150, [0, 100, kind], None, [], rate=r) == f"after-{kind}"
    assert V.cause_of(50, None, None, [], rate=r) == "no-note"
    with pytest.raises(ValueError, match="end kind"):
        V.cause_of(150, [0, 100, None], None, [], rate=r)


def test_the_swapped_cause_order():
    r = 1000
    left, right = [0, 100, "release"], [160, 300, "repluck"]          # a 60-ms gap after a release
    for mid in (120, 140):                                               # both within 50 ms of the next window
        assert V.cause_of(mid, left, right, [], rate=r) == "late-onset"
        assert V.cause_of(mid, left, right, [], rate=r, swapped=True) == "after-release"
    far = [2000, 2100, "mute"]
    assert V.cause_of(1960, left, far, [], rate=r, swapped=True) == "late-onset"     # the end is 1.86 s away
    assert V.cause_of(500, left, far, [(400, 600)], rate=r, swapped=True) == "skipped"
    assert V.cause_of(1940, left, far, [], rate=r, swapped=True) == "no-note"


def test_the_held_frames():
    rate, frame, hop = 100, 10, 5                   # 0.1-s frames at a 0.05-s hop
    levels = [-10.0] * 260
    levels[0] = 0.0                                 # the loudest
    levels[40] = -60.0                              # under the playing floor
    fa = V.held_frames(levels, "A", frame, hop, rate)
    centres = [(i * hop + frame / 2) / rate for i in fa]
    assert min(centres) >= 1.25 and max(centres) < 5.75 and 40 not in fa
    fb = V.held_frames(levels, "B", frame, hop, rate)
    assert min((i * hop + frame / 2) / rate for i in fb) >= 5.75 and not set(fa) & set(fb)
    assert V.held_frames([], "A") == []


def test_cover_figures_on_made_up_windows():
    rate, frame, hop = 100, 10, 10                  # 0.1-s frames, no overlap
    levels = [0.0] * 120                            # 12 s, every frame playing
    win = [(125, 300, "release"), (500, 575, "mute")]            # 1.25-3.0 s, 5.0-5.75 s
    skip = [(400, 450)]
    f = V.cover_figures(levels, win, skip, "A", frame, hop, rate)
    # held A: centres in [1.25, 5.75): frames 12..56 (45 frames); uncovered 3.0-5.0 s (20 frames) and the first
    # frame's 0.05 s before 1.25 s (half a frame)
    assert f["frames"] == 45
    assert abs(f["uncovered_weight"] - 20.5) < 1e-12 and f["whole_frame_share"] == 20 / 45
    by = f["by_cause"]
    assert abs(by["skipped"] - 5.0) < 1e-12                       # 4.0-4.5 s
    assert abs(by["late-onset"] - 1.5) < 1e-12                    # 4.9-5.0 s, and 1.20-1.25 s before the first window
    assert abs(by["after-release"] - 6.0) < 1e-12                 # 3.0-3.6 s (within 600 ms of the end)
    assert abs(by["no-note"] - 8.0) < 1e-12                       # 3.6-4.0 s and 4.5-4.9 s
    assert abs(sum(by.values()) - f["uncovered_weight"]) < 1e-12
    assert abs(f["by_cause_any_distance"]["after-release"] - 6.0 - 8.0) < 1e-12
    assert f["uncovered_share"] == 20.5 / 45
    assert f["by_cause_swapped"] == by                            # here no piece is both late and after an end
    # a 60-ms gap after a release: the declared order books it to late onset, the swapped order to the release
    g = V.cover_figures(levels, [(125, 300, "release"), (306, 575, "mute")], [], "A", frame, hop, rate)
    assert abs(g["uncovered_weight"] - 0.5 - 0.6) < 1e-12        # 1.20-1.25 s and 3.00-3.06 s
    assert abs(g["by_cause"]["late-onset"] - 1.1) < 1e-12 and g["by_cause"]["after-release"] == 0.0
    sw = g["by_cause_swapped"]
    assert abs(sw["late-onset"] - 0.5) < 1e-12 and abs(sw["after-release"] - 0.6) < 1e-12   # 1.20-1.25 s has no end
    assert abs(sum(sw.values()) - g["uncovered_weight"]) < 1e-12


def test_unclaimed_groups():
    hop, rate = 48, 48000                           # rise_curve's 1-ms hop
    rise = [0.0] * 3000
    rise[1015] = 5.0                                # a rise at 1.015 s
    rise[2030] = 2.9                                # under 3 dB
    u = V.unclaimed_groups([1.0, 2.0, 2.5, 0.0], rise, hop, rate)
    assert u["groups"] == 4 and u["flags"] == [False, True, True, True] and u["share"] == 0.75
    assert V.unclaimed_groups([1.0], rise, hop, rate, window=0.01)["flags"] == [True]   # 15 ms off, a 10-ms window
    assert V.unclaimed_groups([], rise, hop)["share"] is None
    assert V.unclaimed_groups([5.0], rise, hop)["flags"] == [True]                      # past the curve's end


def test_the_unclaimed_rule_at_exactly_20_ms():
    hop, rate = 48, 48000
    for at, t in ((1000, 1.02), (1000, 0.98)):     # the rise exactly 20 ms after, then before, the onset
        rise = [0.0] * 3000
        rise[at] = 3.0                              # exactly 3 dB: claimed (the rule is "under 3 dB")
        lo = max(0, int((t - 0.02) * rate) // hop)
        hi = int((t + 0.02) * rate) // hop + 1
        assert lo <= at < hi, (t, lo, hi)
        assert V.unclaimed_groups([t], rise, hop, rate)["flags"] == [False]
    rise = [0.0] * 3000
    rise[1022] = 9.0                                # 22 ms after: outside the window
    assert V.unclaimed_groups([1.0], rise, hop, rate)["flags"] == [True]


def test_the_route_split():
    cover = {"a": {"by_cause": {"after-release": 3.0, "late-onset": 1.0}},
             "b": {"by_cause": {"no-note": 1.0, "skipped": 1.0}}, "c": {"by_cause": {"no-note": 100.0}}}
    r = V.route_split(cover, ["a", "b"])
    assert r["total_weight"] == 6.0 and r["shares"] == {"synthesis rules": 4 / 6, "note reading": 2 / 6}
    assert abs(sum(r["cause_shares"].values()) - 1) < 1e-12
    assert V.route_split({}, ["a"])["shares"] is None
    assert "note reading 33%" in V.route_text(r) and V.route_text(r).startswith("synthesis rules 67%")


def test_the_route_is_marked_cause_order_sensitive_when_the_leader_changes():
    a = {"shares": {"synthesis rules": 0.4, "note reading": 0.6}}
    b = {"shares": {"synthesis rules": 0.7, "note reading": 0.3}}
    r = V.route_order(a, b)
    assert r["order_label"] == V.CAUSE_ORDER_SENSITIVE and r["swapped_shares"] == b["shares"]
    text = V.route_text(r)
    assert text.startswith("note reading 60%") and "cause-order-sensitive" in text
    assert "with the order swapped, synthesis rules 70%; note reading 30%" in text
    same = V.route_order(a, {"shares": {"synthesis rules": 0.45, "note reading": 0.55}})
    assert same["order_label"] is None and "cause-order-sensitive" not in V.route_text(same)
    assert V.route_order(a, {"shares": None})["order_label"] is None
    assert V.leading(None) is None and V.leading({"x": 0.5, "a": 0.5}) == "a"
    nxt = V.xv_code(_ivs("matches", "worse"), OK, r)["next"]
    assert "cause-order-sensitive" in nxt and "note reading 60%" in nxt and "synthesis rules 70%" in nxt


def test_spearman_and_ranks():
    assert V.ranks([3, 1, 2, 2]) == [4.0, 1.0, 2.5, 2.5]
    assert V.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert V.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert V.spearman([1, 2, 3, 4, 5], [2, 1, 4, 3, 5]) == pytest.approx(0.8)
    assert V.spearman([1, 2], [1, 2]) is None and V.spearman([1, 1, 1], [1, 2, 3]) is None
    assert V.spearman([1, 2, 3], [1, 2]) is None


def test_the_median_split_the_largest_and_the_tags():
    share = {"a": 0.1, "b": 0.2, "c": 0.3, "d": None, "e": 0.2}
    above, below, med = V.median_split(share, ["a", "b", "c", "d", "e"])
    assert med == 0.2 and above == ["c"] and below == ["a", "b", "e"]
    assert V.median_split({}, ["a"]) == ([], [], None)
    assert V.largest({"a": 0.1, "b": -0.5, "c": 0.3, "d": None, "e": 0.3}, list("abcde")) == ["b", "c", "e"]
    assert len(V.tag("bks__k/1")) == 12 and V.tag("x") != V.tag("y")
    parts = [{"pkey": "goat__z", "set": "goat"}, {"pkey": "goat__a", "set": "goat"},
             {"pkey": "bks__m", "set": "bks"}, {"pkey": "panel__a", "set": "panel"}]
    assert V.check_parts(parts) == ["bks__m", "goat__a"]


# --- the spend gate ------------------------------------------------------------------------------------------------------------

def test_the_spend_gate():
    for kind in V.SPEND_KINDS:
        assert "read and its audit first" in V.spend_refusal({}, kind)
        assert "read and its audit first" in V.spend_refusal({V.PHASE_OUTCOME: {}}, kind)
        for code in ("XV-anomaly", "XV-undecided", "XV-notes"):
            assert V.spend_refusal({V.PHASE_OUTCOME: {"code": code}}, kind)
        for code in V.SPEND_CODES:
            m = {V.PHASE_OUTCOME: {"code": code}}
            assert "control" in V.spend_refusal(m, kind) and "waiver" in V.spend_refusal(m, kind)
            assert V.spend_refusal(dict(m, **{V.PHASE_CONTROL: {}}), kind)        # declared is not run
            assert V.spend_refusal(dict(m, **{V.PHASE_CONTROL_OUTCOME: {}}), kind)   # an outcome needs its code
            assert V.spend_refusal(dict(m, **{V.PHASE_CONTROL_OUTCOME: {"code": "x"}}), kind) is None
            assert V.spend_refusal(dict(m, **{V.PHASE_WAIVER: {"user_words": "go", "date": "2026-11-27"}}),
                                   kind) is None
            assert V.spend_refusal(dict(m, **{V.PHASE_WAIVER: {"date": "2026-11-27"}}), kind)
    assert "no synthesis spend" in V.spend_refusal({V.PHASE_OUTCOME: {"code": "XV-notes"}}, "synthesis")
    with pytest.raises(ValueError):
        V.spend_refusal({}, "training")


def test_require_spend_refuses_off_main_and_closed(monkeypatch):
    monkeypatch.setattr(V, "on_main", lambda: (None, "this checkout's ['learn/scratch_voice.py'] differ"))
    with pytest.raises(SystemExit, match="differ"):
        V.require_spend("synthesis")
    monkeypatch.setattr(V, "on_main", lambda: ({V.PHASE_OUTCOME: {"code": "XV-both"}}, None))
    with pytest.raises(SystemExit, match="control"):
        V.require_spend("synthesis")
    m = {V.PHASE_OUTCOME: {"code": "XV-both"}, V.PHASE_CONTROL_OUTCOME: {"code": "a control code"}}
    monkeypatch.setattr(V, "on_main", lambda: (m, None))
    assert V.require_spend("search-row") is m


# --- the guards ------------------------------------------------------------------------------------------------------------------

def _args(**kw):
    return type("A", (), dict(kw))()


def test_the_keys_refusal_sees_its_own_keys_only():
    assert V.keys_refusal({"phase_scratch_voice": 1, "phase_fs": 2}, {"phase_scratch_voice": 1}) is None
    assert V.keys_refusal({"phase_scratch_exact_outcome": 1}, {}) is None
    assert "phase_scratch_voice_dry" in V.keys_refusal({"phase_scratch_voice_dry": {}}, {})
    assert "phase_scratch_voice_outcome" in V.keys_refusal({}, {"phase_scratch_voice_outcome": {}})


def test_on_main_refuses_other_code_or_keys(monkeypatch):
    from learn import note_replay as NRP

    main = {V.PHASE: {}}
    monkeypatch.setattr(V, "main_entry", lambda: (main, None))
    monkeypatch.setattr(V, "pinned_identity", lambda: {"learn/scratch_voice.py": False, "learn/x.py": True})
    m, why = V.on_main()
    assert m is main and "scratch_voice.py" in why and "differ from main's" in why
    monkeypatch.setattr(V, "pinned_identity", lambda: {f: True for f in V.CODE_FILES})
    monkeypatch.setattr(NRP, "ledger_entry", lambda: dict(main, phase_scratch_voice_dry={}))
    assert "phase_scratch_voice_dry" in V.on_main()[1]
    monkeypatch.setattr(NRP, "ledger_entry", lambda: dict(main, phase_fs_other={}))   # another track's key: no refusal
    assert V.on_main() == (main, None)
    monkeypatch.setattr(V, "main_entry", lambda: (None, "main's ledger is not readable: x"))
    assert V.on_main() == (None, "main's ledger is not readable: x")


def test_pinned_identity_asks_git_for_every_code_file(monkeypatch):
    calls = []

    def fake(*a):
        calls.append(a)
        return type("R", (), {"returncode": 0 if a[-1] != "learn/note_rebuild.py" else 1})()
    monkeypatch.setattr(V, "_git", fake)
    got = V.pinned_identity()
    assert set(got) == set(V.CODE_FILES) and got["learn/note_rebuild.py"] is False
    assert all(c[:3] == ("diff", "--quiet", "origin/main") for c in calls)


@pytest.mark.parametrize("cmd", sorted(V.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(V, "on_main", lambda: (None, "this checkout's ['learn/scratch_voice.py'] differ from main's"))
    with pytest.raises(SystemExit, match="differ from main's"):
        V.COMMANDS[cmd](_args())


MAIN_BEFORE = {S.PHASE_DRAW: {}, S.phase_answers("fs-stem"): {}, SE.PHASE_TARGETS: {}}


@pytest.mark.parametrize("cmd", sorted(V.COMMANDS))
def test_every_command_refuses_without_the_declaration_or_its_keys(monkeypatch, cmd):
    main = dict(MAIN_BEFORE)
    monkeypatch.setattr(V, "on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="has no phase_scratch_voice:"):
        V.COMMANDS[cmd](_args())
    main[V.PHASE] = {}
    with pytest.raises(SystemExit, match="has no phase_scratch_voice_dry"):
        V.COMMANDS[cmd](_args())
    del main[SE.PHASE_TARGETS]
    with pytest.raises(SystemExit, match="has no phase_scratch_exact_targets"):
        V.COMMANDS[cmd](_args())


def test_the_cli_knows_only_the_read():
    assert sorted(V.COMMANDS) == ["read"]
    with pytest.raises(SystemExit):
        V.main(["build"])


# --- the read behind fakes ------------------------------------------------------------------------------------------------

HALF = 0.108


def _fake_set_rows(draw):
    sets = {p["pkey"]: p["set"] for p in draw["parts"]}

    def set_rows(sd, draw_, values, keys=None):
        ks = [k for k, v in values.items() if v is not None and (keys is None or k in keys)]
        dec = [values[k] for k in ks if sets.get(k) in ("bks", "goat")]
        if not dec:
            return None
        m = sum(dec) / len(dec)
        iv = {"mean": m, "lo90": m - HALF, "hi90": m + HALF}
        return {"bks_goat": {"all": iv, "clean": iv, "crunch": iv}, "deciding_pool": iv}
    return set_rows


def _world(tmp_path, monkeypatch, refuse=None, s=0.5, n=0.0, k_=0.0):
    """Six made-up parts (two clusters on the 40's sets, two panel), T = 0.822 on every part, S = s, N = n, K = k_.
    A refused part's coverage is all 'no-note', so a route that took it in would lean to note reading."""
    keys = ["bks__a", "bks__b", "goat__c", "goat__d", "panel__e", "panel__f"]
    draw = {"parts": [{"pkey": k, "set": k.split("__")[0], "cluster": f"x|c{i % 2}"} for i, k in enumerate(keys)]}
    monkeypatch.setattr(SN, "set_rows", _fake_set_rows(draw))
    monkeypatch.setattr(SE, "context", lambda: (draw, None))
    monkeypatch.setattr(SE, "share", lambda sd, draw_, num, den, keys=None: {"defined": False, "why": "fake"})
    monkeypatch.setattr(V, "voice_dir", lambda: tmp_path)
    monkeypatch.setattr(V, "require_voice", lambda *a: {})
    fl = {k: _floors(0.822, s, n, k_) for k in keys}
    stored = {k: {"true": {"held": fl[k]["true"]}, "tr-di": {"held": fl[k]["tr-di"]},
                  "tr_di_less_true": math.log(fl[k]["tr-di"] / fl[k]["true"])} for k in keys}
    stored_iv = _fake_set_rows(draw)(None, draw, {k: s["tr_di_less_true"] for k, s in stored.items()})["bks_goat"]["all"]
    monkeypatch.setattr(V, "_stored_floors", lambda m: (stored, stored_iv))
    build = {"proofs_hold": True, "parts": {}}
    for k in keys:
        build["parts"][k] = {"guitars": {g: {"audio_sha256": f"{g}-{k}"} for g in V.RENDERED},
                             "unclaimed": {"share": 0.1 * (keys.index(k) + 1)},
                             "cover": {"by_cause": {"after-release": 2.0, "late-onset": 1.0},
                                       "by_cause_swapped": {"after-release": 2.5, "late-onset": 0.5},
                                       "uncovered_share": 0.03},
                             "ends": {"sample": 1}}
        if refuse and k in refuse:
            build["parts"][k]["cover"] = {"by_cause": {"no-note": 50.0}, "by_cause_swapped": {"no-note": 50.0}}
        rec = {"part": k, "guitars": {g: {"held": fl[k][g], "dry_sha256": f"{g}-{k}"} for g in V.RENDERED}}
        if refuse and k in refuse:
            rec["guitars"]["vc-env"].update(held=math.inf, refused="silent render", reran=True)
        V.floor_path(k).parent.mkdir(parents=True, exist_ok=True)
        V.floor_path(k).write_text(json.dumps(rec))
    for k in V.check_parts(draw["parts"]):
        V.repeat_path(k).parent.mkdir(parents=True, exist_ok=True)
        V.repeat_path(k).write_text(json.dumps({"holds": True}))
    V.build_path().write_text(json.dumps(build))
    monkeypatch.setattr(V, "_build", lambda m: json.loads(V.build_path().read_text()))
    return keys


def test_the_read_on_made_up_floors(monkeypatch, tmp_path, capsys):
    keys = _world(tmp_path, monkeypatch)
    V.cmd_read(_args())
    rep = json.loads(V.report_path().read_text())
    rows = json.loads(V.rows_path().read_text())
    r = rep["read"]
    assert rep["checks"] == OK and rep["t_reproduced"]["holds"]
    assert r["code"] == "XV-sound" and r["label"] is None and r["cut_label"] is None and r["itt"] is None
    assert r["readings"]["S"]["reading"] == "worse" and r["xv"]["F"]["reading"] == "worse"
    assert abs(r["terms"]["S"]["mean"] - 0.5) < 1e-12 and r["mean_sum_gap"] < 1e-12 and r["sum_max_gap"] < 1e-12
    assert r["passing_parts_on_the_40"] == 4 and r["refused"] == []
    assert r["route"]["shares"] == {"synthesis rules": 2 / 3, "note reading": 1 / 3}
    assert r["route"]["swapped_shares"] == {"synthesis rules": 2.5 / 3, "note reading": 0.5 / 3}
    assert r["route_label"] is None and r["route_swapped"]["shares"] == r["route"]["swapped_shares"]
    assert r["unclaimed"]["above"] == 2 and r["unclaimed"]["at_or_below"] == 2
    assert r["unclaimed"]["spearman_with_S"] == V.NOT_COMPUTABLE       # S is the same on every part
    assert len(r["cluster_left_out"]["S"]) == 2 and len(r["largest_three"]["T"]["tags"]) == 3
    assert rep["beside"]["sample_ends"] == 6
    text = json.dumps(rows) + json.dumps(rep)
    for k in keys:                                  # the read's files carry tags, never part keys
        assert k not in text
    assert "XV READ: XV-sound" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="never overwritten"):
        V.cmd_read(_args())


def test_the_read_with_a_refusal_reads_passing_only_and_itt_beside(monkeypatch, tmp_path):
    keys = _world(tmp_path, monkeypatch, refuse={"bks__a", "goat__c"}, s=0.2)
    V.cmd_read(_args())
    rep = json.loads(V.report_path().read_text())
    r = rep["read"]
    assert len(r["refused"]) == 2 and r["passing_parts_on_the_40"] == 2
    assert r["code"] == "XV-sound" and r["itt"] is not None              # passing-only decides: S +0.2 reads worse
    assert r["itt"]["xv"]["code"] == "XV-undecided" and r["label"] == S.REFUSAL_SENSITIVE   # the zeros pull S to +0.1
    assert abs(r["terms"]["S"]["mean"] - 0.2) < 1e-12
    # the refused parts are left out of the route, the median split and Spearman
    assert r["route"]["shares"] == {"synthesis rules": 2 / 3, "note reading": 1 / 3}
    assert r["route"]["by_cause"]["no-note"] == 0.0
    assert r["unclaimed"]["above"] + r["unclaimed"]["at_or_below"] == 2 and r["unclaimed"]["spearman_parts"] == 2
    assert r["unclaimed"]["spearman_with_S"] == V.NOT_COMPUTABLE
    # the refusal report carries tags and the floors' own reasons, never part keys
    rr = rep["refusal_report"]
    assert sorted(rr["kinds"]) == sorted(V.tag(k) for k in ("bks__a", "goat__c"))
    assert all(v["reasons"] == ["vc-env"] and v["kind"] == "technical" for v in rr["kinds"].values())
    assert rr["pooled"]["refused"] == 2 and rr["pooled"]["parts"] == 4
    assert rep["refused_why"] == {V.tag(k): {"vc-env": "silent render"} for k in ("bks__a", "goat__c")}
    text = V.rows_path().read_text() + V.report_path().read_text()
    for k in keys:
        assert k not in text, k


def test_the_cut_label_through_the_read(monkeypatch, tmp_path):
    _world(tmp_path, monkeypatch, s=0.5, n=0.15, k_=-0.05)    # N +0.15 worse; N+K +0.10 undecided; K matches
    V.cmd_read(_args())
    r = json.loads(V.report_path().read_text())["read"]
    assert r["readings"]["N"]["reading"] == "worse" and r["readings"]["K"]["reading"] == "matches"
    assert r["readings"]["N+K"]["reading"] == "undecided"
    assert r["code"] == "XV-both" and r["xv"]["with_n_plus_k"] == "XV-sound" and r["cut_label"] == V.CUT_SENSITIVE


def test_a_malformed_floor_stops_the_read(monkeypatch, tmp_path):
    for bad in (None, math.inf, 0.0, -1.0):
        _world(tmp_path, monkeypatch)
        rec = json.loads(V.floor_path("goat__c").read_text())
        rec["guitars"]["vc-own"]["held"] = bad                 # no refused flag
        V.floor_path("goat__c").write_text(json.dumps(rec, allow_nan=True))
        with pytest.raises(SystemExit, match="malformed floor record"):
            V.cmd_read(_args())
        assert not V.report_path().exists() and not V.rows_path().exists()


def test_a_floor_record_never_sets_the_stored_floors():
    stored = {"k": {"true": {"held": 1.0}, "tr-di": {"held": 2.0}}}
    for g in ("true", "tr-di", "xn-list"):
        with pytest.raises(SystemExit, match="not one of the rendered guitars"):
            V.floors_of(stored, {"k": {"guitars": {g: {"held": 1.0}}}})


def test_a_non_finite_stored_floor_gets_an_explicit_reason(monkeypatch, tmp_path):
    stored = {"k": {"true": {"held": math.inf}, "tr-di": {"held": None}}}
    fl, why = V.floors_of(stored, {"k": {"guitars": {"vc-own": {"held": 1.5}}}})
    assert fl["k"] == {"true": None, "tr-di": None, "vc-own": 1.5}
    assert "stored true floor" in why["k"]["true"] and "stored tr-di floor" in why["k"]["tr-di"]
    _world(tmp_path, monkeypatch)
    real = V._stored_floors
    st, iv = real(None)
    st["panel__e"]["true"]["held"] = math.nan                  # a panel part: the 40 still reproduce T
    st["panel__e"]["tr_di_less_true"] = None
    monkeypatch.setattr(V, "_stored_floors", lambda m: (st, iv))
    V.cmd_read(_args())
    rep = json.loads(V.report_path().read_text())
    assert "stored true floor" in rep["refused_why"][V.tag("panel__e")]["true"]
    assert rep["refusal_report"]["kinds"][V.tag("panel__e")]["reasons"] == ["true"]
    assert rep["t_reproduced"]["holds"] and rep["read"]["code"] == "XV-sound"


def test_the_read_refuses_a_pending_rerun_a_foreign_guitar_and_a_missing_floor(monkeypatch, tmp_path):
    _world(tmp_path, monkeypatch)
    rec = json.loads(V.floor_path("bks__a").read_text())
    rec["guitars"]["vc-cut"].update(refused="silent render")
    V.floor_path("bks__a").write_text(json.dumps(rec))
    with pytest.raises(SystemExit, match="not rerun once"):
        V.cmd_read(_args())
    rec["guitars"]["vc-cut"] = {"held": 1.0, "dry_sha256": "other"}
    V.floor_path("bks__a").write_text(json.dumps(rec))
    with pytest.raises(SystemExit, match="not rendered from the build's guitar"):
        V.cmd_read(_args())
    V.floor_path("bks__a").unlink()
    with pytest.raises(SystemExit, match="no floor record"):
        V.cmd_read(_args())
    assert not V.report_path().exists() and not V.rows_path().exists()


def test_a_failed_repeat_or_proof_reads_anomaly(monkeypatch, tmp_path):
    _world(tmp_path, monkeypatch)
    for k in ("bks__a",):
        V.repeat_path(k).write_text(json.dumps({"holds": False}))
    V.cmd_read(_args())
    r = json.loads(V.report_path().read_text())["read"]
    assert r["code"] == "XV-anomaly" and "repeat" in r["xv"]["anomaly"]


def test_t_reproduces():
    st = {"k": {"true": {"held": 1.0}, "tr-di": {"held": math.exp(0.5)}, "tr_di_less_true": 0.5}}
    iv = _iv(0.822, 0.714, 0.930)
    assert V.t_reproduces(st, iv, dict(iv))["holds"]
    assert not V.t_reproduces(st, iv, _iv(0.822, 0.714, 0.9301))["holds"]
    assert V.t_reproduces(st, _iv(0.8224, 0.714, 0.930), _iv(0.8224, 0.714, 0.930))["holds"]   # 3 places
    assert not V.t_reproduces(st, _iv(0.83, 0.714, 0.930), _iv(0.83, 0.714, 0.930))["holds"]
    st["k"]["tr_di_less_true"] = 0.4
    assert not V.t_reproduces(st, iv, dict(iv))["holds"]
    # None stored values: a part with no stored floor must also have no stored T, and the intervals must exist
    none = {"k": {"true": {"held": None}, "tr-di": {"held": 2.0}, "tr_di_less_true": None}}
    assert V.t_reproduces(none, iv, dict(iv))["per_part"] and V.t_reproduces(none, iv, dict(iv))["holds"]
    assert not V.t_reproduces({"k": dict(none["k"], tr_di_less_true=0.5)}, iv, dict(iv))["per_part"]
    assert V.t_reproduces({"k": {}}, iv, dict(iv))["per_part"]          # nothing stored: None equals None
    for a, b in ((None, iv), (iv, None), (None, None)):
        assert not V.t_reproduces(st, a, b)["holds"]


def test_floors_of_and_pending_reruns():
    stored = {"k": {"true": {"held": 1.0}, "tr-di": {"held": 2.0}}}
    recs = {"k": {"guitars": {"vc-own": {"held": 1.5}, "vc-env": {"held": math.inf, "refused": "silent", "reran": True},
                              "vc-cut": {"held": 1.2, "refused": "silent"}}}}
    fl, why = V.floors_of(stored, recs)
    assert fl["k"] == {"true": 1.0, "tr-di": 2.0, "vc-own": 1.5, "vc-env": None, "vc-cut": None}
    assert why == {"k": {"vc-env": "silent", "vc-cut": "silent"}}
    assert V.pending_reruns(recs) == [("k", "vc-cut")]


# --- the ledger -----------------------------------------------------------------------------------------------------------

def test_the_declaration_in_the_ledger():
    doc = json.loads((REPO / "docs" / "dev-test-ledger.json").read_text())
    e = next(t for t in doc["tests"] if t["test_id"] == V.LEDGER_ID)
    assert V.PHASE in e
    d = e[V.PHASE]
    assert d["plan"].startswith(V.PLAN) and (REPO / V.PLAN).exists()
    assert tuple(d["table"]["codes"]) == V.XV_DECLARED and d["table"]["last_row"] == "anything else"
    assert tuple(d["keys_to_come"]) == V.KEYS_TO_COME
    assert d["renders"]["floors"] == 470 and d["renders"]["repeat"] == 8 and d["renders"]["control"] == 188
    for k in ("planner", "review", "label"):
        assert d["seen"][k], k
    assert "960" in d["seen"]["definitions"]["uncovered"] and "40 dB" in d["seen"]["definitions"]["uncovered"]
    assert V.CAUSE_ORDER_SENSITIVE in d["beside_cause_order"] and "vc-env comes from tr-di" in d["guitar_sources"]
    assert set(d["review_fixes"]) >= {"cause_order", "tags", "malformed_floor"} and "re-fit" in d["limits_finish_refit"]
