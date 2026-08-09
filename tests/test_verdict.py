"""The lightweight listening logger: one verdict, one exact measured render."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from match.store import Run, Store, StoreError, Trial
from match.verdict import VerdictError, record_verdict
from packs.paths import set_data_root

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHA = "a" * 64


@pytest.fixture(autouse=True)
def clear_data_root():
    yield
    set_data_root(None)


def _summary(trial_id=1):
    candidate = {
        "rank": 1,
        "trial_id": trial_id,
        "score": 0.4,
        "worst_input_level_score": 0.6,
        "objectives": {"total": 0.4, "timbre": 0.3},
        "input_level_scores": {"0.0": 0.4},
        "changes": [{"path": "amp/gain", "from": 5.0, "to": 7.0,
                     "heard": True}],
        "fingerprint_delta": [
            {"centre_hz": 100.0, "target_db": 0.0,
             "candidate_db": 1.0, "delta_db": -1.0},
            {"centre_hz": 200.0, "target_db": 0.0,
             "candidate_db": -1.0, "delta_db": 1.0},
        ],
    }
    return {
        "schema": "tone-match-summary-v1",
        "run_id": "run-one",
        "pack": "morgan",
        "reference": {
            "path": "/private/reference.wav",
            "regime": "separated_stem",
            "regime_confidence": 0.55,
            "fingerprint": {
                "source": {"sha256": SHA},
                "spectrum": {"band_centres_hz": [100.0, 200.0],
                             "band_db": [0.0, 0.0]},
            },
        },
        "loss_profile": "unpaired-v1",
        "renderer": {
            "renderer_id": "swift", "plugin_version": "1.1.1",
            "renderer_build": "build-1", "reproducible": False,
            "band_noise_db": 0.23,
        },
        "starting_point": {"score": 0.9, "objectives": {"total": 0.9}},
        "shortlist": [candidate],
    }


def _run(directory: pathlib.Path, *, duplicate=False):
    directory.mkdir()
    store = Store(str(directory / "trials.sqlite3"))
    store.start_run(Run(
        run_id="run-one", pack="morgan", reference_sha=SHA,
        regime="separated_stem", loss_profile="unpaired-v1",
        renderer_id="swift", plugin_version="1.1.1",
        notes=json.dumps({
            "schema": "tone-match-run-notes-v1", "probe_note": None,
            "renderer": _summary()["renderer"],
        }),
    ))
    trial = store.add_trial(
        "run-one", Trial(
            params={"selectedAmp": "PR12", "amp/gain": 7.0},
            objectives={"total": 0.4, "timbre": 0.3},
            fingerprint={"spectrum": {
                "band_centres_hz": [100.0, 200.0], "band_db": [1.0, -1.0],
            }},
        ))
    if duplicate:
        store.add_trial(
            "run-one", Trial(
                params={"selectedAmp": "PR12", "amp/gain": 7.0},
                objectives={"total": 0.4, "timbre": 0.3},
                fingerprint={"spectrum": {
                    "band_centres_hz": [100.0, 200.0], "band_db": [1.0, -1.0],
                }},
            ))
    store.close()
    (directory / "summary.json").write_text(
        json.dumps(_summary(trial.trial_id)), encoding="utf-8")
    (directory / "match-1.json").write_text(json.dumps({
        "name": "candidate",
        "parameters": [
            {"module": "", "key": "selectedAmp", "value": "PR12"},
            {"module": "amp", "key": "gain", "value": 7.0},
            # Specs include dormant controls the renderer never received. A trial's
            # settings are therefore a strict subset, not an equal dictionary.
            {"module": "delay", "key": "sync", "value": False},
        ],
    }), encoding="utf-8")
    return trial


def _cli_argv(run_dir: pathlib.Path, data_dir: pathlib.Path, listener="first-session"):
    return [
        sys.executable, str(ROOT / "scripts" / "log_match_verdict.py"),
        "--run-dir", str(run_dir), "--candidate", "1", "--choice", "candidate",
        "--listener", listener, "--comment", "#2 was less harsh <script>",
        "--data-dir", str(data_dir),
    ]


def _cli(run_dir: pathlib.Path, data_dir: pathlib.Path):
    return subprocess.run(_cli_argv(run_dir, data_dir), cwd=ROOT,
                          capture_output=True, text=True)


def test_cli_records_the_database_row_and_measured_learned_note(tmp_path):
    run_dir, data_dir = tmp_path / "run", tmp_path / "data"
    trial = _run(run_dir)

    done = _cli(run_dir, data_dir)
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"trial {trial.trial_id}" in done.stdout

    with Store(str(run_dir / "trials.sqlite3")) as store:
        verdict, = store.verdicts("run-one")
    assert verdict["listener"] == "first-session"
    assert verdict["choice"] == "candidate"

    note = (data_dir / "packs" / "morgan" / "learned-tones.md").read_text()
    for required in (SHA, "separated_stem", "0.55", "swift", "1.1.1",
                     "unpaired-v1", "starting_score", "Fingerprint delta",
                     "Parameter changes", "#2 was less harsh"):
        assert required in note, required
    assert "reproducible=false" in note
    assert "/private/reference.wav" not in note, "do not leak the user's audio path"
    assert "<script>" not in note, "comments must not become rendered HTML"


def test_repeating_a_listener_verdict_refuses_instead_of_duplicating(tmp_path):
    run_dir, data_dir = tmp_path / "run", tmp_path / "data"
    _run(run_dir)
    assert _cli(run_dir, data_dir).returncode == 0

    repeated = _cli(run_dir, data_dir)
    assert repeated.returncode == 2
    assert "already recorded" in repeated.stderr
    note = (data_dir / "packs" / "morgan" / "learned-tones.md").read_text()
    assert note.count("### ") == 1
    with Store(str(run_dir / "trials.sqlite3")) as store:
        assert len(store.verdicts("run-one")) == 1


def test_a_legacy_summary_resolves_only_a_unique_matching_trial(tmp_path):
    run_dir = tmp_path / "run"
    trial = _run(run_dir)
    summary = _summary()
    del summary["shortlist"][0]["trial_id"]
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    set_data_root(tmp_path / "data")

    recorded = record_verdict(run_dir, candidate_rank=1, choice="template",
                              listener="legacy")
    assert recorded.trial_id == trial.trial_id


def test_a_legacy_summary_refuses_an_ambiguous_trial(tmp_path):
    run_dir = tmp_path / "run"
    _run(run_dir, duplicate=True)
    summary = _summary()
    del summary["shortlist"][0]["trial_id"]
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    set_data_root(tmp_path / "data")

    with pytest.raises(VerdictError, match="matched 2"):
        record_verdict(run_dir, candidate_rank=1, choice="candidate", listener="x")


def test_a_failed_note_replacement_is_recovered_idempotently(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    _run(run_dir)
    set_data_root(tmp_path / "data")

    original = os.replace

    def refused(source, destination):
        if pathlib.Path(destination).name == "learned-tones.md":
            raise PermissionError("read-only notes")
        return original(source, destination)

    monkeypatch.setattr("match.verdict.os.replace", refused)
    with pytest.raises(PermissionError, match="read-only notes"):
        record_verdict(run_dir, candidate_rank=1, choice="candidate", listener="x")

    with Store(str(run_dir / "trials.sqlite3")) as store:
        assert len(store.verdicts("run-one")) == 1, "the durable intent follows the DB"
    assert not (tmp_path / "data" / "packs" / "morgan" /
                "learned-tones.md").exists()
    assert list(run_dir.glob(".verdict-intent-*.json"))

    monkeypatch.setattr("match.verdict.os.replace", original)
    record_verdict(run_dir, candidate_rank=1, choice="candidate", listener="x")
    note = (tmp_path / "data" / "packs" / "morgan" /
            "learned-tones.md").read_text()
    assert note.count("### ") == 1
    assert not list(run_dir.glob(".verdict-intent-*.json"))


def test_a_process_crash_after_database_commit_recovers_on_exact_retry(tmp_path):
    run_dir, data_dir = tmp_path / "run", tmp_path / "data"
    _run(run_dir)
    code = f"""
import os
from match.store import Store
from match.verdict import record_verdict
from packs.paths import set_data_root

original = Store.add_verdict
def commit_then_crash(self, *args, **kwargs):
    original(self, *args, **kwargs)
    os._exit(91)
Store.add_verdict = commit_then_crash
set_data_root({str(data_dir)!r})
record_verdict({str(run_dir)!r}, candidate_rank=1, choice='candidate',
               listener='first-session', comment='#2 was less harsh <script>')
"""
    crashed = subprocess.run([sys.executable, "-c", code], cwd=ROOT)
    assert crashed.returncode == 91
    with Store(str(run_dir / "trials.sqlite3")) as store:
        assert len(store.verdicts("run-one")) == 1
    assert list(run_dir.glob(".verdict-intent-*.json"))

    recovered = _cli(run_dir, data_dir)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    note = (data_dir / "packs" / "morgan" / "learned-tones.md").read_text()
    assert note.count("### ") == 1
    assert not list(run_dir.glob(".verdict-intent-*.json"))


def test_two_run_databases_cannot_overwrite_each_others_note(tmp_path):
    data_dir = tmp_path / "data"
    first, second = tmp_path / "run-one", tmp_path / "run-two"
    _run(first)
    _run(second)

    one = subprocess.Popen(_cli_argv(first, data_dir, "session-one"), cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    two = subprocess.Popen(_cli_argv(second, data_dir, "session-two"), cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    one_out, one_err = one.communicate(timeout=10)
    two_out, two_err = two.communicate(timeout=10)
    assert one.returncode == 0, one_out + one_err
    assert two.returncode == 0, two_out + two_err
    note = (data_dir / "packs" / "morgan" / "learned-tones.md").read_text()
    assert note.count("### ") == 2
    assert "session-one" in note and "session-two" in note


def test_summary_renderer_metadata_must_match_the_run_header(tmp_path):
    run_dir = tmp_path / "run"
    _run(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text())
    summary["renderer"]["plugin_version"] = "invented"
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    set_data_root(tmp_path / "data")

    with pytest.raises(VerdictError, match="different reference, pack, regime"):
        record_verdict(run_dir, candidate_rank=1, choice="candidate", listener="x")


def test_a_legacy_nonreproducible_delta_must_still_be_internally_consistent(tmp_path):
    run_dir = tmp_path / "run"
    _run(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text())
    summary["shortlist"][0]["fingerprint_delta"][0]["delta_db"] = 999.0
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    set_data_root(tmp_path / "data")

    with pytest.raises(VerdictError, match="does not match its score and spec"):
        record_verdict(run_dir, candidate_rank=1, choice="candidate", listener="x")


def test_the_store_refuses_empty_and_duplicate_verdict_identity():
    with Store() as store:
        store.start_run(Run(run_id="r"))
        trial = store.add_trial("r", Trial(params={"a/b": 1},
                                            objectives={"total": 0.5}))
        with pytest.raises(StoreError, match="listener"):
            store.add_verdict(trial.trial_id, " ", "candidate")
        store.add_verdict(trial.trial_id, "session", "candidate")
        with pytest.raises(StoreError, match="already recorded"):
            store.add_verdict(trial.trial_id, "session", "template")
