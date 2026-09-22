"""Score explicit private listening records without rendering or altering verdicts.

    python scripts/score_listening.py --manifest comparisons.json --out-dir audit

The manifest contains a `comparisons` list. Each entry declares id, target_id,
reference and alternatives A/B (path, sha256, optional start_s/duration_s/gain_db/
mono), listening_context, and optional verdict (closer/preferred). Reference
regime is explicit. Records and results belong in private storage, not Git.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _cli import guarded
from build_rab_audition import _write_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=pathlib.Path)
    parser.add_argument("--out-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    from analysis.listening import agreement_report, score_record, sha256
    manifest = json.loads(args.manifest.read_text())
    comparisons = manifest["comparisons"]
    if len({row["id"] for row in comparisons}) != len(comparisons):
        raise ValueError("duplicate comparison ids")
    if any(not row.get("target_id") for row in comparisons):
        raise ValueError("each comparison needs target_id (or explicit unassigned)")
    if args.out_dir.exists():
        raise ValueError("use a new output directory; prior audits are immutable")
    args.out_dir.mkdir(parents=True)
    rows, cache = [], {}
    for index, comparison in enumerate(comparisons):
        try:
            row = score_record(comparison, cache)
        except (OSError, ValueError, KeyError) as error:
            row = {key: value for key, value in comparison.items() if key not in ("objective_scoring", "agreement", "agreement_with_level", "scoring_error")}
            row["scoring_error"] = f"{type(error).__name__}: {error}"
        rows.append(row)
        _write_text(args.out_dir / f"comparison-{index + 1:03d}.json", json.dumps(row, indent=2, allow_nan=False) + "\n")
        print(f"{comparison['id']}: {'UNSCORED ' + row['scoring_error'] if 'scoring_error' in row else 'scored'}", flush=True)
    report = agreement_report(rows)
    report["with_level_sensitivity"] = agreement_report([
        {**row, "agreement": row.get("agreement_with_level", {})} for row in rows])
    report["manifest_sha256"] = sha256(args.manifest)
    report["comparison_count_not_independent_n"] = len(rows)
    report["scored_count"] = sum("objective_scoring" in row for row in rows)
    _write_text(args.out_dir / "report.json", json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    guarded(main)
