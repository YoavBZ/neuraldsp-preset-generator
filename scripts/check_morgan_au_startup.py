"""One declared Morgan startup/metadata/shutdown check. Never renders audio."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PLAN = "docs/morgan-au-startup-plan.md"
REVIEW = "docs/research/morgan-au-startup-review-2026-10-09.md"
OUTPUT = "tmp/morgan-au-startup-20261009"
SOURCES = ("scripts/check_morgan_au_startup.py", "tests/test_morgan_au_startup.py",
           "scripts/morgan_au_startup.swift", "packs/morgan/manifest.json")
TOTAL_SECONDS, COMPILE_SECONDS, REPLY_SECONDS, MAX_REPLY = 180, 120, 30, 1048576
SDK = "/Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def error_record(error):
    return {"type": type(error).__name__, "message": str(error)}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def write_json(path, value):
    with Path(path).open("x") as handle:
        handle.write(json.dumps(value, allow_nan=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def deadline(started, limit=TOTAL_SECONDS):
    if time.monotonic() - started >= limit:
        raise TimeoutError("cooperative startup check budget exhausted")


def committed(name):
    path = ROOT / name
    require(path.resolve() == path and path.is_file() and path.stat().st_nlink == 1,
            "regular unaliased source required: " + name)
    data = path.read_bytes()
    require(data == subprocess.check_output(["git", "show", "HEAD:" + name], cwd=ROOT),
            "uncommitted source: " + name)
    return sha(data)


def guard():
    # Source/declaration metadata only; no binary, instance or dataset access.
    text = (ROOT / PLAN).read_text()
    marker = "<!-- startup-approval\n"
    require(marker in text, "committed fresh review and declaration required")
    approval = json.loads(text.split(marker, 1)[1].split("\nstartup-approval -->", 1)[0])
    require(approval.get("status") == "DECLARED" and approval.get("review") == REVIEW
            and approval.get("no_instance_before_declaration") is True,
            "fresh declaration attestation required")
    pins = {name: committed(name) for name in SOURCES}
    body_sha = sha(text.split("## Frozen design\n", 1)[1].encode())
    require(approval.get("pins") == pins and approval.get("body_sha256") == body_sha,
            "reviewed source/body drift")
    review_sha = committed(REVIEW)
    review = (ROOT / REVIEW).read_text()
    require(approval.get("review_sha256") == review_sha and "Verdict: APPROVE" in review
            and all(h in review for h in (*pins.values(), body_sha)), "exact fresh review required")
    pins[REVIEW], pins[PLAN] = review_sha, committed(PLAN)
    pack = json.loads((ROOT / "packs/morgan/manifest.json").read_text())["audio_unit"]
    require((pack["type"], pack["subtype"], pack["manufacturer"]) == ("aumf", "NMAS", "NDSP"),
            "fixed Morgan component drift")
    require(Path(sys.prefix).resolve() == ROOT / ".venv", "explicit helper environment required")
    return {"pins": pins, "revision": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}


def read_line(stream, raw, timeout=REPLY_SECONDS, cap=MAX_REPLY):
    """One complete OS-pipe line; caller owns partial bytes even on failure."""
    end = time.monotonic() + timeout
    with selectors.DefaultSelector() as selector:
        selector.register(stream.fileno(), selectors.EVENT_READ)
        while not raw.endswith(b"\n"):
            remaining = end - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("complete startup reply deadline exhausted")
            chunk = os.read(stream.fileno(), 1)
            if not chunk:
                raise ValueError("startup EOF before complete reply")
            raw.extend(chunk)
            if len(raw) > cap:
                raise ValueError("startup reply exceeds byte cap")
    return bytes(raw)


def stop_process(process):
    """Attempt quit, close, bounded wait, kill and bounded reaping independently."""
    errors, actions = [], []
    if process is None:
        return {"stopped": True, "actions": [], "errors": []}
    try:
        alive = process.poll() is None
    except Exception as error:
        errors.append(error_record(error))
        alive = True
    if alive:
        for label, action in (("quit", lambda: (process.stdin.write(b'{"quit":true}\n'), process.stdin.flush())),
                              ("stdin-close", lambda: process.stdin.close())):
            try:
                action()
                actions.append(label)
            except Exception as error:
                errors.append(error_record(error))
        try:
            process.wait(timeout=10)
            actions.append("wait")
        except Exception as error:
            errors.append(error_record(error))
            try:
                process.kill()
                actions.append("kill")
            except Exception as second:
                errors.append(error_record(second))
            try:
                process.wait(timeout=10)
                actions.append("reap")
            except Exception as second:
                errors.append(error_record(second))
    for stream in (process.stdin, process.stdout):
        try:
            if stream is not None:
                stream.close()
        except Exception as error:
            errors.append(error_record(error))
    try:
        code = process.poll()
    except Exception as error:
        errors.append(error_record(error))
        code = None
    return {"stopped": code is not None, "returncode": code, "actions": actions, "errors": errors}


def execute(out, started, context):
    # Build only after declaration. No shared render server/compiler cache,
    # Neural DSP renderer, preset, waveform, model or scientific scorer.
    raw, process, stderr = bytearray(), None, None
    report = {"scope": "morgan-startup-metadata-only", "context": context,
              "no_render_or_model": True, "disposition": "INCONCLUSIVE", "complete": False}
    try:
        deadline(started)
        require(not any(os.environ.get(name) for name in
                ("DEVELOPER_DIR", "SDKROOT", "TOOLCHAINS", "MACOSX_DEPLOYMENT_TARGET")),
                "unexpected toolchain environment override")
        build_command = ["/usr/bin/swiftc", "-swift-version", "5", "-sdk", SDK,
                         "-module-cache-path", str(out / "swift-module-cache"), "-O",
                         str(ROOT / "scripts/morgan_au_startup.swift"), "-o", str(out / "morgan_au_startup")]
        write_json(out / "compile-command.json", {"command": build_command, "timeout_seconds": COMPILE_SECONDS,
                                                  "attempts": 1, "cache": False})
        try:
            built = subprocess.run(build_command, capture_output=True, timeout=COMPILE_SECONDS)
        except subprocess.TimeoutExpired as error:
            report["compile"] = {"returncode": None, "error": error_record(error),
                                 "stdout_hex": (error.stdout or b"").hex(), "stderr_hex": (error.stderr or b"").hex(),
                                 "stdout": (error.stdout or b"").decode(errors="replace") if isinstance(error.stdout, bytes) else error.stdout,
                                 "stderr": (error.stderr or b"").decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr}
            write_json(out / "compile.json", report["compile"])
            raise
        report["compile"] = {"returncode": built.returncode,
                             "stdout": built.stdout.decode(errors="replace"), "stderr": built.stderr.decode(errors="replace"),
                             "stdout_hex": built.stdout.hex(), "stderr_hex": built.stderr.hex()}
        write_json(out / "compile.json", report["compile"])
        deadline(started)
        require(built.returncode == 0, "startup probe build failed")
        report["binary_sha256"] = sha((out / "morgan_au_startup").read_bytes())
        command = [str(out / "morgan_au_startup")]
        write_json(out / "launch.json", {"command": command, "reply_seconds": REPLY_SECONDS,
                                         "only_subsequent_command": {"quit": True}})
        stderr = (out / "server.log").open("xb")
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr)
        response = read_line(process.stdout, raw, min(REPLY_SECONDS, max(.001, TOTAL_SECONDS - (time.monotonic()-started))))
        write_json(out / "startup-raw.json", {"raw_hex": raw.hex()})
        reply = json.loads(response)
        require(isinstance(reply, dict) and reply.get("ready") is True
                and isinstance(reply.get("version"), str) and reply["version"] not in ("", "unknown", "n/a"),
                "valid startup version/ready reply required")
        report["reply"] = reply
        deadline(started)
    except Exception as error:
        report["error"] = error_record(error)
    finally:
        report["partial_raw_hex"] = raw.hex()
        report["cleanup"] = stop_process(process)
        if stderr is not None:
            for action in (stderr.flush, lambda: os.fsync(stderr.fileno()), stderr.close):
                try:
                    action()
                except Exception as error:
                    report.setdefault("evidence_errors", []).append(error_record(error))
    try:
        deadline(started)
        require({name: committed(name) for name in context["pins"]} == context["pins"], "source drift after startup")
        require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
                == context["revision"], "HEAD drift after startup")
    except Exception as error:
        report.setdefault("evidence_errors", []).append(error_record(error))
    report["complete"] = True
    if ("error" not in report and not report.get("evidence_errors") and report["cleanup"]["stopped"]
            and not report["cleanup"]["errors"] and report["cleanup"].get("returncode") == 0):
        report["disposition"] = "READY"
    return report


def main():
    require(len(sys.argv) == 1, "no arbitrary commands, paths or overrides accepted")
    started = time.monotonic()
    context = guard()
    out = ROOT / OUTPUT
    require(out.resolve() == out, "unaliased output required")
    out.mkdir(exist_ok=False)
    report = execute(out, started, context)
    try:
        write_json(out / "result.pending.json", report)
        deadline(started)
        (out / "result.pending.json").rename(out / "result.json")
        deadline(started)
    except Exception as error:
        report["disposition"] = "INCONCLUSIVE"
        report["finalization_error"] = error_record(error)
        # Retain the original failure even when withdrawal or failure logging
        # also fails. A result alone is never authoritative: require successful
        # exit and absence of pending/provisional/failure records as well.
        try:
            if (out / "result.json").exists():
                (out / "result.json").rename(out / "failed-result.provisional.json")
        except Exception as second:
            report.setdefault("withdrawal_errors", []).append(error_record(second))
        try:
            write_json(out / "failed-finalization.json", report)
        except Exception as second:
            report.setdefault("failure_log_errors", []).append(error_record(second))
        print(json.dumps(report, allow_nan=False), file=sys.stderr, flush=True)
        raise
    return 0 if report["disposition"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
