"""Build Swift helpers against a compatible installed macOS SDK."""

from __future__ import annotations

import pathlib
import shutil
import subprocess


def compile_swift(source: pathlib.Path, output: pathlib.Path):
    """Compile a helper, retrying real SDK directories after a toolchain mismatch.

    Command Line Tools updates can temporarily leave ``MacOSX.sdk`` pointing at
    an SDK produced by a different Swift build. A writable module cache and an
    older installed SDK keep the local verification tools usable without
    changing the selected developer directory for the whole machine.
    """
    compiler = shutil.which("swiftc")
    if compiler is None:
        return None, "swiftc not found. Install the Xcode command line tools."

    module_cache = output.parent / "swift-module-cache"
    base = [
        compiler,
        "-swift-version",
        "5",
        "-module-cache-path",
        str(module_cache),
        "-O",
        str(source),
        "-o",
        str(output),
    ]
    attempts = [base]
    sdk_root = pathlib.Path("/Library/Developer/CommandLineTools/SDKs")
    if sdk_root.is_dir():
        for sdk in sorted(sdk_root.glob("MacOSX*.sdk"), reverse=True):
            if sdk.is_symlink():
                continue
            attempts.append(base[:1] + ["-sdk", str(sdk)] + base[1:])

    last = None
    for command in attempts:
        last = subprocess.run(command, capture_output=True, text=True)
        if last.returncode == 0:
            return last, None
        if "SDK is not supported by the compiler" not in last.stderr:
            break
    return last, last.stderr if last is not None else "swiftc did not run"
