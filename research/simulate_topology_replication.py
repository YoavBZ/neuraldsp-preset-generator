"""Test two topology-replication allocations before spending plugin renders.

This is not a model of Morgan. It is a fixed stochastic budget experiment: each
topology has twelve latent candidate scores, topology baselines are 0.1 apart,
candidate quality has an exponential 0.08 scale, and one-render noise is swept.
The current policy explores all twelve points and replicates the global shortlist.
Two alternatives either replicate one finalist per topology or spend three renders
per search point and therefore explore only four points at the same search budget.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=20_260_827)
    parser.add_argument("--out", type=pathlib.Path)
    return parser


def simulate(trials: int, seed: int):
    rng = np.random.default_rng(seed)
    rows = []
    for variants in (2, 4, 8):
        shortlist = min(3, variants)
        for sigma in (0.05, 0.15, 0.30):
            totals = {
                "current_regret": 0.0,
                "finalist_regret": 0.0,
                "replicated_points_regret": 0.0,
                "current_exact": 0,
                "finalist_exact": 0,
                "replicated_points_exact": 0,
            }
            for _ in range(trials):
                bases = np.arange(variants, dtype=np.float64) * 0.10
                truth = bases[:, None] + rng.exponential(
                    0.08, size=(variants, 12))
                first = truth + rng.normal(0.0, sigma, size=truth.shape)
                best_topology, best_candidate = np.unravel_index(
                    np.argmin(truth), truth.shape)
                best_truth = truth[best_topology, best_candidate]

                # Current: broad one-render search, then three observations of the
                # global shortlist.
                flat = np.argpartition(first.ravel(), shortlist - 1)[:shortlist]
                old_topology, old_candidate = np.unravel_index(flat, first.shape)
                old_means = (
                    first[old_topology, old_candidate]
                    + truth[old_topology, old_candidate] * 2
                    + rng.normal(0.0, sigma, size=(shortlist, 2)).sum(axis=1)
                ) / 3.0
                old_index = int(np.argmin(old_means))
                old_choice = (int(old_topology[old_index]),
                              int(old_candidate[old_index]))

                # Alternative 1: force one finalist from every topology into the
                # replicated comparison.
                finalists = np.argmin(first, axis=1)
                finalist_means = (
                    first[np.arange(variants), finalists]
                    + truth[np.arange(variants), finalists] * 2
                    + rng.normal(0.0, sigma, size=(variants, 2)).sum(axis=1)
                ) / 3.0
                finalist_topology = int(np.argmin(finalist_means))
                finalist_choice = (finalist_topology,
                                    int(finalists[finalist_topology]))

                # Alternative 2: three observations per search point at the same
                # search-render budget, hence only four points per topology.
                repeated = truth[:, :4, None] + rng.normal(
                    0.0, sigma, size=(variants, 4, 3))
                repeated_means = repeated.mean(axis=2)
                repeated_choice = tuple(int(value) for value in np.unravel_index(
                    np.argmin(repeated_means), repeated_means.shape))

                for prefix, choice in (
                    ("current", old_choice),
                    ("finalist", finalist_choice),
                    ("replicated_points", repeated_choice),
                ):
                    totals[f"{prefix}_regret"] += truth[choice] - best_truth
                    totals[f"{prefix}_exact"] += choice == (
                        best_topology, best_candidate)

            rows.append({
                "topologies": variants,
                "shortlist": shortlist,
                "noise_sigma": sigma,
                "extra_finalist_renders": 2 * (variants - shortlist),
                **{
                    key: (value / trials)
                    for key, value in totals.items()
                },
            })
    return rows


def main() -> None:
    args = build_parser().parse_args()
    if args.trials <= 0:
        raise SystemExit("--trials must be positive")
    result = {
        "schema": "topology-replication-simulation-1",
        "seed": args.seed,
        "trials_per_configuration": args.trials,
        "candidate_points_per_topology": 12,
        "replicated_points_per_topology": 4,
        "observations_per_replicated_score": 3,
        "topology_baseline_step": 0.10,
        "candidate_exponential_scale": 0.08,
        "rows": simulate(args.trials, args.seed),
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out is None:
        print(rendered, end="")
    else:
        args.out.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
