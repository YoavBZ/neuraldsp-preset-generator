"""N9: do capture labels teach what they can test? FTm's recipe with and without the first batch's trusted rows
(`docs/capture-training-plan.md`; ledger `phase_n9`).

    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    PYTHONPATH=. $TORCH_PY -m learn.capture_train tune --arm C-cap --fold 0 --seed 20261042   # one run (MPS)
    PYTHONPATH=. $TORCH_PY -m learn.capture_train read OUT.json                                # held read (CPU)

Folds are the capture units' stored creator folds. Model k trains on BKS's and GOAT's labels, and in C-cap and C-mic on the
trusted capture units of the other folds, less every row sharing a DI file with a fold-k capture unit, so a held unit's
capture, creator and performance stay out of its model. C-ctl has the same drops and no capture row. C-ctl and C-cap take
the same number of updates, FTm's, so C-cap shows each BKS and GOAT row a third less: C-cap - C-ctl is capture rows in place
of a third of those updates. C-c39 is C-ctl at C-cap's epochs, so C-cap - C-c39 is the same rows shown as often. The second
batch stays unread, and V-real, the NS songs and the panel are not read.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import pickle
import statistics
import sys
import time

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

SEEDS = (20261042, 20261043)
FOLDS = 4
CAP_ROW0 = 5_000_000
CAP_PER_EPOCH = 300                  # as BKS's and GOAT's rows per epoch, so each source weighs alike
ARMS = {"C-ctl": ("A-ctl", False), "C-cap": ("A-ctl", True), "C-mic": ("A-mic", True), "C-c39": ("A-ctl", False)}   # (`bakeoff_train` loss, capture rows?)
PAIRS = (("C-cap", "C-ctl"), ("C-mic", "C-cap"), ("C-cap", "C-c39"))
DISK_FLOOR_GB = 33.0


# --- pure -----------------------------------------------------------------------------------------------------------

def held_dis(cap_units, k):
    """The DI files of fold k's capture units."""
    return {u["di"] for u in cap_units if u["fold"] == k}


def keep_clear(recs, unit_of, dis):
    """`recs` whose unit's DI file is not in `dis`."""
    return [r for r in recs if unit_of[r["unit"]]["di"] not in dis]


def steps(epochs, n_rows, batch):
    """The steps `epochs` take on `n_rows`."""
    return epochs * math.ceil(n_rows / batch)


def epochs_for(updates, n_rows, batch):
    """The epochs that give about `updates` steps on `n_rows`, at least one."""
    return max(1, int(round(updates / math.ceil(n_rows / batch))))


def jackknife_t(stat, clusters, t90):
    """A statistic with its delete-one-cluster 90% t interval. stat(drop) -> float, drop None or a cluster."""
    pt = stat(None)
    th = np.array([stat(c) for c in clusters])
    n = len(th)
    h = t90(n - 1) * math.sqrt((n - 1) / n * float(((th - th.mean()) ** 2).sum()))
    return {"point": pt, "lo": pt - h, "hi": pt + h, "clusters": n}


def reading(rows, std):
    """The declared map on C-cap - C-ctl's three rows, by jackknife. rows, std: {group: {point, lo, hi}}, raw and
    head-standardised. A clear raw row with its standardised pair at or below zero reads as moved spread."""
    clear_up = [g for g, r in rows.items() if r["lo"] > 0]
    up = [g for g in clear_up if std[g]["point"] > 0]
    down = [g for g, r in rows.items() if r["hi"] < 0]
    if up and down:
        return "mixed"
    if up:
        return "a lead"
    if down:
        return "a cost to review"
    return "moved spread" if clear_up else "undecided"


# --- the stored data --------------------------------------------------------------------------------------------------

def sources():
    """(BKS records, their units, GOAT records, their units, trusted capture records, capture units)."""
    from learn import capture_labels as CL
    from learn import pipeline_fix as P

    brecs, by_unit, _ = P.real_labels(2)
    grecs, gunits, _ = P.goat_labels()
    caps = list(CL.search_records().values())
    cu = {u["unit"]: u for u in CL.units_of()}
    return brecs, by_unit, grecs, gunits, [r for r in caps if r["label"] is not None], cu


def rows_of(arm, k, src):
    """Model k's real rows for `arm`. -> (rows, counts)."""
    from learn import pipeline_fix as P

    brecs, by_unit, grecs, gunits, caps, cu = src
    dis = held_dis([cu[r["unit"]] for r in caps], k)
    g = keep_clear(grecs, gunits, dis)
    rows = (P.record_rows(P.cycled(brecs, max(P.REAL_PER_EPOCH, len(brecs))), by_unit, P.REAL_ROW0)
            + P.record_rows(P.cycled(g, max(P.GOAT_PER_EPOCH, len(g))), gunits, P.GOAT_ROW0))
    c = []
    if ARMS[arm][1]:
        c = [r for r in keep_clear(caps, cu, dis) if cu[r["unit"]]["fold"] != k]
        rows += P.record_rows(P.cycled(c, max(CAP_PER_EPOCH, len(c))), cu, CAP_ROW0)
    return rows, {"bks": len(brecs), "goat": len(g), "goat_of": len(grecs), "capture": len(c), "held_dis": len(dis)}


def ftm_updates():
    """FTm's steps: the median of its stored E on its own rows."""
    from learn import bakeoff_train as BT
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    es = [BT.stored_e(json.loads((P.out_dir() / "runs" / f"P2b-ftm-k{k}-{s}.json").read_text()))
          for k in range(FOLDS) for s in SEEDS]
    n = len(P.ft_real_rows(0, False)[0])
    return int(statistics.median(es)) * math.ceil(n / PS.BATCH)


def root():
    from learn import pipeline_fix as P

    return P.out_dir() / "captrain"


def cmd_tune(a):
    """One run: W's best state, `arm`'s rows, masked as FTm, FTm's updates."""
    from learn import pipeline_fix as P

    P.require("phase_n9")
    import torch

    from learn import bakeoff_train as BT
    from learn import pretrain_set as PS

    if PS.free_gb() < DISK_FLOOR_GB:
        raise SystemExit(f"DISK: free disk below {DISK_FLOOR_GB:.0f} GB")
    root().mkdir(parents=True, exist_ok=True)
    out = root() / f"{a.arm}-k{a.fold}-{a.seed}.pt"
    if out.exists():
        return print(out.name, "exists")
    e_ = P.require("phase_3")
    croot, _, _, _, dropped = P.recipe_inputs(pin=e_.get("phase_3_doubles"))
    src = sources()
    rows, counts = rows_of(a.arm, a.fold, src)
    doubled = P.doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
    data = P.DfixData(rows, P.rung_path(croot, "b", doubled), set(), {r["i"] for r in rows}, 1.0)
    P.mask_searched(data.Y, rows, P.A_menu_S())
    updates = ftm_updates()
    size = len(rows_of("C-cap", a.fold, src)[0]) if a.arm == "C-c39" else len(rows)   # C-c39 takes C-cap's epochs
    epochs = epochs_for(updates, size, PS.BATCH)
    torch.set_num_threads(2)
    t0 = time.time()
    net = BT.arm_start("A-ctl", a.seed)
    last = BT.train(net, data, np.arange(len(rows)), BT.loss_of(ARMS[a.arm][0]), a.seed, P.device(), epochs, BT.TUNE_LR, None,
                    f"{a.arm} k{a.fold} {a.seed}")
    BT.save_state(net, out)
    BT.run_record(out.with_suffix(".json"), arm=a.arm, seed=a.seed, fold=a.fold, epochs=epochs, ftm_updates=updates,
                  steps=steps(epochs, len(rows), PS.BATCH), rows=len(rows), counts=counts, loss=last,
                  inputs_sha256=data.inputs_sha256, minutes=(time.time() - t0) / 60)
    print(f"{a.arm} k{a.fold} {a.seed}: {epochs} epochs on {len(rows)} rows, last loss {last:.4f}", flush=True)


def load_net(name, seed, _which=None):
    """A stored run, `name` as `arm-k{k}`."""
    import torch

    from learn import full_space as F

    net = F.build_net()
    net.load_state_dict(torch.load(root() / f"{name}-{seed}.pt", map_location="cpu"))
    return net.eval()


def size_rows(rows, label):
    """Per group, how the answers do as answers: squared error against the cell mean, and the slope of label on answer."""
    from learn import reads_v3 as R

    out = {}
    for g, heads in R.HEADS.items():
        a, y = [], []
        for j in heads:
            cells = {}
            for r in rows:
                if r["cm"][j] > 0:
                    cells.setdefault((r["fold"], r["amp"], r["cls"]), []).append((float(r[f"{label}_ans"][j]), float(r["c"][j])))
            for v in cells.values():
                x = np.array(v)
                if len(x) > 1:
                    x -= x.mean(0)
                    a += x[:, 0].tolist()
                    y += x[:, 1].tolist()
        a, y = np.array(a), np.array(y)
        out[g] = {"mse_skill": float(1 - ((y - a) ** 2).mean() / (y ** 2).mean()), "slope": float((a * y).sum() / (a * a).sum()),
                  "n": len(a)}
    return out


def head_rows(rows, label):
    """Per head, r and answer spread against the labels', demeaned within (fold, amp, class): which knobs carry a read."""
    from learn import full_space as F
    from learn import reads_v3 as R

    out = {}
    for g, heads in R.HEADS.items():
        for j in heads:
            cells, a, y = {}, [], []
            for r in rows:
                if r["cm"][j] > 0:
                    cells.setdefault((r["fold"], r["amp"], r["cls"]), []).append((float(r[f"{label}_ans"][j]), float(r["c"][j])))
            for v in cells.values():
                x = np.array(v)
                if len(x) > 1:
                    x -= x.mean(0)
                    a += x[:, 0].tolist()
                    y += x[:, 1].tolist()
            a, y = np.array(a), np.array(y)
            if len(a) > 2 and a.std() > 0 and y.std() > 0:
                out[F.CONT[j]] = {"group": g, "n": len(a), "r": float(np.corrcoef(a, y)[0, 1]), "spread": float(a.std() / y.std())}
    return out


def cmd_read(a):
    from learn import pipeline_fix as P

    P.require("phase_n9")
    from learn import capture_labels as CL
    from learn import pretrain_set as PS
    from learn import reads_capture as RC
    from learn import reads_v3 as R

    grecs, gunits, _ = P.goat_labels()
    RC.control(grecs, gunits)
    print("CONTROL OK", flush=True)
    recs = CL.search_records()
    cu = {u["unit"]: u for u in CL.units_of()}
    rows = []
    for k in range(FOLDS):
        mine = [r for u, r in sorted(recs.items()) if cu[u]["fold"] == k]
        rows += RC.read_fold(k, mine, cu, {x: (f"{x}-k{{k}}", None) for x in ARMS}, load_net)
        print("fold", k, len(mine), "done", flush=True)
    pickle.dump(rows, open(a.out + ".rows.pkl", "wb"))
    RC.MODELS, RC.PAIRS = {x: None for x in ARMS}, PAIRS
    res = RC.report(rows)
    res["jackknife"], res["jackknife_std"] = {}, {}
    for cls in RC.CLASSES:
        S = [r for r in rows if cls in ("all", r["cls"])]
        creators = sorted({r["cluster"] for r in S})
        blocks = {x: R.blocks(S, x) for x in ARMS}
        for p, q in PAIRS:
            res["jackknife"][f"{cls}/{p}-{q}"] = {g: jackknife_t(
                lambda c, g_=g: R.corr(blocks[p], drop=c)[g_][0] - R.corr(blocks[q], drop=c)[g_][0], creators, PS.t90)
                for g in R.GROUPS}
            res["jackknife_std"][f"{cls}/{p}-{q}"] = {g: jackknife_t(
                lambda c, g_=g: R.corr(blocks[p], drop=c)[g_][3] - R.corr(blocks[q], drop=c)[g_][3], creators, PS.t90)
                for g in R.GROUPS}
    res["heads"] = {x: head_rows(rows, x) for x in ARMS}
    res["size"] = {x: size_rows(rows, x) for x in ARMS}
    res["branch"] = reading(res["jackknife"]["all/C-cap-C-ctl"], res["jackknife_std"]["all/C-cap-C-ctl"])
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    for cls in RC.CLASSES:
        for x in ARMS:
            q = res[f"{cls}/{x}"]
            print(cls, x, q["parts"], "  ".join(f"{g} {q['r'][g]['r']:+.3f} {q['r'][g]['boot90']}" for g in R.GROUPS), flush=True)
    print(res["jackknife"]["all/C-cap-C-ctl"], "\nBRANCH:", res["branch"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="step", required=True)
    t = sub.add_parser("tune")
    t.add_argument("--arm", choices=tuple(ARMS), required=True)
    t.add_argument("--fold", type=int, choices=range(FOLDS), required=True)
    t.add_argument("--seed", type=int, choices=SEEDS, required=True)
    r = sub.add_parser("read")
    r.add_argument("out")
    a = ap.parse_args(argv)
    {"tune": cmd_tune, "read": cmd_read}[a.step](a)


if __name__ == "__main__":
    main()
