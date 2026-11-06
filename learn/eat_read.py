"""EfficientAT's frozen reads (`docs/efficientat-plan.md`, tasks S2 to S4). CPU, zero renders.

    $TORCH_PY -m learn.eat_read plugin OUT.json [--net mn10_as] [--reps top f6] [--pcs 24]   # S2 and S3, plugin rows only
    $TORCH_PY -m learn.eat_read check --mid f6 [--pcs 24]                         # S4.1's controls
    $TORCH_PY -m learn.eat_read amp OUT.json --mid f6 [--pcs 24]                  # S3.5, amp tracks alone, zero-shot
    $TORCH_PY -m learn.eat_read real OUT.json --mid f6 [--pcs 24]                 # S4.2, once the ledger declares it
    $TORCH_PY -m learn.eat_read tags OUT.json                                     # S4.4, AudioSet's outputs with no fit
    $TORCH_PY -m learn.eat_read domain OUT.json --reps top f6 mel                 # S3.4, the domain direction, no real label

Every read goes through `bakeoff.candidate_answers` unchanged: within-cell centring, 24 PCs in the fold, ridge with alpha from inner
folds, residuals around the cell's mean, searched heads only, the two halves averaged. Only `feature` and the PC count are swapped,
and `plugin_set` loses each row's own backing, which has no rebuilt audio. Each dimension is scaled by its sd on the `wide` set, no
labels, so a network's arbitrary channel scales do not choose the PCs. LUFS joins as `summary_of` joins it.

Plugin reads fold on whole DIs, and S3's held rows read only backings of pool sessions held in that fold, which training leaves out.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import pathlib
import pickle
import sys

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import bakeoff as B  # noqa: E402
from learn import eat_build as EB  # noqa: E402
from learn import eat_embed as EE  # noqa: E402

LEDGER_ID = "efficientat"
OUT = "eat/reads"
FOLDS = 4
REPS = ("top", *(f"g{q}" for q in EE.G_LAYERS[:-1]), *(f"f{q}" for q in EE.F_LAYERS), "multi", "logits", "mel")
MULTI = tuple(f"f{q}" for q in EE.F_LAYERS)
TRAIN_VARIANTS = 3
MEL_SD_ROWS = 300
MEL_PCS = 24
GROUP_NAMES = ("drive", "tone", "cab")
R_DIMS_TOP = 1921                                       # `top` with LUFS, at width 1
TAG_CLASSES = ("Distortion", "Effects unit", "Electric guitar", "Reverberation", "Echo")
DRAWS = 1000


def stat_of(rep):
    return "g16" if rep == "top" else rep


def scaled(v, sd):
    return v / np.maximum(sd, 1e-6)


class Bank:
    """A network's stored statistics. `vector(rep, key)` -> (2, d + 1), scaled, with the half's LUFS."""

    def __init__(self, net):
        self.net, self.arrays, self.index, self.sds = net, {}, {}, {}

    def array(self, kind, stat):
        q = (kind, stat)
        if q not in self.arrays:
            self.arrays[q] = np.load(EE.embed_root() / self.net / kind / f"{stat}.npy", mmap_mode="r")
        return self.arrays[q]

    def row(self, kind, key):
        if kind not in self.index:
            keys = json.loads((EE.embed_root() / self.net / kind / "keys.json").read_text())
            self.index[kind] = {tuple(k): j for j, k in enumerate(keys)}
        return self.index[kind][key]

    def sd(self, stat):
        if stat not in self.sds:
            a = np.asarray(self.array("wide", stat), np.float32)
            self.sds[stat] = a.reshape(-1, a.shape[-1]).std(0)
        return self.sds[stat]

    def stat(self, kind, key, stat):
        return scaled(np.asarray(self.array(kind, stat)[self.row(kind, key)], np.float32), self.sd(stat))

    def vector(self, rep, kind, key, lufs):
        if rep == "multi":
            v = np.concatenate([self.stat(kind, key, s) / np.sqrt(self.sd(s).size) for s in MULTI], 1)
        else:
            v = self.stat(kind, key, stat_of(rep))
        return np.concatenate([v, (np.asarray(lufs, np.float32)[:, None] + 20.0) / 10.0], 1)


def rebuilt_lufs(kind, key):
    path = {"clean": lambda: EB.clean_path(key[0]), "wide": lambda: EB.wide_path(*key), "real": lambda: EB.real_path(*key),
            "amp": lambda: EB.amp_path(key[0])}[kind]()
    return np.load(path)["lufs"]


def input_of(kind, key):
    """The stored 96-band file of an input: the mel reference reads the same audio as the network."""
    from learn import pipeline_fix as P

    if kind == "clean":
        return str(P.input_path(P.DATA, key[0], P.RUNG_KINDS["a"]))
    if kind == "wide":
        return str(P.wide_path(*key))
    if kind == "amp":
        path = P.real_input_path(key[0])
        return str(path if path.exists() else P.goat_input_path(key[0]))
    return str(P.dfix_input_path(*key))


class Features:
    """`bakeoff.feature`'s replacement, keyed on (kind, key) tuples or on the stored file's path."""

    def __init__(self, bank, paths=None):
        self.bank, self.paths = bank, paths or {}
        self.cache, self.mel_scale = {}, None

    def mel_sd(self):
        """The mel statistics' sd by dimension on the `wide` set's first rows, no labels."""
        if self.mel_scale is None:
            rows, _ = B.plugin_set()
            a = np.stack([B.summary_of("mel", input_of("wide", (r["i"], 0)))[:, :-1] for r in rows[:MEL_SD_ROWS]])
            self.mel_scale = a.reshape(-1, a.shape[-1]).std(0)
        return self.mel_scale

    def __call__(self, name, _seed, f, _amp, _cls):
        kind, key = self.paths[f] if isinstance(f, str) else f
        q = (name, kind, key)
        if q in self.cache:
            return self.cache[q]
        if name == "mel":
            v = B.summary_of("mel", input_of(kind, key))
        elif name.startswith("mix:"):
            m = scaled(B.summary_of("mel", input_of(kind, key))[:, :-1], self.mel_sd())
            e = self.bank.vector(name[4:], kind, key, rebuilt_lufs(kind, key))
            block = np.sqrt(len(MULTI) if name[4:] == "multi" else e.shape[1] - 1)     # `multi`'s blocks are already scaled
            v = np.concatenate([e[:, :-1] / block, m / np.sqrt(m.shape[1]), e[:, -1:]], 1)
        else:
            v = self.bank.vector(name, kind, key, rebuilt_lufs(kind, key))
        self.cache[q] = v.astype(np.float32)
        return self.cache[q]


def group_read(S, labels, pairs):
    """r by group with section-bootstrap intervals, through `reads_v3`'s own pooling."""
    from learn import reads_v3 as R

    iv = R.goat_intervals(S, labels, pairs, draws=DRAWS)
    out = {m: {g: {"r": v[0], "n": v[1], "r_std": v[3], "lo90": iv[(m, g)][0], "hi90": iv[(m, g)][1]}
               for g, v in R.corr(R.blocks(S, m)).items()} for m in labels}
    out["pairs"] = {f"{a}-{b}": {g: iv[(f"{a}-{b}", g)] for g in R.GROUPS} for a, b in pairs}
    return out


def plugin_split():
    """(rows, DI fold per row, {(i, backing): the backing's pool session}, {session: its fold}, each row's DI)."""
    from learn import pipeline_fix as P

    rows, _ = B.plugin_set()
    e = P.require("phase_3")
    _, kept, _, sp, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    dis = [kept[r["i"]]["di"] for r in rows]
    folds = B.inner_folds(dis, FOLDS)
    pool = json.loads(P.wide_pool_path().read_text())["entries"]
    draws = P.wide_draws(sp["train"], kept, pool)
    sess = {(r["i"], k): pool[draws[r["i"]][k][0]]["session"] for r in rows for k in range(EB.WIDE_K)}
    names = sorted({e_["session"] for e_ in pool})
    return rows, folds, sess, dict(zip(names, B.inner_folds(names, FOLDS).tolist())), dis


def backed_files(rows, folds, sess, sfold, k):
    """S3's fold k. -> (training rows' indices and files, held rows' indices and files). A held row reads its first backing of
    a held session; a training row's files are its backings of other sessions, cycled to TRAIN_VARIANTS."""
    tr, trf, te, tef = [], [], [], []
    for j, r in enumerate(rows):
        held = [v for v in range(EB.WIDE_K) if sfold[sess[(r["i"], v)]] == k]
        rest = [v for v in range(EB.WIDE_K) if sfold[sess[(r["i"], v)]] != k]
        if folds[j] == k and held:
            te.append(j)
            tef.append(("wide", (r["i"], held[0])))
        elif folds[j] != k and rest:
            tr.append(j)
            trf.append([("wide", (r["i"], rest[q % len(rest)])) for q in range(TRAIN_VARIANTS)])
    return tr, trf, te, tef


def clean_files(rows, folds, k):
    tr = [j for j in range(len(rows)) if folds[j] != k]
    te = [j for j in range(len(rows)) if folds[j] == k]
    return tr, [[("clean", (rows[j]["i"], -1))] for j in tr], te, [("clean", (rows[j]["i"], -1)) for j in te]


def spiked_size(dims):
    """A spike that outweighs the top PCs of `dims` unit-scaled dimensions."""
    return 10.0 * np.sqrt(dims)


def with_pcs(pcs):
    """`B.pca` at `pcs` components."""
    keep = B.pca
    B.pca = lambda X, k=pcs: keep(X, k)
    return keep


def plugin_answers(rep, split, kind, pcs, check=None):
    """One representation's held answers on W's rows, by fold, alpha and intervals on whole DIs. kind "clean" or "backed". -> rows
    for `reads_v3`. check "shuffle" or "spike": the controls, the spike sized to the representation's total variance."""
    from learn import reads_v3 as R
    from learn import trusted_data_t3 as T3

    rows, folds, sess, sfold, dis = split
    enc = T3.encode_for(T3.FULL)
    Y = [np.stack(z) for z in zip(*(enc(h["label"]) for h in rows))]
    out = []
    keep, spike_size = with_pcs(pcs), B.SPIKE
    if check == "spike":
        B.SPIKE = spiked_size(B.feature(rep, None, ("clean", (rows[0]["i"], -1)), None, None).shape[1])
    for k in range(FOLDS):
        tr, files, te, files_te = clean_files(rows, folds, k) if kind == "clean" else backed_files(rows, folds, sess, sfold, k)
        rows_tr, rows_te = [rows[i] for i in tr], [rows[i] for i in te]
        clusters = [dis[i] for i in tr]
        Ytr = [Y[0][tr], Y[1][tr]]
        spike = (Y[0][tr], Y[0][te]) if check == "spike" else None
        if check == "shuffle":
            Ytr = list(B.shuffled_within(Ytr[0], Ytr[1], [(h["amp"], h["cls"]) for h in rows_tr], R.RNG_SEED + k))
        mu, _ = B.candidate_answers((rep, "ridge", "x"), rows_tr, clusters, files, rows_te, files_te, Ytr, R.searched, (None,), spike)
        for j, i in enumerate(te):
            out.append({"fold": k, "amp": rows[i]["amp"], "cls": rows[i]["cls"], "rec": int(rows[i]["i"]), "cluster": dis[i],
                        "c": Y[0][i], "cm": Y[1][i], f"{rep}_ans": mu[j]})
    B.pca, B.SPIKE = keep, spike_size
    return out


def merged(reads):
    """Rows of several representations' reads, joined on row order, which the folds fix."""
    base = reads[0]
    for other in reads[1:]:
        for a, b in zip(base, other):
            if a["rec"] != b["rec"]:
                raise SystemExit("the reads' rows differ")
            a.update({k: v for k, v in b.items() if k.endswith("_ans")})
    return base


def cmd_plugin(a):
    from learn import reads_v3 as R

    reps = a.reps or list(REPS)
    B.feature = Features(Bank(a.net))
    split = plugin_split()
    res = {"net": a.net, "pcs": a.pcs}
    for kind in ("clean", "backed"):
        rows = merged([plugin_answers(rep, split, kind, a.pcs) for rep in reps])
        pairs = [(r, "mel") for r in reps if r != "mel"] if "mel" in reps else []
        res[kind] = group_read(rows, reps, pairs)
        res[kind + "_rows"] = len(rows)
        print(kind, len(rows), json.dumps({r: {g: round(res[kind][r][g]["r"], 3) for g in GROUP_NAMES} for r in reps}), flush=True)
        if a.controls:
            for check in ("shuffle", "spike"):
                S = plugin_answers(reps[0], split, kind, a.pcs, check)
                res[f"{kind}_{check}"] = {g: v[0] for g, v in R.corr(R.blocks(S, reps[0])).items()}
                print(kind, check, res[f"{kind}_{check}"], flush=True)
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1, default=float))


def code_key():
    h = hashlib.sha256()
    for f in ("bakeoff.py", "bakeoff_inputs.py", "eat_read.py"):
        h.update((PLUGIN_ROOT / "learn" / f).read_bytes())
    return h.hexdigest()[:16]


REFERENCES = {"M-ridge": ("mel", "ridge", "real"), "P4-ridge": ("mel", "ridge", "plugin")}   # at the stored 24 PCs
SAME_COUNT = {"M-pcs": ("mel", "ridge", "real"), "P-pcs": ("mel", "ridge", "plugin")}          # at the candidates' PC count


def candidates(mid):
    mix = f"mix:{mid}"
    return {"E-top": ("top", "ridge", "real"), "E-mid": (mid, "ridge", "real"), "E-mix": (mix, "ridge", "real"),
            "PE-top": ("top", "ridge", "plugin"), "PE-mid": (mid, "ridge", "plugin"), "PE-mix": (mix, "ridge", "plugin")}


def family_of():
    """The declared contrasts: (a, b, group, crunch only)."""
    return tuple((c, b, g, False) for c, b in (("E-top", "FTM"), ("E-mid", "FTM"), ("E-mix", "FTM"), ("E-top", "M-pcs"), ("E-mid", "M-pcs"),
                                               ("E-mix", "M-pcs"), ("PE-top", "W"), ("PE-mid", "W"), ("PE-mix", "W"), ("PE-top", "P-pcs"),
                                               ("PE-mid", "P-pcs"), ("PE-mix", "P-pcs"), ("M-pcs", "FTM"), ("P-pcs", "W")) for g in GROUP_NAMES)


def real_setup(a, pcs=None):
    """`bakeoff`'s harness on the rebuilt inputs: its feature, cache, PC count and plugin files and clusters swapped. The cache
    folder names the net, `mid` and PC count, since `code_key` does not. -> (rows, data, the comparison's own root)."""
    from learn import pipeline_fix as P

    net, pcs = a.net, a.pcs if pcs is None else pcs
    prior = B.root()
    rows, data = B.base_rows()
    pkeep = B.plugin_set()
    split = plugin_split()
    training = B.training_set

    def training_set(src, k, data_):
        if src != "plugin":
            return training(src, k, data_)
        got_rows, got_files = B.plugin_set()
        return got_rows, list(split[4]), got_files

    B.training_set = training_set
    paths = {str(P.dfix_input_path(u, v)): ("real", (u, v)) for u, _, _ in P.dfix_units() for v in range(P.DFIX_K)}
    paths.update({str(P.wide_path(r["i"], k)): ("wide", (r["i"], k)) for r in pkeep[0] for k in range(EB.WIDE_K)})
    B.plugin_set = functools.lru_cache(maxsize=1)(lambda: (pkeep[0], [fs[1:] for fs in pkeep[1]]))
    B.feature = Features(Bank(net), paths)
    B.OUT, B.code_key = f"{OUT}/{net}-{a.mid}-pc{a.pcs}", code_key
    with_pcs(pcs)
    return rows, data, prior


def add_prior(rows, prior, label):
    """A stored candidate's answers from the model comparison's rows, joined by position: both lists are `base_rows`' order."""
    old = pickle.loads((prior / "read-a.json.rows.pkl").read_bytes())
    if len(old) != len(rows):
        raise SystemExit("the stored rows differ")
    for r, q in zip(rows, old):
        if (r["fold"], r["set"], r["amp"], r["cls"], r["cluster"]) != (q["fold"], q["set"], q["amp"], q["cls"], q["cluster"]):
            raise SystemExit("the stored rows are in another order")
        r[f"{label}_ans"], r[f"{label}_swap"] = q[f"{label}_ans"], q[f"{label}_swap"]


def cmd_check(a):
    """S4.1: `M-ridge`'s stored answers from this code's feature path, then the shuffle and the spike."""
    from learn import reads_v3 as R

    rows, data, prior = real_setup(a, MEL_PCS)          # the mel control keeps the stored PC count
    by_fold = {k: [r for r in rows if r["fold"] == k] for k in range(FOLDS)}
    worst = 0.0
    for k in range(FOLDS):
        stored = np.load(prior / "answers" / f"M-ridge-k{k}.npz")["mu"]
        got = B.add_candidates([dict(r) for r in by_fold[k]], k, {"X": REFERENCES["M-ridge"]}, data, check="control")
        worst = max(worst, float(np.abs(np.stack([r["X_ans"] for r in got]) - stored).max()))
    print("M-ridge reproduced within", worst, flush=True)
    if worst > 1e-6:
        raise SystemExit("the mel control failed")
    cands = candidates(a.mid)
    res = {}
    keep_pca = B.pca
    with_pcs(a.pcs)
    for check in ("shuffle", "spike"):
        S = {k: [dict(r) for r in by_fold[k]] for k in range(FOLDS)}
        use = cands if check == "shuffle" else {q: cands[q] for q in ("E-top", "PE-top")}
        B.SPIKE = spiked_size(R_DIMS_TOP)
        for k in range(FOLDS):
            B.add_candidates(S[k], k, use, data, check=check)
        G = [r for k in range(FOLDS) for r in S[k] if r["set"] == "GOAT"]
        res[check] = {m: {g: v[0] for g, v in R.corr(R.blocks(G, m)).items()} for m in use}
        print(check, json.dumps(res[check], default=float), flush=True)
    B.pca = keep_pca
    (B.root().parent / "check.json").write_text(json.dumps({"mel_worst": worst, **res}, indent=1, default=float))


def declared(cands, a):
    ledger = json.loads((PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    entry = next((t for t in ledger["tests"] if t.get("test_id") == LEDGER_ID), None)
    if entry is None or not set(cands) <= set(entry.get("candidates", ())) or entry.get("mid") != a.mid or entry.get("pcs") != a.pcs:
        raise SystemExit(f"no declared read: ledger {LEDGER_ID!r} must list the candidates, the chosen `mid` and the PC count")


def cmd_amp(a):
    """S3.5: readers fitted on W's clean rows, read on each held unit's amp track alone. Report only. BKS's own DIs are among W's
    rows, so only GOAT is zero-shot."""
    from learn import pipeline_fix as P
    from learn import reads_v3 as R

    B.sha_ok()
    cands = {"A-top": ("top", "ridge", "plugin"), "A-mid": (a.mid, "ridge", "plugin"), "A-mel": ("mel", "ridge", "plugin")}
    declared(cands, a)
    rows, data, _ = real_setup(a)
    feats = B.feature
    feats.paths = {str(P.dfix_input_path(u, 0)): ("amp", (u, -1)) for u, _, _ in P.dfix_units()}
    pkeep = B.plugin_set()
    B.plugin_set = functools.lru_cache(maxsize=1)(lambda: (pkeep[0], [[("clean", (r["i"], -1))] for r in pkeep[0]]))
    B.OUT = f"{OUT}/amp-{a.net}-{a.mid}-pc{a.pcs}"
    by_fold = {k: [r for r in rows if r["fold"] == k] for k in range(FOLDS)}
    for k in range(FOLDS):
        B.add_candidates(by_fold[k], k, cands, data)
    flat = [r for k in range(FOLDS) for r in by_fold[k]]
    res = {}
    for st in ("GOAT", "BKS"):
        S = [r for r in flat if r["set"] == st]
        labels = list(cands)
        res[st] = {m: {g: v[0] for g, v in R.corr(R.blocks(S, m)).items()} for m in labels}
        if st == "GOAT":
            res["pairs"] = {k_: v for k_, v in R.goat_intervals(S, labels, [("A-top", "A-mel"), ("A-mid", "A-mel")]).items() if isinstance(v, dict)}
    pathlib.Path(a.out).write_text(json.dumps({"GOAT": res["GOAT"], "BKS": res["BKS"], "pairs": {f"{k_[0]}|{k_[1]}": v for k_, v in res["pairs"].items()}},
                                              indent=1, default=float))


def cmd_real(a):
    from learn import reads_v3 as R

    B.sha_ok()
    cands = candidates(a.mid)
    declared(cands, a)
    rows, data, prior = real_setup(a)
    add_prior(rows, prior, "W-ridge")
    by_fold = {k: [r for r in rows if r["fold"] == k] for k in range(FOLDS)}
    for k in range(FOLDS):
        B.add_candidates(by_fold[k], k, {**cands, **SAME_COUNT}, data)
    with_pcs(MEL_PCS)                                   # the earlier references keep their stored PC count
    for k in range(FOLDS):
        B.add_candidates(by_fold[k], k, REFERENCES, data)
    rows = [r for k in range(FOLDS) for r in by_fold[k]]
    pathlib.Path(a.out + ".rows.pkl").write_bytes(pickle.dumps(rows))
    labels = ["FTM", "W", "W-ridge", *REFERENCES, *SAME_COUNT, *cands]
    fam = family_of()
    side = [(c, "W-ridge") for c in ("E-top", "E-mid", "E-mix")]
    res = R.report(rows, labels, pairs=sorted({(q[0], q[1]) for q in fam} | set(side)))
    res["crunch"] = B.crunch_read(rows, labels)
    res["bounds"] = B.bounds(rows, fam)
    res["player"] = B.player_read(rows, labels, data[4])
    res["family"] = B.family(rows, labels)
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1, default=float))


def auc(score, y):
    """The chance a random positive scores above a random negative, ties halved."""
    from scipy.stats import rankdata

    r = rankdata(score)
    pos = y > 0
    n1, n0 = pos.sum(), (~pos).sum()
    return float((r[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def cmd_domain(a):
    """S3.4: how plainly each representation tells plugin mixes from real ones, and how far the plugin knob directions sit from
    that direction. Plugin rows in backing 0, real units in backing 0, whole DIs held by fold; only plugin labels are read."""
    from learn import pipeline_fix as P
    from learn import reads_v3 as R
    from learn import trusted_data_t3 as T3

    rows, folds = plugin_split()[:2]
    enc = T3.encode_for(T3.FULL)
    feats = Features(Bank(a.net))
    units = P.dfix_units()
    res = {}
    for rep in a.reps:
        Xp = np.stack([feats(rep, None, ("wide", (r["i"], 0)), None, None).mean(0) for r in rows])
        Xr = np.stack([feats(rep, None, ("real", (u, 0)), None, None).mean(0) for u, _, _ in units])
        cp = list(folds)
        cr = B.inner_folds([prt["di"] for _, _, prt in units], FOLDS).tolist()
        X = np.concatenate([Xp, Xr]).astype(np.float64)
        y = np.r_[np.ones(len(Xp)), -np.ones(len(Xr))]
        f = np.array(cp + cr)
        score = np.zeros(len(y))
        for k in range(FOLDS):
            m, comp = B.pca(X[f != k], a.pcs)
            Z = (X - m) @ comp.T
            w = B.ridge(Z[f != k], y[f != k] - y[f != k].mean(), 1.0)
            score[f == k] = Z[f == k] @ w
        m, comp = B.pca(X, a.pcs)
        Z = (X - m) @ comp.T
        wd = B.ridge(Z, y - y.mean(), 1.0)
        wd /= np.linalg.norm(wd)
        c, cm = [np.stack(q) for q in list(zip(*(enc(h["label"]) for h in rows)))[:2]]
        cells = [(h["amp"], h["cls"]) for h in rows]
        Zc, _ = B.centre_within(Z[:len(rows)], cells)
        cosines = {}
        for g, heads in R.HEADS.items():
            v = []
            for j in heads:
                on = cm[:, j] > 0
                if on.sum() < 100:
                    continue
                t, _ = B.centre_within(c[on, j][:, None], [q for q, w_ in zip(cells, on) if w_])
                w = B.ridge(Zc[on], t[:, 0], 1.0)
                v.append(abs(float(w @ wd)) / (np.linalg.norm(w) + 1e-12))
            cosines[g] = float(np.mean(v))
        res[rep] = {"auc": auc(score, y), "abs_cosine": cosines}
        print(rep, res[rep], flush=True)
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1, default=float))


def cmd_tags(a):
    """S4.4, report only: AudioSet's outputs as answers, with no fit: each class's logit on every head, read by group on the
    backed input and on the amp track alone. A within-cell r on GOAT and BKS."""
    from learn import eat_net as E
    from learn import pipeline_fix as P
    from learn import reads_v3 as R

    B.sha_ok()
    declared([f"tag:{c}" for c in TAG_CLASSES], a)
    rows, data = B.base_rows()
    units = []
    for k in range(FOLDS):
        fold = [r for r in rows if r["fold"] == k]
        _, held, _ = P.dfix_rows_of(*data, k)
        if [(h["amp"], h["cls"]) for h in held] != [(r["amp"], r["cls"]) for r in fold]:
            raise SystemExit("the fold's rows are in another order")
        units += [(r, h["real"]) for r, h in zip(fold, held)]
    names = E.class_names()
    res = {}
    for kind, variant in (("real", 0), ("amp", -1)):
        bank = Bank(a.net)
        arr = bank.array(kind, "logits")
        S = []
        for r, unit in units:
            v = np.asarray(arr[bank.row(kind, (unit, variant))], np.float32).mean(0)
            S.append({**r, **{f"{c}_ans": np.full(len(r["c"]), float(v[names.index(c)])) for c in TAG_CLASSES}})
        res[kind] = {st: {c: {g: v[0] for g, v in R.corr(R.blocks([r for r in S if r["set"] == st], c)).items()} for c in TAG_CLASSES}
                     for st in ("GOAT", "BKS")}
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, default=float))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plugin")
    p.add_argument("out")
    p.add_argument("--reps", nargs="+")
    p.add_argument("--controls", action="store_true")
    p.set_defaults(fn=cmd_plugin)
    c = sub.add_parser("check")
    c.add_argument("--mid", required=True)
    c.set_defaults(fn=cmd_check)
    for name, fn in (("amp", cmd_amp), ("real", cmd_real)):
        r = sub.add_parser(name)
        r.add_argument("out")
        r.add_argument("--mid", required=True)
        r.set_defaults(fn=fn)
    t = sub.add_parser("tags")
    t.add_argument("out")
    t.add_argument("--mid", required=True)
    t.set_defaults(fn=cmd_tags)
    d = sub.add_parser("domain")
    d.add_argument("out")
    d.add_argument("--reps", nargs="+", required=True)
    d.set_defaults(fn=cmd_domain)
    for q in (p, c, d, *(sub.choices[n] for n in ("amp", "real", "tags"))):
        q.add_argument("--net", default="mn10_as")
        q.add_argument("--pcs", type=int, default=24)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
