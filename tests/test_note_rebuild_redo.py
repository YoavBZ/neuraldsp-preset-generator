"""The redo's synthesis rules on made-up lists (`learn/note_rebuild.py`, the arms `tr-di` and `tr-plain`;
`docs/note-rebuild-plan.md` section 12): the ring rule, the placing rule, the sample variety and the bend rule, and the
stage-1 arms' code left as it was. Pure: runs on the light CI runner (no numpy)."""
import pathlib
import subprocess

import pytest

from learn import note_rebuild as N

REPO = pathlib.Path(__file__).resolve().parents[1]


def test_the_declared_constants():
    assert N.REDO_ARMS == ("tr-di", "tr-plain") and N.ARMS == ("nr-plain", "nr-level", "nr-oracle")
    assert N.RING_VARIANTS == ("ring-on", "ring-soft") and N.RING_SOFT_S == 0.150
    assert (N.MUTE_FRAME_S, N.MUTE_DROP_DB, N.MUTE_WITHIN_S, N.MUTE_FADE_S) == (0.020, 12.0, 0.060, 0.030)
    assert N.REPLUCK_FADE_S == 0.010 and N.TAIL_FADE_S == 0.150
    assert (N.TILT_ISOLATED_S, N.TILT_EARLY, N.TILT_LATE) == (0.600, (0.0, 0.050), (0.300, 0.500))
    assert (N.TILT_MAX_DB_S, N.TILT_MAX_GAIN_DB, N.TILT_MIN_GROUPS) == (12.0, 12.0, 3)
    assert (N.BEND_MEDIAN, N.BEND_MIN_FRAMES, N.BEND_MAX_SEMITONES, N.BEND_CLEAR_SEMITONES) == (3, 5, 3.0, 2)
    assert N.BEND_FRAME_S == pytest.approx(0.01161, abs=1e-5) and N.BEND_STEPS_PER_SEMITONE == 3
    assert N.VARIETY_S == 2.0 and N.SNAP_S == 0.020 and N.REFINE_S == 0.050


# --- the ring rule ----------------------------------------------------------------------------------------------------------

def test_ring_on_never_cuts_at_the_note_off():
    assert N.note_end(1.0, 1.2, "ring-on", [], 4.0) == (5.0, "sample", N.TAIL_FADE_S)
    assert N.note_end(1.0, 1.2, "ring-on", [], 4.0, repluck=1.5) == (1.5, "repluck", N.REPLUCK_FADE_S)


def test_ring_soft_starts_a_release_at_the_note_off():
    assert N.note_end(1.0, 1.2, "ring-soft", [], 4.0) == (pytest.approx(1.35), "release", N.RING_SOFT_S)
    assert N.note_end(1.0, 1.2, "ring-soft", [], 4.0, repluck=1.3)[1] == "repluck"


def test_a_mute_in_the_di_ends_every_note_sounding():
    mutes = [0.5, 2.0]
    assert N.note_end(1.0, 3.0, "ring-on", mutes, 4.0) == (2.0, "mute", N.MUTE_FADE_S)       # the first mute after it
    assert N.note_end(1.0, 3.0, "ring-soft", mutes, 4.0)[1] == "mute"
    assert N.note_end(2.5, 3.0, "ring-on", mutes, 4.0)[1] == "sample"                         # mutes before it: none
    with pytest.raises(ValueError):
        N.note_end(1.0, 2.0, "ring", [], 4.0)


def test_the_known_lists_cut_each_note_at_its_note_off():
    """The known-notes amendment (`phase_nr_1_redo_known_amend`): `cut` ends a note at its own note-off with the 10-ms
    fade; without it nothing changes (tr-di and tr-plain never pass it)."""
    assert N.note_end(1.0, 1.2, "ring-on", [], 4.0, cut=True) == (1.2, "cut", N.REPLUCK_FADE_S)
    assert N.note_end(1.0, 1.2, "ring-on", [], 4.0) == (5.0, "sample", N.TAIL_FADE_S)
    assert N.note_end(1.0, 3.0, "ring-on", [2.0], 4.0, cut=True)[1] == "mute"        # an earlier end still wins
    assert N.note_end(1.0, 1.2, "ring-on", [], 4.0, repluck=1.1, cut=True)[1] == "repluck"


# --- the placing rule and the variety --------------------------------------------------------------------------------------

def test_placing_prefers_a_string_not_still_ringing():
    assert N.placed_free(64, set(), set()) == (1, 0)              # E4: the open high E
    assert N.placed_free(64, set(), {1}) == (2, 5)                # the high E still rings: the B string's 5th fret
    assert N.placed_free(64, {2}, {1}) == (3, 9)
    assert N.placed_free(64, set(), {1, 2, 3, 4, 5, 6}) == (1, 0)   # every string rings: the lowest fret
    assert N.placed_free(40, {6}, set()) is None                 # E2 only on the low E, taken
    assert N.placed_free(64, set(), set(), lambda s, f: s != 1) == (2, 5)


def test_variety_order_and_next_source():
    src = N.variety_sources(64, (1, 0), set())
    assert src == [(1, 0), (2, 5), (3, 9), (4, 14), (5, 19), (1, 1)]   # placed; other strings by fret; fret +-1
    assert N.variety_sources(64, (2, 5), {1}) == [(2, 5), (3, 9), (4, 14), (5, 19), (2, 4), (2, 6)]
    assert N.next_source(src, (1, 0)) == (2, 5) and N.next_source(src, (1, 1)) == (1, 0)
    assert N.next_source(src, (6, 3)) == (1, 0)
    for last in src:                                             # a re-struck pitch never reuses its last sample
        assert N.next_source(src, last) != last
    assert N.next_source([(1, 0)], (1, 0)) == (1, 0)


# --- the bend rule ------------------------------------------------------------------------------------------------------------

def _note(on=0.0, pitch=64, off=1.0, bends=()):
    return {"on": on, "off": off, "pitch": pitch, "bends": list(bends)}


def test_bend_needs_five_frames_of_a_step_or_more():
    assert N.bend_curve(_note(bends=[0] * 5 + [3] * 5 + [0] * 5)) == [0.0] * 5 + [3.0] * 5 + [0.0] * 5
    assert not any(N.bend_curve(_note(bends=[0] * 5 + [3] * 4 + [0] * 5)))
    assert not any(N.bend_curve(_note(bends=[0, 3, 0, 3, 0, 3, 0])))          # the 3-frame median removes flicker
    assert N.bend_curve(_note()) == []


def test_bend_is_held_within_three_semitones():
    assert max(N.bend_curve(_note(bends=[20] * 8))) == 9.0


def test_no_bend_while_another_note_sounds_within_two_semitones():
    n = _note(bends=[3] * 30)
    near = _note(on=0.0, pitch=66, off=1.0)
    far = _note(on=0.0, pitch=67, off=1.0)
    assert not any(N.bend_curve(n, [n, near]))
    assert N.bend_curve(n, [n, far]) == [3.0] * 30
    late = _note(on=0.2, pitch=65, off=1.0)                       # from 0.2 s: the first 17 frames stay bent
    got = N.bend_curve(n, [n, late])
    assert got[:17] == [3.0] * 17 and not any(got[18:])


# --- the stage-1 arms are untouched ------------------------------------------------------------------------------------------

STAGE1_FUNCTIONS = ("synthesise", "rebuild_dry", "source_for", "placed", "note_length_s", "note_gain_db",
                    "onset_groups", "level_gains", "oracle_gains", "group_spans", "_span_gains", "refine_onsets",
                    "coarse_offset", "rise_curve", "clean_notes", "global_tuning_cents", "denoise_above",
                    "prepare_sample", "shifted", "at_lufs", "loudness", "span_rms", "Bank")


def _sources(text):
    import ast

    tree = ast.parse(text)
    return {n.name: ast.get_source_segment(text, n) for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in STAGE1_FUNCTIONS}


def test_the_stage1_arms_code_is_byte_for_byte_main_at_declaration():
    """Every function the stage-1 arms run, and every constant above the redo's block, as at main 1f13b563 (the commit
    the redo was declared on), byte for byte."""
    old = subprocess.run(["git", "-C", str(REPO), "show", "1f13b563:learn/note_rebuild.py"], capture_output=True,
                         text=True)
    if old.returncode:
        pytest.skip("the declaration's base commit is not in this clone")
    now = (REPO / "learn" / "note_rebuild.py").read_text()
    a, b = _sources(old.stdout), _sources(now)
    assert set(a) == set(STAGE1_FUNCTIONS) and a == b
    head = now.split("\n# --- the redo's dry guitars")[0]          # the redo's block is inserted, nothing else changes
    assert old.stdout.startswith(head) and now.endswith(old.stdout[len(head):])
