"""Recovery check: inject known bleed (a session track, delayed 3 ms and low-passed) into the amp
track of a no-bleed Cambridge part at a set level, then run the v4 estimator."""
import json
import pathlib
import sys

import numpy as np
from scipy import signal

sys.argv = sys.argv[:1] + sys.argv[1:]
import importlib.util
spec = importlib.util.spec_from_file_location("b4", pathlib.Path(__file__).resolve().parent / "bleed4.py")
b4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b4)

slug, track, level = sys.argv[1], sys.argv[2], float(sys.argv[3])
d = json.load(open(b4.REPO / "docs/label-table-parts.json"))["parts"]
Orig = b4.Part


class Inj(Orig):
    def __init__(self, s, crop):
        super().__init__(s, crop)
        names = [g[0] for g in self.groups]
        n = [x for x in names if track in x][0]
        a = signal.resample_poly(b4.io.load(self.sdir / n).mono().astype(np.float32), 1, 2).astype(np.float32)
        a = np.pad(a, (0, max(0, self.length - len(a))))[:self.length]
        a = b4.shift(a, 72)[self.c0:self.c1]
        bb, aa = signal.butter(2, 4000 / (b4.SR / 2))
        a = signal.lfilter(bb, aa, a).astype(np.float32)
        m = np.isin(self.labels, ["A", "B"])
        idx = np.concatenate([np.arange(s0, s0 + b4.NFFT) for s0 in self.starts[m]])
        ey = np.mean(self.y[idx] ** 2)
        ea = np.mean(a[idx] ** 2)
        g = np.sqrt(ey * 10 ** (level / 10) / ea)
        self.y = self.y + g * a
        self.injected = (n, level)


b4.Part = Inj
r = b4.analyse(slug, pathlib.Path(d[slug]["crop"]), nnull=1)
out = {h: (v["clean"]["gain"], v["clean"]["gain_null_mean"], v["clean"]["bleed_db"], v["clean"]["top"][:1]) for h, v in r["halves"].items()}
print(slug, track, level, out, flush=True)
