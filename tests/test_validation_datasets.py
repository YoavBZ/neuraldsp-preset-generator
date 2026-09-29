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
