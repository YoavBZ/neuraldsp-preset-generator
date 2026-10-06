"""Exploratory re-scoring of the DI-robustness picks under the average-guitar question (docs/di-robustness-results.md)."""
import sys,json,math,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'research'))
import kill_tests as K, render_preset_panel as RP
from learn import di_robustness as D
from analysis.aligned import aligned_distance
from concurrent.futures import ProcessPoolExecutor
out=pathlib.Path('~/ndsp-presets/learn/di-robust').expanduser()
panel=json.loads((D.KILL/'pr12-clean'/'index.json').read_text())
names=sorted({r['candidate'] for r in panel['rows'] if 'file' in r and r['candidate']!='template'})
parts,band,lags,_=D.k1_parts()
def job(p):
    import numpy as np
    ref=D.mono(D.CROPS/p/'reference.wav'); adi=np.load(out/'di'/f'{p}--avg.npy')
    o={}
    for bs in D.BAND_SETS:
        for half,(a,b) in (('A',D.HALF_A),('B',D.HALF_B)):
            o[f'{bs}|{half}']={n:aligned_distance(ref,D.mono(out/'renders'/'avg'/p/f'{RP._slug(n)}.wav'),adi,lag=lags[p],render_latency=52,start_s=a,end_s=b,bands=bs).distance for n in names}
    return p,o
if __name__=='__main__':
    res=json.loads((out/'result.json').read_text())
    with ProcessPoolExecutor(4) as ex: S=dict(ex.map(job,parts))
    json.dump(S,open(out/'avg-yardstick-distances.json','w'))
    for bs in D.BAND_SETS:
        for v in ('true','swap','mild','avg','avg+mild','flatstem'):
            rows=[]
            for r in res['rows'].get(f'{v}|{bs}',[]):
                B=S[r['part']][f'{bs}|B']
                if B.get(r['pick']) and B.get('template+R'):
                    rows.append(dict(band=r['band'],x=math.log(B[r['pick']])-math.log(B['template+R'])))
            st=K.band_stat(rows,'x'); print(f"{bs:9s} picks from {v:9s} scored via avg-guitar DI: {st['band_median_log_ratio']:+.3f} p {st['sign_flip_p_two_sided']} parts better {st['parts_better']}/{st['parts']}")
        rows=[]
        for p in parts:
            A,B=S[p][f'{bs}|A'],S[p][f'{bs}|B']
            okA={n:d for n,d in A.items() if d}
            if not okA or not B.get('template+R'): continue
            k=min(okA,key=okA.get)
            if B.get(k): rows.append(dict(band=band[p],x=math.log(B[k])-math.log(B['template+R'])))
        st=K.band_stat(rows,'x'); print(f"{bs:9s} product-yardstick oracle (choose & score via avg DI): {st['band_median_log_ratio']:+.3f} p {st['sign_flip_p_two_sided']}")
