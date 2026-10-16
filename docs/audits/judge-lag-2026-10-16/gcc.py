import sys, json, glob, os
sys.path.insert(0, '/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT')
import numpy as np, soundfile as sf
from learn import knob_ceiling as K
from learn import confirm_run as CR
SR = 48000

def xc(a, b, lo=80, hi=2000, span=2400, phat=False):
    """lags L (a[t] ~ b[t-L]) in [-span, span] -> normalised |corr|"""
    n = min(len(a), len(b)); x = a[:n] - a[:n].mean(); y = b[:n] - b[:n].mean()
    size = 1 << int(np.ceil(np.log2(2 * n)))
    f = np.fft.rfftfreq(size, 1 / SR); keep = (f >= lo) & (f <= hi)
    C = np.fft.rfft(x, size) * np.conj(np.fft.rfft(y, size)) * keep
    if phat:
        C = C / np.maximum(np.abs(C), 1e-20)
    c = np.fft.irfft(C, size)
    if not phat:
        c = c / (np.linalg.norm(x) * np.linalg.norm(y))
    lags = np.arange(-span, span + 1)
    return lags, np.abs(c[lags % size])

def peaks(lags, v, k=3, sep=24):
    out = []; v = v.copy()
    for _ in range(k):
        i = int(np.argmax(v)); out.append((int(lags[i]), round(float(v[i]), 3)))
        v[max(0, i - sep): i + sep] = 0
    return out

ps = K.parts()
slugs = sys.argv[1:]
for s in slugs:
    p = ps[s]
    ref = CR.mono(p['crop'] / 'reference.wav'); raw = CR.mono(p['crop'] / 'di.wav')
    meas = K.measure_di(p)
    print(f"== {s}  stored judge_lag={p['judge_lag']} (+52={p['judge_lag']+52})")
    for name, a, b in (("ref~rawDI", ref, raw), ("ref~measDI", ref, meas), ("measDI~rawDI", meas, raw)):
        for ph in (False, True):
            l, v = xc(a, b, phat=ph)
            print(f"  {name:14s} {'phat' if ph else 'bl  '} top: {peaks(l, v)}")
    for f in sorted(glob.glob(str(K.OUT / 'cells' / s / '*' / 'K_S-A.flac')))[:3]:
        y, sr = sf.read(f); y = y.mean(1) if y.ndim == 2 else y
        amp = f.split('/')[-2]
        for name, a, b in ((f"ref~render[{amp}]", ref, y), (f"render~measDI[{amp}]", y, meas)):
            l, v = xc(a, b)
            print(f"  {name:22s} bl top: {peaks(l, v)}")
