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
