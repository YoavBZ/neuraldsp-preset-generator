import sys, pickle, math, statistics, collections
sys.path.insert(0, sys.argv[1])
from stats import bw, fmt
from scipy.stats import spearmanr
d = pickle.load(open(sys.argv[1]+'/models.pkl','rb'))
e2 = d['e2']
def fin(x): return x is not None and math.isfinite(x)
def rho(sc, hv):
    ok=[i for i,(a,b) in enumerate(zip(sc,hv)) if fin(a) and fin(b) and b>0]
    if len(ok)<10: return None
    return spearmanr([sc[i] for i in ok],[hv[i] for i in ok]).correlation
rows = collections.defaultdict(list)
for r in e2:
    for a in ('B0','B1','B2','B0cens'):
        r['rho_'+a] = rho(r['sc_'+a], r['hv'])
    for a in ('B0','B1','B2'):
        r['rhoS_'+a] = rho(r['so_'+a], r['hv'])
P = lambda f: [(r['slug'], r['band'], f(r)) for r in e2 if f(r) is not None]
# NB report used direction rows (not part-averaged); do both
def bwdir(f): 
    from stats import bw as _bw
    return _bw([(r['slug']+r['amp']+r['search'], r['band'], f(r)) for r in e2 if f(r) is not None])
for a in ('B0','B0cens','B1','B2'): print('rho', a, fmt(bwdir(lambda r: r['rho_'+a])))
for a in ('B0','B1','B2'): print('rho shuffled', a, fmt(bwdir(lambda r: r['rhoS_'+a])), '| true-shuf', fmt(bwdir(lambda r: r['rho_'+a]-r['rhoS_'+a] if r['rhoS_'+a] is not None else None)))
for a,b in (('B2','B0'),('B1','B0'),('B2','B1'),('B2','B0cens')): print('rho diff', a,'-',b, fmt(bwdir(lambda r: r['rho_'+a]-r['rho_'+b])))
# picks among first 8: max-density pick vs mean of first 8 (random pick) vs K_S own pick
def picks(r, a, n=8):
    hv, sv, sc = r['hv'], r['sv'], r['sc_'+a]
    ok=[i for i in range(min(n,len(hv))) if fin(hv[i]) and hv[i]>0 and fin(sc[i])]
    if len(ok)<2: return None
    j=max(ok,key=lambda i:(sc[i],-i)); rnd=statistics.fmean(math.log(hv[i]/r['start_held']) for i in ok)
    okS=[i for i in ok if fin(sv[i])]; k=min(okS,key=lambda i:(sv[i],i))
    return dict(pick=math.log(hv[j]/r['start_held']), rnd=rnd, ks=math.log(hv[k]/r['start_held']), best=min(math.log(hv[i]/r['start_held']) for i in ok))
for n in (8,16):
  for a in ('B0','B1','B2'):
    pk=[(r, picks(r,a,n)) for r in e2]
    print(f'first{n}', a, 'pick-random', fmt(bwdir(lambda r: (lambda p: p and p['pick']-p['rnd'])(picks(r,a,n)))))
  print(f'first{n}', 'K_S search pick - random', fmt(bwdir(lambda r: (lambda p: p and p['ks']-p['rnd'])(picks(r,'B2',n)))), 'random vs S', fmt(bwdir(lambda r: (lambda p: p and p['rnd'])(picks(r,'B2',n)))))
  print(f'first{n}', 'B2 pick - B0 pick', fmt(bwdir(lambda r: (lambda p,q: p and q and p['pick']-q['pick'])(picks(r,'B2',n),picks(r,'B0',n)))))
# within the 8 best-by-search-half of the whole path (closer analog to C-fine: density picks among top-8 of an objective)
def top8(r,a):
    hv, sv, sc = r['hv'], r['sv'], r['sc_'+a]
    ok=sorted([i for i in range(len(hv)) if fin(hv[i]) and hv[i]>0 and fin(sv[i]) and fin(sc[i])], key=lambda i:(sv[i],i))[:8]
    if len(ok)<2: return None
    j=max(ok,key=lambda i:(sc[i],-i)); rnd=statistics.fmean(math.log(hv[i]/r['start_held']) for i in ok)
    return math.log(hv[j]/r['start_held'])-rnd
for a in ('B0','B1','B2'): print('top8-by-search, density pick - random of 8', a, fmt(bwdir(lambda r: top8(r,a))))
# collapse
for src, key in (('songs','songcol'),('targets','tcol')):
    data = d[key]
    for a in ('B0','B1','B2'):
        rs=[x for x in data if x['arm']==a and (src=='songs' or x['view']=='1b')]
        print(src, a, 'median sep %.3f top_w %.3f effK %.2f'%(statistics.median(x['sep'] for x in rs), statistics.median(x['top_w'] for x in rs), statistics.median(x['eff'] for x in rs)), 'n',len(rs))
    if src=='targets':
        for a in ('B0','B1','B2'):
            per = {f: statistics.median(x['sep'] for x in data if x['arm']==a and x['view']=='1b' and x['fold']==f) for f in range(4)}
            print(' per-fold median sep', a, {f: round(v,3) for f,v in per.items()})
