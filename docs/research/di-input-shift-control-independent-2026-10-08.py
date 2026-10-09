"""Independent bounded CPU verification. Only this source and two reports written.

No project imports, subprocesses, Git commands, network, rendering or training.
Committed bytes are read directly from content-addressed objects, without Git commands.
Primary numeric evidence is audit-blocked until the complete derivation is durable.
"""
from __future__ import annotations
import base64
import copy
import datetime
import gzip
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import time
import traceback
import zlib

ROOT = Path('/Users/yoavbz/projects/neuraldsp-preset-generator')
SELF = ROOT/'tmp/di-input-shift-independent.py'
OUT = ROOT/'tmp/di-input-shift-verification.json'
MD = ROOT/'tmp/di-input-shift-verification.md'
PRIMARY = ROOT/'tmp/di-input-shift-control-20261008'
LOG = ROOT/'tmp/di-input-shift-control-20261008.log'
HEAD = '885907f27ea487662ae6c6216226ae7ba6ca8e77'
BRANCH = 'refs/heads/codex/song-model-continuation'
MODEL = Path('/Users/yoavbz/ndsp-presets/learn/direc/models-set3/fold2.pt')
MODEL_SHA = '16b2b734b49cc1cc2d7e547d96d3bb56208007c9cae0d0e33acb1c2a1cdd042b'
PREFIX = '/Users/yoavbz/ndsp-presets/tools/learn-venv'
OFFSETS = (-3,-2,0,2,3)
FFTS = (256,512,1024,2048,4096)
N = 288000
CENTER = slice(72000,216000)
ARMS = {'wet':'input_scores','net':'network_scores','flatref':'flatref_scores'}
METRICS = ('primary','canonical_waveform_l1','raw_lowband')
TOL = 1e-8
OWN = ['learn/di_input_shift_control.py','tests/test_di_input_shift_control.py',
       'docs/di-input-shift-control-plan.md','docs/research/di-input-shift-control-review-2026-10-08.md',
       'docs/research/di-timing-sensitivity-independent-2026-10-08.py',
       'docs/di-timing-sensitivity-verification.json','docs/di-timing-sensitivity.json',
       'docs/di-timing-sensitivity-provenance.json','docs/di-timing-sensitivity-inputs.json',
       'docs/di-timing-sensitivity-baseline-replay.json']
LIMITS = [
 'Independent implementation shares underlying NumPy/SciPy/Torch libraries and CPU kernels with the primary; this is not library-independent verification.',
 'Pinned source, reviewed synthetic tests and saved timestamps support primary call-order barriers. Actual primary runtime calls were not independently observed retrospectively; the verifier directly observes only its own calls and read barrier.',
 'Twelve dependent same-player/guitar development takes and one clean Morgan chain. Known input perturbations include finite padding, context and whole-window standard-deviation effects; no isolated stride causation, native transfer/failure, product or long-training claim.',
 'Original full wet renders survive for the first take/canary only; other full-render/pre-roll evidence is inherited. No separate plugin command transcript; physical latency and plugin state are not remeasured.',
 'Original ten-second preparation QC, canonical target construction and prior provenance remain inherited; allowed six-second raw DI QC and frozen target identities are rechecked. No average/catalog/raw/native/reserved data accessed.',
 'Completion/exit0/session53958/19.60s are supplied by main. Saved output completeness is independently inspected; the historical process exit is not independently reobserved.'
]
started = time.monotonic()
primary_allowed = False
read_events = []
report = {'status':'RUNNING','scientific_disposition':'INCONCLUSIVE','checks':[],
          'failures':[],'limitations':LIMITS,'pinned_revision':HEAD,
          'comparison_statistics':{'finite_numeric_fields_checked':0,'max_absolute_discrepancy':0.,'max_discrepancy_field':None},
          'events':[],'primary_numerical_values_unread':True}

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b).hexdigest()
def fh(p): return sha(Path(p).read_bytes())
def rj(p): return json.loads(Path(p).read_text())
def event(stage):
    budget()
    report['events'].append({'stage':stage,'utc':utc(),'elapsed_seconds':time.monotonic()-started})
    print(stage,flush=True)
def budget():
    if time.monotonic()-started > 900: raise TimeoutError('independent local CPU budget 900 seconds')
def check(name, ok, detail=None):
    x={'name':name,'passed':bool(ok)}
    if detail is not None: x['detail']=detail
    report['checks'].append(x)
    if not ok: report['failures'].append(x)
    return bool(ok)
def require(name,ok,detail=None):
    if not check(name,ok,detail): raise ValueError(name)
def same(name,a,b,tol=TOL):
    if type(a) is dict and type(b) is dict:
        check(name+'.keys',a.keys()==b.keys(),None if a.keys()==b.keys() else {'own':list(a),'saved':list(b)})
        for k in a:
            if k in b: same(name+'.'+str(k),a[k],b[k],tol)
    elif type(a) is list and type(b) is list:
        check(name+'.length',len(a)==len(b))
        for i,(x,y) in enumerate(zip(a,b)): same(f'{name}[{i}]',x,y,tol)
    elif type(a) is float and type(b) in (float,int):
        s=report['comparison_statistics'];s['finite_numeric_fields_checked']+=1
        d=abs(a-b);finite=math.isfinite(a) and math.isfinite(b)
        if finite and d>s['max_absolute_discrepancy']: s.update(max_absolute_discrepancy=d,max_discrepancy_field=name)
        check(name,finite and d<=tol,{'independent':a,'saved':b,'absolute_error':d,'tolerance':tol})
    else:
        check(name,type(a) is type(b) and a==b,None if type(a) is type(b) and a==b else {'independent':a,'saved':b})
def audit(e,args):
    if e=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        p=Path(os.fsdecode(args[0])).absolute(); flags=args[2] or 0
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            if p not in (OUT,MD): raise PermissionError('write outside authorized two reports: '+str(p))
        if p==LOG or p.is_relative_to(PRIMARY) or (p.parent==ROOT/'docs' and p.name.startswith('di-input-shift-control') and p.suffix=='.json'):
            if not primary_allowed: raise PermissionError('primary read before complete durable independent derivation: '+str(p))
            read_events.append({'path':str(p.relative_to(ROOT)),'utc':utc()})
    if e in ('subprocess.Popen','socket.connect','socket.getaddrinfo'): raise PermissionError('subprocess/network forbidden')
def save():
    report['elapsed_seconds']=time.monotonic()-started
    report['primary_access_audit']=read_events
    with OUT.open('w') as f:
        json.dump(report,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    lines=['# Independent known-input-shift verification','',
           f"Verification: **{report['status']}**. Scientific disposition: **{report['scientific_disposition']}**.",'',
           f"Revision `{HEAD}`. {len(report['checks'])} checks; {len(report['failures'])} failures.",'',
           'Independent scorer, gates, finite shifts, Torch architecture and original ordered float32 six-second reconstruction. No project numerical functions imported or called.','']
    if 'independent_screen' in report:
        lines+=['| Offset | Screen | Median advantage | Wins | Chords | Scales |','| ---: | --- | ---: | ---: | ---: | ---: |']
        for s in report['independent_screen']['offset_screens']:
            g=s['screen'];m=g.get('group_medians',{})
            lines.append(f"| {s['offset']} | {g['disposition']} | {g.get('median_relative_improvement',0):.8%} | {g.get('strict_wins',0)}/12 | {m.get('chords',0):.8%} | {m.get('scales',0):.8%} |")
    lines+=['',f"Maximum scalar discrepancy: {report['comparison_statistics']['max_absolute_discrepancy']:.17g}; absolute tolerance {TOL}.",'',
            'Full derivation, compressed expected raw/corrected prediction NPZ bytes, all mismatches, identity checks and read audit are retained in the JSON report.','', '## Evidence limits','']+['- '+v for v in LIMITS]
    if report['failures']:
        lines+=['','## Failures','']+['- '+x['name'] for x in report['failures']]
    if 'verification_attempts' in report:
        lines+=['','## Preserved initial comparison','',
                'The initial comparison retained 36 schema mismatches: this verifier omitted the required empty `nonfinite_diagnostic_fields` list on replay records. All prediction byte checks and numeric comparisons passed. The final comparison adds only that source-defined metadata field and reuses the complete previously persisted independent derivation. No model inference, scoring, tolerance change or case selection was repeated. Original failed checks, logs and source identities are preserved in JSON.']
    if 'discrepancy_breakdown' in report:
        lines+=['','## Discrepancies and stability','']
        for category,s in report['discrepancy_breakdown'].items():lines.append(f"- {category}: maximum {s['max_absolute_discrepancy']:.17g}, {s['numeric_comparisons']} scalar fields; largest at `{s['max_discrepancy_field']}`.")
        lines+=['','All 63 pinned source/dependency identities, HEAD, 48 original artifacts, original model and 67 primary artifacts remained stable. No new inference or scoring was performed during the schema correction.']
    if 'exception' in report: lines+=['','```',report['exception']['traceback'],'```']
    with MD.open('w') as f: f.write('\n'.join(lines)+'\n');f.flush();os.fsync(f.fileno())
def regular(p):
    p=Path(p);s=p.stat()
    require('regular unaliased '+str(p),p.is_absolute() and p.resolve()==p and p.is_file() and s.st_nlink==1)
    return s
def headcheck(label):
    h=(ROOT/'.git/HEAD').read_text().strip()
    require(label+' HEAD symbolic branch',h=='ref: '+BRANCH)
    require(label+' exact revision',(ROOT/'.git'/BRANCH).read_text().strip()==HEAD)
packindices=[]
def packed_location(oid):
    if not packindices:
        for p in sorted((ROOT/'.git/objects/pack').glob('*.idx')):
            b=p.read_bytes()
            if b[:8]!=b'\xfftOc\x00\x00\x00\x02':raise ValueError('unsupported object index')
            count=int.from_bytes(b[1028:1032],'big');names=b[1032:1032+20*count]
            packindices.append((p.with_suffix('.pack'),b,count,names))
    wanted=bytes.fromhex(oid)
    for p,b,count,names in packindices:
        lo,hi=0,count
        while lo<hi:
            mid=(lo+hi)//2
            if names[20*mid:20*mid+20]<wanted:lo=mid+1
            else:hi=mid
        if lo<count and names[20*lo:20*lo+20]==wanted:
            at=1032+24*count+4*lo;off=int.from_bytes(b[at:at+4],'big')
            if off&0x80000000:
                at=1032+28*count+8*(off&0x7fffffff);off=int.from_bytes(b[at:at+8],'big')
            return p,off
    raise FileNotFoundError('committed object unavailable '+oid)
def applydelta(base,delta):
    i=0
    def varint():
        nonlocal i
        value=0;shift=0
        while True:
            c=delta[i];i+=1;value|=(c&127)<<shift
            if not c&128:return value
            shift+=7
    if varint()!=len(base):raise ValueError('delta source length')
    size=varint();out=bytearray()
    while i<len(delta):
        op=delta[i];i+=1
        if op&128:
            offset=0;length=0
            for bit in range(4):
                if op&(1<<bit):offset|=delta[i]<<(8*bit);i+=1
            for bit in range(3):
                if op&(1<<(bit+4)):length|=delta[i]<<(8*bit);i+=1
            length=length or 65536;out.extend(base[offset:offset+length])
        elif op:out.extend(delta[i:i+op]);i+=op
        else:raise ValueError('delta zero opcode')
    if len(out)!=size:raise ValueError('delta result length')
    return bytes(out)
def packed_object(path,offset):
    with path.open('rb') as f:
        f.seek(offset);c=f.read(1)[0];kind=(c>>4)&7;size=c&15;shift=4
        while c&128:c=f.read(1)[0];size|=(c&127)<<shift;shift+=7
        base=None
        if kind==6:
            c=f.read(1)[0];distance=c&127
            while c&128:c=f.read(1)[0];distance=((distance+1)<<7)+(c&127)
            base=(path,offset-distance)
        elif kind==7:base=f.read(20).hex()
        dec=zlib.decompressobj();chunks=[]
        while not dec.eof:
            block=f.read(65536)
            if not block:raise ValueError('truncated object pack')
            chunks.append(dec.decompress(block))
        data=b''.join(chunks)
    if len(data)!=size:raise ValueError('packed object size')
    if base is not None:
        bk,bd=packed_object(*base) if isinstance(base,tuple) else obj(base)
        return bk,applydelta(bd,data)
    return {1:b'commit',2:b'tree',3:b'blob',4:b'tag'}[kind],data
def obj(oid):
    path=ROOT/'.git/objects'/oid[:2]/oid[2:]
    if path.exists():b=zlib.decompress(path.read_bytes())
    else:
        kind,data=packed_object(*packed_location(oid));b=kind+b' '+str(len(data)).encode()+b'\0'+data
    require('content-addressed committed object '+oid,hashlib.sha1(b).hexdigest()==oid)
    header,data=b.split(b'\0',1);kind,size=header.split(b' ')
    require('object length '+oid,int(size)==len(data))
    return kind,data
treecache={}
def committed(name):
    if not treecache:
        kind,c=obj(HEAD);require('declared object is commit',kind==b'commit')
        treecache['root']=c.split(b'\n')[0].split()[1].decode()
        report['declaration_commit_unix']=int(re.search(rb'\ncommitter .* (\d+) [+-]\d+\n',c)[1])
    oid=treecache['root']
    for part in name.split('/'):
        if oid not in treecache:
            kind,data=obj(oid);require('committed directory tree',kind==b'tree');entries={};i=0
            while i<len(data):
                j=data.index(b'\0',i);mode,n=data[i:j].split(b' ',1);entries[n.decode()]=(mode,data[j+1:j+21].hex());i=j+21
            treecache[oid]=entries
        mode,oid=treecache[oid][part]
    data=(ROOT/name).read_bytes()
    require('committed regular blob content hash '+name,mode in (b'100644',b'100755') and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid)
    return data
def sourcecheck(pins,label,committed_check=False):
    headcheck(label)
    for n,h in pins.items():
        budget();regular(ROOT/n);require(label+' source '+n,fh(ROOT/n)==h)
        if committed_check: require('exact committed bytes '+n,(ROOT/n).read_bytes()==committed(n))
def artifactcheck(hashes,label):
    inodes=set()
    for n,h in hashes.items():
        budget();s=regular(ROOT/n);key=(s.st_dev,s.st_ino)
        require(label+' unique inode '+n,key not in inodes);inodes.add(key)
        require(label+' artifact '+n,fh(ROOT/n)==h)
def modelcheck(label):
    budget();regular(MODEL);require(label+' original model SHA256',fh(MODEL)==MODEL_SHA)
def ident(t): return {k:t[k] for k in ('slug','content','take')}
def validnum(v): return type(v) in (float,int) and math.isfinite(v) and v>=0
def rowvalid(r):
    return r.get('qc_valid') is True and validnum(r['oracle']) and r['oracle']<1e-6 and all(set(r[k])==set(METRICS) and all(validnum(v) for v in r[k].values()) and r[a]==r[k]['primary'] for a,k in ARMS.items()) and min(r['wet'],r['flatref'])>0
def gate(rows,takes):
    valid=(len(rows)==12 and len({r['slug'] for r in rows})==12 and [ident(r) for r in rows]==[ident(t) for t in takes] and all(rowvalid(r) for r in rows))
    if not valid: return {'valid':False,'passed':False,'disposition':'INCONCLUSIVE','reason':'invalid coverage/score/QC/oracle'}
    ratios=[(min(r['wet'],r['flatref'])-r['net'])/min(r['wet'],r['flatref']) for r in rows]
    med=float(statistics.median(ratios));wins=sum(v>0 for v in ratios)
    groups={g:float(statistics.median(v for r,v in zip(rows,ratios) if r['content']==g)) for g in ('chords','scales')}
    passed=med>=.1-8*math.ulp(.1) and wins>=9 and all(v>0 for v in groups.values())
    return {'valid':True,'passed':passed,'disposition':'PASS' if passed else 'FAIL','median_relative_improvement':med,'strict_wins':wins,'group_medians':groups,'per_take':[{'slug':r['slug'],'relative_improvement':v} for r,v in zip(rows,ratios)]}
def screens(rows,takes,offsets=OFFSETS,timing=False):
    actual={(r['offset'],r['slug']):r for r in rows};out=[]
    coverage=len(rows)==12*len(offsets) and len(actual)==len(rows) and set(actual)=={(o,t['slug']) for o in offsets for t in takes}
    for o in offsets:
        subset=[actual[o,t['slug']] for t in takes]
        g=gate(subset,takes)
        if not all(r.get('valid') is True and type(r['offset']) is int for r in subset): g={'valid':False,'passed':False,'disposition':'INCONCLUSIVE'}
        out.append({'offset':o,'role':'prerequisite' if o==0 else 'robustness' if o in (-3,-2,2,3) else 'diagnostic_only','screen':g})
    valid=coverage and all(s['screen']['valid'] for s in out) and next(s['screen']['passed'] for s in out if s['offset']==0)
    passed=valid and all(s['screen']['passed'] for s in out if s['offset'] in (-3,-2,2,3))
    d={'valid':bool(valid),'passed':bool(passed),'disposition':('PASS' if passed else 'FAIL') if valid else 'INCONCLUSIVE','offset_screens':out,'required_small_offsets':[-3,-2,2,3]}
    return d
def shift64(x,k):
    x=np.asarray(x,dtype=np.float64);y=np.zeros(x.shape,dtype=np.float64)
    # Index convention derived directly from y[n] = x[n-k].
    first=max(k,0);stop=min(len(x),len(x)+k)
    if stop>first:y[first:stop]=x[first-k:stop-k]
    return y
def inverse32(raw,k):
    raw=np.asarray(raw);out=np.zeros(raw.shape,dtype='<f4')
    first=max(-k,0);stop=min(len(raw),len(raw)-k)
    if stop>first:out[first:stop]=raw[first+k:stop+k]
    return out
def norm64(x):
    x=np.asarray(x,dtype=np.float64);return x/(x.std()+1e-9)*.1
def mags(x,windows):
    result=[]
    for n in FFTS:
        padded=np.pad(x,(n//2,n//2),mode='reflect')
        frames=np.lib.stride_tricks.sliding_window_view(padded,n)[::n//4]
        result.append(np.abs(np.fft.rfft(frames*windows[n],axis=-1))+1e-6)
    return result
def spectral(a,b):
    total=0.
    for A,B in zip(a,b): total+=np.linalg.norm(A-B)/(np.linalg.norm(B)+1e-6)+np.mean(np.abs(np.log(A)-np.log(B)))
    return float(total/5)
def filter64(x): return sosfiltfilt(SOS,np.asarray(x,dtype=np.float64),padtype='odd',padlen=27)
def refs(s,windows):
    y=norm64(s['target'][CENTER]);d=norm64(filter64(s['di'])[CENTER])
    return y,mags(y,windows),mags(d,windows)
def score(x,ref,windows):
    budget();p=norm64(np.asarray(x,dtype=np.float64)[CENTER]);low=norm64(filter64(x)[CENTER])
    return {'primary':spectral(mags(p,windows),ref[1]),'canonical_waveform_l1':float(np.mean(np.abs(p-ref[0]))),'raw_lowband':spectral(mags(low,windows),ref[2])}
def changes(r,z):
    d={}
    for a,k in ARMS.items():
        before=z[k]['primary'];delta=r[k]['primary']-before
        d[a]={'primary_absolute_change':delta,'primary_relative_change':delta/before if before>0 else None,
              'canonical_waveform_l1_change':r[k]['canonical_waveform_l1']-z[k]['canonical_waveform_l1'],
              'raw_lowband_change':r[k]['raw_lowband']-z[k]['raw_lowband']}
    s=min(r['wet'],r['flatref']);s0=min(z['wet'],z['flatref'])
    d['advantage']={'primary_absolute_change':(s-r['net'])-(s0-z['net']),'primary_relative_change':(s-r['net'])/s-(s0-z['net'])/s0}
    return d
def aid(x):return {'dtype':str(x.dtype),'samples':len(x),'sha256':sha(x.tobytes())}
def synthetic():
    bits=np.array([0x80000000,0,1,0x3f800001,0xbe000000,0x47f12060]*10,dtype='<u4');x=bits.view('<f4')
    for k in OFFSETS:
        shifted=shift64(x,k).astype(x.dtype);corrected=inverse32(x,k)
        idx=np.arange(len(x))+k;good=(idx>=0)&(idx<len(x))
        require('synthetic inverse exact signed-zero/subnormal bytes '+str(k),corrected[good].tobytes()==x[idx[good]].tobytes() and corrected[~good].tobytes()==np.zeros(sum(~good),dtype='<f4').tobytes() and corrected.dtype.str=='<f4')
        idx=np.arange(len(x))-k;good=(idx>=0)&(idx<len(x))
        require('synthetic finite shift sign edges '+str(k),shifted[good].tobytes()==x[idx[good]].tobytes() and shifted[~good].tobytes()==np.zeros(sum(~good),dtype='<f4').tobytes())
    t=[{'slug':str(i),'take':str(i),'content':'chords' if i<6 else 'scales'} for i in range(12)]
    def rr(v):return [{**z,'qc_valid':True,'oracle':0.,'wet':2.,'net':v,'flatref':1.,'input_scores':{m:2. for m in METRICS},'network_scores':{m:v for m in METRICS},'flatref_scores':{m:1. for m in METRICS}} for z in t]
    require('inclusive gate synthetic',gate(rr(.9),t)['passed'])
    require('stronger competitor synthetic',not gate(rr(.90001),t)['passed'])
    bad=rr(.5);bad[-1]['oracle']=1e-6;require('invalid gate synthetic',gate(bad,t)['disposition']=='INCONCLUSIVE')

def prerequisites():
    require('explicit CPU prefix bytecode little-endian',sys.prefix==PREFIX and sys.dont_write_bytecode and sys.byteorder=='little')
    headcheck('before');report['verifier_sha256']=fh(SELF)
    report['runtime']={'python':sys.version,'prefix':sys.prefix,'packages':{n:importlib.metadata.version(n) for n in ('numpy','scipy','torch')}}
    prov=rj(ROOT/'docs/di-timing-sensitivity-provenance.json');inherited=prov['pins']
    require('53 inherited pins',len(inherited)==53)
    require('ten disjoint own pins',len(OWN)==10 and not set(OWN)&set(inherited))
    pins={**inherited,**{n:fh(ROOT/n) for n in OWN}};sourcecheck(pins,'before',True);report['source_pins']=pins
    text=(ROOT/OWN[2]).read_text();approval=json.loads(re.search(r'<!-- input-shift-approval\n(.*?)\ninput-shift-approval -->',text,re.S)[1])
    same('declaration',{'status':'DECLARED','fresh_independent_review':True,'scope':'known-input-shift-and-truth-inverse-only',
         'review_sha256':pins[OWN[3]],'source_sha256':pins[OWN[0]],'test_sha256':pins[OWN[1]],
         'design_sha256':sha(text.split('## Frozen design\n',1)[1].encode()),'inputs_sha256':inherited['docs/di-timing-sensitivity-inputs.sha256']},approval,0)
    require('approved review exact snapshot','**Declared:' in text and 'Verdict: APPROVE' in (ROOT/OWN[3]).read_text())
    tv=rj(ROOT/OWN[5]);tr=rj(ROOT/OWN[6]);ti=rj(ROOT/OWN[8]);tb=rj(ROOT/OWN[9])
    require('T prerequisite VERIFIED PASS all23734',tv['status']=='VERIFIED' and tv['scientific_disposition']=='PASS' and tv['failures']==[] and len(tv['checks'])==23734 and all(c['passed'] is True for c in tv['checks']))
    same('T53 pins',inherited,tv['source_pins'],0);same('T archived verifier hash',pins[OWN[4]],tv['verifier_sha256'],0)
    manifest=rj(ROOT/'docs/di-domain-pilot-inputs.json');takes=manifest['takes'];correction=rj(ROOT/'docs/di-domain-pilot-v2-inputs.json')
    require('exact original model declaration',manifest['model']=={'path':str(MODEL),'sha256':MODEL_SHA})
    require('panel12 six six distinct',len(takes)==12 and len({t['slug'] for t in takes})==12 and len({t['take'] for t in takes})==12 and all(sum(t['content']==g for t in takes)==6 for g in ('chords','scales')))
    to=(-128,-52,-16,-8,-3,-2,0,2,3,8,16,52,128)
    require('T complete156',tr['complete'] is True and len(tr['rows'])==156)
    same('T rows independently verified',tr['rows'],tv['independent_rows']);same('T payload rows',tr['rows'],tv['derivation_payload']['rows'])
    tg=screens(tr['rows'],takes,to,True);same('T gates recomputed metadata',tg,tr['screen']);same('T verified screen',tg,tv['independent_screen']);same('T payload screen',tg,tv['derivation_payload']['screen'])
    same('T108 payload',tb,tv['derivation_payload']['baseline']);same('T108 independently verified',tb,tv['independent_baseline_replay'])
    require('T108 complete passed errors',tb['complete'] is True and tb['passed'] is True and tb['scalar_count']==108 and tb['absolute_tolerance']==TOL and len(tb['rows'])==12 and [ident(r) for r in tb['rows']]==[ident(t) for t in takes] and all(r['valid'] is True and len(r['errors'])==9 and all(validnum(v) and v<=TOL for v in r['errors'].values()) for r in tb['rows']))
    same('T input identities',ti,tv['inputs'],0)
    archives={'result.json':OWN[6],'provenance.json':OWN[7],'inputs.json':OWN[8],'baseline-replay.json':OWN[9]}
    snapnames={f'tmp/di-timing-sensitivity-20261008/{n}' for n in (*archives,'progress.jsonl')}|{'tmp/di-timing-sensitivity-20261008.log'}
    require('exact T snapshot allowlist',set(tv['primary_artifact_snapshots'])==snapnames)
    for n in sorted(snapnames):
        regular(ROOT/n);b=(ROOT/n).read_bytes();s=tv['primary_artifact_snapshots'][n]
        require('T snapshot bytes '+n,sha(b)==s['sha256'] and len(b)==s['size'])
        base=Path(n).name
        if base in archives:require('T original/archive bytes '+base,b==(ROOT/archives[base]).read_bytes())
        else:same('T progress/log rows '+base,[json.loads(l) for l in b.splitlines()],tr['rows'],0)
    hashes={}
    expected={f'tmp/di-morgan-control-20261008/{s}/{t["slug"]}.npz' for s in ('prepare','render','infer') for t in takes}|{f'tmp/di-morgan-flatref-20261008/{t["slug"]}.npz' for t in takes}
    for line in (ROOT/'docs/di-timing-sensitivity-inputs.sha256').read_text().splitlines():
        h,n=line.split('  ');require('manifest unique allowed path '+n,n in expected and n not in hashes and re.fullmatch('[a-f0-9]{64}',h) is not None);hashes[n]=h
    require('exact48 manifest',set(hashes)==expected and len(hashes)==48)
    for label,x in [('T provenance',prov),('T result',tr),('T verification',tv)]:same(label+'48 artifacts',hashes,x['input_artifacts'],0)
    same('T inputs48 artifacts',hashes,ti['artifacts'],0)
    prior=rj(ROOT/'docs/di-morgan-flatref-verification.json');control=rj(ROOT/'docs/di-morgan-control-verification.json');prep=rj(ROOT/'docs/di-morgan-control-prepare.json');original=rj(ROOT/'docs/di-morgan-flatref.json')
    for label,v,count,verifier in [('flatref',prior,1215,'docs/research/di-morgan-flatref-independent-2026-10-08.py'),('control',control,767,'docs/research/di-morgan-control-independent-2026-10-08.py')]:
        require(label+' inherited independent verified',v['status']=='VERIFIED_WITH_EVIDENCE_LIMITS' and v['failures']==[] and len(v['checks'])==count and all(c['passed'] is True for c in v['checks']) and v['verifier_sha256']==pins[verifier])
        same(label+' source identities',v['source_pins'],{n:pins[n] for n in v['source_pins']},0)
    require('control renderer canary',control['canary']['passed'] is True)
    same('original baseline stronger gate',gate(original['rows'],takes),original['screen'])
    old36={n:h for n,h in hashes.items() if n.startswith('tmp/di-morgan-control-')}
    same('original36',old36,original['input_artifacts'],0);same('prior original36',old36,prior['input_artifacts'],0)
    for t,r,p,c,v in zip(takes,original['rows'],prep['rows'],control['preparation'],prior['independent_rows']):
        require(t['slug']+' inherited identity QC oracle',ident(t)==ident(r)==ident(p)==ident(c) and p['qc_valid'] is True and p['qc']['valid'] is True and c['qc']['valid'] is True and rowvalid(r))
        same(t['slug']+' inherited original scalars',r,{k:v[k] for k in r});same(t['slug']+' QC',p['qc'],c['qc']);same(t['slug']+' oracle scores',p['oracle_scores'],c['oracle_scores']);same(t['slug']+' oracle primary',r['oracle'],p['oracle_scores']['primary'])
    require('original correction spec',correction['schema']==2 and correction['window_family']=='torch32' and correction['window_dtype']=='<f4' and correction['tolerance']==TOL and correction['original_inputs_sha256']==pins['docs/di-domain-pilot-inputs.json'] and correction['windows']=='docs/di-domain-metric-probe-windows.json.gz')
    b=(ROOT/correction['windows']).read_bytes();require('coefficient archive hash',sha(b)==correction['windows_sha256']);raw=gzip.decompress(b);require('coefficient text hash',sha(raw)==correction['windows_raw_sha256']);table=json.loads(raw);require('five FFT coefficients',set(table)=={str(n) for n in FFTS})
    windows={};report['windows']={}
    for n in FFTS:
        r=table[str(n)]['torch32'];bits=r['bits'];require('coefficient bit shape '+str(n),r['dtype']=='<f4' and len(bits)==n and all(type(v) is int and 0<=v<2**32 for v in bits));b=np.asarray(bits,dtype='<u4').tobytes();require('coefficient bit hash '+str(n),sha(b)==r['sha256']);windows[n]=np.frombuffer(b,dtype='<f4').astype(np.float64);report['windows'][str(n)]=sha(b)
    report.update(input_artifacts=hashes,attribution=manifest['attribution'],inherited_limits={'control':control['limitations'],'flatref':prior['limitations']})
    require('prerequisite checks all pass before arrays',not report['failures'])
    modelcheck('after declaration before arrays');artifactcheck(hashes,'all48 before first load');event('all48 hashed before first array load')
    loaded={};identities={};access=[]
    for i,t in enumerate(takes):
        slug=t['slug'];s={}
        for stage,members in [('prepare',{'di':'di','target':'target'}),('render',{'baseline':'wet'}),('infer',{'prediction':'net'}),('flatref',{'flatref':'flatref'})]:
            name=f'tmp/di-morgan-flatref-20261008/{slug}.npz' if stage=='flatref' else f'tmp/di-morgan-control-20261008/{stage}/{slug}.npz'
            artifactcheck({name:hashes[name]},'immediate before load')
            with np.load(ROOT/name,allow_pickle=False) as z:
                for member,key in members.items():
                    x=z[member];require(slug+' finite active '+key,x.shape==(N,) and x.dtype.kind=='f' and np.isfinite(x).all() and float(np.std(x))>0);x.flags.writeable=False;s[key]=x;access.append({'path':name,'member':member,**aid(x)})
        require(slug+' original dtype hash identities',s['net'].dtype.str=='<f4' and sha(s['net'].tobytes())==control['replay'][i]['prediction_sha256_float32'] and sha(s['target'].astype('<f8').tobytes())==control['preparation'][i]['target_sha256'] and s['flatref'].dtype.str=='<f8' and sha(s['flatref'].tobytes())==prior['waveform_comparison'][i]['primary_sha256_float64'])
        w=prior['waveform_comparison'][i];require(slug+' verified saved flatref artifact',w['byte_identical'] is True and w['max_absolute_error']==0 and w['npz_sha256']==hashes[f'tmp/di-morgan-flatref-20261008/{slug}.npz'])
        identities[slug]={k:aid(x) for k,x in s.items()};loaded[slug]=s
        d=s['di'].astype(np.float64);frame=np.sqrt(np.mean(d.reshape(-1,480)**2,axis=1));qc={'rms':float(np.sqrt(np.mean(d**2))),'clipped_fraction':float(np.mean(np.abs(d)>=.999)),'active_fraction':float(np.mean(frame>frame.max()*.01))}
        require(slug+' fresh score DI QC',qc['rms']>=1e-5 and qc['clipped_fraction']<=1e-4 and qc['active_fraction']>=.8);same(slug+' score DI QC archive',qc,prep['rows'][i]['qc']['metrics']['score'])
    same('original five member identities',{'artifacts':hashes,'waveforms':identities},ti,0);artifactcheck(hashes,'after five members')
    for t in takes:
        slug=t['slug'];name=f'tmp/di-morgan-control-20261008/render/{slug}.npz';artifactcheck({name:hashes[name]},'immediate net_input before load')
        with np.load(ROOT/name,allow_pickle=False) as z:x=z['net_input']
        artifactcheck({name:hashes[name]},'immediate net_input after load')
        require(slug+' input full6s finite active',x.shape==(N,) and x.dtype.kind=='f' and np.isfinite(x).all() and float(x.std())>0)
        wet=loaded[slug]['wet'];require(slug+' original52 overlap exact dtype bytes',x.dtype==wet.dtype and x[52:].tobytes()==wet[:-52].tobytes());x.flags.writeable=False;loaded[slug]['net_input']=x;identities[slug]['net_input']=aid(x);access.append({'path':name,'member':'net_input',**aid(x)})
    report['array_access_audit']=access;require('only six allowed members48 files72 member accesses',len(access)==72 and len({a['path'] for a in access})==48 and {a['member'] for a in access}=={'di','target','baseline','prediction','flatref','net_input'})
    report['inputs']={'artifacts':hashes,'waveforms':identities};artifactcheck(hashes,'after all loading');sourcecheck(pins,'after loading')
    return manifest,takes,loaded,windows,original,pins,hashes

def build_own_network(torch):
    nn=torch.nn
    class OwnNet(nn.Module):
        def __init__(self):
            super().__init__();self.enc=nn.ModuleList();self.dec=nn.ModuleList();widths=[32,64,128,256,512];incoming=1
            for width in widths:
                self.enc.append(nn.Sequential(nn.Conv1d(incoming,width,kernel_size=8,stride=4,padding=2),nn.GELU(),nn.Conv1d(width,2*width,kernel_size=1),nn.GLU(dim=1)));incoming=width
            self.mid=nn.ModuleList([nn.Sequential(nn.Conv1d(512,512,kernel_size=3,padding=d,dilation=d),nn.GELU(),nn.Conv1d(512,512,kernel_size=1)) for d in [1,3,9,27]])
            for width,output in zip([512,256,128,64,32],[256,128,64,32,1]):
                layers=[nn.Conv1d(width,2*width,kernel_size=3,padding=1),nn.GLU(dim=1),nn.ConvTranspose1d(width,output,kernel_size=8,stride=4,padding=2)]
                if output!=1:layers.append(nn.GELU())
                self.dec.append(nn.Sequential(*layers))
        def forward(self,x):
            length=x.shape[-1];h=torch.nn.functional.pad(x,(0,(-length)%1024));skips=[]
            for encoder in self.enc:h=encoder(h);skips.append(h)
            for block in self.mid:h=h+block(h)
            for decoder in self.dec:
                skip=skips.pop();h=decoder(h+skip[...,:h.shape[-1]])
            return h[...,:length]
    return OwnNet().cpu()
def reconstruct(net,raw,torch):
    budget();x=np.asarray(raw,dtype='<f4');n=len(x);window=N;hop=240000;overlap=window-hop
    output=np.zeros(n,dtype=np.float32);denominator=np.zeros(n,dtype=np.float32)
    fade=np.ones(window,dtype=np.float32);fade[:overlap]=np.linspace(0,1,overlap);fade[-overlap:]=np.linspace(1,0,overlap)
    starts=list(range(0,max(1,n-window+1),hop))
    if starts[-1]+window<n:starts.append(max(0,n-window))
    with torch.no_grad():
        for start in starts:
            segment=x[start:start+window].astype(np.float32)
            scale=segment.std()+1e-9
            tensor=torch.tensor(segment/scale*.1,device=torch.device('cpu'))[None,None]
            # Division, multiplication, zero-initialized accumulation, and final
            # division are deliberately distinct original float32 operations.
            predicted=net(tensor)[0,0].cpu().numpy()/.1*scale
            weights=fade[:len(segment)].copy()
            if start==0:weights[:overlap]=1
            if start+window>=n:weights[-min(overlap,len(segment)):]=1
            output[start:start+len(segment)]+=predicted*weights
            denominator[start:start+len(segment)]+=weights
    y=output/np.maximum(denominator,1e-6);budget();return y
def evidence(t,k,x,raw,corrected,original):
    name=f"{t['slug']}.offset-{k:+d}.npz";b=io.BytesIO()
    np.savez_compressed(b,raw_prediction=raw,offset=np.int64(k),corrected_prediction=corrected);data=b.getvalue()
    d={'prediction_file':name,'prediction_file_sha256':sha(data),'imposed_offset':k,'inverse_offset':-k,'input':aid(x),
       'input_sha256_float32':sha(np.asarray(x,dtype='<f4').tobytes()),'original_prediction_sha256_float32':sha(np.asarray(original,dtype='<f4').tobytes()),
       'raw_prediction_dtype':str(raw.dtype),'raw_prediction_sha256':sha(raw.tobytes()),'corrected_prediction_sha256':sha(corrected.tobytes())}
    return d,{'file':name,'npz_sha256':sha(data),'npz_base64':base64.b64encode(data).decode(),'raw_identity':aid(raw),'corrected_identity':aid(corrected)}
def derive(manifest,takes,loaded,windows,original,pins,hashes):
    synthetic();zero=[];replay=[];fixed={}
    for t,archived in zip(takes,original['rows']):
        s=loaded[t['slug']];ref=refs(s,windows);fixed[t['slug']]=ref
        row={**ident(t),'offset':0,'qc_valid':archived['qc_valid'],'oracle':archived['oracle']}
        for arm,key in ARMS.items():row[key]=score(s[arm],ref,windows);row[arm]=row[key]['primary']
        require(t['slug']+' baseline valid',rowvalid(row))
        errors={a+'.'+m:abs(row[k][m]-archived[k][m]) for a,k in ARMS.items() for m in METRICS}
        for a,k in ARMS.items():same(t['slug']+' replay '+a,row[k],archived[k])
        replay.append({**ident(t),'valid':True,'scores':{k:row[k] for k in ARMS.values()},'errors':errors,'nonfinite_diagnostic_fields':[]});zero.append(row)
    baseline={'complete':True,'passed':all(all(v<=TOL for v in r['errors'].values()) for r in replay) and gate(zero,takes)['passed'],'scalar_count':108,'absolute_tolerance':TOL,'rows':replay,'screen':gate(zero,takes)}
    same('original stronger zero replay screen',baseline['screen'],original['screen'])
    report['independent_baseline_replay']=baseline;event('all108 original scalars derived; persisting before model import/load/inference');save()
    persisted=rj(OUT);require('108 replay durable readback',persisted['independent_baseline_replay']==baseline);del persisted
    require('108 scalar positive control permits model',baseline['passed'] and not report['failures'])
    artifactcheck(hashes,'after108 before inference');sourcecheck(pins,'after108 before inference');modelcheck('immediate before Torch load')
    import torch
    torch.set_num_threads(2);net=build_own_network(torch);modelcheck('immediate before checkpoint load');net.load_state_dict(torch.load(MODEL,map_location='cpu',weights_only=True));net.eval()
    require('original CPU eval threads2',torch.get_num_threads()==2 and not net.training and all(p.device.type=='cpu' for p in net.parameters()))
    report['model']={'path':str(MODEL),'sha256':MODEL_SHA,'threads':torch.get_num_threads(),'eval':not net.training,'device':'cpu','state_shapes':{k:list(v.shape) for k,v in net.state_dict().items()}}
    predictions={};evs={};archives={};basee=[];newzero=[]
    for t,base,archived in zip(takes,zero,original['rows']):
        s=loaded[t['slug']];raw=reconstruct(net,s['net_input'],torch);corrected=raw.copy()
        details,archive=evidence(t,0,s['net_input'],raw,corrected,s['net']);archives[archive['file']]=archive
        exact=raw.dtype==s['net'].dtype and raw.dtype.str=='<f4' and raw.shape==s['net'].shape and raw.tobytes()==s['net'].tobytes()
        check(t['slug']+' original baseline exact float32 bytes including signed zeros',exact)
        sc=score(corrected,fixed[t['slug']],windows);errors={m:abs(sc[m]-archived['network_scores'][m]) for m in METRICS};same(t['slug']+' direct ORIGINAL36 inference scores',sc,archived['network_scores'])
        valid=exact and all(v<=TOL for v in errors.values()) and np.isfinite(raw).all()
        item={**ident(t),'offset':0,'valid':bool(valid),**details,'byte_identical':exact,'scores':sc,'errors':errors,'nonfinite_diagnostic_fields':[]};basee.append(item)
        row=copy.deepcopy(base);row.update(network_scores=sc,net=sc['primary'],valid=bool(valid));newzero.append(row)
        predictions[0,t['slug']]=(raw,corrected);evs[0,t['slug']]=details
    bi={'complete':True,'passed':all(r['valid'] for r in basee) and gate(newzero,takes)['passed'],'scalar_count':36,'absolute_tolerance':TOL,'rows':basee,'screen':gate(newzero,takes)}
    report['independent_baseline_inference_replay']=bi;report['independent_prediction_archives']=archives
    event('all12 baseline bytes and direct original36 scores derived; persisting before shifted inference');save();persisted=rj(OUT)
    require('12 exact baseline barrier durable readback',persisted['independent_baseline_inference_replay']==bi and persisted['independent_prediction_archives']==archives);del persisted
    require('12 byte36 score zero PASS barrier permits shifts',bi['passed'] and not report['failures'])
    artifactcheck(hashes,'before first shifted inference');sourcecheck(pins,'before first shifted inference');modelcheck('before first shifted inference')
    rows=[]
    for k in OFFSETS:
        for t,base in zip(takes,newzero):
            s=loaded[t['slug']]
            if k:
                x=shift64(s['net_input'],k).astype(s['net_input'].dtype);raw=reconstruct(net,x,torch);corrected=inverse32(raw,k)
                require(t['slug']+' corrected little-endian32 '+str(k),raw.dtype.str=='<f4' and corrected.dtype.str=='<f4' and np.isfinite(raw).all())
                idx=np.arange(N)+k;good=(idx>=0)&(idx<N)
                require(t['slug']+' corrected retained raw exact bytes '+str(k),corrected[good].tobytes()==raw[idx[good]].tobytes() and corrected[~good].tobytes()==np.zeros(sum(~good),dtype='<f4').tobytes())
                details,archive=evidence(t,k,x,raw,corrected,s['net']);archives[archive['file']]=archive
                row=copy.deepcopy(base);sc=score(corrected,fixed[t['slug']],windows);row.update(offset=k,network_scores=sc,net=sc['primary'])
                predictions[k,t['slug']]=(raw,corrected);evs[k,t['slug']]=details
            else:row=copy.deepcopy(base);details=evs[0,t['slug']]
            require(t['slug']+' case valid '+str(k),rowvalid(row));row.update(details);row.update(valid=True,changes_from_zero=changes(row,base))
            path=f"tmp/di-morgan-control-20261008/infer/{t['slug']}.npz";row.update(original_prediction_file=path,original_prediction_file_sha256=hashes[path]);rows.append(row)
        event('independently derived all12 cases offset '+str(k))
    screen=screens(rows,takes);report['independent_rows']=rows;report['independent_screen']=screen
    report['derivation_payload']={'baseline':baseline,'baseline_inference':bi,'rows':rows,'screen':screen,'inputs':report['inputs'],'prediction_archives':archives}
    require('complete independent60 waves rows5 screens',len(rows)==60 and len(predictions)==60 and len(archives)==60 and len(screen['offset_screens'])==5)
    artifactcheck(hashes,'after complete independent derivation');sourcecheck(pins,'after complete independent derivation');modelcheck('after complete independent derivation')
    event('ALL independent derivations complete; fsync and readback BEFORE opening primary');save()
    persisted=rj(OUT);require('full derivation exact durable readback',persisted['derivation_payload']==report['derivation_payload']);del persisted
    report['derivation_readback_utc']=utc();report['derivation_file_sha256_before_primary']=fh(OUT)
    return predictions

def primary_compare(manifest,takes,pins,hashes,predictions):
    global primary_allowed
    primary_allowed=True;report['primary_numerical_values_unread']=False;event('primary read barrier opened after complete saved derivation readback')
    names=['result.json','provenance.json','inputs.json','baseline-replay.json','baseline-inference-replay.json','progress.jsonl']
    snapshots={};data={}
    for name in names:
        p=PRIMARY/name;regular(p);b=p.read_bytes();snapshots[str(p.relative_to(ROOT))]={'sha256':sha(b),'size':len(b),'mtime_ns':p.stat().st_mtime_ns};data[name]=b
    regular(LOG);lb=LOG.read_bytes();snapshots[str(LOG.relative_to(ROOT))]={'sha256':sha(lb),'size':len(lb),'mtime_ns':LOG.stat().st_mtime_ns}
    result=json.loads(data['result.json']);prov=json.loads(data['provenance.json']);inputs=json.loads(data['inputs.json']);br=json.loads(data['baseline-replay.json']);bi=json.loads(data['baseline-inference-replay.json'])
    same('primary108 barrier',report['independent_baseline_replay'],br);same('primary12 byte36 barrier',report['independent_baseline_inference_replay'],bi)
    same('primary all60 rows',report['independent_rows'],result['rows']);same('primary all5 gates metrics',report['independent_screen'],result['screen']);same('primary inputs all identities',report['inputs'],inputs,0)
    expected_result={'complete':True,'rows':report['independent_rows'],'screen':report['independent_screen'],'input_artifacts':hashes,'elapsed_seconds':result['elapsed_seconds'],'attribution':manifest['attribution'],'interpretation':'Known input shifts with known inverse; finite padding/window normalization included. Dependent clean Morgan controls; no isolated stride cause, native or song product claim.'}
    same('primary complete result schema and all fields',expected_result,result)
    require('primary bounded runtime',type(result['elapsed_seconds']) in (int,float) and 0<result['elapsed_seconds']<900)
    expected_prov={'pins':pins,'git_revision':HEAD,'input_artifacts':hashes,'python':sys.version,'prefix':PREFIX,'started_unix':prov['started_unix'],'budget_seconds':900,'scope':'known-input-shift-and-truth-inverse-only','offsets':list(OFFSETS),'attribution':manifest['attribution'],'thread_count':2,'model':manifest['model'],'packages':report['runtime']['packages']}
    same('primary provenance schema environment source model HEAD',expected_prov,prov,0)
    require('declaration committed before primary',report['declaration_commit_unix']<=prov['started_unix'])
    progress=[json.loads(l) for l in data['progress.jsonl'].splitlines()];stdout=[json.loads(l) for l in lb.splitlines()]
    same('stdout exactly progress all72 stage records',progress,stdout,0)
    require('progress72 ordered stages12 plus60',len(progress)==72 and all(r.get('stage')=='baseline-inference' for r in progress[:12]) and all(r.get('stage')=='cases' for r in progress[12:]))
    strip=lambda r:{k:v for k,v in r.items() if k!='stage'}
    same('baseline12 stage versus baseline-inference replay',[strip(r) for r in progress[:12]],bi['rows'],0)
    same('cases60 stage versus result rows only stage removed',[strip(r) for r in progress[12:]],result['rows'],0)
    same('baseline12 progress versus own derivation',report['independent_baseline_inference_replay']['rows'],[strip(r) for r in progress[:12]])
    same('cases60 progress versus own derivation',report['independent_rows'],[strip(r) for r in progress[12:]])
    bytechecks=[]
    expected_files={r['prediction_file'] for r in report['independent_rows']}
    require('primary exactly60 prediction file names',{p.name for p in PRIMARY.glob('*.npz')}==expected_files)
    for row in report['independent_rows']:
        budget();k,slug=row['offset'],row['slug'];p=PRIMARY/row['prediction_file'];regular(p);before=fh(p)
        snapshots[str(p.relative_to(ROOT))]={'sha256':before,'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
        check(row['prediction_file']+' exact NPZ serialized bytes hash',before==row['prediction_file_sha256'])
        with np.load(p,allow_pickle=False) as z:
            check(p.name+' exact saved schema',set(z.files)=={'raw_prediction','offset','corrected_prediction'})
            raw=z['raw_prediction'];corrected=z['corrected_prediction'];offset=z['offset']
        check(p.name+' offset scalar int64',offset.shape==() and offset.dtype==np.dtype('int64') and int(offset)==k)
        for key,observed,expected in [('raw',raw,predictions[k,slug][0]),('corrected',corrected,predictions[k,slug][1])]:
            exact=observed.shape==expected.shape and observed.dtype.str==expected.dtype.str=='<f4' and observed.tobytes()==expected.tobytes()
            check(p.name+' '+key+' exact dtype little-endian32 shape bytes signed zeros',exact)
            bytechecks.append({'file':p.name,'member':key,'byte_identical':exact,'independent_sha256':sha(expected.tobytes()),'primary_sha256':sha(observed.tobytes()),'dtype':observed.dtype.str,'samples':len(observed)})
        check(p.name+' saved known inverse exact bytes',corrected.dtype.str=='<f4' and corrected.tobytes()==inverse32(raw,k).tobytes())
        require(p.name+' immutable across read',before==fh(p))
    report['prediction_byte_checks']=bytechecks;report['primary_artifact_snapshots']=snapshots
    require('all120 raw corrected float32 byte checks',len(bytechecks)==120 and all(x['byte_identical'] for x in bytechecks))
    m=lambda n:(PRIMARY/n).stat().st_mtime_ns
    zeros=[f"{t['slug']}.offset-+0.npz" for t in takes];shifted=[f"{t['slug']}.offset-{k:+d}.npz" for k in OFFSETS if k for t in takes]
    check('saved-time108 replay before all zero predictions',m('baseline-replay.json')<=min(m(n) for n in zeros))
    check('saved-time complete12 replay after all zeros before all48 shifts',max(m(n) for n in zeros)<=m('baseline-inference-replay.json')<=min(m(n) for n in shifted))
    check('saved-time result after60 predictions',max(m(n) for n in zeros+shifted)<=m('result.json'))
    require('no primary failure file',(PRIMARY/'failure.json').exists() is False)
    sourcecheck(pins,'final');artifactcheck(hashes,'final');modelcheck('final')
    for name,s in snapshots.items():require('primary snapshot stable final '+name,fh(ROOT/name)==s['sha256'] and (ROOT/name).stat().st_size==s['size'])
    report['scientific_disposition']=report['independent_screen']['disposition']

def numerical_fingerprint(payload):
    def strip(value):
        if isinstance(value,dict):return {k:strip(v) for k,v in value.items() if k!='nonfinite_diagnostic_fields'}
        if isinstance(value,list):return [strip(v) for v in value]
        return value
    return sha(json.dumps(strip(payload),sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def resume_saved_schema():
    """Repair a bookkeeping omission from saved evidence; no numerical reexecution."""
    global report,primary_allowed,read_events
    old=rj(OUT)
    if old['status']!='NOTVERIFIED' or len(old['failures'])!=36 or 'derivation_readback_utc' not in old:
        raise ValueError('schema resume requires the complete retained initial comparison')
    for failure in old['failures']:
        if not failure['name'].endswith('.keys') or failure['detail']['saved']!=failure['detail']['own']+['nonfinite_diagnostic_fields']:
            # Key insertion order is not scientifically meaningful; exact set is.
            own=set(failure['detail']['own']);saved=set(failure['detail']['saved'])
            if saved-own!={'nonfinite_diagnostic_fields'} or own-saved:raise ValueError('resume refuses any other mismatch')
    fingerprint=numerical_fingerprint(old['derivation_payload'])
    attempt={k:old[k] for k in ('status','scientific_disposition','checks','failures','comparison_statistics','verifier_sha256','elapsed_seconds','primary_access_audit')}
    attempt['reason']='Verifier schema omission only: required empty nonfinite_diagnostic_fields lists absent in independent replay metadata.'
    attempt['complete_derivation_numerical_fingerprint']=fingerprint
    attempt['raw_corrected_prediction_byte_checks']=old['prediction_byte_checks']
    attempt['stdout_log']='Initial bounded run completed exit0; 53958 checks, 36 schema-only failures, max scalar discrepancy 8.255618411112664e-12. Full numerical derivation had been fsynced/read back before any primary access; all12 original and all120 primary float32 member-byte checks passed.'
    report=old;report['verification_attempts']=[attempt];report['checks']=[];report['failures']=[];report['status']='RUNNING'
    breakdown={c:{'numeric_comparisons':0,'max_absolute_discrepancy':0.,'max_discrepancy_field':None} for c in ('new_primary_numerical_comparisons','original108_and_direct36_replays','inherited_metadata_comparisons')}
    primary_prefixes=('primary108 barrier','primary12 byte36 barrier','primary all60 rows','primary all5 gates','primary complete result','baseline12 progress versus own','cases60 progress versus own')
    for item in attempt['checks']:
        d=item.get('detail');name=item['name']
        if not isinstance(d,dict) or 'absolute_error' not in d:continue
        category='new_primary_numerical_comparisons' if name.startswith(primary_prefixes) else 'original108_and_direct36_replays' if (' replay ' in name or ' direct ORIGINAL36 inference scores' in name or name=='original stronger zero replay screen') else 'inherited_metadata_comparisons'
        s=breakdown[category];s['numeric_comparisons']+=1
        if d['absolute_error']>s['max_absolute_discrepancy']:s.update(max_absolute_discrepancy=d['absolute_error'],max_discrepancy_field=name)
    report['discrepancy_breakdown']=breakdown
    report['comparison_statistics']={'finite_numeric_fields_checked':0,'max_absolute_discrepancy':0.,'max_discrepancy_field':None}
    report['verifier_sha256']=fh(SELF);report['initial_independent_derivation_source_sha256']=attempt['verifier_sha256']
    for key in ('independent_baseline_replay','independent_baseline_inference_replay'):
        for row in report[key]['rows']:row['nonfinite_diagnostic_fields']=[]
    for key in ('baseline','baseline_inference'):
        for row in report['derivation_payload'][key]['rows']:row['nonfinite_diagnostic_fields']=[]
    require('schema correction leaves entire numerical derivation exactly unchanged',fingerprint==numerical_fingerprint(report['derivation_payload']))
    report['schema_correction']={'field':'nonfinite_diagnostic_fields','value':[],'reason':attempt['reason'],
        'numerical_fingerprint_before':fingerprint,'numerical_fingerprint_after':numerical_fingerprint(report['derivation_payload']),
        'no_new_model_inference_or_scoring':True,'original_failures_retained':36,'utc':utc()}
    event('schema-only correction; all original derivations/predictions reused from saved report');save()
    saved=rj(OUT);require('corrected saved derivation readback before renewed comparison',saved['derivation_payload']==report['derivation_payload']);del saved
    predictions={}
    for row in report['independent_rows']:
        archive=report['independent_prediction_archives'][row['prediction_file']];b=base64.b64decode(archive['npz_base64'])
        require(row['prediction_file']+' retained independent archive hash',sha(b)==archive['npz_sha256']==row['prediction_file_sha256'])
        with np.load(io.BytesIO(b),allow_pickle=False) as z:predictions[row['offset'],row['slug']]=(z['raw_prediction'],z['corrected_prediction'])
    primary_allowed=True
    manifest=rj(ROOT/'docs/di-domain-pilot-inputs.json');sourcecheck(report['source_pins'],'schema recompare before');artifactcheck(report['input_artifacts'],'schema recompare before');modelcheck('schema recompare before')
    primary_compare(manifest,manifest['takes'],report['source_pins'],report['input_artifacts'],predictions)
    report['stability_summary']={'head_before':HEAD,'head_after':(ROOT/'.git'/BRANCH).read_text().strip(),'source_dependency_pins':len(report['source_pins']),
        'original_artifacts':len(report['input_artifacts']),'model_sha256_before':MODEL_SHA,'model_sha256_after':fh(MODEL),
        'primary_artifacts':len(report['primary_artifact_snapshots']),'all_before_after_checks_passed':not report['failures']}
    report['check_counts']={'initial_complete_run':len(attempt['checks']),'final_saved_evidence_comparison':len(report['checks']),
        'total_recorded_check_events':len(attempt['checks'])+len(report['checks']),'initial_schema_mismatches_preserved':36,
        'current_unresolved_mismatches':len(report['failures'])}
    # The initial independently observed maximum includes original108/direct36
    # archive replay comparisons, which are deliberately not recomputed here.
    if attempt['comparison_statistics']['max_absolute_discrepancy']>report['comparison_statistics']['max_absolute_discrepancy']:
        report['comparison_statistics']['max_absolute_discrepancy']=attempt['comparison_statistics']['max_absolute_discrepancy']
        report['comparison_statistics']['max_discrepancy_field']=attempt['comparison_statistics']['max_discrepancy_field']
    report['status']='VERIFIED' if not report['failures'] else 'NOTVERIFIED'
    if report['failures']:report['scientific_disposition']='INCONCLUSIVE'
    event('schema-only comparison finished');save()
    print(json.dumps({'status':report['status'],'scientific_disposition':report['scientific_disposition'],'checks':len(report['checks']),'failures':len(report['failures']),'preserved_schema_failures':36,'max_scalar_discrepancy':report['comparison_statistics']['max_absolute_discrepancy']}),flush=True)
def main():
    global np,SOS,sosfiltfilt
    sys.addaudithook(audit)
    try:
        import numpy as np
        from scipy.signal import butter,sosfiltfilt
        SOS=butter(4,(80,4000),btype='bandpass',fs=48000,output='sos')
        if sys.argv[1:]==['--resume-saved-schema']:
            resume_saved_schema();return
        if sys.argv[1:]:raise ValueError('only --resume-saved-schema or no arguments')
        event('independent verifier started; primary numeric reads blocked')
        context=prerequisites();predictions=derive(*context);primary_compare(context[0],context[1],context[5],context[6],predictions)
        report['status']='VERIFIED' if not report['failures'] else 'NOTVERIFIED'
        if report['failures']:report['scientific_disposition']='INCONCLUSIVE'
        event('independent verification finished');save()
        print(json.dumps({'status':report['status'],'scientific_disposition':report['scientific_disposition'],'checks':len(report['checks']),'failures':len(report['failures']),'max_scalar_discrepancy':report['comparison_statistics']['max_absolute_discrepancy']}),flush=True)
    except BaseException as error:
        report['status']='NOTVERIFIED';report['scientific_disposition']='INCONCLUSIVE';report['exception']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()};save();print(report['exception']['traceback'],flush=True);raise

if __name__=='__main__':main()
