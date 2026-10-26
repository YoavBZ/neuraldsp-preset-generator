import numpy as np, soundfile as sf, sys
L='/Users/yoavbz/ndsp-presets/listening/clean-start-volume/listen/'
D="/Users/yoavbz/ndsp-presets/references/datasets/telefunken/Dom McLennon LFTL Sculptors Request/"
T=int(sys.argv[1]); t0=float(sys.argv[2])
def rd(p,start=None,n=None):
    if start is None: x,sr=sf.read(p,always_2d=True,dtype='float32')
    else: x,sr=sf.read(p,start=int(start*48000),frames=n,always_2d=True,dtype='float32')
    return x.mean(1)
X={k:rd(L+f'trial-{T:02d}-{k}.flac') for k in 'RB'}
n=len(X['R'])
for k,f in [('DI1','GTR 1 DI TDP-1-Norm_02-01.wav'),('DI2','GTR 2 DI TDP-1-Norm_02-01.wav'),('A2','GTR 2 Amp M80-Norm_02-01.wav'),('KEYS','Keys TDP-2.1-Norm_01-01.wav'),('BASS','Bass DI TDA-1-Norm_02-01.wav'),('VOX','Vox M80-Norm_02-01.wav'),('ROOM','DRUM Rooms 251.1-Norm_01-01.wav')]:
    X[k]=rd(D+f,t0,n)
def chroma(x,sr=48000,nf=8192,hop=2400):
    fr=np.lib.stride_tricks.sliding_window_view(x,nf)[::hop]*np.hanning(nf)
    S=np.abs(np.fft.rfft(fr,axis=1))**2;f=np.fft.rfftfreq(nf,1/sr);ok=(f>70)&(f<1500)
    pc=(np.round(12*np.log2(f[ok]/440))%12).astype(int)
    C=np.stack([S[:,ok][:,pc==k].sum(1) for k in range(12)],1)
    return C/ (C.sum(1,keepdims=True)+1e-12), S, f
Cs={k:chroma(v) for k,v in X.items()}
def sim(a,b):
    A,B=Cs[a][0],Cs[b][0];m=min(len(A),len(B));A,B=A[:m],B[:m]
    A=A-A.mean(1,keepdims=True);B=B-B.mean(1,keepdims=True)
    return float(np.mean((A*B).sum(1)/(np.linalg.norm(A,axis=1)*np.linalg.norm(B,axis=1)+1e-12)))
for a,b in [('R','B'),('R','DI1'),('B','DI1'),('R','DI2'),('B','DI2'),('R','KEYS'),('B','KEYS'),('R','BASS'),('R','A2'),('R','VOX')]:
    print(a,b,'chroma sim %.2f'%sim(a,b))
for k in X:
    print(k,'mean chroma',np.round(Cs[k][0].mean(0),2), 'rms dB %.1f'%(10*np.log10(np.mean(X[k]**2)+1e-20)))
