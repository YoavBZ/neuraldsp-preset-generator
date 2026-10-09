"""Fresh phase verifier. No repository code imports; fixed original asset allowlist.

derive persists and reads back complete independent evidence before compare may
open any primary phase artifact. FFT-conjugate inverse is intentionally distinct
from the primary periodic time-domain recurrence. No waveform payloads in JSON.
"""
import argparse
import gzip
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import traceback

ROOT = Path('/Users/yoavbz/projects/neuraldsp-preset-generator')
OWN = ROOT / 'tmp/di-phase-independent-arrays'
SELF = ROOT / 'tmp/di-phase-independent.py'
REV = '03b8c00e848727e1864fd948b2a588fae8b3f34a'
CPU = '/Users/yoavbz/ndsp-presets/tools/learn-venv'
PRIMARY = ROOT / 'tmp/di-phase-control-20261008'
N = 288000
A = -0.9
METRICS = ('primary', 'canonical_waveform_l1', 'raw_lowband')
ARMS = {'wet': 'input_scores', 'net': 'network_scores', 'flatref': 'flatref_scores'}
EXTRA = ('learn/di_phase_control.py', 'tests/test_di_phase_control.py',
         'docs/di-phase-control-plan.md', 'docs/research/di-phase-control-review-2026-10-08.md',
         'docs/research/di-input-shift-control-independent-2026-10-08.py',
         'docs/di-input-shift-control-verification.json.gz',
         'docs/di-input-shift-control-verification-archive.json',
         'docs/research/di-input-shift-control-verification-2026-10-08.md',
         'docs/di-input-shift-control-results.md',
         'docs/di-input-shift-control-provenance.json', 'docs/di-input-shift-control-inputs.json',
         'docs/di-input-shift-control-baseline-replay.json',
         'docs/di-input-shift-control-baseline-inference-replay.json', 'docs/di-input-shift-control.json')
CONFIG = {'a': A, 'samples': N, 'sample_rate': 48000,
          'formula': '(a+exp(-j*2*pi*k/N))/(1+a*exp(-j*2*pi*k/N))',
          'dc': 1.0, 'nyquist': -1.0, 'boundary': 'periodic',
          'transform_dtype': 'float64', 'model_input_dtype': '<f4',
          'renderer_latency_samples': 52, 'inverse_prediction': False,
          'control_tolerance': 1e-12, 'quantized_inverse_tolerance': 1e-6}
CHECKS = []
START = time.monotonic()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def regular(path):
    path = Path(path)
    if path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError('nonregular/aliased input: ' + str(path))
    return path


def blob(path):
    return regular(path).read_bytes()


def read(path):
    return json.loads(blob(path))


def persist(path, value):
    data = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    with path.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    return sha(data)


def check(name, passed, category='new', **details):
    CHECKS.append(dict(name=name, passed=bool(passed), category=category, **details))


def require(name, passed, category='new', **details):
    check(name, passed, category, **details)
    if not passed:
        raise ValueError(name)


def tick(stage):
    elapsed = time.monotonic() - START
    entry = dict(stage=stage, unix=time.time(), elapsed_seconds=elapsed)
    with (OWN / 'transcript.jsonl').open('a') as f:
        f.write(json.dumps(entry) + '\n')
        f.flush()
        os.fsync(f.fileno())
    print(stage, round(elapsed, 3), flush=True)
    if elapsed > 900:
        raise TimeoutError('independent execution budget exceeded')


def identity(row):
    return {k: row[k] for k in ('slug', 'content', 'take')}


def member(x):
    return dict(dtype=str(x.dtype), shape=list(x.shape), sha256=sha(x.tobytes()))


def wave_identity(x):
    return dict(dtype=str(x.dtype), samples=len(x), sha256=sha(x.tobytes()))


def archive(path, arrays):
    import numpy as np
    arrays = {k: np.asarray(v) for k, v in arrays.items()}
    with path.open('xb') as f:
        np.savez_compressed(f, **arrays)
        f.flush()
        os.fsync(f.fileno())
    manifest = dict(file=path.name, sha256=sha(blob(path)),
                    members={k: member(v) for k, v in arrays.items()})
    with np.load(path, allow_pickle=False) as z:
        require('own NPZ member coverage ' + path.name, set(z.files) == set(arrays))
        for k, x in arrays.items():
            require('own NPZ durable readback ' + path.name + '/' + k,
                    member(z[k]) == member(x))
    return manifest


def screen(rows, takes):
    def invalid(reason):
        return dict(valid=False, passed=False, disposition='INCONCLUSIVE', reason=reason)
    try:
        if len(rows) != 12 or len(takes) != 12:
            return invalid('require all twelve declared takes')
        by = {r['slug']: r for r in rows}
        if len(by) != 12 or set(by) != {t['slug'] for t in takes} or len({t['take'] for t in takes}) != 12:
            return invalid('coverage or group identity differs from declaration')
        if any(sum(t['content'] == g for t in takes) != 6 for g in ('chords', 'scales')):
            return invalid('coverage or group identity differs from declaration')
        ordered = [by[t['slug']] for t in takes]
        for r, t in zip(ordered, takes):
            if identity(r) != identity(t) or r.get('valid', True) is not True or r['qc_valid'] is not True:
                return invalid('invalid identity or raw-DI QC')
            vals = [r[k] for k in ('wet', 'net', 'flatref', 'oracle')]
            if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in vals):
                return invalid('invalid baseline/net loss')
            if min(r['wet'], r['flatref']) <= 0 or r['oracle'] >= 1e-6:
                return invalid('invalid baseline denominator or oracle')
        v = [(min(r['wet'], r['flatref']) - r['net']) / min(r['wet'], r['flatref']) for r in ordered]
        median = statistics.median(v)
        groups = {g: statistics.median(x for r, x in zip(ordered, v) if r['content'] == g)
                  for g in ('chords', 'scales')}
        wins = sum(x > 0 for x in v)
        passed = median >= .1 - 8 * math.ulp(.1) and wins >= 9 and all(x > 0 for x in groups.values())
        return dict(valid=True, passed=passed, disposition='PASS' if passed else 'FAIL',
                    median_relative_improvement=median, strict_wins=wins, group_medians=groups,
                    per_take=[dict(slug=r['slug'], relative_improvement=x) for r, x in zip(ordered, v)])
    except (KeyError, TypeError, ValueError, OverflowError):
        return invalid('missing score or identity fields')


def paired(row, zero):
    changes = {}
    for arm, key in ARMS.items():
        before = zero[key]['primary']
        delta = row[key]['primary'] - before
        changes[arm] = dict(primary_absolute_change=delta,
                            primary_relative_change=delta / before if before > 0 else None,
                            canonical_waveform_l1_change=row[key]['canonical_waveform_l1'] - zero[key]['canonical_waveform_l1'],
                            raw_lowband_change=row[key]['raw_lowband'] - zero[key]['raw_lowband'])
    s, b = min(row['wet'], row['flatref']), min(zero['wet'], zero['flatref'])
    changes['advantage'] = dict(primary_absolute_change=(s-row['net'])-(b-zero['net']),
                                primary_relative_change=(s-row['net'])/s-(b-zero['net'])/b)
    return changes


def structure(a, b, name, category='new', tol=1e-8):
    """Full schema and all leaves; exact booleans/types, finite scalar tolerance."""
    if isinstance(a, dict) and isinstance(b, dict):
        check(name + '/keys', set(a) == set(b), category, expected=sorted(a), observed=sorted(b))
        for k in sorted(set(a) & set(b)):
            structure(a[k], b[k], name + '/' + k, category, tol)
    elif isinstance(a, list) and isinstance(b, list):
        check(name + '/length', len(a) == len(b), category, expected=len(a), observed=len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            structure(x, y, name + '/' + str(i), category, tol)
    elif type(a) in (int, float) and type(b) in (int, float):
        d = abs(a - b)
        check(name, math.isfinite(a) and math.isfinite(b) and d <= tol, category, absolute_difference=d)
    else:
        check(name, type(a) is type(b) and a == b, category, expected=a, observed=b)


def sources(pins, hashes, model, stage):
    require(stage + '/HEAD', subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == REV, 'stability')
    for n, h in pins.items():
        require(stage + '/source/' + n, sha(blob(ROOT/n)) == h, 'stability')
    for n, h in hashes.items():
        require(stage + '/asset/' + n, sha(blob(ROOT/n)) == h, 'stability')
    require(stage + '/checkpoint', sha(blob(Path(model['path']))) == model['sha256'], 'stability')


def scorer(windows):
    import numpy as np
    from scipy import signal
    sos = signal.butter(4, (80, 4000), btype='bandpass', fs=48000, output='sos')
    center = slice(72000, 216000)
    def standard(x):
        return x / (x.std() + 1e-9) * .1
    def spectral(x, y):
        terms = []
        for n, window in windows.items():
            def stft(z):
                padded = np.pad(z, (n//2, n//2), mode='reflect')
                frames = np.lib.stride_tricks.sliding_window_view(padded, n)[::n//4]
                return abs(np.fft.rfft(frames * window, axis=-1)) + 1e-6
            p, q = stft(x), stft(y)
            terms.append(np.linalg.norm(p-q)/(np.linalg.norm(q)+1e-6) + np.mean(abs(np.log(p)-np.log(q))))
        # Accumulate in declared FFT order, matching the scientific definition.
        return float(sum(terms) / len(terms))
    def score(x, target, di):
        x, target, di = [np.asarray(z, dtype=np.float64) for z in (x, target, di)]
        if any(z.shape != (N,) or not np.isfinite(z).all() for z in (x, target, di)):
            raise ValueError('invalid scoring input')
        p, q = standard(x[center]), standard(target[center])
        px = standard(signal.sosfiltfilt(sos, x, padtype='odd', padlen=27)[center])
        dx = standard(signal.sosfiltfilt(sos, di, padtype='odd', padlen=27)[center])
        return dict(primary=spectral(p, q), canonical_waveform_l1=float(np.mean(abs(p-q))), raw_lowband=spectral(px, dx))
    return score


def own_model():
    import torch
    from torch import nn
    class IndependentNet(nn.Module):
        def __init__(self):
            super().__init__()
            widths = (32, 64, 128, 256, 512)
            self.enc = nn.ModuleList()
            self.mid = nn.ModuleList()
            self.dec = nn.ModuleList()
            inp = 1
            for out in widths:
                self.enc.append(nn.Sequential(nn.Conv1d(inp, out, 8, stride=4, padding=2), nn.GELU(),
                                              nn.Conv1d(out, out*2, 1), nn.GLU(dim=1)))
                inp = out
            for dilation in (1, 3, 9, 27):
                self.mid.append(nn.Sequential(nn.Conv1d(512, 512, 3, padding=dilation, dilation=dilation),
                                              nn.GELU(), nn.Conv1d(512, 512, 1)))
            for inp, out in zip(reversed(widths), (256, 128, 64, 32, 1)):
                layers = [nn.Conv1d(inp, inp*2, 3, padding=1), nn.GLU(dim=1),
                          nn.ConvTranspose1d(inp, out, 8, stride=4, padding=2)]
                if out != 1:
                    layers.append(nn.GELU())
                self.dec.append(nn.Sequential(*layers))
        def forward(self, x):
            size = x.shape[-1]
            x = nn.functional.pad(x, (0, (-size) % 1024))
            skips = []
            for block in self.enc:
                x = block(x)
                skips.append(x)
            for block in self.mid:
                x = x + block(x)
            for block, skip in zip(self.dec, reversed(skips)):
                x = block(x + skip[..., :x.shape[-1]])
            return x[..., :size]
    return IndependentNet()


def rebuild(net, raw):
    import numpy as np
    import torch
    # Complete reimplementation of the fixed six-second window/five-second hop.
    raw = np.asarray(raw, dtype='<f4')
    size, window, hop, overlap = len(raw), 288000, 240000, 48000
    output, weight = np.zeros(size, np.float32), np.zeros(size, np.float32)
    fade = np.ones(window, np.float32)
    fade[:overlap] = np.linspace(0, 1, overlap)
    fade[-overlap:] = np.linspace(1, 0, overlap)
    starts = list(range(0, max(1, size-window+1), hop))
    if starts[-1] + window < size:
        starts.append(max(0, size-window))
    with torch.no_grad():
        for start in starts:
            seg = raw[start:start+window].astype(np.float32)
            scale = seg.std() + 1e-9
            tensor = torch.tensor(seg / scale * .1, device='cpu')[None, None]
            pred = net(tensor)[0, 0].cpu().numpy() / .1 * scale
            f = fade[:len(seg)].copy()
            if start == 0:
                f[:overlap] = 1
            if start + window >= size:
                f[-min(overlap, len(seg)):] = 1
            output[start:start+len(seg)] += pred * f
            weight[start:start+len(seg)] += f
    return output / np.maximum(weight, 1e-6)


def relative(actual, expected):
    import numpy as np
    den = float(np.linalg.norm(expected))
    if not math.isfinite(den) or den <= 0:
        raise ValueError('invalid normalization denominator')
    error = float(np.linalg.norm(np.asarray(actual) - expected) / den)
    if not math.isfinite(error):
        raise ValueError('nonfinite relative error')
    return dict(relative_l2=error, denominator=den)


def controls(values, h):
    import numpy as np
    x, y = values['model_converted_input'], values['forward_float64']
    unit = float(np.max(abs(abs(h) - 1)))
    errors = dict(inverse=relative(values['inverse_float64'], x),
                  norm=relative(np.linalg.norm(y), np.linalg.norm(x)),
                  std=relative(np.std(y), np.std(x)),
                  whole_rfft_magnitude=relative(abs(np.fft.rfft(y)), abs(np.fft.rfft(x))),
                  quantized_inverse=relative(values['inverse_quantized_float64'], x))
    passed = bool(np.isfinite(h).all() and h[0] == 1+0j and h[-1] == -1+0j and unit <= 1e-12
                  and all(e['relative_l2'] <= (1e-6 if k == 'quantized_inverse' else 1e-12) for k, e in errors.items()))
    return dict(passed=passed, unit_magnitude_max_deviation=unit, errors=errors)


def metadata():
    prior = read(ROOT/'docs/di-input-shift-control-provenance.json')
    pins = dict(prior['pins'])
    require('exact inherited63 pins', len(pins) == 63, 'inherited')
    for name in EXTRA:
        require('disjoint phase pin ' + name, name not in pins, 'inherited')
        pins[name] = sha(blob(ROOT/name))
    require('exact77 source pins', len(pins) == 77, 'stability')
    for name, h in pins.items():
        committed = subprocess.check_output(['git', 'show', REV+':'+name], cwd=ROOT)
        require('committed source ' + name, sha(committed) == h and blob(ROOT/name) == committed, 'stability')
    import re
    plan = blob(ROOT/'docs/di-phase-control-plan.md').decode()
    approval = json.loads(re.search(r'<!-- phase-approval\n(.*?)\nphase-approval -->', plan, re.S)[1])
    expect = dict(status='DECLARED', fresh_independent_review=True, scope='fixed-periodic-phase-only-a-minus-0.9',
                  source_sha256=pins[EXTRA[0]], test_sha256=pins[EXTRA[1]],
                  design_sha256=sha(plan.split('## Frozen design\n', 1)[1].encode()),
                  review_sha256=pins[EXTRA[3]], inputs_sha256=pins['docs/di-timing-sensitivity-inputs.sha256'])
    structure(expect, approval, 'declaration', 'stability', 0)
    require('review APPROVE', 'Verdict: APPROVE' in blob(ROOT/EXTRA[3]).decode(), 'stability')
    manifest = read(ROOT/'docs/di-domain-pilot-inputs.json')
    takes = [identity(t) for t in manifest['takes']]
    hashes = {}
    for line in blob(ROOT/'docs/di-timing-sensitivity-inputs.sha256').decode().splitlines():
        h, name = line.split('  ')
        require('unique manifest path ' + name, name not in hashes, 'original')
        hashes[name] = h
    expected = {f'tmp/di-morgan-control-20261008/{stage}/{t["slug"]}.npz'
                for stage in ('prepare', 'render', 'infer') for t in takes}
    expected |= {f'tmp/di-morgan-flatref-20261008/{t["slug"]}.npz' for t in takes}
    require('exact original48 names', set(hashes) == expected and len(hashes) == 48, 'original')
    require('only original checkpoint', manifest['model'] == dict(path='/Users/yoavbz/ndsp-presets/learn/direc/models-set3/fold2.pt',
            sha256='16b2b734b49cc1cc2d7e547d96d3bb56208007c9cae0d0e33acb1c2a1cdd042b'), 'original')
    versions = {n: importlib.metadata.version(n) for n in ('numpy', 'scipy', 'torch')}
    require('original environment', sys.prefix == CPU and sys.byteorder == 'little' and versions == prior['packages']
            and prior['prefix'] == CPU and prior['thread_count'] == 2, 'original')
    gz = blob(ROOT/EXTRA[5]); payload = gzip.decompress(gz)
    attestation = read(ROOT/EXTRA[6]); old = json.loads(payload)
    require('prior compact archive identity', sha(gz) == attestation['tracked_gzip_sha256']
            and len(gz) == attestation['tracked_gzip_size'] and sha(payload) == attestation['tracked_uncompressed_sha256']
            and len(payload) == attestation['tracked_uncompressed_size'], 'inherited')
    require('prior VERIFIED PASS all21246 checks', old['status'] == 'VERIFIED' and old['scientific_disposition'] == 'PASS'
            and old['failures'] == [] and len(old['checks']) == 21246 and all(c['passed'] is True for c in old['checks']), 'inherited')
    require('prior archive attestation', attestation['status'] == 'VERIFIED' and attestation['scientific_disposition'] == 'PASS'
            and attestation['final_comparison_checks'] == 21246 and attestation['final_failures'] == 0
            and attestation['payload_references'] == 120 and attestation['lossless_decompression_verified'] is True
            and attestation['original_sha256'] == old['archive_storage_note']['full_report_sha256'], 'inherited')
    require('prior source/artifact/verifier identities', old['source_pins'] == prior['pins'] and old['input_artifacts'] == hashes
            and old['verifier_sha256'] == pins[EXTRA[4]] == attestation['verifier_sha256'], 'inherited')
    reports = {n: read(ROOT/p) for n, p in {'result.json': EXTRA[-1], 'provenance.json': EXTRA[-5],
                'inputs.json': EXTRA[-4], 'baseline-replay.json': EXTRA[-3], 'baseline-inference-replay.json': EXTRA[-2]}.items()}
    require('prior input48/six-member metadata', reports['inputs.json'] == old['inputs'] and reports['inputs.json']['artifacts'] == hashes,
            'inherited')
    result = reports['result.json']; independent = {(r['offset'], r['slug']): r for r in old['independent_rows']}
    require('prior unique60 coverage', len(result['rows']) == len(independent) == 60 and
            {(r['offset'], r['slug']) for r in result['rows']} == {(o,t['slug']) for o in (-3,-2,0,2,3) for t in takes}, 'inherited')
    derived_screens = []
    for offset in (-3,-2,0,2,3):
        rs = [r for r in result['rows'] if r['offset'] == offset]
        own = screen([independent[offset,t['slug']] for t in takes], takes)
        gate = screen(rs, takes)
        require('prior screen ' + str(offset), own['passed'] and gate['passed'], 'inherited')
        # Compare the small scientific screen and 540 arm scalars, never inherited check trees.
        structure(gate, own, 'prior independent gate '+str(offset), 'inherited')
        derived_screens.append(dict(offset=offset, role='prerequisite' if offset == 0 else 'robustness', screen=gate))
        for r in rs:
            q = independent[offset,r['slug']]
            for key in ARMS.values():
                for m in METRICS:
                    structure(r[key][m], q[key][m], 'prior scalar/'+r['slug']+'/'+str(offset)+'/'+key+'/'+m, 'inherited')
    for stored in (result['screen'], old['independent_screen']):
        structure(dict(valid=True, passed=True, disposition='PASS', offset_screens=derived_screens, required_small_offsets=[-3,-2,2,3]),
                  stored, 'prior aggregate screen', 'inherited')
    for name, count in (('baseline-replay.json',108), ('baseline-inference-replay.json',36)):
        r = reports[name]
        require('prior barrier '+name, r['complete'] is True and r['passed'] is True and r['scalar_count'] == count
                and r['absolute_tolerance'] == 1e-8 and [identity(x) for x in r['rows']] == takes
                and r['screen']['passed'] is True and all(x['valid'] is True and len(x['errors']) == count//12
                and all(math.isfinite(v) and 0 <= v <= 1e-8 for v in x['errors'].values()) for x in r['rows']), 'inherited')
    bas = old['independent_baseline_inference_replay']
    require('prior independent original12/36', bas['complete'] and bas['passed'] and bas['scalar_count'] == 36
            and [identity(x) for x in bas['rows']] == takes, 'inherited')
    for p, q in zip(reports['baseline-inference-replay.json']['rows'], bas['rows']):
        zero = next(r for r in result['rows'] if r['offset'] == 0 and r['slug'] == p['slug'])
        require('prior original exact bytes '+p['slug'], p['byte_identical'] and q['byte_identical'] and
                q['raw_prediction_sha256'] == p['raw_prediction_sha256'] == p['original_prediction_sha256_float32']
                == zero['raw_prediction_sha256'] == zero['corrected_prediction_sha256'], 'inherited')
    refs = old['independent_prediction_archives']; byfile = {r['prediction_file']:r for r in result['rows']}
    bc = old['prediction_byte_checks']
    require('prior120 exact member coverage', len(bc) == 120 and set(refs) == set(byfile) and
            {(c['file'],c['member']) for c in bc} == {(f,m) for f in refs for m in ('raw','corrected')}, 'inherited')
    for c in bc:
        r, ref = byfile[c['file']], refs[c['file']]
        h = r[c['member']+'_prediction_sha256']; pointer = ref['npz_base64']
        require('prior byte reference '+c['file']+'/'+c['member'], c['byte_identical'] is True and
                c['independent_sha256'] == c['primary_sha256'] == h and c['dtype'] == '<f4' and c['samples'] == N
                and ref[c['member']+'_identity'] == dict(dtype='float32',samples=N,sha256=h)
                and isinstance(pointer,dict) and pointer['storage'] == 'full local JSON at original JSON pointer'
                and pointer['json_pointer'] == '/independent_prediction_archives/'+c['file']+'/npz_base64'
                and pointer['decoded_npz_sha256'] == ref['npz_sha256'] == r['prediction_file_sha256'], 'inherited')
    names = {f'tmp/di-input-shift-control-20261008/{n}' for n in reports}
    names |= {'tmp/di-input-shift-control-20261008/progress.jsonl','tmp/di-input-shift-control-20261008.log'}
    snapshots = old['primary_artifact_snapshots']
    require('prior67 snapshot name identities', len(snapshots) == 67 and set(snapshots) == names | {
            'tmp/di-input-shift-control-20261008/'+f for f in refs}, 'inherited')
    for f, r in byfile.items():
        require('prior snapshot array identity '+f, snapshots['tmp/di-input-shift-control-20261008/'+f]['sha256'] == r['prediction_file_sha256'], 'inherited')
    for name in names:
        data = blob(ROOT/name)
        require('prior7 metadata snapshot '+name, sha(data) == snapshots[name]['sha256'] and len(data) == snapshots[name]['size'], 'inherited')
        base = Path(name).name
        if base in reports:
            expected_path = {'result.json':EXTRA[-1], 'provenance.json':EXTRA[-5], 'inputs.json':EXTRA[-4],
                             'baseline-replay.json':EXTRA[-3], 'baseline-inference-replay.json':EXTRA[-2]}[base]
            require('prior original/archive bytes '+base, data == blob(ROOT/expected_path), 'inherited')
    original = read(ROOT/'docs/di-morgan-flatref.json')
    prep = read(ROOT/'docs/di-morgan-control-prepare.json')
    control = read(ROOT/'docs/di-morgan-control-verification.json')
    require('inherited original QC/oracles', prep['complete'] and prep['valid'] and [identity(r) for r in prep['rows']] == takes
            and [identity(r) for r in control['preparation']] == takes and
            all(r['qc_valid'] is True and r['qc']['valid'] is True and 0 <= r['oracle_scores']['primary'] < 1e-6 for r in prep['rows']), 'inherited')
    for p,q,r in zip(prep['rows'],control['preparation'],original['rows']):
        structure(p['qc'],q['qc'],'inherited QC/'+p['slug'],'inherited')
        structure(p['oracle_scores'],q['oracle_scores'],'inherited oracle/'+p['slug'],'inherited')
        structure(p['oracle_scores']['primary'],r['oracle'],'inherited original oracle/'+p['slug'],'inherited')
    return pins, hashes, manifest, takes, versions, reports['inputs.json'], original


def derive():
    OWN.mkdir(exist_ok=False)
    tick('independent derivation started; primary unread')
    pins, hashes, manifest, takes, versions, prior_inputs, original = metadata()
    sources(pins, hashes, manifest['model'], 'before_original_load')
    import numpy as np
    correction = read(ROOT/'docs/di-domain-pilot-v2-inputs.json')
    winzip = blob(ROOT/'docs/di-domain-metric-probe-windows.json.gz')
    winraw = gzip.decompress(winzip)
    require('window compressed/raw identity', sha(winzip) == correction['windows_sha256'] and sha(winraw) == correction['windows_raw_sha256'], 'original')
    table = json.loads(winraw); windows = {}
    require('window exact five sizes', set(table) == {str(n) for n in (256,512,1024,2048,4096)}, 'original')
    for n in (256,512,1024,2048,4096):
        row = table[str(n)]['torch32']; raw = np.array(row['bits'],dtype='<u4').tobytes()
        require('window bits '+str(n), row['dtype'] == '<f4' and len(row['bits']) == n and sha(raw) == row['sha256'], 'original')
        windows[n] = np.frombuffer(raw,dtype='<f4').astype(np.float64)
    loaded, identities = {}, {}
    for t in takes:
        s = t['slug']; values = {}
        pairs = ((f'tmp/di-morgan-control-20261008/prepare/{s}.npz',{'di':'di','target':'target'}),
                 (f'tmp/di-morgan-control-20261008/render/{s}.npz',{'baseline':'wet','net_input':'net_input'}),
                 (f'tmp/di-morgan-control-20261008/infer/{s}.npz',{'prediction':'net'}),
                 (f'tmp/di-morgan-flatref-20261008/{s}.npz',{'flatref':'flatref'}))
        for path, members in pairs:
            with np.load(regular(ROOT/path), allow_pickle=False) as z:
                for m,key in members.items():
                    x = z[m]
                    require('original active finite waveform '+s+'/'+key, x.shape == (N,) and x.dtype.kind == 'f'
                            and np.isfinite(x).all() and float(np.std(x)) > 0, 'original')
                    values[key] = x
        require('original52 exact overlap '+s, values['net_input'].dtype == values['wet'].dtype and
                values['net_input'][52:].tobytes() == values['wet'][:-52].tobytes(), 'original')
        require('original prediction/flatref dtype '+s, values['net'].dtype == np.dtype('<f4') and values['flatref'].dtype == np.dtype('<f8'), 'original')
        loaded[s] = values; identities[s] = {k:wave_identity(x) for k,x in values.items()}
    inputs = dict(artifacts=hashes, waveforms=identities)
    structure(prior_inputs, inputs, 'original six-member identities', 'original', 0)
    sources(pins, hashes, manifest['model'], 'after_original_load')
    score = scorer(windows)
    archived = {r['slug']:r for r in original['rows']}
    zero, baseline_errors = [], []
    for t in takes:
        s = t['slug']; v = loaded[s]; old = archived[s]
        row = dict(**t, offset=0, qc_valid=old['qc_valid'], oracle=old['oracle'])
        errors = {}
        for arm,key in ARMS.items():
            row[key] = score(v[arm],v['target'],v['di']); row[arm] = row[key]['primary']
            for m in METRICS:
                d = abs(row[key][m]-old[key][m]); errors[arm+'.'+m] = d
                require('original scalar '+s+'/'+arm+'/'+m, d <= 1e-8, 'original', absolute_difference=d)
        baseline_errors.append(dict(**t, valid=True, scores={key:row[key] for key in ARMS.values()}, errors=errors,
                                    nonfinite_diagnostic_fields=[]))
        zero.append(row); tick('original scalar replay '+s)
    gate = screen(zero,takes)
    structure(original['screen'],gate,'original F gate','original')
    require('original scalar replay gate PASS', gate['passed'], 'original')
    baseline = dict(complete=True,passed=True,scalar_count=108,absolute_tolerance=1e-8,rows=baseline_errors,screen=gate)
    persist(OWN/'original-scalar-replay.json',baseline)
    require('original scalar barrier readback',read(OWN/'original-scalar-replay.json') == baseline,'original')
    sources(pins, hashes, manifest['model'], 'before_model_load')
    import torch
    torch.set_num_threads(2)
    net = own_model().cpu()
    net.load_state_dict(torch.load(manifest['model']['path'], map_location='cpu',weights_only=True))
    net.eval()
    require('CPU eval exactly two threads', torch.get_num_threads() == 2 and not net.training and all(p.device.type == 'cpu' for p in net.parameters()),'original')
    replay = []; original_archives = {}
    for t,row in zip(takes,zero):
        s=t['slug']; v=loaded[s]; pred=rebuild(net,v['net_input'])
        evidence = archive(OWN/(s+'.offset-+0.npz'),dict(raw_prediction=pred,offset=np.int64(0),corrected_prediction=pred.copy()))
        require('original prediction exact bytes '+s, member(pred) == member(v['net']), 'original')
        scores=score(pred,v['target'],v['di'])
        errors={m:abs(scores[m]-archived[s]['network_scores'][m]) for m in METRICS}
        for m,d in errors.items():
            require('direct original network score '+s+'/'+m,d <= 1e-8,'original',absolute_difference=d)
        row['network_scores']=scores; row['net']=scores['primary']; row['valid']=True
        replay.append(dict(**t,offset=0,valid=True,attempted_file=evidence['file'],returned=True,archive=evidence,
                           prediction_file=evidence['file'],prediction_file_sha256=evidence['sha256'],
                           raw_prediction_sha256=sha(pred.tobytes()),corrected_prediction_sha256=sha(pred.tobytes()),
                           original_prediction_sha256_float32=sha(v['net'].tobytes()),byte_identical=True,
                           scores=scores,errors=errors,nonfinite_diagnostic_fields=[]))
        original_archives[s]=evidence; tick('original model prediction '+s)
    baseline_inference=dict(complete=True,passed=True,scalar_count=36,absolute_tolerance=1e-8,rows=replay,screen=screen(zero,takes))
    persist(OWN/'original-inference-replay.json',baseline_inference)
    require('original inference barrier readback',read(OWN/'original-inference-replay.json') == baseline_inference,'original')
    sources(pins,hashes,manifest['model'],'before_phase_construction')
    z=np.exp(-2j*np.pi*np.arange(N//2+1,dtype=np.float64)/N)
    h=(A+z)/(1+A*z); h[0]=1+0j; h[-1]=-1+0j
    coeff=archive(OWN/'coefficients.npz',dict(h=h))
    def transform(x):
        return np.fft.irfft(np.fft.rfft(np.asarray(x,dtype=np.float64))*h,n=N)
    def inverse(x):
        return np.fft.irfft(np.fft.rfft(np.asarray(x,dtype=np.float64))*np.conj(h),n=N)
    prepared={}; control_rows=[]
    for t in takes:
        s=t['slug']; v=loaded[s]; x=np.asarray(v['net_input'],dtype='<f4').astype(np.float64)
        y=transform(x); q=y.astype('<f4')
        arrays=dict(model_converted_input=x,forward_float64=y,phase_input=q,inverse_float64=inverse(y),
                    inverse_quantized_float64=inverse(q),phase_wet=transform(v['wet']),phase_flatref=transform(v['flatref']))
        art=archive(OWN/(s+'.controls.npz'),arrays); measures=controls(arrays,h)
        require('phase construction controls '+s,measures['passed'], 'new')
        prepared[s]=arrays
        control_rows.append(dict(**t,attempted_file=art['file'],archive=art,**measures,nonfinite_diagnostic_fields=[]))
        tick('independent FFT inverse controls '+s)
    config=dict(CONFIG,coefficients=wave_identity(h))
    construction=dict(complete=True,passed=True,config=config,coefficients_archive=coeff,
                      coefficients_attempt=dict(attempted_file='coefficients.npz',constructed=True,members=coeff['members'],archive=coeff),rows=control_rows)
    persist(OWN/'construction-controls.json',construction)
    require('construction barrier readback',read(OWN/'construction-controls.json') == construction)
    sources(pins,hashes,manifest['model'],'before_phase_inference')
    predictions={}; prediction_evidence=[]
    for t in takes:
        s=t['slug']; arrays={k:prepared[s][k] for k in ('phase_input','phase_wet','phase_flatref')}
        pred=rebuild(net,arrays['phase_input']); arrays['raw_prediction']=pred; predictions[s]=pred
        art=archive(OWN/(s+'.phase.npz'),arrays)
        prediction_evidence.append(dict(**t,returned=True,attempted_file=art['file'],archive=art))
        tick('phase model return retained '+s)
    rows=[]
    for t,base,evidence in zip(takes,zero,prediction_evidence):
        s=t['slug']; v=loaded[s]; pred=predictions[s]
        require('phase raw return validity '+s,pred.dtype == np.dtype('<f4') and pred.shape == (N,) and np.isfinite(pred).all())
        row=dict(**t,valid=True,prediction_evidence=evidence,qc_valid=base['qc_valid'],oracle=base['oracle'])
        for arm,key in ARMS.items():
            wave=pred if arm == 'net' else prepared[s]['phase_'+arm]
            row[key]=score(wave,v['target'],v['di']); row[arm]=row[key]['primary']
            require('phase metric validity '+s+'/'+arm,set(row[key]) == set(METRICS) and all(math.isfinite(a) and a >= 0 for a in row[key].values()))
        row['changes_from_zero']=paired(row,base); row['nonfinite_diagnostic_fields']=[]; rows.append(row)
        tick('phase scores and paired changes '+s)
    phase_gate=screen(rows,takes)
    require('phase gate valid',phase_gate['valid'])
    # Explicit invalid-priority controls on the independently derived panel.
    require('missing coverage yields INCONCLUSIVE',screen(rows[:-1],takes)['disposition'] == 'INCONCLUSIVE')
    bad=[dict(r) for r in rows]; bad[-1]['valid']=False
    require('invalid last case yields INCONCLUSIVE',screen(bad,takes)['disposition'] == 'INCONCLUSIVE')
    sources(pins,hashes,manifest['model'],'after_independent_scoring')
    tick('complete independent derivation BEFORE any primary phase reads')
    result=dict(complete=True,rows=rows,prediction_evidence=prediction_evidence,config=CONFIG,screen=phase_gate,
                baseline_reused_no_new_score=zero,source_pins=pins,input_artifacts=hashes,inputs=inputs,
                model=manifest['model'],takes=takes,packages=versions,prefix=sys.prefix,thread_count=2,
                baseline_replay=baseline,baseline_inference_replay=baseline_inference,construction_controls=construction,
                verifier_sha256_at_derivation=sha(blob(SELF)),elapsed_seconds=time.monotonic()-START,
                primary_read_before_derivation=False,checks=CHECKS)
    digest=persist(OWN/'independent-derivation.json',result)
    require('full independent derivation durable readback',read(OWN/'independent-derivation.json') == result)
    # Reopen every own waveform file and compare each member manifest once more.
    arts=[coeff]+[r['archive'] for r in replay]+[r['archive'] for r in control_rows]+[r['archive'] for r in prediction_evidence]
    for art in arts:
        require('full readback archive '+art['file'],sha(blob(OWN/art['file'])) == art['sha256'])
        with np.load(OWN/art['file'],allow_pickle=False) as saved:
            require('full readback members '+art['file'],{k:member(saved[k]) for k in saved.files} == art['members'])
    persist(OWN/'read-barrier.json',dict(complete=True,derivation_file='independent-derivation.json',derivation_sha256=digest,
            readback_passed=True,archives_readback=len(arts),unix=time.time(),elapsed_seconds=time.monotonic()-START,
            primary_artifacts_read=[],verifier_sha256=sha(blob(SELF)),checks_after_derivation=CHECKS[len(result['checks']):]))
    tick('DURABLE READ BARRIER CLOSED; comparison now permitted')


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('mode',choices=['derive','compare']); args=parser.parse_args()
    try:
        if args.mode == 'derive':
            derive()
        else:
            compare()
    except Exception as error:
        if OWN.exists():
            stamp=str(time.time_ns())
            persist(OWN/('failure-'+stamp+'.json'),dict(mode=args.mode,error_type=type(error).__name__,message=str(error),
                    traceback=traceback.format_exc(),checks=CHECKS,elapsed_seconds=time.monotonic()-START))
        raise


if __name__ == '__main__':
    main()
