"""Independent recomputation of experiment 1's headline from scores/ (no repo code)."""
import json, math, pathlib, itertools, sys
import numpy as np
from scipy import stats

ROOT = pathlib.Path.home() / "ndsp-presets/learn/local-objective"
HERE = pathlib.Path(__file__).parent
P = json.load(open(HERE / "parts.json"))
SIG = json.load(open(ROOT / "sigma.json"))

def rank(x):
    return stats.rankdata(x)  # average ranks

def sp(o, t):
    pr = [(a, b) for a, b in zip(o, t) if math.isfinite(a) and math.isfinite(b) and b > 0]
    if len(pr) < 3: return None
    a, b = zip(*pr)
    if len(set(a)) < 2 or len(set(b)) < 2: return None
    ra, rb = rank(a), rank(b)
    return float(np.corrcoef(ra, rb)[0, 1])

def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None

def rel_pairs(T):
    n = len(T["A"])
    ok = [i for i in range(n) if all(math.isfinite(T[h][i]) and T[h][i] > 0 for h in "AB")]
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
            if not (math.isfinite(a) and math.isfinite(b)): continue
            n += 1
            d = np.sign(a - b)
            c += 1 if d == s else (0.5 if d == 0 else 0)
        if n: accs.append(c / n)
    return mean(accs)

cells = sorted(tuple(c.split("|")) for c in SIG["cells"])
print("cells in sigma:", len(cells), "parts:", len({c[0] for c in cells}), "settings:", sum(len(v) for v in SIG["cells"].values()))
per = {}   # cell -> cfg -> dict
sig_hashes = set(); gcc = {}
for slug, amp in cells:
    sc = {}
    for d in ("cprime", "measure"):
        f = ROOT / "scores" / d / slug / f"{amp}.json"
        j = json.load(open(f)); sig_hashes.add(j["sigma"])
        assert len(j["scores"]) == 48 == len(SIG["cells"][f"{slug}|{amp}"])
        if d == "cprime": gcc[slug] = j["gcc_rebuild_vs_stem"]
        for cfg in j["scores"][0]:
            sc[cfg] = {h: [s[cfg][h] for s in j["scores"]] for h in "AB"}
    T = sc["measure|reference|native|own"]
    pairs = rel_pairs(T)
    per[(slug, amp)] = {"_ceiling": {"cross": sp(T["A"], T["B"])}, "_npairs": len(pairs)}
    for cfg, O in sc.items():
        per[(slug, amp)][cfg] = {
            "same": mean([sp(O[h], T[h]) for h in "AB"]),
            "cross": mean([sp(O[h], T["B" if h == "A" else "A"]) for h in "AB"]),
            "rel": rel_acc(O, pairs)}
print("sigma hashes in score files:", sig_hashes)

def agg(vals, fold=None, wider=False):
    """vals: {cell: v}. part means over amps -> band means -> mean; 90% t on bands."""
    pm = {}
    for (s, a), v in vals.items():
        if v is None: continue
        if fold is not None and P[s]["fold"] != fold: continue
        pm.setdefault(s, []).append(v)
    pm = {s: np.mean(v) for s, v in pm.items()}
    bm = {}
    for s, v in pm.items(): bm.setdefault(P[s]["band"], []).append(v)
    bm = {b: np.mean(v) for b, v in bm.items()}
    x = np.array(list(bm.values())); g = len(x); m = x.mean()
    h = stats.t.ppf(0.95, g - 1) * x.std(ddof=1) / math.sqrt(g)
    lo, hi = m - h, m + h
    pv = np.array(list(pm.values()))
    ph = stats.t.ppf(0.95, len(pv) - 1) * pv.std(ddof=1) / math.sqrt(len(pv))
    out = dict(mean=round(m, 3), lo=round(lo, 3), hi=round(hi, 3), bands=g, parts=len(pm),
               cells=sum(1 for (s, a), v in vals.items() if v is not None and (fold is None or P[s]["fold"] == fold)),
               part_mean=round(pv.mean(), 3), part_lo=round(pv.mean() - ph, 3), part_hi=round(pv.mean() + ph, 3),
               band_pos=int((x > 0).sum()))
    if wider and 2 * ph > 2 * h:
        out["wide_lo"], out["wide_hi"] = round(pv.mean() - ph, 3), round(pv.mean() + ph, 3)
    return out

def col(cfg, k):
    if cfg == "ceiling": return {c: per[c]["_ceiling"]["cross"] for c in per}
    return {c: per[c][cfg][k] for c in per}

def diff(a, b):
    return {c: (a[c] - b[c]) if a[c] is not None and b[c] is not None else None for c in a}

CUR = "cprime|stem|native|own"; TRUE = "measure|reference|native|own"
DEC = "measure|stem|native|own"; CREF = "cprime|reference|native|own"
fold = int(sys.argv[1]) if len(sys.argv) > 1 else None
print("\n=== fold", fold if fold is not None else "all", "===")
print("ceiling cross:", agg(col("ceiling", None), fold, wider=fold is not None))
print("check TRUE cross == ceiling:", agg(col(TRUE, "cross"), fold)["mean"])
for name, cfg in (("current", CUR), ("decisive", DEC), ("C'/ref", CREF), ("truth", TRUE),
                  ("C'/stem/native/record", "cprime|stem|native|record"), ("meas/stem/native/record", "measure|stem|native|record"),
                  ("C'/ref/native/record", "cprime|reference|native|record"), ("meas/ref/native/record", "measure|reference|native|record")):
    for k in ("cross", "same", "rel"):
        print(f"{name:26s} {k:5s}", agg(col(cfg, k), fold, wider=fold is not None))

print("\n-- simple effects from current (paired) --")
for name, cfg in (("DI alone (decisive-current)", DEC), ("reference alone (C'ref-current)", CREF), ("both (truth-current)", TRUE),
                  ("mask record", "cprime|stem|native|record"), ("lag other", "cprime|stem|other|own"),
                  ("lag zero", "cprime|stem|zero|own"), ("lag gcc", "cprime|stem|gcc|own")):
    for k in ("cross", "rel", "same"):
        print(f"{name:34s} {k:5s}", agg(diff(col(cfg, k), col(CUR, k)), fold, wider=fold is not None))
print("decisive - C'ref cross", agg(diff(col(DEC, "cross"), col(CREF, "cross")), fold))

print("\n-- main effects at native lag (mean over the other factors) --")
def me(k, pos, hi, lo, exclude_true=False):
    out = {}
    for c in per:
        ds = []
        for d in ("cprime", "measure"):
            for r in ("stem", "reference"):
                for m in ("own", "record"):
                    cfg = [d, r, "native", m]
                    if cfg[pos] != hi: continue
                    b = list(cfg); b[pos] = lo
                    a_, b_ = "|".join(cfg), "|".join(b)
                    if exclude_true and TRUE in (a_, b_): continue
                    va, vb = per[c][a_][k], per[c][b_][k]
                    if va is not None and vb is not None: ds.append(va - vb)
        out[c] = mean(ds)
    return out
def inter(k, mask_levels=("own", "record")):
    out = {}
    for c in per:
        ds = []
        for m in mask_levels:
            q = [per[c][f"{d}|{r}|native|{m}"][k] for d, r in (("measure", "reference"), ("measure", "stem"), ("cprime", "reference"), ("cprime", "stem"))]
            if None not in q: ds.append((q[0] - q[1]) - (q[2] - q[3]))
        out[c] = mean(ds)
    return out
for k in ("cross", "rel"):
    print(k, "DI       ", agg(me(k, 0, "measure", "cprime"), fold))
    print(k, "reference", agg(me(k, 1, "reference", "stem"), fold))
    print(k, "mask     ", agg(me(k, 3, "record", "own"), fold))
    print(k, "DIxref   ", agg(inter(k), fold))
    print(k, "DIxref own-mask only", agg(inter(k, ("own",)), fold))
    print(k, "DI excl truth corner       ", agg(me(k, 0, "measure", "cprime", True), fold))
    print(k, "reference excl truth corner", agg(me(k, 1, "reference", "stem", True), fold))

npairs = [per[c]["_npairs"] for c in per]
print("\nreliable pairs per cell: min", min(npairs), "median", np.median(npairs), "max", max(npairs))
print("None counts per cfg (cross):", {cfg: sum(per[c][cfg]["cross"] is None for c in per) for cfg in (CUR, DEC, CREF, TRUE)})
print("ceiling None:", sum(per[c]["_ceiling"]["cross"] is None for c in per))
print("gcc rebuild vs stem per part:", gcc)
json.dump({f"{c[0]}|{c[1]}": {k: v for k, v in d.items()} for c, d in per.items()}, open(HERE / f"per_cell_{fold}.json", "w"))
