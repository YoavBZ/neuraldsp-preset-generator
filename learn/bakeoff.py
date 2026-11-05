"""Model comparison, the read without renders (`docs/model-comparison-plan.md`, ledger `model-comparison`).

    $TORCH_PY -m learn.bakeoff control                 # FTm, FT and W, cached, against N1's stored r (CPU)
    $TORCH_PY -m learn.bakeoff read OUT.json           # the declared candidates, read as `reads_v3` reads a model (CPU)

Candidates answer each held real record from what a fold's model may see: the fold's training records (`dfix_rows_of`,
each record once, all its backing variants) and nothing else. Each head fits the label's distance from its (amp, class)
centre, on records where the head was searched, with the regularisation chosen by inner folds on clusters. A held record
is read through variant 0, both halves, as `reads_v3.read_fold` reads it, and goes through `reads_v3`'s own `report`.

Own against swap needs an output shape, so a candidate's knobs are a single Gaussian at its answer, sd the head's training
residual; its switches and mics are flat, which puts their own-against-swap at zero. Nothing is read from plugin rows, NS,
V-real, the panel or captures. Any extra rows come through `extra` and leave by `di`, which holds out more than `di_item`.
"""
from __future__ import annotations

import argparse
import collections
import functools
import hashlib
import json
import math
import pathlib
import pickle
import sys

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

READS_V3_SHA = "a04785f3a4838ae2"
LEDGER_ID = "model-comparison"
OUT = "bakeoff"
BASE = {"FTM": ("P2b-ftm-k{k}", "final"), "FT": ("P2b-ft-k{k}", "final"), "W": ("P2b-wide24", "best")}
ALPHAS = tuple(10.0 ** e for e in range(-2, 6))
INNER = 4
PCS = 24
SD_FLOOR = 0.02
VARIANTS = 25


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def pooled(x):
    """[n, bands, frames] -> [n, 2 * bands]: each band's mean and std over time."""
    return np.concatenate([x.mean(-1), x.std(-1)], axis=1)


def inner_folds(clusters, n=INNER):
    """A fold per row, whole clusters together, stable across runs and machines."""
    def fold(c):
        return int(hashlib.sha256(str(c).encode()).hexdigest(), 16) % n
    return np.array([fold(c) for c in clusters])


def centre_within(v, cells, means=None):
    """v less its cell's mean. -> (centred, {cell: mean}). With `means`, a cell it lacks takes the mean of all of them."""
    v = np.asarray(v, float)
    cells = list(cells)
    if means is None:
        means = {c: v[[i for i, q in enumerate(cells) if q == c]].mean(0) for c in set(cells)}
    fallback = np.mean(list(means.values()), 0)
    return v - np.stack([means.get(c, fallback) for c in cells]), means


def cell_centres(c, mask, cells):
    """{cell: [knobs]}: each head's mean label over a cell's rows where the mask is on, 0.5 where none is."""
    cells = list(cells)
    out = {}
    for q in set(cells):
        i = [j for j, z in enumerate(cells) if z == q]
        n = mask[i].sum(0)
        out[q] = np.where(n > 0, (c[i] * mask[i]).sum(0) / np.maximum(n, 1), 0.5)
    return out


def pca(X, k=PCS):
    """(mean, components) of [n, d]; at most min(n - 1, d, k) components."""
    m = X.mean(0)
    _, _, vt = np.linalg.svd(X - m, full_matrices=False)
    return m, vt[:min(k, max(len(X) - 1, 1), X.shape[1])]


def ridge(X, y, alpha):
    """Weights of a ridge with no intercept: both sides are already centred within cell."""
    X = np.asarray(X, float)
    if X.shape[0] >= X.shape[1]:
        return np.linalg.solve(X.T @ X + alpha * np.eye(X.shape[1]), X.T @ y)
    return X.T @ np.linalg.solve(X @ X.T + alpha * np.eye(X.shape[0]), y)


def choose_alpha(X, y, clusters, alphas=ALPHAS):
    """The alpha with the lowest squared error over inner folds on whole clusters."""
    folds = inner_folds(clusters)
    if len(set(folds)) < 2:
        return alphas[len(alphas) // 2]
    def err(a):
        return sum(((y[folds == f] - X[folds == f] @ ridge(X[folds != f], y[folds != f], a)) ** 2).sum() for f in set(folds))
    return min(alphas, key=err)


def gaussian_output(mu, sd, switches, mics):
    """A candidate's knobs as `reads_v3.loss` reads a model's: [logpi, mu, log sd, switch logits, mic logits], one
    component, switches and mics flat. mu [n, knobs], sd [knobs]."""
    n = len(mu)
    ls = np.broadcast_to(np.log(np.maximum(sd, SD_FLOOR)), mu.shape)
    return [np.zeros((n, 1)), mu[:, None], ls[:, None], np.zeros((n, switches)), np.zeros((n, *mics))]


def family_null(max_by_draw):
    """Selection across candidates: p of each candidate's r against the largest r of any candidate under one label
    permutation. max_by_draw: {group: [largest r per draw]}. -> function (group, r) -> p."""
    return lambda g, r: float((np.array(max_by_draw[g]) >= r).mean())


# --- the data --------------------------------------------------------------------------------------------------------

def unique_rows(rows, recs):
    """Each training record once: `dfix_rows_of` cycles them to a rows-per-epoch count. -> (rows, records)."""
    seen = {}
    for h, r in zip(rows, recs):
        seen.setdefault((h["real"], h["amp"]), (h, r))
    return [q[0] for q in seen.values()], [q[1] for q in seen.values()]


def halves(unit, v):
    """(2, bands, frames) uint8 input of a unit's backing variant v, and its two LUFS."""
    from learn import pipeline_fix as P

    z = np.load(P.dfix_input_path(unit, v))
    a, b = ("mA", "mB") if "mA" in z.files else ("sA", "sB")
    return np.stack([z[a], z[b]]), z["lufs"]


def stats_of(unit, v):
    """(2, 193): each half's band means and stds, normalised as the network's input, without the frames half A masks,
    and the half's LUFS."""
    from learn import pretrain_set as PS
    from learn import song_model as SM

    q, lu = halves(unit, v)
    out = []
    for h in (0, 1):
        x = SM.norm_feat(PS.dequant(q[h]))
        out.append(np.append(pooled((x[:, PS.MASK_A_FRAMES:] if h == 0 else x)[None])[0], float(lu[h])))
    return np.stack(out)


def trunk_of(net, unit, v, amp, cls):
    """(2, 256): W's last hidden layer on a unit's two halves, fed as `RungData.batch` feeds it."""
    import torch

    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_model as SM

    q, lu = halves(unit, v)
    x = SM.norm_feat(np.stack([np.stack([PS.dequant(q[h])] * 2) for h in (0, 1)]))
    c = np.stack([SM.cond_vec(amp, cls, [float(lu[h]), 0.0]) for h in (0, 1)])
    PS.mask_half_a(x, np.array([True, False]))
    DS.zero_inputs(x, c, "Dstem")
    got = []
    hook = net.trunk.register_forward_hook(lambda _m, _i, o: got.append(o))
    try:
        with torch.no_grad():
            net(torch.tensor(x), torch.tensor(c))
    finally:
        hook.remove()
    return got[0].numpy()


_NETS = {}


def net_w(seed):
    from learn import pipeline_fix as P

    if seed not in _NETS:
        _NETS[seed] = P.load_run(BASE["W"][0], seed, BASE["W"][1])[0]
    return _NETS[seed]


@functools.lru_cache(maxsize=None)
def feature(name, seed, unit, v, amp, cls):
    """(2, d) of a declared input; a record's input does not depend on the fold, so each is built once."""
    if name == "mel":
        return stats_of(unit, v).astype(np.float32)
    if name == "ltas":
        return stats_of(unit, v)[:, list(range(96)) + [192]].astype(np.float32)
    if name == "W":
        return trunk_of(net_w(seed), unit, v, amp, cls)
    raise SystemExit(f"{name}: no such input")


# --- the candidates --------------------------------------------------------------------------------------------------

def fit_ridge(X, y, clusters):
    a = choose_alpha(X, y, clusters)
    w = ridge(X, y, a)
    return lambda Z: Z @ w


def fit_trees(X, y, _clusters):
    from sklearn.ensemble import HistGradientBoostingRegressor

    return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=150, l2_regularization=1.0,
                                         random_state=0).fit(X, y).predict


def fit_knn(X, y, clusters):
    """Mean of the k nearest, k by inner folds. Rows of one record's variants sit close, so whole clusters are held."""
    from sklearn.neighbors import KNeighborsRegressor

    folds, best = inner_folds(clusters), (math.inf, 5)
    for k in (5, 15, 45):
        if len(set(folds)) < 2:
            break
        e = sum(((y[folds == f] - KNeighborsRegressor(k).fit(X[folds != f], y[folds != f]).predict(X[folds == f])) ** 2).sum()
                for f in set(folds))
        best = min(best, (e, k))
    return KNeighborsRegressor(best[1]).fit(X, y).predict


FITS = {"ridge": fit_ridge, "trees": fit_trees, "knn": fit_knn}
CANDIDATES = {}                                         # set by the plan's declaration, T2.1: {label: (input, fit)}


def candidate_answers(name, fit, recs_tr, rows_tr, rows_te, Y_tr, searched, seeds=(None,)):
    """A candidate's held answers on one fold, seeds averaged. -> (mu [n, knobs], sd [knobs])."""
    c, cm = Y_tr[0].astype(float), Y_tr[1].astype(float)
    cells_tr = [(h["amp"], h["cls"]) for h in rows_tr]
    cells_te = [(h["amp"], h["cls"]) for h in rows_te]
    mask = cm * np.stack([searched(*q)[0] for q in cells_tr])
    use = np.nonzero(mask.sum(0))[0]
    centre = cell_centres(c, mask, cells_tr)
    fallback = np.mean(list(centre.values()), 0)
    base_te = np.stack([centre.get(q, fallback) for q in cells_te])
    resid = c - np.stack([centre[q] for q in cells_tr])
    sd = np.array([resid[mask[:, j] > 0, j].std() if mask[:, j].sum() > 1 else 0.25 for j in range(c.shape[1])])
    answers = []
    for seed in seeds:
        Xtr = np.stack([[feature(name, seed, h["real"], v, h["amp"], h["cls"]) for v in range(VARIANTS)] for h in rows_tr])   # [n, v, 2, d]
        Xte = np.stack([feature(name, seed, h["real"], 0, h["amp"], h["cls"]) for h in rows_te])                               # [m, 2, d]
        n, v, h_, d = Xtr.shape
        rep = np.repeat(np.arange(n), v * h_)
        flat = Xtr.reshape(-1, d)
        cells = [cells_tr[i] for i in rep]
        cl = [recs_tr[i]["di"] for i in rep]
        flat, means = centre_within(flat, cells)
        m, comp = pca(flat)
        Ztr = (flat - m) @ comp.T
        pred = np.zeros((len(rows_te), c.shape[1]))
        for half in (0, 1):
            Z = (centre_within(Xte[:, half], cells_te, means)[0] - m) @ comp.T
            for j in use:
                rows_j = mask[rep, j] > 0
                if rows_j.sum() >= 2 * VARIANTS:
                    pred[:, j] += 0.5 * FITS[fit](Ztr[rows_j], resid[rep, j][rows_j], [q for q, w in zip(cl, rows_j) if w])(Z)
        answers.append(np.clip(base_te + pred, 0, 1))
    return np.mean(answers, 0), sd


def add_candidates(rows, k, cands, brecs, by_unit, folds, grecs, gunits, extra=()):
    """Each candidate's `_ans` and `_swap` on one fold's `read_fold` rows, in their order. `extra`: more training rows
    as (row, record) pairs, any on a held DI left out."""
    from learn import pipeline_fix as P
    from learn import reads_v3 as R
    from learn import full_space as F
    from learn import trusted_data_t3 as T3

    train, held, _ = P.dfix_rows_of(brecs, by_unit, folds, grecs, gunits, k)
    b, g, bh, gh = P.dfix_records(brecs, by_unit, folds, grecs, gunits, k)
    rows_tr, recs_tr = unique_rows(train, b + g)
    held_dis = {r["di"] for r in bh + gh}
    for row, rec in extra:
        if rec["di"] not in held_dis:
            rows_tr.append(row)
            recs_tr.append(rec)
    assert not held_dis & {r["di"] for r in recs_tr}, "a held DI in the training records"
    enc = T3.encode_for(T3.FULL)
    Y_tr = [np.stack(z) for z in zip(*(enc(h["label"]) for h in rows_tr))]
    Y_te = [np.stack(z) for z in zip(*(enc(h["label"]) for h in held))]
    assert [(h["amp"], h["cls"]) for h in held] == [(q["amp"], q["cls"]) for q in rows]
    c, cm, s, sm, kk, km, _ = Y_te
    for label, (name, fit) in cands.items():
        seeds = R.SEEDS if name == "W" else (None,)
        mu, sd = candidate_answers(name, fit, recs_tr, rows_tr, held, Y_tr, R.searched, seeds)
        o = gaussian_output(mu, sd, len(F.SW), (len(F.CAT), len(F.MICS)))
        for j, row in enumerate(rows):
            sk, ss, sc = R.searched(row["amp"], row["cls"])
            args = (c[j], cm[j] * sk, s[j], sm[j] * ss, kk[j], km[j] * sc)
            others = [i for i, q in enumerate(rows) if i != j and (q["amp"], q["cls"], q["set"]) == (row["amp"], row["cls"], row["set"])
                      and q["cluster"] != row["cluster"]]
            row[f"{label}_ans"] = mu[j]
            row[f"{label}_swap"] = (R.loss(o, j, *args) - np.mean([R.loss(o, i, *args) for i in others], 0)) if others else None
    return rows


# --- the reads -------------------------------------------------------------------------------------------------------

def root():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT


def sha_ok():
    from learn import reads_v3 as R

    if hashlib.sha256(pathlib.Path(R.__file__).read_bytes()).hexdigest()[:16] != READS_V3_SHA:
        raise SystemExit("reads_v3.py is not the file the plan states")


def base_rows():
    """`read_fold`'s rows for FTm, FT and W on all 4 folds, cached: every candidate is read beside them."""
    from learn import pipeline_fix as P
    from learn import reads_v3 as R

    p = root() / "base.rows.pkl"
    brecs, by_unit, folds = P.real_labels(2)
    grecs, gunits, _ = P.goat_labels()
    if p.exists():
        rows = pickle.loads(p.read_bytes())
    else:
        rows = []
        for k in range(4):
            rows += R.read_fold(k, BASE, brecs, by_unit, folds, grecs, gunits)
            print("fold", k, "done", flush=True)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pickle.dumps(rows))
    return rows, (brecs, by_unit, folds, grecs, gunits)


def cmd_control(_args):
    """The cached rows must give N1's stored r and swap total, within 1e-6, on both sets."""
    from learn import pipeline_fix as P
    from learn import reads_v3 as R

    sha_ok()
    rows, _ = base_rows()
    stored = json.loads((P.out_dir() / "night2" / "reads-v3-ftm.json").read_text())
    for st, unit in (("BKS", lambda r: r["fold"]), ("GOAT", lambda r: r["cluster"])):
        S = [r for r in rows if r["set"] == st]
        for label in BASE:
            got = R.corr(R.blocks(S, label))
            for g in R.GROUPS:
                want = stored[f"{st}/{label}"]["r"][g]["r"]
                if abs(got[g][0] - want) > 1e-6:
                    raise SystemExit(f"control: {st} {label} {g} {got[g][0]:+.6f} against stored {want:+.6f}")
            swap = R.t_row([(unit(r), float(r[f"{label}_swap"].sum())) for r in S if r[f"{label}_swap"] is not None])
            want = stored[f"{st}/{label}"]["swap"]["total"]["mean"]
            if abs(swap["mean"] - want) > 1e-6:
                raise SystemExit(f"control: {st} {label} swap {swap['mean']:+.6f} against stored {want:+.6f}")
    print("CONTROL OK", flush=True)


def family(rows, labels, perms=2000):
    """Selection across candidates: under one label permutation per draw, the largest r of any candidate, by set and
    group, and each candidate's p against it."""
    from learn import reads_v3 as R

    out = {}
    for st in ("BKS", "GOAT"):
        S = [r for r in rows if r["set"] == st]
        b = {m: R.blocks(S, m) for m in labels}
        draws = collections.defaultdict(list)
        for d in range(perms):
            top = collections.defaultdict(lambda: -math.inf)
            for m in labels:
                for g, v in R.corr(b[m], np.random.default_rng(R.RNG_SEED + 2 + d)).items():
                    top[g] = max(top[g], v[0])
            for g, v in top.items():
                draws[g].append(v)
        p = family_null(draws)
        base = {m: R.corr(b[m]) for m in labels}
        out[st] = {m: {g: {"r": v[0], "p_family": p(g, v[0])} for g, v in base[m].items()} for m in labels}
    return out


def cmd_read(args):
    from learn import pipeline_fix as P
    from learn import reads_v3 as R

    sha_ok()
    ledger = json.loads((PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    entry = next((t for t in ledger["tests"] if t.get("test_id") == LEDGER_ID), None)
    if entry is None or not CANDIDATES or sorted(entry.get("candidates", ())) != sorted(CANDIDATES):
        raise SystemExit(f"no declared read: ledger {LEDGER_ID!r} must list the candidates in CANDIDATES")
    rows, data = base_rows()
    by_fold = collections.defaultdict(list)
    for r in rows:
        by_fold[r["fold"]].append(r)
    for k in range(4):
        add_candidates(by_fold[k], k, CANDIDATES, *data)
        print("fold", k, "candidates done", flush=True)
    rows = [r for k in range(4) for r in by_fold[k]]
    pickle.dump(rows, open(args.out + ".rows.pkl", "wb"))
    labels = [*BASE, *CANDIDATES]
    res = R.report(rows, labels, pairs=[(c, "FTM") for c in CANDIDATES])
    res["family"] = family(rows, labels)
    json.dump(res, open(args.out, "w"), indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("control").set_defaults(fn=cmd_control)
    r = sub.add_parser("read")
    r.add_argument("out")
    r.set_defaults(fn=cmd_read)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
