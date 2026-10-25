"""Backing composition per section (zero renders): power share of each backing class in the
10-s window, and the chroma similarity of every other guitar track to the part's DI (same riff).
Usage: python backing_comp.py <sections.json> <out.jsonl>   (sections: [[id, split, band, n], ...])
"""
import hashlib, json, pathlib, re, sys
import numpy as np
import soundfile as sf

HOME = pathlib.Path("~/ndsp-presets").expanduser()
B = HOME / "learn/pretrain-set/backings"
INV = {r["id"]: r for r in json.loads((HOME / "learn/clean-di/inventory.json").read_text())["dis"]}
LEAK = json.loads((HOME / "learn/pretrain-set/leakage.json").read_text())
SR = 22050
SEC = 10.0


def cls(t):
    n = t.lower()
    if re.search(r"vox|vocal|voc ", n):
        return "vocals"
    if re.search(r"acous|acgtr|ac gtr|acgt", n):
        return "acgtr"
    if re.search(r"pre ?rec", n):
        return "prerec"
    if re.search(r"bass", n):
        return "bass"
    if re.search(r"gtr|guitar|elec", n):
        return "egtr"
    if re.search(r"key|synth|piano|leslie|moog|yamaha|string|choir|organ|rhodes|wurl", n):
        return "keys"
    if re.search(r"kick|snare|tom|hat|ride|overhead|room|crash|cymb|drum|perc|clap|shak|tamb|crotch|oh|squash", n):
        return "drums"
    return "other"


def load(path, start):
    info = sf.info(str(path))
    a = int(start * info.samplerate)
    n = int(SEC * info.samplerate)
    x, sr = sf.read(str(path), start=a, frames=n, dtype="float32", always_2d=True)
    x = x.mean(1)
    if sr != SR:
        k = sr // SR if sr % SR == 0 else None
        if k:
            x = x[: len(x) // k * k].reshape(-1, k).mean(1)
        else:
            idx = np.arange(0, len(x), sr / SR).astype(int)
            x = x[idx[idx < len(x)]]
    return x


def chroma(x):
    n_fft, hop = 4096, 1024
    if len(x) < n_fft:
        return None
    fr = np.lib.stride_tricks.sliding_window_view(x, n_fft)[::hop] * np.hanning(n_fft)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(n_fft, 1 / SR)
    ok = (f > 80) & (f < 2000)
    pc = (np.round(12 * np.log2(f[ok] / 440.0)) % 12).astype(int)
    C = np.zeros((S.shape[0], 12))
    for k in range(12):
        C[:, k] = S[:, ok][:, pc == k].sum(1)
    e = C.sum(1)
    C = C / (e[:, None] + 1e-12)
    return C, e


def sim(ca, cb):
    """Frame-wise chroma cosine over frames where both play, averaged; and that frame share."""
    (A, ea), (Bm, eb) = ca, cb
    n = min(len(A), len(Bm))
    A, Bm, ea, eb = A[:n], Bm[:n], ea[:n], eb[:n]
    both = (ea > ea.max() * 1e-3) & (eb > eb.max() * 1e-3)
    if both.sum() < 10:
        return None, float(both.mean())
    a = A[both] - A[both].mean(1, keepdims=True)
    b = Bm[both] - Bm[both].mean(1, keepdims=True)
    c = (a * b).sum(1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1) + 1e-12)
    return float(np.mean(c)), float(both.mean())


secs = json.loads(pathlib.Path(sys.argv[1]).read_text())["sections"]
out = pathlib.Path(sys.argv[2])
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as fh:
    for sid, split, band, n in secs:
        if sid in done:
            continue
        di, start = sid.rsplit("@", 1)
        start = float(start)
        rec = INV[di]
        sess = pathlib.Path(rec["session_dir"])
        meta = json.loads((B / (hashlib.sha1(sid.encode()).hexdigest()[:16] + ".json")).read_text())
        tracks = meta["tracks"]["n"]
        d = load(rec["path"], start)
        cd = chroma(d)
        pw, per = {}, {}
        for t in tracks:
            x = load(sess / t, start)
            p = float(np.mean(x ** 2)) if len(x) else 0.0
            c = cls(t)
            pw[c] = pw.get(c, 0.0) + p
            if c in ("egtr", "acgtr", "prerec", "keys"):
                s, both = sim(cd, chroma(x)) if (cd is not None and p > 0) else (None, 0.0)
                per[t] = {"cls": c, "db": round(10 * np.log10(p + 1e-20), 2), "chroma": None if s is None else round(s, 3),
                          "both": round(both, 3)}
        tot = sum(pw.values()) or 1e-20
        row = {"id": sid, "split": split, "band": band, "n_examples": n,
               "share": {k: round(v / tot, 4) for k, v in pw.items()},
               "backing_db": round(10 * np.log10(tot), 2), "di_db": round(10 * np.log10(float(np.mean(d ** 2)) + 1e-20), 2),
               "tracks": per, "leak_dropped": LEAK.get(di, {}).get("dropped", [])}
        fh.write(json.dumps(row) + "\n")
        fh.flush()
print("done")
