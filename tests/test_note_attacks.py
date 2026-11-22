"""The redo's attack detector (`learn/note_attacks.py`, `learn/attack_run.py`; note-rebuild-plan 12m): the share, the
flag, the offset, the ringing rule, the detector's recall and its floor. Pure: runs on the light CI runner (no numpy);
librosa is never imported here."""
import ast
import pathlib

import pytest

from learn import attack_run as AR
from learn import note_attacks as NA

REPO = pathlib.Path(__file__).resolve().parents[1]


def _n(on, off, pitch=60):
    return {"on": on, "off": off, "pitch": pitch}


def test_the_declared_settings():
    assert (NA.ATTACK_HOP, NA.ATTACK_DELTA, NA.FOUND_S, NA.FLAG_UNDER, NA.RINGING_S, NA.RECALL_FLOOR) == \
        (256, 0.07, 0.050, 0.90, 0.100, 0.90)


def test_onsets_found_share_flag_and_offset():
    onsets = [1.0, 2.0, 3.0, 4.0]
    att = [x + 0.011 for x in onsets]                              # the detector 11 ms late
    assert NA.onsets_found(att, onsets, offset=-0.011)["share"] == 1.0
    got = NA.onsets_found(att + [5.5], onsets, offset=-0.011)      # one false attack in five
    assert got["share"] == 0.8 and got["flag"]
    assert NA.onsets_found(att, onsets[:3], offset=-0.011)["found"] == 3
    assert NA.onsets_found([], onsets) == {"attacks": 0, "found": 0, "share": None, "flag": False, "offset_s": 0.0}
    assert NA.onsets_found([1.06], [1.0])["found"] == 0            # beyond 50 ms


def test_the_offset_is_the_median_over_found_attacks():
    rows = [([1.010, 2.012, 3.30], [1.0, 2.0, 3.0]), ([0.508], [0.5, 0.52])]
    assert NA.detector_offset(rows) == pytest.approx(-0.010)        # the 3.30 attack is not near a true onset
    assert NA.detector_offset([]) == 0.0


def test_the_ringing_rule():
    notes = [_n(0.0, 2.0), _n(0.5, 0.6, 62), _n(1.95, 3.0, 64)]
    assert NA.ringing(0.5, notes)                                 # note 0 has sounded 0.5 s and goes on 1.5 s
    assert not NA.ringing(1.95, notes)                            # note 0 ends 50 ms later
    assert not NA.ringing(0.05, notes)                            # nothing has sounded 100 ms yet


def test_detector_recall_overall_and_ringing():
    notes = [_n(0.0, 3.0), _n(0.5, 1.0, 62), _n(1.0, 1.5, 64), _n(1.02, 1.5, 67), _n(2.0, 2.5, 65)]
    att = [0.0, 0.5, 2.0]                                          # the chord at 1.0 missed, a ringing onset
    got = NA.detector_recall(att, notes)
    assert got["groups"] == 4 and got["found"] == 3 and got["recall"] == 0.75
    assert got["ringing"] == 3 and got["ringing_found"] == 2
    pooled = NA.pooled_recall([got, NA.detector_recall([0.0, 0.5, 1.0, 2.0], notes)])
    assert pooled["recall"] == pytest.approx(7 / 8) and not pooled["holds_floor"]
    assert NA.pooled_recall([NA.detector_recall([0.0, 0.5, 1.0, 2.0], notes)])["holds_floor"]


def test_truth_passes():
    assert NA.truth_passes([1.0, 2.0], [1.0, 2.0])
    assert not NA.truth_passes([1.0, 2.0, 2.5], [1.0, 2.0])
    assert NA.onset_groups([1.0, 1.02, 1.06, 2.0]) == [1.0, 1.06, 2.0]


def test_attack_run_is_stdlib_and_39():
    src = (REPO / "learn" / "attack_run.py").read_text()
    ast.parse(src, feature_version=(3, 9))
    top = src.split("def main(")[0]
    assert "librosa" not in "".join(ln for ln in top.splitlines() if ln.startswith(("import", "from")))
    hop, delta, pairs = AR.parse_args(["--hop", "256", "--delta", "0.07", "a.wav", "a.json"])
    assert (hop, delta, pairs) == (256, 0.07, [("a.wav", "a.json")])
    for bad in (["--hop", "256", "a.wav", "a.json"], ["--hop", "256", "--delta", "0.07", "a.wav"]):
        with pytest.raises(SystemExit):
            AR.parse_args(bad)


def test_plays_filter_drops_attacks_in_silence():
    np = pytest.importorskip("numpy")
    sr = 48000
    di = np.zeros(3 * sr)
    di[sr:2 * sr] = 0.3 * np.sin(2 * np.pi * 220 * np.arange(sr) / sr)
    assert NA.plays_filter([0.5, 1.5, 2.5], di) == [1.5]
