"""Bleed robustness, results 1-3: subsets of step 3's 142 units by the held half's bleed flag."""
import sys, json, pathlib, collections
WT = pathlib.Path('/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT')
sys.path.insert(0, str(WT)); sys.path.insert(0, str(WT / 'research'))
from learn import song_readout as R, song_soundspace as SSP, knob_ceiling as K
OUT = pathlib.Path(__file__).parent
BT = json.loads((WT / 'docs/audits/bleed-2026-10-16/bleed-table.json').read_text())
units = SSP.e3_units()
ps = K.parts()
print('units', len(units), 'parts', len({u['slug'] for u in units}), 'classes', collections.Counter(ps[s]['gain_class'] for s in {u['slug'] for u in units}))
print('knob-ceiling parts not in units:', [s for s, v in BT.items() if v['set'] == 'knob-ceiling' and s not in {u['slug'] for u in units}])
def fl(u): return BT[u['slug']]['halves'][u['held']]['flag']
def src(u): return BT[u['slug']]['source']
# weak DI model: guitar share <= 0.75 on the held half (README's 'gtr')
WEAK = {'cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1', 'cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2',
        "cambridge-Today's_The_Day-ElecGtr10", 'cambridge-femme-elecgtr3', 'cambridge-Prodigal-ElecGtr5',
        'cambridge-get-out-of-bed-elecgtr1', 'telefunken-Long_Way_Home-GTR', 'telefunken-Blind_Spots-GTR'}  # README's weak-DI list
print('flag counts on held half:', collections.Counter((src(u), fl(u)) for u in units))
SUBS = {
 'a all': lambda u: True,
 'b no high': lambda u: fl(u) != 'high',
 'c no mod/high': lambda u: fl(u) not in ('moderate', 'high'),
 'd Cambridge': lambda u: src(u) == 'cambridge',
 'x Telefunken all': lambda u: src(u) == 'telefunken',
 'x Telefunken low halves': lambda u: src(u) == 'telefunken' and fl(u) not in ('moderate', 'high'),
 'x Telefunken mod/high halves': lambda u: src(u) == 'telefunken' and fl(u) in ('moderate', 'high'),
 'x Cambridge strong DI': lambda u: src(u) == 'cambridge' and u['slug'] not in WEAK,
 'x Cambridge weak DI': lambda u: src(u) == 'cambridge' and u['slug'] in WEAK,
 'x all, no mod/high, no weak DI': lambda u: fl(u) not in ('moderate', 'high') and u['slug'] not in WEAK,
}
def rd(st, n):
    f = lambda x: 'n/a' if x is None else f'{x:+.3f}'
    return {'mean': st['band_weighted_mean'], 'lo90': st['lo90'], 'hi90': st['hi90'], 'bands': st['bands'],
            'parts': st['parts'], 'units': n, 'bands_better': st['bands_negative'],
            'txt': f"{f(st['band_weighted_mean'])} [{f(st['lo90'])}, {f(st['hi90'])}] parts {st['parts']} bands {st['bands']} units {n} better-bands {st['bands_negative']}/{st['bands']}"}
def logstat(sub, a, b):
    f = R.log_vs(a, b)
    rows = R.part_rows(sub, f)
    return rd(R.bw(rows), sum(f(u) is not None for u in sub))
names = SSP.e3_names()
def pstat(sub, a, b):
    st = SSP.paired(sub, names[a], names[b])
    return rd(st, st['units'])
res = {}
for sn, keep in SUBS.items():
    sub = [u for u in units if keep(u)]
    r = res[sn] = {}
    r['1 K_S vs S'] = logstat(sub, 'K_S', 'S')
    r['2 A vs S'] = logstat(sub, 'A', 'S')
    r["2 3-C'shrink0.5 vs S"] = logstat(sub, "3-C'-shrink-0.5", 'S')
    r["2 3-C'shrink0.5 vs A"] = logstat(sub, "3-C'-shrink-0.5", 'A')
    r['2 K_S vs A'] = logstat(sub, 'K_S', 'A')
    for a in ('B0', 'B1', 'B2'):
        r[f'3 {a} vs S'] = pstat(sub, a, 'S')
    for a in ('B1', 'B2'):
        r[f'3 {a} vs B0'] = pstat(sub, a, 'B0')
    print(f'\n=== {sn} ===')
    for k, v in r.items(): print(f'  {k:24s} {v["txt"]}')
(OUT / 'r123.json').write_text(json.dumps(res, indent=1))

import math, statistics
print('\nwithin-part, mixed-flag parts: A vs S by held half (mean over amps)')
for slug in ('telefunken-Blind_Spots-GTR', 'telefunken-Fragments-GTR'):
    for h in 'AB':
        us = [u for u in units if u['slug'] == slug and u['held'] == h]
        vs = [math.log(u['d']['A'] / u['d']['S']) for u in us]
        print(f'  {slug} held {h} ({BT[slug]["halves"][h]["flag"]}, {BT[slug]["halves"][h]["bleed_db"]} dB): A vs S {statistics.fmean(vs):+.3f} n={len(vs)}; K_S vs S {statistics.fmean(math.log(u["d"]["K_S"]/u["d"]["S"]) for u in us):+.3f}')
print('\nper-part A vs S (mean over held units), with held flags')
for slug in sorted({u['slug'] for u in units}):
    us = [u for u in units if u['slug'] == slug]
    print(f'  {slug[:44]:44s} {ps[slug]["band"][:22]:22s} {ps[slug]["gain_class"]:6s} A {statistics.fmean(math.log(u["d"]["A"]/u["d"]["S"]) for u in us):+.3f} K_S {statistics.fmean(math.log(u["d"]["K_S"]/u["d"]["S"]) for u in us):+.3f} flags {sorted(collections.Counter(fl(u) for u in us).items())}')
