"""N10: the trained models on the second capture batch, in no model's real rows (`docs/capture-training-plan.md`;
ledger `phase_n10`).

    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    PYTHONPATH=. $TORCH_PY -m learn.reads_fresh OUT.json       # CPU, zero renders, zero training

Each network arm answers by the mean of all its fold models, both seeds, since no fold held these units. The ridges fit on every
BKS and GOAT label, and with the first batch's trusted labels, each record once. Read as N6, variant 0, with the ridges on the mean of 25 backings beside, r demeaned within (amp,
class, head), clusters by creator. V-real, the NS songs and the panel are not read.
"""
from __future__ import annotations

import json
import pickle
import sys

import numpy as np

from learn import capture_ridge as CR
from learn import capture_train as CT

NETS = {"FTM": ("P2b-ftm-k{k}", "final"), "C-ctl": ("C-ctl-k{k}", None), "C-cap": ("C-cap-k{k}", None), "C-mic": ("C-mic-k{k}", None),
        "C-c39": ("C-c39-k{k}", None)}
PAIRS = (("C-cap", "C-ctl"), ("M-cap", "M-ctl"), ("C-mic", "C-cap"), ("M-ctl", "C-ctl"), ("C-ctl", "FTM"), ("C-cap", "C-c39"),
         ("M-cap-25", "M-ctl-25"))
PRIMARY = PAIRS[:2]
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


def lead_holds(rows, std, without):
    """A lead's clear rows (clear above, standardised point above zero) keep their sign without the shared creators."""
    return all(without[g]["point"] > 0 for g, r in rows.items() if r["lo"] > 0 and std[g]["point"] > 0)


def decide(net, ridge):
    """The declared next step from the two primary pairs' `capture_train.reading`. A lead that fails `lead_holds` comes in here
    as "undecided"."""
    if net == "a lead":
        return "train on both batches, in its own declaration"
    if ridge == "a lead":
        return "the ridge by the score first, no new network training"
    if "a cost to review" in (net, ridge):
        return "no new training: review the cost, against C-c39 for the nets and the offset for the ridge"
    return "no new training on captures from this read"


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


def ridge_answers(held, src, units):
    """M-ctl and M-cap on the held rows, on variant 0 and the mean of 25 backings, fitted on all of BKS's and GOAT's records,
    and the first batch's trusted ones. `units`: the held units', for the refusal of a held DI."""
    from learn import eat_read as ER
    from learn import pipeline_fix as P
    from learn import trusted_data_t3 as T3

    brecs, bu, grecs, gu, caps, cu = src
    enc = T3.encode_for(T3.FULL)
    base = P.record_rows(brecs, bu, P.REAL_ROW0) + P.record_rows(grecs, gu, P.GOAT_ROW0)
    di = {**bu, **gu, **cu}
    out = {}
    for label, rows in (("M-ctl", base), ("M-cap", base + P.record_rows(caps, cu, CT.CAP_ROW0))):
        clusters = [di[r["real"]]["di"] for r in rows]
        if len({(r["real"], r["amp"]) for r in rows}) != len(rows):
            raise SystemExit(f"{label}: not one row per labelled record")
        if {units[h["real"]]["di"] for h in held} & set(clusters):
            raise SystemExit(f"{label}: a held DI in the training rows")
        Y = [np.stack(z) for z in zip(*(enc(r["label"]) for r in rows))]
        for name, back in ((label, 1), (f"{label}-25", 25)):
            out[name] = ER.fit_predict(rows, clusters, [r["real"] for r in rows], held, [h["real"] for h in held], (Y[0], Y[1]),
                                       rep="mel", pcs=PCS, held=back)[0]
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
    src = CT.sources()
    shared = {src[5][r["unit"]]["creator"] for r in src[4]}      # creators also in the first batch's trusted rows
    for label, mu in ridge_answers(held, src, units).items():
        for j, r in enumerate(rows):
            r[f"{label}_ans"] = mu[j]
    rows = one_fold(rows)
    pickle.dump(rows, open(out + ".rows.pkl", "wb"))
    labels = (*NETS, "M-ctl", "M-cap", "M-ctl-25", "M-cap-25")
    res = {"units": len(rows), "creators": len({r["cluster"] for r in rows}), "arms": {}, "jackknife": {}, "jackknife_std": {},
           "size": {x: CT.size_rows(rows, x) for x in labels}, "heads": {x: CT.head_rows(rows, x) for x in labels}}
    rng = np.random.default_rng(R.RNG_SEED)
    res["swap"] = {cls: {x: {"total": R.t_row([(r["cluster"], float(r[f"{x}_swap"].sum())) for r in rows
                                               if r[f"{x}_swap"] is not None and cls in ("all", r["cls"])]),
                             **{q: R.t_row([(r["cluster"], float(r[f"{x}_swap"][i])) for r in rows
                                            if r[f"{x}_swap"] is not None and cls in ("all", r["cls"])])
                                for i, q in enumerate(("knob", "switch", "mic"))}} for x in NETS} for cls in ("all", "clean")}
    res["shared_creators"] = sorted(shared & {r["cluster"] for r in rows})
    others = [r for r in rows if r["cluster"] not in shared]
    res["units_without_shared"] = len(others)
    blocks_o = {x: R.blocks(others, x) for x in labels}
    res["without_shared"] = {f"{p}-{q}": {g: CT.jackknife_t(
        lambda c, g_=g: R.corr(blocks_o[p], drop=c)[g_][0] - R.corr(blocks_o[q], drop=c)[g_][0],
        sorted({r["cluster"] for r in others}), PS.t90) for g in R.GROUPS} for p, q in PRIMARY}
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
    def held_up(branch, p, q):
        key = f"all/{p}-{q}"
        if branch != "a lead" or lead_holds(res["jackknife"][key], res["jackknife_std"][key], res["without_shared"][f"{p}-{q}"]):
            return branch
        return "undecided"

    res["decision"] = decide(held_up(res["branch"], "C-cap", "C-ctl"), held_up(res["branch_ridge"], "M-cap", "M-ctl"))
    json.dump(res, open(out, "w"), indent=1, default=float)
    for x in labels:
        print(x, {g: round(res["arms"]["all"][x][g]["r"], 3) for g in R.GROUPS})
    print("BRANCH:", res["branch"], "| ridge:", res["branch_ridge"], "|", res["decision"])


if __name__ == "__main__":
    main(sys.argv[1])
