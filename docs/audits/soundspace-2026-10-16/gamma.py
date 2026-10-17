import sys, json, math, statistics, random
sys.path.insert(0,'.'); sys.path.insert(0,'research')
import numpy as np, torch
torch.set_num_threads(1)
from learn import song_soundspace as SP, song_relabel as RL
table = json.loads(RL.WEIGHTS.read_text())['weights']
sets = SP.load_sets()
rows = [r for r in SP.bank_rows() if r['i'] in sets]
out = {}
for f in range(4):
    net = SP.load_net2('B2', f)
    rs = [r for r in rows if r['fold'] != f]
    random.Random(f).shuffle(rs); rs = rs[:80]
    X, C = SP.load_features(rs, SP.feat_path)
    Mm = SP.member_arrays(rs, sets, table)
    with torch.no_grad():
        o = net(torch.tensor(X), torch.tensor(C))
        bt = {n: torch.tensor(v) for n, v in Mm.items()}
        L, joint, nact = SP.member_terms(o, bt)
        g = SP.responsibilities(bt['logw'], joint, nact)
        g_untemp = torch.softmax(bt['logw'] + joint, 1)
        w = torch.softmax(bt['logw'], 1)
    nm = (bt['logw'] > -1e30).sum(1)
    multi = nm > 1
    gm = g[multi]; wm = w[multi]; gu = g_untemp[multi]
    eff = lambda p: torch.exp(-(p.clamp_min(1e-12) * p.clamp_min(1e-12).log()).sum(1))
    out[f] = dict(n=int(multi.sum()), members=float(nm[multi].float().median()), gamma_max=float(gm.max(1).values.median()),
                  eff_gamma=float(eff(gm).median()), eff_w=float(eff(wm).median()), eff_untempered=float(eff(gu).median()),
                  gamma_label=float(gm[:, 0].median()), w_label=float(wm[:, 0].median()),
                  argmax_gamma_is_label=float((gm.argmax(1) == 0).float().mean()))
    print(f, out[f], flush=True)
