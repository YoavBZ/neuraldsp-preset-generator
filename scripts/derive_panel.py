#!/usr/bin/env python3
"""A preset panel limited to the presets stage 0b validated the judge on.

    python scripts/derive_panel.py --panel-dir ~/ndsp-presets/runs/kill/pr12 \\
        --out-dir ~/ndsp-presets/runs/kill/pr12-clean \\
        --lags-json ~/ndsp-presets/runs/kill/pr12-clean/judge-lags.json

Writes a panel folder whose `index.json` lists only the source panel's rows for its
factory presets that are not high-gain (`plan_listening_validation.high_gain`: a drive
pedal on, or the amp's volume above 0.75), template+R and the template. The rows point
at the source's render files; nothing is rendered or copied. A `panel-config.json`
records the source index's sha256 and the presets kept. `--lags-json` also writes the
judge's lag table for `kill_tests_judge.py --lags` from `docs/validation-lags.json`: each
part's recorded lag less the 52-sample latency, none for a part whose lag is ambiguous.
`docs/kill-tests-pr12-plan.md`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

LATENCY = 52


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, required=True)
    ap.add_argument("--out-dir", type=pathlib.Path, required=True)
    ap.add_argument("--lags-json", type=pathlib.Path)
    return ap


def kept_rows(index, high_gain):
    """The rows of `index` a clean panel keeps, and the factory presets it keeps."""
    amp = index["amp"]
    keep = {c for c in {r["candidate"] for r in index["rows"]}
            if not c.startswith("factory:") or not high_gain(f"{amp}:{c}")}
    rows = [r for r in index["rows"] if r["candidate"] in keep]
    return rows, sorted(c for c in keep if c.startswith("factory:"))


def judge_lags(lags_doc, parts):
    """{part: {"lag": recorded - latency}} for every part; a part whose lag is ambiguous
    or missing gets None and a reason, which the judge's script leaves out and lists."""
    out = {}
    for p in sorted(parts):
        row = lags_doc["parts"].get(p)
        if row is None:
            out[p] = {"lag": None, "reason": "no recorded lag"}
        elif row["ambiguous"]:
            out[p] = {"lag": None, "reason": "its recorded lag is ambiguous"}
        else:
            out[p] = {"lag": row["lag_samples"] - LATENCY, "window_ms": None}
    return out


def main():
    args = build_parser().parse_args()
    from benchmark_recordings import LAGS
    from plan_listening_validation import high_gain

    source = args.panel_dir.expanduser()
    raw = (source / "index.json").read_bytes()
    index = json.loads(raw)
    rows, presets = kept_rows(index, high_gain)
    out = args.out_dir.expanduser()
    if out.exists() and any(out.iterdir()):
        die(f"{out} is not empty")
    out.mkdir(parents=True, exist_ok=True)
    config = {"source_panel": str(args.panel_dir),
              "source_index_sha256": hashlib.sha256(raw).hexdigest(),
              "rule": "factory presets with no drive pedal and amp volume <= 0.75",
              "factory_presets": presets}
    (out / "panel-config.json").write_text(json.dumps(config, indent=1) + "\n")
    (out / "index.json").write_text(json.dumps({**{k: v for k, v in index.items() if k != "rows"},
                                                "derived_from": config, "rows": rows},
                                               indent=1) + "\n")
    print(f"{len(presets)} factory presets kept, {len(rows)} rows")
    if args.lags_json:
        lags_doc = json.loads(LAGS.read_text())
        parts = {r["part"] for r in rows}
        table = {"panel": str(args.out_dir),
                 "source": "docs/validation-lags.json, recorded lag less the 52-sample "
                           "latency; parts whose lag is ambiguous have none",
                 "lags_sha256": hashlib.sha256(LAGS.read_bytes()).hexdigest(),
                 "lags": judge_lags(lags_doc, parts), "alternate": {}}
        args.lags_json.expanduser().write_text(json.dumps(table, indent=1) + "\n")
        print(f"{sum(v['lag'] is not None for v in table['lags'].values())} of "
              f"{len(table['lags'])} parts with a lag")


if __name__ == "__main__":
    guarded(main)
