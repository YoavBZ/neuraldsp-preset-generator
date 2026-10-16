from common import *
from learn import di_fine_structure as DF
from learn import train as TR
f3 = sorted(s for s in PS if s != "telefunken-Honey-GTR" and FOLDS[PS[s]["band"]] == 3)
print("fold-3 parts", [(s, PS[s]["band"]) for s in f3])
fold_of, band_of = TR.k3_folds()
print("k3 fold of these bands:", {PS[s]["band"]: fold_of.get(PS[s]["band"]) for s in f3})
caches = [DF.MODELS / c for c in DF.CACHES]
allb = set()
for c in caches:
    for m in J(c / "meta.json"): allb.add(m["band"])
pool = DF.train_pool_bands(3, caches)
for s in f3:
    b = PS[s]["band"]
    near = [x for x in allb if b.lower().split()[0] in x.lower() or x.lower() in b.lower()]
    print(s, "band in pool:", b in pool, "| similar names in caches:", near)
# also: any part's own stem/song in caches by slug words?
print("pool size", len(pool), "all cache bands", len(allb))
# C' fold 3 training config?
import pathlib
for p in sorted((DF.MODELS / "models-cprime-f3").iterdir()): print(p)
