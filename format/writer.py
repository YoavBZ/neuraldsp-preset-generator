"""
Byte-level writer for Neural DSP preset files.

The token list produced by ``format.parser.parse`` is enough to reconstruct the
original file byte-for-byte. To mutate a preset, change a token's ``value``
field (only the string body) and call ``write()``. Marker bytes are preserved
verbatim, which keeps the wrapper structure exactly as the plugin expects.

The writer never recomputes marker bytes from scratch. The value-type markers
in the Morgan format are undocumented; recomputing them risks corrupting the
file. The template-based approach sidesteps this entirely.
"""

from __future__ import annotations

import os
import tempfile
from typing import Iterable

from .parser import Token


def write(tokens: Iterable[Token]) -> bytes:
    """Serialize a token sequence back to the preset binary format."""
    return b"".join(tok.to_bytes() for tok in tokens)


def write_file(path: str, tokens: Iterable[Token]) -> None:
    """Write a preset so the path holds either the old file or the new one.

    Written beside the target and renamed over it. Opening the target itself
    truncated it first, so an interrupted `--force` into the plugin's preset
    folder left a cut-off preset where a working one had been.
    """
    data = write(tokens)
    directory = os.path.dirname(os.path.abspath(path))
    handle, temp = tempfile.mkstemp(prefix=".preset-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(handle, "wb") as f:
            f.write(data)
        # mkstemp creates the file 0600; a preset should get the permissions
        # any other new file here would.
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(temp, 0o666 & ~umask)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise

