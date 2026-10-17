"""Bleed robustness, result 4: cross-half local Spearman (experiment 1b, 'all' 48 points per cell)."""
import sys, json, math, pathlib, statistics
import numpy as np
from scipy import stats
WT = pathlib.Path('/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT')
sys.path.insert(0, str(WT)); sys.path.insert(0, str(WT / 'research'))
from learn import song_readout as R, knob_ceiling as K
ROOT = pathlib.Path.home() / 'ndsp-presets/learn/local-objective'
BT = json.loads((WT / 'docs/audits/bleed-2026-10-16/bleed-table.json').read_text())
PS = K.parts(); SIG = json.load(open(ROOT / 'sigma.json'))
CUR = "cprime|stem|native|own"; TRUE = "measure|reference|native|own"; MAT = "cprime_ref|reference|native|own"
def fin(x): return isinstance(x, (int, float)) and math.isfinite(x)
def sp(o, t):
    pr = [(a, b) for a, b in zip(o, t) if fin(a) and fin(b) and b > 0]
    if len(pr) < 3: return None
    a, b = zip(*pr)
    if len(set(a)) < 2 or len(set(b)) < 2: return None
    return float(np.corrcoef(stats.rankdata(a), stats.rankdata(b))[0, 1])
oth = {'A': 'B', 'B': 'A'}
cells = {}
for key in sorted(SIG['cells']):
    slug, amp = key.split('|'); sc = {}
    for d in ('cprime', 'measure', 'cprime_ref'):
        j = json.load(open(ROOT / 'scores' / d / slug / f'{amp}.json'))
        for cfg in j['scores'][0]:
            sc[cfg] = {h: [s[cfg][h] for s in j['scores']] for h in 'AB'}
    T = sc[TRUE]
    # direction h: objective on half h, truth on the other half
    cells[key] = {'slug': slug, 'ceiling': sp(T['A'], T['B']),
                  'cur': {h: sp(sc[CUR][h], T[oth[h]]) for h in 'AB'},
                  'mat': {h: sp(sc[MAT][h], T[oth[h]]) for h in 'AB'}}
print('cells', len(cells), 'parts', len({c['slug'] for c in cells.values()}))
def flag(slug, h): return BT[slug]['halves'][h]['flag']
BAD = {'b': {'high'}, 'c': {'moderate', 'high'}}
def mean(xs):
    xs = [x for x in xs if x is not None]; return statistics.fmean(xs) if xs else None
def agg(vals):
    """vals {cell: v}: part means over amps -> band-weighted, 90% band-clustered (bw_stats)."""
    by = {}
    for k, v in vals.items():
        if v is None: continue
        by.setdefault(k.split('|')[0], []).append(v)
    rows = [(PS[s]['band'], statistics.fmean(v)) for s, v in by.items()]
    st = R.bw_stats(rows); n = sum(v is not None for v in vals.values())
    f = lambda x: 'n/a' if x is None else f'{x:+.3f}'
    return f"{f(st['band_weighted_mean'])} [{f(st['lo90'])}, {f(st['hi90'])}] parts {st['parts']} bands {st['bands']} cells {n} bands>0 {st['bands_positive']}/{st['bands']}"
def keep_cell(c, rule):
    if rule == 'a': return True
    if rule == 'd': return BT[c['slug']]['source'] == 'cambridge'
    return not any(flag(c['slug'], h) in BAD[rule] for h in 'AB')
def keep_dir(c, h, rule):
    """per-direction: drop the direction whose truth (held) half other(h) is flagged."""
    if rule == 'a': return True
    if rule == 'd': return BT[c['slug']]['source'] == 'cambridge'
    return flag(c['slug'], oth[h]) not in BAD[rule]
for rule in 'abcd':
    print(f'\n=== rule ({rule}) ===')
    kc = {k: c for k, c in cells.items() if keep_cell(c, rule)}
    cur = {k: mean(c['cur'].values()) for k, c in kc.items()}
    mat = {k: mean(c['mat'].values()) for k, c in kc.items()}
    ceil = {k: c['ceiling'] for k, c in kc.items()}
    dif = {k: (mat[k] - cur[k]) if None not in (mat[k], cur[k]) else None for k in kc}
    gap = {k: (ceil[k] - cur[k]) if None not in (ceil[k], cur[k]) else None for k in kc}
    print('  [cell rule: drop a cell if either half is flagged]')
    for n, v in (('ceiling', ceil), ('matched 1b', mat), ('current', cur), ('matched - current', dif), ('ceiling - current', gap)):
        print(f'    {n:20s} {agg(v)}')
    if rule in 'bc':
        print('  [direction rule: drop a direction if its truth half is flagged; ceiling stays on the cell rule]')
        cur2, mat2 = {}, {}
        for k, c in cells.items():
            hs = [h for h in 'AB' if keep_dir(c, h, rule)]
            if not hs: continue
            cur2[k] = mean([c['cur'][h] for h in hs]); mat2[k] = mean([c['mat'][h] for h in hs])
        dif2 = {k: (mat2[k] - cur2[k]) if None not in (mat2[k], cur2[k]) else None for k in cur2}
        for n, v in (('matched 1b', mat2), ('current', cur2), ('matched - current', dif2)):
            print(f'    {n:20s} {agg(v)}')
print('\nTelefunken only, by cell flag:')
for lab, f in (('Telefunken all', lambda c: BT[c['slug']]['source'] == 'telefunken'),
               ('Telefunken both halves low', lambda c: BT[c['slug']]['source'] == 'telefunken' and all(flag(c['slug'], h) == 'low' for h in 'AB')),
               ('Telefunken any half mod/high', lambda c: BT[c['slug']]['source'] == 'telefunken' and any(flag(c['slug'], h) in BAD['c'] for h in 'AB'))):
    kc = {k: c for k, c in cells.items() if f(c)}
    cur = {k: mean(c['cur'].values()) for k, c in kc.items()}; mat = {k: mean(c['mat'].values()) for k, c in kc.items()}
    print(f'  {lab}: ceiling {agg({k: c["ceiling"] for k, c in kc.items()})}')
    print(f'  {"":{len(lab)}s}  matched {agg(mat)}')
    print(f'  {"":{len(lab)}s}  current {agg(cur)}')
    print(f'  {"":{len(lab)}s}  m - c   {agg({k: mat[k] - cur[k] for k in kc if None not in (mat[k], cur[k])})}')
