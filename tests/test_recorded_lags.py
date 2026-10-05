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
sys.path.insert(0, str(ROOT / "research"))

import benchmark_recordings as B  # noqa: E402
import record_part_lags as R  # noqa: E402


def _slug(session, part):
    return "-".join(x.replace("/", "_").replace(" ", "_")
                    for x in (session["source"], session["song"], part["part"]))


def test_every_set_two_development_part_has_one_lag_and_no_held_out_part_does():
    lags = json.loads(B.LAGS.read_text())
    assert lags["schema"] == "validation-lags-3" and lags["latency_samples"] == 52
    catalog = json.loads(B.CATALOG.read_text())
    entry = {_slug(s, p): (p.get("split") or s.get("split"), s.get("set"), p.get("usable"))
             for s in catalog["sessions"] for p in s["parts"]}
    recorded = set(lags["parts"])
    assert len(recorded) == 43
    assert all(entry[p][0] == "development" and entry[p][1] == 2 and entry[p][2]
               for p in recorded)


def test_ambiguity_follows_the_declared_checks():
    lags = json.loads(B.LAGS.read_text())
    assert lags["schema"] == "validation-lags-3"
    for part, row in lags["parts"].items():
        expected = R.classify([c["lag_samples"] for c in row["candidates"]],
                              row["lag_samples"], row["judge_win_share"],
                              row["onset_lag_samples"], row["onset_runner_up"],
                              [s["lag"] for s in row["subsets"]], row["search_refused"])
        assert {k: row[k] for k in expected} == expected, part
        assert any(c["lag_samples"] == row["lag_samples"] for c in row["candidates"]), part


@pytest.mark.parametrize("evidence, ambiguous", [
    (([500], 500, 1.0, 644, 0.95, [500] * 5), False),   # one peak; an unclear onset: no check
    (([500], 500, 1.0, 644, 0.5, [500] * 5), True),     # one peak; a clear onset 3 ms away
    (([500], 500, 1.0, 543, 0.5, [500] * 5), False),    # ...0.9 ms away is within tolerance
    (([500], 500, 1.0, 500, 0.5, [500, 530]), True),    # a subset 0.6 ms from the choice
    (([500, 600], 500, 1.0, 500, 0.5, [500] * 5), False),  # judge and a clear onset agree
    (([500, 600], 500, 1.0, 500, 0.95, [500] * 5), True),  # the onset does not confirm
    (([500, 600], 500, 0.6, 500, 0.5, [500] * 5), True),   # the judge's wins are split
    # The onset between two candidates 49 samples apart, within 1 ms of both but
    # nearer the one not chosen: no confirmation.
    (([72, 23], 72, 1.0, 40, 0.3, [72] * 5), True),
    (([72, 23], 72, 1.0, 60, 0.3, [72] * 5), False),
])
def test_a_choice_among_aliases_needs_a_clear_onset_nearest_it(evidence, ambiguous):
    assert R.classify(*evidence)["ambiguous"] is ambiguous
    assert R.classify(*evidence, refused=True)["ambiguous"] is True


def test_close_peaks_are_both_candidates():
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    lags = np.arange(-100, 101)
    total = np.exp(-((lags + 37) / 6.0) ** 2) + 0.966 * np.exp(-((lags - 37) / 6.0) ** 2)
    found = R.candidates(lags, total)
    assert [lag for lag, _ in found] == [-37, 37]
    assert found[1][1] == pytest.approx(0.966, abs=0.01)
    shoulder = np.exp(-(lags / 20.0) ** 2)                 # one broad peak: one candidate
    assert [lag for lag, _ in R.candidates(lags, shoulder)] == [0]


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
    # Searched around zero, so a flipped sign would read -960, not +960.
    lags, total = R.correlation(recording, [render], 0, 2400)
    assert R.candidates(lags, total)[0][0] + R.LATENCY == pytest.approx(960, abs=24)
    onset, runner_up = R.onset_lag(di, recording, 0, 2400)
    assert onset == pytest.approx(960, abs=24) and runner_up < R.ONSET_CLEAR


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
