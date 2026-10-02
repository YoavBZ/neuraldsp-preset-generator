"""Build Swift helpers against a compatible installed macOS SDK."""

from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import tempfile


def _cache_root() -> pathlib.Path:
    """Where built helpers are kept between runs: ``$NDSP_SWIFT_CACHE`` if set."""
    configured = os.environ.get("NDSP_SWIFT_CACHE")
    if configured:
        return pathlib.Path(configured).expanduser()
    return pathlib.Path.home() / "Library" / "Caches" / "neuraldsp-preset-generator" / "swift"


FLAGS = ["-swift-version", "5", "-O"]
# Read by the cache key, with the compiler and SDKs: what selects the toolchain
# or the SDK a build is made against.
ENVIRONMENT = ("DEVELOPER_DIR", "SDKROOT", "TOOLCHAINS", "MACOSX_DEPLOYMENT_TARGET")


def compile_swift(source: pathlib.Path, output: pathlib.Path):
    """Compile a helper, retrying real SDK directories after a toolchain mismatch.

    Command Line Tools updates can temporarily leave ``MacOSX.sdk`` pointing at
    an SDK produced by a different Swift build. A writable module cache and an
    older installed SDK keep the local verification tools usable without
    changing the selected developer directory for the whole machine.

    A build is kept in a shared cache keyed by the source, the flags, the
    compiler's version, the installed SDKs and the toolchain-selecting
    environment, and copied to ``output`` from there. Every match used to compile
    the render server, and its module cache, from scratch — about a core's worth
    of CPU while several matches ran at once. Where the cache cannot be used (an
    unwritable cache, an unreadable source) the build goes straight to ``output``
    as it always did.
    """
    compiler = shutil.which("swiftc")
    if compiler is None:
        return None, "swiftc not found. Install the Xcode command line tools."

    sdk_root = pathlib.Path("/Library/Developer/CommandLineTools/SDKs")
    sdks = (sorted((sdk for sdk in sdk_root.glob("MacOSX*.sdk") if not sdk.is_symlink()),
                   reverse=True) if sdk_root.is_dir() else [])
    try:
        cached = _cached_path(compiler, source, sdks)
        if cached.is_file():
            _place(cached, output)
            return subprocess.CompletedProcess([compiler], 0, "", ""), None
        cached.parent.mkdir(parents=True, exist_ok=True)
        # Built under a private name and renamed into place, so two processes
        # building at once never see half a binary.
        staged = pathlib.Path(tempfile.mkdtemp(dir=cached.parent)) / cached.name
    except OSError:
        output = pathlib.Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        return _build(compiler, source, output, output.parent / "swift-module-cache", sdks)
    try:
        built, error = _build(compiler, source, staged,
                              _cache_root() / "module-cache", sdks)
        if error is None:
            os.replace(staged, cached)
            _place(cached, output)
        return built, error
    finally:
        shutil.rmtree(staged.parent, ignore_errors=True)


def _cached_path(compiler: str, source: pathlib.Path, sdks) -> pathlib.Path:
    version = subprocess.run([compiler, "--version"], capture_output=True, text=True)
    digest = hashlib.sha256()
    for part in (pathlib.Path(source).read_bytes(), compiler.encode(),
                 (version.stdout + version.stderr).encode(), " ".join(FLAGS).encode(),
                 "\n".join(str(sdk) for sdk in sdks).encode(),
                 "\n".join(f"{name}={os.environ.get(name, '')}"
                           for name in ENVIRONMENT).encode()):
        digest.update(part)
        digest.update(b"\0")
    return _cache_root() / digest.hexdigest() / pathlib.Path(source).stem


def _build(compiler, source, output, module_cache, sdks):
    """swiftc with the default SDK, then each real SDK after a toolchain mismatch."""
    base = [compiler, *FLAGS[:2], "-module-cache-path", str(module_cache), *FLAGS[2:],
            str(source), "-o", str(output)]
    attempts = [base] + [base[:1] + ["-sdk", str(sdk)] + base[1:] for sdk in sdks]
    last = None
    for command in attempts:
        last = subprocess.run(command, capture_output=True, text=True)
        if last.returncode == 0:
            return last, None
        if "SDK is not supported by the compiler" not in last.stderr:
            break
    return last, last.stderr if last is not None else "swiftc did not run"


def _place(cached: pathlib.Path, output: pathlib.Path) -> None:
    output = pathlib.Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cached, output)
