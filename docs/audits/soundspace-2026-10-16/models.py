import sys, json, math, pickle, pathlib, statistics
sys.path.insert(0,'.'); sys.path.insert(0,'research')
import numpy as np, torch
torch.set_num_threads(1)
from learn import song_soundspace as SP, song_diag as D, knob_ceiling as K, song_bank as B, arm_a_levers as AL, song_model as M
OUTD = pathlib.Path(sys.argv[1])
menu = D._menu(); ps, fo = K.parts(), B.folds()
nets = {a: SP._nets_for(a) for a in ('B0','B1','B2')}
flat = json.loads((SP.DIAG/'flat.json').read_text())
preds = json.loads((SP.SS_OUT/'armB'/'predictions.json').read_text())['cells']
ev = SP.SS_OUT/'eval-features'
def collapse(h, amp):
    names = {d.name for d in K.space(amp)}
    aud = np.array([(n in names) and (n not in flat.get(amp, [])) for n in M.CONT])
    pi = np.asarray(h['pi']); 
    return dict(sep=D.mode_separation(h, aud), top_w=float(pi.max()), eff=float(np.exp(-(pi*np.log(np.maximum(pi,1e-12))).sum())))
# ---- E2 per direction + collapse on songs
e2 = []; songcol = []
for slug, amp, search, held in SP.e3_cells():
    kc = json.loads((K.OUT/'cells'/slug/amp/'result.json').read_text())
    run = kc['runs'][search]
    part = ps[slug]; cls = part['gain_class']; _, S = D._S(menu, amp, cls)
    dz = np.load(ev/f'{slug}.npz'); dzo = np.load(ev/f"{preds[f'{slug}|{amp}|{search}']['shuffled0']['source']}.npz")
    fold, band = fo[part['band']], part['band']
    rec = {'slug': slug, 'band': band, 'amp': amp, 'cls': cls, 'search': search}
    hs = {a: SP.heads(nets[a][fold], dz[f'feat{search}'], dz[f'lufs{search}'], amp, cls) for a in nets}
    for a in nets: songcol.append({**rec, 'arm': a, **collapse(hs[a], amp)})
    if 'K_S' in run:
        traj, _ = AL.replay_ks(amp, S, run['K_S']['evals'], search)
        xs = [x for x, _ in traj]; hv = [d[held] for _, d in traj]; sv = [d[search] for _, d in traj]
        rec['start_held'] = run['K_S']['start_held']; rec['hv'] = hv; rec['sv'] = sv
        for a in nets:
            kind = 'truncated' if a == 'B0' else 'censored'
            ho = SP.heads(nets[a][fold], dzo[f'feat{search}'], dzo[f'lufs{search}'], amp, cls)
            rec['sc_'+a] = [SP.box_logprob(hs[a], x, amp, kind) for x in xs]
            rec['so_'+a] = [SP.box_logprob(ho, x, amp, kind) for x in xs]
            if a == 'B0':
                rec['sc_B0cens'] = [SP.box_logprob(hs[a], x, amp, 'censored') for x in xs]
        e2.append(rec)
print('e2 directions', len(e2))
# ---- collapse on E1 targets
targets = json.loads((SP.DIAG/'targets.json').read_text())
tcol = []
for t in targets:
    dzt = np.load(SP.DIAG/'targets'/f"{t['i']:03d}-features.npz")
    for v in SP.VIEWS:
        for h in 'AB':
            for a in nets:
                hh = SP.heads(nets[a][t['fold']], dzt[f'{v}_feat{h}'], dzt[f'{v}_lufs{h}'], t['amp'], t['class'])
                tcol.append({'t': t['i'], 'band': t['band'], 'fold': t['fold'], 'view': v, 'arm': a, **collapse(hh, t['amp'])})
pickle.dump({'e2': e2, 'songcol': songcol, 'tcol': tcol}, open(OUTD/'models.pkl', 'wb'))
print('done')
