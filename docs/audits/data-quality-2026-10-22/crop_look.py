import numpy as np, soundfile as sf, sys
from scipy.optimize import nnls
D="/Users/yoavbz/ndsp-presets/references/datasets/telefunken/Dom McLennon LFTL Sculptors Request/"
t0=float(sys.argv[1]) if len(sys.argv)>1 else 118.5
names={'DI1':'GTR 1 DI TDP-1-Norm_02-01.wav','DI2':'GTR 2 DI TDP-1-Norm_02-01.wav','A1':'GTR 1 Amp M80-Norm_02-01.wav','A2':'GTR 2 Amp M80-Norm_02-01.wav','ROOM':'DRUM Rooms 251.1-Norm_01-01.wav','KEYS':'Keys TDP-2.1-Norm_01-01.wav'}
X={}
for k,f in names.items():
    x,sr=sf.read(D+f,start=int(t0*48000),frames=480000,always_2d=True,dtype='float32');X[k]=x.mean(1)
hop=2400  # 50 ms
def env(x,lo=200,hi=4000):
    fr=np.lib.stride_tricks.sliding_window_view(x,4096)[::hop]*np.hanning(4096)
    P=np.abs(np.fft.rfft(fr,axis=1))**2;f=np.fft.rfftfreq(4096,1/48000)
    return P[:,(f>lo)&(f<hi)].sum(1)
E={k:env(v) for k,v in X.items()}
for k in E: print(k,'level dB %.1f'%(10*np.log10(E[k].mean()+1e-20)))
L=lambda v:10*np.log10(v+1e-12)
for a in ['A1','A2']:
    print(a,'corr logenv with', {k:round(float(np.corrcoef(L(E[a]),L(E[k]))[0,1]),2) for k in ['DI1','DI2','ROOM','KEYS']})
    M=np.stack([E['DI1'],E['DI2'],E['ROOM'],E['KEYS']],1);c,_=nnls(M,E[a]);fit=M*c
    print('  NNLS power share of', a, {k:round(float(fit[:,j].sum()/E[a].sum()),2) for j,k in enumerate(['DI1','DI2','ROOM','KEYS'])},'resid %.2f'%(1-fit.sum()/E[a].sum()))
print('corr DI1-DI2 logenv', round(float(np.corrcoef(L(E['DI1']),L(E['DI2']))[0,1]),2))
# activity
for k in ['DI1','DI2','A1','A2']:
    e=L(E[k]);print(k,'active share (within 30 dB of max) %.2f'%np.mean(e>e.max()-30))
