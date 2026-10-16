import sys, json
sys.path.insert(0, '/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT')
sys.path.insert(0, '/private/tmp/claude-501/-Users-yoavbz-projects-neuraldsp-preset-generator/67cfc004-f421-4d92-9cce-0e70317476ec/scratchpad/lag-audit')
import numpy as np, soundfile as sf
from gcc import xc, peaks, K, CR
ps = K.parts()
out = {}
for s in sys.argv[1:]:
    p = ps[s]; L = p['judge_lag']
    ref = CR.mono(p['crop'] / 'reference.wav'); di = K.measure_di(p)
    for amp in ('ac20', 'pr12', 'sw50r'):
        d = K.OUT / 'cells' / s / amp
        if not (d / 'result.json').exists(): continue
        res = json.loads((d / 'result.json').read_text())
        for tag in ('K_S-A', 'K_M-A'):
            f = d / f'{tag}.flac'
            if not f.exists(): continue
            y, _ = sf.read(f); y = y.mean(1) if y.ndim == 2 else y
            g = peaks(*xc(ref, y), k=1)[0][0]
            run = res['runs']['A'][tag.split('-')[0]]
            lags = {'stored': L, 'gcc': g, 'stored-25': L - 25, 'stored+25': L + 25, 'stored-100': L - 100,
                    'stored+100': L + 100, 'reviewer(-54)': -54}
            row = {k: K.judge(ref, y, di, v) for k, v in lags.items()}
            print(f"{s[:38]:38s} {amp:5s} {tag} stored A={run['search']:.4f} B={run['held']:.4f} | gcc={g}")
            for k, v in lags.items():
                print(f"     {k:14s} lag={v:5d}  A={row[k]['A']:.4f}  B={row[k]['B']:.4f}")
            out[f"{s}|{amp}|{tag}"] = {'stored_result': [run['search'], run['held']], 'lags': lags, 'judge': row}
json.dump(out, open('/private/tmp/claude-501/-Users-yoavbz-projects-neuraldsp-preset-generator/67cfc004-f421-4d92-9cce-0e70317476ec/scratchpad/lag-audit/judge_lags_%s.json' % sys.argv[1][:20], 'w'), indent=1, default=float)
