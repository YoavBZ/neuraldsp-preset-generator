"""Private audits bind archived verdicts to keys without reading raw audio."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("soundfile")
pytest.importorskip("scipy")
pytest.importorskip("pyloudnorm")

from analysis.listening import attach_verdict, score_record, sha256
from scripts._listening_trials import consistency, plan_trials
from tests import fixtures_audio as fx

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIT = ROOT / "research" / "audit_frozen_listening.py"


def _scored(tmp_path, *, comparison_id="first", target_id="song", v2=True,
            v3=False):
    time = np.arange(48000) / 48000
    paths = []
    for index, frequency in enumerate((220, 220, 440)):
        path = fx.write_wav(tmp_path / f"{comparison_id}-{index}.wav",
                            .1 * np.sin(2 * np.pi * frequency * time))
        paths.append({"path": str(path), "sha256": sha256(path)})
    return score_record({
        "id": comparison_id, "target_id": target_id,
        "reference": {**paths[0], "regime": "probe"},
        "alternatives": {"A": paths[1], "B": paths[2]},
    }, include_match_v2=v2, include_match_v3=v3)


def _blind_verdict(tmp_path, scored, *, listener="listener", key_name="audition.flac.key.json"):
    audio = tmp_path / "audition.flac"
    audio.write_bytes(b"private-audition")
    output = {"path": str(audio), "sha256": sha256(audio)}
    key = {"schema": "rab-audition-v1", "output": output,
           "blind_key": {"A": "first", "B": "second"},
           "objective_profiles_frozen": scored.get("objective_profiles_frozen"),
           "objective_record": scored}
    key_path = tmp_path / key_name
    key_path.write_text(json.dumps(key))
    identity = hashlib.sha256(listener.encode()).hexdigest()
    verdict = attach_verdict({**scored, "id": f"{scored['id']}-{identity[:12]}",
                              "listener": listener, "heard_audio": output},
                             {"closer": "A", "preferred": None})
    verdict["audition_key"] = {"path": str(key_path), "sha256": sha256(key_path)}
    verdict_path = tmp_path / f"{key_path.name}.{identity}.objective-verdict.json"
    verdict_path.write_text(json.dumps(verdict))
    return verdict_path, key_path


def _backed_verdict(tmp_path, scored, *, name="backed"):
    output_sha = "a" * 64
    key = {"schema": "prospective-backed-audition-v1", "purpose": "prospective",
           "objective_profiles_frozen": scored.get("objective_profiles_frozen"),
           "objective_record": scored,
           "output": {"path": str(tmp_path / "audition.flac"), "sha256": output_sha}}
    key_path = tmp_path / f"{name}-key.json"
    key_path.write_text(json.dumps(key))
    verdict = {"closer": "A", "preferred": None}
    wrapped = {"schema": "prospective-backed-verdict-v1",
               "audition_key": {"path": str(key_path), "sha256": sha256(key_path)},
               "heard_audio_sha256": output_sha, "verdict": verdict,
               "frozen_scored_record": attach_verdict(scored, verdict)}
    verdict_path = tmp_path / f"{name}-verdict.json"
    verdict_path.write_text(json.dumps(wrapped))
    return verdict_path, key_path


def _run(*records, out_dir):
    command = [sys.executable, str(AUDIT)]
    for record in records:
        command.extend(("--record", str(record)))
    command.extend(("--out-dir", str(out_dir)))
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def test_audit_counts_targets_not_repeats_and_keeps_v1_only_unscored(tmp_path):
    first = _scored(tmp_path, comparison_id="blind")
    repeat = _scored(tmp_path, comparison_id="backed")
    historical = _scored(tmp_path, comparison_id="historical", target_id="other", v2=False)
    blind_path, _ = _blind_verdict(tmp_path, first, key_name="custom-private-key.json")
    backed_path, _ = _backed_verdict(tmp_path, repeat)
    old_path, _ = _backed_verdict(tmp_path, historical, name="old")
    for source in tmp_path.glob("*.wav"):
        source.unlink()

    out_dir = tmp_path / "private-audit"
    completed = _run(blind_path, backed_path, old_path, out_dir=out_dir)
    assert completed.returncode == 0, completed.stderr
    report = json.loads((out_dir / "report.json").read_text())
    assert report["schema"] == "frozen-listening-audit-v1"
    assert report["comparison_count_not_independent_n"] == 3
    assert {source["kind"] for source in report["inputs"]} == {"blind", "backed"}
    assert all("path" not in source for source in report["inputs"])
    assert report["v2"]["summary"]["closer"]["target_groups_with_decisive_verdicts"] == 1
    assert "preferred" not in report["v2"]["summary"]
    assert all("preferred" not in group for group in report["v2"]["target_groups"].values())
    assert len(report["v2"]["target_groups"]["song"]["comparisons"]) == 2
    assert report["v2"]["target_groups"]["other"]["closer"][
        "diagnostic_counts_not_independent_n"] == {"unscored": 1}
    assert report["v3"]["summary"]["closer"]["target_groups_with_decisive_verdicts"] == 0
    assert "preferred" not in completed.stdout
    assert "private-audition" not in completed.stdout


def test_audit_shows_v3_only_for_newly_frozen_records(tmp_path):
    current = _scored(tmp_path, comparison_id="current", v3=True)
    old = _scored(tmp_path, comparison_id="old")
    current_path, _ = _backed_verdict(tmp_path, current, name="current")
    old_path, _ = _backed_verdict(tmp_path, old, name="old")
    out = tmp_path / "v3-audit"
    completed = _run(current_path, old_path, out_dir=out)
    assert completed.returncode == 0, completed.stderr
    report = json.loads((out / "report.json").read_text())
    assert report["v2"]["summary"]["closer"]["target_groups_with_decisive_verdicts"] == 1
    assert report["v3"]["summary"]["closer"]["target_groups_with_decisive_verdicts"] == 1
    assert report["v3"]["target_groups"]["song"]["closer"][
        "diagnostic_counts_not_independent_n"]["unscored"] == 1
    assert "preferred" not in report["v3"]["summary"]


def test_audit_refuses_changed_v3_objective_in_bound_verdict(tmp_path):
    scored = _scored(tmp_path, v3=True)
    path, _ = _backed_verdict(tmp_path, scored)
    wrapped = json.loads(path.read_text())
    wrapped["frozen_scored_record"]["objective_scoring"]["match_v3"]["prediction"] = "B"
    path.write_text(json.dumps(wrapped))
    out = tmp_path / "tampered-v3"
    completed = _run(path, out_dir=out)
    assert completed.returncode != 0
    assert not out.exists()


@pytest.mark.parametrize("kind", ("blind", "backed"))
def test_audit_recomputes_hidden_consistency_and_refuses_changed_answers(tmp_path, kind):
    scored = _scored(tmp_path)
    if kind == "blind":
        path, key_path = _blind_verdict(tmp_path, scored)
    else:
        path, key_path = _backed_verdict(tmp_path, scored)
    key = json.loads(key_path.read_text())
    key.setdefault("blind_key", {"A": "first", "B": "second"})
    trials = plan_trials(37, key["blind_key"], repeats=1, catch=True)
    key["trials"] = trials
    answers = ["indistinguishable" if trial["kind"] == "catch" else
               next(label for label, role in trial["blind_key"].items() if role == "first")
               for trial in trials]
    measured = consistency(trials, answers, key["blind_key"])
    key_path.write_text(json.dumps(key))
    verdict = json.loads(path.read_text())
    verdict["audition_key"]["sha256"] = sha256(key_path)
    verdict["listener_trials"] = answers
    verdict["listener_consistency"] = measured
    path.write_text(json.dumps(verdict))
    out = tmp_path / f"good-{kind}"
    good = _run(path, out_dir=out)
    assert good.returncode == 0, good.stderr
    report = json.loads((out / "report.json").read_text())
    assert report["comparison_count_not_independent_n"] == 1
    assert report["listener_consistency"]["repeat"]["fraction"] == 1.0
    assert report["listener_consistency"]["catch"]["fraction"] == 1.0

    repeat_index = next(i for i, trial in enumerate(trials) if trial["kind"] == "repeat")
    verdict["listener_trials"][repeat_index] = (
        "B" if verdict["listener_trials"][repeat_index] == "A" else "A")
    path.write_text(json.dumps(verdict))
    bad_out = tmp_path / f"changed-{kind}"
    rejected = _run(path, out_dir=bad_out)
    assert rejected.returncode != 0
    assert "consistency disagree" in rejected.stderr
    assert not bad_out.exists()


@pytest.mark.parametrize("damage", ("score", "heard-audio", "key"))
def test_audit_refuses_broken_bindings_before_writing_a_report(tmp_path, damage):
    scored = _scored(tmp_path)
    path, key_path = _blind_verdict(tmp_path, scored)
    if damage == "score":
        verdict = json.loads(path.read_text())
        verdict["objective_scoring"]["match_v2"]["prediction"] = "B"
        path.write_text(json.dumps(verdict))
    elif damage == "heard-audio":
        verdict = json.loads(path.read_text())
        verdict["heard_audio"]["sha256"] = "0" * 64
        path.write_text(json.dumps(verdict))
    else:
        key = json.loads(key_path.read_text())
        key["objective_record"]["target_id"] = "different-song"
        key_path.write_text(json.dumps(key))
    out_dir = tmp_path / "refused-audit"
    completed = _run(path, out_dir=out_dir)
    assert completed.returncode != 0
    assert not out_dir.exists()


def test_audit_refuses_changed_backed_key_and_duplicate_inputs(tmp_path):
    scored = _scored(tmp_path)
    path, key_path = _backed_verdict(tmp_path, scored)
    duplicate = _run(path, path, out_dir=tmp_path / "duplicate-audit")
    assert duplicate.returncode != 0
    assert "duplicate verdict path" in duplicate.stderr
    key_path.write_text(key_path.read_text() + " ")
    changed = _run(path, out_dir=tmp_path / "changed-audit")
    assert changed.returncode != 0
    assert "no longer matches" in changed.stderr


@pytest.mark.parametrize("damage", ("empty-v2", "scoring-error"))
def test_audit_keeps_verdict_but_does_not_count_invalid_v2(tmp_path, damage):
    scored = _scored(tmp_path)
    path, key_path = _backed_verdict(tmp_path, scored)
    key = json.loads(key_path.read_text())
    wrapped = json.loads(path.read_text())
    if damage == "empty-v2":
        key["objective_record"]["objective_scoring"]["match_v2"] = {}
        wrapped["frozen_scored_record"]["objective_scoring"]["match_v2"] = {}
    else:
        for field in ("objective_scoring", "agreement", "agreement_with_level",
                      "agreement_match_v2"):
            wrapped["frozen_scored_record"].pop(field, None)
        wrapped["frozen_scored_record"]["scoring_error"] = "archived source unavailable"
    key_path.write_text(json.dumps(key))
    wrapped["audition_key"]["sha256"] = sha256(key_path)
    path.write_text(json.dumps(wrapped))

    out_dir = tmp_path / "unscored-audit"
    completed = _run(path, out_dir=out_dir)
    assert completed.returncode == 0, completed.stderr
    report = json.loads((out_dir / "report.json").read_text())
    assert report["v2"]["summary"]["closer"]["target_groups_with_decisive_verdicts"] == 0
    assert report["v2"]["target_groups"]["song"]["closer"][
        "diagnostic_counts_not_independent_n"] == {"unscored": 1}
    assert report["scoring_error_count"] == (1 if damage == "scoring-error" else 0)


@pytest.mark.parametrize("damage", ("blind-audio", "backed-audio", "blind-key-swap",
                                    "blind-bad-heard", "backed-bad-key", "blind-no-key-hash",
                                    "blind-bad-objective", "backed-bad-objective"))
def test_audit_rejects_missing_or_malformed_key_bindings(tmp_path, damage):
    scored = _scored(tmp_path)
    if damage.startswith("blind"):
        path, key_path = _blind_verdict(tmp_path, scored)
    else:
        path, key_path = _backed_verdict(tmp_path, scored)
    key = json.loads(key_path.read_text())
    verdict = json.loads(path.read_text())
    if damage == "blind-audio":
        key.pop("output")
        verdict.pop("heard_audio")
    elif damage == "backed-audio":
        key.pop("output")
        verdict.pop("heard_audio_sha256")
    elif damage == "blind-key-swap":
        key["blind_key"] = {"A": "second", "B": "first"}
    elif damage == "blind-bad-heard":
        verdict["heard_audio"] = []
    elif damage == "backed-bad-key":
        verdict["audition_key"] = []
    elif damage in ("blind-bad-objective", "backed-bad-objective"):
        key["objective_record"] = ["not", "an", "object"]
    else:
        verdict.pop("audition_key")
    key_path.write_text(json.dumps(key))
    if damage in ("blind-audio", "backed-audio", "blind-bad-objective",
                  "backed-bad-objective"):
        verdict["audition_key"]["sha256"] = sha256(key_path)
    path.write_text(json.dumps(verdict))
    out_dir = tmp_path / "refused-binding"
    completed = _run(path, out_dir=out_dir)
    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    assert not out_dir.exists()


def test_legacy_v1_blind_sidecar_without_key_hash_remains_unscored(tmp_path):
    scored = _scored(tmp_path, v2=False)
    path, _ = _blind_verdict(tmp_path, scored)
    verdict = json.loads(path.read_text())
    verdict.pop("audition_key")
    path.write_text(json.dumps(verdict))
    out_dir = tmp_path / "legacy-audit"
    completed = _run(path, out_dir=out_dir)
    assert completed.returncode == 0, completed.stderr
    report = json.loads((out_dir / "report.json").read_text())
    assert report["inputs"][0]["kind"] == "blind-legacy-v1-only"
    assert report["v2"]["summary"]["closer"]["target_groups_with_decisive_verdicts"] == 0
