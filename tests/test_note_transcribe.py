"""The note rebuild's redo (`learn/note_transcribe.py`, `learn/bp_run.py`; `docs/note-rebuild-plan.md` section 12):
the clean-up, the note matching, the ear page's kinds, windows, items and cards, every content check's pass rule, the
calibration's pick, the ring variant's rule, the refusal count, the expected-failure table, the overlap song by song,
the lock and the install's pair, the guards and every command's refusal. Pure: runs on the light CI runner (no numpy);
Basic Pitch is never imported. The last test needs the stored data (skipped elsewhere)."""
import json
import pathlib

import pytest

from learn import bp_run as BP
from learn import note_transcribe as T

REPO = pathlib.Path(__file__).resolve().parents[1]


def _n(on, pitch, off=None, bends=()):
    return {"on": on, "off": on + 0.4 if off is None else off, "pitch": pitch, "bends": list(bends)}


# --- the declared settings -------------------------------------------------------------------------------------------------

def test_the_settings_are_the_declared_ones():
    assert T.BP_SETTINGS == {"onset_threshold": 0.5, "frame_threshold": 0.3, "minimum_note_length": 58.0,
                             "minimum_frequency": 60.0, "maximum_frequency": 1400.0, "melodia_trick": True,
                             "multiple_pitch_bends": True}
    assert sorted(T.BP_SETTINGS) == sorted(BP.SETTING_KEYS)
    assert (T.BP_UP, T.BP_DOWN, T.BP_SR) == (147, 320, 22050) and 48000 * 147 / 320 == 22050
    assert T.KEEP_MIDI == (36, 88) and T.MERGE_S == 0.030 and T.MAX_AT_ONCE == 6 and T.OCTAVE_UP_BELOW == 38
    assert T.MARGIN_S == 1.0 and T.BP_PEAK_DBFS == -1.0
    assert T.BASIC_PITCH[:2] == ("basic-pitch", "0.4.0") and T.ONNXRUNTIME[:2] == ("onnxruntime", "1.19.2")
    assert not any("coreml" in r for r in T.REQUIREMENTS)


def test_the_checks_are_the_six_declared():
    assert list(T.CONTENT) == ["annotated-found", "onsets-found", "playing-covered", "judge-accepts", "ring-kept",
                               "chords-kept"]
    assert [k for k, v in T.CONTENT.items() if not v["blocking"]] == ["annotated-found", "onsets-found"]   # 12m
    c = T.CONTENT
    assert (c["annotated-found"]["median"], c["annotated-found"]["floor"], c["annotated-found"]["admission"]) == \
        (0.85, 0.75, "consistent")
    assert (c["onsets-found"]["share"], c["onsets-found"]["within_s"]) == (0.90, 0.050)
    assert (c["playing-covered"]["playing"], c["playing-covered"]["silent"]) == (0.95, 0.10)
    assert (c["judge-accepts"]["pause_over_true"], c["judge-accepts"]["gap_s"], c["judge-accepts"]["gap_db"]) == \
        (0.05, 0.250, 40.0)
    assert (c["ring-kept"]["after_s"], c["ring-kept"]["median_db"], c["ring-kept"]["min_frames"],
            c["ring-kept"]["env_corr"]) == (0.600, 3.0, 20, 0.80)
    assert (c["chords-kept"]["note_f"], c["chords-kept"]["chord_recall"], c["chords-kept"]["min_chord_notes"]) == \
        (0.85, 0.85, 5)
    assert not hasattr(T, "RISE_LEVELS") and not hasattr(T, "RISE_PRECISION")             # retired in 12m
    assert T.CALIBRATION_PASS == 25 and T.DEV_COUNT == 27
    assert T.P2_CHORD_TRIGGER == 0.85 and T.FLAG_TRIGGER == 3
    assert T.REFUSAL_STOP == 3 and T.DECIDING == ("bks", "goat")


# --- the clean-up -------------------------------------------------------------------------------------------------------------

def test_clean_up():
    notes = [_n(0.0, 30), _n(0.0, 89), _n(0.0, 37), _n(0.5, 60), _n(0.52, 60, off=1.5), _n(0.6, 60)]
    kept, cnt = T.clean_transcribed(notes)
    assert cnt == {"out_of_range": 2, "octave_up": 1, "merged": 1, "over_six": 0}
    assert [(n["on"], n["pitch"]) for n in kept] == [(0.0, 49), (0.5, 60), (0.6, 60)]
    assert kept[1]["off"] == 1.5                           # the merged twin's end is the later one
    chord = [_n(1.0 + 0.001 * k, 40 + 5 * k, off=3.0) for k in range(8)]
    kept, cnt = T.clean_transcribed(chord)
    assert len(kept) == 6 and cnt["over_six"] == 2 and [n["pitch"] for n in kept] == [40, 45, 50, 55, 60, 65]
    kept, cnt = T.clean_transcribed([_n(0.0, 36), _n(0.0, 38)])
    assert [n["pitch"] for n in kept] == [38, 48] and cnt["octave_up"] == 1


def test_events_and_window():
    ev = [{"on": 0.1, "off": 0.5, "pitch": 60, "amp": 0.4, "bends": [0, 1]}, {"on": 11.0, "off": 11.5, "pitch": 62}]
    notes = T.notes_from_events(ev)
    assert notes[0]["bends"] == [0, 1] and notes[1]["bends"] == []
    assert [n["pitch"] for n in T.in_window(notes, 10.25)] == [60]
    assert BP.event_record((0.123456, 0.5, 60, 0.3333333, [0, 1, 2])) == {"on": 0.1235, "off": 0.5, "pitch": 60,
                                                                          "amp": 0.333333, "bends": [0, 1, 2]}
    assert BP.event_record((0.1, 0.2, 61, 0.5, None))["bends"] == []


def test_bp_run_arguments_refuse():
    s = json.dumps(T.BP_SETTINGS)
    model, settings, pairs = BP.parse_args(["--model", "m.onnx", "--settings", s, "a.wav", "a.json", "b.wav", "b.json"])
    assert model == "m.onnx" and settings == T.BP_SETTINGS and pairs == [("a.wav", "a.json"), ("b.wav", "b.json")]
    for bad in (["--settings", s, "a.wav", "a.json"], ["--model", "m", "--settings", s, "a.wav"],
                ["--model", "m", "--settings", json.dumps({"onset_threshold": 0.5}), "a", "b"]):
        with pytest.raises(SystemExit):
            BP.parse_args(bad)


def test_bp_run_imports_nothing_heavy():
    src = (REPO / "learn" / "bp_run.py").read_text()
    top = src.split("def main(")[0]
    assert "basic_pitch" not in "".join(ln for ln in top.splitlines() if ln.startswith(("import", "from")))
    assert "onnxruntime" not in "".join(ln for ln in top.splitlines() if ln.startswith(("import", "from")))
    import ast
    ast.parse(src, feature_version=(3, 9))                 # it runs on the venv's Python 3.9

    def imported(text):
        out = set()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                out |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                out.add(node.module.split(".")[0])
        return out
    for name in ("note_transcribe", "scratch_notes", "note_rebuild", "note_rebuild_ear", "scratch_search"):
        got = imported((REPO / "learn" / f"{name}.py").read_text())   # only bp_run, in its venv, imports them
        assert not got & {"basic_pitch", "onnxruntime"}, name


# --- matching -----------------------------------------------------------------------------------------------------------------

def test_match_notes_one_to_one():
    ref = [_n(0.0, 60), _n(0.0, 64), _n(0.5, 67), _n(1.0, 60)]
    est = [_n(0.02, 60), _n(0.03, 60), _n(0.06, 64), _n(0.98, 60), _n(2.0, 70)]
    m = T.match_notes(ref, est, 0.050)
    assert m["matched"] == 2 and m["ref_matched"] == [0, 3]        # 64 is 60 ms late; the second 60 has no partner
    assert m["recall"] == 0.5 and m["precision"] == 0.4 and m["f"] == pytest.approx(4 / 9)
    assert T.pooled_f([m, T.match_notes(ref, ref)]) == pytest.approx((2 * 2 + 2 * 4) / (9 + 8))
    assert T.match_notes([], [])["f"] is None


def test_repeat_identical():
    a = [{"on": 0.1, "pitch": 60}]
    assert T.repeat_identical([a, list(a), [dict(a[0])]])
    assert not T.repeat_identical([a, [{"on": 0.1001, "pitch": 60}], a]) and not T.repeat_identical([])


# --- the ear page's items --------------------------------------------------------------------------------------------------

def test_kinds():
    chords = [_n(t, p) for t in (0.0, 1.0, 2.0) for p in (48, 52, 55)] + [_n(3.0, 60)]
    assert "chord-led" in T.kind_flags(chords) and "single-note" not in T.kind_flags(chords)
    line = [_n(0.3 * k, 60 + k % 5, off=0.3 * k + 0.2) for k in range(10)]
    assert T.kind_flags(line) == {"single-note"}
    bent = [_n(1.0 * k, 64, off=1.0 * k + 0.8, bends=[3] * 20) for k in range(3)]
    assert "bends" in T.kind_flags(bent) and "single-note" not in T.kind_flags(bent)
    ring = [_n(0.5 * k, 60 + k, off=0.5 * k + 1.5) for k in range(6)]
    assert "let-ring" in T.kind_flags(ring)
    assert T.kind_flags([]) == set()


def test_grid_window_and_items():
    notes = [_n(t, 60) for t in (1.0, 2.0, 16.0, 17.0, 18.0, 19.0)]
    assert T.grid_window(notes, 40.0) == 10.0                 # [10.25, 20.25) holds the most onsets (earliest of a tie)
    assert T.grid_window(notes, 9.0) is None and T.grid_window([], 20.0) == 0.0
    kinds = {"a": {"chord-led", "let-ring"}, "b": {"chord-led"}, "c": {"single-note"}, "d": {"bends"},
             "e": {"let-ring"}, "f": {"let-ring"}}
    assert T.pick_ear_items(list("abcdef"), kinds) == {"chord-led": "a", "single-note": "c", "bends": "d",
                                                        "let-ring": "e"}
    assert "bends" not in T.pick_ear_items(list("abc"), kinds)


def test_ear_cards_are_thirteen_with_one_hidden_control():
    cards = T.ear_cards(["item_57", "item_46", "item_160", "item_102"],
                        {"chord-led": "item_5", "single-note": "item_14", "bends": "item_23", "let-ring": "item_29"})
    assert len(cards) == 13 and sum(c["control"] for c in cards) == 1
    assert sum(c["cls"] == "clean" and not c["control"] for c in cards) == 8
    assert sorted(c["item"] for c in cards if c["cls"] == "crunch") == ["item_14", "item_23", "item_29", "item_5"]
    assert [c["n"] for c in cards] == list(range(1, 14)) and len({c["id"] for c in cards}) == 13
    assert cards == T.ear_cards(["item_102", "item_160", "item_46", "item_57"],
                                {"chord-led": "item_5", "single-note": "item_14", "bends": "item_23",
                                 "let-ring": "item_29"})


# --- the checks' pass rules ----------------------------------------------------------------------------------------------------

def test_onsets_and_playing():
    assert T.onsets_found_pass({"attacks": 10, "found": 9})
    assert not T.onsets_found_pass({"attacks": 10, "found": 8})
    assert T.onsets_found_pass({"attacks": 0, "found": 0}) is None
    assert T.playing_covered_pass({"playing_share": 0.95, "silent_share": 0.10})
    assert not T.playing_covered_pass({"playing_share": 0.94, "silent_share": 0.0})
    assert not T.playing_covered_pass({"playing_share": 0.99, "silent_share": 0.11})
    assert T.playing_covered_pass({"playing_share": None}) is None


def _pauses(dry, true):
    return {h: {n: {"dry": dry, "true": true} for n in ("1024", "2048", "4096")} for h in ("A", "B")}


def test_judge_accepts():
    ok = {"judge_finite": True, "pauses": _pauses(0.25, 0.20), "longest_gap_s": 0.25}
    assert T.judge_accepts_pass(ok)
    assert not T.judge_accepts_pass(dict(ok, judge_finite=False))                       # (i) J0 refuses
    assert T.judge_accepts_pass(dict(ok, judge_finite=None))                            # no stem: (ii), (iii)
    assert not T.judge_accepts_pass(dict(ok, pauses=_pauses(0.2501, 0.20)))             # (ii)
    p = _pauses(0.20, 0.20)
    p["B"]["4096"] = {"dry": 0.4, "true": 0.3}
    assert not T.judge_accepts_pass(dict(ok, pauses=p))                                 # any half, any frame size
    assert not T.judge_accepts_pass(dict(ok, longest_gap_s=0.251))                      # (iii)


def test_ring_kept():
    assert T.ring_kept_pass({"late_frames": 20, "late_median_db": -3.0, "env_corr": 0.80})
    assert not T.ring_kept_pass({"late_frames": 20, "late_median_db": 3.1, "env_corr": 0.9})
    assert T.ring_kept_pass({"late_frames": 19, "late_median_db": 9.0, "env_corr": 0.9})   # (i) not measured
    assert not T.ring_kept_pass({"late_frames": 50, "late_median_db": 0.0, "env_corr": 0.79})
    assert not T.ring_kept_pass({"late_frames": 50, "late_median_db": 0.0, "env_corr": float("nan")})


def test_chords_kept():
    assert T.chords_kept_pass({"f": 0.85, "chord_notes": 5, "chord_recall": 0.85})
    assert not T.chords_kept_pass({"f": 0.84, "chord_notes": 0, "chord_recall": None})
    assert not T.chords_kept_pass({"f": 0.9, "chord_notes": 5, "chord_recall": 0.8})
    assert T.chords_kept_pass({"f": 0.9, "chord_notes": 4, "chord_recall": 0.0})          # under 5 chord notes
    di = [_n(0.0, p) for p in (48, 52, 55)] + [_n(1.0, p) for p in (50, 53, 57)] + [_n(2.0, 60)]
    rt = [_n(0.01, p) for p in (48, 52)] + [_n(1.02, p) for p in (50, 53, 57)] + [_n(2.0, 60), _n(3.0, 70)]
    fig = T.chords_kept(rt, di)
    assert fig["chord_notes"] == 6 and fig["chord_recall"] == pytest.approx(5 / 6)
    assert fig["f"] == pytest.approx(2 * 6 / 14) and 0 < fig["pitch_class_cosine"] <= 1


def test_check_verdict_blocks_only_on_blocking_failures():
    figs = {"onsets-found": {"attacks": 10, "found": 10}, "playing-covered": {"playing_share": 1.0,
                                                                              "silent_share": 0.0},
            "judge-accepts": {"judge_finite": True, "pauses": {}, "longest_gap_s": 0.0},
            "ring-kept": {"late_frames": 0, "env_corr": 0.9}, "chords-kept": {"f": 0.9, "chord_notes": 0}}
    assert T.check_verdict(figs)["failed"] == []
    figs["ring-kept"]["env_corr"] = 0.5
    figs["onsets-found"] = {"attacks": 0, "found": 0}                                     # not measured: no block
    v = T.check_verdict(figs)
    assert v["failed"] == ["ring-kept"] and v["passes"]["onsets-found"] is None
    assert T.check_verdict(figs, T.NOTE_CHECKS)["failed"] == []


def test_annotated_found_on_the_top_tertile():
    rows = [{"alignment_f": f, "consistent": True, "recall": r} for f, r in
            [(0.5, 0.1), (0.6, 0.2), (0.7, 0.3), (0.80, 0.9), (0.81, 0.8), (0.82, 0.9), (0.9, 0.86), (0.91, 0.9),
             (0.92, 0.88)]]
    got = T.annotated_found_pass(rows)
    assert got["windows"] == 3 and got["median"] == 0.88 and got["passes"]
    rows[-1]["recall"] = 0.74                                                             # one window under 0.75
    assert not T.annotated_found_pass(rows)["passes"]
    rows[-1]["consistent"] = False                                     # its annotation fails the consistency test
    assert T.annotated_found_pass(rows)["windows"] == 2


def test_calibration_needs_annotated_found_and_playing_covered():
    af = {"passes": True}
    pos = {"avg+mild": [], "true": []}
    caught = {"item_102|nr-plain": "caught by a blocking check", "item_46|nr-plain": "caught by a report only"}
    assert T.calibration_ok(25, af, pos, caught)
    assert not T.calibration_ok(24, af, pos, caught)                     # playing-covered on 25 of the 27
    assert not T.calibration_ok(27, {"passes": False}, pos, caught)      # it gates the transcriber's settings
    assert not T.calibration_ok(27, {"passes": None, "windows": 0}, pos, caught)   # no window to read it on
    assert not T.calibration_ok(27, af, {"avg+mild": ["item_5"], "true": []}, caught)
    assert not T.calibration_ok(27, af, {"avg+mild": [], "true": ["item_5"]}, caught)
    blind = dict(caught, **{"item_160|nr-level": "caught by no check"})
    assert not T.calibration_ok(27, af, pos, blind)                      # caught by no check: the user's go first
    assert T.calibration_ok(27, af, pos, blind, clips_go=True)


def test_the_gate_passes_on_repeatability():
    assert T.gate_passes({"repeat_ok": True, "known_ok": False, "known_f": 0.751})   # 12m: F is a reported figure
    assert not T.gate_passes({"repeat_ok": False, "known_ok": True}) and not T.gate_passes(None)


def test_the_rejected_clips_cases():
    exp = [{"clip": "a|nr-plain", "must_fail_any": ["onsets-found", "playing-covered"]},
           {"clip": "b|nr-plain", "must_fail_any": ["ring-kept", "playing-covered"]},
           {"clip": "c|nr-plain", "must_fail_any": ["onsets-found", "playing-covered"]}]
    res = {"a|nr-plain": {"onsets-found": False, "playing-covered": False},
           "b|nr-plain": {"ring-kept": True, "playing-covered": True},
           "c|nr-plain": {"onsets-found": False, "playing-covered": True}}
    assert T.clip_case(exp, res) == {"a|nr-plain": "caught by a blocking check", "b|nr-plain": "caught by no check",
                                     "c|nr-plain": "caught by a report only"}


def test_the_two_triggers_and_the_versions_loudness():
    assert T.chords_go_refusal(0.86, {}) is None
    assert "to the user first" in T.chords_go_refusal(0.84, {})
    assert T.chords_go_refusal(0.84, {T.PHASE_GO_CHORDS: {"go": True}}) is None
    assert "no P2 chord recall" in T.chords_go_refusal(None, {})
    assert T.p2_chord_recall({"report": {"P2|chords": {"recall": 0.9}}}) == 0.9 and T.p2_chord_recall({}) is None
    assert T.flags_go_refusal(["a", "b"], {}) is None
    assert "3 of the 40" in T.flags_go_refusal(["a", "b", "c"], {})
    assert T.flags_go_refusal(["a", "b", "c"], {T.PHASE_GO_FLAGS: {}}) is None
    parts = {"a": {"figures": {"onsets-found": {"flag": True}}}, "b": {"figures": {"onsets-found": {"flag": False}}},
             "p": {"figures": {"onsets-found": {"flag": True}}}}
    assert T.flagged_parts(parts, {"a": "goat", "b": "bks", "p": "panel"}) == (["a"], ["p"])
    assert T.versions_loud({T.PHASE_VERSIONS: {"code": "NV-loud", "gamma": 2.0}}) == (2.0, None)
    assert "holds no code" in T.versions_loud({})[1]
    assert "to the user first" in T.versions_loud({T.PHASE_VERSIONS: {"code": "NV-short"}})[1]
    read = {"code": "NV-none", "sha256": "s"}
    ok = {"go": True, "versions_sha256": "s", "loud": None}
    assert T.versions_loud({T.PHASE_VERSIONS: read, T.PHASE_GO_VERSIONS: ok}) == (None, None)
    for g in (1.0, 2.0):
        assert T.versions_loud({T.PHASE_VERSIONS: read, T.PHASE_GO_VERSIONS: {**ok, "loud": g}}) == (g, None)
    for bad in ({"loud": None}, {**ok, "go": False}, {k: v for k, v in ok.items() if k != "go"},
                {**ok, "versions_sha256": "other"}, {k: v for k, v in ok.items() if k != "versions_sha256"},
                {**ok, "loud": 3.0}, {**ok, "loud": "1"}, {**ok, "loud": True}, {k: v for k, v in ok.items() if k != "loud"}, "yes"):
        loud, why = T.versions_loud({T.PHASE_VERSIONS: read, T.PHASE_GO_VERSIONS: bad})
        assert loud is None and T.PHASE_GO_VERSIONS in why, bad
    unhashed = {T.PHASE_VERSIONS: {"code": "NV-none"}, T.PHASE_GO_VERSIONS: {"go": True, "loud": None}}
    assert T.PHASE_GO_VERSIONS in T.versions_loud(unhashed)[1]          # no sha on either side binds nothing


def test_the_ladder_windows_and_usable_windows():
    ws = [{"player": pl, "kind": k, "name": nm, "start": st, "consistent": c, "key": f"{pl}{k}{nm}{st}"}
          for pl in ("P1", "P2") for k, nm, st, c in (("chords", "b", 10.0, True), ("chords", "a", 70.0, True),
                                                       ("chords", "a", 10.0, False), ("chords", "c", 10.0, True),
                                                       ("scales", "z", 70.0, True), ("scales", "y", 130.0, True))]
    lw = T.ladder_windows({"windows": ws})
    assert [(w["player"], w["kind"], w["name"], w["start"]) for w in lw] == [
        ("P1", "chords", "a", 70.0), ("P1", "chords", "b", 10.0), ("P1", "scales", "y", 130.0),
        ("P2", "chords", "a", 70.0), ("P2", "chords", "b", 10.0), ("P2", "scales", "y", 130.0)]
    assert len(T.usable_windows({"windows": ws})) == 10 and len(T.usable_windows({"windows": ws}, ("P1",))) == 5


def test_content_shares():
    notes = [_n(0.0, p) for p in (48, 52, 55)] + [_n(1.0, 60, bends=[3] * 10), _n(2.0, 62), _n(3.0, 64)]
    assert T.content_shares(notes) == {"bent_share": pytest.approx(1 / 6), "chord_share": pytest.approx(1 / 4)}
    assert T.content_shares([]) == {"bent_share": None, "chord_share": None}


def test_ring_choice():
    assert T.ring_choice([0.85, 0.86, 0.87], [0.84, 0.85, 0.86]) == "ring-soft"       # within 0.02
    assert T.ring_choice([0.90, 0.91, 0.92], [0.85, 0.86, 0.87]) == "ring-on"
    assert T.ring_choice([0.80], [0.90]) == "ring-soft"


def test_refusal_count_on_the_forty():
    parts = {f"b{i}": {"failed": ["ring-kept"] if i < 2 else []} for i in range(5)}
    parts.update({"p0": {"failed": ["chords-kept"]}, "g0": {"failed": ["onsets-found"]}})
    sets_of = {**{f"b{i}": "bks" for i in range(5)}, "p0": "panel", "g0": "goat"}
    dec, pan, stop = T.refusal_count(parts, sets_of)
    assert sorted(dec) == ["b0", "b1", "g0"] and list(pan) == ["p0"] and stop
    parts["g0"]["failed"] = []
    assert not T.refusal_count(parts, sets_of)[2]                                         # a panel refusal stops nothing


def test_expected_failures_are_a_blind_spot_when_missed():
    exp = [{"clip": "item_46|nr-plain", "must_fail_any": ["chords-kept"]}, {"clip": "item_57|nr-level"}]
    res = {"item_46|nr-plain": {"chords-kept": False, "onsets-found": True},
           "item_57|nr-level": {"onsets-found": True, "playing-covered": None}}
    assert T.expected_failure_refusal(exp, res) == [("item_57|nr-level", ["onsets-found", "playing-covered"])]
    res["item_57|nr-level"]["playing-covered"] = False
    assert T.expected_failure_refusal(exp, res) == []


# --- the overlap, the lock, the install -------------------------------------------------------------------------------------

def test_overlap_song_by_song():
    parts = [{"pkey": "a", "set": "panel", "unit": "panel/Artist One/RAW_05_02@5.0#ArtistOne_SongA_RAW_05_01.wav"},
             {"pkey": "b", "set": "panel", "unit": "panel/Artist Two/RAW_03_08@90.0#ArtistTwo_SongB_RAW_03_09.wav"},
             {"pkey": "c", "set": "panel", "unit": "panel/Band Three/ElecGtr01@55.0#28_ElecGtr01Mic2.wav"},
             {"pkey": "d", "set": "goat", "unit": "goat/item_0@140.0#amp_3"}]
    ids = T.medleydb_index_ids({"tracks": {"ArtistOne_SongA_STEM_15": {}, "Other_Song_STEM_01": {}}})
    assert T.transcriber_overlap_songs(parts, ids) == {"a": "ArtistOne_SongA", "b": None, "c": None}
    assert T.transcriber_overlap_songs(parts, ids + ["ArtistTwo_SongB_STEM_04"])["b"] == "ArtistTwo_SongB"
    assert [T.panel_group(p) for p in parts] == ["medleydb", "medleydb", "laminar_flow", None]
    assert T.medleydb_song("28_ElecGtr01Mic2.wav") is None


def _report(*rows):
    return {"install": [{"metadata": {"name": n, "version": v}, "download_info": {
        "url": f"https://files/{n}-{v}-py3-none-any.whl", "archive_info": {"hashes": {"sha256": s}}}}
        for n, v, s in rows]}


def test_lock_from_the_report():
    rep = _report(("onnxruntime", "1.19.2", T.ONNXRUNTIME[2]), ("pretty_midi", "0.2.11.post0",
                                                                 T.KNOWN_WHEELS["pretty-midi"][1]),
                  ("mir_eval", "0.8.2", T.KNOWN_WHEELS["mir-eval"][1]), ("numpy", "1.26.4", "ab" * 32))
    text = T.lock_lines(rep, [T.BASIC_PITCH[:3]])
    assert "basic-pitch==0.4.0 --hash=sha256:" + T.BASIC_PITCH[2] in text and "pretty-midi==0.2.11.post0" in text
    assert T.lock_refusal(text) is None
    assert "coremltools" in T.lock_refusal(text + "coremltools==7.0 --hash=sha256:" + "cd" * 32 + "\n")
    assert "unhashed" in T.lock_refusal(text + "six==1.16.0\n")
    assert "onnxruntime" in T.lock_refusal(text.replace(T.ONNXRUNTIME[2], "00" * 32))
    fallback = text.replace(T.ONNXRUNTIME[2], T.ONNXRUNTIME_CP311[2])       # the declared 3.11 fallback's wheel
    assert T.lock_refusal(fallback, T.ONNXRUNTIME_CP311) is None and "onnxruntime" in T.lock_refusal(fallback)
    assert T.ONNX_PIN["3.11"][2] == "d863e8acdc7232d705d49e41087e10b274c42f09e259016a46f32c34e06dc4fd"
    assert set(T.ONNX_PIN) == {"3.9", "3.11"} and T.ONNX_PIN["3.9"] == T.ONNXRUNTIME
    bad = _report(("x", "1", "ab" * 32))
    bad["install"][0]["download_info"]["url"] = "https://files/x-1.tar.gz"
    with pytest.raises(SystemExit):
        T.lock_lines(bad)
    with pytest.raises(SystemExit):
        T.lock_lines(_report(("numpy", "1", "ab" * 32), ("numpy", "2", "cd" * 32)))


def test_note_files_are_tied_to_one_install():
    rec = {"lock_sha256": "L", "model_sha256": "M", "settings": dict(T.BP_SETTINGS)}
    assert T.install_refusal(rec, ("L", "M")) is None
    assert "another install" in T.install_refusal(rec, ("L", "M2"))
    assert "other settings" in T.install_refusal(dict(rec, settings={**T.BP_SETTINGS, "onset_threshold": 0.6}),
                                                 ("L", "M"))
    assert T.ledger_pair_refusal({}, ("L", "M")) is None
    assert T.ledger_pair_refusal({T.PHASE_INSTALL: {"lock_sha256": "L", "model_sha256": "M"}}, ("L", "M")) is None
    assert "another lock" in T.ledger_pair_refusal({T.PHASE_INSTALL: {"lock_sha256": "X", "model_sha256": "M"}},
                                                   ("L", "M"))


def test_listing_sha_is_the_hand_backs_form():
    rows = [("nr-plain/b.json", "22" * 32), ("nr-level/a.json", "11" * 32)]
    assert T.listing_text(rows) == f"{'11' * 32}  ./nr-level/a.json\n{'22' * 32}  ./nr-plain/b.json\n"
    assert len(T.DIST_LIST_SHA) == 64 and T.DIST_LIST_SHA.startswith("2dccf3e6") and T.DIST_LIST_SHA.endswith("71de")


# --- the guards ---------------------------------------------------------------------------------------------------------------

def test_the_guard_covers_the_declared_files_and_keys():
    assert set(T.CODE_FILES) == {"learn/scratch_search.py", "learn/scratch_notes.py", "learn/note_rebuild.py",
                                 "learn/note_rebuild_s1.py", "learn/note_rebuild_ear.py", "learn/note_transcribe.py",
                                 "learn/bp_run.py", "learn/note_truth.py", "learn/note_attacks.py",
                                 "learn/attack_run.py", "learn/note_versions.py"}
    assert all((REPO / f).exists() for f in T.CODE_FILES)
    assert T.KEY_PREFIXES == {"preset-ladder": ("phase_fs", "phase_scratch_notes"), "note-rebuild": ("phase_nr",)}
    local = {"preset-ladder": {"phase_fs": 1, "phase_scratch_notes": 2, "phase_l0": 3},
             "note-rebuild": {"phase_nr_1_redo": 4}}
    assert T.keys_refusal(local, json.loads(json.dumps(local))) is None
    assert T.keys_refusal(local, {**local, "preset-ladder": {"phase_fs": 1, "phase_scratch_notes": 2}}) is None
    assert "phase_scratch_notes" in T.keys_refusal(local, {**local, "preset-ladder": {"phase_fs": 1, "phase_l0": 3}})
    assert "phase_nr_1_redo" in T.keys_refusal(local, {**local, "note-rebuild": {}})


def test_the_ledger_holds_the_declarations():
    e = T.entries((REPO / "docs" / "dev-test-ledger.json").read_text())
    assert T.PHASE in e["note-rebuild"] and "phase_scratch_notes" in e["preset-ladder"]
    assert "phase_nr_1_ear" not in e["note-rebuild"]          # the old page's read is never the stage-1 gate key
    assert T.PHASE_CALIB in e["note-rebuild"] and "Measure first" in str(e["note-rebuild"][T.PHASE_CALIB])
    truth = e["note-rebuild"][T.PHASE_TRUTH]                   # step 2's listing, ledgered before any run reads it
    assert truth["sha256"].startswith("3056dcbc") and truth["file"] == "PF/note-rebuild/redo/truth.json"
    for later in (T.PHASE_GO_CHORDS, T.PHASE_GO_CLIPS):
        assert later not in e["note-rebuild"]
    for later in (T.PHASE_INSTALL, T.PHASE_NOTES, T.PHASE_EAR):
        assert later not in e["note-rebuild"]                  # each comes with its own PR
    assert T.PHASE_DRY not in e["preset-ladder"]


def test_the_ladder_refusal_and_the_users_go():
    """12m step 3: a list failing the instrument check stops `versions` unless main holds the user's go naming that
    ghost-ladder.json's sha256; under the go the real set is reported only. The ladder rule itself is unchanged."""
    assert T.ladder_refusal({"go": True, "real_reported_only": False}, {}, "s") == (None, False)
    assert T.ladder_refusal({"go": True, "real_reported_only": True}, {}, "s") == (None, True)
    failed = {"go": False, "real_reported_only": None}
    why, real_only = T.ladder_refusal(failed, {}, "s")
    assert T.PHASE_GO_LADDER in why and real_only is None
    assert T.ladder_refusal(failed, {T.PHASE_GO_LADDER: {"ladder_sha256": "other"}}, "s")[0]   # another run's go
    assert T.ladder_refusal(failed, {T.PHASE_GO_LADDER: "yes"}, "s")[0]
    assert T.ladder_refusal(failed, {T.PHASE_GO_LADDER: {"ladder_sha256": "s"}}, "s")[0]        # no go field
    assert T.ladder_refusal(failed, {T.PHASE_GO_LADDER: {"go": False, "ladder_sha256": "s"}}, "s")[0]
    assert T.ladder_refusal(failed, {T.PHASE_GO_LADDER: {"go": True, "ladder_sha256": "s"}}, "s") == (None, True)


def test_the_users_two_goes_of_2026_11_23():
    """The user's answers after step 3 (AskUserQuestion, 2026-11-23): the ladder's go bound to the stored
    ghost-ladder.json, and the flagged-parts trigger reported, not stopping `build`."""
    e = T.entries((REPO / "docs" / "dev-test-ledger.json").read_text())["note-rebuild"]
    lad, fl = e[T.PHASE_GO_LADDER], e[T.PHASE_GO_FLAGS]
    assert lad["answer"] == "Continue, record why" and lad["go"] is True and lad["real_reported_only"] is True
    assert lad["ladder_sha256"].startswith("15894262") and lad["failing_lists"] == ["chords-four"]
    assert fl["answer"] == "Report it, don't stop" and fl["go"] is True
    failed = {"go": False, "real_reported_only": None}
    assert T.ladder_refusal(failed, e, lad["ladder_sha256"]) == (None, True)
    assert T.flags_go_refusal([f"p{i}" for i in range(40)], e) is None


def test_the_truth_report_refusal_and_the_users_go():
    """12m step 4: a truth report its hum guard stopped is refused unless main holds the user's go, its `go` true and
    naming that truth-report.json's sha256. The guard's rule itself is unchanged."""
    ok = {"stopped": None}
    assert T.truth_report_refusal(ok, {}, "s") is None
    stopped = {"stopped": [["P1|chords|x@10", 0.2]]}
    why = T.truth_report_refusal(stopped, {}, "s")
    assert T.PHASE_GO_HUM in why and "hum guard" in why
    assert T.truth_report_refusal(stopped, {T.PHASE_GO_HUM: {"go": True, "truth_report_sha256": "other"}}, "s")
    assert T.truth_report_refusal(stopped, {T.PHASE_GO_HUM: {"truth_report_sha256": "s"}}, "s")       # no go field
    assert T.truth_report_refusal(stopped, {T.PHASE_GO_HUM: {"go": False, "truth_report_sha256": "s"}}, "s")
    assert T.truth_report_refusal(stopped, {T.PHASE_GO_HUM: "yes"}, "s")
    assert T.truth_report_refusal(stopped, {T.PHASE_GO_HUM: {"go": True, "truth_report_sha256": "s"}}, "s") is None


def test_the_users_hum_go_of_2026_11_23():
    """The user's answer after step 4 (AskUserQuestion, 2026-11-23): the hum guard's stop goes on, bound to the
    stored truth-report.json; the rule unchanged."""
    e = T.entries((REPO / "docs" / "dev-test-ledger.json").read_text())["note-rebuild"]
    hum = e[T.PHASE_GO_HUM]
    assert hum["answer"] == "Continue, record why" and hum["go"] is True
    assert hum["truth_report_sha256"].startswith("425f3fd1") and len(hum["stopping_windows"]) == 18
    assert T.truth_report_refusal({"stopped": [["k", 0.2]]}, e, hum["truth_report_sha256"]) is None


def test_the_note_versions_read_on_main():
    """12m step 5: the read's sha256 and code, ledgered; NV-none is not NV-loud, so `build` refuses without the user's
    decision (`versions_loud`), and with their recorded "Run as is" it runs with no loudness."""
    e = T.entries((REPO / "docs" / "dev-test-ledger.json").read_text())["note-rebuild"]
    rec = e[T.PHASE_VERSIONS]
    assert rec["sha256"].startswith("8f77f5d7") and rec["file"] == "PF/note-rebuild/redo/versions.json"
    assert rec["code"] == "NV-none" and rec["gamma"] is None and rec["real_reported_only"] is True
    assert "not the J0 judge" in rec["distance"]
    without_go = {k: v for k, v in e.items() if k != T.PHASE_GO_VERSIONS}
    loud, why = T.versions_loud(without_go)
    assert loud is None and T.PHASE_GO_VERSIONS in why
    go = e[T.PHASE_GO_VERSIONS]                                # the user's "Run as is", 2026-11-23
    assert go["answer"] == "Run as is (Recommended)" and go["go"] is True and go["versions_sha256"] == rec["sha256"]
    assert T.versions_loud(e) == (None, None)                 # build runs with no loudness


def test_the_old_pages_expected_failure_table():
    """`phase_nr_1_ear_old` (step 2): the stored read, the user's words, and which check must fail which rejected
    clip, ledgered before any check runs on them; the table is the shape `calibrate` reads."""
    e = T.entries((REPO / "docs" / "dev-test-ledger.json").read_text())["note-rebuild"]
    rec = e[T.PHASE_EAR_OLD]
    assert rec["verdict"] == "incomplete" and rec["answers"]["sha256"].startswith("e27df9f2")
    table = T.ear_old_table(e)
    assert [x["clip"] for x in table] == [f"{it}|{arm}" for it in ("item_102", "item_160", "item_46")
                                          for arm in ("nr-plain", "nr-level")]
    for x in table:
        assert x["must_fail_any"] and set(x["must_fail_any"]) <= set(T.CONTENT) - {"annotated-found"}
    want = {"item_102": ["onsets-found", "playing-covered"], "item_160": ["ring-kept", "playing-covered"],
            "item_46": ["onsets-found", "playing-covered"]}      # item_46's chords: reported, not counted (R1)
    assert all(x["must_fail_any"] == want[x["clip"].split("|")[0]] for x in table)
    assert "chords-kept" in rec["chords_not_testable"] and "all 6" in rec["control_stop_rule"]
    only_chords = {x["clip"]: {k: True for k in T.CONTENT} for x in table}
    only_chords["item_46|nr-plain"]["chords-kept"] = False      # a chords-kept failure alone does not catch item_46
    assert ("item_46|nr-plain", want["item_46"]) in T.expected_failure_refusal(table, only_chords)
    assert T.expected_failure_refusal(table, {x["clip"]: {k: False for k in x["must_fail_any"]} for x in table}) == []
    blind = T.expected_failure_refusal(table, {x["clip"]: {k: True for k in T.CONTENT} for x in table})
    assert len(blind) == 6                                    # an expected failure that does not happen: a blind spot
    assert len(rec["users_words"]) == 5 and any("chords" in w for w in rec["users_words"].values())


@pytest.mark.parametrize("cmd", sorted(T.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(T, "redo_on_main", lambda: ({}, "this checkout's learn/note_transcribe.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        T.COMMANDS[cmd](None)


@pytest.mark.parametrize("cmd", sorted(T.COMMANDS))
def test_every_command_refuses_without_the_declaration_on_main(monkeypatch, cmd):
    monkeypatch.setattr(T, "redo_on_main", lambda: ({"note-rebuild": {}, "preset-ladder": {}}, None))
    with pytest.raises(SystemExit, match="phase_nr_1_redo"):
        T.COMMANDS[cmd](None)


def test_the_gate_never_overwrites_a_runs_raw_events(monkeypatch, tmp_path):
    monkeypatch.setattr(T, "redo_on_main", lambda: ({"note-rebuild": {T.PHASE: "declared"}}, None))
    monkeypatch.setattr(T, "REDO", tmp_path)
    assert T.gate_work_dir() == tmp_path / "work" / "install-gate"
    T.gate_work_dir().mkdir(parents=True)                     # the failed run's folder still in place
    with pytest.raises(SystemExit, match="install-gate exists: never overwritten"):
        T.cmd_install_gate(None)
    (tmp_path / "install-gate.json").write_text("{}")
    with pytest.raises(SystemExit, match="install-gate.json exists"):
        T.cmd_install_gate(None)


NEW_COMMANDS = ("truth", "attacks-report", "ghost-ladder", "truth-report", "versions")


@pytest.mark.parametrize("cmd", NEW_COMMANDS + ("calibrate", "transcribe", "build"))
def test_the_amendments_commands_need_its_declaration_on_main(monkeypatch, cmd):
    monkeypatch.setattr(T, "redo_on_main", lambda: ({"note-rebuild": {T.PHASE: "d", T.PHASE_EAR_OLD: {}}}, None))
    with pytest.raises(SystemExit, match=T.PHASE_CALIB):
        T.COMMANDS[cmd](None)


@pytest.mark.parametrize("cmd", [c for c in NEW_COMMANDS if c != "truth"] + ["calibrate", "transcribe", "build"])
def test_the_amendments_commands_need_the_truth_listing_on_main(monkeypatch, cmd):
    monkeypatch.setattr(T, "redo_on_main", lambda: ({"note-rebuild": {T.PHASE: "d", T.PHASE_EAR_OLD: {},
                                                                      T.PHASE_CALIB: "d"}}, None))
    with pytest.raises(SystemExit, match=T.PHASE_TRUTH):
        T.COMMANDS[cmd](None)


@pytest.mark.parametrize("cmd, path", [("truth", "truth.json"), ("attacks-report", "attacks.json"),
                                       ("ghost-ladder", "ghost-ladder.json"), ("truth-report", "truth-report.json"),
                                       ("versions", "versions.json")])
def test_each_new_output_is_written_once(monkeypatch, tmp_path, cmd, path):
    monkeypatch.setattr(T, "redo_on_main", lambda: ({"note-rebuild": {T.PHASE: "d", T.PHASE_CALIB: "d",
                                                                      T.PHASE_TRUTH: {"sha256": "x"}}}, None))
    monkeypatch.setattr(T, "REDO", tmp_path)
    (tmp_path / path).write_text("{}")
    with pytest.raises(SystemExit, match="never overwritten"):      # versions refuses a second run
        T.COMMANDS[cmd](None)


def test_calibrate_needs_the_old_ear_table(monkeypatch, tmp_path):
    monkeypatch.setattr(T, "redo_on_main", lambda: ({"note-rebuild": {T.PHASE: "declared"}}, None))
    with pytest.raises(SystemExit, match=T.PHASE_EAR_OLD):
        T.cmd_calibrate(None)
    with pytest.raises(SystemExit, match="expected_failures"):
        T.ear_old_table({T.PHASE_EAR_OLD: {"verdict": "ok"}})
    assert T.ear_old_table({T.PHASE_EAR_OLD: {"expected_failures": []}}) == []


def test_never_overwrite(tmp_path):
    p = tmp_path / "x.json"
    T.never_overwrite(p)
    p.write_text("{}")
    with pytest.raises(SystemExit, match="never overwritten"):
        T.never_overwrite(p)


def test_paths_stay_in_the_redos_folders():
    assert T.note_path("part", "bks__a|pr12").parent.name == "part"
    assert "/" not in T.note_path("part", "a/b").name
    assert T.dry_path("tr-di", "part|x").parts[-3:-1] == ("dry", "tr-di")
    assert T.REDO.name == "redo" and T.REDO.parent.name == "note-rebuild"
    assert T.clips_dir().name == "note-rebuild-ear-2"
    assert T.SET_ASIDE.name == "stage1.set-aside-20261122" and T.SET_ASIDE_NOTE == "unread: no pick, no score"


def test_probe_start_and_full_window():
    assert T.probe_start(46) == 30.0 and T.probe_start(45) == 1.0
    assert T.full_window(11.25, 1.0) and not T.full_window(11.24, 1.0)


def test_known_lists_fit_the_window_and_hold_chords_and_a_bend():
    assert len(T.KNOWN_NOTES) == 10
    for name, notes in T.KNOWN_NOTES.items():
        assert notes and all(0 <= n["on"] < n["off"] <= 10.25 for n in notes), name
        assert all(40 <= n["pitch"] <= 88 for n in notes), name
    sizes = {len(g) for nm in ("chords-six", "chords-five", "chords-four", "power-chords")
             for g in T.groups_of(T.KNOWN_NOTES[nm])}
    assert {3, 4, 5, 6} <= sizes
    assert any(any(n["bends"]) for n in T.KNOWN_NOTES["bend"])


# --- with the stored data -----------------------------------------------------------------------------------------------------

def test_the_development_windows_are_the_declared_27():
    pytest.importorskip("soundfile")
    from learn import note_rebuild as NR

    if not (NR.GOAT_ZIP.exists() and (NR.OUT / "exclusion.json").exists()):
        pytest.skip("no stored GOAT data")
    import zipfile

    excl, tn = NR.load_exclusion(), NR.load_doc("true-notes.json")
    with zipfile.ZipFile(NR.GOAT_ZIP) as z:
        wins = T.dev_windows(z, excl, tn["items"])
    assert len(wins) == 27 and len({w["item"] for w in wins}) == 27
    assert {"item_102", "item_150"} <= {w["item"] for w in wins}         # the stage-1 declaration's named windows
