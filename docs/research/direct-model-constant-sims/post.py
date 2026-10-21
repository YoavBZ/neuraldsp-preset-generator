"""Exact-ish Bayes posterior under the project-like prior, with a noisy Gaussian 'cue' x = theta + e.
Compare decoders: posterior median (L1-optimal), posterior mean, and 'top component' = posterior mean
within the most probable prior component (factory preset i / start / wide), the analogue of decoding
an MDN by its top-weight component. Also the prior median (the constant)."""
import numpy as np
rng = np.random.default_rng(0)
D, NF = 8, 12
S = rng.uniform(0.2, 0.8, D); F = np.clip(rng.normal(0.5, 0.25, (NF, D)), 0, 1)
def draw(n):
    m = rng.choice(3, n, p=[0.4, 0.2, 0.4]); fi = rng.integers(0, NF, n)
    c = np.where((m == 0)[:, None], F[fi], S)
    j = np.clip(c + rng.normal(0, 0.1, (n, D)), 0, 1)
    y = np.where((m == 2)[:, None], rng.uniform(0, 1, (n, D)), j)
    comp = np.where(m == 0, fi, np.where(m == 1, NF, NF + 1))
    return y, comp
P, Pc = draw(40000)
med = np.median(P, 0)
def wmedian(v, w):
    o = np.argsort(v); c = np.cumsum(w[o]); return v[o][np.searchsorted(c, 0.5 * c[-1])]
for s in (0.1, 0.2, 0.4, 0.8, 1e9):
    T, _ = draw(600); out = np.zeros(4)
    for t in T:
        x = t + rng.normal(0, s if s < 1e8 else 0, D)
        lw = -0.5 * ((P - x) ** 2).sum(1) / s ** 2; w = np.exp(lw - lw.max())
        pm = np.array([wmedian(P[:, d], w) for d in range(D)])
        mean = (w[:, None] * P).sum(0) / w.sum()
        cw = np.bincount(Pc, w, NF + 2); k = cw.argmax(); sel = Pc == k
        top = (w[sel, None] * P[sel]).sum(0) / w[sel].sum()
        out += [np.abs(t - pm).mean(), np.abs(t - mean).mean(), np.abs(t - top).mean(), np.abs(t - med).mean()]
    out /= len(T)
    print("cue sd %-6s post-median %.4f  post-mean %.4f  top-comp %.4f  constant %.4f   top-median %+.4f" % (("inf" if s > 1e8 else s), *out, out[2] - out[0]))
