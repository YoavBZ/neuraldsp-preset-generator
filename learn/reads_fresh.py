"""N10: the trained models on the second capture batch, which no model trained on or was chosen on (`docs/capture-training-plan.md`;
ledger `phase_n10`).

    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    PYTHONPATH=. $TORCH_PY -m learn.reads_fresh OUT.json       # CPU, zero renders, zero training

Each network arm answers by the mean of all its fold models, both seeds, since no fold held these units. The ridges fit on every
BKS and GOAT label, and with the first batch's trusted labels, each record once. Read as N6, variant 0, r demeaned within (amp,
class, head), clusters by creator. V-real, the NS songs and the panel are not read.
"""
from __future__ import annotations

import json
import pickle
import sys

import numpy as np

from learn import capture_ridge as CR
from learn import capture_train as CT

NETS = {"FTM": ("P2b-ftm-k{k}", "final"), "C-ctl": ("C-ctl-k{k}", None), "C-cap": ("C-cap-k{k}", None), "C-mic": ("C-mic-k{k}", None)}
PAIRS = (("C-cap", "C-ctl"), ("M-cap", "M-ctl"), ("C-mic", "C-cap"), ("M-ctl", "C-ctl"), ("C-ctl", "FTM"))
PCS = 64


# --- pure -----------------------------------------------------------------------------------------------------------

def mean_folds(per_fold, label):
    """One row list from a list of `read_fold` outputs on the same rows: `label`'s answers and swaps averaged over folds."""
    out = [dict(r) for r in per_fold[0]]
    for j, r in enumerate(out):
        r[f"{label}_ans"] = np.mean([f[j][f"{label}_ans"] for f in per_fold], 0)
        sw = [f[j][f"{label}_swap"] for f in per_fold]
        r[f"{label}_swap"] = None if any(x is None for x in sw) else np.mean(sw, 0)
    return out


def one_fold(rows):
    """Rows read as one set: every row in fold 0, so r is demeaned within (amp, class, head) alone."""
    return [dict(r, fold=0) for r in rows]


# --- the stored data --------------------------------------------------------------------------------------------------

def load(name, seed, which):
    from learn import pipeline_fix as P

    return CT.load_net(name, seed) if name.startswith("C-") else P.load_run(name, seed, which)[0]


def fresh_records():
    """(the second batch's records with a label, its units): its own trusted set, with the batch switched back after."""
    from learn import capture_labels as CL

    keep = CL.BATCH
    CL.BATCH = CL.BATCH2
    try:
        recs = [r for r in CL.search_records().values() if r["label"] is not None]
        units = {u["unit"]: u for u in CL.units_of()}
    finally:
        CL.BATCH = keep
    return sorted(recs, key=lambda r: r["unit"]), units


def ridge_answers(held, src):
    """M-ctl and M-cap on the held rows, fitted on all of BKS's and GOAT's records, and the first batch's trusted ones."""
    from learn import eat_read as ER
    from learn import pipeline_fix as P
    from learn import trusted_data_t3 as T3

    brecs, bu, grecs, gu, caps, cu = src
    enc = T3.encode_for(T3.FULL)
    base = P.record_rows(brecs, bu, P.REAL_ROW0) + P.record_rows(grecs, gu, P.GOAT_ROW0)
    di = {**bu, **gu, **cu}
    out = {}
    for label, rows in (("M-ctl", base), ("M-cap", base + P.record_rows(caps, cu, CT.CAP_ROW0))):
        Y = [np.stack(z) for z in zip(*(enc(r["label"]) for r in rows))]
        mu, _ = ER.fit_predict(rows, [di[r["real"]]["di"] for r in rows], [r["real"] for r in rows], held,
                               [h["real"] for h in held], (Y[0], Y[1]), rep="mel", pcs=PCS)
        out[label] = mu
    return out


def main(out):
    from learn import pipeline_fix as P

    P.require("phase_n10")
    from learn import pretrain_set as PS
    from learn import reads_capture as RC
    from learn import reads_v3 as R

    grecs, gunits, _ = P.goat_labels()
    RC.control(grecs, gunits)
    print("CONTROL OK", flush=True)
    CR.control()
    recs, units = fresh_records()
    rows = None
    for label, spec in NETS.items():
        per = [RC.read_fold(k, recs, units, {label: spec}, load) for k in range(CT.FOLDS)]
        got = mean_folds(per, label)
        rows = got if rows is None else [{**r, f"{label}_ans": g[f"{label}_ans"], f"{label}_swap": g[f"{label}_swap"]}
                                         for r, g in zip(rows, got)]
        print(label, "done", flush=True)
    held = P.record_rows(recs, units, 0)
    for label, mu in ridge_answers(held, CT.sources()).items():
        for j, r in enumerate(rows):
            r[f"{label}_ans"] = mu[j]
    rows = one_fold(rows)
    pickle.dump(rows, open(out + ".rows.pkl", "wb"))
    labels = (*NETS, "M-ctl", "M-cap")
    res = {"units": len(rows), "creators": len({r["cluster"] for r in rows}), "arms": {}, "jackknife": {}, "jackknife_std": {},
           "size": {x: CT.size_rows(rows, x) for x in labels}, "heads": {x: CT.head_rows(rows, x) for x in labels}}
    rng = np.random.default_rng(R.RNG_SEED)
    for cls in ("all", "clean"):
        S = [r for r in rows if cls in ("all", r["cls"])]
        creators = sorted({r["cluster"] for r in S})
        blocks = {x: R.blocks(S, x) for x in labels}
        res["arms"][cls] = {x: R.read_r(S, x, R.PERMS, rng)[0] for x in labels}
        for p, q in PAIRS:
            for name, at in (("jackknife", 0), ("jackknife_std", 3)):
                res[name][f"{cls}/{p}-{q}"] = {g: CT.jackknife_t(
                    lambda c, g_=g: R.corr(blocks[p], drop=c)[g_][at] - R.corr(blocks[q], drop=c)[g_][at], creators, PS.t90)
                    for g in R.GROUPS}
    res["branch"] = CT.reading(res["jackknife"]["all/C-cap-C-ctl"], res["jackknife_std"]["all/C-cap-C-ctl"])
    res["branch_ridge"] = CT.reading(res["jackknife"]["all/M-cap-M-ctl"], res["jackknife_std"]["all/M-cap-M-ctl"])
    json.dump(res, open(out, "w"), indent=1, default=float)
    for x in labels:
        print(x, {g: round(res["arms"]["all"][x][g]["r"], 3) for g in R.GROUPS})
    print("BRANCH:", res["branch"], "| ridge:", res["branch_ridge"])


if __name__ == "__main__":
    main(sys.argv[1])
