"""The recorded DI-to-amp-track lags: one per set-2 development part, never a held-out
one, each with its evidence, read back by `benchmark_recordings.lag_samples`; and the
measurement's sign convention on synthetic audio."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import benchmark_recordings as B  # noqa: E402
import record_part_lags as R  # noqa: E402


def _slug(session, part):
    return "-".join(x.replace("/", "_").replace(" ", "_")
                    for x in (session["source"], session["song"], part["part"]))


def test_every_set_two_development_part_has_one_lag_and_no_held_out_part_does():
    lags = json.loads(B.LAGS.read_text())
    assert lags["schema"] == "validation-lags-2" and lags["latency_samples"] == 52
    catalog = json.loads(B.CATALOG.read_text())
    entry = {_slug(s, p): (p.get("split") or s.get("split"), s.get("set"), p.get("usable"))
             for s in catalog["sessions"] for p in s["parts"]}
    recorded = set(lags["parts"])
    assert len(recorded) == 43
    assert all(entry[p][0] == "development" and entry[p][1] == 2 and entry[p][2]
               for p in recorded)


def test_ambiguity_follows_the_declared_checks():
    for part, row in json.loads(B.LAGS.read_text())["parts"].items():
        split = len(row["candidates"]) > 1 and row["judge_win_share"] < 2 / 3
        onset = abs(row["onset_lag_samples"] - row["lag_samples"]) / 48 > 1.0
        assert row["onset_disagrees"] == onset, part
        assert row["ambiguous"] == (split or row["subset_spread_ms"] > 0.5 or onset), part
        assert any(c["lag_samples"] == row["lag_samples"] for c in row["candidates"]), part


def test_lag_samples_withholds_ambiguous_lags_unless_asked(tmp_path):
    lags = tmp_path / "lags.json"
    lags.write_text(json.dumps({"parts": {"clear": {"lag_samples": 24, "ambiguous": False},
                                          "unsure": {"lag_samples": 99, "ambiguous": True}}}))
    assert B.lag_samples("clear", lags_path=lags) == 24
    assert B.lag_samples("unsure", lags_path=lags) is None
    assert B.lag_samples("unsure", allow_ambiguous=True, lags_path=lags) == 99
    assert B.lag_samples("absent", lags_path=lags) is None
    with pytest.raises(FileNotFoundError):
        B.lag_samples("clear", lags_path=tmp_path / "missing.json")


def _guitar(np, seconds=6.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * R.SR)) / R.SR
    di = np.zeros_like(t)
    start = 0.2
    while start < seconds - 0.4:
        n = (t >= start) & (t < start + 0.3)
        f0 = rng.choice([110.0, 147.0, 196.0, 247.0])
        di[n] = 0.3 * sum(np.sin(2 * np.pi * f0 * k * (t[n] - start)) / k for k in range(1, 9)) \
            * np.exp(-(t[n] - start) * 6)
        start += 0.3 + rng.uniform(0.05, 0.2)
    return di


def _delay(np, x, n):
    return np.concatenate([np.zeros(n), x])[: len(x)] if n >= 0 else np.concatenate(
        [x[-n:], np.zeros(-n)])


def test_the_lag_reads_recording_after_di_for_both_estimators():
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    pytest.importorskip("scipy.signal", reason="needs the analysis extra")
    di = _guitar(np)
    render = _delay(np, np.tanh(4 * di), R.LATENCY)           # a render lags its DI by 52
    recording = _delay(np, np.tanh(6 * di), 960)              # the amp track by 960
    lags, total = R.correlation(recording, [render], 960 - R.LATENCY, 720)
    assert R.candidates(lags, total)[0][0] + R.LATENCY == pytest.approx(960, abs=24)
    assert R.onset_lag(di, recording, 960, 720) == pytest.approx(960, abs=48)


def test_the_script_refuses_a_panel_with_held_out_material(tmp_path, monkeypatch):
    catalog = json.loads(B.CATALOG.read_text())
    held = next(_slug(s, p) for s in catalog["sessions"] for p in s["parts"]
                if (p.get("split") or s.get("split")) == "held_out")
    panel = tmp_path / "panel"
    panel.mkdir()
    (panel / "index.json").write_text(json.dumps(
        {"rows": [{"part": held, "candidate": "x", "file": str(tmp_path / "never-read.wav")}]}))
    import analysis

    monkeypatch.setattr(analysis, "require", lambda *_: None)
    monkeypatch.setattr(sys, "argv", ["lags", "--panel-dir", str(panel),
                                      "--json", str(tmp_path / "out.json")])
    with pytest.raises(SystemExit):
        R.main()
    assert not (tmp_path / "out.json").exists()
