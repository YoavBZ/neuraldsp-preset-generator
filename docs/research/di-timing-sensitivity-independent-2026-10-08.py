"""Independent bounded NumPy/SciPy verification; three authorized files only.

No project imports, inference, rendering, training, network, raw/native/model or
average access. Primary evidence cannot be opened until own complete derivation
has been flushed, fsynced and read back from the authorized JSON report.
"""
from __future__ import annotations
import ast
import copy
import datetime
import gzip
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import traceback

import numpy as np
from scipy.signal import butter, sosfiltfilt

ROOT = Path('/Users/yoavbz/projects/neuraldsp-preset-generator')
HEAD = '25b3439994977e76f66b61d6d52574ae5f4b3b37'
BRANCH = 'codex/song-model-continuation'
OUT = ROOT/'tmp/di-timing-sensitivity-verification.json'
MD = ROOT/'tmp/di-timing-sensitivity-verification.md'
SELF = ROOT/'tmp/di-timing-sensitivity-independent.py'
PRIMARY = ROOT/'tmp/di-timing-sensitivity-20261008'
LOG = ROOT/'tmp/di-timing-sensitivity-20261008.log'
OLD = ROOT/'tmp/di-morgan-control-20261008'
FLAT = ROOT/'tmp/di-morgan-flatref-20261008'
OFFSETS = (-128, -52, -16, -8, -3, -2, 0, 2, 3, 8, 16, 52, 128)
SMALL = (-3, -2, 2, 3)
FFTS = (256, 512, 1024, 2048, 4096)
SR, SIX = 48000, 288000
CENTER = slice(72000, 216000)
TOL = 1e-8
ARM_KEYS = {'wet':'input_scores', 'net':'network_scores', 'flatref':'flatref_scores'}
METRICS = ('primary', 'canonical_waveform_l1', 'raw_lowband')
PIN_NAMES = '''docs/di-domain-pilot-inputs.json docs/di-domain-pilot-plan.md
learn/di_domain_pilot.py learn/run_di_domain_pilot.py learn/direc.py
learn/di_robustness.py research/render_preset_panel.py match/renderer_au.py
samples/Example_Clean_PR12.xml match/renderer.py match/__init__.py learn/__init__.py
packs/__init__.py packs/loader.py packs/morgan/manifest.json format/__init__.py
format/parser.py format/structured.py format/markers.py format/translate.py
format/writer.py scripts/au_render_server.swift scripts/au_probe.swift scripts/_cli.py
learn/run_di_domain_pilot_v2.py tests/test_di_domain_pilot_v2.py
tests/test_di_domain_pilot.py tests/test_run_di_domain_pilot.py
docs/di-domain-pilot-v2-plan.md docs/di-domain-pilot-v2-inputs.json
docs/di-domain-metric-probe-windows.json.gz docs/di-morgan-control-plan.md
learn/di_morgan_control.py tests/test_di_morgan_control.py scripts/_swift.py
docs/di-morgan-flatref-plan.md docs/di-morgan-flatref-inputs.sha256
learn/di_morgan_flatref.py tests/test_di_morgan_flatref.py
docs/di-morgan-control.json docs/di-morgan-control-verification.json
docs/di-morgan-control-prepare.json docs/di-morgan-control-render.json'''.split()
OWN = '''learn/di_timing_sensitivity.py tests/test_di_timing_sensitivity.py
docs/di-timing-sensitivity-plan.md docs/di-timing-sensitivity-inputs.sha256
docs/research/di-timing-sensitivity-review-2026-10-08.md
docs/research/di-morgan-flatref-independent-2026-10-08.py
docs/research/di-morgan-control-independent-2026-10-08.py
docs/di-morgan-flatref.json docs/di-morgan-flatref-verification.json
docs/di-morgan-flatref-provenance.json'''.split()
LIMITS = [
    'Twelve dependent development takes from one player/guitar and one fixed clean Morgan chain; no population, reserved-validation, product or long-training claim.',
    'Only common post-inference saved-output scoring coordinates are perturbed. No network input-window sensitivity, native causation or alignment-gate change follows.',
    'Full original wet renders survive only for the first take/canary. Other eleven full-render hashes/peaks and pre-roll remain inherited evidence.',
    'No separate plugin parameter-command transcript exists; no physical latency or plugin state is remeasured.',
    'Ten-second raw QC, original canonical construction, original renderer and inference evidence are inherited from committed successful independent reports. Only allowed six-second arrays are freshly accessed; no raw audio, average, model, native or reserved arrays are opened.',
    'Primary replay persistence before shifting is established by pinned source, synthetic execution evidence and saved timestamps. This verifier does not retrospectively observe primary runtime function calls; its own read audit is a separate observation.'
]
started = time.monotonic()
primary_allowed = False
audit_events = []
report = {'status':'RUNNING', 'scientific_disposition':'INCONCLUSIVE',
          'pinned_revision':HEAD, 'checks':[], 'failures':[],
          'primary_numerical_values_unread':True, 'limitations':LIMITS,
          'comparison_statistics':{'leaf_fields_checked':0, 'finite_numeric_fields_checked':0,
                                   'max_absolute_discrepancy':0., 'max_discrepancy_field':None}}

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def filehash(path):
    return digest(Path(path).read_bytes())

def readj(path):
    return json.loads(Path(path).read_text())

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def check(name, condition, detail=None):
    item = {'name':name, 'passed':bool(condition)}
    if detail is not None:
        item['detail'] = detail
    report['checks'].append(item)
    if not condition:
        report['failures'].append(item)
    return bool(condition)

def require(name, condition, detail=None):
    if not check(name, condition, detail):
        raise ValueError(name)

def same(name, own, recorded, tol=TOL):
    """Full structure plus exact ints/booleans/identities; finite floats abs<=tol."""
    if type(own) is dict and type(recorded) is dict:
        check(name+'.keys', own.keys() == recorded.keys(),
              None if own.keys() == recorded.keys() else {'own':sorted(own), 'recorded':sorted(recorded)})
        for k in own.keys() & recorded.keys():
            same(name+'.'+k, own[k], recorded[k], tol)
    elif type(own) is list and type(recorded) is list:
        check(name+'.length', len(own) == len(recorded))
        for i, (a,b) in enumerate(zip(own, recorded)):
            same(f'{name}[{i}]', a, b, tol)
    else:
        stats = report['comparison_statistics']
        stats['leaf_fields_checked'] += 1
        if type(own) is float and type(recorded) in (float, int):
            stats['finite_numeric_fields_checked'] += 1
            error = abs(own-recorded)
            finite = math.isfinite(own) and math.isfinite(recorded)
            if finite and error > stats['max_absolute_discrepancy']:
                stats['max_absolute_discrepancy'] = error
                stats['max_discrepancy_field'] = name
            ok = finite and error <= tol
            check(name, ok, {'independent':own, 'recorded':recorded, 'absolute_error':error,
                             'absolute_tolerance':tol})
        else:
            check(name, type(own) is type(recorded) and own == recorded,
                  None if type(own) is type(recorded) and own == recorded else
                  {'independent':own, 'recorded':recorded})

def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        p = Path(os.fsdecode(args[0])).absolute()
        mode, flags = args[1:3]
        write = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if write and p not in (OUT, MD):
            raise PermissionError('verifier write outside two authorized reports: '+str(p))
        if p == LOG or p.is_relative_to(PRIMARY):
            if not primary_allowed:
                raise PermissionError('primary evidence before persisted independent derivation')
            audit_events.append({'event':'open', 'path':str(p.relative_to(ROOT)), 'utc':utc()})
    elif event in ('socket.connect', 'socket.getaddrinfo'):
        raise PermissionError('network forbidden')
    elif event == 'subprocess.Popen':
        command = args[1]
        if not (command[0] == 'git' and command[1] in ('show', 'rev-parse', 'branch', 'status', 'diff')):
            raise PermissionError('only read-only git subprocesses allowed')

def save():
    report['elapsed_seconds'] = time.monotonic()-started
    report['primary_access_audit'] = audit_events
    with OUT.open('w') as f:
        json.dump(report, f, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    lines = ['# Independent scoring-coordinate sensitivity verification', '',
             f"Verification: **{report['status']}**. Scientific disposition: **{report['scientific_disposition']}**.", '',
             f"Revision `{HEAD}`. {len(report['checks'])} checks; {len(report['failures'])} unresolved failures.", '',
             'Independent NumPy/SciPy scorer, exact archived Torch32 bits, finite shifts, paired changes and original gate. No project functions imported or called.', '']
    if 'independent_screen' in report:
        lines += ['| Offset (samples) | Role | Screen | Median improvement | Strict wins | Chords median | Scales median |',
                  '| ---: | --- | --- | ---: | ---: | ---: | ---: |']
        for s in report['independent_screen']['offset_screens']:
            v = s['screen']
            lines.append(f"| {s['offset']} | {s['role']} | {v['disposition']} | {v.get('median_relative_improvement',0):.8%} | {v.get('strict_wins',0)}/12 | {v.get('group_medians',{}).get('chords',0):.8%} | {v.get('group_medians',{}).get('scales',0):.8%} |")
        small = [s['screen'] for s in report['independent_screen']['offset_screens'] if s['offset'] in SMALL]
        if all(s.get('passed') is True for s in small) and len(small) == 4:
            lines += ['', 'All four required small offsets preserve the established fixed Morgan advantage under the original stronger gate. Wider offsets are diagnostic only.']
        else:
            lines += ['', 'The required small offsets do not all preserve the original stronger gate.']
    if 'blindness_barrier' in report:
        lines += ['', 'Own 108 baseline scalars, all 156 rows, paired changes and thirteen screens were persisted and read back before opening any primary numerical results, replay, progress or log.',
                  '', 'Derivation SHA256: `'+report['blindness_barrier']['derivation_sha256']+'`.']
    lines += ['', 'Comparison statistics: `'+json.dumps(report['comparison_statistics'], sort_keys=True)+'`.', '',
              '## Evidence limits', '']+['- '+v for v in LIMITS]
    if 'primary_replay_barrier' in report:
        lines += ['', 'Primary replay barrier: `'+json.dumps(report['primary_replay_barrier'], sort_keys=True)+'`.']
    if report['failures']:
        lines += ['', '## Preserved failures', '']+['- '+json.dumps(v, sort_keys=True) for v in report['failures']]
    with MD.open('w') as f:
        f.write('\n'.join(lines)+'\n')
        f.flush()
        os.fsync(f.fileno())

def ident(t):
    return {k:t[k] for k in ('slug','content','take')}

def coverage(name, rows, takes):
    require(name, len(rows) == 12 and [ident(r) for r in rows] == [ident(t) for t in takes])

def valid_loss(v):
    return type(v) in (int,float) and math.isfinite(v) and v >= 0

def row_valid(r):
    if r.get('qc_valid') is not True or not valid_loss(r['oracle']) or r['oracle'] >= 1e-6:
        return False
    for arm,key in ARM_KEYS.items():
        if set(r[key]) != set(METRICS) or not all(valid_loss(v) for v in r[key].values()):
            return False
        if r[arm] != r[key]['primary']:
            return False
    return min(r['wet'],r['flatref']) > 0

def gate(rows, takes):
    bad = {'valid':False, 'passed':False, 'disposition':'INCONCLUSIVE'}
    try:
        if len(rows) != 12 or len(takes) != 12 or len({r['slug'] for r in rows}) != 12:
            return bad
        if [ident(r) for r in rows] != [ident(t) for t in takes] or not all(row_valid(r) for r in rows):
            return bad
        values = [(min(r['wet'],r['flatref'])-r['net'])/min(r['wet'],r['flatref']) for r in rows]
        median = float(statistics.median(values))
        groups = {g:float(statistics.median(v for r,v in zip(rows,values) if r['content']==g)) for g in ('chords','scales')}
        wins = sum(v > 0 for v in values)
        passed = median >= .1-8*math.ulp(.1) and wins >= 9 and all(v > 0 for v in groups.values())
        return {'valid':True,'passed':passed,'disposition':'PASS' if passed else 'FAIL',
                'median_relative_improvement':median,'strict_wins':wins,'group_medians':groups,
                'per_take':[{'slug':r['slug'],'relative_improvement':v} for r,v in zip(rows,values)]}
    except (KeyError,TypeError,ValueError):
        return bad

def disposition(rows, takes):
    screens = []
    expected = [(o,t['slug']) for o in OFFSETS for t in takes]
    if len(rows) != 156 or [(r['offset'],r['slug']) for r in rows] != expected:
        return {'valid':False,'passed':False,'disposition':'INCONCLUSIVE','offset_screens':[]}
    for offset in OFFSETS:
        subset = [r for r in rows if r['offset']==offset]
        screen = gate(subset,takes) if all(r.get('valid') is True and type(r['offset']) is int for r in subset) else {'valid':False,'passed':False,'disposition':'INCONCLUSIVE'}
        screens.append({'offset':offset,'role':'prerequisite' if offset==0 else 'robustness' if offset in SMALL else 'diagnostic_only','screen':screen})
    if any(s['screen']['valid'] is not True for s in screens) or screens[6]['screen']['passed'] is not True:
        return {'valid':False,'passed':False,'disposition':'INCONCLUSIVE','offset_screens':screens}
    passed = all(s['screen']['passed'] for s in screens if s['offset'] in SMALL)
    return {'valid':True,'passed':passed,'disposition':'PASS' if passed else 'FAIL',
            'offset_screens':screens,'required_small_offsets':list(SMALL)}

def shift(x, offset):
    if type(offset) is not int:
        raise ValueError('integer offset required')
    # Source-index construction independent of the primary's slicing branches.
    source = np.arange(x.size, dtype=np.int64)-offset
    inside = (source >= 0) & (source < x.size)
    y = np.zeros_like(x)
    y[inside] = x[source[inside]]
    return y

def normalize(x):
    x = np.asarray(x, dtype=np.float64)
    return x/(np.std(x)+1e-9)*.1

def magnitudes(x, windows):
    result = []
    for n in FFTS:
        padded = np.pad(x, (n//2,n//2), mode='reflect')
        frames = np.lib.stride_tricks.sliding_window_view(padded, n)[::n//4]
        result.append(np.abs(np.fft.rfft(frames*windows[n], axis=-1))+1e-6)
    return result

def spectral(a, b):
    terms = [float(np.linalg.norm(x-y)/(np.linalg.norm(y)+1e-6)
                   + np.mean(np.abs(np.log(x)-np.log(y)))) for x,y in zip(a,b)]
    return float(sum(terms)/len(terms))

def fixed_refs(saved, windows):
    sos = butter(4,(80,4000),btype='bandpass',fs=SR,output='sos')
    target = normalize(saved['target'][CENTER])
    low = normalize(sosfiltfilt(sos,np.asarray(saved['di'],np.float64),padtype='odd',padlen=27)[CENTER])
    return target,magnitudes(target,windows),magnitudes(low,windows),sos

def score(x, refs, windows):
    target,target_mag,raw_mag,sos = refs
    x = np.asarray(x,np.float64)
    center = normalize(x[CENTER])
    low = normalize(sosfiltfilt(sos,x,padtype='odd',padlen=27)[CENTER])
    return {'primary':spectral(magnitudes(center,windows),target_mag),
            'canonical_waveform_l1':float(np.mean(np.abs(center-target))),
            'raw_lowband':spectral(magnitudes(low,windows),raw_mag)}

def changes(r,z):
    answer = {}
    for arm,key in ARM_KEYS.items():
        before = z[key]['primary']
        delta = r[key]['primary']-before
        answer[arm] = {'primary_absolute_change':delta,'primary_relative_change':delta/before if before>0 else None,
                       'canonical_waveform_l1_change':r[key]['canonical_waveform_l1']-z[key]['canonical_waveform_l1'],
                       'raw_lowband_change':r[key]['raw_lowband']-z[key]['raw_lowband']}
    simple,old = min(r['wet'],r['flatref']),min(z['wet'],z['flatref'])
    answer['advantage'] = {'primary_absolute_change':simple-r['net']-(old-z['net']),
                           'primary_relative_change':(simple-r['net'])/simple-(old-z['net'])/old}
    return answer

def sources_recheck(pins,label):
    require(label+' source hashes', {n:filehash(ROOT/n) for n in pins} == pins)
    require(label+' HEAD',git('rev-parse','HEAD').decode().strip()==HEAD)
    require(label+' branch',git('branch','--show-current').decode().strip()==BRANCH)

def artifacts_recheck(hashes,label):
    for n,h in hashes.items():
        p = ROOT/n
        require(label+' '+n,p.resolve()==p and p.is_file() and filehash(p)==h)

def own_selfchecks(takes):
    x = np.arange(SIX,dtype=np.float32)+1
    before = x.tobytes()
    for offset in OFFSETS:
        y = shift(x,offset)
        lo,hi = max(0,offset),min(SIX,SIX+offset)
        require('independent shift sign/finite/dtype '+str(offset), y.dtype==x.dtype and
                np.array_equal(y[lo:hi],x[lo-offset:hi-offset]) and not y[:lo].any() and not y[hi:].any()
                and np.array_equal(y[CENTER],x[72000-offset:216000-offset]))
    require('shift leaves source bytes intact',x.tobytes()==before)
    fixture=[]
    for o in OFFSETS:
        for t in takes:
            r={**ident(t),'offset':o,'valid':True,'qc_valid':True,'oracle':0.}
            for arm,key in ARM_KEYS.items():
                v=.9 if arm=='net' else 1.
                r[arm]=v; r[key]={m:v for m in METRICS}
            fixture.append(r)
    require('original inclusive boundary',disposition(fixture,takes)['passed'])
    wide=copy.deepcopy(fixture)
    for r in wide:
        if r['offset'] not in (*SMALL,0): r['net']=r['network_scores']['primary']=1.1
    require('wide failures diagnostic only',disposition(wide,takes)['passed'])
    small=copy.deepcopy(wide)
    for r in small:
        if r['offset']==-3: r['net']=r['network_scores']['primary']=1.1
    require('any small failure fails robustness',disposition(small,takes)['disposition']=='FAIL')
    small[-1]['flatref_scores']['raw_lowband']=float('nan')
    require('wide invalid overrides small failure',disposition(small,takes)['disposition']=='INCONCLUSIVE')
    for label,modify in [('wins',lambda r,i:1.01 if i<4 else .8),('group',lambda r,i:1. if r['content']=='scales' else .5)]:
        f=copy.deepcopy(fixture[:12])
        for i,r in enumerate(f): r['net']=r['network_scores']['primary']=modify(r,i)
        require('original stronger '+label+' restriction',gate(f,takes)['disposition']=='FAIL')
    zero=copy.deepcopy(fixture)
    for r in zero:
        if r['offset']==0:r['net']=r['network_scores']['primary']=1.1
    require('zero failure is inconclusive',disposition(zero,takes)['disposition']=='INCONCLUSIVE')
    require('missing coverage inconclusive',disposition(fixture[:-1],takes)['disposition']=='INCONCLUSIVE')

def prepare():
    require('explicit project interpreter and disabled bytecode', Path(sys.prefix).resolve()==(ROOT/'.venv').resolve() and sys.dont_write_bytecode)
    require('fresh exact declaration HEAD and branch',git('rev-parse','HEAD').decode().strip()==HEAD and git('branch','--show-current').decode().strip()==BRANCH)
    report['runtime']={'python':sys.version,'prefix':sys.prefix,'packages':{n:importlib.metadata.version(n) for n in ('numpy','scipy')}}
    report['verifier_sha256']=filehash(SELF)
    pins={n:filehash(ROOT/n) for n in (*PIN_NAMES,*OWN)}
    require('exact 43 inherited plus ten own sources',len(PIN_NAMES)==43 and len(OWN)==10 and len(pins)==53)
    for n,h in pins.items():
        require('committed exact source '+n,digest(git('show',f'{HEAD}:{n}'))==h)
    report['source_pins']=pins
    text=(ROOT/'docs/di-timing-sensitivity-plan.md').read_text()
    approval=json.loads(re.search(r'<!-- timing-approval\n(.*?)\ntiming-approval -->',text,re.S)[1])
    expected={'status':'DECLARED','fresh_independent_review':True,'scope':'common-post-inference-coordinate-only',
              'review_sha256':pins[OWN[4]],'source_sha256':pins[OWN[0]],'test_sha256':pins[OWN[1]],
              'design_sha256':digest(text.split('## Frozen design\n',1)[1].encode()),'inputs_sha256':pins[OWN[3]]}
    same('approval',expected,approval,0)
    require('declared fresh APPROVE review','**Declared:' in text and 'Verdict: APPROVE' in (ROOT/OWN[4]).read_text())
    # Validate the source's own frozen offset/member/metric constants without executing it.
    tree=ast.parse((ROOT/OWN[0]).read_text())
    constants={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in ('OFFSETS','SMALL','ARMS','METRICS','TOL'):
                    constants[target.id]=ast.literal_eval(node.value)
    require('actual runner frozen constants',constants=={'OFFSETS':OFFSETS,'SMALL':SMALL,'ARMS':ARM_KEYS,'METRICS':METRICS,'TOL':TOL})
    manifest=readj(ROOT/'docs/di-domain-pilot-inputs.json')
    correction=readj(ROOT/'docs/di-domain-pilot-v2-inputs.json')
    takes=manifest['takes']
    require('twelve unique takes and six per group',len(takes)==12 and len({t['slug'] for t in takes})==12 and len({t['take'] for t in takes})==12 and all(sum(t['content']==g for t in takes)==6 for g in ('chords','scales')))
    report['attribution']=manifest['attribution']
    prior=readj(ROOT/'docs/di-morgan-flatref-verification.json')
    control=readj(ROOT/'docs/di-morgan-control-verification.json')
    original=readj(ROOT/'docs/di-morgan-flatref.json')
    prep=readj(ROOT/'docs/di-morgan-control-prepare.json')
    infer=readj(ROOT/'docs/di-morgan-control.json')
    rendered=readj(ROOT/'docs/di-morgan-control-render.json')
    for name,obj,count,verifier in [('flatref',prior,1215,OWN[5]),('control',control,767,OWN[6])]:
        require('successful independent '+name,obj['status']=='VERIFIED_WITH_EVIDENCE_LIMITS' and obj['failures']==[] and len(obj['checks'])==count and all(c['passed'] is True for c in obj['checks']) and obj['independent_screen']['passed'] is True and obj['verifier_sha256']==pins[verifier])
    same('prior 43 source pins',{n:pins[n] for n in PIN_NAMES},prior['source_pins'],0)
    same('control 35 source pins',{n:pins[n] for n in PIN_NAMES[:35]},control['source_pins'],0)
    report['inherited_evidence']={'flatref_status':prior['status'],'flatref_checks':1215,'control_status':control['status'],'control_checks':767,'renderer_canary':control['canary'],'flatref_limits':prior['limitations'],'control_limits':control['limitations']}
    require('prior successful renderer canary',control['canary']['passed'] is True)
    require('prior synthetic Torch parity',len(control['synthetic'])==4 and all(abs(r['independent_numpy']-r['independent_torch'])<=TOL for r in control['synthetic']))
    require('prior original complete passed',original['complete'] is True and original['screen']['passed'] is True and infer['complete'] is True and infer['screen']['passed'] is True and prep['complete'] is True and prep['valid'] is True and rendered['complete'] is True)
    for name,rows in [('original',original['rows']),('independent original',prior['independent_rows']),('prepare',prep['rows']),('independent prepare',control['preparation']),('independent prediction',control['replay']),('infer',infer['rows'])]:
        coverage(name+' ordered coverage',rows,takes)
    for r,v,p,c in zip(original['rows'],prior['independent_rows'],prep['rows'],control['preparation']):
        require(r['slug']+' inherited QC/oracle valid',row_valid(r) and p['qc_valid'] is True and p['qc']['valid'] is True and c['qc']['valid'] is True and valid_loss(p['oracle_scores']['primary']) and p['oracle_scores']['primary']<1e-6)
        same(r['slug']+' prior original values',r,{k:v[k] for k in r})
        same(r['slug']+' independently verified QC',p['qc'],c['qc'])
        same(r['slug']+' independently verified oracle',p['oracle_scores'],c['oracle_scores'])
        same(r['slug']+' row oracle',r['oracle'],p['oracle_scores']['primary'])
    same('prior original screen',gate(original['rows'],takes),original['screen'])
    same('prior independent screen',gate(original['rows'],takes),prior['independent_screen'])
    for stage,archive in [('prepare','docs/di-morgan-control-prepare.json'),('render','docs/di-morgan-control-render.json'),('infer','docs/di-morgan-control.json')]:
        require('original byte-identical '+stage,filehash(OLD/stage/'result.json')==pins[archive])
        same('original '+stage+' provenance',control['source_pins'],readj(OLD/stage/'provenance.json')['pins'],0)
    for saved,archive in [('result.json','docs/di-morgan-flatref.json'),('provenance.json','docs/di-morgan-flatref-provenance.json')]:
        require('flatref byte-identical '+saved,filehash(FLAT/saved)==pins[archive]==prior['primary_artifact_hashes'][saved])
    same('flatref provenance exactly 43 pins',prior['source_pins'],readj(FLAT/'provenance.json')['pins'],0)
    expected_paths={f'tmp/di-morgan-control-20261008/{s}/{t["slug"]}.npz' for s in ('prepare','render','infer') for t in takes}|{f'tmp/di-morgan-flatref-20261008/{t["slug"]}.npz' for t in takes}
    hashes={}
    for line in (ROOT/OWN[3]).read_text().splitlines():
        h,n=line.split('  ')
        require('declared unique allowed path '+n,n in expected_paths and n not in hashes and re.fullmatch('[a-f0-9]{64}',h) is not None)
        hashes[n]=h
    require('exact 48 manifest paths',set(hashes)==expected_paths and len(hashes)==48)
    old={n:h for n,h in hashes.items() if n.startswith('tmp/di-morgan-control-')}
    same('original36 input identities',old,original['input_artifacts'],0)
    same('independent original36 input identities',old,prior['input_artifacts'],0)
    for n,h in hashes.items():
        if n.startswith('tmp/di-morgan-flatref-'):
            same('saved12 '+n,h,prior['primary_artifact_hashes'][Path(n).name],0)
    report['input_artifacts']=hashes
    require('exact frozen coefficient specification',correction['schema']==2 and correction['tolerance']==TOL and correction['window_family']=='torch32' and correction['window_dtype']=='<f4' and correction['original_inputs']=='docs/di-domain-pilot-inputs.json' and correction['original_inputs_sha256']==pins['docs/di-domain-pilot-inputs.json'] and correction['windows']=='docs/di-domain-metric-probe-windows.json.gz')
    compressed=(ROOT/correction['windows']).read_bytes()
    require('exact coefficient archive',digest(compressed)==correction['windows_sha256'])
    uncompressed=gzip.decompress(compressed)
    require('exact coefficient JSON',digest(uncompressed)==correction['windows_raw_sha256'])
    table=json.loads(uncompressed)
    require('coefficient coverage',set(table)=={str(n) for n in FFTS})
    windows={};report['windows']={}
    for n in FFTS:
        row=table[str(n)]['torch32'];bits=row['bits']
        require('exact uint32 bit list '+str(n),row['dtype']=='<f4' and len(bits)==n and all(type(v) is int and 0<=v<2**32 for v in bits))
        raw=np.asarray(bits,dtype='<u4').tobytes()
        require('coefficient bytes '+str(n),digest(raw)==row['sha256'])
        windows[n]=np.frombuffer(raw,dtype='<f4').astype(np.float64)
        require('finite coefficients '+str(n),np.isfinite(windows[n]).all())
        windows[n].flags.writeable=False
        report['windows'][str(n)]=row['sha256']
    own_selfchecks(takes)
    sources_recheck(pins,'before first load')
    artifacts_recheck(hashes,'all48 before first load')
    report['all48_before_first_load_utc']=utc()
    loaded={};identities={};access=[]
    waves=prior['waveform_comparison']
    require('twelve ordered independently identical flatrefs',len(waves)==12 and [w['slug'] for w in waves]==[t['slug'] for t in takes])
    for i,t in enumerate(takes):
        slug=t['slug'];saved={}
        for stage,membermap in [('prepare',{'di':'di','target':'target'}),('render',{'baseline':'wet'}),('infer',{'prediction':'net'}),('flatref',{'flatref':'flatref'})]:
            path=(FLAT if stage=='flatref' else OLD/stage)/f'{slug}.npz'
            n=str(path.relative_to(ROOT))
            artifacts_recheck({n:hashes[n]},'immediate pre-load')
            with np.load(path,allow_pickle=False) as z:
                for member,key in membermap.items():
                    x=z[member]
                    require(slug+' finite active saved '+key,x.dtype.kind=='f' and x.shape==(SIX,) and np.isfinite(x).all() and math.isfinite(float(np.std(x))) and np.std(x)>0)
                    x.flags.writeable=False;saved[key]=x
                    access.append({'path':n,'member':member,'dtype':str(x.dtype),'sha256':digest(x.tobytes())})
        w=waves[i]
        require(slug+' flatref prior exact bytes',w['byte_identical'] is True and w['max_absolute_error']==0 and w['primary_sha256_float64']==prior['independent_rows'][i]['flatref_waveform_sha256_float64'] and w['npz_sha256']==hashes[str((FLAT/f'{slug}.npz').relative_to(ROOT))])
        require(slug+' target prediction flatref inherited bytes',saved['net'].dtype==np.dtype('<f4') and digest(saved['net'].tobytes())==control['replay'][i]['prediction_sha256_float32'] and digest(np.asarray(saved['target'],dtype='<f8').tobytes())==control['preparation'][i]['target_sha256'] and saved['flatref'].dtype==np.dtype('<f8') and digest(saved['flatref'].tobytes())==w['primary_sha256_float64'])
        raw=np.asarray(saved['di'],np.float64)
        frame=np.sqrt(np.mean(raw.reshape(-1,480)**2,axis=1))
        qc={'rms':float(np.sqrt(np.mean(raw**2))),'clipped_fraction':float(np.mean(np.abs(raw)>=.999)),'active_fraction':float(np.mean(frame>frame.max()*.01))}
        require(slug+' fresh six-second raw QC',qc['rms']>=1e-5 and qc['clipped_fraction']<=1e-4 and qc['active_fraction']>=.8)
        same(slug+' fresh raw QC recorded score segment',qc,prep['rows'][i]['qc']['metrics']['score'])
        loaded[slug]=saved
        identities[slug]={k:{'dtype':str(x.dtype),'samples':len(x),'sha256':digest(x.tobytes())} for k,x in saved.items()}
    report['inputs']={'artifacts':hashes,'waveforms':identities}
    report['array_access_audit']=access
    require('exact 48 files/60 allowed members',len(access)==60 and len({r['path'] for r in access})==48 and all(r['member'] in ('di','target','baseline','prediction','flatref') for r in access))
    artifacts_recheck(hashes,'after loading')
    return takes,loaded,windows,original,pins,hashes

def derive(takes,loaded,windows,original,pins,hashes):
    zeros=[];replay=[]
    for i,t in enumerate(takes):
        refs=fixed_refs(loaded[t['slug']],windows)
        r={**ident(t),'offset':0,'qc_valid':True,'oracle':original['rows'][i]['oracle']}
        for arm,key in ARM_KEYS.items():
            r[key]=score(loaded[t['slug']][arm],refs,windows);r[arm]=r[key]['primary']
        require(t['slug']+' valid independent baseline',row_valid(r))
        errors={arm+'.'+m:abs(r[key][m]-original['rows'][i][key][m]) for arm,key in ARM_KEYS.items() for m in METRICS}
        replay.append({**ident(t),'valid':True,'scores':{k:r[k] for k in ARM_KEYS.values()},'errors':errors,'nonfinite_diagnostic_fields':[]})
        zeros.append(r)
    baseline={'complete':True,'passed':all(v<=TOL for r in replay for v in r['errors'].values()),'scalar_count':108,'absolute_tolerance':TOL,'rows':replay,'screen':gate(zeros,takes)}
    same('fresh original screen replay',baseline['screen'],original['screen'])
    report['independent_baseline_replay']=baseline
    report['baseline_rows']=zeros
    report['independent_baseline_saved_utc']=utc()
    save()
    require('complete baseline saved before nonzero shifts',readj(OUT)['independent_baseline_replay']==baseline and baseline['passed'] is True and baseline['screen']['passed'] is True)
    sources_recheck(pins,'before shifts');artifacts_recheck(hashes,'before shifts')
    report['first_nonzero_shift_utc']=utc()
    allrows=[];calls=36;shifts=0
    # Cache only fixed raw/target references, never a shifted arm or its score.
    byoffset={o:[] for o in OFFSETS}
    for i,t in enumerate(takes):
        refs=fixed_refs(loaded[t['slug']],windows)
        z=zeros[i]
        for o in OFFSETS:
            r=copy.deepcopy(z) if o==0 else {**ident(t),'offset':o,'qc_valid':True,'oracle':z['oracle']}
            if o:
                for arm,key in ARM_KEYS.items():
                    wave=shift(loaded[t['slug']][arm],o);shifts+=1
                    r[key]=score(wave,refs,windows);calls+=1;r[arm]=r[key]['primary']
            require(t['slug']+' valid independent offset '+str(o),row_valid(r))
            r.update(valid=True,changes_from_zero=changes(r,z))
            byoffset[o].append(r)
        print('Independent derived take '+str(i+1)+'/12 (all 13 offsets)',flush=True)
    allrows=[r for o in OFFSETS for r in byoffset[o]]
    report['independent_rows']=allrows
    report['independent_screen']=disposition(allrows,takes)
    report['independent_execution_counts']={'score_calls':calls,'nonzero_shifts':shifts,'zero_rescores':0,'baseline_scalars':108,'rows':156,'row_score_scalars':1404,'screens':13}
    require('complete independent numerical derivation',calls==468 and shifts==432 and len(allrows)==156 and len(report['independent_screen']['offset_screens'])==13)
    artifacts_recheck(hashes,'before persisted derivation');sources_recheck(pins,'before persisted derivation')
    for slug,saved in loaded.items():
        same('loaded bytes stable '+slug,report['inputs']['waveforms'][slug],{k:{'dtype':str(x.dtype),'samples':len(x),'sha256':digest(x.tobytes())} for k,x in saved.items()},0)
    payload={'baseline':baseline,'baseline_rows':zeros,'rows':allrows,'screen':report['independent_screen']}
    report['derivation_payload']=payload
    report['blindness_barrier']={'utc':utc(),'all108_and156_and13_and_paired_changes_saved_before_primary_access':True,
                                'derivation_sha256':digest(json.dumps(payload,sort_keys=True,allow_nan=False).encode()),
                                'verifier_sha256':report['verifier_sha256']}
    report['status']='DERIVED_BEFORE_PRIMARY_ACCESS'
    save()
    persisted=readj(OUT)
    require('fsynced complete derivation read-back',persisted['derivation_payload']==payload and digest(json.dumps(persisted['derivation_payload'],sort_keys=True,allow_nan=False).encode())==report['blindness_barrier']['derivation_sha256'])
    return payload

def compare_primary(takes,payload,pins,hashes):
    global primary_allowed
    artifacts_recheck(hashes,'before primary comparison');sources_recheck(pins,'before primary comparison')
    require('no prior independent primary opens',not audit_events)
    report['primary_first_numerical_access_utc']=utc()
    primary_allowed=True
    report['primary_numerical_values_unread']=False
    names=('provenance.json','inputs.json','baseline-replay.json','progress.jsonl','result.json')
    primary_paths=[PRIMARY/n for n in names]+[LOG]
    require('primary exact successful evidence file coverage',set(p.name for p in PRIMARY.iterdir())==set(names))
    snapshots={str(p.relative_to(ROOT)):{'sha256':filehash(p),'birth':p.stat().st_birthtime,'mtime':p.stat().st_mtime,'size':p.stat().st_size} for p in primary_paths}
    report['primary_artifact_snapshots']=snapshots
    result=readj(PRIMARY/'result.json');prov=readj(PRIMARY/'provenance.json');replay=readj(PRIMARY/'baseline-replay.json');inputs=readj(PRIMARY/'inputs.json')
    progress=[json.loads(line) for line in (PRIMARY/'progress.jsonl').read_text().splitlines()]
    log_lines=LOG.read_text().splitlines()
    logrows=[];unparsed=[]
    for line in log_lines:
        try:logrows.append(json.loads(line))
        except json.JSONDecodeError:unparsed.append(line)
    require('primary log exactly all156 JSON rows and no errors',len(logrows)==156 and not unparsed,{'unparsed':unparsed})
    same('all primary rows and paired changes',payload['rows'],result['rows'])
    same('all thirteen primary screens roles and robustness',payload['screen'],result['screen'])
    same('saved complete108 replay scores errors and screen',payload['baseline'],replay)
    same('progress exactly result rows',result['rows'],progress,0)
    same('stdout log exactly result rows',result['rows'],logrows,0)
    same('saved input identities and dtypes',report['inputs'],inputs,0)
    same('primary source pins',pins,prov['pins'],0)
    same('primary artifact identities',hashes,prov['input_artifacts'],0)
    same('result input identities',hashes,result['input_artifacts'],0)
    same('provenance offsets',list(OFFSETS),prov['offsets'],0)
    same('provenance required small offsets',list(SMALL),prov['required_small_offsets'],0)
    for field,expected in [('git_revision',HEAD),('python',sys.version),('prefix',str(ROOT/'.venv')),('packages',report['runtime']['packages']),('budget_seconds',900),('scope','common-post-inference-coordinate-only'),('attribution',report['attribution'])]:
        same('primary provenance '+field,expected,prov[field],0)
    same('complete primary result',True,result['complete'],0)
    same('result attribution',report['attribution'],result['attribution'],0)
    same('result interpretation','Scoring-coordinate sensitivity only; same-player dependent development cases; no native causation or product confirmation.',result['interpretation'],0)
    require('exact provenance and result field coverage',set(prov)=={'pins','git_revision','input_artifacts','python','prefix','started_unix','budget_seconds','packages','offsets','required_small_offsets','attribution','scope'} and set(result)=={'complete','rows','screen','input_artifacts','elapsed_seconds','attribution','interpretation'})
    commit_time=int(git('show','-s','--format=%ct',HEAD).decode().strip())
    stats={n:{'birth':(PRIMARY/n).stat().st_birthtime,'mtime':(PRIMARY/n).stat().st_mtime} for n in names}
    report['commit_before_execution']={'commit_unix':commit_time,'primary_started_unix':prov['started_unix'],'primary_dir_birth':PRIMARY.stat().st_birthtime,'log_birth':LOG.stat().st_birthtime,'artifact_times':stats}
    require('commit before primary creation/start',commit_time<prov['started_unix'] and commit_time<PRIMARY.stat().st_birthtime and commit_time<LOG.stat().st_birthtime and all(commit_time<v['birth'] for v in stats.values()))
    require('elapsed finite positive within original budget',type(result['elapsed_seconds']) in (int,float) and math.isfinite(result['elapsed_seconds']) and 0<result['elapsed_seconds']<=900)
    # A few seconds of wall-clock quantization is a timing consistency check,
    # not a scoring tolerance. Numerical comparison tolerance stays 1e-8.
    wall=(PRIMARY/'result.json').stat().st_mtime-prov['started_unix']
    require('elapsed consistent with saved wall duration',0<=wall<=result['elapsed_seconds']+2 and abs(wall-result['elapsed_seconds'])<=2,{'wall_seconds':wall,'elapsed_seconds':result['elapsed_seconds']})
    replay_time=(PRIMARY/'baseline-replay.json').stat().st_mtime
    progress_time=(PRIMARY/'progress.jsonl').stat().st_birthtime
    require('saved complete replay predates first nonzero progress artifact',replay['complete'] is True and replay['passed'] is True and replay['scalar_count']==108 and replay_time<progress_time and progress[0]['offset']==OFFSETS[0])
    source=(ROOT/OWN[0]).read_text()
    require('pinned source replay persistence before shift loop and zero reuse',
            source.index('zero = replay(out,') < source.index('for offset in OFFSETS:',source.index('def run(')) and
            'R.write_new(out / "baseline-replay.json"' in source and
            'row = dict(base) if offset == 0 else scored_row(' in source and
            source.index('R.write_new(out / "baseline-replay.json"')<source.index('if not passed:',source.index('def replay(')))
    tests=(ROOT/OWN[1]).read_text()
    require('committed synthetic replay barrier and zero reuse evidence',all(s in tests for s in ('assert len(calls) == 468 and len(shifted) == 432','assert len(calls) == 36 and not shifted','assert len(calls) >= 36 and offset != 0')))
    report['primary_replay_barrier']={'complete108_saved':True,'replay_mtime':replay_time,'first_nonzero_progress_birth':progress_time,'saved_time_order':replay_time<progress_time,'pinned_source_persists_before_shifts':True,'zero_scores_reused':True,'runtime_instrumentation_of_primary':False,'evidence':'Pinned reviewed source and synthetic tests plus retained complete108 replay and file creation times; own audit independently establishes own blindness only.'}
    byslug={r['slug']:r for r in payload['baseline_rows']}
    primaryzero=[r for r in result['rows'] if r['offset']==0]
    for r in primaryzero:
        expected=copy.deepcopy(byslug[r['slug']]);expected.update(valid=True,changes_from_zero=changes(expected,expected))
        same('zero reuse '+r['slug'],expected,r)
    artifacts_recheck(hashes,'after primary comparison');sources_recheck(pins,'after primary comparison')
    require('verifier source stable',filehash(SELF)==report['verifier_sha256'])
    for p in primary_paths:
        before=snapshots[str(p.relative_to(ROOT))]
        require('primary evidence stable '+p.name,filehash(p)==before['sha256'] and p.stat().st_size==before['size'] and p.stat().st_mtime==before['mtime'])
    require('derivation still identical after comparison',digest(json.dumps(payload,sort_keys=True,allow_nan=False).encode())==report['blindness_barrier']['derivation_sha256'])
    report['primary_elapsed_seconds']=result['elapsed_seconds']
    report['comparison_summary']={'baseline_scalars':108,'primary_row_score_scalars':1404,'arm_primary_aliases':468,'paired_change_scalars':2184,'screens':13,'progress_rows':len(progress),'stdout_rows':len(logrows),'source_pins':53,'input_files':48,'allowed_array_members':60,'absolute_tolerance':TOL,**report['comparison_statistics']}
    report['scientific_disposition']=payload['screen']['disposition'] if not report['failures'] else 'INCONCLUSIVE'
    report['status']='VERIFIED' if not report['failures'] else 'NOT VERIFIED'
    save()
    print(json.dumps({'status':report['status'],'scientific_disposition':report['scientific_disposition'],'checks':len(report['checks']),'failures':len(report['failures']),'comparison':report['comparison_summary']},sort_keys=True),flush=True)

def main():
    require('no interpreter arguments or output overrides',len(sys.argv)==1)
    require('fresh authorized reports',not OUT.exists() and not MD.exists())
    sys.addaudithook(audit)
    try:
        context=prepare()
        takes,loaded,windows,original,pins,hashes=context
        payload=derive(*context)
        compare_primary(takes,payload,pins,hashes)
    except BaseException as e:
        report['status']='NOT VERIFIED';report['scientific_disposition']='INCONCLUSIVE'
        report['exception']={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}
        check('verification completed without exception',False,report['exception'])
        save()
        print(report['exception']['traceback'],file=sys.stderr,flush=True)
        raise

if __name__=='__main__':
    main()
