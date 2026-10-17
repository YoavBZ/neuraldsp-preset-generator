import sys, json, pathlib, collections
sys.path.insert(0,'.'); sys.path.insert(0,'research')
from learn import song_bank as B, knob_ceiling as K, song_diag as D, song_relabel as RL
H = pathlib.Path.home()/'ndsp-presets'
fo = B.folds(); ps = K.parts()
part_fold = {s: fo[p['band']] for s, p in ps.items() if p['band'] in fo}
targets = json.loads((RL.DIAG/'targets.json').read_text())
ttracks = {t['window']['path'] for t in targets}
new = json.loads((RL.BANK2/'examples.json').read_text())
bad = collections.Counter()
for e in new:
    f = e['fold']
    if e['centre_fold'] != f: bad['centre_fold'] += 1
    cp = pathlib.Path(e['centre']).parent.parent.name
    if part_fold.get(cp) != f: bad['centre_part_fold'] += 1
    w = e['window']
    if w['fold'] != 'all' and w['fold'] != f: bad['window_fold'] += 1
    if w['fold'] != 'all' and fo.get(w['band']) != f: bad['window_band_fold'] += 1
    if w['path'] in ttracks: bad['target_track'] += 1
    if e.get('backing'):
        bp = pathlib.Path(e['backing']).parent.name
        if bp in part_fold and part_fold[bp] != f: bad['backing_fold'] += 1
        elif bp not in part_fold: bad['backing_unknown'] += 1
    if e.get('second_guitar'):
        pass
    bad['centre_fallback:'+str(e['centre_fallback'])] += 1
print('new examples', len(new), dict(bad))
print('new modes', collections.Counter(e['mode'] for e in new), 'centre part count per fold/class', collections.Counter((e['fold'], e['class'], pathlib.Path(e['centre']).parent.parent.name) for e in new if e['class']=='crunch').most_common(12))
# second guitar sources
print('second_guitar keys sample', [ (k,v) for k,v in new[0].items() if 'second' in k or 'guitar' in k])
# relabel anchors: pull1 continuous == an own-fold optimum of same amp/class
plan = json.loads(RL.PLAN.read_text())['examples']
opt = {f: [(a, c, D.st(json.loads(pathlib.Path(p).read_text())), pathlib.Path(p).parent.parent.name) for a, c, p in rows] for f, rows in B.ks_optima().items()}
menu = D._menu()
cnt = collections.Counter()
for k, e in plan.items():
    _, S = D._S(menu, e['amp'], e['class'])
    dims = K.space(e['amp'], S)
    p1 = D.st(e['probes']['pull1'])
    cont = [d for d in dims if d.kind in ('cont','log')]
    def dist(x, y): return max(abs(RL.unit_of(d, x) - RL.unit_of(d, y)) for d in cont)
    hits = []
    for f, rows in opt.items():
        for a, c, x, part in rows:
            if a != e['amp']: continue
            xx = {**S, **x}
            if dist(p1, xx) < 1e-3: hits.append((f, c, part, part_fold.get(part)))
    if not hits: cnt['no_match'] += 1
    elif any(h[0] == e['fold'] and h[3] == e['fold'] for h in hits): cnt['own_fold'] += 1
    else: cnt['OTHER_FOLD'] += 1; print('other', k, e['fold'], hits[:3])
    if e['window'].get('path') in ttracks: cnt['relabel_target_track'] += 1
print('relabel anchors', dict(cnt))
# bank windows on diag target tracks (affects all arms incl. B0)
ex = json.loads((B.OUT/'examples.json').read_text())
print('bank examples on a diag target track', sum(e['window'].get('path') in ttracks for e in ex), 'of', len(ex))
