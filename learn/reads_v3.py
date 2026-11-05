"""Per-track reads of models on held BKS and GOAT rows: did the answer follow THIS recording, beyond its cell?

    $TORCH_PY reads.py OUT.json FT=P2b-ft-k{k}:final W=P2b-wide24:best       # run from the repo root; CPU only

Each MODEL is LABEL=RUN:WHICH, RUN holding {k} for fold-held runs, loaded by `pipeline_fix.load_run` for both seeds.
Rows are each fold's held records (`dfix_records`), read through variant 0 of the real input (`dfix_input_path`),
both halves. Nothing is read from plugin rows, NS, V-real, the panel or captures.

Two reads, chosen because neither can be flattered by a good centre:
- **Own against swap.** The searched-head loss of a row under its own output, minus under the output of another row of
  the same fold, set and (amp, class) from a different cluster. Both sides use the model's own output shape, so unlike
  an NLL against a lookup it does not flip with the comparator (labels sit on the search's 0.25 grid). Negative: its own
  answer fits better. Mean of cluster means, 90% t interval. Clusters: DI on BKS, item on GOAT.
- **Within-cell r.** The real readout (each knob's mixture median, seeds averaged, `full_space.readout`'s a2), against
  the label on searched knobs, one value per (recording, fold, amp, class, head), demeaned within (fold, amp, class,
  head), by group. The null permutes labels among recordings within those cells.

Demean within fold: pooling held folds gives a no-audio answer r of -0.14 to -0.51, since each fold's centre comes from
the other folds. Do not read NLL against a lookup, or a pooled r, as evidence of reading.

Searched head (per record): its (module, key) in `K.space(amp, S)` and sounding in the label, S the class's S.
"""
import collections, itertools, json, math, pickle, re, sys
import numpy as np, torch
sys.path.insert(0, '.')
torch.set_num_threads(1)
from learn import arm_a_levers as L, direct_stems as DS, full_space as F, knob_ceiling as K
from learn import local_objective as LO, pipeline_fix as P, pretrain_set as PS, trusted_data_t3 as T3

SEEDS, PERMS, RNG_SEED, BOOT_DRAWS = (20261042, 20261043), 2000, 20261107, 4000
GROUPS = {'drive': ('inputGain', 'pr12Volume', 'sw50rVolume', 'sw50rLevel', 'ac20Volume', 'ac20Power'),
          'tone': ('pr12Treble', 'pr12Bass', 'sw50rTreble', 'sw50rMid', 'sw50rBass', 'ac20Cut'),
          'cab': ('leftCabPosition', 'rightCabPosition', 'leftCabDistance', 'rightCabDistance', 'rightCabMicLevel')}
MS, ENC, D = L.menu_S(), T3.encode_for(T3.FULL), F.by_name()
HEADS = {g: [j for j, n in enumerate(F.CONT) if D[n].key in v] for g, v in GROUPS.items()}
assert not set.intersection(*(set(v) for v in HEADS.values()))
assert sum(len(v) for v in HEADS.values()) == sum(len(v) for v in GROUPS.values())      # every key found, none twice


def searched(amp, cls):
    s = {(d.module, d.key) for d in K.space(amp, MS[amp][cls][1])}
    return [np.array([(D[n].module, D[n].key) in s for n in names], float) for names in (F.CONT, F.SW, F.CAT)]


def make(rows):
    d = P.RungData.__new__(P.RungData)
    d.rows, d.aug, n = rows, False, len(rows)
    d.X, d.L = np.zeros((n, 2, 96, 446), np.uint8), np.zeros((n, 2), np.float32)
    for j, r in enumerate(rows):
        z = np.load(P.dfix_input_path(r['real'], 0))
        a, b = ('mA', 'mB') if 'mA' in z.files else ('sA', 'sB')
        d.X[j, 0], d.X[j, 1], d.L[j] = z[a], z[b], z['lufs']
    d.Y = [np.stack(z) for z in zip(*(ENC(r['label']) for r in rows))]
    d.centres, d.applied = DS.mel_centres_hz(), {}
    return d


def outputs(net, d):
    o = [[] for _ in range(5)]
    with torch.no_grad():
        for j in range(0, len(d.rows), 64):
            x, c, _ = d.batch(np.arange(j, min(j + 64, len(d.rows))), -1, 'cpu')
            r = net(x, c)
            for q in range(4):
                o[q].append(r[q].numpy())
            o[4].append(np.stack([z.numpy() for z in r[4]], 1))
    return [np.concatenate(z) for z in o]


def both_halves(net, d):
    orig, a = DS.half_of, outputs(net, d)
    DS.half_of = lambda i, e: 1 - orig(i, e)
    try:
        return a, outputs(net, d)
    finally:
        DS.half_of = orig


def lse(a, ax):
    m = a.max(axis=ax, keepdims=True)
    return (m + np.log(np.exp(a - m).sum(axis=ax, keepdims=True))).squeeze(ax)


def loss(o, j, c, km_, s, sm_, k, mm_):
    """(knob marginal NLL, switch BCE, mic CE) of a label under row j's output, means over the masked heads."""
    lp = -0.5 * ((c - o[1][j]) / np.exp(o[2][j])) ** 2 - o[2][j] - 0.5 * math.log(2 * math.pi)
    kn = -lse(o[0][j][:, None] + lp, 0)
    p = o[3][j]
    bce = np.maximum(p, 0) - p * s + np.log1p(np.exp(-np.abs(p)))
    lg = o[4][j] - lse(o[4][j], 1)[:, None]
    ce = -lg[np.arange(len(k)), k]
    return np.array([(v * m).sum() / max(m.sum(), 1) for v, m in ((kn, km_), (bce, sm_), (ce, mm_))])


def read_fold(k, models, brecs, by_unit, folds, grecs, gunits):
    _, held, _ = P.dfix_rows_of(brecs, by_unit, folds, grecs, gunits, k)
    _, _, bh, gh = P.dfix_records(brecs, by_unit, folds, grecs, gunits, k)
    recs = bh + gh
    d = make(held)
    c, cm, s, sm, kk, km, _ = d.Y
    rows = [{'fold': k, 'set': 'BKS' if j < len(bh) else 'GOAT', 'cluster': r['di'], 'rec': r['rig'], 'amp': h['amp'],
             'cls': h['cls'], 'c': c[j], 'cm': cm[j]} for j, (h, r) in enumerate(zip(held, recs))]
    for label, (run, which) in models.items():
        name = run.format(k=k)
        outs = [both_halves(P.load_run(name, sd, which)[0], d) for sd in SEEDS]
        med = np.mean([np.mean([DS.mixture_median(*h[:3]) for h in o], 0) for o in outs], 0)
        for j, row in enumerate(rows):
            sk, ss, sc = searched(row['amp'], row['cls'])
            args = (c[j], cm[j] * sk, s[j], sm[j] * ss, kk[j], km[j] * sc)
            mine = np.mean([[loss(h, j, *args) for h in o] for o in outs], (0, 1))
            others = [i for i, q in enumerate(rows) if i != j and (q['amp'], q['cls'], q['set']) == (row['amp'], row['cls'], row['set'])
                      and q['cluster'] != row['cluster']]
            row[f'{label}_ans'] = med[j]
            row[f'{label}_swap'] = (mine - np.mean([[[loss(h, i, *args) for h in o] for o in outs] for i in others], (0, 1, 2))
                                    if others else None)
    return rows


def t_row(pairs):
    g = collections.defaultdict(list)
    for c, v in pairs:
        g[c].append(v)
    m = np.array([np.mean(v) for v in g.values()])
    n = len(m)
    h = PS.t90(n - 1) * m.std(ddof=1) / math.sqrt(n)
    return {'mean': float(m.mean()), 'lo90': float(m.mean() - h), 'hi90': float(m.mean() + h), 'better': int((m < 0).sum()), 'clusters': n}


def blocks(rows, label, drop_limits=False):
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        cells[(r['fold'], r['amp'], r['cls'])][r['rec']].append(r)
    out = []
    for (_, amp, cls), recs in cells.items():
        use = np.nonzero(searched(amp, cls)[0])[0]
        items = []
        for rig, rr in sorted(recs.items()):
            C, M = np.array([r['c'] for r in rr], float), np.array([r['cm'] for r in rr], float)
            if drop_limits:
                M = M * ~((C < 1e-4) | (C > 1 - 1e-4))
            lab = np.where(M.sum(0) > 0, (C * M).sum(0) / np.maximum(M.sum(0), 1), np.nan)
            items.append((np.mean([r[f'{label}_ans'] for r in rr], 0), lab, rr[0]['cluster'], rig))
        if len(items) >= 2:
            out.append((use, items, amp))
    return out


def corr(b, rng=None, drop=None, fixed=None):
    res = {}
    for g in GROUPS:
        xs, ys, orders, by_head = [], [], dict(fixed or {}), collections.defaultdict(lambda: ([], []))
        for use, items, amp in b:
            it = [t for t in items if t[2] != drop]
            if len(it) < 2:
                continue
            key = tuple(t[3] for t in it)                # BKS: the same recordings on all 3 amps, so one order; GOAT: unique per cell
            if key not in orders:
                orders[key] = rng.permutation(len(it)) if rng is not None else np.arange(len(it))
            order = orders[key]
            for j in set(use.tolist()) & set(HEADS[g]):
                a, c = np.array([t[0][j] for t in it]), np.array([it[o][1][j] for o in order])
                ok = ~np.isnan(c)
                if ok.sum() >= 2:
                    xs.append(a[ok] - a[ok].mean())
                    ys.append(c[ok] - c[ok].mean())
                    by_head[(amp, j)][0].append(xs[-1])
                    by_head[(amp, j)][1].append(ys[-1])
        if not xs:                                       # a single block can hold no head of a group
            continue
        x, y = np.concatenate(xs), np.concatenate(ys)
        z = [(np.concatenate(p), np.concatenate(q)) for p, q in by_head.values()]
        zx = np.concatenate([p / (p.std() + 1e-12) for p, _ in z])
        zy = np.concatenate([q / (q.std() + 1e-12) for _, q in z])
        res[g] = (float(x @ y / math.sqrt((x @ x) * (y @ y) + 1e-12)), len(x), float(x.std() / (y.std() + 1e-12)),
                  float(zx @ zy / math.sqrt((zx @ zx) * (zy @ zy) + 1e-12)))
    return res


def exact_p(b):
    """BKS's exact upper-tail p per group: every joint order of recordings, the same order on a recording set's amps."""
    sets = sorted({tuple(t[3] for t in items) for _, items, _ in b})
    perms = [list(itertools.permutations(range(len(s)))) for s in sets]
    total = math.prod(len(q) for q in perms)
    if total > 100_000:
        raise SystemExit(f'{total} arrangements: the recording sets are not what BKS should give')
    base, vals = corr(b), collections.defaultdict(list)
    for combo in itertools.product(*perms):
        for g, v in corr(b, fixed={s: np.array(c) for s, c in zip(sets, combo)}).items():
            vals[g].append(v[0])
    return {g: float((np.array(v) >= base[g][0] - 1e-12).mean()) for g, v in vals.items()}, total


def flat(S, g):
    """(row, head) pairs of group g on searched sounding heads, with their (fold, amp, class, head) cell ids."""
    I, J, C, cid = [], [], [], {}
    for i, r in enumerate(S):
        sk = searched(r['amp'], r['cls'])[0]
        for j in HEADS[g]:
            if sk[j] and r['cm'][j] > 0:
                I.append(i), J.append(j), C.append(cid.setdefault((r['fold'], r['amp'], r['cls'], j), len(cid)))
    return np.array(I), np.array(J), np.array(C), len(cid)


def wr(x, y, w, C, n):
    """Weighted within-cell r."""
    sw = np.bincount(C, w, n)
    sw[sw == 0] = 1
    a, b = x - (np.bincount(C, w * x, n) / sw)[C], y - (np.bincount(C, w * y, n) / sw)[C]
    return (w * a * b).sum() / math.sqrt((w * a * a).sum() * (w * b * b).sum() + 1e-15)


def goat_intervals(S, labels, pairs, draws=BOOT_DRAWS):
    """GOAT's 90% item-bootstrap intervals on r, and on paired differences from the same draws."""
    items = {u: i for i, u in enumerate(sorted({r['cluster'] for r in S}))}
    of = np.array([items[r['cluster']] for r in S])
    W = np.random.default_rng(RNG_SEED + 1).multinomial(len(items), np.ones(len(items)) / len(items), size=draws)
    out = {}
    for g in GROUPS:
        I, J, C, n = flat(S, g)
        y = np.array([S[i]['c'][j] for i, j in zip(I, J)], float)
        val = {m: np.array([wr(np.array([S[i][f'{m}_ans'][j] for i, j in zip(I, J)], float), y, w[of[I]].astype(float), C, n) for w in W]) for m in labels}
        for m in labels:
            out[(m, g)] = [float(q) for q in np.percentile(val[m], [5, 95])]
        for a, b in pairs:
            d = val[a] - val[b]
            whole = wr(np.array([S[i][f'{a}_ans'][j] for i, j in zip(I, J)], float), y, np.ones(len(y)), C, n) \
                - wr(np.array([S[i][f'{b}_ans'][j] for i, j in zip(I, J)], float), y, np.ones(len(y)), C, n)
            out[(f'{a}-{b}', g)] = {'diff': float(whole), 'lo90': float(np.percentile(d, 5)), 'hi90': float(np.percentile(d, 95))}
    return out


def bks_pair(S, a, b):
    """BKS's paired difference: delete-one-block jackknife over (fold, class), t(3). Four blocks allow no decision."""
    recs = collections.defaultdict(set)
    for r in S:
        recs[(r['fold'], r['cls'])].add(r['rec'])
    keys = sorted(k for k, v in recs.items() if len(v) >= 2)        # a within-cell read needs 2 recordings
    if len(keys) != 4:
        raise SystemExit(f'{len(keys)} usable BKS blocks, not 4: t(3) does not apply')

    def diff(rows, g):
        p, q = corr(blocks(rows, a)).get(g), corr(blocks(rows, b)).get(g)
        return None if p is None or q is None else p[0] - q[0]

    out = {}
    for g in GROUPS:
        jk = np.array([diff([r for r in S if (r['fold'], r['cls']) != k], g) for k in keys], float)
        h = 2.353 * math.sqrt(3 / 4 * ((jk - jk.mean()) ** 2).sum())                       # t(3), 90%
        whole = diff(S, g)
        per = [v for v in (diff([r for r in S if (r['fold'], r['cls']) == k], g) for k in keys) if v is not None]
        if len(per) != 4:
            raise SystemExit(f'{g} is in {len(per)} of the 4 BKS blocks: the jackknife does not apply')
        out[g] = {'diff': whole, 'lo90': whole - h, 'hi90': whole + h, 'blocks_positive': sum(v > 0 for v in per), 'blocks_with_data': len(per)}
    return out


def rig_table(S):
    """BKS's no-audio comparator: each held row's answer is the mean label of the other folds' rows of its song, amp, class and rig letter
    (its song, amp and class if that letter has none). No audio, so any r it reaches needs no reading."""
    name = lambda r: (r['cluster'].split('/')[1], re.search(r'Gtr\d([cde])', r['rec']).group(1))
    for r in S:
        tr = [q for q in S if q['fold'] != r['fold'] and q['amp'] == r['amp'] and q['cls'] == r['cls'] and name(q)[0] == name(r)[0]]
        use = [q for q in tr if name(q)[1] == name(r)[1]] or tr
        C, M = np.array([q['c'] for q in use], float), np.array([q['cm'] for q in use], float)
        r['TAB_ans'] = np.where(M.sum(0) > 0, (C * M).sum(0) / np.maximum(M.sum(0), 1), 0.5)


def read_r(S, label, perms, rng, **kw):
    b = blocks(S, label, **kw)
    base, nul = corr(b), collections.defaultdict(list)
    for _ in range(perms):
        for g, v in corr(b, rng).items():
            nul[g].append(v)
    out = {}
    for g in GROUPS:
        q = np.array(nul[g])
        out[g] = {'r': base[g][0], 'null5': float(np.percentile(q[:, 0], 5)), 'null95': float(np.percentile(q[:, 0], 95)),
                  'p': float((q[:, 0] >= base[g][0]).mean()), 'p_low': float((q[:, 0] <= base[g][0]).mean()), 'sd_ratio': base[g][2], 'n': base[g][1],
                  'r_std': base[g][3], 'p_std': float((q[:, 3] >= base[g][3]).mean())}
    return out, b


def report(rows, models, perms=PERMS, pairs=()):
    res, rng = {}, np.random.default_rng(RNG_SEED)
    for st in ('BKS', 'GOAT'):
        S = [r for r in rows if r['set'] == st]
        n = perms[st] if isinstance(perms, dict) else perms
        if st == 'BKS':
            rig_table(S)
            res['BKS/rig-table'] = {'r': read_r(S, 'TAB', n, rng)[0]}
            ex, tot = exact_p(blocks(S, 'TAB'))
            print('BKS exact arrangements', tot, flush=True)
            for g in GROUPS:
                res['BKS/rig-table']['r'][g]['p_exact'] = ex[g]
        for label in models:
            P_ = [r for r in S if r[f'{label}_swap'] is not None]
            unit = (lambda r: r['fold']) if st == 'BKS' else (lambda r: r['cluster'])    # BKS's DIs swap in reciprocal pairs: one pair, one unit
            r_, b = read_r(S, label, n, rng)
            row = {'swap': {q: t_row([(unit(r), r[f'{label}_swap'][i]) for r in P_]) for i, q in enumerate(('knob', 'switch', 'mic'))}, 'r': r_,
                   'r_no_limit_labels': read_r(S, label, n, rng, drop_limits=True)[0]}
            row['swap']['total'] = t_row([(unit(r), float(r[f'{label}_swap'].sum())) for r in P_])
            if st == 'BKS':
                ex, _ = exact_p(b)
                for g in GROUPS:
                    row['r'][g]['p_exact'] = ex[g]
                    lo = [corr(b, drop=c)[g][0] for c in sorted({r['cluster'] for r in S})]
                    row['r'][g]['lodo'] = [float(min(lo)), float(max(lo))]
            res[f'{st}/{label}'] = row
            t = row['swap']['total']
            print(f"{st:4s} {label:4s} swap total {t['mean']:+.3f} [{t['lo90']:+.3f}, {t['hi90']:+.3f}] {t['better']}/{t['clusters']}  knob {row['swap']['knob']['mean']:+.3f} mic {row['swap']['mic']['mean']:+.3f}  "
                  + '  '.join(f"{g} {row['r'][g]['r']:+.3f} (p {row['r'][g]['p']:.3f}, low {row['r'][g]['p_low']:.3f}, std {row['r'][g]['r_std']:+.3f})" for g in GROUPS), flush=True)
        if st == 'GOAT':
            iv = goat_intervals(S, list(models), pairs)
            for m in models:
                for g in GROUPS:
                    res[f'GOAT/{m}']['r'][g]['boot90'] = iv[(m, g)]
            res['GOAT/pairs'] = {f'{a}-{b}': {g: iv[(f'{a}-{b}', g)] for g in GROUPS} for a, b in pairs}
        else:
            res['BKS/pairs'] = {f'{a}-{b}': bks_pair(S, a, b) for a, b in pairs}
    return res


def main(out, specs):
    pairs = [tuple(s.split('-', 1)) for s in specs if '=' not in s]
    models = {s.split('=')[0]: tuple(s.split('=')[1].split(':')) for s in specs if '=' in s}
    brecs, by_unit, folds = P.real_labels(2)
    grecs, gunits, _ = P.goat_labels()
    rows = []
    for k in range(4):
        rows += read_fold(k, models, brecs, by_unit, folds, grecs, gunits)
        print('fold', k, 'done', flush=True)
    pickle.dump(rows, open(out + '.rows.pkl', 'wb'))
    res = report(rows, models, pairs=pairs)
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
