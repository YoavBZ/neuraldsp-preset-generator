"""The note rebuild's fixes (note-rebuild-plan 12q; `learn/note_fixes.py`): the pure transforms, with no numpy needed
except where marked."""
import math

import pytest

from learn import note_fixes as F
from learn import note_transcribe as T


def note(on, off, pitch, bends=()):
    return {"on": on, "off": off, "pitch": pitch, "amp": 0.5, "bends": list(bends)}


def test_f1_rezeroes_the_bend_baseline():
    notes = [note(0.0, 0.5, 60, [1] * 20), note(1.0, 1.5, 62, [1] * 10 + [4] * 10), note(2.0, 2.5, 64)]
    g = F.rezero_bends(notes, "global")
    assert g[0]["bends"] == [0.0] * 20 and g[1]["bends"][-1] == 3.0 and g[2]["bends"] == []
    m = F.rezero_bends(notes, "median")
    assert m[0]["bends"] == [0.0] * 20 and m[1]["bends"][-1] == 1.5        # the note's own median (2.5) off
    assert F.rezero_bends(notes, None) == notes and F.rezero_bends(notes, None) is not notes   # off: as is
    assert notes[0]["bends"] == [1] * 20                                  # pure: the input untouched
    with pytest.raises(ValueError):
        F.rezero_bends(notes, "other")


def test_f1_removes_the_baselines_bend_from_in_tune_notes():
    flat = [note(0.0, 0.5, 60, [1] * 30), note(1.0, 1.5, 67, [1] * 30)]
    assert F.bent_share(flat) == 1.0                                       # as built: every in-tune note bent
    assert F.bent_share(F.rezero_bends(flat, "global")) == 0.0
    assert F.bent_share([]) is None


def test_f2_pairs_and_joins_same_pitch_refinds():
    notes = [note(0.0, 0.40, 60), note(0.45, 1.0, 60), note(0.50, 0.9, 64), note(2.0, 2.5, 60)]
    pairs = F.refind_pairs(notes)
    assert pairs == [(0, 1)]                                               # 2.0 starts long after: a new pick
    joined = F.join_refinds(notes, pairs, {1})
    assert len(joined) == 3 and joined[0]["off"] == 1.0                    # the sounding note extended
    assert F.join_refinds(notes, pairs, set()) == notes                    # no join: as is
    chain = [note(0.0, 0.3, 60), note(0.31, 0.6, 60), note(0.61, 1.2, 60)]
    p2 = F.refind_pairs(chain)
    assert p2 == [(0, 1), (1, 2)]
    assert [n["off"] for n in F.join_refinds(chain, p2, {1, 2})] == [1.2]  # a chain joins into the first
    assert F.f2_joins(p2, {1: 0.5, 2: 4.0}, 2.0) == {1}
    assert F.f2_joins(p2, {1: 0.5, 2: 4.0}, -math.inf) == set() and F.f2_joins(p2, {1: 0.5, 2: 4.0}, math.inf) == {1, 2}


def test_f3_joins_a_glide_into_one_sample_along_the_bend():
    up = [note(0.0, 0.50, 60, [0] * 30 + [1, 2, 3, 3, 3]), note(0.52, 1.0, 62, [0] * 10)]
    pairs = F.handoff_pairs(up)
    assert pairs == [(0, 1)]
    g = F.join_glides(up, pairs)
    assert len(g) == 1 and g[0]["off"] == 1.0 and g[0]["pitch"] == 60
    k = round(0.52 / F.NR.BEND_FRAME_S)
    assert g[0]["bends"][k] == 6.0                                         # two semitones up from the handover
    away = [note(0.0, 0.5, 60, [0] * 30 + [-1] * 5), note(0.52, 1.0, 62)]
    assert F.handoff_pairs(away) == []                                     # bending the other way: no glide
    far = [note(0.0, 0.5, 60, [0] * 30 + [3] * 5), note(0.52, 1.0, 66)]
    assert F.handoff_pairs(far) == []                                      # beyond the bend cap
    late = [note(0.0, 0.5, 60, [0] * 30 + [3] * 5), note(0.70, 1.0, 62)]
    assert F.handoff_pairs(late) == []


def test_every_fix_off_is_the_identity():
    notes = [note(0.0, 0.40, 60, [1] * 10), note(0.45, 1.0, 60, [1] * 10)]
    got, rep = F.apply_fixes(notes, {})
    assert got == notes and rep == {}


def test_the_interval_and_the_wrap():
    pytest.importorskip("scipy")
    iv = F.interval90([1.0, 2.0, 3.0])
    assert iv["mean"] == 2.0 and iv["lo90"] < 2.0 < iv["hi90"] and iv["n"] == 3
    assert F.interval90([]) is None and F.interval90([1.0])["lo90"] is None
    assert F.wrap_cents(58.0) == -42.0 and F.wrap_cents(-30.0) == -30.0


def test_a_later_pages_ear_items_replace_only_the_ruled_out_di():
    ear = [{"item": "o1", "old": True, "kind": None}, {"item": "a", "old": False, "kind": "chord-led"},
           {"item": "item_5", "old": False, "kind": "let-ring"}]
    order = ["item_5", "a", "b", "c"]
    figs = {"b": {"let-ring": 0.13}, "c": {"let-ring": 0.02}, "item_5": {"let-ring": 0.16}}
    items, repl = T.replace_ruled_out_kinds(order, ear, figs, {})
    assert [e["item"] for e in items] == ["o1", "a", "b"]                 # the others kept; the nearest after item_5
    assert repl["let-ring"]["from"] == "item_5" and repl["let-ring"]["filled"] is False
    items2, repl2 = T.replace_ruled_out_kinds(order, ear, figs, {"c": {"let-ring"}})
    assert items2[-1]["item"] == "c" and repl2["let-ring"]["filled"] is True   # the declared pass first


def test_a_later_build_has_its_own_record_and_dry_root():
    assert T.build_path() == T.REDO / "build.json" and T.build_path("b2") == T.REDO / "build-b2.json"
    assert T.dry_root() == T.REDO / "dry" and T.dry_root("b2") == T.REDO / "dry-b2"
    assert T.ear_items_file("never-made") == T.ear_items_path()


def test_the_replacement_ear_item_is_drawn_outside_d():
    ear = [{"item": "o1", "old": True, "kind": None}, {"item": "item_5", "old": False, "kind": "let-ring"}]
    order = ["item_5", "d1", "b"]
    figs = {"d1": {"let-ring": 0.13}, "b": {"let-ring": 0.02}}
    items, _ = T.replace_ruled_out_kinds(order, ear, figs, {}, exclude={"d1"})
    assert items[-1]["item"] == "b"                                       # D's window never drawn


def test_build_1_is_read_only_after_a_later_build_is_hashed():
    from learn import scratch_notes as SN

    assert "12q R8" in SN.build1_read_refusal({SN.PHASE_DRY: {}})
    assert SN.build1_read_refusal({SN.PHASE_DRY: {}, SN.PHASE_DRY + "_b2": {}}) is None
    assert SN.build1_read_refusal({}, "b2") is None                        # a later build reads freely


def test_the_muscriptor_fixes_are_declared_before_their_numbers():
    import pathlib

    e = T.entries((pathlib.Path(__file__).resolve().parents[1] / "docs" / "dev-test-ledger.json").read_text())
    rec = e["note-rebuild"]["phase_nr_1_redo_fixes_ms"]
    assert {"F2_muscriptor", "F4", "F5", "order"} <= set(rec) and "50, 100, 150 ms" in rec["F2_muscriptor"]
    assert "not tuned bars" in rec["F5"] and "preliminary" not in rec                 # declared: no figures yet


def test_the_muscriptor_fixes_transforms():
    bp = [note(0.0, 0.4, 60), note(0.45, 1.0, 60), note(0.0, 0.4, 72), note(2.0, 2.5, 64)]
    ms = [{"on": 0.01, "off": 0.9, "pitch": 60}, {"on": 2.3, "off": 2.6, "pitch": 64}]
    pairs = F.refind_pairs(bp)
    assert F.f2_ms_joins(bp, pairs, ms, 0.050) == {1}            # MuScriptor hears no new attack at 0.45: join
    assert F.f2_ms_joins(bp, pairs, ms + [{"on": 0.47, "off": 0.9, "pitch": 60}], 0.050) == set()
    assert F.f4_keep(bp, ms) == {0, 1, 3}                          # 72 is a ghost an octave above a confirmed 60
    assert F.f5_keep(bp, ms) == {0}                                # sparse: only confirmed notes (the vote)
    dense = ms + [{"on": 2.05, "off": 2.4, "pitch": 67}, {"on": 2.1, "off": 2.4, "pitch": 71}]
    assert 3 in F.f5_keep(bp, dense)                               # dense context: the veto decides, 64 kept
    truth = [note(0.0, 0.5, 60), note(0.0, 0.5, 64), note(0.0, 0.5, 67), note(2.0, 2.5, 64)]
    got = F.removal_counts(truth + [note(1.0, 1.2, 50)], [truth[0], truth[3]], truth)
    assert got == {"lost": 2, "removed": 1, "chord_lost_proxy": 2}
    dup = [note(0.0, 0.5, 60), note(0.01, 0.5, 60)]                   # two notes on one truth note: one lost at most
    assert F.removal_counts(dup, [], [note(0.0, 0.5, 60)]) == {"lost": 1, "removed": 1, "chord_lost_proxy": 0}
    assert F.chord_recall([truth[0]], truth) == 1 / 3 and F.chord_recall([], [note(0, 1, 60)]) is None


def test_f4_at_50_ms_is_track_1s_veto():
    from learn import note_tx as X

    bp = [note(0.0, 0.4, 60), note(0.0, 0.4, 72), note(0.0, 0.4, 79), note(0.5, 0.9, 64), note(0.5, 0.9, 76),
          note(1.0, 1.3, 67)]
    ms = [{"on": 0.02, "off": 0.4, "pitch": 60}, {"on": 0.55, "off": 0.9, "pitch": 64}, {"on": 1.2, "off": 1.4,
                                                                                         "pitch": 67}]
    assert F.kept_notes(bp, F.f4_keep(bp, ms, below_s=0.050)) == X.veto_notes(bp, ms)


def test_the_ear_items_figure_merge():
    """#589's nit: the annotated kinds' figures come from the annotation, the rest from the scans; only scanned items."""
    tr = {"a": {"single-note": None, "let-ring": 0.08, "bends": 12}, "b": {"single-note": 0.5, "let-ring": 0.01}}
    ann = {"a": {"single-note": 0.92, "let-ring": 0.0}, "c": {"single-note": 1.0}}
    got = T.merge_kind_figures(tr, ann)
    assert got == {"a": {"single-note": 0.92, "let-ring": 0.08, "bends": 12}, "b": {"let-ring": 0.01}}
    assert "c" not in got                                                  # no scan window: no figure


def test_the_kept_fixes_in_order():
    bp = [note(0.0, 0.4, 60, [1] * 10), note(0.45, 1.0, 60, [1] * 10), note(0.0, 0.4, 72)]
    ms = [{"on": 0.01, "off": 0.9, "pitch": 60}]
    assert F.kept_transform(bp, ms, {}) == bp
    n = F.kept_transform(bp, ms, {"F1": "global"})
    assert n[0]["bends"] == [0.0] * 10 and len(n) == 3
    j = F.kept_transform(bp, ms, {"F1": "global", "F2ms": 0.05})
    assert len(j) == 2 and j[0]["off"] == 1.0                         # the re-find joined
    v = F.kept_transform(bp, ms, {"F1": "global", "F4": 0.05})
    assert [x["pitch"] for x in v] == [60, 60]                          # the octave ghost dropped
    for bad in ({"F2": 0.0}, {"F3": True}, {"F1": "global", "F6": 1}):    # unknown keys refused, never dropped
        with pytest.raises(ValueError, match="unknown kept fixes"):
            F.kept_transform(bp, ms, bad)


def test_a_later_build_names_its_own_loudness():
    assert T.build_loudness(None, {}) == (None, None)                       # the versions read's, as the first build
    assert T.build_loudness(2.0, {"F1": "global"}) == (2.0, None)
    assert T.build_loudness(None, {"F1": "global", "loud": 1.0}) == (1.0, None)   # build 2: gamma 1.0
    assert T.build_loudness(1.0, {"loud": None}) == (None, None)
    for bad in (0, -1.0, "1", True):
        assert T.build_loudness(None, {"loud": bad})[1]


def test_a_later_pages_new_ear_item_gets_its_note_checks_in_the_build(monkeypatch):
    tr = {"parts": {}, "ear": {"item_39": {"figures": {"onsets-found": {"share": 1.0}, "playing-covered": {"p": 1}}}}}
    assert T.note_check_figures(tr, "ear", "item_39", [], None) == tr["ear"]["item_39"]["figures"]
    monkeypatch.setattr(T, "playing_covered", lambda notes, di: {"measured": "here"})
    assert T.note_check_figures(tr, "ear", "item_123", [], None) == {"onsets-found": None,
                                                                    "playing-covered": {"measured": "here"}}


def test_a_named_builds_work_folder_is_its_own():
    assert T.build_work_dir() == T.REDO / "work" / "build"
    assert T.build_work_dir("b2") == T.REDO / "work" / "build-b2" != T.build_work_dir()


def test_build_2s_hash_on_main():
    import pathlib

    e = T.entries((pathlib.Path(__file__).resolve().parents[1] / "docs" / "dev-test-ledger.json").read_text())
    rec = e["preset-ladder"]["phase_scratch_notes_dry_b2"]
    assert rec["sha256"].startswith("b6640c44") and rec["rule"] == {"F1": "global", "ring": "ring-soft", "loud": None,
                                                                    "muscriptor": False}


def test_build_2s_ear_verdict_on_main_labels_its_reads():
    import pathlib

    from learn import scratch_notes as SN

    e = T.entries((pathlib.Path(__file__).resolve().parents[1] / "docs" / "dev-test-ledger.json").read_text())
    b2 = e["preset-ladder"]["phase_scratch_notes_dry_b2"]["sha256"]
    rec = e["note-rebuild"][T.ear_key(b2)]
    assert T.ear_key(b2) == "phase_nr_1_redo_ear_b6640c44fc78" and rec["dry_build_sha256"] == b2
    assert rec["verdict"] == "fault-content" and rec["build"] == "f62efa8e1d3f" and not rec["unanswered"]
    assert SN.ear_label(e["note-rebuild"], b2) == "ear fault-content"          # 12q R5: a label, never a gate
    assert SN.ear_refusal(e["note-rebuild"], b2) is not None                    # so the FN code stays provisional


# --- F6, bend chains (note-rebuild-plan 12t) -----------------------------------------------------------------------------

# L's `bend` list as Basic Pitch heard it (the install gate's stored events; a made-up list): three 2-semitone bends
# split into semitone notes, and the artefact step-backs after the true tracks' end (64, 67, 69)
BEND_EVENTS = (
    (0.4992, 0.8243, 64, "1111111111111111111111122233"), (0.8243, 0.9288, 65, "011112233"),
    (0.9288, 1.6602, 66, "0111111111111111111111111111111111111111111111111111111111111-5-5"),
    (1.6254, 2.033, 64, "111111111111111111111111111111111100"), (2.4742, 2.7645, 67, "0011111111111111111111111"),
    (2.7761, 2.927, 68, "-1-100011122223"),
    (2.927, 3.6584, 69, "01111111111111111111111111111111111111111111111111111111111111-5"),
    (3.6352, 4.0312, 67, "11111111111111111111111111111111111"), (4.484, 4.7859, 69, "01111111111111111111111112"),
    (4.7859, 4.9368, 70, "-1000111122233"),
    (4.9368, 5.645, 71, "0111111111111111111111111111111111111111111111111111111111111"),
    (5.6334, 6.0178, 69, "1111111111111111111111111111111111"))
F6P = {"K": 3, "gap": 1, "family": "sequential", "track": "own", "keep": True}


def bend_events():
    import re

    return [note(on, off, p, [int(v) for v in re.findall(r"-?\d", b)]) for on, off, p, b in BEND_EVENTS]


def test_fixes_refuse_unknown_keys_and_f6_without_the_global_baseline():
    notes = [note(0.0, 0.40, 60, [1] * 10)]
    got, _ = F.apply_fixes(notes, {"F1": "global", "loud": None})          # build 2's fixes pass ("loud" whitelisted)
    assert got[0]["bends"] == [0.0] * 10
    for bad in ({"ring": "ring-soft"}, {"F6x": 1}):
        with pytest.raises(ValueError, match="unknown fixes"):
            F.apply_fixes(notes, bad)
    for f1 in (None, "median"):
        with pytest.raises(ValueError, match="F6 needs F1 global"):
            F.apply_fixes(notes, {"F1": f1, "F6": F6P})
    for off_grid in ({**F6P, "K": 2}, {**F6P, "K": True}, {**F6P, "gap": 3}, {**F6P, "family": "overlapping"},
                     {**F6P, "track": "ridge"}, {**F6P, "keep": 1}, {k: v for k, v in F6P.items() if k != "keep"}):
        with pytest.raises(ValueError):
            F.apply_fixes(notes, {"F1": "global", "F6": off_grid})
    assert F.apply_fixes(notes, {"F1": "global", "F6": None})[0] == got     # F6 None: off


def test_f6_gaps_on_the_bend_lists_events():
    n1 = F.rezero_bends(bend_events(), "global")
    up = [(64, 65), (65, 66), (67, 68), (68, 69), (69, 70), (70, 71)]
    down = [(66, 64), (69, 67), (71, 69)]
    for k, want_up, want_down in ((1, [0, 0, 1, 0, 0, 0], [0, 0, 6]), (3, [1, 1, 1, 2, 2, 1], [0, 6, 6]),
                                  (5, [2] * 6, [6, 6, 6])):
        got = {(n1[i]["pitch"], n1[j]["pitch"]): g for i, j, g, kind in F.f6_pairs(n1, k, "both")}
        assert [got[p] for p in up] == want_up and [got[p] for p in down] == want_down
    raw = {(i, j): g for i, j, g, _ in F.f6_pairs(bend_events(), 3, "sequential")}
    assert raw == {(i, j): g for i, j, g, _ in F.f6_pairs(n1, 3, "sequential")}   # the global step moves no gap


def test_f6_joins_the_whole_chain_where_f3_leaves_two():
    notes = [note(0.50, 0.82, 64, [1] * 22 + [2, 2, 3, 3, 4, 4]), note(0.82, 0.93, 65, [1, 1, 2, 2, 3, 3, 4, 4, 4]),
             note(0.93, 1.60, 66, [1] * 58)]
    n1 = F.rezero_bends(notes, "global")
    assert len(F.join_glides(n1, F.handoff_pairs(n1))) == 2   # F3 skips the second hop: its first note joined away
    got, rep = F.apply_fixes(notes, {"F1": "global", "F6": F6P})
    assert len(got) == 1 and rep["F6"]["chains"] == [[0, 1, 2]] and rep["F6"]["joins"] == 2
    s, fr = got[0], F.NR.BEND_FRAME_S
    assert s["pitch"] == 64 and s["off"] == 1.60 and s["keep_bend"] is True
    assert s["bends"][int(round(0.45 / fr))] == 6.0                          # on 66: two semitones up
    assert len(s["bends"]) == math.ceil((1.60 + F.F6_PAD_S - 0.50) / fr)    # padded through the release ...
    assert s["bends"][-1] == 6.0                                             # ... holding its last value
    unkept, _ = F.apply_fixes(notes, {"F1": "global", "F6": {**F6P, "keep": False}})
    assert "keep_bend" not in unkept[0] and unkept[0]["bends"] == s["bends"]


def test_f6_pair_families_are_disjoint_and_follow_j1():
    i = note(0.0, 1.0, 60, [0] * 86)
    notes = [i, note(0.95, 1.5, 62, [0] * 40),           # on_j - off_i = -50 ms: sequential
             note(1.07, 1.5, 62, [0] * 30),               # +70 ms: neither
             note(0.50, 1.5, 61, [0] * 80),               # 500 ms before off_i: overlapping
             note(0.02, 1.5, 61, [0] * 80),               # within 30 ms of on_i: neither
             note(0.95, 1.5, 64, [0] * 40)]               # 4 semitones: neither
    assert {(j, kind) for a, j, _, kind in F.f6_pairs(notes, 3, "both") if a == 0} == {(1, "sequential"),
                                                                                       (3, "overlapping")}
    assert {j for a, j, _, _ in F.f6_pairs(notes, 3, "sequential") if a == 0} == {1}
    short = [note(0.0, 1.0, 60, [0] * 30), note(0.50, 1.5, 61, [0] * 80)]   # no shared frame on i's track: no pair
    assert F.f6_pairs(short, 1, "both") == []


def test_f6_chains_take_the_smallest_gap_and_a_tie_the_later_onset():
    notes = [note(0.0, 0.5, 60, [0] * 43), note(0.5, 1.0, 61, [0] * 43), note(0.52, 1.0, 62, [0] * 43)]
    assert F.f6_chains(notes, [(0, 1, 1.0, "s"), (0, 2, 1.0, "s"), (1, 2, 0.0, "o")], 1) == [[0, 1, 2]]
    assert F.f6_chains(notes, [(0, 1, 1.0, "s"), (0, 2, 1.0, "s")], 1) == [[0, 2]]   # a tie: the later onset
    assert F.f6_chains(notes, [(0, 1, 0.0, "s"), (0, 2, 1.0, "s")], 1) == [[0, 1]]   # the smaller gap first
    assert F.f6_chains(notes, [(0, 1, 2.0, "s")], 1) == []                            # over the gap: no chain


def test_the_stitched_track_switches_at_js_first_frame_and_the_line_is_linear():
    fr = F.NR.BEND_FRAME_S
    i = note(0.0, 1.0, 60, [0.0] * 86)
    j = note(0.40, 0.70, 61, [-2.0] * 26)                 # an overlapping semitone up, its track 2 bins under it
    trk = F.stitched_track([i, j], [0, 1], "own")
    q = math.ceil(0.40 / fr)
    assert trk[q - 1] == 0.0 and trk[q] == 1.0           # from j's first frame: 3 x (61 - 60) - 2
    assert trk[int(0.80 / fr)] == 0.0                    # j ended, i sounds again
    line = F.stitched_track([i, j], [0, 1], "line")
    assert line[0] == 0.0 and line[int(0.20 / fr)] == pytest.approx(1.5, abs=0.1) and line[-1] == 3.0
    assert len(trk) == len(line) == math.ceil((1.0 + F.F6_PAD_S) / fr)
    with pytest.raises(ValueError):
        F.stitched_track([i, j], [0, 1], "ridge")
    assert F.stitched_heads(5, [[1, 3], [2, 4]]) == {1, 2}


def test_pad_every_bent_note_holds_only_notes_that_end_bent():
    bent = note(0.0, 0.5, 60, [0] * 20 + [3] * 23)
    flat = note(1.0, 1.5, 64, [0] * 43)
    got = F.pad_bent([bent, flat])
    assert len(got[0]["bends"]) == math.ceil((0.5 + F.F6_PAD_S) / F.NR.BEND_FRAME_S) and got[0]["bends"][-1] == 3
    assert got[1] == flat and F.ends_bent([bent, flat]) == 1


def test_the_bend_lists_play_their_true_tracks_unchanged():
    assert set(F.BEND_LISTS) == set(F.BEND_POSITIVES) | set(F.BEND_CONTROLS) and len(F.BEND_LISTS) == 10
    for nm, truth in F.BEND_LISTS.items():
        bent = F.bent_truth(truth)
        assert (len(bent) == 4) == (nm in F.BEND_POSITIVES) and (not bent) == (nm in F.BEND_CONTROLS)
        assert max(n["off"] for n in truth) + F.NR.RING_SOFT_S < 10.25
        for i in bent:
            n = truth[i]
            assert n["keep_bend"] and len(n["bends"]) == math.ceil((n["off"] - n["on"] + 0.150) / F.NR.BEND_FRAME_S)
            assert F.NR.bend_curve(n, truth) == [float(v) for v in n["bends"]]    # played as declared
    assert max(F.BEND_LISTS["bend-release"][0]["bends"]) == 6 and F.BEND_LISTS["bend-release"][0]["bends"][-1] == 0
    assert max(F.BEND_LISTS["bend-under-semitone-held"][0]["bends"]) == 2


def test_the_bend_measures_and_their_ladder():
    truth = T.KNOWN_NOTES["bend"]
    rungs = F.ladder_rungs(truth)
    t, fl, st = (F.bend_error(truth, rungs[r]) for r in ("true", "flattened", "steps"))
    assert t["mean_abs_bins"] == 0.0 and t["empty_share"] == 0.0 and fl["mean_abs_bins"] > 4 > 1 > st["mean_abs_bins"]
    assert sum(F.extra_attacks(truth, rungs["true"])) == sum(F.extra_attacks(truth, rungs["flattened"])) == 0
    assert sum(F.extra_attacks(truth, rungs["steps"])) == 6 and F.note_error(truth, rungs["steps"])["extra"] == 6
    assert F.note_error(truth, []) == {"lost": len(truth), "extra": 0, "error": len(truth)}
    ex = F.l_bend_excluded(truth)
    assert len(ex) == 3 and ex[0][0] == pytest.approx(0.5 + 98 * F.NR.BEND_FRAME_S - 0.050) and ex[0][1] == 2.0
    step_back = rungs["true"] + [note(1.62, 2.0, 64)]                 # the artefact's onset: never scored (A)
    assert F.note_error(truth, step_back, ex)["error"] == 0 and F.note_error(truth, step_back)["error"] == 1
    re_ = F.bend_retruth(truth)
    assert len(re_[0]["bends"]) == math.ceil(1.5 / F.NR.BEND_FRAME_S) and re_[0]["bends"][-1] == 0.0


def test_the_second_note_and_the_unsplit_counts():
    bent, held = F.BEND_LISTS["bend-under-semitone-held"][:2]      # a bend under a semitone, a held whole tone above
    assert bent["bends"] and not held["bends"]
    heard = F.rezero_bends([{"on": n["on"], "off": n["off"], "pitch": n["pitch"],
                             "bends": [v + 1 for v in (n["bends"] or [0] * 40)]} for n in (bent, held)], "global")
    assert F.bent_but_cleared(heard) == [0]                          # the clear rule takes its bend
    assert F.fault_kinds([bent, held], heard)["cleared"] == 1
    assert F.second_lost([bent, held], heard) == 0 and F.second_lost([bent, held], heard[:1]) == 1


def test_db_windows_cover_the_most_bends_outside_the_d_window():
    got = F.db_windows([3.0, 20.0, 22.0, 31.0, 40.0], 1.0, 60.0, 10.25)
    assert got == [(15.0, [20.0, 22.0]), (30.0, [31.0, 40.0])]    # 3.0 sits in D's window: no window holds it


def test_annotated_fragments():
    truth = [dict(note(0.0, 1.0, 60), arts=["bend"]), dict(note(2.0, 2.5, 64), arts=[])]
    notes = [note(0.0, 0.3, 60), note(0.3, 0.6, 61), note(0.6, 1.0, 62), note(2.0, 2.5, 64), note(0.5, 0.9, 67)]
    assert F.annotated_fragments(truth, notes) == {"bends": 1, "fragmented": 1, "fragments": 2}
    assert F.annotated_fragments(truth, notes[:1] + notes[3:]) == {"bends": 1, "fragmented": 0, "fragments": 0}
    assert F.art_label(note(0.0, 1.0, 60), truth) == "bend" and F.art_label(note(5.0, 6.0, 60), truth) == "unannotated"


def test_the_f6_pick_rule():
    pytest.importorskip("scipy")
    pts = [("sequential", 3, 1), ("both", 3, 1), ("sequential", 5, 2), ("sequential", 1, 0)]
    fj = {pts[0]: 1, pts[1]: 1, pts[2]: 4, pts[3]: 0}
    ne = {pts[0]: {"a": 2, "b": 3, "c": 1}, pts[1]: {"a": 2, "b": 3, "c": 1}, pts[2]: {"a": 1, "b": 2, "c": 0},
          pts[3]: {"a": 9, "b": 8, "c": 9}}
    got = F.pick_point(ne, fj)
    assert got["minimum"] == pts[2] and got["candidates"] == [pts[2]]   # one more on every list: [1, 1], not a tie
    ne[pts[2]] = {"a": 1, "b": 4, "c": 0}
    got = F.pick_point(ne, fj)
    assert got["minimum"] == pts[2] and set(got["candidates"]) == set(pts[:3])
    assert got["pick"] == pts[0]                          # tied: fewer bend-free joins, then sequential pairs only
    assert F.simpler_key(("both", 3, 2), {("both", 3, 2): 0}) < F.simpler_key(("sequential", 3, 1),
                                                                             {("sequential", 3, 1): 1})
    assert [F.simpler_key(("sequential", k, 1), {("sequential", k, 1): 0})[-1] for k in (3, 5, 1)] == [0, 1, 2]
    be = {("own", False): {"a": 1.0, "b": 2.0}, ("own", True): {"a": 0.9, "b": 2.2},
          ("line", False): {"a": 3.0, "b": 4.0}, ("line", True): {"a": 3.0, "b": 4.1}}
    assert F.pick_track_keep(be)["pick"] == ("own", False)          # a tie takes own, then cleared
    iv = {"mean": -2, "lo90": -3, "hi90": -1}
    assert F.keep_call(iv, {"L": {"mean": 0, "lo90": 0, "hi90": 0}})["call"] == "kept"
    assert F.keep_call(iv, {"L": {"mean": 1, "lo90": 0.5, "hi90": 2}})["call"] == "not kept"
    assert F.keep_call({"mean": -1, "lo90": -3, "hi90": 1}, {})["call"] == "undecided"
    assert F.keep_call({"mean": 2, "lo90": 1, "hi90": 3}, {})["call"] == "not kept"
    cp = F.clopper_pearson(0, 10)
    assert cp["lo90"] == 0.0 and 0 < cp["hi90"] < 0.3 and F.clopper_pearson(0, 0) is None


def test_f6_is_declared_before_its_numbers():
    import pathlib

    e = T.entries((pathlib.Path(__file__).resolve().parents[1] / "docs" / "dev-test-ledger.json").read_text())
    rec = e["note-rebuild"][F.PHASE_F6]
    assert {"junction_rule", "pick_rule", "keep_call", "seen", "E_relabel", "bend_list_artefact", "correction_12q",
            "amendments", "filled_in"} <= set(rec)
    assert "preliminary" not in rec                                   # declared: no figures of its own
    assert F.PHASE_F6_FROZEN not in e["note-rebuild"] and F.PHASE_F6_LISTS not in e["note-rebuild"]
