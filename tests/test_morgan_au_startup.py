"""Generated pipe/process checks only: no installed plugin or study assets."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from scripts import check_morgan_au_startup as M


def test_draft_guard_blocks_before_build_or_instance(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "ROOT", tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / M.PLAN).write_text("DRAFT\n## Frozen design\nsourceonly\n")
    monkeypatch.setattr(M.subprocess, "check_output", lambda *a, **k: pytest.fail("git/asset access before draft rejection"))
    with pytest.raises(ValueError, match="declaration"):
        M.guard()


@pytest.mark.parametrize("kind", ["complete", "partial", "eof", "oversize"])
def test_complete_pipe_reply_deadline_and_partial_preservation(kind):
    read_fd, write_fd = os.pipe()
    stream = os.fdopen(read_fd, "rb")
    payload = b'{"ready":true}\n' if kind == "complete" else b'{"ready":'
    os.write(write_fd, payload)
    if kind == "eof":
        os.close(write_fd)
        write_fd = None
    raw = bytearray()
    try:
        if kind == "complete":
            assert M.read_line(stream, raw, timeout=.02) == payload
        else:
            with pytest.raises(TimeoutError if kind == "partial" else ValueError):
                M.read_line(stream, raw, timeout=.02, cap=2 if kind == "oversize" else 100)
            assert bytes(raw) == (payload[:3] if kind == "oversize" else payload)
    finally:
        stream.close()
        if write_fd is not None:
            os.close(write_fd)


class CapturedInput(io.BytesIO):
    def close(self):
        if not self.closed:
            self.sent = self.getvalue()
        super().close()


class Process:
    def __init__(self, stdout, wait_fails=False):
        self.stdin, self.stdout = CapturedInput(), stdout
        self.code, self.waits, self.kills = None, [], 0
        self.wait_fails = wait_fails
    def poll(self):
        return self.code
    def wait(self, timeout=None):
        self.waits.append(timeout)
        if self.wait_fails and len(self.waits) == 1:
            raise subprocess.TimeoutExpired("synthetic", timeout)
        self.code = 0 if not self.kills else -9
        return self.code
    def kill(self):
        self.kills += 1


@pytest.mark.parametrize("wait_fails", [False, True])
def test_shutdown_quit_and_bounded_kill_reaping(wait_fails):
    proc = Process(io.BytesIO(), wait_fails)
    result = M.stop_process(proc)
    assert result["stopped"] and proc.stdin.sent == b'{"quit":true}\n'
    assert proc.stdin.closed and proc.stdout.closed
    assert proc.waits == ([10, 10] if wait_fails else [10])
    assert proc.kills == int(wait_fails)
    assert bool(result["errors"]) == wait_fails


def test_quit_failure_does_not_skip_close_wait():
    proc = Process(io.BytesIO())
    proc.stdin.write = lambda *a: (_ for _ in ()).throw(OSError("broken input"))
    result = M.stop_process(proc)
    assert result["stopped"] and proc.stdin.closed and proc.stdout.closed
    assert result["errors"][0]["message"] == "broken input" and proc.waits == [10]


@pytest.mark.parametrize("kind", ["ready", "invalid", "partial", "launch-log-error", "source-drift", "stderr-errors", "compile-failure", "compile-timeout"])
def test_execute_no_render_commands_and_retained_errors(tmp_path, monkeypatch, kind):
    # Compile and OS process creation are replaced before execute is called.
    builds = []
    def build(command, **kwargs):
        builds.append(command)
        assert command[0] == "/usr/bin/swiftc" and command[3:5] == ["-sdk", M.SDK]
        assert kwargs == {"capture_output": True, "timeout": 120}
        if kind == "compile-timeout":
            raise subprocess.TimeoutExpired(command, 120, output=b"partial\xff", stderr=b"compiler timeout")
        Path(command[-1]).write_bytes(b"synthetic binary never executed")
        return subprocess.CompletedProcess(command, 1 if kind == "compile-failure" else 0, b"", b"compile rejected" if kind == "compile-failure" else b"")
    monkeypatch.setattr(M.subprocess, "run", build)
    for name in ("DEVELOPER_DIR", "SDKROOT", "TOOLCHAINS", "MACOSX_DEPLOYMENT_TARGET"):
        monkeypatch.delenv(name, raising=False)
    r, w = os.pipe()
    stream = os.fdopen(r, "rb")
    payload = b'{"ready":true,"version":"test-only"}\n' if kind != "invalid" else b'{"ready":true,"version":"unknown"}\n'
    if kind == "partial":
        payload = b'{"ready":'
    os.write(w, payload)
    proc = Process(stream)
    calls = []
    def launch(command, **kwargs):
        calls.append(command)
        assert command == [str(tmp_path / "morgan_au_startup")]
        assert kwargs["stdin"] == subprocess.PIPE and kwargs["stdout"] == subprocess.PIPE
        return proc
    monkeypatch.setattr(M.subprocess, "Popen", launch)
    monkeypatch.setattr(M, "REPLY_SECONDS", .02)
    monkeypatch.setattr(M, "committed", lambda name: "changed" if kind == "source-drift" else "sha")
    monkeypatch.setattr(M.subprocess, "check_output", lambda *a, **k: "synthetic\n")
    actual_write = M.write_json
    def write(path, value):
        if kind == "launch-log-error" and Path(path).name == "launch.json":
            raise OSError("launch log rejected")
        actual_write(path, value)
    monkeypatch.setattr(M, "write_json", write)
    log_handles = []
    if kind == "stderr-errors":
        actual_open = Path.open
        class BrokenLog:
            def flush(self):
                raise OSError("flush rejected")
            def fileno(self):
                raise OSError("fileno rejected")
            def close(self):
                self.closed = True
        def opened(path, *args, **kwargs):
            if path.name == "server.log":
                handle = BrokenLog()
                handle.closed = False
                log_handles.append(handle)
                return handle
            return actual_open(path, *args, **kwargs)
        monkeypatch.setattr(Path, "open", opened)
    try:
        result = M.execute(tmp_path, time.monotonic(), {"pins": {"source": "sha"}, "revision": "synthetic"})
        assert result["complete"] and result["no_render_or_model"]
        assert result["partial_raw_hex"] == (b"" if kind in ("launch-log-error", "compile-failure", "compile-timeout") else payload).hex()
        assert result["disposition"] == ("READY" if kind == "ready" else "INCONCLUSIVE")
        assert len(builds) == 1
        assert len(calls) == (0 if kind in ("launch-log-error", "compile-failure", "compile-timeout") else 1)
        if kind == "compile-timeout":
            assert result["compile"]["stdout_hex"] == b"partial\xff".hex()
            assert result["error"]["type"] == "TimeoutExpired"
        if kind == "compile-failure":
            assert result["compile"]["returncode"] == 1
        if calls:
            assert proc.stdin.sent == b'{"quit":true}\n'
            assert proc.stdin.closed and proc.stdout.closed
        if kind == "partial":
            assert result["error"]["type"] == "TimeoutError"
        if kind == "source-drift":
            assert result["evidence_errors"][0]["message"] == "source drift after startup"
        if kind == "stderr-errors":
            assert log_handles[0].closed
            assert [e["message"] for e in result["evidence_errors"]] == ["flush rejected", "fileno rejected"]
        actual_write(tmp_path / "outer-report.json", result)
        assert json.loads((tmp_path / "outer-report.json").read_text())["disposition"] == result["disposition"]
    finally:
        stream.close()
        os.close(w)


@pytest.mark.parametrize("kind", ["ready", "publish-timeout", "withdrawal-and-log-errors"])
def test_main_publication_retains_original_and_combined_errors(tmp_path, monkeypatch, capsys, kind):
    monkeypatch.setattr(M, "ROOT", tmp_path)
    monkeypatch.setattr(M, "OUTPUT", "output")
    monkeypatch.setattr(M, "guard", lambda: {})
    monkeypatch.setattr(M.sys, "argv", ["synthetic"])
    monkeypatch.setattr(M, "execute", lambda *args: {"disposition": "READY"})
    calls = []
    def budget(*args):
        calls.append(1)
        if kind != "ready" and len(calls) == 2:
            raise TimeoutError("publication timeout")
    monkeypatch.setattr(M, "deadline", budget)
    actual_rename, actual_write = Path.rename, M.write_json
    def renamed(path, target):
        if kind == "withdrawal-and-log-errors" and Path(target).name.startswith("failed-result"):
            raise OSError("withdrawal rejected")
        return actual_rename(path, target)
    def write(path, value):
        if kind == "withdrawal-and-log-errors" and Path(path).name == "failed-finalization.json":
            raise OSError("failure log rejected")
        return actual_write(path, value)
    monkeypatch.setattr(Path, "rename", renamed)
    monkeypatch.setattr(M, "write_json", write)
    if kind == "ready":
        assert M.main() == 0
        assert json.loads((tmp_path / "output/result.json").read_text())["disposition"] == "READY"
    else:
        with pytest.raises(TimeoutError, match="publication timeout"):
            M.main()
        fallback = json.loads(capsys.readouterr().err)
        assert fallback["disposition"] == "INCONCLUSIVE"
        assert fallback["finalization_error"]["message"] == "publication timeout"
        if kind == "withdrawal-and-log-errors":
            assert fallback["withdrawal_errors"][0]["message"] == "withdrawal rejected"
            assert fallback["failure_log_errors"][0]["message"] == "failure log rejected"
        else:
            assert not (tmp_path / "output/result.json").exists()
            assert (tmp_path / "output/failed-result.provisional.json").exists()


@pytest.mark.parametrize("kind", ["valid", "pin-drift", "body-drift", "review-drift", "uncommitted"])
def test_guard_exact_declaration_sources_and_review(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(M, "ROOT", tmp_path)
    monkeypatch.setattr(M.sys, "prefix", str(tmp_path / ".venv"))
    names = [*M.SOURCES, M.REVIEW, M.PLAN]
    for name in names:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    for name in M.SOURCES:
        data = '{"audio_unit":{"type":"aumf","subtype":"NMAS","manufacturer":"NDSP"}}' if name.endswith("manifest.json") else name
        (tmp_path / name).write_text(data)
    pins = {name: M.sha((tmp_path / name).read_bytes()) for name in M.SOURCES}
    body = "synthetic design\n"
    body_hash = M.sha(body.encode())
    (tmp_path / M.REVIEW).write_text("Verdict: APPROVE\n" + "\n".join([*pins.values(), body_hash]))
    approval = {"status": "DECLARED", "review": M.REVIEW, "review_sha256": M.sha((tmp_path / M.REVIEW).read_bytes()),
                "no_instance_before_declaration": True, "pins": pins, "body_sha256": body_hash}
    if kind == "pin-drift":
        approval["pins"][M.SOURCES[0]] = "changed"
    if kind == "body-drift":
        body += "changed"
    if kind == "review-drift":
        approval["review_sha256"] = "changed"
    (tmp_path / M.PLAN).write_text("<!-- startup-approval\n" + json.dumps(approval) + "\nstartup-approval -->\n## Frozen design\n" + body)
    snapshot = {name: (tmp_path / name).read_bytes() for name in names}
    if kind == "uncommitted":
        (tmp_path / M.SOURCES[0]).write_text("uncommitted change")
    def git(command, **kwargs):
        if command[1] == "show":
            return snapshot[command[2][5:]]
        assert command == ["git", "rev-parse", "HEAD"]
        return "synthetic\n"
    monkeypatch.setattr(M.subprocess, "check_output", git)
    if kind == "valid":
        result = M.guard()
        assert len(result["pins"]) == 6 and result["revision"] == "synthetic"
    else:
        with pytest.raises(ValueError, match="drift|review|uncommitted"):
            M.guard()
