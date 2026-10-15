import sys, json, numpy as np
W="/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT"
sys.path.insert(0,W); sys.path.insert(0,W+"/research")
from learn import song_settings as SS, knob_ceiling as K, confirm_run as CR
from learn.direc_check import to_lufs
import pyloudnorm
from scipy.signal import csd, welch
SR=48000
ps=K.parts(); fo=SS.folds()
def gcc(a,b,maxlag=2000):
    n=1<<int(np.ceil(np.log2(len(a)+len(b))))
    A=np.fft.rfft(a,n);B=np.fft.rfft(b,n);X=A*np.conj(B);X/=np.abs(X)+1e-12
    c=np.fft.irfft(X,n);c=np.concatenate([c[-maxlag:],c[:maxlag+1]])
    k=np.argmax(np.abs(c));return k-maxlag, c[k]
def coh(a,b,lo=1000,hi=3000):
    f,Pab=csd(a,b,SR,nperseg=4096);_,Paa=welch(a,SR,nperseg=4096);_,Pbb=welch(b,SR,nperseg=4096)
    c=np.abs(Pab)**2/(Paa*Pbb+1e-30);m=(f>=lo)&(f<hi);return c[m].mean()
def tilt(x):
    f,P=welch(x,SR,nperseg=4096);db=10*np.log10(P+1e-30)
    def band(a,b): m=(f>=a)&(f<b); return db[m].mean()
    return round(band(2000,5000)-band(100,400),1)
m=pyloudnorm.Meter(SR)
d=SS.OUT/"armA-control"
for slug,amp in SS.control_cells():
    p=ps[slug]
    raw=to_lufs(CR.mono(p["crop"]/"di.wav")); meas=K.measure_di(p)
    fake=np.load(d/f"{slug}-{amp}-fake.npy"); reb=np.load(d/f"{slug}-{amp}-rebuilt.npy")
    print(slug,amp,"fold",fo[p["band"]],"len raw/fake/reb",len(raw),len(fake),len(reb),"lufs fake/reb/meas",
          round(m.integrated_loudness(fake),1),round(m.integrated_loudness(reb),1),round(m.integrated_loudness(meas),1))
    for nm,x in (("reb~raw",(reb,raw)),("reb~fake",(reb,fake)),("raw~fake",(raw,fake)),("meas~raw",(meas,raw))):
        l,c=gcc(*x); print("  ",nm,"lag",l,"pk",round(float(c),3))
    # lag-compensated coherence/corr
    l,_=gcc(reb,raw)
    r2=np.roll(reb,-l) if l else reb
    print("   coh1-3k reb/raw",round(coh(r2,raw),3),"meas/raw",round(coh(meas,raw),3),
          "corr",round(np.corrcoef(r2,raw)[0,1],3),"tilt raw/meas/reb",tilt(raw),tilt(meas),tilt(reb))
