import math, statistics, random
from scipy import stats as SS
def agg(rows):
    """rows: (part, band, v) -> per-part mean, then per-band mean of parts. returns dict band->mean, part list"""
    bp = {}
    for p, b, v in rows:
        bp.setdefault((p, b), []).append(v)
    pm = {k: statistics.fmean(v) for k, v in bp.items()}
    bm = {}
    for (p, b), v in pm.items():
        bm.setdefault(b, []).append(v)
    return {b: statistics.fmean(v) for b, v in bm.items()}, pm
def bw(rows, boot=4000, seed=1):
    bm, pm = agg(rows)
    g = len(bm); vals = list(bm.values())
    m = statistics.fmean(vals)
    half = SS.t.ppf(0.95, g-1)*statistics.stdev(vals)/math.sqrt(g)
    lobo = [statistics.fmean([v for c, v in bm.items() if c != b]) for b in bm]
    rng = random.Random(seed); bs = []
    for _ in range(boot):
        bs.append(statistics.fmean([vals[rng.randrange(g)] for _ in range(g)]))
    bs.sort()
    return dict(mean=round(m,4), lo=round(m-half,4), hi=round(m+half,4), bands=g,
                neg=sum(v < -1e-12 for v in vals), pos=sum(v > 1e-12 for v in vals),
                lobo=[round(min(lobo),4), round(max(lobo),4)], part_w=round(statistics.fmean(pm.values()),4),
                boot=[round(bs[int(.05*boot)],4), round(bs[int(.95*boot)],4)], n=len(rows))
def fmt(d): return f"{d['mean']:+.3f} [{d['lo']:+.3f},{d['hi']:+.3f}] boot[{d['boot'][0]:+.3f},{d['boot'][1]:+.3f}] bands -{d['neg']}/+{d['pos']} of {d['bands']} lobo[{d['lobo'][0]:+.3f},{d['lobo'][1]:+.3f}] partw {d['part_w']:+.3f} n={d['n']}"
