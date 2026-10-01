"""The dataset pairing measures and the split draw behave as declared."""

from __future__ import annotations

import pathlib
import sys

import pytest

np = pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")
sf = pytest.importorskip("soundfile", reason="needs the analysis extra")

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validation_datasets as V  # noqa: E402

RATE = 48000


def _bursts(seconds, seed, jitter=None):
    """Notes with a varying envelope; `jitter` offsets each note by samples."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(seconds * RATE))
    for index, start in enumerate(range(0, len(out) - RATE, RATE // 2)):
        shift = 0 if jitter is None else int(jitter[index % len(jitter)])
        at = max(0, start + shift)
        length = int(0.3 * RATE)
        decay = np.exp(-np.arange(length) / (0.08 * RATE))
        out[at:at + length] += rng.uniform(0.2, 1.0) * decay * rng.standard_normal(length)
    return out


def _write(tmp_path, name, samples):
    path = tmp_path / name
    sf.write(str(path), samples.astype(np.float32), RATE)
    return path


def test_the_draw_is_the_declared_one():
    assert V.draw_split() == {"telefunken": "57 Chevy",
                              "cambridge": "That's How I Got To Memphis",
                              "guitar_techs": ["02", "06", "10", "11"]}


def test_a_take_and_its_delayed_copy_pair_with_the_right_sign(tmp_path):
    di = _bursts(60, seed=1)
    amp = np.concatenate([np.zeros(int(0.01 * RATE)), np.tanh(3 * di)])[:len(di)]
    corr, lag = V.pairing(_write(tmp_path, "amp.wav", amp), _write(tmp_path, "di.wav", di))
    assert corr > 0.9 and lag == 10, "the amp track 10 ms later reads +10"
    window = V.windowed_pairing(tmp_path / "amp.wav", tmp_path / "di.wav")
    assert window["in_step_fraction"] == 1.0 and window["median_correlation"] > 0.9


def test_a_take_that_drifts_mid_song_is_not_in_step(tmp_path):
    di = _bursts(80, seed=2)
    # The middle 40 s of the amp track come from the same notes played 80 ms late.
    amp = np.tanh(3 * di)
    late = np.concatenate([np.zeros(int(0.08 * RATE)), amp])[:len(amp)]
    amp[20 * RATE:60 * RATE] = late[20 * RATE:60 * RATE]
    V_amp, V_di = _write(tmp_path, "amp.wav", amp), _write(tmp_path, "di.wav", di)
    window = V.windowed_pairing(V_amp, V_di)
    assert window["in_step_fraction"] < V.IN_STEP_FRACTION


def test_a_rebuild_keeps_the_held_out_ledger(tmp_path, monkeypatch):
    """The ledger records declared uses; re-measuring the audio must not erase it."""
    import json

    out = tmp_path / "catalog.json"
    ledger = [{"test_id": "t", "declaration": "docs/x.md"}]
    out.write_text(json.dumps({"sessions": [], "held_out_uses": ledger}))
    monkeypatch.setattr(V, "build", lambda root: {"sessions": [], "held_out_uses": []})
    monkeypatch.setattr(sys, "argv", ["validation_datasets.py", "--root", str(tmp_path),
                                      "--json", str(out)])
    V.main()
    assert json.loads(out.read_text())["held_out_uses"] == ledger


def test_a_parts_reference_is_its_first_amp_track_by_the_declared_preference():
    ordered = ["GTR M80_01.wav", "12_ElecGtr1Mic1.wav", "14_ElecGtr1Close.wav",
               "ElecGtr03Amp1.wav", "ElecGtr08Amp.wav", "26_ElecGtr2.wav",
               "GTR TF11_01.wav", "13_ElecGtr1Mic2.wav", "15_ElecGtrFar.wav",
               "ElecGtr03Amp2.wav"]
    assert sorted(reversed(ordered), key=V.amp_rank) == ordered
    # A take number after an underscore still counts; a longer number does not.
    assert V.amp_rank("Guitar Amp 1_18.wav") < V.amp_rank("Guitar Amp 2_18.wav")
    assert V.amp_rank("ElecGtr1Mic12.wav") == len(V.AMP_PREFERENCE)


def test_the_second_split_holds_out_whole_bands_reproducibly():
    groups = {"cambridge": {f"band {i}" for i in range(13)},
              "telefunken": {f"act {i}" for i in range(9)}}
    first, again = V.draw_set2_split(groups), V.draw_set2_split(groups)
    assert first == again
    assert len(first["cambridge"]) == 5 and len(first["telefunken"]) == 3
    assert set(first["cambridge"]) <= groups["cambridge"]


def test_a_second_set_session_mixes_each_guitar_once_and_lists_its_vocals(tmp_path):
    session = tmp_path / "cambridge" / "Band_Song_Full"
    session.mkdir(parents=True)
    di = _bursts(45, seed=4)
    amp = np.tanh(3 * di)
    for name, samples in {"01_Kick.wav": _bursts(45, seed=5), "05_ElecGtr1Mic1.wav": amp,
                          "06_ElecGtr1Mic2.wav": 0.7 * amp, "07_ElecGtr1DI.wav": di,
                          "08_ElecGtr1AmpSim.wav": amp, "09_LeadVox.wav": _bursts(45, seed=6),
                          "10_RR Master_01.wav": amp + di, "11_ElecGtr2DI.wav": di,
                          "12_Click.wav": di, "13_AcousticGtr TDP-1.wav": di,
                          "14_Gtr Helix.wav": amp, "15_BassDI.wav": di}.items():
        _write(session, name, samples)
    entry = {"source": "cambridge", "song": "Song", "artist": "Band", "group": "Band",
             "path": "cambridge/Band_Song_Full", "url": "https://example.test/x.zip",
             "archive_sha256": "0" * 64,
             "parts": [{"part": "ElecGtr1", "di": "07_ElecGtr1DI.wav",
                        "amps": ["06_ElecGtr1Mic2.wav", "05_ElecGtr1Mic1.wav"]}]}
    made = V.set2_session(tmp_path, entry, {"cambridge": ["Band"], "telefunken": []})

    part, = made["parts"]
    assert part["reference"] == "05_ElecGtr1Mic1.wav"
    assert part["alternate"] == ["06_ElecGtr1Mic2.wav"] and part["usable"]
    assert made["mix_tracks"] == ["01_Kick.wav", "05_ElecGtr1Mic1.wav", "09_LeadVox.wav",
                                  "13_AcousticGtr TDP-1.wav", "15_BassDI.wav"]
    assert made["vocal_tracks"] == ["09_LeadVox.wav"]
    assert made["split"] == "held_out" and made["set"] == 2
    assert set(made["files"]) == {p.name for p in session.glob("*.wav")}


def test_a_parts_reference_skips_a_preferred_amp_track_that_is_out_of_step(tmp_path):
    session = tmp_path / "telefunken" / "Act - Song"
    session.mkdir(parents=True)
    di = _bursts(45, seed=7)
    amp = np.tanh(3 * di)
    late = np.roll(amp, RATE // 4)      # a quarter second out, between notes
    for name, samples in {"GTR DI.wav": di, "GTR Amp_M80.wav": late,
                          "GTR Amp_TF11.wav": amp}.items():
        _write(session, name, samples)
    entry = {"source": "telefunken", "song": "Song", "artist": "Act", "group": "Act",
             "path": "telefunken/Act - Song", "url": "https://example.test/y.zip",
             "archive_sha256": "0" * 64,
             "parts": [{"part": "GTR", "di": "GTR DI.wav",
                        "amps": ["GTR Amp_M80.wav", "GTR Amp_TF11.wav"]}]}
    part, = V.set2_session(tmp_path, entry, {"cambridge": [], "telefunken": []})["parts"]
    assert part["reference"] == "GTR Amp_TF11.wav" and part["usable"]
    assert part["alternate"] == ["GTR Amp_M80.wav"]

    _write(session, "GTR Amp_TF11.wav", late)
    part, = V.set2_session(tmp_path, entry, {"cambridge": [], "telefunken": []})["parts"]
    assert part["reference"] == "GTR Amp_M80.wav" and not part["usable"]
