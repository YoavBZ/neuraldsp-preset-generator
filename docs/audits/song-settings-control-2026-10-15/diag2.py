import sys, numpy as np
W="/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT"
sys.path.insert(0,W); sys.path.insert(0,W+"/research")
from learn import song_settings as SS, knob_ceiling as K, confirm_run as CR
from learn.di_robustness import smoothed_spectrum
from learn.direc import SPEC_N
SR=48000
f=np.fft.rfftfreq(SPEC_N,1/SR)
bands=[(80,200),(200,500),(500,1000),(1000,2000),(2000,4000),(4000,8000)]
def bandv(s): return [round(float(s[(f>=a)&(f<b)].mean()),1) for a,b in bands]
avg={k:np.load(SS.MODELS/"cache"/f"average-fold{k}.npy") for k in range(4)}
ps=K.parts(); fo=SS.folds(); d=SS.OUT/"armA-control"
print("bands",bands)
for k in range(4): print("avg2-avg%d"%k, bandv(avg[2]-avg[k]))
seen=set()
for slug,amp in SS.control_cells():
    p=ps[slug]; fl=fo[p["band"]]
    meas=K.measure_di(p); reb=np.load(d/f"{slug}-{amp}-rebuilt.npy")
    sm=smoothed_spectrum(meas); sr=smoothed_spectrum(reb)
    diff=(sr-sr.mean())-(sm-sm.mean())
    print(slug[:30],amp,"f",fl,"reb-meas",bandv(diff-np.mean(bandv(diff))))
    if slug not in seen:
        seen.add(slug); sm2=sm-sm.mean()
        print("     meas-avg2", bandv(sm2-avg[2]-np.mean(bandv(sm2-avg[2]))))
