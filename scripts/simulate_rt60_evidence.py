"""Probe what RT60 release-slope agreement can establish, without a plugin.

Use the same deterministic excitation through the synthetic chain with its rack
reverb off and on. The input itself has no reverb. This is a known-state
identifiability check, not a prediction of what the real Tone King or a listener
will do. It neither changes nor recommends a loss-profile weight.

    python scripts/simulate_rt60_evidence.py
    python scripts/simulate_rt60_evidence.py --out docs/rt60-synthetic-evidence.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import platform
import sys
from importlib.metadata import version

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis import SAMPLE_RATE, io, probes, refchain
from analysis.compare import compare
from analysis.fingerprint import fingerprint


def _reading(samples):
    fp = fingerprint(io.from_samples(samples, SAMPLE_RATE), regime="probe", excerpt_s=None)
    return fp, {
        "rt60_s": fp.time_fx.get("rt60_s"),
        "release_slope_agreement": fp.time_fx.get("rt60_confidence"),
        "passes_v1_rt60_gate": (
            fp.time_fx.get("rt60_s") is not None
            and float(fp.time_fx.get("rt60_confidence") or 0.0) >= 0.3
        ),
    }


def experiment() -> dict:
    """A fixed paired protocol; every wet case is compared with its own dry chain."""
    inputs = {
        "noise-short": probes.decaying_noise_bursts(
            seconds=10.0, gap=1.0, decay=18.0, length=0.25, seed=7),
        "noise-long": probes.decaying_noise_bursts(
            seconds=10.0, gap=1.0, decay=5.0, length=0.8, seed=7),
        "synthetic-guitar": probes.synthetic_guitar(seconds=10.0, seed=13),
    }
    rows = []
    for name, di in inputs.items():
        _, input_reading = _reading(di)
        dry_audio = refchain.render(di, {"reverb/reverbActive": False})
        dry_fp, dry_reading = _reading(dry_audio)
        wet = []
        for decay_s in (1.2, 2.4):
            wet_audio = refchain.render(di, {
                "reverb/reverbActive": True,
                "reverb/reverbDecay": decay_s,
                "reverb/reverbMix": 50.0,
            })
            wet_fp, wet_reading = _reading(wet_audio)
            objectives = compare(dry_fp, wet_fp, profile="unpaired-v1")
            wet.append({
                "rack_decay_s": decay_s,
                "rack_mix_percent": 50.0,
                "reading": wet_reading,
                "dry_vs_wet_rt60_term": objectives.detail["ambience"].get("rt60"),
                "dry_vs_wet_ambience_terms": objectives.detail["ambience"],
                "dry_vs_wet_ambience": objectives.values["ambience"],
            })
        rows.append({
            "input": name,
            "dry_input": input_reading,
            "rack_reverb_off": dry_reading,
            "rack_reverb_on": wet,
        })
    return {
        "schema": "rt60-synthetic-evidence-1",
        "method": "Deterministic synthetic DI; Morgan reference chain, identical settings "
                  "except rack reverb. Historical unpaired-v1 RT60 term; v2 omits it. "
                  "No real plugin or listener involved.",
        "sample_rate": SAMPLE_RATE,
        "loss_profile": "unpaired-v1",
        "runtime_versions": {
            "python": platform.python_version(),
            "numpy": version("numpy"),
            "scipy": version("scipy"),
            "pyloudnorm": version("pyloudnorm"),
        },
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path,
                        help="write JSON; default is stdout")
    args = parser.parse_args()
    result = json.dumps(experiment(), indent=2, allow_nan=False) + "\n"
    if args.out is None:
        print(result, end="")
    else:
        if args.out.exists():
            parser.error(f"output already exists: {args.out}")
        args.out.write_text(result)
        print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
