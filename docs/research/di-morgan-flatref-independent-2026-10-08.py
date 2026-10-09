"""Bounded independent reconstruction; only two verification reports are written.

No project numerical imports, model, raw recording, catalog, network or rendering.
All twelve experimental values and their gate are persisted before opening primary
result/replay/progress/waveform files. Prior committed evidence is explicitly inherited.
"""
from __future__ import annotations
import copy
import datetime
import gzip
import hashlib
import importlib.metadata
import json
import math
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
OLD = ROOT / 'tmp/di-morgan-control-20261008'
PRIMARY = ROOT / 'tmp/di-morgan-flatref-20261008'
OUT = ROOT / 'tmp/di-morgan-flatref-verification.json'
MD = ROOT / 'tmp/di-morgan-flatref-verification.md'
HEAD = 'c8c40ad1d89404dfa7aa7177596899d4526f371a'
SR = 48000
SIX = 6 * SR
FFTS = (256, 512, 1024, 2048, 4096)
CENTER = slice(72000, 216000)
TOL = 1e-8
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
started = time.monotonic()
report = dict(status='RUNNING', pinned_revision=HEAD, checks=[], failures=[], replay=[],
              independent_rows=[], primary_numerical_values_unread=True,
              limitations=[
                  'Inherited full ten-second raw-DI QC and original canary/renderer stability from the committed successful independent verification; only saved six-second raw score QC is freshly recomputed. Calibration seconds 0-2 are absent from allowed arrays.',
                  'Original full wet output survives only for the first take/canary. Other eleven full-render hashes/peaks and pre-roll cannot be reconstructed in this scope.',
                  'No separate plugin parameter-command transcript exists. This verification makes no new claim about physical plugin state.',
                  'Saved net-input/baseline overlap checks the fixed 52-sample slicing, without remeasuring physical latency or fitting alignment.',
                  'Predictions are frozen artifacts, checked against prior independently replayed prediction bytes; no fresh model inference is authorized or performed.',
                  'One fixed clean Morgan chain, one player/guitar, twelve reused development performances. No native-transfer, driven-chain, multi-guitar, reserved-validation, song-ranking, shipping or long-training conclusion.'
              ])

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def filehash(path):
    return digest(Path(path).read_bytes())

def readj(path):
    return json.loads(Path(path).read_text())

def check(name, passed, detail=None):
    item = {'name': name, 'passed': bool(passed)}
    if detail is not None:
        item['detail'] = detail
    report['checks'].append(item)
    if not passed:
        report['failures'].append(item)
    return bool(passed)

def require(name, passed, detail=None):
    if not check(name, passed, detail):
        raise ValueError(name)

def scalar(name, actual, expected, tol=TOL):
    error = abs(float(actual)-float(expected))
    check(name, math.isfinite(actual) and math.isfinite(expected) and error <= tol,
          {'actual': float(actual), 'expected': float(expected), 'absolute_error': error, 'tolerance': tol})
    return error

def arrcheck(name, actual, expected, tol=0):
    same_shape = actual.shape == expected.shape
    error = float(np.max(np.abs(actual.astype(np.float64)-expected.astype(np.float64)))) if same_shape else None
    check(name, same_shape and bool(np.isfinite(actual).all()) and bool(np.isfinite(expected).all()) and error <= tol,
          {'actual_shape': list(actual.shape), 'expected_shape': list(expected.shape), 'max_absolute_error': error, 'tolerance': tol})
    return error

def save():
    report['elapsed_seconds'] = time.monotonic()-started
    OUT.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    lines = ['# Independent fixed-render Morgan flatref verification', '',
             f"Status: **{report['status']}**. {len(report['checks'])} checks; {len(report['failures'])} failures.", '',
             'Own NumPy formulas reconstruct flatref, targets, exact five-FFT scores and gate. No project scoring/canonical/gate functions are imported or called.', '']
    if 'independent_screen' in report:
        s = report['independent_screen']
        lines += [f"Stronger screen: **{s['disposition']}**, valid={s['valid']}; median improvement {100*s.get('median_relative_improvement', 0):.10f}%; {s.get('strict_wins', 0)}/12 strict wins.",
                  f"Group medians: {s.get('group_medians')}", '',
                  '| Take | Wet primary | Net primary | Flatref primary | Simple | Net improvement |',
                  '| --- | ---: | ---: | ---: | --- | ---: |']
        for row in report['independent_rows']:
            lines.append(f"| {row['slug']} | {row['wet']:.12g} | {row['net']:.12g} | {row['flatref']:.12g} | {row['simple_choice']} | {100*row['relative_improvement']:.8f}% |")
    if 'comparison_summary' in report:
        lines += ['', 'Comparison: '+json.dumps(report['comparison_summary'], sort_keys=True)]
    lines += ['', 'All twelve own values, waveform hashes and gate were saved before primary numerical access; the JSON records the timestamp and digest.', '', '## Limits', '']
    lines += ['- '+v for v in report['limitations']]
    if report['failures']:
        lines += ['', '## Preserved failures', '']+['- '+json.dumps(f) for f in report['failures']]
    MD.write_text('\n'.join(lines)+'\n')

def normalize(x):
    x = np.asarray(x, dtype=np.float64)
    return x/(np.std(x)+1e-9)*0.1

def mr(a, b, windows):
    total = 0.0
    for n in FFTS:
        mags = []
        for x in (a, b):
            padded = np.pad(x, (n//2, n//2), mode='reflect')
            blocks = np.lib.stride_tricks.sliding_window_view(padded, n)[::n//4]
            mags.append(np.abs(np.fft.rfft(blocks*windows[n], axis=1))+1e-6)
        a_mag, b_mag = mags
        total += np.linalg.norm(a_mag-b_mag)/(np.linalg.norm(b_mag)+1e-6)
        total += np.mean(np.abs(np.log(a_mag)-np.log(b_mag)))
    return float(total/5)

def scores(prediction, target, raw, windows):
    a, b = normalize(prediction[CENTER]), normalize(target[CENTER])
    filt = butter(4, [80, 4000], fs=SR, btype='bandpass', output='sos')
    low = [normalize(sosfiltfilt(filt, np.asarray(x, dtype=np.float64), padtype='odd', padlen=27)[CENTER]) for x in (prediction, raw)]
    return {'primary': mr(a, b, windows),
            'canonical_waveform_l1': float(np.mean(np.abs(a-b))),
            'raw_lowband': mr(*low, windows)}

def own_canonical(signal, average):
    x = np.asarray(signal, dtype=np.float64)
    n = 4096
    blocks = np.lib.stride_tricks.sliding_window_view(x, n)[::1024]
    power = np.abs(np.fft.rfft(blocks*np.hanning(n), axis=1))**2
    energies = power.sum(axis=1)
    active = 10*np.log10(energies+1e-20) >= 10*np.log10(energies.max()+1e-20)-40
    p = power[active].mean(axis=0)
    freq = np.fft.rfftfreq(n, 1/SR)
    smooth = np.empty(2049, dtype=np.float64)
    for i, f in enumerate(freq):
        selected = (freq >= f*2**(-1/12)) & (freq <= f*2**(1/12))
        smooth[i] = p[selected].mean() if selected.any() else p[i]
    own_db = 10*np.log10(smooth+1e-20)
    gains = np.clip(np.asarray(average, dtype=np.float64)-(own_db-own_db.mean()), -15, 15)
    interpolated = np.interp(np.fft.rfftfreq(len(x), 1/SR), freq, gains)
    return np.fft.irfft(np.fft.rfft(x)*10**(interpolated/20), n=len(x))

def qc_score(x):
    rms = float(np.sqrt(np.mean(x**2)))
    clipped = float(np.mean(np.abs(x) >= .999))
    frame_rms = np.sqrt(np.mean(x.reshape(-1, 480)**2, axis=1))
    active = float(np.mean(frame_rms > frame_rms.max()*.01))
    return {'rms': rms, 'clipped_fraction': clipped, 'active_fraction': active}, rms >= 1e-5 and clipped <= 1e-4 and active >= .8

def gate(rows, takes):
    reject = {'valid': False, 'passed': False, 'disposition': 'INCONCLUSIVE'}
    try:
        expected = {t['slug']: (t['content'], t['take']) for t in takes}
        actual = {r['slug']: r for r in rows}
        if len(rows) != 12 or len(takes) != 12 or len(expected) != 12 or len(actual) != 12 or set(actual) != set(expected):
            return reject
        if len({v[1] for v in expected.values()}) != 12 or any(sum(v[0] == g for v in expected.values()) != 6 for g in ('chords', 'scales')):
            return reject
        ordered = [actual[t['slug']] for t in takes]
        improvements = []
        for row in ordered:
            if (row['content'], row['take']) != expected[row['slug']] or row['qc_valid'] is not True:
                return reject
            for key in ('wet', 'net', 'flatref', 'oracle'):
                val = row[key]
                if type(val) not in (float, int) or not math.isfinite(val) or val < 0:
                    return reject
            simple = min(row['wet'], row['flatref'])
            if simple <= 0 or row['oracle'] >= 1e-6:
                return reject
            improvements.append((simple-row['net'])/simple)
        median = statistics.median(improvements)
        groups = {g: statistics.median(v for r, v in zip(ordered, improvements) if r['content'] == g) for g in ('chords', 'scales')}
        wins = sum(v > 0 for v in improvements)
        passed = median >= .1-8*math.ulp(.1) and wins >= 9 and all(v > 0 for v in groups.values())
        return {'valid': True, 'passed': passed, 'disposition': 'PASS' if passed else 'FAIL',
                'median_relative_improvement': median, 'strict_wins': wins, 'group_medians': groups,
                'per_take': [{'slug': r['slug'], 'relative_improvement': v} for r, v in zip(ordered, improvements)]}
    except (KeyError, TypeError, ValueError):
        return reject

def coverage(name, rows, takes, identity=True):
    require(name+' coverage', len(rows) == len(takes) == 12 and [r['slug'] for r in rows] == [t['slug'] for t in takes] and len({r['slug'] for r in rows}) == 12)
    if identity:
        require(name+' identities', all((r['content'], r['take']) == (t['content'], t['take']) for r, t in zip(rows, takes)))

def verify():
    require('exact project environment and disabled bytecode', Path(sys.prefix).resolve() == (ROOT/'.venv').resolve() and sys.dont_write_bytecode)
    require('starting branch/HEAD', subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD and subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip() == 'codex/song-model-continuation')
    report['runtime'] = {'python': sys.version, 'prefix': sys.prefix, 'packages': {n: importlib.metadata.version(n) for n in ('numpy', 'scipy')}}
    report['verifier_sha256'] = filehash(__file__)
    prior = readj(ROOT/'docs/di-morgan-control-verification.json')
    original = readj(ROOT/'docs/di-morgan-control.json')
    prep = readj(ROOT/'docs/di-morgan-control-prepare.json')
    render = readj(ROOT/'docs/di-morgan-control-render.json')
    manifest = readj(ROOT/'docs/di-domain-pilot-inputs.json')
    correction = readj(ROOT/'docs/di-domain-pilot-v2-inputs.json')
    takes = manifest['takes']
    report['attribution'] = manifest['attribution']
    require('successful committed prior independent evidence', prior['status'] == 'VERIFIED_WITH_EVIDENCE_LIMITS' and prior['failures'] == [] and len(prior['checks']) == 767 and all(c['passed'] is True for c in prior['checks']) and prior['independent_screen']['passed'] is True)
    report['inherited_evidence'] = {'verification_sha256': filehash(ROOT/'docs/di-morgan-control-verification.json'), 'pinned_revision': prior['pinned_revision'], 'checks': len(prior['checks']), 'limitations': prior['limitations'], 'canary': prior['canary']}
    pins = {n: filehash(ROOT/n) for n in PIN_NAMES}
    require('43 unique source pins', len(pins) == len(PIN_NAMES) == 43)
    require('unchanged 35 inherited source pins', {n: pins[n] for n in PIN_NAMES[:35]} == prior['source_pins'])
    for n in PIN_NAMES:
        require('committed bytes '+n, digest(subprocess.check_output(['git', 'show', f'{HEAD}:{n}'], cwd=ROOT)) == pins[n])
    require('committed declaration', '**Declared:' in (ROOT/'docs/di-morgan-flatref-plan.md').read_text())
    report['source_pins'] = pins
    report['source_pins_digest'] = digest(''.join(f'{pins[n]}  {n}\n' for n in sorted(pins)).encode())
    commit_time = int(subprocess.check_output(['git', 'show', '-s', '--format=%ct', HEAD], cwd=ROOT, text=True).strip())
    times = {str(p.relative_to(ROOT)): {'birth': p.stat().st_birthtime, 'mtime': p.stat().st_mtime} for p in (PRIMARY, PRIMARY/'provenance.json', ROOT/'tmp/di-morgan-flatref-20261008.log')}
    report['commit_before_execution'] = {'commit_unix_time': commit_time, 'artifact_times': times}
    require('commit predates primary directory provenance and log creation', all(commit_time < v['birth'] for v in times.values()))
    require('primary 43 provenance pins', readj(PRIMARY/'provenance.json')['pins'] == pins)
    for stage, archived in [('prepare', 'docs/di-morgan-control-prepare.json'), ('render', 'docs/di-morgan-control-render.json'), ('infer', 'docs/di-morgan-control.json')]:
        require('byte identical original '+stage+' archive', filehash(OLD/stage/'result.json') == pins[archived])
        require('original '+stage+' 35 provenance pins', readj(OLD/stage/'provenance.json')['pins'] == prior['source_pins'])
    coverage('preparation', prep['rows'], takes)
    coverage('original inference', original['rows'], takes)
    coverage('prior preparation verification', prior['preparation'], takes)
    coverage('prior prediction replay', prior['replay'], takes)
    coverage('render', render['rows'], takes, False)
    require('complete original prepare/render/infer', prep['complete'] is True and prep['valid'] is True and render['complete'] is True and original['complete'] is True and original['screen']['passed'] is True)
    expected = {f'tmp/di-morgan-control-20261008/{stage}/{t["slug"]}.npz' for stage in ('prepare', 'render', 'infer') for t in takes}
    artifacts = {}
    for line in (ROOT/'docs/di-morgan-flatref-inputs.sha256').read_text().splitlines():
        h, n = line.split('  ', 1)
        require('manifest allowed unique path '+n, n in expected and n not in artifacts and re.fullmatch('[a-f0-9]{64}', h) is not None and not (ROOT/n).is_symlink() and (ROOT/n).resolve().is_relative_to(OLD.resolve()))
        require('frozen input bytes '+n, filehash(ROOT/n) == h)
        artifacts[n] = h
    require('exact 36 input coverage', set(artifacts) == expected and len(artifacts) == 36)
    report['input_artifacts'] = artifacts
    require('frozen average exact declared identity', manifest['average'] == {'path': '/Users/yoavbz/ndsp-presets/learn/direc/cache/average-fold2.npy', 'sha256': '9aa3c3bfefc2bc5ba21394be29876b5ef5e0120ad2f55f0b890e599ec3bee9a8'} and filehash(manifest['average']['path']) == manifest['average']['sha256'])
    report['average'] = manifest['average']
    average = np.load(manifest['average']['path'], allow_pickle=False)
    require('average shape finite', average.shape == (2049,) and np.isfinite(average).all())
    require('correction identity', correction['schema'] == 2 and correction['tolerance'] == TOL and correction['window_family'] == 'torch32' and correction['window_dtype'] == '<f4' and correction['original_inputs'] == 'docs/di-domain-pilot-inputs.json' and correction['original_inputs_sha256'] == pins['docs/di-domain-pilot-inputs.json'] and correction['windows'] == 'docs/di-domain-metric-probe-windows.json.gz')
    blob = (ROOT/correction['windows']).read_bytes()
    require('window archive bytes', digest(blob) == correction['windows_sha256'])
    raw_text = gzip.decompress(blob)
    require('window decompressed bytes', digest(raw_text) == correction['windows_raw_sha256'])
    table = json.loads(raw_text)
    require('all five window sizes', set(table) == {str(n) for n in FFTS})
    windows = {}
    report['windows'] = {}
    for n in FFTS:
        row = table[str(n)]['torch32']
        require(f'window {n} exact bit definition', row['dtype'] == '<f4' and len(row['bits']) == n and all(type(b) is int and 0 <= b < 2**32 for b in row['bits']))
        bits = np.array(row['bits'], dtype='<u4').tobytes()
        require(f'window {n} coefficient hash', digest(bits) == row['sha256'])
        windows[n] = np.frombuffer(bits, dtype='<f4').astype(np.float64)
        require(f'window {n} finite', np.isfinite(windows[n]).all())
        windows[n].flags.writeable = False
        report['windows'][str(n)] = row['sha256']
    # Own gate boundary checks, including the added win/group requirements.
    fixture = [{**{k:t[k] for k in ('slug','content','take')}, 'qc_valid': True, 'wet': 1., 'flatref': 1., 'net': .9, 'oracle': 0.} for t in takes]
    require('own gate inclusive ten-percent boundary', gate(fixture, takes)['passed'])
    f = copy.deepcopy(fixture)
    for r in f[:4]: r['net'] = 1.01
    require('own gate fewer than nine wins fails', gate(f, takes)['disposition'] == 'FAIL')
    f = copy.deepcopy(fixture)
    for r in f[:3]: r['net'] = 1.01
    f[3]['net'] = .99
    require('own gate group-median zero fails', gate(f, takes)['disposition'] == 'FAIL')
    f = copy.deepcopy(fixture); f[0]['flatref'] = 0.
    require('own gate zero simple inconclusive', gate(f, takes)['disposition'] == 'INCONCLUSIVE')
    require('own gate missing coverage inconclusive', gate(fixture[:-1], takes)['disposition'] == 'INCONCLUSIVE')
    loaded = []
    replay_errors = []
    for t, old, p, prior_p, prior_r in zip(takes, original['rows'], prep['rows'], prior['preparation'], prior['replay']):
        slug = t['slug']
        with np.load(OLD/'prepare'/f'{slug}.npz', allow_pickle=False) as z:
            require(slug+' prepare array keys', set(z.files) == {'di', 'target', 'render_di'})
            di, target, render_di = z['di'], z['target'], z['render_di']
        with np.load(OLD/'render'/f'{slug}.npz', allow_pickle=False) as z:
            require(slug+' render array keys', set(z.files) == {'net_input', 'baseline'})
            wet, net_input = z['baseline'], z['net_input']
        with np.load(OLD/'infer'/f'{slug}.npz', allow_pickle=False) as z:
            require(slug+' infer array keys', set(z.files) == {'prediction'})
            net = z['prediction']
        for name, x, size in [('di', di, SIX), ('target', target, SIX), ('wet', wet, SIX), ('net_input', net_input, SIX), ('net', net, SIX), ('render_di', render_di, 8*SR)]:
            require(slug+' finite active shape '+name, x.ndim == 1 and x.shape == (size,) and np.isfinite(x).all() and np.std(x) >= 1e-5)
        arrcheck(slug+' DI render interval overlap', render_di[2*SR:], di)
        arrcheck(slug+' fixed 52 sample wet slicing overlap', net_input[52:], wet[:-52])
        require(slug+' frozen prediction byte hash', net.dtype == np.float32 and digest(net.tobytes()) == prior_r['prediction_sha256_float32'])
        require(slug+' frozen network input float32 hash', digest(net_input.astype(np.float32).tobytes()) == prior_r['input_sha256_float32'])
        own_target = own_canonical(di, average)
        target_error = arrcheck(slug+' reconstructed canonical target', own_target, target, 1e-10)
        require(slug+' canonical target prior byte identity', digest(np.asarray(target, dtype='<f8').tobytes()) == prior_p['target_sha256'])
        qc, valid = qc_score(di)
        require(slug+' fresh raw score QC', valid)
        for key, value in qc.items(): scalar(slug+' raw score QC '+key, value, p['qc']['metrics']['score'][key], 1e-14)
        require(slug+' inherited full raw QC', p['qc_valid'] is True and p['qc']['valid'] is True and prior_p['qc']['valid'] is True and p['qc']['reasons'] == prior_p['qc']['reasons'] == [] and p['di_excerpt_sha256'] == prior_p['excerpt_sha256'])
        for section in ('calibration', 'score'):
            q = p['qc']['metrics'][section]
            require(slug+' archived QC threshold '+section, q['rms'] >= 1e-5 and q['clipped_fraction'] <= 1e-4 and q['active_fraction'] >= .8)
            for key, value in q.items(): scalar(slug+' inherited QC consistency '+section+' '+key, value, prior_p['qc']['metrics'][section][key], 1e-14)
        oracle = scores(own_target, own_target.copy(), di, windows)
        require(slug+' fresh canonical oracle', oracle['primary'] < 1e-6 and oracle['canonical_waveform_l1'] == 0.)
        for key, value in oracle.items(): scalar(slug+' oracle '+key, value, p['oracle_scores'][key])
        row = {**{k:t[k] for k in ('slug','content','take')}, 'qc_valid': valid, 'oracle': oracle['primary']}
        errors = {}
        for name, x in [('input_scores', wet), ('network_scores', net)]:
            row[name] = scores(x, target, di, windows)
            for key, value in row[name].items():
                e = scalar(slug+' original72 '+name+'.'+key, value, old[name][key])
                errors[name+'.'+key] = e
                replay_errors.append(e)
                require(slug+' valid replay loss '+name+'.'+key, math.isfinite(value) and value >= 0)
        row.update(wet=row['input_scores']['primary'], net=row['network_scores']['primary'])
        scalar(slug+' original wet scalar', row['wet'], old['morgan_input'])
        scalar(slug+' original net scalar', row['net'], old['morgan_net'])
        scalar(slug+' original oracle scalar', row['oracle'], old['oracle'])
        report['replay'].append({'slug': slug, 'scores': {k:row[k] for k in ('input_scores','network_scores')}, 'errors': errors, 'raw_score_qc': qc, 'canonical_target_max_error': target_error})
        loaded.append((row, di, target, wet))
    require('complete original72 replay before experimental calculation', len(replay_errors) == 72 and max(replay_errors) <= TOL and not report['failures'])
    report['original72_max_absolute_error'] = max(replay_errors)
    report['original72_replay_completed_utc'] = utc()
    save()
    flat_waves = {}
    for row, di, target, wet in loaded:
        flat = own_canonical(wet, average)
        require(row['slug']+' own flatref finite active', flat.shape == (SIX,) and np.isfinite(flat).all() and np.std(flat) >= 1e-5)
        flat_waves[row['slug']] = flat
        row['flatref_scores'] = scores(flat, target, di, windows)
        for key, v in row['flatref_scores'].items(): require(row['slug']+' valid flatref '+key, math.isfinite(v) and v >= 0)
        row['flatref'] = row['flatref_scores']['primary']
        row['simple'] = min(row['wet'], row['flatref'])
        row['simple_choice'] = 'flatref' if row['flatref'] < row['wet'] else 'wet'
        row['relative_improvement'] = (row['simple']-row['net'])/row['simple']
        row['flatref_waveform_sha256_float64'] = digest(np.asarray(flat, dtype='<f8').tobytes())
        report['independent_rows'].append(row)
    coverage('own experimental', report['independent_rows'], takes)
    report['independent_screen'] = gate(report['independent_rows'], takes)
    require('independent stronger screen valid', report['independent_screen']['valid'])
    barrier = {'rows': report['independent_rows'], 'screen': report['independent_screen']}
    report['blindness_barrier'] = {'utc': utc(), 'all12_derived_and_saved_before_primary_numerical_access': True, 'derivation_sha256': digest(json.dumps(barrier, sort_keys=True, allow_nan=False).encode())}
    report['status'] = 'DERIVED_PRIMARY_UNREAD'
    save()
    print('All12 independently derived and persisted; opening primary numerical results now.', flush=True)
    if not (PRIMARY/'result.json').exists():
        report['status'] = 'WAITING_FOR_MAIN_PRIMARY_COMPARISON'
        save()
        return
    # This is the first primary numerical access in this execution/conversation.
    report['primary_numerical_values_unread'] = False
    report['primary_first_numerical_access_utc'] = utc()
    result = readj(PRIMARY/'result.json')
    baseline_replay = readj(PRIMARY/'baseline-replay.json')
    progress = [json.loads(line) for line in (PRIMARY/'progress.jsonl').read_text().splitlines()]
    coverage('primary result', result['rows'], takes)
    coverage('primary progress', progress, takes)
    coverage('primary original replay', baseline_replay['rows'], takes, False)
    require('primary complete and successful original replay', result['complete'] is True and baseline_replay['passed'] is True)
    require('primary progress equals final rows', progress == result['rows'])
    require('primary exact 36 input source pins', result['input_artifacts'] == artifacts)
    require('primary attribution', result['attribution'] == manifest['attribution'])
    comparison_errors, wave_errors = [], []
    report['primary_artifact_hashes'] = {}
    for name in ('result.json', 'baseline-replay.json', 'progress.jsonl', 'provenance.json'):
        report['primary_artifact_hashes'][name] = filehash(PRIMARY/name)
    report['waveform_comparison'] = []
    for own, primary, replay in zip(report['independent_rows'], result['rows'], baseline_replay['rows']):
        slug = own['slug']
        require(slug+' primary QC identity', primary['qc_valid'] is own['qc_valid'])
        for arm in ('input_scores', 'network_scores', 'flatref_scores'):
            require(slug+' primary score key coverage '+arm, set(primary[arm]) == {'primary', 'canonical_waveform_l1', 'raw_lowband'})
            for key, v in own[arm].items(): comparison_errors.append(scalar(slug+' primary '+arm+'.'+key, v, primary[arm][key]))
        for key in ('wet', 'net', 'flatref', 'oracle'): comparison_errors.append(scalar(slug+' primary scalar '+key, own[key], primary[key]))
        require(slug+' primary replay exact scalar coverage', set(replay['errors']) == set(report['replay'][len(wave_errors)]['errors']))
        for key, val in replay['errors'].items():
            require(slug+' primary replay error within tolerance '+key, math.isfinite(val) and 0 <= val <= TOL)
            scalar(slug+' primary versus own replay error '+key, val, report['replay'][len(wave_errors)]['errors'][key])
        path = PRIMARY/f'{slug}.npz'
        report['primary_artifact_hashes'][path.name] = filehash(path)
        with np.load(path, allow_pickle=False) as z:
            require(slug+' primary flatref array keys', z.files == ['flatref'])
            saved = z['flatref']
        error = arrcheck(slug+' primary flatref waveform', flat_waves[slug], saved, 1e-10)
        identical = saved.dtype == np.float64 and saved.tobytes() == flat_waves[slug].tobytes()
        check(slug+' primary waveform byte identity', identical)
        wave_errors.append(error)
        report['waveform_comparison'].append({'slug': slug, 'max_absolute_error': error, 'byte_identical': identical, 'primary_sha256_float64': digest(np.asarray(saved, dtype='<f8').tobytes()), 'npz_sha256': report['primary_artifact_hashes'][path.name]})
    screen = result['screen']
    own_screen = report['independent_screen']
    require('primary exact gate key coverage', set(screen) == set(own_screen))
    for key in ('valid', 'passed', 'disposition', 'strict_wins'): require('primary stronger gate '+key, screen[key] == own_screen[key])
    comparison_errors.append(scalar('primary stronger gate median', own_screen['median_relative_improvement'], screen['median_relative_improvement']))
    require('primary gate exact group coverage', set(screen['group_medians']) == {'chords','scales'})
    for g in ('chords','scales'): comparison_errors.append(scalar('primary stronger gate group '+g, own_screen['group_medians'][g], screen['group_medians'][g]))
    require('primary gate per-take coverage', [r['slug'] for r in screen['per_take']] == [t['slug'] for t in takes])
    for a, b in zip(own_screen['per_take'], screen['per_take']): comparison_errors.append(scalar(a['slug']+' primary stronger gate improvement', a['relative_improvement'], b['relative_improvement']))
    require('all 43 sources unchanged through verification', pins == {n:filehash(ROOT/n) for n in PIN_NAMES})
    require('all36 fixed artifacts unchanged through verification', artifacts == {n:filehash(ROOT/n) for n in artifacts})
    require('average unchanged through verification', filehash(manifest['average']['path']) == manifest['average']['sha256'])
    require('primary artifacts unchanged during comparison', report['primary_artifact_hashes'] == {n:filehash(PRIMARY/n) for n in report['primary_artifact_hashes']})
    require('HEAD unchanged through verification', subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip() == HEAD)
    require('verifier unchanged during execution', filehash(__file__) == report['verifier_sha256'])
    report['comparison_summary'] = {'original_replay_scalar_count': 72, 'primary_score_count': 108, 'score_absolute_tolerance': TOL, 'original72_max_absolute_error': max(replay_errors), 'primary_max_score_scalar_gate_absolute_error': max(comparison_errors), 'flatref_waveforms': 12, 'waveforms_byte_identical': sum(v['byte_identical'] for v in report['waveform_comparison']), 'waveform_max_absolute_error': max(wave_errors), 'source_pins': 43, 'input_pins': 36, 'gate_disposition': own_screen['disposition']}
    report['status'] = 'VERIFIED_WITH_EVIDENCE_LIMITS' if not report['failures'] else 'FAILED'
    save()

if __name__ == '__main__':
    if OUT.exists() or MD.exists():
        raise SystemExit('Refuse to overwrite existing verification reports')
    OUT.touch(exist_ok=False)
    MD.touch(exist_ok=False)
    try:
        verify()
    except BaseException as exc:
        report['status'] = 'FAILED'
        report['failures'].append({'exception': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()})
        save()
        raise
    print(json.dumps({'status': report['status'], 'checks': len(report['checks']), 'failures': len(report['failures']), 'summary': report.get('comparison_summary'), 'screen': report.get('independent_screen')}), flush=True)
