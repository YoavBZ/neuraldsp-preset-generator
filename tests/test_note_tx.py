"""Research track 1, a better note transcriber (`learn/note_tx.py`; `docs/note-transcriber-plan.md`): the frozen
settings, the input guard, the pairing, the vote, the veto, the borrowed loudness, the figures, the readings, the
screen, every code and flag, the recommendations, the bridge table, the lock, the install record, the gate's rules,
the guards and every command's refusals. Pure: runs on the light CI runner (no numpy); MuScriptor and torch are never
imported. The last tests need the stored gate events (skipped elsewhere)."""
import argparse
import itertools
import json
import pathlib
import re

import pytest

from learn import note_transcribe as T
from learn import note_tx as X
from learn import tx_run as R

REPO = pathlib.Path(__file__).resolve().parents[1]
LEDGER = REPO / "docs" / "dev-test-ledger.json"
STORED = T.gate_work_dir() / "known"


def _n(on, pitch, off=None, amp=1.0, bends=()):
    return {"on": on, "off": on + 0.4 if off is None else off, "pitch": pitch, "amp": amp, "bends": list(bends)}


def _iv(m, lo, hi):
    return {"mean": m, "lo90": lo, "hi90": hi, "clusters": 10}


UP, ZERO, DOWN, FLAT = _iv(0.1, 0.05, 0.15), _iv(0.0, -0.05, 0.05), _iv(-0.1, -0.15, -0.05), _iv(0.02, -0.03, 0.07)


# --- the frozen settings -------------------------------------------------------------------------------------------------

def test_the_declared_settings():
    assert X.PACKAGE == ("muscriptor", "0.4.0", "a7e941b6e1d85a25f9fc4e00c2a46b43d4d516de0e751d54b42fda438ac2abb9",
                         1850618)
    med, small = X.WEIGHTS["medium"], X.WEIGHTS["small"]
    assert (med["repo"], med["revision"], med["bytes"], med["config_bytes"]) == (
        "MuScriptor/muscriptor-medium", "f32236969308476e01fd3aae67357de5feb05a2d", 1228144472, 126)
    assert med["sha256"] == "ac80adbdf85d87231735fd948af7013441c0afced316c4e9067fd5d8a7fb97ec"
    assert (small["revision"], small["bytes"], small["config_bytes"]) == (
        "8c127f603b807520fa465c838e9bfee8a91ada4e", 411888600, 124)
    assert small["sha256"] == "bbd482c786b895cf7d8f44185073d951adae2ebb8a66f82ca84cd1f84569549c"
    assert X.REQUIREMENTS == ("torch>=2.3", "numpy>=2", "einops>=0.4", "mido>=1.3", "packaging>=20.0",
                              "safetensors>=0.4", "huggingface_hub>=0.13", "soundfile>=0.14.0")
    assert X.INTERPRETER.endswith(".pyenv/versions/3.14.6/bin/python") and X.PYTHONS == ("3.14", "3.13")
    assert "python@3.13" in X.FALLBACK_INTERPRETER and X.INSTALL_MIN_GB == 36.0
    assert X.TOOLS == T.NR.HOME / "tools" / "muscriptor-venv" and X.WEIGHTS_DIR == T.NR.HOME / "tools" / \
        "muscriptor-weights" and X.OUT == T.NR.OUT / "tx"
    assert (X.MS_SR, X.MS_UP, X.MS_DOWN, X.MS_PEAK_DBFS) == (16000, 1, 3, -1.0) and 48000 * 1 / 3 == 16000
    assert X.MS_SETTINGS == R.MASKED and X.MS_FREE_SETTINGS == R.FREE
    assert X.MS_SETTINGS["use_sampling"] is False and X.MS_SETTINGS["cfg_coef"] == 1.0
    assert X.MS_SETTINGS["batch_size"] == X.MS_SETTINGS["beam_size"] == 1 and X.MS_SETTINGS["prelude_forcing"]
    assert X.DEVICE_DTYPE == {"mps": "float16", "cpu": "float32"} and R.THREADS == 4
    assert X.REPEAT_WINDOWS == 4 and X.DEV_RUNS == 54 == 2 * 27 and X.SIZE_SWITCH_S == 7200.0
    assert (X.PAIR_ONSET_S, X.END_SHARE, X.END_MIN_S) == (0.050, 0.20, 0.050) and X.VETO_INTERVALS == (12, 19, 24)
    assert X.RECALL_GUARD == 0.05 and X.CHECK_SLACK == 1 and X.UNPAIRED_LOOKUP == 0.05
    assert X.GUARDED_CHECKS == ("playing-covered", "judge-accepts", "ring-kept", "chords-kept")
    assert set(X.NOTE_KINDS) == {"list", "list-free", "truth", "goat", "goat-free"}
    assert all(X.NOTE_KINDS[k] == R.FREE for k in ("list-free", "goat-free"))


def test_the_names():
    assert X.LEDGER_ID == "note-transcriber" and X.PLAN == "docs/note-transcriber-plan.md"
    assert (X.PHASE, X.PHASE_GO, X.PHASE_INSTALL, X.PHASE_LISTS, X.PHASE_GO_READ, X.PHASE_NOTES, X.PHASE_READ,
            X.PHASE_BRIDGE) == ("phase_tx", "phase_tx_go", "phase_tx_install", "phase_tx_lists", "phase_tx_go_read",
                                "phase_tx_notes", "phase_tx_read", "phase_tx_bridge")
    assert X.RESERVED_PHASES == ("phase_tx_stems", "phase_tx_stem_read") and X.RESERVED_SEEDS == (20261411, 20261412)
    assert X.RESERVED_CODE_PREFIX == "TXS-" and not any(c.startswith("TXS-") for c in X.CODES + X.SCREEN)
    assert X.ARMS == ("tx-bp", "tx-ms", "tx-vote") and X.BESIDE_ARMS == ("tx-veto", "tx-ms-free")
    assert X.BRIDGE_VERSIONS == ("bv-asis", "bv-loud", "bv-ends")
    assert X.CODES == ("TXR-vote", "TXR-ms", "TXR-ends", "TXR-undecided") and X.SCREEN == ("TXR-none", "lists-go")
    arms = {a.lower() for a in X.ALL_ARMS}
    assert not any(c.lower() in arms for c in X.CODES + X.SCREEN)   # no code differs from an arm only by case
    assert set(X.RECOMMENDATION) == set(X.CODES + X.SCREEN)
    assert X.CODE_FILES == T.CODE_FILES + ("learn/note_tx.py", "learn/tx_run.py")
    assert all((REPO / f).exists() for f in X.CODE_FILES)


# --- the input guard -------------------------------------------------------------------------------------------------------

LISTING = {"files": [{"player": "P1", "kind": "chords", "name": "c1",
                      "di": "/x/guitar-techs/P1-downloads/P1_chords/audio/directinput/directinput_c1.wav",
                      "midi": "/x/guitar-techs/P1-downloads/P1_chords/midi/midi_c1.mid"},
                     {"player": "P2", "kind": "scales", "name": "s1",
                      "di": "/x/elsewhere/directinput_s1.wav", "midi": "/x/elsewhere/midi_s1.mid"},
                     {"player": "P3", "kind": "music", "name": "m1",
                      "di": "/x/guitar-techs/P3_music/directinput_m1.wav", "midi": "/x/P3_music/m.mid"}],
           "windows": [{"key": "P1|chords|c1@10", "player": "P1", "kind": "chords", "name": "c1", "consistent": True},
                       {"key": "P1|chords|c1@70", "player": "P1", "kind": "chords", "name": "c1", "consistent": False},
                       {"key": "P2|scales|s1@10", "player": "P2", "kind": "scales", "name": "s1", "consistent": True},
                       {"key": "P3|music|m1@10", "player": "P3", "kind": "music", "name": "m1", "consistent": True}]}
DEV = [f"item_{k}" for k in range(1, 28)]


def test_declared_input_passes_the_declared_material():
    assert X.declared_input("list:bend", None, None) == {"source": "list:bend", "kind": "list", "key": "bend"}
    assert X.declared_input("truth:P1|chords|c1@10", LISTING, None)["key"] == "P1|chords|c1@10"
    assert X.declared_input("goat-dev:item_7", None, DEV)["kind"] == "goat-dev"
    assert sorted(T.KNOWN_NOTES) == [s.split(":", 1)[1] for s in (f"list:{k}" for k in sorted(T.KNOWN_NOTES))]


@pytest.mark.parametrize("src,match", [
    ("list:chords-seven", "ten known lists"),
    ("truth:P1|chords|c9@10", "not a window"),
    ("truth:P3|music|m1@10", "P3"),                              # a P3 window is never read
    ("truth:P1|chords|c1@70", "not a consistent window"),        # an inconsistent window of the listing
    ("truth:P2|scales|s1@10", "outside"),                        # its file sits outside the P1/P2 folders
    ("goat-dev:item_99", "27 development"),                      # a GOAT item outside the 27
    ("part:bks|unit-1", "not declared material"),                # a row part
    ("replay:goat|item_3@30", "not declared material"),          # a replay part
    ("stem:xlnoG|p1", "not declared material"),
    ("song:anything", "not declared material"),
    ("/Users/someone/song.wav", "not declared material"),        # any path
])
def test_declared_input_refuses_everything_else(src, match):
    with pytest.raises(SystemExit, match=match):
        X.declared_input(src, LISTING, DEV)


def test_the_development_items_must_be_the_27():
    with pytest.raises(SystemExit, match="not the declared 27"):
        X.declared_input("goat-dev:item_7", None, DEV[:26])
    doc = X.manifest_doc([("list:bend", "a" * 64), ("goat-dev:item_7", "b" * 64)])
    assert R.manifest_sources(doc) == {"a" * 64: "list:bend", "b" * 64: "goat-dev:item_7"}   # tx_run reads it


def test_run_ms_refuses_undeclared_material_before_writing(tmp_path):
    with pytest.raises(SystemExit, match="not declared material"):
        X.run_ms([(None, "list:bend"), (None, "part:bks|1")], tmp_path / "w", "w", "cpu", R.MASKED, None, DEV)
    assert not (tmp_path / "w").exists()


# --- the note lists --------------------------------------------------------------------------------------------------------

def test_pair_notes_is_match_notes():
    ref = [_n(0.0, 60), _n(0.0, 64), _n(0.5, 67), _n(1.0, 60), _n(1.02, 60), _n(2.0, 72)]
    est = [_n(0.01, 60), _n(0.04, 60), _n(0.03, 64), _n(0.56, 67), _n(1.01, 60), _n(2.0, 71), _n(2.05, 72)]
    m = T.match_notes(ref, est)
    p = X.pair_notes(ref, est)
    assert len(p) == m["matched"] and sorted(i for i, _ in p) == m["ref_matched"]
    f = X.window_figures(ref, est)
    assert (f["matched"], f["ref"], f["est"]) == (m["matched"], m["ref"], m["est"])
    assert (f["precision"], f["recall"], f["f"]) == (m["precision"], m["recall"], m["f"])
    assert p == [(0, 0), (1, 2), (3, 4), (5, 6)]


def test_end_match_and_the_note_end_pairing():
    r = _n(0.0, 60, off=1.0)
    assert X.end_match(r, _n(0.0, 60, off=1.2)) and not X.end_match(r, _n(0.0, 60, off=1.21))
    s = _n(0.0, 60, off=0.1)
    assert X.end_match(s, _n(0.0, 60, off=0.15)) and not X.end_match(s, _n(0.0, 60, off=0.16))   # the 50 ms floor
    truth = [_n(0.0, 60, off=1.0), _n(1.0, 64, off=2.0)]
    est = [_n(0.01, 60, off=1.1), _n(1.0, 64, off=3.0)]
    f = X.window_figures(truth, est)
    assert f["matched"] == 2 and f["end_matched"] == 1 and f["end_f"] == 0.5


def test_the_vote_of_a_list_with_itself_is_the_list():
    a = [_n(0.0, 52), _n(0.0, 59), _n(0.5, 64, amp=0.4, bends=[0, 3, 3]), _n(1.0, 64)]
    v = X.vote_notes(a, a)
    assert [{k: x[k] for k in a[0]} for x in v] == a and all(x["ms_off"] == x["off"] for x in v)
    assert X.veto_notes(a, a) == a and X.ends_notes(a, a) == a


def test_a_ghost_in_one_list_only_and_an_unpaired_seventh():
    bp = [_n(0.5, 52), _n(0.51, 64), _n(0.52, 59), _n(1.5, 55), _n(1.52, 62)]   # 64: +12 over 52; 62: +7 over 55
    ms = [_n(0.5, 52), _n(0.52, 59), _n(1.51, 55)]
    vote, veto = X.vote_notes(bp, ms), X.veto_notes(bp, ms)
    assert [n["pitch"] for n in vote] == [52, 59, 55]               # the vote drops both
    assert [n["pitch"] for n in veto] == [52, 59, 55, 62]           # the veto drops the +12 ghost and keeps the +7


def test_the_veto_only_drops_the_ghost_shape():
    paired = [_n(0.5, 45), _n(2.0, 45)]
    bp = paired + [_n(0.51, 64), _n(0.53, 69), _n(2.01, 58), _n(1.0, 57)]
    # 64 = 45 + 19, 69 = 45 + 24: dropped; 58 = 45 + 13: kept; 57 = 45 + 12 but in another onset group: kept
    assert sorted(n["pitch"] for n in X.veto_notes(bp, paired)) == [45, 45, 57, 58]
    lone = [_n(0.5, 45), _n(0.51, 57)]                              # +12 over an unpaired note: kept
    assert X.veto_notes(lone, []) == lone


def test_tx_ms_borrows_loudness_and_bends():
    bp = [_n(0.5, 60, amp=0.8, bends=[0, 3, 3]), _n(1.0, 64, amp=0.2), _n(2.0, 67, amp=0.5)]
    ms = [_n(0.52, 60, off=1.3), _n(1.5, 62, off=1.9)]
    notes, rep = X.ms_with_bp(ms, bp)
    assert notes[0] == {"on": 0.52, "off": 1.3, "pitch": 60, "amp": 0.8, "bends": [0, 3, 3]}
    assert notes[1] == {"on": 1.5, "off": 1.9, "pitch": 62, "amp": 0.5, "bends": []}     # the window's median, no bend
    assert rep == {"notes": 2, "unpaired": 1, "unpaired_share": 0.5}
    alone, rep = X.ms_with_bp(ms, [])
    assert "amp" not in alone[0] and rep["unpaired"] == 2                                # counts as 1 in note_weights
    ends = X.ends_notes(bp, ms)
    assert ends[0]["off"] == 1.3 and ends[1] == bp[1] and len(ends) == len(bp)
    arms, reps = X.arm_notes(bp, ms, ms)
    assert set(arms) == set(X.ALL_ARMS) and set(reps) == {"tx-ms", "tx-ms-free"}
    assert "tx-ms-free" not in X.arm_notes(bp, ms)[0]


def test_ms_events_feed_timed_notes():
    rec = {"notes": [{"on": 0.5, "off": 1.0, "pitch": 60, "instrument": "clean_electric_guitar"}], "pre_s": 0.75}
    got = X.ms_events(rec)
    assert got["pre_s"] == 0.75 and T.notes_from_events(got["events"]) == [
        {"on": 0.5, "off": 1.0, "pitch": 60, "amp": 0.0, "bends": []}]


# --- the figures ---------------------------------------------------------------------------------------------------------------

def test_window_figures():
    truth = [_n(0.5, 45), _n(0.5, 52), _n(0.5, 57), _n(1.5, 45), _n(1.5, 52), _n(1.5, 57),
             _n(3.0, 64, off=5.0), _n(4.0, 64, off=4.4)]
    est = [_n(0.5, 45), _n(0.5, 52), _n(0.51, 57), _n(0.52, 69), _n(1.5, 45), _n(1.5, 52), _n(3.0, 64, off=5.0),
           _n(3.5, 64), _n(6.0, 40)]
    f = X.window_figures(truth, est)
    assert (f["matched"], f["ref"], f["est"]) == (6, 8, 9) and f["precision"] == 6 / 9 and f["recall"] == 6 / 8
    assert f["chord_notes"] == 6 and f["chord_found"] == 5 and f["chord_recall"] == 5 / 6
    assert f["restruck_notes"] == 1 and f["restruck_found"] == 0             # the 64 struck while it rings
    assert f["extras"] == {"harmonic": 1, "re-find": 1, "other": 1}
    p = X.pooled([f, f])
    assert p["precision"] == 6 / 9 and p["chord_recall"] == 5 / 6 and p["extras"]["harmonic"] == 2
    assert X.window_figures([], [])["precision"] is None


def test_bend_figures():
    bent = [0] * 3 + [3] * 40
    truth = [_n(0.5, 64, off=1.0, bends=bent), _n(2.0, 67)]
    kept = [_n(0.5, 64, off=1.0, bends=bent), _n(2.0, 67)]
    f = X.bend_figures(truth, kept, kept)
    assert f["ref"] == "truth" and f["bent"] == 1 and f["kept"] == 1 and 0.9 < f["span_share"] <= 1.0
    assert X.bend_figures(truth, [_n(2.0, 67)], kept)["span_share"] == 0.0     # the bent note dropped
    assert X.bend_figures(truth, [_n(0.5, 64, off=1.0)], kept)["span_share"] == 0.0   # kept, plain
    f = X.bend_figures(None, kept, kept)
    assert f["ref"] == "tx-bp" and f["bent"] == 1
    assert X.bend_figures(None, [], [_n(0.5, 60)])["span_share"] is None


def _row(cluster, figs, st="lists", group="lists", kind=None):
    return {"set": st, "cluster": cluster, "key": cluster, "group": group, "kind": kind, "figures": figs}


def _fig(m, ref, est, me=None, chord=(0, 0)):
    me = m if me is None else me
    return {"matched": m, "ref": ref, "est": est, "precision": m / est, "recall": m / ref, "f": 2 * m / (ref + est),
            "end_matched": me, "end_f": 2 * me / (ref + est), "ends_right": me, "end_accuracy": me / m if m else None,
            "chord_notes": chord[1], "chord_found": chord[0], "chord_recall": chord[0] / chord[1] if chord[1] else None,
            "restruck_notes": 0, "restruck_found": 0, "extras": {"harmonic": est - m, "re-find": 0, "other": 0}}


def test_set_summary_pairs_each_window_against_tx_bp():
    rows = [_row("a", {"tx-bp": _fig(10, 10, 20), "tx-vote": _fig(10, 10, 12)}),
            _row("b", {"tx-bp": _fig(10, 10, 16), "tx-vote": _fig(9, 10, 10)}),
            _row("c", {"tx-bp": _fig(8, 10, 10), "tx-vote": _fig(8, 10, 9)})]
    s = X.set_summary(rows, "lists")
    assert s["windows"] == 3 and s["clusters"] == 3 and s["pooled"]["tx-bp"]["precision"] == 28 / 46
    d = s["diff"]["tx-vote"]["precision"]
    want = [10 / 12 - 0.5, 0.9 - 10 / 16, 8 / 9 - 0.8]
    assert d["mean"] == pytest.approx(sum(want) / 3) and d["clusters"] == 3 and d["lo90"] < d["mean"] < d["hi90"]
    assert "tx-bp" not in s["diff"]
    real = [_row("P1|chords|x", {"tx-bp": _fig(1, 2, 2)}, "real", "P1", "chords"),
            _row("P2|scales|y", {"tx-bp": _fig(1, 2, 2)}, "real", "P2", "scales")]
    assert X.report_groups(rows + real) == ["lists", "real", "P1", "P2", "P1|chords", "P2|scales"]
    assert X.set_summary(rows + real, "P2|scales")["windows"] == 1


# --- the readings --------------------------------------------------------------------------------------------------------------

def test_the_reading_rules():
    assert X.precision_raised(UP) and not X.precision_raised(FLAT) and not X.precision_raised(DOWN)
    assert X.precision_not_better(DOWN) and X.precision_not_better(ZERO) and not X.precision_not_better(FLAT)
    assert X.precision_not_better(_iv(0.05, -0.2, 0.0)) and not X.precision_not_better(UP)   # its upper end at 0
    assert not X.precision_not_better({"mean": None, "lo90": None, "hi90": None})
    assert X.f_not_worse(FLAT) and X.f_not_worse(UP) and not X.f_not_worse(DOWN) and X.f_not_worse(None)
    assert X.ends_better(UP) and X.ends_better(UP, FLAT) and not X.ends_better(UP, DOWN) and not X.ends_better(FLAT)
    bp = {"recall": 1.0, "chord_recall": 0.9}
    assert X.recall_held({"recall": 0.95, "chord_recall": 0.85}, bp)
    assert not X.recall_held({"recall": 0.94, "chord_recall": 0.9}, bp)
    assert not X.recall_held({"recall": 1.0, "chord_recall": 0.84}, bp)
    assert X.recall_held({"recall": 1.0, "chord_recall": None}, {"recall": 1.0, "chord_recall": None})
    ck = {c: 20 for c in X.GUARDED_CHECKS}
    assert X.recall_held(bp, bp, checks={**ck, "ring-kept": 19}, checks_bp=ck)        # one window fewer: held
    assert not X.recall_held(bp, bp, checks={**ck, "chords-kept": 18}, checks_bp=ck)  # two fewer: not
    assert X.recall_held(bp, bp, checks={**ck, "onsets-found": 0}, checks_bp={**ck, "onsets-found": 27})   # a report


def _reading(p_l, f_l, e_l, held_l=True, p_r=None, f_r=None, e_r=None, held_r=True):
    def one(p, f, e, h):
        return {"precision": p, "f": f, "end_f": e, "end_accuracy": e, "precision_raised": X.precision_raised(p),
                "precision_not_better": X.precision_not_better(p), "f_not_worse": X.f_not_worse(f), "recall_held": h}
    out = {"lists": one(p_l, f_l, e_l, held_l)}
    if p_r is not None:
        out["real"] = one(p_r, f_r, e_r, held_r)
    out["ends_better"] = X.ends_better(e_l, e_r)
    return out


def test_the_screen():
    nb = _reading(DOWN, FLAT, FLAT)
    assert X.lists_screen({"tx-vote": nb, "tx-ms": nb}) == "TXR-none"          # both decided not better, no ends
    und = _reading(_iv(0.03, -0.01, 0.07), FLAT, FLAT)                         # means above zero, not clear of it
    assert X.lists_screen({"tx-vote": und, "tx-ms": und}) == "lists-go"        # undecided is not failed
    assert X.lists_screen({"tx-vote": nb, "tx-ms": und}) == "lists-go"         # one decided, one undecided
    ends = _reading(DOWN, FLAT, UP)
    assert X.lists_screen({"tx-vote": nb, "tx-ms": ends}) == "lists-go"        # ends better: not TXR-none
    assert X.lists_screen({"tx-vote": _reading(UP, FLAT, FLAT), "tx-ms": nb}) == "lists-go"
    assert X.recommendation("TXR-none")["text"].startswith("stop") and "phase_tx_go_read" in X.recommendation(
        "lists-go")["text"]


def test_fewer_extras_with_the_same_ends_never_read_as_better_ends():
    """PR #553's review, Q2: note-end F falls with extra notes, so it is a report; "ends better" reads end accuracy."""
    rows = []
    for k in range(5):
        bp = _fig(10, 10, 20 + k, me=7)                            # 7 of 10 ends right, many extras
        vote = _fig(10, 10, 11, me=7)                              # the same 7 ends, the extras gone
        better = _fig(10, 10, 20 + k, me=9)                        # the same extras, 9 of 10 ends right
        rows.append(_row(f"l{k}", {"tx-bp": bp, "tx-vote": vote, "tx-ms": better}))
    s = {"lists": X.set_summary(rows, "lists")}
    d = s["lists"]["diff"]
    assert d["tx-vote"]["end_f"]["lo90"] > 0 and d["tx-vote"]["end_accuracy"]["mean"] == 0  # end F up, ends the same
    vote, ms = X.arm_reading(s, "tx-vote"), X.arm_reading(s, "tx-ms")
    assert not vote["ends_better"] and ms["ends_better"]
    nb = X.arm_reading({"lists": X.set_summary([dict(r, figures={"tx-bp": r["figures"]["tx-bp"],
                                                                "tx-vote": r["figures"]["tx-bp"],
                                                                "tx-ms": r["figures"]["tx-vote"]})
                                                for r in rows], "lists")}, "tx-ms")
    assert not nb["ends_better"]                                   # fewer extras alone: never TXR-ends

def test_every_code_and_flag_is_reachable():
    win = _reading(UP, FLAT, FLAT, True, UP, FLAT, FLAT, True)
    lose = _reading(FLAT, FLAT, FLAT, True, FLAT, FLAT, FLAT, True)
    ends = _reading(FLAT, FLAT, UP, True, FLAT, FLAT, FLAT, True)
    assert X.txr_code({"tx-vote": win, "tx-ms": win, "tx-veto": win}) == {
        "code": "TXR-vote", "flags": {"veto-holds": True, "ends_better": False}}
    assert X.txr_code({"tx-vote": lose, "tx-ms": win, "tx-veto": lose})["code"] == "TXR-ms"
    got = X.txr_code({"tx-vote": lose, "tx-ms": ends, "tx-veto": lose})
    assert got == {"code": "TXR-ends", "flags": {"veto-holds": False}}
    got = X.txr_code({"tx-vote": lose, "tx-ms": lose, "tx-veto": win})
    assert got["code"] == "TXR-undecided" and got["flags"]["veto-holds"]
    assert X.recommendation(got["code"], got["flags"])["veto_candidate"]
    assert X.txr_code({"tx-vote": _reading(UP, FLAT, UP, True, UP, FLAT, FLAT, True), "tx-ms": lose,
                       "tx-veto": lose})["flags"]["ends_better"]
    assert X.recommendation("TXR-ms", {}, 0.06)["lookup_first"] and not X.recommendation("TXR-ms", {}, 0.05)[
        "lookup_first"]
    assert not X.recommendation("TXR-vote", {"veto-holds": True})["veto_candidate"]   # a flag, never the code


def test_a_gain_on_one_set_only_or_with_a_broken_guard_is_undecided():
    lists_only = _reading(UP, FLAT, FLAT, True, FLAT, FLAT, FLAT, True)
    worse_f = _reading(UP, DOWN, FLAT, True, UP, FLAT, FLAT, True)     # precision up, recall inside, F decided worse
    lost = _reading(UP, FLAT, FLAT, True, UP, FLAT, FLAT, False)       # recall or a check guard broken on the DIs
    none = _reading(FLAT, FLAT, FLAT, True, FLAT, FLAT, FLAT, True)
    for r in (lists_only, worse_f, lost):
        assert X.txr_code({"tx-vote": r, "tx-ms": none, "tx-veto": none})["code"] == "TXR-undecided"


def test_every_combination_ends_in_exactly_one_code():
    ivs = (UP, FLAT, DOWN)
    seen = set()
    for pv, fv, pm, em, hv in itertools.product(ivs, (FLAT, DOWN), ivs, ivs, (True, False)):
        rv = _reading(pv, fv, FLAT, hv, pv, fv, FLAT, hv)
        rm = _reading(pm, FLAT, em, True, pm, FLAT, FLAT, True)
        got = X.txr_code({"tx-vote": rv, "tx-ms": rm, "tx-veto": rv})
        assert got["code"] in X.CODES
        seen.add(got["code"])
        assert X.lists_screen({"tx-vote": rv, "tx-ms": rm}) in X.SCREEN
    assert seen == set(X.CODES)


def test_summarise_screen_and_read_on_made_up_rows():
    def figs(bp, vote, ms):
        return {"tx-bp": bp, "tx-vote": vote, "tx-ms": ms, "tx-veto": vote, "tx-ms-free": ms}
    rows = [_row(f"l{k}", figs(_fig(10, 10, 16 + k), _fig(10, 10, 11), _fig(10, 10, 12))) for k in range(5)]
    for r in rows:
        r["borrow"] = {"tx-ms": {"notes": 12, "unpaired": 0}}
    s = X.summarise_screen(rows)
    assert s["screen"] == "lists-go" and s["readings"]["tx-vote"]["lists"]["precision_raised"]
    real = [_row(f"P1|chords|f{k}", figs(_fig(10, 10, 15 + k), _fig(10, 10, 11), _fig(9, 10, 12)), "real", "P1",
                 "chords") for k in range(4)]
    ck = {c: True for c in X.GUARDED_CHECKS}
    goat = [{"checks": {a: {"notes": {"playing-covered": True, "onsets-found": True}, "ring-soft": ck}
                        for a in X.BUILT_ARMS}} for _ in range(27)]
    rd = X.summarise_read(rows, real, goat)
    assert rd["code"] == "TXR-vote" and rd["flags"]["veto-holds"] and rd["checks"]["tx-vote"]["chords-kept"] == 27
    assert set(rd["numbers"]) == {"lists", "real", "P1", "P1|chords"} and rd["unpaired_share"] == 0.0
    goat[0]["checks"]["tx-vote"]["ring-soft"] = dict(ck, **{"ring-kept": False})
    goat[1]["checks"]["tx-vote"]["ring-soft"] = dict(ck, **{"ring-kept": False})
    rd = X.summarise_read(rows, real, goat)                                    # two windows fewer: the guard breaks
    assert rd["code"] != "TXR-vote" and not rd["readings"]["tx-vote"]["real"]["recall_held"]


# --- the bridge -----------------------------------------------------------------------------------------------------------------

def test_every_row_of_the_bridge_table():
    b = X.bridge_difference
    assert (b("NV-loud", 1.0, "TXR-vote")["built"], b("NV-loud", 1.0, "TXR-vote")["stored"]) == ("bv-loud", "nv-loud")
    assert b("NV-undecided", 2.0, "TXR-ms")["stored"] == "nv-loud"
    assert (b("NV-short", None, "TXR-ms")["built"], b("NV-short", None, "TXR-ms")["stored"]) == ("bv-asis", "nv-hand")
    assert b("NV-none", None, "TXR-vote")["stored"] == "nv-asis" and b("NV-undecided", None, "TXR-vote")[
        "built"] == "bv-asis"
    for nv in ("NV-loud", "NV-short", "NV-none", "NV-undecided"):
        got = b(nv, 1.0 if nv == "NV-loud" else None, "TXR-ends")
        assert (got["built"], got["stored"]) == ("bv-ends", "nv-asis")
    assert b("NV-loud", 1.0, "TXR-undecided") is None and b("NV-none", None, "TXR-none") is None
    with pytest.raises(ValueError):
        b("NV-loud", None, "TXR-vote")
    assert X.bridge_versions("TXR-vote", 1.0) == ("bv-asis", "bv-loud") and X.bridge_versions("TXR-ms", None) == (
        "bv-asis",)
    assert X.bridge_versions("TXR-ends", 1.0) == ("bv-ends",) and X.bridge_versions("TXR-undecided", 1.0) == ()
    assert X.bridge_reading(b("NV-loud", 1.0, "TXR-vote"), DOWN) == "the winner adds"
    assert X.bridge_reading(b("NV-loud", 1.0, "TXR-vote"), FLAT) == "loudness alone stays"
    assert X.bridge_reading(b("NV-none", None, "TXR-vote"), DOWN) == "reported only"
    assert X.bridge_reading(b("NV-short", None, "TXR-vote"), _iv(0.1, 0.05, 0.2), _iv(1.0, 0.5, 1.5)) == \
        "the winner is the candidate clean-up"
    assert X.bridge_reading(b("NV-short", None, "TXR-vote"), _iv(0.9, 0.7, 1.1), _iv(1.0, 0.5, 1.5)) == "short"
    assert X.bridge_reading(b("NV-none", None, "TXR-ends"), DOWN) == "better ends count"
    assert X.bridge_reading(b("NV-none", None, "TXR-ends"), FLAT) == "better ends do not count"


def test_bridge_body_on_made_up_distances():
    vw, built = [], {}
    for k in range(4):
        d = {"nv-hand": 3.0 + 0.1 * k, "nv-asis": 4.0 + 0.1 * k, "nv-loud": 3.5 + 0.1 * k}
        vw.append({"set": "lists", "cluster": f"l{k}", "key": f"l{k}", "d": {"ring-soft": d, "ring-on": d}})
        built[f"l{k}"] = {"ring-soft": {"bv-asis": 3.2 + 0.1 * k, "bv-loud": 3.1 + 0.1 * k + 0.01 * k * k},
                          "ring-on": {"bv-asis": 3.2, "bv-loud": 3.1}}
    vw.append({"set": "goat", "cluster": "item_1", "key": "item_1", "d": {"ring-soft": {"nv-asis": 4.0, "nv-loud": 3.0}}})
    built["item_1"] = {"ring-soft": {"bv-asis": 3.5, "bv-loud": 2.9}}
    body = X.bridge_body(vw, built, "NV-loud", 1.0, "TXR-vote")
    assert body["difference"]["built"] == "bv-loud" and body["readings"]["lists"] == "the winner adds"
    n = body["numbers"]["ring-soft"]["lists"]
    assert n["bv-asis-nv-hand"]["mean"] == pytest.approx(0.2) and n["C"]["mean"] == pytest.approx(1.0)
    assert "bv-asis-nv-hand" not in body["numbers"]["ring-soft"]["goat"]       # GOAT: no nv-hand
    assert body["readings"]["real"] is None and not body["real_reported_only"]
    vw.append({"set": "real", "cluster": "P1|chords|x", "key": "r1", "d": {"ring-soft": {"nv-hand": 3.0, "nv-asis": 4.0,
                                                                                          "nv-loud": 3.5}}})
    vw.append({"set": "real", "cluster": "P1|chords|y", "key": "r2", "d": {"ring-soft": {"nv-hand": 3.0, "nv-asis": 4.0,
                                                                                          "nv-loud": 3.6}}})
    built.update(r1={"ring-soft": {"bv-asis": 3.2, "bv-loud": 3.0}}, r2={"ring-soft": {"bv-asis": 3.2, "bv-loud": 3.0}})
    assert X.bridge_body(vw, built, "NV-loud", 1.0, "TXR-vote")["readings"]["real"] == "the winner adds"
    held = X.bridge_body(vw, built, "NV-loud", 1.0, "TXR-vote", real_reported_only=True)
    assert held["readings"]["real"] == "reported only (the instrument check)"   # as "Measure first"'s own read
    assert held["readings"]["lists"] == "the winner adds"
    assert X.reproduce_refusal(3.0, 3.0 + 1e-10) is None and "nothing is read" in X.reproduce_refusal(3.0, 3.0001)


# --- the install, the gate and the records ---------------------------------------------------------------------------------

def _lock(extra=()):
    rows = [(X.PACKAGE[0], X.PACKAGE[1], X.PACKAGE[2])] + [
        (r.split(">=")[0].lower().replace("_", "-"), "9.9", "f" * 64) for r in X.REQUIREMENTS] + list(extra)
    return "".join(f"{n}=={v} --hash=sha256:{s}\n" for n, v, s in rows)


def test_the_lock():
    assert X.lock_refusal(_lock()) is None
    assert "unhashed" in X.lock_refusal(_lock() + "mido==1.3\n")
    assert "muscriptor" in X.lock_refusal(_lock().replace(X.PACKAGE[2], "0" * 64))
    assert "twice" in X.lock_refusal(_lock((("einops", "0.8", "e" * 64),)))
    assert "beat-this" in X.lock_refusal(_lock((("beat-this", "1.0", "b" * 64),)))
    assert "torch is not" in X.lock_refusal("".join(ln + "\n" for ln in _lock().splitlines()
                                                    if not ln.startswith("torch")))
    report = {"install": [{"metadata": {"name": "torch", "version": "2.14.0"},
                           "download_info": {"url": "https://x/torch-2.14.0-cp314-cp314-macosx_14_0_arm64.whl",
                                             "archive_info": {"hashes": {"sha256": "1" * 64}}}}]}
    assert "torch==2.14.0 --hash=sha256:" + "1" * 64 in T.lock_lines(report, [X.PACKAGE[:3]])


def test_the_weights_check():
    w = X.WEIGHTS["medium"]
    assert X.weights_refusal("medium", w["bytes"], w["sha256"], 126) is None
    assert "bytes" in X.weights_refusal("medium", 1, w["sha256"], 126)
    assert "sha256" in X.weights_refusal("medium", w["bytes"], "0" * 64, 126)
    assert "config.json" in X.weights_refusal("medium", w["bytes"], w["sha256"], 124)
    assert X.weights_refusal("small", X.WEIGHTS["small"]["bytes"], X.WEIGHTS["small"]["sha256"], 124) is None
    assert "declared size" in X.weights_refusal("large", 0, "", 0)


def test_the_install_record_holds_no_account_name_email_or_token():
    files = [{"path": "bin/python", "size": 10, "sha256": "a" * 64}]
    weights = {"size": "medium", "sha256": X.WEIGHTS["medium"]["sha256"], "config_sha256": "c" * 64}
    man = X.install_manifest("/py", "3.14.6", "l" * 64, "r" * 64, weights, files, 50.0, "2026-11-23 10:00:00")
    assert man["approval"] == {"date": "2026-11-23", "ledger": "note-transcriber phase_tx_go"}
    assert X.private_keys(man) == [] and man["installed_bytes"] == 10
    assert man["licences"]["muscriptor weights"].startswith("CC BY-NC 4.0")
    assert X.private_keys({"a": [{"user_email": 1}], "hf_token": 2}) == ["a[0].user_email", "hf_token"]
    with pytest.raises(SystemExit, match="no account name"):
        X.install_manifest("/py", "3.14", "l", "r", dict(weights, account="x"), files, 1.0, "now")
    rec = {"lock_sha256": "l" * 64, "weights_sha256": weights["sha256"], "gate_sha256": "g", "size": "medium",
           "device": "mps", "list_notes_listing_sha256": "n"}
    assert X.install_record_refusal(rec, man, "g", "n") is None
    assert "names no install" in X.install_record_refusal(None, man, "g", "n")
    assert "another lock" in X.install_record_refusal(dict(rec, lock_sha256="x"), man, "g", "n")
    assert "gate_sha256" in X.install_record_refusal(rec, man, "h", "n")
    assert "listing" in X.install_record_refusal(rec, man, "g", "m")


def test_the_device_and_size_rules():
    ok, bad = {"a": True, "b": True}, {"a": True, "b": False}
    assert X.device_choice({"mps": ok, "cpu": ok}) == "mps" and X.device_choice({"mps": bad, "cpu": ok}) == "cpu"
    assert X.device_choice({"mps": bad, "cpu": bad}) is None and X.device_choice({}) is None
    listing = {"windows": [{"player": "P1", "consistent": True}] * 79 + [{"player": "P1", "consistent": False}] * 159
               + [{"player": "P3", "consistent": True}] * 5}
    runs = X.stage_b_runs(listing)
    assert runs == 79 + 2 * 27                                   # the real count, not 265
    recs = [{"seconds": 2.0, "load_s": 40.0}, {"seconds": 4.0, "load_s": 40.0}]
    assert X.transcription_seconds(recs) == 3.0 and X.transcription_seconds([]) is None   # the load left out
    pr = X.projections_s({"mps": 20.0, "cpu": 30.0}, runs)
    assert pr == {"mps": 20.0 * 133, "cpu": 30.0 * 133}           # both recorded and printed
    assert X.projection_s(pr, "cpu") == 30.0 * 133 and X.projection_s(pr, "mps") == 20.0 * 133   # the chosen one
    assert X.projection_s(pr, None) is None
    assert X.size_choice(X.projection_s(pr, "mps")) == "medium"  # at a made-up 20 s: 44 min on 133 runs, not 88 on 265
    assert X.size_choice(7200.0) == "medium" and X.size_choice(7200.1) == "small" and X.size_choice(None) == "medium"
    one = [{"notes": [1]}, {"notes": [1]}, {"notes": [2]}, {"notes": [2]}]
    assert X.repeat_table(one, [{"notes": [1]}, {"notes": [3]}], 2) == [True, False]


def test_the_records_refusals():
    st = {"a": {"matched": 5, "ref": 6, "est": 9}}
    assert X.gate_list_refusal(st, {"a": {"matched": 5, "ref": 6, "est": 9, "f": 0.6}}) is None
    assert "gate's" in X.gate_list_refusal(st, {"a": {"matched": 5, "ref": 6, "est": 8}})
    assert "differ" in X.gate_list_refusal(st, {"b": st["a"]})
    rows = [{"key": "k1", "matched": 3, "ref": 4, "est": 5}]
    assert X.truth_report_refusal(rows, {"k1": {"matched": 3, "ref": 4, "est": 5}}) is None
    assert "not the truth report's" in X.truth_report_refusal(rows, {"k1": {"matched": 3, "ref": 4, "est": 6}})
    assert "not read" in X.truth_report_refusal(rows, {})
    assert X.lists_go_refusal({"sha256": "x", "screen": "lists-go"}) is None
    assert "stopped" in X.lists_go_refusal({"sha256": "x", "screen": "TXR-none"})
    assert "no screen" in X.lists_go_refusal(None)
    assert X.read_bridge_refusal({"code": "TXR-ends"}) is None and "no bridge" in X.read_bridge_refusal(
        {"code": "TXR-undecided"})
    inst = {"weights_sha256": "w", "lock_sha256": "l", "device": "mps"}
    rec = {"weights_sha256": "w", "lock_sha256": "l", "device": "mps", "settings": R.MASKED, "source": "list:bend"}
    assert X.note_refusal(rec, "list", inst) is None
    assert "settings" in X.note_refusal(rec, "list-free", inst)
    assert "device" in X.note_refusal(dict(rec, device="cpu"), "list", inst)
    assert "another install" in X.note_refusal(dict(rec, weights_sha256="v"), "list", inst)
    assert "not declared" in X.note_refusal(dict(rec, source="part:bks|1"), "list", inst)


# --- the guards and the ledger -------------------------------------------------------------------------------------------------

def test_the_keys_guard_reads_only_this_entry():
    local = {"note-transcriber": {"phase_tx": 1, "phase_tx_go": 2, "plan": "x"}, "note-rebuild": {"phase_nr": 3}}
    assert X.tx_keys_refusal(local, json.loads(json.dumps(local))) is None
    assert X.tx_keys_refusal(local, {**local, "note-rebuild": {}}) is None       # the redo's keys are the redo's
    assert X.tx_keys_refusal(local, {**local, "note-transcriber": {"phase_tx": 1, "phase_tx_go": 2}}) is None
    assert "phase_tx_go" in X.tx_keys_refusal(local, {**local, "note-transcriber": {"phase_tx": 1}})
    e = X.tx_entries(LEDGER.read_text())
    assert set(e) == {"note-transcriber", "note-rebuild"}


def test_the_ledger_holds_the_declaration_and_the_go():
    doc = json.loads(LEDGER.read_text())
    e = X.tx_entries(LEDGER.read_text())["note-transcriber"]
    assert e["plan"] == X.PLAN and (REPO / X.PLAN).exists()
    assert X.PHASE in e and X.PHASE_GO in e
    for later in (X.PHASE_LISTS, X.PHASE_GO_READ, X.PHASE_NOTES, X.PHASE_READ, X.PHASE_BRIDGE) + X.RESERVED_PHASES:
        assert later not in e                                     # each comes with its own PR
    inst = e[X.PHASE_INSTALL]                                     # the hash PR: the shape `require_install` reads
    assert inst["size"] == "medium" and inst["device"] == "mps"
    assert inst["weights_sha256"] == X.WEIGHTS["medium"]["sha256"]
    assert all(len(inst[k]) == 64 for k in ("lock_sha256", "gate_sha256", "list_notes_listing_sha256"))
    assert "No list has been scored" in inst["note"] and X.private_keys(inst) == []
    go = e[X.PHASE_GO]
    assert go["answer"] == "Go, I'll get access" and len(go["key_terms"]) == 4
    terms = " ".join(go["key_terms"])
    for t in ("gated terms", "rights warranty and indemnity", "CC BY-NC", "a development yardstick only"):
        assert t in terms
    assert "Cambridge-MT and MedleyDB" in go["material"] and "separate yes" in go["material"]
    text = json.dumps(e)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", text)               # no email address
    assert not re.search(r"hf_[A-Za-z0-9]{20,}", text)                       # no token
    assert "token is created" in text.lower()
    assert X.private_keys(e) == []
    nr = [t for t in doc["tests"] if t["test_id"] == "note-rebuild"][0]
    assert not any(k.startswith("phase_tx") for k in nr)          # nothing of this track in the redo's entry


@pytest.mark.parametrize("cmd", sorted(X.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(X, "tx_on_main", lambda: ({}, "this checkout's learn/note_tx.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        X.COMMANDS[cmd](argparse.Namespace(size=None, interpreter=None))


NEEDS = {"install": (X.PHASE_GO,), "gate": (X.PHASE_GO,), "lists": (X.PHASE_GO, X.PHASE_INSTALL),
         "transcribe": (X.PHASE_GO, X.PHASE_INSTALL, X.PHASE_LISTS, X.PHASE_GO_READ),
         "read": (X.PHASE_GO, X.PHASE_INSTALL, X.PHASE_LISTS, X.PHASE_GO_READ, X.PHASE_NOTES),
         "bridge": (X.PHASE_GO, X.PHASE_INSTALL, X.PHASE_LISTS, X.PHASE_GO_READ, X.PHASE_NOTES, X.PHASE_READ)}
NEEDS_NR = {"gate": (T.PHASE_TRUTH,), "transcribe": (T.PHASE_TRUTH,), "read": (T.PHASE_TRUTH,), "bridge": (T.PHASE_TRUTH, T.PHASE_VERSIONS)}


@pytest.mark.parametrize("cmd,missing", [(c, k) for c, ks in NEEDS.items() for k in (X.PHASE,) + ks]
                         + [(c, k) for c, ks in NEEDS_NR.items() for k in ks])
def test_every_command_refuses_without_each_phase_on_main(monkeypatch, cmd, missing):
    tx = {k: {"declared": True} for k in (X.PHASE,) + NEEDS[cmd] if k != missing}
    nr = {k: {"declared": True} for k in NEEDS_NR.get(cmd, ()) if k != missing}
    monkeypatch.setattr(X, "tx_on_main", lambda: ({"note-transcriber": tx, "note-rebuild": nr}, None))
    with pytest.raises(SystemExit, match=missing):
        X.COMMANDS[cmd](argparse.Namespace(size=None, interpreter=None))


def test_stage_b_refuses_after_txr_none_and_the_bridge_without_a_bridge_code(monkeypatch):
    tx = {k: {"declared": True} for k in (X.PHASE,) + NEEDS["bridge"]}
    tx[X.PHASE_LISTS] = {"sha256": "x", "screen": "TXR-none"}
    tx[X.PHASE_READ] = {"sha256": "x", "code": "TXR-undecided"}
    nr = {T.PHASE_TRUTH: {}, T.PHASE_VERSIONS: {}}
    monkeypatch.setattr(X, "tx_on_main", lambda: ({"note-transcriber": tx, "note-rebuild": nr}, None))
    with pytest.raises(SystemExit, match="TXR-none"):
        X.cmd_transcribe(None)
    with pytest.raises(SystemExit, match="no bridge"):
        X.cmd_bridge(None)


def test_the_small_gate_runs_only_after_the_size_switch(monkeypatch, tmp_path):
    monkeypatch.setattr(X, "tx_on_main", lambda: ({"note-transcriber": {X.PHASE: 1, X.PHASE_GO: 1},
                                                   "note-rebuild": {T.PHASE_TRUTH: {}}}, None))
    monkeypatch.setattr(X, "MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(X, "OUT", tmp_path / "tx")
    (tmp_path / "manifest.json").write_text("{}")
    with pytest.raises(SystemExit, match="only after the medium gate"):
        X.cmd_gate(argparse.Namespace(size="small"))
    X.gate_path("medium").parent.mkdir(parents=True)
    X.gate_path("medium").write_text(json.dumps({"body": {"size_rule": "medium"}}))
    with pytest.raises(SystemExit, match="only after the medium gate"):
        X.cmd_gate(argparse.Namespace(size="small"))
    with pytest.raises(SystemExit, match="exists: never overwritten"):
        X.cmd_gate(argparse.Namespace(size="medium"))           # a gate file is never overwritten


# --- the stored gate events (skipped without them) --------------------------------------------------------------------------

def _stored():
    if not STORED.exists() or len(list(STORED.glob("*.json"))) != 10:
        pytest.skip("the gate's stored list events are not on this machine")
    return {p.stem.split("-", 1)[1]: json.loads(p.read_text())["events"] for p in sorted(STORED.glob("*.json"))}


def test_the_stored_list_events_give_the_plans_counts():
    known = _stored()
    figs = {nm: X.window_figures([dict(n) for n in T.KNOWN_NOTES[nm]], T.clean_transcribed(T.notes_from_events(ev))[0])
            for nm, ev in known.items()}
    p = X.pooled(list(figs.values()))
    assert (p["matched"], p["ref"], p["est"]) == (259, 259, 431)
    assert p["extras"] == {"harmonic": 126, "re-find": 31, "other": 15}   # the review's sort, as the plan states
    assert p["end_matched"] == 216 and figs["let-ring-arpeggio"]["matched"] - figs["let-ring-arpeggio"][
        "end_matched"] == 19
    assert p["restruck_notes"] == 4                                       # underpowered: a report only
    assert p["ends_right"] == 216 and p["end_accuracy"] == pytest.approx(216 / 259)
    # Q2: with only the extras removed (every end the same), note-end F rises from 0.626 to 0.834; end accuracy does not
    hand = {nm: X.window_figures([dict(n) for n in T.KNOWN_NOTES[nm]], [T.clean_transcribed(T.notes_from_events(ev))[0][j]
                                 for _, j in X.pair_notes(T.KNOWN_NOTES[nm], T.clean_transcribed(
                                     T.notes_from_events(ev))[0])]) for nm, ev in known.items()}
    q = X.pooled(list(hand.values()))
    assert round(p["end_f"], 3) == 0.626 and round(q["end_f"], 3) == 0.834 and q["end_accuracy"] == p["end_accuracy"]
    stored = json.loads(T.gate_path().read_text())["body"]["known"] if T.gate_path().exists() else None
    if stored is not None:
        assert X.gate_list_refusal(stored, X.gate_figures(known)) is None
