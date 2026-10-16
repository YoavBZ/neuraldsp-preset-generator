from common import *
import numpy as np
from learn import rank_margin as RM
import inspect; print(inspect.getsource(RM.gcc_lag)[:900])
f3 = sorted(s for s in PS if s != "telefunken-Honey-GTR" and FOLDS[PS[s]["band"]] == 3)
for s in f3:
    c = np.load(SSO / "rebuilt" / f"{s}.npy"); stem = SS.stem(s)
    out = [s[:22], "C'vsStem", int(RM.gcc_lag(c, stem[:len(c)]))]
    for n in ("1z", "1a", "1b"):
        y = np.load(LV / "rebuilt" / n / f"{s}.npy")
        out += [n, int(RM.gcc_lag(y, c)), round(float(np.corrcoef(y[:len(c)], c[:len(y)])[0, 1]), 3)]
    print(*out)
