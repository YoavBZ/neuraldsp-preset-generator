"""Model comparison, the read without renders (`docs/model-comparison-plan.md`, ledger `model-comparison`).

    $TORCH_PY -m learn.bakeoff control                 # FTm, FT and W, cached, against N1's stored r (CPU)
    $TORCH_PY -m learn.bakeoff check                   # the harness: shuffled labels read near zero, spiked labels read high
    $TORCH_PY -m learn.bakeoff read OUT.json           # the declared candidates, read as `reads_v3` reads a model (CPU)
    $TORCH_PY -m learn.bakeoff arms OUT.json ARM ...   # Phase 4's arms from their stored answers (CPU)

Candidates answer each held real record from what a fold's model may see. A real-trained candidate fits the fold's training
records (`dfix_rows_of`, each record once, all its backing variants). A plugin-trained candidate fits W's stored `train_ids`
and no real row, the same model on every fold; no NS row enters a fit, a choice or a printout. Each head fits the label's
distance from its (amp, class) centre, on records where the head was searched, with the regularisation chosen by inner
folds on clusters. A held record is read through variant 0, both halves, as `reads_v3.read_fold` reads it, and goes through
`reads_v3`'s own `report`.

Own against swap needs an output shape, so a candidate's knobs are a single Gaussian at its answer, sd the head's training
residual; its switches and mics are flat, which puts their own-against-swap at zero, so compare `knob` only. Nothing is read
from V-real, the panel or captures. Any extra rows come through `extra` and leave by `di`, which holds out more than
`di_item`. W's stored body was chosen on NS loss, which `W-ridge` inherits.
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
BASE = {"FTM": ("P2b-ftm-k{k}", "final"), "FT": ("P2b-ft-k{k}", "final"), "W": ("P2b-wide24", "best"),
        "WF": ("P2b-wide24", "final")}
READERS = ("M-ridge", "M-rrr", "M-knn", "M-trees", "W-ridge")
TONE_INPUTS = ("ltas", "ceps-lo")
DRIVE_INPUTS = ("onset", "flat", "hpss", "ceps-hi")
CANDIDATES = {"M-ridge": ("mel", "ridge", "real"), "M-rrr": ("mel", "rrr", "real"), "M-knn": ("mel", "knn", "real"),
              "M-trees": ("mel", "trees", "real"), "W-ridge": ("W", "ridge", "real"),
              **{n: (n, "ridge", "real") for n in (*TONE_INPUTS, *DRIVE_INPUTS)},
              "P-ridge": ("mel", "ridge", "plugin"), **{f"P-{n}": (n, "ridge", "plugin") for n in DRIVE_INPUTS}}
PAIRS = (*((c, "FTM") for c in READERS), *((c, "M-ridge") for c in (*TONE_INPUTS, *DRIVE_INPUTS)), ("P-ridge", "W"),
         *((f"P-{c}", "P-ridge") for c in DRIVE_INPUTS), ("WF", "W"))
BOUND = (*((c, "FTM", g, False) for c in READERS for g in ("drive", "tone", "cab")),            # (a, b, group, crunch only)
         *((c, "M-ridge", g, False) for c in TONE_INPUTS for g in ("tone", "cab")),
         *((c, "M-ridge", "drive", True) for c in DRIVE_INPUTS),
         *((f"P-{c}", "P-ridge", "drive", True) for c in DRIVE_INPUTS),
         *(("P-ridge", "W", g, False) for g in ("drive", "tone", "cab")))
ALPHAS = tuple(10.0 ** e for e in range(-2, 6))
INNER = 4
PCS = 24
RANK = 4
SD_FLOOR = 0.02
SPIKE = 30.0
VARIANTS = 25                                           # a real unit's inputs
BOUND_SEED = 20261042                                   # both W seeds train on the same plugin ids
PLUGIN_VARIANTS = 5                                     # a plugin row's own input and its first 4 backings


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


def residual_sd(c, cm, rows, searched):
    """Each head's sd about its (amp, class) centre on training rows where it was searched, 0.25 where too few."""
    c, cm = np.asarray(c, float), np.asarray(cm, float)
    cells = [(h["amp"], h["cls"]) for h in rows]
    mask = cm * np.stack([searched(*q)[0] for q in cells])
    centre = cell_centres(c, mask, cells)
    resid = (c - np.stack([centre[q] for q in cells])) * mask
    return np.array([resid[mask[:, j] > 0, j].std() if mask[:, j].sum() > 1 else 0.25 for j in range(c.shape[1])])


def rrr_fit(Z, Y, clusters, rank=RANK):
    """Reduced rank: Y [n, heads], with unsearched cells 0, onto its top `rank` directions, a ridge per direction, alpha by
    inner folds. -> predict(Z) -> [m, heads]."""
    _, _, vt = np.linalg.svd(Y, full_matrices=False)
    comp = vt[:min(rank, len(vt))]
    scores = Y @ comp.T
    w = np.stack([ridge(Z, scores[:, j], choose_alpha(Z, scores[:, j], clusters)) for j in range(len(comp))], 1)
    return lambda Q: Q @ w @ comp


def gaussian_output(mu, sd, switches, mics):
    """A candidate's knobs as `reads_v3.loss` reads a model's: [logpi, mu, log sd, switch logits, mic logits], one
    component, switches and mics flat. mu [n, knobs], sd [knobs]."""
    n = len(mu)
    ls = np.broadcast_to(np.log(np.maximum(sd, SD_FLOOR)), mu.shape)
    return [np.zeros((n, 1)), mu[:, None], ls[:, None], np.zeros((n, switches)), np.zeros((n, *mics))]


def max_t_lower(draws, whole, tail=0.95):
    """Simultaneous lower bounds on contrasts from bootstrap draws [n, contrasts] on one set of weights: each contrast's
    estimate less q standard errors, q the `tail` quantile of the largest standardised deviation over the contrasts.
    -> (lower bounds, q)."""
    draws, whole = np.asarray(draws, float), np.asarray(whole, float)
    se = draws.std(0, ddof=1)
    q = float(np.quantile(((draws - whole) / np.maximum(se, 1e-12)).max(1), tail))
    return whole - q * se, q


def family_null(max_by_draw):
    """Selection across candidates: p of each candidate's r against the largest r of any candidate under one label
    permutation. max_by_draw: {group: [largest r per draw]}. -> function (group, r) -> p."""
    return lambda g, r: float((np.array(max_by_draw[g]) >= r).mean())


# --- the data --------------------------------------------------------------------------------------------------------

def code_key():
    """A hash of the code that makes a candidate's answers: a cached answer from other code is not reused."""
    h = hashlib.sha256()
    for name in ("bakeoff.py", "bakeoff_inputs.py"):
        h.update((PLUGIN_ROOT / "learn" / name).read_bytes())
    return h.hexdigest()[:16]


def save_answers(path, **arrays):
    """An answers file written whole: to a temporary name, then moved."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.npz")
    np.savez(tmp, **arrays)
    tmp.replace(path)


def unique_rows(rows, recs):
    """Each training record once: `dfix_rows_of` cycles them to a rows-per-epoch count. -> (rows, records)."""
    seen = {}
    for h, r in zip(rows, recs):
        seen.setdefault((h["real"], h["amp"]), (h, r))
    return [q[0] for q in seen.values()], [q[1] for q in seen.values()]


def halves(path):
    """(2, bands, frames) uint8 input of a stored file, and its two LUFS."""
    z = np.load(path)
    a, b = ("mA", "mB") if "mA" in z.files else ("sA", "sB")
    return np.stack([z[a], z[b]]), z["lufs"]


@functools.lru_cache(maxsize=1)
def centres():
    from learn import direct_stems as DS

    return DS.mel_centres_hz()


def summary_of(name, path):
    """(2, d + 1): a declared input on each half, normalised as the network's input, without the frames half A masks, and
    the half's LUFS scaled as `cond_vec` scales it."""
    from learn import bakeoff_inputs as BI
    from learn import pretrain_set as PS
    from learn import song_model as SM

    q, lu = halves(path)
    out = []
    for h in (0, 1):
        x = SM.norm_feat(PS.dequant(q[h]))
        v = BI.INPUTS[name](x[:, PS.MASK_A_FRAMES:] if h == 0 else x, centres())
        out.append(np.append(v, (float(lu[h]) + 20.0) / 10.0))
    return np.stack(out).astype(np.float32)


def trunk_of(net, path, amp, cls):
    """(2, 256): W's last hidden layer on a file's two halves, fed as `RungData.batch` feeds it."""
    import torch

    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_model as SM

    q, lu = halves(path)
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
def feature(name, seed, path, amp, cls):
    """(2, d) of a declared input; a file's input does not depend on the fold, so each is built once. W's features depend
    on (seed, file, amp, class) and on no fold: W holds no real row."""
    if name == "W":
        return trunk_of(net_w(seed), path, amp, cls)
    return summary_of(name, path)


@functools.lru_cache(maxsize=1)
def plugin_set():
    """W's training rows and each row's input files: its own and its first backings. Refuses unless the ids are W's."""
    import argparse as AP

    from learn import pipeline_fix as P

    e = P.require("phase_3")
    croot, kept, rend, sp, dropped = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    wrec = json.loads((P.out_dir() / "runs" / f"{BASE['W'][0]}-{BOUND_SEED}.json").read_text())
    ids = [i for i in wrec["train_ids"] if i < P.REAL_ROW0]
    pa = AP.Namespace(rung="b", fold=None, frac=1.0, sections=1.0, pc=False, pcsz=False, aug=False)
    tr, *_ = P.plugin_rows(kept, sp, pa, lambda q: [])
    if tr != ids:
        raise SystemExit("the plugin training ids differ from W's")
    rows = P.rung_rows(kept, rend, ids)
    doubled = P.doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
    own = P.rung_path(croot, "b", doubled)
    files = [[str(own(r["i"])), *(str(P.wide_path(r["i"], v)) for v in range(PLUGIN_VARIANTS - 1))] for r in rows]
    return rows, files


def training_set(src, k, data):
    """(rows, clusters, each row's files) a candidate fits on fold k. Real: the fold's training records once each, no held
    DI. Plugin: W's rows, clusters by section."""
    from learn import pipeline_fix as P

    if src == "plugin":
        rows, files = plugin_set()
        return rows, [r["section"] for r in rows], files
    train, _, _ = P.dfix_rows_of(*data, k)
    b, g, bh, gh = P.dfix_records(*data, k)
    rows, recs = unique_rows(train, b + g)
    if {r["di"] for r in bh + gh} & {r["di"] for r in recs}:
        raise SystemExit(f"fold {k}: a held DI in the training records")
    return rows, [r["di"] for r in recs], [[str(P.dfix_input_path(h["real"], v)) for v in range(VARIANTS)] for h in rows]


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


def shuffled_within(c, cm, cells, seed):
    """Labels and their masks moved between a cell's rows: the placebo. -> (c, cm)."""
    rng, order = np.random.default_rng(seed), np.arange(len(c))
    cells = list(cells)
    for q in set(cells):
        i = np.array([j for j, z in enumerate(cells) if z == q])
        order[i] = rng.permutation(i)
    return c[order], cm[order]


def candidate_answers(spec, rows_tr, clusters, files, rows_te, files_te, Y_tr, searched, seeds, spike=None):
    """A candidate's held answers on one fold, seeds averaged. `spike` (train labels, held labels) joins the labels to the
    input, the harness's positive control. -> (mu [n, knobs], sd [knobs])."""
    name, fit, _ = spec
    c, cm = Y_tr[0].astype(float), Y_tr[1].astype(float)
    cells_tr = [(h["amp"], h["cls"]) for h in rows_tr]
    cells_te = [(h["amp"], h["cls"]) for h in rows_te]
    mask = cm * np.stack([searched(*q)[0] for q in cells_tr])
    use = np.nonzero(mask.sum(0))[0]
    centre = cell_centres(c, mask, cells_tr)
    fallback = np.mean(list(centre.values()), 0)
    base_te = np.stack([centre.get(q, fallback) for q in cells_te])
    resid = (c - np.stack([centre[q] for q in cells_tr])) * mask
    sd = residual_sd(c, cm, rows_tr, searched)
    answers = []
    for seed in seeds:
        Xtr = np.stack([[feature(name, seed, f, h["amp"], h["cls"]) for f in fs] for h, fs in zip(rows_tr, files)])  # [n, v, 2, d]
        Xte = np.stack([feature(name, seed, f, h["amp"], h["cls"]) for h, f in zip(rows_te, files_te)])              # [m, 2, d]
        if spike is not None:
            Xtr = np.concatenate([Xtr, np.broadcast_to(SPIKE * spike[0][:, None, None], (*Xtr.shape[:3], spike[0].shape[1]))], -1)
            Xte = np.concatenate([Xte, np.broadcast_to(SPIKE * spike[1][:, None], (*Xte.shape[:2], spike[1].shape[1]))], -1)
        n, v, h_, d = Xtr.shape
        rep = np.repeat(np.arange(n), v * h_)
        flat = Xtr.reshape(-1, d)
        cells = [cells_tr[i] for i in rep]
        cl = [clusters[i] for i in rep]
        flat, means = centre_within(flat, cells)
        m, comp = pca(flat)
        Ztr = (flat - m) @ comp.T
        pred = np.zeros((len(rows_te), c.shape[1]))
        for half in (0, 1):
            Z = (centre_within(Xte[:, half], cells_te, means)[0] - m) @ comp.T
            if fit == "rrr":
                for amp in sorted({q[0] for q in cells_te}):
                    tr_i = np.array([q[0] == amp for q in cells_tr])[rep]
                    te_i = np.array([q[0] == amp for q in cells_te])
                    heads = np.nonzero(mask[np.array([q[0] == amp for q in cells_tr])].sum(0))[0]
                    keep = [q for q, w in zip(cl, tr_i) if w]
                    pred[np.ix_(te_i, heads)] += 0.5 * rrr_fit(Ztr[tr_i], resid[rep][tr_i][:, heads], keep)(Z[te_i])
                continue
            for j in use:
                rows_j = mask[rep, j] > 0
                if rows_j.sum() >= 2 * v:
                    pred[:, j] += 0.5 * FITS[fit](Ztr[rows_j], resid[rep, j][rows_j], [q for q, w in zip(cl, rows_j) if w])(Z)
        answers.append(np.clip(base_te + pred, 0, 1))
    return np.mean(answers, 0), sd


def add_candidates(rows, k, cands, data, extra=(), check=None):
    """Each candidate's `_ans` and `_swap` on one fold's `read_fold` rows, in their order, cached per fold unless `check`.
    `extra`: more real training rows as (row, record) pairs, any on a held DI left out. `check`: "shuffle" or "spike", the
    harness's own controls."""
    from learn import full_space as F
    from learn import pipeline_fix as P
    from learn import reads_v3 as R
    from learn import trusted_data_t3 as T3

    _, held, _ = P.dfix_rows_of(*data, k)
    assert [(h["amp"], h["cls"]) for h in held] == [(q["amp"], q["cls"]) for q in rows]
    enc = T3.encode_for(T3.FULL)
    Y_te = [np.stack(z) for z in zip(*(enc(h["label"]) for h in held))]
    c, cm, s, sm, kk, km, _ = Y_te
    files_te = [str(P.dfix_input_path(h["real"], 0)) for h in held]
    held_dis = {q["cluster"] for q in rows}
    for label, spec in cands.items():
        store = root() / "answers" / f"{label}-k{k}.npz"
        stored = None
        if spec[0] == "arm":
            stored = np.load(store)
        elif check is None and store.exists():
            z = np.load(store)
            stored = z if str(z["key"]) == code_key() else None
        if stored is not None:
            mu, sd = stored["mu"], stored["sd"]
        else:
            rows_tr, clusters, files = training_set(spec[2], k, data)
            if spec[2] == "real":
                keep = [(row, rec) for row, rec in extra if rec["di"] not in held_dis]
                rows_tr = rows_tr + [q[0] for q in keep]
                clusters = clusters + [q[1]["di"] for q in keep]
                files = files + [[str(P.dfix_input_path(q[0]["real"], v)) for v in range(VARIANTS)] for q in keep]
            Y_tr = [np.stack(z) for z in zip(*(enc(h["label"]) for h in rows_tr))]
            spike = (Y_tr[0], Y_te[0]) if check == "spike" else None
            if check == "shuffle":
                Y_tr[0], Y_tr[1] = shuffled_within(Y_tr[0], Y_tr[1], [(h["amp"], h["cls"]) for h in rows_tr], R.RNG_SEED + k)
            seeds = R.SEEDS if spec[0] == "W" else (None,)
            mu, sd = candidate_answers(spec, rows_tr, clusters, files, held, files_te, Y_tr, R.searched, seeds, spike)
            if check is None:
                save_answers(store, mu=mu, sd=sd, key=code_key())
        o = gaussian_output(mu, sd, len(F.SW), (len(F.CAT), len(F.MICS)))
        for j, row in enumerate(rows):
            row[f"{label}_ans"] = mu[j]
        if stored is not None and "swap" in stored.files:              # an arm's own switch and mic output
            for j, row in enumerate(rows):
                row[f"{label}_swap"] = None if np.isnan(stored["swap"][j]).any() else stored["swap"][j]
            continue
        for j, row in enumerate(rows):
            sk, ss, sc = R.searched(row["amp"], row["cls"])
            args = (c[j], cm[j] * sk, s[j], sm[j] * ss, kk[j], km[j] * sc)
            others = [i for i, q in enumerate(rows) if i != j and (q["amp"], q["cls"], q["set"]) == (row["amp"], row["cls"], row["set"])
                      and q["cluster"] != row["cluster"]]
            row[f"{label}_swap"] = (R.loss(o, j, *args) - np.mean([R.loss(o, i, *args) for i in others], 0)) if others else None
        print(k, label, "done", flush=True)
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
        for label in ("FTM", "FT", "W"):
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


def cmd_check(_args):
    """The harness's controls, reading no candidate: every candidate with labels shuffled within cell in training must read
    near zero, or it leaks; labels joined to the input must read high, or rows and labels are misaligned."""
    from learn import reads_v3 as R

    sha_ok()
    rows, data = base_rows()
    res = {}
    for check, cands in (("spike", {k: CANDIDATES[k] for k in ("M-ridge", "W-ridge", "P-ridge")}), ("shuffle", CANDIDATES)):
        by_fold = collections.defaultdict(list)
        for r in rows:
            by_fold[r["fold"]].append(dict(r))
        for k in range(4):
            add_candidates(by_fold[k], k, cands, data, check=check)
        done = [r for k in range(4) for r in by_fold[k]]
        res[check] = {c: {st: {g: R.corr(R.blocks([r for r in done if r["set"] == st], c)).get(g, (None,))[0] for g in R.GROUPS}
                          for st in ("BKS", "GOAT")} for c in cands}
        print(check, json.dumps(res[check]), flush=True)
    (root() / "check.json").write_text(json.dumps(res, indent=1))


def family(rows, labels, perms=2000):
    """How large a read one candidate of this family reaches by chance: under one label permutation per draw, the largest r
    of any label, by set and group, and each label's p against it."""
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


def standardised(S, g, label):
    """x and y of group g's flat points, each within-cell-demeaned value's scale set by its (amp, head) sd, and the flat
    index, as `reads_v3.corr`'s r_std pools them."""
    from learn import reads_v3 as R

    I, J, C, n = R.flat(S, g)
    y = np.array([S[i]["c"][j] for i, j in zip(I, J)], float)
    x = np.array([S[i][f"{label}_ans"][j] for i, j in zip(I, J)], float)
    keys = [(S[i]["amp"], j) for i, j in zip(I, J)]
    for key in set(keys):
        q = np.array([z == key for z in keys])
        cells = C[q]
        for arr in (x, y):
            d = arr[q] - (np.bincount(cells, arr[q], n) / np.maximum(np.bincount(cells, minlength=n), 1))[cells]
            arr[q] = arr[q] / max(d.std(), 1e-12)
    return I, x, y, C, n


def contrast_draws(S, a, b, g, W, of, standard):
    """One paired contrast of r on GOAT rows S: (whole, draws) on the shared item weights W."""
    from learn import reads_v3 as R

    if standard:
        I, xa, y, C, n = standardised(S, g, a)
        _, xb, _, _, _ = standardised(S, g, b)
    else:
        I, J, C, n = R.flat(S, g)
        y = np.array([S[i]["c"][j] for i, j in zip(I, J)], float)
        xa = np.array([S[i][f"{a}_ans"][j] for i, j in zip(I, J)], float)
        xb = np.array([S[i][f"{b}_ans"][j] for i, j in zip(I, J)], float)
    pt = of[I]
    whole = R.wr(xa, y, np.ones(len(y)), C, n) - R.wr(xb, y, np.ones(len(y)), C, n)
    return whole, np.array([R.wr(xa, y, w[pt].astype(float), C, n) - R.wr(xb, y, w[pt].astype(float), C, n) for w in W])


def bounds(rows, family_=BOUND):
    """Every contrast that can move a candidate on, with its plain 90% interval and a simultaneous 95% lower bound over all
    of them, on one set of GOAT item weights. Drive on crunch pairs head-standardised: inputGain alone carries 56% of its
    label variance."""
    from learn import reads_v3 as R

    G = [r for r in rows if r["set"] == "GOAT"]
    items = {u: i for i, u in enumerate(sorted({r["cluster"] for r in G}))}
    W = np.random.default_rng(R.RNG_SEED + 1).multinomial(len(items), np.ones(len(items)) / len(items), size=R.BOOT_DRAWS)
    out, draws, whole = [], [], []
    for a, b, g, crunch in family_:
        S = [r for r in G if r["cls"] == "crunch"] if crunch else G
        of = np.array([items[r["cluster"]] for r in S])
        d, q = contrast_draws(S, a, b, g, W, of, crunch)
        whole.append(d)
        draws.append(q)
        out.append({"a": a, "b": b, "group": g, "crunch": crunch, "diff": float(d), "lo90": float(np.percentile(q, 5)),
                    "hi90": float(np.percentile(q, 95))})
    low, q = max_t_lower(np.stack(draws, 1), np.array(whole))
    for row, x in zip(out, low):
        row["simultaneous_lower"] = float(x)
    return {"q": q, "contrasts": out}


def crunch_read(rows, labels):
    """Drive on GOAT's crunch rows alone, the review's step 3: raw and head-standardised, beside the row count."""
    from learn import reads_v3 as R

    S = [r for r in rows if r["set"] == "GOAT" and r["cls"] == "crunch"]
    iv = R.goat_intervals(S, labels, ())
    out = {"rows": len(S), "items": len({r["cluster"] for r in S})}
    for m in labels:
        v = R.corr(R.blocks(S, m))["drive"]
        out[m] = {"r": v[0], "r_std": v[3], "n": v[1], "boot90": iv[(m, "drive")]}
    return out


def player_read(rows, labels, gunits):
    """GOAT is about 76% one player: each label's r on that player's items and on the rest."""
    from learn import reads_v3 as R

    player = {u["unit"].split("@")[0]: u["band"] for u in gunits.values()}
    G = [r for r in rows if r["set"] == "GOAT"]
    top = collections.Counter(player[r["cluster"]] for r in G).most_common(1)[0][0]
    out = {"main_share": sum(player[r["cluster"]] == top for r in G) / len(G)}
    for name, S in (("main", [r for r in G if player[r["cluster"]] == top]), ("rest", [r for r in G if player[r["cluster"]] != top])):
        out[name] = {m: {g: v[0] for g, v in R.corr(R.blocks(S, m)).items()} for m in labels}
    return out


def swap_pairs(rows, arms):
    """Each arm's switch and mic own-against-swap less FTm's on GOAT, by item, 90% t. An interval wholly above zero says the
    arm's switches or mics lost reading. Knobs are left out: an arm's knob output can have another form."""
    from learn import reads_v3 as R

    G = [r for r in rows if r["set"] == "GOAT" and r["FTM_swap"] is not None]
    out = {}
    for a in arms:
        P_ = [r for r in G if r[f"{a}_swap"] is not None]
        out[a] = {q: R.t_row([(r["cluster"], float(r[f"{a}_swap"][i] - r["FTM_swap"][i])) for r in P_]) for i, q in ((1, "switch"), (2, "mic"))}
    return out


def cmd_arms(args):
    """Phase 4's arms, read from their stored answers beside FTm: `reads_v3`'s report, and the max-t bound over each arm's
    groups against FTm."""
    from learn import reads_v3 as R

    sha_ok()
    arms = {a: ("arm", "arm", "real") for a in args.arms}
    rows, data = base_rows()
    by_fold = collections.defaultdict(list)
    for r in rows:
        by_fold[r["fold"]].append(r)
    for k in range(4):
        add_candidates(by_fold[k], k, arms, data)
    rows = [r for k in range(4) for r in by_fold[k]]
    pathlib.Path(args.out + ".rows.pkl").write_bytes(pickle.dumps(rows))
    labels = [*BASE, *arms]
    res = R.report(rows, labels, pairs=[(a, "FTM") for a in arms])
    res["bounds"] = bounds(rows, tuple((a, "FTM", g, False) for a in arms for g in ("drive", "tone", "cab")))
    res["swap_pairs"] = swap_pairs(rows, arms)
    res["player"] = player_read(rows, labels, data[4])
    pathlib.Path(args.out).write_text(json.dumps(res, indent=1, default=float))


def cmd_read(args):
    from learn import reads_v3 as R

    sha_ok()
    ledger = json.loads((PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    entry = next((t for t in ledger["tests"] if t.get("test_id") == LEDGER_ID), None)
    if entry is None or sorted(entry.get("candidates", ())) != sorted(CANDIDATES):
        raise SystemExit(f"no declared read: ledger {LEDGER_ID!r} must list the candidates in CANDIDATES")
    rows, data = base_rows()
    by_fold = collections.defaultdict(list)
    for r in rows:
        by_fold[r["fold"]].append(r)
    for k in range(4):
        add_candidates(by_fold[k], k, CANDIDATES, data)
    rows = [r for k in range(4) for r in by_fold[k]]
    pathlib.Path(args.out + ".rows.pkl").write_bytes(pickle.dumps(rows))
    labels = [*BASE, *CANDIDATES]
    res = R.report(rows, labels, pairs=list(PAIRS))
    res["crunch"] = crunch_read(rows, labels)
    res["bounds"] = bounds(rows)
    res["player"] = player_read(rows, labels, data[4])
    res["family"] = family(rows, labels)
    pathlib.Path(args.out).write_text(json.dumps(res, indent=1, default=float))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("control").set_defaults(fn=cmd_control)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    r = sub.add_parser("read")
    r.add_argument("out")
    r.set_defaults(fn=cmd_read)
    r = sub.add_parser("arms")
    r.add_argument("out")
    r.add_argument("arms", nargs="+")
    r.set_defaults(fn=cmd_arms)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
