import sys, json, numpy as np
W="/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT"
sys.path.insert(0,W); sys.path.insert(0,W+"/research")
from learn import song_settings as SS, knob_ceiling as K, confirm_run as CR
from learn.rebuilt_judge import rebuilt_distance
from learn.di_robustness import smoothed_spectrum
from learn.direc_check import eq_to, to_lufs
from analysis.aligned import aligned_distance
ps=K.parts(); d=SS.OUT/"armA-control"
def obj(fake,y,di,lag):
    out={}
    for h,(a,b) in K.R.HALVES.items():
        x=aligned_distance(fake,y,di,lag=lag,render_latency=52,start_s=a,end_s=b).distance
        out[h]=round(x,3) if x is not None else None
    return out
rr=K.Renderer(); res={}
try:
    menu=rr.menu()
    for slug,amp in SS.control_cells():
        p=ps[slug]; sel,S=menu[amp][K.START[p["gain_class"]][amp]]
        fake=np.load(d/f"{slug}-{amp}-fake.npy"); reb=np.load(d/f"{slug}-{amp}-rebuilt.npy")
        meas=K.measure_di(p)
        sm=smoothed_spectrum(meas); sr=smoothed_spectrum(reb)
        rebq=to_lufs(eq_to(reb,(sm-sm.mean())-(sr-sr.mean())))   # diagnostic: rebuilt with measure DI's long-term balance
        T={tuple(k.rsplit("/",1)):v for k,v in json.loads((d/f"{slug}-{amp}-target.json").read_text()).items()}
        r={}
        for dn,di in (("reb",reb),("rebEQ",rebq)):
            di32=di.astype(np.float32); rr.render(di32,sel,S)
            for sn,st in (("S",S),("T",T)):
                y=rr.render(di32,sel,st)
                r[f"{dn}/{sn}/lag-52"]=obj(fake,y,di,-52); r[f"{dn}/{sn}/lag0"]=obj(fake,y,di,0)
        res[f"{slug}|{amp}"]=r
        print(slug,amp,json.dumps(r),flush=True)
finally:
    rr.close()
json.dump(res,open("/private/tmp/claude-501/-Users-yoavbz-projects-neuraldsp-preset-generator/67cfc004-f421-4d92-9cce-0e70317476ec/scratchpad/diag3.json","w"),indent=1)
