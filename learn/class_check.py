"""The class check (`docs/family-class-checks-plan.md` part B; ledger `preset-ladder` `phase_class_check`): does a
simple classifier name a held-out unit's class (clean or crunch) from the ladder's stored inputs clearly better than
0.80, research's point figure on the exam? Direction 3's test 1 of the 2026-11-19 strategic review. Zero renders.

    .venv/bin/python -m learn.class_check read     # -> PF/ladder/class/report.json

**Features** (`features`, level-free, both halves averaged): each band's mean over active frames less the mean across
bands (96); each band's sd over active frames (96); spectral flatness per frame, mean and sd (2); the frame level's sd
and 5-to-95% range (2); the mean over active frames of the loudest band less the mean band (1). Active frames: frame
level within 40 dB of the loudest frame, on the stored mel's dB scale (`pretrain_set.dequant`).
**Classifier:** scikit-learn's L2 logistic regression, C = 1, balanced class weights, standardised on the training
units only. Nothing tuned. Trained on `clean-kind` (the amp track alone: no lender) for the T rows.
**Split:** G (GOAT, cap1, n12: 348 units) by C3r's four folds, training on G's other folds less any unit sharing an
identity with the tested fold; R (BKS and the panel, Silent Waves out) tested as one block by a classifier trained on
all of G. R is never in any training.

`CK_TABLE` (the plan's D3_TABLE: CK-reads, CK-stop, CK-between) and its guard are declared here and tested in
`tests/test_class_check.py` before any run.
"""

from __future__ import annotations

import argparse
import json
import math
import time

PLAN = "docs/family-class-checks-plan.md"
PHASE = "phase_class_check"                   # ledger preset-ladder
OUT = "class"                                 # PF/ladder/class/
BAR = 0.80                                    # research's point figure on the exam (8 of 10)
LEAK_MARGIN = 0.02                            # T-alone may not exceed T-clean by more than this
ACTIVE_DB = 40.0
C_REG = 1.0
G_SETS, R_SETS = ("goat", "cap1", "n12"), ("bks", "panel")
EXCLUDED = ("Silent Waves",)                  # the panel's DI titles left out (vocal bleed)
DROWNING = "Drowning"                         # in only after its bleed check (plan C.9); the deciding read is without it
R_CLUSTERS = {"with Drowning": 12, "without Drowning": 11}
R_READS = {12: 10, 11: 9}                     # clusters right for CK-reads
R_STOP = {12: 6, 11: 6}                       # at or below R's majority cluster count (6 of 12; 6 of 11 without Drowning)
R_DECIDING = "without Drowning"
ROWS = {                                      # row: (trained on, tested on)
    "T-alone": ("clean-kind", "xlnoG@-3"),    # decides
    "T-full": ("clean-kind", "xl@-3"),
    "T-clean": ("clean-kind", "clean-kind"),  # the ceiling and the features' control
    "T-mix": ("clean-kind", "mixp@-3"),
    "In-alone": ("xlnoG@-3", "xlnoG@-3"),     # open to the lender leak; beside, and CK-stop's guard
    "In-full": ("xl@-3", "xl@-3")}
EXPECTED = {"G": 348, "R": 50, "off_side": 14, "goat_both_items": 35}
G_READINGS = ("above", "below", "neither")
R_READINGS = ("reads", "stop", "neither")
LEAK = ("ok", "high")
IN_READINGS = ("above", "not")

CK_TABLE = (                    # (predicate over (g, r, leak, in), code, next): each of the 36 combinations once
    (lambda g, r, lk, i: g == "above" and r == "reads" and lk == "ok", "CK-reads",
     "to the user: declare the paired read on the exam's stored renders (audio against research's class)"),
    (lambda g, r, lk, i: not (g == "above" and r == "reads" and lk == "ok") and (g == "below" or r == "stop")
     and i == "not", "CK-stop",
     "a simple classifier does not name the class better than research: class stays with research"),
    (lambda g, r, lk, i: not (g == "above" and r == "reads" and lk == "ok")
     and not ((g == "below" or r == "stop") and i == "not"), "CK-between",
     "not decided. The write-up says which side held it back. A pass that could be the lender leak needs a "
     "class-blind lender redraw (new separations, not declared); it is offered only on this cell"))


# --- the table (pure) ------------------------------------------------------------------------------------------------------

def table_guard():
    for g in G_READINGS:
        for r in R_READINGS:
            for lk in LEAK:
                for i in IN_READINGS:
                    if sum(bool(p(g, r, lk, i)) for p, _, _ in CK_TABLE) != 1:
                        raise SystemExit(f"CK_TABLE holds {(g, r, lk, i)} not once")
    if [c for _, c, _ in CK_TABLE] != ["CK-reads", "CK-stop", "CK-between"]:
        raise SystemExit("CK_TABLE's codes are not the three declared")
    for n in R_CLUSTERS.values():
        if not (R_STOP[n] < R_READS[n] <= n):
            raise SystemExit(f"R's thresholds for {n} clusters are not stop < reads <= n")


def ck_cell(g, r, lk, i):
    table_guard()
    hit = [(c, t) for p, c, t in CK_TABLE if p(g, r, lk, i)]
    if len(hit) != 1:
        raise SystemExit(f"CK_TABLE has {len(hit)} rows for {(g, r, lk, i)}")
    return hit[0]


def g_reading(row, bar=BAR):
    """(Pure.) "above" (lower end over the bar), "below" (upper end under it), else "neither"."""
    if row.get("lo90") is not None and row["lo90"] > bar:
        return "above"
    if row.get("hi90") is not None and row["hi90"] < bar:
        return "below"
    return "neither"


def r_reading(right, n):
    if right >= R_READS[n]:
        return "reads"
    if right <= R_STOP[n]:
        return "stop"
    return "neither"


def leak_reading(t_alone, t_clean, margin=LEAK_MARGIN):
    """(Pure.) "high" when T-alone's accuracy exceeds T-clean's by more than the margin on G (cluster-weighted) or
    on R (units); else "ok"."""
    for k in ("g_acc", "r_acc"):
        if t_alone[k] is None or t_clean[k] is None or t_alone[k] > t_clean[k] + margin:
            return "high"
    return "ok"


def clusters_right(rows):
    """(Pure.) rows [(cluster, right)] -> (clusters right, clusters); a cluster is right when most of its units are (a
    tie is wrong)."""
    by = {}
    for c, ok in rows:
        by.setdefault(c, []).append(bool(ok))
    return sum(sum(v) * 2 > len(v) for v in by.values()), len(by)


def cluster_acc(rows):
    """(Pure.) rows [(cluster, right)] -> the mean of cluster accuracies with a 90% t interval."""
    from learn import gear_family as G

    by = {}
    for c, ok in rows:
        by.setdefault(c, []).append(1.0 if ok else 0.0)
    return G.cluster_t(by)


def balanced(rows):
    """(Pure.) rows [(true, predicted)] -> balanced accuracy."""
    acc = []
    for c in ("clean", "crunch"):
        xs = [p == c for t, p in rows if t == c]
        if xs:
            acc.append(sum(xs) / len(xs))
    return sum(acc) / len(acc) if acc else None


def features(mel_u8):
    """(numpy.) The 197 level-free features of one half's uint8 mel [96, frames]."""
    import numpy as np

    from learn import pretrain_set as PS

    db = PS.dequant(mel_u8).astype(np.float64)               # [bands, frames] in dB
    p = 10.0 ** (db / 10.0)
    lvl = 10.0 * np.log10(p.mean(0) + 1e-30)                  # frame level
    act = lvl >= lvl.max() - ACTIVE_DB
    a = db[:, act]
    pa = p[:, act]
    mean_b = a.mean(1)
    f1 = mean_b - mean_b.mean()
    f2 = a.std(1)
    flat = np.exp(np.log(pa + 1e-30).mean(0)) / (pa.mean(0) + 1e-30)
    la = lvl[act]
    f3 = [flat.mean(), flat.std()]
    f4 = [la.std(), np.percentile(la, 95) - np.percentile(la, 5)]
    f5 = [(a.max(0) - a.mean(0)).mean()]
    return np.concatenate([f1, f2, f3, f4, f5])


def unit_features(halves):
    return (features(halves["A"][0]) + features(halves["B"][0])) / 2.0


def fit_predict(xtr, ytr, xte):
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    sc = StandardScaler().fit(xtr)
    m = LogisticRegression(C=C_REG, class_weight="balanced", max_iter=10000).fit(sc.transform(xtr), ytr)
    return list(m.predict(sc.transform(np.asarray(xte))))


# --- the data ----------------------------------------------------------------------------------------------------------------

def class_dir():
    from learn import preset_ladder as L

    return L.ladder_dir() / OUT


def title_of(ru):
    return ru["unit"].split("/")[2].split("@")[0] if ru["set"] == "panel" else None


def ladder_units(st):
    """The ladder's 400 units (one read part each), Silent Waves out; with set, fold, cluster (BKS: DI file; panel:
    band; G: the C3r cluster), class, identities (G) and lender band."""
    from learn import full_controls_c3r as R
    from learn import preset_ladder as L

    ld = json.loads((L.ladder_dir() / "lends.json").read_text())
    side = {}
    for k, v in ld["pool_by_band"].items():
        c, b = k.split("|")
        side.setdefault(b, {})[c] = v["examples"]
    side = {b: max(sorted(d), key=lambda c: d[c]) for b, d in side.items()}
    ents = {e["unit"]: e for e in st["entries"]}
    units = {}
    for ru in R.read_units(st):
        units.setdefault((ru["set"], ru["unit"]), ru)
    out = []
    for (s, u), ru in sorted(units.items()):
        if title_of(ru) in EXCLUDED:
            continue
        cls = ru["prt"]["cls"]
        if s in G_SETS and st["units"][s][u]["cls"] != cls:
            raise SystemExit(f"{u}: the read part's class differs from C3r's")
        band = ld["units"][u]["band"]
        out.append({"set": s, "unit": u, "ru": ru, "fold": ru["fold"], "cls": cls,
                    "cluster": ru["prt"]["band"] if s == "panel" else ru["cluster"],
                    "ids": ents[u]["ids"] if s in G_SETS else set(), "title": title_of(ru),
                    "lender": band, "off_side": side[band] != cls})
    return out


def checks(units):
    """Refusals: the declared counts, G and R share no DI file or band, R's cluster classes constant."""
    G = [x for x in units if x["set"] in G_SETS]
    Rr = [x for x in units if x["set"] in R_SETS]
    goat_items = {}
    for x in G:
        if x["set"] == "goat":
            goat_items.setdefault(x["cluster"], set()).add(x["cls"])
    got = {"G": len(G), "R": len(Rr), "off_side": sum(x["off_side"] for x in units),
           "goat_both_items": sum(len(v) == 2 for v in goat_items.values())}
    if got != EXPECTED:
        raise SystemExit(f"counts {got}, not the declared {EXPECTED}")
    for k in ("di", "band"):
        if {x["ru"]["prt"].get(k) for x in G} & {x["ru"]["prt"].get(k) for x in Rr} - {None}:
            raise SystemExit(f"G and R share a {k}")
    cl = {}
    for x in Rr:
        cl.setdefault(x["cluster"], set()).add(x["cls"])
    if any(len(v) != 1 for v in cl.values()):
        raise SystemExit("an R cluster holds both classes")
    for name, drop in (("with Drowning", False), ("without Drowning", True)):
        n = len({x["cluster"] for x in Rr if not (drop and x["title"] == DROWNING)})
        if n != R_CLUSTERS[name]:
            raise SystemExit(f"R {name}: {n} clusters, not {R_CLUSTERS[name]}")
    return goat_items


def row_read(units, feats, train_row, test_row, goat_items):
    """One row: G by folds (training on G's other folds less any unit sharing an identity with the tested fold), R by
    a classifier trained on all of G. -> (summary, per-unit predictions, banned count)."""
    import numpy as np

    G = [x for x in units if x["set"] in G_SETS]
    Rr = [x for x in units if x["set"] in R_SETS]
    pred, banned = {}, 0
    for k in sorted({x["fold"] for x in G}):
        te = [x for x in G if x["fold"] == k]
        ban = set().union(*[x["ids"] for x in te])
        tr = [x for x in G if x["fold"] != k and not (x["ids"] & ban)]
        banned += sum(1 for x in G if x["fold"] != k and x["ids"] & ban)
        ps = fit_predict(np.array([feats[train_row][x["unit"]] for x in tr]), [x["cls"] for x in tr],
                         [feats[test_row][x["unit"]] for x in te])
        pred.update({x["unit"]: p for x, p in zip(te, ps)})
    ps = fit_predict(np.array([feats[train_row][x["unit"]] for x in G]), [x["cls"] for x in G],
                     [feats[test_row][x["unit"]] for x in Rr])
    pred.update({x["unit"]: p for x, p in zip(Rr, ps)})

    def sub(xs):
        rows = [(x["cluster"], pred[x["unit"]] == x["cls"]) for x in xs]
        return {"units": len(xs), "acc_units": sum(r for _, r in rows) / len(rows) if rows else None,
                "acc_clusters": cluster_acc(rows), "balanced": balanced([(x["cls"], pred[x["unit"]]) for x in xs]),
                "majority_share": max(sum(x["cls"] == c for x in xs) for c in ("clean", "crunch")) / len(xs)
                if xs else None}

    both = [x for x in G if x["set"] == "goat" and len(goat_items[x["cluster"]]) == 2]
    out = {"G": sub(G), "G by set": {s: sub([x for x in G if x["set"] == s]) for s in G_SETS},
           "GOAT both-class items": sub(both), "R units": sub(Rr),
           "off-side lender units": sub([x for x in units if x["off_side"]]),
           "on-side lender units": sub([x for x in units if not x["off_side"]])}
    for name, drop in (("with Drowning", False), ("without Drowning", True)):
        xs = [x for x in Rr if not (drop and x["title"] == DROWNING)]
        right, n = clusters_right([(x["cluster"], pred[x["unit"]] == x["cls"]) for x in xs])
        majority = max(len({x["cluster"] for x in xs if x["cls"] == c}) for c in ("clean", "crunch"))
        out[f"R clusters {name}"] = {"right": right, "clusters": n, "majority_clusters": majority,
                                     "acc_units": sum(pred[x["unit"]] == x["cls"] for x in xs) / len(xs)}
    return out, pred, banned


def lender_control(units, feats):
    """Beside: is the lender band readable among clean units (The Travelling Band against Hazael), by C3r's folds,
    from the stems and from the amp track alone? -> {row: {acc, majority_share, units}}."""
    import numpy as np

    xs = [x for x in units if x["cls"] == "clean" and x["lender"] in ("The Travelling Band", "Hazael")]
    out = {}
    for row in ("xlnoG@-3", "xl@-3", "clean-kind"):
        right = 0
        for k in sorted({x["fold"] for x in xs}):
            te = [x for x in xs if x["fold"] == k]
            ban = set().union(*[x["ids"] for x in te])
            tr = [x for x in xs if x["fold"] != k and not (x["ids"] & ban)]
            ps = fit_predict(np.array([feats[row][x["unit"]] for x in tr]), [x["lender"] for x in tr],
                             [feats[row][x["unit"]] for x in te])
            right += sum(p == x["lender"] for x, p in zip(te, ps))
        out[row] = {"units": len(xs), "acc": right / len(xs),
                    "majority_share": max(sum(x["lender"] == b for x in xs) for b in ("The Travelling Band",
                                                                                       "Hazael")) / len(xs)}
    return out


def outcome(rows):
    """(Pure.) The cell from the rows: T-clean's control first (its G interval wholly above G's majority share, or the
    read stops with no cell); then g (T-alone on G), r (T-alone's R clusters, without Drowning), the leak (T-alone
    against T-clean) and In-alone on G."""
    tc, ta, ia = rows["T-clean"], rows["T-alone"], rows["In-alone"]
    lo = tc["G"]["acc_clusters"].get("lo90")
    if lo is None or lo <= tc["G"]["majority_share"]:
        return {"code": None, "control": "failed", "next": "T-clean does not beat the majority share with its whole "
                "interval: the features are broken and the read stops (no cell)"}
    rc = ta[f"R clusters {R_DECIDING}"]
    g = g_reading(ta["G"]["acc_clusters"])
    r = r_reading(rc["right"], rc["clusters"])
    lk = leak_reading({"g_acc": ta["G"]["acc_clusters"]["mean"], "r_acc": ta["R units"]["acc_units"]},
                      {"g_acc": tc["G"]["acc_clusters"]["mean"], "r_acc": tc["R units"]["acc_units"]})
    i = "above" if g_reading(ia["G"]["acc_clusters"]) == "above" else "not"
    code, nxt = ck_cell(g, r, lk, i)
    return {"control": "passed", "g": g, "r": r, "leak": lk, "in_alone": i, "code": code, "next": nxt}


def cmd_read(_args):
    import numpy as np  # noqa: F401  (after the refusals below that need none)

    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    table_guard()
    L.require_phase(PHASE)
    path = class_dir() / "report.json"
    if path.exists():
        raise SystemExit(f"{path} exists; never overwritten")
    t0 = time.time()
    st = R.state()
    units = ladder_units(st)
    goat_items = checks(units)
    feats = {}
    for row in sorted({r for pair in ROWS.values() for r in pair}):
        feats[row] = {}
        for x in units:
            h = L.load_feats(row, x["ru"])
            if h is None:
                raise SystemExit(f"{row}: no stored features for {x['unit']}")
            feats[row][x["unit"]] = unit_features(h)
    rows, banned, preds = {}, {}, {}
    for name, (tr, te) in ROWS.items():
        rows[name], preds[name], banned[name] = row_read(units, feats, tr, te, goat_items)
        print(f"{name} done ({time.time() - t0:.0f} s)", flush=True)
    out = {"plan": PLAN, "ledger": f"{L.LEDGER_ID} {PHASE}", "c3r_sha256": st["sha256"], "rows": rows,
           "fold_bans_removed": banned, "lender_control": lender_control(units, feats),
           "outcome": outcome(rows), "r_deciding": R_DECIDING,
           "units": {"G": EXPECTED["G"], "R": EXPECTED["R"], "excluded": list(EXCLUDED)},
           "predictions": {name: {f"{x['set']}|{x['unit']}": p[x["unit"]] for x in units} for name, p in preds.items()},
           "seconds": round(time.time() - t0, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(path, out)
    print(f"CLASS CHECK: {out['outcome'].get('code')} -> {path}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="learn.class_check")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("read").set_defaults(fn=cmd_read)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
