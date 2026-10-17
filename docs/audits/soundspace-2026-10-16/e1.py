import sys, json, math, pickle, collections
sys.path.insert(0,'.'); sys.path.insert(0,'research'); sys.path.insert(0, sys.argv[1])
from stats import bw, fmt
from learn import song_soundspace as SP
units, targets, cands = SP.e1_load_units('report')
print('units', len(units), SP.units_hash(units), collections.Counter(u['type'] for u in units), 'targets', len({u['target'] for u in units}))
def lv(u, name):
    if name == 'S': return 0.0, False
    v = u['d'].get(name); S = u['d']['S']
    if v is None or not math.isfinite(v) or v <= 0: return 0.0, True
    return math.log(v/S), False
names = {'constant': lambda u: 'constant', 'B0': lambda u: f"1b:{u['search']}:top", 'B1': lambda u: f"B1|1b:{u['search']}:top", 'B2': lambda u: f"B2|1b:{u['search']}:top"}
names1a = {'B0': lambda u: f"1a:{u['search']}:top", 'B1': lambda u: f"B1|1a:{u['search']}:top", 'B2': lambda u: f"B2|1a:{u['search']}:top"}
ref = collections.Counter(); rows = []
for u in units:
    r = {'t': str(u['target']), 'band': u['band'], 'type': u['type'], 'amp': None}
    for a, f in names.items():
        r[a], x = lv(u, f(u)); ref[a] += x
    for a, f in names1a.items():
        r[a+'_1a'], x = lv(u, f(u)); ref[a+'_1a'] += x
    rows.append(r)
tby = {str(t['i']): t for t in targets}
for r in rows: r['amp'] = tby[r['t']]['amp']; r['cls'] = tby[r['t']]['class']
print('top-answer refusals', dict(ref))
pickle.dump(rows, open(sys.argv[1]+'/e1rows.pkl','wb'))
def R(f, sel=lambda r: True): return [(r['t'], r['band'], f(r)) for r in rows if sel(r)]
for sub, sel in (('all', lambda r: True), ('broad', lambda r: r['type']=='broad'), ('ks_prior', lambda r: r['type']=='ks_prior')):
    for a in ('constant','B0','B1','B2'): print(sub, a, 'vs S', fmt(bw(R(lambda r: r[a], sel))))
    for a, b in (('B2','B0'),('B2','B1'),('B1','B0')): print(sub, a,'-',b, fmt(bw(R(lambda r: r[a]-r[b], sel))))
for a in ('B0','B1','B2'): print('1a', a, fmt(bw(R(lambda r: r[a+'_1a']))))
print('1a B2-B0', fmt(bw(R(lambda r: r['B2_1a']-r['B0_1a']))))
for amp in ('pr12','sw50r','ac20'):
    print(amp, 'B2-B0', fmt(bw(R(lambda r: r['B2']-r['B0'], lambda r: r['amp']==amp))))
for c in ('clean','crunch'):
    print(c, 'B2-B0', fmt(bw(R(lambda r: r['B2']-r['B0'], lambda r: r['cls']==c))))
