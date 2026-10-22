import json,numpy as np,sys,collections
pairs={p['key']:p for p in json.load(open('pairs-inv.json'))}
pool=json.load(open('/Users/yoavbz/ndsp-presets/learn/pretrain-set/pool.json'))['sections']
use=collections.defaultdict(set)
for s in pool: use[s['di']].add(s['split'])
D=set(x[0].split('@')[0] for x in json.load(open('direct_sections.json'))['sections'])
LEAK=json.load(open('/Users/yoavbz/ndsp-presets/learn/pretrain-set/leakage.json'))
out=[]
for l in open(sys.argv[1]):
    r=json.loads(l)
    if 'error' in r or not r['windows']: out.append((r['key'],None));continue
    ow=[max(v[0] for v in w['own'].values()) if w['own'] else np.nan for w in r['windows']]
    isdi=lambda k: 'di' in k.lower().replace('.wav','')[-6:] or k.lower().endswith('d.wav')
    amps=[{k:v for k,v in w['others'].items() if not isdi(k)} for w in r['windows']]
    ot=[(max(a.items(),key=lambda kv:kv[1][0]) if a else (None,[np.nan])) for a in amps]
    otv=[o[1][0] for o in ot]
    better=np.mean([b>a+0.1 for a,b in zip(ow,otv)])
    top=collections.Counter(o[0] for o,a in zip(ot,ow) if o[1][0]>a+0.1).most_common(1)
    hi_other=collections.Counter(k for a in amps for k,v in a.items() if v[0]>0.6)
    out.append((r['key'],dict(n=len(ow),own_med=float(np.nanmedian(ow)),own_p10=float(np.nanpercentile(ow,10)),other_med=float(np.nanmedian(otv)),better=float(better),top=top,hi_other={k:v for k,v in hi_other.items() if v>=0.25*len(ow)},use=sorted(use.get(r['key'],[])),direct=r['key'] in D,split=pairs[r['key']]['split'],dropped=LEAK.get(r['key'],{}).get('dropped'))))
ok=[o for o in out if o[1]]
print('DIs',len(out),'scored',len(ok))
own=np.array([o[1]['own_med'] for o in ok])
print('own median onset corr: pct5/25/50/75',np.round(np.percentile(own,[5,25,50,75]),2))
print('own_med<0.3:',sum(own<0.3),' <0.4:',sum(own<0.4),'  windows-where-other-better>25%:',sum(o[1]['better']>0.25 for o in ok))
for k,v in sorted(ok,key=lambda o:o[1]['own_med']):
    if v['own_med']<0.4 or v['better']>0.25 or v['hi_other']:
        print('%-75s own %.2f p10 %.2f oth %.2f better %.2f top %s hi %s use %s direct %s %s dropped %s'%(k[-75:],v['own_med'],v['own_p10'],v['other_med'],v['better'],v['top'],v['hi_other'],v['use'],v['direct'],v['split'],v['dropped']))
json.dump(out,open(sys.argv[1]+'.summary.json','w'))
