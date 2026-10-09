"""Development-only routing diagnostic; see docs/set3-development-diagnostic-plan.md.

Reads existing development scores, never audio or reserved scores. No ML dependencies.
Run only after committing the reviewed plan and this entry point.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
DISTANCES = Path.home() / "ndsp-presets/learn/direc/phase2-set3/distances.json"
METADATA = ROOT / "docs/validation-set3.json"
PLAN = ROOT / "docs/set3-development-diagnostic-plan.md"
MENU_INVENTORY = ROOT / "docs/set3-development-diagnostic-menus.json"
AMPS = ("sw50r", "pr12", "ac20")
BAND_SETS = ("recording", "union")
TEMPLATE = "template+R"


def raw_valid(value):
    return (not isinstance(value, bool) and isinstance(value, (float, int))
            and math.isfinite(value) and value >= 0)


def best(scores):
    valid = [name for name, value in scores.items() if raw_valid(value)]
    return min(valid, key=lambda name: (scores[name], name)) if valid else None


def log_ratio(numerator, denominator):
    if not raw_valid(numerator) or not raw_valid(denominator):
        return None
    if numerator <= 0 or denominator <= 0:
        return None
    # Subtract logs rather than dividing: avoid overflow/underflow on valid floats.
    return math.log(numerator) - math.log(denominator)


def raw_win(numerator, denominator):
    return raw_valid(numerator) and raw_valid(denominator) and numerator < denominator


def sign_flip(values):
    """Exact two-sided band-level test, with a declared 1e-12 tail tolerance."""
    observed = abs(math.fsum(values))
    return sum(abs(math.fsum(s * v for s, v in zip(signs, values))) >= observed - 1e-12
               for signs in itertools.product((-1, 1), repeat=len(values))) / 2**len(values)


def validate(distances, parts, menus):
    if not parts or any(p.get("split") != "development" for p in parts):
        raise ValueError("only explicitly declared development parts are allowed")
    slugs = [p["slug"] for p in parts]
    if len(set(slugs)) != len(slugs) or set(distances) != set(slugs):
        raise ValueError("distance slugs must exactly equal the development split")
    if set(menus) != set(AMPS):
        raise ValueError("frozen menu inventory must contain exactly all three amps")
    for bs in BAND_SETS:
        for amp in AMPS:
            inventory = menus[amp]
            expected = set(inventory)
            if (len(expected) != len(inventory) or TEMPLATE not in expected
                    or len(expected) < 2
                    or any(n != TEMPLATE and not n.startswith("factory:") for n in expected)):
                raise ValueError("invalid frozen menu inventory")
            for slug in sorted(slugs):
                for kind in ("measure_A", "measure_B", "net_A"):
                    key = f"{bs}|{amp}|{kind}"
                    scores = distances[slug].get(key)
                    if not isinstance(scores, dict) or TEMPLATE not in scores:
                        raise ValueError(f"missing menu {slug}: {key}")
                    names = set(scores)
                    if len(names) < 2 or any(n != TEMPLATE and not n.startswith("factory:")
                                             for n in names):
                        raise ValueError(f"invalid candidate menu {slug}: {key}")
                    if names != expected:
                        raise ValueError(f"inconsistent menu {slug}: {key}")
                    if any(v is not None and not raw_valid(v) for v in scores.values()):
                        raise ValueError(f"invalid non-null raw distance {slug}: {key}")


def summarize(rows, numerator, denominator):
    bands = sorted({r["band"] for r in rows})
    medians, refused, zero, wins = {}, [], [], {}
    for band in bands:
        subset = [r for r in rows if r["band"] == band]
        ratios = []
        won = 0
        for row in subset:
            n, d = row["B"][numerator], row["B"][denominator]
            ratio = log_ratio(n, d)
            if ratio is None:
                (refused if not raw_valid(n) or not raw_valid(d) else zero).append(row["part"])
            else:
                ratios.append(ratio)
            won += raw_win(n, d)
        medians[band] = statistics.median(ratios) if ratios else None
        wins[band] = won / len(subset)
    available = [v for v in medians.values() if v is not None]
    return {
        "band_medians": medians,
        "band_median_log_ratio": statistics.median(available) if available else None,
        "sign_flip_p_two_sided": sign_flip(available) if len(available) == len(bands) else None,
        "band_weighted_win_share": statistics.mean(wins.values()),
        "refused_parts": sorted(refused),
        "nonpositive_log_parts": sorted(zero),
        "required_parts": len(rows),
        "scorable_parts": len(rows) - len(refused) - len(zero),
        "available_bands": [b for b, v in medians.items() if v is not None],
        "numeric_summaries_descriptive_only": bool(refused or zero),
        "sign_flip_interpretation": "exploratory sensitivity heuristic; independent symmetric signs not established",
    }


def cell(distances, parts, bs, amp, menus):
    def scores(slug, kind):
        return distances[slug][f"{bs}|{amp}|{kind}"]

    names = sorted(menus[amp])
    bands = sorted({p["band"] for p in parts})
    constants, inclusive = {}, {}
    for target, include_template in ((constants, False), (inclusive, True)):
        for band in bands:
            training = [p["slug"] for p in parts if p["band"] != band]
            eligible, excluded = {}, {}
            for name in names:
                if name == TEMPLATE and not include_template:
                    continue
                invalid = [slug for slug in training if not raw_valid(scores(slug, "measure_A")[name])]
                if not training or invalid:
                    excluded[name] = invalid or ["no other development bands"]
                else:
                    eligible[name] = statistics.median(scores(slug, "measure_A")[name] for slug in training)
            target[band] = {
                "preset": best(eligible), "training_parts": training,
                "eligible_medians_raw_A": eligible, "excluded_candidates": excluded,
            }

    rows = []
    for part in sorted(parts, key=lambda p: p["slug"]):
        slug, band = part["slug"], part["band"]
        b = scores(slug, "measure_B")
        picks = {"true_di": best(scores(slug, "measure_A")),
                 "rebuilt_di": best(scores(slug, "net_A")),
                 "constant": constants[band]["preset"],
                 "inclusive_constant": inclusive[band]["preset"],
                 "template": TEMPLATE, "hindsight_B": best(b)}
        values = {method: b.get(name) if name is not None else None for method, name in picks.items()}
        rows.append({"part": slug, "band": band, "picks": picks, "B": values,
                     "hindsight_refused_candidates": [n for n, v in b.items() if not raw_valid(v)]})
    comparisons = {}
    for numerator, denominator in (
        ("true_di", "constant"), ("true_di", "template"),
        ("rebuilt_di", "constant"), ("rebuilt_di", "template"),
        ("true_di", "rebuilt_di"), ("hindsight_B", "true_di"),
        ("hindsight_B", "constant"), ("constant", "template"),
        ("true_di", "inclusive_constant"), ("rebuilt_di", "inclusive_constant"),
        ("hindsight_B", "inclusive_constant"),
    ):
        comparisons[f"{numerator}_vs_{denominator}"] = summarize(rows, numerator, denominator)

    joint = {}
    for label, method, constant in (("true_di", "true_di", "constant"),
                                     ("rebuilt_di", "rebuilt_di", "constant"),
                                     ("true_di_inclusive", "true_di", "inclusive_constant"),
                                     ("rebuilt_di_inclusive", "rebuilt_di", "inclusive_constant")):
        per_band = {}
        for band in bands:
            subset = [r for r in rows if r["band"] == band]
            won = 0
            for row in subset:
                won += all(raw_win(row["B"][method], row["B"][baseline])
                           for baseline in (constant, "template"))
            per_band[band] = won / len(subset)
        joint[label] = {"by_band": per_band, "share": statistics.mean(per_band.values())}

    control = comparisons["true_di_vs_constant"]
    template = comparisons["true_di_vs_template"]
    effect, p = control["band_median_log_ratio"], control["sign_flip_p_two_sided"]
    gates = {
        "no_required_refusals": not control["numeric_summaries_descriptive_only"]
                                 and not template["numeric_summaries_descriptive_only"],
        "constant_margin": effect is not None and effect <= math.log(0.95),
        "constant_sign_flip": p is not None and p < 0.1,
        "joint_win_share": joint["true_di"]["share"] > 0.5,
    }
    inclusive_control = comparisons["true_di_vs_inclusive_constant"]
    inclusive_effect = inclusive_control["band_median_log_ratio"]
    inclusive_p = inclusive_control["sign_flip_p_two_sided"]
    gates.update({
        "inclusive_complete": not inclusive_control["numeric_summaries_descriptive_only"],
        "inclusive_margin": inclusive_effect is not None and inclusive_effect <= math.log(.95),
        "inclusive_sign_flip": inclusive_p is not None and inclusive_p < .1,
        "inclusive_joint_wins": joint["true_di_inclusive"]["share"] > .5,
    })
    gap = comparisons["true_di_vs_rebuilt_di"]
    gap_effect, gap_p = gap["band_median_log_ratio"], gap["sign_flip_p_two_sided"]
    gap_gates = {
        "complete": not gap["numeric_summaries_descriptive_only"],
        "margin": gap_effect is not None and gap_effect <= math.log(.95),
        "sign_flip": gap_p is not None and gap_p < .1,
    }
    agreement_denominator = sum(r["picks"]["true_di"] is not None
                                and r["picks"]["rebuilt_di"] is not None for r in rows)
    agreement_numerator = sum(r["picks"]["true_di"] is not None
                              and r["picks"]["true_di"] == r["picks"]["rebuilt_di"] for r in rows)
    return {"parts": len(parts), "bands": len(bands), "menu_size": len(names),
            "constants_by_excluded_band": constants, "inclusive_constants_by_excluded_band": inclusive,
            "rows": rows,
            "comparisons": comparisons, "joint_wins": joint,
            "selection_agreement": {"same": agreement_numerator, "both_selected": agreement_denominator,
                                    "original_denominator": len(parts),
                                    "all_parts_share": agreement_numerator / len(parts)},
            "missing_true_di_selections": [r["part"] for r in rows if r["picks"]["true_di"] is None],
            "missing_rebuilt_di_selections": [r["part"] for r in rows if r["picks"]["rebuilt_di"] is None],
            "hindsight_full_menu_scorable": all(not r["hindsight_refused_candidates"] for r in rows),
            "headroom_gates": gates, "headroom_observed": all(gates.values()),
            "pipeline_gap_gates": gap_gates, "pipeline_gap_observed": all(gap_gates.values())}


def analyze(distances, parts, menus):
    validate(distances, parts, menus)
    cells = {f"{bs}|{amp}": cell(distances, parts, bs, amp, menus)
             for bs in BAND_SETS for amp in AMPS}
    return {"scope": "exploratory development-only routing; not confirmation or shipping",
            "parts": len(parts), "bands": len({p["band"] for p in parts}), "cells": cells,
            "routing": {amp: {"headroom_observed_both_band_sets": all(
                cells[f"{bs}|{amp}"]["headroom_observed"] for bs in BAND_SETS),
                "pipeline_gap_observed_both_band_sets": all(
                cells[f"{bs}|{amp}"]["pipeline_gap_observed"] for bs in BAND_SETS)} for amp in AMPS},
            "limits": ["Development data were inspected in earlier experiments.",
                       "True DI and hindsight B are unavailable-input controls, not product methods.",
                       "The pipeline contrast combines reconstruction, level, alignment and DI-derived scoring mask.",
                       "Sign enumeration is a sensitivity heuristic, not calibrated inference with fitted overlapping constants.",
                       "Available-case effects with refusals are descriptive; original win denominators retained.",
                       "Audio-distance implementation and heavier-tone perceptual validity are not checked here."]}


def prepare_menus():
    """Read installed factory metadata only, never experimental score values/audio."""
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "research"))
    import render_preset_panel as RP
    from packs.loader import load_pack

    class Dummy:
        def _stored(self, pack, spec, value):
            return pack.to_stored(spec, value, warnings=[])

    pack = load_pack("morgan")
    menus = {}
    for amp in AMPS:
        candidates = RP.candidates(argparse.Namespace(amp=amp, factory_dir=RP.FACTORY), pack, Dummy())
        menus[amp] = sorted(name for name in candidates if name != "template")
    inventory = {"source": "installed factory preset metadata and declared template IDs, not score rows",
                 "menus": menus, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    with MENU_INVENTORY.open("x") as stream:
        json.dump(inventory, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"inventory": str(MENU_INVENTORY),
                      "counts": {amp: len(names) for amp, names in menus.items()}}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "tmp/set3-development-diagnostic.json")
    parser.add_argument("--prepare-menus", action="store_true",
                        help="create the candidate-ID inventory from factory metadata without reading scores")
    args = parser.parse_args()
    if args.prepare_menus:
        prepare_menus()
        return
    output = args.out.resolve()
    if not output.is_relative_to(ROOT / "tmp") or output.exists():
        parser.error("output must be a new file under project tmp/")
    # The input paths are fixed: there is no switch accepting reserved scores/audio.
    metadata = json.loads(METADATA.read_text())
    parts = [p for p in metadata["parts"] if p["split"] == "development"]
    if len(parts) != 33 or len({p["band"] for p in parts}) != 11:
        raise ValueError("declared development panel changed")
    raw = DISTANCES.read_bytes()
    inputs = {"distances": {"path": str(DISTANCES), "sha256": hashlib.sha256(raw).hexdigest()}}
    for name, path in (("metadata", METADATA), ("plan", PLAN), ("script", Path(__file__)),
                       ("menu_inventory", MENU_INVENTORY)):
        inputs[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    result = analyze(json.loads(raw), parts, json.loads(MENU_INVENTORY.read_text())["menus"])
    result["inputs"] = inputs
    result["computed_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["runtime"] = {"python": sys.version, "executable": sys.executable}
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive publication: no previous experiment is overwritten or reused.
    with output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(output), "routing": result["routing"]}, indent=2))


if __name__ == "__main__":
    main()
