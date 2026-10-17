"""Fold 3: 2b's stored local set against this experiment's Σ, by source subset."""
import json, math, pathlib, glob, collections
import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).parent
ROOT = pathlib.Path.home() / "ndsp-presets/learn/local-objective"
P = json.load(open(HERE / "parts.json"))
SIG = json.load(open(ROOT / "sigma.json"))["cells"]

def sp(o, t):
    pr = [(a, b) for a, b in zip(o, t) if math.isfinite(a) and math.isfinite(b) and b > 0]
    if len(pr) < 3: return None
    a, b = zip(*pr)
    if len(set(a)) < 2 or len(set(b)) < 2: return None
    return float(stats.spearmanr(a, b).correlation)

def m(x):
    x = [v for v in x if v is not None]; return sum(x) / len(x) if x else None

def agg(cellvals):
    pm = collections.defaultdict(list)
    for (s, a), v in cellvals.items():
        if v is not None: pm[s].append(v)
    pm = {s: np.mean(v) for s, v in pm.items()}
    bm = collections.defaultdict(list)
    for s, v in pm.items(): bm[P[s]["band"]].append(v)
    bm = {b: round(float(np.mean(v)), 3) for b, v in bm.items()}
    x = np.array(list(bm.values()))
    h = stats.t.ppf(0.95, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x))
    return round(float(x.mean()), 3), round(float(x.mean() - h), 3), round(float(x.mean() + h), 3), bm, round(float(np.mean(list(pm.values()))), 3)

# 2b
f2b = {}
for f in glob.glob(str(pathlib.Path.home() / "ndsp-presets/learn/song-settings/levers/local/C'/*.json")):
    name = pathlib.Path(f).stem
    slug, amp = name.rsplit("-", 1)
    pts = json.load(open(f))["points"]
    O = {h: [p["obj"][h] for p in pts] for h in "AB"}; T = {h: [p["true"][h] for p in pts] for h in "AB"}
    f2b[(slug, amp)] = (O, T)
print("2b cells", len(f2b), "points/cell", {len(v[0]["A"]) for v in f2b.values()})
same = {c: m([sp(O[h], T[h]) for h in "AB"]) for c, (O, T) in f2b.items()}
cross = {c: m([sp(O[h], T["B" if h == "A" else "A"]) for h in "AB"]) for c, (O, T) in f2b.items()}
ceil = {c: sp(T["A"], T["B"]) for c, (O, T) in f2b.items()}
print("2b same-half", agg(same)); print("2b cross-half", agg(cross)); print("2b ceiling", agg(ceil))
# true-d spread in 2b vs here
def sd_log(T): return m([float(np.std(np.log([v for v in T[h] if math.isfinite(v) and v > 0]))) for h in "AB"])
print("2b SD log true d (median over cells)", round(float(np.median([sd_log(T) for O, T in f2b.values()])), 3))

# this experiment, fold 3, by source
here = {}
for c, pts in SIG.items():
    slug, amp = c.split("|")
    if P[slug]["fold"] != 3: continue
    jc = json.load(open(ROOT / "scores/cprime" / slug / f"{amp}.json"))["scores"]
    jm = json.load(open(ROOT / "scores/measure" / slug / f"{amp}.json"))["scores"]
    here[(slug, amp)] = (pts, jc, jm)

def sub(srcs, cfg_o="cprime|stem|native|own", true_cfg="measure|reference|native|own", di_o="cprime"):
    s_, c_, ce = {}, {}, {}
    for cell, (pts, jc, jm) in here.items():
        idx = [i for i, p in enumerate(pts) if p["source"] in srcs]
        src = jc if di_o == "cprime" else jm
        O = {h: [src[i][cfg_o][h] for i in idx] for h in "AB"}
        T = {h: [jm[i][true_cfg][h] for i in idx] for h in "AB"}
        s_[cell] = m([sp(O[h], T[h]) for h in "AB"])
        c_[cell] = m([sp(O[h], T["B" if h == "A" else "A"]) for h in "AB"])
        ce[cell] = sp(T["A"], T["B"])
    return s_, c_, ce, {cell: sd_log({h: [jm[i][true_cfg][h] for i, p in enumerate(pts) if p["source"] in srcs] for h in "AB"}) for cell, (pts, jc, jm) in here.items()}

for name, srcs in (("all", {"S", "nbr", "ks", "armA"}), ("ks only", {"ks"}), ("S+nbr", {"S", "nbr"}), ("armA", {"armA"}), ("ks+armA", {"ks", "armA"})):
    s_, c_, ce, sd = sub(srcs)
    print(f"\nhere fold3 {name}: same", agg(s_)); print("   cross", agg(c_)); print("   ceiling", agg(ce)[:3], "median SD log d", round(float(np.median(list(sd.values()))), 3))
    if name in ("all", "ks only"):
        s2, c2, _, _ = sub(srcs, "measure|stem|native|own", di_o="measure")
        print("   decisive cross", agg(c2)[:4])
        s3, c3, _, _ = sub(srcs, "cprime|reference|native|own")
        print("   C'/ref cross", agg(c3)[:4])

# per-cell comparison on the 2b cells
print("\nper cell: 2b same-half vs here (ks-only, all) same-half")
s_ks, _, _, _ = sub({"ks"}); s_all, _, _, _ = sub({"S", "nbr", "ks", "armA"})
for c in sorted(f2b):
    print(c, P[c[0]]["band"], round(same[c], 3) if same[c] is not None else None, round(s_ks[c], 3) if s_ks[c] is not None else None, round(s_all[c], 3))
