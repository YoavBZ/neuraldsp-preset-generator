"""Independent stopped-attempt verification. No project numerical imports.

Only --derive performs scientific computation; --compare consumes its sealed
readback. Actual waveform access is restricted to explicitly listed members.
"""
import argparse
import gzip
import hashlib
import json
import math
import os
import platform
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import traceback

ROOT = Path('/Users/yoavbz/projects/neuraldsp-preset-generator')
BASE = ROOT / 'tmp'
STEM = 'di-morgan-processing-independent'
SOURCE = BASE / (STEM + '.py')
BLIND = BASE / (STEM + '-blind.py')
TRANSCRIPT = BASE / (STEM + '-transcript.jsonl')
DERIVATION = BASE / (STEM + '-derivation.json')
BARRIER = BASE / (STEM + '-read-barrier.json')
ARRAYS = BASE / (STEM + '-arrays')
HASHES = BASE / (STEM + '-array-hashes.json')
REPORT = BASE / 'di-morgan-processing-verification.json'
MD = BASE / 'di-morgan-processing-verification.md'
RUN = BASE / 'di-morgan-processing-control-20261009'
HEAD = 'df68127c2f0806407f5a5d018cf54844e876223a'
T0 = time.monotonic()
checks = []

def event(kind, **kw):
    with TRANSCRIPT.open('a') as f:
        f.write(json.dumps({'unix': time.time(), 'elapsed': time.monotonic()-T0,
                            'event': kind, **kw}, allow_nan=False) + '\n')
        f.flush()
        os.fsync(f.fileno())

def digest(data):
    return hashlib.sha256(data).hexdigest()

def sha(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('symlink rejected: ' + str(path))
    with path.open('rb') as f:
        state = hashlib.sha256()
        for chunk in iter(lambda: f.read(1024*1024), b''):
            state.update(chunk)
        h = state.hexdigest()
    event('hash_only', path=str(path), sha256=h)
    return h

def read(path):
    event('content_read', path=str(path))
    return Path(path).read_bytes()

def js(path):
    return json.loads(read(path), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

def save(path, obj):
    with Path(path).open('w') as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    event('durable_write', path=str(path), sha256=sha(path))

def check(name, passed, **details):
    row = {'name': name, 'passed': bool(passed), **details}
    checks.append(row)
    event('check', **row)
    return bool(passed)

def budget():
    if time.monotonic()-T0 > 900:
        raise TimeoutError('Independent scientific execution exceeded 900 seconds')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def inventory():
    paths = sorted(p for p in RUN.rglob('*') if p.is_file())
    paths += [BASE / ('di-morgan-processing-' + s + '-20261009.log')
              for s in ('preflight', 'baseline', 'render-clean')]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}

def ident(a):
    return {'dtype': a.dtype.str, 'shape': list(a.shape),
            'byte_sha256': digest(a.tobytes(order='C')), 'finite': bool(np.isfinite(a).all())}

def members(path, names):
    event('npz_members_read', path=str(path), members=list(names))
    with np.load(path, allow_pickle=False) as z:
        return {n: z[n] for n in names}

def archive(name, **values):
    path = ARRAYS / (name + '.npz')
    with path.open('xb') as f:
        np.savez_compressed(f, **values)
        f.flush()
        os.fsync(f.fileno())
    record = {'path': str(path.relative_to(ROOT)), 'file_sha256': sha(path),
              'members': {k: ident(v) for k, v in values.items()}}
    restored = members(path, values.keys())
    assert all(ident(restored[k]) == record['members'][k] for k in values)
    event('array_readback', **record)
    return record

def normalize(x):
    x = np.asarray(x, dtype=np.float64)
    return x / (x.std() + 1e-9) * 0.1

def spectral(a, b, windows):
    total = 0.0
    for n, window in windows.items():
        mags = []
        for x in (a, b):
            padded = np.pad(x, (n//2, n//2), mode='reflect')
            frames = np.lib.stride_tricks.sliding_window_view(padded, n)[::n//4]
            mags.append(np.abs(np.fft.rfft(frames * window, axis=-1)) + 1e-6)
        A, B = mags
        total += np.linalg.norm(A-B)/(np.linalg.norm(B)+1e-6)
        total += np.mean(np.abs(np.log(A)-np.log(B)))
    return float(total / len(windows))

def score(x, target, di, windows):
    from scipy.signal import butter, sosfiltfilt
    x, target, di = [np.asarray(a, dtype=np.float64) for a in (x, target, di)]
    assert all(a.shape == (288000,) and np.isfinite(a).all() for a in (x,target,di))
    center = slice(72000,216000)
    a, b = normalize(x[center]), normalize(target[center])
    sos = butter(4, (80,4000), btype='bandpass', fs=48000, output='sos')
    c, d = [normalize(sosfiltfilt(sos,v,padtype='odd',padlen=27)[center]) for v in (x,di)]
    return {'primary': spectral(a,b,windows),
            'canonical_waveform_l1': float(np.mean(np.abs(a-b))),
            'raw_lowband': spectral(c,d,windows)}

def gate(rows, takes):
    assert len(rows) == len(takes) == 12
    assert len({t['slug'] for t in takes}) == len({t['take'] for t in takes}) == 12
    assert all(sum(t['content']==g for t in takes)==6 for g in ('chords','scales'))
    ordered = {r['slug']: r for r in rows}
    values=[]
    for t in takes:
        r=ordered[t['slug']]
        assert (r['content'],r['take']) == (t['content'],t['take'])
        assert r['qc_valid'] is True and 0 <= r['oracle'] < 1e-6
        assert all(math.isfinite(r[k]) and r[k]>=0 for k in ('wet','net','flatref'))
        base=min(r['wet'],r['flatref'])
        assert base>0
        values.append((base-r['net'])/base)
    median=statistics.median(values)
    groups={g: statistics.median(v for t,v in zip(takes,values) if t['content']==g)
            for g in ('chords','scales')}
    wins=sum(v>0 for v in values)
    passed=median >= .1-8*math.ulp(.1) and wins>=9 and all(v>0 for v in groups.values())
    return {'valid':True,'passed':passed,'disposition':'PASS' if passed else 'FAIL',
            'median_relative_improvement':median,'strict_wins':wins,'group_medians':groups,
            'per_take':[{'slug':t['slug'],'relative_improvement':v} for t,v in zip(takes,values)]}

def network():
    import torch.nn as nn
    class IndependentNet(nn.Module):
        def __init__(self):
            super().__init__()
            widths=(32,64,128,256,512)
            self.enc=nn.ModuleList()
            self.mid=nn.ModuleList()
            self.dec=nn.ModuleList()
            previous=1
            for width in widths:
                self.enc.append(nn.Sequential(nn.Conv1d(previous,width,8,4,padding=2),nn.GELU(),
                                              nn.Conv1d(width,2*width,1),nn.GLU(dim=1)))
                previous=width
            for dilation in (1,3,9,27):
                self.mid.append(nn.Sequential(nn.Conv1d(512,512,3,padding=dilation,dilation=dilation),
                                              nn.GELU(),nn.Conv1d(512,512,1)))
            for width,out in zip(reversed(widths),(256,128,64,32,1)):
                layers=[nn.Conv1d(width,2*width,3,padding=1),nn.GLU(dim=1),
                        nn.ConvTranspose1d(width,out,8,4,padding=2)]
                if out!=1:
                    layers.append(nn.GELU())
                self.dec.append(nn.Sequential(*layers))
        def forward(self,x):
            length=x.shape[-1]
            h=torch.nn.functional.pad(x,(0,(-length)%1024))
            skip=[]
            for block in self.enc:
                h=block(h)
                skip.append(h)
            for block in self.mid:
                h=h+block(h)
            for block in self.dec:
                h=block(h+skip.pop()[...,:h.shape[-1]])
            return h[...,:length]
    return IndependentNet()

def rebuild(net, raw):
    x=np.asarray(raw,dtype='<f4')
    n=len(x); window=288000; hop=240000; overlap=48000
    out=np.zeros(n,np.float32); weights=np.zeros(n,np.float32)
    fade=np.ones(window,np.float32)
    fade[:overlap]=np.linspace(0,1,overlap)
    fade[-overlap:]=np.linspace(1,0,overlap)
    starts=list(range(0,max(1,n-window+1),hop))
    if starts[-1]+window<n:
        starts.append(max(0,n-window))
    with torch.no_grad():
        for start in starts:
            segment=x[start:start+window].astype(np.float32)
            scale=segment.std()+1e-9
            tensor=torch.tensor(segment/scale*0.1,device=torch.device('cpu'))[None,None]
            y=net(tensor)[0,0].cpu().numpy()/0.1*scale
            f=fade[:len(segment)].copy()
            if start==0:
                f[:overlap]=1
            if start+window>=n:
                f[-min(overlap,len(segment)):]=1
            out[start:start+len(segment)]+=y*f
            weights[start:start+len(segment)]+=f
    return out/np.maximum(weights,1e-6)

def derive():
    assert not DERIVATION.exists() and not BARRIER.exists() and not BLIND.exists()
    event('derive_start', command=sys.argv, executable=sys.executable, prefix=sys.prefix,
          prior_tool_reads='execution task first; plan/snapshot/review/source specifications; git and filenames only; no current primary numeric content')
    assert sys.prefix == '/Users/yoavbz/ndsp-presets/tools/learn-venv'
    assert git('rev-parse','HEAD').decode().strip()==HEAD
    plan=read(ROOT/'docs/di-morgan-processing-control-plan.md').decode()
    approval=json.loads(re.search(r'<!-- processing-approval\n(.*?)\nprocessing-approval -->',plan,re.S)[1])
    snapshot=js(BASE/'di-morgan-processing-review-snapshot.json')
    assert approval['source_pins']==snapshot['source_pins']
    pins={**approval['source_pins'],approval['review']:approval['review_sha256']}
    pins['docs/di-morgan-processing-control-plan.md']=digest(plan.encode())
    for name,expected in pins.items():
        assert sha(ROOT/name)==expected
        assert digest(git('show','HEAD:'+name))==expected
    assert digest(plan.split('## Frozen design\n',1)[1].encode())==approval['design_sha256']
    initial=inventory()
    manifest=js(ROOT/'docs/di-domain-pilot-inputs.json')
    takes=[{k:t[k] for k in ('slug','content','take')} for t in manifest['takes']]
    old=js(ROOT/'docs/di-morgan-flatref.json')
    oldrows={r['slug']:r for r in old['rows']}
    declared=js(ROOT/'docs/di-timing-sensitivity-inputs.json')
    artifact_hashes={}
    for line in read(ROOT/'docs/di-timing-sensitivity-inputs.sha256').decode().splitlines():
        h,name=line.split('  ',1)
        assert name not in artifact_hashes
        artifact_hashes[name]=h
        assert sha(ROOT/name)==h
    assert len(artifact_hashes)==48 and artifact_hashes==declared['artifacts']
    asset_hashes={key:{'path':manifest[key]['path'],'sha256':sha(manifest[key]['path'])}
                  for key in ('model','average')}
    assert all(asset_hashes[k]['sha256']==manifest[k]['sha256'] for k in asset_hashes)
    correction=js(ROOT/'docs/di-domain-pilot-v2-inputs.json')
    compressed=read(ROOT/correction['windows'])
    raw=gzip.decompress(compressed)
    assert digest(compressed)==correction['windows_sha256']
    assert digest(raw)==correction['windows_raw_sha256']
    table=json.loads(raw); windows={}; window_ids={}
    assert set(table)=={'256','512','1024','2048','4096'}
    for n in (256,512,1024,2048,4096):
        row=table[str(n)]['torch32']; bits=row['bits']
        assert row['dtype']=='<f4' and len(bits)==n
        data=np.asarray(bits,dtype='<u4').tobytes()
        assert digest(data)==row['sha256']
        windows[n]=np.frombuffer(data,dtype='<f4').astype(np.float64)
        window_ids[str(n)]=ident(windows[n])
    ARRAYS.mkdir(exist_ok=False)
    outputs=[archive('windows',**{str(n):w for n,w in windows.items()})]
    loaded={}; rows=[]; copy_rows=[]
    for take in takes:
        budget(); slug=take['slug']; values={}
        for stage,names in [('prepare',('di','target')),('render',('baseline','net_input')),('infer',('prediction',))]:
            values.update(members(BASE/'di-morgan-control-20261008'/stage/(slug+'.npz'),names))
        values.update(members(BASE/'di-morgan-flatref-20261008'/(slug+'.npz'),('flatref',)))
        mapping={'di':'di','target':'target','wet':'baseline','net':'prediction','flatref':'flatref'}
        for label,name in mapping.items():
            actual=ident(values[name]); expected=declared['waveforms'][slug][label]
            assert actual['shape']==[288000] and actual['finite']
            assert actual['byte_sha256']==expected['sha256'] and str(values[name].dtype)==expected['dtype']
        assert values['net_input'].dtype==np.dtype('float64') and values['net_input'].shape==(288000,)
        assert np.isfinite(values['net_input']).all()
        loaded[slug]=values
        row={**take,'qc_valid':oldrows[slug]['qc_valid'],'oracle':oldrows[slug]['oracle']}
        for label,name in [('wet','baseline'),('net','prediction'),('flatref','flatref')]:
            scores=score(values[name],values['target'],values['di'],windows)
            key={'wet':'input_scores','net':'network_scores','flatref':'flatref_scores'}[label]
            row[key]=scores; row[label]=scores['primary']
        rows.append(row)
        retained=members(RUN/'render-clean'/(slug+'.render-input.npz'),('render_di','saved_di'))
        x,saved=retained['render_di'],retained['saved_di']
        copy_rows.append({**take,'render_di':ident(x),'saved_di':ident(saved),
                          'shape_dtype_finite':bool(x.dtype==np.dtype('float64') and x.shape==(384000,) and np.isfinite(x).all()
                              and saved.dtype==np.dtype('float64') and saved.shape==(288000,) and np.isfinite(saved).all()),
                          'saved_di_original_bytes':saved.tobytes()==values['di'].tobytes(),
                          'suffix_samples_equal':bool(np.array_equal(x[96000:],values['di'])),
                          'suffix_bytes_equal':x[96000:].tobytes()==values['di'].tobytes()})
        event('original_scores_complete',slug=slug)
    screen=gate(rows,takes)
    scalar_diffs=[]
    for r in rows:
        for arm in ('input_scores','network_scores','flatref_scores'):
            for metric,value in r[arm].items():
                expected=oldrows[r['slug']][arm][metric]
                scalar_diffs.append({'slug':r['slug'],'arm':arm,'metric':metric,'own':value,'old_committed':expected,'abs_diff':abs(value-expected)})
    check('old108',len(scalar_diffs)==108 and all(d['abs_diff']<=1e-8 for d in scalar_diffs))
    check('retained12',len(copy_rows)==12 and all(all(r[k] for k in ('shape_dtype_finite','saved_di_original_bytes','suffix_samples_equal','suffix_bytes_equal')) for r in copy_rows))
    budget()
    torch.set_num_threads(2)
    net=network().cpu()
    event('model_read',path=manifest['model']['path'],weights_only=True)
    net.load_state_dict(torch.load(manifest['model']['path'],map_location='cpu',weights_only=True))
    net.eval()
    assert torch.get_num_threads()==2 and not net.training
    inference=[]; directrows=[]
    for take,row in zip(takes,rows):
        budget(); slug=take['slug']; v=loaded[slug]
        prediction=rebuild(net,v['net_input'])
        outputs.append(archive(slug+'.prediction',raw_prediction=prediction))
        assert prediction.dtype==np.dtype('<f4') and prediction.shape==(288000,) and np.isfinite(prediction).all()
        scores=score(prediction,v['target'],v['di'],windows)
        inference.append({**take,'prediction_identity':ident(prediction),
                          'original_byte_identical':prediction.dtype==v['prediction'].dtype and prediction.tobytes()==v['prediction'].tobytes(),
                          'max_absolute_original_difference':float(np.max(np.abs(prediction-v['prediction']))),
                          'scores':scores,'score_diffs':{k:abs(scores[k]-row['network_scores'][k]) for k in scores}})
        directrows.append({**row,'network_scores':scores,'net':scores['primary']})
        event('own_inference_saved',slug=slug)
    direct_screen=gate(directrows,takes)
    check('original12_model_bytes',len(inference)==12 and all(r['original_byte_identical'] for r in inference))
    check('original36_direct_scores',sum(len(r['score_diffs']) for r in inference)==36 and all(v<=1e-8 for r in inference for v in r['score_diffs'].values()))
    runtime={'executable':sys.executable,'prefix':sys.prefix,'python':sys.version,'platform':platform.platform(),
             'machine':platform.machine(),'packages':{'numpy':np.__version__,'scipy':scipy.__version__,'torch':torch.__version__},
             'torch_threads':torch.get_num_threads(),'torch_config':torch.__config__.show(),
             'numpy_config':str(getattr(np.__config__,'CONFIG','unavailable')),
             'environment':{k:os.environ.get(k) for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS')},
             'package_files':{m.__name__:{'path':m.__file__,'sha256':sha(m.__file__)} for m in (np,scipy,torch)},
             'loaded_extension_paths':sorted({m.__file__ for m in tuple(sys.modules.values()) if getattr(m,'__file__',None) and m.__file__.endswith(('.so','.dylib'))})}
    derivation={'complete':True,'head':HEAD,'scope':'reached-original-controls-only; stopped render-clean',
                'pins':pins,'snapshot_sha256':sha(BASE/'di-morgan-processing-review-snapshot.json'),
                'primary_hash_only_inventory':initial,'original_artifacts':artifact_hashes,'assets':asset_hashes,
                'windows':window_ids,'takes':takes,'rows':rows,'old108_diffs':scalar_diffs,
                'screen':screen,'direct_screen':direct_screen,'inference':inference,'retained_copies':copy_rows,
                'arrays':outputs,'checks':checks,'runtime':runtime,
                'counts':{'original_scalar_controls':108,'original_predictions':12,'direct_scalar_controls':36,'retained_render_input_copies':12,'new_audio_returns':0,'new_predictions_computed':0},
                'scientific_elapsed_seconds':time.monotonic()-T0,
                'inherited_metadata_limit':'QC and oracle copied from exact old committed result; not new raw-data QC or absent target regeneration. Average hashed only; not loaded.'}
    save(HASHES,outputs)
    save(DERIVATION,derivation)
    restored=js(DERIVATION)
    assert restored==derivation
    assert js(HASHES)==outputs
    for a in outputs:
        assert sha(ROOT/a['path'])==a['file_sha256']
        assert {k:ident(v) for k,v in members(ROOT/a['path'],a['members'].keys()).items()}==a['members']
    with BLIND.open('xb') as f:
        f.write(read(SOURCE)); f.flush(); os.fsync(f.fileno())
    assert read(BLIND)==read(SOURCE)
    budget()
    save(BARRIER,{'complete_derivation_readback':True,'all_output_arrays_readback':True,
                  'primary_numeric_content_read_before_barrier':False,'head':HEAD,
                  'derivation_sha256':sha(DERIVATION),'array_manifest_sha256':sha(HASHES),
                  'blind_source_sha256':sha(BLIND),'source_sha256':sha(SOURCE),
                  'transcript_prefix_sha256':sha(TRANSCRIPT),'scientific_elapsed_seconds':time.monotonic()-T0,
                  'unix':time.time()})
    assert js(BARRIER)['complete_derivation_readback']
    event('barrier_readback_complete')
    print(json.dumps({'barrier':str(BARRIER),'counts':derivation['counts'],'checks':checks,'seconds':time.monotonic()-T0}),flush=True)

def compare():
    raise NotImplementedError('Comparison code will be finalized after the blind barrier; original blind source is preserved.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('derive','compare'))
    args=parser.parse_args()
    try:
        import numpy as np
        import scipy
        import torch
        if args.phase=='derive':
            derive()
        else:
            compare()
    except BaseException as error:
        event('execution_failure',type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
        print(traceback.format_exc(),flush=True)
        raise
