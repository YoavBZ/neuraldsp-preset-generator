import sys, glob
sys.path.insert(0, '/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT')
sys.path.insert(0, '/private/tmp/claude-501/-Users-yoavbz-projects-neuraldsp-preset-generator/67cfc004-f421-4d92-9cce-0e70317476ec/scratchpad/lag-audit')
import numpy as np
from gcc import xc, peaks, K, CR
H = K.HOME / 'learn'
ps = K.parts()
for s in sys.argv[1:]:
    p = ps[s]
    ref = CR.mono(p['crop'] / 'reference.wav'); raw = CR.mono(p['crop'] / 'di.wav'); meas = K.measure_di(p)
    print('==', s, 'len', len(raw))
    for f in [H/'direc/phase2/measure'/s/'di.npy', H/'direc/songs-check/measfix'/s/'di.npy', H/'direc/songs-check/stem'/s/'di.npy', H/'direc/phase2/flatref'/s/'di.npy']:
        if not f.exists(): print('  missing', f); continue
        d = np.load(f).astype(np.float64).ravel()
        tag = '/'.join(f.parts[-3:-2])
        print(f"  {tag:10s} len={len(d)} ref~it {peaks(*xc(ref, d))}  it~rawDI {peaks(*xc(d, raw))}  it~K.measure_di {peaks(*xc(d, meas))}")
