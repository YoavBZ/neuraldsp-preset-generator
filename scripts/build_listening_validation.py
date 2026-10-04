#!/usr/bin/env python3
"""Stage 0b: build the listening-validation trials from the committed trial list.

    python scripts/build_listening_validation.py \\
        --trials ~/ndsp-presets/runs/listening-validation/draw/trials.json \\
        --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --out-dir ~/ndsp-presets/runs/listening-validation/trials \\
        --private-dir ~/ndsp-presets/runs/listening-validation/private

Trial numbers, the two sittings and every A/B assignment are drawn here from the
system's randomness and written only to `--private-dir`, with the builder's output and
the keys; the listener's folder gets the numbered trial files and an answer sheet,
nothing else. Repeats go in the second sitting with their originals in the first; each
sitting gets at least one hidden reference. On the test pairs the option the judge
calls closer is A on exactly half, chosen at random, so a listener's lean towards A or
B cannot add to or take from agreement. `docs/listening-validation-plan.md`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import secrets
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

SR, SEGMENT_S, SITTING = 48000, 4.0, 15


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trials", type=pathlib.Path, required=True)
    ap.add_argument("--panel-dir", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--out-dir", type=pathlib.Path, required=True)
    ap.add_argument("--private-dir", type=pathlib.Path, required=True)
    return ap


def sittings(trials, rng):
    """Two sittings of 15: repeats in the second with their originals in the first, and a
    hidden reference in each."""
    by_id = {t["id"]: t for t in trials if "id" in t}
    repeats = [t for t in trials if t["kind"] == "repeat"]
    originals = [by_id[t["of"]] for t in repeats]
    rest = [t for t in trials if t["kind"] != "repeat" and t not in originals]
    while True:
        rng.shuffle(rest)
        first = originals + rest[: SITTING - len(originals)]
        second = rest[SITTING - len(originals):] + repeats
        if all(any(t["kind"] == "hidden_reference" for t in s) for s in (first, second)):
            break
    rng.shuffle(first)
    rng.shuffle(second)
    return first, second


def seed_for(first_is_a: bool, rng) -> int:
    """A seed under which `build_rab_audition.py` makes its first input A, or B."""
    import random

    while True:
        seed = rng.getrandbits(63)
        if (not random.Random(seed).getrandbits(1)) == first_is_a:   # its swap bit
            return seed


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("building the listening validation")
    import hashlib

    trials_text = args.trials.expanduser().read_text()
    plan = json.loads(trials_text)
    panel = args.panel_dir.expanduser()
    crops = args.crops_dir.expanduser()
    out_dir, private = args.out_dir.expanduser(), args.private_dir.expanduser()
    if (out_dir.resolve() == private.resolve() or private.resolve().is_relative_to(out_dir.resolve())
            or out_dir.resolve().is_relative_to(private.resolve())):
        die("the private folder and the listener's folder must be separate")
    for d in (out_dir, private):
        if d.exists() and any(d.iterdir()):
            die(f"{d} is not empty; trials are built once")
        d.mkdir(parents=True, exist_ok=True)
    index = json.loads((panel / "index.json").read_text())
    files = {(r["part"], r["candidate"]): r["file"] for r in index["rows"] if "file" in r}
    trials = plan["trials"]
    by_id = {t["id"]: t for t in trials if "id" in t}
    rng = secrets.SystemRandom()
    first, second = sittings(trials, rng)
    tests = [t for t in trials if t["kind"] == "test"]
    judge_first_as_a = set(rng.sample([t["id"] for t in tests], len(tests) // 2))
    order = []
    for sitting, block in ((1, first), (2, second)):
        for t in block:
            pair = by_id[t["of"]] if t["kind"] == "repeat" else t
            order.append({"trial": len(order) + 1, "sitting": sitting, "kind": t["kind"],
                          "id": t.get("id"), "of": t.get("of"), "part": pair["part"],
                          "first": pair["first"], "second": pair["second"]})
    for row in order:
        pair_part = row["part"]
        w = next(t for t in trials if t.get("part") == pair_part and "window_s" in t)
        lag = w["lag"]
        reference = crops / pair_part / "reference.wav"

        def source(name):
            if name == "reference":
                return reference, w["window_s"], "non-Morgan"
            return pathlib.Path(files[(pair_part, name)]), w["window_s"] - lag / SR, "SW50R"

        (a, a_start, a_model), (b, b_start, b_model) = source(row["first"]), source(row["second"])
        if row["kind"] == "test":
            # The judge's closer option is A on exactly half the test pairs.
            judge_first = by_id[row["id"]]["log_ratio"]["judge"] < 0
            seed = seed_for(judge_first == (row["id"] in judge_first_as_a), rng)
        else:
            seed = rng.getrandbits(63)
        n = f"{row['trial']:02d}"
        cmd = [sys.executable, str(PLUGIN_ROOT / "scripts" / "build_rab_audition.py"),
               "--reference", str(reference), "--reference-regime", "isolated_stem",
               "--reference-start", f"{w['window_s']:.6f}",
               "--a", str(a), "--a-start", f"{a_start:.6f}", "--a-amp-model", a_model,
               "--b", str(b), "--b-start", f"{b_start:.6f}", "--b-amp-model", b_model,
               "--duration", str(SEGMENT_S), "--mono",
               "--out", str(out_dir / f"trial-{n}.flac"),
               "--key", str(private / f"trial-{n}.key.json"),
               "--seed", str(seed)]
        done = subprocess.run(cmd, capture_output=True, text=True)
        (private / f"build-{n}.log").write_text(done.stdout + done.stderr)
        if done.returncode:
            die(f"trial {n} failed to build; see {private / f'build-{n}.log'}")
    (private / "trials.json").write_text(trials_text)      # what the scorer checks against
    (private / "order.json").write_text(json.dumps(
        {"trials_sha256": hashlib.sha256(trials_text.encode()).hexdigest(), "order": order},
        indent=1) + "\n")
    lines = ["# Answers", "",
             "For each trial: Reference, A, B, played twice. Which of A and B is closer to",
             "the Reference? Write A, B or ? (can't tell). Same headphones and level throughout.",
             ""]
    for sitting in (1, 2):
        lines.append(f"## Sitting {sitting}")
        lines += [f"{r['trial']:02d}: " for r in order if r["sitting"] == sitting]
        lines.append("")
    (out_dir / "ANSWERS.md").write_text("\n".join(lines))
    print(f"built {len(order)} trials in {out_dir}; keys and order in {private} (do not open "
          f"until every answer is recorded)")


if __name__ == "__main__":
    guarded(main)
