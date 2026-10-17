import sys, glob
sys.path.insert(0, '/private/tmp/claude-501/-Users-yoavbz-projects-neuraldsp-preset-generator/67cfc004-f421-4d92-9cce-0e70317476ec/scratchpad/lag-audit')
import numpy as np, soundfile as sf
from gcc import xc, peaks
H='/Users/yoavbz/ndsp-presets/references/'
for ref, di in [(H+'datasets/cambridge/AdamBuckley_DragMeDown_Full/32_ElecGtr4.wav', H+'datasets/cambridge/AdamBuckley_DragMeDown_Full/33_ElecGtr4DI.wav'),
                (H+"datasets/cambridge/EatTheFeeder_TodaysTheDay_Full/42_ElecGtr10Amp.wav", H+"datasets/cambridge/EatTheFeeder_TodaysTheDay_Full/43_ElecGtr10DI.wav"),
                (glob.glob(H+'datasets-set3/**/18_ElecGtr3Amp.wav', recursive=True)[0], glob.glob(H+'datasets-set3/**/17_ElecGtr3DI.wav', recursive=True)[0])]:
    a, sr = sf.read(ref, always_2d=True); b, _ = sf.read(di, always_2d=True); a = a.mean(1); b = b.mean(1)
    n = min(len(a), len(b)); W = 10 * sr
    rms = [np.sqrt(np.mean(b[i:i+W]**2)) for i in range(0, n - W, W)]
    thr = max(rms) * 0.2
    out = []
    for k, r in enumerate(rms):
        if r >= thr:
            i = k * W; out.append((i // sr, peaks(*xc(a[i:i+W], b[i:i+W]), k=2), peaks(*xc(a[i:i+W], b[i:i+W], phat=True), k=2)))
    print(ref.split('/')[-1], sr, out)
