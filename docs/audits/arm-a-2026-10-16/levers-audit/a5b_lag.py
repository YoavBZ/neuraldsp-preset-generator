from common import *
import numpy as np
from learn import rank_margin as RM
from learn import confirm_run as CR
import inspect; print(inspect.signature(RM.gcc_lag))
for s in sorted(s for s in PS if s != "telefunken-Honey-GTR"):
    p = PS[s]; c = np.load(SSO / "rebuilt" / f"{s}.npy"); stem = SS.stem(s)
    di = CR.mono(p["crop"] / "di.wav"); ref = CR.mono(p["crop"] / "reference.wav")
    n = min(len(c), len(stem))
    print(f"{s[:34]:34s} f{FOLDS[p['band']]} judge_lag {p.get('judge_lag')}  gcc(rebuild,stem) {RM.gcc_lag(c[:n], stem[:n])}  gcc(di,ref) {RM.gcc_lag(di[:min(len(di),len(ref))], ref[:min(len(di),len(ref))])}  len stem/ref {len(stem)}/{len(ref)}")
