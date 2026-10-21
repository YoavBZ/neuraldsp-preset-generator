"""Toy: per-class label prior like the project's (0.4 factory+N(0,.1) clipped, 0.2 start+N(0,.1) clipped,
0.4 uniform). If the input carries no information, the best an MDN can learn is this marginal.
Compare MAE of: per-dim median, per-dim mean, top-weight component mean of a K=4 diagonal GMM fit
(what top_error decodes), and the per-dim median of that same fitted GMM."""
import numpy as np

def em(X, K, rng, it=300):
    n, d = X.shape
    mu = X[rng.choice(n, K, replace=False)].copy(); var = np.full((K, d), X.var(0)); w = np.full(K, 1 / K)
    for _ in range(it):
        lp = np.log(w) - 0.5 * (((X[:, None] - mu) ** 2) / var + np.log(2 * np.pi * var)).sum(-1)
        lp -= lp.max(1, keepdims=True); r = np.exp(lp); r /= r.sum(1, keepdims=True)
        nk = r.sum(0) + 1e-9; w = nk / n; mu = (r.T @ X) / nk[:, None]
        var = (r.T @ X ** 2) / nk[:, None] - mu ** 2 + 1e-4
    return w, mu, var
class G:
    def __init__(s, X, K, seed):
        best = None
        for t in range(3):
            w, mu, var = em(X, K, np.random.default_rng(seed * 10 + t))
            lp = np.log(w) - 0.5 * (((X[:, None] - mu) ** 2) / var + np.log(2 * np.pi * var)).sum(-1)
            m = lp.max(1); ll = (m + np.log(np.exp(lp - m[:, None]).sum(1))).mean()
            if best is None or ll > best[0]: best = (ll, w, mu, var)
        _, s.weights_, s.means_, s.var = best
    def sample(s, n):
        rng = np.random.default_rng(1); k = rng.choice(len(s.weights_), n, p=s.weights_)
        return (s.means_[k] + rng.normal(size=(n, s.means_.shape[1])) * np.sqrt(s.var[k]),)
def GaussianMixture(K, covariance_type=None, random_state=0, n_init=3):
    class F:
        def fit(self, X): return G(X, K, random_state)
    return F()
rng = np.random.default_rng(0)
D, NF, N = 8, 12, 20000
res = []
for rep in range(20):
    S = rng.uniform(0.2, 0.8, D)
    F = np.clip(rng.normal(0.5, 0.25, (NF, D)), 0, 1)
    def draw(n):
        m = rng.choice(3, n, p=[0.4, 0.2, 0.4])
        y = rng.uniform(0, 1, (n, D))
        c = np.where((m == 0)[:, None], F[rng.integers(0, NF, n)], S)
        j = np.clip(c + rng.normal(0, 0.1, (n, D)), 0, 1)
        return np.where((m == 2)[:, None], y, j)
    tr, te = draw(5000), draw(N)
    med, mean = np.median(tr, 0), tr.mean(0)
    g = GaussianMixture(4, covariance_type="diag", random_state=rep, n_init=3).fit(tr)
    top = g.means_[g.weights_.argmax()]
    smp = g.sample(200000)[0]
    gmed = np.median(np.clip(smp, 0, 1), 0)
    mae = lambda p: np.abs(te - p).mean()
    res.append([mae(med), mae(mean), mae(top), mae(gmed), g.weights_.max()])
r = np.array(res)
print("MAE median %.4f  mean %.4f  topmean %.4f  gmm-median %.4f  (top weight %.2f)" % tuple(r.mean(0)))
print("top - median: mean %.4f  min %.4f  max %.4f" % ((r[:,2]-r[:,0]).mean(), (r[:,2]-r[:,0]).min(), (r[:,2]-r[:,0]).max()))
# informative-but-noisy model: prediction = theta + noise, blend with median
for s in (0.1, 0.2, 0.3):
    p = np.clip(te + rng.normal(0, s, te.shape), 0, 1)
    best = min((np.abs(te - (w*p + (1-w)*med)).mean(), w) for w in np.linspace(0, 1, 21))
    print("noise sd %.1f: model MAE %.4f, median %.4f, best blend %.4f at w=%.2f" % (s, np.abs(te-p).mean(), np.abs(te-med).mean(), *best))
