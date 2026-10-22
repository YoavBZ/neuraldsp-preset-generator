"""Whole-session chroma similarity of a DI to candidate tracks (frames where both play)."""
import json,sys,pathlib,numpy as np,soundfile as sf
def chroma_file(p,hop_s=0.1,nf=8192):
    info=sf.info(p);sr=info.samplerate;hop=int(hop_s*sr);C=[];E=[]
    blk=hop*600
    for st in range(0,info.frames,blk):
        x,_=sf.read(p,start=st,frames=blk+nf,dtype='float32',always_2d=True);x=x.mean(1)
        if len(x)<nf: break
        fr=np.lib.stride_tricks.sliding_window_view(x,nf)[::hop][:blk//hop]*np.hanning(nf)
        S=np.abs(np.fft.rfft(fr,axis=1))**2;f=np.fft.rfftfreq(nf,1/sr);ok=(f>70)&(f<1500)
        pc=(np.round(12*np.log2(f[ok]/440))%12).astype(int)
        C.append(np.stack([S[:,ok][:,pc==k].sum(1) for k in range(12)],1));E.append(S[:,ok].sum(1))
    C=np.concatenate(C);E=np.concatenate(E);return C/(C.sum(1,keepdims=True)+1e-12),E
def sim(a,b):
    (A,ea),(B,eb)=a,b;m=min(len(A),len(B));A,B,ea,eb=A[:m],B[:m],ea[:m],eb[:m]
    ok=(ea>ea.max()*1e-3)&(eb>eb.max()*1e-3)
    if ok.sum()<20: return None,int(ok.sum())
    A=A[ok]-A[ok].mean(1,keepdims=True);B=B[ok]-B[ok].mean(1,keepdims=True)
    return round(float(np.mean((A*B).sum(1)/(np.linalg.norm(A,axis=1)*np.linalg.norm(B,axis=1)+1e-12))),3),int(ok.sum())
pairs=json.load(open(sys.argv[1]));keys=sys.argv[2:]
for p in pairs:
    if keys and not any(k in p['key'] for k in keys): continue
    d=chroma_file(p['di'])
    res={pathlib.Path(t).name:sim(d,chroma_file(t)) for t in p['own']+p['others'] if 'DI' not in pathlib.Path(t).name}
    print(p['key'].split('/')[-1], 'own:',{pathlib.Path(t).name[:22]:res[pathlib.Path(t).name] for t in p['own']})
    print('   top others:',sorted(((v[0],k[:22]) for k,v in res.items() if v[0] is not None and k not in [pathlib.Path(t).name for t in p['own']]),reverse=True)[:4])
