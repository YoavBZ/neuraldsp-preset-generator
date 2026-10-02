"""Swift helpers are built once per source, compiler and SDK set, then copied."""

from __future__ import annotations

import pathlib
import stat
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import _swift  # noqa: E402

FAKE = """#!/bin/sh
echo "$@" >> "$FAKE_SWIFTC_LOG"
if [ "$1" = "--version" ]; then echo "fake swift 1.0"; exit 0; fi
while [ $# -gt 0 ]; do
  if [ "$1" = "-o" ]; then shift; printf 'built' > "$1"; fi
  shift
done
"""


def _fake_compiler(tmp_path, monkeypatch):
    compiler = tmp_path / "swiftc"
    compiler.write_text(FAKE)
    compiler.chmod(compiler.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "calls.log"
    monkeypatch.setenv("FAKE_SWIFTC_LOG", str(log))
    monkeypatch.setenv("NDSP_SWIFT_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(_swift.shutil, "which", lambda name: str(compiler))
    return log


def _compiles(log):
    return sum(1 for line in log.read_text().splitlines() if "-o" in line.split())


def test_a_second_build_of_the_same_source_is_copied_not_compiled(tmp_path, monkeypatch):
    log = _fake_compiler(tmp_path, monkeypatch)
    source = tmp_path / "au_render_server.swift"
    source.write_text("print(1)\n")
    for run in ("one", "two"):
        built, error = _swift.compile_swift(source, tmp_path / run / "au_render_server")
        assert error is None and built.returncode == 0
        assert (tmp_path / run / "au_render_server").read_text() == "built"
    assert _compiles(log) == 1
    # The module cache is shared too, not one per output directory.
    assert any(str(tmp_path / "cache" / "module-cache") in line
               for line in log.read_text().splitlines())


def test_a_changed_source_is_compiled_again(tmp_path, monkeypatch):
    log = _fake_compiler(tmp_path, monkeypatch)
    source = tmp_path / "au_probe.swift"
    source.write_text("print(1)\n")
    _swift.compile_swift(source, tmp_path / "a" / "au_probe")
    source.write_text("print(2)\n")
    _swift.compile_swift(source, tmp_path / "b" / "au_probe")
    assert _compiles(log) == 2
    # No half-built leftovers in the cache.
    leftovers = [p for p in (tmp_path / "cache").rglob("*")
                 if p.is_dir() and p.name.startswith("tmp")]
    assert leftovers == []
