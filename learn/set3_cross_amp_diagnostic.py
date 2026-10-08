"""Declared development-only cross-amp diagnostic. Review/commit before execution.

Existing scores only; no audio, model, rendering or plugin imports. Candidate
identities stay tuples internally and become JSON arrays, never colliding ID strings.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import sys
import traceback

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from learn import set3_diagnostic as D
from learn import set3_rank_calibration as R

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/set3-cross-amp-diagnostic-plan.md"
COUNTS = {"sw50r": 45, "pr12": 35, "ac20": 31}


def flatten(distances, slug, bs, kind, menus):
    return {(amp, name): distances[slug][f"{bs}|{amp}|{kind}"][name]
            for amp in sorted(menus) for name in sorted(menus[amp])}


def constants(parts, A, names, inclusive):
    result = {}
    for band in sorted({p["band"] for p in parts}):
        training = sorted(p["slug"] for p in parts if p["band"] != band)
        eligible, excluded = {}, []
        for candidate in names:
            if candidate[1] == D.TEMPLATE and not inclusive:
                continue
            missing = [s for s in training if not D.raw_valid(A[s][candidate])]
            if not training or missing:
                excluded.append({"candidate": candidate, "invalid_training_parts": missing,
                                 "reason": "missing_raw_A" if training else "no_training_parts"})
            else:
                eligible[candidate] = statistics.median(A[s][candidate] for s in training)
        result[band] = {"candidate": D.best(eligible), "training_parts": training,
                        "eligible_medians_raw_A": [{"candidate": c, "median": eligible[c]}
                                                   for c in sorted(eligible)],
                        "excluded_candidates": excluded}
    return result


def net_choice(A, fallback):
    pick = D.best(A)
    all_null = bool(A) and all(v is None for v in A.values())
    return {"candidate": fallback if all_null else pick,
            "fallback_attempted": all_null,
            "fallback_used": all_null and fallback is not None,
            "missing_reason": ("all_raw_A_null_and_no_constant" if all_null and fallback is None
                               else "no_valid_raw_A" if not all_null and pick is None else None)}


def comparison(rows, numerator, denominator):
    result = D.summarize(rows, numerator, denominator)
    result["raw_counts"] = {"win": 0, "loss": 0, "tie": 0, "refusal": 0}
    for row in rows:
        a, b = row["B"][numerator], row["B"][denominator]
        kind = ("refusal" if not D.raw_valid(a) or not D.raw_valid(b)
                else "win" if a < b else "loss" if a > b else "tie")
        result["raw_counts"][kind] += 1
    return result


def margin_gates(c):
    effect, p = c["band_median_log_ratio"], c["sign_flip_p_two_sided"]
    return {"complete_positive": not c["numeric_summaries_descriptive_only"],
            "five_percent_margin": effect is not None and effect <= math.log(.95),
            "sign_flip_below_point_one": p is not None and p < .1}


def summarize_cell(rows, factory, inclusive, names):
    pairs = [("pooled_known_di", d) for d in ("sw50r_known_di", "constant", "inclusive_constant")]
    pairs += [("pooled_net", d) for d in ("sw50r_net", "constant", "inclusive_constant",
                                        "pooled_known_di", "pooled_net_historical")]
    pairs += [("hindsight_amp_net", "sw50r_net"), ("hindsight_amp_net", "pooled_net"),
              ("hindsight_menu_B", "pooled_known_di")]
    comparisons = {f"{a}_vs_{b}": comparison(rows, a, b) for a, b in pairs}
    headroom = margin_gates(comparisons["pooled_known_di_vs_sw50r_known_di"])
    headroom["wins_above_half"] = comparisons["pooled_known_di_vs_sw50r_known_di"]["band_weighted_win_share"] > .5
    net_gates = {f"{base}_{key}": value for base in ("sw50r_net", "constant", "inclusive_constant")
                 for key, value in margin_gates(comparisons[f"pooled_net_vs_{base}"]).items()}
    joint = {}
    for band in sorted({r["band"] for r in rows}):
        subset = [r for r in rows if r["band"] == band]
        wins = sum(all(D.raw_win(r["B"]["pooled_net"], r["B"][b])
                       for b in ("sw50r_net", "constant", "inclusive_constant")) for r in subset)
        joint[band] = {"wins": wins, "required_parts": len(subset), "share": wins / len(subset)}
    joint_share = statistics.mean(v["share"] for v in joint.values())
    net_gates["joint_wins_above_half"] = joint_share > .5
    oracle = comparisons["hindsight_amp_net_vs_sw50r_net"]
    oracle_effect = oracle["band_median_log_ratio"]
    oracle_gates = {"all_three_picks_raw_scorable": all(not r["hindsight_amp_unscorable_policies"] for r in rows),
                    "complete_positive_pairs": not oracle["numeric_summaries_descriptive_only"],
                    "five_percent_headroom": oracle_effect is not None and oracle_effect <= math.log(.95)}
    methods = list(rows[0]["picks"])
    return {"parts": len(rows), "bands": len(joint), "menu_size": len(names), "rows": rows,
            "factory_constants_by_excluded_band": factory,
            "inclusive_constants_by_excluded_band": inclusive, "comparisons": comparisons,
            "headroom_gates": headroom, "headroom_observed": all(headroom.values()),
            "net_improvement_gates": net_gates, "net_improvement_observed": all(net_gates.values()),
            "fixed_net_pick_headroom_gates": oracle_gates,
            "fixed_net_pick_headroom_observed": all(oracle_gates.values()),
            "joint_wins": {"by_band": joint, "share": joint_share},
            "chosen_amp_counts": {m: {amp: sum(r["picks"][m] is not None and r["picks"][m][0] == amp
                                                   for r in rows) for amp in sorted(COUNTS)} for m in methods},
            "fallback_counts": {m: sum(r["net_audits"][m]["fallback_used"] for r in rows)
                                for m in rows[0]["net_audits"]},
            "fallback_parts": {m: [r["part"] for r in rows if r["net_audits"][m]["fallback_used"]]
                               for m in rows[0]["net_audits"]},
            "missing_selections": {m: [r["part"] for r in rows if r["picks"][m] is None] for m in methods},
            "missing_chosen_B": {m: [r["part"] for r in rows if not D.raw_valid(r["B"][m])] for m in methods},
            "zero_chosen_B": {m: [r["part"] for r in rows if D.raw_valid(r["B"][m]) and r["B"][m] == 0]
                              for m in methods},
            "known_net_agreement": {"same": sum(r["picks"]["pooled_known_di"] is not None and
                                               r["picks"]["pooled_known_di"] == r["picks"]["pooled_net"] for r in rows),
                                    "original_denominator": len(rows)},
            "hindsight_full_menu_raw_scorable": all(not r["hindsight_menu_refused_candidates"] for r in rows),
            "hindsight_all_three_net_picks_raw_scorable": all(not r["hindsight_amp_unscorable_policies"] for r in rows)}


def cell(distances, parts, bs, menus):
    names = sorted((amp, name) for amp in menus for name in menus[amp])
    A = {p["slug"]: flatten(distances, p["slug"], bs, "measure_A", menus) for p in parts}
    net = {p["slug"]: flatten(distances, p["slug"], bs, "net_A", menus) for p in parts}
    factory, inclusive = constants(parts, A, names, False), constants(parts, A, names, True)
    frozen = {}
    for part in parts:
        slug, band = part["slug"], part["band"]
        fallback = factory[band]["candidate"]
        audits = {"pooled_net": net_choice(net[slug], fallback)}
        audits.update({f"{amp}_net": net_choice({c: v for c, v in net[slug].items() if c[0] == amp}, fallback)
                       for amp in sorted(menus)})
        picks = {m: audit["candidate"] for m, audit in audits.items()}
        picks.update({"pooled_known_di": D.best(A[slug]),
                      "sw50r_known_di": D.best({c: v for c, v in A[slug].items() if c[0] == "sw50r"}),
                      "constant": fallback, "inclusive_constant": inclusive[band]["candidate"],
                      "pooled_net_historical": D.best(net[slug]),
                      "sw50r_net_historical": D.best({c: v for c, v in net[slug].items() if c[0] == "sw50r"})})
        frozen[slug] = (picks, audits)
    # Every A-based policy has been frozen before consulting any evaluation B.
    rows = []
    for part in sorted(parts, key=lambda p: p["slug"]):
        slug = part["slug"]
        b = flatten(distances, slug, bs, "measure_B", menus)
        picks, audits = frozen[slug]
        amp_scores = {picks[f"{amp}_net"]: b.get(picks[f"{amp}_net"])
                      for amp in sorted(menus) if picks[f"{amp}_net"] is not None}
        picks["hindsight_amp_net"], picks["hindsight_menu_B"] = D.best(amp_scores), D.best(b)
        rows.append({"part": slug, "band": part["band"], "picks": picks, "net_audits": audits,
                     "B": {m: b.get(c) for m, c in picks.items()},
                     "hindsight_menu_refused_candidates": [c for c, v in b.items() if not D.raw_valid(v)],
                     "hindsight_menu_zero_candidates": [c for c, v in b.items() if v == 0],
                     "hindsight_amp_missing_policies": [amp for amp in sorted(menus) if picks[f"{amp}_net"] is None],
                     "hindsight_amp_refused_B_policies": [amp for amp in sorted(menus)
                                                         if picks[f"{amp}_net"] is not None
                                                         and not D.raw_valid(b.get(picks[f"{amp}_net"]))],
                     "hindsight_amp_zero_B_policies": [amp for amp in sorted(menus)
                                                      if b.get(picks[f"{amp}_net"]) == 0],
                     "hindsight_amp_unscorable_policies": [amp for amp in sorted(menus)
                                                           if not D.raw_valid(b.get(picks[f"{amp}_net"]))]})
    return summarize_cell(rows, factory, inclusive, names)


def analyze(distances, metadata, inventory):
    parts = R.select_parts(metadata)
    menus = inventory["menus"]
    if {a: len(menus[a]) for a in menus} != COUNTS:
        raise ValueError("expected frozen 45/35/31 candidate inventories")
    D.validate(distances, parts, menus)
    cells = {bs: cell(distances, parts, bs, menus) for bs in D.BAND_SETS}
    headroom = all(c["headroom_observed"] for c in cells.values())
    net_improved = all(c["net_improvement_observed"] for c in cells.values())
    fixed_headroom = all(c["fixed_net_pick_headroom_observed"] for c in cells.values())
    return {"scope": "exploratory development cross-amp diagnostic, not confirmation or release",
            "parts": len(parts), "bands": len({p["band"] for p in parts}),
            "candidate_inventory": sorted((a, n) for a in menus for n in menus[a]),
            "cells": cells, "headroom_both_band_sets": headroom,
            "net_improvement_both_band_sets": net_improved,
            "fixed_net_pick_headroom_both_band_sets": fixed_headroom,
            "small_amp_selector_followup_supported": headroom and not net_improved and fixed_headroom,
            "limits": ["Development data reused; no generalization claim.",
                       "Known DI and B hindsight are unavailable product inputs.",
                       "Hindsight with refused candidates is best-scorable only.",
                       "Exact sign flips are exploratory sensitivity, not calibrated inference.",
                       "Amp-specific union support can differ under the same frozen distance primitive.",
                       "Standalone net policy labels can select a different amp through the shared fallback.",
                       "A-trained constants are declared baselines, not all possible song-blind policies.",
                       "Judge listening validation covers clear clean-to-crunch PR12 differences only.",
                       "Heavier-tone listening and fresh reserved confirmation remain required."]}


def run(report):
    R.note(report, "validating development-only sources and archived provenance")
    metadata = R.source_json(R.METADATA, report, "metadata")
    R.select_parts(metadata)
    inventory = R.source_json(R.INVENTORY, report, "menu_inventory")
    diagnostic = R.source_json(R.DIAGNOSTIC, report, "full_development_diagnostic")
    verification = R.source_json(R.VERIFICATION, report, "independent_verification")
    for label, path in (("script", Path(__file__).resolve()), ("tests", ROOT / "tests/test_set3_cross_amp_diagnostic.py"),
                        ("plan", PLAN), ("source_diagnostic_code", ROOT / "learn/set3_diagnostic.py"),
                        ("source_diagnostic_plan", ROOT / "docs/set3-development-diagnostic-plan.md"),
                        ("source_calibration_code", ROOT / "learn/set3_rank_calibration.py")):
        report["inputs"][label] = {"path": str(path), "sha256": R.digest(path)}
    distances = R.source_json(R.DISTANCES, report, "distances")
    R.validate_provenance(report, diagnostic, verification)
    R.note(report, "provenance matches; computing declared pooled-menu diagnostic")
    report.update(analyze(distances, metadata, inventory))
    for entry in report["inputs"].values():
        if R.digest(Path(entry["path"])) != entry["sha256"]:
            raise ValueError(f"source changed during execution: {entry['path']}")
    report["status"] = "complete"
    R.note(report, "completed cross-amp development diagnostic")


def execute(output):
    output = R.output_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"status": "running", "inputs": {}, "log": [],
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "runtime": {"python": sys.version, "executable": sys.executable}}
    with output.open("x") as stream:
        try:
            run(report)
        except BaseException as exc:
            report["status"] = "execution_error"
            report["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
            R.note(report, f"execution failed; retaining report at {output}: {exc}")
            raise
        finally:
            report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    execute(parser.parse_args().out)


if __name__ == "__main__":
    main()
