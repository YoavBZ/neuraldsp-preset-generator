#!/usr/bin/env python3
"""Find instant fixed-topology starting points in a response atlas.

    python scripts/query_response_atlas.py \
      --atlas packs/morgan/response_atlas_pr12_pilot.json \
      --reference "Hotel California-lead-D major-74bpm-438hz.wav" \
      --reference-mode separated_stem --out-dir /tmp/hotel-atlas

This does not render the plugin.  It fingerprints the reference, compares it with
the stored fingerprints under the normal loss profile, and writes ordinary specs
that ``apply_spec.py`` accepts.  They are starts for local refinement, not claims
that a finite atlas found the final preset.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(SCRIPT_ROOT))

from _cli import guarded, positive_float, positive_int

REGIMES = ("paired_di", "isolated_stem", "separated_stem", "mix", "probe")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--atlas", required=True, type=pathlib.Path,
                        help="response-atlas JSON to query")
    parser.add_argument("--reference", required=True, type=pathlib.Path,
                        help="audio whose response should be matched")
    parser.add_argument("--reference-mode", choices=REGIMES, default="mix",
                        help="how guitar reaches the reference (default: mix)")
    parser.add_argument("--excerpt", type=positive_float, default=None,
                        help="measure only this many seconds")
    parser.add_argument("--loss-profile", default="unpaired-v1",
                        help="named comparison weights (default: unpaired-v1)")
    parser.add_argument("--limit", type=positive_int, default=3,
                        help="starting specs to write (default: 3)")
    parser.add_argument("--out-dir", required=True, type=pathlib.Path,
                        help="destination for atlas-1.json, atlas-2.json, ...")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    from analysis import io, require

    require("querying a response atlas")
    from analysis.compare import load_profile
    from analysis.fingerprint import fingerprint
    from match import atlas
    from match import space as space_module
    from match_preset import _unmeasurable

    document = atlas.load(args.atlas)
    profile = load_profile(args.loss_profile)
    if float(profile.get("weights", {}).get("residual", 0.0) or 0.0) > 0.0:
        raise atlas.AtlasError(
            f"loss profile {args.loss_profile!r} weights a sample-for-sample residual, "
            "but an atlas stores fingerprints rather than waveforms. Use "
            "unpaired-v1 for lookup; local refinement can use paired-v1 with the "
            "original DI/reamp pair."
        )
    reference = io.load(str(args.reference))
    target = fingerprint(reference, regime=args.reference_mode,
                         excerpt_s=args.excerpt)
    unmeasurable = _unmeasurable(target, reference)
    if unmeasurable:
        raise atlas.AtlasError(unmeasurable)
    matches = atlas.nearest(
        document, target, profile=args.loss_profile, limit=args.limit)
    if not matches:
        raise atlas.AtlasError(
            "no stored fingerprint had a dimension weighted by this loss profile"
        )

    caveat = document.get("measurement_caveat")
    if caveat:
        print(f"CAUTION: {caveat}\n")
    print(f"{document['pack']}/{document['amp']}: {document['sample_count']} "
          f"stored responses, {len(document['dimensions'])} continuous dimensions")
    print(f"reference: {args.reference} ({args.reference_mode})")

    space = space_module.build(document["pack"], amp=document["amp"])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for rank, match in enumerate(matches, 1):
        spec = space.to_spec(
            match.settings,
            name=f"Atlas {document['amp'].upper()} {rank}",
        )
        destination = args.out_dir / f"atlas-{rank}.json"
        destination.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        print(f"  {rank}. entry {match.index}, distance {match.score:.3f}: {destination}")

    outside = atlas.outside_ranges(document, target)
    skipped = atlas.uncomparable_features(document, target)
    if outside:
        print("\noutside this finite atlas sample:")
        for row in outside:
            print(
                f"  {row['feature']}: target {row['value']:.3g}, sampled "
                f"{row['sampled_min']:.3g}..{row['sampled_max']:.3g} "
                f"({row['direction']})"
            )
    elif len(skipped) < len(atlas.RESPONSE_FEATURES):
        print("\nevery compared response feature falls inside this finite sample")
    else:
        print("\nno response feature could be compared at all")
    # A feature nobody could measure is not a feature inside the range, and the
    # line above used to count all six of them whether or not they were compared.
    if skipped:
        print("not compared — the atlas or the reference has no reading for: "
              + ", ".join(skipped))
    print("these are observed ranges on the atlas probe, not mathematical limits; "
          "a target outside one is evidence to distrust the topology, not proof "
          "that no denser sample can reach it")
    print("\napply one spec to the topology template, then use match_preset.py for "
          "local refinement")


if __name__ == "__main__":
    guarded(main)
