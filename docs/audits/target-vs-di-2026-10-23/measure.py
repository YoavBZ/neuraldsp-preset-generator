"""Target-vs-DI check (CPU, read-only on data). Zero renders.

For every amp part in data-review-1 sitting 1: crop halves (6 s) and whole-session 20-s windows,
the DI -> target linear transfer |H|, coherence, linear-fit residual, best-lag waveform r, and
a copy check against every DI / guitar track of the session.
"""
import json, pathlib, re, sys
import numpy as np
import soundfile as sf
import scipy.signal as ss

HOME = pathlib.Path("~/ndsp-presets").expanduser()
REPO = pathlib.Path("/Users/yoavbz/projects/neuraldsp-preset-generator")
PLAN = json.load(open(HOME / "listening/data-review-1/plan.json"))
ANS = {a["id"]: a for a in json.load(open(sys.argv[1]))["answers"]}
OUT = pathlib.Path(sys.argv[2])

CAT12 = json.load(open(REPO / "docs/validation-datasets.json"))
CAT3 = json.load(open(HOME / "references/datasets-set3/catalog.json"))
ROOT12 = HOME / "references/datasets"
ROOT3 = HOME / "references/datasets-set3"

BANDS = [(80, 200), (200, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 6000), (6000, 8000),
         (8000, 12000), (12000, 16000)]


def mono(x):
    return x.mean(axis=1) if x.ndim == 2 else x


def read(path, start=None, stop=None):
    x, sr = sf.read(str(path), start=start, stop=stop, dtype="float64", always_2d=True)
    return mono(x), sr


def best_lag(x, y, maxlag):
    """lag (positive: y later than x) and signed normalized r at |max|."""
    n = len(x) + len(y)
    nfft = 1 << (n - 1).bit_length()
    c = np.fft.irfft(np.conj(np.fft.rfft(x, nfft)) * np.fft.rfft(y, nfft), nfft)
    lags = np.r_[np.arange(0, maxlag + 1), np.arange(-maxlag, 0)]
    vals = np.r_[c[:maxlag + 1], c[-maxlag:]]
    k = int(np.argmax(np.abs(vals)))
    den = np.sqrt(np.sum(x * x) * np.sum(y * y)) + 1e-30
    return int(lags[k]), float(vals[k] / den)


def shift(x, y, lag):
    """align y to x given y is `lag` samples later."""
    if lag > 0:
        return x[:len(x) - lag], y[lag:]
    if lag < 0:
        return x[-lag:], y[:len(y) + lag]
    return x, y


def tf(x, y, sr, nper=4096):
    f, pxx = ss.welch(x, sr, nperseg=nper)
    _, pyy = ss.welch(y, sr, nperseg=nper)
    _, pxy = ss.csd(x, y, sr, nperseg=nper)
    coh = np.abs(pxy) ** 2 / (pxx * pyy + 1e-40)
    H = np.abs(pxy) / (pxx + 1e-40)
    return f, pxx, pyy, coh, H


def summarize(x, y, sr, maxlag_s=0.05):
    lag, r = best_lag(x, y, int(maxlag_s * sr))
    xa, ya = shift(x, y, lag)
    f, pxx, pyy, coh, H = tf(xa, ya, sr)
    sel = (f >= 60) & (f <= 16000)
    resid = 10 * np.log10(np.sum(pyy[sel] * (1 - coh[sel])) / (np.sum(pyy[sel]) + 1e-40) + 1e-12)
    sel2 = (f >= 100) & (f <= 5000)
    resid_lo = 10 * np.log10(np.sum(pyy[sel2] * (1 - coh[sel2])) / (np.sum(pyy[sel2]) + 1e-40) + 1e-12)
    ref = (f >= 1000) & (f < 2000)
    href = 20 * np.log10(np.median(H[ref]) + 1e-20)
    pref = 10 * np.log10(np.median(pyy[ref] / (pxx[ref] + 1e-40)) + 1e-20)
    hb, pb, cb = {}, {}, {}
    for lo, hi in BANDS:
        m = (f >= lo) & (f < hi)
        hb[f"{lo}-{hi}"] = round(20 * np.log10(np.median(H[m]) + 1e-20) - href, 1)
        pb[f"{lo}-{hi}"] = round(10 * np.log10(np.median(pyy[m] / (pxx[m] + 1e-40)) + 1e-20) - pref, 1)
        cb[f"{lo}-{hi}"] = round(float(np.median(coh[m])), 3)
    # ripple of |H| (dB) across 150 Hz-5 kHz after 1/6-oct smoothing and a log-f linear trend
    m = (f >= 150) & (f <= 5000)
    fl, hl = f[m], 20 * np.log10(H[m] + 1e-20)
    sm = np.array([np.median(hl[(fl >= fi * 2 ** (-1 / 12)) & (fl <= fi * 2 ** (1 / 12))]) for fi in fl])
    tr = np.polyval(np.polyfit(np.log2(fl), sm, 1), np.log2(fl))
    ripple = float(np.std(sm - tr))
    # spectral share above 6 kHz, target vs DI
    hi6 = f >= 6000
    share_t = 10 * np.log10(np.sum(pyy[hi6]) / np.sum(pyy) + 1e-20)
    share_d = 10 * np.log10(np.sum(pxx[hi6]) / np.sum(pxx) + 1e-20)
    return {"lag": lag, "r": round(r, 4), "resid_db": round(float(resid), 1),
            "resid_100_5k_db": round(float(resid_lo), 1),
            "H": hb, "P": pb, "coh": cb, "ripple_db": round(ripple, 2),
            "hf_drop_H": round(np.mean([hb["6000-8000"], hb["8000-12000"]]) - np.mean([hb["500-1000"], 0.0]), 1),
            "hf_drop_P": round(np.mean([pb["6000-8000"], pb["8000-12000"]]) - np.mean([pb["500-1000"], 0.0]), 1),
            "share6k_t": round(float(share_t), 1), "share6k_d": round(float(share_d), 1)}


def rms_db(x):
    return 10 * np.log10(np.mean(x * x) + 1e-20)


def session_info(slug, crop):
    rec = json.load(open(crop / "record.json"))
    if rec.get("schema") == "validation-crops-2":
        key = rec["session_key"]
        s = next(s for s in CAT3["sessions"] if s["key"] == key)
        part = next(p for p in s["parts"] if p["part"] == rec["part"])
        base = ROOT3 / s["path"]
        files = sorted(s["files"]) if isinstance(s.get("files"), (list, dict)) else None
        if files is None:
            files = sorted(str(p.relative_to(base)) for p in base.rglob("*.wav"))
        dis = [p["di"] for p in s["parts"] if p.get("di")]
    else:
        s = next(s for s in CAT12["sessions"] if s["source"] == rec["source"] and s["song"] == rec["song"])
        part = next(p for p in s["parts"] if p["part"] == rec["part"])
        base = ROOT12 / s["path"]
        files = sorted(s["files"])
        dis = [p["di"] for p in s["parts"] if p.get("di")]
    return rec, s, part, base, files, dis


def main():
    slugs = {}
    for it in PLAN["items"]:
        if it["section"] == "amp" and it["id"] in ANS:
            slugs.setdefault(it["slug"], []).append(it)
    results = {}
    for slug, its in slugs.items():
        crop = pathlib.Path(its[0]["src"]["main"][0]["path"]).parent
        rec, sess, part, base, files, dis = session_info(slug, crop)
        ref_c, sr_c = read(crop / "reference.wav")
        di_c, _ = read(crop / "di.wav")
        halves = {}
        for it in its:
            a = it["src"]["main"][0]["start_s"]
            b = a + it["src"]["main"][0]["dur_s"]
            sl = slice(int(a * sr_c), int(b * sr_c))
            h = summarize(di_c[sl], ref_c[sl], sr_c)
            h["verdict"] = ANS[it["id"]]["verdict"]
            h["note"] = ANS[it["id"]].get("note", "")
            h["id"] = it["id"]
            h["level_ref_db"] = round(rms_db(ref_c[sl]), 1)
            h["level_di_db"] = round(rms_db(di_c[sl]), 1)
            halves[it["half"]] = h
        # whole session, 20-s windows where DI and target both play
        ref_path, di_path = base / part["reference"], base / part["di"]
        info = sf.info(str(di_path))
        sr = info.samplerate
        di_all, _ = read(di_path)
        ref_all, sr2 = read(ref_path)
        assert sr2 == sr
        n = min(len(di_all), len(ref_all))
        W = 20 * sr
        lv_d = [rms_db(di_all[i:i + W]) for i in range(0, n - W + 1, W)]
        lv_r = [rms_db(ref_all[i:i + W]) for i in range(0, n - W + 1, W)]
        wins = []
        if lv_d:
            md, mr = max(lv_d), max(lv_r)
            for k, i in enumerate(range(0, n - W + 1, W)):
                if lv_d[k] > md - 20 and lv_r[k] > mr - 20:
                    s_ = summarize(di_all[i:i + W], ref_all[i:i + W], sr)
                    s_["t0"] = i / sr
                    wins.append(s_)
        def med(key, sub=None):
            v = [w[key] if sub is None else w[key][sub] for w in wins]
            return (round(float(np.median(v)), 2), round(float(np.min(v)), 2), round(float(np.max(v)), 2)) if v else None
        sess_sum = {"windows": len(wins), "r": med("r"), "resid_db": med("resid_db"), "resid_100_5k_db": med("resid_100_5k_db"),
                    "hf_drop_H": med("hf_drop_H"), "hf_drop_P": med("hf_drop_P"), "ripple_db": med("ripple_db"),
                    "H_8_12k": med("H", "8000-12000"), "H_12_16k": med("H", "12000-16000"),
                    "P_8_12k": med("P", "8000-12000"), "lag": med("lag")}
        # copy check on the crop's span in session time: target vs every DI and guitar/amp track
        t0 = rec["excerpt_start_s"]
        i0, i1 = int(t0 * sr), int((t0 + 10) * sr)
        tgt = ref_all[i0:i1]
        cand = [f for f in files if f.lower().endswith(".wav") and f != part["reference"] and
                (re.search(r"gtr|guit|di", f, re.I))]
        copy = []
        for f in cand:
            try:
                x, srx = read(base / f, i0, i1)
            except Exception as e:
                copy.append({"track": f, "error": str(e)[:80]})
                continue
            if srx != sr or len(x) < len(tgt) // 2 or rms_db(x) < -80:
                copy.append({"track": f, "silent_or_short": True, "level_db": round(rms_db(x), 1) if len(x) else None})
                continue
            m = min(len(x), len(tgt))
            s_ = summarize(x[:m], tgt[:m], sr)
            copy.append({"track": f, "is_own_di": f == part["di"], "is_di": f in dis or bool(re.search(r"DI", f)),
                         "r": s_["r"], "lag": s_["lag"], "resid_db": s_["resid_db"],
                         "hf_drop_H": s_["hf_drop_H"], "level_db": round(rms_db(x[:m]), 1)})
        copy.sort(key=lambda c: c.get("resid_db", 99))
        results[slug] = {"song": rec.get("song"), "part": rec.get("part"), "session": str(base),
                         "reference": part["reference"], "alternate": part.get("alternate", []),
                         "di": part["di"], "pairing_corr": part.get("pairing_corr"),
                         "crop_start_s": t0, "native_sr": sr, "halves": halves, "session_windows": sess_sum,
                         "copy_check": copy}
        hv = " ".join(f"{h}:{v['verdict'][:5]} r={v['r']:+.3f} res={v['resid_db']:.1f} hfH={v['hf_drop_H']:.1f} hfP={v['hf_drop_P']:.1f} rip={v['ripple_db']:.1f}"
                      for h, v in sorted(halves.items()))
        top = copy[0] if copy else {}
        print(f"{slug:50s} {hv} | sess n={sess_sum['windows']} r={sess_sum['r']} res={sess_sum['resid_db']} hfH={sess_sum['hf_drop_H']} | best other={top.get('track')} r={top.get('r')} res={top.get('resid_db')}", flush=True)
    OUT.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
