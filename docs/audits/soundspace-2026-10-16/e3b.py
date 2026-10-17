import sys, pickle, math, statistics, collections
sys.path.insert(0,'.'); sys.path.insert(0,'research'); sys.path.insert(0, sys.argv[1])
from stats import bw, fmt
from learn import arm_a_levers as AL, song_readout as R, song_bank as B, knob_ceiling as K
rows = pickle.load(open(sys.argv[1]+'/e3rows.pkl','rb'))
units, _ = R.drop_refused(AL.gathered_units())
ud = {(u['slug'],u['amp'],u['search']): u for u in units}
fo = B.folds(); ps = K.parts()
for r in rows:
    u = ud[(r['slug'], r['amp'], r['search'])]
    r['fold'] = fo[ps[r['slug']]['band']]
    for n in ('B_half','shuffled','A','K_S','amp_track'):
        v = u['d'].get(n); v = v[0] if isinstance(v, list) else v; r[n] = math.log(v/u['d']['S']) if isinstance(v,(int,float)) and math.isfinite(v) and v > 0 else None
Rr = lambda f, sel=lambda r: True: [(r['slug'], r['band'], f(r)) for r in rows if sel(r) and f(r) is not None]
print('B_half - B0 (model-to-model scale)', fmt(bw(Rr(lambda r: r['B_half'] - r['B0'] if r['B_half'] is not None else None))))
print('B0 shuffled - B0', fmt(bw(Rr(lambda r: r['shuffled'] - r['B0'] if r['shuffled'] is not None else None))))
print('arm A vs S', fmt(bw(Rr(lambda r: r['A']))), '| K_S vs S', fmt(bw(Rr(lambda r: r['K_S']))))
for f in range(4):
    print('fold', f, 'B2-B0 mean %.3f  B2-S %.3f  n %d' % (statistics.fmean(r['B2']-r['B0'] for r in rows if r['fold']==f), statistics.fmean(r['B2'] for r in rows if r['fold']==f), sum(r['fold']==f for r in rows)))
print('directions B2<S', sum(r['B2']<0 for r in rows), 'B2<B0', sum(r['B2']<r['B0'] for r in rows), 'of', len(rows))
# leave-one-part-out for B2-S and B2-B0
parts = sorted({r['slug'] for r in rows})
for name, f in (('B2-S', lambda r: r['B2']), ('B2-B0', lambda r: r['B2']-r['B0'])):
    lo = [bw(Rr(f, lambda r, p=p: r['slug'] != p))['mean'] for p in parts]
    print('leave-one-part-out', name, min(lo), max(lo), 'parts', len(parts))
# trimmed / median per part
import numpy as np
pm = collections.defaultdict(list)
for r in rows: pm[r['slug']].append(r['B2']-r['B0'])
print('median part B2-B0 %.3f' % np.median([np.mean(v) for v in pm.values()]))
