"""The note-rebuild's declared tables and readings, the exclusion list's keys and assert, the tab reader and matcher,
and the re-synthesis' note rules (`learn/note_rebuild.py`, `docs/note-rebuild-plan.md`). Pure: runs on the light CI
runner (no numpy)."""
import pytest

from learn import note_rebuild as N


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


# --- the two-number bar ------------------------------------------------------------------------------------------------

def test_row_reading_needs_both_numbers():
    good = _iv(-0.20, -0.30, -0.12)
    assert N.row_reading(good, good) == "passes"
    blind_i = _iv(0.00, -0.05, 0.05)                    # a blind pick: G passes, I does not
    assert N.row_reading(good, blind_i) == "fails"
    assert N.row_reading(_iv(-0.09, -0.15, -0.03), good) == "undecided"   # decided, mean short of -0.10
    assert N.row_reading(_iv(-0.12, -0.20, 0.01), good) == "undecided"    # mean past -0.10, not decided


def test_row_reading_edges():
    assert N.row_reading(_iv(-0.10, -0.2, -0.0001), _iv(-0.10, -0.2, -0.0001)) == "passes"
    assert N.row_reading(_iv(-0.2, -0.05, 0.1), _iv(-0.2, -0.3, -0.1)) == "fails"   # lower end at -0.05
    assert N.row_reading(_iv(-0.2, -0.0501, 0.1), _iv(-0.2, -0.3, -0.1)) == "undecided"
    with pytest.raises(ValueError):
        N.row_reading({"mean": -0.2}, _iv(-0.2, -0.3, -0.1))


def test_unreadable_wording():
    assert N.unreadable(_iv(0.0, -0.04, 0.05))
    assert not N.unreadable(_iv(0.0, -0.06, 0.04))


# --- the tables --------------------------------------------------------------------------------------------------------

def test_tables_whole():
    N.table_guard()


def test_n1_code_every_pair():
    want = {}
    for p in N.READINGS:
        for lv in N.READINGS:
            want[(p, lv)] = ("N1-pass" if "passes" in (p, lv) else
                             "N1-fail" if (p, lv) == ("fails", "fails") else "N1-between")
    for (p, lv), c in want.items():
        assert N.n1_code(p, lv) == c
    with pytest.raises(ValueError):
        N.n1_code("pass", "fails")


def test_n1_arm_prefers_plain():
    assert N.n1_arm("passes", "passes") == "nr-plain"
    assert N.n1_arm("undecided", "passes") == "nr-level"
    assert N.n1_arm("fails", "undecided") is None


def test_oracle_arm_never_decides():
    assert "nr-oracle" in N.ARMS
    assert N.n1_code.__code__.co_argcount == 2          # only nr-plain and nr-level enter the code


def test_n2_rows_run_only_on_a_pass():
    assert N.n2_next_row({}) == "B-clean"
    assert N.n2_next_row({"B-clean": "passes"}) == "B-alone"
    assert N.n2_next_row({"B-clean": "undecided"}) is None
    assert N.n2_next_row({"B-clean": "passes", "B-alone": "fails"}) is None
    assert N.n2_next_row({"B-clean": "passes", "B-alone": "passes"}) == "B-full"


def test_n2_codes():
    assert N.n2_code({}) is None
    assert N.n2_code({"B-clean": "passes"}) is None                        # B-alone is due
    assert N.n2_code({"B-clean": "fails"}) == "N2-notes"
    assert N.n2_code({"B-clean": "undecided"}) == "N2-between"
    assert N.n2_code({"B-clean": "passes", "B-alone": "fails"}) == "N2-stem"
    assert N.n2_code({"B-clean": "passes", "B-alone": "undecided"}) == "N2-stem"
    assert N.n2_code({"B-clean": "passes", "B-alone": "passes", "B-full": "fails"}) == "N2-exposed"
    assert N.n2_code({"B-clean": "passes", "B-alone": "passes", "B-full": "passes"}) == "N2-full"


def test_sign_test():
    assert N.sign_test_p(0, 0) == 1.0
    assert abs(N.sign_test_p(15, 5) - 0.020695) < 1e-5
    assert N.sign_test_p(14, 6) > 0.05


def test_n3_needs_the_blind_comparison():
    assert N.n3_code((15, 5), (15, 5)) == "N3-heard"
    assert N.n3_code((15, 5), (10, 10)) == "N3-blind"
    assert N.n3_code((5, 15), (15, 5)) == "N3-not-heard"
    assert N.n3_code((10, 10), (15, 5)) == "N3-between"


def test_np_code():
    assert N.np_code(True, [], True, True, 40) == "NP-ready"
    assert N.np_code(True, [], True, True, 29) == "NP-few"
    assert N.np_code(True, ["Middle/1-3"], True, True, 40) == "NP-gap"
    assert N.np_code(False, [], True, True, 40) == "NP-broken"
    assert N.np_code(True, [], True, True, None) is None


# --- P1: the exclusion list ---------------------------------------------------------------------------------------------

UNITS = [
    {"set": "goat", "unit": "goat/item_0@140.0#amp_3", "amp": "ac20",
     "prt": {"di": "goat/item_0", "item": "item_0", "band": "GOAT player1"}},
    {"set": "cap1", "unit": "cap/abc#ac20", "amp": "ac20",
     "prt": {"di": "goat/item_41", "di_item": "item_41", "capture": "abc", "creator": "cycle", "pack": "p1",
             "band": "cycle", "item": "cycle"}},
    {"set": "bks", "unit": "set5/BKS/22_DI.wav@290.0#24_Reamp.wav", "amp": "pr12",
     "prt": {"di": "set5/BKS_Bulldozer_Full/22_DI.wav", "band": "BKS"}},
    {"set": "panel", "unit": "panel/X/RAW@1#a.wav", "amp": "sw50r",
     "prt": {"di": "panel/X/RAW", "band": "X", "source": "MedleyDB (set 6, held out)"}},
]
LENDS = {"u": {"section": "sets-1-2/Forkupines_SugarFaith_Full/28_ElecGtr3DI.wav@310.0", "band": "Forkupines"}}


def test_exclusion_keys():
    k = N.exclusion_keys(UNITS, LENDS)
    assert k["goat_item"] == ["item_0", "item_41"]
    assert k["capture"] == ["abc"] and k["creator"] == ["cycle"] and k["pack"] == ["p1"]
    assert "set5/BKS_Bulldozer_Full" in k["session"]
    assert "sets-1-2/Forkupines_SugarFaith_Full" in k["session"]
    assert "Forkupines" in k["band"]
    assert not any(s.startswith(("goat", "panel")) for s in k["session"])


def test_clear_of_and_assert():
    excl = {"keys": N.exclusion_keys(UNITS, LENDS), "sha256": ["f" * 64]}
    assert N.clear_of({"goat_item": "item_5"}, excl) == []
    assert N.clear_of({"goat_item": "item_41"}, excl) == ["goat_item=item_41"]
    assert N.clear_of({"creator": "cycle", "sha256": "f" * 64}, excl) == ["creator=cycle", "sha256=ffffffffffff"]
    assert N.clear_of({"session": "sets-1-2/Forkupines_SugarFaith_Full"}, excl)
    assert N.assert_clear([{"goat_item": "item_5"}, {"capture": "zzz"}], excl)
    with pytest.raises(SystemExit):
        N.assert_clear([{"goat_item": "item_5"}, {"capture": "abc"}], excl)


def test_transcriber_overlap_flags_the_panel():
    o = N.transcriber_overlap(UNITS)
    assert list(o) == ["panel/X/RAW@1#a.wav|sw50r"]


def test_guitar_tracks():
    assert N.is_guitar_track("24_ElecGtr1DI.wav")
    assert N.is_guitar_track("AcousticGuitar.flac")
    assert not N.is_guitar_track("19_BassDI.wav")
    assert not N.is_guitar_track("gtr-notes.txt")


# --- P3: the tab and the matcher ----------------------------------------------------------------------------------------

TAB = """goat_dataset downtune:-12 tempo:100 start new_measure
clean0:note:s5:f3 clean0:note:s4:f2 wait:480
clean0:note:s3:f0 nfx:hammer wait:480
clean0:note:s3:f0 nfx:tie wait:480
measure:repeat_open new_measure clean0:note:s1:f0 nfx:dead wait:480 measure:repeat_close:2
clean0:note:s2:f1 bfx:tremolo_bar wait:480 end"""


def test_dadagp_notes():
    notes, down = N.dadagp_notes(TAB)
    assert down == -12
    assert [(n["string"], n["fret"]) for n in notes] == [(5, 3), (4, 2), (3, 0), (3, 0), (1, 0), (1, 0), (2, 1)]
    assert notes[2]["arts"] == ["hammer"] and notes[3]["tie"]
    assert notes[4]["arts"] == ["dead"] and notes[5]["arts"] == ["dead"]          # the repeat unrolled
    assert notes[6]["arts"] == ["tremolo_bar"]
    assert [n["beat"] for n in notes] == [0, 0, 1, 2, 3, 4, 5]
    assert [N.tab_pitch(n, 0) for n in notes] == [48, 52, 55, 55, 64, 64, 60]


def test_match_tab_chords_spread_and_missing_notes():
    notes, down = N.dadagp_notes(TAB)
    # MIDI: the chord's notes 20 ms apart, the high one first; the tied note absent; one dead note missing
    midi = [(1.02, 1.5, 48), (1.00, 1.5, 52), (1.5, 2.4, 55), (2.5, 2.6, 64), (3.0, 3.5, 60)]
    off, m = N.best_offset(notes, midi, down)
    assert off == 0 and m == 5
    idx = N.match_tab(notes, midi, off)
    assert [notes[k]["string"] for k in idx] == [5, 4, 3, 1, 2]


def test_best_offset_finds_an_octave():
    notes, down = N.dadagp_notes(TAB)
    midi = [(1.0, 1.5, 60), (1.0, 1.5, 64), (1.5, 2.4, 67), (2.5, 2.6, 76), (3.0, 3.1, 76), (3.5, 4, 72)]
    off, m = N.best_offset(notes, midi, down)
    assert off == 12 and m == 6


def test_window_notes_and_articulated_share():
    notes = [{"on": 0.5, "off": 1.0, "pitch": 60, "from": "tab", "arts": []},
             {"on": 1.9, "off": 2.4, "pitch": 62, "from": "tab", "arts": ["bend"]},
             {"on": 3.0, "off": 3.5, "pitch": 64, "from": "none", "arts": []}]
    w = N.window_notes(notes, 2.0, 1.2)
    assert [round(n["on"], 3) for n in w] == [-0.1, 1.0]
    assert N.articulated_share(notes) == 0.5
    assert N.articulated_share([notes[2]]) is None


# --- P4: the note rules -------------------------------------------------------------------------------------------------

def test_placed_lowest_free_fret():
    assert N.placed(64, set()) == (1, 0)
    assert N.placed(64, {1}) == (2, 5)
    assert N.placed(64, {1}, notes_ok=lambda s, f: (s, f) != (2, 5)) == (3, 9)
    assert N.placed(39, set()) is None


def test_clean_notes():
    notes = [{"on": 0.0, "off": 1, "pitch": 39}, {"on": 0.0, "off": 1, "pitch": 60},
             {"on": 0.01, "off": 1, "pitch": 60}] + \
            [{"on": 0.1, "off": 1, "pitch": 61 + k} for k in range(6)]
    kept, out = N.clean_notes(notes)
    assert out == {"out_of_range": 1, "merged": 1, "over_six": 1}
    assert len(kept) == 6


def test_onset_groups():
    notes = [{"on": t} for t in (0.0, 0.02, 0.2, 0.225, 0.26)]
    assert N.onset_groups(notes) == [[0, 1], [2, 3], [4]]


def test_note_length_and_gain():
    n = {"on": 1.0, "off": 2.0, "arts": []}
    assert N.note_length_s(n, None) == 1.0
    assert N.note_length_s(n, 1.4) == pytest.approx(0.4)
    assert N.note_length_s({**n, "arts": ["dead"]}, None) == pytest.approx(N.DEAD_S)
    assert N.note_length_s({**n, "arts": ["palm_mute"]}, None) == pytest.approx(N.PALM_S)
    assert N.note_gain_db({"arts": ["hammer"]}) == N.LEGATO_DB
    assert N.note_gain_db({"arts": ["dead", "ghost_note"]}) == N.DEAD_DB + N.GHOST_DB


class _OkBank:
    def ok(self, s, f):
        return f in N.FRETS

    def own_cents(self, s, f):
        return 3.0


def test_source_for():
    b = _OkBank()
    assert N.source_for({"pitch": 55, "string": 3, "fret": 0}, 10.0, b) == (3, 0, 7.0)
    # downtuned a semitone: the tab's string and fret, resampled down
    assert N.source_for({"pitch": 54, "string": 3, "fret": 0}, 0.0, b) == (3, 0, -103.0)
    # an octave from the tab: the same string an octave up the neck
    assert N.source_for({"pitch": 67, "string": 3, "fret": 0}, 0.0, b) == (3, 12, -3.0)
    # no tab: the placing rule
    assert N.source_for({"pitch": 64, "string": None, "fret": None, "_taken": {1}}, 0.0, b) == (2, 5, -3.0)


def test_n2_rows_declared_in_order():
    assert N.N2_ROWS == ("B-clean", "B-alone", "B-full")
