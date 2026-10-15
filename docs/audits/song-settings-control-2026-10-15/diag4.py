import sys, numpy as np
W="/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT"
sys.path.insert(0,W); sys.path.insert(0,W+"/research")
from learn import song_settings as SS, knob_ceiling as K
ps=K.parts(); d=SS.OUT/"armA-control"
def env(x,n=1024): k=len(x)//n; return 20*np.log10(np.sqrt((x[:k*n].reshape(k,n)**2).mean(1))+1e-9)
def crest(x): return round(20*np.log10(np.percentile(np.abs(x),99.9)/np.sqrt((x**2).mean())),1)
for slug,amp in SS.control_cells():
    p=ps[slug]; meas=K.measure_di(p); reb=np.load(d/f"{slug}-{amp}-rebuilt.npy")
    em,er=env(meas),env(reb); m=em>em.max()-40
    print(slug[:28],amp,"env corr",round(np.corrcoef(em[m],er[m])[0,1],3),"env rms dB diff",round(np.sqrt(np.mean((em[m]-er[m]-np.median(em[m]-er[m]))**2)),2),
          "crest meas/reb",crest(meas),crest(reb),"rms dBFS meas/reb",round(10*np.log10((meas**2).mean()),1),round(10*np.log10((reb**2).mean()),1))
