"""Source-only synthetic checks: never read any actual study assets."""
from copy import deepcopy
import io
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from learn import di_morgan_processing_control as M


def panel():
    return [{"slug": f"synthetic-{i}", "take": f"take-{i}", "content": "chords" if i < 6 else "scales"}
            for i in range(12)]


def scored(take, chain="clean", net=.7):
    row = {**take, "chain": chain, "valid": True, "qc_valid": True, "oracle": 0.,
           "wet": 1., "flatref": .9, "net": net}
    for arm, key in M.T.ARMS.items():
        row[key] = {m: row[arm] for m in M.T.METRICS}
    return row


def context():
    takes = panel()
    rows = [scored(t) for t in takes]
    return {"manifest": {"takes": takes, "preset": "samples/Example_Clean_PR12.xml"},
            "original": {"rows": rows, "screen": M.F.compare(rows, takes)},
            "pins": {}, "revision": "synthetic", "hashes": {}, "correction": {}, "approval": {}}


def fake_pack():
    from packs.loader import load_pack
    return load_pack("morgan")  # Committed parameter metadata only.


def base_command():
    """A source fixture includes otherwise untouched compressor/output/mic slots."""
    values = {k: "0.21" for changes in M.OVERRIDES.values() for k in changes}
    values.update({"pr12Amp/pr12Volume": "0.62", "drive1/drive1Active": "false",
                   "drive2/drive2Active": "false", "compressor/compressorActive": "true",
                   "parameters/outputGain": "-2.4", "cabParameters/leftMicPosition": "0.31"})
    return {"selectAmp": 1, "edits": [{"module": k.rpartition("/")[0], "key": k.rpartition("/")[2], "value": v}
                                      for k, v in values.items()]}


def test_exact_commands_and_untouched_base():
    base = base_command()
    before = deepcopy(base)
    commands = M.command_panel(base, fake_pack())
    assert base == before and commands["clean"] == before
    assert tuple(commands) == ("clean", *M.EXPERIMENTS)
    original = {e["module"] + "/" + e["key"]: e["value"] for e in base["edits"]}
    for chain, command in commands.items():
        actual = {e["module"] + "/" + e["key"]: e["value"] for e in command["edits"]}
        assert actual == {**original, **M.OVERRIDES[chain]}
        assert command["selectAmp"] == base["selectAmp"]
        assert [e["key"] for e in command["edits"]] == [e["key"] for e in base["edits"]]
    assert commands["drive1"]["edits"][0] is not base["edits"][0]


def test_source_template_and_pack_fixture_without_host():
    # The repository's source preset is allowed; this is not a study NPZ,
    # installed plugin, external preset or AudioUnitRenderer instance.
    from format.parser import parse
    from format.structured import build
    import research.render_preset_panel as RP
    pack = fake_pack()
    preset = build(parse((M.ROOT / "samples/Example_Clean_PR12.xml").read_bytes()))
    values = {(p.module_path, p.key): p.value for p in preset.parameters
              if p.module_path and (s := pack.parameters.get(p.module_path + "/" + p.key)) and s.writable}
    for key, human in {**RP.RULE_SET, RP.SPRING["pr12"]: 0.}.items():
        module, _, name = key.rpartition("/")
        values[module, name] = pack.to_stored(pack.parameters[key], human)
    base = {"selectAmp": int(float(preset.by_path["", "selectedAmp"].value)),
            "edits": [{"module": m, "key": k, "value": v} for (m, k), v in values.items()]}
    commands = M.command_panel(base, pack)
    assert commands["clean"] == base and len(base["edits"]) > 100
    for name in M.EXPERIMENTS:
        assert all(a == b for a, b in zip(base["edits"], commands[name]["edits"])
                   if a["module"] + "/" + a["key"] not in M.OVERRIDES[name])


@pytest.mark.parametrize("mutation", ["volume", "pedal", "selector", "duplicate", "kind", "range"])
def test_command_contract_rejects_drift(mutation):
    base, pack = base_command(), fake_pack()
    if mutation == "volume":
        next(e for e in base["edits"] if e["key"] == "pr12Volume")["value"] = "0.63"
    elif mutation == "pedal":
        next(e for e in base["edits"] if e["key"] == "drive1Active")["value"] = "true"
    elif mutation == "selector":
        base["selectAmp"] = 2
    elif mutation == "duplicate":
        base["edits"].append(base["edits"][0])
    elif mutation == "kind":
        pack.parameters["drive1/drive1Active"].kind = "rotation"
    else:
        pack.parameters["drive1/drive1Drive"].kind = "metered"
    with pytest.raises(ValueError):
        M.command_panel(base, pack)


def test_full_panel_gate_and_invalid_priority():
    takes = panel()
    rows = [scored(t, c) for c in M.EXPERIMENTS for t in takes]
    assert M.compare(rows, takes)["disposition"] == "PASS"
    failing = [scored(t, c, net=.89 if c == "drive1" else .7) for c in M.EXPERIMENTS for t in takes]
    assert M.compare(failing, takes)["disposition"] == "FAIL"
    failing[-1]["network_scores"]["raw_lowband"] = float("nan")
    assert M.compare(failing, takes)["disposition"] == "INCONCLUSIVE"
    for broken in (rows[:-1], rows + [rows[0]], rows[:-1] + [rows[0]]):
        assert M.compare(broken, takes)["disposition"] == "INCONCLUSIVE"


def test_gate_requires_nine_wins_and_both_groups():
    takes = panel()
    # Eight very large wins still fail the frozen strict-win requirement.
    rows = [scored(t, net=.1 if i < 8 else 1.1) for i, t in enumerate(takes)]
    assert M.compare(rows, takes, ("clean",))["disposition"] == "FAIL"
    rows = [scored(t, net=.7 if i < 9 else 1.2) for i, t in enumerate(takes)]
    assert M.compare(rows, takes, ("clean",))["disposition"] == "FAIL"  # scale group median <=0
    rows = [scored(t, net=.1 if i not in (2, 7, 10) else 1.1) for i, t in enumerate(takes)]
    assert M.compare(rows, takes, ("clean",))["disposition"] == "PASS"


def test_render_di_exact_overlap(monkeypatch):
    monkeypatch.setattr(M, "PREROLL", 3)
    monkeypatch.setattr(M, "N", 5)
    di = np.arange(5, dtype=np.float64)
    x = np.r_[np.zeros(3), di]
    M.validate_render_di(x, di)
    for bad in (x.astype(np.float32), x[:-1], np.r_[x[:-1], np.nan], x + 1e-12):
        with pytest.raises(ValueError):
            M.validate_render_di(bad, di)
    a, b = np.zeros(5), np.zeros(8)
    b[3] = -0.
    with pytest.raises(ValueError, match="bytes"):
        M.validate_render_di(b, a)


def test_full_array_slicing_and_proof(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "PREROLL", 3)
    monkeypatch.setattr(M, "N", 5)
    monkeypatch.setattr(M, "LATENCY", 2)
    full = np.arange(10, dtype=np.float64)
    x, wet = M.slices(full)
    assert np.array_equal(x, full[3:8]) and np.array_equal(wet, full[5:10])
    directory = tmp_path / "render-clean" / "clean"
    directory.mkdir(parents=True)
    np.savez(directory / "test.mono.npz", full_mono=full)
    np.savez(directory / "test.slices.npz", net_input=x, wet=wet)
    assert all(np.array_equal(a, b) for a, b in zip(M.load_slices(tmp_path, "render-clean", "clean", "test"), (x, wet)))
    np.savez(directory / "test.slices.npz", net_input=x, wet=wet + 1)
    with pytest.raises(ValueError, match="slicing"):
        M.load_slices(tmp_path, "render-clean", "clean", "test")


@pytest.mark.parametrize("raw", [np.array([np.nan, np.inf]), np.ones((3, 4)), np.array(2.)])
def test_invalid_returns_retained_before_validation(tmp_path, raw):
    archive = M.save_arrays(tmp_path / "returned.npz", raw_prediction=raw)
    assert len(archive["sha256"]) == 64
    with np.load(tmp_path / "returned.npz", allow_pickle=False) as saved:
        assert saved["raw_prediction"].tobytes() == raw.tobytes()
    with pytest.raises(ValueError):
        M.validate_prediction(raw)


def test_save_hash_failure_keeps_npz_and_recovery(tmp_path, monkeypatch):
    monkeypatch.setattr(M.R, "sha", lambda p: (_ for _ in ()).throw(OSError("hash failed")))
    values = np.array([1., np.nan])
    with pytest.raises(OSError, match="hash failed"):
        M.save_arrays(tmp_path / "return.npz", raw_prediction=values)
    with np.load(tmp_path / "return.npz", allow_pickle=False) as saved:
        assert saved["raw_prediction"].tobytes() == values.tobytes()
    assert (tmp_path / "return.npz.raw_prediction.recovery.npy").is_file()
    assert json.loads((tmp_path / "return.save-failure.json").read_text())["original_error"]["type"] == "OSError"


def test_serialization_failure_retains_each_member(tmp_path, monkeypatch):
    monkeypatch.setattr(np, "savez_compressed", lambda *a, **k: (_ for _ in ()).throw(OSError("disk simulation")))
    with pytest.raises(OSError):
        M.save_arrays(tmp_path / "return.npz", raw_prediction=np.array([np.nan]))
    assert (tmp_path / "return.npz").exists()
    assert (tmp_path / "return.npz.raw_prediction.recovery.npy").exists()


def test_json_nonfinite_rejection_is_safe(tmp_path):
    M.write_json(tmp_path / "invalid.json", {"loss": float("nan"), "nested": [float("inf")]})
    value = json.loads((tmp_path / "invalid.json").read_text())
    assert value["loss"] is None and value["nested"] == [None]
    assert value["nonfinite_diagnostic_fields"] == ["row.loss", "row.nested[0]"]


def test_draft_refuses_before_assets(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "ROOT", tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / M.PLAN).write_text("**DRAFT**\n## Frozen design\nsynthetic\n")
    monkeypatch.setattr(M.R, "sha", lambda *a: pytest.fail("asset hashing before declaration"))
    with pytest.raises(ValueError, match="declaration"):
        M.guard(0)


@pytest.mark.parametrize("stage", M.STAGES)
def test_environment_gate(stage, monkeypatch):
    correct = M.expected_prefix(stage)
    monkeypatch.setattr(M.sys, "prefix", str(correct))
    M.require_environment(stage)
    monkeypatch.setattr(M.sys, "prefix", "/synthetic-wrong-python")
    with pytest.raises(ValueError, match="environment"):
        M.require_environment(stage)


def test_barriers_block_clean_prereq_before_plugin(tmp_path, monkeypatch):
    ctx = context()
    calls = []
    def report(run, stage):
        calls.append(stage)
        if stage == "score-clean":
            raise ValueError("clean failed")
        return {"passed": True}
    monkeypatch.setattr(M, "stage_report", report)
    monkeypatch.setattr(M, "read_json", lambda p: {"pins": {}, "revision": "synthetic", "input_artifacts": {}, "files": {}})
    # Empty fake stage dirs satisfy the evidence-set gate; no host factory called.
    for stage in M.STAGES[:4]:
        (tmp_path / stage).mkdir()
        (tmp_path / stage / "seal.json").write_text("{}")
    with pytest.raises(ValueError, match="clean failed"):
        M.barriers(tmp_path, "render-panel", ctx)
    assert calls == list(M.STAGES[:4])


def test_closed_attempt_rejects_every_stage(tmp_path):
    (tmp_path / "closed.json").write_text("{}")
    for stage in M.STAGES:
        with pytest.raises(ValueError, match="closed"):
            M.barriers(tmp_path, stage, context())


def test_replay_partial_failure_is_saved(tmp_path, monkeypatch):
    ctx = context()
    monkeypatch.setattr(M, "check_time", lambda s: None)
    def score(take, *args):
        if take["slug"] == "synthetic-2":
            raise ValueError("synthetic score failure")
        return scored(take)
    monkeypatch.setattr(M.T, "scored_row", score)
    loaded = {t["slug"]: {} for t in panel()}
    with pytest.raises(ValueError, match="score failure"):
        M.replay(tmp_path, ctx, loaded, {}, 0)
    report = json.loads((tmp_path / "scalar-replay.json").read_text())
    assert not report["passed"] and not report["complete"] and report["scalar_count"] == 18
    assert len(report["rows"]) == 3 and (tmp_path / "replay-attempt-03.json").exists()


def test_baseline_scalar_replay_precedes_model_and_does_not_read_render_di(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(M, "replay", lambda *a: calls.append("108") or [])
    monkeypatch.setattr(M, "load_model", lambda *a: calls.append("model") or object())
    with pytest.raises(ValueError):  # No predictions -> original byte/direct36 barrier fails.
        M.baseline(tmp_path, context(), {}, {}, 0)
    assert calls == ["108", "model"]


def test_failed_scalar_replay_blocks_model(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "replay", lambda *a: (_ for _ in ()).throw(ValueError("108 mismatch")))
    monkeypatch.setattr(M, "load_model", lambda *a: pytest.fail("model before scalar barrier"))
    with pytest.raises(ValueError, match="108 mismatch"):
        M.baseline(tmp_path, context(), {}, {}, 0)


def test_baseline_return_saved_before_schema_rejection(tmp_path, monkeypatch):
    ctx = context()
    monkeypatch.setattr(M, "replay", lambda *a: [scored(t) for t in panel()])
    monkeypatch.setattr(M, "load_model", lambda *a: object())
    monkeypatch.setattr(M, "check_time", lambda *a: None)
    monkeypatch.setattr(M, "infer", lambda *a: np.array([np.nan], dtype=np.float32))
    with pytest.raises(ValueError):
        M.baseline(tmp_path, ctx, {t["slug"]: {"net_input": np.ones(3)} for t in panel()}, {}, 0)
    assert (tmp_path / "synthetic-0.prediction.npz").exists()
    record = json.loads((tmp_path / "prediction-replay.json").read_text())
    assert record["rows"][0]["returned"] and not record["passed"]


@pytest.mark.parametrize("chains", [("clean",), M.EXPERIMENTS])
def test_all_predictions_persist_before_validation_or_primary_score(tmp_path, monkeypatch, chains):
    ctx, calls = context(), []
    mock_scoring(monkeypatch)
    monkeypatch.setattr(M, "load_model", lambda *a: object())
    monkeypatch.setattr(M, "load_slices", lambda *a: (np.ones(3), np.ones(3)))
    monkeypatch.setattr(M, "infer", lambda *a: calls.append("infer") or np.array([np.nan], dtype=np.float32))
    monkeypatch.setattr(M, "check_time", lambda *a: None)
    def validate(*args):
        assert len(list(tmp_path.glob("*.prediction.npz"))) == 12 * len(chains)
        assert (tmp_path / "all-predictions-saved.json").exists()
        calls.append("validate")
        raise ValueError("synthetic stop at validation boundary")
    monkeypatch.setattr(M.P, "score_prediction", lambda *a, **k: pytest.fail("primary new score too early"))
    monkeypatch.setattr(M, "validate_prediction", validate)
    result = M.score_stage(tmp_path, tmp_path, "score-clean" if len(chains) == 1 else "score-panel", ctx,
                           {t["slug"]: {} for t in panel()}, {}, 0, chains)
    assert result["disposition"] == "INCONCLUSIVE" and len(result["rows"]) == 12 * len(chains)
    assert all("validation boundary" in r["error"]["message"] for r in result["rows"])
    assert calls == ["infer"] * (12 * len(chains)) + ["validate"] * (12 * len(chains))


def mock_scoring(monkeypatch):
    monkeypatch.setattr(M, "N", 5)
    monkeypatch.setattr(M, "check_time", lambda *a: None)
    monkeypatch.setattr(M, "load_model", lambda *a: object())
    monkeypatch.setattr(M, "load_slices", lambda *a: (np.ones(5), np.ones(5)))
    monkeypatch.setattr(M, "infer", lambda *a: np.full(5, .7, dtype=np.float32))
    monkeypatch.setattr(M, "pinned_asset", lambda *a: None)
    original_load = np.load
    monkeypatch.setattr(np, "load", lambda path, **kwargs: np.zeros(2049) if str(path) == M.AVERAGE["path"]
                        else original_load(path, **kwargs))
    monkeypatch.setattr(M, "read_json", lambda p: {"rows": [{**t, "renderer_metadata": {"plugin_version": "synthetic"}}
                                                           for t in panel()]})
    monkeypatch.setattr(M, "stage_report", lambda *a: {"chains": [{"identity": {"plugin_version": "synthetic"}}],
                                                     "rows": [scored(t) for t in panel()]})
    monkeypatch.setattr(M.P, "canonical_target", lambda wave, average: wave.copy())
    def score(wave, target, *a, **k):
        value = 0. if np.array_equal(wave, target) else .7 if wave.dtype == np.float32 else .9
        return {metric: value for metric in M.T.METRICS}
    monkeypatch.setattr(M.P, "score_prediction", score)
    monkeypatch.setattr(M.R, "repeat_canary", lambda *a: {"passed": True})
    monkeypatch.setattr(M.subprocess, "run", lambda *a, **k: pytest.fail("inline executable invocation"))


@pytest.mark.parametrize("chains", [("clean",), M.EXPERIMENTS])
def test_primary_scores_finish_initial_without_inline_verification(tmp_path, monkeypatch, chains):
    ctx = context()
    mock_scoring(monkeypatch)
    loaded = {t["slug"]: {"di": np.arange(5, dtype=np.float64), "target": np.arange(5, dtype=np.float64),
                           "wet": np.ones(5)} for t in panel()}
    result = M.score_stage(tmp_path, tmp_path, "score-clean" if chains == ("clean",) else "score-panel",
                           ctx, loaded, {}, 0, chains)
    assert result["complete"] and result["passed"] and result["disposition"] == "PASS"
    assert result["verification_status"] == "INITIAL" and not result["independent_verified"]
    assert len(result["rows"]) == 12 * len(chains)
    assert len(list(tmp_path.glob("*.prediction.npz"))) == 12 * len(chains)
    assert len(list(tmp_path.glob("*.construction.npz"))) == 12 * len(chains)


class FakeBackend:
    def _exchange(self, command, timeout=None):
        self.observed_before_call = [json.loads(l)["event"] for l in self.transcript.read_text().splitlines()]
        reply = self._readline(timeout)
        if not reply.get("ok"):
            raise ValueError("server rejected command")
        return reply

    def _readline(self, timeout=None):
        self.observed_timeout = timeout
        return json.loads(self._process.stdout.readline())

    def close(self):
        self.closed = True


class FakeProtocol(M.ProtocolEvidence, FakeBackend):
    pass


@pytest.mark.parametrize("line,expected", [('{"ok":true}\n', "exchange-return"),
                                            ('{"ok":false,"error":"bad"}\n', "exchange-error"),
                                            ('not-json\n', "exchange-error")])
def test_protocol_request_before_call_and_raw_reply_error_after(tmp_path, monkeypatch, line, expected):
    host = FakeProtocol()
    host.transcript, host.started, host.reply_timeout_s = tmp_path / "protocol.jsonl", 0, 120.
    host._process = SimpleNamespace(stdout=io.StringIO(line), poll=lambda: None)
    monkeypatch.setattr(M.time, "monotonic", lambda: 1.)
    if expected == "exchange-error":
        with pytest.raises(ValueError):
            host._exchange({"selectAmp": 1}, timeout=180.)
    else:
        host._exchange({"selectAmp": 1}, timeout=180.)
    events = [json.loads(l) for l in host.transcript.read_text().splitlines()]
    assert host.observed_before_call == ["request"]
    assert events[1]["event"] == "protocol-line" and events[1]["raw"] == line
    assert events[-1]["event"] == expected
    host.close()
    assert host.closed
    assert any(json.loads(l)["event"] == "closed" for l in host.transcript.read_text().splitlines())


def test_host_closes_and_partial_record_survives_render_failure(tmp_path, monkeypatch):
    import research.render_preset_panel as RP
    host = SimpleNamespace(closed=False)
    def close():
        host.closed = True
    host.close = close
    monkeypatch.setattr(RP, "preset_edits", lambda *a: (1, base_command()["edits"]))
    monkeypatch.setattr(M, "full_render", lambda *a: (_ for _ in ()).throw(ValueError("synthetic render error")))
    with pytest.raises(ValueError, match="render error"):
        M.render_chain(tmp_path / "chain", "clean", context(), {"synthetic-0": np.ones(3)}, 0,
                       host_factory=lambda *a: host)
    assert host.closed and (tmp_path / "chain" / "partial.json").exists()


def test_one_host_all_twelve_and_retained_first_end_repeats(tmp_path, monkeypatch):
    import research.render_preset_panel as RP
    monkeypatch.setattr(M, "PREROLL", 3)
    monkeypatch.setattr(M, "N", 5)
    monkeypatch.setattr(M, "LATENCY", 2)
    monkeypatch.setattr(M, "check_time", lambda *a: None)
    monkeypatch.setattr(RP, "preset_edits", lambda *a: (1, base_command()["edits"]))
    labels, hosts = [], []
    def factory(*args):
        host = SimpleNamespace(closed=False)
        host.close = lambda: setattr(host, "closed", True)
        hosts.append(host)
        return host
    def full(host, out, label, *args):
        labels.append(label)
        return np.arange(10, dtype=np.float64), {"plugin_version": "synthetic"}
    monkeypatch.setattr(M, "full_render", full)
    monkeypatch.setattr(M.R, "repeat_canary", lambda *a: {"passed": False})
    result = M.render_chain(tmp_path / "chain", "drive1", context(), {t["slug"]: np.ones(8) for t in panel()}, 0,
                            host_factory=factory)
    assert len(hosts) == 1 and hosts[0].closed
    assert labels == ["warmup", "synthetic-0", "first-repeat", *[t["slug"] for t in panel()[1:]], "end-return-repeat"]
    assert len(result["rows"]) == 12 and not result["valid"]
    assert (tmp_path / "chain" / "repeat-canaries.json").exists()


@pytest.mark.parametrize("bad", ["shape", "nonfinite", "rate", "budget"])
def test_raw_decoder_retains_full_block_return_before_rejection(tmp_path, monkeypatch, bad):
    import soundfile as sf
    raw = np.ones((14, 2), dtype=np.float32)
    rate = M.P.SR
    if bad == "shape":
        raw = raw[:, :1]
    elif bad == "nonfinite":
        raw[0, 0] = np.nan
    elif bad == "rate":
        rate = 44100
    monkeypatch.setattr(sf, "read", lambda *a, **k: (raw, rate))
    monkeypatch.setattr(M, "check_time", lambda *a: None if bad != "budget" else (_ for _ in ()).throw(TimeoutError()))
    host = SimpleNamespace(started=0, block_size=8)
    with pytest.raises((ValueError, TimeoutError)):
        M.ProtocolEvidence._read_render(host, tmp_path / "return.wav", 10)
    with np.load(tmp_path / "return.decoded.npz", allow_pickle=False) as saved:
        assert saved["raw_stereo"].tobytes() == raw.tobytes()
    assert (tmp_path / "return.decoded-mono.npz").exists()


def test_raw_decoder_preserves_padding_then_original_trim(tmp_path, monkeypatch):
    import soundfile as sf
    raw = np.arange(28, dtype=np.float32).reshape(14, 2)
    monkeypatch.setattr(sf, "read", lambda *a, **k: (raw, M.P.SR))
    monkeypatch.setattr(M, "check_time", lambda *a: None)
    trimmed = M.ProtocolEvidence._read_render(SimpleNamespace(started=0, block_size=8), tmp_path / "return.wav", 10)
    assert np.array_equal(trimmed, raw[:10])
    with np.load(tmp_path / "return.decoded.npz", allow_pickle=False) as saved:
        assert np.array_equal(saved["raw_stereo"], raw)


@pytest.mark.parametrize("raw", [np.ones((4, 3), dtype=np.float32), np.full((10, 2), np.nan, dtype=np.float32)])
def test_full_render_retains_stereo_mono_before_validation(tmp_path, monkeypatch, raw):
    monkeypatch.setattr(M, "PREROLL", 3)
    monkeypatch.setattr(M, "N", 5)
    monkeypatch.setattr(M, "LATENCY", 2)
    monkeypatch.setattr(M, "check_time", lambda *a: None)
    host = SimpleNamespace(render=lambda *a: SimpleNamespace(audio=raw, metadata=SimpleNamespace(as_dict=lambda: {
        "sample_rate": M.P.SR, "plugin_version": "synthetic"})))
    with pytest.raises(ValueError):
        M.full_render(host, tmp_path, "bad", np.ones(8), 0)
    with np.load(tmp_path / "bad.full.npz", allow_pickle=False) as saved:
        assert saved["raw_stereo"].tobytes() == raw.tobytes()
    assert (tmp_path / "bad.mono.npz").exists()


def test_panel_does_all36_before_rejecting_repeat_controls(tmp_path, monkeypatch):
    ctx = context()
    monkeypatch.setattr(M, "load_render_di", lambda *a: {})
    monkeypatch.setattr(M, "recheck", lambda *a: None)
    monkeypatch.setattr(M, "check_inputs", lambda *a: None)
    monkeypatch.setattr(M, "stage_report", lambda *a: {"chains": [{"identity": {"plugin_version": "synthetic"}}]})
    observed = []
    def chain(out, name, *args, **kwargs):
        observed.extend((name, t["slug"]) for t in panel())
        return {"identity": {"plugin_version": "synthetic"}, "valid": name != "drive1", "chain": name}
    monkeypatch.setattr(M, "render_chain", chain)
    result = M.render_stage(tmp_path, ctx, {}, 0, M.EXPERIMENTS)
    assert len(observed) == 36 and result["case_count"] == 36
    assert result["disposition"] == "INCONCLUSIVE"


def test_source_head_and_input_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "ROOT", tmp_path)
    monkeypatch.setattr(M, "check_time", lambda *a: None)
    source = tmp_path / "source.py"
    source.write_text("synthetic")
    ctx = {"pins": {"source.py": M.digest(source.read_bytes())}, "revision": "original", "hashes": {"source.py": M.digest(source.read_bytes())}}
    monkeypatch.setattr(M.subprocess, "check_output", lambda *a, **k: "original\n")
    M.recheck(ctx, 0)
    M.check_inputs(ctx, 0)
    source.write_text("changed")
    with pytest.raises(ValueError, match="source drift"):
        M.recheck(ctx, 0)
    with pytest.raises(ValueError, match="artifact drift"):
        M.check_inputs(ctx, 0)
    ctx["pins"] = {}
    monkeypatch.setattr(M.subprocess, "check_output", lambda *a, **k: "changed-head\n")
    with pytest.raises(ValueError, match="HEAD drift"):
        M.recheck(ctx, 0)


def test_budget_covers_final_save_no_final_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "recheck", lambda *a: None)
    monkeypatch.setattr(M, "check_inputs", lambda *a: None)
    monkeypatch.setattr(M, "runtime", lambda: {})
    now = [1.]
    original_write = M.write_json
    def write(path, value):
        original_write(path, value)
        if Path(path).name == "result.pending.json":
            now[0] = 901.
    monkeypatch.setattr(M, "write_json", write)
    monkeypatch.setattr(M.time, "monotonic", lambda: now[0])
    with pytest.raises(TimeoutError):
        M.finish(tmp_path, {"complete": True, "passed": True, "disposition": "PASS"}, {}, 0)
    assert (tmp_path / "result.pending.json").exists()
    assert not (tmp_path / "result.json").exists() and not (tmp_path / "seal.json").exists()


def test_completed_stage_seal_detects_evidence_drift(tmp_path, monkeypatch):
    ctx = context()
    out = tmp_path / "preflight"
    out.mkdir()
    M.write_json(out / "provenance.json", {"pins": {}, "revision": "synthetic", "input_artifacts": {}})
    monkeypatch.setattr(M, "recheck", lambda *a: None)
    monkeypatch.setattr(M, "check_inputs", lambda *a: None)
    monkeypatch.setattr(M, "runtime", lambda: {})
    monkeypatch.setattr(M, "check_time", lambda *a: None)
    M.finish(out, {"complete": True, "passed": True, "disposition": "PASS"}, ctx, 0)
    initial = json.loads((out / "result.json").read_text())
    assert initial["verification_status"] == "INITIAL" and initial["independent_verified"] is False
    M.barriers(tmp_path, "baseline", ctx)
    (out / "runtime.json").write_text("{}")
    with pytest.raises(ValueError, match="evidence drift"):
        M.barriers(tmp_path, "baseline", ctx)


def test_new_member_is_read_only_by_render_loader(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "PREROLL", 3)
    monkeypatch.setattr(M, "N", 5)
    monkeypatch.setattr(M, "check_time", lambda *a: None)
    monkeypatch.setattr(M, "check_inputs", lambda *a: None)
    monkeypatch.setattr(M.T, "SOURCE", tmp_path)
    (tmp_path / "prepare").mkdir()
    ctx = context()
    loaded = {}
    for take in panel():
        di = np.arange(5, dtype=np.float64)
        loaded[take["slug"]] = {"di": di}
        np.savez(tmp_path / "prepare" / (take["slug"] + ".npz"), render_di=np.r_[np.zeros(3), di])
    result = M.load_render_di(ctx, loaded, 0)
    assert len(result) == 12


def test_dependency_closure_is_explicit_and_bounded():
    assert len(M.SOURCE_FILES) == len(set(M.SOURCE_FILES)) < 50
    for path in ("scripts/_swift.py", "scripts/au_render_server.swift", "scripts/au_probe.swift",
                 "packs/loader.py", "packs/morgan/manifest.json", "format/translate.py", "learn/direc.py"):
        assert path in M.SOURCE_FILES
    assert not any("phase-control" in p or "verification.json.gz" in p for p in M.SOURCE_FILES)


def test_panel_startup_identity_blocks_before_any_render_and_closes(tmp_path, monkeypatch):
    host = SimpleNamespace(closed=False, metadata=lambda: SimpleNamespace(as_dict=lambda: {"plugin_version": "changed"}))
    host.close = lambda: setattr(host, "closed", True)
    monkeypatch.setattr(M, "full_render", lambda *a: pytest.fail("render before identity check"))
    with pytest.raises(ValueError, match="sealed clean identity"):
        M.render_chain(tmp_path / "panel", "drive1", context(), {}, 0,
                       host_factory=lambda *a: host, expected_identity={"plugin_version": "clean"})
    assert host.closed and (tmp_path / "panel" / "partial.json").exists()
    observed = json.loads((tmp_path / "panel" / "startup-identity.json").read_text())
    assert observed["expected"] != observed["observed"]


def test_uniform_panel_identity_drift_rejected_in_render_stage(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "stage_report", lambda *a: {"chains": [{"identity": {"plugin_version": "clean"}}]})
    monkeypatch.setattr(M, "load_render_di", lambda *a: {})
    monkeypatch.setattr(M, "recheck", lambda *a: None)
    monkeypatch.setattr(M, "check_inputs", lambda *a: None)
    def changed(*a, **kw):
        assert kw["expected_identity"] == {"plugin_version": "clean"}
        return {"identity": {"plugin_version": "changed"}, "valid": True}
    monkeypatch.setattr(M, "render_chain", changed)
    with pytest.raises(ValueError, match="sealed clean identity"):
        M.render_stage(tmp_path, context(), {}, 0, M.EXPERIMENTS)


def test_uniform_panel_identity_drift_rejected_in_score_stage(tmp_path, monkeypatch):
    mock_scoring(monkeypatch)
    def report(run, stage):
        return {"chains": [{"identity": {"plugin_version": "changed" if stage == "render-panel" else "synthetic"}}],
                "rows": [scored(t) for t in panel()]}
    monkeypatch.setattr(M, "stage_report", report)
    with pytest.raises(ValueError, match="sealed clean identity"):
        M.score_stage(tmp_path, tmp_path, "score-panel", context(), {}, {}, 0, M.EXPERIMENTS)
    assert len(list(tmp_path.glob("*.prediction.npz"))) == 36


def test_transcript_write_failure_still_closes_backend(tmp_path, monkeypatch):
    host = FakeProtocol()
    host.transcript = tmp_path / "protocol.jsonl"
    host._process = SimpleNamespace(poll=lambda: None)
    monkeypatch.setattr(M, "event", lambda *a: (_ for _ in ()).throw(OSError("transcript failure")))
    with pytest.raises(OSError, match="transcript failure"):
        host.close()
    assert host.closed and host.evidence_closed
    assert len(host.evidence_close_errors) == 2


@pytest.mark.parametrize("body_fails", [False, True])
def test_close_failure_still_saves_partial_and_preserves_original(tmp_path, monkeypatch, body_fails):
    import research.render_preset_panel as RP
    monkeypatch.setattr(RP, "preset_edits", lambda *a: (1, base_command()["edits"]))
    host = SimpleNamespace(close=lambda: (_ for _ in ()).throw(OSError("close failure")))
    def render(*a):
        if body_fails:
            raise ValueError("original body failure")
        return np.ones(M.PREROLL + M.N + M.LATENCY), {"plugin_version": "synthetic"}
    monkeypatch.setattr(M, "full_render", render)
    monkeypatch.setattr(M.R, "repeat_canary", lambda *a: {"passed": True})
    monkeypatch.setattr(M, "check_time", lambda *a: None)
    with pytest.raises(ValueError if body_fails else OSError, match="original body failure" if body_fails else "close failure"):
        M.render_chain(tmp_path / "chain", "clean", context(), {t["slug"]: np.ones(8) for t in panel()}, 0,
                       host_factory=lambda *a: host)
    partial = json.loads((tmp_path / "chain" / "partial.json").read_text())
    assert partial["cleanup_errors"][0]["message"] == "close failure"
    assert len(partial["rows"]) == (0 if body_fails else 12)


@pytest.mark.parametrize("chains", [("clean",), M.EXPERIMENTS])
@pytest.mark.parametrize("index", ["first", "last"])
@pytest.mark.parametrize("bad", ["nonfinite", "shape"])
def test_invalid_prediction_has_full_row_coverage_and_priority(tmp_path, monkeypatch, chains, index, bad):
    mock_scoring(monkeypatch)
    count = 12 * len(chains)
    bad_index = 0 if index == "first" else count - 1
    outputs = [np.full(5, 2., dtype=np.float32) for _ in range(count)]  # Valid cases deliberately FAIL.
    outputs[bad_index] = np.full(5, np.nan, dtype=np.float32) if bad == "nonfinite" else np.ones(4, dtype=np.float32)
    returns = iter(outputs)
    monkeypatch.setattr(M, "infer", lambda *a: next(returns))
    def score(wave, target, *a, **k):
        value = 0. if np.array_equal(wave, target) else 2. if wave.dtype == np.float32 else .9
        return {metric: value for metric in M.T.METRICS}
    monkeypatch.setattr(M.P, "score_prediction", score)
    loaded = {t["slug"]: {"di": np.arange(5, dtype=np.float64), "target": np.arange(5, dtype=np.float64),
                           "wet": np.ones(5)} for t in panel()}
    result = M.score_stage(tmp_path, tmp_path, "score-clean" if chains == ("clean",) else "score-panel",
                           context(), loaded, {}, 0, chains)
    assert result["complete"] and result["disposition"] == "INCONCLUSIVE"
    assert len(result["rows"]) == len(list(tmp_path.glob("score-*.json"))) == count
    invalid = [r for r in result["rows"] if not r["valid"]]
    assert len(invalid) == 1 and invalid[0]["prediction_identity"]["sha256"] == M.digest(outputs[bad_index].tobytes())
    assert len(list(tmp_path.glob("*.prediction.npz"))) == count


@pytest.mark.parametrize("deadline_fails", [False, True])
def test_main_finalization_failures_withdraw_authority_before_bad_log(tmp_path, monkeypatch, deadline_fails):
    run = tmp_path / "attempt"
    run.mkdir()
    monkeypatch.setattr(M, "ROOT", tmp_path)
    monkeypatch.setattr(M, "OUTPUT", "attempt")
    for name in ("require_environment", "barriers", "recheck", "check_inputs", "check_time"):
        monkeypatch.setattr(M, name, lambda *a: None)
    monkeypatch.setattr(M, "guard", lambda *a: context())
    monkeypatch.setattr(M, "load_original", lambda *a, **k: {})
    monkeypatch.setattr(M.V, "load_windows", lambda *a: {})
    monkeypatch.setattr(M, "runtime", lambda: {})
    monkeypatch.setattr(M, "score_stage", lambda *a: {"complete": True, "passed": True, "disposition": "PASS"})
    real_write = M.write_json
    def write(path, value):
        if Path(path).name == "closed.json" and not deadline_fails:
            raise OSError("closure failure")
        real_write(path, value)
    monkeypatch.setattr(M, "write_json", write)
    def check(started):
        if deadline_fails and (run / "closed.json").exists():
            raise TimeoutError("final deadline failure")
    monkeypatch.setattr(M, "check_time", check)
    def event(path, value):
        if Path(path).name == "failures.jsonl":
            assert not (run / "score-panel" / "result.json").exists()
            raise OSError("failure log error")
        with Path(path).open("a") as f:
            f.write(json.dumps(value) + "\n")
    monkeypatch.setattr(M, "event", event)
    with pytest.raises(TimeoutError if deadline_fails else OSError, match="final deadline" if deadline_fails else "closure failure"):
        M.main(["score-panel", "--run", str(run)])
    with pytest.raises((ValueError, FileNotFoundError)):
        M.stage_report(run, "score-panel")
    assert (run / "score-panel" / "result.failed-provisional.json").exists()
    assert (run / "score-panel" / "invalidated.json").exists()
    assert (run / "closure-errors.jsonl").exists() and (run / "cleanup-errors.json").exists()


@pytest.mark.parametrize("partial", [b'{"ok":', b'{"ready":'])
def test_partial_protocol_line_deadline_retains_bytes_and_closes(tmp_path, partial):
    read_fd, write_fd = os.pipe()
    stream = os.fdopen(read_fd, "r")
    os.write(write_fd, partial)
    host = FakeProtocol()
    host.transcript, host.started, host.reply_timeout_s = tmp_path / "protocol.jsonl", time.monotonic(), .02
    host._process = SimpleNamespace(stdout=stream, poll=lambda: None)
    before = time.monotonic()
    try:
        with pytest.raises(TimeoutError, match="complete protocol line"):
            host._readline()
        assert time.monotonic() - before < 1.
        assert host.closed
        events = [json.loads(l) for l in host.transcript.read_text().splitlines()]
        error = next(e for e in events if e["event"] == "read-error")
        assert error["partial_raw_hex"] == partial.hex()
    finally:
        stream.close()
        os.close(write_fd)


def test_protocol_complete_pipe_lines_no_read_ahead(tmp_path):
    read_fd, write_fd = os.pipe()
    stream = os.fdopen(read_fd, "r")
    os.write(write_fd, b'{"ready":true}\n{"ok":true}\n')
    host = FakeProtocol()
    host.transcript, host.started, host.reply_timeout_s = tmp_path / "protocol.jsonl", time.monotonic(), .1
    host._process = SimpleNamespace(stdout=stream, poll=lambda: None)
    try:
        assert host._readline() == {"ready": True}
        assert host._readline() == {"ok": True}
    finally:
        stream.close()
        os.close(write_fd)


@pytest.mark.parametrize("startup", [False, True])
def test_timeout_and_transcript_failure_preserve_original_and_partial_fallback(tmp_path, monkeypatch, startup):
    import research.render_preset_panel as RP
    from match.renderer_au import AudioUnitRenderer
    class PipeBackend(FakeBackend):
        _ensure_server = AudioUnitRenderer._ensure_server
        _exchange = AudioUnitRenderer._exchange
        def _au_triple(self):
            return {"type": "fake", "subtype": "fake", "manufacturer": "fake"}
    class PipeHost(M.ProtocolEvidence, PipeBackend):
        pass
    read_fd, write_fd = os.pipe()
    stream = os.fdopen(read_fd, "r")
    partial = b'{"ready":' if startup else b'{"ok":'
    os.write(write_fd, partial)
    proc = SimpleNamespace(stdout=stream, stdin=io.StringIO(), poll=lambda: None)
    host = PipeHost()
    host._process = None if startup else proc
    host._binary, host._workdir, host.settle_ms = tmp_path / "never-executed", tmp_path, 0
    host.started, host.reply_timeout_s, host.transcript = time.monotonic(), .02, tmp_path / "protocol.jsonl"
    host._log = None
    actual_event = M.event
    def broken_transcript(path, record):
        if record["event"] == "request" and record.get("command") != {"quit": True}:
            return actual_event(path, record)
        raise OSError("transcript became unwritable")
    monkeypatch.setattr(M, "event", broken_transcript)
    monkeypatch.setattr(M.subprocess, "Popen", lambda *a, **kw: proc)
    monkeypatch.setattr(RP, "preset_edits", lambda *a: (1, base_command()["edits"]))
    def render(*a):
        if startup:
            host._ensure_server()
        else:
            host._exchange({"synthetic": True})
        pytest.fail("stalled partial reply accepted")
    monkeypatch.setattr(M, "full_render", render)
    try:
        with pytest.raises(TimeoutError, match="complete protocol line") as raised:
            M.render_chain(tmp_path / "chain", "clean", context(), {t["slug"]: np.ones(8) for t in panel()},
                           time.monotonic(), host_factory=lambda *a: host)
        assert host.closed
        # Both independently attempted paths retain evidence, not just exception context.
        for name in ("partial.json", "protocol-fallback.json"):
            saved = (tmp_path / "chain" / name).read_text()
            assert "TimeoutError" in saved and partial.hex() in saved
            assert "transcript became unwritable" in saved
            json.loads(saved)  # No self-referential evidence cycle.
        original = M.failure(raised.value)
        assert original["type"] == "TimeoutError" and partial.hex() in json.dumps(original)
    finally:
        stream.close()
        os.close(write_fd)
        if host._log is not None:
            host._log.close()


@pytest.mark.parametrize("fallback_fails", [False, True])
def test_save_hash_and_diagnostic_failures_keep_original_and_recovery(tmp_path, monkeypatch, fallback_fails):
    actual_write = M.write_json
    def write(path, value):
        if Path(path).name.endswith(".save-failure.json"):
            raise PermissionError("save diagnostic rejected")
        if fallback_fails and Path(path).name.endswith(".save-fallback.json"):
            raise OSError("save fallback rejected")
        return actual_write(path, value)
    monkeypatch.setattr(M, "write_json", write)
    monkeypatch.setattr(M.R, "sha", lambda *a: (_ for _ in ()).throw(OSError("original archive hash failure")))
    with pytest.raises(OSError, match="original archive hash failure") as raised:
        M.save_arrays(tmp_path / "returned.npz", returned=np.arange(4, dtype=np.float64))
    assert (tmp_path / "returned.npz.returned.recovery.npy").exists()
    actual_write(tmp_path / "outer-error.json", {"error": M.failure(raised.value)})
    saved = json.loads((tmp_path / "outer-error.json").read_text())["error"]
    assert saved["type"] == "OSError" and saved["message"] == "original archive hash failure"
    record = saved["processing_evidence"][0]
    assert record["recovery"] == {"returned": "saved"}
    assert record["diagnostic_error"]["message"] == "save diagnostic rejected"
    if fallback_fails:
        assert record["fallback_error"]["message"] == "save fallback rejected"
    else:
        assert json.loads((tmp_path / "returned.save-fallback.json").read_text())["recovery"] == {"returned": "saved"}
