"""Crop-level DI-to-target correspondence for the label-table parts (stage F, knob ceiling, ...).
Per judge half (A 1-5.5 s, B 5.5-10 s): onset correlation of the DI with the reference (best lag
within +-100 ms), log-envelope correlation, chroma similarity, and an NNLS power split of the
reference's 200-4000 Hz envelope into DI vs backing (the backing being every other session track).
Also the same onset/chroma scores of the backing with the DI (does the backing play the DI's part?).
"""
import json, pathlib
import numpy as np
import soundfile as sf
from scipy.optimize import nnls

HOME = pathlib.Path("~/ndsp-presets").expanduser()
parts = json.loads((HOME / "learn/label-table/parts.json").read_text())
OUT = pathlib.Path(__file__).with_name("crop-match2.jsonl")
done = {json.loads(l)["slug"] for l in OUT.open()} if OUT.exists() else set()
HOP = 480  # 10 ms at 48 k
HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}


def rd(p):
    x, sr = sf.read(str(p), always_2d=True, dtype="float32")
    assert sr == 48000, sr
    return x.mean(1)


def bands(x, nf=2048):
    fr = np.lib.stride_tricks.sliding_window_view(x, nf)[::HOP] * np.hanning(nf)
    P = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(nf, 1 / 48000)
    edges = np.geomspace(80, 8000, 25)
    return np.stack([P[:, (f >= edges[k]) & (f < edges[k + 1])].sum(1) for k in range(24)], 1)


def onset(Bp):
    E = 10 * np.log10(Bp + 1e-12)
    E = np.maximum(E, E.max() - 50)
    return np.maximum(np.diff(E, axis=0, prepend=E[:1]), 0).sum(1)


def best_corr(a, b, lag=10):
    best = -1.0
    for L in range(-lag, lag + 1):
        x, y = (a[L:], b[: len(b) - L]) if L >= 0 else (a[: len(a) + L], b[-L:])
        n = min(len(x), len(y))
        if n < 20 or x[:n].std() == 0 or y[:n].std() == 0:
            continue
        best = max(best, float(np.corrcoef(x[:n], y[:n])[0, 1]))
    return best


def chroma(x, nf=8192, hop=2400):
    fr = np.lib.stride_tricks.sliding_window_view(x, nf)[::hop] * np.hanning(nf)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(nf, 1 / 48000)
    ok = (f > 70) & (f < 1500)
    pc = (np.round(12 * np.log2(f[ok] / 440)) % 12).astype(int)
    C = np.stack([S[:, ok][:, pc == k].sum(1) for k in range(12)], 1)
    return C / (C.sum(1, keepdims=True) + 1e-12), S[:, ok].sum(1)


def csim(a, b):
    (A, ea), (B, eb) = a, b
    m = min(len(A), len(B))
    A, B, ea, eb = A[:m], B[:m], ea[:m], eb[:m]
    ok = (ea > ea.max() * 1e-3) & (eb > eb.max() * 1e-3)
    if ok.sum() < 5:
        return None
    A = A[ok] - A[ok].mean(1, keepdims=True)
    B = B[ok] - B[ok].mean(1, keepdims=True)
    return float(np.mean((A * B).sum(1) / (np.linalg.norm(A, axis=1) * np.linalg.norm(B, axis=1) + 1e-12)))


with OUT.open("a") as fh:
    for slug, p in sorted(parts.items()):
        if slug in done:
            continue
        c = pathlib.Path(p["crop"])
        try:
            di, ref = rd(c / "di.wav"), rd(c / "reference.wav")
            bk = None
            for nm in ("backing_instrumental.wav", "backing.wav"):
                try:
                    bk = rd(c / nm); break
                except Exception:  # noqa: BLE001
                    pass
            if bk is None:
                bk = np.zeros_like(ref) + 1e-9 * np.random.default_rng(0).standard_normal(len(ref)).astype(np.float32)
        except Exception as e:  # noqa: BLE001
            fh.write(json.dumps({"slug": slug, "error": str(e)}) + "\n")
            continue
        fr = lambda x: 10 * np.log10(np.convolve(x.astype(np.float64) ** 2, np.ones(4800) / 4800, "valid")[::480] + 1e-20)
        gd, gr = fr(di), fr(ref)
        thr_d, thr_r = gd.max() - 40, gr.max() - 40
        row = {"slug": slug, "set": p["set"], "band": p["band"], "gain_class": p["gain_class"], "halves": {}}
        for h, (a, b) in HALVES.items():
            s = slice(int(a * 48000), int(b * 48000))
            Bd, Br, Bb = bands(di[s]), bands(ref[s]), bands(bk[s])
            od, orf, ob = onset(Bd), onset(Br), onset(Bb)
            m = (np.arange(24) >= 4) & (np.arange(24) <= 19)        # ~200-4000 Hz
            ed, er, eb = Bd[:, m].sum(1), Br[:, m].sum(1), Bb[:, m].sum(1)
            coef, _ = nnls(np.stack([ed, eb], 1), er)
            fit = np.stack([ed * coef[0], eb * coef[1]], 1)
            L = lambda v: 10 * np.log10(v + 1e-12)
            act_d = L(ed) > L(ed).max() - 40
            act_r = L(er) > L(er).max() - 40
            row["halves"][h] = {
                "onset_ref_di": round(best_corr(od, orf), 3),
                "onset_ref_backing": round(best_corr(ob, orf), 3),
                "onset_backing_di": round(best_corr(od, ob), 3),
                "logenv_ref_di": round(float(np.corrcoef(L(ed), L(er))[0, 1]), 3),
                "chroma_ref_di": csim(chroma(ref[s]), chroma(di[s])),
                "chroma_backing_di": csim(chroma(bk[s]), chroma(di[s])),
                "nnls_di_share": round(float(fit[:, 0].sum() / er.sum()), 3),
                "nnls_backing_share": round(float(fit[:, 1].sum() / er.sum()), 3),
                "di_rms_db": round(float(10 * np.log10(np.mean(di[s].astype(np.float64) ** 2) + 1e-20)), 1),
                "ref_rms_db": round(float(10 * np.log10(np.mean(ref[s].astype(np.float64) ** 2) + 1e-20)), 1),
                "di_play_share": round(float((gd[int(a * 100):int(b * 100)] > thr_d).mean()), 3),
                "ref_play_share": round(float((gr[int(a * 100):int(b * 100)] > thr_r).mean()), 3),
                "ref_only_share": round(float(((gr[int(a * 100):int(b * 100)] > thr_r) & ~(gd[int(a * 100):int(b * 100)] > thr_d)).mean()), 3),
                "di_active": round(float(act_d.mean()), 3),
                "ref_active": round(float(act_r.mean()), 3),
                "ref_active_di_silent": round(float((act_r & ~act_d).mean()), 3),
            }
        fh.write(json.dumps(row) + "\n")
        fh.flush()
print("done")
