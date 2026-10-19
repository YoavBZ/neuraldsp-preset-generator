"""Zero-render check (b): judge v3 against the listener on record-match listening check 1.

    .venv/bin/python -m learn.record_match_v3        # reads the stored clips, writes the report

The check stored each arm's held-half render (`private/renders/<slug>.npz`, the render sliced at
the held half's bounds). Placed back at those bounds in a silent buffer, the default judge
reproduces the stored held-half scores (the check below), so the same clips are re-scored with
judge v3 (`analysis.aligned.JUDGE_V3`) and both rankings are set beside the listener's.
"""

from __future__ import annotations

import itertools
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

OUT = pathlib.Path("~/ndsp-presets/learn/record-match-v3").expanduser()
JUDGES = ("default", "v3")


def agreement(ear, d, arms):
    """Spearman's rho (all arms and S, H, D only), pairwise agreements and the top pick."""
    from learn import record_match_listening as RM

    jr = dict(zip(arms, RM.ranks([d[a] for a in arms])))
    sub = [a for a in arms if a != "C"]
    return {"rho": RM.spearman([ear[a] for a in arms], [jr[a] for a in arms]),
            "rho_SHD": RM.spearman(RM.ranks([ear[a] for a in sub]), RM.ranks([d[a] for a in sub])),
            "pairs": sum((ear[x] < ear[y]) == (d[x] < d[y]) for x, y in itertools.combinations(arms, 2)),
            "pairs_SHD": sum((ear[x] < ear[y]) == (d[x] < d[y]) for x, y in itertools.combinations(sub, 2)),
            "top": min(arms, key=lambda a: d[a]), "order": "".join(sorted(arms, key=lambda a: d[a]))}


def main():
    import numpy as np

    from analysis.aligned import JUDGE_V3, aligned_distance
    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR
    from learn import knob_ceiling as K
    from learn import record_match_listening as RM

    key = json.loads((RM.PRIVATE / "key.json").read_text())
    score = json.loads((RM.PRIVATE / "score.json").read_text())
    scores, worst = {}, 0.0
    for n, t in key["trials"].items():
        if t.get("repeat_of"):
            continue
        part = A.part_of("F", t["slug"])
        ref, di, lag = CR.mono(part["crop"] / "reference.wav"), RM.raw_di(part), part["judge_lag"]
        clips = np.load(RM.PRIVATE / "renders" / f"{t['slug']}.npz")
        a, b = K.R.HALVES[t["held"]]
        scores[n] = {}
        for arm in RM.ARMS:
            y = clips[arm]
            full = np.zeros((int((b + 1) * A.SR), y.shape[1]))
            full[int(a * A.SR):int(a * A.SR) + len(y)] = y
            kw = dict(lag=lag, render_latency=K.P.LATENCY, start_s=a, end_s=b)
            dflt = aligned_distance(ref, full, di, **kw).distance
            worst = max(worst, abs(np.log(dflt / t["judge_held"][arm])))
            scores[n][arm] = {"default": dflt, "v3": aligned_distance(ref, full, di, **kw, **JUDGE_V3).distance}
    rows = []
    for tr in score["trials"]:
        src = str(tr["repeat_of"] or tr["trial"])
        row = {"trial": tr["trial"], "slug": tr["slug"], "ear": "".join(sorted(RM.ARMS, key=lambda a: tr["arm_ranks"][a]))}
        for j in JUDGES:
            row[j] = agreement(tr["arm_ranks"], {a: scores[src][a][j] for a in RM.ARMS}, RM.ARMS)
        rows.append(row)
    main5 = [r for r in rows if r["trial"] <= 5]
    summary = {j: {"rho_mean": sum(r[j]["rho"] for r in main5) / 5, "rho_positive": sum(r[j]["rho"] > 0 for r in main5),
                   "rho_SHD_mean": sum(r[j]["rho_SHD"] for r in main5) / 5,
                   "pairs": sum(r[j]["pairs"] for r in main5), "pairs_SHD": sum(r[j]["pairs_SHD"] for r in main5),
                   "top_matches_ear": sum(r[j]["top"] == r["ear"][0] for r in main5),
                   "mean_rank": {a: sum(RM.ranks([scores[str(r['trial'])][x][j] for x in RM.ARMS])[RM.ARMS.index(a)]
                                        for r in main5) / 5 for a in RM.ARMS}}
               for j in JUDGES}
    rep = {"default_reproduces_stored_max_abs_log": worst, "scores": scores, "trials": rows, "summary": summary}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(rep, indent=1))
    print("default judge vs stored: max |log|", f"{worst:.2e}")
    for r in rows:
        print(r["trial"], r["slug"], "ear", r["ear"], *(f"{j} {r[j]['order']} rho {r[j]['rho']:+.1f}" for j in JUDGES))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
