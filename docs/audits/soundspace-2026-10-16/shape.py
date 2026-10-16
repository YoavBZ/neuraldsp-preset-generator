import sys, json, math, random, statistics, pathlib, collections
sys.path.insert(0,'.'); sys.path.insert(0,'research')
import numpy as np
from scipy.stats import spearmanr
from learn import song_soundspace as SP, song_diag as D, knob_ceiling as K, song_relabel as RL, song_bank as B
menu = D._menu()
def shape_rows(rows):
    """rows: (band, amp, answer, target) -> stats"""
    lim, per, sw, mic = [], collections.defaultdict(list), [], []
    for band, amp, x, t in rows:
        for d in K.space(amp, t):
            k = (d.module, d.key)
            if d.kind in ('cont','log'):
                ua, ut = RL.unit_of(d, x), RL.unit_of(d, t)
                lim.append(ua <= 0.01 or ua >= 0.99); per[d.name].append((ua, ut, band))
            elif d.kind == 'switch':
                sw.append(x.get(k) == t.get(k))
    spread = statistics.fmean([np.std([a for a,_,_ in v])/np.std([b for _,b,_ in v]) for v in per.values() if len(v)>2 and np.std([b for _,b,_ in v])>0])
    ig = per.get('parameters/inputGain')
    rho_ig = spearmanr([a for a,_,_ in ig],[b for _,b,_ in ig]).correlation if ig else None
    tone = [n for n in per if n != 'parameters/inputGain' and any(n == d.name for amp in K.AMPS for d in K.AMP_DIMS[amp] if d.kind=='cont')]
    rho_tone = statistics.fmean([spearmanr([a for a,_,_ in per[n]],[b for _,b,_ in per[n]]).correlation for n in tone if len(per[n])>2])
    tlim = statistics.fmean([b <= 0.01 or b >= 0.99 for v in per.values() for _,b,_ in v])
    return dict(limit=statistics.fmean(lim), tlimit=tlim, spread=spread, rho_ig=rho_ig, rho_tone=rho_tone, sw=statistics.fmean(sw))
def boot(rows, arms, B_=1000, seed=0):
    bands = sorted({r[0] for r in rows[arms[0]]})
    pt = {a: shape_rows(rows[a]) for a in arms}
    rng = random.Random(seed); acc = collections.defaultdict(list)
    for _ in range(B_):
        bs = [rng.choice(bands) for _ in bands]
        res = {}
        for a in arms:
            by = collections.defaultdict(list)
            for r in rows[a]: by[r[0]].append(r)
            res[a] = shape_rows([r for b in bs for r in by[b]])
        for a in arms:
            for k, v in res[a].items(): acc[(a,k)].append(v)
        for k in res['B0']:
            for a in arms[1:]: acc[(a+'-B0',k)].append(res[a][k]-res['B0'][k])
    def ci(v): v=sorted(x for x in v if x is not None and math.isfinite(x)); return (round(v[int(.05*len(v))],3), round(v[int(.95*len(v))],3))
    for a in arms:
        print(a, {k: (round(v,3), ci(acc[(a,k)])) for k, v in pt[a].items()})
    for a in arms[1:]:
        print(a+'-B0', {k: (round(pt[a][k]-pt['B0'][k],3), ci(acc[(a+'-B0',k)])) for k in pt['B0']})
# E1 targets, view 1b top
targets = json.loads((SP.DIAG/'targets.json').read_text())
cj = json.loads((SP.DIAG/'candidates.json').read_text())['targets']
for a in ('B1','B2'):
    pr = json.loads((SP.OUT/'e1'/f'proposals-{a}.json').read_text())['targets']
    for k, v in pr.items(): cj[k].update(v)
rows = {a: [] for a in ('B0','B1','B2')}
for t in targets:
    key = str(t['i'])
    for s in 'AB':
        for a in rows:
            n = f"1b:{s}:top" if a=='B0' else f"{a}|1b:{s}:top"
            if n in cj[key]: rows[a].append((t['band'], t['amp'], D.st(cj[key][n]), D.st(t['settings'])))
print('E1 targets (vs target label), n', {a: len(v) for a, v in rows.items()})
boot(rows, ['B0','B1','B2'])
# songs: against the record's K_S optimum from the same search half
ps, fo = K.parts(), B.folds()
preds = json.loads((SP.SS_OUT/'armB'/'predictions.json').read_text())['cells']
top = json.loads((SP.OUT/'e3'/'proposals-top.json').read_text())
rows = {a: [] for a in ('B0','B1','B2')}
for slug, amp, search, held in SP.e3_cells():
    key = f'{slug}|{amp}|{search}'
    p = K.OUT/'cells'/slug/amp/f'K_S-{search}.json'
    if not p.exists(): continue
    _, S = D._S(menu, amp, ps[slug]['gain_class'])
    ks = {**S, **D.st(json.loads(p.read_text()))}
    band = ps[slug]['band']
    rows['B0'].append((band, amp, D.st(preds[key]['B']['settings']), ks))
    rows['B1'].append((band, amp, D.st(top[key]['B1:top']), ks))
    rows['B2'].append((band, amp, D.st(top[key]['B2:top']), ks))
print('songs (vs K_S optimum), n', {a: len(v) for a, v in rows.items()})
boot(rows, ['B0','B1','B2'])
