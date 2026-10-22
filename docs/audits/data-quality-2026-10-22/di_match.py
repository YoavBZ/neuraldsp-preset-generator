"""DI-to-amp-track correspondence (zero renders, CPU).

Per track: 10-ms frames, 24 log-spaced bands 80 Hz-8 kHz, log energy. Onset strength = summed
half-wave-rectified band log-energy rise (dB, floored 50 dB below the track's loudest frame).
Per 10-s window (hop 5 s) where the DI plays: Pearson correlation of the DI's onset strength with
each candidate amp track's onset strength, best over lags -100..+100 ms; also the activity
agreement (frames within 40 dB of the track's max). A DI "follows" a track when the onset
correlation is high; a mismatch is when its own amp track scores low or another part's scores
higher.

    python di_match.py <pairs.json> <out.jsonl>
pairs: [{"key", "di": path, "own": [paths], "others": [paths]}]
"""
import json, pathlib, sys
import numpy as np
import soundfile as sf

HOP_S = 0.01
WIN_S, STEP_S = 10.0, 5.0
LAG = 10   # frames (100 ms)


def feats(path, cache={}):
    path = str(path)
    if path in cache:
        return cache[path]
    info = sf.info(path)
    sr = info.samplerate
    hop = int(round(HOP_S * sr))
    nfft = 2048 if sr <= 48000 else 4096
    f = np.fft.rfftfreq(nfft, 1 / sr)
    edges = np.geomspace(80, 8000, 25)
    idx = [np.where((f >= edges[k]) & (f < edges[k + 1]))[0] for k in range(24)]
    win = np.hanning(nfft).astype(np.float32)
    out = []
    block = hop * 3000
    for start in range(0, info.frames, block):
        x, _ = sf.read(path, start=start, frames=block + nfft, dtype="float32", always_2d=True)
        x = x.mean(1)
        if len(x) < nfft:
            break
        fr = np.lib.stride_tricks.sliding_window_view(x, nfft)[::hop][: block // hop]
        P = np.abs(np.fft.rfft(fr * win, axis=1)) ** 2
        out.append(np.stack([P[:, i].sum(1) for i in idx], 1))
    E = 10 * np.log10(np.concatenate(out) + 1e-12)
    cache.clear()
    cache[path] = E
    return E


def onset(E):
    tot = 10 * np.log10(np.sum(10 ** (E / 10), 1) + 1e-12)
    Ef = np.maximum(E, E.max() - 50)
    o = np.maximum(np.diff(Ef, axis=0, prepend=Ef[:1]), 0).sum(1)
    return o, tot


def best_corr(a, b):
    best, lag = -1.0, 0
    for L in range(-LAG, LAG + 1):
        if L >= 0:
            x, y = a[L:], b[: len(b) - L] if L else b
        else:
            x, y = a[: len(a) + L], b[-L:]
        n = min(len(x), len(y))
        x, y = x[:n], y[:n]
        if x.std() == 0 or y.std() == 0:
            continue
        c = float(np.corrcoef(x, y)[0, 1])
        if c > best:
            best, lag = c, L
    return best, lag


def main():
    pairs = json.loads(pathlib.Path(sys.argv[1]).read_text())
    out = pathlib.Path(sys.argv[2])
    done = {json.loads(l)["key"] for l in out.open()} if out.exists() else set()
    with out.open("a") as fh:
        for p in pairs:
            if p["key"] in done:
                continue
            try:
                od, td = onset(feats(p["di"]))
                tracks = {}
                for t in p["own"] + p["others"]:
                    tracks[t] = onset(feats(t))
            except Exception as e:  # noqa: BLE001
                fh.write(json.dumps({"key": p["key"], "error": str(e)}) + "\n")
                continue
            n = int(WIN_S / HOP_S)
            st = int(STEP_S / HOP_S)
            act_d = td > td.max() - 40
            wins = []
            for a in range(0, len(od) - n + 1, st):
                if act_d[a:a + n].mean() < 0.5:
                    continue
                w = {"t": round(a * HOP_S, 1), "own": {}, "others": {}}
                for t, (o, tt) in tracks.items():
                    if len(o) < a + n:
                        continue
                    c, L = best_corr(od[a:a + n], o[a:a + n])
                    act_t = tt[a:a + n] > tt.max() - 40
                    agree = float((act_t & act_d[a:a + n]).sum() / max(1, (act_t | act_d[a:a + n]).sum()))
                    w["own" if t in p["own"] else "others"][pathlib.Path(t).name] = [round(c, 3), L, round(agree, 3)]
                wins.append(w)
            fh.write(json.dumps({"key": p["key"], "di": p["di"], "windows": wins}) + "\n")
            fh.flush()
            print(p["key"], len(wins), flush=True)


if __name__ == "__main__":
    main()
