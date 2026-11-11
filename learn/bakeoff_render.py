"""Model comparison, by the score (`docs/model-comparison-plan.md`, Phase 5), on read 2's units.

    $TORCH_PY -m learn.bakeoff_render predict --tag M-ridge               # answers, CPU, zero renders
    $TORCH_PY -m learn.bakeoff_render predict-arm --tag A-mic             # a mixture arm's answers, after a control on FTm's nets
    $MAIN -m learn.bakeoff_render render --tags S,RcBG,P2b-ftm,M-ridge --shard 0/3
    $MAIN -m learn.bakeoff_render report OUT.json --tags M-ridge          # zero renders

A ridge candidate reads each direction from its search half. It copies stored `RcBG`'s settings for the direction, overwrites
only the searched knobs, and fits residuals around RcBG's own values, so `ridge - centre` reads only the knob gain. Each direction
is judged on both halves with `distance`, `tonal` and the cross-fitted term; no audio is kept. A re-rendered stored tag is held
to its stored judge and render hash. Shards resume, and stop between units if PF/bakeoff/STOP exists. S, RcBG and FTm are
rendered again because stored judges hold `distance` only.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import sys
import time

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

ANY = "*"
FLOOR_GB = 33
SETS = ("goat", "bks")
TERMS = ("distance", "tonal", "cross")
FTM = "P2b-ftm"


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def overwrite(settings, dims, base, residual):
    """`settings` {(module, key): stored} with each searched knob at its centre value plus the residual, clipped.
    dims: [(dim, head)]; base, residual: per head. -> a new dict."""
    from learn import knob_ceiling as K

    out = dict(settings)
    for d, j in dims:
        out[(d.module, d.key)] = K.fmt(d.from_unit(min(max(float(base[j] + residual[j]), 0.0), 1.0)))
    return out


def direction_rows(units):
    """[(key, search, held)]: each key's answer for a search half is scored on the other."""
    return [(k, s, h) for k in units for s, h in (("A", "B"), ("B", "A"))]


def value(judge, tag, key, search, held, term):
    """One direction's term: None (not rendered), "refused", or a finite value."""
    g = judge.get(tag, {}).get(key) or {}
    v = g.get(search) or g.get(ANY)
    if v is None or held not in v:
        return None
    x = v[held] and v[held].get(term)
    return x if isinstance(x, (int, float)) and math.isfinite(x) else "refused"


def judges_match(old, new, tol=1e-9):
    """Stored {half: distance} against new {half: {term: value} or None}, every half compared; a refusal counts as inf, and a
    refusal against a finite value is a mismatch."""
    for h, x in old.items():
        y = new[h]["distance"] if new.get(h) else math.inf
        if not (x == y or abs(x - y) < tol):
            return False
    return True


def contrast(a, b, s, term):
    """A direction's contrast of a on b, for its three stored values: ln ratio, or the plain difference for `cross`, which can
    be negative; a refused answer scores as S; S refused or a value missing gives None."""
    if s is None or s == "refused" or a is None or b is None:
        return None
    a, b = (s if a == "refused" else a), (s if b == "refused" else b)
    if term == "cross":
        return a - b
    return math.log(a / b) if a > 0 and b > 0 else None


def t_interval(pairs, t90):
    """[(cluster, value)] -> the mean of cluster means with its 90% t interval and the count below zero."""
    g = collections.defaultdict(list)
    for c, v in pairs:
        g[c].append(v)
    m = np.array([np.mean(v) for v in g.values()])
    n = len(m)
    if n < 2:
        return {"mean": float(m.mean()) if n else None, "clusters": n}
    h = t90(n - 1) * m.std(ddof=1) / math.sqrt(n)
    return {"mean": float(m.mean()), "lo90": float(m.mean() - h), "hi90": float(m.mean() + h), "closer": int((m < 0).sum()), "clusters": n}


def strata(values, n=3):
    """{key: stratum 0..n-1} by rank of a value."""
    keys = sorted(values, key=values.get)
    return {k: min(i * n // max(len(keys), 1), n - 1) for i, k in enumerate(keys)}


# --- paths and units -------------------------------------------------------------------------------------------------

def root():
    from learn import pipeline_fix as P

    return P.out_dir() / "bakeoff"


def answers_path(which, tag):
    return root() / "score-answers" / which / f"{tag}.json"


def judge_path(which, tag, key):
    return root() / "score-judge" / which / tag / f"{key.replace('/', '__')}.json"


def stored_dir(which):
    from learn import pipeline_fix as P

    return P.out_dir() / (P.GOAT_DIR if which == "goat" else P.REAL_DIR)


def read_units():
    """[(set, unit record with fold)]: BKS's 40 read units on all three amps' keys, then GOAT's trusted units."""
    from learn import pipeline_fix as P

    folds = P.real_labels(2)[2]
    bks = json.loads((P.out_dir() / P.REAL_DIR / "answers" / "RcBG.json").read_text())["parts"]
    return [("bks", dict(p_, fold=folds[p_["di"]])) for p_ in bks] + [("goat", p_) for p_ in P.goat_read_units()]


def keys_of(which, prt):
    from learn import pipeline_fix as P

    return [P.real_key(prt, a) for a in P.AMPS3] if which == "bks" else [P.real_key(prt, prt["amp"])]


def stored_answers(which, tag):
    """A tag's {key: {search or "*": {select, settings}}}: this plan's own, then the stored read's."""
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    own = answers_path(which, tag)
    if own.exists():
        return json.loads(own.read_text())["answers"]
    if tag == "S" and which == "goat":
        ms = P.A_menu_S()
        out = {}
        for p_ in P.goat_read_units():
            sel, S = ms[p_["amp"]][p_["cls"]]
            out[P.real_key(p_, p_["amp"])] = {ANY: {"select": sel, "settings": LO.sdict(S)}}
        return out
    return json.loads((stored_dir(which) / "answers" / f"{tag}.json").read_text())["answers"]


# --- answers ---------------------------------------------------------------------------------------------------------

def fit_fold(k, name, fit, data, centres, seed=None):
    """A ridge-family candidate on fold k's training records, residuals about the fold's centres; `seed` picks W's seed for
    W's features. -> predict(features [m, d], cells) -> residuals [m, knobs]."""
    from learn import bakeoff as B
    from learn import reads_v3 as R
    from learn import trusted_data_t3 as T3

    rows_tr, clusters, files = B.training_set("real", k, data)
    enc = T3.encode_for(T3.FULL)
    Y = [np.stack(z) for z in zip(*(enc(h["label"]) for h in rows_tr))]
    c, cm = Y[0].astype(float), Y[1].astype(float)
    cells = [(h["amp"], h["cls"]) for h in rows_tr]
    mask = cm * np.stack([R.searched(*q)[0] for q in cells])
    resid = (c - np.stack([centres[(k, *q)] for q in cells])) * mask
    X = np.stack([[B.feature(name, seed, f, h["amp"], h["cls"]) for f in fs] for h, fs in zip(rows_tr, files)])
    n, v, h_, d = X.shape
    rep = np.repeat(np.arange(n), v * h_)
    flat, means = B.centre_within(X.reshape(-1, d), [cells[i] for i in rep])
    m, comp = B.pca(flat)
    Z = (flat - m) @ comp.T
    heads = {}
    for j in np.nonzero(mask.sum(0))[0]:
        keep = mask[rep, j] > 0
        if keep.sum() >= 2 * v:
            heads[int(j)] = B.FITS[fit](Z[keep], resid[rep, j][keep], [clusters[i] for i, w in zip(rep, keep) if w])

    def predict(x, cell):
        q = (B.centre_within(x, cell, means)[0] - m) @ comp.T
        out = np.zeros((len(x), c.shape[1]))
        for j, f in heads.items():
            out[:, j] = f(q)
        return out
    return predict


def cmd_predict(a):
    from learn import bakeoff as B
    from learn import full_space as F
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import reads_v3 as R
    from learn import trusted_data_t3 as T3

    if a.tag not in B.CANDIDATES or B.CANDIDATES[a.tag][1] != "ridge" or B.CANDIDATES[a.tag][2] != "real":
        raise SystemExit("predict takes a real-trained ridge; arms need per-half answers of their own")
    if any((root() / "score-judge" / w / a.tag).exists() for w in SETS):
        raise SystemExit(f"{a.tag}: judges exist, and new answers would sit under old judges; move them aside first")
    name, fit, _ = B.CANDIDATES[a.tag]
    brecs, by_unit, folds = P.real_labels(2)
    grecs, gunits, _ = P.goat_labels()
    data = (brecs, by_unit, folds, grecs, gunits)
    ms = P.A_menu_S()
    enc = T3.encode_for(T3.FULL)
    D = F.by_name()
    stored = {w: stored_answers(w, "RcBG") for w in SETS}
    units = read_units()
    centres = {}
    for which, prt in units:                            # RcBG holds one setting per (fold, amp, class): take it from the store
        for key in keys_of(which, prt):
            amp = key.rsplit("|", 1)[1]
            st = LO.tdict(stored[which][key][ANY]["settings"])
            v = enc(F.label_of(st, amp))[0].astype(float)
            q = (prt["fold"], amp, prt["cls"])
            if q in centres and not np.allclose(centres[q], v):
                raise SystemExit(f"{q}: RcBG differs within a cell")
            centres[q] = v
    # A training cell of a fold with no read unit gets its centre the way RcBG was built.
    src = {k: P.centre_records(brecs, by_unit, folds, grecs, gunits, k) for k in range(P.REAL_FOLDS)}

    def cls_of(r):
        return (by_unit[r["unit"]] if r["unit"] in by_unit else gunits[r["unit"]])["cls"]

    for k in range(P.REAL_FOLDS):
        for amp in P.AMPS3:
            for cls in ("clean", "crunch"):
                if (k, amp, cls) not in centres:
                    sel, S = ms[amp][cls]
                    labels = [LO.tdict(r["label"]) for r in src[k]["RcBG"] if r["amp"] == amp and cls_of(r) == cls]
                    centres[(k, amp, cls)] = enc(F.label_of(P.rc_setting(K.space(amp, S), S, labels), amp))[0].astype(float)
    seeds = R.SEEDS if name == "W" else (None,)
    models = {k: [(sd, fit_fold(k, name, fit, data, centres, sd)) for sd in seeds] for k in range(P.REAL_FOLDS)}
    out = {w: {} for w in SETS}
    for which, prt in units:
        for key in keys_of(which, prt):
            amp = key.rsplit("|", 1)[1]
            cell = (amp, prt["cls"])
            sel, S = ms[amp][prt["cls"]]
            base = LO.tdict(stored[which][key][ANY]["settings"])
            dims = [(D[n], j) for j, n in enumerate(F.CONT) if (D[n].module, D[n].key) in {(d.module, d.key) for d in K.space(amp, S)}]
            res = np.mean([f(B.feature(name, sd, str(P.dfix_input_path(prt["unit"], 0)), amp, prt["cls"]), [cell, cell])
                           for sd, f in models[prt["fold"]]], 0)
            c = centres[(prt["fold"], *cell)]
            out[which][key] = {h: {"select": stored[which][key][ANY]["select"], "settings": LO.sdict(overwrite(base, dims, c, res[i]))}
                               for i, h in enumerate("AB")}
    for which, ans in out.items():
        p = answers_path(which, a.tag)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"tag": a.tag, "code_key": B.code_key(), "time": time.strftime("%Y-%m-%d %H:%M:%S"), "answers": ans}))
        print(a.tag, which, len(ans), "keys", flush=True)


def net_answers(models, units, hold=None):
    """Answers read from nets as `pipeline_fix.goat_predict` reads them: the backed input per search half, seeds pooled, every
    control outside `K.space` at S (`hold`: a C3 tag's per-control hold instead). models: {fold: [net per seed]}.
    -> {set: {key: {search: {select, settings}}}}."""
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    ms = P.A_menu_S()
    out = {w: {} for w in SETS}
    for which, prt in units:
        backed = P.dfix_backed(prt["unit"])
        for key in keys_of(which, prt):
            amp = key.rsplit("|", 1)[1]
            sel, S = ms[amp][prt["cls"]]
            for search in ("A", "B"):
                s8, ls = backed[search]
                x, c = DS.model_input(s8, s8, ls, ls, search, amp, prt["cls"], "Dstem")
                r = F.readout([o[0] for o in F.run_nets(models[prt["fold"]], [x], [c])])
                st = F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"])
                st = P.hold_outside_space(st, S, amp) if hold is None else P.hold_outside_space(st, S, amp, hold)
                out[which].setdefault(key, {})[search] = {"select": sel, "settings": LO.sdict(st)}
    return out


def fold_nets(tag):
    """{fold: [net per seed]}: an H4 tag's FT_k runs (`pipeline_fix.H4_FT_TAGS`), each at its read checkpoint
    (`ft_read_check`) and its own arm's run on the pinned exclusions (`h4_read_check`, which needs `phase_h4` and
    `phase_h4_exclusions`), for `net_answers` to read as it reads FTm's. A C3 tag (`pipeline_fix.C3_TAGS`) reads C3's
    FT_k runs, each checked against C2's state (`full_controls_c3.read_check`)."""
    from learn import pipeline_fix as P

    c3 = tag in P.C3_READ                         # C3's tags and C3i's: C3's C2-state check on each run
    if tag not in P.H4_FT_TAGS and not c3:
        raise SystemExit(f"fold_nets: {tag} is not an H4 tag, nor a C3 one ({', '.join(sorted(P.H4_FT_TAGS | P.C3_READ))})")
    sha = None if c3 else P.h4_exclusions()["sha256"]
    out = {}
    for k in range(P.REAL_FOLDS):
        out[k] = []
        for sd in P.SEEDS:
            net, rec = P.load_run(f"{P.model_base(tag)}-k{k}", sd, "best")
            P.ft_read_check(rec)
            if c3:
                P.C3_read_check(rec)
            else:
                P.h4_read_check(rec, sha)
            out[k].append(net)
    return out


def cmd_predict_arm(a):
    """A mixture arm's per-half answers, after the same code on FTm's own nets reproduces its stored answers."""
    from learn import bakeoff_train as T
    from learn import pipeline_fix as P

    units = read_units()
    ftm = {k: [P.load_run(f"{FTM}-k{k}", sd, "best")[0] for sd in T.SEEDS] for k in range(P.REAL_FOLDS)}
    got = net_answers(ftm, units)
    for w in SETS:
        want = stored_answers(w, FTM)
        bad = [k for k in got[w] if got[w][k] != want[k]]
        if bad:
            raise SystemExit(f"control: {w}: {len(bad)} of {len(got[w])} keys differ from the stored {FTM} answers, first {bad[0]}")
    print("CONTROL OK: FTm's stored answers reproduced", flush=True)
    arm = {k: [T.load_arm(a.tag, k, sd) for sd in T.SEEDS] for k in range(P.REAL_FOLDS)}
    out = net_answers(arm, units)
    for which, ans in out.items():
        p = answers_path(which, a.tag)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"tag": a.tag, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "answers": ans}))
        print(a.tag, which, len(ans), "keys", flush=True)


# --- renders ---------------------------------------------------------------------------------------------------------

def scored(ref, y, di, lag):
    """{half: {term: value}} or a half's None on refusal; `band_errors`' distance is held to J0's."""
    from analysis.aligned import aligned_distance

    from learn import bakeoff_judge as BJ
    from learn import knob_ceiling as K

    out = {}
    for h, (a, b) in K.R.HALVES.items():
        r = aligned_distance(ref, y, di, lag=lag, render_latency=K.P.LATENCY, start_s=a, end_s=b)
        if r.distance is None:
            out[h] = None
            continue
        t = BJ.terms_of(BJ.band_errors(ref, y, di, K.P.LATENCY, a, b, lag=lag))
        if abs(t["distance"] - r.distance) > 1e-9:
            raise SystemExit(f"band_errors left J0: {t['distance']} against {r.distance}")
        out[h] = {"distance": r.distance, "tonal": r.tonal, "cross": t["cross"]}
    return out


def stored_record(which, tag, key):
    """A stored tag's judge and hashes for a key; GOAT's S lives in the search records."""
    from learn import pipeline_fix as P

    if which == "goat" and tag == "S":
        p = stored_dir(which) / P.SEARCH_DIR / f"{key.replace('/', '__')}.json"
        if not p.exists():
            return None
        r = json.loads(p.read_text())
        return {"judge": {ANY: r["s_judge"]}, "render_sha256": {ANY: r["s_render_sha256"]}}
    p = stored_dir(which) / "judge" / tag / f"{key.replace('/', '__')}.json"
    return json.loads(p.read_text()) if p.exists() else None


def cmd_render(a):
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B

    tags = [t for t in a.tags.split(",") if t]
    ans = {w: {t: stored_answers(w, t) for t in tags} for w in SETS}
    k, n = a.shard
    units = read_units()
    mine = [q for j, q in enumerate(units) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for which, prt in mine:
        if (root() / "STOP").exists():
            print("STOPPED between units", flush=True)
            return
        if PS.free_gb() < FLOOR_GB:
            raise SystemExit(f"DISK GUARD: free disk below {FLOOR_GB} GB")
        if which == "goat":
            lag = prt["lag"]
        else:
            lag = json.loads((P.out_dir() / P.REAL_DIR / "lags" / f"{prt['unit'].replace('/', '__')}.json").read_text())["lag"]
            if lag is None:
                continue
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        for key in keys_of(which, prt):
            amp = key.rsplit("|", 1)[1]
            for t in tags:
                if key not in ans[which][t]:
                    continue
                out = judge_path(which, t, key)
                if out.exists():
                    continue
                rec = {"unit": prt["unit"], "amp": amp, "tag": t, "lag": lag, "judge": {}, "render_sha256": {}}
                for search, ask in sorted(ans[which][t][key].items()):
                    st = LO.tdict(ask["settings"])
                    y = np.asarray(AM.fresh_render(CB.new_renderer, di32, ask["select"], st, st), np.float64)[trim[0]:trim[1]]
                    renders += 2
                    rec["judge"][search] = scored(ref, y, di, lag)
                    rec["render_sha256"][search] = AM.audio_sha(y)
                old = stored_record(which, t, key)
                if old is not None:                     # a stored tag must come back the same
                    for search, v in rec["judge"].items():
                        same = old["render_sha256"].get(search) == rec["render_sha256"][search]
                        if not (same and judges_match(old["judge"][search], v)):
                            raise SystemExit(f"{t} {key} {search}: differs from its stored render or judge")
                out.parent.mkdir(parents=True, exist_ok=True)
                tmp = out.with_suffix(".tmp")
                tmp.write_text(json.dumps(rec))
                tmp.replace(out)
        print(f"{which} {prt['unit'][-50:]}: renders so far {renders}", flush=True)
    print(f"BAKEOFF-RENDER DONE {k}/{n}: {renders} renders", flush=True)


# --- the report ------------------------------------------------------------------------------------------------------

def check_goat_s(judge):
    """GOAT's S, rendered again, against the search records' judges and hashes. -> keys compared."""
    n = 0
    for p in (root() / "score-judge" / "goat" / "S").glob("*.json"):
        r = json.loads(p.read_text())
        old = stored_record("goat", "S", f"{r['unit']}|{r['amp']}")
        if old is None:
            continue
        if r["render_sha256"][ANY] != old["render_sha256"][ANY] or not judges_match(old["judge"][ANY], r["judge"][ANY]):
            raise SystemExit(f"GOAT S {r['unit']}: differs from its search record")
        n += 1
    return n


def cmd_report(a):
    from learn import pretrain_set as PS

    tags = [t for t in a.tags.split(",") if t]
    base = ("RcBG", FTM, "S")
    out = {}
    units = read_units()
    for which in SETS:
        judge = {}
        for t in {*tags, *base}:
            judge[t] = {}
            for p in (root() / "score-judge" / which / t).glob("*.json"):
                r = json.loads(p.read_text())
                judge[t][f"{r['unit']}|{r['amp']}"] = r["judge"]
        if which == "goat":
            out["goat_s_held"] = check_goat_s(judge)
        folds = {key: prt for w, prt in units if w == which for key in keys_of(w, prt)}
        keys = sorted(folds)
        d_s = {}
        for key in keys:
            vals = [value(judge, "S", key, s, h, "distance") for _, s, h in direction_rows([key])]
            vals = [v for v in vals if isinstance(v, float)]
            if vals:
                d_s[key] = float(np.mean(vals))
        band = strata(d_s)
        cluster = (lambda q: q["unit"].split("@")[0]) if which == "goat" else (lambda q: q["di"])
        rows = {}
        for x, y in ([(t, b) for t in tags for b in base] + [(FTM, "RcBG"), (FTM, "S"), ("RcBG", "S")]):
            for term in TERMS:
                pts, by_stratum, cnt = [], collections.defaultdict(list), collections.Counter()
                for key, s, h in direction_rows(keys):
                    vx, vy, vs = (value(judge, t, key, s, h, term) for t in (x, y, "S"))
                    if vs == "refused":
                        cnt["s_refused"] += 1
                    elif vx is None or vy is None or vs is None:
                        cnt["missing"] += 1
                    cnt["refused_scored_as_S"] += ("refused" in (vx, vy)) and vs not in (None, "refused")
                    c = contrast(vx, vy, vs, term)
                    if c is None:
                        continue
                    prt = folds[key]
                    pts.append((prt, c, key))
                    if key in band:
                        by_stratum[band[key]].append((cluster(prt), c))
                parts = collections.defaultdict(list)
                for p, c, _ in pts:
                    parts[(cluster(p), p["unit"])].append(c)
                rows[f"{x} - {y} | {term}"] = {
                    "directions": len(pts), **cnt,
                    "by_cluster": t_interval([(cluster(p), c) for p, c, _ in pts], PS.t90),
                    "by_fold": t_interval([(p["fold"], c) for p, c, _ in pts], PS.t90),
                    "part_weighted": t_interval([(q[0], float(np.mean(v))) for q, v in parts.items()], PS.t90),
                    "by_d_S": {str(q): t_interval(v, PS.t90) for q, v in sorted(by_stratum.items())}}
        out[which] = rows
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print("GOAT S held to the search records:", out["goat_s_held"], flush=True)
    for which in SETS:
        for name, r in out[which].items():
            c = r["by_cluster"]
            if name.endswith("distance") and "lo90" in c:
                print(which, name, f"{c['mean']:+.3f} [{c['lo90']:+.3f}, {c['hi90']:+.3f}] n {r['directions']}", flush=True)


def shard(s):
    k, n = s.split("/")
    return int(k), int(n)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("predict")
    p.add_argument("--tag", required=True)
    p.set_defaults(fn=cmd_predict)
    p = sub.add_parser("predict-arm")
    p.add_argument("--tag", required=True)
    p.set_defaults(fn=cmd_predict_arm)
    p = sub.add_parser("render")
    p.add_argument("--tags", required=True)
    p.add_argument("--shard", type=shard, default=(0, 1))
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("report")
    p.add_argument("out")
    p.add_argument("--tags", required=True)
    p.set_defaults(fn=cmd_report)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
