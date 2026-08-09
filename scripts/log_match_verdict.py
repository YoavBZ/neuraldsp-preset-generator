#!/usr/bin/env python3
"""Record which side won a template-versus-matched-candidate audition.

This writes the decision to the run's ``trials.sqlite3`` and appends the measured
context to the pack's user-owned ``learned-tones.md``. Audio is never copied.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import add_data_dir_arg, guarded, positive_int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", type=pathlib.Path, required=True,
                        help="completed match directory containing summary.json, "
                             "match-N.json, and trials.sqlite3")
    parser.add_argument("--candidate", type=positive_int, required=True,
                        help="shortlist candidate auditioned against the template")
    parser.add_argument(
        "--choice", required=True,
        choices=("candidate", "template", "indistinguishable"),
        help="which side won the A/B audition",
    )
    parser.add_argument("--listener", required=True,
                        help="listener or session name; one verdict per trial/name")
    parser.add_argument("--comment",
                        help="optional listening detail, for example '#2 is less harsh'")
    add_data_dir_arg(parser)
    return parser


def main() -> None:
    from match.verdict import record_verdict
    from packs.paths import data_root_warning, set_data_root

    args = build_parser().parse_args()
    set_data_root(args.data_dir)
    warning = data_root_warning()
    if warning:
        print(f"warning: {warning}", file=sys.stderr)
    recorded = record_verdict(
        args.run_dir, candidate_rank=args.candidate, choice=args.choice,
        listener=args.listener, comment=args.comment,
    )
    print(f"recorded {recorded.choice!r} for candidate {recorded.candidate} "
          f"as trial {recorded.trial_id} in run {recorded.run_id}")
    print(f"learned notes: {recorded.notes_path}")


if __name__ == "__main__":
    guarded(main)
