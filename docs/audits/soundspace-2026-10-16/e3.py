import sys, json, math, pathlib, pickle
sys.path.insert(0, '.'); sys.path.insert(0, 'research')
sys.path.insert(0, '/private/tmp/claude-501/-Users-yoavbz-projects-neuraldsp-preset-generator/67cfc004-f421-4d92-9cce-0e70317476ec/scratchpad/3b-audit')
from stats import bw, fmt
from learn import arm_a_levers as AL, song_readout as R
units_all = AL.gathered_units()
print('gathered', len(units_all))
units, dropped = R.drop_refused(units_all)
print('kept', len(units), 'dropped', [(s,a,h) for s,a,h,_ in dropped])
D = pathlib.Path.home()/'ndsp-presets/learn/song-settings/soundspace/e3/scores/top'
new = {p.stem: json.loads(p.read_text())['d'] for p in D.glob('*.json')}
print('new files', len(new))
rows = []
ref = {'B1':0,'B2':0,'B0':0,'constant':0}
for u in units:
    k = f"{u['slug']}_{u['amp']}_{u['search']}"
    d = dict(u['d'])
    for n in ('B1:top','B2:top'):
        d[n.split(':')[0]] = new[k][n][u['held']]
    d['B0'] = d['B']
    rec = {'slug':u['slug'],'band':u['band'],'amp':u['amp'],'cls':u['cls'],'search':u['search'],'held':u['held'],'S':d['S']}
    for a in ('constant','B0','B1','B2'):
        v = d[a]
        if not (v is not None and math.isfinite(v) and v > 0):
            ref[a]+=1; rec[a]=0.0; rec[a+'_ref']=True
        else:
            rec[a] = math.log(v/d['S'])
    for extra in ('K_S','3-C\'','A'):
        if extra in d: rec['raw_'+extra]=d[extra]
    rows.append(rec)
print('refused', ref)
print('keys sample', [k for k in units[0]['d'].keys()][:40])
pickle.dump(rows, open(sys.argv[1],'wb'))
def R_(f, sel=lambda r: True): return [(r['slug'], r['band'], f(r)) for r in rows if sel(r)]
for a in ('constant','B0','B1','B2'): print(a,'vs S', fmt(bw(R_(lambda r: r[a]))))
for a,b in (('B2','B0'),('B2','B1'),('B1','B0'),('B2','constant')): print(a,'-',b, fmt(bw(R_(lambda r: r[a]-r[b]))))
for c in ('clean','crunch'):
    for a,b in (('B2','S'),('B0','S'),('B2','B0')):
        f = (lambda r: r[a]) if b=='S' else (lambda r: r[a]-r[b])
        print(c,a,'-',b, fmt(bw(R_(f, lambda r: r['cls']==c))))
for amp in ('pr12','sw50r','ac20'):
    for a,b in (('B2','S'),('B0','S'),('B2','B0')):
        f = (lambda r: r[a]) if b=='S' else (lambda r: r[a]-r[b])
        print(amp,a,'-',b, fmt(bw(R_(f, lambda r: r['amp']==amp))))
