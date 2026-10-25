import json,glob,numpy as np,collections,math
G='/Users/yoavbz/ndsp-presets/learn/direct-stems/gate/rows/'
J={}
for f in glob.glob(G+'*.jsonl'):
    for l in open(f):
        r=json.loads(l); J[(r['what'],r['i'])]=r
C={json.loads(l)['i']:json.loads(l) for l in open('contam-vsep-xlance_g.jsonl')}
BK={json.loads(l)['id']:json.loads(l) for l in open('b2-val.jsonl')}
rows=[]
for (w,i),r in J.items():
    if w!='D': continue
    c=J.get(('constant',i)); d0=J.get(('D0',i))
    if not c: continue
    v=[];v0=[]
    for h in 'AB':
        a,b=r['judge'].get(h),c['judge'].get(h)
        if a is None or b is None or not (a>0 and b>0) : continue
        v.append(max(-math.log(10),min(math.log(10),math.log(a/b))))
        if d0 and d0['judge'].get(h): v0.append(max(-math.log(10),min(math.log(10),math.log(d0['judge'][h]/b))))
    if not v or i not in C: continue
    cc=C[i]; lk=np.nanmean([cc[k] for k in ('leak_A','leak_B') if cc.get(k) is not None])
    bk=BK[cc['section']]
    rows.append(dict(i=i,band=r['band'],sec=cc['section'],lr=np.mean(v),lr0=np.mean(v0) if v0 else np.nan,leak=lk,ratio=cc['ratio_db'],
        eg=bk['share'].get('egtr',0),base=r['base'],dist_c=np.mean([c['judge'][h] for h in 'AB' if c['judge'].get(h)])))
print('n',len(rows))
json.dump(rows,open('impact_rows.json','w'))
from scipy.stats import spearmanr
bands=sorted(set(r['band'] for r in rows))
for b in bands:
    R=[r for r in rows if r['band']==b]
    lr=np.array([r['lr'] for r in R]);lk=np.array([r['leak'] for r in R]);ra=np.array([r['ratio'] for r in R])
    t=np.nanpercentile(lk,[33.3,66.7])
    lo=lr[lk<=t[0]].mean();hi=lr[lk>t[1]].mean()
    print(b.ljust(20),len(R),'mean lr %.3f'%lr.mean(),'leak med %.2f'%np.median(lk),'rho(lr,leak) %.2f'%spearmanr(lr,lk)[0],'rho(lr,ratio) %.2f'%spearmanr(lr,ra)[0],'lowT %.3f highT %.3f'%(lo,hi), 'egtr %.2f'%np.median([r['eg'] for r in R]))
# pooled within-band: tercile within band; difference high-low per band, then band mean with section bootstrap
rng=np.random.default_rng(0)
def effect(rows):
    out=[]
    for b in bands:
        R=[r for r in rows if r['band']==b]
        lk=np.array([r['leak'] for r in R]);lr=np.array([r['lr'] for r in R])
        t=np.nanpercentile(lk,[33.3,66.7])
        out.append(lr[lk>t[1]].mean()-lr[lk<=t[0]].mean())
    return np.mean(out)
e=effect(rows)
secs=collections.defaultdict(list)
for r in rows: secs[(r['band'],r['sec'])].append(r)
keys=list(secs)
bs=[]
for _ in range(2000):
    samp=[]
    for b in bands:
        kb=[k for k in keys if k[0]==b]
        for j in rng.integers(0,len(kb),len(kb)): samp+=secs[kb[j]]
    bs.append(effect(samp))
print('within-band high-minus-low leak tercile, lr: %.3f [%.3f, %.3f] (90%% section bootstrap)'%(e,*np.percentile(bs,[5,95])))
