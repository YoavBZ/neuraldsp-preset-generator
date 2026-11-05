"""N6: did a model follow a capture it never heard, on a set it was not chosen on? FTm, FT and W on the first batch's units.

    $TORCH_PY -m learn.reads_capture OUT.json              # CPU only, from the repo root

Reads as `reads_v3`, whose functions these are, on the units `capture_labels.search_records` lets through: variant 0 of
the backed input, both halves, one value per unit, demeaned within (fold, amp, class, head). A unit is read by the fold
model that held out its DI (GOAT's fold of the DI's item), so neither the capture nor the performance was in that model's
real rows; W has no real rows. Clusters are creators: own against swap by t, r by the same bootstrap as GOAT's items, the
permutation among units within cells. All, crunch and clean. Nothing is read from V-real, the NS songs or the panel.
Control first: `read_fold` on GOAT's held records must give N1's stored r and swap total (`night2/reads-v3-ftm.json`)
within 1e-6, and `reads_v3.py` its sha.
"""
import hashlib, json, pathlib, pickle, sys
import numpy as np
sys.path.insert(0, '.')
from learn import capture_labels as L, direct_stems as DS, pipeline_fix as P, reads_v3 as R

MODELS = {'FTM': ('P2b-ftm-k{k}', 'final'), 'FT': ('P2b-ft-k{k}', 'final'), 'W': ('P2b-wide24', 'best')}
PAIRS = (('FTM', 'W'), ('FTM', 'FT'))
READS_V3_SHA = 'a04785f3a4838ae2'
CLASSES = ('all', 'crunch', 'clean')


def fold_of(unit, item_fold):
    """The fold that held out a capture unit's DI. item_fold: {GOAT item: fold}."""
    return item_fold[unit['di_item']]


def read_fold(k, recs, by_unit):
    held = P.record_rows(recs, by_unit, 0)
    d = R.make(held)
    c, cm, s, sm, kk, km, _ = d.Y
    rows = [{'fold': k, 'set': 'CAP', 'cluster': by_unit[r['unit']].get('creator') or r['di'], 'rec': r['rig'], 'amp': h['amp'],
             'cls': h['cls'], 'c': c[j], 'cm': cm[j]} for j, (h, r) in enumerate(zip(held, recs))]
    for label, (run, which) in MODELS.items():
        outs = [R.both_halves(P.load_run(run.format(k=k), sd, which)[0], d) for sd in R.SEEDS]
        med = np.mean([np.mean([DS.mixture_median(*h[:3]) for h in o], 0) for o in outs], 0)
        for j, row in enumerate(rows):
            sk, ss, sc = R.searched(row['amp'], row['cls'])
            args = (c[j], cm[j] * sk, s[j], sm[j] * ss, kk[j], km[j] * sc)
            mine = np.mean([[R.loss(h, j, *args) for h in o] for o in outs], (0, 1))
            others = [i for i, q in enumerate(rows) if i != j and (q['amp'], q['cls']) == (row['amp'], row['cls']) and q['cluster'] != row['cluster']]
            row[f'{label}_ans'] = med[j]
            row[f'{label}_swap'] = (mine - np.mean([[[R.loss(h, i, *args) for h in o] for o in outs] for i in others], (0, 1, 2))
                                    if others else None)
    return rows


def control(grecs, gunits):
    """The copied loop must give N1's stored r on GOAT's held records."""
    if hashlib.sha256(pathlib.Path(R.__file__).read_bytes()).hexdigest()[:16] != READS_V3_SHA:
        raise SystemExit('control: reads_v3.py is not the file the plan states')
    rows = []
    for k in range(4):
        rows += read_fold(k, [r for r in grecs if gunits[r['unit']]['fold'] == k], gunits)
    stored = json.loads((P.out_dir() / 'night2' / 'reads-v3-ftm.json').read_text())
    for label in MODELS:
        got = R.corr(R.blocks(rows, label))
        for g in R.GROUPS:
            want = stored[f'GOAT/{label}']['r'][g]['r']
            if abs(got[g][0] - want) > 1e-6:
                raise SystemExit(f'control: {label} {g} {got[g][0]:+.6f} against stored {want:+.6f}')
        swap = R.t_row([(r['cluster'], float(r[f'{label}_swap'].sum())) for r in rows if r[f'{label}_swap'] is not None])
        want = stored[f'GOAT/{label}']['swap']['total']['mean']
        if abs(swap['mean'] - want) > 1e-6:
            raise SystemExit(f"control: {label} swap {swap['mean']:+.6f} against stored {want:+.6f}")
    print('CONTROL OK', flush=True)


def report(rows, perms=R.PERMS):
    res, rng = {}, np.random.default_rng(R.RNG_SEED)
    for cls in CLASSES:
        S = [r for r in rows if cls in ('all', r['cls'])]
        iv = R.goat_intervals(S, list(MODELS), PAIRS)
        for label in MODELS:
            r_, b = R.read_r(S, label, perms, rng)
            for g in R.GROUPS:
                r_[g]['boot90'] = iv[(label, g)]
                lo = [R.corr(b, drop=c)[g][0] for c in sorted({r['cluster'] for r in S})]
                r_[g]['leave_one_creator_out'] = [float(min(lo)), float(max(lo))]
            swap = [r for r in S if r[f'{label}_swap'] is not None]
            res[f'{cls}/{label}'] = {'r': r_, 'r_no_limit_labels': R.read_r(S, label, perms, rng, drop_limits=True)[0],
                                     'swap_total': R.t_row([(r['cluster'], float(r[f'{label}_swap'].sum())) for r in swap]),
                                     'swap': {q: R.t_row([(r['cluster'], float(r[f'{label}_swap'][i])) for r in swap])
                                              for i, q in enumerate(('knob', 'switch', 'mic'))},
                                     'parts': len(S), 'creators': len({r['cluster'] for r in S})}
        res[f'{cls}/pairs'] = {f'{a}-{b}': {g: iv[(f'{a}-{b}', g)] for g in R.GROUPS} for a, b in PAIRS}
    return res


def main(out):
    P.require('phase_n6')
    recs = L.search_records()
    by_unit = {u['unit']: u for u in L.units_of()}
    grecs, gunits, _ = P.goat_labels()
    control(grecs, gunits)
    item_fold = {p['item']: p['fold'] for p in gunits.values()}
    rows = []
    for k in range(4):
        mine = [r for u, r in sorted(recs.items()) if fold_of(by_unit[u], item_fold) == k]
        rows += read_fold(k, mine, by_unit)
        print('fold', k, len(mine), 'done', flush=True)
    pickle.dump(rows, open(out + '.rows.pkl', 'wb'))
    res = report(rows)
    json.dump(res, open(out, 'w'), indent=1)
    for cls in CLASSES:
        for label in MODELS:
            q = res[f'{cls}/{label}']
            print(cls, label, q['parts'], '  '.join(f"{g} {q['r'][g]['r']:+.3f} {q['r'][g]['boot90']}" for g in R.GROUPS), 'swap', q['swap_total'])


if __name__ == '__main__':
    main(sys.argv[1])
