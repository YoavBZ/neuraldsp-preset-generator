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
    assert X.RETIRED_BARS == {"RECALL_GUARD": 0.05, "CHECK_SLACK": 1, "UNPAIRED_LOOKUP": 0.05}   # T1: the record only
    assert not any(hasattr(X, k) for k in X.RETIRED_BARS)          # no bar left in code
    assert X.GUARDED_CHECKS == ("playing-covered", "judge-accepts", "ring-kept", "chords-kept")
    assert set(X.NOTE_KINDS) == {"list", "list-free", "truth", "goat", "goat-free", "list-large", "list-large-free"}
    assert all(X.NOTE_KINDS[k] == R.FREE for k in ("list-free", "goat-free", "list-large-free"))
    assert X.NOTE_KINDS["list-large"] == R.MASKED


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
    # T1: recall held is a direction on the paired intervals, no 0.05 bar
    assert X.recall_held(FLAT, FLAT) and X.recall_held(UP, None) and X.recall_held(None, None)
    small_loss = _iv(-0.04, -0.06, -0.02)                         # recall down 0.04, interval clear of zero below
    assert not X.recall_held(small_loss, FLAT) and not X.recall_held(FLAT, small_loss)   # reads "worse"
    assert X.recall_held(_iv(-0.20, -0.45, +0.05), FLAT)          # a big but undecided loss: not decided worse


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
    for share in (0.01, 0.06, None):                              # T1: on TXR-ms the lookup is always built
        r = X.recommendation("TXR-ms", {}, share)
        assert r["build_lookup"] and r["unpaired_share"] == share and "always built" in r["text"]
    assert not X.recommendation("TXR-vote", {}, 0.5)["build_lookup"]
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
    rd = X.summarise_read(rows, real, goat)                    # T1: two windows fewer is reported, gates nothing
    assert rd["code"] == "TXR-vote" and rd["readings"]["tx-vote"]["real"]["recall_held"]
    assert rd["check_windows"]["tx-vote"]["ring-kept"] == {"windows": 27, "lost": 2, "gained": 0,
                                                           "gained_less_lost": -2}
    assert rd["check_windows"]["tx-veto"]["ring-kept"]["gained_less_lost"] == 0
    assert "sizes: tx-vote lists: recall" in rd["recommendation"]["text"] and rd["sizes"].startswith("tx-vote lists")


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
    assert "declared size" in X.weights_refusal("huge", 0, "", 0)
    big = X.WEIGHTS["large"]
    assert (big["revision"], big["bytes"], big["config_bytes"]) == (
        "8809fdfbed2affa7ade94a7059e746e3880720e7", 5465642136, 125)
    assert big["sha256"] == "ac4eb6ea87dfc26b6ca6b954c6b967ab87ad4c7d08e078b25214f13ed051f397" == R.WEIGHTS["large"][0]
    good = "16bedd02b18770e43740419b0d5777f231047e96e8987f498e8a1123c39c9852"
    assert big["config_sha256"] == good
    assert X.weights_refusal("large", big["bytes"], big["sha256"], 125, good) is None
    assert "config.json is not" in X.weights_refusal("large", big["bytes"], big["sha256"], 125, "0" * 64)
    assert X.weights_refusal("medium", w["bytes"], w["sha256"], 126, "0" * 64) is None   # medium's recorded at install


def _size_rows(fs):
    """Ten made-up list rows whose tx-ms note F is fs[k]."""
    return [_row(f"l{k}", {"tx-bp": _fig(10, 10, 16), "tx-ms": dict(_fig(10, 10, 12), f=f)}) for k, f in enumerate(fs)]


def test_the_size_pick_reads_accuracy_and_reports_speed_beside():
    med = _size_rows([0.80] * 10)
    up = _size_rows([0.80 + 0.01 * (k % 3) for k in range(10)])     # large's F a little higher on average
    down = _size_rows([0.79] * 10)
    p = X.size_pick({"rows": {"medium": med, "large": up}, "projections": {"medium": 262.0, "large": 9000.0}})
    assert p["size"] == "large" and p["diff_large_less_medium"]["lo90"] > 0 and p["diff_large_less_medium"][
        "clusters"] == 10 and p["label"] == "large decided better" and not p["large_open_for_user"]
    mixed = _size_rows([0.80 + (0.03 if k % 2 else -0.02) for k in range(10)])   # mean above zero, interval not
    u = X.size_pick({"rows": {"medium": med, "large": mixed}, "projections": {"medium": 262.0, "large": 300.0}})
    assert u["diff_large_less_medium"]["mean"] > 0 and u["diff_large_less_medium"]["lo90"] <= 0
    assert u["size"] == "large" and u["label"] == "undecided, large kept" and not u["large_open_for_user"]   # T2
    assert p["over_two_hours"] and p["projections"] == {"medium": 262.0, "large": 9000.0}   # speed never picks
    worse = X.size_pick({"rows": {"medium": med, "large": down}, "projections": {}})
    assert worse["size"] == "medium" and worse["label"] == "large decided worse, medium kept"
    tie = X.size_pick({"rows": {"medium": med, "large": _size_rows([0.80] * 10)}, "projections": {"large": 100.0}})
    assert tie["size"] == "large" and not tie["over_two_hours"]       # T2: a tie keeps the default, large
    apart = [dict(r, cluster=f"x{k}") for k, r in enumerate(up)]     # no list in common
    nos = X.size_pick({"rows": {"medium": med, "large": apart}, "projections": {}})
    assert nos["size"] == "large" and nos["label"] == "fewer than two shared lists, large kept"
    assert not nos["large_open_for_user"]
    alone = X.size_pick({"rows": {"medium": med}, "projections": {"medium": 262.0}})
    assert alone["size"] == "medium" and alone["diff_large_less_medium"] is None   # large's gate stopped
    assert X.SCREENED_SIZES == ("medium", "large") and (X.PICK_ARM, X.PICK_FIELD) == ("tx-ms", "f")
    assert X.LIST_KINDS == {"medium": ("list", "list-free"), "large": ("list-large", "list-large-free")}


def test_speed_never_decides_a_muscriptor_size():
    """The user's stance (2026-11-23): no downgrade by speed alone; speed is reported."""
    slow = {"size": "large", "size_pick": {"over_two_hours": True, "projections": {"large": 9000.0}}}
    assert X.speed_note(slow, {"go": "yes"}) == "large's stage b projects 2.50 h (over two hours, reported only)"
    assert X.speed_note({"size": "medium", "size_pick": {"projections": {"medium": 262.0}}}, None) == \
        "medium's stage b projects 0.07 h"
    assert not hasattr(X, "slow_refusal") and not hasattr(X, "size_choice")    # both retired
    for size in ("medium", "large", "small"):
        assert X.gate_rule(size, 10 ** 9) == size and X.gate_rule(size, None) == size   # never a switch to small
    assert X.USER_STANCE.startswith("I don't see any justification to give up on accuracy for speed")


def test_later_stages_run_large_unless_large_is_measured_worse():
    assert X.LATER_STAGE_SIZE == "large"
    go = {"large": {"screen": "lists-go"}}
    for label in ("undecided, medium kept", "undecided, large kept", "large decided better",
                  "fewer than two shared lists, large kept"):
        assert X.later_stage_size({"size_pick": {"label": label}, "sizes": go}) == "large"
        assert X.later_stage_size({"size_pick": {"label": label},
                                   "sizes": {"large": {"screen": "TXR-none"}}}) == "medium"   # never on medium's screen
    assert X.later_stage_size({"size_pick": {"label": "large decided worse, medium kept"}, "sizes": go}) == "medium"
    assert X.later_stage_size({"size_pick": {"label": "large gate stopped, medium kept"}, "sizes": go}) == "medium"
    assert X.later_stage_size({}) == "medium"                    # no large screen at all
    slow = {"size": "large", "size_pick": {"over_two_hours": True, "projections": {"large": 9000.0}}}
    assert X.picked_size(slow) == "large" and X.picked_size({}) == "medium"   # a screen before the amendment
    open_ = {"size": "medium", "size_pick": {"large_open_for_user": True, "projections": {"large": 9000.0}},
             "sizes": {"medium": {"screen": "lists-go"}, "large": {"screen": "lists-go"}}}
    none_large = dict(open_, sizes={"medium": {"screen": "lists-go"}, "large": {"screen": "TXR-none"}})
    assert X.picked_size(none_large, {"size": "large"}) == "medium"   # never large on medium's screen
    assert X.picked_size(open_, {"size": "large"}) == "large"     # the user may take large on an undecided pick
    assert X.picked_size({"size": "medium", "size_pick": {"large_open_for_user": False}}, {"size": "large"}) == "medium"
    assert X.speed_note(open_, {"size": "large"}).startswith("large's stage b")   # reported for the size run
    assert not X.large_stopped({"note-transcriber": {X.PHASE_INSTALL_LARGE: {"gate_sha256": "g"}}})
    stop = {"stopped": "no repeat", "gate_sha256": "g"}
    assert X.large_stop_refusal(stop, "g", {"size": "large", "device": None}) is None
    assert "no gate_sha256" in X.large_stop_refusal({"stopped": "no repeat"}, "g", {"size": "large", "device": None})
    assert "not the file" in X.large_stop_refusal(stop, "h", {"size": "large", "device": None})
    assert "device null" in X.large_stop_refusal(stop, "g", {"size": "large", "device": "mps"})


def test_the_side_figure_counts_only_notes_starting_inside_and_decides_nothing():
    truth = [_n(0.5, 60), _n(1.0, 64)]
    est = [_n(-0.30, 55), _n(-0.03, 67), _n(0.5, 60), _n(1.0, 64)]   # a chord ringing in, a note 30 ms early
    assert X.INSIDE_LEADS == {"inside": 0.0, "inside_lead": 0.050}
    assert [n["pitch"] for n in X.inside_notes(est)] == [60, 64]
    assert [n["pitch"] for n in X.inside_notes(est, 0.05)] == [67, 60, 64]
    row = X.window_row("real", "P1|chords|a", "k", "P1", "chords", truth, {"tx-bp": est, "tx-vote": est[2:]})
    assert row["figures"]["tx-bp"]["precision"] == 0.5                 # the deciding figure is unchanged
    assert row["side"]["inside"]["tx-bp"]["precision"] == 1.0 and row["side"]["inside_lead"]["tx-bp"]["est"] == 3
    rep = X.side_report([row])
    assert rep["real"]["inside"]["tx-bp"]["precision"] == 1.0 and rep["P1|chords"]["inside_lead"]["tx-vote"]["est"] == 2


def _decided_rows():
    """Ten list rows and six real rows (six files, P1 and P2), with decided readings: tx-vote and tx-veto raise precision
    clear of zero, hold recall and F; tx-ms loses recall."""
    def figs(k, bp_est):
        return {"tx-bp": _fig(10, 10, bp_est + k % 3), "tx-vote": _fig(10, 10, 11), "tx-veto": _fig(10, 10, 12),
                "tx-ms": _fig(8, 10, 9), "tx-ms-free": _fig(8, 10, 9)}
    lists = [_row(f"l{k}", figs(k, 16)) for k in range(10)]
    real = [_row(f"P{1 + k % 2}|chords|f{k % 3}", figs(k, 15), "real", f"P{1 + k % 2}", "chords") for k in range(6)]
    for r in lists + real:
        r["borrow"] = {"tx-ms": {"notes": 9, "unpaired": 1}}
    return lists, real


def _side(r, scale):
    """Very different side values: every arm's inside figures replaced by made-up ones."""
    return {k: {a: _fig(10 - scale, 10, 10 + 7 * scale) for a in r["figures"]} for k in X.INSIDE_LEADS}


def test_the_side_figure_never_changes_the_read():
    """PR #577's review: on multi-cluster rows with decided readings, the whole read, less side_inside, is identical
    with and without very different side values."""
    ck = {c: True for c in X.GUARDED_CHECKS}
    goat = [{"checks": {a: {"notes": {"playing-covered": True, "onsets-found": True}, "ring-soft": ck}
                        for a in X.BUILT_ARMS}} for _ in range(27)]
    lists, real = _decided_rows()
    base = X.summarise_read(lists, real, goat)
    v = base["readings"]["tx-vote"]
    assert v["lists"]["precision_raised"] and v["real"]["precision_raised"] and v["real"]["recall_held"]
    assert base["numbers"]["real"]["clusters"] == 6 and base["code"] == "TXR-vote"     # decided readings
    for scale in (0, 3, 9):
        lists2, real2 = _decided_rows()
        for r in lists2 + real2:
            r["side"] = _side(r, scale)
        got = X.summarise_read(lists2, real2, goat)
        assert got["side_inside"] != base["side_inside"]
        assert {k: v for k, v in got.items() if k != "side_inside"} == \
            {k: v for k, v in base.items() if k != "side_inside"}


def test_stage_b_reads_the_truth_report_with_the_users_hum_go(monkeypatch):
    """The truth report stopped on its hum guard; stage b reads it only as the redo does, with main's
    `phase_nr_1_redo_go_hum` naming the file's sha256 (note_transcribe.truth_report_refusal)."""
    seen = []
    monkeypatch.setattr(T, "require_truth", lambda m: {"windows": []})
    monkeypatch.setattr(T, "require_truth_report", lambda nr=None: seen.append(nr) or {"windows": []})
    monkeypatch.setattr(T, "_dev_context", lambda: (None, {"items": {}}, None, None))
    monkeypatch.setattr(T, "dev_windows", lambda z, e, i: [{"item": "item_1"}])
    nr = {T.PHASE_GO_HUM: {"go": True, "truth_report_sha256": "s"}}
    X.stage_b_context({"note-rebuild": nr, "note-transcriber": {}})
    assert seen == [nr]                                          # main's note-rebuild entry, so the go is read
    body = {"stopped": [["w", 0.06]]}
    assert "to the user" in T.truth_report_refusal(body, {}, "s")
    assert T.truth_report_refusal(body, nr, "s") is None and "to the user" in T.truth_report_refusal(body, nr, "t")


def test_a_stop_needs_its_gate_file(monkeypatch, tmp_path):
    monkeypatch.setattr(X, "OUT", tmp_path)
    m = {"note-transcriber": {X.PHASE_INSTALL_LARGE: {"stopped": "no repeat", "gate_sha256": "0" * 64}}}
    with pytest.raises(SystemExit, match="gate-large.json is missing"):
        X.large_stopped(m)
    X.gate_path("large").write_text(json.dumps({"body": {"size": "large", "device": None}}))
    with pytest.raises(SystemExit, match="not the file the stop names"):
        X.large_stopped(m)
    m["note-transcriber"][X.PHASE_INSTALL_LARGE]["gate_sha256"] = T.NR.file_sha(X.gate_path("large"))
    assert X.large_stopped(m)


def test_require_install_refuses_another_size(monkeypatch, tmp_path):
    monkeypatch.setattr(X, "MANIFEST", tmp_path / "manifest.json")
    (tmp_path / "manifest.json").write_text(json.dumps({"lock_sha256": "l", "weights": {"sha256": "w"}}))
    m = {"note-transcriber": {X.PHASE_INSTALL: {"size": "medium"}, X.PHASE_INSTALL_LARGE: {"size": "medium"}}}
    with pytest.raises(SystemExit, match="names size 'medium', not 'large'"):
        X.require_install(m, "large")
    m["note-transcriber"][X.PHASE_INSTALL] = {"size": "small"}
    with pytest.raises(SystemExit, match="names size 'small', not 'medium'"):
        X.require_install(m, "medium")


def test_the_large_install_record_binds_large_weights():
    man = {"lock_sha256": "l", "weights": {"sha256": X.WEIGHTS["medium"]["sha256"]}}
    rec = {"lock_sha256": "l", "weights_sha256": X.WEIGHTS["large"]["sha256"], "gate_sha256": "g",
           "list_notes_listing_sha256": "n"}
    assert X.install_record_refusal(rec, man, "g", "n", X.WEIGHTS["large"]["sha256"]) is None
    assert "another lock or weights" in X.install_record_refusal(rec, man, "g", "n")   # not medium's weights


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
    assert X.gate_rule("medium", X.projection_s(pr, "mps")) == "medium"   # 44 min on 133 runs; speed never decides
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
    for later in (X.PHASE_BRIDGE,) + X.RESERVED_PHASES:
        assert later not in e                                     # each comes with its own PR
    inst = e[X.PHASE_INSTALL]                                     # the hash PR: the shape `require_install` reads
    assert inst["size"] == "medium" and inst["device"] == "mps"
    assert inst["weights_sha256"] == X.WEIGHTS["medium"]["sha256"]
    assert all(re.fullmatch(r"[0-9a-f]{64}", inst[k]) for k in ("lock_sha256", "weights_sha256", "gate_sha256",
                                                                 "list_notes_listing_sha256"))
    assert "labels" not in inst and "frozen" in inst["note"]      # no counts before both sizes are scored
    assert "No list has been scored" in inst["note"] and X.private_keys(inst) == []
    amend = e[X.PHASE_SIZE_AMEND]                                 # declared before large is gated or a list scored
    assert "no switch to small" in amend["gate"].lower()
    big = e[X.PHASE_INSTALL_LARGE]                                # large's hash PR: the shape require_install reads
    assert big["size"] == "large" and big["device"] == "mps" and big["weights_sha256"] == X.WEIGHTS["large"]["sha256"]
    assert big["lock_sha256"] == inst["lock_sha256"] and "stopped" not in big
    assert all(re.fullmatch(r"[0-9a-f]{64}", big[k]) for k in ("lock_sha256", "weights_sha256", "gate_sha256",
                                                                "list_notes_listing_sha256"))
    assert "No list of either size has been scored" in big["note"] and X.private_keys(big) == []
    assert "tx-ms's note F" in amend["pick"] and "slow_ok" in amend["slow"] and X.private_keys(amend) == []
    assert "changes only the weights" in amend["frozen"]
    lists = e[X.PHASE_LISTS]                                      # the screen's result: the shape stage b reads
    assert X.lists_go_refusal(lists) is None and lists["size"] == X.picked_size(lists) == "medium"
    assert re.fullmatch(r"[0-9a-f]{64}", lists["sha256"]) and lists["size_pick"]["label"] == "undecided, medium kept"
    assert lists["size_pick"]["large_open_for_user"] and set(lists["screens"]) == set(X.SCREENED_SIZES)
    bars = e["phase_tx_bars_amend"]                                # T1/T2: the decision agent's calls, not the user's
    assert "not the user's own go" in bars["by"] and "unchanged" in bars["lists_rederived"]
    rd = e[X.PHASE_READ]                                          # the read's result: the shape the bridge reads
    assert re.fullmatch(r"[0-9a-f]{64}", rd["sha256"]) and rd["code"] == "TXR-undecided" and rd["flags"]["veto-holds"]
    assert "no bridge" in X.read_bridge_refusal(rd)               # TXR-undecided has no bridge
    assert "bridge waits" not in json.dumps(rd) and "not measured (1 window, 6 notes)" in rd["note"]
    notes = e[X.PHASE_NOTES]                                      # stage b's hash PR: the shape `read` reads
    assert re.fullmatch(r"[0-9a-f]{64}", notes["listing_sha256"]) and notes["note_files"] == 79 + 2 * 27
    assert notes["size"] == "large" and "item_5" in notes["item_5"] and "12p" in notes["item_5"]
    go_read = e[X.PHASE_GO_READ]                                  # the user's stage-b go and stance
    assert go_read["size"] == "large" and go_read["stance"] == X.USER_STANCE and go_read["date"] == "2026-11-23"
    assert "slow_ok" not in go_read and X.private_keys(go_read) == []
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


NEEDS = {"install": (X.PHASE_GO,), "gate": (X.PHASE_GO,),
         "lists": (X.PHASE_GO, X.PHASE_INSTALL, X.PHASE_SIZE_AMEND, X.PHASE_INSTALL_LARGE),
         "transcribe": (X.PHASE_GO, X.PHASE_INSTALL, X.PHASE_LISTS, X.PHASE_GO_READ),
         "read": (X.PHASE_GO, X.PHASE_INSTALL, X.PHASE_LISTS, X.PHASE_GO_READ, X.PHASE_NOTES),
         "bridge": (X.PHASE_GO, X.PHASE_INSTALL, X.PHASE_LISTS, X.PHASE_GO_READ, X.PHASE_NOTES, X.PHASE_READ)}
NEEDS_NR = {"gate": (T.PHASE_TRUTH,), "transcribe": (T.PHASE_TRUTH,), "read": (T.PHASE_TRUTH, T.PHASE_ITEM5_OUT),
            "bridge": (T.PHASE_TRUTH, T.PHASE_VERSIONS, T.PHASE_ITEM5_OUT)}


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
    with pytest.raises(SystemExit, match=T.PHASE_ITEM5_OUT):      # 12p's order guard: its key on main first
        X.cmd_bridge(None)
    with pytest.raises(SystemExit, match=T.PHASE_ITEM5_OUT):
        X.cmd_read(None)
    nr[T.PHASE_ITEM5_OUT] = {}
    with pytest.raises(SystemExit, match="TXR-none"):
        X.cmd_transcribe(None)
    with pytest.raises(SystemExit, match="no bridge"):
        X.cmd_bridge(None)


@pytest.mark.parametrize("missing", ["phase_tx_size_amend", "phase_tx_install"])
def test_the_large_gate_waits_for_the_amendment_and_medium_bound(monkeypatch, missing):
    tx = {k: {"declared": True} for k in (X.PHASE, X.PHASE_GO, X.PHASE_SIZE_AMEND, X.PHASE_INSTALL) if k != missing}
    monkeypatch.setattr(X, "tx_on_main", lambda: ({"note-transcriber": tx, "note-rebuild": {T.PHASE_TRUTH: {}}}, None))
    with pytest.raises(SystemExit, match=missing):
        X.cmd_gate(argparse.Namespace(size="large"))


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


def test_the_read_and_the_bridge_drop_the_ruled_out_di(monkeypatch, tmp_path):
    """12p, behavioural: stage b's note files keep all 27 windows (DEV_RUNS 54; the checks reported per window since T1); `read` reads
    GOAT's audio first for item_10, never item_5; the bridge builds versions.json's GOAT windows without item_5."""
    pytest.importorskip("numpy")
    assert X.DEV_RUNS == 54 and not hasattr(X, "CHECK_SLACK")    # T1: the slack is retired
    wins = [{"item": f"item_{k}", "start_s": 1.0} for k in [5] + list(range(10, 36))]

    class First(Exception):
        pass

    def first(z, item):
        raise First(item)
    m = {"note-transcriber": {}, "note-rebuild": {}}
    for name, val in (("require_tx", lambda *a, **k: m), ("require_install", lambda *a: {"device": "cpu", "size": "large"}),
                      ("picked_size", lambda *a: "large"), ("notes_listing", lambda *a: ({}, "S")),
                      ("never_overwrite", lambda *a: None), ("lists_path", lambda: tmp_path / "lists.json"),
                      ("stage_b_context", lambda m: ({}, {"windows": [], "goat": {}}, None, list(wins), [])),
                      ("truth_report_refusal", lambda *a: None), ("read_bridge_refusal", lambda rd: None),
                      ("gate_known", lambda: {"a": []}), ("reproduce_refusal", lambda *a: None)):
        monkeypatch.setattr(X, name, val)
    m["note-transcriber"][X.PHASE_NOTES] = {"listing_sha256": "S"}
    m["note-transcriber"][X.PHASE_READ] = {"code": "TXR-vote"}
    m["note-rebuild"][T.PHASE_VERSIONS] = {"sha256": "V", "code": "NV-none"}
    versions = {"windows": [{"set": "goat", "key": "item_5"}, {"set": "goat", "key": "item_14"}]}
    monkeypatch.setattr(T, "require_file_hash", lambda e, ph, p: {"body": versions if ph == T.PHASE_VERSIONS
                                                                  else {"rows": []}})
    for name, val in (("goat_audio", first), ("install_pair", lambda *a: ("L", "M")), ("load_manifest", lambda: {}),
                      ("usable_windows", lambda *a: []), ("TruthAudio", lambda listing: None),
                      ("require_attacks", lambda: {"offset_s": 0.0}), ("versions_loud", lambda m: (None, None)),
                      ("known_audio", lambda nm, bank: [0.0]), ("timed_notes", lambda *a: ([], {})),
                      ("KNOWN_NOTES", {"a": []})):
        monkeypatch.setattr(T, name, val)
    monkeypatch.setattr(X.NR, "Bank", lambda *a, **k: None)
    monkeypatch.setattr(X.NR, "load_notes_doc", lambda: None)
    monkeypatch.setattr(X.NR, "load_exclusion", lambda: {"keys": {}, "sha256": []})   # hermetic: no local data
    monkeypatch.setattr(X.NR, "rebuild_redo", lambda *a, **k: ([0.0], {}))
    monkeypatch.setattr(X.NV, "floored_logmel", lambda *a: 0.0)
    from learn import note_attacks as NA
    from learn import song_bank as SB
    monkeypatch.setattr(NA, "run_attacks", lambda jobs, work: [[] for _ in jobs])
    monkeypatch.setattr(SB, "measure", lambda y: y)
    with pytest.raises(First) as got:
        X.cmd_read(None)
    assert str(got.value) == "item_10"
    with pytest.raises(First) as got:
        X.cmd_bridge(None)
    assert str(got.value) == "item_14"


def test_the_read_takes_the_stage_b_sizes_own_list_rows():
    """PR #582's review: the stored pick kept medium but stage b ran large on the user's go, so the read must take
    large's list rows, not the screen's top-level (medium) rows."""
    med, big = [{"key": "medium-row"}], [{"key": "large-row"}]
    body = {"size": "medium", "rows": med, "sizes": {"medium": {"rows": med}, "large": {"rows": big}}}
    assert X.list_rows_for(body, "large") is big and X.list_rows_for(body, "medium") is med
    assert X.list_rows_for({"size": "medium", "rows": med}, "medium") is med     # a screen before the amendment
    with pytest.raises(SystemExit, match="no rows for large"):
        X.list_rows_for({"rows": med, "sizes": {"medium": {"rows": med}}}, "large")
    go = {"size": "large"}
    body["size_pick"] = {"large_open_for_user": True}
    body["sizes"]["large"]["screen"] = "lists-go"
    assert X.list_rows_for(body, X.picked_size(body, go)) is big                  # what cmd_read does
    p = X.lists_path()
    if p.exists():                                                                # the stored screen, when present
        stored = json.loads(p.read_text())["body"]
        go_read = X.tx_entries(LEDGER.read_text())["note-transcriber"][X.PHASE_GO_READ]
        size = X.picked_size(stored, go_read)
        assert size == "large" and X.list_rows_for(stored, size) == stored["sizes"]["large"]["rows"]
        assert X.list_rows_for(stored, size) != stored["rows"]                    # not medium's rows


def test_the_stored_list_screen_rederives_unchanged_under_t1():
    """T1: the list screen was read under the old bars; re-derived from the stored rows under the new rules (no
    re-run), every reading and the screen are unchanged (skipped without the stored lists.json)."""
    p = X.lists_path()
    if not p.exists():
        pytest.skip("the stored lists.json is not on this machine")
    body = json.loads(p.read_text())["body"]
    for size, v in body["sizes"].items():
        new = X.summarise_screen(v["rows"])
        assert new["screen"] == v["screen"] == "lists-go", size
        for arm, r in new["readings"].items():
            old = v["readings"][arm]
            assert r["ends_better"] == old["ends_better"]
            for k in ("precision_raised", "precision_not_better", "f_not_worse", "recall_held"):
                assert r["lists"][k] == old["lists"][k], (size, arm, k)
