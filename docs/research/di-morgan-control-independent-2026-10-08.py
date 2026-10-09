"""Independent verification. Writes only its JSON/Markdown reports; no subprocesses.

Call explicitly with the existing CPU Torch interpreter. Primary inference files
are opened only AFTER all 12 replay predictions and independent metrics are saved.
Only direc.build_model/rebuild are shared. C/P/R/V numerical code is never imported.
"""
from __future__ import annotations

import ast
import gzip
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time
import traceback

import numpy as np
from scipy.signal import butter, sosfiltfilt
import soundfile as sf

ROOT = Path('/Users/yoavbz/projects/neuraldsp-preset-generator')
RUN = ROOT / 'tmp/di-morgan-control-20261008'
OUT = ROOT / 'tmp/di-morgan-control-verification.json'
MD = ROOT / 'tmp/di-morgan-control-verification.md'
CPU = Path('/Users/yoavbz/ndsp-presets/tools/learn-venv')
HEAD = 'a5b96052bb16d6a3695b4040a9b3923ba90de645'
SR, TOTAL, GUARD, SIX = 48000, 480000, 512, 288000
FFTS = (256, 512, 1024, 2048, 4096)
CENTER = slice(72000, 216000)
SCORE_TOL = 1e-8
ARRAY_TOL = 1e-10
ATTRIBUTION = 'Pedroza et al., Guitar-TECHS, CC BY 4.0, https://zenodo.org/records/14963133'
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
learn/di_morgan_control.py tests/test_di_morgan_control.py scripts/_swift.py'''.split()
report = {'status': 'RUNNING', 'attribution': ATTRIBUTION, 'pinned_revision': HEAD,
          'primary_scores_unread': True, 'checks': [], 'failures': [], 'preparation': [],
          'replay': [], 'limitations': [
              'Full wet renders were retained only for the first take/canary. For the other 11, full-render hashes/peaks and wet pre-roll cannot be independently reconstructed; six-second input/baseline overlap and all original-level host inputs are verified.',
              'Saved host log has no parameter command transcript. Fixed PR12+R and warm-up/close sequence are supported by pinned code; actual plugin state is not separately recorded.',
              'The fixed 52-sample slicing is checked exactly from saved waves. This does not remeasure physical plugin latency or fit a delay.'
          ]}
started = time.monotonic()


def readj(path):
    return json.loads(Path(path).read_text())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def filehash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(1048576), b''):
            h.update(data)
    return h.hexdigest()


def signalhash(x):
    return digest(np.asarray(x, dtype='<f8').tobytes())


def check(name, condition, detail=None):
    result = {'name': name, 'passed': bool(condition)}
    if detail is not None:
        result['detail'] = detail
    report['checks'].append(result)
    if not condition:
        report['failures'].append(result)
    return bool(condition)


def require(name, condition, detail=None):
    if not check(name, condition, detail):
        raise ValueError(name)


def scalar(name, a, b, tol=SCORE_TOL):
    ok = (type(a) in (int, float) and type(b) in (int, float)
          and math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tol)
    check(name, ok, {'independent': a, 'recorded': b, 'absolute_tolerance': tol})


def array(name, a, b, tol=0):
    ok = a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
    delta = float(np.max(np.abs(a.astype(np.float64)-b.astype(np.float64)))) if ok else None
    check(name, ok and delta <= tol, {'shape': list(a.shape), 'other_shape': list(b.shape),
                                    'max_absolute_error': delta, 'absolute_tolerance': tol,
                                    'byte_identical': a.dtype == b.dtype and a.tobytes() == b.tobytes()})


def save():
    report['elapsed_seconds'] = time.monotonic()-started
    report['verifier_sha256'] = filehash(Path(__file__))
    OUT.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    lines = ['# Independent known-DI Morgan control verification', '',
             '**Status: '+report['status']+'**', '', ATTRIBUTION, '',
             'Frozen revision: `'+HEAD+'`. Primary scores unread: '+str(report['primary_scores_unread'])+'.', '',
             'Independent NumPy five-FFT metric, target, raw QC, repeatability canary and gate. Only frozen `direc.build_model/rebuild` are shared.', '',
             'Checks: '+str(len(report['checks']))+'; failures: '+str(len(report['failures']))+'.',
             'Raw preparation rows: '+str(len(report['preparation']))+'; replay rows: '+str(len(report['replay']))+'.', '']
    if report.get('independent_screen'):
        s = report['independent_screen']
        lines += ['Standalone scientific positive control: **'+s['disposition']+'**.', '',
                  'Median improvement: '+format(s['median_relative_improvement'], '.8%')+
                  '; strict wins: '+str(s['strict_wins'])+'/12 (diagnostic).', '',
                  'Group medians (diagnostics): '+str(s['group_medians'])+'.', '',
                  '| Take | Wet primary | Net primary | Improvement |', '|---|---:|---:|---:|']
        for r in report['replay']:
            lines.append('| '+r['slug']+' | '+format(r['input_scores']['primary'], '.10g')+' | '+
                         format(r['network_scores']['primary'], '.10g')+' | '+format(r['relative_improvement'], '.4%')+' |')
        lines.append('')
    if report['failures']:
        lines += ['## Failures', '']+[ '- '+str(f) for f in report['failures']]+['']
    lines += ['## Evidence limits', '']+['- '+x for x in report['limitations']]+['',
        'One player/guitar and one fixed clean Morgan chain. No native-transfer or product claim. Win count and group medians do not add gates.', '']
    MD.write_text('\n'.join(lines))


def metric(a, b, windows):
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    if a.shape != b.shape or a.ndim != 1 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('invalid metric input')
    terms = []
    for n in FFTS:
        magnitudes = []
        for x in (a, b):
            padded = np.pad(x, (n//2, n//2), mode='reflect')
            frames = np.lib.stride_tricks.sliding_window_view(padded, n)[::n//4]
            magnitudes.append(np.abs(np.fft.rfft(frames*windows[n], axis=1))+1e-6)
        A, B = magnitudes
        terms.append(float(np.linalg.norm(A-B)/(np.linalg.norm(B)+1e-6)
                           + np.abs(np.log(A)-np.log(B)).mean()))
    return float(sum(terms)/5)


def normalize(x):
    x = np.asarray(x, np.float64)
    return x/(np.std(x)+1e-9)*0.1


def score(p, target, raw, windows):
    if any(x.shape != (SIX,) or not np.isfinite(x).all() for x in (p, target, raw)):
        raise ValueError('score waveform invalid')
    a, b = normalize(p[CENTER]), normalize(target[CENTER])
    sos = butter(4, (80, 4000), btype='bandpass', fs=SR, output='sos')
    low = [normalize(sosfiltfilt(sos, np.asarray(x, np.float64), padtype='odd', padlen=27)[CENTER]) for x in (p, raw)]
    return {'primary': metric(a, b, windows), 'canonical_waveform_l1': float(np.abs(a-b).mean()),
            'raw_lowband': metric(*low, windows)}


def target_from_raw(x, average):
    frames = np.lib.stride_tricks.sliding_window_view(x, 4096)[::1024]
    power = np.abs(np.fft.rfft(frames*np.hanning(4096), axis=1))**2
    energy = power.sum(axis=1)
    keep = 10*np.log10(energy+1e-20) >= 10*np.log10(energy.max()+1e-20)-40
    p = power[keep].mean(axis=0)
    f = np.fft.rfftfreq(4096, 1/SR)
    smoothed = np.empty(2049, np.float64)
    for i, fc in enumerate(f):
        mask = (f >= fc*2**(-1/12)) & (f <= fc*2**(1/12))
        smoothed[i] = p[mask].mean() if mask.any() else p[i]
    db = 10*np.log10(smoothed+1e-20)
    gain = np.clip(average-(db-db.mean()), -15, 15)
    curve = np.interp(np.fft.rfftfreq(SIX, 1/SR), f, gain)
    return np.fft.irfft(np.fft.rfft(x)*10**(curve/20), n=SIX)


def qc(x):
    valid = x.shape == (TOTAL,) and np.isfinite(x).all()
    metrics, reasons = {}, []
    if not valid:
        return {'valid': False, 'metrics': metrics, 'reasons': ['invalid length or finite status']}
    for label, part in [('calibration', x[:192000]), ('score', x[192000:])]:
        rms = float(np.sqrt(np.mean(part**2)))
        clipped = float(np.mean(np.abs(part) >= .999))
        frame_rms = np.sqrt(np.mean(part.reshape(-1, 480)**2, axis=1))
        active = float(np.mean(frame_rms > frame_rms.max()*.01))
        metrics[label] = {'rms': rms, 'clipped_fraction': clipped, 'active_fraction': active}
        if rms < 1e-5: reasons.append(label+': RMS below 1e-5')
        if clipped > 1e-4: reasons.append(label+': clipping')
        if active < .8: reasons.append(label+': active fraction below 0.8')
    return {'valid': not reasons, 'metrics': metrics, 'reasons': reasons}


def gate(rows, takes):
    expected = {t['slug']: (t['content'], t['take']) for t in takes}
    actual = {r['slug']: r for r in rows}
    valid = (len(rows) == len(takes) == len(expected) == len(actual) == 12
             and set(expected) == set(actual) and len({t['take'] for t in takes}) == 12
             and all(sum(t['content'] == g for t in takes) == 6 for g in ('chords', 'scales')))
    for slug, identity in expected.items():
        r = actual.get(slug, {})
        valid = valid and (r.get('content'), r.get('take')) == identity and r.get('qc_valid') is True
        for key in ('morgan_input', 'morgan_net', 'oracle'):
            v = r.get(key)
            valid = valid and type(v) in (int, float) and math.isfinite(v) and v >= 0
        valid = valid and r.get('morgan_input', 0) > 0 and r.get('oracle', 1) < 1e-6
    if not valid:
        return {'valid': False, 'passed': False, 'disposition': 'INCONCLUSIVE'}
    ordered = [actual[t['slug']] for t in takes]
    improvements = [(r['morgan_input']-r['morgan_net'])/r['morgan_input'] for r in ordered]
    median = statistics.median(improvements)
    passed = median >= .1-8*math.ulp(.1)
    return {'valid': True, 'passed': passed, 'disposition': 'PASS' if passed else 'FAIL',
            'median_relative_improvement': median, 'strict_wins': sum(v > 0 for v in improvements),
            'group_medians': {g: statistics.median(v for r, v in zip(ordered, improvements) if r['content'] == g)
                              for g in ('chords', 'scales')},
            'per_take': [{'slug': r['slug'], 'relative_improvement': v} for r, v in zip(ordered, improvements)]}


def coverage(name, rows, takes, identities=True):
    check(name, len(rows) == 12 and [r['slug'] for r in rows] == [t['slug'] for t in takes])
    if identities:
        check(name+' identities', [(r['content'], r['take']) for r in rows] == [(t['content'], t['take']) for t in takes])


def verify():
    require('explicit CPU Torch environment', Path(sys.prefix).resolve() == CPU.resolve())
    report['runtime'] = {'python': sys.version, 'prefix': sys.prefix,
                         'packages': {k: importlib.metadata.version(k) for k in ('numpy', 'scipy', 'soundfile', 'torch')}}
    pins = {name: filehash(ROOT/name) for name in PIN_NAMES}
    report['source_pins'] = pins
    require('original manifest fixed hash', pins['docs/di-domain-pilot-inputs.json'] == '3220d15a5dfbfb40ee39462377e88104cc8c3a6f6cfcabb4aa2f7d80613e8930')
    require('control plan fixed hash', pins['docs/di-morgan-control-plan.md'] == 'b07d77d97958866fa8d3b68e5d78e564ba8985c4f808a48b02b5ac3499003ff2')
    manifest = readj(ROOT/'docs/di-domain-pilot-inputs.json')
    takes = manifest['takes']
    require('manifest twelve unique six/six', len(takes) == 12 and len({t['slug'] for t in takes}) == 12
            and len({t['take'] for t in takes}) == 12 and all(sum(t['content'] == g for t in takes) == 6 for g in ('chords', 'scales')))
    require('manifest ordering', takes == sorted(takes[:6], key=lambda t: (t['take'], t['start_frame']))+sorted(takes[6:], key=lambda t: (t['take'], t['start_frame'])))
    check('attribution', manifest['attribution'] == ATTRIBUTION)
    expected_versions = {'metric': {'numpy': '2.0.2', 'scipy': '1.13.1', 'soundfile': '0.13.1', 'torch': '2.8.0'},
                         'numpy': {'numpy': '2.5.1', 'scipy': '1.18.0', 'soundfile': '0.14.0', 'torch': None}}
    provenance = {}
    for stage in ('metric', 'numpy', 'prepare', 'render', 'infer'):
        # Infer provenance contains no scores, predictions, or outcome.
        prov = readj(RUN/stage/'provenance.json')
        provenance[stage] = prov
        require(stage+' exact complete source pins', prov['pins'] == pins)
        expected = expected_versions['metric' if stage in ('metric', 'infer') else 'numpy']
        check(stage+' recorded versions', prov['packages'] == expected, prov['packages'])
        check(stage+' explicit environment', prov['prefix'] == str(CPU if stage in ('metric', 'infer') else ROOT/'.venv'))
        check(stage+' failure artifact absent', not (RUN/stage/'failure.json').exists())
        check(stage+' attribution', prov['attribution'] == ATTRIBUTION)
    report['stage_provenance'] = provenance
    check('live CPU package versions', report['runtime']['packages'] == expected_versions['metric'])
    correction = readj(ROOT/'docs/di-domain-pilot-v2-inputs.json')
    require('correction definition', correction == {'schema': 2, 'original_inputs': 'docs/di-domain-pilot-inputs.json',
        'original_inputs_sha256': pins['docs/di-domain-pilot-inputs.json'],
        'windows': 'docs/di-domain-metric-probe-windows.json.gz', 'windows_sha256': pins['docs/di-domain-metric-probe-windows.json.gz'],
        'windows_raw_sha256': '374cacf4a401139e681fc9c43088ff58d2c9e9c47748d73785b61fb9b7e915fc',
        'window_family': 'torch32', 'window_dtype': '<f4', 'tolerance': 1e-8})
    raw = gzip.decompress((ROOT/correction['windows']).read_bytes())
    require('decompressed window hash', digest(raw) == correction['windows_raw_sha256'])
    table = json.loads(raw)
    require('all five coefficient definitions', set(table) == {str(n) for n in FFTS})
    import torch
    torch.set_num_threads(2)
    require('live frozen default dtype', torch.get_default_dtype() == torch.float32)
    windows = {}
    for n in FFTS:
        item = table[str(n)]['torch32']
        require(str(n)+' exact bits definition', item['dtype'] == '<f4' and len(item['bits']) == n
                and all(type(v) is int and 0 <= v < 2**32 for v in item['bits']))
        blob = np.asarray(item['bits'], dtype='<u4').tobytes()
        require(str(n)+' coefficient hash', digest(blob) == item['sha256'])
        w = np.frombuffer(blob, dtype='<f4')
        require(str(n)+' live Torch coefficient bytes', torch.hann_window(n, device='cpu').numpy().tobytes() == blob)
        windows[n] = w.astype(np.float64)
    reference = readj(RUN/'metric/result.json')
    replay = readj(RUN/'numpy/result.json')
    require('synthetic metric and helper gates', reference['passed'] is True and replay['passed'] is True
            and reference['tolerance'] == replay['tolerance'] == 1e-8)
    check('helper synthetic reference file hash', replay['metric_result_sha256'] == filehash(RUN/'metric/result.json'))
    require('synthetic coverage', [r['case'] for r in reference['rows']] == [r['case'] for r in replay['rows']] == list(range(4)))
    check('synthetic reported runtime/dtype', reference['torch_version'] == torch.__version__
          and reference['numpy_version'] == np.__version__ and reference['default_dtype'] == 'torch.float32'
          and replay['numpy_version'] == expected_versions['numpy']['numpy'])
    b = np.random.default_rng(20261008).normal(size=144000)*.1
    synthetic = []
    for i, a in enumerate((b.copy(), b*.5, np.roll(b, 52), np.zeros_like(b))):
        prior, helper = reference['rows'][i], replay['rows'][i]
        require('synthetic '+str(i)+' byte hashes', signalhash(a) == prior['prediction_sha256'] and signalhash(b) == prior['target_sha256'])
        own = metric(a, b, windows)
        # Independent Torch expression, never D.mrstft or P/V numerical code.
        value = torch.tensor(0., dtype=torch.float64)
        for n in FFTS:
            w = torch.hann_window(n, device='cpu')
            spectra = [torch.stft(torch.from_numpy(x)[None], n_fft=n, hop_length=n//4, window=w,
                                  center=True, pad_mode='reflect', normalized=False, onesided=True, return_complex=True).abs()+1e-6 for x in (a, b)]
            A, B = spectra
            value += torch.linalg.vector_norm(A-B)/(torch.linalg.vector_norm(B)+1e-6)+torch.abs(torch.log(A)-torch.log(B)).mean()
        live = float(value/5)
        scalar('synthetic '+str(i)+' independent NumPy vs live Torch', own, live)
        for label, other in [('metric NumPy', prior['numpy']), ('metric Torch', prior['torch']), ('helper NumPy', helper['numpy']), ('helper Torch', helper['torch'])]:
            scalar('synthetic '+str(i)+' '+label, own, other)
        scalar('synthetic '+str(i)+' metric error field', abs(prior['numpy']-prior['torch']), prior['absolute_error'], 0)
        scalar('synthetic '+str(i)+' helper error field', abs(helper['numpy']-helper['torch']), helper['absolute_error'], 0)
        synthetic.append({'case': i, 'independent_numpy': own, 'independent_torch': live})
    require('independent identity oracle synthetic', synthetic[0]['independent_numpy'] < 1e-6)
    report['synthetic'] = synthetic
    # All external model/average reads are confined to these declared paths.
    allowed_assets = {'model': ('/Users/yoavbz/ndsp-presets/learn/direc/models-set3/fold2.pt', '16b2b734b49cc1cc2d7e547d96d3bb56208007c9cae0d0e33acb1c2a1cdd042b'),
                      'average': ('/Users/yoavbz/ndsp-presets/learn/direc/cache/average-fold2.npy', '9aa3c3bfefc2bc5ba21394be29876b5ef5e0120ad2f55f0b890e599ec3bee9a8')}
    assets = readj(RUN/'prepare/assets.json')
    for key, (path, sha) in allowed_assets.items():
        require(key+' exact declared path/hash', manifest[key] == {'path': path, 'sha256': sha})
        require(key+' observed hash', filehash(path) == sha)
        require(key+' saved asset provenance', assets[key] == manifest[key])
    check('asset revision', assets['git_revision'] == HEAD)
    check('catalog historical hash recorded, catalog not reopened', assets.get('catalog') == '03caee40f885b2139fc92eb337690454fbd1c825f69bc6a4bbbb2c4dcb626d64')
    for name in PIN_NAMES[:24]:
        check('asset source '+name, assets[name] == pins[name])
    for stage in ('render', 'infer'):
        check(stage+' identical asset provenance', readj(RUN/stage/'assets.json') == assets)
    report['assets'] = {k: manifest[k] for k in allowed_assets}
    average = np.load(allowed_assets['average'][0], allow_pickle=False)
    require('average shape and finiteness', average.shape == (2049,) and np.isfinite(average).all())
    prep = readj(RUN/'prepare/result.json')
    renders = readj(RUN/'render/result.json')
    require('prepare completion', prep['complete'] is True and prep['valid'] is True)
    require('render completion before saved wave reads', renders['complete'] is True)
    coverage('prepare report coverage', prep['rows'], takes)
    coverage('render report coverage', renders['rows'], takes, False)
    for stage, data in [('prepare', prep), ('render', renders)]:
        progress = [json.loads(line) for line in (RUN/stage/'progress.jsonl').read_text().splitlines()]
        check(stage+' progress equals result rows', progress == data['rows'])
        check(stage+' attribution', data['attribution'] == ATTRIBUTION)
        check(stage+' declared cooperative budget', 0 <= data['elapsed_seconds'] <= 900)
        check(stage+' exact saved NPZ coverage', {p.stem for p in (RUN/stage).glob('*.npz') if p.name != 'repeatability-audio.npz'} == {t['slug'] for t in takes})
    root = Path('/Users/yoavbz/ndsp-presets/references/datasets/guitar-techs/P2-downloads')
    require('DI source root', manifest['source_root'] == str(root))
    prepared, host_names = {}, set()
    for take, prior in zip(takes, prep['rows']):
        slug = take['slug']
        expected = f"P2_{take['content']}/audio/directinput/directinput_{take['take']}.wav"
        require(slug+' explicit DI-only source', take['di'] == expected and Path(expected).parts[0] in ('P2_chords', 'P2_scales'))
        path = root/expected
        require(slug+' DI containment/no link', path.resolve() == path and path.is_relative_to(root) if hasattr(path, 'is_relative_to') else str(path.resolve()) == str(path))
        start = take['start_frame']
        require(slug+' bounded start', type(start) is int and start >= GUARD)
        with sf.SoundFile(str(path)) as source:
            require(slug+' DI header', source.samplerate == SR and source.frames >= start+TOTAL+GUARD)
            source.seek(start-GUARD)
            channels = source.read(TOTAL+2*GUARD, dtype='float64', always_2d=True)
        require(slug+' bounded read finite length', channels.shape[0] == TOTAL+2*GUARD and channels.shape[1] > 0 and np.isfinite(channels).all())
        raw = channels.mean(axis=1)
        check(slug+' excerpt hash', signalhash(raw) == prior['di_excerpt_sha256'])
        di10 = raw[GUARD:GUARD+TOTAL]
        rawscore = di10[192000:]
        independent_qc = qc(di10)
        check(slug+' raw QC validity', independent_qc['valid'] and prior['qc_valid'] is True and prior['qc']['valid'] is True)
        check(slug+' QC reasons', independent_qc['reasons'] == prior['qc']['reasons'])
        for part, measures in independent_qc['metrics'].items():
            for key, val in measures.items(): scalar(slug+' QC '+part+' '+key, val, prior['qc']['metrics'][part][key], 1e-14)
        target = target_from_raw(rawscore, average)
        with np.load(RUN/'prepare'/f'{slug}.npz', allow_pickle=False) as saved:
            require(slug+' prepare array keys', set(saved.files) == {'di', 'target', 'render_di'})
            array(slug+' raw scoring DI', rawscore, saved['di'])
            array(slug+' canonical target', target, saved['target'], ARRAY_TOL)
            array(slug+' original pre-roll/render DI', di10[96000:], saved['render_di'])
        oracle = score(target, target.copy(), rawscore, windows)
        require(slug+' independent canonical oracle', oracle['primary'] < 1e-6)
        for key, value in oracle.items(): scalar(slug+' oracle '+key, value, prior['oracle_scores'][key])
        # Verify float32 host input really retained original DI gain, 2s pre-roll and 52 zeros.
        intended = np.pad(di10[96000:], (0, 52)).astype(np.float32)
        host_name = 'di-'+digest(intended.tobytes())[:16]+'.wav'
        host_names.add(host_name)
        host_path = RUN/'render/au-host'/host_name
        with sf.SoundFile(str(host_path)) as f:
            check(slug+' host input format', f.samplerate == SR and f.frames == 384052 and f.channels == 1 and f.subtype == 'FLOAT')
            observed = f.read(dtype='float32', always_2d=True).mean(axis=1)
        array(slug+' host input original level', intended, observed)
        prepared[slug] = (rawscore, target)
        report['preparation'].append({**{k: take[k] for k in ('slug', 'content', 'take')},
            'source': expected, 'start_read': start-GUARD, 'frames_read': TOTAL+2*GUARD,
            'excerpt_sha256': signalhash(raw), 'target_sha256': signalhash(target), 'qc': independent_qc,
            'oracle_scores': oracle, 'host_input_sha256_float32': digest(intended.tobytes())})
        print('prepared independently '+slug, flush=True)
    check('host input coverage exactly all12', {p.name for p in (RUN/'render/au-host').glob('di-*.wav')} == host_names and len(host_names) == 12)
    # Fixed build identity from source bytes, without creating a renderer or host.
    h = hashlib.sha256()
    for name in ('match/renderer_au.py', 'scripts/au_probe.swift', 'scripts/au_render_server.swift'):
        p = ROOT/name
        h.update(p.name.encode()+b'\0'+p.read_bytes()+b'\0')
    build = 'audio-unit-renderer-'+h.hexdigest()[:12]
    metadata = renders['rows'][0]['renderer_metadata']
    expected_meta = {'renderer_id': 'swift', 'sample_rate': SR, 'block_size': 512, 'plugin_version': '1.1.1',
        'renderer_build': build, 'quality_mode': 'standard;amplitude=1;settle_ms=0;warmup_s=0;isolate=auto;process=reuse',
        'reproducible': False, 'band_noise_db': .23}
    check('renderer metadata fixed options', all(metadata.get(k) == v for k, v in expected_meta.items()))
    for row in renders['rows']:
        check(row['slug']+' renderer identity', row['renderer_metadata'] == metadata)
    canary = readj(RUN/'render/repeatability.json')
    with np.load(RUN/'render/repeatability-audio.npz', allow_pickle=False) as saved:
        require('canary array keys', set(saved.files) == {'first', 'repeat'})
        first, repeat = saved['first'], saved['repeat']
    require('canary saved full waves', first.shape == repeat.shape == (384052,) and np.isfinite(first).all() and np.isfinite(repeat).all())
    a, b = first[96052:], repeat[96052:]
    require('canary finite active', a.shape == b.shape == (SIX,) and min(np.std(a), np.std(b)) >= 1e-5)
    edges = [80, 160, 320, 640, 1280, 2560, 4000]
    f = np.fft.rfftfreq(SIX, 1/SR)
    hann = .5-.5*np.cos(2*np.pi*np.arange(SIX)/SIX)
    powers = []
    for x in (a, b):
        power = np.abs(np.fft.rfft(x*hann))**2
        powers.append([float(power[(f >= lo) & ((f <= hi) if hi == 4000 else (f < hi))].sum()) for lo, hi in zip(edges[:-1], edges[1:])])
    active = [i for i, v in enumerate(powers[0]) if v >= max(powers[0])*1e-4]
    drift = [float(10*np.log10(v/u)) if min(u, v) > 0 else None for u, v in zip(*powers)]
    rmsdrift = float(20*np.log10(np.sqrt(np.mean(b*b))/np.sqrt(np.mean(a*a))))
    passed = abs(rmsdrift) <= 1 and all(drift[i] is not None and abs(drift[i]) <= 1 for i in active)
    require('independent saved-wave canary gate', passed and bool(active))
    scalar('canary rms drift', rmsdrift, canary['rms_drift_db'])
    check('canary active bands', active == canary['active_band_indices'])
    check('canary edge/limit/pass', canary['band_edges_hz'] == edges and canary['limit_db'] == 1 and canary['passed'] is passed)
    for label, own, saved in [('first power', powers[0], canary['first_band_power']), ('repeat power', powers[1], canary['repeat_band_power']), ('drift', drift, canary['band_drift_db'])]:
        for i, (u, v) in enumerate(zip(own, saved)): scalar('canary '+label+' '+str(i), u, v, 1e-6 if 'power' in label else SCORE_TOL)
    scalar('canary max waveform difference', float(np.max(np.abs(a-b))), canary['waveform_max_absolute_difference'])
    scalar('canary relative RMS difference', float(np.sqrt(np.mean((a-b)**2)/np.mean(a**2))), canary['waveform_relative_rms_difference'])
    check('canary sample hashes', signalhash(a) == canary['first_hash'] and signalhash(b) == canary['repeat_hash'])
    check('canary metadata identity', canary['same_renderer_identity'] is True and canary['first_renderer_metadata'] == canary['repeat_renderer_metadata'] == metadata)
    check('first full render hash', signalhash(first) == renders['rows'][0]['render_hash'])
    scalar('first full render peak', float(np.max(np.abs(first))), renders['rows'][0]['render_peak'], 0)
    log = (RUN/'render/au-host/server.log').read_text()
    host_pids = re.findall(r'au_render_server\[(\d+):', log)
    check('saved log one host /14 requests', len(set(host_pids)) == 1 and len(host_pids) == 14,
          {'observed_pids': sorted(set(host_pids)), 'observed_log_records': len(host_pids)})
    report['canary'] = {'passed': passed, 'rms_drift_db': rmsdrift, 'active_band_indices': active,
                        'band_drift_db': drift, 'renderer_metadata': metadata}
    rendered = {}
    for take, row in zip(takes, renders['rows']):
        slug = take['slug']
        with np.load(RUN/'render'/f'{slug}.npz', allow_pickle=False) as saved:
            require(slug+' render keys', set(saved.files) == {'net_input', 'baseline'})
            x, baseline = saved['net_input'], saved['baseline']
        require(slug+' six-second finite render', x.shape == baseline.shape == (SIX,) and np.isfinite(x).all() and np.isfinite(baseline).all() and np.std(x) >= 1e-5)
        array(slug+' exact +52 latency relationship', x[52:], baseline[:-52])
        if slug == takes[0]['slug']:
            array(slug+' saved full-wave net input slice', first[96000:96000+SIX], x)
            array(slug+' saved full-wave baseline slice', first[96052:], baseline)
        check(slug+' recorded peak bounds retained samples', math.isfinite(row['render_peak']) and row['render_peak'] >= max(float(np.max(np.abs(x))), float(np.max(np.abs(baseline)))))
        rendered[slug] = (x, baseline)
    # Independent gate fixtures: strict diagnostic wins/groups, inclusive 10%, bad coverage.
    fixture = [{**{k: t[k] for k in ('slug', 'content', 'take')}, 'qc_valid': True, 'morgan_input': 1., 'morgan_net': .9, 'oracle': 0.} for t in takes]
    check('gate inclusive boundary', gate(fixture, takes)['passed'])
    low = [dict(r, morgan_net=.900001) for r in fixture]
    check('gate below boundary', gate(low, takes)['disposition'] == 'FAIL')
    bad = [dict(r) for r in fixture]; bad[0]['morgan_input'] = 0.
    check('gate zero denominator', gate(bad, takes)['disposition'] == 'INCONCLUSIVE')
    check('gate missing coverage', gate(fixture[:-1], takes)['disposition'] == 'INCONCLUSIVE')
    diag = [dict(r, morgan_net=1.2 if i < 6 else .1) for i, r in enumerate(fixture)]
    check('gate no added win/group criteria', gate(diag, takes)['passed'] and gate(diag, takes)['strict_wins'] == 6 and gate(diag, takes)['group_medians']['chords'] < 0)
    report['status'] = 'PREPARATION_RENDER_VERIFIED_REPLAY_PENDING'
    save()
    # Main explicitly authorized replay after primary completion in this conversation.
    sys.path.insert(0, str(ROOT))
    from learn import direc as D
    require('no shared C/P/R/V numerical imports', not any(n in sys.modules for n in ('learn.di_morgan_control', 'learn.di_domain_pilot', 'learn.run_di_domain_pilot', 'learn.run_di_domain_pilot_v2')))
    net = D.build_model().cpu()
    net.load_state_dict(torch.load(allowed_assets['model'][0], map_location='cpu', weights_only=True))
    net.eval()
    predictions = {}
    for take, prep_row in zip(takes, report['preparation']):
        slug = take['slug']
        x, baseline = rendered[slug]
        raw, target = prepared[slug]
        prediction = D.rebuild(net, x.astype(np.float32), device=torch.device('cpu'))
        own_net = score(prediction, target, raw, windows)
        own_input = score(baseline, target, raw, windows)
        require(slug+' all independent metrics valid', all(math.isfinite(v) and v >= 0 for s in (own_net, own_input) for v in s.values()) and own_input['primary'] > 0)
        improvement = (own_input['primary']-own_net['primary'])/own_input['primary']
        row = {**{k: take[k] for k in ('slug', 'content', 'take')}, 'qc_valid': prep_row['qc']['valid'],
               'network_scores': own_net, 'input_scores': own_input, 'oracle': prep_row['oracle_scores']['primary'],
               'morgan_input': own_input['primary'], 'morgan_net': own_net['primary'], 'relative_improvement': improvement,
               'prediction_sha256_float32': digest(prediction.tobytes()), 'prediction_dtype': str(prediction.dtype),
               'input_sha256_float32': digest(x.astype(np.float32).tobytes())}
        predictions[slug] = prediction
        report['replay'].append(row)
        report['status'] = 'REPLAY_IN_PROGRESS_PRIMARY_SCORES_UNREAD'
        save()
        print('replayed independently '+slug, flush=True)
    require('all12 own predictions/metrics derived before primary read', len(report['replay']) == len(predictions) == 12)
    report['independent_screen'] = gate(report['replay'], takes)
    report['status'] = 'ALL12_INDEPENDENT_DERIVATIONS_SAVED_PRIMARY_SCORES_UNREAD'
    save()
    # Blindness barrier: primary inference NUMBERS and predictions are first read here.
    primary = readj(RUN/'infer/result.json')
    report['primary_scores_unread'] = False
    report['blindness_barrier'] = 'All12 own predictions, hashes, independent metrics and gate persisted before primary result/prediction reads.'
    require('primary inference complete', primary['complete'] is True)
    coverage('infer report coverage', primary['rows'], takes)
    check('infer exact saved prediction coverage', {p.stem for p in (RUN/'infer').glob('*.npz')} == set(predictions))
    check('infer progress equals report', [json.loads(l) for l in (RUN/'infer/progress.jsonl').read_text().splitlines()] == primary['rows'])
    check('infer attribution/version/budget', primary['attribution'] == ATTRIBUTION and primary['torch_version'] == torch.__version__ and 0 <= primary['elapsed_seconds'] <= 900)
    for own, prior in zip(report['replay'], primary['rows']):
        slug = own['slug']
        with np.load(RUN/'infer'/f'{slug}.npz', allow_pickle=False) as saved:
            require(slug+' primary prediction keys', set(saved.files) == {'prediction'})
            primary_prediction = saved['prediction']
        array(slug+' checkpoint replay prediction bytes', predictions[slug], primary_prediction)
        check(slug+' prediction hash identical', digest(primary_prediction.tobytes()) == own['prediction_sha256_float32'])
        check(slug+' primary raw-QC flag', prior['qc_valid'] is own['qc_valid'])
        for group in ('network_scores', 'input_scores'):
            check(slug+' '+group+' exact metric coverage', set(prior[group]) == {'primary', 'canonical_waveform_l1', 'raw_lowband'})
            for key, value in own[group].items(): scalar(slug+' '+group+' '+key, value, prior[group][key])
        for key in ('morgan_input', 'morgan_net', 'oracle'): scalar(slug+' primary '+key, own[key], prior[key])
    independently_from_primary = gate(primary['rows'], takes)
    for label, other in [('recorded primary gate', primary['screen']), ('own gate over primary rows', independently_from_primary)]:
        own = report['independent_screen']
        for key in ('valid', 'passed', 'disposition', 'strict_wins'):
            check(label+' '+key, own[key] == other[key])
        scalar(label+' median', own['median_relative_improvement'], other['median_relative_improvement'])
        for group in ('chords', 'scales'): scalar(label+' '+group, own['group_medians'][group], other['group_medians'][group])
        check(label+' per-take coverage', [r['slug'] for r in other['per_take']] == [t['slug'] for t in takes])
        for a, b in zip(own['per_take'], other['per_take']): scalar(label+' '+a['slug'], a['relative_improvement'], b['relative_improvement'])
    require('sources unchanged through verification', pins == {name: filehash(ROOT/name) for name in PIN_NAMES})
    report['status'] = 'VERIFIED_WITH_EVIDENCE_LIMITS' if not report['failures'] else 'VERIFICATION_FAILED'
    save()
    print(json.dumps({'status': report['status'], 'checks': len(report['checks']), 'failures': len(report['failures']),
                      'screen': report['independent_screen']}, indent=2), flush=True)


if __name__ == '__main__':
    try:
        verify()
    except Exception as error:
        report['status'] = 'VERIFIER_ERROR'
        report['failures'].append({'error_type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()})
        save()
        raise
