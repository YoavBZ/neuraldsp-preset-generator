#!/usr/bin/env python3
"""Copy a declared template byte-for-byte when a match recommends no improvement."""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from scripts._cli import guarded
from research.score_listening import _require_private_out_dir


def copy(template: pathlib.Path, out: pathlib.Path) -> None:
    template = template.expanduser().resolve()
    out = out.expanduser().absolute()
    _require_private_out_dir(out.parent)
    if not template.is_file() or out.exists() or out.is_symlink():
        raise ValueError("template must exist and output must be a new private path")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".declared-template-", dir=out.parent,
                                     delete=False) as staged:
        staged_path = pathlib.Path(staged.name)
    try:
        shutil.copyfile(template, staged_path)
        # Hard-link publication fails if another process claimed the output;
        # os.rename would silently overwrite it after the existence check.
        os.link(staged_path, out)
    finally:
        staged_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    copy(args.template, args.out)


if __name__ == "__main__":
    guarded(main)
