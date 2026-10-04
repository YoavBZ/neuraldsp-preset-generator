#!/usr/bin/env python3
"""Stage 0b: score the listening validation as declared (`docs/listening-validation-plan.md`).

    python scripts/score_listening_validation.py \\
        --private-dir ~/ndsp-presets/runs/listening-validation/private \\
        --answers ~/ndsp-presets/runs/listening-validation/trials/ANSWERS.md --json score.json

`--answers` is the listener's sheet: one line per trial, "NN: A", "NN: B" or "NN: ?"
(can't tell). Every trial must be answered, and the sheet's sha256 is recorded, before
any key is read. The trial list (`trials.json` in the private folder) must match the one
the files were built from. Two or more missed hidden references void the test and
nothing is scored. On the test pairs the listener decided, the judge (default bands) is
**validated** at 70% or more agreement with a one-sided exact binomial p < 0.05,
**rejected** when the one-sided 95% upper bound on its agreement is under 70%, and the
result is **inconclusive** otherwise or with fewer than 12 decided pairs. ALM, the union
band set and v3c are reported on the same pairs. Can't-tell answers are never counted as
half.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

REPORTED = ("judge_union", "alm", "v3c")
MIN_DECIDED, BAR = 12, 0.7


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--private-dir", type=pathlib.Path, required=True)
    ap.add_argument("--answers", type=pathlib.Path, required=True)
    ap.add_argument("--json", type=pathlib.Path)
    return ap


def parse_answers(text: str, count: int) -> dict:
    """{trial number: "A" | "B" | "?"}, refusing a missing, doubled or unreadable line."""
    answers = {}
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s*[:.)]?\s*([ABab?])\s*$", line)
        if not m:
            continue
        n = int(m.group(1))
        if n in answers:
            raise ValueError(f"trial {n} is answered twice")
        answers[n] = m.group(2).upper()
    missing = [n for n in range(1, count + 1) if n not in answers]
    if missing:
        raise ValueError(f"no answer for trials {missing}")
    return answers


def binomial_p(k: int, n: int) -> float:
    """One-sided P(X >= k) for X ~ Binomial(n, 0.5)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0


def upper_bound(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided Clopper-Pearson upper bound on a binomial proportion."""
    if k >= n:
        return 1.0

    def cdf(u):
        return sum(math.comb(n, i) * u ** i * (1 - u) ** (n - i) for i in range(k + 1))

    lo, hi = k / n, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) > alpha else (lo, mid)
    return hi


def outcome(k: int, n: int) -> str:
    if n < MIN_DECIDED:
        return "inconclusive"
    if k / n >= BAR and binomial_p(k, n) < 0.05:
        return "validated"
    if upper_bound(k, n) < BAR:
        return "rejected"
    return "inconclusive"


def score(plan: dict, order: list, keys: dict, answers: dict) -> dict:
    by_id = {t["id"]: t for t in plan["trials"] if "id" in t}
    chosen = {}                     # trial number -> chosen source name, or None (can't tell)
    for row in order:
        a = answers[row["trial"]]
        if a == "?":
            chosen[row["trial"]] = None
            continue
        role = keys[row["trial"]]["blind_key"][a]
        chosen[row["trial"]] = row[role]
    hidden = [r for r in order if r["kind"] == "hidden_reference"]
    missed = [r["trial"] for r in hidden if chosen[r["trial"]] != "reference"]
    out = {"hidden_references_missed": missed, "valid": len(missed) < 2}
    if not out["valid"]:
        out["judge"] = "void"
        return out
    tests = [r for r in order if r["kind"] == "test"]
    decided = [r for r in tests if chosen[r["trial"]] is not None]
    out["test_pairs"] = len(tests)
    out["decided"] = len(decided)
    out["cant_tell_rate"] = 1 - len(decided) / len(tests) if tests else None

    def predicted(row, distance):
        lr = by_id[row["id"]]["log_ratio"][distance]
        return row["first"] if lr < 0 else row["second"]

    agreement = {}
    for d in ("judge",) + REPORTED:
        k = sum(chosen[r["trial"]] == predicted(r, d) for r in decided)
        agreement[d] = {"agree": k, "of": len(decided),
                        "share": k / len(decided) if decided else None,
                        "p_one_sided": binomial_p(k, len(decided))}
    out["agreement"] = agreement
    k, n = agreement["judge"]["agree"], agreement["judge"]["of"]
    out["judge"] = outcome(k, n)
    out["judge_upper_bound"] = upper_bound(k, n) if n else None
    split = [r for r in decided if by_id[r["id"]]["disagree"]]
    sided = sum(chosen[r["trial"]] == predicted(r, "judge") for r in split)
    out["judge_vs_v3c_where_they_disagree"] = {
        "listener_with_judge": sided, "of": len(split),
        "p_two_sided": min(1.0, 2 * min(binomial_p(sided, len(split)),
                                        binomial_p(len(split) - sided, len(split))))}
    repeats = []
    for r in order:
        if r["kind"] == "repeat":
            original = next(o for o in order if o.get("id") == r["of"])
            pair = (chosen[original["trial"]], chosen[r["trial"]])
            repeats.append({"of": r["of"], "same": None if None in pair else pair[0] == pair[1]})
    out["repeats"] = repeats
    return out


def main():
    args = build_parser().parse_args()
    private = args.private_dir.expanduser()
    built = json.loads((private / "order.json").read_text())
    order = built["order"]
    answers_text = args.answers.expanduser().read_text()
    try:
        answers = parse_answers(answers_text, len(order))
    except ValueError as error:
        die(str(error))
    answers_sha = hashlib.sha256(answers_text.encode()).hexdigest()
    (private / "answers.sha256").write_text(answers_sha + "\n")
    trials_text = (private / "trials.json").read_text()
    if hashlib.sha256(trials_text.encode()).hexdigest() != built["trials_sha256"]:
        die("the trial list differs from the one the files were built from")
    plan = json.loads(trials_text)
    # Only now, with every answer recorded and its hash written, are the keys read.
    keys = {r["trial"]: json.loads((private / f"trial-{r['trial']:02d}.key.json").read_text())
            for r in order}
    out = score(plan, order, keys, answers)
    out["answers_sha256"] = answers_sha
    print(json.dumps({k: v for k, v in out.items() if k != "repeats"}, indent=1))
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
