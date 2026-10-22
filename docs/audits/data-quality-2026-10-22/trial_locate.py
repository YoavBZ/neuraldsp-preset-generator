import numpy as np, soundfile as sf, sys
L='/Users/yoavbz/ndsp-presets/listening/clean-start-volume/listen/'
D="/Users/yoavbz/ndsp-presets/references/datasets/telefunken/Dom McLennon LFTL Sculptors Request/"
C="/Users/yoavbz/ndsp-presets/references/validation-crops/telefunken-Sculptor's_Request-GTR_1/"
hop_s=0.02
def env(x,sr):
    hop=int(hop_s*sr);n=2048 if sr<=48000 else 4096
    fr=np.lib.stride_tricks.sliding_window_view(x,n)[::hop]*np.hanning(n)
    P=np.abs(np.fft.rfft(fr,axis=1))**2;f=np.fft.rfftfreq(n,1/sr)
    e=10*np.log10(P[:,(f>150)&(f<5000)].sum(1)+1e-12)
    o=np.maximum(np.diff(np.maximum(e,e.max()-45),prepend=e[0]),0)
    return o
def rd(p):
    x,sr=sf.read(p,always_2d=True,dtype='float32');return x.mean(1),sr
T=int(sys.argv[1])
trial={k:rd(L+f'trial-{T:02d}-{k}.flac') for k in 'RAB'}
for k,(x,sr) in trial.items(): print(k,'dur %.2f s sr %d'%(len(x)/sr,sr))
full={k:rd(D+f) for k,f in [('DI1','GTR 1 DI TDP-1-Norm_02-01.wav'),('DI2','GTR 2 DI TDP-1-Norm_02-01.wav'),('A1','GTR 1 Amp M80-Norm_02-01.wav'),('A2','GTR 2 Amp M80-Norm_02-01.wav')]}
FE={k:env(*v) for k,v in full.items()}
for k,(x,sr) in trial.items():
    e=env(x,sr);n=len(e);res={}
    for fk,fe in FE.items():
        best=(-2,0)
        for s in range(0,len(fe)-n,1):
            seg=fe[s:s+n]
            if seg.std()==0: continue
            c=np.corrcoef(e,seg)[0,1]
            if c>best[0]: best=(c,s*hop_s)
        res[fk]=(round(float(best[0]),3),round(best[1],2))
    print(k,res)
cd,sr=rd(C+'di.wav');cr,_=rd(C+'reference.wav')
for k,(x,sr2) in trial.items():
    e=env(x,sr2)
    for nm,y in [('cropDI',cd),('cropREF',cr)]:
        f=env(y,sr);best=(-2,0)
        for s in range(0,len(f)-len(e)+1):
            c=np.corrcoef(e,f[s:s+len(e)])[0,1]
            if c>best[0]:best=(c,s*hop_s)
        print(' ',k,'vs',nm,'best corr %.3f at %.2f s'%best)
