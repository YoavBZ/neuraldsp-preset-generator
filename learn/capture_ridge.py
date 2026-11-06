"""N9b: does a ridge gain from capture rows? `M-pcs`, the mel ridge at 64 PCs, fitted per capture fold on N9's rows with and
without the capture rows, read on the held capture units (`docs/capture-training-plan.md`; ledger `phase_n9b`).

    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    PYTHONPATH=. $TORCH_PY -m learn.capture_ridge OUT.json       # CPU, zero renders

A ridge takes each real unit once, so here capture rows sit on top of BKS's and GOAT's, which N9's pair could not show. Every
row sharing a DI file with a held capture unit leaves both fits (`capture_train.rows_of`). The second batch, V-real, the NS
songs and the panel are not read.
"""
from __future__ import annotations

import json
import pickle
import sys

import numpy as np

from learn import capture_train as CT

ARMS = {"M-ctl": "C-ctl", "M-cap": "C-cap"}
PAIRS = (("M-cap", "M-ctl"), ("M-cap", "C-cap"), ("M-ctl", "C-ctl"))
PCS = 64


# --- pure -----------------------------------------------------------------------------------------------------------

def unique_rows(rows):
    """`rows` with each real unit once, the first of its cycled copies, in order."""
    seen, out = set(), []
    for r in rows:
        if r["real"] not in seen:
            seen.add(r["real"])
            out.append(r)
    return out


def join_answers(rows, key_of, answers):
    """`answers` ({key: {label: answer}}) copied onto `rows` by `key_of(row)`; refuses a row with no answer."""
    for r in rows:
        got = answers.get(key_of(r))
        if got is None:
            raise SystemExit(f"no answer for {key_of(r)}")
        r.update(got)
    return rows


# --- the stored data --------------------------------------------------------------------------------------------------

def fold_answers(k, src, recs, cu):
    """Each arm's answers on fold k's held units. -> {(rig, amp): {f"{arm}_ans": answer}}."""
    from learn import eat_read as ER
    from learn import pipeline_fix as P
    from learn import trusted_data_t3 as T3

    enc = T3.encode_for(T3.FULL)
    held = P.record_rows(recs, cu, 0)
    di = {**src[1], **src[3], **src[5]}
    out = {(r["rig"], h["amp"]): {} for r, h in zip(recs, held)}
    for arm, rows_arm in ARMS.items():
        rows = unique_rows(CT.rows_of(rows_arm, k, src)[0])
        Y = [np.stack(z) for z in zip(*(enc(r["label"]) for r in rows))]
        mu, _ = ER.fit_predict(rows, [di[r["real"]]["di"] for r in rows], [r["real"] for r in rows], held,
                               [h["real"] for h in held], (Y[0], Y[1]), rep="mel", pcs=PCS)
        for j, (r, h) in enumerate(zip(recs, held)):
            out[(r["rig"], h["amp"])][f"{arm}_ans"] = mu[j]
        print(arm, "fold", k, len(rows), "rows done", flush=True)
    return out


def control():
    """`fit_predict` at these settings must give the stored `M-pcs` answers on BKS's and GOAT's fold 0, within 1e-6."""
    from learn import bakeoff as B
    from learn import eat_read as ER
    from learn import pipeline_fix as P
    from learn import trusted_data_t3 as T3

    _, data = B.base_rows()
    enc = T3.encode_for(T3.FULL)
    rows, clusters, _ = B.training_set("real", 0, data)
    _, held, _ = P.dfix_rows_of(*data, 0)
    Y = [np.stack(z) for z in zip(*(enc(r["label"]) for r in rows))]
    mu, _ = ER.fit_predict(rows, clusters, [r["real"] for r in rows], held, [h["real"] for h in held], (Y[0], Y[1]), rep="mel", pcs=PCS)
    stored = [r for r in pickle.load(open(P.out_dir() / "eat" / "read.json.rows.pkl", "rb")) if r["fold"] == 0]
    worst = float(np.abs(np.stack([r["M-pcs_ans"] for r in stored]) - mu).max())
    if worst > 1e-6:
        raise SystemExit(f"control: `M-pcs` differs from its stored answers by {worst}")
    print(f"CONTROL OK: {len(stored)} rows, worst {worst}", flush=True)


def main(out, n9_rows):
    from learn import pipeline_fix as P

    P.require("phase_n9b")
    from learn import capture_labels as CL
    from learn import pretrain_set as PS
    from learn import reads_v3 as R

    control()
    src = CT.sources()
    recs = CL.search_records()
    cu = {u["unit"]: u for u in CL.units_of()}
    answers = {}
    for k in range(CT.FOLDS):
        answers.update(fold_answers(k, src, [r for u, r in sorted(recs.items()) if cu[u]["fold"] == k], cu))
    rows = join_answers(pickle.load(open(n9_rows, "rb")), lambda r: (r["rec"], r["amp"]), answers)
    pickle.dump(rows, open(out + ".rows.pkl", "wb"))
    labels = (*ARMS, "C-ctl", "C-cap")
    res = {"arms": {}, "jackknife": {}, "jackknife_std": {}, "size": {x: CT.size_rows(rows, x) for x in ARMS},
           "heads": {x: CT.head_rows(rows, x) for x in ARMS}}
    for cls in ("all", "crunch", "clean"):
        S = [r for r in rows if cls in ("all", r["cls"])]
        creators = sorted({r["cluster"] for r in S})
        blocks = {x: R.blocks(S, x) for x in labels}
        res["arms"][cls] = {x: {g: list(v) for g, v in R.corr(blocks[x]).items()} for x in labels}
        for p, q in PAIRS:
            for name, at in (("jackknife", 0), ("jackknife_std", 3)):
                res[name][f"{cls}/{p}-{q}"] = {g: CT.jackknife_t(
                    lambda c, g_=g: R.corr(blocks[p], drop=c)[g_][at] - R.corr(blocks[q], drop=c)[g_][at], creators, PS.t90)
                    for g in R.GROUPS}
    res["branch"] = CT.reading(res["jackknife"]["all/M-cap-M-ctl"], res["jackknife_std"]["all/M-cap-M-ctl"])
    json.dump(res, open(out, "w"), indent=1, default=float)
    print(res["jackknife"]["all/M-cap-M-ctl"], "\nBRANCH:", res["branch"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
