# NOTE (2026-10-09): the large evidence files this closed study reads were moved out of git to
# ~/ndsp-presets/learn/codex-evidence/docs/ (docs/EVIDENCE-OUTSIDE-GIT.md). Copy them back
# under docs/ before re-running. See docs/codex-continuation-review.md for the study's verdict.
"""Fixed development-only nested preset-rank calibration.

See docs/set3-rank-calibration-plan.md. Review and commit precede actual execution.
Imports and synthetic tests never read development scores, audio, or arrays.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import traceback

# Also support execution as a file, without importing any audio/ML code.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from learn import set3_diagnostic as D

ROOT = Path(__file__).resolve().parents[1]
DISTANCES = D.DISTANCES
METADATA = D.METADATA
INVENTORY = D.MENU_INVENTORY
DIAGNOSTIC = ROOT / "docs/set3-development-diagnostic.json"
VERIFICATION = ROOT / "docs/set3-development-diagnostic-verification.json"
PLAN = ROOT / "docs/set3-rank-calibration-plan.md"
AMP = "sw50r"
BAND_SETS = D.BAND_SETS
TEMPLATE = D.TEMPLATE
ALPHAS = (0, 0.25, 0.5, 0.75, 1)
TIE_TOLERANCE = 1e-12
METHODS = ("calibration", "prior", "net", "historical_net", "constant",
           "inclusive_constant", "template", "true_di", "restricted_net")


def positive(value):
    return D.raw_valid(value) and value > 0


def select_parts(metadata):
    """Reject unknown membership, duplicates and overlap before reading scores."""
    parts = metadata["parts"]
    slugs = [p["slug"] for p in parts]
    if (len(set(slugs)) != len(slugs)
            or any(not isinstance(s, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", s)
                   for s in slugs)
            or any(p["split"] not in ("development", "held_out") for p in parts)
            or any(not isinstance(p["band"], str) or not p["band"] for p in parts)):
        raise ValueError("invalid or unknown part membership")
    development = sorted((p for p in parts if p["split"] == "development"),
                         key=lambda p: p["slug"])
    bands = {p["band"] for p in development}
    reserved = set(metadata["held_out_bands"])
    reserved.update(p["band"] for p in parts if p["split"] == "held_out")
    if len(development) != 33 or len(bands) != 11 or bands & reserved:
        raise ValueError("expected exactly 33 development parts in 11 unreserved bands")
    return development


def validate_scores(distances, parts, inventory):
    names = inventory["menus"][AMP]
    if (len(names) != 45 or len(set(names)) != 45 or TEMPLATE not in names
            or any(not isinstance(n, str) or (n != TEMPLATE and not n.startswith("factory:"))
                   for n in names)):
        raise ValueError("expected frozen SW50R 45-candidate inventory")
    if set(distances) != {p["slug"] for p in parts}:
        raise ValueError("scores must exactly match development membership")
    for part in parts:
        for bs in BAND_SETS:
            for kind in ("measure_A", "measure_B", "net_A"):
                scores = distances[part["slug"]].get(f"{bs}|{AMP}|{kind}")
                if not isinstance(scores, dict) or set(scores) != set(names):
                    raise ValueError(f"incomplete candidate menu: {part['slug']} {bs} {kind}")
                if any(v is not None and not D.raw_valid(v) for v in scores.values()):
                    raise ValueError(f"invalid non-null raw distance: {part['slug']} {bs} {kind}")
    return sorted(names)


def frozen_constants(diagnostic, parts, names):
    """Read the archived full-development A constants; do not refit them."""
    bands = {p["band"] for p in parts}
    membership = {p["slug"]: p["band"] for p in parts}
    if diagnostic["parts"] != 33 or diagnostic["bands"] != 11:
        raise ValueError("frozen diagnostic must cover all 33 parts and 11 bands")
    result = {}
    for bs in BAND_SETS:
        cell = diagnostic["cells"][f"{bs}|{AMP}"]
        if (cell["parts"], cell["bands"], cell["menu_size"]) != (33, 11, 45):
            raise ValueError("frozen diagnostic cell inventory changed")
        rows = cell["rows"]
        if (len(rows) != 33 or {r["part"] for r in rows} != set(membership)
                or any(r["band"] != membership[r["part"]] for r in rows)):
            raise ValueError("frozen diagnostic development membership changed")
        result[bs] = {}
        for method, field in (("constant", "constants_by_excluded_band"),
                              ("inclusive_constant", "inclusive_constants_by_excluded_band")):
            audits = cell[field]
            if set(audits) != bands:
                raise ValueError("frozen constants must exclude every development band")
            for band, audit in audits.items():
                training = {p["slug"] for p in parts if p["band"] != band}
                candidates = set(names) - ({TEMPLATE} if method == "constant" else set())
                eligible, excluded = audit["eligible_medians_raw_A"], audit["excluded_candidates"]
                if (set(audit["training_parts"]) != training
                        or len(audit["training_parts"]) != len(training)
                        or set(eligible) & set(excluded)
                        or set(eligible) | set(excluded) != candidates
                        or any(not D.raw_valid(v) for v in eligible.values())
                        or any(not isinstance(v, list) or not v or not set(v) <= training
                               for v in excluded.values())
                        or audit["preset"] != D.best(eligible)):
                    raise ValueError(f"invalid frozen constant: {bs} {band} {method}")
                if any(r["picks"][method] != audit["preset"]
                       for r in rows if r["band"] == band):
                    raise ValueError("frozen constant row disagrees with audit")
            result[bs][method] = audits
    return result


def fit_prior(parts, labels, names):
    """Labels contains only training slugs. Center before eligibility filtering."""
    slugs = sorted(p["slug"] for p in parts)
    if set(labels) != set(slugs) or len(set(slugs)) != len(slugs):
        raise ValueError("prior labels must exactly equal training slugs")
    bands = sorted({p["band"] for p in parts})
    centered, audits = {}, {}
    for slug in slugs:
        values = labels[slug]
        logs = {n: math.log(values[n]) for n in names if positive(values[n])}
        center = statistics.median(logs.values()) if logs else None
        centered[slug] = {n: v - center for n, v in logs.items()}
        audits[slug] = {"median_log_B": center, "centered_log_B": centered[slug],
                        "missing_labels": [n for n in names if values[n] is None],
                        "zero_labels": [n for n in names if D.raw_valid(values[n]) and values[n] == 0]}
    priors, excluded, band_means = {}, {}, {}
    for name in names:
        invalid = {s: "missing_label" if labels[s][name] is None else "nonpositive_label"
                   for s in slugs if name not in centered[s]}
        if not slugs or invalid:
            excluded[name] = {"reason": "no_training_parts" if not slugs else "incomplete_positive_B",
                              "parts": invalid}
            continue
        means = {band: statistics.mean(centered[p["slug"]][name] for p in parts if p["band"] == band)
                 for band in bands}
        band_means[name] = means
        priors[name] = statistics.mean(means.values())
    return {"training_parts": slugs, "training_bands": bands, "part_labels": audits,
            "eligible_candidates": sorted(priors), "excluded_candidates": excluded,
            "candidate_band_means": band_means, "priors": priors,
            "trainable": bool(priors), "missing_reason": None if priors else "no_complete_prior_candidate"}


def predict(prior, raw_A, alpha):
    """No evaluation B can enter prediction. Zero anywhere blocks alpha > 0."""
    if alpha not in ALPHAS:
        raise ValueError("alpha must belong to the fixed grid")
    priors = prior["priors"]
    nulls = sorted(n for n, v in raw_A.items() if v is None)
    zeros = sorted(n for n, v in raw_A.items() if D.raw_valid(v) and v == 0)
    all_null = bool(raw_A) and len(nulls) == len(raw_A)
    result = {"preset": None, "alpha": alpha, "fallback": False,
              "fallback_attempted": all_null, "missing_reason": None,
              "null_net_candidates": nulls, "zero_net_candidates": zeros,
              "excluded_prior_candidates": sorted(set(raw_A) - set(priors)),
              "excluded_missing_net_candidates": sorted(set(priors) & set(nulls)),
              "selection_scores": {}}
    if not priors:
        result["missing_reason"] = "no_complete_prior_candidate"
    elif alpha == 0 or all_null:
        result["selection_scores"] = dict(priors)
        result["preset"] = min(priors, key=lambda n: (priors[n], n))
        result["fallback"] = all_null
    elif zeros:
        result["missing_reason"] = "zero_raw_net_log_unscorable"
    else:
        blended = {n: alpha * math.log(raw_A[n]) + (1 - alpha) * value
                   for n, value in priors.items() if positive(raw_A[n])}
        result["selection_scores"] = blended
        if blended:
            result["preset"] = min(blended, key=lambda n: (blended[n], n))
        else:
            result["missing_reason"] = "no_positive_net_for_prior_candidates"
    return result


def net_prediction(raw_A, prior, fallback):
    """Original unrestricted raw chooser: a raw zero may win."""
    preset = D.best(raw_A)
    all_null = all(v is None for v in raw_A.values())
    result = {"preset": preset, "fallback": False, "fallback_attempted": False,
              "missing_reason": None if preset is not None else "all_raw_net_null"}
    if all_null and fallback:
        choice = predict(prior, raw_A, 0)
        result.update({k: choice[k] for k in result})
    return result


def inner_fold(training, evaluation, labels, features, names):
    """Fit on training only; freeze all five sets of picks before scoring labels."""
    train_slugs = {p["slug"] for p in training}
    if train_slugs & {p["slug"] for p in evaluation}:
        raise ValueError("inner training and evaluation overlap")
    prior = fit_prior(training, {s: labels[s] for s in sorted(train_slugs)}, names)
    predictions = {str(alpha): {p["slug"]: predict(prior, features[p["slug"]], alpha)
                               for p in evaluation} for alpha in ALPHAS}
    evaluated = {}
    for alpha in ALPHAS:
        rows = []
        for part in evaluation:
            slug = part["slug"]
            choice = predictions[str(alpha)][slug]
            value = labels[slug].get(choice["preset"]) if choice["preset"] is not None else None
            rows.append({"part": slug, "band": part["band"], "prediction": choice,
                         "chosen_B": value, "log_chosen_B": math.log(value) if positive(value) else None,
                         "evaluation_reason": None if positive(value) else (
                             "zero_chosen_B" if D.raw_valid(value) else "missing_chosen_B")})
        complete = bool(rows) and all(r["log_chosen_B"] is not None for r in rows)
        evaluated[str(alpha)] = {"rows": rows, "required_parts": len(rows),
                                 "positive_parts": sum(r["log_chosen_B"] is not None for r in rows),
                                 "complete": complete,
                                 "mean_log_B": statistics.mean(r["log_chosen_B"] for r in rows)
                                 if complete else None}
    return {"prior": prior, "evaluation_parts": sorted(p["slug"] for p in evaluation),
            "alphas": evaluated}


def choose_alpha(losses):
    eligible = [a for a in ALPHAS if losses[str(a)]["eligible"]]
    if not eligible:
        return None
    minimum = min(losses[str(a)]["mean_log_B"] for a in eligible)
    return min(a for a in eligible if losses[str(a)]["mean_log_B"] <= minimum + TIE_TOLERANCE)


def fit_outer(parts, labels, features, names):
    """This function receives only outer training labels and net features."""
    slugs = {p["slug"] for p in parts}
    if set(labels) != slugs or set(features) != slugs:
        raise ValueError("outer fitting inputs must exactly equal training slugs")
    bands = sorted({p["band"] for p in parts})
    inner = {}
    for band in bands:
        inner[band] = inner_fold([p for p in parts if p["band"] != band],
                                 [p for p in parts if p["band"] == band], labels, features, names)
    losses = {}
    for alpha in ALPHAS:
        by_band = {b: inner[b]["alphas"][str(alpha)]["mean_log_B"] for b in bands}
        complete = bool(bands) and all(v is not None for v in by_band.values())
        losses[str(alpha)] = {"eligible": complete, "band_mean_log_B": by_band,
                              "mean_log_B": statistics.mean(by_band.values()) if complete else None,
                              "required_parts": len(parts), "required_bands": len(bands),
                              "positive_parts": sum(inner[b]["alphas"][str(alpha)]["positive_parts"]
                                                    for b in bands)}
    alpha = choose_alpha(losses)
    prior = fit_prior(parts, labels, names)
    trainable = alpha is not None and prior["trainable"]
    return {"training_parts": sorted(slugs), "training_bands": bands, "inner_folds": inner,
            "alpha_losses": losses, "selected_alpha": alpha, "prior": prior,
            "trainable": trainable, "missing_reason": None if trainable else (
                "no_eligible_alpha" if alpha is None else "no_complete_prior_candidate")}


def summarize(rows, comparator):
    summary = D.summarize(rows, "calibration", comparator)
    summary["paired_log_ratios"] = {r["part"]: D.log_ratio(r["B"]["calibration"], r["B"][comparator])
                                     for r in rows}
    summary["required_bands"] = len({r["band"] for r in rows})
    summary["band_required_parts"] = {b: sum(r["band"] == b for r in rows)
                                       for b in sorted({r["band"] for r in rows})}
    return summary


def report_cell(rows, folds, constants, names):
    bands = sorted({r["band"] for r in rows})
    comparisons = {f"calibration_vs_{m}": summarize(rows, m) for m in METHODS if m != "calibration"}
    joint, counts = {}, {}
    for band in bands:
        subset = [r for r in rows if r["band"] == band]
        wins = sum(all(D.raw_win(r["B"]["calibration"], r["B"][m]) for m in ("prior", "net"))
                   for r in subset)
        joint[band], counts[band] = wins / len(subset), {"wins": wins, "required_parts": len(subset)}
    joint_report = {"by_band": joint, "counts_by_band": counts,
                    "share": statistics.mean(joint.values()), "required_parts": len(rows),
                    "required_bands": len(bands)}
    gates = {}
    for comparator in ("prior", "net"):
        comparison = comparisons[f"calibration_vs_{comparator}"]
        effect, sensitivity = comparison["band_median_log_ratio"], comparison["sign_flip_p_two_sided"]
        gates[f"{comparator}_complete_positive"] = not comparison["numeric_summaries_descriptive_only"]
        gates[f"{comparator}_five_percent_margin"] = effect is not None and effect <= math.log(.95)
        gates[f"{comparator}_sign_flip_below_point_one"] = sensitivity is not None and sensitivity < .1
    gates["joint_wins_above_half"] = joint_report["share"] > .5
    endpoint = comparisons["calibration_vs_restricted_net"]
    endpoint_effect = endpoint["band_median_log_ratio"]
    endpoint_improved = (not endpoint["numeric_summaries_descriptive_only"]
                         and endpoint_effect is not None and endpoint_effect < 0)
    agreement = {}
    for method in METHODS[1:]:
        same = sum(r["picks"]["calibration"] is not None and r["picks"]["calibration"] == r["picks"][method]
                   for r in rows)
        both = sum(r["picks"]["calibration"] is not None and r["picks"][method] is not None for r in rows)
        agreement[method] = {"same": same, "both_selected": both, "original_denominator": len(rows),
                             "all_parts_share": same / len(rows)}
    alpha_counts = {str(a): sum(f["selected_alpha"] == a for f in folds.values()) for a in ALPHAS}
    alpha_counts["missing"] = sum(f["selected_alpha"] is None for f in folds.values())
    alpha_part_counts = {str(a): sum(folds[r["band"]]["selected_alpha"] == a for r in rows)
                         for a in ALPHAS} if folds else {}
    if folds:
        alpha_part_counts["missing"] = sum(folds[r["band"]]["selected_alpha"] is None for r in rows)
    return {"parts": len(rows), "bands": len(bands), "menu_size": len(names), "outer_folds": folds,
            "frozen_A_constants": constants, "rows": rows, "comparisons": comparisons,
            "joint_wins": joint_report, "selection_agreement": agreement,
            "selected_alpha_fold_counts": alpha_counts,
            "selected_alpha_required_folds": len(bands),
            "selected_alpha_part_counts": alpha_part_counts,
            "selected_alpha_required_parts": len(rows),
            "fallback_counts": {m: sum(r["predictions"][m]["fallback"] for r in rows) for m in METHODS},
            "fallback_required_parts": len(rows),
            "missing_selections": {m: [r["part"] for r in rows if r["picks"][m] is None] for m in METHODS},
            "missing_chosen_B": {m: [r["part"] for r in rows if not D.raw_valid(r["B"][m])] for m in METHODS},
            "zero_chosen_B": {m: [r["part"] for r in rows if D.raw_valid(r["B"][m]) and r["B"][m] == 0]
                              for m in METHODS},
            "followup_gates": gates, "followup_justified": all(gates.values()),
            "followup_scope": "combined calibration procedure; does not alone establish a blending benefit",
            "restricted_endpoint_improved": endpoint_improved,
            "blending_benefit_observed": all(gates.values()) and endpoint_improved,
            "blending_benefit_criterion": "main gates plus complete positive paired band-median improvement over restricted alpha=1; descriptive only"}


def cell(distances, parts, bs, names, constants):
    def scores(slug, kind):
        return distances[slug][f"{bs}|{AMP}|{kind}"]

    folds, frozen = {}, {}
    for band in sorted({p["band"] for p in parts}):
        training = [p for p in parts if p["band"] != band]
        # Outer net scores are not accessed until final prediction, after tuning.
        labels = {p["slug"]: scores(p["slug"], "measure_B") for p in training}
        features = {p["slug"]: scores(p["slug"], "net_A") for p in training}
        fold = fit_outer(training, labels, features, names)
        folds[band] = fold
        for part in parts:
            if part["band"] != band:
                continue
            slug = part["slug"]
            raw_A = scores(slug, "net_A")
            if fold["trainable"]:
                calibration = predict(fold["prior"], raw_A, fold["selected_alpha"])
            else:
                calibration = {"preset": None, "fallback": False, "fallback_attempted": False,
                               "missing_reason": fold["missing_reason"], "alpha": fold["selected_alpha"]}
            choices = {"calibration": calibration, "prior": predict(fold["prior"], raw_A, 0),
                       "restricted_net": predict(fold["prior"], raw_A, 1),
                       "net": net_prediction(raw_A, fold["prior"], True),
                       "historical_net": net_prediction(raw_A, fold["prior"], False)}
            for method in ("constant", "inclusive_constant", "template", "true_di"):
                preset = (constants[method][band]["preset"] if method in constants else
                          TEMPLATE if method == "template" else D.best(scores(slug, "measure_A")))
                choices[method] = {"preset": preset, "fallback": False,
                                   "missing_reason": None if preset is not None else "no_raw_A_selection"}
            frozen[slug] = choices
    # All outer picks have been fixed before attaching their evaluation B values.
    rows = []
    for part in sorted(parts, key=lambda p: p["slug"]):
        slug = part["slug"]
        predictions = frozen[slug]
        picks = {m: predictions[m]["preset"] for m in METHODS}
        labels = scores(slug, "measure_B")
        rows.append({"part": slug, "band": part["band"], "predictions": predictions, "picks": picks,
                     "B": {m: labels.get(n) if n is not None else None for m, n in picks.items()},
                     "missing_B_candidates": [n for n in names if labels[n] is None],
                     "zero_B_candidates": [n for n in names if D.raw_valid(labels[n]) and labels[n] == 0]})
    return report_cell(rows, folds, constants, names)


def analyze(distances, metadata, inventory, diagnostic):
    parts = select_parts(metadata)
    names = validate_scores(distances, parts, inventory)
    constants = frozen_constants(diagnostic, parts, names)
    cells = {f"{bs}|{AMP}": cell(distances, parts, bs, names, constants[bs]) for bs in BAND_SETS}
    justified = all(c["followup_justified"] for c in cells.values())
    return {"scope": "exploratory supervised development rank calibration; no confirmation or release",
            "parts": len(parts), "bands": len({p["band"] for p in parts}), "candidate_inventory": names,
            "panel": [{"slug": p["slug"], "band": p["band"]} for p in parts], "cells": cells,
            "followup_justified_both_band_sets": justified,
            "blending_benefit_observed_both_band_sets": all(c["blending_benefit_observed"] for c in cells.values()),
            "next_step": "separately declare broader development study" if justified else "close this fixed blend",
            "limits": ["Overlapping fitted folds and reused development data preclude calibrated inference.",
                       "Available-case effects are descriptive; all original denominators are retained.",
                       "True DI is an unavailable-input descriptive control.",
                       "The prior minimizes band-weighted mean log B; evaluation uses medians of band medians.",
                       "The alpha=1 endpoint retains training-prior eligibility and differs from unrestricted net.",
                       "A pass supports development follow-up only, not release or new waveform training.",
                       "Do not retune this grid or prior, add features, choose subsets, or reuse the spent reserved split.",
                       "Heavy-tone listening and fresh reserved confirmation remain necessary for a changed method."]}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_json(path, report, label):
    raw = path.read_bytes()
    report["inputs"][label] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
    return json.loads(raw, object_pairs_hook=unique_object)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def validate_provenance(report, diagnostic, verification):
    """Bind archived constants and every original input to independent verification."""
    if (verification.get("verified") is not True
            or verification["comparison"]["mismatch_count"] != 0
            or (verification["parts"], verification["bands"]) != (33, 11)
            or verification["menu_counts"][AMP] != 45):
        raise ValueError("development diagnostic must be independently verified")
    if (report["inputs"]["full_development_diagnostic"]["sha256"]
            != verification["production_report"]["sha256"]):
        raise ValueError("archived diagnostic differs from independently verified report")
    for label, current in (("metadata", "metadata"), ("distances", "distances"),
                           ("menu_inventory", "menu_inventory"), ("script", "source_diagnostic_code"),
                           ("plan", "source_diagnostic_plan")):
        expected = verification["inputs"][label]
        if diagnostic["inputs"][label] != expected or report["inputs"][current] != expected:
            raise ValueError(f"verified development source provenance changed: {label}")


def note(report, message):
    report["log"].append({"at_utc": datetime.now(timezone.utc).isoformat(), "message": message})
    print(message, flush=True)


def run(report):
    note(report, "reading fixed development inputs and archived diagnostic provenance")
    metadata = source_json(METADATA, report, "metadata")
    select_parts(metadata)
    inventory = source_json(INVENTORY, report, "menu_inventory")
    diagnostic = source_json(DIAGNOSTIC, report, "full_development_diagnostic")
    verification = source_json(VERIFICATION, report, "independent_verification")
    for label, path in (("script", Path(__file__).resolve()),
                        ("tests", ROOT / "tests/test_set3_rank_calibration.py"), ("plan", PLAN),
                        ("source_diagnostic_code", ROOT / "learn/set3_diagnostic.py"),
                        ("source_diagnostic_plan", ROOT / "docs/set3-development-diagnostic-plan.md")):
        report["inputs"][label] = {"path": str(path), "sha256": digest(path)}
    distances = source_json(DISTANCES, report, "distances")
    validate_provenance(report, diagnostic, verification)
    note(report, "validated provenance; computing fixed nested leave-band-out calibration")
    report.update(analyze(distances, metadata, inventory, diagnostic))
    for entry in report["inputs"].values():
        if digest(Path(entry["path"])) != entry["sha256"]:
            raise ValueError(f"source changed during execution: {entry['path']}")
    report["status"] = "complete"
    note(report, "completed fixed development calibration; heuristic conclusions only")


def output_path(value):
    path = Path(value).expanduser().absolute()
    boundary = ROOT.resolve() / "tmp"
    if (path.resolve() != path or not path.is_relative_to(boundary)
            or path == boundary or path.exists() or path.is_symlink()):
        raise ValueError("output must be a new regular file under project tmp/")
    return path


def execute(output):
    """Reserve exclusively before input reads, and preserve preflight/computation errors."""
    output = output_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"status": "running", "inputs": {}, "log": [],
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "runtime": {"python": sys.version, "executable": sys.executable},
              "configuration": {"amp": AMP, "band_sets": BAND_SETS, "alpha_grid": ALPHAS,
                                "alpha_tie_tolerance": TIE_TOLERANCE,
                                "prior": "mean of training-band means of median-centered positive log B",
                                "alpha_loss": "mean of inner-band mean log chosen B; all labels required",
                                "sign_flip_tail_tolerance": 1e-12}}
    with output.open("x") as stream:
        try:
            run(report)
        except BaseException as exc:
            report["status"] = "execution_error"
            report["error"] = {"type": type(exc).__name__, "message": str(exc),
                               "traceback": traceback.format_exc()}
            note(report, f"execution failed; retaining report at {output}: {exc}")
            raise
        finally:
            report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new report under project tmp/")
    args = parser.parse_args()
    execute(args.out)


if __name__ == "__main__":
    main()
