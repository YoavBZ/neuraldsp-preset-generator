"""14 bands, corners and simple effects by Σ source subset; plus independent corner checks."""
import json, math, pathlib, collections, sys
import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).parent
ROOT = pathlib.Path.home() / "ndsp-presets/learn/local-objective"
P = json.load(open(HERE / "parts.json"))
SIG = json.load(open(ROOT / "sigma.json"))["cells"]
fold = int(sys.argv[1]) if len(sys.argv) > 1 else None

def sp(o, t):
    pr = [(a, b) for a, b in zip(o, t) if math.isfinite(a) and math.isfinite(b) and b > 0]
    if len(pr) < 3: return None
    a, b = zip(*pr)
    if len(set(a)) < 2 or len(set(b)) < 2: return None
    return float(stats.spearmanr(a, b).correlation)

def m(x):
    x = [v for v in x if v is not None]; return sum(x) / len(x) if x else None

def agg(cv):
    pm = collections.defaultdict(list)
    for (s, a), v in cv.items():
        if v is not None: pm[s].append(v)
    pm = {s: np.mean(v) for s, v in pm.items()}
    bm = collections.defaultdict(list)
    for s, v in pm.items(): bm[P[s]["band"]].append(v)
    x = np.array([np.mean(v) for v in bm.values()])
    h = stats.t.ppf(0.95, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x))
    return f"{x.mean():+.3f} [{x.mean()-h:+.3f}, {x.mean()+h:+.3f}] pw {np.mean(list(pm.values())):+.3f} n={len(x)}b"

data = {}
dev = collections.defaultdict(list)
for c, pts in SIG.items():
    slug, amp = c.split("|")
    jc = json.load(open(ROOT / "scores/cprime" / slug / f"{amp}.json"))["scores"]
    jm = json.load(open(ROOT / "scores/measure" / slug / f"{amp}.json"))["scores"]
    for i, p in enumerate(pts):  # independent corner checks against Σ's stored values
        for h, v in (p.get("true_stored") or {}).items():
            dev["true_vs_KS"].append(abs(math.log(jm[i]["measure|reference|native|own"][h] / v)) if math.isfinite(v) else (0 if not math.isfinite(jm[i]["measure|reference|native|own"][h]) else 9))
        for what in ("obj_stored", "obj_2b"):
            for h, v in (p.get(what) or {}).items():
                o = jc[i]["cprime|stem|native|own"][h]
                dev[what].append(abs(math.log(o / v)) if math.isfinite(v) and math.isfinite(o) else (0 if not math.isfinite(v) and not math.isfinite(o) else 9))
    if fold is None or P[slug]["fold"] == fold:
        data[(slug, amp)] = (pts, jc, jm)
for k, v in dev.items():
    print("corner", k, "n", len(v), "median", f"{np.median(v):.2e}", "max", f"{max(v):.2e}", ">0.005:", sum(x > 0.005 for x in v))

CFG = {"current": ("cprime", "cprime|stem|native|own"), "decisive": ("measure", "measure|stem|native|own"),
       "C'/ref": ("cprime", "cprime|reference|native|own")}
TRUE = "measure|reference|native|own"
for name, srcs in (("all", {"S", "nbr", "ks", "armA"}), ("S+nbr", {"S", "nbr"}), ("ks", {"ks"}), ("armA", {"armA"}),
                   ("S+nbr+ks", {"S", "nbr", "ks"}), ("ks+armA", {"ks", "armA"})):
    cross = {k: {} for k in CFG}; ceil = {}
    for cell, (pts, jc, jm) in data.items():
        idx = [i for i, p in enumerate(pts) if p["source"] in srcs]
        T = {h: [jm[i][TRUE][h] for i in idx] for h in "AB"}
        ceil[cell] = sp(T["A"], T["B"])
        for k, (d, cfg) in CFG.items():
            src = jc if d == "cprime" else jm
            O = {h: [src[i][cfg][h] for i in idx] for h in "AB"}
            cross[k][cell] = m([sp(O[h], T["B" if h == "A" else "A"]) for h in "AB"])
    print(f"\n== {name} (fold {fold}) n/cell ~{len(idx)}")
    print("  ceiling ", agg(ceil))
    for k in CFG: print(f"  {k:9s}", agg(cross[k]))
    dif = lambda a, b: {c: (a[c] - b[c]) if a[c] is not None and b[c] is not None else None for c in a}
    print("  DI alone ", agg(dif(cross["decisive"], cross["current"])))
    print("  ref alone", agg(dif(cross["C'/ref"], cross["current"])))
    print("  both     ", agg(dif(ceil, cross["current"])))
    inter = {c: (ceil[c] - cross["decisive"][c]) - (cross["C'/ref"][c] - cross["current"][c]) for c in ceil}
    print("  DIxref   ", agg(inter))
    # additive-error model: rho/ceil = 1/sqrt(1+e)
    def e(x, c0): r = x / c0; return 1 / r**2 - 1 if r > 0 else float("inf")
    bm = lambda d: np.mean([np.mean([np.mean([d[(s, a)] for (s, a) in d if s == s2]) for s2 in {s for s in P if P[s]["band"] == b and any(k[0] == s for k in d)}]) for b in {P[s]["band"] for s, _ in d}])
    c0, cur, dec, cre = bm(ceil), bm(cross["current"]), bm(cross["decisive"]), bm(cross["C'/ref"])
    print(f"  additive-error check: e(cur)={e(cur,c0):.2f} vs e(dec)+e(C'ref)={e(dec,c0)+e(cre,c0):.2f}  [e(dec)={e(dec,c0):.2f}, e(C'ref)={e(cre,c0):.2f}]")
