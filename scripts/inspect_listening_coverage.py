#!/usr/bin/env python3
"""Inspect unequal listening-score coverage from frozen terms, without audio.

    python scripts/inspect_listening_coverage.py --record PRIVATE_KEY_OR_VERDICT.json

The result is a post-hoc sensitivity check, never an objective-agreement result.
It does not validate the original audio or change an immutable listening key.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.listening import common_term_sensitivity


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, type=pathlib.Path)
    args = parser.parse_args()
    record = json.loads(args.record.expanduser().read_text())
    for field in ("objective_record", "frozen_scored_record"):
        if field in record:
            record = record[field]
            break
    scoring = record.get("objective_scoring", record)
    print(json.dumps(common_term_sensitivity(scoring), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
