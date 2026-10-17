"""Independent recomputation of experiment 1b from scores/ (no repo code)."""
import json, math, pathlib, itertools
import numpy as np
from scipy import stats

ROOT = pathlib.Path.home() / "ndsp-presets/learn/local-objective"
HERE = pathlib.Path(__file__).parent
P = json.load(open(HERE / "parts.json"))
SIG = json.load(open(ROOT / "sigma.json"))
CUR = "cprime|stem|native|own"; TRUE = "measure|reference|native|own"
MAT = "cprime_ref|reference|native|own"; MATG = "cprime_ref|reference|gcc|own"; CREF = "cprime|reference|native|own"

def fin(x): return isinstance(x, (int, float)) and math.isfinite(x)

def sp(o, t):
    pr = [(a, b) for a, b in zip(o, t) if fin(a) and fin(b) and b > 0]
    if len(pr) < 3: return None
    a, b = zip(*pr)
    if len(set(a)) < 2 or len(set(b)) < 2: return None
    return float(np.corrcoef(stats.rankdata(a), stats.rankdata(b))[0, 1])

def sp_worst(o, t):
    a = [x if fin(x) else 1e300 for x in o]; b = [x if fin(x) else 1e300 for x in t]
    if len(set(a)) < 2 or len(set(b)) < 2: return None
    return float(np.corrcoef(stats.rankdata(a), stats.rankdata(b))[0, 1])

def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None

def rel_pairs(T):
    n = len(T["A"]); ok = [i for i in range(n) if all(fin(T[h][i]) and T[h][i] > 0 for h in "AB")]
    out = []
    for i, j in itertools.combinations(ok, 2):
        sa = np.sign(T["A"][i] - T["A"][j]); sb = np.sign(T["B"][i] - T["B"][j])
        if sa != 0 and sa == sb: out.append((i, j, sa))
    return out

def rel_acc(O, pairs):
    accs = []
    for h in "AB":
        n = c = 0
        for i, j, s in pairs:
            a, b = O[h][i], O[h][j]
            if not (fin(a) and fin(b)): continue
            n += 1; d = np.sign(a - b); c += 1 if d == s else (0.5 if d == 0 else 0)
        accs.append(c / n if n else None)
    return mean(accs)

SUBS = {"all": {"S", "nbr", "ks", "armA"}, "nbhd": {"S", "nbr"}, "ks": {"ks"}, "armA": {"armA"},
        "noArmA": {"S", "nbr", "ks"}}
per = {}; nonfin = {MAT: 0, CUR: 0, TRUE: 0}; integ = {"repeat": [], "flac": [], "renders": 0, "warm": 0, "cells": 0}
for key, pts in sorted(SIG["cells"].items()):
    slug, amp = key.split("|")
    sc = {}
    for d in ("cprime", "measure", "cprime_ref"):
        j = json.load(open(ROOT / "scores" / d / slug / f"{amp}.json"))
        assert j["sigma"] == SIG["hash"] and len(j["scores"]) == 48 == len(pts), (d, key)
        for cfg in j["scores"][0]:
            sc[cfg] = {h: [s[cfg][h] for s in j["scores"]] for h in "AB"}
        if d == "cprime_ref":
            integ["flac"] += [v for hv in j["flac_vs_float_S"].values() for v in hv.values()]
    # order check: measure at S vs K_S stored; cprime vs arm A stored
    for i, p in enumerate(pts):
        if p.get("true_stored"):
            for h, v in p["true_stored"].items():
                if not (fin(v) and fin(sc[TRUE][h][i])): assert fin(v) == fin(sc[TRUE][h][i]); continue
                assert abs(math.log(sc[TRUE][h][i] / v)) < 0.01, ("true order", key, i)
        if p.get("obj_stored"):
            for h, v in p["obj_stored"].items():
                if fin(v) and fin(sc[CUR][h][i]):
                    assert abs(math.log(sc[CUR][h][i] / v)) < 0.01, ("obj order", key, i)
    r = json.load(open(ROOT / "renders" / "cprime_ref" / slug / f"{amp}.json"))
    assert r["status"] == "done" and r["sigma"] == SIG["hash"] and r["di"] == "cprime_ref"
    integ["renders"] += r["renders"]; integ["warm"] += r["warm_ups"]; integ["cells"] += 1
    integ["repeat"] += [c[3] for c in r["checks_float"] if c[1] == "repeat_S"]
    assert pts[r["S_float"]["index"]]["source"] == "S"
    for c in (MAT, CUR, TRUE):
        nonfin[c] += sum(not fin(v) for h in "AB" for v in sc[c][h])
    T = sc[TRUE]; per[key] = {}
    for sub, srcs in SUBS.items():
        idx = [i for i, p in enumerate(pts) if p["source"] in srcs]
        t = {h: [T[h][i] for i in idx] for h in "AB"}
        pairs = rel_pairs(t)
        d = {"ceiling": sp(t["A"], t["B"]), "npairs": len(pairs), "n": len(idx)}
        for name, cfg in (("matched", MAT), ("current", CUR), ("cref", CREF), ("matched_gcc", MATG)):
            o = {h: [sc[cfg][h][i] for i in idx] for h in "AB"}
            d[name] = {"cross": mean([sp(o[h], t["B" if h == "A" else "A"]) for h in "AB"]),
                       "same": mean([sp(o[h], t[h]) for h in "AB"]),
                       "worst": mean([sp_worst(o[h], t["B" if h == "A" else "A"]) for h in "AB"]),
                       "rel": rel_acc(o, pairs)}
        per[key][sub] = d

def agg(vals, label=""):
    pm = {}
    for k, v in vals.items():
        if v is None: continue
        pm.setdefault(k.split("|")[0], []).append(v)
    pm = {s: np.mean(v) for s, v in pm.items()}
    bm = {}
    for s, v in pm.items(): bm.setdefault(P[s]["band"], []).append(v)
    bm = {b: np.mean(v) for b, v in bm.items()}
    x = np.array(list(bm.values())); g = len(x); m = x.mean()
    h = stats.t.ppf(0.95, g - 1) * x.std(ddof=1) / math.sqrt(g)
    loo = [np.mean([v for bb, v in bm.items() if bb != b]) for b in bm]
    return dict(m=round(m, 3), lo=round(m - h, 3), hi=round(m + h, 3), bands=g, parts=len(pm),
                cells=sum(v is not None for v in vals.values()), pos=int((x > 0).sum()),
                loo_min=round(min(loo), 3), loo_max=round(max(loo), 3), _bm=bm)

def col(sub, name, k): return {c: per[c][sub][name][k] for c in per}
def ceil(sub): return {c: per[c][sub]["ceiling"] for c in per}
def diff(a, b): return {c: (a[c] - b[c]) if a[c] is not None and b[c] is not None else None for c in a}
def show(lbl, r): print(f"{lbl:38s} {r['m']:+.3f} [{r['lo']:+.3f},{r['hi']:+.3f}] bands={r['bands']} cells={r['cells']} pos={r['pos']} loo=[{r['loo_min']:+.3f},{r['loo_max']:+.3f}]")

print("integrity: cells", integ["cells"], "renders", integ["renders"], "warm", integ["warm"])
print("repeat_S n", len(integ["repeat"]), "max", max(integ["repeat"]), ">0.005", sum(v > 0.005 for v in integ["repeat"]))
print("flac_vs_float n", len(integ["flac"]), "max", max(integ["flac"]), ">0.005", sum(v > 0.005 for v in integ["flac"]))
print("non-finite values (cells x 48 x 2):", nonfin)
for sub in SUBS:
    print(f"\n=== {sub} (n points/cell {per[next(iter(per))][sub]['n']}) ===")
    C = agg(ceil(sub)); show("ceiling", C)
    for k in ("cross", "rel", "same", "worst"):
        M = agg(col(sub, "matched", k)); U = agg(col(sub, "current", k)); D = agg(diff(col(sub, "matched", k), col(sub, "current", k)))
        show(f"matched {k}", M); show(f"current {k}", U); show(f"matched-current {k}", D)
        if k == "cross":
            show("matched - C'/ref cross", agg(diff(col(sub, "matched", k), col(sub, "cref", k))))
            show("matched_gcc - matched cross", agg(diff(col(sub, "matched_gcc", k), col(sub, "matched", k))))
            gap = C["m"] - U["m"]; print(f"  gap {gap:.3f}, closed {D['m']/gap:.1%}, CI-share [{D['lo']/gap:.0%},{D['hi']/gap:.0%}]")
    print("  reliable pairs/cell median", np.median([per[c][sub]["npairs"] for c in per]))

# per band (all, cross)
print("\nper band (all, cross): matched current diff ceiling parts")
bM = agg(col("all", "matched", "cross"))["_bm"]; bU = agg(col("all", "current", "cross"))["_bm"]
bD = agg(diff(col("all", "matched", "cross"), col("all", "current", "cross")))["_bm"]; bC = agg(ceil("all"))["_bm"]
for b in sorted(bD, key=lambda b: -bD[b]):
    print(f"  {b:36s} {bM[b]:+.3f} {bU[b]:+.3f} {bD[b]:+.3f} {bC[b]:+.3f}  {[s for s in P if P[s]['band']==b]}")
x = np.array(list(bD.values())); xs = np.sort(x)[::-1]
print("diff band mean", x.mean().round(3), "median", np.median(x).round(3), "drop top2", xs[2:].mean().round(3), "drop top3", xs[3:].mean().round(3))
print("Wilcoxon band diffs p", stats.wilcoxon(x).pvalue, "sign", int((x > 0).sum()), "/", len(x))
# per amp, per class, per fold
D = diff(col("all", "matched", "cross"), col("all", "current", "cross"))
for a in ("ac20", "pr12", "sw50r"):
    show(f"diff amp {a}", agg({c: v for c, v in D.items() if c.endswith("|" + a)}))
for cl in ("clean", "crunch"):
    show(f"diff class {cl}", agg({c: v for c, v in D.items() if P[c.split('|')[0]]["gain_class"] == cl}))
for f in range(4):
    sub = {c: v for c, v in D.items() if P[c.split('|')[0]]["fold"] == f}
    vs = [v for v in sub.values() if v is not None]
    print(f"diff fold {f}: cells {len(vs)} mean {np.mean(vs):+.3f}")
pdiff = {}
for c, v in D.items():
    if v is not None: pdiff.setdefault(c.split("|")[0], []).append(v)
pd_ = {s: np.mean(v) for s, v in pdiff.items()}
print("parts positive", sum(v > 0 for v in pd_.values()), "/", len(pd_), "cells positive", sum(v > 0 for v in D.values() if v is not None))
print("most negative parts", sorted(pd_.items(), key=lambda t: t[1])[:4])
json.dump(per, open(HERE / "per_cell_1b.json", "w"))
