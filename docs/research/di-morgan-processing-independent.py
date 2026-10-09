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
    import difflib
    event('comparison_start', command=sys.argv,
          tool_reads_after_barrier='After barrier readback tool output, shell read only current results/replays/identities/seal excerpts and failure/protocol/closure/log/commands evidence. These reads were after blind barrier; this log is an attestation, not a retrospective OS access audit.')
    barrier=js(BARRIER)
    assert barrier['complete_derivation_readback'] and barrier['all_output_arrays_readback']
    assert sha(DERIVATION)==barrier['derivation_sha256']
    assert sha(HASHES)==barrier['array_manifest_sha256']
    assert sha(BLIND)==barrier['blind_source_sha256']
    d=js(DERIVATION)
    checks.extend(d['checks'])
    source_diff=''.join(difflib.unified_diff(read(BLIND).decode().splitlines(True),
                        read(SOURCE).decode().splitlines(True),fromfile=BLIND.name,tofile=SOURCE.name))
    check('scientific_source_functions_unchanged',read(BLIND).split(b'def compare():')[0]==read(SOURCE).split(b'def compare():')[0])
    # The barrier hash identifies a complete byte prefix of the append-only transcript.
    prefix=hashlib.sha256(); prefix_length=0; found_prefix=False
    transcript_before_comparison=TRANSCRIPT.read_bytes()
    for line in transcript_before_comparison.splitlines(True):
        prefix.update(line); prefix_length+=len(line)
        if prefix.hexdigest()==barrier['transcript_prefix_sha256']:
            found_prefix=True; break
    check('barrier_transcript_prefix',found_prefix,bytes=prefix_length)
    assert found_prefix
    events=[json.loads(line) for line in transcript_before_comparison.splitlines()]
    barrier_index=next(i for i,e in enumerate(events) if e['event']=='barrier_readback_complete')
    forbidden_reads=[]
    for e in events[:barrier_index]:
        if e['event']=='content_read' and str(RUN) in e.get('path',''):
            forbidden_reads.append(e)
        if e['event']=='npz_members_read' and str(RUN) in e.get('path',''):
            if not e['path'].endswith('.render-input.npz') or e['members']!=['render_di','saved_di']:
                forbidden_reads.append(e)
    check('logged_blind_read_discipline',not forbidden_reads,forbidden_reads=forbidden_reads)
    takes=d['takes']; ownrows={r['slug']:r for r in d['rows']}
    old=js(ROOT/'docs/di-morgan-flatref.json'); oldrows={r['slug']:r for r in old['rows']}
    differences=[]
    def diff(family,path,own,primary,tolerance=1e-8):
        if isinstance(own,bool) or isinstance(primary,bool):
            ok=type(own)==type(primary) and own==primary; delta=None
        elif isinstance(own,(int,float)) and isinstance(primary,(int,float)):
            delta=abs(own-primary); ok=math.isfinite(delta) and delta<=tolerance
        else:
            delta=None; ok=own==primary
        differences.append({'family':family,'path':path,'own':own,'primary':primary,
                            'abs_diff':delta,'tolerance':tolerance if delta is not None else None,'passed':ok})
    def tree(family,path,own,primary):
        if isinstance(own,dict) and isinstance(primary,dict):
            diff(family,path+'.keys',sorted(own),sorted(primary))
            for k in own.keys() & primary.keys():
                tree(family,path+'.'+k,own[k],primary[k])
        elif isinstance(own,list) and isinstance(primary,list):
            diff(family,path+'.length',len(own),len(primary),0)
            for i,(a,b) in enumerate(zip(own,primary)):
                tree(family,path+'.'+str(i),a,b)
        else:
            diff(family,path,own,primary)
    tree('old_committed_gate','screen',d['screen'],old['screen'])
    stage_records={}; seals={}; runtimes={}; provenance={}
    for stage in ('preflight','baseline'):
        directory=RUN/stage
        result=js(directory/'result.json'); replay=js(directory/'scalar-replay.json')
        stage_records[stage]={'result':result,'scalar_replay':replay}
        check(stage+'.initial_pass',result.get('complete') is True and result.get('passed') is True
              and result.get('disposition')=='PASS' and result.get('scalar_count')==108
              and result.get('verification_status')=='INITIAL' and result.get('independent_verified') is False)
        check(stage+'.replay_coverage',replay.get('complete') is True and replay.get('passed') is True
              and replay.get('scalar_count')==108 and len(replay.get('rows',[]))==12
              and [r['slug'] for r in replay['rows']]==[t['slug'] for t in takes]
              and replay.get('absolute_tolerance')==1e-8)
        for i,(t,r) in enumerate(zip(takes,replay['rows']),1):
            check(stage+'.row.'+t['slug'],all(r.get(k)==t[k] for k in t) and r.get('valid') is True)
            attempt=js(directory/('replay-attempt-%02d.json'%i))
            check(stage+'.row_persistence.'+t['slug'],attempt.get('nonfinite_diagnostic_fields')==[]
                  and {k:v for k,v in attempt.items() if k!='nonfinite_diagnostic_fields'}==r)
            for arm,key in [('wet','input_scores'),('net','network_scores'),('flatref','flatref_scores')]:
                check(stage+'.score_keys.'+t['slug']+'.'+arm,set(r['scores'][key])==set(ownrows[t['slug']][key]))
                for metric,value in ownrows[t['slug']][key].items():
                    diff(stage+'.108',t['slug']+'.'+key+'.'+metric,value,r['scores'][key][metric])
                    expected_error=abs(r['scores'][key][metric]-oldrows[t['slug']][key][metric])
                    diff(stage+'.reported_errors',t['slug']+'.'+arm+'.'+metric,expected_error,r['errors'][arm+'.'+metric])
        tree(stage+'.gate','screen',d['screen'],replay['screen'])
        seal=js(directory/'seal.json'); seal_rows=[]
        actual_names={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()}-{'seal.json'}
        check(stage+'.seal_coverage',actual_names==set(seal['files']),sealed_count=len(seal['files']),actual_count=len(actual_names))
        for name,h in seal['files'].items():
            observed=sha(directory/name)
            seal_rows.append({'path':name,'expected':h,'observed':observed,'passed':h==observed})
        check(stage+'.sealed_bytes',all(r['passed'] for r in seal_rows)
              and seal['result_sha256']==sha(directory/'result.json'))
        seals[stage]=seal_rows
        runtimes[stage]=js(directory/'runtime.json')
    for stage in ('preflight','baseline','render-clean'):
        p=js(RUN/stage/'provenance.json'); provenance[stage]=p
        check(stage+'.provenance',p['revision']==HEAD and p['pins']==d['pins']
              and p['input_artifacts']==d['original_artifacts'] and p['stage_budget_seconds']==900)
    prediction=js(RUN/'baseline/prediction-replay.json')
    check('baseline.prediction_coverage',prediction.get('complete') is True and prediction.get('passed') is True
          and prediction.get('scalar_count')==36 and len(prediction.get('rows',[]))==12
          and [r['slug'] for r in prediction['rows']]==[t['slug'] for t in takes]
          and prediction.get('absolute_tolerance')==1e-8)
    check('baseline.prediction_result_count',stage_records['baseline']['result'].get('prediction_scalar_count')==36)
    byte_checks=[]
    for i,(own,p) in enumerate(zip(d['inference'],prediction['rows']),1):
        slug=own['slug']; path=RUN/'baseline'/(slug+'.prediction.npz')
        independent=members(ARRAYS/(slug+'.prediction.npz'),('raw_prediction',))['raw_prediction']
        primary=members(path,('raw_prediction',))['raw_prediction']
        identical=ident(primary)==own['prediction_identity'] and primary.tobytes()==independent.tobytes()
        byte_checks.append({'slug':slug,'byte_identical':identical,
                            'max_abs_difference':float(np.max(np.abs(primary-independent))),
                            'own':ident(independent),'primary':ident(primary)})
        check('baseline.model_output.'+slug,identical and p['valid'] is True and p['returned'] is True
              and p['byte_identical'] is True and all(p[k]==own[k] for k in ('slug','take','content')))
        identity=js(path.with_suffix('.identity.json'))
        expected={'shape':[288000],'dtype':'float32','sha256':own['prediction_identity']['byte_sha256']}
        check('baseline.prediction_identity.'+slug,identity['file']==path.name and identity['sha256']==sha(path)
              and identity['members']=={'raw_prediction':expected}
              and {k:v for k,v in identity.items() if k!='nonfinite_diagnostic_fields'}==p['archive'])
        persisted=js(RUN/'baseline'/('inference-attempt-%02d.json'%i))
        check('baseline.inference_persistence.'+slug,persisted.get('nonfinite_diagnostic_fields')==[]
              and {k:v for k,v in persisted.items() if k!='nonfinite_diagnostic_fields'}==p)
        check('baseline.direct_score_keys.'+slug,set(own['scores'])==set(p['scores']))
        for metric,value in own['scores'].items():
            diff('direct36',slug+'.'+metric,value,p['scores'][metric])
            baseline_saved=next(r for r in stage_records['baseline']['scalar_replay']['rows'] if r['slug']==slug)
            expected_error=abs(p['scores'][metric]-baseline_saved['scores']['network_scores'][metric])
            diff('direct_reported_errors',slug+'.'+metric,expected_error,p['errors'][metric])
    tree('direct_gate','screen',d['direct_screen'],prediction['screen'])
    overlap=js(RUN/'render-clean/render-di-overlap.json')
    check('retained.overlap_report',overlap['passed'] is True and overlap['case_count']==12
          and overlap['dtype']=='float64' and overlap['shape']==[384000]
          and overlap['suffix_start']==96000 and overlap['suffix_samples']==288000
          and overlap['equality']=='exact float64 bytes')
    for own in d['retained_copies']:
        slug=own['slug']; path=RUN/'render-clean'/(slug+'.render-input.npz')
        meta=js(path.with_suffix('.identity.json'))
        expected={k:{'shape':own[k]['shape'],'dtype':'float64','sha256':own[k]['byte_sha256']}
                  for k in ('render_di','saved_di')}
        check('retained.identity.'+slug,meta['file']==path.name and meta['sha256']==sha(path) and meta['members']==expected)
    # Saved command construction is auditable, although no command was applied.
    pack=js(ROOT/'packs/morgan/manifest.json'); specs=pack['parameters']
    buf=read(ROOT/'samples/Example_Clean_PR12.xml')
    tokens=[]
    for m in re.finditer(rb'[\x20-\x7e]+(?=\x00)|(?<=\x01\x02\x05)(?=\x00)',buf):
        start=m.start(); prefix=buf[max(0,start-3):start]
        is_value=len(prefix)==3 and prefix[0]==1 and prefix[2]==5
        if is_value:
            assert prefix[1]-2==len(m[0])
        tokens.append((m[0].decode(),is_value))
    edits={}; module=''; expect_module=False; select=None
    i=0
    while i<len(tokens):
        key,is_value=tokens[i]
        if is_value:
            i+=1; continue
        if key=='subModels':
            expect_module=True; i+=1; continue
        if expect_module:
            module=key; expect_module=False; i+=1; continue
        if i+1<len(tokens) and tokens[i+1][1]:
            value=tokens[i+1][0]; name=module+'/'+key
            if name in specs and specs[name].get('writable',True):
                if module:
                    edits[(module,key)]=value
                elif key=='selectedAmp':
                    select=int(value)
            i+=2
        else:
            i+=1
    rules={'reverb/reverbActive':'false','delay/delayActive':'false','tremolo/tremoloActive':'false',
           'parameters/doublerActive':'false','parameters/gateActive':'false',
           'fxParameters/sectionActive':'true','parameters/transpose':'0','pr12Amp/pr12Reverb':'0'}
    for key,value in rules.items():
        m,k=key.rsplit('/',1); edits[(m,k)]=value
    base={'selectAmp':select,'edits':[{'module':m,'key':k,'value':v} for (m,k),v in edits.items()]}
    expected_commands={}; override={'clean':{},
        'volume85':{'pr12Amp/pr12Volume':'0.85','drive1/drive1Active':'false','drive2/drive2Active':'false'},
        'drive1':{'drive1/drive1Active':'true','drive1/drive1Drive':'0.65','drive1/drive1Tone':'0.5','drive1/drive1Level':'0.5','drive2/drive2Active':'false'},
        'drive2':{'drive2/drive2Active':'true','drive2/drive2Gain':'0.65','drive2/drive2Bass':'0.5','drive2/drive2Treble':'0.5','drive2/drive2Level':'0.5','drive1/drive1Active':'false'}}
    for chain,changes in override.items():
        expected_commands[chain]={'selectAmp':select,'edits':[
            {**e,'value':changes.get(e['module']+'/'+e['key'],e['value'])} for e in base['edits']]}
        for key,value in changes.items():
            spec=specs[key]
            check('command.spec.'+chain+'.'+key,spec.get('writable',True) and
                  (spec['kind']=='switch' if key.endswith('Active') else spec['kind']=='rotation' and 0<=float(value)<=1))
    commands=js(RUN/'render-clean/clean/commands.json')
    check('command.exact_original_template_R',commands['original_full_command']==base,
          edit_count=len(base['edits']),select_amp=select)
    check('command.exact_declared_four',commands['commands']==expected_commands)
    check('command.clean_base_controls',select==1 and edits[('pr12Amp','pr12Volume')]=='0.62'
          and edits[('drive1','drive1Active')]==edits[('drive2','drive2Active')]=='false'
          and edits[('compressor','compressorActive')]=='true' and edits[('fxParameters','sectionActive')]=='true')
    chain=RUN/'render-clean/clean'
    partial=js(chain/'partial.json'); fallback=js(chain/'protocol-fallback.json')
    protocol=[json.loads(line) for line in read(chain/'protocol.jsonl').decode().splitlines()]
    normalized=[{k:v for k,v in r.items() if k!='nonfinite_diagnostic_fields'} for r in protocol]
    expected_protocol=[{'event':'read-error','error':{'type':'ValueError','message':'protocol EOF before complete reply line'},
                        'partial_raw_hex':'','partial_raw':''},
                       {'event':'closed','backend_closed':True,'errors':[]}]
    check('failure.protocol_exact',normalized==expected_protocol)
    check('failure.protocol_persistence',fallback['events']==partial['protocol_evidence']==normalized)
    check('failure.partial_zero_returns',partial['rows']==[] and partial['repeats']=={}
          and partial['cleanup_errors']==[] and partial['protocol_close_errors']==[])
    closed=js(RUN/'closed.json'); invalidated=js(RUN/'render-clean/invalidated.json')
    closure=[json.loads(line) for line in read(RUN/'closure-errors.jsonl').decode().splitlines()]
    failures=[json.loads(line) for line in read(RUN/'render-clean/failures.jsonl').decode().splitlines()]
    check('failure.closure_consistent',closed==invalidated and closure==failures==[closed])
    check('failure.original_error_retained',closed['error']==partial['body_error']
          and closed['error']['type']=='ValueError' and closed['error']['message']=='protocol EOF before complete reply line'
          and closed['error']['processing_evidence']==[{'protocol_read':normalized[0]}])
    check('failure.initial_inconclusive',closed['stage']=='render-clean' and closed['disposition']=='INCONCLUSIVE'
          and closed['verification_status']=='INITIAL' and closed['independent_verified'] is False
          and 0<closed['elapsed_seconds']<=900)
    stderr=read(chain/'au-host/server.log').decode()
    check('failure.observed_stderr',stderr=='instantiate: Error Domain=NSOSStatusErrorDomain Code=-3000 "invalidComponentID"\n')
    logs={s:read(BASE/('di-morgan-processing-'+s+'-20261009.log')).decode()
          for s in ('preflight','baseline','render-clean')}
    check('failure.stage_logs',logs['preflight']==logs['baseline']==''
          and 'ValueError: protocol EOF before complete reply line' in logs['render-clean']
          and 'ready = self._readline()' in logs['render-clean'] and 'metadata = self.metadata()' in logs['render-clean'])
    absent=['score-clean','render-panel','score-panel']
    check('failure.no_later_stage',all(not (RUN/s).exists() for s in absent))
    check('failure.no_render_authority',all(not (RUN/'render-clean'/name).exists() for name in ('result.json','seal.json'))
          and not (chain/'result.json').exists())
    audio_artifacts=[str(p.relative_to(RUN)) for p in (RUN/'render-clean').rglob('*')
                     if p.is_file() and (p.suffix in ('.wav','.npy') or p.suffix=='.npz' and not p.name.endswith('.render-input.npz'))]
    check('failure.no_audio_artifacts',audio_artifacts==[],found=audio_artifacts)
    check('failure.no_cleanup_error_artifacts',not (RUN/'cleanup-errors.json').exists() and not (chain/'cleanup-errors.json').exists())
    check('runtime.original_cpu_environment',runtimes['baseline']['prefix']==d['runtime']['prefix']
          and runtimes['baseline']['torch_threads']==2
          and all(runtimes['baseline']['packages'][k]==d['runtime']['packages'][k] for k in ('numpy','scipy','torch')))
    stability=[]
    for name,expected in {**d['pins'],**d['original_artifacts']}.items():
        observed=sha(ROOT/name)
        stability.append({'path':name,'expected':expected,'observed':observed,'passed':expected==observed})
    for spec in d['assets'].values():
        observed=sha(spec['path'])
        stability.append({'path':spec['path'],'expected':spec['sha256'],'observed':observed,'passed':observed==spec['sha256']})
    check('source_input_asset_stability',all(r['passed'] for r in stability),count=len(stability))
    current=inventory()
    check('all_primary_artifacts_stable',current==d['primary_hash_only_inventory'],file_count=len(current))
    check('head_stable',git('rev-parse','HEAD').decode().strip()==HEAD)
    check('all_numerical_comparisons',all(r['passed'] for r in differences),comparison_records=len(differences))
    families={}
    for r in differences:
        family=families.setdefault(r['family'],{'records':0,'numeric_records':0,'max_abs_difference':0.0,'failures':0})
        family['records']+=1; family['failures']+=int(not r['passed'])
        if r['abs_diff'] is not None:
            family['numeric_records']+=1
            family['max_abs_difference']=max(family['max_abs_difference'],r['abs_diff'])
    failure_checks=[r for r in checks if not r['passed']]
    execution_failures=[e for e in events if e['event']=='execution_failure']
    outcome='VERIFIED INCONCLUSIVE' if not failure_checks else 'INCONCLUSIVE: VERIFICATION DISAGREEMENT'
    limitations=[
        'Independent implementation shares installed NumPy/SciPy/Torch, CPU and platform; agreement does not independently validate those libraries or hardware.',
        'QC/oracle eligibility is inherited from exact old committed metadata. No raw recording QC, target regeneration, average loading, missing prerequisite computation or new audio was performed.',
        'Command construction matches template+R and declared overrides, but startup failed before any acknowledgement or audio command. No live parameter readback or plugin identity can be verified.',
        'Retained transcripts, stderr, stage logs and filesystem inventory support the recorded startup failure and closure. They are not a retrospective OS/process/runtime access audit or independent observation of historical calls.',
        'The record establishes observed invalidComponentID(-3000) stderr; it does not establish why the OS rejected the component.',
        'Main reports primary sessions completed and no CPU overlap. This verifier does not retrospectively prove process exclusivity.',
        'Twelve dependent performances are not twelve independent players; no native/song/preset/product or processing-robustness conclusion follows from original controls.',
        'First verifier launch failed on Python-version hash API compatibility before scientific inputs; preserved in transcript/log. Only one actual original model pass ran. Scientific execution was under 900 seconds.',
        'Tool-level source and post-barrier comparison reads are described in transcript attestations; the transcript instruments this verifier, not all shell/tool operations.'
    ]
    event('comparison_complete',outcome=outcome,checks=len(checks),failures=len(failure_checks),
          numeric_difference_records=len(differences))
    # Final transcript/log hashes are taken without appending a further transcript event.
    evidence_paths=[SOURCE,BLIND,DERIVATION,BARRIER,HASHES,TRANSCRIPT,BASE/(STEM+'.log')]
    identities={str(p.relative_to(ROOT)):{'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size} for p in evidence_paths}
    report={'scientific_outcome':outcome,'primary_scientific_outcome':'INITIAL INCONCLUSIVE',
            'initial_scientific_outcome_verified':not failure_checks,'head':HEAD,
            'comparison_failure_count':len(failure_checks),'difference_failure_count':sum(not r['passed'] for r in differences),
            'check_count':len(checks),'checks':checks,
            'failures':failure_checks,'counts':{**d['counts'],'original_npz_artifacts':48,
                'distinct_original_control_takes':12,'preflight_scalar_comparisons':108,
                'baseline_scalar_comparisons':108,'direct_scalar_comparisons':36,
                'primary_prediction_byte_comparisons':12,'own_prediction_npz_files':12,
                'own_window_npz_files':1,'gate_comparisons':4,'primary_inventory_files':len(current),
                'failure_protocol_events':len(protocol),'new_render_scores_computed':0},
            'difference_families':families,'differences':differences,
            'independent_derivation':d,'primary_prediction_bytes':byte_checks,
            'primary_stage_records':stage_records,'primary_prediction_report':prediction,
            'primary_stage_seals':seals,'primary_provenance':provenance,'primary_runtime':runtimes,
            'failure_audit':{'partial':partial,'fallback':fallback,'protocol':protocol,'closed':closed,
                'invalidated':invalidated,'closure_errors_records':closure,'failures_records':failures,
                'host_stderr':stderr,'stage_logs':logs,'absent_stages':absent,
                'saved_commands':commands,'independent_commands':expected_commands,
                'command_application_acknowledged':False,'startup_reply_received':False,'audio_returns':0},
            'stability':stability,'final_primary_artifacts':current,
            'barrier':barrier,'barrier_transcript_prefix_bytes':prefix_length,
            'evidence_files':identities,'full_source_difference':source_diff,
            'execution_failures_preserved':execution_failures,'limitations':limitations,
            'scientific_elapsed_seconds':barrier['scientific_elapsed_seconds'],
            'comparison_elapsed_seconds':time.monotonic()-T0}
    with REPORT.open('w') as f:
        json.dump(report,f,indent=2,allow_nan=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
    assert json.loads(REPORT.read_bytes())==report
    text=(outcome+'\n\nPrimary outcome: INITIAL INCONCLUSIVE at render-clean. Comparison failures: '
          +str(len(failure_checks))+' / '+str(len(checks))+' checks.\n\n'
          'Independently recomputed 108 original scalar controls, 12 byte-identical original model predictions, '
          '36 direct scalar controls and the original F gate. Validated all 12 retained float64 render-input copies '
          'against original DI, including exact suffix bytes. Unique controls are not multiplied by duplicate persisted report rows.\n\n'
          'Maximum absolute differences by family:\n\n'+ '\n'.join('- '+k+': '+str(v['max_abs_difference']) for k,v in families.items())+'\n\n'
          'Startup EOF with empty partial bytes, zero protocol replies/audio returns; fallback/partial/protocol and '
          'failure/invalidation/closure agree. Host stderr: '+stderr.strip()+'. No cause attribution. '
          'No score-clean/render-panel/score-panel exists or was computed.\n\n'
          'Scientific execution: '+str(barrier['scientific_elapsed_seconds'])+' seconds in original CPU environment. '
          'The earlier hash-API launch failure was preserved; it preceded scientific asset access.\n\n'
          'Evidence (full counts/checks/differences and hashes are in JSON):\n\n'+
          '\n'.join('- '+p+': '+v['sha256'] for p,v in identities.items())+'\n\n'
          'Limitations:\n\n'+'\n'.join('- '+x for x in limitations)+'\n')
    with MD.open('w') as f:
        f.write(text); f.flush(); os.fsync(f.fileno())
    assert MD.read_text()==text

def finalize():
    """Resolve only the demonstrated JSON wrapper mismatch; no science rerun."""
    import difflib
    prior_path=ARRAYS/'comparison-attempt-01.report.json'
    prior=js(prior_path)
    assert digest(REPORT.read_bytes())==digest(prior_path.read_bytes())
    assert prior['difference_failure_count']==0 and len(prior['failures'])==36
    barrier=js(BARRIER)
    assert sha(DERIVATION)==barrier['derivation_sha256']
    assert sha(HASHES)==barrier['array_manifest_sha256']
    assert sha(BLIND)==barrier['blind_source_sha256']
    assert read(BLIND).split(b'def compare():')[0]==read(SOURCE).split(b'def compare():')[0]
    event('reporting_correction_start',reason='Standalone writer adds empty top-level nonfinite_diagnostic_fields; exact payload must match aggregate row. No inference/scoring recomputation.',
          prior_report_sha256=sha(prior_path),prior_source_sha256=sha(ARRAYS/'comparison-attempt-01.source.py'))
    corrections=[]
    for row in prior['checks']:
        if row['passed']:
            continue
        name=row['name']
        stage,kind,slug=name.split('.',2)
        assert (stage in ('preflight','baseline') and kind=='row_persistence') or (stage=='baseline' and kind=='inference_persistence')
        i=next(i for i,t in enumerate(prior['independent_derivation']['takes'],1) if t['slug']==slug)
        if kind=='row_persistence':
            original=prior['primary_stage_records'][stage]['scalar_replay']['rows'][i-1]
            path=RUN/stage/('replay-attempt-%02d.json'%i)
        else:
            original=prior['primary_prediction_report']['rows'][i-1]
            path=RUN/stage/('inference-attempt-%02d.json'%i)
        standalone=js(path)
        exact_extra=set(standalone)-set(original)
        ok=(exact_extra=={'nonfinite_diagnostic_fields'} and standalone['nonfinite_diagnostic_fields']==[]
            and {k:v for k,v in standalone.items() if k!='nonfinite_diagnostic_fields'}==original)
        corrections.append({'name':name,'previous_passed':False,'passed':ok,'extra_keys':sorted(exact_extra),
                            'diagnostic_fields':standalone.get('nonfinite_diagnostic_fields'),
                            'exact_aggregate_payload_equal':{k:v for k,v in standalone.items() if k!='nonfinite_diagnostic_fields'}==original})
        row.update(passed=ok,serialization_wrapper_checked=True)
    assert len(corrections)==36 and all(c['passed'] for c in corrections)
    stability=[]
    for name,expected in {**prior['independent_derivation']['pins'],**prior['independent_derivation']['original_artifacts']}.items():
        actual=sha(ROOT/name)
        stability.append({'path':name,'expected':expected,'observed':actual,'passed':actual==expected})
    for spec in prior['independent_derivation']['assets'].values():
        actual=sha(spec['path'])
        stability.append({'path':spec['path'],'expected':spec['sha256'],'observed':actual,'passed':actual==spec['sha256']})
    current=inventory()
    assert all(r['passed'] for r in stability) and current==prior['final_primary_artifacts']
    assert git('rev-parse','HEAD').decode().strip()==HEAD
    assert not any(not r['passed'] for r in prior['checks'])
    prior['scientific_outcome']='VERIFIED INCONCLUSIVE'
    prior['initial_scientific_outcome_verified']=True
    prior['comparison_failure_count']=0
    prior['failures']=[]
    prior['final_stability']=stability
    prior['reporting_corrections']=corrections
    prior['reporting_correction_explanation']='36 original comparator mismatches were caused solely by required empty top-level nonfinite_diagnostic_fields added to standalone JSON records. All numeric differences already passed. Exact other keys/values were rechecked; original comparison source/report/summary preserved. No inference or scoring rerun.'
    prior['full_source_difference']=''.join(difflib.unified_diff(read(BLIND).decode().splitlines(True),read(SOURCE).decode().splitlines(True),fromfile=BLIND.name,tofile=SOURCE.name))
    executable=Path(sys.executable).resolve()
    prior['comparison_environment']={'explicit_executable':sys.executable,'resolved_executable':str(executable),
                                     'resolved_executable_sha256':sha(executable),'prefix':sys.prefix,
                                     'python':sys.version,'packages':{'numpy':np.__version__,'scipy':scipy.__version__,'torch':torch.__version__}}
    prior['preserved_comparison_attempt']={str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size}
        for p in (prior_path,ARRAYS/'comparison-attempt-01.source.py',ARRAYS/'comparison-attempt-01.report.md')}
    event('final_report_ready',outcome='VERIFIED INCONCLUSIVE',checks=prior['check_count'],comparison_failures=0,
          corrected_serialization_checks=36,no_scientific_recomputation=True)
    paths=[SOURCE,BLIND,DERIVATION,BARRIER,HASHES,TRANSCRIPT,BASE/(STEM+'.log')]
    prior['evidence_files']={str(p.relative_to(ROOT)):{'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size} for p in paths}
    with REPORT.open('w') as f:
        json.dump(prior,f,indent=2,allow_nan=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
    assert json.loads(REPORT.read_bytes())==prior
    text='VERIFIED INCONCLUSIVE\n\n'
    text+='Primary INITIAL INCONCLUSIVE at render-clean agrees. Comparison failures: 0 / '+str(prior['check_count'])+' checks.\n\n'
    text+='108 original scalars and 36 direct scores agree within 1e-8; 12 model outputs are byte identical; all 12 retained float64 input copies pass shape, finiteness and exact original-DI suffix checks. The original F gate agrees.\n\n'
    text+='Maximum absolute differences: preflight scalar replay '+str(prior['difference_families']['preflight.108']['max_abs_difference'])+', CPU baseline scalar replay '+str(prior['difference_families']['baseline.108']['max_abs_difference'])+', direct36 '+str(prior['difference_families']['direct36']['max_abs_difference'])+'.\n\n'
    text+='Startup EOF with empty partial reply, no startup acknowledgement, zero audio returns. Protocol/fallback/partial and closure/invalidation/failure records agree. Observed stderr: '+prior['failure_audit']['host_stderr'].strip()+'. The cause of the OS rejection is unestablished. No later stage exists or was computed.\n\n'
    text+='One scientific CPU pass: '+str(barrier['scientific_elapsed_seconds'])+' seconds. Initial pre-asset hash API failure preserved. First comparison and full source preserved; 36 JSON serialization wrapper checks corrected with exact payload verification, without inference or scoring reruns.\n\n'
    text+='Evidence files:\n\n'+'\n'.join('- '+p+': '+v['sha256'] for p,v in prior['evidence_files'].items())+'\n\n'
    text+='Full JSON: tmp/di-morgan-processing-verification.json (all counts, checks, differences, runtime, stability and preserved failures).\n\n'
    text+='Limitations:\n\n'+'\n'.join('- '+v for v in prior['limitations'])+'\n'
    with MD.open('w') as f:
        f.write(text); f.flush(); os.fsync(f.fileno())
    assert MD.read_text()==text

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('derive','compare','finalize'))
    args=parser.parse_args()
    try:
        import numpy as np
        import scipy
        import torch
        if args.phase=='derive':
            derive()
        elif args.phase=='compare':
            compare()
        else:
            finalize()
    except BaseException as error:
        event('execution_failure',type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
        print(traceback.format_exc(),flush=True)
        raise
